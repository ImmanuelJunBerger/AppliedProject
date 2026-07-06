# Feature usage

Features were lagged before model fitting. ETF/on-chain/options features were
included only where usable data existed; unavailable sources were skipped.

## Feature inventory

| Feature | Source family | Source | Used | Notes |
|---|---|---|---|---|
| equity_realized_vol_21d | WRDS-derived macro | data/processed/wrds_macro_features/wrds_macro_features_daily.csv | Yes | Lagged one day; includes validated macro/rates/USD/credit/equity features where available. |
| equity_momentum_21d | WRDS-derived macro | data/processed/wrds_macro_features/wrds_macro_features_daily.csv | Yes | Lagged one day; includes validated macro/rates/USD/credit/equity features where available. |
| dow_vol_level | WRDS-derived macro | data/processed/wrds_macro_features/wrds_macro_features_daily.csv | Yes | Lagged one day; includes validated macro/rates/USD/credit/equity features where available. |
| vix_level | WRDS-derived macro | data/processed/wrds_macro_features/wrds_macro_features_daily.csv | Yes | Lagged one day; includes validated macro/rates/USD/credit/equity features where available. |
| vix_change_5d | WRDS-derived macro | data/processed/wrds_macro_features/wrds_macro_features_daily.csv | Yes | Lagged one day; includes validated macro/rates/USD/credit/equity features where available. |
| vix_change_21d | WRDS-derived macro | data/processed/wrds_macro_features/wrds_macro_features_daily.csv | Yes | Lagged one day; includes validated macro/rates/USD/credit/equity features where available. |
| stablecoin_supply_acceleration | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| stablecoin_supply_percentile | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| tvl_acceleration | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| tvl_percentile | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| combined_crypto_liquidity_impulse | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| top20_above_30dma_pct | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| top20_30d_high_pct | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| eth_btc_relative_strength_14d | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| eth_btc_relative_strength_30d | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| market_dollar_volume_growth_30d | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| volume_confirmation_of_price_trend | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| volatility_of_volatility | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| dispersion_acceleration | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| upside_semivariance | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| downside_to_upside_volatility_ratio | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| jump_intensity | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| distance_from_90d_lows | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| recovery_from_drawdown | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| falling_vix_after_high_vix | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| risk_appetite_recovery_score | Expansion Tier-1 crypto-native | reports/upside_expansion_models/expansion_feature_tiers.csv | Yes | Previously validated Expansion Tier-1 feature. |
| funding_rate_btc_eth_mean | derivatives/funding | data\processed\derivatives\derivatives_daily_merged.csv | Yes | BTC/ETH Binance futures-derived feature, lagged one day. |
| basis_close_btc_eth_mean | derivatives/funding | data\processed\derivatives\derivatives_daily_merged.csv | Yes | BTC/ETH Binance futures-derived feature, lagged one day. |
| open_interest_growth_7d | derivatives/funding | data\processed\derivatives\derivatives_daily_merged.csv | Yes | BTC/ETH Binance futures-derived feature, lagged one day. |
| long_short_ratio_btc_eth_mean | derivatives/funding | data\processed\derivatives\derivatives_daily_merged.csv | Yes | BTC/ETH Binance futures-derived feature, lagged one day. |
| taker_imbalance_btc_eth_mean | derivatives/funding | data\processed\derivatives\derivatives_daily_merged.csv | Yes | BTC/ETH Binance futures-derived feature, lagged one day. |
| new_data_tier1 | ETF/on-chain/options | reports\new_data_expansion_strategy\feature_tiers.csv | No | No New Data Tier-1 features found; ETF/on-chain/options skipped. |

## Source-family importance proxy

| Source family | Total absolute model importance |
|---|---|
| Expansion Tier-1 crypto-native | 51.486 |
| WRDS-derived macro | 20.264 |
| derivatives/funding | 5.087 |
| N/A | 3.182 |
