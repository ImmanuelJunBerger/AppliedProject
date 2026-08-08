"""Tier-2 for the late-added family-F survivors. VALIDATION partition.

Same battery as run_tier2.py, plus TWO GATES THAT ONLY APPLY TO THIS SIGNAL TYPE.

F02 and F08 are market-wide tilts: when the signal fires they go long (or short)
the entire universe at once. That is structurally different from A12, which was
cross-sectional and roughly dollar-neutral. A market-wide tilt measured over a
period when the market rose will look profitable even if the signal is noise, so
two extra gates are added rather than reusing the cross-sectional battery as-is:

  * market_alpha   -- regress net returns on the equal-weight market return.
                      The intercept must be positive and t>2. If the edge is all
                      beta, alpha collapses and the gate fails.
  * beats_buy_hold -- the strategy must beat simply holding the equal-weight
                      basket over the same window. A timing signal that
                      underperforms always-on exposure has negative information.

Adding gates to a candidate is tightening, not tuning. Neither gate was chosen
after seeing whether it would pass.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_tier2 import (block_bootstrap, deflated_sharpe, mc_drawdown, outlier_dependence,
                       purged_kfold, quarterly_consistency, random_entry_benchmark,
                       sharpe, walk_forward)
from src import ledger, panel as P, partitions as PART
import run_family_f as FF

OUT = Path("results_v7")
BPY = 24 * 365


def market_return(pan) -> pd.Series:
    """Equal-weight return of every asset alive at each bar -- the honest 'market'."""
    live = pan.close.notna()
    n = live.sum(axis=1).replace(0, np.nan)
    W = live.astype(float).div(n, axis=0).fillna(0.0)
    return P.evaluate(W, pan, cost_mult=0.0)["net_returns"]


def market_alpha(net: pd.Series, mkt: pd.Series) -> dict:
    d = pd.concat([net, mkt], axis=1).dropna()
    d.columns = ["r", "m"]
    if len(d) < 200:
        return {"status": "INCONCLUSIVE"}
    x = np.column_stack([np.ones(len(d)), d["m"].values])
    y = d["r"].values
    b, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ b
    s2 = resid @ resid / (len(d) - 2)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(x.T @ x)))
    t_a = float(b[0] / se[0]) if se[0] > 0 else 0.0
    return {"alpha_bps_per_bar": round(float(b[0]) * 1e4, 4), "t_alpha": round(t_a, 2),
            "beta_to_market": round(float(b[1]), 3),
            "status": "PASS" if (b[0] > 0 and t_a > 2.0) else "FAIL",
            "note": "an edge that is only market beta has alpha ~ 0 regardless of its Sharpe"}


def beats_buy_hold(net: pd.Series, mkt: pd.Series) -> dict:
    sm, ss = sharpe(mkt.dropna()), sharpe(net.dropna())
    return {"strategy_sharpe": round(ss, 3), "equal_weight_buyhold_sharpe": round(sm, 3),
            "status": "PASS" if ss > sm else "FAIL",
            "note": "buy-and-hold is costless here, which is generous to the benchmark on purpose"}


def main():
    PART.assert_partition()
    man = json.load(open(OUT / "download_manifest.json"))
    uni = [s for s, n in man["klines"].items() if isinstance(n, int) and n > 24 * 60]
    t0, t1 = PART.PARTITIONS["validation"]
    print(f"building VALIDATION panel {t0.date()}..{t1.date()}", flush=True)
    pan = P.build_panel(uni, t0, t1, need_metrics=False)
    dev = P.build_panel(uni, *PART.PARTITIONS["development"], need_metrics=False)
    btc = pan.close["BTCUSDT"]
    mkt = market_return(pan)
    print(f"validation: {len(pan.index)} bars x {len(pan.assets)} assets  "
          f"| equal-weight market Sharpe {sharpe(mkt):.3f}", flush=True)

    want = {"F02_stablecoin_growth", "F08_active_address_growth"}
    val_specs = {t: fn for t, _f, _h, _m, fn in FF.build_specs(pan) if t in want}
    dev_specs = {t: fn for t, _f, _h, _m, fn in FF.build_specs(dev) if t in want}

    results, streams = {}, {}
    for name, fn in val_specs.items():
        print(f"\n=== {name} ===", flush=True)
        g = {}
        W = fn()
        cost_rows = {}
        for lvl, mult in (("optimistic", 1.0), ("base", 1.5), ("pessimistic", 2.5)):
            r = P.evaluate(W, pan, cost_mult=mult)
            cost_rows[lvl] = {"net_bps_per_bar": r["net_bps_per_bar"], "sharpe": r["sharpe_net"],
                              "n_trades": r["n_trades"],
                              "gross_bps_per_bar": r["gross_bps_per_bar"],
                              "max_dd_pct": r["max_dd_pct"]}
        g["cost_levels"] = cost_rows
        base = P.evaluate(W, pan, cost_mult=1.5)
        nr = base["net_returns"]
        streams[name] = nr

        wf_fn = lambda sub, _n=name: {t: f for t, _a, _b, _c, f in FF.build_specs(sub)}[_n]()
        g["8.1_sample_size"] = {"status": "PASS" if base["n_trades"] >= 300 else "FAIL",
                                "n_trades": base["n_trades"]}
        g["walk_forward"] = walk_forward(wf_fn, pan)
        g["purged_kfold"] = purged_kfold(wf_fn, pan)
        g["regime"] = P.regime_split(nr, btc)
        g["regime"]["status"] = "PASS" if g["regime"]["n_positive_regimes"] >= 2 else "FAIL"
        g["block_bootstrap"] = block_bootstrap(nr)
        g["mc_drawdown"] = mc_drawdown(nr)
        g["quarterly"] = quarterly_consistency(nr)
        g["outlier"] = outlier_dependence(nr)
        g["market_alpha"] = market_alpha(nr, mkt)
        g["beats_buy_hold"] = beats_buy_hold(nr, mkt)

        delays = {}
        for s in (1, 2, 3):
            rr = P.evaluate(W.shift(s).fillna(0.0), pan, cost_mult=1.5)
            delays[f"delay_+{s}"] = round(rr["sharpe_net"], 3)
        g["entry_shift"] = {"actual": round(base["sharpe_net"], 3), "delays": delays,
                            "status": "PASS" if base["sharpe_net"] > max(delays.values()) else "FAIL"}

        # threshold plateau, swept on DEVELOPMENT only
        sweep = {}
        base_dev = dev_specs[name]
        for th in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
            src = {"F02_stablecoin_growth": "stab", "F08_active_address_growth": "addr"}[name]
            Wd = _rebuild(dev, src, th)
            sweep[th] = round(P.evaluate(Wd, dev, cost_mult=2.5)["net_bps_per_bar"], 4)
        pos = sum(1 for v in sweep.values() if v > 0)
        g["parameter_plateau"] = {"sweep_dev_net_bps": sweep,
                                  "fraction_positive": round(pos / len(sweep), 2),
                                  "status": "PASS" if pos / len(sweep) >= 0.6 else "FAIL"}
        _ = base_dev

        gross, net = base["gross_bps_per_bar"], base["net_bps_per_bar"]
        cost = gross - net
        g["cost_ratio"] = {"gross_bps": gross, "cost_bps": round(cost, 4),
                           "gross_to_cost_ratio": round(gross / cost, 2) if cost > 0 else None,
                           "status": "PASS" if (cost > 0 and gross / cost >= 1.5) else "FAIL"}
        results[name] = g
        for k, v in g.items():
            if isinstance(v, dict) and "status" in v:
                print(f"   {k:22s} {v['status']}", flush=True)

    S = pd.DataFrame(streams).dropna()
    results["_correlation"] = S.corr().round(3).to_dict()
    print("\ncorrelation:\n", S.corr().round(3).to_string(), flush=True)

    tt = max(results[n]["8.1_sample_size"]["n_trades"] for n in val_specs)
    rb = random_entry_benchmark(pan, tt, n_iter=300)
    total = ledger.total_trials()
    for name in val_specs:
        s_act = results[name]["cost_levels"]["base"]["sharpe"]
        pct = float(np.mean([x < s_act for x in rb["dist"]]) * 100)
        results[name]["random_entry"] = {"strategy_sharpe": s_act, "random_median": rb["median"],
                                         "random_p95": rb["p95"], "percentile": round(pct, 1),
                                         "status": "PASS" if pct >= 95 else "FAIL"}
        d = deflated_sharpe(streams[name], total)
        d["status"] = "PASS" if d.get("deflated_sharpe_prob", 0) >= 0.95 else "FAIL"
        results[name]["deflated_sharpe"] = d
        print(f"{name}: random-entry pct {pct:.1f} | DSR vs {total} trials "
              f"{d.get('deflated_sharpe_prob')} -> {d['status']}", flush=True)

    S.to_csv(OUT / "tier2b_return_streams.csv")
    json.dump(results, open(OUT / "tier2b_results.json", "w"), indent=2, default=str)

    rows = []
    for name in val_specs:
        g = results[name]
        gates = {k: v.get("status") for k, v in g.items() if isinstance(v, dict) and "status" in v}
        passed = [k for k, v in gates.items() if v == "PASS"]
        failed = [k for k, v in gates.items() if v == "FAIL"]
        outcome = "ADVANCE_TIER3" if not failed else "KILLED_TIER2"
        ledger.open_trial(f"T2_{name}", "F", "Tier-2 full gate battery (+market-neutrality gates)",
                          "market-wide on-chain tilt", "threshold z=1.0, hold=24h", "1h",
                          "135 perps", "2", "validation")
        rows.append({"trial_id": f"T2_{name}", "n_trades": g["8.1_sample_size"]["n_trades"],
                     "gross_edge_bps": g["cost_levels"]["base"]["gross_bps_per_bar"],
                     "net_edge_bps_pessimistic": g["cost_levels"]["pessimistic"]["net_bps_per_bar"],
                     "sharpe_raw": g["cost_levels"]["base"]["sharpe"],
                     "gates_passed": ";".join(passed), "gates_failed": ";".join(failed),
                     "outcome": outcome,
                     "cause_of_death": "" if not failed else "failed: " + ",".join(failed)})
        print(f"\n{name}: {outcome}  failed={failed}", flush=True)
    ledger.bulk_close(rows)
    print(f"\n=== TIER 2b DONE. counted trials={ledger.total_trials()} ===", flush=True)


def _rebuild(pan, src: str, thresh: float):
    """Re-derive an F02/F08 tilt at an arbitrary threshold, for the plateau sweep."""
    from src import data_onchain as OC
    H = 24
    if src == "stab":
        s = OC.to_hourly_lagged(OC.stablecoin_supply(), pan.index).pct_change(28 * H)
    else:
        s = OC.to_hourly_lagged(OC.blockchain_chart("n-unique-addresses"),
                                pan.index).pct_change(28 * H)
    return FF._macro_tilt(FF._z(s.fillna(0.0), 180 * H), pan, thresh)


if __name__ == "__main__":
    main()
