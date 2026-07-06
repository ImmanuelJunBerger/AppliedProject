# Tier-1 regime-gated cross-sectional crypto momentum

## Protocol

- Regime gate features: `stablecoin_supply_change_7d, tvl_growth_30d, volatility_4h_7d, volatility_expansion_probability, cross_sectional_dispersion`.
- No Tier 2 or Tier 3 feature is used for regime classification.
- Selection layer: simple cross-sectional momentum ranks only; this layer does not predict individual returns.
- Development period: through 2024-12-31.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: CPCV inside development only.
- Tested configurations: 768.
- Selected candidate: **u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum**.

## Selected candidate

```json
{
  "name": "u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum",
  "universe_size": 10,
  "rebalance_days": 7,
  "momentum_signal": "momentum_63d",
  "top_k": 3,
  "threshold_set": "balanced",
  "risk_on_votes": 4,
  "neutral_policy": "reduced_momentum",
  "turnover_cap": 0.75,
  "max_asset_weight": 0.2
}
```

## Development comparison at 25 bps

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 62.76% | 1.553 | 1.597 | -45.43% | 1.381 | 12.865 | 24.99% |
| btc_eth_50_50 | 83.92% | 1.222 | 1.596 | -76.25% | 1.101 | 0.000 | 100.00% |
| eth_buy_hold | 91.49% | 1.202 | 1.633 | -79.30% | 1.154 | 0.000 | 100.00% |
| btc_buy_hold | 66.95% | 1.121 | 1.493 | -76.63% | 0.874 | 0.000 | 100.00% |
| pure_cross_sectional_momentum | 55.31% | 1.058 | 1.471 | -72.63% | 0.762 | 17.056 | 60.00% |
| equal_weight_top30 | 36.04% | 0.809 | 1.003 | -90.37% | 0.399 | 2.850 | 100.00% |

## Locked holdout comparison

| Strategy | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure |
|---|---|---|---|---|---|---|---|
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | 4.88% | 0.313 | 0.322 | -26.35% | 0.185 | 16.586 | 26.76% |
| eth_buy_hold | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% |
| btc_eth_50_50 | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% |
| btc_buy_hold | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% |
| pure_cross_sectional_momentum | -25.58% | -0.584 | -0.831 | -47.00% | -0.544 | 15.367 | 60.00% |
| equal_weight_top30 | -55.24% | -0.658 | -0.953 | -76.26% | -0.724 | 3.121 | 100.00% |

## Statistical controls

- Approximate PBO: 57.14%.
- Deflated Sharpe probability for selected holdout returns: 0.26%.
