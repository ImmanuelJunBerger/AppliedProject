# Overlay comparison

Positive delta maximum drawdown means a less severe drawdown. Each overlay is compared with its standalone base; regime switching uses standalone volatility breakout as its declared reference.

## Holdout deltas across costs

| Cost bps | Overlay | Reference | Delta Sharpe | Delta Sortino | Delta CAGR | Delta max DD | Delta Calmar | Delta turnover |
|---|---|---|---|---|---|---|---|---|
| 10 | breakout_activation | standalone_volatility_breakout | -1.035 | -0.295 | -5.48% | 3.41% | -0.741 | -0.91% |
| 25 | breakout_activation | standalone_volatility_breakout | -0.997 | -0.259 | -4.97% | 3.53% | -0.680 | -0.91% |
| 50 | breakout_activation | standalone_volatility_breakout | -0.935 | -0.198 | -4.13% | 3.71% | -0.584 | -0.91% |
| 100 | breakout_activation | standalone_volatility_breakout | -0.811 | -0.082 | -2.47% | 4.02% | -0.419 | -0.91% |
| 10 | breakout_risk_off_sizing | standalone_volatility_breakout | 0.034 | 0.026 | 0.27% | 1.50% | 0.042 | -0.13% |
| 25 | breakout_risk_off_sizing | standalone_volatility_breakout | 0.034 | 0.025 | 0.34% | 1.54% | 0.037 | -0.13% |
| 50 | breakout_risk_off_sizing | standalone_volatility_breakout | 0.035 | 0.021 | 0.45% | 1.61% | 0.030 | -0.13% |
| 100 | breakout_risk_off_sizing | standalone_volatility_breakout | 0.037 | 0.016 | 0.67% | 1.74% | 0.018 | -0.13% |
| 10 | breakout_volatility_targeted | standalone_volatility_breakout | 0.093 | 0.077 | 0.84% | 1.74% | 0.110 | -0.06% |
| 25 | breakout_volatility_targeted | standalone_volatility_breakout | 0.092 | 0.071 | 0.86% | 1.77% | 0.096 | -0.06% |
| 50 | breakout_volatility_targeted | standalone_volatility_breakout | 0.089 | 0.059 | 0.91% | 1.82% | 0.076 | -0.06% |
| 100 | breakout_volatility_targeted | standalone_volatility_breakout | 0.085 | 0.038 | 0.99% | 1.91% | 0.044 | -0.06% |
| 10 | trend_risk_off_sizing | standalone_trend_following | 0.105 | 0.065 | 15.10% | 20.66% | 0.063 | -1.24% |
| 25 | trend_risk_off_sizing | standalone_trend_following | 0.092 | 0.048 | 15.32% | 20.69% | 0.060 | -1.24% |
| 50 | trend_risk_off_sizing | standalone_trend_following | 0.072 | 0.023 | 15.67% | 20.70% | 0.055 | -1.24% |
| 100 | trend_risk_off_sizing | standalone_trend_following | 0.031 | -0.027 | 16.26% | 20.62% | 0.051 | -1.24% |
| 10 | trend_volatility_targeted | standalone_trend_following | 0.254 | 0.217 | 14.01% | 18.21% | 0.075 | -0.48% |
| 25 | trend_volatility_targeted | standalone_trend_following | 0.242 | 0.199 | 13.91% | 17.89% | 0.068 | -0.48% |
| 50 | trend_volatility_targeted | standalone_trend_following | 0.221 | 0.172 | 13.75% | 17.37% | 0.059 | -0.48% |
| 100 | trend_volatility_targeted | standalone_trend_following | 0.181 | 0.117 | 13.40% | 16.36% | 0.048 | -0.48% |
| 10 | volatility_regime_switching | standalone_volatility_breakout | -0.123 | -0.077 | -2.45% | -4.70% | -0.184 | 1.57% |
| 25 | volatility_regime_switching | standalone_volatility_breakout | -0.132 | -0.098 | -3.27% | -4.56% | -0.214 | 1.57% |
| 50 | volatility_regime_switching | standalone_volatility_breakout | -0.148 | -0.132 | -4.60% | -4.57% | -0.260 | 1.57% |
| 100 | volatility_regime_switching | standalone_volatility_breakout | -0.182 | -0.201 | -7.11% | -7.81% | -0.245 | 1.57% |

## Paired holdout Sharpe uncertainty at 25 bps

| Overlay | Reference | 2.5% | Median | 97.5% |
|---|---|---|---|---|
| breakout_risk_off_sizing | standalone_volatility_breakout | -0.042 | 0.036 | 0.101 |
| breakout_activation | standalone_volatility_breakout | -2.345 | -0.892 | 0.715 |
| breakout_volatility_targeted | standalone_volatility_breakout | -0.053 | 0.067 | 0.265 |
| trend_risk_off_sizing | standalone_trend_following | -0.393 | 0.080 | 0.498 |
| trend_volatility_targeted | standalone_trend_following | -0.182 | 0.235 | 0.642 |
| volatility_regime_switching | standalone_volatility_breakout | -1.465 | -0.141 | 1.390 |

## Development-only CPCV selection audit

`overlay_selection.csv` contains every predeclared candidate, its CPCV score, and the selected flag. There are no holdout-return columns in that file.
