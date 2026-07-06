# Regime diagnostics

The table tests whether pure cross-sectional momentum performs differently inside
the Tier-1 feature regimes selected on development data.

| Split | Regime | Days | Fraction days | Gated mean daily return | Pure momentum mean daily return | Pure momentum Sharpe | Gated Sharpe |
|---|---|---|---|---|---|---|---|
| development | risk_on | 222 | 12.15% | 0.51% | 0.64% | 1.282 | 1.094 |
| development | neutral | 644 | 35.25% | 0.19% | 0.23% | 0.822 | 0.867 |
| development | risk_off | 961 | 52.60% | 0.04% | 0.01% | 0.015 | 0.524 |
| holdout | risk_on | 73 | 13.57% | -0.02% | 0.01% | 0.014 | -0.248 |
| holdout | neutral | 198 | 36.80% | -0.05% | -0.13% | -0.971 | -0.522 |
| holdout | risk_off | 267 | 49.63% | 0.09% | -0.03% | -0.177 | 0.991 |
