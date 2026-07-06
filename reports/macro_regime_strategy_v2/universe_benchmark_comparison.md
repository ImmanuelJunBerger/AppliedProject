# Universe benchmark comparison

## Method

- Equal-weight top-universe benchmarks use point-in-time top 10, top 20, and top
  30 liquid universes.
- Pure momentum benchmarks use the same point-in-time universe construction,
  rank by lagged 63-day momentum, and hold the top 5 assets weekly.
- Stablecoins and wrapped assets are excluded.
- Universe membership uses lagged liquidity/history through the existing
  `point_in_time_liquid_universe` builder.
- This is not today's-top-coins retroactively applied.

## Survivorship and data limitations

- Top-universe benchmarks use lagged liquidity-based universe construction and exclude stable/wrapped assets.
- The Binance panel itself contains only assets available in the existing research dataset; missing historical listings cannot be recovered.
- The benchmark construction does not use today's top coins retroactively.

## Locked holdout at 25 bps

| Strategy | Group | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure | Transaction costs | Worst month |
|---|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | selected_fixed_strategy | 25.07% | 0.970 | 1.234 | -18.42% | 1.361 | 10.177 | 28.95% | 3.75% | -5.98% |
| pure_top10_momentum | point_in_time_momentum | -35.42% | -0.407 | -0.598 | -63.09% | -0.561 | 15.928 | 100.00% | 5.87% | -21.94% |
| equal_weight_top10 | point_in_time_top_universe | -39.25% | -0.418 | -0.619 | -63.51% | -0.618 | 1.493 | 100.00% | 0.55% | -28.25% |
| pure_top20_momentum | point_in_time_momentum | -45.13% | -0.471 | -0.684 | -71.82% | -0.628 | 24.139 | 100.00% | 8.90% | -26.80% |
| equal_weight_top20 | point_in_time_top_universe | -50.49% | -0.571 | -0.835 | -72.72% | -0.694 | 3.121 | 100.00% | 1.15% | -29.97% |
| equal_weight_top30 | point_in_time_top_universe | -55.59% | -0.668 | -0.968 | -76.52% | -0.726 | 3.121 | 100.00% | 1.15% | -31.12% |
| pure_top30_momentum | point_in_time_momentum | -57.72% | -0.701 | -1.042 | -81.90% | -0.705 | 28.012 | 100.00% | 10.32% | -32.89% |

## Universe benchmark cost sensitivity

| Strategy | Cost bps | CAGR | Sharpe | Sortino | Max DD | Annual turnover | Exposure | Transaction costs | Worst month |
|---|---|---|---|---|---|---|---|---|---|
| btc_eth_macro_gate_balanced | 10 | 26.99% | 1.028 | 1.304 | -18.05% | 10.177 | 28.95% | 1.50% | -5.77% |
| btc_eth_macro_gate_balanced | 25 | 25.07% | 0.970 | 1.234 | -18.42% | 10.177 | 28.95% | 3.75% | -5.98% |
| btc_eth_macro_gate_balanced | 50 | 21.92% | 0.874 | 1.115 | -19.03% | 10.177 | 28.95% | 7.50% | -6.34% |
| btc_eth_macro_gate_balanced | 100 | 15.85% | 0.681 | 0.871 | -20.25% | 10.177 | 28.95% | 15.00% | -7.06% |
| equal_weight_top10 | 10 | -39.12% | -0.415 | -0.614 | -63.45% | 1.493 | 100.00% | 0.22% | -28.25% |
| equal_weight_top10 | 25 | -39.25% | -0.418 | -0.619 | -63.51% | 1.493 | 100.00% | 0.55% | -28.25% |
| equal_weight_top10 | 50 | -39.48% | -0.424 | -0.627 | -63.63% | 1.493 | 100.00% | 1.10% | -28.25% |
| equal_weight_top10 | 100 | -39.93% | -0.435 | -0.644 | -63.89% | 1.493 | 100.00% | 2.20% | -28.25% |
| equal_weight_top20 | 10 | -50.26% | -0.565 | -0.826 | -72.60% | 3.121 | 100.00% | 0.46% | -29.94% |
| equal_weight_top20 | 25 | -50.49% | -0.571 | -0.835 | -72.72% | 3.121 | 100.00% | 1.15% | -29.97% |
| equal_weight_top20 | 50 | -50.88% | -0.581 | -0.851 | -72.93% | 3.121 | 100.00% | 2.30% | -30.02% |
| equal_weight_top20 | 100 | -51.64% | -0.602 | -0.880 | -73.35% | 3.121 | 100.00% | 4.60% | -30.13% |
| equal_weight_top30 | 10 | -55.38% | -0.662 | -0.959 | -76.37% | 3.121 | 100.00% | 0.46% | -31.11% |
| equal_weight_top30 | 25 | -55.59% | -0.668 | -0.968 | -76.52% | 3.121 | 100.00% | 1.15% | -31.12% |
| equal_weight_top30 | 50 | -55.93% | -0.678 | -0.983 | -76.78% | 3.121 | 100.00% | 2.30% | -31.13% |
| equal_weight_top30 | 100 | -56.61% | -0.698 | -1.013 | -77.29% | 3.121 | 100.00% | 4.60% | -31.16% |
| pure_top10_momentum | 10 | -33.85% | -0.368 | -0.541 | -62.43% | 15.928 | 100.00% | 2.35% | -21.84% |
| pure_top10_momentum | 25 | -35.42% | -0.407 | -0.598 | -63.09% | 15.928 | 100.00% | 5.87% | -21.94% |
| pure_top10_momentum | 50 | -37.94% | -0.472 | -0.694 | -64.18% | 15.928 | 100.00% | 11.74% | -22.09% |
| pure_top10_momentum | 100 | -42.71% | -0.601 | -0.884 | -66.75% | 15.928 | 100.00% | 23.48% | -22.40% |
| pure_top20_momentum | 10 | -43.11% | -0.421 | -0.611 | -70.40% | 24.139 | 100.00% | 3.56% | -26.58% |
| pure_top20_momentum | 25 | -45.13% | -0.471 | -0.684 | -71.82% | 24.139 | 100.00% | 8.90% | -26.80% |
| pure_top20_momentum | 50 | -48.34% | -0.555 | -0.805 | -74.03% | 24.139 | 100.00% | 17.79% | -27.15% |
| pure_top20_momentum | 100 | -54.24% | -0.723 | -1.047 | -77.96% | 24.139 | 100.00% | 35.58% | -27.86% |
| pure_top30_momentum | 10 | -55.89% | -0.648 | -0.964 | -80.81% | 28.012 | 100.00% | 4.13% | -32.65% |
| pure_top30_momentum | 25 | -57.72% | -0.701 | -1.042 | -81.90% | 28.012 | 100.00% | 10.32% | -32.89% |
| pure_top30_momentum | 50 | -60.60% | -0.790 | -1.172 | -83.57% | 28.012 | 100.00% | 20.64% | -33.28% |
| pure_top30_momentum | 100 | -65.80% | -0.968 | -1.430 | -86.49% | 28.012 | 100.00% | 41.29% | -34.07% |

## Conclusion

- The selected strategy beats simple crypto beta after costs on Sharpe, CAGR, and max drawdown.
- The selected strategy beats top-universe exposure after costs on Sharpe, CAGR, and max drawdown.
- The selected strategy beats pure momentum after costs on Sharpe, CAGR, and max drawdown.
- The selected strategy beats the prior best Tier-1 regime-gated momentum strategy after costs on Sharpe, CAGR, and max drawdown.
- Universe benchmarks are point-in-time within the available Binance research panel, but the panel may still omit assets not present in the collected historical dataset.
