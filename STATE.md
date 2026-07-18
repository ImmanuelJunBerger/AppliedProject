# STATE — RUN 2 COMPLETE (see RUN 2 section below; Run 1 section preserved as history)

## RUN 2 — Crypto Edge Hunt v2 (2026-07-18, second session)

**Status: complete.** `HYPOTHESES.md` pre-registered before any Run-2 data work. All Track A and
Track B items executed or cleanly skipped. `RESULTS_V2.md` written. Headline: **120 hypothesis/
variant tests run, 49 produced a p-value, 0 survived Benjamini-Hochberg FDR at q=0.10, 0 cleared
the full minimum-evidence bar.** Run 1's 0.86 momentum Sharpe is confirmed dead (inverts to -1.80
net Sharpe once the universe is point-in-time). Nothing found in Run 2 should be traded.

New infra: `src/stats.py` (train/holdout split, BH-FDR, deflated Sharpe, N_TESTS registry at
`results/n_tests_registry.csv`), `data.fetch_okx_history_candles` (paginated OKX history-candles,
~400 days hourly vs. Run 1's single-call 300-candle cap).

New strategy modules: `src/strategy_momentum_v2.py` (A1, point-in-time universe), 
`src/strategy_pairs_v2.py` (A2, pooled pairs trades), `src/track_b.py` (B1-B9).

Key numbers to remember if resuming further: N_TESTS=120, scored=49, BH survivors=0, raw
p<0.05 survivors=2 (both below trade-count floor: B3 BTC carry n=13, B5 BTC OI n=5).

Residual open items for a hypothetical Run 3: B1 (unlocks) and B8 (listing announcements) remain
untestable without a paid data source. B2/B3's OKX-side depth is capped by OKX's free funding-
history retention (~95-180 days observed this session). Everything else in Track A/B reached a
statistically resolved (mostly negative) conclusion.

---

# STATE — RUN 1 (COMPLETE, preserved for history)

## Environment
- venv at `./.venv`, deps: pandas numpy scipy statsmodels pyarrow requests ccxt — installed OK.
- Network probe (2026-07-18): `data-api.binance.vision` 200, `www.okx.com` 200,
  `api.hyperliquid.xyz` 200, `api.dexscreener.com` 200.
  `api.binance.com` / `fapi.binance.com` -> **451 (geo-blocked)**. `api.bybit.com` / `api.bytick.com` -> **403**.
  => Binance spot OHLCV comes from the `data-api.binance.vision` mirror (works, no key).
     Binance futures/funding is NOT reachable. Perp + funding data comes from **OKX** and
     **Hyperliquid** public APIs instead. New-launch data from DexScreener.

## Done — all 9 planned steps complete
- [x] `src/data.py` — fetch+cache layer for Binance-vision spot OHLCV, OKX perp candles+funding,
      Hyperliquid perp candles+funding+meta, DexScreener search/profiles. Cached to `data/cache/*.parquet`.
- [x] `src/engine.py` — cost model (taker/maker fees, liquidity-scaled slippage, funding P&L),
      `compute_metrics` (Sharpe ann., maxDD, win rate, turnover, net EUR P&L on 1000 EUR base),
      `walk_forward_splits`, `synthetic_ohlcv` for smoke testing only.
- [x] Engine validated on synthetic data (SMA crossover + buy&hold smoke tests, no look-ahead
      confirmed via next-bar signal shift, walk-forward split boundaries verified non-overlapping).
- [x] Strategy 1: funding-rate carry (`src/strategy_funding_carry.py`) — OKX same-venue: funding
      never cleared cost threshold, 0 trades on all 5 instruments (genuine null). HL+Binance-proxy:
      BTC/ETH/XMR small-to-large positive net Sharpe but only 9-14 trades each (below 30-trade
      noise floor, flagged unreliable). `results/funding_carry_summary.md`.
- [x] Strategy 2: cross-sectional momentum (`src/strategy_momentum.py`) — full-sample net Sharpe up
      to 0.86 (7d long-only) but OOS split (first 60%/last 40%) shows decay/inversion for 14d/30d.
      Critical caveat: 0/50 universe symbols have 90%+ history over the 2yr window (universe =
      today's top-50-by-volume applied retroactively = look-ahead bias in universe construction).
      `results/momentum_summary.md`, `results/momentum_oos_split.json`.
- [x] Strategy 3: short-horizon reversal (`src/strategy_reversal.py`) — loses money GROSS (before
      fees) at all three lookbacks (1/2/3d): short-horizon momentum dominates this sample, not
      reversal. Net-of-cost near-total wipeout given ~655 trades/lookback of daily turnover. Valid
      negative finding. `results/reversal_summary.md`.
- [x] Strategy 4: pairs/cointegration stat-arb (`src/strategy_pairs.py`) — L1/DeFi/Meme sectors,
      walk-forward Engle-Granger. 31-50% of pairs cointegrate in >=1 fold (above chance), but
      mean/median Sharpe across cointegrated pairs clusters near zero and per-pair trade counts are
      almost always 1-3 over 2 years — no reliable edge. `results/pairs_summary.md`.
- [x] Strategy 5: DexScreener new-launch momentum (`src/strategy_new_launch.py`) — honesty-gated,
      NO backtest run (no historical launch panel available free). Real measured stat: >=20%
      attrition (dead/illiquid) among 30 profiled tokens within hours of profiling (lower bound).
      Survivor price-change stats explicitly labeled UNRELIABLE, no edge claimed.
      `results/new_launch_summary.md`.
- [x] `RESULTS.md` written — ranked table (net Sharpe primary, maxDD tiebreak), reliability column
      on every row, READ THIS FIRST caveat block, per-strategy honest verdicts, cost assumptions.

## Overall finding
No strategy in this report is a demonstrated, trustworthy edge net of costs. Best Sharpes are on
too few trades (funding carry); the best-powered result (momentum) has structural universe
look-ahead bias; reversal fails outright; pairs show no edge once trade counts are weighted; new-
launch has no backtestable data at all. This null-dominant outcome is itself the honest conclusion
the task asked for.

## If resumed / extended further
- Could deepen momentum/reversal by building a genuinely point-in-time daily-ranked universe
  (requires per-day historical volume ranking, not available from a single current snapshot) to
  remove the look-ahead bias — flagged as the single highest-value follow-up.
- Could extend OKX funding history by stitching multiple free sources' historical funding archives
  (none identified beyond the ~3-month retention window during this session).
- Could add more Hyperliquid alt coins to the funding-carry universe (only BTC/ETH/SOL/XMR tested)
  once a reliable spot-proxy pairing is confirmed for each.

## Key assumptions logged
- Capital: 1,000 EUR. Fees: 5bps taker perp/side, 10bps taker spot/side, 2bps maker perp when resting.
- Slippage: 5bps flat for BTC/ETH-class majors; alts start at 20bps floor, scale with
  order-notional / daily-quote-volume participation, capped at 100bps.
- Binance spot universe used for momentum/reversal excludes stablecoin-quoted pairs, gold/forex
  wrapper tokens, and Binance's tokenized-equity spot pairs (see `data.NON_CRYPTO_BASES` /
  `TOKENIZED_EQUITY_BASES`) — none of these are directional crypto assets.
- Data depth: OKX funding-rate-history free endpoint retains ~3 months (paginated via `after`, not
  `before` — OKX's `before` param returns newer-than, `after` returns older-than, confirmed by
  direct testing). Hyperliquid `fundingHistory` paginated forward in ~500-hour chunks per call to
  build a ~400-day panel.
- Funding-carry delta-neutral legs assume the spot leg's price return equals the perp leg's
  (no basis-risk model) for the Hyperliquid+Binance-proxy variant; OKX same-venue variant has no
  such assumption since both legs are on the same venue.
