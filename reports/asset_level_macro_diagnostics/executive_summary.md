# Executive summary

This standalone diagnostic explains the frozen strategy **btc_eth_macro_gate_balanced**.  It does not modify, reselect, or retune the strategy.

## Key reconciliation

- Holdout gross Sharpe at 0 bps: 1.066
- Holdout net Sharpe at 25 bps: 0.970
- Development gross Sharpe at 0 bps: 0.676
- Development net Sharpe at 25 bps: 0.618
- Development net max drawdown at 25 bps: -74.09%
- Holdout net max drawdown at 25 bps: -18.42%

## Interpretation

The strong holdout Sharpe is a **holdout-period, mostly risk-avoidance result**, not evidence that the strategy always had stable performance.  The development-period drawdown is real in the frozen backtest and is driven by being exposed during a severe crypto drawdown regime before the macro gate moved sufficiently defensive.

No implementation error was found in this diagnostic.  The final strategy remains **btc_eth_macro_gate_balanced** and should still be framed as a paper-monitoring candidate, not proven live alpha.
