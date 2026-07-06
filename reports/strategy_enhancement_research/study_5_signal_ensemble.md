# Study 5: Signal ensemble

## Development-only selection

| Candidate | Family | Selection score | Median fold Sharpe | Worst fold | Positive folds | Dev Sharpe | Dev turnover |
|---|---|---|---|---|---|---|---|
| ensemble_equal_weight | Interpretable signal ensemble | 1.762 | 1.595 | -1.068 | 86.67% | 1.368 | 11.117 |
| ensemble_linear_predeclared | Interpretable signal ensemble | 1.702 | 1.545 | -1.102 | 86.67% | 1.262 | 11.359 |
| ensemble_rank_average | Interpretable signal ensemble | 1.650 | 1.442 | -0.902 | 86.67% | 1.420 | 8.440 |
| logistic_ensemble | Interpretable logistic signal ensemble | 1.456 | 1.221 | -0.793 | 86.67% | 1.179 | 6.493 |

Selected by development-only CPCV: **ensemble_equal_weight**.

## Development vs holdout

| Candidate | Dev Sharpe | Holdout Sharpe | Sharpe retention | Dev CAGR | Holdout CAGR | CAGR retention | Dev max DD | Holdout max DD | Holdout turnover | Holdout exposure |
|---|---|---|---|---|---|---|---|---|---|---|
| ensemble_equal_weight | 1.368 | -0.216 | -15.81% | 56.35% | -10.13% | -17.97% | -50.35% | -41.04% | 11.087 | 50.38% |
| ensemble_rank_average | 1.420 | 0.256 | 18.05% | 64.36% | 3.35% | 5.20% | -42.09% | -33.50% | 8.911 | 44.30% |
| ensemble_linear_predeclared | 1.262 | -0.286 | -22.66% | 49.29% | -11.89% | -24.13% | -54.13% | -42.04% | 11.284 | 50.63% |
| logistic_ensemble | 1.179 | 0.061 | 5.20% | 46.37% | -3.26% | -7.03% | -43.13% | -32.94% | 5.767 | 55.02% |

## Statistical validation

- PBO: 72.86%
- Deflated Sharpe probability for selected candidate: 9.44%
- Worst CPCV fold: -1.068
- Positive CPCV folds: 86.67%

## Frozen benchmark comparison

- Frozen holdout Sharpe: 0.970
- Frozen holdout CAGR: 25.07%
- Frozen holdout max drawdown: -18.42%
- Selected candidate holdout Sharpe: -0.216
- Selected candidate holdout CAGR: -10.13%
- Selected candidate holdout max drawdown: -41.04%

## Interpretation

Status: **failed_holdout**.

Candidate improves or ranks well in development but fails locked holdout economics.

Feature drivers: macro, momentum, volatility, dispersion, stablecoin growth, TVL growth.

### Economic interpretation and decision mechanics

The ensemble raises exposure when multiple predeclared signals agree: favourable macro regime, positive BTC/ETH momentum, lower volatility stress, lower dispersion stress, positive stablecoin growth, and positive TVL growth. Exposure falls when signal agreement weakens. The ensemble does not independently choose BTC versus ETH.

The selected candidate's holdout CAGR is below the frozen benchmark. Even when Sharpe or drawdown improves, it should be treated as a conservative overlay for paper monitoring rather than a replacement.
