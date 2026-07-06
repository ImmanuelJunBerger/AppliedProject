# ML-enhanced cross-sectional crypto momentum

## Dataset and locked protocol

- Data: Binance daily spot panel, 2019-07-05 to 2026-06-19.
- Primary universe: point-in-time top 30 by trailing 90-day median dollar volume.
- Weekly cross-sectional observations: 363.
- Asset/weekly event rows: 10721.
- Unique historical universe members: 133.
- Full price-matrix missingness: 53.73%.
- Derivatives: daily Binance funding included.
- Locked holdout: 2025-01-01 onward; no holdout model, feature, target, or portfolio selection.
- Primary portfolio: top 5, weekly, equal weight subject to 20% cap, 75% turnover cap, 25 bps.

The source market catalogue cannot recover pairs Binance has removed, so the universe remains subject to delisting survivorship bias. Target B is mathematically rank-equivalent to Target A because subtracting the same weekly universe return does not change cross-sectional ranks; the implementation reports this rather than treating it as independent evidence.

## Development comparison

| Name | Model | Target | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure | Holdings |
|---|---|---|---|---|---|---|---|---|---|---|
| random_forest__forward_rank | random_forest | forward_rank | 112.60% | 1.375 | 1.852 | -80.75% | 1.394 | 10.05% | 100.00% | 5.252 |
| random_forest__residual_rank | random_forest | residual_rank | 112.60% | 1.375 | 1.852 | -80.75% | 1.394 | 10.05% | 100.00% | 5.252 |
| btc_eth_50_50 | benchmark | benchmark | 89.02% | 1.283 | 1.809 | -76.25% | 1.167 | 0.00% | 100.00% | 2.000 |
| eth_buy_hold | benchmark | benchmark | 94.58% | 1.230 | 1.785 | -79.30% | 1.193 | 0.00% | 100.00% | 1.000 |
| random_forest__risk_adjusted_rank | random_forest | risk_adjusted_rank | 90.71% | 1.214 | 1.633 | -84.42% | 1.074 | 12.10% | 100.00% | 5.378 |
| btc_buy_hold | benchmark | benchmark | 73.68% | 1.204 | 1.744 | -76.63% | 0.962 | 0.00% | 100.00% | 1.000 |
| boosted_tree__forward_rank | boosted_tree | forward_rank | 84.05% | 1.193 | 1.588 | -81.17% | 1.036 | 10.76% | 100.00% | 5.287 |
| boosted_tree__residual_rank | boosted_tree | residual_rank | 84.05% | 1.193 | 1.588 | -81.17% | 1.036 | 10.76% | 100.00% | 5.287 |
| gradient_boosting__forward_rank | gradient_boosting | forward_rank | 84.70% | 1.185 | 1.590 | -84.28% | 1.005 | 12.42% | 100.00% | 5.390 |
| gradient_boosting__residual_rank | gradient_boosting | residual_rank | 84.70% | 1.185 | 1.590 | -84.28% | 1.005 | 12.42% | 100.00% | 5.390 |
| boosted_tree__top_quintile | boosted_tree | top_quintile | 84.35% | 1.135 | 1.540 | -92.37% | 0.913 | 12.70% | 100.00% | 5.362 |
| ensemble__forward_rank | ensemble | forward_rank | 63.47% | 1.044 | 1.377 | -81.76% | 0.776 | 9.28% | 100.00% | 5.217 |
| ensemble__residual_rank | ensemble | residual_rank | 63.47% | 1.044 | 1.377 | -81.76% | 0.776 | 9.28% | 100.00% | 5.217 |
| random_forest__top_quintile | random_forest | top_quintile | 63.78% | 1.003 | 1.392 | -90.15% | 0.707 | 12.70% | 100.00% | 5.354 |
| boosted_tree__risk_adjusted_rank | boosted_tree | risk_adjusted_rank | 57.10% | 0.968 | 1.285 | -84.87% | 0.673 | 13.02% | 100.00% | 5.422 |
| gradient_boosting__top_quintile | gradient_boosting | top_quintile | 57.12% | 0.959 | 1.311 | -90.97% | 0.628 | 13.39% | 100.00% | 5.397 |
| gradient_boosting__risk_adjusted_rank | gradient_boosting | risk_adjusted_rank | 54.46% | 0.947 | 1.252 | -90.06% | 0.605 | 14.66% | 100.00% | 5.499 |
| pure_momentum_top10 | baseline | benchmark | 51.89% | 0.923 | 1.246 | -90.72% | 0.572 | 5.52% | 100.00% | 10.050 |
| equal_weight_top30 | benchmark | benchmark | 41.89% | 0.846 | 1.105 | -90.55% | 0.463 | 0.80% | 100.00% | 29.992 |
| elastic_net__risk_adjusted_rank | elastic_net | risk_adjusted_rank | 39.84% | 0.829 | 1.070 | -84.48% | 0.472 | 10.07% | 100.00% | 5.292 |
| elastic_net__forward_rank | elastic_net | forward_rank | 36.87% | 0.802 | 1.026 | -82.99% | 0.444 | 7.53% | 100.00% | 5.169 |
| elastic_net__residual_rank | elastic_net | residual_rank | 36.87% | 0.802 | 1.026 | -82.99% | 0.444 | 7.53% | 100.00% | 5.169 |
| pure_momentum | baseline | momentum_90_ex_7 | 32.92% | 0.798 | 1.087 | -95.99% | 0.343 | 7.24% | 100.00% | 5.116 |
| pure_momentum_top5 | baseline | benchmark | 32.92% | 0.798 | 1.087 | -95.99% | 0.343 | 7.24% | 100.00% | 5.116 |
| ensemble__risk_adjusted_rank | ensemble | risk_adjusted_rank | 25.20% | 0.683 | 0.899 | -87.88% | 0.287 | 11.31% | 100.00% | 5.317 |
| logistic__top_quintile | logistic | top_quintile | 0.22% | 0.490 | 0.663 | -97.81% | 0.002 | 12.58% | 100.00% | 5.332 |
| pure_momentum_top3 | baseline | benchmark | 5.73% | 0.425 | 0.576 | -87.49% | 0.065 | 5.01% | 100.00% | 3.040 |

## Locked holdout comparison

| Name | Model | Target | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure | Holdings |
|---|---|---|---|---|---|---|---|---|---|---|
| elastic_net__forward_rank | elastic_net | forward_rank | -12.62% | -0.038 | -0.052 | -48.99% | -0.258 | 1.57% | 100.00% | 5.004 |
| elastic_net__residual_rank | elastic_net | residual_rank | -12.62% | -0.038 | -0.052 | -48.99% | -0.258 | 1.57% | 100.00% | 5.004 |
| ensemble__forward_rank | ensemble | forward_rank | -13.96% | -0.041 | -0.055 | -53.78% | -0.260 | 3.21% | 100.00% | 5.022 |
| ensemble__residual_rank | ensemble | residual_rank | -13.96% | -0.041 | -0.055 | -53.78% | -0.260 | 3.21% | 100.00% | 5.022 |
| boosted_tree__forward_rank | boosted_tree | forward_rank | -18.96% | -0.129 | -0.180 | -57.13% | -0.332 | 3.51% | 100.00% | 5.006 |
| boosted_tree__residual_rank | boosted_tree | residual_rank | -18.96% | -0.129 | -0.180 | -57.13% | -0.332 | 3.51% | 100.00% | 5.006 |
| gradient_boosting__forward_rank | gradient_boosting | forward_rank | -19.96% | -0.149 | -0.205 | -56.15% | -0.355 | 4.49% | 100.00% | 5.019 |
| gradient_boosting__residual_rank | gradient_boosting | residual_rank | -19.96% | -0.149 | -0.205 | -56.15% | -0.355 | 4.49% | 100.00% | 5.019 |
| random_forest__forward_rank | random_forest | forward_rank | -21.13% | -0.168 | -0.232 | -54.46% | -0.388 | 2.99% | 100.00% | 5.007 |
| random_forest__residual_rank | random_forest | residual_rank | -21.13% | -0.168 | -0.232 | -54.46% | -0.388 | 2.99% | 100.00% | 5.007 |
| ensemble__risk_adjusted_rank | ensemble | risk_adjusted_rank | -22.18% | -0.238 | -0.323 | -52.19% | -0.425 | 3.51% | 100.00% | 5.034 |
| elastic_net__risk_adjusted_rank | elastic_net | risk_adjusted_rank | -21.66% | -0.246 | -0.332 | -50.32% | -0.430 | 0.30% | 100.00% | 5.000 |
| boosted_tree__risk_adjusted_rank | boosted_tree | risk_adjusted_rank | -22.62% | -0.256 | -0.352 | -56.74% | -0.399 | 4.49% | 100.00% | 5.050 |
| eth_buy_hold | benchmark | benchmark | -36.61% | -0.269 | -0.402 | -67.52% | -0.542 | 0.00% | 100.00% | 1.000 |
| btc_eth_50_50 | benchmark | benchmark | -28.69% | -0.320 | -0.460 | -59.21% | -0.484 | 0.00% | 100.00% | 2.000 |
| random_forest__risk_adjusted_rank | random_forest | risk_adjusted_rank | -27.31% | -0.364 | -0.492 | -54.22% | -0.504 | 3.51% | 100.00% | 5.011 |
| btc_buy_hold | benchmark | benchmark | -23.21% | -0.372 | -0.523 | -51.16% | -0.454 | 0.00% | 100.00% | 1.000 |
| gradient_boosting__top_quintile | gradient_boosting | top_quintile | -40.05% | -0.387 | -0.578 | -70.59% | -0.567 | 13.08% | 100.00% | 5.378 |
| logistic__top_quintile | logistic | top_quintile | -49.70% | -0.592 | -0.888 | -77.77% | -0.639 | 10.62% | 100.00% | 5.247 |
| random_forest__top_quintile | random_forest | top_quintile | -44.63% | -0.594 | -0.853 | -68.04% | -0.656 | 12.41% | 100.00% | 5.340 |
| pure_momentum_top3 | baseline | benchmark | -39.61% | -0.637 | -0.953 | -66.35% | -0.597 | 4.56% | 100.00% | 3.037 |
| gradient_boosting__risk_adjusted_rank | gradient_boosting | risk_adjusted_rank | -38.30% | -0.651 | -0.892 | -61.70% | -0.621 | 6.65% | 100.00% | 5.095 |
| equal_weight_top30 | benchmark | benchmark | -55.27% | -0.655 | -0.954 | -75.73% | -0.730 | 0.87% | 100.00% | 30.000 |
| pure_momentum | baseline | momentum_90_ex_7 | -57.48% | -0.662 | -0.947 | -82.26% | -0.699 | 7.18% | 100.00% | 5.114 |
| pure_momentum_top5 | baseline | benchmark | -57.48% | -0.662 | -0.947 | -82.26% | -0.699 | 7.18% | 100.00% | 5.114 |
| boosted_tree__top_quintile | boosted_tree | top_quintile | -45.42% | -0.667 | -0.981 | -70.88% | -0.641 | 12.26% | 100.00% | 5.346 |
| pure_momentum_top10 | baseline | benchmark | -59.22% | -0.826 | -1.201 | -80.96% | -0.732 | 5.76% | 100.00% | 10.032 |

## Development-selected champion

- Candidate: **random_forest__forward_rank**
- Model: **random_forest**
- Target: **forward_rank**
- Feature set: **all_features**
- Configurations counted: 127
