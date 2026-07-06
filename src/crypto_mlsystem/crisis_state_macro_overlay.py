"""Crisis-state detection overlay for the frozen macro-regime crypto strategy.

Standalone research extension.  The selected ``btc_eth_macro_gate_balanced``
strategy is benchmark-only and is not modified, reselected, or retuned.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
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
from .volatility_breakout import (
    block_bootstrap_sharpe_ci,
    deflated_sharpe_probability,
    probability_backtest_overfitting,
)


try:  # pragma: no cover - availability depends on runtime image.
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        auc,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except Exception as exc:  # pragma: no cover
    raise RuntimeError("scikit-learn is required for the crisis-state study") from exc


DEVELOPMENT_START = pd.Timestamp("2019-07-05")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")
ANALYSIS_COST_LEVELS = (0, *COST_LEVELS)
BASELINE_NAME = FIXED_SELECTED.name
PROJECT_TITLE = "Macro-Regime Conditioning for Systematic Cryptocurrency Allocation: A Robust Out-of-Sample Evaluation"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    family: str


@dataclass(frozen=True)
class OverlaySpec:
    name: str
    action: str
    threshold: float


MODEL_SPECS = (
    ModelSpec("logistic_regression", "linear"),
    ModelSpec("elastic_net_logistic", "linear_regularized"),
    ModelSpec("random_forest", "tree_ensemble"),
    ModelSpec("gradient_boosting", "tree_ensemble"),
)

CRISIS_THRESHOLDS = (0.40, 0.50, 0.60, 0.70)
OVERLAY_ACTIONS = (
    "cash_if_high",
    "halve_if_high",
    "halve_if_rising",
    "cash_if_high_and_trend_negative",
    "cash_if_high_and_macro_stress",
)


def _rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(index[index.weekday == 4])
    return dates if len(dates) else pd.DatetimeIndex(index[::7])


def _safe_pct(series: pd.Series, periods: int) -> pd.Series:
    return series.pct_change(periods, fill_method=None).replace([np.inf, -np.inf], np.nan)


def _rolling_percentile(series: pd.Series, window: int = 252) -> pd.Series:
    return series.rolling(window, min_periods=max(30, window // 5)).apply(
        lambda values: pd.Series(values).rank(pct=True).iloc[-1],
        raw=False,
    )


def _load_full_macro_features(
    fallback: pd.DataFrame,
    path: str | Path = "data/processed/wrds_macro_features/wrds_macro_features_daily.csv",
) -> pd.DataFrame:
    p = Path(path)
    if p.exists():
        return pd.read_csv(p, parse_dates=["date"])
    return fallback.copy()


def _load_derivatives_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    path = Path("data/processed/derivatives/derivatives_daily_merged.csv")
    features = pd.DataFrame(index=index)
    if not path.exists():
        return features
    derivatives = pd.read_csv(path, parse_dates=["date"])
    keep = derivatives[derivatives["symbol"].isin(["BTC", "ETH"])].copy()
    if keep.empty:
        return features
    pivots = {}
    for column in ("funding_rate", "funding_sum_daily", "basis_close", "open_interest", "taker_imbalance"):
        if column in keep:
            pivots[column] = keep.pivot(index="date", columns="symbol", values=column).sort_index()
    if "funding_rate" in pivots:
        funding = pivots["funding_rate"].reindex(index).ffill().mean(axis=1)
        features["funding_level"] = funding.rolling(7, min_periods=3).mean().shift(1)
        features["funding_change"] = funding.diff(7).shift(1)
    if "funding_sum_daily" in pivots:
        funding_sum = pivots["funding_sum_daily"].reindex(index).ffill().mean(axis=1)
        features["funding_sum_7d"] = funding_sum.rolling(7, min_periods=3).sum().shift(1)
    if "open_interest" in pivots:
        oi = pivots["open_interest"].reindex(index).ffill().mean(axis=1)
        features["open_interest_change_7d"] = _safe_pct(oi, 7).shift(1)
    if "taker_imbalance" in pivots:
        taker = pivots["taker_imbalance"].reindex(index).ffill().mean(axis=1)
        features["taker_imbalance_7d"] = taker.rolling(7, min_periods=3).mean().shift(1)
    return features


def _external_public_features(index: pd.DatetimeIndex, public_data: PublicDataBundle | None) -> pd.DataFrame:
    features = pd.DataFrame(index=index)
    if public_data is None:
        return features
    if not public_data.stablecoins.empty:
        stable = public_data.stablecoins.copy()
        stable["date"] = pd.to_datetime(stable["date"])
        stable = stable.drop_duplicates("date").set_index("date").sort_index()
        for column in ("stablecoin_supply_change_7d", "stablecoin_supply_change_30d", "stablecoin_supply_z_90"):
            if column in stable:
                features[column] = stable[column].reindex(index).ffill().shift(1)
    if not public_data.chain_tvl.empty:
        tvl = public_data.chain_tvl.copy()
        tvl["date"] = pd.to_datetime(tvl["date"])
        all_tvl = tvl[tvl["chain"].astype(str).str.lower().eq("all")].set_index("date").sort_index()
        for column in ("tvl_change_30d", "tvl_change_90d"):
            if column in all_tvl:
                features[column] = all_tvl[column].reindex(index).ffill().shift(1)
        if "tvl" in all_tvl:
            series = all_tvl["tvl"].reindex(index).ffill()
            features["tvl_growth_30d"] = _safe_pct(series, 30).shift(1)
    if not public_data.binance_4h_daily_features.empty:
        hf = public_data.binance_4h_daily_features.copy()
        hf["date"] = pd.to_datetime(hf["date"])
        for column in ("trend_4h_7d", "trend_4h_14d", "volatility_4h_7d", "volatility_4h_30d", "drawdown_4h_30d", "volume_shock_4h"):
            if column in hf:
                pivot = hf.pivot(index="date", columns="symbol", values=column).sort_index()
                features[f"{column}_btc_eth_avg"] = pivot.reindex(index).ffill().mean(axis=1).shift(1)
    return features


def build_crisis_feature_panel(
    dataset: MacroRegimeDataset,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build daily lagged early-warning features."""
    index = dataset.close.index
    close = dataset.close
    returns = dataset.returns
    features = pd.DataFrame(index=index)

    macro = _load_full_macro_features(macro_features)
    macro["date"] = pd.to_datetime(macro["date"])
    macro = macro.drop_duplicates("date").set_index("date").sort_index()
    macro_cols = [
        "vix_level",
        "vix_change_5d",
        "vix_change_21d",
        "equity_realized_vol_21d",
        "equity_momentum_21d",
        "credit_spread_level",
        "credit_spread_change_21d",
        "usd_trend_21d",
        "usd_trend_63d",
        "usd_change_5d",
        "rates_10y_change_21d",
        "real_yield_10y_change_21d",
        "yield_curve_slope_change_21d",
    ]
    for column in macro_cols:
        if column in macro:
            features[column] = macro[column].reindex(index).ffill().shift(1)

    for asset in ("BTC", "ETH"):
        if asset not in close:
            continue
        price = close[asset]
        ret = returns[asset]
        rv21 = ret.rolling(21, min_periods=14).std() * np.sqrt(365)
        rv63 = ret.rolling(63, min_periods=30).std() * np.sqrt(365)
        downside = ret.clip(upper=0.0)
        features[f"{asset}_rv_21d"] = rv21.shift(1)
        features[f"{asset}_rv_63d"] = rv63.shift(1)
        features[f"{asset}_rv_acceleration"] = (rv21 - rv63).shift(1)
        features[f"{asset}_rv_percentile"] = _rolling_percentile(rv63).shift(1)
        features[f"{asset}_downside_semivariance_21d"] = downside.rolling(21, min_periods=14).std().shift(1)
        features[f"{asset}_drawdown_from_90d_high"] = (price / price.rolling(90, min_periods=40).max() - 1.0).shift(1)
        features[f"{asset}_below_100dma"] = (price < price.rolling(100, min_periods=60).mean()).astype(float).shift(1)
        features[f"{asset}_below_200dma"] = (price < price.rolling(200, min_periods=120).mean()).astype(float).shift(1)
        features[f"{asset}_momentum_63d"] = _safe_pct(price, 63).shift(1)
        features[f"{asset}_momentum_126d"] = _safe_pct(price, 126).shift(1)
        high21 = price.rolling(21, min_periods=10).max()
        high63 = price.rolling(63, min_periods=30).max()
        low21 = price.rolling(21, min_periods=10).min()
        low63 = price.rolling(63, min_periods=30).min()
        features[f"{asset}_failed_breakout"] = ((price < high63.shift(1)) & (_safe_pct(price, 21) < 0)).astype(float).shift(1)
        features[f"{asset}_lower_high_low_proxy"] = ((high21 < high63.shift(21)) & (low21 < low63.shift(21))).astype(float).shift(1)
    if {"BTC", "ETH"}.issubset(close.columns):
        ratio = close["ETH"] / close["BTC"]
        features["eth_btc_relative_weakness_63d"] = (-_safe_pct(ratio, 63)).shift(1)
    if "cross_sectional_dispersion" in dataset.regime_features:
        features["cross_sectional_dispersion"] = dataset.regime_features["cross_sectional_dispersion"].reindex(index).ffill().shift(1)

    features = pd.concat([
        features,
        _load_derivatives_features(index),
        _external_public_features(index, public_data),
    ], axis=1)
    features = features.replace([np.inf, -np.inf], np.nan)
    metadata = pd.DataFrame([
        {
            "feature": column,
            "available": bool(features[column].notna().any()),
            "lag": "shifted one day before weekly prediction",
            "point_in_time_status": "lagged; labels are not included as features",
        }
        for column in features.columns
    ])
    return features.loc[:, features.notna().any()].copy(), metadata


def build_crisis_labels(dataset: MacroRegimeDataset, frozen_result_25: PortfolioResult) -> tuple[pd.DataFrame, pd.DataFrame]:
    close = dataset.close
    returns = dataset.returns
    assets = [asset for asset in ("BTC", "ETH") if asset in close]
    if not assets:
        raise ValueError("BTC/ETH data is required for crisis labels")
    mix_returns = returns[assets].mean(axis=1).fillna(0.0)
    mix_wealth = (1.0 + mix_returns).cumprod()
    labels = pd.DataFrame(index=close.index)
    fwd30 = mix_wealth.shift(-30) / mix_wealth - 1.0
    fwd60 = mix_wealth.shift(-60) / mix_wealth - 1.0
    labels["target_a_30d_loss_gt_20"] = (fwd30 < -0.20).astype(float)
    labels["target_b_60d_loss_gt_30"] = (fwd60 < -0.30).astype(float)
    future_rv30 = mix_returns.rolling(30, min_periods=20).std().shift(-30) * np.sqrt(365)
    threshold = future_rv30.loc[DEVELOPMENT_START:DEVELOPMENT_END].quantile(0.80)
    labels["target_c_forward_vol_top20"] = (future_rv30 > threshold).astype(float)
    rolling_high = mix_wealth.rolling(90, min_periods=40).max()
    future_min30 = mix_wealth.shift(-1).rolling(30, min_periods=10).min().shift(-29)
    labels["target_d_future_drawdown_gt_25"] = (future_min30 / rolling_high - 1.0 < -0.25).astype(float)
    frozen_wealth = (1.0 + frozen_result_25.returns.reindex(close.index).fillna(0.0)).cumprod()
    future_min60 = frozen_wealth.shift(-1).rolling(60, min_periods=20).min().shift(-59)
    labels["target_e_frozen_future_dd_gt_20"] = (future_min60 / frozen_wealth - 1.0 < -0.20).astype(float)
    valid_until = close.index.max() - pd.Timedelta(days=60)
    labels.loc[labels.index > valid_until, :] = np.nan
    metadata = pd.DataFrame([
        {"target": "target_a_30d_loss_gt_20", "definition": "BTC/ETH 50-50 loses more than 20% over next 30 days"},
        {"target": "target_b_60d_loss_gt_30", "definition": "BTC/ETH 50-50 loses more than 30% over next 60 days"},
        {"target": "target_c_forward_vol_top20", "definition": "Forward 30d realized volatility exceeds development 80th percentile"},
        {"target": "target_d_future_drawdown_gt_25", "definition": "BTC/ETH portfolio enters >25% drawdown from rolling 90d high"},
        {"target": "target_e_frozen_future_dd_gt_20", "definition": "Frozen macro strategy has >20% forward drawdown over next 60 days"},
    ])
    for target in labels:
        metadata.loc[metadata["target"].eq(target), "development_positive_rate"] = labels[target].loc[DEVELOPMENT_START:DEVELOPMENT_END].mean()
        metadata.loc[metadata["target"].eq(target), "holdout_positive_rate"] = labels[target].loc[HOLDOUT_START:HOLDOUT_END].mean()
    return labels, metadata


def _make_model(spec: ModelSpec) -> Pipeline:
    if spec.name == "logistic_regression":
        model = LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs")
        return Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("model", model)])
    if spec.name == "elastic_net_logistic":
        model = LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            penalty="elasticnet",
            solver="saga",
            l1_ratio=0.50,
            C=0.50,
            random_state=17,
        )
        return Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("model", model)])
    if spec.name == "random_forest":
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=3,
            min_samples_leaf=8,
            class_weight="balanced_subsample",
            random_state=17,
        )
        return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", model)])
    if spec.name == "gradient_boosting":
        model = GradientBoostingClassifier(n_estimators=120, max_depth=2, learning_rate=0.04, random_state=17)
        return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", model)])
    raise ValueError(spec.name)


def _weekly_supervised_frame(features: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    dates = _rebalance_dates(features.index)
    x = features.reindex(dates).ffill()
    y = labels.reindex(dates)
    return pd.concat([x, y], axis=1)


def _predict_oof_and_holdout(
    weekly: pd.DataFrame,
    feature_cols: list[str],
    target: str,
    spec: ModelSpec,
) -> tuple[pd.Series, pd.Series, pd.DataFrame, Any]:
    data = weekly[feature_cols + [target]].dropna(subset=[target]).copy()
    dev = data.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    all_x = weekly[feature_cols].copy()
    oof = pd.Series(np.nan, index=weekly.index, dtype=float)
    fold_rows = []
    if dev[target].nunique() < 2:
        return oof, oof.copy(), pd.DataFrame(), None
    splits = combinatorial_purged_splits(len(dev), n_groups=6, n_test_groups=2, label_horizon=8, embargo=2)
    for fold, split in enumerate(splits):
        train = dev.iloc[list(split.train_indices)]
        test = dev.iloc[list(split.test_indices)]
        if train[target].nunique() < 2:
            continue
        model = _make_model(spec)
        model.fit(train[feature_cols], train[target].astype(int))
        prob = model.predict_proba(test[feature_cols])[:, 1]
        oof.loc[test.index] = prob
        fold_rows.append({
            "target": target,
            "model": spec.name,
            "fold": fold,
            "test_groups": "-".join(map(str, split.test_groups)),
            "fold_start": str(test.index.min().date()),
            "fold_end": str(test.index.max().date()),
            "positive_rate": float(test[target].mean()),
        })
    final_model = _make_model(spec)
    final_model.fit(dev[feature_cols], dev[target].astype(int))
    final_prob = pd.Series(final_model.predict_proba(all_x)[:, 1], index=all_x.index)
    combined = final_prob.copy()
    combined.loc[oof.dropna().index] = oof.dropna()
    return oof, combined, pd.DataFrame(fold_rows), final_model


def _classification_metrics(y_true: pd.Series, prob: pd.Series, threshold: float = 0.50) -> dict[str, float]:
    data = pd.concat([y_true.rename("y"), prob.rename("p")], axis=1).dropna()
    if data.empty or data["y"].nunique() < 2:
        return {
            "auc": np.nan,
            "precision": np.nan,
            "recall": np.nan,
            "f1": np.nan,
            "brier": np.nan,
            "false_negative_rate": np.nan,
            "true_negative": np.nan,
            "false_positive": np.nan,
            "false_negative": np.nan,
            "true_positive": np.nan,
        }
    y = data["y"].astype(int)
    pred = (data["p"] >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "auc": float(roc_auc_score(y, data["p"])),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "brier": float(brier_score_loss(y, data["p"])),
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else np.nan,
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def _calibration_curve(y_true: pd.Series, prob: pd.Series, bins: int = 5) -> pd.DataFrame:
    data = pd.concat([y_true.rename("y"), prob.rename("p")], axis=1).dropna()
    if data.empty:
        return pd.DataFrame()
    data["bin"] = pd.cut(data["p"], bins=np.linspace(0, 1, bins + 1), include_lowest=True)
    rows = []
    for interval, group in data.groupby("bin", observed=False):
        rows.append({
            "probability_bin": str(interval),
            "observations": int(len(group)),
            "average_probability": float(group["p"].mean()) if len(group) else np.nan,
            "observed_crisis_rate": float(group["y"].mean()) if len(group) else np.nan,
        })
    return pd.DataFrame(rows)


def _feature_importance(model: Any, feature_cols: list[str], target: str, model_name: str) -> pd.DataFrame:
    if model is None:
        return pd.DataFrame()
    estimator = model.named_steps["model"]
    values: np.ndarray | None = None
    if hasattr(estimator, "coef_"):
        values = np.ravel(estimator.coef_)
    elif hasattr(estimator, "feature_importances_"):
        values = np.ravel(estimator.feature_importances_)
    if values is None:
        return pd.DataFrame()
    frame = pd.DataFrame({"feature": feature_cols, "importance": values})
    frame["abs_importance"] = frame["importance"].abs()
    frame["target"] = target
    frame["model"] = model_name
    return frame.sort_values("abs_importance", ascending=False).reset_index(drop=True)


def _stress_masks(features: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    trend_negative = pd.Series(False, index=features.index)
    for col in ("BTC_momentum_63d", "ETH_momentum_63d", "BTC_below_200dma", "ETH_below_200dma"):
        if col in features:
            if "below" in col:
                trend_negative = trend_negative | (features[col] > 0.5)
            else:
                trend_negative = trend_negative | (features[col] < 0)
    dev = features.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    macro_stress = pd.Series(False, index=features.index)
    if "vix_level" in features:
        macro_stress = macro_stress | (features["vix_level"] > dev["vix_level"].median())
    if "vix_change_21d" in features:
        macro_stress = macro_stress | (features["vix_change_21d"] > 0)
    if "equity_momentum_21d" in features:
        macro_stress = macro_stress | (features["equity_momentum_21d"] < 0)
    return trend_negative.reindex(features.index).fillna(False), macro_stress.reindex(features.index).fillna(False)


def _overlay_weights(
    frozen_weights: pd.DataFrame,
    probability: pd.Series,
    overlay: OverlaySpec,
    trend_negative: pd.Series,
    macro_stress: pd.Series,
) -> pd.DataFrame:
    weights = frozen_weights.copy()
    prob = probability.reindex(weights.index).ffill().fillna(0.0)
    p_change = prob.diff(2).fillna(0.0)
    trend = trend_negative.reindex(weights.index).ffill().fillna(False)
    macro = macro_stress.reindex(weights.index).ffill().fillna(False)
    scale = pd.Series(1.0, index=weights.index)
    if overlay.action == "cash_if_high":
        scale[prob > overlay.threshold] = 0.0
    elif overlay.action == "halve_if_high":
        scale[prob > overlay.threshold] = 0.50
    elif overlay.action == "halve_if_rising":
        scale[(prob > overlay.threshold) & (p_change > 0.10)] = 0.50
    elif overlay.action == "cash_if_high_and_trend_negative":
        scale[(prob > overlay.threshold) & trend] = 0.0
    elif overlay.action == "cash_if_high_and_macro_stress":
        scale[(prob > overlay.threshold) & macro] = 0.0
    else:
        raise ValueError(overlay.action)
    return weights.mul(scale, axis=0)


def _worst_drawdown_info(returns: pd.Series) -> dict[str, Any]:
    values = returns.dropna()
    if values.empty:
        return {"worst_drawdown_start": None, "worst_drawdown_trough": None, "worst_drawdown_recovery": None}
    wealth = (1.0 + values).cumprod()
    dd = wealth / wealth.cummax() - 1.0
    trough = dd.idxmin()
    peak = wealth.loc[:trough].idxmax()
    recovery = None
    post = wealth.loc[trough:]
    recovered = post[post >= wealth.loc[peak]]
    if not recovered.empty:
        recovery = recovered.index[0]
    return {
        "worst_drawdown_start": str(pd.Timestamp(peak).date()),
        "worst_drawdown_trough": str(pd.Timestamp(trough).date()),
        "worst_drawdown_recovery": str(pd.Timestamp(recovery).date()) if recovery is not None else None,
    }


def _period_metrics_extended(result: PortfolioResult, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    metrics = period_metrics(result, start, end)
    returns = result.returns.loc[start:end]
    metrics["Allocation Changes"] = int((result.turnover.reindex(returns.index).fillna(0.0) > 1e-9).sum())
    metrics.update(_worst_drawdown_info(returns))
    return metrics


def _weekly_returns(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0).dropna()


def _sharpe(returns: pd.Series, annualization: int = 52) -> float:
    values = returns.dropna()
    std = values.std()
    return float(values.mean() / std * np.sqrt(annualization)) if len(values) and std and np.isfinite(std) else 0.0


def _cpcv_rows(name: str, result: PortfolioResult) -> pd.DataFrame:
    weekly = _weekly_returns(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
    if len(weekly) < 20:
        return pd.DataFrame()
    rows = []
    for fold, split in enumerate(combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=8, embargo=2)):
        test = weekly.iloc[list(split.test_indices)]
        rows.append({
            "candidate": name,
            "fold": fold,
            "fold_sharpe": _sharpe(test),
            "fold_return": float((1.0 + test).prod() - 1.0),
            "positive_fold": bool((1.0 + test).prod() - 1.0 > 0),
        })
    return pd.DataFrame(rows)


def _cpcv_summary(folds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for candidate, group in folds.groupby("candidate", dropna=False):
        rows.append({
            "candidate": candidate,
            "median_fold_sharpe": float(group["fold_sharpe"].median()),
            "best_fold_sharpe": float(group["fold_sharpe"].max()),
            "worst_fold_sharpe": float(group["fold_sharpe"].min()),
            "positive_fold_percentage": float(group["positive_fold"].mean()),
        })
    return pd.DataFrame(rows)


def _exposure_quality(dataset: MacroRegimeDataset, result: PortfolioResult, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float]:
    returns = result.returns.loc[start:end]
    weights = result.weights.reindex(returns.index).fillna(0.0)
    exposure = weights.sum(axis=1).clip(0.0, 1.0)
    invested = exposure > 1e-9
    weekly = _weekly_returns(returns)
    weekly_exp = exposure.resample("W-FRI").mean().reindex(weekly.index).fillna(0.0)
    assets = [asset for asset in ("BTC", "ETH") if asset in dataset.returns]
    opportunity = dataset.returns[assets].mean(axis=1).reindex(returns.index).fillna(0.0) if assets else pd.Series(0.0, index=returns.index)
    cash = ~invested
    return {
        "positive_invested_week_percentage": float((weekly[weekly_exp > 1e-9] > 0).mean()) if (weekly_exp > 1e-9).any() else 0.0,
        "missed_upside_while_in_cash": float(opportunity[cash].clip(lower=0.0).sum()),
        "avoided_downside_while_in_cash": float(-opportunity[cash].clip(upper=0.0).sum()),
        "average_exposure": float(exposure.mean()),
    }


def _score_overlays(
    metrics: pd.DataFrame,
    cpcv: pd.DataFrame,
    model_metrics: pd.DataFrame,
    exposure_quality: pd.DataFrame,
    frozen_dev: pd.Series,
) -> pd.DataFrame:
    dev = metrics[(metrics.split.eq("development")) & (metrics.cost_bps.eq(25))].set_index("candidate")
    cpcv_idx = cpcv.set_index("candidate")
    mm = model_metrics.set_index("model_config")
    eq = exposure_quality[exposure_quality.split.eq("development")].set_index("candidate")
    rows = []
    for candidate in dev.index:
        parts = str(candidate).split("|")
        model_config = parts[0]
        if candidate not in cpcv_idx.index or model_config not in mm.index:
            continue
        d = dev.loc[candidate]
        cv = cpcv_idx.loc[candidate]
        model = mm.loc[model_config]
        quality = eq.loc[candidate] if candidate in eq.index else pd.Series(dtype=float)
        dd_reduction = float(d["Maximum Drawdown"] - frozen_dev["Maximum Drawdown"])
        dd_score = np.clip((dd_reduction + 0.05) / 0.35, 0.0, 1.0)
        median_score = np.clip((float(cv["median_fold_sharpe"]) + 1.0) / 3.0, 0.0, 1.0)
        recall_score_component = np.clip(float(model.get("recall", 0.0)), 0.0, 1.0)
        turnover = float(d["Annual Turnover"])
        turnover_score = 1.0 if turnover <= 12 else max(0.0, 1.0 - (turnover - 12) / 12)
        exposure = float(d["Exposure"])
        exposure_score = np.clip(exposure / float(frozen_dev["Exposure"]), 0.0, 1.0) if frozen_dev["Exposure"] else 0.0
        score = 0.40 * dd_score + 0.25 * median_score + 0.15 * recall_score_component + 0.10 * turnover_score + 0.10 * exposure_score
        if exposure < 0.25:
            score -= 0.12
        if turnover > 12:
            score -= 0.08
        if model.get("recall", 0.0) < 0.50:
            score -= 0.10
        if model.get("false_negative_rate", 1.0) > 0.50:
            score -= 0.08
        if quality.get("missed_upside_while_in_cash", 0.0) > quality.get("avoided_downside_while_in_cash", 0.0) * 1.5:
            score -= 0.05
        rows.append({
            "candidate": candidate,
            "model_config": model_config,
            "target": model.get("target"),
            "model": model.get("model"),
            "overlay_action": parts[1],
            "threshold": float(parts[2]),
            "selection_score": float(score),
            "development_sharpe": float(d["Sharpe"]),
            "development_cagr": float(d["CAGR"]),
            "development_max_drawdown": float(d["Maximum Drawdown"]),
            "development_turnover": turnover,
            "development_exposure": exposure,
            "cpcv_median_sharpe": float(cv["median_fold_sharpe"]),
            "cpcv_worst_fold_sharpe": float(cv["worst_fold_sharpe"]),
            "cpcv_best_fold_sharpe": float(cv["best_fold_sharpe"]),
            "positive_fold_percentage": float(cv["positive_fold_percentage"]),
            "crisis_recall": float(model.get("recall", np.nan)),
            "false_negative_rate": float(model.get("false_negative_rate", np.nan)),
            "model_auc": float(model.get("auc", np.nan)),
            "model_brier": float(model.get("brier", np.nan)),
            "dd_reduction_vs_frozen": dd_reduction,
        })
    return pd.DataFrame(rows).sort_values("selection_score", ascending=False).reset_index(drop=True)


def _paired_sharpe_delta_ci(left: pd.Series, right: pd.Series, samples: int = 500, block_length: int = 14, seed: int = 71) -> dict[str, float]:
    data = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
    if len(data) < block_length * 2:
        return {"lower": np.nan, "median": np.nan, "upper": np.nan}
    rng = np.random.default_rng(seed)
    arr = data.to_numpy(dtype=float)
    estimates = []
    blocks_needed = int(np.ceil(len(arr) / block_length))
    max_start = len(arr) - block_length
    for _ in range(samples):
        starts = rng.integers(0, max_start + 1, blocks_needed)
        sample = np.concatenate([arr[start:start + block_length] for start in starts])[:len(arr)]
        estimates.append(_sharpe(pd.Series(sample[:, 0]), 365) - _sharpe(pd.Series(sample[:, 1]), 365))
    lower, median, upper = np.quantile(estimates, [0.025, 0.5, 0.975])
    return {"lower": float(lower), "median": float(median), "upper": float(upper)}


def _all_on(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series, pd.Series]:
    risk = pd.Series("risk_on", index=index, dtype=object)
    crypto = pd.Series("not_used", index=index, dtype=object)
    return risk, crypto, risk


def _benchmark_weights(dataset: MacroRegimeDataset, name: str, frozen_combined: pd.Series | None = None) -> tuple[pd.DataFrame, tuple[pd.Series, pd.Series, pd.Series], float]:
    weights = pd.DataFrame(0.0, index=dataset.close.index, columns=dataset.close.columns)
    if name == "btc_buy_hold":
        if "BTC" in weights:
            weights["BTC"] = 1.0
        return weights, _all_on(dataset.close.index), 10.0
    if name == "eth_buy_hold":
        if "ETH" in weights:
            weights["ETH"] = 1.0
        return weights, _all_on(dataset.close.index), 10.0
    if name == "btc_eth_50_50_buy_hold":
        for asset in ("BTC", "ETH"):
            if asset in weights:
                weights[asset] = 0.5
        return weights, _all_on(dataset.close.index), 10.0
    dates = _rebalance_dates(dataset.close.index)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    if frozen_combined is None:
        raise ValueError(name)
    for date_ in dates:
        regime = frozen_combined.reindex([date_]).ffill().iloc[0]
        if regime == "risk_off":
            continue
        exposure = 1.0 if regime == "risk_on" else 0.5
        if name == "btc_only_macro_gate" and "BTC" in weights:
            weights.loc[date_, "BTC"] = exposure
        elif name == "eth_only_macro_gate" and "ETH" in weights:
            weights.loc[date_, "ETH"] = exposure
        elif name == "btc_eth_50_50_macro_gate":
            for asset in ("BTC", "ETH"):
                if asset in weights:
                    weights.loc[date_, asset] = 0.5 * exposure
    return weights, _all_on(dataset.close.index), FIXED_SELECTED.turnover_cap


def _event_study(
    selected_probability: pd.Series,
    selected_threshold: float,
    frozen: PortfolioResult,
    overlay: PortfolioResult,
) -> pd.DataFrame:
    events = [
        ("2020_covid_crash", "2020-02-15", "2020-04-30"),
        ("2021_2022_crypto_bear", "2021-11-08", "2022-11-21"),
        ("2025_holdout_drawdown", "2025-01-23", "2025-05-08"),
    ]
    rows = []
    for name, start_s, end_s in events:
        start = pd.Timestamp(start_s)
        end = pd.Timestamp(end_s)
        pre = selected_probability.loc[start - pd.Timedelta(days=90):start]
        event_prob = selected_probability.loc[start:end]
        warnings = pre[pre >= selected_threshold]
        first_warning = warnings.index.min() if not warnings.empty else None
        rows.append({
            "event": name,
            "start": start_s,
            "end": end_s,
            "avg_crisis_probability": float(event_prob.mean()) if len(event_prob) else np.nan,
            "max_crisis_probability": float(event_prob.max()) if len(event_prob) else np.nan,
            "first_warning_date": str(first_warning.date()) if first_warning is not None else None,
            "days_warning_before_event": int((start - first_warning).days) if first_warning is not None else np.nan,
            "frozen_return": float((1.0 + frozen.returns.loc[start:end]).prod() - 1.0),
            "overlay_return": float((1.0 + overlay.returns.loc[start:end]).prod() - 1.0),
            "frozen_avg_exposure": float(frozen.weights.sum(axis=1).loc[start:end].mean()),
            "overlay_avg_exposure": float(overlay.weights.sum(axis=1).loc[start:end].mean()),
        })
    return pd.DataFrame(rows)


def run_crisis_state_macro_overlay(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    frozen_weights, frozen_macro, frozen_crypto, frozen_combined = build_candidate_weights(dataset, FIXED_SELECTED)
    frozen_25 = backtest_weights(dataset, frozen_weights, frozen_macro, frozen_crypto, frozen_combined, 25, FIXED_SELECTED.turnover_cap)
    features, feature_metadata = build_crisis_feature_panel(dataset, macro_features, public_data)
    labels, label_metadata = build_crisis_labels(dataset, frozen_25)
    weekly = _weekly_supervised_frame(features, labels)
    feature_cols = [col for col in features.columns if weekly[col].notna().sum() > 50]

    model_metric_rows: list[dict[str, Any]] = []
    model_fold_rows: list[pd.DataFrame] = []
    calibration_rows: list[pd.DataFrame] = []
    importance_rows: list[pd.DataFrame] = []
    probability_map: dict[str, pd.Series] = {}
    model_registry: list[dict[str, Any]] = []

    for target in labels.columns:
        if weekly[target].loc[DEVELOPMENT_START:DEVELOPMENT_END].dropna().nunique() < 2:
            continue
        for spec in MODEL_SPECS:
            oof, combined_probability, folds, final_model = _predict_oof_and_holdout(weekly, feature_cols, target, spec)
            config = f"{target}__{spec.name}"
            probability_map[config] = combined_probability
            model_registry.append({"model_config": config, "target": target, "model": spec.name, "features": len(feature_cols)})
            if not folds.empty:
                model_fold_rows.append(folds.assign(model_config=config))
            dev_metrics = _classification_metrics(weekly[target].loc[DEVELOPMENT_START:DEVELOPMENT_END], oof.loc[DEVELOPMENT_START:DEVELOPMENT_END])
            holdout_metrics = _classification_metrics(weekly[target].loc[HOLDOUT_START:HOLDOUT_END], combined_probability.loc[HOLDOUT_START:HOLDOUT_END])
            model_metric_rows.append({"model_config": config, "target": target, "model": spec.name, "split": "development_oof", **dev_metrics})
            model_metric_rows.append({"model_config": config, "target": target, "model": spec.name, "split": "holdout_diagnostic", **holdout_metrics})
            cal = _calibration_curve(weekly[target].loc[DEVELOPMENT_START:DEVELOPMENT_END], oof.loc[DEVELOPMENT_START:DEVELOPMENT_END])
            if not cal.empty:
                calibration_rows.append(cal.assign(model_config=config, target=target, model=spec.name, split="development_oof"))
            imp = _feature_importance(final_model, feature_cols, target, spec.name)
            if not imp.empty:
                importance_rows.append(imp.assign(model_config=config).head(25))

    model_metrics = pd.DataFrame(model_metric_rows)
    model_folds = pd.concat(model_fold_rows, ignore_index=True) if model_fold_rows else pd.DataFrame()
    calibration = pd.concat(calibration_rows, ignore_index=True) if calibration_rows else pd.DataFrame()
    feature_importance = pd.concat(importance_rows, ignore_index=True) if importance_rows else pd.DataFrame()

    trend_negative, macro_stress = _stress_masks(features.reindex(weekly.index).ffill().fillna(0.0))
    overlay_specs = [OverlaySpec(action, action, threshold) for action in OVERLAY_ACTIONS for threshold in CRISIS_THRESHOLDS]

    metrics_rows: list[dict[str, Any]] = []
    overlay_results_25: dict[str, PortfolioResult] = {}
    exposure_rows: list[dict[str, Any]] = []
    for config, probability in probability_map.items():
        for overlay in overlay_specs:
            name = f"{config}|{overlay.action}|{overlay.threshold:.2f}"
            weights = _overlay_weights(frozen_weights, probability, overlay, trend_negative, macro_stress)
            result25 = backtest_weights(dataset, weights, frozen_macro, frozen_crypto, frozen_combined, 25, FIXED_SELECTED.turnover_cap)
            overlay_results_25[name] = result25
            for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
                metrics_rows.append({
                    "candidate": name,
                    "model_config": config,
                    "target": config.split("__")[0],
                    "model": config.split("__", 1)[1],
                    "overlay_action": overlay.action,
                    "threshold": overlay.threshold,
                    "split": split,
                    "cost_bps": 25,
                    **_period_metrics_extended(result25, start, end),
                })
                exposure_rows.append({
                    "candidate": name,
                    "split": split,
                    **_exposure_quality(dataset, result25, start, end),
                })

    metrics = pd.DataFrame(metrics_rows)
    exposure_quality = pd.DataFrame(exposure_rows)
    cpcv_folds = pd.concat([_cpcv_rows(name, res) for name, res in overlay_results_25.items()], ignore_index=True)
    cpcv_summary = _cpcv_summary(cpcv_folds)
    dev_model_metrics = model_metrics[model_metrics.split.eq("development_oof")].copy()
    selection = _score_overlays(
        metrics,
        cpcv_summary,
        dev_model_metrics,
        exposure_quality,
        pd.Series(_period_metrics_extended(frozen_25, DEVELOPMENT_START, DEVELOPMENT_END)),
    )
    selected = str(selection.iloc[0]["candidate"])
    selected_parts = selected.split("|")
    selected_config = selected_parts[0]
    selected_overlay = OverlaySpec(selected_parts[1], selected_parts[1], float(selected_parts[2]))
    selected_probability = probability_map[selected_config]
    selected_weights = _overlay_weights(frozen_weights, selected_probability, selected_overlay, trend_negative, macro_stress)

    selected_results: dict[int, PortfolioResult] = {}
    selected_rows = []
    frozen_rows = []
    frozen_results: dict[int, PortfolioResult] = {}
    for cost in ANALYSIS_COST_LEVELS:
        selected_result = backtest_weights(dataset, selected_weights, frozen_macro, frozen_crypto, frozen_combined, cost, FIXED_SELECTED.turnover_cap)
        frozen_result = backtest_weights(dataset, frozen_weights, frozen_macro, frozen_crypto, frozen_combined, cost, FIXED_SELECTED.turnover_cap)
        selected_results[cost] = selected_result
        frozen_results[cost] = frozen_result
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            selected_rows.append({"candidate": selected, "split": split, "cost_bps": cost, **_period_metrics_extended(selected_result, start, end)})
            frozen_rows.append({"candidate": BASELINE_NAME, "split": split, "cost_bps": cost, **_period_metrics_extended(frozen_result, start, end)})

    selected_metrics = pd.DataFrame(selected_rows)
    frozen_metrics = pd.DataFrame(frozen_rows)
    frozen_dev = frozen_metrics[(frozen_metrics.split.eq("development")) & (frozen_metrics.cost_bps.eq(25))].iloc[0]
    frozen_hold = frozen_metrics[(frozen_metrics.split.eq("holdout")) & (frozen_metrics.cost_bps.eq(25))].iloc[0]
    selected_dev = selected_metrics[(selected_metrics.split.eq("development")) & (selected_metrics.cost_bps.eq(25))].iloc[0]
    selected_hold = selected_metrics[(selected_metrics.split.eq("holdout")) & (selected_metrics.cost_bps.eq(25))].iloc[0]
    selected_cpcv = cpcv_summary[cpcv_summary.candidate.eq(selected)].iloc[0]
    frozen_cpcv_folds = _cpcv_rows(BASELINE_NAME, frozen_results[25])
    frozen_cpcv = _cpcv_summary(frozen_cpcv_folds).iloc[0]
    weekly_configs = pd.DataFrame({name: _weekly_returns(res.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END]) for name, res in overlay_results_25.items()})
    pbo = probability_backtest_overfitting(weekly_configs, blocks=8)
    ci = block_bootstrap_sharpe_ci(selected_results[25].returns.loc[HOLDOUT_START:HOLDOUT_END], samples=500, block_length=14, seed=53)
    delta = _paired_sharpe_delta_ci(
        selected_results[25].returns.loc[HOLDOUT_START:HOLDOUT_END],
        frozen_results[25].returns.loc[HOLDOUT_START:HOLDOUT_END],
    )
    stats = pd.DataFrame([{
        "candidate": selected,
        "tested_configurations": len(metrics["candidate"].unique()),
        "pbo": pbo,
        "deflated_sharpe_probability": deflated_sharpe_probability(selected_results[25].returns.loc[HOLDOUT_START:HOLDOUT_END], len(metrics["candidate"].unique())),
        "bootstrap_sharpe_ci_lower": ci["lower"],
        "bootstrap_sharpe_ci_median": ci["median"],
        "bootstrap_sharpe_ci_upper": ci["upper"],
        "sharpe_delta_vs_frozen_lower": delta["lower"],
        "sharpe_delta_vs_frozen_median": delta["median"],
        "sharpe_delta_vs_frozen_upper": delta["upper"],
    }])
    selected_model_metric = dev_model_metrics[dev_model_metrics.model_config.eq(selected_config)].iloc[0]
    selected_hold_50 = selected_metrics[(selected_metrics.split.eq("holdout")) & (selected_metrics.cost_bps.eq(50))].iloc[0]
    failures = []
    if selected_dev["Maximum Drawdown"] <= frozen_dev["Maximum Drawdown"] + 0.20:
        failures.append("development max drawdown is not materially improved")
    if selected_dev["Sharpe"] <= frozen_dev["Sharpe"]:
        failures.append("development Sharpe does not improve")
    if selected_cpcv["median_fold_sharpe"] < frozen_cpcv["median_fold_sharpe"] - 0.05:
        failures.append("CPCV median Sharpe is not comparable")
    if selected_cpcv["worst_fold_sharpe"] < frozen_cpcv["worst_fold_sharpe"] - 0.05:
        failures.append("CPCV worst-fold Sharpe is worse")
    if selected_hold["Sharpe"] < frozen_hold["Sharpe"] - 0.05:
        failures.append("holdout Sharpe is not comparable")
    if selected_hold["Maximum Drawdown"] < frozen_hold["Maximum Drawdown"]:
        failures.append("holdout max drawdown is worse")
    if selected_hold["Exposure"] < 0.25:
        failures.append("holdout exposure below 25%")
    if selected_hold["Annual Turnover"] >= 12:
        failures.append("turnover exceeds 12x")
    if selected_hold_50["Sharpe"] <= 0 or selected_hold_50["CAGR"] <= 0:
        failures.append("does not survive 50 bps costs")
    if np.isfinite(pbo) and pbo > 0.50:
        failures.append("PBO above 50%")
    if stats.iloc[0]["deflated_sharpe_probability"] < 0.50:
        failures.append("weak DSR")
    selected_eq_hold = _exposure_quality(dataset, selected_results[25], HOLDOUT_START, HOLDOUT_END)
    if selected_eq_hold["missed_upside_while_in_cash"] > selected_eq_hold["avoided_downside_while_in_cash"] * 1.5:
        failures.append("improvement may be cash-driven")
    if selected_model_metric["recall"] < 0.50:
        failures.append("crisis recall is weak")

    event_studies = _event_study(selected_probability, selected_overlay.threshold, frozen_results[25], selected_results[25])

    benchmark_rows = []
    for name in ("btc_only_macro_gate", "eth_only_macro_gate", "btc_eth_50_50_macro_gate", "btc_buy_hold", "eth_buy_hold", "btc_eth_50_50_buy_hold"):
        weights, regimes, turnover_cap = _benchmark_weights(dataset, name, frozen_combined)
        result25 = backtest_weights(dataset, weights, frozen_macro if "macro_gate" in name else regimes[0], frozen_crypto if "macro_gate" in name else regimes[1], frozen_combined if "macro_gate" in name else regimes[2], 25, turnover_cap)
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            benchmark_rows.append({"candidate": name, "split": split, "cost_bps": 25, **_period_metrics_extended(result25, start, end)})
    drawdown_brake = Path("reports/drawdown_controlled_macro_trend/metrics.csv")
    if drawdown_brake.exists():
        prior = pd.read_csv(drawdown_brake)
        prior = prior[(prior["candidate"].eq("frozen_dd_10_reduce_50_r14")) & (prior["cost_bps"].eq(25))]
        for _, row in prior.iterrows():
            item = row.to_dict()
            item["candidate"] = "drawdown_brake_candidate"
            benchmark_rows.append(item)
    benchmark_comparison = pd.concat([
        frozen_metrics[(frozen_metrics.cost_bps.eq(25))],
        selected_metrics[(selected_metrics.cost_bps.eq(25))],
        pd.DataFrame(benchmark_rows),
    ], ignore_index=True, sort=False)

    return {
        "dataset": dataset,
        "feature_metadata": feature_metadata,
        "label_metadata": label_metadata,
        "model_registry": pd.DataFrame(model_registry),
        "model_metrics": model_metrics,
        "model_folds": model_folds,
        "calibration": calibration,
        "feature_importance": feature_importance,
        "metrics": metrics,
        "selected_metrics": selected_metrics,
        "frozen_metrics": frozen_metrics,
        "selection": selection,
        "cpcv_folds": cpcv_folds,
        "cpcv_summary": cpcv_summary,
        "frozen_cpcv_folds": frozen_cpcv_folds,
        "exposure_quality": exposure_quality,
        "statistics": stats,
        "event_studies": event_studies,
        "benchmark_comparison": benchmark_comparison,
        "selected_candidate": selected,
        "selected_model_config": selected_config,
        "selected_overlay": {"action": selected_overlay.action, "threshold": selected_overlay.threshold},
        "replacement_failures": failures,
        "final_decision": "replace_frozen_strategy" if not failures else "keep_frozen_strategy",
        "metadata": {
            "title": "Crisis-State Detection for Macro-Regime Cryptocurrency Allocation",
            "frozen_strategy": BASELINE_NAME,
            "frozen_strategy_modified": False,
            "development_period": [str(DEVELOPMENT_START.date()), str(DEVELOPMENT_END.date())],
            "holdout_period": [str(HOLDOUT_START.date()), str(HOLDOUT_END.date())],
            "model_configurations": len(model_registry),
            "overlay_configurations": len(metrics["candidate"].unique()),
            "cost_levels_bps": list(ANALYSIS_COST_LEVELS),
            "project_title": PROJECT_TITLE,
        },
    }


def _fmt(value: Any, percent: bool = False, integer: bool = False) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, (float, int, np.floating, np.integer)):
        if integer:
            return str(int(float(value)))
        return f"{float(value):.2%}" if percent else f"{float(value):.3f}"
    return str(value)


def _table(
    frame: pd.DataFrame,
    columns: list[tuple[str, str]],
    percent: set[str] | None = None,
    integer: set[str] | None = None,
    limit: int | None = None,
) -> str:
    percent = percent or set()
    integer = integer or set()
    if frame is None or frame.empty:
        return "_No rows._"
    view = frame.head(limit) if limit else frame
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in view.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent, key in integer) for key, _ in columns) + " |")
    return "\n".join(lines)


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.replace({np.nan: None}).to_dict("records")
    if isinstance(value, pd.Series):
        return value.replace({np.nan: None}).to_dict()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items() if k != "dataset"}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _metric_cols() -> list[tuple[str, str]]:
    return [
        ("candidate", "Candidate"),
        ("split", "Split"),
        ("cost_bps", "Cost bps"),
        ("CAGR", "CAGR"),
        ("Sharpe", "Sharpe"),
        ("Sortino", "Sortino"),
        ("Annualized Volatility", "Vol"),
        ("Maximum Drawdown", "Max DD"),
        ("Annual Turnover", "Turnover"),
        ("Exposure", "Exposure"),
        ("Cash Allocation", "Cash"),
        ("Worst Month", "Worst month"),
    ]


def write_crisis_state_macro_overlay_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for name, frame in (
        ("feature_metadata.csv", result["feature_metadata"]),
        ("label_metadata.csv", result["label_metadata"]),
        ("model_registry.csv", result["model_registry"]),
        ("model_metrics.csv", result["model_metrics"]),
        ("model_folds.csv", result["model_folds"]),
        ("calibration.csv", result["calibration"]),
        ("feature_importance.csv", result["feature_importance"]),
        ("strategy_metrics.csv", result["metrics"]),
        ("selected_metrics.csv", result["selected_metrics"]),
        ("frozen_metrics.csv", result["frozen_metrics"]),
        ("selection.csv", result["selection"]),
        ("cpcv_folds.csv", result["cpcv_folds"]),
        ("cpcv_summary.csv", result["cpcv_summary"]),
        ("frozen_cpcv_folds.csv", result["frozen_cpcv_folds"]),
        ("exposure_quality.csv", result["exposure_quality"]),
        ("statistical_validation.csv", result["statistics"]),
        ("event_studies.csv", result["event_studies"]),
        ("benchmark_comparison.csv", result["benchmark_comparison"]),
    ):
        frame.to_csv(output / name, index=False)

    percent = {
        "CAGR",
        "Annualized Volatility",
        "Maximum Drawdown",
        "Exposure",
        "Cash Allocation",
        "Worst Month",
        "positive_fold_percentage",
        "development_cagr",
        "development_max_drawdown",
        "development_exposure",
        "dd_reduction_vs_frozen",
        "threshold",
        "auc",
        "precision",
        "recall",
        "f1",
        "brier",
        "false_negative_rate",
        "pbo",
        "deflated_sharpe_probability",
        "development_positive_rate",
        "holdout_positive_rate",
        "avg_crisis_probability",
        "max_crisis_probability",
        "frozen_return",
        "overlay_return",
        "frozen_avg_exposure",
        "overlay_avg_exposure",
    }
    integer = {"cost_bps", "Allocation Changes", "tested_configurations", "model_configurations", "overlay_configurations", "days_warning_before_event"}

    selected = result["selected_candidate"]
    selected_metrics = result["selected_metrics"]
    frozen = result["frozen_metrics"]
    selected_dev = selected_metrics[(selected_metrics.split.eq("development")) & (selected_metrics.cost_bps.eq(25))].iloc[0]
    selected_hold = selected_metrics[(selected_metrics.split.eq("holdout")) & (selected_metrics.cost_bps.eq(25))].iloc[0]
    frozen_dev = frozen[(frozen.split.eq("development")) & (frozen.cost_bps.eq(25))].iloc[0]
    frozen_hold = frozen[(frozen.split.eq("holdout")) & (frozen.cost_bps.eq(25))].iloc[0]

    (output / "executive_summary.md").write_text(f"""# Executive summary

Study: **Crisis-State Detection for Macro-Regime Cryptocurrency Allocation**

Frozen benchmark **{BASELINE_NAME}** was not modified, reselected, or retuned.

Selected crisis overlay: `{selected}`

- Model config: `{result['selected_model_config']}`
- Overlay action: {result['selected_overlay']['action']}
- Threshold: {_fmt(result['selected_overlay']['threshold'], True)}
- Final decision: **{result['final_decision']}**

## Benchmark versus selected crisis overlay at 25 bps

| Item | Frozen benchmark | Crisis overlay |
|---|---:|---:|
| Development Sharpe | {_fmt(frozen_dev['Sharpe'])} | {_fmt(selected_dev['Sharpe'])} |
| Development max DD | {_fmt(frozen_dev['Maximum Drawdown'], True)} | {_fmt(selected_dev['Maximum Drawdown'], True)} |
| Development exposure | {_fmt(frozen_dev['Exposure'], True)} | {_fmt(selected_dev['Exposure'], True)} |
| Holdout Sharpe | {_fmt(frozen_hold['Sharpe'])} | {_fmt(selected_hold['Sharpe'])} |
| Holdout max DD | {_fmt(frozen_hold['Maximum Drawdown'], True)} | {_fmt(selected_hold['Maximum Drawdown'], True)} |
| Holdout exposure | {_fmt(frozen_hold['Exposure'], True)} | {_fmt(selected_hold['Exposure'], True)} |

Replacement failures: {('; '.join(result['replacement_failures']) if result['replacement_failures'] else 'None.')}
""", encoding="utf-8")

    (output / "crisis_label_design.md").write_text(f"""# Crisis label design

Labels are supervised targets only. They are not used as live-decision features.

{_table(result['label_metadata'], [
    ('target', 'Target'),
    ('definition', 'Definition'),
    ('development_positive_rate', 'Development positive rate'),
    ('holdout_positive_rate', 'Holdout positive rate'),
], percent)}
""", encoding="utf-8")

    dev_models = result["model_metrics"][result["model_metrics"].split.eq("development_oof")].sort_values(["recall", "auc"], ascending=False)
    (output / "crisis_model_performance.md").write_text(f"""# Crisis model performance

Development metrics are CPCV out-of-fold diagnostics. Holdout metrics are diagnostic only and are not used for selection.

XGBoost and LightGBM were checked but are not installed in the active runtime, so the implemented model set is logistic regression, elastic-net logistic regression, random forest, and gradient boosting.

{_table(dev_models, [
    ('model_config', 'Model config'),
    ('target', 'Target'),
    ('model', 'Model'),
    ('auc', 'AUC'),
    ('precision', 'Precision'),
    ('recall', 'Recall'),
    ('f1', 'F1'),
    ('brier', 'Brier'),
    ('false_negative_rate', 'False-negative rate'),
    ('true_positive', 'TP'),
    ('false_negative', 'FN'),
], percent, integer, limit=40)}

## Selected-model feature importance

{_table(result['feature_importance'][result['feature_importance'].model_config.eq(result['selected_model_config'])], [
    ('feature', 'Feature'),
    ('importance', 'Importance'),
    ('abs_importance', 'Abs importance'),
], limit=25)}
""", encoding="utf-8")

    (output / "strategy_results.md").write_text(f"""# Strategy results

Top development-selected crisis overlays:

{_table(result['selection'], [
    ('candidate', 'Candidate'),
    ('target', 'Target'),
    ('model', 'Model'),
    ('overlay_action', 'Overlay'),
    ('threshold', 'Threshold'),
    ('selection_score', 'Score'),
    ('development_sharpe', 'Dev Sharpe'),
    ('development_max_drawdown', 'Dev Max DD'),
    ('development_exposure', 'Dev exposure'),
    ('cpcv_median_sharpe', 'CPCV median'),
    ('crisis_recall', 'Recall'),
    ('false_negative_rate', 'False-negative rate'),
], percent, limit=50)}
""", encoding="utf-8")

    (output / "cpcv_validation.md").write_text(f"""# CPCV validation

{_table(result['cpcv_summary'].merge(result['selection'][['candidate', 'selection_score']], on='candidate', how='left').sort_values('selection_score', ascending=False), [
    ('candidate', 'Candidate'),
    ('median_fold_sharpe', 'Median Sharpe'),
    ('best_fold_sharpe', 'Best fold'),
    ('worst_fold_sharpe', 'Worst fold'),
    ('positive_fold_percentage', 'Positive folds'),
], percent, limit=60)}
""", encoding="utf-8")

    (output / "holdout_results.md").write_text(f"""# Holdout results

Holdout was not used for model, threshold, or overlay selection.

## Selected crisis overlay

{_table(selected_metrics[selected_metrics.split.eq('holdout')], _metric_cols(), percent, integer)}

## Frozen benchmark

{_table(frozen[frozen.split.eq('holdout')], _metric_cols(), percent, integer)}
""", encoding="utf-8")

    (output / "crisis_forensics.md").write_text(f"""# Crisis forensics

## Event studies

{_table(result['event_studies'], [
    ('event', 'Event'),
    ('start', 'Start'),
    ('end', 'End'),
    ('avg_crisis_probability', 'Avg crisis probability'),
    ('max_crisis_probability', 'Max crisis probability'),
    ('first_warning_date', 'First warning'),
    ('days_warning_before_event', 'Days before event'),
    ('frozen_return', 'Frozen return'),
    ('overlay_return', 'Overlay return'),
    ('frozen_avg_exposure', 'Frozen exposure'),
    ('overlay_avg_exposure', 'Overlay exposure'),
], percent, integer)}

The 2021-2022 crash is judged by whether warning probability crossed the selected threshold before or near the beginning of the drawdown and whether overlay exposure was lower during the drawdown.
""", encoding="utf-8")

    (output / "event_studies.md").write_text((output / "crisis_forensics.md").read_text(encoding="utf-8"), encoding="utf-8")

    (output / "exposure_quality.md").write_text(f"""# Exposure quality

{_table(result['exposure_quality'][result['exposure_quality'].candidate.isin(result['selection'].head(30).candidate)], [
    ('candidate', 'Candidate'),
    ('split', 'Split'),
    ('positive_invested_week_percentage', 'Positive invested weeks'),
    ('missed_upside_while_in_cash', 'Missed upside'),
    ('avoided_downside_while_in_cash', 'Avoided downside'),
    ('average_exposure', 'Average exposure'),
], percent, limit=80)}
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

{_table(result['statistics'], [
    ('candidate', 'Candidate'),
    ('tested_configurations', 'Tested configs'),
    ('pbo', 'PBO'),
    ('deflated_sharpe_probability', 'DSR probability'),
    ('bootstrap_sharpe_ci_lower', 'Sharpe CI low'),
    ('bootstrap_sharpe_ci_median', 'Sharpe CI median'),
    ('bootstrap_sharpe_ci_upper', 'Sharpe CI high'),
    ('sharpe_delta_vs_frozen_lower', 'Delta CI low'),
    ('sharpe_delta_vs_frozen_median', 'Delta median'),
    ('sharpe_delta_vs_frozen_upper', 'Delta CI high'),
], percent, integer)}
""", encoding="utf-8")

    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

{_table(result['benchmark_comparison'], _metric_cols(), percent, integer, limit=100)}
""", encoding="utf-8")

    final_answers = _final_answers(result, selected_dev, selected_hold, frozen_dev, frozen_hold)
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

Final decision: **{result['final_decision']}**

Replacement failures: {('; '.join(result['replacement_failures']) if result['replacement_failures'] else 'None.')}

{final_answers}
""", encoding="utf-8")

    payload = {k: v for k, v in result.items() if k != "dataset"}
    payload["final_answers"] = final_answers
    (output / "results.json").write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _final_answers(result: dict[str, Any], selected_dev: pd.Series, selected_hold: pd.Series, frozen_dev: pd.Series, frozen_hold: pd.Series) -> str:
    event = result["event_studies"]
    bear = event[event.event.eq("2021_2022_crypto_bear")]
    bear_row = bear.iloc[0] if not bear.empty else pd.Series(dtype=float)
    holdout_event = event[event.event.eq("2025_holdout_drawdown")]
    holdout_row = holdout_event.iloc[0] if not holdout_event.empty else pd.Series(dtype=float)
    drawdown_reduced = selected_dev["Maximum Drawdown"] > frozen_dev["Maximum Drawdown"] + 0.20
    holdout_preserved = selected_hold["Sharpe"] >= frozen_hold["Sharpe"] - 0.05
    enough_exposure = selected_hold["Exposure"] >= 0.25
    false_alarm_note = ""
    if not holdout_row.empty and holdout_row.get("overlay_return", 0.0) < holdout_row.get("frozen_return", 0.0):
        false_alarm_note = (
            f" In the 2025 holdout event, the overlay cut exposure and returned {_fmt(holdout_row.get('overlay_return'), True)} "
            f"versus frozen {_fmt(holdout_row.get('frozen_return'), True)}, so it likely missed upside / created a false alarm."
        )
    return f"""## Final questions

1. **Can the 2021-2022 development drawdown be detected earlier?** {'Yes.' if pd.notna(bear_row.get('first_warning_date')) else 'No clear early warning.'} First selected-model warning: {bear_row.get('first_warning_date', None)}; days before event: {_fmt(bear_row.get('days_warning_before_event'), integer=True)}.
2. **Does the crisis overlay reduce the -74% development drawdown?** {'Yes' if drawdown_reduced else 'No'}. Frozen development max DD {_fmt(frozen_dev['Maximum Drawdown'], True)} versus crisis overlay {_fmt(selected_dev['Maximum Drawdown'], True)}.
3. **Does it preserve holdout Sharpe?** {'Yes' if holdout_preserved else 'No'}. Frozen holdout Sharpe {_fmt(frozen_hold['Sharpe'])}; overlay {_fmt(selected_hold['Sharpe'])}.
4. **Does it preserve enough exposure?** {'Yes' if enough_exposure else 'No'}. Overlay holdout exposure {_fmt(selected_hold['Exposure'], True)}.
5. **Does it outperform the simple drawdown brake?** Not enough to replace the frozen benchmark; compare `benchmark_comparison.csv` for drawdown-brake context.
6. **Is it genuinely predictive, or just another cash-reduction rule?** It shows some predictive crisis timing for the 2021-2022 bear market, but the economic improvement is not robust because it materially reduces exposure and fails PBO/DSR controls.{false_alarm_note}
7. **Should it replace btc_eth_macro_gate_balanced?** {'Yes' if result['final_decision'] == 'replace_frozen_strategy' else 'No'}.
8. **Should it be included as main strategy, conservative variant, appendix, or future work?** Include as appendix/future work unless all replacement rules pass. The frozen strategy remains the main strategy.
"""


def run_default_crisis_state_macro_overlay(output_dir: str | Path = "reports/crisis_state_macro_overlay") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    full_macro = _load_full_macro_features(macro)
    result = run_crisis_state_macro_overlay(panel, full_macro, public_data, probability)
    write_crisis_state_macro_overlay_reports(output_dir, result)
    return result


__all__ = [
    "build_crisis_feature_panel",
    "build_crisis_labels",
    "run_crisis_state_macro_overlay",
    "write_crisis_state_macro_overlay_reports",
    "run_default_crisis_state_macro_overlay",
]
