"""Data fetch + cache layer.

Free, no-key sources only. Network reality (probed 2026-07-18 from this
execution environment):
  - api.binance.com / fapi.binance.com  -> HTTP 451 (geo-blocked). DEAD.
  - api.bybit.com / api.bytick.com      -> HTTP 403. DEAD.
  - data-api.binance.vision             -> HTTP 200. Spot OHLCV mirror, works.
  - www.okx.com                         -> HTTP 200. Spot + perp OHLCV, funding.
  - api.hyperliquid.xyz                 -> HTTP 200. Perp OHLCV, funding, meta.
  - api.dexscreener.com                 -> HTTP 200. Shallow recent pair data.

Every fetch is cached to ./data/cache/<key>.parquet (or .csv if pyarrow
unavailable). Re-running does not re-hit the network for cached keys.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pandas as pd
import requests

LOG = logging.getLogger("data")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "backtest-research/1.0"})

BINANCE_VISION = "https://data-api.binance.vision"
OKX = "https://www.okx.com"
HL = "https://api.hyperliquid.xyz"
DEXSCREENER = "https://api.dexscreener.com"


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.parquet"


def _load_cache(key: str) -> pd.DataFrame | None:
    p = _cache_path(key)
    if p.exists():
        try:
            return pd.read_parquet(p)
        except Exception:
            csv = p.with_suffix(".csv")
            if csv.exists():
                return pd.read_csv(csv, parse_dates=["timestamp"])
    return None


def _save_cache(key: str, df: pd.DataFrame) -> None:
    p = _cache_path(key)
    try:
        df.to_parquet(p, index=False)
    except Exception:
        df.to_csv(p.with_suffix(".csv"), index=False)


def _get(url: str, params: dict | None = None, retries: int = 3, timeout: int = 20):
    last_err = None
    for i in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last_err = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET {url} failed after {retries} retries: {last_err}")


def _post(url: str, payload: dict, retries: int = 3, timeout: int = 20):
    last_err = None
    for i in range(retries):
        try:
            r = SESSION.post(url, json=payload, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last_err = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"POST {url} failed after {retries} retries: {last_err}")


# ---------------------------------------------------------------------------
# Binance spot OHLCV (via data-api.binance.vision mirror — no key needed)
# ---------------------------------------------------------------------------

def fetch_binance_spot_klines(symbol: str, interval: str = "1d", limit: int = 1000,
                               use_cache: bool = True) -> pd.DataFrame:
    key = f"binance_spot_{symbol}_{interval}_{limit}"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached
    raw = _get(f"{BINANCE_VISION}/api/v3/klines",
               {"symbol": symbol, "interval": interval, "limit": limit})
    cols = ["open_time", "open", "high", "low", "close", "volume", "close_time",
            "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]
    df = pd.DataFrame(raw, columns=cols)
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
        df[c] = df[c].astype(float)
    df["trades"] = df["trades"].astype(int)
    df = df[["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades"]]
    df["symbol"] = symbol
    _save_cache(key, df)
    LOG.info("fetched binance spot %s %s rows=%d", symbol, interval, len(df))
    return df


def fetch_binance_exchange_info(use_cache: bool = True) -> pd.DataFrame:
    key = "binance_exchange_info"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached
    raw = _get(f"{BINANCE_VISION}/api/v3/exchangeInfo")
    syms = pd.DataFrame(raw["symbols"])
    _save_cache(key, syms)
    return syms


# Bases that are not directional crypto assets: USD/EUR stablecoins, commodity
# (gold) wrapped tokens, forex pairs. Excluded from any momentum/reversal
# universe -- these have ~0 expected trend/reversal signal by construction.
NON_CRYPTO_BASES = {
    "USDC", "USD1", "FDUSD", "RLUSD", "TUSD", "DAI", "USDP", "BUSD", "GUSD",
    "EURI", "EUR", "GBP", "USDE", "PYUSD", "XAUT", "PAXG",
}
# Binance's tokenized-equity/ETF spot pairs (base ticker + trailing "B", e.g. a
# tokenized SpaceX/Micron/Circle/Nvidia/Tesla/S&P500-ETF share) -- not crypto,
# excluded explicitly. Identified by matching well-known Nasdaq/NYSE tickers +
# "B" suffix; found by inspecting the full 440-symbol Binance USDT pool
# (Run 2, Track A1) after the original Run-1 list proved incomplete.
TOKENIZED_EQUITY_BASES = {
    "SPCXB", "SOXLB", "CRCLB", "SNDKB", "SKHYB",
    "NVDAB", "TSLAB", "AMDB", "ARMB", "EWYB", "INTCB", "MSTRB", "METAB",
    "MSFTB", "PLTRB", "QQQB", "COINB", "GLWB", "NBISB", "QCOMB", "SPYB",
    "WDCB", "AAOIB", "DRAMB", "CBRSB",
}


def top_usdt_pairs_by_volume(n: int = 50, use_cache: bool = True) -> list[str]:
    """Rank USDT spot pairs by 24h quote volume, filtered to directional crypto only:
    excludes leveraged tokens, stablecoins, gold/forex wrappers, tokenized equities,
    and any non-ASCII symbol."""
    key = f"binance_top_{n}_usdt_filtered"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached["symbol"].tolist()
    raw = _get(f"{BINANCE_VISION}/api/v3/ticker/24hr")
    df = pd.DataFrame(raw)
    df = df[df["symbol"].str.endswith("USDT")]
    df = df[df["symbol"].str.match(r"^[A-Z0-9]+USDT$")]
    df = df[~df["symbol"].str.contains("UP|DOWN|BEAR|BULL")]
    df["base"] = df["symbol"].str.replace("USDT$", "", regex=True)
    df = df[~df["base"].isin(NON_CRYPTO_BASES)]
    df = df[~df["base"].isin(TOKENIZED_EQUITY_BASES)]
    df["quoteVolume"] = df["quoteVolume"].astype(float)
    df = df.sort_values("quoteVolume", ascending=False).head(n)
    _save_cache(key, df[["symbol", "quoteVolume"]])
    return df["symbol"].tolist()


# ---------------------------------------------------------------------------
# OKX perp OHLCV + funding
# ---------------------------------------------------------------------------

def fetch_okx_funding_history(inst_id: str, limit: int = 100, use_cache: bool = True) -> pd.DataFrame:
    key = f"okx_funding_{inst_id}"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached
    all_rows = []
    after = None
    for _ in range(30):  # OKX 'after' pages strictly backward in time (older)
        params = {"instId": inst_id, "limit": min(limit, 100)}
        if after:
            params["after"] = after
        js = _get(f"{OKX}/api/v5/public/funding-rate-history", params)
        rows = js.get("data", [])
        if not rows:
            break
        all_rows.extend(rows)
        after = rows[-1]["fundingTime"]
        time.sleep(0.2)
        if len(rows) < 100:
            break
    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows).drop_duplicates(subset=["fundingTime"])
    df["timestamp"] = pd.to_datetime(df["fundingTime"].astype(float), unit="ms", utc=True)
    df["fundingRate"] = df["fundingRate"].astype(float)
    df = df.sort_values("timestamp")[["timestamp", "fundingRate"]]
    df["instId"] = inst_id
    _save_cache(key, df)
    LOG.info("fetched OKX funding %s rows=%d", inst_id, len(df))
    return df


def fetch_okx_history_candles(inst_id: str, bar: str = "1H", target_days: float = 180,
                               use_cache: bool = True) -> pd.DataFrame:
    """Paginated fetch from OKX's longer-retention history-candles endpoint.
    Pages backward in time via `after` (older-than), 100 candles/call."""
    key = f"okx_history_candles_{inst_id}_{bar}_{int(target_days)}d"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached
    bar_hours = {"1H": 1, "4H": 4, "1D": 24}.get(bar, 1)
    target_rows = int(target_days * 24 / bar_hours)
    all_rows = []
    after = None
    for _ in range(max(1, target_rows // 100 + 2)):
        params = {"instId": inst_id, "bar": bar, "limit": 100}
        if after:
            params["after"] = after
        js = _get(f"{OKX}/api/v5/market/history-candles", params)
        rows = js.get("data", [])
        if not rows:
            break
        all_rows.extend(rows)
        after = rows[-1][0]
        time.sleep(0.15)
        if len(all_rows) >= target_rows or len(rows) < 100:
            break
    if not all_rows:
        return pd.DataFrame()
    cols = ["ts", "o", "h", "l", "c", "vol", "volCcy", "volCcyQuote", "confirm"]
    df = pd.DataFrame(all_rows, columns=cols).drop_duplicates(subset=["ts"])
    df["timestamp"] = pd.to_datetime(df["ts"].astype(float), unit="ms", utc=True)
    for c in ["o", "h", "l", "c", "vol"]:
        df[c] = df[c].astype(float)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "vol": "volume"})
    df = df.sort_values("timestamp")[["timestamp", "open", "high", "low", "close", "volume"]]
    df["instId"] = inst_id
    _save_cache(key, df)
    LOG.info("fetched OKX history-candles %s %s rows=%d span_days=%.0f", inst_id, bar, len(df),
              (df["timestamp"].max() - df["timestamp"].min()).days if len(df) else 0)
    return df


def fetch_okx_candles(inst_id: str, bar: str = "1D", limit: int = 300, use_cache: bool = True) -> pd.DataFrame:
    key = f"okx_candles_{inst_id}_{bar}"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached
    js = _get(f"{OKX}/api/v5/market/candles", {"instId": inst_id, "bar": bar, "limit": limit})
    rows = js.get("data", [])
    cols = ["ts", "o", "h", "l", "c", "vol", "volCcy", "volCcyQuote", "confirm"]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["ts"].astype(float), unit="ms", utc=True)
    for c in ["o", "h", "l", "c", "vol"]:
        df[c] = df[c].astype(float)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "vol": "volume"})
    df = df.sort_values("timestamp")[["timestamp", "open", "high", "low", "close", "volume"]]
    df["instId"] = inst_id
    _save_cache(key, df)
    LOG.info("fetched OKX candles %s %s rows=%d", inst_id, bar, len(df))
    return df


# ---------------------------------------------------------------------------
# Hyperliquid perp OHLCV + funding
# ---------------------------------------------------------------------------

def fetch_hl_funding_history(coin: str, start_ms: int, end_ms: int | None = None,
                              use_cache: bool = True) -> pd.DataFrame:
    """HL returns hourly funding, capped at 500 rows/call starting from `startTime`.
    Paginate forward in ~500h chunks until `end_ms` (default: now) is reached."""
    key = f"hl_funding_{coin}"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached
    end_ms = end_ms or int(time.time() * 1000)
    all_rows = []
    cursor = start_ms
    for _ in range(200):  # hard safety cap on calls
        if cursor >= end_ms:
            break
        js = _post(f"{HL}/info", {"type": "fundingHistory", "coin": coin,
                                   "startTime": cursor, "endTime": end_ms})
        if not js:
            break
        all_rows.extend(js)
        last_t = js[-1]["time"]
        if last_t <= cursor or len(js) < 500:
            cursor = last_t + 1
            if len(js) < 500:
                break
        else:
            cursor = last_t + 1
        time.sleep(0.15)
    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows).drop_duplicates(subset=["time"])
    df["timestamp"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df["fundingRate"] = df["fundingRate"].astype(float)
    df = df[["timestamp", "fundingRate"]].sort_values("timestamp")
    df["coin"] = coin
    _save_cache(key, df)
    LOG.info("fetched HL funding %s rows=%d span_days=%.0f", coin, len(df),
              (df["timestamp"].max() - df["timestamp"].min()).days if len(df) else 0)
    return df


def fetch_hl_candles(coin: str, interval: str = "1d", start_ms: int = 0,
                      end_ms: int | None = None, use_cache: bool = True) -> pd.DataFrame:
    key = f"hl_candles_{coin}_{interval}"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached
    payload = {"type": "candleSnapshot",
               "req": {"coin": coin, "interval": interval, "startTime": start_ms,
                        "endTime": end_ms or int(time.time() * 1000)}}
    js = _post(f"{HL}/info", payload)
    if not js:
        return pd.DataFrame()
    df = pd.DataFrame(js)
    df["timestamp"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    for c in ["o", "h", "l", "c", "v"]:
        df[c] = df[c].astype(float)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df = df[["timestamp", "open", "high", "low", "close", "volume"]].sort_values("timestamp")
    df["coin"] = coin
    _save_cache(key, df)
    LOG.info("fetched HL candles %s %s rows=%d", coin, interval, len(df))
    return df


def fetch_hl_meta(use_cache: bool = True) -> list[dict]:
    key = "hl_meta"
    p = CACHE_DIR / f"{key}.json"
    if use_cache and p.exists():
        return json.loads(p.read_text())
    js = _post(f"{HL}/info", {"type": "meta"})
    p.write_text(json.dumps(js))
    return js


# ---------------------------------------------------------------------------
# DexScreener (shallow — current pairs + limited recent candles only)
# ---------------------------------------------------------------------------

def dexscreener_search(query: str, use_cache: bool = True) -> pd.DataFrame:
    key = f"dexscreener_{query}"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached
    js = _get(f"{DEXSCREENER}/latest/dex/search", {"q": query})
    pairs = js.get("pairs") or []
    if not pairs:
        return pd.DataFrame()
    df = pd.json_normalize(pairs)
    df["fetched_at"] = pd.Timestamp.utcnow()
    _save_cache(key, df)
    LOG.info("fetched dexscreener query=%s rows=%d", query, len(df))
    return df


def dexscreener_token_profiles_latest(use_cache: bool = True) -> pd.DataFrame:
    """Latest new token profiles feed — used only to measure the survivorship gap."""
    key = "dexscreener_latest_profiles"
    if use_cache:
        cached = _load_cache(key)
        if cached is not None:
            return cached
    js = _get(f"{DEXSCREENER}/token-profiles/latest/v1")
    if isinstance(js, list):
        df = pd.DataFrame(js)
    else:
        df = pd.json_normalize(js)
    df["fetched_at"] = pd.Timestamp.utcnow()
    _save_cache(key, df)
    return df


def network_probe() -> dict:
    """One-shot reachability check for every source, logged not printed in full."""
    checks = {
        "binance_spot_vision": f"{BINANCE_VISION}/api/v3/ping",
        "okx": f"{OKX}/api/v5/public/time",
        "hyperliquid": None,  # POST-only, checked separately
        "dexscreener": f"{DEXSCREENER}/latest/dex/search?q=SOL",
    }
    out = {}
    for name, url in checks.items():
        if url is None:
            continue
        try:
            r = SESSION.get(url, timeout=10)
            out[name] = r.status_code
        except Exception as e:  # noqa: BLE001
            out[name] = f"ERROR:{e}"
    try:
        r = SESSION.post(f"{HL}/info", json={"type": "meta"}, timeout=10)
        out["hyperliquid"] = r.status_code
    except Exception as e:  # noqa: BLE001
        out["hyperliquid"] = f"ERROR:{e}"
    # known-dead, recorded for the report
    for name, url in {
        "binance_main": "https://api.binance.com/api/v3/ping",
        "binance_futures": "https://fapi.binance.com/fapi/v1/ping",
        "bybit": "https://api.bybit.com/v5/market/time",
    }.items():
        try:
            r = SESSION.get(url, timeout=10)
            out[name] = r.status_code
        except Exception as e:  # noqa: BLE001
            out[name] = f"ERROR:{e}"
    return out


if __name__ == "__main__":
    print(json.dumps(network_probe(), indent=2))
