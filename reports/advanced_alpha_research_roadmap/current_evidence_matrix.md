# Current evidence matrix

This table answers the required final-output questions for datasets/models
already tested in the project.

| Item | Type | New information | Statistically significant? | Economically meaningful? | Survives holdout? | Improves frozen strategy? | Complexity justified? | Decision |
|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | frozen benchmark strategy | Tier-1 macro regime features. | Moderate; PBO and DSR concerns remain. | Yes: holdout Sharpe about 0.97, CAGR about 25%, max DD about -18%. | Yes, as paper-monitoring candidate. | N/A benchmark. | Yes for paper monitoring; not proven live alpha. | Keep frozen. |
| New public ETF/on-chain/options data | new data source test | Public BTC on-chain activity proxies; inventory of ETF/options/on-chain sources. | No Tier-1 features; 3 Tier-2 features only. | Not tested because feature gate failed. | Holdout diagnostic only; no accepted feature. | No strategy run. | No, until licensed/structured data is added. | New data does not yet provide enough independently validated Tier-1 upside features to justify a strategy test. |
| Expansion Tier-1 overlay | crypto-native expansion overlay | Previously validated expansion features. | Not enough: PBO high and DSR low. | No: selected overlay underperformed frozen holdout Sharpe/CAGR. | No replacement evidence. | No. | No. | Expansion Tier-1 overlay does not improve the frozen strategy economically. |
| Simplified macro gates | simplification/model-risk test | No new data; simpler macro variants. | Development-selected simplified candidate failed holdout. | No replacement evidence. | No. | No. | Keep current frozen strategy instead. | keep current strategy |
