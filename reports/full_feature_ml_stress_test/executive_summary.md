# Executive summary

Study: **Full-Feature Machine Learning Stress Test for Macro-Regime Cryptocurrency Allocation**

The frozen strategy **btc_eth_macro_gate_balanced** was not modified, reselected, or retuned.

## Outcome

- Selected development-CPCV ML strategy: ml_full_feature_alpha_7d_s+10
- Final decision: reject_full_feature_ml_keep_frozen
- Strategy gate outcome: Full-feature ML is rejected; keep btc_eth_macro_gate_balanced unchanged.
- Tested prediction configurations: 121
- Tested strategy configurations: 22
- PBO: 5.71%
- Deflated Sharpe probability: 0.09%
- Bootstrap Sharpe CI: [-1.917, 0.995]

Failure reasons: holdout Sharpe does not materially improve versus frozen strategy; holdout CAGR is not comparable or better; max drawdown worsens materially; does not survive 50 bps costs; deflated Sharpe probability is weak; bootstrap Sharpe CI includes negative outcomes
