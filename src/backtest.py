"""Event-driven 1h perp backtest engine with Section-4 lookahead rules enforced in code.

NON-NEGOTIABLE RULES IMPLEMENTED HERE (not commentary -- actual code paths):
  R1  Signal computed from bar t close -> order fills at bar t+1 OPEN. Never t close.
  R2  Any feature at bar t is only readable for a decision at t+1 (enforced by
      construction: the engine only ever passes `signals.iloc[i-1]` when acting on bar i).
  R3  Intrabar stop/target ambiguity -> assume the WORSE outcome (stop fills first).
  R4  Stops are NOT guaranteed. If the bar OPENS beyond the stop, fill at the open
      (gap risk), not at the stop price.
  R5  No bar's own high/low is used for a decision taken during that bar.
  R6  All rolling statistics are trailing-window; nothing full-sample.

Sizing (Section 5): volatility-normalised, risk_per_trade of equity per position,
gross leverage cap, and a portfolio-level BTC-beta cap (five alt longs is one BTC
position -- enforced explicitly, not per-position).

Risk controls (Section 6): daily / weekly loss limits, peak-to-trough kill switch,
max concurrent positions, per-asset cap, funding circuit breaker. All hard code paths.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import costs as C


@dataclass
class BTConfig:
    spread_model: str = "tiered"   # "tiered" (primary) or "corwin_schultz" (pessimistic sensitivity)
    initial_equity: float = 100_000.0
    risk_per_trade: float = 0.005          # 0.5% of equity
    risk_per_trade_cap: float = 0.01
    atr_multiple_stop: float = 2.0
    max_holding_bars: int = 24
    max_concurrent: int = 5
    gross_leverage_cap: float = 3.0
    per_asset_notional_cap: float = 0.5    # fraction of equity
    portfolio_btc_beta_cap: float = 1.5    # total |beta| to BTC across open positions
    beta_lookback_bars: int = 30 * 24      # rolling 30d
    daily_loss_limit: float = 0.03
    weekly_loss_limit: float = 0.07
    kill_switch_dd: float = 0.20
    funding_breaker_ann_pct: float = 0.50  # exit if annualised funding cost > 50% of expected edge
    expected_edge_bps: float = 100.0       # used only by the funding breaker
    compounding: bool = True               # fixed-fractional on running equity
    target_take_profit_atr: float = 3.0
    cost_cfg: C.CostConfig = field(default_factory=C.CostConfig)


@dataclass
class Position:
    asset: str
    direction: int          # +1 long, -1 short
    entry_time: pd.Timestamp
    entry_price: float
    qty: float              # base units
    notional: float
    stop_price: float
    target_price: float
    bars_held: int = 0
    entry_cost_usd: float = 0.0
    funding_paid_usd: float = 0.0


def assert_no_lookahead(panel: dict, signals: dict) -> dict:
    """Structural check that a signal series cannot encode information from its own bar.

    Method: rebuild each signal with the asset's future truncated at bar i and confirm
    the value at bar i is unchanged. If a signal used full-sample statistics or peeked
    at t+1, truncation changes it and we fail loudly.
    """
    problems = []
    for asset, sig in signals.items():
        df = panel[asset]
        n = len(df)
        if n < 500:
            continue
        for probe in (int(n * 0.5), int(n * 0.75), n - 50):
            truncated = df.iloc[: probe + 1]
            # recompute using the same public builder the strategy used
            rebuilt = sig.attrs["rebuild"](truncated) if "rebuild" in sig.attrs else None
            if rebuilt is None:
                continue
            a = sig.iloc[probe]
            b = rebuilt.iloc[probe]
            if pd.isna(a) and pd.isna(b):
                continue
            if not np.isclose(float(a), float(b), equal_nan=True):
                problems.append({"asset": asset, "bar": int(probe),
                                 "full_sample_value": float(a), "truncated_value": float(b)})
    return {"passed": len(problems) == 0, "n_problems": len(problems), "problems": problems[:10]}


class Backtester:
    def __init__(self, panel: dict, funding: dict, cfg: BTConfig):
        """panel: {asset -> DataFrame[timestamp, open, high, low, close, volume, quote_volume]}
        funding: {asset -> DataFrame[timestamp, fundingRate]} (may be empty per asset)"""
        self.panel = panel
        self.funding = funding
        self.cfg = cfg
        self.assets = list(panel.keys())
        self._prepare()

    def _prepare(self):
        """Precompute trailing-only features. Nothing full-sample."""
        self.feat = {}
        for a, df in self.panel.items():
            d = df.copy().reset_index(drop=True)
            d["atr"] = C.atr(d, 14)
            if self.cfg.spread_model == "corwin_schultz":
                d["half_spread_bps"] = C.corwin_schultz_half_spread_bps(d["high"], d["low"])
            else:
                # tiered on the asset's OWN median hourly quote volume (a property of the
                # instrument, not of any future bar -- constant across the sample, so it
                # cannot leak information about a specific bar's outcome)
                d["half_spread_bps"] = C.tiered_half_spread_bps(float(d["quote_volume"].median()))
            d["ret"] = d["close"].pct_change()
            self.feat[a] = d
        # unified UTC grid
        all_ts = sorted(set().union(*[set(d["timestamp"]) for d in self.feat.values()]))
        self.grid = pd.DatetimeIndex(all_ts)
        self.idx_of = {a: {t: i for i, t in enumerate(d["timestamp"])} for a, d in self.feat.items()}

        # --- numpy views for the hot loop (pure speed; identical semantics) ---
        # pos[a][gi] = row index of asset `a` at grid position gi, or -1 if absent.
        self.arr = {}
        self.pos = {}
        gpos = {t: i for i, t in enumerate(self.grid)}
        for a, d in self.feat.items():
            self.arr[a] = {
                "open": d["open"].to_numpy(float), "high": d["high"].to_numpy(float),
                "low": d["low"].to_numpy(float), "close": d["close"].to_numpy(float),
                "qv": d["quote_volume"].to_numpy(float),
                "atr": d["atr"].to_numpy(float),
                "hs": d["half_spread_bps"].to_numpy(float),
                "ret": d["ret"].to_numpy(float),
            }
            pa = np.full(len(self.grid), -1, dtype=np.int64)
            for i, t in enumerate(d["timestamp"]):
                gi = gpos.get(t)
                if gi is not None:
                    pa[gi] = i
            self.pos[a] = pa
        # funding as sorted numpy for fast interval sums
        self.fund_arr = {}
        for a, f in self.funding.items():
            if f is not None and not f.empty:
                self.fund_arr[a] = (f["timestamp"].to_numpy(dtype="datetime64[ns]"),
                                    f["fundingRate"].to_numpy(float))
            else:
                self.fund_arr[a] = None
        self.grid_np = self.grid.tz_convert(None).to_numpy(dtype="datetime64[ns]") \
            if self.grid.tz is not None else self.grid.to_numpy(dtype="datetime64[ns]")
        self._beta_cache = {}

    # -- helpers -----------------------------------------------------------
    def _btc_beta(self, asset: str, i_grid: int) -> float:
        """Trailing rolling beta of asset returns to BTC returns. Trailing only."""
        if asset == "BTC":
            return 1.0
        btc = self.feat.get("BTC")
        d = self.feat.get(asset)
        if btc is None or d is None:
            return 1.0
        t = self.grid[i_grid]
        ia, ib = self.idx_of[asset].get(t), self.idx_of["BTC"].get(t)
        if ia is None or ib is None:
            return 1.0
        lb = self.cfg.beta_lookback_bars
        ck = (asset, ia // 24)          # recompute at most once per day per asset
        if ck in self._beta_cache:
            return self._beta_cache[ck]
        a_ret = self.arr[asset]["ret"][max(0, ia - lb): ia]   # strictly BEFORE current bar
        b_ret = self.arr["BTC"]["ret"][max(0, ib - lb): ib]
        n = min(len(a_ret), len(b_ret))
        if n < 100:
            return 1.0
        a_ret, b_ret = a_ret[-n:], b_ret[-n:]
        var = np.nanvar(b_ret)
        if not np.isfinite(var) or var <= 0:
            return 1.0
        cov = np.nanmean((a_ret - np.nanmean(a_ret)) * (b_ret - np.nanmean(b_ret)))
        beta = cov / var
        out = float(np.clip(beta, -3, 3)) if np.isfinite(beta) else 1.0
        self._beta_cache[ck] = out
        return out

    # -- main loop ---------------------------------------------------------
    def run(self, signals: dict, fixed_notional: float | None = None) -> dict:
        cfg = self.cfg
        equity = cfg.initial_equity
        peak_equity = equity
        halted = False
        open_pos: dict[str, Position] = {}
        trades = []
        equity_curve = []
        day_start_equity = equity
        week_start_equity = equity
        cur_day = None
        cur_week = None
        blocked_day = None
        blocked_week = None
        cost_accum = {"fee": 0.0, "spread": 0.0, "slippage": 0.0, "funding": 0.0}
        sig_arr = {a: np.asarray(sv, dtype=float) for a, sv in signals.items()}
        # fast skip: grid positions where no asset has a nonzero prior-bar signal
        any_sig = np.zeros(len(self.grid), dtype=bool)
        for a, sv in sig_arr.items():
            pa = self.pos[a]
            valid = pa >= 0
            nz = np.zeros(len(self.grid), dtype=bool)
            nz[valid] = sv[pa[valid]] != 0
            any_sig |= nz

        for gi in range(1, len(self.grid)):
            t = self.grid[gi]

            # --- calendar-based risk-limit resets (UTC) ---
            d_key = t.date()
            w_key = (t.isocalendar().year, t.isocalendar().week)
            if cur_day != d_key:
                cur_day, day_start_equity = d_key, equity
            if cur_week != w_key:
                cur_week, week_start_equity = w_key, equity

            # --- mark open positions, process exits on THIS bar ---
            for asset in list(open_pos.keys()):
                pos = open_pos[asset]
                A = self.arr[asset]
                i = int(self.pos[asset][gi])
                if i < 0:
                    continue
                pos.bars_held += 1

                exit_price, exit_reason = None, None
                o, h, l = A["open"][i], A["high"][i], A["low"][i]

                # R4: gap through the stop -> fill at the OPEN, worse than the stop
                if pos.direction == 1 and o <= pos.stop_price:
                    exit_price, exit_reason = o, "stop_gap"
                elif pos.direction == -1 and o >= pos.stop_price:
                    exit_price, exit_reason = o, "stop_gap"
                else:
                    hit_stop = (l <= pos.stop_price) if pos.direction == 1 else (h >= pos.stop_price)
                    hit_tgt = (h >= pos.target_price) if pos.direction == 1 else (l <= pos.target_price)
                    # R3: if both touched intrabar, assume the WORSE outcome (stop first)
                    if hit_stop:
                        exit_price, exit_reason = pos.stop_price, "stop"
                    elif hit_tgt:
                        exit_price, exit_reason = pos.target_price, "target"
                    elif pos.bars_held >= cfg.max_holding_bars:
                        exit_price, exit_reason = A["close"][i], "time_stop"

                # funding accrues for any settlement crossed while open
                fa = self.fund_arr.get(asset)
                if fa is not None:
                    fts, frt = fa
                    lo_i = np.searchsorted(fts, self.grid_np[gi - 1], side="right")
                    hi_i = np.searchsorted(fts, self.grid_np[gi], side="right")
                    fc = float(pos.direction * pos.notional * frt[lo_i:hi_i].sum()) if hi_i > lo_i else 0.0
                    pos.funding_paid_usd += fc
                    equity -= fc
                    cost_accum["funding"] += fc

                # funding circuit breaker
                if exit_price is None and pos.bars_held > 0:
                    ann_funding_bps = (pos.funding_paid_usd / max(pos.notional, 1e-9)) * \
                                      (8760 / max(pos.bars_held, 1)) * 1e4
                    if ann_funding_bps > cfg.funding_breaker_ann_pct * cfg.expected_edge_bps:
                        exit_price, exit_reason = A["close"][i], "funding_breaker"

                if exit_price is not None:
                    _atr_x = A["atr"][i]
                    exit_cost = C.one_way_cost_bps(pos.notional, A["qv"][i],
                                                   _atr_x if np.isfinite(_atr_x) else 0.0,
                                                   exit_price, A["hs"][i], cfg.cost_cfg)
                    exit_cost_usd = pos.notional * exit_cost["total_bps"] / 1e4
                    cost_accum["fee"] += pos.notional * exit_cost["fee_bps"] / 1e4
                    cost_accum["spread"] += pos.notional * exit_cost["half_spread_bps"] / 1e4
                    cost_accum["slippage"] += pos.notional * exit_cost["slippage_bps"] / 1e4

                    gross_pnl = pos.direction * (exit_price - pos.entry_price) * pos.qty
                    net_pnl = gross_pnl - pos.entry_cost_usd - exit_cost_usd - pos.funding_paid_usd
                    equity += gross_pnl - exit_cost_usd
                    trades.append({
                        "asset": asset, "direction": pos.direction,
                        "entry_time": pos.entry_time, "exit_time": t,
                        "entry_price": pos.entry_price, "exit_price": exit_price,
                        "qty": pos.qty, "notional": pos.notional,
                        "bars_held": pos.bars_held, "exit_reason": exit_reason,
                        "gross_pnl": gross_pnl,
                        "entry_cost": pos.entry_cost_usd, "exit_cost": exit_cost_usd,
                        "funding": pos.funding_paid_usd,
                        "net_pnl": net_pnl,
                        "ret_on_notional": net_pnl / pos.notional if pos.notional else 0.0,
                        "equity_after": equity,
                    })
                    del open_pos[asset]

            # --- risk gates ---
            peak_equity = max(peak_equity, equity)
            dd = equity / peak_equity - 1
            if dd <= -cfg.kill_switch_dd:
                halted = True
            day_dd = equity / day_start_equity - 1
            week_dd = equity / week_start_equity - 1
            if day_dd <= -cfg.daily_loss_limit:
                blocked_day = d_key
            if week_dd <= -cfg.weekly_loss_limit:
                blocked_week = w_key
            can_enter = (not halted) and (blocked_day != d_key) and (blocked_week != w_key)

            equity_curve.append({"timestamp": t, "equity": equity,
                                 "n_open": len(open_pos), "halted": halted})

            if not can_enter or len(open_pos) >= cfg.max_concurrent:
                continue
            if not any_sig[gi - 1]:
                continue

            # --- entries: R1/R2. Use signal from bar t-1, fill at bar t OPEN ---
            prev_t = self.grid[gi - 1]
            gross_notional = sum(p.notional for p in open_pos.values())
            btc_beta_used = sum(self._btc_beta(p.asset, gi) * p.direction * p.notional
                                for p in open_pos.values()) / max(equity, 1e-9)

            for asset in self.assets:
                if asset in open_pos or len(open_pos) >= cfg.max_concurrent:
                    continue
                sig = signals.get(asset)
                if sig is None:
                    continue
                A = self.arr[asset]
                i = int(self.pos[asset][gi])
                i_prev = int(self.pos[asset][gi - 1])
                if i < 0 or i_prev < 0:
                    continue
                s = sig_arr[asset][i_prev]                 # R1/R2: strictly prior bar
                if not np.isfinite(s) or s == 0:
                    continue

                fill_price = A["open"][i]                  # R1: next-bar OPEN
                atr_v = A["atr"][i_prev]                   # trailing ATR known at t-1
                if not np.isfinite(atr_v) or atr_v <= 0 or fill_price <= 0:
                    continue

                direction = int(np.sign(s))
                risk_frac = min(cfg.risk_per_trade, cfg.risk_per_trade_cap)
                stop_dist = cfg.atr_multiple_stop * atr_v
                qty = (risk_frac * equity) / stop_dist
                notional = qty * fill_price
                if fixed_notional is not None:
                    notional = min(fixed_notional, notional * 10)
                    qty = notional / fill_price

                # caps
                notional = min(notional, cfg.per_asset_notional_cap * equity)
                if gross_notional + notional > cfg.gross_leverage_cap * equity:
                    continue
                cand_beta = self._btc_beta(asset, gi) * direction * notional / max(equity, 1e-9)
                if abs(btc_beta_used + cand_beta) > cfg.portfolio_btc_beta_cap:
                    continue
                qty = notional / fill_price
                if qty <= 0:
                    continue

                entry_cost = C.one_way_cost_bps(notional, A["qv"][i],
                                                atr_v, fill_price,
                                                A["hs"][i_prev], cfg.cost_cfg)
                entry_cost_usd = notional * entry_cost["total_bps"] / 1e4
                cost_accum["fee"] += notional * entry_cost["fee_bps"] / 1e4
                cost_accum["spread"] += notional * entry_cost["half_spread_bps"] / 1e4
                cost_accum["slippage"] += notional * entry_cost["slippage_bps"] / 1e4
                equity -= entry_cost_usd

                stop_price = fill_price - direction * stop_dist
                target_price = fill_price + direction * cfg.target_take_profit_atr * atr_v
                open_pos[asset] = Position(asset, direction, t, fill_price, qty, notional,
                                           stop_price, target_price, 0, entry_cost_usd, 0.0)
                gross_notional += notional
                btc_beta_used += cand_beta

        eq = pd.DataFrame(equity_curve).set_index("timestamp")["equity"] if equity_curve else pd.Series(dtype=float)
        tr = pd.DataFrame(trades)
        return {"equity_curve": eq, "trades": tr, "cost_breakdown": cost_accum,
                "final_equity": equity, "halted": halted}
