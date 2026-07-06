# Final research recommendation

## Single recommended direction

Determine whether **derivatives positioning, options pricing, and liquidity state improve forecasts of seven-day realized-volatility expansion for a point-in-time top-10 liquid crypto basket beyond a strong price-only HAR-style model**.

This is narrower than “predict market opportunity.” It has a persistent and observable target, direct economic use, plausible alternative-data mechanisms, enough event frequency to validate, and a credible fallback: a price-only volatility model. It does not require return-direction prediction.

## 1. Exact target

### Universe and basket

At each Monday 00:00 UTC:

1. take non-stablecoin, non-wrapped, non-leveraged spot assets available on at least two approved venues;
2. require 180 calendar days of price history and 90% hourly completeness over the prior 30 days;
3. rank by trailing 90-day median daily dollar volume using only data available then;
4. select the top 10 and hold membership for one week;
5. weight by square-root dollar volume and cap each asset at 20%, redistributing excess pro rata.

Preserve delisted assets and historical membership. A fixed BTC-only target is a sensitivity check, not the primary result.

### Label

Using one-hour basket log returns \(r_{m,u}\), define

\[
RV^{future}_{t,7}=\sum_{u=t+1h}^{t+7d} r^2_{m,u},
\qquad
RV^{past}_{t,7}=\sum_{u=t-7d+1h}^{t} r^2_{m,u}.
\]

The primary continuous target is

\[
y_t=\log\left(\frac{RV^{future}_{t,7}+10^{-12}}{RV^{past}_{t,7}+10^{-12}}\right).
\]

Create one observation daily at 00:00 UTC. Labels overlap by design; validation and inference statistics must account for seven-day dependence. The primary model predicts the conditional mean of \(y_t\). A secondary, predeclared output is the probability that \(y_t\) exceeds the rolling training-window 75th percentile; it is not a separate model-selection target.

Sensitivity checks, fixed before the holdout:

- future log RV level rather than ratio;
- bipower-variation/jump-adjusted label;
- 1-day and 14-day horizons;
- BTC and equal-weight top-10 basket targets.

Only the seven-day expansion target determines the main conclusion.

## 2. Exact features

All continuous features are winsorized to training-fold 0.5/99.5 percentiles and robust-standardized using training-fold medians/IQR. Store both event and publication timestamps. No value may enter before it could have been retrieved live.

### Block P — price-only baseline

- basket realized variance over 1, 3, 7 and 30 days;
- upside and downside semivariance over 1 and 7 days;
- bipower variation and jump share over 1 and 7 days;
- basket return over 1, 7 and 30 days;
- aggregate dollar volume and turnover: levels, 1-day and 7-day changes;
- Amihud illiquidity and high–low spread proxy over 1 and 7 days;
- cross-sectional return dispersion over 1 and 7 days;
- average shrunk correlation and first-eigenvalue share over 7 and 30 days;
- trend breadth above 20- and 50-day moving averages;
- BTC and ETH basket weights and BTC market dominance.

### Block D — derivatives positioning

For BTC, ETH and the covered universe, aggregate with lagged dollar-OI weights and retain cross-sectional median, IQR and extreme share:

- realized funding level, absolute value and change over 1, 3 and 7 days;
- dollar OI level and change over 1, 3 and 7 days;
- OI change residual after controlling for contemporaneous price and volume change;
- funding × OI-growth interaction;
- annualized perpetual/quarterly basis level, slope and 1/7-day change;
- long and short liquidation dollar volume divided by lagged OI and spot volume;
- cross-venue funding and basis dispersion.

### Block O — options state

Use BTC and ETH only, because broad altcoin options history is not sufficiently consistent:

- constant-maturity 7- and 30-day ATM implied volatility;
- ATM IV minus trailing realized volatility;
- 25-delta put–call skew at 7 and 30 days;
- 7-to-30-day IV term-structure slope;
- options volume and OI change, normalized by spot volume;
- stale/sparse-surface flags.

### Block L — liquidity and market plumbing

- quoted spread and 1% depth for BTC/ETH and a coverage-weighted universe aggregate;
- top-of-book imbalance and depth change, aggregated to one-hour then daily summaries;
- cross-venue executable price dispersion after fees;
- venue outage/staleness count;
- stablecoin peg deviation and dispersion for USDT/USDC;
- stablecoin exchange net flow as an optional separately reported feature, lagged for label revisions.

Do not add sentiment, hundreds of technical indicators, or broad on-chain catalogs in the first study. If D/O/L blocks fail, more opaque features are unlikely to rescue the target robustly. Entity-labeled BTC exchange flows and stablecoin destination flows are a second-stage block only after revision-vintage data are available.

## 3. Exact models

### Baselines

1. Persistence: predict no expansion, \(\hat y_t=0\).
2. Historical expanding-window mean.
3. HAR-RV using 1/7/30-day realized variance.
4. Elastic-net linear regression on Block P.

### Candidate models

5. Elastic-net regression on P+D, P+D+O, and P+D+O+L.
6. Shallow XGBoost regression on the same cumulative blocks: maximum depth 2–4, minimum leaf/child weight constrained, learning rate 0.01–0.1, and early stopping only inside inner validation.
7. A fixed 50/50 average of standardized elastic-net and XGBoost predictions, eligible only if both models independently beat HAR-RV in outer folds.

Do not use RF, LSTM, TFT, PatchTST, foundation models or GNNs in the confirmatory stage. They remain challengers only after a tabular feature block passes the untouched holdout. This caps researcher degrees of freedom and keeps the result deployable.

## 4. Exact validation protocol

### Data partitions

- **Development start:** first date with 80% coverage of required P+D features, targeted no later than 1 January 2020.
- **Outer development period:** start through 31 December 2024.
- **Untouched holdout:** 1 January 2025 through 22 June 2026.
- The holdout remains encrypted/access-controlled or is materialized only after the model card, feature list, transformations, and selection rule are signed off.

### Nested walk-forward development

Use expanding training windows with six-month outer test blocks. The first outer training window must contain at least 24 months. Inside each outer training window:

- use three or more rolling validation folds of six months where history permits;
- purge observations whose seven-day labels cross a train/validation boundary;
- apply a seven-day embargo after each boundary;
- fit universe transforms, missing-value handling, scaling, feature selection, hyperparameters, and calibration only on the inner training portion;
- rank configurations by median inner-fold QLIKE, with log-RV MSE as a secondary metric;
- prefer the simpler model if median QLIKE differs by less than 1%;
- refit the selected configuration on the full outer training window and predict the next six months once.

At 31 December 2024, freeze one model/feature-block selection rule based only on outer predictions. Refit it once on all eligible development data and generate holdout predictions sequentially. No feature, threshold, provider substitution, hyperparameter, or retraining schedule changes are allowed after the first holdout outcome is viewed. Quarterly refits may occur only if that schedule was fixed before unblinding.

### Primary scores and statistical control

- Primary statistical loss: QLIKE on future variance reconstructed from the expansion prediction.
- Secondary: MSE/MAE of log RV, Spearman rank correlation, top-quartile Brier score, calibration slope/intercept.
- Economic forecast utility: realized-volatility target error from a mechanical inverse-volatility risk scaler, evaluated without claiming a return strategy.
- Paired comparison: alternative-data model minus matched price-only model on identical dates.
- Confidence intervals: stationary/block bootstrap with expected block length at least seven days; report sensitivity at 14 and 28 days.
- Report Diebold–Mariano-style paired loss tests with dependence-robust errors, but do not rely on their p-values alone.
- Correct the confirmatory family across the two model classes and three cumulative alternative-data blocks using Holm correction.
- Publish the total number of labels, features, transforms, model/hyperparameter configurations and sensitivity analyses attempted.

### Graduation threshold

Call the alternative data genuinely useful only if the selected model:

1. reduces median outer-fold QLIKE by at least 3% versus the matched Block-P model;
2. improves QLIKE in at least 70% of outer folds;
3. reduces untouched-holdout QLIKE by at least 3%;
4. has a 95% block-bootstrap interval for holdout paired loss improvement excluding zero;
5. improves volatility-target error without materially increasing turnover in the mechanical risk scaler;
6. does not derive more than half its improvement from any single 30-day episode;
7. retains the sign of improvement under the predeclared label and data-lag sensitivities.

Anything weaker is exploratory, even if one model or subperiod looks attractive.

## 5. Required data sources

| Need | Preferred source | Fallback / validation source |
|---|---|---|
| Spot hourly trades/OHLCV and metadata | Binance + Coinbase direct APIs | Coin Metrics MDF or Amberdata normalized feed |
| Historical funding, OI, basis, liquidations | Coin Metrics MDF, Amberdata, or another contracted normalized vendor | Binance/Bybit direct history plus prospectively archived feeds; limited history must be disclosed |
| BTC/ETH options surface | Deribit instruments, books and trades with self-built constant maturities | Coin Metrics/Amberdata normalized options history |
| Historical spread/depth and venue status | Contracted institutional feed | Low-frequency OHLCV liquidity proxies; reduced-scope study |
| Stablecoin peg/reference prices | Multi-venue spot feeds | CoinGecko reference aggregation |
| Stablecoin exchange flows, optional | One provider with vintage entity labels | Omit rather than use retrospectively revised labels |
| Asset identity and point-in-time membership | Vendor security master plus archived exchange metadata | Internally versioned mapping with manual audit |

The project should pay for **one** normalized historical derivatives/microstructure source, not several alternative-data catalogs. Use direct exchange feeds as a cross-check and for prospective collection.

## 6. Expected difficulty

**Overall: high data-engineering difficulty, medium modeling difficulty.**

The hard work is contract normalization, historical OI/liquidation depth, expired options, constant-maturity surfaces, delisted symbols, point-in-time universe membership, provider revisions and 24/7 timestamp alignment. The recommended models are intentionally ordinary. A credible common panel may take more effort than fitting every candidate model combined.

Main risks:

- common-sample history becomes too short after alternative-data coverage filters;
- direct exchange endpoints do not retain enough OI/liquidation history;
- options features mostly restate contemporaneous realized volatility;
- one crisis drives all apparent incremental gain;
- vendor-derived labels are retrospectively revised;
- dynamic-universe construction leaks today’s survivors.

## 7. Expected deployability

**Medium–high if the price-only model is always available; medium for the full alternative-data model.**

Forecasting daily for a seven-day horizon is latency-tolerant. Elastic net/XGBoost inference is cheap and explainable enough for risk oversight. The production service must fall back to Block P when a derivatives/options source is stale, cap forecast changes, and keep exposure decisions in a deterministic risk layer. Data licensing, feed monitoring and options-surface quality are the continuing operational costs.

The forecast is suitable for:

- portfolio volatility targeting and cash/risk-budget control;
- dynamic concentration and liquidity limits;
- hedge-budget planning;
- a market-state input to separately validated strategies.

It is not a standalone trading signal and should not be presented as expected-return alpha.

## 8. Estimated probability of genuine signal

**Estimated probability that the alternative-data model meets all graduation criteria: 40%.**

This is a subjective ex-ante research estimate, not a statistical output. The probability is below 50% because [recent crypto-volatility research](https://doi.org/10.1016/j.irfa.2023.102914) finds internal market determinants highly important, the effective crisis sample is small, and clean historical derivatives/microstructure coverage is uneven. It is still high enough to justify the study because funding/OI, options IV/skew, and liquidity have direct mechanisms and volatility is materially more predictable than return direction.

For context:

- probability that a price-only model beats naive persistence: approximately 75%;
- probability that some alternative-data configuration appears to help during development: approximately 70%;
- probability that the improvement survives the predeclared untouched holdout and operational-cost test: approximately 40%.

The gap between the last two estimates is exactly why the holdout and configuration accounting are mandatory.

## Stop / proceed decisions

1. **Data gate:** stop or reduce scope if P+D common coverage cannot provide at least four distinct volatility regimes and 80% feature availability.
2. **Baseline gate:** proceed to alternative data only after HAR-RV and Block-P results are reproducible across providers.
3. **Development gate:** purchase/maintain expanded options and depth data only if D adds stable outer-fold value or O/L has a separately pre-registered mechanism.
4. **Holdout gate:** deploy the alternative model only if all graduation criteria pass; otherwise deploy the simpler price-only risk forecast, if useful.
5. **Complexity gate:** consider TFT/graphs only after a tabular alternative-data block survives the holdout.

## Final conclusion

The best next project is not a new return predictor or a large deep-learning system. It is a tightly controlled test of whether leverage, option-implied risk and liquidity improve a seven-day volatility-expansion forecast over price history. The expected result should be treated skeptically: price-only volatility persistence may remain the winner. That negative outcome would still save substantial data and model-maintenance cost and would be a successful research decision.
