# Predictive performance

All prediction models were selected using development CPCV only.

## Development-CPCV ranking

| Family | Config | Model | Selection score | AUC | Precision | Recall | F1 | Brier |
|---|---|---|---|---|---|---|---|---|
| transition | risk_off_to_risk_on_2_4w__gradient_boosting | gradient_boosting | 0.565 | 0.700 | 0.391 | 0.161 | 0.228 | 0.157 |
| transition | risk_off_to_risk_on_2_4w__xgboost | xgboost | 0.549 | 0.684 | 0.355 | 0.196 | 0.253 | 0.160 |
| transition | risk_off_to_risk_on_2_4w__random_forest | random_forest | 0.545 | 0.708 | 0.363 | 0.661 | 0.468 | 0.209 |
| transition | risk_off_to_risk_on_2_4w__elastic_net_logistic | elastic_net_logistic | 0.448 | 0.651 | 0.258 | 0.821 | 0.393 | 0.242 |
| transition | risk_off_to_risk_on_2_4w__logistic_regression | logistic_regression | 0.435 | 0.642 | 0.259 | 0.804 | 0.391 | 0.246 |
| cross_sectional | top20_top_quintile_30d__xgboost | xgboost | 0.412 | 0.571 | 0.000 | 0.000 | 0.000 | 0.159 |
| cross_sectional | top20_top_quintile_30d__gradient_boosting | gradient_boosting | 0.399 | 0.559 | 0.111 | 0.001 | 0.002 | 0.160 |
| relative | eth_leads_btc_30d_gt_5__elastic_net_logistic | elastic_net_logistic | 0.397 | 0.603 | 0.359 | 0.835 | 0.502 | 0.256 |
| relative | eth_leads_btc_30d_gt_5__logistic_regression | logistic_regression | 0.384 | 0.595 | 0.362 | 0.800 | 0.498 | 0.260 |
| cross_sectional | top20_top_quintile_30d__elastic_net_logistic | elastic_net_logistic | 0.350 | 0.563 | 0.202 | 0.915 | 0.331 | 0.246 |
| cross_sectional | top20_top_quintile_30d__logistic_regression | logistic_regression | 0.350 | 0.562 | 0.202 | 0.910 | 0.330 | 0.246 |
| cross_sectional | top20_top_quintile_30d__random_forest | random_forest | 0.347 | 0.558 | 0.200 | 1.000 | 0.334 | 0.244 |
| relative | btc_leads_eth_30d_gt_5__elastic_net_logistic | elastic_net_logistic | 0.337 | 0.537 | 0.354 | 0.813 | 0.493 | 0.249 |
| relative | eth_leads_btc_30d_gt_5__random_forest | random_forest | 0.337 | 0.535 | 0.343 | 0.847 | 0.488 | 0.247 |
| relative | btc_leads_eth_30d_gt_5__logistic_regression | logistic_regression | 0.333 | 0.535 | 0.362 | 0.791 | 0.497 | 0.251 |
| convex | btc_30d_gt_15__random_forest | random_forest | 0.292 | 0.490 | 0.259 | 0.500 | 0.341 | 0.232 |
| relative | btc_leads_eth_30d_gt_5__gradient_boosting | gradient_boosting | 0.283 | 0.495 | 0.348 | 0.341 | 0.344 | 0.247 |
| relative | btc_leads_eth_30d_gt_5__random_forest | random_forest | 0.275 | 0.484 | 0.332 | 0.747 | 0.459 | 0.255 |
| convex | btc_eth_50_50_30d_gt_15__elastic_net_logistic | elastic_net_logistic | 0.272 | 0.494 | 0.293 | 0.500 | 0.369 | 0.259 |
| convex | btc_eth_50_50_30d_gt_15__logistic_regression | logistic_regression | 0.259 | 0.487 | 0.294 | 0.488 | 0.367 | 0.264 |
| relative | btc_leads_eth_30d_gt_5__xgboost | xgboost | 0.257 | 0.472 | 0.358 | 0.319 | 0.337 | 0.249 |
| convex | btc_30d_gt_15__elastic_net_logistic | elastic_net_logistic | 0.255 | 0.480 | 0.263 | 0.473 | 0.338 | 0.259 |
| convex | btc_eth_50_50_30d_gt_15__random_forest | random_forest | 0.254 | 0.459 | 0.288 | 0.573 | 0.384 | 0.243 |
| convex | btc_30d_gt_15__logistic_regression | logistic_regression | 0.247 | 0.477 | 0.271 | 0.473 | 0.345 | 0.264 |
| convex | eth_30d_gt_20__elastic_net_logistic | elastic_net_logistic | 0.242 | 0.467 | 0.263 | 0.603 | 0.367 | 0.262 |
| convex | eth_30d_gt_20__logistic_regression | logistic_regression | 0.233 | 0.462 | 0.261 | 0.562 | 0.357 | 0.265 |
| relative | eth_leads_btc_30d_gt_5__xgboost | xgboost | 0.228 | 0.451 | 0.304 | 0.282 | 0.293 | 0.252 |
| convex | btc_eth_50_50_30d_gt_15__xgboost | xgboost | 0.215 | 0.441 | 0.279 | 0.146 | 0.192 | 0.245 |
| convex | btc_30d_gt_15__xgboost | xgboost | 0.211 | 0.426 | 0.290 | 0.122 | 0.171 | 0.232 |
| relative | eth_leads_btc_30d_gt_5__gradient_boosting | gradient_boosting | 0.210 | 0.442 | 0.259 | 0.247 | 0.253 | 0.258 |
| convex | eth_30d_gt_20__random_forest | random_forest | 0.203 | 0.412 | 0.237 | 0.548 | 0.331 | 0.242 |
| convex | btc_30d_gt_15__gradient_boosting | gradient_boosting | 0.203 | 0.419 | 0.321 | 0.122 | 0.176 | 0.233 |
| convex | btc_eth_50_50_30d_gt_15__gradient_boosting | gradient_boosting | 0.202 | 0.431 | 0.289 | 0.134 | 0.183 | 0.247 |
| convex | eth_30d_gt_20__xgboost | xgboost | 0.142 | 0.373 | 0.129 | 0.055 | 0.077 | 0.239 |
| convex | eth_30d_gt_20__gradient_boosting | gradient_boosting | 0.134 | 0.368 | 0.133 | 0.055 | 0.078 | 0.242 |

## Holdout predictive diagnostics

| Family | Config | AUC | Precision | Recall | F1 | Brier | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|---|---|
| convex | btc_30d_gt_15__logistic_regression | 0.385 | 0.043 | 0.400 | 0.078 | 0.248 | 2 | 44 | 3 | 24 |
| convex | btc_30d_gt_15__elastic_net_logistic | 0.424 | 0.043 | 0.400 | 0.078 | 0.237 | 2 | 44 | 3 | 24 |
| convex | btc_30d_gt_15__random_forest | 0.826 | 0.122 | 1.000 | 0.217 | 0.186 | 5 | 36 | 0 | 32 |
| convex | btc_30d_gt_15__gradient_boosting | 0.882 | 0.214 | 0.600 | 0.316 | 0.089 | 3 | 11 | 2 | 57 |
| convex | btc_30d_gt_15__xgboost | 0.756 | 0.167 | 0.600 | 0.261 | 0.109 | 3 | 15 | 2 | 53 |
| convex | eth_30d_gt_20__logistic_regression | 0.563 | 0.156 | 0.909 | 0.267 | 0.249 | 10 | 54 | 1 | 8 |
| convex | eth_30d_gt_20__elastic_net_logistic | 0.585 | 0.156 | 0.909 | 0.267 | 0.240 | 10 | 54 | 1 | 8 |
| convex | eth_30d_gt_20__random_forest | 0.613 | 0.174 | 0.727 | 0.281 | 0.197 | 8 | 38 | 3 | 24 |
| convex | eth_30d_gt_20__gradient_boosting | 0.598 | 0.500 | 0.091 | 0.154 | 0.133 | 1 | 1 | 10 | 61 |
| convex | eth_30d_gt_20__xgboost | 0.563 | 0.000 | 0.000 | 0.000 | 0.138 | 0 | 2 | 11 | 60 |
| convex | btc_eth_50_50_30d_gt_15__logistic_regression | 0.590 | 0.149 | 0.700 | 0.246 | 0.243 | 7 | 40 | 3 | 23 |
| convex | btc_eth_50_50_30d_gt_15__elastic_net_logistic | 0.638 | 0.154 | 0.800 | 0.258 | 0.234 | 8 | 44 | 2 | 19 |
| convex | btc_eth_50_50_30d_gt_15__random_forest | 0.781 | 0.196 | 0.900 | 0.321 | 0.194 | 9 | 37 | 1 | 26 |
| convex | btc_eth_50_50_30d_gt_15__gradient_boosting | 0.810 | 0.357 | 0.500 | 0.417 | 0.123 | 5 | 9 | 5 | 54 |
| convex | btc_eth_50_50_30d_gt_15__xgboost | 0.784 | 0.368 | 0.700 | 0.483 | 0.129 | 7 | 12 | 3 | 51 |
| relative | eth_leads_btc_30d_gt_5__logistic_regression | 0.636 | 0.271 | 0.812 | 0.406 | 0.215 | 13 | 35 | 3 | 22 |
| relative | eth_leads_btc_30d_gt_5__elastic_net_logistic | 0.659 | 0.271 | 0.812 | 0.406 | 0.212 | 13 | 35 | 3 | 22 |
| relative | eth_leads_btc_30d_gt_5__random_forest | 0.703 | 0.270 | 0.625 | 0.377 | 0.182 | 10 | 27 | 6 | 30 |
| relative | eth_leads_btc_30d_gt_5__gradient_boosting | 0.647 | 0.600 | 0.188 | 0.286 | 0.161 | 3 | 2 | 13 | 55 |
| relative | eth_leads_btc_30d_gt_5__xgboost | 0.663 | 0.500 | 0.188 | 0.273 | 0.159 | 3 | 3 | 13 | 54 |
| relative | btc_leads_eth_30d_gt_5__logistic_regression | 0.671 | 0.462 | 0.909 | 0.612 | 0.233 | 30 | 35 | 3 | 5 |
| relative | btc_leads_eth_30d_gt_5__elastic_net_logistic | 0.657 | 0.457 | 0.970 | 0.621 | 0.237 | 32 | 38 | 1 | 2 |
| relative | btc_leads_eth_30d_gt_5__random_forest | 0.649 | 0.470 | 0.939 | 0.626 | 0.237 | 31 | 35 | 2 | 5 |
| relative | btc_leads_eth_30d_gt_5__gradient_boosting | 0.546 | 0.464 | 0.394 | 0.426 | 0.257 | 13 | 15 | 20 | 25 |
| relative | btc_leads_eth_30d_gt_5__xgboost | 0.539 | 0.478 | 0.333 | 0.393 | 0.254 | 11 | 12 | 22 | 28 |
| transition | risk_off_to_risk_on_2_4w__logistic_regression | 0.677 | 0.239 | 0.688 | 0.355 | 0.213 | 11 | 35 | 5 | 22 |
| transition | risk_off_to_risk_on_2_4w__elastic_net_logistic | 0.684 | 0.239 | 0.688 | 0.355 | 0.211 | 11 | 35 | 5 | 22 |
| transition | risk_off_to_risk_on_2_4w__random_forest | 0.627 | 0.364 | 0.500 | 0.421 | 0.202 | 8 | 14 | 8 | 43 |
| transition | risk_off_to_risk_on_2_4w__gradient_boosting | 0.573 | 0.714 | 0.312 | 0.435 | 0.163 | 5 | 2 | 11 | 55 |
| transition | risk_off_to_risk_on_2_4w__xgboost | 0.586 | 0.714 | 0.312 | 0.435 | 0.164 | 5 | 2 | 11 | 55 |
| cross_sectional | top20_top_quintile_30d__logistic_regression | 0.586 | 0.203 | 0.986 | 0.337 | 0.242 | 288 | 1129 | 4 | 39 |
| cross_sectional | top20_top_quintile_30d__elastic_net_logistic | 0.587 | 0.203 | 0.986 | 0.337 | 0.242 | 288 | 1130 | 4 | 38 |
| cross_sectional | top20_top_quintile_30d__random_forest | 0.633 | 0.200 | 1.000 | 0.333 | 0.238 | 292 | 1168 | 0 | 0 |
| cross_sectional | top20_top_quintile_30d__gradient_boosting | 0.601 | 0.000 | 0.000 | 0.000 | 0.157 | 0 | 0 | 292 | 1168 |
| cross_sectional | top20_top_quintile_30d__xgboost | 0.626 | 0.000 | 0.000 | 0.000 | 0.155 | 0 | 0 | 292 | 1168 |
