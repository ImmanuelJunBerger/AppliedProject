# Development-only candidate selection

The grid below was declared in code before evaluation. CPCV uses five chronological groups with two held-out groups per path, one-week label purging, and one-week embargo. Only development returns enter the ranking.

Rule families are fixed as follows:

- A requires BTC above its lagged 200-day average, positive BTC 30-day momentum, top-10 breadth above 50%, acceptable market drawdown, and volatility probability below its declared gate; otherwise it holds cash.
- B selects only BTC or ETH when lagged 30/90-day trends and drawdown are acceptable, then volatility-scales the selected asset.
- C holds the top momentum assets at 0%, 50%, or 100% confidence exposure before volatility targeting and the declared drawdown brake.
- D trades only BTC/ETH on biweekly or four-week intervals. The volatility forecast is used as a continuous sizing multiplier only; no forecast threshold filters trades.

Family winners:

- **A_market_gated_momentum:** A_market_gate_k5_dd20_vp65
- **B_defensive_top_asset_rotation:** B_defensive_rotation_dd25_vp70_vt35
- **C_momentum_cash_floor:** C_cash_floor_k5_vt35_brake10
- **D_low_turnover_btc_eth_trend:** D_btc_eth_biweekly_vt25

Overall primary candidate: **D_btc_eth_biweekly_vt25**.

| Candidate | Family | Median CPCV Sharpe | Worst fold | Positive folds | Development Sharpe | Development CAGR | Development max DD | Exposure | Family winner | Primary |
|---|---|---|---|---|---|---|---|---|---|---|
| A_market_gate_k5_dd20_vp65 | A_market_gated_momentum | 0.885 | 0.000 | 70.00% | 1.089 | 40.29% | -32.37% | 10.88% | Yes | No |
| A_market_gate_k5_dd20_vp75 | A_market_gated_momentum | 0.885 | 0.000 | 70.00% | 1.068 | 39.52% | -32.37% | 11.17% | No | No |
| A_market_gate_k3_dd20_vp75 | A_market_gated_momentum | 0.730 | 0.000 | 70.00% | 0.796 | 19.71% | -27.24% | 6.90% | No | No |
| A_market_gate_k3_dd20_vp65 | A_market_gated_momentum | 0.685 | 0.000 | 70.00% | 0.780 | 18.94% | -27.24% | 6.67% | No | No |
| A_market_gate_k5_dd10_vp65 | A_market_gated_momentum | 0.675 | 0.000 | 70.00% | 0.892 | 24.29% | -25.49% | 6.16% | No | No |
| A_market_gate_k5_dd10_vp75 | A_market_gated_momentum | 0.675 | 0.000 | 70.00% | 0.864 | 23.60% | -25.49% | 6.45% | No | No |
| A_market_gate_k3_dd10_vp75 | A_market_gated_momentum | 0.379 | 0.000 | 70.00% | 0.527 | 9.68% | -23.75% | 4.14% | No | No |
| A_market_gate_k3_dd10_vp65 | A_market_gated_momentum | 0.326 | 0.000 | 70.00% | 0.504 | 8.97% | -23.75% | 3.91% | No | No |
| B_defensive_rotation_dd25_vp70_vt35 | B_defensive_top_asset_rotation | 0.458 | -0.054 | 90.00% | 1.148 | 19.83% | -19.40% | 13.48% | Yes | No |
| B_defensive_rotation_dd25_vp70_vt25 | B_defensive_top_asset_rotation | 0.381 | -0.055 | 90.00% | 1.145 | 14.48% | -14.44% | 9.96% | No | No |
| B_defensive_rotation_dd25_vp80_vt35 | B_defensive_top_asset_rotation | 0.107 | -0.217 | 70.00% | 0.958 | 17.32% | -27.58% | 15.82% | No | No |
| B_defensive_rotation_dd15_vp80_vt25 | B_defensive_top_asset_rotation | 0.097 | -1.080 | 50.00% | 0.199 | 1.08% | -12.77% | 2.11% | No | No |
| B_defensive_rotation_dd15_vp80_vt35 | B_defensive_top_asset_rotation | 0.089 | -1.026 | 50.00% | 0.197 | 1.37% | -16.47% | 2.99% | No | No |
| B_defensive_rotation_dd25_vp80_vt25 | B_defensive_top_asset_rotation | 0.087 | -0.329 | 70.00% | 0.943 | 12.41% | -21.30% | 11.47% | No | No |
| B_defensive_rotation_dd15_vp70_vt25 | B_defensive_top_asset_rotation | -0.339 | -1.091 | 40.00% | 0.145 | 0.72% | -13.05% | 1.97% | No | No |
| B_defensive_rotation_dd15_vp70_vt35 | B_defensive_top_asset_rotation | -0.348 | -1.038 | 40.00% | 0.142 | 0.87% | -16.95% | 2.80% | No | No |
| C_cash_floor_k5_vt35_brake10 | C_momentum_cash_floor | 0.749 | -1.843 | 70.00% | 0.819 | 9.71% | -21.22% | 8.58% | Yes | No |
| C_cash_floor_k5_vt25_brake10 | C_momentum_cash_floor | 0.577 | -1.496 | 80.00% | 0.695 | 6.48% | -17.58% | 7.12% | No | No |
| C_cash_floor_k5_vt35_brake20 | C_momentum_cash_floor | 0.570 | -1.681 | 80.00% | 0.722 | 9.58% | -27.03% | 10.43% | No | No |
| C_cash_floor_k5_vt25_brake20 | C_momentum_cash_floor | 0.467 | -1.714 | 80.00% | 0.631 | 6.64% | -21.96% | 8.74% | No | No |
| C_cash_floor_k3_vt35_brake10 | C_momentum_cash_floor | 0.205 | -1.562 | 70.00% | 0.296 | 2.89% | -19.20% | 8.10% | No | No |
| C_cash_floor_k3_vt25_brake20 | C_momentum_cash_floor | 0.193 | -1.334 | 60.00% | 0.235 | 2.01% | -18.23% | 8.03% | No | No |
| C_cash_floor_k3_vt25_brake10 | C_momentum_cash_floor | 0.192 | -1.638 | 60.00% | 0.224 | 1.58% | -16.53% | 5.86% | No | No |
| C_cash_floor_k3_vt35_brake20 | C_momentum_cash_floor | 0.031 | -1.618 | 50.00% | 0.149 | 1.10% | -25.96% | 9.26% | No | No |
| D_btc_eth_biweekly_vt25 | D_low_turnover_btc_eth_trend | 1.011 | 0.629 | 100.00% | 1.011 | 17.96% | -21.99% | 16.65% | Yes | Yes |
| D_btc_eth_biweekly_vt35 | D_low_turnover_btc_eth_trend | 0.975 | 0.532 | 100.00% | 1.001 | 24.02% | -29.84% | 22.55% | No | No |
| D_btc_eth_monthly_vt25 | D_low_turnover_btc_eth_trend | 0.654 | 0.345 | 100.00% | 0.623 | 10.95% | -29.94% | 16.98% | No | No |
| D_btc_eth_monthly_vt35 | D_low_turnover_btc_eth_trend | 0.648 | 0.345 | 100.00% | 0.595 | 13.23% | -40.30% | 23.16% | No | No |
