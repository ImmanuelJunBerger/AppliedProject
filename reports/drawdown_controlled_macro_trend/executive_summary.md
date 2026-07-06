# Executive summary

Study: **Drawdown-Controlled Macro Trend Allocation for BTC/ETH/Cash**

Frozen benchmark **btc_eth_macro_gate_balanced** was not modified, reselected, or retuned.

## Development-selected candidate

- Candidate: `frozen_dd_10_reduce_50_r14`
- Family: Family E: Frozen macro allocation plus drawdown-control overlay
- Tested configurations: 360
- Final decision: **keep_frozen_strategy**

## Benchmark versus selected candidate at 25 bps

| Item | Frozen benchmark | Development-selected candidate |
|---|---:|---:|
| Development Sharpe | 0.618 | 0.884 |
| Development max DD | -74.09% | -49.42% |
| Development exposure | 47.09% | 29.30% |
| Holdout Sharpe | 0.970 | 0.926 |
| Holdout max DD | -18.42% | -13.77% |
| Holdout exposure | 28.95% | 15.61% |

Replacement failures: holdout net Sharpe at 25 bps does not improve materially; holdout exposure is not above 35%; deflated Sharpe probability is weak; bootstrap Sharpe delta confidence interval is not supportive
