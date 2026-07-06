# Robustness and limitations

## Rolling diagnostics

Rolling diagnostics are saved to `rolling_performance.csv`.

| Window | Median Sharpe | Worst Sharpe | Median drawdown | Worst drawdown | Median exposure | Median annual turnover |
|---|---|---|---|---|---|---|
| 3_month | 0.679 | -5.527 | -8.52% | -63.44% | 28.06% | 12.167 |
| 6_month | 0.751 | -3.116 | -14.86% | -67.03% | 28.19% | 11.153 |

## Stress-period diagnostics

| Stress period | Weeks | Selected CAGR | Selected Sharpe | Selected max DD | BTC mean weekly | 50/50 mean weekly |
|---|---|---|---|---|---|---|
| worst_btc_drawdown_weeks | 4 | 0.00% | N/A | 0.00% | -13.86% | -15.97% |
| high_vix_periods | 7 | 56.65% | 1.330 | -3.49% | 0.06% | -1.17% |
| rising_vix_periods | 16 | -28.09% | -2.939 | -9.65% | -3.05% | -4.16% |
| negative_equity_momentum_periods | 24 | 1.75% | 0.181 | -10.45% | -0.99% | -1.73% |
| crypto_bear_weeks | 32 | 5.62% | 0.430 | -8.09% | -1.40% | -1.85% |

## Limitations

- The selected strategy passed mechanical holdout criteria, but prior PBO and
  deflated-Sharpe controls were weak.
- WRDS macro data availability is imperfect; some FRB fields stop before the
  full 2026 holdout.
- The Binance panel is point-in-time within the available dataset, but it may
  omit assets that were not collected historically.
- The strategy was tested retrospectively. It needs prospective paper monitoring
  before any capital decision.
- Gate orientation is empirical from the prior feature-research/selection
  process. In particular, higher VIX level being favourable should be monitored
  carefully because it may be capturing crisis-rebound conditions rather than a
  stable causal relationship.
