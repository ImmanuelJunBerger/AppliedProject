# Overfitting diagnostics

- Number of tested prediction configurations: 121
- Number of tested strategy configurations: 22
- Total tested configurations: 143
- PBO: 5.71%
- Deflated Sharpe probability: 0.09%
- Bootstrap Sharpe CI: [-1.917, 0.995]
- Selected holdout exposure: 98.00%
- Frozen holdout exposure: 28.95%

Reject conditions triggered: holdout Sharpe does not materially improve versus frozen strategy; holdout CAGR is not comparable or better; max drawdown worsens materially; does not survive 50 bps costs; deflated Sharpe probability is weak; bootstrap Sharpe CI includes negative outcomes

## CPCV fold distribution

| Candidate | Type | Fold | Fold Sharpe |
|---|---|---|---|
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 0 | 2.342 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 1 | 0.206 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 2 | 1.402 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 3 | 2.098 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 4 | 1.365 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 5 | 0.958 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 6 | 1.955 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 7 | 2.519 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 8 | 1.942 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 9 | -0.257 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 10 | 0.082 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 11 | -0.580 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 12 | 1.542 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 13 | 0.827 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 14 | 1.613 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 0 | 1.682 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 1 | -0.138 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 2 | 1.200 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 3 | 0.995 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 4 | 0.922 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 5 | 0.238 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 6 | 1.617 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 7 | 1.550 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 8 | 1.454 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 9 | -0.324 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 10 | -1.147 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 11 | -1.146 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 12 | 0.880 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 13 | 0.799 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 14 | 0.450 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 0 | 1.614 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 1 | -0.124 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 2 | 1.212 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 3 | 1.010 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 4 | 0.938 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 5 | 0.152 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 6 | 1.534 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 7 | 1.443 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 8 | 1.349 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 9 | -0.324 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 10 | -1.147 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 11 | -1.146 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 12 | 0.880 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 13 | 0.799 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 14 | 0.450 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 0 | 2.287 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 1 | 0.293 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 2 | 1.334 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 3 | 2.098 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 4 | 1.365 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 5 | 0.923 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 6 | 1.828 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 7 | 2.483 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 8 | 1.874 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 9 | -0.278 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 10 | 0.188 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 11 | -0.482 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 12 | 1.473 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 13 | 0.735 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 14 | 1.613 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 0 | 1.830 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 1 | -0.107 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 2 | 1.200 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 3 | 0.939 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 4 | 0.852 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 5 | 0.384 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 6 | 1.775 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 7 | 1.727 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 8 | 1.603 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 9 | -0.291 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 10 | -1.186 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 11 | -1.225 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 12 | 0.817 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 13 | 0.719 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 14 | 0.021 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 0 | 1.425 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 1 | -0.167 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 2 | 1.176 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 3 | 0.957 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 4 | 0.842 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 5 | -0.033 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 6 | 1.381 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 7 | 1.243 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 8 | 1.108 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 9 | -0.319 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 10 | -1.147 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 11 | -1.233 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 12 | 0.887 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 13 | 0.756 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 14 | 0.321 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 0 | 2.684 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 1 | 0.688 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 2 | 1.886 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 3 | 2.396 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 4 | 1.597 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 5 | 1.234 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 6 | 2.322 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 7 | 2.786 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 8 | 2.090 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 9 | 0.291 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 10 | 0.539 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 11 | -0.438 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 12 | 1.941 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 13 | 1.093 |
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 14 | 1.748 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 0 | 1.530 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 1 | 0.153 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 2 | 1.103 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 3 | 1.083 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 4 | 1.072 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 5 | -0.314 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 6 | 1.112 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 7 | 1.630 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 8 | 1.577 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 9 | -0.556 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 10 | -0.995 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 11 | -1.000 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 12 | 0.446 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 13 | 0.432 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 14 | 0.518 |
