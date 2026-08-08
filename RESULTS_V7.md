# Run 7 — Crypto Strategy Discovery Program

**Verdict: NOTHING PASSES.** 130 counted trials across families A–H. Four candidates
reached Tier 2. All four were killed. Zero strategies were eligible for the final
holdout, so **the holdout was never touched — 0 of 3 touches used.**

This is a null result, and it is reported as a null result. No gate was loosened, no
search was extended to find something, and no least-bad candidate is being presented
as promising.

---

## 1. Executive verdict

| | |
|---|---|
| **Total trials counted** (DSR denominator) | **130** |
| Ledger rows (incl. 7 skipped, 4 superseded) | 141 |
| Hypotheses pre-registered before any test | 85 (`HYPOTHESES_V7.md`) |
| Tier-1 screened | 121 |
| Reached Tier 2 | 4 |
| **Survivors** | **0** |
| **Deflated Sharpe of best candidate** | **0.121** (F08; needs ≥ 0.95) |
| **Holdout touches used** | **0 / 3** |
| **Honest verdict** | No deployable edge found. Do not allocate capital. |

The best candidate by raw validation Sharpe (F08, 1.22) has a **12% probability** of
being better than the best of 130 random strategies. That is not close.

---

## 2. What was searched

**Universe.** 135 Binance USD-M perpetuals, **survivorship-bias-free** — the archive at
`data.binance.vision` retains delisted symbols, so LUNAUSDT, SRMUSDT, BZRXUSDT,
TOMOUSDT, EOSUSDT, MATICUSDT and 8 others are present, contribute their real collapse,
and then go NaN. Three of the dead symbols rank top-25 by volume, so this is material:
every previous run in this repo could only *disclose* survivorship bias. This one fixed it.

**Span & partitions** (locked in `src/partitions.py` **before** idea generation):

| Partition | Window | Bars | Use |
|---|---|---|---|
| Development | 2021-01-01 → 2024-05-07 | 29,328 | Tier-1 screen, all parameter sweeps |
| Validation | 2024-05-07 → 2025-09-29 | 12,240 | Tier-2 gate battery |
| **Holdout** | 2025-09-29 → 2026-08-01 | — | **never loaded** |

The holdout is the most recent slice, and `log_holdout_touch()` raises after 3 touches.

**Data.** 1h OHLCV + quote volume for all 135; funding rates back to 2020 (6,114 8h
prints for BTC); 5-minute positioning metrics (open interest, top-trader long/short,
retail account long/short, taker buy/sell ratio) for 25 symbols; plus free on-chain
series (see §6).

---

## 3. The four candidates and why each died

All gates measured on **validation**, at the base (1.5×) cost level unless stated.

### A12 — fade the crowded retail side (z = 2.0 / 3.0)

*Mechanism:* when the retail account long/short ratio hits an extreme, the crowded side
is disproportionately small, over-levered accounts. They are the ones who get liquidated,
and they cannot stop because their margin decides for them. Fade them.

This was the strongest thing the program found. On development it looked genuinely good:
**Sharpe +1.51, net +1.26 bps/bar after pessimistic costs, positive in every year.**

| Gate | z = 2.0 | z = 3.0 |
|---|---|---|
| Sample size (≥300 trades) | PASS (1,254) | PASS (336) |
| Walk-forward (5 folds) | **FAIL** (mean −0.30, 1/5 positive) | PASS (mean 0.15) |
| Purged k-fold (embargo 24h) | **FAIL** (mean −0.39) | PASS (mean 0.25) |
| Regime (≥2 of 3 positive) | **FAIL** (1/3) | **FAIL** (1/3) |
| Block bootstrap 95% CI | **FAIL** [−2.04, +1.31] | **FAIL** [−1.72, +1.76] |
| Quarterly consistency (≥60%) | **FAIL** (33%) | **FAIL** (50%) |
| Outlier dependence (drop top 5%) | **FAIL** (+0.28 → −1.47 bps) | **FAIL** (+0.005 → −1.07 bps) |
| Entry-shift placebo | PASS | PASS |
| Parameter plateau (dev sweep) | PASS (7/7 thresholds positive) | PASS |
| Gross-to-cost ratio (≥1.5) | **FAIL** (0.72) | **FAIL** (1.01) |
| Random-entry percentile (≥95) | PASS (99.4) | PASS (99.8) |
| **Deflated Sharpe vs 130 trials** | **FAIL (0.0013)** | **FAIL (0.0049)** |
| **Validation Sharpe** | **−0.35** | **+0.01** |

The two variants correlate 0.59 on validation — just under the 0.6 "same strategy"
threshold, so they are reported separately, but they are clearly the same idea.

**The decisive number is the outlier test.** Strip the top 5% of bars by |P&L| and
z = 3.0 goes from +0.005 to **−1.07 bps/bar**. The entire apparent edge lives in a
handful of bars. That is not a strategy, it is a lottery ticket with a story attached.

### F02 / F08 — on-chain market-wide tilts

*Mechanisms:* stablecoin supply growth = dry powder that has already accepted fiat and
must deploy (F02); unique-active-address growth = genuine new participation, i.e. new
marginal buyers (F08).

Both look superficially attractive on validation — F08 posts Sharpe **1.22** with only
−22.6% max drawdown. Both fail anyway:

| Gate | F02 | F08 |
|---|---|---|
| **Market alpha** (t > 2 required) | **FAIL** (α +0.42 bps, **t = 1.17**) | **FAIL** (α +0.50 bps, **t = 1.44**) |
| Beats equal-weight buy & hold | PASS | PASS |
| Block bootstrap 95% CI | **FAIL** [−0.70, +2.52] | **FAIL** [−0.32, +2.77] |
| Walk-forward / purged k-fold | **FAIL** / **FAIL** | PASS / PASS |
| Quarterly consistency | PASS | **FAIL** |
| Entry-shift placebo | **FAIL** | **FAIL** |
| **Deflated Sharpe vs 130 trials** | **FAIL (0.061)** | **FAIL (0.121)** |

Two things kill these. First, **the alpha t-stats are 1.17 and 1.44** — the point
estimates are positive but statistically indistinguishable from zero over 12,240 bars.
Second, **both fail the entry-shift placebo**: acting 1–3 bars late performs as well or
better, which means the signal carries no timing information. A daily on-chain series
lagged a full day and held for 24h was never going to have hour-level timing content,
and the placebo test says so directly.

The market-alpha and beats-buy-hold gates were **added** for these two candidates
because a market-wide tilt is structurally different from a dollar-neutral
cross-sectional signal and the standard battery would have flattered it. Adding gates
to a candidate is tightening, not tuning; neither gate was selected after seeing the
result.

### Combination stage — VOID

Combining Tier-2 *survivors* is meaningless when there are none. Run as pure
diagnostics, the four candidates are pleasingly uncorrelated (A12 vs F: −0.06 to −0.21)
and blending them does improve the point estimate — inverse-vol Sharpe 0.85 — but the
bootstrap CI is **[−0.85, +2.55]** and the deflated Sharpe is **0.052**. A blend of four
rejected strategies is still rejected. Nothing from this stage was eligible for the holdout.

---

## 4. The graveyard

121 Tier-1 trials, by cause of death:

| Family | Advanced | Net-negative after costs | Only 1/3 regimes | Too few trades |
|---|---|---|---|---|
| A — Positioning / funding / OI (38) | 2 | 36 | 0 | 0 |
| B — Cross-sectional (26) | 0 | 23 | 3 | 0 |
| C — Volatility structure (7) | 0 | 7 | 0 | 0 |
| D — Time-of-day / calendar (23) | 0 | 21 | 2 | 0 |
| E — Lead-lag / cointegration (9) | 0 | 6 | 0 | 3 |
| F — On-chain (5 testable of 8) | 2 | 3 | 0 | 0 |
| H — Event-driven (13) | 0 | 0 | 0 | 13 |
| **Total (121)** | **4** | **96** | **5** | **16** |

**96 of 121 ideas — 79% — died to transaction costs, not to being wrong.**

Of the 72 trials that were *gross-positive*, **58 were cost-killed**: median gross
**+0.17 bps/bar**, median net **−1.36 bps/bar**. The cost model ate roughly 1.5 bps per
bar of gross edge, and almost nothing generated that much.

The clearest illustration is family B. Long-only cross-sectional momentum produced real
gross edge at every horizon — +1.09 bps (7d), +1.08 bps (3d), +1.02 bps (1d) — and net
returns of +0.25, −0.02 and −0.42 bps respectively. **The edge is real and it is
monotonically consumed by turnover.** The 1-day version trades 33,160 times and pays all
of it away; the 7-day version trades 10,096 times and keeps a quarter of it. This is the
single most reproducible finding in the program.

Family H is a different failure: 13 trials, all killed for too few trades. The delisting
run-up (H04) shows the largest net edge in the entire study — **+1.11 bps/bar** — on
**7 events**. Seven. It is reported as too-few-trades, not as a discovery, because a
7-sample mean is not evidence.

---

## 5. What the failures teach

**1. The cost floor is the binding constraint in 1h crypto, not signal quality.**
79% of deaths were cost, not sign. Round-trip cost is ~34 bps at the pessimistic level
for a liquid perp. To clear it, an hourly signal needs a gross edge most hourly signals
do not have. The productive direction is not "find a better signal" — it is **hold
longer, trade less, or execute passively.** Every horizon extension in family B
improved net return.

**2. The strongest-looking result was outlier-dependent, and only the outlier test
found it.** A12 passed sample size, parameter plateau, and the random-entry benchmark
at the 99th percentile. It looked like a real edge. Trimming 5% of bars flipped it from
+0.005 to −1.07 bps/bar. Without that gate this program would have taken A12 to the
holdout and had a coin-flip chance of a false positive reaching capital.

**3. Development-to-validation decay was catastrophic and one-directional for the
genuine cross-sectional signal.**

| | A12 z=2.0 | A12 z=3.0 |
|---|---|---|
| Development Sharpe | +1.51 | +1.18 |
| Validation Sharpe | **−0.35** | **+0.01** |
| Dev net bps/bar | +1.26 | +1.22 |
| Val net bps/bar | **−0.28** | **+0.005** |
| Dev yearly (2021/22/23/24) | 0.78 / 2.40 / 0.12 / 2.67 | 0.33 / 2.57 / 0.02 / 3.41 |
| Val yearly (2024/25) | 0.06 / **−0.57** | 1.05 / **−0.92** |

Retention is negative. The signal did not weaken, it inverted. Note the pattern inside
development too: 2021 and 2023 were weak, 2022 and 2024 were strong. A12 works in
violent deleveraging years and not otherwise — which is exactly what the regime gate
caught (positive in 1 of 3 regimes, both variants).

The two on-chain tilts moved the *other* way (dev 0.20/0.59 → val 0.91/1.22), but with
t-stats of 1.17 and 1.44 that is market conditions improving, not an edge strengthening.

**4. Mechanism quality did not predict survival.** Family A had the best economic story
in the whole pre-registration — forced liquidation of over-levered retail is a genuine,
identifiable, structurally trapped loser — and it produced 36 cost-killed trials out of
38. A correct mechanism tells you where to look. It does not tell you the edge is large
enough to pay for itself.

**5. Carry-forward from the previous run was confirmed.** Section 1 required diagnosing
the prior REJECT. Decomposed: fading down-cascades is **gross +18.06 bps** (right sign,
below the ~40 bps cost floor — cost-killed, not wrong); fading up-cascades is **gross
−31.44 bps** (wrong-signed — violent up-moves continue, they do not revert). The
restructured long-only version (A15) was retested here as a new trial and cost-killed
again at −0.07 bps net.

---

## 6. Data availability — measured, not assumed

`HYPOTHESES_V7.md` pre-declared family F and H01/H03/H08 as skips *conditional on a
probe failing*. The probe (`results_v7/data_availability_probe.json`) only partly failed,
and the pre-declaration turned out to be **too pessimistic**:

| Source | Status | Consequence |
|---|---|---|
| Glassnode / CryptoQuant / Dune | 401 | F01, F03–F06 → **SKIPPED_NO_DATA** |
| DeFiLlama emissions | 402 | H03 → **SKIPPED_NO_DATA** |
| Index membership history | none free | H08 → **SKIPPED_NO_DATA** |
| blockchain.info charts | 200, daily to 2009 | F07, F08 → **tested** |
| DeFiLlama stablecoins | 200, daily to 2017 | F02 → **tested** |
| Binance announcement CMS | 200, 261 symbols | H01 → **tested** |

Rather than take the free skip, the reachable ones were tested at the same Tier-1 bar as
everything else. Five ideas that would have been recorded as "untested" were measured;
two of them reached Tier 2 and were then killed there.

**7 hypotheses remain genuinely unmeasured** (F01, F03, F04, F05, F06, H03, H08). They
are logged `SKIPPED_NO_DATA` and **excluded from the 130-trial denominator** — no test
ran, so no selection pressure was spent. They are recorded as *unmeasured, not
falsified*. A barren family and an unmeasured family teach different things.

---

## 7. Deployment guidance

**None. Do not deploy anything from this program.**

The prompt asked for sizing from the lower bound of the bootstrap Sharpe CI. Applied
honestly, that rule answers itself:

| Candidate | Bootstrap Sharpe 95% CI | Lower bound | Implied size |
|---|---|---|---|
| A12 z=2.0 | [−2.04, +1.31] | −2.04 | zero |
| A12 z=3.0 | [−1.72, +1.76] | −1.72 | zero |
| F02 | [−0.70, +2.52] | −0.70 | zero |
| F08 | [−0.32, +2.77] | −0.32 | zero |
| Inverse-vol blend | [−0.85, +2.55] | −0.85 | zero |

Every lower bound is negative. There is no positive-Sharpe floor to size against.

Capacity, for completeness: A12 z=2.0 is capacity-constrained at roughly **$0.6m (10th
percentile) to $3.1m (median)** at 5% of ADV. Capacity was never the binding constraint —
1,000 EUR of retail capital is four orders of magnitude below it. The binding constraint
was always the per-trade cost floor, which does not improve with smaller size; it gets
worse.

**Pre-registered live kill criteria** — recorded for the *next* program, since nothing
is being deployed from this one. Any strategy that does reach live capital is killed if:

1. Realised 90-day rolling Sharpe falls below the lower bound of its validation
   bootstrap CI, at any point.
2. Realised round-trip cost exceeds the base-level model estimate by more than 50%,
   measured over 100 fills.
3. Two consecutive negative quarters.
4. Drawdown exceeds the Monte Carlo 5th-percentile drawdown from the validation set.
5. Realised trade count deviates more than 30% from backtest expectation over a month
   (indicates the signal is firing on different data than modelled).
6. The stated mechanism is publicly invalidated — e.g. the exchange stops publishing the
   positioning metric the signal reads.

Criteria are absolute and evaluated before any discretionary override.

---

## 8. Reproducing

```bash
.venv/bin/python run_tier1.py      # 113 trials, development
.venv/bin/python run_skips.py      # data-availability probe
.venv/bin/python run_family_f.py   #   8 trials, development
.venv/bin/python run_tier2.py      # A12 battery, validation
.venv/bin/python run_tier2b.py     # F battery + market-neutrality, validation
.venv/bin/python run_decay.py      # decay, combination (void), graveyard
.venv/bin/python run_tier3.py      # asserts holdout untouched; refuses to load it
.venv/bin/python tests/test_engine.py
```

Artifacts: `results_v7/trials_ledger.csv` (141 rows, append-only, row written before
each test), `tier1_results.csv`, `family_f_results.csv`, `tier2_results.json`,
`tier2b_results.json`, `decay_and_combination.json`, `tier3_holdout.json`,
`data_availability_probe.json`, `partitions.json`.

### A correction made during this run

The entry-shift placebo gate was first coded to test shifts −3…+3 and require the actual
to beat all of them. **That was wrong.** A negative shift feeds bar *t+k*'s signal into
bar *t+1*'s return — that is deliberate lookahead, not a placebo, and it wins by
construction (Sharpe 4.10 vs −0.35). The gate was corrected to test delays only, with the
lookahead runs kept as a separate informational sanity check. This flipped `entry_shift`
from FAIL to PASS for both A12 variants. **The verdict did not change** — both still fail
regime, bootstrap, quarterly, outlier, cost-ratio and DSR. The corrected re-run was logged
as two *additional* ledger rows rather than overwriting the originals, which raises the
DSR denominator and therefore makes the test harder, not easier.

---

## 9. Closing block

```
Total trials              : 130 counted (141 ledger rows; 7 skipped for no data,
                            4 superseded placeholders — neither counts)
Survivors                 : 0
Deflated Sharpe of best   : 0.121  (F08_active_address_growth; threshold 0.95)
                            best cross-sectional: 0.005 (A12 z=3.0)
Holdout touches used      : 0 / 3
Honest verdict            : NOTHING PASSES. No strategy in this program is
                            deployable. The holdout remains sealed and is fully
                            available for future work.

Biggest reason this could still be wrong:
  The cost model is the single assumption doing the most work, and it killed 79%
  of the ideas. It is a static liquidity-tiered estimate — 2 x (4.5 bps taker +
  0.5-4.0 bps half-spread + 2.0 bps slippage floor) x {1.0, 1.5, 2.5} — calibrated
  from median hourly quote volume, never validated against actual fills, because
  this program places no orders. If real achievable costs are materially lower than
  modelled, in particular for a maker-only or passive-execution implementation that
  avoids the 4.5 bps taker fee entirely, then a large number of the 96 cost-killed
  ideas would flip sign. Family B cross-sectional momentum is the specific case:
  gross +1.09 bps/bar at a 7-day horizon is real, survivorship-free, and consistent
  across horizons, and it lost only its net margin. That family deserves a rerun
  under a measured passive-execution cost model before being written off.

  Second-order: the validation window is 12,240 bars (~17 months) covering one
  market cycle phase. A12's dev-period profile shows it working in 2022 and 2024
  and not in 2021 or 2023 — a validation window that happened to land on a
  favourable phase would have produced a false pass. This one did not, but the
  point cuts both ways: 17 months is thin evidence for a regime-dependent signal
  in either direction.
```
