# Statistical validation

All candidates were selected using development-only CPCV. Holdout metrics were
reported only after each study selected its candidate.

## Study-level statistics

| Study | Selected candidate | PBO | Deflated Sharpe probability | Holdout Sharpe | Holdout CAGR | Passes criteria |
|---|---|---|---|---|---|---|
| study_1_exposure_sizing | discrete_aggressive | 34.29% | 5.29% | -0.261 | -14.89% | No |
| study_2_meta_labeling | meta_gradient_boosting_60 | 30.00% | 88.49% | 1.582 | 17.31% | Yes |
| study_3_asset_selection | asset_btc_uncertain_eth_strong | 22.86% | 1.81% | -0.856 | -33.61% | No |
| study_4_dynamic_horizon | fixed_momentum_126d | 27.14% | 2.86% | -0.426 | -28.36% | No |
| study_5_signal_ensemble | ensemble_equal_weight | 72.86% | 9.44% | -0.216 | -10.13% | No |

## Candidate retention and fold summaries

| Study | Candidate | Dev Sharpe | Holdout Sharpe | Sharpe retention | CAGR retention | Worst fold | Positive folds | PBO | DSR probability |
|---|---|---|---|---|---|---|---|---|---|
| study_1_exposure_sizing | discrete_balanced_0_25_50_75_100 | 1.048 | -0.360 | -34.38% | -39.17% | -1.073 | 80.00% | 34.29% | 4.12% |
| study_1_exposure_sizing | discrete_conservative | 0.953 | -0.233 | -24.47% | -30.10% | -1.425 | 80.00% | 34.29% | 5.67% |
| study_1_exposure_sizing | discrete_aggressive | 1.127 | -0.261 | -23.20% | -30.45% | -1.011 | 86.67% | 34.29% | 5.29% |
| study_1_exposure_sizing | continuous_linear_percentile | 1.084 | -0.374 | -34.44% | -37.98% | -1.057 | 80.00% | 34.29% | 3.98% |
| study_1_exposure_sizing | continuous_conservative_percentile | 0.963 | -0.284 | -29.47% | -33.42% | -1.198 | 86.67% | 34.29% | 5.01% |
| study_1_exposure_sizing | continuous_aggressive_percentile | 1.162 | -0.407 | -35.02% | -38.52% | -0.888 | 80.00% | 34.29% | 3.65% |
| study_2_meta_labeling | meta_logistic_55 | 0.396 | 1.576 | 398.43% | 431.60% | -1.368 | 60.00% | 30.00% | 88.25% |
| study_2_meta_labeling | meta_logistic_60 | 0.247 | 1.591 | 645.22% | 2336.94% | -1.365 | 60.00% | 30.00% | 91.82% |
| study_2_meta_labeling | meta_random_forest_55 | 0.441 | 1.365 | 309.60% | 343.10% | -1.172 | 73.33% | 30.00% | 73.45% |
| study_2_meta_labeling | meta_random_forest_60 | 0.161 | 1.312 | 812.76% | -1217.22% | -1.304 | 66.67% | 30.00% | 72.42% |
| study_2_meta_labeling | meta_gradient_boosting_55 | 0.038 | 1.574 | 4182.46% | -510.98% | -1.153 | 53.33% | 30.00% | 87.26% |
| study_2_meta_labeling | meta_gradient_boosting_60 | 0.102 | 1.582 | 1557.16% | -2574.26% | -1.051 | 66.67% | 30.00% | 88.49% |
| study_3_asset_selection | asset_speculative_eth | 0.737 | -0.514 | -69.78% | -97.57% | -1.644 | 73.33% | 22.86% | 4.68% |
| study_3_asset_selection | asset_conservative_btc | 0.800 | -0.570 | -71.28% | -88.31% | -1.647 | 73.33% | 22.86% | 4.05% |
| study_3_asset_selection | asset_eth_when_low_vol | 0.847 | -0.360 | -42.48% | -64.79% | -1.675 | 73.33% | 22.86% | 6.84% |
| study_3_asset_selection | asset_btc_uncertain_eth_strong | 0.687 | -0.856 | -124.57% | -139.88% | -1.641 | 73.33% | 22.86% | 1.81% |
| study_4_dynamic_horizon | fixed_momentum_21d | 1.082 | -0.552 | -50.99% | -56.44% | -1.422 | 80.00% | 27.14% | 2.00% |
| study_4_dynamic_horizon | fixed_momentum_42d | 0.933 | -0.642 | -68.79% | -82.49% | -1.464 | 80.00% | 27.14% | 1.53% |
| study_4_dynamic_horizon | fixed_momentum_63d | 0.902 | -0.382 | -42.34% | -68.75% | -1.609 | 73.33% | 27.14% | 3.22% |
| study_4_dynamic_horizon | fixed_momentum_126d | 1.165 | -0.426 | -36.53% | -44.12% | -1.652 | 80.00% | 27.14% | 2.86% |
| study_4_dynamic_horizon | dynamic_short_risk_on_long_neutral | 1.095 | -0.566 | -51.71% | -58.48% | -1.652 | 80.00% | 27.14% | 1.91% |
| study_4_dynamic_horizon | dynamic_medium_risk_on_long_neutral | 1.004 | -0.623 | -62.07% | -67.91% | -1.630 | 73.33% | 27.14% | 1.61% |
| study_4_dynamic_horizon | dynamic_short_risk_on_medium_neutral | 0.901 | -0.411 | -45.64% | -71.98% | -1.667 | 73.33% | 27.14% | 2.97% |
| study_5_signal_ensemble | ensemble_equal_weight | 1.368 | -0.216 | -15.81% | -17.97% | -1.068 | 86.67% | 72.86% | 9.44% |
| study_5_signal_ensemble | ensemble_rank_average | 1.420 | 0.256 | 18.05% | 5.20% | -0.902 | 86.67% | 72.86% | 22.94% |
| study_5_signal_ensemble | ensemble_linear_predeclared | 1.262 | -0.286 | -22.66% | -24.13% | -1.102 | 86.67% | 72.86% | 8.10% |
| study_5_signal_ensemble | logistic_ensemble | 1.179 | 0.061 | 5.20% | -7.03% | -0.793 | 86.67% | 72.86% | 16.41% |
