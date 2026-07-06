# Feature importance stability

Permutation and model-importance stability are computed for the best development-CPCV prediction configuration.

## Stability summary

| Feature | Model importance mean | Model importance std | Permutation importance mean | Top-5 frequency | Mean top-5 Jaccard |
|---|---|---|---|---|---|
| equity_realized_vol_21d | 0.311 | 0.039 | 0.036 | 100.00% | 78.52% |
| dow_vol_level | 0.240 | 0.047 | 0.014 | 100.00% | 78.52% |
| vix_level | 0.210 | 0.030 | 0.017 | 100.00% | 78.52% |
| vix_change_5d | 0.081 | 0.013 | 0.008 | 90.00% | 78.52% |
| vix_change_21d | 0.079 | 0.031 | 0.003 | 60.00% | 78.52% |
| equity_momentum_21d | 0.078 | 0.038 | -0.002 | 50.00% | 78.52% |

## Raw model importance

| Config | Model | Feature | Importance | Method |
|---|---|---|---|---|
| macro_tier1__btc_eth_50_50_forward_positive_30d__elastic_net_logistic | elastic_net_logistic | vix_level | 0.479 | coefficient |
| macro_tier1__btc_eth_50_50_forward_positive_30d__elastic_net_logistic | elastic_net_logistic | equity_realized_vol_21d | -0.273 | coefficient |
| macro_tier1__btc_eth_50_50_forward_positive_30d__elastic_net_logistic | elastic_net_logistic | vix_change_21d | -0.242 | coefficient |
| macro_tier1__btc_eth_50_50_forward_positive_30d__elastic_net_logistic | elastic_net_logistic | dow_vol_level | 0.212 | coefficient |
| macro_tier1__btc_eth_50_50_forward_positive_30d__elastic_net_logistic | elastic_net_logistic | equity_momentum_21d | -0.187 | coefficient |
| macro_tier1__btc_eth_50_50_forward_positive_30d__elastic_net_logistic | elastic_net_logistic | vix_change_5d | -0.028 | coefficient |
| macro_tier1__btc_eth_50_50_forward_positive_30d__random_forest | random_forest | equity_realized_vol_21d | 0.194 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__random_forest | random_forest | dow_vol_level | 0.192 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__random_forest | random_forest | vix_level | 0.177 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__random_forest | random_forest | vix_change_5d | 0.170 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__random_forest | random_forest | equity_momentum_21d | 0.144 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__random_forest | random_forest | vix_change_21d | 0.123 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__gradient_boosting | gradient_boosting | equity_realized_vol_21d | 0.336 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__gradient_boosting | gradient_boosting | dow_vol_level | 0.230 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__gradient_boosting | gradient_boosting | vix_level | 0.179 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__gradient_boosting | gradient_boosting | equity_momentum_21d | 0.109 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__gradient_boosting | gradient_boosting | vix_change_21d | 0.073 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__gradient_boosting | gradient_boosting | vix_change_5d | 0.073 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__extra_trees | extra_trees | dow_vol_level | 0.270 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__extra_trees | extra_trees | equity_momentum_21d | 0.223 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__extra_trees | extra_trees | vix_level | 0.222 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__extra_trees | extra_trees | equity_realized_vol_21d | 0.127 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__extra_trees | extra_trees | vix_change_5d | 0.085 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__extra_trees | extra_trees | vix_change_21d | 0.074 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__shallow_mlp | shallow_mlp | equity_realized_vol_21d | 0.000 | not_available |
| macro_tier1__btc_eth_50_50_forward_positive_30d__shallow_mlp | shallow_mlp | equity_momentum_21d | 0.000 | not_available |
| macro_tier1__btc_eth_50_50_forward_positive_30d__shallow_mlp | shallow_mlp | dow_vol_level | 0.000 | not_available |
| macro_tier1__btc_eth_50_50_forward_positive_30d__shallow_mlp | shallow_mlp | vix_level | 0.000 | not_available |
| macro_tier1__btc_eth_50_50_forward_positive_30d__shallow_mlp | shallow_mlp | vix_change_5d | 0.000 | not_available |
| macro_tier1__btc_eth_50_50_forward_positive_30d__shallow_mlp | shallow_mlp | vix_change_21d | 0.000 | not_available |
| macro_tier1__btc_eth_50_50_forward_positive_30d__xgboost | xgboost | equity_realized_vol_21d | 0.201 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__xgboost | xgboost | dow_vol_level | 0.198 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__xgboost | xgboost | vix_level | 0.175 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__xgboost | xgboost | equity_momentum_21d | 0.148 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__xgboost | xgboost | vix_change_21d | 0.147 | model_importance |
| macro_tier1__btc_eth_50_50_forward_positive_30d__xgboost | xgboost | vix_change_5d | 0.131 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__elastic_net_logistic | elastic_net_logistic | vix_level | 0.329 | coefficient |
| macro_tier1__btc_forward_30d_gt_10__elastic_net_logistic | elastic_net_logistic | equity_realized_vol_21d | -0.236 | coefficient |
| macro_tier1__btc_forward_30d_gt_10__elastic_net_logistic | elastic_net_logistic | vix_change_5d | -0.151 | coefficient |
| macro_tier1__btc_forward_30d_gt_10__elastic_net_logistic | elastic_net_logistic | dow_vol_level | 0.116 | coefficient |
| macro_tier1__btc_forward_30d_gt_10__elastic_net_logistic | elastic_net_logistic | equity_momentum_21d | -0.088 | coefficient |
| macro_tier1__btc_forward_30d_gt_10__elastic_net_logistic | elastic_net_logistic | vix_change_21d | -0.033 | coefficient |
| macro_tier1__btc_forward_30d_gt_10__random_forest | random_forest | equity_realized_vol_21d | 0.192 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__random_forest | random_forest | dow_vol_level | 0.186 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__random_forest | random_forest | vix_change_21d | 0.184 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__random_forest | random_forest | equity_momentum_21d | 0.161 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__random_forest | random_forest | vix_level | 0.141 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__random_forest | random_forest | vix_change_5d | 0.137 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__gradient_boosting | gradient_boosting | equity_realized_vol_21d | 0.372 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__gradient_boosting | gradient_boosting | vix_level | 0.203 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__gradient_boosting | gradient_boosting | vix_change_21d | 0.132 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__gradient_boosting | gradient_boosting | equity_momentum_21d | 0.122 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__gradient_boosting | gradient_boosting | dow_vol_level | 0.107 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__gradient_boosting | gradient_boosting | vix_change_5d | 0.064 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__extra_trees | extra_trees | equity_realized_vol_21d | 0.298 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__extra_trees | extra_trees | equity_momentum_21d | 0.218 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__extra_trees | extra_trees | vix_level | 0.170 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__extra_trees | extra_trees | dow_vol_level | 0.132 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__extra_trees | extra_trees | vix_change_21d | 0.131 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__extra_trees | extra_trees | vix_change_5d | 0.050 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__shallow_mlp | shallow_mlp | equity_realized_vol_21d | 0.000 | not_available |
| macro_tier1__btc_forward_30d_gt_10__shallow_mlp | shallow_mlp | equity_momentum_21d | 0.000 | not_available |
| macro_tier1__btc_forward_30d_gt_10__shallow_mlp | shallow_mlp | dow_vol_level | 0.000 | not_available |
| macro_tier1__btc_forward_30d_gt_10__shallow_mlp | shallow_mlp | vix_level | 0.000 | not_available |
| macro_tier1__btc_forward_30d_gt_10__shallow_mlp | shallow_mlp | vix_change_5d | 0.000 | not_available |
| macro_tier1__btc_forward_30d_gt_10__shallow_mlp | shallow_mlp | vix_change_21d | 0.000 | not_available |
| macro_tier1__btc_forward_30d_gt_10__xgboost | xgboost | equity_realized_vol_21d | 0.188 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__xgboost | xgboost | vix_level | 0.172 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__xgboost | xgboost | vix_change_21d | 0.169 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__xgboost | xgboost | equity_momentum_21d | 0.163 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__xgboost | xgboost | dow_vol_level | 0.158 | model_importance |
| macro_tier1__btc_forward_30d_gt_10__xgboost | xgboost | vix_change_5d | 0.150 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__elastic_net_logistic | elastic_net_logistic | vix_level | 0.715 | coefficient |
| macro_tier1__eth_forward_30d_gt_15__elastic_net_logistic | elastic_net_logistic | equity_realized_vol_21d | -0.556 | coefficient |
| macro_tier1__eth_forward_30d_gt_15__elastic_net_logistic | elastic_net_logistic | vix_change_5d | -0.369 | coefficient |
| macro_tier1__eth_forward_30d_gt_15__elastic_net_logistic | elastic_net_logistic | equity_momentum_21d | -0.316 | coefficient |
| macro_tier1__eth_forward_30d_gt_15__elastic_net_logistic | elastic_net_logistic | dow_vol_level | 0.276 | coefficient |
| macro_tier1__eth_forward_30d_gt_15__elastic_net_logistic | elastic_net_logistic | vix_change_21d | -0.139 | coefficient |
| macro_tier1__eth_forward_30d_gt_15__random_forest | random_forest | dow_vol_level | 0.240 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__random_forest | random_forest | vix_level | 0.208 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__random_forest | random_forest | equity_momentum_21d | 0.176 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__random_forest | random_forest | equity_realized_vol_21d | 0.140 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__random_forest | random_forest | vix_change_21d | 0.134 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__random_forest | random_forest | vix_change_5d | 0.102 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__gradient_boosting | gradient_boosting | vix_level | 0.349 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__gradient_boosting | gradient_boosting | equity_realized_vol_21d | 0.175 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__gradient_boosting | gradient_boosting | dow_vol_level | 0.168 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__gradient_boosting | gradient_boosting | equity_momentum_21d | 0.148 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__gradient_boosting | gradient_boosting | vix_change_21d | 0.086 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__gradient_boosting | gradient_boosting | vix_change_5d | 0.073 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__extra_trees | extra_trees | dow_vol_level | 0.333 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__extra_trees | extra_trees | vix_level | 0.220 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__extra_trees | extra_trees | equity_momentum_21d | 0.217 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__extra_trees | extra_trees | equity_realized_vol_21d | 0.135 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__extra_trees | extra_trees | vix_change_21d | 0.062 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__extra_trees | extra_trees | vix_change_5d | 0.033 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__shallow_mlp | shallow_mlp | equity_realized_vol_21d | 0.000 | not_available |
| macro_tier1__eth_forward_30d_gt_15__shallow_mlp | shallow_mlp | equity_momentum_21d | 0.000 | not_available |
| macro_tier1__eth_forward_30d_gt_15__shallow_mlp | shallow_mlp | dow_vol_level | 0.000 | not_available |
| macro_tier1__eth_forward_30d_gt_15__shallow_mlp | shallow_mlp | vix_level | 0.000 | not_available |
| macro_tier1__eth_forward_30d_gt_15__shallow_mlp | shallow_mlp | vix_change_5d | 0.000 | not_available |
| macro_tier1__eth_forward_30d_gt_15__shallow_mlp | shallow_mlp | vix_change_21d | 0.000 | not_available |
| macro_tier1__eth_forward_30d_gt_15__xgboost | xgboost | dow_vol_level | 0.212 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__xgboost | xgboost | vix_level | 0.205 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__xgboost | xgboost | equity_momentum_21d | 0.156 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__xgboost | xgboost | equity_realized_vol_21d | 0.153 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__xgboost | xgboost | vix_change_5d | 0.147 | model_importance |
| macro_tier1__eth_forward_30d_gt_15__xgboost | xgboost | vix_change_21d | 0.127 | model_importance |
| macro_tier1__frozen_macro_positive_next_period__elastic_net_logistic | elastic_net_logistic | vix_level | 0.769 | coefficient |
| macro_tier1__frozen_macro_positive_next_period__elastic_net_logistic | elastic_net_logistic | vix_change_5d | -0.218 | coefficient |
| macro_tier1__frozen_macro_positive_next_period__elastic_net_logistic | elastic_net_logistic | vix_change_21d | -0.183 | coefficient |
| macro_tier1__frozen_macro_positive_next_period__elastic_net_logistic | elastic_net_logistic | equity_momentum_21d | -0.032 | coefficient |
| macro_tier1__frozen_macro_positive_next_period__elastic_net_logistic | elastic_net_logistic | equity_realized_vol_21d | 0.000 | coefficient |
| macro_tier1__frozen_macro_positive_next_period__elastic_net_logistic | elastic_net_logistic | dow_vol_level | 0.000 | coefficient |
| macro_tier1__frozen_macro_positive_next_period__random_forest | random_forest | equity_realized_vol_21d | 0.239 | model_importance |
| macro_tier1__frozen_macro_positive_next_period__random_forest | random_forest | vix_level | 0.219 | model_importance |
| macro_tier1__frozen_macro_positive_next_period__random_forest | random_forest | dow_vol_level | 0.174 | model_importance |
| macro_tier1__frozen_macro_positive_next_period__random_forest | random_forest | vix_change_21d | 0.156 | model_importance |
| macro_tier1__frozen_macro_positive_next_period__random_forest | random_forest | vix_change_5d | 0.129 | model_importance |
| macro_tier1__frozen_macro_positive_next_period__random_forest | random_forest | equity_momentum_21d | 0.082 | model_importance |
