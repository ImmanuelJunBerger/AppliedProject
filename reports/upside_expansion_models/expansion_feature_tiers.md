# Expansion feature tiers

Tiering rules:

- Expansion Tier 1: development evidence, CPCV stability, not highly redundant, and holdout sign diagnostic consistency.
- Expansion Tier 2: promising but weaker development evidence or stability.
- Expansion Tier 3: unstable, redundant, or no evidence.

No new expansion-specific feature was added to the final candidate in this run.

| Feature | Family | Best target | Tier | Dev AUC | Dev IC | NW t | Stable folds | Holdout IC | Holdout AUC | Max |corr| | Reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| recovery_from_drawdown | recovery_capitulation | eth_vs_btc_leadership | Expansion Tier 1 | 0.667 | 0.271 | 4.432 | 86.67% | 0.203 | 0.641 | 0.808 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| tvl_percentile | liquidity_inflow | eth_vs_btc_leadership | Expansion Tier 1 | 0.654 | 0.251 | 4.594 | 93.33% | 0.132 | 0.592 | 0.808 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| jump_intensity | volatility_structure | eth_vs_btc_leadership | Expansion Tier 1 | 0.647 | -0.244 | -4.511 | 86.67% | -0.048 | 0.532 | 0.584 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| stablecoin_supply_percentile | liquidity_inflow | eth_vs_btc_leadership | Expansion Tier 1 | 0.622 | 0.202 | 3.915 | 73.33% | 0.194 | 0.628 | 0.786 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| eth_btc_relative_strength_30d | leadership | eth_30d_upside | Expansion Tier 1 | 0.618 | -0.184 | -6.895 | 100.00% | -0.033 | 0.526 | 0.744 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| upside_semivariance | volatility_structure | eth_vs_btc_leadership | Expansion Tier 1 | 0.616 | 0.188 | 3.661 | 73.33% | 0.162 | 0.613 | 0.714 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| distance_from_90d_lows | recovery_capitulation | eth_vs_btc_leadership | Expansion Tier 1 | 0.606 | 0.172 | 4.839 | 93.33% | 0.066 | 0.546 | 0.762 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| top20_30d_high_pct | participation_breadth | eth_vs_btc_leadership | Expansion Tier 1 | 0.599 | 0.172 | 5.624 | 100.00% | 0.147 | 0.587 | 0.732 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| downside_to_upside_volatility_ratio | volatility_structure | eth_vs_btc_leadership | Expansion Tier 1 | 0.594 | -0.153 | -4.528 | 86.67% | -0.148 | 0.603 | 0.748 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| top20_above_30dma_pct | participation_breadth | eth_vs_btc_leadership | Expansion Tier 1 | 0.590 | 0.146 | 5.539 | 93.33% | 0.275 | 0.691 | 0.826 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| dispersion_acceleration | volatility_structure | eth_30d_upside | Expansion Tier 1 | 0.586 | -0.134 | -6.431 | 100.00% | -0.102 | 0.582 | 0.413 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| risk_appetite_recovery_score | macro_recovery | btc_eth_50_50_30d_upside | Expansion Tier 1 | 0.581 | -0.130 | -4.832 | 80.00% | -0.021 | 0.517 | 0.677 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| volume_confirmation_of_price_trend | volume_attention | eth_vs_btc_leadership | Expansion Tier 1 | 0.580 | 0.131 | 4.983 | 93.33% | 0.194 | 0.635 | 0.846 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| volatility_of_volatility | volatility_structure | btc_eth_50_50_30d_upside | Expansion Tier 1 | 0.569 | 0.111 | 1.421 | 80.00% | 0.200 | 0.668 | 0.272 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| tvl_acceleration | liquidity_inflow | eth_vs_btc_leadership | Expansion Tier 1 | 0.559 | 0.096 | 7.541 | 100.00% | 0.080 | 0.556 | 0.799 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| market_dollar_volume_growth_30d | volume_attention | eth_vs_btc_leadership | Expansion Tier 1 | 0.549 | 0.079 | 2.086 | 80.00% | 0.140 | 0.598 | 0.738 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| combined_crypto_liquidity_impulse | liquidity_inflow | eth_30d_upside | Expansion Tier 1 | 0.546 | 0.071 | 3.045 | 86.67% | 0.087 | 0.570 | 0.799 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| stablecoin_supply_acceleration | liquidity_inflow | eth_30d_upside | Expansion Tier 1 | 0.542 | 0.065 | 3.287 | 86.67% | 0.134 | 0.609 | 0.640 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| eth_btc_relative_strength_14d | leadership | btc_eth_50_50_30d_upside | Expansion Tier 1 | 0.539 | -0.063 | -4.018 | 86.67% | -0.047 | 0.540 | 0.618 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| falling_vix_after_high_vix | macro_recovery | btc_eth_50_50_30d_upside | Expansion Tier 1 | 0.521 | -0.046 | -2.163 | 73.33% | -0.225 | 0.651 | 0.517 | development evidence, CPCV stability, non-redundant, holdout sign diagnostic consistent |
| eth_btc_breakout_strength | leadership | eth_30d_upside | Expansion Tier 2 | 0.688 | -0.292 | -6.782 | 100.00% | 0.046 | 0.537 | 0.744 | promising development evidence but weaker stability/significance/holdout diagnostic |
| eth_btc_relative_strength_63d | leadership | eth_30d_upside | Expansion Tier 2 | 0.652 | -0.237 | -6.346 | 93.33% | 0.078 | 0.563 | 0.584 | promising development evidence but weaker stability/significance/holdout diagnostic |
| stablecoin_supply_7d_30d_spread | liquidity_inflow | eth_30d_upside | Expansion Tier 2 | 0.639 | -0.217 | -1.351 | 66.67% | 0.042 | 0.534 | 0.786 | promising development evidence but weaker stability/significance/holdout diagnostic |
| equity_momentum_recovery | macro_recovery | btc_eth_50_50_30d_upside | Expansion Tier 2 | 0.582 | -0.131 | -3.485 | 73.33% | 0.102 | 0.586 | 0.677 | promising development evidence but weaker stability/significance/holdout diagnostic |
| distance_from_180d_lows | recovery_capitulation | eth_vs_btc_leadership | Expansion Tier 2 | 0.581 | 0.131 | 1.216 | 60.00% | -0.086 | 0.560 | 0.762 | promising development evidence but weaker stability/significance/holdout diagnostic |
| volume_acceleration | volume_attention | eth_30d_upside | Expansion Tier 2 | 0.571 | 0.111 | 5.860 | 100.00% | -0.069 | 0.556 | 0.738 | promising development evidence but weaker stability/significance/holdout diagnostic |
| btc_dominance_proxy_change_30d | leadership | btc_eth_50_50_30d_upside | Expansion Tier 2 | 0.568 | 0.109 | 4.638 | 86.67% | -0.059 | 0.549 | 0.445 | promising development evidence but weaker stability/significance/holdout diagnostic |
| tvl_7d_30d_spread | liquidity_inflow | eth_vs_btc_leadership | Expansion Tier 2 | 0.554 | -0.087 | -0.445 | 53.33% | -0.104 | 0.572 | 0.706 | promising development evidence but weaker stability/significance/holdout diagnostic |
| abnormal_volume_zscore | volume_attention | eth_30d_upside | Expansion Tier 2 | 0.553 | 0.082 | 5.991 | 100.00% | -0.013 | 0.510 | 0.578 | promising development evidence but weaker stability/significance/holdout diagnostic |
| realized_volatility_compression | volatility_structure | eth_30d_upside | Expansion Tier 2 | 0.537 | -0.058 | -0.519 | 53.33% | 0.020 | 0.516 | 0.714 | promising development evidence but weaker stability/significance/holdout diagnostic |
| equity_volatility_compression | macro_recovery | eth_vs_btc_leadership | Expansion Tier 2 | 0.531 | -0.051 | -2.151 | 73.33% | 0.069 | 0.548 | 0.493 | promising development evidence but weaker stability/significance/holdout diagnostic |
| volume_breadth | volume_attention | eth_vs_btc_leadership | Expansion Tier 2 | 0.530 | 0.049 | 2.093 | 66.67% | 0.120 | 0.583 | 0.750 | promising development evidence but weaker stability/significance/holdout diagnostic |
| distance_from_30d_lows | recovery_capitulation | eth_vs_btc_leadership | Expansion Tier 3 | 0.633 | 0.215 | 5.134 | 93.33% | 0.283 | 0.697 | 0.918 | unstable, redundant, or weak development evidence |
| assets_rebounding_from_30d_lows_pct | recovery_capitulation | eth_vs_btc_leadership | Expansion Tier 3 | 0.610 | 0.179 | 4.096 | 93.33% | 0.322 | 0.724 | 0.918 | unstable, redundant, or weak development evidence |
| top10_breadth_acceleration | participation_breadth | btc_30d_upside | Expansion Tier 3 | 0.607 | 0.169 | 4.032 | 86.67% | 0.009 | 0.510 | 0.947 | unstable, redundant, or weak development evidence |
| top20_breadth_acceleration | participation_breadth | eth_vs_btc_leadership | Expansion Tier 3 | 0.581 | 0.132 | 17.291 | 100.00% | 0.195 | 0.636 | 0.947 | unstable, redundant, or weak development evidence |
| top20_equal_weight_minus_btc_return_30d | leadership | eth_30d_upside | Expansion Tier 3 | 0.575 | -0.116 | -3.551 | 73.33% | 0.040 | 0.532 | 0.999 | unstable, redundant, or weak development evidence |
| altcoin_leadership_proxy_30d | leadership | eth_30d_upside | Expansion Tier 3 | 0.572 | -0.112 | -3.317 | 73.33% | 0.056 | 0.545 | 0.999 | unstable, redundant, or weak development evidence |
| top20_positive_30d_return_pct | participation_breadth | eth_vs_btc_leadership | Expansion Tier 3 | 0.572 | 0.116 | 4.716 | 86.67% | 0.178 | 0.624 | 0.975 | unstable, redundant, or weak development evidence |
| top20_equal_weight_minus_btc_vol_adj_30d | leadership | eth_30d_upside | Expansion Tier 3 | 0.565 | -0.102 | -3.181 | 80.00% | 0.045 | 0.537 | 0.977 | unstable, redundant, or weak development evidence |
| breadth_recovery_from_depressed | participation_breadth | eth_vs_btc_leadership | Expansion Tier 3 | 0.563 | 0.102 | 4.432 | 86.67% | 0.216 | 0.650 | 0.975 | unstable, redundant, or weak development evidence |
