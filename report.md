# Crypto Intraday Strategy Backtest — Liquidation-Cascade Mean Reversion (1h perps)

**Verdict: REJECT.** 7 of 8 validation gates FAIL. The strategy loses money *gross*, before a
single basis point of cost is applied, and performs worse than 91.5% of random-entry portfolios.

---

## 0. READ THIS FIRST — the strategy spec was not supplied

**Section 1 of the task prompt (STRATEGY SPEC) was left as unfilled template placeholders.**
Hypothesis, universe, timeframe and direction were `[e.g. ...]` examples; entry and exit logic
were descriptions of what to write, not rules. No strategy was actually specified.

Rather than block, this run implements the prompt's **own worked example hypothesis, verbatim**:

> "Forced liquidation sellers are price-insensitive, so violent moves accompanied by OI collapse
> overshoot fair value and revert within N hours."

Everything else (Sections 2–11) is strategy-agnostic machinery and was built exactly as specified.
The signal layer is isolated behind a single function (`src/strategy.py::build_signal`), so a real
spec can be swapped in without touching the engine, costs, gates, or benchmarks.

**If this is not the strategy you meant to test, the framework is reusable and the verdict below
applies only to this hypothesis.**

### The OI leg of the hypothesis is NOT testable on free data
The hypothesis names *open-interest collapse* as the confirming condition. Measured limits:

| Series | Depth available | Verdict |
|---|---|---|
| OKX OI, 1H granularity | **29 days** | unusable for a 3-year study |
| OKX OI, 1D granularity | **179 days** | unusable |
| Binance futures (would have OI) | HTTP 451 geo-blocked | unreachable |
| Bybit | HTTP 403 | unreachable |

So this tests the **price + volume half** of the hypothesis, using a volume spike as the
forced-flow proxy. This is a genuinely weaker test — volume spikes occur for many reasons other
than forced liquidation — and it is reported as a limitation rather than papered over.

---

## 1. Data

| Property | Value |
|---|---|
| Source | OKX USDT perpetual swaps, 1H bars (`/api/v5/market/history-candles`, deep `after` pagination) |
| Universe | 20 crypto perps: BTC ETH SOL XRP DOGE ADA WLD PEPE SUI UNI AAVE FIL NEAR LINK AVAX SHIB LTC BCH XLM DOT |
| Span | 2023-08-04 → 2026-08-08 (1,099 days ≈ 3.0 years), 26,400 bars per asset |
| Timezone | UTC throughout, no exceptions |

**Integrity report** (`results_v6/data_integrity_report.json`), all 20 assets:

| Check | Result |
|---|---|
| Missing bars vs. expected hourly grid | **0** (0.000%) |
| Duplicate timestamps | **0** |
| Zero-volume bars | **0** |
| OHLC violations (high<low etc.) | **0** |
| Non-positive prices | **0** |
| Return spikes >10σ | 153 total across 20 assets — **classified, not dropped** |
| Wick-artifact candidates (extreme range, normal close) | 39 |

**Universe-selection note:** OKX's perp list is now heavily contaminated with tokenized equities
and commodities (SNDK, SPCX, MU, XAU, SOXL, INTC, …), several of which out-rank real crypto by
volume. These were excluded via an explicit crypto allowlist. Selecting "top 20 by volume" naively
would have silently backtested tokenized Micron stock.

### Survivorship bias — present, and it flatters the result
The universe is built from **currently-listed** OKX perps. Perps delisted during 2023–2026 are
absent. Assets also had to have ~3 years of history to be included, which further selects for
survivors. **All cross-sectional results should be read as optimistic on this axis.** No free
source of delisted-perp OHLCV was found.

### Funding is materially incomplete — and its absence also flatters the result
OKX's free funding-rate endpoint retains only ~95 days. **Only 173 of 1,134 out-of-sample trades
(15%) fall inside the funding-data window**; total funding charged across all OOS trades was just
$17.80. Funding wiring was verified correct against a synthetic series (longs paid +$107.42,
shorts received −$281.17 over the full span), so this is a *data coverage* gap, not a bug. Since
the strategy is net-long-biased in a market with predominantly positive funding, **omitting
funding makes the reported results better than reality, not worse.**

---

## 2. Cost model (built first, per Section 3)

Per side: taker 4.5 bps · liquidity-tiered half-spread · √-participation slippage (floor 2 bps) ·
real historical funding at 00/08/16 UTC settlements. Three levels: optimistic (1×), base (1.5×),
pessimistic (2.5×).

### A real cost bug, caught and corrected before it drove the verdict
The spread was first estimated with the **Corwin-Schultz (2012)** high-low estimator. On this data
it returned a **median half-spread of 5.0 bps on BTC perp and 7.2 bps on ETH perp** — roughly 10×
the true quoted spread. CS is calibrated for *daily equity* bars, where the high-low range is
dominated by bid-ask bounce; on 1h crypto bars the range is dominated by genuine volatility, so it
massively overestimates. Left in place it would have produced a REJECT driven by a measurement
artifact — which is as much a failure of this exercise as a fake PASS.

It was replaced with a liquidity-tiered half-spread (0.5 bp for BTC/ETH-class, up to 4.0 bp for
thin books) and **CS was retained as an explicit pessimistic sensitivity.**

**The verdict does not depend on the spread model** (event study, k=3/z=3.0/hold=24, 9,305 events):

| Spread model | Cost level | Mean cost (bps) | Mean gross (bps) | Mean **net** (bps) |
|---|---|---|---|---|
| Tiered (primary) | optimistic | 25.6 | +6.53 | **−19.03** |
| Tiered | base | 38.3 | +6.53 | **−31.81** |
| Tiered | pessimistic | 63.9 | +6.53 | **−57.37** |
| Corwin-Schultz | optimistic | 54.7 | +6.53 | **−48.16** |
| Corwin-Schultz | base | 82.0 | +6.53 | **−75.51** |
| Corwin-Schultz | pessimistic | 136.7 | +6.53 | **−130.21** |

Negative under **every** combination, including the most optimistic.

### Cost-to-stop ratio — structurally fee-bound
| Metric | Value |
|---|---|
| Median stop distance | 231.9 bps |
| Median round-trip cost (base) | 22.5 bps |
| **Stop-to-cost ratio** | **10.3** |

**FLAG: below the 20× threshold.** The strategy is structurally fee-bound regardless of signal
quality. Slippage is insensitive to `k` at retail size (2.0 bps at k=0.5 and k=1.0; the 2 bp floor
binds), so this is driven by fees and spread, not by the impact assumption.

### Null-strategy calibration (`tests/test_engine.py`)
Random entries, identical holding/sizing/costs: 178 trades, gross +$3,588, costs $23,558, net
−$19,971. The accounting identity `net == gross − costs` holds to float precision, confirming the
cost model is wired into P&L rather than decorative.

---

## 3. Lookahead elimination — all Section 4 rules enforced and tested

`tests/test_engine.py` — **7/7 pass**:

| Test | Result |
|---|---|
| `assert_no_lookahead()` — truncating the future cannot change a past signal | PASS (0 problems; also PASS on real data) |
| Fill is next-bar **open**, never signal-bar close | PASS (exact price match) |
| Stop wins intrabar ties vs. target (worse outcome assumed) | PASS |
| Gap through stop fills at the **open**, not the stop price | PASS |
| Cost levels strictly monotonic | PASS |
| Null strategy loses ≈ modelled cost | PASS |
| Kill switch halts on a −95% path | PASS |

All rolling statistics (σ, median volume, ATR, BTC beta) are trailing windows, `.shift(1)`-ed so a
bar never enters its own threshold. Nothing is full-sample normalised.

---

## 4. Headline result — walk-forward out-of-sample

Anchored walk-forward, 12-month train → 3-month test, 8 folds, parameters re-selected on train
only and never re-optimised on test. **1,134 OOS trades.**

| Metric | Value |
|---|---|
| OOS trades | 1,134 |
| Mean IS Sharpe | −0.075 |
| **Mean OOS Sharpe** | **−3.738** |
| Win rate | **39.77%** ± 1.45% (95% CI 36.9–42.6) |
| Mean return / trade | **−46.25 bps** |
| Cost as % of gross P&L | **131.2%** |
| Realized max drawdown | **−99.89%** |
| Longest underwater | 1,095 days (the entire sample) |

Exit reasons: stop 470 · time-stop 277 · target 251 · funding-breaker 92 · stop-gap 44.

**Costs exceed gross P&L (131%) — but gross P&L is itself negative (−$8,104 at centre params).**
This is not a strategy killed by fees; it is a strategy whose signal points the wrong way, with
fees applied on top.

---

## 5. Validation gates

| Gate | Status | Evidence |
|---|---|---|
| **8.1 Sample size** | **PASS** | 1,134 trades (>500). But win rate 39.8% is *outside* 2 SE of a coin flip in the **wrong direction** |
| **8.2 Walk-forward** | **FAIL** | Mean OOS Sharpe −3.74; requirement is positive and ≥50% of IS |
| **8.3 Purged k-fold** | **FAIL** | 5 folds, embargo 24 bars (= max holding). Mean fold Sharpe −3.47. **0 of 5 folds positive** |
| **8.4 Deflated Sharpe** | **FAIL** | 602 trials. Raw annualised Sharpe −2.31; expected max under null +0.096; **DSR probability 0.0000** |
| **8.5 Parameter stability** | **FAIL** | 25-point ±50% sweep: **0 of 25 points positive**. Best −0.517, median −1.09. Not a plateau — nothing works anywhere |
| **8.6 Regime robustness** | **FAIL** | **0 of 3 direction regimes profitable.** Bear −46.8 bps, bull −11.3 bps, chop −57.5 bps. High-vol −28.6, low-vol −58.6. Every year negative (2024 −7.6, 2025 −48.0, 2026 −66.3) |
| **8.7 Block bootstrap** | **FAIL** | 10,000 iters, block 20. **Sharpe 95% CI [−4.11, −0.70] — entirely below zero.** Total-return CI [−100%, −92.6%] |
| **8.8 MC drawdown** | INFO | 10,000 resamples. Realized max DD −99.89%; MC median −99.81%, worst −99.95%. Longest losing streak: realized 15, MC p95 17 |

**Note on 8.1:** this is the only PASS, and it is a Pyrrhic one — the sample is large enough to
establish, with confidence, that the strategy is reliably *unprofitable*.

---

## 6. Benchmarks (Section 7)

| Benchmark | Result |
|---|---|
| **1. Buy-and-hold BTC** | +121.9% total, Sharpe **0.801** — beats the strategy by an enormous margin |
| **2. Random entry** (1,000 iters, matched count/holding/sizing/costs) | Random median Sharpe −1.08, p95 +0.594. **Strategy sits at the 8.5th percentile** — worse than 91.5% of random portfolios. Requirement was ≥95th. **FAIL** |
| **3. Shifted entries** (±1,2,3 bars) | −0.89, −1.63, −0.81, −3.43, −3.30, −3.53 — all negative. No timing edge to destroy |
| **4. Vol-matched passive** | Buy-and-hold BTC above serves this role; strategy is dominated |

Benchmark 2 is the most damning single number in this report: **the signal is worse than noise.**
Random entry at least loses only the spread; this strategy actively selects losing entries.

---

## 7. Diagnostic — unthrottled event study (large sample)

The portfolio caps concurrency at 5 across 20 correlated assets, discarding most signals. To test
the *underlying effect* free of that constraint, every cascade event was measured as a forward
return (still next-bar-open entry, still cost-charged). 3,463–14,931 events per cell.

**Decomposition by direction (14,931 events) — the hypothesis is half-right and still unprofitable:**

| Side | n | Mean gross | Mean net |
|---|---|---|---|
| **Fade down-cascade (buy the crash)** | 7,228 | **+18.06 bps** | **−21.57 bps** |
| **Fade up-cascade (short the pop)** | 7,703 | **−31.44 bps** | **−68.79 bps** |

There *is* a small genuine overshoot after violent **down** moves — about **+18 bps gross** — which
is directionally consistent with the forced-seller story. But it is less than half the ~40 bps
round-trip cost, so it is not harvestable. The **short side is actively wrong-signed**: violent up
moves *continue* rather than revert, costing −31 bps gross. Trading both directions blends a
too-small edge with a negative one.

**Not driven by outliers:** dropping the top 5% of events by |P&L| makes the OOS mean *worse*
(−46.25 → −66.21 bps) and the event-study mean −27.98 bps. The loss is pervasive, not tail-driven.

**Every year negative:** 2023 −32.2, 2024 −35.6, 2025 −66.0, 2026 −40.3 bps.

---

## 8. Metrics table (net of costs, out-of-sample)

| Category | Metric | Value |
|---|---|---|
| Return | Total return / CAGR | −18.7% / −6.65% (centre params, full sample) |
| Risk-adjusted | Sharpe / Sortino / Calmar | −2.31 / −0.10 / −0.33 |
| Risk-adjusted | **Deflated Sharpe (602 trials)** | **0.0000** |
| Drawdown | Max DD / longest underwater | −99.89% / 1,095 days |
| Trades | n / win rate ± SE | 1,134 / 39.77% ± 1.45% |
| Trades | Mean return per trade | −46.25 bps |
| Streaks | Longest losing run (realized / MC p95) | 15 / 17 |
| Costs | Fees / spread / slippage / funding | $3,839 / $1,944 / $4,851 / $0 (see §1) |
| Costs | **Cost as % of gross P&L** | **131.2%** |
| Tails | Skew / excess kurtosis | +0.63 / +1.58 |

Plots in `results_v6/plots/`: OOS equity (log), underwater curve, rolling Sharpe, per-regime
returns, parameter surface, MC drawdown histogram, return distribution vs normal, event-study
net-return curve.

---

## 9. Anti-pattern checklist (Section 11) — explicit confirmation

| Anti-pattern | Status |
|---|---|
| Signal-bar close fills | **Not present** — unit-tested next-bar-open fills |
| Full-sample normalization / z-scores / threshold calibration | **Not present** — all trailing, `.shift(1)`-ed; `assert_no_lookahead` passes on synthetic and real data |
| Parameters chosen after seeing test-set results | **Not present** — grid pre-registered; walk-forward selects on train only |
| Survivorship-biased universe | **PRESENT AND DISCLOSED** — currently-listed perps only; results optimistic (§1) |
| Costs as flat % with no slippage/funding | **Not present** — fees + tiered spread + √-participation slippage + real funding, 3 levels. Funding coverage incomplete and disclosed (§1) |
| Guaranteed stop fills with no gap modelling | **Not present** — gap-through-stop fills at the open; 44 OOS trades exited this way |
| Best-of-many-variants without correction | **Not present** — 633 trials logged; DSR uses 602 |
| <200 trades presented as conclusive | **Not present** — 1,134 OOS trades |
| Results driven by 1–2 outliers | **Not present** — dropping top 5% makes results *worse* |
| Long-only in a bull-market dataset | **Not present** — both directions tested; long-only tested separately; sample spans bull/bear/chop |

---

## 10. Final deliverable

> **Verdict: REJECT**
>
> **Gates failed:** 8.2 walk-forward · 8.3 purged k-fold · 8.4 deflated Sharpe · 8.5 parameter
> stability · 8.6 regime robustness · 8.7 block bootstrap. (8.1 sample size passes; 8.8 is
> informational.) Also fails Benchmark 2 — worse than 91.5% of random-entry portfolios.
>
> **Single biggest threat to this result:** the open-interest confirmation named in the hypothesis
> could not be tested at all (OKX exposes 29 days of 1H OI against a 3-year study), so this
> rejects a volume-proxied version of the hypothesis rather than the hypothesis as literally
> stated.
>
> **What would change my mind:** a source of deep historical open interest and liquidation prints
> (paid — Coinalyze, Amberdata, or exchange bulk archives) showing that cascades *confirmed by OI
> collapse* are a materially different population from volume-spike cascades, with gross reversion
> above ~60 bps — i.e. comfortably more than double the ~40 bps round-trip cost floor. The
> down-cascade side already shows +18 bps gross, so the effect is real but roughly 3× too small;
> OI filtering would have to more than triple its magnitude, not merely improve its sign.
>
> **Recommended starting size if deployed:** **zero.** The lower bound of the Sharpe CI is −4.11
> and the upper bound is −0.70 — the entire 95% interval is below zero. There is no fraction of
> capital at which a negative-expectancy strategy is correctly sized.

---

## What this backtest cannot tell you

It measures whether an edge existed historically in this data. It cannot tell you the edge
persists, that live execution would match simulation, or that you would hold through the
drawdowns Section 8.8 predicts. In this case that caveat is academic — nothing survived to deploy.
The framework itself (`src/`, `tests/`) is reusable and its correctness is independently tested;
that, plus the finding that down-cascade reversion is real but ~3× too small to trade, is the
durable output of this run.
