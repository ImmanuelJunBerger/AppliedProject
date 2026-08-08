"""DIAGNOSTIC (not the headline): unthrottled cascade event study.

The portfolio backtest caps concurrent positions at 5 across 20 assets. Crypto
cascades are highly correlated -- when one asset dumps, most dump together -- so
the cap discards the large majority of signals and leaves only ~100-160 trades
over three years. That is below the Section 8.1 sample-size floor, which makes
the portfolio result INCONCLUSIVE on sample size alone rather than informative
about the underlying hypothesis.

This script therefore measures the RAW effect with no portfolio throttle: every
cascade event on every asset is measured as a forward return, so we can say
whether the hypothesised reversion exists at all, independent of whether a
5-position portfolio can harvest it. It is explicitly a diagnostic and is
reported as such -- it is NOT a tradeable P&L, because it ignores capital
constraints, and it is NOT used as the headline result.

Costs ARE applied (round-trip, base level) so the question asked is the honest
one: "does the average cascade event revert by more than it costs to trade?"
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import costs as C
from src import data_intraday as di
from src import strategy as ST
from src import validation as V

OUT = Path("results_v6")
OUT.mkdir(exist_ok=True)

UNIVERSE = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "WLD", "PEPE", "SUI", "UNI",
            "AAVE", "FIL", "NEAR", "LINK", "AVAX", "SHIB", "LTC", "BCH", "XLM", "DOT"]
HOLD_BARS = [4, 12, 24]


def load_panel():
    panel = {}
    for b in UNIVERSE:
        df = di.fetch_okx_perp_1h(f"{b}-USDT-SWAP", target_days=1100)
        if not df.empty:
            panel[b] = df.reset_index(drop=True)
    return panel


def event_study(panel: dict, p: ST.SignalParams, hold: int, cost_mult: float,
                spread_model: str = "tiered") -> pd.DataFrame:
    """One row per cascade event: forward return over `hold` bars, entered at the
    NEXT bar's open (no lookahead), net of a modelled round-trip cost."""
    rows = []
    cfg = C.CostConfig(multiplier=cost_mult)
    for asset, df in panel.items():
        d = df.reset_index(drop=True)
        sig = ST.build_signal(d, p)
        if spread_model == "corwin_schultz":
            hs = C.corwin_schultz_half_spread_bps(d["high"], d["low"])
        else:
            hs = pd.Series(C.tiered_half_spread_bps(float(d["quote_volume"].median())),
                           index=d.index)
        a = C.atr(d, 14)
        idx = np.flatnonzero(sig.values != 0)
        for i in idx:
            j_entry = i + 1                    # fill at next bar OPEN
            j_exit = j_entry + hold
            if j_exit >= len(d):
                continue
            direction = float(sig.iloc[i])
            entry = float(d["open"].iloc[j_entry])
            exit_p = float(d["open"].iloc[j_exit])
            if entry <= 0:
                continue
            gross = direction * (exit_p / entry - 1)
            notional = 5_000.0                 # representative retail clip
            rt_bps = C.round_trip_cost_bps(notional, float(d["quote_volume"].iloc[j_entry]),
                                           float(a.iloc[i]) if np.isfinite(a.iloc[i]) else 0.0,
                                           entry, float(hs.iloc[i]), cfg)
            net = gross - rt_bps / 1e4
            rows.append({"asset": asset, "entry_time": d["timestamp"].iloc[j_entry],
                         "direction": direction, "hold": hold,
                         "gross_ret": gross, "cost_bps": rt_bps, "net_ret": net})
    return pd.DataFrame(rows)


def summarize(ev: pd.DataFrame, label: str) -> dict:
    if ev.empty or len(ev) < 10:
        return {"label": label, "n": int(len(ev))}
    g, n = ev["gross_ret"].values, ev["net_ret"].values
    t_g = sps.ttest_1samp(g, 0.0)
    t_n = sps.ttest_1samp(n, 0.0)
    return {"label": label, "n_events": int(len(ev)),
            "mean_gross_bps": round(float(g.mean()) * 1e4, 2),
            "mean_net_bps": round(float(n.mean()) * 1e4, 2),
            "median_net_bps": round(float(np.median(n)) * 1e4, 2),
            "win_rate_net_pct": round(100 * float((n > 0).mean()), 2),
            "mean_cost_bps": round(float(ev["cost_bps"].mean()), 2),
            "t_stat_gross": round(float(t_g.statistic), 3),
            "p_gross_two_sided": round(float(t_g.pvalue), 5),
            "t_stat_net": round(float(t_n.statistic), 3),
            "p_net_two_sided": round(float(t_n.pvalue), 5),
            "sharpe_per_event": round(float(n.mean() / (n.std(ddof=1) + 1e-12)), 4)}


def main():
    panel = load_panel()
    print(f"loaded {len(panel)} assets")
    results, all_rows = [], []
    grid = [ST.SignalParams(lookback_bars=k, z_threshold=z, vol_multiple=v)
            for k, z, v in itertools.product([1, 3, 6], [2.5, 3.0, 4.0], [2.0])]
    for p in grid:
        for hold in HOLD_BARS:
            ev = event_study(panel, p, hold, C.COST_LEVELS["base"])
            s = summarize(ev, f"{p.tag()}|hold{hold}")
            s.update({"k": p.lookback_bars, "z": p.z_threshold, "v": p.vol_multiple, "hold_bars": hold})
            results.append(s)
            print(f"  k={p.lookback_bars} z={p.z_threshold} hold={hold:2d}  "
                  f"n={s.get('n_events',0):5d} gross={s.get('mean_gross_bps')} "
                  f"net={s.get('mean_net_bps')} p_net={s.get('p_net_two_sided')}")
            if not ev.empty:
                ev2 = ev.copy(); ev2["k"] = p.lookback_bars; ev2["z"] = p.z_threshold
                all_rows.append(ev2)

    res = pd.DataFrame(results)
    res.to_csv(OUT / "event_study_summary.csv", index=False)

    # regime + best-config detail on the largest-sample config
    detail = {}
    if all_rows:
        big = max(all_rows, key=len)
        big.to_csv(OUT / "event_study_events.csv", index=False)
        btc = panel["BTC"]
        reg = V.classify_regimes(btc).dropna(subset=["dir_regime"]).set_index("timestamp")
        big = big.copy()
        big["dir_regime"] = big["entry_time"].map(reg["dir_regime"])
        big["year"] = pd.to_datetime(big["entry_time"]).dt.year
        detail["by_regime"] = {str(k): {"n": int(len(g)),
                                        "mean_net_bps": round(float(g["net_ret"].mean()) * 1e4, 2),
                                        "win_pct": round(100 * float((g["net_ret"] > 0).mean()), 1)}
                               for k, g in big.groupby("dir_regime")}
        detail["by_year"] = {str(k): {"n": int(len(g)),
                                      "mean_net_bps": round(float(g["net_ret"].mean()) * 1e4, 2)}
                             for k, g in big.groupby("year")}
        detail["by_direction"] = {("fade_down_long" if k > 0 else "fade_up_short"):
                                  {"n": int(len(g)),
                                   "mean_gross_bps": round(float(g["gross_ret"].mean()) * 1e4, 2),
                                   "mean_net_bps": round(float(g["net_ret"].mean()) * 1e4, 2)}
                                  for k, g in big.groupby("direction")}
        # outlier sensitivity: drop top 5% of events by |P&L|
        cut = big["net_ret"].abs().quantile(0.95)
        trimmed = big[big["net_ret"].abs() <= cut]
        detail["drop_top5pct_by_abs_pnl"] = {
            "n": int(len(trimmed)),
            "mean_net_bps": round(float(trimmed["net_ret"].mean()) * 1e4, 2)}
    # SPREAD-MODEL SENSITIVITY: rerun the largest-sample config under the pessimistic
    # Corwin-Schultz spread estimator, so the report can state whether the verdict
    # depends on the spread assumption at all.
    sens = {}
    p_ref = ST.SignalParams(lookback_bars=3, z_threshold=3.0, vol_multiple=2.0)
    for model in ("tiered", "corwin_schultz"):
        for lvl, mult in C.COST_LEVELS.items():
            ev = event_study(panel, p_ref, 24, mult, spread_model=model)
            sens[f"{model}|{lvl}"] = summarize(ev, f"{model}|{lvl}")
    detail["spread_model_sensitivity"] = sens
    print("\n-- spread-model sensitivity (k=3,z=3.0,hold=24) --")
    for kk, vv in sens.items():
        print(f"  {kk:28s} n={vv.get('n_events')} gross={vv.get('mean_gross_bps')} "
              f"net={vv.get('mean_net_bps')} cost={vv.get('mean_cost_bps')}")

    json.dump({"summary": results, "detail": detail},
              open(OUT / "event_study.json", "w"), indent=2, default=str)
    print("\nsaved event_study.json")


if __name__ == "__main__":
    main()
