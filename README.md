# Dynamic Strategy Allocation in Cryptocurrency Markets Using Machine Learning

This repository implements a research-first framework for testing whether machine learning improves dynamic allocation across independent long-only cryptocurrency strategies. The project is designed to falsify, not assume, ML value-add through strict walk-forward validation, lagged features, cost sensitivity, benchmark comparisons, and transparent risk controls.

## Prediction-only volatility-expansion study

The volatility-expansion study predicts whether realized variance of a weekly
point-in-time top-10 liquid crypto basket will be higher over the next seven days
than over the trailing seven days. It evaluates HAR, Elastic Net, and XGBoost with
walk-forward development tests, CPCV tuning confined to each training window, and
a locked 2025–2026 holdout. It does not construct or backtest a trading strategy.

Run the available price and liquidity feature sets with:

```bash
python -m src.run_volatility_expansion_study \
  --data data/binance_usdt_broad_2019.csv \
  --output-dir reports/volatility_expansion
```

Derivatives and options are evaluated only when point-in-time columns are supplied
in the price panel or in a separate file keyed by `date,symbol` (or by `date` for
market-level options data):

```bash
python -m src.run_volatility_expansion_study \
  --data data/binance_usdt_broad_2019.csv \
  --alternative-data data/alternative_market_data.csv
```

The included narrow collector can retrieve realized Binance USD-M funding for the
historical universe emitted by an initial study run:

```bash
python -m src.download_derivatives \
  --membership reports/volatility_expansion/universe_membership.csv \
  --output data/binance_funding_daily.csv

python -m src.run_volatility_expansion_study \
  --data data/binance_usdt_broad_2019.csv \
  --alternative-data data/binance_funding_daily.csv
```

Funding is aggregated by UTC date. This collector does not claim long-history open
interest, liquidation, basis, or options coverage; those require a separately
licensed point-in-time source.

## Derivatives market-timing and relative-value study

The independent derivatives study downloads public Binance USD-M data, builds
one-day-lagged BTC/ETH derivatives features, runs purged walk-forward predictive
tests, and evaluates predeclared long-only BTC/ETH/cash strategies:

```bash
python -m src.run_derivatives_signals --refresh-data
```

Raw API responses are retained under `data/raw/derivatives`, processed daily data
under `data/processed/derivatives`, and research outputs under
`reports/derivatives_signals`. The public endpoints provide long realized funding
and premium-index basis histories, but only recent snapshots for open interest,
account positioning, and taker imbalance. OI-dependent studies are therefore
reported as unavailable instead of being filled with synthetic proxies.

The 2025 onward period is excluded from fitting and tuning. It is not described as
pristine, however, because earlier project work had already inspected that period;
the module treats it as a reused evaluation period and recommends a newly
registered prospective holdout before any capital deployment.

## WRDS data-discovery and integration planning

The WRDS inventory module is a credential-safe discovery layer for determining
whether licensed WRDS datasets can improve this project beyond Binance OHLCV and
funding data. It does not run a trading strategy and does not download backtest
features by default.

Credentials are read only from environment variables:

```powershell
$env:WRDS_USERNAME = "your_wrds_username"
$env:WRDS_PASSWORD = "your_wrds_password"
python -m src.run_wrds_inventory --scan-all-tables
```

If credentials or the optional `wrds` package are unavailable, the command still
writes setup instructions and non-live planning reports under
`reports/wrds_inventory`. Use `.env.example` only as a placeholder template; never
commit real credentials.

The current strategy direction proposed by this module is a low-turnover
BTC/ETH/cash "Macro-Conditioned Crypto Exposure Strategy" using WRDS-sourced
macro, USD, rates, equity, VIX, commodity, ETF-flow, news, and options-implied
risk-regime features where licensed and timestamp-safe.

## Public crypto-native data and feature research

When WRDS is unavailable, the public-data module investigates crypto-native
external features from public APIs before any new strategy is allowed:

```bash
python -m src.run_public_crypto_data --refresh-data \
  --data data/binance_usdt_broad_2019.csv
```

The runner writes public-data inventory reports under
`reports/public_crypto_data` and feature-research reports under
`reports/feature_research`. It currently checks CoinGecko, DefiLlama, Binance
4h BTC/ETH bars, and token-unlock availability. Missing token-unlock data is
reported as unavailable; no synthetic unlock data is created.

The required feature-research phase computes Spearman ICs versus 1/2/4-week
forward returns, Newey-West t-statistics, quantile spreads, regime stability,
holdout IC, redundancy diagnostics, VIF-style correlation checks, and model
importance comparisons. Features are classified into Tier 1, Tier 2, and Tier 3.
Tier 3 features are blocked from later strategy design.

The predeclared stablecoin/liquidity-conditioned BTC/ETH/cash strategy is not
run unless the required inputs pass the feature-tier gate. The current run found
Tier 1 evidence for 7-day stablecoin supply change, 30-day TVL growth, 7-day 4h
volatility, volatility-expansion probability, and cross-sectional dispersion,
but blocked the original candidate because some requested gates were Tier 3.

## Fixed-forecast portfolio overlay study

After the volatility study has produced its locked predictions, test their economic
value without refitting the prediction model:

```bash
python -m src.run_forecast_portfolio_study \
  --data data/binance_usdt_broad_2019.csv \
  --forecast-predictions reports/volatility_expansion/predictions.csv \
  --universe-membership reports/volatility_expansion/universe_membership.csv
```

This runner uses only the saved Elastic Net price-only probabilities. Risk-off,
breakout-activation, inverse-risk, and regime-switching rules are selected by CPCV
on development returns at 25 bps, then frozen for the 2025–2026 holdout and the
10/25/50/100 bps cost comparison. It never fits or recalibrates a forecast model.

Recognized derivatives columns are `funding_rate`, `open_interest`, `basis`,
`liquidations`, `long_liquidations`, and `short_liquidations`. Recognized options
columns include `atm_iv_7d`, `atm_iv_30d`, `put_call_skew_25d`, `put_skew_25d`,
`iv_term_slope`, `options_volume`, and `options_open_interest`. These inputs are
lagged one day by default. Missing feature families are reported as unavailable;
the runner never manufactures proxies and never treats spot OHLCV as derivatives.

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
- `crypto_mlsystem.derivatives_data`: public Binance derivatives collection, raw persistence, coverage accounting, and daily normalization.
- `crypto_mlsystem.derivatives_features`: lagged funding, basis, positioning, crowding, market-state, and derivatives-target construction.
- `crypto_mlsystem.derivatives_research`: purged walk-forward predictive tests and predeclared BTC/ETH/cash derivatives strategies.
- `crypto_mlsystem.wrds_inventory`: optional WRDS library/table discovery, external-risk-regime feature planning, and next-strategy specification.
- `crypto_mlsystem.public_crypto_data`: public CoinGecko, DefiLlama, Binance 4h, and token-unlock availability integration.
- `crypto_mlsystem.feature_research`: pre-strategy feature IC, quantile, stability, redundancy, and feature-tier analysis.

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

For a changing, point-in-time top-20/top-50 universe, download the broad exchange
cross-section rather than today's top assets, then run both experiments:

```bash
python -m src.download_data --exchange binance --quote USDT --historical-universe --since 2022-01-01 --output data/binance_usdt_broad_2022.csv
python -m src.run_real_results --data data/binance_usdt_broad_2022.csv --sizes 20 50 --model logistic_regression --cost-bps 25
```

Membership is formed at each month start using the prior 30 days' median dollar
turnover and a 365-day point-in-time history requirement. Stablecoins, fiat base
assets, wrapped assets, and tokenized commodities are excluded. The resulting
membership history is written to `reports/artifacts/real_data_membership.csv`.

The downloader ranks available spot markets by ticker turnover when the exchange exposes `fetch_tickers`, always attempts to include BTC and ETH first, and excludes stablecoins and wrapped assets from the discovered universe. Binance commonly uses `USDT` quote pairs; Coinbase commonly uses `USD` quote pairs. The output CSV matches the research pipeline schema: `date`, `symbol`, `open`, `high`, `low`, `close`, `volume`, and `market_cap`.

After downloading, pass the CSV into the research runner from Python:

```python
from crypto_mlsystem.run_research import run
result = run(data_path="data/binance_ohlcv.csv", top_n=20, model_name="logistic_regression", cost_bps=25)
print(result["result"]["metrics"])
```

Real-data limitations remain important: ccxt exposes the exchange's current market
catalogue, so fully delisted assets may be missing and some survivorship bias
remains. Liquidity is exchange-specific, OHLCV cannot provide true market cap, and
the legacy `run_research` transaction-cost layer charges strategy-allocation
turnover. The extended runner below charges underlying asset-weight turnover.

## Extended signal and meta-label research

The extended runner uses explicit lagged asset-level signals, underlying-asset
turnover costs, volatility-scaled triple-barrier meta-labels, and walk-forward
strategy allocation. To reproduce the 2019 onward research reports:

```bash
python -m src.download_data --exchange binance --quote USDT --historical-universe --since 2019-01-01 --output data/binance_usdt_broad_2019.csv
python -m src.run_extended_research --data data/binance_usdt_broad_2019.csv --output-dir reports/real_data
```

The runner produces the requested subperiod, robustness, diagnostics, and
limitations reports under `reports/real_data/`. Coinbase remains available through
`--exchange coinbase --quote USD` as a separate-venue fallback; histories are not
automatically spliced across exchanges.

## Locked volatility-breakout research

The breakout-focused runner fixes 2019–2021 as training, 2022–2024 as validation,
and 2025 onward as the untouched holdout. Model family, label type, rejection rate,
and confidence threshold are selected without using holdout performance:

```bash
python -m src.run_vol_breakout_research --data data/binance_usdt_broad_2019.csv --output-dir reports/real_data
```

It compares unfiltered breakout signals with binary and probability-weighted ML
filters, drawdown-aware and volatility-targeted exposure, and writes bootstrap,
deflated-Sharpe, and backtest-overfitting diagnostics.

## Defensive momentum paper-trading candidates

The paper-trading candidate runner evaluates a predeclared grid of market-gated
momentum, BTC/ETH defensive rotation, momentum-with-cash, and low-turnover BTC/ETH
trend rules. Candidate and threshold selection uses development-only CPCV; the
2025 onward holdout is opened only after the family winners and primary candidate
are frozen.

```bash
python -m src.run_paper_trading_candidate
```

Reports are written to `reports/paper_trading_candidate/`. The locked acceptance
test requires holdout Sharpe above 0.5, positive CAGR, a drawdown better than BTC,
positive performance at 50 bps, and annual turnover below 12x.
