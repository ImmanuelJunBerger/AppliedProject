# Task 4: Liquidation & buffer analysis

**Method**: empirical, not a distributional assumption. Using 400 days of real hourly BTC/ETH price
data (OKX perp, `data/cache/okx_history_candles_{BTC,ETH}-USDT-SWAP_1H_400d.parquet`), computed the
maximum adverse move (running worst drawdown from entry, and running best rally from entry — a long
leg is liquidated by a drawdown, a short leg by a rally) over every possible rolling 30-day (720h)
holding window (8,880 overlapping windows per coin).

**Liquidation-threshold assumption (stated plainly, not hidden in the code)**: liquidation is
modeled as triggering when the adverse move consumes 50% of the position's initial margin cushion
— i.e. `liquidation_threshold = 0.5 / leverage`. This is a simplifying, moderately conservative
approximation of typical cross-margined maintenance-margin mechanics for majors; it is **not** a
venue-specific liquidation formula (those require each venue's own maintenance-margin table, which
was not exhaustively pulled for all 10 venues in Task 1). Treat the exact percentages below as
directionally right, order-of-magnitude correct, not a precise trigger price for any specific venue.

## Probability at least one leg is liquidated within a month

| Coin | Leverage | Liq. threshold | P(long leg liq.) | P(short leg liq.) | **P(either leg liq.)** |
|---|---|---|---|---|---|
| BTC | 1x | 50.0% | 0.0% | 0.0% | **0.0%** |
| BTC | 2x | 25.0% | 12.7% | 0.0% | **12.7%** |
| BTC | 3x | 16.7% | 25.8% | 6.2% | **31.9%** |
| ETH | 1x | 50.0% | 0.0% | 6.1% | **6.1%** |
| ETH | 2x | 25.0% | 25.5% | 15.4% | **40.9%** |
| ETH | 3x | 16.7% | 36.8% | 28.9% | **64.7%** |

**These are large, real numbers from a realized-volatility window, not a stress scenario.** At 3x,
roughly a third of BTC monthly holding periods and nearly two-thirds of ETH ones saw a move big
enough to blow through a 50%-of-margin liquidation threshold on at least one leg. The long-leg and
short-leg probabilities are asymmetric (not identical) because the realized path in this window had
more/larger drawdowns than rallies for BTC and a milder asymmetry for ETH.

## Margin buffer needed for <1% liquidation probability

| Coin | 99th-percentile worst-case 30-day move | Leverage that keeps P(liq.) ≤1% |
|---|---|---|
| BTC | 37.0% | **1.35x** |
| ETH | 61.9% | **0.81x** (i.e. even fully unlevered notional needs an idle cash buffer on top) |

**Knock-on effect on working capital / volume / points**: if a farmer wants to run nominal 3x
leverage to maximize volume-per-euro, but the <1%-liquidation-risk ceiling is 1.35x (BTC) or 0.81x
(ETH), the honest choices are: (a) accept a monthly liquidation probability far above 1% (12-65% per
the table above), or (b) post extra idle margin as a buffer so *effective* leverage stays at the
safe level even though *nominal* leverage is higher. Concretely, for a farmer targeting 3x nominal
leverage on BTC with 1,000 EUR total capital: minimum margin at 3x = 333 EUR/leg; margin required
for the 1.35x safe level on the SAME notional = 741 EUR/leg — a buffer of **~408 EUR (41% of total
1,000 EUR capital) sitting idle, not generating volume or points**, just to keep monthly liquidation
risk near 1%. This is folded directly into the leveraged volume-per-euro figures in `src/farm_cost.py`
and the cost grid in `FARMING_COST.md` — see the "safe-leverage-adjusted" columns there.

Full data: `results/farm_liquidation_probabilities.csv`.

## Caveat on the estimation window
This 400-day window includes a period of substantial realized crypto volatility (consistent with
the large drawdowns already seen in this project's Run 1/Run 2 backtests). If forward volatility is
calmer, these liquidation probabilities would be lower; if crypto's well-documented fat tails
produce another volatile stretch, they could be similar or worse. This is reported as the realized
distribution actually observed, not a forecast of the next 30 days.
