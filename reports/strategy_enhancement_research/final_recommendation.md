# Final recommendation

## Recommendation

The following enhancement survived the predeclared criteria: meta_gradient_boosting_60. Paper-monitor it separately as a conservative overlay, while keeping btc_eth_macro_gate_balanced frozen as the selected benchmark.

## Rationale

The goal was not to maximize holdout Sharpe. The goal was to identify an
economically defensible enhancement that survives development-only CPCV and
locked holdout evaluation. Every hypothesis was evaluated independently and
failures are reported.

Final decision: **paper-monitor the strongest surviving enhancement without modifying the frozen strategy**.

## Study outcomes

| Study | Selected candidate | Status | Conclusion |
|---|---|---|---|
| study_1_exposure_sizing | discrete_aggressive | failed_holdout | Candidate improves or ranks well in development but fails locked holdout economics. |
| study_2_meta_labeling | meta_gradient_boosting_60 | survives | Candidate improves frozen benchmark under the predeclared criteria; treat as a paper-monitoring enhancement, not a replacement. |
| study_3_asset_selection | asset_btc_uncertain_eth_strong | failed_holdout | Candidate improves or ranks well in development but fails locked holdout economics. |
| study_4_dynamic_horizon | fixed_momentum_126d | failed_holdout | Candidate improves or ranks well in development but fails locked holdout economics. |
| study_5_signal_ensemble | ensemble_equal_weight | failed_holdout | Candidate improves or ranks well in development but fails locked holdout economics. |

The frozen selected strategy remains unchanged.
