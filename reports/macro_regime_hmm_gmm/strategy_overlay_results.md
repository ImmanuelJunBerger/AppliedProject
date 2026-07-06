# Strategy overlay results

The current strategy is not modified. HMM/GMM/KMeans regimes are tested as
separate direct allocation rules, confirmation filters, and exposure scalers.

## Development-only CPCV selection

| Candidate | Family | Overlay | Selection score | Median fold Sharpe | Worst fold | Positive folds | Dev Sharpe | Dev turnover |
|---|---|---|---|---|---|---|---|---|
| gmm_macro_crypto_direct | GMM direct BTC/ETH/cash allocation | direct | 2.105 | 1.705 | -0.266 | 93.33% | 1.639 | 2.697 |
| gmm_macro_crypto_exposure_scaling | Current strategy + GMM exposure scaling | exposure_scaling | 1.943 | 1.442 | 0.006 | 100.00% | 1.366 | 6.293 |
| gmm_macro_crypto_confirmation_filter | Current strategy + GMM confirmation filter | confirmation_filter | 1.850 | 1.396 | -0.054 | 93.33% | 1.242 | 9.589 |
| markov_fallback_macro_crypto_direct | Fallback Markov direct BTC/ETH/cash allocation | direct | 1.829 | 1.527 | -0.523 | 86.67% | 1.198 | 1.398 |
| kmeans_macro_crypto_direct | KMEANS direct BTC/ETH/cash allocation | direct | 1.827 | 1.527 | -0.533 | 86.67% | 1.289 | 1.398 |
| kmeans_macro_direct | KMEANS direct BTC/ETH/cash allocation | direct | 1.741 | 1.412 | -0.419 | 86.67% | 1.331 | 3.996 |
| markov_fallback_macro_direct | Fallback Markov direct BTC/ETH/cash allocation | direct | 1.683 | 1.388 | -0.553 | 86.67% | 1.279 | 3.396 |
| gmm_macro_direct | GMM direct BTC/ETH/cash allocation | direct | 1.452 | 1.206 | -0.751 | 86.67% | 1.233 | 4.795 |
| kmeans_macro_exposure_scaling | Current strategy + KMEANS exposure scaling | exposure_scaling | 1.092 | 0.943 | -1.004 | 80.00% | 0.830 | 11.787 |
| kmeans_macro_crypto_exposure_scaling | Current strategy + KMEANS exposure scaling | exposure_scaling | 1.053 | 0.924 | -1.082 | 80.00% | 0.831 | 6.992 |
| markov_fallback_macro_crypto_exposure_scaling | Current strategy + Fallback Markov exposure scaling | exposure_scaling | 1.053 | 0.924 | -1.082 | 80.00% | 0.703 | 7.292 |
| kmeans_macro_crypto_confirmation_filter | Current strategy + KMEANS confirmation filter | confirmation_filter | 0.993 | 0.880 | -1.147 | 80.00% | 0.811 | 10.888 |
| markov_fallback_macro_exposure_scaling | Current strategy + Fallback Markov exposure scaling | exposure_scaling | 0.975 | 0.898 | -1.160 | 73.33% | 0.693 | 11.388 |
| btc_eth_macro_gate_balanced | Current selected strategy | current | 0.960 | 0.880 | -1.147 | 73.33% | 0.628 | 11.088 |
| markov_fallback_macro_crypto_confirmation_filter | Current strategy + Fallback Markov confirmation filter | confirmation_filter | 0.960 | 0.880 | -1.147 | 73.33% | 0.637 | 11.188 |
| gmm_macro_confirmation_filter | Current strategy + GMM confirmation filter | confirmation_filter | 0.924 | 0.865 | -1.229 | 73.33% | 0.638 | 10.888 |
| kmeans_macro_confirmation_filter | Current strategy + KMEANS confirmation filter | confirmation_filter | 0.892 | 0.812 | -1.147 | 73.33% | 0.590 | 11.288 |
| markov_fallback_macro_confirmation_filter | Current strategy + Fallback Markov confirmation filter | confirmation_filter | 0.892 | 0.812 | -1.147 | 73.33% | 0.590 | 11.288 |
| gmm_macro_exposure_scaling | Current strategy + GMM exposure scaling | exposure_scaling | 0.753 | 0.752 | -1.329 | 66.67% | 0.714 | 9.589 |

Development-selected candidate: **gmm_macro_crypto_direct**.

## Direct regime models and current baseline, holdout at 25 bps

| Candidate | Family | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | Current selected strategy | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |
| markov_fallback_macro_crypto_direct | Fallback Markov direct BTC/ETH/cash allocation | -11.25% | -0.285 | -0.410 | -34.38% | -0.327 | 0.000 | 50.00% |
| kmeans_macro_crypto_direct | KMEANS direct BTC/ETH/cash allocation | -11.81% | -0.309 | -0.442 | -34.38% | -0.344 | 0.678 | 49.35% |
| kmeans_macro_direct | KMEANS direct BTC/ETH/cash allocation | -29.76% | -0.408 | -0.575 | -60.93% | -0.488 | 3.392 | 92.84% |
| markov_fallback_macro_direct | Fallback Markov direct BTC/ETH/cash allocation | -31.79% | -0.468 | -0.656 | -62.58% | -0.508 | 3.392 | 92.19% |
| gmm_macro_direct | GMM direct BTC/ETH/cash allocation | -37.52% | -0.739 | -0.950 | -60.04% | -0.625 | 6.445 | 79.51% |
| gmm_macro_crypto_direct | GMM direct BTC/ETH/cash allocation | -22.74% | -0.890 | -1.145 | -38.69% | -0.588 | 4.071 | 42.19% |

## Confirmation and scaling overlays, holdout at 25 bps

| Candidate | Family | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| markov_fallback_macro_confirmation_filter | Current strategy + Fallback Markov confirmation filter | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |
| kmeans_macro_confirmation_filter | Current strategy + KMEANS confirmation filter | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |
| markov_fallback_macro_crypto_confirmation_filter | Current strategy + Fallback Markov confirmation filter | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |
| kmeans_macro_exposure_scaling | Current strategy + KMEANS exposure scaling | 21.33% | 0.926 | 1.161 | -14.17% | 1.505 | 10.177 | 24.72% |
| markov_fallback_macro_crypto_exposure_scaling | Current strategy + Fallback Markov exposure scaling | 11.80% | 0.902 | 1.132 | -9.70% | 1.216 | 5.428 | 14.31% |
| kmeans_macro_crypto_confirmation_filter | Current strategy + KMEANS confirmation filter | 21.40% | 0.876 | 1.078 | -18.42% | 1.162 | 10.855 | 27.32% |
| kmeans_macro_crypto_exposure_scaling | Current strategy + KMEANS exposure scaling | 11.18% | 0.869 | 1.075 | -9.70% | 1.152 | 5.767 | 13.66% |
| markov_fallback_macro_exposure_scaling | Current strategy + Fallback Markov exposure scaling | 18.02% | 0.821 | 1.011 | -14.17% | 1.272 | 9.498 | 24.07% |
| gmm_macro_confirmation_filter | Current strategy + GMM confirmation filter | 8.41% | 0.457 | 0.505 | -18.42% | 0.457 | 10.177 | 24.07% |
| gmm_macro_exposure_scaling | Current strategy + GMM exposure scaling | 5.37% | 0.375 | 0.383 | -12.72% | 0.422 | 8.480 | 17.57% |
| gmm_macro_crypto_exposure_scaling | Current strategy + GMM exposure scaling | -0.59% | -0.009 | -0.008 | -6.66% | -0.089 | 5.767 | 9.76% |
| gmm_macro_crypto_confirmation_filter | Current strategy + GMM confirmation filter | -2.46% | -0.033 | -0.030 | -13.29% | -0.185 | 10.516 | 19.19% |
