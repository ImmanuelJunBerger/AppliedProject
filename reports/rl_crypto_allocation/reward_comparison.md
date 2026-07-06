# Reward comparison

Rows are grouped by model and reward function. Selection is based on development
CPCV only.

| Model | Reward | Configs | Median CPCV Sharpe | Best CPCV Sharpe | Median development Sharpe |
|---|---|---|---|---|---|
| fitted_q_linear | raw_return | 4 | 1.209 | 1.658 | 1.193 |
| fitted_q_linear | adaptive_risk_control | 4 | 1.030 | 1.640 | 1.214 |
| fitted_q_linear | return_minus_drawdown | 4 | 0.942 | 1.640 | 1.193 |
| fitted_q_linear | return_minus_turnover | 4 | 1.209 | 1.640 | 1.193 |
| fitted_q_linear | return_minus_volatility | 4 | 1.183 | 1.640 | 1.203 |
| tabular_q | adaptive_risk_control | 4 | 0.752 | 0.990 | 4.650 |
| tabular_q | raw_return | 4 | 0.702 | 0.990 | 4.431 |
| tabular_q | return_minus_drawdown | 4 | 0.702 | 0.990 | 4.528 |
| tabular_q | return_minus_turnover | 4 | 0.702 | 0.990 | 4.461 |
| tabular_q | return_minus_volatility | 4 | 0.702 | 0.990 | 4.563 |

## Top selected configurations

| Candidate | Universe | Rebalance | Model | Reward | Median fold Sharpe | Worst fold Sharpe | Development Sharpe | Development turnover |
|---|---|---|---|---|---|---|---|---|
| rl_fitted_q_linear_btc_eth_r14_raw_return | btc_eth | 14 | fitted_q_linear | raw_return | 1.658 | -0.692 | 1.193 | 0.200 |
| rl_fitted_q_linear_btc_eth_r14_return_minus_volatility | btc_eth | 14 | fitted_q_linear | return_minus_volatility | 1.640 | -0.692 | 1.193 | 0.200 |
| rl_fitted_q_linear_btc_eth_r14_return_minus_drawdown | btc_eth | 14 | fitted_q_linear | return_minus_drawdown | 1.640 | -0.692 | 1.193 | 0.200 |
| rl_fitted_q_linear_btc_eth_r14_return_minus_turnover | btc_eth | 14 | fitted_q_linear | return_minus_turnover | 1.640 | -0.692 | 1.193 | 0.200 |
| rl_fitted_q_linear_btc_eth_r14_adaptive_risk_control | btc_eth | 14 | fitted_q_linear | adaptive_risk_control | 1.640 | -0.692 | 1.193 | 0.200 |
| rl_fitted_q_linear_btc_eth_r7_raw_return | btc_eth | 7 | fitted_q_linear | raw_return | 1.478 | -0.891 | 1.193 | 0.200 |
| rl_fitted_q_linear_btc_eth_r7_return_minus_turnover | btc_eth | 7 | fitted_q_linear | return_minus_turnover | 1.478 | -0.891 | 1.193 | 0.200 |
| rl_fitted_q_linear_top10_r7_return_minus_volatility | top10 | 7 | fitted_q_linear | return_minus_volatility | 1.424 | -2.268 | 1.214 | 0.200 |
| rl_fitted_q_linear_top10_r14_adaptive_risk_control | top10 | 14 | fitted_q_linear | adaptive_risk_control | 1.118 | -2.459 | 1.214 | 0.200 |
| rl_tabular_q_top10_r14_adaptive_risk_control | top10 | 14 | tabular_q | adaptive_risk_control | 0.990 | N/A | 4.314 | 23.480 |
| rl_tabular_q_top10_r14_return_minus_volatility | top10 | 14 | tabular_q | return_minus_volatility | 0.990 | N/A | 4.179 | 25.347 |
| rl_tabular_q_top10_r14_return_minus_drawdown | top10 | 14 | tabular_q | return_minus_drawdown | 0.990 | N/A | 4.179 | 25.347 |
| rl_tabular_q_top10_r14_return_minus_turnover | top10 | 14 | tabular_q | return_minus_turnover | 0.990 | N/A | 4.085 | 25.213 |
| rl_tabular_q_top10_r14_raw_return | top10 | 14 | tabular_q | raw_return | 0.990 | N/A | 4.054 | 26.027 |
| rl_tabular_q_btc_eth_r14_adaptive_risk_control | btc_eth | 14 | tabular_q | adaptive_risk_control | 0.975 | N/A | 3.986 | 17.400 |
| rl_tabular_q_btc_eth_r14_return_minus_volatility | btc_eth | 14 | tabular_q | return_minus_volatility | 0.975 | N/A | 3.954 | 19.000 |
| rl_tabular_q_btc_eth_r14_return_minus_turnover | btc_eth | 14 | tabular_q | return_minus_turnover | 0.975 | N/A | 3.949 | 19.200 |
| rl_tabular_q_btc_eth_r14_return_minus_drawdown | btc_eth | 14 | tabular_q | return_minus_drawdown | 0.975 | N/A | 3.945 | 19.200 |
| rl_tabular_q_btc_eth_r14_raw_return | btc_eth | 14 | tabular_q | raw_return | 0.975 | N/A | 3.943 | 19.600 |
| rl_fitted_q_linear_btc_eth_r7_return_minus_volatility | btc_eth | 7 | fitted_q_linear | return_minus_volatility | 0.942 | -0.891 | 1.193 | 0.200 |
| rl_fitted_q_linear_btc_eth_r7_return_minus_drawdown | btc_eth | 7 | fitted_q_linear | return_minus_drawdown | 0.942 | -0.891 | 1.193 | 0.200 |
| rl_fitted_q_linear_top10_r7_return_minus_drawdown | top10 | 7 | fitted_q_linear | return_minus_drawdown | 0.942 | -2.268 | 1.214 | 0.200 |
| rl_fitted_q_linear_top10_r7_adaptive_risk_control | top10 | 7 | fitted_q_linear | adaptive_risk_control | 0.942 | N/A | 1.214 | 0.200 |
| rl_fitted_q_linear_top10_r14_return_minus_volatility | top10 | 14 | fitted_q_linear | return_minus_volatility | 0.939 | -2.459 | 1.214 | 0.200 |
| rl_fitted_q_linear_top10_r14_raw_return | top10 | 14 | fitted_q_linear | raw_return | 0.939 | -2.459 | 1.008 | 19.933 |
