# Track A2: Pooled pairs/cointegration trades — summary

Same walk-forward Engle-Granger selection and z-score trading rule as Run 1 (unchanged), but every
individual trade across all cointegrated pairs (L1/DeFi/Meme sectors) is now pooled into one
distribution instead of reported per-pair.

**Pooled result: 94 trades total (54 in-sample, 40 holdout) — well above the 50-trade floor.**

| Slice | Trades | Mean return/trade | Win rate | Rough ann. Sharpe | p-value | Total P&L (EUR) |
|---|---|---|---|---|---|---|
| All | 94 | -0.43% | 35.1% | -0.28 | 0.83 | -401.86 |
| In-sample | 54 | -0.52% | 27.8% | -0.32 | 0.79 | -279.61 |
| Holdout | 40 | -0.31% | 45.0% | -0.23 | 0.69 | -122.26 |
| Ex best pair (BONK/PENGU dropped) | 92 | -0.68% | 33.7% | -0.49 | 0.95 | -629.62 |
| Ex best month (2025-09 dropped) | 92 | -0.61% | 33.7% | -0.41 | 0.91 | -557.59 |

Deflated Sharpe (in-sample, n_trials=4 sector/pooled variants): probability 0.036 — i.e. essentially
certain this in-sample Sharpe is noise-or-worse, not skill, even before touching holdout.

**Verdict: negative, not just "no edge."** Pooling fixes Run 1's power problem cleanly (94 real
trades vs. 1-3 per pair), and the answer is unambiguous: the pooled strategy loses money in-sample,
loses money in holdout, loses money with the best pair removed, loses money with the best month
removed. It does not even clear "no edge" — it's a small but consistent net loser once fees are
included, both because roughly two-thirds of trades lose and because entry/exit costs on two legs
per trade add up over 94 round trips. The Meme sector shows an eye-catching +15.4 Sharpe, 100% win
rate — on exactly 3 trades, which is the precise trap this run's evidence bar (≥50 trades) exists to
catch; it is excluded from any finding and flagged as noise dressed up as a result.

Full trade-level data: `results/pairs_pooled_trades.csv`. Raw: `results/pairs_pooled_raw.json`.
