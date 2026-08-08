"""Aligned point-in-time panel + fast vectorised evaluator for the Tier-1 screen.

POINT-IN-TIME BY CONSTRUCTION: every field is a (time x asset) DataFrame where an
asset is NaN before it listed and NaN after it delisted. Signals built on these
frames therefore cannot trade an asset that did not exist, and delisted assets
(LUNA, SRM, BZRX, ...) contribute their real collapse and then vanish -- which is
exactly what survivorship-free means here.

NO LOOKAHEAD: `evaluate()` shifts the weight matrix by one bar before applying it
to returns, so a weight decided from bar-t information is only ever paid bar-t+1's
return. Every helper in this module uses trailing windows only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BARS_PER_YEAR = 24 * 365

# Pessimistic round-trip cost tiers (bps) by median hourly quote volume.
# = 2 x (taker 4.5 + half-spread + slippage floor 2.0) x 2.5 pessimistic multiplier,
# consistent with the Run-6 cost model that was independently unit-tested.
def rt_cost_bps_pessimistic(median_qv: float) -> float:
    if median_qv >= 1e8:
        hs = 0.5
    elif median_qv >= 2e7:
        hs = 1.0
    elif median_qv >= 5e6:
        hs = 2.0
    else:
        hs = 4.0
    return 2 * (4.5 + hs + 2.0) * 2.5


def rt_cost_bps_level(median_qv: float, mult: float) -> float:
    if median_qv >= 1e8:
        hs = 0.5
    elif median_qv >= 2e7:
        hs = 1.0
    elif median_qv >= 5e6:
        hs = 2.0
    else:
        hs = 4.0
    return 2 * (4.5 + hs + 2.0) * mult


class Panel:
    def __init__(self, fields: dict, cost_bps: pd.Series):
        self.f = fields                    # name -> DataFrame(time x asset)
        self.cost_bps = cost_bps           # asset -> pessimistic round-trip bps
        self.index = fields["close"].index
        self.assets = list(fields["close"].columns)

    @property
    def close(self): return self.f["close"]
    @property
    def open(self): return self.f["open"]
    @property
    def ret(self): return self.f["ret"]

    def sub(self, t0, t1) -> "Panel":
        m = (self.index >= t0) & (self.index < t1)
        return Panel({k: v.loc[m] for k, v in self.f.items()}, self.cost_bps)


# Canonical full-span cache keys. Sub-periods are sliced from these in memory --
# never re-fetched with a different date range, which would miss the cache entirely.
FULL_START = pd.Timestamp("2021-01-01", tz="UTC")
FULL_END = pd.Timestamp("2026-08-01", tz="UTC")


def build_panel(symbols: list[str], start=None, end=None, need_metrics: bool = True,
                metrics_symbols: list[str] | None = None) -> Panel:
    """Always loads the FULL cached span, then slices to [start, end).

    `metrics_symbols` is an explicit allowlist for the OI/positioning join. Without
    it, build_panel would try to fetch ~2,000 daily metric files for every symbol
    that has none cached -- so this is an allowlist, not "whatever happens to be
    cached".
    """
    from . import data_binance as db
    start = FULL_START if start is None else start
    end = FULL_END if end is None else end
    mset = set(metrics_symbols or [])
    close, openp, high, low, qv, fund = {}, {}, {}, {}, {}, {}
    oi, tt_ratio, acct_ratio, taker_ratio = {}, {}, {}, {}
    for s in symbols:
        k = db.fetch_klines_1h(s, FULL_START, FULL_END)
        if k.empty or len(k) < 24 * 60:
            continue
        k = k.set_index("timestamp")
        close[s] = k["close"]; openp[s] = k["open"]; high[s] = k["high"]
        low[s] = k["low"]; qv[s] = k["quote_volume"]
        f = db.fetch_funding(s, FULL_START, FULL_END)
        if not f.empty:
            fund[s] = f.set_index("timestamp")["fundingRate"]
        if need_metrics and s in mset:
            m = db.fetch_metrics_1h(s, FULL_START, FULL_END)
            if not m.empty:
                m = m.set_index("timestamp")
                oi[s] = m["sum_open_interest_value"]
                tt_ratio[s] = m["sum_toptrader_long_short_ratio"]
                acct_ratio[s] = m["count_long_short_ratio"]
                taker_ratio[s] = m["sum_taker_long_short_vol_ratio"]

    C = pd.DataFrame(close).sort_index()
    idx = C.index
    def align(d):
        return pd.DataFrame(d).reindex(idx) if d else pd.DataFrame(index=idx)
    fields = {
        "close": C, "open": align(openp), "high": align(high), "low": align(low),
        "qv": align(qv),
        # funding prints every 8h -> forward-fill the LAST KNOWN rate (never a future one)
        "funding": align(fund).ffill(),
        "oi": align(oi), "tt_ratio": align(tt_ratio),
        "acct_ratio": align(acct_ratio), "taker_ratio": align(taker_ratio),
    }
    fields["ret"] = C.pct_change()
    med_qv = fields["qv"].median()
    cost = med_qv.apply(rt_cost_bps_pessimistic)
    pan = Panel(fields, cost)
    return pan.sub(start, end)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def normalize_weights(W: pd.DataFrame, gross: float = 1.0) -> pd.DataFrame:
    """Scale each row to a fixed gross exposure so different signals are comparable."""
    s = W.abs().sum(axis=1).replace(0, np.nan)
    return (W.div(s, axis=0) * gross).fillna(0.0)


def evaluate(W: pd.DataFrame, panel: Panel, cost_mult: float = 2.5,
             min_trades: int = 0) -> dict:
    """Vectorised portfolio P&L.

    W[t] is the target weight decided using information available AT bar t.
    It is shifted one bar before earning returns, so it can only ever be paid
    bar t+1's return -- the vectorised equivalent of next-bar-open execution.
    """
    W = W.reindex(panel.index).fillna(0.0)
    W = W.where(panel.close.notna(), 0.0)          # cannot hold a non-existent asset
    Wl = W.shift(1).fillna(0.0)

    ret = panel.ret.reindex(panel.index).fillna(0.0)
    gross_ret = (Wl * ret).sum(axis=1)

    turnover = (W - Wl).abs()
    cost_frac = pd.Series(
        {a: rt_cost_bps_level(panel.f["qv"][a].median(), cost_mult) / 2 / 1e4
         for a in W.columns})                       # one-way = half of round trip
    cost_ret = (turnover * cost_frac).sum(axis=1)
    net_ret = gross_ret - cost_ret

    # a "trade" = an asset going from flat to non-flat
    entries = ((Wl == 0) & (W != 0)).sum().sum()
    n_bars = len(net_ret)
    gross_bps = float(gross_ret.mean()) * 1e4
    net_bps = float(net_ret.mean()) * 1e4
    sd = net_ret.std(ddof=1)
    sharpe = float(net_ret.mean() / sd * np.sqrt(BARS_PER_YEAR)) if sd > 0 else 0.0
    gsd = gross_ret.std(ddof=1)
    gsharpe = float(gross_ret.mean() / gsd * np.sqrt(BARS_PER_YEAR)) if gsd > 0 else 0.0
    eq = (1 + net_ret).cumprod()
    dd = float((eq / eq.cummax() - 1).min()) if len(eq) else 0.0
    return {"n_trades": int(entries), "n_bars": int(n_bars),
            "gross_bps_per_bar": round(gross_bps, 4),
            "net_bps_per_bar": round(net_bps, 4),
            "sharpe_net": round(sharpe, 3), "sharpe_gross": round(gsharpe, 3),
            "max_dd_pct": round(dd * 100, 2),
            "total_net_return_pct": round(float(eq.iloc[-1] - 1) * 100, 2) if len(eq) else 0.0,
            "avg_turnover_per_bar": round(float(turnover.sum(axis=1).mean()), 5),
            "net_returns": net_ret}


def regime_split(net_ret: pd.Series, btc_close: pd.Series) -> dict:
    """Trailing-only bull/bear/chop labels from BTC, then expectancy per regime."""
    trend = btc_close.pct_change(24 * 30).reindex(net_ret.index)
    lab = pd.Series(np.where(trend > 0.10, "bull", np.where(trend < -0.10, "bear", "chop")),
                    index=net_ret.index)
    out = {}
    for r in ("bull", "bear", "chop"):
        v = net_ret[lab == r]
        out[r] = round(float(v.mean()) * 1e4, 3) if len(v) > 50 else None
    out["n_positive_regimes"] = sum(1 for r in ("bull", "bear", "chop")
                                    if out.get(r) is not None and out[r] > 0)
    return out
