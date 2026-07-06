# Strategy input table

No missing metrics are fabricated.  Null fields remain missing in `results.json` and CSV outputs.

| Strategy | Family | Sharpe | CAGR | Max DD | Turnover | Exposure | 50 bps survives | PBO | DSR | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | BTC/ETH/cash macro risk gate | 0.970 | 25.07% | -18.42% | 10.177 | 28.95% | Yes | 61.43% | 42.45% | final Applied Project strategy / paper-monitoring candidate |
| meta_gradient_boosting_60 | Conservative ML meta-label overlay | 1.582 | 17.31% | -6.80% | 2.714 | 5.53% | N/A | 30.00% | 88.49% | prior overlay benchmark only |
| expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | Expansion-first best strategy | 0.993 | 11.32% | -7.41% | 5.480 | 10.27% | Yes | 78.57% | 5.92% | rejected as replacement; diagnostic benchmark |
| hybrid__btc_eth_only__confidence_weight__vol_target | Hybrid best strategy | 1.168 | 25.28% | -14.02% | 8.709 | 16.86% | Yes | 78.57% | 9.17% | rejected as replacement; diagnostic benchmark |
| inverse_volatility__btc_eth__static | Portfolio optimisation candidate | 0.936 | 22.36% | -16.94% | 10.240 | 28.95% | Yes | 91.43% | 12.39% | rejected as replacement |
| trend_scanning_meta_model_biweekly | Trend-scanning selected candidate | 0.102 | -4.16% | -38.07% | 8.311 | 63.34% | No | 27.14% | 0.67% | rejected as replacement |
| random_forest__forward_rank | Cross-sectional ML candidate | -0.168 | -21.13% | -54.46% | N/A | 100.00% | No | 28.57% | 0.24% | rejected as replacement |
| derivatives_risk_gate | Derivatives/funding candidate | -0.233 | -9.56% | -32.29% | 15.604 | 32.90% | No | 95.71% | 0.22% | rejected as replacement |
| gmm_macro_crypto_direct | HMM/GMM macro-regime candidate | -0.890 | -22.74% | -38.69% | 4.071 | 42.19% | No | 7.14% | 0.15% | rejected as replacement; explanatory only |
| rl_fitted_q_linear_btc_eth_r14_raw_return | Risk-aware reinforcement learning candidate | -0.239 | -35.10% | -67.52% | 0.000 | 100.00% | No | 0.00% | 0.66% | rejected as replacement |
| btc_buy_hold | BTC buy-and-hold | -0.332 | -21.82% | -51.16% | 0.000 | 100.00% | No | N/A | N/A | benchmark only |
| eth_buy_hold | ETH buy-and-hold | -0.239 | -35.10% | -67.52% | 0.000 | 100.00% | No | N/A | N/A | benchmark only |
| btc_eth_50_50 | 50/50 BTC/ETH | -0.285 | -27.21% | -59.21% | 0.000 | 100.00% | No | N/A | N/A | benchmark only |
| pure_top10_momentum | Pure momentum benchmark | -0.471 | -45.13% | -71.82% | 24.139 | 100.00% | No | N/A | N/A | benchmark only |
