# Locked holdout results

The selected candidate was chosen by development CPCV before reading holdout results.

## Holdout strategies and benchmarks at 25 bps

| Strategy | Family | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | BTC/ETH/cash macro risk gate | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |
| eth_buy_hold | Benchmark | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| btc_eth_50_50 | Benchmark | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| btc_buy_hold | Benchmark | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| pure_top10_momentum | Pure top-10 momentum benchmark | -35.42% | -0.407 | -0.598 | -63.09% | -0.561 | 15.928 | 100.00% |
| equal_weight_top10 | Benchmark | -39.25% | -0.418 | -0.619 | -63.51% | -0.618 | 1.493 | 100.00% |

## Cost sensitivity for selected strategy

| Cost bps | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| 10 | 26.99% | 1.028 | 1.304 | -18.05% | 1.496 | 10.177 | 28.95% |
| 25 | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |
| 50 | 21.92% | 0.874 | 1.115 | -19.03% | 1.152 | 10.177 | 28.95% |
| 100 | 15.85% | 0.681 | 0.871 | -20.25% | 0.783 | 10.177 | 28.95% |

## Acceptance criteria

- Passes paper-trading criteria: Yes
- Holdout Sharpe > 0.5: 0.970
- Holdout CAGR: 25.07%
- Holdout max drawdown: -18.42%
- Holdout annual turnover: 10.177x
- Survives 50 bps: Yes
- Failures: None
