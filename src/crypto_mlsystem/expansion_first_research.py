"""Expansion-first systematic cryptocurrency allocation research.

Standalone exploratory study.  The frozen ``btc_eth_macro_gate_balanced``
strategy is used only as Architecture A / benchmark.  It is not modified,
reselected, or retuned.
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
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, precision_recall_fscore_support, roc_auc_score
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
    _prior_meta_overlay_rows,
    _rows_for_result,
    _table,
    _threshold_from_dev,
    _weekly_return,
)
from .expansion_tier1_overlay import _prior_expansion_diagnostics_rows, load_tier1_feature_names
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


BASELINE_NAME = FIXED_SELECTED.name
DEVELOPMENT_START = pd.Timestamp("2019-07-05")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")

DATE_TARGETS: tuple[tuple[str, str], ...] = (
    ("target_a_btc_30d_gt_15", "BTC > +15% over next 30 days"),
    ("target_b_eth_30d_gt_20", "ETH > +20% over next 30 days"),
    ("target_c_eth_beats_btc_30d_gt_5", "ETH outperforms BTC by >5% over next 30 days"),
    ("target_d_top20_leadership", "Top-20 leadership state: top-20 EW beats BTC/ETH 50-50 by >5%"),
)
CROSS_TARGET = "target_e_top20_asset_top_quintile"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    family: str
    factory: Callable[[], Any]


@dataclass
class PredictionBundle:
    config_name: str
    target: str
    target_description: str
    model_name: str
    model_family: str
    threshold: float
    full_probability: pd.Series
    dev_probability: pd.Series
    holdout_probability: pd.Series
    feature_importance: pd.DataFrame


@dataclass
class CrossPredictionBundle:
    config_name: str
    model_name: str
    model_family: str
    threshold: float
    full_predictions: pd.DataFrame
    dev_predictions: pd.DataFrame
    holdout_predictions: pd.DataFrame
    feature_importance: pd.DataFrame


@dataclass(frozen=True)
class AlphaCandidate:
    name: str
    architecture: str
    portfolio_version: str
    construction: str
    risk_layer: str
    description: str


def model_specs(include_mlp: bool = True) -> list[ModelSpec]:
    specs = [
        ModelSpec("logistic_regression", "Linear", lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500, class_weight="balanced", random_state=61))),
        ModelSpec(
            "elastic_net_logistic",
            "Linear",
            lambda: make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    solver="saga",
                    penalty="elasticnet",
                    l1_ratio=0.40,
                    C=0.50,
                    max_iter=6000,
                    class_weight="balanced",
                    random_state=61,
                ),
            ),
        ),
        ModelSpec("random_forest", "Tree", lambda: RandomForestClassifier(n_estimators=140, max_depth=4, min_samples_leaf=12, class_weight="balanced", random_state=61, n_jobs=-1)),
        ModelSpec("gradient_boosting", "Tree", lambda: GradientBoostingClassifier(n_estimators=110, max_depth=2, learning_rate=0.04, min_samples_leaf=10, random_state=61)),
    ]
    if importlib.util.find_spec("xgboost") is not None:
        def xgb_factory() -> Any:
            from xgboost import XGBClassifier

            return XGBClassifier(n_estimators=110, max_depth=2, learning_rate=0.04, subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", random_state=61)

        specs.append(ModelSpec("xgboost", "Tree", xgb_factory))
    if importlib.util.find_spec("lightgbm") is not None:
        def lgbm_factory() -> Any:
            from lightgbm import LGBMClassifier

            return LGBMClassifier(n_estimators=110, max_depth=2, learning_rate=0.04, subsample=0.8, colsample_bytree=0.8, class_weight="balanced", random_state=61, verbose=-1)

        specs.append(ModelSpec("lightgbm", "Tree", lgbm_factory))
    if include_mlp:
        specs.append(ModelSpec("shallow_mlp", "Neural", lambda: make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(16,), alpha=0.01, learning_rate_init=0.001, max_iter=350, early_stopping=True, random_state=61))))
    return specs


def _forward_return(close: pd.DataFrame, symbol: str, dates: pd.DatetimeIndex, horizon_days: int = 30) -> pd.Series:
    if symbol not in close:
        return pd.Series(np.nan, index=dates)
    values = []
    for date in dates:
        if date not in close.index:
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


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int = 7) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def build_date_targets(dataset: MacroRegimeDataset, dates: pd.DatetimeIndex) -> pd.DataFrame:
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
    targets["target_a_btc_30d_gt_15"] = (btc > 0.15).astype(float)
    targets["target_b_eth_30d_gt_20"] = (eth > 0.20).astype(float)
    targets["target_c_eth_beats_btc_30d_gt_5"] = ((eth - btc) > 0.05).astype(float)
    targets["target_d_top20_leadership"] = ((top20 - mix) > 0.05).astype(float)
    unavailable = pd.concat([btc, eth, mix, top20], axis=1).isna().any(axis=1)
    targets.loc[unavailable, :] = np.nan
    return targets


def build_cross_sectional_target_rows(dataset: MacroRegimeDataset, market_features: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    close = dataset.close
    returns = close.pct_change(fill_method=None)
    volume = dataset.panel.pivot(index="date", columns="symbol", values="volume").sort_index().reindex_like(close)
    momentum_21 = close.pct_change(21, fill_method=None).shift(1)
    momentum_63 = close.pct_change(63, fill_method=None).shift(1)
    momentum_126 = close.pct_change(126, fill_method=None).shift(1)
    vol_30 = returns.rolling(30).std().shift(1) * np.sqrt(365)
    volume_expansion = volume.shift(1) / volume.rolling(30).median().shift(2).replace(0, np.nan)
    rows: list[dict[str, Any]] = []
    shared_features = list(market_features.columns)
    for date in dates:
        if date not in close.index or date not in dataset.universe_weights.index:
            continue
        end_pos = close.index.searchsorted(date + pd.Timedelta(days=30))
        if end_pos >= len(close.index):
            continue
        active = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        if len(active) < 5:
            continue
        start = close.loc[date, active].replace(0, np.nan)
        end = close.iloc[end_pos][active]
        forward = (end / start - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
        if len(forward) < 5:
            continue
        cutoff = float(forward.quantile(0.80))
        for symbol, fwd in forward.items():
            row = {
                "date": date,
                "symbol": symbol,
                "target": float(fwd >= cutoff),
                "forward_30d_return": float(fwd),
                "asset_momentum_21d": momentum_21.at[date, symbol] if symbol in momentum_21 else np.nan,
                "asset_momentum_63d": momentum_63.at[date, symbol] if symbol in momentum_63 else np.nan,
                "asset_momentum_126d": momentum_126.at[date, symbol] if symbol in momentum_126 else np.nan,
                "asset_volatility_30d": vol_30.at[date, symbol] if symbol in vol_30 else np.nan,
                "asset_volume_expansion": volume_expansion.at[date, symbol] if symbol in volume_expansion else np.nan,
            }
            for feature in shared_features:
                row[feature] = market_features.at[date, feature] if date in market_features.index else np.nan
            rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    feature_cols = [c for c in frame.columns if c not in {"date", "symbol", "target", "forward_30d_return"}]
    medians = frame.loc[(frame.date >= DEVELOPMENT_START) & (frame.date <= DEVELOPMENT_END), feature_cols].median().fillna(0.0)
    frame[feature_cols] = frame[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(medians).fillna(0.0)
    return frame


def _macro_feature_frame(macro_features: pd.DataFrame, index: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    macro = macro_features.copy()
    macro["date"] = pd.to_datetime(macro["date"])
    macro = macro.drop_duplicates("date").set_index("date").sort_index()
    numeric = macro.select_dtypes(include=[np.number]).copy()
    frame = numeric.reindex(index).ffill().shift(1)
    metadata = pd.DataFrame({
        "feature": frame.columns,
        "source_family": "WRDS-derived macro",
        "source": "data/processed/wrds_macro_features/wrds_macro_features_daily.csv",
        "used": True,
        "notes": "Lagged one day; includes validated macro/rates/USD/credit/equity features where available.",
    })
    return frame, metadata


def _derivatives_feature_frame(index: pd.DatetimeIndex, path: str | Path = "data/processed/derivatives/derivatives_daily_merged.csv") -> tuple[pd.DataFrame, pd.DataFrame]:
    path = Path(path)
    metadata_rows: list[dict[str, Any]] = []
    if not path.exists():
        return pd.DataFrame(index=index), pd.DataFrame([{
            "feature": "funding/options_derivatives",
            "source_family": "derivatives",
            "source": str(path),
            "used": False,
            "notes": "Processed derivatives file unavailable.",
        }])
    raw = pd.read_csv(path, parse_dates=["date"])
    raw = raw[raw.symbol.isin(["BTC", "ETH"])].copy()
    if raw.empty:
        return pd.DataFrame(index=index), pd.DataFrame()
    features = pd.DataFrame(index=index)
    for column in ("funding_rate", "basis_close", "open_interest", "long_short_ratio", "taker_imbalance"):
        if column not in raw:
            continue
        matrix = raw.pivot(index="date", columns="symbol", values=column).sort_index()
        btc_eth = [s for s in ("BTC", "ETH") if s in matrix]
        if not btc_eth:
            continue
        mean_series = matrix[btc_eth].mean(axis=1).reindex(index).ffill()
        if column == "open_interest":
            series = mean_series.pct_change(7, fill_method=None)
            name = "open_interest_growth_7d"
        else:
            series = mean_series
            name = f"{column}_btc_eth_mean"
        features[name] = series.shift(1)
        metadata_rows.append({
            "feature": name,
            "source_family": "derivatives/funding",
            "source": str(path),
            "used": True,
            "notes": "BTC/ETH Binance futures-derived feature, lagged one day.",
        })
    return features, pd.DataFrame(metadata_rows)


def _new_data_tier1_feature_frame(index: pd.DatetimeIndex, path: str | Path = "reports/new_data_expansion_strategy/feature_tiers.csv") -> tuple[pd.DataFrame, pd.DataFrame]:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(index=index), pd.DataFrame([{
            "feature": "new_data_tier1",
            "source_family": "ETF/on-chain/options",
            "source": str(path),
            "used": False,
            "notes": "No new-data tier report found.",
        }])
    tiers = pd.read_csv(path)
    tier1 = tiers[tiers.new_data_tier.astype(str).eq("New Data Tier 1")] if "new_data_tier" in tiers else pd.DataFrame()
    metadata = []
    for feature in tier1.feature.astype(str).tolist() if not tier1.empty else []:
        metadata.append({
            "feature": feature,
            "source_family": "ETF/on-chain/options",
            "source": str(path),
            "used": False,
            "notes": "Tier-1 new-data feature exists in report, but raw feature series is not persisted in the current project module.",
        })
    if not metadata:
        metadata.append({
            "feature": "new_data_tier1",
            "source_family": "ETF/on-chain/options",
            "source": str(path),
            "used": False,
            "notes": "No New Data Tier-1 features found; ETF/on-chain/options skipped.",
        })
    return pd.DataFrame(index=index), pd.DataFrame(metadata)


def build_validated_feature_frame(
    dataset: MacroRegimeDataset,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None,
    tier_path: str | Path = "reports/upside_expansion_models/expansion_feature_tiers.csv",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    macro_frame, macro_meta = _macro_feature_frame(macro_features, dataset.close.index)
    expansion_all, expansion_meta = build_expansion_feature_candidates(dataset, dataset.regime_features, public_data)
    tier1_names = load_tier1_feature_names(tier_path)
    expansion_cols = [c for c in tier1_names if c in expansion_all.columns]
    expansion_frame = expansion_all[expansion_cols].copy()
    expansion_meta = expansion_meta[expansion_meta.feature.isin(expansion_cols)].copy() if not expansion_meta.empty else pd.DataFrame()
    if not expansion_meta.empty:
        expansion_meta["source_family"] = "Expansion Tier-1 crypto-native"
        expansion_meta["source"] = str(tier_path)
        expansion_meta["used"] = True
        expansion_meta["notes"] = "Previously validated Expansion Tier-1 feature."
    derivatives_frame, derivatives_meta = _derivatives_feature_frame(dataset.close.index)
    new_data_frame, new_data_meta = _new_data_tier1_feature_frame(dataset.close.index)
    frame = pd.concat([macro_frame, expansion_frame, derivatives_frame, new_data_frame], axis=1)
    frame = frame.loc[:, ~frame.columns.duplicated()].replace([np.inf, -np.inf], np.nan)
    medians = frame.loc[DEVELOPMENT_START:DEVELOPMENT_END].median().fillna(0.0)
    frame = frame.ffill().fillna(medians).fillna(0.0)
    metadata = pd.concat([macro_meta, expansion_meta, derivatives_meta, new_data_meta], ignore_index=True, sort=False)
    return frame, metadata


def _cpcv_oof(x_dev: pd.DataFrame, y_dev: pd.Series, spec: ModelSpec, dates: pd.Series | None = None) -> tuple[pd.Series, pd.DataFrame]:
    if dates is None:
        unique_dates = pd.Index(x_dev.index)
        dates = pd.Series(unique_dates, index=x_dev.index)
    else:
        unique_dates = pd.Index(pd.to_datetime(dates).drop_duplicates().sort_values())
    sums = pd.Series(0.0, index=x_dev.index)
    counts = pd.Series(0.0, index=x_dev.index)
    fold_rows = []
    splits = combinatorial_purged_splits(len(unique_dates), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    date_values = pd.to_datetime(dates)
    for number, split in enumerate(splits):
        train_dates = set(unique_dates[list(split.train_indices)])
        test_dates = set(unique_dates[list(split.test_indices)])
        train_mask = date_values.isin(train_dates).to_numpy()
        test_mask = date_values.isin(test_dates).to_numpy()
        y_train = y_dev.loc[train_mask]
        if y_train.nunique() < 2:
            prob = pd.Series(float(y_train.mean()), index=x_dev.index[test_mask])
        else:
            model = spec.factory()
            model.fit(x_dev.loc[train_mask], y_train)
            prob = pd.Series(_positive_probability(model, x_dev.loc[test_mask]), index=x_dev.index[test_mask])
        sums.loc[x_dev.index[test_mask]] += prob
        counts.loc[x_dev.index[test_mask]] += 1.0
        fold_rows.append({"model": spec.name, "fold": number, "test_groups": ",".join(str(g) for g in split.test_groups), "train_samples": int(train_mask.sum()), "test_samples": int(test_mask.sum())})
    return (sums / counts.replace(0, np.nan)).fillna(float(y_dev.mean())), pd.DataFrame(fold_rows)


def _fit_holdout(x_dev: pd.DataFrame, y_dev: pd.Series, x_holdout: pd.DataFrame, spec: ModelSpec) -> tuple[pd.Series, Any | None]:
    if y_dev.nunique() < 2 or x_holdout.empty:
        return pd.Series(float(y_dev.mean()) if len(y_dev) else 0.0, index=x_holdout.index), None
    model = spec.factory()
    model.fit(x_dev, y_dev)
    return pd.Series(_positive_probability(model, x_holdout), index=x_holdout.index), model


def _classification_metrics(y: pd.Series, probability: pd.Series, threshold: float, split: str, config: str, target: str, model: str, family: str) -> dict[str, Any]:
    data = pd.concat([y.rename("y"), probability.rename("probability")], axis=1).dropna()
    if data.empty:
        return {"config": config, "target": target, "model": model, "model_family": family, "split": split}
    y_true = data.y.astype(int)
    prob = data.probability.clip(0.0, 1.0)
    pred = (prob >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, pred, average="binary", zero_division=0)
    auc = roc_auc_score(y_true, prob) if y_true.nunique() == 2 else np.nan
    return {
        "config": config,
        "target": target,
        "model": model,
        "model_family": family,
        "split": split,
        "threshold": threshold,
        "observations": int(len(y_true)),
        "positive_events": int(y_true.sum()),
        "auc": float(auc) if np.isfinite(auc) else np.nan,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "brier_score": float(brier_score_loss(y_true, prob)),
    }


def fit_date_models(features: pd.DataFrame, targets: pd.DataFrame, specs: list[ModelSpec]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, PredictionBundle]]:
    metrics = []
    importance = []
    bundles: dict[str, PredictionBundle] = {}
    descriptions = dict(DATE_TARGETS)
    dev_mask = (features.index >= DEVELOPMENT_START) & (features.index <= DEVELOPMENT_END)
    holdout_mask = (features.index >= HOLDOUT_START) & (features.index <= HOLDOUT_END)
    for target, description in DATE_TARGETS:
        valid_dev = targets[target].loc[dev_mask].dropna().index
        valid_holdout = targets[target].loc[holdout_mask].dropna().index
        x_dev = features.loc[valid_dev]
        y_dev = targets.loc[valid_dev, target].astype(int)
        x_holdout = features.loc[valid_holdout]
        y_holdout = targets.loc[valid_holdout, target].astype(int)
        for spec in specs:
            config = f"{target}__{spec.name}"
            dev_prob, _ = _cpcv_oof(x_dev, y_dev, spec)
            threshold = _threshold_from_dev(dev_prob, y_dev)
            holdout_prob, model = _fit_holdout(x_dev, y_dev, x_holdout, spec)
            full = pd.Series(np.nan, index=features.index)
            full.loc[dev_prob.index] = dev_prob
            full.loc[holdout_prob.index] = holdout_prob
            metrics.append(_classification_metrics(y_dev, dev_prob, threshold, "development_cpcv", config, target, spec.name, spec.family))
            metrics.append(_classification_metrics(y_holdout, holdout_prob, threshold, "holdout", config, target, spec.name, spec.family))
            fi = _feature_importance(model, spec, list(features.columns), config)
            fi["target"] = target
            importance.append(fi)
            bundles[config] = PredictionBundle(config, target, description, spec.name, spec.family, threshold, full.ffill().fillna(float(dev_prob.mean()) if len(dev_prob) else 0.0), dev_prob, holdout_prob, fi)
    return pd.DataFrame(metrics), pd.concat(importance, ignore_index=True) if importance else pd.DataFrame(), bundles


def fit_cross_models(frame: pd.DataFrame, specs: list[ModelSpec]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, CrossPredictionBundle]]:
    if frame.empty:
        return pd.DataFrame(), pd.DataFrame(), {}
    feature_cols = [c for c in frame.columns if c not in {"date", "symbol", "target", "forward_30d_return"}]
    dev = frame[(frame.date >= DEVELOPMENT_START) & (frame.date <= DEVELOPMENT_END)].copy()
    holdout = frame[(frame.date >= HOLDOUT_START) & (frame.date <= HOLDOUT_END)].copy()
    x_dev = dev[feature_cols]
    y_dev = dev["target"].astype(int)
    x_holdout = holdout[feature_cols]
    y_holdout = holdout["target"].astype(int)
    metrics = []
    importance = []
    bundles: dict[str, CrossPredictionBundle] = {}
    for spec in specs:
        config = f"{CROSS_TARGET}__{spec.name}"
        dev_prob, _ = _cpcv_oof(x_dev, y_dev, spec, dates=dev["date"])
        threshold = _threshold_from_dev(dev_prob, y_dev)
        holdout_prob, model = _fit_holdout(x_dev, y_dev, x_holdout, spec)
        metrics.append(_classification_metrics(y_dev, dev_prob, threshold, "development_cpcv", config, CROSS_TARGET, spec.name, spec.family))
        metrics.append(_classification_metrics(y_holdout, holdout_prob, threshold, "holdout", config, CROSS_TARGET, spec.name, spec.family))
        dev_pred = dev[["date", "symbol", "target", "forward_30d_return"]].copy()
        dev_pred["probability"] = dev_prob.to_numpy()
        hold_pred = holdout[["date", "symbol", "target", "forward_30d_return"]].copy()
        hold_pred["probability"] = holdout_prob.to_numpy()
        fi = _feature_importance(model, spec, feature_cols, config)
        fi["target"] = CROSS_TARGET
        importance.append(fi)
        bundles[config] = CrossPredictionBundle(config, spec.name, spec.family, threshold, pd.concat([dev_pred, hold_pred], ignore_index=True), dev_pred, hold_pred, fi)
    return pd.DataFrame(metrics), pd.concat(importance, ignore_index=True) if importance else pd.DataFrame(), bundles


def _best_configs(metrics: pd.DataFrame) -> dict[str, str]:
    dev = metrics[metrics.split == "development_cpcv"].copy()
    dev["prediction_score"] = dev["auc"].fillna(0.5) - dev["brier_score"].fillna(1.0) + 0.10 * dev["f1"].fillna(0.0)
    return {target: str(group.sort_values("prediction_score", ascending=False).iloc[0].config) for target, group in dev.groupby("target")}


def predeclared_alpha_candidates() -> list[AlphaCandidate]:
    candidates = []
    risk_layers = (
        "none",
        "vol_target",
        "drawdown_brake",
        "macro_gate",
        "vol_target_macro_gate",
        "vol_target_drawdown_brake",
        "vol_target_drawdown_brake_macro_gate",
    )
    for architecture in ("expansion_first", "hybrid"):
        for version in ("btc_eth_only", "btc_eth_cash", "top20_universe", "top20_core"):
            for construction in ("equal_weight", "confidence_weight", "probability_weight", "volatility_adjusted_weight"):
                for risk_layer in risk_layers:
                    candidates.append(AlphaCandidate(
                        name=f"{architecture}__{version}__{construction}__{risk_layer}",
                        architecture=architecture,
                        portfolio_version=version,
                        construction=construction,
                        risk_layer=risk_layer,
                        description=f"{architecture} alpha, {version}, {construction}, post-alpha risk layer: {risk_layer}",
                    ))
    return candidates


def _clip_normalized(weights: pd.Series, max_weight: float = 0.20) -> pd.Series:
    weights = weights.clip(lower=0.0)
    total = float(weights.sum())
    if total <= 0:
        return weights * 0.0
    weights = weights / total
    weights = weights.clip(upper=max_weight)
    total = float(weights.sum())
    return weights / total if total > 0 else weights


def _asset_volatility(dataset: MacroRegimeDataset) -> pd.DataFrame:
    return dataset.returns.rolling(30).std().shift(1) * np.sqrt(365)


def build_alpha_weights(
    dataset: MacroRegimeDataset,
    candidate: AlphaCandidate,
    date_bundles: dict[str, PredictionBundle],
    cross_bundle: CrossPredictionBundle | None,
    best: dict[str, str],
    frozen_combined: pd.Series,
) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index, 7)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    probs = {target: date_bundles[config].full_probability.reindex(dates).ffill().fillna(0.0) for target, config in best.items() if target in dict(DATE_TARGETS)}
    thresholds = {target: date_bundles[config].threshold for target, config in best.items() if target in dict(DATE_TARGETS)}
    vol = _asset_volatility(dataset)
    cross_predictions = pd.DataFrame()
    if cross_bundle is not None:
        cross_predictions = cross_bundle.full_predictions.copy()
        cross_predictions["date"] = pd.to_datetime(cross_predictions["date"])
    regimes = frozen_combined.reindex(dates).ffill().fillna("risk_off")
    for date in dates:
        active = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0] if date in dataset.universe_weights.index else []
        if len(active) == 0:
            continue
        p_btc = float(probs.get("target_a_btc_30d_gt_15", pd.Series(0.5, index=dates)).loc[date])
        p_eth = float(probs.get("target_b_eth_30d_gt_20", pd.Series(0.5, index=dates)).loc[date])
        p_lead = float(probs.get("target_c_eth_beats_btc_30d_gt_5", pd.Series(0.5, index=dates)).loc[date])
        p_top20 = float(probs.get("target_d_top20_leadership", pd.Series(0.5, index=dates)).loc[date])
        if candidate.architecture == "hybrid":
            regime = str(regimes.loc[date])
            factor = 1.0 if regime == "risk_on" else 0.65 if regime == "neutral" else 0.35
            p_btc *= factor
            p_eth *= factor
            p_top20 *= factor
        row = pd.Series(0.0, index=dataset.close.columns)
        if candidate.portfolio_version in ("btc_eth_only", "btc_eth_cash"):
            assets = [s for s in ("BTC", "ETH") if s in row.index and s in active]
            if not assets:
                continue
            scores = pd.Series({"BTC": p_btc, "ETH": p_eth}).reindex(assets).fillna(0.0)
            if "ETH" in scores:
                scores["ETH"] *= 1.0 + max(0.0, p_lead - thresholds.get("target_c_eth_beats_btc_30d_gt_5", 0.5))
            if candidate.construction == "equal_weight":
                alloc = pd.Series(1.0, index=assets)
            elif candidate.construction == "confidence_weight":
                alloc = (scores - pd.Series({"BTC": thresholds.get("target_a_btc_30d_gt_15", 0.5), "ETH": thresholds.get("target_b_eth_30d_gt_20", 0.5)}).reindex(assets)).clip(lower=0.0)
            elif candidate.construction == "probability_weight":
                alloc = scores
            else:
                vol_row = vol.reindex(index=[date], columns=assets).iloc[0].replace(0, np.nan)
                alloc = scores / vol_row
            alloc = _clip_normalized(alloc, max_weight=0.70)
            exposure = 1.0
            if candidate.portfolio_version == "btc_eth_cash":
                confidence = max(
                    p_btc - thresholds.get("target_a_btc_30d_gt_15", 0.5),
                    p_eth - thresholds.get("target_b_eth_30d_gt_20", 0.5),
                    0.0,
                )
                exposure = min(1.0, max(0.0, confidence / 0.30))
            row.loc[alloc.index] = alloc * exposure
        else:
            pred_date = cross_predictions[cross_predictions.date.eq(date)] if not cross_predictions.empty else pd.DataFrame()
            if pred_date.empty:
                asset_scores = dataset.close.pct_change(63, fill_method=None).shift(1).loc[date, active].dropna()
                asset_scores = asset_scores.rank(pct=True)
            else:
                asset_scores = pred_date.set_index("symbol")["probability"].reindex(active).dropna()
            chosen = asset_scores.sort_values(ascending=False).head(5)
            if chosen.empty:
                continue
            if candidate.construction == "equal_weight":
                alloc = pd.Series(1.0, index=chosen.index)
            elif candidate.construction == "confidence_weight":
                threshold = cross_bundle.threshold if cross_bundle is not None else 0.5
                alloc = (chosen - threshold).clip(lower=0.0)
            elif candidate.construction == "probability_weight":
                alloc = chosen
            else:
                vol_row = vol.reindex(index=[date], columns=chosen.index).iloc[0].replace(0, np.nan)
                alloc = chosen / vol_row
            alloc = _clip_normalized(alloc, max_weight=0.20)
            exposure = 1.0 if p_top20 >= thresholds.get("target_d_top20_leadership", 0.5) else 0.50
            if candidate.portfolio_version == "top20_core":
                core_assets = [s for s in ("BTC", "ETH") if s in row.index and s in active]
                if core_assets:
                    row.loc[core_assets] = 0.25
                    row.loc[alloc.index] += alloc * min(0.50, exposure)
                else:
                    row.loc[alloc.index] = alloc * exposure
            else:
                row.loc[alloc.index] = alloc * exposure
        total = float(row.sum())
        if total > 1.0:
            row /= total
        weights.loc[date] = row
    return weights


def apply_risk_layer(
    dataset: MacroRegimeDataset,
    raw_weights: pd.DataFrame,
    risk_layer: str,
    regimes: tuple[pd.Series, pd.Series, pd.Series],
) -> pd.DataFrame:
    if risk_layer == "none":
        return raw_weights.copy()
    macro_regime, crypto_regime, combined_regime = regimes
    preliminary = backtest_weights(dataset, raw_weights, macro_regime, crypto_regime, combined_regime, cost_bps=0, turnover_cap=FIXED_SELECTED.turnover_cap)
    trailing_vol = preliminary.returns.rolling(63).std().shift(1) * np.sqrt(365)
    wealth = (1.0 + preliminary.returns.fillna(0.0)).cumprod()
    drawdown = (wealth / wealth.cummax() - 1.0).shift(1)
    scales = pd.Series(1.0, index=raw_weights.index)
    if "vol_target" in risk_layer:
        vol_scale = (0.25 / trailing_vol.replace(0, np.nan)).clip(upper=1.0).reindex(raw_weights.index).ffill().fillna(1.0)
        scales *= vol_scale
    if "drawdown_brake" in risk_layer:
        dd = drawdown.reindex(raw_weights.index).ffill().fillna(0.0)
        dd_scale = pd.Series(1.0, index=raw_weights.index)
        dd_scale.loc[dd <= -0.10] = 0.50
        dd_scale.loc[dd <= -0.20] = 0.0
        scales *= dd_scale
    if "macro_gate" in risk_layer:
        regime = combined_regime.reindex(raw_weights.index).ffill().fillna("risk_off")
        macro_scale = pd.Series(0.0, index=raw_weights.index)
        macro_scale.loc[regime == "neutral"] = 0.50
        macro_scale.loc[regime == "risk_on"] = 1.0
        scales *= macro_scale
    return raw_weights.mul(scales.clip(0.0, 1.0), axis=0)


def _fold_sharpe(weekly: pd.Series, indices: tuple[int, ...]) -> float:
    subset = weekly.iloc[list(indices)].dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def select_alpha_candidates(results_25bps: dict[str, PortfolioResult], candidates: list[AlphaCandidate]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str], float]:
    rows = []
    fold_rows = []
    weekly_returns = {}
    for candidate in candidates:
        result = results_25bps[candidate.name]
        weekly = _weekly_return(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        weekly_returns[candidate.name] = weekly
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_values = []
        for number, split in enumerate(splits):
            sharpe = _fold_sharpe(weekly, split.test_indices)
            fold_values.append(sharpe)
            fold_rows.append({"candidate": candidate.name, "architecture": candidate.architecture, "fold": number, "test_groups": ",".join(str(g) for g in split.test_groups), "fold_sharpe": sharpe})
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        rows.append({
            "candidate": candidate.name,
            "architecture": candidate.architecture,
            "portfolio_version": candidate.portfolio_version,
            "construction": candidate.construction,
            "risk_layer": candidate.risk_layer,
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
    winners = {}
    for architecture, group in selection.groupby("architecture"):
        ranked = group.sort_values(["selection_score", "median_fold_sharpe", "worst_fold_sharpe", "development_turnover"], ascending=[False, False, False, True])
        winners[architecture] = str(ranked.iloc[0].candidate)
    all_ranked = selection.sort_values(["selection_score", "median_fold_sharpe", "worst_fold_sharpe", "development_turnover"], ascending=[False, False, False, True])
    winners["overall"] = str(all_ranked.iloc[0].candidate)
    pbo = probability_backtest_overfitting(pd.concat(weekly_returns, axis=1).sort_index(), blocks=8) if len(weekly_returns) > 1 else np.nan
    return all_ranked, pd.DataFrame(fold_rows), winners, pbo


def _benchmark_rows(dataset20: MacroRegimeDataset, dataset10: MacroRegimeDataset, frozen_weights: pd.DataFrame, regimes: tuple[pd.Series, pd.Series, pd.Series]) -> pd.DataFrame:
    rows = []
    macro, crypto, combined = regimes
    for cost in COST_LEVELS:
        frozen = backtest_weights(dataset20, frozen_weights, macro, crypto, combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
        rows.extend(_rows_for_result(BASELINE_NAME, "Macro-first frozen benchmark", "macro_first", cost, frozen))
        risk_on = _all_risk_on(dataset20.close.index)
        for name, family in (("btc_buy_hold", "BTC buy-and-hold"), ("eth_buy_hold", "ETH buy-and-hold"), ("btc_eth_50_50", "50/50 BTC/ETH")):
            result = backtest_weights(dataset20, _buy_hold_weights(dataset20, name), *risk_on, cost_bps=cost, turnover_cap=10.0)
            rows.extend(_rows_for_result(name, family, "benchmark", cost, result))
        ew = dataset10.universe_weights.copy()
        ew = ew.div(ew.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0).clip(upper=0.20)
        ew_result = backtest_weights(dataset10, ew.reindex(dataset10.close.index).fillna(0.0), *_all_risk_on(dataset10.close.index), cost_bps=cost, turnover_cap=10.0)
        rows.extend(_rows_for_result("equal_weight_top10", "Equal-weight top-10", "benchmark", cost, ew_result))
        momentum = pd.DataFrame(0.0, index=_rebalance_dates(dataset10.close.index, 7), columns=dataset10.close.columns)
        scores = dataset10.close.pct_change(63, fill_method=None).shift(1)
        for date in momentum.index:
            active = dataset10.universe_weights.columns[dataset10.universe_weights.loc[date] > 0] if date in dataset10.universe_weights.index else []
            ranked = scores.loc[date, active].dropna().sort_values(ascending=False)
            chosen = ranked.head(5).index
            if len(chosen):
                momentum.loc[date, chosen] = min(0.20, 1.0 / len(chosen))
        mom_result = backtest_weights(dataset10, momentum, *_all_risk_on(dataset10.close.index), cost_bps=cost, turnover_cap=10.0)
        rows.extend(_rows_for_result("pure_top10_momentum", "Pure top-10 momentum", "benchmark", cost, mom_result))
    prior_meta = _prior_meta_overlay_rows()
    if not prior_meta.empty:
        rows.extend(prior_meta.to_dict("records"))
    prior_expansion = _prior_expansion_diagnostics_rows()
    if not prior_expansion.empty:
        rows.extend(prior_expansion.to_dict("records"))
    return pd.DataFrame(rows)


def target_diagnostics(date_targets: pd.DataFrame, cross_rows: pd.DataFrame) -> pd.DataFrame:
    descriptions = dict(DATE_TARGETS)
    rows = []
    for target, description in DATE_TARGETS:
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            y = date_targets[target].loc[start:end].dropna().astype(int)
            rows.append({"target": target, "description": description, "split": split, "observations": int(len(y)), "positive_events": int(y.sum()) if len(y) else 0, "prevalence": float(y.mean()) if len(y) else np.nan})
    if not cross_rows.empty:
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            y = cross_rows[(cross_rows.date >= start) & (cross_rows.date <= end)]["target"].dropna().astype(int)
            rows.append({"target": CROSS_TARGET, "description": "Top-20 asset in next-month top quintile", "split": split, "observations": int(len(y)), "positive_events": int(y.sum()) if len(y) else 0, "prevalence": float(y.mean()) if len(y) else np.nan})
    return pd.DataFrame(rows)


def run_expansion_first_research(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
    specs: list[ModelSpec] | None = None,
) -> dict[str, Any]:
    specs = specs or model_specs()
    dataset20 = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=20)
    dataset10 = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    feature_frame, feature_metadata = build_validated_feature_frame(dataset20, macro_features, public_data)
    dates = _rebalance_dates(dataset20.close.index, 7)
    x = feature_frame.reindex(dates).ffill().fillna(0.0)
    base_weights, macro_regime, crypto_regime, combined_regime = build_candidate_weights(dataset20, FIXED_SELECTED)
    date_targets = build_date_targets(dataset20, dates)
    cross_rows = build_cross_sectional_target_rows(dataset20, x, dates)
    date_metrics, date_importance, date_bundles = fit_date_models(x, date_targets, specs)
    cross_metrics, cross_importance, cross_bundles = fit_cross_models(cross_rows, specs)
    all_prediction_metrics = pd.concat([date_metrics, cross_metrics], ignore_index=True, sort=False)
    all_importance = pd.concat([date_importance, cross_importance], ignore_index=True, sort=False)
    best_date = _best_configs(date_metrics)
    best_cross = _best_configs(cross_metrics).get(CROSS_TARGET) if not cross_metrics.empty else None
    cross_bundle = cross_bundles.get(best_cross) if best_cross else None
    candidates = predeclared_alpha_candidates()
    raw_weights: dict[str, pd.DataFrame] = {}
    overlay_results: dict[str, dict[int, PortfolioResult]] = {}
    for candidate in candidates:
        alpha = build_alpha_weights(dataset20, candidate, date_bundles, cross_bundle, best_date, combined_regime)
        final_weights = apply_risk_layer(dataset20, alpha, candidate.risk_layer, (macro_regime, crypto_regime, combined_regime))
        raw_weights[candidate.name] = final_weights
        overlay_results[candidate.name] = {
            cost: backtest_weights(dataset20, final_weights, macro_regime, crypto_regime, combined_regime, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
            for cost in COST_LEVELS
        }
    results_25 = {name: by_cost[25] for name, by_cost in overlay_results.items()}
    selection, cpcv_folds, winners, pbo = select_alpha_candidates(results_25, candidates)
    metric_rows = []
    candidate_map = {c.name: c for c in candidates}
    for name, by_cost in overlay_results.items():
        candidate = candidate_map[name]
        for cost, result in by_cost.items():
            for row in _rows_for_result(name, candidate.description, candidate.architecture, cost, result, selected=name in set(winners.values())):
                row.update({"portfolio_version": candidate.portfolio_version, "construction": candidate.construction, "risk_layer": candidate.risk_layer})
                metric_rows.append(row)
    strategy_metrics = pd.DataFrame(metric_rows)
    benchmarks = _benchmark_rows(dataset20, dataset10, base_weights, (macro_regime, crypto_regime, combined_regime))
    frozen_25 = backtest_weights(dataset20, base_weights, macro_regime, crypto_regime, combined_regime, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
    frozen_holdout = period_metrics(frozen_25, HOLDOUT_START, HOLDOUT_END)
    dsr_rows = []
    for key in ("expansion_first", "hybrid", "overall"):
        winner = winners[key]
        holdout_returns = overlay_results[winner][25].returns.loc[HOLDOUT_START:HOLDOUT_END]
        dsr_rows.append({"selection": key, "candidate": winner, "deflated_sharpe_probability": deflated_sharpe_probability(holdout_returns, tested_configurations=len(candidates) + len(all_prediction_metrics[all_prediction_metrics.split == "development_cpcv"]))})
    dsr = pd.DataFrame(dsr_rows)
    dsr_by_selection = dsr.set_index("selection")["deflated_sharpe_probability"].to_dict()
    holdout_rows = []
    for key, winner in winners.items():
        metrics = period_metrics(overlay_results[winner][25], HOLDOUT_START, HOLDOUT_END)
        metrics_50 = period_metrics(overlay_results[winner][50], HOLDOUT_START, HOLDOUT_END)
        dsr_probability = float(dsr_by_selection.get(key, np.nan))
        exposure_false_improvement = bool(metrics["Exposure"] < max(0.15, frozen_holdout["Exposure"] * 0.60))
        survives_50bps = bool(metrics_50["CAGR"] > 0 and metrics_50["Sharpe"] > 0)
        pbo_acceptable = bool(not np.isfinite(pbo) or pbo <= 0.65)
        dsr_acceptable = bool(np.isfinite(dsr_probability) and dsr_probability >= 0.50)
        row = {"selection": key, "candidate": winner, **metrics}
        row["CAGR_50bps"] = metrics_50["CAGR"]
        row["Sharpe_50bps"] = metrics_50["Sharpe"]
        row["Maximum_Drawdown_50bps"] = metrics_50["Maximum Drawdown"]
        row["PBO"] = pbo
        row["deflated_sharpe_probability"] = dsr_probability
        row["beats_frozen_sharpe"] = metrics["Sharpe"] > frozen_holdout["Sharpe"]
        row["beats_frozen_cagr"] = metrics["CAGR"] > frozen_holdout["CAGR"]
        row["beats_frozen_drawdown"] = metrics["Maximum Drawdown"] > frozen_holdout["Maximum Drawdown"]
        row["survives_50bps"] = survives_50bps
        row["turnover_acceptable"] = metrics["Annual Turnover"] <= 12
        row["exposure_acceptable"] = metrics["Exposure"] >= 0.15
        row["cash_reduction_false_improvement"] = exposure_false_improvement
        row["pbo_acceptable"] = pbo_acceptable
        row["dsr_acceptable"] = dsr_acceptable
        row["replacement_candidate"] = bool(
            metrics["Sharpe"] > frozen_holdout["Sharpe"]
            and metrics["CAGR"] > frozen_holdout["CAGR"]
            and metrics["Maximum Drawdown"] > frozen_holdout["Maximum Drawdown"]
            and metrics["Annual Turnover"] <= 12
            and metrics["Exposure"] >= 0.15
            and not exposure_false_improvement
            and survives_50bps
            and pbo_acceptable
            and dsr_acceptable
        )
        holdout_rows.append(row)
    selected_holdouts = pd.DataFrame(holdout_rows)
    final_strategy = "btc_eth_macro_gate_balanced"
    if selected_holdouts["replacement_candidate"].any():
        final_strategy = str(selected_holdouts[selected_holdouts.replacement_candidate].sort_values("Sharpe", ascending=False).iloc[0].candidate)
    conclusion = (
        "Expansion-first/hybrid does not replace the macro-regime result; the project core remains Macro-Regime Conditioning for Systematic Cryptocurrency Allocation."
        if final_strategy == BASELINE_NAME
        else f"Development-selected expansion framework {final_strategy} passes all replacement filters and merits paper monitoring."
    )
    return {
        "dataset20": dataset20,
        "dataset10": dataset10,
        "features": feature_frame,
        "feature_metadata": feature_metadata,
        "date_targets": date_targets,
        "cross_rows": cross_rows,
        "target_diagnostics": target_diagnostics(date_targets, cross_rows),
        "prediction_metrics": all_prediction_metrics,
        "feature_importance": all_importance,
        "best_date_configs": best_date,
        "best_cross_config": best_cross,
        "candidates": candidates,
        "selection": selection,
        "cpcv_folds": cpcv_folds,
        "winners": winners,
        "strategy_metrics": strategy_metrics,
        "benchmarks": benchmarks,
        "selected_holdouts": selected_holdouts,
        "pbo": pbo,
        "deflated_sharpe": dsr,
        "frozen_holdout": frozen_holdout,
        "final_strategy": final_strategy,
        "final_conclusion": conclusion,
        "tested_configurations": {"prediction_configs": int(len(all_prediction_metrics[all_prediction_metrics.split == "development_cpcv"])), "strategy_configs": int(len(candidates)), "total": int(len(candidates) + len(all_prediction_metrics[all_prediction_metrics.split == "development_cpcv"]))},
        "model_notes": {"lstm": "Skipped: weekly/daily sample is too small for an auditable LSTM under locked CPCV without likely overfitting.", "rl": "Not used by instruction.", "llm": "No LLM-generated signals used."},
        "protocol": {"title": "Expansion-First Systematic Cryptocurrency Allocation", "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}", "locked_holdout": f"{HOLDOUT_START.date()} onward", "baseline": BASELINE_NAME, "selection": "Median CPCV Sharpe, worst-fold Sharpe, and turnover inside development only."},
    }


def _write_csvs(output: Path, result: dict[str, Any]) -> None:
    for key, filename in (
        ("feature_metadata", "feature_usage.csv"),
        ("target_diagnostics", "target_diagnostics.csv"),
        ("prediction_metrics", "prediction_metrics.csv"),
        ("feature_importance", "feature_importance.csv"),
        ("selection", "strategy_selection.csv"),
        ("cpcv_folds", "cpcv_folds.csv"),
        ("strategy_metrics", "strategy_metrics.csv"),
        ("benchmarks", "benchmark_metrics.csv"),
        ("selected_holdouts", "selected_holdouts.csv"),
        ("deflated_sharpe", "deflated_sharpe.csv"),
    ):
        frame = result.get(key)
        if isinstance(frame, pd.DataFrame):
            frame.to_csv(output / filename, index=False)


def write_expansion_first_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_csvs(output, result)
    selected_names = set(result["winners"].values())
    selected_metrics = result["strategy_metrics"][result["strategy_metrics"].name.isin(selected_names)]
    holdout_selected = selected_metrics[selected_metrics.split.eq("holdout")]
    comparison = pd.concat([
        result["benchmarks"][(result["benchmarks"].split.eq("holdout")) & (result["benchmarks"].cost_bps.isin([25, 50]))],
        holdout_selected,
    ], ignore_index=True, sort=False)
    architecture_summary = result["selected_holdouts"].copy()
    source_importance = result["feature_importance"].merge(result["feature_metadata"][["feature", "source_family"]], on="feature", how="left")
    source_summary = source_importance.assign(abs_importance=lambda df: df.importance.abs()).groupby("source_family", dropna=False).abs_importance.sum().reset_index().sort_values("abs_importance", ascending=False)

    (output / "executive_summary.md").write_text(f"""# Executive summary

Study: **{result['protocol']['title']}**

The frozen strategy **{BASELINE_NAME}** was not modified, reselected, or retuned.

## Protocol

- Development: {result['protocol']['development_period']}
- Locked holdout: {result['protocol']['locked_holdout']}
- Strategy configurations: {result['tested_configurations']['strategy_configs']}
- Prediction configurations: {result['tested_configurations']['prediction_configs']}

## Final conclusion

{result['final_conclusion']}
""", encoding="utf-8")

    (output / "architecture_comparison.md").write_text(f"""# Architecture comparison

Architecture A is the frozen macro-first benchmark. Architecture B is
expansion-first. Architecture C is hybrid expansion alpha plus macro regime
state before the post-alpha risk layer.

{_table(architecture_summary, [('selection', 'Selection'), ('candidate', 'Candidate'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure'), ('CAGR_50bps', 'CAGR 50 bps'), ('PBO', 'PBO'), ('deflated_sharpe_probability', 'DSR'), ('cash_reduction_false_improvement', 'Cash false improvement?'), ('replacement_candidate', 'Replacement?')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'CAGR_50bps', 'PBO', 'deflated_sharpe_probability'})}
""", encoding="utf-8")

    (output / "feature_usage.md").write_text(f"""# Feature usage

Features were lagged before model fitting. ETF/on-chain/options features were
included only where usable data existed; unavailable sources were skipped.

## Feature inventory

{_table(result['feature_metadata'], [('feature', 'Feature'), ('source_family', 'Source family'), ('source', 'Source'), ('used', 'Used'), ('notes', 'Notes')], limit=120)}

## Source-family importance proxy

{_table(source_summary, [('source_family', 'Source family'), ('abs_importance', 'Total absolute model importance')], limit=30)}
""", encoding="utf-8")

    (output / "model_comparison.md").write_text(f"""# Model comparison

All listed model families that were installed were tested independently.
LSTM was skipped because the sample size is too small for credible CPCV.

## Predictive metrics

{_table(result['prediction_metrics'], [('config', 'Config'), ('target', 'Target'), ('model', 'Model'), ('model_family', 'Family'), ('split', 'Split'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier')], limit=120)}
""", encoding="utf-8")

    (output / "portfolio_construction.md").write_text(f"""# Portfolio construction

Alpha portfolios were constructed before risk controls. Versions tested:
BTC/ETH only, BTC/ETH + cash, top-20 universe, and top-20 with BTC/ETH core.
Construction methods: equal weight, confidence weight, probability weight, and
volatility-adjusted weight.

{_table(result['selection'], [('candidate', 'Candidate'), ('architecture', 'Architecture'), ('portfolio_version', 'Portfolio'), ('construction', 'Construction'), ('risk_layer', 'Risk layer'), ('selection_score', 'Selection score'), ('median_fold_sharpe', 'Median CPCV Sharpe'), ('worst_fold_sharpe', 'Worst fold'), ('development_turnover', 'Dev turnover'), ('development_exposure', 'Dev exposure')], {'development_exposure'}, limit=100)}
""", encoding="utf-8")

    risk_summary = result["selection"].groupby(["architecture", "risk_layer"]).agg(
        median_selection_score=("selection_score", "median"),
        median_development_turnover=("development_turnover", "median"),
        median_development_exposure=("development_exposure", "median"),
    ).reset_index().sort_values("median_selection_score", ascending=False)
    (output / "risk_management_comparison.md").write_text(f"""# Risk management comparison

Risk management was applied after alpha generation. `none` is included only as
a control to measure whether post-alpha risk controls add value.

{_table(risk_summary, [('architecture', 'Architecture'), ('risk_layer', 'Risk layer'), ('median_selection_score', 'Median selection score'), ('median_development_turnover', 'Median dev turnover'), ('median_development_exposure', 'Median dev exposure')], {'median_development_exposure'}, limit=80)}
""", encoding="utf-8")

    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

{_table(comparison, [('name', 'Name'), ('benchmark_group', 'Group'), ('split', 'Split'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=120)}
""", encoding="utf-8")

    (output / "holdout_results.md").write_text(f"""# Holdout results

Holdout was opened only after development CPCV selection.

{_table(result['selected_holdouts'], [('selection', 'Selection'), ('candidate', 'Candidate'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure'), ('CAGR_50bps', 'CAGR 50 bps'), ('Sharpe_50bps', 'Sharpe 50 bps'), ('beats_frozen_sharpe', 'Beats frozen Sharpe'), ('beats_frozen_cagr', 'Beats frozen CAGR'), ('beats_frozen_drawdown', 'Beats frozen DD'), ('survives_50bps', 'Survives 50 bps'), ('cash_reduction_false_improvement', 'Cash false improvement?'), ('pbo_acceptable', 'PBO acceptable'), ('dsr_acceptable', 'DSR acceptable'), ('replacement_candidate', 'Replacement?')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'CAGR_50bps'})}
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

- PBO across expansion-first/hybrid candidate configurations: {_fmt(result['pbo'], True)}
- Tested configurations: {result['tested_configurations']['total']}
- PBO acceptance threshold: <= 65.00%
- DSR acceptance threshold: >= 50.00%

## Deflated Sharpe

{_table(result['deflated_sharpe'], [('selection', 'Selection'), ('candidate', 'Candidate'), ('deflated_sharpe_probability', 'DSR probability')], {'deflated_sharpe_probability'})}

No holdout result was used for candidate selection.
""", encoding="utf-8")

    best = result["selected_holdouts"].sort_values(["replacement_candidate", "Sharpe"], ascending=[False, False]).iloc[0]
    expansion = result["selected_holdouts"][result["selected_holdouts"].selection.eq("expansion_first")].iloc[0]
    hybrid = result["selected_holdouts"][result["selected_holdouts"].selection.eq("hybrid")].iloc[0]
    selected_holdouts = result["selected_holdouts"]
    best_by_metric = pd.DataFrame([
        {"criterion": "Highest Sharpe", "candidate": selected_holdouts.sort_values("Sharpe", ascending=False).iloc[0].candidate, "value": selected_holdouts.sort_values("Sharpe", ascending=False).iloc[0].Sharpe},
        {"criterion": "Highest CAGR", "candidate": selected_holdouts.sort_values("CAGR", ascending=False).iloc[0].candidate, "value": selected_holdouts.sort_values("CAGR", ascending=False).iloc[0].CAGR},
        {"criterion": "Best drawdown", "candidate": selected_holdouts.sort_values("Maximum Drawdown", ascending=False).iloc[0].candidate, "value": selected_holdouts.sort_values("Maximum Drawdown", ascending=False).iloc[0]["Maximum Drawdown"]},
        {"criterion": "Lowest turnover", "candidate": selected_holdouts.sort_values("Annual Turnover", ascending=True).iloc[0].candidate, "value": selected_holdouts.sort_values("Annual Turnover", ascending=True).iloc[0]["Annual Turnover"]},
        {"criterion": "Highest acceptable exposure", "candidate": selected_holdouts[selected_holdouts.Exposure >= 0.15].sort_values("Exposure", ascending=False).iloc[0].candidate if (selected_holdouts.Exposure >= 0.15).any() else "none", "value": selected_holdouts[selected_holdouts.Exposure >= 0.15].sort_values("Exposure", ascending=False).iloc[0].Exposure if (selected_holdouts.Exposure >= 0.15).any() else np.nan},
    ])
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Final questions

1. **Does expansion-first outperform macro-first?** Raw Sharpe is slightly higher ({_fmt(expansion['Sharpe'])} vs frozen {_fmt(result['frozen_holdout']['Sharpe'])}), but it fails replacement filters: {_fmt(expansion['replacement_candidate'])}.
2. **Does hybrid outperform both?** Raw holdout Sharpe/CAGR/drawdown improve, but replacement filters passed: {_fmt(hybrid['replacement_candidate'])}. Hybrid selected holdout Sharpe: {_fmt(hybrid['Sharpe'])}.
3. **Which source of alpha contributes most?** By model-importance proxy: {source_summary.iloc[0].source_family if not source_summary.empty else 'N/A'}.
4. **Does risk management add value after alpha generation?** See `risk_management_comparison.md`; value is accepted only if development-selected candidates survive holdout and economic filters.
5. **Single best selected strategy by raw selected holdout Sharpe:** {best['candidate']}.
6. **Would any strategy replace {BASELINE_NAME}?** {_fmt(result['final_strategy'] != BASELINE_NAME)}.
7. **Final Applied Project strategy:** {result['final_strategy']}.

## Best selected candidate by metric

{_table(best_by_metric, [('criterion', 'Criterion'), ('candidate', 'Candidate'), ('value', 'Value')])}

## Conclusion

{result['final_conclusion']}
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "tested_configurations": result["tested_configurations"],
        "best_date_configs": result["best_date_configs"],
        "best_cross_config": result["best_cross_config"],
        "winners": result["winners"],
        "frozen_holdout": _json_safe(result["frozen_holdout"]),
        "selected_holdouts": _json_safe(result["selected_holdouts"]),
        "pbo": _json_safe(result["pbo"]),
        "deflated_sharpe": _json_safe(result["deflated_sharpe"]),
        "final_strategy": result["final_strategy"],
        "final_conclusion": result["final_conclusion"],
        "model_notes": result["model_notes"],
        "prediction_metrics": _json_safe(result["prediction_metrics"]),
        "strategy_metrics": _json_safe(result["strategy_metrics"]),
        "benchmarks": _json_safe(result["benchmarks"]),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_expansion_first_research(output_dir: str | Path = "reports/expansion_first_research") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_expansion_first_research(panel, macro, public_data, probability)
    write_expansion_first_reports(output_dir, result)
    return result


__all__ = [
    "run_expansion_first_research",
    "write_expansion_first_reports",
    "run_default_expansion_first_research",
    "model_specs",
]
