# Economic value of the fixed volatility-expansion forecast

## Locked design

- Forecast: Elastic Net, price-only, seven-day volatility-expansion probability.
- Forecast artifact SHA-256: `2c0a1cac9a32f20f71ec691c4457802109d2c42d35356d9b548b70d0a9aac46d`.
- Prediction model refit or recalibration in this study: **No**.
- Portfolio-rule selection: development-only 8-group CPCV; median Sharpe, turnover tie-break.
- Selection cost: 25 bps; cost sensitivity reuses the same frozen rules.
- Locked holdout: 2025-01-01 to 2026-06-15.
- Holdout threshold searches: 0.
- Rebalance: weekly Friday; forecast at Friday close affects subsequent returns.

## Selected development-only rules

| Portfolio | Method | Floor | Threshold | Target probability | Low | High | Low regime |
|---|---|---|---|---|---|---|---|
| breakout_risk_off_sizing | risk_off_sizing | 0.750 | 0.500 | 0.500 | 0.400 | 0.600 | trend |
| trend_risk_off_sizing | risk_off_sizing | 0.250 | 0.500 | 0.500 | 0.400 | 0.600 | trend |
| breakout_activation | breakout_activation | 1.000 | 0.500 | 0.500 | 0.400 | 0.600 | trend |
| breakout_volatility_targeted | volatility_targeted_sizing | 0.250 | 0.500 | 0.500 | 0.400 | 0.600 | trend |
| trend_volatility_targeted | volatility_targeted_sizing | 0.500 | 0.500 | 0.400 | 0.400 | 0.600 | trend |
| volatility_regime_switching | strategy_switching | 1.000 | 0.500 | 0.500 | 0.400 | 0.600 | trend |

## Development results at 25 bps

| Portfolio | Cost bps | CAGR | Sharpe | Sortino | Max drawdown | Calmar | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| btc_buy_hold | 25 | 26.04% | 0.694 | 0.983 | -76.63% | 0.340 | 0.08% | 99.92% |
| btc_eth_50_50 | 25 | 19.37% | 0.596 | 0.834 | -76.25% | 0.254 | 0.08% | 99.92% |
| equal_weight_top10 | 25 | -8.71% | 0.249 | 0.327 | -90.60% | -0.096 | 1.18% | 99.92% |
| eth_buy_hold | 25 | 9.20% | 0.475 | 0.682 | -79.30% | 0.116 | 0.08% | 99.92% |
| breakout_activation | 25 | 0.74% | 0.155 | 0.063 | -9.59% | 0.077 | 0.35% | 4.47% |
| breakout_risk_off_sizing | 25 | 10.97% | 1.127 | 1.072 | -7.70% | 1.424 | 0.81% | 11.18% |
| breakout_volatility_targeted | 25 | 11.47% | 1.161 | 1.180 | -7.66% | 1.497 | 0.81% | 11.18% |
| trend_risk_off_sizing | 25 | 3.37% | 0.258 | 0.316 | -53.84% | 0.063 | 3.50% | 72.52% |
| trend_volatility_targeted | 25 | 2.44% | 0.247 | 0.300 | -64.22% | 0.038 | 4.37% | 72.52% |
| volatility_regime_switching | 25 | 11.12% | 0.516 | 0.497 | -41.16% | 0.270 | 4.31% | 42.33% |
| standalone_trend_following | 25 | -6.00% | 0.111 | 0.133 | -78.61% | -0.076 | 4.67% | 72.52% |
| standalone_volatility_breakout | 25 | 11.40% | 1.081 | 0.958 | -8.73% | 1.305 | 0.89% | 11.18% |

## Locked holdout results at 25 bps

| Portfolio | Cost bps | CAGR | Sharpe | Sortino | Max drawdown | Calmar | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| btc_buy_hold | 25 | -21.07% | -0.308 | -0.433 | -51.16% | -0.412 | 0.00% | 100.00% |
| btc_eth_50_50 | 25 | -26.60% | -0.267 | -0.383 | -59.21% | -0.449 | 0.00% | 100.00% |
| equal_weight_top10 | 25 | -39.24% | -0.412 | -0.606 | -64.05% | -0.613 | 0.45% | 100.00% |
| eth_buy_hold | 25 | -34.69% | -0.225 | -0.336 | -67.52% | -0.514 | 0.00% | 100.00% |
| breakout_activation | 25 | -4.91% | -0.944 | -0.225 | -7.28% | -0.675 | 0.38% | 5.27% |
| breakout_risk_off_sizing | 25 | 0.39% | 0.088 | 0.058 | -9.28% | 0.042 | 1.15% | 14.50% |
| breakout_volatility_targeted | 25 | 0.92% | 0.145 | 0.105 | -9.05% | 0.101 | 1.22% | 14.50% |
| trend_risk_off_sizing | 25 | -17.05% | -0.732 | -0.769 | -28.48% | -0.599 | 2.91% | 70.24% |
| trend_volatility_targeted | 25 | -18.46% | -0.583 | -0.618 | -31.28% | -0.590 | 3.67% | 70.24% |
| volatility_regime_switching | 25 | -3.22% | -0.079 | -0.065 | -15.37% | -0.209 | 2.85% | 38.61% |
| standalone_trend_following | 25 | -32.37% | -0.825 | -0.817 | -49.17% | -0.658 | 4.15% | 70.24% |
| standalone_volatility_breakout | 25 | 0.05% | 0.053 | 0.034 | -10.82% | 0.005 | 1.28% | 14.50% |

## Answer

The volatility forecast predicts volatility well but does **not** demonstrate robust economic value under the predeclared after-cost criterion. Some overlays have higher point-estimate Sharpe (breakout_risk_off_sizing, breakout_volatility_targeted, trend_risk_off_sizing, trend_volatility_targeted), but fail the full drawdown/growth/bootstrap criterion.

Economic value requires higher Sharpe, CAGR and Calmar, no worse maximum drawdown, and a positive 95% paired block-bootstrap lower bound for Sharpe improvement versus the relevant standalone strategy.
