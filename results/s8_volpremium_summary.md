# S8: Volatility risk premium — summary — SHARPE IS MISLEADING HERE, READ THE TAIL STATS

Proxy: CBOE S&P 500 PutWrite Index (`^PUT`, a genuine published CBOE benchmark, not a constructed
series), 1996-2026, net of an assumed 0.5%/yr ETF-wrapper drag. Cross-check: SVXY (real short-vol
ETF, 2011+).

**Data bug caught and fixed before publishing**: Yahoo's `^PUT` print for 2020-03-13 showed the
index up +35% in one day while SPX itself was up +9.3% — implausible for a passive monthly
put-write index, and it mechanically produced an equally implausible -28% "correction" three
trading days later. Cross-checked against SPX's own (real, extreme) moves that week; the single
suspect print was dropped rather than silently smoothed, with 2020-03-16's return recomputed
against the last trusted close.

| Metric | Full sample (net) | In-sample | Holdout |
|---|---|---|---|
| Sharpe (annualized) | 0.66 | 0.67 | 0.63 |
| p-value | - | 0.0010 | 0.029 |
| **Skew** | **-0.73** | -0.57 | **-1.16** |
| Excess kurtosis | 27.5 | 25.9 | 31.8 |
| **Max drawdown** | **-37.3%** | -37.3% | -29.0% |
| **Worst single day** | **-9.8%** | -9.4% | -9.8% |
| Worst single month | -17.7% | -17.7% | -13.5% |

Regime breakdown, full detail: `results/s8_volpremium_raw.json`. Returns: `results/s8_volpremium_PUT_net_returns.csv`.

**SVXY cross-check (real tradeable ETF, 2011+) makes the warning concrete**: Sharpe 0.56 — similar
to PUT's — but max drawdown **-95.2%** and worst single day **-83.0%**. A Sharpe ratio in the
same neighborhood as PUT's utterly fails to signal that this instrument came within a few percent
of a total wipeout. **This is exactly why Sharpe is the wrong single number for this strategy**,
stated as bluntly as the pre-registration required.

**Verdict: statistically significant (p<0.03 in holdout too), and genuinely dangerous.** Negatively
skewed, fat-tailed, capable of -30-40% drawdowns and near-total wipeouts in the ETF-wrapper case.
It technically clears this run's mechanical evidence bar (>=100 obs, positive Sharpe IS and
holdout, p<0.05 in both). It is carried into the portfolio-construction step on that basis, but
**flagged for special treatment there** (position-sized or weighted with its tail risk explicitly
in view, never allocated as if its Sharpe were the whole story) — treating it identically to a
symmetric-return strategy at the same Sharpe would be a real, avoidable mistake.
