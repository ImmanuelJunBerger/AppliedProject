# Benchmark comparison

| Candidate | Split | Cost bps | CAGR | Sharpe | Sortino | Vol | Max DD | Turnover | Exposure | Cash | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | development | 25 | 19.19% | 0.618 | 0.575 | 48.52% | -74.09% | 11.185 | 47.09% | 52.91% | -43.29% |
| btc_eth_macro_gate_balanced | holdout | 25 | 25.07% | 0.970 | 1.234 | 26.61% | -18.42% | 10.177 | 28.95% | 71.05% | -5.98% |
| target_d_future_drawdown_gt_25__elastic_net_logistic|cash_if_high_and_macro_stress|0.40 | development | 25 | 33.09% | 1.178 | 1.013 | 27.47% | -49.23% | 10.093 | 25.55% | 74.45% | -18.29% |
| target_d_future_drawdown_gt_25__elastic_net_logistic|cash_if_high_and_macro_stress|0.40 | holdout | 25 | 9.75% | 0.640 | 0.606 | 16.66% | -8.64% | 8.820 | 13.66% | 86.34% | -5.78% |
| btc_only_macro_gate | development | 25 | 18.30% | 0.613 | 0.578 | 44.06% | -74.88% | 11.185 | 47.09% | 52.91% | -38.46% |
| btc_only_macro_gate | holdout | 25 | 16.88% | 0.898 | 1.090 | 19.46% | -10.67% | 10.177 | 28.95% | 71.05% | -2.50% |
| eth_only_macro_gate | development | 25 | 17.25% | 0.578 | 0.562 | 57.07% | -76.43% | 11.185 | 47.09% | 52.91% | -47.91% |
| eth_only_macro_gate | holdout | 25 | 32.21% | 0.945 | 1.275 | 36.15% | -25.99% | 10.177 | 28.95% | 71.05% | -9.45% |
| btc_eth_50_50_macro_gate | development | 25 | 19.19% | 0.618 | 0.575 | 48.52% | -74.09% | 11.185 | 47.09% | 52.91% | -43.29% |
| btc_eth_50_50_macro_gate | holdout | 25 | 25.07% | 0.970 | 1.234 | 26.61% | -18.42% | 10.177 | 28.95% | 71.05% | -5.98% |
| btc_buy_hold | development | 25 | 47.25% | 0.926 | 1.245 | 65.22% | -76.63% | 0.000 | 100.00% | 0.00% | -37.29% |
| btc_buy_hold | holdout | 25 | -21.82% | -0.332 | -0.468 | 44.40% | -51.16% | 0.000 | 100.00% | 0.00% | -17.65% |
| eth_buy_hold | development | 25 | 56.67% | 0.964 | 1.304 | 83.49% | -79.30% | 0.000 | 100.00% | 0.00% | -44.85% |
| eth_buy_hold | holdout | 25 | -35.10% | -0.239 | -0.356 | 72.33% | -67.52% | 0.000 | 100.00% | 0.00% | -32.21% |
| btc_eth_50_50_buy_hold | development | 25 | 56.13% | 0.992 | 1.296 | 71.00% | -76.25% | 0.000 | 100.00% | 0.00% | -41.05% |
| btc_eth_50_50_buy_hold | holdout | 25 | -27.21% | -0.285 | -0.410 | 56.17% | -59.21% | 0.000 | 100.00% | 0.00% | -25.10% |
| drawdown_brake_candidate | development | 25 | 24.29% | 0.884 | 0.887 | 29.56% | -49.42% | 4.547 | 29.30% | 70.70% | -22.08% |
| drawdown_brake_candidate | holdout | 25 | 12.91% | 0.926 | 1.086 | 14.18% | -13.77% | 4.410 | 15.61% | 84.39% | -6.78% |
