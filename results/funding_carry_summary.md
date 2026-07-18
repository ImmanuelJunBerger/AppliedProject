# Strategy 1: Funding-rate carry — summary

**OKX same-venue (BTC/ETH/SOL/DOGE/XRP-USDT-SWAP, ~94 days, 8h funding, no cross-venue basis risk):**
Mean funding never cleared the round-trip cost threshold (~11%/yr) in this window
(realized annualized mean funding: BTC 2.1%, ETH 2.3%, SOL 0.7%, DOGE 4.3%, XRP 2.2%).
Strategy never entered a single trade on any instrument — 0 trades, flat 1000 EUR. This is a
genuine, non-fabricated null result for the current (mid-2026) market regime on OKX majors.

**Hyperliquid perp + Binance spot proxy (BTC/ETH/SOL/XMR, ~400 days BTC/ETH/SOL, ~183 days XMR,
hourly funding):** BTC net +1.9% (Sharpe 1.98, 13 trades), ETH net +0.6% (Sharpe 0.72, 12 trades),
SOL net -4.1% (Sharpe -1.92, 14 trades), XMR net +7.5% (Sharpe 6.22, 9 trades, mean funding 25%/yr).

**Caveats (non-negotiable, read before trusting any number above):**
1. Trade counts are 9-14 per instrument — **below the 30-trade noise floor**. None of these
   Sharpe ratios are statistically reliable; XMR's Sharpe 6.22 in particular is built on 9 trades
   and should not be treated as a real edge estimate.
2. The HL leg is NOT delta-neutral against real execution: the long leg is a *Binance spot price
   proxy*, not an actual position held on the same venue as the short HL perp. Basis risk between
   HL mark price and Binance spot price is **not modeled** — real P&L would include basis noise
   this backtest cannot see.
3. No walk-forward/OOS split was run for this strategy: trade counts are already too low to
   split further without becoming pure noise. Entry/exit thresholds were fixed a priori from
   round-trip cost coverage, not fit to this data, which limits (but does not eliminate)
   overfitting risk.
4. OKX sample is short (~94 days) because OKX's free funding-rate-history endpoint only retains
   about 3 months.

**Verdict:** No reliable edge demonstrated. OKX majors currently pay too little funding to clear
costs. HL BTC/ETH show a small positive net-of-cost edge but on too few trades to trust. XMR looks
attractive but is the least trustworthy of all (shortest sample, fewest trades, largest Sharpe —
classic overfitting-shaped result even though thresholds were not tuned on it).
