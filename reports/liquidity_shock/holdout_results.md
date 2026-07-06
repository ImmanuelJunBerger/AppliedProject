# Locked holdout results

## Holdout comparison

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| pure_cross_sectional_momentum_top10 | -36.81% | -0.412 | -0.625 | -65.49% | -0.562 | 26.972 | 100.00% |
| equal_weight_top10 | -39.03% | -0.413 | -0.610 | -63.42% | -0.615 | 1.493 | 100.00% |
| volatility_shock_continuation_u20_r14_top_momentum_k5_balanced | -13.87% | -0.529 | -0.417 | -40.60% | -0.342 | 8.287 | 20.38% |

## Cost sensitivity for selected strategy

| Cost bps | CAGR | Sharpe | Max DD | Annual turnover | Exposure |
|---|---|---|---|---|---|
| 10 | -12.79% | -0.476 | -39.77% | 8.287 | 20.38% |
| 25 | -13.87% | -0.529 | -40.60% | 8.287 | 20.38% |
| 50 | -15.64% | -0.618 | -41.96% | 8.287 | 20.38% |
| 100 | -19.09% | -0.793 | -44.59% | 8.287 | 20.38% |

## Acceptance

- Passes paper-trading criteria: No
- Holdout Sharpe: -0.529
- Holdout CAGR: -13.87%
- Holdout max drawdown: -40.60%
- Holdout annual turnover: 8.29x
- Failures: holdout Sharpe <= 0.5; holdout CAGR <= 0; does not survive 50 bps
