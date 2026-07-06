# Development vs holdout analysis

The selected strategy is fixed as **btc_eth_macro_gate_balanced**. This analysis does
not retune thresholds or select a new strategy.

## Development and holdout metrics

| Split | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| development | 20.00% | 0.628 | 0.593 | -74.09% | 0.270 | 11.088 | 49.81% |
| holdout | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |

## Retention and change

| Diagnostic | Value | Classification |
|---|---:|---|
| Sharpe retention | 154.44% | Excellent |
| CAGR retention | 125.32% | Excellent |
| Drawdown change | 55.67% | less negative is better |
| Turnover change | -0.911x | lower is better |
| Exposure change | -20.86% | lower exposure may indicate defensive behavior |

Retention labels: Excellent >80%, Good 60-80%, Moderate 40-60%, Weak <40%.

## CPCV fold distribution

| Fold statistic | Value |
|---|---:|
| Best fold Sharpe | 1.693 |
| Median fold Sharpe | 0.880 |
| Worst fold Sharpe | -1.147 |
| Positive CPCV folds | 73.33% |
| Holdout weekly Sharpe | 1.129 |
| Holdout percentile vs CPCV folds | 66.67% |

Full fold-level diagnostics are saved to `development_cpcv_folds.csv`.

## Interpretation

- Performance degradation assessment: No material degradation: holdout Sharpe and CAGR exceeded development-period values.
- Retention/degradation consistent with a robust strategy: Yes.
- Substantial overfitting suggested: No.
- Holdout Sharpe plausibly explained by development performance: Yes.

Final conclusion: **appears to generalize reasonably from development to holdout**.
