# Risk-aware reinforcement learning for crypto allocation

## Protocol

- Development period: 2020-01-01 through 2024-12-31.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: CPCV inside development only.
- No holdout tuning and no holdout cell selection.
- Tested configurations: 40.
- Selected candidate: **rl_fitted_q_linear_btc_eth_r14_raw_return**.
- Policy kind: `fitted_q_linear`.
- DQN/PPO status: not_run; simple tabular/fitted-Q baselines are tested first.
- Stable-Baselines3 available: No.

## Selected candidate

```json
{
  "name": "rl_fitted_q_linear_btc_eth_r14_raw_return",
  "universe": "btc_eth",
  "rebalance_days": 14,
  "model": "fitted_q_linear",
  "reward": "raw_return",
  "gamma": 0.8,
  "episodes_or_iterations": 4,
  "cost_bps_train": 25
}
```

## Development comparison at 25 bps

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| btc_eth_50_50 | 83.92% | 1.222 | 1.596 | -76.25% | 1.101 | 0.000 | 100.00% |
| eth_buy_hold | 91.49% | 1.202 | 1.633 | -79.30% | 1.154 | 0.000 | 100.00% |
| rl_fitted_q_linear_btc_eth_r14_raw_return | 90.03% | 1.193 | 1.620 | -79.30% | 1.135 | 0.200 | 100.00% |
| btc_buy_hold | 66.95% | 1.121 | 1.493 | -76.63% | 0.874 | 0.000 | 100.00% |
| defensive_btc_eth_cash_rule | 34.54% | 0.951 | 0.635 | -48.23% | 0.716 | 2.397 | 22.99% |

## Locked holdout comparison

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| prior_tier1_regime_momentum:u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 4.88% | 0.313 | 0.322 | -26.35% | 0.185 | 16.586 | 26.76% |
| defensive_btc_eth_cash_rule | 0.00% | 0.000 | N/A | 0.00% | 0.000 | 0.000 | 0.00% |
| rl_fitted_q_linear_btc_eth_r14_raw_return | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| prior_risk_managed_momentum:rm_mom_u20_r14_m21_k3_vol30_tv25 | -17.37% | -0.663 | -0.928 | -36.91% | -0.471 | 12.379 | 32.67% |

## Statistical controls

- Approximate PBO: 0.00%.
- Deflated Sharpe probability: 0.66%.
