"""Economic-value study using a fixed volatility-expansion probability series.

This module never fits, tunes, or recalibrates a prediction model. Portfolio overlay
parameters are selected on development returns with CPCV and frozen before the
locked holdout.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .metrics import performance_metrics
from .signals import SignalBundle, build_signal_bundle


HOLDOUT_START = pd.Timestamp("2025-01-01")
HOLDOUT_END = pd.Timestamp("2026-06-22")
COST_LEVELS = (10, 25, 50, 100)


@dataclass(frozen=True)
class OverlayRule:
    method: str
    floor: float = 1.0
    threshold: float = 0.5
    target_probability: float = 0.5
    low_threshold: float = 0.4
    high_threshold: float = 0.6
    low_regime: str = "trend"


@dataclass
class PortfolioOutcome:
    returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series


@dataclass
class ForecastPortfolioResult:
    metrics: pd.DataFrame
    comparisons: pd.DataFrame
    selection_history: pd.DataFrame
    returns: pd.DataFrame
    bootstrap: pd.DataFrame
    selected_rules: dict[str, OverlayRule]
    protocol: dict[str, Any]


def overlay_candidates(method: str) -> list[OverlayRule]:
    """Small grids declared in code before holdout scoring."""
    if method == "risk_off_sizing":
        return [OverlayRule(method, floor=floor) for floor in (0.25, 0.50, 0.75)]
    if method == "breakout_activation":
        return [OverlayRule(method, threshold=threshold) for threshold in (0.40, 0.50, 0.60)]
    if method == "volatility_targeted_sizing":
        return [
            OverlayRule(method, floor=floor, target_probability=target)
            for floor in (0.25, 0.50)
            for target in (0.40, 0.50, 0.60)
        ]
    if method == "strategy_switching":
        regimes = ((0.35, 0.55), (0.40, 0.60), (0.45, 0.65))
        return [
            OverlayRule(method, low_threshold=low, high_threshold=high, low_regime=low_regime)
            for low, high in regimes
            for low_regime in ("trend", "cash")
        ]
    raise ValueError(f"Unknown overlay method: {method}")


def _forecast_at_rebalances(
    forecast: pd.Series,
    index: pd.DatetimeIndex,
    rebalance_dates: pd.DatetimeIndex,
) -> pd.Series:
    forecast = forecast.sort_index().astype(float).clip(0, 1)
    return forecast.reindex(index).ffill().reindex(rebalance_dates)


def build_overlay_weights(
    bundle: SignalBundle,
    forecast: pd.Series,
    rule: OverlayRule,
    base_strategy: str | None = None,
) -> pd.DataFrame:
    """Apply a fixed forecast as-of each weekly rebalance, then hold weights."""
    breakout = bundle.weights["volatility_breakout"]
    trend = bundle.weights["trend_following"]
    base = bundle.weights.get(base_strategy) if base_strategy else None
    if rule.method != "strategy_switching" and base is None:
        raise ValueError(f"{rule.method} requires a base strategy")
    probabilities = _forecast_at_rebalances(forecast, breakout.index, bundle.rebalance_dates)
    snapshots = pd.DataFrame(np.nan, index=breakout.index, columns=breakout.columns, dtype=float)
    for rebalance_date in bundle.rebalance_dates:
        probability = probabilities.get(rebalance_date, np.nan)
        if pd.isna(probability):
            snapshots.loc[rebalance_date] = 0.0
            continue
        if rule.method == "standalone":
            target = base.loc[rebalance_date]
        elif rule.method == "risk_off_sizing":
            # p=0 retains full exposure; p=1 reaches the selected floor.
            multiplier = rule.floor + (1 - rule.floor) * (1 - probability)
            target = base.loc[rebalance_date] * multiplier
        elif rule.method == "breakout_activation":
            if base_strategy != "volatility_breakout":
                raise ValueError("breakout_activation is defined only for volatility_breakout")
            target = base.loc[rebalance_date] if probability >= rule.threshold else base.loc[rebalance_date] * 0.0
        elif rule.method == "volatility_targeted_sizing":
            # Inverse-probability risk proxy, capped at 1x and bounded by a floor.
            multiplier = np.clip(rule.target_probability / max(probability, 0.05), rule.floor, 1.0)
            target = base.loc[rebalance_date] * multiplier
        elif rule.method == "strategy_switching":
            if probability >= rule.high_threshold:
                target = breakout.loc[rebalance_date]
            elif probability <= rule.low_threshold:
                target = trend.loc[rebalance_date] if rule.low_regime == "trend" else trend.loc[rebalance_date] * 0.0
            else:
                # Medium-risk state: reduced trend exposure, fixed before testing.
                target = trend.loc[rebalance_date] * 0.50
        else:
            raise ValueError(f"Unknown overlay method: {rule.method}")
        snapshots.loc[rebalance_date] = target
    return snapshots.ffill().fillna(0.0)


def build_benchmark_weights(
    bundle: SignalBundle,
    forecast: pd.Series,
    benchmark: str,
) -> pd.DataFrame:
    """Create comparable long-only benchmark weights activated with forecast coverage."""
    template = bundle.asset_returns
    probabilities = _forecast_at_rebalances(forecast, template.index, bundle.rebalance_dates)
    snapshots = pd.DataFrame(np.nan, index=template.index, columns=template.columns, dtype=float)
    for rebalance_date in bundle.rebalance_dates:
        if pd.isna(probabilities.get(rebalance_date, np.nan)):
            snapshots.loc[rebalance_date] = 0.0
            continue
        target = pd.Series(0.0, index=template.columns)
        if benchmark == "btc_buy_hold" and "BTC" in target:
            target.BTC = 1.0
        elif benchmark == "eth_buy_hold" and "ETH" in target:
            target.ETH = 1.0
        elif benchmark == "btc_eth_50_50" and {"BTC", "ETH"}.issubset(target.index):
            target.loc[["BTC", "ETH"]] = 0.50
        elif benchmark == "equal_weight_top10":
            members = bundle.eligible.columns[bundle.eligible.loc[rebalance_date]]
            if len(members):
                target.loc[members] = 1.0 / len(members)
        else:
            if benchmark not in {"btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top10"}:
                raise ValueError(f"Unknown benchmark: {benchmark}")
        snapshots.loc[rebalance_date] = target
    return snapshots.ffill().fillna(0.0)


def execute_asset_weights(bundle: SignalBundle, weights: pd.DataFrame, cost_bps: int) -> PortfolioOutcome:
    weights = weights.reindex_like(bundle.asset_returns).fillna(0.0).clip(lower=0.0)
    gross = (weights.shift(1).fillna(0.0) * bundle.asset_returns).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(weights.abs().sum(axis=1))
    costs = turnover * cost_bps / 10000.0
    return PortfolioOutcome(gross - costs, gross, weights, turnover, costs)


def _period_metrics(outcome: PortfolioOutcome, dates: pd.DatetimeIndex) -> dict[str, float]:
    returns = outcome.returns.reindex(dates)
    metrics = performance_metrics(
        returns,
        outcome.turnover.reindex(dates),
        outcome.costs.reindex(dates),
    )
    metrics["Exposure"] = float((outcome.weights.reindex(dates).sum(axis=1) > 1e-9).mean())
    return metrics


def _sharpe(returns: pd.Series) -> float:
    returns = returns.dropna()
    volatility = returns.std() * np.sqrt(365)
    return float(returns.mean() * 365 / volatility) if volatility and np.isfinite(volatility) else 0.0


def _candidate_score(
    outcome: PortfolioOutcome,
    development_dates: pd.DatetimeIndex,
    n_groups: int = 8,
) -> tuple[float, float, list[float]]:
    dates = development_dates.intersection(outcome.returns.index)
    if len(dates) < 120:
        raise ValueError("At least 120 development observations are required for CPCV overlay selection")
    groups = min(n_groups, max(4, len(dates) // 60))
    splits = combinatorial_purged_splits(
        len(dates), n_groups=groups, n_test_groups=2,
        label_horizon=7, embargo=7,
    )
    fold_scores = [
        _sharpe(outcome.returns.reindex(dates[list(split.test_indices)]))
        for split in splits
    ]
    return (
        float(np.median(fold_scores)),
        float(outcome.turnover.reindex(dates).mean()),
        fold_scores,
    )


def select_overlay_rule(
    bundle: SignalBundle,
    forecast: pd.Series,
    method: str,
    development_dates: pd.DatetimeIndex,
    base_strategy: str | None,
    selection_cost_bps: int = 25,
) -> tuple[OverlayRule, pd.DataFrame]:
    rows = []
    for rule in overlay_candidates(method):
        weights = build_overlay_weights(bundle, forecast, rule, base_strategy)
        outcome = execute_asset_weights(bundle, weights, selection_cost_bps)
        score, turnover, fold_scores = _candidate_score(outcome, development_dates)
        rows.append({
            **asdict(rule),
            "base_strategy": base_strategy or "combined",
            "selection_cost_bps": selection_cost_bps,
            "median_cpcv_sharpe": score,
            "development_turnover": turnover,
            "cpcv_fold_count": len(fold_scores),
            "cpcv_sharpe_min": float(np.min(fold_scores)),
            "cpcv_sharpe_max": float(np.max(fold_scores)),
        })
    candidates = pd.DataFrame(rows)
    best = candidates.sort_values(
        ["median_cpcv_sharpe", "development_turnover"], ascending=[False, True]
    ).iloc[0]
    selected = OverlayRule(
        method=str(best.method), floor=float(best.floor), threshold=float(best.threshold),
        target_probability=float(best.target_probability), low_threshold=float(best.low_threshold),
        high_threshold=float(best.high_threshold), low_regime=str(best.low_regime),
    )
    fields = asdict(selected)
    selected_mask = pd.Series(True, index=candidates.index)
    for field, value in fields.items():
        selected_mask &= candidates[field] == value
    candidates["selected"] = selected_mask
    return selected, candidates


def _paired_sharpe_bootstrap(
    baseline: pd.Series,
    overlay: pd.Series,
    samples: int = 1000,
    block_length: int = 14,
    seed: int = 42,
) -> dict[str, float]:
    aligned = pd.concat([baseline.rename("baseline"), overlay.rename("overlay")], axis=1).dropna()
    if len(aligned) < 30:
        return {"lower": np.nan, "median": np.nan, "upper": np.nan}
    rng = np.random.default_rng(seed)
    starts = np.arange(max(1, len(aligned) - block_length + 1))
    blocks_needed = int(np.ceil(len(aligned) / block_length))
    differences = []
    for _ in range(samples):
        indices = np.concatenate([
            np.arange(start, min(start + block_length, len(aligned)))
            for start in rng.choice(starts, size=blocks_needed, replace=True)
        ])[: len(aligned)]
        sampled = aligned.iloc[indices]
        differences.append(_sharpe(sampled.overlay) - _sharpe(sampled.baseline))
    lower, median, upper = np.quantile(differences, [0.025, 0.50, 0.975])
    return {"lower": float(lower), "median": float(median), "upper": float(upper)}


def _portfolio_definitions(selected: dict[str, OverlayRule]) -> dict[str, tuple[str, str | None]]:
    return {
        "standalone_volatility_breakout": ("standalone", "volatility_breakout"),
        "standalone_trend_following": ("standalone", "trend_following"),
        "breakout_risk_off_sizing": ("risk_off_sizing", "volatility_breakout"),
        "trend_risk_off_sizing": ("risk_off_sizing", "trend_following"),
        "breakout_activation": ("breakout_activation", "volatility_breakout"),
        "breakout_volatility_targeted": ("volatility_targeted_sizing", "volatility_breakout"),
        "trend_volatility_targeted": ("volatility_targeted_sizing", "trend_following"),
        "volatility_regime_switching": ("strategy_switching", None),
    }


def run_forecast_portfolio_study(
    panel: pd.DataFrame,
    forecast_predictions: pd.DataFrame,
    universes: dict[pd.Timestamp, list[str]],
    forecast_model: str = "elastic_net",
    forecast_feature_set: str = "price_only",
    holdout_start: str | pd.Timestamp = HOLDOUT_START,
    holdout_end: str | pd.Timestamp = HOLDOUT_END,
    cost_levels: tuple[int, ...] = COST_LEVELS,
) -> ForecastPortfolioResult:
    """Freeze portfolio rules on development CPCV, then score the locked holdout."""
    holdout_start, holdout_end = pd.Timestamp(holdout_start), pd.Timestamp(holdout_end)
    fixed = forecast_predictions[
        (forecast_predictions.model == forecast_model)
        & (forecast_predictions.feature_set == forecast_feature_set)
    ].copy()
    if fixed.empty or fixed.duplicated("date").any():
        raise ValueError("The requested fixed forecast must have one probability per date")
    forecast = fixed.set_index(pd.to_datetime(fixed.date)).probability.astype(float).sort_index().loc[:holdout_end]
    development_dates = forecast.index[forecast.index < holdout_start]
    holdout_dates = forecast.index[(forecast.index >= holdout_start) & (forecast.index <= holdout_end)]
    if development_dates.empty or holdout_dates.empty:
        raise ValueError("Both development and locked-holdout forecast observations are required")

    bundle = build_signal_bundle(panel, universes, "W-FRI", 0.20)
    selection_specs = {
        "breakout_risk_off_sizing": ("risk_off_sizing", "volatility_breakout"),
        "trend_risk_off_sizing": ("risk_off_sizing", "trend_following"),
        "breakout_activation": ("breakout_activation", "volatility_breakout"),
        "breakout_volatility_targeted": ("volatility_targeted_sizing", "volatility_breakout"),
        "trend_volatility_targeted": ("volatility_targeted_sizing", "trend_following"),
        "volatility_regime_switching": ("strategy_switching", None),
    }
    selected_rules = {
        "standalone_volatility_breakout": OverlayRule("standalone"),
        "standalone_trend_following": OverlayRule("standalone"),
    }
    selection_parts = []
    for portfolio, (method, base_strategy) in selection_specs.items():
        selected, candidates = select_overlay_rule(
            bundle, forecast, method, development_dates, base_strategy, 25
        )
        candidates.insert(0, "portfolio", portfolio)
        selection_parts.append(candidates)
        selected_rules[portfolio] = selected

    portfolio_weights = {}
    definitions = _portfolio_definitions(selected_rules)
    for portfolio, (method, base_strategy) in definitions.items():
        rule = selected_rules[portfolio]
        portfolio_weights[portfolio] = build_overlay_weights(bundle, forecast, rule, base_strategy)
    for benchmark in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top10"):
        portfolio_weights[benchmark] = build_benchmark_weights(bundle, forecast, benchmark)

    outcomes = {
        (portfolio, cost): execute_asset_weights(bundle, weights, cost)
        for portfolio, weights in portfolio_weights.items()
        for cost in cost_levels
    }
    metrics_rows = []
    return_columns = {}
    for (portfolio, cost), outcome in outcomes.items():
        category = "benchmark" if portfolio in {
            "btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top10"
        } else ("standalone" if portfolio.startswith("standalone") else "forecast_overlay")
        for split, dates in (("development", development_dates), ("holdout", holdout_dates)):
            metrics_rows.append({
                "split": split,
                "portfolio": portfolio,
                "category": category,
                "cost_bps": cost,
                "start": dates.min(),
                "end": dates.max(),
                **_period_metrics(outcome, dates),
            })
        return_columns[f"{portfolio}__cost_{cost}"] = outcome.returns.reindex(forecast.index)
    metrics = pd.DataFrame(metrics_rows)

    references = {
        "breakout_risk_off_sizing": "standalone_volatility_breakout",
        "breakout_activation": "standalone_volatility_breakout",
        "breakout_volatility_targeted": "standalone_volatility_breakout",
        "trend_risk_off_sizing": "standalone_trend_following",
        "trend_volatility_targeted": "standalone_trend_following",
        "volatility_regime_switching": "standalone_volatility_breakout",
    }
    comparison_rows = []
    for split in ("development", "holdout"):
        for cost in cost_levels:
            subset = metrics[(metrics.split == split) & (metrics.cost_bps == cost)].set_index("portfolio")
            for overlay, reference in references.items():
                row, baseline = subset.loc[overlay], subset.loc[reference]
                comparison_rows.append({
                    "split": split,
                    "cost_bps": cost,
                    "portfolio": overlay,
                    "reference": reference,
                    "delta_sharpe": row.Sharpe - baseline.Sharpe,
                    "delta_sortino": row.Sortino - baseline.Sortino,
                    "delta_cagr": row.CAGR - baseline.CAGR,
                    "delta_max_drawdown": row["Maximum Drawdown"] - baseline["Maximum Drawdown"],
                    "delta_calmar": row.Calmar - baseline.Calmar,
                    "delta_turnover": row.Turnover - baseline.Turnover,
                })
    comparisons = pd.DataFrame(comparison_rows)

    bootstrap_rows = []
    for overlay, reference in references.items():
        interval = _paired_sharpe_bootstrap(
            outcomes[(reference, 25)].returns.reindex(holdout_dates),
            outcomes[(overlay, 25)].returns.reindex(holdout_dates),
        )
        bootstrap_rows.append({"portfolio": overlay, "reference": reference, **interval})
    bootstrap = pd.DataFrame(bootstrap_rows)
    protocol = {
        "fixed_forecast_model": forecast_model,
        "fixed_forecast_feature_set": forecast_feature_set,
        "prediction_model_fitted": False,
        "forecast_recalibrated": False,
        "weekly_rebalance": "W-FRI",
        "selection_cost_bps": 25,
        "reported_cost_bps": list(cost_levels),
        "development_start": str(development_dates.min().date()),
        "development_end": str(development_dates.max().date()),
        "holdout_start": str(holdout_dates.min().date()),
        "holdout_end": str(holdout_dates.max().date()),
        "portfolio_selection": "development-only 8-group CPCV; median Sharpe, turnover tie-break",
        "holdout_threshold_searches": 0,
        "switching_definition": "high=breakout; low=trend or cash; medium=50% trend exposure",
    }
    return ForecastPortfolioResult(
        metrics, comparisons, pd.concat(selection_parts, ignore_index=True),
        pd.DataFrame(return_columns), bootstrap, selected_rules, protocol,
    )
