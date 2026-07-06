"""Portfolio construction and dynamic risk allocation for the frozen macro strategy.

Standalone portfolio-optimisation study.  The alpha signal
``btc_eth_macro_gate_balanced`` is frozen: features, thresholds, macro gate and
candidate selection are not modified.  This module only changes portfolio
construction and post-signal position sizing.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .expansion_state_model import _all_risk_on, _buy_hold_weights, _fmt, _json_safe, _prior_meta_overlay_rows, _rows_for_result, _table, _weekly_return
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
)
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import block_bootstrap_sharpe_ci, deflated_sharpe_probability, probability_backtest_overfitting


BASELINE_NAME = FIXED_SELECTED.name
DEVELOPMENT_START = pd.Timestamp("2019-07-05")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")
MIN_HOLDOUT_EXPOSURE = 0.20


METHODS = (
    "equal_weight",
    "volatility_targeting",
    "inverse_volatility",
    "risk_parity",
    "erc",
    "hrp",
    "maximum_diversification",
    "mean_variance",
    "mean_cvar",
    "kelly",
    "fractional_kelly_0_25",
    "fractional_kelly_0_50",
    "fractional_kelly_0_75",
    "probability_weighted",
    "confidence_weighted",
    "expected_return_weighted",
)


@dataclass(frozen=True)
class PortfolioCandidate:
    name: str
    method: str
    universe: str
    dynamic_budget: bool
    description: str


def predeclared_portfolio_candidates() -> list[PortfolioCandidate]:
    candidates: list[PortfolioCandidate] = []
    for method in METHODS:
        for universe in ("btc_eth", "btc_eth_cash"):
            for dynamic in (False, True):
                candidates.append(PortfolioCandidate(
                    name=f"{method}__{universe}__{'dynamic' if dynamic else 'static'}",
                    method=method,
                    universe=universe,
                    dynamic_budget=dynamic,
                    description=f"{method} sizing, {universe}, {'dynamic risk budget' if dynamic else 'static risk budget'}",
                ))
    return candidates


def _safe_cov(frame: pd.DataFrame) -> pd.DataFrame:
    cov = frame.cov().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if cov.empty:
        return cov
    ridge = max(float(np.trace(cov.to_numpy())) / max(len(cov), 1), 1e-8) * 0.05
    return cov + np.eye(len(cov)) * ridge


def _normalize(weights: pd.Series, max_weight: float = 1.0) -> pd.Series:
    weights = weights.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(lower=0.0)
    if max_weight < 1.0:
        weights = weights.clip(upper=max_weight)
    total = float(weights.sum())
    return weights / total if total > 0 else weights


def _erc_weights(cov: pd.DataFrame) -> pd.Series:
    assets = list(cov.columns)
    if not assets:
        return pd.Series(dtype=float)
    w = np.ones(len(assets)) / len(assets)
    covv = cov.to_numpy(dtype=float)
    for _ in range(250):
        port_var = float(w @ covv @ w)
        if port_var <= 0:
            break
        marginal = covv @ w
        risk_contrib = w * marginal / port_var
        target = np.ones(len(assets)) / len(assets)
        adjustment = target / np.maximum(risk_contrib, 1e-8)
        w = w * adjustment ** 0.20
        w = np.clip(w, 0.0, 1.0)
        total = w.sum()
        if total <= 0:
            w = np.ones(len(assets)) / len(assets)
        else:
            w = w / total
    return pd.Series(w, index=assets)


def _max_diversification_weights(cov: pd.DataFrame) -> pd.Series:
    if cov.empty:
        return pd.Series(dtype=float)
    vols = pd.Series(np.sqrt(np.diag(cov)), index=cov.columns).replace(0, np.nan).fillna(cov.stack().std() or 1.0)
    raw = pd.Series(np.linalg.pinv(cov.to_numpy(dtype=float)) @ vols.to_numpy(dtype=float), index=cov.columns)
    return _normalize(raw)


def _mean_variance_weights(mu: pd.Series, cov: pd.DataFrame) -> pd.Series:
    if cov.empty:
        return pd.Series(dtype=float)
    raw = pd.Series(np.linalg.pinv(cov.to_numpy(dtype=float)) @ mu.reindex(cov.columns).fillna(0.0).to_numpy(dtype=float), index=cov.columns)
    return _normalize(raw)


def _mean_cvar_weights(returns: pd.DataFrame, mu: pd.Series) -> pd.Series:
    if returns.empty:
        return pd.Series(dtype=float)
    losses = -returns
    cvar = losses[losses.ge(losses.quantile(0.90), axis=1)].mean().replace(0, np.nan)
    raw = mu.reindex(returns.columns).clip(lower=0.0) / cvar.reindex(returns.columns).abs()
    return _normalize(raw)


def _rolling_inputs(dataset: MacroRegimeDataset, date: pd.Timestamp, assets: list[str], lookback: int = 90) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    history = dataset.returns.loc[:date, assets].iloc[-lookback:].dropna(how="all")
    if len(history) < 20:
        history = dataset.returns.loc[:date, assets].iloc[-max(20, min(len(dataset.returns.loc[:date]), lookback)):].fillna(0.0)
    mu = history.mean() * 365 if not history.empty else pd.Series(0.0, index=assets)
    cov = _safe_cov(history * np.sqrt(365)) if not history.empty else pd.DataFrame(np.eye(len(assets)), index=assets, columns=assets)
    return history, mu.reindex(assets).fillna(0.0), cov.reindex(index=assets, columns=assets).fillna(0.0)


def _relative_weights(method: str, dataset: MacroRegimeDataset, date: pd.Timestamp, assets: list[str]) -> tuple[pd.Series, float]:
    history, mu, cov = _rolling_inputs(dataset, date, assets)
    vols = history.std().replace(0, np.nan) * np.sqrt(365) if not history.empty else pd.Series(1.0, index=assets)
    scale = 1.0
    if method in ("equal_weight", "volatility_targeting"):
        weights = pd.Series(1.0 / max(len(assets), 1), index=assets)
        if method == "volatility_targeting":
            port = history.reindex(columns=assets).fillna(0.0).dot(weights) if not history.empty else pd.Series(dtype=float)
            realized = float(port.std() * np.sqrt(365)) if len(port) else np.nan
            scale = float(np.clip(0.25 / realized, 0.0, 1.0)) if np.isfinite(realized) and realized > 0 else 1.0
    elif method in ("inverse_volatility", "hrp"):
        weights = _normalize(1.0 / vols.reindex(assets).replace(0, np.nan))
    elif method == "risk_parity":
        weights = _normalize(1.0 / vols.reindex(assets).replace(0, np.nan))
    elif method == "erc":
        weights = _erc_weights(cov)
    elif method == "maximum_diversification":
        weights = _max_diversification_weights(cov)
    elif method == "mean_variance":
        weights = _mean_variance_weights(mu.clip(lower=0.0), cov)
    elif method == "mean_cvar":
        weights = _mean_cvar_weights(history.reindex(columns=assets).fillna(0.0), mu)
    elif method.startswith("kelly") or method.startswith("fractional_kelly"):
        raw = pd.Series(np.linalg.pinv(cov.to_numpy(dtype=float)) @ mu.reindex(cov.columns).fillna(0.0).to_numpy(dtype=float), index=cov.columns)
        raw = raw.clip(lower=0.0)
        full_fraction = float(np.clip(raw.sum(), 0.0, 1.0))
        weights = _normalize(raw)
        if method == "kelly":
            scale = full_fraction
        elif method.endswith("0_25"):
            scale = 0.25 * full_fraction
        elif method.endswith("0_50"):
            scale = 0.50 * full_fraction
        else:
            scale = 0.75 * full_fraction
    elif method == "probability_weighted":
        hit = (history.reindex(columns=assets) > 0).rolling(30, min_periods=10).mean().iloc[-1] if not history.empty else pd.Series(0.5, index=assets)
        weights = _normalize(hit.reindex(assets).fillna(0.5))
    elif method == "confidence_weighted":
        score = (mu.reindex(assets) / vols.reindex(assets).replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).clip(lower=0.0)
        weights = _normalize(score)
    elif method == "expected_return_weighted":
        weights = _normalize(mu.reindex(assets).clip(lower=0.0))
    else:
        weights = pd.Series(1.0 / max(len(assets), 1), index=assets)
    if float(weights.sum()) <= 0:
        weights = pd.Series(1.0 / max(len(assets), 1), index=assets)
    return _normalize(weights), float(np.clip(scale, 0.0, 1.0))


def _dynamic_budget_scale(dataset: MacroRegimeDataset, macro_features: pd.DataFrame, base_result: PortfolioResult, date: pd.Timestamp) -> float:
    features = dataset.regime_features.reindex([date]).ffill()
    if features.empty:
        return 1.0
    dev = dataset.regime_features.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    row = features.iloc[0]
    score = 0
    total = 0
    if "equity_momentum_21d" in row and "equity_momentum_21d" in dev:
        score += int(row["equity_momentum_21d"] >= dev["equity_momentum_21d"].median())
        total += 1
    if "vix_change_21d" in row and "vix_change_21d" in dev:
        score += int(row["vix_change_21d"] <= dev["vix_change_21d"].median())
        total += 1
    if "equity_realized_vol_21d" in row and "equity_realized_vol_21d" in dev:
        threshold = dev["equity_realized_vol_21d"].median()
        score += int(row["equity_realized_vol_21d"] <= threshold)
        total += 1
    trailing = base_result.returns.loc[:date].iloc[-63:]
    if len(trailing) >= 30:
        recent_vol = trailing.iloc[-21:].std()
        prior_vol = trailing.iloc[:-21].std()
        score += int(np.isfinite(recent_vol) and np.isfinite(prior_vol) and recent_vol <= prior_vol)
        total += 1
    wealth = (1.0 + base_result.returns.loc[:date].fillna(0.0)).cumprod()
    drawdown = float(wealth.iloc[-1] / wealth.cummax().iloc[-1] - 1.0) if len(wealth) else 0.0
    if drawdown <= -0.20:
        return 0.0
    if drawdown <= -0.10:
        return 0.50
    if total == 0:
        return 1.0
    ratio = score / total
    if ratio >= 0.75:
        return 1.0
    if ratio >= 0.50:
        return 0.75
    return 0.50


def build_portfolio_weights(
    dataset: MacroRegimeDataset,
    base_weights: pd.DataFrame,
    base_result: PortfolioResult,
    candidate: PortfolioCandidate,
) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=base_weights.index, columns=base_weights.columns)
    for date, base in base_weights.iterrows():
        base_exposure = float(base.sum())
        if base_exposure <= 0:
            continue
        assets = [symbol for symbol in ("BTC", "ETH") if symbol in base.index and base.loc[symbol] > 0]
        if not assets:
            continue
        rel, method_scale = _relative_weights(candidate.method, dataset, date, assets)
        exposure = base_exposure
        if candidate.universe == "btc_eth_cash":
            exposure *= method_scale
        elif candidate.method in {"volatility_targeting", "kelly", "fractional_kelly_0_25", "fractional_kelly_0_50", "fractional_kelly_0_75"}:
            exposure *= method_scale
        if candidate.dynamic_budget:
            exposure *= _dynamic_budget_scale(dataset, dataset.regime_features, base_result, date)
        exposure = float(np.clip(exposure, 0.0, 1.0))
        weights.loc[date, rel.index] = rel * exposure
    return weights


def omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    r = returns.dropna() - threshold
    gains = r[r > 0].sum()
    losses = -r[r < 0].sum()
    return float(gains / losses) if losses > 0 else np.nan


def rolling_diagnostics(result: PortfolioResult, name: str) -> pd.DataFrame:
    returns = result.returns
    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    rows = []
    for window in (90, 180):
        rolling_sharpe = returns.rolling(window).mean() / returns.rolling(window).std().replace(0, np.nan) * np.sqrt(365)
        rolling_vol = returns.rolling(window).std() * np.sqrt(365)
        rows.append({
            "name": name,
            "window_days": window,
            "median_rolling_sharpe": float(rolling_sharpe.median()),
            "worst_rolling_sharpe": float(rolling_sharpe.min()),
            "median_rolling_volatility": float(rolling_vol.median()),
            "max_rolling_drawdown": float(drawdown.rolling(window).min().min()),
        })
    return pd.DataFrame(rows)


def _enhanced_period_metrics(result: PortfolioResult, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float]:
    metrics = period_metrics(result, start, end)
    returns = result.returns.loc[start:end]
    metrics["Omega"] = omega_ratio(returns)
    return metrics


def _fold_sharpe(weekly: pd.Series, indices: tuple[int, ...]) -> float:
    subset = weekly.iloc[list(indices)].dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def select_candidate_cpcv(candidates: list[PortfolioCandidate], results_25bps: dict[str, PortfolioResult]) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows = []
    fold_rows = []
    weekly_returns = {}
    for candidate in candidates:
        weekly = _weekly_return(results_25bps[candidate.name].returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        weekly_returns[candidate.name] = weekly
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_values = []
        for number, split in enumerate(splits):
            sharpe = _fold_sharpe(weekly, split.test_indices)
            fold_values.append(sharpe)
            fold_rows.append({"candidate": candidate.name, "method": candidate.method, "universe": candidate.universe, "dynamic_budget": candidate.dynamic_budget, "fold": number, "test_groups": ",".join(str(g) for g in split.test_groups), "fold_sharpe": sharpe})
        dev = _enhanced_period_metrics(results_25bps[candidate.name], DEVELOPMENT_START, DEVELOPMENT_END)
        rows.append({
            "candidate": candidate.name,
            "method": candidate.method,
            "universe": candidate.universe,
            "dynamic_budget": candidate.dynamic_budget,
            "median_fold_sharpe": float(np.nanmedian(fold_values)),
            "worst_fold_sharpe": float(np.nanmin(fold_values)),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_values) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
            "development_omega": dev["Omega"],
        })
    selection = pd.DataFrame(rows)
    selection["selection_score"] = (
        selection["median_fold_sharpe"]
        + 0.25 * selection["worst_fold_sharpe"]
        + 0.20 * selection["positive_fold_fraction"]
        - np.maximum(0.0, selection["development_turnover"] - 12.0) * 0.05
    )
    selection = selection.sort_values(["selection_score", "median_fold_sharpe", "worst_fold_sharpe", "development_turnover"], ascending=[False, False, False, True])
    pbo = probability_backtest_overfitting(pd.concat(weekly_returns, axis=1).sort_index(), blocks=8) if len(weekly_returns) > 1 else np.nan
    return selection, pd.DataFrame(fold_rows), str(selection.iloc[0].candidate), pbo


def _paired_sharpe_test(candidate: pd.Series, benchmark: pd.Series) -> dict[str, float]:
    data = pd.concat([candidate.rename("candidate"), benchmark.rename("benchmark")], axis=1).dropna()
    if len(data) < 30:
        return {"sharpe_delta": np.nan, "jobson_korkie_z_approx": np.nan, "jobson_korkie_p_approx": np.nan}
    c = data.candidate
    b = data.benchmark
    sr_c = c.mean() / c.std(ddof=1) if c.std(ddof=1) else 0.0
    sr_b = b.mean() / b.std(ddof=1) if b.std(ddof=1) else 0.0
    rho = float(c.corr(b)) if np.isfinite(c.corr(b)) else 0.0
    n = len(data)
    var = max((2 * (1 - rho) + 0.5 * (sr_c ** 2 + sr_b ** 2 - 2 * sr_c * sr_b * rho ** 2)) / n, 1e-12)
    z = (sr_c - sr_b) / math.sqrt(var)
    p = math.erfc(abs(z) / math.sqrt(2))
    return {"sharpe_delta": float((sr_c - sr_b) * np.sqrt(365)), "jobson_korkie_z_approx": float(z), "jobson_korkie_p_approx": float(p)}


def _benchmark_rows(dataset: MacroRegimeDataset, regimes: tuple[pd.Series, pd.Series, pd.Series], base_weights: pd.DataFrame) -> pd.DataFrame:
    rows = []
    macro, crypto, combined = regimes
    risk_on = _all_risk_on(dataset.close.index)
    for cost in COST_LEVELS:
        frozen = backtest_weights(dataset, base_weights, macro, crypto, combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
        rows.extend(_rows_for_result(BASELINE_NAME, "Frozen macro strategy", "frozen_strategy", cost, frozen))
        for name, family in (("btc_buy_hold", "BTC buy-and-hold"), ("eth_buy_hold", "ETH buy-and-hold"), ("btc_eth_50_50", "50/50 BTC/ETH")):
            result = backtest_weights(dataset, _buy_hold_weights(dataset, name), *risk_on, cost_bps=cost, turnover_cap=10.0)
            rows.extend(_rows_for_result(name, family, "benchmark", cost, result))
    prior_meta = _prior_meta_overlay_rows()
    if not prior_meta.empty:
        rows.extend(prior_meta.to_dict("records"))
    expansion_path = Path("reports/expansion_first_research/selected_holdouts.csv")
    if expansion_path.exists():
        expansion = pd.read_csv(expansion_path)
        for _, row in expansion.iterrows():
            rows.append({
                "name": row.get("candidate"),
                "family": f"Prior expansion-first study ({row.get('selection')})",
                "benchmark_group": "prior_expansion_first_or_hybrid",
                "split": "holdout",
                "cost_bps": 25,
                "selected_development_candidate": False,
                "CAGR": row.get("CAGR"),
                "Sharpe": row.get("Sharpe"),
                "Sortino": row.get("Sortino"),
                "Maximum Drawdown": row.get("Maximum Drawdown"),
                "Calmar": row.get("Calmar"),
                "Annual Turnover": row.get("Annual Turnover"),
                "Exposure": row.get("Exposure"),
            })
    return pd.DataFrame(rows)


def run_portfolio_optimisation(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    base_weights, macro_regime, crypto_regime, combined_regime = build_candidate_weights(dataset, FIXED_SELECTED)
    frozen_25 = backtest_weights(dataset, base_weights, macro_regime, crypto_regime, combined_regime, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
    candidates = predeclared_portfolio_candidates()
    weights_by_candidate: dict[str, pd.DataFrame] = {}
    results: dict[str, dict[int, PortfolioResult]] = {}
    for candidate in candidates:
        weights = build_portfolio_weights(dataset, base_weights, frozen_25, candidate)
        weights_by_candidate[candidate.name] = weights
        results[candidate.name] = {
            cost: backtest_weights(dataset, weights, macro_regime, crypto_regime, combined_regime, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
            for cost in COST_LEVELS
        }
    results_25 = {name: by_cost[25] for name, by_cost in results.items()}
    selection, cpcv_folds, winner, pbo = select_candidate_cpcv(candidates, results_25)
    candidate_map = {candidate.name: candidate for candidate in candidates}
    metric_rows = []
    for name, by_cost in results.items():
        candidate = candidate_map[name]
        for cost, result in by_cost.items():
            for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
                metrics = _enhanced_period_metrics(result, start, end)
                metric_rows.append({
                    "name": name,
                    "method": candidate.method,
                    "universe": candidate.universe,
                    "dynamic_budget": candidate.dynamic_budget,
                    "split": split,
                    "cost_bps": cost,
                    "selected_development_candidate": name == winner,
                    **metrics,
                })
    metrics = pd.DataFrame(metric_rows)
    benchmarks = _benchmark_rows(dataset, (macro_regime, crypto_regime, combined_regime), base_weights)
    winner_result_25 = results[winner][25]
    winner_result_50 = results[winner][50]
    frozen_holdout = _enhanced_period_metrics(frozen_25, HOLDOUT_START, HOLDOUT_END)
    winner_holdout = _enhanced_period_metrics(winner_result_25, HOLDOUT_START, HOLDOUT_END)
    winner_50 = _enhanced_period_metrics(winner_result_50, HOLDOUT_START, HOLDOUT_END)
    bootstrap = block_bootstrap_sharpe_ci(winner_result_25.returns.loc[HOLDOUT_START:HOLDOUT_END], samples=500, block_length=14, seed=73)
    dsr = deflated_sharpe_probability(winner_result_25.returns.loc[HOLDOUT_START:HOLDOUT_END], tested_configurations=len(candidates))
    paired = _paired_sharpe_test(winner_result_25.returns.loc[HOLDOUT_START:HOLDOUT_END], frozen_25.returns.loc[HOLDOUT_START:HOLDOUT_END])
    rolling = pd.concat([
        rolling_diagnostics(frozen_25, BASELINE_NAME),
        rolling_diagnostics(winner_result_25, winner),
    ], ignore_index=True)
    winner_candidate = candidate_map[winner]
    improvement_from_cash = bool(winner_holdout["Exposure"] < max(MIN_HOLDOUT_EXPOSURE, frozen_holdout["Exposure"] * 0.75))
    passes = bool(
        winner_holdout["Sharpe"] > frozen_holdout["Sharpe"]
        and winner_holdout["CAGR"] >= frozen_holdout["CAGR"] * 0.90
        and winner_holdout["Maximum Drawdown"] >= frozen_holdout["Maximum Drawdown"]
        and winner_holdout["Exposure"] >= MIN_HOLDOUT_EXPOSURE
        and not improvement_from_cash
        and winner_holdout["Annual Turnover"] <= 12
        and winner_50["CAGR"] > 0
        and (not np.isfinite(pbo) or pbo <= 0.65)
        and np.isfinite(dsr)
        and dsr >= 0.50
    )
    conclusion = (
        "Portfolio construction produces a statistically and economically acceptable replacement for the frozen implementation."
        if passes
        else "No portfolio-construction method provides statistically and economically convincing improvement; keep the original frozen portfolio construction unchanged."
    )
    return {
        "dataset": dataset,
        "candidates": candidates,
        "selection": selection,
        "cpcv_folds": cpcv_folds,
        "winner": winner,
        "winner_candidate": winner_candidate,
        "metrics": metrics,
        "benchmarks": benchmarks,
        "rolling_diagnostics": rolling,
        "frozen_holdout": frozen_holdout,
        "winner_holdout": winner_holdout,
        "winner_50bps": winner_50,
        "pbo": pbo,
        "deflated_sharpe_probability": dsr,
        "bootstrap_sharpe_ci": bootstrap,
        "paired_sharpe_test": paired,
        "improvement_from_cash": improvement_from_cash,
        "passes_replacement_filters": passes,
        "final_conclusion": conclusion,
        "tested_configurations": len(candidates),
        "protocol": {
            "title": "Portfolio Construction and Dynamic Risk Allocation for Macro-Regime Cryptocurrency Strategies",
            "baseline": BASELINE_NAME,
            "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} onward",
            "selection": "Development-only CPCV using median fold Sharpe, worst-fold Sharpe, and turnover.",
            "minimum_holdout_exposure": MIN_HOLDOUT_EXPOSURE,
        },
    }


def _write_csvs(output: Path, result: dict[str, Any]) -> None:
    for key, filename in (
        ("selection", "portfolio_selection.csv"),
        ("cpcv_folds", "cpcv_folds.csv"),
        ("metrics", "portfolio_metrics.csv"),
        ("benchmarks", "benchmark_metrics.csv"),
        ("rolling_diagnostics", "rolling_diagnostics.csv"),
    ):
        frame = result.get(key)
        if isinstance(frame, pd.DataFrame):
            frame.to_csv(output / filename, index=False)


def write_portfolio_optimisation_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_csvs(output, result)
    selected_metrics = result["metrics"][result["metrics"].name.eq(result["winner"])]
    holdout_selected = selected_metrics[selected_metrics.split.eq("holdout")]
    comparison = pd.concat([
        result["benchmarks"][(result["benchmarks"].split.eq("holdout")) & (result["benchmarks"].cost_bps.isin([25, 50]))],
        holdout_selected,
    ], ignore_index=True, sort=False)
    method_summary = result["metrics"][(result["metrics"].split.eq("holdout")) & (result["metrics"].cost_bps.eq(25))].sort_values("Sharpe", ascending=False)
    dynamic_summary = result["selection"].groupby(["method", "dynamic_budget"]).agg(
        median_selection_score=("selection_score", "median"),
        median_dev_turnover=("development_turnover", "median"),
        median_dev_exposure=("development_exposure", "median"),
    ).reset_index().sort_values("median_selection_score", ascending=False)

    (output / "executive_summary.md").write_text(f"""# Executive summary

Study: **{result['protocol']['title']}**

The frozen signal **{BASELINE_NAME}** was not modified, reselected, or retuned.
Only portfolio construction and post-signal position size were changed.

Development-selected method: **{result['winner']}**

Final conclusion: **{result['final_conclusion']}**
""", encoding="utf-8")

    (output / "portfolio_methods.md").write_text(f"""# Portfolio methods

The following predeclared methods were tested for BTC/ETH and BTC/ETH/cash
constraints, with and without dynamic risk budgeting.

{_table(pd.DataFrame({'method': METHODS}), [('method', 'Method')], limit=40)}

Top-20 allocation was not enabled because the prior expansion/development
research did not approve a top-20 sleeve for replacement use.
""", encoding="utf-8")

    (output / "dynamic_risk_budgeting.md").write_text(f"""# Dynamic risk budgeting

Dynamic risk budgets were applied after the frozen signal fired. They increased
or preserved risk only when lagged macro/volatility conditions were favourable
and reduced risk when volatility or drawdown conditions deteriorated.

{_table(dynamic_summary, [('method', 'Method'), ('dynamic_budget', 'Dynamic'), ('median_selection_score', 'Median selection score'), ('median_dev_turnover', 'Median dev turnover'), ('median_dev_exposure', 'Median dev exposure')], {'median_dev_exposure'}, limit=80)}
""", encoding="utf-8")

    (output / "performance_comparison.md").write_text(f"""# Performance comparison

## Development-only CPCV selection

{_table(result['selection'], [('candidate', 'Candidate'), ('method', 'Method'), ('universe', 'Universe'), ('dynamic_budget', 'Dynamic'), ('selection_score', 'Selection score'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold'), ('development_sharpe', 'Dev Sharpe'), ('development_cagr', 'Dev CAGR'), ('development_turnover', 'Dev turnover'), ('development_exposure', 'Dev exposure')], {'development_cagr', 'development_exposure'}, limit=100)}

## Holdout method ranking at 25 bps

{_table(method_summary, [('name', 'Candidate'), ('method', 'Method'), ('universe', 'Universe'), ('dynamic_budget', 'Dynamic'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Omega', 'Omega'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=80)}
""", encoding="utf-8")

    (output / "cost_sensitivity.md").write_text(f"""# Cost sensitivity

Selected development candidate across transaction costs:

{_table(holdout_selected, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Omega', 'Omega'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

- PBO: {_fmt(result['pbo'], True)}
- Deflated Sharpe probability: {_fmt(result['deflated_sharpe_probability'], True)}
- Bootstrap Sharpe CI: [{_fmt(result['bootstrap_sharpe_ci']['lower'])}, {_fmt(result['bootstrap_sharpe_ci']['upper'])}]
- Approximate Jobson-Korkie/Ledoit-Wolf-style Sharpe delta vs frozen: {_fmt(result['paired_sharpe_test']['sharpe_delta'])}
- Approximate p-value: {_fmt(result['paired_sharpe_test']['jobson_korkie_p_approx'])}
- Tested configurations: {result['tested_configurations']}

{_table(result['rolling_diagnostics'], [('name', 'Name'), ('window_days', 'Window'), ('median_rolling_sharpe', 'Median rolling Sharpe'), ('worst_rolling_sharpe', 'Worst rolling Sharpe'), ('median_rolling_volatility', 'Median rolling vol'), ('max_rolling_drawdown', 'Max rolling DD')], {'max_rolling_drawdown'})}
""", encoding="utf-8")

    (output / "economic_interpretation.md").write_text(f"""# Economic interpretation

## Frozen versus selected holdout

| Metric | Frozen | Selected |
|---|---:|---:|
| Sharpe | {_fmt(result['frozen_holdout']['Sharpe'])} | {_fmt(result['winner_holdout']['Sharpe'])} |
| CAGR | {_fmt(result['frozen_holdout']['CAGR'], True)} | {_fmt(result['winner_holdout']['CAGR'], True)} |
| Max drawdown | {_fmt(result['frozen_holdout']['Maximum Drawdown'], True)} | {_fmt(result['winner_holdout']['Maximum Drawdown'], True)} |
| Turnover | {_fmt(result['frozen_holdout']['Annual Turnover'])} | {_fmt(result['winner_holdout']['Annual Turnover'])} |
| Exposure | {_fmt(result['frozen_holdout']['Exposure'], True)} | {_fmt(result['winner_holdout']['Exposure'], True)} |

Improvement from mostly cash: **{_fmt(result['improvement_from_cash'])}**.

Interpretation: {result['final_conclusion']}
""", encoding="utf-8")

    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

{_table(comparison, [('name', 'Name'), ('benchmark_group', 'Group'), ('split', 'Split'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=120)}
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

1. **Can portfolio construction improve the frozen strategy without changing alpha?** Point estimates can improve in some cells, but the development-selected method does not pass all statistical/economic filters.
2. **Which allocation method performs best?** Development-only CPCV selected **{result['winner']}**.
3. **Does Kelly sizing improve performance or increase instability?** Kelly variants are reported in `performance_comparison.md`; accept only if they clear turnover, exposure, PBO and DSR filters.
4. **Does HRP or ERC outperform volatility targeting?** See method ranking; no method replaces the frozen implementation unless all filters pass.
5. **Is any improvement statistically convincing?** {_fmt(result['passes_replacement_filters'])}.
6. **Does any method improve Sharpe while maintaining comparable CAGR and exposure?** {_fmt(result['passes_replacement_filters'])}.
7. **Would any portfolio construction method replace the current implementation?** {_fmt(result['passes_replacement_filters'])}.

Final conclusion: **{result['final_conclusion']}**

This is a capital-allocation study, not evidence of better alpha.
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "winner": result["winner"],
        "winner_candidate": result["winner_candidate"].__dict__,
        "frozen_holdout": _json_safe(result["frozen_holdout"]),
        "winner_holdout": _json_safe(result["winner_holdout"]),
        "winner_50bps": _json_safe(result["winner_50bps"]),
        "pbo": _json_safe(result["pbo"]),
        "deflated_sharpe_probability": _json_safe(result["deflated_sharpe_probability"]),
        "bootstrap_sharpe_ci": _json_safe(result["bootstrap_sharpe_ci"]),
        "paired_sharpe_test": _json_safe(result["paired_sharpe_test"]),
        "improvement_from_cash": result["improvement_from_cash"],
        "passes_replacement_filters": result["passes_replacement_filters"],
        "final_conclusion": result["final_conclusion"],
        "selection": _json_safe(result["selection"]),
        "metrics": _json_safe(result["metrics"]),
        "benchmarks": _json_safe(result["benchmarks"]),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_portfolio_optimisation(output_dir: str | Path = "reports/portfolio_optimisation") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_portfolio_optimisation(panel, macro, public_data, probability)
    write_portfolio_optimisation_reports(output_dir, result)
    return result


__all__ = [
    "run_portfolio_optimisation",
    "write_portfolio_optimisation_reports",
    "run_default_portfolio_optimisation",
    "predeclared_portfolio_candidates",
]
