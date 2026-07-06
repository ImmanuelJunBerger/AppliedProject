"""Real cryptocurrency OHLCV download utilities using ccxt.

This module keeps ccxt optional: importing the module does not require network or
third-party packages. Runtime methods raise a clear error if ccxt is not installed.
"""
from __future__ import annotations
import csv
import importlib
import importlib.util
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

STABLE_QUOTES = {"USDT", "USDC", "USD"}
EXCLUDED_BASES = {
    "USDT", "USDC", "DAI", "BUSD", "TUSD", "FDUSD", "USDP", "PYUSD",
    "USDE", "USDS", "USD1", "XUSD", "USDD", "USDJ", "UST", "USTC",
    "GUSD", "LUSD", "SUSD", "CUSD", "FRAX", "RLUSD", "BFUSD", "AEUR",
    "EURS", "EURC", "BIDR", "IDRT", "EUR", "GBP", "AUD", "BRL", "TRY",
    "RUB", "UAH", "NGN", "PLN", "RON", "ZAR", "ARS", "MXN", "JPY",
    "WBTC", "WETH", "STETH", "WSTETH", "WBETH", "BETH", "BTCB", "CBBTC",
    "PAXG", "XAUT",
}

@dataclass(frozen=True)
class DownloadConfig:
    exchange: str = "binance"
    quote: str = "USDT"
    timeframe: str = "1d"
    since: str | None = "2020-01-01"
    limit: int = 1000
    top_n: int = 20
    output: str = "data/ohlcv_real.csv"
    rate_limit_sleep: float = 0.25
    historical_universe: bool = False


def _ccxt_module():
    if importlib.util.find_spec("ccxt") is None:
        raise ImportError("ccxt is required for real-data downloads. Install with `python -m pip install ccxt` or `python -m pip install -r requirements.txt`.")
    return importlib.import_module("ccxt")


def _exchange_instance(exchange_name: str):
    ccxt = _ccxt_module()
    if not hasattr(ccxt, exchange_name):
        raise ValueError(f"Unsupported ccxt exchange '{exchange_name}'. Try 'binance' or 'coinbase'.")
    exchange_cls = getattr(ccxt, exchange_name)
    return exchange_cls({"enableRateLimit": True})


def _parse_since(exchange, since: str | None):
    return None if since is None else exchange.parse8601(f"{since}T00:00:00Z")


def _eligible_market_symbols(markets: dict, quote: str) -> list[str]:
    symbols = []
    for symbol, market in markets.items():
        if not market.get("active", True) or market.get("spot") is False:
            continue
        base = market.get("base") or symbol.split("/")[0]
        market_quote = market.get("quote") or (symbol.split("/")[1] if "/" in symbol else "")
        if market_quote == quote and base not in EXCLUDED_BASES:
            symbols.append(symbol)
    return symbols


def discover_liquid_symbols(exchange_name: str = "binance", quote: str = "USDT", top_n: int = 20, include_major: bool = True) -> list[str]:
    """Return BTC, ETH, and top quote-pair assets ranked by quoted turnover when available."""
    exchange = _exchange_instance(exchange_name)
    markets = exchange.load_markets()
    tickers = exchange.fetch_tickers() if getattr(exchange, "has", {}).get("fetchTickers") else {}
    candidates = []
    for symbol in _eligible_market_symbols(markets, quote):
        ticker = tickers.get(symbol, {}) if isinstance(tickers, dict) else {}
        score = ticker.get("quoteVolume") or ticker.get("baseVolume") or 0
        candidates.append((float(score or 0), symbol))
    ranked = [symbol for _, symbol in sorted(candidates, reverse=True)]
    majors = [f"BTC/{quote}", f"ETH/{quote}"] if include_major else []
    out = []
    for symbol in majors + ranked:
        if symbol in markets and symbol not in out:
            out.append(symbol)
        if len(out) >= top_n:
            break
    return out


def fetch_ohlcv_symbol(exchange, symbol: str, timeframe: str, since_ms: int | None, limit: int, sleep_seconds: float) -> list[dict]:
    """Fetch OHLCV pages for one symbol without looking ahead or modifying timestamps."""
    rows = []
    next_since = since_ms
    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=next_since, limit=limit)
        if not batch:
            break
        for ts, open_, high, low, close, volume in batch:
            rows.append({
                "date": exchange.iso8601(ts)[:10], "symbol": symbol.split("/")[0],
                "open": open_, "high": high, "low": low, "close": close,
                "volume": volume, "market_cap": close * volume,
            })
        if len(batch) < limit:
            break
        next_since = batch[-1][0] + 1
        time.sleep(sleep_seconds)
    return rows


def download_ohlcv(config: DownloadConfig, symbols: Iterable[str] | None = None) -> list[dict]:
    exchange = _exchange_instance(config.exchange)
    markets = exchange.load_markets()
    if symbols:
        selected = list(symbols)
    elif config.historical_universe:
        # Fetch the broad current exchange cross-section, then rank independently
        # at every historical rebalance date. ccxt cannot recover pairs an
        # exchange has removed from its market catalogue.
        selected = _eligible_market_symbols(markets, config.quote)
    else:
        selected = discover_liquid_symbols(config.exchange, config.quote, config.top_n)
    since_ms = _parse_since(exchange, config.since)
    rows = []
    for index, symbol in enumerate(selected, start=1):
        try:
            rows.extend(fetch_ohlcv_symbol(exchange, symbol, config.timeframe, since_ms, config.limit, config.rate_limit_sleep))
        except Exception as exc:
            print(f"warning: skipped {symbol}: {exc}", file=sys.stderr, flush=True)
        if index == 1 or index % 25 == 0 or index == len(selected):
            print(f"downloaded {index}/{len(selected)} symbols ({len(rows)} rows)", flush=True)
        time.sleep(config.rate_limit_sleep)
    return rows


def write_ohlcv_csv(rows: list[dict], output: str | Path) -> Path:
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["date", "symbol", "open", "high", "low", "close", "volume", "market_cap"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(rows)
    return path
