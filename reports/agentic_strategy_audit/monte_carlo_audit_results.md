# Monte Carlo audit results

Each strategy was evaluated over 100 seeded audit paths.

| Strategy | Accept % | Monitor % | Reject % | Mean reward | Reward std | Dominant reason |
|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | 0.00% | 100.00% | 0.00% | 0.825 | 0.120 | statistical_governance_focus |
| meta_gradient_boosting_60 | 0.00% | 0.00% | 100.00% | 0.738 | 0.074 | low_exposure_cash_driven |
| hybrid__btc_eth_only__confidence_weight__vol_target | 0.00% | 0.00% | 100.00% | 0.659 | 0.105 | high_pbo_rejection |
| inverse_volatility__btc_eth__static | 0.00% | 0.00% | 100.00% | 0.635 | 0.126 | high_pbo_rejection |
| eth_buy_hold | 0.00% | 80.00% | 20.00% | 0.584 | 0.060 | benchmark_context |
| btc_buy_hold | 0.00% | 82.00% | 18.00% | 0.582 | 0.059 | benchmark_context |
| btc_eth_50_50 | 0.00% | 81.00% | 19.00% | 0.573 | 0.064 | benchmark_context |
| pure_top10_momentum | 0.00% | 47.00% | 53.00% | 0.490 | 0.068 | benchmark_context |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | 0.00% | 0.00% | 100.00% | 0.453 | 0.173 | high_pbo_rejection |
| rl_fitted_q_linear_btc_eth_r14_raw_return | 0.00% | 0.00% | 100.00% | 0.450 | 0.109 | weak_dsr_rejection |
| trend_scanning_meta_model_biweekly | 0.00% | 0.00% | 100.00% | 0.446 | 0.110 | weak_dsr_rejection |
| gmm_macro_crypto_direct | 0.00% | 0.00% | 100.00% | 0.416 | 0.113 | weak_dsr_rejection |
| random_forest__forward_rank | 0.00% | 0.00% | 100.00% | 0.367 | 0.106 | weak_dsr_rejection |
| derivatives_risk_gate | 0.00% | 0.00% | 100.00% | 0.331 | 0.143 | high_pbo_rejection |
