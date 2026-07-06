# Final recommendation

**3. Recommend stopping because no preselected candidate passes the criteria.**

Do not paper trade these rules; return to research only with a new predeclared hypothesis.

The primary rule was selected before opening the holdout:

- Strategy: **D_btc_eth_biweekly_vt25**
- Family: D_low_turnover_btc_eth_trend
- Parameters: `{"drawdown_brake": null, "drawdown_threshold": -0.2, "family": "D_low_turnover_btc_eth_trend", "name": "D_btc_eth_biweekly_vt25", "rebalance_weeks": 2, "top_k": 0, "volatility_probability_threshold": 0.75, "volatility_target": 0.25}`
- For family D, only `rebalance_weeks` and `volatility_target` are grid parameters; volatility probability is a fixed continuous sizing input.
- Holdout Sharpe: 0.023
- Holdout CAGR: -0.52%
- Holdout max drawdown: -11.19%
- Holdout annual turnover: 3.20x
- Acceptance failures: holdout Sharpe is not above 0.5; holdout CAGR is not positive; performance collapses at 50 bps

No alternative is promoted because it happened to look better in the locked holdout.
