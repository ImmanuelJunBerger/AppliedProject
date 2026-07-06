# Train, validation, and holdout results

## Selected strategy versus frozen strategy at 25 bps

| Name | Family | Split | Cost bps | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure | Transaction costs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ml_full_feature_alpha_7d_s+10 | Standalone BTC/ETH/cash ML alpha strategy using full accepted features. | development | 25 | 109.40% | 1.595 | 1.890 | -63.35% | 1.727 | 12.137 | 71.47% | 0.152 |
| ml_full_feature_alpha_7d_s+10 | Standalone BTC/ETH/cash ML alpha strategy using full accepted features. | holdout | 25 | -29.60% | -0.387 | -0.555 | -57.31% | -0.517 | 7.768 | 98.00% | 0.029 |
| btc_eth_macro_gate_balanced | Frozen macro gate | development | 25 | 20.00% | 0.628 | 0.593 | -74.09% | 0.270 | 11.088 | 49.81% | 0.139 |
| btc_eth_macro_gate_balanced | Frozen macro gate | holdout | 25 | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | 0.038 |

## Selected strategy cost sensitivity

| Name | Cost bps | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure | Transaction costs |
|---|---|---|---|---|---|---|---|---|---|
| ml_full_feature_alpha_7d_s+10 | 10 | -28.78% | -0.365 | -0.523 | -56.91% | -0.506 | 7.768 | 98.00% | 0.011 |
| ml_full_feature_alpha_7d_s+10 | 25 | -29.60% | -0.387 | -0.555 | -57.31% | -0.517 | 7.768 | 98.00% | 0.029 |
| ml_full_feature_alpha_7d_s+10 | 50 | -30.95% | -0.423 | -0.607 | -57.98% | -0.534 | 7.768 | 98.00% | 0.057 |
| ml_full_feature_alpha_7d_s+10 | 100 | -33.58% | -0.496 | -0.711 | -59.28% | -0.566 | 7.768 | 98.00% | 0.114 |

## Development CPCV strategy selection

| Candidate | Type | Median fold Sharpe | Worst fold Sharpe | Positive folds | Development Sharpe | Development turnover | Development exposure | Selection score |
|---|---|---|---|---|---|---|---|---|
| ml_full_feature_alpha_7d_s+10 | ml_full_feature_alpha | 1.748 | -0.438 | 93.33% | 1.595 | 12.137 | 71.47% | 1.912 |
| ml_full_feature_alpha_14d_s+10 | ml_full_feature_alpha | 1.622 | -0.390 | 93.33% | 1.542 | 7.312 | 74.06% | 1.804 |
| ml_btc_vs_eth_allocator_14d_m10 | ml_btc_vs_eth_allocator | 1.529 | -0.378 | 86.67% | 1.391 | 9.190 | 100.00% | 1.695 |
| ml_btc_vs_eth_allocator_14d_m5 | ml_btc_vs_eth_allocator | 1.385 | -0.456 | 86.67% | 1.313 | 8.291 | 100.00% | 1.531 |
| ml_full_feature_alpha_7d_s-5 | ml_full_feature_alpha | 1.402 | -0.580 | 86.67% | 1.220 | 7.871 | 98.95% | 1.517 |
| ml_btc_vs_eth_allocator_7d_m10 | ml_btc_vs_eth_allocator | 1.529 | -0.422 | 86.67% | 1.409 | 15.483 | 100.00% | 1.509 |
| ml_full_feature_alpha_7d_s+0 | ml_full_feature_alpha | 1.365 | -0.482 | 86.67% | 1.203 | 9.320 | 95.02% | 1.504 |
| ml_btc_vs_eth_allocator_7d_m5 | ml_btc_vs_eth_allocator | 1.415 | -0.536 | 86.67% | 1.329 | 13.785 | 100.00% | 1.452 |
| ml_full_feature_alpha_14d_s-5 | ml_full_feature_alpha | 1.300 | -0.538 | 86.67% | 1.205 | 5.094 | 98.85% | 1.425 |
| ml_full_feature_alpha_14d_s+0 | ml_full_feature_alpha | 1.249 | -0.538 | 86.67% | 1.239 | 5.654 | 94.25% | 1.374 |
| ml_risk_off_overlay_14d_s+10 | ml_risk_off_overlay | 1.070 | -1.265 | 80.00% | 0.797 | 7.192 | 30.65% | 0.994 |
| ml_risk_off_overlay_7d_s+10 | ml_risk_off_overlay | 1.010 | -1.238 | 80.00% | 0.890 | 10.788 | 30.46% | 0.941 |
| ml_risk_off_overlay_7d_s-5 | ml_risk_off_overlay | 0.880 | -1.147 | 73.33% | 0.596 | 11.188 | 49.52% | 0.813 |
| ml_confirmation_overlay_7d_s-5 | ml_confirmation_overlay | 0.880 | -1.147 | 73.33% | 0.623 | 10.788 | 49.52% | 0.813 |
| ml_risk_off_overlay_7d_s+0 | ml_risk_off_overlay | 0.842 | -1.233 | 66.67% | 0.499 | 11.487 | 47.13% | 0.734 |
| ml_confirmation_overlay_7d_s+0 | ml_confirmation_overlay | 0.817 | -1.225 | 73.33% | 0.645 | 9.040 | 47.08% | 0.731 |
| ml_confirmation_overlay_14d_s-5 | ml_confirmation_overlay | 0.683 | -1.212 | 80.00% | 0.764 | 6.743 | 48.28% | 0.620 |
| ml_risk_off_overlay_14d_s-5 | ml_risk_off_overlay | 0.683 | -1.212 | 80.00% | 0.808 | 6.892 | 48.85% | 0.620 |
| ml_confirmation_overlay_14d_s+10 | ml_confirmation_overlay | 0.655 | -1.019 | 73.33% | 0.678 | 3.946 | 30.46% | 0.620 |
| ml_risk_off_overlay_14d_s+0 | ml_risk_off_overlay | 0.630 | -1.262 | 80.00% | 0.776 | 6.693 | 46.55% | 0.555 |
| ml_confirmation_overlay_14d_s+0 | ml_confirmation_overlay | 0.584 | -1.083 | 80.00% | 0.788 | 5.943 | 45.98% | 0.553 |
| ml_confirmation_overlay_7d_s+10 | ml_confirmation_overlay | 0.518 | -1.000 | 73.33% | 0.404 | 6.093 | 30.60% | 0.488 |
