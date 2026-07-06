# Universe comparison

This diagnostic asks whether broader tradable universes damage performance relative to BTC/ETH/cash macro timing.

| Strategy | Split | Cost bps | CAGR | Sharpe | Sortino | Vol | Max DD | Calmar | Turnover | Exposure | Cash | Changes | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | development | 25 | 19.19% | 0.618 | 0.575 | 48.52% | -74.09% | 0.259 | 11.185 | 47.09% | 52.91% | 118 | -43.29% |
| btc_eth_macro_gate_balanced | holdout | 25 | 25.07% | 0.970 | 1.234 | 26.61% | -18.42% | 1.361 | 10.177 | 28.95% | 71.05% | 30 | -5.98% |
| top10_macro_gated_momentum | development | 25 | -3.22% | 0.267 | 0.235 | 59.92% | -92.52% | -0.035 | 17.964 | 47.03% | 52.97% | 190 | -70.90% |
| top10_macro_gated_momentum | holdout | 25 | 2.59% | 0.226 | 0.231 | 24.72% | -20.03% | 0.129 | 13.164 | 29.06% | 70.94% | 38 | -4.72% |
| top20_macro_gated_momentum | development | 25 | 9.32% | 0.459 | 0.444 | 58.79% | -83.53% | 0.112 | 20.605 | 46.74% | 53.26% | 201 | -38.42% |
| top20_macro_gated_momentum | holdout | 25 | -4.05% | 0.021 | 0.019 | 30.87% | -26.68% | -0.152 | 14.796 | 29.16% | 70.84% | 42 | -7.26% |
| equal_weight_top10 | development | 25 | 29.96% | 0.745 | 0.941 | 83.08% | -90.85% | 0.330 | 3.455 | 100.00% | 0.00% | 91 | -54.89% |
| equal_weight_top10 | holdout | 25 | -39.25% | -0.418 | -0.619 | 66.42% | -63.51% | -0.618 | 1.493 | 100.00% | 0.00% | 11 | -28.25% |
| pure_top10_momentum | development | 25 | 19.18% | 0.656 | 0.832 | 87.90% | -95.00% | 0.202 | 18.753 | 99.91% | 0.09% | 217 | -71.49% |
| pure_top10_momentum | holdout | 25 | -35.42% | -0.407 | -0.598 | 61.41% | -63.09% | -0.561 | 15.928 | 100.00% | 0.00% | 51 | -21.94% |
| equal_weight_top20 | development | 25 | 13.88% | 0.594 | 0.744 | 85.04% | -88.39% | 0.157 | 3.390 | 100.00% | 0.00% | 156 | -41.83% |
| equal_weight_top20 | holdout | 25 | -50.49% | -0.571 | -0.835 | 74.31% | -72.72% | -0.694 | 3.121 | 100.00% | 0.00% | 42 | -29.97% |

## Interpretation

Broad-universe variants are treated as diagnostics only. They add more idiosyncratic coin risk and turnover. If they do not improve holdout Sharpe, drawdown, and CPCV stability, they do not justify changing the final project framing.
