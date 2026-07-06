# Process reward results

| Strategy | Process reward | Final score | Decision | Reason |
|---|---|---|---|---|
| btc_eth_macro_gate_balanced | 0.906 | 0.887 | monitor | Frozen selected strategy remains the paper-monitoring benchmark. |
| meta_gradient_boosting_60 | 0.781 | 0.749 | reject | Rejected by mechanical governance: low exposure suggests cash-driven improvement. |
| hybrid__btc_eth_only__confidence_weight__vol_target | 0.766 | 0.749 | reject | Rejected by mechanical governance: PBO exceeds acceptable threshold. |
| inverse_volatility__btc_eth__static | 0.711 | 0.689 | reject | Rejected by mechanical governance: PBO exceeds acceptable threshold. |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | 0.646 | 0.604 | reject | Rejected by mechanical governance: PBO exceeds acceptable threshold. |
| eth_buy_hold | 0.637 | 0.536 | benchmark only | Benchmark is not eligible for replacement. |
| btc_eth_50_50 | 0.636 | 0.535 | benchmark only | Benchmark is not eligible for replacement. |
| btc_buy_hold | 0.636 | 0.535 | benchmark only | Benchmark is not eligible for replacement. |
| trend_scanning_meta_model_biweekly | 0.592 | 0.490 | reject | Rejected by mechanical governance: Deflated Sharpe probability is too weak. |
| gmm_macro_crypto_direct | 0.579 | 0.468 | reject | Rejected by mechanical governance: Deflated Sharpe probability is too weak. |
| rl_fitted_q_linear_btc_eth_r14_raw_return | 0.578 | 0.468 | reject | Rejected by mechanical governance: Deflated Sharpe probability is too weak. |
| pure_top10_momentum | 0.566 | 0.462 | benchmark only | Benchmark is not eligible for replacement. |
| random_forest__forward_rank | 0.515 | 0.417 | reject | Rejected by mechanical governance: Deflated Sharpe probability is too weak. |
| derivatives_risk_gate | 0.510 | 0.410 | reject | Rejected by mechanical governance: PBO exceeds acceptable threshold. |

Interpretation: high process reward requires both investment results and a defensible process.  Low-exposure, high-headline strategies are penalized.
