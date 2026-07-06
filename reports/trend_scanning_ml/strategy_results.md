# Strategy results

Strategy candidates were selected by development-only CPCV using median fold Sharpe, worst-fold Sharpe, positive fold rate, turnover, and simplicity.

## CPCV selection

| Candidate | Family | Rebalance days | Selection score | Median fold Sharpe | Worst fold | Positive folds | Dev Sharpe | Dev CAGR | Dev turnover | Dev exposure |
|---|---|---|---|---|---|---|---|---|---|---|
| trend_scanning_meta_model_biweekly | trend_scanning_meta_model | 14 | 1.696 | 1.367 | 0.278 | 100.00% | 1.293 | 68.97% | 5.274 | 69.83% |
| trend_scanning_meta_model_weekly | trend_scanning_meta_model | 7 | 1.562 | 1.236 | 0.264 | 100.00% | 1.189 | 60.10% | 8.366 | 67.65% |
| pure_trend_scanning_biweekly | pure_trend_scanning | 14 | 1.252 | 0.977 | -0.085 | 93.33% | 0.975 | 46.84% | 4.910 | 74.89% |
| pure_trend_scanning_weekly | pure_trend_scanning | 7 | 1.157 | 0.867 | -0.027 | 93.33% | 0.851 | 37.24% | 6.911 | 75.24% |
| relative_btc_eth_trend_biweekly | relative_btc_eth_trend | 14 | 1.002 | 0.858 | -0.397 | 86.67% | 0.972 | 54.70% | 5.801 | 97.04% |
| relative_btc_eth_trend_weekly | relative_btc_eth_trend | 7 | 0.975 | 0.816 | -0.339 | 86.67% | 0.985 | 56.16% | 8.584 | 96.51% |
| macro_gate_trend_confirmation_weekly | macro_gate_trend_confirmation | 7 | 0.938 | 0.781 | -0.254 | 80.00% | 0.640 | 18.29% | 9.730 | 36.36% |
| trend_first_macro_overlay_weekly | trend_first_macro_overlay | 7 | 0.938 | 0.781 | -0.254 | 80.00% | 0.640 | 18.29% | 9.730 | 36.36% |
| macro_gate_trend_confirmation_biweekly | macro_gate_trend_confirmation | 14 | 0.839 | 0.778 | -0.540 | 73.33% | 0.789 | 24.89% | 6.092 | 36.62% |
| trend_first_macro_overlay_biweekly | trend_first_macro_overlay | 14 | 0.839 | 0.778 | -0.540 | 73.33% | 0.789 | 24.89% | 6.092 | 36.62% |

## Selected candidate holdout cost sensitivity

| Cost bps | CAGR | Sharpe | Sortino | Calmar | Max DD | Turnover | Exposure | Worst month |
|---|---|---|---|---|---|---|---|---|
| 10 | -2.95% | 0.133 | 0.178 | -0.078 | -37.92% | 8.311 | 63.34% | -16.05% |
| 25 | -4.16% | 0.102 | 0.138 | -0.109 | -38.07% | 8.311 | 63.34% | -16.15% |
| 50 | -6.14% | 0.052 | 0.071 | -0.160 | -38.30% | 8.311 | 63.34% | -16.31% |
| 100 | -9.99% | -0.048 | -0.065 | -0.258 | -38.77% | 8.311 | 63.34% | -16.64% |

## Selected holdout decision frequencies

| Decision | Frequency |
|---|---|
| meta_take | 57.89% |
| cash | 34.21% |
| meta_reduce | 5.26% |
| meta_skip | 2.63% |

## Incremental contribution

| Split | Frozen total return | Selected total return | Incremental total return |
|---|---|---|---|
| development | 162.52% | 1688.86% | 1526.34% |
| holdout | 39.06% | -6.07% | -45.12% |
