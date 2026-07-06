# Final recommendation

## Decision

**keep current strategy**

Development-selected candidate: **simple_equity_vol_equity_momentum**

Reason: The simplified development-selected gate does not clear every robustness condition strongly enough to replace the existing fixed strategy. Keep the current strategy as paper-monitoring only, while recognizing its high PBO.

## Development-selected simplified candidate check

The development-only selector chose **simple_equity_vol_equity_momentum**, but it failed the locked
holdout validation:

- Development Sharpe: 1.500
- Holdout Sharpe: -0.157
- Sharpe retention: -10.49%
- Development CAGR: 72.12%
- Holdout CAGR: -8.93%

The current strategy remains stronger on validation despite higher known
overfitting concern:

- Current development Sharpe: 0.628
- Current holdout Sharpe: 0.970
- Current Sharpe retention: 154.44%
- Current holdout CAGR: 25.07%

## Benchmark comparison at 25 bps

| Strategy | Category | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure | Worst month |
|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | selected_fixed_strategy | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | -5.98% |
| u10_r7_momentum_63d_k3_balanced_v4_reduced_momentum | prior_tier1_regime_momentum | 4.88% | 0.313 | 0.322 | -26.35% | 0.185 | 16.586 | 26.76% | -8.60% |
| simple_equity_vol_equity_momentum | v3_selected_simplified | -8.93% | -0.157 | -0.193 | -40.08% | -0.223 | 9.159 | 47.86% | -12.38% |
| eth_buy_hold | simple_crypto_beta | -35.10% | -0.239 | -0.356 | -67.52% | -0.520 | 0.000 | 100.00% | -32.21% |
| btc_eth_50_50 | simple_crypto_beta | -27.21% | -0.285 | -0.410 | -59.21% | -0.459 | 0.000 | 100.00% | -25.10% |
| btc_buy_hold | simple_crypto_beta | -21.82% | -0.332 | -0.468 | -51.16% | -0.427 | 0.000 | 100.00% | -17.65% |
| equal_weight_top10 | point_in_time_top_universe | -39.25% | -0.418 | -0.619 | -63.51% | -0.618 | 1.493 | 100.00% | -28.25% |

## Selected candidate cost sensitivity

| Candidate | Cost bps | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure |
|---|---|---|---|---|---|---|---|---|
| simple_equity_vol_equity_momentum | 10 | -7.66% | -0.112 | -0.137 | -39.58% | -0.194 | 9.159 | 47.86% |
| simple_equity_vol_equity_momentum | 25 | -8.93% | -0.157 | -0.193 | -40.08% | -0.223 | 9.159 | 47.86% |
| simple_equity_vol_equity_momentum | 50 | -11.00% | -0.233 | -0.285 | -40.91% | -0.269 | 9.159 | 47.86% |
| simple_equity_vol_equity_momentum | 100 | -15.02% | -0.382 | -0.467 | -42.53% | -0.353 | 9.159 | 47.86% |

## Interpretation

The v3 process prefers simplicity and CPCV stability over holdout Sharpe. A
simpler candidate should only replace the current strategy if it was selected
inside development, has lower overfitting risk, and remains economically viable
on the locked holdout. No strategy is promoted purely because it has the highest
holdout Sharpe.
