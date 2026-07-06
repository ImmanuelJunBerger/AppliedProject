# Feature mapping

All included features are lagged before use. Unavailable data is excluded and documented.

## Available mapped features

| Feature | Source | Point-in-time status | Available |
|---|---|---|---|
| equity_realized_vol_21d | existing macro/crypto regime feature | lagged before strategy use | Yes |
| equity_momentum_21d | existing macro/crypto regime feature | lagged before strategy use | Yes |
| dow_vol_level | existing macro/crypto regime feature | lagged before strategy use | Yes |
| vix_level | existing macro/crypto regime feature | lagged before strategy use | Yes |
| vix_change_5d | existing macro/crypto regime feature | lagged before strategy use | Yes |
| vix_change_21d | existing macro/crypto regime feature | lagged before strategy use | Yes |
| stablecoin_supply_change_7d | existing macro/crypto regime feature | lagged before strategy use | Yes |
| tvl_growth_30d | existing macro/crypto regime feature | lagged before strategy use | Yes |
| volatility_expansion_probability | existing macro/crypto regime feature | lagged before strategy use | Yes |
| cross_sectional_dispersion | existing macro/crypto regime feature | lagged before strategy use | Yes |
| funding_change | accepted new-data feature panel | lagged before strategy use | Yes |
| funding_level | accepted new-data feature panel | lagged before strategy use | Yes |
| tvl_percentile | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| tvl_acceleration | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| stablecoin_supply_percentile | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| stablecoin_acceleration | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| top_universe_above_30dma_pct | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| top_universe_positive_30d_pct | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| top_universe_30d_high_pct | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| breadth_recovery | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| realized_vol_21d | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| realized_vol_percentile | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| volatility_compression | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| jump_intensity | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| upside_semivariance | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| downside_to_upside_volatility_ratio | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| market_drawdown | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| recovery_from_drawdown | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| distance_from_90d_lows | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| eth_btc_relative_strength_30d | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |
| eth_btc_relative_strength_z | engineered from point-in-time OHLCV/public crypto data | lagged before strategy use | Yes |

## Excluded unavailable features

| Feature | Reason |
|---|---|
| ETF flows | No point-in-time local ETF flow table is available. |
| full options implied-volatility surface | No accepted local options surface with sufficient timestamp integrity. |
| COT/CME positioning | No audited point-in-time COT/CME positioning file is available. |
| entity-adjusted exchange flows/MVRV/realized cap | No accepted professional on-chain provider file is available. |
| trend-scanning labels | Existing trend-scanning labels are generated from forward price paths; allowed as labels, rejected as live-decision features. |
