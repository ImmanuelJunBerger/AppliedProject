# Crypto Edge Hunt v2 — READ THIS FIRST

**Headline finding: we tested 120 hypothesis/variant combinations and none survived correction.
Zero raw-significant results reach conventional significance after honest counting; the two that
were raw-significant (p<0.05) both run on 5-13 trades, far under the evidence bar, and neither
survives Benjamini-Hochberg FDR correction at q=0.10 across the 49 tests that produced a p-value.
Run 1's headline momentum lead (net Sharpe 0.86) is dead — it inverts to strongly negative once the
universe is built point-in-time instead of look-ahead. This is a complete, valuable, negative
answer, not a failure to find something.**

## The numbers behind that statement
- **N_TESTS = 120** total hypothesis/parameter-variant combinations run and logged in
  `results/n_tests_registry.csv`, exactly as pre-registered in `HYPOTHESES.md`. This includes 62
  individual hour/day-of-week bucket comparisons from B7 (seasonality) that were pre-committed to
  count toward the denominator even though only 4 of them (the best-in-sample bucket per
  asset×axis) were carried to a scored holdout test — the other 58 have no individual p-value and
  are not in the correction pool below, but they are the reason a seasonality "win" needs to be
  read as 1-of-62, not 1-of-1.
- **49 of the 120** tests produced an actual p-value (the rest are either data-availability skips
  — B1, B8 — or descriptive pre-screens not individually scored — most of B3's mean-funding rows,
  B7's raw bucket scan). BH-FDR correction (q=0.10) was applied to exactly these 49.
- **2 of 49 were raw-significant (p<0.05)**: `B3_carry_90d+_BTC` (p=0.019, but this is just Run 1's
  already-reported Hyperliquid BTC funding carry re-surfacing here as part of the age-bucket
  comparison, n=13 trades) and `B5_oi_BTC_A_short_cover_hold3d` (p=0.030, n=5 trades).
- **0 of 49 survive BH-FDR at q=0.10.** Full ranked table: `results/bh_correction_table.csv`.
- **0 hypotheses clear the full minimum-evidence bar** (≥50 trades, positive net Sharpe IS AND
  holdout, survives BH, structural reason, survives dropping best token/month). Every candidate
  that looked good on at least one axis failed on trade count, holdout, or both.

## What is and isn't trustworthy here
- **Trustworthy (well-powered, holdout-tested, clean nulls or clean kills)**: A1 point-in-time
  momentum (105 trades, both IS and holdout decisively negative), A2 pooled pairs (94 trades, IS
  and holdout both negative), B4 cascade reversion (296-1,626 trades per variant, decisively
  negative), B6 settlement microstructure (1,200 hourly observations, decisively negative), B7
  seasonality (up to 408 holdout observations, decisively negative/non-significant), B9 stablecoin
  depeg (non-overlapping trades, small but clean negative).
- **Correctly inconclusive, not evidence of anything**: B2 (dispersion is real but tiny — 95th
  percentile ~13bps on BTC, versus a ~10bps round-trip cost floor — genuinely too small to trade,
  which is itself the "too small to matter" family's expected null), B3's carry backtests on actual
  young coins (only 1-2 trades available — the coins are too new to have enough history, which is
  the honest answer, not a workaround), B5's BTC "short-cover" convention (n=5-6, noise).
- **Cleanly skipped, not fabricated**: B1 (token unlocks — DeFiLlama's emissions endpoints returned
  HTTP 402, paid-only; no free calendar found) and B8 (listing announcements — no free
  announcement-timestamp source exists among reachable APIs). Zero tests counted for either.

## Ranked table (all scored tests with ≥30 trades, sorted by holdout/IS Sharpe)

| Test | Family | Trades | Sharpe IS | Sharpe Holdout | Raw p | BH q=0.10 | Verdict |
|---|---|---|---|---|---|---|---|
| B4 cascade reversion (hold1d, down-only) | forced_flow | 296 | -2.85 (full-sample) | n/a (no split) | 0.999 | fail | Decisively negative, well-powered |
| B4 cascade reversion (hold3d, down-only) | forced_flow | 295 | -6.09 | n/a | 1.000 | fail | Decisively negative |
| B6 OKX BTC pre-settlement hour | calendar | 1200 | -21.31 (net) | n/a | 1.000 | fail | Decisively negative/non-sig |
| B6 OKX ETH pre-settlement hour | calendar | 1200 | -17.24 (net) | n/a | 1.000 | fail | Decisively negative/non-sig |
| A1 momentum 7d long-only (PIT) | none — extra scrutiny | 105 | -1.35 | -3.20 | 0.946 (holdout) | fail | Run 1's 0.86 fully inverted |
| A1 momentum 14d long/short (PIT) | none | 105 | -0.40 | -1.92 | 0.875 (holdout) | fail | Negative IS and holdout |
| A2 pairs pooled (all sectors) | none — thin edge expected | 94 | -0.32 | -0.23 | 0.688 (holdout) | fail | Negative IS and holdout |
| B9 FDUSDUSDT depeg reversion (0bps buffer) | too_small_to_matter | 20 | -7.48 (per-trade, not ann.) | n/a | ~1.0 | fail | Negative, below 30-trade floor too |
| B2 cross-venue dispersion, all coins/buffers | too_small_to_matter | 0 | n/a | n/a | n/a | n/a | Never triggers — dispersion too small to clear costs |
| B5 OI/price divergence (ETH, SOL, most conventions) | forced_flow_adjacent | 41-54 | -0.2 to -3.98 | n/a | 0.54-0.96 | fail | Negative/non-significant |
| B3 funding carry, established coins (BTC/ETH, 90d+ bucket) | too_small_too_new | 12-13 | 0.72-1.98 | n/a | 0.02-0.23 | fail (BH) | Same Run-1 result; below 50-trade floor |
| B3 funding carry, young coins (GRAM/CASHCAT, 0-30d bucket) | too_small_too_new | 1-2 | -5.8 to +8.28 | n/a | 0.12-0.89 | fail | Uninterpretable — 1-2 trades |
| B7 seasonality, best bucket per asset×axis (4 candidates) | none — highest FP risk | 120-408 (holdout) | n/a | -17.4 to -24.5 | 0.979-1.0 | fail | Decisively killed by holdout, as expected |

Full detail for every test: `results/n_tests_registry.csv`, `results/bh_correction_table.csv`, and
the per-hypothesis raw JSON files (`results/pit_momentum_raw.json`, `results/pairs_pooled_raw.json`,
`results/track_b_part1_raw.json`, `b3_out.json`, `b4_out.json`, `b5_oi_price_divergence` inline
above). Equity curves as CSV: `results/pit_momentum_*_net_equity.csv`,
`results/pairs_pooled_trades.csv`, `results/b2_dispersion_*.csv`, `results/b5_oi_*.csv`.

## Per-hypothesis honest paragraphs

**A1 — Point-in-time momentum.** Run 1's 0.86 net Sharpe was an artifact of ranking the universe by
today's volume and applying it retroactively. Rebuilt point-in-time across a 420-symbol pool with
weekly eligibility decided only from trailing data, all 6 variants (7/14/30d × long-short/long-only)
are negative gross AND net, in-sample AND holdout, with 103-105 trades each. The 7d long-only equity
curve declines from 1,000 EUR to ~23 EUR over 2 years — a real, gradual decline, not a bug. This is
the single most important result of Run 2: the Run-1 lead does not survive an honest universe.

**A2 — Pooled pairs.** Pooling every trade across Run 1's walk-forward cointegrated pairs (94 total,
54 IS / 40 holdout) turns "no statistical power" into "statistical power showing a small net loss."
Negative in-sample, negative holdout, still negative with the best pair or best month removed.

**B1 — Token unlocks.** Skipped cleanly. DeFiLlama's emissions/unlocks endpoints require a paid
plan (HTTP 402 on every probe); no other free calendar source was found. Zero tests counted, no
dates guessed.

**B2 — Cross-venue funding dispersion.** Real effect, wrong magnitude. Hyperliquid vs OKX funding on
BTC/ETH/SOL disperses by a few bps typically (95th percentile ~13bps on BTC over 285 8h-periods),
against a ~10bps round-trip cost floor from fees alone (before any transfer-cost buffer). The
strategy never enters a single trade on any coin/buffer combination — correctly, since the
opportunity essentially never clears costs. This is the "too small to matter" family's expected
null, not a bug: it's evidence the two venues are already well-arbitraged at this cost structure.

**B3 — Newly-listed perp funding.** The descriptive signal holds: mean |funding| is far richer on
freshly-listed coins (0-30d bucket: 158%/yr annualized; 30-90d: 75%/yr) than on established ones
(90d+: 13%/yr). But the newest coins simply don't have enough history to backtest — the two 0-30d
coins sampled (GRAM, CASHCAT) produced only 1-2 total trades each, uninterpretable. The established-
coin backtests (BTC, ETH) reproduce Run 1's already-reported result (12-13 trades, below the
30-trade floor). Directionally suggestive, not tradeable with the data available.

**B4 — Post-liquidation-cascade reversion.** Well-powered (296-1,626 trades per variant) and
decisively negative across every holding period and direction filter. Fading extreme-range/extreme-
volume days loses money, confirming (more strongly, with a cleaner causal proxy) Run 1's finding
that short-horizon reversal does not work in this market.

**B5 — Open interest / price divergence.** Mostly negative and non-significant (n=41-54 for ETH/SOL
across all sign conventions and holding periods). BTC's "short-cover" convention shows a tempting
Sharpe (6.5-7.7) but on only 5-6 trades — exactly the kind of result the evidence bar exists to
reject. No edge.

**B6 — Funding-settlement microstructure.** Well-powered now (1,200 observations per venue/hour-
type over 400 days) and cleanly negative net of costs, exactly as predicted when this was
pre-registered ("will likely die on costs at retail — that's a valid finding"). No pre- or
post-settlement price pressure survives 2 taker legs of fees.

**B7 — Hour-of-day / day-of-week seasonality.** The highest false-positive-risk hypothesis in the
run, held to the strictest scrutiny as pre-committed. All 4 best-in-sample-bucket candidates
(BTC/ETH × hour/day-of-week) fail decisively on holdout (Sharpe -17 to -25, p≈0.98-1.0) despite
having 120-408 holdout observations. The pre-registered discipline of counting all 62 underlying
bucket comparisons toward N_TESTS, not just the 4 promoted to holdout, is exactly what this
hypothesis was flagged for — and it died the way pre-registration predicted it likely would.

**B8 — Exchange listing announcements.** Skipped cleanly. None of the four reachable data sources
are news/announcement feeds; no free historical listing-announcement timestamp source was found.
Zero tests counted.

**B9 — Stablecoin micro-depeg reversion.** USDC never deviates enough from 1.0 to clear costs (zero
trigger events). FDUSD does deviate enough to trigger the rule regularly, but the reversion trade
loses money on average (-0.19% per non-overlapping trade, 0% win rate on the scored sample, 20
trades) — the "reversion to peg within 24h" assumption doesn't hold cleanly enough to profit after
a 20bps round-trip cost. TUSD had too few non-overlapping trigger events to test. Clean, cheap,
negative result, as predicted.

## Data-quality note (found and fixed mid-run, does not change any conclusion)
While inspecting the 440-symbol broad pool for A1, 20 of them turned out to be Binance's
tokenized-equity/ETF spot pairs (NVDAB, TSLAB, MSTRB, QQQB, SPYB, COINB, and 14 others) that
Run 1's original `TOKENIZED_EQUITY_BASES` exclusion list didn't catch (it only had the 5 that
appeared in Run 1's smaller top-80 sample). Fixed in `src/data.py`, universe pool shrank from 440
to 420, and A1 was re-run. **Every number is unchanged to two decimal places** — the equity tokens
were immaterial to the result. Documented here rather than silently fixed, per this run's own
disclosure standard.

## Cost model and infrastructure notes
Reused Run 1's `src/engine.py` cost model unchanged (5bps taker perp/side, 10bps taker spot/side,
liquidity-scaled slippage, real funding). New infrastructure this run: `src/stats.py` (locked
holdout split, Benjamini-Hochberg FDR, deflated Sharpe ratio per Bailey & Lopez de Prado 2014,
N_TESTS registry). New data capability: `data.fetch_okx_history_candles` (paginated OKX
history-candles endpoint, ~400 days of hourly data vs. the single-call 300-candle limit used in
Run 1) — this materially improved statistical power for B6/B7 and is available for future runs.

## What would change this conclusion
A real unlock/emissions calendar and a real listing-announcement timestamp feed (both paid in every
source checked) would let B1 and B8 actually run. Longer OKX funding-rate-history retention (or a
paid archive) would let B2/B3's cost-clearing tests run on more than ~95-180 days for OKX-side
comparisons. None of that was available here, and nothing was fabricated to fill the gap.

**Bottom line, restated once more so it can't be missed: nothing in this run should be traded.**
