"""Strategy 1: funding-rate carry (delta-neutral).

Hypothesis: perp funding is persistently positive on majors/liquid alts
(retail long bias), so short-perp + long-spot collects funding while price
risk cancels out (delta neutral by construction).

Two venue setups, both real data, different tradeoffs:
  (A) OKX same-venue: short BTC/ETH/SOL/DOGE/XRP-USDT-SWAP + long spot same
      venue. No cross-venue basis risk. Only ~95 days of funding history
      available from OKX's free public endpoint (retention limit) -> short
      sample, flagged.
  (B) Hyperliquid perp + Binance spot proxy: short HL perp (BTC/ETH/SOL/XMR)
      + long spot on Binance. ~400 days of hourly funding, much more
      statistical power, but assumes the spot leg's price return equals the
      perp's (delta-neutral assumption) with NO explicit basis-risk model
      between the two venues -- flagged as an unmodeled risk.

Rule: enter when trailing 24h average funding > ENTRY_TH (annualized ~11%),
exit when it drops below EXIT_TH (hysteresis avoids fee-churn on noise).
Capital: 1,000 EUR notional matched on both legs (assumes sufficient margin
efficiency on the perp leg from cross-margining / leverage headroom).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data, engine

ENTRY_TH_8H = 0.01 / 100      # ~0.01%/8h -> ~11% annualized
EXIT_TH_8H = 0.002 / 100
ENTRY_TH_1H = ENTRY_TH_8H / 8
EXIT_TH_1H = EXIT_TH_8H / 8
NOTIONAL_LEG_EUR = engine.CAPITAL_EUR


def _avg_daily_quote_volume_eur(symbol: str) -> float | None:
    try:
        df = data.fetch_binance_spot_klines(symbol, "1d", 30)
        return float(df["quote_volume"].tail(30).mean())
    except Exception:
        return None


def _run_carry(funding: pd.Series, periods_per_year: int, k_lookback: int,
                entry_th: float, exit_th: float, symbol_for_cost: str,
                adv_eur: float | None, venue_perp: str = "perp",
                venue_spot: str = "spot") -> tuple[pd.Series, int, float]:
    """funding: Series indexed by timestamp, one funding payment per period."""
    funding = funding.sort_index()
    signal = funding.rolling(k_lookback).mean()
    position = pd.Series(0, index=funding.index)
    state = 0
    for i in range(len(funding)):
        s = signal.iloc[i]
        if pd.isna(s):
            position.iloc[i] = state
            continue
        if state == 0 and s > entry_th:
            state = 1
        elif state == 1 and s < exit_th:
            state = 0
        position.iloc[i] = state
    # position[t] decided using info available through t (funding up to t);
    # it is applied to the funding realized at t+1 (shift to avoid look-ahead).
    applied_position = position.shift(1).fillna(0)

    equity = [engine.CAPITAL_EUR]
    trades = 0
    turnover = 0.0
    idx = funding.index
    for i in range(1, len(funding)):
        pos_now = applied_position.iloc[i]
        pnl = 0.0
        if pos_now == 1:
            pnl = NOTIONAL_LEG_EUR * funding.iloc[i]  # short perp receives positive funding
        e = equity[-1] + pnl
        if applied_position.iloc[i] != applied_position.iloc[i - 1]:
            # entering or exiting: 2 legs, spot + perp
            entry_cost = engine.trade_cost_eur(symbol_for_cost, NOTIONAL_LEG_EUR, venue_perp, adv_eur)
            entry_cost += engine.trade_cost_eur(symbol_for_cost, NOTIONAL_LEG_EUR, venue_spot, adv_eur)
            e -= entry_cost
            trades += 1
            turnover += 2 * NOTIONAL_LEG_EUR
        equity.append(e)
    eq = pd.Series(equity, index=idx)
    return eq, trades, turnover


def run_okx_same_venue() -> dict:
    insts = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "DOGE-USDT-SWAP", "XRP-USDT-SWAP"]
    spot_symbol_map = {"BTC-USDT-SWAP": "BTCUSDT", "ETH-USDT-SWAP": "ETHUSDT",
                        "SOL-USDT-SWAP": "SOLUSDT", "DOGE-USDT-SWAP": "DOGEUSDT",
                        "XRP-USDT-SWAP": "XRPUSDT"}
    out = {}
    for inst in insts:
        f = data.fetch_okx_funding_history(inst)
        if f.empty or len(f) < 20:
            out[inst] = {"error": "insufficient funding history"}
            continue
        fs = f.set_index("timestamp")["fundingRate"]
        adv = _avg_daily_quote_volume_eur(spot_symbol_map[inst])
        eq, trades, turnover = _run_carry(fs, periods_per_year=365 * 3, k_lookback=3,
                                           entry_th=ENTRY_TH_8H, exit_th=EXIT_TH_8H,
                                           symbol_for_cost=spot_symbol_map[inst], adv_eur=adv)
        m = engine.compute_metrics(eq, periods_per_year=365 * 3, trade_count=trades, turnover_eur=turnover)
        m["n_funding_periods"] = len(fs)
        m["span_days"] = (fs.index.max() - fs.index.min()).days
        m["mean_funding_ann_pct"] = round(float(fs.mean()) * 3 * 365 * 100, 2)
        out[inst] = m
        eq.to_frame("equity_eur").to_csv(f"results/funding_carry_okx_{inst}_equity.csv")
    return out


def run_hl_binance_proxy(lookback_days: int = 400) -> dict:
    import time
    start_ms = int((time.time() - lookback_days * 86400) * 1000)
    coins = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "XMR": "XMRUSDT"}
    out = {}
    for coin, spot_symbol in coins.items():
        f = data.fetch_hl_funding_history(coin, start_ms)
        if f.empty or len(f) < 48:
            out[coin] = {"error": "insufficient funding history"}
            continue
        fs = f.set_index("timestamp")["fundingRate"]
        adv = _avg_daily_quote_volume_eur(spot_symbol)
        eq, trades, turnover = _run_carry(fs, periods_per_year=365 * 24, k_lookback=24,
                                           entry_th=ENTRY_TH_1H, exit_th=EXIT_TH_1H,
                                           symbol_for_cost=spot_symbol, adv_eur=adv)
        m = engine.compute_metrics(eq, periods_per_year=365 * 24, trade_count=trades, turnover_eur=turnover)
        m["n_funding_periods"] = len(fs)
        m["span_days"] = (fs.index.max() - fs.index.min()).days
        m["mean_funding_ann_pct"] = round(float(fs.mean()) * 24 * 365 * 100, 2)
        out[coin] = m
        # save equity curve
        eq.to_frame("equity_eur").to_csv(f"results/funding_carry_hl_{coin}_equity.csv")
    return out


if __name__ == "__main__":
    import json
    okx = run_okx_same_venue()
    hl = run_hl_binance_proxy()
    print("=== OKX same-venue (short sample, clean basis) ===")
    print(json.dumps(okx, indent=2, default=str))
    print("=== Hyperliquid perp + Binance spot proxy (long sample, basis-risk unmodeled) ===")
    print(json.dumps(hl, indent=2, default=str))
