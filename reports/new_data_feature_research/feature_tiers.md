# Feature tiers

Tier-1 rule: strong development evidence, stable sign, economic interpretability, non-redundancy versus existing Tier-1 macro/crypto features, and reasonable holdout diagnostic sign consistency.

Strategy testing requires at least **3 Genuine New / Alternative Data Tier-1** features. Additional WRDS/macro extensions are reported separately and do not count toward this gate.

## Tier counts

| Tier | Count |
|---|---|
| New Data Tier 3 | 38 |
| New Data Tier 2 | 9 |
| New Data Tier 1 | 2 |

## Tier-1 audit classification

- Original statistical Tier-1 count: 2
- Genuine new / alternative-data Tier-1 count: 1
- Additional macro / WRDS-extension Tier-1 count: 1
- Existing control / redundancy Tier-1 count: 0
- Genuine new / alternative-data Tier-1 features: funding_change
- Additional macro / WRDS-extension Tier-1 features: credit_spread_level

## Feature classifications

| Feature | Family | Evidence group | Tier | Best target | Dev IC | NW t | p-value | AUC | CPCV stability | Macro redundancy | Crypto redundancy | Holdout sign | Reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| active_address_growth_7d | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 2 | eth_outperforms_btc_30d | 0.075 | 1.625 | 0.104 | 0.546 | 93.33% | 6.86% | 9.30% | No | Some development evidence, but weaker significance/stability or partial redundancy. |
| active_address_growth_30d | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 2 | eth_outperforms_btc_30d | 0.090 | 0.838 | 0.402 | 0.556 | 80.00% | 15.29% | 27.59% | Yes | Some development evidence, but weaker significance/stability or partial redundancy. |
| transaction_count_growth_7d | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 2 | frozen_macro_drawdown_avoidance | 0.065 | 2.107 | 0.035 | 0.537 | 86.67% | 6.34% | 6.53% | No | Some development evidence, but weaker significance/stability or partial redundancy. |
| transaction_count_growth_30d | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 2 | eth_outperforms_btc_30d | 0.093 | 1.059 | 0.289 | 0.557 | 80.00% | 15.24% | 13.41% | Yes | Some development evidence, but weaker significance/stability or partial redundancy. |
| funding_level | derivatives/crowding | Genuine New / Alternative Data Tier-1 | New Data Tier 2 | eth_outperforms_btc_30d | 0.160 | 1.943 | 0.052 | 0.599 | 86.67% | 31.04% | 65.66% | Yes | Some development evidence, but weaker significance/stability or partial redundancy. |
| funding_change | derivatives/crowding | Genuine New / Alternative Data Tier-1 | New Data Tier 1 | frozen_macro_drawdown_avoidance | 0.102 | 2.189 | 0.029 | 0.559 | 100.00% | 19.04% | 11.00% | Yes | Strong development IC/t-stat, stable CPCV sign, non-redundant, and holdout sign diagnostic is consistent. |
| open_interest_growth | derivatives/crowding | Genuine New / Alternative Data Tier-1 | New Data Tier 3 | btc_forward_30d_return | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Weak, unstable, redundant, or no holdout diagnostic support. |
| long_short_ratio | derivatives/crowding | Genuine New / Alternative Data Tier-1 | New Data Tier 3 | btc_forward_30d_return | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Weak, unstable, redundant, or no holdout diagnostic support. |
| taker_buy_sell_imbalance | derivatives/crowding | Genuine New / Alternative Data Tier-1 | New Data Tier 3 | btc_forward_30d_return | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Weak, unstable, redundant, or no holdout diagnostic support. |
| leverage_crowding_score | derivatives/crowding | Genuine New / Alternative Data Tier-1 | New Data Tier 3 | btc_forward_30d_return | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Weak, unstable, redundant, or no holdout diagnostic support. |
| credit_spread_level | macro/vintage | Additional Macro / WRDS Extension Tier-1 | New Data Tier 1 | frozen_macro_drawdown_avoidance | -0.293 | -4.314 | 0.000 | 0.669 | 86.67% | 55.12% | 46.17% | Yes | Strong development IC/t-stat, stable CPCV sign, non-redundant, and holdout sign diagnostic is consistent. |
| credit_spread_change | macro/vintage | Additional Macro / WRDS Extension Tier-1 | New Data Tier 2 | frozen_macro_positive_next_period | -0.127 | 0.110 | 0.912 | 0.575 | 86.67% | 62.92% | 30.70% | No | Some development evidence, but weaker significance/stability or partial redundancy. |
| real_yield_level | macro/vintage | Additional Macro / WRDS Extension Tier-1 | New Data Tier 2 | frozen_macro_drawdown_avoidance | 0.383 | 4.202 | 0.000 | 0.721 | 86.67% | 53.67% | 55.30% | No | Some development evidence, but weaker significance/stability or partial redundancy. |
| real_yield_change | macro/vintage | Additional Macro / WRDS Extension Tier-1 | New Data Tier 2 | eth_outperforms_btc_30d | -0.124 | -0.919 | 0.358 | 0.577 | 73.33% | 40.54% | 23.84% | No | Some development evidence, but weaker significance/stability or partial redundancy. |
| dxy_momentum | macro/vintage | Additional Macro / WRDS Extension Tier-1 | New Data Tier 2 | eth_outperforms_btc_30d | 0.132 | 2.330 | 0.020 | 0.582 | 93.33% | 52.58% | 22.86% | No | Some development evidence, but weaker significance/stability or partial redundancy. |
| exchange_netflow_7d | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| exchange_netflow_30d | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| exchange_pressure_percentile | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| mvrv_level | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| mvrv_percentile | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| realized_cap_growth_30d | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| holder_accumulation_proxy | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| whale_accumulation_proxy | on-chain | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| etf_net_flow_1d | ETF flows | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| etf_net_flow_5d | ETF flows | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| etf_net_flow_21d | ETF flows | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| etf_flow_acceleration | ETF flows | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| etf_flow_percentile | ETF flows | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| etf_inflow_streak | ETF flows | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| etf_outflow_shock | ETF flows | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| etf_flow_as_aum_if_available | ETF flows | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| iv_level | options-implied | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| iv_change_7d | options-implied | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| iv_change_30d | options-implied | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| iv_term_slope | options-implied | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| skew_level | options-implied | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| skew_change | options-implied | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| put_call_ratio | options-implied | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| risk_reversal | options-implied | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| option_oi_change | options-implied | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| liquidation_shock | derivatives/crowding | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| asset_manager_net_position | COT/CME | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| leveraged_fund_net_position | COT/CME | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| dealer_net_position | COT/CME | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| positioning_change_1w | COT/CME | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| positioning_percentile | COT/CME | Genuine New / Alternative Data Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| liquidity_growth | macro/vintage | Additional Macro / WRDS Extension Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| financial_conditions_level | macro/vintage | Additional Macro / WRDS Extension Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
| financial_conditions_change | macro/vintage | Additional Macro / WRDS Extension Tier-1 | New Data Tier 3 |  | N/A | N/A | N/A | N/A | N/A | N/A | N/A | No | Unavailable or unusable under strict acceptance rules. |
