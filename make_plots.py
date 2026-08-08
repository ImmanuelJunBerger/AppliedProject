"""Section 10 plots. Reads results_v6/* produced by run_backtest.py and event_study.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path("results_v6")
PLOTS = OUT / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3,
                     "font.size": 9})


def savefig(fig, name):
    fig.tight_layout()
    fig.savefig(PLOTS / name, bbox_inches="tight")
    plt.close(fig)
    print("  wrote", name)


def main():
    res = json.load(open(OUT / "backtest_results.json"))

    # 1-3. OOS equity curve (log), underwater, rolling Sharpe
    p = OUT / "oos_trades.csv"
    if p.exists():
        tr = pd.read_csv(p, parse_dates=["entry_time", "exit_time"]).sort_values("exit_time")
        eq = (1 + tr["ret_on_notional"]).cumprod()
        eq.index = tr["exit_time"].values

        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(eq.index, eq.values, lw=1.3, color="#1f4e79")
        ax.set_yscale("log")
        ax.axhline(1.0, color="k", ls="--", lw=0.8)
        ax.set_title("Walk-forward OUT-OF-SAMPLE equity (log scale), net of costs")
        ax.set_ylabel("growth of 1")
        savefig(fig, "01_oos_equity_log.png")

        dd = eq / eq.cummax() - 1
        fig, ax = plt.subplots(figsize=(9, 3))
        ax.fill_between(dd.index, dd.values * 100, 0, color="#b03a2e", alpha=0.7)
        ax.set_title("OOS underwater curve")
        ax.set_ylabel("drawdown %")
        savefig(fig, "02_oos_underwater.png")

        r = tr.set_index("exit_time")["ret_on_notional"]
        roll = r.rolling(90, min_periods=30)
        rs = roll.mean() / roll.std(ddof=1) * np.sqrt(max(len(r) / 3, 1))
        fig, ax = plt.subplots(figsize=(9, 3))
        ax.plot(rs.index, rs.values, lw=1.2, color="#1f4e79")
        ax.axhline(0, color="k", ls="--", lw=0.8)
        ax.set_title("Rolling 90-trade Sharpe (OOS)")
        savefig(fig, "03_rolling_sharpe.png")

        # 7. return distribution vs normal
        fig, ax = plt.subplots(figsize=(7, 4))
        v = r.values * 1e4
        ax.hist(v, bins=60, density=True, alpha=0.65, color="#1f4e79", label="OOS trade returns")
        xs = np.linspace(v.min(), v.max(), 300)
        ax.plot(xs, (1 / (v.std() * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((xs - v.mean()) / v.std()) ** 2),
                "r--", lw=1.4, label="normal fit")
        ax.axvline(0, color="k", lw=0.8)
        ax.set_xlabel("trade return (bps)"); ax.legend()
        ax.set_title("OOS trade return distribution vs normal")
        savefig(fig, "07_return_distribution.png")

    # 4. per-regime returns (event study, big sample)
    esj = OUT / "event_study.json"
    if esj.exists():
        es = json.load(open(esj))
        byr = es.get("detail", {}).get("by_regime", {})
        if byr:
            fig, ax = plt.subplots(figsize=(6, 3.4))
            ks = list(byr.keys()); vs = [byr[k]["mean_net_bps"] for k in ks]
            ax.bar(ks, vs, color=["#b03a2e" if v < 0 else "#1e8449" for v in vs])
            ax.axhline(0, color="k", lw=0.9)
            ax.set_ylabel("mean net return (bps)")
            ax.set_title("Cascade events: mean NET return by BTC regime")
            savefig(fig, "04_by_regime.png")

        summ = pd.read_csv(OUT / "event_study_summary.csv")
        if not summ.empty:
            fig, ax = plt.subplots(figsize=(8, 4))
            for hold, g in summ.groupby("hold_bars"):
                g2 = g.sort_values("z")
                ax.plot(g2["z"], g2["mean_net_bps"], marker="o", label=f"hold {hold}h")
            ax.axhline(0, color="k", ls="--", lw=1)
            ax.set_xlabel("z threshold"); ax.set_ylabel("mean NET return (bps)")
            ax.set_title("Event study: net return vs threshold (all >3,400 events/cell)")
            ax.legend()
            savefig(fig, "08_event_study_net.png")

    # 5. parameter sensitivity surface
    ps = OUT / "parameter_surface.csv"
    if ps.exists():
        sw = pd.read_csv(ps)
        if not sw.empty and sw["sharpe"].notna().any():
            piv = sw.pivot_table(index="k", columns="z", values="sharpe")
            fig, ax = plt.subplots(figsize=(6.5, 4))
            im = ax.imshow(piv.values, cmap="RdYlGn", aspect="auto",
                           vmin=-abs(np.nanmax(np.abs(piv.values))),
                           vmax=abs(np.nanmax(np.abs(piv.values))))
            ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels([f"{c:g}" for c in piv.columns])
            ax.set_yticks(range(len(piv.index))); ax.set_yticklabels(piv.index)
            ax.set_xlabel("z threshold"); ax.set_ylabel("lookback k (bars)")
            ax.set_title("Parameter sensitivity surface (Sharpe)\nplateau = robust, peak = overfit")
            for i in range(piv.shape[0]):
                for j in range(piv.shape[1]):
                    v = piv.values[i, j]
                    if np.isfinite(v):
                        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8)
            fig.colorbar(im, ax=ax, label="Sharpe")
            savefig(fig, "05_parameter_surface.png")

    # 6. Monte Carlo drawdown histogram
    mc = res.get("gates", {}).get("8.8_mc_drawdown", {})
    tr_p = OUT / "oos_trades.csv"
    if tr_p.exists() and mc.get("status") != "INCONCLUSIVE":
        tr = pd.read_csv(tr_p)
        r = tr["ret_on_notional"].values
        rng = np.random.default_rng(11)
        dds = []
        for _ in range(5000):
            s = rng.permutation(r)
            e = np.cumprod(1 + s)
            dds.append((e / np.maximum.accumulate(e) - 1).min() * 100)
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(dds, bins=60, color="#b03a2e", alpha=0.75)
        realized = mc.get("realized_max_dd_pct")
        if realized is not None:
            ax.axvline(realized, color="k", lw=2, label=f"realized {realized}%")
        ax.axvline(np.percentile(dds, 5), color="orange", ls="--", lw=1.5,
                   label=f"5th pct {np.percentile(dds,5):.1f}%")
        ax.set_xlabel("max drawdown %"); ax.legend()
        ax.set_title("Monte Carlo max-drawdown distribution (trade order resampled)")
        savefig(fig, "06_mc_drawdown.png")

    print("plots done ->", PLOTS)


if __name__ == "__main__":
    main()
