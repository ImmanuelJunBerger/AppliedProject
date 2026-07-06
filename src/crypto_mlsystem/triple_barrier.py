"""Volatility-scaled triple-barrier labels and walk-forward meta-label filtering."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .signals import SignalBundle
from .strategies import price_matrix


@dataclass
class MetaLabelResult:
    weights: dict[str, pd.DataFrame]
    events: pd.DataFrame
    confidences: pd.Series
    feature_importance: pd.Series
    rejected_percentage: float
    first_prediction_date: pd.Timestamp | None


def triple_barrier_events(
    panel: pd.DataFrame,
    bundle: SignalBundle,
    profit_taking: float = 1.5,
    stop_loss: float = 1.0,
    vertical_days: int = 14,
) -> pd.DataFrame:
    """Label active signal events using first barrier touched after the event date."""
    px = price_matrix(panel)
    high = panel.pivot(index="date", columns="symbol", values="high").reindex_like(px)
    low = panel.pivot(index="date", columns="symbol", values="low").reindex_like(px)
    daily_vol = px.pct_change(fill_method=None).rolling(20, min_periods=10).std().shift(1)
    positions = {date: i for i, date in enumerate(px.index)}
    rows = []
    for strategy, weights in bundle.weights.items():
        strength = bundle.strengths[strategy]
        for date in bundle.rebalance_dates:
            if date not in positions:
                continue
            start = positions[date]
            end = min(len(px.index) - 1, start + vertical_days)
            if end <= start:
                continue
            active = weights.columns[weights.loc[date] > 0]
            for symbol in active:
                entry = px.at[date, symbol]
                sigma = daily_vol.at[date, symbol]
                if pd.isna(entry) or pd.isna(sigma) or entry <= 0 or sigma <= 0:
                    continue
                upper = entry * (1 + profit_taking * sigma)
                lower = entry * (1 - stop_loss * sigma)
                outcome = "vertical"
                label_end = px.index[end]
                label = None
                exit_price = px.at[label_end, symbol]
                for offset in range(start + 1, end + 1):
                    event_date = px.index[offset]
                    touched_stop = pd.notna(low.at[event_date, symbol]) and low.at[event_date, symbol] <= lower
                    touched_profit = pd.notna(high.at[event_date, symbol]) and high.at[event_date, symbol] >= upper
                    if touched_stop:
                        label, outcome, label_end, exit_price = 0, "stop_loss", event_date, lower
                        break
                    if touched_profit:
                        label, outcome, label_end, exit_price = 1, "profit_taking", event_date, upper
                        break
                if label is None:
                    label = int(pd.notna(exit_price) and exit_price > entry)
                rows.append({
                    "date": date,
                    "label_end": label_end,
                    "strategy": strategy,
                    "symbol": symbol,
                    "label": label,
                    "outcome": outcome,
                    "barrier_return": float(exit_price / entry - 1) if pd.notna(exit_price) else np.nan,
                    "signal_weight": float(weights.at[date, symbol]),
                    "signal_strength": float(strength.at[date, symbol]),
                    "volatility_at_entry": float(sigma),
                })
    return pd.DataFrame(rows)


def build_meta_features(panel: pd.DataFrame, bundle: SignalBundle, strategy_returns: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    px = price_matrix(panel)
    ret = px.pct_change(fill_method=None)
    volume = panel.pivot(index="date", columns="symbol", values="volume").reindex_like(px)
    eligible_ret = ret.where(bundle.eligible)
    market = pd.DataFrame(index=px.index)
    market["market_volatility_30"] = eligible_ret.mean(axis=1).rolling(30).std().shift(1) * np.sqrt(365)
    positive_breadth = (px.pct_change(30, fill_method=None).shift(1) > 0) & bundle.eligible
    market["market_breadth_30"] = positive_breadth.sum(axis=1) / bundle.eligible.sum(axis=1).replace(0, np.nan)
    market["market_dispersion_30"] = eligible_ret.rolling(30).std().mean(axis=1).shift(1)
    market["market_correlation_60"] = eligible_ret.rolling(60).corr().groupby(level=0).mean().mean(axis=1).shift(1)
    market_curve = (1 + eligible_ret.mean(axis=1).fillna(0)).cumprod()
    market["market_drawdown"] = (market_curve / market_curve.cummax() - 1).shift(1)

    asset_features = {
        "asset_momentum_7": px.pct_change(7, fill_method=None).shift(1),
        "asset_momentum_30": px.pct_change(30, fill_method=None).shift(1),
        "asset_momentum_90": px.pct_change(90, fill_method=None).shift(1),
        "asset_volatility_20": ret.rolling(20).std().shift(1) * np.sqrt(365),
        "asset_drawdown_90": (px / px.rolling(90).max() - 1).shift(1),
        "asset_volume_growth_30": volume.pct_change(30).shift(1),
    }
    health = pd.DataFrame(index=strategy_returns.index)
    for name in strategy_returns:
        series = strategy_returns[name]
        health[f"health_return_28__{name}"] = series.rolling(28).mean().shift(1)
        health[f"health_volatility_28__{name}"] = series.rolling(28).std().shift(1)
        curve = (1 + series.fillna(0)).cumprod()
        health[f"health_drawdown__{name}"] = (curve / curve.cummax() - 1).shift(1)

    records = []
    for event in events.itertuples(index=False):
        row = {
            "date": event.date,
            "label_end": event.label_end,
            "strategy": event.strategy,
            "symbol": event.symbol,
            "label": event.label,
            "signal_weight": event.signal_weight,
            "signal_strength": event.signal_strength,
            "volatility_at_entry": event.volatility_at_entry,
        }
        for column in market:
            row[column] = market.at[event.date, column]
        for name, frame in asset_features.items():
            row[name] = frame.at[event.date, event.symbol]
        row["strategy_health_return_28"] = health.at[event.date, f"health_return_28__{event.strategy}"]
        row["strategy_health_volatility_28"] = health.at[event.date, f"health_volatility_28__{event.strategy}"]
        row["strategy_health_drawdown"] = health.at[event.date, f"health_drawdown__{event.strategy}"]
        records.append(row)
    frame = pd.DataFrame(records)
    frame = pd.concat([frame, pd.get_dummies(frame["strategy"], prefix="strategy", dtype=float)], axis=1)
    excluded = {"date", "label_end", "strategy", "symbol", "label"}
    feature_columns = [column for column in frame.columns if column not in excluded]
    frame[feature_columns] = frame[feature_columns].replace([np.inf, -np.inf], np.nan)
    return frame, feature_columns


def walk_forward_meta_filter(
    bundle: SignalBundle,
    meta_frame: pd.DataFrame,
    feature_columns: list[str],
    acceptance_threshold: float = 0.55,
    min_train_events: int = 250,
    training_lookback_days: int = 730,
) -> MetaLabelResult:
    filtered_snapshots = {
        name: pd.DataFrame(np.nan, index=weights.index, columns=weights.columns)
        for name, weights in bundle.weights.items()
    }
    predictions = []
    importance_rows = []
    last_fit_month = None
    model = None
    first_prediction_date = None

    for date in bundle.rebalance_dates:
        date = pd.Timestamp(date)
        for snapshot in filtered_snapshots.values():
            snapshot.loc[date] = 0.0
        month = date.to_period("M")
        if month != last_fit_month:
            train = meta_frame[
                (meta_frame.label_end < date)
                & (meta_frame.date >= date - pd.Timedelta(days=training_lookback_days))
            ].dropna(subset=feature_columns + ["label"])
            if len(train) >= min_train_events and train.label.nunique() >= 2:
                model = make_pipeline(
                    StandardScaler(),
                    LogisticRegression(max_iter=500, class_weight="balanced", random_state=42),
                )
                model.fit(train[feature_columns], train.label.astype(int))
            last_fit_month = month

        current = meta_frame[meta_frame.date == date].dropna(subset=feature_columns)
        if model is None or current.empty:
            continue
        probabilities = model.predict_proba(current[feature_columns])[:, list(model.classes_).index(1)]
        if first_prediction_date is None:
            first_prediction_date = date
        estimator = model[-1]
        importance_rows.append(pd.Series(np.abs(estimator.coef_[0]), index=feature_columns, name=date))
        for event, probability in zip(current.itertuples(index=False), probabilities):
            accepted = bool(probability >= acceptance_threshold)
            if accepted:
                filtered_snapshots[event.strategy].at[date, event.symbol] = bundle.weights[event.strategy].at[date, event.symbol]
            predictions.append({
                "date": date,
                "strategy": event.strategy,
                "symbol": event.symbol,
                "label": int(event.label),
                "confidence": float(probability),
                "accepted": accepted,
            })

    filtered = {name: snapshot.ffill().fillna(0.0) for name, snapshot in filtered_snapshots.items()}
    prediction_frame = pd.DataFrame(predictions)
    confidence = prediction_frame.confidence if not prediction_frame.empty else pd.Series(dtype=float)
    importance = pd.concat(importance_rows, axis=1).mean(axis=1).sort_values(ascending=False) if importance_rows else pd.Series(dtype=float)
    rejected = float((~prediction_frame.accepted).mean()) if not prediction_frame.empty else 1.0
    return MetaLabelResult(filtered, prediction_frame, confidence, importance, rejected, first_prediction_date)
