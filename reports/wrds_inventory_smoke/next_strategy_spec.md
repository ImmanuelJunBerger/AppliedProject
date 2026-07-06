# Next strategy specification: Macro-Conditioned Crypto Exposure Strategy

## Objective

Test whether external macro/risk-regime data improves a simple BTC/ETH/cash
allocation without adding high turnover or opaque return-prediction models.

This is a design only. Do not backtest until WRDS data coverage is confirmed,
downloaded, normalized, lagged, and frozen.

## Universe

- Assets: BTC, ETH, cash.
- Direction: long-only spot exposure.
- Rebalance: weekly first; biweekly as robustness.
- Costs: 10, 25, 50, and 100 bps.
- Leverage: none.

## Required crypto-state features

- BTC 200-day trend.
- ETH 200-day trend.
- BTC and ETH 30/90-day momentum.
- Existing 7-day volatility-expansion probability.
- BTC/ETH drawdown state.

## Required WRDS/external-state features

- Equity risk trend: S&P 500 or Nasdaq above 200-day average; 30-day momentum.
- VIX regime: VIX level percentile and 5/20-day change.
- USD regime: DXY or broad-dollar trend and 20/60-day momentum.
- Rates regime: 2Y/10Y yield trend, real-yield change, or Fed-funds/SOFR pressure.
- Commodity/risk sentiment: gold, copper, oil, or copper/gold trend if available.
- Optional: ETF flow, RavenPack sentiment, and options-implied volatility only if
  coverage is timely and complete enough for weekly decisions.

## Candidate rules

1. Full exposure condition:
   - BTC or ETH trend is positive.
   - Equity risk trend is positive.
   - VIX is below its trailing high-risk percentile and not rising sharply.
   - USD trend is not strongly positive.
   - Rates shock filter is not hostile.
   - Crypto volatility-expansion probability is not in the high-risk bucket.
2. Asset selection:
   - Hold BTC/ETH 50/50 when both trends are favorable.
   - Tilt 70/30 toward the stronger 90-day volatility-adjusted momentum asset.
   - Hold only the stronger asset if the other is below its 200-day average.
3. Partial exposure condition:
   - If crypto trend is favorable but macro is mixed, hold 25-50% exposure and
     the rest cash.
4. Cash condition:
   - If crypto trend is negative or two or more macro risk filters are hostile,
     hold cash.
5. Drawdown control:
   - If strategy drawdown exceeds a predeclared threshold selected on development
     data only, reduce exposure by half until recovery.

## Why it may generalize

- It uses broad, economically motivated risk-regime variables rather than fitting
  a high-dimensional crypto return model.
- It trades only BTC/ETH/cash, reducing liquidity, survivorship, and execution
  complexity.
- Cash is an explicit state, which is necessary for surviving crypto bear markets.
- Weekly/biweekly cadence keeps turnover manageable.

## Why it may fail

- Macro variables may lag crypto regime changes.
- BTC/ETH can rally during hostile macro states, creating opportunity cost.
- Too many gates can over-filter and leave the strategy underexposed.
- WRDS datasets may be delayed, revised, or unavailable under the current license.

## Acceptance criteria before paper trading

- Candidate selected on development-only CPCV.
- No threshold selection on the locked evaluation period.
- Holdout CAGR above zero.
- Holdout Sharpe above 0.5.
- Max drawdown materially better than BTC buy-and-hold.
- Does not collapse at 50 bps.
- Annual turnover low enough for manual or simple bot execution.
