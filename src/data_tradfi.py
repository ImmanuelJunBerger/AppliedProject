"""Traditional-markets data fetch + cache layer for Run 5.

Sources confirmed reachable (see HYPOTHESES_V5.md probe): Kenneth French Data
Library, FRED, CFTC Socrata API, Yahoo Finance (requires a User-Agent header),
Fed FOMC historical calendar pages. Stooq is blocked (JS challenge) and not used.

Every fetch is cached to ./data/cache_tradfi/<key>.parquet (or .json for
non-tabular data). Re-running does not re-hit the network for cached keys.
"""
from __future__ import annotations

import io
import json
import logging
import re
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

LOG = logging.getLogger("data_tradfi")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DIR = DATA_DIR / "cache_tradfi"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research/1.0"})

FRENCH_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
CFTC_BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
FED_CAL_BASE = "https://www.federalreserve.gov/monetarypolicy"


def _cache_path(key: str, ext: str = "parquet") -> Path:
    return CACHE_DIR / f"{key}.{ext}"


def _load_parquet(key: str) -> pd.DataFrame | None:
    p = _cache_path(key)
    if p.exists():
        return pd.read_parquet(p)
    return None


def _save_parquet(key: str, df: pd.DataFrame) -> None:
    df.to_parquet(_cache_path(key), index=False)


# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------

def fetch_yahoo_history(ticker: str, use_cache: bool = True, retries: int = 3) -> pd.DataFrame:
    key = f"yahoo_{ticker.replace('=', '_').replace('^', 'IDX_')}"
    if use_cache:
        cached = _load_parquet(key)
        if cached is not None:
            return cached
    url = f"{YAHOO_BASE}/{ticker}"
    params = {"period1": 0, "period2": 9999999999, "interval": "1d", "events": "div,split"}
    last_err = None
    for i in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=20)
            if r.status_code == 200:
                js = r.json()
                result = js.get("chart", {}).get("result")
                if not result:
                    return pd.DataFrame()
                res = result[0]
                ts = res.get("timestamp")
                if not ts:
                    return pd.DataFrame()
                quote = res["indicators"]["quote"][0]
                df = pd.DataFrame({
                    "timestamp": pd.to_datetime(ts, unit="s", utc=True),
                    "open": quote.get("open"), "high": quote.get("high"),
                    "low": quote.get("low"), "close": quote.get("close"),
                    "volume": quote.get("volume"),
                })
                adj = res["indicators"].get("adjclose")
                if adj:
                    df["adjclose"] = adj[0].get("adjclose")
                df = df.dropna(subset=["close"]).reset_index(drop=True)
                df["ticker"] = ticker
                _save_parquet(key, df)
                LOG.info("fetched yahoo %s rows=%d span=%s..%s", ticker, len(df),
                          df["timestamp"].min(), df["timestamp"].max())
                return df
            last_err = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(1.5 * (i + 1))
    LOG.warning("yahoo fetch failed for %s: %s", ticker, last_err)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Kenneth French Data Library
# ---------------------------------------------------------------------------

def fetch_french_dataset(name: str, use_cache: bool = True) -> pd.DataFrame:
    """name e.g. 'F-F_Research_Data_5_Factors_2x3_daily', 'F-F_Momentum_Factor_daily'."""
    key = f"french_{name}"
    if use_cache:
        cached = _load_parquet(key)
        if cached is not None:
            return cached
    url = f"{FRENCH_BASE}/{name}_CSV.zip"
    r = SESSION.get(url, timeout=30)
    if r.status_code != 200:
        LOG.warning("french fetch failed for %s: HTTP %s", name, r.status_code)
        return pd.DataFrame()
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    inner_name = zf.namelist()[0]
    raw = zf.read(inner_name).decode("latin1")
    lines = raw.splitlines()
    # find the header row (starts with a blank col then factor names) and data rows (date,val,val,...)
    start = None
    for i, line in enumerate(lines):
        parts = line.split(",")
        if len(parts) > 1 and re.match(r"^\d{8}$", parts[0].strip()):
            start = i
            break
    if start is None:
        LOG.warning("could not locate data start in french file %s", name)
        return pd.DataFrame()
    header_line = lines[start - 1] if start > 0 else None
    cols = [c.strip() for c in header_line.split(",")] if header_line else None
    end = start
    while end < len(lines):
        parts = lines[end].split(",")
        if len(parts) > 1 and re.match(r"^\d{8}$", parts[0].strip()):
            end += 1
        else:
            break
    data_lines = lines[start:end]
    rows = [line.split(",") for line in data_lines]
    ncols = len(rows[0])
    if not cols or len(cols) != ncols:
        cols = ["date"] + [f"col{i}" for i in range(1, ncols)]
    else:
        cols[0] = "date"
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", utc=True)
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce") / 100.0  # French data is in percent
    _save_parquet(key, df)
    LOG.info("fetched french %s rows=%d span=%s..%s", name, len(df), df["date"].min(), df["date"].max())
    return df


# ---------------------------------------------------------------------------
# FRED
# ---------------------------------------------------------------------------

def fetch_fred_series(series_id: str, use_cache: bool = True, retries: int = 3) -> pd.DataFrame:
    """The `requests` library has proven unreliable (hangs) against this specific
    host through the environment's proxy in testing, while plain `curl` succeeds
    consistently and quickly -- shell out to curl instead."""
    key = f"fred_{series_id}"
    if use_cache:
        cached = _load_parquet(key)
        if cached is not None:
            return cached
    import subprocess
    url = f"{FRED_BASE}?id={series_id}"
    text = None
    last_err = None
    for i in range(retries):
        try:
            out = subprocess.run(["curl", "-sS", "-m", "30", url], capture_output=True, timeout=40)
            if out.returncode == 0 and out.stdout:
                text = out.stdout.decode("utf-8", errors="replace")
                break
            last_err = f"curl rc={out.returncode} stderr={out.stderr[:200]}"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(2 * (i + 1))
    if text is None:
        LOG.warning("fred fetch failed for %s: %s", series_id, last_err)
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO(text))
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    df = df.dropna()
    _save_parquet(key, df)
    LOG.info("fetched fred %s rows=%d span=%s..%s", series_id, len(df), df["date"].min(), df["date"].max())
    return df


# ---------------------------------------------------------------------------
# CFTC Commitments of Traders (Socrata legacy futures-only report)
# ---------------------------------------------------------------------------

def fetch_cftc_cot(market_name_contains: str, start_year: int = 1994, use_cache: bool = True) -> pd.DataFrame:
    key = f"cftc_{re.sub(r'[^A-Za-z0-9]', '_', market_name_contains)}"
    if use_cache:
        cached = _load_parquet(key)
        if cached is not None:
            return cached
    all_rows = []
    offset = 0
    limit = 1000
    where = f"market_and_exchange_names like '%{market_name_contains}%' AND report_date_as_yyyy_mm_dd >= '{start_year}-01-01'"
    for _ in range(50):
        params = {"$where": where, "$limit": limit, "$offset": offset, "$order": "report_date_as_yyyy_mm_dd"}
        r = SESSION.get(CFTC_BASE, params=params, timeout=30)
        if r.status_code != 200:
            LOG.warning("cftc fetch failed: HTTP %s body=%s", r.status_code, r.text[:200])
            break
        rows = r.json()
        if not rows:
            break
        all_rows.extend(rows)
        offset += limit
        time.sleep(0.2)
        if len(rows) < limit:
            break
    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows)
    df["report_date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"], utc=True)
    for c in ["open_interest_all", "noncomm_positions_long_all", "noncomm_positions_short_all",
              "comm_positions_long_all", "comm_positions_short_all"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    _save_parquet(key, df)
    LOG.info("fetched cftc %s rows=%d span=%s..%s", market_name_contains, len(df),
              df["report_date"].min(), df["report_date"].max())
    return df


# ---------------------------------------------------------------------------
# FOMC historical calendar
# ---------------------------------------------------------------------------

_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


_MEETING_PATTERN = re.compile(
    r"(" + "|".join(_MONTHS) + r")\s+(\d{1,2})(?:-(\d{1,2}))?\*?\s+(Meeting|Statement)")
_YEAR_SECTION_PATTERN = re.compile(r"(\d{4})\s+FOMC Meetings")


def _extract_meeting_dates_from_html(html: str, fallback_year: int | None = None) -> set:
    """Announcement date = last day of the meeting range (statement/decision day),
    NOT the later minutes-release date. Requires the date to be immediately
    followed by 'Meeting' or 'Statement' (excludes '(Released <date>)' minutes
    mentions, and excludes ad-hoc 'Conference Call' entries on historical pages
    which are unscheduled and not comparable to a publicly pre-known event)."""
    text = re.sub("<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    year_positions = [(m.start(), int(m.group(1))) for m in _YEAR_SECTION_PATTERN.finditer(text)]
    dates = set()
    for m in _MEETING_PATTERN.finditer(text):
        pos = m.start()
        yr = fallback_year
        for p, y in year_positions:
            if p <= pos:
                yr = y
            else:
                break
        if yr is None:
            continue
        month, d1, d2, _kind = m.groups()
        day = d2 or d1
        try:
            dates.add(pd.Timestamp(f"{month} {day} {yr}", tz="UTC"))
        except Exception:
            continue
    return dates


def fetch_fomc_meeting_dates(start_year: int = 1994, end_year: int = 2026, use_cache: bool = True) -> list:
    key = "fomc_meeting_dates"
    cache_json = CACHE_DIR / f"{key}.json"
    if use_cache and cache_json.exists():
        return [pd.Timestamp(d, tz="UTC") for d in json.loads(cache_json.read_text())]

    dates = set()
    # current calendar page covers roughly the last 5-6 years in one page
    try:
        r = SESSION.get(f"{FED_CAL_BASE}/fomccalendars.htm", timeout=20)
        if r.status_code == 200:
            dates |= _extract_meeting_dates_from_html(r.text)
    except Exception:
        pass
    # historical pages, one per year, cover everything else
    for year in range(start_year, end_year + 1):
        url = f"{FED_CAL_BASE}/fomchistorical{year}.htm"
        try:
            r = SESSION.get(url, timeout=20)
        except Exception:
            continue
        if r.status_code != 200:
            continue
        dates |= _extract_meeting_dates_from_html(r.text, fallback_year=year)
        time.sleep(0.3)
    dates = sorted(d for d in dates if start_year <= d.year <= end_year)
    cache_json.write_text(json.dumps([d.strftime("%Y-%m-%d") for d in dates]))
    LOG.info("parsed %d FOMC scheduled-meeting announcement dates %s..%s", len(dates),
              dates[0] if dates else None, dates[-1] if dates else None)
    return dates


if __name__ == "__main__":
    print(fetch_yahoo_history("^GSPC").shape)
    print(fetch_french_dataset("F-F_Research_Data_5_Factors_2x3_daily").shape)
    print(fetch_fred_series("DGS10").shape)
