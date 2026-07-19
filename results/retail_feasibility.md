# Retail feasibility check

Portfolio: S2 (overnight IXIC/Nasdaq) + S4 (turn-of-month SPX), simple-risk-parity target weights
66% S4 / 34% S2 (the 2-strategy version — see RESULTS_V5.md for why S8 is excluded here). Current
prices used: SPX 7,458, Nasdaq-100 28,593 (S2's backtest used IXIC/Nasdaq Composite; MNQ futures
and Nasdaq-100 UCITS ETFs track the Nasdaq-**100**, a close but not identical proxy — a real
tracking-difference caveat, not modeled further here).

## Vehicle 1: micro futures (MES, MNQ) — the granularity problem is severe and binding

1 MES contract = ~$37,288 notional (margin ~$2,000). 1 MNQ contract = ~$57,185 notional (margin
~$2,200). **Minimum to hold one contract of each leg: $4,200 margin, $94,474 notional.**

| Capital (EUR) | Best achievable position | Actual weight (target 66/34) | Total notional | Effective leverage |
|---|---|---|---|---|
| 3,000 | **Cannot hold 1 contract of each** within a prudent 50%-margin-buffer rule | n/a | n/a | n/a |
| 10,000 | 1 MES + 1 MNQ | 39% / 61% (badly off-target) | $94,474 | **9.45x** |
| 25,000 | 3 MES + 1 MNQ | 66% / 34% (on target) | $169,051 | 6.76x |
| 50,000 | 3 MES + 1 MNQ | 66% / 34% | $169,051 | 3.38x |
| 100,000 | 3 MES + 1 MNQ | 66% / 34% | $169,051 | 1.69x |
| 250,000 | 3 MES + 1 MNQ | 66% / 34% | $169,051 | 0.68x |

**This is the binding constraint, and it is severe.** The backtest assumes ~1x notional exposure
(unleveraged) during active windows, at an ~8-10% realized annual portfolio volatility. To hold
that SAME risk level with correctly-weighted micro futures requires roughly **$250,000-500,000** —
below that, a retail trader is forced to choose between an unusably small, badly-mismatched
position (10k EUR: 61% in the wrong leg) or accepting leverage 2-9x higher than what was backtested
(meaning realized volatility and drawdowns would be that many times worse than the numbers reported
in `RESULTS_V5.md`). **Micro futures are the wrong vehicle for this portfolio below roughly a
quarter-million EUR of capital.**

## Vehicle 2: UCITS ETFs — solves the granularity problem, is the realistic retail vehicle

A UCITS-domiciled S&P 500 ETF (e.g. tracking the same underlying as `^GSPC`) and a UCITS
Nasdaq-100 ETF allow buying an arbitrary EUR amount (fractional shares on most modern EU brokers),
so target weights are achievable almost exactly at every capital tier from 3,000 EUR up — the
granularity problem effectively disappears. **This is the realistic implementation vehicle for
this portfolio at retail scale**, not futures.

**EU access constraint, stated plainly (PRIIPs/KID)**: the backtest itself used `^GSPC`/`^IXIC`
cash-index data as a clean proxy. A real EU retail investor generally **cannot buy the corresponding
US-domiciled ETFs** (e.g. SPY, QQQ) under PRIIPs/KID rules. A UCITS-domiciled equivalent (widely
available for S&P 500 and Nasdaq-100 exposure) is the accessible substitute, with a small,
generally immaterial additional cost (UCITS ETF TER typically 0.07-0.30%/yr, not separately modeled
in the cost grids above) and minor index-methodology tracking difference. **S8 (vol risk premium /
PutWrite) has no comparable UCITS proxy that this research identified** — the closest instrument
(PUTW, a US-domiciled ETF) is itself PRIIPs-blocked for EU retail, and the alternative (manually
writing cash-secured puts) requires options-trading approval, active monthly management, and
carries assignment risk — not a passive buy-and-hold position. **This is an independent, converging
reason (on top of S8's weak marginal Sharpe contribution and high tail risk, both found earlier) to
exclude S8 from a realistic EU retail implementation of this portfolio.**

## Operational / time cost

S4 (turn-of-month) trades ~24 times/year (in near month-end, out a few sessions into the next
month) — a handful of minutes, twice a month, to place two trades. S2 (overnight) as modeled is a
**daily** round trip (buy at close, sell next open) — this is a materially higher realistic
maintenance burden (a trade every single trading day, ~252/year) than the other strategies in this
portfolio, and is worth weighing against its modest marginal Sharpe contribution (see ablation in
`RESULTS_V5.md`) even before considering broker cost/slippage assumptions holding up in practice at
that frequency. **Realistic verdict: S4 alone is a low-maintenance, easily-held retail position;
S2 as literally backtested (daily overnight round trips) is a meaningfully higher-effort, easier-to-
get-wrong-in-practice position than its Sharpe number alone conveys.**
