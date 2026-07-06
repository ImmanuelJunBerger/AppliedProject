# Data inventory

This inventory covers local files, prior API checks, free/public endpoints, and previously configured WRDS-derived files. Unavailable data is not fabricated.

| Source | Category | Available | Access | Start | End | Frequency | Assets | PIT safe | Usable | Class | Reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Blockchain.com BTC active addresses | on-chain | Yes | local processed public Blockchain.com chart | 2009-01-03 | 2026-06-24 | irregular daily chart samples | BTC | Yes | Yes | accepted |  |
| Blockchain.com BTC transaction count | on-chain | Yes | local processed public Blockchain.com chart | 2009-01-17 | 2026-06-24 | irregular daily chart samples | BTC | Yes | Yes | accepted |  |
| Exchange inflows/outflows/netflow | on-chain | No | not available locally; usually requires entity-labelled on-chain provider |  |  | daily if licensed | BTC/ETH | No | No | future-work only | No entity-labelled exchange-flow dataset is available locally; cannot fabricate flows. |
| MVRV / realized cap / holder cohorts / whale balances / miner flows | on-chain | No | not available locally; Coin Metrics/Glassnode-style data required |  |  | daily if licensed | BTC/ETH | No | No | future-work only | No point-in-time MVRV, realized-cap, holder cohort, whale, or miner-flow history is available locally. |
| BTC/ETH ETF daily flows | ETF flows | No | prior public Farside-style extraction was blocked/unstructured; WRDS ETF mapping not audited |  |  | daily if available | BTC/ETH ETFs | No | No | future-work only | No locally usable point-in-time ETF flow/AUM file; public table extraction was previously blocked and WRDS mapping/reporting lag is not confirmed. |
| Deribit BTC/ETH historical volatility endpoint | options-implied | Yes | local processed Deribit public endpoint sample | 2026-06-10 | 2026-06-26 | daily/intraday sample | BTC/ETH | Yes | No | monitoring-only | Endpoint sample exists but does not cover at least 24 months before 2025-01-01. |
| Options skew / put-call / term structure / risk reversal | options-implied | No | not available locally; full options surface required |  |  | daily/intraday if licensed | BTC/ETH | No | No | future-work only | No full historical crypto option surface, skew, put/call, or term-structure dataset is available locally. |
| Binance futures derivatives/crowding | derivatives/crowding | Yes | local processed Binance futures public endpoints | 2019-09-10 | 2026-06-22 | daily | BTC/ETH and broader listed futures where available | Yes | Yes | accepted |  |
| Liquidations | derivatives/crowding | No | not available locally |  |  | intraday/daily if provider available | BTC/ETH | No | No | future-work only | No liquidation dataset is available locally. |
| CME/CFTC futures positioning | institutional futures positioning | No | not available locally; CFTC/CME mapping needed |  |  | weekly | BTC/ETH futures if mapped | No | No | future-work only | No CME/CFTC crypto positioning file with audited reporting lag is available locally. |
| WRDS macro/vintage risk variables | macro/vintage | Yes | local processed WRDS/FRED/market macro file | 2019-01-01 | 2026-06-22 | daily/monthly variables forward-filled to daily | macro | Yes | Yes | accepted |  |
