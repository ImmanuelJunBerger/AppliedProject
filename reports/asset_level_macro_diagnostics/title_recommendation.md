# Title and strategy implications

1. **Does BTC-only macro timing outperform the current BTC/ETH/cash strategy?** No on the main holdout risk-adjusted metric. BTC-only has holdout Sharpe 0.898, CAGR 16.88%, and max DD -10.67% versus current Sharpe 0.970, CAGR 25.07%, and max DD -18.42%. BTC-only improves drawdown but gives up too much return and Sharpe.
2. **Does ETH-only macro timing outperform the current strategy?** No. ETH-only has holdout Sharpe 0.945, CAGR 32.21%, and max DD -25.99%. It improves CAGR versus BTC-only but has worse drawdown than the current balanced strategy and slightly lower Sharpe.
3. **Does 50/50 BTC/ETH macro timing outperform the current strategy?** It is effectively the current strategy. The 50/50 macro gate has holdout Sharpe 0.970, CAGR 25.07%, and max DD -18.42%, matching **btc_eth_macro_gate_balanced**.
4. **Does BTC/ETH allocation add value beyond simple macro timing?** It adds diversification between BTC defensive crypto beta and ETH speculative upside, but it is not evidence of dynamic BTC-vs-ETH selection alpha. The current strategy is a fixed balanced allocation when the macro gate permits exposure.
5. **Is the strategy mainly risk avoidance or genuine asset-selection alpha?** Mainly **risk avoidance / exposure timing**. Asset selection is simple and static.
6. **Is the development drawdown fatal?** It is a serious limitation, not an implementation error. Development net 25 bps max DD is -74.09% and must be disclosed; it does not invalidate the diagnostic, but it prevents overclaiming live alpha.
7. **Should the AP title remain unchanged?** **Yes.**
8. **Should the title become BTC-specific or ETH-specific?** **No.** Neither BTC-only nor ETH-only clearly dominates the frozen BTC/ETH/cash macro strategy under the diagnostic criteria.
9. **Best final framing:** macro-regime conditioning improves crypto exposure timing and drawdown control in holdout, but the strategy should be framed as a systematic BTC/ETH/cash paper-monitoring candidate, not guaranteed live alpha.

Recommended title: **Macro-Regime Conditioning for Systematic Cryptocurrency Allocation: A Robust Out-of-Sample Evaluation**
