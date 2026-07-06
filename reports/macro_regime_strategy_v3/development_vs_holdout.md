# Development vs holdout consistency

The table below is validation reporting only. It was not used to choose the v3
candidate.

| Candidate | Dev Sharpe | Holdout Sharpe | Sharpe retention | Dev CAGR | Holdout CAGR | CAGR retention | Dev max DD | Holdout max DD | Dev turnover | Holdout turnover | Dev exposure | Holdout exposure | Dev Sharpe >= holdout | Retains >=70% | Both CAGR positive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| simple_vix_level_equity_momentum | 1.267 | -0.305 | -24.06% | 51.98% | -13.45% | -25.88% | -48.45% | -39.92% | 10.189 | 11.533 | 51.20% | 50.65% | Yes | No | No |
| simple_vix_change_equity_momentum | 1.125 | 0.293 | 26.07% | 54.57% | 4.34% | 7.95% | -70.55% | -26.33% | 15.483 | 18.657 | 64.52% | 57.81% | Yes | No | Yes |
| simple_equity_vol_equity_momentum | 1.500 | -0.157 | -10.49% | 72.12% | -8.93% | -12.38% | -49.84% | -40.08% | 10.189 | 9.159 | 52.03% | 47.86% | Yes | No | No |
| simple_vix_level_change_equity_momentum | 1.207 | 0.158 | 13.06% | 49.29% | -0.12% | -0.24% | -51.28% | -26.03% | 15.483 | 18.996 | 50.44% | 52.28% | Yes | No | No |
| btc_eth_macro_gate_balanced | 0.628 | 0.970 | 154.44% | 20.00% | 25.07% | 125.32% | -74.09% | -18.42% | 11.088 | 10.177 | 49.81% | 28.95% | No | Yes | Yes |

Preferred consistency profile:

- development Sharpe above holdout Sharpe;
- holdout retains at least 70% of development Sharpe;
- development and holdout CAGR are both positive;
- drawdown is controlled in both periods.
