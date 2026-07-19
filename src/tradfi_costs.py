"""Cost model for traditional-markets strategies (Run 5).

Crypto's engine.py constants (5bps perp, 10bps spot) do NOT apply here --
futures trade in fixed tick/commission terms, not bps of notional, and
spreads vary enormously by contract liquidity. Every number below is a
stated, moderate-conservative ASSUMPTION based on general knowledge of
typical retail futures-broker commission schedules and typical quoted
spreads for these contracts (not a live orderbook pull) -- flagged plainly,
not presented as a verified fee schedule the way Run 3's venues.csv facts
were sourced from primary docs. Where a number matters a lot to a
conclusion, that is called out in the strategy write-up, not buried here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FuturesContract:
    symbol: str
    tick_size: float
    tick_value_micro: float      # USD value of 1 tick, MICRO contract size
    tick_value_full: float       # USD value of 1 tick, FULL-size contract
    spread_ticks: float          # ASSUMPTION: typical quoted spread, in ticks
    commission_rt_micro: float   # ASSUMPTION: round-turn commission, micro, USD
    commission_rt_full: float    # ASSUMPTION: round-turn commission, full-size, USD
    init_margin_micro_usd: float # ASSUMPTION: approx initial margin, micro contract
    init_margin_full_usd: float  # ASSUMPTION: approx initial margin, full-size contract
    notional_per_point_micro: float  # USD notional change per 1.0 index/price point, micro
    notional_per_point_full: float


# Representative liquid + one deliberately obscure market, matching S1's universe.
# Margins/commissions are ballpark retail-broker figures (2026), not live quotes.
FUTURES_CONTRACTS = {
    "ES": FuturesContract("ES", 0.25, 1.25, 12.50, 1.0, 0.85, 2.25, 2000, 20000, 5.0, 50.0),
    "MNQ": FuturesContract("MNQ", 0.25, 0.50, 5.00, 1.0, 0.85, 2.25, 2200, 22000, 2.0, 20.0),
    "ZN": FuturesContract("ZN", 1 / 64, 7.8125, 15.625, 1.0, 0.85, 2.40, 600, 1500, 15.625 * 64, 15.625 * 64),
    "6E": FuturesContract("6E", 0.00005, 0.625, 6.25, 1.0, 0.85, 2.25, 900, 2500, 12500, 125000),
    "GC": FuturesContract("GC", 0.10, 1.00, 10.00, 1.5, 0.85, 2.25, 1200, 11000, 10, 100),
    "CL": FuturesContract("CL", 0.01, 1.00, 10.00, 1.0, 0.85, 2.25, 1300, 6500, 100, 1000),
    "HE": FuturesContract("HE", 0.00025, 10.00, 10.00, 3.0, 0.85, 2.25, 900, 900, 40000, 40000),
}

# --- equities / ETFs: commission (modern zero-commission retail broker), spread + impact in bps ---
EQUITY_COMMISSION_USD = 0.0        # ASSUMPTION: typical modern retail broker, zero explicit commission
EQUITY_SPREAD_BPS_LIQUID = 1.0     # ASSUMPTION: SPY/major-index ETF, very liquid
EQUITY_SPREAD_BPS_ILLIQUID = 8.0   # ASSUMPTION: thinner ETF/product
EQUITY_IMPACT_BPS_PER_10PCT_ADV = 2.0  # ASSUMPTION: crude linear impact scaling, retail size is never close to binding


def futures_round_trip_cost_usd(symbol: str, use_micro: bool = True) -> float:
    c = FUTURES_CONTRACTS[symbol]
    tick_value = c.tick_value_micro if use_micro else c.tick_value_full
    commission = c.commission_rt_micro if use_micro else c.commission_rt_full
    spread_cost = c.spread_ticks * tick_value  # one-way half-spread paid on entry, again on exit -> full spread per round trip
    return commission + spread_cost


def futures_margin_usd(symbol: str, use_micro: bool = True) -> float:
    c = FUTURES_CONTRACTS[symbol]
    return c.init_margin_micro_usd if use_micro else c.init_margin_full_usd


def futures_notional_per_point(symbol: str, use_micro: bool = True) -> float:
    c = FUTURES_CONTRACTS[symbol]
    return c.notional_per_point_micro if use_micro else c.notional_per_point_full


def equity_round_trip_cost_bps(liquid: bool = True) -> float:
    spread = EQUITY_SPREAD_BPS_LIQUID if liquid else EQUITY_SPREAD_BPS_ILLIQUID
    return spread  # round-trip = full bid/ask spread crossed once each way, expressed as bps of notional


def annualized_turnover(n_round_trips_per_year: float, avg_holding_days: float | None = None) -> dict:
    return {"round_trips_per_year": n_round_trips_per_year,
            "avg_holding_days": avg_holding_days,
            "implied_holding_period_note": "high round-trip count => high turnover => must clear a higher net-of-cost bar"}
