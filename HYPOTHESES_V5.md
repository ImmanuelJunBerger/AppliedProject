# HYPOTHESES_V5.md — Pre-registration for Run 5 (Multi-Strategy Portfolio Research, TradFi)

**Written**: 2026-07-19 19:48 UTC, before any Run-5 strategy data was fetched or examined. Data
*reachability* was probed (see below) — that is infrastructure discovery, not results-peeking —
but no return series, factor value, or price history was inspected before this document was
finalized. Anything conceived after this point goes in the POST-HOC (UNTRUSTED) section and is
never treated as a finding.

## Correction to the task's stated context
The task brief references "Runs 1-4" and an existing `src/experiment_log.py`. The actual repo
history is **Runs 1-3** only (crypto backtest engine, crypto edge-hunt v2, perp-DEX farming cost
model) — there is no Run 4, and no `src/experiment_log.py` module. The closest existing
equivalent is `src/stats.py` (holdout split, Benjamini-Hochberg FDR, deflated Sharpe, N_TESTS
registry pattern), built in Run 2 — that is what this run reuses and extends. Noted here rather
than silently fabricated or silently ignored.

## Data reachability probe (2026-07-19, infrastructure only)
| Source | Status | Note |
|---|---|---|
| Kenneth French Data Library (mba.tuck.dartmouth.edu) | **WORKS** | Real zip downloads confirmed (daily factors CSV, 177KB) |
| FRED (fred.stlouisfed.org) | **WORKS** | Real CSV, e.g. DGS10 back to 1962 |
| CFTC Commitments of Traders (publicreporting.cftc.gov, Socrata API) | **WORKS** | Real JSON, weekly legacy futures-only reports confirmed |
| Stooq (stooq.com) | **BLOCKED** | Returns a JavaScript proof-of-work challenge page, not fetchable by a plain HTTP client in this environment. Dropped as a source. |
| Yahoo Finance (query1/query2.finance.yahoo.com) | **WORKS** (requires a `User-Agent` header — bare requests get HTTP 429) | Confirmed: `^GSPC` daily history back to 1970 (14,256 bars), futures continuous tickers (e.g. `ES=F`) also resolve |
| FOMC historical calendar (federalreserve.gov/monetarypolicy/fomchistorical*.htm) | **WORKS** | Confirmed reachable for 1994, 2000, 2008, 2015, 2020 archive pages |
| SEC EDGAR company-facts API | **WORKS** but insufficient for S10 (see below) | Gives fundamentals for known/current CIKs only, not a survivorship-free delisted-inclusive universe with attached return data |

**Consequence for the strategy list**: Stooq is dropped; all futures/index/ETF price series come
from Yahoo Finance (with the important caveat, stated once and applying everywhere below, that
Yahoo's own equity-index and ETF series can have minor historical revisions/gaps and are not a
CRSP-grade survivorship-bias-free academic dataset — flagged wherever it could plausibly change a
result, per the task's own instruction).

## Global rules locked in before testing (carried over from Run 2, adapted for decade-scale data)
- **Holdout**: most recent ~30% of each series' available history, reserved, touched once at the
  end, only for hypotheses that already cleared in-sample.
- **N_TESTS**: a *new*, separate registry (`results/n_tests_registry_v5.csv`) — Run 2's crypto
  registry is a different hypothesis family (different market, different data, different period)
  and mixing denominators across unrelated families would misrepresent both. Every
  (strategy × parameter variant × market/universe variant) that produces a Sharpe/p-value is one
  test, logged as it happens, fixed grids below, no expansion after seeing interim results.
- **Minimum evidence bar for calling anything a finding** (all required): ≥100 trades OR ≥10
  years of daily observations, positive net Sharpe in-sample **and** holdout, survives BH-FDR
  (q=0.10) across the full N_TESTS pool, a stated structural reason, survives dropping the single
  best year and the single best market.
- **Regime split**: pre-2008 / 2008-2015 / post-2015 reported separately for every surviving
  candidate. A strategy that only works in one regime is a regime bet, not an edge.
- **Portfolio construction is an outcome, not a target.** No hypothesis, parameter, or strategy
  is added or re-tuned after seeing the correlation matrix or portfolio Sharpe. If assembling the
  portfolio surfaces a genuinely new idea, it goes in POST-HOC and is excluded from the headline
  portfolio.
- Cost model: new `src/tradfi_costs.py`, per-market commission+spread (not one blanket number),
  next-bar-open fills, financing/roll costs where relevant, turnover reported next to every Sharpe.

---

## S1 — Time-series momentum / trend-following
- **Structural cause**: under-reaction to information + hedging/rebalancing flows that persist in
  one direction; the most out-of-sample-replicated systematic effect in the literature (multiple
  disjoint author groups, multiple disjoint multi-decade samples).
- **Universe (deliberately includes obscure markets, not just S&P)**: equity index (ES=F/`^GSPC`
  proxy), 10Y note (ZN=F/TNX proxy), a currency (6E=F or `EURUSD=X`), and commodities — gold
  (GC=F), crude (CL=F), and one genuinely obscure market if its Yahoo ticker resolves cleanly
  (e.g. lean hogs `HE=F` or lumber) — obscure markets are lower-crowding by construction, which is
  the entire structural argument for including them.
- **Exact rule**: trailing total return over {63, 126, 252} trading days (≈3/6/12 months); go
  long if positive, short if negative; position sized to a fixed ex-ante volatility target (10%
  annualized) using a trailing 60-day realized-vol scalar; monthly rebalance.
- **Parameter grid**: 3 lookbacks × up to 6 markets = up to 18 tests (single-market), plus a
  simple equal-weight multi-market blend per lookback (+3 tests) = ≤21 tests.
- **Prediction**: Sharpe ~0.4-0.7 pre-cost on the blend, obscure single markets noisier
  individually; expect the blend to beat any single market (this is the point of the strategy).

## S2 — Overnight vs. intraday decomposition
- **Structural cause**: candidate mechanisms are an overnight risk premium, ETF/index
  market-maker overnight hedging flow, and retail order-flow timing concentrated at the open —
  named plainly as candidates, not proven mechanisms.
- **Exact rule**: for `^GSPC` (and one or two other indices if data is clean), split each day's
  return into close(t-1)->open(t) and open(t)->close(t). Compare cumulative overnight-only vs.
  intraday-only equity curves. Then cost the overnight strategy as an actual daily round-trip
  (buy at close, sell at next open) against realistic costs.
- **Parameter grid**: 2-3 indices = 2-3 tests (gross), same count net-of-cost.
- **Prediction**: gross overnight return materially exceeds gross intraday return (well-documented
  historically); net-of-realistic-daily-round-trip-costs is expected to be much weaker or negative
  — explicitly a plausible-to-die-on-turnover result per the task brief, and that would be a valid
  finding, not a failure.

## S3 — Pre-FOMC announcement drift
- **Structural cause**: pre-scheduled resolution of monetary-policy uncertainty; documented
  academic effect (Lucca & Moench and follow-ups) of positive equity drift in the ~24h before
  scheduled FOMC statements.
- **Exact rule**: using the Fed's own historical meeting-date archive (1994-2026), take `^GSPC`
  return from close on the trading day before the FOMC statement day to close on the statement
  day itself (the pre-announcement window); pool across all meetings.
- **Parameter grid**: 1 window definition × {full sample, ex-2008-2009 crisis, ex-2020} = 3 tests.
- **Prediction**: small, positive, pooled pre-FOMC drift — the interesting question is whether
  ~250 meeting-events over 32 years gives enough power to say so with confidence net of costs
  (this is a low-frequency effect; ~8 trades/year, so absolute EUR turnover cost is trivial even
  if the per-event edge is small).

## S4 — Turn-of-month effect
- **Structural cause**: pension contributions, payroll-linked retail flows, and index-fund
  rebalancing concentrate around calendar month boundaries — a forced/insensitive-flow story.
- **Exact rule**: on `^GSPC`, compare the return over the last N and first M trading days of each
  month (test N,M ∈ {1,2,3,4}) against the return on all other days.
- **Parameter grid**: 4×4 = 16 window combinations, but only 4 "diagonal" combinations (N=M) are
  scored as primary tests to avoid a disguised parameter search; the other 12 are logged
  descriptively (counted in N_TESTS, not individually promoted to holdout) exactly as Run 2's B7
  handled its 62 seasonality buckets.
- **Prediction**: a real but small effect, likely to shrink materially once realistic costs for
  ~24 round trips/year are applied.

## S5 — Carry / term structure
- **Structural cause**: futures curve backwardation/contango reflects a real risk-transfer price
  (storage cost, convenience yield, roll compensation to hedgers) — one of the few styles with
  genuine decades-long, cross-asset academic support (Koijen et al., "Carry").
- **Exact rule**: where a near/far futures pair is obtainable from Yahoo for the same underlying
  (front-month vs. a further-dated contract), carry = annualized (far/near - 1) scaled by time to
  expiry; go long the highest-carry markets, short the lowest, cross-sectionally, monthly rebal.
  **Data check required first**: Yahoo's free continuous-contract tickers do not reliably expose
  multiple simultaneous maturities for most markets — if a clean near/far pair can't be
  constructed for at least 3 markets, this is logged **SKIPPED — insufficient data** rather than
  proxied with a fabricated curve.
- **Parameter grid**: up to 4 tests (one per market pair, if obtainable) + 1 cross-sectional blend.
- **Prediction**: genuinely uncertain given the stated data-availability risk; may skip entirely.

## S6 — CFTC COT positioning extremes
- **Structural cause**: commercial hedgers are argued to have superior informational/economic
  positioning versus speculators; extreme net-positioning readings (commercials very long /
  specs very short, or vice versa) are a documented contrarian signal in the futures literature.
- **Exact rule**: weekly CFTC legacy report, commercial net position as a % of open interest,
  z-scored over a trailing 3-year window; go with the commercials' direction when the z-score
  exceeds ±2, flat otherwise. Tested on 2-3 liquid futures markets with long COT history (e.g.
  S&P 500 index futures, crude oil, 10Y note).
- **Parameter grid**: 3 markets × 1 threshold = 3 tests, plus a sensitivity at ±1.5 z = 3 more = 6.
- **Prediction**: weekly-resolution signal, low trade frequency; genuinely under-tested by retail
  per the task brief, so no strong prior either way beyond "plausible small effect."

## S7 — Cross-sectional equity factors (French library) — reference only
- **Not scored as a candidate portfolio strategy.** Pulled solely as a correlation reference set
  (Fama-French 5 factors + momentum, daily, from the French library) to check whether any of
  S1-S6/S8-S9's return streams are secretly disguised factor exposure. No hypothesis test, no
  N_TESTS entries, no holdout — it's a diagnostic column, not a candidate.

## S8 — Volatility risk premium (systematic short-vol proxy)
- **Structural cause**: implied volatility has a well-documented, persistent premium over
  subsequently realized volatility (insurance-buyer demand exceeds compensated risk) — the
  standard "sell insurance" risk premium story. **Warning taken seriously**: this return stream is
  negatively skewed by construction; Sharpe ratio is a misleading single-number summary for it and
  will be reported alongside max drawdown, skew, and worst-single-period loss, prominently, not as
  a footnote.
- **Exact rule/data check**: proxy via a short-vol-style ETF/instrument if a sufficiently long,
  clean Yahoo history exists (e.g. a VIX-linked short-volatility product); if no clean long-history
  proxy is obtainable free, construct a synthetic proxy is EXPLICITLY DISALLOWED (would violate
  the no-fabrication rule) — log **SKIPPED — insufficient data** instead. This will be checked
  before committing to it as a scored test.
- **Parameter grid**: 1 test if a proxy is found, else 0 (skip).
- **Prediction**: if testable, expect a high standalone Sharpe that the report must actively warn
  the reader not to trust at face value, per the task's own instruction.

## S9 — Defensive / regime overlay
- **Structural cause**: not a standalone return source — a risk-switch. The candidate mechanism is
  simply avoiding known high-drawdown regimes (e.g. price below its own 200-day moving average, or
  an inverted yield curve from FRED) rather than harvesting a new premium.
- **Exact rule**: apply a trend filter (`^GSPC` above/below its 200-day moving average) and,
  separately, a yield-curve filter (10Y-3M spread from FRED, negative = defensive) to scale equity
  exposure between 100% and 0% (or 100% and 50%, tested as a variant); measure the effect on
  PORTFOLIO Sharpe/drawdown when overlaid on the S1-S8 blend, not as a standalone return stream.
- **Parameter grid**: 2 filters × 2 intensity variants = 4 tests.
- **Prediction**: per the task brief's own framing, expect this to reduce return roughly
  proportionally to reduced exposure, with an open question of whether risk-adjusted (Sharpe) and
  drawdown metrics actually improve or whether it's a wash — testing this honestly, not assuming
  the "defensive overlays help" folk wisdom is true.

## S10 — Microcap post-earnings drift
- **Structural cause, if testable**: post-earnings-announcement drift is real and well-documented;
  the microcap segment is capacity-constrained (an advantage at retail size, a disadvantage for
  any institutional money that would otherwise compete it away).
- **Data check (done now, before any test is attempted)**: this requires BOTH (a) a
  survivorship-bias-free universe including delisted/failed microcaps, and (b) point-in-time
  earnings-surprise data, joined to daily returns. SEC EDGAR's company-facts API (confirmed
  reachable above) provides fundamentals only for currently-known CIKs — it is not a
  delisted-inclusive universe, and pairing it with free daily-return data for stocks that have
  since delisted is not achievable with the sources available here (Yahoo Finance does not serve
  meaningful history for delisted tickers once they stop trading). **Verdict: SKIPPED —
  insufficient data**, decided here from the data-availability check alone, before any attempt to
  proxy or approximate it. Zero tests counted.

---

## POST-HOC (untrusted) — anything conceived after this document was written
*(empty at time of writing.)*
