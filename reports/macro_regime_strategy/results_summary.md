# Macro-regime conditioned crypto exposure strategy

## Protocol

- Development period: 2020-01-01 to 2024-12-31.
- Locked holdout: 2025-01-01 to 2026-06-22.
- Candidate selection: CPCV inside development only; holdout not used for selection.
- Tested configurations: 8.
- Selected candidate: **btc_eth_macro_gate_balanced**.
- Tier 1 macro features: `equity_realized_vol_21d, equity_momentum_21d, dow_vol_level, vix_level, vix_change_5d, vix_change_21d`.
- Optional Tier 1 crypto-native features: `stablecoin_supply_change_7d, tvl_growth_30d, volatility_expansion_probability, cross_sectional_dispersion`.
- Tier 2 and Tier 3 features are not used for regime gates.

## Selected candidate

```json
{
  "name": "btc_eth_macro_gate_balanced",
  "family": "BTC/ETH/cash macro risk gate",
  "gate_profile": "balanced",
  "use_crypto_gate": false,
  "allocation": "btc_eth",
  "rebalance_days": 7,
  "top_k": 5,
  "universe_size": 10,
  "max_asset_weight": 0.2,
  "turnover_cap": 0.75
}
```

## Development comparison at 25 bps

| Strategy | Family | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| btc_eth_50_50 | Benchmark | 83.92% | 1.222 | 1.596 | -76.25% | 1.101 | 0.000 | 100.00% |
| eth_buy_hold | Benchmark | 91.49% | 1.202 | 1.633 | -79.30% | 1.154 | 0.000 | 100.00% |
| btc_buy_hold | Benchmark | 66.95% | 1.121 | 1.493 | -76.63% | 0.874 | 0.000 | 100.00% |
| equal_weight_top10 | Benchmark | 54.55% | 0.953 | 1.201 | -90.85% | 0.600 | 3.516 | 100.00% |
| pure_top10_momentum | Pure top-10 momentum benchmark | 43.48% | 0.868 | 1.097 | -95.00% | 0.458 | 18.898 | 100.00% |
| btc_eth_macro_gate_balanced | BTC/ETH/cash macro risk gate | 20.00% | 0.628 | 0.593 | -74.09% | 0.270 | 11.088 | 49.81% |

## Locked holdout comparison at 25 bps

| Strategy | Family | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | BTC/ETH/cash macro risk gate | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% |
| eth_buy_hold | Benchmark | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| btc_eth_50_50 | Benchmark | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| btc_buy_hold | Benchmark | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| pure_top10_momentum | Pure top-10 momentum benchmark | -35.42% | -0.407 | -0.598 | -63.09% | -0.561 | 15.928 | 100.00% |
| equal_weight_top10 | Benchmark | -39.25% | -0.418 | -0.619 | -63.51% | -0.618 | 1.493 | 100.00% |

## Statistical controls

- Approximate PBO: 61.43%.
- Deflated Sharpe probability for selected holdout returns: 42.45%.
- Comparable benchmark for selected candidate: `btc_eth_50_50`.
- Holdout Sharpe delta versus comparable benchmark: 1.255.
- Holdout CAGR delta versus comparable benchmark: 52.27%.
- Holdout max-drawdown delta versus comparable benchmark: 40.79%.
