# Public crypto-native data inventory

WRDS is excluded from this module. Public data is used only when fetched from
unauthenticated public endpoints or supplied as a local file. Missing public
token-unlock data is reported as unavailable; no synthetic unlock series is
created.

## Endpoint coverage

| Dataset | Source | Status | Start | End | N | Strategy usable | Limitation |
|---|---|---|---|---|---|---|---|
| stablecoin_supply | DefiLlama stablecoincharts/all | available | 2017-11-29 | 2026-06-24 | 3130 | Yes | Free public endpoint; aggregate stablecoin supply only, not exchange-specific liquidity. |
| chain_tvl_all | DefiLlama historicalChainTvl | available | 2017-09-27 | 2026-06-24 | 3193 | No | Useful for feature research; not used in the first predeclared BTC/ETH/cash strategy. |
| chain_tvl_Ethereum | DefiLlama historicalChainTvl | available | 2017-09-27 | 2026-06-24 | 3193 | No | Useful for feature research; not used in the first predeclared BTC/ETH/cash strategy. |
| chain_tvl_Solana | DefiLlama historicalChainTvl | available | 2021-03-17 | 2026-06-24 | 1926 | No | Useful for feature research; not used in the first predeclared BTC/ETH/cash strategy. |
| chain_tvl_Tron | DefiLlama historicalChainTvl | available | 2020-04-03 | 2026-06-24 | 2274 | No | Useful for feature research; not used in the first predeclared BTC/ETH/cash strategy. |
| chain_tvl_Arbitrum | DefiLlama historicalChainTvl | available | 2021-06-04 | 2026-06-24 | 1786 | No | Useful for feature research; not used in the first predeclared BTC/ETH/cash strategy. |
| chain_tvl_Base | DefiLlama historicalChainTvl | available | 2023-06-15 | 2026-06-24 | 1106 | No | Useful for feature research; not used in the first predeclared BTC/ETH/cash strategy. |
| protocol_tvl_current | DefiLlama protocols | available | N/A | N/A | 7702 | No | Current protocol metadata only in this module; not sufficient alone for locked historical trading. |
| global_market_snapshot | CoinGecko /global | available | 2026-06-24 | 2026-06-24 | 1 | No | Current snapshot only; useful for dominance proxy documentation, not historical strategy selection. |
| coin_market_cap_supply_volume | CoinGecko /coins/markets | available | 2026-06-24 | 2026-06-24 | 250 | No | Current top-250 snapshot; not point-in-time enough for historical top-universe backtests. |
| coin_categories | CoinGecko /coins/categories | available | 2026-06-24 | 2026-06-24 | 728 | No | Current category/sector snapshot; historical category membership needs vendor support or frozen snapshots. |
| BTC_market_cap_volume_history | CoinGecko market_chart/range | failed: request failed: https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range?vs_currency=usd&from=1546300800&to=1782086400: HTTP Error 429: Too Many Requests | N/A | N/A | 0 | No | N/A |
| ETH_market_cap_volume_history | CoinGecko market_chart/range | failed: request failed: https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range?vs_currency=usd&from=1546300800&to=1782086400: HTTP Error 429: Too Many Requests | N/A | N/A | 0 | No | N/A |
| BTCUSDT_4h_ohlcv | Binance spot klines 4h | available | 2019-01-01 | 2026-06-22 | 16370 | Yes | Exchange-specific public 4h spot bars; no order book or cross-exchange aggregation. |
| ETHUSDT_4h_ohlcv | Binance spot klines 4h | available | 2019-01-01 | 2026-06-22 | 16370 | Yes | Exchange-specific public 4h spot bars; no order book or cross-exchange aggregation. |
| token_unlocks | Token unlock public APIs | unavailable | N/A | N/A | 0 | No | No reliable unauthenticated official/public endpoint was integrated; no synthetic unlock data created. |

## Source-specific interpretation

- **CoinGecko:** supports market cap, supply, volume, category, and global market
  snapshots. Current category membership is useful for research design, but
  historical category membership should be snapshotted prospectively before
  use in point-in-time backtests.
- **DefiLlama:** stablecoin aggregate supply and chain TVL are accessible and
  directly relevant for crypto liquidity/risk-regime features.
- **Token unlocks:** no reliable unauthenticated public endpoint was integrated.
  Use a licensed source or manually versioned file before testing unlock-driven
  hypotheses.
- **Binance 4h:** BTC/ETH 4h spot bars are accessible and converted into lagged
  daily trend, volatility, drawdown, and volume-shock features.

## Files written

- `data/processed/public_crypto/coverage.csv`
- `data/processed/public_crypto/defillama_stablecoin_daily.csv`
- `data/processed/public_crypto/defillama_chain_tvl_daily.csv`
- `data/processed/public_crypto/defillama_protocols_current.csv`
- `data/processed/public_crypto/coingecko_markets_current.csv`
- `data/processed/public_crypto/coingecko_categories_current.csv`
- `data/processed/public_crypto/coingecko_coin_market_daily.csv`
- `data/processed/public_crypto/binance_btc_eth_4h_ohlcv.csv`
- `data/processed/public_crypto/binance_btc_eth_4h_daily_features.csv`
