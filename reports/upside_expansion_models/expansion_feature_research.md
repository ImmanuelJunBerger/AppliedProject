# Expansion feature research

Selection discipline: feature evidence is evaluated on the development period.
Holdout IC/AUC is reported as a diagnostic only and is not used to alter the
current final candidate.

## Top feature-target diagnostics

| Feature | Target | Target label | Dev IC | Mean fold IC | NW t | p-value | Stable folds | Dev AUC | Holdout IC | Holdout AUC | Holdout sign consistent |
|---|---|---|---|---|---|---|---|---|---|---|---|
| eth_btc_breakout_strength | eth_30d_upside | ETH 30d > +20% | -0.292 | -0.263 | -6.782 | 0.000 | 100.00% | 0.688 | 0.046 | 0.537 | No |
| eth_btc_breakout_strength | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.271 | -0.243 | -6.184 | 0.000 | 100.00% | 0.668 | -0.089 | 0.575 | Yes |
| recovery_from_drawdown | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.271 | 0.185 | 4.432 | 0.000 | 86.67% | 0.667 | 0.203 | 0.641 | Yes |
| tvl_percentile | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.251 | 0.186 | 4.594 | 0.000 | 93.33% | 0.654 | 0.132 | 0.592 | Yes |
| eth_btc_relative_strength_63d | eth_30d_upside | ETH 30d > +20% | -0.237 | -0.260 | -6.346 | 0.000 | 93.33% | 0.652 | 0.078 | 0.563 | No |
| jump_intensity | eth_vs_btc_leadership | ETH beats BTC by +5% | -0.244 | -0.230 | -4.511 | 0.000 | 86.67% | 0.647 | -0.048 | 0.532 | Yes |
| stablecoin_supply_7d_30d_spread | eth_30d_upside | ETH 30d > +20% | -0.217 | -0.076 | -1.351 | 0.177 | 66.67% | 0.639 | 0.042 | 0.534 | No |
| distance_from_30d_lows | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.215 | 0.166 | 5.134 | 0.000 | 93.33% | 0.633 | 0.283 | 0.697 | Yes |
| stablecoin_supply_7d_30d_spread | eth_vs_btc_leadership | ETH beats BTC by +5% | -0.208 | -0.104 | -2.298 | 0.022 | 66.67% | 0.628 | 0.050 | 0.535 | No |
| eth_btc_breakout_strength | btc_30d_upside | BTC 30d > +15% | -0.195 | -0.175 | -5.577 | 0.000 | 100.00% | 0.625 | -0.206 | 0.735 | Yes |
| stablecoin_supply_percentile | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.202 | 0.141 | 3.915 | 0.000 | 73.33% | 0.622 | 0.194 | 0.628 | Yes |
| eth_btc_relative_strength_30d | eth_30d_upside | ETH 30d > +20% | -0.184 | -0.197 | -6.895 | 0.000 | 100.00% | 0.618 | -0.033 | 0.526 | Yes |
| upside_semivariance | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.188 | 0.118 | 3.661 | 0.000 | 73.33% | 0.616 | 0.162 | 0.613 | Yes |
| eth_btc_breakout_strength | eth_vs_btc_leadership | ETH beats BTC by +5% | -0.188 | -0.180 | -8.476 | 0.000 | 100.00% | 0.616 | 0.071 | 0.549 | No |
| eth_btc_relative_strength_63d | eth_vs_btc_leadership | ETH beats BTC by +5% | -0.185 | -0.249 | -9.113 | 0.000 | 100.00% | 0.614 | 0.083 | 0.558 | No |
| eth_btc_relative_strength_30d | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.182 | -0.189 | -4.218 | 0.000 | 100.00% | 0.613 | -0.138 | 0.616 | Yes |
| stablecoin_supply_percentile | eth_30d_upside | ETH 30d > +20% | 0.178 | 0.080 | 1.812 | 0.070 | 60.00% | 0.612 | 0.178 | 0.636 | Yes |
| stablecoin_supply_7d_30d_spread | btc_30d_upside | BTC 30d > +15% | -0.173 | -0.081 | -1.991 | 0.046 | 66.67% | 0.611 | 0.069 | 0.579 | No |
| assets_rebounding_from_30d_lows_pct | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.179 | 0.130 | 4.096 | 0.000 | 93.33% | 0.610 | 0.322 | 0.724 | Yes |
| tvl_percentile | eth_30d_upside | ETH 30d > +20% | 0.169 | 0.059 | 1.010 | 0.312 | 66.67% | 0.608 | 0.130 | 0.605 | Yes |
| top10_breadth_acceleration | btc_30d_upside | BTC 30d > +15% | 0.169 | 0.158 | 4.032 | 0.000 | 86.67% | 0.607 | 0.009 | 0.510 | Yes |
| distance_from_90d_lows | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.172 | 0.137 | 4.839 | 0.000 | 93.33% | 0.606 | 0.066 | 0.546 | Yes |
| stablecoin_supply_7d_30d_spread | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.167 | -0.058 | -1.313 | 0.189 | 66.67% | 0.604 | 0.095 | 0.579 | No |
| eth_btc_relative_strength_63d | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.163 | -0.191 | -6.087 | 0.000 | 100.00% | 0.601 | -0.091 | 0.576 | Yes |
| top20_30d_high_pct | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.172 | 0.164 | 5.624 | 0.000 | 100.00% | 0.599 | 0.147 | 0.587 | Yes |
| downside_to_upside_volatility_ratio | eth_vs_btc_leadership | ETH beats BTC by +5% | -0.153 | -0.165 | -4.528 | 0.000 | 86.67% | 0.594 | -0.148 | 0.603 | Yes |
| top10_breadth_acceleration | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | 0.151 | 0.142 | 4.278 | 0.000 | 80.00% | 0.593 | 0.079 | 0.566 | Yes |
| upside_semivariance | eth_30d_upside | ETH 30d > +20% | 0.143 | 0.065 | 1.804 | 0.071 | 66.67% | 0.592 | 0.187 | 0.651 | Yes |
| recovery_from_drawdown | eth_30d_upside | ETH 30d > +20% | 0.142 | 0.026 | 0.554 | 0.580 | 53.33% | 0.591 | 0.236 | 0.691 | Yes |
| top20_above_30dma_pct | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.146 | 0.125 | 5.539 | 0.000 | 93.33% | 0.590 | 0.275 | 0.691 | Yes |
| top10_breadth_acceleration | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.145 | 0.147 | 17.519 | 0.000 | 100.00% | 0.589 | 0.193 | 0.634 | Yes |
| dispersion_acceleration | eth_30d_upside | ETH 30d > +20% | -0.134 | -0.155 | -6.431 | 0.000 | 100.00% | 0.586 | -0.102 | 0.582 | Yes |
| equity_momentum_recovery | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.131 | -0.136 | -3.485 | 0.000 | 73.33% | 0.582 | 0.102 | 0.586 | No |
| risk_appetite_recovery_score | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.130 | -0.140 | -4.832 | 0.000 | 80.00% | 0.581 | -0.021 | 0.517 | Yes |
| top20_breadth_acceleration | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.132 | 0.132 | 17.291 | 0.000 | 100.00% | 0.581 | 0.195 | 0.636 | Yes |
| distance_from_180d_lows | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.131 | 0.071 | 1.216 | 0.224 | 60.00% | 0.581 | -0.086 | 0.560 | No |
| volume_confirmation_of_price_trend | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.131 | 0.111 | 4.983 | 0.000 | 93.33% | 0.580 | 0.194 | 0.635 | Yes |
| jump_intensity | eth_30d_upside | ETH 30d > +20% | -0.122 | -0.128 | -11.654 | 0.000 | 100.00% | 0.577 | -0.046 | 0.536 | Yes |
| top20_breadth_acceleration | btc_30d_upside | BTC 30d > +15% | 0.117 | 0.107 | 3.316 | 0.001 | 80.00% | 0.575 | -0.035 | 0.540 | No |
| top20_equal_weight_minus_btc_return_30d | eth_30d_upside | ETH 30d > +20% | -0.116 | -0.135 | -3.551 | 0.000 | 73.33% | 0.575 | 0.040 | 0.532 | No |
| top10_breadth_acceleration | eth_30d_upside | ETH 30d > +20% | 0.117 | 0.105 | 2.319 | 0.020 | 73.33% | 0.575 | 0.211 | 0.669 | Yes |
| risk_appetite_recovery_score | btc_30d_upside | BTC 30d > +15% | -0.116 | -0.130 | -4.317 | 0.000 | 86.67% | 0.574 | -0.363 | 0.915 | Yes |
| tvl_percentile | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | 0.118 | 0.025 | 0.673 | 0.501 | 53.33% | 0.573 | -0.143 | 0.620 | No |
| dispersion_acceleration | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.118 | -0.130 | -4.396 | 0.000 | 86.67% | 0.573 | -0.276 | 0.732 | Yes |
| equity_momentum_recovery | btc_30d_upside | BTC 30d > +15% | -0.113 | -0.126 | -2.266 | 0.023 | 66.67% | 0.573 | 0.031 | 0.535 | No |
| altcoin_leadership_proxy_30d | eth_30d_upside | ETH 30d > +20% | -0.112 | -0.128 | -3.317 | 0.001 | 73.33% | 0.572 | 0.056 | 0.545 | No |
| top20_positive_30d_return_pct | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.116 | 0.092 | 4.716 | 0.000 | 86.67% | 0.572 | 0.178 | 0.624 | Yes |
| volume_acceleration | eth_30d_upside | ETH 30d > +20% | 0.111 | 0.144 | 5.860 | 0.000 | 100.00% | 0.571 | -0.069 | 0.556 | No |
| eth_btc_relative_strength_30d | eth_vs_btc_leadership | ETH beats BTC by +5% | -0.113 | -0.137 | -5.033 | 0.000 | 100.00% | 0.570 | 0.083 | 0.558 | No |
| eth_btc_relative_strength_30d | btc_30d_upside | BTC 30d > +15% | -0.108 | -0.115 | -2.825 | 0.005 | 86.67% | 0.569 | -0.162 | 0.685 | Yes |
| volatility_of_volatility | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | 0.111 | 0.075 | 1.421 | 0.155 | 80.00% | 0.569 | 0.200 | 0.668 | Yes |
| stablecoin_supply_percentile | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | 0.113 | 0.035 | 0.925 | 0.355 | 46.67% | 0.569 | 0.078 | 0.562 | Yes |
| tvl_percentile | btc_30d_upside | BTC 30d > +15% | 0.107 | 0.020 | 0.603 | 0.547 | 60.00% | 0.568 | -0.265 | 0.803 | No |
| stablecoin_supply_percentile | btc_30d_upside | BTC 30d > +15% | 0.109 | 0.050 | 1.406 | 0.160 | 53.33% | 0.568 | -0.046 | 0.550 | No |
| btc_dominance_proxy_change_30d | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | 0.109 | 0.114 | 4.638 | 0.000 | 86.67% | 0.568 | -0.059 | 0.549 | No |
| dispersion_acceleration | btc_30d_upside | BTC 30d > +15% | -0.105 | -0.112 | -3.489 | 0.000 | 80.00% | 0.567 | -0.198 | 0.726 | Yes |
| top20_equal_weight_minus_btc_vol_adj_30d | eth_30d_upside | ETH 30d > +20% | -0.102 | -0.121 | -3.181 | 0.001 | 80.00% | 0.565 | 0.045 | 0.537 | No |
| upside_semivariance | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | 0.102 | 0.059 | 1.705 | 0.088 | 60.00% | 0.564 | 0.170 | 0.643 | Yes |
| volatility_of_volatility | eth_30d_upside | ETH 30d > +20% | 0.099 | 0.056 | 1.338 | 0.181 | 66.67% | 0.563 | -0.042 | 0.534 | No |
| breadth_recovery_from_depressed | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.102 | 0.085 | 4.432 | 0.000 | 86.67% | 0.563 | 0.216 | 0.650 | Yes |
| top20_breadth_acceleration | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | 0.097 | 0.088 | 2.992 | 0.003 | 80.00% | 0.561 | 0.044 | 0.537 | Yes |
| tvl_acceleration | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.096 | 0.102 | 7.541 | 0.000 | 100.00% | 0.559 | 0.080 | 0.556 | Yes |
| top20_equal_weight_minus_btc_return_30d | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.094 | -0.100 | -2.027 | 0.043 | 73.33% | 0.559 | -0.089 | 0.575 | Yes |
| altcoin_leadership_proxy_30d | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.090 | -0.094 | -1.899 | 0.058 | 73.33% | 0.556 | -0.079 | 0.567 | Yes |
| eth_btc_relative_strength_63d | btc_30d_upside | BTC 30d > +15% | -0.087 | -0.114 | -3.862 | 0.000 | 86.67% | 0.555 | -0.299 | 0.841 | Yes |
| volatility_of_volatility | btc_30d_upside | BTC 30d > +15% | 0.086 | 0.052 | 0.899 | 0.368 | 66.67% | 0.555 | 0.309 | 0.853 | Yes |
| top20_breadth_acceleration | eth_30d_upside | ETH 30d > +20% | 0.084 | 0.071 | 1.419 | 0.156 | 60.00% | 0.554 | 0.209 | 0.669 | Yes |
| tvl_7d_30d_spread | eth_vs_btc_leadership | ETH beats BTC by +5% | -0.087 | -0.020 | -0.445 | 0.656 | 53.33% | 0.554 | -0.104 | 0.572 | Yes |
| top20_equal_weight_minus_btc_vol_adj_30d | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | -0.085 | -0.092 | -2.182 | 0.029 | 73.33% | 0.553 | -0.083 | 0.570 | Yes |
| recovery_from_drawdown | btc_30d_upside | BTC 30d > +15% | 0.082 | 0.006 | 0.135 | 0.892 | 66.67% | 0.553 | -0.072 | 0.582 | No |
| abnormal_volume_zscore | eth_30d_upside | ETH 30d > +20% | 0.082 | 0.087 | 5.991 | 0.000 | 100.00% | 0.553 | -0.013 | 0.510 | No |
| recovery_from_drawdown | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | 0.084 | -0.001 | -0.013 | 0.989 | 60.00% | 0.552 | 0.064 | 0.554 | Yes |
| distance_from_30d_lows | eth_30d_upside | ETH 30d > +20% | 0.079 | -0.005 | -0.159 | 0.874 | 60.00% | 0.551 | 0.258 | 0.708 | Yes |
| volume_acceleration | btc_eth_50_50_30d_upside | BTC/ETH 50-50 30d > +15% | 0.081 | 0.102 | 3.687 | 0.000 | 86.67% | 0.550 | 0.100 | 0.584 | Yes |
| btc_dominance_proxy_change_30d | btc_30d_upside | BTC 30d > +15% | 0.076 | 0.085 | 7.789 | 0.000 | 86.67% | 0.549 | -0.072 | 0.582 | No |
| market_dollar_volume_growth_30d | eth_vs_btc_leadership | ETH beats BTC by +5% | 0.079 | 0.065 | 2.086 | 0.037 | 80.00% | 0.549 | 0.140 | 0.598 | Yes |
| btc_dominance_proxy_change_30d | eth_30d_upside | ETH 30d > +20% | 0.071 | 0.087 | 5.613 | 0.000 | 100.00% | 0.546 | -0.180 | 0.645 | No |
| combined_crypto_liquidity_impulse | eth_30d_upside | ETH 30d > +20% | 0.071 | 0.081 | 3.045 | 0.002 | 86.67% | 0.546 | 0.087 | 0.570 | Yes |
| risk_appetite_recovery_score | eth_30d_upside | ETH 30d > +20% | -0.071 | -0.082 | -3.070 | 0.002 | 86.67% | 0.546 | 0.209 | 0.669 | No |
| tvl_7d_30d_spread | btc_30d_upside | BTC 30d > +15% | -0.069 | -0.044 | -1.113 | 0.266 | 66.67% | 0.544 | -0.028 | 0.532 | Yes |
