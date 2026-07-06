# Binance Futures microstructure data coverage

The study probes public Binance Futures endpoints but does not assume full
one-second/order-book history is available.

| Endpoint | Status | Obs | Historical depth | Usable holdout | Limitation |
|---|---|---|---|---|---|
| depth_snapshot | available | 1 | current_snapshot | No | Current order-book snapshot only; not historical through REST. |
| book_ticker | available | 1 | current_snapshot | No | Current top-of-book only; not historical through REST. |
| recent_agg_trades | available | 20 | recent_or_query_limited | No | Useful for prospective collection; full historical backtest requires archived/backfilled data. |
| historical_agg_trades_2025_sample | empty_response | 0 | one_hour_query_sample | No | Even if sample is available, full 2025+ holdout across assets requires large systematic backfill. |
| historical_1m_klines_2025_sample | available | 20 | one_hour_query_sample | No | 1m klines provide high-frequency OHLCV, not book/trade-flow microstructure. |
| taker_long_short_ratio | available | 20 | recent_public_ratio | No | Ratio endpoint is useful context but not sufficient order-book/trade-flow history. |

## Coverage decision

No complete local historical Binance Futures order-book/trade-flow feature panel covering the locked holdout. The module therefore does not run microstructure-confirmed overlays B/C/D as final backtests.

## Prospective collection path

For a valid future test, collect and store timestamped data prospectively:

- `bookTicker` or depth snapshots every 1-5 seconds for BTCUSDT/ETHUSDT and selected top futures symbols.
- `aggTrades` continuously for taker buy/sell imbalance and trade-count imbalance.
- 1m futures klines for deployable 1h/4h volatility and volume concentration features.
- Aggregate raw data to immutable 1h and 4h feature tables before strategy testing.
- Lock thresholds using only the collection development window; keep a future untouched paper holdout.
