# Executive summary

Project: **Macro-Regime Conditioning for Systematic Cryptocurrency Allocation: A Robust Out-of-Sample Evaluation**

The frozen selected strategy remains **btc_eth_macro_gate_balanced**. It was not modified,
replaced, or reselected.

## Frozen benchmark

- Development Sharpe: 0.628
- Holdout Sharpe: 0.970
- Holdout CAGR: 25.07%
- Holdout max drawdown: -18.42%

## Enhancement decisions

| Study | Development-selected candidate | Status | Holdout Sharpe | Holdout CAGR | PBO | Deflated Sharpe probability | Passes criteria |
|---|---|---|---|---|---|---|---|
| study_1_exposure_sizing | discrete_aggressive | failed_holdout | -0.261 | -14.89% | 34.29% | 5.29% | No |
| study_2_meta_labeling | meta_gradient_boosting_60 | survives | 1.582 | 17.31% | 30.00% | 88.49% | Yes |
| study_3_asset_selection | asset_btc_uncertain_eth_strong | failed_holdout | -0.856 | -33.61% | 22.86% | 1.81% | No |
| study_4_dynamic_horizon | fixed_momentum_126d | failed_holdout | -0.426 | -28.36% | 27.14% | 2.86% | No |
| study_5_signal_ensemble | ensemble_equal_weight | failed_holdout | -0.216 | -10.13% | 72.86% | 9.44% | No |

Final decision: **paper-monitor the strongest surviving enhancement without modifying the frozen strategy**.
