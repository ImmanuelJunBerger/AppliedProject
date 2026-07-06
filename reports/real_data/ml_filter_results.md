# False-breakout ML filter results

Every quarterly refit uses a trailing three-year training window. The last 25% of dates inside that window is an inner validation segment used to choose the raw-after-cost or volatility-adjusted label and a target rejection rate from 10% through 70%. Labels enter training only after their holding period ends.

Funding is not present in the Binance spot OHLCV file and was therefore not used. The runner will include a lagged funding feature when that column is supplied by a separate derivatives source.

## Locked 2022–2024 validation comparison

| Configuration | Train CAGR | Train Sharpe | Validation CAGR | Validation Sharpe | Validation Max DD | Rejected |
|---|---|---|---|---|---|---|
| no_ml_filter | 75.70% | 1.900 | 2.87% | 0.279 | -19.97% | 0.00% |
| logistic_regression__binary_filter | 139.57% | 2.704 | 3.65% | 0.349 | -19.31% | 29.58% |
| logistic_regression__probability_weighted | 82.74% | 2.050 | 6.87% | 0.528 | -18.25% | 29.58% |
| logistic_regression__drawdown_aware | 94.63% | 1.840 | 6.33% | 0.467 | -19.53% | 29.58% |
| logistic_regression__volatility_targeted | 115.42% | 2.363 | 8.99% | 0.439 | -45.14% | 29.58% |
| random_forest__binary_filter | 110.85% | 2.302 | 0.94% | 0.139 | -22.03% | 23.14% |
| random_forest__probability_weighted | 86.42% | 2.096 | 4.15% | 0.328 | -22.94% | 23.14% |
| random_forest__drawdown_aware | 100.83% | 1.915 | 3.03% | 0.256 | -23.74% | 23.14% |
| random_forest__volatility_targeted | 120.08% | 2.401 | 9.80% | 0.463 | -46.02% | 23.14% |
| gradient_boosting__binary_filter | 86.11% | 2.026 | 11.94% | 0.647 | -31.56% | 22.94% |
| gradient_boosting__probability_weighted | 91.03% | 2.129 | 4.09% | 0.373 | -19.21% | 22.94% |
| gradient_boosting__drawdown_aware | 91.59% | 1.836 | 2.76% | 0.260 | -20.33% | 22.94% |
| gradient_boosting__volatility_targeted | 110.05% | 2.322 | 9.01% | 0.435 | -46.38% | 22.94% |

Selected before holdout: **gradient_boosting__binary_filter**.

The minimum probability-weighted exposure multiplier is 20%, and binary filtering accepts at least 30% of available signals at every rebalance. This prevents recurrence of the prior 67.98% unconstrained over-filtering behavior.
