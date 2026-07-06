"""Prediction-only study of seven-day cryptocurrency volatility expansion.

The module deliberately contains no portfolio or trading-strategy logic.  It builds
a point-in-time liquid universe, creates a forward volatility label, and evaluates
probabilistic classifiers with nested CPCV tuning inside walk-forward windows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import product
from math import erf, sqrt
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn import __version__ as sklearn_version
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .data import STABLE_OR_WRAPPED


HOLDOUT_START = pd.Timestamp("2025-01-01")
HOLDOUT_END = pd.Timestamp("2026-06-22")
LABEL_HORIZON = 7
HAR_FEATURES = ["har_log_rv_1", "har_log_rv_7", "har_log_rv_30"]
DERIVATIVE_COLUMNS = {
    "funding_rate",
    "open_interest",
    "basis",
    "liquidations",
    "long_liquidations",
    "short_liquidations",
}
OPTION_COLUMNS = {
    "atm_iv_7d",
    "atm_iv_30d",
    "put_call_skew_25d",
    "put_skew_25d",
    "iv_term_slope",
    "options_volume",
    "options_open_interest",
}


@dataclass
class VolatilityExpansionDataset:
    frame: pd.DataFrame
    feature_sets: dict[str, list[str]]
    feature_blocks: dict[str, list[str]]
    weights: pd.DataFrame
    universes: dict[pd.Timestamp, list[str]]
    metadata: dict[str, Any]


@dataclass
class VolatilityExpansionResult:
    predictions: pd.DataFrame
    metrics: pd.DataFrame
    calibration: pd.DataFrame
    feature_importance: pd.DataFrame
    selection_history: pd.DataFrame
    comparisons: pd.DataFrame
    availability: pd.DataFrame
    dataset: VolatilityExpansionDataset
    protocol: dict[str, Any]


def _capped_weights(values: pd.Series, cap: float) -> pd.Series:
    """Normalize non-negative values while respecting a per-asset cap."""
    values = values.clip(lower=0).dropna().astype(float)
    if values.empty or values.sum() <= 0:
        return pd.Series(dtype=float)
    weights = values / values.sum()
    free = pd.Series(True, index=weights.index)
    result = pd.Series(0.0, index=weights.index)
    for _ in range(len(weights) + 1):
        remaining = 1.0 - result.sum()
        if remaining <= 1e-12 or not free.any():
            break
        proposal = weights[free] / weights[free].sum() * remaining
        hit = proposal >= cap
        if not hit.any():
            result.loc[proposal.index] = proposal
            break
        capped_names = proposal.index[hit]
        result.loc[capped_names] = cap
        free.loc[capped_names] = False
    return result.clip(upper=cap)


def point_in_time_liquid_universe(
    panel: pd.DataFrame,
    top_n: int = 10,
    min_history_days: int = 180,
    liquidity_lookback_days: int = 90,
    completeness_lookback_days: int = 30,
    minimum_completeness: float = 0.90,
    max_asset_weight: float = 0.20,
) -> tuple[pd.DataFrame, dict[pd.Timestamp, list[str]]]:
    """Return weekly top-liquidity weights using observations strictly before each reset."""
    clean = panel.loc[~panel.symbol.isin(STABLE_OR_WRAPPED)].copy()
    close = clean.pivot(index="date", columns="symbol", values="close").sort_index()
    volume = clean.pivot(index="date", columns="symbol", values="volume").reindex_like(close)
    dollar_volume = close * volume

    history = close.notna().cumsum().shift(1).fillna(0)
    completeness = close.notna().rolling(completeness_lookback_days).mean().shift(1)
    liquidity = dollar_volume.rolling(
        liquidity_lookback_days,
        min_periods=max(20, completeness_lookback_days),
    ).median().shift(1)

    dates = close.index
    effective_dates = dates[dates.weekday == 0]
    if effective_dates.empty and len(dates):
        effective_dates = dates[::7]
    snapshots = pd.DataFrame(np.nan, index=dates, columns=close.columns, dtype=float)
    universes: dict[pd.Timestamp, list[str]] = {}
    for effective_date in effective_dates:
        eligible = (
            (history.loc[effective_date] >= min_history_days)
            & (completeness.loc[effective_date] >= minimum_completeness)
            & liquidity.loc[effective_date].notna()
        )
        ranking = liquidity.loc[effective_date, eligible].sort_values(ascending=False).head(top_n)
        members = ranking.index.tolist()
        universes[pd.Timestamp(effective_date)] = members
        snapshots.loc[effective_date] = 0.0
        if members:
            selected = _capped_weights(np.sqrt(ranking), max_asset_weight)
            snapshots.loc[effective_date, selected.index] = selected
    return snapshots.ffill().fillna(0.0), universes


def _weighted_mean(values: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    valid_weights = weights.where(values.notna(), 0.0)
    denominator = valid_weights.sum(axis=1).replace(0, np.nan)
    return (values.fillna(0.0) * valid_weights).sum(axis=1) / denominator


def _weighted_sum(values: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    return (values.fillna(0.0) * (weights > 0)).sum(axis=1)


def _weighted_dispersion(values: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    mean = _weighted_mean(values, weights)
    valid_weights = weights.where(values.notna(), 0.0)
    denominator = valid_weights.sum(axis=1).replace(0, np.nan)
    variance = ((values.sub(mean, axis=0) ** 2).fillna(0.0) * valid_weights).sum(axis=1) / denominator
    return np.sqrt(variance.clip(lower=0))


def _correlation_features(
    returns: pd.DataFrame,
    weights: pd.DataFrame,
    window: int = 30,
) -> tuple[pd.Series, pd.Series]:
    average = pd.Series(np.nan, index=returns.index, dtype=float)
    first_eigen_share = pd.Series(np.nan, index=returns.index, dtype=float)
    for position in range(window - 1, len(returns)):
        date_ = returns.index[position]
        members = weights.columns[weights.loc[date_] > 0]
        if len(members) < 2:
            continue
        sample = returns.iloc[position - window + 1 : position + 1][members]
        sample = sample.dropna(axis=1, thresh=max(10, window // 2))
        if sample.shape[1] < 2:
            continue
        corr = sample.corr(min_periods=max(10, window // 2)).fillna(0.0)
        corr_values = corr.to_numpy(copy=True)
        np.fill_diagonal(corr_values, 1.0)
        upper = corr_values[np.triu_indices(len(corr_values), 1)]
        average.at[date_] = float(np.nanmean(upper))
        eigenvalues = np.linalg.eigvalsh(corr_values)
        total = eigenvalues.clip(min=0).sum()
        if total > 0:
            first_eigen_share.at[date_] = float(eigenvalues[-1] / total)
    return average, first_eigen_share


def _pivot(panel: pd.DataFrame, column: str, like: pd.DataFrame) -> pd.DataFrame:
    return panel.pivot(index="date", columns="symbol", values=column).reindex(index=like.index, columns=like.columns)


def _price_and_liquidity_features(
    panel: pd.DataFrame,
    weights: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], list[str], pd.Series]:
    close = panel.pivot(index="date", columns="symbol", values="close").sort_index()
    close = close.reindex(index=weights.index, columns=weights.columns)
    high = _pivot(panel, "high", close)
    low = _pivot(panel, "low", close)
    volume = _pivot(panel, "volume", close)
    asset_returns = close.pct_change(fill_method=None)
    basket_return = _weighted_mean(asset_returns, weights)
    squared = basket_return.pow(2)
    epsilon = 1e-12

    features = pd.DataFrame(index=close.index)
    features["har_log_rv_1"] = np.log(squared + epsilon)
    features["har_log_rv_7"] = np.log(squared.rolling(7).mean() + epsilon)
    features["har_log_rv_30"] = np.log(squared.rolling(30).mean() + epsilon)
    features["rv_ratio_1_7"] = features["har_log_rv_1"] - features["har_log_rv_7"]
    features["rv_ratio_7_30"] = features["har_log_rv_7"] - features["har_log_rv_30"]
    downside = basket_return.where(basket_return < 0, 0.0).pow(2)
    upside = basket_return.where(basket_return > 0, 0.0).pow(2)
    features["log_downside_semivariance_7"] = np.log(downside.rolling(7).sum() + epsilon)
    features["log_upside_semivariance_7"] = np.log(upside.rolling(7).sum() + epsilon)
    features["jump_share_7"] = squared.rolling(7).max() / squared.rolling(7).sum().replace(0, np.nan)
    features["market_return_1"] = basket_return
    features["market_return_7"] = (1 + basket_return).rolling(7).apply(np.prod, raw=True) - 1
    features["market_return_30"] = (1 + basket_return).rolling(30).apply(np.prod, raw=True) - 1
    wealth = (1 + basket_return.fillna(0.0)).cumprod()
    features["market_drawdown"] = wealth / wealth.cummax() - 1

    momentum_20 = close.pct_change(20, fill_method=None)
    eligible = weights > 0
    features["breadth_20"] = ((momentum_20 > 0) & eligible).sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)
    cross_dispersion = _weighted_dispersion(asset_returns, weights)
    features["cross_sectional_dispersion_1"] = cross_dispersion
    features["cross_sectional_dispersion_7"] = cross_dispersion.rolling(7).mean()
    average_corr, first_eigen = _correlation_features(asset_returns, weights, 30)
    features["average_correlation_30"] = average_corr
    features["first_eigenvalue_share_30"] = first_eigen

    dollar_volume = close * volume
    aggregate_dollar_volume = _weighted_sum(dollar_volume, weights)
    features["log_dollar_volume"] = np.log1p(aggregate_dollar_volume)
    features["dollar_volume_change_1"] = features["log_dollar_volume"].diff()
    features["dollar_volume_change_7"] = features["log_dollar_volume"].diff(7)
    features["dollar_volume_change_30"] = features["log_dollar_volume"].diff(30)
    amihud = asset_returns.abs() / dollar_volume.replace(0, np.nan)
    features["amihud_illiquidity"] = np.log(_weighted_mean(amihud, weights).clip(lower=0) + epsilon)
    range_spread = (high - low) / close.replace(0, np.nan)
    features["high_low_spread"] = _weighted_mean(range_spread, weights)
    active_dollar_volume = dollar_volume.where(eligible)
    shares = active_dollar_volume.div(active_dollar_volume.sum(axis=1), axis=0)
    features["volume_concentration"] = shares.pow(2).sum(axis=1)
    features["zero_volume_share"] = ((volume <= 0) & eligible).sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)

    price_columns = [
        "har_log_rv_1", "har_log_rv_7", "har_log_rv_30", "rv_ratio_1_7", "rv_ratio_7_30",
        "log_downside_semivariance_7", "log_upside_semivariance_7", "jump_share_7",
        "market_return_1", "market_return_7", "market_return_30", "market_drawdown",
        "breadth_20", "cross_sectional_dispersion_1", "cross_sectional_dispersion_7",
        "average_correlation_30", "first_eigenvalue_share_30",
    ]
    liquidity_columns = [
        "log_dollar_volume", "dollar_volume_change_1", "dollar_volume_change_7",
        "dollar_volume_change_30", "amihud_illiquidity", "high_low_spread",
        "volume_concentration", "zero_volume_share",
    ]
    return features, price_columns, liquidity_columns, basket_return


def _available_columns(panel: pd.DataFrame, candidates: set[str]) -> list[str]:
    return sorted(column for column in candidates if column in panel.columns and panel[column].notna().any())


def _derivative_features(
    panel: pd.DataFrame,
    weights: pd.DataFrame,
    lag_days: int,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    close = panel.pivot(index="date", columns="symbol", values="close").reindex_like(weights)
    output = pd.DataFrame(index=weights.index)
    raw_available = _available_columns(panel, DERIVATIVE_COLUMNS)
    for column in raw_available:
        values = _pivot(panel, column, close).shift(lag_days)
        coverage = ((values.notna()) & (weights > 0)).sum(axis=1) / (weights > 0).sum(axis=1).replace(0, np.nan)
        output[f"deriv_{column}_coverage"] = coverage
        mean = _weighted_mean(values, weights)
        dispersion = _weighted_dispersion(values, weights)
        if column == "open_interest":
            level = _weighted_sum(values.clip(lower=0), weights)
            output["deriv_log_open_interest"] = np.log1p(level)
            output["deriv_open_interest_change_1"] = output["deriv_log_open_interest"].diff()
            output["deriv_open_interest_change_7"] = output["deriv_log_open_interest"].diff(7)
            output["deriv_open_interest_dispersion"] = dispersion
        elif column == "funding_rate":
            output["deriv_funding_mean"] = mean
            output["deriv_funding_abs"] = _weighted_mean(values.abs(), weights)
            output["deriv_funding_dispersion"] = dispersion
            output["deriv_funding_sum_3"] = mean.rolling(3).sum()
            output["deriv_funding_sum_7"] = mean.rolling(7).sum()
        elif column == "basis":
            output["deriv_basis_mean"] = mean
            output["deriv_basis_dispersion"] = dispersion
            output["deriv_basis_change_1"] = mean.diff()
            output["deriv_basis_change_7"] = mean.diff(7)
        else:
            total = _weighted_sum(values.clip(lower=0), weights)
            output[f"deriv_log_{column}"] = np.log1p(total)
            output[f"deriv_{column}_change_7"] = np.log1p(total).diff(7)
    if {"funding_rate", "open_interest"}.issubset(raw_available):
        output["deriv_funding_x_oi_growth"] = output["deriv_funding_abs"] * output["deriv_open_interest_change_7"]
    return output, output.columns.tolist(), raw_available


def _option_features(
    panel: pd.DataFrame,
    index: pd.Index,
    lag_days: int,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    output = pd.DataFrame(index=index)
    raw_available = _available_columns(panel, OPTION_COLUMNS)
    for column in raw_available:
        daily = panel.groupby("date")[column].median().reindex(index).shift(lag_days)
        output[f"option_{column}"] = daily
        if column in {"atm_iv_7d", "atm_iv_30d", "options_volume", "options_open_interest"}:
            output[f"option_{column}_change_7"] = daily.diff(7)
    if {"atm_iv_7d", "atm_iv_30d"}.issubset(raw_available):
        output["option_iv_term_slope_7_30"] = output["option_atm_iv_30d"] - output["option_atm_iv_7d"]
    return output, output.columns.tolist(), raw_available


def build_volatility_expansion_dataset(
    panel: pd.DataFrame,
    top_n: int = 10,
    alternative_data_lag_days: int = 1,
) -> VolatilityExpansionDataset:
    """Build features and labels without fitting transforms or using future features."""
    panel = panel.copy().sort_values(["date", "symbol"])
    panel["date"] = pd.to_datetime(panel["date"])
    weights, universes = point_in_time_liquid_universe(panel, top_n=top_n)
    features, price_columns, liquidity_columns, basket_return = _price_and_liquidity_features(panel, weights)
    derivative_frame, derivative_columns, raw_derivatives = _derivative_features(panel, weights, alternative_data_lag_days)
    option_frame, option_columns, raw_options = _option_features(panel, weights.index, alternative_data_lag_days)
    features = features.join(derivative_frame).join(option_frame)
    features = features.replace([np.inf, -np.inf], np.nan)

    squared = basket_return.pow(2)
    past_rv = squared.rolling(LABEL_HORIZON).sum()
    future_rv = squared.rolling(LABEL_HORIZON).sum().shift(-LABEL_HORIZON)
    label_end = pd.Series(weights.index, index=weights.index).shift(-LABEL_HORIZON)
    valid_target = future_rv.notna() & past_rv.gt(0)

    frame = features.copy()
    frame["past_rv_7"] = past_rv
    frame["future_rv_7"] = future_rv
    frame["current_log_rv"] = np.log(past_rv + 1e-12)
    frame["target_log_future_rv"] = np.log(future_rv + 1e-12)
    frame["target_expand"] = np.where(valid_target, (future_rv > past_rv).astype(int), np.nan)
    frame["label_end"] = label_end
    frame = frame.loc[frame.target_expand.notna() & frame[HAR_FEATURES].notna().all(axis=1)].copy()
    frame["target_expand"] = frame["target_expand"].astype(int)

    development = frame.index < HOLDOUT_START
    def usable(columns: Iterable[str]) -> list[str]:
        return [column for column in columns if frame.loc[development, column].notna().mean() >= 0.20]

    price_columns = usable(price_columns)
    liquidity_columns = usable(liquidity_columns)
    derivative_columns = usable(derivative_columns)
    option_columns = usable(option_columns)
    feature_blocks = {
        "price": price_columns,
        "liquidity": liquidity_columns,
        "derivatives": derivative_columns,
        "options": option_columns,
    }
    feature_sets = {
        "price_only": price_columns,
        "price_liquidity": price_columns + liquidity_columns,
    }
    if derivative_columns:
        feature_sets["price_derivatives"] = price_columns + derivative_columns
    if derivative_columns and option_columns:
        feature_sets["price_derivatives_options"] = price_columns + derivative_columns + option_columns

    active_universes = {date_: members for date_, members in universes.items() if members}
    all_members = sorted({member for members in active_universes.values() for member in members})
    metadata = {
        "target": "future 7-day basket realized variance exceeds trailing 7-day basket realized variance",
        "top_n": top_n,
        "start": str(frame.index.min().date()) if len(frame) else None,
        "end": str(frame.index.max().date()) if len(frame) else None,
        "observations": int(len(frame)),
        "positive_rate": float(frame.target_expand.mean()) if len(frame) else np.nan,
        "universe_rebalances": len(active_universes),
        "unique_assets": len(all_members),
        "raw_derivative_columns": raw_derivatives,
        "raw_option_columns": raw_options,
        "alternative_data_lag_days": alternative_data_lag_days,
        "holdout_start": str(HOLDOUT_START.date()),
        "holdout_end": str(HOLDOUT_END.date()),
        "frequency": "daily close prediction; weekly point-in-time universe refresh",
    }
    return VolatilityExpansionDataset(frame, feature_sets, feature_blocks, weights, universes, metadata)


def _positive_probability(model: Any, X: pd.DataFrame) -> np.ndarray:
    classes = list(model.classes_)
    if 1 not in classes:
        return np.zeros(len(X), dtype=float)
    return np.asarray(model.predict_proba(X)[:, classes.index(1)], dtype=float)


def _elastic_model(params: dict[str, Any]):
    version_parts = tuple(int(part) for part in sklearn_version.split(".")[:2])
    logistic_options: dict[str, Any] = {
        "solver": "saga",
        "C": float(params["C"]),
        "l1_ratio": float(params["l1_ratio"]),
        "max_iter": 5000,
        "tol": 1e-3,
        "random_state": 42,
    }
    if version_parts < (1, 8):
        logistic_options["penalty"] = "elasticnet"
    return make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(**logistic_options),
    )


def _boosting_backend() -> tuple[str, Any]:
    try:
        from xgboost import XGBClassifier
        return "xgboost", XGBClassifier
    except ImportError:
        try:
            from lightgbm import LGBMClassifier
            return "lightgbm", LGBMClassifier
        except ImportError as exc:
            raise ImportError(
                "The volatility-expansion study requires xgboost or lightgbm. "
                "Install project requirements before running the boosted-tree model."
            ) from exc


def _boosting_model(params: dict[str, Any]):
    backend, estimator = _boosting_backend()
    common = {
        "n_estimators": int(params["n_estimators"]),
        "max_depth": int(params["max_depth"]),
        "learning_rate": float(params["learning_rate"]),
        "subsample": 0.8,
        "random_state": 42,
        "n_jobs": 1,
    }
    if backend == "xgboost":
        common.update({"colsample_bytree": 0.8, "eval_metric": "logloss", "tree_method": "hist"})
    else:
        common.update({"colsample_bytree": 0.8, "verbosity": -1})
    return make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        estimator(**common),
    )


def _parameter_grid(model_name: str) -> list[dict[str, Any]]:
    if model_name == "elastic_net":
        return [
            {"C": c_value, "l1_ratio": ratio}
            for c_value, ratio in product((0.05, 0.20, 1.0), (0.10, 0.50, 0.90))
        ]
    if model_name == "boosted_tree":
        return [
            {"n_estimators": trees, "max_depth": depth, "learning_rate": rate}
            for trees, depth, rate in (
                (100, 2, 0.03), (200, 2, 0.05), (100, 3, 0.03), (200, 3, 0.05)
            )
        ]
    return [{}]


def _classifier(model_name: str, params: dict[str, Any]):
    if model_name == "elastic_net":
        return _elastic_model(params)
    if model_name == "boosted_tree":
        return _boosting_model(params)
    raise ValueError(f"Unknown classifier: {model_name}")


def _tune_classifier(
    X: pd.DataFrame,
    y: pd.Series,
    model_name: str,
    n_groups: int = 6,
) -> tuple[dict[str, Any], float]:
    if len(X) < 60 or y.nunique() < 2:
        raise ValueError("At least 60 observations and two classes are required for CPCV tuning")
    groups = min(n_groups, max(3, len(X) // 60))
    splits = combinatorial_purged_splits(
        len(X), n_groups=groups, n_test_groups=1,
        label_horizon=LABEL_HORIZON, embargo=LABEL_HORIZON,
    )
    candidates = []
    for params in _parameter_grid(model_name):
        losses = []
        for split in splits:
            train_indices = list(split.train_indices)
            test_indices = list(split.test_indices)
            y_train = y.iloc[train_indices]
            if y_train.nunique() < 2 or not test_indices:
                continue
            model = _classifier(model_name, params)
            model.fit(X.iloc[train_indices], y_train)
            probability = _positive_probability(model, X.iloc[test_indices])
            losses.append(brier_score_loss(y.iloc[test_indices], probability))
        if losses:
            candidates.append((float(np.mean(losses)), params))
    if not candidates:
        raise ValueError("CPCV tuning produced no valid folds")
    return min(candidates, key=lambda item: item[0])[1], min(item[0] for item in candidates)


def _normal_cdf(values: np.ndarray) -> np.ndarray:
    return np.array([0.5 * (1.0 + erf(float(value) / sqrt(2.0))) for value in values])


def _fit_har(
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> tuple[np.ndarray, pd.Series]:
    pipeline = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LinearRegression(),
    )
    pipeline.fit(train[HAR_FEATURES], train["target_log_future_rv"])
    fitted = pipeline.predict(train[HAR_FEATURES])
    residual_std = float(np.std(train["target_log_future_rv"].to_numpy() - fitted, ddof=len(HAR_FEATURES) + 1))
    residual_std = max(residual_std, 1e-6)
    forecast = pipeline.predict(test[HAR_FEATURES])
    probability = _normal_cdf((forecast - test["current_log_rv"].to_numpy()) / residual_std)
    estimator = pipeline[-1]
    importance = pd.Series(np.abs(estimator.coef_), index=HAR_FEATURES)
    return probability.clip(0, 1), importance


def _extract_importance(model: Any, feature_names: list[str]) -> pd.Series:
    estimator = model[-1]
    values = getattr(estimator, "feature_importances_", None)
    if values is None and hasattr(estimator, "coef_"):
        values = np.abs(np.asarray(estimator.coef_)).reshape(-1)
    if values is None:
        return pd.Series(dtype=float)
    return pd.Series(np.asarray(values, dtype=float), index=feature_names)


def _fit_candidate(
    train: pd.DataFrame,
    test: pd.DataFrame,
    model_name: str,
    feature_columns: list[str],
    params: dict[str, Any] | None = None,
) -> tuple[np.ndarray, pd.Series, Any]:
    if model_name == "har":
        probability, importance = _fit_har(train, test)
        return probability, importance, None
    params = params or _tune_classifier(train[feature_columns], train.target_expand, model_name)[0]
    model = _classifier(model_name, params)
    model.fit(train[feature_columns], train.target_expand)
    probability = _positive_probability(model, test[feature_columns])
    return probability, _extract_importance(model, feature_columns), model


def _candidate_pairs(
    dataset: VolatilityExpansionDataset,
    model_names: Iterable[str],
) -> list[tuple[str, str]]:
    pairs = []
    for model_name in model_names:
        if model_name == "har":
            pairs.append(("har", "price_only"))
        else:
            pairs.extend((model_name, feature_set) for feature_set in dataset.feature_sets)
    return pairs


def _prediction_rows(
    test: pd.DataFrame,
    probabilities: np.ndarray,
    split: str,
    model_name: str,
    feature_set: str,
    train_end: pd.Timestamp,
) -> pd.DataFrame:
    return pd.DataFrame({
        "date": test.index,
        "label_end": test.label_end.to_numpy(),
        "split": split,
        "model": model_name,
        "feature_set": feature_set,
        "target_expand": test.target_expand.to_numpy(dtype=int),
        "past_rv_7": test.past_rv_7.to_numpy(dtype=float),
        "future_rv_7": test.future_rv_7.to_numpy(dtype=float),
        "probability": probabilities,
        "prediction": (probabilities >= 0.5).astype(int),
        "train_end": train_end,
    })


def _metrics(frame: pd.DataFrame) -> dict[str, Any]:
    y = frame.target_expand.astype(int)
    probability = frame.probability.astype(float).clip(0, 1)
    prediction = (probability >= 0.5).astype(int)
    auc = float(roc_auc_score(y, probability)) if y.nunique() > 1 else np.nan
    return {
        "observations": int(len(frame)),
        "positive_rate": float(y.mean()),
        "auc": auc,
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "recall": float(recall_score(y, prediction, zero_division=0)),
        "brier_score": float(brier_score_loss(y, probability)),
        "mean_probability": float(probability.mean()),
    }


def _calibration_rows(predictions: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    rows = []
    for keys, group in predictions.groupby(["split", "model", "feature_set"], sort=True):
        if group.target_expand.nunique() < 2 or group.probability.nunique() < 2:
            continue
        fraction, mean_probability = calibration_curve(
            group.target_expand, group.probability,
            n_bins=min(bins, max(2, group.probability.nunique())), strategy="quantile",
        )
        for bin_number, (predicted, observed) in enumerate(zip(mean_probability, fraction), start=1):
            rows.append({
                "split": keys[0], "model": keys[1], "feature_set": keys[2],
                "bin": bin_number, "mean_predicted_probability": float(predicted),
                "observed_frequency": float(observed),
            })
    return pd.DataFrame(rows)


def _comparison_rows(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in sorted(predictions.split.unique()):
        split_frame = predictions[predictions.split == split]
        for model_name in ["elastic_net", "boosted_tree"]:
            model_frame = split_frame[split_frame.model == model_name]
            baseline = model_frame[model_frame.feature_set == "price_only"]
            if baseline.empty:
                continue
            for feature_set in sorted(set(model_frame.feature_set) - {"price_only"}):
                alternative = model_frame[model_frame.feature_set == feature_set]
                matched = baseline.merge(
                    alternative, on=["date", "target_expand"], suffixes=("_price", "_alternative")
                )
                if matched.empty:
                    continue
                price_metrics = _metrics(pd.DataFrame({
                    "target_expand": matched.target_expand,
                    "probability": matched.probability_price,
                }))
                alternative_metrics = _metrics(pd.DataFrame({
                    "target_expand": matched.target_expand,
                    "probability": matched.probability_alternative,
                }))
                delta_auc = alternative_metrics["auc"] - price_metrics["auc"]
                delta_brier = alternative_metrics["brier_score"] - price_metrics["brier_score"]
                rows.append({
                    "split": split,
                    "model": model_name,
                    "alternative_feature_set": feature_set,
                    "matched_observations": len(matched),
                    "price_auc": price_metrics["auc"],
                    "alternative_auc": alternative_metrics["auc"],
                    "delta_auc": delta_auc,
                    "price_brier": price_metrics["brier_score"],
                    "alternative_brier": alternative_metrics["brier_score"],
                    "delta_brier": delta_brier,
                    "improves_both": bool(delta_auc > 0 and delta_brier < 0),
                })
    return pd.DataFrame(rows)


def run_volatility_expansion_study(
    panel: pd.DataFrame,
    top_n: int = 10,
    holdout_start: str | pd.Timestamp = HOLDOUT_START,
    holdout_end: str | pd.Timestamp = HOLDOUT_END,
    min_training_days: int = 730,
    outer_test_months: int = 6,
    alternative_data_lag_days: int = 1,
    model_names: Iterable[str] = ("har", "elastic_net", "boosted_tree"),
) -> VolatilityExpansionResult:
    """Run nested development walk-forwards and one untouched final holdout."""
    holdout_start = pd.Timestamp(holdout_start)
    holdout_end = pd.Timestamp(holdout_end)
    dataset = build_volatility_expansion_dataset(panel, top_n, alternative_data_lag_days)
    frame = dataset.frame.loc[:holdout_end].copy()
    if frame.empty:
        raise ValueError("No eligible volatility-expansion observations were produced")
    pairs = _candidate_pairs(dataset, model_names)
    prediction_parts = []
    importance_parts = []
    selection_rows = []

    development = frame[frame.index < holdout_start]
    first_test = development.index.min() + pd.Timedelta(days=min_training_days)
    block_start = first_test
    while block_start < holdout_start:
        block_end = min(block_start + pd.DateOffset(months=outer_test_months), holdout_start)
        train = development[(development.index < block_start) & (development.label_end < block_start)]
        test = development[(development.index >= block_start) & (development.index < block_end)]
        if len(train) >= 60 and not test.empty and train.target_expand.nunique() > 1:
            for model_name, feature_set in pairs:
                feature_columns = HAR_FEATURES if model_name == "har" else dataset.feature_sets[feature_set]
                params: dict[str, Any] = {}
                cpcv_brier = np.nan
                if model_name != "har":
                    params, cpcv_brier = _tune_classifier(
                        train[feature_columns], train.target_expand, model_name
                    )
                probability, importance, _ = _fit_candidate(
                    train, test, model_name, feature_columns, params
                )
                prediction_parts.append(_prediction_rows(
                    test, probability, "development", model_name, feature_set, train.index.max()
                ))
                importance_parts.append(pd.DataFrame({
                    "split": "development", "refit_date": block_start,
                    "model": model_name, "feature_set": feature_set,
                    "feature": importance.index, "importance": importance.values,
                }))
                selection_rows.append({
                    "split": "development", "refit_date": block_start,
                    "test_end": block_end - pd.Timedelta(days=1),
                    "model": model_name, "feature_set": feature_set,
                    "parameters": params, "cpcv_brier": cpcv_brier,
                    "train_observations": len(train), "train_end": train.index.max(),
                    "max_train_label_end": train.label_end.max(),
                })
        block_start = block_end

    final_train = frame[(frame.index < holdout_start) & (frame.label_end < holdout_start)]
    holdout = frame[(frame.index >= holdout_start) & (frame.index <= holdout_end)]
    if holdout.empty:
        raise ValueError("The input has no matured labels in the locked 2025-2026 holdout")
    for model_name, feature_set in pairs:
        feature_columns = HAR_FEATURES if model_name == "har" else dataset.feature_sets[feature_set]
        params = {}
        cpcv_brier = np.nan
        if model_name != "har":
            params, cpcv_brier = _tune_classifier(
                final_train[feature_columns], final_train.target_expand, model_name
            )
        probability, importance, _ = _fit_candidate(
            final_train, holdout, model_name, feature_columns, params
        )
        prediction_parts.append(_prediction_rows(
            holdout, probability, "holdout", model_name, feature_set, final_train.index.max()
        ))
        importance_parts.append(pd.DataFrame({
            "split": "holdout", "refit_date": holdout_start,
            "model": model_name, "feature_set": feature_set,
            "feature": importance.index, "importance": importance.values,
        }))
        selection_rows.append({
            "split": "holdout", "refit_date": holdout_start,
            "test_end": holdout.index.max(), "model": model_name,
            "feature_set": feature_set, "parameters": params,
            "cpcv_brier": cpcv_brier, "train_observations": len(final_train),
            "train_end": final_train.index.max(),
            "max_train_label_end": final_train.label_end.max(),
        })

    predictions = pd.concat(prediction_parts, ignore_index=True)
    importance = pd.concat(importance_parts, ignore_index=True)
    selection = pd.DataFrame(selection_rows)
    metric_rows = []
    for keys, group in predictions.groupby(["split", "model", "feature_set"], sort=True):
        metric_rows.append({"split": keys[0], "model": keys[1], "feature_set": keys[2], **_metrics(group)})
    metrics = pd.DataFrame(metric_rows)
    calibration = _calibration_rows(predictions)
    comparisons = _comparison_rows(predictions)

    availability_rows = []
    for feature_set in ("price_only", "price_liquidity", "price_derivatives", "price_derivatives_options"):
        available = feature_set in dataset.feature_sets
        reason = "available"
        if not available and feature_set == "price_derivatives":
            reason = "no usable funding/open-interest/basis/liquidation columns in input"
        elif not available and feature_set == "price_derivatives_options":
            reason = "derivative and/or options columns are absent or below 20% development coverage"
        availability_rows.append({
            "feature_set": feature_set, "available": available,
            "feature_count": len(dataset.feature_sets.get(feature_set, [])), "reason": reason,
        })
    availability = pd.DataFrame(availability_rows)
    protocol = {
        "run_date": str(date.today()),
        "prediction_target": dataset.metadata["target"],
        "holdout_start": str(holdout_start.date()),
        "holdout_end": str(holdout_end.date()),
        "holdout_training_rule": "all labels end before holdout start; no holdout outcomes used for tuning",
        "outer_validation": f"expanding walk-forward with {outer_test_months}-month test blocks",
        "inner_tuning": "6-group CPCV, one test group, 7-observation purge horizon and embargo",
        "selection_metric": "minimum mean CPCV Brier score",
        "classification_threshold": 0.5,
        "models": list(model_names),
        "trading_strategy_built": False,
    }
    return VolatilityExpansionResult(
        predictions, metrics, calibration, importance, selection,
        comparisons, availability, dataset, protocol,
    )
