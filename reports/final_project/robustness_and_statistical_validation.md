# Robustness and statistical validation

## Development vs holdout retention

| Diagnostic | Value | Classification |
|---|---:|---|
| Sharpe retention | 154.44% | Excellent |
| CAGR retention | 125.32% | Excellent |
| Drawdown change | 55.67% | less negative is better |
| Turnover change | -0.911x | lower is better |
| Exposure change | -20.86% | lower exposure may indicate defensive behaviour |

## CPCV fold distribution

| Statistic | Value |
|---|---:|
| Best fold Sharpe | 1.693 |
| Median fold Sharpe | 0.880 |
| Worst fold Sharpe | -1.147 |
| Positive CPCV folds | 73.33% |
| Holdout weekly Sharpe | 1.129 |
| Holdout percentile vs CPCV folds | 66.67% |

## PBO and deflated Sharpe

- Original macro-regime tested configurations: 8
- PBO: 61.43%
- Deflated Sharpe probability: 42.45%

These controls are material. They prevent the holdout result from being treated
as proof of live alpha.

## Simplification study

The v3 simplification study tested only four small macro gates plus the current
strategy. It did not search for unrelated strategies. Its final decision was:
**keep current strategy**.

| Candidate | Dev Sharpe | Holdout Sharpe | Retention | Dev CAGR | Holdout CAGR | Dev max DD | Holdout max DD |
|---|---|---|---|---|---|---|---|
| simple_vix_level_equity_momentum | 1.267 | -0.305 | -24.06% | 51.98% | -13.45% | -48.45% | -39.92% |
| simple_vix_change_equity_momentum | 1.125 | 0.293 | 26.07% | 54.57% | 4.34% | -70.55% | -26.33% |
| simple_equity_vol_equity_momentum | 1.500 | -0.157 | -10.49% | 72.12% | -8.93% | -49.84% | -40.08% |
| simple_vix_level_change_equity_momentum | 1.207 | 0.158 | 13.06% | 49.29% | -0.12% | -51.28% | -26.03% |
| btc_eth_macro_gate_balanced | 0.628 | 0.970 | 154.44% | 20.00% | 25.07% | -74.09% | -18.42% |

## Rolling and stress diagnostics

| Window | Median Sharpe | Worst Sharpe | Median DD | Worst DD | Median exposure | Median turnover |
|---|---|---|---|---|---|---|
| 3_month | 0.679 | -5.527 | -8.52% | -63.44% | 28.06% | 12.167 |
| 6_month | 0.751 | -3.116 | -14.86% | -67.03% | 28.19% | 11.153 |

| Stress period | Weeks | Selected CAGR | Selected Sharpe | Selected max DD | BTC mean weekly | 50/50 mean weekly |
|---|---|---|---|---|---|---|
| worst_btc_drawdown_weeks | 4 | 0.00% | N/A | 0.00% | -13.86% | -15.97% |
| high_vix_periods | 7 | 56.65% | 1.330 | -3.49% | 0.06% | -1.17% |
| rising_vix_periods | 16 | -28.09% | -2.939 | -9.65% | -3.05% | -4.16% |
| negative_equity_momentum_periods | 24 | 1.75% | 0.181 | -10.45% | -0.99% | -1.73% |
| crypto_bear_weeks | 32 | 5.62% | 0.430 | -8.09% | -1.40% | -1.85% |
