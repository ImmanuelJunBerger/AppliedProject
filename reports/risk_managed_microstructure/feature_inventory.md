# Microstructure feature inventory

| Feature | Formula | Source | Availability | Limitation |
|---|---|---|---|---|
| spread_over_mid | best_ask - best_bid divided by mid | depth/bookTicker | current only unless collected | Not valid for locked holdout without historical snapshots. |
| l1_imbalance | bid_qty - ask_qty divided by bid_qty + ask_qty | depth/bookTicker | current only unless collected | Needs synchronized book snapshots. |
| depth_imbalance | sum bid depth - sum ask depth over top levels divided by total depth | depth | current only unless collected | Sensitive to chosen depth levels and snapshot timing. |
| taker_buy_sell_imbalance | taker buy volume - taker sell volume divided by total volume | aggTrades | query/prospective | Historically backfillable only with systematic archived trade data. |
| trade_count_imbalance | buy trade count - sell trade count divided by total trade count | aggTrades | query/prospective | Requires reliable buyer-maker flag handling. |
| volume_imbalance | buy volume - sell volume divided by total volume | aggTrades | query/prospective | Same as taker imbalance when using taker-classified aggTrades. |
| buy_vwap_to_mid | taker-buy VWAP divided by mid minus one | aggTrades + book mid | prospective | Needs synchronized midquote. |
| sell_vwap_to_mid | taker-sell VWAP divided by mid minus one | aggTrades + book mid | prospective | Needs synchronized midquote. |
| net_order_flow | taker buy volume minus taker sell volume | aggTrades | query/prospective | Must be normalized by volume or volatility for cross-asset use. |
| short_horizon_volatility | 1m/5m/15m/1h realized volatility | klines/aggTrades | query/prospective | Can be built from 1m futures klines but is not book flow. |
| volume_concentration | largest trade or bar volume divided by total interval volume | aggTrades/klines | query/prospective | Trade-level version requires aggTrades. |
| aggregated_1m_5m_15m_1h_features | resample raw trades/book data into deployable bars | bookTicker/depth/aggTrades/klines | prospective | Requires raw data retention before aggregation; cannot reconstruct historical book snapshots later. |
