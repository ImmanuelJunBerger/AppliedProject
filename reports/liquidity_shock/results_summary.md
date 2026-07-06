# Crypto liquidity shock and reversal/continuation strategy

## Protocol

- Development period: 2020-01-01 through 2024-12-31.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: CPCV on development returns only.
- No holdout threshold tuning and no holdout cell selection.
- Tested configurations: 144.
- Selected candidate: **volatility_shock_continuation_u20_r14_top_momentum_k5_balanced**.
- Shock lookback: 180 trailing calendar days using prior observations only.

## Selected candidate

```json
{
  "name": "volatility_shock_continuation_u20_r14_top_momentum_k5_balanced",
  "family": "volatility_shock_continuation",
  "universe_size": 20,
  "rebalance_days": 14,
  "allocation": "top_momentum",
  "top_k": 5,
  "threshold_set": "balanced",
  "max_asset_weight": 0.2,
  "turnover_cap": 0.75
}
```

## Development comparison at 25 bps

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| volatility_shock_continuation_u20_r14_top_momentum_k5_balanced | 59.44% | 1.540 | 1.322 | -17.90% | 3.321 | 7.200 | 17.69% |
| btc_eth_50_50 | 83.92% | 1.222 | 1.596 | -76.25% | 1.101 | 0.000 | 100.00% |
| eth_buy_hold | 91.49% | 1.202 | 1.633 | -79.30% | 1.154 | 0.000 | 100.00% |
| btc_buy_hold | 66.95% | 1.121 | 1.493 | -76.63% | 0.874 | 0.000 | 100.00% |
| equal_weight_top10 | 55.91% | 0.964 | 1.214 | -90.72% | 0.616 | 3.516 | 100.00% |
| pure_cross_sectional_momentum_top10 | 51.50% | 0.929 | 1.186 | -93.25% | 0.552 | 28.737 | 100.00% |

## Locked holdout comparison

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| pure_cross_sectional_momentum_top10 | -36.81% | -0.412 | -0.625 | -65.49% | -0.562 | 26.972 | 100.00% |
| equal_weight_top10 | -39.03% | -0.413 | -0.610 | -63.42% | -0.615 | 1.493 | 100.00% |
| volatility_shock_continuation_u20_r14_top_momentum_k5_balanced | -13.87% | -0.529 | -0.417 | -40.60% | -0.342 | 8.287 | 20.38% |

## Statistical controls

- Approximate PBO: 11.43%.
- Deflated Sharpe probability: 0.05%.
