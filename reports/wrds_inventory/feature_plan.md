# Crypto-relevant WRDS feature plan

All WRDS features must be timestamped, lagged, and joined to the crypto decision
calendar before any trading experiment. The first use case should be regime
filtering, not return prediction.

| Feature group | WRDS source | Example features | Trading use | Leakage control |
|---|---|---|---|---|
| macro risk regime | Datastream/LSEG, FRED/FRB macro series if accessible | financial-conditions z-score; recession/stress proxy; release-lagged macro surprise where available | Permit crypto exposure only outside broad macro stress. | Use publication/release lags; do not use revised values at original dates without point-in-time vintages. |
| USD liquidity | DXY/broad USD from Datastream/LSEG or FRED; money-market/rates series | DXY 50/200-day trend; 20-day USD momentum; liquidity impulse proxy | Reduce BTC/ETH exposure during strong USD/liquidity-tightening regimes. | Daily series lagged one trading day; macro proxies lagged by release schedule. |
| rates | Treasury, Fed funds, SOFR, real yields from FRED/FRB/Datastream | 2Y and 10Y yield trend; 10Y real-yield change; yield-curve slope | Identify tightening shocks that historically pressure high-duration risk assets. | Use prior close or conservative one-day lag. |
| equity risk-on/risk-off | CRSP/Compustat/Datastream equity index data | S&P 500 above 200-day average; Nasdaq 30-day momentum; equity drawdown | Gate crypto risk when equities are in confirmed uptrends. | Align to crypto decision timestamp; lag one day because crypto trades 24/7. |
| commodity risk sentiment | Datastream/LSEG commodity series | gold trend; copper/gold ratio; oil shock filter; broad commodity momentum | Differentiate inflation shocks, growth risk, and safe-haven regimes. | Daily lag; predeclare transformations to avoid narrative fitting. |
| VIX / volatility | CBOE/Datastream VIX, VVIX, MOVE if licensed | VIX level percentile; 5-day VIX change; volatility shock dummy | Risk-off gate or position-size reduction during volatility shocks. | Use only observations known before rebalance. |
| ETF / institutional flows | ETF Global, CRSP mutual fund/ETF, Lipper, holdings databases if licensed | BTC ETF AUM/flow change; crypto-equity ETF flow; institutional demand proxy | Confirm risk-on exposure if spot ETF flow data is timely and complete. | Use actual report availability dates; assume stale if only monthly/quarterly. |
| news sentiment | RavenPack if licensed | crypto entity sentiment; macro risk sentiment; novelty-weighted negative-news shock | Avoid exposure during broad negative event clusters; do not use as a standalone alpha yet. | Use timestamped news only; aggregate before rebalance cut-off. |
| options-implied volatility | OptionMetrics, CBOE, Datastream | SPY/QQQ implied volatility; skew; term-structure slope; VIX/VVIX | Forward-looking risk proxy for macro-conditioned crypto exposure. | Lag option metrics and ensure no post-close values enter same-day crypto decisions. |

## Integration rules

1. Store downloaded WRDS data under `data/raw/wrds/` and normalized daily features
   under `data/processed/wrds/`.
2. Preserve vendor identifiers, query dates, and field descriptions.
3. Convert all timestamps to a documented decision calendar. For daily US market
   data, use at least a one-day lag before crypto allocation decisions.
4. For macro releases, use release dates or conservative lags. Do not use revised
   values as if they were known historically.
5. Keep the existing 2025+ evaluation period locked. If the hypothesis is refined
   after seeing that period, register a new prospective holdout.
