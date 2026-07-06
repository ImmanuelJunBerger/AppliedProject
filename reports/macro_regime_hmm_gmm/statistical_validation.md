# Statistical validation

## PBO and deflated Sharpe

- Tested configurations: 19
- Family PBO: 7.14%
- Current-strategy PBO reference: 61.43%
- Development-selected candidate deflated Sharpe probability: 0.15%
- Development-selected candidate bootstrap Sharpe CI: [-2.367, 0.693]

## Candidate statistics

| Candidate | Family PBO | Deflated Sharpe probability | Bootstrap lower | Bootstrap median | Bootstrap upper | Best fold | Median fold | Worst fold | Positive folds |
|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | 7.14% | 27.11% | -0.607 | 1.024 | 2.281 | 1.693 | 0.880 | -1.147 | 73.33% |
| gmm_macro_direct | 7.14% | 0.28% | -2.117 | -0.738 | 0.958 | 2.606 | 1.206 | -0.751 | 86.67% |
| gmm_macro_confirmation_filter | 7.14% | 9.52% | -1.019 | 0.467 | 1.725 | 1.991 | 0.865 | -1.229 | 73.33% |
| gmm_macro_exposure_scaling | 7.14% | 7.89% | -0.892 | 0.377 | 1.473 | 2.082 | 0.752 | -1.329 | 66.67% |
| kmeans_macro_direct | 7.14% | 0.88% | -1.942 | -0.401 | 1.325 | 2.547 | 1.412 | -0.419 | 86.67% |
| kmeans_macro_confirmation_filter | 7.14% | 27.11% | -0.607 | 1.024 | 2.281 | 1.617 | 0.812 | -1.147 | 73.33% |
| kmeans_macro_exposure_scaling | 7.14% | 25.65% | -0.634 | 0.948 | 2.132 | 1.858 | 0.943 | -1.004 | 80.00% |
| markov_fallback_macro_direct | 7.14% | 0.73% | -1.989 | -0.466 | 1.217 | 2.589 | 1.388 | -0.553 | 86.67% |
| markov_fallback_macro_confirmation_filter | 7.14% | 27.11% | -0.607 | 1.024 | 2.281 | 1.617 | 0.812 | -1.147 | 73.33% |
| markov_fallback_macro_exposure_scaling | 7.14% | 21.15% | -0.667 | 0.831 | 2.052 | 1.860 | 0.898 | -1.160 | 73.33% |
| gmm_macro_crypto_direct | 7.14% | 0.15% | -2.367 | -0.888 | 0.693 | 2.652 | 1.705 | -0.266 | 93.33% |
| gmm_macro_crypto_confirmation_filter | 7.14% | 2.75% | -1.192 | 0.035 | 1.036 | 2.284 | 1.396 | -0.054 | 93.33% |
| gmm_macro_crypto_exposure_scaling | 7.14% | 2.95% | -1.150 | 0.061 | 1.099 | 2.300 | 1.442 | 0.006 | 100.00% |
| kmeans_macro_crypto_direct | 7.14% | 1.21% | -1.764 | -0.297 | 1.321 | 2.724 | 1.527 | -0.533 | 86.67% |
| kmeans_macro_crypto_confirmation_filter | 7.14% | 22.94% | -0.649 | 0.926 | 2.184 | 2.357 | 0.880 | -1.147 | 80.00% |
| kmeans_macro_crypto_exposure_scaling | 7.14% | 22.71% | -0.709 | 0.951 | 2.216 | 1.988 | 0.924 | -1.082 | 80.00% |
| markov_fallback_macro_crypto_direct | 7.14% | 1.31% | -1.754 | -0.264 | 1.315 | 2.182 | 1.527 | -0.523 | 86.67% |
| markov_fallback_macro_crypto_confirmation_filter | 7.14% | 27.11% | -0.607 | 1.024 | 2.281 | 1.776 | 0.880 | -1.147 | 73.33% |
| markov_fallback_macro_crypto_exposure_scaling | 7.14% | 24.06% | -0.683 | 0.985 | 2.255 | 1.595 | 0.924 | -1.082 | 80.00% |

## CPCV folds

| Candidate | Fold | Test groups | Fold Sharpe | Test weeks |
|---|---|---|---|---|
| btc_eth_macro_gate_balanced | 0 | 0,1 | 1.693 | 88 |
| btc_eth_macro_gate_balanced | 1 | 0,2 | -0.124 | 88 |
| btc_eth_macro_gate_balanced | 2 | 0,3 | 1.212 | 88 |
| btc_eth_macro_gate_balanced | 3 | 0,4 | 1.010 | 87 |
| btc_eth_macro_gate_balanced | 4 | 0,5 | 0.938 | 87 |
| btc_eth_macro_gate_balanced | 5 | 1,2 | 0.238 | 88 |
| btc_eth_macro_gate_balanced | 6 | 1,3 | 1.617 | 88 |
| btc_eth_macro_gate_balanced | 7 | 1,4 | 1.550 | 87 |
| btc_eth_macro_gate_balanced | 8 | 1,5 | 1.454 | 87 |
| btc_eth_macro_gate_balanced | 9 | 2,3 | -0.324 | 88 |
| btc_eth_macro_gate_balanced | 10 | 2,4 | -1.147 | 87 |
| btc_eth_macro_gate_balanced | 11 | 2,5 | -1.146 | 87 |
| btc_eth_macro_gate_balanced | 12 | 3,4 | 0.880 | 87 |
| btc_eth_macro_gate_balanced | 13 | 3,5 | 0.799 | 87 |
| btc_eth_macro_gate_balanced | 14 | 4,5 | 0.450 | 86 |
| gmm_macro_direct | 0 | 0,1 | 2.474 | 88 |
| gmm_macro_direct | 1 | 0,2 | 0.223 | 88 |
| gmm_macro_direct | 2 | 0,3 | 1.252 | 88 |
| gmm_macro_direct | 3 | 0,4 | 2.404 | 87 |
| gmm_macro_direct | 4 | 0,5 | 1.005 | 87 |
| gmm_macro_direct | 5 | 1,2 | 1.206 | 88 |
| gmm_macro_direct | 6 | 1,3 | 1.878 | 88 |
| gmm_macro_direct | 7 | 1,4 | 2.606 | 87 |
| gmm_macro_direct | 8 | 1,5 | 1.725 | 87 |
| gmm_macro_direct | 9 | 2,3 | -0.451 | 88 |
| gmm_macro_direct | 10 | 2,4 | 0.442 | 87 |
| gmm_macro_direct | 11 | 2,5 | -0.751 | 87 |
| gmm_macro_direct | 12 | 3,4 | 1.433 | 87 |
| gmm_macro_direct | 13 | 3,5 | 0.201 | 87 |
| gmm_macro_direct | 14 | 4,5 | 1.202 | 86 |
| gmm_macro_confirmation_filter | 0 | 0,1 | 1.991 | 88 |
| gmm_macro_confirmation_filter | 1 | 0,2 | -0.271 | 88 |
| gmm_macro_confirmation_filter | 2 | 0,3 | 1.420 | 88 |
| gmm_macro_confirmation_filter | 3 | 0,4 | 1.478 | 87 |
| gmm_macro_confirmation_filter | 4 | 0,5 | 1.216 | 87 |
| gmm_macro_confirmation_filter | 5 | 1,2 | 0.238 | 88 |
| gmm_macro_confirmation_filter | 6 | 1,3 | 1.617 | 88 |
| gmm_macro_confirmation_filter | 7 | 1,4 | 1.536 | 87 |
| gmm_macro_confirmation_filter | 8 | 1,5 | 1.390 | 87 |
| gmm_macro_confirmation_filter | 9 | 2,3 | -0.324 | 88 |
| gmm_macro_confirmation_filter | 10 | 2,4 | -1.163 | 87 |
| gmm_macro_confirmation_filter | 11 | 2,5 | -1.229 | 87 |
| gmm_macro_confirmation_filter | 12 | 3,4 | 0.865 | 87 |
| gmm_macro_confirmation_filter | 13 | 3,5 | 0.729 | 87 |
| gmm_macro_confirmation_filter | 14 | 4,5 | 0.214 | 86 |
| gmm_macro_exposure_scaling | 0 | 0,1 | 2.082 | 88 |
| gmm_macro_exposure_scaling | 1 | 0,2 | -0.350 | 88 |
| gmm_macro_exposure_scaling | 2 | 0,3 | 1.193 | 88 |
| gmm_macro_exposure_scaling | 3 | 0,4 | 1.548 | 87 |
| gmm_macro_exposure_scaling | 4 | 0,5 | 0.831 | 87 |
| gmm_macro_exposure_scaling | 5 | 1,2 | 0.637 | 88 |
| gmm_macro_exposure_scaling | 6 | 1,3 | 1.677 | 88 |
| gmm_macro_exposure_scaling | 7 | 1,4 | 1.729 | 87 |
| gmm_macro_exposure_scaling | 8 | 1,5 | 1.423 | 87 |
| gmm_macro_exposure_scaling | 9 | 2,3 | -0.283 | 88 |
| gmm_macro_exposure_scaling | 10 | 2,4 | -1.051 | 87 |
| gmm_macro_exposure_scaling | 11 | 2,5 | -1.329 | 87 |
| gmm_macro_exposure_scaling | 12 | 3,4 | 0.752 | 87 |
| gmm_macro_exposure_scaling | 13 | 3,5 | 0.440 | 87 |
| gmm_macro_exposure_scaling | 14 | 4,5 | -0.089 | 86 |
