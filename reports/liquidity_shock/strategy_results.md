# Strategy results

## Selected strategy and benchmarks

| Split | Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| development | volatility_shock_continuation_u20_r14_top_momentum_k5_balanced | 59.44% | 1.540 | 1.322 | -17.90% | 3.321 | 7.200 | 17.69% |
| development | btc_eth_50_50 | 83.92% | 1.222 | 1.596 | -76.25% | 1.101 | 0.000 | 100.00% |
| development | eth_buy_hold | 91.49% | 1.202 | 1.633 | -79.30% | 1.154 | 0.000 | 100.00% |
| development | btc_buy_hold | 66.95% | 1.121 | 1.493 | -76.63% | 0.874 | 0.000 | 100.00% |
| development | equal_weight_top10 | 55.91% | 0.964 | 1.214 | -90.72% | 0.616 | 3.516 | 100.00% |
| development | pure_cross_sectional_momentum_top10 | 51.50% | 0.929 | 1.186 | -93.25% | 0.552 | 28.737 | 100.00% |
| holdout | eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| holdout | btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| holdout | btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| holdout | pure_cross_sectional_momentum_top10 | -36.81% | -0.412 | -0.625 | -65.49% | -0.562 | 26.972 | 100.00% |
| holdout | equal_weight_top10 | -39.03% | -0.413 | -0.610 | -63.42% | -0.615 | 1.493 | 100.00% |
| holdout | volatility_shock_continuation_u20_r14_top_momentum_k5_balanced | -13.87% | -0.529 | -0.417 | -40.60% | -0.342 | 8.287 | 20.38% |

## Top development-CPCV candidates

| Candidate | Family | Universe | Rebalance days | Allocation | Top K | Thresholds | Median fold Sharpe | Worst fold Sharpe | Development Sharpe | Development turnover |
|---|---|---|---|---|---|---|---|---|---|---|
| volatility_shock_continuation_u20_r14_top_momentum_k5_balanced | volatility_shock_continuation | 20 | 14 | top_momentum | 5 | balanced | 1.745 | 0.927 | 1.540 | 7.200 |
| volatility_shock_reversal_u10_r14_top_losers_k3_balanced | volatility_shock_reversal | 10 | 14 | top_losers | 3 | balanced | 1.531 | 0.234 | 1.122 | 5.744 |
| volatility_shock_reversal_u10_r14_top_losers_k5_balanced | volatility_shock_reversal | 10 | 14 | top_losers | 5 | balanced | 1.470 | 0.569 | 1.199 | 7.065 |
| volatility_shock_reversal_u20_r14_top_losers_k5_balanced | volatility_shock_reversal | 20 | 14 | top_losers | 5 | balanced | 1.443 | 0.409 | 1.275 | 7.159 |
| volatility_shock_continuation_u20_r7_top_momentum_k5_balanced | volatility_shock_continuation | 20 | 7 | top_momentum | 5 | balanced | 1.429 | 0.250 | 1.574 | 12.966 |
| volatility_shock_reversal_u20_r14_top_losers_k3_balanced | volatility_shock_reversal | 20 | 14 | top_losers | 3 | balanced | 1.296 | 0.112 | 1.093 | 5.874 |
| volatility_shock_continuation_u10_r14_top_momentum_k5_balanced | volatility_shock_continuation | 10 | 14 | top_momentum | 5 | balanced | 1.250 | 0.739 | 1.455 | 7.192 |
| volatility_shock_continuation_u20_r14_top_momentum_k3_balanced | volatility_shock_continuation | 20 | 14 | top_momentum | 3 | balanced | 1.109 | 0.645 | 1.303 | 5.675 |
| volatility_shock_continuation_u20_r7_top_momentum_k3_balanced | volatility_shock_continuation | 20 | 7 | top_momentum | 3 | balanced | 1.068 | 0.472 | 1.506 | 9.180 |
| volatility_shock_continuation_u10_r14_top_momentum_k3_balanced | volatility_shock_continuation | 10 | 14 | top_momentum | 3 | balanced | 1.021 | 0.555 | 1.313 | 5.729 |
| volatility_shock_continuation_u10_r7_top_momentum_k5_balanced | volatility_shock_continuation | 10 | 7 | top_momentum | 5 | balanced | 0.997 | 0.337 | 1.474 | 12.315 |
| combined_shock_index_u20_r14_top_momentum_k3_strict | combined_shock_index | 20 | 14 | top_momentum | 3 | strict | 0.963 | 0.206 | 0.789 | 4.165 |
| volatility_shock_continuation_u20_r7_top_momentum_k5_strict | volatility_shock_continuation | 20 | 7 | top_momentum | 5 | strict | 0.944 | -0.445 | 0.739 | 6.269 |
| volatility_shock_reversal_u10_r7_top_losers_k5_balanced | volatility_shock_reversal | 10 | 7 | top_losers | 5 | balanced | 0.938 | 0.252 | 1.118 | 13.415 |
| negative_liquidity_risk_off_u20_r14_top_momentum_k3_strict | negative_liquidity_risk_off | 20 | 14 | top_momentum | 3 | strict | 0.929 | 0.017 | 0.972 | 12.486 |
| volatility_shock_continuation_u10_r7_top_momentum_k3_balanced | volatility_shock_continuation | 10 | 7 | top_momentum | 3 | balanced | 0.925 | 0.157 | 1.383 | 8.900 |
| volatility_shock_reversal_u10_r7_top_losers_k3_strict | volatility_shock_reversal | 10 | 7 | top_losers | 3 | strict | 0.907 | 0.450 | 0.774 | 5.077 |
| volatility_shock_reversal_u10_r7_top_losers_k3_balanced | volatility_shock_reversal | 10 | 7 | top_losers | 3 | balanced | 0.900 | -0.084 | 0.991 | 10.925 |
| negative_liquidity_risk_off_u10_r7_top_momentum_k3_strict | negative_liquidity_risk_off | 10 | 7 | top_momentum | 3 | strict | 0.897 | -0.323 | 0.919 | 19.089 |
| volatility_shock_continuation_u10_r7_top_momentum_k5_strict | volatility_shock_continuation | 10 | 7 | top_momentum | 5 | strict | 0.895 | -0.408 | 0.794 | 6.152 |
| negative_liquidity_risk_off_u20_r7_top_momentum_k3_strict | negative_liquidity_risk_off | 20 | 7 | top_momentum | 3 | strict | 0.874 | -0.722 | 0.937 | 20.814 |
| combined_shock_index_u20_r14_top_momentum_k3_balanced | combined_shock_index | 20 | 14 | top_momentum | 3 | balanced | 0.862 | 0.495 | 0.781 | 5.724 |
| volatility_shock_continuation_u10_r14_top_momentum_k5_strict | volatility_shock_continuation | 10 | 14 | top_momentum | 5 | strict | 0.854 | N/A | 1.142 | 4.217 |
| volatility_shock_reversal_u20_r7_top_losers_k5_strict | volatility_shock_reversal | 20 | 7 | top_losers | 5 | strict | 0.852 | 0.231 | 0.902 | 6.241 |
| negative_liquidity_risk_off_u10_r14_top_momentum_k3_strict | negative_liquidity_risk_off | 10 | 14 | top_momentum | 3 | strict | 0.835 | -0.139 | 0.807 | 11.719 |
