# Benchmark comparison

| Name | Group | Split | Cost bps | CAGR | Sharpe | Sortino | Max DD | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | frozen_strategy | holdout | 25 | 25.07% | 0.970 | 1.234 | -18.42% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | holdout | 25 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | holdout | 25 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | holdout | 25 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| btc_eth_macro_gate_balanced | frozen_strategy | holdout | 50 | 21.92% | 0.874 | 1.115 | -19.03% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | holdout | 50 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | holdout | 50 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | holdout | 50 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| meta_gradient_boosting_60 | prior_conservative_meta_overlay | holdout | 25 | 17.31% | 1.582 | N/A | -6.80% | 2.714 | 5.53% |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | prior_expansion_first_or_hybrid | holdout | 25 | 11.32% | 0.993 | 1.016 | -7.41% | 5.480 | 10.27% |
| hybrid__btc_eth_only__confidence_weight__vol_target | prior_expansion_first_or_hybrid | holdout | 25 | 25.28% | 1.168 | 1.059 | -14.02% | 8.709 | 16.86% |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | prior_expansion_first_or_hybrid | holdout | 25 | 11.32% | 0.993 | 1.016 | -7.41% | 5.480 | 10.27% |
| inverse_volatility__btc_eth__static | N/A | holdout | 10 | 24.25% | 0.998 | 1.245 | -16.56% | 10.240 | 28.95% |
| inverse_volatility__btc_eth__static | N/A | holdout | 25 | 22.36% | 0.936 | 1.171 | -16.94% | 10.240 | 28.95% |
| inverse_volatility__btc_eth__static | N/A | holdout | 50 | 19.26% | 0.831 | 1.044 | -17.57% | 10.240 | 28.95% |
| inverse_volatility__btc_eth__static | N/A | holdout | 100 | 13.28% | 0.623 | 0.784 | -18.81% | 10.240 | 28.95% |
