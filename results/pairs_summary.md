# Strategy 4: Pairs / cointegration stat-arb — summary

Walk-forward (train 180d / test 60d, Engle-Granger re-tested every fold, hedge ratio + spread
mean/std fit only on train), sector buckets L1 / DeFi / Meme from the same universe as strategies
2-3 (same look-ahead-in-universe-construction caveat applies).

| Sector | Pairs tested | Ever cointegrated (walk-forward) | Mean Sharpe (cointegrated) | Median Sharpe | % pairs net-positive |
|---|---|---|---|---|---|
| L1   | 36 | 11 (31%) | 0.19  | 0.04  | 54.5% |
| DeFi | 15 | 7 (47%)  | -0.35 | -0.13 | 42.9% |
| Meme | 6  | 3 (50%)  | 0.54  | 0.76  | 66.7% |

Full per-pair breakdown: `results/pairs_<sector-seed-symbol>_per_pair.csv`. Raw: `results/pairs_raw.json`.

**Critical caveat: trade counts per pair are tiny.** Best/worst pairs shown in the raw output
typically have **1-3 total trades** across the whole 2-year walk-forward run (e.g. best L1 pair
ADAUSDT/TRXUSDT: 1 trade; best Meme pair PEPEUSDT/BONKUSDT: 3 trades). This is drastically below
the 30-trade noise floor. A single 9% or 14.5% "return" on one trade is not evidence of an edge —
it is one z-score excursion that happened to mean-revert once. The cointegration hit rate (31-50%
of pairs cointegrate in at least one fold) is itself informative and above what pure chance at a
5% p-value threshold would suggest, meaning genuine relationships likely exist among some of these
assets -- but the trading rule built on top of them does not generate enough signal frequency at
daily-bar/2-year-history resolution to say anything about its Sharpe.

**Verdict:** No reliable stat-arb edge demonstrated. Mean/median Sharpe across all pairs that ever
cointegrated cluster near zero (DeFi sector is net negative on average). Trade frequency is far too
low for the Sharpe numbers on individual "best" pairs to mean anything — this is the exact trap the
task warned about (a pair that only cointegrates in-sample, or trades once, is not a strategy).
Higher-frequency (intraday) data would be needed to get meaningful trade counts per pair; that data
is not available from the free sources used here.
