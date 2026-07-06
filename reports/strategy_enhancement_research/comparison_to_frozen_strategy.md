# Comparison to frozen strategy

The frozen benchmark is **btc_eth_macro_gate_balanced** and remains unchanged.

## Frozen benchmark

| Split | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development | 20.00% | 0.628 | 0.593 | -74.09% | 0.270 | 11.088 | 49.81% |
| Holdout | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |

## Candidate holdout comparison

| Study | Candidate | Holdout Sharpe | Holdout CAGR | Holdout max DD | Holdout turnover | Beats frozen Sharpe | Beats frozen CAGR | DD not worse |
|---|---|---|---|---|---|---|---|---|
| study_2_meta_labeling | meta_logistic_60 | 1.591 | 32.50% | -7.22% | 3.731 | Yes | Yes | Yes |
| study_2_meta_labeling | meta_gradient_boosting_60 | 1.582 | 17.31% | -6.80% | 2.714 | Yes | No | Yes |
| study_2_meta_labeling | meta_logistic_55 | 1.576 | 33.68% | -7.22% | 4.749 | Yes | Yes | Yes |
| study_2_meta_labeling | meta_gradient_boosting_55 | 1.574 | 19.62% | -7.22% | 3.731 | Yes | No | Yes |
| study_2_meta_labeling | meta_random_forest_55 | 1.365 | 32.39% | -13.64% | 8.480 | Yes | Yes | Yes |
| study_2_meta_labeling | meta_random_forest_60 | 1.312 | 29.29% | -10.68% | 5.767 | Yes | Yes | Yes |
| study_5_signal_ensemble | ensemble_rank_average | 0.256 | 3.35% | -33.50% | 8.911 | No | No | No |
| study_5_signal_ensemble | logistic_ensemble | 0.061 | -3.26% | -32.94% | 5.767 | No | No | No |
| study_5_signal_ensemble | ensemble_equal_weight | -0.216 | -10.13% | -41.04% | 11.087 | No | No | No |
| study_1_exposure_sizing | discrete_conservative | -0.233 | -7.96% | -35.48% | 10.007 | No | No | No |
| study_1_exposure_sizing | discrete_aggressive | -0.261 | -14.89% | -48.42% | 10.007 | No | No | No |
| study_1_exposure_sizing | continuous_conservative_percentile | -0.284 | -9.35% | -36.98% | 11.703 | No | No | No |
| study_5_signal_ensemble | ensemble_linear_predeclared | -0.286 | -11.89% | -42.04% | 11.284 | No | No | No |
| study_3_asset_selection | asset_eth_when_low_vol | -0.360 | -22.80% | -61.31% | 27.774 | No | No | No |
| study_1_exposure_sizing | discrete_balanced_0_25_50_75_100 | -0.360 | -15.01% | -45.89% | 13.230 | No | No | No |
| study_1_exposure_sizing | continuous_linear_percentile | -0.374 | -14.62% | -43.72% | 10.768 | No | No | No |
| study_4_dynamic_horizon | fixed_momentum_63d | -0.382 | -28.07% | -69.03% | 15.530 | No | No | No |
| study_1_exposure_sizing | continuous_aggressive_percentile | -0.407 | -18.53% | -48.15% | 9.376 | No | No | No |
| study_4_dynamic_horizon | dynamic_short_risk_on_medium_neutral | -0.411 | -28.96% | -69.06% | 19.473 | No | No | No |
| study_4_dynamic_horizon | fixed_momentum_126d | -0.426 | -28.36% | -63.65% | 12.890 | No | No | No |
| study_3_asset_selection | asset_speculative_eth | -0.514 | -26.67% | -59.10% | 25.781 | No | No | No |
| study_4_dynamic_horizon | fixed_momentum_21d | -0.552 | -31.31% | -63.31% | 20.998 | No | No | No |
| study_4_dynamic_horizon | dynamic_short_risk_on_long_neutral | -0.566 | -33.31% | -64.43% | 20.438 | No | No | No |
| study_3_asset_selection | asset_conservative_btc | -0.570 | -27.77% | -59.41% | 25.060 | No | No | No |
| study_4_dynamic_horizon | dynamic_medium_risk_on_long_neutral | -0.623 | -33.66% | -64.96% | 21.201 | No | No | No |
| study_4_dynamic_horizon | fixed_momentum_42d | -0.642 | -35.37% | -68.71% | 19.770 | No | No | No |
| study_3_asset_selection | asset_btc_uncertain_eth_strong | -0.856 | -33.61% | -57.42% | 19.949 | No | No | No |
