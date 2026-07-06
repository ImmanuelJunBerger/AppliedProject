# Final recommendation

1. **Do Tier-1 features identify favourable crypto regimes?**
   Partially. The selected gate creates distinct risk-on/neutral/risk-off states,
   but holdout evidence is weak. In holdout, the selected gate spent
   49.63% of days in risk-off, and the main benefit came
   from reducing exposure during bad periods rather than from finding a strongly
   profitable risk-on momentum regime. The result should be treated cautiously
   because PBO is 57.14% and the deflated Sharpe
   probability is 0.26%.

2. **Does cross-sectional momentum perform better inside those regimes?**
   The regime-gated strategy outperformed pure cross-sectional momentum on the
   locked holdout: selected Sharpe 0.313 versus pure momentum
   Sharpe -0.584. However, the holdout risk-on pure-momentum Sharpe
   was only 0.014, so the gate did not clearly identify a
   robust high-return momentum state.

3. **Does the regime-gated strategy survive the locked holdout?**
   Only weakly. It had positive holdout CAGR at 25 bps and 50 bps, but holdout Sharpe stayed below the 0.5 acceptance threshold and performance turns negative at 100 bps.

4. **Is it suitable for paper trading?**
   No.

5. **What failed?**
   holdout Sharpe <= 0.5; annual turnover > 12x

No strategy was selected using holdout results.
