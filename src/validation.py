"""Section 8 validation gates. Every gate returns an explicit PASS / FAIL / INCONCLUSIVE.

Nothing here is allowed to be graded on a curve. A gate that cannot be evaluated
returns INCONCLUSIVE with the reason, never a silent pass.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

BARS_PER_YEAR = 24 * 365
EULER_GAMMA = 0.5772156649015329


# ---------------------------------------------------------------------------
# shared metric helpers
# ---------------------------------------------------------------------------

def trade_sharpe(trade_returns: np.ndarray, trades_per_year: float) -> float:
    r = np.asarray(trade_returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 3:
        return np.nan
    sd = r.std(ddof=1)
    if sd <= 0:
        return 0.0
    return float(r.mean() / sd * np.sqrt(trades_per_year))


def equity_metrics(eq: pd.Series, periods_per_year: float = BARS_PER_YEAR) -> dict:
    eq = eq.dropna()
    if len(eq) < 10:
        return {"error": "insufficient equity points"}
    ret = eq.pct_change().dropna()
    sd = ret.std(ddof=1)
    sharpe = float(ret.mean() / sd * np.sqrt(periods_per_year)) if sd > 0 else 0.0
    downside = ret[ret < 0].std(ddof=1)
    sortino = float(ret.mean() / downside * np.sqrt(periods_per_year)) if downside and downside > 0 else np.nan
    dd = eq / eq.cummax() - 1
    max_dd = float(dd.min())
    years = len(eq) / periods_per_year
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) if years > 0 and eq.iloc[0] > 0 else np.nan
    calmar = float(cagr / abs(max_dd)) if max_dd < 0 and np.isfinite(cagr) else np.nan
    underwater = (dd < 0)
    longest_uw, cur = 0, 0
    for v in underwater:
        cur = cur + 1 if v else 0
        longest_uw = max(longest_uw, cur)
    return {"sharpe": round(sharpe, 3), "sortino": round(sortino, 3) if np.isfinite(sortino) else None,
            "cagr_pct": round(cagr * 100, 2) if np.isfinite(cagr) else None,
            "total_return_pct": round(float(eq.iloc[-1] / eq.iloc[0] - 1) * 100, 2),
            "max_dd_pct": round(max_dd * 100, 2), "calmar": round(calmar, 3) if np.isfinite(calmar) else None,
            "longest_underwater_bars": int(longest_uw),
            "longest_underwater_days": round(longest_uw / 24, 1), "n_bars": len(eq)}


# ---------------------------------------------------------------------------
# 8.1 sample size
# ---------------------------------------------------------------------------

def gate_sample_size(trades: pd.DataFrame, min_trades: int = 500,
                      inconclusive_below: int = 200) -> dict:
    n = len(trades)
    if n == 0:
        return {"gate": "8.1 sample size", "status": "FAIL", "n_trades": 0,
                "detail": "no trades generated"}
    wins = (trades["net_pnl"] > 0).sum()
    p = wins / n
    se = float(np.sqrt(p * (1 - p) / n))
    edge_vs_coinflip = p - 0.5
    inside_2se = abs(edge_vs_coinflip) < 2 * se
    status = "PASS" if n >= min_trades else ("INCONCLUSIVE" if n < inconclusive_below else "FAIL")
    return {"gate": "8.1 sample size", "status": status, "n_trades": int(n),
            "win_rate_pct": round(100 * p, 2), "win_rate_se_pct": round(100 * se, 2),
            "win_rate_ci95": [round(100 * (p - 1.96 * se), 2), round(100 * (p + 1.96 * se), 2)],
            "edge_inside_2se_of_coinflip": bool(inside_2se),
            "detail": ("win rate is inside 2 standard errors of a coin flip -- this is noise"
                       if inside_2se else "win rate is outside 2 SE of a coin flip")}


# ---------------------------------------------------------------------------
# 8.2 anchored walk-forward
# ---------------------------------------------------------------------------

def gate_walk_forward(run_fn, param_grid: list, start: pd.Timestamp, end: pd.Timestamp,
                       train_months: int = 12, test_months: int = 3,
                       select_metric: str = "sharpe") -> dict:
    """Anchored walk-forward: expand train window, pick best param on TRAIN ONLY,
    evaluate that choice on the immediately following TEST window. Never re-optimise
    on test. Returns stitched OOS trade list -- the headline result."""
    folds, oos_trades, is_sharpes, oos_sharpes = [], [], [], []
    anchor = start
    train_end = anchor + pd.DateOffset(months=train_months)
    while train_end + pd.DateOffset(months=test_months) <= end:
        test_end = train_end + pd.DateOffset(months=test_months)
        best, best_m = None, -np.inf
        for params in param_grid:
            tr = run_fn(params, anchor, train_end)
            if tr is None or len(tr) < 10:
                continue
            m = trade_sharpe(tr["ret_on_notional"].values, trades_per_year=_tpy(tr, anchor, train_end))
            if np.isfinite(m) and m > best_m:
                best, best_m = params, m
        if best is not None:
            te = run_fn(best, train_end, test_end)
            oos_m = (trade_sharpe(te["ret_on_notional"].values, _tpy(te, train_end, test_end))
                     if te is not None and len(te) >= 3 else np.nan)
            folds.append({"train_start": str(anchor.date()), "train_end": str(train_end.date()),
                          "test_end": str(test_end.date()), "chosen_params": str(best),
                          "is_sharpe": round(best_m, 3),
                          "oos_sharpe": round(oos_m, 3) if np.isfinite(oos_m) else None,
                          "oos_trades": int(len(te)) if te is not None else 0})
            if te is not None and len(te):
                oos_trades.append(te)
            is_sharpes.append(best_m)
            if np.isfinite(oos_m):
                oos_sharpes.append(oos_m)
        train_end = test_end
    all_oos = pd.concat(oos_trades, ignore_index=True) if oos_trades else pd.DataFrame()
    mean_is = float(np.nanmean(is_sharpes)) if is_sharpes else np.nan
    mean_oos = float(np.nanmean(oos_sharpes)) if oos_sharpes else np.nan
    ratio = (mean_oos / mean_is) if (np.isfinite(mean_is) and mean_is > 0) else np.nan
    status = "PASS" if (np.isfinite(ratio) and ratio >= 0.5 and mean_oos > 0) else "FAIL"
    return {"gate": "8.2 walk-forward", "status": status, "n_folds": len(folds),
            "mean_is_sharpe": round(mean_is, 3) if np.isfinite(mean_is) else None,
            "mean_oos_sharpe": round(mean_oos, 3) if np.isfinite(mean_oos) else None,
            "oos_to_is_ratio": round(ratio, 3) if np.isfinite(ratio) else None,
            "n_oos_trades": int(len(all_oos)), "folds": folds,
            "oos_trades": all_oos,
            "detail": "OOS Sharpe must be >=50% of IS Sharpe and positive"}


def _tpy(trades: pd.DataFrame, t0, t1) -> float:
    days = max((t1 - t0).days, 1)
    return len(trades) / (days / 365.25) if len(trades) else 1.0


# ---------------------------------------------------------------------------
# 8.3 purged k-fold with embargo
# ---------------------------------------------------------------------------

def gate_purged_kfold(trades: pd.DataFrame, k: int = 5, embargo_bars: int = 24) -> dict:
    """Purge trades whose holding window straddles a fold boundary, and embargo a
    window >= max holding period after each test fold, to kill label leakage."""
    if len(trades) < k * 10:
        return {"gate": "8.3 purged k-fold", "status": "INCONCLUSIVE",
                "detail": f"only {len(trades)} trades, need >= {k*10}"}
    t = trades.sort_values("entry_time").reset_index(drop=True)
    embargo = pd.Timedelta(hours=embargo_bars)
    bounds = np.array_split(np.arange(len(t)), k)
    fold_sharpes = []
    for f in bounds:
        if len(f) < 5:
            continue
        test = t.iloc[f]
        t0, t1 = test["entry_time"].min(), test["exit_time"].max()
        # purge: drop train trades overlapping the test window, plus embargo
        keep = ~(((t["exit_time"] >= t0 - embargo) & (t["entry_time"] <= t1 + embargo)))
        train = t[keep]
        s_test = trade_sharpe(test["ret_on_notional"].values, _tpy(test, t0, t1))
        fold_sharpes.append({"n_test": int(len(test)), "n_train_after_purge": int(len(train)),
                             "test_sharpe": round(s_test, 3) if np.isfinite(s_test) else None,
                             "window": f"{t0.date()}..{t1.date()}"})
    vals = [f["test_sharpe"] for f in fold_sharpes if f["test_sharpe"] is not None]
    mean_s = float(np.mean(vals)) if vals else np.nan
    frac_pos = float(np.mean([v > 0 for v in vals])) if vals else np.nan
    status = "PASS" if (np.isfinite(mean_s) and mean_s > 0 and frac_pos >= 0.6) else "FAIL"
    return {"gate": "8.3 purged k-fold", "status": status, "k": k,
            "embargo_bars": embargo_bars, "mean_fold_sharpe": round(mean_s, 3) if np.isfinite(mean_s) else None,
            "fraction_folds_positive": round(frac_pos, 2) if np.isfinite(frac_pos) else None,
            "folds": fold_sharpes}


# ---------------------------------------------------------------------------
# 8.4 deflated Sharpe with the TRUE trial count
# ---------------------------------------------------------------------------

def deflated_sharpe(trade_returns: np.ndarray, n_trials: int, trades_per_year: float) -> dict:
    r = np.asarray(trade_returns, dtype=float)
    r = r[np.isfinite(r)]
    T = len(r)
    if T < 20:
        return {"error": "insufficient trades", "T": T}
    sd = r.std(ddof=1)
    if sd <= 0:
        return {"error": "zero variance"}
    sr = r.mean() / sd                      # per-trade Sharpe
    g3, g4 = float(skew(r)), float(kurtosis(r, fisher=False))
    sigma_sr = np.sqrt(max(1e-12, (1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / max(1, T - 1)))
    if n_trials > 1:
        sr0 = sigma_sr * ((1 - EULER_GAMMA) * norm.ppf(1 - 1.0 / n_trials) +
                          EULER_GAMMA * norm.ppf(1 - 1.0 / (n_trials * np.e)))
    else:
        sr0 = 0.0
    z = (sr - sr0) / sigma_sr
    return {"per_trade_sharpe": round(float(sr), 5),
            "annualised_sharpe_raw": round(float(sr * np.sqrt(trades_per_year)), 3),
            "expected_max_sharpe_under_null": round(float(sr0), 5),
            "deflated_sharpe_prob": round(float(norm.cdf(z)), 4),
            "n_trials": int(n_trials), "T": T, "skew": round(g3, 3),
            "excess_kurtosis": round(g4 - 3, 3)}


def gate_deflated_sharpe(trade_returns, n_trials, trades_per_year, threshold=0.95) -> dict:
    d = deflated_sharpe(trade_returns, n_trials, trades_per_year)
    if "error" in d:
        return {"gate": "8.4 deflated Sharpe", "status": "INCONCLUSIVE", **d}
    status = "PASS" if d["deflated_sharpe_prob"] >= threshold else "FAIL"
    return {"gate": "8.4 deflated Sharpe", "status": status, "threshold": threshold, **d}


# ---------------------------------------------------------------------------
# 8.5 parameter stability
# ---------------------------------------------------------------------------

def gate_parameter_stability(surface: pd.DataFrame, metric: str = "sharpe") -> dict:
    """surface: one row per parameter combination with the metric.
    A genuine edge sits on a PLATEAU; a sharp peak with losing neighbours is overfitting."""
    if surface.empty:
        return {"gate": "8.5 parameter stability", "status": "INCONCLUSIVE", "detail": "no surface"}
    s = surface.dropna(subset=[metric])
    if len(s) < 4:
        return {"gate": "8.5 parameter stability", "status": "INCONCLUSIVE",
                "detail": f"only {len(s)} evaluated points"}
    best = s.loc[s[metric].idxmax()]
    frac_positive = float((s[metric] > 0).mean())
    median_m = float(s[metric].median())
    peak = float(best[metric])
    # plateau test: is the best point an isolated spike vs the rest of the surface?
    others = s[metric].drop(best.name)
    peak_premium = (peak - others.median()) / (others.std(ddof=1) + 1e-12)
    is_plateau = (frac_positive >= 0.6) and (median_m > 0) and (peak_premium < 3.0)
    status = "PASS" if is_plateau else "FAIL"
    return {"gate": "8.5 parameter stability", "status": status,
            "n_points": int(len(s)), "best_metric": round(peak, 3),
            "median_metric": round(median_m, 3),
            "fraction_positive": round(frac_positive, 3),
            "peak_zscore_vs_rest": round(float(peak_premium), 2),
            "best_params": {k: best[k] for k in s.columns if k != metric},
            "detail": ("surface is a plateau (majority positive, peak not isolated)" if is_plateau
                       else "surface is a PEAK not a plateau, and/or most neighbours lose money "
                            "-- consistent with overfitting")}


# ---------------------------------------------------------------------------
# 8.6 regime robustness
# ---------------------------------------------------------------------------

def classify_regimes(btc: pd.DataFrame) -> pd.DataFrame:
    """Trailing-only regime labels from BTC: bull/bear/chop by 30d trend vs vol,
    and high/low vol by trailing 30d realised vol median. No lookahead."""
    d = btc.copy().reset_index(drop=True)
    d["ret"] = d["close"].pct_change()
    win = 24 * 30
    d["trend"] = d["close"].pct_change(win)
    d["vol"] = d["ret"].rolling(win).std() * np.sqrt(BARS_PER_YEAR)
    vol_med = d["vol"].expanding(min_periods=win).median()      # expanding = trailing only
    d["vol_regime"] = np.where(d["vol"] > vol_med, "high_vol", "low_vol")
    thresh = 0.10
    d["dir_regime"] = np.where(d["trend"] > thresh, "bull",
                        np.where(d["trend"] < -thresh, "bear", "chop"))
    return d[["timestamp", "dir_regime", "vol_regime", "trend", "vol"]]


def gate_regime_robustness(trades: pd.DataFrame, regimes: pd.DataFrame) -> dict:
    if trades.empty:
        return {"gate": "8.6 regime robustness", "status": "INCONCLUSIVE", "detail": "no trades"}
    t = trades.copy()
    r = regimes.dropna(subset=["dir_regime"]).set_index("timestamp")
    t["dir_regime"] = t["entry_time"].map(r["dir_regime"])
    t["vol_regime"] = t["entry_time"].map(r["vol_regime"])
    t["year"] = pd.to_datetime(t["entry_time"]).dt.year

    def _blk(sub):
        if len(sub) < 5:
            return {"n": int(len(sub)), "note": "too few trades"}
        return {"n": int(len(sub)),
                "mean_ret_bps": round(float(sub["ret_on_notional"].mean()) * 1e4, 2),
                "win_rate_pct": round(100 * float((sub["net_pnl"] > 0).mean()), 1),
                "total_net_pnl": round(float(sub["net_pnl"].sum()), 2),
                "sharpe_per_trade": round(float(sub["ret_on_notional"].mean() /
                                                (sub["ret_on_notional"].std(ddof=1) + 1e-12)), 4)}

    by_dir = {k: _blk(g) for k, g in t.groupby("dir_regime", dropna=True)}
    by_vol = {k: _blk(g) for k, g in t.groupby("vol_regime", dropna=True)}
    by_year = {int(k): _blk(g) for k, g in t.groupby("year")}
    pos = [v.get("total_net_pnl", 0) > 0 for v in by_dir.values() if "total_net_pnl" in v]
    frac_pos = float(np.mean(pos)) if pos else np.nan
    status = "PASS" if (np.isfinite(frac_pos) and frac_pos >= 0.6) else "FAIL"
    return {"gate": "8.6 regime robustness", "status": status,
            "fraction_dir_regimes_profitable": round(frac_pos, 2) if np.isfinite(frac_pos) else None,
            "by_direction_regime": by_dir, "by_vol_regime": by_vol, "by_year": by_year,
            "detail": "a strategy profitable in only one regime is a regime bet, not an edge"}


# ---------------------------------------------------------------------------
# 8.7 block bootstrap CIs
# ---------------------------------------------------------------------------

def gate_block_bootstrap(trades: pd.DataFrame, n_iter: int = 10_000, block: int = 20,
                          trades_per_year: float = 100.0, seed: int = 7) -> dict:
    if len(trades) < 30:
        return {"gate": "8.7 block bootstrap", "status": "INCONCLUSIVE",
                "detail": f"only {len(trades)} trades"}
    r = trades["ret_on_notional"].values.astype(float)
    rng = np.random.default_rng(seed)
    n = len(r)
    nblocks = int(np.ceil(n / block))
    sharpes, cagrs, dds, exps = [], [], [], []
    for _ in range(n_iter):
        starts = rng.integers(0, max(1, n - block), size=nblocks)
        sample = np.concatenate([r[s:s + block] for s in starts])[:n]
        sd = sample.std(ddof=1)
        sharpes.append(sample.mean() / sd * np.sqrt(trades_per_year) if sd > 0 else 0.0)
        exps.append(sample.mean())
        eq = np.cumprod(1 + sample)
        dds.append(float((eq / np.maximum.accumulate(eq) - 1).min()))
        cagrs.append(eq[-1] - 1)
    def ci(a):
        return [round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)]
    sharpe_ci = ci(sharpes)
    status = "PASS" if sharpe_ci[0] > 0 else "FAIL"
    return {"gate": "8.7 block bootstrap", "status": status, "n_iter": n_iter, "block": block,
            "sharpe_ci95": sharpe_ci, "sharpe_median": round(float(np.median(sharpes)), 3),
            "expectancy_ci95": ci(exps), "total_return_ci95": ci(cagrs),
            "max_dd_ci95": ci(dds),
            "detail": ("lower bound of Sharpe CI is below 0 -- strategy is NOT demonstrated"
                       if sharpe_ci[0] <= 0 else "Sharpe CI lower bound is above 0")}


# ---------------------------------------------------------------------------
# 8.8 Monte Carlo drawdown / streak distribution
# ---------------------------------------------------------------------------

def gate_monte_carlo_drawdown(trades: pd.DataFrame, n_iter: int = 10_000, seed: int = 11) -> dict:
    if len(trades) < 30:
        return {"gate": "8.8 MC drawdown", "status": "INCONCLUSIVE",
                "detail": f"only {len(trades)} trades"}
    r = trades["ret_on_notional"].values.astype(float)
    rng = np.random.default_rng(seed)
    dds, streaks = [], []
    for _ in range(n_iter):
        s = rng.permutation(r)
        eq = np.cumprod(1 + s)
        dds.append(float((eq / np.maximum.accumulate(eq) - 1).min()))
        losing = s <= 0
        best, cur = 0, 0
        for v in losing:
            cur = cur + 1 if v else 0
            best = max(best, cur)
        streaks.append(best)
    realized_eq = np.cumprod(1 + r)
    realized_dd = float((realized_eq / np.maximum.accumulate(realized_eq) - 1).min())
    losing = r <= 0
    best, cur = 0, 0
    for v in losing:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return {"gate": "8.8 MC drawdown", "status": "INFO", "n_iter": n_iter,
            "realized_max_dd_pct": round(realized_dd * 100, 2),
            "mc_max_dd_median_pct": round(float(np.median(dds)) * 100, 2),
            "mc_max_dd_p95_pct": round(float(np.percentile(dds, 5)) * 100, 2),
            "mc_max_dd_worst_pct": round(float(np.min(dds)) * 100, 2),
            "realized_longest_losing_streak": int(best),
            "mc_streak_median": int(np.median(streaks)),
            "mc_streak_p95": int(np.percentile(streaks, 95)),
            "detail": "the realized backtest drawdown is ONE draw and is usually optimistic"}
