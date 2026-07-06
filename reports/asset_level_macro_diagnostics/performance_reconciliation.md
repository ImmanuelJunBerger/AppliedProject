# Performance reconciliation

The table below reconciles full-sample, development, and locked-holdout performance for **btc_eth_macro_gate_balanced**.  `gross_0bps` is an explicit no-cost rerun, not an estimate.

| Strategy | Period | Gross Sharpe | Net Sharpe 10 bps | Net Sharpe 25 bps | Net Sharpe 50 bps | Net Sharpe 100 bps | Gross CAGR | Gross Max DD | 25 bps CAGR | 25 bps Max DD | 25 bps turnover | 25 bps exposure | 25 bps changes | Worst DD start | Worst DD trough | Worst DD recovery |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | full_sample | 0.687 | 0.663 | 0.628 | 0.569 | 0.450 | 22.00% | -73.20% | 18.92% | -74.09% | 10.239 | 40.36% | 148 | 2021-11-08 | 2022-11-21 |  |
| btc_eth_macro_gate_balanced | development | 0.676 | 0.653 | 0.618 | 0.560 | 0.445 | 22.56% | -73.20% | 19.19% | -74.09% | 11.185 | 47.09% | 118 | 2021-11-08 | 2022-11-21 |  |
| btc_eth_macro_gate_balanced | holdout | 1.066 | 1.028 | 0.970 | 0.874 | 0.681 | 28.29% | -17.84% | 25.07% | -18.42% | 10.177 | 28.95% | 30 | 2025-01-23 | 2025-04-08 | 2025-05-08 |

## Explicit number sources

- Gross Sharpe around 1.06: **btc_eth_macro_gate_balanced**, locked holdout, 0 bps gross, source `reports/asset_level_macro_diagnostics/performance_reconciliation.csv`.
- Net holdout Sharpe around 0.970: **btc_eth_macro_gate_balanced**, locked holdout, 25 bps net, same source.
- Development Sharpe around 0.6: **btc_eth_macro_gate_balanced**, development period, 25 bps net, same source.
- Development max drawdown around -71%: **btc_eth_macro_gate_balanced**, development period, net/gross diagnostic drawdown from the frozen backtest, same source.
- Holdout max drawdown around -18.42%: **btc_eth_macro_gate_balanced**, locked holdout, 25 bps net, same source.
