# Final recommendation

## Does risk-aware RL produce genuine economic value?

The selected RL policy does not show genuine economic value.

Selected holdout Sharpe: -0.239.
Selected holdout CAGR: -35.10%.
Acceptance pass: No.
Failures: holdout Sharpe <= 0.5; holdout CAGR <= 0; max drawdown not better than BTC; does not survive 50 bps.
Dominant holdout action: eth (100.00% of evaluated days).

## Interpretation

- PBO: 0.00%.
- Deflated Sharpe probability: 0.66%.
- The policy was selected using development-only CPCV, not holdout performance.
- The selected policy effectively collapses to the dominant holdout action above,
  so it is not evidence that RL learned robust dynamic risk control.
- Risk-aware reward variants did not beat the raw-return selected policy in a
  way that translated to the locked holdout.
- If development performance is materially stronger than holdout performance,
  the correct interpretation is development-period overfitting rather than
  validated RL alpha.

## Decision

Do not paper trade with capital. Risk-aware RL did not clear the locked-holdout criteria.
