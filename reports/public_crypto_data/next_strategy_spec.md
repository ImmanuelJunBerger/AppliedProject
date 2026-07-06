# Next strategy specification: Stablecoin and Market-Liquidity Conditioned BTC/ETH Exposure

## Scope

- Assets: BTC, ETH, cash.
- Direction: long-only spot.
- Rebalance: weekly or biweekly, selected on development data only.
- Costs: 10, 25, 50, 100 bps.
- No leverage.
- No broad strategy search.

## Predeclared exposure rule

At each rebalance date, hold BTC and/or ETH only if all gates are satisfied:

1. Asset trend is positive: 90-day momentum > 0 and price > 200-day moving average.
2. 4h confirmation is positive when available: lagged 4h 7-day trend > 0.
3. Stablecoin liquidity is expanding over the candidate lookback window.
4. BTC/ETH basket drawdown is not worse than the candidate drawdown threshold.
5. Existing volatility-expansion probability is below the candidate high-risk threshold.

If no asset is eligible or any market gate fails, hold cash.

## Development-only candidate set

- weekly, 30-day stablecoin expansion, vol-risk threshold 0.80, drawdown threshold -25%.
- weekly, 90-day stablecoin expansion, vol-risk threshold 0.80, drawdown threshold -25%.
- biweekly, 30-day stablecoin expansion, vol-risk threshold 0.80, drawdown threshold -25%.
- biweekly, 90-day stablecoin expansion, vol-risk threshold 0.85, drawdown threshold -30%.

The selected candidate is the highest development Sharpe, breaking ties by
development CAGR and then lower turnover. The locked 2025-2026 evaluation is not
used for selection.

## Acceptance criteria

- Holdout Sharpe > 0.5.
- Holdout CAGR > 0.
- Holdout drawdown better than BTC buy-and-hold.
- Positive Sharpe and CAGR at 50 bps.
- Annual turnover not above 12x.
