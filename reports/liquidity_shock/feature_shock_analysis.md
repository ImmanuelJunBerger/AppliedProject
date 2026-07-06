# Feature shock analysis

Shock features are computed as z-scores and percentile ranks versus the prior
180-day distribution. The table below ranks the strongest top-minus-bottom
target spreads across development and holdout diagnostics.

| Split | Feature | Target | Obs | Spearman IC | Bottom quintile target | Top quintile target | Top-bottom |
|---|---|---|---|---|---|---|---|
| holdout | tvl_growth_30d_shock_z | target_btc_eth_2w | 75 | 0.177 | -3.19% | 2.55% | 5.74% |
| holdout | market_breadth_7d_shock_z | target_btc_eth_2w | 75 | 0.105 | -4.67% | 0.85% | 5.52% |
| holdout | combined_liquidity_risk_shock_index | target_btc_eth_2w | 75 | 0.158 | -1.74% | 3.78% | 5.52% |
| development | volatility_4h_7d_shock_z | target_btc_eth_2w | 261 | 0.109 | 3.08% | 8.45% | 5.37% |
| development | volatility_4h_7d_shock_z | target_top10_basket_1w | 261 | 0.113 | -0.03% | 4.64% | 4.67% |
| holdout | stablecoin_supply_change_7d_shock_z | target_top10_basket_1w | 76 | 0.154 | -3.23% | 0.97% | 4.20% |
| holdout | stablecoin_supply_change_7d_shock_z | target_btc_eth_1w | 76 | 0.176 | -3.28% | 0.81% | 4.08% |
| holdout | combined_liquidity_risk_shock_index | target_csm_spread_1w | 76 | 0.123 | 0.04% | 4.11% | 4.08% |
| development | market_breadth_7d_shock_z | target_top10_basket_1w | 261 | 0.092 | 1.15% | 5.09% | 3.94% |
| development | volatility_4h_7d_shock_z | target_btc_eth_1w | 261 | 0.103 | 0.59% | 4.07% | 3.48% |
| holdout | stablecoin_supply_change_7d_shock_z | target_btc_eth_2w | 75 | 0.094 | -4.95% | -1.75% | 3.20% |
| holdout | combined_liquidity_risk_shock_index | target_btc_eth_1w | 76 | 0.174 | -0.91% | 1.92% | 2.84% |
| holdout | volatility_4h_7d_shock_z | target_btc_eth_2w | 75 | 0.055 | -4.96% | -2.18% | 2.78% |
| development | market_breadth_7d_shock_z | target_btc_eth_1w | 261 | 0.049 | 2.10% | 4.83% | 2.73% |
| holdout | tvl_growth_30d_shock_z | target_btc_eth_1w | 76 | 0.157 | -1.02% | 1.49% | 2.51% |
| holdout | market_volume_change_7d_shock_z | target_csm_spread_1w | 76 | -0.035 | -2.17% | 0.22% | 2.39% |
| development | cross_sectional_dispersion_shock_z | target_btc_eth_2w | 261 | 0.029 | 1.82% | 4.14% | 2.32% |
| development | stablecoin_supply_change_7d_shock_z | target_top10_basket_1w | 261 | 0.051 | 1.04% | 3.35% | 2.31% |
| holdout | combined_liquidity_risk_shock_index | target_top10_basket_1w | 76 | 0.134 | -1.02% | 1.26% | 2.28% |
| holdout | market_breadth_7d_shock_z | target_btc_eth_1w | 76 | 0.039 | -1.27% | 0.99% | 2.26% |
| holdout | stablecoin_supply_change_7d_shock_z | target_reversal_spread_1w | 76 | 0.118 | 1.16% | 3.39% | 2.23% |
| holdout | cross_sectional_dispersion_shock_z | target_reversal_spread_1w | 76 | 0.163 | -1.19% | 1.03% | 2.22% |
| development | tvl_growth_30d_shock_z | target_csm_spread_1w | 261 | 0.091 | -0.53% | 1.68% | 2.21% |
| development | combined_liquidity_risk_shock_index | target_csm_spread_1w | 261 | 0.070 | 0.05% | 2.20% | 2.15% |
| holdout | volatility_4h_7d_shock_z | target_top10_basket_1w | 76 | 0.052 | -2.63% | -0.55% | 2.08% |
| holdout | volatility_4h_7d_shock_z | target_btc_eth_1w | 76 | 0.027 | -2.50% | -0.62% | 1.89% |
| holdout | market_breadth_7d_shock_z | target_top10_basket_1w | 76 | -0.004 | -1.18% | 0.70% | 1.88% |
| holdout | volatility_4h_7d_shock_z | target_reversal_spread_1w | 76 | 0.082 | -0.99% | 0.78% | 1.76% |
| holdout | market_volume_change_7d_shock_z | target_reversal_spread_1w | 76 | 0.103 | -1.18% | 0.56% | 1.74% |
| development | cross_sectional_dispersion_shock_z | target_csm_spread_1w | 261 | 0.071 | 1.02% | 2.72% | 1.70% |
