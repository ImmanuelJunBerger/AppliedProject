# S1: Time-series momentum/trend — summary

6 markets (ES, ZN, 6E, GC, CL, HE) × 3 lookbacks (63/126/252d), vol-targeted to 10% ann., monthly
rebal, ~2000-2026 (26 years), net of futures commission+spread costs (`src/tradfi_costs.py`).

| Market | lb63 net Sharpe (full/IS/holdout) | lb126 | lb252 |
|---|---|---|---|
| ES (S&P) | 0.29 / 0.22 / 0.43 | 0.25 / 0.42 / -0.08 | **0.38 / 0.42 / 0.30** |
| ZN (10Y) | -0.01 / -0.14 / 0.30 | 0.03 / -0.12 / 0.36 | 0.07 / 0.07 / 0.06 |
| 6E (EUR) | 0.25 / 0.36 / 0.00 | 0.15 / 0.30 / -0.21 | -0.01 / 0.08 / -0.19 |
| GC (gold) | 0.25 / -0.03 / 0.85 | **0.54 / 0.53 / 0.56** | **0.48 / 0.51 / 0.43** |
| CL (crude) | 0.14 / -0.05 / 0.41 | 0.21 / 0.10 / 0.39 | 0.10 / 0.12 / 0.07 |
| HE (lean hogs, obscure) | -0.25 / -0.38 / 0.04 | **-0.72 / -0.72 / -0.71** | -0.42 / -0.27 / -0.74 |
| Equal-weight blend | 0.24 / -0.02 / 0.77 | 0.16 / 0.16 / 0.15 | 0.21 / 0.33 / -0.03 |

Full metrics + DSR: `results/s1_tsmom_raw.json`. Per-series returns: `results/s1_tsmom_*_net_returns.csv`.

**Most consistent single-market survivor: gold (GC), both 126d and 252d lookbacks positive IS AND
holdout (0.53/0.56 and 0.51/0.43).** ES 252d also holds up reasonably (0.42/0.30). **The obscure
market (lean hogs) is not a hidden gem — it is consistently, sometimes severely, negative across
all three lookbacks and both regimes.** This directly contradicts the naive "obscure = less
crowded = better" prior stated in the pre-registration; reported exactly as found, not softened.
The equal-weight blend is noisier than any individual well-behaved market (lb252 blend is IS 0.33 /
holdout -0.03) because it's dragged down by including HE and the weaker legs — an early signal that
naive equal-weighting across including-the-losers is not obviously better than a more selective
combination, which the portfolio-construction step (correlation/ablation) will test properly rather
than asserting here.

No single-market result here clears the run's evidence bar alone (dropping-best-year/best-market
and BH-FDR correction applied fleet-wide in the final synthesis, not per-strategy) — these are
candidate return streams for the portfolio step, not standalone claims yet.
