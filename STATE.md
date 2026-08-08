# STATE — RUN 7 COMPLETE (see RUN 7 section below; Runs 1-6 preserved as history)

## RUN 7 — Crypto Strategy Discovery Program (2026-08-08, sixth session)

**Status: complete. Verdict NOTHING PASSES — 130 counted trials, 0 survivors, holdout untouched (0/3).**
Full write-up in `RESULTS_V7.md`; pre-registration in `HYPOTHESES_V7.md`.

**Survivorship bias finally FIXED, not just disclosed.** `data.binance.vision` (the bulk archive) is
NOT geo-blocked, unlike `fapi.binance.com` (451), and it retains delisted symbols. Universe = 135
USD-M perps including 14 that died (LUNAUSDT, SRMUSDT, BZRXUSDT, TOMOUSDT, EOSUSDT, MATICUSDT,
BTTUSDT, HNTUSDT, KEEPUSDT, AKROUSDT, BTSUSDT, DODOUSDT, SXPUSDT, YFIIUSDT). Three of the dead rank
top-25 by volume, so it is material. Also unlocked funding back to 2020 (vs Run 6's OKX 95d) and
5-min positioning metrics (OI, top-trader L/S, retail account L/S, taker ratio) for 25 symbols —
family A was untestable in Run 6 and is testable here. S3 listing needs
`s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=...`; the `?prefix=` form on
the main host returns a JS shell. Watch the ms→µs timestamp switch mid-archive.

**Partitions locked BEFORE idea generation** (`src/partitions.py`, `results_v7/partitions.json`):
dev 2021-01-01→2024-05-07 (29,328 bars), val →2025-09-29 (12,240), holdout →2026-08-01 (most recent).
`log_holdout_touch()` raises past 3 touches. Never called — `run_tier3.py` refuses to load the
holdout and asserts the counter is 0.

**Funnel:** 121 Tier-1 trials on development → 4 to Tier 2 on validation → 0 survivors → Tier 3 not run.
- A12 retail-L/S fade: dev Sharpe +1.51 → val **−0.35**. Killed on regime (1/3), bootstrap CI
  [−2.04,+1.31], quarterly 33%, outlier (drop top 5% ⇒ +0.005 → **−1.07** bps/bar), gross/cost 0.72,
  DSR 0.0013. The outlier gate is what caught it; it passed random-entry at the 99th percentile.
- F02/F08 on-chain tilts: val Sharpe 0.91/1.22 but **market-alpha t = 1.17/1.44** and both fail the
  delay placebo. Added `market_alpha` + `beats_buy_hold` gates specifically because a market-wide
  tilt would be flattered by the cross-sectional battery.
- Combination stage VOID (no survivors); run as diagnostics only, inverse-vol Sharpe 0.85, CI
  [−0.85,+2.55], DSR 0.052.

**Headline finding: cost is the binding constraint, not signal quality.** 96 of 121 deaths (79%) were
net-negative-after-costs. Of 72 gross-positive trials, 58 were cost-killed (median gross +0.17 →
net −1.36 bps/bar). Family B long-only momentum is the clean case: gross +1.09/+1.08/+1.02 bps at
7d/3d/1d → net +0.25/−0.02/−0.42. Edge is real and monotonically eaten by turnover. **Highest-value
follow-up: rerun family B under a measured passive/maker execution cost model.**

**Pre-declared skips were partly WRONG and were corrected by an actual probe.** Glassnode/CryptoQuant/
Dune 401 and DeFiLlama emissions 402 (→ F01, F03–F06, H03, H08 genuinely SKIPPED_NO_DATA, excluded
from the DSR denominator as unmeasured-not-falsified), but blockchain.info charts, DeFiLlama
stablecoins and the Binance announcement CMS all return 200 with usable history — so F02/F07/F08/H01
were tested rather than skipped. Daily on-chain series carry a mandatory +1-day availability lag
(`data_onchain.to_hourly_lagged`); without it every one of them fabricates a day of lookahead.

**Gate bug found and corrected mid-run:** the entry-shift placebo originally tested shifts −3…+3 and
required the actual to beat all of them. Negative shifts are LOOKAHEAD, not placebos, and win by
construction (Sharpe 4.10 vs −0.35). Corrected to delays-only, with advances kept as a separate
informational sanity check. Flipped `entry_shift` FAIL→PASS for both A12 variants; **verdict
unchanged**. Corrected re-run logged as two ADDITIONAL ledger rows (raises the DSR denominator =
harder), not as an overwrite.

**Ledger accounting:** `results_v7/trials_ledger.csv`, 141 rows, append-only, row written before each
test. `total_trials()` = 130 and excludes `SKIPPED_NO_DATA` (7, never executed) and `SUPERSEDED`
(4, placeholder skip rows the probe overturned; the real tests have their own ids).

Deliverables: `RESULTS_V7.md`, `HYPOTHESES_V7.md`, `src/{partitions,data_binance,data_onchain,ledger,
panel,signals_v7}.py`, `run_{tier1,skips,family_f,tier2,tier2b,decay,tier3}.py`, `results_v7/*`.
Engine tests still 7/7.

---

# STATE — RUN 6 COMPLETE (see RUN 6 section below; Runs 1-5 preserved as history)

## RUN 6 — Crypto intraday (1h perp) strategy backtest (2026-08-08, fifth session)

**Status: complete. Verdict REJECT — 7 of 8 gates FAIL.**

**Spec gap, handled explicitly:** Section 1 (STRATEGY SPEC) of the task prompt arrived as unfilled
template placeholders -- no hypothesis, universe, or entry/exit rules. Implemented the prompt's own
worked example (liquidation-cascade mean reversion) and isolated the signal behind
`src/strategy.py::build_signal` so a real spec swaps in without touching engine/costs/gates.

**Data:** OKX USDT perps, 20 crypto assets, 1H bars, 2023-08-04..2026-08-08 (26,400 bars/asset).
Integrity: zero missing bars, zero dupes, zero zero-volume bars, zero OHLC violations across all 20.
Filtered out tokenized equities (SNDK/SPCX/MU/XAU/SOXL/INTC...) now polluting OKX's perp volume
rankings. Depth limits found: OKX funding ~95d (only 15% of trades covered -- flatters results),
OKX OI 29d@1H / 179d@1D (so the hypothesis's OI-collapse leg is UNTESTABLE), HL 1h candles ~200d,
Binance futures 451 / Bybit 403.

**Cost-model bug caught before it drove the verdict:** Corwin-Schultz spread estimator returned a
5.0bp median half-spread on BTC perp (~10x reality) because CS is calibrated for daily equity bars
where high-low range is bid-ask bounce, not volatility. Replaced with liquidity-tiered half-spread;
CS retained as pessimistic sensitivity. Verdict is negative under BOTH models at ALL cost levels.

**Result:** 1,134 walk-forward OOS trades. Mean OOS Sharpe -3.74. Win rate 39.8% +/- 1.45%.
Bootstrap Sharpe CI [-4.11, -0.70] entirely below zero. DSR probability 0.0000 on 602 trials.
0/25 parameter-sweep points positive. 0/3 regimes profitable. Worse than 91.5% of random-entry
portfolios. Costs 131% of gross -- but gross is itself negative, so the signal points the wrong way.

**Most useful finding (event study, 14,931 events):** the hypothesis is HALF right. Fading
down-cascades earns +18.06 bps gross (real overshoot, consistent with forced-seller story) but the
~40bp round-trip cost floor is >2x that. Fading up-cascades is actively wrong-signed at -31.44 bps
gross -- violent up moves continue, they don't revert. Not outlier-driven: dropping the top 5% of
trades makes results worse.

**Engine correctness:** 7/7 tests pass -- assert_no_lookahead (synthetic + real), next-bar-open
fills, stop-wins-intrabar-ties, gap-through-stop-fills-at-open, monotonic cost levels,
null-strategy cost identity, kill-switch engagement. Engine numpy-ised for a ~50x speedup
(15s -> 0.31s per 20-asset/26,400-bar run) which made 1,000 random-entry iterations tractable.

Deliverables: `report.md`, `src/{data_intraday,costs,backtest,strategy,validation}.py`,
`run_backtest.py`, `event_study.py`, `make_plots.py`, `tests/test_engine.py`,
`results_v6/` (trials_log.csv with all 633 trials, 8 plots, per-gate JSON).

---

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
