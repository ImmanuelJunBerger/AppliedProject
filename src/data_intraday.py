"""Intraday perp data layer for Run 6 (1h bars) + integrity validation.

Venue reachability (probed 2026-08-07, same as Runs 1-5):
  OKX (www.okx.com)            -> 200. Primary source: perp 1H OHLCV, funding, OI.
  Hyperliquid (api.hyperliquid)-> 200. Cross-venue check; 1h candles only ~200d deep.
  Binance futures (fapi)       -> 451 geo-blocked. UNAVAILABLE.
  Bybit                        -> 403. UNAVAILABLE.

DEPTH LIMITS MEASURED (these constrain the whole study -- see report):
  OKX 1H OHLCV  : chains back ~3yr via explicit `after` pagination.       OK
  OKX funding   : free endpoint retains ~95 days only.                    SHORT
  OKX OI (rubik): 1H period = 29 days; 1D period = 179 days.              TOO SHORT
  HL 1h candles : ~200 days only.                                         SHORT
  HL funding    : back to ~2023-11, 480 rows/call, paginable.             OK

Everything cached to data/cache_intraday/*.parquet. UTC everywhere, no exceptions.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

LOG = logging.getLogger("data_intraday")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CACHE = Path(__file__).resolve().parent.parent / "data" / "cache_intraday"
CACHE.mkdir(parents=True, exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": "research/1.0"})
OKX = "https://www.okx.com"
HL = "https://api.hyperliquid.xyz"


def _cache(key: str) -> Path:
    return CACHE / f"{key}.parquet"


def _get(url, params=None, retries=4, timeout=25):
    last = None
    for i in range(retries):
        try:
            r = S.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def _post(url, payload, retries=4, timeout=25):
    last = None
    for i in range(retries):
        try:
            r = S.post(url, json=payload, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"POST {url} failed: {last}")


# ---------------------------------------------------------------------------
# OKX perp 1H OHLCV -- deep pagination
# ---------------------------------------------------------------------------

def fetch_okx_perp_1h(inst_id: str, target_days: int = 1100, use_cache: bool = True) -> pd.DataFrame:
    key = f"okx1h_{inst_id}_{target_days}d"
    if use_cache and _cache(key).exists():
        return pd.read_parquet(_cache(key))

    target_bars = int(target_days * 24)
    rows, after = [], None
    max_calls = target_bars // 100 + 20
    for _ in range(max_calls):
        p = {"instId": inst_id, "bar": "1H", "limit": 100}
        if after:
            p["after"] = after
        js = _get(f"{OKX}/api/v5/market/history-candles", p)
        batch = js.get("data", [])
        if not batch:
            break
        rows.extend(batch)
        after = batch[-1][0]
        if len(rows) >= target_bars:
            break
        time.sleep(0.06)

    if not rows:
        return pd.DataFrame()
    cols = ["ts", "open", "high", "low", "close", "vol", "volCcy", "volCcyQuote", "confirm"]
    df = pd.DataFrame(rows, columns=cols).drop_duplicates(subset="ts")
    df["timestamp"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "vol", "volCcyQuote"]:
        df[c] = df[c].astype(float)
    df = df.rename(columns={"vol": "volume", "volCcyQuote": "quote_volume"})
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["inst_id"] = inst_id
    df = df[["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "inst_id"]]
    df.to_parquet(_cache(key), index=False)
    LOG.info("OKX 1H %s rows=%d span=%s..%s", inst_id, len(df),
             df.timestamp.min().date(), df.timestamp.max().date())
    return df


def fetch_okx_funding(inst_id: str, use_cache: bool = True) -> pd.DataFrame:
    """OKX free funding-rate-history retains ~95 days. `after` pages BACKWARD."""
    key = f"okxfund_{inst_id}"
    if use_cache and _cache(key).exists():
        return pd.read_parquet(_cache(key))
    rows, after = [], None
    for _ in range(40):
        p = {"instId": inst_id, "limit": 100}
        if after:
            p["after"] = after
        js = _get(f"{OKX}/api/v5/public/funding-rate-history", p)
        batch = js.get("data", [])
        if not batch:
            break
        rows.extend(batch)
        after = batch[-1]["fundingTime"]
        if len(batch) < 100:
            break
        time.sleep(0.12)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).drop_duplicates(subset="fundingTime")
    df["timestamp"] = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms", utc=True)
    df["fundingRate"] = df["fundingRate"].astype(float)
    df = df.sort_values("timestamp")[["timestamp", "fundingRate"]].reset_index(drop=True)
    df["inst_id"] = inst_id
    df.to_parquet(_cache(key), index=False)
    LOG.info("OKX funding %s rows=%d span=%s..%s", inst_id, len(df),
             df.timestamp.min().date(), df.timestamp.max().date())
    return df


def fetch_hl_funding(coin: str, days: int = 1000, use_cache: bool = True) -> pd.DataFrame:
    """HL hourly funding, 480 rows/call, paginate forward. Reaches back to ~2023-11."""
    key = f"hlfund_{coin}_{days}d"
    if use_cache and _cache(key).exists():
        return pd.read_parquet(_cache(key))
    end = int(time.time() * 1000)
    cursor = end - days * 86400 * 1000
    rows = []
    for _ in range(300):
        if cursor >= end:
            break
        js = _post(f"{HL}/info", {"type": "fundingHistory", "coin": coin,
                                  "startTime": cursor, "endTime": end})
        if not js:
            break
        rows.extend(js)
        last_t = js[-1]["time"]
        cursor = last_t + 1
        if len(js) < 480:
            break
        time.sleep(0.08)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).drop_duplicates(subset="time")
    df["timestamp"] = pd.to_datetime(df["time"].astype("int64"), unit="ms", utc=True)
    df["fundingRate"] = df["fundingRate"].astype(float)
    df = df.sort_values("timestamp")[["timestamp", "fundingRate"]].reset_index(drop=True)
    df["coin"] = coin
    df.to_parquet(_cache(key), index=False)
    LOG.info("HL funding %s rows=%d span=%s..%s", coin, len(df),
             df.timestamp.min().date(), df.timestamp.max().date())
    return df


def fetch_okx_oi(ccy: str, period: str = "1H", use_cache: bool = True) -> pd.DataFrame:
    """Open interest. HARD LIMIT: 1H period returns ~29 days, 1D ~179 days.
    Far too short for a multi-year study -- documented, not worked around."""
    key = f"okxoi_{ccy}_{period}"
    if use_cache and _cache(key).exists():
        return pd.read_parquet(_cache(key))
    js = _get(f"{OKX}/api/v5/rubik/stat/contracts/open-interest-volume",
              {"ccy": ccy, "period": period})
    rows = js.get("data", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["ts", "oi_ccy", "vol_ccy"])
    df["timestamp"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    df["oi_ccy"] = df["oi_ccy"].astype(float)
    df = df.sort_values("timestamp")[["timestamp", "oi_ccy"]].reset_index(drop=True)
    df.to_parquet(_cache(key), index=False)
    return df


def okx_swap_universe(use_cache: bool = True) -> pd.DataFrame:
    """All live USDT perps + 24h volume, for universe selection.
    NOTE: this is a LIVE snapshot -- it contains only currently-listed instruments.
    Delisted perps are absent. That is a survivorship limitation, reported not hidden."""
    key = "okx_swap_universe"
    if use_cache and _cache(key).exists():
        return pd.read_parquet(_cache(key))
    js = _get(f"{OKX}/api/v5/market/tickers", {"instType": "SWAP"})
    df = pd.DataFrame(js.get("data", []))
    df = df[df["instId"].str.endswith("-USDT-SWAP")].copy()
    df["volCcy24h"] = pd.to_numeric(df["volCcy24h"], errors="coerce")
    df["last"] = pd.to_numeric(df["last"], errors="coerce")
    df["quote_vol_24h"] = df["volCcy24h"] * df["last"]
    df = df.sort_values("quote_vol_24h", ascending=False).reset_index(drop=True)
    df[["instId", "quote_vol_24h"]].to_parquet(_cache(key), index=False)
    return df[["instId", "quote_vol_24h"]]


# ---------------------------------------------------------------------------
# Integrity validation (Section 2)
# ---------------------------------------------------------------------------

def integrity_report(df: pd.DataFrame, inst_id: str, sigma: float = 10.0) -> dict:
    """Runs every Section-2 check. Classifies spikes rather than blindly dropping."""
    out = {"inst_id": inst_id, "n_bars": len(df)}
    if df.empty:
        out["error"] = "empty"
        return out

    ts = df["timestamp"]
    out["start"] = str(ts.min())
    out["end"] = str(ts.max())
    out["span_days"] = int((ts.max() - ts.min()).total_seconds() // 86400)

    # timezone
    out["tz_is_utc"] = str(ts.dt.tz) == "UTC"

    # duplicates
    out["duplicate_timestamps"] = int(ts.duplicated().sum())

    # gaps: expected hourly grid
    full = pd.date_range(ts.min(), ts.max(), freq="1h", tz="UTC")
    missing = full.difference(pd.DatetimeIndex(ts))
    out["expected_bars"] = len(full)
    out["missing_bars"] = len(missing)
    out["missing_pct"] = round(100 * len(missing) / len(full), 3) if len(full) else None
    if len(missing):
        # cluster consecutive missing bars into outage blocks
        gaps = pd.Series(missing)
        blocks = (gaps.diff() != pd.Timedelta("1h")).cumsum()
        sizes = gaps.groupby(blocks).size()
        out["n_gap_blocks"] = int(len(sizes))
        out["largest_gap_bars"] = int(sizes.max())
        out["largest_gap_start"] = str(gaps.groupby(blocks).first().loc[sizes.idxmax()])
    else:
        out["n_gap_blocks"] = 0
        out["largest_gap_bars"] = 0

    # zero volume
    out["zero_volume_bars"] = int((df["volume"] <= 0).sum())

    # price spikes: classify wick artifact vs real move
    ret = df["close"].pct_change()
    z = (ret - ret.mean()) / ret.std(ddof=1)
    spike_idx = z.abs() > sigma
    out["close_return_spikes_gt_sigma"] = int(spike_idx.sum())
    # wick artifact heuristic: extreme high/low vs both neighbouring closes but close itself normal
    hl_range = (df["high"] - df["low"]) / df["close"]
    rng_z = (hl_range - hl_range.mean()) / hl_range.std(ddof=1)
    artifact = (rng_z > sigma) & (z.abs() < 3)
    out["wick_artifact_candidates"] = int(artifact.sum())
    out["real_move_spikes"] = int((spike_idx & ~artifact).sum())
    if spike_idx.any():
        worst = z.abs().idxmax()
        out["worst_spike_ts"] = str(df["timestamp"].iloc[worst])
        out["worst_spike_ret_pct"] = round(float(ret.iloc[worst]) * 100, 2)

    # OHLC sanity
    bad_ohlc = ((df["high"] < df["low"]) | (df["high"] < df["open"]) | (df["high"] < df["close"]) |
                (df["low"] > df["open"]) | (df["low"] > df["close"]))
    out["ohlc_violations"] = int(bad_ohlc.sum())
    out["nonpositive_prices"] = int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
    return out


def funding_alignment_report(fund: pd.DataFrame, inst_id: str) -> dict:
    """Verify funding timestamps land on real 00/08/16 UTC settlements."""
    out = {"inst_id": inst_id, "n": len(fund)}
    if fund.empty:
        out["error"] = "empty"
        return out
    hours = fund["timestamp"].dt.hour
    out["hours_present"] = sorted(hours.unique().tolist())
    out["pct_on_0_8_16"] = round(100 * float(hours.isin([0, 8, 16]).mean()), 2)
    deltas = fund["timestamp"].diff().dropna().dt.total_seconds() / 3600
    out["median_interval_hrs"] = float(deltas.median()) if len(deltas) else None
    out["start"] = str(fund["timestamp"].min())
    out["end"] = str(fund["timestamp"].max())
    out["span_days"] = int((fund["timestamp"].max() - fund["timestamp"].min()).total_seconds() // 86400)
    return out


if __name__ == "__main__":
    import json
    df = fetch_okx_perp_1h("BTC-USDT-SWAP", target_days=1100, use_cache=False)
    print(json.dumps(integrity_report(df, "BTC-USDT-SWAP"), indent=2, default=str))
