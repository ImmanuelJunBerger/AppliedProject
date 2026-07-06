# Strategy signal diagnostics

| Experiment | Trades | Hit rate | Average win | Average loss | Turnover | Exposure | Costs |
|---|---|---|---|---|---|---|---|
| base_equal_strategy_mix | 3158 | 50.34% | 0.66% | -0.65% | 1.59% | 98.24% | 9.45% |
| ml_strategy_allocation | 4588 | 49.75% | 0.57% | -0.55% | 1.91% | 98.24% | 11.35% |
| triple_barrier_meta_labeling | 1618 | 26.38% | 0.44% | -0.41% | 0.84% | 52.73% | 5.02% |
| ml_plus_triple_barrier | 2061 | 25.96% | 0.38% | -0.34% | 0.88% | 52.73% | 5.24% |

## Allocator feature importance

| Feature | Mean absolute coefficient |
|---|---|
| strategy_drawdown__cross_sectional_momentum | 0.817 |
| market_drawdown | 0.777 |
| market_volatility_30 | 0.631 |
| market_dispersion_30 | 0.611 |
| strategy_volatility_28__trend_following | 0.611 |
| market_correlation_60 | 0.556 |
| strategy_hit_rate_28__trend_following | 0.450 |
| strategy_drawdown__defensive_cash | 0.449 |
| strategy_drawdown__trend_following | 0.433 |
| strategy_hit_rate_28__defensive_cash | 0.425 |
| strategy_drawdown__volatility_breakout | 0.390 |
| strategy_volatility_28__cross_sectional_momentum | 0.369 |
| strategy_return_28__defensive_cash | 0.368 |
| market_momentum_90 | 0.365 |
| market_breadth_30 | 0.355 |
| strategy_volatility_28__mean_reversion | 0.338 |
| strategy_hit_rate_28__cross_sectional_momentum | 0.336 |
| strategy_return_28__trend_following | 0.336 |
| strategy_hit_rate_28__volatility_breakout | 0.333 |
| strategy_return_28__cross_sectional_momentum | 0.326 |
