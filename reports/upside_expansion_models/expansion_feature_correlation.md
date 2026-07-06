# Expansion feature correlation and redundancy

Correlation is computed on the development period only. Highly correlated pairs
are reported so redundant features can be excluded from future model design.

| Type | Feature | Feature 2 | Correlation |
|---|---|---|---|
| feature_max_abs_corr | top20_equal_weight_minus_btc_return_30d | altcoin_leadership_proxy_30d | 0.999 |
| feature_max_abs_corr | altcoin_leadership_proxy_30d | top20_equal_weight_minus_btc_return_30d | 0.999 |
| high_correlation_pair | altcoin_leadership_proxy_30d | top20_equal_weight_minus_btc_return_30d | 0.999 |
| high_correlation_pair | top20_equal_weight_minus_btc_return_30d | top20_equal_weight_minus_btc_vol_adj_30d | 0.977 |
| feature_max_abs_corr | top20_equal_weight_minus_btc_vol_adj_30d | top20_equal_weight_minus_btc_return_30d | 0.977 |
| high_correlation_pair | altcoin_leadership_proxy_30d | top20_equal_weight_minus_btc_vol_adj_30d | 0.977 |
| feature_max_abs_corr | top20_positive_30d_return_pct | breadth_recovery_from_depressed | 0.975 |
| feature_max_abs_corr | breadth_recovery_from_depressed | top20_positive_30d_return_pct | 0.975 |
| high_correlation_pair | top20_positive_30d_return_pct | breadth_recovery_from_depressed | 0.975 |
| feature_max_abs_corr | top10_breadth_acceleration | top20_breadth_acceleration | 0.947 |
| high_correlation_pair | top10_breadth_acceleration | top20_breadth_acceleration | 0.947 |
| feature_max_abs_corr | top20_breadth_acceleration | top10_breadth_acceleration | 0.947 |
| high_correlation_pair | distance_from_30d_lows | assets_rebounding_from_30d_lows_pct | 0.918 |
| feature_max_abs_corr | distance_from_30d_lows | assets_rebounding_from_30d_lows_pct | 0.918 |
| feature_max_abs_corr | assets_rebounding_from_30d_lows_pct | distance_from_30d_lows | 0.918 |
| feature_max_abs_corr | volume_confirmation_of_price_trend | top20_positive_30d_return_pct | 0.846 |
| feature_max_abs_corr | top20_above_30dma_pct | top20_positive_30d_return_pct | 0.826 |
| feature_max_abs_corr | recovery_from_drawdown | tvl_percentile | 0.808 |
| feature_max_abs_corr | tvl_percentile | recovery_from_drawdown | 0.808 |
| feature_max_abs_corr | tvl_acceleration | combined_crypto_liquidity_impulse | 0.799 |
| feature_max_abs_corr | combined_crypto_liquidity_impulse | tvl_acceleration | 0.799 |
| feature_max_abs_corr | stablecoin_supply_7d_30d_spread | stablecoin_supply_percentile | 0.786 |
| feature_max_abs_corr | stablecoin_supply_percentile | stablecoin_supply_7d_30d_spread | 0.786 |
| feature_max_abs_corr | distance_from_180d_lows | distance_from_90d_lows | 0.762 |
| feature_max_abs_corr | distance_from_90d_lows | distance_from_180d_lows | 0.762 |
| feature_max_abs_corr | volume_breadth | volume_confirmation_of_price_trend | 0.750 |
| feature_max_abs_corr | downside_to_upside_volatility_ratio | top20_positive_30d_return_pct | 0.748 |
| feature_max_abs_corr | eth_btc_breakout_strength | eth_btc_relative_strength_30d | 0.744 |
| feature_max_abs_corr | eth_btc_relative_strength_30d | eth_btc_breakout_strength | 0.744 |
| feature_max_abs_corr | market_dollar_volume_growth_30d | volume_acceleration | 0.738 |
| feature_max_abs_corr | volume_acceleration | market_dollar_volume_growth_30d | 0.738 |
| feature_max_abs_corr | top20_30d_high_pct | top20_above_30dma_pct | 0.732 |
| feature_max_abs_corr | realized_volatility_compression | upside_semivariance | 0.714 |
| feature_max_abs_corr | upside_semivariance | realized_volatility_compression | 0.714 |
| feature_max_abs_corr | tvl_7d_30d_spread | top20_positive_30d_return_pct | 0.706 |
| feature_max_abs_corr | risk_appetite_recovery_score | equity_momentum_recovery | 0.677 |
| feature_max_abs_corr | equity_momentum_recovery | risk_appetite_recovery_score | 0.677 |
| feature_max_abs_corr | stablecoin_supply_acceleration | combined_crypto_liquidity_impulse | 0.640 |
| feature_max_abs_corr | eth_btc_relative_strength_14d | eth_btc_relative_strength_30d | 0.618 |
| feature_max_abs_corr | eth_btc_relative_strength_63d | eth_btc_breakout_strength | 0.584 |
| feature_max_abs_corr | jump_intensity | realized_volatility_compression | 0.584 |
| feature_max_abs_corr | abnormal_volume_zscore | volume_breadth | 0.578 |
| feature_max_abs_corr | falling_vix_after_high_vix | risk_appetite_recovery_score | 0.517 |
| feature_max_abs_corr | equity_volatility_compression | risk_appetite_recovery_score | 0.493 |
| feature_max_abs_corr | btc_dominance_proxy_change_30d | top20_equal_weight_minus_btc_return_30d | 0.445 |
| feature_max_abs_corr | dispersion_acceleration | distance_from_30d_lows | 0.413 |
| feature_max_abs_corr | volatility_of_volatility | realized_volatility_compression | 0.272 |
