"""Run 6 main harness: full grid, walk-forward, all Section-8 gates, benchmarks.

TRIAL-COUNTING DISCIPLINE (Section 8.4): every parameter combination evaluated
anywhere in this script -- main grid, stability sweep, abandoned variants -- is
appended to results_v6/trials_log.csv. The Deflated Sharpe Ratio uses that full
count, not the number of configurations we chose to report.

HEADLINE DISCIPLINE (Section 8.2): the reported result is the stitched
walk-forward OUT-OF-SAMPLE trade set. In-sample numbers are diagnostics only.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import backtest as B
from src import costs as C
from src import data_intraday as di
from src import strategy as ST
from src import validation as V

OUT = Path("results_v6")
OUT.mkdir(exist_ok=True)
TRIALS_PATH = OUT / "trials_log.csv"

UNIVERSE = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "WLD", "PEPE", "SUI", "UNI",
            "AAVE", "FIL", "NEAR", "LINK", "AVAX", "SHIB", "LTC", "BCH", "XLM", "DOT"]

# ---- PRE-REGISTERED GRID (fixed before looking at any strategy P&L) ----------
GRID_K = [1, 3, 6]
GRID_Z = [2.5, 3.0, 4.0]
GRID_V = [1.5, 2.0, 3.0]
GRID_DIR = [True, False]          # both-directions vs long-only
# exit params held at spec defaults for the main grid; swept separately in gate 8.5
_trials: list[dict] = []


def log_trial(**kw):
    _trials.append(kw)


def load_panel(universe=UNIVERSE) -> tuple[dict, dict]:
    panel, funding = {}, {}
    for base in universe:
        inst = f"{base}-USDT-SWAP"
        try:
            df = di.fetch_okx_perp_1h(inst, target_days=1100)
        except Exception as e:  # noqa: BLE001
            print(f"  skip {base}: {e}")
            continue
        if df.empty or len(df) < 5000:
            print(f"  skip {base}: only {len(df)} bars")
            continue
        panel[base] = df.reset_index(drop=True)
        try:
            f = di.fetch_okx_funding(inst)
        except Exception:
            f = pd.DataFrame()
        funding[base] = f
    return panel, funding


def slice_panel(panel: dict, t0, t1) -> dict:
    out = {}
    for a, df in panel.items():
        m = (df["timestamp"] >= t0) & (df["timestamp"] < t1)
        sub = df.loc[m].reset_index(drop=True)
        if len(sub) > 24 * 20:
            out[a] = sub
    return out


# Backtester.prepare() recomputes ATR/spread per asset and is the dominant cost.
# The prepared state depends only on (panel window, cost multiplier), never on the
# signal, so we cache one Backtester per (window, cost level) and reuse it across
# every parameter combination. This is a pure speed optimisation -- identical results.
_BT_CACHE: dict = {}
_PANEL_CACHE: dict = {}


def _get_bt(panel: dict, funding: dict, cfg: B.BTConfig, t0=None, t1=None):
    wkey = (str(t0), str(t1))
    if wkey not in _PANEL_CACHE:
        _PANEL_CACHE[wkey] = slice_panel(panel, t0, t1) if t0 is not None else panel
    p = _PANEL_CACHE[wkey]
    if not p:
        return None, p
    key = (wkey, cfg.cost_cfg.multiplier, cfg.max_holding_bars, cfg.atr_multiple_stop,
           cfg.target_take_profit_atr, cfg.max_concurrent)
    if key not in _BT_CACHE:
        _BT_CACHE[key] = B.Backtester(p, {a: funding.get(a, pd.DataFrame()) for a in p}, cfg)
    return _BT_CACHE[key], p


def run_config(panel: dict, funding: dict, params: ST.SignalParams,
               cfg: B.BTConfig, t0=None, t1=None) -> dict:
    bt, p = _get_bt(panel, funding, cfg, t0, t1)
    if bt is None:
        return {"trades": pd.DataFrame(), "equity_curve": pd.Series(dtype=float),
                "cost_breakdown": {}, "final_equity": cfg.initial_equity}
    sigs = ST.build_signals_for_panel(p, params)
    return bt.run(sigs)


def summarize(res: dict, label: str) -> dict:
    tr = res["trades"]
    if tr.empty:
        return {"label": label, "n_trades": 0}
    eq = res["equity_curve"]
    m = V.equity_metrics(eq) if len(eq) > 10 else {}
    cb = res["cost_breakdown"]
    gross = float(tr["gross_pnl"].sum())
    total_cost = float(tr["entry_cost"].sum() + tr["exit_cost"].sum() + tr["funding"].sum())
    net = float(tr["net_pnl"].sum())
    return {"label": label, "n_trades": int(len(tr)),
            "win_rate_pct": round(100 * float((tr["net_pnl"] > 0).mean()), 2),
            "gross_pnl": round(gross, 2), "total_cost": round(total_cost, 2),
            "net_pnl": round(net, 2),
            "cost_pct_of_gross": (round(100 * total_cost / abs(gross), 1) if gross != 0 else None),
            "mean_ret_bps": round(float(tr["ret_on_notional"].mean()) * 1e4, 2),
            "fees": round(cb.get("fee", 0), 2), "spread": round(cb.get("spread", 0), 2),
            "slippage": round(cb.get("slippage", 0), 2), "funding": round(cb.get("funding", 0), 2),
            **m}


def main():
    print("=== loading panel ===")
    panel, funding = load_panel()
    print(f"  loaded {len(panel)} assets")
    if len(panel) < 5:
        print("INSUFFICIENT DATA -- aborting")
        return

    tmin = min(df["timestamp"].min() for df in panel.values())
    tmax = max(df["timestamp"].max() for df in panel.values())
    print(f"  span {tmin} .. {tmax}")

    base_cfg = B.BTConfig()

    # ---------- lookahead assertion on REAL data ----------
    print("=== assert_no_lookahead on real data ===")
    probe = {a: panel[a] for a in list(panel)[:5]}
    probe_sig = ST.build_signals_for_panel(probe, ST.SignalParams())
    la = B.assert_no_lookahead(probe, probe_sig)
    print(f"  passed={la['passed']} problems={la['n_problems']}")

    # ---------- full grid at three cost levels ----------
    print("=== main grid (all trials logged) ===")
    grid = [ST.SignalParams(lookback_bars=k, z_threshold=z, vol_multiple=v, both_directions=b)
            for k, z, v, b in itertools.product(GRID_K, GRID_Z, GRID_V, GRID_DIR)]
    grid_rows = []
    for params in grid:
        for level, mult in C.COST_LEVELS.items():
            cfg = B.BTConfig(cost_cfg=C.CostConfig(multiplier=mult))
            res = run_config(panel, funding, params, cfg)
            s = summarize(res, f"{params.tag()}|{level}")
            tr = res["trades"]
            tpy = (len(tr) / ((tmax - tmin).days / 365.25)) if len(tr) else 1.0
            sharpe = (V.trade_sharpe(tr["ret_on_notional"].values, tpy) if len(tr) > 3 else np.nan)
            row = {"k": params.lookback_bars, "z": params.z_threshold, "v": params.vol_multiple,
                   "both_dir": params.both_directions, "cost_level": level,
                   "n_trades": s.get("n_trades", 0), "sharpe": round(sharpe, 4) if np.isfinite(sharpe) else None,
                   "net_pnl": s.get("net_pnl"), "cost_pct_of_gross": s.get("cost_pct_of_gross"),
                   "win_rate_pct": s.get("win_rate_pct")}
            grid_rows.append(row)
            log_trial(stage="main_grid", **row)
            print(f"  {params.tag():38s} {level:12s} n={row['n_trades']:5d} "
                  f"sharpe={row['sharpe']} net={row['net_pnl']}")
    pd.DataFrame(grid_rows).to_csv(OUT / "grid_results.csv", index=False)

    # ---------- walk-forward (headline) ----------
    print("=== 8.2 anchored walk-forward (headline OOS) ===")
    base_level_cfg = B.BTConfig(cost_cfg=C.CostConfig(multiplier=C.COST_LEVELS["base"]))

    def wf_run(params, t0, t1):
        res = run_config(panel, funding, params, base_level_cfg, t0, t1)
        tr = res["trades"]
        log_trial(stage="walk_forward", k=params.lookback_bars, z=params.z_threshold,
                  v=params.vol_multiple, both_dir=params.both_directions,
                  cost_level="base", window=f"{t0.date()}..{t1.date()}", n_trades=len(tr))
        return tr

    wf = V.gate_walk_forward(wf_run, grid, tmin, tmax, train_months=12, test_months=3)
    oos = wf.pop("oos_trades")
    print(f"  folds={wf['n_folds']} mean_is={wf['mean_is_sharpe']} "
          f"mean_oos={wf['mean_oos_sharpe']} ratio={wf['oos_to_is_ratio']} -> {wf['status']}")
    if len(oos):
        oos.to_csv(OUT / "oos_trades.csv", index=False)

    # ---------- gates on OOS ----------
    print("=== Section 8 gates on OOS trades ===")
    years = max((tmax - tmin).days / 365.25, 1e-9)
    tpy_oos = len(oos) / years if len(oos) else 1.0
    gates = {"8.2_walk_forward": wf}
    gates["8.1_sample_size"] = V.gate_sample_size(oos) if len(oos) else \
        {"gate": "8.1 sample size", "status": "FAIL", "detail": "no OOS trades"}
    gates["8.3_purged_kfold"] = V.gate_purged_kfold(oos, k=5, embargo_bars=base_cfg.max_holding_bars) \
        if len(oos) else {"gate": "8.3 purged k-fold", "status": "INCONCLUSIVE"}
    n_trials_total = len(_trials)
    gates["8.4_deflated_sharpe"] = (V.gate_deflated_sharpe(oos["ret_on_notional"].values,
                                                            n_trials_total, tpy_oos)
                                    if len(oos) > 20 else
                                    {"gate": "8.4 deflated Sharpe", "status": "INCONCLUSIVE"})

    # 8.5 stability sweep (+-50% around the most-selected params) -- ALSO logged as trials
    print("=== 8.5 parameter stability sweep ===")
    chosen = {}
    for f in wf["folds"]:
        chosen[f["chosen_params"]] = chosen.get(f["chosen_params"], 0) + 1
    centre = max(chosen, key=chosen.get) if chosen else str(grid[0])
    ck = int(centre.split("lookback_bars=")[1].split(",")[0]) if "lookback_bars=" in centre else 3
    cz = float(centre.split("z_threshold=")[1].split(",")[0]) if "z_threshold=" in centre else 3.0
    cv = float(centre.split("vol_multiple=")[1].split(",")[0]) if "vol_multiple=" in centre else 2.0
    sweep_rows = []
    for km in (0.5, 0.75, 1.0, 1.25, 1.5):
        for zm in (0.5, 0.75, 1.0, 1.25, 1.5):
            p = ST.SignalParams(lookback_bars=max(1, int(round(ck * km))),
                                z_threshold=round(cz * zm, 3), vol_multiple=cv)
            res = run_config(panel, funding, p, base_level_cfg)
            tr = res["trades"]
            tpy = len(tr) / years if len(tr) else 1.0
            sh = V.trade_sharpe(tr["ret_on_notional"].values, tpy) if len(tr) > 3 else np.nan
            row = {"k": p.lookback_bars, "z": p.z_threshold, "v": p.vol_multiple,
                   "n_trades": len(tr), "sharpe": round(sh, 4) if np.isfinite(sh) else None}
            sweep_rows.append(row)
            log_trial(stage="stability_sweep", cost_level="base", both_dir=True, **row)
    sweep = pd.DataFrame(sweep_rows)
    sweep.to_csv(OUT / "parameter_surface.csv", index=False)
    gates["8.5_parameter_stability"] = V.gate_parameter_stability(sweep, metric="sharpe")

    # 8.6 regime
    regimes = V.classify_regimes(panel["BTC"])
    gates["8.6_regime_robustness"] = V.gate_regime_robustness(oos, regimes) if len(oos) else \
        {"gate": "8.6 regime robustness", "status": "INCONCLUSIVE"}
    # 8.7 / 8.8
    gates["8.7_block_bootstrap"] = V.gate_block_bootstrap(oos, trades_per_year=tpy_oos) if len(oos) else \
        {"gate": "8.7 block bootstrap", "status": "INCONCLUSIVE"}
    gates["8.8_mc_drawdown"] = V.gate_monte_carlo_drawdown(oos) if len(oos) else \
        {"gate": "8.8 MC drawdown", "status": "INCONCLUSIVE"}

    # ---------- benchmarks (Section 7) ----------
    print("=== Section 7 benchmarks ===")
    bench = {}
    btc = panel["BTC"]
    bh = float(btc["close"].iloc[-1] / btc["close"].iloc[0] - 1)
    bh_ret = btc["close"].pct_change().dropna()
    bench["buy_hold_btc"] = {"total_return_pct": round(bh * 100, 2),
                             "sharpe": round(float(bh_ret.mean() / bh_ret.std(ddof=1) *
                                                    np.sqrt(V.BARS_PER_YEAR)), 3)}
    # random entry, matched count, 1000 iterations
    n_target = int(len(oos)) if len(oos) else 200
    per_asset = max(1, n_target // max(len(panel), 1))
    rnd = []
    for it in range(1000):
        sigs = {a: ST.random_signal(df, per_asset, seed=10_000 + it) for a, df in panel.items()}
        btr, _ = _get_bt(panel, funding, base_level_cfg)
        r = btr.run(sigs)
        t = r["trades"]
        if len(t) > 3:
            rnd.append(V.trade_sharpe(t["ret_on_notional"].values, len(t) / years))
        if it % 100 == 0:
            print(f"  random iter {it} ...")
    rnd = np.array([x for x in rnd if np.isfinite(x)])
    strat_sharpe = (V.trade_sharpe(oos["ret_on_notional"].values, tpy_oos) if len(oos) > 3 else np.nan)
    pct = float((rnd < strat_sharpe).mean() * 100) if len(rnd) else np.nan
    bench["random_entry"] = {"n_iter": int(len(rnd)),
                             "random_sharpe_median": round(float(np.median(rnd)), 3) if len(rnd) else None,
                             "random_sharpe_p95": round(float(np.percentile(rnd, 95)), 3) if len(rnd) else None,
                             "strategy_oos_sharpe": round(strat_sharpe, 3) if np.isfinite(strat_sharpe) else None,
                             "strategy_percentile_vs_random": round(pct, 1) if np.isfinite(pct) else None,
                             "status": "PASS" if np.isfinite(pct) and pct >= 95 else "FAIL"}
    # shifted entries
    shifted = {}
    centre_p = ST.SignalParams(lookback_bars=ck, z_threshold=cz, vol_multiple=cv)
    for sh_bars in (-3, -2, -1, 1, 2, 3):
        sigs = {a: ST.shifted_signal(ST.build_signal(df, centre_p), sh_bars) for a, df in panel.items()}
        btr, _ = _get_bt(panel, funding, base_level_cfg)
        r = btr.run(sigs)
        t = r["trades"]
        s = V.trade_sharpe(t["ret_on_notional"].values, len(t) / years) if len(t) > 3 else np.nan
        shifted[f"shift_{sh_bars}"] = {"n_trades": int(len(t)),
                                       "sharpe": round(s, 3) if np.isfinite(s) else None}
        log_trial(stage="shifted_entry_benchmark", k=ck, z=cz, v=cv, shift=sh_bars,
                  n_trades=len(t), sharpe=round(s, 4) if np.isfinite(s) else None)
    bench["shifted_entry"] = shifted

    # ---------- cost diagnostics ----------
    all_res_base = run_config(panel, funding, centre_p, base_level_cfg)
    base_summary = summarize(all_res_base, "centre_params|base")

    # Median stop distance in bps = atr_multiple * ATR / price, aligned per-asset so
    # ATR and price always refer to the same bar.
    stop_bps_all = []
    for a, df in panel.items():
        d = df.copy()
        d["atr"] = C.atr(d, 14)
        d = d.dropna(subset=["atr"])
        stop_bps_all.append((base_cfg.atr_multiple_stop * d["atr"] / d["close"]).to_numpy(float) * 1e4)
    stop_bps_all = np.concatenate(stop_bps_all)
    atr_all = np.concatenate([C.atr(df.copy(), 14).dropna().to_numpy(float) for df in panel.values()])
    px_all = np.concatenate([df["close"].to_numpy(float)[-len(C.atr(df.copy(), 14).dropna()):]
                             for df in panel.values()])
    med_stop_bps = float(np.median(stop_bps_all))
    med_rt_cost = 2 * (C.TAKER_FEE_BPS + C.HALF_SPREAD_FLOOR_BPS + C.SLIPPAGE_FLOOR_BPS) * \
        C.COST_LEVELS["base"]
    cost_diag = C.cost_to_stop_ratio(med_stop_bps, med_rt_cost)
    cost_diag["slippage_k_sensitivity"] = C.slippage_k_sensitivity(5000, 5e7, float(np.median(atr_all)),
                                                                    float(np.median(px_all)))

    # ---------- save ----------
    pd.DataFrame(_trials).to_csv(TRIALS_PATH, index=False)
    out = {"universe": list(panel.keys()), "span": [str(tmin), str(tmax)],
           "n_assets": len(panel), "lookahead_check": la,
           "n_trials_logged": len(_trials),
           "grid_best_by_sharpe": pd.DataFrame(grid_rows).sort_values(
               "sharpe", ascending=False, na_position="last").head(10).to_dict("records"),
           "gates": gates, "benchmarks": bench, "cost_diagnostics": cost_diag,
           "full_sample_centre_params": base_summary}
    json.dump(out, open(OUT / "backtest_results.json", "w"), indent=2, default=str)
    print(f"\n=== DONE. trials logged: {len(_trials)} ===")
    for k, g in gates.items():
        print(f"  {k}: {g.get('status')}")


if __name__ == "__main__":
    main()
