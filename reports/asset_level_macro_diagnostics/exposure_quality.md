# Exposure quality

## Exposure quality by strategy

| Strategy | Split | Return/exposure | Sharpe/exposure | Drawdown/exposure | Invested Sharpe | Positive invested weeks | Avg return invested | Avg return cash | Missed upside | Avoided downside | Exposure | Cash |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| btc_only_macro_gate | development | 38.87% | 1.302 | -159.04% | 0.799 | 0.455 | 0.001 | -0.000 | 9.364 | 8.173 | 0.471 | 52.91% |
| btc_only_macro_gate | holdout | 58.32% | 3.102 | -36.84% | 1.306 | 0.465 | 0.001 | 0.000 | 2.841 | 3.403 | 0.289 | 71.05% |
| eth_only_macro_gate | development | 36.65% | 1.227 | -162.33% | 0.767 | 0.474 | 0.002 | -0.000 | 9.364 | 8.173 | 0.471 | 52.91% |
| eth_only_macro_gate | holdout | 111.25% | 3.264 | -89.77% | 1.217 | 0.465 | 0.002 | 0.000 | 2.841 | 3.403 | 0.289 | 71.05% |
| btc_eth_50_50_macro_gate | development | 40.75% | 1.313 | -157.35% | 0.814 | 0.459 | 0.001 | -0.000 | 9.364 | 8.173 | 0.471 | 52.91% |
| btc_eth_50_50_macro_gate | holdout | 86.59% | 3.351 | -63.62% | 1.305 | 0.465 | 0.001 | 0.000 | 2.841 | 3.403 | 0.289 | 71.05% |
| btc_eth_macro_gate_balanced | development | 40.75% | 1.313 | -157.35% | 0.814 | 0.459 | 0.001 | -0.000 | 9.364 | 8.173 | 0.471 | 52.91% |
| btc_eth_macro_gate_balanced | holdout | 86.59% | 3.351 | -63.62% | 1.305 | 0.465 | 0.001 | 0.000 | 2.841 | 3.403 | 0.289 | 71.05% |
| top10_macro_gated_momentum | development | -6.85% | 0.567 | -196.72% | 0.363 | 0.483 | 0.001 | -0.000 | 9.364 | 8.173 | 0.470 | 52.97% |
| top10_macro_gated_momentum | holdout | 8.92% | 0.777 | -68.94% | 0.174 | 0.419 | 0.000 | 0.000 | 2.841 | 3.403 | 0.291 | 70.94% |
| top20_macro_gated_momentum | development | 19.95% | 0.981 | -178.74% | 0.584 | 0.469 | 0.001 | 0.000 | 9.364 | 8.173 | 0.467 | 53.26% |
| top20_macro_gated_momentum | holdout | -13.90% | 0.071 | -91.49% | -0.178 | 0.442 | -0.000 | 0.000 | 2.841 | 3.403 | 0.292 | 70.84% |
| equal_weight_top10 | development | 29.96% | 0.745 | -90.85% | 0.745 | 0.528 | 0.002 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| equal_weight_top10 | holdout | -39.25% | -0.418 | -63.51% | -0.418 | 0.513 | -0.001 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| pure_top10_momentum | development | 19.19% | 0.656 | -95.08% | 0.656 | 0.535 | 0.002 |  | 0.000 | -0.000 | 0.999 | 0.09% |
| pure_top10_momentum | holdout | -35.42% | -0.407 | -63.09% | -0.407 | 0.449 | -0.001 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| btc_buy_hold | development | 47.25% | 0.926 | -76.63% | 0.926 | 0.521 | 0.002 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| btc_buy_hold | holdout | -21.82% | -0.332 | -51.16% | -0.332 | 0.513 | -0.000 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| eth_buy_hold | development | 56.67% | 0.964 | -79.30% | 0.964 | 0.535 | 0.002 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| eth_buy_hold | holdout | -35.10% | -0.239 | -67.52% | -0.239 | 0.474 | -0.000 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| btc_eth_50_50_buy_hold | development | 56.13% | 0.992 | -76.25% | 0.992 | 0.542 | 0.002 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| btc_eth_50_50_buy_hold | holdout | -27.21% | -0.285 | -59.21% | -0.285 | 0.487 | -0.000 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| equal_weight_top20 | development | 13.88% | 0.594 | -88.39% | 0.594 | 0.535 | 0.001 |  | 0.000 | -0.000 | 1.000 | 0.00% |
| equal_weight_top20 | holdout | -50.49% | -0.571 | -72.72% | -0.571 | 0.462 | -0.001 |  | 0.000 | -0.000 | 1.000 | 0.00% |

## Current strategy return decomposition

| Split | Cash timing effect | BTC exposure effect | ETH exposure effect | BTC-vs-ETH allocation effect | Transaction-cost drag | Gross return sum | Net return sum |
|---|---|---|---|---|---|---|---|
| development | -2.072 | 0.819 | 0.983 | 0.000 | -0.154 | 1.803 | 1.649 |
| holdout | 0.654 | 0.147 | 0.270 | 0.000 | -0.038 | 0.418 | 0.380 |
