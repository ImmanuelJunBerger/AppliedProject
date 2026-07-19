# S7: Fama-French factors — correlation reference only

Not a scored candidate strategy (no hypothesis test, no N_TESTS entries, no holdout — a diagnostic
column, per pre-registration). Mkt-RF, SMB (size), HML (value), RMW (profitability/quality), CMA
(investment), Mom (momentum), RF (risk-free), daily, 1963-2026 (15,833 days), from the Kenneth
French Data Library. Used in the portfolio-construction correlation matrix to check whether any of
S1/S2/S4/S8/S9's surviving return streams are secretly disguised factor exposure rather than an
independent source of return. Cached: `results/s7_french_factors_reference.csv`.
