# Feature sets

All features are shifted one rebalance period before prediction. Rejected or unavailable ETF/options/COT/on-chain datasets are not included.

Feature panel status: **wrote parquet: data\processed\new_data_feature_panel.parquet**

## Feature-set summary

| Feature set | Description | Features | Observations | Development observations | Feature/dev obs ratio | Auto selection |
|---|---|---|---|---|---|---|
| macro_tier1 | Macro Tier-1 only. | 6 | 390 | 261 | 2.30% | No |
| macro_plus_crypto_tier1 | Macro Tier-1 plus existing crypto Tier-1. | 10 | 390 | 261 | 3.83% | No |
| all_accepted | All accepted point-in-time-safe features. | 31 | 390 | 261 | 11.88% | No |
| all_accepted_auto_selection | All accepted features with train-fold-only automatic selection/regularisation. | 31 | 390 | 261 | 11.88% | Yes |

## Feature inventory

| Feature | Family | Source | Start | End | Coverage | Lag rule |
|---|---|---|---|---|---|---|
| equity_realized_vol_21d | macro Tier-1 | existing WRDS macro-regime feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| equity_momentum_21d | macro Tier-1 | existing WRDS macro-regime feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| dow_vol_level | macro Tier-1 | existing WRDS macro-regime feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| vix_level | macro Tier-1 | existing WRDS macro-regime feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| vix_change_5d | macro Tier-1 | existing WRDS macro-regime feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| vix_change_21d | macro Tier-1 | existing WRDS macro-regime feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| stablecoin_supply_change_7d | crypto Tier-1 | existing public crypto-native feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| tvl_growth_30d | crypto Tier-1 | existing public crypto-native feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| volatility_expansion_probability | crypto Tier-1 | existing public crypto-native feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| cross_sectional_dispersion | crypto Tier-1 | existing public crypto-native feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| trend_4h_7d | public crypto 4h | accepted Binance 4h public feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| trend_4h_14d | public crypto 4h | accepted Binance 4h public feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| volatility_4h_7d | public crypto 4h | accepted Binance 4h public feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| volatility_4h_30d | public crypto 4h | accepted Binance 4h public feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| drawdown_4h_30d | public crypto 4h | accepted Binance 4h public feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| volume_shock_4h | public crypto 4h | accepted Binance 4h public feature | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| active_address_growth_7d | on-chain | Blockchain.com BTC active addresses | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| active_address_growth_30d | on-chain | Blockchain.com BTC active addresses | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| transaction_count_growth_7d | on-chain | Blockchain.com BTC transaction count | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| transaction_count_growth_30d | on-chain | Blockchain.com BTC transaction count | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| funding_level | derivatives/crowding | Binance futures funding | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| funding_change | derivatives/crowding | Binance futures funding | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| open_interest_growth | derivatives/crowding | Binance futures open interest | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| long_short_ratio | derivatives/crowding | Binance long/short ratio | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| taker_buy_sell_imbalance | derivatives/crowding | Binance taker buy/sell flow | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| leverage_crowding_score | derivatives/crowding | Binance funding + open interest | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| credit_spread_level | macro/vintage | WRDS macro feature file | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| credit_spread_change | macro/vintage | WRDS macro feature file | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| real_yield_level | macro/vintage | WRDS macro feature file | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| real_yield_change | macro/vintage | WRDS macro feature file | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
| dxy_momentum | macro/vintage | WRDS macro feature file | 2019-01-04 | 2026-06-19 | 100.00% | weekly feature matrix shifted one rebalance period before prediction |
