"""Locked walk-forward volatility-breakout research components."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import UniverseBuilder
from .metrics import performance_metrics
from .signals import _capped_long_only, _rebalance
from .strategies import price_matrix


MODEL_NAMES = ("logistic_regression", "random_forest", "gradient_boosting")
REJECTION_TARGETS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70)
LABEL_COLUMNS = ("label_after_costs", "label_vol_adjusted")


@dataclass
class BreakoutContext:
    panel: pd.DataFrame
    universes: dict[pd.Timestamp, list[str]]
    weights: pd.DataFrame
    strengths: pd.DataFrame
    features: dict[str, pd.DataFrame | pd.Series]
    eligible: pd.DataFrame
    returns: pd.DataFrame
    rebalance_dates: pd.DatetimeIndex
    events: pd.DataFrame


@dataclass
class FilterPredictions:
    events: pd.DataFrame
    selection_history: pd.DataFrame
    feature_importance: pd.Series
    first_prediction_date: pd.Timestamp | None


@dataclass
class BreakoutResult:
    returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    metrics: dict
    diagnostics: dict


def _model(name: str):
    if name == "logistic_regression":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(C=1.0, max_iter=750, class_weight="balanced", random_state=42),
        )
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=150, max_depth=6, min_samples_leaf=10,
            class_weight="balanced", random_state=42, n_jobs=-1,
        )
    if name == "gradient_boosting":
        return GradientBoostingClassifier(
            n_estimators=125, learning_rate=0.05, max_depth=2,
            min_samples_leaf=10, random_state=42,
        )
    raise ValueError(f"Unknown model: {name}")


def _positive_probability(model, X: pd.DataFrame) -> np.ndarray:
    classes = list(model.classes_)
    if 1 not in classes:
        return np.zeros(len(X))
    return model.predict_proba(X)[:, classes.index(1)]


def build_breakout_context(
    full_panel: pd.DataFrame,
    top_n: int = 10,
    rebalance_frequency: str = "W-FRI",
    max_asset_weight: float = 0.20,
    min_history_days: int = 90,
    baseline_cost_bps: int = 25,
) -> BreakoutContext:
    builder = UniverseBuilder(min_history_days=min_history_days)
    universes = builder.monthly_universe(full_panel, top_n)
    selected = sorted(set().union(*universes.values()))
    panel = full_panel[full_panel.symbol.isin(selected)].copy()
    px = price_matrix(panel)
    high = panel.pivot(index="date", columns="symbol", values="high").reindex_like(px)
    volume = panel.pivot(index="date", columns="symbol", values="volume").reindex_like(px)
    ret = px.pct_change(fill_method=None)
    eligible = builder.membership_mask(panel, universes).reindex_like(px).fillna(False)

    prior_close = px.shift(1)
    breakout_level = px.shift(2).rolling(20).max()
    daily_strength = (prior_close / breakout_level - 1).clip(lower=0)
    breakout_strength = daily_strength.rolling(7).max().where(eligible)
    raw = breakout_strength.where(breakout_strength > 0, 0.0).fillna(0.0)
    target = _capped_long_only(raw, max_asset_weight)
    weights, rebalance_dates = _rebalance(target, rebalance_frequency)

    realized_vol = ret.rolling(20).std().shift(1) * np.sqrt(365)
    volume_expansion = volume.shift(1) / volume.rolling(20).median().shift(2).replace(0, np.nan)
    trend_alignment = prior_close / px.rolling(100).mean().shift(1) - 1
    momentum_30 = px.pct_change(30, fill_method=None).shift(1)
    breadth = ((momentum_30 > 0) & eligible).sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)
    btc = px["BTC"] if "BTC" in px else px.iloc[:, 0]
    btc_trend = btc.pct_change(30, fill_method=None).shift(1)
    eligible_returns = ret.where(eligible)
    average_correlation = eligible_returns.rolling(60).corr().groupby(level=0).mean().mean(axis=1).shift(1)
    dispersion = eligible_returns.rolling(30).std().mean(axis=1).shift(1) * np.sqrt(365)

    preliminary = (weights.shift(1).fillna(0.0) * ret.fillna(0.0)).sum(axis=1)
    strategy_curve = (1 + preliminary).cumprod()
    strategy_drawdown = (strategy_curve / strategy_curve.cummax() - 1).shift(1)
    strategy_hit_rate = (preliminary > 0).rolling(56).mean().shift(1)
    features = {
        "breakout_strength": breakout_strength,
        "realized_volatility": realized_vol,
        "volume_expansion": volume_expansion,
        "trend_alignment": trend_alignment,
        "market_breadth": breadth,
        "btc_trend": btc_trend,
        "average_correlation": average_correlation,
        "cross_sectional_dispersion": dispersion,
        "recent_strategy_drawdown": strategy_drawdown,
        "recent_breakout_hit_rate": strategy_hit_rate,
    }
    if "funding_rate" in panel.columns:
        features["funding_rate"] = panel.pivot(index="date", columns="symbol", values="funding_rate").reindex_like(px).shift(1)

    events = build_breakout_events(
        px, weights, features, rebalance_dates, baseline_cost_bps, ret
    )
    return BreakoutContext(panel, universes, weights, breakout_strength, features, eligible, ret.fillna(0.0), rebalance_dates, events)


def build_breakout_events(
    px: pd.DataFrame,
    weights: pd.DataFrame,
    features: dict[str, pd.DataFrame | pd.Series],
    rebalance_dates: pd.DatetimeIndex,
    cost_bps: int,
    returns: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    dates = list(rebalance_dates)
    for position, date in enumerate(dates[:-1]):
        next_date = dates[position + 1]
        if date not in px.index or next_date not in px.index:
            continue
        active = weights.columns[weights.loc[date] > 0]
        holding_days = max((next_date - date).days, 1)
        for symbol in active:
            entry, exit_ = px.at[date, symbol], px.at[next_date, symbol]
            if pd.isna(entry) or pd.isna(exit_) or entry <= 0:
                continue
            forward_return = float(exit_ / entry - 1)
            forward_net = forward_return - 2 * cost_bps / 10000.0
            exante_daily_vol = returns[symbol].rolling(20).std().shift(1).at[date]
            vol_hurdle = 0.25 * exante_daily_vol * np.sqrt(holding_days) if pd.notna(exante_daily_vol) else np.nan
            row = {
                "date": date,
                "label_end": next_date,
                "symbol": symbol,
                "signal_weight": float(weights.at[date, symbol]),
                "forward_return": forward_return,
                "forward_net_return": forward_net,
                "label_after_costs": int(forward_net > 0),
                "label_vol_adjusted": int(pd.notna(vol_hurdle) and forward_net > vol_hurdle),
            }
            for name, value in features.items():
                if isinstance(value, pd.DataFrame):
                    row[name] = value.at[date, symbol]
                else:
                    row[name] = value.at[date]
            rows.append(row)
    frame = pd.DataFrame(rows)
    feature_columns = [name for name in features]
    frame[feature_columns] = frame[feature_columns].replace([np.inf, -np.inf], np.nan)
    return frame


def _event_validation_sharpe(frame: pd.DataFrame, accepted: np.ndarray) -> float:
    selected = frame.assign(accepted=accepted)
    by_date = selected.groupby("date").apply(
        lambda group: group.loc[group.accepted, "forward_net_return"].mean() if group.accepted.any() else 0.0,
        include_groups=False,
    )
    std = by_date.std()
    return float(by_date.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else -np.inf


def _accept_with_cap(probabilities: np.ndarray, threshold: float, max_rejection: float = 0.70) -> np.ndarray:
    accepted = probabilities >= threshold
    minimum = max(1, int(np.ceil(len(probabilities) * (1 - max_rejection))))
    if accepted.sum() < minimum:
        order = np.argsort(probabilities)[::-1]
        accepted[order[:minimum]] = True
    return accepted


def nested_walk_forward_filter(
    context: BreakoutContext,
    model_name: str,
    refit_frequency: str = "QS",
    training_lookback_days: int = 1095,
    min_train_events: int = 250,
) -> FilterPredictions:
    events = context.events.copy()
    feature_columns = list(context.features)
    prediction_rows = []
    selection_rows = []
    importance_rows = []
    fitted = None
    threshold = None
    selected_label = None
    selected_rejection = None
    last_refit_period = None
    first_prediction = None

    for date in sorted(events.date.unique()):
        date = pd.Timestamp(date)
        period = date.to_period("Q") if refit_frequency.upper().startswith("Q") else date.to_period(refit_frequency)
        if period != last_refit_period:
            train = events[
                (events.label_end < date)
                & (events.date >= date - pd.Timedelta(days=training_lookback_days))
            ].dropna(subset=feature_columns)
            if len(train) >= min_train_events:
                unique_dates = sorted(train.date.unique())
                split_date = pd.Timestamp(unique_dates[max(1, int(len(unique_dates) * 0.75)) - 1])
                inner_fit = train[train.date <= split_date]
                inner_validation = train[train.date > split_date]
                candidates = []
                for label_column in LABEL_COLUMNS:
                    if inner_fit[label_column].nunique() < 2 or inner_validation.empty:
                        continue
                    candidate_model = _model(model_name)
                    candidate_model.fit(inner_fit[feature_columns], inner_fit[label_column])
                    fit_probability = _positive_probability(candidate_model, inner_fit[feature_columns])
                    validation_probability = _positive_probability(candidate_model, inner_validation[feature_columns])
                    for rejection_target in REJECTION_TARGETS:
                        candidate_threshold = float(np.quantile(fit_probability, rejection_target))
                        accepted_parts = []
                        for _, group in inner_validation.assign(probability=validation_probability).groupby("date", sort=True):
                            accepted_parts.extend(_accept_with_cap(group.probability.to_numpy(), candidate_threshold, 0.70))
                        score = _event_validation_sharpe(inner_validation, np.asarray(accepted_parts, dtype=bool))
                        candidates.append((score, -rejection_target, label_column, rejection_target, candidate_threshold))
                if candidates:
                    score, _, selected_label, selected_rejection, _ = max(candidates)
                    fitted = _model(model_name)
                    fitted.fit(train[feature_columns], train[selected_label])
                    train_probability = _positive_probability(fitted, train[feature_columns])
                    threshold = float(np.quantile(train_probability, selected_rejection))
                    estimator = fitted[-1] if model_name == "logistic_regression" else fitted
                    raw_importance = getattr(estimator, "feature_importances_", None)
                    if raw_importance is None and hasattr(estimator, "coef_"):
                        raw_importance = np.abs(estimator.coef_).mean(axis=0)
                    if raw_importance is not None:
                        importance_rows.append(pd.Series(raw_importance, index=feature_columns, name=date))
                    selection_rows.append({
                        "refit_date": date,
                        "model": model_name,
                        "label": selected_label,
                        "rejection_target": selected_rejection,
                        "threshold": threshold,
                        "inner_validation_sharpe": score,
                        "train_events": len(train),
                        "inner_fit_end": split_date,
                    })
            last_refit_period = period

        current = events[events.date == date].dropna(subset=feature_columns)
        if fitted is None or current.empty:
            continue
        probabilities = _positive_probability(fitted, current[feature_columns])
        accepted = _accept_with_cap(probabilities, threshold, 0.70)
        if first_prediction is None:
            first_prediction = date
        for event, probability, accept in zip(current.itertuples(index=False), probabilities, accepted):
            prediction_rows.append({
                "date": date,
                "label_end": event.label_end,
                "symbol": event.symbol,
                "signal_weight": event.signal_weight,
                "forward_net_return": event.forward_net_return,
                "label_after_costs": event.label_after_costs,
                "label_vol_adjusted": event.label_vol_adjusted,
                "probability": float(probability),
                "accepted": bool(accept),
                "model": model_name,
                "selected_label": selected_label,
                "rejection_target": selected_rejection,
                "threshold": threshold,
            })
    importance = pd.concat(importance_rows, axis=1).mean(axis=1).sort_values(ascending=False) if importance_rows else pd.Series(dtype=float)
    return FilterPredictions(pd.DataFrame(prediction_rows), pd.DataFrame(selection_rows), importance, first_prediction)


def filtered_breakout_weights(
    context: BreakoutContext,
    predictions: FilterPredictions,
    mode: str,
    minimum_exposure_floor: float = 0.20,
    max_asset_weight: float = 0.20,
) -> pd.DataFrame:
    snapshots = pd.DataFrame(np.nan, index=context.weights.index, columns=context.weights.columns)
    prediction_dates = set(predictions.events.date.unique()) if not predictions.events.empty else set()
    for date in context.rebalance_dates:
        snapshots.loc[date] = 0.0
        base = context.weights.loc[date]
        active = base[base > 0]
        if active.empty:
            continue
        if date not in prediction_dates:
            continue
        current = predictions.events[predictions.events.date == date].set_index("symbol")
        common = active.index.intersection(current.index)
        if mode == "binary_filter":
            multiplier = current.loc[common, "accepted"].astype(float)
        elif mode in {"probability_weighted", "drawdown_aware", "volatility_targeted"}:
            multiplier = minimum_exposure_floor + (1 - minimum_exposure_floor) * current.loc[common, "probability"]
        else:
            raise ValueError(f"Unknown filter mode: {mode}")
        target = active.loc[common] * multiplier
        if target.sum() > 0 and target.sum() < minimum_exposure_floor:
            target *= minimum_exposure_floor / target.sum()
        snapshots.loc[date, common] = target.clip(upper=max_asset_weight)
    return snapshots.ffill().fillna(0.0)


def execute_breakout(
    context: BreakoutContext,
    decision_weights: pd.DataFrame,
    cost_bps: int = 25,
    volatility_scaling: bool = True,
    drawdown_brake: bool = True,
    target_volatility: float = 0.35,
    turnover_cap: float = 0.75,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> BreakoutResult:
    desired = decision_weights.reindex_like(context.returns).fillna(0.0).clip(lower=0)
    preliminary = (desired.shift(1).fillna(0.0) * context.returns).sum(axis=1)
    scale = pd.Series(1.0, index=desired.index)
    if volatility_scaling:
        realized = preliminary.rolling(30).std().shift(1) * np.sqrt(365)
        scale *= (target_volatility / realized.replace(0, np.nan)).clip(lower=0, upper=1).fillna(1.0)
    if drawdown_brake:
        curve = (1 + preliminary.fillna(0)).cumprod()
        drawdown = (curve / curve.cummax() - 1).shift(1).fillna(0)
        brake = pd.Series(1.0, index=desired.index)
        brake.loc[drawdown <= -0.10] = 0.50
        brake.loc[drawdown <= -0.20] = 0.25
        scale *= brake
    scale = scale.where(scale.index.isin(context.rebalance_dates)).ffill().fillna(1.0)
    desired = desired.mul(scale, axis=0)

    executed = pd.DataFrame(0.0, index=desired.index, columns=desired.columns)
    previous = pd.Series(0.0, index=desired.columns)
    for date in desired.index:
        target = desired.loc[date]
        change = target - previous
        turnover = float(change.abs().sum())
        if turnover > turnover_cap:
            target = previous + change * turnover_cap / turnover
        executed.loc[date] = target
        previous = target
    gross = (executed.shift(1).fillna(0.0) * context.returns).sum(axis=1)
    turnover = executed.diff().abs().sum(axis=1).fillna(executed.abs().sum(axis=1))
    costs = turnover * cost_bps / 10000.0
    net = gross - costs
    if start_date is not None:
        net, gross, turnover, costs, executed = [item.loc[pd.Timestamp(start_date):] for item in (net, gross, turnover, costs, executed)]
    if end_date is not None:
        net, gross, turnover, costs, executed = [item.loc[:pd.Timestamp(end_date)] for item in (net, gross, turnover, costs, executed)]
    wins, losses = net[net > 0], net[net < 0]
    diagnostics = {
        "number_of_trades": int((executed.diff().abs() > 1e-6).sum().sum()),
        "hit_rate": float((net > 0).mean()),
        "average_win": float(wins.mean()) if len(wins) else 0.0,
        "average_loss": float(losses.mean()) if len(losses) else 0.0,
        "turnover": float(turnover.mean()),
        "exposure": float((executed.sum(axis=1) > 1e-9).mean()),
        "average_gross_exposure": float(executed.sum(axis=1).mean()),
        "transaction_costs": float(costs.sum()),
    }
    return BreakoutResult(net, gross, executed, turnover, costs, performance_metrics(net, turnover, costs), diagnostics)


def block_bootstrap_sharpe_ci(returns: pd.Series, samples: int = 1000, block_length: int = 14, seed: int = 42) -> dict:
    values = returns.dropna().to_numpy()
    if len(values) < block_length * 2:
        return {"lower": np.nan, "median": np.nan, "upper": np.nan}
    rng = np.random.default_rng(seed)
    estimates = []
    blocks_needed = int(np.ceil(len(values) / block_length))
    max_start = len(values) - block_length
    for _ in range(samples):
        starts = rng.integers(0, max_start + 1, blocks_needed)
        sample = np.concatenate([values[start:start + block_length] for start in starts])[:len(values)]
        std = sample.std(ddof=1)
        estimates.append(sample.mean() / std * np.sqrt(365) if std else 0.0)
    lower, median, upper = np.quantile(estimates, [0.025, 0.5, 0.975])
    return {"lower": float(lower), "median": float(median), "upper": float(upper)}


def deflated_sharpe_probability(returns: pd.Series, tested_configurations: int) -> float:
    values = returns.dropna().to_numpy()
    if len(values) < 3 or values.std(ddof=1) == 0:
        return np.nan
    daily_sharpe = values.mean() / values.std(ddof=1)
    trials = max(tested_configurations, 2)
    euler_gamma = 0.5772156649
    sr_std = np.sqrt((1 - skew(values) * daily_sharpe + ((kurtosis(values, fisher=False) - 1) / 4) * daily_sharpe ** 2) / (len(values) - 1))
    expected_max = sr_std * (
        (1 - euler_gamma) * norm.ppf(1 - 1 / trials)
        + euler_gamma * norm.ppf(1 - 1 / (trials * np.e))
    )
    return float(norm.cdf((daily_sharpe - expected_max) / sr_std)) if sr_std > 0 else np.nan


def probability_backtest_overfitting(configuration_returns: pd.DataFrame, blocks: int = 8) -> float:
    data = configuration_returns.dropna(how="all").fillna(0.0)
    if len(data) < blocks or data.shape[1] < 2:
        return np.nan
    partitions = np.array_split(np.arange(len(data)), blocks)
    logits = []
    for train_blocks in combinations(range(blocks), blocks // 2):
        train_index = np.concatenate([partitions[i] for i in train_blocks])
        test_index = np.concatenate([partitions[i] for i in range(blocks) if i not in train_blocks])
        train_sharpe = data.iloc[train_index].mean() / data.iloc[train_index].std().replace(0, np.nan)
        winner = train_sharpe.idxmax()
        test_sharpe = data.iloc[test_index].mean() / data.iloc[test_index].std().replace(0, np.nan)
        rank = test_sharpe.rank(pct=True).loc[winner]
        rank = float(np.clip(rank, 1e-6, 1 - 1e-6))
        logits.append(np.log(rank / (1 - rank)))
    return float(np.mean(np.asarray(logits) <= 0))
