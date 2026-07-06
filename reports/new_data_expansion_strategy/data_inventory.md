# Data inventory

The module checked WRDS inventory artifacts and small public sources for ETF
flows, on-chain activity, and options-implied indicators. No unavailable source
was fabricated or proxied into a model.

| Family | Source | Status | Start | End | Obs | Frequency | PIT usable | Notes |
|---|---|---|---|---|---|---|---|---|
| on-chain | Blockchain.com btc transaction count | downloaded | 2009-01-17 | 2026-06-24 | 1592 | irregular/daily chart samples | Yes | Usable as BTC-only public on-chain activity proxy; not entity-adjusted and not exchange-flow data. |
| on-chain | Blockchain.com btc active addresses | downloaded | 2009-01-03 | 2026-06-24 | 1589 | irregular/daily chart samples | Yes | Usable as BTC-only public on-chain activity proxy; not entity-adjusted and not exchange-flow data. |
| options-implied | Deribit BTC historical volatility endpoint | downloaded_short_history | 2026-06-10 | 2026-06-26 | 17 | intraday endpoint aggregated to daily | No | Endpoint is reachable but does not provide enough 2019-2026 history for this study; no options feature enters the model. |
| options-implied | Deribit ETH historical volatility endpoint | downloaded_short_history | 2026-06-10 | 2026-06-26 | 17 | intraday endpoint aggregated to daily | No | Endpoint is reachable but does not provide enough 2019-2026 history for this study; no options feature enters the model. |
| ETF flows | WRDS ETF/fund-flow tables | potential_wrds_matches_found |  |  | 118 | unknown from inventory | No | Potential institutional-flow source, but BTC/ETH ETF identifier mapping and reporting lag are not confirmed. Matched 118 candidate table(s); no large WRDS dataset downloaded in this module. |
| options-implied | WRDS OptionMetrics/CBOE tables | potential_wrds_tables_found | date: 1996-01-04 to 1996-12-31 | date: 1996-01-04 to 1996-12-31 | 154 | daily/date-stamped likely | No | Useful for equity/index option risk proxies; prior inventory did not identify complete crypto options surfaces. Matched 154 table(s); no large WRDS dataset downloaded in this module. |
| news/sentiment | WRDS RavenPack/news tables | potential_wrds_matches_found |  |  | 341 | unknown from inventory | No | Potential sentiment source if licensed; high-dimensional and timestamp-sensitive, not downloaded here. Matched 341 candidate table(s); no large WRDS dataset downloaded in this module. |
| ETF flows | Farside Bitcoin ETF flow table | not_downloaded_structured_table_unavailable |  |  | 0 | daily if accessible | No | Public page was identified, but structured table extraction returned HTTP 403 in this environment; no ETF-flow data was used. |
| ETF flows | Farside Ethereum ETF flow table | not_downloaded_structured_table_unavailable |  |  | 0 | daily if accessible | No | Public page was identified, but structured table extraction returned HTTP 403 in this environment; no ETF-flow data was used. |
| on-chain | Coin Metrics community asset metrics API | unavailable |  |  | 0 | unknown | No | Potential source for active addresses, transaction count, realized cap, and MVRV; access was blocked/unauthenticated in this environment. Access check failed: HTTPError: HTTP Error 400: Bad Request |
