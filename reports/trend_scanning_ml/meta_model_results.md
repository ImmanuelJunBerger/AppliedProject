# Meta-model results

Selected meta-model by development metrics: **meta_btc_eth_upward_trend__sgd_classifier**.

The meta target is whether a candidate trend-scanning signal produced positive net return after estimated 25 bps round-trip costs over the selected trend horizon.  True future returns are used only as labels, never as live-decision features.

## Meta-model metrics

| Config | Split | Model | Obs | AUC | Precision | Recall | F1 | Brier | Selection score |
|---|---|---|---|---|---|---|---|---|---|
| meta_btc_eth_upward_trend__logistic_regression | development_cpcv | logistic_regression | 215 | 0.648 | 0.676 | 0.907 | 0.774 | 0.228 | 0.497 |
| meta_btc_eth_upward_trend__logistic_regression | holdout | logistic_regression | 50 | 0.747 | 0.545 | 0.857 | 0.667 | 0.221 | 0.497 |
| meta_btc_eth_upward_trend__elastic_net_logistic | development_cpcv | elastic_net_logistic | 215 | 0.631 | 0.682 | 0.871 | 0.765 | 0.230 | 0.477 |
| meta_btc_eth_upward_trend__elastic_net_logistic | holdout | elastic_net_logistic | 50 | 0.783 | 0.567 | 0.810 | 0.667 | 0.192 | 0.477 |
| meta_btc_eth_upward_trend__random_forest | development_cpcv | random_forest | 215 | 0.445 | 0.651 | 0.971 | 0.779 | 0.255 | 0.268 |
| meta_btc_eth_upward_trend__random_forest | holdout | random_forest | 50 | 0.773 | 0.444 | 0.952 | 0.606 | 0.212 | 0.268 |
| meta_btc_eth_upward_trend__gradient_boosting | development_cpcv | gradient_boosting | 215 | 0.560 | 0.658 | 0.936 | 0.773 | 0.244 | 0.393 |
| meta_btc_eth_upward_trend__gradient_boosting | holdout | gradient_boosting | 50 | 0.778 | 0.450 | 0.857 | 0.590 | 0.210 | 0.393 |
| meta_btc_eth_upward_trend__sgd_classifier | development_cpcv | sgd_classifier | 215 | 0.704 | 0.690 | 0.921 | 0.789 | 0.224 | 0.560 |
| meta_btc_eth_upward_trend__sgd_classifier | holdout | sgd_classifier | 50 | 0.668 | 0.488 | 0.952 | 0.645 | 0.363 | 0.560 |
| meta_btc_eth_upward_trend__xgboost | development_cpcv | xgboost | 215 | 0.514 | 0.657 | 0.943 | 0.774 | 0.249 | 0.342 |
| meta_btc_eth_upward_trend__xgboost | holdout | xgboost | 50 | 0.749 | 0.462 | 0.857 | 0.600 | 0.226 | 0.342 |

## Meta-model feature importance

| Config | Feature | Importance | Method |
|---|---|---|---|
| meta_btc_eth_upward_trend__logistic_regression | distance_from_90d_lows | 2.649 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | past_trend_t_stat | 1.641 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | primary_trend_probability | -1.567 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | falling_vix_after_high_vix | 1.525 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | dow_vol_level | 1.313 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | eth_btc_relative_strength_30d | -1.258 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | cross_sectional_dispersion | -1.247 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | volatility_4h_7d | -0.791 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | vix_level | 0.789 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | vix_change_21d | 0.631 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | volatility_expansion_probability | -0.605 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | tvl_percentile | -0.597 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | stablecoin_supply_change_7d | 0.586 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | volatility_of_volatility | 0.548 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | downside_to_upside_volatility_ratio | 0.542 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | tvl_growth_30d | -0.529 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | past_selected_trend_horizon | 0.509 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | recovery_from_drawdown | -0.418 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | equity_realized_vol_21d | -0.377 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | volume_confirmation_of_price_trend | 0.313 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | top20_30d_high_pct | -0.283 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | previous_drawdown | -0.266 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | upside_semivariance | 0.234 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | top20_above_30dma_pct | 0.220 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | dispersion_acceleration | -0.216 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | market_dollar_volume_growth_30d | 0.188 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | past_label_confidence | -0.180 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | eth_btc_relative_strength_14d | -0.173 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | equity_momentum_21d | -0.173 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | combined_crypto_liquidity_impulse | 0.151 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | risk_appetite_recovery_score | -0.112 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | realized_volatility | 0.108 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | tvl_acceleration | -0.078 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | stablecoin_supply_percentile | -0.078 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | vix_change_5d | -0.032 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | stablecoin_supply_acceleration | 0.018 | coefficient |
| meta_btc_eth_upward_trend__logistic_regression | jump_intensity | 0.003 | coefficient |
| meta_btc_eth_upward_trend__elastic_net_logistic | distance_from_90d_lows | 1.875 | coefficient |
| meta_btc_eth_upward_trend__elastic_net_logistic | past_trend_t_stat | 1.448 | coefficient |
| meta_btc_eth_upward_trend__elastic_net_logistic | primary_trend_probability | -0.987 | coefficient |
