# Locked holdout evaluation

Acceptance requires all of the following: Sharpe above 0.5, positive CAGR, max drawdown better than BTC buy-and-hold, positive Sharpe and CAGR at 50 bps, and annual turnover no higher than 12x.

## Finalists and benchmarks at 25 bps

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

## Cost sensitivity of development-selected family winners

| Strategy | Cost bps | CAGR | Sharpe | Max DD | Annual turnover | Exposure |
|---|---|---|---|---|---|---|
| A_market_gate_k5_dd20_vp65 | 10 | 0.00% | 0.000 | 0.00% | 0.000 | 0.00% |
| A_market_gate_k5_dd20_vp65 | 25 | 0.00% | 0.000 | 0.00% | 0.000 | 0.00% |
| A_market_gate_k5_dd20_vp65 | 50 | 0.00% | 0.000 | 0.00% | 0.000 | 0.00% |
| A_market_gate_k5_dd20_vp65 | 100 | 0.00% | 0.000 | 0.00% | 0.000 | 0.00% |
| B_defensive_rotation_dd25_vp70_vt35 | 10 | -5.38% | -0.357 | -13.99% | 5.327 | 8.41% |
| B_defensive_rotation_dd25_vp70_vt35 | 25 | -6.13% | -0.417 | -14.24% | 5.327 | 8.41% |
| B_defensive_rotation_dd25_vp70_vt35 | 50 | -7.38% | -0.517 | -15.84% | 5.327 | 8.41% |
| B_defensive_rotation_dd25_vp70_vt35 | 100 | -9.84% | -0.710 | -19.07% | 5.327 | 8.41% |
| C_cash_floor_k5_vt35_brake10 | 10 | -9.26% | -1.957 | -14.98% | 1.743 | 3.08% |
| C_cash_floor_k5_vt35_brake10 | 25 | -8.15% | -1.859 | -13.43% | 1.714 | 2.98% |
| C_cash_floor_k5_vt35_brake10 | 50 | -8.34% | -1.928 | -13.68% | 1.709 | 2.87% |
| C_cash_floor_k5_vt35_brake10 | 100 | -8.90% | -2.164 | -13.80% | 1.586 | 2.76% |
| D_btc_eth_biweekly_vt25 | 10 | -0.04% | 0.061 | -10.98% | 3.201 | 13.24% |
| D_btc_eth_biweekly_vt25 | 25 | -0.52% | 0.023 | -11.19% | 3.201 | 13.24% |
| D_btc_eth_biweekly_vt25 | 50 | -1.31% | -0.040 | -11.54% | 3.201 | 13.24% |
| D_btc_eth_biweekly_vt25 | 100 | -2.88% | -0.165 | -12.23% | 3.201 | 13.24% |

## Acceptance decisions

| Candidate | Primary | Sharpe | CAGR | Max DD | Annual turnover | Passes | Failures |
|---|---|---|---|---|---|---|---|
| A_market_gate_k5_dd20_vp65 | No | 0.000 | 0.00% | 0.00% | 0.000 | No | holdout Sharpe is not above 0.5; holdout CAGR is not positive; performance collapses at 50 bps |
| B_defensive_rotation_dd25_vp70_vt35 | No | -0.417 | -6.13% | -14.24% | 5.327 | No | holdout Sharpe is not above 0.5; holdout CAGR is not positive; performance collapses at 50 bps |
| C_cash_floor_k5_vt35_brake10 | No | -1.859 | -8.15% | -13.43% | 1.714 | No | holdout Sharpe is not above 0.5; holdout CAGR is not positive; performance collapses at 50 bps |
| D_btc_eth_biweekly_vt25 | Yes | 0.023 | -0.52% | -11.19% | 3.201 | No | holdout Sharpe is not above 0.5; holdout CAGR is not positive; performance collapses at 50 bps |
