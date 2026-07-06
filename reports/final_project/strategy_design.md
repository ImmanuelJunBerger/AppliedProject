# Strategy design

## Allocation rule

`btc_eth_macro_gate_balanced` is a BTC/ETH/cash allocation strategy.

- **Risk-on:** target BTC/ETH exposure, usually 50% BTC and 50% ETH when both
  are eligible.
- **Neutral:** target reduced BTC/ETH exposure, usually 25% BTC and 25% ETH
  with 50% cash.
- **Risk-off:** hold cash.
- If only one of BTC/ETH is eligible, the single-asset weight is capped at 50%.

## Why it de-risks

The strategy de-risks when the macro feature vote count is insufficient. The
economic idea is that crypto beta should be held only when cross-asset risk
conditions are supportive enough.

## Turnover and costs

- Rebalance: weekly.
- Turnover cap: 0.75.
- Baseline transaction cost: 25 bps.
- Cost sensitivity: 10, 25, 50, and 100 bps.
- Costs are deducted as turnover multiplied by the bps cost rate.

## Regime frequency and allocation contribution

| Regime | Weeks | Frequency | Forward BTC/ETH 7d | BTC weight | ETH weight | Cash weight | Exposure |
|---|---|---|---|---|---|---|---|
| neutral | 92 | 23.59% | 1.49% | 24.18% | 24.18% | 51.63% | 48.37% |
| risk_off | 183 | 46.92% | 0.71% | 0.00% | 0.00% | 100.00% | 0.00% |
| risk_on | 115 | 29.49% | 1.61% | 48.70% | 48.70% | 2.61% | 97.39% |

| Allocation | Weeks | Frequency | Forward BTC/ETH 7d | BTC weight | ETH weight | Cash weight | Exposure |
|---|---|---|---|---|---|---|---|
| BTC/ETH | 201 | 51.54% | 1.38% | 38.93% | 38.93% | 22.14% | 77.86% |
| cash | 189 | 48.46% | 0.92% | 0.00% | 0.00% | 100.00% | 0.00% |
