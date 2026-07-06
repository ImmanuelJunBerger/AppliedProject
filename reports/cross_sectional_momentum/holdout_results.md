# Locked holdout results

The champion was selected using development performance only. All candidates are shown to expose selection risk; none was substituted after viewing holdout results.

| Name | Model | Target | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure | Holdings | Total costs | Best month | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| elastic_net__forward_rank | elastic_net | forward_rank | -12.62% | -0.038 | -0.052 | -48.99% | -0.258 | 1.57% | 100.00% | 5.004 | 2.10% | 30.05% | -20.15% |
| elastic_net__residual_rank | elastic_net | residual_rank | -12.62% | -0.038 | -0.052 | -48.99% | -0.258 | 1.57% | 100.00% | 5.004 | 2.10% | 30.05% | -20.15% |
| ensemble__forward_rank | ensemble | forward_rank | -13.96% | -0.041 | -0.055 | -53.78% | -0.260 | 3.21% | 100.00% | 5.022 | 4.30% | 28.47% | -21.63% |
| ensemble__residual_rank | ensemble | residual_rank | -13.96% | -0.041 | -0.055 | -53.78% | -0.260 | 3.21% | 100.00% | 5.022 | 4.30% | 28.47% | -21.63% |
| boosted_tree__forward_rank | boosted_tree | forward_rank | -18.96% | -0.129 | -0.180 | -57.13% | -0.332 | 3.51% | 100.00% | 5.006 | 4.70% | 28.33% | -25.68% |
| boosted_tree__residual_rank | boosted_tree | residual_rank | -18.96% | -0.129 | -0.180 | -57.13% | -0.332 | 3.51% | 100.00% | 5.006 | 4.70% | 28.33% | -25.68% |
| gradient_boosting__forward_rank | gradient_boosting | forward_rank | -19.96% | -0.149 | -0.205 | -56.15% | -0.355 | 4.49% | 100.00% | 5.019 | 6.00% | 29.45% | -26.39% |
| gradient_boosting__residual_rank | gradient_boosting | residual_rank | -19.96% | -0.149 | -0.205 | -56.15% | -0.355 | 4.49% | 100.00% | 5.019 | 6.00% | 29.45% | -26.39% |
| random_forest__forward_rank | random_forest | forward_rank | -21.13% | -0.168 | -0.232 | -54.46% | -0.388 | 2.99% | 100.00% | 5.007 | 4.00% | 27.49% | -26.39% |
| random_forest__residual_rank | random_forest | residual_rank | -21.13% | -0.168 | -0.232 | -54.46% | -0.388 | 2.99% | 100.00% | 5.007 | 4.00% | 27.49% | -26.39% |
| ensemble__risk_adjusted_rank | ensemble | risk_adjusted_rank | -22.18% | -0.238 | -0.323 | -52.19% | -0.425 | 3.51% | 100.00% | 5.034 | 4.70% | 23.77% | -20.24% |
| elastic_net__risk_adjusted_rank | elastic_net | risk_adjusted_rank | -21.66% | -0.246 | -0.332 | -50.32% | -0.430 | 0.30% | 100.00% | 5.000 | 0.40% | 25.27% | -25.77% |
| boosted_tree__risk_adjusted_rank | boosted_tree | risk_adjusted_rank | -22.62% | -0.256 | -0.352 | -56.74% | -0.399 | 4.49% | 100.00% | 5.050 | 6.00% | 25.27% | -20.20% |
| eth_buy_hold | benchmark | benchmark | -36.61% | -0.269 | -0.402 | -67.52% | -0.542 | 0.00% | 100.00% | 1.000 | 0.00% | 48.80% | -32.21% |
| btc_eth_50_50 | benchmark | benchmark | -28.69% | -0.320 | -0.460 | -59.21% | -0.484 | 0.00% | 100.00% | 2.000 | 0.00% | 27.10% | -25.10% |
| random_forest__risk_adjusted_rank | random_forest | risk_adjusted_rank | -27.31% | -0.364 | -0.492 | -54.22% | -0.504 | 3.51% | 100.00% | 5.011 | 4.70% | 25.27% | -27.29% |
| btc_buy_hold | benchmark | benchmark | -23.21% | -0.372 | -0.523 | -51.16% | -0.454 | 0.00% | 100.00% | 1.000 | 0.00% | 14.08% | -17.65% |
| gradient_boosting__top_quintile | gradient_boosting | top_quintile | -40.05% | -0.387 | -0.578 | -70.59% | -0.567 | 13.08% | 100.00% | 5.378 | 17.50% | 42.41% | -29.74% |
| logistic__top_quintile | logistic | top_quintile | -49.70% | -0.592 | -0.888 | -77.77% | -0.639 | 10.62% | 100.00% | 5.247 | 14.20% | 41.23% | -31.50% |
| random_forest__top_quintile | random_forest | top_quintile | -44.63% | -0.594 | -0.853 | -68.04% | -0.656 | 12.41% | 100.00% | 5.340 | 16.60% | 32.70% | -29.97% |
| pure_momentum_top3 | baseline | benchmark | -39.61% | -0.637 | -0.953 | -66.35% | -0.597 | 4.56% | 100.00% | 3.037 | 6.10% | 18.83% | -23.52% |
| gradient_boosting__risk_adjusted_rank | gradient_boosting | risk_adjusted_rank | -38.30% | -0.651 | -0.892 | -61.70% | -0.621 | 6.65% | 100.00% | 5.095 | 8.90% | 22.22% | -23.26% |
| equal_weight_top30 | benchmark | benchmark | -55.27% | -0.655 | -0.954 | -75.73% | -0.730 | 0.87% | 100.00% | 30.000 | 1.17% | 27.06% | -31.11% |
| pure_momentum | baseline | momentum_90_ex_7 | -57.48% | -0.662 | -0.947 | -82.26% | -0.699 | 7.18% | 100.00% | 5.114 | 9.60% | 21.98% | -32.17% |
| pure_momentum_top5 | baseline | benchmark | -57.48% | -0.662 | -0.947 | -82.26% | -0.699 | 7.18% | 100.00% | 5.114 | 9.60% | 21.98% | -32.17% |
| boosted_tree__top_quintile | boosted_tree | top_quintile | -45.42% | -0.667 | -0.981 | -70.88% | -0.641 | 12.26% | 100.00% | 5.346 | 16.40% | 33.35% | -26.42% |
| pure_momentum_top10 | baseline | benchmark | -59.22% | -0.826 | -1.201 | -80.96% | -0.732 | 5.76% | 100.00% | 10.032 | 7.70% | 18.85% | -31.70% |

## Paired comparison with pure momentum

- Sharpe delta 95% block-bootstrap interval: [-0.289, 1.493]
- Median Sharpe delta: 0.590
- Holdout survives with positive Sharpe and CAGR: **No**
