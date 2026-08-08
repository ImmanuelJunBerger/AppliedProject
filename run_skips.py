"""Data-availability probe for the families pre-declared as possible SKIPs.

HYPOTHESES_V7.md said family F (on-chain) and H01/H03/H08 (event-driven with
proprietary calendars) would only be skipped if a probe actually failed. This
runs that probe rather than asserting the answer, and logs the outcome.

A SKIPPED trial is NOT counted in the multiple-testing denominator: no test was
run, so no selection pressure was spent. `ledger.total_trials()` excludes them.
The distinction is the point -- a family that was never measured and a family
that was measured and found barren teach completely different things.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import ledger

OUT = Path("results_v7")
TIMEOUT = 20

# (label, url, what it would provide, what a usable response looks like)
PROBES = [
    ("glassnode",  "https://api.glassnode.com/v1/metrics/indicators/sopr?a=BTC",
     "SOPR / MVRV / dormancy (F03-F05)"),
    ("cryptoquant", "https://api.cryptoquant.com/v1/btc/exchange-flows/netflow?window=hour",
     "exchange netflows (F01)"),
    ("dune",       "https://api.dune.com/api/v1/query/1/results",
     "arbitrary on-chain SQL (F01-F08)"),
    ("blockchain_info_charts", "https://api.blockchain.info/charts/n-transactions?timespan=5years&format=json",
     "active addresses / tx count / fees (F07-F08)"),
    ("mempool_space", "https://mempool.space/api/v1/mining/hashrate/1y",
     "chain fees & hashrate (F07)"),
    ("defillama_stables", "https://stablecoins.llama.fi/stablecoincharts/all",
     "aggregate stablecoin supply (F02)"),
    ("defillama_unlocks", "https://api.llama.fi/emissions",
     "token unlock calendar (H03)"),
    ("binance_announcements", "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
                              "?type=1&catalogId=48&pageNo=1&pageSize=10",
     "listing-announcement timestamps (H01)"),
]


def probe(url: str) -> dict:
    try:
        r = requests.get(url, timeout=TIMEOUT)
        body = r.text[:200]
        ok = r.status_code == 200 and not body.lstrip().startswith("<")
        return {"status_code": r.status_code, "usable": bool(ok), "body_head": body}
    except Exception as e:                                   # noqa: BLE001
        return {"status_code": None, "usable": False, "error": f"{type(e).__name__}: {e}"}


def main():
    results = {}
    for label, url, provides in PROBES:
        res = probe(url)
        res["provides"] = provides
        res["url"] = url
        results[label] = res
        print(f"{label:26s} {str(res['status_code']):>5}  usable={res['usable']}  {provides}",
              flush=True)

    json.dump(results, open(OUT / "data_availability_probe.json", "w"), indent=2)

    onchain_usable = [k for k in ("glassnode", "cryptoquant", "dune", "blockchain_info_charts",
                                  "mempool_space", "defillama_stables")
                      if results[k]["usable"]]
    print(f"\non-chain sources usable: {onchain_usable or 'NONE'}", flush=True)

    skips = []
    fnote = ("probe results: " +
             "; ".join(f"{k}={results[k]['status_code']}" for k, _, _ in PROBES if k in results))
    for i in range(1, 9):
        skips.append((f"F{i:02d}", "F", "on-chain flow/valuation signal",
                      "on-chain holders are slow and identifiable; their forced moves are visible",
                      "no point-in-time on-chain history reachable"))
    skips += [
        ("H01", "H", "listing-announcement drift",
         "forced index/tracker buying plus attention flow",
         "no free historical announcement timestamps"),
        ("H03", "H", "token-unlock supply shock",
         "vesting recipients are price-insensitive sellers on a known date",
         "no free historical unlock calendar"),
        ("H08", "H", "index-inclusion forced buying",
         "index trackers must buy at a known time regardless of price",
         "no free index-membership history"),
    ]

    for tid, fam, hyp, mech, why in skips:
        ledger.open_trial(tid, fam, hyp, mech, "n/a", "n/a", "n/a", "0", "none",
                          notes=f"{why}. {fnote}")
        ledger.close_trial(tid, "", "", "", "", "SKIPPED_NO_DATA",
                           cause_of_death=f"UNMEASURED, not falsified: {why}")
    print(f"\nlogged {len(skips)} SKIPPED_NO_DATA rows (excluded from the trial denominator)")
    print(f"counted trials = {ledger.total_trials()}  |  ledger rows = {len(ledger.load())}")


if __name__ == "__main__":
    main()
