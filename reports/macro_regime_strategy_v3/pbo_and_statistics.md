# PBO and statistical controls

## Family-level controls

- Tested configurations: 5.
- Restricted-family PBO: 37.14%.
- Prior current-strategy PBO reference from the broader macro-regime search: 61.43%.
- Selected deflated Sharpe probability: 8.33%
- Selected bootstrap Sharpe CI: [-1.970, 1.482]

The PBO reported here is a family-level statistic for this restricted five-gate
experiment. It is not candidate-specific. The lower PBO mainly reflects the
smaller, predeclared candidate set; it does not rescue a simplified candidate
that fails the locked holdout.

## Candidate statistics

| Candidate | Family PBO | Deflated Sharpe probability | Bootstrap lower | Bootstrap median | Bootstrap upper | Best fold | Median fold | Worst fold | Positive folds |
|---|---|---|---|---|---|---|---|---|---|
| simple_vix_level_equity_momentum | 37.14% | 5.91% | -2.059 | -0.470 | 1.294 | 2.590 | 1.417 | -0.531 | 86.67% |
| simple_vix_change_equity_momentum | 37.14% | 20.22% | -1.769 | 0.132 | 1.778 | 2.554 | 1.408 | -0.679 | 86.67% |
| simple_equity_vol_equity_momentum | 37.14% | 8.33% | -1.970 | -0.262 | 1.482 | 2.600 | 1.588 | -0.869 | 86.67% |
| simple_vix_level_change_equity_momentum | 37.14% | 15.85% | -1.859 | 0.003 | 1.639 | 2.863 | 1.284 | -0.544 | 86.67% |
| btc_eth_macro_gate_balanced | 37.14% | 53.03% | -0.413 | 0.899 | 2.275 | 1.693 | 0.880 | -1.147 | 73.33% |

## CPCV fold distribution

| Candidate | Fold | Test groups | Train Sharpe | Fold Sharpe | Train/test decay |
|---|---|---|---|---|---|
| simple_vix_level_equity_momentum | 0 | 0,1 | 0.604 | 2.590 | -1.986 |
| simple_vix_level_equity_momentum | 1 | 0,2 | 1.542 | 0.577 | 0.966 |
| simple_vix_level_equity_momentum | 2 | 0,3 | 1.100 | 1.763 | -0.663 |
| simple_vix_level_equity_momentum | 3 | 0,4 | 0.719 | 2.528 | -1.809 |
| simple_vix_level_equity_momentum | 4 | 0,5 | 1.118 | 1.417 | -0.299 |
| simple_vix_level_equity_momentum | 5 | 1,2 | 1.515 | 0.919 | 0.596 |
| simple_vix_level_equity_momentum | 6 | 1,3 | 1.112 | 1.797 | -0.685 |
| simple_vix_level_equity_momentum | 7 | 1,4 | 0.670 | 2.456 | -1.786 |
| simple_vix_level_equity_momentum | 8 | 1,5 | 1.154 | 1.580 | -0.426 |
| simple_vix_level_equity_momentum | 9 | 2,3 | 1.953 | -0.531 | 2.484 |
| simple_vix_level_equity_momentum | 10 | 2,4 | 1.616 | 0.501 | 1.114 |
| simple_vix_level_equity_momentum | 11 | 2,5 | 2.047 | -0.525 | 2.572 |
| simple_vix_level_equity_momentum | 12 | 3,4 | 1.148 | 1.577 | -0.429 |
| simple_vix_level_equity_momentum | 13 | 3,5 | 1.551 | 0.426 | 1.125 |
| simple_vix_level_equity_momentum | 14 | 4,5 | 1.238 | 1.297 | -0.059 |
| simple_vix_change_equity_momentum | 0 | 0,1 | 0.305 | 2.554 | -2.250 |
| simple_vix_change_equity_momentum | 1 | 0,2 | 1.520 | 0.488 | 1.032 |
| simple_vix_change_equity_momentum | 2 | 0,3 | 1.014 | 1.408 | -0.394 |
| simple_vix_change_equity_momentum | 3 | 0,4 | 0.616 | 2.434 | -1.818 |
| simple_vix_change_equity_momentum | 4 | 0,5 | 0.847 | 1.665 | -0.818 |
| simple_vix_change_equity_momentum | 5 | 1,2 | 1.442 | 0.742 | 0.700 |
| simple_vix_change_equity_momentum | 6 | 1,3 | 0.957 | 1.564 | -0.606 |
| simple_vix_change_equity_momentum | 7 | 1,4 | 0.526 | 2.450 | -1.923 |
| simple_vix_change_equity_momentum | 8 | 1,5 | 0.777 | 1.789 | -1.012 |
| simple_vix_change_equity_momentum | 9 | 2,3 | 2.087 | -0.679 | 2.766 |
| simple_vix_change_equity_momentum | 10 | 2,4 | 1.635 | 0.062 | 1.573 |
| simple_vix_change_equity_momentum | 11 | 2,5 | 1.898 | -0.579 | 2.477 |
| simple_vix_change_equity_momentum | 12 | 3,4 | 1.155 | 1.154 | 0.001 |
| simple_vix_change_equity_momentum | 13 | 3,5 | 1.402 | 0.437 | 0.966 |
| simple_vix_change_equity_momentum | 14 | 4,5 | 1.052 | 1.468 | -0.417 |
| simple_equity_vol_equity_momentum | 0 | 0,1 | 0.632 | 2.589 | -1.957 |
| simple_equity_vol_equity_momentum | 1 | 0,2 | 1.650 | 0.737 | 0.913 |
| simple_equity_vol_equity_momentum | 2 | 0,3 | 1.377 | 1.591 | -0.214 |
| simple_equity_vol_equity_momentum | 3 | 0,4 | 0.989 | 2.600 | -1.611 |
| simple_equity_vol_equity_momentum | 4 | 0,5 | 1.201 | 1.780 | -0.579 |
| simple_equity_vol_equity_momentum | 5 | 1,2 | 1.607 | 1.282 | 0.325 |
| simple_equity_vol_equity_momentum | 6 | 1,3 | 1.330 | 1.764 | -0.434 |
| simple_equity_vol_equity_momentum | 7 | 1,4 | 0.806 | 2.472 | -1.666 |
| simple_equity_vol_equity_momentum | 8 | 1,5 | 1.115 | 1.944 | -0.828 |
| simple_equity_vol_equity_momentum | 9 | 2,3 | 2.124 | -0.869 | 2.993 |
