# Target diagnostics

The expansion targets were predeclared and use 30-day forward outcomes only as
supervised labels, never as signal-time features.

| Target | Description | Split | Obs | Events | Prevalence |
|---|---|---|---|---|---|
| btc_30d_gt_15 | BTC 30-day forward return > +15% | development | 261 | 74 | 28.35% |
| btc_30d_gt_15 | BTC 30-day forward return > +15% | holdout | 73 | 5 | 6.85% |
| eth_30d_gt_20 | ETH 30-day forward return > +20% | development | 261 | 73 | 27.97% |
| eth_30d_gt_20 | ETH 30-day forward return > +20% | holdout | 73 | 11 | 15.07% |
| btc_eth_50_50_30d_gt_15 | 50/50 BTC/ETH 30-day forward return > +15% | development | 261 | 82 | 31.42% |
| btc_eth_50_50_30d_gt_15 | 50/50 BTC/ETH 30-day forward return > +15% | holdout | 73 | 10 | 13.70% |
| top10_30d_gt_20 | Top-10 crypto basket 30-day forward return > +20% | development | 261 | 68 | 26.05% |
| top10_30d_gt_20 | Top-10 crypto basket 30-day forward return > +20% | holdout | 73 | 5 | 6.85% |
| eth_leads_btc_30d_gt_5 | ETH outperforms BTC over the next 30 days by at least +5% | development | 261 | 85 | 32.57% |
| eth_leads_btc_30d_gt_5 | ETH outperforms BTC over the next 30 days by at least +5% | holdout | 73 | 16 | 21.92% |
