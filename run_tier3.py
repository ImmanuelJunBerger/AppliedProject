"""Tier 3 -- final holdout. NOT EXECUTED. This file records why.

Tier 3 admits only strategies that cleared the Tier-2 battery completely. Four
candidates reached Tier 2 (A12_z2.0, A12_z3.0, F02_stablecoin_growth,
F08_active_address_growth) and all four failed multiple gates, including the
deflated Sharpe against the full trial count in every case.

So the holdout is not touched. Running it anyway would be the single most
damaging thing this program could do: there is no candidate whose holdout result
could change the verdict, so the only possible effect is to burn one of three
irreplaceable touches and create an opportunity to rationalise a lucky number.
An unspent holdout is worth more than a curiosity satisfied.

This script deliberately refuses to load the holdout partition. It asserts the
touch counter is still zero and exits.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import ledger, partitions as PART

OUT = Path("results_v7")


def main():
    df = ledger.load()
    eligible = df[df["outcome"] == "ADVANCE_TIER3"]
    tier2 = df[df["outcome"].isin(["ADVANCE_TIER3", "KILLED_TIER2"])]

    print(f"Tier-2 candidates evaluated : {len(tier2)}")
    print(f"cleared the full battery    : {len(eligible)}")
    for _, r in tier2.iterrows():
        print(f"  {r['trial_id']:34s} {r['outcome']:14s} {r['cause_of_death'][:80]}")

    if len(eligible) == 0:
        used = PART.holdout_touches_used()
        assert used == 0, f"holdout was touched ({used}) despite there being no eligible strategy"
        print(f"\nNO ELIGIBLE STRATEGY -> holdout NOT touched. "
              f"{used}/{PART.MAX_HOLDOUT_TOUCHES} touches used; "
              f"{PART.MAX_HOLDOUT_TOUCHES - used} remain for future work.")
        json.dump({"tier3_executed": False,
                   "eligible_strategies": 0,
                   "tier2_candidates": int(len(tier2)),
                   "holdout_touches_used": used,
                   "holdout_touch_budget": PART.MAX_HOLDOUT_TOUCHES,
                   "holdout_window": [str(PART.PARTITIONS["holdout"][0]),
                                      str(PART.PARTITIONS["holdout"][1])],
                   "reason": ("no Tier-2 survivor; touching the holdout could not change the "
                              "verdict and would spend an irreplaceable resource")},
                  open(OUT / "tier3_holdout.json", "w"), indent=2)
        return

    raise SystemExit("Eligible strategies exist -- Tier 3 must be run deliberately, "
                     "with frozen parameters and exactly one pass. Do not automate this.")


if __name__ == "__main__":
    main()
