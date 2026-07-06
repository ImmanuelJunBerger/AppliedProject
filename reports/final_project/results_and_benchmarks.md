# Results and benchmarks

## Development and holdout

| Split | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure |
|---|---|---|---|---|---|---|---|
| development | 20.00% | 0.628 | 0.593 | -74.09% | 0.270 | 11.088 | 49.81% |
| holdout | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |

## Holdout benchmark comparison at 25 bps

| Strategy | Group | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure | Worst month |
|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | selected_fixed_strategy | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | -5.98% |
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | prior_tier1_regime_momentum | 4.88% | 0.313 | 0.322 | -26.35% | 0.185 | 16.586 | 26.76% | -8.60% |
| eth_buy_hold | simple_crypto_beta | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% | -32.21% |
| btc_eth_50_50 | simple_crypto_beta | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% | -25.10% |
| btc_buy_hold | simple_crypto_beta | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% | -17.65% |
| pure_top10_momentum | point_in_time_momentum | -35.42% | -0.407 | -0.598 | -63.09% | -0.561 | 15.928 | 100.00% | -21.94% |
| equal_weight_top10 | point_in_time_top_universe | -39.25% | -0.418 | -0.619 | -63.51% | -0.618 | 1.493 | 100.00% | -28.25% |
| pure_top20_momentum | point_in_time_momentum | -45.13% | -0.471 | -0.684 | -71.82% | -0.628 | 24.139 | 100.00% | -26.80% |
| equal_weight_top20 | point_in_time_top_universe | -50.49% | -0.571 | -0.835 | -72.72% | -0.694 | 3.121 | 100.00% | -29.97% |
| equal_weight_top30 | point_in_time_top_universe | -55.59% | -0.668 | -0.968 | -76.52% | -0.726 | 3.121 | 100.00% | -31.12% |
| pure_top30_momentum | point_in_time_momentum | -57.72% | -0.701 | -1.042 | -81.90% | -0.705 | 28.012 | 100.00% | -32.89% |

## Benchmark-group result

| Benchmark group | Best benchmark | Selected Sharpe | Best benchmark Sharpe | Selected CAGR | Best benchmark CAGR | Beats Sharpe | Beats CAGR | Beats drawdown |
|---|---|---|---|---|---|---|---|---|
| simple_crypto_beta | eth_buy_hold | 0.970 | -0.239 | 25.07% | -35.10% | Yes | Yes | Yes |
| point_in_time_top_universe | equal_weight_top10 | 0.970 | -0.418 | 25.07% | -39.25% | Yes | Yes | Yes |
| point_in_time_momentum | pure_top10_momentum | 0.970 | -0.407 | 25.07% | -35.42% | Yes | Yes | Yes |
| prior_tier1_regime_momentum | u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 0.970 | 0.313 | 25.07% | 4.88% | Yes | Yes | Yes |

## Cost sensitivity

| Cost bps | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure | Transaction costs |
|---|---|---|---|---|---|---|---|---|
| 10 | 26.99% | 1.028 | 1.304 | -18.05% | 1.496 | 10.177 | 28.95% | 1.50% |
| 25 | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | 3.75% |
| 50 | 21.92% | 0.874 | 1.115 | -19.03% | 1.152 | 10.177 | 28.95% | 7.50% |
| 100 | 15.85% | 0.681 | 0.871 | -20.25% | 0.783 | 10.177 | 28.95% | 15.00% |
