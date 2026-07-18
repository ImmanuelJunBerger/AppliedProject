"""Strategy 5: new-launch / DexScreener momentum. HONESTY GATE.

This strategy category is explicitly flagged by the task as unreliable by
construction: DexScreener's free API gives only a live snapshot (current
token-profiles feed + current pair stats), not a point-in-time historical
panel of every token that ever launched. There is no way, from free data, to
see the population of launches that already went to zero and vanished from
the feed. Any positive-looking number from this strategy is a description of
survivors, not evidence of a tradeable edge.

What this script actually does (best-effort, no fabrication):
  1. Pull DexScreener's "latest token profiles" feed (today's newly
     profiled/promoted tokens across chains) -- a convenience/marketing feed,
     NOT a complete launch registry. This is itself a selection-biased
     sample (profiled/boosted tokens skew toward ones already getting
     attention/promoted, not a random sample of all launches).
  2. For each, query the live pair data. Count how many resolve to a real
     trading pair with nonzero liquidity right now vs how many are already
     dead/unresolvable -- this is a real, computable rug/attrition-rate
     proxy, reported honestly as a lower bound (it only sees deaths that
     happen to still be visible; anything that fully delisted from
     DexScreener between profiling and now is invisible to us too).
  3. Report descriptive stats (price change distribution, liquidity) for the
     SURVIVING tokens only, labeled UNRELIABLE, with no claimed Sharpe,
     no claimed backtest, no claimed entry/exit trading rule performance.
     A real entry/exit backtest is NOT attempted because there is no
     historical panel to backtest against -- doing so would require
     fabricating point-in-time data.
"""
from __future__ import annotations

import time
import pandas as pd

from . import data


def run() -> dict:
    profiles = data.dexscreener_token_profiles_latest(use_cache=False)
    n_profiled = len(profiles)
    rows = []
    n_unresolvable = 0
    now_ms = int(time.time() * 1000)
    for _, row in profiles.iterrows():
        chain, addr = row["chainId"], row["tokenAddress"]
        try:
            js = data._get(f"{data.DEXSCREENER}/token-pairs/v1/{chain}/{addr}")
        except Exception:
            n_unresolvable += 1
            continue
        if not js:
            n_unresolvable += 1
            continue
        pair = max(js, key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0)
        liq = (pair.get("liquidity") or {}).get("usd", 0) or 0
        if liq < 100:
            n_unresolvable += 1
        pc = pair.get("priceChange") or {}
        created = pair.get("pairCreatedAt")
        age_hours = (now_ms - created) / 3.6e6 if created else None
        rows.append({
            "chain": chain, "symbol": pair.get("baseToken", {}).get("symbol"),
            "liquidity_usd": liq, "volume_h24_usd": (pair.get("volume") or {}).get("h24"),
            "priceChange_h1_pct": pc.get("h1"), "priceChange_h6_pct": pc.get("h6"),
            "priceChange_h24_pct": pc.get("h24"), "age_hours": age_hours,
            "fdv_usd": pair.get("fdv"),
        })
        time.sleep(0.1)

    df = pd.DataFrame(rows)
    df.to_csv("results/new_launch_snapshot.csv", index=False)

    result = {
        "n_profiled_tokens_in_feed": n_profiled,
        "n_unresolvable_or_dead_or_illiquid": n_unresolvable,
        "attrition_rate_pct_LOWER_BOUND": round(100 * n_unresolvable / n_profiled, 1) if n_profiled else None,
        "n_surviving_with_liquidity": len(df[df["liquidity_usd"] >= 100]) if len(df) else 0,
    }
    if len(df):
        live = df[df["liquidity_usd"] >= 100]
        if len(live):
            result["survivors_median_priceChange_h24_pct_UNRELIABLE"] = round(float(live["priceChange_h24_pct"].median()), 1)
            result["survivors_median_age_hours"] = round(float(live["age_hours"].median()), 2)
            result["survivors_median_liquidity_usd"] = round(float(live["liquidity_usd"].median()), 0)
    result["HONESTY_NOTE"] = (
        "No backtest was run: no point-in-time historical panel exists in free data to backtest "
        "entry/exit rules against. Any price-change stats above describe only tokens still visible "
        "and liquid right now -- tokens that already rugged/delisted between being profiled and this "
        "query are excluded from the 'survivors' stats, biasing them strongly upward. Do not treat "
        "any number in this file as a tradeable edge."
    )
    return result


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
