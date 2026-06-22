from pathlib import Path
import pytest
from crypto_mlsystem.real_data import discover_liquid_symbols, fetch_ohlcv_symbol, write_ohlcv_csv


class FakeExchange:
    has = {"fetchTickers": True}

    def __init__(self):
        self.calls = 0

    def load_markets(self):
        return {
            "BTC/USDT": {"active": True, "spot": True, "base": "BTC", "quote": "USDT"},
            "ETH/USDT": {"active": True, "spot": True, "base": "ETH", "quote": "USDT"},
            "SOL/USDT": {"active": True, "spot": True, "base": "SOL", "quote": "USDT"},
            "USDC/USDT": {"active": True, "spot": True, "base": "USDC", "quote": "USDT"},
            "WBTC/USDT": {"active": True, "spot": True, "base": "WBTC", "quote": "USDT"},
            "OLD/USDT": {"active": False, "spot": True, "base": "OLD", "quote": "USDT"},
        }

    def fetch_tickers(self):
        return {"SOL/USDT": {"quoteVolume": 1000}, "ETH/USDT": {"quoteVolume": 500}, "BTC/USDT": {"quoteVolume": 800}}

    def fetch_ohlcv(self, symbol, timeframe="1d", since=None, limit=1000):
        self.calls += 1
        if self.calls > 1:
            return []
        return [[1577836800000, 1, 2, 0.5, 1.5, 10]]

    def iso8601(self, ts):
        return "2020-01-01T00:00:00.000Z"


def test_discover_liquid_symbols_includes_majors_and_excludes_wrapped_or_stable(monkeypatch):
    monkeypatch.setattr("crypto_mlsystem.real_data._exchange_instance", lambda exchange_name: FakeExchange())
    symbols = discover_liquid_symbols("binance", "USDT", top_n=3)
    assert symbols[:2] == ["BTC/USDT", "ETH/USDT"]
    assert "SOL/USDT" in symbols
    assert "USDC/USDT" not in symbols
    assert "WBTC/USDT" not in symbols


def test_fetch_ohlcv_symbol_maps_rows_without_future_adjustment():
    rows = fetch_ohlcv_symbol(FakeExchange(), "BTC/USDT", "1d", since_ms=1577836800000, limit=1000, sleep_seconds=0)
    assert rows == [{"date": "2020-01-01", "symbol": "BTC", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "market_cap": 15.0}]


def test_write_ohlcv_csv(tmp_path):
    path = write_ohlcv_csv([{"date": "2020-01-01", "symbol": "BTC", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "market_cap": 15}], tmp_path / "ohlcv.csv")
    assert Path(path).read_text().splitlines()[0] == "date,symbol,open,high,low,close,volume,market_cap"
