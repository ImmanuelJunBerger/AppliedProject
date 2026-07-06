# Macro-regime strategy v3 simplification results

## Scope

This module does not search for a new unrelated strategy. It tests only four
small, interpretable macro-gate variants plus the existing
`btc_eth_macro_gate_balanced` strategy.

Holdout was not used for candidate selection. Selection uses development-only
CPCV and an explicit complexity/stability penalty.

## Candidate specifications

| Candidate | Label | Features | Feature count | Risk-on votes | Neutral votes | Economic interpretation |
|---|---|---|---|---|---|---|
| simple_vix_level_equity_momentum | A. VIX level + equity momentum | vix_level:low, equity_momentum_21d:high | 2 | 2 | 1 | Risk-on only when equity trend is positive and VIX is not elevated. |
| simple_vix_change_equity_momentum | B. VIX change + equity momentum | vix_change_5d:low, vix_change_21d:low, equity_momentum_21d:high | 3 | 2 | 1 | Risk-on when volatility stress is not accelerating and equity trend is positive. |
| simple_equity_vol_equity_momentum | C. Equity realized volatility + equity momentum | equity_realized_vol_21d:low, equity_momentum_21d:high | 2 | 2 | 1 | Risk-on only when equity trend is positive and realized equity volatility is contained. |
| simple_vix_level_change_equity_momentum | D. VIX level + VIX change + equity momentum | vix_level:low, vix_change_5d:low, vix_change_21d:low, equity_momentum_21d:high | 4 | 3 | 2 | Risk-on when equity trend is positive and both VIX level/change confirm a benign macro regime. |
| btc_eth_macro_gate_balanced | E. Full current strategy | equity_realized_vol_21d:high, equity_momentum_21d:high, dow_vol_level:high, vix_level:high, vix_change_5d:low, vix_change_21d:low | 6 | 4 | 3 | Existing balanced six-feature empirical macro gate. |

## Development-only selection score

| Candidate | Features | Selection score | Median CPCV Sharpe | Worst fold | Positive folds | Dev turnover | Exposure stability penalty | CPCV train/test decay proxy |
|---|---|---|---|---|---|---|---|---|
| simple_equity_vol_equity_momentum | 2 | 1.378 | 1.588 | -0.869 | 86.67% | 10.189 | 0.385 | -0.211 |
| simple_vix_level_equity_momentum | 2 | 1.316 | 1.417 | -0.531 | 86.67% | 10.189 | 0.381 | -0.263 |
| simple_vix_change_equity_momentum | 3 | 0.893 | 1.408 | -0.679 | 86.67% | 15.483 | 0.374 | -0.356 |
| simple_vix_level_change_equity_momentum | 4 | 0.694 | 1.284 | -0.544 | 86.67% | 15.483 | 0.410 | 0.061 |
| btc_eth_macro_gate_balanced | 6 | 0.037 | 0.880 | -1.147 | 73.33% | 11.088 | 0.426 | -0.347 |

## Selected by development-only CPCV

Selected candidate: **simple_equity_vol_equity_momentum**

Selection inputs: Development-only CPCV median Sharpe, worst-fold Sharpe, positive-fold fraction, fold instability, CPCV train/test decay proxy, feature count, turnover, and exposure stability.

Actual holdout decay is reported separately and was not used in the selection score.
