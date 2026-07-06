# Benchmark comparison

The full-feature ML stress-test candidate is included only as a rejected benchmark.

| Name | Family | Group | Split | Cost bps | CAGR | Sharpe | Sortino | Max DD | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | Frozen macro gate | frozen_strategy | development | 10 | 22.01% | 0.661 | 0.623 | -73.56% | 11.088 | 49.81% |
| btc_eth_macro_gate_balanced | Frozen macro gate | frozen_strategy | holdout | 10 | 26.99% | 1.028 | 1.304 | -18.05% | 10.177 | 28.95% |
| btc_buy_hold | BTC buy-and-hold | benchmark | development | 10 | 66.95% | 1.121 | 1.493 | -76.63% | 0.000 | 100.00% |
| btc_buy_hold | BTC buy-and-hold | benchmark | holdout | 10 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | ETH buy-and-hold | benchmark | development | 10 | 91.49% | 1.202 | 1.633 | -79.30% | 0.000 | 100.00% |
| eth_buy_hold | ETH buy-and-hold | benchmark | holdout | 10 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | 50/50 BTC/ETH | benchmark | development | 10 | 83.92% | 1.222 | 1.596 | -76.25% | 0.000 | 100.00% |
| btc_eth_50_50 | 50/50 BTC/ETH | benchmark | holdout | 10 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | Equal-weight top 10 | benchmark | development | 10 | 55.37% | 0.960 | 1.209 | -90.77% | 3.516 | 100.00% |
| equal_weight_top10 | Equal-weight top 10 | benchmark | holdout | 10 | -39.12% | -0.415 | -0.614 | -63.45% | 1.493 | 100.00% |
| pure_momentum | Pure momentum | benchmark | development | 10 | 48.92% | 0.910 | 1.151 | -94.82% | 19.419 | 100.00% |
| pure_momentum | Pure momentum | benchmark | holdout | 10 | -33.74% | -0.363 | -0.534 | -62.53% | 16.554 | 100.00% |
| btc_eth_macro_gate_balanced | Frozen macro gate | frozen_strategy | development | 25 | 20.00% | 0.628 | 0.593 | -74.09% | 11.088 | 49.81% |
| btc_eth_macro_gate_balanced | Frozen macro gate | frozen_strategy | holdout | 25 | 25.07% | 0.970 | 1.234 | -18.42% | 10.177 | 28.95% |
| btc_buy_hold | BTC buy-and-hold | benchmark | development | 25 | 66.95% | 1.121 | 1.493 | -76.63% | 0.000 | 100.00% |
| btc_buy_hold | BTC buy-and-hold | benchmark | holdout | 25 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | ETH buy-and-hold | benchmark | development | 25 | 91.49% | 1.202 | 1.633 | -79.30% | 0.000 | 100.00% |
| eth_buy_hold | ETH buy-and-hold | benchmark | holdout | 25 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | 50/50 BTC/ETH | benchmark | development | 25 | 83.92% | 1.222 | 1.596 | -76.25% | 0.000 | 100.00% |
| btc_eth_50_50 | 50/50 BTC/ETH | benchmark | holdout | 25 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | Equal-weight top 10 | benchmark | development | 25 | 54.55% | 0.953 | 1.201 | -90.85% | 3.516 | 100.00% |
| equal_weight_top10 | Equal-weight top 10 | benchmark | holdout | 25 | -39.25% | -0.418 | -0.619 | -63.51% | 1.493 | 100.00% |
| pure_momentum | Pure momentum | benchmark | development | 25 | 44.67% | 0.877 | 1.111 | -95.13% | 19.419 | 100.00% |
| pure_momentum | Pure momentum | benchmark | holdout | 25 | -35.37% | -0.403 | -0.594 | -63.20% | 16.554 | 100.00% |
| btc_eth_macro_gate_balanced | Frozen macro gate | frozen_strategy | development | 50 | 16.73% | 0.573 | 0.543 | -74.95% | 11.088 | 49.81% |
| btc_eth_macro_gate_balanced | Frozen macro gate | frozen_strategy | holdout | 50 | 21.92% | 0.874 | 1.115 | -19.03% | 10.177 | 28.95% |
| btc_buy_hold | BTC buy-and-hold | benchmark | development | 50 | 66.95% | 1.121 | 1.493 | -76.63% | 0.000 | 100.00% |
| btc_buy_hold | BTC buy-and-hold | benchmark | holdout | 50 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | ETH buy-and-hold | benchmark | development | 50 | 91.49% | 1.202 | 1.633 | -79.30% | 0.000 | 100.00% |
| eth_buy_hold | ETH buy-and-hold | benchmark | holdout | 50 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | 50/50 BTC/ETH | benchmark | development | 50 | 83.92% | 1.222 | 1.596 | -76.25% | 0.000 | 100.00% |
| btc_eth_50_50 | 50/50 BTC/ETH | benchmark | holdout | 50 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | Equal-weight top 10 | benchmark | development | 50 | 53.19% | 0.943 | 1.188 | -90.98% | 3.516 | 100.00% |
| equal_weight_top10 | Equal-weight top 10 | benchmark | holdout | 50 | -39.48% | -0.424 | -0.627 | -63.63% | 1.493 | 100.00% |
| pure_momentum | Pure momentum | benchmark | development | 50 | 37.84% | 0.823 | 1.043 | -95.60% | 19.419 | 100.00% |
| pure_momentum | Pure momentum | benchmark | holdout | 50 | -37.99% | -0.470 | -0.693 | -64.28% | 16.554 | 100.00% |
| btc_eth_macro_gate_balanced | Frozen macro gate | frozen_strategy | development | 100 | 10.42% | 0.463 | 0.441 | -77.36% | 11.088 | 49.81% |
| btc_eth_macro_gate_balanced | Frozen macro gate | frozen_strategy | holdout | 100 | 15.85% | 0.681 | 0.871 | -20.25% | 10.177 | 28.95% |
| btc_buy_hold | BTC buy-and-hold | benchmark | development | 100 | 66.95% | 1.121 | 1.493 | -76.63% | 0.000 | 100.00% |
| btc_buy_hold | BTC buy-and-hold | benchmark | holdout | 100 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | ETH buy-and-hold | benchmark | development | 100 | 91.49% | 1.202 | 1.633 | -79.30% | 0.000 | 100.00% |
| eth_buy_hold | ETH buy-and-hold | benchmark | holdout | 100 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | 50/50 BTC/ETH | benchmark | development | 100 | 83.92% | 1.222 | 1.596 | -76.25% | 0.000 | 100.00% |
| btc_eth_50_50 | 50/50 BTC/ETH | benchmark | holdout | 100 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | Equal-weight top 10 | benchmark | development | 100 | 50.51% | 0.922 | 1.161 | -91.23% | 3.516 | 100.00% |
| equal_weight_top10 | Equal-weight top 10 | benchmark | holdout | 100 | -39.93% | -0.435 | -0.644 | -63.89% | 1.493 | 100.00% |
| pure_momentum | Pure momentum | benchmark | development | 100 | 25.11% | 0.715 | 0.907 | -96.43% | 19.419 | 100.00% |
| pure_momentum | Pure momentum | benchmark | holdout | 100 | -42.93% | -0.604 | -0.892 | -66.92% | 16.554 | 100.00% |
| best_expansion_first_strategy | prior_expansion_first | prior_expansion_first | development | 25 | 24.97% | 1.239 | 1.343 | -20.90% | 8.045 | 17.96% |
| best_expansion_first_strategy | prior_expansion_first | prior_expansion_first | holdout | 25 | 11.32% | 0.993 | 1.016 | -7.41% | 5.480 | 10.27% |
| best_expansion_first_strategy | prior_expansion_first | prior_expansion_first | development | 50 | 22.48% | 1.136 | 1.238 | -22.08% | 8.045 | 17.96% |
| best_expansion_first_strategy | prior_expansion_first | prior_expansion_first | holdout | 50 | 9.80% | 0.871 | 0.893 | -7.62% | 5.480 | 10.27% |
| best_expansion_first_strategy | prior_expansion_first | prior_expansion_first | development | 25 | 32.04% | 1.173 | 1.084 | -29.12% | 10.004 | 20.77% |
| best_expansion_first_strategy | prior_expansion_first | prior_expansion_first | holdout | 25 | 25.28% | 1.168 | 1.059 | -14.02% | 8.709 | 16.86% |
| best_expansion_first_strategy | prior_expansion_first | prior_expansion_first | development | 50 | 28.77% | 1.078 | 1.002 | -31.17% | 10.004 | 20.77% |
| best_expansion_first_strategy | prior_expansion_first | prior_expansion_first | holdout | 50 | 22.57% | 1.062 | 0.968 | -14.35% | 8.709 | 16.86% |
| best_portfolio_optimisation_candidate | prior_portfolio_optimisation | prior_portfolio_optimisation | development | 25 | 19.87% | 0.632 | 0.586 | -74.24% | 11.388 | 47.09% |
| best_portfolio_optimisation_candidate | prior_portfolio_optimisation | prior_portfolio_optimisation | holdout | 25 | 22.36% | 0.936 | 1.171 | -16.94% | 10.240 | 28.95% |
| best_portfolio_optimisation_candidate | prior_portfolio_optimisation | prior_portfolio_optimisation | development | 50 | 16.50% | 0.572 | 0.532 | -75.15% | 11.388 | 47.09% |
| best_portfolio_optimisation_candidate | prior_portfolio_optimisation | prior_portfolio_optimisation | holdout | 50 | 19.26% | 0.831 | 1.044 | -17.57% | 10.240 | 28.95% |
| ml_full_feature_alpha_7d_s+10 | rejected_full_feature_ml | rejected_full_feature_ml | development | 25 | 109.40% | 1.595 | 1.890 | -63.35% | 12.137 | 71.47% |
| ml_full_feature_alpha_7d_s+10 | rejected_full_feature_ml | rejected_full_feature_ml | holdout | 25 | -29.60% | -0.387 | -0.555 | -57.31% | 7.768 | 98.00% |
| ml_full_feature_alpha_7d_s+10 | rejected_full_feature_ml | rejected_full_feature_ml | development | 50 | 103.12% | 1.540 | 1.829 | -64.40% | 12.137 | 71.47% |
| ml_full_feature_alpha_7d_s+10 | rejected_full_feature_ml | rejected_full_feature_ml | holdout | 50 | -30.95% | -0.423 | -0.607 | -57.98% | 7.768 | 98.00% |
