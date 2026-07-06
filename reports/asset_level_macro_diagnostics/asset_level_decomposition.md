# Asset-level decomposition

This section compares frozen, non-tuned decompositions using the same macro gate where possible.

## Development and holdout metrics

| Strategy | Split | Cost bps | CAGR | Sharpe | Sortino | Vol | Max DD | Calmar | Turnover | Exposure | Cash | Changes | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| btc_only_macro_gate | development | 0 | 21.65% | 0.676 | 0.627 | 44.07% | -73.46% | 0.295 | 11.185 | 47.09% | 52.91% | 118 | -38.31% |
| btc_only_macro_gate | holdout | 0 | 19.90% | 1.030 | 1.254 | 19.43% | -9.61% | 2.070 | 10.177 | 28.95% | 71.05% | 30 | -2.37% |
| btc_only_macro_gate | development | 25 | 18.30% | 0.613 | 0.578 | 44.06% | -74.88% | 0.244 | 11.185 | 47.09% | 52.91% | 118 | -38.46% |
| btc_only_macro_gate | holdout | 25 | 16.88% | 0.898 | 1.090 | 19.46% | -10.67% | 1.583 | 10.177 | 28.95% | 71.05% | 30 | -2.50% |
| eth_only_macro_gate | development | 0 | 20.57% | 0.627 | 0.600 | 57.08% | -75.88% | 0.271 | 11.185 | 47.09% | 52.91% | 118 | -47.79% |
| eth_only_macro_gate | holdout | 0 | 35.61% | 1.015 | 1.369 | 36.15% | -25.57% | 1.393 | 10.177 | 28.95% | 71.05% | 30 | -9.10% |
| eth_only_macro_gate | development | 25 | 17.25% | 0.578 | 0.562 | 57.07% | -76.43% | 0.226 | 11.185 | 47.09% | 52.91% | 118 | -47.91% |
| eth_only_macro_gate | holdout | 25 | 32.21% | 0.945 | 1.275 | 36.15% | -25.99% | 1.239 | 10.177 | 28.95% | 71.05% | 30 | -9.45% |
| btc_eth_50_50_macro_gate | development | 0 | 22.56% | 0.676 | 0.618 | 48.53% | -73.20% | 0.308 | 11.185 | 47.09% | 52.91% | 118 | -43.15% |
| btc_eth_50_50_macro_gate | holdout | 0 | 28.29% | 1.066 | 1.357 | 26.60% | -17.84% | 1.586 | 10.177 | 28.95% | 71.05% | 30 | -5.67% |
| btc_eth_50_50_macro_gate | development | 25 | 19.19% | 0.618 | 0.575 | 48.52% | -74.09% | 0.259 | 11.185 | 47.09% | 52.91% | 118 | -43.29% |
| btc_eth_50_50_macro_gate | holdout | 25 | 25.07% | 0.970 | 1.234 | 26.61% | -18.42% | 1.361 | 10.177 | 28.95% | 71.05% | 30 | -5.98% |
| btc_eth_macro_gate_balanced | development | 0 | 22.56% | 0.676 | 0.618 | 48.53% | -73.20% | 0.308 | 11.185 | 47.09% | 52.91% | 118 | -43.15% |
| btc_eth_macro_gate_balanced | holdout | 0 | 28.29% | 1.066 | 1.357 | 26.60% | -17.84% | 1.586 | 10.177 | 28.95% | 71.05% | 30 | -5.67% |
| btc_eth_macro_gate_balanced | development | 25 | 19.19% | 0.618 | 0.575 | 48.52% | -74.09% | 0.259 | 11.185 | 47.09% | 52.91% | 118 | -43.29% |
| btc_eth_macro_gate_balanced | holdout | 25 | 25.07% | 0.970 | 1.234 | 26.61% | -18.42% | 1.361 | 10.177 | 28.95% | 71.05% | 30 | -5.98% |

## CPCV summary at 25 bps

| Strategy | Cost bps | Median fold Sharpe | Best fold Sharpe | Worst fold Sharpe | Positive folds |
|---|---|---|---|---|---|
| btc_eth_50_50_macro_gate | 25 | 0.419 | 2.194 | -0.594 | 60.00% |
| btc_eth_macro_gate_balanced | 25 | 0.419 | 2.194 | -0.594 | 60.00% |
| btc_only_macro_gate | 25 | 0.481 | 2.085 | -0.754 | 66.67% |
| eth_only_macro_gate | 25 | 0.340 | 2.003 | -0.483 | 60.00% |

## Statistical diagnostics

| Strategy | PBO context | DSR probability | Sharpe CI low | Sharpe CI mid | Sharpe CI high | Sharpe delta vs frozen |
|---|---|---|---|---|---|---|
| btc_only_macro_gate | 45.71% | 29.84% | -0.445 | 0.887 | 2.042 | -0.030 |
| eth_only_macro_gate | 45.71% | 34.30% | -0.575 | 0.936 | 2.127 | -0.047 |
| btc_eth_50_50_macro_gate | 45.71% | 34.60% | -0.472 | 0.968 | 2.157 | 0.000 |
| btc_eth_macro_gate_balanced | 45.71% | 34.60% | -0.472 | 0.968 | 2.157 | 0.000 |
