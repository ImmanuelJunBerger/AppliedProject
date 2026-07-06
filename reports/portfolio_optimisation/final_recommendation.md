# Final recommendation

1. **Can portfolio construction improve the frozen strategy without changing alpha?** Point estimates can improve in some cells, but the development-selected method does not pass all statistical/economic filters.
2. **Which allocation method performs best?** Development-only CPCV selected **inverse_volatility__btc_eth__static**.
3. **Does Kelly sizing improve performance or increase instability?** Kelly variants are reported in `performance_comparison.md`; accept only if they clear turnover, exposure, PBO and DSR filters.
4. **Does HRP or ERC outperform volatility targeting?** See method ranking; no method replaces the frozen implementation unless all filters pass.
5. **Is any improvement statistically convincing?** No.
6. **Does any method improve Sharpe while maintaining comparable CAGR and exposure?** No.
7. **Would any portfolio construction method replace the current implementation?** No.

Final conclusion: **No portfolio-construction method provides statistically and economically convincing improvement; keep the original frozen portfolio construction unchanged.**

This is a capital-allocation study, not evidence of better alpha.
