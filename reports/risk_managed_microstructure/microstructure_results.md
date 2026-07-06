# Microstructure strategy results

## Requested comparisons

| Variant | Status | Reason |
|---|---|---|
| A. Pure risk-managed momentum | Run | See `baseline_momentum_results.md`. |
| B. Risk-managed momentum with microstructure confirmation | Not run as final backtest | No complete local historical Binance Futures order-book/trade-flow feature panel covering the locked holdout. The module therefore does not run microstructure-confirmed overlays B/C/D as final backtests. |
| C. Risk-managed momentum with microstructure risk-off filter | Not run as final backtest | No complete local historical Binance Futures order-book/trade-flow feature panel covering the locked holdout. The module therefore does not run microstructure-confirmed overlays B/C/D as final backtests. |
| D. BTC/ETH-only microstructure-confirmed trend | Not run as final backtest | No complete local historical Binance Futures order-book/trade-flow feature panel covering the locked holdout. The module therefore does not run microstructure-confirmed overlays B/C/D as final backtests. |

The correct next step for microstructure is prospective data collection or a
separate historical archive backfill. It would be invalid to tune or evaluate
microstructure overlays on the locked holdout without a complete point-in-time
feature panel.
