# Public crypto-native feature plan

All features must be lagged before trading decisions. The first use case is
risk timing for BTC/ETH/cash, not broad altcoin selection.

| Feature family | Source | Example features | Rationale | Leakage control |
|---|---|---|---|---|
| Stablecoin liquidity | DefiLlama stablecoincharts/all | aggregate supply, 7/30/90-day supply change, supply z-score | Stablecoin expansion can proxy crypto-native liquidity and collateral availability. | Use previous day's published aggregate value; no same-day rebalance value. |
| DeFi liquidity | DefiLlama chain/protocol TVL | total TVL trend, Ethereum/Solana/Tron TVL change, protocol category TVL | TVL contraction can identify liquidity withdrawal and risk-off conditions. | Lag daily TVL; avoid current protocol snapshots in historical tests unless snapshotted. |
| Coin market structure | CoinGecko markets/global | BTC/ETH dominance, market cap, circulating supply, volume | Dominance and capitalization can identify concentration and speculative regime. | Historical features need market_chart/range or prospective snapshots; current categories are not point-in-time. |
| Categories/sectors | CoinGecko categories | sector market-cap/volume share, category momentum | Helps design sector/breadth hypotheses after point-in-time snapshots exist. | Do not backfill today's categories into prior dates. |
| Token unlock pressure | External unlock source or local file | unlock size / market cap, days to unlock, emission pressure | Supply overhang can impair altcoin momentum and risk appetite. | Requires timestamped, point-in-time unlock calendar; unavailable data is not imputed. |
| 4h BTC/ETH state | Binance spot klines | 4h trend, realized volatility, drawdown, volume shock | Intraday risk state can detect deterioration before weekly rebalance. | Aggregate to daily and shift one day before weekly/biweekly allocation. |

Recommended first engineered features:

1. `stablecoin_supply_change_30d` and `stablecoin_supply_change_90d`.
2. Stablecoin expansion dummy: change greater than zero.
3. Total DeFi TVL 30/90-day change.
4. BTC/ETH 4h 7-day trend confirmation.
5. BTC/ETH 4h 30-day drawdown.
6. BTC/ETH 4h volume shock.
7. BTC/ETH dominance proxy from CoinGecko global snapshots once a history is built.
