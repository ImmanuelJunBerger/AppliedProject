# Statistical significance and selection-risk controls

## Block-bootstrap Sharpe intervals

Intervals use 1,000 deterministic 14-day block-bootstrap samples.

| Configuration | Period | 2.5% | Median | 97.5% |
|---|---|---|---|---|
| no_ml_filter | validation | -0.829 | 0.382 | 1.741 |
| no_ml_filter | holdout | -1.792 | -0.142 | 1.672 |
| gradient_boosting__binary_filter | validation | -0.652 | 0.722 | 1.976 |
| gradient_boosting__binary_filter | holdout | -2.161 | -0.790 | 0.635 |

- Number of explicitly evaluated configurations: 109
- Deflated-Sharpe probability, champion holdout: 0.02%
- CSCV-style probability of backtest overfitting on development configurations: 48.57%

These controls are approximate. The robustness grid is exploratory and was not used to replace the validation-selected champion. Multiple testing, venue survivorship bias, and the short holdout materially limit confidence.
