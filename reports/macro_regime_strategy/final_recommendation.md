# Final recommendation

## Conclusion

Macro-regime conditioning passes the declared paper-trading thresholds, but statistical controls are weak. Treat it as a paper-trading monitoring candidate, not as a capital-ready strategy.

Selected candidate: **btc_eth_macro_gate_balanced**.

## What the test says

- Holdout Sharpe: 0.970
- Holdout CAGR: 25.07%
- Holdout max drawdown: -18.42%
- Holdout annual turnover: 10.177x
- Survives 50 bps: Yes
- Approximate PBO: 61.43%
- Deflated Sharpe probability: 42.45%
- Failures: None

## Does macro conditioning add economic value?

Comparable benchmark: `btc_eth_50_50`.

- Sharpe delta: 1.255
- CAGR delta: 52.27%
- Max-drawdown delta: 40.79%

## Interpretation

The result is strongest as a risk-management and exposure-timing diagnostic.
Because PBO is high and the deflated Sharpe probability is below 50%, the
appropriate next step is paper monitoring, not capital deployment. No holdout
cell was used to select the final candidate; the holdout-best strict variant is
shown below only as a diagnostic.

## Candidate holdout diagnostics

The table below is diagnostic only and was not used for selection.

| Candidate | Family | CAGR | Sharpe | Max DD | Annual turnover | Exposure |
|---|---|---|---|---|---|---|
| btc_eth_macro_gate_strict | BTC/ETH/cash macro risk gate | 25.69% | 1.555 | -4.58% | 3.731 | 7.81% |
| btc_eth_macro_gate_balanced | BTC/ETH/cash macro risk gate | 25.07% | 0.970 | -18.42% | 10.177 | 28.95% |
| btc_eth_macro_crypto_gate_strict | BTC/ETH/cash macro + crypto-native risk gate | 8.87% | 0.918 | -4.58% | 3.392 | 4.88% |
| btc_eth_macro_crypto_gate_balanced | BTC/ETH/cash macro + crypto-native risk gate | 15.50% | 0.874 | -10.99% | 10.177 | 19.52% |
| top10_momentum_macro_gate_strict | Top-10 momentum when macro regime is favourable | 10.70% | 0.852 | -8.53% | 4.688 | 7.69% |
| top10_momentum_macro_crypto_gate_balanced | Top-10 momentum when both macro and crypto-native regimes are favourable | 4.91% | 0.355 | -17.42% | 11.392 | 19.54% |
| top10_momentum_macro_crypto_gate_strict | Top-10 momentum when both macro and crypto-native regimes are favourable | 2.13% | 0.280 | -8.53% | 3.799 | 4.88% |
| top10_momentum_macro_gate_balanced | Top-10 momentum when macro regime is favourable | 2.59% | 0.226 | -20.03% | 13.164 | 29.06% |
