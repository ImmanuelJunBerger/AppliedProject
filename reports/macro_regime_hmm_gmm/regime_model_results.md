# HMM/GMM macro-regime model results

## Protocol

- Development period: 2020-01-01 to 2024-12-31.
- Locked holdout: 2025-01-01 to 2026-06-22.
- Regime model fitting: Unsupervised models fit on development features only; future returns are not used for fitting or risk labels.
- Holdout use: Holdout is used only for final validation and reporting.
- Tested strategy configurations: 19

## Model inventory

| Model | Type | Feature set | Features | Train start | Train end | hmmlearn available |
|---|---|---|---|---|---|---|
| gmm_macro | gmm | macro | equity_realized_vol_21d, equity_momentum_21d, dow_vol_level, vix_level, vix_change_5d, vix_change_21d | 2020-01-01 | 2024-12-31 | No |
| kmeans_macro | kmeans | macro | equity_realized_vol_21d, equity_momentum_21d, dow_vol_level, vix_level, vix_change_5d, vix_change_21d | 2020-01-01 | 2024-12-31 | No |
| markov_fallback_macro | markov_fallback | macro | equity_realized_vol_21d, equity_momentum_21d, dow_vol_level, vix_level, vix_change_5d, vix_change_21d | 2020-01-01 | 2024-12-31 | No |
| gmm_macro_crypto | gmm | macro_crypto | equity_realized_vol_21d, equity_momentum_21d, dow_vol_level, vix_level, vix_change_5d, vix_change_21d, stablecoin_supply_change_7d, tvl_growth_30d, volatility_expansion_probability, cross_sectional_dispersion | 2020-01-01 | 2024-12-31 | No |
| kmeans_macro_crypto | kmeans | macro_crypto | equity_realized_vol_21d, equity_momentum_21d, dow_vol_level, vix_level, vix_change_5d, vix_change_21d, stablecoin_supply_change_7d, tvl_growth_30d, volatility_expansion_probability, cross_sectional_dispersion | 2020-01-01 | 2024-12-31 | No |
| markov_fallback_macro_crypto | markov_fallback | macro_crypto | equity_realized_vol_21d, equity_momentum_21d, dow_vol_level, vix_level, vix_change_5d, vix_change_21d, stablecoin_supply_change_7d, tvl_growth_30d, volatility_expansion_probability, cross_sectional_dispersion | 2020-01-01 | 2024-12-31 | No |

Regime labels are assigned by macro risk scores only. Future crypto returns are not used to label risk-on, neutral, or risk-off states.
