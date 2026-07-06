# Predictive results

Models use annual expanding walk-forward evaluation. Hyperparameters are chosen by purged, embargoed CPCV inside each historical training window. The classification threshold is fixed at 0.50.

The requested risk-adjusted-return sign target is the sign of forward return after
division by a strictly positive trailing-volatility scale. It is therefore not an
independent directional target; the implementation retains the requested name but
makes this equivalence explicit. The three drawdown thresholds are tracked as
separate target configurations.

## Metrics

| Target | Model | Features | Split | N | Positive rate | AUC | Brier | Precision | Recall |
|---|---|---|---|---|---|---|---|---|---|
| drawdown_10 | boosted_tree | price_derivatives | development | 2922 | 14.65% | 0.497 | 0.131 | 0.274 | 0.040 |
| drawdown_10 | gradient_boosting | price_derivatives | development | 2922 | 14.65% | 0.503 | 0.134 | 0.295 | 0.091 |
| drawdown_10 | boosted_tree | derivatives_only | development | 2922 | 14.65% | 0.479 | 0.135 | 0.300 | 0.056 |
| drawdown_10 | gradient_boosting | derivatives_only | development | 2922 | 14.65% | 0.483 | 0.136 | 0.316 | 0.100 |
| drawdown_10 | random_forest | price_derivatives | development | 2922 | 14.65% | 0.513 | 0.184 | 0.240 | 0.227 |
| drawdown_10 | random_forest | derivatives_only | development | 2922 | 14.65% | 0.500 | 0.198 | 0.145 | 0.215 |
| drawdown_10 | elastic_net | price_only | development | 2922 | 14.65% | 0.543 | 0.228 | 0.217 | 0.280 |
| drawdown_10 | logistic | price_only | development | 2922 | 14.65% | 0.541 | 0.229 | 0.212 | 0.280 |
| drawdown_10 | elastic_net | price_derivatives | development | 2922 | 14.65% | 0.534 | 0.234 | 0.211 | 0.381 |
| drawdown_10 | elastic_net | derivatives_only | development | 2922 | 14.65% | 0.542 | 0.235 | 0.203 | 0.439 |
| drawdown_10 | logistic | price_derivatives | development | 2922 | 14.65% | 0.535 | 0.235 | 0.212 | 0.390 |
| drawdown_10 | logistic | derivatives_only | development | 2922 | 14.65% | 0.540 | 0.237 | 0.198 | 0.439 |
| drawdown_10 | boosted_tree | price_derivatives | holdout | 1062 | 14.03% | 0.550 | 0.122 | 0.000 | 0.000 |
| drawdown_10 | gradient_boosting | price_derivatives | holdout | 1062 | 14.03% | 0.522 | 0.122 | 0.000 | 0.000 |
| drawdown_10 | gradient_boosting | derivatives_only | holdout | 1062 | 14.03% | 0.413 | 0.123 | 0.000 | 0.000 |
| drawdown_10 | boosted_tree | derivatives_only | holdout | 1062 | 14.03% | 0.423 | 0.123 | 0.000 | 0.000 |
| drawdown_10 | random_forest | price_derivatives | holdout | 1062 | 14.03% | 0.570 | 0.162 | 0.169 | 0.074 |
| drawdown_10 | random_forest | derivatives_only | holdout | 1062 | 14.03% | 0.486 | 0.175 | 0.111 | 0.020 |
| drawdown_10 | logistic | price_derivatives | holdout | 1062 | 14.03% | 0.460 | 0.197 | 0.150 | 0.148 |
| drawdown_10 | elastic_net | price_derivatives | holdout | 1062 | 14.03% | 0.462 | 0.198 | 0.146 | 0.148 |
| drawdown_10 | logistic | derivatives_only | holdout | 1062 | 14.03% | 0.416 | 0.212 | 0.123 | 0.148 |
| drawdown_10 | logistic | price_only | holdout | 1062 | 14.03% | 0.517 | 0.213 | 0.141 | 0.188 |
| drawdown_10 | elastic_net | price_only | holdout | 1062 | 14.03% | 0.518 | 0.213 | 0.136 | 0.181 |
| drawdown_10 | elastic_net | derivatives_only | holdout | 1062 | 14.03% | 0.415 | 0.213 | 0.128 | 0.161 |
| drawdown_15 | boosted_tree | price_derivatives | development | 2922 | 6.26% | 0.430 | 0.063 | 0.000 | 0.000 |
| drawdown_15 | gradient_boosting | price_derivatives | development | 2922 | 6.26% | 0.447 | 0.069 | 0.022 | 0.005 |
| drawdown_15 | boosted_tree | derivatives_only | development | 2922 | 6.26% | 0.415 | 0.070 | 0.000 | 0.000 |
| drawdown_15 | gradient_boosting | derivatives_only | development | 2922 | 6.26% | 0.457 | 0.072 | 0.101 | 0.038 |
| drawdown_15 | random_forest | price_derivatives | development | 2922 | 6.26% | 0.422 | 0.126 | 0.073 | 0.120 |
| drawdown_15 | random_forest | derivatives_only | development | 2922 | 6.26% | 0.421 | 0.148 | 0.056 | 0.142 |
| drawdown_15 | elastic_net | price_only | development | 2922 | 6.26% | 0.497 | 0.227 | 0.086 | 0.311 |
| drawdown_15 | logistic | price_only | development | 2922 | 6.26% | 0.498 | 0.227 | 0.085 | 0.311 |
| drawdown_15 | logistic | derivatives_only | development | 2922 | 6.26% | 0.424 | 0.234 | 0.061 | 0.306 |
| drawdown_15 | elastic_net | derivatives_only | development | 2922 | 6.26% | 0.425 | 0.241 | 0.056 | 0.295 |
| drawdown_15 | logistic | price_derivatives | development | 2922 | 6.26% | 0.435 | 0.245 | 0.059 | 0.273 |
| drawdown_15 | elastic_net | price_derivatives | development | 2922 | 6.26% | 0.425 | 0.246 | 0.056 | 0.273 |
| drawdown_15 | boosted_tree | price_derivatives | holdout | 1062 | 5.18% | 0.572 | 0.049 | 0.000 | 0.000 |
| drawdown_15 | gradient_boosting | price_derivatives | holdout | 1062 | 5.18% | 0.566 | 0.049 | 0.000 | 0.000 |
| drawdown_15 | boosted_tree | derivatives_only | holdout | 1062 | 5.18% | 0.487 | 0.049 | 0.000 | 0.000 |
| drawdown_15 | gradient_boosting | derivatives_only | holdout | 1062 | 5.18% | 0.513 | 0.049 | 0.000 | 0.000 |
| drawdown_15 | random_forest | price_derivatives | holdout | 1062 | 5.18% | 0.563 | 0.112 | 0.074 | 0.091 |
| drawdown_15 | random_forest | derivatives_only | holdout | 1062 | 5.18% | 0.486 | 0.126 | 0.069 | 0.127 |
| drawdown_15 | elastic_net | price_derivatives | holdout | 1062 | 5.18% | 0.472 | 0.195 | 0.057 | 0.273 |
| drawdown_15 | logistic | price_derivatives | holdout | 1062 | 5.18% | 0.466 | 0.199 | 0.055 | 0.273 |
| drawdown_15 | logistic | price_only | holdout | 1062 | 5.18% | 0.579 | 0.203 | 0.049 | 0.236 |
| drawdown_15 | elastic_net | price_only | holdout | 1062 | 5.18% | 0.580 | 0.203 | 0.048 | 0.236 |
| drawdown_15 | elastic_net | derivatives_only | holdout | 1062 | 5.18% | 0.398 | 0.210 | 0.051 | 0.309 |
| drawdown_15 | logistic | derivatives_only | holdout | 1062 | 5.18% | 0.402 | 0.216 | 0.052 | 0.327 |
| drawdown_5 | boosted_tree | price_derivatives | development | 2922 | 34.77% | 0.561 | 0.228 | 0.434 | 0.094 |
| drawdown_5 | gradient_boosting | price_derivatives | development | 2922 | 34.77% | 0.564 | 0.228 | 0.433 | 0.083 |
| drawdown_5 | boosted_tree | derivatives_only | development | 2922 | 34.77% | 0.484 | 0.237 | 0.456 | 0.147 |
| drawdown_5 | gradient_boosting | derivatives_only | development | 2922 | 34.77% | 0.477 | 0.238 | 0.485 | 0.139 |
| drawdown_5 | random_forest | price_derivatives | development | 2922 | 34.77% | 0.566 | 0.238 | 0.437 | 0.377 |
| drawdown_5 | elastic_net | price_only | development | 2922 | 34.77% | 0.580 | 0.240 | 0.448 | 0.358 |
| drawdown_5 | logistic | price_only | development | 2922 | 34.77% | 0.576 | 0.241 | 0.444 | 0.355 |
| drawdown_5 | random_forest | derivatives_only | development | 2922 | 34.77% | 0.502 | 0.249 | 0.370 | 0.394 |
| drawdown_5 | elastic_net | price_derivatives | development | 2922 | 34.77% | 0.546 | 0.254 | 0.444 | 0.404 |
| drawdown_5 | elastic_net | derivatives_only | development | 2922 | 34.77% | 0.528 | 0.255 | 0.411 | 0.420 |
| drawdown_5 | logistic | price_derivatives | development | 2922 | 34.77% | 0.544 | 0.256 | 0.443 | 0.404 |
| drawdown_5 | logistic | derivatives_only | development | 2922 | 34.77% | 0.527 | 0.257 | 0.411 | 0.432 |
| drawdown_5 | boosted_tree | price_derivatives | holdout | 1062 | 33.71% | 0.561 | 0.227 | 0.111 | 0.003 |
| drawdown_5 | gradient_boosting | price_derivatives | holdout | 1062 | 33.71% | 0.549 | 0.228 | 0.100 | 0.003 |
| drawdown_5 | gradient_boosting | derivatives_only | holdout | 1062 | 33.71% | 0.414 | 0.230 | 0.000 | 0.000 |
| drawdown_5 | boosted_tree | derivatives_only | holdout | 1062 | 33.71% | 0.410 | 0.231 | 0.000 | 0.000 |
| drawdown_5 | random_forest | price_derivatives | holdout | 1062 | 33.71% | 0.562 | 0.233 | 0.389 | 0.383 |
| drawdown_5 | elastic_net | price_derivatives | holdout | 1062 | 33.71% | 0.521 | 0.238 | 0.362 | 0.226 |
| drawdown_5 | logistic | price_derivatives | holdout | 1062 | 33.71% | 0.518 | 0.238 | 0.355 | 0.218 |
| drawdown_5 | elastic_net | price_only | holdout | 1062 | 33.71% | 0.539 | 0.239 | 0.377 | 0.304 |
| drawdown_5 | logistic | price_only | holdout | 1062 | 33.71% | 0.537 | 0.239 | 0.380 | 0.302 |
| drawdown_5 | random_forest | derivatives_only | holdout | 1062 | 33.71% | 0.437 | 0.241 | 0.207 | 0.034 |
| drawdown_5 | elastic_net | derivatives_only | holdout | 1062 | 33.71% | 0.425 | 0.248 | 0.293 | 0.212 |
| drawdown_5 | logistic | derivatives_only | holdout | 1062 | 33.71% | 0.423 | 0.248 | 0.281 | 0.190 |
| eth_outperforms_btc | random_forest | price_derivatives | development | 1461 | 46.20% | 0.506 | 0.260 | 0.461 | 0.716 |
| eth_outperforms_btc | random_forest | derivatives_only | development | 1461 | 46.20% | 0.487 | 0.261 | 0.457 | 0.807 |
| eth_outperforms_btc | boosted_tree | derivatives_only | development | 1461 | 46.20% | 0.482 | 0.264 | 0.457 | 0.484 |
| eth_outperforms_btc | gradient_boosting | price_derivatives | development | 1461 | 46.20% | 0.495 | 0.267 | 0.470 | 0.461 |
| eth_outperforms_btc | boosted_tree | price_derivatives | development | 1461 | 46.20% | 0.492 | 0.268 | 0.470 | 0.499 |
| eth_outperforms_btc | elastic_net | price_only | development | 1461 | 46.20% | 0.462 | 0.268 | 0.461 | 0.321 |
| eth_outperforms_btc | logistic | price_only | development | 1461 | 46.20% | 0.464 | 0.270 | 0.458 | 0.338 |
| eth_outperforms_btc | gradient_boosting | derivatives_only | development | 1461 | 46.20% | 0.465 | 0.271 | 0.429 | 0.516 |
| eth_outperforms_btc | elastic_net | derivatives_only | development | 1461 | 46.20% | 0.466 | 0.278 | 0.444 | 0.480 |
| eth_outperforms_btc | logistic | derivatives_only | development | 1461 | 46.20% | 0.467 | 0.281 | 0.449 | 0.501 |
| eth_outperforms_btc | elastic_net | price_derivatives | development | 1461 | 46.20% | 0.470 | 0.293 | 0.450 | 0.483 |
| eth_outperforms_btc | logistic | price_derivatives | development | 1461 | 46.20% | 0.468 | 0.296 | 0.450 | 0.467 |
| eth_outperforms_btc | gradient_boosting | derivatives_only | holdout | 531 | 43.13% | 0.507 | 0.246 | 0.500 | 0.105 |
| eth_outperforms_btc | elastic_net | price_only | holdout | 531 | 43.13% | 0.563 | 0.246 | 0.485 | 0.493 |
| eth_outperforms_btc | logistic | price_only | holdout | 531 | 43.13% | 0.563 | 0.246 | 0.481 | 0.502 |
| eth_outperforms_btc | boosted_tree | derivatives_only | holdout | 531 | 43.13% | 0.492 | 0.247 | 0.393 | 0.048 |
| eth_outperforms_btc | logistic | derivatives_only | holdout | 531 | 43.13% | 0.494 | 0.249 | 0.464 | 0.197 |
| eth_outperforms_btc | elastic_net | derivatives_only | holdout | 531 | 43.13% | 0.488 | 0.250 | 0.438 | 0.183 |
| eth_outperforms_btc | elastic_net | price_derivatives | holdout | 531 | 43.13% | 0.521 | 0.251 | 0.519 | 0.349 |
| eth_outperforms_btc | gradient_boosting | price_derivatives | holdout | 531 | 43.13% | 0.485 | 0.251 | 0.429 | 0.131 |
| eth_outperforms_btc | logistic | price_derivatives | holdout | 531 | 43.13% | 0.521 | 0.251 | 0.519 | 0.349 |
| eth_outperforms_btc | random_forest | price_derivatives | holdout | 531 | 43.13% | 0.485 | 0.252 | 0.433 | 0.336 |
| eth_outperforms_btc | random_forest | derivatives_only | holdout | 531 | 43.13% | 0.467 | 0.252 | 0.389 | 0.297 |
| eth_outperforms_btc | boosted_tree | price_derivatives | holdout | 531 | 43.13% | 0.464 | 0.252 | 0.484 | 0.131 |
| risk_adjusted_sign | elastic_net | price_only | development | 2922 | 52.26% | 0.520 | 0.251 | 0.551 | 0.379 |
| risk_adjusted_sign | logistic | price_only | development | 2922 | 52.26% | 0.520 | 0.252 | 0.547 | 0.390 |
| risk_adjusted_sign | random_forest | price_derivatives | development | 2922 | 52.26% | 0.476 | 0.257 | 0.510 | 0.578 |
| risk_adjusted_sign | random_forest | derivatives_only | development | 2922 | 52.26% | 0.462 | 0.259 | 0.499 | 0.518 |
| risk_adjusted_sign | boosted_tree | price_derivatives | development | 2922 | 52.26% | 0.473 | 0.262 | 0.513 | 0.764 |
| risk_adjusted_sign | gradient_boosting | derivatives_only | development | 2922 | 52.26% | 0.471 | 0.262 | 0.521 | 0.766 |
| risk_adjusted_sign | gradient_boosting | price_derivatives | development | 2922 | 52.26% | 0.481 | 0.262 | 0.510 | 0.744 |
| risk_adjusted_sign | boosted_tree | derivatives_only | development | 2922 | 52.26% | 0.465 | 0.263 | 0.515 | 0.736 |
| risk_adjusted_sign | elastic_net | derivatives_only | development | 2922 | 52.26% | 0.462 | 0.267 | 0.507 | 0.456 |
| risk_adjusted_sign | elastic_net | price_derivatives | development | 2922 | 52.26% | 0.485 | 0.269 | 0.512 | 0.451 |
| risk_adjusted_sign | logistic | derivatives_only | development | 2922 | 52.26% | 0.464 | 0.270 | 0.509 | 0.449 |
| risk_adjusted_sign | logistic | price_derivatives | development | 2922 | 52.26% | 0.490 | 0.270 | 0.517 | 0.449 |
| risk_adjusted_sign | logistic | price_only | holdout | 1062 | 48.02% | 0.540 | 0.249 | 0.524 | 0.469 |
| risk_adjusted_sign | elastic_net | price_only | holdout | 1062 | 48.02% | 0.539 | 0.249 | 0.518 | 0.455 |
| risk_adjusted_sign | random_forest | price_derivatives | holdout | 1062 | 48.02% | 0.508 | 0.251 | 0.499 | 0.345 |
| risk_adjusted_sign | random_forest | derivatives_only | holdout | 1062 | 48.02% | 0.499 | 0.251 | 0.450 | 0.184 |
| risk_adjusted_sign | elastic_net | price_derivatives | holdout | 1062 | 48.02% | 0.520 | 0.251 | 0.494 | 0.451 |
| risk_adjusted_sign | logistic | price_derivatives | holdout | 1062 | 48.02% | 0.519 | 0.251 | 0.489 | 0.447 |
| risk_adjusted_sign | elastic_net | derivatives_only | holdout | 1062 | 48.02% | 0.475 | 0.252 | 0.422 | 0.282 |
| risk_adjusted_sign | logistic | derivatives_only | holdout | 1062 | 48.02% | 0.473 | 0.252 | 0.404 | 0.269 |
| risk_adjusted_sign | boosted_tree | derivatives_only | holdout | 1062 | 48.02% | 0.491 | 0.253 | 0.485 | 0.924 |
| risk_adjusted_sign | boosted_tree | price_derivatives | holdout | 1062 | 48.02% | 0.508 | 0.253 | 0.486 | 0.665 |
| risk_adjusted_sign | gradient_boosting | price_derivatives | holdout | 1062 | 48.02% | 0.505 | 0.254 | 0.483 | 0.686 |
| risk_adjusted_sign | gradient_boosting | derivatives_only | holdout | 1062 | 48.02% | 0.496 | 0.254 | 0.481 | 0.988 |
| volatility_expansion | boosted_tree | price_derivatives | development | 2922 | 48.49% | 0.727 | 0.211 | 0.630 | 0.735 |
| volatility_expansion | gradient_boosting | price_derivatives | development | 2922 | 48.49% | 0.726 | 0.211 | 0.627 | 0.733 |
| volatility_expansion | elastic_net | price_only | development | 2922 | 48.49% | 0.723 | 0.213 | 0.625 | 0.696 |
| volatility_expansion | logistic | price_only | development | 2922 | 48.49% | 0.723 | 0.214 | 0.623 | 0.694 |
| volatility_expansion | random_forest | price_derivatives | development | 2922 | 48.49% | 0.717 | 0.215 | 0.607 | 0.742 |
| volatility_expansion | elastic_net | price_derivatives | development | 2922 | 48.49% | 0.720 | 0.219 | 0.613 | 0.759 |
| volatility_expansion | logistic | price_derivatives | development | 2922 | 48.49% | 0.719 | 0.219 | 0.614 | 0.751 |
| volatility_expansion | random_forest | derivatives_only | development | 2922 | 48.49% | 0.540 | 0.251 | 0.518 | 0.608 |
| volatility_expansion | boosted_tree | derivatives_only | development | 2922 | 48.49% | 0.539 | 0.252 | 0.522 | 0.464 |
| volatility_expansion | gradient_boosting | derivatives_only | development | 2922 | 48.49% | 0.539 | 0.253 | 0.515 | 0.449 |
| volatility_expansion | elastic_net | derivatives_only | development | 2922 | 48.49% | 0.536 | 0.257 | 0.514 | 0.674 |
| volatility_expansion | logistic | derivatives_only | development | 2922 | 48.49% | 0.533 | 0.257 | 0.515 | 0.695 |
| volatility_expansion | logistic | price_only | holdout | 1062 | 49.72% | 0.733 | 0.209 | 0.634 | 0.759 |
| volatility_expansion | elastic_net | price_only | holdout | 1062 | 49.72% | 0.733 | 0.209 | 0.634 | 0.759 |
| volatility_expansion | random_forest | price_derivatives | holdout | 1062 | 49.72% | 0.737 | 0.209 | 0.669 | 0.720 |
| volatility_expansion | gradient_boosting | price_derivatives | holdout | 1062 | 49.72% | 0.731 | 0.211 | 0.663 | 0.705 |
| volatility_expansion | boosted_tree | price_derivatives | holdout | 1062 | 49.72% | 0.732 | 0.211 | 0.661 | 0.714 |
| volatility_expansion | elastic_net | price_derivatives | holdout | 1062 | 49.72% | 0.725 | 0.211 | 0.652 | 0.722 |
| volatility_expansion | logistic | price_derivatives | holdout | 1062 | 49.72% | 0.723 | 0.212 | 0.652 | 0.720 |
| volatility_expansion | random_forest | derivatives_only | holdout | 1062 | 49.72% | 0.596 | 0.245 | 0.577 | 0.597 |
| volatility_expansion | boosted_tree | derivatives_only | holdout | 1062 | 49.72% | 0.593 | 0.245 | 0.585 | 0.470 |
| volatility_expansion | gradient_boosting | derivatives_only | holdout | 1062 | 49.72% | 0.579 | 0.247 | 0.576 | 0.386 |
| volatility_expansion | elastic_net | derivatives_only | holdout | 1062 | 49.72% | 0.530 | 0.249 | 0.519 | 0.470 |
| volatility_expansion | logistic | derivatives_only | holdout | 1062 | 49.72% | 0.523 | 0.250 | 0.515 | 0.470 |

## Matched incremental comparisons

Positive AUC delta and negative Brier delta favor price plus derivatives.

| Target | Model | Split | Delta AUC | Delta Brier | Improves both |
|---|---|---|---|---|---|
| drawdown_10 | elastic_net | development | -0.009 | 0.005 | No |
| drawdown_10 | elastic_net | holdout | -0.056 | -0.015 | No |
| drawdown_10 | logistic | development | -0.007 | 0.007 | No |
| drawdown_10 | logistic | holdout | -0.058 | -0.016 | No |
| drawdown_15 | elastic_net | development | -0.072 | 0.019 | No |
| drawdown_15 | elastic_net | holdout | -0.108 | -0.008 | No |
| drawdown_15 | logistic | development | -0.063 | 0.018 | No |
| drawdown_15 | logistic | holdout | -0.113 | -0.004 | No |
| drawdown_5 | elastic_net | development | -0.033 | 0.014 | No |
| drawdown_5 | elastic_net | holdout | -0.017 | -0.002 | No |
| drawdown_5 | logistic | development | -0.032 | 0.015 | No |
| drawdown_5 | logistic | holdout | -0.020 | -0.002 | No |
| eth_outperforms_btc | elastic_net | development | 0.008 | 0.024 | No |
| eth_outperforms_btc | elastic_net | holdout | -0.042 | 0.005 | No |
| eth_outperforms_btc | logistic | development | 0.004 | 0.026 | No |
| eth_outperforms_btc | logistic | holdout | -0.042 | 0.005 | No |
| risk_adjusted_sign | elastic_net | development | -0.035 | 0.018 | No |
| risk_adjusted_sign | elastic_net | holdout | -0.020 | 0.002 | No |
| risk_adjusted_sign | logistic | development | -0.030 | 0.019 | No |
| risk_adjusted_sign | logistic | holdout | -0.021 | 0.003 | No |
| volatility_expansion | elastic_net | development | -0.003 | 0.006 | No |
| volatility_expansion | elastic_net | holdout | -0.009 | 0.003 | No |
| volatility_expansion | logistic | development | -0.004 | 0.006 | No |
| volatility_expansion | logistic | holdout | -0.010 | 0.003 | No |

No OI-dependent crowding-unwind model is reported because the target has no adequate development-era OI coverage.
