# S6: CFTC COT positioning extremes — summary

Weekly CFTC legacy report, commercial net position (% of open interest) z-scored over a trailing
156-week window; go with commercials' direction when |z| exceeds 2.0 (primary) or 1.5
(sensitivity), 3 markets (ES E-mini S&P, CL WTI crude, GC gold).

| Market | Threshold | Net Sharpe (full/IS/holdout) | p (IS) | p (holdout) | n |
|---|---|---|---|---|---|
| ES | z=2.0 | 0.60 / 0.56 / 0.67 | 0.27 | 0.31 | 88 |
| ES | z=1.5 | 0.13 / -0.24 / 0.78 | 0.65 | 0.21 | 188 |
| CL | z=2.0 | -0.91 / -0.63 / -1.77 | 0.75 | 0.89 | 85 |
| CL | z=1.5 | -0.20 / -0.32 / 0.02 | 0.68 | 0.49 | 165 |
| GC | z=2.0 | 0.75 / **0.88** / 0.44 | 0.13 | 0.36 | 121 |
| GC | z=1.5 | 0.43 / 0.66 / -0.21 | 0.10 | 0.60 | 280 |

Full detail: `results/s6_cot_raw.json`. Trade-level data: `results/s6_cot_*_trades.csv`.

**Data-quality note fixed before running**: the CFTC's own market-label for the E-mini S&P 500
contract changed from "E-MINI S&P 500 STOCK INDEX - CME" to "E-MINI S&P 500 - CME" on 2022-02-08
(same underlying, just a relabeling) — the two name variants were spliced into one continuous
series; using either alone would have silently truncated 4+ years of history.

**Verdict: no clear edge.** No slice reaches conventional significance (best p=0.10, GC z=1.5,
in-sample only). Crude oil is directionally negative throughout, both thresholds, both regimes —
a real (if weakly powered) non-finding, not noise-both-ways. Gold is the most suggestive (IS Sharpe
0.66-0.88) but weakens or inverts in holdout at both thresholds, the same instability pattern seen
in S3. Weekly-resolution positioning data simply does not generate enough independent events over
the available ~20-26 years to give this hypothesis real statistical power — consistent with the
pre-registration's own "no strong prior either way" framing. Excluded from the portfolio candidate
set: fails the p<0.05-somewhere-with-holdout-confirmation bar cleanly.
