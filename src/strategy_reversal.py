"""Strategy 3: short-horizon reversal.

Same universe and same look-ahead/survivorship caveat as strategy 2
(see strategy_momentum.py docstring) -- current top-50-by-volume applied
retroactively.

Rule: each day, rank by trailing L-day return (L in 1/2/3), go long the
biggest losers (bottom quintile) and short the biggest winners (top
quintile), equal-weighted, hold 1 day, rebalance daily. Daily rebalancing
means turnover -- and cost drag -- is much higher than the weekly momentum
strategy; this is the whole point of the test (reversal is a known crypto
effect that often does not survive fees).
"""
from __future__ import annotations

import pandas as pd

from . import data, engine
from .strategy_momentum import load_universe_panel

LOOKBACKS = [1, 2, 3]
DECILE_FRAC = 0.2


def backtest_reversal(price_panel: pd.DataFrame, vol_panel: pd.DataFrame, lookback: int) -> tuple[pd.Series, pd.Series, int, float]:
    trailing_ret = price_panel.pct_change(lookback)
    daily_rets = price_panel.pct_change()
    daily_index = price_panel.index

    gross_equity = [engine.CAPITAL_EUR]
    net_equity = [engine.CAPITAL_EUR]
    dates_out = [daily_index[0]]
    current_weights = pd.Series(dtype=float)
    trades = 0
    turnover = 0.0

    for i in range(1, len(daily_index)):
        d = daily_index[i]
        prev_d = daily_index[i - 1]
        if prev_d in trailing_ret.index:
            sig = trailing_ret.loc[prev_d].dropna()
            sig = sig[price_panel.loc[prev_d, sig.index].notna()]
            n = len(sig)
            if n >= 10:
                k = max(1, int(n * DECILE_FRAC))
                ranked = sig.sort_values(ascending=True)  # biggest losers first
                losers = ranked.index[:k]
                winners = ranked.index[-k:]
                w = pd.Series(0.0, index=sig.index)
                w.loc[losers] = 1.0 / k
                w.loc[winners] = -1.0 / k
                new_weights = w
            else:
                new_weights = current_weights
        else:
            new_weights = current_weights

        day_ret = daily_rets.loc[d]
        port_ret = float((current_weights.reindex(day_ret.index).fillna(0) * day_ret.fillna(0)).sum())
        g = gross_equity[-1] * (1 + port_ret)
        n_e = net_equity[-1] * (1 + port_ret)

        if not new_weights.equals(current_weights):
            all_syms = set(new_weights.index) | set(current_weights.index)
            cost_frac = 0.0
            traded_notional = 0.0
            for sym in all_syms:
                dw = abs(new_weights.get(sym, 0.0) - current_weights.get(sym, 0.0))
                if dw < 1e-9:
                    continue
                notional = dw * n_e
                traded_notional += notional
                adv = float(vol_panel[sym].reindex([prev_d]).iloc[0]) if sym in vol_panel.columns and prev_d in vol_panel.index else None
                cost_frac += engine.trade_cost_eur(sym, notional, "spot", adv)
            if traded_notional > 1e-6:
                n_e -= cost_frac
                trades += 1
                turnover += traded_notional
            current_weights = new_weights

        gross_equity.append(g)
        net_equity.append(n_e)
        dates_out.append(d)

    return (pd.Series(gross_equity, index=dates_out), pd.Series(net_equity, index=dates_out), trades, turnover)


def run_all() -> dict:
    price_panel, vol_panel, _ = load_universe_panel()
    results = {}
    for lb in LOOKBACKS:
        gross, net, trades, turnover = backtest_reversal(price_panel, vol_panel, lb)
        m_gross = engine.compute_metrics(gross, 365, trades, turnover)
        m_net = engine.compute_metrics(net, 365, trades, turnover)
        results[f"lookback{lb}d"] = {"gross": m_gross, "net": m_net}
        net.to_frame("equity_eur").to_csv(f"results/reversal_{lb}d_net_equity.csv")
        gross.to_frame("equity_eur").to_csv(f"results/reversal_{lb}d_gross_equity.csv")
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=2, default=str))
