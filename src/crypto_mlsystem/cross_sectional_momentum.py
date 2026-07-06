"""Leakage-controlled cross-sectional cryptocurrency momentum research.

The module produces asset scores and tradable long-only weights.  Model tuning is
date-grouped CPCV inside each historical training window; the 2025+ holdout is
never used for feature, target, hyperparameter, or portfolio selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .metrics import performance_metrics
from .volatility_breakout import (
    block_bootstrap_sharpe_ci,
    deflated_sharpe_probability,
    probability_backtest_overfitting,
)
from .volatility_expansion import (
    _capped_weights,
    _correlation_features,
    _weighted_dispersion,
    _weighted_mean,
    point_in_time_liquid_universe,
)


HOLDOUT_START = pd.Timestamp("2025-01-01")
HOLDOUT_END = pd.Timestamp("2026-06-22")
COST_LEVELS = (10, 25, 50, 100)
TARGETS = {
    "forward_rank": "target_forward_rank",
    "residual_rank": "target_residual_rank",
    "top_quintile": "target_top_quintile",
    "risk_adjusted_rank": "target_risk_adjusted_rank",
}


@dataclass
class MomentumDataset:
    events: pd.DataFrame
    feature_sets: dict[str, list[str]]
    feature_blocks: dict[str, list[str]]
    weights: pd.DataFrame
    universes: dict[pd.Timestamp, list[str]]
    asset_returns: pd.DataFrame
    asset_volatility: pd.DataFrame
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Candidate:
    name: str
    model: str
    target: str
    feature_set: str = "all_features"


@dataclass
class PortfolioResult:
    returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    metrics: dict[str, float]
    diagnostics: dict[str, float]


@dataclass
class MomentumStudyResult:
    dataset: MomentumDataset
    scores: pd.DataFrame
    selection_history: pd.DataFrame
    feature_importance: pd.DataFrame
    metrics: pd.DataFrame
    primary_returns: pd.DataFrame
    champion: Candidate
    robustness: pd.DataFrame
    ablation: pd.DataFrame
    subperiods: pd.DataFrame
    statistics: dict[str, Any]
    protocol: dict[str, Any]


def _pivot(panel: pd.DataFrame, column: str, like: pd.DataFrame) -> pd.DataFrame:
    return panel.pivot(index="date", columns="symbol", values=column).reindex(index=like.index, columns=like.columns)


def _rolling_downside_volatility(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    downside = returns.where(returns < 0, 0.0)
    return downside.rolling(window).std() * np.sqrt(365)


def _market_features(
    close: pd.DataFrame,
    returns: pd.DataFrame,
    weights: pd.DataFrame,
    momentum_30: pd.DataFrame,
    volatility_probability: pd.Series | None,
) -> pd.DataFrame:
    eligible = weights > 0
    basket_return = _weighted_mean(returns, weights)
    market = pd.DataFrame(index=close.index)
    if "BTC" in close:
        market["market_btc_trend_30"] = close.BTC.pct_change(30, fill_method=None).shift(1)
    if "ETH" in close:
        market["market_eth_trend_30"] = close.ETH.pct_change(30, fill_method=None).shift(1)
    market["market_breadth_30"] = ((momentum_30 > 0) & eligible).sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)
    market["market_dispersion_7"] = _weighted_dispersion(returns, weights).rolling(7).mean().shift(1)
    average_corr, _ = _correlation_features(returns, weights, 30)
    market["market_average_correlation_30"] = average_corr.shift(1)
    market["market_realized_volatility_30"] = basket_return.rolling(30).std().shift(1) * np.sqrt(365)
    wealth = (1 + basket_return.fillna(0.0)).cumprod()
    market["market_drawdown"] = (wealth / wealth.cummax() - 1).shift(1)
    if volatility_probability is not None:
        market["market_volatility_expansion_probability"] = (
            volatility_probability.sort_index().reindex(close.index).ffill().shift(1)
        )
    return market


def build_momentum_dataset(
    panel: pd.DataFrame,
    top_n: int = 30,
    volatility_probability: pd.Series | None = None,
    min_history_days: int = 180,
) -> MomentumDataset:
    panel = panel.copy().sort_values(["date", "symbol"])
    panel["date"] = pd.to_datetime(panel.date)
    weights, universes = point_in_time_liquid_universe(
        panel, top_n=top_n, min_history_days=min_history_days,
    )
    close = panel.pivot(index="date", columns="symbol", values="close").reindex_like(weights)
    high = _pivot(panel, "high", close)
    volume = _pivot(panel, "volume", close)
    returns = close.pct_change(fill_method=None)
    lag_close = close.shift(1)
    eligible = weights > 0

    features: dict[str, pd.DataFrame] = {}
    for horizon in (7, 14, 30, 90):
        features[f"momentum_{horizon}"] = close.pct_change(horizon, fill_method=None).shift(1)
    features["momentum_30_ex_7"] = close.shift(8) / close.shift(31) - 1
    features["momentum_90_ex_7"] = close.shift(8) / close.shift(91) - 1
    realized_vol = returns.rolling(30).std().shift(1) * np.sqrt(365)
    features["realized_volatility_30"] = realized_vol
    features["downside_volatility_30"] = _rolling_downside_volatility(returns, 30).shift(1)
    rolling_peak = lag_close.rolling(90).max()
    current_drawdown = lag_close / rolling_peak - 1
    features["max_drawdown_90"] = current_drawdown.rolling(90).min()
    dollar_volume = close * volume
    log_dollar_volume = np.log1p(dollar_volume.rolling(30).median().shift(1))
    features["log_dollar_volume_30"] = log_dollar_volume
    features["volume_growth_7_30"] = np.log1p(dollar_volume.rolling(7).mean().shift(1)) - np.log1p(
        dollar_volume.rolling(30).mean().shift(1)
    )
    features["amihud_illiquidity_30"] = np.log(
        (returns.abs() / dollar_volume.replace(0, np.nan)).rolling(30).mean().shift(1) + 1e-12
    )
    features["volatility_adjusted_momentum"] = features["momentum_30"] / realized_vol.replace(0, np.nan)
    features["distance_ma_20"] = lag_close / close.rolling(20).mean().shift(1) - 1
    features["distance_ma_100"] = lag_close / close.rolling(100).mean().shift(1) - 1
    features["distance_ma_200"] = lag_close / close.rolling(200).mean().shift(1) - 1
    features["breakout_strength_20"] = lag_close / high.rolling(20).max().shift(2) - 1
    features["reversal_7"] = -features["momentum_7"]
    age = close.notna().cumsum().shift(1)
    features["asset_age_days"] = np.log1p(age)
    features["recent_listing_flag"] = ((age >= min_history_days) & (age < min_history_days + 90)).astype(float)

    derivative_columns = []
    if "funding_rate" in panel.columns and panel.funding_rate.notna().any():
        funding = _pivot(panel, "funding_rate", close).shift(1)
        features["funding_rate"] = funding
        features["funding_rate_abs"] = funding.abs()
        features["funding_rate_change_7"] = funding.diff(7)
        features["funding_coverage_flag"] = funding.notna().astype(float)
        derivative_columns = [
            "funding_rate", "funding_rate_abs", "funding_rate_change_7", "funding_coverage_flag"
        ]

    price_columns = [
        "momentum_7", "momentum_14", "momentum_30", "momentum_90",
        "momentum_30_ex_7", "momentum_90_ex_7", "realized_volatility_30",
        "downside_volatility_30", "max_drawdown_90", "volatility_adjusted_momentum",
        "distance_ma_20", "distance_ma_100", "distance_ma_200", "breakout_strength_20", "reversal_7",
        "asset_age_days", "recent_listing_flag",
    ]
    liquidity_columns = ["log_dollar_volume_30", "volume_growth_7_30", "amihud_illiquidity_30"]
    market = _market_features(close, returns, weights, features["momentum_30"], volatility_probability)
    market_columns = market.columns.tolist()

    rebalance_dates = close.resample("W-FRI").last().index.intersection(close.index)
    rows = []
    close_dates = list(close.index)
    position_by_date = {date_: position for position, date_ in enumerate(close_dates)}
    for rebalance_date in rebalance_dates:
        position = position_by_date[rebalance_date]
        if position + 7 >= len(close_dates):
            continue
        future_date = close_dates[position + 7]
        members = weights.columns[weights.loc[rebalance_date] > 0]
        if not len(members):
            continue
        forward = close.loc[future_date, members] / close.loc[rebalance_date, members] - 1
        universe_return = float(forward.mean(skipna=True))
        provisional = []
        for symbol in members:
            value = forward.get(symbol, np.nan)
            if pd.isna(value):
                continue
            signal_volatility = realized_vol.at[rebalance_date, symbol]
            if pd.isna(signal_volatility) or signal_volatility <= 0:
                signal_volatility = np.nan
            row: dict[str, Any] = {
                "date": rebalance_date,
                "label_end": future_date,
                "symbol": symbol,
                "forward_return": float(value),
                "forward_residual_return": float(value - universe_return),
                "forward_risk_adjusted_return": float(value / signal_volatility),
            }
            for name, matrix in features.items():
                row[name] = matrix.at[rebalance_date, symbol]
            for name in market_columns:
                row[name] = market.at[rebalance_date, name]
            provisional.append(row)
        if not provisional:
            continue
        weekly = pd.DataFrame(provisional)
        weekly["target_forward_rank"] = weekly.forward_return.rank(pct=True, method="average")
        weekly["target_residual_rank"] = weekly.forward_residual_return.rank(pct=True, method="average")
        weekly["target_top_quintile"] = (weekly.target_forward_rank > 0.80).astype(int)
        weekly["target_risk_adjusted_rank"] = weekly.forward_risk_adjusted_return.rank(pct=True, method="average")
        rows.extend(weekly.to_dict("records"))
    events = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)

    feature_blocks = {
        "price": price_columns,
        "liquidity": liquidity_columns,
        "market": market_columns,
        "derivatives": derivative_columns,
    }
    development = events.date < HOLDOUT_START
    def usable(columns: Iterable[str]) -> list[str]:
        return [column for column in columns if events.loc[development, column].notna().mean() >= 0.20]
    feature_blocks = {name: usable(columns) for name, columns in feature_blocks.items()}
    feature_sets = {
        "price_only": feature_blocks["price"],
        "price_liquidity": feature_blocks["price"] + feature_blocks["liquidity"],
        "price_market": feature_blocks["price"] + feature_blocks["market"],
    }
    if feature_blocks["derivatives"]:
        feature_sets["price_derivatives"] = feature_blocks["price"] + feature_blocks["derivatives"]
    feature_sets["all_features"] = list(dict.fromkeys(sum(feature_blocks.values(), [])))
    active_universes = {date_: members for date_, members in universes.items() if members}
    unique_members = sorted({symbol for members in active_universes.values() for symbol in members})
    missingness = float(close.isna().mean().mean())
    metadata = {
        "top_n": top_n,
        "start": str(events.date.min().date()),
        "end": str(events.label_end.max().date()),
        "event_rows": int(len(events)),
        "rebalance_observations": int(events.date.nunique()),
        "unique_historical_members": len(unique_members),
        "missingness_full_price_matrix": missingness,
        "derivatives_available": bool(derivative_columns),
        "residual_rank_equals_forward_rank": bool(
            np.allclose(events.target_forward_rank, events.target_residual_rank, equal_nan=True)
        ),
    }
    return MomentumDataset(events, feature_sets, feature_blocks, weights, universes, returns.fillna(0.0), realized_vol, metadata)


def primary_candidates(feature_set: str = "all_features") -> list[Candidate]:
    candidates = []
    for target in ("forward_rank", "residual_rank", "risk_adjusted_rank"):
        for model in ("elastic_net", "random_forest", "gradient_boosting", "boosted_tree"):
            candidates.append(Candidate(f"{model}__{target}", model, target, feature_set))
        candidates.append(Candidate(f"ensemble__{target}", "ensemble", target, feature_set))
    for model in ("logistic", "random_forest", "gradient_boosting", "boosted_tree"):
        candidates.append(Candidate(f"{model}__top_quintile", model, "top_quintile", feature_set))
    return candidates


def _boosting_backend():
    try:
        from xgboost import XGBClassifier, XGBRegressor
        return XGBClassifier, XGBRegressor
    except ImportError as exc:
        raise ImportError("xgboost is required for the cross-sectional momentum study") from exc


def _parameter_grid(model: str) -> list[dict[str, Any]]:
    grids = {
        "elastic_net": [{"alpha": 0.001, "l1_ratio": 0.10}, {"alpha": 0.01, "l1_ratio": 0.50}],
        "logistic": [{"C": 0.10}, {"C": 1.0}],
        "random_forest": [{"max_depth": 4, "min_samples_leaf": 20}, {"max_depth": 7, "min_samples_leaf": 10}],
        "gradient_boosting": [{"n_estimators": 75, "max_depth": 2}, {"n_estimators": 150, "max_depth": 2}],
        "boosted_tree": [{"n_estimators": 75, "max_depth": 2}, {"n_estimators": 150, "max_depth": 3}],
    }
    return grids[model]


def _model(model: str, classification: bool, params: dict[str, Any]):
    if model == "elastic_net":
        return make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            StandardScaler(),
            ElasticNet(alpha=params["alpha"], l1_ratio=params["l1_ratio"], max_iter=5000, random_state=42),
        )
    if model == "logistic":
        return make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            StandardScaler(),
            LogisticRegression(C=params["C"], max_iter=2000, random_state=42),
        )
    if model == "random_forest":
        cls = RandomForestClassifier if classification else RandomForestRegressor
        return make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            cls(n_estimators=125, max_depth=params["max_depth"], min_samples_leaf=params["min_samples_leaf"], n_jobs=-1, random_state=42),
        )
    if model == "gradient_boosting":
        cls = GradientBoostingClassifier if classification else GradientBoostingRegressor
        return make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            cls(n_estimators=params["n_estimators"], max_depth=params["max_depth"], learning_rate=0.04, min_samples_leaf=15, random_state=42),
        )
    if model == "boosted_tree":
        classifier, regressor = _boosting_backend()
        cls = classifier if classification else regressor
        options = {
            "n_estimators": params["n_estimators"], "max_depth": params["max_depth"],
            "learning_rate": 0.04, "subsample": 0.8, "colsample_bytree": 0.8,
            "n_jobs": 1, "random_state": 42, "tree_method": "hist",
        }
        if classification:
            options["eval_metric"] = "logloss"
        return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), cls(**options))
    raise ValueError(f"Unknown model: {model}")


def _predict(model, X: pd.DataFrame, classification: bool) -> np.ndarray:
    if classification:
        classes = list(model[-1].classes_)
        return model.predict_proba(X)[:, classes.index(1)] if 1 in classes else np.zeros(len(X))
    return np.asarray(model.predict(X), dtype=float)


def _mean_date_ic(frame: pd.DataFrame, prediction: np.ndarray, target_column: str) -> float:
    scored = frame[["date", target_column]].copy()
    scored["score"] = prediction
    correlations = scored.groupby("date", group_keys=False).apply(
        lambda group: group.score.corr(group[target_column], method="spearman")
    )
    return float(correlations.mean()) if correlations.notna().any() else -1.0


def tune_candidate(
    train: pd.DataFrame,
    candidate: Candidate,
    feature_columns: list[str],
) -> tuple[dict[str, Any], float]:
    if candidate.model == "ensemble":
        raise ValueError("Ensemble parameters come from its component models")
    target_column = TARGETS[candidate.target]
    classification = candidate.target == "top_quintile"
    unique_dates = pd.DatetimeIndex(sorted(train.date.unique()))
    groups = min(4, max(3, len(unique_dates) // 20))
    splits = combinatorial_purged_splits(
        len(unique_dates), n_groups=groups, n_test_groups=1, label_horizon=1, embargo=1
    )
    scored_params = []
    for params in _parameter_grid(candidate.model):
        scores = []
        for split in splits:
            train_dates = set(unique_dates[list(split.train_indices)])
            test_dates = set(unique_dates[list(split.test_indices)])
            fit = train[train.date.isin(train_dates)]
            validation = train[train.date.isin(test_dates)]
            if fit.empty or validation.empty or (classification and fit[target_column].nunique() < 2):
                continue
            estimator = _model(candidate.model, classification, params)
            estimator.fit(fit[feature_columns], fit[target_column])
            prediction = _predict(estimator, validation[feature_columns], classification)
            if classification:
                scores.append(-brier_score_loss(validation[target_column], prediction))
            else:
                scores.append(_mean_date_ic(validation, prediction, target_column))
        if scores:
            scored_params.append((float(np.mean(scores)), params))
    if not scored_params:
        raise ValueError(f"No valid CPCV folds for {candidate.name}")
    return max(scored_params, key=lambda item: item[0])[1], max(item[0] for item in scored_params)


def _extract_importance(estimator, feature_columns: list[str]) -> pd.Series:
    final = estimator[-1]
    values = getattr(final, "feature_importances_", None)
    if values is None and hasattr(final, "coef_"):
        values = np.abs(np.asarray(final.coef_)).reshape(-1)
    return pd.Series(values, index=feature_columns) if values is not None else pd.Series(dtype=float)


def walk_forward_candidate_scores(
    dataset: MomentumDataset,
    candidates: list[Candidate],
    holdout_start: pd.Timestamp = HOLDOUT_START,
    holdout_end: pd.Timestamp = HOLDOUT_END,
    minimum_training_weeks: int = 26,
    tune_yearly: bool = True,
    fixed_parameters: dict[str, dict[str, Any]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, dict[str, Any]]]:
    events = dataset.events.copy()
    all_dates = pd.DatetimeIndex(sorted(events.date.unique()))
    development_dates = all_dates[all_dates < holdout_start]
    first_prediction = development_dates[min(minimum_training_weeks, len(development_dates) - 1)]
    quarter_starts = pd.date_range(first_prediction, holdout_start, freq="QS")
    score_parts, selection_rows, importance_parts = [], [], []
    latest_params: dict[str, dict[str, Any]] = dict(fixed_parameters or {})
    last_tuned_year: dict[str, int] = {}

    def fit_block(block_start: pd.Timestamp, block_end: pd.Timestamp, split_name: str, final_holdout: bool = False):
        train = events[(events.date < block_start) & (events.label_end < block_start)]
        test = events[(events.date >= block_start) & (events.date < block_end)]
        if train.date.nunique() < minimum_training_weeks or test.empty:
            return
        component_predictions: dict[tuple[str, str], pd.DataFrame] = {}
        for candidate in [item for item in candidates if item.model != "ensemble"]:
            features = dataset.feature_sets[candidate.feature_set]
            should_tune = candidate.name not in latest_params
            if tune_yearly and last_tuned_year.get(candidate.name) != block_start.year:
                should_tune = candidate.name not in (fixed_parameters or {})
            if should_tune:
                params, cpcv_score = tune_candidate(train, candidate, features)
                latest_params[candidate.name] = params
                last_tuned_year[candidate.name] = block_start.year
            else:
                params = latest_params[candidate.name]
                cpcv_score = np.nan
            target_column = TARGETS[candidate.target]
            classification = candidate.target == "top_quintile"
            estimator = _model(candidate.model, classification, params)
            estimator.fit(train[features], train[target_column])
            prediction = _predict(estimator, test[features], classification)
            scored = test[["date", "label_end", "symbol"]].copy()
            scored["candidate"] = candidate.name
            scored["model"] = candidate.model
            scored["target"] = candidate.target
            scored["feature_set"] = candidate.feature_set
            scored["score"] = prediction
            scored["split"] = split_name
            score_parts.append(scored)
            component_predictions[(candidate.model, candidate.target)] = scored[["date", "symbol", "score"]]
            importance = _extract_importance(estimator, features)
            importance_parts.append(pd.DataFrame({
                "refit_date": block_start, "split": split_name, "candidate": candidate.name,
                "feature": importance.index, "importance": importance.values,
            }))
            selection_rows.append({
                "refit_date": block_start, "test_end": block_end - pd.Timedelta(days=1),
                "split": split_name, "candidate": candidate.name, "parameters": params,
                "cpcv_score": cpcv_score, "train_rows": len(train),
                "train_dates": train.date.nunique(), "max_train_label_end": train.label_end.max(),
            })
        for candidate in [item for item in candidates if item.model == "ensemble"]:
            elastic = component_predictions.get(("elastic_net", candidate.target))
            gradient = component_predictions.get(("gradient_boosting", candidate.target))
            if elastic is None or gradient is None:
                continue
            merged = elastic.merge(gradient, on=["date", "symbol"], suffixes=("_elastic", "_gradient"))
            for column in ("score_elastic", "score_gradient"):
                merged[column] = merged.groupby("date")[column].rank(pct=True)
            merged["score"] = merged[["score_elastic", "score_gradient"]].mean(axis=1)
            merged["candidate"] = candidate.name
            merged["model"] = "ensemble"
            merged["target"] = candidate.target
            merged["feature_set"] = candidate.feature_set
            merged["split"] = split_name
            # Recover label_end from the event panel.
            merged = merged.merge(events[["date", "symbol", "label_end"]], on=["date", "symbol"], how="left")
            score_parts.append(merged[["date", "label_end", "symbol", "candidate", "model", "target", "feature_set", "score", "split"]])

    for position, block_start in enumerate(quarter_starts[:-1]):
        block_end = min(quarter_starts[position + 1], holdout_start)
        fit_block(block_start, block_end, "development")
    # Final fit is tuned on pre-holdout data only and then frozen for the full holdout.
    latest_params = dict(fixed_parameters or {})
    last_tuned_year = {}
    fit_block(holdout_start, holdout_end + pd.Timedelta(days=1), "holdout", True)
    return (
        pd.concat(score_parts, ignore_index=True),
        pd.DataFrame(selection_rows),
        pd.concat(importance_parts, ignore_index=True),
        latest_params,
    )


def momentum_baseline_scores(dataset: MomentumDataset) -> pd.DataFrame:
    events = dataset.events
    return pd.DataFrame({
        "date": events.date, "label_end": events.label_end, "symbol": events.symbol,
        "candidate": "pure_momentum", "model": "baseline", "target": "momentum_90_ex_7",
        "feature_set": "price_only", "score": events.momentum_90_ex_7,
        "split": np.where(events.date < HOLDOUT_START, "development", "holdout"),
    })


def scores_to_portfolio(
    dataset: MomentumDataset,
    scores: pd.DataFrame,
    top_k: int = 5,
    cost_bps: int = 25,
    rebalance: str = "weekly",
    weighting: str = "equal",
    max_asset_weight: float = 0.20,
    turnover_cap: float = 0.75,
    volatility_targeting: bool = False,
    drawdown_brake: bool = False,
) -> PortfolioResult:
    dates = pd.DatetimeIndex(sorted(scores.date.unique()))
    if rebalance == "biweekly":
        dates = dates[::2]
    snapshots = pd.DataFrame(np.nan, index=dataset.asset_returns.index, columns=dataset.asset_returns.columns)
    for date_ in dates:
        current = scores[scores.date == date_].dropna(subset=["score"]).sort_values("score", ascending=False).head(top_k)
        target = pd.Series(0.0, index=snapshots.columns)
        if not current.empty:
            selected = current.symbol.tolist()
            if weighting == "volatility_scaled":
                inverse = 1 / dataset.asset_volatility.loc[date_, selected].replace(0, np.nan)
                chosen = _capped_weights(inverse, max_asset_weight)
            else:
                chosen = _capped_weights(pd.Series(1.0, index=selected), max_asset_weight)
            target.loc[chosen.index] = chosen
        snapshots.loc[date_] = target
    desired = snapshots.ffill().fillna(0.0)

    if volatility_targeting:
        preliminary = (desired.shift(1).fillna(0.0) * dataset.asset_returns).sum(axis=1)
        realized = preliminary.rolling(30).std().shift(1) * np.sqrt(365)
        scale = (0.35 / realized.replace(0, np.nan)).clip(lower=0, upper=1).fillna(1.0)
        scale = scale.where(scale.index.isin(dates)).ffill().fillna(1.0)
        desired = desired.mul(scale, axis=0)
    if drawdown_brake:
        preliminary = (desired.shift(1).fillna(0.0) * dataset.asset_returns).sum(axis=1)
        wealth = (1 + preliminary.fillna(0)).cumprod()
        drawdown = (wealth / wealth.cummax() - 1).shift(1).fillna(0)
        scale = pd.Series(1.0, index=desired.index)
        scale.loc[drawdown <= -0.10] = 0.50
        scale.loc[drawdown <= -0.20] = 0.25
        scale = scale.where(scale.index.isin(dates)).ffill().fillna(1.0)
        desired = desired.mul(scale, axis=0)

    executed = pd.DataFrame(0.0, index=desired.index, columns=desired.columns)
    previous = pd.Series(0.0, index=desired.columns)
    for date_ in desired.index:
        target = desired.loc[date_]
        change = target - previous
        turnover = float(change.abs().sum())
        if turnover > turnover_cap:
            target = previous + change * turnover_cap / turnover
        executed.loc[date_] = target
        previous = target
    gross = (executed.shift(1).fillna(0.0) * dataset.asset_returns).sum(axis=1)
    turnover = executed.diff().abs().sum(axis=1).fillna(executed.abs().sum(axis=1))
    costs = turnover * cost_bps / 10000.0
    net = gross - costs
    active_start, active_end = scores.date.min(), scores.label_end.max()
    net, gross, turnover, costs, executed = [item.loc[active_start:active_end] for item in (net, gross, turnover, costs, executed)]
    metrics = performance_metrics(net, turnover, costs)
    metrics["Exposure"] = float((executed.sum(axis=1) > 1e-9).mean())
    monthly = net.resample("ME").apply(lambda values: (1 + values).prod() - 1)
    diagnostics = {
        "average_holdings": float((executed > 1e-6).sum(axis=1).mean()),
        "best_month": float(monthly.max()) if len(monthly) else np.nan,
        "worst_month": float(monthly.min()) if len(monthly) else np.nan,
    }
    return PortfolioResult(net, gross, executed, turnover, costs, metrics, diagnostics)


def benchmark_portfolio(
    dataset: MomentumDataset,
    name: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    cost_bps: int,
) -> PortfolioResult:
    scores = []
    dates = pd.DatetimeIndex(sorted(dataset.events.date.unique()))
    for date_ in dates:
        if name == "btc_buy_hold":
            symbols = ["BTC"]
        elif name == "eth_buy_hold":
            symbols = ["ETH"]
        elif name == "btc_eth_50_50":
            symbols = ["BTC", "ETH"]
        elif name == "equal_weight_top30":
            symbols = dataset.events.loc[dataset.events.date == date_, "symbol"].tolist()
        else:
            raise ValueError(name)
        for symbol in symbols:
            if symbol in dataset.asset_returns:
                scores.append({"date": date_, "label_end": date_ + pd.Timedelta(days=7), "symbol": symbol, "score": 1.0})
    top_k = 30 if name == "equal_weight_top30" else len(set(row["symbol"] for row in scores))
    benchmark_cap = {"btc_buy_hold": 1.0, "eth_buy_hold": 1.0, "btc_eth_50_50": 0.50}.get(name, 0.20)
    return scores_to_portfolio(
        dataset,
        pd.DataFrame(scores),
        top_k=top_k,
        cost_bps=cost_bps,
        max_asset_weight=benchmark_cap,
    )


def period_metrics(result: PortfolioResult, start: str | pd.Timestamp, end: str | pd.Timestamp) -> dict[str, float]:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    returns = result.returns.loc[start:end]
    metrics = performance_metrics(returns, result.turnover.reindex(returns.index), result.costs.reindex(returns.index))
    weights = result.weights.reindex(returns.index)
    metrics["Exposure"] = float((weights.sum(axis=1) > 1e-9).mean())
    monthly = returns.resample("ME").apply(lambda values: (1 + values).prod() - 1)
    metrics.update({
        "Average Holdings": float((weights > 1e-6).sum(axis=1).mean()),
        "Best Month": float(monthly.max()) if len(monthly) else np.nan,
        "Worst Month": float(monthly.min()) if len(monthly) else np.nan,
    })
    return metrics


def paired_sharpe_delta_ci(
    baseline: pd.Series,
    candidate: pd.Series,
    samples: int = 1000,
    block_length: int = 14,
    seed: int = 42,
) -> dict[str, float]:
    aligned = pd.concat([baseline.rename("baseline"), candidate.rename("candidate")], axis=1).dropna()
    rng = np.random.default_rng(seed)
    blocks = int(np.ceil(len(aligned) / block_length))
    starts = np.arange(max(1, len(aligned) - block_length + 1))
    deltas = []
    for _ in range(samples):
        indices = np.concatenate([
            np.arange(start, min(start + block_length, len(aligned)))
            for start in rng.choice(starts, blocks, replace=True)
        ])[: len(aligned)]
        sample = aligned.iloc[indices]
        def sharpe(values):
            return values.mean() / values.std() * np.sqrt(365) if values.std() else 0.0
        deltas.append(sharpe(sample.candidate) - sharpe(sample.baseline))
    lower, median, upper = np.quantile(deltas, [0.025, 0.5, 0.975])
    return {"lower": float(lower), "median": float(median), "upper": float(upper)}
