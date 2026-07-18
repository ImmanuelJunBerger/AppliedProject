"""Strategy 2: cross-sectional momentum.

Universe: today's top-50 USDT spot pairs by volume on Binance (via the
data-api.binance.vision mirror), non-crypto bases filtered out.

**Known bias, disclosed up front**: the universe is CURRENT top-50-by-volume
applied retroactively across the whole backtest window. This is a form of
look-ahead / survivorship bias -- we would not have known in the past which
tokens would be today's volume leaders. Tokens that pumped into today's top
50 are overrepresented; tokens that were liquid historically but faded (or
delisted) are absent entirely. Results are biased upward and that bias is
NOT correctable with the free data available here. Flagged, not hidden.

Rule: rank by trailing K-day return (K in 7/14/30), long top decile / short
bottom decile, equal-weighted, rebalance weekly, execute at next-day open
(signal formed at a day's close is not tradeable until the next session).
Both long-short and long-only-vs-cash variants reported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data, engine

LOOKBACKS = [7, 14, 30]
REBAL_FREQ_DAYS = 7
DECILE_FRAC = 0.2  # with 50 names, quintile (10 names/side) gives more trades than true decile


def load_universe_panel(n_symbols: int = 50, days: int = 750) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    symbols = data.top_usdt_pairs_by_volume(n_symbols)
    closes = {}
    vols = {}
    coverage = {}
    for sym in symbols:
        try:
            df = data.fetch_binance_spot_klines(sym, "1d", days)
        except Exception as e:  # noqa: BLE001
            coverage[sym] = f"fetch_error:{e}"
            continue
        if df.empty:
            coverage[sym] = "empty"
            continue
        s = df.set_index("timestamp")["close"]
        v = df.set_index("timestamp")["quote_volume"]
        closes[sym] = s
        vols[sym] = v
        coverage[sym] = {"n_days": len(df), "first": str(df["timestamp"].min()), "last": str(df["timestamp"].max())}
    price_panel = pd.DataFrame(closes).sort_index()
    vol_panel = pd.DataFrame(vols).sort_index()
    return price_panel, vol_panel, coverage


def _rebalance_dates(index: pd.DatetimeIndex, freq_days: int) -> list:
    return list(index[::freq_days])


def backtest_cross_sectional(price_panel: pd.DataFrame, vol_panel: pd.DataFrame,
                              lookback: int, allow_short: bool) -> tuple[pd.Series, pd.Series, int, float]:
    """Returns (gross_equity, net_equity, trade_count, turnover_eur)."""
    rets_fwd = price_panel.pct_change().shift(-1)  # not used directly; costs computed on rebalance
    trailing_ret = price_panel.pct_change(lookback)
    rebal_dates = _rebalance_dates(price_panel.index, REBAL_FREQ_DAYS)

    gross_equity = [engine.CAPITAL_EUR]
    net_equity = [engine.CAPITAL_EUR]
    dates_out = [price_panel.index[0]]
    prev_weights = pd.Series(dtype=float)
    trades = 0
    turnover = 0.0

    daily_index = price_panel.index
    daily_rets = price_panel.pct_change()

    current_weights = pd.Series(dtype=float)
    for i in range(1, len(daily_index)):
        d = daily_index[i]
        # rebalance decision made using data available at previous close (d-1),
        # executed on this day's return (i.e. applied starting this bar) -> no lookahead
        if d in rebal_dates and (daily_index[i - 1] in trailing_ret.index):
            sig = trailing_ret.loc[daily_index[i - 1]].dropna()
            avail = sig.index[price_panel.loc[daily_index[i - 1], sig.index].notna()]
            sig = sig.loc[avail]
            n = len(sig)
            if n >= 10:
                k = max(1, int(n * DECILE_FRAC))
                ranked = sig.sort_values(ascending=False)
                longs = ranked.index[:k]
                shorts = ranked.index[-k:] if allow_short else []
                w = pd.Series(0.0, index=sig.index)
                w.loc[longs] = 1.0 / k
                if allow_short:
                    w.loc[shorts] = -1.0 / k
                new_weights = w
            else:
                new_weights = current_weights
        else:
            new_weights = current_weights

        # apply today's return using YESTERDAY's weights (positions held into today)
        day_ret = daily_rets.loc[d]
        port_ret = float((current_weights.reindex(day_ret.index).fillna(0) * day_ret.fillna(0)).sum())
        g = gross_equity[-1] * (1 + port_ret)
        n_e = net_equity[-1] * (1 + port_ret)

        if not new_weights.equals(current_weights):
            all_syms = set(new_weights.index) | set(current_weights.index)
            turnover_frac = sum(abs(new_weights.reindex(all_syms).fillna(0) - current_weights.reindex(all_syms).fillna(0)))
            traded_notional = turnover_frac * n_e
            if traded_notional > 1e-6:
                cost_frac = 0.0
                for sym in all_syms:
                    dw = abs(new_weights.get(sym, 0.0) - current_weights.get(sym, 0.0))
                    if dw < 1e-9:
                        continue
                    notional = dw * n_e
                    adv = float(vol_panel[sym].reindex([daily_index[i - 1]]).iloc[0]) if sym in vol_panel.columns else None
                    cost = engine.trade_cost_eur(sym, notional, "spot", adv)
                    cost_frac += cost
                n_e -= cost_frac
                trades += 1
                turnover += traded_notional
            current_weights = new_weights

        gross_equity.append(g)
        net_equity.append(n_e)
        dates_out.append(d)

    return (pd.Series(gross_equity, index=dates_out),
            pd.Series(net_equity, index=dates_out), trades, turnover)


def run_all() -> dict:
    price_panel, vol_panel, coverage = load_universe_panel()
    n_syms = price_panel.shape[1]
    full_hist = (price_panel.notna().sum() >= 0.9 * len(price_panel)).sum()
    results = {"universe_size": n_syms,
               "symbols_with_near_full_history": int(full_hist),
               "backtest_span": [str(price_panel.index.min()), str(price_panel.index.max())]}
    for lb in LOOKBACKS:
        for allow_short in (True, False):
            gross, net, trades, turnover = backtest_cross_sectional(price_panel, vol_panel, lb, allow_short)
            periods_per_year = 365
            m_gross = engine.compute_metrics(gross, periods_per_year, trades, turnover)
            m_net = engine.compute_metrics(net, periods_per_year, trades, turnover)
            key = f"lookback{lb}d_{'longshort' if allow_short else 'longonly'}"
            results[key] = {"gross": m_gross, "net": m_net}
            tag = f"{lb}_{'ls' if allow_short else 'lo'}"
            net.to_frame("equity_eur").to_csv(f"results/momentum_{tag}_net_equity.csv")
            gross.to_frame("equity_eur").to_csv(f"results/momentum_{tag}_gross_equity.csv")
    return results


if __name__ == "__main__":
    import json
    out = run_all()
    print(json.dumps(out, indent=2, default=str))
