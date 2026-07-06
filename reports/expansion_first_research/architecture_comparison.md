# Architecture comparison

Architecture A is the frozen macro-first benchmark. Architecture B is
expansion-first. Architecture C is hybrid expansion alpha plus macro regime
state before the post-alpha risk layer.

| Selection | Candidate | CAGR | Sharpe | Sortino | Max DD | Turnover | Exposure | CAGR 50 bps | PBO | DSR | Cash false improvement? | Replacement? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| expansion_first | expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | 11.32% | 0.993 | 1.016 | -7.41% | 5.480 | 10.27% | 9.80% | 78.57% | 5.92% | Yes | No |
| hybrid | hybrid__btc_eth_only__confidence_weight__vol_target | 25.28% | 1.168 | 1.059 | -14.02% | 8.709 | 16.86% | 22.57% | 78.57% | 9.17% | Yes | No |
| overall | expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | 11.32% | 0.993 | 1.016 | -7.41% | 5.480 | 10.27% | 9.80% | 78.57% | 5.92% | Yes | No |
