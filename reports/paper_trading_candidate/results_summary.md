# Defensive momentum paper-trading candidates

## Locked protocol

- Data: Binance daily spot data, 2019-07-05 to 2026-06-19.
- Universe: point-in-time top 30 for momentum and top 10 for the market-breadth gate.
- Selection sample: 2020-01-01 through 2024-12-31 only.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: median Sharpe across development-only CPCV folds; worst-fold Sharpe and then lower turnover break ties.
- Primary candidate frozen before holdout: **D_btc_eth_biweekly_vt25**.
- Candidate configurations tested: 28.
- No holdout result was used to select a rule, threshold, family winner, or primary candidate.

## Development results

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure | Cash | Worst month |
|---|---|---|---|---|---|---|---|---|---|
| btc_eth_50_50 | 83.92% | 1.222 | 1.596 | -76.25% | 1.101 | 0.000 | 100.00% | 0.00% | -41.05% |
| eth_buy_hold | 91.49% | 1.202 | 1.633 | -79.30% | 1.154 | 0.000 | 100.00% | 0.00% | -44.85% |
| B_defensive_rotation_dd25_vp70_vt35 | 19.80% | 1.147 | 0.933 | -19.40% | 1.021 | 6.445 | 13.47% | 86.53% | -8.22% |
| btc_buy_hold | 66.95% | 1.121 | 1.493 | -76.63% | 0.874 | 0.000 | 100.00% | 0.00% | -37.29% |
| A_market_gate_k5_dd20_vp65 | 40.24% | 1.089 | 0.595 | -32.37% | 1.243 | 5.045 | 10.87% | 89.13% | -21.46% |
| D_btc_eth_biweekly_vt25 | 17.94% | 1.010 | 0.929 | -21.99% | 0.816 | 3.707 | 16.63% | 83.37% | -8.34% |
| equal_weight_top10 | 46.74% | 0.892 | 1.116 | -90.77% | 0.515 | 3.516 | 100.00% | 0.00% | -54.68% |
| C_cash_floor_k5_vt35_brake10 | 9.65% | 0.815 | 0.868 | -21.22% | 0.455 | 3.897 | 8.58% | 91.42% | -7.09% |

## Locked holdout results

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure | Cash | Worst month |
|---|---|---|---|---|---|---|---|---|---|
| D_btc_eth_biweekly_vt25 | -0.52% | 0.023 | 0.017 | -11.19% | -0.047 | 3.201 | 13.24% | 86.76% | -7.11% |
| A_market_gate_k5_dd20_vp65 | 0.00% | 0.000 | N/A | 0.00% | 0.000 | 0.000 | 0.00% | 100.00% | 0.00% |
| eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% | 0.00% | -32.21% |
| btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% | 0.00% | -25.10% |
| btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% | 0.00% | -17.65% |
| B_defensive_rotation_dd25_vp70_vt35 | -6.13% | -0.417 | -0.262 | -14.24% | -0.431 | 5.327 | 8.41% | 91.59% | -10.15% |
| equal_weight_top10 | -40.64% | -0.452 | -0.666 | -64.05% | -0.635 | 1.628 | 100.00% | 0.00% | -28.25% |
| C_cash_floor_k5_vt35_brake10 | -8.15% | -1.859 | -1.511 | -13.43% | -0.607 | 1.714 | 2.98% | 97.02% | -2.97% |

## Decision

**3. Recommend stopping because no preselected candidate passes the criteria.** Do not paper trade these rules; return to research only with a new predeclared hypothesis.
