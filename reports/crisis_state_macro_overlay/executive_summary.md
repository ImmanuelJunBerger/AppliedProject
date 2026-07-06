# Executive summary

Study: **Crisis-State Detection for Macro-Regime Cryptocurrency Allocation**

Frozen benchmark **btc_eth_macro_gate_balanced** was not modified, reselected, or retuned.

Selected crisis overlay: `target_d_future_drawdown_gt_25__elastic_net_logistic|cash_if_high_and_macro_stress|0.40`

- Model config: `target_d_future_drawdown_gt_25__elastic_net_logistic`
- Overlay action: cash_if_high_and_macro_stress
- Threshold: 40.00%
- Final decision: **keep_frozen_strategy**

## Benchmark versus selected crisis overlay at 25 bps

| Item | Frozen benchmark | Crisis overlay |
|---|---:|---:|
| Development Sharpe | 0.618 | 1.178 |
| Development max DD | -74.09% | -49.23% |
| Development exposure | 47.09% | 25.55% |
| Holdout Sharpe | 0.970 | 0.640 |
| Holdout max DD | -18.42% | -8.64% |
| Holdout exposure | 28.95% | 13.66% |

Replacement failures: holdout Sharpe is not comparable; holdout exposure below 25%; PBO above 50%; weak DSR
