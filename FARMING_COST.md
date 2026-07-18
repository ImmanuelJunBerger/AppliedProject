# Perp DEX Farming — Cost & Breakeven Model — READ THIS FIRST

**This is a cost-accounting report, not a strategy recommendation. It does not conclude farming is
or isn't "worth it" — that depends on inputs nobody can know (see the SPECULATIVE section) and on
your own risk appetite.**

## The one number that matters most: base-case monthly cost
1,000 EUR capital, delta-neutral across two currently-live-points-program venues with typical fees
(Pacifica + StandX, ~4bps taker/leg), 1x leverage, generating 50× your capital in monthly trading
volume per venue (a moderate, not aggressive, farming pace):

**Monthly cost: 97.68 EUR (9.77% of capital).**
**3-month farming campaign total cost: 307.04 EUR (30.7% of capital) — this is the breakeven
airdrop value: you need at least 307 EUR of real, realized, post-haircut, actually-received
airdrop value just to break even against doing nothing.**

At a cheaper fee pair (Variational + Extended, ~1.25bps taker/leg), the same setup costs 70.18
EUR/month (7.02% of capital) — fees and slippage are real but not the dominant cost at moderate
volume; a flat, assumption-based rebalancing cost (24 EUR/month) and foregone stablecoin yield
(2.67 EUR/month, sourced) matter more than people usually expect at this capital size.

## The payoff side is unknowable — stated plainly
Allocation %, FDV, TGE date, Sybil rules, and post-TGE price are unknown for essentially every
venue in Task 1. Of 10 venues researched from primary sources, **only Variational (Omni)** has a
currently-live, pre-TGE points program with a stated allocation percentage (~50% of $VAR to
community distribution, not points-only) confirmed directly from its own documentation. Every other
venue is either already concluded (Hyperliquid, Avantis), running with an explicitly unannounced
allocation (Extended, Paradex Season 3, StandX, Pacifica), or has data quality too weak to trust
(Nado, Reya — direct primary-source fetches were blocked or contradictory). **The cost side of this
report is precise to the assumptions stated. The payoff side is not a forecast anywhere in this
document — treat every airdrop-value number below as a dial you turn, not a number we predict.**

---

## Task 1 — Venue fact sheet

Full machine-readable table: `venues.csv` (10 venues, primary-sources-only discipline; every fact
tagged `primary`, `blog-only` (excluded from calculations), or `insufficient data`).

**Concluded programs (zero forward farming value — excluded from the cost-model venue pairing)**:
- **Hyperliquid**: original HYPE airdrop TGE'd 2024-11-29 (31% of supply, already distributed). No
  confirmed new points campaign since.
- **Avantis**: TGE'd 2025-09-15; Season 3 XP program (4% of supply, confirmed primary) ran through
  ~2026-02-28, already past as of today (2026-07-18).
- **Paradex**: the historical Season 1-2 program (25% of $DIME supply) already TGE'd and claimed
  (~2026-03-19). A new Season 3 is live but has no announced allocation — treated as unmonetized,
  not "concluded," but zero confirmed forward value either.

**Live, farmable-in-principle programs** (used for the cost-model fee scenarios): Variational
(highest confidence — primary-sourced on every field), Extended (primary-sourced, but explicitly
undecided allocation terms per its own docs), Pacifica, StandX, GRVT (fee schedule is stale —
expired 2026-03-23, current rate unconfirmed), Nado (weakest verification — docs domain blocked
direct fetch throughout, relied on search-cached snippets).

**Status unknown, excluded from modeling**: Reya — contradictory signals (site still shows an "ICO
live" banner; TGE and points-program status could not be confirmed either way from primary sources).

## Task 2 — Live funding differential (confirms Run 2's finding)

| Coin | Median disp./8h | P10 | P90 | % of periods clearing a 20bps round-trip cost |
|---|---|---|---|---|
| BTC | +0.0026% | -0.0061% | +0.0096% | **0.0%** |
| ETH | +0.0030% | -0.0065% | +0.0100% | **0.0%** |
| SOL | +0.0013% | -0.0092% | +0.0107% | **0.0%** |

**Funding roughly washes out, as expected.** It is modeled as a small, near-symmetric noise term on
held notional in the cost grid below — not a subsidy, not a reliable drag. Full detail:
`results/farm_funding_differential_summary.md`.

## Task 3 — Cost model and grid

Cost components modeled (`src/farm_cost.py`): trading fees (both legs, both venues), slippage
(3bps/leg, stated ASSUMPTION — no live orderbook depth was pulled for 10 venues), funding
differential (Task 2's measured median), rebalancing (weekly, 3 EUR/transfer ASSUMPTION — most
venues had no published bridge-fee figure), bridging + gas, EUR↔USDC FX spread (10bps each way,
ASSUMPTION), and opportunity cost (**3.21% APY, SOURCED**: Aave V3 USDC on Ethereum, DefiLlama
yields API, fetched 2026-07-18, ~$199.7M TVL pool).

Full grid (90 rows: 2 fee scenarios × 3 capital levels × 3 leverage levels × 5 volume multiples):
`results/farm_cost_grid.csv`. Selected rows, 1,000 EUR capital, typical fees:

| Leverage | Vol. multiple | Fee cost | Slippage | Funding | Rebalance | Opp. cost | **Total/month** | **% of capital** |
|---|---|---|---|---|---|---|---|---|
| 1x | 10x | 8.00 | 6.00 | 1.01 | 24.00 | 2.67 | **41.68** | **4.17%** |
| 1x | 50x | 40.00 | 30.00 | 1.01 | 24.00 | 2.67 | **97.68** | **9.77%** |
| 1x | 100x | 80.00 | 60.00 | 1.01 | 24.00 | 2.67 | **167.68** | **16.77%** |
| 1x | 250x | 200.00 | 150.00 | 1.01 | 24.00 | 2.67 | **377.68** | **37.77%** |
| 3x | 50x | 40.00 | 30.00 | 3.02 | 24.00 | 2.67 | **99.70** | **9.97%** |

**Leverage barely changes the monthly EUR cost** in this model — fees and slippage scale with
traded volume, not leverage; leverage mainly changes held notional (a small funding-cost effect,
+/-2 EUR/month here) and, far more importantly, **liquidation risk** (Task 4). Do not read "3x
costs almost the same as 1x" as "3x is free" — it isn't; the real 3x cost is the liquidation
probability below, not an extra fee line.

**Fixed costs disproportionately hurt smaller capital.** At 50x volume multiple, 1x leverage,
typical fees: 500 EUR capital pays 12.17%/month, 1,000 EUR pays 9.77%/month, 2,000 EUR pays
8.57%/month — the flat 24 EUR/month rebalancing assumption and one-time bridging costs don't scale
down, so smaller accounts are structurally worse off per euro farmed.

## Task 4 — Liquidation & buffer analysis

Empirical, from 400 days of real hourly BTC/ETH price data (not a distributional assumption).
Liquidation modeled as triggering when an adverse move consumes 50% of initial margin (a stated,
moderate-conservative simplification — not a venue-specific maintenance-margin formula).

| Coin | 1x | 2x | 3x | Safe leverage for <1%/month |
|---|---|---|---|---|
| BTC | 0.0% | 12.7% | **31.9%** | 1.35x |
| ETH | 6.1% | 40.9% | **64.7%** | 0.81x |

At 3x nominal leverage, this window's realized volatility implies a **32% (BTC) to 65% (ETH)**
chance at least one leg gets liquidated within a month — stranding the other leg's gain on a
different venue while crystallizing a real loss. Keeping that probability under 1% requires capping
effective leverage at 1.35x (BTC) or below 1x (ETH) — i.e. holding idle margin buffer beyond the
minimum. For a BTC farmer targeting nominal 3x on 1,000 EUR: minimum margin at 3x is 333 EUR/leg;
the 1.35x-safe margin for the same notional is 741 EUR/leg — **~408 EUR (41% of total capital)
sitting idle** just to hold liquidation risk near 1%, none of it generating volume or points. Full
detail and the important caveat about this being a realized-not-forecast volatility window:
`results/farm_liquidation_summary.md`.

## Task 5 — Breakeven table (cost side, not a prediction)

Full table (360 rows): `results/farm_breakeven_table.csv`. Selected cells, 1,000 EUR capital,
typical fees, 1x leverage:

| Volume multiple | 1 month | 3 months | 6 months | 12 months |
|---|---|---|---|---|
| 10x | 55.68 | 139.04 | 264.08 | 514.16 |
| 50x | 111.68 | 307.04 | 600.08 | 1,186.16 |
| 100x | 181.68 | 517.04 | 1,020.08 | 2,026.16 |
| 250x | 391.68 | 1,147.04 | 2,280.08 | 4,546.16 |

Each cell = monthly recurring cost × duration + a one-time 14 EUR FX+bridge setup/exit cost
(charged once per campaign, not per month) — e.g. the 50x/1-month cell is 97.68×1 + 14.00 = 111.68.

**These EUR figures ARE the breakeven gross airdrop value** — the minimum real, received,
post-haircut value needed to match what 1,000 EUR would have earned sitting in Aave USDC instead.

### SPECULATIVE — inputs are assumptions, not forecasts
Full grid (108 rows, illustrative allocation levels × haircut × TGE-probability × Sybil-pass-
probability): `results/farm_speculative_scenario_grid.csv`. Costed against the 3-month, 50x-volume,
1,000-EUR base case (307.04 EUR cost). Only **12% of the 108 scenario combinations** produce a
positive expected net outcome — concentrated at the higher-allocation, lower-haircut,
higher-probability corners of the grid. Sample slice (allocation = 500 EUR at TGE price, -50%
haircut):

| TGE prob. | Sybil-pass prob. | P(receive) | Expected payoff | Cost | **Expected net** |
|---|---|---|---|---|---|
| 100% | 100% | 100.0% | 250.00 | 307.04 | **-57.04** |
| 100% | 80% | 80.0% | 200.00 | 307.04 | **-107.04** |
| 50% | 50% | 25.0% | 62.50 | 307.04 | **-244.54** |
| 25% | 50% | 12.5% | 31.25 | 307.04 | **-275.79** |

Change the four inputs (allocation, haircut, TGE probability, Sybil-pass probability) to your own
beliefs and re-run `python -m src.farm_cost` — do not anchor on the illustrative numbers above.

## Task 6 — Risk register
See `RISKS.md`. Headline risks not priced into any EUR figure above: Sybil disqualification (total
loss of points), unilateral program changes, smart-contract exploit, venue insolvency/withdrawal
freeze, and German tax treatment of airdrops (income at receipt — confirm with a tax advisor, this
is not tax advice).

---

## Bottom line
The cost side is precise to its stated assumptions: **~10% of capital per month** at a moderate
farming pace on the cheapest verified live venues, growing to **~38%/month** at an aggressive 250×
volume pace, plus a real, quantified liquidation risk that leverage makes materially worse (32-65%
monthly chance of a leg blowing up at 3x). The payoff side cannot be estimated responsibly with the
data available — 9 of 10 venues have no confirmed allocation percentage, and even the one that does
(Variational) has not had its TGE. **The honest headline, as instructed: the cost side is
computable and program terms are largely unverifiable — that itself is a reason for caution, not a
reason to avoid the question.** The decision is yours to make with your own risk appetite and your
own beliefs about the SPECULATIVE inputs above.
