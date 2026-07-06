# Predictive performance

All prediction models use lagged features only.  Development metrics are out-of-fold CPCV estimates; holdout metrics are reported after development selection.

## Selected trend models by target

| Target | Config | Model | Label threshold | Probability threshold |
|---|---|---|---|---|
| btc_eth_upward_trend | btc_eth_upward_trend__t1_0__elastic_net_logistic | elastic_net_logistic | 1.000 | 0.400 |
| btc_upward_trend | btc_upward_trend__t1_0__random_forest | random_forest | 1.000 | 0.400 |
| eth_upward_trend | eth_upward_trend__t1_0__elastic_net_logistic | elastic_net_logistic | 1.000 | 0.400 |
| eth_vs_btc_relative_trend | eth_vs_btc_relative_trend__t1_0__random_forest | random_forest | 1.000 | 0.400 |
| top20_upward_trend | top20_upward_trend__t1_0__elastic_net_logistic | elastic_net_logistic | 1.000 | 0.400 |

## Top development-CPCV predictive configurations

| Config | Target | Model | Label threshold | AUC | Precision | Recall | F1 | Brier | Selection score |
|---|---|---|---|---|---|---|---|---|---|
| eth_upward_trend__t1_0__elastic_net_logistic | eth_upward_trend | elastic_net_logistic | 1.000 | 0.646 | 0.651 | 0.795 | 0.716 | 0.238 | 0.479 |
| eth_upward_trend__t1_5__elastic_net_logistic | eth_upward_trend | elastic_net_logistic | 1.500 | 0.646 | 0.651 | 0.795 | 0.716 | 0.238 | 0.479 |
| eth_upward_trend__t2_0__elastic_net_logistic | eth_upward_trend | elastic_net_logistic | 2.000 | 0.646 | 0.651 | 0.795 | 0.716 | 0.238 | 0.479 |
| eth_upward_trend__t1_0__logistic_regression | eth_upward_trend | logistic_regression | 1.000 | 0.644 | 0.662 | 0.801 | 0.725 | 0.245 | 0.472 |
| eth_upward_trend__t1_5__logistic_regression | eth_upward_trend | logistic_regression | 1.500 | 0.644 | 0.662 | 0.801 | 0.725 | 0.245 | 0.472 |
| eth_upward_trend__t2_0__logistic_regression | eth_upward_trend | logistic_regression | 2.000 | 0.644 | 0.662 | 0.801 | 0.725 | 0.245 | 0.472 |
| eth_upward_trend__t2_0__sgd_classifier | eth_upward_trend | sgd_classifier | 2.000 | 0.653 | 0.657 | 0.807 | 0.724 | 0.262 | 0.463 |
| eth_upward_trend__t1_5__sgd_classifier | eth_upward_trend | sgd_classifier | 1.500 | 0.653 | 0.657 | 0.807 | 0.724 | 0.262 | 0.463 |
| eth_upward_trend__t1_0__sgd_classifier | eth_upward_trend | sgd_classifier | 1.000 | 0.653 | 0.657 | 0.807 | 0.724 | 0.262 | 0.463 |
| eth_vs_btc_relative_trend__t1_5__random_forest | eth_vs_btc_relative_trend | random_forest | 1.500 | 0.604 | 0.450 | 0.832 | 0.584 | 0.237 | 0.425 |
| eth_vs_btc_relative_trend__t2_0__random_forest | eth_vs_btc_relative_trend | random_forest | 2.000 | 0.604 | 0.450 | 0.832 | 0.584 | 0.237 | 0.425 |
| eth_vs_btc_relative_trend__t1_0__random_forest | eth_vs_btc_relative_trend | random_forest | 1.000 | 0.604 | 0.450 | 0.832 | 0.584 | 0.237 | 0.425 |
| btc_eth_upward_trend__t1_0__elastic_net_logistic | btc_eth_upward_trend | elastic_net_logistic | 1.000 | 0.602 | 0.656 | 0.806 | 0.723 | 0.254 | 0.420 |
| btc_eth_upward_trend__t1_5__elastic_net_logistic | btc_eth_upward_trend | elastic_net_logistic | 1.500 | 0.602 | 0.656 | 0.806 | 0.723 | 0.254 | 0.420 |
| btc_eth_upward_trend__t2_0__elastic_net_logistic | btc_eth_upward_trend | elastic_net_logistic | 2.000 | 0.602 | 0.656 | 0.806 | 0.723 | 0.254 | 0.420 |
| btc_eth_upward_trend__t2_0__logistic_regression | btc_eth_upward_trend | logistic_regression | 2.000 | 0.600 | 0.660 | 0.800 | 0.724 | 0.262 | 0.411 |
| btc_eth_upward_trend__t1_5__logistic_regression | btc_eth_upward_trend | logistic_regression | 1.500 | 0.600 | 0.660 | 0.800 | 0.724 | 0.262 | 0.411 |
| btc_eth_upward_trend__t1_0__logistic_regression | btc_eth_upward_trend | logistic_regression | 1.000 | 0.600 | 0.660 | 0.800 | 0.724 | 0.262 | 0.411 |
| eth_vs_btc_relative_trend__t1_5__elastic_net_logistic | eth_vs_btc_relative_trend | elastic_net_logistic | 1.500 | 0.612 | 0.512 | 0.555 | 0.532 | 0.255 | 0.409 |
| eth_vs_btc_relative_trend__t1_0__elastic_net_logistic | eth_vs_btc_relative_trend | elastic_net_logistic | 1.000 | 0.612 | 0.512 | 0.555 | 0.532 | 0.255 | 0.409 |
| eth_vs_btc_relative_trend__t2_0__elastic_net_logistic | eth_vs_btc_relative_trend | elastic_net_logistic | 2.000 | 0.612 | 0.512 | 0.555 | 0.532 | 0.255 | 0.409 |
| btc_eth_upward_trend__t1_5__sgd_classifier | btc_eth_upward_trend | sgd_classifier | 1.500 | 0.602 | 0.673 | 0.754 | 0.712 | 0.287 | 0.386 |
| btc_eth_upward_trend__t2_0__sgd_classifier | btc_eth_upward_trend | sgd_classifier | 2.000 | 0.602 | 0.673 | 0.754 | 0.712 | 0.287 | 0.386 |
| btc_eth_upward_trend__t1_0__sgd_classifier | btc_eth_upward_trend | sgd_classifier | 1.000 | 0.602 | 0.673 | 0.754 | 0.712 | 0.287 | 0.386 |
| eth_vs_btc_relative_trend__t1_5__logistic_regression | eth_vs_btc_relative_trend | logistic_regression | 1.500 | 0.602 | 0.496 | 0.529 | 0.512 | 0.268 | 0.386 |
| eth_vs_btc_relative_trend__t2_0__logistic_regression | eth_vs_btc_relative_trend | logistic_regression | 2.000 | 0.602 | 0.496 | 0.529 | 0.512 | 0.268 | 0.386 |
| eth_vs_btc_relative_trend__t1_0__logistic_regression | eth_vs_btc_relative_trend | logistic_regression | 1.000 | 0.602 | 0.496 | 0.529 | 0.512 | 0.268 | 0.386 |
| eth_upward_trend__t1_0__random_forest | eth_upward_trend | random_forest | 1.000 | 0.547 | 0.593 | 0.877 | 0.708 | 0.250 | 0.368 |
| eth_upward_trend__t1_5__random_forest | eth_upward_trend | random_forest | 1.500 | 0.547 | 0.593 | 0.877 | 0.708 | 0.250 | 0.368 |
| eth_upward_trend__t2_0__random_forest | eth_upward_trend | random_forest | 2.000 | 0.547 | 0.593 | 0.877 | 0.708 | 0.250 | 0.368 |

## Holdout metrics for selected target models

| Config | Target | Model | AUC | Precision | Recall | F1 | Brier | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| btc_upward_trend__t1_0__random_forest | btc_upward_trend | random_forest | 0.360 | 0.455 | 0.857 | 0.594 | 0.275 | 30 | 36 | 5 | 5 |
| eth_upward_trend__t1_0__elastic_net_logistic | eth_upward_trend | elastic_net_logistic | 0.616 | 0.462 | 0.774 | 0.578 | 0.262 | 24 | 28 | 7 | 17 |
| btc_eth_upward_trend__t1_0__elastic_net_logistic | btc_eth_upward_trend | elastic_net_logistic | 0.516 | 0.420 | 0.656 | 0.512 | 0.288 | 21 | 29 | 11 | 15 |
| eth_vs_btc_relative_trend__t1_0__random_forest | eth_vs_btc_relative_trend | random_forest | 0.609 | 0.411 | 0.821 | 0.548 | 0.231 | 23 | 33 | 5 | 15 |
| top20_upward_trend__t1_0__elastic_net_logistic | top20_upward_trend | elastic_net_logistic | 0.668 | 0.400 | 0.857 | 0.545 | 0.261 | 24 | 36 | 4 | 12 |

## Calibration

See `calibration.csv` for bin-level predicted probability versus realized event rate.
