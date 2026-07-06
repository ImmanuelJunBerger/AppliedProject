"""Strategy-allocation and portfolio execution for real-data experiments."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .metrics import performance_metrics
from .signals import SignalBundle
from .strategies import price_matrix


@dataclass
class AllocationResult:
    weights: pd.DataFrame
    confidences: pd.Series
    feature_importance: pd.Series
    first_prediction_date: pd.Timestamp | None


@dataclass
class PortfolioResult:
    returns: pd.Series
    gross_returns: pd.Series
    asset_weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    metrics: dict
    diagnostics: dict


def build_allocator_features(panel: pd.DataFrame, bundle: SignalBundle, strategy_returns: pd.DataFrame) -> pd.DataFrame:
    px = price_matrix(panel)
    ret = px.pct_change(fill_method=None).where(bundle.eligible)
    market_return = ret.mean(axis=1)
    features = pd.DataFrame(index=px.index)
    features["market_volatility_30"] = market_return.rolling(30).std() * np.sqrt(365)
    positive_breadth = (px.pct_change(30, fill_method=None) > 0) & bundle.eligible
    features["market_breadth_30"] = positive_breadth.sum(axis=1) / bundle.eligible.sum(axis=1).replace(0, np.nan)
    features["market_dispersion_30"] = ret.rolling(30).std().mean(axis=1)
    features["market_correlation_60"] = ret.rolling(60).corr().groupby(level=0).mean().mean(axis=1)
    features["market_momentum_30"] = px.pct_change(30, fill_method=None).where(bundle.eligible).mean(axis=1)
    features["market_momentum_90"] = px.pct_change(90, fill_method=None).where(bundle.eligible).mean(axis=1)
    market_curve = (1 + market_return.fillna(0)).cumprod()
    features["market_drawdown"] = market_curve / market_curve.cummax() - 1
    for name in strategy_returns:
        series = strategy_returns[name]
        features[f"strategy_return_28__{name}"] = series.rolling(28).mean()
        features[f"strategy_volatility_28__{name}"] = series.rolling(28).std()
        features[f"strategy_hit_rate_28__{name}"] = (series > 0).rolling(28).mean()
        curve = (1 + series.fillna(0)).cumprod()
        features[f"strategy_drawdown__{name}"] = curve / curve.cummax() - 1
    return features.shift(1).replace([np.inf, -np.inf], np.nan).dropna()


def walk_forward_strategy_allocator(
    features: pd.DataFrame,
    strategy_returns: pd.DataFrame,
    prediction_frequency: str = "W-FRI",
    train_min_days: int = 180,
    label_horizon_days: int = 7,
    max_strategy_weight: float = 0.45,
    confidence_floor: float = 0.30,
    feature_columns: list[str] | None = None,
    strategies: list[str] | None = None,
) -> AllocationResult:
    strategies = strategies or list(strategy_returns.columns)
    future = strategy_returns[strategies].rolling(label_horizon_days).sum().shift(-label_horizon_days)
    valid = future.notna().any(axis=1)
    targets = pd.Series(pd.NA, index=future.index, dtype="object")
    targets.loc[valid] = future.loc[valid].idxmax(axis=1)
    columns = feature_columns or list(features.columns)
    index = features.index.intersection(targets.dropna().index)
    X = features.loc[index, columns]
    y = targets.loc[index]
    prediction_dates = X.resample(prediction_frequency).last().index.intersection(X.index)
    rows = []
    confidence_rows = []
    importance_rows = []
    first_prediction = None
    for date in prediction_dates:
        train_index = X.index[X.index < date - pd.Timedelta(days=label_horizon_days)]
        if len(train_index) < train_min_days or y.loc[train_index].nunique() < 2:
            continue
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=750, class_weight="balanced", random_state=42),
        )
        model.fit(X.loc[train_index], y.loc[train_index])
        probabilities = pd.Series(0.0, index=strategies, name=date)
        predicted = model.predict_proba(X.loc[[date]])[0]
        probabilities.loc[model.classes_] = predicted
        confidence = float(probabilities.max())
        confidence_scale = float(np.clip((confidence - 0.20) / max(confidence_floor - 0.20, 1e-9), 0, 1))
        probabilities = probabilities.clip(upper=max_strategy_weight) * confidence_scale
        rows.append(probabilities)
        confidence_rows.append((date, confidence))
        importance_rows.append(pd.Series(np.abs(model[-1].coef_).mean(axis=0), index=columns, name=date))
        first_prediction = first_prediction or date
    weights = pd.DataFrame(rows, columns=strategies).fillna(0.0)
    confidence_series = pd.Series(dict(confidence_rows), name="confidence", dtype=float)
    importance = pd.concat(importance_rows, axis=1).mean(axis=1).sort_values(ascending=False) if importance_rows else pd.Series(dtype=float)
    return AllocationResult(weights, confidence_series, importance, first_prediction)


def constant_strategy_allocations(index: pd.DatetimeIndex, strategy_names: list[str]) -> pd.DataFrame:
    return pd.DataFrame(1 / len(strategy_names), index=index, columns=strategy_names)


def execute_portfolio(
    bundle: SignalBundle,
    strategy_weights: dict[str, pd.DataFrame],
    strategy_allocations: pd.DataFrame,
    cost_bps: int = 25,
    max_asset_weight: float = 0.10,
    target_volatility: float = 0.35,
    turnover_cap: float = 0.75,
    start_date: pd.Timestamp | None = None,
) -> PortfolioResult:
    index = bundle.asset_returns.index
    allocations = strategy_allocations.reindex(index).ffill().fillna(0.0)
    desired = pd.DataFrame(0.0, index=index, columns=bundle.asset_returns.columns)
    for strategy, weights in strategy_weights.items():
        if strategy in allocations:
            desired += weights.reindex_like(desired).fillna(0.0).mul(allocations[strategy], axis=0)
    desired = desired.clip(lower=0, upper=max_asset_weight)

    preliminary = (desired.shift(1).fillna(0.0) * bundle.asset_returns).sum(axis=1)
    realized_vol = preliminary.rolling(30).std().shift(1) * np.sqrt(365)
    scale = (target_volatility / realized_vol.replace(0, np.nan)).clip(lower=0, upper=1).fillna(1.0)
    scale = scale.where(scale.index.isin(bundle.rebalance_dates)).ffill().fillna(1.0)
    desired = desired.mul(scale, axis=0)

    executed = pd.DataFrame(0.0, index=index, columns=desired.columns)
    previous = pd.Series(0.0, index=desired.columns)
    for date in index:
        target = desired.loc[date]
        change = target - previous
        turnover = float(change.abs().sum())
        if turnover > turnover_cap:
            target = previous + change * (turnover_cap / turnover)
        executed.loc[date] = target
        previous = target

    gross = (executed.shift(1).fillna(0.0) * bundle.asset_returns).sum(axis=1)
    turnover = executed.diff().abs().sum(axis=1).fillna(executed.abs().sum(axis=1))
    costs = turnover * cost_bps / 10000.0
    net = gross - costs
    if start_date is not None:
        net = net.loc[start_date:]
        gross = gross.loc[start_date:]
        turnover = turnover.loc[start_date:]
        costs = costs.loc[start_date:]
        executed = executed.loc[start_date:]
    wins = net[net > 0]
    losses = net[net < 0]
    trade_changes = executed.diff().abs() > 1e-6
    diagnostics = {
        "number_of_trades": int(trade_changes.sum().sum()),
        "hit_rate": float((net > 0).mean()),
        "average_win": float(wins.mean()) if len(wins) else 0.0,
        "average_loss": float(losses.mean()) if len(losses) else 0.0,
        "turnover": float(turnover.mean()),
        "exposure": float((executed.sum(axis=1) > 1e-9).mean()),
        "average_gross_exposure": float(executed.sum(axis=1).mean()),
        "transaction_costs": float(costs.sum()),
    }
    return PortfolioResult(net, gross, executed, turnover, costs, performance_metrics(net, turnover, costs), diagnostics)
