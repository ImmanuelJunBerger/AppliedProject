# Development metrics

Development-only CPCV selection ranking:

| Candidate | Allocation | Multiplier | Selection score | Median fold Sharpe | Worst fold | Positive folds | Dev Sharpe | Dev turnover | Dev exposure |
|---|---|---|---|---|---|---|---|---|---|
| balanced_gradient_boosting_m1_0 | balanced_btc_eth | 1.000 | 0.743 | 0.724 | -0.564 | 80.00% | 0.800 | 8.639 | 32.87% |
| balanced_gradient_boosting_m1_5 | balanced_btc_eth | 1.500 | 0.743 | 0.724 | -0.564 | 80.00% | 0.800 | 8.639 | 32.87% |
| balanced_gradient_boosting_m2_0 | balanced_btc_eth | 2.000 | 0.743 | 0.724 | -0.564 | 80.00% | 0.800 | 8.639 | 32.87% |
| dynamic_tilt_gradient_boosting_m1_0 | dynamic_btc_eth_tilt | 1.000 | 0.740 | 0.740 | -0.643 | 80.00% | 0.754 | 10.248 | 32.87% |
| dynamic_tilt_gradient_boosting_m1_5 | dynamic_btc_eth_tilt | 1.500 | 0.740 | 0.740 | -0.643 | 80.00% | 0.754 | 10.248 | 32.87% |
| dynamic_tilt_gradient_boosting_m2_0 | dynamic_btc_eth_tilt | 2.000 | 0.740 | 0.740 | -0.643 | 80.00% | 0.754 | 10.248 | 32.87% |
| balanced_xgboost_m1_0 | balanced_btc_eth | 1.000 | 0.732 | 0.724 | -0.607 | 80.00% | 0.789 | 8.366 | 32.79% |
| balanced_xgboost_m1_5 | balanced_btc_eth | 1.500 | 0.732 | 0.724 | -0.607 | 80.00% | 0.789 | 8.366 | 32.79% |
| balanced_xgboost_m2_0 | balanced_btc_eth | 2.000 | 0.732 | 0.724 | -0.607 | 80.00% | 0.789 | 8.366 | 32.79% |
| dynamic_tilt_xgboost_m1_0 | dynamic_btc_eth_tilt | 1.000 | 0.665 | 0.684 | -0.717 | 80.00% | 0.695 | 10.339 | 32.79% |
| dynamic_tilt_xgboost_m1_5 | dynamic_btc_eth_tilt | 1.500 | 0.665 | 0.684 | -0.717 | 80.00% | 0.695 | 10.339 | 32.79% |
| dynamic_tilt_xgboost_m2_0 | dynamic_btc_eth_tilt | 2.000 | 0.665 | 0.684 | -0.717 | 80.00% | 0.695 | 10.339 | 32.79% |
| balanced_logistic_regression_m0_5 | balanced_btc_eth | 0.500 | 0.662 | 0.639 | -0.492 | 73.33% | 0.721 | 6.911 | 29.47% |
| balanced_elastic_net_logistic_m0_5 | balanced_btc_eth | 0.500 | 0.662 | 0.639 | -0.492 | 73.33% | 0.721 | 6.911 | 29.47% |
| balanced_random_forest_m0_5 | balanced_btc_eth | 0.500 | 0.662 | 0.639 | -0.492 | 73.33% | 0.721 | 6.911 | 29.47% |
| balanced_gradient_boosting_m0_5 | balanced_btc_eth | 0.500 | 0.662 | 0.639 | -0.492 | 73.33% | 0.721 | 6.911 | 29.47% |
| balanced_xgboost_m0_5 | balanced_btc_eth | 0.500 | 0.662 | 0.639 | -0.492 | 73.33% | 0.721 | 6.911 | 29.47% |
| dynamic_tilt_elastic_net_logistic_m0_5 | dynamic_btc_eth_tilt | 0.500 | 0.648 | 0.627 | -0.502 | 73.33% | 0.766 | 9.130 | 29.47% |
| dynamic_tilt_logistic_regression_m0_5 | dynamic_btc_eth_tilt | 0.500 | 0.644 | 0.627 | -0.517 | 73.33% | 0.761 | 9.348 | 29.47% |
| dynamic_tilt_gradient_boosting_m0_5 | dynamic_btc_eth_tilt | 0.500 | 0.626 | 0.622 | -0.571 | 73.33% | 0.674 | 8.693 | 29.47% |
| dynamic_tilt_elastic_net_logistic_m1_0 | dynamic_btc_eth_tilt | 1.000 | 0.550 | 0.559 | -0.622 | 73.33% | 0.716 | 11.876 | 36.45% |
| dynamic_tilt_elastic_net_logistic_m1_5 | dynamic_btc_eth_tilt | 1.500 | 0.550 | 0.559 | -0.622 | 73.33% | 0.716 | 11.876 | 36.45% |
| dynamic_tilt_elastic_net_logistic_m2_0 | dynamic_btc_eth_tilt | 2.000 | 0.550 | 0.559 | -0.622 | 73.33% | 0.716 | 11.876 | 36.45% |
| dynamic_tilt_random_forest_m0_5 | dynamic_btc_eth_tilt | 0.500 | 0.547 | 0.530 | -0.518 | 73.33% | 0.673 | 8.693 | 29.47% |
| dynamic_tilt_xgboost_m0_5 | dynamic_btc_eth_tilt | 0.500 | 0.542 | 0.548 | -0.610 | 73.33% | 0.624 | 9.202 | 29.47% |
| dynamic_tilt_logistic_regression_m1_0 | dynamic_btc_eth_tilt | 1.000 | 0.540 | 0.559 | -0.661 | 73.33% | 0.750 | 11.921 | 36.45% |
| dynamic_tilt_logistic_regression_m1_5 | dynamic_btc_eth_tilt | 1.500 | 0.540 | 0.559 | -0.661 | 73.33% | 0.750 | 11.921 | 36.45% |
| dynamic_tilt_logistic_regression_m2_0 | dynamic_btc_eth_tilt | 2.000 | 0.540 | 0.559 | -0.661 | 73.33% | 0.750 | 11.921 | 36.45% |
| balanced_random_forest_m1_0 | balanced_btc_eth | 1.000 | 0.459 | 0.436 | -0.492 | 73.33% | 0.682 | 11.457 | 41.77% |
| balanced_random_forest_m1_5 | balanced_btc_eth | 1.500 | 0.459 | 0.436 | -0.492 | 73.33% | 0.682 | 11.457 | 41.77% |
| balanced_random_forest_m2_0 | balanced_btc_eth | 2.000 | 0.459 | 0.436 | -0.492 | 73.33% | 0.682 | 11.457 | 41.77% |
| balanced_elastic_net_logistic_m1_0 | balanced_btc_eth | 1.000 | 0.434 | 0.444 | -0.629 | 73.33% | 0.653 | 10.366 | 36.45% |
| balanced_elastic_net_logistic_m1_5 | balanced_btc_eth | 1.500 | 0.434 | 0.444 | -0.629 | 73.33% | 0.653 | 10.366 | 36.45% |
| balanced_elastic_net_logistic_m2_0 | balanced_btc_eth | 2.000 | 0.434 | 0.444 | -0.629 | 73.33% | 0.653 | 10.366 | 36.45% |
| balanced_logistic_regression_m1_0 | balanced_btc_eth | 1.000 | 0.429 | 0.444 | -0.648 | 73.33% | 0.691 | 10.184 | 36.45% |
| balanced_logistic_regression_m1_5 | balanced_btc_eth | 1.500 | 0.429 | 0.444 | -0.648 | 73.33% | 0.691 | 10.184 | 36.45% |
| balanced_logistic_regression_m2_0 | balanced_btc_eth | 2.000 | 0.429 | 0.444 | -0.648 | 73.33% | 0.691 | 10.184 | 36.45% |
| dynamic_tilt_random_forest_m1_0 | dynamic_btc_eth_tilt | 1.000 | 0.303 | 0.309 | -0.515 | 73.33% | 0.619 | 12.476 | 41.77% |
| dynamic_tilt_random_forest_m1_5 | dynamic_btc_eth_tilt | 1.500 | 0.303 | 0.309 | -0.515 | 73.33% | 0.619 | 12.476 | 41.77% |
| dynamic_tilt_random_forest_m2_0 | dynamic_btc_eth_tilt | 2.000 | 0.303 | 0.309 | -0.515 | 73.33% | 0.619 | 12.476 | 41.77% |
