# Feature research

Feature validation uses development data only for classification. Holdout
columns are diagnostics only and were not used for feature selection.

## Target diagnostics

| Target | Split | Obs | Positive | Prevalence |
|---|---|---|---|---|
| target_a_btc_30d_upside | development | 287 | 77 | 26.83% |
| target_a_btc_30d_upside | holdout | 73 | 5 | 6.85% |
| target_b_eth_30d_upside | development | 287 | 75 | 26.13% |
| target_b_eth_30d_upside | holdout | 73 | 11 | 15.07% |
| target_c_btc_eth_50_50_30d_upside | development | 287 | 84 | 29.27% |
| target_c_btc_eth_50_50_30d_upside | holdout | 73 | 10 | 13.70% |
| target_d_eth_beats_btc_30d | development | 287 | 91 | 31.71% |
| target_d_eth_beats_btc_30d | holdout | 73 | 16 | 21.92% |
| target_e_top20_leadership | development | 287 | 71 | 24.74% |
| target_e_top20_leadership | holdout | 73 | 10 | 13.70% |

## Feature-target evidence

| Feature | Target | Dev directed AUC | Dev IC | NW t | p-value | Positive CPCV folds | Holdout directed AUC |
|---|---|---|---|---|---|---|---|
| btc_active_address_growth_30d | target_a_btc_30d_upside | 0.506 | -0.010 | 0.073 | 0.941 | 60.00% | 0.521 |
| btc_active_address_growth_30d | target_b_eth_30d_upside | 0.522 | 0.034 | 0.208 | 0.836 | 40.00% | 0.664 |
| btc_active_address_growth_30d | target_c_btc_eth_50_50_30d_upside | 0.510 | -0.015 | -0.353 | 0.724 | 73.33% | 0.524 |
| btc_active_address_growth_30d | target_d_eth_beats_btc_30d | 0.556 | 0.090 | 0.838 | 0.402 | 80.00% | 0.529 |
| btc_active_address_growth_30d | target_e_top20_leadership | 0.524 | -0.036 | -1.062 | 0.288 | 73.33% | 0.608 |
| btc_active_address_growth_7d | target_a_btc_30d_upside | 0.524 | -0.037 | -0.055 | 0.956 | 66.67% | 0.506 |
| btc_active_address_growth_7d | target_b_eth_30d_upside | 0.516 | 0.024 | 0.983 | 0.326 | 66.67% | 0.562 |
| btc_active_address_growth_7d | target_c_btc_eth_50_50_30d_upside | 0.517 | -0.026 | 0.044 | 0.965 | 86.67% | 0.502 |
| btc_active_address_growth_7d | target_d_eth_beats_btc_30d | 0.546 | 0.075 | 1.625 | 0.104 | 93.33% | 0.509 |
| btc_active_address_growth_7d | target_e_top20_leadership | 0.512 | 0.018 | 1.651 | 0.099 | 60.00% | 0.551 |
| btc_transaction_growth_30d | target_a_btc_30d_upside | 0.500 | 0.000 | -0.202 | 0.840 | 53.33% | 0.538 |
| btc_transaction_growth_30d | target_b_eth_30d_upside | 0.516 | 0.024 | 0.003 | 0.998 | 53.33% | 0.654 |
| btc_transaction_growth_30d | target_c_btc_eth_50_50_30d_upside | 0.514 | -0.022 | -0.548 | 0.583 | 60.00% | 0.533 |
| btc_transaction_growth_30d | target_d_eth_beats_btc_30d | 0.557 | 0.093 | 1.059 | 0.289 | 80.00% | 0.607 |
| btc_transaction_growth_30d | target_e_top20_leadership | 0.544 | -0.066 | -0.497 | 0.619 | 73.33% | 0.644 |
| btc_transaction_growth_7d | target_a_btc_30d_upside | 0.510 | 0.015 | 0.496 | 0.620 | 60.00% | 0.585 |
| btc_transaction_growth_7d | target_b_eth_30d_upside | 0.519 | -0.029 | -0.612 | 0.540 | 66.67% | 0.506 |
| btc_transaction_growth_7d | target_c_btc_eth_50_50_30d_upside | 0.520 | -0.032 | -0.214 | 0.831 | 73.33% | 0.521 |
| btc_transaction_growth_7d | target_d_eth_beats_btc_30d | 0.507 | -0.012 | -0.740 | 0.459 | 53.33% | 0.522 |
| btc_transaction_growth_7d | target_e_top20_leadership | 0.523 | -0.035 | -1.239 | 0.215 | 86.67% | 0.559 |
