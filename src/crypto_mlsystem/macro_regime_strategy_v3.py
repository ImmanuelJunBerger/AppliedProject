"""Simplified macro-regime gates for the fixed BTC/ETH/cash strategy family.

This module does not search for unrelated strategies.  It compares a small,
predeclared set of interpretable macro gates against the existing
``btc_eth_macro_gate_balanced`` strategy.  Selection uses development-period
CPCV only.  Holdout metrics are generated only after selection for validation
and interpretation.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .macro_regime_benchmark_analysis import (
    FIXED_SELECTED,
    load_default_inputs,
    run_macro_regime_benchmark_analysis,
)
from .macro_regime_strategy import (
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
    portfolio_metrics,
)
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import (
    block_bootstrap_sharpe_ci,
    deflated_sharpe_probability,
    probability_backtest_overfitting,
)


CURRENT_STRATEGY_PBO_REFERENCE = 0.6143


@dataclass(frozen=True)
class GateFeature:
    name: str
    direction: str  # "high" or "low"
    rationale: str


@dataclass(frozen=True)
class SimplifiedMacroGateCandidate:
    name: str
    label: str
    features: tuple[GateFeature, ...]
    risk_on_votes: int
    neutral_votes: int
    economic_interpretation: str
    is_current_strategy: bool = False
    turnover_cap: float = 0.75

    @property
    def feature_count(self) -> int:
        return len(self.features)


def predeclared_simplified_macro_candidates() -> list[SimplifiedMacroGateCandidate]:
    """Return the five user-specified simplified/current macro-gate variants."""
    equity_momentum = GateFeature(
        "equity_momentum_21d",
        "high",
        "Positive equity momentum proxies broader risk appetite.",
    )
    return [
        SimplifiedMacroGateCandidate(
            name="simple_vix_level_equity_momentum",
            label="A. VIX level + equity momentum",
            features=(
                GateFeature("vix_level", "low", "Lower VIX indicates calmer cross-asset risk conditions."),
                equity_momentum,
            ),
            risk_on_votes=2,
            neutral_votes=1,
            economic_interpretation="Risk-on only when equity trend is positive and VIX is not elevated.",
        ),
        SimplifiedMacroGateCandidate(
            name="simple_vix_change_equity_momentum",
            label="B. VIX change + equity momentum",
            features=(
                GateFeature("vix_change_5d", "low", "Falling or non-rising short VIX change indicates easing stress."),
                GateFeature("vix_change_21d", "low", "Falling or non-rising monthly VIX change indicates easing stress."),
                equity_momentum,
            ),
            risk_on_votes=2,
            neutral_votes=1,
            economic_interpretation="Risk-on when volatility stress is not accelerating and equity trend is positive.",
        ),
        SimplifiedMacroGateCandidate(
            name="simple_equity_vol_equity_momentum",
            label="C. Equity realized volatility + equity momentum",
            features=(
                GateFeature("equity_realized_vol_21d", "low", "Lower equity realized volatility indicates calmer risk conditions."),
                equity_momentum,
            ),
            risk_on_votes=2,
            neutral_votes=1,
            economic_interpretation="Risk-on only when equity trend is positive and realized equity volatility is contained.",
        ),
        SimplifiedMacroGateCandidate(
            name="simple_vix_level_change_equity_momentum",
            label="D. VIX level + VIX change + equity momentum",
            features=(
                GateFeature("vix_level", "low", "Lower VIX indicates calmer cross-asset risk conditions."),
                GateFeature("vix_change_5d", "low", "Short-term VIX stress should not be rising."),
                GateFeature("vix_change_21d", "low", "Monthly VIX stress should not be rising."),
                equity_momentum,
            ),
            risk_on_votes=3,
            neutral_votes=2,
            economic_interpretation="Risk-on when equity trend is positive and both VIX level/change confirm a benign macro regime.",
        ),
        SimplifiedMacroGateCandidate(
            name=FIXED_SELECTED.name,
            label="E. Full current strategy",
            features=(
                GateFeature("equity_realized_vol_21d", "high", "Current empirical gate orientation from prior module."),
                equity_momentum,
                GateFeature("dow_vol_level", "high", "Current empirical gate orientation from prior module."),
                GateFeature("vix_level", "high", "Current empirical gate orientation from prior module."),
                GateFeature("vix_change_5d", "low", "Current empirical gate orientation from prior module."),
                GateFeature("vix_change_21d", "low", "Current empirical gate orientation from prior module."),
            ),
            risk_on_votes=4,
            neutral_votes=3,
            economic_interpretation="Existing balanced six-feature empirical macro gate.",
            is_current_strategy=True,
            turnover_cap=FIXED_SELECTED.turnover_cap,
        ),
    ]


def _development_thresholds(dataset: MacroRegimeDataset, candidate: SimplifiedMacroGateCandidate) -> dict[str, float]:
    if candidate.is_current_strategy:
        return dict(dataset.thresholds[FIXED_SELECTED.gate_profile]["thresholds"])
    development = dataset.regime_features.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    return {
        feature.name: float(development[feature.name].median())
        for feature in candidate.features
        if feature.name in development
    }


def _classify_simple_regime(
    dataset: MacroRegimeDataset,
    candidate: SimplifiedMacroGateCandidate,
) -> tuple[pd.Series, pd.Series, pd.Series, dict[str, float]]:
    thresholds = _development_thresholds(dataset, candidate)
    votes = pd.Series(0.0, index=dataset.regime_features.index)
    for feature in candidate.features:
        if feature.name not in dataset.regime_features or feature.name not in thresholds:
            continue
        values = dataset.regime_features[feature.name]
        threshold = thresholds[feature.name]
        if feature.direction == "high":
            votes += (values >= threshold).fillna(False).astype(float)
        elif feature.direction == "low":
            votes += (values <= threshold).fillna(False).astype(float)
        else:
            raise ValueError(f"Unknown feature direction: {feature.direction}")
    regime = pd.Series("risk_off", index=votes.index, dtype=object)
    regime.loc[votes >= candidate.neutral_votes] = "neutral"
    regime.loc[votes >= candidate.risk_on_votes] = "risk_on"
    crypto = pd.Series("not_used", index=regime.index, dtype=object)
    return regime, crypto, regime.copy(), thresholds


def _rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(index[index.weekday == 4])
    return dates if len(dates) else pd.DatetimeIndex(index[::7])


def _btc_eth_weights_from_regime(dataset: MacroRegimeDataset, regimes: pd.Series) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    for date in dates:
        regime = regimes.reindex([date]).ffill().iloc[0] if date in regimes.index else "risk_off"
        if regime == "risk_off":
            continue
        exposure = 1.0 if regime == "risk_on" else 0.50
        eligible = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        assets = [symbol for symbol in ("BTC", "ETH") if symbol in weights.columns and symbol in eligible]
        if assets:
            weights.loc[date, assets] = min(0.50, exposure / len(assets))
    return weights


def build_simplified_candidate(
    dataset: MacroRegimeDataset,
    candidate: SimplifiedMacroGateCandidate,
    cost_bps: int = 25,
) -> tuple[PortfolioResult, pd.DataFrame, pd.Series, pd.Series, pd.Series, dict[str, float]]:
    if candidate.is_current_strategy:
        weights, macro, crypto, combined = build_candidate_weights(dataset, FIXED_SELECTED)
        thresholds = _development_thresholds(dataset, candidate)
    else:
        macro, crypto, combined, thresholds = _classify_simple_regime(dataset, candidate)
        weights = _btc_eth_weights_from_regime(dataset, combined)
    result = backtest_weights(
        dataset,
        weights,
        macro,
        crypto,
        combined,
        cost_bps=cost_bps,
        turnover_cap=candidate.turnover_cap,
    )
    return result, weights, macro, crypto, combined, thresholds


def _weekly_return(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0).dropna()


def _period_sharpe(values: pd.Series, indices: tuple[int, ...]) -> float:
    subset = values.iloc[list(indices)].replace([np.inf, -np.inf], np.nan).dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def _selection_penalty_score(row: dict[str, Any]) -> float:
    """Development-only robustness score with explicit simplicity penalties."""
    turnover_penalty = max(0.0, row["development_turnover"] - 10.0) * 0.05
    score = (
        row["median_fold_sharpe"]
        + 0.30 * row["worst_fold_sharpe"]
        + 0.75 * row["positive_fold_fraction"]
        - 0.10 * row["feature_count"]
        - 0.20 * row["fold_sharpe_std"]
        - 0.15 * max(0.0, row["cpcv_train_test_decay"])
        - 0.50 * row["development_exposure_std"]
        - turnover_penalty
    )
    return float(score)


def select_simplified_candidate_cpcv(
    candidates: list[SimplifiedMacroGateCandidate],
    results: dict[str, PortfolioResult],
) -> tuple[pd.DataFrame, pd.DataFrame, str, float, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    config_returns: dict[str, pd.Series] = {}
    for candidate in candidates:
        result = results[candidate.name]
        weekly = _weekly_return(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        config_returns[candidate.name] = weekly
        if len(weekly) < 20:
            continue
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        test_sharpes = []
        train_sharpes = []
        for number, split in enumerate(splits):
            test_sharpe = _period_sharpe(weekly, split.test_indices)
            train_sharpe = _period_sharpe(weekly, split.train_indices)
            test_sharpes.append(test_sharpe)
            train_sharpes.append(train_sharpe)
            fold_rows.append({
                "candidate": candidate.name,
                "fold": number,
                "test_groups": ",".join(str(group) for group in split.test_groups),
                "train_sharpe": train_sharpe,
                "fold_sharpe": test_sharpe,
                "train_test_decay": train_sharpe - test_sharpe if np.isfinite(train_sharpe) and np.isfinite(test_sharpe) else np.nan,
            })
        fold_values = np.asarray(test_sharpes, dtype=float)
        train_values = np.asarray(train_sharpes, dtype=float)
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        dev_exposure = result.weights.sum(axis=1).loc[DEVELOPMENT_START:DEVELOPMENT_END].clip(0.0, 1.0)
        row = {
            "candidate": candidate.name,
            "label": candidate.label,
            "feature_count": candidate.feature_count,
            "features": ", ".join(feature.name for feature in candidate.features),
            "economic_interpretation": candidate.economic_interpretation,
            "is_current_strategy": candidate.is_current_strategy,
            "median_fold_sharpe": float(np.nanmedian(fold_values)),
            "worst_fold_sharpe": float(np.nanmin(fold_values)),
            "best_fold_sharpe": float(np.nanmax(fold_values)),
            "fold_sharpe_std": float(np.nanstd(fold_values)),
            "positive_fold_fraction": float(np.nanmean(fold_values > 0)),
            "median_train_sharpe": float(np.nanmedian(train_values)),
            "cpcv_train_test_decay": float(np.nanmedian(train_values) - np.nanmedian(fold_values)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
            "development_exposure_std": float(dev_exposure.std()) if len(dev_exposure) else np.nan,
            "turnover_below_10x": bool(dev["Annual Turnover"] <= 10.0),
        }
        row["selection_score"] = _selection_penalty_score(row)
        rows.append(row)
    selection = pd.DataFrame(rows).sort_values(
        ["selection_score", "median_fold_sharpe", "worst_fold_sharpe", "feature_count"],
        ascending=[False, False, False, True],
    )
    winner = str(selection.iloc[0].candidate)
    aligned = pd.concat(config_returns, axis=1).sort_index()
    pbo = probability_backtest_overfitting(aligned, blocks=8)
    return selection, pd.DataFrame(fold_rows), winner, pbo, aligned


def _development_holdout_table(
    candidates: list[SimplifiedMacroGateCandidate],
    results: dict[str, PortfolioResult],
) -> pd.DataFrame:
    rows = []
    for candidate in candidates:
        dev = period_metrics(results[candidate.name], DEVELOPMENT_START, DEVELOPMENT_END)
        hold = period_metrics(results[candidate.name], HOLDOUT_START, HOLDOUT_END)
        sharpe_retention = hold["Sharpe"] / dev["Sharpe"] if dev["Sharpe"] else np.nan
        cagr_retention = hold["CAGR"] / dev["CAGR"] if dev["CAGR"] else np.nan
        rows.append({
            "candidate": candidate.name,
            "label": candidate.label,
            "feature_count": candidate.feature_count,
            "development_sharpe": dev["Sharpe"],
            "holdout_sharpe": hold["Sharpe"],
            "sharpe_retention": sharpe_retention,
            "development_cagr": dev["CAGR"],
            "holdout_cagr": hold["CAGR"],
            "cagr_retention": cagr_retention,
            "development_max_drawdown": dev["Maximum Drawdown"],
            "holdout_max_drawdown": hold["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "holdout_turnover": hold["Annual Turnover"],
            "development_exposure": dev["Exposure"],
            "holdout_exposure": hold["Exposure"],
            "development_sharpe_higher_than_holdout": bool(dev["Sharpe"] >= hold["Sharpe"]),
            "retains_at_least_70pct_sharpe": bool(np.isfinite(sharpe_retention) and sharpe_retention >= 0.70),
            "both_cagr_positive": bool(dev["CAGR"] > 0 and hold["CAGR"] > 0),
        })
    return pd.DataFrame(rows)


def _regime_stability_table(
    candidates: list[SimplifiedMacroGateCandidate],
    results: dict[str, PortfolioResult],
) -> pd.DataFrame:
    periods = (
        ("2020_2021_bull", pd.Timestamp("2020-01-01"), pd.Timestamp("2021-12-31")),
        ("2022_bear", pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")),
        ("2023_2024_recovery", pd.Timestamp("2023-01-01"), pd.Timestamp("2024-12-31")),
        ("2025_2026_holdout", HOLDOUT_START, HOLDOUT_END),
    )
    rows = []
    for candidate in candidates:
        for period, start, end in periods:
            metrics = period_metrics(results[candidate.name], start, end)
            rows.append({
                "candidate": candidate.name,
                "period": period,
                "CAGR": metrics["CAGR"],
                "Sharpe": metrics["Sharpe"],
                "Maximum Drawdown": metrics["Maximum Drawdown"],
                "Calmar": metrics["Calmar"],
                "Annual Turnover": metrics["Annual Turnover"],
                "Exposure": metrics["Exposure"],
                "positive_cagr": bool(metrics["CAGR"] > 0),
            })
    frame = pd.DataFrame(rows)
    positive_counts = frame.groupby("candidate").positive_cagr.sum().rename("positive_regime_count")
    frame = frame.merge(positive_counts, on="candidate", how="left")
    return frame


def _cost_sensitivity(
    dataset: MacroRegimeDataset,
    candidate: SimplifiedMacroGateCandidate,
) -> pd.DataFrame:
    rows = []
    for cost in COST_LEVELS:
        result, *_ = build_simplified_candidate(dataset, candidate, cost_bps=cost)
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            rows.append({
                "candidate": candidate.name,
                "split": split,
                "cost_bps": cost,
                **period_metrics(result, start, end),
            })
    return pd.DataFrame(rows)


def _benchmark_comparison(
    selected_name: str,
    selected_result: PortfolioResult,
    benchmark_result: dict[str, Any],
) -> pd.DataFrame:
    selected_rows = []
    for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
        selected_rows.append({
            "name": selected_name,
            "category": "v3_selected_simplified",
            "split": split,
            "cost_bps": 25,
            **period_metrics(selected_result, start, end),
        })
    selected_frame = pd.DataFrame(selected_rows)
    benchmark_metrics = benchmark_result["metrics"].copy()
    wanted = {
        FIXED_SELECTED.name,
        "btc_buy_hold",
        "eth_buy_hold",
        "btc_eth_50_50",
        "equal_weight_top10",
    }
    prior = benchmark_metrics[benchmark_metrics.benchmark_group.eq("prior_tier1_regime_momentum")].name.unique().tolist()
    wanted.update(prior)
    filtered = benchmark_metrics[
        benchmark_metrics.name.isin(wanted)
        & benchmark_metrics.split.isin(["development", "holdout"])
        & benchmark_metrics.cost_bps.eq(25)
    ].copy()
    filtered["category"] = filtered.get("benchmark_group", "benchmark")
    return pd.concat([selected_frame, filtered], ignore_index=True, sort=False)


def _statistics_table(
    candidates: list[SimplifiedMacroGateCandidate],
    results: dict[str, PortfolioResult],
    folds: pd.DataFrame,
    pbo: float,
) -> pd.DataFrame:
    rows = []
    for candidate in candidates:
        holdout_returns = results[candidate.name].returns.loc[HOLDOUT_START:HOLDOUT_END]
        ci = block_bootstrap_sharpe_ci(holdout_returns, samples=500, block_length=14, seed=42)
        candidate_folds = folds[folds.candidate == candidate.name]
        rows.append({
            "candidate": candidate.name,
            "tested_configurations": len(candidates),
            "family_pbo": pbo,
            "current_strategy_pbo_reference": CURRENT_STRATEGY_PBO_REFERENCE if candidate.name == FIXED_SELECTED.name else np.nan,
            "deflated_sharpe_probability": deflated_sharpe_probability(holdout_returns, tested_configurations=len(candidates)),
            "bootstrap_sharpe_lower": ci["lower"],
            "bootstrap_sharpe_median": ci["median"],
            "bootstrap_sharpe_upper": ci["upper"],
            "best_fold_sharpe": float(candidate_folds.fold_sharpe.max()) if not candidate_folds.empty else np.nan,
            "median_fold_sharpe": float(candidate_folds.fold_sharpe.median()) if not candidate_folds.empty else np.nan,
            "worst_fold_sharpe": float(candidate_folds.fold_sharpe.min()) if not candidate_folds.empty else np.nan,
            "positive_fold_fraction": float((candidate_folds.fold_sharpe > 0).mean()) if not candidate_folds.empty else np.nan,
        })
    return pd.DataFrame(rows)


def _recommendation(
    winner: SimplifiedMacroGateCandidate,
    dev_holdout: pd.DataFrame,
    statistics: pd.DataFrame,
) -> dict[str, Any]:
    selected_row = dev_holdout[dev_holdout.candidate == winner.name].iloc[0]
    current_row = dev_holdout[dev_holdout.candidate == FIXED_SELECTED.name].iloc[0]
    selected_stats = statistics[statistics.candidate == winner.name].iloc[0]
    selected_consistent = bool(
        selected_row.development_sharpe_higher_than_holdout
        and selected_row.retains_at_least_70pct_sharpe
        and selected_row.both_cagr_positive
        and selected_row.holdout_sharpe > 0.5
        and selected_row.holdout_max_drawdown > -0.35
    )
    lower_pbo_family = bool(
        np.isfinite(selected_stats.family_pbo)
        and selected_stats.family_pbo < CURRENT_STRATEGY_PBO_REFERENCE
    )
    if winner.name != FIXED_SELECTED.name and selected_consistent and lower_pbo_family:
        decision = "replace with simpler lower-PBO strategy"
        reason = (
            "The development-selected simplified gate satisfies the consistency screen, "
            "keeps positive development and holdout performance, and the restricted "
            "candidate family has lower PBO than the previous broad selection."
        )
    elif current_row.holdout_sharpe > 0.5 and current_row.holdout_cagr > 0:
        decision = "keep current strategy"
        reason = (
            "The simplified development-selected gate does not clear every robustness "
            "condition strongly enough to replace the existing fixed strategy. Keep the "
            "current strategy as paper-monitoring only, while recognizing its high PBO."
        )
    else:
        decision = "reject both because robustness is insufficient"
        reason = (
            "Neither the current nor simplified candidate gives enough robustness evidence "
            "to justify paper-trading promotion."
        )
    return {
        "development_selected_candidate": winner.name,
        "decision": decision,
        "reason": reason,
        "selected_consistency_screen_passes": selected_consistent,
        "restricted_family_pbo_below_current_reference": lower_pbo_family,
    }


def run_macro_regime_strategy_v3(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    candidates = predeclared_simplified_macro_candidates()
    results: dict[str, PortfolioResult] = {}
    weights: dict[str, pd.DataFrame] = {}
    thresholds: dict[str, dict[str, float]] = {}
    for candidate in candidates:
        result, target_weights, *_rest, candidate_thresholds = build_simplified_candidate(dataset, candidate, cost_bps=25)
        results[candidate.name] = result
        weights[candidate.name] = target_weights
        thresholds[candidate.name] = candidate_thresholds

    selection, folds, winner_name, pbo, aligned_development_returns = select_simplified_candidate_cpcv(candidates, results)
    by_name = {candidate.name: candidate for candidate in candidates}
    winner = by_name[winner_name]
    dev_holdout = _development_holdout_table(candidates, results)
    stability = _regime_stability_table(candidates, results)
    statistics = _statistics_table(candidates, results, folds, pbo)
    cost_sensitivity = _cost_sensitivity(dataset, winner)
    benchmark_result = run_macro_regime_benchmark_analysis(panel, macro_features, public_data, volatility_probability)
    benchmarks = _benchmark_comparison(winner.name, results[winner.name], benchmark_result)
    recommendation = _recommendation(winner, dev_holdout, statistics)
    return {
        "dataset": dataset,
        "candidates": candidates,
        "winner": winner,
        "results": results,
        "weights": weights,
        "thresholds": thresholds,
        "selection": selection,
        "folds": folds,
        "aligned_development_returns": aligned_development_returns,
        "development_holdout": dev_holdout,
        "regime_stability": stability,
        "statistics": statistics,
        "cost_sensitivity": cost_sensitivity,
        "benchmark_comparison": benchmarks,
        "recommendation": recommendation,
        "protocol": {
            "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} to {HOLDOUT_END.date()}",
            "candidate_count": len(candidates),
            "candidate_scope": "Only four simplified macro gates plus the current btc_eth_macro_gate_balanced strategy.",
            "selection_inputs": (
                "Development-only CPCV median Sharpe, worst-fold Sharpe, positive-fold fraction, "
                "fold instability, CPCV train/test decay proxy, feature count, turnover, and exposure stability."
            ),
            "holdout_use": "Holdout is used only after selection for validation and reporting.",
        },
    }


def write_macro_regime_strategy_v3_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    selection = result["selection"]
    folds = result["folds"]
    dev_holdout = result["development_holdout"]
    stability = result["regime_stability"]
    statistics = result["statistics"]
    benchmarks = result["benchmark_comparison"]
    costs = result["cost_sensitivity"]
    recommendation = result["recommendation"]
    winner: SimplifiedMacroGateCandidate = result["winner"]
    thresholds = pd.DataFrame([
        {"candidate": name, "feature": feature, "threshold": value}
        for name, mapping in result["thresholds"].items()
        for feature, value in mapping.items()
    ])
    candidate_specs = pd.DataFrame([
        {
            "candidate": candidate.name,
            "label": candidate.label,
            "features": ", ".join(f"{feature.name}:{feature.direction}" for feature in candidate.features),
            "feature_count": candidate.feature_count,
            "risk_on_votes": candidate.risk_on_votes,
            "neutral_votes": candidate.neutral_votes,
            "economic_interpretation": candidate.economic_interpretation,
            "is_current_strategy": candidate.is_current_strategy,
        }
        for candidate in result["candidates"]
    ])
    selection.to_csv(output / "selection_scores.csv", index=False)
    folds.to_csv(output / "cpcv_folds.csv", index=False)
    dev_holdout.to_csv(output / "development_vs_holdout.csv", index=False)
    stability.to_csv(output / "regime_stability.csv", index=False)
    statistics.to_csv(output / "statistics.csv", index=False)
    benchmarks.to_csv(output / "benchmark_comparison.csv", index=False)
    costs.to_csv(output / "cost_sensitivity.csv", index=False)
    thresholds.to_csv(output / "gate_thresholds.csv", index=False)
    candidate_specs.to_csv(output / "candidate_specs.csv", index=False)

    selection_text = _table(
        selection,
        [
            ("candidate", "Candidate"),
            ("feature_count", "Features"),
            ("selection_score", "Selection score"),
            ("median_fold_sharpe", "Median CPCV Sharpe"),
            ("worst_fold_sharpe", "Worst fold"),
            ("positive_fold_fraction", "Positive folds"),
            ("development_turnover", "Dev turnover"),
            ("development_exposure_std", "Exposure stability penalty"),
            ("cpcv_train_test_decay", "CPCV train/test decay proxy"),
        ],
        {"positive_fold_fraction"},
    )
    (output / "simplification_results.md").write_text(f"""# Macro-regime strategy v3 simplification results

## Scope

This module does not search for a new unrelated strategy. It tests only four
small, interpretable macro-gate variants plus the existing
`{FIXED_SELECTED.name}` strategy.

Holdout was not used for candidate selection. Selection uses development-only
CPCV and an explicit complexity/stability penalty.

## Candidate specifications

{_table(candidate_specs, [('candidate', 'Candidate'), ('label', 'Label'), ('features', 'Features'), ('feature_count', 'Feature count'), ('risk_on_votes', 'Risk-on votes'), ('neutral_votes', 'Neutral votes'), ('economic_interpretation', 'Economic interpretation')])}

## Development-only selection score

{selection_text}

## Selected by development-only CPCV

Selected candidate: **{winner.name}**

Selection inputs: {result['protocol']['selection_inputs']}

Actual holdout decay is reported separately and was not used in the selection score.
""", encoding="utf-8")

    (output / "development_vs_holdout.md").write_text(f"""# Development vs holdout consistency

The table below is validation reporting only. It was not used to choose the v3
candidate.

{_table(dev_holdout, [('candidate', 'Candidate'), ('development_sharpe', 'Dev Sharpe'), ('holdout_sharpe', 'Holdout Sharpe'), ('sharpe_retention', 'Sharpe retention'), ('development_cagr', 'Dev CAGR'), ('holdout_cagr', 'Holdout CAGR'), ('cagr_retention', 'CAGR retention'), ('development_max_drawdown', 'Dev max DD'), ('holdout_max_drawdown', 'Holdout max DD'), ('development_turnover', 'Dev turnover'), ('holdout_turnover', 'Holdout turnover'), ('development_exposure', 'Dev exposure'), ('holdout_exposure', 'Holdout exposure'), ('development_sharpe_higher_than_holdout', 'Dev Sharpe >= holdout'), ('retains_at_least_70pct_sharpe', 'Retains >=70%'), ('both_cagr_positive', 'Both CAGR positive')], {'sharpe_retention', 'development_cagr', 'holdout_cagr', 'cagr_retention', 'development_max_drawdown', 'holdout_max_drawdown', 'development_exposure', 'holdout_exposure'})}

Preferred consistency profile:

- development Sharpe above holdout Sharpe;
- holdout retains at least 70% of development Sharpe;
- development and holdout CAGR are both positive;
- drawdown is controlled in both periods.
""", encoding="utf-8")

    (output / "regime_stability.md").write_text(f"""# Regime stability

Positive performance across regimes is more important here than maximizing
holdout Sharpe. Subperiod performance is reported for all candidates.

{_table(stability, [('candidate', 'Candidate'), ('period', 'Period'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure'), ('positive_cagr', 'Positive CAGR'), ('positive_regime_count', 'Positive regime count')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}
""", encoding="utf-8")

    selected_stats = statistics[statistics.candidate == winner.name].iloc[0]
    selected_consistency = dev_holdout[dev_holdout.candidate == winner.name].iloc[0]
    current_consistency = dev_holdout[dev_holdout.candidate == FIXED_SELECTED.name].iloc[0]
    (output / "pbo_and_statistics.md").write_text(f"""# PBO and statistical controls

## Family-level controls

- Tested configurations: {len(result['candidates'])}.
- Restricted-family PBO: {_fmt(selected_stats.family_pbo, True)}.
- Prior current-strategy PBO reference from the broader macro-regime search: {_fmt(CURRENT_STRATEGY_PBO_REFERENCE, True)}.
- Selected deflated Sharpe probability: {_fmt(selected_stats.deflated_sharpe_probability, True)}
- Selected bootstrap Sharpe CI: [{_fmt(selected_stats.bootstrap_sharpe_lower)}, {_fmt(selected_stats.bootstrap_sharpe_upper)}]

The PBO reported here is a family-level statistic for this restricted five-gate
experiment. It is not candidate-specific. The lower PBO mainly reflects the
smaller, predeclared candidate set; it does not rescue a simplified candidate
that fails the locked holdout.

## Candidate statistics

{_table(statistics, [('candidate', 'Candidate'), ('family_pbo', 'Family PBO'), ('deflated_sharpe_probability', 'Deflated Sharpe probability'), ('bootstrap_sharpe_lower', 'Bootstrap lower'), ('bootstrap_sharpe_median', 'Bootstrap median'), ('bootstrap_sharpe_upper', 'Bootstrap upper'), ('best_fold_sharpe', 'Best fold'), ('median_fold_sharpe', 'Median fold'), ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds')], {'family_pbo', 'deflated_sharpe_probability', 'positive_fold_fraction'})}

## CPCV fold distribution

{_table(folds, [('candidate', 'Candidate'), ('fold', 'Fold'), ('test_groups', 'Test groups'), ('train_sharpe', 'Train Sharpe'), ('fold_sharpe', 'Fold Sharpe'), ('train_test_decay', 'Train/test decay')], limit=40)}
""", encoding="utf-8")

    holdout_bench = benchmarks[benchmarks.split.eq("holdout")].sort_values("Sharpe", ascending=False)
    selected_costs = costs[costs.split.eq("holdout")]
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Decision

**{recommendation['decision']}**

Development-selected candidate: **{recommendation['development_selected_candidate']}**

Reason: {recommendation['reason']}

## Development-selected simplified candidate check

The development-only selector chose **{winner.name}**, but it failed the locked
holdout validation:

- Development Sharpe: {_fmt(selected_consistency.development_sharpe)}
- Holdout Sharpe: {_fmt(selected_consistency.holdout_sharpe)}
- Sharpe retention: {_fmt(selected_consistency.sharpe_retention, True)}
- Development CAGR: {_fmt(selected_consistency.development_cagr, True)}
- Holdout CAGR: {_fmt(selected_consistency.holdout_cagr, True)}

The current strategy remains stronger on validation despite higher known
overfitting concern:

- Current development Sharpe: {_fmt(current_consistency.development_sharpe)}
- Current holdout Sharpe: {_fmt(current_consistency.holdout_sharpe)}
- Current Sharpe retention: {_fmt(current_consistency.sharpe_retention, True)}
- Current holdout CAGR: {_fmt(current_consistency.holdout_cagr, True)}

## Benchmark comparison at 25 bps

{_table(holdout_bench, [('name', 'Strategy'), ('category', 'Category'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure'), ('Worst Month', 'Worst month')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'Worst Month'})}

## Selected candidate cost sensitivity

{_table(selected_costs, [('candidate', 'Candidate'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Interpretation

The v3 process prefers simplicity and CPCV stability over holdout Sharpe. A
simpler candidate should only replace the current strategy if it was selected
inside development, has lower overfitting risk, and remains economically viable
on the locked holdout. No strategy is promoted purely because it has the highest
holdout Sharpe.
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "recommendation": recommendation,
        "winner": asdict(winner),
        "selection": _json_safe(selection.to_dict("records")),
        "development_holdout": _json_safe(dev_holdout.to_dict("records")),
        "regime_stability": _json_safe(stability.to_dict("records")),
        "statistics": _json_safe(statistics.to_dict("records")),
        "benchmark_comparison": _json_safe(benchmarks.to_dict("records")),
        "cost_sensitivity": _json_safe(costs.to_dict("records")),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_macro_regime_strategy_v3(output_dir: str | Path = "reports/macro_regime_strategy_v3") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_macro_regime_strategy_v3(panel, macro, public_data, probability)
    write_macro_regime_strategy_v3_reports(output_dir, result)
    return result


def _fmt(value: Any, percent: bool = False) -> str:
    if value is None or (isinstance(value, (float, np.floating)) and not np.isfinite(value)):
        return "N/A"
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if value else "No"
    if isinstance(value, (float, np.floating)):
        return f"{value:.2%}" if percent else f"{value:.3f}"
    return str(value)


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]], percent: set[str] | None = None, limit: int | None = None) -> str:
    percent = percent or set()
    if frame is None or frame.empty:
        return "_No rows._"
    view = frame.head(limit) if limit else frame
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in view.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, pd.Series):
        return _json_safe(value.to_dict())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value)
    return value


__all__ = [
    "GateFeature",
    "SimplifiedMacroGateCandidate",
    "predeclared_simplified_macro_candidates",
    "run_macro_regime_strategy_v3",
    "write_macro_regime_strategy_v3_reports",
    "run_default_macro_regime_strategy_v3",
]
