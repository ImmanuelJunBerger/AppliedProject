"""Statistical discipline layer for Run 2: locked holdout splitting, a
running N_TESTS registry, Benjamini-Hochberg FDR correction, and the
deflated Sharpe ratio (Bailey & Lopez de Prado 2014).

Every hypothesis test in Run 2 must call `register_test(...)` exactly once
per (hypothesis, variant) so the denominator in RESULTS_V2.md is real, not
whatever subset looks convenient afterward.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "results" / "n_tests_registry.csv"
REGISTRY_PATH_V5 = Path(__file__).resolve().parent.parent / "results" / "n_tests_registry_v5.csv"
EULER_GAMMA = 0.5772156649015329


def train_holdout_split(dates, holdout_frac: float = 0.3):
    """Locked 70/30 split by date. Call once per hypothesis; holdout dates
    must only be used for the single confirmatory pass."""
    idx = pd.DatetimeIndex(sorted(pd.Index(dates).unique()))
    n = len(idx)
    split = int(n * (1 - holdout_frac))
    return idx[:split], idx[split:]


def one_sided_pvalue(returns: np.ndarray) -> float:
    """p-value for H0: mean per-period return <= 0, via a normal approximation
    to the t-statistic (Lo 2002 style). Fine for the moderate sample sizes here;
    not claiming small-sample exactness."""
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]
    T = len(returns)
    if T < 5:
        return 1.0
    sd = returns.std(ddof=1)
    if sd == 0:
        return 1.0
    t_stat = returns.mean() / sd * np.sqrt(T)
    return float(1 - norm.cdf(t_stat))


def deflated_sharpe_ratio(returns: np.ndarray, n_trials: int) -> dict:
    """Probability the observed Sharpe is genuine skill rather than the best
    of `n_trials` noise draws. Returns per-period (not annualized) SR."""
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]
    T = len(returns)
    if T < 10 or n_trials < 1:
        return {"error": "insufficient_data", "T": T, "n_trials": n_trials}
    sd = returns.std(ddof=1)
    if sd == 0:
        return {"error": "zero_variance", "T": T, "n_trials": n_trials}
    sr = returns.mean() / sd
    g3 = float(skew(returns))
    g4 = float(kurtosis(returns, fisher=False))  # normal = 3
    sigma_sr = np.sqrt(max(1e-12, (1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / max(1, T - 1)))
    if n_trials > 1 and sigma_sr > 0:
        sr0 = sigma_sr * ((1 - EULER_GAMMA) * norm.ppf(1 - 1.0 / n_trials) +
                           EULER_GAMMA * norm.ppf(1 - 1.0 / (n_trials * np.e)))
    else:
        sr0 = 0.0
    z = (sr - sr0) / sigma_sr if sigma_sr > 0 else 0.0
    dsr = float(norm.cdf(z))
    return {"sr_per_period": round(float(sr), 4), "sr0_expected_max_under_null": round(float(sr0), 4),
            "sigma_sr": round(float(sigma_sr), 4), "z": round(float(z), 3),
            "deflated_sharpe_prob": round(dsr, 4), "T": T, "n_trials": n_trials}


def benjamini_hochberg(pvalues: dict, q: float = 0.10) -> dict:
    """Standard BH step-up procedure. pvalues: {test_id: p}. Returns which
    test_ids survive at FDR q, plus the full ranked table for transparency."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    if m == 0:
        return {"significant": set(), "m": 0, "table": []}
    threshold_rank = 0
    for i, (_, p) in enumerate(items, start=1):
        if p <= (i / m) * q:
            threshold_rank = i
    significant = {items[i][0] for i in range(threshold_rank)}
    table = [{"test_id": k, "raw_p": round(p, 5), "rank": i + 1,
              "bh_threshold": round((i + 1) / m * q, 5), "survives_bh": k in significant}
             for i, (k, p) in enumerate(items)]
    return {"significant": significant, "m": m, "q": q, "table": table}


def reset_registry(registry_path: Path = REGISTRY_PATH):
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w", newline="") as f:
        csv.writer(f).writerow(["test_id", "hypothesis", "variant", "family", "n_trades",
                                 "sharpe_is", "p_is", "sharpe_holdout", "p_holdout", "note"])


def register_test(test_id: str, hypothesis: str, variant: str, family: str, n_trades,
                   sharpe_is=None, p_is=None, sharpe_holdout=None, p_holdout=None, note: str = "",
                   registry_path: Path = REGISTRY_PATH):
    """registry_path lets independent hypothesis families (e.g. Run 2's crypto
    tests vs. Run 5's TradFi tests) keep separate N_TESTS denominators --
    mixing unrelated families into one FDR pool would misrepresent both."""
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not registry_path.exists()
    with open(registry_path, "a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["test_id", "hypothesis", "variant", "family", "n_trades",
                        "sharpe_is", "p_is", "sharpe_holdout", "p_holdout", "note"])
        w.writerow([test_id, hypothesis, variant, family, n_trades, sharpe_is, p_is,
                    sharpe_holdout, p_holdout, note])


def load_registry(registry_path: Path = REGISTRY_PATH) -> pd.DataFrame:
    if not registry_path.exists():
        return pd.DataFrame()
    return pd.read_csv(registry_path)
