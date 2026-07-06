# Model comparison

All listed model families that were installed were tested independently.
LSTM was skipped because the sample size is too small for credible CPCV.

## Predictive metrics

| Config | Target | Model | Family | Split | AUC | Precision | Recall | F1 | Brier |
|---|---|---|---|---|---|---|---|---|---|
| target_a_btc_30d_gt_15__logistic_regression | target_a_btc_30d_gt_15 | logistic_regression | Linear | development_cpcv | 0.536 | 0.299 | 0.558 | 0.389 | 0.255 |
| target_a_btc_30d_gt_15__logistic_regression | target_a_btc_30d_gt_15 | logistic_regression | Linear | holdout | 0.432 | 0.049 | 0.400 | 0.087 | 0.255 |
| target_a_btc_30d_gt_15__elastic_net_logistic | target_a_btc_30d_gt_15 | elastic_net_logistic | Linear | development_cpcv | 0.530 | 0.270 | 0.494 | 0.349 | 0.244 |
| target_a_btc_30d_gt_15__elastic_net_logistic | target_a_btc_30d_gt_15 | elastic_net_logistic | Linear | holdout | 0.444 | 0.045 | 0.400 | 0.082 | 0.240 |
| target_a_btc_30d_gt_15__random_forest | target_a_btc_30d_gt_15 | random_forest | Tree | development_cpcv | 0.509 | 0.263 | 0.649 | 0.375 | 0.237 |
| target_a_btc_30d_gt_15__random_forest | target_a_btc_30d_gt_15 | random_forest | Tree | holdout | 0.847 | 0.119 | 1.000 | 0.213 | 0.185 |
| target_a_btc_30d_gt_15__gradient_boosting | target_a_btc_30d_gt_15 | gradient_boosting | Tree | development_cpcv | 0.428 | 0.196 | 0.117 | 0.146 | 0.226 |
| target_a_btc_30d_gt_15__gradient_boosting | target_a_btc_30d_gt_15 | gradient_boosting | Tree | holdout | 0.785 | 0.167 | 0.200 | 0.182 | 0.088 |
| target_a_btc_30d_gt_15__xgboost | target_a_btc_30d_gt_15 | xgboost | Tree | development_cpcv | 0.447 | 0.200 | 0.104 | 0.137 | 0.222 |
| target_a_btc_30d_gt_15__xgboost | target_a_btc_30d_gt_15 | xgboost | Tree | holdout | 0.791 | 0.333 | 0.400 | 0.364 | 0.085 |
| target_a_btc_30d_gt_15__shallow_mlp | target_a_btc_30d_gt_15 | shallow_mlp | Neural | development_cpcv | 0.447 | 0.271 | 0.909 | 0.418 | 0.390 |
| target_a_btc_30d_gt_15__shallow_mlp | target_a_btc_30d_gt_15 | shallow_mlp | Neural | holdout | 0.729 | 0.167 | 0.600 | 0.261 | 0.148 |
| target_b_eth_30d_gt_20__logistic_regression | target_b_eth_30d_gt_20 | logistic_regression | Linear | development_cpcv | 0.541 | 0.295 | 0.520 | 0.377 | 0.252 |
| target_b_eth_30d_gt_20__logistic_regression | target_b_eth_30d_gt_20 | logistic_regression | Linear | holdout | 0.610 | 0.191 | 0.818 | 0.310 | 0.255 |
| target_b_eth_30d_gt_20__elastic_net_logistic | target_b_eth_30d_gt_20 | elastic_net_logistic | Linear | development_cpcv | 0.566 | 0.320 | 0.533 | 0.400 | 0.240 |
| target_b_eth_30d_gt_20__elastic_net_logistic | target_b_eth_30d_gt_20 | elastic_net_logistic | Linear | holdout | 0.635 | 0.174 | 0.727 | 0.281 | 0.233 |
| target_b_eth_30d_gt_20__random_forest | target_b_eth_30d_gt_20 | random_forest | Tree | development_cpcv | 0.543 | 0.282 | 0.640 | 0.392 | 0.223 |
| target_b_eth_30d_gt_20__random_forest | target_b_eth_30d_gt_20 | random_forest | Tree | holdout | 0.641 | 0.167 | 0.545 | 0.255 | 0.185 |
| target_b_eth_30d_gt_20__gradient_boosting | target_b_eth_30d_gt_20 | gradient_boosting | Tree | development_cpcv | 0.530 | 0.242 | 0.107 | 0.148 | 0.207 |
| target_b_eth_30d_gt_20__gradient_boosting | target_b_eth_30d_gt_20 | gradient_boosting | Tree | holdout | 0.667 | 0.750 | 0.273 | 0.400 | 0.119 |
| target_b_eth_30d_gt_20__xgboost | target_b_eth_30d_gt_20 | xgboost | Tree | development_cpcv | 0.536 | 0.222 | 0.080 | 0.118 | 0.204 |
| target_b_eth_30d_gt_20__xgboost | target_b_eth_30d_gt_20 | xgboost | Tree | holdout | 0.692 | 0.800 | 0.364 | 0.500 | 0.114 |
| target_b_eth_30d_gt_20__shallow_mlp | target_b_eth_30d_gt_20 | shallow_mlp | Neural | development_cpcv | 0.504 | 0.280 | 0.947 | 0.432 | 0.360 |
| target_b_eth_30d_gt_20__shallow_mlp | target_b_eth_30d_gt_20 | shallow_mlp | Neural | holdout | 0.729 | 0.257 | 0.818 | 0.391 | 0.184 |
| target_c_eth_beats_btc_30d_gt_5__logistic_regression | target_c_eth_beats_btc_30d_gt_5 | logistic_regression | Linear | development_cpcv | 0.690 | 0.457 | 0.637 | 0.532 | 0.214 |
| target_c_eth_beats_btc_30d_gt_5__logistic_regression | target_c_eth_beats_btc_30d_gt_5 | logistic_regression | Linear | holdout | 0.698 | 0.333 | 0.562 | 0.419 | 0.172 |
| target_c_eth_beats_btc_30d_gt_5__elastic_net_logistic | target_c_eth_beats_btc_30d_gt_5 | elastic_net_logistic | Linear | development_cpcv | 0.709 | 0.505 | 0.527 | 0.516 | 0.208 |
| target_c_eth_beats_btc_30d_gt_5__elastic_net_logistic | target_c_eth_beats_btc_30d_gt_5 | elastic_net_logistic | Linear | holdout | 0.682 | 0.471 | 0.500 | 0.485 | 0.176 |
| target_c_eth_beats_btc_30d_gt_5__random_forest | target_c_eth_beats_btc_30d_gt_5 | random_forest | Tree | development_cpcv | 0.629 | 0.366 | 0.747 | 0.491 | 0.226 |
| target_c_eth_beats_btc_30d_gt_5__random_forest | target_c_eth_beats_btc_30d_gt_5 | random_forest | Tree | holdout | 0.775 | 0.300 | 0.938 | 0.455 | 0.189 |
| target_c_eth_beats_btc_30d_gt_5__gradient_boosting | target_c_eth_beats_btc_30d_gt_5 | gradient_boosting | Tree | development_cpcv | 0.594 | 0.411 | 0.330 | 0.366 | 0.222 |
| target_c_eth_beats_btc_30d_gt_5__gradient_boosting | target_c_eth_beats_btc_30d_gt_5 | gradient_boosting | Tree | holdout | 0.603 | 0.600 | 0.188 | 0.286 | 0.158 |
| target_c_eth_beats_btc_30d_gt_5__xgboost | target_c_eth_beats_btc_30d_gt_5 | xgboost | Tree | development_cpcv | 0.606 | 0.446 | 0.319 | 0.372 | 0.219 |
| target_c_eth_beats_btc_30d_gt_5__xgboost | target_c_eth_beats_btc_30d_gt_5 | xgboost | Tree | holdout | 0.680 | 0.429 | 0.188 | 0.261 | 0.154 |
| target_c_eth_beats_btc_30d_gt_5__shallow_mlp | target_c_eth_beats_btc_30d_gt_5 | shallow_mlp | Neural | development_cpcv | 0.540 | 0.343 | 0.956 | 0.504 | 0.336 |
| target_c_eth_beats_btc_30d_gt_5__shallow_mlp | target_c_eth_beats_btc_30d_gt_5 | shallow_mlp | Neural | holdout | 0.660 | 0.333 | 0.500 | 0.400 | 0.180 |
| target_d_top20_leadership__logistic_regression | target_d_top20_leadership | logistic_regression | Linear | development_cpcv | 0.401 | 0.214 | 0.380 | 0.274 | 0.272 |
| target_d_top20_leadership__logistic_regression | target_d_top20_leadership | logistic_regression | Linear | holdout | 0.581 | 0.172 | 1.000 | 0.294 | 0.361 |
| target_d_top20_leadership__elastic_net_logistic | target_d_top20_leadership | elastic_net_logistic | Linear | development_cpcv | 0.395 | 0.218 | 0.408 | 0.284 | 0.268 |
| target_d_top20_leadership__elastic_net_logistic | target_d_top20_leadership | elastic_net_logistic | Linear | holdout | 0.576 | 0.167 | 1.000 | 0.286 | 0.335 |
| target_d_top20_leadership__random_forest | target_d_top20_leadership | random_forest | Tree | development_cpcv | 0.456 | 0.230 | 0.648 | 0.339 | 0.235 |
| target_d_top20_leadership__random_forest | target_d_top20_leadership | random_forest | Tree | holdout | 0.433 | 0.138 | 0.800 | 0.235 | 0.236 |
| target_d_top20_leadership__gradient_boosting | target_d_top20_leadership | gradient_boosting | Tree | development_cpcv | 0.439 | 0.194 | 0.085 | 0.118 | 0.214 |
| target_d_top20_leadership__gradient_boosting | target_d_top20_leadership | gradient_boosting | Tree | holdout | 0.410 | 0.000 | 0.000 | 0.000 | 0.147 |
| target_d_top20_leadership__xgboost | target_d_top20_leadership | xgboost | Tree | development_cpcv | 0.446 | 0.226 | 0.099 | 0.137 | 0.210 |
| target_d_top20_leadership__xgboost | target_d_top20_leadership | xgboost | Tree | holdout | 0.486 | 0.000 | 0.000 | 0.000 | 0.147 |
| target_d_top20_leadership__shallow_mlp | target_d_top20_leadership | shallow_mlp | Neural | development_cpcv | 0.510 | 0.246 | 0.859 | 0.382 | 0.362 |
| target_d_top20_leadership__shallow_mlp | target_d_top20_leadership | shallow_mlp | Neural | holdout | 0.668 | 0.175 | 1.000 | 0.299 | 0.242 |
| target_e_top20_asset_top_quintile__logistic_regression | target_e_top20_asset_top_quintile | logistic_regression | Linear | development_cpcv | 0.564 | 0.203 | 0.959 | 0.336 | 0.248 |
| target_e_top20_asset_top_quintile__logistic_regression | target_e_top20_asset_top_quintile | logistic_regression | Linear | holdout | 0.596 | 0.203 | 0.983 | 0.337 | 0.254 |
| target_e_top20_asset_top_quintile__elastic_net_logistic | target_e_top20_asset_top_quintile | elastic_net_logistic | Linear | development_cpcv | 0.565 | 0.203 | 0.967 | 0.336 | 0.249 |
| target_e_top20_asset_top_quintile__elastic_net_logistic | target_e_top20_asset_top_quintile | elastic_net_logistic | Linear | holdout | 0.597 | 0.203 | 0.983 | 0.336 | 0.253 |
| target_e_top20_asset_top_quintile__random_forest | target_e_top20_asset_top_quintile | random_forest | Tree | development_cpcv | 0.528 | 0.201 | 1.000 | 0.335 | 0.244 |
| target_e_top20_asset_top_quintile__random_forest | target_e_top20_asset_top_quintile | random_forest | Tree | holdout | 0.627 | 0.200 | 1.000 | 0.333 | 0.244 |
| target_e_top20_asset_top_quintile__gradient_boosting | target_e_top20_asset_top_quintile | gradient_boosting | Tree | development_cpcv | 0.532 | 0.250 | 0.001 | 0.002 | 0.162 |
| target_e_top20_asset_top_quintile__gradient_boosting | target_e_top20_asset_top_quintile | gradient_boosting | Tree | holdout | 0.588 | 0.500 | 0.007 | 0.014 | 0.158 |
| target_e_top20_asset_top_quintile__xgboost | target_e_top20_asset_top_quintile | xgboost | Tree | development_cpcv | 0.540 | 0.000 | 0.000 | 0.000 | 0.161 |
| target_e_top20_asset_top_quintile__xgboost | target_e_top20_asset_top_quintile | xgboost | Tree | holdout | 0.626 | 0.000 | 0.000 | 0.000 | 0.156 |
| target_e_top20_asset_top_quintile__shallow_mlp | target_e_top20_asset_top_quintile | shallow_mlp | Neural | development_cpcv | 0.498 | 0.207 | 0.073 | 0.108 | 0.174 |
| target_e_top20_asset_top_quintile__shallow_mlp | target_e_top20_asset_top_quintile | shallow_mlp | Neural | holdout | 0.483 | 0.222 | 0.171 | 0.193 | 0.180 |
