# Dynamic risk budgeting

Dynamic risk budgets were applied after the frozen signal fired. They increased
or preserved risk only when lagged macro/volatility conditions were favourable
and reduced risk when volatility or drawdown conditions deteriorated.

| Method | Dynamic | Median selection score | Median dev turnover | Median dev exposure |
|---|---|---|---|---|
| hrp | No | 0.441 | 11.388 | 47.09% |
| inverse_volatility | No | 0.441 | 11.388 | 47.09% |
| risk_parity | No | 0.441 | 11.388 | 47.09% |
| erc | No | 0.440 | 11.377 | 47.09% |
| maximum_diversification | No | 0.440 | 11.377 | 47.09% |
| fractional_kelly_0_75 | No | 0.420 | 10.748 | 31.34% |
| fractional_kelly_0_25 | No | 0.418 | 3.719 | 10.46% |
| fractional_kelly_0_50 | No | 0.418 | 7.385 | 20.92% |
| equal_weight | No | 0.418 | 11.185 | 47.09% |
| volatility_targeting | No | 0.417 | 4.911 | 17.03% |
| probability_weighted | No | 0.403 | 11.668 | 47.09% |
| kelly | No | 0.178 | 13.267 | 41.85% |
| mean_variance | No | 0.082 | 14.489 | 46.98% |
| confidence_weighted | No | 0.081 | 14.327 | 47.04% |
| expected_return_weighted | No | 0.075 | 14.229 | 47.04% |
| mean_cvar | No | 0.074 | 14.421 | 47.04% |
| risk_parity | Yes | -0.343 | 5.673 | 15.74% |
| inverse_volatility | Yes | -0.343 | 5.673 | 15.74% |
| hrp | Yes | -0.343 | 5.673 | 15.74% |
| maximum_diversification | Yes | -0.344 | 5.671 | 15.74% |
| erc | Yes | -0.344 | 5.671 | 15.74% |
| equal_weight | Yes | -0.370 | 5.638 | 15.74% |
| probability_weighted | Yes | -0.397 | 5.720 | 15.74% |
| volatility_targeting | Yes | -0.406 | 1.942 | 5.38% |
| fractional_kelly_0_25 | Yes | -0.628 | 1.665 | 3.76% |
| mean_variance | Yes | -0.631 | 6.567 | 15.79% |
| fractional_kelly_0_50 | Yes | -0.633 | 3.330 | 7.51% |
| confidence_weighted | Yes | -0.633 | 5.862 | 15.74% |
| expected_return_weighted | Yes | -0.635 | 5.904 | 15.74% |
| mean_cvar | Yes | -0.635 | 5.903 | 15.74% |
| fractional_kelly_0_75 | Yes | -0.638 | 4.894 | 11.26% |
| kelly | Yes | -0.641 | 6.308 | 15.18% |
