# Final recommendation

## Does liquidity/risk shock alpha improve on prior approaches?

No. The selected liquidity-shock rule did not improve locked-holdout trading
performance versus the best prior defensive result, BTC buy-and-hold, or pure
cross-sectional momentum on a risk-adjusted basis.

Selected liquidity-shock holdout Sharpe: -0.529.
Pure cross-sectional momentum holdout Sharpe: -0.412.
BTC buy-and-hold holdout Sharpe: -0.332.

- Tier-1 regime momentum selected holdout Sharpe was 0.313 and did not pass paper-trading criteria.
- Previous defensive candidates also failed the declared paper-trading criteria.
- Volatility forecast trading overlays previously failed to provide robust economic value after costs.
- Derivatives/funding signals did not produce a sufficiently robust paper-trading candidate.

## Paper-trading decision

Do not recommend paper trading.

## Why

- Acceptance pass: No
- Failures: holdout Sharpe <= 0.5; holdout CAGR <= 0; does not survive 50 bps
- PBO: 11.43%
- Deflated Sharpe probability: 0.05%
- Predictive diagnostics are not strong enough: development CPCV AUCs are close
  to random for most targets, and holdout classifier performance is mixed.

If the strategy predicts some shock/target relationships but fails after costs,
the correct conclusion is that the shock signal is not yet economically useful.
