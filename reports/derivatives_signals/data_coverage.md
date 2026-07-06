# Derivatives data coverage

## Available data

| Dataset | Symbol | Start | End | N | Usable | Limitation |
|---|---|---|---|---|---|---|
| open_interest | BTC | 2026-05-23 | 2026-06-22 | 31 | No | Binance public market-data endpoint retains only recent history; excluded from 2019-2026 validation. |
| long_short | BTC | 2026-05-23 | 2026-06-22 | 31 | No | Binance public market-data endpoint retains only recent history; excluded from 2019-2026 validation. |
| taker | BTC | 2026-05-22 | 2026-06-21 | 31 | No | Binance public market-data endpoint retains only recent history; excluded from 2019-2026 validation. |
| funding | BTC | 2019-09-10 | 2026-06-22 | 2478 | Yes | Contract listing-dependent; realized funding aggregated to UTC day. |
| premium_index_basis | BTC | 2019-12-24 | 2026-06-22 | 2373 | Yes | Premium-index kline, not a tradeable futures cash-and-carry return. |
| open_interest | ETH | 2026-05-23 | 2026-06-22 | 31 | No | Binance public market-data endpoint retains only recent history; excluded from 2019-2026 validation. |
| long_short | ETH | 2026-05-23 | 2026-06-22 | 31 | No | Binance public market-data endpoint retains only recent history; excluded from 2019-2026 validation. |
| taker | ETH | 2026-05-22 | 2026-06-21 | 31 | No | Binance public market-data endpoint retains only recent history; excluded from 2019-2026 validation. |
| funding | ETH | 2019-11-27 | 2026-06-22 | 2400 | Yes | Contract listing-dependent; realized funding aggregated to UTC day. |
| premium_index_basis | ETH | 2019-12-24 | 2026-06-22 | 2373 | Yes | Premium-index kline, not a tradeable futures cash-and-carry return. |

Long-history realized funding and Binance premium-index klines are the only derivatives fields with enough development and evaluation coverage. The premium index is a basis proxy, not a directly executable cash-and-carry return.

## Unavailable for the locked study

- Open interest, global long/short ratio and taker buy/sell history were downloaded from public endpoints but retained only for recent dates. They are saved and audited, but excluded from model and strategy selection.
- Public/free liquidation history with consistent 2019–2026 coverage was unavailable. No synthetic liquidation series was substituted.
- No historical order-book imbalance or multi-venue derivatives aggregation was available.

The current 2025–2026 period has been examined in prior projects. It is reused here because requested, but cannot be described as untouched for a hypothesis designed in June 2026.
