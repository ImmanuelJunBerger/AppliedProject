# S2: Overnight vs. intraday decomposition — summary

**Bug caught before publishing (exactly what this run was told to hunt for):** Yahoo's daily
`open` field for `^GSPC` equals the PRIOR close for ~94% of records before 2008 (no real recorded
intraday open), and for `^DJI` before ~1996 — an initial full-history run therefore assigned almost
the entire multi-decade return to the "intraday" bucket by construction, producing a spurious 3730%
cumulative "intraday" return for SPX that contradicted the literature. `^IXIC`'s open field is
genuine back to 1971 (checked, <1% match rate every year). **Fixed**: each index restricted to its
own verified-clean start year (SPX 2008+, DJI 1996+, IXIC 1971+) before any result is reported.

| Index (clean period) | Overnight gross Sharpe | Overnight net Sharpe (full/IS/holdout) | Intraday gross Sharpe | Intraday net Sharpe (full/IS/holdout) |
|---|---|---|---|---|
| SPX (2008+) | 0.66 | 0.28 / 0.14 / 0.56 | 0.35 | 0.21 / 0.17 / 0.32 |
| DJI (1996+) | 0.18 | -0.36 / **-4.02** / 0.42 | 0.49 | 0.34 / 0.39 / 0.20 |
| IXIC (1971+) | **0.84** | **0.63 / 0.64 / 0.60** | 0.13 | -0.03 / -0.16 / 0.27 |

Full metrics: `results/s2_overnight_raw.json`. Per-series returns: `results/s2_overnight_*_net_returns.csv`.

**With clean data, the classic direction (overnight > intraday) reappears for SPX and IXIC** — a
useful sanity anchor against the literature. **IXIC's overnight effect is large, consistent across
55 years, and survives holdout (0.60) essentially unchanged from in-sample (0.64)** — the strongest,
cleanest single result in the entire Run 5 candidate set so far. SPX is weaker but directionally
consistent. **DJI inverts**, and its IS Sharpe of -4.02 is not a bug: DJI's gross overnight edge is
already the weakest of the three (0.18) and realized daily volatility of the overnight leg is very
low (~6bps/day in-sample) — a flat 1bp round-trip cost charged 252x/year is enough to flip a small
gross edge decisively negative, and at low volatility that flip produces an extreme-looking
annualized Sharpe. This is precisely the "turnover kills it" outcome flagged as a valid possibility
in the pre-registration, not softened here.

**Caveat carried forward**: none of these numbers should be read as a directly tradeable strategy —
holding cash overnight and equities intraday (or vice versa) requires closing and reopening a full
position every single trading day, and the cost model here is a flat, stated bps assumption, not a
live-quote spread. IXIC's result is the most promising SURVIVOR CANDIDATE for the portfolio step;
DJI's is not.
