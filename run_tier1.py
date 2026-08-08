"""Tier-1 cheap screen (development partition ONLY, pessimistic costs).

Purpose is ELIMINATION, not measurement. Every hypothesis gets a ledger row written
BEFORE it runs. Advancement requires, on development data:
    * net edge > 0 at the PESSIMISTIC cost level
    * >= 300 trades
    * positive expectancy in >= 2 of 3 BTC regimes (bull / bear / chop)
"""
from __future__ import annotations

import json
import sys
import traceback
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import ledger, panel as P, partitions as PART
from src import signals_v7 as SG

OUT = Path("results_v7"); OUT.mkdir(exist_ok=True)
MIN_TRADES = 300
MIN_POS_REGIMES = 2

M = {  # short mechanism strings for the ledger
 "A": "leveraged traders pay funding/get liquidated; forced flow cannot wait",
 "B": "slow information diffusion / liquidity provision across fragmented retail market",
 "C": "insurance buyers overpay for vol; vol is autocorrelated so forecasts are reliable",
 "D": "participant mix changes by clock; scheduled payments are dodged predictably",
 "E": "inventory-driven dislocation between substitutes must revert",
 "H": "forced/price-insensitive flow around scheduled listing & delisting events",
}


def build_specs():
    """(trial_id, family, hypothesis, mechanism, callable) -- fixed BEFORE running."""
    S = []
    add = lambda *a: S.append(a)

    # ---- Family A: flow & positioning ----
    for z in (1.5, 2.0, 3.0):
        add(f"A01_z{z}", "A", "Long when funding z-score extremely negative", M["A"],
            partial(SG.A01_funding_neg_extreme, z=z))
        add(f"A02_z{z}", "A", "Short when funding z-score extremely positive", M["A"],
            partial(SG.A02_funding_pos_extreme, z=z))
    for th in (0.00005, 0.0001, 0.0003):
        add(f"A03_t{th}", "A", "Funding carry: short perp when funding persistently positive", M["A"],
            partial(SG.A03_funding_carry, thresh=th))
    add("A04", "A", "Funding sign flip as regime change", M["A"], SG.A04_funding_signflip)
    for frac in (0.1, 0.2):
        add(f"A05_f{frac}", "A", "Cross-sectional funding rank long cheap/short dear", M["A"],
            partial(SG.A05_xs_funding_rank, frac=frac))
    for hold in (6, 12, 24):
        add(f"A06_h{hold}", "A", "OI up + price up -> fade crowded longs", M["A"],
            partial(SG.A06_oi_up_px_up_fade, hold=hold))
        add(f"A07_h{hold}", "A", "OI down + price up -> follow short squeeze", M["A"],
            partial(SG.A07_oi_dn_px_up_follow, hold=hold))
        add(f"A08_h{hold}", "A", "OI up + price down -> fade new shorts", M["A"],
            partial(SG.A08_oi_up_px_dn_fade, hold=hold))
        add(f"A09_h{hold}", "A", "OI down + price down -> buy long capitulation", M["A"],
            partial(SG.A09_oi_dn_px_dn_buy, hold=hold))
    for z in (2.0, 3.0):
        add(f"A10_z{z}", "A", "OI rate-of-change extreme -> fade leverage build-up", M["A"],
            partial(SG.A10_oi_roc_extreme, z=z))
        add(f"A11_z{z}", "A", "Top-trader L/S extreme -> follow informed cohort", M["A"],
            partial(SG.A11_toptrader_follow, z=z))
        add(f"A12_z{z}", "A", "Retail account L/S extreme -> fade the crowd", M["A"],
            partial(SG.A12_retail_fade, z=z))
        add(f"A13_z{z}", "A", "Taker buy/sell ratio extreme -> fade aggressive flow", M["A"],
            partial(SG.A13_taker_flow_fade, z=z))
    for z in (3.0, 4.0):
        for hold in (12, 24, 48):
            add(f"A15_z{z}_h{hold}", "A",
                "Cascade reversion RESTRUCTURED: long-only, higher z, longer hold (Run-6 fix)",
                "Run-6: long side was gross +18bps and cost-killed; short side wrong-signed",
                partial(SG.A15_cascade_long_only, z=z, hold=hold))

    # ---- Family B: cross-sectional ----
    for lb, tag in ((24, "1d"), (72, "3d"), (168, "7d"), (720, "30d")):
        for frac in (0.1, 0.2):
            add(f"B_mom_{tag}_f{frac}", "B", f"Cross-sectional momentum {tag} decile L/S", M["B"],
                partial(SG.B_momentum, lookback_h=lb, frac=frac))
        add(f"B_momLO_{tag}", "B", f"Cross-sectional momentum {tag} LONG-ONLY", M["B"],
            partial(SG.B_momentum, lookback_h=lb, long_only=True))
    for lb in (1, 3, 6):
        for hold in (1, 3, 6):
            add(f"B_rev_{lb}h_h{hold}", "B", f"Short-horizon reversal {lb}h", M["B"],
                partial(SG.B_reversal, lookback_h=lb, hold=hold))
    add("B08", "B", "Idiosyncratic-vol ranking (long low idio vol)", M["B"], SG.B08_idio_vol)
    add("B09", "B", "Low-beta anomaly ranking", M["B"], SG.B09_low_beta)
    add("B10", "B", "Funding-adjusted momentum", M["B"], SG.B10_funding_adj_momentum)
    add("B11", "B", "Liquidity-scaled momentum", M["B"], SG.B11_liquidity_scaled_momentum)
    add("B12", "B", "Sector rotation L1/DeFi/Meme/Infra", M["B"], SG.B12_sector_rotation)

    # ---- Family C: volatility ----
    for q in (0.1, 0.2, 0.3):
        add(f"C01_q{q}", "C", "Realised-vol compression -> expansion breakout", M["C"],
            partial(SG.C01_vol_compression_breakout, q=q))
    for hold in (6, 12, 24):
        add(f"C05_h{hold}", "C", "Range contraction -> breakout", M["C"],
            partial(SG.C05_range_contraction, hold=hold))
    add("C10", "C", "Regime-conditional: revert in high vol, trend in low vol", M["C"],
        SG.C10_regime_conditional)

    # ---- Family D: time & microstructure ----
    sessions = {"asia_open": [0,1,2], "europe_open": [7,8,9], "us_open": [13,14,15],
                "europe_close": [16,17], "us_close": [20,21]}
    for name, hrs in sessions.items():
        for d in (1, -1):
            add(f"D_{name}_{'long' if d>0 else 'short'}", "D",
                f"Session effect {name} ({'long' if d>0 else 'short'})", M["D"],
                partial(SG.D_hour_bucket, hours=hrs, direction=d))
    for d in (1, -1):
        add(f"D06_pre_settle_{'long' if d>0 else 'short'}", "D",
            "Pre-funding-settlement hour drift", M["D"],
            partial(SG.D_hour_bucket, hours=[23,7,15], direction=d))
        add(f"D07_post_settle_{'long' if d>0 else 'short'}", "D",
            "Post-funding-settlement hour drift", M["D"],
            partial(SG.D_hour_bucket, hours=[0,8,16], direction=d))
    add("D08", "D", "Settlement drift conditional on funding sign", M["D"], SG.D08_settlement_conditional)
    add("D09", "D", "Weekend move reverts", M["D"], SG.D09_weekend_revert)
    for dow in range(7):
        add(f"D12_dow{dow}", "D", f"Day-of-week {dow} long", M["D"],
            partial(SG.D_dow_bucket, days=[dow], direction=1))

    # ---- Family E: stat-arb ----
    for z in (1.5, 2.0, 3.0):
        add(f"E06_z{z}", "E", "Beta-hedged residual reversion", M["E"],
            partial(SG.E06_residual_reversion, z=z))
        add(f"E09_z{z}", "E", "Alt/BTC ratio reversion", M["E"],
            partial(SG.E09_alt_btc_ratio_revert, z=z))
    for lag in (1, 2, 3):
        add(f"E04_lag{lag}", "E", f"BTC leads alts by {lag}h", M["E"],
            partial(SG.E04_btc_leadlag, lag=lag))

    # ---- Family H: events ----
    for days in (7, 14, 30):
        for d in (1, -1):
            add(f"H02_d{days}_{'long' if d>0 else 'short'}", "H",
                f"New perp listing first {days}d drift", M["H"],
                partial(SG.H02_new_listing_drift, days=days, direction=d))
    for days in (7, 14):
        for d in (1, -1):
            add(f"H04_d{days}_{'long' if d>0 else 'short'}", "H",
                f"Delisting run-up last {days}d", M["H"],
                partial(SG.H04_delisting_runup, days=days, direction=d))
    return S


def main():
    PART.assert_partition()
    manifest = json.load(open(OUT / "download_manifest.json"))
    universe = [s for s, n in manifest["klines"].items() if isinstance(n, int) and n > 24 * 60]
    print(f"universe with usable klines: {len(universe)}")

    mman = json.load(open(OUT / "metrics_manifest.json"))
    msyms = mman["metrics_universe"]
    t0, t1 = PART.PARTITIONS["development"]
    print(f"building development panel ... (metrics allowlist: {len(msyms)} symbols)", flush=True)
    pan = P.build_panel(universe, t0, t1, need_metrics=True, metrics_symbols=msyms)
    print(f"panel: {len(pan.index)} bars x {len(pan.assets)} assets "
          f"({pan.index.min()} .. {pan.index.max()})")
    have_metrics = int(pan.f["oi"].notna().any().sum())
    print(f"assets with positioning/OI metrics: {have_metrics}")
    btc = pan.close["BTCUSDT"] if "BTCUSDT" in pan.close.columns else pan.close.iloc[:, 0]

    specs = build_specs()
    print(f"specs to screen: {len(specs)}")
    rows, results = [], []
    for tid, fam, hyp, mech, fn in specs:
        ledger.open_trial(tid, fam, hyp, mech, params=str(getattr(fn, "keywords", {})),
                          timeframe="1h", universe=f"{len(pan.assets)} perps incl delisted",
                          tier="1", partition="development")
        try:
            W = fn(pan)
            if W is None or W.abs().to_numpy().sum() == 0:
                raise ValueError("empty signal")
            r = P.evaluate(W, pan, cost_mult=2.5)
            reg = P.regime_split(r["net_returns"], btc)
            passed = (r["net_bps_per_bar"] > 0 and r["n_trades"] >= MIN_TRADES
                      and reg["n_positive_regimes"] >= MIN_POS_REGIMES)
            if passed:
                cause, outcome = "", "ADVANCE_TIER2"
            elif r["n_trades"] < MIN_TRADES:
                cause, outcome = f"too few trades ({r['n_trades']}<{MIN_TRADES})", "KILLED"
            elif r["net_bps_per_bar"] <= 0:
                cause, outcome = f"net edge {r['net_bps_per_bar']}bps<=0 at pessimistic cost", "KILLED"
            else:
                cause, outcome = f"only {reg['n_positive_regimes']}/3 regimes positive", "KILLED"
            rows.append({"trial_id": tid, "n_trades": r["n_trades"],
                         "gross_edge_bps": r["gross_bps_per_bar"],
                         "net_edge_bps_pessimistic": r["net_bps_per_bar"],
                         "sharpe_raw": r["sharpe_net"], "outcome": outcome,
                         "cause_of_death": cause,
                         "notes": f"regimes={reg['bull']}/{reg['bear']}/{reg['chop']} "
                                  f"dd={r['max_dd_pct']}%"})
            results.append({"trial_id": tid, "family": fam, "hypothesis": hyp,
                            **{k: v for k, v in r.items() if k != "net_returns"},
                            "regime_bull": reg["bull"], "regime_bear": reg["bear"],
                            "regime_chop": reg["chop"], "n_pos_regimes": reg["n_positive_regimes"],
                            "outcome": outcome, "cause_of_death": cause})
            print(f"  {tid:28s} n={r['n_trades']:6d} gross={r['gross_bps_per_bar']:+7.3f} "
                  f"net={r['net_bps_per_bar']:+7.3f} sh={r['sharpe_net']:+6.2f} {outcome}")
        except Exception as e:  # noqa: BLE001
            rows.append({"trial_id": tid, "outcome": "ERROR", "cause_of_death": str(e)[:120]})
            results.append({"trial_id": tid, "family": fam, "hypothesis": hyp,
                            "outcome": "ERROR", "cause_of_death": str(e)[:120]})
            print(f"  {tid:28s} ERROR {str(e)[:80]}")
    ledger.bulk_close(rows)
    pd.DataFrame(results).to_csv(OUT / "tier1_results.csv", index=False)
    adv = [r for r in results if r.get("outcome") == "ADVANCE_TIER2"]
    print(f"\n=== TIER 1 DONE. specs={len(specs)} advanced={len(adv)} "
          f"total_ledger_trials={ledger.total_trials()} ===")
    for a in adv:
        print(f"   ADVANCE {a['trial_id']:28s} net={a['net_bps_per_bar']} sharpe={a['sharpe_net']}")


if __name__ == "__main__":
    main()
