# Benchmark comparison

Benchmarks include the frozen strategy, simple crypto beta, equal-weight top 10,
and prior modules where report artifacts are available.

| Name | Group | Cost bps | CAGR | Sharpe | Sortino | Max DD | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | frozen_strategy | 25 | 25.07% | 0.970 | 1.234 | -18.42% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | 25 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | 25 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | 25 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | benchmark | 25 | -39.25% | -0.418 | -0.619 | -63.51% | 1.493 | 100.00% |
| btc_eth_macro_gate_balanced | frozen_strategy | 50 | 21.92% | 0.874 | 1.115 | -19.03% | 10.177 | 28.95% |
| btc_buy_hold | benchmark | 50 | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% |
| eth_buy_hold | benchmark | 50 | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% |
| btc_eth_50_50 | benchmark | 50 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% |
| equal_weight_top10 | benchmark | 50 | -39.48% | -0.424 | -0.627 | -63.63% | 1.493 | 100.00% |
| meta_gradient_boosting_60 | prior_conservative_meta_overlay | 25 | 17.31% | 1.582 | N/A | -6.80% | 2.714 | 5.53% |
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | prior_tier1_regime_momentum | 25 | 4.88% | 0.313 | 0.322 | -26.35% | 16.586 | 26.76% |
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | prior_tier1_regime_momentum | 50 | 0.61% | 0.155 | 0.160 | -27.86% | 16.586 | 26.76% |
| expansion_filter_t60_14d | expansion_threshold_filter | 10 | 5.98% | 0.943 | 0.814 | -5.06% | 2.035 | 4.55% |
| expansion_filter_t60_14d | expansion_threshold_filter | 25 | 5.65% | 0.894 | 0.779 | -5.16% | 2.035 | 4.55% |
| expansion_filter_t60_14d | expansion_threshold_filter | 50 | 5.12% | 0.812 | 0.718 | -5.34% | 2.035 | 4.55% |
| expansion_filter_t60_14d | expansion_threshold_filter | 100 | 4.05% | 0.649 | 0.586 | -5.83% | 2.035 | 4.55% |
