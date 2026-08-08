"""Data partition for the Run 7 discovery program. Section 2.

Written BEFORE any hypothesis was generated or any strategy result was seen.
Boundaries are hard-coded here and asserted at load time by `assert_partition`.

    Development  60%  -> idea generation, screening, parameter selection
    Validation   25%  -> walk-forward + gate testing, never fit to
    Final holdout15%  -> LOCKED. Max 3 touches for the entire program.

The holdout is the MOST RECENT slice on purpose: recency is what tests whether
an edge still exists, which is the only question that matters for deployment.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PARTITION_FILE = ROOT / "results_v7" / "partitions.json"
HOLDOUT_LEDGER = ROOT / "results_v7" / "holdout_touches.csv"

# Full study span (Binance USD-M futures bulk archive coverage)
SPAN_START = pd.Timestamp("2021-01-01", tz="UTC")
SPAN_END = pd.Timestamp("2026-08-01", tz="UTC")

_total_days = (SPAN_END - SPAN_START).days
DEV_END = SPAN_START + pd.Timedelta(days=int(_total_days * 0.60))
VAL_END = SPAN_START + pd.Timedelta(days=int(_total_days * 0.85))

PARTITIONS = {
    "development": (SPAN_START, DEV_END),
    "validation": (DEV_END, VAL_END),
    "holdout": (VAL_END, SPAN_END),
}
MAX_HOLDOUT_TOUCHES = 3


def write_partition_file() -> dict:
    PARTITION_FILE.parent.mkdir(parents=True, exist_ok=True)
    d = {k: {"start": str(v[0]), "end": str(v[1]),
             "days": (v[1] - v[0]).days,
             "pct": round(100 * (v[1] - v[0]).days / _total_days, 1)}
         for k, v in PARTITIONS.items()}
    d["_span"] = {"start": str(SPAN_START), "end": str(SPAN_END), "total_days": _total_days}
    d["_max_holdout_touches"] = MAX_HOLDOUT_TOUCHES
    PARTITION_FILE.write_text(json.dumps(d, indent=2))
    return d


def assert_partition() -> None:
    """Fail loudly if partitions are non-contiguous, overlapping, or mis-ordered."""
    dev, val, hold = PARTITIONS["development"], PARTITIONS["validation"], PARTITIONS["holdout"]
    assert dev[0] == SPAN_START, "development must start at span start"
    assert dev[1] == val[0], "development/validation must be contiguous"
    assert val[1] == hold[0], "validation/holdout must be contiguous"
    assert hold[1] == SPAN_END, "holdout must end at span end"
    assert dev[0] < dev[1] < val[1] < hold[1], "partitions must be strictly ordered"
    assert hold[1] > val[1] > dev[1], "holdout must be the MOST RECENT slice"
    if PARTITION_FILE.exists():
        on_disk = json.loads(PARTITION_FILE.read_text())
        assert on_disk["development"]["start"] == str(dev[0]), "partition file drift: development start"
        assert on_disk["holdout"]["end"] == str(hold[1]), "partition file drift: holdout end"


def slice_to(df: pd.DataFrame, partition: str, tcol: str = "timestamp") -> pd.DataFrame:
    assert partition in PARTITIONS, f"unknown partition {partition}"
    t0, t1 = PARTITIONS[partition]
    return df[(df[tcol] >= t0) & (df[tcol] < t1)]


def holdout_touches_used() -> int:
    if not HOLDOUT_LEDGER.exists():
        return 0
    return max(0, sum(1 for _ in open(HOLDOUT_LEDGER)) - 1)


def log_holdout_touch(reason: str, strategies: str) -> int:
    """Every holdout read must go through here. Refuses beyond the cap."""
    HOLDOUT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    used = holdout_touches_used()
    if used >= MAX_HOLDOUT_TOUCHES:
        raise RuntimeError(f"HOLDOUT EXHAUSTED: {used}/{MAX_HOLDOUT_TOUCHES} touches already used. "
                           "There is no second holdout.")
    new = not HOLDOUT_LEDGER.exists()
    with open(HOLDOUT_LEDGER, "a") as f:
        if new:
            f.write("touch_number,timestamp,reason,strategies\n")
        f.write(f"{used+1},{pd.Timestamp.utcnow()},{reason},\"{strategies}\"\n")
    return used + 1


if __name__ == "__main__":
    d = write_partition_file()
    assert_partition()
    print(json.dumps(d, indent=2))
