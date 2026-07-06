# Stablecoin and market-liquidity conditioned strategy results

The strategy was **not run**.

Reason: the mandatory feature research phase completed first, and the originally
specified strategy uses features that are currently classified as Tier 3. The
new rule says Tier 3 features must not be used in subsequent strategy design.

## Tier gate decision

Tier 1 features that can motivate a future redesigned public-data strategy:

- `stablecoin_supply_change_7d`
- `tvl_growth_30d`
- `volatility_4h_7d`
- `volatility_expansion_probability`
- `cross_sectional_dispersion`

Features in the requested rule that cannot be used as written:

- `market_drawdown`: Tier 3
- `distance_to_200dma`: Tier 3
- `trend_4h_7d`: Tier 3
- `drawdown_4h_30d`: Tier 3
- `stablecoin_supply_change_30d`: Tier 3

Tier 2 features that may be useful only as context/robustness inputs:

- `stablecoin_supply_change_90d`
- `stablecoin_supply_z_90`
- `distance_to_50dma`
- `momentum_consistency_63d`
- `trend_persistence_63d`
- realized/downside/upside volatility features
- `tvl_momentum_90d`

## Conclusion

Public data integration and feature research are complete. Strategy execution is
blocked until a new candidate is specified using Tier 1 features as its economic
motivation and excluding Tier 3 inputs.

No trading strategy was run and no data was fabricated.
