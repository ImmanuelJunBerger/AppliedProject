# Results summary

Project: **Crypto Expansion-State Detection for Systematic Allocation**

The frozen baseline remains **btc_eth_macro_gate_balanced**. This module did not modify or
reselect it.

## Protocol

- Development period: 2020-01-01 to 2024-12-31
- Locked holdout: 2025-01-01 to 2026-06-22
- Selection rule: Prediction and overlay selection use development-only CPCV. Holdout is reported after selection only.
- Tested configurations: 61 total (25 prediction, 36 overlay)

## Development-selected models

- Expansion model: **btc_30d_gt_15__random_forest**
- ETH leadership model: **eth_leads_btc_30d_gt_5__elastic_net_logistic**
- Overlay selected by development-only CPCV: **expansion_filter_t60_14d**

## Holdout comparison at 25 bps

| Strategy | Sharpe | CAGR | Max DD | Turnover | Exposure |
|---|---:|---:|---:|---:|---:|
| Frozen btc_eth_macro_gate_balanced | 0.970 | 25.07% | -18.42% | 10.177 | 28.95% |
| Selected expansion overlay | 0.894 | 5.65% | -5.16% | 2.035 | 4.55% |

Final conclusion: **expansion-state model is useful as diagnostics only because selected exposure is trivially low**.
