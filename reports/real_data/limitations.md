# Real-data limitations

- ccxt returns Binance's current market catalogue. Markets that were fully delisted and removed cannot be reconstructed, so survivorship bias remains despite point-in-time monthly ranking.
- Binance began trading in 2017, but the requested consistent panel starts in 2019 and most assets list later. Full rectangular-panel missingness is 53.73%; within-listing-span missingness is 0.09%.
- Coinbase is supported as a fallback downloader, but histories are not automatically spliced across venues because doing so would mix liquidity, prices, fees, and listing rules.
- OHLCV supplies exchange turnover, not true circulating market capitalization. Universes are therefore ranked by lagged dollar turnover, not market cap.
- High/low daily bars do not reveal intraday ordering when both barriers are touched. The implementation conservatively assigns stop-loss first.
- Backtests do not model spread, market impact, order-book depth, taxes, funding, or exchange outages. Costs are linear sensitivity assumptions, not execution guarantees.
- Feature importance is mean absolute standardized logistic-regression coefficient, not causal importance.
- Multiple robustness comparisons increase selection risk. Results should be validated on another venue and a later untouched holdout before deployment.
