# Risk management comparison

Risk management was applied after alpha generation. `none` is included only as
a control to measure whether post-alpha risk controls add value.

| Architecture | Risk layer | Median selection score | Median dev turnover | Median dev exposure |
|---|---|---|---|---|
| hybrid | vol_target | 0.897 | 6.139 | 33.82% |
| hybrid | none | 0.880 | 9.709 | 59.45% |
| expansion_first | vol_target | 0.631 | 8.994 | 35.85% |
| expansion_first | none | 0.590 | 12.031 | 84.05% |
| hybrid | vol_target_drawdown_brake_macro_gate | 0.487 | 2.944 | 5.28% |
| expansion_first | vol_target_drawdown_brake_macro_gate | 0.487 | 2.015 | 4.80% |
| expansion_first | macro_gate | 0.471 | 13.300 | 36.73% |
| hybrid | macro_gate | 0.471 | 12.441 | 32.40% |
| hybrid | vol_target_macro_gate | 0.402 | 6.107 | 16.10% |
| expansion_first | vol_target_macro_gate | 0.375 | 6.038 | 15.71% |
| hybrid | vol_target_drawdown_brake | -0.239 | 3.807 | 9.78% |
| hybrid | drawdown_brake | -0.282 | 5.733 | 16.58% |
| expansion_first | drawdown_brake | -0.439 | 5.948 | 18.57% |
| expansion_first | vol_target_drawdown_brake | -0.535 | 2.741 | 10.10% |
