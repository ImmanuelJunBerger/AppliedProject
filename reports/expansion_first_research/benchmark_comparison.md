# Benchmark comparison

| Name | Group | Split | Cost bps | CAGR | Sharpe | Sortino | Max DD | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | macro_first | holdout | 25 | 25.07% | 0.970 | 1.234 | -18.42% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | holdout | 25 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | holdout | 25 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | holdout | 25 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | benchmark | holdout | 25 | -37.18% | -0.405 | -0.593 | -62.92% | 1.380 | 100.00% |
| pure_top10_momentum | benchmark | holdout | 25 | -35.37% | -0.403 | -0.594 | -63.20% | 16.554 | 100.00% |
| btc_eth_macro_gate_balanced | macro_first | holdout | 50 | 21.92% | 0.874 | 1.115 | -19.03% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | holdout | 50 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | holdout | 50 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | holdout | 50 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | benchmark | holdout | 50 | -37.40% | -0.410 | -0.600 | -63.02% | 1.380 | 100.00% |
| pure_top10_momentum | benchmark | holdout | 50 | -37.99% | -0.470 | -0.693 | -64.28% | 16.554 | 100.00% |
| meta_gradient_boosting_60 | prior_conservative_meta_overlay | holdout | 25 | 17.31% | 1.582 | N/A | -6.80% | 2.714 | 5.53% |
| expansion_filter_t60_14d | prior_expansion_diagnostics_overlay | holdout | 25 | 5.65% | 0.894 | 0.779 | -5.16% | 2.035 | 4.55% |
| expansion_filter_t60_14d | prior_expansion_diagnostics_overlay | holdout | 50 | 5.12% | 0.812 | 0.718 | -5.34% | 2.035 | 4.55% |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | expansion_first | holdout | 10 | 12.24% | 1.066 | 1.087 | -7.29% | 5.480 | 10.27% |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | expansion_first | holdout | 25 | 11.32% | 0.993 | 1.016 | -7.41% | 5.480 | 10.27% |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | expansion_first | holdout | 50 | 9.80% | 0.871 | 0.893 | -7.62% | 5.480 | 10.27% |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | expansion_first | holdout | 100 | 6.82% | 0.628 | 0.644 | -8.03% | 5.480 | 10.27% |
| hybrid__btc_eth_only__confidence_weight__vol_target | hybrid | holdout | 10 | 26.94% | 1.231 | 1.114 | -13.82% | 8.709 | 16.86% |
| hybrid__btc_eth_only__confidence_weight__vol_target | hybrid | holdout | 25 | 25.28% | 1.168 | 1.059 | -14.02% | 8.709 | 16.86% |
| hybrid__btc_eth_only__confidence_weight__vol_target | hybrid | holdout | 50 | 22.57% | 1.062 | 0.968 | -14.35% | 8.709 | 16.86% |
| hybrid__btc_eth_only__confidence_weight__vol_target | hybrid | holdout | 100 | 17.30% | 0.850 | 0.778 | -15.00% | 8.709 | 16.86% |
