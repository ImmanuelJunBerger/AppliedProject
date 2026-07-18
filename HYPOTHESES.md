# HYPOTHESES.md — Pre-registration for Run 2 (Crypto Edge Hunt)

**Written:** 2026-07-18 20:20 UTC, before any Run-2 data was fetched or examined. Everything below
was decided from domain reasoning and Run-1's already-published findings (`RESULTS.md`), not from
peeking at new data. Any hypothesis conceived after this point goes in the POST-HOC section at the
bottom and is never treated as a finding, however good it looks.

## Global rules locked in before testing
- **Holdout**: every hypothesis with a date axis splits history into IN-SAMPLE = oldest ~70% and
  HOLDOUT = newest ~30%. Holdout is touched exactly once, at the end, only for hypotheses that
  already cleared the in-sample bar. Touching holdout more than once for the same hypothesis marks
  it dead regardless of the number.
- **N_TESTS**: every (hypothesis × parameter variant × asset-universe variant) combination that
  produces a Sharpe/p-value is one test, logged in `results/n_tests_registry.csv` as it happens.
  Parameter grids below are fixed now — no grid expansion after seeing interim results.
- **Minimum evidence bar for calling anything a finding** (all required): ≥50 trades (flag if
  <100), positive net Sharpe IS **and** holdout, survives Benjamini-Hochberg FDR at q=0.10 across
  the full N_TESTS pool, a stated structural reason, and survives dropping the single best token
  and the single best month.
- Cost model, universe filters (`NON_CRYPTO_BASES`, `TOKENIZED_EQUITY_BASES`), and fee/slippage
  constants are reused unchanged from `src/engine.py` / `src/data.py` (Run 1).

---

## TRACK A — fixing Run 1's two live leads

### A1. Point-in-time cross-sectional momentum
- **Why it's being redone**: Run 1 ranked by *today's* volume and applied that universe
  retroactively across 2 years (0/50 symbols had 90%+ history over the window) — look-ahead bias
  in universe construction, not just survivorship.
- **Structural family**: none of the three cleanly (momentum is a well-known, heavily-arbitraged
  effect at institutional size). Flagged for extra skepticism per the ROLE instructions; a survival
  here is evidence the Run-1 number was an artifact, not evidence of a real retail edge, unless it
  also clears the evidence bar.
- **Exact rule**: at each weekly rebalance date, build the tradeable universe using ONLY the top-50
  USDT pairs by trailing 24h quote volume *as of that date* (computed from the historical daily
  volume series already cached, not the live ticker). Tokens must have >= `lookback` days of prior
  history *as of that date* to be ranked (else excluded that week, not backfilled). Rank by trailing
  return, long top quintile / short bottom quintile, equal-weighted.
- **Parameter grid** (fixed): lookback ∈ {7, 14, 30} days × {long/short, long-only} = 6 variants.
- **Prediction**: the 0.86 net Sharpe (7d, long-only) shrinks substantially or goes negative once
  the universe can no longer see the future. Reporting either outcome honestly.

### A2. Pooled pairs/cointegration trades
- **Why it's being redone**: Run 1's per-pair trade counts (1-3 typical) had no statistical power.
- **Structural family**: none cleanly (classic stat-arb, usually arbitraged away at size; retail
  edge case would be "too small to matter" if restricted to illiquid alt pairs — noted, not assumed).
- **Exact rule**: reuse Run 1's exact walk-forward Engle-Granger pair selection (180d train / 60d
  test, p<0.05, trained hedge ratio/z-score, entry |z|>2, exit |z|<0.5, stop |z|>4) across the same
  three sectors (L1, DeFi, Meme), but this time pool every individual trade (not per-pair equity
  curves) into one distribution and evaluate the pooled Sharpe/trade-level stats as a single
  strategy. IS/holdout split applied on trade *entry date*.
- **Parameter grid**: 3 sectors, no new variants (reusing Run 1's fixed rule) = 1 test (pooled
  strategy) + 3 sector-level sub-tests = 4 tests.
- **Prediction**: pooled trade count clears 50 for at least one sector; pooled Sharpe likely still
  near zero given Run 1's per-pair Sharpes clustered near zero, but now with enough power to say so
  with actual confidence instead of noise.

---

## TRACK B — structural edge hunt

### B1. Token unlock / vesting cliff drift
- **Family**: forced/insensitive flow.
- **Rule**: for tokens with a freely-obtainable unlock calendar (>2% of circulating supply in a
  single event), measure cumulative abnormal return (vs. an equal-weight BTC/ETH benchmark) in
  windows [-7,-1] and [0,+7] trading days around the unlock date.
- **Parameter grid**: 2 windows × {all unlocks, >5% of float only} = 4 tests, per data source found.
- **Data check required first**: none of Run 1's four sources (Binance-vision, OKX, Hyperliquid,
  DexScreener) publish unlock calendars. If no free calendar source is found in Track B execution,
  this is logged **SKIPPED — insufficient data** and zero tests are counted for it. No dates will
  be guessed or hand-entered from memory.

### B2. Cross-venue funding-rate dispersion (spread, not level)
- **Family**: too small to matter.
- **Rule**: for assets listed as perps on both Hyperliquid and OKX (Binance/Bybit unreachable —
  logged as a real constraint, not worked around), compare funding rates at matching UTC funding
  timestamps. When |rate_HL - rate_OKX| × notional exceeds round-trip cost (4 taker legs: 2 entries
  + 2 exits, both venues, plus an assumed fixed transfer-cost buffer), simulate long the
  negative/cheap venue + short the positive/expensive venue, hold to next funding or convergence.
- **Parameter grid**: transfer-cost buffer ∈ {0bps, 10bps} × asset set {BTC, ETH, SOL} = 6 tests.
- **Prediction**: dispersion exists intermittently but the fixed-cost floor (4 legs of fees) likely
  eats most of it at 1,000 EUR size; expect a mostly-null result with maybe brief windows that work.

### B3. Newly-listed perp funding richness
- **Family**: too small + too new.
- **Rule**: proxy "days since listing" per Hyperliquid coin as (query date − first available funding
  history timestamp for that coin). Bucket coins by listing age (0-30d, 30-90d, 90d+) and compare
  mean |funding rate| and a simple carry-collection backtest (same entry rule as Run 1's funding
  carry) by bucket.
- **Parameter grid**: 3 age buckets × 2 metrics (mean |funding|, backtested net Sharpe) = 6 tests
  (the mean-|funding| comparisons are descriptive/pre-screening, not scored as findings on their
  own — only the backtested Sharpe entries count toward the evidence bar).
- **Prediction**: newer listings show higher, more volatile funding; whether it's *capturable* net
  of costs and thin liquidity (higher slippage bucket) is the real test.

### B4. Post-liquidation-cascade reversion
- **Family**: forced flow.
- **Rule**: proxy a cascade day as trailing-30d-vol-adjusted daily range > 3σ AND daily volume > 3×
  its trailing-30d average, computed per symbol in the Run-1 top-50 universe (point-in-time
  version from A1). On cascade days, test 1-day and 3-day forward mean reversion (buy if the
  cascade day was down, sell if up), separately from Run 1's blanket daily reversal (which used
  every day, not specifically cascade days — this tests a distinct causal claim).
- **Parameter grid**: holding period {1d, 3d} × direction-conditional {down-cascade only,
  up-cascade only, both} = 6 tests.
- **Prediction**: uncertain a priori — could go either way; explicitly must check this isn't just
  Run 1's already-killed reversal effect wearing a cascade costume (compare cascade-day-only
  reversal Sharpe against all-day reversal Sharpe from Run 1 as a sanity anchor, not a new test).

### B5. Open-interest / price divergence
- **Family**: forced-flow adjacent (flagged for skepticism — classic TA signal, no strong forcing
  mechanism beyond "someone eventually has to close").
- **Rule**: using OKX open-interest history (`/api/v5/rubik/stat/contracts/open-interest-volume` or
  equivalent) for BTC/ETH/SOL swaps, build a daily OI-change vs price-change signal: long when OI
  rising + price falling (interpreted as short-covering fuel) or price rising + OI falling
  (short squeeze continuation) — test both sign conventions since prior literature disagrees on
  which regime is bullish.
- **Parameter grid**: 2 sign conventions × holding period {1d, 3d} = 4 tests.
- **Data check required first**: confirm the OKX OI endpoint is reachable/free before counting
  these tests; if not, log SKIPPED — insufficient data.

### B6. Funding-settlement microstructure
- **Family**: calendar-predictable.
- **Rule**: using the finest free intraday granularity available (hourly — true minute bars are not
  confirmed free; noted as a real resolution limitation), test mean return in the hour immediately
  before vs. immediately after each 8h funding settlement (00:00/08:00/16:00 UTC) on BTC/ETH perps
  (OKX + HL), vs. all other hours as a control.
- **Parameter grid**: 2 venues × {pre-settlement hour, post-settlement hour} = 4 tests.
- **Prediction**: per the task's own steer, likely dies on costs at hourly resolution even if a
  raw statistical pattern exists — that is an acceptable, valid outcome.

### B7. Hour-of-day / day-of-week seasonality
- **Family**: none cleanly (explicitly the highest false-positive-risk hypothesis here — many
  buckets, no strong structural story). Held to strictest scrutiny; a raw-significant survivor here
  is the single most likely false positive in the whole run and will be treated as such even if it
  technically clears BH correction, given how it interacts with the other 30 seasonality buckets.
- **Rule**: for BTC and ETH (chosen as the only assets with clean full-history hourly OKX/HL data),
  compute mean hourly return for each of 24 hour-of-day buckets and 7 day-of-week buckets on
  in-sample data, identify the single best bucket per axis, then check it on holdout.
- **Parameter grid**: 2 assets × (24 hour buckets + 7 day buckets) = 62 individual bucket tests, but
  only the single best-in-sample bucket per (asset × axis) is carried to holdout = 2 assets × 2 axes
  = 4 holdout-tested candidates. **All 62 in-sample bucket comparisons count toward N_TESTS**, not
  just the 4 that reach holdout — this is exactly the kind of undercounting that makes seasonality
  results look better than they are, and pre-registering the full 62 here prevents doing that later.

### B8. Exchange listing announcement drift
- **Family**: forced-flow / calendar.
- **Rule**: price response in [0,+3] days after a major-venue new-listing announcement.
- **Data check required first**: none of the four Run-1 sources are news/announcement feeds. If no
  free source of historical listing-announcement timestamps is found, this is logged
  **SKIPPED — insufficient data** with zero tests counted, per the task's explicit instruction to
  skip cleanly rather than force it.

### B9. Stablecoin micro-depeg reversion
- **Family**: too small to matter.
- **Rule**: using Binance-vision fine-grained klines (1m/5m if available) for USDC/USDT, FDUSD/USDT,
  TUSD/USDT, DAI-equivalent if listed, measure deviations from 1.0000. Whenever |deviation| exceeds
  round-trip cost (2× taker spot fee + assumed 5bps slippage on a stable pair), simulate a reversion
  trade back to peg, capped hold of 24h.
- **Parameter grid**: 3-4 stablecoin pairs × entry threshold {cost-only, cost+2bps buffer} = 6-8
  tests depending on how many pairs have data.
- **Prediction**: very likely null — stables rarely deviate enough to clear costs, and when they do
  (e.g. a real depeg event) the "reversion" assumption itself becomes risky (peg could break for
  real). Cheap to test, expected to die quickly.

---

## POST-HOC (untrusted) — anything conceived after this document was written
*(empty at time of writing; anything added here during the run is explicitly excluded from
`RESULTS_V2.md`'s ranked findings table and can only appear, if at all, in a clearly labeled
"ideas for a future run" note.)*
