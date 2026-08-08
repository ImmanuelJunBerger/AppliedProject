"""Combination stage, decay analysis, and graveyard forensics.

COMBINATION STAGE IS VOID. It combines Tier-2 survivors, and there are none. It is
still run below on the four Tier-2 *candidates* purely as diagnostics, and the
output is labelled as such -- combining four rejected strategies does not produce
an accepted one, and no combination result is eligible for the holdout.

DECAY is the interesting part. Every candidate looked fine on development and
died on validation. This quantifies how fast, which is the single most useful
thing the program produced.

The holdout partition is never loaded by this file.
"""
from __future__ import annotations

import json
import sys
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_tier2 import block_bootstrap, deflated_sharpe, sharpe
from src import ledger, panel as P, partitions as PART
from src import signals_v7 as SG
import run_family_f as FF

OUT = Path("results_v7")
BPY = 24 * 365


def decay_profile(name, fn_dev, fn_val, dev, val) -> dict:
    """Development vs validation, plus a time-trend regression inside each."""
    out = {"name": name}
    for tag, fn, pan in (("development", fn_dev, dev), ("validation", fn_val, val)):
        r = P.evaluate(fn(), pan, cost_mult=1.5)
        nr = r["net_returns"]
        half = len(nr) // 2
        # slope of cumulative P&L against time: negative => the edge is fading
        y = nr.fillna(0.0).values
        x = np.arange(len(y))
        slope = float(np.polyfit(x, np.cumsum(y), 1)[0]) * 1e4
        out[tag] = {
            "net_bps_per_bar": r["net_bps_per_bar"],
            "sharpe": r["sharpe_net"],
            "first_half_bps": round(float(nr.iloc[:half].mean()) * 1e4, 4),
            "second_half_bps": round(float(nr.iloc[half:].mean()) * 1e4, 4),
            "cum_pnl_slope_bps_per_bar": round(slope, 5),
            "yearly_bps": {str(k): round(float(v) * 1e4, 3)
                           for k, v in nr.groupby(nr.index.year).mean().items()},
            "rolling_90d_sharpe_frac_positive": round(float(
                (nr.rolling(24 * 90).mean() > 0).mean()), 3),
        }
    d, v = out["development"], out["validation"]
    out["decay"] = {
        "dev_to_val_sharpe_drop": round(d["sharpe"] - v["sharpe"], 3),
        "dev_to_val_net_bps_drop": round(d["net_bps_per_bar"] - v["net_bps_per_bar"], 4),
        "retained_fraction": (round(v["net_bps_per_bar"] / d["net_bps_per_bar"], 3)
                              if d["net_bps_per_bar"] > 0 else None),
    }
    return out


def capacity_estimate(name, W: pd.DataFrame, pan, adv_frac=0.05) -> dict:
    """Crude capacity: notional at which one bar's trades exceed adv_frac of volume.

    Deliberately crude and stated as such. It answers "is this a 1k EUR idea or a
    1m EUR idea", not "what is the exact capacity".
    """
    turn = (W - W.shift(1)).abs()
    qv = pan.f["qv"].reindex_like(turn)
    # per-bar tradable notional per unit of book gross, then take a low percentile
    with np.errstate(divide="ignore", invalid="ignore"):
        cap = (qv * adv_frac / turn.replace(0, np.nan))
    per_bar = cap.min(axis=1).dropna()
    if per_bar.empty:
        return {"status": "INCONCLUSIVE"}
    return {"adv_fraction_assumed": adv_frac,
            "capacity_usd_p10": round(float(np.percentile(per_bar, 10))),
            "capacity_usd_median": round(float(np.median(per_bar))),
            "note": "binding constraint is the least liquid asset held in a bar"}


def main():
    PART.assert_partition()
    man = json.load(open(OUT / "download_manifest.json"))
    mman = json.load(open(OUT / "metrics_manifest.json"))
    uni = [s for s, n in man["klines"].items() if isinstance(n, int) and n > 24 * 60]
    dev = P.build_panel(uni, *PART.PARTITIONS["development"], need_metrics=True,
                        metrics_symbols=mman["metrics_universe"])
    val = P.build_panel(uni, *PART.PARTITIONS["validation"], need_metrics=True,
                        metrics_symbols=mman["metrics_universe"])
    print(f"dev {len(dev.index)} bars | val {len(val.index)} bars", flush=True)

    cands = {
        "A12_z2.0": (partial(SG.A12_retail_fade, z=2.0), partial(SG.A12_retail_fade, z=2.0)),
        "A12_z3.0": (partial(SG.A12_retail_fade, z=3.0), partial(SG.A12_retail_fade, z=3.0)),
    }
    for nm in ("F02_stablecoin_growth", "F08_active_address_growth"):
        cands[nm] = ({t: f for t, *_r, f in [(s[0], s[1], s[2], s[3], s[4])
                                             for s in FF.build_specs(dev)]}[nm],
                     {t: f for t, *_r, f in [(s[0], s[1], s[2], s[3], s[4])
                                             for s in FF.build_specs(val)]}[nm])

    report = {"combination_stage": {"status": "VOID",
                                    "reason": "zero Tier-2 survivors; nothing eligible to combine",
                                    "diagnostic_only": True}}

    decay, streams_val, streams_dev = {}, {}, {}
    for name, (fd, fv) in cands.items():
        fdev = (lambda f=fd: f(dev)) if name.startswith("A12") else fd
        fval = (lambda f=fv: f(val)) if name.startswith("A12") else fv
        decay[name] = decay_profile(name, fdev, fval, dev, val)
        streams_dev[name] = P.evaluate(fdev(), dev, cost_mult=1.5)["net_returns"]
        Wv = fval()
        streams_val[name] = P.evaluate(Wv, val, cost_mult=1.5)["net_returns"]
        decay[name]["capacity"] = capacity_estimate(name, Wv, val)
        d = decay[name]
        print(f"\n{name}: dev sharpe {d['development']['sharpe']:+.3f} -> "
              f"val {d['validation']['sharpe']:+.3f}  "
              f"(net {d['development']['net_bps_per_bar']:+.3f} -> "
              f"{d['validation']['net_bps_per_bar']:+.3f} bps)", flush=True)
        print(f"   dev yearly: {d['development']['yearly_bps']}", flush=True)
        print(f"   val yearly: {d['validation']['yearly_bps']}", flush=True)
        print(f"   capacity  : {d['capacity']}", flush=True)
    report["decay"] = decay

    # --- diagnostic-only combination on the VALIDATION streams -----------------
    S = pd.DataFrame(streams_val).dropna()
    corr = S.corr()
    report["combination_stage"]["correlation_validation"] = corr.round(3).to_dict()
    print("\nvalidation correlation:\n", corr.round(3).to_string(), flush=True)

    combos = {}
    ew = S.mean(axis=1)
    iv = (S / S.std()).mean(axis=1)
    combos["equal_weight"] = ew
    combos["inverse_vol"] = iv
    total = ledger.total_trials()
    for cname, cr in combos.items():
        bb = block_bootstrap(cr)
        combos_out = {"sharpe": round(sharpe(cr), 3),
                      "net_bps_per_bar": round(float(cr.mean()) * 1e4, 4),
                      "bootstrap": bb,
                      "deflated_sharpe": deflated_sharpe(cr, total),
                      "eligible_for_holdout": False,
                      "note": "diagnostic only -- a blend of rejected strategies is still rejected"}
        report["combination_stage"][cname] = combos_out
        print(f"{cname:14s} sharpe {combos_out['sharpe']:+.3f} "
              f"CI {bb.get('sharpe_ci95')} DSR {combos_out['deflated_sharpe'].get('deflated_sharpe_prob')}",
              flush=True)

    # --- graveyard forensics ---------------------------------------------------
    t1 = pd.read_csv(OUT / "tier1_results.csv")
    ff = pd.read_csv(OUT / "family_f_results.csv")
    allt = pd.concat([t1, ff], ignore_index=True)
    fam = allt.groupby("family").agg(
        n=("trial_id", "size"),
        median_gross=("gross_bps_per_bar", "median"),
        median_net=("net_bps_per_bar", "median"),
        best_net=("net_bps_per_bar", "max"),
        advanced=("outcome", lambda s: int((s == "ADVANCE_TIER2").sum())),
    ).round(4)
    gp = allt[allt.gross_bps_per_bar > 0]
    cost_killed = gp[gp.net_bps_per_bar <= 0]
    causes = allt["cause_of_death"].fillna("").str.extract(
        r"^(too few trades|net-negative after costs|positive in only)")[0].value_counts()
    report["graveyard"] = {
        "by_family": fam.to_dict(orient="index"),
        "n_total_screened": int(len(allt)),
        "n_gross_positive": int(len(gp)),
        "n_gross_positive_but_cost_killed": int(len(cost_killed)),
        "median_gross_of_cost_killed_bps": round(float(cost_killed.gross_bps_per_bar.median()), 4)
        if len(cost_killed) else None,
        "median_net_of_cost_killed_bps": round(float(cost_killed.net_bps_per_bar.median()), 4)
        if len(cost_killed) else None,
        "cause_counts": causes.to_dict(),
    }
    print("\n--- graveyard by family ---\n", fam.to_string(), flush=True)
    print(f"\ngross-positive: {len(gp)}/{len(allt)}   of those, cost-killed: {len(cost_killed)}",
          flush=True)
    print("causes:", causes.to_dict(), flush=True)

    report["trial_accounting"] = {
        "counted_trials_dsr_denominator": total,
        "ledger_rows": int(len(ledger.load())),
        "holdout_touches_used": PART.holdout_touches_used(),
        "holdout_touch_budget": PART.MAX_HOLDOUT_TOUCHES,
    }
    json.dump(report, open(OUT / "decay_and_combination.json", "w"), indent=2, default=str)
    print(f"\ncounted trials={total}  holdout touches used="
          f"{PART.holdout_touches_used()}/{PART.MAX_HOLDOUT_TOUCHES}", flush=True)


if __name__ == "__main__":
    main()
