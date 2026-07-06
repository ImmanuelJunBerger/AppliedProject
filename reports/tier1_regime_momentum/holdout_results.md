# Locked holdout results

## Final selected strategy and benchmarks

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 4.88% | 0.313 | 0.322 | -26.35% | 0.185 | 16.586 | 26.76% |
| eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| pure_cross_sectional_momentum | -25.58% | -0.584 | -0.831 | -47.00% | -0.544 | 15.367 | 60.00% |
| equal_weight_top30 | -55.24% | -0.658 | -0.953 | -76.26% | -0.724 | 3.121 | 100.00% |

## Cost sensitivity for selected strategy

| Cost bps | CAGR | Sharpe | Max DD | Annual turnover | Exposure |
|---|---|---|---|---|---|
| 10 | 7.53% | 0.408 | -25.54% | 16.586 | 26.76% |
| 25 | 4.88% | 0.313 | -26.35% | 16.586 | 26.76% |
| 50 | 0.61% | 0.155 | -27.86% | 16.586 | 26.76% |
| 100 | -7.43% | -0.160 | -33.96% | 16.586 | 26.76% |

## Previous defensive BTC/ETH/cash candidates

| Previous defensive candidate | CAGR | Sharpe | Max DD | Annual turnover | Exposure |
|---|---|---|---|---|---|
| D_btc_eth_biweekly_vt25 | -0.52% | 0.023 | -11.19% | 3.201 | 13.24% |
| A_market_gate_k5_dd20_vp65 | 0.00% | 0.000 | 0.00% | 0.000 | 0.00% |
| eth_buy_hold | -35.10% | -0.239 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | -27.21% | -0.285 | -59.21% | 0.000 | 100.00% |
| btc_buy_hold | -21.82% | -0.332 | -51.16% | 0.000 | 100.00% |
| B_defensive_rotation_dd25_vp70_vt35 | -6.13% | -0.417 | -14.24% | 5.327 | 8.41% |
| equal_weight_top10 | -40.64% | -0.452 | -64.05% | 1.628 | 100.00% |
| C_cash_floor_k5_vt35_brake10 | -8.15% | -1.859 | -13.43% | 1.714 | 2.98% |

## Acceptance

- Passes paper-trading criteria: No
- Holdout Sharpe: 0.313
- Holdout CAGR: 4.88%
- Holdout max drawdown: -26.35%
- Holdout annual turnover: 16.59x
- Failures: holdout Sharpe <= 0.5; annual turnover > 12x
