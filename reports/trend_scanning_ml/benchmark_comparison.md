# Benchmark comparison

Benchmarks are recomputed where possible from the same crypto panel.  Prior overlay rows are included only when prior reports exist.

| Name | Group | Cost bps | CAGR | Sharpe | Sortino | Max DD | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | frozen_strategy | 25 | 25.07% | 0.970 | 1.234 | -18.42% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | 25 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | 25 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | 25 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | benchmark | 25 | -50.49% | -0.571 | -0.835 | -72.72% | 3.121 | 100.00% |
| pure_top10_momentum | benchmark | 25 | -45.13% | -0.471 | -0.684 | -71.82% | 24.139 | 100.00% |
| btc_eth_macro_gate_balanced | frozen_strategy | 50 | 21.92% | 0.874 | 1.115 | -19.03% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | 50 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | 50 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | 50 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | benchmark | 50 | -50.88% | -0.581 | -0.851 | -72.93% | 3.121 | 100.00% |
| pure_top10_momentum | benchmark | 50 | -48.34% | -0.555 | -0.805 | -74.03% | 24.139 | 100.00% |
| meta_gradient_boosting_60 | prior_meta_overlay | 25 | 17.31% | 1.582 | N/A | -6.80% | 2.714 | 5.53% |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | prior_expansion_first | 25 | 11.32% | 0.993 | 1.016 | -7.41% | 5.480 | 10.27% |
| hybrid__btc_eth_only__confidence_weight__vol_target | prior_hybrid | 25 | 25.28% | 1.168 | 1.059 | -14.02% | 8.709 | 16.86% |
| trend_scanning_meta_model_biweekly | trend_scanning_meta_model | 10 | -2.95% | 0.133 | 0.178 | -37.92% | 8.311 | 63.34% |
| trend_scanning_meta_model_biweekly | trend_scanning_meta_model | 25 | -4.16% | 0.102 | 0.138 | -38.07% | 8.311 | 63.34% |
| trend_scanning_meta_model_biweekly | trend_scanning_meta_model | 50 | -6.14% | 0.052 | 0.071 | -38.30% | 8.311 | 63.34% |
| trend_scanning_meta_model_biweekly | trend_scanning_meta_model | 100 | -9.99% | -0.048 | -0.065 | -38.77% | 8.311 | 63.34% |
