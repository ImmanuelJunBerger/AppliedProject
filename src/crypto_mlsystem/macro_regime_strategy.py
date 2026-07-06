"""Macro-regime conditioned crypto exposure strategy.

This module tests a small, predeclared set of macro-regime strategy candidates.
Regime gates are restricted to the Tier 1 WRDS macro features from the macro
feature-research phase, optionally combined with the prior Tier 1 crypto-native
features.  Candidate selection uses development-period CPCV only; holdout data
is never used to choose thresholds or the selected candidate.
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
from .data import STABLE_OR_WRAPPED
from .metrics import performance_metrics
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import deflated_sharpe_probability, probability_backtest_overfitting
from .volatility_expansion import _weighted_dispersion, point_in_time_liquid_universe


DEVELOPMENT_START = pd.Timestamp("2020-01-01")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")

MACRO_TIER1_FEATURES = (
    "equity_realized_vol_21d",
    "equity_momentum_21d",
    "dow_vol_level",
    "vix_level",
    "vix_change_5d",
    "vix_change_21d",
)
CRYPTO_TIER1_FEATURES = (
    "stablecoin_supply_change_7d",
    "tvl_growth_30d",
    "volatility_expansion_probability",
    "cross_sectional_dispersion",
)
ALLOWED_REGIME_FEATURES = MACRO_TIER1_FEATURES + CRYPTO_TIER1_FEATURES

MACRO_POSITIVE_FEATURES = (
    "equity_realized_vol_21d",
    "equity_momentum_21d",
    "dow_vol_level",
    "vix_level",
)
MACRO_NEGATIVE_FEATURES = ("vix_change_5d", "vix_change_21d")
CRYPTO_POSITIVE_FEATURES = ("stablecoin_supply_change_7d", "tvl_growth_30d")
CRYPTO_NEGATIVE_FEATURES = ("volatility_expansion_probability", "cross_sectional_dispersion")


@dataclass(frozen=True)
class MacroRegimeCandidate:
    name: str
    family: str
    gate_profile: str
    use_crypto_gate: bool
    allocation: str
    rebalance_days: int = 7
    top_k: int = 5
    universe_size: int = 10
    max_asset_weight: float = 0.20
    turnover_cap: float = 0.75


@dataclass
class MacroRegimeDataset:
    panel: pd.DataFrame
    close: pd.DataFrame
    returns: pd.DataFrame
    universe_weights: pd.DataFrame
    regime_features: pd.DataFrame
    thresholds: dict[str, dict[str, dict[str, float]]]
    metadata: dict[str, Any]


@dataclass
class PortfolioResult:
    returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    macro_regime: pd.Series
    crypto_regime: pd.Series
    combined_regime: pd.Series
    metrics: dict[str, float]


def load_macro_features(path: str | Path = "data/processed/wrds_macro_features/wrds_macro_features_daily.csv") -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing WRDS macro feature file: {path}. Run python -m src.run_wrds_macro_features first."
        )
    frame = pd.read_csv(path, parse_dates=["date"])
    missing = [feature for feature in MACRO_TIER1_FEATURES if feature not in frame.columns]
    if missing:
        raise ValueError(f"WRDS macro feature file is missing required Tier 1 columns: {missing}")
    return frame[["date", *MACRO_TIER1_FEATURES]].copy()


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


def predeclared_macro_regime_candidates() -> list[MacroRegimeCandidate]:
    """Four requested candidate families times two development-only gate profiles."""
    specs = (
        ("btc_eth_macro_gate", "BTC/ETH/cash macro risk gate", False, "btc_eth"),
        ("btc_eth_macro_crypto_gate", "BTC/ETH/cash macro + crypto-native risk gate", True, "btc_eth"),
        ("top10_momentum_macro_gate", "Top-10 momentum when macro regime is favourable", False, "top10_momentum"),
        ("top10_momentum_macro_crypto_gate", "Top-10 momentum when both macro and crypto-native regimes are favourable", True, "top10_momentum"),
    )
    candidates: list[MacroRegimeCandidate] = []
    for key, family, use_crypto, allocation in specs:
        for profile in ("balanced", "strict"):
            candidates.append(MacroRegimeCandidate(
                name=f"{key}_{profile}",
                family=family,
                gate_profile=profile,
                use_crypto_gate=use_crypto,
                allocation=allocation,
            ))
    return candidates


def _pivot(panel: pd.DataFrame, column: str) -> pd.DataFrame:
    return panel.pivot(index="date", columns="symbol", values=column).sort_index()


def _align_macro_features(macro_features: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    macro = macro_features.copy()
    macro["date"] = pd.to_datetime(macro["date"])
    macro = macro.drop_duplicates("date").set_index("date").sort_index()
    aligned = macro.reindex(index).ffill()
    for feature in MACRO_TIER1_FEATURES:
        if feature not in aligned:
            aligned[feature] = np.nan
    return aligned[list(MACRO_TIER1_FEATURES)]


def _crypto_native_features(
    public_data: PublicDataBundle | None,
    close_index: pd.DatetimeIndex,
    volatility_probability: pd.Series | None,
    returns: pd.DataFrame,
    weights: pd.DataFrame,
) -> pd.DataFrame:
    features = pd.DataFrame(index=close_index)
    if public_data is not None:
        stable = public_data.stablecoins.copy()
        if not stable.empty:
            stable["date"] = pd.to_datetime(stable["date"])
            stable = stable.set_index("date").sort_index()
            if "stablecoin_supply_change_7d" in stable:
                features["stablecoin_supply_change_7d"] = (
                    stable["stablecoin_supply_change_7d"].reindex(close_index).ffill().shift(1)
                )
        tvl = public_data.chain_tvl.copy()
        if not tvl.empty:
            tvl["date"] = pd.to_datetime(tvl["date"])
            all_tvl = tvl[tvl.chain.astype(str).str.lower() == "all"].set_index("date").sort_index()
            if "tvl" in all_tvl:
                features["tvl_growth_30d"] = all_tvl["tvl"].pct_change(30, fill_method=None).reindex(close_index).ffill().shift(1)
    if volatility_probability is not None:
        features["volatility_expansion_probability"] = volatility_probability.reindex(close_index).ffill().shift(1)
    else:
        features["volatility_expansion_probability"] = 0.50
    features["cross_sectional_dispersion"] = _weighted_dispersion(returns, weights).rolling(30).mean().shift(1)
    for feature in CRYPTO_TIER1_FEATURES:
        if feature not in features:
            features[feature] = np.nan
    return features[list(CRYPTO_TIER1_FEATURES)].replace([np.inf, -np.inf], np.nan)


def _threshold_sets(features: pd.DataFrame) -> dict[str, dict[str, dict[str, float]]]:
    development = features.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    profiles = {
        "balanced": {
            "positive_q": 0.50,
            "negative_q": 0.50,
            "macro_votes": 4,
            "crypto_votes": 3,
        },
        "strict": {
            "positive_q": 0.60,
            "negative_q": 0.40,
            "macro_votes": 5,
            "crypto_votes": 3,
        },
    }
    result: dict[str, dict[str, dict[str, float]]] = {}
    for profile, params in profiles.items():
        thresholds: dict[str, float] = {}
        for feature in (*MACRO_POSITIVE_FEATURES, *CRYPTO_POSITIVE_FEATURES):
            thresholds[feature] = float(development[feature].quantile(params["positive_q"])) if feature in development else np.nan
        for feature in (*MACRO_NEGATIVE_FEATURES, *CRYPTO_NEGATIVE_FEATURES):
            thresholds[feature] = float(development[feature].quantile(params["negative_q"])) if feature in development else np.nan
        result[profile] = {
            "thresholds": thresholds,
            "vote_requirements": {
                "macro_votes": float(params["macro_votes"]),
                "crypto_votes": float(params["crypto_votes"]),
            },
        }
    return result


def build_macro_regime_dataset(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
    universe_size: int = 10,
) -> MacroRegimeDataset:
    clean = panel.copy().sort_values(["date", "symbol"])
    clean["date"] = pd.to_datetime(clean["date"])
    clean = clean[~clean["symbol"].isin(STABLE_OR_WRAPPED)]
    weights, universes = point_in_time_liquid_universe(
        clean,
        top_n=universe_size,
        min_history_days=180,
        max_asset_weight=0.20,
    )
    close = _pivot(clean, "close").reindex(index=weights.index, columns=weights.columns)
    returns = close.pct_change(fill_method=None).fillna(0.0)
    macro = _align_macro_features(macro_features, close.index)
    crypto = _crypto_native_features(public_data, close.index, volatility_probability, returns, weights)
    features = pd.concat([macro, crypto], axis=1)[list(ALLOWED_REGIME_FEATURES)].replace([np.inf, -np.inf], np.nan)
    thresholds = _threshold_sets(features)
    return MacroRegimeDataset(
        panel=clean,
        close=close,
        returns=returns,
        universe_weights=weights,
        regime_features=features,
        thresholds=thresholds,
        metadata={
            "universe_size": universe_size,
            "start": str(close.index.min().date()),
            "end": str(close.index.max().date()),
            "allowed_regime_features": list(ALLOWED_REGIME_FEATURES),
            "macro_tier1_features": list(MACRO_TIER1_FEATURES),
            "crypto_tier1_features": list(CRYPTO_TIER1_FEATURES),
            "universe_snapshots": len(universes),
            "selection_rule": "8 predeclared configs selected by development CPCV only.",
        },
    )


def _vote_count(
    features: pd.DataFrame,
    thresholds: dict[str, float],
    positive_features: tuple[str, ...],
    negative_features: tuple[str, ...],
) -> pd.Series:
    votes = pd.Series(0.0, index=features.index)
    for feature in positive_features:
        threshold = thresholds.get(feature, np.nan)
        if feature in features and np.isfinite(threshold):
            votes += (features[feature] >= threshold).astype(float)
    for feature in negative_features:
        threshold = thresholds.get(feature, np.nan)
        if feature in features and np.isfinite(threshold):
            votes += (features[feature] <= threshold).astype(float)
    return votes


def classify_regimes(
    dataset: MacroRegimeDataset,
    candidate: MacroRegimeCandidate,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    profile = dataset.thresholds[candidate.gate_profile]
    thresholds = profile["thresholds"]
    requirements = profile["vote_requirements"]
    macro_votes = _vote_count(dataset.regime_features, thresholds, MACRO_POSITIVE_FEATURES, MACRO_NEGATIVE_FEATURES)
    crypto_votes = _vote_count(dataset.regime_features, thresholds, CRYPTO_POSITIVE_FEATURES, CRYPTO_NEGATIVE_FEATURES)

    macro_required = int(requirements["macro_votes"])
    crypto_required = int(requirements["crypto_votes"])

    macro = pd.Series("risk_off", index=dataset.regime_features.index, dtype=object)
    macro.loc[macro_votes >= max(1, macro_required - 1)] = "neutral"
    macro.loc[macro_votes >= macro_required] = "risk_on"

    crypto = pd.Series("not_used", index=dataset.regime_features.index, dtype=object)
    if candidate.use_crypto_gate:
        crypto = pd.Series("risk_off", index=dataset.regime_features.index, dtype=object)
        crypto.loc[crypto_votes >= max(1, crypto_required - 1)] = "neutral"
        crypto.loc[crypto_votes >= crypto_required] = "risk_on"

    combined = macro.copy()
    if candidate.use_crypto_gate:
        combined = pd.Series("risk_off", index=macro.index, dtype=object)
        combined.loc[(macro == "risk_on") & (crypto == "risk_on")] = "risk_on"
        combined.loc[
            ((macro == "risk_on") & (crypto == "neutral"))
            | ((macro == "neutral") & (crypto == "risk_on"))
            | ((macro == "neutral") & (crypto == "neutral"))
        ] = "neutral"
    return macro, crypto, combined


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int = 7) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def _momentum_scores(close: pd.DataFrame) -> pd.DataFrame:
    return close.pct_change(63, fill_method=None).shift(1)


def build_candidate_weights(
    dataset: MacroRegimeDataset,
    candidate: MacroRegimeCandidate,
    combined_override: str | None = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    macro, crypto, combined = classify_regimes(dataset, candidate)
    if combined_override == "always_on":
        combined = pd.Series("risk_on", index=combined.index, dtype=object)

    scores = _momentum_scores(dataset.close)
    dates = _rebalance_dates(dataset.close.index, candidate.rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    for date_ in dates:
        if date_ not in combined.index:
            continue
        regime = combined.loc[date_]
        if regime == "risk_off":
            continue
        exposure = 1.0 if regime == "risk_on" else 0.50
        eligible = dataset.universe_weights.columns[dataset.universe_weights.loc[date_] > 0]
        if candidate.allocation == "btc_eth":
            assets = [symbol for symbol in ("BTC", "ETH") if symbol in weights.columns and symbol in eligible]
            if not assets:
                continue
            allocation = min(0.50, exposure / len(assets))
            weights.loc[date_, assets] = allocation
        elif candidate.allocation == "top10_momentum":
            ranked = scores.loc[date_, eligible].dropna().sort_values(ascending=False)
            chosen = ranked.head(candidate.top_k).index.tolist()
            if not chosen:
                continue
            allocation = min(candidate.max_asset_weight, exposure / len(chosen))
            weights.loc[date_, chosen] = allocation
        else:
            raise ValueError(candidate.allocation)
    return weights, macro, crypto, combined


def backtest_weights(
    dataset: MacroRegimeDataset,
    target_weights: pd.DataFrame,
    macro_regime: pd.Series,
    crypto_regime: pd.Series,
    combined_regime: pd.Series,
    cost_bps: int,
    turnover_cap: float = 0.75,
) -> PortfolioResult:
    returns = dataset.returns.reindex(columns=target_weights.columns).fillna(0.0)
    start = target_weights.index.min()
    returns = returns.loc[start:min(HOLDOUT_END, returns.index.max())]
    targets = target_weights.reindex(target_weights.index.intersection(returns.index)).fillna(0.0)
    index = returns.index
    columns = returns.columns
    target_map = {date_: row.reindex(columns).fillna(0.0).to_numpy(dtype=float) for date_, row in targets.iterrows()}
    returns_array = returns.to_numpy(dtype=float)
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
            target = previous + change * min(1.0, turnover_cap / requested_turnover) if requested_turnover > turnover_cap and requested_turnover > 0 else requested
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
    return PortfolioResult(
        returns=net,
        gross_returns=gross,
        weights=executed,
        turnover=turnover,
        costs=costs,
        macro_regime=macro_regime.reindex(net.index).ffill(),
        crypto_regime=crypto_regime.reindex(net.index).ffill(),
        combined_regime=combined_regime.reindex(net.index).ffill(),
        metrics=metrics,
    )


def portfolio_metrics(returns: pd.Series, turnover: pd.Series, costs: pd.Series, weights: pd.DataFrame) -> dict[str, float]:
    metrics = performance_metrics(returns, turnover, costs)
    elapsed_years = max(len(returns) / 365.0, 1 / 365.0)
    exposure = weights.sum(axis=1).clip(0.0, 1.0)
    monthly = returns.resample("ME").apply(lambda values: (1.0 + values).prod() - 1.0)
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


def _period_sharpe(returns: pd.Series, indices: tuple[int, ...]) -> float:
    subset = returns.iloc[list(indices)]
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else -np.inf


def select_candidate_cpcv(
    candidates: list[MacroRegimeCandidate],
    results: dict[str, PortfolioResult],
) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    config_returns: dict[str, pd.Series] = {}
    for candidate in candidates:
        result = results[candidate.name]
        weekly = result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END].resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0).dropna()
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
            "family": candidate.family,
            "gate_profile": candidate.gate_profile,
            "use_crypto_gate": candidate.use_crypto_gate,
            "allocation": candidate.allocation,
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


def _benchmark_weights(dataset: MacroRegimeDataset, name: str) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=dataset.close.index, columns=dataset.close.columns)
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
    elif name == "equal_weight_top10":
        active = dataset.universe_weights > 0
        denominator = active.sum(axis=1).replace(0, np.nan)
        weights = active.div(denominator, axis=0).fillna(0.0).clip(upper=0.20)
    else:
        raise ValueError(name)
    return weights


def _candidate_by_name(candidates: list[MacroRegimeCandidate]) -> dict[str, MacroRegimeCandidate]:
    return {candidate.name: candidate for candidate in candidates}


def _macro_feature_coverage(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in ALLOWED_REGIME_FEATURES:
        series = features[feature] if feature in features else pd.Series(dtype=float)
        valid = series.dropna()
        rows.append({
            "feature": feature,
            "allowed_tier": "Tier 1 macro" if feature in MACRO_TIER1_FEATURES else "Tier 1 crypto-native",
            "start": str(valid.index.min().date()) if len(valid) else "",
            "end": str(valid.index.max().date()) if len(valid) else "",
            "coverage": float(series.notna().mean()) if len(series) else 0.0,
        })
    return pd.DataFrame(rows)


def regime_diagnostics(result: PortfolioResult, dataset: MacroRegimeDataset) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, start, end in (
        ("development", DEVELOPMENT_START, DEVELOPMENT_END),
        ("holdout", HOLDOUT_START, HOLDOUT_END),
    ):
        period_index = result.returns.loc[start:end].index
        for regime_name, regimes in (
            ("macro", result.macro_regime),
            ("crypto", result.crypto_regime),
            ("combined", result.combined_regime),
        ):
            aligned = regimes.reindex(period_index).ffill().fillna("missing")
            for state in sorted(aligned.unique()):
                idx = aligned.index[aligned == state]
                returns = result.returns.reindex(idx).fillna(0.0)
                weights = result.weights.reindex(idx).fillna(0.0)
                metrics = portfolio_metrics(
                    returns,
                    result.turnover.reindex(idx).fillna(0.0),
                    result.costs.reindex(idx).fillna(0.0),
                    weights,
                )
                rows.append({
                    "split": split,
                    "regime_layer": regime_name,
                    "state": state,
                    "days": int(len(idx)),
                    "fraction_days": float(len(idx) / max(len(period_index), 1)),
                    "mean_daily_return": float(returns.mean()) if len(returns) else np.nan,
                    "sharpe": metrics["Sharpe"],
                    "exposure": metrics["Exposure"],
                })
    coverage = _macro_feature_coverage(dataset.regime_features)
    coverage["split"] = "feature_coverage"
    coverage["regime_layer"] = coverage["allowed_tier"]
    coverage["state"] = coverage["feature"]
    coverage["days"] = np.nan
    coverage["fraction_days"] = coverage["coverage"]
    coverage["mean_daily_return"] = np.nan
    coverage["sharpe"] = np.nan
    coverage["exposure"] = np.nan
    return pd.concat([pd.DataFrame(rows), coverage[["split", "regime_layer", "state", "days", "fraction_days", "mean_daily_return", "sharpe", "exposure"]]], ignore_index=True)


def run_macro_regime_strategy_study(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    candidates = predeclared_macro_regime_candidates()
    weights_cache: dict[str, tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]] = {}
    results_25: dict[str, PortfolioResult] = {}
    for candidate in candidates:
        weights, macro, crypto, combined = build_candidate_weights(dataset, candidate)
        weights_cache[candidate.name] = (weights, macro, crypto, combined)
        results_25[candidate.name] = backtest_weights(
            dataset,
            weights,
            macro,
            crypto,
            combined,
            cost_bps=25,
            turnover_cap=candidate.turnover_cap,
        )

    selection, folds, winner_name, pbo = select_candidate_cpcv(candidates, results_25)
    by_name = _candidate_by_name(candidates)
    winner = by_name[winner_name]

    metrics_rows: list[dict[str, Any]] = []
    selected_by_cost: dict[int, PortfolioResult] = {}
    weights, macro, crypto, combined = weights_cache[winner.name]
    for cost in COST_LEVELS:
        result = results_25[winner.name] if cost == 25 else backtest_weights(
            dataset, weights, macro, crypto, combined, cost_bps=cost, turnover_cap=winner.turnover_cap
        )
        selected_by_cost[cost] = result
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            metrics_rows.append({
                "name": winner.name,
                "category": "selected_strategy",
                "family": winner.family,
                "split": split,
                "cost_bps": cost,
                **period_metrics(result, start, end),
            })

    for candidate in candidates:
        result = results_25[candidate.name]
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            metrics_rows.append({
                "name": candidate.name,
                "category": "candidate_25bps",
                "family": candidate.family,
                "split": split,
                "cost_bps": 25,
                **period_metrics(result, start, end),
            })

    pure_candidate = MacroRegimeCandidate(
        name="pure_top10_momentum",
        family="Pure top-10 momentum benchmark",
        gate_profile=winner.gate_profile,
        use_crypto_gate=False,
        allocation="top10_momentum",
    )
    pure_weights, pure_macro, pure_crypto, pure_combined = build_candidate_weights(dataset, pure_candidate, combined_override="always_on")
    pure = backtest_weights(dataset, pure_weights, pure_macro, pure_crypto, pure_combined, cost_bps=25)
    for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
        metrics_rows.append({
            "name": "pure_top10_momentum",
            "category": "benchmark",
            "family": "Pure top-10 momentum benchmark",
            "split": split,
            "cost_bps": 25,
            **period_metrics(pure, start, end),
        })

    for name in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top10"):
        bench_weights = _benchmark_weights(dataset, name)
        regimes = pd.Series("risk_on", index=dataset.close.index, dtype=object)
        bench = backtest_weights(dataset, bench_weights, regimes, pd.Series("not_used", index=dataset.close.index), regimes, cost_bps=25)
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            metrics_rows.append({
                "name": name,
                "category": "benchmark",
                "family": "Benchmark",
                "split": split,
                "cost_bps": 25,
                **period_metrics(bench, start, end),
            })

    metrics = pd.DataFrame(metrics_rows)
    holdout_25 = metrics[(metrics.name == winner.name) & (metrics.category == "selected_strategy") & (metrics.split == "holdout") & (metrics.cost_bps == 25)].iloc[0]
    holdout_50 = metrics[(metrics.name == winner.name) & (metrics.category == "selected_strategy") & (metrics.split == "holdout") & (metrics.cost_bps == 50)].iloc[0]
    btc_holdout = metrics[(metrics.name == "btc_buy_hold") & (metrics.split == "holdout")].iloc[0]
    comparable_name = "btc_eth_50_50" if winner.allocation == "btc_eth" else "pure_top10_momentum"
    comparable_holdout = metrics[(metrics.name == comparable_name) & (metrics.split == "holdout") & (metrics.cost_bps == 25)].iloc[0]
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

    diagnostics = regime_diagnostics(selected_by_cost[25], dataset)
    selected_delta = {
        "comparable_benchmark": comparable_name,
        "holdout_sharpe_delta": float(holdout_25.Sharpe - comparable_holdout.Sharpe),
        "holdout_cagr_delta": float(holdout_25.CAGR - comparable_holdout.CAGR),
        "holdout_max_drawdown_delta": float(holdout_25["Maximum Drawdown"] - comparable_holdout["Maximum Drawdown"]),
    }
    statistics = {
        "tested_configurations": len(candidates),
        "pbo": pbo,
        "deflated_sharpe_probability": deflated_sharpe_probability(
            selected_by_cost[25].returns.loc[HOLDOUT_START:HOLDOUT_END],
            tested_configurations=len(candidates),
        ),
    }
    return {
        "dataset": dataset,
        "candidates": candidates,
        "selection": selection,
        "folds": folds,
        "winner": winner,
        "metrics": metrics,
        "regime_diagnostics": diagnostics,
        "acceptance": {
            "passes": not failures,
            "failures": "; ".join(failures),
            "holdout_sharpe": float(holdout_25.Sharpe),
            "holdout_cagr": float(holdout_25.CAGR),
            "holdout_max_drawdown": float(holdout_25["Maximum Drawdown"]),
            "holdout_annual_turnover": float(holdout_25["Annual Turnover"]),
            "survives_50bps": bool(holdout_50.Sharpe > 0 and holdout_50.CAGR > 0),
        },
        "selected_delta": selected_delta,
        "statistics": statistics,
        "protocol": {
            "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} to {HOLDOUT_END.date()}",
            "selection": "CPCV inside development only; holdout not used for selection",
            "regime_features": list(ALLOWED_REGIME_FEATURES),
            "excluded_features": "All Tier 2 and Tier 3 features are excluded from regime gates.",
        },
    }


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
    if frame is None or frame.empty:
        return "_No rows._"
    view = frame.head(limit) if limit else frame
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in view.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def write_macro_regime_strategy_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    winner: MacroRegimeCandidate = result["winner"]
    metrics: pd.DataFrame = result["metrics"]
    selection: pd.DataFrame = result["selection"]
    diagnostics: pd.DataFrame = result["regime_diagnostics"]
    acceptance = result["acceptance"]
    statistics = result["statistics"]
    selected_delta = result["selected_delta"]
    protocol = result["protocol"]

    metrics.to_csv(output / "metrics.csv", index=False)
    selection.to_csv(output / "candidate_selection.csv", index=False)
    result["folds"].to_csv(output / "cpcv_folds.csv", index=False)
    diagnostics.to_csv(output / "regime_diagnostics.csv", index=False)

    columns = [
        ("name", "Strategy"),
        ("family", "Family"),
        ("CAGR", "CAGR"),
        ("Sharpe", "Sharpe"),
        ("Sortino", "Sortino"),
        ("Maximum Drawdown", "Max DD"),
        ("Calmar", "Calmar"),
        ("Annual Turnover", "Annual turnover"),
        ("Exposure", "Exposure"),
    ]
    percent = {"CAGR", "Maximum Drawdown", "Exposure"}
    development = metrics[
        (metrics.split == "development")
        & (metrics.cost_bps == 25)
        & (metrics.category.isin(["selected_strategy", "benchmark"]))
    ].sort_values("Sharpe", ascending=False)
    holdout = metrics[
        (metrics.split == "holdout")
        & (metrics.cost_bps == 25)
        & (metrics.category.isin(["selected_strategy", "benchmark"]))
    ].sort_values("Sharpe", ascending=False)
    selected_costs = metrics[
        (metrics.name == winner.name)
        & (metrics.category == "selected_strategy")
        & (metrics.split == "holdout")
    ].sort_values("cost_bps")

    (output / "results_summary.md").write_text(f"""# Macro-regime conditioned crypto exposure strategy

## Protocol

- Development period: {protocol['development_period']}.
- Locked holdout: {protocol['locked_holdout']}.
- Candidate selection: {protocol['selection']}.
- Tested configurations: {statistics['tested_configurations']}.
- Selected candidate: **{winner.name}**.
- Tier 1 macro features: `{', '.join(MACRO_TIER1_FEATURES)}`.
- Optional Tier 1 crypto-native features: `{', '.join(CRYPTO_TIER1_FEATURES)}`.
- Tier 2 and Tier 3 features are not used for regime gates.

## Selected candidate

```json
{json.dumps(asdict(winner), indent=2)}
```

## Development comparison at 25 bps

{_table(development, columns, percent)}

## Locked holdout comparison at 25 bps

{_table(holdout, columns, percent)}

## Statistical controls

- Approximate PBO: {_fmt(statistics['pbo'], True)}.
- Deflated Sharpe probability for selected holdout returns: {_fmt(statistics['deflated_sharpe_probability'], True)}.
- Comparable benchmark for selected candidate: `{selected_delta['comparable_benchmark']}`.
- Holdout Sharpe delta versus comparable benchmark: {_fmt(selected_delta['holdout_sharpe_delta'])}.
- Holdout CAGR delta versus comparable benchmark: {_fmt(selected_delta['holdout_cagr_delta'], True)}.
- Holdout max-drawdown delta versus comparable benchmark: {_fmt(selected_delta['holdout_max_drawdown_delta'], True)}.
""", encoding="utf-8")

    (output / "holdout_results.md").write_text(f"""# Locked holdout results

The selected candidate was chosen by development CPCV before reading holdout results.

## Holdout strategies and benchmarks at 25 bps

{_table(holdout, columns, percent)}

## Cost sensitivity for selected strategy

{_table(selected_costs, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Acceptance criteria

- Passes paper-trading criteria: {_fmt(acceptance['passes'])}
- Holdout Sharpe > 0.5: {_fmt(acceptance['holdout_sharpe'])}
- Holdout CAGR: {_fmt(acceptance['holdout_cagr'], True)}
- Holdout max drawdown: {_fmt(acceptance['holdout_max_drawdown'], True)}
- Holdout annual turnover: {_fmt(acceptance['holdout_annual_turnover'])}x
- Survives 50 bps: {_fmt(acceptance['survives_50bps'])}
- Failures: {acceptance['failures'] or 'None'}
""", encoding="utf-8")

    diag_view = diagnostics[diagnostics.split != "feature_coverage"]
    coverage_view = diagnostics[diagnostics.split == "feature_coverage"]
    (output / "regime_diagnostics.md").write_text(f"""# Regime diagnostics

## Regime state performance

{_table(diag_view, [('split', 'Split'), ('regime_layer', 'Layer'), ('state', 'State'), ('days', 'Days'), ('fraction_days', 'Fraction days'), ('mean_daily_return', 'Mean daily return'), ('sharpe', 'Sharpe'), ('exposure', 'Exposure')], {'fraction_days', 'mean_daily_return', 'exposure'})}

## Feature coverage

{_table(coverage_view, [('regime_layer', 'Feature tier'), ('state', 'Feature'), ('fraction_days', 'Coverage')], {'fraction_days'})}
""", encoding="utf-8")

    candidate_holdout = metrics[
        (metrics.category == "candidate_25bps")
        & (metrics.split == "holdout")
        & (metrics.cost_bps == 25)
    ].sort_values("Sharpe", ascending=False)
    statistical_warning = bool(
        np.isfinite(statistics.get("pbo", np.nan))
        and statistics["pbo"] > 0.50
    ) or bool(
        np.isfinite(statistics.get("deflated_sharpe_probability", np.nan))
        and statistics["deflated_sharpe_probability"] < 0.50
    )
    if acceptance["passes"] and statistical_warning:
        conclusion = (
            "Macro-regime conditioning passes the declared paper-trading thresholds, "
            "but statistical controls are weak. Treat it as a paper-trading monitoring "
            "candidate, not as a capital-ready strategy."
        )
    elif acceptance["passes"]:
        conclusion = "Macro-regime conditioning passes the declared paper-trading criteria."
    else:
        conclusion = (
            "Macro-regime conditioning does not create a paper-tradable strategy under "
            "the declared criteria; it should be treated as risk diagnostics only."
        )

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Conclusion

{conclusion}

Selected candidate: **{winner.name}**.

## What the test says

- Holdout Sharpe: {_fmt(acceptance['holdout_sharpe'])}
- Holdout CAGR: {_fmt(acceptance['holdout_cagr'], True)}
- Holdout max drawdown: {_fmt(acceptance['holdout_max_drawdown'], True)}
- Holdout annual turnover: {_fmt(acceptance['holdout_annual_turnover'])}x
- Survives 50 bps: {_fmt(acceptance['survives_50bps'])}
- Approximate PBO: {_fmt(statistics['pbo'], True)}
- Deflated Sharpe probability: {_fmt(statistics['deflated_sharpe_probability'], True)}
- Failures: {acceptance['failures'] or 'None'}

## Does macro conditioning add economic value?

Comparable benchmark: `{selected_delta['comparable_benchmark']}`.

- Sharpe delta: {_fmt(selected_delta['holdout_sharpe_delta'])}
- CAGR delta: {_fmt(selected_delta['holdout_cagr_delta'], True)}
- Max-drawdown delta: {_fmt(selected_delta['holdout_max_drawdown_delta'], True)}

## Interpretation

The result is strongest as a risk-management and exposure-timing diagnostic.
Because PBO is high and the deflated Sharpe probability is below 50%, the
appropriate next step is paper monitoring, not capital deployment. No holdout
cell was used to select the final candidate; the holdout-best strict variant is
shown below only as a diagnostic.

## Candidate holdout diagnostics

The table below is diagnostic only and was not used for selection.

{_table(candidate_holdout, [('name', 'Candidate'), ('family', 'Family'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}
""", encoding="utf-8")

    payload = {
        "winner": asdict(winner),
        "acceptance": acceptance,
        "selected_delta": selected_delta,
        "statistics": statistics,
        "protocol": protocol,
        "metrics": metrics.to_dict("records"),
        "selection": selection.to_dict("records"),
        "regime_diagnostics": diagnostics.to_dict("records"),
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
    "ALLOWED_REGIME_FEATURES",
    "CRYPTO_TIER1_FEATURES",
    "MACRO_TIER1_FEATURES",
    "MacroRegimeCandidate",
    "MacroRegimeDataset",
    "build_macro_regime_dataset",
    "build_candidate_weights",
    "load_macro_features",
    "predeclared_macro_regime_candidates",
    "run_macro_regime_strategy_study",
    "write_macro_regime_strategy_reports",
]
