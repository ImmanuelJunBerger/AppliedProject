# Validation results

Selection was performed using development-period CPCV only. Holdout was opened only after candidate selection.

## Selected candidate cost sensitivity

| Candidate | Cost bps | CAGR | Sharpe | Sortino | Calmar | Max DD | Annual turnover | Exposure | Worst month | Hit rate | Avg win | Avg loss | Time BTC | Time ETH | Time cash |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vol_compression_breakout_score | 10 | -16.47% | -0.256 | -0.268 | -0.318 | -51.73% | 13.297 | 50.93% | -0.159 | 0.290 | 0.018 | -0.017 | 59.29% | 59.29% | 40.71% |
| vol_compression_breakout_score | 25 | -18.12% | -0.307 | -0.322 | -0.347 | -52.23% | 13.297 | 50.93% | -0.161 | 0.288 | 0.018 | -0.017 | 59.29% | 59.29% | 40.71% |
| vol_compression_breakout_score | 50 | -20.79% | -0.391 | -0.412 | -0.392 | -53.07% | 13.297 | 50.93% | -0.165 | 0.288 | 0.018 | -0.017 | 59.29% | 59.29% | 40.71% |
| vol_compression_breakout_score | 100 | -25.88% | -0.560 | -0.593 | -0.473 | -54.70% | 13.297 | 50.93% | -0.172 | 0.284 | 0.018 | -0.018 | 59.29% | 59.29% | 40.71% |

## Rejected candidates

| Candidate | Family | Rejection reason |
|---|---|---|
| vol_compression_breakout_score | Family C: Volatility Compression Breakout | Selected by development CPCV but failed replacement filters. |
| agentic_three_signal_ensemble | Family G: Agentic Deterministic Ensemble | Not selected by development CPCV; documented as rejected candidate. |
| macro_liquidity_expansion_score | Family A: Macro + Liquidity Expansion | Not selected by development CPCV; documented as rejected candidate. |
| capitulation_rebound_score | Family B: Capitulation-Rebound Strategy | Not selected by development CPCV; documented as rejected candidate. Exposure below 20%. |
| eth_btc_leadership_rotation | Family D: ETH/BTC Leadership Rotation | Not selected by development CPCV; documented as rejected candidate. |
| macro_gated_expansion_rebound | Family F: Macro-Gated Expansion Rebound | Not selected by development CPCV; documented as rejected candidate. |
| trend_scanning_confirmation | Family E: Trend-Scanning Meta Strategy | Not selected by development CPCV; documented as rejected candidate. Exposure below 20%. |
