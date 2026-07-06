# Data and feature engineering

## Data sources

- Crypto panel: Binance OHLCV research dataset.
- Macro features: WRDS-derived CRSP/CBOE/FRB daily features.
- Final strategy features: Tier 1 macro features only.

## Tier 1 macro features

| Feature | Name | Selected rule | Economic rationale | Interpretation note |
|---|---|---|---|---|
| equity_realized_vol_21d | 21-day equity realized volatility | value >= development threshold | Equity realized volatility proxies cross-asset risk stress and the price of bearing risk. For crypto, it can matter because BTC/ETH often behave as high-beta liquidity assets. | The selected empirical gate treats higher values as favourable. This is not the usual defensive interpretation; it likely captures post-stress rebound or elevated risk-premium conditions and should be monitored carefully. |
| equity_momentum_21d | 21-day equity momentum | value >= development threshold | Positive equity momentum indicates broad risk appetite, easier financing conditions, and better demand for high-beta assets. | Higher values are favourable, matching the risk-on interpretation. |
| dow_vol_level | Dow volatility level | value >= development threshold | Dow volatility captures stress in large-cap US equities. Crypto allocation can be sensitive to this because institutional risk budgets often adjust across risky assets together. | The selected empirical gate treats higher values as favourable. This is potentially counterintuitive and may reflect risk-premium/rebound timing rather than a stable causal effect. |
| vix_level | VIX level | value >= development threshold | VIX measures expected US equity volatility and is a common global risk-aversion proxy. It affects crypto through deleveraging, liquidity demand, and broad risk appetite. | The selected empirical gate treats higher VIX levels as favourable. This should not be read as a general claim that high VIX is always good for crypto; it may capture rebound windows when stress is elevated but no longer worsening. |
| vix_change_5d | 5-day VIX change | value <= development threshold | Short-term VIX changes capture whether risk stress is accelerating or easing. A falling/non-rising VIX is typically more supportive for crypto exposure. | Lower values are favourable, matching the stress-easing interpretation. |
| vix_change_21d | 21-day VIX change | value <= development threshold | Monthly VIX change captures persistent changes in macro risk aversion. Easing volatility over this horizon can support risk-on allocation. | Lower values are favourable, matching the medium-term stress-easing interpretation. |

## Feature activation

| Feature | Activation rate | Favourable weeks | Total weeks | Average value | Threshold |
|---|---|---|---|---|---|
| vix_change_21d | 52.31% | 204 | 390 | -0.044 | -0.180 |
| equity_momentum_21d | 49.23% | 192 | 390 | 0.008 | 0.016 |
| vix_change_5d | 44.36% | 173 | 390 | 0.238 | -0.160 |
| equity_realized_vol_21d | 43.33% | 169 | 390 | 0.154 | 0.141 |
| dow_vol_level | 41.54% | 162 | 390 | 18.776 | 17.840 |
| vix_level | 41.03% | 160 | 390 | 20.130 | 19.540 |

## Common favourable and blocking features

| Feature | Favourable weeks | Fraction weeks |
|---|---|---|
| vix_change_21d | 204 | 52.31% |
| equity_momentum_21d | 192 | 49.23% |
| vix_change_5d | 173 | 44.36% |
| equity_realized_vol_21d | 169 | 43.33% |
| dow_vol_level | 162 | 41.54% |
| vix_level | 160 | 41.03% |

| Feature | Blocking weeks | Fraction weeks |
|---|---|---|
| vix_level | 230 | 58.97% |
| dow_vol_level | 228 | 58.46% |
| equity_realized_vol_21d | 221 | 56.67% |
| vix_change_5d | 217 | 55.64% |
| equity_momentum_21d | 198 | 50.77% |
| vix_change_21d | 186 | 47.69% |

## Forward-return conditioning

Future returns below are next-7-day BTC/ETH 50/50 returns after weekly decision
dates. They are diagnostic labels only and are not used in live decision
features.

| Feature | Favourable return | Unfavourable return | Spread | Favourable exposure | Unfavourable exposure |
|---|---|---|---|---|---|
| equity_realized_vol_21d | 0.78% | 1.45% | -0.67% | 73.08% | 14.93% |
| equity_momentum_21d | 2.03% | 0.31% | 1.73% | 48.18% | 32.32% |
| dow_vol_level | 1.89% | 0.64% | 1.25% | 71.60% | 17.76% |
| vix_level | 1.71% | 0.77% | 0.95% | 72.81% | 17.39% |
| vix_change_5d | 1.21% | 1.12% | 0.09% | 58.38% | 25.58% |
| vix_change_21d | 1.46% | 0.82% | 0.64% | 52.45% | 26.61% |
