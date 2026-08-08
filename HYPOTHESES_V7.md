# HYPOTHESES_V7.md — Pre-registered hypothesis ledger (Run 7 discovery program)

**Written 2026-08-08, BEFORE any Run-7 strategy was backtested.** Data partitions were locked
first (`src/partitions.py`, `results_v7/partitions.json`), then the universe was assembled, then
this document was written. No strategy P&L had been computed at the time of writing.

**Declared trial budget: 85 primary hypotheses.** Parameter variants, filters, overlays and
abandoned ideas all count additionally and are appended to `results_v7/trials_ledger.csv`. The
Deflated Sharpe is computed against the **total** row count of that ledger, not against 85 and not
against the survivor's own variant count.

**Standing rule for this document:** no mechanism, no test. Every row below names *who loses money
and why they cannot stop*. Where I could not write a credible loser, the idea was dropped before
testing rather than tested "just to see" — that is the main lever against false positives, and
dropped-for-no-mechanism ideas are listed in §9.

---

## Data foundation (assembled before hypothesis generation)

| Property | Value |
|---|---|
| Source | **Binance USD-M futures bulk archive** (`data.binance.vision`) — not geo-blocked, unlike the API (451) |
| Span | 2021-01-01 → 2026-08-01 (2,038 days ≈ 5.6 years) |
| Bars | 1h klines; BTC verified 48,912 bars, **zero missing, zero duplicates** |
| Funding | Real 8h prints, full span (vs Run 6's 95-day OKX window) |
| Positioning | 5-min `metrics`: open interest, top-trader L/S (account + position), overall account L/S, taker buy/sell ratio → resampled to 1h |
| Implied vol | Deribit DVOL hourly, 22,193 prints from 2021-03 |
| **Survivorship** | **FIXED.** Universe = 117 symbols alive at 2021-06 **including the 14 that later died** (LUNAUSDT, SRMUSDT, BZRXUSDT, TOMOUSDT, EOSUSDT, MATICUSDT, BTTUSDT, HNTUSDT, KEEPUSDT, AKROUSDT, BTSUSDT, DODOUSDT, SXPUSDT, YFIIUSDT) + 20 major later listings, entering only from their own listing date |

Run 6 had to disclose survivorship as uncorrectable. Here LUNA — the single most famous crypto
death — is *in* the universe. This materially changes what a cross-sectional test means.

---

## Partitions (locked before idea generation)

| Partition | Period | Days | Use |
|---|---|---|---|
| Development | 2021-01-01 → 2024-05-07 | 1,222 (60%) | Idea generation, screening, parameter selection |
| Validation | 2024-05-07 → 2025-09-29 | 510 (25%) | Walk-forward + gates. Look, never fit. |
| **Final holdout** | **2025-09-29 → 2026-08-01** | **306 (15%)** | **LOCKED. Max 3 touches, enforced in code.** |

`src/partitions.py::log_holdout_touch` raises rather than allowing a 4th read.

---

## Family A — Flow & positioning (15) — *prioritised: crypto-native, no TradFi equivalent*

The mechanism that makes this family special: leverage is **visible** (OI, funding, L/S ratios are
public) and liquidation is **mechanical**. A forced seller cannot choose to wait.

| ID | Hypothesis | Mechanism — who loses and why they can't stop | Hold | Falsifier |
|---|---|---|---|---|
| A01 | Long when funding z-score is extremely negative | Shorts are paying longs to hold; crowded shorts must keep paying or close, and a squeeze forces closure at the worst price | 8–48h | No positive drift after extreme negative funding |
| A02 | Short when funding z-score is extremely positive | Symmetric: crowded longs bleed carry and are the first liquidated on a dip | 8–48h | No negative drift after extreme positive funding |
| A03 | Funding carry: short perp when funding is persistently positive | Leveraged longs structurally pay for leverage; they can't stop because the position *is* the leverage | days | Carry < costs, or price drift offsets carry |
| A04 | Funding sign-flip as regime change | Flip marks positioning regime turn; late longs unwind into it | 8–72h | Flips carry no information |
| A05 | Cross-sectional funding rank: long cheapest-funded, short dearest | Dollar-neutral harvest of the same carry, market beta removed | days | Rank spread doesn't pay |
| A06 | OI↑ & price↑ → fade (crowded longs) | New leveraged longs pile in at highs; they are weak hands with liquidation prices just below | 4–24h | No reversal after leveraged rallies |
| A07 | OI↓ & price↑ → follow (short squeeze) | Shorts covering *is* the buying; squeeze continues until shorts are exhausted | 4–24h | No continuation |
| A08 | OI↑ & price↓ → fade (new shorts crowding) | Fresh shorts at lows are squeeze fuel | 4–24h | No bounce |
| A09 | OI↓ & price↓ → buy (long capitulation done) | Forced longs have finished exiting; supply exhausted | 4–24h | No bounce |
| A10 | OI rate-of-change extreme → fade | Rapid leverage build-up is fragile by construction | 4–24h | Leverage build-up doesn't predict reversal |
| A11 | Top-trader long/short ratio extreme → **follow** | Top traders are the informed cohort; retail is the counterparty | 8–48h | Top traders have no edge |
| A12 | Retail account long/short ratio extreme → **fade** | Retail account-count skew marks the crowded, under-capitalised side | 8–48h | Retail skew uninformative |
| A13 | Taker buy/sell volume ratio extreme → fade | Aggressive market-order flow pays the spread and is impatient; impatience is compensated by the passive side | 1–12h | No reversal after aggressive flow |
| A14 | Funding paid vs realised drift (is carry actually compensated?) | Diagnostic: tests whether the funding premium is a risk premium or a free lunch | n/a | Drift exactly offsets funding (efficient) |
| A15 | **Cascade reversion, restructured** — long side only, higher z, longer hold, maker entry | Run 6's diagnosis: the long side was gross-POSITIVE (+18 bps) and cost-killed, the short side was wrong-signed. Structural fix, logged as a NEW trial | 12–48h | Long side gross still < round-trip cost |

## Family B — Cross-sectional (12)

Rank-based and dollar-neutral, so market beta is removed by construction rather than hoped away.

| ID | Hypothesis | Mechanism | Hold | Falsifier |
|---|---|---|---|---|
| B01–B04 | Momentum, 1d / 3d / 7d / 30d lookback, long top decile / short bottom | Slow information diffusion across a fragmented retail market; attention flows to recent winners | 1–7d | No rank persistence |
| B05–B07 | Short-horizon reversal, 1h / 3h / 6h | Liquidity provision: someone must be paid to absorb impatient flow | 1–6h | Reversal < spread |
| B08 | Idiosyncratic-vol ranking (long low idio-vol) | Lottery-preference: retail overpays for high-idio-vol "moonshots" | days | No idio-vol premium |
| B09 | Beta-to-BTC ranking (low-beta anomaly) | Leverage-constrained traders buy high-beta instead of levering low-beta | days | No low-beta premium |
| B10 | Funding-adjusted momentum (momentum net of carry) | Momentum winners often have expensive funding; net signal should dominate raw | 1–7d | No improvement over raw momentum |
| B11 | Liquidity-scaled momentum (rank ÷ ADV) | Edge should concentrate where liquidity is thin, if it's a compensation-for-liquidity story | 1–7d | Edge unrelated to liquidity |
| B12 | Sector rotation (L1 / DeFi / meme / AI-RWA) | Narrative capital rotates in blocks; sector membership is stable and public | 3–14d | No sector-level persistence |

## Family C — Volatility (10)

Vol is the most autocorrelated quantity in crypto, so vol forecasts are more reliable than return
forecasts. Most of this family's value is expected to be as **sizing/overlay**, not standalone.

| ID | Hypothesis | Mechanism | Hold | Falsifier |
|---|---|---|---|---|
| C01 | Realised-vol compression → expansion breakout | Option sellers and market makers suppress vol until inventory forces a re-price | 4–48h | Compression doesn't precede expansion |
| C02 | Variance risk premium: DVOL implied vs realised | Insurance buyers (protective puts, structured products) systematically overpay | days | IV ≈ RV on average |
| C03 | VRP as a directional filter (high VRP → risk-on) | High premium marks fear that is over-priced | days | VRP uninformative for direction |
| C04 | Vol-of-vol regime classification | Regime switch cost is borne by fixed-parameter traders | days | No regime persistence |
| C05 | Range expansion after NR-style contraction | Same as C01 at bar level | 4–24h | No expansion |
| C06 | **Vol-forecast sizing overlay** applied to other strategies | Not a signal — a risk transform. Equal-risk beats equal-notional when vol varies 5x | n/a | Overlay doesn't improve Sharpe |
| C07 | DVOL term structure slope | Term premium in vol | days | No slope information |
| C08 | Intraday vol seasonality (size by hour) | Participant mix genuinely differs by session | n/a | Flat vol surface |
| C09 | Vol persistence (high vol → high vol) | Well-documented clustering; used for sizing | n/a | No clustering |
| C10 | Regime-conditional: mean-revert in high vol, trend in low vol | Different microstructure regimes reward different behaviour | 4–48h | No interaction |

## Family D — Time & microstructure (12)

Structural because the *participant mix* genuinely changes by clock — not a statistical fluke.
**Flagged as the highest false-positive-risk family** (many buckets, weak priors), so it is held to
the strictest reading and every bucket counts toward the trial total.

| ID | Hypothesis | Mechanism | Hold | Falsifier |
|---|---|---|---|---|
| D01–D03 | Asia / Europe / US session open drift | Regional retail wakes and trades directionally into thin books | 1–8h | No session skew |
| D04–D05 | Europe / US session close drift | Position squaring before desks go home | 1–4h | No close effect |
| D06 | Pre-funding-settlement drift (hour before 00/08/16 UTC) | Traders dodge a known, scheduled payment; the dodge is predictable | 1h | No pre-settlement move |
| D07 | Post-funding-settlement drift | Positions re-established after payment avoided | 1–4h | No post move |
| D08 | Settlement drift **conditional on funding sign** | The dodge should only exist when the payment is large | 1–4h | No conditioning effect |
| D09 | Weekend thinness → exaggerated moves revert | Institutional liquidity absent; retail moves price further than warranted | 1–3d | No weekend distortion |
| D10 | Monday gap continuation/reversal | Weekend news repriced at institutional open | 1–2d | No gap effect |
| D11 | Hour-of-day return surface | As D01–D05, tested exhaustively | 1h | Flat surface |
| D12 | Day-of-week return surface | As above | 1d | Flat surface |

## Family E — Statistical arbitrage (10)

| ID | Hypothesis | Mechanism | Hold | Falsifier |
|---|---|---|---|---|
| E01 | ETH/BTC cointegration z-score | Two dominant assets share macro drivers; dislocations are inventory-driven | 4–72h | No cointegration out of sample |
| E02 | L1 basket cointegration | Same sector, same beta drivers | 4–72h | Basket doesn't cointegrate |
| E03 | Basket vs constituent dislocation | Index-like flow hits the basket unevenly | 4–48h | No dislocation |
| E04 | BTC leads alts (lead-lag at 1h) | Information arrives in BTC first; alt market makers update with lag | 1–6h | No lead-lag |
| E05 | ETH leads alts | As E04 within the alt complex | 1–6h | No lead-lag |
| E06 | Residual reversion after beta-hedging to BTC | Idiosyncratic moves are liquidity events, not information | 1–12h | Residuals are random walks |
| E07 | Within-sector pairs z-score | Closest substitutes should not diverge persistently | 4–72h | Pairs don't revert |
| E08 | Beta-hedged spread z-score | As E07, beta-neutral | 4–72h | No reversion |
| E09 | Alt-vs-BTC relative-strength reversion | Alt/BTC ratio is itself mean-reverting within regimes | 1–7d | Ratio trends |
| E10 | Correlation-breakdown trade | Correlation spikes are forced-deleveraging signatures | 1–7d | No breakdown signal |

## Family F — On-chain (8) — **DATA CHECK REQUIRED BEFORE TESTING**

Realistically multi-day signals; weak at hourly. F01–F08 cover exchange netflows, stablecoin
supply, MVRV, SOPR, dormancy, whale accumulation, chain fees, active addresses.

**No free, historical, point-in-time on-chain source has been verified reachable from this
environment.** Glassnode/CryptoQuant/Nansen are paid. If probing fails, this family is logged
**SKIPPED — insufficient data**, zero trials counted, and reported as untested rather than as
"tested and failed". The distinction matters: a barren family and an unmeasured family teach
different things.

## Family G — Macro & regime overlays (10)

Tested as **filters on other strategies**, not standalone signals, because that is how they are
actually usable.

| ID | Hypothesis | Mechanism |
|---|---|---|
| G01 | BTC-dominance regime switches BTC vs alt exposure | Capital rotates between BTC and alts in identifiable regimes |
| G02 | Trend/chop classifier as on/off gate | Mean-reversion and trend strategies fail in each other's regime |
| G03–G05 | DXY / SPX / VIX correlation-regime filters | Crypto's macro beta is regime-dependent |
| G06 | Realised-vol regime filter overlay | Size down when vol regime shifts |
| G07 | Market-wide funding as a risk gate | Aggregate funding = aggregate leverage = fragility |
| G08 | Time-since-ATH regime | Distance from highs proxies holder pain |
| G09 | Drawdown-state regime | As G08 |
| G10 | Combined overlay applied to Tier-2 survivors | Best overlay stacked on best signal |

## Family H — Event-driven (8)

| ID | Hypothesis | Mechanism | Data status |
|---|---|---|---|
| H01 | Listing-announcement drift | Forced index/tracker buying + attention | Announcement timestamps **not freely available** → likely SKIP |
| H02 | **New perp listing: first-N-days behaviour** | Derivable from the archive itself (symbol's first file = listing date). Listing brings leverage to a previously spot-only asset; early leverage is badly priced | **TESTABLE** |
| H03 | Token unlock schedules | Known supply shock, price-insensitive sellers | Unlock calendars paid (Run 3 found DeFiLlama 402) → SKIP |
| H04 | **Delisting run-up** | Derivable: symbol's last file = delisting. Forced closure of all positions | **TESTABLE** |
| H05 | Quarterly futures expiry | Calendar-known roll flow | Derivable |
| H06 | Monthly options expiry (Deribit, last Friday) | Dealer gamma unwinds on a known date | Derivable |
| H07 | Post-listing momentum vs reversal | As H02 | **TESTABLE** |
| H08 | Index inclusion | Forced buying | Not freely available → SKIP |

---

## §9 — Ideas considered and DROPPED for having no credible mechanism

Recorded so the search space is auditable, and so I don't quietly re-introduce them later:

- Moving-average crossovers, RSI/MACD/Bollinger threshold rules, Ichimoku, Elliott waves,
  Fibonacci levels — no identifiable loser; these are chart geometry, not economics.
- "Round number" price magnets *as a standalone directional signal* — the liquidation-clustering
  version (A10-adjacent) has a mechanism, the bare psychological version does not.
- Lunar/calendar-cycle effects, "Uptober"-style folklore — no mechanism, pure data-mining bait.
- Social-media sentiment scores — plausible mechanism but no free point-in-time historical
  source; would be an unverifiable backtest, so not attempted.

---

## Expected outcome, stated in advance

Base rate from Runs 1–6: 120 crypto tests → 0 survivors; 60 TradFi tests → 2 survivors. My prior
is that **0–3 of these 85 survive to holdout**, most likely from Family A (the only family with a
genuinely crypto-native, mechanically-forced loser and now, for the first time in this project,
adequate data). Families D and B are the most likely sources of false positives and are treated
with corresponding suspicion. If nothing survives, that is the reported result.
