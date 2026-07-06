# Signal-engineering library

## Purpose

These are transparent base signals, not ML predictions and not tested recommendations. A model may size or filter a signal only after the base rule has independent walk-forward evidence. Every signal uses data ending at `t-1`, trades after the rebalance decision and holds cash when no asset qualifies.

## Signal definitions

### 1. BTC/ETH trend-following

- **Economic rationale:** persistent adoption, flows and slow-moving risk appetite can create medium-horizon trends in the two deepest crypto assets.
- **Exact rule:** at each Friday close, an asset is eligible when `P(t-1)>MA200(t-1)`, 30-day momentum is positive and 90-day momentum is positive. If both qualify, weight equally; if one qualifies, hold that asset; otherwise hold cash. Scale total exposure to a 20% annualized volatility target using trailing 30-day portfolio volatility, capped at 100% and never leveraged.
- **Required features:** distance from MA200, 30/90-day momentum, RV30.
- **Likely environment:** persistent bull or recovery trends; partial protection in prolonged bear markets.
- **Expected failure:** whipsaw near the moving average, abrupt crashes before the slow filter exits, and repeated false recoveries.
- **Difficulty:** Low. Suitable for manual execution.

### 2. Top-asset rotation

- **Economic rationale:** leadership rotates between BTC, ETH and occasionally the most liquid altcoins; holding only positive-trend leaders avoids permanent exposure to laggards.
- **Exact rule:** biweekly, score BTC and ETH by the mean of their cross-sectional ranks in 30-day momentum, 90-day momentum and volatility-adjusted momentum. The winner must have positive 30/90-day momentum and be above MA200. Hold the winner at volatility-targeted exposure; otherwise cash. A separate version may admit a top-10 altcoin only when the risk-off gate below is favorable; that choice must be frozen before testing.
- **Required features:** 30/90-day momentum, volatility-adjusted momentum, MA200, RV30, risk-off gate if alts are admitted.
- **Likely environment:** clear leadership and sustained directional markets.
- **Expected failure:** short-lived leadership changes, concentrated single-asset risk and high turnover if checked too frequently.
- **Difficulty:** Low.

### 3. Cross-sectional momentum

- **Economic rationale:** information diffusion, investor attention and flow persistence can make recent relative winners continue to outperform.
- **Exact rule:** weekly in the point-in-time top-30 by trailing 90-day median dollar volume, rank `momentum_90_ex_7`. Require positive 30-day momentum. Hold the top five qualifying assets, equal weighted with a 20% asset cap. Unused weight remains cash.
- **Required features:** point-in-time liquidity universe, 90-day skip-week momentum, 30-day momentum.
- **Likely environment:** broad risk-on markets with stable cross-sectional leadership.
- **Expected failure:** sharp reversals, one-factor crashes, listing effects, unstable altcoin composition and transaction costs.
- **Difficulty:** Medium because universe history and delistings matter more than the formula.

### 4. Residual momentum

- **Economic rationale:** raw crypto momentum often restates BTC/ETH beta. Asset-specific continuation should be cleaner after common market exposure is removed.
- **Exact rule:** for each eligible asset, estimate `r_i=α+β_BTC r_BTC+β_ETH r_ETH+ε_i` using the 180 daily observations ending at `t-1`, requiring at least 120 paired observations. Compound residual returns from `t-90` through `t-8`, rank within the top-30 universe, require a positive residual score, and hold the top five with a 20% cap. Re-estimate only at the weekly decision; cash absorbs unused weight.
- **Required features:** rolling BTC/ETH betas, regression residuals, asset age, point-in-time universe.
- **Likely environment:** differentiated sector/asset trends not driven solely by the market factor.
- **Expected failure:** unstable betas, omitted common factors, thin asset histories and residual trends that are not executable after costs.
- **Difficulty:** Medium.

### 5. Volatility breakout

- **Economic rationale:** a new high accompanied by expanding volatility and participation can mark a transition from compression to directional price discovery.
- **Exact rule:** weekly, signal when `P(t-1)` exceeds the maximum high from `t-21` through `t-2`, RV20 exceeds RV60 and volume is at least 1.5 times its trailing 20-day median ending `t-2`. Rank positive breakout margins and hold up to five assets at a 20% cap until the next rebalance. No signal means cash.
- **Required features:** prior 20-day high, RV20/RV60, volume expansion, point-in-time universe.
- **Likely environment:** early trend expansion after consolidation.
- **Expected failure:** exhaustion gaps, manipulated volume, one-day spikes and bear-market relief rallies.
- **Difficulty:** Low–medium.

### 6. Reversal after capitulation

- **Economic rationale:** forced deleveraging can temporarily push liquid assets below prices justified by ordinary volatility; a breadth reversal can confirm exhaustion.
- **Exact rule:** an asset becomes a candidate when its 7-day reversal z-score is below -2, its abnormal dollar volume z-score is above 2 and its 90-day drawdown is below -25%. Enter only after top-10 breadth improves by at least 10 percentage points over the following completed week and the asset closes above its 5-day moving average. Hold for one week, cap each asset at 20%, and hold cash otherwise.
- **Required features:** reversal z-score, abnormal volume, drawdown, breadth acceleration, MA5.
- **Likely environment:** panic followed by stabilization.
- **Expected failure:** catching a continuing collapse, exchange-specific distress, delisting and repeated entries during structural impairment.
- **Difficulty:** Medium; the confirmation delay and event timestamps require care.

### 7. Risk-off cash gate

- **Economic rationale:** long-only crypto strategies share large downside beta; avoiding hostile market states may matter more than fine asset ranking.
- **Exact rule:** risk-on requires BTC above MA200, BTC 30-day momentum positive, top-10 breadth above 50%, market drawdown above -20%, and average 30-day correlation below 0.80. If any condition fails, new altcoin entries are prohibited and the portfolio moves to cash subject to the turnover cap. The fixed volatility-expansion probability may scale risk continuously but must not change the gate threshold.
- **Required features:** BTC trend, breadth, market drawdown, average correlation, optional frozen volatility probability.
- **Likely environment:** avoids broad bear trends and one-factor panic.
- **Expected failure:** conjunctive gates can eliminate nearly all exposure, enter late and miss V-shaped recoveries.
- **Difficulty:** Low; threshold-selection risk is high.

### 8. Market-breadth confirmation

- **Economic rationale:** a trend supported by many liquid assets is less dependent on one token and may be more persistent.
- **Exact rule:** a long signal is confirmed only when top-10 breadth is above 50% and its 7-day change is non-negative. Breadth does not create a trade; it confirms a separately defined trend, momentum or breakout signal. If confirmation fails, hold cash for that signal sleeve.
- **Required features:** point-in-time top-10 breadth and breadth acceleration.
- **Likely environment:** broad advances and orderly recoveries.
- **Expected failure:** BTC-led rallies with weak alt participation, denominator changes and late confirmation.
- **Difficulty:** Low.

### 9. Funding-crowding avoidance

- **Economic rationale:** extreme funding indicates crowded directional leverage and asymmetric squeeze/liquidation risk.
- **Exact rule:** calculate each asset's funding z-score from the prior 90 realized funding observations. Reject a long candidate when funding z-score exceeds +2. If normalized OI is available, also reject when absolute funding z-score exceeds 2 and 7-day OI growth exceeds 10%. Negative extreme funding does not automatically create a long trade.
- **Required features:** lagged funding, funding history/coverage; optional USD-normalized OI growth.
- **Likely environment:** leveraged speculative expansions and crowded late trends.
- **Expected failure:** high positive funding can persist during strong bull trends; incomplete derivatives coverage can bias the filter.
- **Difficulty:** Medium with current funding; high with multi-venue OI.

### 10. Dispersion-gated momentum

- **Economic rationale:** cross-sectional ranking has little opportunity when assets move as one factor. Rising dispersion with non-collapsing breadth indicates differentiated leadership that momentum can exploit.
- **Exact rule:** calculate liquidity-weighted 7-day cross-sectional dispersion and its trailing 252-day percentile using only history available at `t-1`. Activate the residual-momentum or skip-week momentum portfolio only when dispersion is between the 60th and 95th historical percentiles, dispersion acceleration is positive, top-10 breadth is at least 50% and BTC is above MA200. Above the 95th percentile, hold cash because dispersion may represent panic rather than opportunity. Rebalance biweekly and cap each asset at 20%.
- **Required features:** dispersion level/percentile/acceleration, breadth, BTC MA200 and momentum score.
- **Likely environment:** differentiated risk-on leadership rather than one-factor rallies or panics.
- **Expected failure:** percentile instability, too few active periods, false distinction between opportunity and stress, and missed low-dispersion trends.
- **Difficulty:** Medium.

## Signal-governance rules

1. No signal is promoted because an ML score is high; it must have a fixed economic rule and standalone accounting.
2. A confirmation or risk gate may suppress a signal but may not reverse it into a short position in this long-only framework.
3. Thresholds above are canonical research definitions. If alternatives are tested, every alternative is a configuration and must be selected inside development CPCV.
4. Cash is an explicit weight, not missing data or a backtest default.
5. Signal returns, active days, rejected opportunities, turnover and capacity are reported before any allocator or meta-model is fitted.

