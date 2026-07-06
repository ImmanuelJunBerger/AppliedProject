# Statistical validation

- PBO: 91.43%
- Deflated Sharpe probability: 12.39%
- Bootstrap Sharpe CI: [-0.364, 2.308]
- Approximate Jobson-Korkie/Ledoit-Wolf-style Sharpe delta vs frozen: -0.035
- Approximate p-value: 0.596
- Tested configurations: 64

| Name | Window | Median rolling Sharpe | Worst rolling Sharpe | Median rolling vol | Max rolling DD |
|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | 90 | 0.679 | -5.527 | 0.254 | -74.09% |
| btc_eth_macro_gate_balanced | 180 | 0.751 | -3.116 | 0.319 | -74.09% |
| inverse_volatility__btc_eth__static | 90 | 0.700 | -5.502 | 0.257 | -74.24% |
| inverse_volatility__btc_eth__static | 180 | 0.762 | -3.109 | 0.307 | -74.24% |
