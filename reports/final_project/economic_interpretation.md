# Economic interpretation

The strategy uses macro variables to decide whether the market environment is
favourable enough to hold BTC/ETH exposure. It does not directly predict
individual coin returns.

## Feature-level interpretation

| Feature | Selected rule | Economic rationale | Orientation caveat |
|---|---|---|---|
| equity_realized_vol_21d | value >= development threshold | Equity realized volatility proxies cross-asset risk stress and the price of bearing risk. For crypto, it can matter because BTC/ETH often behave as high-beta liquidity assets. | The selected empirical gate treats higher values as favourable. This is not the usual defensive interpretation; it likely captures post-stress rebound or elevated risk-premium conditions and should be monitored carefully. |
| equity_momentum_21d | value >= development threshold | Positive equity momentum indicates broad risk appetite, easier financing conditions, and better demand for high-beta assets. | Higher values are favourable, matching the risk-on interpretation. |
| dow_vol_level | value >= development threshold | Dow volatility captures stress in large-cap US equities. Crypto allocation can be sensitive to this because institutional risk budgets often adjust across risky assets together. | The selected empirical gate treats higher values as favourable. This is potentially counterintuitive and may reflect risk-premium/rebound timing rather than a stable causal effect. |
| vix_level | value >= development threshold | VIX measures expected US equity volatility and is a common global risk-aversion proxy. It affects crypto through deleveraging, liquidity demand, and broad risk appetite. | The selected empirical gate treats higher VIX levels as favourable. This should not be read as a general claim that high VIX is always good for crypto; it may capture rebound windows when stress is elevated but no longer worsening. |
| vix_change_5d | value <= development threshold | Short-term VIX changes capture whether risk stress is accelerating or easing. A falling/non-rising VIX is typically more supportive for crypto exposure. | Lower values are favourable, matching the stress-easing interpretation. |
| vix_change_21d | value <= development threshold | Monthly VIX change captures persistent changes in macro risk aversion. Easing volatility over this horizon can support risk-on allocation. | Lower values are favourable, matching the medium-term stress-easing interpretation. |

## Favourable vs unfavourable future crypto returns

The table uses next-7-day BTC/ETH 50/50 returns after weekly decision dates.
These returns are diagnostic only.

| Feature | Favourable frequency | Favourable return | Unfavourable return | Spread | Favourable exposure | Unfavourable exposure |
|---|---|---|---|---|---|---|
| equity_realized_vol_21d | 43.33% | 0.78% | 1.45% | -0.67% | 73.08% | 14.93% |
| equity_momentum_21d | 49.23% | 2.03% | 0.31% | 1.73% | 48.18% | 32.32% |
| dow_vol_level | 41.54% | 1.89% | 0.64% | 1.25% | 71.60% | 17.76% |
| vix_level | 41.03% | 1.71% | 0.77% | 0.95% | 72.81% | 17.39% |
| vix_change_5d | 44.36% | 1.21% | 1.12% | 0.09% | 58.38% | 25.58% |
| vix_change_21d | 52.31% | 1.46% | 0.82% | 0.64% | 52.45% | 26.61% |

## Cash/BTC/ETH allocation contribution

| Feature | State | Weeks | Frequency | BTC weight | ETH weight | Cash weight | Exposure | Exposure contribution |
|---|---|---|---|---|---|---|---|---|
| dow_vol_level | unfavourable | 228 | 58.46% | 8.88% | 8.88% | 82.24% | 17.76% | 10.38% |
| dow_vol_level | favourable | 162 | 41.54% | 35.80% | 35.80% | 28.40% | 71.60% | 29.74% |
| equity_momentum_21d | unfavourable | 198 | 50.77% | 16.16% | 16.16% | 67.68% | 32.32% | 16.41% |
| equity_momentum_21d | favourable | 192 | 49.23% | 24.09% | 24.09% | 51.82% | 48.18% | 23.72% |
| equity_realized_vol_21d | unfavourable | 221 | 56.67% | 7.47% | 7.47% | 85.07% | 14.93% | 8.46% |
| equity_realized_vol_21d | favourable | 169 | 43.33% | 36.54% | 36.54% | 26.92% | 73.08% | 31.67% |
| vix_change_21d | unfavourable | 186 | 47.69% | 13.31% | 13.31% | 73.39% | 26.61% | 12.69% |
| vix_change_21d | favourable | 204 | 52.31% | 26.23% | 26.23% | 47.55% | 52.45% | 27.44% |
| vix_change_5d | unfavourable | 217 | 55.64% | 12.79% | 12.79% | 74.42% | 25.58% | 14.23% |
| vix_change_5d | favourable | 173 | 44.36% | 29.19% | 29.19% | 41.62% | 58.38% | 25.90% |
| vix_level | unfavourable | 230 | 58.97% | 8.70% | 8.70% | 82.61% | 17.39% | 10.26% |
| vix_level | favourable | 160 | 41.03% | 36.41% | 36.41% | 27.19% | 72.81% | 29.87% |

## Risk-on/risk-off frequency and forward returns

| Regime | Weeks | Frequency | Forward BTC/ETH 7d | Hit rate | BTC weight | ETH weight | Cash weight | Exposure |
|---|---|---|---|---|---|---|---|---|
| neutral | 92 | 23.59% | 1.49% | 57.61% | 24.18% | 24.18% | 51.63% | 48.37% |
| risk_off | 183 | 46.92% | 0.71% | 50.27% | 0.00% | 0.00% | 100.00% | 0.00% |
| risk_on | 115 | 29.49% | 1.61% | 54.78% | 48.70% | 48.70% | 2.61% | 97.39% |

## Interpretation caveat

Positive equity momentum and falling VIX changes have clear risk-on
interpretations. Higher VIX level and higher Dow volatility level are more
empirical. They should be interpreted as conditional rebound/risk-premium
signals, not as a universal claim that high volatility is good for crypto.
