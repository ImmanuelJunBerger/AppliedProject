# Feature research

Feature research was performed before any strategy test. Holdout columns are diagnostics only and were not used for feature selection.

| Feature | Target | Type | Full IC | Dev IC | Holdout IC | NW t | p-value | AUC | Sign stable | CPCV stability | Macro redundancy | Crypto redundancy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| active_address_growth_7d | btc_forward_30d_return | continuous | -0.013 | -0.024 | 0.066 | 0.138 | 0.890 | N/A | No | 60.00% | 6.86% | 9.30% |
| active_address_growth_7d | eth_forward_30d_return | continuous | 0.016 | 0.029 | 0.063 | 1.049 | 0.294 | N/A | Yes | 86.67% | 6.86% | 9.30% |
| active_address_growth_7d | btc_eth_50_50_forward_30d_return | continuous | 0.007 | 0.014 | 0.065 | 0.728 | 0.466 | N/A | Yes | 46.67% | 6.86% | 9.30% |
| active_address_growth_7d | btc_upward_expansion_30d | binary | -0.032 | -0.037 | 0.005 | -0.055 | 0.956 | 0.524 | No | 66.67% | 6.86% | 9.30% |
| active_address_growth_7d | eth_upward_expansion_30d | binary | 0.019 | 0.024 | 0.076 | 0.983 | 0.326 | 0.516 | Yes | 66.67% | 6.86% | 9.30% |
| active_address_growth_7d | eth_outperforms_btc_30d | binary | 0.057 | 0.075 | -0.013 | 1.625 | 0.104 | 0.546 | No | 93.33% | 6.86% | 9.30% |
| active_address_growth_7d | frozen_macro_positive_next_period | binary | -0.019 | 0.022 | -0.136 | 1.188 | 0.235 | 0.513 | No | 60.00% | 6.86% | 9.30% |
| active_address_growth_7d | frozen_macro_drawdown_avoidance | binary | -0.027 | -0.029 | -0.020 | -0.408 | 0.683 | 0.517 | Yes | 66.67% | 6.86% | 9.30% |
| active_address_growth_30d | btc_forward_30d_return | continuous | 0.048 | -0.013 | 0.068 | -0.020 | 0.984 | N/A | No | 66.67% | 15.29% | 27.59% |
| active_address_growth_30d | eth_forward_30d_return | continuous | 0.100 | 0.044 | 0.143 | 0.791 | 0.429 | N/A | Yes | 73.33% | 15.29% | 27.59% |
| active_address_growth_30d | btc_eth_50_50_forward_30d_return | continuous | 0.086 | 0.027 | 0.123 | 0.487 | 0.626 | N/A | Yes | 73.33% | 15.29% | 27.59% |
| active_address_growth_30d | btc_upward_expansion_30d | binary | 0.048 | -0.010 | 0.018 | 0.073 | 0.941 | 0.506 | No | 60.00% | 15.29% | 27.59% |
| active_address_growth_30d | eth_upward_expansion_30d | binary | 0.094 | 0.034 | 0.204 | 0.208 | 0.836 | 0.522 | Yes | 40.00% | 15.29% | 27.59% |
| active_address_growth_30d | eth_outperforms_btc_30d | binary | 0.078 | 0.090 | 0.041 | 0.838 | 0.402 | 0.556 | Yes | 80.00% | 15.29% | 27.59% |
| active_address_growth_30d | frozen_macro_positive_next_period | binary | -0.001 | 0.004 | 0.138 | 0.386 | 0.700 | 0.502 | Yes | 46.67% | 15.29% | 27.59% |
| active_address_growth_30d | frozen_macro_drawdown_avoidance | binary | 0.013 | -0.032 | 0.079 | -0.684 | 0.494 | 0.519 | No | 60.00% | 15.29% | 27.59% |
| transaction_count_growth_7d | btc_forward_30d_return | continuous | -0.039 | -0.056 | -0.001 | -1.162 | 0.245 | N/A | Yes | 93.33% | 6.34% | 6.53% |
| transaction_count_growth_7d | eth_forward_30d_return | continuous | -0.021 | -0.028 | -0.011 | -1.055 | 0.292 | N/A | Yes | 60.00% | 6.34% | 6.53% |
| transaction_count_growth_7d | btc_eth_50_50_forward_30d_return | continuous | -0.029 | -0.041 | 0.009 | -1.197 | 0.231 | N/A | No | 80.00% | 6.34% | 6.53% |
| transaction_count_growth_7d | btc_upward_expansion_30d | binary | 0.003 | 0.015 | 0.075 | 0.496 | 0.620 | 0.510 | Yes | 60.00% | 6.34% | 6.53% |
| transaction_count_growth_7d | eth_upward_expansion_30d | binary | -0.044 | -0.029 | -0.007 | -0.612 | 0.540 | 0.519 | Yes | 66.67% | 6.34% | 6.53% |
| transaction_count_growth_7d | eth_outperforms_btc_30d | binary | -0.013 | -0.012 | -0.031 | -0.740 | 0.459 | 0.507 | Yes | 53.33% | 6.34% | 6.53% |
| transaction_count_growth_7d | frozen_macro_positive_next_period | binary | -0.023 | -0.027 | 0.010 | -0.904 | 0.366 | 0.516 | No | 73.33% | 6.34% | 6.53% |
| transaction_count_growth_7d | frozen_macro_drawdown_avoidance | binary | 0.046 | 0.065 | -0.008 | 2.107 | 0.035 | 0.537 | No | 86.67% | 6.34% | 6.53% |
| transaction_count_growth_30d | btc_forward_30d_return | continuous | -0.008 | -0.080 | 0.206 | -0.785 | 0.432 | N/A | No | 73.33% | 15.24% | 13.41% |
| transaction_count_growth_30d | eth_forward_30d_return | continuous | 0.059 | -0.013 | 0.245 | -0.195 | 0.845 | N/A | No | 53.33% | 15.24% | 13.41% |
| transaction_count_growth_30d | btc_eth_50_50_forward_30d_return | continuous | 0.033 | -0.043 | 0.266 | -0.513 | 0.608 | N/A | No | 60.00% | 15.24% | 13.41% |
| transaction_count_growth_30d | btc_upward_expansion_30d | binary | -0.003 | 0.000 | -0.033 | -0.202 | 0.840 | 0.500 | No | 53.33% | 15.24% | 13.41% |
| transaction_count_growth_30d | eth_upward_expansion_30d | binary | 0.055 | 0.024 | 0.191 | 0.003 | 0.998 | 0.516 | Yes | 53.33% | 15.24% | 13.41% |
| transaction_count_growth_30d | eth_outperforms_btc_30d | binary | 0.106 | 0.093 | 0.154 | 1.059 | 0.289 | 0.557 | Yes | 80.00% | 15.24% | 13.41% |
| transaction_count_growth_30d | frozen_macro_positive_next_period | binary | 0.018 | 0.002 | 0.072 | -0.202 | 0.840 | 0.501 | Yes | 33.33% | 15.24% | 13.41% |
| transaction_count_growth_30d | frozen_macro_drawdown_avoidance | binary | -0.009 | -0.022 | 0.015 | 0.466 | 0.642 | 0.513 | No | 46.67% | 15.24% | 13.41% |
| funding_level | btc_forward_30d_return | continuous | 0.040 | -0.018 | -0.170 | -0.308 | 0.758 | N/A | Yes | 73.33% | 31.04% | 65.66% |
| funding_level | eth_forward_30d_return | continuous | 0.131 | 0.098 | -0.062 | 0.999 | 0.318 | N/A | No | 60.00% | 31.04% | 65.66% |
| funding_level | btc_eth_50_50_forward_30d_return | continuous | 0.108 | 0.067 | -0.084 | 0.514 | 0.607 | N/A | No | 53.33% | 31.04% | 65.66% |
| funding_level | btc_upward_expansion_30d | binary | 0.120 | 0.065 | -0.185 | 0.344 | 0.731 | 0.542 | No | 40.00% | 31.04% | 65.66% |
| funding_level | eth_upward_expansion_30d | binary | 0.137 | 0.111 | 0.147 | 1.615 | 0.106 | 0.573 | Yes | 46.67% | 31.04% | 65.66% |
| funding_level | eth_outperforms_btc_30d | binary | 0.170 | 0.160 | 0.158 | 1.943 | 0.052 | 0.599 | Yes | 86.67% | 31.04% | 65.66% |
| funding_level | frozen_macro_positive_next_period | binary | -0.053 | -0.036 | -0.228 | -0.186 | 0.852 | 0.521 | Yes | 66.67% | 31.04% | 65.66% |
| funding_level | frozen_macro_drawdown_avoidance | binary | 0.058 | 0.089 | -0.077 | -0.223 | 0.824 | 0.551 | No | 73.33% | 31.04% | 65.66% |
| funding_change | btc_forward_30d_return | continuous | 0.040 | 0.026 | 0.020 | -0.116 | 0.907 | N/A | Yes | 73.33% | 19.04% | 11.00% |
| funding_change | eth_forward_30d_return | continuous | 0.057 | 0.058 | 0.051 | 0.647 | 0.518 | N/A | Yes | 93.33% | 19.04% | 11.00% |
| funding_change | btc_eth_50_50_forward_30d_return | continuous | 0.051 | 0.047 | 0.034 | 0.365 | 0.715 | N/A | Yes | 80.00% | 19.04% | 11.00% |
| funding_change | btc_upward_expansion_30d | binary | 0.010 | 0.001 | -0.046 | -1.001 | 0.317 | 0.501 | No | 40.00% | 19.04% | 11.00% |
| funding_change | eth_upward_expansion_30d | binary | 0.032 | 0.039 | 0.024 | 1.889 | 0.059 | 0.525 | Yes | 66.67% | 19.04% | 11.00% |
| funding_change | eth_outperforms_btc_30d | binary | 0.018 | 0.026 | 0.025 | 1.733 | 0.083 | 0.516 | Yes | 66.67% | 19.04% | 11.00% |
| funding_change | frozen_macro_positive_next_period | binary | -0.054 | -0.046 | -0.007 | 0.433 | 0.665 | 0.527 | Yes | 86.67% | 19.04% | 11.00% |
| funding_change | frozen_macro_drawdown_avoidance | binary | 0.094 | 0.102 | 0.033 | 2.189 | 0.029 | 0.559 | Yes | 100.00% | 19.04% | 11.00% |
| open_interest_growth | btc_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| open_interest_growth | eth_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| open_interest_growth | btc_eth_50_50_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| open_interest_growth | btc_upward_expansion_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| open_interest_growth | eth_upward_expansion_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| open_interest_growth | eth_outperforms_btc_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| open_interest_growth | frozen_macro_positive_next_period | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| open_interest_growth | frozen_macro_drawdown_avoidance | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| long_short_ratio | btc_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| long_short_ratio | eth_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| long_short_ratio | btc_eth_50_50_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| long_short_ratio | btc_upward_expansion_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| long_short_ratio | eth_upward_expansion_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| long_short_ratio | eth_outperforms_btc_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| long_short_ratio | frozen_macro_positive_next_period | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| long_short_ratio | frozen_macro_drawdown_avoidance | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| taker_buy_sell_imbalance | btc_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| taker_buy_sell_imbalance | eth_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| taker_buy_sell_imbalance | btc_eth_50_50_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| taker_buy_sell_imbalance | btc_upward_expansion_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| taker_buy_sell_imbalance | eth_upward_expansion_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| taker_buy_sell_imbalance | eth_outperforms_btc_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| taker_buy_sell_imbalance | frozen_macro_positive_next_period | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| taker_buy_sell_imbalance | frozen_macro_drawdown_avoidance | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| leverage_crowding_score | btc_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| leverage_crowding_score | eth_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| leverage_crowding_score | btc_eth_50_50_forward_30d_return | continuous | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| leverage_crowding_score | btc_upward_expansion_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| leverage_crowding_score | eth_upward_expansion_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| leverage_crowding_score | eth_outperforms_btc_30d | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| leverage_crowding_score | frozen_macro_positive_next_period | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| leverage_crowding_score | frozen_macro_drawdown_avoidance | binary | N/A | N/A | N/A | N/A | N/A | N/A | No | N/A | N/A | N/A |
| credit_spread_level | btc_forward_30d_return | continuous | 0.156 | 0.078 | -0.077 | 1.515 | 0.130 | N/A | No | 66.67% | 55.12% | 46.17% |
| credit_spread_level | eth_forward_30d_return | continuous | 0.159 | 0.119 | -0.239 | 2.154 | 0.031 | N/A | No | 80.00% | 55.12% | 46.17% |
| credit_spread_level | btc_eth_50_50_forward_30d_return | continuous | 0.160 | 0.099 | -0.182 | 2.035 | 0.042 | N/A | No | 73.33% | 55.12% | 46.17% |
| credit_spread_level | btc_upward_expansion_30d | binary | 0.177 | 0.065 | -0.054 | 1.300 | 0.193 | 0.542 | No | 53.33% | 55.12% | 46.17% |
| credit_spread_level | eth_upward_expansion_30d | binary | 0.082 | 0.031 | -0.084 | 0.923 | 0.356 | 0.520 | No | 40.00% | 55.12% | 46.17% |
| credit_spread_level | eth_outperforms_btc_30d | binary | 0.069 | 0.039 | -0.106 | 1.542 | 0.123 | 0.524 | No | 53.33% | 55.12% | 46.17% |
| credit_spread_level | frozen_macro_positive_next_period | binary | 0.133 | 0.212 | -0.139 | 4.955 | 0.000 | 0.626 | No | 100.00% | 55.12% | 46.17% |
| credit_spread_level | frozen_macro_drawdown_avoidance | binary | -0.232 | -0.293 | -0.060 | -4.314 | 0.000 | 0.669 | Yes | 86.67% | 55.12% | 46.17% |
| credit_spread_change | btc_forward_30d_return | continuous | -0.018 | -0.015 | 0.179 | 0.294 | 0.769 | N/A | No | 46.67% | 62.92% | 30.70% |
| credit_spread_change | eth_forward_30d_return | continuous | -0.030 | -0.017 | 0.117 | 1.026 | 0.305 | N/A | No | 60.00% | 62.92% | 30.70% |
| credit_spread_change | btc_eth_50_50_forward_30d_return | continuous | -0.024 | -0.015 | 0.137 | 0.761 | 0.447 | N/A | No | 46.67% | 62.92% | 30.70% |
| credit_spread_change | btc_upward_expansion_30d | binary | 0.003 | -0.007 | 0.034 | 0.846 | 0.398 | 0.505 | No | 46.67% | 62.92% | 30.70% |
| credit_spread_change | eth_upward_expansion_30d | binary | -0.006 | 0.003 | 0.053 | 1.378 | 0.168 | 0.502 | Yes | 53.33% | 62.92% | 30.70% |
| credit_spread_change | eth_outperforms_btc_30d | binary | 0.025 | 0.061 | 0.066 | 2.350 | 0.019 | 0.538 | Yes | 66.67% | 62.92% | 30.70% |
| credit_spread_change | frozen_macro_positive_next_period | binary | -0.088 | -0.127 | 0.166 | 0.110 | 0.912 | 0.575 | No | 86.67% | 62.92% | 30.70% |
| credit_spread_change | frozen_macro_drawdown_avoidance | binary | -0.012 | -0.019 | 0.171 | -0.887 | 0.375 | 0.511 | No | 66.67% | 62.92% | 30.70% |
| real_yield_level | btc_forward_30d_return | continuous | -0.045 | 0.026 | -0.037 | -0.047 | 0.963 | N/A | No | 60.00% | 53.67% | 55.30% |
| real_yield_level | eth_forward_30d_return | continuous | -0.129 | -0.095 | -0.194 | -1.430 | 0.153 | N/A | Yes | 46.67% | 53.67% | 55.30% |
| real_yield_level | btc_eth_50_50_forward_30d_return | continuous | -0.104 | -0.054 | -0.147 | -0.849 | 0.396 | N/A | Yes | 46.67% | 53.67% | 55.30% |
| real_yield_level | btc_upward_expansion_30d | binary | -0.223 | -0.167 | -0.054 | -1.521 | 0.128 | 0.609 | Yes | 73.33% | 53.67% | 55.30% |
| real_yield_level | eth_upward_expansion_30d | binary | -0.185 | -0.191 | -0.084 | -2.118 | 0.034 | 0.626 | Yes | 60.00% | 53.67% | 55.30% |
| real_yield_level | eth_outperforms_btc_30d | binary | -0.246 | -0.296 | -0.106 | -3.693 | 0.000 | 0.684 | Yes | 93.33% | 53.67% | 55.30% |
| real_yield_level | frozen_macro_positive_next_period | binary | -0.115 | -0.135 | -0.139 | -2.055 | 0.040 | 0.580 | Yes | 80.00% | 53.67% | 55.30% |
| real_yield_level | frozen_macro_drawdown_avoidance | binary | 0.330 | 0.383 | -0.261 | 4.202 | 0.000 | 0.721 | No | 86.67% | 53.67% | 55.30% |
| real_yield_change | btc_forward_30d_return | continuous | 0.029 | 0.060 | 0.234 | 0.361 | 0.718 | N/A | Yes | 66.67% | 40.54% | 23.84% |
| real_yield_change | eth_forward_30d_return | continuous | 0.007 | -0.000 | 0.136 | -0.311 | 0.756 | N/A | No | 46.67% | 40.54% | 23.84% |
| real_yield_change | btc_eth_50_50_forward_30d_return | continuous | 0.020 | 0.030 | 0.157 | -0.017 | 0.986 | N/A | Yes | 66.67% | 40.54% | 23.84% |
| real_yield_change | btc_upward_expansion_30d | binary | 0.027 | 0.070 | 0.024 | 0.429 | 0.668 | 0.546 | Yes | 73.33% | 40.54% | 23.84% |
| real_yield_change | eth_upward_expansion_30d | binary | 0.044 | 0.044 | 0.037 | 0.564 | 0.573 | 0.529 | Yes | 66.67% | 40.54% | 23.84% |
| real_yield_change | eth_outperforms_btc_30d | binary | -0.082 | -0.124 | 0.046 | -0.919 | 0.358 | 0.577 | No | 73.33% | 40.54% | 23.84% |
| real_yield_change | frozen_macro_positive_next_period | binary | -0.014 | -0.049 | -0.029 | -0.667 | 0.505 | 0.529 | Yes | 80.00% | 40.54% | 23.84% |
| real_yield_change | frozen_macro_drawdown_avoidance | binary | 0.051 | 0.062 | 0.113 | 0.598 | 0.550 | 0.536 | Yes | 66.67% | 40.54% | 23.84% |
| dxy_momentum | btc_forward_30d_return | continuous | 0.095 | 0.069 | 0.009 | 0.603 | 0.547 | N/A | Yes | 80.00% | 52.58% | 22.86% |
| dxy_momentum | eth_forward_30d_return | continuous | 0.103 | 0.095 | -0.153 | 0.787 | 0.431 | N/A | No | 86.67% | 52.58% | 22.86% |
| dxy_momentum | btc_eth_50_50_forward_30d_return | continuous | 0.108 | 0.092 | -0.101 | 0.736 | 0.462 | N/A | No | 86.67% | 52.58% | 22.86% |
| dxy_momentum | btc_upward_expansion_30d | binary | 0.108 | 0.090 | -0.034 | 1.462 | 0.144 | 0.559 | No | 80.00% | 52.58% | 22.86% |
| dxy_momentum | eth_upward_expansion_30d | binary | 0.098 | 0.095 | -0.053 | 1.529 | 0.126 | 0.562 | No | 86.67% | 52.58% | 22.86% |
| dxy_momentum | eth_outperforms_btc_30d | binary | 0.110 | 0.132 | -0.066 | 2.330 | 0.020 | 0.582 | No | 93.33% | 52.58% | 22.86% |
| dxy_momentum | frozen_macro_positive_next_period | binary | -0.051 | -0.053 | -0.008 | -0.260 | 0.795 | 0.531 | Yes | 66.67% | 52.58% | 22.86% |
| dxy_momentum | frozen_macro_drawdown_avoidance | binary | 0.076 | 0.057 | -0.160 | 0.173 | 0.862 | 0.533 | No | 53.33% | 52.58% | 22.86% |

---

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

