# Crisis label design

Labels are supervised targets only. They are not used as live-decision features.

| Target | Definition | Development positive rate | Holdout positive rate |
|---|---|---|---|
| target_a_30d_loss_gt_20 | BTC/ETH 50-50 loses more than 20% over next 30 days | 7.77% | 12.34% |
| target_b_60d_loss_gt_30 | BTC/ETH 50-50 loses more than 30% over next 60 days | 6.18% | 6.49% |
| target_c_forward_vol_top20 | Forward 30d realized volatility exceeds development 80th percentile | 20.03% | 9.83% |
| target_d_future_drawdown_gt_25 | BTC/ETH portfolio enters >25% drawdown from rolling 90d high | 42.55% | 59.41% |
| target_e_frozen_future_dd_gt_20 | Frozen macro strategy has >20% forward drawdown over next 60 days | 14.50% | 0.00% |
