"""Agentic AI-inspired deterministic strategy discovery.

The workflow is deterministic and auditable:

Thinker -> Feature Worker -> Strategy Worker -> Verifier.

No LLM calls occur during backtests.  The frozen
``btc_eth_macro_gate_balanced`` strategy is only used as a benchmark and is not
modified, reselected, or retuned.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .expansion_state_model import _fmt, _json_safe, _table
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
from .new_data_extension import build_data_inventory, build_feature_panel
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import block_bootstrap_sharpe_ci, deflated_sharpe_probability, probability_backtest_overfitting


BASELINE_NAME = FIXED_SELECTED.name
PROJECT_TITLE = "Macro-Regime Conditioning for Systematic Cryptocurrency Allocation: A Robust Out-of-Sample Evaluation"


@dataclass(frozen=True)
class AgenticCandidate:
    candidate_name: str
    strategy_family: str
    hypothesis: str
    economic_rationale: str
    required_features: tuple[str, ...]
    data_availability: str
    point_in_time_status: str
    exact_formula_or_model_specification: str
    parameters: dict[str, Any]
    rebalance_frequency: str
    asset_universe: str
    transaction_cost_assumption: str
    risk_controls: str
    expected_failure_mode: str
    reason_not_full_feature_ml: str
    reason_not_duplicate_frozen_macro: str
    deterministic_rule: bool = True
    llm_calls_inside_backtest: bool = False


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int = 7) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def _rolling_percentile(series: pd.Series, window: int = 252) -> pd.Series:
    return series.rolling(window, min_periods=max(20, window // 5)).apply(
        lambda values: pd.Series(values).rank(pct=True).iloc[-1],
        raw=False,
    )


def _zscore(series: pd.Series, window: int = 180) -> pd.Series:
    mean = series.rolling(window, min_periods=max(20, window // 5)).mean()
    std = series.rolling(window, min_periods=max(20, window // 5)).std().replace(0, np.nan)
    return (series - mean) / std


def _top_universe_breadth(dataset: MacroRegimeDataset) -> pd.DataFrame:
    close = dataset.close
    active = dataset.universe_weights.reindex(close.index).ffill().fillna(0.0) > 0
    above_30 = (close > close.rolling(30, min_periods=20).mean()) & active
    ret_30 = close.pct_change(30, fill_method=None)
    positive_30 = (ret_30 > 0) & active
    high_30 = (close >= close.rolling(30, min_periods=20).max()) & active
    denominator = active.sum(axis=1).replace(0, np.nan)
    return pd.DataFrame({
        "top_universe_above_30dma_pct": above_30.sum(axis=1) / denominator,
        "top_universe_positive_30d_pct": positive_30.sum(axis=1) / denominator,
        "top_universe_30d_high_pct": high_30.sum(axis=1) / denominator,
    }).replace([np.inf, -np.inf], np.nan)


def _load_trend_scanning_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    # The existing trend label table is built by scanning forward price paths.
    # It is valid as a supervised label source, but not as a live-decision
    # feature.  The Verifier therefore excludes it from this standalone
    # deterministic strategy search.
    return pd.DataFrame(index=index)


def build_agentic_feature_panel(
    dataset: MacroRegimeDataset,
    public_data: PublicDataBundle | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build a parsimonious, lagged, point-in-time feature panel."""
    daily_index = dataset.close.index
    close = dataset.close
    returns = dataset.returns
    btc = close["BTC"] if "BTC" in close else close.mean(axis=1)
    eth = close["ETH"] if "ETH" in close else close.mean(axis=1)
    mix = 0.50 * btc + 0.50 * eth
    features = dataset.regime_features.reindex(daily_index).ffill().copy()

    new_data_features, new_data_metadata, _ = build_feature_panel(dataset, build_data_inventory())
    for column in ("funding_change", "funding_level"):
        if column in new_data_features:
            features[column] = new_data_features[column].reindex(daily_index).ffill()

    if public_data is not None and not public_data.chain_tvl.empty:
        tvl = public_data.chain_tvl.copy()
        tvl["date"] = pd.to_datetime(tvl["date"])
        all_tvl = tvl[tvl.chain.astype(str).str.lower().eq("all")].set_index("date").sort_index()
        if "tvl" in all_tvl:
            series = all_tvl["tvl"].reindex(daily_index).ffill()
            features["tvl_percentile"] = _rolling_percentile(series)
            features["tvl_acceleration"] = series.pct_change(7, fill_method=None) - series.pct_change(30, fill_method=None)
    if public_data is not None and not public_data.stablecoins.empty:
        stable = public_data.stablecoins.copy()
        stable["date"] = pd.to_datetime(stable["date"])
        stable = stable.drop_duplicates("date").set_index("date").sort_index()
        column = "stablecoin_supply_usd" if "stablecoin_supply_usd" in stable else None
        if column:
            series = stable[column].reindex(daily_index).ffill()
            features["stablecoin_supply_percentile"] = _rolling_percentile(series)
            features["stablecoin_acceleration"] = series.pct_change(7, fill_method=None) - series.pct_change(30, fill_method=None)

    breadth = _top_universe_breadth(dataset)
    features = pd.concat([features, breadth], axis=1)
    features["breadth_recovery"] = features["top_universe_above_30dma_pct"] - features["top_universe_above_30dma_pct"].rolling(30, min_periods=10).min()
    features["realized_vol_21d"] = returns[[c for c in ("BTC", "ETH") if c in returns]].mean(axis=1).rolling(21).std() * np.sqrt(365)
    features["realized_vol_percentile"] = _rolling_percentile(features["realized_vol_21d"])
    features["volatility_compression"] = 1.0 - features["realized_vol_percentile"]
    features["jump_intensity"] = (returns[[c for c in ("BTC", "ETH") if c in returns]].mean(axis=1).abs() > 2.5 * returns[[c for c in ("BTC", "ETH") if c in returns]].mean(axis=1).rolling(63).std()).rolling(21).mean()
    upside = returns[[c for c in ("BTC", "ETH") if c in returns]].clip(lower=0).mean(axis=1)
    downside = returns[[c for c in ("BTC", "ETH") if c in returns]].clip(upper=0).abs().mean(axis=1)
    features["upside_semivariance"] = upside.rolling(21).std()
    features["downside_to_upside_volatility_ratio"] = downside.rolling(21).std() / upside.rolling(21).std().replace(0, np.nan)
    features["market_drawdown"] = mix / mix.rolling(252, min_periods=60).max() - 1.0
    features["recovery_from_drawdown"] = mix / mix.rolling(90, min_periods=30).min() - 1.0
    features["distance_from_90d_lows"] = features["recovery_from_drawdown"]
    features["eth_btc_relative_strength_30d"] = eth.pct_change(30, fill_method=None) - btc.pct_change(30, fill_method=None)
    features["eth_btc_relative_strength_z"] = _zscore(features["eth_btc_relative_strength_30d"])
    features = pd.concat([features, _load_trend_scanning_features(daily_index)], axis=1)

    available = [column for column in features.columns if features[column].notna().any()]
    feature_metadata = []
    for column in available:
        if column in dataset.regime_features:
            source = "existing macro/crypto regime feature"
        elif column in new_data_features.columns:
            source = "accepted new-data feature panel"
        elif column.startswith("trend_"):
            source = "existing trend-scanning labels"
        else:
            source = "engineered from point-in-time OHLCV/public crypto data"
        feature_metadata.append({
            "feature": column,
            "source": source,
            "point_in_time_status": "lagged before strategy use",
            "available": True,
        })

    weekly = features[available].reindex(_rebalance_dates(daily_index, 7)).ffill()
    weekly = weekly.shift(1)
    medians = weekly.loc[DEVELOPMENT_START:DEVELOPMENT_END].median().fillna(0.0)
    weekly = weekly.ffill().fillna(medians).fillna(0.0)
    excluded = pd.DataFrame([
        {"feature": "ETF flows", "reason": "No point-in-time local ETF flow table is available."},
        {"feature": "full options implied-volatility surface", "reason": "No accepted local options surface with sufficient timestamp integrity."},
        {"feature": "COT/CME positioning", "reason": "No audited point-in-time COT/CME positioning file is available."},
        {"feature": "entity-adjusted exchange flows/MVRV/realized cap", "reason": "No accepted professional on-chain provider file is available."},
        {"feature": "trend-scanning labels", "reason": "Existing trend-scanning labels are generated from forward price paths; allowed as labels, rejected as live-decision features."},
    ])
    return weekly, pd.DataFrame(feature_metadata), excluded


def _candidate_registry() -> list[AgenticCandidate]:
    """Deterministic Thinker/Worker/Verifier candidate registry."""
    common_cost = "10/25/50/100 bps; selection at 25 bps only"
    return [
        AgenticCandidate(
            "macro_liquidity_expansion_score",
            "Family A: Macro + Liquidity Expansion",
            "Crypto performs best when macro risk appetite and crypto liquidity expansion align.",
            "Risk appetite lowers discount rates for speculative assets; stablecoin/TVL expansion proxies available crypto liquidity.",
            ("vix_level", "vix_change_21d", "equity_momentum_21d", "equity_realized_vol_21d", "stablecoin_supply_change_7d", "tvl_growth_30d", "top_universe_above_30dma_pct"),
            "available from existing macro/public crypto files",
            "all features lagged weekly",
            "Score = macro votes + liquidity/breadth votes; BTC/ETH/cash allocation by score.",
            {"risk_on_score": 5, "neutral_score": 4, "btc_weight": 0.5, "eth_weight": 0.5},
            "weekly",
            "BTC/ETH/cash",
            common_cost,
            "cash when score is weak; no leverage; turnover cap inherited from frozen framework",
            "Fails if liquidity proxies are stale or macro risk appetite is already priced.",
            "Uses seven economically filtered features, not all accepted features.",
            "Includes liquidity and breadth; not the same six-feature macro vote gate.",
        ),
        AgenticCandidate(
            "capitulation_rebound_score",
            "Family B: Capitulation-Rebound Strategy",
            "Best opportunities occur after severe drawdowns when recovery and liquidity appear.",
            "Crypto rebounds can be convex after forced selling if liquidity and breadth recover.",
            ("market_drawdown", "recovery_from_drawdown", "distance_from_90d_lows", "breadth_recovery", "stablecoin_supply_percentile", "tvl_acceleration"),
            "available from OHLCV/public crypto files",
            "all features lagged weekly",
            "Enter BTC/ETH after severe drawdown plus recovery/liquidity score.",
            {"drawdown_quantile": 0.35, "recovery_score": 3},
            "weekly",
            "BTC/ETH/cash",
            common_cost,
            "cash until capitulation and recovery both appear",
            "Can catch falling knives or miss V-shaped rebounds.",
            "Small recovery/liquidity feature set only.",
            "Entry requires prior drawdown/recovery, unlike the frozen macro gate.",
        ),
        AgenticCandidate(
            "vol_compression_breakout_score",
            "Family C: Volatility Compression Breakout",
            "Upside follows volatility compression when breadth and trend confirm expansion.",
            "Compression can precede expansion; breadth confirmation reduces false breakouts.",
            ("realized_vol_percentile", "volatility_expansion_probability", "top_universe_above_30dma_pct", "top_universe_30d_high_pct", "cross_sectional_dispersion", "jump_intensity"),
            "available from OHLCV/volatility/public features",
            "all features lagged weekly",
            "Risk-on when volatility percentile is low and breadth/highs confirm.",
            {"vol_percentile_max": 0.45, "breadth_min": 0.55},
            "weekly",
            "BTC/ETH/cash",
            common_cost,
            "cash during high-volatility or weak-breadth states",
            "Breakouts may fail after compression or occur without prior compression.",
            "Uses a mechanism-specific volatility/breadth set.",
            "Not a macro vote gate; macro only indirectly used via volatility probability if available.",
        ),
        AgenticCandidate(
            "eth_btc_leadership_rotation",
            "Family D: ETH/BTC Leadership Rotation",
            "ETH leadership signals speculative expansion; BTC leadership is more defensive.",
            "ETH/BTC relative strength can proxy risk appetite inside crypto.",
            ("eth_btc_relative_strength_30d", "eth_btc_relative_strength_z", "top_universe_above_30dma_pct", "vix_level", "equity_momentum_21d"),
            "available from BTC/ETH OHLCV and macro files",
            "all features lagged weekly",
            "Choose ETH, BTC, 50/50, or cash from relative strength plus macro stress.",
            {"eth_z": 0.40, "btc_z": -0.20, "macro_score_min": 2},
            "weekly",
            "BTC/ETH/cash",
            common_cost,
            "cash when macro/breadth state is poor",
            "ETH/BTC leadership can whipsaw and underperform during deleveraging.",
            "Single leadership mechanism, not kitchen-sink ML.",
            "Chooses BTC versus ETH, not just macro risk-on/off.",
        ),
        AgenticCandidate(
            "trend_scanning_confirmation",
            "Family E: Trend-Scanning Meta Strategy",
            "Trend-scanning labels identify statistically meaningful trend states better than fixed labels.",
            "Uses existing trend labels as confirmation, with macro stress as a safety filter.",
            ("trend_t_stat", "trend_confidence", "trend_upward_label", "vix_level", "equity_momentum_21d", "market_drawdown"),
            "rejected by Verifier: existing trend-scanning label file is forward-looking",
            "not point-in-time safe as live-decision features",
            "Invest only when lagged trend label is positive and macro stress is not extreme.",
            {"trend_upward": 1, "confidence_min": 1.0, "macro_score_min": 2},
            "weekly",
            "BTC/ETH/cash",
            common_cost,
            "cash when trend or macro confirmation is weak",
            "Trend labels may be unstable or too late after trend reversals.",
            "Uses trend labels plus few controls, not all features.",
            "Trend confirmation is structurally different from the frozen macro gate.",
        ),
        AgenticCandidate(
            "macro_gated_expansion_rebound",
            "Family F: Macro-Gated Expansion Rebound",
            "Expansion/rebound signals work only when macro stress is not extreme.",
            "Combines rebound/volatility alpha with a simpler stress filter.",
            ("vix_level", "equity_momentum_21d", "recovery_from_drawdown", "volatility_compression", "top_universe_positive_30d_pct", "stablecoin_supply_percentile"),
            "available from macro/OHLCV/public files",
            "all features lagged weekly",
            "Rebound or compression breakout signal must pass a simple VIX/equity stress filter.",
            {"vix_quantile_max": 0.80, "equity_momentum_quantile_min": 0.25},
            "weekly",
            "BTC/ETH/cash",
            common_cost,
            "cash if macro stress is extreme",
            "Could duplicate risk-off behavior without adding real rebound alpha.",
            "Small rebound/stress feature set.",
            "Macro filter is simpler and paired with rebound/expansion alpha.",
        ),
        AgenticCandidate(
            "agentic_three_signal_ensemble",
            "Family G: Agentic Deterministic Ensemble",
            "Different simple families may work in different regimes.",
            "Combines up to three independently rational component signals selected by development CPCV.",
            ("component_strategy_weights",),
            "derived only from deterministic component candidates",
            "component candidates selected using development CPCV only",
            "Equal-weight ensemble of top three non-ensemble components by development CPCV selection score.",
            {"max_components": 3, "weighting": "equal"},
            "weekly",
            "BTC/ETH/cash",
            common_cost,
            "no component can exceed 1/3 of ensemble target; no leverage",
            "May average away signal or inherit component overfitting.",
            "Combines deterministic component rules, not ML over all features.",
            "Ensembles non-macro mechanisms; frozen macro gate is benchmark only.",
        ),
    ]


def _dev_quantiles(features: pd.DataFrame) -> dict[str, dict[float, float]]:
    dev = features.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    qs = (0.20, 0.25, 0.35, 0.40, 0.50, 0.55, 0.60, 0.65, 0.75, 0.80)
    return {
        column: {q: float(dev[column].quantile(q)) if column in dev else np.nan for q in qs}
        for column in features.columns
    }


def _macro_score(row: pd.Series, q: dict[str, dict[float, float]]) -> int:
    score = 0
    score += int(row.get("vix_level", np.nan) <= q.get("vix_level", {}).get(0.50, np.nan))
    score += int(row.get("vix_change_21d", np.nan) <= q.get("vix_change_21d", {}).get(0.50, np.nan))
    score += int(row.get("equity_momentum_21d", np.nan) >= q.get("equity_momentum_21d", {}).get(0.50, np.nan))
    score += int(row.get("equity_realized_vol_21d", np.nan) <= q.get("equity_realized_vol_21d", {}).get(0.50, np.nan))
    return score


def _set_btc_eth(weights: pd.DataFrame, date: pd.Timestamp, exposure: float, eth_tilt: float = 0.50) -> None:
    exposure = float(np.clip(exposure, 0.0, 1.0))
    if "BTC" in weights.columns and "ETH" in weights.columns:
        weights.loc[date, "BTC"] = exposure * (1.0 - eth_tilt)
        weights.loc[date, "ETH"] = exposure * eth_tilt
    elif "BTC" in weights.columns:
        weights.loc[date, "BTC"] = exposure
    elif "ETH" in weights.columns:
        weights.loc[date, "ETH"] = exposure


def build_candidate_weights_from_rule(
    dataset: MacroRegimeDataset,
    features: pd.DataFrame,
    candidate: AgenticCandidate,
) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index, 7)
    q = _dev_quantiles(features)
    x = features.reindex(dates).ffill().fillna(0.0)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    for date, row in x.iterrows():
        macro_score = _macro_score(row, q)
        eth_z = float(row.get("eth_btc_relative_strength_z", 0.0))
        eth_tilt = 0.70 if eth_z >= 0.40 else (0.30 if eth_z <= -0.20 else 0.50)
        name = candidate.candidate_name
        if name == "macro_liquidity_expansion_score":
            score = macro_score
            score += int(row.get("stablecoin_supply_change_7d", 0.0) >= q.get("stablecoin_supply_change_7d", {}).get(0.50, 0.0))
            score += int(row.get("tvl_growth_30d", 0.0) >= q.get("tvl_growth_30d", {}).get(0.50, 0.0))
            score += int(row.get("top_universe_above_30dma_pct", 0.0) >= q.get("top_universe_above_30dma_pct", {}).get(0.50, 0.0))
            exposure = 1.0 if score >= 5 else (0.50 if score >= 4 else 0.0)
            _set_btc_eth(weights, date, exposure, 0.50)
        elif name == "capitulation_rebound_score":
            severe = row.get("market_drawdown", 0.0) <= q.get("market_drawdown", {}).get(0.35, -0.20)
            recovery = row.get("recovery_from_drawdown", 0.0) >= q.get("recovery_from_drawdown", {}).get(0.60, 0.0)
            liquidity = row.get("stablecoin_supply_percentile", 0.0) >= 0.50 or row.get("tvl_acceleration", 0.0) >= q.get("tvl_acceleration", {}).get(0.55, 0.0)
            breadth = row.get("breadth_recovery", 0.0) >= q.get("breadth_recovery", {}).get(0.55, 0.0)
            if severe and recovery and (liquidity or breadth) and macro_score >= 2:
                _set_btc_eth(weights, date, 1.0, eth_tilt)
        elif name == "vol_compression_breakout_score":
            compression = row.get("realized_vol_percentile", 1.0) <= 0.45
            breadth = row.get("top_universe_above_30dma_pct", 0.0) >= 0.55 or row.get("top_universe_30d_high_pct", 0.0) >= q.get("top_universe_30d_high_pct", {}).get(0.60, 0.0)
            dispersion_ok = row.get("cross_sectional_dispersion", 0.0) <= q.get("cross_sectional_dispersion", {}).get(0.75, 1.0)
            if compression and breadth and dispersion_ok:
                _set_btc_eth(weights, date, 1.0, eth_tilt)
        elif name == "eth_btc_leadership_rotation":
            breadth_ok = row.get("top_universe_above_30dma_pct", 0.0) >= q.get("top_universe_above_30dma_pct", {}).get(0.40, 0.0)
            if macro_score >= 2 and breadth_ok:
                _set_btc_eth(weights, date, 1.0, eth_tilt)
        elif name == "trend_scanning_confirmation":
            trend = row.get("trend_upward_label", 0.0) >= 1.0 and row.get("trend_confidence", 0.0) >= 1.0
            stress_ok = macro_score >= 2 and row.get("market_drawdown", 0.0) >= q.get("market_drawdown", {}).get(0.20, -0.50)
            if trend and stress_ok:
                _set_btc_eth(weights, date, 1.0, eth_tilt)
        elif name == "macro_gated_expansion_rebound":
            simple_macro = (
                row.get("vix_level", np.nan) <= q.get("vix_level", {}).get(0.80, np.nan)
                and row.get("equity_momentum_21d", np.nan) >= q.get("equity_momentum_21d", {}).get(0.25, np.nan)
            )
            rebound = row.get("recovery_from_drawdown", 0.0) >= q.get("recovery_from_drawdown", {}).get(0.60, 0.0)
            expansion = row.get("volatility_compression", 0.0) >= 0.55 and row.get("top_universe_positive_30d_pct", 0.0) >= 0.50
            liquidity = row.get("stablecoin_supply_percentile", 0.0) >= 0.50
            if simple_macro and (rebound or expansion) and liquidity:
                _set_btc_eth(weights, date, 1.0, eth_tilt)
        elif name == "agentic_three_signal_ensemble":
            raise ValueError("Ensemble weights are built after component selection.")
        else:
            raise ValueError(name)
    return weights.clip(0.0, 1.0)


def _all_risk_on(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series, pd.Series]:
    risk_on = pd.Series("risk_on", index=index, dtype=object)
    crypto = pd.Series("not_used", index=index, dtype=object)
    return risk_on, crypto, risk_on


def _extended_metrics(result: PortfolioResult, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, float]:
    metrics = period_metrics(result, start, end)
    returns = result.returns.loc[start:end].dropna()
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    weights = result.weights.reindex(returns.index).fillna(0.0)
    exposure = weights.sum(axis=1).clip(0.0, 1.0)
    metrics.update({
        "Average Winning Period": float(wins.mean()) if len(wins) else 0.0,
        "Average Losing Period": float(losses.mean()) if len(losses) else 0.0,
        "Time in BTC": float((weights.get("BTC", pd.Series(0.0, index=weights.index)) > 1e-6).mean()) if len(weights) else 0.0,
        "Time in ETH": float((weights.get("ETH", pd.Series(0.0, index=weights.index)) > 1e-6).mean()) if len(weights) else 0.0,
        "Time in Cash": float((exposure <= 1e-6).mean()) if len(exposure) else 0.0,
    })
    return metrics


def _rows_for_result(name: str, family: str, group: str, cost: int, result: PortfolioResult, selected: bool = False) -> list[dict[str, Any]]:
    rows = []
    for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
        rows.append({
            "name": name,
            "family": family,
            "benchmark_group": group,
            "split": split,
            "cost_bps": cost,
            "selected_development_candidate": selected,
            **_extended_metrics(result, start, end),
        })
    return rows


def _weekly_return(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0).dropna()


def _fold_sharpe(values: pd.Series, indices: tuple[int, ...]) -> float:
    subset = values.iloc[list(indices)].replace([np.inf, -np.inf], np.nan).dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def _safe_nanmedian(values: list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    return float(np.nanmedian(arr)) if arr.size and np.isfinite(arr).any() else np.nan


def _safe_nanmin(values: list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    return float(np.nanmin(arr)) if arr.size and np.isfinite(arr).any() else np.nan


def select_candidates_cpcv(results_25bps: dict[str, PortfolioResult], registry: list[AgenticCandidate]) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    config_returns: dict[str, pd.Series] = {}
    candidate_by_name = {candidate.candidate_name: candidate for candidate in registry}
    for name, result in results_25bps.items():
        weekly = _weekly_return(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        config_returns[name] = weekly
        fold_values = []
        if len(weekly) >= 40:
            splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
            for number, split in enumerate(splits):
                sharpe = _fold_sharpe(weekly, split.test_indices)
                fold_values.append(sharpe)
                fold_rows.append({
                    "candidate": name,
                    "family": candidate_by_name[name].strategy_family if name in candidate_by_name else "ensemble",
                    "fold": number,
                    "fold_sharpe": sharpe,
                    "test_groups": ",".join(str(group) for group in split.test_groups),
                })
        dev = _extended_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)
        turnover_penalty = max(0.0, dev["Annual Turnover"] - 12.0) * 0.05
        exposure_penalty = max(0.0, 0.20 - dev["Exposure"]) * 0.75
        simplicity_penalty = 0.02 if "ensemble" in name else 0.0
        rows.append({
            "candidate": name,
            "family": candidate_by_name[name].strategy_family if name in candidate_by_name else "Family G: Agentic Deterministic Ensemble",
            "median_fold_sharpe": _safe_nanmedian(fold_values),
            "worst_fold_sharpe": _safe_nanmin(fold_values),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_values) > 0)) if fold_values else np.nan,
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
            "turnover_penalty": turnover_penalty,
            "exposure_penalty": exposure_penalty,
            "simplicity_penalty": simplicity_penalty,
        })
    selection = pd.DataFrame(rows)
    selection["selection_score"] = (
        selection["median_fold_sharpe"].fillna(-5)
        + 0.25 * selection["worst_fold_sharpe"].fillna(-5)
        + 0.30 * selection["positive_fold_fraction"].fillna(0.0)
        - selection["turnover_penalty"]
        - selection["exposure_penalty"]
        - selection["simplicity_penalty"]
    )
    selection = selection.sort_values("selection_score", ascending=False)
    pbo = probability_backtest_overfitting(pd.concat(config_returns, axis=1).sort_index(), blocks=8)
    return selection, pd.DataFrame(fold_rows), str(selection.iloc[0].candidate), pbo


def _build_ensemble_weights(component_weights: dict[str, pd.DataFrame], component_names: list[str], columns: pd.Index) -> pd.DataFrame:
    if not component_names:
        raise ValueError("No component strategies supplied for ensemble.")
    index = component_weights[component_names[0]].index
    combined = pd.DataFrame(0.0, index=index, columns=columns)
    for name in component_names:
        combined += component_weights[name].reindex(index).fillna(0.0).reindex(columns=columns).fillna(0.0) / len(component_names)
    gross = combined.sum(axis=1)
    too_high = gross > 1.0
    if too_high.any():
        combined.loc[too_high] = combined.loc[too_high].div(gross.loc[too_high], axis=0)
    return combined


def _benchmark_weights(dataset: MacroRegimeDataset, name: str) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=dataset.close.index, columns=dataset.close.columns)
    if name == "btc_buy_hold" and "BTC" in weights:
        weights["BTC"] = 1.0
    elif name == "eth_buy_hold" and "ETH" in weights:
        weights["ETH"] = 1.0
    elif name == "btc_eth_50_50":
        for symbol in ("BTC", "ETH"):
            if symbol in weights:
                weights[symbol] = 0.50
    elif name == "equal_weight_top10":
        active = dataset.universe_weights > 0
        weights = active.div(active.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0).clip(upper=0.20)
    elif name == "pure_momentum":
        candidate = MacroRegimeCandidate(
            name="pure_momentum",
            family="Pure momentum benchmark",
            gate_profile="balanced",
            use_crypto_gate=False,
            allocation="top10_momentum",
        )
        weights, _, _, _ = build_candidate_weights(dataset, candidate, combined_override="always_on")
    else:
        raise ValueError(name)
    return weights


def _prior_benchmark_rows() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sources = [
        ("meta_gradient_boosting_60", "reports/strategy_enhancement_research/development_holdout_retention.csv", "prior_meta_overlay"),
        ("best_expansion_first_strategy", "reports/expansion_first_research/strategy_metrics.csv", "prior_expansion_first"),
        ("best_hybrid_strategy", "reports/strategy_enhancement_research/candidate_metrics.csv", "prior_hybrid"),
        ("best_portfolio_optimisation_candidate", "reports/portfolio_optimisation/portfolio_metrics.csv", "prior_portfolio_optimisation"),
        ("ml_full_feature_alpha_7d_s+10", "reports/full_feature_ml_stress_test/strategy_metrics.csv", "rejected_full_feature_ml"),
    ]
    for desired_name, path, group in sources:
        p = Path(path)
        if not p.exists():
            continue
        frame = pd.read_csv(p)
        if desired_name in frame.get("name", pd.Series(dtype=str)).astype(str).values:
            selected = frame[frame["name"].astype(str).eq(desired_name)].copy()
        elif "selected_development_candidate" in frame:
            selected = frame[frame["selected_development_candidate"].astype(str).str.lower().eq("true")].copy()
        else:
            selected = frame.head(0)
        if selected.empty:
            continue
        for _, row in selected.iterrows():
            split = row.get("split", "")
            cost = int(float(row.get("cost_bps", 25))) if pd.notna(row.get("cost_bps", 25)) else 25
            if split not in ("development", "holdout") or cost not in (25, 50):
                continue
            rows.append({
                "name": desired_name,
                "family": group,
                "benchmark_group": group,
                "split": split,
                "cost_bps": cost,
                "selected_development_candidate": False,
                "CAGR": row.get("CAGR", row.get("holdout_cagr", np.nan)),
                "Sharpe": row.get("Sharpe", row.get("holdout_sharpe", np.nan)),
                "Sortino": row.get("Sortino", np.nan),
                "Calmar": row.get("Calmar", np.nan),
                "Maximum Drawdown": row.get("Maximum Drawdown", row.get("holdout_max_drawdown", np.nan)),
                "Annual Turnover": row.get("Annual Turnover", row.get("holdout_turnover", np.nan)),
                "Exposure": row.get("Exposure", row.get("holdout_exposure", np.nan)),
            })
    return pd.DataFrame(rows)


def evaluate_benchmarks(dataset: MacroRegimeDataset, frozen_weights: pd.DataFrame, frozen_regimes: tuple[pd.Series, pd.Series, pd.Series]) -> tuple[pd.DataFrame, dict[str, PortfolioResult]]:
    rows: list[dict[str, Any]] = []
    results: dict[str, PortfolioResult] = {}
    macro, crypto, combined = frozen_regimes
    for cost in COST_LEVELS:
        frozen = backtest_weights(dataset, frozen_weights, macro, crypto, combined, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
        rows.extend(_rows_for_result(BASELINE_NAME, "Frozen macro gate", "frozen_strategy", cost, frozen))
        results[f"{BASELINE_NAME}_{cost}"] = frozen
        risk_on = _all_risk_on(dataset.close.index)
        for name, family in (
            ("btc_buy_hold", "BTC buy-and-hold"),
            ("eth_buy_hold", "ETH buy-and-hold"),
            ("btc_eth_50_50", "50/50 BTC/ETH"),
            ("equal_weight_top10", "Equal-weight top 10"),
            ("pure_momentum", "Pure momentum"),
        ):
            bench = backtest_weights(dataset, _benchmark_weights(dataset, name), *risk_on, cost_bps=cost, turnover_cap=10.0)
            rows.extend(_rows_for_result(name, family, "benchmark", cost, bench))
            results[f"{name}_{cost}"] = bench
    prior = _prior_benchmark_rows()
    if not prior.empty:
        rows.extend(prior.to_dict("records"))
    return pd.DataFrame(rows), results


def _paired_sharpe_delta_ci(left: pd.Series, right: pd.Series, samples: int = 500, block_length: int = 14, seed: int = 97) -> dict[str, float]:
    data = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
    if len(data) < block_length * 2:
        return {"lower": np.nan, "median": np.nan, "upper": np.nan, "approx_p_value": np.nan}
    rng = np.random.default_rng(seed)
    arr = data.to_numpy()
    estimates = []
    blocks = int(np.ceil(len(arr) / block_length))
    max_start = len(arr) - block_length
    for _ in range(samples):
        starts = rng.integers(0, max_start + 1, blocks)
        sample = np.concatenate([arr[start:start + block_length] for start in starts])[:len(arr)]
        left_sr = sample[:, 0].mean() / sample[:, 0].std(ddof=1) * np.sqrt(365) if sample[:, 0].std(ddof=1) else 0.0
        right_sr = sample[:, 1].mean() / sample[:, 1].std(ddof=1) * np.sqrt(365) if sample[:, 1].std(ddof=1) else 0.0
        estimates.append(left_sr - right_sr)
    lower, median, upper = np.quantile(estimates, [0.025, 0.5, 0.975])
    p_value = 2.0 * min(np.mean(np.asarray(estimates) <= 0), np.mean(np.asarray(estimates) >= 0))
    return {"lower": float(lower), "median": float(median), "upper": float(upper), "approx_p_value": float(min(1.0, p_value))}


def _rolling_diagnostics(result: PortfolioResult, name: str) -> pd.DataFrame:
    returns = result.returns.loc[HOLDOUT_START:HOLDOUT_END]
    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    dd = wealth / wealth.cummax() - 1.0
    return pd.DataFrame({
        "date": returns.index,
        "candidate": name,
        "rolling_90d_sharpe": returns.rolling(90).mean() / returns.rolling(90).std() * np.sqrt(365),
        "rolling_drawdown": dd,
        "exposure": result.weights.reindex(returns.index).fillna(0.0).sum(axis=1).values,
    })


def run_agentic_strategy_discovery(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    features, feature_metadata, excluded_features = build_agentic_feature_panel(dataset, public_data)
    registry = _candidate_registry()
    component_registry = [candidate for candidate in registry if candidate.candidate_name != "agentic_three_signal_ensemble"]
    all_regimes = _all_risk_on(dataset.close.index)
    weights_cache: dict[str, pd.DataFrame] = {}
    results_25: dict[str, PortfolioResult] = {}
    for candidate in component_registry:
        weights = build_candidate_weights_from_rule(dataset, features, candidate)
        weights_cache[candidate.candidate_name] = weights
        results_25[candidate.candidate_name] = backtest_weights(dataset, weights, *all_regimes, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)

    pre_selection, _, _, _ = select_candidates_cpcv(results_25, component_registry)
    top_components = pre_selection.head(3).candidate.astype(str).tolist()
    ensemble = [candidate for candidate in registry if candidate.candidate_name == "agentic_three_signal_ensemble"][0]
    ensemble_weights = _build_ensemble_weights(weights_cache, top_components, dataset.close.columns)
    weights_cache[ensemble.candidate_name] = ensemble_weights
    results_25[ensemble.candidate_name] = backtest_weights(dataset, ensemble_weights, *all_regimes, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)

    selection, cpcv_folds, winner_name, pbo = select_candidates_cpcv(results_25, registry)
    candidate_by_name = {candidate.candidate_name: candidate for candidate in registry}
    strategy_results: dict[str, dict[int, PortfolioResult]] = {}
    metric_rows: list[dict[str, Any]] = []
    for candidate in registry:
        strategy_results[candidate.candidate_name] = {}
        for cost in COST_LEVELS:
            result = results_25[candidate.candidate_name] if cost == 25 else backtest_weights(
                dataset,
                weights_cache[candidate.candidate_name],
                *all_regimes,
                cost_bps=cost,
                turnover_cap=FIXED_SELECTED.turnover_cap,
            )
            strategy_results[candidate.candidate_name][cost] = result
            metric_rows.extend(_rows_for_result(
                candidate.candidate_name,
                candidate.strategy_family,
                "agentic_candidate",
                cost,
                result,
                selected=candidate.candidate_name == winner_name,
            ))
    metrics = pd.DataFrame(metric_rows)

    frozen_weights, frozen_macro, frozen_crypto, frozen_combined = build_candidate_weights(dataset, FIXED_SELECTED)
    benchmarks, benchmark_results = evaluate_benchmarks(dataset, frozen_weights, (frozen_macro, frozen_crypto, frozen_combined))

    winner_25 = strategy_results[winner_name][25]
    winner_50 = strategy_results[winner_name][50]
    frozen_25 = benchmark_results[f"{BASELINE_NAME}_25"]
    winner_holdout = metrics[(metrics.name == winner_name) & (metrics.split == "holdout") & (metrics.cost_bps == 25)].iloc[0]
    winner_holdout_50 = metrics[(metrics.name == winner_name) & (metrics.split == "holdout") & (metrics.cost_bps == 50)].iloc[0]
    frozen_holdout = benchmarks[(benchmarks.name == BASELINE_NAME) & (benchmarks.split == "holdout") & (benchmarks.cost_bps == 25)].iloc[0]
    frozen_holdout_50 = benchmarks[(benchmarks.name == BASELINE_NAME) & (benchmarks.split == "holdout") & (benchmarks.cost_bps == 50)].iloc[0]
    tested_configurations = len(registry)
    dsr = deflated_sharpe_probability(winner_25.returns.loc[HOLDOUT_START:HOLDOUT_END], tested_configurations)
    bootstrap_ci = block_bootstrap_sharpe_ci(winner_25.returns.loc[HOLDOUT_START:HOLDOUT_END], samples=500, block_length=14, seed=123)
    sharpe_delta_ci = _paired_sharpe_delta_ci(
        winner_25.returns.loc[HOLDOUT_START:HOLDOUT_END],
        frozen_25.returns.loc[HOLDOUT_START:HOLDOUT_END],
    )
    exposure_threshold_sensitivity = pd.DataFrame([
        {"threshold": threshold, "selected_holdout_exposure": winner_holdout["Exposure"], "passes": bool(winner_holdout["Exposure"] >= threshold)}
        for threshold in (0.15, 0.20, 0.30, 0.50)
    ])

    failures = []
    if winner_holdout["Sharpe"] <= frozen_holdout["Sharpe"]:
        failures.append("holdout Sharpe does not exceed frozen macro strategy")
    if winner_holdout["CAGR"] < frozen_holdout["CAGR"] * 0.90:
        failures.append("holdout CAGR is materially lower than frozen macro strategy")
    if winner_holdout["Maximum Drawdown"] < frozen_holdout["Maximum Drawdown"]:
        failures.append("max drawdown is worse than frozen macro strategy")
    if winner_holdout["Annual Turnover"] > 12:
        failures.append("annual turnover exceeds 12x")
    if winner_holdout["Exposure"] < 0.20:
        failures.append("average exposure below 20%")
    if winner_holdout["Exposure"] < frozen_holdout["Exposure"] * 0.60:
        failures.append("result may be primarily cash-driven")
    if winner_holdout_50["Sharpe"] <= 0.80 or winner_holdout_50["CAGR"] <= 0:
        failures.append("does not satisfy 50 bps Sharpe/CAGR replacement rule")
    if np.isfinite(pbo) and pbo > 0.50:
        failures.append("PBO is not acceptable")
    if np.isfinite(dsr) and dsr < 0.50:
        failures.append("deflated Sharpe probability is not supportive")
    if np.isfinite(sharpe_delta_ci["upper"]) and sharpe_delta_ci["upper"] <= 0:
        failures.append("bootstrap Sharpe delta versus frozen is not supportive")

    family_best = metrics[(metrics.split == "holdout") & (metrics.cost_bps == 25)].sort_values("Sharpe", ascending=False).groupby("family").head(1)
    rolling = _rolling_diagnostics(winner_25, winner_name)
    final_decision = "replace_frozen_strategy" if not failures else "reject_agentic_replacement_keep_frozen"
    final_conclusion = (
        "Agentic AI discovered a superior deterministic replacement."
        if not failures
        else "Agentic AI did not discover a superior replacement; btc_eth_macro_gate_balanced remains final."
    )
    title_recommendation = (
        "Agentic Strategy Discovery and Robust Validation in Cryptocurrency Allocation"
        if not failures
        else PROJECT_TITLE
    )
    rejected = []
    for _, row in selection.iterrows():
        name = str(row.candidate)
        hold = metrics[(metrics.name == name) & (metrics.split == "holdout") & (metrics.cost_bps == 25)]
        reason = "Selected by development CPCV but failed replacement filters." if name == winner_name and failures else "Not selected by development CPCV; documented as rejected candidate."
        if not hold.empty and hold.iloc[0]["Exposure"] < 0.20:
            reason += " Exposure below 20%."
        rejected.append({"candidate": name, "family": row.family, "rejection_reason": reason})

    return {
        "dataset": dataset,
        "features": features,
        "feature_metadata": feature_metadata,
        "excluded_features": excluded_features,
        "candidate_registry": registry,
        "component_selection": pre_selection,
        "ensemble_components": top_components,
        "selection": selection,
        "cpcv_folds": cpcv_folds,
        "winner": candidate_by_name[winner_name],
        "metrics": metrics,
        "benchmarks": benchmarks,
        "family_best": family_best,
        "rolling_diagnostics": rolling,
        "exposure_threshold_sensitivity": exposure_threshold_sensitivity,
        "statistics": {
            "tested_configurations": tested_configurations,
            "pbo": pbo,
            "deflated_sharpe_probability": dsr,
            "bootstrap_sharpe_ci": bootstrap_ci,
            "sharpe_delta_ci_vs_frozen": sharpe_delta_ci,
            "winner_holdout_sharpe": float(winner_holdout["Sharpe"]),
            "winner_holdout_cagr": float(winner_holdout["CAGR"]),
            "winner_holdout_max_drawdown": float(winner_holdout["Maximum Drawdown"]),
            "winner_holdout_50bps_sharpe": float(winner_holdout_50["Sharpe"]),
            "winner_holdout_50bps_cagr": float(winner_holdout_50["CAGR"]),
            "frozen_holdout_sharpe": float(frozen_holdout["Sharpe"]),
            "frozen_holdout_cagr": float(frozen_holdout["CAGR"]),
            "frozen_holdout_max_drawdown": float(frozen_holdout["Maximum Drawdown"]),
            "frozen_holdout_50bps_sharpe": float(frozen_holdout_50["Sharpe"]),
            "frozen_holdout_50bps_cagr": float(frozen_holdout_50["CAGR"]),
        },
        "replacement_failures": failures,
        "rejected_candidates": pd.DataFrame(rejected),
        "final_decision": final_decision,
        "final_conclusion": final_conclusion,
        "title_recommendation": title_recommendation,
    }


def _registry_frame(registry: list[AgenticCandidate]) -> pd.DataFrame:
    rows = []
    for candidate in registry:
        row = asdict(candidate)
        row["required_features"] = ", ".join(candidate.required_features)
        row["parameters"] = json.dumps(candidate.parameters, sort_keys=True)
        rows.append(row)
    return pd.DataFrame(rows)


def write_agentic_strategy_discovery_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    registry = _registry_frame(result["candidate_registry"])
    registry.to_json(output / "candidate_registry.json", orient="records", indent=2)
    registry.to_csv(output / "candidate_registry.csv", index=False)
    result["feature_metadata"].to_csv(output / "feature_mapping.csv", index=False)
    result["excluded_features"].to_csv(output / "excluded_features.csv", index=False)
    result["selection"].to_csv(output / "candidate_selection.csv", index=False)
    result["cpcv_folds"].to_csv(output / "cpcv_folds.csv", index=False)
    result["metrics"].to_csv(output / "strategy_metrics.csv", index=False)
    result["benchmarks"].to_csv(output / "benchmark_metrics.csv", index=False)
    result["family_best"].to_csv(output / "family_best.csv", index=False)
    result["rolling_diagnostics"].to_csv(output / "rolling_diagnostics.csv", index=False)
    result["exposure_threshold_sensitivity"].to_csv(output / "exposure_threshold_sensitivity.csv", index=False)
    result["rejected_candidates"].to_csv(output / "rejected_candidates.csv", index=False)

    stats = result["statistics"]
    failures = result["replacement_failures"]
    winner = result["winner"]

    (output / "executive_summary.md").write_text(f"""# Executive summary

Study: **Agentic AI Strategy Discovery for Systematic Cryptocurrency Allocation**

The frozen benchmark **{BASELINE_NAME}** was not modified, reselected, or retuned.

## Outcome

- Development-CPCV selected candidate: {winner.candidate_name}
- Candidate family: {winner.strategy_family}
- Tested deterministic configurations: {stats['tested_configurations']}
- Final decision: {result['final_decision']}
- Final conclusion: {result['final_conclusion']}
- Recommended project title: {result['title_recommendation']}

## Holdout comparison at 25 bps

- Selected agentic Sharpe: {_fmt(stats['winner_holdout_sharpe'])}
- Frozen Sharpe: {_fmt(stats['frozen_holdout_sharpe'])}
- Selected agentic CAGR: {_fmt(stats['winner_holdout_cagr'], True)}
- Frozen CAGR: {_fmt(stats['frozen_holdout_cagr'], True)}
- Selected max drawdown: {_fmt(stats['winner_holdout_max_drawdown'], True)}
- Frozen max drawdown: {_fmt(stats['frozen_holdout_max_drawdown'], True)}

Failure reasons: {('; '.join(failures) if failures else 'None.')}
""", encoding="utf-8")

    (output / "agentic_architecture.md").write_text("""# Agentic architecture

The workflow is deterministic and auditable.

1. Strategy Thinker: generates economically motivated hypotheses from prior evidence.
2. Feature Worker: maps each hypothesis to existing point-in-time-safe local features.
3. Strategy Worker: converts each hypothesis into a deterministic BTC/ETH/cash rule.
4. Verifier: rejects lookahead, unavailable data, broad kitchen-sink feature use, holdout tuning, low exposure, excessive turnover, unclear rationale, and similarity to rejected full-feature ML.

No LLM calls occur inside historical backtest loops. Final trading rules are reproducible without live LLM calls.
""", encoding="utf-8")

    (output / "candidate_registry.md").write_text(f"""# Candidate registry

All candidates are deterministic. Failed candidates are not silently discarded.

{_table(registry, [('candidate_name', 'Candidate'), ('strategy_family', 'Family'), ('hypothesis', 'Hypothesis'), ('required_features', 'Required features'), ('exact_formula_or_model_specification', 'Rule'), ('reason_not_full_feature_ml', 'Not full-feature ML'), ('reason_not_duplicate_frozen_macro', 'Not duplicate')], limit=80)}
""", encoding="utf-8")

    (output / "feature_mapping.md").write_text(f"""# Feature mapping

All included features are lagged before use. Unavailable data is excluded and documented.

## Available mapped features

{_table(result['feature_metadata'], [('feature', 'Feature'), ('source', 'Source'), ('point_in_time_status', 'Point-in-time status'), ('available', 'Available')], limit=120)}

## Excluded unavailable features

{_table(result['excluded_features'], [('feature', 'Feature'), ('reason', 'Reason')], limit=40)}
""", encoding="utf-8")

    (output / "strategy_family_results.md").write_text(f"""# Strategy family results

## Development-CPCV selection

{_table(result['selection'], [('candidate', 'Candidate'), ('family', 'Family'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold Sharpe'), ('positive_fold_fraction', 'Positive folds'), ('development_sharpe', 'Development Sharpe'), ('development_turnover', 'Development turnover'), ('development_exposure', 'Development exposure'), ('selection_score', 'Selection score')], {'positive_fold_fraction', 'development_exposure'}, limit=80)}

## Best holdout result by family

{_table(result['family_best'], [('name', 'Candidate'), ('family', 'Family'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure'), ('Time in Cash', 'Time in cash')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'Time in Cash'}, limit=80)}
""", encoding="utf-8")

    selected_metrics = result["metrics"][result["metrics"].selected_development_candidate.astype(bool)]
    (output / "validation_results.md").write_text(f"""# Validation results

Selection was performed using development-period CPCV only. Holdout was opened only after candidate selection.

## Selected candidate cost sensitivity

{_table(selected_metrics[selected_metrics.split.eq('holdout')], [('name', 'Candidate'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Calmar', 'Calmar'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure'), ('Worst Month', 'Worst month'), ('Hit Rate', 'Hit rate'), ('Average Winning Period', 'Avg win'), ('Average Losing Period', 'Avg loss'), ('Time in BTC', 'Time BTC'), ('Time in ETH', 'Time ETH'), ('Time in Cash', 'Time cash')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'Time in BTC', 'Time in ETH', 'Time in Cash'}, limit=20)}

## Rejected candidates

{_table(result['rejected_candidates'], [('candidate', 'Candidate'), ('family', 'Family'), ('rejection_reason', 'Rejection reason')], limit=80)}
""", encoding="utf-8")

    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

The full-feature ML stress-test candidate is included only as a rejected benchmark.

{_table(result['benchmarks'], [('name', 'Name'), ('family', 'Family'), ('benchmark_group', 'Group'), ('split', 'Split'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=160)}
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

- Tested configurations: {stats['tested_configurations']}
- PBO: {_fmt(stats['pbo'], True)}
- Deflated Sharpe probability: {_fmt(stats['deflated_sharpe_probability'], True)}
- Bootstrap Sharpe CI: [{_fmt(stats['bootstrap_sharpe_ci']['lower'])}, {_fmt(stats['bootstrap_sharpe_ci']['upper'])}]
- Sharpe delta vs frozen median: {_fmt(stats['sharpe_delta_ci_vs_frozen']['median'])}
- Sharpe delta CI vs frozen: [{_fmt(stats['sharpe_delta_ci_vs_frozen']['lower'])}, {_fmt(stats['sharpe_delta_ci_vs_frozen']['upper'])}]
- Approximate paired bootstrap p-value: {_fmt(stats['sharpe_delta_ci_vs_frozen']['approx_p_value'], True)}

## CPCV fold distribution

{_table(result['cpcv_folds'], [('candidate', 'Candidate'), ('family', 'Family'), ('fold', 'Fold'), ('fold_sharpe', 'Fold Sharpe')], limit=160)}

## Exposure-threshold sensitivity

{_table(result['exposure_threshold_sensitivity'], [('threshold', 'Exposure threshold'), ('selected_holdout_exposure', 'Selected exposure'), ('passes', 'Passes')], {'threshold', 'selected_holdout_exposure'})}
""", encoding="utf-8")

    (output / "economic_interpretation.md").write_text(f"""# Economic interpretation

Best development-CPCV candidate: **{winner.candidate_name}**.

## Why it should work

{winner.economic_rationale}

## Why it might fail

{winner.expected_failure_mode}

## Alpha or risk avoidance?

The selected candidate is compared against the frozen macro-regime benchmark. If it fails replacement criteria, the result is treated as statistical noise or insufficient risk-adjusted evidence, not proven alpha.

## Adds beyond macro-regime conditioning?

{winner.reason_not_duplicate_frozen_macro}

## Interpretability

The selected rule is deterministic and more mechanism-specific than full-feature ML. It is not promoted unless it beats the frozen strategy under holdout, cost, and statistical controls.
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

1. Did agentic AI discover a superior strategy? {'Yes' if result['final_decision'] == 'replace_frozen_strategy' else 'No'}.
2. Which strategy family worked best? Development CPCV selected **{winner.strategy_family}** via `{winner.candidate_name}`.
3. Did the improvement come from alpha or lower exposure? Replacement was {'accepted' if not failures else 'rejected'}; lower-exposure/cash-driven evidence is not promoted.
4. Did the best candidate survive 50 bps costs? Selected 50 bps Sharpe: {_fmt(stats['winner_holdout_50bps_sharpe'])}; CAGR: {_fmt(stats['winner_holdout_50bps_cagr'], True)}.
5. Was the result statistically convincing? {'Yes' if not failures else 'No'}; PBO {_fmt(stats['pbo'], True)}, DSR {_fmt(stats['deflated_sharpe_probability'], True)}.
6. Did the result avoid repeating full-feature ML? Yes. Candidates use parsimonious deterministic mechanisms; the rejected full-feature ML stress-test candidate is benchmark-only.
7. Should the Applied Project title change? {'Yes' if result['final_decision'] == 'replace_frozen_strategy' else 'No'}.
8. Should {BASELINE_NAME} be replaced? {'Yes' if result['final_decision'] == 'replace_frozen_strategy' else 'No'}.

Final conclusion: **{result['final_conclusion']}**

Recommended title: **{result['title_recommendation']}**

Agentic AI may be used as a monitoring, explanation, or research-assistance layer unless a future deterministic candidate clears the full replacement criteria.
""", encoding="utf-8")

    payload = {
        "candidate_registry": registry,
        "feature_metadata": result["feature_metadata"],
        "excluded_features": result["excluded_features"],
        "selection": result["selection"],
        "cpcv_folds": result["cpcv_folds"],
        "metrics": result["metrics"],
        "benchmarks": result["benchmarks"],
        "family_best": result["family_best"],
        "statistics": result["statistics"],
        "ensemble_components": result["ensemble_components"],
        "replacement_failures": failures,
        "final_decision": result["final_decision"],
        "final_conclusion": result["final_conclusion"],
        "title_recommendation": result["title_recommendation"],
    }
    (output / "results.json").write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def run_default_agentic_strategy_discovery(output_dir: str | Path = "reports/agentic_strategy_discovery") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_agentic_strategy_discovery(panel, macro, public_data, probability)
    write_agentic_strategy_discovery_reports(output_dir, result)
    return result


__all__ = [
    "AgenticCandidate",
    "build_agentic_feature_panel",
    "build_candidate_weights_from_rule",
    "run_agentic_strategy_discovery",
    "write_agentic_strategy_discovery_reports",
    "run_default_agentic_strategy_discovery",
]
