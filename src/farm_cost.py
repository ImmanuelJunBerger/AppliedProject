"""Cost model for delta-neutral perp-DEX points farming.

NOT a backtest, NOT a strategy search. Prices a known cost (fees, slippage,
funding, rebalancing, bridging, FX, foregone yield) against a target trading
volume, for a two-venue delta-neutral setup (long notional on venue A, equal
short notional on venue B). Every constant below is either SOURCED (with a
citation) or an explicitly labeled ASSUMPTION -- never silently invented.

Reuses fee/slippage primitives from src/engine.py where applicable; this
module adds farming-specific components (funding differential, rebalancing,
bridging, FX, opportunity cost) that engine.py has no notion of.
"""
from __future__ import annotations

import pandas as pd

CAPITAL_CASES_EUR = [500.0, 1000.0, 2000.0]
LEVERAGE_CASES = [1, 2, 3]
VOLUME_MULTIPLES = [10, 25, 50, 100, 250]  # monthly traded notional / capital, per venue

# --- fee scenarios: drawn directly from venues.csv (Task 1), live-program venues only ---
# "cheap": Variational (0bps taker) + Extended (2.5bps taker), both live pre-allocation-unknown programs
# "typical": Pacifica (4bps taker) + StandX (4bps taker), both live
FEE_SCENARIOS_TAKER_BPS = {"cheap_pair (Variational+Extended)": (0.0 + 2.5) / 2,
                            "typical_pair (Pacifica+StandX)": (4.0 + 4.0) / 2}

# --- ASSUMPTIONS (no primary source found; stated plainly, used consistently) ---
SLIPPAGE_BPS_ASSUMPTION = 3.0          # ASSUMPTION: typical clip-size slippage on majors, moderate-depth venues
AVG_HOLD_FRACTION_OF_MONTH = 0.8       # ASSUMPTION: fraction of the month a leg sits open on average
REBALANCE_EVENTS_PER_MONTH = 4         # ASSUMPTION: weekly rebalance of drifted margin
BRIDGE_TRANSFER_COST_EUR = 3.0         # ASSUMPTION: most venues had "insufficient data" for a fixed bridge fee (venues.csv); placeholder based on typical L2 gas + relayer fee
FX_SPREAD_BPS_EACH_WAY = 10.0          # ASSUMPTION: EUR<->USDC conversion spread, one way

# --- SOURCED ---
# Aave V3 USDC (Ethereum), base supply APY, largest-TVL USDC pool (~$200M TVL),
# fetched from DefiLlama's yields API (https://yields.llama.fi/pools) on 2026-07-18.
STABLECOIN_YIELD_APY = 0.0321
STABLECOIN_YIELD_SOURCE = "DefiLlama yields.llama.fi/pools, Aave V3 USDC Ethereum, fetched 2026-07-18, apyBase=3.21%, tvlUsd~$199.7M"

# --- funding differential, from Task 2 (results/farm_funding_differential_summary.md) ---
# median dispersion per 8h period, BTC/ETH average, roughly symmetric/near-zero
FUNDING_DIFF_MEDIAN_8H = 0.000028   # ~0.0028% / 8h, average of BTC (0.0026%) and ETH (0.0030%)
FUNDING_DIFF_P10_8H = -0.000063
FUNDING_DIFF_P90_8H = 0.000098
FUNDING_PERIODS_PER_MONTH = 90       # 3/day * 30 days

# --- liquidation-driven safe leverage, from Task 4 (results/farm_liquidation_summary.md) ---
# BTC used as the primary reference (less extreme than ETH in the measured window);
# leverage above this cannot be run at <1% monthly liquidation probability without
# an idle margin buffer eating into working capital.
SAFE_LEVERAGE_BTC = 1.35
SAFE_LEVERAGE_ETH = 0.81  # shown separately as a sensitivity note, not the main grid


def monthly_recurring_cost(capital_eur: float, leverage: int, volume_multiple: float,
                            taker_fee_bps: float, funding_diff_8h: float = FUNDING_DIFF_MEDIAN_8H) -> dict:
    """All monthly-recurring cost components for one (capital, leverage, volume, fee) cell.
    Volume multiple is defined as monthly traded notional PER VENUE / capital; both venues
    trade in lockstep to stay delta-neutral, so fee/slippage apply to 2x that notional."""
    monthly_volume_per_venue = capital_eur * volume_multiple
    two_venue_turnover = 2 * monthly_volume_per_venue

    fee_cost = two_venue_turnover * taker_fee_bps / 10_000
    slippage_cost = two_venue_turnover * SLIPPAGE_BPS_ASSUMPTION / 10_000

    margin_per_leg = capital_eur / 2
    held_notional_per_leg = margin_per_leg * leverage * AVG_HOLD_FRACTION_OF_MONTH
    funding_cost = held_notional_per_leg * funding_diff_8h * FUNDING_PERIODS_PER_MONTH

    rebalance_cost = REBALANCE_EVENTS_PER_MONTH * 2 * BRIDGE_TRANSFER_COST_EUR
    opportunity_cost = capital_eur * STABLECOIN_YIELD_APY / 12

    total = fee_cost + slippage_cost + funding_cost + rebalance_cost + opportunity_cost
    return {
        "capital_eur": capital_eur, "leverage": leverage, "volume_multiple": volume_multiple,
        "taker_fee_bps": round(taker_fee_bps, 3),
        "fee_cost_eur": round(fee_cost, 2), "slippage_cost_eur": round(slippage_cost, 2),
        "funding_cost_eur": round(funding_cost, 2), "rebalance_cost_eur": round(rebalance_cost, 2),
        "opportunity_cost_eur": round(opportunity_cost, 2),
        "total_monthly_cost_eur": round(total, 2),
        "total_monthly_cost_pct_of_capital": round(100 * total / capital_eur, 2),
    }


def one_time_setup_exit_cost(capital_eur: float) -> dict:
    """FX in/out + entry/exit bridging to both venues. Occurs once per farming
    campaign, not monthly -- added separately in the breakeven calc."""
    fx_cost = 2 * FX_SPREAD_BPS_EACH_WAY / 10_000 * capital_eur  # in once, out once
    bridge_cost = 4 * BRIDGE_TRANSFER_COST_EUR  # 2 venues in + 2 venues out
    total = fx_cost + bridge_cost
    return {"capital_eur": capital_eur, "fx_cost_eur": round(fx_cost, 2),
            "bridge_cost_eur": round(bridge_cost, 2), "one_time_total_eur": round(total, 2)}


def build_cost_grid() -> pd.DataFrame:
    rows = []
    for fee_label, taker_bps in FEE_SCENARIOS_TAKER_BPS.items():
        for capital in CAPITAL_CASES_EUR:
            for leverage in LEVERAGE_CASES:
                for vol_mult in VOLUME_MULTIPLES:
                    row = monthly_recurring_cost(capital, leverage, vol_mult, taker_bps)
                    row["fee_scenario"] = fee_label
                    # liquidation flag: does this leverage exceed the <1%-risk safe level?
                    row["exceeds_safe_leverage_BTC"] = leverage > SAFE_LEVERAGE_BTC
                    rows.append(row)
    df = pd.DataFrame(rows)
    cols = ["fee_scenario", "capital_eur", "leverage", "volume_multiple", "taker_fee_bps",
            "fee_cost_eur", "slippage_cost_eur", "funding_cost_eur", "rebalance_cost_eur",
            "opportunity_cost_eur", "total_monthly_cost_eur", "total_monthly_cost_pct_of_capital",
            "exceeds_safe_leverage_BTC"]
    return df[cols]


def build_breakeven_table(durations_months=(1, 3, 6, 12)) -> pd.DataFrame:
    rows = []
    for fee_label, taker_bps in FEE_SCENARIOS_TAKER_BPS.items():
        for capital in CAPITAL_CASES_EUR:
            for leverage in LEVERAGE_CASES:
                for vol_mult in VOLUME_MULTIPLES:
                    monthly = monthly_recurring_cost(capital, leverage, vol_mult, taker_bps)
                    setup = one_time_setup_exit_cost(capital)
                    for months in durations_months:
                        total_cost = monthly["total_monthly_cost_eur"] * months + setup["one_time_total_eur"]
                        rows.append({
                            "fee_scenario": fee_label, "capital_eur": capital, "leverage": leverage,
                            "volume_multiple": vol_mult, "duration_months": months,
                            "total_cost_eur": round(total_cost, 2),
                            "breakeven_airdrop_eur": round(total_cost, 2),
                            "breakeven_as_multiple_of_capital": round(total_cost / capital, 3),
                        })
    return pd.DataFrame(rows)



# ---------------------------------------------------------------------------
# SPECULATIVE scenario grid (Task 5, second half). Every input here is a
# user-adjustable assumption, NOT a forecast. Do not read any single number
# in this section as "the expected airdrop." See FARMING_COST.md's own
# SPECULATIVE banner for the required framing.
# ---------------------------------------------------------------------------

SCENARIO_ALLOCATION_EUR = [50, 150, 500, 1500]     # illustrative gross airdrop value AT TGE PRICE, before haircut
SCENARIO_HAIRCUT_PCT = [0, -50, -80]               # post-TGE price decline applied to the allocation value
SCENARIO_TGE_PROB_PCT = [100, 50, 25]              # probability the token generation event happens at all
SCENARIO_SYBIL_PASS_PROB_PCT = [100, 80, 50]       # probability of passing anti-Sybil filters and receiving the allocation


def build_speculative_scenario_grid(total_cost_eur: float) -> pd.DataFrame:
    """Every row is (allocation, haircut, TGE-prob, Sybil-prob) -> expected net
    outcome vs. `total_cost_eur` (a specific cost-side number the caller
    supplies from the cost/breakeven tables above). Purely mechanical
    arithmetic on user-supplied assumptions -- not a prediction."""
    rows = []
    for alloc in SCENARIO_ALLOCATION_EUR:
        for haircut in SCENARIO_HAIRCUT_PCT:
            realized_alloc = alloc * (1 + haircut / 100)
            for tge_p in SCENARIO_TGE_PROB_PCT:
                for sybil_p in SCENARIO_SYBIL_PASS_PROB_PCT:
                    p_receive = (tge_p / 100) * (sybil_p / 100)
                    expected_payoff = realized_alloc * p_receive
                    expected_net = expected_payoff - total_cost_eur
                    rows.append({
                        "allocation_at_tge_eur": alloc, "haircut_pct": haircut,
                        "realized_allocation_eur": round(realized_alloc, 2),
                        "tge_probability_pct": tge_p, "sybil_pass_probability_pct": sybil_p,
                        "probability_receive_pct": round(100 * p_receive, 1),
                        "expected_payoff_eur": round(expected_payoff, 2),
                        "cost_eur": round(total_cost_eur, 2),
                        "expected_net_eur": round(expected_net, 2),
                    })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import os
    os.makedirs("results", exist_ok=True)
    grid = build_cost_grid()
    grid.to_csv("results/farm_cost_grid.csv", index=False)
    breakeven = build_breakeven_table()
    breakeven.to_csv("results/farm_breakeven_table.csv", index=False)
    print("cost grid rows:", len(grid))
    print("breakeven rows:", len(breakeven))

    # base case for the speculative grid: 1000 EUR, typical fees, 1x leverage,
    # 50x monthly volume multiple, 3-month duration
    base_row = breakeven[(breakeven.capital_eur == 1000) & (breakeven.leverage == 1) &
                          (breakeven.volume_multiple == 50) & (breakeven.duration_months == 3) &
                          (breakeven.fee_scenario.str.startswith("typical"))].iloc[0]
    base_cost = float(base_row["total_cost_eur"])
    print("base case 3-month total cost (EUR):", base_cost)
    spec = build_speculative_scenario_grid(base_cost)
    spec.to_csv("results/farm_speculative_scenario_grid.csv", index=False)
    print("speculative scenario rows:", len(spec))
    print(grid[(grid.capital_eur == 1000) & (grid.fee_scenario.str.startswith("typical"))].to_string())
