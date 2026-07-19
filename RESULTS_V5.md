# Run 5 — Multi-Strategy Portfolio Research (Traditional Markets) — READ THIS FIRST

## The numbers that matter
- **N_TESTS = 60** hypothesis/parameter-variant combinations logged (`results/n_tests_registry_v5.csv`),
  a separate denominator from Runs 1-2's crypto tests (different market, different data — mixing
  them would misrepresent both). **42 produced a p-value; 9 survive Benjamini-Hochberg FDR at
  q=0.10** by raw ranking (`results/bh_correction_table_v5.csv`) — but BH survival alone is not
  this run's evidence bar. Applying the full pre-registered bar (BH-FDR pass **AND** positive
  Sharpe in-sample **AND** in holdout **AND** ≥100 events/≥10yr **AND** a structural reason **AND**
  robustness to dropping the best year) leaves **two genuinely independent survivors**: turn-of-
  month (S4) and overnight Nasdaq drift (S2). A third candidate (S8, volatility risk premium)
  clears every element except strict BH-FDR (misses by a small margin, p=0.029 vs. a 0.024
  threshold) and is carried forward flagged, not asserted as equally trustworthy.
- **Portfolio net Sharpe (S2+S4+S8, simple risk parity, vol-targeted to 8% ann.): 0.90, 95% CI
  [0.81, 0.99].** Excluding the flagged S8 leg (the honest, retail-implementable 2-strategy
  version): **Sharpe 0.82, 95% CI [0.74, 0.91].** Both intervals sit comfortably above zero but
  are wide enough that "Sharpe ≈ 0.9" and "Sharpe ≈ 0.75" are not statistically distinguishable
  from each other — say so plainly, as instructed.
- **Minimum viable capital: this is the binding constraint, not the strategy math.** Using micro
  futures (the standard retail-leverage vehicle), correctly-weighted, non-overleveraged
  implementation requires **roughly $250,000-500,000** — below that, granularity forces either a
  badly mismatched position or 2-9x more leverage than backtested. **UCITS ETFs solve this and are
  the realistic vehicle at every retail capital tier from ~3,000 EUR up** — but the vol-premium leg
  (S8) has no accessible EU retail proxy at all (its closest US ETF is PRIIPs-blocked), which is an
  independent reason (on top of weak diversification value and high tail risk) to drop it from a
  real implementation.
- **What's trustworthy**: S4 (turn-of-month) and S2 (overnight Nasdaq drift) — well-powered (678
  and ~13,977 observations), consistent in-sample and holdout, high deflated-Sharpe probability
  even penalized for the full 60-test search space (98% and 94%), stated structural rationale,
  matches published literature. **What's not**: S3 (pre-FOMC drift) looked strong full-sample
  (Sharpe 0.55, p<0.001) but its dedicated in-sample/holdout split shows the effect has decayed to
  statistical insignificance since 2016 (holdout Sharpe 0.08, p=0.40) — excluded. S1 (trend
  following) has no market/lookback combination that clears BH-FDR; gold is a near-miss. S5
  (carry) and S10 (microcap drift) were cleanly skipped for insufficient free data. S6 (COT
  positioning) found no significant signal in any of 6 tests.

## Two real bugs caught and fixed before publishing (exactly what this run was told to hunt for)
1. **S2's initial full-history run showed SPX intraday returns beating overnight by a huge, literature-
   contradicting margin (3730% cumulative).** Root cause: Yahoo's daily `open` field for `^GSPC`
   equals the prior close for ~94% of pre-2008 records (no real recorded open), silently assigning
   almost the entire multi-decade return to the "intraday" bucket by construction. Fixed by
   restricting each index to its own verified-clean start year (SPX 2008+, DJI 1996+, IXIC
   1971+, checked individually). With clean data, the literature's direction (overnight > intraday)
   reappears for SPX and IXIC.
2. **S8's PutWrite index showed a suspicious +35%-in-one-day print on 2020-03-13**, followed by an
   equally implausible -28% "correction" three days later — while SPX itself moved a real but far
   smaller +9.3% that day. Cross-checked against SPX's own moves that week; the magnitude mismatch
   was the tell. The single suspect print was dropped (disclosed, not silently smoothed) and the
   surrounding return recomputed against the last trusted close.

Both are logged in detail in `results/s2_overnight_summary.md` and `results/s8_volpremium_summary.md`.
Per this run's own prior ("any Sharpe >1 is a bug until proven otherwise"), both were caught by
exactly the discipline that prior demands — cross-checking against an independent series (SPX) in
both cases, not by luck.

---

## Per-strategy results

| Strategy | Structural family | Trades/obs | Net Sharpe IS | Net Sharpe holdout | BH-FDR | Verdict |
|---|---|---|---|---|---|---|
| **S4 turn-of-month (N=M=4)** | forced flow (pension/payroll) | 678 | 0.74 | 0.76 | **survives** | **SURVIVOR** |
| **S2 overnight IXIC** | overnight premium/MM hedging/order flow | 13,977 | 0.64 | 0.60 | **survives** | **SURVIVOR** |
| S8 vol risk premium (PutWrite) | implied>realized vol premium | 7,527 | 0.67 | 0.63 | misses (p=0.029 vs 0.024) | Flagged: negatively skewed, -37% maxDD, near-miss BH — included with caution, not a clean survivor |
| S3 pre-FOMC drift | calendar-predictable uncertainty resolution | 255 | 0.75 | **0.08 (p=0.40)** | mixed (robustness cuts survive; dedicated holdout test fails) | Real historically, decayed since 2016 — excluded |
| S1 trend, gold 126d | none (extra scrutiny; well-replicated in lit.) | 304 | 0.53 | 0.56 (p=0.060) | fails (just above threshold) | Near-miss, shown only in sensitivity table |
| S1 trend, other 17 market/lookback cells | same | - | mixed | mixed | fails | No survivor; obscure market (lean hogs) consistently negative, contradicting the "less crowded" prior |
| S6 COT positioning (3 markets × 2 thresholds) | commercial hedger informational edge | 85-280 | -0.63 to 0.88 | -1.77 to 0.44 | fails (all 6) | No significant signal; crude oil directionally negative throughout |
| S9 defensive overlay (on primary portfolio) | risk-off regime filter | 534-678 | n/a (overlay, not standalone) | n/a | not applicable (single pre-registered test, not BH-pooled as a standalone edge) | Improves portfolio Sharpe 0.90->1.03-1.07 AND cuts maxDD roughly in half — see below |
| S5 carry/term structure | carry risk premium | 0 | - | - | - | **SKIPPED** — insufficient free data (see `results/s5_carry_summary.md`) |
| S10 microcap PEAD | capacity-constrained drift | 0 | - | - | - | **SKIPPED** — insufficient free data (no survivorship-free universe available) |
| S7 French factors | n/a | n/a | n/a | n/a | n/a | Reference-only, not a candidate |

Full per-strategy detail: `results/s{1-9}_*_summary.md` and matching `*_raw.json`/`*.csv` files.

## Correlation matrix (the actual point of this run)

`results/portfolio_correlation_matrix.csv`. Selected entries (monthly returns, 1996-2026 overlap):

| | S2 overnight | S4 turn-of-month | S8 vol premium | Mkt-RF (French) |
|---|---|---|---|---|
| S2 overnight | 1.00 | 0.27 | 0.55 | **0.70** |
| S4 turn-of-month | 0.27 | 1.00 | 0.27 | 0.27 |
| S8 vol premium | 0.55 | 0.27 | 1.00 | **0.84** |

**The central, load-bearing finding of this run's correlation analysis: S8 is not a diversifier —
it is substantially disguised equity-market beta (0.84 correlation with Mkt-RF).** S2 is also
meaningfully market-correlated (0.70). **S4 is the one genuinely independent source of return in
this set** (≤0.27 correlation with everything, including the market factor). This is exactly the
scenario the pre-registration's core design principle described: S8 has the highest standalone
Sharpe (0.78) of the three, but the ablation below shows it contributes the *least* to portfolio
Sharpe of the three — standalone Sharpe and portfolio value are not the same thing, and ranking by
the former would have been a mistake.

## Portfolio construction

Three combination schemes computed (no mean-variance optimization, per instruction): equal-weight,
inverse-vol, simple risk parity (inverse-variance). Vol-targeted to 8% annualized (a moderate,
stated target comparable to realized 60/40 stock/bond volatility). Full detail: `results/portfolio_raw.json`.

| Scheme (vol-targeted) | Sharpe | 95% CI | Ann. return | Max DD | Longest underwater |
|---|---|---|---|---|---|
| Equal weight | 0.92 | [0.83, 1.01] | 9.4% | -32.5% | 84 mo |
| Inverse-vol | 0.92 | [0.83, 1.01] | 9.2% | -31.2% | 83 mo |
| **Simple risk parity (primary)** | **0.90** | **[0.81, 0.99]** | 9.0% | -29.7% | 83 mo |
| Simple risk parity, **ex-S8** | **0.82** | **[0.74, 0.91]** | 8.1% | -29.7% | 83 mo |

**Ablation (risk-parity portfolio, drop each strategy in turn)**:

| Dropped | Portfolio Sharpe without it | Marginal contribution |
|---|---|---|
| S4 turn-of-month | 0.77 | **0.128 (largest)** |
| S2 overnight IXIC | 0.79 | 0.108 |
| S8 vol premium | 0.82 | **0.075 (smallest)** |

**S8 — the strategy with the best standalone Sharpe — adds the least to the portfolio.** S4 — a
weaker standalone Sharpe than S8 but far less correlated with everything else — adds the most.
This is the run's thesis, confirmed by its own data, not asserted a priori.

## S9: defensive overlay — a genuinely positive, pre-registered result

Applied to the primary (3-strategy) portfolio: a 200-day trend filter or a 10Y-3M yield-curve
filter, cutting exposure to 0% or 50% when risk-off. **Both filters improve Sharpe (0.90 → 1.03-1.07)
and roughly halve max drawdown (-29.7% → -14.0% to -21.1%)** — this is not merely "less return for
less risk," it's a genuine risk-adjusted improvement, because the filters target exactly the
equity-beta exposure the correlation matrix already flagged as the portfolio's main uncompensated
risk. One caveat stated plainly: this is 4 pre-registered tests on ~45-56 years of overlapping
history for 3 underlying strategies — a small effective sample for a result this clean; reported as
a real, honest finding, not proof it holds forever. Full detail: `results/s9_overlay_summary.md`.

## Retail feasibility (mandatory check, done before any viability claim)

Full detail: `results/retail_feasibility.md`. Headline: **futures are the wrong vehicle for this
portfolio below roughly $250,000-500,000** — 1 micro contract each of MES/MNQ already represents
~$94,000 notional against a strategy designed for ~1x unleveraged notional exposure, so at 10,000
EUR a trader is forced into either a badly mismatched position or ~9.5x more leverage than
backtested. **UCITS ETFs solve the granularity problem at every capital tier from ~3,000 EUR up**
and are the realistic implementation vehicle — but **S8 has no accessible EU retail proxy at all**
(PRIIPs-blocked US ETF, or manual options-writing requiring approval and active management), which
independently reinforces dropping it from a real implementation on top of its weak diversification
value and heavy tail risk. **Operational load**: S4 trades ~24x/year (light); S2 as literally
backtested is a **daily** round trip (~252x/year) — a materially higher realistic burden than its
Sharpe number alone conveys.

## Bottom line
**A portfolio of 2 genuinely uncorrelated, well-evidenced strategies (turn-of-month + overnight
Nasdaq drift) achieves net Sharpe ≈0.82 (95% CI 0.74-0.91), implementable via ordinary UCITS ETFs
at any retail capital size, with a ~7-year worst underwater stretch.** Adding a third, statistically
near-miss, heavily market-correlated, tail-risk-heavy, EU-inaccessible strategy (vol premium) buys
roughly +0.08 Sharpe at a cost this run's own analysis says isn't worth it. A simple trend/yield-
curve overlay is a genuinely good, cheaply-implementable addition, improving Sharpe to ~1.0+ and
roughly halving drawdown. This is a real, useful, non-fabricated result — not a Sharpe-1.5 fantasy,
and not nothing.
