# WRDS macro-regime feature inventory

All features are market-level and lagged by one calendar day after calculation before joining to the crypto weekly panel.

| Feature | Family | Source | Formula | Lag | Economic rationale |
|---|---|---|---|---|---|
| equity_momentum_21d | equity_risk | CRSP index | S&P/CRSP equity index 21d pct_change | 1 calendar day after feature calculation | Equity risk appetite often transmits into crypto beta. |
| equity_momentum_63d | equity_risk | CRSP index | S&P/CRSP equity index 63d pct_change | 1 calendar day after feature calculation | Medium-term equity trend as risk-on/risk-off proxy. |
| equity_drawdown_252d | equity_risk | CRSP index | Index / trailing 252d high - 1 | 1 calendar day after feature calculation | Equity drawdown captures broad risk stress. |
| equity_realized_vol_21d | equity_risk | CRSP index | 21d annualized equity realized volatility | 1 calendar day after feature calculation | Equity volatility is a risk-regime proxy. |
| vix_level | volatility_risk | CBOE | CBOE VIX close | 1 calendar day after feature calculation | High VIX indicates hostile global risk conditions. |
| vix_change_5d | volatility_risk | CBOE | VIX 5d difference | 1 calendar day after feature calculation | Rapid volatility increases can precede crypto de-risking. |
| vix_change_21d | volatility_risk | CBOE | VIX 21d difference | 1 calendar day after feature calculation | Medium-term volatility trend. |
| vix_percentile_252d | volatility_risk | CBOE | VIX percentile versus trailing 252d history | 1 calendar day after feature calculation | Normalizes volatility level across regimes. |
| nasdaq_vol_level | volatility_risk | CBOE | VXN close | 1 calendar day after feature calculation | Equity-index volatility proxy. |
| dow_vol_level | volatility_risk | CBOE | VXD close | 1 calendar day after feature calculation | Equity-index volatility proxy. |
| rates_10y_level | rates | FRB | 10y Treasury yield level | 1 calendar day after feature calculation | Higher rates can pressure speculative duration-like assets. |
| rates_10y_change_21d | rates | FRB | 10y Treasury yield 21d difference | 1 calendar day after feature calculation | Rates shocks can mark hostile macro regimes. |
| rates_10y_change_63d | rates | FRB | 10y Treasury yield 63d difference | 1 calendar day after feature calculation | Medium-term rates trend. |
| fed_funds_level | rates | FRB | Effective fed funds rate | 1 calendar day after feature calculation | Policy-rate regime proxy. |
| sofr_level | rates | FRB | SOFR level | 1 calendar day after feature calculation | Short-rate/liquidity proxy. |
| real_yield_10y_level | rates | FRB | 10y TIPS real yield | 1 calendar day after feature calculation | Real yields can reduce appetite for speculative assets. |
| real_yield_10y_change_21d | rates | FRB | 10y real yield 21d difference | 1 calendar day after feature calculation | Real-rate shock proxy. |
| yield_curve_slope_10y2y | rates | FRB | 10y yield - 2y yield or FRB T10Y2Y | 1 calendar day after feature calculation | Curve slope captures growth/liquidity regime. |
| yield_curve_slope_change_21d | rates | FRB | 10y-2y slope 21d difference | 1 calendar day after feature calculation | Curve-steepening/flattening shock. |
| yield_curve_slope_10y3m | rates | FRB | 10y-3m slope | 1 calendar day after feature calculation | Alternative recession/risk-state proxy. |
| credit_spread_level | credit | FRB/FRED | High-yield spread level | 1 calendar day after feature calculation | Credit stress proxy. |
| credit_spread_change_21d | credit | FRB/FRED | High-yield spread 21d difference | 1 calendar day after feature calculation | Credit stress acceleration. |
| usd_trend_21d | usd | FRB FX | Trade-weighted USD 21d pct_change | 1 calendar day after feature calculation | USD strength can be hostile to crypto liquidity. |
| usd_trend_63d | usd | FRB FX | Trade-weighted USD 63d pct_change | 1 calendar day after feature calculation | Medium-term dollar trend. |
| usd_change_5d | usd | FRB FX | Trade-weighted USD 5d pct_change | 1 calendar day after feature calculation | Short USD shock proxy. |
| macro_risk_on_composite | macro_composite | WRDS macro blend | Equal-weighted trailing z-scores of equity trend, drawdown, VIX, rates, USD, curve, and credit risk | 1 calendar day after feature calculation | Single predeclared risk-on/risk-off macro summary. |
