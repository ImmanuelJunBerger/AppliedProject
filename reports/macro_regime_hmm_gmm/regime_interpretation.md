# Regime interpretation

## Economic profile by regime

| Model | Feature set | Regime | Frequency | Avg BTC daily | Avg ETH daily | Avg 50/50 daily | Ann vol | Max DD | Avg VIX | Avg equity mom | Avg equity vol | Avg duration |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gmm_macro | macro | risk_on | 64.69% | 0.11% | 0.13% | 0.12% | 62.81% | -63.22% | 16.386 | 0.014 | 0.111 | 17.146 |
| gmm_macro | macro | neutral | 30.99% | 0.22% | 0.30% | 0.26% | 70.81% | -65.30% | 24.771 | 0.001 | 0.200 | 7.691 |
| gmm_macro | macro | risk_off | 4.32% | 0.39% | 0.19% | 0.29% | 117.41% | -51.80% | 40.211 | -0.030 | 0.480 | 5.364 |
| kmeans_macro | macro | risk_on | 80.51% | 0.12% | 0.17% | 0.14% | 63.02% | -70.00% | 17.356 | 0.017 | 0.124 | 34.344 |
| kmeans_macro | macro | neutral | 18.53% | 0.32% | 0.29% | 0.30% | 76.89% | -59.22% | 29.388 | -0.022 | 0.252 | 7.785 |
| kmeans_macro | macro | risk_off | 0.95% | 0.17% | -0.28% | -0.05% | 209.92% | -42.78% | 62.370 | -0.176 | 0.846 | 13.000 |
| markov_fallback_macro | macro | risk_on | 81.87% | 0.13% | 0.16% | 0.15% | 64.17% | -64.43% | 17.462 | 0.017 | 0.124 | 85.962 |
| markov_fallback_macro | macro | neutral | 17.22% | 0.28% | 0.31% | 0.29% | 73.28% | -54.89% | 29.867 | -0.022 | 0.261 | 17.407 |
| markov_fallback_macro | macro | risk_off | 0.92% | 0.32% | -0.08% | 0.12% | 213.56% | -42.78% | 62.985 | -0.179 | 0.865 | 12.500 |
| gmm_macro_crypto | macro_crypto | risk_on | 32.45% | 0.37% | 0.51% | 0.44% | 77.36% | -56.00% | 20.394 | 0.020 | 0.149 | 80.545 |
| gmm_macro_crypto | macro_crypto | neutral | 58.53% | 0.09% | 0.10% | 0.10% | 57.01% | -61.56% | 18.235 | 0.010 | 0.134 | 29.593 |
| gmm_macro_crypto | macro_crypto | risk_off | 9.01% | -0.20% | -0.43% | -0.31% | 96.51% | -78.09% | 30.228 | -0.046 | 0.312 | 5.348 |
| kmeans_macro_crypto | macro_crypto | risk_on | 14.98% | 0.19% | 0.51% | 0.35% | 77.12% | -43.22% | 23.985 | 0.031 | 0.181 | 14.103 |
| kmeans_macro_crypto | macro_crypto | neutral | 83.52% | 0.15% | 0.13% | 0.14% | 63.15% | -76.25% | 18.671 | 0.007 | 0.140 | 71.250 |
| kmeans_macro_crypto | macro_crypto | risk_off | 1.50% | 0.02% | -0.15% | -0.06% | 180.07% | -51.80% | 55.210 | -0.149 | 0.691 | 8.200 |
| markov_fallback_macro_crypto | macro_crypto | risk_on | 13.99% | 0.25% | 0.45% | 0.35% | 78.95% | -38.15% | 24.666 | 0.028 | 0.189 | 38.200 |
| markov_fallback_macro_crypto | macro_crypto | neutral | 84.69% | 0.15% | 0.16% | 0.16% | 63.17% | -76.25% | 18.675 | 0.008 | 0.141 | 177.846 |
| markov_fallback_macro_crypto | macro_crypto | risk_off | 1.32% | -0.38% | -1.04% | -0.71% | 185.49% | -51.80% | 56.746 | -0.158 | 0.694 | 12.000 |

## Transition probabilities

| Model | From | To | Probability | Count |
|---|---|---|---|---|
| gmm_macro | neutral | neutral | 87.00% | 736 |
| gmm_macro | neutral | risk_off | 1.65% | 14 |
| gmm_macro | neutral | risk_on | 11.35% | 96 |
| gmm_macro | risk_off | neutral | 13.56% | 16 |
| gmm_macro | risk_off | risk_off | 81.36% | 96 |
| gmm_macro | risk_off | risk_on | 5.08% | 6 |
| gmm_macro | risk_on | neutral | 5.33% | 94 |
| gmm_macro | risk_on | risk_off | 0.45% | 8 |
| gmm_macro | risk_on | risk_on | 94.22% | 1663 |
| kmeans_macro | neutral | neutral | 87.15% | 441 |
| kmeans_macro | neutral | risk_off | 0.40% | 2 |
| kmeans_macro | neutral | risk_on | 12.45% | 63 |
| kmeans_macro | risk_off | neutral | 7.69% | 2 |
| kmeans_macro | risk_off | risk_off | 92.31% | 24 |
| kmeans_macro | risk_on | neutral | 2.87% | 63 |
| kmeans_macro | risk_on | risk_on | 97.13% | 2134 |
| markov_fallback_macro | neutral | neutral | 94.26% | 443 |
| markov_fallback_macro | neutral | risk_off | 0.43% | 2 |
| markov_fallback_macro | neutral | risk_on | 5.32% | 25 |
| markov_fallback_macro | risk_off | neutral | 8.00% | 2 |
| markov_fallback_macro | risk_off | risk_off | 92.00% | 23 |
| markov_fallback_macro | risk_on | neutral | 1.12% | 25 |
| markov_fallback_macro | risk_on | risk_on | 98.88% | 2209 |
| gmm_macro_crypto | neutral | neutral | 96.68% | 1544 |
| gmm_macro_crypto | neutral | risk_off | 2.76% | 44 |
| gmm_macro_crypto | neutral | risk_on | 0.56% | 9 |
| gmm_macro_crypto | risk_off | neutral | 17.89% | 44 |
| gmm_macro_crypto | risk_off | risk_off | 81.30% | 200 |
| gmm_macro_crypto | risk_off | risk_on | 0.81% | 2 |
| gmm_macro_crypto | risk_on | neutral | 1.02% | 9 |
| gmm_macro_crypto | risk_on | risk_off | 0.23% | 2 |
| gmm_macro_crypto | risk_on | risk_on | 98.76% | 875 |
| kmeans_macro_crypto | neutral | neutral | 98.64% | 2248 |
| kmeans_macro_crypto | neutral | risk_off | 0.18% | 4 |
| kmeans_macro_crypto | neutral | risk_on | 1.18% | 27 |
| kmeans_macro_crypto | risk_off | neutral | 7.32% | 3 |
| kmeans_macro_crypto | risk_off | risk_off | 87.80% | 36 |
| kmeans_macro_crypto | risk_off | risk_on | 4.88% | 2 |
| kmeans_macro_crypto | risk_on | neutral | 6.85% | 28 |
| kmeans_macro_crypto | risk_on | risk_off | 0.24% | 1 |
| kmeans_macro_crypto | risk_on | risk_on | 92.91% | 380 |
| markov_fallback_macro_crypto | neutral | neutral | 99.48% | 2299 |
| markov_fallback_macro_crypto | neutral | risk_off | 0.13% | 3 |
| markov_fallback_macro_crypto | neutral | risk_on | 0.39% | 9 |
| markov_fallback_macro_crypto | risk_off | neutral | 5.56% | 2 |
| markov_fallback_macro_crypto | risk_off | risk_off | 91.67% | 33 |
| markov_fallback_macro_crypto | risk_off | risk_on | 2.78% | 1 |
| markov_fallback_macro_crypto | risk_on | neutral | 2.62% | 10 |
| markov_fallback_macro_crypto | risk_on | risk_on | 97.38% | 372 |
