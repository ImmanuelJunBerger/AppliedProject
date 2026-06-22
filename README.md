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

## Installation

This repository is runnable in two modes:

1. **Full research mode** (recommended locally):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.run_demo
```

2. **Restricted-environment fallback mode**: `python -m src.run_demo` uses only the Python standard library and produces deterministic synthetic reports under `reports/`. This fallback is for execution validation only; it is not evidence that a live crypto strategy is profitable.

Advanced boosted-tree packages are optional. If XGBoost or LightGBM is unavailable, the framework falls back to scikit-learn gradient boosting for model-comparison plumbing.

## CPCV validation

The project implements Combinatorial Purged Cross Validation in `crypto_mlsystem.cpcv`. Random K-fold is invalid for this research because financial observations are temporally ordered, serially correlated, and often have overlapping forward-return labels. CPCV forms chronological group combinations inside each walk-forward training window, purges training labels that overlap validation labels, and embargoes observations immediately after validation samples. CPCV is used for hyperparameter tuning only inside the historical training window; the outer walk-forward test period is never used for tuning.

## Environment limitation observed here

The provided execution environment did not have `numpy`, `pandas`, or `scikit-learn` available for the active interpreter, and network installation was blocked with a 403 tunnel error. The standard-library demo and CPCV tests were run successfully here. To run the full pandas/scikit-learn pipeline, install `requirements.txt` in a local environment with package-index access.

## Real-data download path

The framework now includes an optional ccxt downloader for real OHLCV data. Install dependencies, then run one of:

```bash
python -m src.download_data --exchange binance --quote USDT --top-n 20 --since 2020-01-01 --output data/binance_ohlcv.csv
python -m src.download_data --exchange coinbase --quote USD --symbols BTC/USD ETH/USD --since 2020-01-01 --output data/coinbase_ohlcv.csv
```

The downloader ranks available spot markets by ticker turnover when the exchange exposes `fetch_tickers`, always attempts to include BTC and ETH first, and excludes stablecoins and wrapped assets from the discovered universe. Binance commonly uses `USDT` quote pairs; Coinbase commonly uses `USD` quote pairs. The output CSV matches the research pipeline schema: `date`, `symbol`, `open`, `high`, `low`, `close`, `volume`, and `market_cap`.

After downloading, pass the CSV into the research runner from Python:

```python
from crypto_mlsystem.run_research import run
result = run(data_path="data/binance_ohlcv.csv", top_n=20, model_name="logistic_regression", cost_bps=25)
print(result["result"]["metrics"])
```

Real-data limitations remain important: exchange listings vary through time, delisted assets may be missing, ticker liquidity can be exchange-specific, and `market_cap` is approximated from OHLCV unless a separate market-cap data vendor is integrated.
