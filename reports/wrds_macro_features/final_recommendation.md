# WRDS macro feature final recommendation

Proceed only with macro-regime strategy design using Tier 1 features listed below.

## Tier counts

- Tier 1: 6
- Tier 2: 6
- Tier 3: 14

## Tier classification

| Feature | Tier | 1w IC | NW t | Holdout IC | Reason |
|---|---|---|---|---|---|
| equity_realized_vol_21d | Tier 1 | 0.0891 | 10.0861 | 0.0667 | significant, economically meaningful, stable, and holdout-consistent |
| equity_momentum_21d | Tier 1 | 0.0954 | 8.5578 | 0.0212 | significant, economically meaningful, stable, and holdout-consistent |
| dow_vol_level | Tier 1 | 0.0794 | 6.3887 | 0.1371 | significant, economically meaningful, stable, and holdout-consistent |
| vix_level | Tier 1 | 0.0582 | 3.9092 | 0.0836 | significant, economically meaningful, stable, and holdout-consistent |
| vix_change_5d | Tier 1 | -0.0729 | -4.8474 | -0.1609 | significant, economically meaningful, stable, and holdout-consistent |
| vix_change_21d | Tier 1 | -0.0867 | -8.7267 | -0.1135 | significant, economically meaningful, stable, and holdout-consistent |
| credit_spread_level | Tier 2 | 0.0861 | 4.8523 | -0.0461 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| yield_curve_slope_change_21d | Tier 2 | 0.0273 | -2.6263 | 0.0153 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| real_yield_10y_change_21d | Tier 2 | -0.0804 | -3.0024 | 0.1356 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| credit_spread_change_21d | Tier 2 | -0.0600 | -3.5722 | -0.0077 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| usd_change_5d | Tier 2 | -0.0517 | -3.8177 | -0.1891 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| equity_momentum_63d | Tier 2 | 0.0332 | -4.9702 | -0.1307 | development/full-sample evidence exists but holdout or stability evidence is weaker |
| usd_trend_63d | Tier 3 | -0.0004 | 5.1331 | -0.0779 | unstable, insignificant, redundant, or no holdout support |
| yield_curve_slope_10y2y | Tier 3 | 0.0779 | 1.8259 | -0.2098 | unstable, insignificant, redundant, or no holdout support |
| macro_risk_on_composite | Tier 3 | 0.0558 | 1.3440 | -0.0262 | unstable, insignificant, redundant, or no holdout support |
| nasdaq_vol_level | Tier 3 | 0.0370 | 1.0974 | 0.0710 | unstable, insignificant, redundant, or no holdout support |
| fed_funds_level | Tier 3 | -0.0683 | 1.0068 | N/A | unstable, insignificant, redundant, or no holdout support |
| rates_10y_change_63d | Tier 3 | 0.0093 | 0.2111 | -0.0104 | unstable, insignificant, redundant, or no holdout support |
| real_yield_10y_level | Tier 3 | -0.0866 | 0.0904 | -0.2098 | unstable, insignificant, redundant, or no holdout support |
| vix_percentile_252d | Tier 3 | -0.0353 | -0.3302 | 0.0298 | unstable, insignificant, redundant, or no holdout support |
| yield_curve_slope_10y3m | Tier 3 | 0.0349 | -0.4187 | 0.1439 | unstable, insignificant, redundant, or no holdout support |
| sofr_level | Tier 3 | -0.0812 | -0.4486 | -0.1378 | unstable, insignificant, redundant, or no holdout support |
| rates_10y_level | Tier 3 | -0.1116 | -0.8854 | -0.0567 | unstable, insignificant, redundant, or no holdout support |
| usd_trend_21d | Tier 3 | -0.0294 | -0.9097 | -0.0874 | unstable, insignificant, redundant, or no holdout support |
| rates_10y_change_21d | Tier 3 | -0.0296 | -1.2026 | -0.0639 | unstable, insignificant, redundant, or no holdout support |
| equity_drawdown_252d | Tier 3 | 0.0177 | -2.8628 | -0.1081 | unstable, insignificant, redundant, or no holdout support |

## Next data work before strategy testing

- Confirm a commodity source or Datastream identifiers for gold, oil, and copper if commodity momentum remains required.
- Confirm whether a WRDS-accessible VVIX series exists outside the compact CBOE table.
- Extend FRB/rates/FX data beyond the current WRDS snapshot before treating 2025-2026 holdout conclusions as final.

No trading strategy was run, no trading model was fit, and no holdout threshold was selected.
