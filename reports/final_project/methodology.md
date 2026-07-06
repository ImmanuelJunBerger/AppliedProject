# Methodology

## Protocol

- Development period: 2020-01-01 to 2024-12-31.
- Locked holdout: 2025-01-01 to 2026-06-22.
- Candidate selection occurred in the prior macro-regime module using
  development-only CPCV.
- This final report does not introduce new strategy variants.

## Macro gate

The fixed gate uses these development-period thresholds:

| Feature | Orientation | Threshold | Gate profile |
|---|---|---|---|
| equity_realized_vol_21d | high is favourable | 0.141 | balanced |
| equity_momentum_21d | high is favourable | 0.016 | balanced |
| dow_vol_level | high is favourable | 17.840 | balanced |
| vix_level | high is favourable | 19.540 | balanced |
| vix_change_5d | low/rising less is favourable | -0.160 | balanced |
| vix_change_21d | low/rising less is favourable | -0.180 | balanced |

Risk-on/risk-off classification is based on favourable-feature vote counts. The
thresholds are fixed before holdout evaluation.

## Evaluation metrics

The report uses CAGR, Sharpe, Sortino, max drawdown, Calmar, turnover, exposure,
cost sensitivity, CPCV fold distribution, PBO, and deflated Sharpe probability.
