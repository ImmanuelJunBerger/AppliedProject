# Track A1: Point-in-time cross-sectional momentum — summary

Universe pool: all 440 currently-listed non-stablecoin USDT spot pairs on Binance (vs. Run 1's
pre-selected top-50-by-today's-volume). At each weekly rebalance, eligibility and the top-50
volume-ranked pool are computed using **only trailing data available as of that date** — no
future information. 105 (7d/14d) or 103 (30d) weekly rebalances over the same 2024-06 to 2026-07
window as Run 1.

| Variant | Gross Sharpe | Net Sharpe (full) | Net Sharpe (IS) | Net Sharpe (holdout) | Trades | DSR (n_trials=6) |
|---|---|---|---|---|---|---|
| 7d long/short  | -0.64 | -1.43 | -1.10 | -2.17 | 105 | 0.023 |
| 7d long-only   | -1.50 | -1.80 | -1.35 | -3.20 | 105 | 0.068 |
| 14d long/short | -0.28 | -0.85 | -0.40 | -1.92 | 105 | 0.003 |
| 14d long-only  | -1.41 | -1.64 | -1.20 | -3.01 | 105 | 0.008 |
| 30d long/short | -0.94 | -1.36 | -0.77 | -2.70 | 103 | 0.022 |
| 30d long-only  | -1.28 | -1.45 | -0.80 | -3.37 | 103 | 0.110 |

Full metrics: `results/pit_momentum_raw.json`. Equity curves: `results/pit_momentum_<variant>_net_equity.csv`.

**Result: the fix confirms the suspicion. Run 1's headline 0.86 net Sharpe (7d, long-only,
look-ahead universe) fully inverts to -1.80 once the universe is point-in-time correct.** Every one
of the 6 tested variants is negative gross AND net, both in-sample and holdout — this is not a
borderline result. The 7d long-only equity curve declines from 1,000 EUR to ~23 EUR (net) over the
2-year window, gradually and monotonically (checked directly, not a single-bar blowup) — consistent
with a well-documented, mundane phenomenon: most altcoins depreciate steadily against USD/BTC over
multi-year windows, and buying recent-volume-ranked momentum winners in a broad, mostly-low-quality
altcoin pool repeatedly buys tokens near local tops of pump cycles that then bleed out. Deflated
Sharpe (accounting for the 6 parameter variants tested) confirms this is not noise in the "looks
bad" direction either — these are genuinely, robustly negative results, not just unlucky draws.

**Residual, disclosed, uncorrectable bias**: the 440-symbol pool is still every symbol *currently*
listed on Binance — tokens that fully delisted between 2024 and now are invisible to this method,
same as Run 1. This fixes the ranking-date look-ahead (the specific bug identified in Run 1) but
does not fix delisted-token survivorship. Given the result is unambiguously negative even with this
remaining upward bias still present, the true (uncorrectable) result is presumably even worse.

**Verdict: Run 1's momentum lead is dead. It was a look-ahead artifact, not a real signal.**
Cross-sectional volume-momentum on Binance-listed alts, done honestly, loses money — sometimes
catastrophically — net of costs. This is the single highest-value finding of Run 2's Track A,
exactly as anticipated when this test was pre-registered.
