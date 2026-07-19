"""Portfolio construction from Run 5's surviving strategy candidates.

Strict survivors (positive Sharpe in-sample AND holdout, cleared BH-FDR
q=0.10 against the full N_TESTS pool, >=100 events or >=10yr daily,
structural reason stated): S2 IXIC overnight, S4 turn-of-month (N4=M4).
S8 (vol risk premium) is included as a flagged, tail-risk-heavy candidate:
it clears every element of the evidence bar except strict BH-FDR (raw
p=0.029 in holdout, just above the q=0.10 threshold rank cutoff at
p=0.0238) -- included with its skew/drawdown risk carried forward
explicitly, not smoothed into a single Sharpe number. S1 (trend, best case
gold lb126) is a near-miss (holdout p=0.0595, fails BH) -- shown ONLY in a
separate sensitivity table, never in the primary portfolio, exactly so a
reader can see what including a non-qualifying candidate would have done
without us pretending it qualifies.

No mean-variance optimization (would overfit the correlation matrix at this
sample size, per the task's own instruction). Equal-weight, inverse-vol,
and simple risk parity only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data_tradfi as dt

VOL_TARGET_ANN = 0.08  # ASSUMPTION: comparable to realized 60/40 stock/bond vol; a moderate,
                        # stated target for a supplementary diversifying multi-strategy book.


def _tz_naive(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    idx = pd.to_datetime(idx)
    return idx.tz_localize(None) if idx.tz is not None else idx


def _to_monthly(daily_ret: pd.Series) -> pd.Series:
    daily_ret = daily_ret.copy()
    daily_ret.index = _tz_naive(daily_ret.index)
    return (1 + daily_ret).resample("ME").prod() - 1


def load_candidate_returns() -> dict:
    out = {}

    s2 = pd.read_csv("results/s2_overnight_IXIC_overnight_net_returns.csv", index_col=0, parse_dates=True)["ret"]
    out["S2_overnight_IXIC"] = _to_monthly(s2)

    s4 = pd.read_csv("results/s4_tom_N4_M4_events.csv", parse_dates=["date"]).set_index("date")["ret_net"]
    s4.index = _tz_naive(s4.index).to_period("M").to_timestamp("M")
    s4 = s4.groupby(s4.index).sum()  # in the rare case >1 event lands in the same period (shouldn't happen, defensive)
    out["S4_turn_of_month"] = s4

    s8 = pd.read_csv("results/s8_volpremium_PUT_net_returns.csv", index_col=0, parse_dates=True)["ret"]
    out["S8_vol_premium"] = _to_monthly(s8)

    # sensitivity-only candidate, NOT in the primary portfolio (see module docstring)
    s1 = pd.read_csv("results/s1_tsmom_GC_lb126_net_returns.csv", index_col=0, parse_dates=True)["ret"]
    out["S1_trend_GC_SENSITIVITY_ONLY"] = _to_monthly(s1)

    return out


def load_french_reference() -> pd.DataFrame:
    f = pd.read_csv("results/s7_french_factors_reference.csv", parse_dates=["date"])
    f = f.set_index("date")
    f.index = _tz_naive(f.index)
    monthly = {}
    for col in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]:
        monthly[col] = (1 + f[col]).resample("ME").prod() - 1
    return pd.DataFrame(monthly)


def correlation_matrix(returns: dict, french_ref: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(returns)
    combined = df.join(french_ref, how="left")
    return combined.corr(min_periods=24)


def _ann_stats(monthly_ret: pd.Series) -> dict:
    monthly_ret = monthly_ret.dropna()
    if len(monthly_ret) < 12:
        return {"error": "insufficient data"}
    mean, std = monthly_ret.mean(), monthly_ret.std(ddof=1)
    sharpe = float(mean / std * np.sqrt(12)) if std > 0 else 0.0
    # Sharpe CI via Lo (2002) / Jobson-Korkie approx: SE(SR) ~ sqrt((1+0.5*SR^2)/T)
    T = len(monthly_ret)
    se = np.sqrt((1 + 0.5 * sharpe ** 2) / T)
    ci_lo, ci_hi = sharpe - 1.96 * se, sharpe + 1.96 * se
    equity = (1 + monthly_ret).cumprod()
    running_max = equity.cummax()
    dd = equity / running_max - 1
    max_dd = float(dd.min())
    underwater = dd < 0
    longest_underwater = 0
    current = 0
    for v in underwater:
        current = current + 1 if v else 0
        longest_underwater = max(longest_underwater, current)
    return {"sharpe_ann": round(sharpe, 3), "sharpe_ci95_lo": round(float(ci_lo), 3),
            "sharpe_ci95_hi": round(float(ci_hi), 3), "ann_return_pct": round(float(mean * 12) * 100, 2),
            "ann_vol_pct": round(float(std * np.sqrt(12)) * 100, 2), "max_dd_pct": round(max_dd * 100, 2),
            "longest_underwater_months": longest_underwater, "n_months": T}


def combine_portfolio(returns: dict, weights: dict) -> pd.Series:
    """Renormalizes weights among strategies with actual data each period --
    a strategy with a shorter history (e.g. S8 starts 1996, S2 starts 1971)
    must NOT be silently credited a hard 0% return for the months before its
    data exists, which would understate the portfolio's true exposure/return
    in the earlier period and distort the whole-sample Sharpe."""
    df = pd.DataFrame(returns)
    w = pd.Series(weights)[df.columns]
    avail = df.notna()
    w_matrix = avail.mul(w, axis=1)
    w_row_sum = w_matrix.sum(axis=1)
    w_normalized = w_matrix.div(w_row_sum, axis=0).fillna(0.0)
    port = (df.fillna(0.0) * w_normalized).sum(axis=1)
    port[w_row_sum == 0] = np.nan
    return port


def vol_target(monthly_ret: pd.Series, target_ann_vol: float = VOL_TARGET_ANN, lookback_months: int = 12) -> pd.Series:
    realized_vol = monthly_ret.rolling(lookback_months).std() * np.sqrt(12)
    scalar = (target_ann_vol / realized_vol).clip(upper=3.0).shift(1).fillna(1.0)
    return monthly_ret * scalar


def build_weights(returns: dict) -> dict:
    df = pd.DataFrame(returns)
    vols = df.std() * np.sqrt(12)
    n = len(df.columns)
    equal = {c: 1.0 / n for c in df.columns}
    inv_vol_raw = {c: 1.0 / vols[c] for c in df.columns}
    s = sum(inv_vol_raw.values())
    inv_vol = {c: v / s for c, v in inv_vol_raw.items()}
    # "simple risk parity" here = inverse-variance (a common simple approximation
    # to full risk parity when cross-correlations are modest; NOT mean-variance optimization)
    inv_var_raw = {c: 1.0 / (vols[c] ** 2) for c in df.columns}
    s2 = sum(inv_var_raw.values())
    risk_parity = {c: v / s2 for c, v in inv_var_raw.items()}
    return {"equal_weight": equal, "inverse_vol": inv_vol, "simple_risk_parity": risk_parity}


if __name__ == "__main__":
    import json
    candidates = load_candidate_returns()
    primary = {k: v for k, v in candidates.items() if "SENSITIVITY" not in k}
    french = load_french_reference()

    corr = correlation_matrix(primary, french)
    corr.to_csv("results/portfolio_correlation_matrix.csv")

    weight_schemes = build_weights(primary)
    results = {"weight_schemes": weight_schemes, "per_strategy_stats": {}, "portfolios": {}}

    for name, ret in primary.items():
        results["per_strategy_stats"][name] = _ann_stats(ret)

    for scheme_name, weights in weight_schemes.items():
        port = combine_portfolio(primary, weights)
        port_vt = vol_target(port)
        stats_raw = _ann_stats(port)
        stats_vt = _ann_stats(port_vt)
        results["portfolios"][scheme_name] = {"raw": stats_raw, "vol_targeted": stats_vt}
        port_vt.to_frame("ret").to_csv(f"results/portfolio_{scheme_name}_vt_monthly_returns.csv")

    # ablation: drop each strategy from the risk-parity portfolio (chosen as primary scheme)
    ablation = {}
    rp_weights = weight_schemes["simple_risk_parity"]
    full_port = vol_target(combine_portfolio(primary, rp_weights))
    full_sharpe = _ann_stats(full_port)["sharpe_ann"]
    for drop in primary:
        remaining = {k: v for k, v in primary.items() if k != drop}
        remaining_weights = build_weights(remaining)["simple_risk_parity"]
        port_wo = vol_target(combine_portfolio(remaining, remaining_weights))
        sharpe_wo = _ann_stats(port_wo)["sharpe_ann"]
        ablation[f"drop_{drop}"] = {"portfolio_sharpe_without": sharpe_wo,
                                     "full_portfolio_sharpe": full_sharpe,
                                     "marginal_contribution": round(full_sharpe - sharpe_wo, 3)}
    results["ablation_risk_parity"] = ablation

    print(json.dumps(results, indent=2, default=str))
