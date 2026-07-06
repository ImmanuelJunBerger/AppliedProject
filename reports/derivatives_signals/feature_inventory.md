# Derivatives feature inventory

All decision features are shifted one complete UTC day. Rolling z-scores and percentiles use trailing observations only.

| Feature set | Feature | Lag days |
|---|---|---|
| price_only | price_momentum_7 | 1 |
| price_only | price_momentum_30 | 1 |
| price_only | price_momentum_90 | 1 |
| price_only | price_realized_volatility_7 | 1 |
| price_only | price_realized_volatility_30 | 1 |
| price_only | price_drawdown_90 | 1 |
| price_only | price_volume_shock | 1 |
| price_only | price_volatility_shock | 1 |
| derivatives_only | funding_rate | 1 |
| derivatives_only | funding_mean_3 | 1 |
| derivatives_only | funding_mean_7 | 1 |
| derivatives_only | funding_mean_14 | 1 |
| derivatives_only | funding_change_1 | 1 |
| derivatives_only | funding_abs | 1 |
| derivatives_only | funding_zscore_90 | 1 |
| derivatives_only | funding_percentile_252 | 1 |
| derivatives_only | funding_positive_streak | 1 |
| derivatives_only | funding_negative_streak | 1 |
| derivatives_only | basis | 1 |
| derivatives_only | basis_zscore_90 | 1 |
| derivatives_only | basis_change_1 | 1 |
| derivatives_only | basis_compression | 1 |
| derivatives_only | basis_expansion | 1 |
| derivatives_only | crowding_high_funding_negative_momentum | 1 |
| derivatives_only | crowding_extreme_funding | 1 |
| price_derivatives | price_momentum_7 | 1 |
| price_derivatives | price_momentum_30 | 1 |
| price_derivatives | price_momentum_90 | 1 |
| price_derivatives | price_realized_volatility_7 | 1 |
| price_derivatives | price_realized_volatility_30 | 1 |
| price_derivatives | price_drawdown_90 | 1 |
| price_derivatives | price_volume_shock | 1 |
| price_derivatives | price_volatility_shock | 1 |
| price_derivatives | funding_rate | 1 |
| price_derivatives | funding_mean_3 | 1 |
| price_derivatives | funding_mean_7 | 1 |
| price_derivatives | funding_mean_14 | 1 |
| price_derivatives | funding_change_1 | 1 |
| price_derivatives | funding_abs | 1 |
| price_derivatives | funding_zscore_90 | 1 |
| price_derivatives | funding_percentile_252 | 1 |
| price_derivatives | funding_positive_streak | 1 |
| price_derivatives | funding_negative_streak | 1 |
| price_derivatives | basis | 1 |
| price_derivatives | basis_zscore_90 | 1 |
| price_derivatives | basis_change_1 | 1 |
| price_derivatives | basis_compression | 1 |
| price_derivatives | basis_expansion | 1 |
| price_derivatives | crowding_high_funding_negative_momentum | 1 |
| price_derivatives | crowding_extreme_funding | 1 |

## Implemented but excluded for low historical coverage

- `crowding_high_funding_high_oi`
- `crowding_rising_oi_falling_price`
- `long_short_ratio`
- `open_interest_change_1`
- `open_interest_change_7`
- `open_interest_log`
- `open_interest_to_volume`
- `open_interest_zscore_30`
- `price_down_oi_down`
- `price_down_oi_up`
- `price_up_oi_down`
- `price_up_oi_up`
- `taker_imbalance`

Funding features include the daily rate, 3/7/14-day means, one-day change, absolute rate, trailing z-score/percentile and positive/negative streaks. Basis features include level, z-score, change, compression and expansion. OI quadrants, crowding interactions, long/short ratio and taker imbalance activate automatically only when development coverage exceeds 20%.
