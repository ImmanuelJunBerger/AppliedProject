# Triple-barrier meta-labeling results

Profit-taking is 1.5 times trailing daily volatility, stop-loss is 1.0 times volatility, and the vertical barrier is 14 days. Barrier labels are only admitted to training after `label_end`; live features are lagged.

- Rejected trades: 67.98%
- Meta-model confidence: {"count": 7101, "mean": 0.4831875953008654, "p10": 0.2921762303817016, "p25": 0.38064800706184615, "median": 0.4771252773311713, "p75": 0.5910402934846382, "p90": 0.695207050332802}

| Strategy | Events | Positive labels | Average barrier return |
|---|---|---|---|
| cross_sectional_momentum | 2059 | 39.05% | -0.24% |
| defensive_cash | 2180 | 37.43% | -0.43% |
| mean_reversion | 503 | 39.36% | -0.36% |
| trend_following | 2601 | 39.25% | -0.18% |
| volatility_breakout | 142 | 47.89% | 0.88% |

## Experiment comparison

| Experiment | CAGR | Sharpe | Max DD | Turnover |
|---|---|---|---|---|
| base_equal_strategy_mix | 5.29% | 0.354 | -42.41% | 1.59% |
| ml_strategy_allocation | 3.04% | 0.252 | -45.72% | 1.91% |
| triple_barrier_meta_labeling | 1.72% | 0.210 | -23.89% | 0.84% |
| ml_plus_triple_barrier | 0.98% | 0.145 | -23.97% | 0.88% |
| BTC_buy_and_hold | 40.10% | 0.864 | -76.63% | 0.00% |
| ETH_buy_and_hold | 46.63% | 0.884 | -79.30% | 0.00% |
| 50_50_BTC_ETH | 47.20% | 0.916 | -76.25% | 0.00% |
| equal_weight_top_20 | 0.53% | 0.440 | -93.15% | 1.15% |
| standalone_trend_following | 9.21% | 0.449 | -53.17% | 2.25% |
| standalone_cross_sectional_momentum | 1.21% | 0.181 | -61.26% | 1.76% |
| standalone_mean_reversion | -2.99% | -0.198 | -24.80% | 1.81% |
| standalone_volatility_breakout | 5.38% | 1.020 | -6.99% | 0.52% |
| standalone_defensive_cash | -2.15% | 0.101 | -68.35% | 2.68% |
| equal_weight_strategy_mix | 5.29% | 0.354 | -42.41% | 1.59% |
