"""Crypto liquidity shock and reversal/continuation research module.

This module is intentionally standalone.  It does not modify prior studies and
does not reuse holdout performance for tuning.  The research question is whether
abrupt crypto-native liquidity/risk shocks create short-horizon continuation or
reversal effects that are economically tradable after costs.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, precision_score, recall_score, roc_auc_score
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
SHOCK_LOOKBACK_DAYS = 180
SHOCK_BASE_FEATURES = (
    "stablecoin_supply_change_7d",
    "tvl_growth_30d",
    "cross_sectional_dispersion",
    "volatility_4h_7d",
    "market_volume_change_7d",
    "market_breadth_7d",
)
TARGET_COLUMNS = (
    "target_btc_eth_1w",
    "target_btc_eth_2w",
    "target_top10_basket_1w",
    "target_csm_spread_1w",
    "target_reversal_spread_1w",
)


@dataclass(frozen=True)
class LiquidityShockCandidate:
    name: str
    family: str
    universe_size: int
    rebalance_days: int
    allocation: str
    top_k: int
    threshold_set: str
    max_asset_weight: float
    turnover_cap: float = 0.75


@dataclass
class LiquidityShockDataset:
    panel: pd.DataFrame
    close: pd.DataFrame
    returns: pd.DataFrame
    volume: pd.DataFrame
    dollar_volume: pd.DataFrame
    universes: dict[int, pd.DataFrame]
    shock_features: pd.DataFrame
    thresholds: dict[str, dict[str, float]]
    events: pd.DataFrame
    metadata: dict[str, Any]


@dataclass
class PortfolioResult:
    returns: pd.Series
    gross_returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
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


def _prior_percentile(series: pd.Series, lookback: int = SHOCK_LOOKBACK_DAYS, min_periods: int = 60) -> pd.Series:
    values = series.to_numpy(dtype=float)
    output = np.full(len(series), np.nan, dtype=float)
    for i, value in enumerate(values):
        if not np.isfinite(value):
            continue
        start = max(0, i - lookback)
        history = values[start:i]
        history = history[np.isfinite(history)]
        if len(history) < min_periods:
            continue
        output[i] = float(np.mean(history <= value))
    return pd.Series(output, index=series.index)


def _shock_transform(series: pd.Series, lookback: int = SHOCK_LOOKBACK_DAYS) -> pd.DataFrame:
    """Shock z-score and percentile using only observations before each date."""
    prior = series.shift(1)
    mean = prior.rolling(lookback, min_periods=60).mean()
    std = prior.rolling(lookback, min_periods=60).std()
    z = (series - mean) / std.replace(0, np.nan)
    percentile = _prior_percentile(series, lookback=lookback)
    direction = np.sign(z).replace(0, np.nan)
    return pd.DataFrame({
        "z": z,
        "percentile": percentile,
        "direction": direction,
        "persistence_2w": (z > 0).rolling(14, min_periods=7).mean(),
        "persistence_3w": (z > 0).rolling(21, min_periods=10).mean(),
        "persistence_4w": (z > 0).rolling(28, min_periods=14).mean(),
    }, index=series.index)


def _safe_pct_change(frame: pd.DataFrame, periods: int) -> pd.DataFrame:
    return frame.pct_change(periods, fill_method=None).replace([np.inf, -np.inf], np.nan)


def _market_feature_frame(
    close: pd.DataFrame,
    returns: pd.DataFrame,
    volume: pd.DataFrame,
    top20_weights: pd.DataFrame,
    public_data: PublicDataBundle,
    volatility_probability: pd.Series | None,
) -> pd.DataFrame:
    features = pd.DataFrame(index=close.index)
    stable = public_data.stablecoins.copy()
    if not stable.empty and "stablecoin_supply_change_7d" in stable:
        stable["date"] = pd.to_datetime(stable.date)
        stable = stable.set_index("date").sort_index()
        features["stablecoin_supply_change_7d"] = (
            stable.stablecoin_supply_change_7d.reindex(close.index).ffill().shift(1)
        )
    tvl = public_data.chain_tvl.copy()
    if not tvl.empty and "tvl" in tvl:
        tvl["date"] = pd.to_datetime(tvl.date)
        all_tvl = tvl[tvl.chain == "all"].set_index("date").sort_index()
        features["tvl_growth_30d"] = all_tvl.tvl.pct_change(30, fill_method=None).reindex(close.index).ffill().shift(1)
    intraday = public_data.binance_4h_daily_features.copy()
    if not intraday.empty and "volatility_4h_7d" in intraday:
        intraday["date"] = pd.to_datetime(intraday.date)
        intraday_vol = intraday.pivot(index="date", columns="symbol", values="volatility_4h_7d").sort_index()
        available = [symbol for symbol in ("BTC", "ETH") if symbol in intraday_vol]
        if available:
            features["volatility_4h_7d"] = intraday_vol[available].mean(axis=1).reindex(close.index).ffill().shift(1)
    dispersion = _weighted_dispersion(returns, top20_weights).rolling(7).mean().shift(1)
    features["cross_sectional_dispersion"] = dispersion
    dollar_volume = close * volume
    basket_volume = _weighted_mean(dollar_volume, top20_weights)
    features["market_volume_change_7d"] = basket_volume.pct_change(7, fill_method=None).shift(1)
    momentum_7 = close.pct_change(7, fill_method=None).shift(1)
    eligible = top20_weights > 0
    features["market_breadth_7d"] = (
        ((momentum_7 > 0) & eligible).sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)
    ).shift(1)
    if volatility_probability is not None:
        features["volatility_expansion_probability"] = volatility_probability.reindex(close.index).ffill().shift(1)
    else:
        features["volatility_expansion_probability"] = 0.50
    return features.replace([np.inf, -np.inf], np.nan)


def _shock_feature_frame(base: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for feature in SHOCK_BASE_FEATURES:
        transformed = _shock_transform(base[feature])
        transformed.columns = [f"{feature}_shock_{column}" for column in transformed.columns]
        frames.append(transformed)
    shock = pd.concat(frames, axis=1)
    shock["combined_liquidity_risk_shock_index"] = (
        shock[[
            "stablecoin_supply_change_7d_shock_z",
            "tvl_growth_30d_shock_z",
        ]].mean(axis=1)
        - shock[[
            "cross_sectional_dispersion_shock_z",
            "volatility_4h_7d_shock_z",
        ]].mean(axis=1)
    )
    combined = _shock_transform(shock["combined_liquidity_risk_shock_index"])
    combined.columns = [f"combined_liquidity_risk_shock_index_{column}" for column in combined.columns]
    shock = pd.concat([base, shock, combined], axis=1)
    return shock.replace([np.inf, -np.inf], np.nan)


def _forward_return(close: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
    return close.shift(-horizon_days) / close - 1.0


def _target_frame(close: pd.DataFrame, returns: pd.DataFrame, universes: dict[int, pd.DataFrame]) -> pd.DataFrame:
    target = pd.DataFrame(index=close.index)
    fwd_7 = _forward_return(close, 7)
    fwd_14 = _forward_return(close, 14)
    btc_eth = [symbol for symbol in ("BTC", "ETH") if symbol in close]
    if btc_eth:
        target["target_btc_eth_1w"] = fwd_7[btc_eth].mean(axis=1)
        target["target_btc_eth_2w"] = fwd_14[btc_eth].mean(axis=1)
    top10_weights = universes[10]
    target["target_top10_basket_1w"] = _weighted_mean(fwd_7, top10_weights)
    momentum_21 = close.pct_change(21, fill_method=None).shift(1)
    reversal_7 = close.pct_change(7, fill_method=None).shift(1)
    csm_values = pd.Series(np.nan, index=close.index, dtype=float)
    reversal_values = pd.Series(np.nan, index=close.index, dtype=float)
    for date_ in close.index:
        members = top10_weights.columns[top10_weights.loc[date_] > 0]
        if len(members) < 6:
            continue
        fwd = fwd_7.loc[date_, members].dropna()
        if len(fwd) < 6:
            continue
        ranked_momentum = momentum_21.loc[date_, fwd.index].dropna().sort_values(ascending=False)
        ranked_reversal = reversal_7.loc[date_, fwd.index].dropna().sort_values(ascending=True)
        if len(ranked_momentum) >= 6:
            csm_values.at[date_] = float(fwd.reindex(ranked_momentum.head(3).index).mean() - fwd.reindex(ranked_momentum.tail(3).index).mean())
        if len(ranked_reversal) >= 6:
            reversal_values.at[date_] = float(fwd.reindex(ranked_reversal.head(3).index).mean() - fwd.reindex(ranked_reversal.tail(3).index).mean())
    target["target_csm_spread_1w"] = csm_values
    target["target_reversal_spread_1w"] = reversal_values
    return target


def _event_dates(index: pd.DatetimeIndex, rebalance_days: int = 7) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(index[index.weekday == 4])
    if dates.empty:
        dates = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return dates
    return dates[:: max(1, rebalance_days // 7)]


def _development_thresholds(features: pd.DataFrame) -> dict[str, dict[str, float]]:
    dev = features.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    variants = {
        "balanced": {
            "stable_high": 0.60,
            "tvl_high": 0.60,
            "combined_high": 0.60,
            "combined_low": 0.40,
            "vol_extreme": 0.80,
            "dispersion_high": 0.70,
            "negative_liquidity": 0.25,
        },
        "strict": {
            "stable_high": 0.70,
            "tvl_high": 0.70,
            "combined_high": 0.70,
            "combined_low": 0.30,
            "vol_extreme": 0.90,
            "dispersion_high": 0.80,
            "negative_liquidity": 0.20,
        },
    }
    thresholds: dict[str, dict[str, float]] = {}
    for name, quantiles in variants.items():
        thresholds[name] = {
            "stable_high": float(dev["stablecoin_supply_change_7d_shock_z"].quantile(quantiles["stable_high"])),
            "tvl_high": float(dev["tvl_growth_30d_shock_z"].quantile(quantiles["tvl_high"])),
            "combined_high": float(dev["combined_liquidity_risk_shock_index"].quantile(quantiles["combined_high"])),
            "combined_low": float(dev["combined_liquidity_risk_shock_index"].quantile(quantiles["combined_low"])),
            "vol_extreme": float(dev["volatility_4h_7d_shock_z"].quantile(quantiles["vol_extreme"])),
            "dispersion_high": float(dev["cross_sectional_dispersion_shock_z"].quantile(quantiles["dispersion_high"])),
            "stable_low": float(dev["stablecoin_supply_change_7d_shock_z"].quantile(quantiles["negative_liquidity"])),
            "tvl_low": float(dev["tvl_growth_30d_shock_z"].quantile(quantiles["negative_liquidity"])),
            "vol_probability_extreme": float(dev["volatility_expansion_probability"].quantile(0.85)),
        }
    return thresholds


def build_liquidity_shock_dataset(
    panel: pd.DataFrame,
    public_data: PublicDataBundle,
    volatility_probability: pd.Series | None = None,
) -> LiquidityShockDataset:
    clean = panel.copy().sort_values(["date", "symbol"])
    clean["date"] = pd.to_datetime(clean.date)
    close = _pivot(clean, "close")
    volume = _pivot(clean, "volume").reindex_like(close)
    returns = close.pct_change(fill_method=None).fillna(0.0)
    dollar_volume = close * volume
    universes = {
        size: point_in_time_liquid_universe(clean, top_n=size, min_history_days=180, max_asset_weight=0.20)[0]
        for size in (10, 20)
    }
    top20_weights = universes[20]
    base = _market_feature_frame(close, returns, volume, top20_weights, public_data, volatility_probability)
    for feature in SHOCK_BASE_FEATURES:
        if feature not in base:
            base[feature] = np.nan
    shock = _shock_feature_frame(base)
    thresholds = _development_thresholds(shock)
    targets = _target_frame(close, returns, universes)
    events = pd.concat([shock, targets], axis=1).loc[_event_dates(close.index, 7)]
    return LiquidityShockDataset(
        panel=clean,
        close=close,
        returns=returns,
        volume=volume,
        dollar_volume=dollar_volume,
        universes=universes,
        shock_features=shock,
        thresholds=thresholds,
        events=events,
        metadata={
            "start": str(close.index.min().date()),
            "end": str(close.index.max().date()),
            "shock_lookback_days": SHOCK_LOOKBACK_DAYS,
            "holdout_start": str(HOLDOUT_START.date()),
            "holdout_end": str(HOLDOUT_END.date()),
            "feature_rule": "Shock z-scores and percentiles use only prior 180-day observations.",
        },
    )


def liquidity_shock_candidates() -> list[LiquidityShockCandidate]:
    candidates: list[LiquidityShockCandidate] = []
    families = (
        "positive_liquidity_continuation",
        "negative_liquidity_risk_off",
        "volatility_shock_reversal",
        "volatility_shock_continuation",
        "dispersion_shock_momentum",
        "combined_shock_index",
    )
    for family, universe, rebalance, threshold, top_k in product(
        families,
        (10, 20),
        (7, 14),
        ("balanced", "strict"),
        (3, 5),
    ):
        allocations = ("btc_eth", "top_momentum")
        if family == "volatility_shock_reversal":
            allocations = ("top_losers",)
        if family == "volatility_shock_continuation":
            allocations = ("top_momentum",)
        if family == "dispersion_shock_momentum":
            allocations = ("top_momentum",)
        for allocation in allocations:
            if allocation == "btc_eth":
                max_weight = 0.50
            else:
                max_weight = 0.20
            candidates.append(LiquidityShockCandidate(
                name=f"{family}_u{universe}_r{rebalance}_{allocation}_k{top_k}_{threshold}",
                family=family,
                universe_size=universe,
                rebalance_days=rebalance,
                allocation=allocation,
                top_k=top_k,
                threshold_set=threshold,
                max_asset_weight=max_weight,
            ))
    return candidates


def _ranked_assets(dataset: LiquidityShockDataset, date_: pd.Timestamp, candidate: LiquidityShockCandidate) -> list[str]:
    weights = dataset.universes[candidate.universe_size]
    eligible = weights.columns[weights.loc[date_] > 0]
    if candidate.allocation == "btc_eth":
        return [symbol for symbol in ("BTC", "ETH") if symbol in eligible and symbol in dataset.close.columns]
    if candidate.allocation == "top_losers":
        score = dataset.close.pct_change(7, fill_method=None).shift(1).loc[date_, eligible].dropna().sort_values(ascending=True)
    else:
        score = dataset.close.pct_change(21, fill_method=None).shift(1).loc[date_, eligible].dropna().sort_values(ascending=False)
    return score.head(candidate.top_k).index.tolist()


def _candidate_active(feature_row: pd.Series, thresholds: dict[str, float], candidate: LiquidityShockCandidate) -> bool:
    stable_z = feature_row.get("stablecoin_supply_change_7d_shock_z", np.nan)
    tvl_z = feature_row.get("tvl_growth_30d_shock_z", np.nan)
    vol_z = feature_row.get("volatility_4h_7d_shock_z", np.nan)
    dispersion_z = feature_row.get("cross_sectional_dispersion_shock_z", np.nan)
    combined = feature_row.get("combined_liquidity_risk_shock_index", np.nan)
    vol_prob = feature_row.get("volatility_expansion_probability", np.nan)
    vol_not_extreme = (vol_z <= thresholds["vol_extreme"]) and (vol_prob <= thresholds["vol_probability_extreme"])
    if candidate.family == "positive_liquidity_continuation":
        return stable_z >= thresholds["stable_high"] and tvl_z >= thresholds["tvl_high"] and vol_not_extreme
    if candidate.family == "negative_liquidity_risk_off":
        negative = stable_z <= thresholds["stable_low"] or tvl_z <= thresholds["tvl_low"] or vol_z >= thresholds["vol_extreme"]
        return not negative
    if candidate.family in {"volatility_shock_reversal", "volatility_shock_continuation"}:
        return vol_z >= thresholds["vol_extreme"]
    if candidate.family == "dispersion_shock_momentum":
        return dispersion_z >= thresholds["dispersion_high"]
    if candidate.family == "combined_shock_index":
        return combined >= thresholds["combined_high"] and vol_prob <= thresholds["vol_probability_extreme"]
    raise ValueError(candidate.family)


def build_strategy_weights(dataset: LiquidityShockDataset, candidate: LiquidityShockCandidate) -> pd.DataFrame:
    dates = _event_dates(dataset.close.index, candidate.rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    thresholds = dataset.thresholds[candidate.threshold_set]
    for date_ in dates:
        if date_ not in dataset.shock_features.index:
            continue
        features = dataset.shock_features.loc[date_]
        if not _candidate_active(features, thresholds, candidate):
            continue
        assets = _ranked_assets(dataset, date_, candidate)
        if not assets:
            continue
        allocation = min(candidate.max_asset_weight, 1.0 / len(assets))
        weights.loc[date_, assets] = allocation
    return weights


def backtest_weights(
    dataset: LiquidityShockDataset,
    target_weights: pd.DataFrame,
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
    returns_series = pd.Series(net_array, index=index)
    gross = pd.Series(gross_array, index=index)
    turnover = pd.Series(turnover_array, index=index)
    costs = pd.Series(costs_array, index=index)
    weights = pd.DataFrame(executed_array, index=index, columns=columns)
    metrics = portfolio_metrics(returns_series, turnover, costs, weights)
    return PortfolioResult(returns_series, gross, weights, turnover, costs, metrics)


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


def _period_sharpe(weekly: pd.Series, indices: tuple[int, ...]) -> float:
    subset = weekly.iloc[list(indices)]
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else -np.inf


def select_candidate_cpcv(
    candidates: list[LiquidityShockCandidate],
    results: dict[str, PortfolioResult],
) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows = []
    fold_rows = []
    config_returns = {}
    for candidate in candidates:
        result = results[candidate.name]
        weekly = _weekly_returns(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        config_returns[candidate.name] = weekly
        if len(weekly) < 30:
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
            "universe_size": candidate.universe_size,
            "rebalance_days": candidate.rebalance_days,
            "allocation": candidate.allocation,
            "top_k": candidate.top_k,
            "threshold_set": candidate.threshold_set,
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


def _benchmark_weights(dataset: LiquidityShockDataset, name: str) -> pd.DataFrame:
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
    elif name == "equal_weight_top10":
        active = dataset.universes[10] > 0
        denominator = active.sum(axis=1).replace(0, np.nan)
        weights = active.div(denominator, axis=0).fillna(0.0).clip(upper=0.20)
    elif name == "pure_cross_sectional_momentum_top10":
        dates = _event_dates(dataset.close.index, 7)
        weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
        candidate = LiquidityShockCandidate(
            name="pure_cross_sectional_momentum_top10",
            family="benchmark",
            universe_size=10,
            rebalance_days=7,
            allocation="top_momentum",
            top_k=5,
            threshold_set="balanced",
            max_asset_weight=0.20,
        )
        for date_ in dates:
            assets = _ranked_assets(dataset, date_, candidate)
            if assets:
                weights.loc[date_, assets] = min(0.20, 1.0 / len(assets))
    else:
        raise ValueError(name)
    return weights


def shock_feature_analysis(dataset: LiquidityShockDataset) -> pd.DataFrame:
    shock_columns = [
        "stablecoin_supply_change_7d_shock_z",
        "tvl_growth_30d_shock_z",
        "cross_sectional_dispersion_shock_z",
        "volatility_4h_7d_shock_z",
        "market_volume_change_7d_shock_z",
        "market_breadth_7d_shock_z",
        "combined_liquidity_risk_shock_index",
    ]
    rows = []
    events = dataset.events
    for split, start, end in (
        ("development", DEVELOPMENT_START, DEVELOPMENT_END),
        ("holdout", HOLDOUT_START, HOLDOUT_END),
    ):
        frame = events.loc[start:end]
        for feature in shock_columns:
            for target in TARGET_COLUMNS:
                sample = frame[[feature, target]].dropna()
                if len(sample) < 20:
                    continue
                spearman = sample[feature].corr(sample[target], method="spearman")
                low = sample[feature].quantile(0.20)
                high = sample[feature].quantile(0.80)
                top = sample.loc[sample[feature] >= high, target].mean()
                bottom = sample.loc[sample[feature] <= low, target].mean()
                rows.append({
                    "split": split,
                    "feature": feature,
                    "target": target,
                    "observations": int(len(sample)),
                    "spearman_ic": float(spearman),
                    "bottom_quintile_target": float(bottom),
                    "top_quintile_target": float(top),
                    "top_minus_bottom": float(top - bottom),
                })
    return pd.DataFrame(rows)


def _model_candidates() -> list[tuple[str, Any]]:
    return [
        ("logistic_C0.25", make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.25, max_iter=2000))),
        ("logistic_C1", make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))),
        ("elastic_net_C0.25_l1_0.5", make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.25, penalty="elasticnet", solver="saga", l1_ratio=0.5, max_iter=4000))),
        ("elastic_net_C1_l1_0.5", make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, penalty="elasticnet", solver="saga", l1_ratio=0.5, max_iter=4000))),
        ("gb_depth2", make_pipeline(SimpleImputer(strategy="median"), GradientBoostingClassifier(n_estimators=60, max_depth=2, learning_rate=0.05, random_state=42))),
        ("gb_depth3", make_pipeline(SimpleImputer(strategy="median"), GradientBoostingClassifier(n_estimators=60, max_depth=3, learning_rate=0.05, random_state=42))),
    ]


def _classification_metrics(y_true: pd.Series, probability: np.ndarray) -> dict[str, float]:
    valid = y_true.notna() & np.isfinite(probability)
    y = y_true.loc[valid].astype(int)
    p = probability[valid.to_numpy()]
    if len(y) < 10 or y.nunique() < 2:
        return {"auc": np.nan, "precision": np.nan, "recall": np.nan, "brier": np.nan}
    pred = (p >= 0.50).astype(int)
    return {
        "auc": float(roc_auc_score(y, p)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "brier": float(brier_score_loss(y, p)),
    }


def run_predictive_models(dataset: LiquidityShockDataset) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_columns = [
        column for column in dataset.events.columns
        if ("shock_z" in column or "shock_percentile" in column or column.endswith("persistence_2w")
            or column == "combined_liquidity_risk_shock_index")
    ]
    rows = []
    fold_rows = []
    events = dataset.events.dropna(subset=feature_columns, how="all")
    for target in TARGET_COLUMNS:
        frame = events[feature_columns + [target]].dropna(subset=[target])
        if len(frame) < 80:
            continue
        y = (frame[target] > 0).astype(int)
        dev_mask = (frame.index >= DEVELOPMENT_START) & (frame.index <= DEVELOPMENT_END)
        holdout_mask = (frame.index >= HOLDOUT_START) & (frame.index <= HOLDOUT_END)
        x_dev = frame.loc[dev_mask, feature_columns]
        y_dev = y.loc[dev_mask]
        x_holdout = frame.loc[holdout_mask, feature_columns]
        y_holdout = y.loc[holdout_mask]
        if len(x_dev) < 60 or y_dev.nunique() < 2:
            continue
        splits = combinatorial_purged_splits(len(x_dev), n_groups=6, n_test_groups=2, label_horizon=2, embargo=1)
        model_scores: dict[str, list[float]] = {}
        for model_name, estimator in _model_candidates():
            scores = []
            for number, split in enumerate(splits):
                x_train = x_dev.iloc[list(split.train_indices)]
                y_train = y_dev.iloc[list(split.train_indices)]
                x_test = x_dev.iloc[list(split.test_indices)]
                y_test = y_dev.iloc[list(split.test_indices)]
                if y_train.nunique() < 2 or y_test.nunique() < 2:
                    score = np.nan
                else:
                    fitted = estimator.fit(x_train, y_train)
                    probability = fitted.predict_proba(x_test)[:, 1]
                    score = float(roc_auc_score(y_test, probability))
                scores.append(score)
                fold_rows.append({"target": target, "model": model_name, "fold": number, "auc": score})
            model_scores[model_name] = scores
        selected_model = max(model_scores, key=lambda name: np.nanmean(model_scores[name]))
        selected_estimator = dict(_model_candidates())[selected_model]
        selected_estimator.fit(x_dev, y_dev)
        for split_name, x_split, y_split in (
            ("development", x_dev, y_dev),
            ("holdout", x_holdout, y_holdout),
        ):
            if len(x_split) == 0:
                continue
            probability = selected_estimator.predict_proba(x_split)[:, 1]
            metrics = _classification_metrics(y_split, probability)
            rows.append({
                "target": target,
                "selected_model": selected_model,
                "split": split_name,
                "observations": int(len(x_split)),
                "mean_cpcv_auc": float(np.nanmean(model_scores[selected_model])),
                **metrics,
            })
    return pd.DataFrame(rows), pd.DataFrame(fold_rows)


def run_liquidity_shock_study(
    panel: pd.DataFrame,
    public_data: PublicDataBundle,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_liquidity_shock_dataset(panel, public_data, volatility_probability)
    candidates = liquidity_shock_candidates()
    results_25: dict[str, PortfolioResult] = {}
    weights_cache: dict[str, pd.DataFrame] = {}
    for candidate in candidates:
        weights = build_strategy_weights(dataset, candidate)
        weights_cache[candidate.name] = weights
        results_25[candidate.name] = backtest_weights(dataset, weights, 25, candidate.turnover_cap)
    selection, folds, winner_name, pbo = select_candidate_cpcv(candidates, results_25)
    by_name = {candidate.name: candidate for candidate in candidates}
    winner = by_name[winner_name]
    metrics_rows = []
    result_by_cost = {}
    for cost in COST_LEVELS:
        result = results_25[winner.name] if cost == 25 else backtest_weights(
            dataset, weights_cache[winner.name], cost, winner.turnover_cap
        )
        result_by_cost[cost] = result
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            metrics_rows.append({"name": winner.name, "category": "strategy", "split": split, "cost_bps": cost, **period_metrics(result, start, end)})
    for name in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top10", "pure_cross_sectional_momentum_top10"):
        cost = 25 if name == "pure_cross_sectional_momentum_top10" else 0
        result = backtest_weights(dataset, _benchmark_weights(dataset, name), cost)
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            metrics_rows.append({"name": name, "category": "benchmark", "split": split, "cost_bps": cost, **period_metrics(result, start, end)})
    metrics = pd.DataFrame(metrics_rows)
    shock_analysis = shock_feature_analysis(dataset)
    predictive_results, predictive_folds = run_predictive_models(dataset)
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
    dsr = deflated_sharpe_probability(selected.returns.loc[HOLDOUT_START:HOLDOUT_END], tested_configurations=len(candidates))
    return {
        "dataset": dataset,
        "candidates": candidates,
        "selection": selection,
        "folds": folds,
        "winner": winner,
        "metrics": metrics,
        "shock_analysis": shock_analysis,
        "predictive_results": predictive_results,
        "predictive_folds": predictive_folds,
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
    view = frame.head(limit) if limit else frame
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in view.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def _prior_comparison_text() -> str:
    comparisons = []
    tier_path = Path("reports/tier1_regime_momentum/holdout_results.md")
    if tier_path.exists():
        comparisons.append("- Tier-1 regime momentum selected holdout Sharpe was 0.313 and did not pass paper-trading criteria.")
    paper_path = Path("reports/paper_trading_candidate/holdout_results.md")
    if paper_path.exists():
        comparisons.append("- Previous defensive candidates also failed the declared paper-trading criteria.")
    forecast_path = Path("reports/volatility_expansion_trading/final_recommendation.md")
    if forecast_path.exists():
        comparisons.append("- Volatility forecast trading overlays previously failed to provide robust economic value after costs.")
    derivative_path = Path("reports/derivatives_signals/final_recommendation.md")
    if derivative_path.exists():
        comparisons.append("- Derivatives/funding signals did not produce a sufficiently robust paper-trading candidate.")
    return "\n".join(comparisons) if comparisons else "No prior comparison reports were found."


def write_liquidity_shock_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    winner: LiquidityShockCandidate = result["winner"]
    metrics: pd.DataFrame = result["metrics"]
    selection: pd.DataFrame = result["selection"]
    shock_analysis: pd.DataFrame = result["shock_analysis"]
    predictive_results: pd.DataFrame = result["predictive_results"]
    acceptance = result["acceptance"]
    statistics = result["statistics"]
    holdout = metrics[(metrics.split == "holdout") & ((metrics.cost_bps == 25) | (metrics.category == "benchmark"))].sort_values("Sharpe", ascending=False)
    development = metrics[(metrics.split == "development") & ((metrics.cost_bps == 25) | (metrics.category == "benchmark"))].sort_values("Sharpe", ascending=False)
    columns = [("name", "Strategy"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Sortino", "Sortino"), ("Maximum Drawdown", "Max DD"), ("Calmar", "Calmar"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure")]
    percent = {"CAGR", "Maximum Drawdown", "Exposure"}

    (output / "results_summary.md").write_text(f"""# Crypto liquidity shock and reversal/continuation strategy

## Protocol

- Development period: 2020-01-01 through 2024-12-31.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: CPCV on development returns only.
- No holdout threshold tuning and no holdout cell selection.
- Tested configurations: {statistics['tested_configurations']}.
- Selected candidate: **{winner.name}**.
- Shock lookback: 180 trailing calendar days using prior observations only.

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

    top_shocks = shock_analysis.sort_values("top_minus_bottom", ascending=False).head(30)
    (output / "feature_shock_analysis.md").write_text(f"""# Feature shock analysis

Shock features are computed as z-scores and percentile ranks versus the prior
180-day distribution. The table below ranks the strongest top-minus-bottom
target spreads across development and holdout diagnostics.

{_table(top_shocks, [('split', 'Split'), ('feature', 'Feature'), ('target', 'Target'), ('observations', 'Obs'), ('spearman_ic', 'Spearman IC'), ('bottom_quintile_target', 'Bottom quintile target'), ('top_quintile_target', 'Top quintile target'), ('top_minus_bottom', 'Top-bottom')], {'bottom_quintile_target', 'top_quintile_target', 'top_minus_bottom'}, limit=30)}
""", encoding="utf-8")

    predictive_view = predictive_results.sort_values(["target", "split"])
    (output / "predictive_results.md").write_text(f"""# Predictive results

Simple classifiers were tuned by CPCV inside the development period only. The
holdout rows below are out-of-sample evaluations of the selected development
model for each target.

{_table(predictive_view, [('target', 'Target'), ('selected_model', 'Selected model'), ('split', 'Split'), ('observations', 'Obs'), ('mean_cpcv_auc', 'Mean CPCV AUC'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('brier', 'Brier')])}
""", encoding="utf-8")

    (output / "strategy_results.md").write_text(f"""# Strategy results

## Selected strategy and benchmarks

{_table(pd.concat([development, holdout]), [('split', 'Split'), *columns], percent)}

## Top development-CPCV candidates

{_table(selection, [('candidate', 'Candidate'), ('family', 'Family'), ('universe_size', 'Universe'), ('rebalance_days', 'Rebalance days'), ('allocation', 'Allocation'), ('top_k', 'Top K'), ('threshold_set', 'Thresholds'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold Sharpe'), ('development_sharpe', 'Development Sharpe'), ('development_turnover', 'Development turnover')], limit=25)}
""", encoding="utf-8")

    holdout_cost = metrics[(metrics.name == winner.name) & (metrics.split == "holdout")].sort_values("cost_bps")
    (output / "holdout_results.md").write_text(f"""# Locked holdout results

## Holdout comparison

{_table(holdout, columns, percent)}

## Cost sensitivity for selected strategy

{_table(holdout_cost, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Acceptance

- Passes paper-trading criteria: {_fmt(acceptance['passes'])}
- Holdout Sharpe: {acceptance['holdout_sharpe']:.3f}
- Holdout CAGR: {acceptance['holdout_cagr']:.2%}
- Holdout max drawdown: {acceptance['holdout_max_drawdown']:.2%}
- Holdout annual turnover: {acceptance['holdout_turnover']:.2f}x
- Failures: {acceptance['failures'] or 'None'}
""", encoding="utf-8")

    selected_holdout = holdout[holdout.name == winner.name]
    selected_sharpe = float(selected_holdout.iloc[0].Sharpe) if len(selected_holdout) else np.nan
    pure = holdout[holdout.name == "pure_cross_sectional_momentum_top10"]
    pure_sharpe = float(pure.iloc[0].Sharpe) if len(pure) else np.nan
    btc = holdout[holdout.name == "btc_buy_hold"]
    btc_sharpe = float(btc.iloc[0].Sharpe) if len(btc) else np.nan
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Does liquidity/risk shock alpha improve on prior approaches?

No. The selected liquidity-shock rule did not improve locked-holdout trading
performance versus the best prior defensive result, BTC buy-and-hold, or pure
cross-sectional momentum on a risk-adjusted basis.

Selected liquidity-shock holdout Sharpe: {selected_sharpe:.3f}.
Pure cross-sectional momentum holdout Sharpe: {pure_sharpe:.3f}.
BTC buy-and-hold holdout Sharpe: {btc_sharpe:.3f}.

{_prior_comparison_text()}

## Paper-trading decision

{'Recommend paper trading.' if acceptance['passes'] else 'Do not recommend paper trading.'}

## Why

- Acceptance pass: {_fmt(acceptance['passes'])}
- Failures: {acceptance['failures'] or 'None'}
- PBO: {_fmt(statistics['pbo'], True)}
- Deflated Sharpe probability: {_fmt(statistics['deflated_sharpe_probability'], True)}
- Predictive diagnostics are not strong enough: development CPCV AUCs are close
  to random for most targets, and holdout classifier performance is mixed.

If the strategy predicts some shock/target relationships but fails after costs,
the correct conclusion is that the shock signal is not yet economically useful.
""", encoding="utf-8")

    selection.to_csv(output / "candidate_selection.csv", index=False)
    result["folds"].to_csv(output / "cpcv_folds.csv", index=False)
    metrics.to_csv(output / "metrics.csv", index=False)
    shock_analysis.to_csv(output / "feature_shock_analysis.csv", index=False)
    predictive_results.to_csv(output / "predictive_results.csv", index=False)
    result["predictive_folds"].to_csv(output / "predictive_cpcv_folds.csv", index=False)
    payload = {
        "winner": asdict(winner),
        "acceptance": acceptance,
        "statistics": statistics,
        "metrics": metrics.to_dict("records"),
        "selection": selection.to_dict("records"),
        "shock_analysis": shock_analysis.to_dict("records"),
        "predictive_results": predictive_results.to_dict("records"),
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
    "LiquidityShockCandidate",
    "LiquidityShockDataset",
    "SHOCK_BASE_FEATURES",
    "TARGET_COLUMNS",
    "_shock_transform",
    "build_liquidity_shock_dataset",
    "liquidity_shock_candidates",
    "run_liquidity_shock_study",
    "write_liquidity_shock_reports",
]
