# Target comparison

## Notation and measurement rules

At decision time \(t\), let \(r_{i,u}\) be the return of asset \(i\) during interval \(u\), \(w_{i,t}\) its point-in-time universe weight, \(h\) the forecast horizon, and \(\mathcal U_t\) the investable universe known at \(t\). All future windows begin after the feature cutoff. Universe membership, weights, thresholds, and normalizers must be frozen using training data only.

Recommended base frequency is hourly measurement aggregated to a daily decision record, with a primary seven-day horizon. Daily data can be used for a lower-cost first pass, but it produces a noisier realized-volatility label.

## Ranked targets

| Rank | Target | Predictability prior | Measurement robustness | Economic usefulness | Main failure mode |
|---:|---|---|---|---|---|
| 1 | A. Future realized volatility | High | High for liquid assets | High | A sophisticated model merely rediscovers volatility persistence |
| 2 | B. Future drawdown probability | Medium | Medium | Very high | Rare events, overlapping labels, poor probability calibration |
| 3 | C. Future market dispersion | Medium | Medium–high | High | Universe changes and microcap noise |
| 4 | D. Future correlation regime | Medium | Medium | High | Noisy covariance estimates and unstable regime definitions |
| 5 | E. Future breadth expansion | Medium–low | Medium | Medium–high | Threshold sensitivity and asset-list survivorship |
| 6 | F. Future opportunity score | Unknown | Low unless externally fixed | Potentially high | Composite target embeds the desired answer and creates test-set flexibility |

The ordering reflects probability of finding a stable, deployable forecast—not novelty or maximum hypothetical payoff.

## A. Future realized volatility

### Definition

For an aggregate crypto-market return \(r_{m,u}=\sum_{i\in\mathcal U_t}w_{i,t}r_{i,u}\), define future realized variance from intraday returns as

\[
RV_{t,h}=\sum_{u=t+1}^{t+h}\sum_{k=1}^{K}r^2_{m,u,k},
\qquad
y^{RV}_{t,h}=\log(RV_{t,h}+\epsilon).
\]

The preferred expansion target removes the current volatility level:

\[
y^{\Delta RV}_{t,h}=\log\left(\frac{RV_{t,h}+\epsilon}{RV^{past}_{t,L}+\epsilon}\right).
\]

Use five-minute or hourly returns for the label where reliable, with jump-robust realized measures as sensitivity checks. A secondary classification target is \(1[y^{\Delta RV}_{t,h}>q_{0.75,train}]\).

### Intuition and relative predictability

Volatility clusters because information arrival, leverage, liquidity, positioning, and risk limits evolve more slowly than returns. Lagged volatility is therefore informative; funding/open interest, implied volatility, liquidation pressure and liquidity may add information about the next volatility state. Unlike the sign of a return, the magnitude of movement has strong persistence.

### Monetization

- Scale gross exposure or risk budgets.
- Choose cash buffers and execution urgency.
- Time or size option hedges where derivatives are permitted.
- Raise margin/liquidity reserves and reduce concentration before predicted expansion.

The forecast can create value without predicting direction.

## B. Future drawdown probability

### Definition

For cumulative aggregate return \(R_{t,k}=\prod_{u=t+1}^{t+k}(1+r_{m,u})-1\), define

\[
y^{DD}_{t,h,d}=1\left[\min_{1\le k\le h}R_{t,k}\le-d\right],
\]

where \(d\) is a loss threshold selected before the holdout, for example 10%. A continuous alternative is maximum future drawdown:

\[
MDD_{t,h}=\min_{1\le k\le h}\left(\frac{V_{t+k}}{\max_{0\le j\le k}V_{t+j}}-1\right).
\]

### Intuition and relative predictability

Drawdowns can be preceded by high leverage, negative skew, basis inversion, liquidity deterioration, exchange inflows, concentrated correlation, and weakening breadth. The target is still partly directional and much rarer than high volatility, so it is less statistically stable.

### Monetization

Use calibrated probability to reduce risk, increase cash, cap position concentration, or buy protection. Evaluate Brier score, log loss, calibration slope, precision–recall AUC, and expected loss avoided—not accuracy.

## C. Future market dispersion

### Definition

Cross-sectional realized dispersion at interval \(u\) is

\[
D_u=\sqrt{\sum_{i\in\mathcal U_t}w_{i,t}(r_{i,u}-r_{m,u})^2}.
\]

The target is

\[
y^{DISP}_{t,h}=\log\left(\frac{h^{-1}\sum_{u=t+1}^{t+h}D_u+\epsilon}{L^{-1}\sum_{u=t-L+1}^{t}D_u+\epsilon}\right).
\]

Calculate on a point-in-time top-liquidity universe with caps on individual weights. Report both equal-weight and liquidity-weight variants.

### Intuition and relative predictability

Sector narratives, protocol-specific activity, token unlocks, dominance shifts, and heterogeneous leverage can create persistent relative movement. Dispersion is an absolute cross-sectional magnitude, so it avoids predicting which asset wins. It is less persistent and more universe-sensitive than aggregate volatility.

### Monetization

Determine whether the environment can support cross-sectional selection, market-neutral relative-value research, or broader/narrower risk budgets. For a long-only system, high forecast dispersion can justify stronger selection and tighter concentration limits; it does not by itself identify winners.

## D. Future correlation regime

### Definition

Estimate a shrinkage correlation matrix \(\hat\rho_{t,h}\) from future returns and define average pairwise correlation

\[
\bar\rho_{t,h}=\frac{2}{N_t(N_t-1)}\sum_{i<j}\hat\rho_{ij,t,h}.
\]

The continuous target is \(y^{CORR}_{t,h}=\bar\rho_{t,h}\). A regime target is

\[
z^{CORR}_{t,h}=1[\bar\rho_{t,h}>q_{0.75,train}],
\]

where the threshold is set inside the training window. Alternatives include the first eigenvalue share or network density.

### Intuition and relative predictability

Correlation rises when a common risk factor, leverage unwind, or liquidity shock dominates idiosyncratic information. Current breadth, dominance, funding dispersion, stablecoin stress, and network concentration may precede this state. Sampling error is significant when \(N\) is large relative to \(h\).

### Monetization

Adjust diversification assumptions, portfolio concentration, hedge ratios, scenario shocks, and risk limits. A predicted high-correlation regime is especially valuable because nominal asset count overstates true diversification.

## E. Future breadth expansion

### Definition

For a fixed trend rule known at \(t\), such as price above its 50-day moving average, define breadth

\[
B_u=\frac{1}{N_u}\sum_{i\in\mathcal U_u}1[P_{i,u}>MA^{50}_{i,u}].
\]

The continuous expansion target is

\[
y^{BR}_{t,h}=B_{t+h}-B_t,
\]

and a classification version is \(1[y^{BR}_{t,h}>\delta]\), with \(\delta\) fixed from training data. A return-based breadth definition—share of assets with positive trailing returns—should be a pre-declared robustness check.

### Intuition and relative predictability

Breadth can diffuse as liquidity moves from the largest assets into the cross-section. Stablecoin flows, BTC dominance, volume participation, correlation and dispersion may reveal that transition. It is more stable than choosing individual winners, but its moving-average and universe definitions introduce discretion.

### Monetization

Control the number of active positions, shift between cap-weight and equal-weight exposure, or gate altcoin risk. High breadth without sufficient liquidity is not deployable opportunity.

## F. Future opportunity score

### Definition

One defensible pre-specified score is

\[
O_{t,h}=z(DISP_{t,h})+z(RV_{t,h})-z(\bar\rho_{t,h})-z(COST_{t,h}),
\]

where each \(z(\cdot)\) uses training-window robust location/scale and \(COST\) is a liquidity/slippage proxy. The score says that opportunity is greater when movement and dispersion are high, co-movement is lower, and capacity costs are lower.

### Intuition and relative predictability

It aligns the statistical target with a research-allocation decision. However, weights, transforms, horizons and cost proxies can be changed until a preferred result appears. Its components should first be forecast separately.

### Monetization

Allocate research attention, strategy risk, turnover budget, or the number of assets traded. It is unsuitable as the first primary target because an attractive score is not proof that any implementable strategy captures it.

## Required baselines and acceptance criteria

For every target, compare:

1. unconditional historical mean or class rate;
2. persistence / last observation;
3. target-specific econometric baseline (HAR-RV for volatility, shrinkage covariance for correlation, autoregressive breadth/dispersion);
4. price-only regularized linear and boosted-tree models;
5. the same model plus one alternative-data block at a time.

An alternative-data block is useful only if it improves median rolling-fold loss, remains directionally useful across regimes and assets, survives an untouched holdout, and improves the intended risk decision after data and execution costs. Multiple targets and feature families must be counted as tested configurations.

## Recommendation from the target comparison

Use **seven-day market realized-volatility expansion** as the primary research target. Retain calibrated 30-day drawdown probability and seven-day dispersion as secondary, separately scored tasks. Do not begin with the opportunity score; construct it only after its components demonstrate independent out-of-sample skill.
