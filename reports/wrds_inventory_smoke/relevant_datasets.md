# WRDS datasets relevant to crypto research

WRDS is unlikely to replace exchange-native crypto data for OHLCV, funding,
open interest, liquidations, or order-book features. Its likely value here is
external market-state data: macro, rates, USD, equity, volatility, ETF flow,
news, and options-implied-risk proxies.

| Category | Candidate source | Likely libraries | Status | Matched examples | Crypto relevance | Limitation |
|---|---|---|---|---|---|---|
| crypto market data | Datastream / LSEG digital asset series, if licensed | datastream, tr_ds, ds, lseg, refinitiv | not queried | none | Potential independent BTC/ETH prices, index series, and cross-venue macro-aligned timestamps. | Coverage and identifiers depend on the institution's Datastream/LSEG license; WRDS is not usually the best source for crypto-native OHLCV. |
| Datastream / LSEG time series | Refinitiv Datastream / LSEG cross-asset time series | datastream, tr_ds, ds, lseg, refinitiv | not queried | none | Single source for broad macro/risk-regime inputs that can be lagged and merged with crypto daily bars. | Symbol mapping must be versioned; vendor revisions and holidays need explicit treatment. |
| macro variables | FRED, Federal Reserve, BEA/BLS, or Datastream macro series through WRDS | fred, frb, bea, bls, macro, datastream | not queried | none | Macro liquidity and risk-regime features: liquidity impulse, inflation/rates pressure, economic stress. | Low-frequency macro data is released with delays and revisions; use release calendars or conservative lags. |
| FX | USD index and major FX series from Datastream/LSEG or FRED | datastream, tr_ds, fred, fx | not queried | none | Crypto often trades as a high-beta anti-USD liquidity asset; USD uptrends can gate risk down. | FX data helps regime filtering but is not crypto-specific. |
| interest rates | Treasury, SOFR/Fed funds, real yield, and yield-curve series | fred, frb, datastream, ice | not queried | none | Rates trend and real-rate shocks can identify hostile conditions for speculative assets. | Daily rates are useful; macro release data must be lagged to avoid revision leakage. |
| commodities | Gold, copper, oil, broad commodity indices | datastream, tr_ds, cme, commodity | not queried | none | Commodity trends can proxy inflation, growth, and risk sentiment; gold/BTC interaction may be relevant. | Commodity signals are indirect and can add noise if used without a predeclared regime rule. |
| equity indices | CRSP/Compustat/Datastream equity index returns | crsp, comp, datastream, msci, snp | not queried | none | Risk-on/risk-off gate: equity trend, drawdown, breadth, and realized volatility. | Equity data is useful for regime, not as a direct crypto alpha source. |
| volatility indices | CBOE VIX/VVIX or Datastream volatility index series | cboe, datastream, optionm | not queried | none | Volatility shock filter: reduce crypto exposure when VIX is high or rapidly rising. | VIX reflects equity options, not crypto options; still useful as a global risk proxy. |
| ETF flows | ETF Global, CRSP mutual fund/ETF, Lipper, or fund-holdings data if licensed | etf, crsp, lipper, fund | not queried | none | Institutional flow proxy, especially for spot BTC/ETH ETFs if covered after launch. | WRDS ETF flow coverage may not include crypto ETFs or may arrive with delays unsuitable for weekly trading. |
| news / RavenPack | RavenPack or other licensed news sentiment on WRDS | ravenpack, raven, news | not queried | none | Risk-event filter and sentiment confirmation if crypto entities or broad market risk topics are covered. | News is high-dimensional, licensed, timestamp-sensitive, and easy to overfit. |
| options / OptionMetrics | OptionMetrics IvyDB and index/ETF options | optionm, optionmetrics, ivydb | not queried | none | Equity/index options can provide implied-risk features; crypto options are unlikely unless specifically licensed elsewhere. | Useful for market-regime filters, but not a substitute for Deribit-style crypto implied volatility. |

## Useful vs not useful

Useful for this project:

- Datastream/LSEG or equivalent cross-asset series for USD, rates, equity indices, commodities, and VIX-style volatility proxies.
- FRED/FRB-style macro and rates series if point-in-time or conservatively lagged.
- OptionMetrics/CBOE-style implied risk measures for broad markets.
- ETF/fund-flow datasets only if they include timely BTC/ETH ETF flow or institutional risk-flow proxies.
- RavenPack/news only if timestamped entity-level coverage is available and the feature set is tightly predeclared.

Not useful as a first priority:

- Corporate fundamentals and accounting databases for single-name equities.
- Intraday equity TAQ data unless the research question shifts to cross-market microstructure.
- Equity options chains for single stocks unrelated to crypto, except as broad risk-regime aggregates.
- Static holdings or delayed fund data that cannot be known before weekly crypto rebalances.
