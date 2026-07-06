"""Public crypto-native data discovery, feature engineering, and one predeclared strategy.

The module intentionally avoids WRDS and avoids fabricating unavailable data.  It
uses public unauthenticated endpoints where possible and records coverage before
any strategy evaluation.  The only trading experiment is the predeclared
BTC/ETH/cash liquidity-conditioned exposure rule requested by the user.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .metrics import performance_metrics


COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEFILLAMA_BASE = "https://api.llama.fi"
DEFILLAMA_STABLECOINS_BASE = "https://stablecoins.llama.fi"
BINANCE_SPOT_BASE = "https://api.binance.com"
DEVELOPMENT_START = pd.Timestamp("2020-01-01")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")


@dataclass(frozen=True)
class PublicDataCoverage:
    dataset: str
    source: str
    status: str
    start: str | None
    end: str | None
    observations: int
    usable_for_strategy: bool
    limitation: str


@dataclass(frozen=True)
class LiquidityCandidate:
    name: str
    rebalance_days: int
    stablecoin_lookback_days: int
    volatility_probability_threshold: float
    market_drawdown_threshold: float
    volatility_target: float
    use_4h_confirmation: bool = True


@dataclass
class PublicDataBundle:
    coverage: pd.DataFrame
    stablecoins: pd.DataFrame
    chain_tvl: pd.DataFrame
    protocol_tvl: pd.DataFrame
    coingecko_markets: pd.DataFrame
    coingecko_categories: pd.DataFrame
    coingecko_coin_daily: pd.DataFrame
    binance_4h: pd.DataFrame
    binance_4h_daily_features: pd.DataFrame
    token_unlocks: pd.DataFrame
    metadata: dict[str, Any]


def _request_json(url: str, pause_seconds: float = 0.20) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "crypto-ml-research-public-data/1.0",
        },
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read().decode("utf-8")
            time.sleep(pause_seconds)
            return json.loads(payload)
        except Exception as exc:  # pragma: no cover - network-specific
            last_error = exc
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"request failed: {url}: {last_error}")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _date_from_seconds(value: Any) -> pd.Timestamp:
    return pd.to_datetime(int(float(value)), unit="s", utc=True).tz_localize(None).normalize()


def _date_from_ms(value: Any) -> pd.Timestamp:
    return pd.to_datetime(int(float(value)), unit="ms", utc=True).tz_localize(None)


def _nested_number(value: Any, *keys: str) -> float:
    current = value
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return np.nan
        current = current[key]
    try:
        return float(current)
    except Exception:
        return np.nan


def _coverage(
    dataset: str,
    source: str,
    status: str,
    frame: pd.DataFrame | None,
    date_column: str = "date",
    usable_for_strategy: bool = False,
    limitation: str = "",
) -> PublicDataCoverage:
    if frame is None or frame.empty or date_column not in frame:
        return PublicDataCoverage(dataset, source, status, None, None, 0, False, limitation)
    dates = pd.to_datetime(frame[date_column]).dropna()
    return PublicDataCoverage(
        dataset=dataset,
        source=source,
        status=status,
        start=str(dates.min().date()) if len(dates) else None,
        end=str(dates.max().date()) if len(dates) else None,
        observations=int(len(frame)),
        usable_for_strategy=usable_for_strategy,
        limitation=limitation,
    )


def parse_stablecoin_chart(payload: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in payload:
        rows.append({
            "date": _date_from_seconds(item["date"]),
            "stablecoin_supply": _nested_number(item, "totalCirculating", "peggedUSD"),
            "stablecoin_supply_usd": _nested_number(item, "totalCirculatingUSD", "peggedUSD"),
        })
    frame = pd.DataFrame(rows).dropna(subset=["date"]).sort_values("date")
    if frame.empty:
        return frame
    frame["stablecoin_supply"] = frame.stablecoin_supply.fillna(frame.stablecoin_supply_usd)
    frame["stablecoin_supply_usd"] = frame.stablecoin_supply_usd.fillna(frame.stablecoin_supply)
    for window in (7, 30, 90):
        frame[f"stablecoin_supply_change_{window}d"] = frame.stablecoin_supply_usd.pct_change(window, fill_method=None)
    frame["stablecoin_supply_z_90"] = (
        (frame.stablecoin_supply_usd - frame.stablecoin_supply_usd.rolling(90).mean())
        / frame.stablecoin_supply_usd.rolling(90).std()
    )
    return frame


def parse_chain_tvl(payload: list[dict[str, Any]], chain: str = "all") -> pd.DataFrame:
    rows = []
    for item in payload:
        rows.append({
            "date": _date_from_seconds(item["date"]),
            "chain": chain,
            "tvl": float(item.get("tvl", np.nan)),
        })
    frame = pd.DataFrame(rows).dropna(subset=["date"]).sort_values(["chain", "date"])
    if frame.empty:
        return frame
    frame["tvl_change_30d"] = frame.groupby("chain").tvl.pct_change(30, fill_method=None)
    frame["tvl_change_90d"] = frame.groupby("chain").tvl.pct_change(90, fill_method=None)
    return frame


def parse_protocols(payload: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in payload:
        rows.append({
            "name": item.get("name"),
            "category": item.get("category"),
            "chain": item.get("chain"),
            "tvl": item.get("tvl"),
            "change_1d": item.get("change_1d"),
            "change_7d": item.get("change_7d"),
            "change_1m": item.get("change_1m"),
        })
    return pd.DataFrame(rows)


def parse_coingecko_markets(payload: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    snapshot_date = pd.Timestamp.utcnow().tz_localize(None).normalize()
    for item in payload:
        rows.append({
            "date": snapshot_date,
            "id": item.get("id"),
            "symbol": str(item.get("symbol", "")).upper(),
            "name": item.get("name"),
            "market_cap": item.get("market_cap"),
            "circulating_supply": item.get("circulating_supply"),
            "total_supply": item.get("total_supply"),
            "volume": item.get("total_volume"),
            "rank": item.get("market_cap_rank"),
        })
    return pd.DataFrame(rows)


def parse_coingecko_categories(payload: list[dict[str, Any]]) -> pd.DataFrame:
    snapshot_date = pd.Timestamp.utcnow().tz_localize(None).normalize()
    rows = []
    for item in payload:
        rows.append({
            "date": snapshot_date,
            "category_id": item.get("id"),
            "name": item.get("name"),
            "market_cap": item.get("market_cap"),
            "volume_24h": item.get("volume_24h"),
            "market_cap_change_24h": item.get("market_cap_change_24h"),
        })
    return pd.DataFrame(rows)


def parse_coingecko_coin_daily(payload: dict[str, Any], coin_id: str, symbol: str) -> pd.DataFrame:
    def to_frame(name: str, column: str) -> pd.DataFrame:
        rows = payload.get(name, []) or []
        frame = pd.DataFrame(rows, columns=["timestamp", column])
        if frame.empty:
            return pd.DataFrame(columns=["date", column])
        frame["date"] = frame.timestamp.map(_date_from_ms).dt.normalize()
        return frame[["date", column]]

    frames = [
        to_frame("prices", "price"),
        to_frame("market_caps", "market_cap"),
        to_frame("total_volumes", "volume"),
    ]
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="date", how="outer")
    if merged.empty:
        return merged
    merged["coin_id"] = coin_id
    merged["symbol"] = symbol
    return merged.sort_values("date")


def fetch_binance_4h_ohlcv(
    symbol: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    pause_seconds: float = 0.05,
) -> pd.DataFrame:
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)
    cursor = start_ms
    rows: list[list[Any]] = []
    while cursor <= end_ms:
        params = urllib.parse.urlencode({
            "symbol": symbol,
            "interval": "4h",
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 1000,
        })
        batch = _request_json(f"{BINANCE_SPOT_BASE}/api/v3/klines?{params}", pause_seconds=pause_seconds)
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        next_cursor = int(batch[-1][0]) + 4 * 60 * 60 * 1000
        if next_cursor <= cursor:
            break
        cursor = next_cursor
    frame = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])
    if frame.empty:
        return frame
    for column in ("open", "high", "low", "close", "volume", "quote_volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["timestamp"] = frame.open_time.map(_date_from_ms)
    frame["date"] = frame.timestamp.dt.normalize()
    frame["symbol"] = symbol.replace("USDT", "")
    return frame[["timestamp", "date", "symbol", "open", "high", "low", "close", "volume", "quote_volume"]]


def build_4h_daily_features(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    rows = []
    for symbol, group in frame.sort_values("timestamp").groupby("symbol"):
        group = group.copy()
        returns = group.close.pct_change(fill_method=None)
        features = pd.DataFrame({
            "timestamp": group.timestamp,
            "date": group.date,
            "symbol": symbol,
            "close_4h": group.close,
            "trend_4h_7d": group.close.pct_change(42, fill_method=None),
            "trend_4h_14d": group.close.pct_change(84, fill_method=None),
            "volatility_4h_7d": returns.rolling(42).std() * np.sqrt(6 * 365),
            "volatility_4h_30d": returns.rolling(180).std() * np.sqrt(6 * 365),
            "drawdown_4h_30d": group.close / group.close.rolling(180).max() - 1,
            "volume_shock_4h": np.log1p(group.quote_volume) - np.log1p(group.quote_volume.rolling(42).median()),
        })
        daily = features.groupby("date").tail(1).copy()
        feature_columns = [
            "trend_4h_7d", "trend_4h_14d", "volatility_4h_7d",
            "volatility_4h_30d", "drawdown_4h_30d", "volume_shock_4h",
        ]
        daily[feature_columns] = daily[feature_columns].shift(1)
        rows.append(daily[["date", "symbol", *feature_columns]])
    return pd.concat(rows, ignore_index=True).sort_values(["date", "symbol"])


def download_public_crypto_data(
    raw_dir: str | Path = "data/raw/public_crypto",
    processed_dir: str | Path = "data/processed/public_crypto",
    start: str = "2019-01-01",
    end: str | pd.Timestamp = HOLDOUT_END,
    token_unlocks_csv: str | Path | None = None,
) -> PublicDataBundle:
    raw = Path(raw_dir)
    processed = Path(processed_dir)
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    coverage: list[PublicDataCoverage] = []

    stablecoins = pd.DataFrame()
    chain_tvl_frames: list[pd.DataFrame] = []
    protocol_tvl = pd.DataFrame()
    markets = pd.DataFrame()
    categories = pd.DataFrame()
    coin_daily_frames: list[pd.DataFrame] = []
    binance_frames: list[pd.DataFrame] = []
    token_unlocks = pd.DataFrame()

    try:
        payload = _request_json(f"{DEFILLAMA_STABLECOINS_BASE}/stablecoincharts/all")
        _write_json(raw / "defillama_stablecoincharts_all.json", payload)
        stablecoins = parse_stablecoin_chart(payload)
        stablecoins.to_csv(processed / "defillama_stablecoin_daily.csv", index=False)
        coverage.append(_coverage(
            "stablecoin_supply", "DefiLlama stablecoincharts/all", "available", stablecoins,
            usable_for_strategy=not stablecoins.empty and stablecoins.date.min() <= DEVELOPMENT_START,
            limitation="Free public endpoint; aggregate stablecoin supply only, not exchange-specific liquidity.",
        ))
    except Exception as exc:
        coverage.append(_coverage("stablecoin_supply", "DefiLlama stablecoincharts/all", f"failed: {exc}", None))

    for chain, url in {
        "all": f"{DEFILLAMA_BASE}/v2/historicalChainTvl",
        "Ethereum": f"{DEFILLAMA_BASE}/v2/historicalChainTvl/Ethereum",
        "Solana": f"{DEFILLAMA_BASE}/v2/historicalChainTvl/Solana",
        "Tron": f"{DEFILLAMA_BASE}/v2/historicalChainTvl/Tron",
        "Arbitrum": f"{DEFILLAMA_BASE}/v2/historicalChainTvl/Arbitrum",
        "Base": f"{DEFILLAMA_BASE}/v2/historicalChainTvl/Base",
    }.items():
        try:
            payload = _request_json(url)
            _write_json(raw / f"defillama_chain_tvl_{chain.lower()}.json", payload)
            frame = parse_chain_tvl(payload, chain)
            chain_tvl_frames.append(frame)
            coverage.append(_coverage(
                f"chain_tvl_{chain}", "DefiLlama historicalChainTvl", "available", frame,
                usable_for_strategy=False,
                limitation="Useful for feature research; not used in the first predeclared BTC/ETH/cash strategy.",
            ))
        except Exception as exc:
            coverage.append(_coverage(f"chain_tvl_{chain}", "DefiLlama historicalChainTvl", f"failed: {exc}", None))
    chain_tvl = pd.concat(chain_tvl_frames, ignore_index=True) if chain_tvl_frames else pd.DataFrame()
    if not chain_tvl.empty:
        chain_tvl.to_csv(processed / "defillama_chain_tvl_daily.csv", index=False)

    try:
        payload = _request_json(f"{DEFILLAMA_BASE}/protocols")
        _write_json(raw / "defillama_protocols.json", payload)
        protocol_tvl = parse_protocols(payload)
        protocol_tvl.to_csv(processed / "defillama_protocols_current.csv", index=False)
        coverage.append(PublicDataCoverage(
            "protocol_tvl_current", "DefiLlama protocols", "available", None, None,
            int(len(protocol_tvl)), False,
            "Current protocol metadata only in this module; not sufficient alone for locked historical trading.",
        ))
    except Exception as exc:
        coverage.append(_coverage("protocol_tvl_current", "DefiLlama protocols", f"failed: {exc}", None))

    try:
        global_payload = _request_json(f"{COINGECKO_BASE}/global")
        _write_json(raw / "coingecko_global.json", global_payload)
        coverage.append(PublicDataCoverage(
            "global_market_snapshot", "CoinGecko /global", "available", str(pd.Timestamp.utcnow().date()),
            str(pd.Timestamp.utcnow().date()), 1, False,
            "Current snapshot only; useful for dominance proxy documentation, not historical strategy selection.",
        ))
    except Exception as exc:
        coverage.append(_coverage("global_market_snapshot", "CoinGecko /global", f"failed: {exc}", None))

    try:
        params = urllib.parse.urlencode({
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 250,
            "page": 1,
            "sparkline": "false",
        })
        payload = _request_json(f"{COINGECKO_BASE}/coins/markets?{params}")
        _write_json(raw / "coingecko_markets_top250.json", payload)
        markets = parse_coingecko_markets(payload)
        markets.to_csv(processed / "coingecko_markets_current.csv", index=False)
        coverage.append(_coverage(
            "coin_market_cap_supply_volume", "CoinGecko /coins/markets", "available", markets,
            usable_for_strategy=False,
            limitation="Current top-250 snapshot; not point-in-time enough for historical top-universe backtests.",
        ))
    except Exception as exc:
        coverage.append(_coverage("coin_market_cap_supply_volume", "CoinGecko /coins/markets", f"failed: {exc}", None))

    try:
        payload = _request_json(f"{COINGECKO_BASE}/coins/categories")
        _write_json(raw / "coingecko_categories.json", payload)
        categories = parse_coingecko_categories(payload)
        categories.to_csv(processed / "coingecko_categories_current.csv", index=False)
        coverage.append(_coverage(
            "coin_categories", "CoinGecko /coins/categories", "available", categories,
            usable_for_strategy=False,
            limitation="Current category/sector snapshot; historical category membership needs vendor support or frozen snapshots.",
        ))
    except Exception as exc:
        coverage.append(_coverage("coin_categories", "CoinGecko /coins/categories", f"failed: {exc}", None))

    start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
    end_ts = int(pd.Timestamp(end, tz="UTC").timestamp())
    for coin_id, symbol in (("bitcoin", "BTC"), ("ethereum", "ETH")):
        try:
            params = urllib.parse.urlencode({"vs_currency": "usd", "from": start_ts, "to": end_ts})
            payload = _request_json(f"{COINGECKO_BASE}/coins/{coin_id}/market_chart/range?{params}", pause_seconds=1.2)
            _write_json(raw / f"coingecko_{coin_id}_market_chart.json", payload)
            frame = parse_coingecko_coin_daily(payload, coin_id, symbol)
            coin_daily_frames.append(frame)
            coverage.append(_coverage(
                f"{symbol}_market_cap_volume_history", "CoinGecko market_chart/range", "available", frame,
                usable_for_strategy=False,
                limitation="BTC/ETH only in this module; used for feature planning and cross-checks, not the first strategy rule.",
            ))
        except Exception as exc:
            coverage.append(_coverage(f"{symbol}_market_cap_volume_history", "CoinGecko market_chart/range", f"failed: {exc}", None))
    coingecko_coin_daily = pd.concat(coin_daily_frames, ignore_index=True) if coin_daily_frames else pd.DataFrame()
    if not coingecko_coin_daily.empty:
        coingecko_coin_daily.to_csv(processed / "coingecko_coin_market_daily.csv", index=False)

    for symbol in ("BTCUSDT", "ETHUSDT"):
        try:
            frame = fetch_binance_4h_ohlcv(symbol, start, end)
            binance_frames.append(frame)
            coverage.append(_coverage(
                f"{symbol}_4h_ohlcv", "Binance spot klines 4h", "available", frame,
                usable_for_strategy=not frame.empty and frame.date.min() <= DEVELOPMENT_START,
                limitation="Exchange-specific public 4h spot bars; no order book or cross-exchange aggregation.",
            ))
        except Exception as exc:
            coverage.append(_coverage(f"{symbol}_4h_ohlcv", "Binance spot klines 4h", f"failed: {exc}", None))
    binance_4h = pd.concat(binance_frames, ignore_index=True) if binance_frames else pd.DataFrame()
    binance_features = build_4h_daily_features(binance_4h) if not binance_4h.empty else pd.DataFrame()
    if not binance_4h.empty:
        binance_4h.to_csv(processed / "binance_btc_eth_4h_ohlcv.csv", index=False)
    if not binance_features.empty:
        binance_features.to_csv(processed / "binance_btc_eth_4h_daily_features.csv", index=False)

    if token_unlocks_csv and Path(token_unlocks_csv).exists():
        token_unlocks = pd.read_csv(token_unlocks_csv, parse_dates=["date"])
        token_unlocks.to_csv(processed / "token_unlocks.csv", index=False)
        coverage.append(_coverage(
            "token_unlocks", str(token_unlocks_csv), "available", token_unlocks,
            usable_for_strategy=False,
            limitation="User-supplied file; this module found no reliable unauthenticated public token-unlock API.",
        ))
    else:
        coverage.append(PublicDataCoverage(
            "token_unlocks", "Token unlock public APIs", "unavailable", None, None, 0, False,
            "No reliable unauthenticated official/public endpoint was integrated; no synthetic unlock data created.",
        ))

    coverage_frame = pd.DataFrame([asdict(item) for item in coverage])
    coverage_frame.to_csv(processed / "coverage.csv", index=False)
    return PublicDataBundle(
        coverage=coverage_frame,
        stablecoins=stablecoins,
        chain_tvl=chain_tvl,
        protocol_tvl=protocol_tvl,
        coingecko_markets=markets,
        coingecko_categories=categories,
        coingecko_coin_daily=coingecko_coin_daily,
        binance_4h=binance_4h,
        binance_4h_daily_features=binance_features,
        token_unlocks=token_unlocks,
        metadata={
            "raw_dir": str(raw),
            "processed_dir": str(processed),
            "start": str(pd.Timestamp(start).date()),
            "end": str(pd.Timestamp(end).date()),
        },
    )


def load_processed_public_data(processed_dir: str | Path = "data/processed/public_crypto") -> PublicDataBundle:
    processed = Path(processed_dir)
    def read_csv(name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
        path = processed / name
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path, parse_dates=parse_dates or [])
    coverage = read_csv("coverage.csv")
    return PublicDataBundle(
        coverage=coverage,
        stablecoins=read_csv("defillama_stablecoin_daily.csv", ["date"]),
        chain_tvl=read_csv("defillama_chain_tvl_daily.csv", ["date"]),
        protocol_tvl=read_csv("defillama_protocols_current.csv"),
        coingecko_markets=read_csv("coingecko_markets_current.csv", ["date"]),
        coingecko_categories=read_csv("coingecko_categories_current.csv", ["date"]),
        coingecko_coin_daily=read_csv("coingecko_coin_market_daily.csv", ["date"]),
        binance_4h=read_csv("binance_btc_eth_4h_ohlcv.csv", ["timestamp", "date"]),
        binance_4h_daily_features=read_csv("binance_btc_eth_4h_daily_features.csv", ["date"]),
        token_unlocks=read_csv("token_unlocks.csv", ["date"]),
        metadata={"processed_dir": str(processed)},
    )


def liquidity_candidates() -> list[LiquidityCandidate]:
    return [
        LiquidityCandidate("weekly_stable30_vol80_dd25", 7, 30, 0.80, -0.25, 0.35),
        LiquidityCandidate("weekly_stable90_vol80_dd25", 7, 90, 0.80, -0.25, 0.35),
        LiquidityCandidate("biweekly_stable30_vol80_dd25", 14, 30, 0.80, -0.25, 0.35),
        LiquidityCandidate("biweekly_stable90_vol85_dd30", 14, 90, 0.85, -0.30, 0.35),
    ]


def _load_volatility_probability(path: str | Path) -> pd.Series | None:
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


def _btc_eth_returns(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    clean = panel[panel.symbol.isin(["BTC", "ETH"])].copy()
    close = clean.pivot(index="date", columns="symbol", values="close").sort_index()
    returns = close.pct_change(fill_method=None).fillna(0.0)
    return close, returns


def _market_state(
    panel: pd.DataFrame,
    stablecoins: pd.DataFrame,
    features_4h: pd.DataFrame,
    volatility_probability: pd.Series | None,
) -> pd.DataFrame:
    close, returns = _btc_eth_returns(panel)
    state = pd.DataFrame(index=close.index)
    for symbol in ("BTC", "ETH"):
        if symbol not in close:
            continue
        state[f"{symbol}_momentum_90"] = close[symbol].pct_change(90, fill_method=None).shift(1)
        state[f"{symbol}_distance_ma_200"] = close[symbol].shift(1) / close[symbol].rolling(200).mean().shift(1) - 1
        state[f"{symbol}_realized_vol_30"] = returns[symbol].rolling(30).std().shift(1) * np.sqrt(365)
    basket = returns.reindex(columns=["BTC", "ETH"]).mean(axis=1)
    wealth = (1 + basket.fillna(0.0)).cumprod()
    state["market_drawdown"] = (wealth / wealth.cummax() - 1).shift(1)

    stable = stablecoins.set_index("date").sort_index() if not stablecoins.empty else pd.DataFrame()
    for column in ("stablecoin_supply", "stablecoin_supply_usd", "stablecoin_supply_change_30d", "stablecoin_supply_change_90d", "stablecoin_supply_z_90"):
        state[column] = stable[column].reindex(state.index).ffill().shift(1) if column in stable else np.nan

    if volatility_probability is not None:
        state["volatility_expansion_probability"] = volatility_probability.reindex(state.index).ffill().shift(1)
    else:
        state["volatility_expansion_probability"] = 0.50
    state["volatility_expansion_probability"] = state.volatility_expansion_probability.fillna(0.50)

    if not features_4h.empty:
        for symbol in ("BTC", "ETH"):
            f = features_4h[features_4h.symbol == symbol].set_index("date").sort_index()
            state[f"{symbol}_trend_4h_7d"] = f.trend_4h_7d.reindex(state.index).ffill()
            state[f"{symbol}_drawdown_4h_30d"] = f.drawdown_4h_30d.reindex(state.index).ffill()
            state[f"{symbol}_volume_shock_4h"] = f.volume_shock_4h.reindex(state.index).ffill()
    return state


def build_liquidity_conditioned_weights(
    panel: pd.DataFrame,
    stablecoins: pd.DataFrame,
    features_4h: pd.DataFrame,
    volatility_probability: pd.Series | None,
    candidate: LiquidityCandidate,
) -> pd.DataFrame:
    close, _ = _btc_eth_returns(panel)
    state = _market_state(panel, stablecoins, features_4h, volatility_probability)
    rebalance_dates = pd.DatetimeIndex(close.resample(f"{candidate.rebalance_days}D").last().index)
    rebalance_dates = rebalance_dates.intersection(close.index)
    weights = pd.DataFrame(0.0, index=rebalance_dates, columns=["BTC", "ETH"])
    stable_column = f"stablecoin_supply_change_{candidate.stablecoin_lookback_days}d"

    for date_ in rebalance_dates:
        if date_ not in state.index:
            continue
        row = state.loc[date_]
        stable_expanding = bool(row.get(stable_column, np.nan) > 0)
        drawdown_ok = bool(row.get("market_drawdown", np.nan) > candidate.market_drawdown_threshold)
        vol_ok = bool(row.get("volatility_expansion_probability", 0.50) < candidate.volatility_probability_threshold)
        if not (stable_expanding and drawdown_ok and vol_ok):
            continue
        eligible = []
        vols = []
        for symbol in ("BTC", "ETH"):
            trend_ok = bool(
                row.get(f"{symbol}_momentum_90", np.nan) > 0
                and row.get(f"{symbol}_distance_ma_200", np.nan) > 0
            )
            if candidate.use_4h_confirmation and f"{symbol}_trend_4h_7d" in state.columns:
                trend_ok = trend_ok and bool(row.get(f"{symbol}_trend_4h_7d", np.nan) > 0)
            if trend_ok:
                eligible.append(symbol)
                vols.append(row.get(f"{symbol}_realized_vol_30", np.nan))
        if not eligible:
            continue
        realized = pd.Series(vols).replace([np.inf, -np.inf], np.nan).dropna()
        exposure = 1.0
        if not realized.empty and realized.mean() > 0:
            exposure = float(np.clip(candidate.volatility_target / realized.mean(), 0.25, 1.0))
        allocation = exposure / len(eligible)
        weights.loc[date_, eligible] = allocation
    return weights


def backtest_daily_weights(
    panel: pd.DataFrame,
    target_weights: pd.DataFrame,
    cost_bps: int,
    end: pd.Timestamp = HOLDOUT_END,
) -> dict[str, Any]:
    _, returns = _btc_eth_returns(panel)
    start = target_weights.index.min()
    returns = returns.loc[start:min(end, returns.index.max()), ["BTC", "ETH"]].fillna(0.0)
    targets = target_weights.reindex(target_weights.index.intersection(returns.index)).fillna(0.0)
    executed = pd.DataFrame(0.0, index=returns.index, columns=["BTC", "ETH"])
    gross = pd.Series(0.0, index=returns.index)
    net = pd.Series(0.0, index=returns.index)
    turnover = pd.Series(0.0, index=returns.index)
    costs = pd.Series(0.0, index=returns.index)
    previous = pd.Series(0.0, index=["BTC", "ETH"])
    for date_ in returns.index:
        gross.at[date_] = float((previous * returns.loc[date_]).sum())
        target = previous.copy()
        if date_ in targets.index:
            target = targets.loc[date_].reindex(previous.index).fillna(0.0)
            turnover.at[date_] = float((target - previous).abs().sum())
            costs.at[date_] = turnover.at[date_] * cost_bps / 10000.0
        net.at[date_] = gross.at[date_] - costs.at[date_]
        executed.loc[date_] = target
        previous = target
    metrics = _portfolio_metrics(net, turnover, costs, executed)
    return {
        "returns": net,
        "gross_returns": gross,
        "weights": executed,
        "turnover": turnover,
        "costs": costs,
        "metrics": metrics,
    }


def _portfolio_metrics(
    returns: pd.Series,
    turnover: pd.Series,
    costs: pd.Series,
    weights: pd.DataFrame,
) -> dict[str, float]:
    metrics = performance_metrics(returns, turnover, costs)
    elapsed_years = max(len(returns) / 365.0, 1 / 365.0)
    exposure = weights.sum(axis=1).clip(0, 1)
    monthly = returns.resample("ME").apply(lambda values: (1 + values).prod() - 1)
    metrics.update({
        "Exposure": float(exposure.mean()),
        "Cash Allocation": float(1 - exposure.mean()),
        "Annual Turnover": float(turnover.sum() / elapsed_years),
        "Worst Month": float(monthly.min()) if len(monthly) else np.nan,
        "Best Month": float(monthly.max()) if len(monthly) else np.nan,
    })
    return metrics


def period_metrics(result: dict[str, Any], start: str | pd.Timestamp, end: str | pd.Timestamp) -> dict[str, float]:
    returns = result["returns"].loc[pd.Timestamp(start):pd.Timestamp(end)]
    return _portfolio_metrics(
        returns,
        result["turnover"].reindex(returns.index).fillna(0.0),
        result["costs"].reindex(returns.index).fillna(0.0),
        result["weights"].reindex(returns.index).fillna(0.0),
    )


def benchmark_weights(panel: pd.DataFrame, name: str) -> pd.DataFrame:
    close, _ = _btc_eth_returns(panel)
    weights = pd.DataFrame(0.0, index=close.index, columns=["BTC", "ETH"])
    if name == "btc_buy_hold":
        weights["BTC"] = 1.0
    elif name == "eth_buy_hold":
        weights["ETH"] = 1.0
    elif name == "btc_eth_50_50":
        weights.loc[:, ["BTC", "ETH"]] = 0.50
    else:
        raise ValueError(name)
    return weights


def run_liquidity_conditioned_strategy(
    panel: pd.DataFrame,
    public_data: PublicDataBundle,
    volatility_predictions_path: str | Path = "reports/volatility_expansion/predictions.csv",
) -> dict[str, Any]:
    if public_data.stablecoins.empty:
        return {"available": False, "reason": "stablecoin history unavailable"}
    if public_data.stablecoins.date.min() > DEVELOPMENT_START:
        return {"available": False, "reason": "stablecoin history starts after the development period"}
    close, _ = _btc_eth_returns(panel)
    if not {"BTC", "ETH"}.issubset(close.columns):
        return {"available": False, "reason": "BTC/ETH daily price data unavailable"}
    probability = _load_volatility_probability(volatility_predictions_path)
    candidates = liquidity_candidates()
    rows = []
    results: dict[tuple[str, int], dict[str, Any]] = {}
    weights_by_candidate = {}
    for candidate in candidates:
        weights = build_liquidity_conditioned_weights(
            panel, public_data.stablecoins, public_data.binance_4h_daily_features,
            probability, candidate,
        )
        weights_by_candidate[candidate.name] = weights
        result_25 = backtest_daily_weights(panel, weights, 25)
        results[(candidate.name, 25)] = result_25
        dev = period_metrics(result_25, DEVELOPMENT_START, DEVELOPMENT_END)
        rows.append({
            "name": candidate.name,
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
        })
    selection = pd.DataFrame(rows).sort_values(
        ["development_sharpe", "development_cagr", "development_turnover"],
        ascending=[False, False, True],
    )
    selected_name = str(selection.iloc[0].name if False else selection.iloc[0]["name"])
    for cost in COST_LEVELS:
        if (selected_name, cost) not in results:
            results[(selected_name, cost)] = backtest_daily_weights(panel, weights_by_candidate[selected_name], cost)

    metrics_rows = []
    for cost in COST_LEVELS:
        selected_result = results[(selected_name, cost)]
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            metrics_rows.append({"name": selected_name, "category": "strategy", "split": split, "cost_bps": cost, **period_metrics(selected_result, start, end)})

    for bench in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50"):
        result = backtest_daily_weights(panel, benchmark_weights(panel, bench), 0)
        for split, start, end in (
            ("development", DEVELOPMENT_START, DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            metrics_rows.append({"name": bench, "category": "benchmark", "split": split, "cost_bps": 0, **period_metrics(result, start, end)})

    metrics = pd.DataFrame(metrics_rows)
    holdout_25 = metrics[(metrics.name == selected_name) & (metrics.split == "holdout") & (metrics.cost_bps == 25)].iloc[0]
    holdout_50 = metrics[(metrics.name == selected_name) & (metrics.split == "holdout") & (metrics.cost_bps == 50)].iloc[0]
    btc_holdout = metrics[(metrics.name == "btc_buy_hold") & (metrics.split == "holdout")].iloc[0]
    failures = []
    if holdout_25.Sharpe <= 0.50:
        failures.append("holdout Sharpe <= 0.5")
    if holdout_25.CAGR <= 0:
        failures.append("holdout CAGR <= 0")
    if holdout_25["Maximum Drawdown"] <= btc_holdout["Maximum Drawdown"]:
        failures.append("drawdown not better than BTC")
    if holdout_50.Sharpe <= 0 or holdout_50.CAGR <= 0:
        failures.append("does not survive 50 bps")
    if holdout_25["Annual Turnover"] > 12:
        failures.append("turnover above 12x/year")

    return {
        "available": True,
        "candidates": pd.DataFrame([asdict(candidate) for candidate in candidates]),
        "selection": selection,
        "selected_name": selected_name,
        "metrics": metrics,
        "acceptance": {
            "name": selected_name,
            "passes": not failures,
            "failures": "; ".join(failures),
            "holdout_sharpe": float(holdout_25.Sharpe),
            "holdout_cagr": float(holdout_25.CAGR),
            "holdout_max_drawdown": float(holdout_25["Maximum Drawdown"]),
            "holdout_turnover": float(holdout_25["Annual Turnover"]),
        },
    }


def _format(value: Any, percent: bool = False) -> str:
    if value is None or (isinstance(value, (float, np.floating)) and not np.isfinite(value)):
        return "N/A"
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if value else "No"
    if isinstance(value, (float, np.floating)):
        return f"{value:.2%}" if percent else f"{value:.3f}"
    return str(value)


def _markdown_table(frame: pd.DataFrame, columns: list[tuple[str, str]], percent: set[str] | None = None) -> str:
    percent = percent or set()
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in frame.to_dict("records"):
        lines.append("| " + " | ".join(_format(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def write_public_crypto_reports(
    output_dir: str | Path,
    data: PublicDataBundle,
    strategy_result: dict[str, Any] | None = None,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    coverage = data.coverage if not data.coverage.empty else pd.DataFrame()
    coverage_table = _markdown_table(
        coverage,
        [("dataset", "Dataset"), ("source", "Source"), ("status", "Status"), ("start", "Start"), ("end", "End"), ("observations", "N"), ("usable_for_strategy", "Strategy usable"), ("limitation", "Limitation")],
    ) if not coverage.empty else "No public data coverage was recorded."

    (output / "data_inventory.md").write_text(f"""# Public crypto-native data inventory

WRDS is excluded from this module. Public data is used only when fetched from
unauthenticated public endpoints or supplied as a local file. Missing public
token-unlock data is reported as unavailable; no synthetic unlock series is
created.

## Endpoint coverage

{coverage_table}

## Source-specific interpretation

- **CoinGecko:** supports market cap, supply, volume, category, and global market
  snapshots. Current category membership is useful for research design, but
  historical category membership should be snapshotted prospectively before
  use in point-in-time backtests.
- **DefiLlama:** stablecoin aggregate supply and chain TVL are accessible and
  directly relevant for crypto liquidity/risk-regime features.
- **Token unlocks:** no reliable unauthenticated public endpoint was integrated.
  Use a licensed source or manually versioned file before testing unlock-driven
  hypotheses.
- **Binance 4h:** BTC/ETH 4h spot bars are accessible and converted into lagged
  daily trend, volatility, drawdown, and volume-shock features.

## Files written

- `data/processed/public_crypto/coverage.csv`
- `data/processed/public_crypto/defillama_stablecoin_daily.csv`
- `data/processed/public_crypto/defillama_chain_tvl_daily.csv`
- `data/processed/public_crypto/defillama_protocols_current.csv`
- `data/processed/public_crypto/coingecko_markets_current.csv`
- `data/processed/public_crypto/coingecko_categories_current.csv`
- `data/processed/public_crypto/coingecko_coin_market_daily.csv`
- `data/processed/public_crypto/binance_btc_eth_4h_ohlcv.csv`
- `data/processed/public_crypto/binance_btc_eth_4h_daily_features.csv`
""", encoding="utf-8")

    (output / "feature_plan.md").write_text("""# Public crypto-native feature plan

All features must be lagged before trading decisions. The first use case is
risk timing for BTC/ETH/cash, not broad altcoin selection.

| Feature family | Source | Example features | Rationale | Leakage control |
|---|---|---|---|---|
| Stablecoin liquidity | DefiLlama stablecoincharts/all | aggregate supply, 7/30/90-day supply change, supply z-score | Stablecoin expansion can proxy crypto-native liquidity and collateral availability. | Use previous day's published aggregate value; no same-day rebalance value. |
| DeFi liquidity | DefiLlama chain/protocol TVL | total TVL trend, Ethereum/Solana/Tron TVL change, protocol category TVL | TVL contraction can identify liquidity withdrawal and risk-off conditions. | Lag daily TVL; avoid current protocol snapshots in historical tests unless snapshotted. |
| Coin market structure | CoinGecko markets/global | BTC/ETH dominance, market cap, circulating supply, volume | Dominance and capitalization can identify concentration and speculative regime. | Historical features need market_chart/range or prospective snapshots; current categories are not point-in-time. |
| Categories/sectors | CoinGecko categories | sector market-cap/volume share, category momentum | Helps design sector/breadth hypotheses after point-in-time snapshots exist. | Do not backfill today's categories into prior dates. |
| Token unlock pressure | External unlock source or local file | unlock size / market cap, days to unlock, emission pressure | Supply overhang can impair altcoin momentum and risk appetite. | Requires timestamped, point-in-time unlock calendar; unavailable data is not imputed. |
| 4h BTC/ETH state | Binance spot klines | 4h trend, realized volatility, drawdown, volume shock | Intraday risk state can detect deterioration before weekly rebalance. | Aggregate to daily and shift one day before weekly/biweekly allocation. |

Recommended first engineered features:

1. `stablecoin_supply_change_30d` and `stablecoin_supply_change_90d`.
2. Stablecoin expansion dummy: change greater than zero.
3. Total DeFi TVL 30/90-day change.
4. BTC/ETH 4h 7-day trend confirmation.
5. BTC/ETH 4h 30-day drawdown.
6. BTC/ETH 4h volume shock.
7. BTC/ETH dominance proxy from CoinGecko global snapshots once a history is built.
""", encoding="utf-8")

    (output / "hypothesis_library.md").write_text("""# Public crypto-native hypothesis library

These are research hypotheses, not strategy results.

| Hypothesis | Data required | Test design | Expected failure mode |
|---|---|---|---|
| Stablecoin liquidity expansion improves BTC/ETH timing | DefiLlama aggregate stablecoin supply | Compare BTC/ETH trend exposure with and without stablecoin expansion gate. | Stablecoin growth may lag price rallies or reflect flight-to-cash rather than risk appetite. |
| TVL contraction identifies hostile crypto liquidity regimes | DefiLlama chain/protocol TVL | Add TVL trend/drawdown gate to BTC/ETH/cash system. | TVL is DeFi-specific and may miss centralized-exchange liquidity. |
| 4h BTC/ETH deterioration improves weekly drawdown control | Binance 4h klines | Require positive 4h trend and limited 4h drawdown before weekly exposure. | Intraday filters can overreact and reduce exposure during profitable recoveries. |
| BTC/ETH dominance shifts predict altcoin fragility | CoinGecko global/dominance snapshots | Use dominance trend as a risk-off feature for altcoin baskets after historical snapshots exist. | Current CoinGecko category/dominance snapshots are insufficient for point-in-time backtests unless stored prospectively. |
| Token unlock pressure weakens asset-level momentum | Token unlock calendar | Exclude assets with large upcoming unlocks as % market cap. | Public unlock data may be incomplete, revised, or unavailable without a licensed provider. |

The first tradable hypothesis is deliberately narrow: stablecoin liquidity plus
BTC/ETH trend and drawdown controls for BTC/ETH/cash only.
""", encoding="utf-8")

    (output / "next_strategy_spec.md").write_text("""# Next strategy specification: Stablecoin and Market-Liquidity Conditioned BTC/ETH Exposure

## Scope

- Assets: BTC, ETH, cash.
- Direction: long-only spot.
- Rebalance: weekly or biweekly, selected on development data only.
- Costs: 10, 25, 50, 100 bps.
- No leverage.
- No broad strategy search.

## Predeclared exposure rule

At each rebalance date, hold BTC and/or ETH only if all gates are satisfied:

1. Asset trend is positive: 90-day momentum > 0 and price > 200-day moving average.
2. 4h confirmation is positive when available: lagged 4h 7-day trend > 0.
3. Stablecoin liquidity is expanding over the candidate lookback window.
4. BTC/ETH basket drawdown is not worse than the candidate drawdown threshold.
5. Existing volatility-expansion probability is below the candidate high-risk threshold.

If no asset is eligible or any market gate fails, hold cash.

## Development-only candidate set

- weekly, 30-day stablecoin expansion, vol-risk threshold 0.80, drawdown threshold -25%.
- weekly, 90-day stablecoin expansion, vol-risk threshold 0.80, drawdown threshold -25%.
- biweekly, 30-day stablecoin expansion, vol-risk threshold 0.80, drawdown threshold -25%.
- biweekly, 90-day stablecoin expansion, vol-risk threshold 0.85, drawdown threshold -30%.

The selected candidate is the highest development Sharpe, breaking ties by
development CAGR and then lower turnover. The locked 2025-2026 evaluation is not
used for selection.

## Acceptance criteria

- Holdout Sharpe > 0.5.
- Holdout CAGR > 0.
- Holdout drawdown better than BTC buy-and-hold.
- Positive Sharpe and CAGR at 50 bps.
- Annual turnover not above 12x.
""", encoding="utf-8")

    if strategy_result and strategy_result.get("available"):
        metrics = strategy_result["metrics"]
        selection = strategy_result["selection"]
        candidates = strategy_result["candidates"]
        acceptance = strategy_result["acceptance"]
        selected = strategy_result["selected_name"]
        holdout = metrics[(metrics.split == "holdout") & ((metrics.cost_bps == 25) | (metrics.category == "benchmark"))].sort_values("Sharpe", ascending=False)
        development = metrics[(metrics.split == "development") & ((metrics.cost_bps == 25) | (metrics.category == "benchmark"))].sort_values("Sharpe", ascending=False)
        prior_path = Path("reports/paper_trading_candidate/metrics.csv")
        prior_text = "Previous defensive-candidate metrics were not found."
        if prior_path.exists():
            prior = pd.read_csv(prior_path)
            prior_holdout = prior[(prior.split == "holdout") & (prior.cost_bps == 25)].sort_values("Sharpe", ascending=False).head(8)
            prior_text = _markdown_table(prior_holdout, [("name", "Prior strategy"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Maximum Drawdown", "Max DD"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure")], {"CAGR", "Maximum Drawdown", "Exposure"})
        columns = [("name", "Strategy"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Sortino", "Sortino"), ("Maximum Drawdown", "Max DD"), ("Calmar", "Calmar"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure"), ("Worst Month", "Worst month")]
        percent = {"CAGR", "Maximum Drawdown", "Exposure", "Worst Month"}
        (output / "strategy_results.md").write_text(f"""# Stablecoin and market-liquidity conditioned strategy results

The strategy was run because DefiLlama stablecoin history, Binance 4h BTC/ETH
data, and BTC/ETH daily price data were accessible. Candidate selection used
development data only.

## Candidate selection

Selected candidate: **{selected}**

{_markdown_table(selection, [("name", "Candidate"), ("development_sharpe", "Development Sharpe"), ("development_cagr", "Development CAGR"), ("development_max_drawdown", "Development max DD"), ("development_turnover", "Development turnover"), ("development_exposure", "Development exposure")], {"development_cagr", "development_max_drawdown", "development_exposure"})}

## Candidate definitions

{_markdown_table(candidates, [("name", "Candidate"), ("rebalance_days", "Rebalance days"), ("stablecoin_lookback_days", "Stablecoin lookback"), ("volatility_probability_threshold", "Vol threshold"), ("market_drawdown_threshold", "Drawdown threshold"), ("volatility_target", "Vol target"), ("use_4h_confirmation", "4h confirm")], {"market_drawdown_threshold", "volatility_target"})}

## Development comparison

{_markdown_table(development, columns, percent)}

## Locked 2025-2026 holdout comparison

{_markdown_table(holdout, columns, percent)}

## Cost sensitivity for selected candidate

{_markdown_table(metrics[(metrics.name == selected) & (metrics.split == "holdout")].sort_values("cost_bps"), [("cost_bps", "Cost bps"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Maximum Drawdown", "Max DD"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure")], {"CAGR", "Maximum Drawdown", "Exposure"})}

## Previous defensive candidates at 25 bps

{prior_text}

## Acceptance

- Passes: {_format(acceptance['passes'])}
- Holdout Sharpe: {acceptance['holdout_sharpe']:.3f}
- Holdout CAGR: {acceptance['holdout_cagr']:.2%}
- Holdout max drawdown: {acceptance['holdout_max_drawdown']:.2%}
- Holdout annual turnover: {acceptance['holdout_turnover']:.2f}x
- Failures: {acceptance['failures'] or 'None'}
""", encoding="utf-8")
        selection.to_csv(output / "liquidity_strategy_selection.csv", index=False)
        metrics.to_csv(output / "liquidity_strategy_metrics.csv", index=False)
        candidates.to_csv(output / "liquidity_strategy_candidates.csv", index=False)
    elif strategy_result:
        (output / "strategy_results.md").write_text(f"""# Stablecoin and market-liquidity conditioned strategy results

The strategy was not run.

Reason: {strategy_result.get('reason', 'unknown')}

No data was fabricated.
""", encoding="utf-8")

    payload: dict[str, Any] = {
        "coverage": coverage.to_dict("records") if not coverage.empty else [],
        "metadata": data.metadata,
        "strategy": None,
    }
    if strategy_result:
        payload["strategy"] = {
            key: value
            for key, value in strategy_result.items()
            if key not in {"metrics", "selection", "candidates"}
        }
        if strategy_result.get("available"):
            payload["strategy"]["metrics"] = strategy_result["metrics"].to_dict("records")
            payload["strategy"]["selection"] = strategy_result["selection"].to_dict("records")
            payload["strategy"]["candidates"] = strategy_result["candidates"].to_dict("records")
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
    if isinstance(value, (pd.Timestamp,)):
        return str(value)
    return value


__all__ = [
    "PublicDataBundle",
    "PublicDataCoverage",
    "LiquidityCandidate",
    "download_public_crypto_data",
    "load_processed_public_data",
    "run_liquidity_conditioned_strategy",
    "write_public_crypto_reports",
    "parse_stablecoin_chart",
    "build_4h_daily_features",
    "build_liquidity_conditioned_weights",
]
