# Macro-regime selected strategy benchmark comparison

Selected strategy is fixed as **btc_eth_macro_gate_balanced**. This report does not modify the selected strategy,
tune on benchmarks, or select a new model.

## Locked holdout at 25 bps

| Strategy | Group | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure | Transaction costs | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | selected_fixed_strategy | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | 3.75% | -5.98% |
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | prior_tier1_regime_momentum | 4.88% | 0.313 | 0.322 | -26.35% | 0.185 | 16.586 | 26.76% | 6.11% | -8.60% |
| eth_buy_hold | simple_crypto_beta | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% | 0.00% | -32.21% |
| btc_eth_50_50 | simple_crypto_beta | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% | 0.00% | -25.10% |
| btc_buy_hold | simple_crypto_beta | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% | 0.00% | -17.65% |

## Cost sensitivity for selected strategy

| Strategy | Group | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure | Transaction costs | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | selected_fixed_strategy | 26.99% | 1.028 | 1.304 | -18.05% | 1.496 | 10.177 | 28.95% | 1.50% | -5.77% |
| btc_eth_macro_gate_balanced | selected_fixed_strategy | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | 3.75% | -5.98% |
| btc_eth_macro_gate_balanced | selected_fixed_strategy | 21.92% | 0.874 | 1.115 | -19.03% | 1.152 | 10.177 | 28.95% | 7.50% | -6.34% |
| btc_eth_macro_gate_balanced | selected_fixed_strategy | 15.85% | 0.681 | 0.871 | -20.25% | 0.783 | 10.177 | 28.95% | 15.00% | -7.06% |

## All holdout cost sensitivity

| Strategy | Cost bps | CAGR | Sharpe | Sortino | Max DD | Annual turnover | Exposure | Transaction costs | Worst month |
|---|---|---|---|---|---|---|---|---|---|
| btc_buy_hold | 10 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% | 0.00% | -17.65% |
| btc_buy_hold | 25 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% | 0.00% | -17.65% |
| btc_buy_hold | 50 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% | 0.00% | -17.65% |
| btc_buy_hold | 100 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% | 0.00% | -17.65% |
| btc_eth_50_50 | 10 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% | 0.00% | -25.10% |
| btc_eth_50_50 | 25 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% | 0.00% | -25.10% |
| btc_eth_50_50 | 50 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% | 0.00% | -25.10% |
| btc_eth_50_50 | 100 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% | 0.00% | -25.10% |
| btc_eth_macro_gate_balanced | 10 | 26.99% | 1.028 | 1.304 | -18.05% | 10.177 | 28.95% | 1.50% | -5.77% |
| btc_eth_macro_gate_balanced | 25 | 25.07% | 0.970 | 1.234 | -18.42% | 10.177 | 28.95% | 3.75% | -5.98% |
| btc_eth_macro_gate_balanced | 50 | 21.92% | 0.874 | 1.115 | -19.03% | 10.177 | 28.95% | 7.50% | -6.34% |
| btc_eth_macro_gate_balanced | 100 | 15.85% | 0.681 | 0.871 | -20.25% | 10.177 | 28.95% | 15.00% | -7.06% |
| equal_weight_top10 | 10 | -39.12% | -0.415 | -0.614 | -63.45% | 1.493 | 100.00% | 0.22% | -28.25% |
| equal_weight_top10 | 25 | -39.25% | -0.418 | -0.619 | -63.51% | 1.493 | 100.00% | 0.55% | -28.25% |
| equal_weight_top10 | 50 | -39.48% | -0.424 | -0.627 | -63.63% | 1.493 | 100.00% | 1.10% | -28.25% |
| equal_weight_top10 | 100 | -39.93% | -0.435 | -0.644 | -63.89% | 1.493 | 100.00% | 2.20% | -28.25% |
| equal_weight_top20 | 10 | -50.26% | -0.565 | -0.826 | -72.60% | 3.121 | 100.00% | 0.46% | -29.94% |
| equal_weight_top20 | 25 | -50.49% | -0.571 | -0.835 | -72.72% | 3.121 | 100.00% | 1.15% | -29.97% |
| equal_weight_top20 | 50 | -50.88% | -0.581 | -0.851 | -72.93% | 3.121 | 100.00% | 2.30% | -30.02% |
| equal_weight_top20 | 100 | -51.64% | -0.602 | -0.880 | -73.35% | 3.121 | 100.00% | 4.60% | -30.13% |
| equal_weight_top30 | 10 | -55.38% | -0.662 | -0.959 | -76.37% | 3.121 | 100.00% | 0.46% | -31.11% |
| equal_weight_top30 | 25 | -55.59% | -0.668 | -0.968 | -76.52% | 3.121 | 100.00% | 1.15% | -31.12% |
| equal_weight_top30 | 50 | -55.93% | -0.678 | -0.983 | -76.78% | 3.121 | 100.00% | 2.30% | -31.13% |
| equal_weight_top30 | 100 | -56.61% | -0.698 | -1.013 | -77.29% | 3.121 | 100.00% | 4.60% | -31.16% |
| eth_buy_hold | 10 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% | 0.00% | -32.21% |
| eth_buy_hold | 25 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% | 0.00% | -32.21% |
| eth_buy_hold | 50 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% | 0.00% | -32.21% |
| eth_buy_hold | 100 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% | 0.00% | -32.21% |
| pure_top10_momentum | 10 | -33.85% | -0.368 | -0.541 | -62.43% | 15.928 | 100.00% | 2.35% | -21.84% |
| pure_top10_momentum | 25 | -35.42% | -0.407 | -0.598 | -63.09% | 15.928 | 100.00% | 5.87% | -21.94% |
| pure_top10_momentum | 50 | -37.94% | -0.472 | -0.694 | -64.18% | 15.928 | 100.00% | 11.74% | -22.09% |
| pure_top10_momentum | 100 | -42.71% | -0.601 | -0.884 | -66.75% | 15.928 | 100.00% | 23.48% | -22.40% |
| pure_top20_momentum | 10 | -43.11% | -0.421 | -0.611 | -70.40% | 24.139 | 100.00% | 3.56% | -26.58% |
| pure_top20_momentum | 25 | -45.13% | -0.471 | -0.684 | -71.82% | 24.139 | 100.00% | 8.90% | -26.80% |
| pure_top20_momentum | 50 | -48.34% | -0.555 | -0.805 | -74.03% | 24.139 | 100.00% | 17.79% | -27.15% |
| pure_top20_momentum | 100 | -54.24% | -0.723 | -1.047 | -77.96% | 24.139 | 100.00% | 35.58% | -27.86% |
| pure_top30_momentum | 10 | -55.89% | -0.648 | -0.964 | -80.81% | 28.012 | 100.00% | 4.13% | -32.65% |
| pure_top30_momentum | 25 | -57.72% | -0.701 | -1.042 | -81.90% | 28.012 | 100.00% | 10.32% | -32.89% |
| pure_top30_momentum | 50 | -60.60% | -0.790 | -1.172 | -83.57% | 28.012 | 100.00% | 20.64% | -33.28% |
| pure_top30_momentum | 100 | -65.80% | -0.968 | -1.430 | -86.49% | 28.012 | 100.00% | 41.29% | -34.07% |
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 10 | 7.53% | 0.408 | 0.418 | -25.54% | 16.586 | 26.76% | 2.44% | -8.42% |
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 25 | 4.88% | 0.313 | 0.322 | -26.35% | 16.586 | 26.76% | 6.11% | -8.60% |
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 50 | 0.61% | 0.155 | 0.160 | -27.86% | 16.586 | 26.76% | 12.22% | -8.91% |
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 100 | -7.43% | -0.160 | -0.167 | -33.96% | 16.586 | 26.76% | 24.45% | -9.52% |

## Group comparison

| Benchmark group | Best benchmark | Selected Sharpe | Best benchmark Sharpe | Selected CAGR | Best benchmark CAGR | Selected max DD | Best benchmark max DD | Beats Sharpe | Beats CAGR | Beats DD |
|---|---|---|---|---|---|---|---|---|---|---|
| simple_crypto_beta | eth_buy_hold | 0.970 | -0.239 | 25.07% | -35.10% | -18.42% | -67.52% | Yes | Yes | Yes |
| point_in_time_top_universe | equal_weight_top10 | 0.970 | -0.418 | 25.07% | -39.25% | -18.42% | -63.51% | Yes | Yes | Yes |
| point_in_time_momentum | pure_top10_momentum | 0.970 | -0.407 | 25.07% | -35.42% | -18.42% | -63.09% | Yes | Yes | Yes |
| prior_tier1_regime_momentum | u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 0.970 | 0.313 | 25.07% | 4.88% | -18.42% | -26.35% | Yes | Yes | Yes |

## Conclusion

- The selected strategy beats simple crypto beta after costs on Sharpe, CAGR, and max drawdown.
- The selected strategy beats top-universe exposure after costs on Sharpe, CAGR, and max drawdown.
- The selected strategy beats pure momentum after costs on Sharpe, CAGR, and max drawdown.
- The selected strategy beats the prior best Tier-1 regime-gated momentum strategy after costs on Sharpe, CAGR, and max drawdown.
- Universe benchmarks are point-in-time within the available Binance research panel, but the panel may still omit assets not present in the collected historical dataset.
