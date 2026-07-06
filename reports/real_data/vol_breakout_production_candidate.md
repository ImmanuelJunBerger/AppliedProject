# Volatility-breakout production candidate

## Locked protocol

- Dataset: 2019-01-01 to 2026-06-22
- Universe: point-in-time top 10 by lagged dollar turnover
- Rebalance: weekly
- Portfolio: long-only spot, no leverage, 20% maximum asset weight
- Baseline execution: 25 bps costs, 35% volatility target, drawdown brake, cash when no signal exists
- Training: 2019–2021
- Validation/model selection: 2022–2024
- Untouched holdout: 2025-01-01 to 2026-06-22

The first two years are used as warm-up because the nested model requires 250 matured breakout events. Comparable strategy reporting therefore starts on 2021-01-01; the “train” result covers the remaining part of the locked training segment.

## Baseline results

| Period | CAGR | Sharpe | Max DD | Volatility |
|---|---|---|---|---|
| train_2019_2021 | 75.70% | 1.900 | -18.13% | 32.45% |
| validation_2022_2024 | 2.87% | 0.279 | -19.97% | 13.34% |
| untouched_holdout_2025_2026 | -3.83% | -0.123 | -26.99% | 18.22% |
| full_walk_forward | 11.40% | 0.651 | -27.17% | 19.50% |

## Cost sensitivity

| Cost | CAGR | Sharpe | Max DD |
|---|---|---|---|
| 10 bps | 12.93% | 0.721 | -26.52% |
| 25 bps | 11.40% | 0.651 | -27.17% |
| 50 bps | 8.89% | 0.535 | -28.97% |
| 100 bps | 4.04% | 0.301 | -32.77% |

## Subperiods: baseline versus validation-selected ML filter

| Period | Configuration | CAGR | Sharpe | Max DD |
|---|---|---|---|---|
| 2020-2021 bull market | no_ml_filter | 75.70% | 1.900 | -18.13% |
| 2020-2021 bull market | gradient_boosting__binary_filter | 86.11% | 2.026 | -18.56% |
| 2022 bear market | no_ml_filter | -15.02% | -1.209 | -19.97% |
| 2022 bear market | gradient_boosting__binary_filter | -14.94% | -1.244 | -17.75% |
| 2023 recovery | no_ml_filter | 7.70% | 0.874 | -9.27% |
| 2023 recovery | gradient_boosting__binary_filter | 13.53% | 1.515 | -4.49% |
| 2024-2026 recent period | no_ml_filter | 4.79% | 0.353 | -26.99% |
| 2024-2026 recent period | gradient_boosting__binary_filter | 7.60% | 0.427 | -31.56% |

## Universe and frequency robustness

These cells use the validation-selected ML method, 25 bps, volatility scaling, and the drawdown brake. They are exploratory and did not alter the locked champion.

| Top N | Frequency | Validation Sharpe | Holdout Sharpe | Holdout CAGR | Note |
|---|---|---|---|---|---|
| 5 | W-FRI | -0.013 | -0.637 | -4.52% |  |
| 5 | 2W-FRI | 0 | 0 | 0.00% | insufficient events; cash |
| 10 | W-FRI | 0.647 | -0.805 | -12.23% |  |
| 10 | 2W-FRI | 0.409 | -0.610 | -3.49% |  |
| 20 | W-FRI | -0.250 | -1.228 | -7.37% |  |
| 20 | 2W-FRI | 0.830 | -1.848 | -14.64% |  |

## Risk-control ablation

| Vol scaling | Drawdown brake | Validation Sharpe | Holdout Sharpe |
|---|---|---|---|
| False | False | 0.549 | -0.558 |
| False | True | 0.551 | -0.816 |
| True | False | 0.629 | -0.543 |
| True | True | 0.647 | -0.805 |

Signals use only prior-close data. A breakout is a new 20-day closing high observed within the preceding seven days. The position is held to the next rebalance and otherwise remains in cash.
