# Predictive performance

Prediction models were selected on development CPCV only. Holdout metrics are
diagnostic and were not used for model selection.

## Development selection

| Config | Target | Model | Selection score | AUC | Precision | Recall | F1 | Brier |
|---|---|---|---|---|---|---|---|---|
| eth_leads_btc_30d_gt_5__elastic_net_logistic | eth_leads_btc_30d_gt_5 | elastic_net_logistic | 0.414 | 0.616 | 0.372 | 0.859 | 0.520 | 0.254 |
| eth_leads_btc_30d_gt_5__logistic_regression | eth_leads_btc_30d_gt_5 | logistic_regression | 0.400 | 0.607 | 0.374 | 0.824 | 0.515 | 0.258 |
| eth_leads_btc_30d_gt_5__random_forest | eth_leads_btc_30d_gt_5 | random_forest | 0.333 | 0.532 | 0.343 | 0.824 | 0.484 | 0.247 |
| btc_30d_gt_15__random_forest | btc_30d_gt_15 | random_forest | 0.300 | 0.493 | 0.283 | 0.527 | 0.368 | 0.230 |
| btc_eth_50_50_30d_gt_15__elastic_net_logistic | btc_eth_50_50_30d_gt_15 | elastic_net_logistic | 0.300 | 0.519 | 0.307 | 0.524 | 0.387 | 0.258 |
| btc_eth_50_50_30d_gt_15__logistic_regression | btc_eth_50_50_30d_gt_15 | logistic_regression | 0.288 | 0.514 | 0.298 | 0.476 | 0.366 | 0.263 |
| eth_30d_gt_20__elastic_net_logistic | eth_30d_gt_20 | elastic_net_logistic | 0.269 | 0.492 | 0.275 | 0.630 | 0.383 | 0.262 |
| btc_eth_50_50_30d_gt_15__random_forest | btc_eth_50_50_30d_gt_15 | random_forest | 0.268 | 0.470 | 0.292 | 0.549 | 0.381 | 0.241 |
| btc_30d_gt_15__elastic_net_logistic | btc_30d_gt_15 | elastic_net_logistic | 0.267 | 0.492 | 0.258 | 0.459 | 0.330 | 0.258 |
| btc_30d_gt_15__logistic_regression | btc_30d_gt_15 | logistic_regression | 0.264 | 0.492 | 0.279 | 0.459 | 0.347 | 0.263 |
| eth_30d_gt_20__logistic_regression | eth_30d_gt_20 | logistic_regression | 0.261 | 0.489 | 0.274 | 0.589 | 0.374 | 0.265 |
| btc_30d_gt_15__xgboost | btc_30d_gt_15 | xgboost | 0.238 | 0.447 | 0.357 | 0.135 | 0.196 | 0.228 |
| btc_eth_50_50_30d_gt_15__xgboost | btc_eth_50_50_30d_gt_15 | xgboost | 0.218 | 0.443 | 0.308 | 0.146 | 0.198 | 0.245 |
| eth_30d_gt_20__random_forest | eth_30d_gt_20 | random_forest | 0.218 | 0.424 | 0.245 | 0.548 | 0.339 | 0.240 |
| btc_eth_50_50_30d_gt_15__gradient_boosting | btc_eth_50_50_30d_gt_15 | gradient_boosting | 0.218 | 0.443 | 0.306 | 0.134 | 0.186 | 0.244 |
| eth_leads_btc_30d_gt_5__xgboost | eth_leads_btc_30d_gt_5 | xgboost | 0.215 | 0.440 | 0.292 | 0.247 | 0.268 | 0.252 |
| btc_30d_gt_15__gradient_boosting | btc_30d_gt_15 | gradient_boosting | 0.214 | 0.427 | 0.333 | 0.135 | 0.192 | 0.232 |
| top10_30d_gt_20__random_forest | top10_30d_gt_20 | random_forest | 0.210 | 0.419 | 0.226 | 0.529 | 0.317 | 0.240 |
| eth_leads_btc_30d_gt_5__gradient_boosting | eth_leads_btc_30d_gt_5 | gradient_boosting | 0.206 | 0.435 | 0.303 | 0.235 | 0.265 | 0.255 |
| top10_30d_gt_20__gradient_boosting | top10_30d_gt_20 | gradient_boosting | 0.190 | 0.400 | 0.242 | 0.118 | 0.158 | 0.226 |
| top10_30d_gt_20__xgboost | top10_30d_gt_20 | xgboost | 0.174 | 0.390 | 0.172 | 0.074 | 0.103 | 0.225 |
| eth_30d_gt_20__xgboost | eth_30d_gt_20 | xgboost | 0.165 | 0.392 | 0.300 | 0.041 | 0.072 | 0.234 |
| top10_30d_gt_20__elastic_net_logistic | top10_30d_gt_20 | elastic_net_logistic | 0.158 | 0.414 | 0.221 | 0.529 | 0.312 | 0.287 |
| eth_30d_gt_20__gradient_boosting | eth_30d_gt_20 | gradient_boosting | 0.154 | 0.386 | 0.111 | 0.041 | 0.060 | 0.238 |
| top10_30d_gt_20__logistic_regression | top10_30d_gt_20 | logistic_regression | 0.136 | 0.401 | 0.217 | 0.500 | 0.302 | 0.296 |

## All prediction metrics

| Config | Split | AUC | Precision | Recall | F1 | Brier | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|---|---|
| btc_30d_gt_15__logistic_regression | development_cpcv | 0.492 | 0.279 | 0.459 | 0.347 | 0.263 | 34 | 88 | 40 | 99 |
| btc_30d_gt_15__logistic_regression | holdout | 0.385 | 0.043 | 0.400 | 0.078 | 0.253 | 2 | 44 | 3 | 24 |
| btc_30d_gt_15__elastic_net_logistic | development_cpcv | 0.492 | 0.258 | 0.459 | 0.330 | 0.258 | 34 | 98 | 40 | 89 |
| btc_30d_gt_15__elastic_net_logistic | holdout | 0.432 | 0.043 | 0.400 | 0.077 | 0.243 | 2 | 45 | 3 | 23 |
| btc_30d_gt_15__random_forest | development_cpcv | 0.493 | 0.283 | 0.527 | 0.368 | 0.230 | 39 | 99 | 35 | 88 |
| btc_30d_gt_15__random_forest | holdout | 0.782 | 0.122 | 1.000 | 0.217 | 0.191 | 5 | 36 | 0 | 32 |
| btc_30d_gt_15__gradient_boosting | development_cpcv | 0.427 | 0.333 | 0.135 | 0.192 | 0.232 | 10 | 20 | 64 | 167 |
| btc_30d_gt_15__gradient_boosting | holdout | 0.838 | 0.200 | 0.600 | 0.300 | 0.102 | 3 | 12 | 2 | 56 |
| btc_30d_gt_15__xgboost | development_cpcv | 0.447 | 0.357 | 0.135 | 0.196 | 0.228 | 10 | 18 | 64 | 169 |
| btc_30d_gt_15__xgboost | holdout | 0.738 | 0.111 | 0.400 | 0.174 | 0.116 | 2 | 16 | 3 | 52 |
| eth_30d_gt_20__logistic_regression | development_cpcv | 0.489 | 0.274 | 0.589 | 0.374 | 0.265 | 43 | 114 | 30 | 74 |
| eth_30d_gt_20__logistic_regression | holdout | 0.579 | 0.156 | 0.909 | 0.267 | 0.254 | 10 | 54 | 1 | 8 |
| eth_30d_gt_20__elastic_net_logistic | development_cpcv | 0.492 | 0.275 | 0.630 | 0.383 | 0.262 | 46 | 121 | 27 | 67 |
| eth_30d_gt_20__elastic_net_logistic | holdout | 0.597 | 0.154 | 0.909 | 0.263 | 0.246 | 10 | 55 | 1 | 7 |
| eth_30d_gt_20__random_forest | development_cpcv | 0.424 | 0.245 | 0.548 | 0.339 | 0.240 | 40 | 123 | 33 | 65 |
| eth_30d_gt_20__random_forest | holdout | 0.616 | 0.182 | 0.727 | 0.291 | 0.198 | 8 | 36 | 3 | 26 |
| eth_30d_gt_20__gradient_boosting | development_cpcv | 0.386 | 0.111 | 0.041 | 0.060 | 0.238 | 3 | 24 | 70 | 164 |
| eth_30d_gt_20__gradient_boosting | holdout | 0.674 | 0.500 | 0.091 | 0.154 | 0.127 | 1 | 1 | 10 | 61 |
| eth_30d_gt_20__xgboost | development_cpcv | 0.392 | 0.300 | 0.041 | 0.072 | 0.234 | 3 | 7 | 70 | 181 |
| eth_30d_gt_20__xgboost | holdout | 0.635 | 0.000 | 0.000 | 0.000 | 0.134 | 0 | 0 | 11 | 62 |
| btc_eth_50_50_30d_gt_15__logistic_regression | development_cpcv | 0.514 | 0.298 | 0.476 | 0.366 | 0.263 | 39 | 92 | 43 | 87 |
| btc_eth_50_50_30d_gt_15__logistic_regression | holdout | 0.600 | 0.146 | 0.700 | 0.241 | 0.248 | 7 | 41 | 3 | 22 |
| btc_eth_50_50_30d_gt_15__elastic_net_logistic | development_cpcv | 0.519 | 0.307 | 0.524 | 0.387 | 0.258 | 43 | 97 | 39 | 82 |
| btc_eth_50_50_30d_gt_15__elastic_net_logistic | holdout | 0.651 | 0.145 | 0.800 | 0.246 | 0.240 | 8 | 47 | 2 | 16 |
| btc_eth_50_50_30d_gt_15__random_forest | development_cpcv | 0.470 | 0.292 | 0.549 | 0.381 | 0.241 | 45 | 109 | 37 | 70 |
| btc_eth_50_50_30d_gt_15__random_forest | holdout | 0.792 | 0.191 | 0.900 | 0.316 | 0.199 | 9 | 38 | 1 | 25 |
| btc_eth_50_50_30d_gt_15__gradient_boosting | development_cpcv | 0.443 | 0.306 | 0.134 | 0.186 | 0.244 | 11 | 25 | 71 | 154 |
| btc_eth_50_50_30d_gt_15__gradient_boosting | holdout | 0.854 | 0.353 | 0.600 | 0.444 | 0.126 | 6 | 11 | 4 | 52 |
| btc_eth_50_50_30d_gt_15__xgboost | development_cpcv | 0.443 | 0.308 | 0.146 | 0.198 | 0.245 | 12 | 27 | 70 | 152 |
| btc_eth_50_50_30d_gt_15__xgboost | holdout | 0.830 | 0.364 | 0.800 | 0.500 | 0.134 | 8 | 14 | 2 | 49 |
| top10_30d_gt_20__logistic_regression | development_cpcv | 0.401 | 0.217 | 0.500 | 0.302 | 0.296 | 34 | 123 | 34 | 70 |
| top10_30d_gt_20__logistic_regression | holdout | 0.744 | 0.070 | 0.800 | 0.129 | 0.229 | 4 | 53 | 1 | 15 |
| top10_30d_gt_20__elastic_net_logistic | development_cpcv | 0.414 | 0.221 | 0.529 | 0.312 | 0.287 | 36 | 127 | 32 | 66 |
| top10_30d_gt_20__elastic_net_logistic | holdout | 0.750 | 0.081 | 1.000 | 0.149 | 0.224 | 5 | 57 | 0 | 11 |
| top10_30d_gt_20__random_forest | development_cpcv | 0.419 | 0.226 | 0.529 | 0.317 | 0.240 | 36 | 123 | 32 | 70 |
| top10_30d_gt_20__random_forest | holdout | 0.685 | 0.098 | 1.000 | 0.179 | 0.210 | 5 | 46 | 0 | 22 |
| top10_30d_gt_20__gradient_boosting | development_cpcv | 0.400 | 0.242 | 0.118 | 0.158 | 0.226 | 8 | 25 | 60 | 168 |
| top10_30d_gt_20__gradient_boosting | holdout | 0.782 | 0.200 | 0.400 | 0.267 | 0.099 | 2 | 8 | 3 | 60 |
| top10_30d_gt_20__xgboost | development_cpcv | 0.390 | 0.172 | 0.074 | 0.103 | 0.225 | 5 | 24 | 63 | 169 |
| top10_30d_gt_20__xgboost | holdout | 0.624 | 0.059 | 0.200 | 0.091 | 0.122 | 1 | 16 | 4 | 52 |
| eth_leads_btc_30d_gt_5__logistic_regression | development_cpcv | 0.607 | 0.374 | 0.824 | 0.515 | 0.258 | 70 | 117 | 15 | 59 |
| eth_leads_btc_30d_gt_5__logistic_regression | holdout | 0.658 | 0.260 | 0.812 | 0.394 | 0.214 | 13 | 37 | 3 | 20 |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | development_cpcv | 0.616 | 0.372 | 0.859 | 0.520 | 0.254 | 73 | 123 | 12 | 53 |
| eth_leads_btc_30d_gt_5__elastic_net_logistic | holdout | 0.677 | 0.275 | 0.875 | 0.418 | 0.211 | 14 | 37 | 2 | 20 |
| eth_leads_btc_30d_gt_5__random_forest | development_cpcv | 0.532 | 0.343 | 0.824 | 0.484 | 0.247 | 70 | 134 | 15 | 42 |
| eth_leads_btc_30d_gt_5__random_forest | holdout | 0.682 | 0.270 | 0.625 | 0.377 | 0.184 | 10 | 27 | 6 | 30 |
| eth_leads_btc_30d_gt_5__gradient_boosting | development_cpcv | 0.435 | 0.303 | 0.235 | 0.265 | 0.255 | 20 | 46 | 65 | 130 |
| eth_leads_btc_30d_gt_5__gradient_boosting | holdout | 0.714 | 0.500 | 0.188 | 0.273 | 0.153 | 3 | 3 | 13 | 54 |
| eth_leads_btc_30d_gt_5__xgboost | development_cpcv | 0.440 | 0.292 | 0.247 | 0.268 | 0.252 | 21 | 51 | 64 | 125 |
| eth_leads_btc_30d_gt_5__xgboost | holdout | 0.660 | 0.500 | 0.188 | 0.273 | 0.160 | 3 | 3 | 13 | 54 |
