"""Predictive and strategy evaluation for the independent derivatives study."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .derivatives_features import DerivativesResearchDataset
from .metrics import performance_metrics


HOLDOUT_START = pd.Timestamp("2025-01-01")
HOLDOUT_END = pd.Timestamp("2026-06-22")
COST_LEVELS = (10, 25, 50, 100)


@dataclass(frozen=True)
class PredictiveCandidate:
    target: str
    model: str
    feature_set: str

    @property
    def name(self) -> str:
        return f"{self.target}__{self.model}__{self.feature_set}"


@dataclass
class SpotOutcome:
    returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series


def predictive_candidates(dataset: DerivativesResearchDataset) -> list[PredictiveCandidate]:
    frame = dataset.frame
    development = frame.date < HOLDOUT_START
    targets = []
    for name, column in dataset.target_columns.items():
        subset = frame.loc[development & frame[column].notna(), column]
        if len(subset) >= 200 and subset.nunique() == 2 and subset.value_counts().min() >= 25:
            targets.append(name)
    candidates = []
    for target in targets:
        candidates.extend([
            PredictiveCandidate(target, "logistic", "price_only"),
            PredictiveCandidate(target, "elastic_net", "price_only"),
        ])
        for feature_set, model in product(
            ("derivatives_only", "price_derivatives"),
            ("logistic", "elastic_net", "random_forest", "gradient_boosting", "boosted_tree"),
        ):
            if dataset.feature_sets[feature_set]:
                candidates.append(PredictiveCandidate(target, model, feature_set))
    return candidates


def _grid(model: str) -> list[dict[str, Any]]:
    return {
        "logistic": [{"C": 0.1}, {"C": 1.0}],
        "elastic_net": [{"C": 0.1, "l1_ratio": 0.25}, {"C": 1.0, "l1_ratio": 0.75}],
        "random_forest": [{"max_depth": 4, "min_samples_leaf": 20}, {"max_depth": 7, "min_samples_leaf": 10}],
        "gradient_boosting": [{"n_estimators": 75, "max_depth": 2}, {"n_estimators": 125, "max_depth": 2}],
        "boosted_tree": [{"n_estimators": 75, "max_depth": 2}, {"n_estimators": 125, "max_depth": 3}],
    }[model]


def _model(name: str, params: dict[str, Any]):
    if name == "logistic":
        return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(), LogisticRegression(
            C=params["C"], max_iter=2000, class_weight="balanced", random_state=42,
        ))
    if name == "elastic_net":
        return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(), LogisticRegression(
            C=params["C"], penalty="elasticnet", solver="saga", l1_ratio=params["l1_ratio"],
            max_iter=3000, class_weight="balanced", random_state=42,
        ))
    if name == "random_forest":
        return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), RandomForestClassifier(
            n_estimators=150, max_depth=params["max_depth"], min_samples_leaf=params["min_samples_leaf"],
            class_weight="balanced", n_jobs=-1, random_state=42,
        ))
    if name == "gradient_boosting":
        return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), GradientBoostingClassifier(
            n_estimators=params["n_estimators"], max_depth=params["max_depth"], learning_rate=0.04,
            min_samples_leaf=15, random_state=42,
        ))
    if name == "boosted_tree":
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:  # pragma: no cover
            raise ImportError("xgboost is required for boosted_tree") from exc
        return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), XGBClassifier(
            n_estimators=params["n_estimators"], max_depth=params["max_depth"], learning_rate=0.04,
            subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", tree_method="hist",
            n_jobs=1, random_state=42,
        ))
    raise ValueError(name)


def _positive_probability(model, features: pd.DataFrame) -> np.ndarray:
    classes = list(model[-1].classes_)
    if 1 not in classes:
        return np.zeros(len(features))
    return model.predict_proba(features)[:, classes.index(1)]


def tune_candidate(
    train: pd.DataFrame,
    candidate: PredictiveCandidate,
    features: list[str],
    target_column: str,
) -> tuple[dict[str, Any], float]:
    dates = pd.DatetimeIndex(sorted(train.date.unique()))
    splits = combinatorial_purged_splits(
        len(dates), n_groups=4, n_test_groups=1, label_horizon=7, embargo=7
    )
    scored = []
    for params in _grid(candidate.model):
        losses = []
        for split in splits:
            fit_dates = dates[list(split.train_indices)]
            validation_dates = dates[list(split.test_indices)]
            fit = train[train.date.isin(fit_dates)]
            validation = train[train.date.isin(validation_dates)]
            if fit[target_column].nunique() < 2 or validation.empty:
                continue
            estimator = _model(candidate.model, params)
            estimator.fit(fit[features], fit[target_column].astype(int))
            probability = _positive_probability(estimator, validation[features])
            losses.append(brier_score_loss(validation[target_column], probability))
        if losses:
            scored.append((float(np.mean(losses)), params))
    if not scored:
        raise ValueError(f"No valid CPCV folds for {candidate.name}")
    return min(scored, key=lambda item: item[0])[1], min(item[0] for item in scored)


def walk_forward_predictions(
    dataset: DerivativesResearchDataset,
    candidates: list[PredictiveCandidate],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = dataset.frame.copy()
    blocks = [
        (pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year + 1}-01-01"), "development")
        for year in range(2021, 2025)
    ] + [(HOLDOUT_START, HOLDOUT_END + pd.Timedelta(days=1), "holdout")]
    predictions, selection = [], []
    for candidate in candidates:
        features = dataset.feature_sets[candidate.feature_set]
        target_column = dataset.target_columns[candidate.target]
        candidate_frame = frame.copy()
        if candidate.target == "eth_outperforms_btc":
            candidate_frame = candidate_frame[candidate_frame.symbol == "ETH"]
        candidate_frame = candidate_frame.dropna(subset=[target_column])
        for block_start, block_end, split_name in blocks:
            train = candidate_frame[
                (candidate_frame.date < block_start) & (candidate_frame.label_end < block_start)
            ]
            test = candidate_frame[
                (candidate_frame.date >= block_start) & (candidate_frame.date < block_end)
            ]
            if len(train) < 300 or test.empty or train[target_column].nunique() < 2:
                continue
            params, cpcv_brier = tune_candidate(train, candidate, features, target_column)
            estimator = _model(candidate.model, params)
            estimator.fit(train[features], train[target_column].astype(int))
            probability = _positive_probability(estimator, test[features])
            scored = test[["date", "label_end", "symbol", target_column]].copy()
            scored = scored.rename(columns={target_column: "target_value"})
            scored["candidate"] = candidate.name
            scored["target"] = candidate.target
            scored["model"] = candidate.model
            scored["feature_set"] = candidate.feature_set
            scored["probability"] = probability
            scored["split"] = split_name
            predictions.append(scored)
            selection.append({
                "candidate": candidate.name, "target": candidate.target, "model": candidate.model,
                "feature_set": candidate.feature_set, "refit_date": block_start,
                "split": split_name, "parameters": params, "cpcv_brier": cpcv_brier,
                "train_rows": len(train), "max_train_label_end": train.label_end.max(),
            })
    return pd.concat(predictions, ignore_index=True), pd.DataFrame(selection)


def predictive_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_columns = ["target", "model", "feature_set", "split"]
    for keys, group in predictions.groupby(group_columns):
        target, model, feature_set, split = keys
        y = group.target_value.astype(int)
        probability = group.probability.clip(0, 1)
        prediction = probability >= 0.50
        rows.append({
            "target": target, "model": model, "feature_set": feature_set, "split": split,
            "observations": len(group), "positive_rate": y.mean(),
            "auc": roc_auc_score(y, probability) if y.nunique() == 2 else np.nan,
            "brier": brier_score_loss(y, probability),
            "precision": precision_score(y, prediction, zero_division=0),
            "recall": recall_score(y, prediction, zero_division=0),
        })
    return pd.DataFrame(rows)


def strategy_weights(
    dataset: DerivativesResearchDataset,
    strategy: str,
) -> tuple[pd.DataFrame | None, str | None]:
    frame = dataset.frame.copy().set_index(["date", "symbol"])
    dates = pd.DatetimeIndex(sorted(dataset.frame.date.unique()))
    rebalance_dates = dates[dates.weekday == 4]
    weights = pd.DataFrame(0.0, index=rebalance_dates, columns=["BTC", "ETH"])
    oi_available = "open_interest_change_7" in dataset.feature_sets["derivatives_only"]
    if strategy in {"oi_confirmed_trend", "oi_divergence_risk_off"} and not oi_available:
        return None, "Open-interest history has insufficient development coverage."
    for date_ in rebalance_dates:
        try:
            current = frame.loc[date_]
        except KeyError:
            continue
        eligible = current[(current.price_momentum_30 > 0) & (current.price_momentum_90 > 0)]
        base = pd.Series(0.0, index=weights.columns)
        if len(eligible):
            base.loc[eligible.index] = 1.0 / len(eligible)
        target = base.copy()
        if strategy == "price_only_trend":
            pass
        elif strategy == "funding_crowding_avoidance":
            crowded = (current.funding_zscore_90 > 2) & (current.funding_percentile_252 > 0.90)
            target.loc[crowded[crowded].index] = 0.0
            if target.sum() > 0:
                target /= target.sum()
        elif strategy == "funding_mean_reversion":
            for symbol in target.index:
                row = current.loc[symbol]
                if row.funding_zscore_90 > 2 and row.price_momentum_7 < 0:
                    target.loc[symbol] = 0.0
                elif row.funding_zscore_90 < -2 and row.price_momentum_30 > 0:
                    target.loc[symbol] = max(target.loc[symbol], 0.5)
            if target.sum() > 1:
                target /= target.sum()
        elif strategy == "oi_confirmed_trend":
            confirmed = current.open_interest_change_7 > 0
            target.loc[~confirmed] = 0.0
        elif strategy == "oi_divergence_risk_off":
            divergence = (current.price_momentum_7 < 0) & (current.open_interest_change_7 > 0)
            if divergence.any():
                target *= 0.0
        elif strategy == "btc_eth_relative_value":
            valid = current.dropna(subset=["price_momentum_90", "funding_zscore_90", "basis_zscore_90"])
            valid = valid[(valid.price_momentum_30 > 0) & (valid.price_momentum_90 > 0)]
            if valid.empty:
                target *= 0.0
            else:
                component = pd.DataFrame({
                    "momentum": valid.price_momentum_90.rank(pct=True),
                    "funding": (-valid.funding_zscore_90).rank(pct=True),
                    "basis": (-valid.basis_zscore_90.abs()).rank(pct=True),
                })
                target *= 0.0
                target.loc[component.mean(axis=1).idxmax()] = 1.0
        elif strategy == "derivatives_risk_gate":
            risk = (
                current.funding_zscore_90.abs().max() > 2.5
                or current.basis_zscore_90.abs().max() > 2.5
            )
            if risk:
                target *= 0.0
        else:
            raise ValueError(strategy)
        weights.loc[date_] = target.clip(lower=0)
    return weights, None


def backtest_spot_weights(
    spot_panel: pd.DataFrame,
    weekly_weights: pd.DataFrame,
    cost_bps: int,
) -> SpotOutcome:
    close = spot_panel[spot_panel.symbol.isin(weekly_weights.columns)].pivot(
        index="date", columns="symbol", values="close"
    ).sort_index()
    returns = close.pct_change(fill_method=None).fillna(0.0)
    desired = pd.DataFrame(np.nan, index=returns.index, columns=returns.columns)
    active = weekly_weights.index.intersection(desired.index)
    desired.loc[active] = weekly_weights.loc[active]
    desired = desired.ffill().fillna(0.0).clip(lower=0)
    gross = (desired.shift(1).fillna(0.0) * returns).sum(axis=1)
    turnover = desired.diff().abs().sum(axis=1).fillna(desired.abs().sum(axis=1))
    costs = turnover * cost_bps / 10000.0
    return SpotOutcome(gross - costs, desired, turnover, costs)


def period_metrics(outcome: SpotOutcome, start: str, end: str) -> dict[str, float]:
    returns = outcome.returns.loc[start:end]
    metrics = performance_metrics(
        returns, outcome.turnover.reindex(returns.index), outcome.costs.reindex(returns.index)
    )
    weights = outcome.weights.reindex(returns.index)
    years = max(len(returns) / 365, 1 / 365)
    monthly = returns.resample("ME").apply(lambda values: (1 + values).prod() - 1)
    metrics.update({
        "Exposure": float(weights.sum(axis=1).mean()),
        "Cash Allocation": float(1 - weights.sum(axis=1).mean()),
        "Annual Turnover": float(outcome.turnover.reindex(returns.index).sum() / years),
        "Worst Month": float(monthly.min()) if len(monthly) else np.nan,
    })
    return metrics


def acceptance(candidate: dict[str, float], cost_50: dict[str, float], btc: dict[str, float]) -> tuple[bool, list[str]]:
    checks = {
        "Sharpe <= 0.5": candidate["Sharpe"] > 0.5,
        "CAGR <= 0": candidate["CAGR"] > 0,
        "drawdown not better than BTC": candidate["Maximum Drawdown"] > btc["Maximum Drawdown"],
        "fails at 50 bps": cost_50["Sharpe"] > 0 and cost_50["CAGR"] > 0,
        "annual turnover > 12x": candidate["Annual Turnover"] <= 12,
    }
    failures = [reason for reason, passed in checks.items() if not passed]
    return not failures, failures

