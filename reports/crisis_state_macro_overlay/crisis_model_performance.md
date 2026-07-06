# Crisis model performance

Development metrics are CPCV out-of-fold diagnostics. Holdout metrics are diagnostic only and are not used for selection.

XGBoost and LightGBM were checked but are not installed in the active runtime, so the implemented model set is logistic regression, elastic-net logistic regression, random forest, and gradient boosting.

| Model config | Target | Model | AUC | Precision | Recall | F1 | Brier | False-negative rate | TP | FN |
|---|---|---|---|---|---|---|---|---|---|---|
| target_d_future_drawdown_gt_25__gradient_boosting | target_d_future_drawdown_gt_25 | gradient_boosting | 79.90% | 61.78% | 79.51% | 69.53% | 21.32% | 20.49% | 97.000 | 25.000 |
| target_d_future_drawdown_gt_25__random_forest | target_d_future_drawdown_gt_25 | random_forest | 81.88% | 63.95% | 77.05% | 69.89% | 18.04% | 22.95% | 94.000 | 28.000 |
| target_d_future_drawdown_gt_25__elastic_net_logistic | target_d_future_drawdown_gt_25 | elastic_net_logistic | 65.92% | 58.96% | 64.75% | 61.72% | 28.49% | 35.25% | 79.000 | 43.000 |
| target_d_future_drawdown_gt_25__logistic_regression | target_d_future_drawdown_gt_25 | logistic_regression | 62.06% | 53.57% | 61.48% | 57.25% | 32.48% | 38.52% | 75.000 | 47.000 |
| target_c_forward_vol_top20__random_forest | target_c_forward_vol_top20 | random_forest | 73.23% | 56.00% | 49.12% | 52.34% | 17.14% | 50.88% | 28.000 | 29.000 |
| target_c_forward_vol_top20__elastic_net_logistic | target_c_forward_vol_top20 | elastic_net_logistic | 59.76% | 36.62% | 45.61% | 40.62% | 20.65% | 54.39% | 26.000 | 31.000 |
| target_c_forward_vol_top20__logistic_regression | target_c_forward_vol_top20 | logistic_regression | 56.76% | 32.50% | 45.61% | 37.96% | 23.33% | 54.39% | 26.000 | 31.000 |
| target_c_forward_vol_top20__gradient_boosting | target_c_forward_vol_top20 | gradient_boosting | 69.48% | 48.98% | 42.11% | 45.28% | 15.12% | 57.89% | 24.000 | 33.000 |
| target_a_30d_loss_gt_20__logistic_regression | target_a_30d_loss_gt_20 | logistic_regression | 38.25% | 5.26% | 27.27% | 8.82% | 35.94% | 72.73% | 6.000 | 16.000 |
| target_a_30d_loss_gt_20__elastic_net_logistic | target_a_30d_loss_gt_20 | elastic_net_logistic | 40.69% | 4.72% | 22.73% | 7.81% | 31.73% | 77.27% | 5.000 | 17.000 |
| target_e_frozen_future_dd_gt_20__logistic_regression | target_e_frozen_future_dd_gt_20 | logistic_regression | 36.12% | 6.61% | 20.51% | 10.00% | 40.15% | 79.49% | 8.000 | 31.000 |
| target_e_frozen_future_dd_gt_20__elastic_net_logistic | target_e_frozen_future_dd_gt_20 | elastic_net_logistic | 35.01% | 6.15% | 20.51% | 9.47% | 39.16% | 79.49% | 8.000 | 31.000 |
| target_e_frozen_future_dd_gt_20__gradient_boosting | target_e_frozen_future_dd_gt_20 | gradient_boosting | 29.31% | 6.06% | 10.26% | 7.62% | 24.68% | 89.74% | 4.000 | 35.000 |
| target_b_60d_loss_gt_30__logistic_regression | target_b_60d_loss_gt_30 | logistic_regression | 57.08% | 1.85% | 6.25% | 2.86% | 18.90% | 93.75% | 1.000 | 15.000 |
| target_b_60d_loss_gt_30__elastic_net_logistic | target_b_60d_loss_gt_30 | elastic_net_logistic | 56.02% | 2.00% | 6.25% | 3.03% | 15.95% | 93.75% | 1.000 | 15.000 |
| target_e_frozen_future_dd_gt_20__random_forest | target_e_frozen_future_dd_gt_20 | random_forest | 23.45% | 2.50% | 5.13% | 3.36% | 24.40% | 94.87% | 2.000 | 37.000 |
| target_b_60d_loss_gt_30__gradient_boosting | target_b_60d_loss_gt_30 | gradient_boosting | 38.19% | 0.00% | 0.00% | 0.00% | 13.07% | 100.00% | 0.000 | 16.000 |
| target_a_30d_loss_gt_20__gradient_boosting | target_a_30d_loss_gt_20 | gradient_boosting | 37.37% | 0.00% | 0.00% | 0.00% | 19.20% | 100.00% | 0.000 | 22.000 |
| target_b_60d_loss_gt_30__random_forest | target_b_60d_loss_gt_30 | random_forest | 30.49% | 0.00% | 0.00% | 0.00% | 12.56% | 100.00% | 0.000 | 16.000 |
| target_a_30d_loss_gt_20__random_forest | target_a_30d_loss_gt_20 | random_forest | 28.68% | 0.00% | 0.00% | 0.00% | 14.36% | 100.00% | 0.000 | 22.000 |

## Selected-model feature importance

| Feature | Importance | Abs importance |
|---|---|---|
| BTC_rv_63d | 1.208 | 1.208 |
| ETH_below_200dma | 1.031 | 1.031 |
| drawdown_4h_30d_btc_eth_avg | -0.930 | 0.930 |
| BTC_drawdown_from_90d_high | -0.890 | 0.890 |
| eth_btc_relative_weakness_63d | -0.865 | 0.865 |
| tvl_change_90d | -0.745 | 0.745 |
| usd_trend_63d | 0.728 | 0.728 |
| rates_10y_change_21d | -0.663 | 0.663 |
| usd_trend_21d | -0.654 | 0.654 |
| BTC_rv_percentile | -0.553 | 0.553 |
| stablecoin_supply_z_90 | 0.532 | 0.532 |
| BTC_below_100dma | 0.479 | 0.479 |
| ETH_rv_percentile | -0.434 | 0.434 |
| BTC_downside_semivariance_21d | 0.429 | 0.429 |
| BTC_below_200dma | -0.399 | 0.399 |
| ETH_drawdown_from_90d_high | -0.367 | 0.367 |
| vix_change_21d | 0.364 | 0.364 |
| equity_realized_vol_21d | 0.360 | 0.360 |
| BTC_momentum_63d | -0.332 | 0.332 |
| BTC_rv_acceleration | -0.274 | 0.274 |
| ETH_lower_high_low_proxy | -0.237 | 0.237 |
| yield_curve_slope_change_21d | -0.233 | 0.233 |
| volatility_4h_7d_btc_eth_avg | 0.182 | 0.182 |
| vix_level | -0.139 | 0.139 |
| funding_level | 0.128 | 0.128 |
