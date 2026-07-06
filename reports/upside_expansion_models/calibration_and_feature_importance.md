# Calibration and feature importance

SHAP was requested if available. The `shap` package is not installed in this
environment, so this module reports model coefficients or native feature
importance instead.

## Calibration

| Config | Split | Bin | Obs | Mean probability | Event rate |
|---|---|---|---|---|---|
| btc_30d_gt_15__random_forest | development_cpcv | 1 | 27 | 22.88% | 11.11% |
| btc_30d_gt_15__random_forest | development_cpcv | 2 | 26 | 28.26% | 57.69% |
| btc_30d_gt_15__random_forest | development_cpcv | 3 | 26 | 32.93% | 30.77% |
| btc_30d_gt_15__random_forest | development_cpcv | 4 | 26 | 36.79% | 23.08% |
| btc_30d_gt_15__random_forest | development_cpcv | 5 | 26 | 39.85% | 30.77% |
| btc_30d_gt_15__random_forest | development_cpcv | 6 | 26 | 43.28% | 23.08% |
| btc_30d_gt_15__random_forest | development_cpcv | 7 | 26 | 46.24% | 23.08% |
| btc_30d_gt_15__random_forest | development_cpcv | 8 | 26 | 49.32% | 23.08% |
| btc_30d_gt_15__random_forest | development_cpcv | 9 | 26 | 52.61% | 34.62% |
| btc_30d_gt_15__random_forest | development_cpcv | 10 | 26 | 59.02% | 26.92% |
| btc_30d_gt_15__random_forest | holdout | 1 | 8 | 25.46% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 2 | 7 | 30.53% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 3 | 7 | 34.00% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 4 | 7 | 37.95% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 5 | 8 | 40.16% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 6 | 7 | 42.19% | 0.00% |
| btc_30d_gt_15__random_forest | holdout | 7 | 7 | 45.02% | 14.29% |
| btc_30d_gt_15__random_forest | holdout | 8 | 7 | 50.03% | 14.29% |
| btc_30d_gt_15__random_forest | holdout | 9 | 7 | 54.93% | 28.57% |
| btc_30d_gt_15__random_forest | holdout | 10 | 8 | 62.80% | 12.50% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 1 | 27 | 31.44% | 18.52% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 2 | 26 | 37.49% | 19.23% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 3 | 26 | 40.36% | 38.46% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 4 | 26 | 43.23% | 26.92% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 5 | 26 | 45.89% | 30.77% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 6 | 26 | 49.21% | 23.08% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 7 | 26 | 53.25% | 38.46% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 8 | 26 | 59.24% | 38.46% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 9 | 26 | 69.00% | 46.15% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 10 | 26 | 86.47% | 46.15% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 1 | 8 | 31.99% | 12.50% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 2 | 7 | 36.90% | 14.29% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 3 | 7 | 38.42% | 0.00% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 4 | 7 | 40.38% | 14.29% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 5 | 8 | 42.92% | 25.00% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 6 | 7 | 44.67% | 14.29% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 7 | 7 | 46.60% | 28.57% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 8 | 7 | 49.61% | 57.14% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 9 | 7 | 52.48% | 14.29% |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 10 | 8 | 62.44% | 37.50% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 1 | 27 | 23.34% | 33.33% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 2 | 26 | 37.27% | 30.77% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 3 | 26 | 42.39% | 23.08% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 4 | 26 | 44.87% | 34.62% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 5 | 26 | 46.50% | 46.15% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 6 | 26 | 48.72% | 26.92% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 7 | 26 | 50.84% | 42.31% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 8 | 26 | 53.16% | 26.92% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 9 | 26 | 55.74% | 42.31% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | development_cpcv | 10 | 26 | 61.88% | 42.31% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 1 | 8 | 39.81% | 37.50% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 2 | 7 | 43.19% | 42.86% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 3 | 7 | 44.72% | 42.86% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 4 | 7 | 46.53% | 14.29% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 5 | 8 | 47.44% | 25.00% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 6 | 7 | 49.54% | 28.57% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 7 | 7 | 51.54% | 42.86% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 8 | 7 | 52.92% | 71.43% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 9 | 7 | 54.89% | 85.71% |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | holdout | 10 | 8 | 61.79% | 62.50% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 1 | 27 | 4.23% | 7.41% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 2 | 26 | 7.28% | 0.00% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 3 | 26 | 10.13% | 11.54% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 4 | 26 | 12.40% | 11.54% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 5 | 26 | 15.19% | 34.62% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 6 | 26 | 18.61% | 26.92% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 7 | 26 | 23.36% | 15.38% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 8 | 26 | 28.87% | 30.77% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 9 | 26 | 34.62% | 42.31% |
| risk_off_to_risk_on_2_4w__gradient_boosting | development_cpcv | 10 | 26 | 50.36% | 34.62% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 1 | 8 | 3.64% | 25.00% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 2 | 7 | 6.20% | 0.00% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 3 | 7 | 8.21% | 42.86% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 4 | 7 | 10.95% | 28.57% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 5 | 8 | 15.23% | 12.50% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 6 | 7 | 17.76% | 14.29% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 7 | 7 | 20.70% | 14.29% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 8 | 7 | 23.80% | 0.00% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 9 | 7 | 29.31% | 14.29% |
| risk_off_to_risk_on_2_4w__gradient_boosting | holdout | 10 | 8 | 50.32% | 62.50% |

## Selected-model feature importance

| Config | Feature | Importance | Method |
|---|---|---|---|
| btc_30d_gt_15__random_forest | tvl_growth_30d | 0.139 | model_importance |
| btc_30d_gt_15__random_forest | dow_vol_level | 0.136 | model_importance |
| btc_30d_gt_15__random_forest | vix_level | 0.123 | model_importance |
| btc_30d_gt_15__random_forest | vix_change_21d | 0.096 | model_importance |
| btc_30d_gt_15__random_forest | volatility_expansion_probability | 0.095 | model_importance |
| btc_30d_gt_15__random_forest | volatility_4h_7d | 0.084 | model_importance |
| btc_30d_gt_15__random_forest | cross_sectional_dispersion | 0.081 | model_importance |
| btc_30d_gt_15__random_forest | equity_realized_vol_21d | 0.070 | model_importance |
| btc_30d_gt_15__random_forest | equity_momentum_21d | 0.067 | model_importance |
| btc_30d_gt_15__random_forest | stablecoin_supply_change_7d | 0.062 | model_importance |
| btc_30d_gt_15__random_forest | vix_change_5d | 0.047 | model_importance |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | volatility_4h_7d | 0.559 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | dow_vol_level | 0.358 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | vix_change_5d | -0.280 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | cross_sectional_dispersion | -0.261 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | tvl_growth_30d | 0.250 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | equity_realized_vol_21d | -0.236 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | stablecoin_supply_change_7d | 0.067 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | volatility_expansion_probability | 0.065 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | vix_change_21d | 0.062 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | equity_momentum_21d | -0.052 | coefficient |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | vix_level | 0.000 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | volatility_4h_7d | -0.367 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | equity_momentum_21d | -0.245 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | cross_sectional_dispersion | 0.217 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | vix_level | -0.190 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | volatility_expansion_probability | -0.179 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | vix_change_5d | 0.133 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | equity_realized_vol_21d | 0.129 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | stablecoin_supply_change_7d | 0.126 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | tvl_growth_30d | 0.006 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | vix_change_21d | -0.001 | coefficient |
| btc_leads_eth_30d_gt_5__elastic_net_logistic | dow_vol_level | 0.000 | coefficient |
| risk_off_to_risk_on_2_4w__gradient_boosting | vix_change_21d | 0.232 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | vix_change_5d | 0.188 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | equity_momentum_21d | 0.104 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | cross_sectional_dispersion | 0.089 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | vix_level | 0.084 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | equity_realized_vol_21d | 0.078 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | stablecoin_supply_change_7d | 0.071 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | dow_vol_level | 0.063 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | volatility_4h_7d | 0.037 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | volatility_expansion_probability | 0.035 | model_importance |
| risk_off_to_risk_on_2_4w__gradient_boosting | tvl_growth_30d | 0.019 | model_importance |
| top20_top_quintile_30d__xgboost | cross_sectional_dispersion | 0.110 | model_importance |
| top20_top_quintile_30d__xgboost | volatility_expansion_probability | 0.101 | model_importance |
| top20_top_quintile_30d__xgboost | asset_volatility_30d | 0.076 | model_importance |
| top20_top_quintile_30d__xgboost | vix_change_21d | 0.076 | model_importance |
| top20_top_quintile_30d__xgboost | asset_momentum_90d | 0.072 | model_importance |
| top20_top_quintile_30d__xgboost | asset_momentum_30d | 0.068 | model_importance |
| top20_top_quintile_30d__xgboost | vix_level | 0.068 | model_importance |
| top20_top_quintile_30d__xgboost | equity_momentum_21d | 0.063 | model_importance |
| top20_top_quintile_30d__xgboost | asset_volume_expansion | 0.059 | model_importance |
| top20_top_quintile_30d__xgboost | equity_realized_vol_21d | 0.057 | model_importance |
| top20_top_quintile_30d__xgboost | tvl_growth_30d | 0.056 | model_importance |
| top20_top_quintile_30d__xgboost | volatility_4h_7d | 0.053 | model_importance |
| top20_top_quintile_30d__xgboost | dow_vol_level | 0.048 | model_importance |
| top20_top_quintile_30d__xgboost | stablecoin_supply_change_7d | 0.047 | model_importance |
| top20_top_quintile_30d__xgboost | vix_change_5d | 0.045 | model_importance |
