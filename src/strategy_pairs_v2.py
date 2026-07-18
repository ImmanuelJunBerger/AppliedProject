"""Track A2: pooled pairs/cointegration trades.

Run 1 (`src/strategy_pairs.py`) found near-zero mean/median Sharpe across
cointegrated pairs but with only 1-3 trades per pair -- no statistical
power to say anything. This module reuses Run 1's exact walk-forward
Engle-Granger selection and trading rule unchanged, but records every
individual trade's P&L and pools them (across pairs, within and across
sectors) into one distribution big enough to actually test.
"""
from __future__ import annotations

import itertools
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

from . import engine, stats
from .strategy_momentum import load_universe_panel
from .strategy_pairs import SECTORS, TRAIN_DAYS, TEST_DAYS, ENTRY_Z, EXIT_Z, STOP_Z, COINT_PVAL, NOTIONAL_LEG_EUR


def _pooled_trades_one_pair(a: str, b: str, price_panel: pd.DataFrame, vol_panel: pd.DataFrame,
                             logp: pd.DataFrame, dates: pd.DatetimeIndex, sector: str) -> list[dict]:
    trades = []
    for train_dates, test_dates in engine.walk_forward_splits(dates, TRAIN_DAYS, TEST_DAYS, TEST_DAYS):
        train = logp.loc[logp.index.isin(train_dates), [a, b]].dropna()
        if len(train) < TRAIN_DAYS * 0.8:
            continue
        try:
            _, pval, _ = coint(train[a], train[b])
        except Exception:
            continue
        if pval >= COINT_PVAL:
            continue
        beta, alpha = np.polyfit(train[b], train[a], 1)
        spread_train = train[a] - (alpha + beta * train[b])
        mu, sigma = spread_train.mean(), spread_train.std()
        if sigma == 0 or np.isnan(sigma):
            continue

        test_idx = logp.index[(logp.index >= test_dates[0]) & (logp.index <= test_dates[-1])]
        pos = 0
        entry_date = None
        entry_equity = None
        running_pnl = 0.0
        prev_d = None
        for d in test_idx:
            if d not in logp.index:
                continue
            pa, pb = logp.loc[d, a], logp.loc[d, b]
            if pd.isna(pa) or pd.isna(pb):
                continue
            z = (pa - (alpha + beta * pb) - mu) / sigma
            new_pos = pos
            if pos == 0:
                if z > ENTRY_Z:
                    new_pos = -1
                elif z < -ENTRY_Z:
                    new_pos = 1
            else:
                if abs(z) < EXIT_Z or abs(z) > STOP_Z:
                    new_pos = 0
            if prev_d is not None and pos != 0:
                d_spread = (pa - beta * pb) - (logp.loc[prev_d, a] - beta * logp.loc[prev_d, b])
                running_pnl += pos * d_spread * NOTIONAL_LEG_EUR
            if new_pos != pos:
                adv_a = float(vol_panel[a].reindex([d]).iloc[0]) if a in vol_panel.columns and d in vol_panel.index else None
                adv_b = float(vol_panel[b].reindex([d]).iloc[0]) if b in vol_panel.columns and d in vol_panel.index else None
                cost = (engine.trade_cost_eur(a, NOTIONAL_LEG_EUR, "spot", adv_a) +
                        engine.trade_cost_eur(b, NOTIONAL_LEG_EUR, "spot", adv_b))
                if pos == 0 and new_pos != 0:
                    entry_date = d
                    running_pnl = -cost
                elif pos != 0 and new_pos == 0:
                    running_pnl -= cost
                    trades.append({
                        "pair": f"{a}/{b}", "sector": sector, "entry_date": entry_date, "exit_date": d,
                        "pnl_eur": running_pnl, "return_frac": running_pnl / (2 * NOTIONAL_LEG_EUR),
                        "direction": pos,
                    })
                    running_pnl = 0.0
                    entry_date = None
                elif pos != 0 and new_pos != 0 and new_pos != pos:
                    # direct flip: close then reopen same bar
                    running_pnl -= cost
                    trades.append({
                        "pair": f"{a}/{b}", "sector": sector, "entry_date": entry_date, "exit_date": d,
                        "pnl_eur": running_pnl, "return_frac": running_pnl / (2 * NOTIONAL_LEG_EUR),
                        "direction": pos,
                    })
                    entry_date = d
                    running_pnl = -cost
                pos = new_pos
            prev_d = d
    return trades


def run_pooled() -> dict:
    price_panel, vol_panel, _ = load_universe_panel()
    train_dates, holdout_dates = stats.train_holdout_split(price_panel.index, 0.3)
    holdout_start = train_dates.max()

    all_trades = []
    for sector, syms in SECTORS.items():
        avail = [s for s in syms if s in price_panel.columns]
        logp = np.log(price_panel[avail])
        dates = logp.dropna(how="all").index
        for a, b in itertools.combinations(avail, 2):
            all_trades.extend(_pooled_trades_one_pair(a, b, price_panel, vol_panel, logp, dates, sector))

    df = pd.DataFrame(all_trades)
    df.to_csv("results/pairs_pooled_trades.csv", index=False)
    if df.empty:
        return {"error": "no trades", "n_trades": 0}

    df["entry_date"] = pd.to_datetime(df["entry_date"])
    is_trades = df[df["entry_date"] <= holdout_start]
    ho_trades = df[df["entry_date"] > holdout_start]

    def _stats_block(sub: pd.DataFrame) -> dict:
        if len(sub) < 2:
            return {"n_trades": len(sub), "error": "too few trades"}
        rets = sub["return_frac"].values
        sharpe = float(rets.mean() / rets.std(ddof=1) * np.sqrt(252 / 30)) if rets.std(ddof=1) > 0 else 0.0  # rough trade-freq annualization
        p = stats.one_sided_pvalue(rets)
        return {"n_trades": len(sub), "mean_return_frac": round(float(rets.mean()), 5),
                "win_rate_pct": round(100 * float((rets > 0).mean()), 1),
                "sharpe_rough_annualized": round(sharpe, 2), "p_value": round(p, 5),
                "total_pnl_eur": round(float(sub["pnl_eur"].sum()), 2)}

    overall = {"all": _stats_block(df), "in_sample": _stats_block(is_trades), "holdout": _stats_block(ho_trades)}
    for sector in SECTORS:
        overall[f"sector_{sector}"] = _stats_block(df[df["sector"] == sector])

    # robustness: drop single best pair, drop single best month
    if len(df) >= 5:
        best_pair = df.groupby("pair")["pnl_eur"].sum().idxmax()
        without_best_pair = df[df["pair"] != best_pair]
        overall["ex_best_pair"] = {"dropped": best_pair, **_stats_block(without_best_pair)}

        df["month"] = df["entry_date"].dt.to_period("M")
        best_month = df.groupby("month")["pnl_eur"].sum().idxmax()
        without_best_month = df[df["month"] != best_month]
        overall["ex_best_month"] = {"dropped": str(best_month), **_stats_block(without_best_month)}

    dsr = stats.deflated_sharpe_ratio(is_trades["return_frac"].values, n_trials=4) if len(is_trades) >= 10 else {"error": "insufficient"}
    overall["deflated_sharpe_is"] = dsr

    stats.register_test("A2_pairs_pooled_all", "A2_pairs_pooled", "all_sectors_pooled", "none (stat-arb, thin edge expected)",
                         len(df), sharpe_is=overall["in_sample"].get("sharpe_rough_annualized"),
                         p_is=overall["in_sample"].get("p_value"),
                         sharpe_holdout=overall["holdout"].get("sharpe_rough_annualized"),
                         p_holdout=overall["holdout"].get("p_value"))
    for sector in SECTORS:
        blk = overall[f"sector_{sector}"]
        stats.register_test(f"A2_pairs_pooled_{sector}", "A2_pairs_pooled", f"sector={sector}", "none",
                             blk.get("n_trades"), sharpe_is=blk.get("sharpe_rough_annualized"), p_is=blk.get("p_value"))

    return overall


if __name__ == "__main__":
    import json
    print(json.dumps(run_pooled(), indent=2, default=str))
