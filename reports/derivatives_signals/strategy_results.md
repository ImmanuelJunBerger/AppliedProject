# Predeclared derivatives strategy results

No strategy or threshold was selected using holdout performance. OI-dependent strategies remain unavailable rather than being approximated.

## Availability

| Strategy | Available | Reason |
|---|---|---|
| price_only_trend | Yes | available |
| funding_crowding_avoidance | Yes | available |
| funding_mean_reversion | Yes | available |
| oi_confirmed_trend | No | Open-interest history has insufficient development coverage. |
| oi_divergence_risk_off | No | Open-interest history has insufficient development coverage. |
| btc_eth_relative_value | Yes | available |
| derivatives_risk_gate | Yes | available |
| btc_buy_hold | Yes | benchmark |
| eth_buy_hold | Yes | benchmark |
| btc_eth_50_50 | Yes | benchmark |

## Development at 25 bps

| Strategy | CAGR | Sharpe | Sortino | Max DD | Annual turnover | Exposure | Worst month |
|---|---|---|---|---|---|---|---|
| funding_crowding_avoidance | 39.57% | 0.909 | 0.873 | -49.77% | 12.991 | 45.86% | -14.36% |
| btc_eth_relative_value | 42.72% | 0.909 | 0.954 | -53.33% | 19.986 | 48.73% | -14.83% |
| price_only_trend | 39.80% | 0.902 | 0.892 | -49.77% | 10.992 | 48.73% | -12.74% |
| funding_mean_reversion | 39.00% | 0.891 | 0.887 | -49.77% | 11.742 | 48.49% | -14.66% |
| btc_eth_50_50 | 43.64% | 0.875 | 1.218 | -76.25% | 0.000 | 100.00% | -41.05% |
| eth_buy_hold | 45.87% | 0.872 | 1.242 | -79.30% | 0.000 | 100.00% | -44.85% |
| derivatives_risk_gate | 31.86% | 0.811 | 0.728 | -49.77% | 14.740 | 40.11% | -14.36% |
| btc_buy_hold | 34.09% | 0.782 | 1.125 | -76.63% | 0.000 | 100.00% | -37.29% |

## Cost sensitivity

| Strategy | Split | Cost bps | CAGR | Sharpe | Max DD | Annual turnover |
|---|---|---|---|---|---|---|
| btc_eth_relative_value | development | 10 | 47.09% | 0.962 | -51.28% | 19.986 |
| btc_eth_relative_value | development | 25 | 42.72% | 0.909 | -53.33% | 19.986 |
| btc_eth_relative_value | development | 50 | 35.71% | 0.820 | -56.77% | 19.986 |
| btc_eth_relative_value | development | 100 | 22.63% | 0.641 | -64.50% | 19.986 |
| btc_eth_relative_value | holdout | 10 | 0.15% | 0.168 | -33.70% | 18.318 |
| btc_eth_relative_value | holdout | 25 | -2.58% | 0.085 | -34.59% | 18.318 |
| btc_eth_relative_value | holdout | 50 | -6.98% | -0.053 | -36.05% | 18.318 |
| btc_eth_relative_value | holdout | 100 | -15.24% | -0.326 | -38.88% | 18.318 |
| derivatives_risk_gate | development | 10 | 34.82% | 0.856 | -49.77% | 14.740 |
| derivatives_risk_gate | development | 25 | 31.86% | 0.811 | -49.77% | 14.740 |
| derivatives_risk_gate | development | 50 | 27.07% | 0.735 | -49.77% | 14.740 |
| derivatives_risk_gate | development | 100 | 17.96% | 0.583 | -55.50% | 14.740 |
| derivatives_risk_gate | holdout | 10 | -7.42% | -0.147 | -31.38% | 15.604 |
| derivatives_risk_gate | holdout | 25 | -9.56% | -0.233 | -32.29% | 15.604 |
| derivatives_risk_gate | holdout | 50 | -13.01% | -0.376 | -33.78% | 15.604 |
| derivatives_risk_gate | holdout | 100 | -19.56% | -0.662 | -36.68% | 15.604 |
| funding_crowding_avoidance | development | 10 | 42.32% | 0.948 | -49.77% | 12.991 |
| funding_crowding_avoidance | development | 25 | 39.57% | 0.909 | -49.77% | 12.991 |
| funding_crowding_avoidance | development | 50 | 35.09% | 0.845 | -50.16% | 12.991 |
| funding_crowding_avoidance | development | 100 | 26.52% | 0.716 | -60.10% | 12.991 |
| funding_crowding_avoidance | holdout | 10 | -5.79% | -0.081 | -31.38% | 14.247 |
| funding_crowding_avoidance | holdout | 25 | -7.78% | -0.159 | -32.29% | 14.247 |
| funding_crowding_avoidance | holdout | 50 | -11.00% | -0.290 | -33.78% | 14.247 |
| funding_crowding_avoidance | holdout | 100 | -17.14% | -0.549 | -36.68% | 14.247 |
| funding_mean_reversion | development | 10 | 41.48% | 0.925 | -49.77% | 11.742 |
| funding_mean_reversion | development | 25 | 39.00% | 0.891 | -49.77% | 11.742 |
| funding_mean_reversion | development | 50 | 34.95% | 0.834 | -49.77% | 11.742 |
| funding_mean_reversion | development | 100 | 27.17% | 0.721 | -57.96% | 11.742 |
| funding_mean_reversion | holdout | 10 | -6.02% | -0.088 | -31.62% | 14.926 |
| funding_mean_reversion | holdout | 25 | -8.09% | -0.170 | -32.63% | 14.926 |
| funding_mean_reversion | holdout | 50 | -11.46% | -0.306 | -34.28% | 14.926 |
| funding_mean_reversion | holdout | 100 | -17.84% | -0.577 | -37.47% | 14.926 |
| price_only_trend | development | 10 | 42.13% | 0.934 | -49.77% | 10.992 |
| price_only_trend | development | 25 | 39.80% | 0.902 | -49.77% | 10.992 |
| price_only_trend | development | 50 | 35.98% | 0.849 | -49.77% | 10.992 |
| price_only_trend | development | 100 | 28.63% | 0.742 | -55.99% | 10.992 |
| price_only_trend | holdout | 10 | -5.79% | -0.081 | -31.38% | 14.247 |
| price_only_trend | holdout | 25 | -7.78% | -0.159 | -32.29% | 14.247 |
| price_only_trend | holdout | 50 | -11.00% | -0.290 | -33.78% | 14.247 |
| price_only_trend | holdout | 100 | -17.14% | -0.549 | -36.68% | 14.247 |
