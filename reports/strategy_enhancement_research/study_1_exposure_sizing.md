# Study 1: Macro-conditioned exposure sizing

## Development-only selection

| Candidate | Family | Selection score | Median fold Sharpe | Worst fold | Positive folds | Dev Sharpe | Dev turnover |
|---|---|---|---|---|---|---|---|
| discrete_aggressive | Macro-conditioned exposure sizing | 1.658 | 1.477 | -1.011 | 86.67% | 1.127 | 10.938 |
| continuous_aggressive_percentile | Macro-conditioned continuous sizing | 1.652 | 1.474 | -0.888 | 80.00% | 1.162 | 10.478 |
| continuous_linear_percentile | Macro-conditioned continuous sizing | 1.583 | 1.447 | -1.057 | 80.00% | 1.084 | 11.527 |
| continuous_conservative_percentile | Macro-conditioned continuous sizing | 1.444 | 1.312 | -1.198 | 86.67% | 0.963 | 12.038 |
| discrete_balanced_0_25_50_75_100 | Macro-conditioned exposure sizing | 1.419 | 1.354 | -1.073 | 80.00% | 1.048 | 13.335 |
| discrete_conservative | Macro-conditioned exposure sizing | 1.351 | 1.308 | -1.425 | 80.00% | 0.953 | 10.938 |

Selected by development-only CPCV: **discrete_aggressive**.

## Development vs holdout

| Candidate | Dev Sharpe | Holdout Sharpe | Sharpe retention | Dev CAGR | Holdout CAGR | CAGR retention | Dev max DD | Holdout max DD | Holdout turnover | Holdout exposure |
|---|---|---|---|---|---|---|---|---|---|---|
| discrete_balanced_0_25_50_75_100 | 1.048 | -0.360 | -34.38% | 38.32% | -15.01% | -39.17% | -60.17% | -45.89% | 13.230 | 53.53% |
| discrete_conservative | 0.953 | -0.233 | -24.47% | 26.46% | -7.96% | -30.10% | -53.22% | -35.48% | 10.007 | 39.45% |
| discrete_aggressive | 1.127 | -0.261 | -23.20% | 48.90% | -14.89% | -30.45% | -66.48% | -48.42% | 10.007 | 64.45% |
| continuous_linear_percentile | 1.084 | -0.374 | -34.44% | 38.50% | -14.62% | -37.98% | -60.88% | -43.72% | 10.768 | 52.52% |
| continuous_conservative_percentile | 0.963 | -0.284 | -29.47% | 27.98% | -9.35% | -33.42% | -53.71% | -36.98% | 11.703 | 40.99% |
| continuous_aggressive_percentile | 1.162 | -0.407 | -35.02% | 48.11% | -18.53% | -38.52% | -65.27% | -48.15% | 9.376 | 62.09% |

## Statistical validation

- PBO: 34.29%
- Deflated Sharpe probability for selected candidate: 5.29%
- Worst CPCV fold: -1.011
- Positive CPCV folds: 86.67%

## Frozen benchmark comparison

- Frozen holdout Sharpe: 0.970
- Frozen holdout CAGR: 25.07%
- Frozen holdout max drawdown: -18.42%
- Selected candidate holdout Sharpe: -0.261
- Selected candidate holdout CAGR: -14.89%
- Selected candidate holdout max drawdown: -48.42%

## Interpretation

Status: **failed_holdout**.

Candidate improves or ranks well in development but fails locked holdout economics.

Feature drivers: vix_level, vix_change, equity_momentum, equity_volatility.

### Economic interpretation and decision mechanics

Exposure rises when lagged equity momentum is stronger and volatility stress is lower (lower VIX, smaller VIX increases, and lower equity realized volatility). Exposure falls when those macro risk indicators deteriorate. The candidate does not change BTC versus ETH selection; it only changes total invested exposure.

The selected candidate's holdout CAGR is below the frozen benchmark. Even when Sharpe or drawdown improves, it should be treated as a conservative overlay for paper monitoring rather than a replacement.
