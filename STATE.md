# STATE — COMPLETE

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
