"""Crypto upside expansion and relative leadership models.

Standalone research module.  The frozen benchmark
``btc_eth_macro_gate_balanced`` is used as a comparator and Layer-1 macro gate,
but is not modified, replaced, or reselected.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, confusion_matrix, precision_recall_fscore_support, roc_auc_score

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .expansion_state_model import (
    FEATURES,
    ModelSpec,
    PredictionBundle,
    _all_risk_on,
    _buy_hold_weights,
    _classification_metrics,
    _feature_frame,
    _feature_importance,
    _fmt,
    _fold_sharpe,
    _forward_return,
    _json_safe,
    _positive_probability,
    _prior_meta_overlay_rows,
    _prior_tier1_rows,
    _rebalance_dates,
    _rows_for_result,
    _table,
    _threshold_from_dev,
    _top10_forward_return,
    _train_holdout_probabilities,
    _weekly_return,
    available_model_specs,
    calibration_table,
)
from .feature_research import _newey_west_stats, _rank_spearman
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    MacroRegimeCandidate,
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
)
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import deflated_sharpe_probability, probability_backtest_overfitting


BASELINE_NAME = FIXED_SELECTED.name
AGGREGATE_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("convex", "btc_30d_gt_15", "BTC 30-day forward return > +15%"),
    ("convex", "eth_30d_gt_20", "ETH 30-day forward return > +20%"),
    ("convex", "btc_eth_50_50_30d_gt_15", "BTC/ETH 50-50 30-day forward return > +15%"),
    ("relative", "eth_leads_btc_30d_gt_5", "ETH outperforms BTC over the next 30 days by at least +5%"),
    ("relative", "btc_leads_eth_30d_gt_5", "BTC outperforms ETH over the next 30 days by at least +5%"),
    ("transition", "risk_off_to_risk_on_2_4w", "Frozen macro state transitions from defensive to risk-on within 2-4 weeks"),
)
CROSS_SECTIONAL_TARGET = "top20_top_quintile_30d"


EXPANSION_TARGET_LABELS = {
    "btc_30d_upside": "BTC 30d > +15%",
    "eth_30d_upside": "ETH 30d > +20%",
    "btc_eth_50_50_30d_upside": "BTC/ETH 50-50 30d > +15%",
    "eth_vs_btc_leadership": "ETH beats BTC by +5%",
    "top20_leadership_payoff": "Top-20 top-quintile payoff spread",
}


@dataclass(frozen=True)
class UpsideOverlaySpec:
    name: str
    family: str
    overlay_type: str
    rebalance_days: int
    threshold: float
    secondary_threshold: float | None
    top_k: int = 5
    description: str = ""


@dataclass
class CrossSectionalPredictionBundle:
    config_name: str
    model_name: str
    model_family: str
    threshold: float
    dev_predictions: pd.DataFrame
    holdout_predictions: pd.DataFrame
    full_predictions: pd.DataFrame
    feature_importance: pd.DataFrame


def _build_aggregate_targets(
    dataset: MacroRegimeDataset,
    dates: pd.DatetimeIndex,
    frozen_combined: pd.Series,
) -> pd.DataFrame:
    btc = _forward_return(dataset.close, "BTC", dates)
    eth = _forward_return(dataset.close, "ETH", dates)
    mix = 0.50 * btc + 0.50 * eth
    targets = pd.DataFrame(index=dates)
    targets["btc_30d_gt_15"] = (btc > 0.15).astype(float)
    targets["eth_30d_gt_20"] = (eth > 0.20).astype(float)
    targets["btc_eth_50_50_30d_gt_15"] = (mix > 0.15).astype(float)
    targets["eth_leads_btc_30d_gt_5"] = ((eth - btc) > 0.05).astype(float)
    targets["btc_leads_eth_30d_gt_5"] = ((btc - eth) > 0.05).astype(float)

    aligned_regime = frozen_combined.reindex(dates).ffill().fillna("risk_off")
    transition = pd.Series(0.0, index=dates)
    for pos, date in enumerate(dates):
        current = str(aligned_regime.loc[date])
        future = aligned_regime.iloc[min(pos + 2, len(dates) - 1): min(pos + 5, len(dates))]
        transition.loc[date] = float(current != "risk_on" and (future == "risk_on").any())
    targets["risk_off_to_risk_on_2_4w"] = transition

    unavailable = pd.concat([btc, eth, mix], axis=1).isna().any(axis=1)
    targets.loc[unavailable, :] = np.nan
    return targets


def _cross_sectional_rows(dataset: MacroRegimeDataset, market_features: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    close = dataset.close
    returns = close.pct_change(fill_method=None)
    momentum_30 = close.pct_change(30, fill_method=None).shift(1)
    momentum_90 = close.pct_change(90, fill_method=None).shift(1)
    vol_30 = returns.rolling(30).std().shift(1) * np.sqrt(365)
    volume = dataset.panel.pivot(index="date", columns="symbol", values="volume").reindex_like(close)
    volume_expansion = volume.shift(1) / volume.rolling(30).median().shift(2).replace(0, np.nan)
    rows: list[dict[str, Any]] = []
    for date in dates:
        if date not in close.index or date not in dataset.universe_weights.index:
            continue
        end_pos = close.index.searchsorted(date + pd.Timedelta(days=30))
        if end_pos >= len(close.index):
            continue
        active = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        if len(active) < 5:
            continue
        start = close.loc[date, active].replace(0, np.nan)
        end = close.iloc[end_pos][active]
        forward = (end / start - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
        if len(forward) < 5:
            continue
        cutoff = float(forward.quantile(0.80))
        for symbol, fwd in forward.items():
            row = {
                "date": date,
                "symbol": symbol,
                "target": float(fwd >= cutoff),
                "forward_30d_return": float(fwd),
                "asset_momentum_30d": momentum_30.at[date, symbol] if symbol in momentum_30 else np.nan,
                "asset_momentum_90d": momentum_90.at[date, symbol] if symbol in momentum_90 else np.nan,
                "asset_volatility_30d": vol_30.at[date, symbol] if symbol in vol_30 else np.nan,
                "asset_volume_expansion": volume_expansion.at[date, symbol] if symbol in volume_expansion else np.nan,
            }
            for feature in FEATURES:
                row[feature] = market_features.at[date, feature] if feature in market_features and date in market_features.index else np.nan
            rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    feature_cols = [c for c in frame.columns if c not in {"date", "symbol", "target", "forward_30d_return"}]
    medians = frame.loc[(frame.date >= DEVELOPMENT_START) & (frame.date <= DEVELOPMENT_END), feature_cols].median().fillna(0.0)
    frame[feature_cols] = frame[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(medians).fillna(0.0)
    return frame


def target_diagnostics(aggregate_targets: pd.DataFrame, cross_sectional: pd.DataFrame) -> pd.DataFrame:
    descriptions = {name: description for _, name, description in AGGREGATE_TARGETS}
    rows: list[dict[str, Any]] = []
    for family, target, description in AGGREGATE_TARGETS:
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            y = aggregate_targets[target].loc[start:end].dropna().astype(int)
            rows.append({
                "family": family,
                "target": target,
                "description": description,
                "split": split,
                "observations": int(len(y)),
                "positive_events": int(y.sum()) if len(y) else 0,
                "prevalence": float(y.mean()) if len(y) else np.nan,
            })
    if not cross_sectional.empty:
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            y = cross_sectional[(cross_sectional.date >= start) & (cross_sectional.date <= end)]["target"].dropna().astype(int)
            rows.append({
                "family": "cross_sectional",
                "target": CROSS_SECTIONAL_TARGET,
                "description": "Point-in-time top-20 asset is top-quintile 30-day performer",
                "split": split,
                "observations": int(len(y)),
                "positive_events": int(y.sum()) if len(y) else 0,
                "prevalence": float(y.mean()) if len(y) else np.nan,
            })
    return pd.DataFrame(rows)


def _rolling_percentile(series: pd.Series, window: int = 365) -> pd.Series:
    return series.rolling(window, min_periods=max(20, window // 5)).apply(
        lambda values: pd.Series(values).rank(pct=True).iloc[-1],
        raw=False,
    )


def _rolling_zscore(series: pd.Series, window: int = 180) -> pd.Series:
    mean = series.rolling(window, min_periods=max(20, window // 5)).mean()
    std = series.rolling(window, min_periods=max(20, window // 5)).std().replace(0, np.nan)
    return (series - mean) / std


def _weighted_active_mean(frame: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    aligned = frame.reindex_like(weights).replace([np.inf, -np.inf], np.nan)
    active = weights > 0
    return aligned.where(active).mean(axis=1)


def build_expansion_feature_candidates(
    dataset: MacroRegimeDataset,
    market_features: pd.DataFrame,
    public_data: PublicDataBundle | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create expansion-specific features as diagnostics only.

    All returned features are shifted one full day before use.
    """
    close = dataset.close
    returns = close.pct_change(fill_method=None)
    weights = dataset.universe_weights.reindex_like(close).fillna(0.0)
    active = weights > 0
    volume = dataset.panel.pivot(index="date", columns="symbol", values="volume").sort_index().reindex_like(close)
    dollar_volume = close * volume
    market_cap = dataset.panel.pivot(index="date", columns="symbol", values="market_cap").sort_index().reindex_like(close)
    features = pd.DataFrame(index=close.index)
    metadata: list[dict[str, Any]] = []

    def add(name: str, series: pd.Series, family: str, rationale: str, availability: str = "available") -> None:
        features[name] = series.reindex(close.index)
        metadata.append({
            "feature": name,
            "family": family,
            "rationale": rationale,
            "availability": availability,
            "used_in_final_overlay": False,
        })

    stable_supply = pd.Series(dtype=float)
    tvl = pd.Series(dtype=float)
    if public_data is not None and not public_data.stablecoins.empty:
        stable = public_data.stablecoins.copy()
        stable["date"] = pd.to_datetime(stable["date"])
        stable = stable.drop_duplicates("date").set_index("date").sort_index()
        if "stablecoin_supply_usd" in stable:
            stable_supply = stable["stablecoin_supply_usd"].reindex(close.index).ffill()
    if public_data is not None and not public_data.chain_tvl.empty:
        chain = public_data.chain_tvl.copy()
        chain["date"] = pd.to_datetime(chain["date"])
        all_tvl = chain[chain.chain.astype(str).str.lower().eq("all")].drop_duplicates("date").set_index("date").sort_index()
        if "tvl" in all_tvl:
            tvl = all_tvl["tvl"].reindex(close.index).ffill()
    if not stable_supply.empty:
        stable_7 = stable_supply.pct_change(7, fill_method=None)
        stable_30 = stable_supply.pct_change(30, fill_method=None)
        add("stablecoin_supply_acceleration", stable_7 - stable_7.shift(7), "liquidity_inflow", "acceleration in stablecoin liquidity")
        add("stablecoin_supply_7d_30d_spread", stable_7 - stable_30, "liquidity_inflow", "short-term stablecoin growth above trend")
        add("stablecoin_supply_percentile", _rolling_percentile(stable_supply), "liquidity_inflow", "stablecoin supply relative to its own history")
    if not tvl.empty:
        tvl_7 = tvl.pct_change(7, fill_method=None)
        tvl_30 = tvl.pct_change(30, fill_method=None)
        add("tvl_acceleration", tvl_7 - tvl_7.shift(7), "liquidity_inflow", "acceleration in DeFi liquidity")
        add("tvl_7d_30d_spread", tvl_7 - tvl_30, "liquidity_inflow", "short-term TVL growth above trend")
        add("tvl_percentile", _rolling_percentile(tvl), "liquidity_inflow", "TVL relative to its own history")
    if "stablecoin_supply_acceleration" in features and "tvl_acceleration" in features:
        add(
            "combined_crypto_liquidity_impulse",
            _rolling_zscore(features["stablecoin_supply_acceleration"]) + _rolling_zscore(features["tvl_acceleration"]),
            "liquidity_inflow",
            "joint stablecoin and TVL liquidity impulse",
        )

    momentum_30 = close.pct_change(30, fill_method=None)
    above_30dma = close > close.rolling(30).mean()
    making_30d_high = close >= close.rolling(30).max()
    top20_breadth = ((momentum_30 > 0) & active).sum(axis=1) / active.sum(axis=1).replace(0, np.nan)
    top10_assets = weights.rank(axis=1, ascending=False, method="first") <= 10
    top10_breadth = ((momentum_30 > 0) & top10_assets & active).sum(axis=1) / (top10_assets & active).sum(axis=1).replace(0, np.nan)
    add("top10_breadth_acceleration", top10_breadth - top10_breadth.shift(14), "participation_breadth", "top-10 breadth acceleration")
    add("top20_breadth_acceleration", top20_breadth - top20_breadth.shift(14), "participation_breadth", "top-20 breadth acceleration")
    add("top20_above_30dma_pct", (above_30dma & active).sum(axis=1) / active.sum(axis=1).replace(0, np.nan), "participation_breadth", "share of top-20 above 30d moving average")
    add("top20_positive_30d_return_pct", top20_breadth, "participation_breadth", "share of top-20 with positive 30d returns")
    add("top20_30d_high_pct", (making_30d_high & active).sum(axis=1) / active.sum(axis=1).replace(0, np.nan), "participation_breadth", "share of top-20 making 30d highs")
    add("breadth_recovery_from_depressed", top20_breadth - top20_breadth.rolling(90).min(), "participation_breadth", "breadth recovery after depressed participation")

    if {"BTC", "ETH"}.issubset(close.columns):
        eth_btc = close["ETH"] / close["BTC"]
        for lookback in (14, 30, 63):
            add(f"eth_btc_relative_strength_{lookback}d", eth_btc.pct_change(lookback, fill_method=None), "leadership", f"ETH/BTC {lookback}d relative strength")
        add("eth_btc_breakout_strength", eth_btc / eth_btc.rolling(63).max() - 1.0, "leadership", "ETH/BTC distance to 63d breakout")
        if "BTC" in market_cap:
            btc_dom = market_cap["BTC"] / market_cap.where(active).sum(axis=1).replace(0, np.nan)
            add("btc_dominance_proxy_change_30d", btc_dom.diff(30), "leadership", "BTC dominance proxy change")
        equal_top20 = returns.where(active).mean(axis=1)
        btc_ret = returns["BTC"]
        top20_ex_btc_eth = returns.where(active).drop(columns=[c for c in ("BTC", "ETH") if c in returns], errors="ignore").mean(axis=1)
        add("altcoin_leadership_proxy_30d", top20_ex_btc_eth.rolling(30).sum() - btc_ret.rolling(30).sum(), "leadership", "altcoin basket leadership versus BTC")
        spread = equal_top20.rolling(30).sum() - btc_ret.rolling(30).sum()
        add("top20_equal_weight_minus_btc_return_30d", spread, "leadership", "top-20 equal weight return minus BTC")
        spread_vol = returns.where(active).mean(axis=1).rolling(30).std().replace(0, np.nan)
        add("top20_equal_weight_minus_btc_vol_adj_30d", spread / spread_vol, "leadership", "volatility-adjusted top-20 leadership versus BTC")

    market_dollar_volume = dollar_volume.where(active).sum(axis=1)
    volume_7 = market_dollar_volume.pct_change(7, fill_method=None)
    volume_30 = market_dollar_volume.pct_change(30, fill_method=None)
    volume_breadth = ((dollar_volume > dollar_volume.rolling(30).median()) & active).sum(axis=1) / active.sum(axis=1).replace(0, np.nan)
    add("market_dollar_volume_growth_30d", volume_30, "volume_attention", "market dollar-volume growth")
    add("volume_acceleration", volume_7 - volume_30, "volume_attention", "short-term volume acceleration versus 30d growth")
    add("abnormal_volume_zscore", _rolling_zscore(volume_7), "volume_attention", "abnormal market volume growth")
    add("volume_breadth", volume_breadth, "volume_attention", "share of top-20 with above-median volume")
    add("volume_confirmation_of_price_trend", volume_breadth * top20_breadth, "volume_attention", "volume breadth confirming price breadth")

    market_return = returns.where(active).mean(axis=1)
    realized_vol = market_return.rolling(30).std() * np.sqrt(365)
    upside = market_return.clip(lower=0)
    downside = market_return.clip(upper=0).abs()
    upside_semivar = upside.rolling(30).std()
    downside_vol = downside.rolling(30).std()
    add("realized_volatility_compression", 1.0 - _rolling_percentile(realized_vol), "volatility_structure", "low realized volatility before expansion")
    add("volatility_of_volatility", realized_vol.rolling(30).std(), "volatility_structure", "volatility-of-volatility")
    if "cross_sectional_dispersion" in market_features:
        dispersion = market_features["cross_sectional_dispersion"].reindex(close.index).ffill()
        add("dispersion_acceleration", dispersion - dispersion.shift(14), "volatility_structure", "cross-sectional dispersion acceleration")
    add("upside_semivariance", upside_semivar, "volatility_structure", "upside volatility participation")
    add("downside_to_upside_volatility_ratio", downside_vol / upside_semivar.replace(0, np.nan), "volatility_structure", "downside-to-upside volatility balance")
    add("jump_intensity", (market_return.abs() > 2.0 * market_return.rolling(60).std()).rolling(30).mean(), "volatility_structure", "frequency of large market moves")

    for lookback in (30, 90, 180):
        dist = (close / close.rolling(lookback).min() - 1.0).where(active).mean(axis=1)
        add(f"distance_from_{lookback}d_lows", dist, "recovery_capitulation", f"average distance from {lookback}d lows")
    wealth = (1 + market_return.fillna(0.0)).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    add("recovery_from_drawdown", drawdown - drawdown.rolling(90).min(), "recovery_capitulation", "market recovery from recent drawdown trough")
    rebound = ((close / close.rolling(30).min() - 1.0) > 0.10) & active
    add("assets_rebounding_from_30d_lows_pct", rebound.sum(axis=1) / active.sum(axis=1).replace(0, np.nan), "recovery_capitulation", "share of assets rebounding from 30d lows")
    if "funding_rate" in dataset.panel.columns:
        funding = dataset.panel.pivot(index="date", columns="symbol", values="funding_rate").sort_index().reindex_like(close)
        avg_funding = funding.where(active).mean(axis=1)
        add("funding_normalization_after_extreme", -avg_funding.abs() + avg_funding.abs().shift(14), "recovery_capitulation", "funding normalization after extremes", "available")

    macro = dataset.regime_features.reindex(close.index).ffill()
    if {"vix_level", "vix_change_21d", "equity_momentum_21d", "equity_realized_vol_21d"}.issubset(macro.columns):
        vix_high = _rolling_percentile(macro["vix_level"], 252)
        add("falling_vix_after_high_vix", (vix_high > 0.75).astype(float) * (-macro["vix_change_21d"]), "macro_recovery", "falling VIX after high-volatility regime")
        add("equity_momentum_recovery", macro["equity_momentum_21d"] - macro["equity_momentum_21d"].rolling(63).min(), "macro_recovery", "equity momentum recovery from local trough")
        eq_vol_compression = 1.0 - _rolling_percentile(macro["equity_realized_vol_21d"], 252)
        add("equity_volatility_compression", eq_vol_compression, "macro_recovery", "compression in equity realized volatility")
        add("risk_appetite_recovery_score", _rolling_zscore(-macro["vix_change_21d"]) + _rolling_zscore(macro["equity_momentum_21d"]) + _rolling_zscore(eq_vol_compression), "macro_recovery", "combined macro risk-appetite recovery score")

    feature_frame = features.replace([np.inf, -np.inf], np.nan).shift(1)
    development = feature_frame.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    medians = development.median().fillna(0.0)
    feature_frame = feature_frame.ffill().fillna(medians).fillna(0.0)
    return feature_frame, pd.DataFrame(metadata)


def _date_level_top20_leadership_targets(cross_rows: pd.DataFrame) -> pd.Series:
    if cross_rows.empty:
        return pd.Series(dtype=float)
    grouped = cross_rows.groupby("date")
    payoff = grouped.apply(
        lambda group: group.loc[group.target.astype(bool), "forward_30d_return"].mean()
        - group["forward_30d_return"].median(),
        include_groups=False,
    )
    return payoff.replace([np.inf, -np.inf], np.nan)


def _spearman_feature_target(feature: pd.Series, target: pd.Series) -> float:
    data = pd.concat([feature, target], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 5 or data.iloc[:, 0].nunique() < 3 or data.iloc[:, 1].nunique() < 2:
        return np.nan
    return float(data.iloc[:, 0].rank().corr(data.iloc[:, 1].rank()))


def _expansion_feature_targets(aggregate_targets: pd.DataFrame, cross_rows: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    targets = pd.DataFrame(index=aggregate_targets.index)
    targets["btc_30d_upside"] = aggregate_targets["btc_30d_gt_15"]
    targets["eth_30d_upside"] = aggregate_targets["eth_30d_gt_20"]
    targets["btc_eth_50_50_30d_upside"] = aggregate_targets["btc_eth_50_50_30d_gt_15"]
    targets["eth_vs_btc_leadership"] = aggregate_targets["eth_leads_btc_30d_gt_5"]
    top20_payoff = _date_level_top20_leadership_targets(cross_rows)
    targets["top20_leadership_payoff"] = top20_payoff.reindex(targets.index)
    target_types = {
        "btc_30d_upside": "binary",
        "eth_30d_upside": "binary",
        "btc_eth_50_50_30d_upside": "binary",
        "eth_vs_btc_leadership": "binary",
        "top20_leadership_payoff": "continuous",
    }
    return targets, target_types


def _feature_fold_stats(feature: pd.Series, target: pd.Series, target_type: str) -> dict[str, Any]:
    data = pd.concat([feature.rename("feature"), target.rename("target")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 30:
        return {"mean_ic": np.nan, "newey_west_t": np.nan, "p_value": np.nan, "positive_fold_fraction": np.nan, "auc": np.nan}
    splits = combinatorial_purged_splits(len(data), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    fold_ics = []
    fold_aucs = []
    for split in splits:
        fold = data.iloc[list(split.test_indices)]
        ic = _spearman_feature_target(fold["feature"], fold["target"])
        fold_ics.append(ic)
        if target_type == "binary" and fold["target"].nunique() == 2:
            try:
                auc = roc_auc_score(fold["target"].astype(int), fold["feature"])
                fold_aucs.append(max(auc, 1.0 - auc))
            except ValueError:
                pass
    stats = _newey_west_stats(pd.Series(fold_ics), lags=2)
    full_ic = _spearman_feature_target(data["feature"], data["target"])
    auc_full = np.nan
    if target_type == "binary" and data["target"].nunique() == 2:
        try:
            raw_auc = roc_auc_score(data["target"].astype(int), data["feature"])
            auc_full = max(raw_auc, 1.0 - raw_auc)
        except ValueError:
            auc_full = np.nan
    return {
        "full_ic": full_ic,
        "mean_ic": stats["mean"],
        "newey_west_t": stats["t_stat"],
        "p_value": stats["p_value"],
        "positive_fold_fraction": float(np.nanmean(np.sign(fold_ics) == np.sign(full_ic))) if np.isfinite(full_ic) else np.nan,
        "auc": auc_full,
        "fold_ic_std": float(pd.Series(fold_ics).std()) if len(fold_ics) else np.nan,
    }


def run_expansion_feature_research(
    feature_frame: pd.DataFrame,
    metadata: pd.DataFrame,
    aggregate_targets: pd.DataFrame,
    cross_rows: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    targets, target_types = _expansion_feature_targets(aggregate_targets, cross_rows)
    rows: list[dict[str, Any]] = []
    for feature in feature_frame.columns:
        for target_name in targets.columns:
            dev_stats = _feature_fold_stats(
                feature_frame[feature].loc[DEVELOPMENT_START:DEVELOPMENT_END],
                targets[target_name].loc[DEVELOPMENT_START:DEVELOPMENT_END],
                target_types[target_name],
            )
            holdout_data = pd.concat([
                feature_frame[feature].loc[HOLDOUT_START:HOLDOUT_END].rename("feature"),
                targets[target_name].loc[HOLDOUT_START:HOLDOUT_END].rename("target"),
            ], axis=1).dropna()
            holdout_ic = _spearman_feature_target(holdout_data["feature"], holdout_data["target"]) if not holdout_data.empty else np.nan
            holdout_auc = np.nan
            if target_types[target_name] == "binary" and not holdout_data.empty and holdout_data["target"].nunique() == 2:
                try:
                    raw_auc = roc_auc_score(holdout_data["target"].astype(int), holdout_data["feature"])
                    holdout_auc = max(raw_auc, 1.0 - raw_auc)
                except ValueError:
                    holdout_auc = np.nan
            rows.append({
                "feature": feature,
                "target": target_name,
                "target_label": EXPANSION_TARGET_LABELS[target_name],
                "target_type": target_types[target_name],
                **dev_stats,
                "holdout_ic": holdout_ic,
                "holdout_auc": holdout_auc,
                "holdout_sign_consistent": bool(np.sign(holdout_ic) == np.sign(dev_stats.get("full_ic", np.nan))) if np.isfinite(holdout_ic) and np.isfinite(dev_stats.get("full_ic", np.nan)) else False,
            })
    research = pd.DataFrame(rows)
    corr = feature_frame.loc[DEVELOPMENT_START:DEVELOPMENT_END].corr(method="spearman").replace([np.inf, -np.inf], np.nan)
    corr_rows: list[dict[str, Any]] = []
    for i, feature in enumerate(corr.columns):
        values = corr[feature].drop(labels=[feature], errors="ignore").abs().dropna()
        max_corr = float(values.max()) if len(values) else 0.0
        max_partner = str(values.idxmax()) if len(values) else ""
        corr_rows.append({"row_type": "feature_max_abs_corr", "feature": feature, "feature_2": max_partner, "correlation": max_corr})
        for partner, value in values.items():
            if corr.columns.get_loc(partner) > i and value >= 0.85:
                corr_rows.append({"row_type": "high_correlation_pair", "feature": feature, "feature_2": partner, "correlation": float(value)})
    correlation = pd.DataFrame(corr_rows)
    best = research.sort_values(["feature", "auc", "newey_west_t"], ascending=[True, False, False]).groupby("feature", as_index=False).first()
    tier_rows = []
    family_lookup = metadata.set_index("feature")["family"].to_dict() if not metadata.empty else {}
    rationale_lookup = metadata.set_index("feature")["rationale"].to_dict() if not metadata.empty else {}
    for _, row in best.iterrows():
        max_corr_row = correlation[(correlation.row_type == "feature_max_abs_corr") & (correlation.feature == row.feature)]
        max_corr = float(max_corr_row.iloc[0]["correlation"]) if not max_corr_row.empty else 0.0
        dev_strong = (
            (pd.notna(row.auc) and row.auc >= 0.55)
            or (pd.notna(row.mean_ic) and abs(row.mean_ic) >= 0.05 and pd.notna(row.newey_west_t) and abs(row.newey_west_t) >= 1.5)
        )
        dev_promising = (
            (pd.notna(row.auc) and row.auc >= 0.52)
            or (pd.notna(row.mean_ic) and abs(row.mean_ic) >= 0.03)
        )
        stable = pd.notna(row.positive_fold_fraction) and row.positive_fold_fraction >= 0.60
        not_redundant = max_corr < 0.90
        if dev_strong and stable and not_redundant and bool(row.holdout_sign_consistent):
            tier = "Expansion Tier 1"
            reason = "development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent"
        elif dev_promising and not_redundant:
            tier = "Expansion Tier 2"
            reason = "promising development evidence but weaker stability/significance/holdout diagnostic"
        else:
            tier = "Expansion Tier 3"
            reason = "unstable, redundant, or weak development evidence"
        tier_rows.append({
            "feature": row.feature,
            "family": family_lookup.get(row.feature, ""),
            "best_target": row.target,
            "feature_tier": tier,
            "development_auc": row.auc,
            "development_ic": row.full_ic,
            "newey_west_t": row.newey_west_t,
            "positive_fold_fraction": row.positive_fold_fraction,
            "holdout_ic": row.holdout_ic,
            "holdout_auc": row.holdout_auc,
            "holdout_sign_consistent": row.holdout_sign_consistent,
            "max_abs_correlation": max_corr,
            "rationale": rationale_lookup.get(row.feature, ""),
            "tier_reason": reason,
        })
    tiers = pd.DataFrame(tier_rows).sort_values(["feature_tier", "development_auc", "newey_west_t"], ascending=[True, False, False])
    return {
        "inventory": metadata,
        "research": research,
        "correlation": correlation,
        "tiers": tiers,
    }


def _cpcv_probabilities_by_date(x_dev: pd.DataFrame, y_dev: pd.Series, dates: pd.Series, spec: ModelSpec) -> tuple[pd.Series, pd.DataFrame]:
    unique_dates = pd.Index(pd.Series(dates).drop_duplicates().sort_values())
    if len(unique_dates) < 30:
        return pd.Series(float(y_dev.mean()), index=x_dev.index), pd.DataFrame()
    sums = pd.Series(0.0, index=x_dev.index)
    counts = pd.Series(0.0, index=x_dev.index)
    fold_rows: list[dict[str, Any]] = []
    splits = combinatorial_purged_splits(len(unique_dates), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    for number, split in enumerate(splits):
        train_dates = set(unique_dates[list(split.train_indices)])
        test_dates = set(unique_dates[list(split.test_indices)])
        train_mask = dates.isin(train_dates).to_numpy()
        test_mask = dates.isin(test_dates).to_numpy()
        y_train = y_dev.loc[train_mask]
        if y_train.nunique() < 2:
            prob = pd.Series(float(y_train.mean()), index=x_dev.index[test_mask])
        else:
            model = spec.factory()
            model.fit(x_dev.loc[train_mask], y_train)
            prob = pd.Series(_positive_probability(model, x_dev.loc[test_mask]), index=x_dev.index[test_mask])
        sums.loc[test_mask] += prob
        counts.loc[test_mask] += 1.0
        fold_rows.append({
            "model": spec.name,
            "fold": number,
            "test_groups": ",".join(str(group) for group in split.test_groups),
            "train_samples": int(train_mask.sum()),
            "test_samples": int(test_mask.sum()),
        })
    return (sums / counts.replace(0, np.nan)).fillna(float(y_dev.mean())), pd.DataFrame(fold_rows)


def _fit_aggregate_models(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    model_specs: list[ModelSpec],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, PredictionBundle], pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    fold_rows: list[pd.DataFrame] = []
    bundles: dict[str, PredictionBundle] = {}
    dev_mask = (features.index >= DEVELOPMENT_START) & (features.index <= DEVELOPMENT_END)
    holdout_mask = (features.index >= HOLDOUT_START) & (features.index <= HOLDOUT_END)
    for family, target, description in AGGREGATE_TARGETS:
        valid_dev = targets[target].loc[dev_mask].dropna().index
        valid_holdout = targets[target].loc[holdout_mask].dropna().index
        x_dev = features.loc[valid_dev]
        y_dev = targets.loc[valid_dev, target].astype(int)
        x_holdout = features.loc[valid_holdout]
        y_holdout = targets.loc[valid_holdout, target].astype(int)
        for spec in model_specs:
            config = f"{target}__{spec.name}"
            dev_prob, folds = _cpcv_probabilities_by_date(x_dev, y_dev, pd.Series(x_dev.index, index=x_dev.index), spec)
            if not folds.empty:
                folds["config"] = config
                folds["target"] = target
                folds["family"] = family
                fold_rows.append(folds)
            threshold = _threshold_from_dev(dev_prob, y_dev)
            holdout_prob, model = _train_holdout_probabilities(x_dev, y_dev, x_holdout, spec)
            full = pd.Series(np.nan, index=features.index)
            full.loc[dev_prob.index] = dev_prob
            full.loc[holdout_prob.index] = holdout_prob
            rows.append({**_classification_metrics(y_dev, dev_prob, threshold, "development_cpcv", config, target, spec.name), "family": family})
            rows.append({**_classification_metrics(y_holdout, holdout_prob, threshold, "holdout", config, target, spec.name), "family": family})
            bundles[config] = PredictionBundle(
                config_name=config,
                target=target,
                target_description=description,
                model_name=spec.name,
                model_family=spec.family,
                threshold=threshold,
                dev_probability=dev_prob,
                holdout_probability=holdout_prob,
                full_probability=full.ffill().fillna(float(dev_prob.mean()) if len(dev_prob) else 0.0),
                feature_importance=_feature_importance(model, spec, list(features.columns), config),
            )
    metrics = pd.DataFrame(rows)
    dev = metrics[metrics.split == "development_cpcv"].copy()
    dev["selection_score"] = dev["auc"].fillna(0.5) - dev["brier_score"].fillna(1.0) + 0.10 * dev["f1"].fillna(0.0)
    return metrics, dev.sort_values(["family", "selection_score"], ascending=[True, False]), bundles, pd.concat(fold_rows, ignore_index=True) if fold_rows else pd.DataFrame()


def _classification_metrics_frame(
    y_true: pd.Series,
    probability: pd.Series,
    threshold: float,
    split: str,
    config: str,
    target: str,
    model: str,
    family: str,
) -> dict[str, Any]:
    aligned = pd.concat([y_true.rename("y"), probability.rename("probability")], axis=1).dropna()
    if aligned.empty:
        return {"config": config, "target": target, "model": model, "family": family, "split": split}
    y = aligned.y.astype(int)
    p = aligned.probability.clip(0, 1)
    pred = (p >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    matrix = confusion_matrix(y, pred, labels=[0, 1])
    auc = roc_auc_score(y, p) if y.nunique() == 2 else np.nan
    return {
        "config": config,
        "target": target,
        "model": model,
        "family": family,
        "split": split,
        "threshold": threshold,
        "observations": int(len(y)),
        "positive_events": int(y.sum()),
        "auc": float(auc) if np.isfinite(auc) else np.nan,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "brier_score": float(brier_score_loss(y, p)),
        "true_negative": int(matrix[0, 0]),
        "false_positive": int(matrix[0, 1]),
        "false_negative": int(matrix[1, 0]),
        "true_positive": int(matrix[1, 1]),
    }


def _fit_cross_sectional_models(
    frame: pd.DataFrame,
    model_specs: list[ModelSpec],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, CrossSectionalPredictionBundle], pd.DataFrame]:
    if frame.empty:
        return pd.DataFrame(), pd.DataFrame(), {}, pd.DataFrame()
    feature_cols = [c for c in frame.columns if c not in {"date", "symbol", "target", "forward_30d_return"}]
    dev_frame = frame[(frame.date >= DEVELOPMENT_START) & (frame.date <= DEVELOPMENT_END)].copy()
    holdout_frame = frame[(frame.date >= HOLDOUT_START) & (frame.date <= HOLDOUT_END)].copy()
    rows: list[dict[str, Any]] = []
    fold_rows: list[pd.DataFrame] = []
    bundles: dict[str, CrossSectionalPredictionBundle] = {}
    x_dev = dev_frame[feature_cols]
    y_dev = dev_frame["target"].astype(int)
    x_holdout = holdout_frame[feature_cols]
    y_holdout = holdout_frame["target"].astype(int)
    for spec in model_specs:
        config = f"{CROSS_SECTIONAL_TARGET}__{spec.name}"
        dev_prob, folds = _cpcv_probabilities_by_date(x_dev, y_dev, dev_frame["date"], spec)
        if not folds.empty:
            folds["config"] = config
            folds["target"] = CROSS_SECTIONAL_TARGET
            folds["family"] = "cross_sectional"
            fold_rows.append(folds)
        threshold = _threshold_from_dev(dev_prob, y_dev)
        holdout_prob, model = _train_holdout_probabilities(x_dev, y_dev, x_holdout, spec)
        rows.append(_classification_metrics_frame(y_dev, dev_prob, threshold, "development_cpcv", config, CROSS_SECTIONAL_TARGET, spec.name, "cross_sectional"))
        rows.append(_classification_metrics_frame(y_holdout, holdout_prob, threshold, "holdout", config, CROSS_SECTIONAL_TARGET, spec.name, "cross_sectional"))
        dev_predictions = dev_frame[["date", "symbol", "target", "forward_30d_return"]].copy()
        dev_predictions["probability"] = dev_prob.to_numpy()
        holdout_predictions = holdout_frame[["date", "symbol", "target", "forward_30d_return"]].copy()
        holdout_predictions["probability"] = holdout_prob.to_numpy()
        bundles[config] = CrossSectionalPredictionBundle(
            config_name=config,
            model_name=spec.name,
            model_family=spec.family,
            threshold=threshold,
            dev_predictions=dev_predictions,
            holdout_predictions=holdout_predictions,
            full_predictions=pd.concat([dev_predictions, holdout_predictions], ignore_index=True),
            feature_importance=_feature_importance(model, spec, feature_cols, config),
        )
    metrics = pd.DataFrame(rows)
    dev = metrics[metrics.split == "development_cpcv"].copy()
    dev["selection_score"] = dev["auc"].fillna(0.5) - dev["brier_score"].fillna(1.0) + 0.10 * dev["f1"].fillna(0.0)
    return metrics, dev.sort_values("selection_score", ascending=False), bundles, pd.concat(fold_rows, ignore_index=True) if fold_rows else pd.DataFrame()


def _best_bundle(selection: pd.DataFrame, bundles: dict[str, PredictionBundle], family: str, target: str | None = None) -> PredictionBundle:
    rows = selection[selection.family == family]
    if target is not None:
        rows = rows[rows.target == target]
    if rows.empty:
        raise ValueError(f"No model selection rows for {family}/{target}")
    return bundles[str(rows.iloc[0].config)]


def _best_cross_bundle(selection: pd.DataFrame, bundles: dict[str, CrossSectionalPredictionBundle]) -> CrossSectionalPredictionBundle | None:
    if selection.empty or not bundles:
        return None
    return bundles[str(selection.iloc[0].config)]


def _threshold_grid(value: float) -> tuple[float, ...]:
    return tuple(sorted(set([0.50, 0.60, float(value)])))


def predeclared_overlay_specs(
    convex_threshold: float,
    eth_threshold: float,
    btc_threshold: float,
    transition_threshold: float,
    cross_threshold: float,
    component_passes: dict[str, bool] | None = None,
) -> list[UpsideOverlaySpec]:
    component_passes = component_passes or {}
    specs: list[UpsideOverlaySpec] = []
    for days in (7, 14):
        for threshold in _threshold_grid(convex_threshold):
            specs.append(UpsideOverlaySpec(f"convex_upside_t{int(threshold*100)}_{days}d", "convex", "convex_upside", days, threshold, None, description="Convex-upside exposure participation overlay."))
        for eth_t in _threshold_grid(eth_threshold):
            for btc_t in _threshold_grid(btc_threshold):
                specs.append(UpsideOverlaySpec(f"relative_winner_e{int(eth_t*100)}_b{int(btc_t*100)}_{days}d", "relative", "relative_winner", days, eth_t, btc_t, description="ETH/BTC relative-winner tilt overlay."))
        for threshold in _threshold_grid(transition_threshold):
            specs.append(UpsideOverlaySpec(f"regime_transition_t{int(threshold*100)}_{days}d", "transition", "regime_transition", days, threshold, None, description="Early re-entry overlay for predicted risk-off to risk-on transitions."))
        for threshold in _threshold_grid(cross_threshold):
            for top_k in (3, 5):
                specs.append(UpsideOverlaySpec(f"cross_sectional_top{top_k}_t{int(threshold*100)}_{days}d", "cross_sectional", "cross_sectional_leadership", days, threshold, None, top_k=top_k, description="Top-20 cross-sectional leadership sleeve overlay."))
        enabled = {name for name, passed in component_passes.items() if passed}
        if enabled:
            label = "_".join(sorted(enabled))
            specs.append(UpsideOverlaySpec(f"combined_{label}_{days}d", "combined", "combined", days, convex_threshold, eth_threshold, top_k=5, description=f"Predeclared combined overlay using development-passing components: {sorted(enabled)}."))
    return specs


def _balanced_btc_eth(weights: pd.DataFrame, date: pd.Timestamp, exposure: float, btc_weight: float = 0.50) -> None:
    if "BTC" in weights.columns and "ETH" in weights.columns:
        weights.loc[date, "BTC"] = exposure * btc_weight
        weights.loc[date, "ETH"] = exposure * (1.0 - btc_weight)
    elif "BTC" in weights.columns:
        weights.loc[date, "BTC"] = exposure
    elif "ETH" in weights.columns:
        weights.loc[date, "ETH"] = exposure


def build_overlay_weights(
    dataset: MacroRegimeDataset,
    frozen_combined: pd.Series,
    probabilities: dict[str, pd.Series],
    cross_predictions: pd.DataFrame,
    spec: UpsideOverlaySpec,
    component_passes: dict[str, bool] | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    component_passes = component_passes or {}
    dates = _rebalance_dates(dataset.close.index, spec.rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    decisions = pd.Series("cash", index=dates, dtype=object)
    regimes = frozen_combined.reindex(dates).ffill().fillna("risk_off")
    convex = probabilities["convex"].reindex(dates).ffill().fillna(0.0)
    eth = probabilities["eth_leads_btc"].reindex(dates).ffill().fillna(0.0)
    btc = probabilities["btc_leads_eth"].reindex(dates).ffill().fillna(0.0)
    transition = probabilities["transition"].reindex(dates).ffill().fillna(0.0)
    cross_map = cross_predictions.copy()
    if not cross_map.empty:
        cross_map["date"] = pd.to_datetime(cross_map["date"])
    for date in dates:
        regime = str(regimes.loc[date])
        if regime == "risk_off":
            if spec.overlay_type in {"regime_transition", "combined"} and float(transition.loc[date]) >= spec.threshold:
                exposure = 0.25
                decisions.loc[date] = "transition_early_reentry"
                _balanced_btc_eth(weights, date, exposure)
            else:
                decisions.loc[date] = "macro_risk_off_cash"
            continue
        exposure = 1.0 if regime == "risk_on" else 0.50
        btc_share = 0.50
        if spec.overlay_type == "convex_upside":
            if float(convex.loc[date]) >= spec.threshold:
                exposure = 1.0
                decisions.loc[date] = "convex_upside_full_exposure"
            else:
                decisions.loc[date] = "frozen_macro_allocation"
        elif spec.overlay_type == "relative_winner":
            if float(eth.loc[date]) >= spec.threshold and float(eth.loc[date]) >= float(btc.loc[date]):
                btc_share = 0.30
                decisions.loc[date] = "eth_overweight"
            elif spec.secondary_threshold is not None and float(btc.loc[date]) >= spec.secondary_threshold:
                btc_share = 0.70
                decisions.loc[date] = "btc_overweight"
            else:
                decisions.loc[date] = "balanced_btc_eth"
        elif spec.overlay_type == "regime_transition":
            decisions.loc[date] = "frozen_macro_allocation"
        elif spec.overlay_type == "cross_sectional_leadership":
            decisions.loc[date] = "frozen_macro_allocation"
        elif spec.overlay_type == "combined":
            decisions.loc[date] = "combined_base"
            if component_passes.get("convex") and float(convex.loc[date]) >= spec.threshold:
                exposure = 1.0
                decisions.loc[date] = "combined_convex_full_exposure"
            if component_passes.get("relative"):
                if float(eth.loc[date]) >= (spec.secondary_threshold or 0.60) and float(eth.loc[date]) >= float(btc.loc[date]):
                    btc_share = 0.30
                    decisions.loc[date] = decisions.loc[date] + "_eth_tilt"
                elif float(btc.loc[date]) >= 0.60:
                    btc_share = 0.70
                    decisions.loc[date] = decisions.loc[date] + "_btc_tilt"
        else:
            raise ValueError(spec.overlay_type)
        _balanced_btc_eth(weights, date, exposure, btc_share)
        use_cross = spec.overlay_type == "cross_sectional_leadership" or (spec.overlay_type == "combined" and component_passes.get("cross_sectional"))
        if use_cross and regime == "risk_on" and not cross_map.empty:
            daily = cross_map[(cross_map.date == date) & (cross_map.probability >= spec.threshold)].sort_values("probability", ascending=False)
            chosen = [s for s in daily.symbol.head(spec.top_k).tolist() if s in weights.columns]
            if chosen:
                sleeve = min(0.40, exposure)
                current_total = float(weights.loc[date].sum())
                if current_total > 0:
                    weights.loc[date] *= max(0.0, exposure - sleeve) / current_total
                allocation = sleeve / len(chosen)
                for symbol in chosen:
                    weights.loc[date, symbol] += allocation
                decisions.loc[date] = decisions.loc[date] + "_cross_sectional_sleeve"
    weights = weights.clip(lower=0.0, upper=1.0)
    totals = weights.sum(axis=1)
    over = totals > 1.0
    weights.loc[over] = weights.loc[over].div(totals.loc[over], axis=0)
    return weights, decisions


def _evaluate_overlay_family(
    family: str,
    specs: list[UpsideOverlaySpec],
    results_25: dict[str, PortfolioResult],
) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    family_specs = [spec for spec in specs if spec.family == family]
    rows: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    config_returns: dict[str, pd.Series] = {}
    for spec in family_specs:
        result = results_25[spec.name]
        weekly = _weekly_return(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        config_returns[spec.name] = weekly
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_values = []
        for number, split in enumerate(splits):
            sharpe = _fold_sharpe(weekly, split.test_indices)
            fold_values.append(sharpe)
            folds.append({"family": family, "candidate": spec.name, "fold": number, "test_groups": ",".join(str(g) for g in split.test_groups), "fold_sharpe": sharpe})
        dev = period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        rows.append({
            "family": family,
            "candidate": spec.name,
            "overlay_type": spec.overlay_type,
            "description": spec.description,
            "median_fold_sharpe": float(np.nanmedian(fold_values)),
            "worst_fold_sharpe": float(np.nanmin(fold_values)),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_values) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
        })
    selection = pd.DataFrame(rows)
    if selection.empty:
        return selection, pd.DataFrame(folds), "", np.nan
    selection["selection_score"] = (
        selection["median_fold_sharpe"]
        + 0.25 * selection["worst_fold_sharpe"]
        + 0.40 * selection["positive_fold_fraction"]
        - np.maximum(0.0, selection["development_turnover"] - 12.0) * 0.05
        - np.maximum(0.0, 0.15 - selection["development_exposure"]) * 0.50
    )
    selection = selection.sort_values("selection_score", ascending=False)
    pbo = probability_backtest_overfitting(pd.concat(config_returns, axis=1).sort_index(), blocks=8) if len(config_returns) > 1 else np.nan
    return selection, pd.DataFrame(folds), str(selection.iloc[0].candidate), pbo


def _pure_top10_momentum_weights(dataset: MacroRegimeDataset) -> pd.DataFrame:
    candidate = MacroRegimeCandidate(
        name="pure_top10_momentum",
        family="Pure top-10 momentum",
        gate_profile="balanced",
        use_crypto_gate=False,
        allocation="top10_momentum",
        top_k=5,
        universe_size=10,
    )
    weights, _, _, _ = build_candidate_weights(dataset, candidate, combined_override="always_on")
    return weights


def _evaluate_benchmarks(
    dataset20: MacroRegimeDataset,
    dataset10: MacroRegimeDataset,
    frozen_weights: pd.DataFrame,
    frozen_regimes: tuple[pd.Series, pd.Series, pd.Series],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    macro, crypto, combined = frozen_regimes
    for cost in COST_LEVELS:
        frozen = backtest_weights(dataset20, frozen_weights, macro, crypto, combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
        rows.extend(_rows_for_result(BASELINE_NAME, "Frozen macro gate", "frozen_strategy", cost, frozen))
        risk_on = _all_risk_on(dataset10.close.index)
        for name, family in (
            ("btc_buy_hold", "BTC buy-and-hold"),
            ("eth_buy_hold", "ETH buy-and-hold"),
            ("btc_eth_50_50", "50/50 BTC/ETH"),
            ("equal_weight_top10", "Equal-weight top 10"),
        ):
            result = backtest_weights(dataset10, _buy_hold_weights(dataset10, name), *risk_on, cost_bps=cost, turnover_cap=10.0)
            rows.extend(_rows_for_result(name, family, "benchmark", cost, result))
        pure = backtest_weights(dataset10, _pure_top10_momentum_weights(dataset10), *risk_on, cost_bps=cost, turnover_cap=0.75)
        rows.extend(_rows_for_result("pure_top10_momentum", "Pure top-10 momentum", "benchmark", cost, pure))
    prior_meta = _prior_meta_overlay_rows()
    if not prior_meta.empty:
        rows.extend(prior_meta.to_dict("records"))
    prior_tier1 = _prior_tier1_rows()
    if not prior_tier1.empty:
        rows.extend(prior_tier1.to_dict("records"))
    return pd.DataFrame(rows)


def run_upside_expansion_models(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
    model_specs: list[ModelSpec] | None = None,
) -> dict[str, Any]:
    model_specs = model_specs or available_model_specs()
    dataset20 = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=20)
    dataset10 = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    features = _feature_frame(dataset20, public_data)
    dates = _rebalance_dates(dataset20.close.index, 7)
    x = features.reindex(dates).ffill().fillna(0.0)
    frozen_weights, frozen_macro, frozen_crypto, frozen_combined = build_candidate_weights(dataset20, FIXED_SELECTED)
    frozen_regimes = (frozen_macro, frozen_crypto, frozen_combined)
    aggregate_targets = _build_aggregate_targets(dataset20, dates, frozen_combined)
    cross_rows = _cross_sectional_rows(dataset20, features, dates)
    expansion_feature_frame, expansion_feature_metadata = build_expansion_feature_candidates(dataset20, features, public_data)
    expansion_feature_research = run_expansion_feature_research(
        expansion_feature_frame,
        expansion_feature_metadata,
        aggregate_targets,
        cross_rows,
    )

    agg_metrics, agg_selection, agg_bundles, agg_folds = _fit_aggregate_models(x, aggregate_targets, model_specs)
    cross_metrics, cross_selection, cross_bundles, cross_folds = _fit_cross_sectional_models(cross_rows, model_specs)
    prediction_metrics = pd.concat([agg_metrics, cross_metrics], ignore_index=True, sort=False)
    prediction_selection = pd.concat([agg_selection, cross_selection], ignore_index=True, sort=False)
    diagnostics = target_diagnostics(aggregate_targets, cross_rows)

    convex = _best_bundle(agg_selection, agg_bundles, "convex")
    eth_lead = _best_bundle(agg_selection, agg_bundles, "relative", "eth_leads_btc_30d_gt_5")
    btc_lead = _best_bundle(agg_selection, agg_bundles, "relative", "btc_leads_eth_30d_gt_5")
    transition = _best_bundle(agg_selection, agg_bundles, "transition")
    cross = _best_cross_bundle(cross_selection, cross_bundles)

    calibration = calibration_table(aggregate_targets, [convex, eth_lead, btc_lead, transition])
    feature_importance = pd.concat(
        [bundle.feature_importance for bundle in agg_bundles.values()]
        + ([bundle.feature_importance for bundle in cross_bundles.values()] if cross_bundles else []),
        ignore_index=True,
    )

    component_passes = {
        "convex": bool(float(agg_selection[agg_selection.config == convex.config_name].iloc[0]["auc"]) >= 0.52),
        "relative": bool(float(agg_selection[agg_selection.config == eth_lead.config_name].iloc[0]["auc"]) >= 0.55),
        "transition": bool(float(agg_selection[agg_selection.config == transition.config_name].iloc[0]["auc"]) >= 0.52),
        "cross_sectional": bool(not cross_selection.empty and float(cross_selection.iloc[0]["auc"]) >= 0.52),
    }
    cross_predictions = cross.full_predictions if cross is not None else pd.DataFrame()
    specs = predeclared_overlay_specs(convex.threshold, eth_lead.threshold, btc_lead.threshold, transition.threshold, cross.threshold if cross else 0.60, component_passes)
    probabilities = {
        "convex": convex.full_probability,
        "eth_leads_btc": eth_lead.full_probability,
        "btc_leads_eth": btc_lead.full_probability,
        "transition": transition.full_probability,
    }
    overlay_results: dict[str, dict[int, PortfolioResult]] = {}
    overlay_decisions: dict[str, pd.Series] = {}
    for spec in specs:
        weights, decisions = build_overlay_weights(dataset20, frozen_combined, probabilities, cross_predictions, spec, component_passes)
        overlay_decisions[spec.name] = decisions
        overlay_results[spec.name] = {
            cost: backtest_weights(dataset20, weights, frozen_macro, frozen_crypto, frozen_combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
            for cost in COST_LEVELS
        }
    results_25 = {name: by_cost[25] for name, by_cost in overlay_results.items()}
    selections = []
    folds = []
    pbo_rows = []
    selected_by_family: dict[str, str] = {}
    for family in ("convex", "relative", "transition", "cross_sectional", "combined"):
        selection, family_folds, winner, pbo = _evaluate_overlay_family(family, specs, results_25)
        if not selection.empty:
            selections.append(selection)
            folds.append(family_folds)
            pbo_rows.append({"family": family, "pbo": pbo, "selected_candidate": winner})
            selected_by_family[family] = winner
    overlay_selection = pd.concat(selections, ignore_index=True) if selections else pd.DataFrame()
    overlay_folds = pd.concat(folds, ignore_index=True) if folds else pd.DataFrame()
    pbo_frame = pd.DataFrame(pbo_rows)

    overlay_metric_rows: list[dict[str, Any]] = []
    for spec in specs:
        for cost, result in overlay_results[spec.name].items():
            for row in _rows_for_result(spec.name, spec.description, spec.family, cost, result, selected=spec.name in selected_by_family.values()):
                row.update({"overlay_type": spec.overlay_type, "rebalance_days": spec.rebalance_days, "threshold": spec.threshold, "secondary_threshold": spec.secondary_threshold, "top_k": spec.top_k})
                overlay_metric_rows.append(row)
    overlay_metrics = pd.DataFrame(overlay_metric_rows)
    benchmarks = _evaluate_benchmarks(dataset20, dataset10, frozen_weights, frozen_regimes)
    frozen_25 = backtest_weights(dataset20, frozen_weights, frozen_macro, frozen_crypto, frozen_combined, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
    frozen_holdout = period_metrics(frozen_25, HOLDOUT_START, HOLDOUT_END)

    if "combined" in selected_by_family:
        final_candidate = selected_by_family["combined"]
    else:
        eligible = []
        for family, candidate in selected_by_family.items():
            hold = overlay_metrics[(overlay_metrics.name == candidate) & (overlay_metrics.split == "holdout") & (overlay_metrics.cost_bps == 25)].iloc[0]
            if hold["Exposure"] >= 0.15:
                eligible.append(candidate)
        final_candidate = eligible[0] if eligible else next(iter(selected_by_family.values()))
    final_holdout = overlay_metrics[(overlay_metrics.name == final_candidate) & (overlay_metrics.split == "holdout") & (overlay_metrics.cost_bps == 25)].iloc[0]
    final_50 = overlay_metrics[(overlay_metrics.name == final_candidate) & (overlay_metrics.split == "holdout") & (overlay_metrics.cost_bps == 50)].iloc[0]
    total_configs = int(len(prediction_selection) + len(specs))
    pbo = float(pbo_frame["pbo"].dropna().max()) if not pbo_frame.empty and pbo_frame["pbo"].notna().any() else np.nan
    family_validation_rows: list[dict[str, Any]] = []
    for family, candidate in selected_by_family.items():
        hold = overlay_metrics[(overlay_metrics.name == candidate) & (overlay_metrics.split == "holdout") & (overlay_metrics.cost_bps == 25)].iloc[0]
        hold_50 = overlay_metrics[(overlay_metrics.name == candidate) & (overlay_metrics.split == "holdout") & (overlay_metrics.cost_bps == 50)].iloc[0]
        pbo_row = pbo_frame[pbo_frame.family == family]
        family_pbo = float(pbo_row.iloc[0]["pbo"]) if not pbo_row.empty and pd.notna(pbo_row.iloc[0]["pbo"]) else np.nan
        family_dsr = deflated_sharpe_probability(
            overlay_results[candidate][25].returns.loc[HOLDOUT_START:HOLDOUT_END],
            tested_configurations=total_configs,
        )
        passes = bool(
            hold["Sharpe"] > frozen_holdout["Sharpe"] + 0.10
            and hold["CAGR"] >= frozen_holdout["CAGR"] * 0.90
            and hold["Maximum Drawdown"] >= frozen_holdout["Maximum Drawdown"] - 0.05
            and hold_50["CAGR"] > 0
            and hold["Annual Turnover"] <= 12
            and hold["Exposure"] >= 0.15
            and (not np.isfinite(family_pbo) or family_pbo <= 0.65)
            and family_dsr >= 0.50
        )
        family_validation_rows.append({
            "family": family,
            "candidate": candidate,
            "holdout_sharpe": hold["Sharpe"],
            "holdout_cagr": hold["CAGR"],
            "holdout_max_drawdown": hold["Maximum Drawdown"],
            "holdout_turnover": hold["Annual Turnover"],
            "holdout_exposure": hold["Exposure"],
            "cost_50_cagr": hold_50["CAGR"],
            "pbo": family_pbo,
            "deflated_sharpe_probability": family_dsr,
            "passes_guardrails": passes,
        })
    family_validation = pd.DataFrame(family_validation_rows)
    final_validation = family_validation[family_validation.candidate == final_candidate].iloc[0]
    dsr = float(final_validation["deflated_sharpe_probability"])
    replacement_ok = bool(
        final_holdout["Sharpe"] > frozen_holdout["Sharpe"] + 0.10
        and final_holdout["CAGR"] >= frozen_holdout["CAGR"] * 0.90
        and final_holdout["Maximum Drawdown"] >= frozen_holdout["Maximum Drawdown"] - 0.05
        and final_50["CAGR"] > 0
        and final_holdout["Annual Turnover"] <= 12
        and final_holdout["Exposure"] >= 0.15
        and (not np.isfinite(pbo) or pbo <= 0.65)
        and dsr >= 0.50
    )
    if replacement_ok:
        final_conclusion = "the combined upside overlay complements the frozen macro risk gate for paper monitoring"
    elif bool(family_validation["passes_guardrails"].any()):
        passing = ", ".join(family_validation.loc[family_validation.passes_guardrails, "family"].astype(str))
        final_conclusion = f"standalone family overlay(s) pass paper-monitoring guardrails ({passing}), but the combined overlay fails full criteria"
    elif final_holdout["Exposure"] < 0.15:
        final_conclusion = "upside detection is diagnostic only because the selected candidate is a low-exposure cash strategy"
    elif final_holdout["Sharpe"] <= frozen_holdout["Sharpe"]:
        final_conclusion = "upside detection fails to improve the frozen macro strategy economically"
    else:
        final_conclusion = "upside detection has partial evidence but fails full replacement criteria"

    family_holdouts = []
    for family, candidate in selected_by_family.items():
        row = overlay_metrics[(overlay_metrics.name == candidate) & (overlay_metrics.split == "holdout") & (overlay_metrics.cost_bps == 25)].iloc[0].to_dict()
        row["family"] = family
        family_holdouts.append(row)
    family_holdouts_frame = pd.DataFrame(family_holdouts)

    return {
        "dataset20": dataset20,
        "features": features,
        "aggregate_targets": aggregate_targets,
        "cross_sectional_rows": cross_rows,
        "expansion_feature_frame": expansion_feature_frame,
        "expansion_feature_research": expansion_feature_research,
        "target_diagnostics": diagnostics,
        "prediction_metrics": prediction_metrics,
        "prediction_selection": prediction_selection,
        "aggregate_prediction_folds": agg_folds,
        "cross_prediction_folds": cross_folds,
        "prediction_bundles": agg_bundles,
        "cross_prediction_bundles": cross_bundles,
        "selected_models": {
            "convex": convex,
            "eth_leadership": eth_lead,
            "btc_leadership": btc_lead,
            "transition": transition,
            "cross_sectional": cross,
        },
        "component_passes": component_passes,
        "calibration": calibration,
        "feature_importance": feature_importance,
        "overlay_specs": specs,
        "overlay_results": overlay_results,
        "overlay_decisions": overlay_decisions,
        "overlay_selection": overlay_selection,
        "overlay_folds": overlay_folds,
        "overlay_metrics": overlay_metrics,
        "selected_by_family": selected_by_family,
        "family_pbo": pbo_frame,
        "family_holdouts": family_holdouts_frame,
        "family_validation": family_validation,
        "benchmarks": benchmarks,
        "frozen_holdout": frozen_holdout,
        "final_candidate": final_candidate,
        "final_candidate_dsr": dsr,
        "final_candidate_pbo_reference": pbo,
        "final_conclusion": final_conclusion,
        "replacement_ok": replacement_ok,
        "tested_configurations": {
            "prediction_configs": int(len(prediction_selection)),
            "overlay_configs": int(len(specs)),
            "total": total_configs,
        },
        "protocol": {
            "title": "Crypto Upside Expansion and Relative Leadership Models",
            "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} to {HOLDOUT_END.date()}",
            "baseline": BASELINE_NAME,
            "selection_rule": "Prediction and overlay candidates are selected with development-only CPCV. Holdout is reported after selection only.",
        },
    }


def _family_report(result: dict[str, Any], family: str, title: str) -> str:
    selection = result["overlay_selection"][result["overlay_selection"].family == family]
    metrics = result["overlay_metrics"][(result["overlay_metrics"].benchmark_group == family) & (result["overlay_metrics"].split == "holdout")]
    winner = result["selected_by_family"].get(family, "none")
    pbo = result["family_pbo"][result["family_pbo"].family == family]
    pbo_value = pbo.iloc[0]["pbo"] if not pbo.empty else np.nan
    return f"""# {title}

Selected by development-only CPCV: **{winner}**.

## Development selection

{_table(selection, [('candidate', 'Candidate'), ('selection_score', 'Selection score'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds'), ('development_sharpe', 'Dev Sharpe'), ('development_turnover', 'Dev turnover'), ('development_exposure', 'Dev exposure')], {'positive_fold_fraction', 'development_exposure'}, limit=40)}

## Holdout cost sensitivity

{_table(metrics[metrics.name == winner], [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Statistical note

- Family PBO: {_fmt(pbo_value, True)}
- Holdout was not used for family selection.
"""


def write_upside_expansion_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for key, filename in (
        ("target_diagnostics", "target_diagnostics.csv"),
        ("prediction_metrics", "prediction_metrics.csv"),
        ("prediction_selection", "prediction_selection.csv"),
        ("calibration", "calibration_curve.csv"),
        ("feature_importance", "feature_importance.csv"),
        ("overlay_selection", "overlay_selection.csv"),
        ("overlay_folds", "overlay_cpcv_folds.csv"),
        ("overlay_metrics", "overlay_metrics.csv"),
        ("benchmarks", "benchmark_metrics.csv"),
        ("family_pbo", "family_pbo.csv"),
        ("family_holdouts", "family_holdouts.csv"),
        ("family_validation", "family_validation.csv"),
    ):
        result[key].to_csv(output / filename, index=False)
    feature_research = result["expansion_feature_research"]
    feature_research["inventory"].to_csv(output / "expansion_feature_inventory.csv", index=False)
    feature_research["research"].to_csv(output / "expansion_feature_research.csv", index=False)
    feature_research["tiers"].to_csv(output / "expansion_feature_tiers.csv", index=False)
    feature_research["correlation"].to_csv(output / "expansion_feature_correlation.csv", index=False)
    frozen = result["frozen_holdout"]
    final = result["overlay_metrics"][(result["overlay_metrics"].name == result["final_candidate"]) & (result["overlay_metrics"].split == "holdout") & (result["overlay_metrics"].cost_bps == 25)].iloc[0]
    best_predictive = result["prediction_selection"].sort_values("selection_score", ascending=False).iloc[0]
    family_holdouts = result["family_holdouts"].sort_values("Sharpe", ascending=False)
    family_validation = result["family_validation"].sort_values("holdout_sharpe", ascending=False)

    (output / "results_summary.md").write_text(f"""# Results summary

Project: **{result['protocol']['title']}**

The frozen baseline remains **{BASELINE_NAME}** and was not modified, replaced,
or reselected.

## Protocol

- Development period: {result['protocol']['development_period']}
- Locked holdout: {result['protocol']['locked_holdout']}
- Tested configurations: {result['tested_configurations']['total']} total ({result['tested_configurations']['prediction_configs']} prediction, {result['tested_configurations']['overlay_configs']} overlay)

## Best predictive target family

Best development-CPCV predictive configuration: **{best_predictive['config']}**
from family **{best_predictive['family']}**.

## Best economic overlay by predeclared process

Final candidate: **{result['final_candidate']}**

| Strategy | Sharpe | CAGR | Max DD | Turnover | Exposure |
|---|---:|---:|---:|---:|---:|
| Frozen {BASELINE_NAME} | {_fmt(frozen['Sharpe'])} | {_fmt(frozen['CAGR'], True)} | {_fmt(frozen['Maximum Drawdown'], True)} | {_fmt(frozen['Annual Turnover'])} | {_fmt(frozen['Exposure'], True)} |
| Final upside overlay | {_fmt(final['Sharpe'])} | {_fmt(final['CAGR'], True)} | {_fmt(final['Maximum Drawdown'], True)} | {_fmt(final['Annual Turnover'])} | {_fmt(final['Exposure'], True)} |

Final conclusion: **{result['final_conclusion']}**.
""", encoding="utf-8")

    (output / "target_diagnostics.md").write_text(f"""# Target diagnostics

{_table(result['target_diagnostics'], [('family', 'Family'), ('target', 'Target'), ('description', 'Description'), ('split', 'Split'), ('observations', 'Obs'), ('positive_events', 'Events'), ('prevalence', 'Prevalence')], {'prevalence'})}
""", encoding="utf-8")

    (output / "expansion_feature_inventory.md").write_text(f"""# Expansion feature inventory

These features are engineered specifically for upside expansion detection rather
than broad risk avoidance. They are diagnostics only in this run and were not
added to the final overlay candidate.

{_table(feature_research['inventory'], [('feature', 'Feature'), ('family', 'Family'), ('rationale', 'Economic rationale'), ('availability', 'Availability'), ('used_in_final_overlay', 'Used in final overlay')], limit=120)}
""", encoding="utf-8")

    research_top = feature_research["research"].sort_values(["auc", "newey_west_t"], ascending=[False, False])
    (output / "expansion_feature_research.md").write_text(f"""# Expansion feature research

Selection discipline: feature evidence is evaluated on the development period.
Holdout IC/AUC is reported as a diagnostic only and is not used to alter the
current final candidate.

## Top feature-target diagnostics

{_table(research_top, [('feature', 'Feature'), ('target', 'Target'), ('target_label', 'Target label'), ('full_ic', 'Dev IC'), ('mean_ic', 'Mean fold IC'), ('newey_west_t', 'NW t'), ('p_value', 'p-value'), ('positive_fold_fraction', 'Stable folds'), ('auc', 'Dev AUC'), ('holdout_ic', 'Holdout IC'), ('holdout_auc', 'Holdout AUC'), ('holdout_sign_consistent', 'Holdout sign consistent')], {'positive_fold_fraction'}, limit=80)}
""", encoding="utf-8")

    (output / "expansion_feature_tiers.md").write_text(f"""# Expansion feature tiers

Tiering rules:

- Expansion Tier 1: development evidence, CPCV stability, not highly redundant, and holdout sign diagnostic consistency.
- Expansion Tier 2: promising but weaker development evidence or stability.
- Expansion Tier 3: unstable, redundant, or no evidence.

No new expansion-specific feature was added to the final candidate in this run.

{_table(feature_research['tiers'], [('feature', 'Feature'), ('family', 'Family'), ('best_target', 'Best target'), ('feature_tier', 'Tier'), ('development_auc', 'Dev AUC'), ('development_ic', 'Dev IC'), ('newey_west_t', 'NW t'), ('positive_fold_fraction', 'Stable folds'), ('holdout_ic', 'Holdout IC'), ('holdout_auc', 'Holdout AUC'), ('max_abs_correlation', 'Max |corr|'), ('tier_reason', 'Reason')], {'positive_fold_fraction'}, limit=120)}
""", encoding="utf-8")

    (output / "expansion_feature_correlation.md").write_text(f"""# Expansion feature correlation and redundancy

Correlation is computed on the development period only. Highly correlated pairs
are reported so redundant features can be excluded from future model design.

{_table(feature_research['correlation'].sort_values('correlation', ascending=False), [('row_type', 'Type'), ('feature', 'Feature'), ('feature_2', 'Feature 2'), ('correlation', 'Correlation')], limit=120)}
""", encoding="utf-8")

    (output / "predictive_performance.md").write_text(f"""# Predictive performance

All prediction models were selected using development CPCV only.

## Development-CPCV ranking

{_table(result['prediction_selection'].sort_values('selection_score', ascending=False), [('family', 'Family'), ('config', 'Config'), ('model', 'Model'), ('selection_score', 'Selection score'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier')], limit=80)}

## Holdout predictive diagnostics

{_table(result['prediction_metrics'][result['prediction_metrics'].split == 'holdout'], [('family', 'Family'), ('config', 'Config'), ('auc', 'AUC'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1'), ('brier_score', 'Brier'), ('true_positive', 'TP'), ('false_positive', 'FP'), ('false_negative', 'FN'), ('true_negative', 'TN')], limit=80)}
""", encoding="utf-8")

    selected_configs = [bundle.config_name for bundle in result["selected_models"].values() if bundle is not None]
    importance = result["feature_importance"][result["feature_importance"].config.isin(selected_configs)]
    (output / "calibration_and_feature_importance.md").write_text(f"""# Calibration and feature importance

SHAP was requested if available. The `shap` package is not installed in this
environment, so this module reports model coefficients or native feature
importance instead.

## Calibration

{_table(result['calibration'], [('config', 'Config'), ('split', 'Split'), ('bin', 'Bin'), ('observations', 'Obs'), ('mean_probability', 'Mean probability'), ('event_rate', 'Event rate')], {'mean_probability', 'event_rate'}, limit=80)}

## Selected-model feature importance

{_table(importance, [('config', 'Config'), ('feature', 'Feature'), ('importance', 'Importance'), ('method', 'Method')], limit=80)}
""", encoding="utf-8")

    report_names = {
        "convex": ("convex_upside_results.md", "Convex-upside results"),
        "relative": ("relative_winner_results.md", "Relative-winner results"),
        "transition": ("regime_transition_results.md", "Regime-transition results"),
        "cross_sectional": ("cross_sectional_leadership_results.md", "Cross-sectional leadership results"),
        "combined": ("combined_overlay_results.md", "Combined overlay results"),
    }
    for family, (filename, title) in report_names.items():
        (output / filename).write_text(_family_report(result, family, title), encoding="utf-8")

    holdout_benchmarks = result["benchmarks"][(result["benchmarks"].split == "holdout") & (result["benchmarks"].cost_bps.isin([25, 50]))]
    final_rows = result["overlay_metrics"][(result["overlay_metrics"].name == result["final_candidate"]) & (result["overlay_metrics"].split == "holdout")]
    comparison = pd.concat([holdout_benchmarks, final_rows], ignore_index=True, sort=False)
    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

{_table(comparison, [('name', 'Name'), ('benchmark_group', 'Group'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=100)}
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

## Family-level PBO

{_table(result['family_pbo'], [('family', 'Family'), ('selected_candidate', 'Selected candidate'), ('pbo', 'PBO')], {'pbo'})}

## Final candidate controls

- Final candidate: **{result['final_candidate']}**
- Deflated Sharpe probability: {_fmt(result['final_candidate_dsr'], True)}
- PBO reference used for final decision: {_fmt(result['final_candidate_pbo_reference'], True)}
- Replacement/complement criteria passed: {_fmt(result['replacement_ok'])}

## Independent family guardrails

{_table(family_validation, [('family', 'Family'), ('candidate', 'Candidate'), ('holdout_sharpe', 'Holdout Sharpe'), ('holdout_cagr', 'Holdout CAGR'), ('holdout_max_drawdown', 'Max DD'), ('holdout_turnover', 'Turnover'), ('holdout_exposure', 'Exposure'), ('pbo', 'PBO'), ('deflated_sharpe_probability', 'DSR probability'), ('passes_guardrails', 'Passes')], {'holdout_cagr', 'holdout_max_drawdown', 'holdout_exposure', 'pbo', 'deflated_sharpe_probability'})}

## Selected family holdouts

{_table(family_holdouts, [('family', 'Family'), ('name', 'Candidate'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}
""", encoding="utf-8")

    best_economic = family_holdouts.iloc[0] if not family_holdouts.empty else final
    tier_counts = feature_research["tiers"]["feature_tier"].value_counts().to_dict()
    tier1_count = int(tier_counts.get("Expansion Tier 1", 0))
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Answers

1. Best predictive family: **{best_predictive['family']}** via `{best_predictive['config']}`.
2. Best economic family, as an ex-post holdout diagnostic among development-selected family winners: **{best_economic['family']}** via `{best_economic['name']}`.
3. Upside detection complements the macro risk gate only if it improves economics without becoming a low-exposure cash strategy.
4. Final candidate: **{result['final_candidate']}**.
5. Paper-monitoring status: **{result['final_conclusion']}**.
6. Expansion-specific feature discovery: **{tier1_count}** feature(s) reached Expansion Tier 1 under diagnostic rules; none were inserted into the current final overlay.

## Recommendation

Do not modify or replace **{BASELINE_NAME}** based on this module. A standalone
family overlay may be paper-monitored only if it passes the independent
guardrails above; the combined overlay must pass separately before it can be
treated as a candidate complement.
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "tested_configurations": result["tested_configurations"],
        "component_passes": result["component_passes"],
        "selected_by_family": result["selected_by_family"],
        "final_candidate": result["final_candidate"],
        "replacement_ok": result["replacement_ok"],
        "final_candidate_dsr": _json_safe(result["final_candidate_dsr"]),
        "final_candidate_pbo_reference": _json_safe(result["final_candidate_pbo_reference"]),
        "frozen_holdout": _json_safe(frozen),
        "final_holdout_25bps": _json_safe(final.to_dict()),
        "final_conclusion": result["final_conclusion"],
        "prediction_selection": _json_safe(result["prediction_selection"]),
        "prediction_metrics": _json_safe(result["prediction_metrics"]),
        "overlay_selection": _json_safe(result["overlay_selection"]),
        "overlay_metrics": _json_safe(result["overlay_metrics"]),
        "family_validation": _json_safe(result["family_validation"]),
        "expansion_feature_tiers": _json_safe(feature_research["tiers"]),
        "benchmarks": _json_safe(result["benchmarks"]),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_upside_expansion_models(output_dir: str | Path = "reports/upside_expansion_models") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_upside_expansion_models(panel, macro, public_data, probability)
    write_upside_expansion_reports(output_dir, result)
    return result


__all__ = [
    "AGGREGATE_TARGETS",
    "CROSS_SECTIONAL_TARGET",
    "run_upside_expansion_models",
    "write_upside_expansion_reports",
    "run_default_upside_expansion_models",
]
