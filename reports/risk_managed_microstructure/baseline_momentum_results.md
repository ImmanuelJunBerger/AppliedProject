# Risk-managed momentum baseline

## Protocol

- Development period: 2020-01-01 through 2024-12-31.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: CPCV on development returns only.
- No holdout threshold tuning or holdout cell selection.
- Tested baseline configurations: 216.
- Selected candidate: **rm_mom_u20_r14_m21_k3_vol30_tv25**.

```json
{
  "name": "rm_mom_u20_r14_m21_k3_vol30_tv25",
  "universe_size": 20,
  "rebalance_days": 14,
  "momentum_days": 21,
  "top_k": 3,
  "volatility_lookback": 30,
  "target_volatility": 0.25,
  "max_asset_weight": 0.5,
  "turnover_cap": 0.75
}
```

## Development comparison at 25 bps

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| rm_mom_u20_r14_m21_k3_vol30_tv25 | 36.19% | 1.260 | 1.637 | -47.18% | 0.767 | 10.273 | 28.46% |
| btc_eth_50_50 | 83.92% | 1.222 | 1.596 | -76.25% | 1.101 | 0.000 | 100.00% |
| eth_buy_hold | 91.49% | 1.202 | 1.633 | -79.30% | 1.154 | 0.000 | 100.00% |
| btc_buy_hold | 66.95% | 1.121 | 1.493 | -76.63% | 0.874 | 0.000 | 100.00% |
| equal_weight_top10 | 55.91% | 0.964 | 1.214 | -90.72% | 0.616 | 3.516 | 100.00% |
| equal_weight_top30 | 36.04% | 0.809 | 1.003 | -90.37% | 0.399 | 2.850 | 100.00% |

## Locked holdout comparison

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| equal_weight_top10 | -39.03% | -0.413 | -0.610 | -63.42% | -0.615 | 1.493 | 100.00% |
| equal_weight_top30 | -55.24% | -0.658 | -0.953 | -76.26% | -0.724 | 3.121 | 100.00% |
| rm_mom_u20_r14_m21_k3_vol30_tv25 | -17.37% | -0.663 | -0.928 | -36.91% | -0.471 | 12.379 | 32.67% |

## Cost sensitivity for selected baseline

| Cost bps | CAGR | Sharpe | Max DD | Annual turnover | Exposure |
|---|---|---|---|---|---|
| 10 | -15.82% | -0.587 | -36.23% | 12.379 | 32.67% |
| 25 | -17.37% | -0.663 | -36.91% | 12.379 | 32.67% |
| 50 | -19.89% | -0.790 | -38.98% | 12.379 | 32.67% |
| 100 | -24.72% | -1.040 | -42.93% | 12.379 | 32.67% |

## Statistical controls

- PBO: 34.29%.
- Deflated Sharpe probability: 0.02%.
