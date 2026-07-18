# Strategy 2: Cross-sectional momentum — summary

Universe: current top-50 non-stablecoin USDT spot pairs by volume on Binance, 2024-03-26 to
2026-07-18 (845 daily bars). Weekly rebalance, next-bar execution, quintile (10/50) long-top /
short-bottom, equal-weighted.

**Full-sample net-of-cost results** (gross vs net, per lookback):
| Lookback | Variant | Gross Sharpe | Net Sharpe | Net total return | Net maxDD | Trades |
|---|---|---|---|---|---|---|
| 7d  | long/short | 1.15 | 0.43 | +20.2% | -51.9% | 106 |
| 7d  | long-only  | 1.14 | 0.86 | +126.6% | -60.6% | 106 |
| 14d | long/short | 1.41 | 0.45 | +22.4% | -55.2% | 93 |
| 14d | long-only  | (see raw) | 0.44 | +13.4% | -64.3% | 93 |
| 30d | long/short | (see raw) | 0.21 | -7.7% | -54.1% | 91 |
| 30d | long-only  | (see raw) | 0.51 | +31.7% | -64.2% | 98 |

Full metrics: `results/momentum_raw.json`. Equity curves: `results/momentum_<lb>_<ls|lo>_{gross,net}_equity.csv`.

**Out-of-sample split** (first 60% vs last 40% of the window, `results/momentum_oos_split.json`):
every lookback except 7d-long/short **decays or inverts** out-of-sample — 14d and 30d both go from
double-digit-Sharpe in-sample to negative Sharpe out-of-sample. 7d long-only similarly collapses
from Sharpe 1.26 (IS) to 0.24 (OOS). Only 7d long/short improves OOS, which on 6 tested variants is
as consistent with noise as with a real effect.

**Critical caveat — universe construction is not point-in-time.** `symbols_with_near_full_history`
= **0 of 50**: not one of today's top-50-by-volume tokens has 90%+ price history across the full
2024-03-26..2026-07-18 window. The universe is today's winners projected backward — a token that
pumped into the top 50 in 2026 is included for its whole (short) history, while tokens that were
liquid in 2024 but have since faded or delisted are invisible to this dataset. This is look-ahead
bias baked into the universe, not just standard survivorship, and it is NOT correctable with the
free data sources available here. **Results are biased upward and should be read as an upper
bound, not an estimate of a tradeable edge.**

**Verdict:** Full-sample net numbers look attractive (up to Sharpe 0.86, long-only 7d), but (a) the
universe bias above is severe and structural, and (b) the OOS split shows the edge is unstable
across lookbacks and time. Do not trust this as a standalone signal; at best it's weak evidence
that short-lookback (7d) long-only momentum had a period of working, in a data sample that is
itself contaminated by hindsight token selection.
