# WRDS macro feature research

This report evaluates predictive feature quality only. It does not backtest, train a trading model, or select a strategy.

## 1-week IC ranking

| Feature | Method | Full IC | Mean IC | NW t | p-value | IC IR | Rolling stability | Tier |
|---|---|---|---|---|---|---|---|---|
| equity_realized_vol_21d | market_time_series | 0.0891 | 0.1167 | 10.0861 | 0.0000 | 8.6808 | 0.9303 | Tier 1 |
| vix_change_21d | market_time_series | -0.0867 | -0.0660 | -8.7267 | 0.0000 | -7.3037 | 0.9164 | Tier 1 |
| equity_momentum_21d | market_time_series | 0.0954 | 0.0667 | 8.5578 | 0.0000 | 7.2904 | 0.9164 | Tier 1 |
| dow_vol_level | market_time_series | 0.0794 | 0.0714 | 6.3887 | 0.0000 | 5.5244 | 0.8885 | Tier 1 |
| usd_trend_63d | market_time_series | -0.0004 | 0.0610 | 5.1331 | 0.0000 | 4.5045 | 0.1877 | Tier 3 |
| equity_momentum_63d | market_time_series | 0.0332 | -0.0463 | -4.9702 | 0.0000 | -4.2795 | 0.2753 | Tier 2 |
| credit_spread_level | market_time_series | 0.0861 | 0.0715 | 4.8523 | 0.0000 | N/A | 0.7687 | Tier 2 |
| vix_change_5d | market_time_series | -0.0729 | -0.0857 | -4.8474 | 0.0000 | -4.3405 | 0.6551 | Tier 1 |
| vix_level | market_time_series | 0.0582 | 0.0424 | 3.9092 | 0.0001 | 3.3646 | 0.8049 | Tier 1 |
| usd_change_5d | market_time_series | -0.0517 | -0.0583 | -3.8177 | 0.0001 | -3.5050 | 0.5933 | Tier 2 |
| credit_spread_change_21d | market_time_series | -0.0600 | -0.0363 | -3.5722 | 0.0004 | -3.0894 | 0.6642 | Tier 2 |
| real_yield_10y_change_21d | market_time_series | -0.0804 | -0.0512 | -3.0024 | 0.0027 | -2.7603 | 0.7675 | Tier 2 |
| equity_drawdown_252d | market_time_series | 0.0177 | -0.0390 | -2.8628 | 0.0042 | -2.4995 | 0.3798 | Tier 3 |
| yield_curve_slope_change_21d | market_time_series | 0.0273 | -0.0352 | -2.6263 | 0.0086 | -2.3722 | 0.4022 | Tier 2 |
| yield_curve_slope_10y2y | market_time_series | 0.0779 | 0.0284 | 1.8259 | 0.0679 | N/A | 0.6530 | Tier 3 |
| macro_risk_on_composite | market_time_series | 0.0558 | 0.0144 | 1.3440 | 0.1789 | 1.1653 | 0.5749 | Tier 3 |
| rates_10y_change_21d | market_time_series | -0.0296 | -0.0160 | -1.2026 | 0.2291 | -1.0899 | 0.6421 | Tier 3 |
| nasdaq_vol_level | market_time_series | 0.0370 | 0.0127 | 1.0974 | 0.2725 | 0.9475 | 0.5470 | Tier 3 |
| fed_funds_level | market_time_series | -0.0683 | 0.0148 | 1.0068 | 0.3140 | N/A | 0.4027 | Tier 3 |
| usd_trend_21d | market_time_series | -0.0294 | -0.0148 | -0.9097 | 0.3630 | -0.8299 | 0.4391 | Tier 3 |
| rates_10y_level | market_time_series | -0.1116 | -0.0158 | -0.8854 | 0.3760 | N/A | 0.5224 | Tier 3 |
| sofr_level | market_time_series | -0.0812 | -0.0064 | -0.4486 | 0.6537 | N/A | 0.4925 | Tier 3 |
| yield_curve_slope_10y3m | market_time_series | 0.0349 | -0.0093 | -0.4187 | 0.6755 | N/A | 0.4776 | Tier 3 |
| vix_percentile_252d | market_time_series | -0.0353 | -0.0041 | -0.3302 | 0.7413 | -0.2891 | 0.5436 | Tier 3 |
| rates_10y_change_63d | market_time_series | 0.0093 | 0.0038 | 0.2111 | 0.8328 | 0.1907 | 0.6209 | Tier 3 |

## Holdout IC checks

| Feature | Holdout IC | NW t | p-value | Sign consistent | Tier |
|---|---|---|---|---|---|
| equity_momentum_21d | 0.0212 | -0.6858 | 0.4928 | True | Tier 1 |
| equity_momentum_63d | -0.1307 | -9.2030 | 0.0000 | False | Tier 2 |
| equity_drawdown_252d | -0.1081 | -8.0902 | 0.0000 | False | Tier 3 |
| equity_realized_vol_21d | 0.0667 | 9.6709 | 0.0000 | True | Tier 1 |
| vix_level | 0.0836 | 14.1639 | 0.0000 | True | Tier 1 |
| vix_change_5d | -0.1609 | -6.3019 | 0.0000 | True | Tier 1 |
| vix_change_21d | -0.1135 | 1.3378 | 0.1810 | True | Tier 1 |
| vix_percentile_252d | 0.0298 | 2.8923 | 0.0038 | False | Tier 3 |
| nasdaq_vol_level | 0.0710 | 5.0724 | 0.0000 | False | Tier 3 |
| dow_vol_level | 0.1371 | 19.6975 | 0.0000 | True | Tier 1 |
| rates_10y_level | -0.0567 | N/A | N/A | True | Tier 3 |
| rates_10y_change_21d | -0.0639 | 0.5960 | 0.5512 | True | Tier 3 |
| rates_10y_change_63d | -0.0104 | 0.9194 | 0.3579 | True | Tier 3 |
| fed_funds_level | N/A | N/A | N/A | False | Tier 3 |
| sofr_level | -0.1378 | N/A | N/A | True | Tier 3 |
| real_yield_10y_level | -0.2098 | N/A | N/A | True | Tier 3 |
| real_yield_10y_change_21d | 0.1356 | 5.7257 | 0.0000 | False | Tier 2 |
| yield_curve_slope_10y2y | -0.2098 | N/A | N/A | False | Tier 3 |
| yield_curve_slope_change_21d | 0.0153 | 3.6082 | 0.0003 | True | Tier 2 |
| yield_curve_slope_10y3m | 0.1439 | N/A | N/A | True | Tier 3 |
| credit_spread_level | -0.0461 | N/A | N/A | False | Tier 2 |
| credit_spread_change_21d | -0.0077 | 2.2887 | 0.0221 | True | Tier 2 |
| usd_trend_21d | -0.0874 | -2.6456 | 0.0082 | True | Tier 3 |
| usd_trend_63d | -0.0779 | -1.6597 | 0.0970 | False | Tier 3 |
| usd_change_5d | -0.1891 | N/A | N/A | True | Tier 2 |
| macro_risk_on_composite | -0.0262 | -2.2862 | 0.0222 | False | Tier 3 |

## 1-week quintile spread checks

| Feature | Sample | Top-minus-bottom | Positive fraction | Monotonicity | Observations |
|---|---|---|---|---|---|
| credit_spread_change_21d | full_sample | -0.0056 | 0.0000 | -0.8000 | 363 |
| credit_spread_change_21d | development_pre_2025 | -0.0123 | 0.0000 | -0.3000 | 287 |
| credit_spread_change_21d | holdout_2025_2026 | N/A | N/A | N/A | 76 |
| credit_spread_change_21d | 2020_2021_bull | -0.0371 | 0.0000 | -0.4000 | 105 |
| credit_spread_change_21d | 2022_bear | 0.0217 | 1.0000 | 0.3000 | 52 |
| credit_spread_change_21d | 2023_2024_recovery | -0.0150 | 0.0000 | -0.3000 | 104 |
| credit_spread_change_21d | 2025_2026_holdout | N/A | N/A | N/A | 76 |
| credit_spread_level | full_sample | 0.0195 | 1.0000 | 0.5000 | 363 |
| credit_spread_level | development_pre_2025 | 0.0057 | 1.0000 | 0.1000 | 287 |
| credit_spread_level | holdout_2025_2026 | N/A | N/A | N/A | 76 |
| credit_spread_level | 2020_2021_bull | 0.0263 | 1.0000 | 0.1000 | 105 |
| credit_spread_level | 2022_bear | 0.0586 | 1.0000 | 0.9000 | 52 |
| credit_spread_level | 2023_2024_recovery | -0.0176 | 0.0000 | 0.0000 | 104 |
| credit_spread_level | 2025_2026_holdout | N/A | N/A | N/A | 76 |
| dow_vol_level | full_sample | 0.0120 | 1.0000 | 0.7000 | 363 |
| dow_vol_level | development_pre_2025 | 0.0039 | 1.0000 | 0.7000 | 287 |
| dow_vol_level | holdout_2025_2026 | 0.0642 | 1.0000 | 0.7000 | 76 |
| dow_vol_level | 2020_2021_bull | -0.0005 | 0.0000 | -0.4000 | 105 |
| dow_vol_level | 2022_bear | 0.0309 | 1.0000 | 0.0000 | 52 |
| dow_vol_level | 2023_2024_recovery | 0.0216 | 1.0000 | 0.7000 | 104 |
| dow_vol_level | 2025_2026_holdout | 0.0642 | 1.0000 | 0.7000 | 76 |
| equity_drawdown_252d | full_sample | 0.0289 | 1.0000 | 0.2000 | 363 |
| equity_drawdown_252d | development_pre_2025 | 0.0435 | 1.0000 | 0.7000 | 287 |
| equity_drawdown_252d | holdout_2025_2026 | -0.0121 | 0.0000 | -0.3000 | 76 |
| equity_drawdown_252d | 2020_2021_bull | 0.0285 | 1.0000 | 0.8000 | 105 |
| equity_drawdown_252d | 2022_bear | -0.0310 | 0.0000 | -0.7000 | 52 |
| equity_drawdown_252d | 2023_2024_recovery | -0.0092 | 0.0000 | -0.1000 | 104 |
| equity_drawdown_252d | 2025_2026_holdout | -0.0121 | 0.0000 | -0.3000 | 76 |
| equity_momentum_21d | full_sample | 0.0347 | 1.0000 | 1.0000 | 363 |
| equity_momentum_21d | development_pre_2025 | 0.0351 | 1.0000 | 0.9000 | 287 |
| equity_momentum_21d | holdout_2025_2026 | 0.0012 | 1.0000 | 0.1000 | 76 |
| equity_momentum_21d | 2020_2021_bull | 0.0622 | 1.0000 | 0.7000 | 105 |
| equity_momentum_21d | 2022_bear | -0.0212 | 0.0000 | -0.4000 | 52 |
| equity_momentum_21d | 2023_2024_recovery | 0.0327 | 1.0000 | 0.5000 | 104 |
| equity_momentum_21d | 2025_2026_holdout | 0.0012 | 1.0000 | 0.1000 | 76 |
| equity_momentum_63d | full_sample | 0.0278 | 1.0000 | 0.3000 | 363 |
| equity_momentum_63d | development_pre_2025 | 0.0347 | 1.0000 | 0.6000 | 287 |
| equity_momentum_63d | holdout_2025_2026 | -0.0255 | 0.0000 | -0.6000 | 76 |
| equity_momentum_63d | 2020_2021_bull | 0.0195 | 1.0000 | 0.5000 | 105 |
| equity_momentum_63d | 2022_bear | -0.0385 | 0.0000 | -0.5000 | 52 |
| equity_momentum_63d | 2023_2024_recovery | 0.0049 | 1.0000 | 0.3000 | 104 |
| equity_momentum_63d | 2025_2026_holdout | -0.0255 | 0.0000 | -0.6000 | 76 |
| equity_realized_vol_21d | full_sample | 0.0130 | 1.0000 | 0.3000 | 363 |
| equity_realized_vol_21d | development_pre_2025 | 0.0081 | 1.0000 | 0.3000 | 287 |
| equity_realized_vol_21d | holdout_2025_2026 | 0.0332 | 1.0000 | 0.3000 | 76 |

## Redundancy / correlation checks

| Type | Feature | Feature 2 | Correlation | VIF | Interpretation |
|---|---|---|---|---|---|
| high_correlation_pair | vix_level | nasdaq_vol_level | 0.9739 | N/A | potential duplicate information content |
| high_correlation_pair | vix_level | dow_vol_level | 0.9452 | N/A | potential duplicate information content |
| high_correlation_pair | nasdaq_vol_level | dow_vol_level | 0.9196 | N/A | potential duplicate information content |
| high_correlation_pair | rates_10y_level | fed_funds_level | 0.8611 | N/A | potential duplicate information content |
| high_correlation_pair | rates_10y_level | real_yield_10y_level | 0.9200 | N/A | potential duplicate information content |
| high_correlation_pair | fed_funds_level | sofr_level | 0.9744 | N/A | potential duplicate information content |
| high_correlation_pair | fed_funds_level | real_yield_10y_level | 0.8700 | N/A | potential duplicate information content |
| high_correlation_pair | sofr_level | real_yield_10y_level | 0.8704 | N/A | potential duplicate information content |
| high_correlation_pair | sofr_level | yield_curve_slope_10y3m | -0.8529 | N/A | potential duplicate information content |
| vif | equity_momentum_21d |  | N/A | 8.8144 | acceptable |
| vif | equity_momentum_63d |  | N/A | 4.6860 | acceptable |
| vif | equity_drawdown_252d |  | N/A | 15.4213 | high multicollinearity |
| vif | equity_realized_vol_21d |  | N/A | 12.5184 | high multicollinearity |
| vif | vix_level |  | N/A | 96.9335 | high multicollinearity |
| vif | vix_change_5d |  | N/A | 3.3281 | acceptable |
| vif | vix_change_21d |  | N/A | 7.8911 | acceptable |
| vif | vix_percentile_252d |  | N/A | 3.2151 | acceptable |
| vif | nasdaq_vol_level |  | N/A | 29.9497 | high multicollinearity |
| vif | dow_vol_level |  | N/A | 34.2729 | high multicollinearity |
| vif | rates_10y_level |  | N/A | 186.6958 | high multicollinearity |
| vif | rates_10y_change_21d |  | N/A | 6.5381 | acceptable |
| vif | rates_10y_change_63d |  | N/A | 3.5893 | acceptable |
| vif | fed_funds_level |  | N/A | 12553.4795 | high multicollinearity |
| vif | sofr_level |  | N/A | 12139.0389 | high multicollinearity |
| vif | real_yield_10y_level |  | N/A | 98.7634 | high multicollinearity |
| vif | real_yield_10y_change_21d |  | N/A | 6.3303 | acceptable |
| vif | yield_curve_slope_10y2y |  | N/A | 15.4473 | high multicollinearity |
| vif | yield_curve_slope_change_21d |  | N/A | 1.9066 | acceptable |
| vif | yield_curve_slope_10y3m |  | N/A | 122.3363 | high multicollinearity |
| vif | credit_spread_level |  | N/A | 17.7745 | high multicollinearity |
| vif | credit_spread_change_21d |  | N/A | 7.7823 | acceptable |
| vif | usd_trend_21d |  | N/A | 4.3250 | acceptable |
| vif | usd_trend_63d |  | N/A | 4.7890 | acceptable |
| vif | usd_change_5d |  | N/A | 2.0320 | acceptable |
| vif | macro_risk_on_composite |  | N/A | 11.2939 | high multicollinearity |
