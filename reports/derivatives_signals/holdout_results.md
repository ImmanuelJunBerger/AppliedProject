# Reused 2025–2026 evaluation results

This period is held out from fitting and CPCV tuning in this module. Because its market outcomes were already inspected in earlier projects, it is not a pristine prospective holdout for the newly designed derivatives hypotheses.

| Strategy | CAGR | Sharpe | Sortino | Max DD | Annual turnover | Exposure | Worst month |
|---|---|---|---|---|---|---|---|
| btc_eth_relative_value | -2.58% | 0.085 | 0.074 | -34.59% | 18.318 | 34.20% | -15.52% |
| price_only_trend | -7.78% | -0.159 | -0.133 | -32.29% | 14.247 | 34.20% | -14.35% |
| funding_crowding_avoidance | -7.78% | -0.159 | -0.133 | -32.29% | 14.247 | 34.20% | -14.35% |
| funding_mean_reversion | -8.09% | -0.170 | -0.145 | -32.63% | 14.926 | 34.85% | -14.35% |
| derivatives_risk_gate | -9.56% | -0.233 | -0.193 | -32.29% | 15.604 | 32.90% | -14.35% |
| eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | 0.000 | 100.00% | -32.21% |
| btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | 0.000 | 100.00% | -25.10% |
| btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | 0.000 | 100.00% | -17.65% |

## Paper-trading acceptance

| Strategy | Passes | Failures |
|---|---|---|
| price_only_trend | No | Sharpe <= 0.5; CAGR <= 0; fails at 50 bps; annual turnover > 12x |
| funding_crowding_avoidance | No | Sharpe <= 0.5; CAGR <= 0; fails at 50 bps; annual turnover > 12x |
| funding_mean_reversion | No | Sharpe <= 0.5; CAGR <= 0; fails at 50 bps; annual turnover > 12x |
| btc_eth_relative_value | No | Sharpe <= 0.5; CAGR <= 0; fails at 50 bps; annual turnover > 12x |
| derivatives_risk_gate | No | Sharpe <= 0.5; CAGR <= 0; fails at 50 bps; annual turnover > 12x |

- Tested configurations: 112.
- Approximate PBO: 95.71%.
- Deflated-Sharpe probability for the predeclared derivatives risk gate: 0.22%.
