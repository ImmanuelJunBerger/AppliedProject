# Executive summary

Study: **Trend-Scanning Labels and Meta-Models for Macro-Regime Cryptocurrency Allocation**

The frozen strategy **btc_eth_macro_gate_balanced** was not modified, reselected, or retuned.

## Protocol

- Development period: 2019-07-05 to 2024-12-31
- Locked holdout: 2025-01-01 onward
- Label horizons: 7, 14, 21, 30, 45, 60 days
- Trend-label t-stat thresholds tested inside development CPCV: 1.0, 1.5, 2.0
- Total tested configurations: 121

## Development-selected strategy

Selected by development-only CPCV: **trend_scanning_meta_model_biweekly**

| Metric | Frozen macro strategy | Trend-scanning selected |
|---|---:|---:|
| Development Sharpe | 0.618 | 1.293 |
| Holdout Sharpe | 0.970 | 0.102 |
| Holdout CAGR | 25.07% | -4.16% |
| Holdout max DD | -18.42% | -38.07% |
| Holdout turnover | 10.177 | 8.311 |
| Holdout exposure | 28.95% | 63.34% |

Final conclusion: **Trend-scanning does not beat the frozen macro strategy after locked-holdout evaluation.**
