# Accepted datasets

Accepted datasets satisfy the strict rules: at least 24 months before 2025-01-01, clear timestamps, realistic lagging, documented revision risk, distinct economic content, and no lookahead in weekly joins.

| Source | Category | Start | End | Frequency | Assets | Lag |
|---|---|---|---|---|---|---|
| Blockchain.com BTC active addresses | on-chain | 2009-01-03 | 2026-06-24 | irregular daily chart samples | BTC | unknown; lag by at least one day after UTC date close |
| Blockchain.com BTC transaction count | on-chain | 2009-01-17 | 2026-06-24 | irregular daily chart samples | BTC | unknown; lag by at least one day after UTC date close |
| Binance futures derivatives/crowding | derivatives/crowding | 2019-09-10 | 2026-06-22 | daily | BTC/ETH and broader listed futures where available | exchange timestamp; lagged by at least one day |
| WRDS macro/vintage risk variables | macro/vintage | 2019-01-01 | 2026-06-22 | daily/monthly variables forward-filled to daily | macro | economic releases and WRDS fields are lagged in feature engineering; revision risk documented |
