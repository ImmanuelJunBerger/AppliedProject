# Study 3: Regime-dependent BTC vs ETH allocation

## Development-only selection

| Candidate | Family | Selection score | Median fold Sharpe | Worst fold | Positive folds | Dev Sharpe | Dev turnover |
|---|---|---|---|---|---|---|---|
| asset_btc_uncertain_eth_strong | Regime-dependent BTC vs ETH allocation | 0.421 | 0.974 | -1.641 | 73.33% | 0.687 | 22.184 |
| asset_conservative_btc | Regime-dependent BTC vs ETH allocation | 0.399 | 0.947 | -1.647 | 73.33% | 0.800 | 22.061 |
| asset_eth_when_low_vol | Regime-dependent BTC vs ETH allocation | 0.280 | 0.998 | -1.675 | 73.33% | 0.847 | 25.320 |
| asset_speculative_eth | Regime-dependent BTC vs ETH allocation | 0.238 | 0.955 | -1.644 | 73.33% | 0.737 | 25.448 |

Selected by development-only CPCV: **asset_btc_uncertain_eth_strong**.

## Development vs holdout

| Candidate | Dev Sharpe | Holdout Sharpe | Sharpe retention | Dev CAGR | Holdout CAGR | CAGR retention | Dev max DD | Holdout max DD | Holdout turnover | Holdout exposure |
|---|---|---|---|---|---|---|---|---|---|---|
| asset_speculative_eth | 0.737 | -0.514 | -69.78% | 27.33% | -26.67% | -97.57% | -78.93% | -59.10% | 25.781 | 80.81% |
| asset_conservative_btc | 0.800 | -0.570 | -71.28% | 31.45% | -27.77% | -88.31% | -79.55% | -59.41% | 25.060 | 81.35% |
| asset_eth_when_low_vol | 0.847 | -0.360 | -42.48% | 35.19% | -22.80% | -64.79% | -79.60% | -61.31% | 27.774 | 81.07% |
| asset_btc_uncertain_eth_strong | 0.687 | -0.856 | -124.57% | 24.03% | -33.61% | -139.88% | -78.39% | -57.42% | 19.949 | 80.61% |

## Statistical validation

- PBO: 22.86%
- Deflated Sharpe probability for selected candidate: 1.81%
- Worst CPCV fold: -1.641
- Positive CPCV folds: 73.33%

## Frozen benchmark comparison

- Frozen holdout Sharpe: 0.970
- Frozen holdout CAGR: 25.07%
- Frozen holdout max drawdown: -18.42%
- Selected candidate holdout Sharpe: -0.856
- Selected candidate holdout CAGR: -33.61%
- Selected candidate holdout max drawdown: -57.42%

## Interpretation

Status: **failed_holdout**.

Candidate improves or ranks well in development but fails locked holdout economics.

Feature drivers: lagged macro Tier 1 features.

### Economic interpretation and decision mechanics

The strategy holds cash in macro risk-off states, BTC in uncertain or moderate states, 50/50 BTC/ETH in ordinary risk-on states, and ETH only in the strongest speculative macro states. The economic premise is that ETH should be favoured only when macro risk appetite is unusually strong.

The selected candidate's holdout CAGR is below the frozen benchmark. Even when Sharpe or drawdown improves, it should be treated as a conservative overlay for paper monitoring rather than a replacement.
