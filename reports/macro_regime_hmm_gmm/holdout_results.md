# Locked holdout results

Holdout results are reported after development-only model fitting and CPCV
selection. They are not used to choose the final model.

## Holdout ranking at 25 bps

| Candidate | Family | Overlay | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | Current selected strategy | current | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | -5.98% |
| markov_fallback_macro_confirmation_filter | Current strategy + Fallback Markov confirmation filter | confirmation_filter | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | -5.98% |
| kmeans_macro_confirmation_filter | Current strategy + KMEANS confirmation filter | confirmation_filter | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | -5.98% |
| markov_fallback_macro_crypto_confirmation_filter | Current strategy + Fallback Markov confirmation filter | confirmation_filter | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | -5.98% |
| kmeans_macro_exposure_scaling | Current strategy + KMEANS exposure scaling | exposure_scaling | 21.33% | 0.926 | 1.161 | -14.17% | 1.505 | 10.177 | 24.72% | -5.78% |
| markov_fallback_macro_crypto_exposure_scaling | Current strategy + Fallback Markov exposure scaling | exposure_scaling | 11.80% | 0.902 | 1.132 | -9.70% | 1.216 | 5.428 | 14.31% | -2.94% |
| kmeans_macro_crypto_confirmation_filter | Current strategy + KMEANS confirmation filter | confirmation_filter | 21.40% | 0.876 | 1.078 | -18.42% | 1.162 | 10.855 | 27.32% | -5.98% |
| kmeans_macro_crypto_exposure_scaling | Current strategy + KMEANS exposure scaling | exposure_scaling | 11.18% | 0.869 | 1.075 | -9.70% | 1.152 | 5.767 | 13.66% | -2.94% |
| markov_fallback_macro_exposure_scaling | Current strategy + Fallback Markov exposure scaling | exposure_scaling | 18.02% | 0.821 | 1.011 | -14.17% | 1.272 | 9.498 | 24.07% | -5.78% |
| gmm_macro_confirmation_filter | Current strategy + GMM confirmation filter | confirmation_filter | 8.41% | 0.457 | 0.505 | -18.42% | 0.457 | 10.177 | 24.07% | -5.98% |
| gmm_macro_exposure_scaling | Current strategy + GMM exposure scaling | exposure_scaling | 5.37% | 0.375 | 0.383 | -12.72% | 0.422 | 8.480 | 17.57% | -5.78% |
| gmm_macro_crypto_exposure_scaling | Current strategy + GMM exposure scaling | exposure_scaling | -0.59% | -0.009 | -0.008 | -6.66% | -0.089 | 5.767 | 9.76% | -2.94% |
| gmm_macro_crypto_confirmation_filter | Current strategy + GMM confirmation filter | confirmation_filter | -2.46% | -0.033 | -0.030 | -13.29% | -0.185 | 10.516 | 19.19% | -5.98% |
| markov_fallback_macro_crypto_direct | Fallback Markov direct BTC/ETH/cash allocation | direct | -11.25% | -0.285 | -0.410 | -34.38% | -0.327 | 0.000 | 50.00% | -13.21% |
| kmeans_macro_crypto_direct | KMEANS direct BTC/ETH/cash allocation | direct | -11.81% | -0.309 | -0.442 | -34.38% | -0.344 | 0.678 | 49.35% | -13.21% |
| kmeans_macro_direct | KMEANS direct BTC/ETH/cash allocation | direct | -29.76% | -0.408 | -0.575 | -60.93% | -0.488 | 3.392 | 92.84% | -25.10% |
| markov_fallback_macro_direct | Fallback Markov direct BTC/ETH/cash allocation | direct | -31.79% | -0.468 | -0.656 | -62.58% | -0.508 | 3.392 | 92.19% | -25.10% |
| gmm_macro_direct | GMM direct BTC/ETH/cash allocation | direct | -37.52% | -0.739 | -0.950 | -60.04% | -0.625 | 6.445 | 79.51% | -25.10% |
| gmm_macro_crypto_direct | GMM direct BTC/ETH/cash allocation | direct | -22.74% | -0.890 | -1.145 | -38.69% | -0.588 | 4.071 | 42.19% | -13.21% |

## Development-selected candidate cost sensitivity

| Candidate | Cost bps | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| gmm_macro_crypto_direct | 10 | -22.27% | -0.866 | -1.112 | -38.32% | -0.581 | 4.071 | 42.19% |
| gmm_macro_crypto_direct | 25 | -22.74% | -0.890 | -1.145 | -38.69% | -0.588 | 4.071 | 42.19% |
| gmm_macro_crypto_direct | 50 | -23.53% | -0.929 | -1.200 | -39.30% | -0.599 | 4.071 | 42.19% |
| gmm_macro_crypto_direct | 100 | -25.07% | -1.008 | -1.309 | -40.51% | -0.619 | 4.071 | 42.19% |

## Replacement criteria

- Holdout Sharpe must materially improve versus current strategy by at least 0.100.
- Holdout CAGR must remain positive.
- Max drawdown must not worsen.
- 50 bps result must remain positive.
- Annual turnover must remain <= 12x.
- PBO must not increase versus the current reference.
- Economic interpretation must be clearer.

Passes replacement criteria: **No**.
