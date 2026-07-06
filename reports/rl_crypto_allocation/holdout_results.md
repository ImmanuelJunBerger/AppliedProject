# Locked holdout results

## Holdout comparison

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| prior_tier1_regime_momentum:u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 4.88% | 0.313 | 0.322 | -26.35% | 0.185 | 16.586 | 26.76% |
| defensive_btc_eth_cash_rule | 0.00% | 0.000 | N/A | 0.00% | 0.000 | 0.000 | 0.00% |
| rl_fitted_q_linear_btc_eth_r14_raw_return | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| prior_risk_managed_momentum:rm_mom_u20_r14_m21_k3_vol30_tv25 | -17.37% | -0.663 | -0.928 | -36.91% | -0.471 | 12.379 | 32.67% |

## Cost sensitivity for selected RL policy

| Cost bps | CAGR | Sharpe | Max DD | Annual turnover | Exposure |
|---|---|---|---|---|---|
| 10 | -35.10% | -0.239 | -67.52% | 0.000 | 100.00% |
| 25 | -35.10% | -0.239 | -67.52% | 0.000 | 100.00% |
| 50 | -35.10% | -0.239 | -67.52% | 0.000 | 100.00% |
| 100 | -35.10% | -0.239 | -67.52% | 0.000 | 100.00% |

## Acceptance

- Passes paper-trading criteria: No
- Holdout Sharpe: -0.239
- Holdout CAGR: -35.10%
- Holdout max drawdown: -67.52%
- Holdout annual turnover: 0.00x
- Failures: holdout Sharpe <= 0.5; holdout CAGR <= 0; max drawdown not better than BTC; does not survive 50 bps
