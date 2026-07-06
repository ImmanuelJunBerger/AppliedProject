# Final recommendation

## Answers

1. Best predictive family: **transition** via `risk_off_to_risk_on_2_4w__gradient_boosting`.
2. Best economic family, as an ex-post holdout diagnostic among development-selected family winners: **convex** via `convex_upside_t40_14d`.
3. Upside detection complements the macro risk gate only if it improves economics without becoming a low-exposure cash strategy.
4. Final candidate: **combined_cross_sectional_relative_transition_7d**.
5. Paper-monitoring status: **upside detection has partial evidence but fails full replacement criteria**.
6. Expansion-specific feature discovery: **20** feature(s) reached Expansion Tier 1 under diagnostic rules; none were inserted into the current final overlay.

## Recommendation

Do not modify or replace **btc_eth_macro_gate_balanced** based on this module. A standalone
family overlay may be paper-monitored only if it passes the independent
guardrails above; the combined overlay must pass separately before it can be
treated as a candidate complement.
