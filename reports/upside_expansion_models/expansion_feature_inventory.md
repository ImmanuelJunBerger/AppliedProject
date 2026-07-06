# Expansion feature inventory

These features are engineered specifically for upside expansion detection rather
than broad risk avoidance. They are diagnostics only in this run and were not
added to the final overlay candidate.

| Feature | Family | Economic rationale | Availability | Used in final overlay |
|---|---|---|---|---|
| stablecoin_supply_acceleration | liquidity_inflow | acceleration in stablecoin liquidity | available | No |
| stablecoin_supply_7d_30d_spread | liquidity_inflow | short-term stablecoin growth above trend | available | No |
| stablecoin_supply_percentile | liquidity_inflow | stablecoin supply relative to its own history | available | No |
| tvl_acceleration | liquidity_inflow | acceleration in DeFi liquidity | available | No |
| tvl_7d_30d_spread | liquidity_inflow | short-term TVL growth above trend | available | No |
| tvl_percentile | liquidity_inflow | TVL relative to its own history | available | No |
| combined_crypto_liquidity_impulse | liquidity_inflow | joint stablecoin and TVL liquidity impulse | available | No |
| top10_breadth_acceleration | participation_breadth | top-10 breadth acceleration | available | No |
| top20_breadth_acceleration | participation_breadth | top-20 breadth acceleration | available | No |
| top20_above_30dma_pct | participation_breadth | share of top-20 above 30d moving average | available | No |
| top20_positive_30d_return_pct | participation_breadth | share of top-20 with positive 30d returns | available | No |
| top20_30d_high_pct | participation_breadth | share of top-20 making 30d highs | available | No |
| breadth_recovery_from_depressed | participation_breadth | breadth recovery after depressed participation | available | No |
| eth_btc_relative_strength_14d | leadership | ETH/BTC 14d relative strength | available | No |
| eth_btc_relative_strength_30d | leadership | ETH/BTC 30d relative strength | available | No |
| eth_btc_relative_strength_63d | leadership | ETH/BTC 63d relative strength | available | No |
| eth_btc_breakout_strength | leadership | ETH/BTC distance to 63d breakout | available | No |
| btc_dominance_proxy_change_30d | leadership | BTC dominance proxy change | available | No |
| altcoin_leadership_proxy_30d | leadership | altcoin basket leadership versus BTC | available | No |
| top20_equal_weight_minus_btc_return_30d | leadership | top-20 equal weight return minus BTC | available | No |
| top20_equal_weight_minus_btc_vol_adj_30d | leadership | volatility-adjusted top-20 leadership versus BTC | available | No |
| market_dollar_volume_growth_30d | volume_attention | market dollar-volume growth | available | No |
| volume_acceleration | volume_attention | short-term volume acceleration versus 30d growth | available | No |
| abnormal_volume_zscore | volume_attention | abnormal market volume growth | available | No |
| volume_breadth | volume_attention | share of top-20 with above-median volume | available | No |
| volume_confirmation_of_price_trend | volume_attention | volume breadth confirming price breadth | available | No |
| realized_volatility_compression | volatility_structure | low realized volatility before expansion | available | No |
| volatility_of_volatility | volatility_structure | volatility-of-volatility | available | No |
| dispersion_acceleration | volatility_structure | cross-sectional dispersion acceleration | available | No |
| upside_semivariance | volatility_structure | upside volatility participation | available | No |
| downside_to_upside_volatility_ratio | volatility_structure | downside-to-upside volatility balance | available | No |
| jump_intensity | volatility_structure | frequency of large market moves | available | No |
| distance_from_30d_lows | recovery_capitulation | average distance from 30d lows | available | No |
| distance_from_90d_lows | recovery_capitulation | average distance from 90d lows | available | No |
| distance_from_180d_lows | recovery_capitulation | average distance from 180d lows | available | No |
| recovery_from_drawdown | recovery_capitulation | market recovery from recent drawdown trough | available | No |
| assets_rebounding_from_30d_lows_pct | recovery_capitulation | share of assets rebounding from 30d lows | available | No |
| falling_vix_after_high_vix | macro_recovery | falling VIX after high-volatility regime | available | No |
| equity_momentum_recovery | macro_recovery | equity momentum recovery from local trough | available | No |
| equity_volatility_compression | macro_recovery | compression in equity realized volatility | available | No |
| risk_appetite_recovery_score | macro_recovery | combined macro risk-appetite recovery score | available | No |
