"""Binance public derivatives ingestion with explicit history/coverage handling."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BINANCE_FUTURES_URL = "https://fapi.binance.com"


@dataclass
class DerivativesCoverage:
    dataset: str
    symbol: str
    start: str | None
    end: str | None
    observations: int
    usable_for_locked_study: bool
    limitation: str


class BinanceDerivativesDownloader:
    def __init__(self, base_url: str = BINANCE_FUTURES_URL, pause_seconds: float = 0.08):
        self.base_url = base_url.rstrip("/")
        self.pause_seconds = pause_seconds

    def _request(self, path: str, params: dict[str, Any]) -> list[Any] | dict[str, Any]:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}{path}?{query}",
            headers={"User-Agent": "crypto-ml-research/1.0"},
        )
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception as exc:  # pragma: no cover - network-specific
                last_error = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"Binance request failed: {path}: {last_error}")

    def funding_history(self, symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> list[dict[str, Any]]:
        cursor = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
        end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)
        rows: list[dict[str, Any]] = []
        while cursor <= end_ms:
            batch = self._request("/fapi/v1/fundingRate", {
                "symbol": symbol, "startTime": cursor, "endTime": end_ms, "limit": 1000,
            })
            if not isinstance(batch, list) or not batch:
                break
            rows.extend(batch)
            next_cursor = int(batch[-1]["fundingTime"]) + 1
            if next_cursor <= cursor:
                break
            cursor = next_cursor
            time.sleep(self.pause_seconds)
        return rows

    def premium_index_history(self, symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> list[list[Any]]:
        cursor = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
        end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)
        rows: list[list[Any]] = []
        while cursor <= end_ms:
            batch = self._request("/fapi/v1/premiumIndexKlines", {
                "symbol": symbol, "interval": "1d", "startTime": cursor,
                "endTime": end_ms, "limit": 1500,
            })
            if not isinstance(batch, list) or not batch:
                break
            rows.extend(batch)
            next_cursor = int(batch[-1][0]) + 86_400_000
            if next_cursor <= cursor:
                break
            cursor = next_cursor
            time.sleep(self.pause_seconds)
        return rows

    def recent_metric(self, endpoint: str, symbol: str, period: str = "1d", limit: int = 500) -> list[dict[str, Any]]:
        data = self._request(endpoint, {"symbol": symbol, "period": period, "limit": limit})
        return data if isinstance(data, list) else []


def fetch_funding_history(
    assets: list[str] | tuple[str, ...],
    since: str = "2019-01-01",
    until: str | None = None,
    limit: int = 1000,
    sleep_seconds: float = 0.08,
    exchange: Any | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Compatibility API for the original ccxt funding collector.

    Returns UTC-daily realized funding sums for active linear USDT swaps and a
    list of requested assets for which no suitable contract or observations were
    available. The newer public-HTTP collector remains the production path.
    """
    if exchange is None:  # pragma: no cover - optional live dependency
        try:
            import ccxt  # type: ignore
        except ImportError as exc:
            raise ImportError("Install ccxt to use fetch_funding_history") from exc
        exchange = ccxt.binanceusdm({"enableRateLimit": True})

    markets = exchange.load_markets()
    requested = [str(asset).upper() for asset in assets]
    start_ms = int(exchange.parse8601(f"{since}T00:00:00Z"))
    end_value = until or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    end_ms = int(exchange.parse8601(f"{end_value}T00:00:00Z"))
    records: list[dict[str, Any]] = []
    missing: list[str] = []

    for asset in requested:
        contract = next((
            symbol for symbol, market in markets.items()
            if str(market.get("base", "")).upper() == asset
            and str(market.get("quote", "")).upper() == "USDT"
            and str(market.get("settle", "")).upper() == "USDT"
            and bool(market.get("swap")) and bool(market.get("linear"))
            and market.get("active", True) is not False
        ), None)
        if contract is None:
            missing.append(asset)
            continue

        cursor = start_ms
        asset_rows = 0
        while cursor < end_ms:
            batch = exchange.fetch_funding_rate_history(contract, since=cursor, limit=limit)
            if not batch:
                break
            latest = cursor
            for item in batch:
                timestamp = int(item.get("timestamp", 0))
                if start_ms <= timestamp < end_ms:
                    records.append({
                        "date": pd.to_datetime(timestamp, unit="ms", utc=True).tz_localize(None).normalize(),
                        "symbol": asset,
                        "funding_rate": float(item.get("fundingRate", np.nan)),
                    })
                    asset_rows += 1
                latest = max(latest, timestamp + 1)
            if latest <= cursor:
                break
            cursor = latest
            if len(batch) < limit:
                break
            time.sleep(sleep_seconds)
        if asset_rows == 0:
            missing.append(asset)

    if not records:
        return pd.DataFrame(columns=["date", "symbol", "funding_rate"]), missing
    daily = pd.DataFrame(records).groupby(["date", "symbol"], as_index=False).funding_rate.sum()
    return daily.sort_values(["date", "symbol"]).reset_index(drop=True), missing


def _write_json(path: Path, records: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def _funding_frame(records: list[dict[str, Any]], symbol: str) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["date", "symbol", "funding_rate"])
    frame = pd.DataFrame(records)
    frame["date"] = pd.to_datetime(frame.fundingTime, unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    frame["symbol"] = symbol.removesuffix("USDT")
    frame["funding_rate"] = pd.to_numeric(frame.fundingRate, errors="coerce")
    return frame.groupby(["date", "symbol"], as_index=False).agg(
        funding_rate=("funding_rate", "mean"),
        funding_sum_daily=("funding_rate", "sum"),
        funding_observations=("funding_rate", "count"),
    )


def _premium_frame(records: list[list[Any]], symbol: str) -> pd.DataFrame:
    columns = [
        "open_time", "basis_open", "basis_high", "basis_low", "basis_close", "volume",
        "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
    ]
    if not records:
        return pd.DataFrame(columns=["date", "symbol", "basis_open", "basis_high", "basis_low", "basis_close"])
    frame = pd.DataFrame(records, columns=columns)
    frame["date"] = pd.to_datetime(frame.open_time, unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    frame["symbol"] = symbol.removesuffix("USDT")
    for column in ("basis_open", "basis_high", "basis_low", "basis_close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame[["date", "symbol", "basis_open", "basis_high", "basis_low", "basis_close"]]


def _recent_frame(records: list[dict[str, Any]], symbol: str, kind: str) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["date", "symbol"])
    frame = pd.DataFrame(records)
    frame["date"] = pd.to_datetime(frame.timestamp, unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    frame["symbol"] = symbol.removesuffix("USDT")
    if kind == "open_interest":
        frame["open_interest"] = pd.to_numeric(frame.sumOpenInterestValue, errors="coerce")
        return frame[["date", "symbol", "open_interest"]]
    if kind == "long_short":
        frame["long_short_ratio"] = pd.to_numeric(frame.longShortRatio, errors="coerce")
        return frame[["date", "symbol", "long_short_ratio"]]
    if kind == "taker":
        buy = pd.to_numeric(frame.buyVol, errors="coerce")
        sell = pd.to_numeric(frame.sellVol, errors="coerce")
        frame["taker_buy_sell_ratio"] = buy / sell.replace(0, np.nan)
        frame["taker_imbalance"] = (buy - sell) / (buy + sell).replace(0, np.nan)
        return frame[["date", "symbol", "taker_buy_sell_ratio", "taker_imbalance"]]
    raise ValueError(kind)


def download_public_derivatives(
    raw_dir: str | Path,
    processed_dir: str | Path,
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT"),
    start: str = "2019-01-01",
    end: str = "2026-06-22",
    downloader: BinanceDerivativesDownloader | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download available public history and persist raw plus normalized files."""
    raw_dir, processed_dir = Path(raw_dir), Path(processed_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    client = downloader or BinanceDerivativesDownloader()
    all_frames: list[pd.DataFrame] = []
    coverage: list[DerivativesCoverage] = []
    endpoints = {
        "open_interest": "/futures/data/openInterestHist",
        "long_short": "/futures/data/globalLongShortAccountRatio",
        "taker": "/futures/data/takerlongshortRatio",
    }
    for symbol in symbols:
        funding = client.funding_history(symbol, pd.Timestamp(start), pd.Timestamp(end))
        premium = client.premium_index_history(symbol, pd.Timestamp(start), pd.Timestamp(end))
        _write_json(raw_dir / f"{symbol}_funding.json", funding)
        _write_json(raw_dir / f"{symbol}_premium_index.json", premium)
        symbol_frame = _funding_frame(funding, symbol).merge(
            _premium_frame(premium, symbol), on=["date", "symbol"], how="outer"
        )
        for kind, endpoint in endpoints.items():
            records = client.recent_metric(endpoint, symbol)
            _write_json(raw_dir / f"{symbol}_{kind}.json", records)
            recent = _recent_frame(records, symbol, kind)
            symbol_frame = symbol_frame.merge(recent, on=["date", "symbol"], how="outer")
            start_date = recent.date.min() if len(recent) else None
            end_date = recent.date.max() if len(recent) else None
            coverage.append(DerivativesCoverage(
                kind, symbol.removesuffix("USDT"),
                str(start_date.date()) if start_date is not None else None,
                str(end_date.date()) if end_date is not None else None,
                len(recent), False,
                "Binance public market-data endpoint retains only recent history; excluded from 2019-2026 validation.",
            ))
        all_frames.append(symbol_frame)
        for kind, frame, limitation in (
            ("funding", _funding_frame(funding, symbol), "Contract listing-dependent; realized funding aggregated to UTC day."),
            ("premium_index_basis", _premium_frame(premium, symbol), "Premium-index kline, not a tradeable futures cash-and-carry return."),
        ):
            start_date = frame.date.min() if len(frame) else None
            end_date = frame.date.max() if len(frame) else None
            coverage.append(DerivativesCoverage(
                kind, symbol.removesuffix("USDT"),
                str(start_date.date()) if start_date is not None else None,
                str(end_date.date()) if end_date is not None else None,
                len(frame), bool(len(frame) >= 365), limitation,
            ))
    processed = pd.concat(all_frames, ignore_index=True).sort_values(["date", "symbol"])
    processed.to_csv(processed_dir / "binance_derivatives_daily.csv", index=False)
    coverage_frame = pd.DataFrame([item.__dict__ for item in coverage])
    coverage_frame.to_csv(processed_dir / "coverage.csv", index=False)
    return processed, coverage_frame


def merge_existing_funding(processed: pd.DataFrame, funding_path: str | Path | None) -> pd.DataFrame:
    """Use the broader archived funding panel without overwriting API observations."""
    if funding_path is None or not Path(funding_path).exists():
        return processed
    funding = pd.read_csv(funding_path, parse_dates=["date"])
    combined = processed.merge(funding, on=["date", "symbol"], how="outer", suffixes=("", "_archive"))
    if "funding_rate_archive" in combined:
        combined["funding_rate"] = combined.funding_rate.combine_first(combined.funding_rate_archive)
        combined = combined.drop(columns="funding_rate_archive")
    return combined.sort_values(["date", "symbol"])
