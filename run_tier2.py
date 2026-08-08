"""Tier-2 full validation for Tier-1 survivors. VALIDATION partition.

Complete gate battery. Every gate returns PASS / FAIL / INCONCLUSIVE explicitly.
Additional Tier-2 gates beyond the previous phase's battery:
  * Deflated Sharpe vs TOTAL trials in the ledger (not this strategy's own count)
  * pairwise correlation of survivors (>0.6 => same strategy, keep the better)
  * outlier dependence (drop top 5% of bars by |P&L|)
  * sub-period consistency (>=60% of quarters profitable)
  * cost-to-gross ratio (the honest analogue of cost-to-stop for a weight strategy)
"""
from __future__ import annotations

import json
import sys
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import ledger, panel as P, partitions as PART
from src import signals_v7 as SG

OUT = Path("results_v7")
BPY = 24 * 365
# This battery was executed once with a defective entry-shift gate (it pooled
# lookahead "advance" runs into the placebo set). The corrected re-run is logged
# under a fresh trial id rather than overwriting the original rows: the ledger is
# append-only, and letting the denominator grow makes the deflated Sharpe harder,
# not easier. Nothing about the strategy definition changed between the two runs.
RUN_TAG = "r2"
EULER = 0.5772156649015329


def sharpe(r: pd.Series) -> float:
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(BPY)) if sd > 0 else 0.0


def deflated_sharpe(r: pd.Series, n_trials: int) -> dict:
    x = r.dropna().values
    T = len(x)
    sd = x.std(ddof=1)
    if T < 50 or sd <= 0:
        return {"error": "insufficient", "T": T}
    sr = x.mean() / sd
    g3, g4 = float(skew(x)), float(kurtosis(x, fisher=False))
    sig = np.sqrt(max(1e-12, (1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / max(1, T - 1)))
    sr0 = sig * ((1 - EULER) * norm.ppf(1 - 1.0 / n_trials) +
                 EULER * norm.ppf(1 - 1.0 / (n_trials * np.e))) if n_trials > 1 else 0.0
    return {"per_bar_sharpe": round(float(sr), 6),
            "annualised": round(float(sr * np.sqrt(BPY)), 3),
            "expected_max_under_null": round(float(sr0), 6),
            "deflated_sharpe_prob": round(float(norm.cdf((sr - sr0) / sig)), 4),
            "n_trials": int(n_trials), "T": T}


def block_bootstrap(r: pd.Series, n_iter=10000, block=24, seed=7) -> dict:
    x = r.dropna().values
    if len(x) < 200:
        return {"status": "INCONCLUSIVE"}
    rng = np.random.default_rng(seed)
    n = len(x); nb = int(np.ceil(n / block))
    out = []
    for _ in range(n_iter):
        st = rng.integers(0, max(1, n - block), size=nb)
        s = np.concatenate([x[i:i + block] for i in st])[:n]
        sd = s.std(ddof=1)
        out.append(s.mean() / sd * np.sqrt(BPY) if sd > 0 else 0.0)
    lo, hi = np.percentile(out, [2.5, 97.5])
    return {"status": "PASS" if lo > 0 else "FAIL",
            "sharpe_ci95": [round(float(lo), 3), round(float(hi), 3)],
            "median": round(float(np.median(out)), 3)}


def mc_drawdown(r: pd.Series, n_iter=10000, seed=11) -> dict:
    x = r.dropna().values
    if len(x) < 200:
        return {"status": "INCONCLUSIVE"}
    rng = np.random.default_rng(seed)
    dds = []
    for _ in range(n_iter):
        s = rng.permutation(x)
        eq = np.cumprod(1 + s)
        dds.append(float((eq / np.maximum.accumulate(eq) - 1).min()))
    eq = np.cumprod(1 + x)
    return {"status": "INFO",
            "realized_max_dd_pct": round(float((eq / np.maximum.accumulate(eq) - 1).min()) * 100, 2),
            "mc_median_pct": round(float(np.median(dds)) * 100, 2),
            "mc_p05_pct": round(float(np.percentile(dds, 5)) * 100, 2)}


def quarterly_consistency(r: pd.Series) -> dict:
    q = r.resample("QE").sum()
    if len(q) < 3:
        return {"status": "INCONCLUSIVE", "n_quarters": int(len(q))}
    frac = float((q > 0).mean())
    return {"status": "PASS" if frac >= 0.60 else "FAIL", "n_quarters": int(len(q)),
            "fraction_positive": round(frac, 2),
            "by_quarter_bps": {str(k.date()): round(v * 1e4, 1) for k, v in q.items()}}


def outlier_dependence(r: pd.Series) -> dict:
    x = r.dropna()
    cut = x.abs().quantile(0.95)
    trimmed = x[x.abs() <= cut]
    return {"full_mean_bps": round(float(x.mean()) * 1e4, 4),
            "trimmed_mean_bps": round(float(trimmed.mean()) * 1e4, 4),
            "status": "PASS" if trimmed.mean() > 0 else "FAIL",
            "note": "edge must survive removing top 5% of bars by |P&L|"}


def walk_forward(fn, pan, n_folds=5) -> dict:
    idx = pan.index
    bounds = np.array_split(np.arange(len(idx)), n_folds)
    sh = []
    for b in bounds:
        sub = pan.sub(idx[b[0]], idx[b[-1]])
        if len(sub.index) < 200:
            continue
        r = P.evaluate(fn(sub), sub, cost_mult=1.5)
        sh.append(sharpe(r["net_returns"]))
    if not sh:
        return {"status": "INCONCLUSIVE"}
    return {"status": "PASS" if (np.mean(sh) > 0 and np.mean([s > 0 for s in sh]) >= 0.6) else "FAIL",
            "fold_sharpes": [round(s, 3) for s in sh],
            "mean": round(float(np.mean(sh)), 3),
            "fraction_positive": round(float(np.mean([s > 0 for s in sh])), 2)}


def purged_kfold(fn, pan, k=5, embargo_bars=24) -> dict:
    idx = pan.index
    bounds = np.array_split(np.arange(len(idx)), k)
    sh = []
    for b in bounds:
        lo = max(0, b[0] + embargo_bars)     # embargo the first `embargo_bars` of each fold
        if lo >= b[-1]:
            continue
        sub = pan.sub(idx[lo], idx[b[-1]])
        if len(sub.index) < 200:
            continue
        r = P.evaluate(fn(sub), sub, cost_mult=1.5)
        sh.append(sharpe(r["net_returns"]))
    if not sh:
        return {"status": "INCONCLUSIVE"}
    return {"status": "PASS" if (np.mean(sh) > 0 and np.mean([s > 0 for s in sh]) >= 0.6) else "FAIL",
            "fold_sharpes": [round(s, 3) for s in sh], "mean": round(float(np.mean(sh)), 3),
            "embargo_bars": embargo_bars}


def random_entry_benchmark(pan, target_trades, n_iter=500, seed=3) -> dict:
    rng = np.random.default_rng(seed)
    idx, cols = pan.index, pan.close.columns
    n = len(idx)
    per = max(1, int(target_trades / max(len(cols), 1)))
    out = []
    for it in range(n_iter):
        W = pd.DataFrame(0.0, index=idx, columns=cols)
        for c in cols:
            picks = rng.choice(n, size=min(per, n), replace=False)
            W.iloc[picks, W.columns.get_loc(c)] = rng.choice([1.0, -1.0], size=len(picks))
        W = SG._fwd_hold(W, 24)
        r = P.evaluate(W, pan, cost_mult=1.5)
        out.append(sharpe(r["net_returns"]))
    return {"n_iter": n_iter, "median": round(float(np.median(out)), 3),
            "p95": round(float(np.percentile(out, 95)), 3), "dist": out}


def main():
    PART.assert_partition()
    man = json.load(open(OUT / "download_manifest.json"))
    mman = json.load(open(OUT / "metrics_manifest.json"))
    uni = [s for s, n in man["klines"].items() if isinstance(n, int) and n > 24 * 60]
    t0, t1 = PART.PARTITIONS["validation"]
    print(f"building VALIDATION panel {t0.date()}..{t1.date()}", flush=True)
    pan = P.build_panel(uni, t0, t1, need_metrics=True, metrics_symbols=mman["metrics_universe"])
    dev = P.build_panel(uni, *PART.PARTITIONS["development"], need_metrics=True,
                        metrics_symbols=mman["metrics_universe"])
    btc = pan.close["BTCUSDT"]
    print(f"validation: {len(pan.index)} bars x {len(pan.assets)} assets", flush=True)

    survivors = {"A12_z2.0": partial(SG.A12_retail_fade, z=2.0),
                 "A12_z3.0": partial(SG.A12_retail_fade, z=3.0)}

    results, streams = {}, {}
    for name, fn in survivors.items():
        print(f"\n=== {name} ===", flush=True)
        g = {}
        # 3 cost levels on validation
        cost_rows = {}
        for lvl, mult in (("optimistic", 1.0), ("base", 1.5), ("pessimistic", 2.5)):
            r = P.evaluate(fn(pan), pan, cost_mult=mult)
            cost_rows[lvl] = {"net_bps_per_bar": r["net_bps_per_bar"],
                              "sharpe": r["sharpe_net"], "n_trades": r["n_trades"],
                              "gross_bps_per_bar": r["gross_bps_per_bar"],
                              "max_dd_pct": r["max_dd_pct"]}
        g["cost_levels"] = cost_rows
        base = P.evaluate(fn(pan), pan, cost_mult=1.5)
        nr = base["net_returns"]
        streams[name] = nr

        g["8.1_sample_size"] = {"status": "PASS" if base["n_trades"] >= 300 else "FAIL",
                                "n_trades": base["n_trades"]}
        g["walk_forward"] = walk_forward(fn, pan)
        g["purged_kfold"] = purged_kfold(fn, pan)
        g["regime"] = P.regime_split(nr, btc)
        g["regime"]["status"] = "PASS" if g["regime"]["n_positive_regimes"] >= 2 else "FAIL"
        g["block_bootstrap"] = block_bootstrap(nr)
        g["mc_drawdown"] = mc_drawdown(nr)
        g["quarterly"] = quarterly_consistency(nr)
        g["outlier"] = outlier_dependence(nr)

        # Entry-shift tests. These are TWO different things and must not be pooled:
        #   * DELAY (+k): the real placebo. Act k bars late on the same signal. If the
        #     edge survives being late, the timing carries no information and what is
        #     really being measured is regime/beta exposure.
        #   * ADVANCE (-k): NOT a placebo -- W.shift(-k) feeds bar t+k's signal into
        #     bar t+1's return, i.e. deliberate lookahead. It is a sanity check that
        #     the engine can detect an edge at all, never a gate.
        # An earlier version of this gate pooled both and required the actual to beat
        # the maximum, which the lookahead variants always win. That was a defect in
        # the gate, not evidence about the strategy.
        delays, advances = {}, {}
        for s in (1, 2, 3):
            rr = P.evaluate(fn(pan).shift(s).fillna(0.0), pan, cost_mult=1.5)
            delays[f"delay_+{s}"] = round(rr["sharpe_net"], 3)
            ra = P.evaluate(fn(pan).shift(-s).fillna(0.0), pan, cost_mult=1.5)
            advances[f"advance_-{s}"] = round(ra["sharpe_net"], 3)
        g["entry_shift"] = {"actual": round(base["sharpe_net"], 3), "delays": delays,
                            "status": "PASS" if base["sharpe_net"] > max(delays.values()) else "FAIL",
                            "note": ("PASS only means the edge degrades when acted on late. "
                                     "It says nothing about whether the edge is positive.")}
        g["lookahead_sanity"] = {"advances": advances, "actual": round(base["sharpe_net"], 3),
                                 "note": ("INFORMATIONAL ONLY -- these are lookahead runs. "
                                          "Higher Sharpe here is expected and is not a result.")}

        # parameter plateau, swept on DEVELOPMENT (never on validation)
        sweep = {}
        for z in (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
            rr = P.evaluate(SG.A12_retail_fade(dev, z=z), dev, cost_mult=2.5)
            sweep[z] = round(rr["net_bps_per_bar"], 4)
        pos = sum(1 for v in sweep.values() if v > 0)
        g["parameter_plateau"] = {"sweep_dev_net_bps": sweep,
                                  "fraction_positive": round(pos / len(sweep), 2),
                                  "status": "PASS" if pos / len(sweep) >= 0.6 else "FAIL"}

        # cost-to-gross (honest analogue of cost-to-stop for a weights strategy)
        gross = base["gross_bps_per_bar"]; net = base["net_bps_per_bar"]
        cost = gross - net
        g["cost_ratio"] = {"gross_bps": gross, "cost_bps": round(cost, 4),
                           "cost_pct_of_gross": round(100 * cost / abs(gross), 1) if gross else None,
                           "gross_to_cost_ratio": round(gross / cost, 2) if cost > 0 else None,
                           "status": "PASS" if (cost > 0 and gross / cost >= 1.5) else "FAIL",
                           "note": ("cost-to-STOP is undefined for a continuous-weight strategy; "
                                    "gross-to-cost is reported as the honest analogue")}
        results[name] = g
        for k, v in g.items():
            if isinstance(v, dict) and "status" in v:
                print(f"   {k:22s} {v['status']}", flush=True)

    # correlation between survivors
    S = pd.DataFrame(streams).dropna()
    corr = S.corr()
    results["_correlation"] = corr.round(3).to_dict()
    print("\ncorrelation:\n", corr.round(3).to_string(), flush=True)

    # random-entry benchmark (shared)
    tt = max(results[n]["8.1_sample_size"]["n_trades"] for n in survivors)
    rb = random_entry_benchmark(pan, tt, n_iter=500)
    for name in survivors:
        s_act = results[name]["cost_levels"]["base"]["sharpe"]
        pct = float(np.mean([x < s_act for x in rb["dist"]]) * 100)
        results[name]["random_entry"] = {"strategy_sharpe": s_act,
                                         "random_median": rb["median"], "random_p95": rb["p95"],
                                         "percentile": round(pct, 1),
                                         "status": "PASS" if pct >= 95 else "FAIL"}
        print(f"{name} random-entry percentile: {pct:.1f} -> "
              f"{results[name]['random_entry']['status']}", flush=True)

    # DSR against TOTAL ledger trials
    total = ledger.total_trials()
    for name in survivors:
        results[name]["deflated_sharpe"] = deflated_sharpe(streams[name], total)
        d = results[name]["deflated_sharpe"]
        d["status"] = "PASS" if d.get("deflated_sharpe_prob", 0) >= 0.95 else "FAIL"
        print(f"{name} DSR vs {total} trials: {d.get('deflated_sharpe_prob')} -> {d['status']}",
              flush=True)

    S.to_csv(OUT / "tier2_return_streams.csv")
    json.dump(results, open(OUT / "tier2_results.json", "w"), indent=2, default=str)

    # ledger update
    rows = []
    for name in survivors:
        g = results[name]
        gates = {k: v.get("status") for k, v in g.items() if isinstance(v, dict) and "status" in v}
        passed = [k for k, v in gates.items() if v == "PASS"]
        failed = [k for k, v in gates.items() if v == "FAIL"]
        outcome = "ADVANCE_TIER3" if not failed else "KILLED_TIER2"
        ledger.open_trial(f"T2_{name}_{RUN_TAG}", "A", "Tier-2 full gate battery",
                          "retail account L/S extreme -> fade the crowded, under-capitalised side",
                          "z=2.0/3.0, win=30d, hold=24h", "1h", "25 metrics symbols",
                          "2", "validation")
        rows.append({"trial_id": f"T2_{name}_{RUN_TAG}",
                     "n_trades": g["8.1_sample_size"]["n_trades"],
                     "gross_edge_bps": g["cost_levels"]["base"]["gross_bps_per_bar"],
                     "net_edge_bps_pessimistic": g["cost_levels"]["pessimistic"]["net_bps_per_bar"],
                     "sharpe_raw": g["cost_levels"]["base"]["sharpe"],
                     "gates_passed": ";".join(passed), "gates_failed": ";".join(failed),
                     "outcome": outcome,
                     "cause_of_death": ("" if not failed else "failed: " + ",".join(failed))})
        print(f"\n{name}: {outcome}  failed={failed}", flush=True)
    ledger.bulk_close(rows)
    print(f"\n=== TIER 2 DONE. total ledger trials={ledger.total_trials()} ===", flush=True)


if __name__ == "__main__":
    main()
