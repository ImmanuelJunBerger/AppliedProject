# Robustness

This table summarizes all predeclared configurations. It is diagnostic only;
the selected strategy was chosen by development CPCV, not by holdout cells.

## Summary by universe and rebalance cadence

| Universe | Rebalance days | Configs | Median dev Sharpe | Best dev Sharpe | Median holdout Sharpe | Best holdout Sharpe | Median holdout CAGR |
|---|---|---|---|---|---|---|---|
| 10 | 7 | 96 | 1.236 | 1.688 | 0.022 | 0.575 | -3.55% |
| 10 | 14 | 96 | 0.972 | 1.388 | -0.211 | 0.474 | -8.49% |
| 20 | 7 | 96 | 1.184 | 1.601 | -0.098 | 0.677 | -7.24% |
| 20 | 14 | 96 | 0.913 | 1.362 | -0.338 | 0.317 | -12.75% |
| 30 | 7 | 96 | 1.143 | 1.600 | -0.168 | 0.288 | -9.40% |
| 30 | 14 | 96 | 1.060 | 1.491 | -0.683 | 0.051 | -22.51% |
| 50 | 7 | 96 | 1.194 | 1.670 | -0.192 | 0.318 | -10.94% |
| 50 | 14 | 96 | 0.927 | 1.681 | -0.691 | 0.068 | -25.46% |

## Top development-CPCV candidates

| Candidate | Median fold Sharpe | Worst fold Sharpe | Positive folds | Development Sharpe | Development turnover |
|---|---|---|---|---|---|
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 1.753 | -0.393 | 80.00% | 1.553 | 12.865 |
| u50_r7_momentum_126d_k10_strict_v3_reduced_momentum | 1.742 | 0.068 | 100.00% | 1.653 | 19.078 |
| u50_r14_momentum_63d_k10_strict_v3_btc_eth | 1.730 | -0.305 | 80.00% | 1.681 | 12.037 |
| u50_r7_momentum_63d_k10_strict_v3_btc_eth | 1.712 | -0.194 | 80.00% | 1.658 | 21.551 |
| u30_r7_momentum_21d_k3_balanced_v3_btc_eth | 1.697 | -0.573 | 80.00% | 1.431 | 24.988 |
| u10_r7_momentum_21d_k10_balanced_v4_btc_eth | 1.683 | -0.718 | 86.67% | 1.537 | 11.949 |
| u10_r7_momentum_63d_k10_balanced_v4_btc_eth | 1.683 | -0.718 | 86.67% | 1.537 | 11.949 |
| u10_r7_momentum_126d_k10_balanced_v4_btc_eth | 1.683 | -0.718 | 86.67% | 1.537 | 11.949 |
| u10_r7_volatility_adjusted_momentum_k10_balanced_v4_btc_eth | 1.683 | -0.718 | 86.67% | 1.537 | 11.949 |
| u10_r7_momentum_21d_k3_balanced_v4_btc_eth | 1.670 | -0.183 | 86.67% | 1.688 | 11.742 |
| u50_r7_volatility_adjusted_momentum_k10_strict_v3_btc_eth | 1.651 | -0.162 | 80.00% | 1.612 | 22.049 |
| u20_r7_momentum_21d_k5_balanced_v4_btc_eth | 1.651 | -0.407 | 86.67% | 1.522 | 13.821 |
| u20_r7_momentum_63d_k5_strict_v3_btc_eth | 1.629 | -0.286 | 86.67% | 1.308 | 20.495 |
| u50_r7_momentum_126d_k10_strict_v3_btc_eth | 1.624 | -0.033 | 86.67% | 1.559 | 20.845 |
| u10_r7_volatility_adjusted_momentum_k3_balanced_v4_btc_eth | 1.618 | -0.403 | 86.67% | 1.632 | 11.504 |
| u10_r7_momentum_63d_k3_strict_v3_btc_eth | 1.617 | -0.487 | 86.67% | 1.435 | 17.028 |
| u20_r7_momentum_21d_k3_balanced_v4_btc_eth | 1.614 | -0.152 | 93.33% | 1.601 | 12.289 |
| u30_r7_momentum_21d_k5_balanced_v4_reduced_momentum | 1.608 | -0.719 | 80.00% | 1.298 | 17.921 |
| u30_r7_momentum_21d_k5_balanced_v4_btc_eth | 1.599 | -0.136 | 86.67% | 1.418 | 14.360 |
| u10_r7_momentum_21d_k10_balanced_v4_reduced_momentum | 1.586 | -0.847 | 86.67% | 1.424 | 10.828 |
| u10_r7_momentum_63d_k10_balanced_v4_reduced_momentum | 1.586 | -0.847 | 86.67% | 1.424 | 10.828 |
| u10_r7_momentum_126d_k10_balanced_v4_reduced_momentum | 1.586 | -0.847 | 86.67% | 1.424 | 10.828 |
| u10_r7_volatility_adjusted_momentum_k10_balanced_v4_reduced_momentum | 1.586 | -0.847 | 86.67% | 1.424 | 10.828 |
| u50_r7_momentum_63d_k10_strict_v4_reduced_momentum | 1.581 | -0.307 | 80.00% | 1.400 | 9.774 |
| u10_r7_momentum_63d_k3_strict_v3_reduced_momentum | 1.570 | -0.489 | 80.00% | 1.332 | 16.354 |
