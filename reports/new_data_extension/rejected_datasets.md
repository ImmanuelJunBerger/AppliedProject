# Rejected and monitoring-only datasets

| Source | Category | Class | Reason |
|---|---|---|---|
| Exchange inflows/outflows/netflow | on-chain | future-work only | No entity-labelled exchange-flow dataset is available locally; cannot fabricate flows. |
| MVRV / realized cap / holder cohorts / whale balances / miner flows | on-chain | future-work only | No point-in-time MVRV, realized-cap, holder cohort, whale, or miner-flow history is available locally. |
| BTC/ETH ETF daily flows | ETF flows | future-work only | No locally usable point-in-time ETF flow/AUM file; public table extraction was previously blocked and WRDS mapping/reporting lag is not confirmed. |
| Deribit BTC/ETH historical volatility endpoint | options-implied | monitoring-only | Endpoint sample exists but does not cover at least 24 months before 2025-01-01. |
| Options skew / put-call / term structure / risk reversal | options-implied | future-work only | No full historical crypto option surface, skew, put/call, or term-structure dataset is available locally. |
| Liquidations | derivatives/crowding | future-work only | No liquidation dataset is available locally. |
| CME/CFTC futures positioning | institutional futures positioning | future-work only | No CME/CFTC crypto positioning file with audited reporting lag is available locally. |
