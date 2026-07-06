# Data inventory for market-structure forecasting

## Reading this inventory

Provider capabilities and plans were reviewed on 22 June 2026. “Coverage” below is a research expectation, not a contractual guarantee. Exchange APIs commonly expose only the life of a listed instrument, may omit delisted markets, and may impose endpoint-specific lookback limits. Vendor history, asset support, point-in-time behavior, redistribution rights, and prices must be confirmed with pilot API calls and a written quote before engineering.

Cost labels are deliberately qualitative:

- **Free:** public endpoint, subject to rate limits.
- **Freemium:** useful public/community subset; serious coverage or rate limits require a plan.
- **Paid:** subscription or enterprise quote likely required for research-grade history.

Ease rates the work needed to form a clean, point-in-time panel—not how easy it is to download one response.

## Price and reference-market data

| Dataset | Primary source(s) | Cost | API | Expected history | Ease | Important limitations |
|---|---|---|---|---|---|---|
| Spot OHLCV | [Binance market-data endpoints](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints), [Coinbase candles](https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles) | Free | REST | From each venue/instrument listing while retained | High | Venue-specific; Coinbase documents a maximum of 300 candles per request and says historical rates may be incomplete. Delistings and symbol changes require a security master. |
| Aggregated OHLCV / market cap | [CoinGecko historical range](https://docs.coingecko.com/reference/coins-id-market-chart-range) | Freemium | REST | Asset-dependent; range endpoint provides automatic granularity | High | Aggregation methodology, asset mapping and plan limits; market cap is not liquidity. |
| Trades, quotes and candles across venues | [Coin Metrics Market Data Feed](https://docs.coinmetrics.io/market-data/market-data-overview), [Amberdata](https://docs.amberdata.io/) | Paid / some community access | REST, files, streams depending on provider | Provider and venue dependent; potentially deep institutional history | Medium | Licensing cost, large volumes, venue normalization and data revisions. |
| Volume | Same exchange feeds; CoinGecko for aggregates | Free to paid | REST/files | Listing-dependent | High | Wash trading, quote currency conversion, venue fragmentation, and changing venue share. |
| Turnover | Derived from volume and lagged market cap/free float | Derived | N/A | Limited by clean supply/market-cap history | Medium | Reported supply can include locked, treasury, bridged or inaccessible tokens. |
| Security master / listings | Coin Metrics reference data, CoinGecko IDs, exchange metadata | Freemium/paid | REST/files | Provider dependent | Medium | Essential for renames, redenominations, migrations, wrapped assets and delistings. |

## Derivatives data

| Dataset | Primary source(s) | Cost | API | Expected history | Ease | Important limitations |
|---|---|---|---|---|---|---|
| Perpetual funding rates | [Binance funding history](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History), [Bybit funding history](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate), Coin Metrics MDF | Direct feeds free; normalized multi-venue history paid | REST/files | Contract/listing-dependent; pagination required | High direct / medium normalized | Funding schedules and formulas differ by venue and changed over time. Use timestamped realized funding, not a vendor’s later reconstruction. |
| Open interest | [Binance OI statistics](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics), [Bybit OI](https://bybit-exchange.github.io/docs/v5/market/open-interest), Coin Metrics MDF | Direct free; deep normalized history paid | REST/files | Direct endpoints can have short retained history; Binance documents the latest one month on its statistics endpoint | Medium | Units differ (contracts, coins, USD); contract multipliers and price changes must be normalized. Archive prospectively. |
| Futures/perpetual basis | Derive from spot and contract prices; Coin Metrics, Amberdata | Free direct to paid normalized | REST/files | Instrument-dependent | Medium | Requires time-aligned spot reference, maturity rolls, venue and collateral controls. |
| Liquidations | [CoinGlass API](https://docs.coinglass.com/reference/getting-started-with-your-api), Coin Metrics MDF, Amberdata; exchange streams for prospective capture | Mostly paid for useful history | REST/files/streams | Often materially shorter and less consistent than price history | Low–medium | Exchange definitions and aggregation differ; websocket capture is not retroactive; missing venues bias totals. |
| Options IV, skew, term structure and Greeks | [Deribit API](https://docs.deribit.com/#public-get_historical_volatility), Coin Metrics MDF, Amberdata | Public snapshots/direct endpoints; full history paid | REST/streams/files | Mainly BTC/ETH; depth depends on instrument and vendor | Medium–low | Sparse altcoin options, changing strikes/maturities, stale quotes, and survivorship across expired instruments. Build constant-maturity surfaces. |
| Order books / spreads / depth | Exchange streams; Coin Metrics MDF; Amberdata | Live direct free; historical depth paid and storage-heavy | WebSocket/files | High-quality history generally vendor-specific | Low | Sequence gaps, venue outages, symbol mapping, enormous volume, and no common depth definition. |

## On-chain and stablecoin data

| Dataset | Primary source(s) | Cost | API | Expected history | Ease | Important limitations |
|---|---|---|---|---|---|---|
| Active addresses / transaction count / fees | [Coin Metrics Network Data](https://docs.coinmetrics.io/network-data/network-data-overview), [Glassnode API](https://docs.glassnode.com/basic-api/api-key), [Santiment SanAPI](https://academy.santiment.net/sanapi/) | Community subset to paid | REST/files | Genesis or metric inception for supported chains | Medium | Address ≠ user; chain architecture, batching, bots and fee markets make cross-chain comparison nontrivial. |
| Exchange inflows/outflows/net flow | Glassnode, CryptoQuant, Coin Metrics where available, Santiment | Paid for broad labeled history | REST/files | Label- and asset-dependent, often revised as entities are discovered | Low–medium | Entity labels are backward revised; internal exchange reshuffles can resemble flows. Store observation and retrieval timestamps. |
| Whale activity | Glassnode/CryptoQuant/Santiment labels; [Etherscan](https://docs.etherscan.io/) or [Dune](https://docs.dune.com/api-reference/overview/introduction) custom queries | Freemium to paid; custom queries incur compute | REST/SQL | Chain genesis for raw transfers; labeled history depends on provider | Low | “Whale” thresholds drift with price; transfers may be custody, bridge or internal movements rather than intent. |
| Stablecoin issuance, burns and supply | Coin Metrics, Glassnode, Santiment, Dune; DefiLlama stablecoin datasets | Freemium to paid | REST/SQL/files | Contract launch onward | Medium | Separate authorized but unissued, treasury inventory, bridged supply and circulating supply. Stablecoin design and depegs are structural breaks. |
| Stablecoin exchange flows | Glassnode/CryptoQuant/Santiment; Dune custom labels | Mostly paid / query cost | REST/SQL | Label-dependent | Low | Minting is not necessarily exchange inflow or risk appetite; chain bridges and treasury moves are major confounders. |
| Realized capitalization | Coin Metrics / Glassnode | Freemium subset to paid | REST/files | Long history for BTC and selected UTXO/account chains | Medium | Methodology differs by chain; lost coins, account models and token migrations complicate interpretation. |
| MVRV | Glassnode / Coin Metrics; derive from market and realized cap | Freemium subset to paid | REST/files | Asset/methodology dependent | Medium | Sensitive to realized-cap methodology, supply definition and historical price mapping. |
| SOPR | Glassnode (documented API example), other specialist vendors | Usually plan-gated | REST/files | Mainly supported UTXO-style assets; metric-specific | Medium–low | Coin-age/entity adjustments and account-based analogues are not directly comparable. |
| Protocol TVL, fees and users | [DefiLlama API plans](https://docs.llama.fi/pro-api), Dune, Amberdata | Free endpoints plus paid/pro tiers | REST/SQL/files | Protocol deployment onward | Medium | Protocol taxonomy, double counting, incentives, bridges and contract upgrades require point-in-time mapping. |
| Raw chain events | Etherscan, Dune, self-hosted nodes/indexers | Free-tier to substantial infrastructure cost | REST/SQL/RPC | Chain genesis if fully indexed | Low | Maximum control but high engineering, decoding, reorg, archive-node and entity-label cost. |

## Derived market-structure features

| Dataset | Construction | Inputs / source | Cost | History | Ease | Controls required |
|---|---|---|---|---|---|---|
| Breadth | Share of point-in-time assets above a trend threshold; share with positive trailing return; advance/decline volume | Survivorship-free OHLCV and membership | Derived | Limited by membership history | Medium | Lag membership, minimum listing age, stale-price rules, liquidity threshold, wrapped/stablecoin exclusions. |
| Average correlation | Shrunk average pairwise correlation or first eigenvalue share | Synchronous returns | Derived | Price-history dependent | Medium | 24/7 timestamp alignment, stale assets, window length, shrinkage, missing observations. |
| Cross-sectional dispersion | Weighted standard deviation or median absolute deviation of asset returns | Returns and lagged liquidity weights | Derived | Price-history dependent | High | Point-in-time universe; cap microcap influence; both equal/liquidity weighting. |
| BTC/ETH/stablecoin dominance | Asset or category market cap divided by total eligible crypto cap | CoinGecko/Coin Metrics/reference supply data | Freemium/paid | Provider dependent | Medium | Denominator changes, missing assets, stablecoin/wrapped-asset classification, free-float ambiguity. |
| Liquidity stress | Spread, depth, Amihud, Corwin–Schultz, zero-return share | Trades/quotes/OHLCV | Free low-frequency / paid high-frequency | Source dependent | Medium | Quote conversion, venue aggregation, outliers and market outages. |
| Funding/OI breadth | Fraction of contracts with positive funding or expanding OI; funding dispersion | Multi-venue derivatives panel | Paid or self-archived | Contract-dependent | Medium | Contract multipliers, venue coverage and instrument survivorship. |
| Network connectedness | Correlation/volatility graph density, centrality, first eigenvalue | Return/volatility panel | Derived | Price-history dependent | Low–medium | Denoising, graph threshold chosen only in training, fixed universe policy, estimation uncertainty. |

## Recommended minimum viable data stack

### Tier 1 — low-cost falsification

1. Binance and Coinbase spot OHLCV/trades, with a point-in-time security master.
2. Binance and Bybit funding/OI captured and archived prospectively.
3. Deribit BTC/ETH options snapshots, converted to constant-maturity IV/skew features.
4. Derived market volatility, breadth, correlation, dispersion, dominance and low-frequency liquidity.
5. CoinGecko or a comparable reference feed for asset IDs, supply and aggregate market-cap checks.

This tier can test whether derivatives and derived market structure add value over price-only features, but it cannot recreate complete historical liquidation/order-book/on-chain panels.

### Tier 2 — research-grade historical study

- Add one normalized derivatives/microstructure vendor (Coin Metrics MDF, Amberdata, or equivalent).
- Add one on-chain entity-label provider (Glassnode, CryptoQuant, Santiment, or equivalent).
- Obtain provider documentation for metric definitions, historical revisions, timestamps and licensing.
- Overlap at least two providers for a small set of critical variables to quantify source risk.

Do not buy multiple broad feeds before Tier 1 establishes that the target and validation pipeline behave correctly.

## Data due-diligence checklist

- Record `event_time`, `provider_publish_time`, `retrieval_time`, provider version and raw response hash.
- Confirm whether history is point-in-time or recomputed using today’s entity labels.
- Preserve delisted assets and historical symbols; never reconstruct an old universe from today’s listings.
- Convert all contract units and quote currencies using contemporaneous prices.
- Predeclare maximum staleness and missing-data behavior; missingness can itself be a regime feature only if known live.
- Detect exchange outages, duplicate candles, zero prices, crossed books and chain reorganizations.
- Quantify feature availability by date and asset before choosing a modeling start date.
- Re-run a small sample against a second source; document discrepancies instead of silently overwriting them.
- Confirm research, storage, derived-data and deployment rights in the vendor agreement.

## Procurement conclusion

The first paid priority is **normalized historical derivatives and microstructure**, not a broad collection of opaque alternative metrics. Funding, OI, basis, options and liquidity have direct mechanisms for volatility and drawdown risk and faster publication than most on-chain fundamentals. Entity-labeled exchange and stablecoin flows are the second priority after their revision behavior is audited.
