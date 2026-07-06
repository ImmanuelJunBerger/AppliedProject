# WRDS macro feature data coverage

Scope: targeted small daily WRDS series only. No large tables, trading strategy, or model fitting was run.

- Raw macro rows: 2568
- Raw macro date range: 2019-01-01 to 2026-05-29
- Lagged macro feature rows: 2730
- Lagged macro feature date range with data: 2019-01-02 to 2026-06-22
- Joined weekly crypto rows: 7247
- Joined weekly crypto date range: 2019-07-05 to 2026-06-19
- Locked holdout reference: 2025-01-01 to 2026-06-22

## Downloaded sources

| Source | Library | Table | Start | End | Rows | Columns |
|---|---|---|---|---|---|---|
| crsp_sp500_index | crsp_q_indexes | dsp500_v2 | 2019-01-02 | 2026-03-31 | 1821 | sp500_return, sp500_index, sp500_value_weighted_return, sp500_equal_weighted_return, sp500_total_value, sp500_member_count |
| crsp_broad_market_index | crsp | dsi | 2019-01-02 | 2024-12-31 | 1510 | crsp_market_value_weighted_return, crsp_market_equal_weighted_return, crsp_sp500_return_legacy, crsp_sp500_index_legacy, crsp_total_market_value, crsp_total_count |
| cboe_volatility_indices | cboe | cboe | 2019-01-02 | 2026-05-29 | 1895 | vix, vix_open, vix_high, vix_low, vxo, vxn, vxd |
| frb_rates_daily | frb | rates_daily | 2019-01-01 | 2025-02-13 | 2236 | treasury_10y, treasury_2y, treasury_3m, fed_funds_effective, sofr, tips_10y_real_yield, yield_curve_10y2y, yield_curve_10y3m, breakeven_10y, high_yield_spread, high_yield_effective_yield, corp_bond_effective_yield |
| frb_fx_daily | frb | fx_daily | 2019-01-01 | 2025-02-07 | 1594 | trade_weighted_usd_broad, trade_weighted_usd_advanced_foreign, trade_weighted_usd_emerging_market, usd_per_eur, jpy_per_usd, usd_per_gbp |

## Sources not used or unavailable

_No rows._

## Explicit limitations

- CBOE VVIX was searched in accessible CBOE metadata but was not available in the compact CBOE index table.
- Commodity proxies were not downloaded because no small confirmed gold/oil/copper table or Datastream identifier was available.
- Datastream/LSEG equivalents were not downloaded because identifiers/tables were not easy to confirm from the accessible metadata.
- Several FRB daily rates/FX fields stop before the full 2026 crypto holdout; feature-research reports expose resulting missing coverage.
