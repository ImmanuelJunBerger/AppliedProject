# Final recommendation

1. Does using all accepted features improve performance versus Tier-1 feature selection? No. The best development-CPCV prediction configuration was `macro_tier1__frozen_macro_positive_next_period__extra_trees` with feature set `macro_tier1`. The best all-feature prediction configuration was `all_accepted_auto_selection__frozen_macro_positive_next_period__elastic_net_logistic`, but the development-selected full-feature trading candidate failed the locked holdout.
2. Do complex models outperform simpler models? Not economically. The top development prediction model was `extra_trees`, and the selected full-feature alpha layer used ML probabilities, but the resulting strategy had negative holdout Sharpe and failed statistical controls.
3. Is any improvement real or overfit? The replacement rules classify the selected ML result as **reject_full_feature_ml_keep_frozen**.
4. Does any model beat btc_eth_macro_gate_balanced on locked holdout? No development-selected ML strategy beat the frozen benchmark. Selected ML holdout Sharpe is -0.387 versus frozen 0.970.
5. Does it survive 50 bps costs? No. Selected 50 bps holdout Sharpe is -0.423; CAGR is -30.95%.
6. Should full-feature ML replace, complement, or be rejected? **Full-feature ML is rejected; keep btc_eth_macro_gate_balanced unchanged.**

The frozen strategy remains the benchmark unless a future data source/model clears the full evidence standard without relying on holdout tuning or cash-driven Sharpe.
