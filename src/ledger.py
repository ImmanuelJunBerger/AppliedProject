"""Append-only trials ledger (Section 7). ONE ledger for the entire program.

The row is written BEFORE the test runs (`open_trial`), then completed after
(`close_trial`). That ordering is deliberate: it makes it impossible to quietly
drop a test whose result you didn't like, because the row already exists.

The Deflated Sharpe uses `total_trials()` — every row, including variants,
overlays, and abandoned ideas — not the survivor's own count.
"""
from __future__ import annotations

import csv
import threading
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "results_v7" / "trials_ledger.csv"
_LOCK = threading.Lock()

FIELDS = ["trial_id", "timestamp", "family", "hypothesis_one_line", "mechanism_who_loses",
          "params", "timeframe", "universe", "tier", "partition_used",
          "n_trades", "gross_edge_bps", "net_edge_bps_pessimistic", "sharpe_raw",
          "gates_passed", "gates_failed", "outcome", "cause_of_death", "notes"]


def _ensure():
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if not LEDGER.exists():
        with open(LEDGER, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()


def open_trial(trial_id: str, family: str, hypothesis: str, mechanism: str, params: str,
               timeframe: str, universe: str, tier: str, partition: str, notes: str = "") -> str:
    """Write the row BEFORE running the test."""
    _ensure()
    with _LOCK, open(LEDGER, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writerow({
            "trial_id": trial_id, "timestamp": pd.Timestamp.utcnow().isoformat(),
            "family": family, "hypothesis_one_line": hypothesis,
            "mechanism_who_loses": mechanism, "params": params, "timeframe": timeframe,
            "universe": universe, "tier": tier, "partition_used": partition,
            "n_trades": "", "gross_edge_bps": "", "net_edge_bps_pessimistic": "",
            "sharpe_raw": "", "gates_passed": "", "gates_failed": "",
            "outcome": "OPEN", "cause_of_death": "", "notes": notes})
    return trial_id


def close_trial(trial_id: str, n_trades, gross_bps, net_bps, sharpe, outcome,
                cause_of_death: str = "", gates_passed: str = "", gates_failed: str = "",
                notes: str = ""):
    """Complete the row in place. Never deletes; only fills the result fields."""
    _ensure()
    with _LOCK:
        df = pd.read_csv(LEDGER, dtype=str, keep_default_na=False)
        m = df["trial_id"] == trial_id
        if not m.any():
            return
        i = df.index[m][-1]
        for col, val in [("n_trades", n_trades), ("gross_edge_bps", gross_bps),
                         ("net_edge_bps_pessimistic", net_bps), ("sharpe_raw", sharpe),
                         ("outcome", outcome), ("cause_of_death", cause_of_death),
                         ("gates_passed", gates_passed), ("gates_failed", gates_failed)]:
            df.loc[i, col] = "" if val is None else str(val)
        if notes:
            df.loc[i, "notes"] = (df.loc[i, "notes"] + " | " + notes).strip(" |")
        df.to_csv(LEDGER, index=False)


def bulk_close(rows: list[dict]):
    """Efficient completion of many trials at once (Tier-1 screen)."""
    _ensure()
    with _LOCK:
        df = pd.read_csv(LEDGER, dtype=str, keep_default_na=False)
        idx = {t: i for i, t in enumerate(df["trial_id"])}
        for r in rows:
            i = idx.get(r["trial_id"])
            if i is None:
                continue
            for k, v in r.items():
                if k != "trial_id" and k in df.columns:
                    df.loc[i, k] = "" if v is None else str(v)
        df.to_csv(LEDGER, index=False)


def total_trials() -> int:
    """Trials that consumed multiple-testing budget -- the DSR denominator.

    Two outcomes are excluded, both because they represent zero executed tests:
      SKIPPED_NO_DATA -- no data source, so no test ran and no selection
                         pressure was spent. Kept in the ledger because "never
                         measured" and "measured and barren" are different findings.
      SUPERSEDED      -- a placeholder skip row that a later probe overturned;
                         the real test exists under its own trial id, so counting
                         both would double-charge the same hypothesis.
    Everything else counts, forever, including variants and abandoned runs.
    """
    if not LEDGER.exists():
        return 0
    df = pd.read_csv(LEDGER, dtype=str, keep_default_na=False)
    return int((~df["outcome"].isin(["SKIPPED_NO_DATA", "SUPERSEDED"])).sum())


def load() -> pd.DataFrame:
    if not LEDGER.exists():
        return pd.DataFrame(columns=FIELDS)
    return pd.read_csv(LEDGER, dtype=str, keep_default_na=False)
