# Feature research summary

This phase runs before any new strategy construction. Features classified as
Tier 3 must not be used in subsequent strategy design.

## Scope

- Observations: 7248
- Features tested: 40
- Horizons: 1-week, 2-week, and 4-week forward returns.
- IC method: cross-sectional Spearman IC for asset-level features; rolling
  time-series Spearman IC for market-level features that are constant across
  assets on a date.
- Significance: Newey-West adjusted t-statistics over IC series.
- Regimes: 2020-2021 bull, 2022 bear, 2023-2024 recovery, 2025-2026 holdout.

## Tier counts

- Tier 1: 5
- Tier 2: 13
- Tier 3: 22

## Feature families by tier

| Family | Tier | Count |
|---|---|---|
| cross_sectional | Tier 3 | 3 |
| external_new_data | Tier 1 | 3 |
| external_new_data | Tier 2 | 3 |
| external_new_data | Tier 3 | 7 |
| liquidity | Tier 2 | 2 |
| liquidity | Tier 3 | 2 |
| market_regime | Tier 1 | 2 |
| market_regime | Tier 3 | 3 |
| momentum | Tier 2 | 1 |
| momentum | Tier 3 | 5 |
| trend | Tier 2 | 2 |
| trend | Tier 3 | 2 |
| volatility | Tier 2 | 5 |

## Feature classification

| Feature | Tier | 1w IC | NW t-stat | Holdout IC | Reason |
|---|---|---|---|---|---|
| tvl_growth_30d | Tier 1 | 0.1207 | 6.6279 | 0.0173 | significant, economically meaningful, stable, and holdout-consistent |
| stablecoin_supply_change_7d | Tier 1 | 0.0823 | 6.0861 | 0.0463 | significant, economically meaningful, stable, and holdout-consistent |
| volatility_4h_7d | Tier 1 | 0.0619 | 3.2248 | 0.0579 | significant, economically meaningful, stable, and holdout-consistent |
| volatility_expansion_probability | Tier 1 | -0.0837 | -7.0640 | -0.1315 | significant, economically meaningful, stable, and holdout-consistent |
| cross_sectional_dispersion | Tier 1 | -0.0523 | -12.6992 | -0.1419 | significant, economically meaningful, stable, and holdout-consistent |
| turnover_30d | Tier 2 | 0.0835 | 6.5171 | 0.1199 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| stablecoin_supply_z_90 | Tier 2 | 0.0726 | 3.9884 | 0.1183 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| jump_intensity_30d | Tier 2 | 0.0275 | 2.2861 | 0.0022 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| distance_to_50dma | Tier 2 | 0.0296 | 2.2012 | 0.0622 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| momentum_consistency_63d | Tier 2 | 0.0297 | 2.0026 | 0.0512 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| trend_persistence_63d | Tier 2 | 0.0297 | 2.0026 | 0.0512 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| volatility_of_volatility_30d | Tier 2 | -0.0835 | -5.8221 | -0.0781 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| stablecoin_supply_change_90d | Tier 2 | 0.0522 | -5.8339 | -0.1445 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| tvl_momentum_90d | Tier 2 | 0.0244 | -6.2262 | -0.1401 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| upside_volatility_30d | Tier 2 | -0.1094 | -6.2623 | -0.1610 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| realized_volatility_30d | Tier 2 | -0.1236 | -6.6737 | -0.1811 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| downside_volatility_30d | Tier 2 | -0.1259 | -6.8638 | -0.1724 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| amihud_illiquidity_30d | Tier 2 | -0.1087 | -7.2810 | -0.1536 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| average_correlation_30d | Tier 3 | -0.0064 | 2.4603 | 0.1900 | unstable, insignificant, redundant, or no holdout support |
| drawdown_4h_30d | Tier 3 | 0.0513 | 1.9452 | 0.0758 | unstable, insignificant, redundant, or no holdout support |
| volume_acceleration | Tier 3 | 0.0268 | 1.8585 | 0.0233 | unstable, insignificant, redundant, or no holdout support |
| volume_concentration_7_30 | Tier 3 | 0.0268 | 1.8585 | 0.0233 | unstable, insignificant, redundant, or no holdout support |
| volume_shock_4h | Tier 3 | 0.0280 | 1.6842 | 0.0042 | unstable, insignificant, redundant, or no holdout support |
| stablecoin_supply_change_30d | Tier 3 | 0.0867 | 1.5368 | -0.0513 | unstable, insignificant, redundant, or no holdout support |
| stablecoin_supply_growth_30d | Tier 3 | 0.0867 | 1.5368 | -0.0513 | unstable, insignificant, redundant, or no holdout support |
| momentum_21d | Tier 3 | 0.0143 | 0.9365 | 0.0000 | unstable, insignificant, redundant, or no holdout support |
| momentum_7d | Tier 3 | 0.0125 | 0.8859 | 0.0434 | unstable, insignificant, redundant, or no holdout support |
| volatility_4h_30d | Tier 3 | 0.0279 | 0.4679 | 0.1028 | unstable, insignificant, redundant, or no holdout support |
| distance_to_200dma | Tier 3 | 0.0071 | 0.4338 | 0.0499 | unstable, insignificant, redundant, or no holdout support |
| volatility_adjusted_momentum_63d | Tier 3 | 0.0048 | 0.3271 | 0.0571 | unstable, insignificant, redundant, or no holdout support |
| momentum_acceleration | Tier 3 | 0.0021 | 0.1337 | -0.0505 | unstable, insignificant, redundant, or no holdout support |
| momentum_63d | Tier 3 | 0.0017 | 0.1066 | 0.0492 | unstable, insignificant, redundant, or no holdout support |
| percentile_momentum_63d | Tier 3 | 0.0017 | 0.1066 | 0.0492 | unstable, insignificant, redundant, or no holdout support |
| relative_strength_rank | Tier 3 | 0.0017 | 0.1066 | 0.0492 | unstable, insignificant, redundant, or no holdout support |
| trend_slope_63d | Tier 3 | 0.0017 | 0.1048 | 0.0492 | unstable, insignificant, redundant, or no holdout support |
| momentum_126d | Tier 3 | -0.0080 | -0.4990 | 0.0168 | unstable, insignificant, redundant, or no holdout support |
| market_breadth | Tier 3 | 0.0242 | -0.5461 | -0.0195 | unstable, insignificant, redundant, or no holdout support |
| trend_4h_14d | Tier 3 | 0.0325 | -1.0765 | 0.0858 | unstable, insignificant, redundant, or no holdout support |
| trend_4h_7d | Tier 3 | -0.0109 | -3.8618 | 0.0286 | unstable, insignificant, redundant, or no holdout support |
| market_drawdown | Tier 3 | 0.0176 | -9.8194 | -0.1664 | unstable, insignificant, redundant, or no holdout support |

## Interpretation rule for later strategies

Any future strategy must explicitly list the Tier 1 features motivating its
rules. Tier 2 features may be used only as robustness/context inputs. Tier 3
features are excluded from strategy design unless a later prospective dataset
changes their classification.
