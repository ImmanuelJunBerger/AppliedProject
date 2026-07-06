# Mechanical vs agentic decisions

Mechanical validation uses the predeclared rule: accept replacement only if Sharpe improves, CAGR is comparable or better, drawdown is not materially worse, exposure is at least 15%, turnover is at most 12x, 50 bps costs survive, PBO/DSR are acceptable, improvement is not cash-driven, and holdout was not used for reselection.

| Strategy | Mechanical | Agentic | Comparison | Reason |
|---|---|---|---|---|
| btc_eth_macro_gate_balanced | monitor | monitor | agrees | Frozen selected strategy remains the paper-monitoring benchmark. |
| meta_gradient_boosting_60 | reject | reject | agrees | Rejected by mechanical governance: low exposure suggests cash-driven improvement. |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | reject | reject | agrees | Rejected by mechanical governance: PBO exceeds acceptable threshold. |
| hybrid__btc_eth_only__confidence_weight__vol_target | reject | reject | agrees | Rejected by mechanical governance: PBO exceeds acceptable threshold. |
| inverse_volatility__btc_eth__static | reject | reject | agrees | Rejected by mechanical governance: PBO exceeds acceptable threshold. |
| trend_scanning_meta_model_biweekly | reject | reject | agrees | Rejected by mechanical governance: Deflated Sharpe probability is too weak. |
| random_forest__forward_rank | reject | reject | agrees | Rejected by mechanical governance: Deflated Sharpe probability is too weak. |
| derivatives_risk_gate | reject | reject | agrees | Rejected by mechanical governance: PBO exceeds acceptable threshold. |
| gmm_macro_crypto_direct | reject | reject | agrees | Rejected by mechanical governance: Deflated Sharpe probability is too weak. |
| rl_fitted_q_linear_btc_eth_r14_raw_return | reject | reject | agrees | Rejected by mechanical governance: Deflated Sharpe probability is too weak. |
| btc_buy_hold | benchmark only | benchmark only | agrees | Benchmark is not eligible for replacement. |
| eth_buy_hold | benchmark only | benchmark only | agrees | Benchmark is not eligible for replacement. |
| btc_eth_50_50 | benchmark only | benchmark only | agrees | Benchmark is not eligible for replacement. |
| pure_top10_momentum | benchmark only | benchmark only | agrees | Benchmark is not eligible for replacement. |
