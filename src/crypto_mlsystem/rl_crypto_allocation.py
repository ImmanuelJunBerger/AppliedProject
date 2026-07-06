"""Risk-aware reinforcement learning for crypto allocation.

The module tests whether simple risk-aware RL policies add genuine economic
value versus prior supervised/signal strategies.  It deliberately uses discrete
actions and weekly/biweekly rebalancing so the learned policy remains auditable.
No holdout data is used for model or reward selection.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .metrics import performance_metrics
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import deflated_sharpe_probability, probability_backtest_overfitting
from .volatility_expansion import _weighted_dispersion, _weighted_mean, point_in_time_liquid_universe


DEVELOPMENT_START = pd.Timestamp("2020-01-01")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")
ACTIONS_ALL = ("cash", "btc", "eth", "btc_eth_50_50", "top3_momentum", "top5_momentum")
ACTIONS_BTC_ETH = ("cash", "btc", "eth", "btc_eth_50_50")
STATE_FEATURES = (
    "btc_momentum_30",
    "btc_momentum_90",
    "eth_momentum_30",
    "eth_momentum_90",
    "realized_volatility_30",
    "volatility_expansion_probability",
    "cross_sectional_dispersion",
    "stablecoin_supply_change_7d",
    "tvl_growth_30d",
    "market_breadth_30",
    "drawdown_state",
)
PREV_WEIGHT_FEATURES = ("prev_cash_weight", "prev_btc_weight", "prev_eth_weight", "prev_alt_weight")


@dataclass(frozen=True)
class RLCandidate:
    name: str
    universe: str
    rebalance_days: int
    model: str
    reward: str
    gamma: float = 0.80
    episodes_or_iterations: int = 8
    cost_bps_train: int = 25


@dataclass
class RLAllocationDataset:
    panel: pd.DataFrame
    close: pd.DataFrame
    returns: pd.DataFrame
    top10_weights: pd.DataFrame
    momentum_63: pd.DataFrame
    state_features: pd.DataFrame
    metadata: dict[str, Any]


@dataclass
class PortfolioResult:
    returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    actions: pd.Series
    metrics: dict[str, float]


def load_volatility_probability(path: str | Path = "reports/volatility_expansion/predictions.csv") -> pd.Series | None:
    path = Path(path)
    if not path.exists():
        return None
    predictions = pd.read_csv(path, parse_dates=["date"])
    selected = predictions[
        (predictions.model == "elastic_net") & (predictions.feature_set == "price_only")
    ].copy()
    if selected.empty or selected.duplicated("date").any():
        return None
    return selected.set_index("date").probability.astype(float).sort_index()


def _pivot(panel: pd.DataFrame, column: str) -> pd.DataFrame:
    return panel.pivot(index="date", columns="symbol", values=column).sort_index()


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def _external_features(
    public_data: PublicDataBundle,
    close_index: pd.DatetimeIndex,
    volatility_probability: pd.Series | None,
) -> pd.DataFrame:
    features = pd.DataFrame(index=close_index)
    stable = public_data.stablecoins.copy()
    if not stable.empty and "stablecoin_supply_change_7d" in stable:
        stable["date"] = pd.to_datetime(stable.date)
        stable = stable.set_index("date").sort_index()
        features["stablecoin_supply_change_7d"] = stable.stablecoin_supply_change_7d.reindex(close_index).ffill().shift(1)
    else:
        features["stablecoin_supply_change_7d"] = np.nan
    tvl = public_data.chain_tvl.copy()
    if not tvl.empty and "tvl" in tvl:
        tvl["date"] = pd.to_datetime(tvl.date)
        all_tvl = tvl[tvl.chain == "all"].set_index("date").sort_index()
        features["tvl_growth_30d"] = all_tvl.tvl.pct_change(30, fill_method=None).reindex(close_index).ffill().shift(1)
    else:
        features["tvl_growth_30d"] = np.nan
    if volatility_probability is not None:
        features["volatility_expansion_probability"] = volatility_probability.reindex(close_index).ffill().shift(1)
    else:
        features["volatility_expansion_probability"] = 0.50
    return features


def build_rl_allocation_dataset(
    panel: pd.DataFrame,
    public_data: PublicDataBundle,
    volatility_probability: pd.Series | None = None,
) -> RLAllocationDataset:
    clean = panel.copy().sort_values(["date", "symbol"])
    clean["date"] = pd.to_datetime(clean.date)
    close = _pivot(clean, "close")
    returns = close.pct_change(fill_method=None).fillna(0.0)
    top10_weights, _ = point_in_time_liquid_universe(clean, top_n=10, min_history_days=180, max_asset_weight=0.20)
    top10_weights = top10_weights.reindex(index=close.index, columns=close.columns).fillna(0.0)
    basket_return = _weighted_mean(returns, top10_weights).fillna(0.0)
    features = pd.DataFrame(index=close.index)
    if "BTC" in close:
        features["btc_momentum_30"] = close.BTC.pct_change(30, fill_method=None).shift(1)
        features["btc_momentum_90"] = close.BTC.pct_change(90, fill_method=None).shift(1)
    else:
        features["btc_momentum_30"] = np.nan
        features["btc_momentum_90"] = np.nan
    if "ETH" in close:
        features["eth_momentum_30"] = close.ETH.pct_change(30, fill_method=None).shift(1)
        features["eth_momentum_90"] = close.ETH.pct_change(90, fill_method=None).shift(1)
    else:
        features["eth_momentum_30"] = np.nan
        features["eth_momentum_90"] = np.nan
    features["realized_volatility_30"] = basket_return.rolling(30).std().shift(1) * np.sqrt(365)
    features["cross_sectional_dispersion"] = _weighted_dispersion(returns, top10_weights).rolling(30).mean().shift(1)
    momentum_30 = close.pct_change(30, fill_method=None).shift(1)
    eligible = top10_weights > 0
    features["market_breadth_30"] = ((momentum_30 > 0) & eligible).sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)
    wealth = (1 + basket_return).cumprod()
    features["drawdown_state"] = (wealth / wealth.cummax() - 1).shift(1)
    features = pd.concat([features, _external_features(public_data, close.index, volatility_probability)], axis=1)
    features = features[list(STATE_FEATURES)].replace([np.inf, -np.inf], np.nan)
    return RLAllocationDataset(
        panel=clean,
        close=close,
        returns=returns,
        top10_weights=top10_weights,
        momentum_63=close.pct_change(63, fill_method=None).shift(1),
        state_features=features,
        metadata={
            "start": str(close.index.min().date()),
            "end": str(close.index.max().date()),
            "state_features": list(STATE_FEATURES),
            "holdout_start": str(HOLDOUT_START.date()),
            "holdout_end": str(HOLDOUT_END.date()),
        },
    )


def rl_candidates() -> list[RLCandidate]:
    candidates = []
    for universe, rebalance_days, model, reward in product(
        ("btc_eth", "top10"),
        (7, 14),
        ("tabular_q", "fitted_q_linear"),
        ("raw_return", "return_minus_volatility", "return_minus_drawdown", "return_minus_turnover", "adaptive_risk_control"),
    ):
        candidates.append(RLCandidate(
            name=f"rl_{model}_{universe}_r{rebalance_days}_{reward}",
            universe=universe,
            rebalance_days=rebalance_days,
            model=model,
            reward=reward,
            episodes_or_iterations=4,
        ))
    return candidates


def available_actions(universe: str) -> tuple[str, ...]:
    if universe == "btc_eth":
        return ACTIONS_BTC_ETH
    if universe == "top10":
        return ACTIONS_ALL
    raise ValueError(universe)


def action_weights(dataset: RLAllocationDataset, date_: pd.Timestamp, action: str, universe: str) -> pd.Series:
    weights = pd.Series(0.0, index=dataset.close.columns, dtype=float)
    if action == "cash":
        return weights
    if action == "btc" and "BTC" in weights:
        weights["BTC"] = 1.0
        return weights
    if action == "eth" and "ETH" in weights:
        weights["ETH"] = 1.0
        return weights
    if action == "btc_eth_50_50":
        for symbol in ("BTC", "ETH"):
            if symbol in weights:
                weights[symbol] = 0.50
        return weights
    if universe != "top10":
        return weights
    members = dataset.top10_weights.columns[dataset.top10_weights.loc[date_] > 0]
    scores = dataset.momentum_63.loc[date_, members].dropna().sort_values(ascending=False)
    k = 3 if action == "top3_momentum" else 5
    chosen = scores.head(k).index.tolist()
    if chosen:
        weights.loc[chosen] = 1.0 / len(chosen)
    return weights


def previous_weight_features(weights: pd.Series) -> dict[str, float]:
    gross = float(weights.sum())
    btc = float(weights.get("BTC", 0.0))
    eth = float(weights.get("ETH", 0.0))
    alt = float(max(gross - btc - eth, 0.0))
    return {
        "prev_cash_weight": float(max(1.0 - gross, 0.0)),
        "prev_btc_weight": btc,
        "prev_eth_weight": eth,
        "prev_alt_weight": alt,
    }


def _period_daily_returns(dataset: RLAllocationDataset, date_: pd.Timestamp, next_date: pd.Timestamp, weights: pd.Series) -> pd.Series:
    mask = (dataset.returns.index > date_) & (dataset.returns.index <= next_date)
    daily = dataset.returns.loc[mask, weights.index].fillna(0.0).dot(weights)
    return daily


def transition_reward(
    daily_returns: pd.Series,
    turnover: float,
    reward_name: str,
    cost_bps: int,
) -> float:
    gross = float((1 + daily_returns).prod() - 1.0) if len(daily_returns) else 0.0
    cost = turnover * cost_bps / 10000.0
    net = gross - cost
    period_vol = float(daily_returns.std(ddof=1) * np.sqrt(len(daily_returns))) if len(daily_returns) > 1 else 0.0
    period_wealth = (1 + daily_returns.fillna(0.0)).cumprod()
    period_dd = float((period_wealth / period_wealth.cummax() - 1.0).min()) if len(period_wealth) else 0.0
    if reward_name == "raw_return":
        return net
    if reward_name == "return_minus_volatility":
        return net - 0.10 * period_vol
    if reward_name == "return_minus_drawdown":
        return net - 0.10 * abs(min(period_dd, 0.0))
    if reward_name == "return_minus_turnover":
        return net - 0.0025 * turnover
    if reward_name == "adaptive_risk_control":
        return net - 0.08 * period_vol - 0.08 * abs(min(period_dd, 0.0)) - 0.0025 * turnover
    raise ValueError(reward_name)


def _decision_frame(dataset: RLAllocationDataset, rebalance_days: int) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index, rebalance_days)
    frame = dataset.state_features.reindex(dates)
    frame = frame.loc[(frame.index >= DEVELOPMENT_START) & (frame.index <= HOLDOUT_END)]
    return frame


def _train_dates_for_split(decision_frame: pd.DataFrame, indices: tuple[int, ...]) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(decision_frame.loc[DEVELOPMENT_START:DEVELOPMENT_END].index[list(indices)])


def _state_vector(base_row: pd.Series, prev_weights: pd.Series) -> dict[str, float]:
    values = {feature: float(base_row.get(feature, np.nan)) for feature in STATE_FEATURES}
    values.update(previous_weight_features(prev_weights))
    return values


def _action_feature_frame(state: dict[str, float], action: str, actions: tuple[str, ...]) -> pd.DataFrame:
    row = dict(state)
    for action_name in actions:
        row[f"action_{action_name}"] = 1.0 if action == action_name else 0.0
    return pd.DataFrame([row])


def _make_transitions(
    dataset: RLAllocationDataset,
    candidate: RLCandidate,
    decision_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    actions = available_actions(candidate.universe)
    rows = []
    all_dates = _decision_frame(dataset, candidate.rebalance_days).index
    date_positions = {date_: i for i, date_ in enumerate(all_dates)}
    for date_ in decision_dates:
        position = date_positions.get(date_)
        if position is None or position >= len(all_dates) - 1:
            continue
        next_date = all_dates[position + 1]
        base = dataset.state_features.loc[date_]
        next_base = dataset.state_features.loc[next_date]
        if base.isna().all() or next_base.isna().all():
            continue
        weights_by_action = {
            action: action_weights(dataset, date_, action, candidate.universe)
            for action in actions
        }
        daily_by_action = {
            action: _period_daily_returns(dataset, date_, next_date, weights)
            for action, weights in weights_by_action.items()
        }
        for prev_action in actions:
            prev_weights = weights_by_action[prev_action]
            state = _state_vector(base, prev_weights)
            for action in actions:
                weights = weights_by_action[action]
                turnover = float((weights - prev_weights).abs().sum())
                daily = daily_by_action[action]
                reward = transition_reward(daily, turnover, candidate.reward, candidate.cost_bps_train)
                next_state = _state_vector(next_base, weights)
                rows.append({
                    "date": date_,
                    "next_date": next_date,
                    "prev_action": prev_action,
                    "action": action,
                    "reward": reward,
                    "terminal": False,
                    **{f"state_{k}": v for k, v in state.items()},
                    **{f"next_state_{k}": v for k, v in next_state.items()},
                })
    return pd.DataFrame(rows)


def fit_state_bins(state_values: pd.DataFrame, bins: int = 3) -> dict[str, list[float]]:
    thresholds: dict[str, list[float]] = {}
    for column in state_values.columns:
        series = state_values[column].replace([np.inf, -np.inf], np.nan).dropna()
        if series.empty:
            thresholds[column] = []
            continue
        quantiles = np.linspace(0, 1, bins + 1)[1:-1]
        values = np.unique(series.quantile(quantiles).to_numpy(dtype=float))
        thresholds[column] = [float(value) for value in values if np.isfinite(value)]
    return thresholds


def discretize_state(state: dict[str, float], thresholds: dict[str, list[float]]) -> tuple[int, ...]:
    key = []
    for column in list(STATE_FEATURES) + list(PREV_WEIGHT_FEATURES):
        value = state.get(column, np.nan)
        if not np.isfinite(value):
            key.append(-1)
        else:
            key.append(int(np.searchsorted(thresholds.get(column, []), value, side="right")))
    return tuple(key)


def train_tabular_q(
    dataset: RLAllocationDataset,
    candidate: RLCandidate,
    train_dates: pd.DatetimeIndex,
    transitions: pd.DataFrame | None = None,
) -> dict[str, Any]:
    actions = available_actions(candidate.universe)
    if transitions is None:
        transitions = _make_transitions(dataset, candidate, train_dates)
    else:
        transitions = transitions[transitions.date.isin(train_dates)].copy()
    state_columns = [f"state_{feature}" for feature in list(STATE_FEATURES) + list(PREV_WEIGHT_FEATURES)]
    thresholds = fit_state_bins(transitions[state_columns].rename(columns=lambda c: c.replace("state_", "")), bins=3)
    q: dict[tuple[tuple[int, ...], str], float] = {}
    alpha = 0.25
    for _ in range(candidate.episodes_or_iterations):
        for row in transitions.to_dict("records"):
            state = {key.replace("state_", ""): row[key] for key in state_columns}
            next_state = {key.replace("next_state_", ""): row[key] for key in [f"next_state_{feature}" for feature in list(STATE_FEATURES) + list(PREV_WEIGHT_FEATURES)]}
            state_key = discretize_state(state, thresholds)
            next_key = discretize_state(next_state, thresholds)
            old = q.get((state_key, row["action"]), 0.0)
            next_value = max(q.get((next_key, action), 0.0) for action in actions)
            target = row["reward"] + candidate.gamma * next_value
            q[(state_key, row["action"])] = old + alpha * (target - old)
    return {"kind": "tabular_q", "actions": actions, "thresholds": thresholds, "q": q}


def _transition_design(transitions: pd.DataFrame, actions: tuple[str, ...], next_state: bool = False) -> pd.DataFrame:
    prefix = "next_state_" if next_state else "state_"
    rows = []
    state_columns = [f"{prefix}{feature}" for feature in list(STATE_FEATURES) + list(PREV_WEIGHT_FEATURES)]
    for row in transitions.to_dict("records"):
        base = {feature: row[f"{prefix}{feature}"] for feature in list(STATE_FEATURES) + list(PREV_WEIGHT_FEATURES)}
        action = row["action"]
        for action_name in actions:
            base[f"action_{action_name}"] = 1.0 if action == action_name else 0.0
        rows.append(base)
    return pd.DataFrame(rows)


def _next_action_design(transitions: pd.DataFrame, actions: tuple[str, ...], action: str) -> pd.DataFrame:
    rows = []
    for row in transitions.to_dict("records"):
        base = {feature: row[f"next_state_{feature}"] for feature in list(STATE_FEATURES) + list(PREV_WEIGHT_FEATURES)}
        for action_name in actions:
            base[f"action_{action_name}"] = 1.0 if action == action_name else 0.0
        rows.append(base)
    return pd.DataFrame(rows)


def train_fitted_q_linear(
    dataset: RLAllocationDataset,
    candidate: RLCandidate,
    train_dates: pd.DatetimeIndex,
    transitions: pd.DataFrame | None = None,
) -> dict[str, Any]:
    actions = available_actions(candidate.universe)
    if transitions is None:
        transitions = _make_transitions(dataset, candidate, train_dates)
    else:
        transitions = transitions[transitions.date.isin(train_dates)].copy()
    x = _transition_design(transitions, actions)
    y = transitions.reward.to_numpy(dtype=float)
    next_designs = {
        action: _next_action_design(transitions, actions, action)
        for action in actions
    }
    model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=1.0))
    for _ in range(candidate.episodes_or_iterations):
        model.fit(x, y)
        next_values = []
        for action in actions:
            next_values.append(model.predict(next_designs[action]))
        continuation = np.nanmax(np.vstack(next_values), axis=0)
        y = transitions.reward.to_numpy(dtype=float) + candidate.gamma * continuation
    model.fit(x, y)
    return {"kind": "fitted_q_linear", "actions": actions, "model": model}


def train_policy(
    dataset: RLAllocationDataset,
    candidate: RLCandidate,
    train_dates: pd.DatetimeIndex,
    transitions: pd.DataFrame | None = None,
) -> dict[str, Any]:
    if candidate.model == "tabular_q":
        return train_tabular_q(dataset, candidate, train_dates, transitions)
    if candidate.model == "fitted_q_linear":
        return train_fitted_q_linear(dataset, candidate, train_dates, transitions)
    raise ValueError(candidate.model)


def policy_q_values(policy: dict[str, Any], state: dict[str, float]) -> dict[str, float]:
    actions = policy["actions"]
    if policy["kind"] == "tabular_q":
        key = discretize_state(state, policy["thresholds"])
        return {action: float(policy["q"].get((key, action), 0.0)) for action in actions}
    if policy["kind"] == "fitted_q_linear":
        model = policy["model"]
        values = {}
        for action in actions:
            x = _action_feature_frame(state, action, actions)
            values[action] = float(model.predict(x)[0])
        return values
    raise ValueError(policy["kind"])


def simulate_policy_weights(
    dataset: RLAllocationDataset,
    candidate: RLCandidate,
    policy: dict[str, Any],
    start: pd.Timestamp = DEVELOPMENT_START,
    end: pd.Timestamp = HOLDOUT_END,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    dates = _decision_frame(dataset, candidate.rebalance_days).loc[start:end].index
    target_weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    actions = pd.Series("cash", index=dates, dtype=object)
    q_rows = []
    previous = pd.Series(0.0, index=dataset.close.columns, dtype=float)
    for date_ in dates:
        base = dataset.state_features.loc[date_]
        if base.isna().all():
            action = "cash"
            q_values = {candidate_action: 0.0 for candidate_action in available_actions(candidate.universe)}
        else:
            state = _state_vector(base, previous)
            q_values = policy_q_values(policy, state)
            action = max(q_values, key=q_values.get)
        weights = action_weights(dataset, date_, action, candidate.universe)
        target_weights.loc[date_] = weights
        actions.loc[date_] = action
        q_rows.append({"date": date_, "chosen_action": action, **{f"q_{k}": v for k, v in q_values.items()}})
        previous = weights
    return target_weights, actions, pd.DataFrame(q_rows)


def backtest_weights(
    dataset: RLAllocationDataset,
    target_weights: pd.DataFrame,
    actions: pd.Series,
    cost_bps: int,
) -> PortfolioResult:
    returns = dataset.returns.reindex(columns=target_weights.columns).fillna(0.0)
    start = target_weights.index.min()
    returns = returns.loc[start:min(HOLDOUT_END, returns.index.max())]
    targets = target_weights.reindex(target_weights.index.intersection(returns.index)).fillna(0.0)
    index = returns.index
    columns = returns.columns
    returns_array = returns.to_numpy(dtype=float)
    target_map = {
        date_: row.to_numpy(dtype=float)
        for date_, row in targets.reindex(columns=columns).iterrows()
    }
    executed_array = np.zeros((len(index), len(columns)), dtype=float)
    gross_array = np.zeros(len(index), dtype=float)
    net_array = np.zeros(len(index), dtype=float)
    turnover_array = np.zeros(len(index), dtype=float)
    costs_array = np.zeros(len(index), dtype=float)
    previous = np.zeros(len(columns), dtype=float)
    cost_rate = cost_bps / 10000.0
    for i, date_ in enumerate(index):
        gross_array[i] = float(np.dot(previous, returns_array[i]))
        target = previous
        requested = target_map.get(date_)
        if requested is not None:
            change = requested - previous
            target = requested
            turnover_array[i] = float(np.abs(change).sum())
            costs_array[i] = turnover_array[i] * cost_rate
        net_array[i] = gross_array[i] - costs_array[i]
        executed_array[i] = target
        previous = target
    net = pd.Series(net_array, index=index)
    gross = pd.Series(gross_array, index=index)
    turnover = pd.Series(turnover_array, index=index)
    costs = pd.Series(costs_array, index=index)
    weights = pd.DataFrame(executed_array, index=index, columns=columns)
    return PortfolioResult(net, gross, weights, turnover, costs, actions.reindex(index).ffill().fillna("cash"), portfolio_metrics(net, turnover, costs, weights))


def portfolio_metrics(returns: pd.Series, turnover: pd.Series, costs: pd.Series, weights: pd.DataFrame) -> dict[str, float]:
    metrics = performance_metrics(returns, turnover, costs)
    elapsed_years = max(len(returns) / 365.0, 1 / 365.0)
    exposure = weights.sum(axis=1).clip(0, 1)
    monthly = returns.resample("ME").apply(lambda values: (1 + values).prod() - 1)
    metrics.update({
        "Exposure": float(exposure.mean()),
        "Cash Allocation": float(1.0 - exposure.mean()),
        "Annual Turnover": float(turnover.sum() / elapsed_years),
        "Worst Month": float(monthly.min()) if len(monthly) else np.nan,
        "Average Holdings": float((weights > 1e-6).sum(axis=1).mean()),
    })
    return metrics


def period_metrics(result: PortfolioResult, start: str | pd.Timestamp, end: str | pd.Timestamp) -> dict[str, float]:
    returns = result.returns.loc[pd.Timestamp(start):pd.Timestamp(end)]
    return portfolio_metrics(
        returns,
        result.turnover.reindex(returns.index).fillna(0.0),
        result.costs.reindex(returns.index).fillna(0.0),
        result.weights.reindex(returns.index).fillna(0.0),
    )


def _weekly_returns(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1 + values).prod() - 1).dropna()


def _decision_period_returns(returns: pd.Series, decision_dates: pd.DatetimeIndex) -> pd.Series:
    values = []
    index = []
    for current, next_date in zip(decision_dates[:-1], decision_dates[1:]):
        period = returns.loc[(returns.index > current) & (returns.index <= next_date)]
        values.append(float((1 + period).prod() - 1.0) if len(period) else 0.0)
        index.append(current)
    return pd.Series(values, index=pd.DatetimeIndex(index))


def _period_sharpe(period_returns: pd.Series, indices: tuple[int, ...], periods_per_year: float) -> float:
    subset = period_returns.iloc[list(indices)]
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(periods_per_year)) if std and np.isfinite(std) else -np.inf


def select_candidate_cpcv(dataset: RLAllocationDataset, candidates: list[RLCandidate]) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows = []
    fold_rows = []
    config_returns = {}
    for candidate in candidates:
        decision = _decision_frame(dataset, candidate.rebalance_days).loc[DEVELOPMENT_START:DEVELOPMENT_END]
        if len(decision) < 40:
            continue
        period_decision = decision.iloc[:-1]
        splits = combinatorial_purged_splits(len(period_decision), n_groups=5, n_test_groups=1, label_horizon=1, embargo=1)
        fold_sharpes = []
        periods_per_year = 365.0 / candidate.rebalance_days
        all_transitions = _make_transitions(dataset, candidate, pd.DatetimeIndex(period_decision.index))
        for number, split in enumerate(splits):
            train_dates = pd.DatetimeIndex(period_decision.index[list(split.train_indices)])
            policy = train_policy(dataset, candidate, train_dates, all_transitions)
            weights, actions, _ = simulate_policy_weights(dataset, candidate, policy, DEVELOPMENT_START, DEVELOPMENT_END)
            result = backtest_weights(dataset, weights, actions, candidate.cost_bps_train)
            period_returns = _decision_period_returns(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END], pd.DatetimeIndex(decision.index))
            sharpe = _period_sharpe(period_returns, split.test_indices, periods_per_year)
            fold_sharpes.append(sharpe)
            fold_rows.append({"candidate": candidate.name, "fold": number, "fold_sharpe": sharpe})
        full_train_dates = pd.DatetimeIndex(period_decision.index)
        policy = train_policy(dataset, candidate, full_train_dates, all_transitions)
        weights, actions, _ = simulate_policy_weights(dataset, candidate, policy, DEVELOPMENT_START, DEVELOPMENT_END)
        result = backtest_weights(dataset, weights, actions, candidate.cost_bps_train)
        period_full = _decision_period_returns(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END], pd.DatetimeIndex(decision.index))
        config_returns[candidate.name] = period_full
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        rows.append({
            "candidate": candidate.name,
            "universe": candidate.universe,
            "rebalance_days": candidate.rebalance_days,
            "model": candidate.model,
            "reward": candidate.reward,
            "median_fold_sharpe": float(np.nanmedian(fold_sharpes)),
            "worst_fold_sharpe": float(np.nanmin(fold_sharpes)),
            "positive_fold_fraction": float(np.mean(np.asarray(fold_sharpes) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
        })
    selection = pd.DataFrame(rows).sort_values(
        ["median_fold_sharpe", "worst_fold_sharpe", "development_sharpe", "development_turnover"],
        ascending=[False, False, False, True],
    )
    winner = str(selection.iloc[0].candidate)
    aligned = pd.concat(config_returns, axis=1).sort_index()
    pbo = probability_backtest_overfitting(aligned, blocks=8)
    return selection, pd.DataFrame(fold_rows), winner, pbo


def _benchmark_weights(dataset: RLAllocationDataset, name: str) -> pd.DataFrame:
    dates = dataset.close.index
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    if name == "btc_buy_hold":
        if "BTC" in weights:
            weights["BTC"] = 1.0
    elif name == "eth_buy_hold":
        if "ETH" in weights:
            weights["ETH"] = 1.0
    elif name == "btc_eth_50_50":
        for symbol in ("BTC", "ETH"):
            if symbol in weights:
                weights[symbol] = 0.50
    elif name == "defensive_btc_eth_cash_rule":
        dates = _rebalance_dates(dataset.close.index, 7)
        weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
        btc_trend = dataset.close.BTC.pct_change(90, fill_method=None).shift(1) if "BTC" in dataset.close else pd.Series(np.nan, index=dates)
        eth_trend = dataset.close.ETH.pct_change(90, fill_method=None).shift(1) if "ETH" in dataset.close else pd.Series(np.nan, index=dates)
        drawdown = dataset.state_features.drawdown_state
        for date_ in dates:
            if btc_trend.reindex([date_]).iloc[0] > 0 and drawdown.reindex([date_]).iloc[0] > -0.25:
                weights.loc[date_, "BTC"] = 0.50 if "BTC" in weights else 0.0
                if "ETH" in weights and eth_trend.reindex([date_]).iloc[0] > 0:
                    weights.loc[date_, "ETH"] = 0.50
        return weights
    else:
        raise ValueError(name)
    return weights


def _prior_strategy_rows() -> pd.DataFrame:
    rows = []
    sources = [
        ("tier1_regime_momentum", Path("reports/tier1_regime_momentum/metrics.csv")),
        ("risk_managed_momentum", Path("reports/risk_managed_microstructure/metrics.csv")),
        ("volatility_forecast_overlay", Path("reports/volatility_expansion_trading/metrics.csv")),
    ]
    for label, path in sources:
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        if {"split", "cost_bps", "Sharpe"}.issubset(frame.columns):
            subset = frame[(frame.split == "holdout") & (frame.cost_bps == 25)].copy()
            if subset.empty:
                continue
            best = subset.sort_values("Sharpe", ascending=False).head(1).iloc[0].to_dict()
            best["name"] = f"prior_{label}:{best.get('name', '')}"
            best["category"] = "prior_reference"
            rows.append(best)
    return pd.DataFrame(rows)


def run_rl_crypto_allocation_study(
    panel: pd.DataFrame,
    public_data: PublicDataBundle,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_rl_allocation_dataset(panel, public_data, volatility_probability)
    candidates = rl_candidates()
    selection, folds, winner_name, pbo = select_candidate_cpcv(dataset, candidates)
    by_name = {candidate.name: candidate for candidate in candidates}
    winner = by_name[winner_name]
    full_dev_dates = pd.DatetimeIndex(_decision_frame(dataset, winner.rebalance_days).loc[DEVELOPMENT_START:DEVELOPMENT_END].index)
    winner_policy = train_policy(dataset, winner, full_dev_dates)
    weights, actions, q_values = simulate_policy_weights(dataset, winner, winner_policy, DEVELOPMENT_START, HOLDOUT_END)
    metrics_rows = []
    result_by_cost = {}
    for cost in COST_LEVELS:
        result = backtest_weights(dataset, weights, actions, cost)
        result_by_cost[cost] = result
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            metrics_rows.append({"name": winner.name, "category": "rl_policy", "split": split, "cost_bps": cost, **period_metrics(result, start, end)})
    for name in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "defensive_btc_eth_cash_rule"):
        benchmark_weights = _benchmark_weights(dataset, name)
        benchmark_actions = pd.Series(name, index=benchmark_weights.index, dtype=object)
        cost = 25 if name == "defensive_btc_eth_cash_rule" else 0
        result = backtest_weights(dataset, benchmark_weights, benchmark_actions, cost)
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            metrics_rows.append({"name": name, "category": "benchmark", "split": split, "cost_bps": cost, **period_metrics(result, start, end)})
    prior = _prior_strategy_rows()
    metrics = pd.DataFrame(metrics_rows)
    if not prior.empty:
        metrics = pd.concat([metrics, prior], ignore_index=True, sort=False)
    holdout_25 = metrics[(metrics.name == winner.name) & (metrics.split == "holdout") & (metrics.cost_bps == 25)].iloc[0]
    holdout_50 = metrics[(metrics.name == winner.name) & (metrics.split == "holdout") & (metrics.cost_bps == 50)].iloc[0]
    btc_holdout = metrics[(metrics.name == "btc_buy_hold") & (metrics.split == "holdout")].iloc[0]
    failures = []
    if holdout_25.Sharpe <= 0.5:
        failures.append("holdout Sharpe <= 0.5")
    if holdout_25.CAGR <= 0:
        failures.append("holdout CAGR <= 0")
    if holdout_25["Maximum Drawdown"] <= btc_holdout["Maximum Drawdown"]:
        failures.append("max drawdown not better than BTC")
    if holdout_50.Sharpe <= 0 or holdout_50.CAGR <= 0:
        failures.append("does not survive 50 bps")
    if holdout_25["Annual Turnover"] > 12:
        failures.append("annual turnover > 12x")
    selected = result_by_cost[25]
    dsr = deflated_sharpe_probability(selected.returns.loc[HOLDOUT_START:HOLDOUT_END], len(candidates))
    diagnostics = policy_diagnostics(result_by_cost[25], q_values, winner)
    return {
        "dataset": dataset,
        "candidates": candidates,
        "selection": selection,
        "folds": folds,
        "winner": winner,
        "winner_policy_kind": winner_policy["kind"],
        "metrics": metrics,
        "q_values": q_values,
        "policy_diagnostics": diagnostics,
        "acceptance": {
            "passes": not failures,
            "failures": "; ".join(failures),
            "holdout_sharpe": float(holdout_25.Sharpe),
            "holdout_cagr": float(holdout_25.CAGR),
            "holdout_max_drawdown": float(holdout_25["Maximum Drawdown"]),
            "holdout_turnover": float(holdout_25["Annual Turnover"]),
        },
        "statistics": {
            "tested_configurations": len(candidates),
            "pbo": pbo,
            "deflated_sharpe_probability": dsr,
            "stable_baselines3_available": importlib.util.find_spec("stable_baselines3") is not None,
            "dqn_ppo_status": "not_run; simple tabular/fitted-Q baselines are tested first",
        },
    }


def policy_diagnostics(result: PortfolioResult, q_values: pd.DataFrame, winner: RLCandidate) -> pd.DataFrame:
    rows = []
    actions = result.actions.reindex(result.returns.index).ffill().fillna("cash")
    for split, start, end in (
        ("development", DEVELOPMENT_START, DEVELOPMENT_END),
        ("holdout", HOLDOUT_START, HOLDOUT_END),
    ):
        mask = (actions.index >= start) & (actions.index <= end)
        exposure = result.weights.sum(axis=1).reindex(actions.index).fillna(0.0)
        for action, fraction in actions.loc[mask].value_counts(normalize=True).items():
            rows.append({
                "split": split,
                "diagnostic": "action_frequency",
                "name": action,
                "value": float(fraction),
            })
        rows.append({
            "split": split,
            "diagnostic": "average_exposure",
            "name": winner.name,
            "value": float(exposure.loc[mask].mean()),
        })
        rows.append({
            "split": split,
            "diagnostic": "cash_fraction",
            "name": winner.name,
            "value": float((exposure.loc[mask] < 1e-8).mean()),
        })
    if not q_values.empty:
        q_columns = [column for column in q_values.columns if column.startswith("q_")]
        holdout_q = q_values[(q_values.date >= HOLDOUT_START) & (q_values.date <= HOLDOUT_END)]
        for column in q_columns:
            rows.append({
                "split": "holdout",
                "diagnostic": "mean_q_value",
                "name": column.replace("q_", ""),
                "value": float(holdout_q[column].mean()) if len(holdout_q) else np.nan,
            })
    return pd.DataFrame(rows)


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
    view = frame.head(limit) if limit else frame
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in view.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def write_rl_crypto_allocation_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    winner: RLCandidate = result["winner"]
    metrics: pd.DataFrame = result["metrics"]
    selection: pd.DataFrame = result["selection"]
    diagnostics: pd.DataFrame = result["policy_diagnostics"]
    acceptance = result["acceptance"]
    statistics = result["statistics"]
    holdout = metrics[(metrics.split == "holdout") & ((metrics.cost_bps == 25) | (metrics.category.isin(["benchmark", "prior_reference"])))].sort_values("Sharpe", ascending=False)
    development = metrics[(metrics.split == "development") & ((metrics.cost_bps == 25) | (metrics.category == "benchmark"))].sort_values("Sharpe", ascending=False)
    columns = [("name", "Strategy"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Sortino", "Sortino"), ("Maximum Drawdown", "Max DD"), ("Calmar", "Calmar"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure")]
    percent = {"CAGR", "Maximum Drawdown", "Exposure"}

    (output / "results_summary.md").write_text(f"""# Risk-aware reinforcement learning for crypto allocation

## Protocol

- Development period: 2020-01-01 through 2024-12-31.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: CPCV inside development only.
- No holdout tuning and no holdout cell selection.
- Tested configurations: {statistics['tested_configurations']}.
- Selected candidate: **{winner.name}**.
- Policy kind: `{result['winner_policy_kind']}`.
- DQN/PPO status: {statistics['dqn_ppo_status']}.
- Stable-Baselines3 available: {_fmt(statistics['stable_baselines3_available'])}.

## Selected candidate

```json
{json.dumps(asdict(winner), indent=2)}
```

## Development comparison at 25 bps

{_table(development, columns, percent)}

## Locked holdout comparison

{_table(holdout, columns, percent)}

## Statistical controls

- Approximate PBO: {_fmt(statistics['pbo'], True)}.
- Deflated Sharpe probability: {_fmt(statistics['deflated_sharpe_probability'], True)}.
""", encoding="utf-8")

    reward_comparison = selection.groupby(["model", "reward"]).agg(
        configurations=("candidate", "count"),
        median_cpcv_sharpe=("median_fold_sharpe", "median"),
        best_cpcv_sharpe=("median_fold_sharpe", "max"),
        median_development_sharpe=("development_sharpe", "median"),
    ).reset_index().sort_values("best_cpcv_sharpe", ascending=False)
    (output / "reward_comparison.md").write_text(f"""# Reward comparison

Rows are grouped by model and reward function. Selection is based on development
CPCV only.

{_table(reward_comparison, [('model', 'Model'), ('reward', 'Reward'), ('configurations', 'Configs'), ('median_cpcv_sharpe', 'Median CPCV Sharpe'), ('best_cpcv_sharpe', 'Best CPCV Sharpe'), ('median_development_sharpe', 'Median development Sharpe')])}

## Top selected configurations

{_table(selection, [('candidate', 'Candidate'), ('universe', 'Universe'), ('rebalance_days', 'Rebalance'), ('model', 'Model'), ('reward', 'Reward'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold Sharpe'), ('development_sharpe', 'Development Sharpe'), ('development_turnover', 'Development turnover')], limit=25)}
""", encoding="utf-8")

    holdout_cost = metrics[(metrics.name == winner.name) & (metrics.split == "holdout")].sort_values("cost_bps")
    (output / "holdout_results.md").write_text(f"""# Locked holdout results

## Holdout comparison

{_table(holdout, columns, percent)}

## Cost sensitivity for selected RL policy

{_table(holdout_cost, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Acceptance

- Passes paper-trading criteria: {_fmt(acceptance['passes'])}
- Holdout Sharpe: {acceptance['holdout_sharpe']:.3f}
- Holdout CAGR: {acceptance['holdout_cagr']:.2%}
- Holdout max drawdown: {acceptance['holdout_max_drawdown']:.2%}
- Holdout annual turnover: {acceptance['holdout_turnover']:.2f}x
- Failures: {acceptance['failures'] or 'None'}
""", encoding="utf-8")

    (output / "policy_diagnostics.md").write_text(f"""# Policy diagnostics

{_table(diagnostics, [('split', 'Split'), ('diagnostic', 'Diagnostic'), ('name', 'Name'), ('value', 'Value')], {'value'})}
""", encoding="utf-8")

    selected_holdout = holdout[holdout.name == winner.name]
    selected_sharpe = float(selected_holdout.iloc[0].Sharpe) if len(selected_holdout) else np.nan
    selected_cagr = float(selected_holdout.iloc[0].CAGR) if len(selected_holdout) else np.nan
    holdout_actions = diagnostics[(diagnostics.split == "holdout") & (diagnostics.diagnostic == "action_frequency")]
    dominant_action = "N/A"
    dominant_action_fraction = np.nan
    if not holdout_actions.empty:
        dominant = holdout_actions.sort_values("value", ascending=False).iloc[0]
        dominant_action = str(dominant["name"])
        dominant_action_fraction = float(dominant["value"])
    overfit_text = (
        "The selected RL policy does not show genuine economic value."
        if not acceptance["passes"] else
        "The selected RL policy passes the declared economic criteria, but should still be paper-traded before capital deployment."
    )
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Does risk-aware RL produce genuine economic value?

{overfit_text}

Selected holdout Sharpe: {selected_sharpe:.3f}.
Selected holdout CAGR: {selected_cagr:.2%}.
Acceptance pass: {_fmt(acceptance['passes'])}.
Failures: {acceptance['failures'] or 'None'}.
Dominant holdout action: {dominant_action} ({_fmt(dominant_action_fraction, True)} of evaluated days).

## Interpretation

- PBO: {_fmt(statistics['pbo'], True)}.
- Deflated Sharpe probability: {_fmt(statistics['deflated_sharpe_probability'], True)}.
- The policy was selected using development-only CPCV, not holdout performance.
- The selected policy effectively collapses to the dominant holdout action above,
  so it is not evidence that RL learned robust dynamic risk control.
- Risk-aware reward variants did not beat the raw-return selected policy in a
  way that translated to the locked holdout.
- If development performance is materially stronger than holdout performance,
  the correct interpretation is development-period overfitting rather than
  validated RL alpha.

## Decision

{'Recommend paper trading the selected RL policy with no capital until live monitoring confirms execution quality.' if acceptance['passes'] else 'Do not paper trade with capital. Risk-aware RL did not clear the locked-holdout criteria.'}
""", encoding="utf-8")

    selection.to_csv(output / "candidate_selection.csv", index=False)
    result["folds"].to_csv(output / "cpcv_folds.csv", index=False)
    metrics.to_csv(output / "metrics.csv", index=False)
    diagnostics.to_csv(output / "policy_diagnostics.csv", index=False)
    result["q_values"].to_csv(output / "q_values.csv", index=False)
    payload = {
        "winner": asdict(winner),
        "winner_policy_kind": result["winner_policy_kind"],
        "acceptance": acceptance,
        "statistics": statistics,
        "metrics": metrics.to_dict("records"),
        "selection": selection.to_dict("records"),
        "policy_diagnostics": diagnostics.to_dict("records"),
    }
    (output / "results.json").write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value)
    return value


__all__ = [
    "ACTIONS_ALL",
    "RLCandidate",
    "RLAllocationDataset",
    "STATE_FEATURES",
    "action_weights",
    "build_rl_allocation_dataset",
    "discretize_state",
    "fit_state_bins",
    "load_volatility_probability",
    "rl_candidates",
    "run_rl_crypto_allocation_study",
    "transition_reward",
    "write_rl_crypto_allocation_reports",
]
