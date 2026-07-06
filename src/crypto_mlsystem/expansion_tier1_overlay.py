"""Expansion-state overlay using previously validated Expansion Tier-1 features.

This module is standalone.  It does not modify or reselect the frozen
``btc_eth_macro_gate_balanced`` strategy.  The frozen macro gate remains Layer 1;
Expansion Tier-1 features are tested only as a Layer-2 exposure/tilt overlay
when the frozen gate is already risk-on.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .expansion_state_model import (
    _all_risk_on,
    _buy_hold_weights,
    _feature_importance,
    _fmt,
    _json_safe,
    _positive_probability,
    _prior_meta_overlay_rows,
    _rebalance_dates,
    _rows_for_result,
    _table,
    _threshold_from_dev,
    _weekly_return,
)
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
from .upside_expansion_models import build_expansion_feature_candidates
from .volatility_breakout import deflated_sharpe_probability, probability_backtest_overfitting


DEVELOPMENT_START_TIER1 = pd.Timestamp("2019-07-05")
DEVELOPMENT_END_TIER1 = pd.Timestamp("2024-12-31")
BASELINE_NAME = FIXED_SELECTED.name
DEFAULT_TIER1_FEATURES = (
    "recovery_from_drawdown",
    "tvl_percentile",
    "jump_intensity",
    "stablecoin_supply_percentile",
    "eth_btc_relative_strength_30d",
    "upside_semivariance",
    "distance_from_90d_lows",
    "top20_30d_high_pct",
    "downside_to_upside_volatility_ratio",
    "top20_above_30dma_pct",
    "dispersion_acceleration",
    "risk_appetite_recovery_score",
    "volume_confirmation_of_price_trend",
    "volatility_of_volatility",
    "tvl_acceleration",
    "market_dollar_volume_growth_30d",
    "combined_crypto_liquidity_impulse",
    "stablecoin_supply_acceleration",
    "eth_btc_relative_strength_14d",
    "falling_vix_after_high_vix",
)
TARGETS = (
    ("target_a_btc_eth_upside", "BTC/ETH 50-50 30-day forward return > +15%"),
    ("target_b_eth_leadership", "ETH outperforms BTC over the next 30 days by > +5%"),
    ("target_c_top20_leadership", "Point-in-time top-20 equal-weight 30-day return beats BTC/ETH by > +5%"),
)


@dataclass(frozen=True)
class ModelSpec:
    name: str
    family: str
    factory: Callable[[], Any]


@dataclass(frozen=True)
class OverlayCandidate:
    name: str
    allocation_type: str
    expansion_model: str
    leadership_model: str | None
    top20_model: str | None
    multiplier: float
    threshold: float
    description: str


@dataclass
class PredictionBundle:
    config_name: str
    target: str
    target_description: str
    model_name: str
    threshold: float
    full_probability: pd.Series
    dev_probability: pd.Series
    holdout_probability: pd.Series
    feature_importance: pd.DataFrame


def model_specs() -> list[ModelSpec]:
    specs = [
        ModelSpec(
            "logistic_regression",
            "Logistic regression",
            lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500, class_weight="balanced", random_state=31)),
        ),
        ModelSpec(
            "elastic_net_logistic",
            "Elastic Net logistic regression",
            lambda: make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    solver="saga",
                    penalty="elasticnet",
                    l1_ratio=0.40,
                    C=0.50,
                    max_iter=6000,
                    class_weight="balanced",
                    random_state=31,
                ),
            ),
        ),
        ModelSpec(
            "random_forest",
            "Random forest",
            lambda: RandomForestClassifier(
                n_estimators=160,
                max_depth=4,
                min_samples_leaf=12,
                class_weight="balanced",
                random_state=31,
                n_jobs=-1,
            ),
        ),
        ModelSpec(
            "gradient_boosting",
            "Gradient boosting",
            lambda: GradientBoostingClassifier(n_estimators=120, max_depth=2, learning_rate=0.04, min_samples_leaf=10, random_state=31),
        ),
    ]
    if importlib.util.find_spec("xgboost") is not None:
        def xgb_factory() -> Any:
            from xgboost import XGBClassifier

            return XGBClassifier(
                n_estimators=120,
                max_depth=2,
                learning_rate=0.04,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric="logloss",
                random_state=31,
            )

        specs.append(ModelSpec("xgboost", "XGBoost", xgb_factory))
    return specs


def load_tier1_feature_names(path: str | Path = "reports/upside_expansion_models/expansion_feature_tiers.csv") -> list[str]:
    path = Path(path)
    if path.exists():
        tiers = pd.read_csv(path)
        selected = tiers[tiers.feature_tier.astype(str).eq("Expansion Tier 1")]
        if not selected.empty:
            return selected.feature.astype(str).tolist()
    return list(DEFAULT_TIER1_FEATURES)


def _forward_return(close: pd.DataFrame, symbol: str, dates: pd.DatetimeIndex, horizon_days: int = 30) -> pd.Series:
    values = []
    for date in dates:
        if date not in close.index or symbol not in close:
            values.append(np.nan)
            continue
        end_pos = close.index.searchsorted(date + pd.Timedelta(days=horizon_days))
        if end_pos >= len(close.index):
            values.append(np.nan)
            continue
        start = close.at[date, symbol]
        end = close.iloc[end_pos][symbol]
        values.append(float(end / start - 1.0) if pd.notna(start) and pd.notna(end) and start > 0 else np.nan)
    return pd.Series(values, index=dates)


def build_targets(dataset: MacroRegimeDataset, dates: pd.DatetimeIndex) -> pd.DataFrame:
    btc = _forward_return(dataset.close, "BTC", dates)
    eth = _forward_return(dataset.close, "ETH", dates)
    mix = 0.50 * btc + 0.50 * eth
    top20_values = []
    for date in dates:
        if date not in dataset.close.index or date not in dataset.universe_weights.index:
            top20_values.append(np.nan)
            continue
        end_pos = dataset.close.index.searchsorted(date + pd.Timedelta(days=30))
        if end_pos >= len(dataset.close.index):
            top20_values.append(np.nan)
            continue
        active = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        start = dataset.close.loc[date, active].replace(0, np.nan)
        end = dataset.close.iloc[end_pos][active]
        forward = (end / start - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
        top20_values.append(float(forward.mean()) if len(forward) else np.nan)
    top20 = pd.Series(top20_values, index=dates)
    targets = pd.DataFrame(index=dates)
    targets["target_a_btc_eth_upside"] = (mix > 0.15).astype(float)
    targets["target_b_eth_leadership"] = ((eth - btc) > 0.05).astype(float)
    targets["target_c_top20_leadership"] = ((top20 - mix) > 0.05).astype(float)
    unavailable = pd.concat([btc, eth, mix, top20], axis=1).isna().any(axis=1)
    targets.loc[unavailable, :] = np.nan
    return targets


def target_diagnostics(targets: pd.DataFrame) -> pd.DataFrame:
    descriptions = dict(TARGETS)
    rows = []
    for target in targets.columns:
        for split, start, end in (
            ("development", DEVELOPMENT_START_TIER1, DEVELOPMENT_END_TIER1),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            y = targets[target].loc[start:end].dropna().astype(int)
            rows.append({
                "target": target,
                "description": descriptions.get(target, target),
                "split": split,
                "observations": int(len(y)),
                "positive_events": int(y.sum()) if len(y) else 0,
                "prevalence": float(y.mean()) if len(y) else np.nan,
            })
    return pd.DataFrame(rows)


def _cpcv_oof_probabilities(x_dev: pd.DataFrame, y_dev: pd.Series, spec: ModelSpec) -> tuple[pd.Series, pd.DataFrame]:
    sums = pd.Series(0.0, index=x_dev.index)
    counts = pd.Series(0.0, index=x_dev.index)
    rows = []
    splits = combinatorial_purged_splits(len(x_dev), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    for number, split in enumerate(splits):
        train_index = x_dev.index[list(split.train_indices)]
        test_index = x_dev.index[list(split.test_indices)]
        y_train = y_dev.loc[train_index]
        if y_train.nunique() < 2:
            prob = pd.Series(float(y_train.mean()), index=test_index)
        else:
            model = spec.factory()
            model.fit(x_dev.loc[train_index], y_train)
            prob = pd.Series(_positive_probability(model, x_dev.loc[test_index]), index=test_index)
        sums.loc[test_index] += prob
        counts.loc[test_index] += 1.0
        rows.append({
            "model": spec.name,
            "fold": number,
            "test_groups": ",".join(str(group) for group in split.test_groups),
            "train_samples": len(train_index),
            "test_samples": len(test_index),
        })
    return (sums / counts.replace(0, np.nan)).fillna(float(y_dev.mean())), pd.DataFrame(rows)


def _fit_holdout_probability(x_dev: pd.DataFrame, y_dev: pd.Series, x_holdout: pd.DataFrame, spec: ModelSpec) -> tuple[pd.Series, Any | None]:
    if y_dev.nunique() < 2:
        return pd.Series(float(y_dev.mean()), index=x_holdout.index), None
    model = spec.factory()
    model.fit(x_dev, y_dev)
    return pd.Series(_positive_probability(model, x_holdout), index=x_holdout.index), model


def _classification_metrics(y: pd.Series, probability: pd.Series, threshold: float, split: str, config: str, target: str, model: str) -> dict[str, Any]:
    data = pd.concat([y.rename("y"), probability.rename("probability")], axis=1).dropna()
    if data.empty:
        return {"config": config, "target": target, "model": model, "split": split}
    y_true = data.y.astype(int)
    prob = data.probability.clip(0.0, 1.0)
    pred = (prob >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, pred, average="binary", zero_division=0)
    matrix = confusion_matrix(y_true, pred, labels=[0, 1])
    auc = roc_auc_score(y_true, prob) if y_true.nunique() == 2 else np.nan
    return {
        "config": config,
        "target": target,
        "model": model,
        "split": split,
        "threshold": threshold,
        "observations": int(len(y_true)),
        "positive_events": int(y_true.sum()),
        "auc": float(auc) if np.isfinite(auc) else np.nan,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "brier_score": float(brier_score_loss(y_true, prob)),
        "true_negative": int(matrix[0, 0]),
        "false_positive": int(matrix[0, 1]),
        "false_negative": int(matrix[1, 0]),
        "true_positive": int(matrix[1, 1]),
    }


def fit_prediction_models(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    specs: list[ModelSpec] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, PredictionBundle]]:
    specs = specs or model_specs()
    metrics = []
    folds = []
    importance = []
    bundles: dict[str, PredictionBundle] = {}
    dev_mask = (features.index >= DEVELOPMENT_START_TIER1) & (features.index <= DEVELOPMENT_END_TIER1)
    holdout_mask = (features.index >= HOLDOUT_START) & (features.index <= HOLDOUT_END)
    for target, description in TARGETS:
        valid_dev = targets[target].loc[dev_mask].dropna().index
        valid_holdout = targets[target].loc[holdout_mask].dropna().index
        x_dev = features.loc[valid_dev]
        y_dev = targets.loc[valid_dev, target].astype(int)
        x_holdout = features.loc[valid_holdout]
        y_holdout = targets.loc[valid_holdout, target].astype(int)
        for spec in specs:
            config = f"{target}__{spec.name}"
            dev_prob, fold = _cpcv_oof_probabilities(x_dev, y_dev, spec)
            fold["config"] = config
            fold["target"] = target
            folds.append(fold)
            threshold = _threshold_from_dev(dev_prob, y_dev)
            holdout_prob, model = _fit_holdout_probability(x_dev, y_dev, x_holdout, spec)
            full = pd.Series(np.nan, index=features.index)
            full.loc[dev_prob.index] = dev_prob
            full.loc[holdout_prob.index] = holdout_prob
            metrics.append(_classification_metrics(y_dev, dev_prob, threshold, "development_cpcv", config, target, spec.name))
            metrics.append(_classification_metrics(y_holdout, holdout_prob, threshold, "holdout", config, target, spec.name))
            fi = _feature_importance(model, spec, list(features.columns), config)
            fi["target"] = target
            importance.append(fi)
            bundles[config] = PredictionBundle(
                config_name=config,
                target=target,
                target_description=description,
                model_name=spec.name,
                threshold=threshold,
                full_probability=full.ffill().fillna(float(dev_prob.mean()) if len(dev_prob) else 0.0),
                dev_probability=dev_prob,
                holdout_probability=holdout_prob,
                feature_importance=fi,
            )
    return (
        pd.DataFrame(metrics),
        pd.concat(folds, ignore_index=True) if folds else pd.DataFrame(),
        pd.concat(importance, ignore_index=True) if importance else pd.DataFrame(),
        bundles,
    )


def _best_predictive_by_target(metrics: pd.DataFrame) -> dict[str, str]:
    dev = metrics[metrics.split == "development_cpcv"].copy()
    dev["prediction_score"] = dev["auc"].fillna(0.5) - dev["brier_score"].fillna(1.0) + 0.10 * dev["f1"].fillna(0.0)
    return {
        target: str(group.sort_values("prediction_score", ascending=False).iloc[0].config)
        for target, group in dev.groupby("target")
    }


def predeclared_overlay_candidates(
    bundles: dict[str, PredictionBundle],
    top20_passes_development: bool,
) -> list[OverlayCandidate]:
    by_target: dict[str, list[PredictionBundle]] = {}
    for bundle in bundles.values():
        by_target.setdefault(bundle.target, []).append(bundle)
    candidates: list[OverlayCandidate] = []
    for expansion in by_target["target_a_btc_eth_upside"]:
        for multiplier in (0.5, 1.0, 1.5, 2.0):
            candidates.append(OverlayCandidate(
                name=f"balanced_{expansion.model_name}_m{str(multiplier).replace('.', '_')}",
                allocation_type="balanced_btc_eth",
                expansion_model=expansion.config_name,
                leadership_model=None,
                top20_model=None,
                multiplier=multiplier,
                threshold=expansion.threshold,
                description="Balanced BTC/ETH expansion probability exposure multiplier.",
            ))
            leadership_key = f"target_b_eth_leadership__{expansion.model_name}"
            leadership_model = leadership_key if leadership_key in bundles else next(b.config_name for b in by_target["target_b_eth_leadership"])
            candidates.append(OverlayCandidate(
                name=f"dynamic_tilt_{expansion.model_name}_m{str(multiplier).replace('.', '_')}",
                allocation_type="dynamic_btc_eth_tilt",
                expansion_model=expansion.config_name,
                leadership_model=leadership_model,
                top20_model=None,
                multiplier=multiplier,
                threshold=expansion.threshold,
                description="Expansion exposure multiplier with dynamic ETH/BTC leadership tilt.",
            ))
            if top20_passes_development:
                top20_key = f"target_c_top20_leadership__{expansion.model_name}"
                top20_model = top20_key if top20_key in bundles else next(b.config_name for b in by_target["target_c_top20_leadership"])
                candidates.append(OverlayCandidate(
                    name=f"top20_sleeve_{expansion.model_name}_m{str(multiplier).replace('.', '_')}",
                    allocation_type="top20_sleeve",
                    expansion_model=expansion.config_name,
                    leadership_model=leadership_model,
                    top20_model=top20_model,
                    multiplier=multiplier,
                    threshold=expansion.threshold,
                    description="Expansion multiplier with top-20 sleeve when leadership state is predicted.",
                ))
    return candidates


def _top20_sleeve_weights(dataset: MacroRegimeDataset, date: pd.Timestamp, sleeve: float) -> pd.Series:
    row = pd.Series(0.0, index=dataset.close.columns)
    if date not in dataset.universe_weights.index:
        return row
    active = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
    if len(active) == 0:
        return row
    allocation = sleeve / len(active)
    row.loc[active] = allocation
    return row


def build_overlay_weights(
    dataset: MacroRegimeDataset,
    base_weights: pd.DataFrame,
    combined_regime: pd.Series,
    candidate: OverlayCandidate,
    bundles: dict[str, PredictionBundle],
) -> tuple[pd.DataFrame, pd.Series]:
    dates = pd.DatetimeIndex(base_weights.index)
    weights = base_weights.copy()
    decisions = pd.Series("frozen_macro_gate", index=dates, dtype=object)
    expansion = bundles[candidate.expansion_model].full_probability.reindex(dates).ffill().fillna(0.0)
    leadership = bundles[candidate.leadership_model].full_probability.reindex(dates).ffill().fillna(0.5) if candidate.leadership_model else pd.Series(0.5, index=dates)
    top20 = bundles[candidate.top20_model].full_probability.reindex(dates).ffill().fillna(0.0) if candidate.top20_model else pd.Series(0.0, index=dates)
    regimes = combined_regime.reindex(dates).ffill().fillna("risk_off")
    for date in dates:
        if str(regimes.loc[date]) != "risk_on":
            continue
        base = base_weights.loc[date].copy()
        base_exposure = float(base.sum())
        if base_exposure <= 0:
            continue
        high_expansion = float(expansion.loc[date]) >= candidate.threshold
        factor = candidate.multiplier if high_expansion else 0.50
        target_exposure = min(1.0, max(0.0, base_exposure * factor))
        scaled = base * (target_exposure / base_exposure)
        decisions.loc[date] = "expansion_high" if high_expansion else "expansion_low_reduced"
        if candidate.allocation_type == "dynamic_btc_eth_tilt":
            total = float(scaled.sum())
            if {"BTC", "ETH"}.issubset(scaled.index) and total > 0:
                if float(leadership.loc[date]) >= bundles[candidate.leadership_model].threshold:
                    scaled.loc["BTC"] = total * 0.30
                    scaled.loc["ETH"] = total * 0.70
                    decisions.loc[date] += "_eth_tilt"
                elif float(leadership.loc[date]) <= (1.0 - bundles[candidate.leadership_model].threshold):
                    scaled.loc["BTC"] = total * 0.70
                    scaled.loc["ETH"] = total * 0.30
                    decisions.loc[date] += "_btc_tilt"
        elif candidate.allocation_type == "top20_sleeve" and candidate.top20_model:
            if float(top20.loc[date]) >= bundles[candidate.top20_model].threshold:
                sleeve = min(0.40, target_exposure)
                core_exposure = max(0.0, target_exposure - sleeve)
                core = base * (core_exposure / base_exposure)
                scaled = core + _top20_sleeve_weights(dataset, date, sleeve).reindex(core.index).fillna(0.0)
                decisions.loc[date] += "_top20_sleeve"
        weights.loc[date] = scaled
        total = float(weights.loc[date].sum())
        if total > 1.0:
            weights.loc[date] /= total
    return weights, decisions


def _fold_sharpe(weekly: pd.Series, indices: tuple[int, ...]) -> float:
    subset = weekly.iloc[list(indices)].dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def select_overlay_cpcv(candidates: list[OverlayCandidate], results_25bps: dict[str, PortfolioResult]) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows = []
    fold_rows = []
    weekly_returns = {}
    for candidate in candidates:
        weekly = _weekly_return(results_25bps[candidate.name].returns.loc[DEVELOPMENT_START_TIER1:DEVELOPMENT_END_TIER1])
        weekly_returns[candidate.name] = weekly
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_values = []
        for number, split in enumerate(splits):
            sharpe = _fold_sharpe(weekly, split.test_indices)
            fold_values.append(sharpe)
            fold_rows.append({
                "candidate": candidate.name,
                "allocation_type": candidate.allocation_type,
                "fold": number,
                "test_groups": ",".join(str(group) for group in split.test_groups),
                "fold_sharpe": sharpe,
            })
        dev = period_metrics(results_25bps[candidate.name], DEVELOPMENT_START_TIER1, DEVELOPMENT_END_TIER1)
        rows.append({
            "candidate": candidate.name,
            "allocation_type": candidate.allocation_type,
            "expansion_model": candidate.expansion_model,
            "leadership_model": candidate.leadership_model,
            "top20_model": candidate.top20_model,
            "multiplier": candidate.multiplier,
            "threshold": candidate.threshold,
            "description": candidate.description,
            "median_fold_sharpe": float(np.nanmedian(fold_values)),
            "worst_fold_sharpe": float(np.nanmin(fold_values)),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_values) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
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


def _prior_expansion_diagnostics_rows(path: str | Path = "reports/expansion_state_model/overlay_metrics.csv") -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    selected = frame[frame.get("selected_development_candidate", False).astype(str).str.lower().isin(["true", "1"])] if "selected_development_candidate" in frame else frame.head(0)
    if selected.empty and "name" in frame:
        selected = frame[frame.name.astype(str).str.contains("expansion_filter_t60_14d", regex=False)]
    if selected.empty:
        return pd.DataFrame()
    selected = selected.copy()
    selected["benchmark_group"] = "prior_expansion_diagnostics_overlay"
    selected["family"] = "Prior expansion diagnostics overlay"
    return selected


def benchmark_rows(dataset: MacroRegimeDataset, base_weights: pd.DataFrame, regimes: tuple[pd.Series, pd.Series, pd.Series]) -> pd.DataFrame:
    rows = []
    macro, crypto, combined = regimes
    for cost in COST_LEVELS:
        frozen = backtest_weights(dataset, base_weights, macro, crypto, combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
        rows.extend(_rows_for_result(BASELINE_NAME, "Frozen macro gate", "frozen_strategy", cost, frozen))
        risk_on = _all_risk_on(dataset.close.index)
        for name, family in (
            ("btc_buy_hold", "BTC buy-and-hold"),
            ("eth_buy_hold", "ETH buy-and-hold"),
            ("btc_eth_50_50", "50/50 BTC/ETH"),
        ):
            result = backtest_weights(dataset, _buy_hold_weights(dataset, name), *risk_on, cost_bps=cost, turnover_cap=10.0)
            rows.extend(_rows_for_result(name, family, "benchmark", cost, result))
    prior_meta = _prior_meta_overlay_rows()
    if not prior_meta.empty:
        rows.extend(prior_meta.to_dict("records"))
    prior_expansion = _prior_expansion_diagnostics_rows()
    if not prior_expansion.empty:
        rows.extend(prior_expansion.to_dict("records"))
    return pd.DataFrame(rows)


def _calibration_table(targets: pd.DataFrame, bundles: dict[str, PredictionBundle]) -> pd.DataFrame:
    rows = []
    for bundle in bundles.values():
        for split, probability in (("development_cpcv", bundle.dev_probability), ("holdout", bundle.holdout_probability)):
            y = targets[bundle.target].reindex(probability.index).dropna().astype(int)
            data = pd.concat([y.rename("y"), probability.rename("p")], axis=1).dropna()
            if data.empty:
                continue
            ranked = data["p"].rank(method="first")
            bins = pd.qcut(ranked, q=min(10, len(data)), duplicates="drop")
            for number, (_, group) in enumerate(data.groupby(bins, observed=False), start=1):
                rows.append({
                    "config": bundle.config_name,
                    "target": bundle.target,
                    "split": split,
                    "bin": number,
                    "observations": int(len(group)),
                    "mean_probability": float(group.p.mean()),
                    "event_rate": float(group.y.mean()),
                })
    return pd.DataFrame(rows)


def run_expansion_tier1_overlay(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
    specs: list[ModelSpec] | None = None,
    tier_path: str | Path = "reports/upside_expansion_models/expansion_feature_tiers.csv",
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=20)
    all_feature_frame, metadata = build_expansion_feature_candidates(dataset, dataset.regime_features, public_data)
    tier1_features = load_tier1_feature_names(tier_path)
    available_features = [feature for feature in tier1_features if feature in all_feature_frame.columns]
    feature_frame = all_feature_frame.reindex(columns=available_features).replace([np.inf, -np.inf], np.nan)
    medians = feature_frame.loc[DEVELOPMENT_START_TIER1:DEVELOPMENT_END_TIER1].median().fillna(0.0)
    feature_frame = feature_frame.ffill().fillna(medians).fillna(0.0)
    dates = _rebalance_dates(dataset.close.index, 7)
    x = feature_frame.reindex(dates).ffill().fillna(0.0)
    targets = build_targets(dataset, dates)
    prediction_metrics, prediction_folds, feature_importance, bundles = fit_prediction_models(x, targets, specs)
    dev_metrics = prediction_metrics[prediction_metrics.split == "development_cpcv"].copy()
    top20_best = dev_metrics[dev_metrics.target == "target_c_top20_leadership"].sort_values(["auc", "f1"], ascending=False).head(1)
    top20_passes = bool(not top20_best.empty and top20_best.iloc[0]["auc"] >= 0.55 and top20_best.iloc[0]["f1"] >= 0.05)
    candidates = predeclared_overlay_candidates(bundles, top20_passes)

    base_weights, macro_regime, crypto_regime, combined_regime = build_candidate_weights(dataset, FIXED_SELECTED)
    overlay_results: dict[str, dict[int, PortfolioResult]] = {}
    overlay_decisions: dict[str, pd.Series] = {}
    for candidate in candidates:
        weights, decisions = build_overlay_weights(dataset, base_weights, combined_regime, candidate, bundles)
        overlay_decisions[candidate.name] = decisions
        overlay_results[candidate.name] = {
            cost: backtest_weights(dataset, weights, macro_regime, crypto_regime, combined_regime, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
            for cost in COST_LEVELS
        }
    results_25 = {name: by_cost[25] for name, by_cost in overlay_results.items()}
    selection, cpcv_folds, winner, pbo = select_overlay_cpcv(candidates, results_25)
    overlay_metric_rows = []
    for candidate in candidates:
        for cost, result in overlay_results[candidate.name].items():
            for row in _rows_for_result(candidate.name, candidate.description, candidate.allocation_type, cost, result, selected=candidate.name == winner):
                row.update({
                    "multiplier": candidate.multiplier,
                    "expansion_model": candidate.expansion_model,
                    "leadership_model": candidate.leadership_model,
                    "top20_model": candidate.top20_model,
                })
                overlay_metric_rows.append(row)
    overlay_metrics = pd.DataFrame(overlay_metric_rows)
    benchmarks = benchmark_rows(dataset, base_weights, (macro_regime, crypto_regime, combined_regime))
    frozen_25 = backtest_weights(dataset, base_weights, macro_regime, crypto_regime, combined_regime, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
    winner_25 = overlay_results[winner][25]
    frozen_dev = period_metrics(frozen_25, DEVELOPMENT_START_TIER1, DEVELOPMENT_END_TIER1)
    frozen_holdout = period_metrics(frozen_25, HOLDOUT_START, HOLDOUT_END)
    winner_dev = period_metrics(winner_25, DEVELOPMENT_START_TIER1, DEVELOPMENT_END_TIER1)
    winner_holdout = period_metrics(winner_25, HOLDOUT_START, HOLDOUT_END)
    winner_50 = period_metrics(overlay_results[winner][50], HOLDOUT_START, HOLDOUT_END)
    dsr = deflated_sharpe_probability(winner_25.returns.loc[HOLDOUT_START:HOLDOUT_END], tested_configurations=len(candidates) + len(prediction_metrics[prediction_metrics.split == "development_cpcv"]))

    exposure = pd.DataFrame({
        "frozen_exposure": frozen_25.weights.sum(axis=1),
        "overlay_exposure": winner_25.weights.sum(axis=1),
        "expansion_probability": bundles[selection.iloc[0].expansion_model].full_probability.reindex(winner_25.weights.index).ffill(),
    })
    exposure["exposure_delta"] = exposure.overlay_exposure - exposure.frozen_exposure
    contribution = pd.DataFrame({
        "frozen_return": frozen_25.returns,
        "overlay_return": winner_25.returns,
    }).loc[DEVELOPMENT_START_TIER1:HOLDOUT_END]
    contribution["incremental_return"] = contribution.overlay_return - contribution.frozen_return
    contribution["period"] = np.where(contribution.index >= HOLDOUT_START, "holdout", "development")
    contribution_rows = []
    for period, group in contribution.groupby("period"):
        frozen_total = float((1 + group["frozen_return"]).prod() - 1)
        overlay_total = float((1 + group["overlay_return"]).prod() - 1)
        contribution_rows.append({
            "period": period,
            "frozen_total_return": frozen_total,
            "overlay_total_return": overlay_total,
            "incremental_total_return": overlay_total - frozen_total,
        })
    contribution_summary = pd.DataFrame(contribution_rows)
    decision_counts = overlay_decisions[winner].loc[HOLDOUT_START:HOLDOUT_END].value_counts(normalize=True).rename_axis("decision").reset_index(name="frequency")
    calibration = _calibration_table(targets, bundles)

    passes = bool(
        winner_holdout["Sharpe"] > frozen_holdout["Sharpe"] + 0.10
        and winner_holdout["CAGR"] >= frozen_holdout["CAGR"] * 0.90
        and winner_holdout["Maximum Drawdown"] >= frozen_holdout["Maximum Drawdown"] - 0.05
        and winner_50["CAGR"] > 0
        and winner_holdout["Annual Turnover"] <= 12
        and winner_holdout["Exposure"] >= 0.15
        and (not np.isfinite(pbo) or pbo <= 0.65)
        and dsr >= 0.50
    )
    if passes:
        conclusion = "Expansion Tier-1 overlay shows paper-monitoring evidence of genuine upside capture."
    elif winner_holdout["Exposure"] < frozen_holdout["Exposure"] * 0.75:
        conclusion = "Expansion Tier-1 overlay mostly reduces exposure and hides risk rather than creating genuine upside capture."
    elif winner_holdout["Sharpe"] <= frozen_holdout["Sharpe"] or winner_holdout["CAGR"] <= frozen_holdout["CAGR"]:
        conclusion = "Expansion Tier-1 overlay does not improve the frozen strategy economically."
    else:
        conclusion = "Expansion Tier-1 overlay shows partial upside-capture evidence but fails statistical or implementation guardrails."
    return {
        "dataset": dataset,
        "tier1_features": available_features,
        "excluded_features": [feature for feature in tier1_features if feature not in available_features],
        "feature_metadata": metadata[metadata.feature.isin(available_features)].copy() if not metadata.empty else pd.DataFrame(),
        "feature_frame": feature_frame,
        "targets": targets,
        "target_diagnostics": target_diagnostics(targets),
        "prediction_metrics": prediction_metrics,
        "prediction_folds": prediction_folds,
        "feature_importance": feature_importance,
        "prediction_bundles": bundles,
        "top20_passes_development": top20_passes,
        "candidates": candidates,
        "selection": selection,
        "cpcv_folds": cpcv_folds,
        "winner": winner,
        "overlay_results": overlay_results,
        "overlay_metrics": overlay_metrics,
        "benchmarks": benchmarks,
        "frozen_development": frozen_dev,
        "frozen_holdout": frozen_holdout,
        "winner_development": winner_dev,
        "winner_holdout": winner_holdout,
        "winner_holdout_50bps": winner_50,
        "pbo": pbo,
        "deflated_sharpe_probability": dsr,
        "exposure_analysis": exposure,
        "contribution_summary": contribution_summary,
        "decision_counts": decision_counts,
        "calibration": calibration,
        "passes_guardrails": passes,
        "final_conclusion": conclusion,
        "tested_configurations": {
            "prediction_configs": int(len(prediction_metrics[prediction_metrics.split == "development_cpcv"])),
            "overlay_configs": int(len(candidates)),
            "total": int(len(prediction_metrics[prediction_metrics.split == "development_cpcv"]) + len(candidates)),
        },
        "protocol": {
            "title": "Expansion-State Overlay Using Tier-1 Expansion Features",
            "development_period": f"{DEVELOPMENT_START_TIER1.date()} to {DEVELOPMENT_END_TIER1.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} onward",
            "selection_rule": "Models and overlays are selected with development-only CPCV. Holdout is reported after selection only.",
            "baseline": BASELINE_NAME,
        },
    }


def _write_csvs(output: Path, result: dict[str, Any]) -> None:
    for key, filename in (
        ("target_diagnostics", "target_diagnostics.csv"),
        ("prediction_metrics", "prediction_metrics.csv"),
        ("prediction_folds", "prediction_folds.csv"),
        ("feature_importance", "feature_importance.csv"),
        ("selection", "overlay_selection.csv"),
        ("cpcv_folds", "overlay_cpcv_folds.csv"),
        ("overlay_metrics", "overlay_metrics.csv"),
        ("benchmarks", "benchmark_metrics.csv"),
        ("exposure_analysis", "exposure_analysis.csv"),
        ("contribution_summary", "contribution_summary.csv"),
        ("decision_counts", "decision_counts.csv"),
        ("calibration", "calibration.csv"),
        ("feature_metadata", "tier1_feature_metadata.csv"),
    ):
        frame = result.get(key)
        if isinstance(frame, pd.DataFrame):
            frame.to_csv(output / filename, index=True if key == "exposure_analysis" else False)


def write_expansion_tier1_overlay_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_csvs(output, result)
    selected = result["winner"]
    selected_costs = result["overlay_metrics"][(result["overlay_metrics"].name == selected) & (result["overlay_metrics"].split == "holdout")]
    holdout_benchmarks = result["benchmarks"][(result["benchmarks"].split == "holdout") & (result["benchmarks"].cost_bps.isin([25, 50]))]
    comparison = pd.concat([holdout_benchmarks, selected_costs], ignore_index=True, sort=False)
    top_importance = result["feature_importance"][result["feature_importance"].config.isin([
        result["selection"].iloc[0].expansion_model,
        result["selection"].iloc[0].leadership_model,
        result["selection"].iloc[0].top20_model,
    ])]

    (output / "results_summary.md").write_text(f"""# Results summary

Project: **{result['protocol']['title']}**

The frozen strategy **{BASELINE_NAME}** was not modified or reselected.

## Protocol

- Development: {result['protocol']['development_period']}
- Locked holdout: {result['protocol']['locked_holdout']}
- Tier-1 features used: {len(result['tier1_features'])}
- Tested configurations: {result['tested_configurations']['total']} total

## Development-selected overlay

Selected by development-only CPCV: **{selected}**

| Metric | Frozen | Selected overlay |
|---|---:|---:|
| Development Sharpe | {_fmt(result['frozen_development']['Sharpe'])} | {_fmt(result['winner_development']['Sharpe'])} |
| Holdout Sharpe | {_fmt(result['frozen_holdout']['Sharpe'])} | {_fmt(result['winner_holdout']['Sharpe'])} |
| Holdout CAGR | {_fmt(result['frozen_holdout']['CAGR'], True)} | {_fmt(result['winner_holdout']['CAGR'], True)} |
| Holdout max DD | {_fmt(result['frozen_holdout']['Maximum Drawdown'], True)} | {_fmt(result['winner_holdout']['Maximum Drawdown'], True)} |
| Holdout turnover | {_fmt(result['frozen_holdout']['Annual Turnover'])} | {_fmt(result['winner_holdout']['Annual Turnover'])} |
| Holdout exposure | {_fmt(result['frozen_holdout']['Exposure'], True)} | {_fmt(result['winner_holdout']['Exposure'], True)} |

Final conclusion: **{result['final_conclusion']}**
""", encoding="utf-8")

    (output / "development_metrics.md").write_text(f"""# Development metrics

Development-only CPCV selection ranking:

{_table(result['selection'], [('candidate', 'Candidate'), ('allocation_type', 'Allocation'), ('multiplier', 'Multiplier'), ('selection_score', 'Selection score'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds'), ('development_sharpe', 'Dev Sharpe'), ('development_turnover', 'Dev turnover'), ('development_exposure', 'Dev exposure')], {'positive_fold_fraction', 'development_exposure'}, limit=60)}
""", encoding="utf-8")

    (output / "holdout_metrics.md").write_text(f"""# Holdout metrics

Holdout was not used for model or overlay selection.

## Selected overlay cost sensitivity

{_table(selected_costs, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}
""", encoding="utf-8")

    (output / "exposure_turnover_drawdown.md").write_text(f"""# Exposure, turnover, and drawdown analysis

## Exposure summary

| Metric | Value |
|---|---:|
| Mean frozen exposure, holdout | {_fmt(result['frozen_holdout']['Exposure'], True)} |
| Mean overlay exposure, holdout | {_fmt(result['winner_holdout']['Exposure'], True)} |
| Overlay turnover, holdout | {_fmt(result['winner_holdout']['Annual Turnover'])} |
| Overlay max drawdown, holdout | {_fmt(result['winner_holdout']['Maximum Drawdown'], True)} |

## Holdout overlay decision frequencies

{_table(result['decision_counts'], [('decision', 'Decision'), ('frequency', 'Frequency')], {'frequency'})}
""", encoding="utf-8")

    (output / "expansion_layer_contribution.md").write_text(f"""# Contribution of expansion layer

Incremental return is overlay return minus frozen strategy return.

{_table(result['contribution_summary'], [('period', 'Period'), ('frozen_total_return', 'Frozen total return'), ('overlay_total_return', 'Overlay total return'), ('incremental_total_return', 'Incremental total return')], {'frozen_total_return', 'overlay_total_return', 'incremental_total_return'})}

Interpretation: {result['final_conclusion']}
""", encoding="utf-8")

    (output / "feature_importance.md").write_text(f"""# Feature importance

Only Expansion Tier-1 features were allowed in models.

## Tier-1 features used

{_table(pd.DataFrame({'feature': result['tier1_features']}), [('feature', 'Feature')], limit=80)}

## Selected-model feature importance

{_table(top_importance, [('config', 'Config'), ('target', 'Target'), ('feature', 'Feature'), ('importance', 'Importance'), ('method', 'Method')], limit=80)}
""", encoding="utf-8")

    (output / "calibration.md").write_text(f"""# Calibration

{_table(result['calibration'], [('config', 'Config'), ('target', 'Target'), ('split', 'Split'), ('bin', 'Bin'), ('observations', 'Obs'), ('mean_probability', 'Mean probability'), ('event_rate', 'Event rate')], {'mean_probability', 'event_rate'}, limit=100)}
""", encoding="utf-8")

    (output / "cpcv_diagnostics.md").write_text(f"""# CPCV diagnostics

## Fold distribution for selected overlay

{_table(result['cpcv_folds'][result['cpcv_folds'].candidate == selected], [('candidate', 'Candidate'), ('allocation_type', 'Allocation'), ('fold', 'Fold'), ('test_groups', 'Test groups'), ('fold_sharpe', 'Fold Sharpe')])}

## Prediction diagnostics

{_table(result['prediction_metrics'], [('config', 'Config'), ('target', 'Target'), ('split', 'Split'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier')], limit=80)}
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

- PBO: {_fmt(result['pbo'], True)}
- Deflated Sharpe probability: {_fmt(result['deflated_sharpe_probability'], True)}
- Guardrails passed: {_fmt(result['passes_guardrails'])}
- Top-20 allocation allowed by development criteria: {_fmt(result['top20_passes_development'])}

No holdout information was used to select models, thresholds, features, or overlay candidates.
""", encoding="utf-8")

    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

{_table(comparison, [('name', 'Name'), ('benchmark_group', 'Group'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=100)}
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Main question

Did the expansion layer create genuine upside capture, or did it simply reduce
exposure and hide risk?

**Answer:** {result['final_conclusion']}

## Recommendation

Do not modify or replace **{BASELINE_NAME}** unless the overlay passes the
reported statistical and economic guardrails. Treat any positive result here as
paper-monitoring evidence only.
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "tier1_features": result["tier1_features"],
        "excluded_features": result["excluded_features"],
        "winner": selected,
        "tested_configurations": result["tested_configurations"],
        "frozen_development": _json_safe(result["frozen_development"]),
        "frozen_holdout": _json_safe(result["frozen_holdout"]),
        "winner_development": _json_safe(result["winner_development"]),
        "winner_holdout": _json_safe(result["winner_holdout"]),
        "winner_holdout_50bps": _json_safe(result["winner_holdout_50bps"]),
        "pbo": _json_safe(result["pbo"]),
        "deflated_sharpe_probability": _json_safe(result["deflated_sharpe_probability"]),
        "passes_guardrails": result["passes_guardrails"],
        "final_conclusion": result["final_conclusion"],
        "selection": _json_safe(result["selection"]),
        "overlay_metrics": _json_safe(result["overlay_metrics"]),
        "prediction_metrics": _json_safe(result["prediction_metrics"]),
        "benchmarks": _json_safe(result["benchmarks"]),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_expansion_tier1_overlay(output_dir: str | Path = "reports/expansion_tier1_overlay") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_expansion_tier1_overlay(panel, macro, public_data, probability)
    write_expansion_tier1_overlay_reports(output_dir, result)
    return result


__all__ = [
    "DEFAULT_TIER1_FEATURES",
    "DEVELOPMENT_START_TIER1",
    "run_expansion_tier1_overlay",
    "write_expansion_tier1_overlay_reports",
    "run_default_expansion_tier1_overlay",
]
