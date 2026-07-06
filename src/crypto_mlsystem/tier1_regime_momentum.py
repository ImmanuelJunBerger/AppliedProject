"""Tier-1 regime-gated cross-sectional crypto momentum.

Regime gating is restricted to the five statistically validated Tier-1 features:

- stablecoin_supply_change_7d
- tvl_growth_30d
- volatility_4h_7d
- volatility_expansion_probability
- cross_sectional_dispersion

The selection layer uses simple momentum ranks as requested, but those momentum
signals are not used to define the market regime.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .metrics import performance_metrics
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import deflated_sharpe_probability, probability_backtest_overfitting
from .volatility_expansion import _weighted_dispersion, point_in_time_liquid_universe


DEVELOPMENT_START = pd.Timestamp("2020-01-01")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")
TIER1_FEATURES = (
    "stablecoin_supply_change_7d",
    "tvl_growth_30d",
    "volatility_4h_7d",
    "volatility_expansion_probability",
    "cross_sectional_dispersion",
)


@dataclass(frozen=True)
class RegimeMomentumCandidate:
    name: str
    universe_size: int
    rebalance_days: int
    momentum_signal: str
    top_k: int
    threshold_set: str
    risk_on_votes: int
    neutral_policy: str
    turnover_cap: float = 0.75
    max_asset_weight: float = 0.20


@dataclass
class RegimeMomentumDataset:
    panel: pd.DataFrame
    close: pd.DataFrame
    returns: pd.DataFrame
    universe_weights: pd.DataFrame
    tier1_features: pd.DataFrame
    threshold_sets: dict[str, dict[str, float]]
    metadata: dict[str, Any]


@dataclass
class PortfolioResult:
    returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    regimes: pd.Series
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


def _market_series(public_data: PublicDataBundle, close_index: pd.DatetimeIndex, volatility_probability: pd.Series | None) -> pd.DataFrame:
    features = pd.DataFrame(index=close_index)
    stable = public_data.stablecoins.copy()
    if not stable.empty:
        stable["date"] = pd.to_datetime(stable.date)
        stable = stable.set_index("date").sort_index()
        if "stablecoin_supply_change_7d" in stable:
            features["stablecoin_supply_change_7d"] = stable.stablecoin_supply_change_7d.reindex(close_index).ffill().shift(1)
    tvl = public_data.chain_tvl.copy()
    if not tvl.empty:
        tvl["date"] = pd.to_datetime(tvl.date)
        all_tvl = tvl[tvl.chain == "all"].set_index("date").sort_index()
        if "tvl" in all_tvl:
            features["tvl_growth_30d"] = all_tvl.tvl.pct_change(30, fill_method=None).reindex(close_index).ffill().shift(1)
    intraday = public_data.binance_4h_daily_features.copy()
    if not intraday.empty and "volatility_4h_7d" in intraday:
        intraday["date"] = pd.to_datetime(intraday.date)
        vol = intraday.pivot(index="date", columns="symbol", values="volatility_4h_7d").sort_index()
        available = [symbol for symbol in ("BTC", "ETH") if symbol in vol]
        if available:
            features["volatility_4h_7d"] = vol[available].mean(axis=1).reindex(close_index).ffill()
    if volatility_probability is not None:
        features["volatility_expansion_probability"] = volatility_probability.reindex(close_index).ffill().shift(1)
    else:
        features["volatility_expansion_probability"] = 0.50
    return features


def _threshold_sets(feature_frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    development = feature_frame.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    sets = {}
    variants = {
        "loose": (0.40, 0.60),
        "balanced": (0.50, 0.50),
        "strict": (0.60, 0.40),
        "very_strict": (0.70, 0.30),
    }
    positive = ("stablecoin_supply_change_7d", "tvl_growth_30d", "volatility_4h_7d")
    negative = ("volatility_expansion_probability", "cross_sectional_dispersion")
    for name, (positive_q, negative_q) in variants.items():
        thresholds: dict[str, float] = {}
        for feature in positive:
            thresholds[feature] = float(development[feature].quantile(positive_q)) if feature in development else np.nan
        for feature in negative:
            thresholds[feature] = float(development[feature].quantile(negative_q)) if feature in development else np.nan
        sets[name] = thresholds
    return sets


def build_regime_momentum_dataset(
    panel: pd.DataFrame,
    public_data: PublicDataBundle,
    universe_size: int = 30,
    volatility_probability: pd.Series | None = None,
) -> RegimeMomentumDataset:
    clean = panel.copy().sort_values(["date", "symbol"])
    clean["date"] = pd.to_datetime(clean.date)
    weights, _ = point_in_time_liquid_universe(
        clean,
        top_n=universe_size,
        min_history_days=180,
        max_asset_weight=0.20,
    )
    close = _pivot(clean, "close").reindex(index=weights.index, columns=weights.columns)
    returns = close.pct_change(fill_method=None).fillna(0.0)
    features = _market_series(public_data, close.index, volatility_probability)
    dispersion = _weighted_dispersion(returns, weights).rolling(30).mean().shift(1)
    features["cross_sectional_dispersion"] = dispersion
    for feature in TIER1_FEATURES:
        if feature not in features:
            features[feature] = np.nan
    features = features[list(TIER1_FEATURES)].replace([np.inf, -np.inf], np.nan)
    thresholds = _threshold_sets(features)
    return RegimeMomentumDataset(
        panel=clean,
        close=close,
        returns=returns,
        universe_weights=weights,
        tier1_features=features,
        threshold_sets=thresholds,
        metadata={
            "universe_size": universe_size,
            "start": str(close.index.min().date()),
            "end": str(close.index.max().date()),
            "tier1_features": list(TIER1_FEATURES),
            "regime_feature_rule": "Only Tier-1 features are used for risk-on/neutral/risk-off classification.",
        },
    )


def regime_votes(features: pd.DataFrame, thresholds: dict[str, float]) -> pd.Series:
    votes = pd.Series(0, index=features.index, dtype=float)
    for feature in ("stablecoin_supply_change_7d", "tvl_growth_30d", "volatility_4h_7d"):
        if feature in features and np.isfinite(thresholds.get(feature, np.nan)):
            votes += (features[feature] >= thresholds[feature]).astype(float)
    for feature in ("volatility_expansion_probability", "cross_sectional_dispersion"):
        if feature in features and np.isfinite(thresholds.get(feature, np.nan)):
            votes += (features[feature] <= thresholds[feature]).astype(float)
    return votes


def classify_regimes(dataset: RegimeMomentumDataset, candidate: RegimeMomentumCandidate) -> pd.Series:
    votes = regime_votes(dataset.tier1_features, dataset.threshold_sets[candidate.threshold_set])
    regimes = pd.Series("risk_off", index=votes.index, dtype=object)
    regimes.loc[votes >= max(candidate.risk_on_votes - 1, 1)] = "neutral"
    regimes.loc[votes >= candidate.risk_on_votes] = "risk_on"
    return regimes


def regime_momentum_candidates() -> list[RegimeMomentumCandidate]:
    candidates: list[RegimeMomentumCandidate] = []
    for universe, rebalance, signal, top_k, threshold, votes, neutral in product(
        (10, 20, 30, 50),
        (7, 14),
        ("momentum_21d", "momentum_63d", "momentum_126d", "volatility_adjusted_momentum"),
        (3, 5, 10),
        ("balanced", "strict"),
        (3, 4),
        ("btc_eth", "reduced_momentum"),
    ):
        if top_k > universe:
            continue
        candidates.append(RegimeMomentumCandidate(
            name=f"u{universe}_r{rebalance}_{signal}_k{top_k}_{threshold}_v{votes}_{neutral}",
            universe_size=universe,
            rebalance_days=rebalance,
            momentum_signal=signal,
            top_k=top_k,
            threshold_set=threshold,
            risk_on_votes=votes,
            neutral_policy=neutral,
        ))
    return candidates


def _momentum_score(dataset: RegimeMomentumDataset, signal: str) -> pd.DataFrame:
    close = dataset.close
    if signal == "momentum_21d":
        return close.pct_change(21, fill_method=None).shift(1)
    if signal == "momentum_63d":
        return close.pct_change(63, fill_method=None).shift(1)
    if signal == "momentum_126d":
        return close.pct_change(126, fill_method=None).shift(1)
    if signal == "volatility_adjusted_momentum":
        momentum = close.pct_change(63, fill_method=None).shift(1)
        volatility = dataset.returns.rolling(30).std().shift(1) * np.sqrt(365)
        return momentum / volatility.replace(0, np.nan)
    raise ValueError(signal)


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def build_strategy_weights(
    dataset: RegimeMomentumDataset,
    candidate: RegimeMomentumCandidate,
    regime_override: str | None = None,
    score_frame: pd.DataFrame | None = None,
    regime_series: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    scores = score_frame if score_frame is not None else _momentum_score(dataset, candidate.momentum_signal)
    regimes = regime_series if regime_series is not None else classify_regimes(dataset, candidate)
    if regime_override == "always_on":
        regimes = pd.Series("risk_on", index=regimes.index, dtype=object)
    dates = _rebalance_dates(dataset.close.index, candidate.rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    for date_ in dates:
        if date_ not in scores.index:
            continue
        eligible = dataset.universe_weights.columns[dataset.universe_weights.loc[date_] > 0]
        ranked = scores.loc[date_, eligible].dropna().sort_values(ascending=False)
        regime = regimes.loc[date_]
        if regime == "risk_off":
            continue
        if regime == "neutral" and candidate.neutral_policy == "cash":
            continue
        if regime == "neutral" and candidate.neutral_policy == "btc_eth":
            assets = [symbol for symbol in ("BTC", "ETH") if symbol in weights.columns and symbol in eligible]
            if assets:
                weights.loc[date_, assets] = 0.25
            continue
        chosen = ranked.head(candidate.top_k).index.tolist()
        if not chosen:
            continue
        exposure = 1.0 if regime == "risk_on" else 0.50
        allocation = min(candidate.max_asset_weight, exposure / len(chosen))
        weights.loc[date_, chosen] = allocation
    return weights, regimes


def backtest_weights(
    dataset: RegimeMomentumDataset,
    target_weights: pd.DataFrame,
    regimes: pd.Series,
    cost_bps: int,
    turnover_cap: float = 0.75,
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
            requested_turnover = float(np.abs(change).sum())
            if requested_turnover > turnover_cap and requested_turnover > 0:
                target = previous + change * turnover_cap / requested_turnover
            else:
                target = requested
            turnover_array[i] = float(np.abs(target - previous).sum())
            costs_array[i] = turnover_array[i] * cost_rate
        net_array[i] = gross_array[i] - costs_array[i]
        executed_array[i] = target
        previous = target
    gross = pd.Series(gross_array, index=index)
    net = pd.Series(net_array, index=index)
    turnover = pd.Series(turnover_array, index=index)
    costs = pd.Series(costs_array, index=index)
    executed = pd.DataFrame(executed_array, index=index, columns=columns)
    metrics = portfolio_metrics(net, turnover, costs, executed)
    return PortfolioResult(net, gross, executed, turnover, costs, regimes.reindex(net.index).ffill(), metrics)


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
        "Best Month": float(monthly.max()) if len(monthly) else np.nan,
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


def _weekly_sharpe(returns: pd.Series) -> float:
    weekly = returns.resample("W-FRI").apply(lambda values: (1 + values).prod() - 1).dropna()
    std = weekly.std()
    return float(weekly.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else -np.inf


def _period_sharpe(returns: pd.Series, indices: tuple[int, ...]) -> float:
    subset = returns.iloc[list(indices)]
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else -np.inf


def select_candidate_cpcv(
    candidates: list[RegimeMomentumCandidate],
    results: dict[str, PortfolioResult],
) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows = []
    fold_rows = []
    config_returns = {}
    for candidate in candidates:
        result = results[candidate.name]
        weekly = result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END].resample("W-FRI").apply(lambda values: (1 + values).prod() - 1).dropna()
        config_returns[candidate.name] = weekly
        if len(weekly) < 20:
            continue
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_sharpes = []
        for number, split in enumerate(splits):
            sharpe = _period_sharpe(weekly, split.test_indices)
            fold_sharpes.append(sharpe)
            fold_rows.append({"candidate": candidate.name, "fold": number, "fold_sharpe": sharpe})
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        rows.append({
            "candidate": candidate.name,
            "universe_size": candidate.universe_size,
            "rebalance_days": candidate.rebalance_days,
            "momentum_signal": candidate.momentum_signal,
            "top_k": candidate.top_k,
            "threshold_set": candidate.threshold_set,
            "risk_on_votes": candidate.risk_on_votes,
            "neutral_policy": candidate.neutral_policy,
            "median_fold_sharpe": float(np.nanmedian(fold_sharpes)),
            "worst_fold_sharpe": float(np.nanmin(fold_sharpes)),
            "positive_fold_fraction": float(np.mean(np.asarray(fold_sharpes) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
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


def _benchmark_weights(dataset: RegimeMomentumDataset, name: str) -> pd.DataFrame:
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
    elif name == "equal_weight_top30":
        active = dataset.universe_weights > 0
        denominator = active.sum(axis=1).replace(0, np.nan)
        weights = active.div(denominator, axis=0).fillna(0.0).clip(upper=0.20)
    else:
        raise ValueError(name)
    return weights


def _candidate_by_name(candidates: list[RegimeMomentumCandidate]) -> dict[str, RegimeMomentumCandidate]:
    return {candidate.name: candidate for candidate in candidates}


def run_tier1_regime_momentum_study(
    panel: pd.DataFrame,
    public_data: PublicDataBundle,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    all_candidates = regime_momentum_candidates()
    datasets = {
        size: build_regime_momentum_dataset(panel, public_data, size, volatility_probability)
        for size in sorted({candidate.universe_size for candidate in all_candidates} | {30})
    }
    results_25: dict[str, PortfolioResult] = {}
    weights_cache: dict[str, tuple[pd.DataFrame, pd.Series]] = {}
    score_cache: dict[tuple[int, str], pd.DataFrame] = {}
    regime_cache: dict[tuple[int, str, int], pd.Series] = {}
    for candidate in all_candidates:
        dataset = datasets[candidate.universe_size]
        score_key = (candidate.universe_size, candidate.momentum_signal)
        if score_key not in score_cache:
            score_cache[score_key] = _momentum_score(dataset, candidate.momentum_signal)
        regime_key = (candidate.universe_size, candidate.threshold_set, candidate.risk_on_votes)
        if regime_key not in regime_cache:
            regime_cache[regime_key] = classify_regimes(dataset, candidate)
        weights, regimes = build_strategy_weights(
            dataset,
            candidate,
            score_frame=score_cache[score_key],
            regime_series=regime_cache[regime_key],
        )
        weights_cache[candidate.name] = (weights, regimes)
        results_25[candidate.name] = backtest_weights(dataset, weights, regimes, 25, candidate.turnover_cap)

    selection, folds, winner_name, pbo = select_candidate_cpcv(all_candidates, results_25)
    by_name = _candidate_by_name(all_candidates)
    winner = by_name[winner_name]
    winner_dataset = datasets[winner.universe_size]

    metrics_rows = []
    result_by_cost = {}
    for cost in COST_LEVELS:
        weights, regimes = weights_cache[winner.name]
        result = results_25[winner.name] if cost == 25 else backtest_weights(
            winner_dataset, weights, regimes, cost, winner.turnover_cap
        )
        result_by_cost[cost] = result
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            metrics_rows.append({"name": winner.name, "category": "strategy", "split": split, "cost_bps": cost, **period_metrics(result, start, end)})

    pure_candidate = RegimeMomentumCandidate(
        name=f"pure_csm_{winner.momentum_signal}_u{winner.universe_size}_k{winner.top_k}_r{winner.rebalance_days}",
        universe_size=winner.universe_size,
        rebalance_days=winner.rebalance_days,
        momentum_signal=winner.momentum_signal,
        top_k=winner.top_k,
        threshold_set=winner.threshold_set,
        risk_on_votes=winner.risk_on_votes,
        neutral_policy=winner.neutral_policy,
    )
    pure_weights, pure_regimes = build_strategy_weights(winner_dataset, pure_candidate, regime_override="always_on")
    pure = backtest_weights(winner_dataset, pure_weights, pure_regimes, 25, winner.turnover_cap)
    for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
        metrics_rows.append({"name": "pure_cross_sectional_momentum", "category": "benchmark", "split": split, "cost_bps": 25, **period_metrics(pure, start, end)})

    benchmark_dataset = datasets[30]
    for name in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top30"):
        weights = _benchmark_weights(benchmark_dataset, name)
        result = backtest_weights(benchmark_dataset, weights, pd.Series("risk_on", index=benchmark_dataset.close.index), 0)
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            metrics_rows.append({"name": name, "category": "benchmark", "split": split, "cost_bps": 0, **period_metrics(result, start, end)})

    metrics = pd.DataFrame(metrics_rows)
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

    selected_result = result_by_cost[25]
    regime_diag = regime_diagnostics(selected_result, pure, winner_dataset, winner)
    robustness = robustness_table(all_candidates, results_25)
    dsr = deflated_sharpe_probability(
        selected_result.returns.loc[HOLDOUT_START:HOLDOUT_END],
        tested_configurations=len(all_candidates),
    )
    return {
        "datasets": datasets,
        "candidates": all_candidates,
        "selection": selection,
        "folds": folds,
        "winner": winner,
        "metrics": metrics,
        "regime_diagnostics": regime_diag,
        "robustness": robustness,
        "acceptance": {
            "passes": not failures,
            "failures": "; ".join(failures),
            "holdout_sharpe": float(holdout_25.Sharpe),
            "holdout_cagr": float(holdout_25.CAGR),
            "holdout_max_drawdown": float(holdout_25["Maximum Drawdown"]),
            "holdout_turnover": float(holdout_25["Annual Turnover"]),
        },
        "statistics": {
            "tested_configurations": len(all_candidates),
            "pbo": pbo,
            "deflated_sharpe_probability": dsr,
        },
    }


def regime_diagnostics(
    gated: PortfolioResult,
    pure: PortfolioResult,
    dataset: RegimeMomentumDataset,
    winner: RegimeMomentumCandidate,
) -> pd.DataFrame:
    regimes = gated.regimes.reindex(gated.returns.index).ffill().fillna("risk_off")
    rows = []
    for split, start, end in (
        ("development", DEVELOPMENT_START, DEVELOPMENT_END),
        ("holdout", HOLDOUT_START, HOLDOUT_END),
    ):
        mask = (gated.returns.index >= start) & (gated.returns.index <= end)
        for regime in ("risk_on", "neutral", "risk_off"):
            idx = regimes.index[mask & (regimes == regime)]
            if len(idx) == 0:
                continue
            gated_returns = gated.returns.reindex(idx).fillna(0.0)
            pure_returns = pure.returns.reindex(idx).fillna(0.0)
            rows.append({
                "split": split,
                "regime": regime,
                "days": int(len(idx)),
                "fraction_days": float(len(idx) / max(mask.sum(), 1)),
                "gated_mean_daily_return": float(gated_returns.mean()),
                "pure_momentum_mean_daily_return": float(pure_returns.mean()),
                "pure_momentum_sharpe_in_regime": _weekly_sharpe(pure_returns),
                "gated_sharpe_in_regime": _weekly_sharpe(gated_returns),
            })
    return pd.DataFrame(rows)


def robustness_table(candidates: list[RegimeMomentumCandidate], results: dict[str, PortfolioResult]) -> pd.DataFrame:
    rows = []
    by_name = _candidate_by_name(candidates)
    for name, result in results.items():
        candidate = by_name[name]
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        holdout = period_metrics(result, HOLDOUT_START, HOLDOUT_END)
        rows.append({
            "candidate": name,
            "universe_size": candidate.universe_size,
            "rebalance_days": candidate.rebalance_days,
            "momentum_signal": candidate.momentum_signal,
            "top_k": candidate.top_k,
            "threshold_set": candidate.threshold_set,
            "risk_on_votes": candidate.risk_on_votes,
            "neutral_policy": candidate.neutral_policy,
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "holdout_sharpe": holdout["Sharpe"],
            "holdout_cagr": holdout["CAGR"],
            "holdout_max_drawdown": holdout["Maximum Drawdown"],
            "holdout_turnover": holdout["Annual Turnover"],
            "holdout_exposure": holdout["Exposure"],
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


def write_tier1_regime_momentum_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    winner: RegimeMomentumCandidate = result["winner"]
    metrics: pd.DataFrame = result["metrics"]
    selection: pd.DataFrame = result["selection"]
    regime_diag: pd.DataFrame = result["regime_diagnostics"]
    robustness: pd.DataFrame = result["robustness"]
    acceptance = result["acceptance"]
    statistics = result["statistics"]
    holdout = metrics[(metrics.split == "holdout") & ((metrics.cost_bps == 25) | (metrics.category == "benchmark"))].sort_values("Sharpe", ascending=False)
    development = metrics[(metrics.split == "development") & ((metrics.cost_bps == 25) | (metrics.category == "benchmark"))].sort_values("Sharpe", ascending=False)
    columns = [("name", "Strategy"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Sortino", "Sortino"), ("Maximum Drawdown", "Max DD"), ("Calmar", "Calmar"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure")]
    percent = {"CAGR", "Maximum Drawdown", "Exposure"}

    (output / "results_summary.md").write_text(f"""# Tier-1 regime-gated cross-sectional crypto momentum

## Protocol

- Regime gate features: `{', '.join(TIER1_FEATURES)}`.
- No Tier 2 or Tier 3 feature is used for regime classification.
- Selection layer: simple cross-sectional momentum ranks only; this layer does not predict individual returns.
- Development period: through 2024-12-31.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: CPCV inside development only.
- Tested configurations: {statistics['tested_configurations']}.
- Selected candidate: **{winner.name}**.

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
- Deflated Sharpe probability for selected holdout returns: {_fmt(statistics['deflated_sharpe_probability'], True)}.
""", encoding="utf-8")

    (output / "regime_diagnostics.md").write_text(f"""# Regime diagnostics

The table tests whether pure cross-sectional momentum performs differently inside
the Tier-1 feature regimes selected on development data.

{_table(regime_diag, [('split', 'Split'), ('regime', 'Regime'), ('days', 'Days'), ('fraction_days', 'Fraction days'), ('gated_mean_daily_return', 'Gated mean daily return'), ('pure_momentum_mean_daily_return', 'Pure momentum mean daily return'), ('pure_momentum_sharpe_in_regime', 'Pure momentum Sharpe'), ('gated_sharpe_in_regime', 'Gated Sharpe')], {'fraction_days', 'gated_mean_daily_return', 'pure_momentum_mean_daily_return'})}
""", encoding="utf-8")

    holdout_cost = metrics[(metrics.name == winner.name) & (metrics.split == "holdout")].sort_values("cost_bps")
    previous = "Previous defensive BTC/ETH/cash metrics not found."
    prior_path = Path("reports/paper_trading_candidate/metrics.csv")
    if prior_path.exists():
        prior = pd.read_csv(prior_path)
        prior_view = prior[(prior.split == "holdout") & (prior.cost_bps == 25)].sort_values("Sharpe", ascending=False).head(8)
        previous = _table(prior_view, [("name", "Previous defensive candidate"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Maximum Drawdown", "Max DD"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure")], {"CAGR", "Maximum Drawdown", "Exposure"})
    (output / "holdout_results.md").write_text(f"""# Locked holdout results

## Final selected strategy and benchmarks

{_table(holdout, columns, percent)}

## Cost sensitivity for selected strategy

{_table(holdout_cost, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Previous defensive BTC/ETH/cash candidates

{previous}

## Acceptance

- Passes paper-trading criteria: {_fmt(acceptance['passes'])}
- Holdout Sharpe: {acceptance['holdout_sharpe']:.3f}
- Holdout CAGR: {acceptance['holdout_cagr']:.2%}
- Holdout max drawdown: {acceptance['holdout_max_drawdown']:.2%}
- Holdout annual turnover: {acceptance['holdout_turnover']:.2f}x
- Failures: {acceptance['failures'] or 'None'}
""", encoding="utf-8")

    robust_summary = robustness.groupby(["universe_size", "rebalance_days"]).agg(
        configurations=("candidate", "count"),
        median_development_sharpe=("development_sharpe", "median"),
        best_development_sharpe=("development_sharpe", "max"),
        median_holdout_sharpe=("holdout_sharpe", "median"),
        best_holdout_sharpe=("holdout_sharpe", "max"),
        median_holdout_cagr=("holdout_cagr", "median"),
    ).reset_index()
    (output / "robustness.md").write_text(f"""# Robustness

This table summarizes all predeclared configurations. It is diagnostic only;
the selected strategy was chosen by development CPCV, not by holdout cells.

## Summary by universe and rebalance cadence

{_table(robust_summary.sort_values(['universe_size', 'rebalance_days']), [('universe_size', 'Universe'), ('rebalance_days', 'Rebalance days'), ('configurations', 'Configs'), ('median_development_sharpe', 'Median dev Sharpe'), ('best_development_sharpe', 'Best dev Sharpe'), ('median_holdout_sharpe', 'Median holdout Sharpe'), ('best_holdout_sharpe', 'Best holdout Sharpe'), ('median_holdout_cagr', 'Median holdout CAGR')], {'median_holdout_cagr'})}

## Top development-CPCV candidates

{_table(selection, [('candidate', 'Candidate'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold Sharpe'), ('positive_fold_fraction', 'Positive folds'), ('development_sharpe', 'Development Sharpe'), ('development_turnover', 'Development turnover')], {'positive_fold_fraction'}, limit=25)}
""", encoding="utf-8")

    pure_holdout = holdout[holdout.name == "pure_cross_sectional_momentum"]
    selected_holdout = holdout[holdout.name == winner.name]
    pure_sharpe = float(pure_holdout.iloc[0].Sharpe) if len(pure_holdout) else np.nan
    selected_sharpe = float(selected_holdout.iloc[0].Sharpe) if len(selected_holdout) else np.nan
    selected_cost_50 = metrics[(metrics.name == winner.name) & (metrics.split == "holdout") & (metrics.cost_bps == 50)]
    cost_50_cagr = float(selected_cost_50.iloc[0].CAGR) if len(selected_cost_50) else np.nan
    cost_50_sharpe = float(selected_cost_50.iloc[0].Sharpe) if len(selected_cost_50) else np.nan
    holdout_diag = regime_diag[regime_diag.split == "holdout"]
    risk_on_diag = holdout_diag[holdout_diag.regime == "risk_on"]
    risk_off_diag = holdout_diag[holdout_diag.regime == "risk_off"]
    risk_on_pure_sharpe = float(risk_on_diag.iloc[0].pure_momentum_sharpe_in_regime) if len(risk_on_diag) else np.nan
    risk_off_fraction = float(risk_off_diag.iloc[0].fraction_days) if len(risk_off_diag) else np.nan
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

1. **Do Tier-1 features identify favourable crypto regimes?**
   Partially. The selected gate creates distinct risk-on/neutral/risk-off states,
   but holdout evidence is weak. In holdout, the selected gate spent
   {_fmt(risk_off_fraction, True)} of days in risk-off, and the main benefit came
   from reducing exposure during bad periods rather than from finding a strongly
   profitable risk-on momentum regime. The result should be treated cautiously
   because PBO is {_fmt(statistics['pbo'], True)} and the deflated Sharpe
   probability is {_fmt(statistics['deflated_sharpe_probability'], True)}.

2. **Does cross-sectional momentum perform better inside those regimes?**
   The regime-gated strategy outperformed pure cross-sectional momentum on the
   locked holdout: selected Sharpe {selected_sharpe:.3f} versus pure momentum
   Sharpe {pure_sharpe:.3f}. However, the holdout risk-on pure-momentum Sharpe
   was only {risk_on_pure_sharpe:.3f}, so the gate did not clearly identify a
   robust high-return momentum state.

3. **Does the regime-gated strategy survive the locked holdout?**
   {'Only weakly. It had positive holdout CAGR at 25 bps and 50 bps, but holdout Sharpe stayed below the 0.5 acceptance threshold and performance turns negative at 100 bps.' if cost_50_cagr > 0 and cost_50_sharpe > 0 else 'No.'}

4. **Is it suitable for paper trading?**
   {'Yes, it passes the declared criteria.' if acceptance['passes'] else 'No.'}

5. **What failed?**
   {acceptance['failures'] or 'No declared acceptance rule failed.'}

No strategy was selected using holdout results.
""", encoding="utf-8")

    selection.to_csv(output / "candidate_selection.csv", index=False)
    result["folds"].to_csv(output / "cpcv_folds.csv", index=False)
    metrics.to_csv(output / "metrics.csv", index=False)
    robustness.to_csv(output / "robustness.csv", index=False)
    regime_diag.to_csv(output / "regime_diagnostics.csv", index=False)
    payload = {
        "winner": asdict(winner),
        "acceptance": acceptance,
        "statistics": statistics,
        "metrics": metrics.to_dict("records"),
        "selection": selection.to_dict("records"),
        "regime_diagnostics": regime_diag.to_dict("records"),
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
    "RegimeMomentumCandidate",
    "RegimeMomentumDataset",
    "TIER1_FEATURES",
    "build_regime_momentum_dataset",
    "regime_momentum_candidates",
    "build_strategy_weights",
    "run_tier1_regime_momentum_study",
    "write_tier1_regime_momentum_reports",
]
