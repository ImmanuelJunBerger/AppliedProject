"""Binance USD-M futures BULK ARCHIVE loader (Run 7).

WHY THIS SOURCE: Binance's REST API (fapi.binance.com) returns HTTP 451 from this
environment, but the public bulk archive at data.binance.vision is NOT geo-blocked.
This matters enormously:

  * DELISTED symbols remain in the archive (verified: FTTUSDT, SRMUSDT, RAYUSDT,
    ANTUSDT, SCUSDT all serve 2022 data). Run 6 had to disclose survivorship bias
    as uncorrectable; here it is actually FIXABLE.
  * fundingRate monthly dumps go back to 2020 (vs OKX's ~95-day API retention).
  * `metrics` daily dumps carry open interest, top-trader long/short ratio (by
    account and by position), overall account long/short ratio, and taker
    buy/sell volume ratio -- i.e. the whole Family-A flow/positioning dataset that
    Run 6 could not test.

Granularity: klines 1h (monthly zips), fundingRate (monthly zips, 8h prints),
metrics (DAILY zips, 5-min prints -> resampled to 1h on ingest).
Everything cached to data/cache_binance/*.parquet. UTC throughout.
"""
from __future__ import annotations

import io
import logging
import re
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

LOG = logging.getLogger("data_binance")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BASE = "https://data.binance.vision/data/futures/um"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
CACHE = Path(__file__).resolve().parent.parent / "data" / "cache_binance"
CACHE.mkdir(parents=True, exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": "research/1.0"})
_ad = requests.adapters.HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=0)
S.mount("https://", _ad)


def _cache(key: str) -> Path:
    return CACHE / f"{key}.parquet"


def _get_zip(url: str, retries: int = 3) -> bytes | None:
    for i in range(retries):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
        except Exception:
            pass
        time.sleep(0.6 * (i + 1))
    return None


def list_symbols() -> list[str]:
    """All USDT-margined perp symbols in the archive, including delisted ones."""
    key = "symbol_list"
    p = CACHE / f"{key}.txt"
    if p.exists():
        return p.read_text().split()
    r = S.get(f"{S3}?delimiter=/&prefix=data/futures/um/monthly/klines/", timeout=60)
    syms = re.findall(r"<Prefix>data/futures/um/monthly/klines/([^/<]+)/</Prefix>", r.text)
    syms = [s for s in syms if s.endswith("USDT")]
    p.write_text("\n".join(syms))
    return syms


def _months(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    return [d.strftime("%Y-%m") for d in pd.date_range(start, end, freq="MS")]


# ---------------------------------------------------------------------------
# 1h klines
# ---------------------------------------------------------------------------
KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def fetch_klines_1h(symbol: str, start: pd.Timestamp, end: pd.Timestamp,
                    use_cache: bool = True) -> pd.DataFrame:
    key = f"kl1h_{symbol}_{start:%Y%m}_{end:%Y%m}"
    if use_cache and _cache(key).exists():
        return pd.read_parquet(_cache(key))
    frames = []
    for ym in _months(start, end):
        blob = _get_zip(f"{BASE}/monthly/klines/{symbol}/1h/{symbol}-1h-{ym}.zip")
        if blob is None:
            continue
        try:
            zf = zipfile.ZipFile(io.BytesIO(blob))
            raw = zf.read(zf.namelist()[0]).decode()
        except Exception:
            continue
        first = raw.split("\n", 1)[0]
        hdr = 0 if first.startswith("open_time") else None
        df = pd.read_csv(io.StringIO(raw), header=hdr, names=None if hdr == 0 else KLINE_COLS)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    ot = pd.to_numeric(df["open_time"], errors="coerce")
    # Binance switched open_time from ms to us in some 2025+ files
    unit = "us" if ot.max() > 1e15 else "ms"
    df["timestamp"] = pd.to_datetime(ot, unit=unit, utc=True)
    for c in ["open", "high", "low", "close", "volume", "quote_volume",
              "taker_buy_volume", "taker_buy_quote_volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["count"] = pd.to_numeric(df["count"], errors="coerce")
    df = (df.dropna(subset=["timestamp", "close"])
            .drop_duplicates(subset="timestamp")
            .sort_values("timestamp").reset_index(drop=True))
    df["symbol"] = symbol
    df = df[["timestamp", "open", "high", "low", "close", "volume", "quote_volume",
             "count", "taker_buy_volume", "taker_buy_quote_volume", "symbol"]]
    df.to_parquet(_cache(key), index=False)
    return df


# ---------------------------------------------------------------------------
# funding rate (8h prints, back to 2020)
# ---------------------------------------------------------------------------

def fetch_funding(symbol: str, start: pd.Timestamp, end: pd.Timestamp,
                  use_cache: bool = True) -> pd.DataFrame:
    key = f"fund_{symbol}_{start:%Y%m}_{end:%Y%m}"
    if use_cache and _cache(key).exists():
        return pd.read_parquet(_cache(key))
    frames = []
    for ym in _months(start, end):
        blob = _get_zip(f"{BASE}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{ym}.zip")
        if blob is None:
            continue
        try:
            zf = zipfile.ZipFile(io.BytesIO(blob))
            raw = zf.read(zf.namelist()[0]).decode()
        except Exception:
            continue
        first = raw.split("\n", 1)[0]
        hdr = 0 if first.startswith("calc_time") else None
        df = pd.read_csv(io.StringIO(raw), header=hdr,
                         names=None if hdr == 0 else ["calc_time", "funding_interval_hours",
                                                       "last_funding_rate"])
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    ct = pd.to_numeric(df["calc_time"], errors="coerce")
    unit = "us" if ct.max() > 1e15 else "ms"
    df["timestamp"] = pd.to_datetime(ct, unit=unit, utc=True)
    df["fundingRate"] = pd.to_numeric(df["last_funding_rate"], errors="coerce")
    df["interval_hours"] = pd.to_numeric(df.get("funding_interval_hours"), errors="coerce")
    df = (df.dropna(subset=["timestamp", "fundingRate"]).drop_duplicates(subset="timestamp")
            .sort_values("timestamp").reset_index(drop=True))
    df["symbol"] = symbol
    df = df[["timestamp", "fundingRate", "interval_hours", "symbol"]]
    df.to_parquet(_cache(key), index=False)
    return df


# ---------------------------------------------------------------------------
# metrics: OI + positioning (DAILY zips, 5-min prints -> hourly)
# ---------------------------------------------------------------------------
METRIC_COLS = ["create_time", "symbol", "sum_open_interest", "sum_open_interest_value",
               "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
               "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]


def _one_metric_day(symbol: str, day: str) -> pd.DataFrame | None:
    blob = _get_zip(f"{BASE}/daily/metrics/{symbol}/{symbol}-metrics-{day}.zip", retries=2)
    if blob is None:
        return None
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
        raw = zf.read(zf.namelist()[0]).decode()
    except Exception:
        return None
    first = raw.split("\n", 1)[0]
    hdr = 0 if first.startswith("create_time") else None
    return pd.read_csv(io.StringIO(raw), header=hdr, names=None if hdr == 0 else METRIC_COLS)


def fetch_metrics_1h(symbol: str, start: pd.Timestamp, end: pd.Timestamp,
                     use_cache: bool = True, workers: int = 12) -> pd.DataFrame:
    """OI + positioning, resampled 5min -> 1h (last value in each hour)."""
    key = f"met1h_{symbol}_{start:%Y%m%d}_{end:%Y%m%d}"
    if use_cache and _cache(key).exists():
        return pd.read_parquet(_cache(key))
    days = [d.strftime("%Y-%m-%d") for d in pd.date_range(start, end, freq="D")]
    frames = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for out in ex.map(lambda d: _one_metric_day(symbol, d), days):
            if out is not None and len(out):
                frames.append(out)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["create_time"], utc=True, errors="coerce")
    num = ["sum_open_interest", "sum_open_interest_value",
           "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
           "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    h = (df.set_index("timestamp")[num].resample("1h").last().dropna(how="all").reset_index())
    h["symbol"] = symbol
    h.to_parquet(_cache(key), index=False)
    return h


# ---------------------------------------------------------------------------
# Deribit implied vol (DVOL) for the variance risk premium
# ---------------------------------------------------------------------------

def fetch_dvol(currency: str, start: pd.Timestamp, end: pd.Timestamp,
               use_cache: bool = True) -> pd.DataFrame:
    key = f"dvol_{currency}"
    if use_cache and _cache(key).exists():
        return pd.read_parquet(_cache(key))
    frames, cur = [], start
    while cur < end:
        nxt = min(cur + pd.Timedelta(days=90), end)
        try:
            r = S.get("https://www.deribit.com/api/v2/public/get_volatility_index_data",
                      params={"currency": currency, "resolution": 3600,
                              "start_timestamp": int(cur.timestamp() * 1000),
                              "end_timestamp": int(nxt.timestamp() * 1000)}, timeout=45)
            data = r.json().get("result", {}).get("data", [])
            if data:
                frames.append(pd.DataFrame(data, columns=["ts", "open", "high", "low", "close"]))
        except Exception:
            pass
        cur = nxt
        time.sleep(0.15)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset="ts")
    df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.sort_values("timestamp")[["timestamp", "close"]].rename(columns={"close": "dvol"})
    df["currency"] = currency
    df.to_parquet(_cache(key), index=False)
    return df


def integrity(df: pd.DataFrame, name: str) -> dict:
    if df.empty:
        return {"name": name, "error": "empty"}
    ts = df["timestamp"]
    full = pd.date_range(ts.min(), ts.max(), freq="1h", tz="UTC")
    return {"name": name, "n": len(df), "start": str(ts.min()), "end": str(ts.max()),
            "span_days": int((ts.max() - ts.min()).days),
            "dupes": int(ts.duplicated().sum()),
            "missing_1h_bars": int(len(full.difference(pd.DatetimeIndex(ts)))),
            "missing_pct": round(100 * len(full.difference(pd.DatetimeIndex(ts))) / max(len(full), 1), 3)}
