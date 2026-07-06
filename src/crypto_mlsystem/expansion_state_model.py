"""Crypto expansion-state detection for systematic allocation.

This module is intentionally standalone.  It does not modify the frozen
``btc_eth_macro_gate_balanced`` strategy.  Expansion-state models are selected
with development-only CPCV, then evaluated on the locked 2025+ holdout.
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
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    brier_score_loss,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
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
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import deflated_sharpe_probability, probability_backtest_overfitting


BASELINE_NAME = FIXED_SELECTED.name
CRYPTO_EXPANSION_FEATURES = (
    "stablecoin_supply_change_7d",
    "tvl_growth_30d",
    "volatility_4h_7d",
    "volatility_expansion_probability",
    "cross_sectional_dispersion",
)
FEATURES = tuple(MACRO_TIER1_FEATURES + CRYPTO_EXPANSION_FEATURES)
TARGET_SPECS: tuple[tuple[str, str], ...] = (
    ("btc_30d_gt_15", "BTC 30-day forward return > +15%"),
    ("eth_30d_gt_20", "ETH 30-day forward return > +20%"),
    ("btc_eth_50_50_30d_gt_15", "50/50 BTC/ETH 30-day forward return > +15%"),
    ("top10_30d_gt_20", "Top-10 crypto basket 30-day forward return > +20%"),
    ("eth_leads_btc_30d_gt_5", "ETH outperforms BTC over the next 30 days by at least +5%"),
)
OVERLAY_TYPES = (
    "expansion_probability_sizing",
    "expansion_threshold_filter",
    "eth_leadership_tilt",
    "expansion_sizing_eth_tilt",
)


@dataclass(frozen=True)
class ModelSpec:
    name: str
    family: str
    factory: Callable[[], Any]


@dataclass(frozen=True)
class OverlaySpec:
    name: str
    overlay_type: str
    expansion_threshold: float
    leadership_threshold: float
    rebalance_days: int
    description: str


@dataclass
class PredictionBundle:
    config_name: str
    target: str
    target_description: str
    model_name: str
    model_family: str
    threshold: float
    dev_probability: pd.Series
    holdout_probability: pd.Series
    full_probability: pd.Series
    feature_importance: pd.DataFrame
    model_available_note: str = ""


def available_model_specs() -> list[ModelSpec]:
    specs: list[ModelSpec] = [
        ModelSpec(
            "logistic_regression",
            "Logistic regression",
            lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=750, class_weight="balanced", random_state=23)),
        ),
        ModelSpec(
            "elastic_net_logistic",
            "Elastic Net logistic regression",
            lambda: make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    solver="saga",
                    l1_ratio=0.40,
                    C=0.50,
                    max_iter=5000,
                    class_weight="balanced",
                    random_state=23,
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
                random_state=23,
                n_jobs=-1,
            ),
        ),
        ModelSpec(
            "gradient_boosting",
            "Gradient boosting",
            lambda: GradientBoostingClassifier(
                n_estimators=120,
                max_depth=2,
                learning_rate=0.04,
                min_samples_leaf=10,
                random_state=23,
            ),
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
                random_state=23,
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
                random_state=23,
                verbose=-1,
            )

        specs.append(ModelSpec("lightgbm", "LightGBM", lgbm_factory))
    return specs


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int = 7) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def _feature_frame(dataset: MacroRegimeDataset, public_data: PublicDataBundle | None = None) -> pd.DataFrame:
    base = dataset.regime_features.copy()
    if "volatility_4h_7d" not in base:
        vol = pd.Series(np.nan, index=base.index)
        if public_data is not None and not public_data.binance_4h_daily_features.empty:
            intraday = public_data.binance_4h_daily_features.copy()
            if "volatility_4h_7d" in intraday:
                intraday["date"] = pd.to_datetime(intraday["date"])
                matrix = intraday.pivot(index="date", columns="symbol", values="volatility_4h_7d").sort_index()
                available = [symbol for symbol in ("BTC", "ETH") if symbol in matrix]
                if available:
                    vol = matrix[available].mean(axis=1).reindex(base.index).ffill()
        if vol.isna().all():
            available = [symbol for symbol in ("BTC", "ETH") if symbol in dataset.returns]
            if available:
                vol = dataset.returns[available].rolling(7).std().mean(axis=1) * np.sqrt(365)
        base["volatility_4h_7d"] = vol
    frame = base.reindex(columns=list(FEATURES)).replace([np.inf, -np.inf], np.nan).shift(1)
    development = frame.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    medians = development.median().fillna(0.0)
    return frame.ffill().fillna(medians).fillna(0.0)


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
        end_pos = index.searchsorted(date + pd.Timedelta(days=horizon_days))
        if end_pos >= len(index):
            values.append(np.nan)
            continue
        start_price = prices.loc[date]
        end_price = prices.iloc[end_pos]
        values.append(float(end_price / start_price - 1.0) if pd.notna(start_price) and pd.notna(end_price) and start_price > 0 else np.nan)
    return pd.Series(values, index=dates)


def _top10_forward_return(dataset: MacroRegimeDataset, dates: pd.DatetimeIndex, horizon_days: int = 30) -> pd.Series:
    values = []
    close = dataset.close
    index = close.index
    for date in dates:
        if date not in index or date not in dataset.universe_weights.index:
            values.append(np.nan)
            continue
        end_pos = index.searchsorted(date + pd.Timedelta(days=horizon_days))
        if end_pos >= len(index):
            values.append(np.nan)
            continue
        assets = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        if len(assets) == 0:
            values.append(np.nan)
            continue
        start = close.loc[date, assets].replace(0, np.nan)
        end = close.iloc[end_pos][assets]
        asset_returns = (end / start - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
        values.append(float(asset_returns.mean()) if len(asset_returns) else np.nan)
    return pd.Series(values, index=dates)


def build_expansion_targets(dataset: MacroRegimeDataset, dates: pd.DatetimeIndex) -> pd.DataFrame:
    btc = _forward_return(dataset.close, "BTC", dates)
    eth = _forward_return(dataset.close, "ETH", dates)
    mix = 0.50 * btc + 0.50 * eth
    top10 = _top10_forward_return(dataset, dates)
    targets = pd.DataFrame(index=dates)
    targets["btc_30d_gt_15"] = (btc > 0.15).astype(float)
    targets["eth_30d_gt_20"] = (eth > 0.20).astype(float)
    targets["btc_eth_50_50_30d_gt_15"] = (mix > 0.15).astype(float)
    targets["top10_30d_gt_20"] = (top10 > 0.20).astype(float)
    targets["eth_leads_btc_30d_gt_5"] = ((eth - btc) > 0.05).astype(float)
    unavailable = pd.concat([btc, eth, mix, top10], axis=1).isna().any(axis=1)
    targets.loc[unavailable, :] = np.nan
    return targets


def target_diagnostics(targets: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    descriptions = dict(TARGET_SPECS)
    for target in targets.columns:
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
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


def _positive_probability(model: Any, x: pd.DataFrame) -> np.ndarray:
    if len(x) == 0:
        return np.array([])
    classes = list(getattr(model, "classes_", []))
    if 1 not in classes:
        return np.zeros(len(x))
    return model.predict_proba(x)[:, classes.index(1)]


def _constant_prob(y: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(float(y.mean()) if len(y) else 0.0, index=index)


def _cpcv_probabilities(x_dev: pd.DataFrame, y_dev: pd.Series, spec: ModelSpec) -> tuple[pd.Series, pd.DataFrame]:
    probabilities = pd.Series(0.0, index=x_dev.index)
    counts = pd.Series(0.0, index=x_dev.index)
    fold_rows: list[dict[str, Any]] = []
    if len(x_dev) < 30:
        return _constant_prob(y_dev, x_dev.index), pd.DataFrame()
    splits = combinatorial_purged_splits(len(x_dev), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    for number, split in enumerate(splits):
        train_index = x_dev.index[list(split.train_indices)]
        test_index = x_dev.index[list(split.test_indices)]
        y_train = y_dev.loc[train_index]
        if y_train.nunique() < 2:
            prob = _constant_prob(y_train, test_index)
        else:
            model = spec.factory()
            model.fit(x_dev.loc[train_index], y_train)
            prob = pd.Series(_positive_probability(model, x_dev.loc[test_index]), index=test_index)
        probabilities.loc[test_index] += prob
        counts.loc[test_index] += 1.0
        fold_rows.append({
            "model": spec.name,
            "fold": number,
            "test_groups": ",".join(str(group) for group in split.test_groups),
            "train_samples": len(train_index),
            "test_samples": len(test_index),
        })
    return (probabilities / counts.replace(0, np.nan)).fillna(float(y_dev.mean())), pd.DataFrame(fold_rows)


def _train_holdout_probabilities(x_dev: pd.DataFrame, y_dev: pd.Series, x_holdout: pd.DataFrame, spec: ModelSpec) -> tuple[pd.Series, Any | None]:
    if y_dev.nunique() < 2 or len(x_holdout) == 0:
        return _constant_prob(y_dev, x_holdout.index), None
    model = spec.factory()
    model.fit(x_dev, y_dev)
    return pd.Series(_positive_probability(model, x_holdout), index=x_holdout.index), model


def _threshold_from_dev(prob: pd.Series, y: pd.Series) -> float:
    best_threshold = 0.50
    best_score = -np.inf
    grid = (0.40, 0.50, 0.60, 0.70)
    for threshold in grid:
        pred = (prob >= threshold).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
        score = float(f1 + 0.05 * precision + 0.05 * recall)
        if score > best_score:
            best_score = score
            best_threshold = threshold
    return best_threshold


def _classification_metrics(y: pd.Series, prob: pd.Series, threshold: float, split: str, config_name: str, target: str, model: str) -> dict[str, Any]:
    aligned = pd.concat([y.rename("y"), prob.rename("probability")], axis=1).dropna()
    if aligned.empty:
        return {
            "config": config_name,
            "target": target,
            "model": model,
            "split": split,
            "threshold": threshold,
            "observations": 0,
            "positive_events": 0,
            "auc": np.nan,
            "precision": np.nan,
            "recall": np.nan,
            "f1": np.nan,
            "brier_score": np.nan,
            "true_negative": 0,
            "false_positive": 0,
            "false_negative": 0,
            "true_positive": 0,
        }
    y_true = aligned["y"].astype(int)
    probabilities = aligned["probability"].clip(0.0, 1.0)
    pred = (probabilities >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, pred, average="binary", zero_division=0)
    matrix = confusion_matrix(y_true, pred, labels=[0, 1])
    auc = roc_auc_score(y_true, probabilities) if y_true.nunique() == 2 else np.nan
    return {
        "config": config_name,
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


def _feature_importance(model: Any | None, spec: ModelSpec, feature_names: list[str], config_name: str) -> pd.DataFrame:
    if model is None:
        return pd.DataFrame({"config": [config_name], "feature": ["constant_probability"], "importance": [0.0], "method": ["constant"]})
    fitted = model
    if hasattr(model, "named_steps"):
        fitted = list(model.named_steps.values())[-1]
    if hasattr(fitted, "coef_"):
        values = np.ravel(fitted.coef_)
        method = "coefficient"
    elif hasattr(fitted, "feature_importances_"):
        values = np.ravel(fitted.feature_importances_)
        method = "model_importance"
    else:
        values = np.zeros(len(feature_names))
        method = "not_available"
    rows = []
    for feature, value in zip(feature_names, values):
        rows.append({"config": config_name, "model": spec.name, "feature": feature, "importance": float(value), "method": method})
    return pd.DataFrame(rows).sort_values("importance", key=lambda s: s.abs(), ascending=False)


def fit_expansion_models(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    model_specs: list[ModelSpec] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, PredictionBundle], pd.DataFrame]:
    model_specs = model_specs or available_model_specs()
    dates = features.index
    dev_mask = (dates >= DEVELOPMENT_START) & (dates <= DEVELOPMENT_END)
    holdout_mask = (dates >= HOLDOUT_START) & (dates <= HOLDOUT_END)
    x_dev_all = features.loc[dev_mask]
    x_holdout = features.loc[holdout_mask]
    rows: list[dict[str, Any]] = []
    fold_rows: list[pd.DataFrame] = []
    bundles: dict[str, PredictionBundle] = {}
    for target_name, description in TARGET_SPECS:
        if target_name not in targets:
            continue
        valid_dev = targets[target_name].loc[x_dev_all.index].dropna().index
        y_dev = targets.loc[valid_dev, target_name].astype(int)
        x_dev = x_dev_all.loc[valid_dev]
        y_holdout = targets.loc[x_holdout.index, target_name].dropna().astype(int)
        x_holdout_valid = x_holdout.loc[y_holdout.index]
        for spec in model_specs:
            config_name = f"{target_name}__{spec.name}"
            dev_prob, folds = _cpcv_probabilities(x_dev, y_dev, spec)
            if not folds.empty:
                folds["config"] = config_name
                folds["target"] = target_name
                fold_rows.append(folds)
            threshold = _threshold_from_dev(dev_prob, y_dev)
            holdout_prob, model = _train_holdout_probabilities(x_dev, y_dev, x_holdout_valid, spec)
            full_probability = pd.Series(np.nan, index=features.index)
            full_probability.loc[dev_prob.index] = dev_prob
            full_probability.loc[holdout_prob.index] = holdout_prob
            rows.append(_classification_metrics(y_dev, dev_prob, threshold, "development_cpcv", config_name, target_name, spec.name))
            rows.append(_classification_metrics(y_holdout, holdout_prob, threshold, "holdout", config_name, target_name, spec.name))
            bundles[config_name] = PredictionBundle(
                config_name=config_name,
                target=target_name,
                target_description=description,
                model_name=spec.name,
                model_family=spec.family,
                threshold=threshold,
                dev_probability=dev_prob,
                holdout_probability=holdout_prob,
                full_probability=full_probability.ffill().fillna(float(dev_prob.mean()) if len(dev_prob) else 0.0),
                feature_importance=_feature_importance(model, spec, list(features.columns), config_name),
            )
    metrics = pd.DataFrame(rows)
    if metrics.empty:
        selection = pd.DataFrame()
    else:
        dev = metrics[metrics.split == "development_cpcv"].copy()
        dev["selection_score"] = dev["auc"].fillna(0.5) - dev["brier_score"].fillna(1.0) + 0.10 * dev["f1"].fillna(0.0)
        selection = dev.sort_values(["selection_score", "auc", "brier_score"], ascending=[False, False, True])
    folds = pd.concat(fold_rows, ignore_index=True) if fold_rows else pd.DataFrame()
    return metrics, selection, bundles, folds


def select_prediction_bundles(selection: pd.DataFrame, bundles: dict[str, PredictionBundle]) -> tuple[PredictionBundle, PredictionBundle]:
    if selection.empty:
        raise ValueError("No expansion-state prediction configurations were available.")
    expansion_rows = selection[selection.target != "eth_leads_btc_30d_gt_5"]
    leadership_rows = selection[selection.target == "eth_leads_btc_30d_gt_5"]
    expansion_config = str((expansion_rows if not expansion_rows.empty else selection).iloc[0].config)
    leadership_config = str((leadership_rows if not leadership_rows.empty else selection).iloc[0].config)
    return bundles[expansion_config], bundles[leadership_config]


def calibration_table(targets: pd.DataFrame, bundles: list[PredictionBundle]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        for split, probability in (
            ("development_cpcv", bundle.dev_probability),
            ("holdout", bundle.holdout_probability),
        ):
            y = targets[bundle.target].reindex(probability.index).dropna().astype(int)
            aligned = pd.concat([y.rename("y"), probability.rename("p")], axis=1).dropna()
            if aligned.empty:
                continue
            ranked = aligned["p"].rank(method="first")
            bins = pd.qcut(ranked, q=min(10, len(aligned)), duplicates="drop")
            grouped = aligned.groupby(bins, observed=False)
            for number, (_, group) in enumerate(grouped, start=1):
                rows.append({
                    "config": bundle.config_name,
                    "target": bundle.target,
                    "split": split,
                    "bin": number,
                    "observations": int(len(group)),
                    "mean_probability": float(group["p"].mean()),
                    "event_rate": float(group["y"].mean()),
                })
    return pd.DataFrame(rows)


def predeclared_overlay_specs(expansion_threshold: float, leadership_threshold: float) -> list[OverlaySpec]:
    expansion_grid = tuple(sorted(set([0.50, 0.60, float(expansion_threshold)])))
    leadership_grid = tuple(sorted(set([0.50, 0.60, float(leadership_threshold)])))
    specs: list[OverlaySpec] = []
    for rebalance_days in (7, 14):
        for threshold in expansion_grid:
            specs.append(OverlaySpec(
                name=f"expansion_sizing_t{int(threshold * 100)}_{rebalance_days}d",
                overlay_type="expansion_probability_sizing",
                expansion_threshold=threshold,
                leadership_threshold=leadership_threshold,
                rebalance_days=rebalance_days,
                description="Macro gate plus expansion probability sizing.",
            ))
            specs.append(OverlaySpec(
                name=f"expansion_filter_t{int(threshold * 100)}_{rebalance_days}d",
                overlay_type="expansion_threshold_filter",
                expansion_threshold=threshold,
                leadership_threshold=leadership_threshold,
                rebalance_days=rebalance_days,
                description="Macro gate plus expansion threshold filter.",
            ))
            for lead_threshold in leadership_grid:
                specs.append(OverlaySpec(
                    name=f"expansion_sizing_eth_tilt_e{int(threshold * 100)}_l{int(lead_threshold * 100)}_{rebalance_days}d",
                    overlay_type="expansion_sizing_eth_tilt",
                    expansion_threshold=threshold,
                    leadership_threshold=lead_threshold,
                    rebalance_days=rebalance_days,
                    description="Macro gate plus expansion sizing and ETH leadership tilt.",
                ))
        for lead_threshold in leadership_grid:
            specs.append(OverlaySpec(
                name=f"eth_leadership_tilt_l{int(lead_threshold * 100)}_{rebalance_days}d",
                overlay_type="eth_leadership_tilt",
                expansion_threshold=expansion_threshold,
                leadership_threshold=lead_threshold,
                rebalance_days=rebalance_days,
                description="Macro gate plus ETH leadership tilt.",
            ))
    unique: dict[str, OverlaySpec] = {}
    for spec in specs:
        unique[spec.name] = spec
    return list(unique.values())


def _base_exposure_for_regime(regime: str) -> float:
    if regime == "risk_on":
        return 1.0
    if regime == "neutral":
        return 0.50
    return 0.0


def build_overlay_weights(
    dataset: MacroRegimeDataset,
    base_combined: pd.Series,
    expansion_probability: pd.Series,
    leadership_probability: pd.Series,
    spec: OverlaySpec,
) -> tuple[pd.DataFrame, pd.Series]:
    dates = _rebalance_dates(dataset.close.index, spec.rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    decision = pd.Series("cash", index=dates, dtype=object)
    expansion = expansion_probability.reindex(dates).ffill().fillna(0.0).clip(0.0, 1.0)
    leadership = leadership_probability.reindex(dates).ffill().fillna(0.0).clip(0.0, 1.0)
    regimes = base_combined.reindex(dates).ffill().fillna("risk_off")
    for date in dates:
        regime = str(regimes.loc[date])
        if regime == "risk_off":
            decision.loc[date] = "macro_risk_off_cash"
            continue
        base_exposure = _base_exposure_for_regime(regime)
        expansion_prob = float(expansion.loc[date])
        leadership_prob = float(leadership.loc[date])
        if spec.overlay_type == "expansion_probability_sizing":
            if expansion_prob >= spec.expansion_threshold:
                exposure = max(base_exposure, 1.0 if regime == "risk_on" else 0.75)
                decision.loc[date] = "high_expansion_fuller_exposure"
            elif expansion_prob < max(0.0, spec.expansion_threshold - 0.20):
                exposure = min(base_exposure, 0.50 if regime == "risk_on" else 0.25)
                decision.loc[date] = "low_expansion_conservative"
            else:
                exposure = base_exposure
                decision.loc[date] = "medium_expansion_base"
        elif spec.overlay_type == "expansion_threshold_filter":
            if expansion_prob >= spec.expansion_threshold:
                exposure = base_exposure
                decision.loc[date] = "expansion_confirmed"
            else:
                exposure = 0.25 if regime == "risk_on" else 0.0
                decision.loc[date] = "expansion_not_confirmed_reduced"
        elif spec.overlay_type == "eth_leadership_tilt":
            exposure = base_exposure
            decision.loc[date] = "eth_tilt" if leadership_prob >= spec.leadership_threshold else "balanced_btc_eth"
        elif spec.overlay_type == "expansion_sizing_eth_tilt":
            if expansion_prob >= spec.expansion_threshold:
                exposure = max(base_exposure, 1.0 if regime == "risk_on" else 0.75)
                decision.loc[date] = "high_expansion_eth_tilt" if leadership_prob >= spec.leadership_threshold else "high_expansion_balanced"
            elif expansion_prob < max(0.0, spec.expansion_threshold - 0.20):
                exposure = min(base_exposure, 0.50 if regime == "risk_on" else 0.25)
                decision.loc[date] = "low_expansion_reduced"
            else:
                exposure = base_exposure
                decision.loc[date] = "medium_expansion_eth_tilt" if leadership_prob >= spec.leadership_threshold else "medium_expansion_balanced"
        else:
            raise ValueError(spec.overlay_type)

        eligible = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        btc_available = "BTC" in weights.columns and "BTC" in eligible
        eth_available = "ETH" in weights.columns and "ETH" in eligible
        if not btc_available and not eth_available:
            continue
        use_eth_tilt = "eth_tilt" in decision.loc[date] or "ETH leadership" in spec.description
        if use_eth_tilt and leadership_prob >= spec.leadership_threshold and btc_available and eth_available:
            weights.loc[date, "BTC"] = min(0.40, exposure * 0.30)
            weights.loc[date, "ETH"] = min(0.70, exposure * 0.70)
        elif btc_available and eth_available:
            weights.loc[date, "BTC"] = min(0.50, exposure * 0.50)
            weights.loc[date, "ETH"] = min(0.50, exposure * 0.50)
        elif btc_available:
            weights.loc[date, "BTC"] = min(1.0, exposure)
        elif eth_available:
            weights.loc[date, "ETH"] = min(1.0, exposure)
    return weights, decision


def _weekly_return(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0).dropna()


def _fold_sharpe(values: pd.Series, indices: tuple[int, ...]) -> float:
    subset = values.iloc[list(indices)].replace([np.inf, -np.inf], np.nan).dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def select_overlay_cpcv(results_25bps: dict[str, PortfolioResult], specs: list[OverlaySpec]) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    config_returns: dict[str, pd.Series] = {}
    for spec in specs:
        result = results_25bps[spec.name]
        weekly = _weekly_return(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        config_returns[spec.name] = weekly
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_values = []
        for number, split in enumerate(splits):
            sharpe = _fold_sharpe(weekly, split.test_indices)
            fold_values.append(sharpe)
            fold_rows.append({
                "candidate": spec.name,
                "overlay_type": spec.overlay_type,
                "fold": number,
                "test_groups": ",".join(str(group) for group in split.test_groups),
                "fold_sharpe": sharpe,
            })
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        turnover_penalty = max(0.0, dev["Annual Turnover"] - 12.0) * 0.05
        exposure_penalty = max(0.0, 0.15 - dev["Exposure"]) * 0.50
        rows.append({
            "candidate": spec.name,
            "overlay_type": spec.overlay_type,
            "description": spec.description,
            "rebalance_days": spec.rebalance_days,
            "expansion_threshold": spec.expansion_threshold,
            "leadership_threshold": spec.leadership_threshold,
            "median_fold_sharpe": float(np.nanmedian(fold_values)),
            "worst_fold_sharpe": float(np.nanmin(fold_values)),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_values) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
            "turnover_penalty": turnover_penalty,
            "exposure_penalty": exposure_penalty,
        })
    selection = pd.DataFrame(rows)
    selection["selection_score"] = (
        selection["median_fold_sharpe"]
        + 0.25 * selection["worst_fold_sharpe"]
        + 0.40 * selection["positive_fold_fraction"]
        - selection["turnover_penalty"]
        - selection["exposure_penalty"]
    )
    selection = selection.sort_values("selection_score", ascending=False)
    pbo = probability_backtest_overfitting(pd.concat(config_returns, axis=1).sort_index(), blocks=8)
    return selection, pd.DataFrame(fold_rows), str(selection.iloc[0].candidate), pbo


def _all_risk_on(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series, pd.Series]:
    risk_on = pd.Series("risk_on", index=index, dtype=object)
    crypto = pd.Series("not_used", index=index, dtype=object)
    return risk_on, crypto, risk_on


def _buy_hold_weights(dataset: MacroRegimeDataset, name: str) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=dataset.close.index, columns=dataset.close.columns)
    if name == "btc_buy_hold" and "BTC" in weights:
        weights["BTC"] = 1.0
    elif name == "eth_buy_hold" and "ETH" in weights:
        weights["ETH"] = 1.0
    elif name == "btc_eth_50_50":
        for symbol in ("BTC", "ETH"):
            if symbol in weights:
                weights[symbol] = 0.50
    elif name == "equal_weight_top10":
        active = dataset.universe_weights > 0
        weights = active.div(active.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    else:
        if name != "equal_weight_top10":
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


def _prior_meta_overlay_rows(path: str | Path = "reports/strategy_enhancement_research/development_holdout_retention.csv") -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    selected = frame[frame.candidate == "meta_gradient_boosting_60"].copy()
    if selected.empty:
        return pd.DataFrame()
    rows = []
    for _, row in selected.iterrows():
        rows.append({
            "name": "meta_gradient_boosting_60",
            "family": "Conservative ML meta-label overlay from prior module",
            "benchmark_group": "prior_conservative_meta_overlay",
            "split": "development",
            "cost_bps": 25,
            "selected_development_candidate": False,
            "CAGR": row["development_cagr"],
            "Sharpe": row["development_sharpe"],
            "Maximum Drawdown": row["development_max_drawdown"],
            "Annual Turnover": row["development_turnover"],
            "Exposure": row["development_exposure"],
        })
        rows.append({
            "name": "meta_gradient_boosting_60",
            "family": "Conservative ML meta-label overlay from prior module",
            "benchmark_group": "prior_conservative_meta_overlay",
            "split": "holdout",
            "cost_bps": 25,
            "selected_development_candidate": False,
            "CAGR": row["holdout_cagr"],
            "Sharpe": row["holdout_sharpe"],
            "Maximum Drawdown": row["holdout_max_drawdown"],
            "Annual Turnover": row["holdout_turnover"],
            "Exposure": row["holdout_exposure"],
        })
    return pd.DataFrame(rows)


def _prior_tier1_rows(path: str | Path = "reports/tier1_regime_momentum/metrics.csv") -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    selected = frame[frame.get("category", "").astype(str).eq("strategy")].copy() if "category" in frame else frame.copy()
    if selected.empty:
        return pd.DataFrame()
    name = str(selected.iloc[0].get("name", "prior_tier1_regime_momentum"))
    selected = selected[selected.get("name", name) == name].copy() if "name" in selected else selected.head(0)
    if selected.empty:
        return pd.DataFrame()
    selected["family"] = "Prior Tier-1 regime momentum"
    selected["benchmark_group"] = "prior_tier1_regime_momentum"
    selected["selected_development_candidate"] = False
    return selected


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
            ("equal_weight_top10", "Equal-weight top 10"),
        ):
            result = backtest_weights(dataset, _buy_hold_weights(dataset, name), *risk_on, cost_bps=cost, turnover_cap=10.0)
            rows.extend(_rows_for_result(name, family, "benchmark", cost, result))
            results[f"{name}_{cost}"] = result
    prior_meta = _prior_meta_overlay_rows()
    if not prior_meta.empty:
        rows.extend(prior_meta.to_dict("records"))
    prior_tier1 = _prior_tier1_rows()
    if not prior_tier1.empty:
        rows.extend(prior_tier1.to_dict("records"))
    return pd.DataFrame(rows), results


def run_expansion_state_model(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
    model_specs: list[ModelSpec] | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    features = _feature_frame(dataset, public_data)
    dates = _rebalance_dates(dataset.close.index, 7)
    x = features.reindex(dates).ffill().fillna(0.0)
    targets = build_expansion_targets(dataset, dates)
    diagnostics = target_diagnostics(targets)
    prediction_metrics, prediction_selection, bundles, cpcv_model_folds = fit_expansion_models(x, targets, model_specs)
    expansion_bundle, leadership_bundle = select_prediction_bundles(prediction_selection, bundles)
    selected_calibration = calibration_table(targets, [expansion_bundle, leadership_bundle])
    feature_importance = pd.concat([bundle.feature_importance for bundle in bundles.values()], ignore_index=True)

    frozen_weights, frozen_macro, frozen_crypto, frozen_combined = build_candidate_weights(dataset, FIXED_SELECTED)
    frozen_regimes = (frozen_macro, frozen_crypto, frozen_combined)
    frozen_25 = backtest_weights(dataset, frozen_weights, frozen_macro, frozen_crypto, frozen_combined, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
    frozen_holdout = period_metrics(frozen_25, HOLDOUT_START, HOLDOUT_END)

    overlay_specs = predeclared_overlay_specs(expansion_bundle.threshold, leadership_bundle.threshold)
    overlay_results: dict[str, dict[int, PortfolioResult]] = {}
    overlay_decisions: dict[str, pd.Series] = {}
    for spec in overlay_specs:
        weights, decision = build_overlay_weights(
            dataset,
            frozen_combined,
            expansion_bundle.full_probability,
            leadership_bundle.full_probability,
            spec,
        )
        overlay_decisions[spec.name] = decision
        overlay_results[spec.name] = {
            cost: backtest_weights(dataset, weights, frozen_macro, frozen_crypto, frozen_combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
            for cost in COST_LEVELS
        }
    results_25bps = {name: by_cost[25] for name, by_cost in overlay_results.items()}
    overlay_selection, overlay_folds, selected_overlay, strategy_pbo = select_overlay_cpcv(results_25bps, overlay_specs)

    overlay_metric_rows: list[dict[str, Any]] = []
    for spec in overlay_specs:
        for cost, result in overlay_results[spec.name].items():
            rows = _rows_for_result(
                spec.name,
                spec.description,
                spec.overlay_type,
                cost,
                result,
                selected=spec.name == selected_overlay,
            )
            for row in rows:
                row.update({
                    "expansion_threshold": spec.expansion_threshold,
                    "leadership_threshold": spec.leadership_threshold,
                    "rebalance_days": spec.rebalance_days,
                })
            overlay_metric_rows.extend(rows)
    overlay_metrics = pd.DataFrame(overlay_metric_rows)
    benchmarks, benchmark_results = evaluate_benchmarks(dataset, frozen_weights, frozen_regimes)

    selected_holdout = overlay_metrics[
        (overlay_metrics.name == selected_overlay)
        & (overlay_metrics.split == "holdout")
        & (overlay_metrics.cost_bps == 25)
    ].iloc[0]
    selected_holdout_50 = overlay_metrics[
        (overlay_metrics.name == selected_overlay)
        & (overlay_metrics.split == "holdout")
        & (overlay_metrics.cost_bps == 50)
    ].iloc[0]
    selected_result = overlay_results[selected_overlay][25]
    selected_dsr = deflated_sharpe_probability(
        selected_result.returns.loc[HOLDOUT_START:HOLDOUT_END],
        tested_configurations=len(overlay_specs) + len(prediction_selection),
    )
    exposure_classification = "replacement_candidate" if selected_holdout["Exposure"] >= 0.15 else "risk_monitoring_only"
    improves = bool(
        selected_holdout["Sharpe"] > frozen_holdout["Sharpe"] + 0.10
        and selected_holdout["CAGR"] >= frozen_holdout["CAGR"] * 0.90
        and selected_holdout["Maximum Drawdown"] >= frozen_holdout["Maximum Drawdown"] - 0.05
        and selected_holdout_50["CAGR"] > 0
        and selected_holdout["Annual Turnover"] <= 12
        and selected_holdout["Exposure"] >= 0.15
    )
    if improves:
        final_conclusion = "expansion-state overlay complements the frozen strategy for paper monitoring"
    elif selected_holdout["Exposure"] < 0.15:
        final_conclusion = "expansion-state model is useful as diagnostics only because selected exposure is trivially low"
    elif selected_holdout["Sharpe"] > frozen_holdout["Sharpe"]:
        final_conclusion = "expansion-state model improves some risk metrics but fails full replacement criteria"
    else:
        final_conclusion = "expansion-state model fails to improve the frozen macro strategy"

    selected_decision_counts = overlay_decisions[selected_overlay].loc[HOLDOUT_START:HOLDOUT_END].value_counts(normalize=True).rename_axis("decision").reset_index(name="frequency")
    return {
        "dataset": dataset,
        "features": features,
        "targets": targets,
        "target_diagnostics": diagnostics,
        "prediction_metrics": prediction_metrics,
        "prediction_selection": prediction_selection,
        "prediction_bundles": bundles,
        "selected_expansion_model": expansion_bundle,
        "selected_leadership_model": leadership_bundle,
        "calibration": selected_calibration,
        "feature_importance": feature_importance,
        "cpcv_model_folds": cpcv_model_folds,
        "overlay_specs": overlay_specs,
        "overlay_results": overlay_results,
        "overlay_selection": overlay_selection,
        "overlay_folds": overlay_folds,
        "overlay_metrics": overlay_metrics,
        "overlay_decisions": overlay_decisions,
        "selected_overlay": selected_overlay,
        "selected_decision_counts": selected_decision_counts,
        "benchmarks": benchmarks,
        "benchmark_results": benchmark_results,
        "frozen_holdout": frozen_holdout,
        "strategy_pbo": strategy_pbo,
        "selected_deflated_sharpe_probability": selected_dsr,
        "exposure_classification": exposure_classification,
        "final_conclusion": final_conclusion,
        "tested_configurations": {
            "prediction_configs": int(len(prediction_selection)),
            "overlay_configs": int(len(overlay_specs)),
            "total": int(len(prediction_selection) + len(overlay_specs)),
        },
        "protocol": {
            "title": "Crypto Expansion-State Detection for Systematic Allocation",
            "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} to {HOLDOUT_END.date()}",
            "baseline": BASELINE_NAME,
            "selection_rule": "Prediction and overlay selection use development-only CPCV. Holdout is reported after selection only.",
            "holdout_rule": "No holdout threshold tuning, model selection, or best-cell selection.",
        },
    }


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
    if isinstance(value, pd.DataFrame):
        return _json_safe(value.to_dict("records"))
    if isinstance(value, pd.Series):
        return _json_safe(value.to_dict())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value)
    return value


def write_expansion_state_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result["target_diagnostics"].to_csv(output / "target_diagnostics.csv", index=False)
    result["prediction_metrics"].to_csv(output / "prediction_metrics.csv", index=False)
    result["prediction_selection"].to_csv(output / "prediction_selection.csv", index=False)
    result["calibration"].to_csv(output / "calibration_curve.csv", index=False)
    result["feature_importance"].to_csv(output / "feature_importance.csv", index=False)
    result["overlay_selection"].to_csv(output / "overlay_selection.csv", index=False)
    result["overlay_folds"].to_csv(output / "overlay_cpcv_folds.csv", index=False)
    result["overlay_metrics"].to_csv(output / "overlay_metrics.csv", index=False)
    result["benchmarks"].to_csv(output / "benchmark_metrics.csv", index=False)
    result["selected_decision_counts"].to_csv(output / "selected_overlay_decision_counts.csv", index=False)

    frozen = result["frozen_holdout"]
    selected = result["selected_overlay"]
    selected_holdout = result["overlay_metrics"][
        (result["overlay_metrics"].name == selected)
        & (result["overlay_metrics"].split == "holdout")
        & (result["overlay_metrics"].cost_bps == 25)
    ].iloc[0]
    selected_costs = result["overlay_metrics"][(result["overlay_metrics"].name == selected) & (result["overlay_metrics"].split == "holdout")]
    selected_expansion = result["selected_expansion_model"]
    selected_leadership = result["selected_leadership_model"]

    (output / "results_summary.md").write_text(f"""# Results summary

Project: **{result['protocol']['title']}**

The frozen baseline remains **{BASELINE_NAME}**. This module did not modify or
reselect it.

## Protocol

- Development period: {result['protocol']['development_period']}
- Locked holdout: {result['protocol']['locked_holdout']}
- Selection rule: {result['protocol']['selection_rule']}
- Tested configurations: {result['tested_configurations']['total']} total ({result['tested_configurations']['prediction_configs']} prediction, {result['tested_configurations']['overlay_configs']} overlay)

## Development-selected models

- Expansion model: **{selected_expansion.config_name}**
- ETH leadership model: **{selected_leadership.config_name}**
- Overlay selected by development-only CPCV: **{selected}**

## Holdout comparison at 25 bps

| Strategy | Sharpe | CAGR | Max DD | Turnover | Exposure |
|---|---:|---:|---:|---:|---:|
| Frozen {BASELINE_NAME} | {_fmt(frozen['Sharpe'])} | {_fmt(frozen['CAGR'], True)} | {_fmt(frozen['Maximum Drawdown'], True)} | {_fmt(frozen['Annual Turnover'])} | {_fmt(frozen['Exposure'], True)} |
| Selected expansion overlay | {_fmt(selected_holdout['Sharpe'])} | {_fmt(selected_holdout['CAGR'], True)} | {_fmt(selected_holdout['Maximum Drawdown'], True)} | {_fmt(selected_holdout['Annual Turnover'])} | {_fmt(selected_holdout['Exposure'], True)} |

Final conclusion: **{result['final_conclusion']}**.
""", encoding="utf-8")

    (output / "target_diagnostics.md").write_text(f"""# Target diagnostics

The expansion targets were predeclared and use 30-day forward outcomes only as
supervised labels, never as signal-time features.

{_table(result['target_diagnostics'], [('target', 'Target'), ('description', 'Description'), ('split', 'Split'), ('observations', 'Obs'), ('positive_events', 'Events'), ('prevalence', 'Prevalence')], {'prevalence'})}
""", encoding="utf-8")

    (output / "predictive_performance.md").write_text(f"""# Predictive performance

Prediction models were selected on development CPCV only. Holdout metrics are
diagnostic and were not used for model selection.

## Development selection

{_table(result['prediction_selection'], [('config', 'Config'), ('target', 'Target'), ('model', 'Model'), ('selection_score', 'Selection score'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier')], limit=30)}

## All prediction metrics

{_table(result['prediction_metrics'], [('config', 'Config'), ('split', 'Split'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier'), ('true_positive', 'TP'), ('false_positive', 'FP'), ('false_negative', 'FN'), ('true_negative', 'TN')], limit=80)}
""", encoding="utf-8")

    top_importance = result["feature_importance"][result["feature_importance"].config.isin([selected_expansion.config_name, selected_leadership.config_name])]
    (output / "calibration_and_feature_importance.md").write_text(f"""# Calibration and feature importance

SHAP values are not required for this module and are only used if available in a
future extension. The current report uses model coefficients or native feature
importance where available.

## Calibration curve

{_table(result['calibration'], [('config', 'Config'), ('split', 'Split'), ('bin', 'Bin'), ('observations', 'Obs'), ('mean_probability', 'Mean probability'), ('event_rate', 'Event rate')], {'mean_probability', 'event_rate'}, limit=80)}

## Selected model feature importance

{_table(top_importance, [('config', 'Config'), ('feature', 'Feature'), ('importance', 'Importance'), ('method', 'Method')], limit=40)}
""", encoding="utf-8")

    (output / "strategy_overlay_results.md").write_text(f"""# Strategy overlay results

The existing macro risk engine is Layer 1. Expansion-state predictions are only
Layer 2 overlays.

## Overlay selection using development-only CPCV

{_table(result['overlay_selection'], [('candidate', 'Candidate'), ('overlay_type', 'Overlay'), ('selection_score', 'Selection score'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds'), ('development_sharpe', 'Dev Sharpe'), ('development_turnover', 'Dev turnover'), ('development_exposure', 'Dev exposure')], {'positive_fold_fraction', 'development_exposure'}, limit=40)}

## Holdout cost sensitivity for selected overlay

{_table(selected_costs, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Selected overlay decision frequencies in holdout

{_table(result['selected_decision_counts'], [('decision', 'Decision'), ('frequency', 'Frequency')], {'frequency'})}
""", encoding="utf-8")

    holdout_benchmarks = result["benchmarks"][(result["benchmarks"].split == "holdout") & (result["benchmarks"].cost_bps.isin([25, 50]))]
    selected_holdout_rows = result["overlay_metrics"][(result["overlay_metrics"].name == selected) & (result["overlay_metrics"].split == "holdout")]
    comparison = pd.concat([holdout_benchmarks, selected_holdout_rows], ignore_index=True, sort=False)
    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

Benchmarks include the frozen strategy, simple crypto beta, equal-weight top 10,
and prior modules where report artifacts are available.

{_table(comparison, [('name', 'Name'), ('benchmark_group', 'Group'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=80)}
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

## Strategy-level controls

- PBO across overlay configurations: {_fmt(result['strategy_pbo'], True)}
- Deflated Sharpe probability for selected overlay: {_fmt(result['selected_deflated_sharpe_probability'], True)}
- Exposure classification: **{result['exposure_classification']}**
- Minimum exposure rule for replacement: 15% average holdout exposure

## CPCV fold distribution for selected overlay

{_table(result['overlay_folds'][result['overlay_folds'].candidate == selected], [('candidate', 'Candidate'), ('fold', 'Fold'), ('test_groups', 'Test groups'), ('fold_sharpe', 'Fold Sharpe')])}

The holdout period was not used to select prediction models, thresholds, or
overlay candidates.
""", encoding="utf-8")

    replacement_text = (
        "The selected overlay may be paper-monitored as a complement, but not as proven live alpha."
        if result["exposure_classification"] == "replacement_candidate"
        else "The selected overlay should be treated as risk/opportunity diagnostics only because exposure is below the replacement threshold."
    )
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Recommendation

{replacement_text}

## Interpretation

The expansion-state model asks a different question than the frozen macro gate:
the macro gate primarily avoids hostile environments, while the expansion model
tries to identify unusually strong upside regimes. The selected overlay changes
exposure only after the macro gate permits crypto exposure.

Final conclusion: **{result['final_conclusion']}**.

## Guardrails

- Do not replace **{BASELINE_NAME}** based on this study alone.
- Do not claim live alpha.
- Do not promote any candidate that improves Sharpe only by going almost always to cash.
- Continue to paper-monitor if the result remains economically interpretable and statistically stable.
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "tested_configurations": result["tested_configurations"],
        "selected_expansion_model": {
            "config": selected_expansion.config_name,
            "target": selected_expansion.target,
            "model": selected_expansion.model_name,
            "threshold": selected_expansion.threshold,
        },
        "selected_leadership_model": {
            "config": selected_leadership.config_name,
            "target": selected_leadership.target,
            "model": selected_leadership.model_name,
            "threshold": selected_leadership.threshold,
        },
        "selected_overlay": selected,
        "frozen_holdout": _json_safe(frozen),
        "selected_holdout_25bps": _json_safe(selected_holdout.to_dict()),
        "strategy_pbo": _json_safe(result["strategy_pbo"]),
        "selected_deflated_sharpe_probability": _json_safe(result["selected_deflated_sharpe_probability"]),
        "exposure_classification": result["exposure_classification"],
        "final_conclusion": result["final_conclusion"],
        "prediction_metrics": _json_safe(result["prediction_metrics"]),
        "overlay_selection": _json_safe(result["overlay_selection"]),
        "overlay_metrics": _json_safe(result["overlay_metrics"]),
        "benchmarks": _json_safe(result["benchmarks"]),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_expansion_state_model(output_dir: str | Path = "reports/expansion_state_model") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_expansion_state_model(panel, macro, public_data, probability)
    write_expansion_state_reports(output_dir, result)
    return result


__all__ = [
    "TARGET_SPECS",
    "available_model_specs",
    "build_expansion_targets",
    "run_expansion_state_model",
    "write_expansion_state_reports",
    "run_default_expansion_state_model",
]
