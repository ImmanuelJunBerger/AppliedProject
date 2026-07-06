# Feature engineering

Only lagged features from actually available small public datasets were
implemented. Requested but unavailable ETF-flow, exchange-flow, MVRV,
realized-cap, holder-behaviour, and options-surface features are recorded but
not used.

## Implemented features

| Feature | Family | Formula | Source | Lag | Rationale |
|---|---|---|---|---|---|
| btc_active_address_growth_30d | on-chain | pct_change(active addresses, 30d), lagged 1 day | Blockchain.com charts API | 1 day | Rising BTC address activity can proxy broader network participation and attention before upside expansion. |
| btc_active_address_growth_7d | on-chain | pct_change(active addresses, 7d), lagged 1 day | Blockchain.com charts API | 1 day | Rising BTC address activity can proxy broader network participation and attention before upside expansion. |
| btc_transaction_growth_30d | on-chain | pct_change(transaction count, 30d), lagged 1 day | Blockchain.com charts API | 1 day | Rising BTC transaction count can proxy chain usage and settlement demand before upside expansion. |
| btc_transaction_growth_7d | on-chain | pct_change(transaction count, 7d), lagged 1 day | Blockchain.com charts API | 1 day | Rising BTC transaction count can proxy chain usage and settlement demand before upside expansion. |

## Full requested feature inventory

| Feature | Family | Availability | Formula | Source |
|---|---|---|---|---|
| btc_active_address_growth_30d | on-chain | implemented | pct_change(active addresses, 30d), lagged 1 day | Blockchain.com charts API |
| btc_active_address_growth_7d | on-chain | implemented | pct_change(active addresses, 7d), lagged 1 day | Blockchain.com charts API |
| btc_transaction_growth_30d | on-chain | implemented | pct_change(transaction count, 30d), lagged 1 day | Blockchain.com charts API |
| btc_transaction_growth_7d | on-chain | implemented | pct_change(transaction count, 7d), lagged 1 day | Blockchain.com charts API |
| etf_net_flow | ETF flows | unavailable | daily BTC/ETH ETF net flow | Farside/WRDS ETF-flow source unavailable or not point-in-time audited |
| etf_flow_as_pct_aum | ETF flows | unavailable | net flow divided by AUM | ETF AUM/flow source unavailable |
| etf_5d_flow | ETF flows | unavailable | 5-day net ETF flow | ETF-flow source unavailable |
| etf_21d_flow | ETF flows | unavailable | 21-day net ETF flow | ETF-flow source unavailable |
| etf_flow_acceleration | ETF flows | unavailable | 5-day flow minus prior 5-day flow | ETF-flow source unavailable |
| etf_flow_percentile | ETF flows | unavailable | rolling percentile of ETF flow | ETF-flow source unavailable |
| etf_inflow_streak | ETF flows | unavailable | consecutive days of positive flow | ETF-flow source unavailable |
| etf_outflow_shock | ETF flows | unavailable | large negative flow shock | ETF-flow source unavailable |
| exchange_flow_pressure | on-chain | unavailable | exchange inflow minus outflow pressure | entity-labeled exchange-flow data unavailable |
| mvrv_percentile | on-chain | unavailable | MVRV rolling percentile | MVRV/realized-cap source unavailable |
| realized_cap_growth | on-chain | unavailable | realized cap growth | realized-cap source unavailable |
| holder_accumulation_proxy | on-chain | unavailable | holder accumulation proxy | holder cohort/source unavailable |
| option_iv_level | options-implied | unavailable | constant-maturity IV level | full options surface history unavailable |
| option_iv_change | options-implied | unavailable | change in IV | full options surface history unavailable |
| option_skew_level | options-implied | unavailable | put/call skew level | full options surface history unavailable |
| option_skew_change | options-implied | unavailable | change in skew | full options surface history unavailable |
| option_put_call_change | options-implied | unavailable | put/call ratio change | put/call history unavailable |
| option_term_structure_slope | options-implied | unavailable | long IV minus short IV | full term structure unavailable |
| option_risk_reversal_proxy | options-implied | unavailable | call IV minus put IV | risk reversal history unavailable |
