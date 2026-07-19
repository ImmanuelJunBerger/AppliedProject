# S4: Turn-of-month effect — summary

`^GSPC`, N trading days before month-end through N trading days into next month (diagonal N=M
combinations scored; 12 off-diagonal combinations logged descriptively only, matching Run 2's
seasonality-bucket discipline), 1970-2026, 678 monthly events (near-full coverage).

| Window | Gross Sharpe | Net Sharpe (full) | Net Sharpe (IS) | Net Sharpe (holdout) | p (IS) | p (holdout) |
|---|---|---|---|---|---|---|
| N=M=1 | 0.42 | 0.40 | 0.52 | 0.13 | - | - |
| N=M=2 | 0.61 | 0.59 | 0.63 | 0.49 | - | - |
| N=M=3 | 0.68 | 0.66 | 0.66 | **0.68** | 0.00002 | 0.0026 |
| **N=M=4** | **0.76** | **0.74** | **0.74** | **0.76** | **~0** | **0.0009** |

Full detail: `results/s4_tom_raw.json`. Event data: `results/s4_tom_N{k}_M{k}_events.csv`.

**Strongest, cleanest candidate found so far in Run 5.** N=M=4 (last 4 trading days of the month
through the first 4 of the next): 678 events, Sharpe 0.74 in-sample and 0.76 in holdout — holdout
is not just positive, it's *as strong as* in-sample, unusual and reassuring. Win rate 61-66%.
**Robustness check (drop single best year): removing 2020 (the best year) moves net Sharpe from
0.743 to 0.712 — a 4% relative change, not a strategy carried by one lucky year.** N=1 and N=2 are
weaker and decay substantially in holdout, suggesting the effect concentrates specifically in the
wider ~1-week window around month-end, not the single boundary day itself — consistent with a
multi-day flow-based mechanism (payroll/pension contributions arriving over several days) rather
than a single-tick calendar quirk.

**Clears every element of this run's evidence bar** on its own terms: >100 trades (678), positive
net Sharpe in-sample AND holdout, survives dropping the best year, has a stated structural
rationale (forced pension/payroll flow), matches decades-old published literature (Ariel 1987,
Lakonishok & Smidt 1988). Final BH-FDR correction against the full Run-5 N_TESTS pool applied in
`RESULTS_V5.md`, not asserted here as a finding in isolation.
