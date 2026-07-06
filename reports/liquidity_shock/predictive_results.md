# Predictive results

Simple classifiers were tuned by CPCV inside the development period only. The
holdout rows below are out-of-sample evaluations of the selected development
model for each target.

| Target | Selected model | Split | Obs | Mean CPCV AUC | AUC | Precision | Recall | Brier |
|---|---|---|---|---|---|---|---|---|
| target_btc_eth_1w | gb_depth3 | development | 261 | 0.507 | 0.962 | 0.827 | 0.972 | 0.142 |
| target_btc_eth_1w | gb_depth3 | holdout | 76 | 0.507 | 0.556 | 0.500 | 0.694 | 0.269 |
| target_btc_eth_2w | logistic_C0.25 | development | 261 | 0.550 | 0.695 | 0.628 | 0.755 | 0.225 |
| target_btc_eth_2w | logistic_C0.25 | holdout | 75 | 0.550 | 0.527 | 0.467 | 0.600 | 0.266 |
| target_csm_spread_1w | gb_depth3 | development | 261 | 0.519 | 0.996 | 0.923 | 0.986 | 0.120 |
| target_csm_spread_1w | gb_depth3 | holdout | 76 | 0.519 | 0.539 | 0.581 | 0.658 | 0.262 |
| target_reversal_spread_1w | gb_depth2 | development | 261 | 0.517 | 0.910 | 0.873 | 0.590 | 0.171 |
| target_reversal_spread_1w | gb_depth2 | holdout | 76 | 0.517 | 0.628 | 0.593 | 0.421 | 0.246 |
| target_top10_basket_1w | gb_depth3 | development | 261 | 0.566 | 0.977 | 0.860 | 0.986 | 0.131 |
| target_top10_basket_1w | gb_depth3 | holdout | 76 | 0.566 | 0.466 | 0.483 | 0.744 | 0.292 |
