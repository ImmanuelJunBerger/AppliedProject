# Benchmark comparison

| Name | Group | Cost bps | CAGR | Sharpe | Sortino | Max DD | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | frozen_strategy | 25 | 25.07% | 0.970 | 1.234 | -18.42% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | 25 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | 25 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | 25 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| btc_eth_macro_gate_balanced | frozen_strategy | 50 | 21.92% | 0.874 | 1.115 | -19.03% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | 50 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | 50 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | 50 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| meta_gradient_boosting_60 | prior_conservative_meta_overlay | 25 | 17.31% | 1.582 | N/A | -6.80% | 2.714 | 5.53% |
| expansion_filter_t60_14d | prior_expansion_diagnostics_overlay | 25 | 5.65% | 0.894 | 0.779 | -5.16% | 2.035 | 4.55% |
| expansion_filter_t60_14d | prior_expansion_diagnostics_overlay | 50 | 5.12% | 0.812 | 0.718 | -5.34% | 2.035 | 4.55% |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 10 | 15.54% | 0.817 | 0.939 | -17.74% | 8.141 | 23.42% |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 25 | 14.14% | 0.756 | 0.872 | -18.05% | 8.141 | 23.42% |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 50 | 11.84% | 0.655 | 0.759 | -18.57% | 8.141 | 23.42% |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 100 | 7.36% | 0.451 | 0.527 | -19.59% | 8.141 | 23.42% |
