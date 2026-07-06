# Executive summary

Project title: **Macro-Regime Conditioning for Systematic Cryptocurrency
Allocation: A Robust Out-of-Sample Evaluation**.

The selected strategy is **btc_eth_macro_gate_balanced**, a fixed BTC/ETH/cash
macro-risk gate. This final stage does not change the strategy, search for new
strategies, or tune on holdout.

## Locked-holdout result at 25 bps

- CAGR: 25.07%
- Sharpe: 0.970
- Sortino: 1.234
- Max drawdown: -18.42%
- Calmar: 1.361
- Annual turnover: 10.177x
- Exposure: 28.95%
- Worst month: -5.98%

## Final conclusion

`btc_eth_macro_gate_balanced` is a strong **paper-monitoring** candidate and a robust
research result in the limited sense that it survived the locked holdout and
beat simple crypto-beta benchmarks after costs. It is **not** proven live alpha,
and it is not guaranteed profitable.

The main caution is statistical: original macro-regime PBO is
61.43% and deflated Sharpe probability is
42.45%.
