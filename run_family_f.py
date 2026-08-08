"""Family F (testable subset) + H01 -- Tier-1 screen on the DEVELOPMENT partition.

HYPOTHESES_V7.md pre-declared family F as SKIP *conditional on a probe failing*.
The probe (results_v7/data_availability_probe.json) only partly failed:
  * REACHABLE -> F02 stablecoin supply, F07 chain fees, F08 active addresses, H01
    listing announcements. These are tested here rather than skipped, because
    skipping a measurable hypothesis is a silent narrowing of the search.
  * UNREACHABLE -> F01 exchange netflows, F03 SOPR, F04 MVRV, F05 dormancy,
    F06 whale accumulation (all Glassnode/CryptoQuant, HTTP 401); H03 unlocks
    (DeFiLlama 402); H08 index inclusion. Those stay SKIPPED_NO_DATA.

Same Tier-1 bar as the other 113 trials: >=300 trades, positive net edge under
the pessimistic cost model, positive in >=2 of 3 regimes. No gate is relaxed
because these arrived late.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import data_onchain as OC, ledger, panel as P, partitions as PART

OUT = Path("results_v7")
MIN_TRADES, MIN_POS_REGIMES = 300, 2


def _macro_tilt(sig: pd.Series, pan, thresh=1.0) -> pd.DataFrame:
    """Turn a single market-wide series into an equal-weight long/short book.

    These are macro on-chain signals, not cross-sectional ones: they say something
    about the whole market, so the only honest expression is a market-wide tilt
    spread equally over the assets that exist at that bar.
    """
    live = pan.close.notna()
    n = live.sum(axis=1).replace(0, np.nan)
    d = pd.Series(0.0, index=pan.index)
    d[sig >= thresh] = 1.0
    d[sig <= -thresh] = -1.0
    return live.astype(float).div(n, axis=0).mul(d, axis=0).fillna(0.0)


def _z(s: pd.Series, win: int) -> pd.Series:
    m = s.rolling(win, min_periods=win // 2).mean()
    sd = s.rolling(win, min_periods=win // 2).std()
    return ((s - m) / sd.replace(0, np.nan)).fillna(0.0)


def build_specs(pan):
    idx = pan.index
    H = 24

    stables = OC.to_hourly_lagged(OC.stablecoin_supply(), idx)
    fees = OC.to_hourly_lagged(OC.blockchain_chart("transaction-fees-usd"), idx)
    addrs = OC.to_hourly_lagged(OC.blockchain_chart("n-unique-addresses"), idx)
    ntx = OC.to_hourly_lagged(OC.blockchain_chart("n-transactions"), idx)

    # growth rates, then z-scored on a trailing 180-day window
    g_stab = _z(stables.pct_change(28 * H).fillna(0.0), 180 * H)
    g_fee = _z(np.log1p(fees).diff(1 * H).fillna(0.0), 180 * H)
    g_addr = _z(addrs.pct_change(28 * H).fillna(0.0), 180 * H)
    g_ntx = _z(ntx.pct_change(28 * H).fillna(0.0), 180 * H)

    specs = [
        ("F02_stablecoin_growth", "F",
         "Accelerating aggregate stablecoin supply precedes higher crypto returns",
         "Newly minted stablecoins are dry powder that entered to buy; the minter has "
         "already accepted fiat and must deploy",
         lambda: _macro_tilt(g_stab, pan, 1.0)),
        ("F02b_stablecoin_contraction", "F",
         "Contracting stablecoin supply precedes lower returns (short side of F02)",
         "Redemptions are capital leaving the system for good",
         lambda: _macro_tilt(g_stab, pan, 0.5)),
        ("F07_fee_spike_fade", "F",
         "BTC chain-fee spikes mark urgency-driven flow and are followed by reversal",
         "Whoever overpays a congested fee is transacting on urgency, not price; "
         "urgent flow is the classic price-insensitive loser",
         lambda: _macro_tilt(-g_fee, pan, 1.0)),
        ("F08_active_address_growth", "F",
         "Growth in unique active addresses precedes higher returns",
         "Address growth proxies genuine new participation, i.e. new marginal buyers",
         lambda: _macro_tilt(g_addr, pan, 1.0)),
        ("F08b_tx_count_growth", "F",
         "Growth in confirmed BTC transaction count precedes higher returns",
         "As F08, using settlement count instead of address count",
         lambda: _macro_tilt(g_ntx, pan, 1.0)),
    ]

    # H01 -- listing announcement drift
    ann = OC.perp_listing_announcements()
    if not ann.empty:
        def h01(hold_h):
            W = pd.DataFrame(0.0, index=idx, columns=pan.close.columns)
            hits = 0
            for _, r in ann.iterrows():
                if r["symbol"] not in W.columns:
                    continue
                lo = idx.searchsorted(r["ts"])
                if lo >= len(idx):
                    continue
                W.iloc[lo:lo + hold_h, W.columns.get_loc(r["symbol"])] = 1.0
                hits += 1
            return P.normalize_weights(W) if hits else W
        for hh in (24, 72, 168):
            specs.append((f"H01_announce_drift_{hh}h", "H",
                          f"Long from the perp-listing announcement for {hh}h",
                          "Announcement brings attention plus index/tracker and market-maker "
                          "inventory build before the contract exists",
                          (lambda h=hh: h01(h))))
    else:
        print("H01: announcement parse returned nothing -- leaving as SKIPPED", flush=True)
    return specs


def main():
    PART.assert_partition()
    man = json.load(open(OUT / "download_manifest.json"))
    uni = [s for s, n in man["klines"].items() if isinstance(n, int) and n > 24 * 60]
    t0, t1 = PART.PARTITIONS["development"]
    print(f"building DEVELOPMENT panel {t0.date()}..{t1.date()}", flush=True)
    pan = P.build_panel(uni, t0, t1, need_metrics=False)
    btc = pan.close["BTCUSDT"]
    print(f"development: {len(pan.index)} bars x {len(pan.assets)} assets", flush=True)

    specs = build_specs(pan)
    ann = OC.perp_listing_announcements()
    print(f"announcements parsed: {len(ann)} symbols, "
          f"{ann['ts'].min() if len(ann) else '-'} .. {ann['ts'].max() if len(ann) else '-'}",
          flush=True)

    rows, results = [], []
    for tid, fam, hyp, mech, fn in specs:
        ledger.open_trial(tid, fam, hyp, mech, "hold=24h unless stated", "1h",
                          f"{len(pan.assets)} perps (survivorship-free)", "1", "development",
                          notes="late-added after data-availability probe succeeded")
        try:
            W = fn()
            r = P.evaluate(W, pan, cost_mult=2.5)
            reg = P.regime_split(r["net_returns"], btc)
            ok = (r["n_trades"] >= MIN_TRADES and r["net_bps_per_bar"] > 0
                  and reg["n_positive_regimes"] >= MIN_POS_REGIMES)
            cause = ""
            if not ok:
                if r["n_trades"] < MIN_TRADES:
                    cause = f"too few trades ({r['n_trades']}<{MIN_TRADES})"
                elif r["net_bps_per_bar"] <= 0:
                    cause = (f"net-negative after costs (gross {r['gross_bps_per_bar']:+.3f} -> "
                             f"net {r['net_bps_per_bar']:+.3f} bps)")
                else:
                    cause = f"positive in only {reg['n_positive_regimes']}/3 regimes"
            out = "ADVANCE_TIER2" if ok else "KILLED"
            rows.append({"trial_id": tid, "n_trades": r["n_trades"],
                         "gross_edge_bps": r["gross_bps_per_bar"],
                         "net_edge_bps_pessimistic": r["net_bps_per_bar"],
                         "sharpe_raw": r["sharpe_net"], "outcome": out,
                         "cause_of_death": cause})
            results.append({"trial_id": tid, "family": fam, "hypothesis": hyp,
                            **{k: v for k, v in r.items() if k != "net_returns"},
                            "regime_bull": reg["bull"], "regime_bear": reg["bear"],
                            "regime_chop": reg["chop"],
                            "n_pos_regimes": reg["n_positive_regimes"],
                            "outcome": out, "cause_of_death": cause})
            print(f"{tid:30s} n={r['n_trades']:6d} gross={r['gross_bps_per_bar']:+8.4f} "
                  f"net={r['net_bps_per_bar']:+8.4f} sh={r['sharpe_net']:+6.3f} {out}", flush=True)
        except Exception as e:                                # noqa: BLE001
            rows.append({"trial_id": tid, "outcome": "ERROR", "cause_of_death": f"{type(e).__name__}: {e}"})
            print(f"{tid:30s} ERROR {type(e).__name__}: {e}", flush=True)
    ledger.bulk_close(rows)
    pd.DataFrame(results).to_csv(OUT / "family_f_results.csv", index=False)
    adv = [r["trial_id"] for r in results if r["outcome"] == "ADVANCE_TIER2"]
    print(f"\nadvanced: {adv or 'NONE'}   counted trials now = {ledger.total_trials()}")


if __name__ == "__main__":
    main()
