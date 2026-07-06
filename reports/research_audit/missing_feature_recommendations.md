# Missing-feature recommendations

## Selection principle

Missing features are recommended only when they add a distinct mechanism, can be timestamped live and can be tested as a small predeclared block against the existing price-only baseline. They are not authorization for a broad feature search. All rolling transforms must end at `t-1` for a close-to-close strategy, use point-in-time universe membership, and be fitted or normalized inside each training fold.

## Price-derived features available from the current panel

| Feature | Exact proposed construction | Data | Why it may help | Main risk | Priority | Minimal falsification test |
|---|---|---|---|---|:---:|---|
| Volatility-of-volatility | `std(log RV7, 30)` and `std(RV7, 30)/mean(RV7,30)` ending t-1 | Existing daily closes | Separates stable high volatility from unstable risk transitions | Daily RV is noisy; overlaps the volatility-expansion forecast | A | Add only these two columns to the frozen price-only model; require consistent Brier/QLIKE improvement |
| Realized skewness | `mean((r-mean r)^3)/std(r)^3` over 30 and 90 days; winsorize inside train fold | Existing closes | Negative skew can identify crash-prone trend states; positive skew may mark speculative runs | Very unstable in short windows | A | Require stable sign and improvement across both windows without selecting one on holdout |
| Realized kurtosis | fourth standardized central moment over 30/90 days, excess form minus 3 | Existing closes | Captures jump/tail concentration beyond RV | Dominated by single bad candles | B | Repeat after robust clipping and after excluding known bad candles |
| Downside beta to BTC | `cov(r_i,r_BTC | r_BTC<0)/var(r_BTC | r_BTC<0)` over 90/180 days | Existing closes | Identifies assets that amplify BTC selloffs | Few downside observations; beta instability | A | Compare with ordinary beta; require better drawdown/rank prediction in most folds |
| Upside beta to BTC | analogous beta using days with positive BTC return | Existing closes | Separates upside participation from downside fragility | Conditional sample is noisy | A | Test downside-minus-upside beta as one preregistered asymmetry feature |
| Rolling beta to BTC | trailing 90/180-day OLS beta, estimated through t-1 | Existing closes | Controls systematic crypto exposure | Errors-in-variables and changing beta | A | Use 180d primary, 90d sensitivity; require minimum 60 paired observations |
| Correlation breakdown | `corr30-corr90`, 5-day change in average correlation, and share of pairs whose 30d correlation falls below their 252d median | Existing closes | Momentum selection may work when assets differentiate; panic raises correlations | Pairwise missingness and universe churn | A | Use shrinkage; test as one three-feature block, not separate searches |
| Trend consistency | share of positive daily returns over 30/90 days; regression slope divided by residual error; sign agreement of 30/90 momentum | Existing closes | Distinguishes smooth trends from one-jump momentum | Multiple equivalent definitions create search risk | A | Freeze sign-agreement plus positive-day share as the primary pair |
| Volume confirmation | sign of 30d price trend × `log(mean DV7/mean DV30)` | Existing OHLCV | Trends supported by participation may persist better | Exchange volume can be inflated | A | Test interaction against price momentum and volume growth separately |
| Abnormal volume | `(log DV(t-1)-median(log DV,60))/MAD(log DV,60)` | Existing OHLCV | Robustly detects unusual participation around signals | Listings/outages create false anomalies | A | Exclude first 180 days and require signal across liquidity tiers |
| Distance from all-time high | `P(t-1)/max(P up to t-1)-1`, only after minimum 365-day history | Existing closes | Long-horizon damage/recovery and anchoring | “All time” depends on data start/exchange listing | B | Report both exchange-history ATH and 365d high sensitivity |
| Distance from 30/90/180-day high | `P(t-1)/rolling_max_h(t-1)-1` for fixed h | Existing closes | Measures trend extension and recovery at several economically distinct horizons | Highly collinear; searching the best horizon | A | Use 30/90/180 as one block; do not select a single horizon by holdout |
| Market concentration | Herfindahl index of lagged dollar-volume shares now; true market-cap HHI when point-in-time cap is available | Existing DV; later market cap | Narrow concentration can weaken cross-sectional breadth and increase systemic risk | DV concentration is not ownership/value concentration | A for DV, B for cap | Rename current feature explicitly; test changes and level together |
| Breadth acceleration | `breadth20(t-1)-breadth20(t-8)` and breadth minus its 30d mean | Existing closes/universe | Early improvement/deterioration may precede index trend | Threshold and denominator instability | A | Primary definition is 7d change; 30d deviation is sensitivity only |
| Dispersion acceleration | `dispersion7(t-1)/dispersion30(t-1)-1` and 7d change in log dispersion | Existing closes/universe | Identifies expanding cross-sectional opportunity | Volatility spikes can masquerade as opportunity | A | Condition on market drawdown in analysis; do not add a return-direction target |
| Cross-sectional volatility rank | percentile rank of each asset's RV30 within `U_t` | Existing closes/universe | Normalizes risk across changing regimes and assets | Rank hides absolute risk | A | Test rank alongside log absolute RV, not as a replacement |
| Idiosyncratic momentum | cumulative residual return from a rolling BTC/ETH factor regression, days t-90 to t-8 | Existing closes | Measures asset-specific trend rather than market beta | Regression estimation error and thin histories | A | Estimate betas with trailing 180d only; compare with raw skip-week momentum |
| Residual momentum after BTC/ETH beta removal | fit `r_i=α+β_B r_BTC+β_E r_ETH+ε_i` on prior 180d; compound ε over days 8–90 | Existing closes | Correct implementation of residual momentum; common market moves are removed asset by asset | Same-period residualization or full-sample beta leaks | A | Betas fixed from data ending t-1; require rank IC and portfolio evidence in nested walk-forward tests |

## Derivatives, stablecoin and forced-flow features

| Feature | Exact proposed construction | Required data | Why it may help | Main risk | Priority | Data gate / falsification test |
|---|---|---|---|---|:---:|---|
| Stablecoin risk proxy | weighted peg deviation, 7d change in exchange-held stablecoin balance, and stablecoin share of total crypto market cap | Point-in-time USDT/USDC/DAI prices, supply and exchange balances | Depegs and defensive capital shifts can signal funding/liquidity stress | Supply revisions, treasury mints and bridge transfers are not investor flows | C | Omit until vintage timestamps and stablecoin taxonomy are available; never infer from spot universe exclusions |
| Funding crowding | asset funding z-score over trailing 90 observations; market share with absolute z-score above 2; interaction with OI growth | Existing funding plus normalized OI for full version | Extreme directional carry plus leverage creates squeeze/liquidation risk | Venue schedules and contract survivorship | A for funding-only, A+ after OI | Test funding-only first; graduate interaction only on common-sample data |
| Open-interest change | 1d/7d `Δlog(USD OI)` and OI/DV ratio | Multi-venue contract OI normalized to USD | Measures leverage accumulation | Direct endpoints retain short history; contract units change | A when data exists | Require at least three regimes and 80% point-in-time coverage |
| Liquidation proxy | actual long/short liquidation notional divided by DV; fallback: downside jump × abnormal volume × OI decline | Multi-venue liquidation history; OHLCV/OI fallback | Forced selling/buying can mark capitulation and subsequent risk | Proxy is endogenous and directionally ambiguous | B | Label fallback explicitly as a proxy; compare with actual liquidations on overlap |
| Funding dispersion acceleration | cross-sectional funding dispersion7 / dispersion30 - 1 | Existing asset funding panel | Heterogeneous crowding may precede return dispersion | Coverage changes can create artificial dispersion | B | Hold contract set constant within each calculation and report coverage |
| Basis stress | median perp/spot basis, dispersion and 7d change | Time-aligned perpetual and spot prices | Carry dislocation and balance-sheet stress | Cross-venue price timing and collateral differences | B | Require synchronized snapshots and venue sensitivity |

## Recommended implementation order

1. **Core price block:** rolling BTC beta, downside/upside beta, idiosyncratic skip-week momentum, trend consistency and distance-to-high features.
2. **Opportunity-state block:** dispersion acceleration, correlation breakdown, breadth acceleration, market concentration and cross-sectional volatility rank.
3. **Participation block:** robust abnormal volume and volume-confirmed trend.
4. **Higher-moment block:** volatility-of-volatility, skewness and kurtosis, evaluated primarily as risk-state features.
5. **Derivatives block:** funding crowding now; OI, basis and liquidations only after a point-in-time data-quality audit.
6. **Stablecoin block:** defer until vintage supply, peg and exchange-flow data can be sourced without retrospective entity-label leakage.

## Engineering rules

- Add feature blocks, not one-off columns selected by apparent performance.
- Calculate rolling normalization parameters using the current training window only.
- Maintain availability and staleness flags; never impute an unavailable derivative observation as zero funding or zero OI.
- Require the exact same active universe and timestamp policy for feature and target construction.
- Persist raw inputs, formula version, observation timestamp, source timestamp and code hash for every production feature.
- Remove any feature whose incremental value depends on a single 30-day episode or one asset.

