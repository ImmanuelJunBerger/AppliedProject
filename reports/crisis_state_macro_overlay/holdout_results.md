# Holdout results

Holdout was not used for model, threshold, or overlay selection.

## Selected crisis overlay

| Candidate | Split | Cost bps | CAGR | Sharpe | Sortino | Vol | Max DD | Turnover | Exposure | Cash | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|---|
| target_d_future_drawdown_gt_25__elastic_net_logistic|cash_if_high_and_macro_stress|0.40 | holdout | 0 | 12.20% | 0.772 | 0.731 | 16.66% | -8.17% | 8.820 | 13.66% | 86.34% | -5.67% |
| target_d_future_drawdown_gt_25__elastic_net_logistic|cash_if_high_and_macro_stress|0.40 | holdout | 10 | 11.21% | 0.719 | 0.675 | 16.66% | -8.33% | 8.820 | 13.66% | 86.34% | -5.71% |
| target_d_future_drawdown_gt_25__elastic_net_logistic|cash_if_high_and_macro_stress|0.40 | holdout | 25 | 9.75% | 0.640 | 0.606 | 16.66% | -8.64% | 8.820 | 13.66% | 86.34% | -5.78% |
| target_d_future_drawdown_gt_25__elastic_net_logistic|cash_if_high_and_macro_stress|0.40 | holdout | 50 | 7.36% | 0.507 | 0.484 | 16.67% | -9.15% | 8.820 | 13.66% | 86.34% | -5.90% |
| target_d_future_drawdown_gt_25__elastic_net_logistic|cash_if_high_and_macro_stress|0.40 | holdout | 100 | 2.71% | 0.241 | 0.234 | 16.76% | -10.17% | 8.820 | 13.66% | 86.34% | -6.14% |

## Frozen benchmark

| Candidate | Split | Cost bps | CAGR | Sharpe | Sortino | Vol | Max DD | Turnover | Exposure | Cash | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | holdout | 0 | 28.29% | 1.066 | 1.357 | 26.60% | -17.84% | 10.177 | 28.95% | 71.05% | -5.67% |
| btc_eth_macro_gate_balanced | holdout | 10 | 26.99% | 1.028 | 1.304 | 26.60% | -18.05% | 10.177 | 28.95% | 71.05% | -5.77% |
| btc_eth_macro_gate_balanced | holdout | 25 | 25.07% | 0.970 | 1.234 | 26.61% | -18.42% | 10.177 | 28.95% | 71.05% | -5.98% |
| btc_eth_macro_gate_balanced | holdout | 50 | 21.92% | 0.874 | 1.115 | 26.63% | -19.03% | 10.177 | 28.95% | 71.05% | -6.34% |
| btc_eth_macro_gate_balanced | holdout | 100 | 15.85% | 0.681 | 0.871 | 26.72% | -20.25% | 10.177 | 28.95% | 71.05% | -7.06% |
