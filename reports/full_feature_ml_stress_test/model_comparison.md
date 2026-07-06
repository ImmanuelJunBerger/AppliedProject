# Model comparison

Model selection uses development CPCV only. Holdout metrics are reported after selection and are not used for promotion.

Stacking note: Stacking evaluated only for the top development-supported feature/target pair.

## Top development-CPCV prediction configurations

| Config | Feature set | Model | Target | AUC | Precision | Recall | F1 | Brier | Train AUC | Train/validation gap | Selection score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| macro_tier1__frozen_macro_positive_next_period__extra_trees | macro_tier1 | extra_trees | frozen_macro_positive_next_period | 68.84% | 48.07% | 85.29% | 61.48% | 23.34% | 73.71% | 4.87% | 51.16% |
| macro_tier1__frozen_macro_positive_next_period__random_forest | macro_tier1 | random_forest | frozen_macro_positive_next_period | 68.50% | 48.90% | 87.25% | 62.68% | 22.22% | 84.85% | 16.35% | 50.92% |
| macro_tier1__frozen_macro_positive_next_period__elastic_net_logistic | macro_tier1 | elastic_net_logistic | frozen_macro_positive_next_period | 67.69% | 51.82% | 69.61% | 59.41% | 22.96% | 69.16% | 1.47% | 50.53% |
| macro_tier1__frozen_macro_positive_next_period__stacking_ensemble | macro_tier1 | stacking_ensemble | frozen_macro_positive_next_period | 67.97% | 43.98% | 93.14% | 59.75% | 23.85% | 69.34% | 1.37% | 49.96% |
| macro_plus_crypto_tier1__frozen_macro_positive_next_period__extra_trees | macro_plus_crypto_tier1 | extra_trees | frozen_macro_positive_next_period | 67.97% | 46.55% | 79.41% | 58.70% | 23.30% | 76.13% | 8.16% | 49.73% |
| macro_plus_crypto_tier1__frozen_macro_positive_next_period__random_forest | macro_plus_crypto_tier1 | random_forest | frozen_macro_positive_next_period | 66.65% | 46.15% | 82.35% | 59.15% | 22.55% | 87.24% | 20.59% | 47.96% |
| macro_plus_crypto_tier1__frozen_macro_positive_next_period__elastic_net_logistic | macro_plus_crypto_tier1 | elastic_net_logistic | frozen_macro_positive_next_period | 65.27% | 43.94% | 85.29% | 58.00% | 23.30% | 70.56% | 5.28% | 47.24% |
| all_accepted_auto_selection__frozen_macro_positive_next_period__elastic_net_logistic | all_accepted_auto_selection | elastic_net_logistic | frozen_macro_positive_next_period | 64.60% | 44.33% | 88.24% | 59.02% | 23.68% | 70.79% | 6.19% | 46.20% |
| macro_tier1__frozen_macro_positive_next_period__xgboost | macro_tier1 | xgboost | frozen_macro_positive_next_period | 64.42% | 48.98% | 70.59% | 57.83% | 22.45% | 88.65% | 24.23% | 45.32% |
| all_accepted_auto_selection__frozen_macro_positive_next_period__extra_trees | all_accepted_auto_selection | extra_trees | frozen_macro_positive_next_period | 64.77% | 39.08% | 100.00% | 56.20% | 23.95% | 78.36% | 13.59% | 45.08% |
| all_accepted__frozen_macro_positive_next_period__random_forest | all_accepted | random_forest | frozen_macro_positive_next_period | 65.03% | 42.67% | 94.12% | 58.72% | 23.20% | 92.72% | 27.69% | 44.93% |
| macro_tier1__frozen_macro_positive_next_period__gradient_boosting | macro_tier1 | gradient_boosting | frozen_macro_positive_next_period | 63.32% | 48.34% | 71.57% | 57.71% | 22.76% | 88.56% | 25.23% | 43.81% |

## Target diagnostics

| Target | Description | Split | Observations | Positive events | Prevalence |
|---|---|---|---|---|---|
| btc_eth_50_50_forward_positive_30d | BTC/ETH 50-50 30-day forward return positive | development | 261 | 148 | 56.70% |
| btc_eth_50_50_forward_positive_30d | BTC/ETH 50-50 30-day forward return positive | holdout | 73 | 35 | 47.95% |
| btc_forward_30d_gt_10 | BTC forward 30-day return > +10% | development | 261 | 95 | 36.40% |
| btc_forward_30d_gt_10 | BTC forward 30-day return > +10% | holdout | 73 | 12 | 16.44% |
| eth_forward_30d_gt_15 | ETH forward 30-day return > +15% | development | 261 | 91 | 34.87% |
| eth_forward_30d_gt_15 | ETH forward 30-day return > +15% | holdout | 73 | 13 | 17.81% |
| frozen_macro_positive_next_period | Frozen macro strategy next-period return positive | development | 261 | 102 | 39.08% |
| frozen_macro_positive_next_period | Frozen macro strategy next-period return positive | holdout | 73 | 24 | 32.88% |
| avoid_large_negative_btc_eth_30d | Avoid exposure before large negative next-period BTC/ETH return | development | 261 | 205 | 78.54% |
| avoid_large_negative_btc_eth_30d | Avoid exposure before large negative next-period BTC/ETH return | holdout | 73 | 51 | 69.86% |
