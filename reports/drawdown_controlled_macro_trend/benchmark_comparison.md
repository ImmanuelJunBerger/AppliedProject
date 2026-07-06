# Benchmark comparison

Includes current deterministic reruns and prior-module benchmark context where available.

| Candidate | Family | Source | Split | Cost bps | CAGR | Sharpe | Max DD | Turnover | Exposure | PBO | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| btc_only_macro_gate | requested benchmark | current deterministic diagnostic rerun | development | 25 | 18.30% | 0.613 | -74.88% | 11.185 | 47.09% |  |  |
| btc_only_macro_gate | requested benchmark | current deterministic diagnostic rerun | holdout | 25 | 16.88% | 0.898 | -10.67% | 10.177 | 28.95% |  |  |
| eth_only_macro_gate | requested benchmark | current deterministic diagnostic rerun | development | 25 | 17.25% | 0.578 | -76.43% | 11.185 | 47.09% |  |  |
| eth_only_macro_gate | requested benchmark | current deterministic diagnostic rerun | holdout | 25 | 32.21% | 0.945 | -25.99% | 10.177 | 28.95% |  |  |
| btc_eth_50_50_macro_gate | requested benchmark | current deterministic diagnostic rerun | development | 25 | 19.19% | 0.618 | -74.09% | 11.185 | 47.09% |  |  |
| btc_eth_50_50_macro_gate | requested benchmark | current deterministic diagnostic rerun | holdout | 25 | 25.07% | 0.970 | -18.42% | 10.177 | 28.95% |  |  |
| btc_buy_hold | requested benchmark | current deterministic diagnostic rerun | development | 25 | 47.25% | 0.926 | -76.63% | 0.000 | 100.00% |  |  |
| btc_buy_hold | requested benchmark | current deterministic diagnostic rerun | holdout | 25 | -21.82% | -0.332 | -51.16% | 0.000 | 100.00% |  |  |
| eth_buy_hold | requested benchmark | current deterministic diagnostic rerun | development | 25 | 56.67% | 0.964 | -79.30% | 0.000 | 100.00% |  |  |
| eth_buy_hold | requested benchmark | current deterministic diagnostic rerun | holdout | 25 | -35.10% | -0.239 | -67.52% | 0.000 | 100.00% |  |  |
| btc_eth_50_50_buy_hold | requested benchmark | current deterministic diagnostic rerun | development | 25 | 56.13% | 0.992 | -76.25% | 0.000 | 100.00% |  |  |
| btc_eth_50_50_buy_hold | requested benchmark | current deterministic diagnostic rerun | holdout | 25 | -27.21% | -0.285 | -59.21% | 0.000 | 100.00% |  |  |
| btc_eth_macro_gate_balanced | frozen selected benchmark | current deterministic diagnostic rerun | holdout | 25 | 25.07% | 0.970 | -18.42% | 10.177 | 28.95% |  |  |
| meta_gradient_boosting_60 | prior meta-label overlay | reports/agentic_strategy_audit/results.json | holdout | 25 | 17.31% | 1.582 | -6.80% | 2.714 | 5.53% | 30.00% | 88.49% |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | prior expansion-first best strategy | reports/agentic_strategy_audit/results.json | holdout | 25 | 11.32% | 0.993 | -7.41% | 5.480 | 10.27% | 78.57% | 5.92% |
| hybrid__btc_eth_only__confidence_weight__vol_target | prior hybrid strategy | reports/agentic_strategy_audit/results.json | holdout | 25 | 25.28% | 1.168 | -14.02% | 8.709 | 16.86% | 78.57% | 9.17% |
| trend_scanning_meta_model_biweekly | prior trend-scanning strategy | reports/agentic_strategy_audit/results.json | holdout | 25 | -4.16% | 0.102 | -38.07% | 8.311 | 63.34% | 27.14% | 0.67% |
| vol_compression_breakout_score | agentic strategy discovery candidate | reports/agentic_strategy_discovery/results.json | holdout | 25 | -18.12% | -0.307 | -52.23% |  |  | 70.00% | 3.93% |
