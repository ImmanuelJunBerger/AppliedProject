# Dynamic Strategy Allocation in Cryptocurrency Markets Using Machine Learning

This repository implements a research-first framework for testing whether machine learning improves dynamic allocation across independent long-only cryptocurrency strategies. The project is designed to falsify, not assume, ML value-add through strict walk-forward validation, lagged features, cost sensitivity, benchmark comparisons, and transparent risk controls.

## Design principles

- No random train/test splits; all validation is chronological and walk-forward.
- Features are shifted by one observation before training or prediction.
- Models predict next-period strategy leadership rather than coin prices.
- Equal-weight strategy allocation, standalone strategies, BTC/ETH proxies, and equal-weight universe portfolios are included as baselines.
- Transaction costs are explicit and configurable at 0, 10, 25, 50, and 100 bps.
- The optional reasoning layer is deterministic, rule-based, and auditable.

## Modules

- `crypto_mlsystem.data`: CSV ingestion, cleaning, synthetic fixtures, monthly liquidity universe construction.
- `crypto_mlsystem.strategies`: trend following, cross-sectional momentum, mean reversion, volatility breakout, and defensive cash strategy return streams.
- `crypto_mlsystem.features`: lagged market-state, trend, risk, liquidity, and strategy-health features.
- `crypto_mlsystem.ml`: equal-weight, logistic regression, random forest, and gradient-boosting walk-forward allocation models.
- `crypto_mlsystem.risk`: transparent reasoning layer with volatility and turnover constraints.
- `crypto_mlsystem.backtest`: allocation application, transaction costs, and benchmarks.
- `crypto_mlsystem.metrics`: CAGR, Sharpe, Sortino, Calmar, volatility, drawdown, hit rate, turnover, exposure, and costs.

## Quick start

```bash
python -m crypto_mlsystem.run_research
```

By default the runner uses deterministic synthetic data so CI can test the full pipeline without network dependencies. For research, pass a cleaned CSV containing `date`, `symbol`, `open`, `high`, `low`, `close`, `volume`, and `market_cap`; optional derivatives columns are preserved.

## Research workflow

1. Ingest market, capitalization, liquidity, and optional derivatives data.
2. Reconstitute top-10, top-20, and top-30 liquid universes monthly, excluding stablecoins, wrapped assets, and insufficient-history assets.
3. Backtest each standalone strategy independently.
4. Build lagged feature matrices and next-period strategy-leadership targets.
5. Run monthly/weekly walk-forward allocation experiments for equal-weight, logistic regression, random forest, and gradient boosting.
6. Apply risk controls and transaction-cost assumptions.
7. Compare against standalone strategies and buy-and-hold/equal-weight benchmarks.
8. Run robustness tests across universes, rebalance frequencies, costs, feature ablations, strategy removals, and market regimes.

## Important limitation

The included synthetic fixture is only for software validation. Evidence-driven conclusions require real historical data with documented coverage, exchange methodology, delistings where available, and survivorship-bias assessment.
