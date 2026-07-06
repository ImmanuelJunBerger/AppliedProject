# Final recommendation

1. **Does ML improve cross-sectional momentum?** No, not under the locked economic-value criterion.
2. **Does it survive the locked holdout?** No.
3. **Best target selected on development:** forward_rank.
4. **Best model selected on development:** random_forest.
5. **Does it beat pure momentum after 25 bps?** No robust improvement.
6. **Suitable for paper trading?** No.
7. **What failed?** the development-selected ML score did not deliver a statistically supported holdout Sharpe/CAGR improvement over pure momentum; the champion did not retain both positive holdout Sharpe and CAGR.

## Statistical controls

- Champion holdout Sharpe CI: {'lower': -1.614636535784934, 'median': -0.2552042773162856, 'upper': 1.3412535239089993}.
- Pure momentum holdout Sharpe CI: {'lower': -2.0899403278444972, 'median': -0.8513409993546783, 'upper': 0.5053431285131046}.
- Paired Sharpe delta CI: {'lower': -0.28863970919140347, 'median': 0.5903893467312593, 'upper': 1.493052910980395}.
- Deflated-Sharpe probability: 0.24%.
- Approximate probability of backtest overfitting: 28.57%.
- Tested configurations: 127.

The recommendation is based on the locked champion, not the best holdout cell in the robustness grid.
