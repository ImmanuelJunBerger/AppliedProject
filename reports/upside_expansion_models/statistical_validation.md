# Statistical validation

## Family-level PBO

| Family | Selected candidate | PBO |
|---|---|---|
| convex | convex_upside_t40_14d | 61.43% |
| relative | relative_winner_e60_b60_7d | 77.14% |
| transition | regime_transition_t40_7d | 60.00% |
| cross_sectional | cross_sectional_top3_t40_7d | 60.00% |
| combined | combined_cross_sectional_relative_transition_7d | 60.00% |

## Final candidate controls

- Final candidate: **combined_cross_sectional_relative_transition_7d**
- Deflated Sharpe probability: 14.01%
- PBO reference used for final decision: 77.14%
- Replacement/complement criteria passed: No

## Independent family guardrails

| Family | Candidate | Holdout Sharpe | Holdout CAGR | Max DD | Turnover | Exposure | PBO | DSR probability | Passes |
|---|---|---|---|---|---|---|---|---|---|
| convex | convex_upside_t40_14d | 1.175 | 33.32% | -23.01% | 8.820 | 33.83% | 61.43% | 18.12% | No |
| combined | combined_cross_sectional_relative_transition_7d | 1.049 | 28.66% | -20.18% | 12.449 | 30.25% | 60.00% | 14.01% | No |
| transition | regime_transition_t40_7d | 1.019 | 27.02% | -20.32% | 11.194 | 30.25% | 60.00% | 13.26% | No |
| relative | relative_winner_e60_b60_7d | 0.979 | 25.50% | -18.04% | 11.126 | 28.95% | 77.14% | 12.22% | No |
| cross_sectional | cross_sectional_top3_t40_7d | 0.970 | 25.07% | -18.42% | 10.177 | 28.95% | 60.00% | 11.94% | No |

## Selected family holdouts

| Family | Candidate | CAGR | Sharpe | Max DD | Turnover | Exposure |
|---|---|---|---|---|---|---|
| convex | convex_upside_t40_14d | 33.32% | 1.175 | -23.01% | 8.820 | 33.83% |
| combined | combined_cross_sectional_relative_transition_7d | 28.66% | 1.049 | -20.18% | 12.449 | 30.25% |
| transition | regime_transition_t40_7d | 27.02% | 1.019 | -20.32% | 11.194 | 30.25% |
| relative | relative_winner_e60_b60_7d | 25.50% | 0.979 | -18.04% | 11.126 | 28.95% |
| cross_sectional | cross_sectional_top3_t40_7d | 25.07% | 0.970 | -18.42% | 10.177 | 28.95% |
