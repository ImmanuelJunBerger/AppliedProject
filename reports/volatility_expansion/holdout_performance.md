# Locked holdout diagnostics

## Predictive metrics

| Model | Feature set | N | Expansion rate | AUC | Precision | Recall | Brier |
|---|---|---|---|---|---|---|---|
| boosted_tree | price_derivatives | 531 | 51.04% | 0.8400 | 0.7372 | 0.8487 | 0.1715 |
| boosted_tree | price_liquidity | 531 | 51.04% | 0.8371 | 0.6879 | 0.8782 | 0.1786 |
| boosted_tree | price_only | 531 | 51.04% | 0.8389 | 0.7273 | 0.8856 | 0.1731 |
| elastic_net | price_derivatives | 531 | 51.04% | 0.8574 | 0.7762 | 0.8192 | 0.1611 |
| elastic_net | price_liquidity | 531 | 51.04% | 0.8579 | 0.7484 | 0.8561 | 0.1624 |
| elastic_net | price_only | 531 | 51.04% | 0.8567 | 0.7786 | 0.8044 | 0.1592 |
| har | price_only | 531 | 51.04% | 0.8220 | 0.7246 | 0.8155 | 0.1779 |

## Calibration curve

The machine-readable curve is in `calibration_curve.csv`; `calibration_curve.svg` plots observed frequency against predicted probability. Perfect calibration lies on the diagonal.

| Model | Feature set | Bin | Predicted | Observed |
|---|---|---|---|---|
| boosted_tree | price_derivatives | 1 | 0.1255 | 0.0909 |
| boosted_tree | price_derivatives | 2 | 0.2514 | 0.2308 |
| boosted_tree | price_derivatives | 3 | 0.3853 | 0.0755 |
| boosted_tree | price_derivatives | 4 | 0.4569 | 0.3019 |
| boosted_tree | price_derivatives | 5 | 0.5311 | 0.5472 |
| boosted_tree | price_derivatives | 6 | 0.6082 | 0.6038 |
| boosted_tree | price_derivatives | 7 | 0.6697 | 0.7358 |
| boosted_tree | price_derivatives | 8 | 0.7301 | 0.7358 |
| boosted_tree | price_derivatives | 9 | 0.7809 | 0.8302 |
| boosted_tree | price_derivatives | 10 | 0.8487 | 0.9623 |
| boosted_tree | price_liquidity | 1 | 0.1469 | 0.0926 |
| boosted_tree | price_liquidity | 2 | 0.2663 | 0.2453 |
| boosted_tree | price_liquidity | 3 | 0.4309 | 0.1321 |
| boosted_tree | price_liquidity | 4 | 0.4991 | 0.2778 |
| boosted_tree | price_liquidity | 5 | 0.5652 | 0.4808 |
| boosted_tree | price_liquidity | 6 | 0.6374 | 0.5926 |
| boosted_tree | price_liquidity | 7 | 0.7162 | 0.6731 |
| boosted_tree | price_liquidity | 8 | 0.7553 | 0.8491 |
| boosted_tree | price_liquidity | 9 | 0.7861 | 0.7963 |
| boosted_tree | price_liquidity | 10 | 0.8298 | 0.9808 |
| boosted_tree | price_only | 1 | 0.1271 | 0.0926 |
| boosted_tree | price_only | 2 | 0.2643 | 0.1698 |
| boosted_tree | price_only | 3 | 0.4049 | 0.1887 |
| boosted_tree | price_only | 4 | 0.4771 | 0.2830 |
| boosted_tree | price_only | 5 | 0.5567 | 0.5094 |
| boosted_tree | price_only | 6 | 0.6391 | 0.6226 |
| boosted_tree | price_only | 7 | 0.7176 | 0.6415 |
| boosted_tree | price_only | 8 | 0.7629 | 0.8302 |
| boosted_tree | price_only | 9 | 0.8045 | 0.7736 |
| boosted_tree | price_only | 10 | 0.8660 | 1.0000 |
| elastic_net | price_derivatives | 1 | 0.1154 | 0.0741 |
| elastic_net | price_derivatives | 2 | 0.2608 | 0.1698 |
| elastic_net | price_derivatives | 3 | 0.3511 | 0.1132 |
| elastic_net | price_derivatives | 4 | 0.4233 | 0.3208 |
| elastic_net | price_derivatives | 5 | 0.4937 | 0.4528 |
| elastic_net | price_derivatives | 6 | 0.5678 | 0.6226 |
| elastic_net | price_derivatives | 7 | 0.6526 | 0.7736 |
| elastic_net | price_derivatives | 8 | 0.7235 | 0.7736 |
| elastic_net | price_derivatives | 9 | 0.7882 | 0.8302 |
| elastic_net | price_derivatives | 10 | 0.9005 | 0.9811 |
| elastic_net | price_liquidity | 1 | 0.1233 | 0.0556 |
| elastic_net | price_liquidity | 2 | 0.2836 | 0.2075 |
| elastic_net | price_liquidity | 3 | 0.3749 | 0.1132 |
| elastic_net | price_liquidity | 4 | 0.4604 | 0.3019 |
| elastic_net | price_liquidity | 5 | 0.5269 | 0.4717 |
| elastic_net | price_liquidity | 6 | 0.5979 | 0.6226 |
| elastic_net | price_liquidity | 7 | 0.6830 | 0.6792 |
| elastic_net | price_liquidity | 8 | 0.7532 | 0.8491 |
| elastic_net | price_liquidity | 9 | 0.8195 | 0.8302 |
| elastic_net | price_liquidity | 10 | 0.9131 | 0.9811 |
| elastic_net | price_only | 1 | 0.1021 | 0.0370 |
| elastic_net | price_only | 2 | 0.2403 | 0.2075 |
| elastic_net | price_only | 3 | 0.3331 | 0.0943 |
| elastic_net | price_only | 4 | 0.4142 | 0.3774 |
| elastic_net | price_only | 5 | 0.4900 | 0.4717 |
| elastic_net | price_only | 6 | 0.5709 | 0.6038 |
| elastic_net | price_only | 7 | 0.6627 | 0.7170 |
| elastic_net | price_only | 8 | 0.7364 | 0.7547 |
| elastic_net | price_only | 9 | 0.8073 | 0.8868 |
| elastic_net | price_only | 10 | 0.9123 | 0.9623 |
| har | price_only | 1 | 0.1408 | 0.0556 |
| har | price_only | 2 | 0.3018 | 0.2075 |
| har | price_only | 3 | 0.4000 | 0.3208 |
| har | price_only | 4 | 0.4530 | 0.2453 |
| har | price_only | 5 | 0.5117 | 0.5660 |
| har | price_only | 6 | 0.5651 | 0.4717 |
| har | price_only | 7 | 0.6365 | 0.6792 |
| har | price_only | 8 | 0.7096 | 0.7358 |
| har | price_only | 9 | 0.7842 | 0.8491 |
| har | price_only | 10 | 0.9032 | 0.9811 |

## Top holdout-fit feature importance

Importance is absolute standardized coefficient magnitude for HAR/Elastic Net and native split importance for the boosted-tree backend. It is descriptive, not causal.

| Model | Feature set | Feature | Normalized importance |
|---|---|---|---|
| boosted_tree | price_derivatives | har_log_rv_7 | 0.1480 |
| boosted_tree | price_derivatives | rv_ratio_7_30 | 0.0884 |
| boosted_tree | price_derivatives | log_upside_semivariance_7 | 0.0607 |
| boosted_tree | price_derivatives | market_drawdown | 0.0527 |
| boosted_tree | price_derivatives | deriv_funding_mean | 0.0521 |
| boosted_tree | price_derivatives | har_log_rv_30 | 0.0520 |
| boosted_tree | price_derivatives | deriv_funding_abs | 0.0502 |
| boosted_tree | price_derivatives | log_downside_semivariance_7 | 0.0440 |
| boosted_tree | price_derivatives | first_eigenvalue_share_30 | 0.0440 |
| boosted_tree | price_derivatives | jump_share_7 | 0.0402 |
| boosted_tree | price_derivatives | market_return_30 | 0.0393 |
| boosted_tree | price_derivatives | average_correlation_30 | 0.0389 |
| boosted_tree | price_derivatives | deriv_funding_rate_coverage | 0.0345 |
| boosted_tree | price_derivatives | deriv_funding_sum_3 | 0.0335 |
| boosted_tree | price_derivatives | deriv_funding_sum_7 | 0.0324 |
| boosted_tree | price_liquidity | har_log_rv_7 | 0.1720 |
| boosted_tree | price_liquidity | rv_ratio_7_30 | 0.1279 |
| boosted_tree | price_liquidity | log_upside_semivariance_7 | 0.0859 |
| boosted_tree | price_liquidity | har_log_rv_30 | 0.0579 |
| boosted_tree | price_liquidity | market_drawdown | 0.0535 |
| boosted_tree | price_liquidity | amihud_illiquidity | 0.0486 |
| boosted_tree | price_liquidity | log_downside_semivariance_7 | 0.0468 |
| boosted_tree | price_liquidity | first_eigenvalue_share_30 | 0.0466 |
| boosted_tree | price_liquidity | average_correlation_30 | 0.0439 |
| boosted_tree | price_liquidity | market_return_30 | 0.0408 |
| boosted_tree | price_liquidity | jump_share_7 | 0.0382 |
| boosted_tree | price_liquidity | market_return_7 | 0.0365 |
| boosted_tree | price_liquidity | log_dollar_volume | 0.0356 |
| boosted_tree | price_liquidity | volume_concentration | 0.0348 |
| boosted_tree | price_liquidity | dollar_volume_change_7 | 0.0314 |
| boosted_tree | price_only | har_log_rv_7 | 0.1848 |
| boosted_tree | price_only | rv_ratio_7_30 | 0.1171 |
| boosted_tree | price_only | log_upside_semivariance_7 | 0.0825 |
| boosted_tree | price_only | jump_share_7 | 0.0703 |
| boosted_tree | price_only | har_log_rv_30 | 0.0665 |
| boosted_tree | price_only | log_downside_semivariance_7 | 0.0642 |
| boosted_tree | price_only | market_drawdown | 0.0600 |
| boosted_tree | price_only | first_eigenvalue_share_30 | 0.0542 |
| boosted_tree | price_only | average_correlation_30 | 0.0528 |
| boosted_tree | price_only | cross_sectional_dispersion_7 | 0.0414 |
| boosted_tree | price_only | market_return_30 | 0.0389 |
| boosted_tree | price_only | har_log_rv_1 | 0.0346 |
| boosted_tree | price_only | breadth_20 | 0.0343 |
| boosted_tree | price_only | market_return_7 | 0.0332 |
| boosted_tree | price_only | cross_sectional_dispersion_1 | 0.0278 |
| elastic_net | price_derivatives | har_log_rv_7 | 0.4481 |
| elastic_net | price_derivatives | market_drawdown | 0.1397 |
| elastic_net | price_derivatives | rv_ratio_7_30 | 0.1337 |
| elastic_net | price_derivatives | log_upside_semivariance_7 | 0.0732 |
| elastic_net | price_derivatives | deriv_funding_abs | 0.0467 |
| elastic_net | price_derivatives | market_return_7 | 0.0271 |
| elastic_net | price_derivatives | cross_sectional_dispersion_1 | 0.0252 |
| elastic_net | price_derivatives | average_correlation_30 | 0.0249 |
| elastic_net | price_derivatives | breadth_20 | 0.0225 |
| elastic_net | price_derivatives | log_downside_semivariance_7 | 0.0153 |
| elastic_net | price_derivatives | market_return_1 | 0.0153 |
| elastic_net | price_derivatives | deriv_funding_rate_coverage | 0.0113 |
| elastic_net | price_derivatives | deriv_funding_mean | 0.0104 |
| elastic_net | price_derivatives | jump_share_7 | 0.0064 |
| elastic_net | price_derivatives | har_log_rv_1 | 0.0000 |
| elastic_net | price_liquidity | har_log_rv_7 | 0.4769 |
| elastic_net | price_liquidity | market_drawdown | 0.1796 |
| elastic_net | price_liquidity | rv_ratio_7_30 | 0.0980 |
| elastic_net | price_liquidity | log_dollar_volume | 0.0944 |
| elastic_net | price_liquidity | log_upside_semivariance_7 | 0.0692 |
| elastic_net | price_liquidity | breadth_20 | 0.0221 |
| elastic_net | price_liquidity | market_return_1 | 0.0149 |
| elastic_net | price_liquidity | market_return_7 | 0.0138 |
| elastic_net | price_liquidity | log_downside_semivariance_7 | 0.0120 |
| elastic_net | price_liquidity | cross_sectional_dispersion_1 | 0.0087 |
| elastic_net | price_liquidity | dollar_volume_change_7 | 0.0051 |
| elastic_net | price_liquidity | jump_share_7 | 0.0034 |
| elastic_net | price_liquidity | amihud_illiquidity | 0.0020 |
| elastic_net | price_liquidity | dollar_volume_change_1 | 0.0000 |
| elastic_net | price_liquidity | har_log_rv_1 | 0.0000 |
| elastic_net | price_only | har_log_rv_7 | 0.2232 |
| elastic_net | price_only | rv_ratio_7_30 | 0.1937 |
| elastic_net | price_only | market_drawdown | 0.1301 |
| elastic_net | price_only | har_log_rv_30 | 0.0781 |
| elastic_net | price_only | log_upside_semivariance_7 | 0.0650 |
| elastic_net | price_only | market_return_7 | 0.0503 |
| elastic_net | price_only | cross_sectional_dispersion_1 | 0.0444 |
| elastic_net | price_only | breadth_20 | 0.0417 |
| elastic_net | price_only | log_downside_semivariance_7 | 0.0377 |
| elastic_net | price_only | market_return_1 | 0.0299 |
| elastic_net | price_only | average_correlation_30 | 0.0295 |
| elastic_net | price_only | har_log_rv_1 | 0.0254 |
| elastic_net | price_only | jump_share_7 | 0.0223 |
| elastic_net | price_only | rv_ratio_1_7 | 0.0198 |
| elastic_net | price_only | cross_sectional_dispersion_7 | 0.0060 |
| har | price_only | har_log_rv_30 | 0.5405 |
| har | price_only | har_log_rv_7 | 0.3434 |
| har | price_only | har_log_rv_1 | 0.1161 |

## Leakage boundary audit

- Maximum allowed training label end: before 2025-01-01
- Actual maximum label end used in each fit is recorded in `selection_history.csv`.
- Alternative data are lagged 1 day(s).
- Hyperparameters are selected by training-window CPCV Brier score.
- No holdout outcome is used for tuning or refitting.
