# Data and features

## Data sources

- Crypto panel: Binance OHLCV research dataset.
- Macro features: WRDS CRSP/CBOE/FRB targeted daily series.
- Public crypto-native features were available in prior modules but the final
  selected strategy uses macro features only.

## Feature activation

| Feature | Activation rate | Favourable weeks | Total weeks | Average value | Threshold |
|---|---|---|---|---|---|
| vix_change_21d | 52.31% | 204 | 390 | -0.044 | -0.180 |
| equity_momentum_21d | 49.23% | 192 | 390 | 0.008 | 0.016 |
| vix_change_5d | 44.36% | 173 | 390 | 0.238 | -0.160 |
| equity_realized_vol_21d | 43.33% | 169 | 390 | 0.154 | 0.141 |
| dow_vol_level | 41.54% | 162 | 390 | 18.776 | 17.840 |
| vix_level | 41.03% | 160 | 390 | 20.130 | 19.540 |

## Most common favourable gate drivers

| Feature | Favourable weeks | Fraction weeks |
|---|---|---|
| vix_change_21d | 204 | 52.31% |
| equity_momentum_21d | 192 | 49.23% |
| vix_change_5d | 173 | 44.36% |
| equity_realized_vol_21d | 169 | 43.33% |
| dow_vol_level | 162 | 41.54% |
| vix_level | 160 | 41.03% |

## Most common risk-off / reduced-risk blockers

| Feature | Blocking weeks | Fraction weeks |
|---|---|---|
| vix_level | 230 | 58.97% |
| dow_vol_level | 228 | 58.46% |
| equity_realized_vol_21d | 221 | 56.67% |
| vix_change_5d | 217 | 55.64% |
| equity_momentum_21d | 198 | 50.77% |
| vix_change_21d | 186 | 47.69% |

## Regime and allocation activation

| Macro regime | Allocation | Weeks | Average exposure | Average cash | Avg favourable features |
|---|---|---|---|---|---|
| neutral | BTC/ETH | 89 | 50.00% | 50.00% | 3.000 |
| neutral | cash | 3 | 0.00% | 100.00% | 3.000 |
| risk_off | cash | 183 | 0.00% | 100.00% | 1.361 |
| risk_on | BTC/ETH | 112 | 100.00% | 0.00% | 4.670 |
| risk_on | cash | 3 | 0.00% | 100.00% | 4.000 |

## Allocation explanations

The strategy target allocation is cash when the macro gate is risk-off, reduced
BTC/ETH exposure when neutral, and full BTC/ETH exposure when risk-on. Weekly
target explanations are written to `allocation_explanations_weekly.csv`.

| Allocation | Weeks | Average exposure | Average cash |
|---|---|---|---|
| BTC/ETH | 201 | 77.86% | 22.14% |
| cash | 189 | 0.00% | 100.00% |
