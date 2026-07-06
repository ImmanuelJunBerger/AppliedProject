# Study 2: Meta-labeling

## Development-only selection

| Candidate | Family | Selection score | Median fold Sharpe | Worst fold | Positive folds | Dev Sharpe | Dev turnover |
|---|---|---|---|---|---|---|---|
| meta_gradient_boosting_60 | Meta-labeling take/reduce/skip | 0.871 | 0.800 | -1.051 | 66.67% | 0.102 | 6.892 |
| meta_logistic_55 | Meta-labeling take/reduce/skip | 0.678 | 0.720 | -1.368 | 60.00% | 0.396 | 6.892 |
| meta_random_forest_60 | Meta-labeling take/reduce/skip | 0.512 | 0.505 | -1.304 | 66.67% | 0.161 | 7.991 |
| meta_random_forest_55 | Meta-labeling take/reduce/skip | 0.455 | 0.381 | -1.172 | 73.33% | 0.441 | 7.991 |
| meta_logistic_60 | Meta-labeling take/reduce/skip | 0.272 | 0.314 | -1.365 | 60.00% | 0.247 | 6.493 |
| meta_gradient_boosting_55 | Meta-labeling take/reduce/skip | 0.149 | 0.171 | -1.153 | 53.33% | 0.038 | 8.191 |

Selected by development-only CPCV: **meta_gradient_boosting_60**.

## Development vs holdout

| Candidate | Dev Sharpe | Holdout Sharpe | Sharpe retention | Dev CAGR | Holdout CAGR | CAGR retention | Dev max DD | Holdout max DD | Holdout turnover | Holdout exposure |
|---|---|---|---|---|---|---|---|---|---|---|
| meta_logistic_55 | 0.396 | 1.576 | 398.43% | 7.80% | 33.68% | 431.60% | -68.54% | -7.22% | 4.749 | 15.29% |
| meta_logistic_60 | 0.247 | 1.591 | 645.22% | 1.39% | 32.50% | 2336.94% | -69.04% | -7.22% | 3.731 | 13.01% |
| meta_random_forest_55 | 0.441 | 1.365 | 309.60% | 9.44% | 32.39% | 343.10% | -67.40% | -13.64% | 8.480 | 20.17% |
| meta_random_forest_60 | 0.161 | 1.312 | 812.76% | -2.41% | 29.29% | -1217.22% | -70.06% | -10.68% | 5.767 | 17.24% |
| meta_gradient_boosting_55 | 0.038 | 1.574 | 4182.46% | -3.84% | 19.62% | -510.98% | -61.82% | -7.22% | 3.731 | 7.48% |
| meta_gradient_boosting_60 | 0.102 | 1.582 | 1557.16% | -0.67% | 17.31% | -2574.26% | -52.17% | -6.80% | 2.714 | 5.53% |

## Statistical validation

- PBO: 30.00%
- Deflated Sharpe probability for selected candidate: 88.49%
- Worst CPCV fold: -1.051
- Positive CPCV folds: 66.67%

## Frozen benchmark comparison

- Frozen holdout Sharpe: 0.970
- Frozen holdout CAGR: 25.07%
- Frozen holdout max drawdown: -18.42%
- Selected candidate holdout Sharpe: 1.582
- Selected candidate holdout CAGR: 17.31%
- Selected candidate holdout max drawdown: -6.80%

## Interpretation

Status: **survives**.

Candidate improves frozen benchmark under the predeclared criteria; treat as a paper-monitoring enhancement, not a replacement.

Feature drivers: vix_level, vix_change_5d, vix_change_21d, equity_momentum_21d, equity_realized_vol_21d, dow_vol_level, volatility_expansion_probability, cross_sectional_dispersion, stablecoin_supply_change_7d, tvl_growth_30d.

### Economic interpretation and decision mechanics

The primary frozen signal remains unchanged. The meta-model only decides whether to take, reduce, or skip that signal using lagged macro and crypto-native conditions. It increases exposure when the predicted probability that the next frozen signal beats cash clears the development-selected threshold, reduces exposure in the middle band, and holds cash when confidence is low. It does not independently prefer BTC over ETH; it scales the frozen BTC/ETH allocation.

Important caveat: the selected candidate's holdout exposure is below 10%. Its risk-adjusted performance is therefore driven substantially by risk avoidance and cash allocation, not by higher participation in crypto upside.

The selected candidate's holdout CAGR is below the frozen benchmark. Even when Sharpe or drawdown improves, it should be treated as a conservative overlay for paper monitoring rather than a replacement.
