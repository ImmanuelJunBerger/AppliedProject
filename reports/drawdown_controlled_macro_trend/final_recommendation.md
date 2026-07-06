# Final recommendation

Final decision: **keep_frozen_strategy**

Replacement failures: holdout net Sharpe at 25 bps does not improve materially; holdout exposure is not above 35%; deflated Sharpe probability is weak; bootstrap Sharpe delta confidence interval is not supportive

## Final questions

1. **Can the -74% development drawdown be materially repaired?** Yes for the development-selected candidate. Frozen development max DD -74.09% versus selected -49.42%.
2. **Does any candidate preserve or improve holdout Sharpe?** Yes in the diagnostic table, but the best holdout cell was not selected by development CPCV. Best holdout Sharpe was `frozen_pi_static_85_m3_r14` at 1.064, versus frozen 0.970. The development-selected candidate `frozen_dd_10_reduce_50_r14` had holdout Sharpe 0.926, so it did not preserve/improve Sharpe.
3. **Does any candidate achieve higher exposure without worse drawdown?** No across the diagnostic grid. The development-selected candidate had exposure 15.61% versus frozen 28.95%.
4. **Does BTC-only solve the problem better than BTC/ETH?** No replacement conclusion is made from BTC-only variants unless they pass the full rules; the diagnostic benchmark remains BTC/ETH/cash.
5. **Does ETH-only solve the problem better than BTC/ETH?** No. ETH-only variants remain concentration-risk diagnostics unless the selected candidate and controls support replacement.
6. **Does CPPI/TIPP-style portfolio insurance help?** Best portfolio-insurance holdout Sharpe 1.064 with max DD -23.01%, but it was not development-selected and did not clear all replacement rules. It remains path-dependent and gap-risk sensitive.
7. **Does volatility targeting help?** Best volatility-overlay holdout Sharpe 1.028 with max DD -20.09%, but it did not justify replacement.
8. **Does trend confirmation help?** Best trend-family holdout Sharpe 0.974 with max DD -4.48%, but trend-confirmed candidates did not dominate the frozen benchmark under the full rule set.
9. **Is the improvement real or overfit?** not robust enough for replacement.
10. **Should btc_eth_macro_gate_balanced be replaced?** No.
11. **Should the Applied Project title change?** No. Keep **Macro-Regime Conditioning for Systematic Cryptocurrency Allocation: A Robust Out-of-Sample Evaluation**.

