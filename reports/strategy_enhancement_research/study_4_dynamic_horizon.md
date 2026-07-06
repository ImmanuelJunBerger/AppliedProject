# Study 4: Regime-dependent momentum horizon

## Development-only selection

| Candidate | Family | Selection score | Median fold Sharpe | Worst fold | Positive folds | Dev Sharpe | Dev turnover |
|---|---|---|---|---|---|---|---|
| fixed_momentum_126d | Regime-dependent momentum horizon | 1.079 | 1.296 | -1.652 | 80.00% | 1.165 | 16.096 |
| fixed_momentum_42d | Regime-dependent momentum horizon | 0.978 | 1.289 | -1.464 | 80.00% | 0.933 | 18.894 |
| fixed_momentum_63d | Regime-dependent momentum horizon | 0.928 | 1.286 | -1.609 | 73.33% | 0.902 | 18.455 |
| dynamic_short_risk_on_long_neutral | Regime-dependent momentum horizon | 0.733 | 1.286 | -1.652 | 80.00% | 1.095 | 22.811 |
| dynamic_medium_risk_on_long_neutral | Regime-dependent momentum horizon | 0.679 | 1.124 | -1.630 | 73.33% | 1.004 | 20.098 |
| fixed_momentum_21d | Regime-dependent momentum horizon | 0.538 | 1.092 | -1.422 | 80.00% | 1.082 | 23.974 |
| dynamic_short_risk_on_medium_neutral | Regime-dependent momentum horizon | 0.381 | 1.039 | -1.667 | 73.33% | 0.901 | 24.149 |

Selected by development-only CPCV: **fixed_momentum_126d**.

## Development vs holdout

| Candidate | Dev Sharpe | Holdout Sharpe | Sharpe retention | Dev CAGR | Holdout CAGR | CAGR retention | Dev max DD | Holdout max DD | Holdout turnover | Holdout exposure |
|---|---|---|---|---|---|---|---|---|---|---|
| fixed_momentum_21d | 1.082 | -0.552 | -50.99% | 55.47% | -31.31% | -56.44% | -78.84% | -63.31% | 20.998 | 78.82% |
| fixed_momentum_42d | 0.933 | -0.642 | -68.79% | 42.88% | -35.37% | -82.49% | -79.56% | -68.71% | 19.770 | 80.48% |
| fixed_momentum_63d | 0.902 | -0.382 | -42.34% | 40.83% | -28.07% | -68.75% | -83.08% | -69.03% | 15.530 | 80.83% |
| fixed_momentum_126d | 1.165 | -0.426 | -36.53% | 64.28% | -28.36% | -44.12% | -82.25% | -63.65% | 12.890 | 81.78% |
| dynamic_short_risk_on_long_neutral | 1.095 | -0.566 | -51.71% | 56.96% | -33.31% | -58.48% | -81.62% | -64.43% | 20.438 | 80.38% |
| dynamic_medium_risk_on_long_neutral | 1.004 | -0.623 | -62.07% | 49.57% | -33.66% | -67.91% | -82.71% | -64.96% | 21.201 | 80.12% |
| dynamic_short_risk_on_medium_neutral | 0.901 | -0.411 | -45.64% | 40.24% | -28.96% | -71.98% | -83.49% | -69.06% | 19.473 | 79.02% |

## Statistical validation

- PBO: 27.14%
- Deflated Sharpe probability for selected candidate: 2.86%
- Worst CPCV fold: -1.652
- Positive CPCV folds: 80.00%

## Frozen benchmark comparison

- Frozen holdout Sharpe: 0.970
- Frozen holdout CAGR: 25.07%
- Frozen holdout max drawdown: -18.42%
- Selected candidate holdout Sharpe: -0.426
- Selected candidate holdout CAGR: -28.36%
- Selected candidate holdout max drawdown: -63.65%

## Interpretation

Status: **failed_holdout**.

Candidate improves or ranks well in development but fails locked holdout economics.

Feature drivers: macro regime score plus BTC/ETH momentum.

### Economic interpretation and decision mechanics

The strategy chooses BTC or ETH using lagged momentum, with the lookback horizon tied to macro regime. Shorter horizons are intended for strong risk-on environments, while longer horizons are intended for uncertain regimes. Cash is held in risk-off states.

The selected candidate's holdout CAGR is below the frozen benchmark. Even when Sharpe or drawdown improves, it should be treated as a conservative overlay for paper monitoring rather than a replacement.
