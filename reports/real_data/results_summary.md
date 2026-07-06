# Real-data results summary

## Dataset

- Source: Binance spot USDT OHLCV through ccxt
- Coverage: 2019-01-01 to 2026-06-22
- Assets: 415
- Observations: 524,164
- Full-panel missingness: 53.73%
- Within-listing-span missingness: 0.09%

## Main comparison

All portfolios are long-only, rebalanced weekly, volatility-scaled, subject to asset/strategy caps and a turnover cap, and charged 25 bps on underlying asset turnover.

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

## Robustness tests

| Dimension | Case | CAGR | Sharpe | Max DD |
|---|---|---|---|---|
| universe | 20 | 0.98% | 0.145 | -23.97% |
| universe | 10 | 5.09% | 0.491 | -19.88% |
| universe | 50 | 1.55% | 0.200 | -17.02% |
| frequency | W-FRI | 0.98% | 0.145 | -23.97% |
| frequency | 2W-FRI | 0.71% | 0.122 | -25.82% |
| frequency | ME | -0.32% | 0.014 | -18.18% |
| cost | 10 | 1.47% | 0.190 | -23.04% |
| cost | 25 | 0.98% | 0.145 | -23.97% |
| cost | 50 | 0.18% | 0.070 | -25.96% |
| cost | 100 | -1.42% | -0.078 | -30.49% |
| feature_ablation | all_features | 0.98% | 0.145 | -23.97% |
| feature_ablation | without_market_state | 1.42% | 0.185 | -26.58% |
| feature_ablation | without_strategy_health | 3.92% | 0.366 | -29.80% |
| strategy_ablation | without_trend_following | 0.81% | 0.133 | -22.47% |
| strategy_ablation | without_cross_sectional_momentum | 0.16% | 0.066 | -27.43% |
| strategy_ablation | without_mean_reversion | 3.50% | 0.338 | -29.18% |
| strategy_ablation | without_volatility_breakout | 0.87% | 0.132 | -30.27% |
| strategy_ablation | without_defensive_cash | 1.54% | 0.202 | -22.83% |

## Conclusion

The combined ML and triple-barrier system did not improve both CAGR and Sharpe over the base signal mix; the evidence does not support claiming ML value-add.
