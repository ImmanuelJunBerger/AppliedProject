# Volatility-expansion signal study

## Scope

This is a prediction study only. It contains no return target, portfolio construction, position sizing, execution rule, or trading backtest.

- Target: future 7-day basket realized variance exceeds trailing 7-day basket realized variance
- Universe: weekly point-in-time top 10 by trailing 90-day median dollar volume
- Observations: 2513 from 2019-07-30 to 2026-06-15
- Positive-class rate: 50.70%
- Unique historical universe members: 54
- Development evaluation: expanding walk-forward six-month blocks
- Inner tuning: CPCV entirely inside each training window
- Locked holdout: 2025-01-01 to 2026-06-22
- Holdout rule: all labels end before holdout start; no holdout outcomes used for tuning

## Feature availability

| Feature set | Available | Features | Reason |
|---|---|---|---|
| price_only | Yes | 17 | available |
| price_liquidity | Yes | 25 | available |
| price_derivatives | Yes | 23 | available |
| price_derivatives_options | No | 0 | derivative and/or options columns are absent or below 20% development coverage |

## Walk-forward development performance

| Model | Feature set | N | Expansion rate | AUC | Precision | Recall | Brier |
|---|---|---|---|---|---|---|---|
| boosted_tree | price_derivatives | 1252 | 51.92% | 0.7517 | 0.6732 | 0.7954 | 0.2043 |
| boosted_tree | price_liquidity | 1252 | 51.92% | 0.7534 | 0.6718 | 0.8092 | 0.2043 |
| boosted_tree | price_only | 1252 | 51.92% | 0.7583 | 0.6774 | 0.8077 | 0.2015 |
| elastic_net | price_derivatives | 1252 | 51.92% | 0.7660 | 0.7063 | 0.7585 | 0.1985 |
| elastic_net | price_liquidity | 1252 | 51.92% | 0.7621 | 0.6906 | 0.7831 | 0.2012 |
| elastic_net | price_only | 1252 | 51.92% | 0.7672 | 0.7037 | 0.7600 | 0.1976 |
| har | price_only | 1252 | 51.92% | 0.7642 | 0.6879 | 0.7631 | 0.1996 |

## Locked holdout performance

| Model | Feature set | N | Expansion rate | AUC | Precision | Recall | Brier |
|---|---|---|---|---|---|---|---|
| boosted_tree | price_derivatives | 531 | 51.04% | 0.8400 | 0.7372 | 0.8487 | 0.1715 |
| boosted_tree | price_liquidity | 531 | 51.04% | 0.8371 | 0.6879 | 0.8782 | 0.1786 |
| boosted_tree | price_only | 531 | 51.04% | 0.8389 | 0.7273 | 0.8856 | 0.1731 |
| elastic_net | price_derivatives | 531 | 51.04% | 0.8574 | 0.7762 | 0.8192 | 0.1611 |
| elastic_net | price_liquidity | 531 | 51.04% | 0.8579 | 0.7484 | 0.8561 | 0.1624 |
| elastic_net | price_only | 531 | 51.04% | 0.8567 | 0.7786 | 0.8044 | 0.1592 |
| har | price_only | 531 | 51.04% | 0.8220 | 0.7246 | 0.8155 | 0.1779 |

## Incremental feature-set comparison

Positive Delta AUC is better; negative Delta Brier is better. "Improves both" requires both conditions on matched dates.

| Split | Model | Alternative set | N | Delta AUC | Delta Brier | Improves both |
|---|---|---|---|---|---|---|
| development | elastic_net | price_derivatives | 1252 | -0.0012 | 0.0008 | No |
| development | elastic_net | price_liquidity | 1252 | -0.0051 | 0.0036 | No |
| development | boosted_tree | price_derivatives | 1252 | -0.0066 | 0.0029 | No |
| development | boosted_tree | price_liquidity | 1252 | -0.0049 | 0.0028 | No |
| holdout | elastic_net | price_derivatives | 531 | 0.0007 | 0.0018 | No |
| holdout | elastic_net | price_liquidity | 531 | 0.0012 | 0.0032 | No |
| holdout | boosted_tree | price_derivatives | 531 | 0.0012 | -0.0016 | Yes |
| holdout | boosted_tree | price_liquidity | 531 | -0.0017 | 0.0055 | No |

## Conclusion

The price-history volatility signal survives the untouched holdout: Elastic Net with price-only features achieves AUC 0.857 and Brier 0.159, versus AUC 0.500 and Brier 0.250 for a constant-rate forecast.

No derivatives/options feature set improved both AUC and Brier score consistently in development and holdout. Boosted-tree funding features produced a small holdout-only improvement (AUC +0.0012; Brier -0.0016), but they worsened both metrics in development and therefore do not establish robust incremental value. Liquidity features also failed to improve both metrics consistently. Historical options data were unavailable and were not approximated.

This study establishes only predictive discrimination and calibration. Even a positive result is insufficient authorization to construct a trading strategy.

## Limitations

- Realized variance is estimated from daily closes because the available broad panel is daily, not intraday.
- Seven-day labels overlap, so the 531 holdout observations are not 531 independent observations.
- Universe ranks are point-in-time within the downloaded Binance market catalog, but removed/delisted pairs absent from that catalog cannot be recovered.
- The derivatives block currently contains realized funding only; long-history open interest, basis, liquidations, and options were unavailable.
- Funding coverage follows currently mapped linear perpetual contracts and is lagged one day.
