# Regime diagnostics

## Regime state performance

| Split | Layer | State | Days | Fraction days | Mean daily return | Sharpe | Exposure |
|---|---|---|---|---|---|---|---|
| development | macro | neutral | 474.000 | 25.94% | -0.08% | -0.518 | 45.73% |
| development | macro | risk_off | 695.000 | 38.04% | 0.02% | 0.377 | 14.21% |
| development | macro | risk_on | 658.000 | 36.02% | 0.28% | 1.595 | 90.35% |
| development | crypto | not_used | 1827.000 | 100.00% | 0.09% | 0.628 | 49.81% |
| development | combined | neutral | 474.000 | 25.94% | -0.08% | -0.518 | 45.73% |
| development | combined | risk_off | 695.000 | 38.04% | 0.02% | 0.377 | 14.21% |
| development | combined | risk_on | 658.000 | 36.02% | 0.28% | 1.595 | 90.35% |
| holdout | macro | neutral | 133.000 | 24.72% | -0.07% | -0.872 | 37.22% |
| holdout | macro | risk_off | 311.000 | 57.81% | 0.03% | 0.672 | 11.82% |
| holdout | macro | risk_on | 94.000 | 17.47% | 0.39% | 3.207 | 73.94% |
| holdout | crypto | not_used | 538.000 | 100.00% | 0.07% | 0.970 | 28.95% |
| holdout | combined | neutral | 133.000 | 24.72% | -0.07% | -0.872 | 37.22% |
| holdout | combined | risk_off | 311.000 | 57.81% | 0.03% | 0.672 | 11.82% |
| holdout | combined | risk_on | 94.000 | 17.47% | 0.39% | 3.207 | 73.94% |

## Feature coverage

| Feature tier | Feature | Coverage |
|---|---|---|
| Tier 1 macro | equity_realized_vol_21d | 99.60% |
| Tier 1 macro | equity_momentum_21d | 99.16% |
| Tier 1 macro | dow_vol_level | 99.93% |
| Tier 1 macro | vix_level | 99.93% |
| Tier 1 macro | vix_change_5d | 99.74% |
| Tier 1 macro | vix_change_21d | 99.16% |
| Tier 1 crypto-native | stablecoin_supply_change_7d | 99.96% |
| Tier 1 crypto-native | tvl_growth_30d | 99.96% |
| Tier 1 crypto-native | volatility_expansion_probability | 65.53% |
| Tier 1 crypto-native | cross_sectional_dispersion | 92.27% |
