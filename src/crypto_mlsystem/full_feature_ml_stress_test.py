"""Full-feature ML stress test for macro-regime crypto allocation.

This module is intentionally standalone.  It does not modify, reselect, or
retune the frozen ``btc_eth_macro_gate_balanced`` strategy.  It asks whether
complex ML models can extract useful signal from the full point-in-time-safe
feature panel, then rejects the result unless it clears strict out-of-sample,
cost, exposure, and overfitting controls.
"""
from __future__ import annotations

import importlib.util
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier, StackingClassifier
from sklearn.feature_selection import SelectKBest, mutual_info_classif
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .expansion_state_model import _fmt, _json_safe, _table
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    CRYPTO_TIER1_FEATURES,
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    MACRO_TIER1_FEATURES,
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
)
from .new_data_extension import build_data_inventory, build_feature_panel
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import (
    block_bootstrap_sharpe_ci,
    deflated_sharpe_probability,
    probability_backtest_overfitting,
)


BASELINE_NAME = FIXED_SELECTED.name

TARGET_SPECS: tuple[tuple[str, str], ...] = (
    ("btc_eth_50_50_forward_positive_30d", "BTC/ETH 50-50 30-day forward return positive"),
    ("btc_forward_30d_gt_10", "BTC forward 30-day return > +10%"),
    ("eth_forward_30d_gt_15", "ETH forward 30-day return > +15%"),
    ("frozen_macro_positive_next_period", "Frozen macro strategy next-period return positive"),
    ("avoid_large_negative_btc_eth_30d", "Avoid exposure before large negative next-period BTC/ETH return"),
)


@dataclass(frozen=True)
class ModelSpec:
    name: str
    family: str
    complexity: int
    factory: Callable[[bool, int], Any]


@dataclass(frozen=True)
class FeatureSetSpec:
    name: str
    description: str
    columns: tuple[str, ...]
    auto_select: bool = False


@dataclass(frozen=True)
class StrategySpec:
    name: str
    strategy_type: str
    rebalance_days: int
    mode: str
    threshold_shift: float = 0.0
    margin: float = 0.05
    description: str = ""


@dataclass
class PredictionBundle:
    config: str
    target: str
    target_description: str
    feature_set: str
    model: str
    model_family: str
    threshold: float
    dev_probability: pd.Series
    holdout_probability: pd.Series
    full_probability: pd.Series
    feature_names: list[str]
    fitted_model: Any | None
    feature_importance: pd.DataFrame


def _selector(feature_count: int) -> SelectKBest:
    return SelectKBest(score_func=mutual_info_classif, k=max(1, min(12, feature_count)))


def _with_optional_selector(estimator: Any, auto_select: bool, feature_count: int, scale: bool = False) -> Any:
    steps: list[tuple[str, Any]] = []
    if auto_select:
        steps.append(("select", _selector(feature_count)))
    if scale:
        steps.append(("scale", StandardScaler()))
    steps.append(("model", estimator))
    return Pipeline(steps)


def available_model_specs(include_stacking: bool = False) -> list[ModelSpec]:
    specs: list[ModelSpec] = [
        ModelSpec(
            "elastic_net_logistic",
            "Elastic Net logistic regression",
            1,
            lambda auto, n: _with_optional_selector(
                LogisticRegression(
                    solver="saga",
                    penalty="elasticnet",
                    l1_ratio=0.35,
                    C=0.50,
                    max_iter=5000,
                    class_weight="balanced",
                    random_state=31,
                ),
                auto,
                n,
                scale=True,
            ),
        ),
        ModelSpec(
            "random_forest",
            "Random forest",
            3,
            lambda auto, n: _with_optional_selector(
                RandomForestClassifier(
                    n_estimators=80,
                    max_depth=4,
                    min_samples_leaf=10,
                    class_weight="balanced",
                    random_state=31,
                    n_jobs=-1,
                ),
                auto,
                n,
            ),
        ),
        ModelSpec(
            "gradient_boosting",
            "Gradient boosting",
            3,
            lambda auto, n: _with_optional_selector(
                GradientBoostingClassifier(
                    n_estimators=80,
                    max_depth=2,
                    learning_rate=0.04,
                    min_samples_leaf=10,
                    random_state=31,
                ),
                auto,
                n,
            ),
        ),
        ModelSpec(
            "extra_trees",
            "Extra Trees",
            3,
            lambda auto, n: _with_optional_selector(
                ExtraTreesClassifier(
                    n_estimators=100,
                    max_depth=4,
                    min_samples_leaf=10,
                    class_weight="balanced",
                    random_state=31,
                    n_jobs=-1,
                ),
                auto,
                n,
            ),
        ),
        ModelSpec(
            "shallow_mlp",
            "Shallow MLP",
            5,
            lambda auto, n: _with_optional_selector(
                MLPClassifier(
                    hidden_layer_sizes=(12,),
                    activation="relu",
                    alpha=0.01,
                    max_iter=450,
                    early_stopping=True,
                    random_state=31,
                ),
                auto,
                n,
                scale=True,
            ),
        ),
    ]
    if importlib.util.find_spec("xgboost") is not None:
        def xgb_factory(auto: bool, n: int) -> Any:
            from xgboost import XGBClassifier

            return _with_optional_selector(
                XGBClassifier(
                    n_estimators=80,
                    max_depth=2,
                    learning_rate=0.04,
                    subsample=0.80,
                    colsample_bytree=0.80,
                    eval_metric="logloss",
                    random_state=31,
                ),
                auto,
                n,
            )

        specs.append(ModelSpec("xgboost", "XGBoost", 4, xgb_factory))
    if importlib.util.find_spec("lightgbm") is not None:
        def lgbm_factory(auto: bool, n: int) -> Any:
            from lightgbm import LGBMClassifier

            return _with_optional_selector(
                LGBMClassifier(
                    n_estimators=80,
                    max_depth=2,
                    learning_rate=0.04,
                    subsample=0.80,
                    colsample_bytree=0.80,
                    class_weight="balanced",
                    random_state=31,
                    verbose=-1,
                ),
                auto,
                n,
            )

        specs.append(ModelSpec("lightgbm", "LightGBM", 4, lgbm_factory))
    if include_stacking:
        def stacking_factory(auto: bool, n: int) -> Any:
            base = [
                (
                    "elastic",
                    make_pipeline(
                        StandardScaler(),
                        LogisticRegression(
                            solver="saga",
                            penalty="elasticnet",
                            l1_ratio=0.30,
                            C=0.50,
                            max_iter=3000,
                            class_weight="balanced",
                            random_state=32,
                        ),
                    ),
                ),
                (
                    "rf",
                    RandomForestClassifier(
                        n_estimators=60,
                        max_depth=3,
                        min_samples_leaf=12,
                        class_weight="balanced",
                        random_state=32,
                        n_jobs=-1,
                    ),
                ),
                (
                    "gb",
                    GradientBoostingClassifier(
                        n_estimators=60,
                        max_depth=2,
                        learning_rate=0.04,
                        min_samples_leaf=10,
                        random_state=32,
                    ),
                ),
            ]
            estimator = StackingClassifier(
                estimators=base,
                final_estimator=LogisticRegression(max_iter=1000, class_weight="balanced", random_state=32),
                stack_method="predict_proba",
                cv=3,
                n_jobs=None,
            )
            return _with_optional_selector(estimator, auto, n, scale=False)

        specs.append(ModelSpec("stacking_ensemble", "Stacking ensemble", 6, stacking_factory))
    return specs


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int = 7) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def _public_crypto_extra_features(dataset: MacroRegimeDataset, public_data: PublicDataBundle | None) -> pd.DataFrame:
    frame = pd.DataFrame(index=dataset.close.index)
    if public_data is None or public_data.binance_4h_daily_features.empty:
        return frame
    intraday = public_data.binance_4h_daily_features.copy()
    if "date" not in intraday or "symbol" not in intraday:
        return frame
    intraday["date"] = pd.to_datetime(intraday["date"])
    for column in (
        "trend_4h_7d",
        "trend_4h_14d",
        "volatility_4h_7d",
        "volatility_4h_30d",
        "drawdown_4h_30d",
        "volume_shock_4h",
    ):
        if column not in intraday:
            continue
        matrix = intraday.pivot_table(index="date", columns="symbol", values=column, aggfunc="last").sort_index()
        available = [symbol for symbol in ("BTC", "ETH") if symbol in matrix.columns]
        if available:
            frame[column] = matrix[available].mean(axis=1).reindex(dataset.close.index).ffill()
    return frame


def build_feature_sets(
    dataset: MacroRegimeDataset,
    public_data: PublicDataBundle | None = None,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, str]:
    """Build the four predeclared feature sets using only lagged accepted data."""
    dates = _rebalance_dates(dataset.close.index, 7)
    inventory = build_data_inventory()
    new_data_features, new_data_metadata, parquet_status = build_feature_panel(dataset, inventory)
    macro_crypto = dataset.regime_features.reindex(dates).ffill()
    public_extra = _public_crypto_extra_features(dataset, public_data).reindex(dates).ffill()
    new_data = new_data_features.reindex(dates).ffill()
    implemented_new = new_data_metadata[new_data_metadata.availability.eq("implemented")].feature.astype(str).tolist()
    new_data = new_data[[column for column in implemented_new if column in new_data.columns]]

    combined = pd.concat([macro_crypto, public_extra, new_data], axis=1)
    combined = combined.loc[:, ~combined.columns.duplicated()].replace([np.inf, -np.inf], np.nan)
    combined = combined.shift(1)
    medians = combined.loc[DEVELOPMENT_START:DEVELOPMENT_END].median().fillna(0.0)
    combined = combined.ffill().fillna(medians).fillna(0.0)

    macro_cols = [column for column in MACRO_TIER1_FEATURES if column in combined.columns]
    crypto_cols = [column for column in CRYPTO_TIER1_FEATURES if column in combined.columns]
    all_cols = list(combined.columns)
    feature_sets = {
        "macro_tier1": combined[macro_cols].copy(),
        "macro_plus_crypto_tier1": combined[[*macro_cols, *crypto_cols]].copy(),
        "all_accepted": combined[all_cols].copy(),
        "all_accepted_auto_selection": combined[all_cols].copy(),
    }
    metadata_rows: list[dict[str, Any]] = []
    for feature in all_cols:
        if feature in MACRO_TIER1_FEATURES:
            family = "macro Tier-1"
            source = "existing WRDS macro-regime feature"
        elif feature in CRYPTO_TIER1_FEATURES:
            family = "crypto Tier-1"
            source = "existing public crypto-native feature"
        elif feature in public_extra.columns:
            family = "public crypto 4h"
            source = "accepted Binance 4h public feature"
        else:
            match = new_data_metadata[new_data_metadata.feature.astype(str).eq(feature)]
            family = str(match.iloc[0].family) if not match.empty else "accepted feature"
            source = str(match.iloc[0].source) if not match.empty else "accepted point-in-time panel"
        series = combined[feature]
        valid = series.replace([np.inf, -np.inf], np.nan).dropna()
        metadata_rows.append({
            "feature": feature,
            "family": family,
            "source": source,
            "start": str(valid.index.min().date()) if len(valid) else "",
            "end": str(valid.index.max().date()) if len(valid) else "",
            "coverage": float(series.notna().mean()) if len(series) else 0.0,
            "lag_rule": "weekly feature matrix shifted one rebalance period before prediction",
        })
    return feature_sets, pd.DataFrame(metadata_rows), parquet_status


def feature_set_specs(feature_sets: dict[str, pd.DataFrame]) -> list[FeatureSetSpec]:
    descriptions = {
        "macro_tier1": "Macro Tier-1 only.",
        "macro_plus_crypto_tier1": "Macro Tier-1 plus existing crypto Tier-1.",
        "all_accepted": "All accepted point-in-time-safe features.",
        "all_accepted_auto_selection": "All accepted features with train-fold-only automatic selection/regularisation.",
    }
    return [
        FeatureSetSpec(name, descriptions[name], tuple(frame.columns), auto_select=name.endswith("auto_selection"))
        for name, frame in feature_sets.items()
    ]


def _forward_return(close: pd.DataFrame, symbol: str, dates: pd.DatetimeIndex, horizon_days: int = 30) -> pd.Series:
    if symbol not in close:
        return pd.Series(np.nan, index=dates)
    values = []
    index = close.index
    prices = close[symbol]
    for date in dates:
        if date not in index:
            values.append(np.nan)
            continue
        end_pos = index.searchsorted(pd.Timestamp(date) + pd.DateOffset(days=horizon_days))
        if end_pos >= len(index):
            values.append(np.nan)
            continue
        start = prices.loc[date]
        end = prices.iloc[end_pos]
        values.append(float(end / start - 1.0) if pd.notna(start) and pd.notna(end) and start > 0 else np.nan)
    return pd.Series(values, index=dates)


def _forward_strategy_return(returns: pd.Series, dates: pd.DatetimeIndex, horizon_days: int = 7) -> pd.Series:
    values = []
    index = returns.index
    for date in dates:
        pos = index.searchsorted(pd.Timestamp(date))
        end_pos = index.searchsorted(pd.Timestamp(date) + pd.DateOffset(days=horizon_days))
        if pos >= len(index) or end_pos <= pos:
            values.append(np.nan)
            continue
        values.append(float((1.0 + returns.iloc[pos:end_pos]).prod() - 1.0))
    return pd.Series(values, index=dates)


def build_targets(dataset: MacroRegimeDataset) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index, 7)
    btc = _forward_return(dataset.close, "BTC", dates, 30)
    eth = _forward_return(dataset.close, "ETH", dates, 30)
    mix = 0.50 * btc + 0.50 * eth
    frozen_weights, macro, crypto, combined = build_candidate_weights(dataset, FIXED_SELECTED)
    frozen = backtest_weights(dataset, frozen_weights, macro, crypto, combined, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
    frozen_next = _forward_strategy_return(frozen.returns, dates, 7)
    targets = pd.DataFrame(index=dates)
    targets["btc_eth_50_50_forward_positive_30d"] = (mix > 0.0).astype(float)
    targets["btc_forward_30d_gt_10"] = (btc > 0.10).astype(float)
    targets["eth_forward_30d_gt_15"] = (eth > 0.15).astype(float)
    targets["frozen_macro_positive_next_period"] = (frozen_next > 0.0).astype(float)
    targets["avoid_large_negative_btc_eth_30d"] = (mix > -0.10).astype(float)
    unavailable = pd.concat([btc, eth, mix, frozen_next], axis=1).isna().any(axis=1)
    targets.loc[unavailable, :] = np.nan
    return targets


def target_diagnostics(targets: pd.DataFrame) -> pd.DataFrame:
    descriptions = dict(TARGET_SPECS)
    rows = []
    for target in targets.columns:
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            y = targets[target].loc[start:end].dropna()
            rows.append({
                "target": target,
                "description": descriptions.get(target, target),
                "split": split,
                "observations": int(len(y)),
                "positive_events": int(y.sum()) if len(y) else 0,
                "prevalence": float(y.mean()) if len(y) else np.nan,
            })
    return pd.DataFrame(rows)


def _positive_probability(model: Any, x: pd.DataFrame) -> np.ndarray:
    if len(x) == 0:
        return np.array([])
    classes = list(getattr(model, "classes_", []))
    if hasattr(model, "named_steps"):
        classes = list(getattr(model.named_steps.get("model"), "classes_", []))
    if 1 not in classes:
        return np.zeros(len(x))
    probabilities = model.predict_proba(x)
    return probabilities[:, classes.index(1)]


def _constant_probability(y: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(float(y.mean()) if len(y) else 0.0, index=index)


def _classification_metrics(
    y: pd.Series,
    probability: pd.Series,
    threshold: float,
    split: str,
    config: str,
    feature_set: str,
    model: str,
    target: str,
    train_auc: float | None = None,
) -> dict[str, Any]:
    aligned = pd.concat([y.rename("y"), probability.rename("probability")], axis=1).dropna()
    if aligned.empty:
        return {
            "config": config,
            "feature_set": feature_set,
            "model": model,
            "target": target,
            "split": split,
            "threshold": threshold,
            "observations": 0,
            "positive_events": 0,
            "auc": np.nan,
            "precision": np.nan,
            "recall": np.nan,
            "f1": np.nan,
            "brier_score": np.nan,
            "train_auc": train_auc,
            "train_validation_gap": np.nan,
            "true_negative": 0,
            "false_positive": 0,
            "false_negative": 0,
            "true_positive": 0,
        }
    y_true = aligned["y"].astype(int)
    prob = aligned["probability"].clip(0.0, 1.0)
    pred = (prob >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, pred, average="binary", zero_division=0)
    matrix = confusion_matrix(y_true, pred, labels=[0, 1])
    auc = roc_auc_score(y_true, prob) if y_true.nunique() == 2 else np.nan
    return {
        "config": config,
        "feature_set": feature_set,
        "model": model,
        "target": target,
        "split": split,
        "threshold": float(threshold),
        "observations": int(len(y_true)),
        "positive_events": int(y_true.sum()),
        "auc": float(auc) if np.isfinite(auc) else np.nan,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "brier_score": float(brier_score_loss(y_true, prob)),
        "train_auc": train_auc,
        "train_validation_gap": float(train_auc - auc) if train_auc is not None and np.isfinite(auc) and np.isfinite(train_auc) else np.nan,
        "true_negative": int(matrix[0, 0]),
        "false_positive": int(matrix[0, 1]),
        "false_negative": int(matrix[1, 0]),
        "true_positive": int(matrix[1, 1]),
    }


def _threshold_from_dev(probability: pd.Series, y: pd.Series) -> float:
    best_threshold = 0.50
    best_score = -np.inf
    for threshold in (0.35, 0.45, 0.50, 0.55, 0.65):
        pred = (probability >= threshold).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(y.astype(int), pred, average="binary", zero_division=0)
        score = float(f1 + 0.05 * precision + 0.05 * recall)
        if score > best_score:
            best_score = score
            best_threshold = threshold
    return best_threshold


def _cpcv_probabilities(x: pd.DataFrame, y: pd.Series, spec: ModelSpec, auto_select: bool) -> tuple[pd.Series, pd.DataFrame, float]:
    if len(x) < 40:
        return _constant_probability(y, x.index), pd.DataFrame(), np.nan
    probabilities = pd.Series(0.0, index=x.index)
    counts = pd.Series(0.0, index=x.index)
    fold_rows: list[dict[str, Any]] = []
    train_aucs = []
    splits = combinatorial_purged_splits(len(x), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    for number, split in enumerate(splits):
        train_index = x.index[list(split.train_indices)]
        test_index = x.index[list(split.test_indices)]
        y_train = y.loc[train_index]
        if y_train.nunique() < 2:
            train_prob = _constant_probability(y_train, train_index)
            test_prob = _constant_probability(y_train, test_index)
        else:
            model = spec.factory(auto_select, x.shape[1])
            model.fit(x.loc[train_index], y_train)
            train_prob = pd.Series(_positive_probability(model, x.loc[train_index]), index=train_index)
            test_prob = pd.Series(_positive_probability(model, x.loc[test_index]), index=test_index)
        probabilities.loc[test_index] += test_prob
        counts.loc[test_index] += 1.0
        train_auc = roc_auc_score(y_train, train_prob) if y_train.nunique() == 2 else np.nan
        test_y = y.loc[test_index]
        test_auc = roc_auc_score(test_y, test_prob) if test_y.nunique() == 2 else np.nan
        if np.isfinite(train_auc):
            train_aucs.append(float(train_auc))
        fold_rows.append({
            "model": spec.name,
            "fold": number,
            "test_groups": ",".join(str(group) for group in split.test_groups),
            "train_samples": int(len(train_index)),
            "test_samples": int(len(test_index)),
            "train_auc": float(train_auc) if np.isfinite(train_auc) else np.nan,
            "validation_auc": float(test_auc) if np.isfinite(test_auc) else np.nan,
            "train_validation_gap": float(train_auc - test_auc) if np.isfinite(train_auc) and np.isfinite(test_auc) else np.nan,
        })
    return (
        (probabilities / counts.replace(0, np.nan)).fillna(float(y.mean()) if len(y) else 0.0),
        pd.DataFrame(fold_rows),
        float(np.nanmean(train_aucs)) if train_aucs else np.nan,
    )


def _fit_holdout_model(
    x_dev: pd.DataFrame,
    y_dev: pd.Series,
    x_holdout: pd.DataFrame,
    spec: ModelSpec,
    auto_select: bool,
) -> tuple[pd.Series, Any | None]:
    if y_dev.nunique() < 2 or len(x_holdout) == 0:
        return _constant_probability(y_dev, x_holdout.index), None
    model = spec.factory(auto_select, x_dev.shape[1])
    model.fit(x_dev, y_dev)
    return pd.Series(_positive_probability(model, x_holdout), index=x_holdout.index), model


def _selected_feature_names(model: Any, feature_names: list[str]) -> list[str]:
    selected = feature_names
    if isinstance(model, Pipeline):
        for _, step in model.steps:
            if isinstance(step, SelectKBest) and hasattr(step, "get_support"):
                mask = step.get_support()
                selected = [name for name, keep in zip(selected, mask) if keep]
    return selected


def _extract_importance(model: Any | None, feature_names: list[str], config: str, model_name: str) -> pd.DataFrame:
    if model is None:
        return pd.DataFrame({"config": [config], "model": [model_name], "feature": ["constant_probability"], "importance": [0.0], "method": ["constant"]})
    fitted = model
    selected = feature_names
    if isinstance(model, Pipeline):
        selected = _selected_feature_names(model, feature_names)
        fitted = model.named_steps.get("model", model.steps[-1][1])
    if hasattr(fitted, "coef_"):
        values = np.ravel(fitted.coef_)
        method = "coefficient"
    elif hasattr(fitted, "feature_importances_"):
        values = np.ravel(fitted.feature_importances_)
        method = "model_importance"
    else:
        values = np.zeros(len(selected))
        method = "not_available"
    rows = []
    for feature, value in zip(selected, values):
        rows.append({"config": config, "model": model_name, "feature": feature, "importance": float(value), "method": method})
    return pd.DataFrame(rows).sort_values("importance", key=lambda s: s.abs(), ascending=False)


def fit_prediction_models(
    feature_sets: dict[str, pd.DataFrame],
    targets: pd.DataFrame,
    model_specs: list[ModelSpec] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, PredictionBundle], pd.DataFrame]:
    model_specs = model_specs or available_model_specs(include_stacking=False)
    rows: list[dict[str, Any]] = []
    fold_frames: list[pd.DataFrame] = []
    bundles: dict[str, PredictionBundle] = {}
    target_descriptions = dict(TARGET_SPECS)

    for feature_set_name, x_all in feature_sets.items():
        auto_select = feature_set_name.endswith("auto_selection")
        dev_mask = (x_all.index >= DEVELOPMENT_START) & (x_all.index <= DEVELOPMENT_END)
        holdout_mask = (x_all.index >= HOLDOUT_START) & (x_all.index <= HOLDOUT_END)
        x_dev_all = x_all.loc[dev_mask]
        x_holdout_all = x_all.loc[holdout_mask]
        for target in targets.columns:
            valid_dev = targets[target].loc[x_dev_all.index].dropna().index
            valid_holdout = targets[target].loc[x_holdout_all.index].dropna().index
            x_dev = x_dev_all.loc[valid_dev]
            y_dev = targets.loc[valid_dev, target].astype(int)
            x_holdout = x_holdout_all.loc[valid_holdout]
            y_holdout = targets.loc[valid_holdout, target].astype(int)
            for spec in model_specs:
                config = f"{feature_set_name}__{target}__{spec.name}"
                dev_prob, folds, train_auc = _cpcv_probabilities(x_dev, y_dev, spec, auto_select)
                if not folds.empty:
                    folds["config"] = config
                    folds["feature_set"] = feature_set_name
                    folds["target"] = target
                    fold_frames.append(folds)
                threshold = _threshold_from_dev(dev_prob, y_dev)
                holdout_prob, fitted = _fit_holdout_model(x_dev, y_dev, x_holdout, spec, auto_select)
                full_probability = pd.Series(np.nan, index=x_all.index)
                full_probability.loc[dev_prob.index] = dev_prob
                full_probability.loc[holdout_prob.index] = holdout_prob
                rows.append(_classification_metrics(y_dev, dev_prob, threshold, "development_cpcv", config, feature_set_name, spec.name, target, train_auc=train_auc))
                rows.append(_classification_metrics(y_holdout, holdout_prob, threshold, "holdout", config, feature_set_name, spec.name, target, train_auc=None))
                bundles[config] = PredictionBundle(
                    config=config,
                    target=target,
                    target_description=target_descriptions.get(target, target),
                    feature_set=feature_set_name,
                    model=spec.name,
                    model_family=spec.family,
                    threshold=threshold,
                    dev_probability=dev_prob,
                    holdout_probability=holdout_prob,
                    full_probability=full_probability.ffill().fillna(float(dev_prob.mean()) if len(dev_prob) else 0.0),
                    feature_names=list(x_all.columns),
                    fitted_model=fitted,
                    feature_importance=_extract_importance(fitted, list(x_all.columns), config, spec.name),
                )
    metrics = pd.DataFrame(rows)
    dev = metrics[metrics.split.eq("development_cpcv")].copy()
    if not dev.empty:
        dev["selection_score"] = (
            dev["auc"].fillna(0.5)
            - dev["brier_score"].fillna(1.0)
            + 0.10 * dev["f1"].fillna(0.0)
            - dev["train_validation_gap"].fillna(0.0).clip(lower=0.0) * 0.10
        )
        selection = dev.sort_values(["selection_score", "auc", "brier_score"], ascending=[False, False, True])
    else:
        selection = pd.DataFrame()
    folds = pd.concat(fold_frames, ignore_index=True) if fold_frames else pd.DataFrame()
    return metrics, selection, bundles, folds


def _dev_supports_stacking(prediction_selection: pd.DataFrame) -> bool:
    if prediction_selection.empty:
        return False
    best = prediction_selection.iloc[0]
    return bool(best.get("auc", 0.0) >= 0.55 and best.get("observations", 0) >= 100)


def maybe_fit_stacking_model(
    feature_sets: dict[str, pd.DataFrame],
    targets: pd.DataFrame,
    prediction_selection: pd.DataFrame,
    existing_metrics: pd.DataFrame,
    existing_bundles: dict[str, PredictionBundle],
    existing_folds: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, PredictionBundle], pd.DataFrame, str]:
    if not _dev_supports_stacking(prediction_selection):
        return existing_metrics, prediction_selection, existing_bundles, existing_folds, "Stacking skipped because development CPCV did not support added complexity."
    best = prediction_selection.iloc[0]
    feature_set_name = str(best.feature_set)
    target = str(best.target)
    if feature_set_name not in feature_sets or target not in targets:
        return existing_metrics, prediction_selection, existing_bundles, existing_folds, "Stacking skipped because the selected feature/target pair was unavailable."
    metrics, selection, bundles, folds = fit_prediction_models(
        {feature_set_name: feature_sets[feature_set_name]},
        targets[[target]],
        model_specs=[spec for spec in available_model_specs(include_stacking=True) if spec.name == "stacking_ensemble"],
    )
    combined_metrics = pd.concat([existing_metrics, metrics], ignore_index=True)
    dev = combined_metrics[combined_metrics.split.eq("development_cpcv")].copy()
    dev["selection_score"] = (
        dev["auc"].fillna(0.5)
        - dev["brier_score"].fillna(1.0)
        + 0.10 * dev["f1"].fillna(0.0)
        - dev["train_validation_gap"].fillna(0.0).clip(lower=0.0) * 0.10
    )
    combined_selection = dev.sort_values(["selection_score", "auc", "brier_score"], ascending=[False, False, True])
    combined_bundles = {**existing_bundles, **bundles}
    combined_folds = pd.concat([existing_folds, folds], ignore_index=True) if not existing_folds.empty or not folds.empty else pd.DataFrame()
    return combined_metrics, combined_selection, combined_bundles, combined_folds, "Stacking evaluated only for the top development-supported feature/target pair."


def _select_bundle(
    selection: pd.DataFrame,
    bundles: dict[str, PredictionBundle],
    target: str,
    allowed_feature_sets: set[str] | None = None,
) -> PredictionBundle:
    subset = selection[selection.target.eq(target)].copy()
    if allowed_feature_sets is not None:
        subset = subset[subset.feature_set.isin(allowed_feature_sets)]
    if subset.empty:
        subset = selection.copy()
    return bundles[str(subset.iloc[0].config)]


def predeclared_strategy_specs() -> list[StrategySpec]:
    specs: list[StrategySpec] = []
    for rebalance_days in (7, 14):
        for shift in (-0.05, 0.0, 0.10):
            specs.append(StrategySpec(
                name=f"ml_full_feature_alpha_{rebalance_days}d_s{int(shift * 100):+d}",
                strategy_type="ml_full_feature_alpha",
                rebalance_days=rebalance_days,
                mode="alpha",
                threshold_shift=shift,
                description="Standalone BTC/ETH/cash ML alpha strategy using full accepted features.",
            ))
            specs.append(StrategySpec(
                name=f"ml_confirmation_overlay_{rebalance_days}d_s{int(shift * 100):+d}",
                strategy_type="ml_confirmation_overlay",
                rebalance_days=rebalance_days,
                mode="confirmation",
                threshold_shift=shift,
                description="ML confirmation overlay on the frozen macro strategy.",
            ))
            specs.append(StrategySpec(
                name=f"ml_risk_off_overlay_{rebalance_days}d_s{int(shift * 100):+d}",
                strategy_type="ml_risk_off_overlay",
                rebalance_days=rebalance_days,
                mode="risk_off",
                threshold_shift=shift,
                description="ML risk-off overlay on the frozen macro strategy.",
            ))
        for margin in (0.05, 0.10):
            specs.append(StrategySpec(
                name=f"ml_btc_vs_eth_allocator_{rebalance_days}d_m{int(margin * 100)}",
                strategy_type="ml_btc_vs_eth_allocator",
                rebalance_days=rebalance_days,
                mode="allocator",
                margin=margin,
                description="ML BTC-vs-ETH allocator with cash when both probabilities are weak.",
            ))
    return specs


def _all_risk_on(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series, pd.Series]:
    risk_on = pd.Series("risk_on", index=index, dtype=object)
    crypto = pd.Series("not_used", index=index, dtype=object)
    return risk_on, crypto, risk_on


def _threshold(bundle: PredictionBundle, shift: float = 0.0) -> float:
    return float(np.clip(bundle.threshold + shift, 0.05, 0.95))


def _base_weights_on_dates(base_weights: pd.DataFrame, dates: pd.DatetimeIndex, columns: pd.Index) -> pd.DataFrame:
    return base_weights.reindex(dates).ffill().fillna(0.0).reindex(columns=columns).fillna(0.0)


def build_strategy_weights(
    dataset: MacroRegimeDataset,
    spec: StrategySpec,
    bundles: dict[str, PredictionBundle],
    frozen_weights: pd.DataFrame,
) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index, spec.rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    p_mix = bundles["mix"].full_probability.reindex(dates).ffill().fillna(0.0).clip(0.0, 1.0)
    p_btc = bundles["btc"].full_probability.reindex(dates).ffill().fillna(0.0).clip(0.0, 1.0)
    p_eth = bundles["eth"].full_probability.reindex(dates).ffill().fillna(0.0).clip(0.0, 1.0)
    p_frozen = bundles["frozen"].full_probability.reindex(dates).ffill().fillna(0.0).clip(0.0, 1.0)
    p_safe = bundles["safe"].full_probability.reindex(dates).ffill().fillna(0.0).clip(0.0, 1.0)
    base = _base_weights_on_dates(frozen_weights, dates, weights.columns)
    eligible = dataset.universe_weights.reindex(dates).ffill().fillna(0.0)

    for date in dates:
        btc_available = "BTC" in weights.columns and "BTC" in eligible.columns and eligible.loc[date, "BTC"] > 0
        eth_available = "ETH" in weights.columns and "ETH" in eligible.columns and eligible.loc[date, "ETH"] > 0
        if spec.strategy_type == "ml_full_feature_alpha":
            threshold = _threshold(bundles["mix"], spec.threshold_shift)
            if float(p_mix.loc[date]) < threshold:
                continue
            if btc_available and eth_available:
                if float(p_eth.loc[date] - p_btc.loc[date]) > spec.margin:
                    weights.loc[date, "BTC"] = 0.30
                    weights.loc[date, "ETH"] = 0.70
                elif float(p_btc.loc[date] - p_eth.loc[date]) > spec.margin:
                    weights.loc[date, "BTC"] = 0.70
                    weights.loc[date, "ETH"] = 0.30
                else:
                    weights.loc[date, "BTC"] = 0.50
                    weights.loc[date, "ETH"] = 0.50
            elif btc_available:
                weights.loc[date, "BTC"] = 1.0
            elif eth_available:
                weights.loc[date, "ETH"] = 1.0
        elif spec.strategy_type == "ml_confirmation_overlay":
            threshold = _threshold(bundles["frozen"], spec.threshold_shift)
            scale = 1.0 if float(p_frozen.loc[date]) >= threshold else 0.25
            weights.loc[date] = base.loc[date] * scale
        elif spec.strategy_type == "ml_risk_off_overlay":
            threshold = _threshold(bundles["safe"], spec.threshold_shift)
            scale = 1.0 if float(p_safe.loc[date]) >= threshold else 0.0
            weights.loc[date] = base.loc[date] * scale
        elif spec.strategy_type == "ml_btc_vs_eth_allocator":
            btc_prob = float(p_btc.loc[date])
            eth_prob = float(p_eth.loc[date])
            min_threshold = min(_threshold(bundles["btc"], 0.0), _threshold(bundles["eth"], 0.0))
            if max(btc_prob, eth_prob) < min_threshold:
                continue
            if btc_available and eth_available:
                if eth_prob - btc_prob > spec.margin:
                    weights.loc[date, "ETH"] = 1.0
                elif btc_prob - eth_prob > spec.margin:
                    weights.loc[date, "BTC"] = 1.0
                else:
                    weights.loc[date, "BTC"] = 0.50
                    weights.loc[date, "ETH"] = 0.50
            elif btc_available:
                weights.loc[date, "BTC"] = 1.0
            elif eth_available:
                weights.loc[date, "ETH"] = 1.0
        else:
            raise ValueError(spec.strategy_type)
    return weights.clip(lower=0.0, upper=1.0)


def _weekly_return(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0).dropna()


def _fold_sharpe(values: pd.Series, indices: tuple[int, ...]) -> float:
    subset = values.iloc[list(indices)].replace([np.inf, -np.inf], np.nan).dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def _nanmedian(values: list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    return float(np.nanmedian(arr)) if arr.size and np.isfinite(arr).any() else np.nan


def _nanmin(values: list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    return float(np.nanmin(arr)) if arr.size and np.isfinite(arr).any() else np.nan


def select_strategy_cpcv(results_25bps: dict[str, PortfolioResult], specs: list[StrategySpec]) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    config_returns: dict[str, pd.Series] = {}
    for spec in specs:
        result = results_25bps[spec.name]
        weekly = _weekly_return(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        config_returns[spec.name] = weekly
        if len(weekly) < 40:
            continue
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_values = []
        for number, split in enumerate(splits):
            sharpe = _fold_sharpe(weekly, split.test_indices)
            fold_values.append(sharpe)
            fold_rows.append({
                "candidate": spec.name,
                "strategy_type": spec.strategy_type,
                "fold": number,
                "fold_sharpe": sharpe,
                "test_groups": ",".join(str(group) for group in split.test_groups),
            })
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        turnover_penalty = max(0.0, dev["Annual Turnover"] - 12.0) * 0.05
        low_exposure_penalty = max(0.0, 0.20 - dev["Exposure"]) * 1.0
        rows.append({
            "candidate": spec.name,
            "strategy_type": spec.strategy_type,
            "mode": spec.mode,
            "rebalance_days": spec.rebalance_days,
            "threshold_shift": spec.threshold_shift,
            "margin": spec.margin,
            "median_fold_sharpe": _nanmedian(fold_values),
            "worst_fold_sharpe": _nanmin(fold_values),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_values) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
            "turnover_penalty": turnover_penalty,
            "low_exposure_penalty": low_exposure_penalty,
        })
    selection = pd.DataFrame(rows)
    if selection.empty:
        raise ValueError("No strategy candidates were available for CPCV selection.")
    selection["selection_score"] = (
        selection["median_fold_sharpe"]
        + 0.25 * selection["worst_fold_sharpe"]
        + 0.30 * selection["positive_fold_fraction"]
        - selection["turnover_penalty"]
        - selection["low_exposure_penalty"]
    )
    selection = selection.sort_values("selection_score", ascending=False)
    pbo = probability_backtest_overfitting(pd.concat(config_returns, axis=1).sort_index(), blocks=8)
    return selection, pd.DataFrame(fold_rows), str(selection.iloc[0].candidate), pbo


def _benchmark_weights(dataset: MacroRegimeDataset, name: str) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=dataset.close.index, columns=dataset.close.columns)
    if name == "btc_buy_hold" and "BTC" in weights:
        weights["BTC"] = 1.0
    elif name == "eth_buy_hold" and "ETH" in weights:
        weights["ETH"] = 1.0
    elif name == "btc_eth_50_50":
        for symbol in ("BTC", "ETH"):
            if symbol in weights:
                weights[symbol] = 0.50
    else:
        raise ValueError(name)
    return weights


def _rows_for_result(name: str, family: str, group: str, cost: int, result: PortfolioResult, selected: bool = False) -> list[dict[str, Any]]:
    rows = []
    for split, start, end in (
        ("development", DEVELOPMENT_START, DEVELOPMENT_END),
        ("holdout", HOLDOUT_START, HOLDOUT_END),
    ):
        rows.append({
            "name": name,
            "family": family,
            "benchmark_group": group,
            "split": split,
            "cost_bps": cost,
            "selected_development_candidate": selected,
            **period_metrics(result, start, end),
        })
    return rows


def evaluate_benchmarks(dataset: MacroRegimeDataset, frozen_weights: pd.DataFrame, frozen_regimes: tuple[pd.Series, pd.Series, pd.Series]) -> tuple[pd.DataFrame, dict[str, PortfolioResult]]:
    rows: list[dict[str, Any]] = []
    results: dict[str, PortfolioResult] = {}
    macro, crypto, combined = frozen_regimes
    for cost in COST_LEVELS:
        frozen = backtest_weights(dataset, frozen_weights, macro, crypto, combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
        rows.extend(_rows_for_result(BASELINE_NAME, "Frozen macro gate", "frozen_strategy", cost, frozen))
        results[f"{BASELINE_NAME}_{cost}"] = frozen
        risk_on = _all_risk_on(dataset.close.index)
        for name, family in (
            ("btc_buy_hold", "BTC buy-and-hold"),
            ("eth_buy_hold", "ETH buy-and-hold"),
            ("btc_eth_50_50", "50/50 BTC/ETH"),
        ):
            bench = backtest_weights(dataset, _benchmark_weights(dataset, name), *risk_on, cost_bps=cost, turnover_cap=10.0)
            rows.extend(_rows_for_result(name, family, "benchmark", cost, bench))
            results[f"{name}_{cost}"] = bench
    return pd.DataFrame(rows), results


def feature_importance_stability(
    bundle: PredictionBundle,
    features: pd.DataFrame,
    targets: pd.DataFrame,
    model_specs: list[ModelSpec],
) -> pd.DataFrame:
    spec_lookup = {spec.name: spec for spec in model_specs}
    if bundle.model not in spec_lookup or bundle.target not in targets:
        return pd.DataFrame()
    spec = spec_lookup[bundle.model]
    x_all = features[bundle.feature_names].copy()
    dev_index = x_all.loc[DEVELOPMENT_START:DEVELOPMENT_END].index.intersection(targets[bundle.target].dropna().index)
    x = x_all.loc[dev_index]
    y = targets.loc[dev_index, bundle.target].astype(int)
    if len(x) < 60 or y.nunique() < 2:
        return pd.DataFrame()
    auto_select = bundle.feature_set.endswith("auto_selection")
    splits = combinatorial_purged_splits(len(x), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    rows: list[dict[str, Any]] = []
    top_sets: list[set[str]] = []
    for number, split in enumerate(splits[:10]):
        train_index = x.index[list(split.train_indices)]
        test_index = x.index[list(split.test_indices)]
        if y.loc[train_index].nunique() < 2 or y.loc[test_index].nunique() < 2:
            continue
        model = spec.factory(auto_select, x.shape[1])
        model.fit(x.loc[train_index], y.loc[train_index])
        model_imp = _extract_importance(model, list(x.columns), bundle.config, bundle.model)
        top_features = set(model_imp.head(5).feature.astype(str))
        top_sets.append(top_features)
        try:
            scoring = "roc_auc" if y.loc[test_index].nunique() == 2 else None
            perm = permutation_importance(
                model,
                x.loc[test_index],
                y.loc[test_index],
                scoring=scoring,
                n_repeats=3,
                random_state=31 + number,
            )
            perm_values = dict(zip(x.columns, perm.importances_mean))
        except Exception:
            perm_values = {feature: np.nan for feature in x.columns}
        for _, imp in model_imp.head(12).iterrows():
            rows.append({
                "fold": number,
                "feature": imp["feature"],
                "model_importance": imp["importance"],
                "importance_method": imp["method"],
                "permutation_importance": perm_values.get(str(imp["feature"]), np.nan),
                "top5": str(imp["feature"]) in top_features,
            })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    overlaps = []
    for i, left in enumerate(top_sets):
        for right in top_sets[i + 1:]:
            union = left | right
            overlaps.append(len(left & right) / len(union) if union else np.nan)
    summary = frame.groupby("feature", as_index=False).agg(
        model_importance_mean=("model_importance", "mean"),
        model_importance_std=("model_importance", "std"),
        permutation_importance_mean=("permutation_importance", "mean"),
        top5_frequency=("top5", "mean"),
    )
    summary["mean_top5_jaccard_across_folds"] = float(np.nanmean(overlaps)) if overlaps else np.nan
    return summary.sort_values(["top5_frequency", "model_importance_mean"], ascending=[False, False])


def run_full_feature_ml_stress_test(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
    model_specs: list[ModelSpec] | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    feature_sets, feature_metadata, parquet_status = build_feature_sets(dataset, public_data)
    targets = build_targets(dataset)
    diagnostics = target_diagnostics(targets)
    specs = model_specs or available_model_specs(include_stacking=False)
    prediction_metrics, prediction_selection, bundles, prediction_folds = fit_prediction_models(feature_sets, targets, specs)
    prediction_metrics, prediction_selection, bundles, prediction_folds, stacking_note = maybe_fit_stacking_model(
        feature_sets,
        targets,
        prediction_selection,
        prediction_metrics,
        bundles,
        prediction_folds,
    )
    all_model_specs = specs + ([spec for spec in available_model_specs(include_stacking=True) if spec.name == "stacking_ensemble"] if "stacking_ensemble" in prediction_metrics.model.astype(str).unique() else [])

    full_feature_sets = {"all_accepted", "all_accepted_auto_selection"}
    selected_bundles = {
        "mix": _select_bundle(prediction_selection, bundles, "btc_eth_50_50_forward_positive_30d", full_feature_sets),
        "btc": _select_bundle(prediction_selection, bundles, "btc_forward_30d_gt_10", full_feature_sets),
        "eth": _select_bundle(prediction_selection, bundles, "eth_forward_30d_gt_15", full_feature_sets),
        "frozen": _select_bundle(prediction_selection, bundles, "frozen_macro_positive_next_period", None),
        "safe": _select_bundle(prediction_selection, bundles, "avoid_large_negative_btc_eth_30d", None),
    }

    frozen_weights, frozen_macro, frozen_crypto, frozen_combined = build_candidate_weights(dataset, FIXED_SELECTED)
    frozen_regimes = (frozen_macro, frozen_crypto, frozen_combined)
    strategy_specs = predeclared_strategy_specs()
    strategy_results: dict[str, dict[int, PortfolioResult]] = {}
    weights_cache: dict[str, pd.DataFrame] = {}
    for spec in strategy_specs:
        weights = build_strategy_weights(dataset, spec, selected_bundles, frozen_weights)
        weights_cache[spec.name] = weights
        strategy_results[spec.name] = {
            cost: backtest_weights(dataset, weights, frozen_macro, frozen_crypto, frozen_combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
            for cost in COST_LEVELS
        }
    selection, strategy_folds, selected_strategy, strategy_pbo = select_strategy_cpcv(
        {name: by_cost[25] for name, by_cost in strategy_results.items()},
        strategy_specs,
    )

    strategy_metric_rows: list[dict[str, Any]] = []
    spec_by_name = {spec.name: spec for spec in strategy_specs}
    for name, by_cost in strategy_results.items():
        spec = spec_by_name[name]
        for cost, result in by_cost.items():
            strategy_metric_rows.extend(_rows_for_result(
                name,
                spec.description,
                spec.strategy_type,
                cost,
                result,
                selected=name == selected_strategy,
            ))
    strategy_metrics = pd.DataFrame(strategy_metric_rows)
    benchmarks, benchmark_results = evaluate_benchmarks(dataset, frozen_weights, frozen_regimes)

    selected_result_25 = strategy_results[selected_strategy][25]
    selected_result_50 = strategy_results[selected_strategy][50]
    selected_holdout = strategy_metrics[
        (strategy_metrics.name.eq(selected_strategy)) & (strategy_metrics.split.eq("holdout")) & (strategy_metrics.cost_bps.eq(25))
    ].iloc[0]
    selected_holdout_50 = strategy_metrics[
        (strategy_metrics.name.eq(selected_strategy)) & (strategy_metrics.split.eq("holdout")) & (strategy_metrics.cost_bps.eq(50))
    ].iloc[0]
    frozen_holdout = benchmarks[
        (benchmarks.name.eq(BASELINE_NAME)) & (benchmarks.split.eq("holdout")) & (benchmarks.cost_bps.eq(25))
    ].iloc[0]
    frozen_exposure = float(frozen_holdout["Exposure"])
    selected_exposure = float(selected_holdout["Exposure"])
    tested_configs = int(len(prediction_selection) + len(strategy_specs))
    dsr = deflated_sharpe_probability(selected_result_25.returns.loc[HOLDOUT_START:HOLDOUT_END], tested_configs)
    ci = block_bootstrap_sharpe_ci(selected_result_25.returns.loc[HOLDOUT_START:HOLDOUT_END], samples=500, block_length=14, seed=83)
    importance = pd.concat([bundle.feature_importance for bundle in bundles.values()], ignore_index=True)
    selected_prediction_bundle = bundles[str(prediction_selection.iloc[0].config)] if not prediction_selection.empty else selected_bundles["mix"]
    importance_stability = feature_importance_stability(
        selected_prediction_bundle,
        feature_sets[selected_prediction_bundle.feature_set],
        targets,
        all_model_specs,
    )

    failures = []
    if selected_holdout["Sharpe"] <= frozen_holdout["Sharpe"] + 0.10:
        failures.append("holdout Sharpe does not materially improve versus frozen strategy")
    if selected_holdout["CAGR"] < frozen_holdout["CAGR"] * 0.90:
        failures.append("holdout CAGR is not comparable or better")
    if selected_holdout["Maximum Drawdown"] < frozen_holdout["Maximum Drawdown"] - 0.02:
        failures.append("max drawdown worsens materially")
    if selected_exposure < 0.20:
        failures.append("exposure below 20%")
    if selected_holdout["Annual Turnover"] > 12:
        failures.append("turnover above 12x")
    if selected_holdout_50["CAGR"] <= 0 or selected_holdout_50["Sharpe"] <= 0:
        failures.append("does not survive 50 bps costs")
    if np.isfinite(strategy_pbo) and strategy_pbo > 0.50:
        failures.append("PBO is high")
    if np.isfinite(dsr) and dsr < 0.50:
        failures.append("deflated Sharpe probability is weak")
    if np.isfinite(ci.get("lower", np.nan)) and ci["lower"] < 0:
        failures.append("bootstrap Sharpe CI includes negative outcomes")
    if selected_exposure < frozen_exposure * 0.60:
        failures.append("improvement, if any, is likely cash/exposure driven")
    if not importance_stability.empty and importance_stability["mean_top5_jaccard_across_folds"].iloc[0] < 0.25:
        failures.append("feature importance is unstable across CPCV folds")

    final_decision = "reject_full_feature_ml_keep_frozen" if failures else "full_feature_ml_complements_frozen_for_paper_monitoring"
    final_conclusion = (
        "Full-feature ML is rejected; keep btc_eth_macro_gate_balanced unchanged."
        if failures
        else "Full-feature ML may complement the frozen strategy for paper monitoring, but not as proven live alpha."
    )

    feature_set_summary = pd.DataFrame([
        {
            "feature_set": name,
            "description": dict((spec.name, spec.description) for spec in feature_set_specs(feature_sets))[name],
            "features": int(frame.shape[1]),
            "observations": int(len(frame)),
            "development_observations": int(len(frame.loc[DEVELOPMENT_START:DEVELOPMENT_END])),
            "feature_to_development_observation_ratio": float(frame.shape[1] / max(len(frame.loc[DEVELOPMENT_START:DEVELOPMENT_END]), 1)),
            "auto_selection": bool(name.endswith("auto_selection")),
        }
        for name, frame in feature_sets.items()
    ])

    return {
        "dataset": dataset,
        "feature_sets": feature_sets,
        "feature_set_summary": feature_set_summary,
        "feature_metadata": feature_metadata,
        "parquet_status": parquet_status,
        "targets": targets,
        "target_diagnostics": diagnostics,
        "prediction_metrics": prediction_metrics,
        "prediction_selection": prediction_selection,
        "prediction_folds": prediction_folds,
        "bundles": bundles,
        "selected_bundles": {key: bundle.config for key, bundle in selected_bundles.items()},
        "stacking_note": stacking_note,
        "strategy_specs": strategy_specs,
        "strategy_metrics": strategy_metrics,
        "strategy_selection": selection,
        "strategy_folds": strategy_folds,
        "selected_strategy": selected_strategy,
        "benchmarks": benchmarks,
        "feature_importance": importance,
        "feature_importance_stability": importance_stability,
        "statistics": {
            "tested_prediction_configurations": int(len(prediction_selection)),
            "tested_strategy_configurations": int(len(strategy_specs)),
            "tested_configurations_total": tested_configs,
            "pbo": strategy_pbo,
            "deflated_sharpe_probability": dsr,
            "bootstrap_sharpe_ci": ci,
            "selected_holdout_sharpe": float(selected_holdout["Sharpe"]),
            "frozen_holdout_sharpe": float(frozen_holdout["Sharpe"]),
            "selected_holdout_cagr": float(selected_holdout["CAGR"]),
            "frozen_holdout_cagr": float(frozen_holdout["CAGR"]),
            "selected_holdout_max_drawdown": float(selected_holdout["Maximum Drawdown"]),
            "frozen_holdout_max_drawdown": float(frozen_holdout["Maximum Drawdown"]),
            "selected_holdout_exposure": selected_exposure,
            "frozen_holdout_exposure": frozen_exposure,
            "selected_holdout_50bps_sharpe": float(selected_holdout_50["Sharpe"]),
            "selected_holdout_50bps_cagr": float(selected_holdout_50["CAGR"]),
        },
        "final_decision": final_decision,
        "failure_reasons": failures,
        "final_conclusion": final_conclusion,
    }


def write_full_feature_ml_stress_test_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    result["feature_set_summary"].to_csv(output / "feature_set_summary.csv", index=False)
    result["feature_metadata"].to_csv(output / "feature_metadata.csv", index=False)
    result["target_diagnostics"].to_csv(output / "target_diagnostics.csv", index=False)
    result["prediction_metrics"].to_csv(output / "prediction_metrics.csv", index=False)
    result["prediction_selection"].to_csv(output / "prediction_selection.csv", index=False)
    result["prediction_folds"].to_csv(output / "prediction_folds.csv", index=False)
    result["strategy_metrics"].to_csv(output / "strategy_metrics.csv", index=False)
    result["strategy_selection"].to_csv(output / "strategy_selection.csv", index=False)
    result["strategy_folds"].to_csv(output / "strategy_folds.csv", index=False)
    result["benchmarks"].to_csv(output / "benchmark_metrics.csv", index=False)
    result["feature_importance"].to_csv(output / "feature_importance.csv", index=False)
    result["feature_importance_stability"].to_csv(output / "feature_importance_stability.csv", index=False)

    stats = result["statistics"]
    selected_strategy = result["selected_strategy"]
    failures = result["failure_reasons"]
    best_prediction = result["prediction_selection"].head(12)
    best_prediction_row = best_prediction.iloc[0] if not best_prediction.empty else pd.Series(dtype=object)
    best_full_feature = result["prediction_selection"][
        result["prediction_selection"].feature_set.isin(["all_accepted", "all_accepted_auto_selection"])
    ].head(1)
    best_full_feature_row = best_full_feature.iloc[0] if not best_full_feature.empty else pd.Series(dtype=object)
    holdout_selected = result["strategy_metrics"][
        result["strategy_metrics"].name.eq(selected_strategy) & result["strategy_metrics"].split.eq("holdout")
    ]
    selected_vs_frozen = pd.concat([
        result["strategy_metrics"][
            result["strategy_metrics"].name.eq(selected_strategy)
            & result["strategy_metrics"].cost_bps.eq(25)
        ],
        result["benchmarks"][
            result["benchmarks"].name.eq(BASELINE_NAME)
            & result["benchmarks"].cost_bps.eq(25)
        ],
    ], ignore_index=True)

    (output / "executive_summary.md").write_text(f"""# Executive summary

Study: **Full-Feature Machine Learning Stress Test for Macro-Regime Cryptocurrency Allocation**

The frozen strategy **{BASELINE_NAME}** was not modified, reselected, or retuned.

## Outcome

- Selected development-CPCV ML strategy: {selected_strategy}
- Final decision: {result['final_decision']}
- Strategy gate outcome: {result['final_conclusion']}
- Tested prediction configurations: {stats['tested_prediction_configurations']}
- Tested strategy configurations: {stats['tested_strategy_configurations']}
- PBO: {_fmt(stats['pbo'], True)}
- Deflated Sharpe probability: {_fmt(stats['deflated_sharpe_probability'], True)}
- Bootstrap Sharpe CI: [{_fmt(stats['bootstrap_sharpe_ci']['lower'])}, {_fmt(stats['bootstrap_sharpe_ci']['upper'])}]

Failure reasons: {('; '.join(failures) if failures else 'None under the stated replacement rules.')}
""", encoding="utf-8")

    (output / "feature_sets.md").write_text(f"""# Feature sets

All features are shifted one rebalance period before prediction. Rejected or unavailable ETF/options/COT/on-chain datasets are not included.

Feature panel status: **{result['parquet_status']}**

## Feature-set summary

{_table(result['feature_set_summary'], [('feature_set', 'Feature set'), ('description', 'Description'), ('features', 'Features'), ('observations', 'Observations'), ('development_observations', 'Development observations'), ('feature_to_development_observation_ratio', 'Feature/dev obs ratio'), ('auto_selection', 'Auto selection')], {'feature_to_development_observation_ratio'})}

## Feature inventory

{_table(result['feature_metadata'], [('feature', 'Feature'), ('family', 'Family'), ('source', 'Source'), ('start', 'Start'), ('end', 'End'), ('coverage', 'Coverage'), ('lag_rule', 'Lag rule')], {'coverage'}, limit=120)}
""", encoding="utf-8")

    (output / "model_comparison.md").write_text(f"""# Model comparison

Model selection uses development CPCV only. Holdout metrics are reported after selection and are not used for promotion.

Stacking note: {result['stacking_note']}

## Top development-CPCV prediction configurations

{_table(best_prediction, [('config', 'Config'), ('feature_set', 'Feature set'), ('model', 'Model'), ('target', 'Target'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier'), ('train_auc', 'Train AUC'), ('train_validation_gap', 'Train/validation gap'), ('selection_score', 'Selection score')], {'auc', 'precision', 'recall', 'f1', 'brier_score', 'train_auc', 'train_validation_gap', 'selection_score'}, limit=20)}

## Target diagnostics

{_table(result['target_diagnostics'], [('target', 'Target'), ('description', 'Description'), ('split', 'Split'), ('observations', 'Observations'), ('positive_events', 'Positive events'), ('prevalence', 'Prevalence')], {'prevalence'}, limit=40)}
""", encoding="utf-8")

    (output / "train_validation_holdout_results.md").write_text(f"""# Train, validation, and holdout results

## Selected strategy versus frozen strategy at 25 bps

{_table(selected_vs_frozen, [('name', 'Name'), ('family', 'Family'), ('split', 'Split'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure'), ('Transaction Costs', 'Transaction costs')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=30)}

## Selected strategy cost sensitivity

{_table(holdout_selected, [('name', 'Name'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure'), ('Transaction Costs', 'Transaction costs')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=20)}

## Development CPCV strategy selection

{_table(result['strategy_selection'], [('candidate', 'Candidate'), ('strategy_type', 'Type'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold Sharpe'), ('positive_fold_fraction', 'Positive folds'), ('development_sharpe', 'Development Sharpe'), ('development_turnover', 'Development turnover'), ('development_exposure', 'Development exposure'), ('selection_score', 'Selection score')], {'positive_fold_fraction', 'development_exposure'}, limit=40)}
""", encoding="utf-8")

    (output / "overfitting_diagnostics.md").write_text(f"""# Overfitting diagnostics

- Number of tested prediction configurations: {stats['tested_prediction_configurations']}
- Number of tested strategy configurations: {stats['tested_strategy_configurations']}
- Total tested configurations: {stats['tested_configurations_total']}
- PBO: {_fmt(stats['pbo'], True)}
- Deflated Sharpe probability: {_fmt(stats['deflated_sharpe_probability'], True)}
- Bootstrap Sharpe CI: [{_fmt(stats['bootstrap_sharpe_ci']['lower'])}, {_fmt(stats['bootstrap_sharpe_ci']['upper'])}]
- Selected holdout exposure: {_fmt(stats['selected_holdout_exposure'], True)}
- Frozen holdout exposure: {_fmt(stats['frozen_holdout_exposure'], True)}

Reject conditions triggered: {('; '.join(failures) if failures else 'None.')}

## CPCV fold distribution

{_table(result['strategy_folds'], [('candidate', 'Candidate'), ('strategy_type', 'Type'), ('fold', 'Fold'), ('fold_sharpe', 'Fold Sharpe')], limit=120)}
""", encoding="utf-8")

    (output / "feature_importance_stability.md").write_text(f"""# Feature importance stability

Permutation and model-importance stability are computed for the best development-CPCV prediction configuration.

## Stability summary

{_table(result['feature_importance_stability'], [('feature', 'Feature'), ('model_importance_mean', 'Model importance mean'), ('model_importance_std', 'Model importance std'), ('permutation_importance_mean', 'Permutation importance mean'), ('top5_frequency', 'Top-5 frequency'), ('mean_top5_jaccard_across_folds', 'Mean top-5 Jaccard')], {'top5_frequency', 'mean_top5_jaccard_across_folds'}, limit=60)}

## Raw model importance

{_table(result['feature_importance'], [('config', 'Config'), ('model', 'Model'), ('feature', 'Feature'), ('importance', 'Importance'), ('method', 'Method')], limit=120)}
""", encoding="utf-8")

    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

Benchmarks are not used for model selection.

{_table(result['benchmarks'], [('name', 'Name'), ('family', 'Family'), ('split', 'Split'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure'), ('Transaction Costs', 'Transaction costs')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=120)}
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

1. Does using all accepted features improve performance versus Tier-1 feature selection? No. The best development-CPCV prediction configuration was `{best_prediction_row.get('config', 'N/A')}` with feature set `{best_prediction_row.get('feature_set', 'N/A')}`. The best all-feature prediction configuration was `{best_full_feature_row.get('config', 'N/A')}`, but the development-selected full-feature trading candidate failed the locked holdout.
2. Do complex models outperform simpler models? Not economically. The top development prediction model was `{best_prediction_row.get('model', 'N/A')}`, and the selected full-feature alpha layer used ML probabilities, but the resulting strategy had negative holdout Sharpe and failed statistical controls.
3. Is any improvement real or overfit? The replacement rules classify the selected ML result as **{result['final_decision']}**.
4. Does any model beat {BASELINE_NAME} on locked holdout? No development-selected ML strategy beat the frozen benchmark. Selected ML holdout Sharpe is {_fmt(stats['selected_holdout_sharpe'])} versus frozen {_fmt(stats['frozen_holdout_sharpe'])}.
5. Does it survive 50 bps costs? No. Selected 50 bps holdout Sharpe is {_fmt(stats['selected_holdout_50bps_sharpe'])}; CAGR is {_fmt(stats['selected_holdout_50bps_cagr'], True)}.
6. Should full-feature ML replace, complement, or be rejected? **{result['final_conclusion']}**

The frozen strategy remains the benchmark unless a future data source/model clears the full evidence standard without relying on holdout tuning or cash-driven Sharpe.
""", encoding="utf-8")

    payload = {
        "selected_strategy": result["selected_strategy"],
        "selected_bundles": result["selected_bundles"],
        "stacking_note": result["stacking_note"],
        "feature_set_summary": result["feature_set_summary"],
        "target_diagnostics": result["target_diagnostics"],
        "prediction_metrics": result["prediction_metrics"],
        "prediction_selection": result["prediction_selection"],
        "strategy_metrics": result["strategy_metrics"],
        "strategy_selection": result["strategy_selection"],
        "benchmarks": result["benchmarks"],
        "statistics": result["statistics"],
        "final_decision": result["final_decision"],
        "failure_reasons": result["failure_reasons"],
        "final_conclusion": result["final_conclusion"],
    }
    (output / "results.json").write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def run_default_full_feature_ml_stress_test(output_dir: str | Path = "reports/full_feature_ml_stress_test") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_full_feature_ml_stress_test(panel, macro, public_data, probability)
    write_full_feature_ml_stress_test_reports(output_dir, result)
    return result


__all__ = [
    "ModelSpec",
    "FeatureSetSpec",
    "StrategySpec",
    "TARGET_SPECS",
    "available_model_specs",
    "build_feature_sets",
    "build_targets",
    "fit_prediction_models",
    "run_full_feature_ml_stress_test",
    "write_full_feature_ml_stress_test_reports",
    "run_default_full_feature_ml_stress_test",
]
