# Crypto Strategy Backtest Results — READ THIS FIRST

This report ranks 5 retail-scale (1,000 EUR) crypto strategy families by net-of-cost risk-adjusted
return, using only free, no-key data sources. **Ranking position and "looks good" are not the same
thing as trustworthy.** Read the reliability column before drawing any conclusion.

**Bottom line up front: no strategy here is a demonstrated, trustworthy edge.** The best-looking
net Sharpe numbers (funding carry on XMR/BTC) are built on 9-14 total trades, far below any
threshold for statistical confidence. The strategy with the most trades and best-behaved sample
size (cross-sectional momentum) is contaminated by a structural look-ahead bias in how its universe
was built (today's top-50-by-volume tokens, applied retroactively across 2 years) that inflates its
numbers in a way this dataset cannot correct. Short-horizon reversal loses money outright, even
before costs. Pairs trading shows no edge once trade counts are accounted for. New-launch momentum
could not be backtested at all with free data and is reported as a pure honesty-gate exercise.

**Live trading would be worse than every number below.** This backtest's slippage model is a
liquidity-scaled estimate, not observed fills; it does not model latency, partial fills, exchange
downtime, funding-rate prediction error, or the operational cost of running a 1,000 EUR account
across multiple venues (KYC, withdrawal fees, moving collateral to rebalance a cross-venue
delta-neutral position). Treat every net number here as optimistic.

## Data reality (logged, not assumed)
Probed 2026-07-18 from this execution environment: `api.binance.com` and `fapi.binance.com` return
HTTP 451 (geo-blocked); `api.bybit.com` / `api.bytick.com` return HTTP 403. Working free sources:
Binance spot OHLCV via the `data-api.binance.vision` mirror, OKX public spot/perp/funding API,
Hyperliquid public `info` API (perp OHLCV + funding), DexScreener public API. All backtests below
are built exclusively from these four sources — nothing fabricated, nothing pulled from a paid feed.

## Ranked summary (primary metric: net Sharpe, tiebreak: max drawdown)

| Rank | Strategy | Net Sharpe | Net return | Max DD | Trades | Reliable? |
|---|---|---|---|---|---|---|
| 1 | Funding carry — HL XMR (perp) + Binance spot proxy | 6.22 | +7.5% | -1.7% | 9 | **NO — 9 trades, 183d sample** |
| 2 | Funding carry — HL BTC (perp) + Binance spot proxy | 1.98 | +1.9% | -0.6% | 13 | **NO — 13 trades** |
| 3 | Momentum — 7d lookback, long-only | 0.86 | +126.6% | -60.6% | 106 | **NO — universe look-ahead bias; OOS decays** |
| 4 | Funding carry — HL ETH (perp) + Binance spot proxy | 0.72 | +0.6% | -1.3% | 12 | **NO — 12 trades** |
| 5 | Momentum — 30d lookback, long-only | 0.51 | +31.7% | -64.2% | 98 | **NO — same bias; OOS negative** |
| 6 | Pairs — Meme sector (mean across cointegrated pairs) | 0.54 | n/a (avg) | n/a | 1-3/pair | **NO — 1-3 trades per pair** |
| 7 | Momentum — 14d lookback, long/short | 0.45 | +22.4% | -55.2% | 93 | **NO — same bias; OOS negative** |
| 8 | Momentum — 7d lookback, long/short | 0.43 | +20.2% | -51.9% | 106 | **NO — same bias** |
| 9 | Momentum — 14d lookback, long-only | 0.44 | +13.4% | -64.3% | 93 | **NO — same bias; OOS negative** |
| 10 | Pairs — L1 sector (mean across cointegrated pairs) | 0.19 | n/a (avg) | n/a | 1-11/pair | **NO — near-zero, thin trades** |
| 11 | Funding carry — OKX majors (BTC/ETH/SOL/DOGE/XRP, same-venue) | 0.00 | 0.0% | 0.0% | 0 | Clean null result — never triggered |
| 12 | Momentum — 30d lookback, long/short | 0.21 | -7.7% | -54.1% | 91 | **NO — negative, same bias** |
| 13 | Pairs — DeFi sector (mean across cointegrated pairs) | -0.35 | n/a (avg) | n/a | 2-59/pair | **NO — net negative on average** |
| — | New-launch / DexScreener momentum | n/a | n/a | n/a | n/a | **No backtest possible — free data insufficient** |
| 14 | Funding carry — HL SOL (perp) + Binance spot proxy | -1.92 | -4.1% | -5.1% | 14 | **NO — negative, 14 trades** |
| 15 | Reversal — 3d lookback | -4.18 | -99.3% (net) | -99.4% | 653 | Reliable sample size; strategy fails outright |
| 16 | Reversal — 2d lookback | -4.33 | -99.4% (net) | -99.5% | 654 | Reliable sample size; strategy fails outright |
| 17 | Reversal — 1d lookback | -6.64 | -99.95% (net) | -99.95% | 655 | Reliable sample size; strategy fails outright |

Full per-strategy detail, gross-vs-net breakdowns, and raw JSON/CSV are in `results/`.

## Per-strategy honest verdicts

**1. Funding-rate carry (delta-neutral).** OKX same-venue (BTC/ETH/SOL/DOGE/XRP, ~94 days of
funding history — OKX's free endpoint only retains ~3 months): realized funding never cleared the
~11%/yr round-trip cost threshold on any instrument, so the strategy never entered a single trade.
This is a genuine null result, not a bug. Hyperliquid perp + Binance spot proxy (BTC/ETH/SOL/XMR,
~400/183 days, hourly funding): BTC and ETH show small positive net-of-cost edges, SOL is negative,
XMR looks strong (25%/yr average funding) — but every one of these runs on 9-14 total trades, well
under the 30-trade reliability floor, and the HL leg is hedged against a *different venue's* spot
price with no basis-risk model. **Top caveat: not enough trades to trust any of these numbers, and
cross-venue basis risk is unmodeled.**

**2. Cross-sectional momentum.** Full-sample net Sharpe up to 0.86 (7d, long-only) looks like the
best-behaved result of the whole report by trade count (91-106 trades). But the universe is today's
top-50-by-volume tokens applied retroactively across the full 2024-2026 window — literally 0 of 50
symbols have 90%+ price history across that window, meaning the backtest is dominated by tokens
that only became liquid/relevant recently. This is look-ahead bias in universe construction, not
correctable with the data available, and it biases every number here upward. The out-of-sample
split (first 60% vs last 40%) shows most lookback/variant combinations decay or flip sign OOS.
**Top caveat: universe selection itself is not point-in-time; treat all numbers as an upper bound.**

**3. Short-horizon reversal.** Loses money **before any fees are applied** at all three lookbacks
(1/2/3 day). Daily long-biggest-losers/short-biggest-winners behaved like anti-reversal in this
2024-2026 sample: short-horizon momentum dominated, not mean reversion. With ~653-655 trades of
daily turnover on top of an already-negative gross signal, net-of-cost results are a near-total
capital wipeout. **This is a valid, well-powered negative finding, not a data problem.**

**4. Pairs / cointegration stat-arb.** 31-50% of tested pairs cointegrate in at least one
walk-forward fold (above what pure chance at a 5% p-value threshold would suggest, so the
relationships are likely real). But mean/median Sharpe across all pairs that ever cointegrated
clusters near zero (DeFi sector net negative on average), and per-pair trade counts are almost
always 1-3 over the full 2-year run — far too thin to say anything about Sharpe. **Top caveat:
cointegration existing is not the same as a tradeable, frequent-enough signal at daily-bar
resolution.**

**5. New-launch / DexScreener momentum — honesty gate.** No backtest was run: free data gives only
a live snapshot, not a historical launch panel, so there is no point-in-time data to backtest
against without fabrication. What was measured instead: of 30 tokens from DexScreener's "latest
profiles" feed (mostly Solana pump.fun launches), **≥20% were already dead/illiquid** by the time
of the query — a real, computed lower bound on attrition (true rate is almost certainly higher,
since fully-delisted tokens are invisible to this method too). The median 24h price change among
survivors (+46.2%) is explicitly **not** a strategy return — it describes only the tokens that
happened to still be alive, which is survivorship bias by definition. **No tradeable edge is
claimed here.**

## Cost assumptions applied to every backtest
Taker fees: 5bps/side perp, 10bps/side spot. Slippage: 5bps flat for BTC/ETH-class majors; alts
start at a 20bps floor and scale with order-notional / daily-quote-volume participation, capped at
100bps. Funding: real historical 8h (OKX) / 1h (Hyperliquid) funding applied to any perp position
held across a funding timestamp. See `src/engine.py` for the exact implementation.

## What would change this conclusion
A paid/keyed data source with (a) full historical delisted-token coverage for the momentum/reversal
universe, (b) longer funding-rate history than OKX's free 3-month retention, and (c) a real
point-in-time new-launch panel including rugs, would let every "NO — insufficient sample /
look-ahead bias" caveat above actually be tested properly. None of that was available here, and no
data was fabricated to fill the gap.
