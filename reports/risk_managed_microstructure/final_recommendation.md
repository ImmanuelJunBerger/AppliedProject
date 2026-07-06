# Final recommendation

## Decision

Evidence supports **prospective data collection, not capital paper trading**.

## Baseline risk-managed momentum

- Selected holdout Sharpe: -0.663
- Selected holdout CAGR: -17.37%
- Acceptance pass: No
- Failures: holdout Sharpe <= 0.5; holdout CAGR <= 0; does not survive 50 bps; annual turnover > 12x

## Microstructure evidence

Microstructure overlays were not run as final locked-holdout strategies because
complete historical Binance Futures order-book/trade-flow features were not
available locally. Current/recent public endpoints are useful for prospective
collection, but they do not by themselves create a valid 2025+ holdout feature
panel.

## Bottom line

Do not allocate capital based on this module yet. If continuing, collect
microstructure data prospectively and evaluate it only after a separately locked
future paper holdout exists.
