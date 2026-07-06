# Feature-engineering inventory

## Conventions

- `P`, `H`, `L`, `V` are close, high, low and base volume; `DV=P×V`; `r=Δlog(P)` or simple return where the implementation uses `pct_change`.
- `RV_h` is annualized trailing standard deviation unless explicitly called realized variance.
- `U_t` is the point-in-time eligible universe. Cross-sectional statistics use only `U_t`.
- `t-1` means the last completed daily close before the decision timestamp. “Close t → next period” is also leakage-safe when the trade becomes effective after that close.
- “Conditional” means the feature is implemented in code but the required raw field does not have adequate coverage in the current panel.
- Leakage risk is assessed for live use, not merely whether the current code shifts the series.

## Price trend

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `distance_ma_20` | `P(t-1)/mean(P,t-20:t-1)-1` | 20d | Asset | 1d | Short trend state and extension | Low if MA ends at t-1 | Yes | Yes, but pair with a slower trend |
| `distance_ma_100` | `P(t-1)/MA100(t-1)-1` | 100d | Asset | 1d | Medium/long trend regime | Low | Yes | Yes |
| `distance_ma_200` | `P(t-1)/MA200(t-1)-1` | 200d | Asset | 1d | Slow risk-on/risk-off filter | Low; listing warm-up is essential | Yes | Yes for BTC/ETH and mature assets |
| `trend_alignment` | `P(t-1)/MA100(t-1)-1` | 100d | Asset | 1d | Confirms breakout direction | Low | Yes, breakout module | Yes |
| MA crossover | `1[MA20(t-1)>MA100(t-1)]` | 20/100d | Asset | 1d | Persistent trend confirmation | Low | Yes, signal engine | Yes as a rule, not a continuous ML feature alone |
| `breakout_strength_20` | `P(t-1)/max(H,t-21:t-2)-1` | 20d | Asset | 1d | Measures new-high penetration | Medium if the current high is included; code excludes it | Yes | Yes |

## Momentum

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `momentum_7` | `P(t-1)/P(t-8)-1` | 7d | Asset | 1d | Short continuation/reversal state | Low | Yes | Conditional; unstable alone |
| `momentum_14` | `P(t-1)/P(t-15)-1` | 14d | Asset | 1d | Short/medium continuation | Low | Yes | Yes in multi-horizon composite |
| `momentum_30` | `P(t-1)/P(t-31)-1` | 30d | Asset | 1d | Monthly trend | Low | Yes | Yes |
| `momentum_90` | `P(t-1)/P(t-91)-1` | 90d | Asset | 1d | Quarterly trend | Low | Yes | Yes |
| `momentum_30_ex_7` | `P(t-8)/P(t-31)-1` | days 8–30 | Asset | 8d endpoint | Removes recent reversal contamination | Low | Yes | Yes |
| `momentum_90_ex_7` | `P(t-8)/P(t-91)-1` | days 8–90 | Asset | 8d endpoint | Standard skip-week cross-sectional signal | Low | Yes | Yes; strongest simple ranking input |
| `volatility_adjusted_momentum` | `momentum_30/RV30` | 30d | Asset | 1d | Compares trend per unit risk | Low; guard near-zero volatility | Yes | Yes |
| `market_momentum_30` | mean eligible 30d returns | 30d | Market | 1d in production allocator | Broad market direction | Medium if membership is not point-in-time | Yes | Yes |
| `market_momentum_90` | mean eligible 90d returns | 90d | Market | 1d | Slow market regime | Medium if universe drifts | Yes | Yes |

## Reversal

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `reversal_7` | `-momentum_7` | 7d | Asset | 1d | Short-term bounce candidate | Low | Yes | Only with capitulation/liquidity confirmation |
| `reversal_z` | `(mom7-7×mean(r,20))/(std(r,20)×sqrt(7))` | 7/20d | Asset | 1d | Identifies statistically extreme short moves | Low | Yes, mean-reversion signal | Yes with a fixed extreme threshold |

## Volatility

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `realized_volatility_20` | `std(r,20)×sqrt(365)` | 20d | Asset | 1d | Current asset risk | Low | Yes | Yes |
| `realized_volatility_30` | `std(r,30)×sqrt(365)` | 30d | Asset/market | 1d | Risk scaling and regime state | Low | Yes | Yes |
| `volatility_60` | `std(r,60)` | 60d | Asset | 1d | Slow volatility comparator | Low | Yes, signal engine | Yes |
| `har_log_rv_1` | `log(r_t²+ε)` | 1d | Market basket | Close t → next period | HAR short component | Low if decision follows close | Yes | Yes |
| `har_log_rv_7` | `log(mean(r²,7)+ε)` | 7d | Market | Close t → next period | Volatility persistence | Low | Yes | Strongly recommended |
| `har_log_rv_30` | `log(mean(r²,30)+ε)` | 30d | Market | Close t → next period | Slow volatility state | Low | Yes | Strongly recommended |
| `rv_ratio_1_7` | `logRV1-logRV7` | 1/7d | Market | Close t → next period | Short volatility shock | Low | Yes | Yes |
| `rv_ratio_7_30` | `logRV7-logRV30` | 7/30d | Market | Close t → next period | Volatility acceleration | Low | Yes | Strongly recommended |
| `jump_share_7` | `max(r²,7)/sum(r²,7)` | 7d | Market | Close t → next period | Concentration of recent variance in one jump | Low | Yes | Yes |
| `market_volatility_expansion_probability` | Frozen Elastic Net probability that future RV7 exceeds past RV7 | 7d target | Market | Forecast known at t; momentum module adds 1d lag | Calibrated forward risk state | High if refitted or recalibrated on trading results | Yes | Yes for monitoring and deterministic sizing only |

## Downside risk

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `downside_volatility_30` | `std(min(r,0),30)×sqrt(365)` | 30d | Asset | 1d | Separates harmful from upside volatility | Low | Yes | Yes |
| `log_downside_semivariance_7` | `log(sum(r²×1[r<0],7)+ε)` | 7d | Market | Close t → next period | Downside shock intensity | Low | Yes | Strongly recommended |
| `log_upside_semivariance_7` | `log(sum(r²×1[r≥0],7)+ε)` | 7d | Market | Close t → next period | Asymmetry against downside variance | Low | Yes | Yes |
| `tail_proxy_30` | rolling 5th percentile of market return | 30d | Market | 1d in legacy feature builder | Recent left-tail state | Medium with only 30 observations | Yes, legacy | Prefer semivariance or longer expected shortfall |
| volatility-adjusted success hurdle | `forward net return > 0.25×daily vol×sqrt(holding days)` | 20d vol | Event label | Future label only | Requires payoff beyond ordinary noise | Not a live feature; label leakage if reused at decision time | Yes | Yes as a secondary label only |

## Drawdown

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `max_drawdown_90` | minimum of `P/rolling_peak90-1` | 90d | Asset | 1d | Persistent damage/recovery state | Low | Yes | Yes |
| `asset_drawdown_90` | `P(t-1)/max(P,90 through t-1)-1` | 90d | Asset | 1d | Current distance below recent peak | Low | Yes | Yes |
| `market_drawdown` | market wealth / running peak - 1 | Expanding | Market | 1d in live strategy modules | Broad stress and recovery state | Medium if wealth uses future universe members | Yes | Yes with point-in-time basket |
| `strategy_drawdown` | strategy wealth / running peak - 1 | Expanding | Strategy | 1d | Detects deterioration of a deployed rule | High if strategy definition changes retrospectively | Yes | Yes only for frozen strategies |

## Liquidity

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `log_dollar_volume_30` | `log(1+median(P×V,30))` | 30d | Asset | 1d | Capacity and tradability | Medium from wash volume and quote conversion | Yes | Yes |
| aggregate `log_dollar_volume` | `log(1+sum_U DV)` | 1d | Market | Close t → next period | Market activity state | Medium from changing universe | Yes | Yes |
| `amihud_illiquidity_30` | `log(mean(abs(r)/DV,30)+ε)` | 30d | Asset/market | 1d or close t | Price impact proxy | High for tiny/stale DV values | Yes | Yes with winsorization |
| `high_low_spread` | weighted mean `(H-L)/P` | 1d | Market | Close t → next period | Low-frequency range/liquidity proxy | Medium because range also measures volatility | Yes | Yes as a control |
| turnover proxy | aggregate dollar volume / market cap | 1d | Market | 1d in legacy module | Trading intensity relative to size | High because OHLCV `market_cap` is not true cap in the exchange panel | Legacy only | No until true point-in-time market cap exists |
| universe liquidity rank | rank by trailing median DV | 90d | Asset membership | 1d | Point-in-time investable universe | High if based on today's listings | Yes | Essential |

## Volume

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `volume_growth_7_30` | `log(1+mean(DV,7))-log(1+mean(DV,30))` | 7/30d | Asset | 1d | Recent participation acceleration | Low after volume cleaning | Yes | Yes |
| `asset_volume_growth_30` | `V(t-1)/V(t-31)-1` | 30d | Asset | 1d | Event participation | High around listing/unit changes | Yes | Prefer normalized abnormal volume |
| `volume_expansion` | `V(t-1)/median(V,t-21:t-2)` | 20d | Asset | 1d | Breakout confirmation | Medium around exchange outages | Yes | Yes |
| `dollar_volume_change_1` | `Δ log aggregate DV` | 1d | Market | Close t → next period | Activity shock | Medium | Yes | Yes after robust clipping |
| `dollar_volume_change_7/30` | difference in log aggregate DV | 7/30d | Market | Close t → next period | Persistent activity change | Medium | Yes | Yes |
| `volume_concentration` | sum of squared asset DV shares | 1d | Market | Close t → next period | Activity concentrated in few assets | Medium from incomplete universe | Yes | Yes; call it volume concentration, not market-cap concentration |
| `zero_volume_share` | share of eligible assets with `V≤0` | 1d | Market | Close t → next period | Data/liquidity stress | High because zeros may be feed failures | Yes | Use mainly as data-quality flag |

## Market breadth

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `breadth_20` | share of eligible assets with positive 20d momentum | 20d | Market | Close t → next period | Participation in market trend | Medium if universe membership leaks | Yes | Yes |
| `market_breadth_30` | share of eligible assets with positive 30d momentum | 30d | Market | 1d/live | Distinguishes broad from narrow rallies | Medium if stale prices count as flat | Yes | Strongly recommended |
| top-10 breadth gate | same measure restricted to point-in-time top 10 | 30d | Market | 1d | Liquid-market confirmation | Low after point-in-time membership | Yes | Yes |

## Dispersion

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `cross_sectional_dispersion_1` | weighted standard deviation of same-day asset returns | 1d | Market | Close t → next period | Current cross-sectional opportunity/state | Medium with missing/stale assets | Yes | Yes |
| `cross_sectional_dispersion_7` | mean of daily cross-sectional dispersion | 7d | Market | Close t or 1d | Persistent differentiation among assets | Medium | Yes | Strongly recommended for momentum gating |
| `market_dispersion_30` | mean asset trailing return volatility | 30d | Market | 1d | Broad heterogeneity proxy | Medium; not identical to return dispersion | Yes | Keep but label precisely |

## Correlation

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `average_correlation_30` | mean off-diagonal pairwise correlation | 30d | Market | Close t or 1d | Systemic co-movement | High with pairwise missingness and small samples | Yes | Yes with shrinkage and coverage reporting |
| `market_correlation_60` | mean pairwise eligible-asset correlation | 60d | Market | 1d | Slow systemic regime | High if correlation panel includes ineligible assets | Yes | Yes |
| `first_eigenvalue_share_30` | largest correlation eigenvalue / sum positive eigenvalues | 30d | Market | Close t → next period | One-factor dominance/herding | High with non-positive-definite noisy matrices | Yes | Yes with shrinkage |

## Dominance / market state

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `market_btc_trend_30` | BTC 30d return | 30d | Market | 1d | Crypto market direction anchor | Low | Yes | Yes |
| `market_eth_trend_30` | ETH 30d return | 30d | Market | 1d | Secondary market anchor | Low | Yes | Yes |
| BTC above MA200 | `1[BTC P(t-1)>MA200(t-1)]` | 200d | Market | 1d | Slow risk regime | Low | Yes, paper-candidate rules | Yes |
| BTC/ETH/stablecoin dominance | category market cap / total eligible market cap | Variable | Market | Provider publication lag | Capital rotation and defensive demand | High from supply revisions and denominator drift | No | Recommended only with point-in-time market-cap data |
| equal-weight market return | mean eligible asset return | 1d | Market | 1d or close t | Broad market state independent of BTC | Medium from membership | Yes | Yes |

## Funding / derivatives

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `funding_rate` | realized perpetual funding | Latest | Asset | 1d | Directional leverage pressure | High from venue/schedule differences | Yes | Yes after multi-venue normalization |
| `funding_rate_abs` | absolute realized funding | Latest | Asset | 1d | Crowding intensity independent of direction | Medium | Yes | Yes |
| `funding_rate_change_7` | funding at t-1 minus funding at t-8 | 7d | Asset | 1d | Crowding acceleration | Medium with missing contracts | Yes | Yes |
| `funding_coverage_flag` | funding observation present | 1d | Asset | 1d | Distinguishes missing from neutral | Low if missingness known live | Yes | Essential |
| `deriv_funding_mean/abs/dispersion` | weighted cross-sectional funding moments | 1d | Market | 1d | Aggregate leverage and disagreement | High from changing venue coverage | Yes | Yes; current data supports funding only |
| `deriv_funding_sum_3/7` | rolling sum of mean funding | 3/7d | Market | 1d | Sustained carry/crowding | Medium | Yes | Yes |
| OI level/change/dispersion | log aggregate OI; 1/7d changes; cross-sectional dispersion | 1/7d | Market | 1d | Outstanding leverage and leverage growth | High from contract units and limited history | Conditional, data unavailable | Strongly recommended after normalization |
| basis level/change/dispersion | perpetual/future price minus aligned spot reference | 1/7d | Market | 1d | Carry demand and price discovery | High from timestamp/contract mismatch | Conditional, data unavailable | Recommended |
| liquidation level/change | log aggregate liquidation notional and 7d change | 1/7d | Market | 1d | Forced-flow stress | High from incomplete venues/definitions | Conditional code path; data unavailable | Recommended only with reliable history |
| funding × OI growth | `abs(funding)×Δlog(OI,7)` | 7d | Market | 1d | Crowded leverage more informative than either input alone | High from both input issues | Conditional | High priority |
| option ATM IV and change | constant-maturity 7d/30d ATM implied volatility | 1/7d change | Market | 1d | Forward-looking risk price | High from stale quotes and surface construction | Conditional, unavailable | Recommended for BTC/ETH only |
| option IV term slope | `IV30-IV7` | 7/30d maturity | Market | 1d | Near-term event/stress premium | High from interpolation | Conditional, unavailable | Recommended after surface QA |

## Asset age / listing effects

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `asset_age_days` | `log(1+number of prior valid closes)` | Expanding | Asset | 1d | Controls for immature/listing-sensitive behavior | Low if history begins at true listing | Yes | Yes |
| `recent_listing_flag` | age between minimum-history cutoff and cutoff+90d | 90d band | Asset | 1d | Marks post-listing instability | Medium if pre-exchange history is missing | Yes | Yes |

## Regime / risk state

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| volatility-expansion regime | fixed probability or declared probability bins | 7d forecast | Market | As-of forecast | Forward risk budget | High if bins are optimized on returns | Yes | Use continuous sizing or preregistered bins |
| risk-on gate | BTC mom30 positive, market vol below 80%, breadth above 45% | 30d | Market | 1d | Avoids weak/high-risk markets | High threshold-selection risk | Yes | Use only with preregistered thresholds |
| market-gated momentum state | BTC above MA200, BTC mom30 positive, top-10 breadth above 50%, drawdown and volatility gates | Mixed | Market | 1d | Requires aligned direction and participation | High from conjunctive threshold search | Yes | Keep as a transparent benchmark, not search space |
| correlation/eigenvalue state | average correlation and first eigenvalue share | 30/60d | Market | 1d | Detects one-factor panic/herding | Estimation and threshold risk | Features yes; explicit state no | Recommended |
| dispersion state | rolling cross-sectional dispersion level | 7/30d | Market | 1d | Conditions cross-sectional opportunity | Threshold risk | Feature yes; gate not yet tested as locked primary | High-priority next hypothesis |
| drawdown brake state | deterministic exposure cuts after strategy drawdown | Expanding | Strategy | 1d | Limits path-dependent risk | High if brake thresholds are searched | Yes | Use one preregistered schedule |

## Strategy health

| Feature | Formula | Window | Level | Lag | Economic rationale | Leakage risk | Implemented | Recommended |
|---|---|---:|---|---|---|---|---|---|
| `strategy_return_28` | mean daily strategy return | 28d | Strategy | 1d | Recent efficacy | High if strategy is redefined | Yes | Yes for monitoring; weak allocation evidence |
| `strategy_volatility_28` | standard deviation of strategy returns | 28d | Strategy | 1d | Current strategy risk | Low for frozen rule | Yes | Yes |
| `strategy_hit_rate_28` | share of positive daily returns | 28d | Strategy | 1d | Recent consistency | Medium with many zero-exposure days | Yes | Replace with active-trade hit rate where possible |
| `recent_breakout_hit_rate` | share of positive preliminary breakout returns | 56d | Strategy | 1d | Breakout-specific deterioration | Medium from sparse events | Yes | Yes with minimum-event count |
| `strategy_health_drawdown` | frozen strategy wealth / running peak - 1 | Expanding | Strategy | 1d | Detects prolonged failure | High if backfilled after rule changes | Yes | Yes for monitoring and fixed brakes |

## Inventory conclusions

1. The implemented price, volatility, breadth, dispersion and correlation blocks are sufficient for a disciplined next study; another broad raw-feature expansion is unnecessary.
2. Volatility features have the strongest locked evidence. Momentum and market-state features have economic rationale but weak strategy evidence.
3. Funding is available but does not yet have robust incremental value. OI, basis, liquidations, options and true dominance remain data-gated.
4. The highest-priority engineering gaps are residual/idiosyncratic momentum, trend consistency, volatility-of-volatility, higher moments, beta asymmetry, dispersion/breadth acceleration and correlation breakdown.

