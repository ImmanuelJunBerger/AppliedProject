# Feature importance

Only Expansion Tier-1 features were allowed in models.

## Tier-1 features used

| Feature |
|---|
| recovery_from_drawdown |
| tvl_percentile |
| jump_intensity |
| stablecoin_supply_percentile |
| eth_btc_relative_strength_30d |
| upside_semivariance |
| distance_from_90d_lows |
| top20_30d_high_pct |
| downside_to_upside_volatility_ratio |
| top20_above_30dma_pct |
| dispersion_acceleration |
| risk_appetite_recovery_score |
| volume_confirmation_of_price_trend |
| volatility_of_volatility |
| tvl_acceleration |
| market_dollar_volume_growth_30d |
| combined_crypto_liquidity_impulse |
| stablecoin_supply_acceleration |
| eth_btc_relative_strength_14d |
| falling_vix_after_high_vix |

## Selected-model feature importance

| Config | Target | Feature | Importance | Method |
|---|---|---|---|---|
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | volatility_of_volatility | 0.174 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | downside_to_upside_volatility_ratio | 0.104 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | eth_btc_relative_strength_30d | 0.104 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | recovery_from_drawdown | 0.102 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | upside_semivariance | 0.081 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | distance_from_90d_lows | 0.070 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | stablecoin_supply_acceleration | 0.067 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | dispersion_acceleration | 0.067 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | tvl_percentile | 0.056 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | risk_appetite_recovery_score | 0.042 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | combined_crypto_liquidity_impulse | 0.026 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | top20_30d_high_pct | 0.025 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | jump_intensity | 0.023 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | market_dollar_volume_growth_30d | 0.018 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | volume_confirmation_of_price_trend | 0.016 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | tvl_acceleration | 0.014 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | stablecoin_supply_percentile | 0.008 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | eth_btc_relative_strength_14d | 0.004 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | top20_above_30dma_pct | 0.000 | model_importance |
| target_a_btc_eth_upside__gradient_boosting | target_a_btc_eth_upside | falling_vix_after_high_vix | 0.000 | model_importance |
