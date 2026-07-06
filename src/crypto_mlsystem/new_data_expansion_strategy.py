"""New-data upside expansion research.

This module is intentionally gated:

1. Inventory WRDS/public sources for ETF flows, on-chain indicators, and
   options-implied indicators.
2. Engineer only lagged features from actually available small public datasets.
3. Validate features against predeclared upside targets using development data.
4. Run the trading overlay only if at least three New Data Tier-1 features are
   found from development-only evidence.

The frozen ``btc_eth_macro_gate_balanced`` strategy is used as a benchmark and
Layer 1. It is never modified or reselected by this module.
"""
from __future__ import annotations

import importlib.util
import json
import math
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, precision_recall_fscore_support, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .expansion_state_model import (
    _all_risk_on,
    _buy_hold_weights,
    _feature_importance,
    _fmt,
    _json_safe,
    _positive_probability,
    _prior_meta_overlay_rows,
    _rebalance_dates,
    _rows_for_result,
    _table,
    _threshold_from_dev,
    _weekly_return,
)
from .expansion_tier1_overlay import benchmark_rows as previous_benchmark_rows
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
)
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import deflated_sharpe_probability, probability_backtest_overfitting


DEVELOPMENT_START = pd.Timestamp("2019-07-05")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")
BASELINE_NAME = FIXED_SELECTED.name
OUTPUT_DATA_DIR = Path("data/processed/new_data_expansion")


TARGET_SPECS = (
    ("target_a_btc_30d_upside", "BTC 30-day forward return > +15%"),
    ("target_b_eth_30d_upside", "ETH 30-day forward return > +20%"),
    ("target_c_btc_eth_50_50_30d_upside", "BTC/ETH 50-50 30-day forward return > +15%"),
    ("target_d_eth_beats_btc_30d", "ETH beats BTC over next 30 days by > +5%"),
    ("target_e_top20_leadership", "Top-20 equal-weight basket beats BTC/ETH 50-50 by > +5%"),
)


@dataclass(frozen=True)
class SourceInventoryRow:
    source_family: str
    source: str
    status: str
    start_date: str
    end_date: str
    observations: int
    frequency: str
    timestamp_convention: str
    reporting_lag: str
    point_in_time_usable: bool
    notes: str
    url_or_wrds_table: str


@dataclass(frozen=True)
class ModelSpec:
    name: str
    family: str
    factory: Callable[[], Any]


@dataclass(frozen=True)
class OverlayCandidate:
    name: str
    allocation_type: str
    expansion_model: str
    leadership_model: str | None
    top20_model: str | None
    multiplier: float
    threshold: float
    description: str


@dataclass
class PredictionBundle:
    config_name: str
    target: str
    target_description: str
    model_name: str
    threshold: float
    full_probability: pd.Series
    dev_probability: pd.Series
    holdout_probability: pd.Series
    feature_importance: pd.DataFrame


def _request_json(url: str, pause_seconds: float = 0.15) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/html,*/*",
            "User-Agent": "crypto-ml-research-new-data/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = response.read().decode("utf-8")
    time.sleep(pause_seconds)
    return json.loads(payload)


def _source_row(
    source_family: str,
    source: str,
    status: str,
    frame: pd.DataFrame | None,
    frequency: str,
    timestamp_convention: str,
    reporting_lag: str,
    point_in_time_usable: bool,
    notes: str,
    url_or_wrds_table: str,
) -> SourceInventoryRow:
    if frame is not None and not frame.empty and "date" in frame:
        dates = pd.to_datetime(frame["date"]).dropna()
        return SourceInventoryRow(
            source_family,
            source,
            status,
            str(dates.min().date()) if len(dates) else "",
            str(dates.max().date()) if len(dates) else "",
            int(len(frame)),
            frequency,
            timestamp_convention,
            reporting_lag,
            point_in_time_usable,
            notes,
            url_or_wrds_table,
        )
    return SourceInventoryRow(
        source_family,
        source,
        status,
        "",
        "",
        0,
        frequency,
        timestamp_convention,
        reporting_lag,
        False,
        notes,
        url_or_wrds_table,
    )


def _parse_blockchain_chart(payload: dict[str, Any], column: str) -> pd.DataFrame:
    rows = []
    for item in payload.get("values", []) or []:
        rows.append({"date": pd.to_datetime(item.get("x"), unit="s", utc=True).tz_localize(None).normalize(), column: item.get("y")})
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")


def _fetch_blockchain_charts(processed_dir: Path) -> tuple[pd.DataFrame, list[SourceInventoryRow]]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    specs = {
        "btc_transaction_count": "https://api.blockchain.info/charts/n-transactions?timespan=all&format=json",
        "btc_active_addresses": "https://api.blockchain.info/charts/n-unique-addresses?timespan=all&format=json",
    }
    frames = []
    rows = []
    for column, url in specs.items():
        try:
            frame = _parse_blockchain_chart(_request_json(url), column)
            frame.to_csv(processed_dir / f"blockchain_{column}.csv", index=False)
            rows.append(_source_row(
                "on-chain",
                f"Blockchain.com {column.replace('_', ' ')}",
                "downloaded",
                frame,
                "irregular/daily chart samples",
                "chart timestamp is UTC date supplied by API",
                "unknown; treated as available after date close and lagged one day",
                True,
                "Usable as BTC-only public on-chain activity proxy; not entity-adjusted and not exchange-flow data.",
                url,
            ))
            frames.append(frame.set_index("date"))
        except Exception as exc:  # pragma: no cover - network dependent
            rows.append(_source_row(
                "on-chain",
                f"Blockchain.com {column.replace('_', ' ')}",
                "unavailable",
                None,
                "daily",
                "UTC",
                "unknown",
                False,
                f"Download failed: {type(exc).__name__}: {exc}",
                url,
            ))
    if not frames:
        return pd.DataFrame(), rows
    merged = pd.concat(frames, axis=1).sort_index().reset_index()
    merged.to_csv(processed_dir / "blockchain_btc_onchain_activity.csv", index=False)
    return merged, rows


def _fetch_deribit_hist_vol(processed_dir: Path) -> tuple[pd.DataFrame, list[SourceInventoryRow]]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    frames = []
    for currency in ("BTC", "ETH"):
        url = f"https://www.deribit.com/api/v2/public/get_historical_volatility?currency={currency}"
        try:
            payload = _request_json(url)
            data = payload.get("result", []) if isinstance(payload, dict) else []
            frame = pd.DataFrame(data, columns=["timestamp_ms", f"{currency.lower()}_deribit_hist_vol"])
            if not frame.empty:
                frame["timestamp"] = pd.to_datetime(frame.timestamp_ms, unit="ms", utc=True).dt.tz_localize(None)
                frame["date"] = frame.timestamp.dt.normalize()
                frame = frame.groupby("date", as_index=False)[f"{currency.lower()}_deribit_hist_vol"].last()
                frame.to_csv(processed_dir / f"deribit_{currency.lower()}_historical_volatility.csv", index=False)
            usable = bool(not frame.empty and frame["date"].min() <= DEVELOPMENT_END and frame["date"].max() >= HOLDOUT_START and len(frame) >= 365)
            rows.append(_source_row(
                "options-implied",
                f"Deribit {currency} historical volatility endpoint",
                "downloaded_short_history" if not usable else "downloaded",
                frame,
                "intraday endpoint aggregated to daily",
                "exchange timestamp UTC",
                "public endpoint; no full historical option-surface vintage available",
                usable,
                "Endpoint is reachable but does not provide enough 2019-2026 history for this study; no options feature enters the model.",
                url,
            ))
            frames.append(frame.set_index("date"))
        except Exception as exc:  # pragma: no cover - network dependent
            rows.append(_source_row(
                "options-implied",
                f"Deribit {currency} historical volatility endpoint",
                "unavailable",
                None,
                "intraday",
                "UTC",
                "public endpoint",
                False,
                f"Download failed: {type(exc).__name__}: {exc}",
                url,
            ))
    if not frames:
        return pd.DataFrame(), rows
    merged = pd.concat(frames, axis=1).sort_index().reset_index()
    merged.to_csv(processed_dir / "deribit_public_historical_volatility.csv", index=False)
    return merged, rows


def _try_source(url: str, source_family: str, source: str, notes: str) -> SourceInventoryRow:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "crypto-ml-research-new-data/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            status = getattr(response, "status", 200)
            response.read(128)
        return _source_row(source_family, source, f"reachable_http_{status}", None, "unknown", "unknown", "unknown", False, notes, url)
    except Exception as exc:  # pragma: no cover - network dependent
        return _source_row(
            source_family,
            source,
            "unavailable",
            None,
            "unknown",
            "unknown",
            "unknown",
            False,
            f"{notes} Access check failed: {type(exc).__name__}: {exc}",
            url,
        )


def _wrds_inventory_rows(path: str | Path = "reports/wrds_inventory/results.json") -> list[SourceInventoryRow]:
    path = Path(path)
    if not path.exists():
        return [
            _source_row("WRDS", "WRDS prior inventory", "not_found", None, "unknown", "unknown", "unknown", False, "No prior WRDS inventory report found.", str(path))
        ]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [_source_row("WRDS", "WRDS prior inventory", "unreadable", None, "unknown", "unknown", "unknown", False, str(exc), str(path))]

    details = payload.get("table_details", []) or []
    matches = payload.get("table_matches", []) or []
    rows: list[SourceInventoryRow] = []

    def match(category: str, wanted: tuple[str, ...], family: str, source: str, note: str) -> None:
        examples = []
        for item in details:
            cats = " ".join(item.get("categories", []) or []).lower()
            lib_table = f"{item.get('library', '')}.{item.get('table', '')}".lower()
            if category in cats or any(term in lib_table for term in wanted):
                examples.append(item)
        if examples:
            first = examples[0]
            rows.append(SourceInventoryRow(
                family,
                source,
                "potential_wrds_tables_found",
                str(first.get("date_coverage", "")),
                str(first.get("date_coverage", "")),
                len(examples),
                str(first.get("frequency", "unknown")),
                "WRDS table date columns; publication timestamp must be audited per table",
                "unknown until table-specific download/audit",
                False,
                f"{note} Matched {len(examples)} table(s); no large WRDS dataset downloaded in this module.",
                "; ".join(f"{x.get('library')}.{x.get('table')}" for x in examples[:8]),
            ))
        else:
            match_examples = []
            for item in matches:
                cats = str(item.get("category", "")).lower()
                lib_table = f"{item.get('library', '')}.{item.get('table', '')}".lower()
                if category in cats or any(term in lib_table for term in wanted):
                    match_examples.append(item)
            if match_examples:
                rows.append(SourceInventoryRow(
                    family,
                    source,
                    "potential_wrds_matches_found",
                    "",
                    "",
                    len(match_examples),
                    "unknown from inventory",
                    "WRDS table date columns; publication timestamp must be audited per table",
                    "unknown until table-specific download/audit",
                    False,
                    f"{note} Matched {len(match_examples)} candidate table(s); no large WRDS dataset downloaded in this module.",
                    "; ".join(f"{x.get('library')}.{x.get('table')}" for x in match_examples[:8]),
                ))
            else:
                rows.append(_source_row(family, source, "not_found_in_prior_wrds_inventory", None, "unknown", "unknown", "unknown", False, note, str(path)))

    match("etf flows", ("fund_flows", "etf", "flows"), "ETF flows", "WRDS ETF/fund-flow tables", "Potential institutional-flow source, but BTC/ETH ETF identifier mapping and reporting lag are not confirmed.")
    match("options / optionmetrics", ("optionm", "opprcd", "option_price"), "options-implied", "WRDS OptionMetrics/CBOE tables", "Useful for equity/index option risk proxies; prior inventory did not identify complete crypto options surfaces.")
    match("news / ravenpack", ("raven", "news"), "news/sentiment", "WRDS RavenPack/news tables", "Potential sentiment source if licensed; high-dimensional and timestamp-sensitive, not downloaded here.")
    return rows


def discover_new_data_sources(processed_dir: str | Path = OUTPUT_DATA_DIR) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    processed = Path(processed_dir)
    frames: dict[str, pd.DataFrame] = {}
    inventory_rows: list[SourceInventoryRow] = []
    blockchain, rows = _fetch_blockchain_charts(processed)
    frames["blockchain_btc_onchain"] = blockchain
    inventory_rows.extend(rows)
    deribit, rows = _fetch_deribit_hist_vol(processed)
    frames["deribit_hist_vol"] = deribit
    inventory_rows.extend(rows)
    inventory_rows.extend(_wrds_inventory_rows())
    inventory_rows.append(_source_row(
        "ETF flows",
        "Farside Bitcoin ETF flow table",
        "not_downloaded_structured_table_unavailable",
        None,
        "daily if accessible",
        "web table date convention must be audited",
        "same/next-day web publication; exact timestamp unavailable",
        False,
        "Public page was identified, but structured table extraction returned HTTP 403 in this environment; no ETF-flow data was used.",
        "https://farside.co.uk/bitcoin-etf-flow-all-data/",
    ))
    inventory_rows.append(_source_row(
        "ETF flows",
        "Farside Ethereum ETF flow table",
        "not_downloaded_structured_table_unavailable",
        None,
        "daily if accessible",
        "web table date convention must be audited",
        "same/next-day web publication; exact timestamp unavailable",
        False,
        "Public page was identified, but structured table extraction returned HTTP 403 in this environment; no ETF-flow data was used.",
        "https://farside.co.uk/ethereum-etf-flow-all-data/",
    ))
    inventory_rows.append(_try_source(
        "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
        "on-chain",
        "Coin Metrics community asset metrics API",
        "Potential source for active addresses, transaction count, realized cap, and MVRV; access was blocked/unauthenticated in this environment.",
    ))
    inventory = pd.DataFrame([row.__dict__ for row in inventory_rows])
    inventory.to_csv(processed / "data_inventory.csv", index=False)
    return inventory, frames


def build_new_data_features(frames: dict[str, pd.DataFrame], date_index: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = pd.DataFrame(index=pd.DatetimeIndex(date_index).sort_values())
    metadata: list[dict[str, Any]] = []

    def add(name: str, series: pd.Series, family: str, formula: str, source: str, available: bool = True) -> None:
        if available:
            features[name] = series.reindex(features.index).ffill()
        metadata.append({
            "feature": name,
            "family": family,
            "formula": formula,
            "source": source,
            "lag": "1 day",
            "availability": "implemented" if available else "unavailable",
            "economic_rationale": _feature_rationale(name),
        })

    blockchain = frames.get("blockchain_btc_onchain", pd.DataFrame())
    if not blockchain.empty and "date" in blockchain:
        daily = blockchain.copy()
        daily["date"] = pd.to_datetime(daily["date"])
        daily = daily.drop_duplicates("date").set_index("date").sort_index().reindex(features.index).ffill()
        if "btc_active_addresses" in daily:
            add(
                "btc_active_address_growth_30d",
                daily["btc_active_addresses"].pct_change(30, fill_method=None).shift(1),
                "on-chain",
                "pct_change(active addresses, 30d), lagged 1 day",
                "Blockchain.com charts API",
            )
            add(
                "btc_active_address_growth_7d",
                daily["btc_active_addresses"].pct_change(7, fill_method=None).shift(1),
                "on-chain",
                "pct_change(active addresses, 7d), lagged 1 day",
                "Blockchain.com charts API",
            )
        if "btc_transaction_count" in daily:
            add(
                "btc_transaction_growth_30d",
                daily["btc_transaction_count"].pct_change(30, fill_method=None).shift(1),
                "on-chain",
                "pct_change(transaction count, 30d), lagged 1 day",
                "Blockchain.com charts API",
            )
            add(
                "btc_transaction_growth_7d",
                daily["btc_transaction_count"].pct_change(7, fill_method=None).shift(1),
                "on-chain",
                "pct_change(transaction count, 7d), lagged 1 day",
                "Blockchain.com charts API",
            )

    unavailable_specs = (
        ("etf_net_flow", "ETF flows", "daily BTC/ETH ETF net flow", "Farside/WRDS ETF-flow source unavailable or not point-in-time audited"),
        ("etf_flow_as_pct_aum", "ETF flows", "net flow divided by AUM", "ETF AUM/flow source unavailable"),
        ("etf_5d_flow", "ETF flows", "5-day net ETF flow", "ETF-flow source unavailable"),
        ("etf_21d_flow", "ETF flows", "21-day net ETF flow", "ETF-flow source unavailable"),
        ("etf_flow_acceleration", "ETF flows", "5-day flow minus prior 5-day flow", "ETF-flow source unavailable"),
        ("etf_flow_percentile", "ETF flows", "rolling percentile of ETF flow", "ETF-flow source unavailable"),
        ("etf_inflow_streak", "ETF flows", "consecutive days of positive flow", "ETF-flow source unavailable"),
        ("etf_outflow_shock", "ETF flows", "large negative flow shock", "ETF-flow source unavailable"),
        ("exchange_flow_pressure", "on-chain", "exchange inflow minus outflow pressure", "entity-labeled exchange-flow data unavailable"),
        ("mvrv_percentile", "on-chain", "MVRV rolling percentile", "MVRV/realized-cap source unavailable"),
        ("realized_cap_growth", "on-chain", "realized cap growth", "realized-cap source unavailable"),
        ("holder_accumulation_proxy", "on-chain", "holder accumulation proxy", "holder cohort/source unavailable"),
        ("option_iv_level", "options-implied", "constant-maturity IV level", "full options surface history unavailable"),
        ("option_iv_change", "options-implied", "change in IV", "full options surface history unavailable"),
        ("option_skew_level", "options-implied", "put/call skew level", "full options surface history unavailable"),
        ("option_skew_change", "options-implied", "change in skew", "full options surface history unavailable"),
        ("option_put_call_change", "options-implied", "put/call ratio change", "put/call history unavailable"),
        ("option_term_structure_slope", "options-implied", "long IV minus short IV", "full term structure unavailable"),
        ("option_risk_reversal_proxy", "options-implied", "call IV minus put IV", "risk reversal history unavailable"),
    )
    for name, family, formula, source in unavailable_specs:
        add(name, pd.Series(dtype=float), family, formula, source, available=False)

    features = features.replace([np.inf, -np.inf], np.nan)
    development = features.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    medians = development.median().fillna(0.0)
    features = features.ffill().fillna(medians).fillna(0.0)
    return features, pd.DataFrame(metadata)


def _feature_rationale(name: str) -> str:
    if "active_address" in name:
        return "Rising BTC address activity can proxy broader network participation and attention before upside expansion."
    if "transaction" in name:
        return "Rising BTC transaction count can proxy chain usage and settlement demand before upside expansion."
    if name.startswith("etf"):
        return "ETF flows would proxy regulated institutional demand if timely data were available."
    if name.startswith("option"):
        return "Option-implied variables would proxy forward-looking risk appetite and tail pricing if historical surfaces were available."
    if "mvrv" in name or "realized" in name:
        return "Valuation and realized-cap measures can identify undervaluation/repricing regimes if methodology and vintages are available."
    return "Potential new-data feature; excluded unless available and development-validated."


def _forward_return(close: pd.DataFrame, symbol: str, dates: pd.DatetimeIndex, horizon_days: int = 30) -> pd.Series:
    values = []
    for date in dates:
        if date not in close.index or symbol not in close:
            values.append(np.nan)
            continue
        end_pos = close.index.searchsorted(date + pd.Timedelta(days=horizon_days))
        if end_pos >= len(close.index):
            values.append(np.nan)
            continue
        start = close.at[date, symbol]
        end = close.iloc[end_pos][symbol]
        values.append(float(end / start - 1.0) if pd.notna(start) and pd.notna(end) and start > 0 else np.nan)
    return pd.Series(values, index=dates)


def build_new_data_targets(dataset: MacroRegimeDataset, dates: pd.DatetimeIndex) -> pd.DataFrame:
    btc = _forward_return(dataset.close, "BTC", dates)
    eth = _forward_return(dataset.close, "ETH", dates)
    mix = 0.50 * btc + 0.50 * eth
    top20_values = []
    for date in dates:
        if date not in dataset.close.index or date not in dataset.universe_weights.index:
            top20_values.append(np.nan)
            continue
        end_pos = dataset.close.index.searchsorted(date + pd.Timedelta(days=30))
        if end_pos >= len(dataset.close.index):
            top20_values.append(np.nan)
            continue
        active = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        start = dataset.close.loc[date, active].replace(0, np.nan)
        end = dataset.close.iloc[end_pos][active]
        forward = (end / start - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
        top20_values.append(float(forward.mean()) if len(forward) else np.nan)
    top20 = pd.Series(top20_values, index=dates)
    targets = pd.DataFrame(index=dates)
    targets["target_a_btc_30d_upside"] = (btc > 0.15).astype(float)
    targets["target_b_eth_30d_upside"] = (eth > 0.20).astype(float)
    targets["target_c_btc_eth_50_50_30d_upside"] = (mix > 0.15).astype(float)
    targets["target_d_eth_beats_btc_30d"] = ((eth - btc) > 0.05).astype(float)
    targets["target_e_top20_leadership"] = ((top20 - mix) > 0.05).astype(float)
    unavailable = pd.concat([btc, eth, mix, top20], axis=1).isna().any(axis=1)
    targets.loc[unavailable, :] = np.nan
    return targets


def _normal_p_value(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return np.nan
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _newey_west_tstat(x: pd.Series, y: pd.Series, lags: int = 4) -> tuple[float, float]:
    data = pd.concat([x.rename("x"), y.rename("y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 30 or data.x.std() == 0:
        return np.nan, np.nan
    x_std = (data.x - data.x.mean()) / data.x.std()
    design = np.column_stack([np.ones(len(data)), x_std.to_numpy()])
    yv = data.y.to_numpy(dtype=float)
    xtx_inv = np.linalg.pinv(design.T @ design)
    beta = xtx_inv @ design.T @ yv
    residuals = yv - design @ beta
    meat = np.zeros((2, 2))
    for lag in range(0, min(lags, len(data) - 1) + 1):
        weight = 1.0 if lag == 0 else 1.0 - lag / (lags + 1.0)
        if lag == 0:
            gamma = design.T @ np.diag(residuals ** 2) @ design
            meat += gamma
        else:
            for t in range(lag, len(data)):
                outer = np.outer(design[t], design[t - lag])
                meat += weight * residuals[t] * residuals[t - lag] * (outer + outer.T)
    cov = xtx_inv @ meat @ xtx_inv
    se = math.sqrt(max(cov[1, 1], 0.0)) if cov.shape == (2, 2) else np.nan
    t_stat = float(beta[1] / se) if se and np.isfinite(se) and se > 0 else np.nan
    return t_stat, _normal_p_value(t_stat)


def _spearman_ic(feature: pd.Series, target: pd.Series) -> float:
    data = pd.concat([feature.rename("x"), target.rename("y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 30 or data.x.nunique() < 3 or data.y.nunique() < 2:
        return np.nan
    return float(data.x.rank().corr(data.y.rank()))


def _auc(feature: pd.Series, target: pd.Series) -> tuple[float, float, int]:
    data = pd.concat([feature.rename("x"), target.rename("y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 30 or data.y.nunique() < 2 or data.x.nunique() < 3:
        return np.nan, np.nan, 1
    auc = float(roc_auc_score(data.y.astype(int), data.x))
    direction = 1 if auc >= 0.5 else -1
    return auc, max(auc, 1.0 - auc), direction


def _cpcv_feature_stability(feature: pd.Series, target: pd.Series, direction: int) -> tuple[float, float, int]:
    data = pd.concat([feature.rename("x"), target.rename("y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 60 or data.y.nunique() < 2:
        return np.nan, np.nan, 0
    splits = combinatorial_purged_splits(len(data), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    fold_aucs = []
    for split in splits:
        subset = data.iloc[list(split.test_indices)]
        if subset.y.nunique() < 2 or subset.x.nunique() < 3:
            continue
        fold_aucs.append(float(roc_auc_score(subset.y.astype(int), subset.x)))
    if not fold_aucs:
        return np.nan, np.nan, 0
    folds = np.asarray(fold_aucs, dtype=float)
    stable = folds >= 0.5 if direction >= 0 else folds <= 0.5
    return float(np.nanmedian(np.where(direction >= 0, folds, 1.0 - folds))), float(np.nanmean(stable)), int(len(folds))


def run_feature_research(features: pd.DataFrame, targets: pd.DataFrame, metadata: pd.DataFrame) -> dict[str, pd.DataFrame]:
    implemented = metadata[metadata.availability == "implemented"].feature.astype(str).tolist() if not metadata.empty else list(features.columns)
    rows = []
    calibration_rows = []
    for feature in implemented:
        for target, description in TARGET_SPECS:
            dev_feature = features[feature].loc[DEVELOPMENT_START:DEVELOPMENT_END]
            dev_target = targets[target].loc[DEVELOPMENT_START:DEVELOPMENT_END]
            holdout_feature = features[feature].loc[HOLDOUT_START:HOLDOUT_END]
            holdout_target = targets[target].loc[HOLDOUT_START:HOLDOUT_END]
            dev_auc, dev_directed_auc, direction = _auc(dev_feature, dev_target)
            holdout_auc, holdout_directed_auc, _ = _auc(holdout_feature, holdout_target)
            ic = _spearman_ic(dev_feature, dev_target)
            holdout_ic = _spearman_ic(holdout_feature, holdout_target)
            nw_t, p_value = _newey_west_tstat(dev_feature, dev_target)
            median_fold_auc, positive_fold_fraction, fold_count = _cpcv_feature_stability(dev_feature, dev_target, direction)
            rows.append({
                "feature": feature,
                "target": target,
                "target_description": description,
                "development_observations": int(pd.concat([dev_feature, dev_target], axis=1).dropna().shape[0]),
                "development_auc": dev_auc,
                "development_directed_auc": dev_directed_auc,
                "auc_direction": direction,
                "development_ic": ic,
                "newey_west_t_stat": nw_t,
                "p_value": p_value,
                "median_cpcv_directed_auc": median_fold_auc,
                "positive_cpcv_fold_fraction": positive_fold_fraction,
                "cpcv_fold_count": fold_count,
                "holdout_auc_diagnostic": holdout_auc,
                "holdout_directed_auc_diagnostic": holdout_directed_auc,
                "holdout_ic_diagnostic": holdout_ic,
                "holdout_sign_consistent_diagnostic": bool(np.sign(ic) == np.sign(holdout_ic)) if np.isfinite(ic) and np.isfinite(holdout_ic) else False,
            })
            data = pd.concat([dev_feature.rename("feature"), dev_target.rename("target")], axis=1).dropna()
            if len(data) >= 30 and data.feature.nunique() >= 3:
                ranked = data.feature.rank(method="first")
                bins = pd.qcut(ranked, q=min(5, len(data)), duplicates="drop")
                for number, (_, group) in enumerate(data.groupby(bins, observed=False), start=1):
                    calibration_rows.append({
                        "feature": feature,
                        "target": target,
                        "split": "development",
                        "bin": number,
                        "observations": int(len(group)),
                        "mean_feature": float(group.feature.mean()),
                        "event_rate": float(group.target.mean()),
                    })
    research = pd.DataFrame(rows)
    tiers = classify_new_data_features(research, metadata)
    corr = features[implemented].loc[DEVELOPMENT_START:DEVELOPMENT_END].corr(method="spearman").stack().reset_index()
    corr.columns = ["feature_1", "feature_2", "spearman_correlation"]
    corr = corr[corr.feature_1 < corr.feature_2].sort_values("spearman_correlation", key=lambda s: s.abs(), ascending=False)
    return {
        "feature_research": research,
        "feature_tiers": tiers,
        "calibration": pd.DataFrame(calibration_rows),
        "feature_correlation": corr,
    }


def classify_new_data_features(research: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    rows = []
    implemented = set(metadata[metadata.availability == "implemented"].feature.astype(str)) if not metadata.empty else set()
    for feature in metadata.feature.astype(str).unique() if not metadata.empty else research.feature.astype(str).unique():
        subset = research[research.feature == feature].copy()
        if feature not in implemented or subset.empty:
            tier = "New Data Tier 3"
            reason = "Unavailable source or no usable feature observations."
            best = {}
        else:
            subset["score"] = (
                subset["development_directed_auc"].fillna(0.5)
                + subset["development_ic"].abs().fillna(0.0)
                + 0.10 * subset["positive_cpcv_fold_fraction"].fillna(0.0)
                - subset["p_value"].fillna(1.0) * 0.05
            )
            best_row = subset.sort_values("score", ascending=False).iloc[0]
            best = best_row.to_dict()
            if (
                best_row["development_observations"] >= 100
                and best_row["development_directed_auc"] >= 0.60
                and abs(best_row["development_ic"]) >= 0.08
                and best_row["positive_cpcv_fold_fraction"] >= 0.60
                and best_row["p_value"] <= 0.10
            ):
                tier = "New Data Tier 1"
                reason = "Development evidence meets AUC, IC, Newey-West, and CPCV stability thresholds."
            elif (
                best_row["development_observations"] >= 80
                and (best_row["development_directed_auc"] >= 0.55 or abs(best_row["development_ic"]) >= 0.05)
                and best_row["positive_cpcv_fold_fraction"] >= 0.50
            ):
                tier = "New Data Tier 2"
                reason = "Promising but weaker or less statistically stable development evidence."
            else:
                tier = "New Data Tier 3"
                reason = "Weak, unstable, redundant, or unavailable development evidence."
        rows.append({
            "feature": feature,
            "new_data_tier": tier,
            "reason": reason,
            "best_target": best.get("target", ""),
            "development_directed_auc": best.get("development_directed_auc", np.nan),
            "development_ic": best.get("development_ic", np.nan),
            "newey_west_t_stat": best.get("newey_west_t_stat", np.nan),
            "p_value": best.get("p_value", np.nan),
            "positive_cpcv_fold_fraction": best.get("positive_cpcv_fold_fraction", np.nan),
            "holdout_directed_auc_diagnostic": best.get("holdout_directed_auc_diagnostic", np.nan),
            "holdout_sign_consistent_diagnostic": best.get("holdout_sign_consistent_diagnostic", False),
        })
    return pd.DataFrame(rows)


def model_specs() -> list[ModelSpec]:
    specs = [
        ModelSpec("logistic_regression", "Logistic regression", lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500, class_weight="balanced", random_state=41))),
        ModelSpec(
            "elastic_net_logistic",
            "Elastic Net logistic regression",
            lambda: make_pipeline(
                StandardScaler(),
                LogisticRegression(solver="saga", penalty="elasticnet", l1_ratio=0.40, C=0.50, max_iter=6000, class_weight="balanced", random_state=41),
            ),
        ),
        ModelSpec("random_forest", "Random forest", lambda: RandomForestClassifier(n_estimators=160, max_depth=4, min_samples_leaf=12, class_weight="balanced", random_state=41, n_jobs=-1)),
        ModelSpec("gradient_boosting", "Gradient boosting", lambda: GradientBoostingClassifier(n_estimators=120, max_depth=2, learning_rate=0.04, min_samples_leaf=10, random_state=41)),
    ]
    if importlib.util.find_spec("xgboost") is not None:
        def xgb_factory() -> Any:
            from xgboost import XGBClassifier

            return XGBClassifier(n_estimators=120, max_depth=2, learning_rate=0.04, subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", random_state=41)

        specs.append(ModelSpec("xgboost", "XGBoost", xgb_factory))
    return specs


def _cpcv_oof_probabilities(x_dev: pd.DataFrame, y_dev: pd.Series, spec: ModelSpec) -> pd.Series:
    sums = pd.Series(0.0, index=x_dev.index)
    counts = pd.Series(0.0, index=x_dev.index)
    splits = combinatorial_purged_splits(len(x_dev), n_groups=6, n_test_groups=2, label_horizon=4, embargo=1)
    for split in splits:
        train_index = x_dev.index[list(split.train_indices)]
        test_index = x_dev.index[list(split.test_indices)]
        y_train = y_dev.loc[train_index]
        if y_train.nunique() < 2:
            prob = pd.Series(float(y_train.mean()), index=test_index)
        else:
            model = spec.factory()
            model.fit(x_dev.loc[train_index], y_train)
            prob = pd.Series(_positive_probability(model, x_dev.loc[test_index]), index=test_index)
        sums.loc[test_index] += prob
        counts.loc[test_index] += 1.0
    return (sums / counts.replace(0, np.nan)).fillna(float(y_dev.mean()))


def _fit_holdout_probability(x_dev: pd.DataFrame, y_dev: pd.Series, x_holdout: pd.DataFrame, spec: ModelSpec) -> tuple[pd.Series, Any | None]:
    if y_dev.nunique() < 2 or x_holdout.empty:
        return pd.Series(float(y_dev.mean()) if len(y_dev) else 0.0, index=x_holdout.index), None
    model = spec.factory()
    model.fit(x_dev, y_dev)
    return pd.Series(_positive_probability(model, x_holdout), index=x_holdout.index), model


def _classification_metrics(y: pd.Series, probability: pd.Series, threshold: float, split: str, config: str, target: str, model: str) -> dict[str, Any]:
    data = pd.concat([y.rename("y"), probability.rename("probability")], axis=1).dropna()
    if data.empty:
        return {"config": config, "target": target, "model": model, "split": split}
    y_true = data.y.astype(int)
    prob = data.probability.clip(0.0, 1.0)
    pred = (prob >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, pred, average="binary", zero_division=0)
    auc = roc_auc_score(y_true, prob) if y_true.nunique() == 2 else np.nan
    return {
        "config": config,
        "target": target,
        "model": model,
        "split": split,
        "threshold": threshold,
        "observations": int(len(y_true)),
        "positive_events": int(y_true.sum()),
        "auc": float(auc) if np.isfinite(auc) else np.nan,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "brier_score": float(brier_score_loss(y_true, prob)),
    }


def fit_new_data_models(features: pd.DataFrame, targets: pd.DataFrame, specs: list[ModelSpec] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, PredictionBundle]]:
    specs = specs or model_specs()
    metrics = []
    importance = []
    bundles: dict[str, PredictionBundle] = {}
    dev_mask = (features.index >= DEVELOPMENT_START) & (features.index <= DEVELOPMENT_END)
    holdout_mask = (features.index >= HOLDOUT_START) & (features.index <= HOLDOUT_END)
    descriptions = dict(TARGET_SPECS)
    for target in ("target_c_btc_eth_50_50_30d_upside", "target_d_eth_beats_btc_30d", "target_e_top20_leadership"):
        valid_dev = targets[target].loc[dev_mask].dropna().index
        valid_holdout = targets[target].loc[holdout_mask].dropna().index
        x_dev = features.loc[valid_dev]
        y_dev = targets.loc[valid_dev, target].astype(int)
        x_holdout = features.loc[valid_holdout]
        y_holdout = targets.loc[valid_holdout, target].astype(int)
        for spec in specs:
            config = f"{target}__{spec.name}"
            dev_prob = _cpcv_oof_probabilities(x_dev, y_dev, spec)
            threshold = _threshold_from_dev(dev_prob, y_dev)
            holdout_prob, model = _fit_holdout_probability(x_dev, y_dev, x_holdout, spec)
            full = pd.Series(np.nan, index=features.index)
            full.loc[dev_prob.index] = dev_prob
            full.loc[holdout_prob.index] = holdout_prob
            metrics.append(_classification_metrics(y_dev, dev_prob, threshold, "development_cpcv", config, target, spec.name))
            metrics.append(_classification_metrics(y_holdout, holdout_prob, threshold, "holdout", config, target, spec.name))
            fi = _feature_importance(model, spec, list(features.columns), config)
            fi["target"] = target
            importance.append(fi)
            bundles[config] = PredictionBundle(
                config,
                target,
                descriptions[target],
                spec.name,
                threshold,
                full.ffill().fillna(float(dev_prob.mean()) if len(dev_prob) else 0.0),
                dev_prob,
                holdout_prob,
                fi,
            )
    return pd.DataFrame(metrics), pd.concat(importance, ignore_index=True) if importance else pd.DataFrame(), bundles


def _predeclared_candidates(bundles: dict[str, PredictionBundle], top20_allowed: bool) -> list[OverlayCandidate]:
    by_target: dict[str, list[PredictionBundle]] = {}
    for bundle in bundles.values():
        by_target.setdefault(bundle.target, []).append(bundle)
    candidates: list[OverlayCandidate] = []
    for expansion in by_target.get("target_c_btc_eth_50_50_30d_upside", []):
        for multiplier in (0.5, 1.0, 1.5, 2.0):
            candidates.append(OverlayCandidate(
                f"balanced_{expansion.model_name}_m{str(multiplier).replace('.', '_')}",
                "balanced_btc_eth",
                expansion.config_name,
                None,
                None,
                multiplier,
                expansion.threshold,
                "New-data expansion probability exposure multiplier over frozen BTC/ETH allocation.",
            ))
            leader_key = f"target_d_eth_beats_btc_30d__{expansion.model_name}"
            leader = leader_key if leader_key in bundles else next(iter(by_target.get("target_d_eth_beats_btc_30d", [expansion]))).config_name
            candidates.append(OverlayCandidate(
                f"dynamic_tilt_{expansion.model_name}_m{str(multiplier).replace('.', '_')}",
                "dynamic_btc_eth_tilt",
                expansion.config_name,
                leader,
                None,
                multiplier,
                expansion.threshold,
                "New-data expansion multiplier with ETH leadership tilt.",
            ))
            if top20_allowed:
                top20_key = f"target_e_top20_leadership__{expansion.model_name}"
                top20 = top20_key if top20_key in bundles else next(iter(by_target.get("target_e_top20_leadership", [expansion]))).config_name
                candidates.append(OverlayCandidate(
                    f"top20_sleeve_{expansion.model_name}_m{str(multiplier).replace('.', '_')}",
                    "top20_sleeve",
                    expansion.config_name,
                    leader,
                    top20,
                    multiplier,
                    expansion.threshold,
                    "New-data expansion multiplier with top-20 sleeve when leadership passes.",
                ))
    return candidates


def _top20_sleeve_weights(dataset: MacroRegimeDataset, date: pd.Timestamp, sleeve: float) -> pd.Series:
    row = pd.Series(0.0, index=dataset.close.columns)
    if date not in dataset.universe_weights.index:
        return row
    active = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
    if len(active) == 0:
        return row
    row.loc[active] = sleeve / len(active)
    return row


def build_new_data_overlay_weights(
    dataset: MacroRegimeDataset,
    base_weights: pd.DataFrame,
    combined_regime: pd.Series,
    candidate: OverlayCandidate,
    bundles: dict[str, PredictionBundle],
) -> tuple[pd.DataFrame, pd.Series]:
    dates = pd.DatetimeIndex(base_weights.index)
    weights = base_weights.copy()
    decisions = pd.Series("frozen_macro_gate", index=dates, dtype=object)
    expansion = bundles[candidate.expansion_model].full_probability.reindex(dates).ffill().fillna(0.0)
    leadership = bundles[candidate.leadership_model].full_probability.reindex(dates).ffill().fillna(0.5) if candidate.leadership_model else pd.Series(0.5, index=dates)
    top20 = bundles[candidate.top20_model].full_probability.reindex(dates).ffill().fillna(0.0) if candidate.top20_model else pd.Series(0.0, index=dates)
    regimes = combined_regime.reindex(dates).ffill().fillna("risk_off")
    for date in dates:
        if str(regimes.loc[date]) != "risk_on":
            continue
        base = base_weights.loc[date].copy()
        base_exposure = float(base.sum())
        if base_exposure <= 0:
            continue
        if float(expansion.loc[date]) < candidate.threshold:
            continue
        target_exposure = min(1.0, max(0.0, base_exposure * candidate.multiplier))
        scaled = base * (target_exposure / base_exposure)
        decisions.loc[date] = "new_data_expansion_high"
        if candidate.allocation_type == "dynamic_btc_eth_tilt" and candidate.leadership_model:
            total = float(scaled.sum())
            if {"BTC", "ETH"}.issubset(scaled.index) and total > 0:
                if float(leadership.loc[date]) >= bundles[candidate.leadership_model].threshold:
                    scaled.loc["BTC"] = total * 0.30
                    scaled.loc["ETH"] = total * 0.70
                    decisions.loc[date] += "_eth_tilt"
        elif candidate.allocation_type == "top20_sleeve" and candidate.top20_model:
            if float(top20.loc[date]) >= bundles[candidate.top20_model].threshold:
                sleeve = min(0.40, target_exposure)
                core_exposure = max(0.0, target_exposure - sleeve)
                core = base * (core_exposure / base_exposure)
                scaled = core + _top20_sleeve_weights(dataset, date, sleeve).reindex(core.index).fillna(0.0)
                decisions.loc[date] += "_top20_sleeve"
        weights.loc[date] = scaled
        if float(weights.loc[date].sum()) > 1.0:
            weights.loc[date] /= float(weights.loc[date].sum())
    return weights, decisions


def _fold_sharpe(weekly: pd.Series, indices: tuple[int, ...]) -> float:
    subset = weekly.iloc[list(indices)].dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def _select_overlay_cpcv(candidates: list[OverlayCandidate], results_25bps: dict[str, PortfolioResult]) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows = []
    fold_rows = []
    weekly_returns = {}
    for candidate in candidates:
        weekly = _weekly_return(results_25bps[candidate.name].returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        weekly_returns[candidate.name] = weekly
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_values = []
        for number, split in enumerate(splits):
            sharpe = _fold_sharpe(weekly, split.test_indices)
            fold_values.append(sharpe)
            fold_rows.append({"candidate": candidate.name, "allocation_type": candidate.allocation_type, "fold": number, "test_groups": ",".join(str(g) for g in split.test_groups), "fold_sharpe": sharpe})
        dev = period_metrics(results_25bps[candidate.name], DEVELOPMENT_START, DEVELOPMENT_END)
        rows.append({
            "candidate": candidate.name,
            "allocation_type": candidate.allocation_type,
            "expansion_model": candidate.expansion_model,
            "leadership_model": candidate.leadership_model,
            "top20_model": candidate.top20_model,
            "multiplier": candidate.multiplier,
            "threshold": candidate.threshold,
            "median_fold_sharpe": float(np.nanmedian(fold_values)),
            "worst_fold_sharpe": float(np.nanmin(fold_values)),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_values) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
        })
    selection = pd.DataFrame(rows)
    selection["selection_score"] = (
        selection["median_fold_sharpe"]
        + 0.25 * selection["worst_fold_sharpe"]
        + 0.20 * selection["positive_fold_fraction"]
        - np.maximum(0.0, selection["development_turnover"] - 12.0) * 0.05
    )
    selection = selection.sort_values(["selection_score", "median_fold_sharpe", "worst_fold_sharpe", "development_turnover"], ascending=[False, False, False, True])
    pbo = probability_backtest_overfitting(pd.concat(weekly_returns, axis=1).sort_index(), blocks=8) if len(weekly_returns) > 1 else np.nan
    return selection, pd.DataFrame(fold_rows), str(selection.iloc[0].candidate), pbo


def _run_strategy_if_allowed(
    dataset: MacroRegimeDataset,
    model_features: pd.DataFrame,
    targets: pd.DataFrame,
    tier1_features: list[str],
    specs: list[ModelSpec] | None,
) -> dict[str, Any]:
    if len(tier1_features) < 3:
        return {
            "strategy_ran": False,
            "skip_reason": f"Strategy gate failed: {len(tier1_features)} New Data Tier-1 feature(s) found; at least 3 required.",
            "prediction_metrics": pd.DataFrame(),
            "feature_importance": pd.DataFrame(),
            "overlay_metrics": pd.DataFrame(),
            "benchmarks": pd.DataFrame(),
            "selection": pd.DataFrame(),
            "cpcv_folds": pd.DataFrame(),
            "winner": "",
            "pbo": np.nan,
            "deflated_sharpe_probability": np.nan,
            "passes_acceptance": False,
        }
    x = model_features[tier1_features]
    prediction_metrics, feature_importance, bundles = fit_new_data_models(x, targets, specs)
    dev_metrics = prediction_metrics[prediction_metrics.split == "development_cpcv"].copy()
    top20_best = dev_metrics[dev_metrics.target == "target_e_top20_leadership"].sort_values(["auc", "f1"], ascending=False).head(1)
    top20_allowed = bool(not top20_best.empty and top20_best.iloc[0]["auc"] >= 0.55 and top20_best.iloc[0]["f1"] >= 0.05)
    candidates = _predeclared_candidates(bundles, top20_allowed)
    base_weights, macro_regime, crypto_regime, combined_regime = build_candidate_weights(dataset, FIXED_SELECTED)
    overlay_results: dict[str, dict[int, PortfolioResult]] = {}
    overlay_decisions: dict[str, pd.Series] = {}
    for candidate in candidates:
        weights, decisions = build_new_data_overlay_weights(dataset, base_weights, combined_regime, candidate, bundles)
        overlay_decisions[candidate.name] = decisions
        overlay_results[candidate.name] = {
            cost: backtest_weights(dataset, weights, macro_regime, crypto_regime, combined_regime, cost_bps=cost, turnover_cap=FIXED_SELECTED.turnover_cap)
            for cost in COST_LEVELS
        }
    results_25 = {name: by_cost[25] for name, by_cost in overlay_results.items()}
    selection, cpcv_folds, winner, pbo = _select_overlay_cpcv(candidates, results_25)
    overlay_metric_rows = []
    for candidate in candidates:
        for cost, result in overlay_results[candidate.name].items():
            for row in _rows_for_result(candidate.name, candidate.description, candidate.allocation_type, cost, result, selected=candidate.name == winner):
                row.update({"multiplier": candidate.multiplier, "expansion_model": candidate.expansion_model, "leadership_model": candidate.leadership_model, "top20_model": candidate.top20_model})
                overlay_metric_rows.append(row)
    overlay_metrics = pd.DataFrame(overlay_metric_rows)
    benchmarks = previous_benchmark_rows(dataset, base_weights, (macro_regime, crypto_regime, combined_regime))
    frozen_25 = backtest_weights(dataset, base_weights, macro_regime, crypto_regime, combined_regime, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
    frozen_holdout = period_metrics(frozen_25, HOLDOUT_START, HOLDOUT_END)
    winner_holdout = period_metrics(overlay_results[winner][25], HOLDOUT_START, HOLDOUT_END)
    winner_50 = period_metrics(overlay_results[winner][50], HOLDOUT_START, HOLDOUT_END)
    pbo_ref = 0.70  # prior Expansion Tier-1 overlay report; used as a materiality reference, not a selection criterion.
    dsr = deflated_sharpe_probability(overlay_results[winner][25].returns.loc[HOLDOUT_START:HOLDOUT_END], tested_configurations=len(candidates) + len(prediction_metrics[prediction_metrics.split == "development_cpcv"]))
    passes = bool(
        winner_holdout["Sharpe"] > frozen_holdout["Sharpe"] + 0.10
        and winner_holdout["CAGR"] >= frozen_holdout["CAGR"] * 0.90
        and winner_holdout["Maximum Drawdown"] >= frozen_holdout["Maximum Drawdown"] - 0.05
        and winner_50["CAGR"] > 0
        and winner_holdout["Annual Turnover"] <= 12
        and winner_holdout["Exposure"] >= 0.15
        and (not np.isfinite(pbo) or pbo <= pbo_ref + 0.05)
        and dsr >= 0.50
    )
    return {
        "strategy_ran": True,
        "skip_reason": "",
        "prediction_metrics": prediction_metrics,
        "feature_importance": feature_importance,
        "overlay_metrics": overlay_metrics,
        "benchmarks": benchmarks,
        "selection": selection,
        "cpcv_folds": cpcv_folds,
        "winner": winner,
        "pbo": pbo,
        "deflated_sharpe_probability": dsr,
        "passes_acceptance": passes,
        "frozen_holdout": frozen_holdout,
        "winner_holdout": winner_holdout,
        "winner_holdout_50bps": winner_50,
        "top20_allowed": top20_allowed,
    }


def run_new_data_expansion_strategy(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
    specs: list[ModelSpec] | None = None,
    processed_dir: str | Path = OUTPUT_DATA_DIR,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=20)
    inventory, frames = discover_new_data_sources(processed_dir)
    features_daily, feature_metadata = build_new_data_features(frames, dataset.close.index)
    dates = _rebalance_dates(dataset.close.index, 7)
    features = features_daily.reindex(dates).ffill().fillna(0.0)
    targets = build_new_data_targets(dataset, dates)
    research_parts = run_feature_research(features, targets, feature_metadata)
    tier1_features = research_parts["feature_tiers"].loc[
        research_parts["feature_tiers"].new_data_tier.eq("New Data Tier 1"), "feature"
    ].astype(str).tolist()
    strategy = _run_strategy_if_allowed(dataset, features, targets, tier1_features, specs)
    if strategy["strategy_ran"]:
        if strategy["passes_acceptance"]:
            conclusion = "New-data features pass the strategy gate and show paper-monitoring evidence of incremental upside information."
        else:
            conclusion = "New-data features passed the feature gate, but the overlay did not pass economic/statistical acceptance rules."
    else:
        conclusion = "New data does not yet provide enough independently validated Tier-1 upside features to justify a strategy test."
    return {
        "dataset": dataset,
        "inventory": inventory,
        "feature_metadata": feature_metadata,
        "features": features,
        "targets": targets,
        "target_diagnostics": target_diagnostics(targets),
        **research_parts,
        **strategy,
        "tier1_features": tier1_features,
        "final_conclusion": conclusion,
        "protocol": {
            "title": "New-Data Upside Expansion Strategy",
            "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} onward",
            "baseline": BASELINE_NAME,
            "strategy_gate": "Run overlay only if at least 3 New Data Tier-1 features pass development-only feature research.",
        },
    }


def target_diagnostics(targets: pd.DataFrame) -> pd.DataFrame:
    descriptions = dict(TARGET_SPECS)
    rows = []
    for target in targets.columns:
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            y = targets[target].loc[start:end].dropna().astype(int)
            rows.append({
                "target": target,
                "description": descriptions.get(target, target),
                "split": split,
                "observations": int(len(y)),
                "positive_events": int(y.sum()) if len(y) else 0,
                "prevalence": float(y.mean()) if len(y) else np.nan,
            })
    return pd.DataFrame(rows)


def _write_csvs(output: Path, result: dict[str, Any]) -> None:
    for key, filename in (
        ("inventory", "data_inventory.csv"),
        ("feature_metadata", "feature_metadata.csv"),
        ("target_diagnostics", "target_diagnostics.csv"),
        ("feature_research", "feature_research.csv"),
        ("feature_tiers", "feature_tiers.csv"),
        ("calibration", "calibration.csv"),
        ("feature_correlation", "feature_correlation.csv"),
        ("prediction_metrics", "prediction_metrics.csv"),
        ("feature_importance", "model_feature_importance.csv"),
        ("overlay_metrics", "strategy_metrics.csv"),
        ("benchmarks", "benchmark_metrics.csv"),
        ("selection", "strategy_selection.csv"),
        ("cpcv_folds", "strategy_cpcv_folds.csv"),
    ):
        frame = result.get(key)
        if isinstance(frame, pd.DataFrame):
            frame.to_csv(output / filename, index=False)


def write_new_data_expansion_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_csvs(output, result)

    inventory = result["inventory"]
    tiers = result["feature_tiers"]
    tier_counts = tiers.new_data_tier.value_counts().rename_axis("tier").reset_index(name="count") if not tiers.empty else pd.DataFrame()
    implemented = result["feature_metadata"][result["feature_metadata"].availability.eq("implemented")] if not result["feature_metadata"].empty else pd.DataFrame()

    (output / "data_inventory.md").write_text(f"""# Data inventory

The module checked WRDS inventory artifacts and small public sources for ETF
flows, on-chain activity, and options-implied indicators. No unavailable source
was fabricated or proxied into a model.

{_table(inventory, [('source_family', 'Family'), ('source', 'Source'), ('status', 'Status'), ('start_date', 'Start'), ('end_date', 'End'), ('observations', 'Obs'), ('frequency', 'Frequency'), ('point_in_time_usable', 'PIT usable'), ('notes', 'Notes')], limit=80)}
""", encoding="utf-8")

    (output / "feature_engineering.md").write_text(f"""# Feature engineering

Only lagged features from actually available small public datasets were
implemented. Requested but unavailable ETF-flow, exchange-flow, MVRV,
realized-cap, holder-behaviour, and options-surface features are recorded but
not used.

## Implemented features

{_table(implemented, [('feature', 'Feature'), ('family', 'Family'), ('formula', 'Formula'), ('source', 'Source'), ('lag', 'Lag'), ('economic_rationale', 'Rationale')], limit=80)}

## Full requested feature inventory

{_table(result['feature_metadata'], [('feature', 'Feature'), ('family', 'Family'), ('availability', 'Availability'), ('formula', 'Formula'), ('source', 'Source')], limit=120)}
""", encoding="utf-8")

    (output / "feature_research.md").write_text(f"""# Feature research

Feature validation uses development data only for classification. Holdout
columns are diagnostics only and were not used for feature selection.

## Target diagnostics

{_table(result['target_diagnostics'], [('target', 'Target'), ('split', 'Split'), ('observations', 'Obs'), ('positive_events', 'Positive'), ('prevalence', 'Prevalence')], {'prevalence'}, limit=20)}

## Feature-target evidence

{_table(result['feature_research'], [('feature', 'Feature'), ('target', 'Target'), ('development_directed_auc', 'Dev directed AUC'), ('development_ic', 'Dev IC'), ('newey_west_t_stat', 'NW t'), ('p_value', 'p-value'), ('positive_cpcv_fold_fraction', 'Positive CPCV folds'), ('holdout_directed_auc_diagnostic', 'Holdout directed AUC')], {'positive_cpcv_fold_fraction'}, limit=120)}
""", encoding="utf-8")

    (output / "feature_tiers.md").write_text(f"""# Feature tiers

Strategy gate: at least **3 New Data Tier-1** features are required before any
overlay test is allowed.

## Tier counts

{_table(tier_counts, [('tier', 'Tier'), ('count', 'Count')])}

## Feature classifications

{_table(tiers, [('feature', 'Feature'), ('new_data_tier', 'Tier'), ('best_target', 'Best target'), ('development_directed_auc', 'Dev directed AUC'), ('development_ic', 'Dev IC'), ('newey_west_t_stat', 'NW t'), ('p_value', 'p-value'), ('positive_cpcv_fold_fraction', 'Positive CPCV folds'), ('reason', 'Reason')], {'positive_cpcv_fold_fraction'}, limit=120)}
""", encoding="utf-8")

    if result["strategy_ran"]:
        selected = result["winner"]
        selected_metrics = result["overlay_metrics"][(result["overlay_metrics"].name == selected)]
        holdout_selected = selected_metrics[selected_metrics.split.eq("holdout")]
        strategy_text = f"""# Strategy results

The feature gate passed, so the New-Data Expansion Overlay was evaluated using
development-only CPCV selection.

Selected overlay: **{selected}**

{_table(holdout_selected, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}
"""
        benchmark_text = f"""# Benchmark comparison

{_table(pd.concat([result['benchmarks'], selected_metrics], ignore_index=True, sort=False), [('name', 'Name'), ('benchmark_group', 'Group'), ('split', 'Split'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'}, limit=120)}
"""
        stats_text = f"""# Statistical validation

- Strategy ran: Yes
- PBO: {_fmt(result['pbo'], True)}
- Deflated Sharpe probability: {_fmt(result['deflated_sharpe_probability'], True)}
- Acceptance passed: {_fmt(result['passes_acceptance'])}
- Top-20 sleeve allowed by development criteria: {_fmt(result.get('top20_allowed', False))}

{_table(result['selection'], [('candidate', 'Candidate'), ('allocation_type', 'Allocation'), ('multiplier', 'Multiplier'), ('selection_score', 'Selection score'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold Sharpe'), ('positive_fold_fraction', 'Positive folds'), ('development_turnover', 'Dev turnover')], {'positive_fold_fraction'}, limit=80)}
"""
    else:
        strategy_text = f"""# Strategy results

Strategy test was not run.

Reason: **{result['skip_reason']}**

This follows the predeclared rule: no strategy unless at least three New Data
Tier-1 upside features are found using development-only validation.
"""
        benchmark_text = """# Benchmark comparison

Benchmark comparison was not run because the New Data Tier-1 feature gate failed.
The frozen strategy remains the active benchmark.
"""
        stats_text = f"""# Statistical validation

- Strategy ran: No
- Reason: {result['skip_reason']}
- PBO: N/A
- Deflated Sharpe probability: N/A

Feature classification used development data only. Holdout diagnostics are
reported for transparency but did not affect the tier labels.
"""
    (output / "strategy_results.md").write_text(strategy_text, encoding="utf-8")
    (output / "benchmark_comparison.md").write_text(benchmark_text, encoding="utf-8")
    (output / "statistical_validation.md").write_text(stats_text, encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

Final conclusion: **{result['final_conclusion']}**

The new data source does not currently justify modifying or replacing
**{BASELINE_NAME}** unless the strategy gate and acceptance rules pass. In this
run, available public data was too limited: ETF flows were inaccessible, full
on-chain valuation/holder/exchange-flow metrics were unavailable, and public
Deribit options data did not provide sufficient history for the locked
2019-2026 protocol.

Recommendation: keep **{BASELINE_NAME}** frozen. Treat the new-data work as a
data-acquisition roadmap, not a paper-trading improvement, unless licensed
ETF-flow/on-chain/options history is added and passes the same development-only
feature gate.
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "tier1_features": result["tier1_features"],
        "strategy_ran": result["strategy_ran"],
        "skip_reason": result["skip_reason"],
        "winner": result["winner"],
        "pbo": _json_safe(result["pbo"]),
        "deflated_sharpe_probability": _json_safe(result["deflated_sharpe_probability"]),
        "passes_acceptance": result["passes_acceptance"],
        "final_conclusion": result["final_conclusion"],
        "inventory": _json_safe(result["inventory"]),
        "feature_tiers": _json_safe(result["feature_tiers"]),
        "feature_research": _json_safe(result["feature_research"]),
        "strategy_metrics": _json_safe(result["overlay_metrics"]),
        "benchmarks": _json_safe(result["benchmarks"]),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_new_data_expansion_strategy(output_dir: str | Path = "reports/new_data_expansion_strategy") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_new_data_expansion_strategy(panel, macro, public_data, probability)
    write_new_data_expansion_reports(output_dir, result)
    return result


__all__ = [
    "run_new_data_expansion_strategy",
    "write_new_data_expansion_reports",
    "run_default_new_data_expansion_strategy",
    "build_new_data_features",
    "run_feature_research",
]
