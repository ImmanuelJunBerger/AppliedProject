# Strategy 3: Short-horizon reversal — summary

Same universe/caveats as Strategy 2. Daily rebalance, long biggest 1/2/3-day losers, short
biggest 1/2/3-day winners (quintile, equal-weighted), held 1 day.

| Lookback | Gross return | Gross Sharpe | Net return | Net Sharpe | Trades |
|---|---|---|---|---|---|
| 1d | -87.8% | -1.35 | -99.95% (near wipeout) | -6.64 | 655 |
| 2d | -74.5% | -0.77 | -99.44% | -4.33 | 654 |
| 3d | -88.9% | -1.39 | -99.31% | -4.18 | 653 |

Full metrics: `results/reversal_raw.json`. Equity curves: `results/reversal_<lb>d_{gross,net}_equity.csv`.

**Verdict: reversal loses money even gross, before a single fee is applied.** This is not a
"fails to survive costs" result — the sign of the effect is wrong for this universe/period. Daily
long-loser/short-winner in this 2024-2026 crypto sample behaves like anti-reversal: recent losers
kept losing and recent winners kept winning at the 1-3 day horizon, i.e. short-horizon momentum
dominated, not mean reversion. Layering ~655 trades/lookback of turnover and fees on top of an
already-negative gross signal turns it into a near-total capital wipeout net of costs.

This is treated as a valid, informative negative result per the task's own honesty standard: a
strategy that loses is a finding, not a failure to report. No parameter search was run to try to
flip the sign — that would be exactly the kind of post-hoc tuning the task instructions prohibit.
Same universe-construction bias as Strategy 2 applies (today's top-50 projected backward); it does
not change the sign of this result, since gross returns are negative before that bias would even
have a chance to help.
