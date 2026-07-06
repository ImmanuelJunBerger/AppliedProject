# Final recommendation

- 1. Do trend-scanning labels produce better ML targets than fixed forward-return targets? Fixed forward-return targets from earlier modules were not re-optimized in this module; comparison is methodological and based on prior report outcomes plus trend-label diagnostics. Best development trend-label model AUC was 0.646; selected-config holdout AUC was 0.616.
- 2. Does the meta-model improve the primary trend-scanning signal? Selected meta-model: meta_btc_eth_upward_trend__sgd_classifier. The selected strategy result below determines economic usefulness; meta-model inclusion is not promoted unless it survives CPCV and holdout.
- 3. Does trend-scanning improve upside capture? Incremental holdout total return vs frozen was -45.12%.
- 4. Does any trend-scanning strategy beat btc_eth_macro_gate_balanced? No on the predeclared Sharpe/CAGR comparison for the development-selected candidate.
- 5. Does any improvement survive 50 bps costs? No for the development-selected candidate.
- 6. Is the improvement statistically convincing or likely overfit? Not statistically convincing; overfitting risk remains material.
- 7. Should trend-scanning replace, complement, or be rejected relative to the frozen macro strategy? Trend-scanning does not beat the frozen macro strategy after locked-holdout evaluation.

## Recommendation

**Trend-scanning does not beat the frozen macro strategy after locked-holdout evaluation.**

Do not promote a trend-scanning strategy unless it improves economically and statistically.  If the selected development-CPCV candidate fails the guardrails, the frozen macro-regime strategy remains the final candidate.
