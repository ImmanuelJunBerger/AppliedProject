# Feature engineering

All implemented features are shifted by at least one day before joining to forward-return targets. Unavailable requested features are recorded but not used.

Feature panel status: **wrote parquet: data\processed\new_data_feature_panel.parquet**

## Implemented features

| Feature | Family | Source | Formula | Rationale |
|---|---|---|---|---|
| active_address_growth_7d | on-chain | Blockchain.com BTC active addresses | pct_change(active addresses, 7d), lagged | Rising network usage may indicate improving crypto demand. |
| active_address_growth_30d | on-chain | Blockchain.com BTC active addresses | pct_change(active addresses, 30d), lagged | Sustained address growth may indicate broader participation. |
| transaction_count_growth_7d | on-chain | Blockchain.com BTC transaction count | pct_change(transaction count, 7d), lagged | Short-term transaction growth can proxy settlement demand. |
| transaction_count_growth_30d | on-chain | Blockchain.com BTC transaction count | pct_change(transaction count, 30d), lagged | Persistent transaction growth can proxy network activity. |
| funding_level | derivatives/crowding | Binance futures funding | average BTC/ETH funding rate, lagged | High funding may indicate crowded long positioning. |
| funding_change | derivatives/crowding | Binance futures funding | 7d change in average funding, lagged | Funding changes can proxy changing leverage pressure. |
| open_interest_growth | derivatives/crowding | Binance futures open interest | 7d open-interest growth, lagged | Open-interest growth can proxy leverage and participation. |
| long_short_ratio | derivatives/crowding | Binance long/short ratio | average BTC/ETH long-short account ratio, lagged | Long/short imbalance can proxy directional crowding. |
| taker_buy_sell_imbalance | derivatives/crowding | Binance taker buy/sell flow | average taker imbalance, lagged | Aggressive taker flow may indicate short-term demand/supply pressure. |
| leverage_crowding_score | derivatives/crowding | Binance funding + open interest | zscore(funding) + zscore(7d OI growth), lagged | Combines funding and leverage growth into a crowding proxy. |
| credit_spread_level | macro/vintage | WRDS macro feature file | credit spread level, lagged | Wider spreads indicate tighter credit and risk-off conditions. |
| credit_spread_change | macro/vintage | WRDS macro feature file | 21d change in credit spread, lagged | Rising spreads can pressure speculative assets. |
| real_yield_level | macro/vintage | WRDS macro feature file | 10y real yield level, lagged | Higher real yields can reduce demand for long-duration/speculative assets. |
| real_yield_change | macro/vintage | WRDS macro feature file | 21d real-yield change, lagged | Real-yield increases can tighten macro liquidity. |
| dxy_momentum | macro/vintage | WRDS macro feature file | 21d USD trend, lagged | A stronger dollar often coincides with tighter global liquidity. |

## Full requested feature coverage

| Feature | Family | Availability | Source | Formula |
|---|---|---|---|---|
| active_address_growth_7d | on-chain | implemented | Blockchain.com BTC active addresses | pct_change(active addresses, 7d), lagged |
| active_address_growth_30d | on-chain | implemented | Blockchain.com BTC active addresses | pct_change(active addresses, 30d), lagged |
| transaction_count_growth_7d | on-chain | implemented | Blockchain.com BTC transaction count | pct_change(transaction count, 7d), lagged |
| transaction_count_growth_30d | on-chain | implemented | Blockchain.com BTC transaction count | pct_change(transaction count, 30d), lagged |
| funding_level | derivatives/crowding | implemented | Binance futures funding | average BTC/ETH funding rate, lagged |
| funding_change | derivatives/crowding | implemented | Binance futures funding | 7d change in average funding, lagged |
| open_interest_growth | derivatives/crowding | implemented | Binance futures open interest | 7d open-interest growth, lagged |
| long_short_ratio | derivatives/crowding | implemented | Binance long/short ratio | average BTC/ETH long-short account ratio, lagged |
| taker_buy_sell_imbalance | derivatives/crowding | implemented | Binance taker buy/sell flow | average taker imbalance, lagged |
| leverage_crowding_score | derivatives/crowding | implemented | Binance funding + open interest | zscore(funding) + zscore(7d OI growth), lagged |
| credit_spread_level | macro/vintage | implemented | WRDS macro feature file | credit spread level, lagged |
| credit_spread_change | macro/vintage | implemented | WRDS macro feature file | 21d change in credit spread, lagged |
| real_yield_level | macro/vintage | implemented | WRDS macro feature file | 10y real yield level, lagged |
| real_yield_change | macro/vintage | implemented | WRDS macro feature file | 21d real-yield change, lagged |
| dxy_momentum | macro/vintage | implemented | WRDS macro feature file | 21d USD trend, lagged |
| exchange_netflow_7d | on-chain | unavailable | unavailable | exchange-flow provider unavailable |
| exchange_netflow_30d | on-chain | unavailable | unavailable | exchange-flow provider unavailable |
| exchange_pressure_percentile | on-chain | unavailable | unavailable | exchange-flow provider unavailable |
| mvrv_level | on-chain | unavailable | unavailable | MVRV provider unavailable |
| mvrv_percentile | on-chain | unavailable | unavailable | MVRV provider unavailable |
| realized_cap_growth_30d | on-chain | unavailable | unavailable | realized-cap provider unavailable |
| holder_accumulation_proxy | on-chain | unavailable | unavailable | holder cohort provider unavailable |
| whale_accumulation_proxy | on-chain | unavailable | unavailable | whale balance provider unavailable |
| etf_net_flow_1d | ETF flows | unavailable | unavailable | ETF flow source unavailable or not point-in-time audited |
| etf_net_flow_5d | ETF flows | unavailable | unavailable | ETF flow source unavailable or not point-in-time audited |
| etf_net_flow_21d | ETF flows | unavailable | unavailable | ETF flow source unavailable or not point-in-time audited |
| etf_flow_acceleration | ETF flows | unavailable | unavailable | ETF flow source unavailable or not point-in-time audited |
| etf_flow_percentile | ETF flows | unavailable | unavailable | ETF flow source unavailable or not point-in-time audited |
| etf_inflow_streak | ETF flows | unavailable | unavailable | ETF flow source unavailable or not point-in-time audited |
| etf_outflow_shock | ETF flows | unavailable | unavailable | ETF flow source unavailable or not point-in-time audited |
| etf_flow_as_aum_if_available | ETF flows | unavailable | unavailable | ETF AUM unavailable |
| iv_level | options-implied | unavailable | unavailable | full options surface history unavailable |
| iv_change_7d | options-implied | unavailable | unavailable | full options surface history unavailable |
| iv_change_30d | options-implied | unavailable | unavailable | full options surface history unavailable |
| iv_term_slope | options-implied | unavailable | unavailable | full options term structure unavailable |
| skew_level | options-implied | unavailable | unavailable | skew history unavailable |
| skew_change | options-implied | unavailable | unavailable | skew history unavailable |
| put_call_ratio | options-implied | unavailable | unavailable | put/call history unavailable |
| risk_reversal | options-implied | unavailable | unavailable | risk reversal history unavailable |
| option_oi_change | options-implied | unavailable | unavailable | options OI history unavailable |
| liquidation_shock | derivatives/crowding | unavailable | unavailable | liquidations unavailable |
| asset_manager_net_position | COT/CME | unavailable | unavailable | COT/CME positioning unavailable |
| leveraged_fund_net_position | COT/CME | unavailable | unavailable | COT/CME positioning unavailable |
| dealer_net_position | COT/CME | unavailable | unavailable | COT/CME positioning unavailable |
| positioning_change_1w | COT/CME | unavailable | unavailable | COT/CME positioning unavailable |
| positioning_percentile | COT/CME | unavailable | unavailable | COT/CME positioning unavailable |
| liquidity_growth | macro/vintage | unavailable | unavailable | macro liquidity vintage unavailable |
| financial_conditions_level | macro/vintage | unavailable | unavailable | financial conditions index unavailable |
| financial_conditions_change | macro/vintage | unavailable | unavailable | financial conditions index unavailable |
