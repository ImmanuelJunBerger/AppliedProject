"""Free on-chain / event data that the Section-2 probe verified reachable.

AVAILABILITY LAG IS THE WHOLE PROBLEM HERE. A daily series stamped at 00:00 UTC
of day D reports what happened DURING day D, so it is not knowable until D ends.
Every daily series returned by this module is therefore shifted forward one full
day before it is joined to the hourly panel: the value for day D first becomes
usable at D+1 00:00. Skipping that shift would manufacture a full day of
lookahead and would make every on-chain signal look tradable when it is not.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

CACHE = Path(__file__).resolve().parent.parent / "data" / "onchain"
CACHE.mkdir(parents=True, exist_ok=True)
TIMEOUT = 40


def _cached(name: str, fetch):
    p = CACHE / f"{name}.json"
    if p.exists():
        return json.loads(p.read_text())
    obj = fetch()
    p.write_text(json.dumps(obj))
    return obj


def blockchain_chart(chart: str) -> pd.Series:
    """Daily BTC chain series from blockchain.info, indexed at the day it MEASURES."""
    def go():
        u = f"https://api.blockchain.info/charts/{chart}?timespan=all&format=json"
        return requests.get(u, timeout=TIMEOUT).json()
    j = _cached(f"bci_{chart}", go)
    v = j.get("values", [])
    if not v:
        return pd.Series(dtype=float)
    s = pd.Series({pd.Timestamp(d["x"], unit="s", tz="UTC"): float(d["y"]) for d in v})
    return s.sort_index()


def stablecoin_supply() -> pd.Series:
    """Aggregate USD-pegged stablecoin circulating supply, daily (DeFiLlama)."""
    def go():
        return requests.get("https://stablecoins.llama.fi/stablecoincharts/all",
                            timeout=TIMEOUT).json()
    j = _cached("llama_stables_all", go)
    out = {}
    for row in j:
        try:
            out[pd.Timestamp(int(row["date"]), unit="s", tz="UTC")] = \
                float(row["totalCirculatingUSD"]["peggedUSD"])
        except (KeyError, TypeError, ValueError):
            continue
    return pd.Series(out).sort_index()


_SYM = re.compile(r"\b([A-Z0-9]{2,15}USDT)\b")


def perp_listing_announcements() -> pd.DataFrame:
    """Binance 'New Cryptocurrency Listing' announcements with release timestamps.

    Returns one row per (symbol, announcement time). The release timestamp is a
    real event time, so unlike the daily series it needs no extra lag -- but it is
    still only actionable on the NEXT hourly bar, which `evaluate()` enforces.
    """
    def go():
        arts, page = [], 1
        while page <= 60:
            u = ("https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
                 f"?type=1&catalogId=48&pageNo={page}&pageSize=50")
            r = requests.get(u, timeout=TIMEOUT)
            if r.status_code != 200:
                break
            cats = (r.json().get("data") or {}).get("catalogs") or []
            batch = cats[0].get("articles") or [] if cats else []
            if not batch:
                break
            arts += [{"title": a["title"], "releaseDate": a["releaseDate"]} for a in batch]
            page += 1
            time.sleep(0.25)
        return arts
    arts = _cached("binance_listing_announcements", go)
    rows = []
    for a in arts:
        t = a["title"]
        if "Futures Will Launch" not in t and "Perpetual" not in t:
            continue
        for sym in set(_SYM.findall(t.upper())):
            rows.append({"symbol": sym,
                         "ts": pd.Timestamp(a["releaseDate"], unit="ms", tz="UTC"),
                         "title": t})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("ts").drop_duplicates("symbol", keep="first").reset_index(drop=True)


def to_hourly_lagged(daily: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Daily series -> hourly, with the mandatory one-full-day availability lag.

    The value measuring day D is stamped forward to D+1 00:00 and then held flat.
    Reindexing with ffill after that shift can only ever surface a value that was
    already complete, never one from the future.
    """
    if daily.empty:
        return pd.Series(index=index, dtype=float)
    s = daily.copy()
    s.index = s.index.normalize() + pd.Timedelta(days=1)
    return s.reindex(s.index.union(index)).ffill().reindex(index)
