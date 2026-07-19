# S9: Defensive/regime overlay — summary

Tested on the primary constructed portfolio (S2 overnight + S4 turn-of-month + S8 vol premium,
simple-risk-parity weights, vol-targeted to 8% ann.), not as a standalone return stream, per
pre-registration. Two filters (SPX vs. 200-day MA; 10Y-3M yield curve sign) × two intensities
(cut exposure to 0% or 50% when risk-off). Signal from month-end t-1 applied to month t.

| Overlay | Sharpe | Ann. return | Ann. vol | Max DD | Longest underwater | n months |
|---|---|---|---|---|---|---|
| **Base portfolio (no overlay)** | 0.90 | 8.98% | 10.0% | -29.7% | 83mo | 678 |
| Trend (200dma), floor 0% | **1.07** | 8.31% | 7.8% | **-14.0%** | **50mo** | 678 |
| Trend (200dma), floor 50% | 1.03 | 8.65% | 8.4% | -18.1% | 66mo | 678 |
| Yield curve (10Y-3M), floor 0% | 1.03 | 9.71% | 9.4% | -21.1% | 61mo | 534 |
| Yield curve (10Y-3M), floor 50% | 1.05 | 10.07% | 9.6% | -21.1% | 61mo | 534 |

Full detail: `results/s9_overlay_raw.json`. Returns: `results/s9_overlay_*_monthly_returns.csv`.

**The overlay does not merely reduce return proportionally — it improves risk-adjusted return and
materially shortens pain.** This coheres with, rather than contradicts, the correlation-matrix
finding: S2 and S8 both carry substantial equity-market beta (0.70 and 0.84 correlation with
Mkt-RF respectively), so an equity risk-off filter is hedging exactly the exposure the portfolio
already has too much of. Max drawdown roughly halves (trend/floor-0%: -29.7% -> -14.0%) and the
longest underwater stretch shrinks from 83 to 50 months. The yield-curve filter has a shorter usable
history (FRED's T10Y3M starts 1982, 44 years of coverage vs. the base portfolio's 56) — disclosed,
not hidden, in the `n_months` column.

**Caveat, stated plainly**: this is one pre-registered test (2 filters × 2 intensities, no grid
search after seeing results), on a portfolio built from only 3 underlying strategies over
overlapping history — a genuinely small effective sample for a claim this clean-looking. It is
reported as a real, honest, pre-specified finding, not as proof the overlay will keep working
exactly this well going forward.
