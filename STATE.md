# STATE — RUN 5 COMPLETE (see RUN 5 section below; Runs 1-3 sections preserved as history)

## RUN 5 — Multi-Strategy Portfolio Research, Traditional Markets (2026-07-19, fourth session)

**Status: complete.** Note: the task brief referenced "Runs 1-4" and `src/experiment_log.py`,
neither of which exist in this repo's actual history (Runs 1-3 only; closest equivalent is
`src/stats.py`) — corrected in `HYPOTHESES_V5.md` rather than silently fabricated or ignored.

New data sources (all confirmed working, `src/data_tradfi.py`): Kenneth French Data Library, FRED
(via curl subprocess — the `requests` library proved unreliable/hanging against this host through
the environment's proxy in testing), CFTC Commitments of Traders (Socrata API), Yahoo Finance
(requires a `User-Agent` header), Fed FOMC historical meeting-date archive (custom HTML parser,
distinguishes real meeting/statement dates from minutes-release-date mentions and ad-hoc
unscheduled conference calls). Stooq is blocked (JS proof-of-work challenge) and unused.

Tested 9 strategies (S1-S9) + 2 cleanly-skipped (S5 carry, S10 microcap — insufficient free data)
+ 1 reference-only (S7 French factors). N_TESTS=60 (separate registry,
`results/n_tests_registry_v5.csv`, kept independent from Run 2's crypto denominator). Two real
data-quality bugs caught and fixed before publishing (S2's pre-2008 Yahoo `open`-field artifact;
S8's 2020-03-13 PutWrite-index bad print) — both caught by cross-checking against an independent
series, matching this run's own stated prior that "any Sharpe >1 is a bug until proven otherwise."

**Final survivors** (BH-FDR q=0.10 AND positive Sharpe IS+holdout AND structural reason AND
adequate power): **S4 turn-of-month** (Sharpe 0.74 IS / 0.76 holdout, 678 events) and **S2
overnight Nasdaq drift** (0.64 IS / 0.60 holdout, ~14k daily obs). S8 (vol risk premium) is a
near-miss, included flagged (fails strict BH by a small margin, 0.84 correlated with equity market
beta per the correlation matrix, severe tail risk, no EU-retail-accessible instrument). S3
(pre-FOMC drift) looked strong full-sample but its dedicated holdout split shows the effect decayed
to insignificance post-2016 — excluded. S1 (trend) has no clean BH survivor; gold is a near-miss.

**Portfolio**: simple risk parity, vol-targeted 8% ann. 3-strategy (incl. flagged S8): Sharpe 0.90
[CI 0.81-0.99]. 2-strategy (S2+S4 only, the realistic retail version): Sharpe 0.82 [CI 0.74-0.91].
Ablation confirms the run's core thesis empirically: S8 (best standalone Sharpe) contributes LEAST
marginally (+0.075); S4 (weaker standalone Sharpe, much lower correlation) contributes MOST
(+0.128). A trend/yield-curve defensive overlay on the 3-strategy portfolio improves Sharpe to
1.03-1.07 and roughly halves max drawdown (-29.7% -> -14 to -21%).

**Retail feasibility is the binding constraint, not the strategy math**: micro futures require
~$250k-500k EUR for correctly-weighted, non-overleveraged implementation (1 MES+1 MNQ contract
already = ~$94k notional against a strategy designed for ~1x notional exposure). UCITS ETFs solve
this at every capital tier from ~3k EUR up and are the realistic vehicle — but S8 has no accessible
EU retail proxy at all (PRIIPs-blocked), an independent reason (beyond weak diversification value
and tail risk) to exclude it from a real implementation.

Deliverables: `HYPOTHESES_V5.md`, `RESULTS_V5.md`, `src/data_tradfi.py`, `src/tradfi_costs.py`,
`src/stats.py` (extended with a configurable `registry_path` so hypothesis families stay
independent), `src/strategy_tsmom.py`, `src/strategy_overnight.py`, `src/strategy_fomc_drift.py`,
`src/strategy_turn_of_month.py`, `src/strategy_cot.py`, `src/strategy_vol_premium.py`,
`src/strategy_defensive_overlay.py`, `src/portfolio.py`, `results/s{1-9}_*` (raw JSON + summaries +
CSVs), `results/retail_feasibility.md`.

---

# STATE — RUN 3 COMPLETE (see RUN 3 section below; Run 1/2 sections preserved as history)

## RUN 3 — Perp DEX Farming Cost & Breakeven Model (2026-07-18, third session)

**Status: complete.** Not a backtest, not a strategy search — a cost-accounting model for
delta-neutral perp-DEX points farming, reusing Run 1/2's `src/engine.py`, `src/data.py`,
`src/stats.py`. Deliverables: `venues.csv` (10 venues, primary-sources-only), `src/farm_cost.py`
(cost grid + breakeven + speculative scenario grid), `RISKS.md`, `FARMING_COST.md`.

Headline: base case (1,000 EUR, typical fees, 1x leverage, 50x monthly volume multiple) costs
97.68 EUR/month (9.77% of capital); 3-month breakeven airdrop value is 307.04 EUR. At 3x leverage,
empirical BTC/ETH volatility implies 32-65% monthly probability of at least one leg being
liquidated. Only 1 of 10 researched venues (Variational/Omni) has a primary-sourced, currently-live,
pre-TGE points program with an announced allocation %; 2 venues' programs have already concluded
(Hyperliquid Nov 2024, Avantis Feb 2026); 2 venues (Nado, Reya) had the weakest verification quality
(docs domains blocked direct fetch or gave contradictory signals). Payoff side never estimated as a
forecast — only as a user-adjustable scenario grid (108 combinations, 12% show positive expected
net at the illustrative inputs used).

Research method note: used 3 parallel general-purpose research agents (one per venue group) with
an identical, strict source-discipline brief (primary docs/blog/API only; blog-only facts marked
UNVERIFIED and excluded from calculations; STATUS UNKNOWN when program liveness couldn't be
confirmed). Synthesized their findings into `venues.csv` myself rather than trusting agent output
verbatim.

---

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
