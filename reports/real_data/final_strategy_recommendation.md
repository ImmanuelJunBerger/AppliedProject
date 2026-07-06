# Final strategy recommendation

- Volatility breakout remains above 0.8 Sharpe: **False** (0.651 on the stated reference period).
- ML effect: **does not improve both validation and holdout**.
- Untouched holdout survived: **False**.
- Paper-trading recommendation: **not yet suitable for paper trading**.

The production decision is based on the untouched holdout and statistical uncertainty, not on the best exploratory robustness cell. A positive point estimate is insufficient when the holdout confidence interval or deflated-Sharpe evidence is weak.
