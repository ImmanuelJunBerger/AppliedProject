# Calibration and feature importance

SHAP values are not required for this module and are only used if available in a
future extension. The current report uses model coefficients or native feature
importance where available.

## Calibration curve

| Config | Split | Bin | Obs | Mean probability | Event rate |
|---|---|---|---|---|---|
| btc_30d_gt_15__random_forest | development_cpcv | 1 | 27 | 22.30% | 22.22% |
| btc_30d_gt_15__random_forest | development_cpcv | 2 | 26 | 28.04% | 38.46% |
| btc_30d_gt_15__random_forest | development_cpcv | 3 | 26 | 32.36% | 34.62% |
| btc_30d_gt_15__random_forest | development_cpcv | 4 | 26 | 36.33% | 26.92% |
| btc_30d_gt_15__random_forest | development_cpcv | 5 | 26 | 39.34% | 30.77% |
| btc_30d_gt_15__random_forest | development_cpcv | 6 | 26 | 41.91% | 23.08% |
| btc_30d_gt_15__random_forest | development_cpcv | 7 | 26 | 44.96% | 23.08% |
| btc_30d_gt_15__random_forest | development_cpcv | 8 | 26 | 48.75% | 26.92% |
| btc_30d_gt_15__random_forest | development_cpcv | 9 | 26 | 52.66% | 26.92% |
| btc_30d_gt_15__random_forest | development_cpcv | 10 | 26 | 58.93% | 30.77% |
| btc_30d_gt_15__random_forest | holdout | 1 | 8 | 25.80% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 2 | 7 | 30.17% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 3 | 7 | 34.03% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 4 | 7 | 38.55% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 5 | 8 | 40.39% | 12.50% |
| btc_30d_gt_15__random_forest | holdout | 6 | 7 | 43.01% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 7 | 7 | 45.72% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 8 | 7 | 50.11% | 28.57% |
| btc_30d_gt_15__random_forest | holdout | 9 | 7 | 55.63% | 14.29% |
| btc_30d_gt_15__random_forest | holdout | 10 | 8 | 63.28% | 12.50% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 1 | 27 | 29.81% | 18.52% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 2 | 26 | 37.21% | 23.08% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 3 | 26 | 39.86% | 15.38% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 4 | 26 | 42.76% | 38.46% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 5 | 26 | 45.51% | 38.46% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 6 | 26 | 48.85% | 30.77% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 7 | 26 | 52.85% | 26.92% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 8 | 26 | 58.97% | 46.15% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 9 | 26 | 69.20% | 42.31% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 10 | 26 | 87.04% | 46.15% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 1 | 8 | 31.57% | 12.50% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 2 | 7 | 36.59% | 14.29% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 3 | 7 | 39.02% | 0.00% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 4 | 7 | 41.08% | 14.29% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 5 | 8 | 42.67% | 12.50% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 6 | 7 | 44.84% | 14.29% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 7 | 7 | 47.35% | 57.14% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 8 | 7 | 50.11% | 28.57% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 9 | 7 | 52.33% | 28.57% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 10 | 8 | 62.68% | 37.50% |

## Selected model feature importance

| Config | Feature | Importance | Method |
|---|---|---|---|
| btc_30d_gt_15__random_forest | tvl_growth_30d | 0.128 | model_importance |
| btc_30d_gt_15__random_forest | dow_vol_level | 0.126 | model_importance |
| btc_30d_gt_15__random_forest | vix_level | 0.124 | model_importance |
| btc_30d_gt_15__random_forest | cross_sectional_dispersion | 0.106 | model_importance |
| btc_30d_gt_15__random_forest | volatility_expansion_probability | 0.093 | model_importance |
| btc_30d_gt_15__random_forest | vix_change_21d | 0.091 | model_importance |
| btc_30d_gt_15__random_forest | volatility_4h_7d | 0.089 | model_importance |
| btc_30d_gt_15__random_forest | stablecoin_supply_change_7d | 0.069 | model_importance |
| btc_30d_gt_15__random_forest | equity_realized_vol_21d | 0.065 | model_importance |
| btc_30d_gt_15__random_forest | equity_momentum_21d | 0.063 | model_importance |
| btc_30d_gt_15__random_forest | vix_change_5d | 0.046 | model_importance |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | volatility_4h_7d | 0.603 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | dow_vol_level | 0.349 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | cross_sectional_dispersion | -0.316 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | vix_change_5d | -0.275 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | tvl_growth_30d | 0.261 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | equity_realized_vol_21d | -0.227 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | volatility_expansion_probability | 0.083 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | stablecoin_supply_change_7d | 0.067 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | vix_change_21d | 0.057 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | equity_momentum_21d | -0.053 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | vix_level | 0.000 | coefficient |
