# Task 2: Live cross-venue funding differential (BTC/ETH/SOL, HL vs OKX)

Confirms Run 2's B2 finding with fresh data (94-day OKX retention window, matched against
Hyperliquid hourly funding aggregated into the same 8h windows).

| Coin | Periods (8h) | Span (days) | Median disp/8h | P10 | P90 | Median \|disp\| | P90 \|disp\| | P95 \|disp\| | % periods clearing a 20bps round-trip cost |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 285 | 94 | +0.0026% | -0.0061% | +0.0096% | 0.0045% | 0.0104% | 0.0130% | **0.0%** |
| ETH | 285 | 94 | +0.0030% | -0.0065% | +0.0100% | 0.0048% | 0.0115% | 0.0135% | **0.0%** |
| SOL | 285 | 94 | +0.0013% | -0.0092% | +0.0107% | 0.0057% | 0.0123% | 0.0142% | **0.0%** |

**Confirmed, not refuted: funding differential roughly washes out.** Median dispersion is tiny
(1-3bps per 8h period) and roughly symmetric around zero (positive and negative periods both
occur — this is not a one-directional subsidy). Even the 95th-percentile absolute dispersion tops
out at ~13-14bps, well short of a 20bps round-trip cost floor if you tried to trade the dispersion
as a standalone arb. **0% of periods would clear that bar.**

For the farming cost model (`src/farm_cost.py`), this justifies treating the funding differential
as a small, roughly-zero-mean, symmetric-noise term applied continuously to held notional — not a
source of subsidized cost, and not reliably a drag either. The model uses the realized median as a
point estimate and reports the P10/P90 range as a sensitivity band, exactly as observed here.

Annualized median dispersion (informational only, not a claim this compounds cleanly):
BTC +2.8%/yr, ETH +3.3%/yr, SOL +1.4%/yr — small relative to the fee/slippage costs computed in
Task 3.
