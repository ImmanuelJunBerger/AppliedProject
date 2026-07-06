# Final recommendation

## Final questions

1. **Does expansion-first outperform macro-first?** Raw Sharpe is slightly higher (0.993 vs frozen 0.970), but it fails replacement filters: No.
2. **Does hybrid outperform both?** Raw holdout Sharpe/CAGR/drawdown improve, but replacement filters passed: No. Hybrid selected holdout Sharpe: 1.168.
3. **Which source of alpha contributes most?** By model-importance proxy: Expansion Tier-1 crypto-native.
4. **Does risk management add value after alpha generation?** See `risk_management_comparison.md`; value is accepted only if development-selected candidates survive holdout and economic filters.
5. **Single best selected strategy by raw selected holdout Sharpe:** hybrid__btc_eth_only__confidence_weight__vol_target.
6. **Would any strategy replace btc_eth_macro_gate_balanced?** No.
7. **Final Applied Project strategy:** btc_eth_macro_gate_balanced.

## Best selected candidate by metric

| Criterion | Candidate | Value |
|---|---|---:|
| Highest Sharpe | hybrid__btc_eth_only__confidence_weight__vol_target | 1.168 |
| Highest CAGR | hybrid__btc_eth_only__confidence_weight__vol_target | 25.28% |
| Best drawdown | expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | -7.41% |
| Lowest turnover | expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate | 5.480 |
| Highest acceptable exposure | hybrid__btc_eth_only__confidence_weight__vol_target | 16.86% |

## Conclusion

Expansion-first/hybrid does not replace the macro-regime result; the project core remains Macro-Regime Conditioning for Systematic Cryptocurrency Allocation.
