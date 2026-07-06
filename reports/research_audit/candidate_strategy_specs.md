# Predeclared candidate-strategy specifications

## Status

These specifications are **research designs only**. They have not been implemented or backtested in this task. Similar components have appeared in prior experiments, so the historical 2025–2026 results cannot serve as an untouched test of these newly assembled rules. The exact formulas below must be registered before code is run.

## Common execution and acceptance contract

- Long-only spot; no leverage and no shorts.
- Decision features end at the prior completed UTC daily close. Orders become effective after the scheduled rebalance close.
- Point-in-time Binance top-liquidity membership, excluding stablecoins, wrapped assets and assets with less than 365 days of valid history.
- Baseline costs: 25 bps per unit of one-way turnover; sensitivities at 10, 50 and 100 bps.
- Maximum asset weight: 20% for altcoins, 50% for BTC/ETH in multi-asset portfolios, 100% only when a specification explicitly holds one of BTC or ETH.
- Maximum one-way turnover per rebalance: 75%; unexecuted change carries to the next scheduled rebalance.
- Cash earns zero in the research backtest. Any later deployment must specify the actual custody/yield treatment separately.
- A candidate passes only if the new prospective holdout has Sharpe above 0.5, CAGR above zero, max drawdown better than BTC buy-and-hold, positive CAGR and Sharpe at 50 bps, annual turnover below 12x, and no 95% paired block-bootstrap evidence that it is worse than its stated baseline.
- Promotion additionally requires positive performance in at least 60% of outer walk-forward test blocks and no single 30-day period contributing more than half of total profit.

## A. BTC/ETH/cash trend rotation

### Full rules

1. Rebalance every four Fridays.
2. For BTC and ETH, calculate lagged 30-day momentum, 90-day momentum, distance above MA200, 30/90-day positive-return share and RV30.
3. An asset qualifies only when price is above MA200, both momentum horizons are positive and the mean of its 30/90-day positive-return shares is at least 55%.
4. If neither qualifies, hold 100% cash. If one qualifies, hold that asset. If both qualify, choose the asset with the larger mean percentile rank across 30-day momentum, 90-day momentum and trend-consistency score.
5. Total exposure is `min(1, 20%/RV30)` using the selected asset's lagged RV30. No volatility-expansion threshold is used.
6. If the selected asset's 90-day drawdown is below -30%, set exposure to zero until the next rebalance.

### Design

- **Features:** MA200 distance, 30/90-day momentum, trend consistency, RV30 and 90-day drawdown.
- **Universe:** BTC, ETH and cash.
- **Frequency:** Four-week.
- **Risk controls:** 20% volatility target, 100% exposure cap, -30% asset drawdown stop-state, cash fallback.
- **Why it may generalize:** very liquid assets, slow signals, low turnover, few degrees of freedom and an intuitive trend mechanism.
- **Why it may fail:** slow exits, whipsaw, concentration, flat returns when cash dominates, and no edge during range-bound markets.
- **Primary baseline:** 50/50 BTC/ETH with the same cost convention.
- **Additional acceptance:** must outperform a simple equal-weight “both above MA200” trend rule on development CPCV; otherwise the rotation step is unnecessary complexity.

## B. Market-gated cross-sectional momentum

### Full rules

1. Rebalance weekly in the point-in-time top-30 universe.
2. Rank assets by 90-day momentum excluding the most recent seven days. Require positive 30-day momentum and dollar-volume history above the universe cutoff.
3. The market gate is favorable only when BTC is above MA200, BTC 30-day momentum is positive, top-10 breadth is at least 50%, market drawdown is above -20% and average 30-day correlation is below 0.80.
4. When favorable, hold the top five qualifying assets at 20% each. Otherwise hold cash.
5. Exclude an asset whose funding z-score is above +2 when at least 90 realized funding observations are available; missing funding does not imply zero funding and is reported separately.

### Design

- **Features:** skip-week momentum, 30-day momentum, BTC MA200/30-day trend, breadth, market drawdown, correlation and funding crowding.
- **Universe:** Point-in-time top 30.
- **Frequency:** Weekly.
- **Risk controls:** hard cash gate, 20% asset cap, funding-crowding exclusion and turnover cap.
- **Why it may generalize:** combines relative continuation with broad risk and participation confirmation.
- **Why it may fail:** conjunctive filters can eliminate exposure, correlations change quickly, and the gate can miss BTC-led recoveries.
- **Primary baseline:** ungated top-five skip-week momentum with identical universe and costs.
- **Additional acceptance:** active exposure must be at least 15% of holdout days; a zero-trade result cannot pass regardless of drawdown.

## C. Dispersion-gated momentum

### Full rules

1. Rebalance biweekly in the point-in-time top-30 universe.
2. Calculate liquidity-weighted cross-sectional return dispersion over seven days, its 7/30-day acceleration ratio and its expanding historical percentile using observations available through `t-1` after a 252-day warm-up.
3. Opportunity is active when dispersion is between its 60th and 95th historical percentiles, dispersion acceleration is positive, top-10 breadth is at least 50%, BTC is above MA200 and average correlation is below 0.80.
4. Rank assets by a fixed 50/50 blend of percentile-ranked `momentum_90_ex_7` and trend consistency. Require positive 30-day momentum.
5. Hold the top five at 20% each while active; otherwise cash. Above the 95th dispersion percentile, hold cash because the state is classified as stress rather than opportunity.
6. If portfolio drawdown reaches -15%, reduce target exposure to 50%; at -25%, move to cash until drawdown recovers above -10%. These levels are fixed and not candidates for tuning.

### Design

- **Features:** dispersion level/percentile/acceleration, average correlation, breadth, BTC MA200, skip-week momentum and trend consistency.
- **Universe:** Point-in-time top 30.
- **Frequency:** Biweekly.
- **Risk controls:** two-sided dispersion gate, market confirmation, 20% asset cap, drawdown schedule and cash.
- **Why it may generalize:** it explicitly conditions cross-sectional momentum on the existence of cross-sectional opportunity while distinguishing orderly differentiation from panic.
- **Why it may fail:** dispersion may be contemporaneous rather than predictive, percentile estimates drift, and the rule may still hold correlated altcoins during rapid crashes.
- **Primary baseline:** the same blended momentum portfolio without the dispersion, breadth or correlation gate.
- **Additional acceptance:** the gate must improve both median outer-fold Sharpe and max drawdown, and must retain at least 20% average exposure.

## D. Residual momentum after BTC/ETH beta removal

### Full rules

1. Rebalance biweekly in the point-in-time top-30 universe; require at least 365 days of asset history.
2. At each decision, fit for each asset an OLS model `r_i=α+β_BTC r_BTC+β_ETH r_ETH+ε_i` using the prior 180 daily observations ending at `t-1`, with at least 120 complete paired observations.
3. Compound residual returns from `t-90` through `t-8`. Rank positive residual momentum within the current universe.
4. Exclude assets with downside BTC beta above 1.5, abnormal-volume z-score below -2 or 30-day median dollar volume below the current top-30 cutoff.
5. Hold the top five at 20% each. If fewer qualify, unused weight remains cash.
6. Scale total exposure to a 30% ex-ante volatility target based on the trailing 60-day covariance matrix, capped at 100%; do not optimize the target.

### Design

- **Features:** rolling BTC/ETH beta, downside beta, residual skip-week momentum, abnormal volume, liquidity and covariance.
- **Universe:** Point-in-time top 30 with 365-day history.
- **Frequency:** Biweekly.
- **Risk controls:** beta-risk exclusion, liquidity screen, covariance-based scaling, asset cap and cash.
- **Why it may generalize:** removes the dominant common crypto factor and tests continuation in asset-specific information.
- **Why it may fail:** factor betas are unstable, ETH and BTC may not span the common factor, and residual estimates can be noisy for changing token economics.
- **Primary baseline:** raw skip-week momentum under identical universe, frequency and risk controls.
- **Additional acceptance:** median cross-sectional rank IC must be positive in at least 60% of outer folds before portfolio performance is considered.

## E. Volatility breakout with market-state filter

### Full rules

1. Rebalance weekly in the point-in-time top-10 universe.
2. An asset breaks out when its prior close exceeds the maximum high of the preceding 20 completed days, RV20 exceeds RV60 and prior-day volume is at least 1.5 times its trailing 20-day median.
3. The market-state filter requires BTC above MA200, top-10 breadth at least 50%, average 30-day correlation below 0.85 and market drawdown above -20%.
4. Rank valid assets by breakout margin multiplied by clipped volume expansion. Hold up to five at a 20% cap; otherwise cash.
5. The fixed volatility-expansion probability is used only for continuous sizing: multiplier `clip(0.5/p, 0.25, 1)` where `p` is the frozen probability. It does not activate or reject trades.
6. Apply a 25% portfolio volatility target and a fixed drawdown brake: 50% exposure below -15% and cash below -25%.

### Design

- **Features:** breakout margin, RV20/RV60, volume expansion, BTC MA200, breadth, correlation, market drawdown and fixed volatility probability.
- **Universe:** Point-in-time top 10.
- **Frequency:** Weekly.
- **Risk controls:** market-state filter, continuous risk forecast sizing, volatility target, drawdown brake, asset cap and cash.
- **Why it may generalize:** the base breakout has the strongest prior standalone evidence and low turnover; the filter uses broad mechanisms rather than an event-level ML classifier.
- **Why it may fail:** it is vulnerable to post-hoc rescue of a previously weak holdout, the filter may remove rare winning breakouts, and high volatility is not directional.
- **Primary baseline:** identical standalone breakout without the market-state filter or forecast sizing.
- **Additional acceptance:** paired holdout Sharpe-delta bootstrap lower bound must be above zero; point-estimate improvement is insufficient because this candidate follows earlier breakout research.

## Configuration accounting

The five specifications are five primary configurations. Each baseline, cost level, universe sensitivity, timing sensitivity, ablation and alternative data definition is also counted. None may replace a failed primary because it performs better in the prospective holdout. Candidate C is recommended first in `final_next_step.md`; the other four remain registered but dormant until that test is concluded.

