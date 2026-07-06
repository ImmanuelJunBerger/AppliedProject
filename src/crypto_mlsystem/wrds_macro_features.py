"""Targeted WRDS macro-regime feature dataset.

This module deliberately stops at data/feature research.  It downloads only
small daily WRDS time series needed for crypto regime research, creates lagged
macro features, joins them to the existing weekly crypto panel, and runs
predictive feature diagnostics.  It does not backtest strategies or fit trading
models.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .data import STABLE_OR_WRAPPED
from .feature_research import (
    HORIZONS,
    REGIMES,
    classify_features,
    correlation_analysis,
    information_coefficient_report,
    regime_stability,
)
from .volatility_expansion import HOLDOUT_END, HOLDOUT_START, point_in_time_liquid_universe
from .wrds_inventory import (
    WRDS_PASSWORD_ENV,
    WRDS_USERNAME_ENV,
    _connect_with_env,
    _quote_identifier,
    _safe_exception,
    credential_status,
    merged_environment,
)


DEFAULT_START = "2019-01-01"
DEFAULT_END = "2026-06-22"


@dataclass(frozen=True)
class WRDSSeriesSpec:
    source_name: str
    library: str
    table: str
    date_column: str
    columns: dict[str, str]
    frequency: str
    description: str


@dataclass(frozen=True)
class MacroFeatureResearchResult:
    macro_daily: pd.DataFrame
    macro_features_daily: pd.DataFrame
    weekly_panel: pd.DataFrame
    metadata: pd.DataFrame
    coverage: pd.DataFrame
    ic_report: pd.DataFrame
    quantile_report: pd.DataFrame
    stability_report: pd.DataFrame
    correlation_report: pd.DataFrame
    tiers: pd.DataFrame


SERIES_SPECS = (
    WRDSSeriesSpec(
        source_name="crsp_sp500_index",
        library="crsp_q_indexes",
        table="dsp500_v2",
        date_column="caldt",
        columns={
            "sprtrn": "sp500_return",
            "spindx": "sp500_index",
            "vwretd": "sp500_value_weighted_return",
            "ewretd": "sp500_equal_weighted_return",
            "totval": "sp500_total_value",
            "totcnt": "sp500_member_count",
        },
        frequency="daily",
        description="CRSP S&P 500 index return/level proxy for broad equity risk appetite.",
    ),
    WRDSSeriesSpec(
        source_name="crsp_broad_market_index",
        library="crsp",
        table="dsi",
        date_column="date",
        columns={
            "vwretd": "crsp_market_value_weighted_return",
            "ewretd": "crsp_market_equal_weighted_return",
            "sprtrn": "crsp_sp500_return_legacy",
            "spindx": "crsp_sp500_index_legacy",
            "totval": "crsp_total_market_value",
            "totcnt": "crsp_total_count",
        },
        frequency="daily",
        description="CRSP broad-market daily index table. In this account snapshot it ends before the 2025 holdout.",
    ),
    WRDSSeriesSpec(
        source_name="cboe_volatility_indices",
        library="cboe",
        table="cboe",
        date_column="date",
        columns={
            "vix": "vix",
            "vixo": "vix_open",
            "vixh": "vix_high",
            "vixl": "vix_low",
            "vxo": "vxo",
            "vxn": "vxn",
            "vxd": "vxd",
        },
        frequency="daily",
        description="CBOE daily volatility indices. VVIX was searched for but not found in accessible CBOE metadata.",
    ),
    WRDSSeriesSpec(
        source_name="frb_rates_daily",
        library="frb",
        table="rates_daily",
        date_column="date",
        columns={
            "dgs10": "treasury_10y",
            "dgs2": "treasury_2y",
            "dgs3mo": "treasury_3m",
            "dff": "fed_funds_effective",
            "sofr": "sofr",
            "dfii10": "tips_10y_real_yield",
            "t10y2y": "yield_curve_10y2y",
            "t10y3m": "yield_curve_10y3m",
            "t10yie": "breakeven_10y",
            "bamlh0a0hym2": "high_yield_spread",
            "bamlh0a0hym2ey": "high_yield_effective_yield",
            "bamlc0a0cmey": "corp_bond_effective_yield",
        },
        frequency="daily",
        description="Federal Reserve daily rates, curve, real yield, inflation expectation, and credit-spread proxies.",
    ),
    WRDSSeriesSpec(
        source_name="frb_fx_daily",
        library="frb",
        table="fx_daily",
        date_column="date",
        columns={
            "dtwexbgs": "trade_weighted_usd_broad",
            "dtwexafegs": "trade_weighted_usd_advanced_foreign",
            "dtwexemegs": "trade_weighted_usd_emerging_market",
            "dexuseu": "usd_per_eur",
            "dexjpus": "jpy_per_usd",
            "dexusuk": "usd_per_gbp",
        },
        frequency="daily",
        description="Federal Reserve daily FX and trade-weighted dollar proxies.",
    ),
)


def _empty_coverage(source_name: str, library: str, table: str, status: str, note: str) -> dict[str, Any]:
    return {
        "source_name": source_name,
        "library": library,
        "table": table,
        "status": status,
        "start_date": "",
        "end_date": "",
        "rows": 0,
        "columns": "",
        "frequency": "",
        "note": note,
    }


def _read_spec(connection: Any, spec: WRDSSeriesSpec, start: str, end: str, env: dict[str, str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read one small selected-column WRDS source.

    The connection object is the direct wrapper created by the official wrds
    package in :mod:`wrds_inventory`.
    """
    try:
        import pandas as pd
        import sqlalchemy as sa  # type: ignore

        available = {name.lower(): name for name, _ in connection.list_columns(spec.library, spec.table)}
        date_column = available.get(spec.date_column.lower())
        selected = {source: alias for source, alias in spec.columns.items() if source.lower() in available}
        if date_column is None:
            return pd.DataFrame(), _empty_coverage(
                spec.source_name,
                spec.library,
                spec.table,
                "missing_date_column",
                f"Expected date column {spec.date_column!r} was not available.",
            )
        if not selected:
            return pd.DataFrame(), _empty_coverage(
                spec.source_name,
                spec.library,
                spec.table,
                "missing_selected_columns",
                "No requested columns were available.",
            )
        schema = _quote_identifier(spec.library)
        table = _quote_identifier(spec.table)
        date_expr = _quote_identifier(date_column)
        select_cols = [f"{date_expr} AS date"]
        for source, alias in selected.items():
            select_cols.append(f"{_quote_identifier(available[source.lower()])} AS {_quote_identifier(alias)}")
        query = sa.text(
            f"""
            SELECT {", ".join(select_cols)}
            FROM {schema}.{table}
            WHERE {date_expr} BETWEEN :start_date AND :end_date
            ORDER BY {date_expr}
            """
        )
        frame = pd.read_sql(query, connection._connection, params={"start_date": start, "end_date": end})
        if frame.empty:
            return frame, _empty_coverage(
                spec.source_name,
                spec.library,
                spec.table,
                "empty",
                "Query succeeded but returned no rows for the requested date range.",
            )
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.drop_duplicates("date").sort_values("date")
        for column in frame.columns:
            if column != "date":
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame, {
            "source_name": spec.source_name,
            "library": spec.library,
            "table": spec.table,
            "status": "downloaded",
            "start_date": str(frame.date.min().date()),
            "end_date": str(frame.date.max().date()),
            "rows": int(len(frame)),
            "columns": ", ".join([c for c in frame.columns if c != "date"]),
            "frequency": spec.frequency,
            "note": spec.description,
        }
    except Exception as exc:  # pragma: no cover - live WRDS dependent
        return pd.DataFrame(), _empty_coverage(
            spec.source_name,
            spec.library,
            spec.table,
            "error",
            _safe_exception(exc, env),
        )


def download_wrds_macro_series(
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    env_file: str | Path | None = ".env",
    processed_dir: str | Path = "data/processed/wrds_macro_features",
    env: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download small selected WRDS macro series and save metadata.

    Credentials are read through ``merged_environment`` and never written.
    """
    merged = merged_environment(env=env, env_file=env_file)
    status = credential_status(merged)
    if not status.ready:
        coverage = pd.DataFrame([
            {
                "source_name": "wrds_connection",
                "library": "",
                "table": "",
                "status": "credentials_missing",
                "start_date": "",
                "end_date": "",
                "rows": 0,
                "columns": "",
                "frequency": "",
                "note": f"Missing {WRDS_USERNAME_ENV if not merged.get(WRDS_USERNAME_ENV) else WRDS_PASSWORD_ENV}.",
            }
        ])
        return pd.DataFrame(columns=["date"]), coverage

    frames: list[pd.DataFrame] = []
    coverage_rows: list[dict[str, Any]] = []
    connection = None
    try:
        connection = _connect_with_env(merged)
        for spec in SERIES_SPECS:
            frame, coverage = _read_spec(connection, spec, start, end, merged)
            coverage_rows.append(coverage)
            if not frame.empty:
                frames.append(frame)
    except Exception as exc:  # pragma: no cover - live WRDS dependent
        coverage_rows.append({
            "source_name": "wrds_connection",
            "library": "",
            "table": "",
            "status": "connection_failed",
            "start_date": "",
            "end_date": "",
            "rows": 0,
            "columns": "",
            "frequency": "",
            "note": _safe_exception(exc, merged),
        })
    finally:
        if connection is not None:
            connection.close()

    if frames:
        macro = frames[0]
        for frame in frames[1:]:
            macro = macro.merge(frame, on="date", how="outer")
        macro = macro.sort_values("date").drop_duplicates("date")
    else:
        macro = pd.DataFrame(columns=["date"])
    coverage = pd.DataFrame(coverage_rows)

    processed = Path(processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    macro.to_csv(processed / "wrds_macro_daily.csv", index=False)
    coverage.to_csv(processed / "coverage.csv", index=False)
    return macro, coverage


def _rolling_percentile(series: pd.Series, window: int) -> pd.Series:
    def percentile(values: np.ndarray) -> float:
        current = values[-1]
        history = values[:-1]
        history = history[np.isfinite(history)]
        if not np.isfinite(current) or len(history) < max(20, window // 4):
            return np.nan
        return float((history <= current).mean())

    return series.rolling(window + 1, min_periods=max(21, window // 4)).apply(percentile, raw=True)


def _rolling_zscore(series: pd.Series, window: int = 252) -> pd.Series:
    mean = series.rolling(window, min_periods=max(40, window // 5)).mean().shift(1)
    std = series.rolling(window, min_periods=max(40, window // 5)).std().shift(1)
    return (series - mean) / std.replace(0, np.nan)


def build_lagged_macro_features(
    macro_daily: pd.DataFrame,
    crypto_panel: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create lagged daily macro-regime features aligned to crypto calendar."""
    crypto_dates = pd.to_datetime(crypto_panel["date"])
    if crypto_dates.empty:
        raise ValueError("crypto_panel has no dates")
    full_index = pd.date_range(crypto_dates.min(), crypto_dates.max(), freq="D")

    macro = macro_daily.copy()
    if macro.empty:
        aligned = pd.DataFrame(index=full_index)
    else:
        macro["date"] = pd.to_datetime(macro["date"])
        aligned = macro.drop_duplicates("date").set_index("date").sort_index().reindex(full_index).ffill()
        for column in aligned.columns:
            aligned[column] = pd.to_numeric(aligned[column], errors="coerce")

    raw: dict[str, pd.Series] = {}
    metadata: list[dict[str, str]] = []

    def add(name: str, series: pd.Series, family: str, formula: str, source: str, rationale: str) -> None:
        raw[name] = series.reindex(full_index)
        metadata.append({
            "feature": name,
            "family": family,
            "level": "market",
            "lookback_window": formula,
            "lag": "1 calendar day after feature calculation",
            "source": source,
            "rationale": rationale,
            "formula": formula,
        })

    equity_index = aligned.get("sp500_index", pd.Series(index=full_index, dtype=float)).combine_first(
        aligned.get("crsp_sp500_index_legacy", pd.Series(index=full_index, dtype=float))
    )
    equity_return = aligned.get("sp500_return", equity_index.pct_change(fill_method=None))
    if equity_index.notna().any():
        add("equity_momentum_21d", equity_index.pct_change(21, fill_method=None), "equity_risk", "S&P/CRSP equity index 21d pct_change", "CRSP index", "Equity risk appetite often transmits into crypto beta.")
        add("equity_momentum_63d", equity_index.pct_change(63, fill_method=None), "equity_risk", "S&P/CRSP equity index 63d pct_change", "CRSP index", "Medium-term equity trend as risk-on/risk-off proxy.")
        add("equity_drawdown_252d", equity_index / equity_index.rolling(252, min_periods=60).max() - 1.0, "equity_risk", "Index / trailing 252d high - 1", "CRSP index", "Equity drawdown captures broad risk stress.")
        add("equity_realized_vol_21d", equity_return.rolling(21, min_periods=10).std() * np.sqrt(252), "equity_risk", "21d annualized equity realized volatility", "CRSP index", "Equity volatility is a risk-regime proxy.")

    if "vix" in aligned:
        add("vix_level", aligned["vix"], "volatility_risk", "CBOE VIX close", "CBOE", "High VIX indicates hostile global risk conditions.")
        add("vix_change_5d", aligned["vix"].diff(5), "volatility_risk", "VIX 5d difference", "CBOE", "Rapid volatility increases can precede crypto de-risking.")
        add("vix_change_21d", aligned["vix"].diff(21), "volatility_risk", "VIX 21d difference", "CBOE", "Medium-term volatility trend.")
        add("vix_percentile_252d", _rolling_percentile(aligned["vix"], 252), "volatility_risk", "VIX percentile versus trailing 252d history", "CBOE", "Normalizes volatility level across regimes.")
    for column, feature in (("vxn", "nasdaq_vol_level"), ("vxd", "dow_vol_level")):
        if column in aligned:
            add(feature, aligned[column], "volatility_risk", f"{column.upper()} close", "CBOE", "Equity-index volatility proxy.")

    if "treasury_10y" in aligned:
        add("rates_10y_level", aligned["treasury_10y"], "rates", "10y Treasury yield level", "FRB", "Higher rates can pressure speculative duration-like assets.")
        add("rates_10y_change_21d", aligned["treasury_10y"].diff(21), "rates", "10y Treasury yield 21d difference", "FRB", "Rates shocks can mark hostile macro regimes.")
        add("rates_10y_change_63d", aligned["treasury_10y"].diff(63), "rates", "10y Treasury yield 63d difference", "FRB", "Medium-term rates trend.")
    if "fed_funds_effective" in aligned:
        add("fed_funds_level", aligned["fed_funds_effective"], "rates", "Effective fed funds rate", "FRB", "Policy-rate regime proxy.")
    if "sofr" in aligned:
        add("sofr_level", aligned["sofr"], "rates", "SOFR level", "FRB", "Short-rate/liquidity proxy.")
    if "tips_10y_real_yield" in aligned:
        add("real_yield_10y_level", aligned["tips_10y_real_yield"], "rates", "10y TIPS real yield", "FRB", "Real yields can reduce appetite for speculative assets.")
        add("real_yield_10y_change_21d", aligned["tips_10y_real_yield"].diff(21), "rates", "10y real yield 21d difference", "FRB", "Real-rate shock proxy.")
    slope = aligned.get("yield_curve_10y2y")
    if slope is None and {"treasury_10y", "treasury_2y"}.issubset(aligned.columns):
        slope = aligned["treasury_10y"] - aligned["treasury_2y"]
    if slope is not None:
        add("yield_curve_slope_10y2y", slope, "rates", "10y yield - 2y yield or FRB T10Y2Y", "FRB", "Curve slope captures growth/liquidity regime.")
        add("yield_curve_slope_change_21d", slope.diff(21), "rates", "10y-2y slope 21d difference", "FRB", "Curve-steepening/flattening shock.")
    if "yield_curve_10y3m" in aligned:
        add("yield_curve_slope_10y3m", aligned["yield_curve_10y3m"], "rates", "10y-3m slope", "FRB", "Alternative recession/risk-state proxy.")
    if "high_yield_spread" in aligned:
        add("credit_spread_level", aligned["high_yield_spread"], "credit", "High-yield spread level", "FRB/FRED", "Credit stress proxy.")
        add("credit_spread_change_21d", aligned["high_yield_spread"].diff(21), "credit", "High-yield spread 21d difference", "FRB/FRED", "Credit stress acceleration.")

    usd = aligned.get("trade_weighted_usd_broad")
    if usd is not None and usd.notna().any():
        add("usd_trend_21d", usd.pct_change(21, fill_method=None), "usd", "Trade-weighted USD 21d pct_change", "FRB FX", "USD strength can be hostile to crypto liquidity.")
        add("usd_trend_63d", usd.pct_change(63, fill_method=None), "usd", "Trade-weighted USD 63d pct_change", "FRB FX", "Medium-term dollar trend.")
        add("usd_change_5d", usd.pct_change(5, fill_method=None), "usd", "Trade-weighted USD 5d pct_change", "FRB FX", "Short USD shock proxy.")

    composite_inputs = []
    for name, sign in (
        ("equity_momentum_63d", 1.0),
        ("equity_drawdown_252d", 1.0),
        ("vix_level", -1.0),
        ("vix_change_21d", -1.0),
        ("rates_10y_change_63d", -1.0),
        ("usd_trend_63d", -1.0),
        ("yield_curve_slope_10y2y", 1.0),
        ("credit_spread_level", -1.0),
    ):
        if name in raw:
            composite_inputs.append(sign * _rolling_zscore(raw[name], 252))
    if composite_inputs:
        composite = pd.concat(composite_inputs, axis=1).mean(axis=1)
        add("macro_risk_on_composite", composite, "macro_composite", "Equal-weighted trailing z-scores of equity trend, drawdown, VIX, rates, USD, curve, and credit risk", "WRDS macro blend", "Single predeclared risk-on/risk-off macro summary.")

    features = pd.DataFrame(raw, index=full_index).replace([np.inf, -np.inf], np.nan).shift(1)
    features.index.name = "date"
    features = features.reset_index()
    metadata = pd.DataFrame(metadata).drop_duplicates("feature")
    return features, metadata


def build_weekly_macro_crypto_panel(
    crypto_panel: pd.DataFrame,
    macro_features_daily: pd.DataFrame,
    top_n: int = 20,
    min_history_days: int = 180,
) -> pd.DataFrame:
    """Join lagged macro features to weekly point-in-time crypto observations."""
    clean = crypto_panel.copy().sort_values(["date", "symbol"])
    clean["date"] = pd.to_datetime(clean["date"])
    clean = clean[~clean["symbol"].isin(STABLE_OR_WRAPPED)]
    weights, _ = point_in_time_liquid_universe(clean, top_n=top_n, min_history_days=min_history_days)
    close = clean.pivot(index="date", columns="symbol", values="close").sort_index().reindex_like(weights)
    macro = macro_features_daily.copy()
    macro["date"] = pd.to_datetime(macro["date"])
    macro = macro.drop_duplicates("date").set_index("date").sort_index().reindex(close.index).ffill()
    feature_columns = [column for column in macro.columns if column != "date"]

    weekly_dates = pd.DatetimeIndex(close.resample("W-FRI").last().index).intersection(close.index)
    rows: list[dict[str, Any]] = []
    for date_ in weekly_dates:
        members = weights.columns[weights.loc[date_] > 0]
        if len(members) == 0:
            continue
        macro_values = macro.loc[date_, feature_columns].to_dict() if date_ in macro.index else {}
        for symbol in members:
            if pd.isna(close.at[date_, symbol]):
                continue
            row: dict[str, Any] = {"date": date_, "symbol": symbol}
            for horizon, label in HORIZONS.items():
                future_idx = close.index.searchsorted(date_ + pd.Timedelta(days=horizon))
                if future_idx < len(close.index):
                    future_date = close.index[future_idx]
                    row[f"future_return_{label}"] = close.at[future_date, symbol] / close.at[date_, symbol] - 1
                else:
                    row[f"future_return_{label}"] = np.nan
            row.update(macro_values)
            rows.append(row)
    return pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan)


def macro_time_series_quantile_analysis(frame: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    """Quantile analysis for market-level macro features across weekly dates."""
    sample_windows: dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]] = {
        "full_sample": (None, None),
        "development_pre_2025": (pd.Timestamp("2019-01-01"), HOLDOUT_START - pd.Timedelta(days=1)),
        "holdout_2025_2026": (HOLDOUT_START, HOLDOUT_END),
    }
    sample_windows.update(REGIMES)
    rows: list[dict[str, Any]] = []
    for feature in metadata.feature:
        for horizon, label in HORIZONS.items():
            target = f"future_return_{label}"
            by_date = frame.groupby("date")[[feature, target]].mean().replace([np.inf, -np.inf], np.nan).dropna()
            for sample, (start, end) in sample_windows.items():
                subset = by_date.copy()
                if start is not None:
                    subset = subset[subset.index >= start]
                if end is not None:
                    subset = subset[subset.index <= end]
                for buckets, bucket_name in ((5, "quintile"), (10, "decile")):
                    result = {
                        "feature": feature,
                        "horizon": label,
                        "bucket_type": bucket_name,
                        "sample": sample,
                        "method": "market_time_series",
                        "mean_top_minus_bottom": np.nan,
                        "positive_spread_fraction": np.nan,
                        "mean_monotonicity": np.nan,
                        "n_periods": 0,
                        "n_observations": int(len(subset)),
                    }
                    data = subset[[feature, target]].dropna()
                    if len(data) >= buckets * 3 and data[feature].nunique() >= buckets:
                        try:
                            data = data.copy()
                            data["bucket"] = pd.qcut(data[feature], buckets, labels=False, duplicates="drop")
                            means = data.groupby("bucket")[target].mean()
                            if len(means) >= max(3, buckets // 2):
                                spread = float(means.iloc[-1] - means.iloc[0])
                                monotonicity = float(
                                    pd.Series(means.index.astype(float), index=means.index).rank().corr(means.rank())
                                )
                                result.update({
                                    "mean_top_minus_bottom": spread,
                                    "positive_spread_fraction": float(spread > 0),
                                    "mean_monotonicity": monotonicity,
                                    "n_periods": int(len(means)),
                                })
                        except ValueError:
                            pass
                    rows.append(result)
    return pd.DataFrame(rows)


def run_macro_feature_research(
    crypto_panel: pd.DataFrame,
    macro_daily: pd.DataFrame,
    coverage: pd.DataFrame,
    output_dir: str | Path = "reports/wrds_macro_features",
    processed_dir: str | Path = "data/processed/wrds_macro_features",
    top_n: int = 20,
) -> MacroFeatureResearchResult:
    macro_features_daily, metadata = build_lagged_macro_features(macro_daily, crypto_panel)
    weekly_panel = build_weekly_macro_crypto_panel(crypto_panel, macro_features_daily, top_n=top_n)
    if metadata.empty or weekly_panel.empty:
        ic = pd.DataFrame()
        quantiles = pd.DataFrame()
        stability = pd.DataFrame()
        corr = pd.DataFrame()
        tiers = pd.DataFrame(columns=["feature", "feature_tier", "tier_reason"])
    else:
        ic = information_coefficient_report(weekly_panel, metadata)
        quantiles = macro_time_series_quantile_analysis(weekly_panel, metadata)
        stability_raw = regime_stability(weekly_panel, metadata, ic)
        tiers = classify_features(ic, stability_raw, quantiles)
        stability = stability_raw.drop(columns=["feature_tier", "tier_reason"], errors="ignore").merge(
            tiers, on="feature", how="left"
        )
        corr = correlation_analysis(weekly_panel, metadata)

    processed = Path(processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    macro_features_daily.to_csv(processed / "wrds_macro_features_daily.csv", index=False)
    weekly_panel.to_csv(processed / "wrds_macro_weekly_crypto_panel.csv", index=False)

    write_wrds_macro_feature_reports(
        output_dir=output_dir,
        macro_daily=macro_daily,
        macro_features_daily=macro_features_daily,
        weekly_panel=weekly_panel,
        metadata=metadata,
        coverage=coverage,
        ic=ic,
        quantiles=quantiles,
        stability=stability,
        corr=corr,
        tiers=tiers,
    )
    return MacroFeatureResearchResult(
        macro_daily=macro_daily,
        macro_features_daily=macro_features_daily,
        weekly_panel=weekly_panel,
        metadata=metadata,
        coverage=coverage,
        ic_report=ic,
        quantile_report=quantiles,
        stability_report=stability,
        correlation_report=corr,
        tiers=tiers,
    )


def write_wrds_macro_feature_reports(
    output_dir: str | Path,
    macro_daily: pd.DataFrame,
    macro_features_daily: pd.DataFrame,
    weekly_panel: pd.DataFrame,
    metadata: pd.DataFrame,
    coverage: pd.DataFrame,
    ic: pd.DataFrame,
    quantiles: pd.DataFrame,
    stability: pd.DataFrame,
    corr: pd.DataFrame,
    tiers: pd.DataFrame,
) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(output / "data_coverage.csv", index=False)
    metadata.to_csv(output / "feature_inventory.csv", index=False)
    ic.to_csv(output / "feature_ic_report.csv", index=False)
    quantiles.to_csv(output / "feature_quantile_analysis.csv", index=False)
    stability.to_csv(output / "feature_stability_report.csv", index=False)
    corr.to_csv(output / "feature_correlation_analysis.csv", index=False)
    tiers.to_csv(output / "feature_tiers.csv", index=False)

    downloaded = coverage[coverage.get("status", pd.Series(dtype=str)).eq("downloaded")] if not coverage.empty else pd.DataFrame()
    missing = coverage[~coverage.get("status", pd.Series(dtype=str)).eq("downloaded")] if not coverage.empty else pd.DataFrame()
    macro_start = _date_or_na(macro_daily, "min")
    macro_end = _date_or_na(macro_daily, "max")
    feature_start = _date_or_na(macro_features_daily.dropna(how="all", subset=[c for c in macro_features_daily.columns if c != "date"]), "min") if not macro_features_daily.empty else "N/A"
    feature_end = _date_or_na(macro_features_daily.dropna(how="all", subset=[c for c in macro_features_daily.columns if c != "date"]), "max") if not macro_features_daily.empty else "N/A"
    weekly_start = _date_or_na(weekly_panel, "min")
    weekly_end = _date_or_na(weekly_panel, "max")

    (output / "data_coverage.md").write_text(
        "# WRDS macro feature data coverage\n\n"
        "Scope: targeted small daily WRDS series only. No large tables, trading strategy, or model fitting was run.\n\n"
        f"- Raw macro rows: {len(macro_daily)}\n"
        f"- Raw macro date range: {macro_start} to {macro_end}\n"
        f"- Lagged macro feature rows: {len(macro_features_daily)}\n"
        f"- Lagged macro feature date range with data: {feature_start} to {feature_end}\n"
        f"- Joined weekly crypto rows: {len(weekly_panel)}\n"
        f"- Joined weekly crypto date range: {weekly_start} to {weekly_end}\n"
        f"- Locked holdout reference: {HOLDOUT_START.date()} to {HOLDOUT_END.date()}\n\n"
        "## Downloaded sources\n\n"
        f"{_table(downloaded, [('source_name', 'Source'), ('library', 'Library'), ('table', 'Table'), ('start_date', 'Start'), ('end_date', 'End'), ('rows', 'Rows'), ('columns', 'Columns')])}\n\n"
        "## Sources not used or unavailable\n\n"
        f"{_table(missing, [('source_name', 'Source'), ('library', 'Library'), ('table', 'Table'), ('status', 'Status'), ('note', 'Note')])}\n\n"
        "## Explicit limitations\n\n"
        "- CBOE VVIX was searched in accessible CBOE metadata but was not available in the compact CBOE index table.\n"
        "- Commodity proxies were not downloaded because no small confirmed gold/oil/copper table or Datastream identifier was available.\n"
        "- Datastream/LSEG equivalents were not downloaded because identifiers/tables were not easy to confirm from the accessible metadata.\n"
        "- Several FRB daily rates/FX fields stop before the full 2026 crypto holdout; feature-research reports expose resulting missing coverage.\n",
        encoding="utf-8",
    )

    (output / "feature_inventory.md").write_text(
        "# WRDS macro-regime feature inventory\n\n"
        "All features are market-level and lagged by one calendar day after calculation before joining to the crypto weekly panel.\n\n"
        f"{_table(metadata, [('feature', 'Feature'), ('family', 'Family'), ('source', 'Source'), ('formula', 'Formula'), ('lag', 'Lag'), ('rationale', 'Economic rationale')])}\n",
        encoding="utf-8",
    )

    holdout_ic = stability[(stability.get("regime", pd.Series(dtype=str)) == "2025_2026_holdout")] if not stability.empty else pd.DataFrame()
    primary = ic[ic.get("horizon", pd.Series(dtype=str)).eq("1w")].copy() if not ic.empty else pd.DataFrame()
    if not primary.empty and not tiers.empty:
        primary = primary.merge(tiers[["feature", "feature_tier", "tier_reason"]], on="feature", how="left", suffixes=("", "_tier"))
        primary = primary.sort_values("newey_west_t", key=lambda s: s.abs(), ascending=False)
    quintiles = quantiles[(quantiles.get("horizon", pd.Series(dtype=str)) == "1w") & (quantiles.get("bucket_type", pd.Series(dtype=str)) == "quintile")] if not quantiles.empty else pd.DataFrame()
    if not quintiles.empty:
        sample_order = {
            "full_sample": 0,
            "development_pre_2025": 1,
            "holdout_2025_2026": 2,
            "2020_2021_bull": 3,
            "2022_bear": 4,
            "2023_2024_recovery": 5,
            "2025_2026_holdout": 6,
        }
        quintiles = quintiles.assign(_sample_order=quintiles["sample"].map(sample_order).fillna(99))
        quintiles = quintiles.sort_values(["feature", "_sample_order"]).drop(columns=["_sample_order"])
    redundancy = corr.head(40) if not corr.empty else pd.DataFrame()

    (output / "feature_research.md").write_text(
        "# WRDS macro feature research\n\n"
        "This report evaluates predictive feature quality only. It does not backtest, train a trading model, or select a strategy.\n\n"
        "## 1-week IC ranking\n\n"
        f"{_table(primary.head(25), [('feature', 'Feature'), ('method', 'Method'), ('full_sample_ic', 'Full IC'), ('mean_ic', 'Mean IC'), ('newey_west_t', 'NW t'), ('p_value', 'p-value'), ('ic_information_ratio', 'IC IR'), ('rolling_ic_stability', 'Rolling stability'), ('feature_tier', 'Tier')])}\n\n"
        "## Holdout IC checks\n\n"
        f"{_table(holdout_ic[holdout_ic.get('horizon', pd.Series(dtype=str)).eq('1w')].head(30), [('feature', 'Feature'), ('full_period_ic', 'Holdout IC'), ('newey_west_t', 'NW t'), ('p_value', 'p-value'), ('sign_consistent_with_development', 'Sign consistent'), ('feature_tier', 'Tier')])}\n\n"
        "## 1-week quintile spread checks\n\n"
        f"{_table(quintiles.head(45), [('feature', 'Feature'), ('sample', 'Sample'), ('mean_top_minus_bottom', 'Top-minus-bottom'), ('positive_spread_fraction', 'Positive fraction'), ('mean_monotonicity', 'Monotonicity'), ('n_observations', 'Observations')])}\n\n"
        "## Redundancy / correlation checks\n\n"
        f"{_table(redundancy, [('row_type', 'Type'), ('feature', 'Feature'), ('feature_2', 'Feature 2'), ('correlation', 'Correlation'), ('vif', 'VIF'), ('interpretation', 'Interpretation')])}\n",
        encoding="utf-8",
    )

    tier_counts = tiers.feature_tier.value_counts().to_dict() if not tiers.empty and "feature_tier" in tiers else {}
    tier_table = _table(
        tiers.sort_values(["feature_tier", "primary_t_stat"], ascending=[True, False]) if not tiers.empty else tiers,
        [("feature", "Feature"), ("feature_tier", "Tier"), ("primary_ic", "1w IC"), ("primary_t_stat", "NW t"), ("holdout_ic", "Holdout IC"), ("tier_reason", "Reason")],
    )
    candidate_tier1 = tiers[tiers.feature_tier.eq("Tier 1")].feature.tolist() if not tiers.empty and "feature_tier" in tiers else []
    recommendation = (
        "Proceed only with macro-regime strategy design using Tier 1 features listed below."
        if candidate_tier1 else
        "Do not use WRDS macro features in a trading strategy yet. The current feature set does not contain Tier 1 evidence under the project classifier."
    )
    (output / "final_recommendation.md").write_text(
        "# WRDS macro feature final recommendation\n\n"
        f"{recommendation}\n\n"
        "## Tier counts\n\n"
        f"- Tier 1: {tier_counts.get('Tier 1', 0)}\n"
        f"- Tier 2: {tier_counts.get('Tier 2', 0)}\n"
        f"- Tier 3: {tier_counts.get('Tier 3', 0)}\n\n"
        "## Tier classification\n\n"
        f"{tier_table}\n\n"
        "## Next data work before strategy testing\n\n"
        "- Confirm a commodity source or Datastream identifiers for gold, oil, and copper if commodity momentum remains required.\n"
        "- Confirm whether a WRDS-accessible VVIX series exists outside the compact CBOE table.\n"
        "- Extend FRB/rates/FX data beyond the current WRDS snapshot before treating 2025-2026 holdout conclusions as final.\n\n"
        "No trading strategy was run, no trading model was fit, and no holdout threshold was selected.\n",
        encoding="utf-8",
    )
    return output


def _date_or_na(frame: pd.DataFrame, how: str) -> str:
    if frame.empty or "date" not in frame:
        return "N/A"
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
    if dates.empty:
        return "N/A"
    value = dates.min() if how == "min" else dates.max()
    return str(value.date())


def _format(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and not np.isfinite(value):
        return "N/A"
    if isinstance(value, (float, np.floating)):
        return f"{value:.4f}"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")[:300]


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]]) -> str:
    if frame is None or frame.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in frame.to_dict("records"):
        lines.append("| " + " | ".join(_format(row.get(key)) for key, _ in columns) + " |")
    return "\n".join(lines)


__all__ = [
    "MacroFeatureResearchResult",
    "SERIES_SPECS",
    "build_lagged_macro_features",
    "build_weekly_macro_crypto_panel",
    "download_wrds_macro_series",
    "macro_time_series_quantile_analysis",
    "run_macro_feature_research",
]
