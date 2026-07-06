"""WRDS discovery and integration planning.

This module is intentionally read-only. It discovers available WRDS libraries
and relevant tables when credentials are supplied through environment
variables, then writes research-planning reports. It does not download research
data for backtests and it never stores or prints credentials.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from getpass import getpass
from pathlib import Path
from typing import Any, Callable, Iterable


WRDS_USERNAME_ENV = "WRDS_USERNAME"
WRDS_PASSWORD_ENV = "WRDS_PASSWORD"
DEFAULT_ENV_FILE = ".env"


@dataclass(frozen=True)
class WRDSCredentialStatus:
    username_present: bool
    password_present: bool

    @property
    def ready(self) -> bool:
        return self.username_present and self.password_present

    @property
    def label(self) -> str:
        if self.ready:
            return "available"
        missing = []
        if not self.username_present:
            missing.append(WRDS_USERNAME_ENV)
        if not self.password_present:
            missing.append(WRDS_PASSWORD_ENV)
        return "missing " + ", ".join(missing)


@dataclass(frozen=True)
class TableMatch:
    library: str
    table: str
    category: str
    rationale: str


@dataclass(frozen=True)
class TableDetail:
    library: str
    table: str
    categories: tuple[str, ...]
    date_coverage: str
    frequency: str
    fields_available: str
    relevance: str
    status: str


@dataclass(frozen=True)
class DatasetCandidate:
    category: str
    source: str
    likely_libraries: tuple[str, ...]
    likely_tables_or_identifiers: tuple[str, ...]
    crypto_relevance: str
    limitation: str


@dataclass
class WRDSInventoryResult:
    status: str
    credential_status: WRDSCredentialStatus
    wrds_package_available: bool | None
    libraries: list[str]
    tables_by_library: dict[str, list[str]]
    scanned_libraries: list[str]
    table_matches: list[TableMatch]
    table_errors: dict[str, str]
    candidates: list[DatasetCandidate]
    notes: list[str]
    current_user: str | None = None
    table_counts_by_schema: dict[str, int] = field(default_factory=dict)
    table_details: list[TableDetail] = field(default_factory=list)


class _WRDSDirectInventoryConnection:
    """Small wrapper around a live WRDS SQLAlchemy connection.

    The official WRDS connection eagerly runs a heavy library-list query. Some
    environments close the SSL connection during that query. This wrapper uses
    simpler information_schema queries after authentication succeeds.
    """

    def __init__(self, connection: Any, close_callback: Callable[[], None], libraries: list[str]):
        self._connection = connection
        self._close_callback = close_callback
        self._libraries = libraries

    def list_libraries(self) -> list[str]:
        return self._libraries

    def list_tables(self, library: str) -> list[str]:
        import sqlalchemy as sa  # type: ignore

        query = sa.text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
            ORDER BY table_name
            """
        )
        rows = self._connection.execute(query, {"schema": library}).fetchall()
        return [str(row[0]) for row in rows]

    def current_user(self) -> str:
        import sqlalchemy as sa  # type: ignore

        row = self._connection.execute(sa.text("SELECT current_user")).fetchone()
        return str(row[0]) if row else ""

    def table_counts_by_schema(self) -> dict[str, int]:
        import sqlalchemy as sa  # type: ignore

        query = sa.text(
            """
            SELECT table_schema, COUNT(*) AS table_count
            FROM information_schema.tables
            WHERE table_schema <> 'information_schema'
              AND table_schema NOT LIKE 'pg_%'
              AND has_schema_privilege(table_schema, 'USAGE')
            GROUP BY table_schema
            ORDER BY table_schema
            """
        )
        rows = self._connection.execute(query).fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    def list_columns(self, library: str, table: str) -> list[tuple[str, str]]:
        import sqlalchemy as sa  # type: ignore

        query = sa.text(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table
            ORDER BY ordinal_position
            """
        )
        rows = self._connection.execute(query, {"schema": library, "table": table}).fetchall()
        return [(str(row[0]), str(row[1])) for row in rows]

    def date_coverage(self, library: str, table: str, column: str) -> tuple[str | None, str | None]:
        import sqlalchemy as sa  # type: ignore

        schema = _quote_identifier(library)
        table_name = _quote_identifier(table)
        column_name = _quote_identifier(column)
        query = sa.text(f"SELECT MIN({column_name}) AS min_date, MAX({column_name}) AS max_date FROM {schema}.{table_name}")
        try:
            self._connection.execute(sa.text("SET statement_timeout TO 8000"))
        except Exception:
            pass
        row = self._connection.execute(query).fetchone()
        if not row:
            return None, None
        return (str(row[0]) if row[0] is not None else None, str(row[1]) if row[1] is not None else None)

    def close(self) -> None:
        self._close_callback()


CATEGORY_TERMS: dict[str, dict[str, tuple[str, ...]]] = {
    "crypto market data": {
        "library": ("crypto", "coin", "tr_ds", "trdssamp", "trdstrm"),
        "table": ("crypto", "bitcoin", "btc", "ethereum", "eth", "coin", "digital_asset"),
    },
    "Datastream / LSEG time series": {
        "library": ("datastream", "lseg", "refinitiv", "worldscope", "tr_ds", "trdssamp", "trdstrm", "trsamp_ds", "trsamp_worldscope"),
        "table": ("datastream", "worldscope", "lseg", "refinitiv", "exchange_rate", "ds2"),
    },
    "macro variables": {
        "library": ("fred", "frb", "bea", "bls", "macro", "econdb", "imf", "worldbank", "trsamp_dsecon"),
        "table": ("gdp", "cpi", "pce", "payroll", "unemployment", "liquidity", "money", "macro", "inflation", "fred"),
    },
    "FX": {
        "library": ("fx", "currency", "tr_ds", "trdssamp", "trdstrm"),
        "table": ("exchange", "currency", "fx", "dxy", "broad_dollar", "exchange_rate"),
    },
    "interest rates": {
        "library": ("fred", "frb", "treasury", "ice", "swap", "fisd", "crsp_a_treasuries", "crsp_q_treasuries"),
        "table": ("treasury", "yield", "sofr", "fedfunds", "swap", "term", "move", "bill", "bond"),
    },
    "commodities": {
        "library": ("commodity", "commodities", "cme", "datastream", "lseg", "crb"),
        "table": ("oil", "gold", "copper", "commodity", "futures", "crb", "brent", "wti"),
    },
    "equity indices": {
        "library": ("crsp_a_indexes", "crsp_q_indexes", "crsp_q_indexhist", "msci", "djones", "snp", "spglobal", "tr_ds", "trdssamp", "trdstrm"),
        "table": ("sp500", "nasdaq", "russell", "msci", "djia", "dji", "dsi", "dsix", "index_level", "indexhist"),
    },
    "volatility indices": {
        "library": ("cboe", "option", "optionm", "datastream", "lseg", "cfe"),
        "table": ("vix", "vvix", "vx", "move", "volatility", "implied_vol", "skew", "cboe"),
    },
    "ETF flows": {
        "library": ("etfg", "etfg_samp", "etfgsamp", "lipper", "tfn", "wrds_mutualfund"),
        "table": ("etf", "fund_flow", "flows", "holdings", "mutualfund", "portfolio"),
    },
    "news / RavenPack": {
        "library": ("raven", "ravenpack", "news", "dowjones", "djones"),
        "table": ("news", "sentiment", "raven", "rpna", "entity"),
    },
    "options / OptionMetrics": {
        "library": ("optionm", "option", "ivydb", "cboe"),
        "table": ("option", "ivydb", "opprcd", "implied", "surface", "volatility", "cboe"),
    },
}


DATASET_CANDIDATES: list[DatasetCandidate] = [
    DatasetCandidate(
        "crypto market data",
        "Datastream / LSEG digital asset series, if licensed",
        ("datastream", "tr_ds", "ds", "lseg", "refinitiv"),
        ("BTC", "ETH", "crypto", "digital asset identifiers"),
        "Potential independent BTC/ETH prices, index series, and cross-venue macro-aligned timestamps.",
        "Coverage and identifiers depend on the institution's Datastream/LSEG license; WRDS is not usually the best source for crypto-native OHLCV.",
    ),
    DatasetCandidate(
        "Datastream / LSEG time series",
        "Refinitiv Datastream / LSEG cross-asset time series",
        ("datastream", "tr_ds", "ds", "lseg", "refinitiv"),
        ("equity indices", "DXY", "commodities", "rates", "VIX"),
        "Single source for broad macro/risk-regime inputs that can be lagged and merged with crypto daily bars.",
        "Symbol mapping must be versioned; vendor revisions and holidays need explicit treatment.",
    ),
    DatasetCandidate(
        "macro variables",
        "FRED, Federal Reserve, BEA/BLS, or Datastream macro series through WRDS",
        ("fred", "frb", "bea", "bls", "macro", "datastream"),
        ("DFF", "SOFR", "CPI", "unemployment", "money supply", "financial conditions"),
        "Macro liquidity and risk-regime features: liquidity impulse, inflation/rates pressure, economic stress.",
        "Low-frequency macro data is released with delays and revisions; use release calendars or conservative lags.",
    ),
    DatasetCandidate(
        "FX",
        "USD index and major FX series from Datastream/LSEG or FRED",
        ("datastream", "tr_ds", "fred", "fx"),
        ("DXY", "broad USD index", "EURUSD", "JPY", "CNH"),
        "Crypto often trades as a high-beta anti-USD liquidity asset; USD uptrends can gate risk down.",
        "FX data helps regime filtering but is not crypto-specific.",
    ),
    DatasetCandidate(
        "interest rates",
        "Treasury, SOFR/Fed funds, real yield, and yield-curve series",
        ("fred", "frb", "datastream", "ice"),
        ("2Y", "10Y", "TIPS real yield", "SOFR", "Fed funds", "2s10s"),
        "Rates trend and real-rate shocks can identify hostile conditions for speculative assets.",
        "Daily rates are useful; macro release data must be lagged to avoid revision leakage.",
    ),
    DatasetCandidate(
        "commodities",
        "Gold, copper, oil, broad commodity indices",
        ("datastream", "tr_ds", "cme", "commodity"),
        ("gold", "copper", "WTI", "Brent", "CRB"),
        "Commodity trends can proxy inflation, growth, and risk sentiment; gold/BTC interaction may be relevant.",
        "Commodity signals are indirect and can add noise if used without a predeclared regime rule.",
    ),
    DatasetCandidate(
        "equity indices",
        "CRSP/Compustat/Datastream equity index returns",
        ("crsp", "comp", "datastream", "msci", "snp"),
        ("S&P 500", "Nasdaq 100", "Russell 2000", "MSCI World"),
        "Risk-on/risk-off gate: equity trend, drawdown, breadth, and realized volatility.",
        "Equity data is useful for regime, not as a direct crypto alpha source.",
    ),
    DatasetCandidate(
        "volatility indices",
        "CBOE VIX/VVIX or Datastream volatility index series",
        ("cboe", "datastream", "optionm"),
        ("VIX", "VVIX", "MOVE", "volatility index"),
        "Volatility shock filter: reduce crypto exposure when VIX is high or rapidly rising.",
        "VIX reflects equity options, not crypto options; still useful as a global risk proxy.",
    ),
    DatasetCandidate(
        "ETF flows",
        "ETF Global, CRSP mutual fund/ETF, Lipper, or fund-holdings data if licensed",
        ("etf", "crsp", "lipper", "fund"),
        ("ETF flows", "holdings", "AUM", "fund returns"),
        "Institutional flow proxy, especially for spot BTC/ETH ETFs if covered after launch.",
        "WRDS ETF flow coverage may not include crypto ETFs or may arrive with delays unsuitable for weekly trading.",
    ),
    DatasetCandidate(
        "news / RavenPack",
        "RavenPack or other licensed news sentiment on WRDS",
        ("ravenpack", "raven", "news"),
        ("entity sentiment", "event novelty", "relevance", "crypto entities"),
        "Risk-event filter and sentiment confirmation if crypto entities or broad market risk topics are covered.",
        "News is high-dimensional, licensed, timestamp-sensitive, and easy to overfit.",
    ),
    DatasetCandidate(
        "options / OptionMetrics",
        "OptionMetrics IvyDB and index/ETF options",
        ("optionm", "optionmetrics", "ivydb"),
        ("SPY", "QQQ", "VIX-linked products", "implied volatility", "skew"),
        "Equity/index options can provide implied-risk features; crypto options are unlikely unless specifically licensed elsewhere.",
        "Useful for market-regime filters, but not a substitute for Deribit-style crypto implied volatility.",
    ),
]


FEATURE_PLAN_ROWS: list[dict[str, str]] = [
    {
        "feature_group": "macro risk regime",
        "wrds_source": "Datastream/LSEG, FRED/FRB macro series if accessible",
        "example_features": "financial-conditions z-score; recession/stress proxy; release-lagged macro surprise where available",
        "trading_use": "Permit crypto exposure only outside broad macro stress.",
        "leakage_control": "Use publication/release lags; do not use revised values at original dates without point-in-time vintages.",
    },
    {
        "feature_group": "USD liquidity",
        "wrds_source": "DXY/broad USD from Datastream/LSEG or FRED; money-market/rates series",
        "example_features": "DXY 50/200-day trend; 20-day USD momentum; liquidity impulse proxy",
        "trading_use": "Reduce BTC/ETH exposure during strong USD/liquidity-tightening regimes.",
        "leakage_control": "Daily series lagged one trading day; macro proxies lagged by release schedule.",
    },
    {
        "feature_group": "rates",
        "wrds_source": "Treasury, Fed funds, SOFR, real yields from FRED/FRB/Datastream",
        "example_features": "2Y and 10Y yield trend; 10Y real-yield change; yield-curve slope",
        "trading_use": "Identify tightening shocks that historically pressure high-duration risk assets.",
        "leakage_control": "Use prior close or conservative one-day lag.",
    },
    {
        "feature_group": "equity risk-on/risk-off",
        "wrds_source": "CRSP/Compustat/Datastream equity index data",
        "example_features": "S&P 500 above 200-day average; Nasdaq 30-day momentum; equity drawdown",
        "trading_use": "Gate crypto risk when equities are in confirmed uptrends.",
        "leakage_control": "Align to crypto decision timestamp; lag one day because crypto trades 24/7.",
    },
    {
        "feature_group": "commodity risk sentiment",
        "wrds_source": "Datastream/LSEG commodity series",
        "example_features": "gold trend; copper/gold ratio; oil shock filter; broad commodity momentum",
        "trading_use": "Differentiate inflation shocks, growth risk, and safe-haven regimes.",
        "leakage_control": "Daily lag; predeclare transformations to avoid narrative fitting.",
    },
    {
        "feature_group": "VIX / volatility",
        "wrds_source": "CBOE/Datastream VIX, VVIX, MOVE if licensed",
        "example_features": "VIX level percentile; 5-day VIX change; volatility shock dummy",
        "trading_use": "Risk-off gate or position-size reduction during volatility shocks.",
        "leakage_control": "Use only observations known before rebalance.",
    },
    {
        "feature_group": "ETF / institutional flows",
        "wrds_source": "ETF Global, CRSP mutual fund/ETF, Lipper, holdings databases if licensed",
        "example_features": "BTC ETF AUM/flow change; crypto-equity ETF flow; institutional demand proxy",
        "trading_use": "Confirm risk-on exposure if spot ETF flow data is timely and complete.",
        "leakage_control": "Use actual report availability dates; assume stale if only monthly/quarterly.",
    },
    {
        "feature_group": "news sentiment",
        "wrds_source": "RavenPack if licensed",
        "example_features": "crypto entity sentiment; macro risk sentiment; novelty-weighted negative-news shock",
        "trading_use": "Avoid exposure during broad negative event clusters; do not use as a standalone alpha yet.",
        "leakage_control": "Use timestamped news only; aggregate before rebalance cut-off.",
    },
    {
        "feature_group": "options-implied volatility",
        "wrds_source": "OptionMetrics, CBOE, Datastream",
        "example_features": "SPY/QQQ implied volatility; skew; term-structure slope; VIX/VVIX",
        "trading_use": "Forward-looking risk proxy for macro-conditioned crypto exposure.",
        "leakage_control": "Lag option metrics and ensure no post-close values enter same-day crypto decisions.",
    },
]


def credential_status(env: dict[str, str] | None = None) -> WRDSCredentialStatus:
    """Return credential presence without exposing values."""
    source = os.environ if env is None else env
    return WRDSCredentialStatus(
        username_present=bool(source.get(WRDS_USERNAME_ENV)),
        password_present=bool(source.get(WRDS_PASSWORD_ENV)),
    )


def load_env_file(path: str | Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    """Load simple KEY=VALUE lines from a local env file without mutating os.environ."""
    env_path = Path(path)
    if not env_path.exists():
        return {}
    loaded: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in {WRDS_USERNAME_ENV, WRDS_PASSWORD_ENV}:
            loaded[key] = value
    return loaded


def merged_environment(env: dict[str, str] | None = None, env_file: str | Path | None = DEFAULT_ENV_FILE) -> dict[str, str]:
    """Merge process env, optional env file, and explicit env without printing secrets."""
    merged = dict(os.environ)
    if env_file:
        merged.update(load_env_file(env_file))
    if env:
        merged.update(env)
    return merged


def prompt_for_credentials(env: dict[str, str] | None = None) -> dict[str, str]:
    """Prompt for missing WRDS credentials without echoing or persisting values."""
    source = dict(os.environ if env is None else env)
    if not source.get(WRDS_USERNAME_ENV):
        username = input("Please enter your WRDS username: ").strip()
        if username:
            source[WRDS_USERNAME_ENV] = username
    if not source.get(WRDS_PASSWORD_ENV):
        password = getpass("Please enter your WRDS password: ")
        if password:
            source[WRDS_PASSWORD_ENV] = password
    return source


def _safe_exception(exc: Exception, env: dict[str, str] | None = None) -> str:
    text = f"{type(exc).__name__}: {exc}"
    source = os.environ if env is None else env
    for key in (WRDS_USERNAME_ENV, WRDS_PASSWORD_ENV):
        value = source.get(key)
        if value:
            text = text.replace(value, "[redacted]")
    return text[:500]


def _contains_any(value: str, terms: Iterable[str]) -> bool:
    lower = value.lower()
    return any(term.lower() in lower for term in terms)


def _classify(library: str, table: str | None = None) -> list[str]:
    matches = []
    for category, terms in CATEGORY_TERMS.items():
        lib_match = _contains_any(library, terms["library"])
        table_match = bool(table and _contains_any(table, terms["table"]))
        if lib_match or table_match:
            matches.append(category)
    return matches


def _should_scan_library(library: str) -> bool:
    return bool(_classify(library))


def _connect_with_env(env: dict[str, str] | None = None):
    source = os.environ if env is None else env
    try:
        import wrds  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError("wrds Python package is not installed") from exc

    version = getattr(getattr(wrds, "_version", None), "__version_tuple__", (3, 0, 0))
    appname = f"codex-crypto-wrds/{'.'.join(str(part) for part in version)}"
    db = wrds.Connection(
        autoconnect=False,
        verbose=False,
        wrds_username=source[WRDS_USERNAME_ENV],
        wrds_password=source[WRDS_PASSWORD_ENV],
        wrds_connect_args={"sslmode": "require", "application_name": appname, "connect_timeout": 45},
    )
    db.connect()

    def close() -> None:
        db.close()

    return _WRDSDirectInventoryConnection(
        db.connection,
        close,
        _list_wrds_libraries_direct(db.connection),
    )


def _list_wrds_libraries_direct(connection: Any) -> list[str]:
    import sqlalchemy as sa  # type: ignore

    query = sa.text(
        """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name <> 'information_schema'
          AND schema_name NOT LIKE 'pg_%'
          AND has_schema_privilege(schema_name, 'USAGE')
        ORDER BY schema_name
        """
    )
    rows = connection.execute(query).fetchall()
    return [str(row[0]) for row in rows]


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


DATE_COLUMN_CANDIDATES = (
    "date", "caldt", "datadate", "fdate", "time", "timestamp", "datetime",
    "obs_date", "tradedate", "trade_date", "bdate", "begdat", "enddat",
)


def _infer_frequency(columns: list[tuple[str, str]], table: str) -> str:
    names = {name.lower() for name, _ in columns}
    lower = table.lower()
    if any(name in names for name in ("time", "timestamp", "datetime")) or "intraday" in lower:
        return "intraday or timestamped"
    if any(name in names for name in ("date", "caldt", "datadate", "fdate", "obs_date", "tradedate", "trade_date")):
        if any(term in lower for term in ("monthly", "month", "mth", "m_")):
            return "monthly likely"
        if any(term in lower for term in ("quarter", "qtr", "q_")):
            return "quarterly likely"
        return "daily/date-stamped likely"
    if any(term in lower for term in ("annual", "year")):
        return "annual likely"
    return "unknown from metadata"


def _date_column(columns: list[tuple[str, str]]) -> str | None:
    lower_to_original = {name.lower(): name for name, _ in columns}
    for candidate in DATE_COLUMN_CANDIDATES:
        if candidate in lower_to_original:
            return lower_to_original[candidate]
    for name, data_type in columns:
        if "date" in data_type.lower() or "time" in data_type.lower():
            return name
    return None


def _category_relevance(category: str) -> tuple[str, str]:
    high = {
        "Datastream / LSEG time series",
        "macro variables",
        "FX",
        "interest rates",
        "equity indices",
        "volatility indices",
    }
    medium = {
        "ETF flows",
        "news / RavenPack",
        "options / OptionMetrics",
        "commodities",
        "crypto market data",
    }
    if category in high:
        return "High relevance", "Directly supports macro/risk-regime features for crypto stability and regime-aware prediction."
    if category in medium:
        return "Medium relevance", "Potentially useful as a regime or confirmation feature, but requires stricter coverage/timing checks."
    return "Low relevance", "Indirect or uncertain relevance for the current crypto regime-modelling objective."


def _match_priority(match: TableMatch) -> tuple[int, str, str]:
    library = match.library.lower()
    table = match.table.lower()
    preferred_libraries = (
        "crsp_a_indexes", "crsp_q_indexes", "crsp_q_indexhist", "crsp",
        "crsp_a_treasuries", "crsp_q_treasuries", "cboe", "optionm",
        "ravenpack", "etfg", "frb", "tr_ds", "trdssamp", "trdstrm",
        "trsamp_dsecon", "trsamp_dscom", "trsamp_dsfut",
    )
    preferred_tables = (
        "dsi", "dsix", "dsp500", "treasury", "yield", "vix", "vvix",
        "move", "option", "opprcd", "raven", "sentiment", "etf",
        "flow", "exchange_rate", "dxy", "gold", "oil", "copper",
    )
    preferred_library_score = 0 if any(library == item or library.startswith(item) for item in preferred_libraries) else 1
    preferred_table_score = 0 if any(term in table for term in preferred_tables) else 1
    category_score = 0 if match.category in {
        "equity indices", "volatility indices", "interest rates", "Datastream / LSEG time series", "macro variables", "FX"
    } else 1
    return (preferred_library_score, preferred_table_score, category_score, library, table)


def _table_details(conn: Any, matches: list[TableMatch], limit: int = 250) -> list[TableDetail]:
    details: list[TableDetail] = []
    seen: set[tuple[str, str]] = set()
    for match in sorted(matches, key=_match_priority):
        key = (match.library, match.table)
        if key in seen:
            continue
        seen.add(key)
        if len(details) >= limit:
            break
        categories = tuple(sorted(_classify(match.library, match.table)))
        try:
            columns = conn.list_columns(match.library, match.table) if hasattr(conn, "list_columns") else []
        except Exception:
            columns = []
        fields = ", ".join(name for name, _ in columns[:40]) if columns else "not available"
        if len(columns) > 40:
            fields += f", ... ({len(columns)} fields)"
        frequency = _infer_frequency(columns, match.table) if columns else "unknown"
        date_coverage = "not available from metadata"
        date_col = _date_column(columns)
        if date_col and hasattr(conn, "date_coverage"):
            try:
                start, end = conn.date_coverage(match.library, match.table, date_col)
                date_coverage = f"{date_col}: {start or 'unknown'} to {end or 'unknown'}"
            except Exception:
                date_coverage = f"{date_col}: coverage query timed out or unavailable"
        rank, rationale = _category_relevance(categories[0] if categories else "")
        details.append(TableDetail(
            library=match.library,
            table=match.table,
            categories=categories,
            date_coverage=date_coverage,
            frequency=frequency,
            fields_available=fields,
            relevance=rationale,
            status=rank,
        ))
    return details


def discover_wrds_inventory(
    env: dict[str, str] | None = None,
    connection_factory: Callable[[], Any] | None = None,
    scan_all_tables: bool = True,
) -> WRDSInventoryResult:
    """Discover WRDS libraries/tables without failing when credentials are absent."""
    status = credential_status(env)
    notes: list[str] = []
    if connection_factory is None and not status.ready:
        return WRDSInventoryResult(
            status="credentials_missing",
            credential_status=status,
            wrds_package_available=None,
            libraries=[],
            tables_by_library={},
            scanned_libraries=[],
            table_matches=[],
            table_errors={},
            candidates=DATASET_CANDIDATES,
            notes=[
                "No live WRDS query was attempted because WRDS_USERNAME and/or WRDS_PASSWORD is missing.",
                "Reports were generated from the predeclared WRDS research inventory only.",
            ],
        )

    package_available: bool | None = True
    try:
        conn = connection_factory() if connection_factory is not None else _connect_with_env(env)
    except RuntimeError as exc:
        if "wrds Python package" in str(exc):
            package_available = False
            return WRDSInventoryResult(
                status="wrds_package_missing",
                credential_status=status,
                wrds_package_available=package_available,
                libraries=[],
                tables_by_library={},
                scanned_libraries=[],
                table_matches=[],
                table_errors={},
                candidates=DATASET_CANDIDATES,
                notes=["The optional wrds package is not installed; install wrds>=3.2 to query live inventory."],
            )
        return WRDSInventoryResult(
            status="connection_failed",
            credential_status=status,
            wrds_package_available=package_available,
            libraries=[],
            tables_by_library={},
            scanned_libraries=[],
            table_matches=[],
            table_errors={"connection": _safe_exception(exc, env)},
            candidates=DATASET_CANDIDATES,
            notes=["WRDS connection failed. Credentials were not printed or persisted."],
        )
    except Exception as exc:  # pragma: no cover - network/auth dependent
        return WRDSInventoryResult(
            status="connection_failed",
            credential_status=status,
            wrds_package_available=package_available,
            libraries=[],
            tables_by_library={},
            scanned_libraries=[],
            table_matches=[],
            table_errors={"connection": _safe_exception(exc, env)},
            candidates=DATASET_CANDIDATES,
            notes=["WRDS connection failed. Credentials were not printed or persisted."],
        )

    libraries: list[str] = []
    scanned: list[str] = []
    tables_by_library: dict[str, list[str]] = {}
    matches: list[TableMatch] = []
    errors: dict[str, str] = {}
    current_user: str | None = None
    table_counts: dict[str, int] = {}
    details: list[TableDetail] = []
    try:
        if hasattr(conn, "current_user"):
            try:
                current_user = str(conn.current_user())
            except Exception as exc:
                errors["current_user"] = _safe_exception(exc, env)
        if hasattr(conn, "table_counts_by_schema"):
            try:
                table_counts = conn.table_counts_by_schema()
            except Exception as exc:
                errors["table_counts_by_schema"] = _safe_exception(exc, env)
        libraries = sorted(str(item) for item in conn.list_libraries())
        for library in libraries:
            if not scan_all_tables and not _should_scan_library(library):
                continue
            try:
                tables = sorted(str(item) for item in conn.list_tables(library=library))
            except Exception as exc:  # pragma: no cover - WRDS permission dependent
                errors[library] = _safe_exception(exc, env)
                continue
            tables_by_library[library] = tables
            scanned.append(library)
            library_categories = _classify(library)
            for table in tables:
                categories = _classify(library, table)
                if not categories:
                    continue
                for category in categories:
                    rationale = "library name matched" if category in library_categories else "table name matched"
                    matches.append(TableMatch(library=library, table=table, category=category, rationale=rationale))
        details = _table_details(conn, matches)
    finally:
        close = getattr(conn, "close", None)
        if callable(close):
            close()

    if not scanned:
        notes.append("No table lists were scanned. Check WRDS permissions or run with scan_all_tables=True.")
    if not matches:
        notes.append("No relevant table-name matches were found; manual WRDS web search may still identify licensed datasets.")
    return WRDSInventoryResult(
        status="queried",
        credential_status=status,
        wrds_package_available=package_available,
        libraries=libraries,
        tables_by_library=tables_by_library,
        scanned_libraries=scanned,
        table_matches=matches,
        table_errors=errors,
        candidates=DATASET_CANDIDATES,
        notes=notes,
        current_user=current_user,
        table_counts_by_schema=table_counts or {library: len(tables) for library, tables in tables_by_library.items()},
        table_details=details,
    )


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "not checked"
    return "yes" if value else "no"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(lines)


def _candidate_status(candidate: DatasetCandidate, result: WRDSInventoryResult) -> str:
    if result.status != "queried":
        return "not queried"
    matched_libraries = {match.library.lower() for match in result.table_matches}
    for library in result.libraries:
        lower = library.lower()
        if any(name in lower for name in candidate.likely_libraries):
            return "library accessible"
    if any(any(name in library for name in candidate.likely_libraries) for library in matched_libraries):
        return "matched table"
    return "not found in accessible inventory"


def _matches_by_category(result: WRDSInventoryResult) -> dict[str, list[TableMatch]]:
    grouped: dict[str, list[TableMatch]] = {}
    for match in result.table_matches:
        grouped.setdefault(match.category, []).append(match)
    return grouped


def write_wrds_reports(result: WRDSInventoryResult, output_dir: str | Path) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    auth_status = "success" if result.status == "queried" else "not authenticated"
    current_user_status = "queried successfully; value redacted from report" if result.current_user else "not available"
    schema_count_rows = [
        [schema, count]
        for schema, count in sorted(result.table_counts_by_schema.items())
    ] or [["none", 0]]

    (output / "connection_test.md").write_text(f"""# WRDS connection test

## Result

{_table(['Field', 'Value'], [
    ['status', result.status],
    ['authentication', auth_status],
    ['current_user query', current_user_status],
    ['credentials source', '.env and/or process environment'],
    ['credentials written to report', 'no'],
    ['wrds package available', _format_bool(result.wrds_package_available)],
    ['accessible schema count', len(result.libraries)],
    ['accessible table count', sum(len(tables) for tables in result.tables_by_library.values())],
])}

## Table counts per accessible schema

{_table(['Schema', 'Table count'], schema_count_rows)}

## Notes

{_table(['Note'], [[note] for note in result.notes] or [['none']])}

The authenticated WRDS user value was queried to verify login, but it is redacted
from this report so that credential-like identifiers are not persisted.
""", encoding="utf-8")

    (output / "access_setup.md").write_text(f"""# WRDS access setup

## Credential handling

This project reads WRDS credentials only from environment variables:

- `{WRDS_USERNAME_ENV}`
- `{WRDS_PASSWORD_ENV}`

The code does not hardcode, print, serialize, or commit credentials. The current
session credential status is: **{result.credential_status.label}**.

## Local setup

Install the optional connector:

```bash
python -m pip install wrds
```

Set credentials for the current PowerShell session:

```powershell
$env:WRDS_USERNAME = "your_wrds_username"
$env:WRDS_PASSWORD = "your_wrds_password"
python -m src.run_wrds_inventory --scan-all-tables
```

For persistent local configuration, copy `.env.example` to `.env` and load it
with your own shell or secret manager. `.env` and credential-style files are
ignored by git. Do not paste real credentials into source files, notebooks,
reports, command history that is shared, or issue trackers.

## Non-failing behavior

If credentials or the optional `wrds` package are unavailable, this module still
writes planning reports and marks live access as not queried. That is the
expected behavior for CI and credential-free research review.
""", encoding="utf-8")

    library_rows = [[library] for library in result.libraries] or [["No live WRDS libraries were queried."]]
    scanned = ", ".join(result.scanned_libraries[:30])
    if len(result.scanned_libraries) > 30:
        scanned += f", ... ({len(result.scanned_libraries)} scanned total)"
    if not scanned:
        scanned = "none"
    table_rows = [
        [library, table]
        for library in sorted(result.tables_by_library)
        for table in result.tables_by_library[library]
    ] or [["No live WRDS tables were queried.", ""]]
    (output / "available_libraries.md").write_text(f"""# WRDS available libraries

## Query status

{_table(['Field', 'Value'], [
    ['status', result.status],
    ['credentials', result.credential_status.label],
    ['wrds package available', _format_bool(result.wrds_package_available)],
    ['library count', len(result.libraries)],
    ['table count', sum(len(tables) for tables in result.tables_by_library.values())],
    ['scanned libraries', scanned],
])}

## Accessible library names

{_table(['Library'], library_rows)}

## Table counts by schema

{_table(['Schema', 'Table count'], schema_count_rows)}

## Table-query errors

{_table(['Library', 'Error'], [[key, value] for key, value in result.table_errors.items()] or [['none', 'none']])}

## Interpretation

When credentials are missing, this report intentionally does not claim dataset
access. When credentials are present, `library count` reflects the WRDS account's
accessible libraries and the relevant table matches are summarized in
`relevant_datasets.md`.
""", encoding="utf-8")

    (output / "available_tables.md").write_text(f"""# WRDS available tables

## Full accessible table inventory

{_table(['Library', 'Table'], table_rows)}

## Table-query errors

{_table(['Library', 'Error'], [[key, value] for key, value in result.table_errors.items()] or [['none', 'none']])}
""", encoding="utf-8")

    relevant_rows = []
    grouped = _matches_by_category(result)
    for candidate in result.candidates:
        matches = grouped.get(candidate.category, [])
        sample_matches = "; ".join(f"{match.library}.{match.table}" for match in matches[:6])
        if len(matches) > 6:
            sample_matches += f"; ... ({len(matches)} matches)"
        relevant_rows.append([
            candidate.category,
            candidate.source,
            ", ".join(candidate.likely_libraries),
            _candidate_status(candidate, result),
            sample_matches or "none",
            candidate.crypto_relevance,
            candidate.limitation,
        ])

    detail_rows = [
        [
            detail.status,
            detail.library,
            detail.table,
            ", ".join(detail.categories),
            detail.date_coverage,
            detail.frequency,
            detail.fields_available,
            detail.relevance,
        ]
        for detail in result.table_details
    ] or [["not found", "", "", "", "", "", "", "No live relevant tables were discovered."]]

    (output / "relevant_datasets.md").write_text(f"""# WRDS datasets relevant to crypto research

WRDS is unlikely to replace exchange-native crypto data for OHLCV, funding,
open interest, liquidations, or order-book features. Its likely value here is
external market-state data: macro, rates, USD, equity, volatility, ETF flow,
news, and options-implied-risk proxies.

{_table(['Category', 'Candidate source', 'Likely libraries', 'Status', 'Matched examples', 'Crypto relevance', 'Limitation'], relevant_rows)}

## Discovered relevant tables

{_table(['Rank', 'Library', 'Table', 'Categories', 'Date coverage', 'Frequency', 'Fields available', 'Relevance'], detail_rows)}

## Useful vs not useful

Useful for this project:

- Datastream/LSEG or equivalent cross-asset series for USD, rates, equity indices, commodities, and VIX-style volatility proxies.
- FRED/FRB-style macro and rates series if point-in-time or conservatively lagged.
- OptionMetrics/CBOE-style implied risk measures for broad markets.
- ETF/fund-flow datasets only if they include timely BTC/ETH ETF flow or institutional risk-flow proxies.
- RavenPack/news only if timestamped entity-level coverage is available and the feature set is tightly predeclared.

Not useful as a first priority:

- Corporate fundamentals and accounting databases for single-name equities.
- Intraday equity TAQ data unless the research question shifts to cross-market microstructure.
- Equity options chains for single stocks unrelated to crypto, except as broad risk-regime aggregates.
- Static holdings or delayed fund data that cannot be known before weekly crypto rebalances.
""", encoding="utf-8")

    high = [detail for detail in result.table_details if detail.status == "High relevance"]
    medium = [detail for detail in result.table_details if detail.status == "Medium relevance"]
    low = [detail for detail in result.table_details if detail.status == "Low relevance"]

    def rows_for(items: list[TableDetail]) -> list[list[Any]]:
        return [
            [
                item.library,
                item.table,
                ", ".join(item.categories),
                item.date_coverage,
                item.frequency,
                item.relevance,
            ]
            for item in items
        ] or [["none", "", "", "", "", ""]]

    (output / "crypto_research_opportunities.md").write_text(f"""# WRDS opportunities for crypto regime modelling

Project: **Feature Stability and Regime-Aware Prediction in Cryptocurrency Markets**

The ranking below is based on accessible WRDS libraries/tables discovered through
metadata queries. It does not imply that any dataset has been downloaded for
modelling.

## High relevance

{_table(['Library', 'Table', 'Categories', 'Date coverage', 'Frequency', 'Why relevant'], rows_for(high))}

## Medium relevance

{_table(['Library', 'Table', 'Categories', 'Date coverage', 'Frequency', 'Why relevant'], rows_for(medium))}

## Low relevance

{_table(['Library', 'Table', 'Categories', 'Date coverage', 'Frequency', 'Why relevant'], rows_for(low))}

## First download priorities

1. High-relevance macro/risk-regime series: equity indices, VIX/VVIX/MOVE-style
   volatility proxies, USD/DXY or broad-dollar series, Treasury/rates series.
2. Datastream/LSEG cross-asset daily series if licensed and accessible.
3. OptionMetrics/CBOE implied-risk aggregates only after broad macro series are
   normalized.
4. RavenPack/news and ETF/fund-flow data only if timestamp coverage and reporting
   delays can be documented.

Do not use these datasets in a strategy until the query, field definitions,
timestamp convention, release lag, and point-in-time availability are documented.
""", encoding="utf-8")

    (output / "feature_plan.md").write_text(f"""# Crypto-relevant WRDS feature plan

All WRDS features must be timestamped, lagged, and joined to the crypto decision
calendar before any trading experiment. The first use case should be regime
filtering, not return prediction.

{_table(['Feature group', 'WRDS source', 'Example features', 'Trading use', 'Leakage control'], [
    [row['feature_group'], row['wrds_source'], row['example_features'], row['trading_use'], row['leakage_control']]
    for row in FEATURE_PLAN_ROWS
])}

## Integration rules

1. Store downloaded WRDS data under `data/raw/wrds/` and normalized daily features
   under `data/processed/wrds/`.
2. Preserve vendor identifiers, query dates, and field descriptions.
3. Convert all timestamps to a documented decision calendar. For daily US market
   data, use at least a one-day lag before crypto allocation decisions.
4. For macro releases, use release dates or conservative lags. Do not use revised
   values as if they were known historically.
5. Keep the existing 2025+ evaluation period locked. If the hypothesis is refined
   after seeing that period, register a new prospective holdout.
""", encoding="utf-8")

    (output / "next_strategy_spec.md").write_text("""# Next strategy specification: Macro-Conditioned Crypto Exposure Strategy

## Objective

Test whether external macro/risk-regime data improves a simple BTC/ETH/cash
allocation without adding high turnover or opaque return-prediction models.

This is a design only. Do not backtest until WRDS data coverage is confirmed,
downloaded, normalized, lagged, and frozen.

## Universe

- Assets: BTC, ETH, cash.
- Direction: long-only spot exposure.
- Rebalance: weekly first; biweekly as robustness.
- Costs: 10, 25, 50, and 100 bps.
- Leverage: none.

## Required crypto-state features

- BTC 200-day trend.
- ETH 200-day trend.
- BTC and ETH 30/90-day momentum.
- Existing 7-day volatility-expansion probability.
- BTC/ETH drawdown state.

## Required WRDS/external-state features

- Equity risk trend: S&P 500 or Nasdaq above 200-day average; 30-day momentum.
- VIX regime: VIX level percentile and 5/20-day change.
- USD regime: DXY or broad-dollar trend and 20/60-day momentum.
- Rates regime: 2Y/10Y yield trend, real-yield change, or Fed-funds/SOFR pressure.
- Commodity/risk sentiment: gold, copper, oil, or copper/gold trend if available.
- Optional: ETF flow, RavenPack sentiment, and options-implied volatility only if
  coverage is timely and complete enough for weekly decisions.

## Candidate rules

1. Full exposure condition:
   - BTC or ETH trend is positive.
   - Equity risk trend is positive.
   - VIX is below its trailing high-risk percentile and not rising sharply.
   - USD trend is not strongly positive.
   - Rates shock filter is not hostile.
   - Crypto volatility-expansion probability is not in the high-risk bucket.
2. Asset selection:
   - Hold BTC/ETH 50/50 when both trends are favorable.
   - Tilt 70/30 toward the stronger 90-day volatility-adjusted momentum asset.
   - Hold only the stronger asset if the other is below its 200-day average.
3. Partial exposure condition:
   - If crypto trend is favorable but macro is mixed, hold 25-50% exposure and
     the rest cash.
4. Cash condition:
   - If crypto trend is negative or two or more macro risk filters are hostile,
     hold cash.
5. Drawdown control:
   - If strategy drawdown exceeds a predeclared threshold selected on development
     data only, reduce exposure by half until recovery.

## Why it may generalize

- It uses broad, economically motivated risk-regime variables rather than fitting
  a high-dimensional crypto return model.
- It trades only BTC/ETH/cash, reducing liquidity, survivorship, and execution
  complexity.
- Cash is an explicit state, which is necessary for surviving crypto bear markets.
- Weekly/biweekly cadence keeps turnover manageable.

## Why it may fail

- Macro variables may lag crypto regime changes.
- BTC/ETH can rally during hostile macro states, creating opportunity cost.
- Too many gates can over-filter and leave the strategy underexposed.
- WRDS datasets may be delayed, revised, or unavailable under the current license.

## Acceptance criteria before paper trading

- Candidate selected on development-only CPCV.
- No threshold selection on the locked evaluation period.
- Holdout CAGR above zero.
- Holdout Sharpe above 0.5.
- Max drawdown materially better than BTC buy-and-hold.
- Does not collapse at 50 bps.
- Annual turnover low enough for manual or simple bot execution.
""", encoding="utf-8")

    payload = {
        "status": result.status,
        "credential_status": asdict(result.credential_status),
        "wrds_package_available": result.wrds_package_available,
        "current_user_queried": bool(result.current_user),
        "library_count": len(result.libraries),
        "libraries": result.libraries,
        "table_counts_by_schema": result.table_counts_by_schema,
        "tables_by_library": result.tables_by_library,
        "scanned_libraries": result.scanned_libraries,
        "table_matches": [asdict(match) for match in result.table_matches],
        "table_details": [asdict(detail) for detail in result.table_details],
        "table_errors": result.table_errors,
        "candidate_datasets": [asdict(candidate) for candidate in result.candidates],
        "feature_plan": FEATURE_PLAN_ROWS,
        "notes": result.notes,
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output


def run_wrds_inventory(output_dir: str | Path = "reports/wrds_inventory", scan_all_tables: bool = True) -> WRDSInventoryResult:
    result = discover_wrds_inventory(scan_all_tables=scan_all_tables)
    write_wrds_reports(result, output_dir)
    return result


def run_wrds_inventory_with_optional_prompt(
    output_dir: str | Path = "reports/wrds_inventory",
    scan_all_tables: bool = True,
    prompt: bool = False,
    env_file: str | Path | None = DEFAULT_ENV_FILE,
) -> WRDSInventoryResult:
    env = merged_environment(env_file=env_file)
    if prompt and not credential_status(env).ready:
        env = prompt_for_credentials(env=env)
    result = discover_wrds_inventory(env=env, scan_all_tables=scan_all_tables)
    write_wrds_reports(result, output_dir)
    return result


__all__ = [
    "DATASET_CANDIDATES",
    "FEATURE_PLAN_ROWS",
    "WRDS_PASSWORD_ENV",
    "WRDS_USERNAME_ENV",
    "WRDSCredentialStatus",
    "WRDSInventoryResult",
    "credential_status",
    "discover_wrds_inventory",
    "load_env_file",
    "merged_environment",
    "prompt_for_credentials",
    "run_wrds_inventory",
    "run_wrds_inventory_with_optional_prompt",
    "write_wrds_reports",
]
