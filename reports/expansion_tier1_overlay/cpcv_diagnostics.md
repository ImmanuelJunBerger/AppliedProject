# CPCV diagnostics

## Fold distribution for selected overlay

| Candidate | Allocation | Fold | Test groups | Fold Sharpe |
|---|---|---|---|---|
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 0 | 0,1 | 2.193 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 1 | 0,2 | 0.631 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 2 | 0,3 | 0.162 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 3 | 0,4 | 1.023 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 4 | 0,5 | 1.048 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 5 | 1,2 | 1.670 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 6 | 1,3 | 1.117 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 7 | 1,4 | 2.076 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 8 | 1,5 | 2.114 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 9 | 2,3 | -0.564 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 10 | 2,4 | 0.185 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 11 | 2,5 | 0.187 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 12 | 3,4 | -0.297 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 13 | 3,5 | -0.308 |
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 14 | 4,5 | 0.724 |

## Prediction diagnostics

| Config | Target | Split | AUC | Precision | Recall | F1 | Brier |
|---|---|---|---|---|---|---|---|
| target_a_btc_eth_upside__logistic_regression | target_a_btc_eth_upside | development_cpcv | 0.579 | 0.345 | 0.583 | 0.434 | 0.259 |
| target_a_btc_eth_upside__logistic_regression | target_a_btc_eth_upside | holdout | 0.667 | 0.143 | 0.600 | 0.231 | 0.232 |
| target_a_btc_eth_upside__elastic_net_logistic | target_a_btc_eth_upside | development_cpcv | 0.579 | 0.338 | 0.595 | 0.431 | 0.254 |
| target_a_btc_eth_upside__elastic_net_logistic | target_a_btc_eth_upside | holdout | 0.665 | 0.156 | 0.700 | 0.255 | 0.236 |
| target_a_btc_eth_upside__random_forest | target_a_btc_eth_upside | development_cpcv | 0.563 | 0.310 | 0.774 | 0.442 | 0.233 |
| target_a_btc_eth_upside__random_forest | target_a_btc_eth_upside | holdout | 0.684 | 0.182 | 1.000 | 0.308 | 0.215 |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | development_cpcv | 0.499 | 0.300 | 0.214 | 0.250 | 0.226 |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | holdout | 0.752 | 0.444 | 0.400 | 0.421 | 0.121 |
| target_a_btc_eth_upside__xgboost | target_a_btc_eth_upside | development_cpcv | 0.526 | 0.385 | 0.238 | 0.294 | 0.221 |
| target_a_btc_eth_upside__xgboost | target_a_btc_eth_upside | holdout | 0.714 | 0.455 | 0.500 | 0.476 | 0.127 |
| target_b_eth_leadership__logistic_regression | target_b_eth_leadership | development_cpcv | 0.646 | 0.412 | 0.725 | 0.526 | 0.241 |
| target_b_eth_leadership__logistic_regression | target_b_eth_leadership | holdout | 0.579 | 0.263 | 0.625 | 0.370 | 0.221 |
| target_b_eth_leadership__elastic_net_logistic | target_b_eth_leadership | development_cpcv | 0.659 | 0.435 | 0.703 | 0.538 | 0.233 |
| target_b_eth_leadership__elastic_net_logistic | target_b_eth_leadership | holdout | 0.573 | 0.268 | 0.688 | 0.386 | 0.224 |
| target_b_eth_leadership__random_forest | target_b_eth_leadership | development_cpcv | 0.612 | 0.360 | 0.736 | 0.484 | 0.231 |
| target_b_eth_leadership__random_forest | target_b_eth_leadership | holdout | 0.641 | 0.259 | 0.875 | 0.400 | 0.215 |
| target_b_eth_leadership__gradient_boosting | target_b_eth_leadership | development_cpcv | 0.585 | 0.400 | 0.330 | 0.361 | 0.231 |
| target_b_eth_leadership__gradient_boosting | target_b_eth_leadership | holdout | 0.521 | 0.500 | 0.188 | 0.273 | 0.171 |
| target_b_eth_leadership__xgboost | target_b_eth_leadership | development_cpcv | 0.599 | 0.373 | 0.308 | 0.337 | 0.226 |
| target_b_eth_leadership__xgboost | target_b_eth_leadership | holdout | 0.533 | 0.429 | 0.188 | 0.261 | 0.171 |
| target_c_top20_leadership__logistic_regression | target_c_top20_leadership | development_cpcv | 0.360 | 0.191 | 0.408 | 0.260 | 0.282 |
| target_c_top20_leadership__logistic_regression | target_c_top20_leadership | holdout | 0.637 | 0.147 | 1.000 | 0.256 | 0.349 |
| target_c_top20_leadership__elastic_net_logistic | target_c_top20_leadership | development_cpcv | 0.345 | 0.181 | 0.394 | 0.248 | 0.276 |
| target_c_top20_leadership__elastic_net_logistic | target_c_top20_leadership | holdout | 0.622 | 0.147 | 1.000 | 0.256 | 0.328 |
| target_c_top20_leadership__random_forest | target_c_top20_leadership | development_cpcv | 0.431 | 0.220 | 0.648 | 0.329 | 0.239 |
| target_c_top20_leadership__random_forest | target_c_top20_leadership | holdout | 0.557 | 0.138 | 0.800 | 0.235 | 0.238 |
| target_c_top20_leadership__gradient_boosting | target_c_top20_leadership | development_cpcv | 0.401 | 0.220 | 0.127 | 0.161 | 0.217 |
| target_c_top20_leadership__gradient_boosting | target_c_top20_leadership | holdout | 0.554 | 0.000 | 0.000 | 0.000 | 0.141 |
| target_c_top20_leadership__xgboost | target_c_top20_leadership | development_cpcv | 0.410 | 0.357 | 0.070 | 0.118 | 0.213 |
| target_c_top20_leadership__xgboost | target_c_top20_leadership | holdout | 0.546 | 0.000 | 0.000 | 0.000 | 0.143 |
