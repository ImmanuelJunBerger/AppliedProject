"""Trend-scanning labels and meta-models for macro-regime crypto allocation.

Standalone methodological study.  The frozen ``btc_eth_macro_gate_balanced``
strategy is used only as an unchanged benchmark/risk layer.  This module tests
whether López de Prado-style trend-scanning labels produce a useful supervised
target for BTC/ETH/cash allocation under development-only CPCV and locked
2025+ holdout evaluation.
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
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import brier_score_loss, confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.neural_network import MLPClassifier
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
    _rebalance_dates,
    _table,
    _threshold_from_dev,
    _weekly_return,
)
from .expansion_tier1_overlay import DEFAULT_TIER1_FEATURES, load_tier1_feature_names
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    CRYPTO_TIER1_FEATURES,
    MACRO_TIER1_FEATURES,
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
)
from .public_crypto_data import PublicDataBundle
from .upside_expansion_models import build_expansion_feature_candidates
from .volatility_breakout import (
    block_bootstrap_sharpe_ci,
    deflated_sharpe_probability,
    probability_backtest_overfitting,
)


BASELINE_NAME = FIXED_SELECTED.name
DEVELOPMENT_START = pd.Timestamp("2019-07-05")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")
LABEL_HORIZONS = (7, 14, 21, 30, 45, 60)
LABEL_TSTAT_THRESHOLDS = (1.0, 1.5, 2.0)
MIN_HOLDOUT_EXPOSURE = 0.15

TARGET_SPECS: tuple[tuple[str, str], ...] = (
    ("btc_upward_trend", "BTC upward trend-scanning label"),
    ("eth_upward_trend", "ETH upward trend-scanning label"),
    ("btc_eth_upward_trend", "BTC/ETH 50-50 upward trend-scanning label"),
    ("eth_vs_btc_relative_trend", "ETH-vs-BTC relative upward trend label"),
    ("top20_upward_trend", "Top-20 basket upward trend label if point-in-time data is available"),
)

STRATEGY_FAMILIES = (
    "pure_trend_scanning",
    "trend_scanning_meta_model",
    "macro_gate_trend_confirmation",
    "trend_first_macro_overlay",
    "relative_btc_eth_trend",
)


@dataclass(frozen=True)
class ModelSpec:
    name: str
    family: str
    factory: Callable[[], Any]
    exploratory: bool = False


@dataclass
class TrendPredictionBundle:
    config_name: str
    target: str
    target_description: str
    model_name: str
    model_family: str
    label_tstat_threshold: float
    probability_threshold: float
    dev_probability: pd.Series
    holdout_probability: pd.Series
    full_probability: pd.Series
    feature_importance: pd.DataFrame


@dataclass
class MetaPredictionBundle:
    config_name: str
    model_name: str
    model_family: str
    probability_threshold: float
    dev_probability: pd.Series
    holdout_probability: pd.Series
    full_probability: pd.Series
    feature_importance: pd.DataFrame
    train_observations: int


@dataclass(frozen=True)
class StrategySpec:
    name: str
    family: str
    rebalance_days: int
    complexity: int
    description: str


def available_model_specs(include_exploratory_mlp: bool = True) -> list[ModelSpec]:
    specs: list[ModelSpec] = [
        ModelSpec(
            "logistic_regression",
            "Logistic regression",
            lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500, class_weight="balanced", random_state=71)),
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
                    random_state=71,
                ),
            ),
        ),
        ModelSpec(
            "random_forest",
            "Random forest",
            lambda: RandomForestClassifier(
                n_estimators=140,
                max_depth=4,
                min_samples_leaf=12,
                class_weight="balanced",
                random_state=71,
                n_jobs=-1,
            ),
        ),
        ModelSpec(
            "gradient_boosting",
            "Gradient boosting",
            lambda: GradientBoostingClassifier(n_estimators=100, max_depth=2, learning_rate=0.04, min_samples_leaf=10, random_state=71),
        ),
        ModelSpec(
            "sgd_classifier",
            "SGD logistic classifier",
            lambda: make_pipeline(
                StandardScaler(),
                SGDClassifier(loss="log_loss", alpha=0.0005, max_iter=2000, class_weight="balanced", random_state=71),
            ),
        ),
    ]
    if importlib.util.find_spec("xgboost") is not None:
        def xgb_factory() -> Any:
            from xgboost import XGBClassifier

            return XGBClassifier(
                n_estimators=100,
                max_depth=2,
                learning_rate=0.04,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric="logloss",
                random_state=71,
            )

        specs.append(ModelSpec("xgboost", "XGBoost", xgb_factory))
    if importlib.util.find_spec("lightgbm") is not None:
        def lgbm_factory() -> Any:
            from lightgbm import LGBMClassifier

            return LGBMClassifier(
                n_estimators=120,
                max_depth=2,
                learning_rate=0.04,
                subsample=0.8,
                colsample_bytree=0.8,
                class_weight="balanced",
                random_state=71,
                verbose=-1,
            )

        specs.append(ModelSpec("lightgbm", "LightGBM", lgbm_factory))
    if include_exploratory_mlp:
        specs.append(
            ModelSpec(
                "shallow_mlp_exploratory",
                "Shallow MLP exploratory",
                lambda: make_pipeline(
                    StandardScaler(),
                    MLPClassifier(hidden_layer_sizes=(12,), alpha=0.01, max_iter=450, early_stopping=True, random_state=71),
                ),
                exploratory=True,
            )
        )
    return specs


def _safe_probability(model: Any, x: pd.DataFrame) -> np.ndarray:
    if len(x) == 0:
        return np.array([])
    if hasattr(model, "predict_proba"):
        return _positive_probability(model, x)
    pred = model.predict(x)
    return np.asarray(pred, dtype=float)


def _ols_slope_tstat(log_path: np.ndarray) -> float:
    values = np.asarray(log_path, dtype=float)
    values = values[np.isfinite(values)]
    n = len(values)
    if n < 4 or np.nanstd(values) == 0:
        return np.nan
    x = np.arange(n, dtype=float)
    x = x - x.mean()
    y = values - values.mean()
    sxx = float(np.dot(x, x))
    if sxx <= 0:
        return np.nan
    slope = float(np.dot(x, y) / sxx)
    resid = y - slope * x
    sigma2 = float(np.dot(resid, resid) / max(n - 2, 1))
    se = math.sqrt(sigma2 / sxx) if sigma2 > 0 else 0.0
    return float(slope / se) if se > 0 else np.nan


def _trend_scan_one_series(price: pd.Series, dates: pd.DatetimeIndex, target: str) -> pd.DataFrame:
    clean = price.replace([np.inf, -np.inf], np.nan).dropna()
    rows: list[dict[str, Any]] = []
    for date in dates:
        date = pd.Timestamp(date)
        if date not in clean.index:
            rows.append({"date": date, "target": target, "selected_horizon": np.nan, "t_stat": np.nan, "trend_strength": np.nan, "forward_realized_return": np.nan})
            continue
        start_pos = clean.index.get_loc(date)
        if isinstance(start_pos, slice) or isinstance(start_pos, np.ndarray):
            rows.append({"date": date, "target": target, "selected_horizon": np.nan, "t_stat": np.nan, "trend_strength": np.nan, "forward_realized_return": np.nan})
            continue
        best_horizon = np.nan
        best_t = np.nan
        best_return = np.nan
        start_price = float(clean.iloc[int(start_pos)])
        for horizon in LABEL_HORIZONS:
            end_date = date + pd.DateOffset(days=int(horizon))
            end_pos = clean.index.searchsorted(end_date)
            if end_pos >= len(clean.index) or end_pos <= int(start_pos) + 2:
                continue
            path = clean.iloc[int(start_pos): end_pos + 1]
            if path.isna().any() or start_price <= 0:
                continue
            t_stat = _ols_slope_tstat(np.log(path.to_numpy(dtype=float)))
            if not np.isfinite(t_stat):
                continue
            if not np.isfinite(best_t) or abs(t_stat) > abs(best_t):
                end_price = float(path.iloc[-1])
                best_t = t_stat
                best_horizon = horizon
                best_return = end_price / start_price - 1.0
        rows.append({
            "date": date,
            "target": target,
            "selected_horizon": best_horizon,
            "t_stat": best_t,
            "trend_strength": abs(best_t) if np.isfinite(best_t) else np.nan,
            "forward_realized_return": best_return,
        })
    return pd.DataFrame(rows).set_index("date")


def _top20_basket_price(dataset: MacroRegimeDataset) -> pd.Series:
    active = dataset.universe_weights.reindex_like(dataset.close).fillna(0.0) > 0
    basket_returns = dataset.returns.where(active).mean(axis=1).fillna(0.0)
    return (1.0 + basket_returns).cumprod()


def _mix_price(dataset: MacroRegimeDataset) -> pd.Series:
    available = [symbol for symbol in ("BTC", "ETH") if symbol in dataset.returns]
    if not available:
        return pd.Series(dtype=float)
    returns = dataset.returns[available].mean(axis=1).fillna(0.0)
    return (1.0 + returns).cumprod()


def build_trend_scan_table(dataset: MacroRegimeDataset, dates: pd.DatetimeIndex) -> pd.DataFrame:
    series_map: dict[str, pd.Series] = {}
    if "BTC" in dataset.close:
        series_map["btc_upward_trend"] = dataset.close["BTC"]
    if "ETH" in dataset.close:
        series_map["eth_upward_trend"] = dataset.close["ETH"]
    mix = _mix_price(dataset)
    if not mix.empty:
        series_map["btc_eth_upward_trend"] = mix
    if {"BTC", "ETH"}.issubset(dataset.close.columns):
        series_map["eth_vs_btc_relative_trend"] = dataset.close["ETH"] / dataset.close["BTC"].replace(0, np.nan)
    top20 = _top20_basket_price(dataset)
    if not top20.empty:
        series_map["top20_upward_trend"] = top20

    frames = [_trend_scan_one_series(series, dates, target) for target, series in series_map.items()]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).reset_index().sort_values(["target", "date"])


def apply_trend_thresholds(scan_table: pd.DataFrame, thresholds: tuple[float, ...] | None = None) -> pd.DataFrame:
    thresholds = thresholds or LABEL_TSTAT_THRESHOLDS
    rows: list[pd.DataFrame] = []
    for threshold in thresholds:
        frame = scan_table.copy()
        frame["label_tstat_threshold"] = threshold
        frame["sign_label"] = np.select(
            [frame.t_stat > threshold, frame.t_stat < -threshold],
            [1, -1],
            default=0,
        )
        frame.loc[frame.t_stat.isna(), "sign_label"] = np.nan
        frame["upward_target"] = (frame["sign_label"] == 1).astype(float)
        frame.loc[frame.sign_label.isna(), "upward_target"] = np.nan
        frame["label_confidence"] = (frame["trend_strength"] / threshold).clip(0.0, 5.0)
        rows.append(frame)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def label_diagnostics(label_table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (target, threshold, split), group in label_table.assign(
        split=lambda x: np.where(pd.to_datetime(x.date) >= HOLDOUT_START, "holdout", "development")
    ).groupby(["target", "label_tstat_threshold", "split"]):
        period = group[pd.to_datetime(group.date).between(DEVELOPMENT_START, DEVELOPMENT_END)] if split == "development" else group[pd.to_datetime(group.date).between(HOLDOUT_START, HOLDOUT_END)]
        valid = period.dropna(subset=["sign_label"])
        rows.append({
            "target": target,
            "label_tstat_threshold": threshold,
            "split": split,
            "observations": int(len(valid)),
            "positive_labels": int((valid.sign_label == 1).sum()),
            "negative_labels": int((valid.sign_label == -1).sum()),
            "neutral_labels": int((valid.sign_label == 0).sum()),
            "positive_rate": float((valid.sign_label == 1).mean()) if len(valid) else np.nan,
            "median_selected_horizon": float(valid.selected_horizon.median()) if len(valid) else np.nan,
            "median_abs_t_stat": float(valid.trend_strength.median()) if len(valid) else np.nan,
            "mean_forward_return": float(valid.forward_realized_return.mean()) if len(valid) else np.nan,
        })
    return pd.DataFrame(rows)


def _crypto_tier1_feature_frame(dataset: MacroRegimeDataset, public_data: PublicDataBundle | None, volatility_probability: pd.Series | None = None) -> pd.DataFrame:
    from .expansion_state_model import _feature_frame

    # _feature_frame already shifts macro/crypto inputs by one day.
    return _feature_frame(dataset, public_data)


def build_trend_feature_frame(
    dataset: MacroRegimeDataset,
    public_data: PublicDataBundle | None,
    dates: pd.DatetimeIndex,
    tier_path: str | Path = "reports/upside_expansion_models/expansion_feature_tiers.csv",
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    base = _crypto_tier1_feature_frame(dataset, public_data)
    expansion, metadata = build_expansion_feature_candidates(dataset, dataset.regime_features, public_data)
    tier1 = load_tier1_feature_names(tier_path)
    if not tier1:
        tier1 = list(DEFAULT_TIER1_FEATURES)
    expansion_available = [feature for feature in tier1 if feature in expansion.columns]
    frame = pd.concat([base, expansion.reindex(columns=expansion_available)], axis=1)
    frame = frame.loc[:, ~frame.columns.duplicated()].replace([np.inf, -np.inf], np.nan)
    development = frame.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    medians = development.median().fillna(0.0)
    frame = frame.ffill().fillna(medians).fillna(0.0)
    aligned = frame.reindex(dates).ffill().fillna(medians).fillna(0.0)
    missing = [feature for feature in tier1 if feature not in expansion_available]
    if not metadata.empty:
        metadata = metadata.copy()
        metadata["used_in_trend_scanning_models"] = metadata.feature.isin(expansion_available)
    return aligned, metadata, missing


def _constant_prob(y: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(float(y.mean()) if len(y) else 0.0, index=index)


def _cpcv_probabilities(x_dev: pd.DataFrame, y_dev: pd.Series, spec: ModelSpec, label_horizon: int = 4) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    probabilities = pd.Series(0.0, index=x_dev.index)
    counts = pd.Series(0.0, index=x_dev.index)
    fold_rows: list[dict[str, Any]] = []
    importance_rows: list[pd.DataFrame] = []
    if len(x_dev) < 36:
        return _constant_prob(y_dev, x_dev.index), pd.DataFrame(), pd.DataFrame()
    splits = combinatorial_purged_splits(len(x_dev), n_groups=6, n_test_groups=2, label_horizon=label_horizon, embargo=1)
    for number, split in enumerate(splits):
        train_index = x_dev.index[list(split.train_indices)]
        test_index = x_dev.index[list(split.test_indices)]
        y_train = y_dev.loc[train_index]
        if y_train.nunique() < 2:
            prob = _constant_prob(y_train, test_index)
            model = None
        else:
            model = spec.factory()
            model.fit(x_dev.loc[train_index], y_train)
            prob = pd.Series(_safe_probability(model, x_dev.loc[test_index]), index=test_index)
        probabilities.loc[test_index] += prob
        counts.loc[test_index] += 1.0
        fold_rows.append({
            "model": spec.name,
            "fold": number,
            "test_groups": ",".join(str(group) for group in split.test_groups),
            "train_samples": int(len(train_index)),
            "test_samples": int(len(test_index)),
        })
        if model is not None:
            fi = _feature_importance(model, spec, list(x_dev.columns), f"{spec.name}_fold_{number}")
            fi["fold"] = number
            importance_rows.append(fi)
    prob = (probabilities / counts.replace(0, np.nan)).fillna(float(y_dev.mean()) if len(y_dev) else 0.0)
    importance = pd.concat(importance_rows, ignore_index=True) if importance_rows else pd.DataFrame()
    return prob, pd.DataFrame(fold_rows), importance


def _train_holdout_probabilities(x_dev: pd.DataFrame, y_dev: pd.Series, x_holdout: pd.DataFrame, spec: ModelSpec) -> tuple[pd.Series, Any | None]:
    if y_dev.nunique() < 2 or len(x_holdout) == 0:
        return _constant_prob(y_dev, x_holdout.index), None
    model = spec.factory()
    model.fit(x_dev, y_dev)
    return pd.Series(_safe_probability(model, x_holdout), index=x_holdout.index), model


def _classification_metrics(y: pd.Series, prob: pd.Series, threshold: float, split: str, config: str, target: str, model: str) -> dict[str, Any]:
    data = pd.concat([y.rename("y"), prob.rename("probability")], axis=1).dropna()
    if data.empty:
        return {"config": config, "target": target, "model": model, "split": split, "threshold": threshold, "observations": 0}
    y_true = data.y.astype(int)
    probabilities = data.probability.clip(0.0, 1.0)
    pred = (probabilities >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, pred, average="binary", zero_division=0)
    matrix = confusion_matrix(y_true, pred, labels=[0, 1])
    auc = roc_auc_score(y_true, probabilities) if y_true.nunique() == 2 else np.nan
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
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "true_negative": int(matrix[0, 0]),
        "false_positive": int(matrix[0, 1]),
        "false_negative": int(matrix[1, 0]),
        "true_positive": int(matrix[1, 1]),
    }


def _targets_from_labels(label_table: pd.DataFrame, target: str, threshold: float, dates: pd.DatetimeIndex) -> pd.Series:
    selected = label_table[(label_table.target == target) & (label_table.label_tstat_threshold == threshold)]
    if selected.empty:
        return pd.Series(np.nan, index=dates)
    return selected.drop_duplicates("date").set_index("date")["upward_target"].reindex(dates)


def fit_trend_prediction_models(
    features: pd.DataFrame,
    label_table: pd.DataFrame,
    specs: list[ModelSpec] | None = None,
    thresholds: tuple[float, ...] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, TrendPredictionBundle]]:
    specs = specs or available_model_specs()
    thresholds = thresholds or LABEL_TSTAT_THRESHOLDS
    metrics: list[dict[str, Any]] = []
    fold_frames: list[pd.DataFrame] = []
    importance_frames: list[pd.DataFrame] = []
    stability_frames: list[pd.DataFrame] = []
    bundles: dict[str, TrendPredictionBundle] = {}
    dates = features.index
    dev_dates = dates[(dates >= DEVELOPMENT_START) & (dates <= DEVELOPMENT_END)]
    holdout_dates = dates[(dates >= HOLDOUT_START) & (dates <= HOLDOUT_END)]
    descriptions = dict(TARGET_SPECS)
    for target, description in TARGET_SPECS:
        for label_threshold in thresholds:
            y = _targets_from_labels(label_table, target, label_threshold, dates)
            valid_dev = y.loc[dev_dates].dropna().index
            valid_holdout = y.loc[holdout_dates].dropna().index
            if len(valid_dev) < 50:
                continue
            x_dev = features.loc[valid_dev]
            y_dev = y.loc[valid_dev].astype(int)
            x_holdout = features.loc[valid_holdout]
            y_holdout = y.loc[valid_holdout].astype(int)
            for spec in specs:
                config = f"{target}__t{str(label_threshold).replace('.', '_')}__{spec.name}"
                dev_prob, folds, fold_importance = _cpcv_probabilities(x_dev, y_dev, spec)
                if not folds.empty:
                    folds["config"] = config
                    folds["target"] = target
                    folds["label_tstat_threshold"] = label_threshold
                    fold_frames.append(folds)
                if not fold_importance.empty:
                    fold_importance["config"] = config
                    fold_importance["target"] = target
                    fold_importance["label_tstat_threshold"] = label_threshold
                    importance_frames.append(fold_importance)
                    ranks = fold_importance.assign(abs_importance=lambda z: z.importance.abs()).groupby(["fold", "feature"])["abs_importance"].sum().groupby(level=0).rank(ascending=False)
                    rank_frame = ranks.rename("rank").reset_index()
                    stability_frames.append(pd.DataFrame({
                        "config": config,
                        "target": target,
                        "rank_correlation_proxy": rank_frame.groupby("feature")["rank"].std().mean(),
                    }, index=[0]))
                probability_threshold = _threshold_from_dev(dev_prob, y_dev)
                holdout_prob, model = _train_holdout_probabilities(x_dev, y_dev, x_holdout, spec)
                full = pd.Series(np.nan, index=features.index)
                full.loc[dev_prob.index] = dev_prob
                full.loc[holdout_prob.index] = holdout_prob
                final_importance = _feature_importance(model, spec, list(features.columns), config)
                final_importance["target"] = target
                final_importance["label_tstat_threshold"] = label_threshold
                final_importance["exploratory_model"] = spec.exploratory
                importance_frames.append(final_importance)
                metrics.append(_classification_metrics(y_dev, dev_prob, probability_threshold, "development_cpcv", config, target, spec.name))
                metrics[-1]["label_tstat_threshold"] = label_threshold
                metrics[-1]["exploratory_model"] = spec.exploratory
                metrics.append(_classification_metrics(y_holdout, holdout_prob, probability_threshold, "holdout", config, target, spec.name))
                metrics[-1]["label_tstat_threshold"] = label_threshold
                metrics[-1]["exploratory_model"] = spec.exploratory
                bundles[config] = TrendPredictionBundle(
                    config_name=config,
                    target=target,
                    target_description=description,
                    model_name=spec.name,
                    model_family=spec.family,
                    label_tstat_threshold=label_threshold,
                    probability_threshold=probability_threshold,
                    dev_probability=dev_prob,
                    holdout_probability=holdout_prob,
                    full_probability=full.ffill().fillna(float(dev_prob.mean()) if len(dev_prob) else 0.0),
                    feature_importance=final_importance,
                )
    metrics_frame = pd.DataFrame(metrics)
    if not metrics_frame.empty:
        dev = metrics_frame[metrics_frame.split == "development_cpcv"].copy()
        dev["prediction_selection_score"] = (
            dev["auc"].fillna(0.5)
            - dev["brier_score"].fillna(1.0)
            + 0.10 * dev["f1"].fillna(0.0)
            - dev["exploratory_model"].astype(float) * 0.02
        )
        metrics_frame = metrics_frame.merge(
            dev[["config", "prediction_selection_score"]],
            on="config",
            how="left",
        )
    return (
        metrics_frame,
        pd.concat(fold_frames, ignore_index=True) if fold_frames else pd.DataFrame(),
        pd.concat(importance_frames, ignore_index=True) if importance_frames else pd.DataFrame(),
        pd.concat(stability_frames, ignore_index=True) if stability_frames else pd.DataFrame(),
        bundles,
    )


def select_best_bundles(prediction_metrics: pd.DataFrame, bundles: dict[str, TrendPredictionBundle]) -> dict[str, TrendPredictionBundle]:
    selected: dict[str, TrendPredictionBundle] = {}
    if prediction_metrics.empty:
        return selected
    dev = prediction_metrics[prediction_metrics.split == "development_cpcv"].copy()
    for target, group in dev.groupby("target"):
        ranked = group.sort_values(["prediction_selection_score", "auc", "brier_score"], ascending=[False, False, True])
        config = str(ranked.iloc[0].config)
        if config in bundles:
            selected[target] = bundles[config]
    return selected


def _scan_for_target(scan_table: pd.DataFrame, target: str, dates: pd.DatetimeIndex) -> pd.DataFrame:
    selected = scan_table[scan_table.target == target].drop_duplicates("date").set_index("date")
    return selected.reindex(dates)


def _meta_feature_frame(
    features: pd.DataFrame,
    scan_table: pd.DataFrame,
    primary: TrendPredictionBundle,
    dataset: MacroRegimeDataset,
) -> pd.DataFrame:
    frame = features.copy()
    raw = _scan_for_target(scan_table, primary.target, features.index)
    frame["primary_trend_probability"] = primary.full_probability.reindex(frame.index).ffill().fillna(0.0)
    frame["past_trend_t_stat"] = raw["t_stat"].shift(1).rolling(8, min_periods=1).mean()
    frame["past_selected_trend_horizon"] = raw["selected_horizon"].shift(1).rolling(8, min_periods=1).mean()
    frame["past_label_confidence"] = raw["trend_strength"].shift(1).rolling(8, min_periods=1).mean()
    available = [symbol for symbol in ("BTC", "ETH") if symbol in dataset.returns]
    if available:
        mix_returns = dataset.returns[available].mean(axis=1).reindex(frame.index).fillna(0.0)
        wealth = (1.0 + mix_returns).cumprod()
        frame["previous_drawdown"] = (wealth / wealth.cummax() - 1.0).shift(1)
        frame["realized_volatility"] = mix_returns.rolling(30).std().shift(1) * np.sqrt(365)
    frame = frame.replace([np.inf, -np.inf], np.nan)
    medians = frame.loc[DEVELOPMENT_START:DEVELOPMENT_END].median().fillna(0.0)
    return frame.ffill().fillna(medians).fillna(0.0)


def fit_meta_models(
    features: pd.DataFrame,
    scan_table: pd.DataFrame,
    primary: TrendPredictionBundle,
    dataset: MacroRegimeDataset,
    specs: list[ModelSpec] | None = None,
    cost_bps: int = 25,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, MetaPredictionBundle]]:
    specs = [spec for spec in (specs or available_model_specs(include_exploratory_mlp=False)) if spec.name != "sgd_classifier" or True]
    meta_features = _meta_feature_frame(features, scan_table, primary, dataset)
    raw = _scan_for_target(scan_table, primary.target, meta_features.index)
    net_return = raw["forward_realized_return"] - (2.0 * cost_bps / 10000.0)
    signal = primary.full_probability.reindex(meta_features.index).ffill().fillna(0.0) >= primary.probability_threshold
    y = (net_return > 0).astype(float)
    y[raw["forward_realized_return"].isna() | ~signal] = np.nan
    dev_dates = meta_features.index[(meta_features.index >= DEVELOPMENT_START) & (meta_features.index <= DEVELOPMENT_END)]
    holdout_dates = meta_features.index[(meta_features.index >= HOLDOUT_START) & (meta_features.index <= HOLDOUT_END)]
    valid_dev = y.loc[dev_dates].dropna().index
    valid_holdout = y.loc[holdout_dates].dropna().index
    rows: list[dict[str, Any]] = []
    folds_all: list[pd.DataFrame] = []
    importance_all: list[pd.DataFrame] = []
    bundles: dict[str, MetaPredictionBundle] = {}
    if len(valid_dev) < 30:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), bundles
    x_dev = meta_features.loc[valid_dev]
    y_dev = y.loc[valid_dev].astype(int)
    x_holdout = meta_features.loc[valid_holdout]
    y_holdout = y.loc[valid_holdout].astype(int)
    for spec in specs:
        config = f"meta_{primary.target}__{spec.name}"
        dev_prob, folds, _ = _cpcv_probabilities(x_dev, y_dev, spec)
        if not folds.empty:
            folds["config"] = config
            folds_all.append(folds)
        threshold = _threshold_from_dev(dev_prob, y_dev)
        holdout_prob, model = _train_holdout_probabilities(x_dev, y_dev, x_holdout, spec)
        full = pd.Series(np.nan, index=meta_features.index)
        full.loc[dev_prob.index] = dev_prob
        full.loc[holdout_prob.index] = holdout_prob
        rows.append(_classification_metrics(y_dev, dev_prob, threshold, "development_cpcv", config, "meta_positive_net_return", spec.name))
        rows.append(_classification_metrics(y_holdout, holdout_prob, threshold, "holdout", config, "meta_positive_net_return", spec.name))
        fi = _feature_importance(model, spec, list(meta_features.columns), config)
        importance_all.append(fi)
        bundles[config] = MetaPredictionBundle(
            config_name=config,
            model_name=spec.name,
            model_family=spec.family,
            probability_threshold=threshold,
            dev_probability=dev_prob,
            holdout_probability=holdout_prob,
            full_probability=full.ffill().fillna(float(dev_prob.mean()) if len(dev_prob) else 0.0),
            feature_importance=fi,
            train_observations=int(len(valid_dev)),
        )
    metrics = pd.DataFrame(rows)
    if not metrics.empty:
        dev = metrics[metrics.split == "development_cpcv"].copy()
        dev["selection_score"] = dev["auc"].fillna(0.5) - dev["brier_score"].fillna(1.0) + 0.10 * dev["f1"].fillna(0.0)
        metrics = metrics.merge(dev[["config", "selection_score"]], on="config", how="left")
    return (
        metrics,
        pd.concat(folds_all, ignore_index=True) if folds_all else pd.DataFrame(),
        pd.concat(importance_all, ignore_index=True) if importance_all else pd.DataFrame(),
        bundles,
    )


def select_meta_bundle(meta_metrics: pd.DataFrame, bundles: dict[str, MetaPredictionBundle]) -> MetaPredictionBundle | None:
    if meta_metrics.empty or not bundles:
        return None
    dev = meta_metrics[meta_metrics.split == "development_cpcv"].sort_values(["selection_score", "auc", "brier_score"], ascending=[False, False, True])
    if dev.empty:
        return None
    return bundles.get(str(dev.iloc[0].config))


def predeclared_strategy_specs() -> list[StrategySpec]:
    specs: list[StrategySpec] = []
    complexity = {
        "pure_trend_scanning": 1,
        "trend_scanning_meta_model": 3,
        "macro_gate_trend_confirmation": 2,
        "trend_first_macro_overlay": 2,
        "relative_btc_eth_trend": 2,
    }
    descriptions = {
        "pure_trend_scanning": "Long BTC/ETH when the trend-scanning model predicts an upward BTC/ETH trend; cash otherwise.",
        "trend_scanning_meta_model": "Primary trend model proposes trades; meta-model decides take, reduce, or skip.",
        "macro_gate_trend_confirmation": "Frozen macro gate must permit exposure and trend model confirms BTC/ETH exposure.",
        "trend_first_macro_overlay": "Trend model is the alpha engine; frozen macro gate acts as risk overlay.",
        "relative_btc_eth_trend": "Use BTC/ETH trend probability for exposure and relative trend probability for BTC-vs-ETH tilt.",
    }
    for family in STRATEGY_FAMILIES:
        for rebalance in (7, 14):
            specs.append(StrategySpec(
                name=f"{family}_{'weekly' if rebalance == 7 else 'biweekly'}",
                family=family,
                rebalance_days=rebalance,
                complexity=complexity[family],
                description=descriptions[family],
            ))
    return specs


def _balanced_btc_eth_row(columns: pd.Index, exposure: float = 1.0, btc_weight: float = 0.50) -> pd.Series:
    row = pd.Series(0.0, index=columns)
    if "BTC" in row and "ETH" in row:
        row["BTC"] = exposure * btc_weight
        row["ETH"] = exposure * (1.0 - btc_weight)
    elif "BTC" in row:
        row["BTC"] = exposure
    elif "ETH" in row:
        row["ETH"] = exposure
    return row.clip(lower=0.0, upper=1.0)


def build_strategy_weights(
    dataset: MacroRegimeDataset,
    spec: StrategySpec,
    base_weights: pd.DataFrame,
    combined_regime: pd.Series,
    selected_bundles: dict[str, TrendPredictionBundle],
    meta_bundle: MetaPredictionBundle | None,
) -> tuple[pd.DataFrame, pd.Series]:
    dates = _rebalance_dates(dataset.close.index, spec.rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    decisions = pd.Series("cash", index=dates, dtype=object)
    mix = selected_bundles.get("btc_eth_upward_trend")
    btc = selected_bundles.get("btc_upward_trend")
    eth = selected_bundles.get("eth_upward_trend")
    relative = selected_bundles.get("eth_vs_btc_relative_trend")
    if mix is None:
        return weights, decisions
    mix_prob = mix.full_probability.reindex(dates).ffill().fillna(0.0)
    mix_signal = mix_prob >= mix.probability_threshold
    rel_prob = relative.full_probability.reindex(dates).ffill().fillna(0.5) if relative else pd.Series(0.5, index=dates)
    regimes = combined_regime.reindex(dates).ffill().fillna("risk_off")
    base = base_weights.reindex(dates).fillna(0.0)
    meta_prob = meta_bundle.full_probability.reindex(dates).ffill().fillna(0.0) if meta_bundle else pd.Series(0.0, index=dates)
    for date in dates:
        signal = bool(mix_signal.loc[date])
        regime = str(regimes.loc[date])
        if spec.family == "pure_trend_scanning":
            if signal:
                weights.loc[date] = _balanced_btc_eth_row(weights.columns, 1.0)
                decisions.loc[date] = "trend_take"
        elif spec.family == "trend_scanning_meta_model":
            if signal and meta_bundle is not None:
                threshold = meta_bundle.probability_threshold
                probability = float(meta_prob.loc[date])
                if probability >= threshold:
                    exposure = 1.0
                    action = "meta_take"
                elif probability >= max(0.0, threshold - 0.15):
                    exposure = 0.50
                    action = "meta_reduce"
                else:
                    exposure = 0.0
                    action = "meta_skip"
                weights.loc[date] = _balanced_btc_eth_row(weights.columns, exposure)
                decisions.loc[date] = action
        elif spec.family == "macro_gate_trend_confirmation":
            if signal and regime != "risk_off":
                row = base.loc[date].copy()
                if row.sum() <= 0:
                    row = _balanced_btc_eth_row(weights.columns, 0.50 if regime == "neutral" else 1.0)
                weights.loc[date] = row
                decisions.loc[date] = f"macro_{regime}_trend_confirmed"
        elif spec.family == "trend_first_macro_overlay":
            if signal:
                exposure = 1.0 if regime == "risk_on" else 0.50 if regime == "neutral" else 0.0
                weights.loc[date] = _balanced_btc_eth_row(weights.columns, exposure)
                decisions.loc[date] = f"trend_first_macro_{regime}"
        elif spec.family == "relative_btc_eth_trend":
            btc_signal = bool(btc.full_probability.reindex(dates).ffill().fillna(0.0).loc[date] >= btc.probability_threshold) if btc else signal
            eth_signal = bool(eth.full_probability.reindex(dates).ffill().fillna(0.0).loc[date] >= eth.probability_threshold) if eth else signal
            if signal or btc_signal or eth_signal:
                p = float(rel_prob.loc[date])
                rel_threshold = relative.probability_threshold if relative else 0.55
                if p >= rel_threshold:
                    btc_weight, action = 0.30, "relative_eth_tilt"
                elif p <= 1.0 - rel_threshold:
                    btc_weight, action = 0.70, "relative_btc_tilt"
                else:
                    btc_weight, action = 0.50, "relative_balanced"
                weights.loc[date] = _balanced_btc_eth_row(weights.columns, 1.0, btc_weight)
                decisions.loc[date] = action
    return weights.clip(lower=0.0, upper=1.0), decisions


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


def _pure_momentum_weights(dataset: MacroRegimeDataset) -> pd.DataFrame:
    from .macro_regime_strategy import MacroRegimeCandidate

    candidate = MacroRegimeCandidate(
        name="pure_top10_momentum",
        family="Pure top-10 momentum benchmark",
        gate_profile="balanced",
        use_crypto_gate=False,
        allocation="top10_momentum",
        rebalance_days=7,
        top_k=5,
        universe_size=10,
        max_asset_weight=0.20,
        turnover_cap=0.75,
    )
    weights, _, _, _ = build_candidate_weights(dataset, candidate, combined_override="always_on")
    return weights


def _prior_strategy_rows() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    meta_path = Path("reports/strategy_enhancement_research/development_holdout_retention.csv")
    if meta_path.exists():
        frame = pd.read_csv(meta_path)
        selected = frame[frame.candidate.astype(str).eq("meta_gradient_boosting_60")].copy() if "candidate" in frame else pd.DataFrame()
        for _, row in selected.iterrows():
            rows.extend([
                {
                    "name": "meta_gradient_boosting_60",
                    "family": "Prior conservative ML meta-label overlay",
                    "benchmark_group": "prior_meta_overlay",
                    "split": "development",
                    "cost_bps": 25,
                    "CAGR": row.get("development_cagr"),
                    "Sharpe": row.get("development_sharpe"),
                    "Maximum Drawdown": row.get("development_max_drawdown"),
                    "Annual Turnover": row.get("development_turnover"),
                    "Exposure": row.get("development_exposure"),
                },
                {
                    "name": "meta_gradient_boosting_60",
                    "family": "Prior conservative ML meta-label overlay",
                    "benchmark_group": "prior_meta_overlay",
                    "split": "holdout",
                    "cost_bps": 25,
                    "CAGR": row.get("holdout_cagr"),
                    "Sharpe": row.get("holdout_sharpe"),
                    "Maximum Drawdown": row.get("holdout_max_drawdown"),
                    "Annual Turnover": row.get("holdout_turnover"),
                    "Exposure": row.get("holdout_exposure"),
                },
            ])
    selected_path = Path("reports/expansion_first_research/selected_holdouts.csv")
    if selected_path.exists():
        frame = pd.read_csv(selected_path)
        for label in ("expansion_first", "hybrid"):
            chosen = frame[frame.selection.astype(str).eq(label)].copy() if "selection" in frame else pd.DataFrame()
            if chosen.empty:
                continue
            row = chosen.iloc[0]
            rows.append({
                "name": row.get("candidate", label),
                "family": f"Prior {label.replace('_', '-')} strategy",
                "benchmark_group": f"prior_{label}",
                "split": "holdout",
                "cost_bps": 25,
                "CAGR": row.get("CAGR"),
                "Sharpe": row.get("Sharpe"),
                "Sortino": row.get("Sortino"),
                "Calmar": row.get("Calmar"),
                "Maximum Drawdown": row.get("Maximum Drawdown"),
                "Annual Turnover": row.get("Annual Turnover"),
                "Exposure": row.get("Exposure"),
            })
    return pd.DataFrame(rows)


def benchmark_rows(dataset: MacroRegimeDataset, base_weights: pd.DataFrame, regimes: tuple[pd.Series, pd.Series, pd.Series]) -> tuple[pd.DataFrame, dict[str, PortfolioResult]]:
    rows: list[dict[str, Any]] = []
    results: dict[str, PortfolioResult] = {}
    macro, crypto, combined = regimes
    for cost in COST_LEVELS:
        frozen = backtest_weights(dataset, base_weights, macro, crypto, combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
        rows.extend(_rows_for_result(BASELINE_NAME, "Frozen macro gate", "frozen_strategy", cost, frozen))
        results[f"{BASELINE_NAME}_{cost}"] = frozen
        risk_on = _all_risk_on(dataset.close.index)
        for name, family in (
            ("btc_buy_hold", "BTC buy-and-hold"),
            ("eth_buy_hold", "ETH buy-and-hold"),
            ("btc_eth_50_50", "50/50 BTC/ETH"),
            ("equal_weight_top10", "Equal-weight top 10"),
        ):
            result = backtest_weights(dataset, _buy_hold_weights(dataset, name), *risk_on, cost_bps=cost, turnover_cap=10.0)
            rows.extend(_rows_for_result(name, family, "benchmark", cost, result))
            results[f"{name}_{cost}"] = result
        momentum = backtest_weights(dataset, _pure_momentum_weights(dataset), *risk_on, cost_bps=cost, turnover_cap=0.75)
        rows.extend(_rows_for_result("pure_top10_momentum", "Pure top-10 momentum", "benchmark", cost, momentum))
        results[f"pure_top10_momentum_{cost}"] = momentum
    prior = _prior_strategy_rows()
    if not prior.empty:
        rows.extend(prior.to_dict("records"))
    return pd.DataFrame(rows), results


def select_strategy_cpcv(results_25bps: dict[str, PortfolioResult], specs: list[StrategySpec]) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    weekly_returns: dict[str, pd.Series] = {}
    for spec in specs:
        result = results_25bps[spec.name]
        weekly = _weekly_return(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        weekly_returns[spec.name] = weekly
        if len(weekly) < 30:
            continue
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_sharpes = []
        for number, split in enumerate(splits):
            subset = weekly.iloc[list(split.test_indices)]
            std = subset.std()
            sharpe = float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan
            fold_sharpes.append(sharpe)
            fold_rows.append({
                "candidate": spec.name,
                "family": spec.family,
                "fold": number,
                "test_groups": ",".join(str(group) for group in split.test_groups),
                "fold_sharpe": sharpe,
            })
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        turnover_penalty = max(0.0, dev["Annual Turnover"] - 12.0) * 0.05
        complexity_penalty = spec.complexity * 0.03
        rows.append({
            "candidate": spec.name,
            "family": spec.family,
            "description": spec.description,
            "rebalance_days": spec.rebalance_days,
            "complexity": spec.complexity,
            "median_fold_sharpe": float(np.nanmedian(fold_sharpes)),
            "worst_fold_sharpe": float(np.nanmin(fold_sharpes)),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_sharpes) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
            "turnover_penalty": turnover_penalty,
            "complexity_penalty": complexity_penalty,
        })
    selection = pd.DataFrame(rows)
    if selection.empty:
        raise ValueError("No valid trend-scanning strategy candidates were available for CPCV selection.")
    selection["selection_score"] = (
        selection["median_fold_sharpe"]
        + 0.25 * selection["worst_fold_sharpe"]
        + 0.35 * selection["positive_fold_fraction"]
        - selection["turnover_penalty"]
        - selection["complexity_penalty"]
    )
    selection = selection.sort_values(["selection_score", "median_fold_sharpe", "worst_fold_sharpe", "development_turnover"], ascending=[False, False, False, True])
    pbo = probability_backtest_overfitting(pd.concat(weekly_returns, axis=1).sort_index(), blocks=8) if len(weekly_returns) > 1 else np.nan
    return selection, pd.DataFrame(fold_rows), str(selection.iloc[0].candidate), pbo


def _calibration_table(label_table: pd.DataFrame, bundles: dict[str, TrendPredictionBundle]) -> pd.DataFrame:
    rows = []
    for bundle in bundles.values():
        y = _targets_from_labels(label_table, bundle.target, bundle.label_tstat_threshold, bundle.full_probability.index)
        for split, probability in (("development_cpcv", bundle.dev_probability), ("holdout", bundle.holdout_probability)):
            data = pd.concat([y.reindex(probability.index).rename("y"), probability.rename("p")], axis=1).dropna()
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


def _paired_sharpe_test(candidate: pd.Series, frozen: pd.Series) -> dict[str, float]:
    aligned = pd.concat([candidate.rename("candidate"), frozen.rename("frozen")], axis=1).dropna()
    if len(aligned) < 20:
        return {"sharpe_delta": np.nan, "jobson_korkie_z_approx": np.nan, "jobson_korkie_p_approx": np.nan}
    cand = aligned.candidate
    base = aligned.frozen
    def sharpe(x: pd.Series) -> float:
        std = x.std()
        return float(x.mean() / std * np.sqrt(365)) if std and np.isfinite(std) else np.nan
    delta = sharpe(cand) - sharpe(base)
    diff = cand - base
    se = diff.std() / math.sqrt(len(diff)) if diff.std() and np.isfinite(diff.std()) else np.nan
    z = float(diff.mean() / se) if se and np.isfinite(se) else np.nan
    try:
        from scipy.stats import norm

        p = float(2.0 * (1.0 - norm.cdf(abs(z)))) if np.isfinite(z) else np.nan
    except Exception:
        p = np.nan
    return {"sharpe_delta": float(delta), "jobson_korkie_z_approx": z, "jobson_korkie_p_approx": p}


def run_trend_scanning_ml(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
    model_specs: list[ModelSpec] | None = None,
    tier_path: str | Path = "reports/upside_expansion_models/expansion_feature_tiers.csv",
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=20)
    dates = _rebalance_dates(dataset.close.index, 7)
    features, feature_metadata, missing_tier1 = build_trend_feature_frame(dataset, public_data, dates, tier_path)
    scan_table = build_trend_scan_table(dataset, dates)
    label_table = apply_trend_thresholds(scan_table)
    diagnostics = label_diagnostics(label_table)
    prediction_metrics, prediction_folds, feature_importance, importance_stability, bundles = fit_trend_prediction_models(
        features,
        label_table,
        specs=model_specs,
    )
    selected_bundles = select_best_bundles(prediction_metrics, bundles)
    primary = selected_bundles.get("btc_eth_upward_trend")
    meta_metrics = pd.DataFrame()
    meta_folds = pd.DataFrame()
    meta_importance = pd.DataFrame()
    meta_bundles: dict[str, MetaPredictionBundle] = {}
    selected_meta = None
    if primary is not None:
        meta_metrics, meta_folds, meta_importance, meta_bundles = fit_meta_models(
            features,
            scan_table,
            primary,
            dataset,
            specs=[spec for spec in (model_specs or available_model_specs(include_exploratory_mlp=False)) if not spec.exploratory],
        )
        selected_meta = select_meta_bundle(meta_metrics, meta_bundles)

    base_weights, macro_regime, crypto_regime, combined_regime = build_candidate_weights(dataset, FIXED_SELECTED)
    strategy_specs = predeclared_strategy_specs()
    strategy_results: dict[str, dict[int, PortfolioResult]] = {}
    strategy_decisions: dict[str, pd.Series] = {}
    for spec in strategy_specs:
        weights, decisions = build_strategy_weights(dataset, spec, base_weights, combined_regime, selected_bundles, selected_meta)
        strategy_decisions[spec.name] = decisions
        strategy_results[spec.name] = {
            cost: backtest_weights(dataset, weights, macro_regime, crypto_regime, combined_regime, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
            for cost in COST_LEVELS
        }
    results_25 = {name: by_cost[25] for name, by_cost in strategy_results.items()}
    selection, cpcv_folds, winner, pbo = select_strategy_cpcv(results_25, strategy_specs)
    strategy_metric_rows = []
    spec_by_name = {spec.name: spec for spec in strategy_specs}
    for name, by_cost in strategy_results.items():
        spec = spec_by_name[name]
        for cost, result in by_cost.items():
            strategy_metric_rows.extend(_rows_for_result(name, spec.description, spec.family, cost, result, selected=name == winner))
    strategy_metrics = pd.DataFrame(strategy_metric_rows)
    benchmarks, benchmark_results = benchmark_rows(dataset, base_weights, (macro_regime, crypto_regime, combined_regime))
    frozen_25 = benchmark_results[f"{BASELINE_NAME}_25"]
    winner_25 = strategy_results[winner][25]
    frozen_dev = period_metrics(frozen_25, DEVELOPMENT_START, DEVELOPMENT_END)
    frozen_holdout = period_metrics(frozen_25, HOLDOUT_START, HOLDOUT_END)
    winner_dev = period_metrics(winner_25, DEVELOPMENT_START, DEVELOPMENT_END)
    winner_holdout = period_metrics(winner_25, HOLDOUT_START, HOLDOUT_END)
    winner_50 = period_metrics(strategy_results[winner][50], HOLDOUT_START, HOLDOUT_END)
    selected_returns = winner_25.returns.loc[HOLDOUT_START:HOLDOUT_END]
    frozen_returns = frozen_25.returns.loc[HOLDOUT_START:HOLDOUT_END]
    tested_configurations = int(
        len(prediction_metrics[prediction_metrics.split == "development_cpcv"])
        + len(meta_metrics[meta_metrics.split == "development_cpcv"]) if not meta_metrics.empty else len(prediction_metrics[prediction_metrics.split == "development_cpcv"])
    ) + len(strategy_specs)
    dsr = deflated_sharpe_probability(selected_returns, tested_configurations=tested_configurations)
    bootstrap = block_bootstrap_sharpe_ci(selected_returns, samples=500, block_length=14)
    paired = _paired_sharpe_test(selected_returns, frozen_returns)
    calibration = _calibration_table(label_table, {k: selected_bundles[k] for k in selected_bundles if k in selected_bundles})
    selected_decisions = strategy_decisions[winner].loc[HOLDOUT_START:HOLDOUT_END].value_counts(normalize=True).rename_axis("decision").reset_index(name="frequency")
    contribution = pd.DataFrame({"frozen": frozen_25.returns, "selected": winner_25.returns}).loc[DEVELOPMENT_START:HOLDOUT_END]
    contribution["incremental"] = contribution.selected - contribution.frozen
    contribution["split"] = np.where(contribution.index >= HOLDOUT_START, "holdout", "development")
    contribution_summary = contribution.groupby("split").apply(
        lambda group: pd.Series({
            "frozen_total_return": float((1 + group.frozen).prod() - 1),
            "selected_total_return": float((1 + group.selected).prod() - 1),
            "incremental_total_return": float((1 + group.selected).prod() - (1 + group.frozen).prod()),
        }),
        include_groups=False,
    ).reset_index()
    passes = bool(
        winner_holdout["Sharpe"] > frozen_holdout["Sharpe"] + 0.10
        and winner_holdout["CAGR"] >= frozen_holdout["CAGR"] * 0.90
        and winner_holdout["Maximum Drawdown"] >= frozen_holdout["Maximum Drawdown"] - 0.05
        and winner_50["CAGR"] > 0
        and winner_holdout["Annual Turnover"] <= 12
        and winner_holdout["Exposure"] >= MIN_HOLDOUT_EXPOSURE
        and (not np.isfinite(pbo) or pbo <= 0.65)
        and (not np.isfinite(dsr) or dsr >= 0.50)
        and paired["sharpe_delta"] > 0
    )
    if passes:
        conclusion = "Trend-scanning provides paper-monitoring evidence as a complementary overlay, but the frozen strategy remains the benchmark until prospective validation."
    elif winner_holdout["Exposure"] < MIN_HOLDOUT_EXPOSURE:
        conclusion = "Trend-scanning improvement, if any, is mostly a low-exposure/cash effect; reject as a replacement."
    elif winner_holdout["Sharpe"] <= frozen_holdout["Sharpe"] or paired["sharpe_delta"] <= 0:
        conclusion = "Trend-scanning does not beat the frozen macro strategy after locked-holdout evaluation."
    else:
        conclusion = "Trend-scanning shows partial economic evidence but fails statistical or implementation guardrails; keep the frozen macro strategy."
    return {
        "protocol": {
            "title": "Trend-Scanning Labels and Meta-Models for Macro-Regime Cryptocurrency Allocation",
            "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} onward",
            "baseline": BASELINE_NAME,
            "selection_rule": "Trend-label thresholds, models, meta-models, and strategy candidates are selected by development-only CPCV. Holdout is reported only after selection.",
        },
        "dataset": dataset,
        "features": features,
        "feature_metadata": feature_metadata,
        "missing_tier1_features": missing_tier1,
        "scan_table": scan_table,
        "label_table": label_table,
        "label_diagnostics": diagnostics,
        "prediction_metrics": prediction_metrics,
        "prediction_folds": prediction_folds,
        "feature_importance": feature_importance,
        "importance_stability": importance_stability,
        "prediction_bundles": bundles,
        "selected_bundles": selected_bundles,
        "meta_metrics": meta_metrics,
        "meta_folds": meta_folds,
        "meta_importance": meta_importance,
        "meta_bundles": meta_bundles,
        "selected_meta": selected_meta,
        "strategy_specs": strategy_specs,
        "strategy_results": strategy_results,
        "strategy_metrics": strategy_metrics,
        "strategy_selection": selection,
        "strategy_cpcv_folds": cpcv_folds,
        "strategy_decisions": strategy_decisions,
        "winner": winner,
        "benchmarks": benchmarks,
        "frozen_development": frozen_dev,
        "frozen_holdout": frozen_holdout,
        "winner_development": winner_dev,
        "winner_holdout": winner_holdout,
        "winner_holdout_50bps": winner_50,
        "pbo": pbo,
        "deflated_sharpe_probability": dsr,
        "bootstrap_sharpe_ci": bootstrap,
        "paired_sharpe_test": paired,
        "calibration": calibration,
        "selected_decision_counts": selected_decisions,
        "contribution_summary": contribution_summary,
        "passes_guardrails": passes,
        "final_conclusion": conclusion,
        "tested_configurations": {
            "label_thresholds": len(LABEL_TSTAT_THRESHOLDS),
            "prediction_configs": int(len(prediction_metrics[prediction_metrics.split == "development_cpcv"])),
            "meta_configs": int(len(meta_metrics[meta_metrics.split == "development_cpcv"])) if not meta_metrics.empty else 0,
            "strategy_configs": len(strategy_specs),
            "total": tested_configurations,
        },
    }


def _write_csvs(output: Path, result: dict[str, Any]) -> None:
    for key, filename in (
        ("feature_metadata", "feature_metadata.csv"),
        ("scan_table", "trend_scan_raw.csv"),
        ("label_table", "trend_labels.csv"),
        ("label_diagnostics", "label_diagnostics.csv"),
        ("prediction_metrics", "prediction_metrics.csv"),
        ("prediction_folds", "prediction_folds.csv"),
        ("feature_importance", "feature_importance.csv"),
        ("importance_stability", "feature_importance_stability.csv"),
        ("meta_metrics", "meta_metrics.csv"),
        ("meta_folds", "meta_folds.csv"),
        ("meta_importance", "meta_feature_importance.csv"),
        ("strategy_selection", "strategy_selection.csv"),
        ("strategy_cpcv_folds", "strategy_cpcv_folds.csv"),
        ("strategy_metrics", "strategy_metrics.csv"),
        ("benchmarks", "benchmark_metrics.csv"),
        ("calibration", "calibration.csv"),
        ("selected_decision_counts", "selected_decision_counts.csv"),
        ("contribution_summary", "contribution_summary.csv"),
    ):
        frame = result.get(key)
        if isinstance(frame, pd.DataFrame):
            frame.to_csv(output / filename, index=True if key in {"scan_table"} else False)


def _selected_prediction_table(result: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for target, bundle in result["selected_bundles"].items():
        rows.append({
            "target": target,
            "config": bundle.config_name,
            "model": bundle.model_name,
            "label_tstat_threshold": bundle.label_tstat_threshold,
            "probability_threshold": bundle.probability_threshold,
        })
    return pd.DataFrame(rows)


def _holdout_strategy_table(result: dict[str, Any]) -> pd.DataFrame:
    metrics = result["strategy_metrics"]
    selected = result["winner"]
    return metrics[(metrics.name == selected) & (metrics.split == "holdout")].copy()


def _final_questions(result: dict[str, Any]) -> str:
    prediction = result["prediction_metrics"]
    fixed_comparison_note = "Fixed forward-return targets from earlier modules were not re-optimized in this module; comparison is methodological and based on prior report outcomes plus trend-label diagnostics."
    dev_best = prediction[prediction.split == "development_cpcv"].sort_values("prediction_selection_score", ascending=False).head(1)
    hold_best = prediction[prediction.split == "holdout"].merge(dev_best[["config"]], on="config", how="inner") if not dev_best.empty else pd.DataFrame()
    selected_meta = result.get("selected_meta")
    meta_text = "No usable meta-model was trained." if selected_meta is None else f"Selected meta-model: {selected_meta.config_name}."
    winner_hold = result["winner_holdout"]
    frozen_hold = result["frozen_holdout"]
    beats = winner_hold["Sharpe"] > frozen_hold["Sharpe"] and winner_hold["CAGR"] >= frozen_hold["CAGR"]
    survives_50 = result["winner_holdout_50bps"]["CAGR"] > 0 and result["winner_holdout_50bps"]["Sharpe"] > 0
    statistical = result["passes_guardrails"]
    lines = [
        f"1. Do trend-scanning labels produce better ML targets than fixed forward-return targets? {fixed_comparison_note} Best development trend-label model AUC was {_fmt(dev_best.iloc[0].auc) if not dev_best.empty else 'N/A'}; selected-config holdout AUC was {_fmt(hold_best.iloc[0].auc) if not hold_best.empty else 'N/A'}.",
        f"2. Does the meta-model improve the primary trend-scanning signal? {meta_text} The selected strategy result below determines economic usefulness; meta-model inclusion is not promoted unless it survives CPCV and holdout.",
        f"3. Does trend-scanning improve upside capture? Incremental holdout total return vs frozen was {_fmt(result['contribution_summary'].set_index('split').loc['holdout', 'incremental_total_return'], True) if 'holdout' in set(result['contribution_summary'].split) else 'N/A'}.",
        f"4. Does any trend-scanning strategy beat {BASELINE_NAME}? {'Yes' if beats else 'No'} on the predeclared Sharpe/CAGR comparison for the development-selected candidate.",
        f"5. Does any improvement survive 50 bps costs? {'Yes' if survives_50 else 'No'} for the development-selected candidate.",
        f"6. Is the improvement statistically convincing or likely overfit? {'Statistically convincing under the guardrails' if statistical else 'Not statistically convincing; overfitting risk remains material'}.",
        f"7. Should trend-scanning replace, complement, or be rejected relative to the frozen macro strategy? {result['final_conclusion']}",
    ]
    return "\n".join(f"- {line}" for line in lines)


def write_trend_scanning_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_csvs(output, result)
    selected = result["winner"]
    selected_costs = _holdout_strategy_table(result)
    selected_predictions = _selected_prediction_table(result)
    benchmark_holdout = result["benchmarks"][(result["benchmarks"].split == "holdout") & (result["benchmarks"].cost_bps.isin([25, 50]))].copy()
    selected_holdout = result["strategy_metrics"][(result["strategy_metrics"].name == selected) & (result["strategy_metrics"].split == "holdout")]
    comparison = pd.concat([benchmark_holdout, selected_holdout], ignore_index=True, sort=False)
    top_importance = result["feature_importance"][result["feature_importance"].config.isin(selected_predictions.config.tolist())].copy()
    if top_importance.empty:
        top_importance = result["feature_importance"].copy()

    (output / "executive_summary.md").write_text(f"""# Executive summary

Study: **{result['protocol']['title']}**

The frozen strategy **{BASELINE_NAME}** was not modified, reselected, or retuned.

## Protocol

- Development period: {result['protocol']['development_period']}
- Locked holdout: {result['protocol']['locked_holdout']}
- Label horizons: {', '.join(str(h) for h in LABEL_HORIZONS)} days
- Trend-label t-stat thresholds tested inside development CPCV: {', '.join(str(x) for x in LABEL_TSTAT_THRESHOLDS)}
- Total tested configurations: {result['tested_configurations']['total']}

## Development-selected strategy

Selected by development-only CPCV: **{selected}**

| Metric | Frozen macro strategy | Trend-scanning selected |
|---|---:|---:|
| Development Sharpe | {_fmt(result['frozen_development']['Sharpe'])} | {_fmt(result['winner_development']['Sharpe'])} |
| Holdout Sharpe | {_fmt(result['frozen_holdout']['Sharpe'])} | {_fmt(result['winner_holdout']['Sharpe'])} |
| Holdout CAGR | {_fmt(result['frozen_holdout']['CAGR'], True)} | {_fmt(result['winner_holdout']['CAGR'], True)} |
| Holdout max DD | {_fmt(result['frozen_holdout']['Maximum Drawdown'], True)} | {_fmt(result['winner_holdout']['Maximum Drawdown'], True)} |
| Holdout turnover | {_fmt(result['frozen_holdout']['Annual Turnover'])} | {_fmt(result['winner_holdout']['Annual Turnover'])} |
| Holdout exposure | {_fmt(result['frozen_holdout']['Exposure'], True)} | {_fmt(result['winner_holdout']['Exposure'], True)} |

Final conclusion: **{result['final_conclusion']}**
""", encoding="utf-8")

    (output / "trend_label_construction.md").write_text(f"""# Trend label construction

For each rebalance date and target asset/basket, the module scans forward horizons of {', '.join(str(h) for h in LABEL_HORIZONS)} calendar days.

For each horizon it regresses the forward log price path on time and computes the slope t-statistic.  The selected horizon is the horizon with the largest absolute t-statistic.  The sign label is:

- `+1` when selected t-stat is above the positive threshold.
- `-1` when selected t-stat is below the negative threshold.
- `0` otherwise.

Thresholds were not selected on holdout.  Threshold candidates were embedded into model configurations and selected only through development-period CPCV.

## Stored label fields

- selected horizon
- t-stat
- sign label
- trend strength
- forward realized return
- label confidence

Raw tables:

- `trend_scan_raw.csv`
- `trend_labels.csv`
""", encoding="utf-8")

    (output / "label_diagnostics.md").write_text(f"""# Label diagnostics

{_table(result['label_diagnostics'], [('target', 'Target'), ('label_tstat_threshold', 'Threshold'), ('split', 'Split'), ('observations', 'Obs'), ('positive_rate', 'Positive rate'), ('median_selected_horizon', 'Median horizon'), ('median_abs_t_stat', 'Median |t|'), ('mean_forward_return', 'Mean fwd return')], {'positive_rate', 'mean_forward_return'}, limit=120)}
""", encoding="utf-8")

    (output / "predictive_performance.md").write_text(f"""# Predictive performance

All prediction models use lagged features only.  Development metrics are out-of-fold CPCV estimates; holdout metrics are reported after development selection.

## Selected trend models by target

{_table(selected_predictions, [('target', 'Target'), ('config', 'Config'), ('model', 'Model'), ('label_tstat_threshold', 'Label threshold'), ('probability_threshold', 'Probability threshold')])}

## Top development-CPCV predictive configurations

{_table(result['prediction_metrics'][result['prediction_metrics'].split == 'development_cpcv'].sort_values('prediction_selection_score', ascending=False).head(30), [('config', 'Config'), ('target', 'Target'), ('model', 'Model'), ('label_tstat_threshold', 'Label threshold'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier'), ('prediction_selection_score', 'Selection score')])}

## Holdout metrics for selected target models

{_table(result['prediction_metrics'][(result['prediction_metrics'].split == 'holdout') & (result['prediction_metrics'].config.isin(selected_predictions.config.tolist()))], [('config', 'Config'), ('target', 'Target'), ('model', 'Model'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier'), ('true_positive', 'TP'), ('false_positive', 'FP'), ('false_negative', 'FN'), ('true_negative', 'TN')])}

## Calibration

See `calibration.csv` for bin-level predicted probability versus realized event rate.
""", encoding="utf-8")

    selected_meta = result.get("selected_meta")
    meta_summary = "No meta-model had enough valid primary-signal observations." if selected_meta is None else f"Selected meta-model by development metrics: **{selected_meta.config_name}**."
    (output / "meta_model_results.md").write_text(f"""# Meta-model results

{meta_summary}

The meta target is whether a candidate trend-scanning signal produced positive net return after estimated 25 bps round-trip costs over the selected trend horizon.  True future returns are used only as labels, never as live-decision features.

## Meta-model metrics

{_table(result['meta_metrics'], [('config', 'Config'), ('split', 'Split'), ('model', 'Model'), ('observations', 'Obs'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier'), ('selection_score', 'Selection score')], limit=80)}

## Meta-model feature importance

{_table(result['meta_importance'].head(40), [('config', 'Config'), ('feature', 'Feature'), ('importance', 'Importance'), ('method', 'Method')])}
""", encoding="utf-8")

    (output / "strategy_results.md").write_text(f"""# Strategy results

Strategy candidates were selected by development-only CPCV using median fold Sharpe, worst-fold Sharpe, positive fold rate, turnover, and simplicity.

## CPCV selection

{_table(result['strategy_selection'], [('candidate', 'Candidate'), ('family', 'Family'), ('rebalance_days', 'Rebalance days'), ('selection_score', 'Selection score'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds'), ('development_sharpe', 'Dev Sharpe'), ('development_cagr', 'Dev CAGR'), ('development_turnover', 'Dev turnover'), ('development_exposure', 'Dev exposure')], {'positive_fold_fraction', 'development_cagr', 'development_exposure'}, limit=80)}

## Selected candidate holdout cost sensitivity

{_table(selected_costs, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Calmar', 'Calmar'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure'), ('Worst Month', 'Worst month')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'Worst Month'})}

## Selected holdout decision frequencies

{_table(result['selected_decision_counts'], [('decision', 'Decision'), ('frequency', 'Frequency')], {'frequency'})}

## Incremental contribution

{_table(result['contribution_summary'], [('split', 'Split'), ('frozen_total_return', 'Frozen total return'), ('selected_total_return', 'Selected total return'), ('incremental_total_return', 'Incremental total return')], {'frozen_total_return', 'selected_total_return', 'incremental_total_return'})}
""", encoding="utf-8")

    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

Benchmarks are recomputed where possible from the same crypto panel.  Prior overlay rows are included only when prior reports exist.

{_table(comparison, [('name', 'Name'), ('benchmark_group', 'Group'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=120)}
""", encoding="utf-8")

    (output / "feature_importance.md").write_text(f"""# Feature importance

Feature importance is reported from coefficients or model impurity/importances when available.  Permutation importance and SHAP are not used for model selection; SHAP is only available if the dependency is installed and is not required for this report.

## Selected-model feature importance

{_table(top_importance.head(80), [('config', 'Config'), ('feature', 'Feature'), ('importance', 'Importance'), ('method', 'Method')])}

## Importance stability proxy

Lower rank-dispersion proxy implies more stable fold-level importance ranking.

{_table(result['importance_stability'].head(40), [('config', 'Config'), ('target', 'Target'), ('rank_correlation_proxy', 'Rank-dispersion proxy')])}

## Feature availability

Expansion Tier-1 features skipped because they were unavailable in reconstructed data: {', '.join(result['missing_tier1_features']) if result['missing_tier1_features'] else 'None'}.
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

- PBO: {_fmt(result['pbo'], True)}
- Deflated Sharpe probability: {_fmt(result['deflated_sharpe_probability'], True)}
- Bootstrap Sharpe CI: [{_fmt(result['bootstrap_sharpe_ci']['lower'])}, {_fmt(result['bootstrap_sharpe_ci']['upper'])}]
- Sharpe delta vs frozen benchmark: {_fmt(result['paired_sharpe_test']['sharpe_delta'])}
- Approximate p-value: {_fmt(result['paired_sharpe_test']['jobson_korkie_p_approx'])}
- Tested configurations: {result['tested_configurations']['total']}

## CPCV fold distribution for strategy candidates

{_table(result['strategy_cpcv_folds'], [('candidate', 'Candidate'), ('family', 'Family'), ('fold', 'Fold'), ('fold_sharpe', 'Fold Sharpe')], limit=120)}
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

{_final_questions(result)}

## Recommendation

**{result['final_conclusion']}**

Do not promote a trend-scanning strategy unless it improves economically and statistically.  If the selected development-CPCV candidate fails the guardrails, the frozen macro-regime strategy remains the final candidate.
""", encoding="utf-8")

    json_payload = {
        "protocol": result["protocol"],
        "winner": result["winner"],
        "selected_predictions": _json_safe(selected_predictions),
        "selected_meta": result["selected_meta"].config_name if result.get("selected_meta") is not None else None,
        "frozen_development": _json_safe(result["frozen_development"]),
        "frozen_holdout": _json_safe(result["frozen_holdout"]),
        "winner_development": _json_safe(result["winner_development"]),
        "winner_holdout": _json_safe(result["winner_holdout"]),
        "winner_holdout_50bps": _json_safe(result["winner_holdout_50bps"]),
        "pbo": _json_safe(result["pbo"]),
        "deflated_sharpe_probability": _json_safe(result["deflated_sharpe_probability"]),
        "bootstrap_sharpe_ci": _json_safe(result["bootstrap_sharpe_ci"]),
        "paired_sharpe_test": _json_safe(result["paired_sharpe_test"]),
        "passes_guardrails": result["passes_guardrails"],
        "tested_configurations": result["tested_configurations"],
        "final_conclusion": result["final_conclusion"],
    }
    (output / "results.json").write_text(json.dumps(json_payload, indent=2), encoding="utf-8")


def run_default_trend_scanning_ml(output_dir: str | Path = "reports/trend_scanning_ml") -> dict[str, Any]:
    panel, macro_features, public_data, volatility_probability = load_default_inputs()
    result = run_trend_scanning_ml(panel, macro_features, public_data, volatility_probability)
    write_trend_scanning_reports(output_dir, result)
    return result


__all__ = [
    "LABEL_HORIZONS",
    "LABEL_TSTAT_THRESHOLDS",
    "TARGET_SPECS",
    "build_trend_scan_table",
    "apply_trend_thresholds",
    "run_trend_scanning_ml",
    "write_trend_scanning_reports",
    "run_default_trend_scanning_ml",
]
