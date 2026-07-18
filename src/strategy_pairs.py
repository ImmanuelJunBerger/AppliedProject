"""Strategy 4: pairs / cointegration stat-arb.

Same price panel and same universe-construction caveat as strategies 2-3.

Method: within each sector bucket, walk-forward over rolling
train(180d)/test(60d) windows, for every pair within the sector. In each
fold: run Engle-Granger cointegration (statsmodels `coint`) on log prices
using ONLY the train window; if p-value < 0.05, fit the OLS hedge ratio and
the spread's mean/std on the SAME train window, then trade the z-scored
spread in the test window using those train-fitted parameters (walk-forward
discipline -- a pair that only cointegrates in-sample, or whose hedge ratio
is fit on the test window itself, is exactly the trap the task warns about).
A pair sits flat (no position, no cost) during any fold where it fails the
cointegration test that fold.

Enter at |z|>2, exit at |z|<0.5, hard stop at |z|>4 (spread has diverged,
cut losses rather than assume reversion).

Each pair gets its own independent 1,000 EUR equity curve across the full
date range (flat during non-cointegrated folds). Sector-level results report
the full distribution across pairs (mean/median/best/worst Sharpe), not just
the best pair -- picking only the best pair after the fact would itself be a
form of the overfitting the task explicitly prohibits.
"""
from __future__ import annotations

import itertools
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

from . import engine
from .strategy_momentum import load_universe_panel

SECTORS = {
    "L1": ["ETHUSDT", "SOLUSDT", "ADAUSDT", "NEARUSDT", "AVAXUSDT", "TONUSDT", "DOTUSDT", "TRXUSDT", "SUIUSDT"],
    "DeFi": ["UNIUSDT", "AAVEUSDT", "LDOUSDT", "LINKUSDT", "ENAUSDT", "DODOUSDT"],
    "Meme": ["PEPEUSDT", "BONKUSDT", "DOGEUSDT", "PENGUUSDT"],
}

TRAIN_DAYS = 180
TEST_DAYS = 60
ENTRY_Z = 2.0
EXIT_Z = 0.5
STOP_Z = 4.0
COINT_PVAL = 0.05
NOTIONAL_LEG_EUR = engine.CAPITAL_EUR / 2


def _backtest_one_pair(a: str, b: str, price_panel: pd.DataFrame, vol_panel: pd.DataFrame,
                        logp: pd.DataFrame, dates: pd.DatetimeIndex) -> tuple[pd.Series, int, int]:
    """Full-history equity curve for pair (a,b): flat except in folds where the
    train window cointegrates; trades the z-scored spread in the test window
    using train-fitted (alpha, beta, mu, sigma). Returns (equity, n_trades, n_tradeable_folds)."""
    equity_val = engine.CAPITAL_EUR
    equity = {dates[0]: equity_val}
    n_trades = 0
    n_tradeable_folds = 0
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
        n_tradeable_folds += 1
        beta, alpha = np.polyfit(train[b], train[a], 1)
        spread_train = train[a] - (alpha + beta * train[b])
        mu, sigma = spread_train.mean(), spread_train.std()
        if sigma == 0 or np.isnan(sigma):
            continue

        test_idx = logp.index[(logp.index >= test_dates[0]) & (logp.index <= test_dates[-1])]
        pos = 0
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
                equity_val += pos * d_spread * NOTIONAL_LEG_EUR
            if new_pos != pos:
                adv_a = float(vol_panel[a].reindex([d]).iloc[0]) if a in vol_panel.columns and d in vol_panel.index else None
                adv_b = float(vol_panel[b].reindex([d]).iloc[0]) if b in vol_panel.columns and d in vol_panel.index else None
                cost = (engine.trade_cost_eur(a, NOTIONAL_LEG_EUR, "spot", adv_a) +
                        engine.trade_cost_eur(b, NOTIONAL_LEG_EUR, "spot", adv_b))
                equity_val -= cost
                n_trades += 1
                pos = new_pos
            equity[d] = equity_val
            prev_d = d
    eq = pd.Series(equity).sort_index()
    eq = eq.reindex(dates).ffill().fillna(engine.CAPITAL_EUR)
    return eq, n_trades, n_tradeable_folds


def find_pairs_and_backtest(price_panel: pd.DataFrame, vol_panel: pd.DataFrame, symbols: list[str]) -> dict:
    avail = [s for s in symbols if s in price_panel.columns]
    logp = np.log(price_panel[avail])
    dates = logp.dropna(how="all").index

    per_pair = []
    for a, b in itertools.combinations(avail, 2):
        eq, n_trades, n_folds = _backtest_one_pair(a, b, price_panel, vol_panel, logp, dates)
        if n_folds == 0:
            continue
        m = engine.compute_metrics(eq, 365, trade_count=n_trades)
        per_pair.append({"pair": f"{a}/{b}", "tradeable_folds": n_folds, **m})

    n_pairs_total = len(list(itertools.combinations(avail, 2)))
    if not per_pair:
        return {"n_pairs_total": n_pairs_total, "n_pairs_ever_cointegrated": 0,
                "verdict": "no pair cointegrated in any walk-forward fold"}

    df = pd.DataFrame(per_pair).sort_values("sharpe_annualized", ascending=False)
    df.to_csv(f"results/pairs_{'_'.join(symbols[:1])}_per_pair.csv", index=False)
    best = df.iloc[0].to_dict()
    return {
        "n_pairs_total": n_pairs_total,
        "n_pairs_ever_cointegrated": len(df),
        "mean_sharpe_across_cointegrated_pairs": round(float(df["sharpe_annualized"].mean()), 2),
        "median_sharpe_across_cointegrated_pairs": round(float(df["sharpe_annualized"].median()), 2),
        "pct_pairs_with_positive_net_pnl": round(100 * float((df["net_profit_eur_on_1000"] > 0).mean()), 1),
        "best_pair": best,
        "worst_pair": df.iloc[-1].to_dict(),
        "all_pairs_csv": f"results/pairs_{symbols[0]}_per_pair.csv",
    }


def run_all() -> dict:
    price_panel, vol_panel, _ = load_universe_panel()
    out = {}
    for sector, syms in SECTORS.items():
        out[sector] = find_pairs_and_backtest(price_panel, vol_panel, syms)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=2, default=str))
