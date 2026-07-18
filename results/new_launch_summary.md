# Strategy 5: New-launch / DexScreener momentum — HONESTY GATE

**No backtest was run and none is reported.** DexScreener's free API only exposes a live snapshot
(current "latest profiled tokens" feed + current pair stats) — there is no historical point-in-time
panel of launches available for free, so there is nothing to backtest an entry/exit rule against
without fabricating data. Per the task's explicit instruction, the answer for a real backtest here
is "insufficient data," full stop.

**What was measured instead (real, not fabricated):** snapshot of 30 tokens from DexScreener's
"latest token profiles" feed (mostly Solana pump.fun launches + a "robinhood"-chain feed of
synthetic/tokenized assets), each looked up live for its trading pair.

- **6 of 30 (20%) were already unresolvable / had no real trading pair / had <$100 liquidity** —
  this is a real, computed **lower bound** on the rug/attrition rate. It is a lower bound because
  tokens that fully delisted from DexScreener between being profiled and this query are invisible
  to us too, so the true failure rate is higher, likely much higher — pump.fun-style launches are
  widely documented to fail (go to ~zero liquidity) at rates well above 90% within days.
- Among the 24 "surviving" tokens: median age ~1 hour, median 24h price change **+46.2%**, median
  liquidity ~$10.1k.

**This +46.2% number is explicitly labeled UNRELIABLE and is not a strategy return.** It describes
only tokens that happened to still be alive and liquid at the moment of the query — the tokens that
already went to zero in the hours since being profiled are excluded by construction. This is
survivorship bias in its purest form: a population where failures vanish and only winners remain
visible will always look profitable in a snapshot, regardless of whether any tradeable edge exists.
Raw per-token data: `results/new_launch_snapshot.csv`.

**Verdict: no tradeable edge is claimed or supportable from this data.** The one honest,
load-bearing finding here is the ≥20% near-instant attrition rate — a caution about this token
category's base rate, not a strategy.
