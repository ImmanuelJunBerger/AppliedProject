"""S4: turn-of-month effect.

Structural cause: pension contributions, payroll-linked retail flows, and
index-fund rebalancing concentrate around calendar month boundaries --
forced/insensitive flow. Rule: hold from N trading days before month-end
through M trading days into the next month (one round trip per month),
N,M in {1,2,3,4}. Only the 4 "diagonal" (N=M) combinations are scored as
primary tests; the other 12 are logged descriptively only, matching Run 2's
B7 seasonality-bucket discipline (counted in N_TESTS, not promoted to holdout).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data_tradfi as dt
from . import tradfi_costs as tc
from . import stats

WINDOWS = [1, 2, 3, 4]


def _sharpe_block(ret: np.ndarray, events_per_year: float = 12) -> dict:
    ret = np.asarray(ret, dtype=float)
    ret = ret[~np.isnan(ret)]
    if len(ret) < 5:
        return {"sharpe_ann": None, "mean_pct": None, "n": len(ret)}
    mean, std = ret.mean(), ret.std(ddof=1)
    sharpe = float(mean / std * np.sqrt(events_per_year)) if std > 0 else 0.0
    return {"sharpe_ann": round(sharpe, 3), "mean_pct": round(float(mean) * 100, 4),
            "win_rate_pct": round(100 * float((ret > 0).mean()), 1), "n": len(ret)}


def run_all() -> dict:
    px = dt.fetch_yahoo_history("^GSPC").sort_values("timestamp").reset_index(drop=True)
    px["date"] = px["timestamp"].dt.tz_convert(None).dt.normalize()
    px["ym"] = px["date"].dt.to_period("M")
    close = px.set_index("date")["close"]
    cost_bps = tc.equity_round_trip_cost_bps(liquid=True)

    months = sorted(px["ym"].unique())
    month_day_idx = {m: px.index[px["ym"] == m].tolist() for m in months}

    all_window_returns = {}  # (N,M) -> list of (event_date, ret)
    for N in WINDOWS:
        for M in WINDOWS:
            events = []
            for mi in range(len(months) - 1):
                this_month_days = month_day_idx[months[mi]]
                next_month_days = month_day_idx[months[mi + 1]]
                if len(this_month_days) < N or len(next_month_days) < M:
                    continue
                entry_loc = this_month_days[-N]  # N-th-to-last trading day of this month
                exit_loc = next_month_days[M - 1]  # M-th trading day of next month
                entry_px = px["close"].iloc[entry_loc - 1] if entry_loc > 0 else None  # prior close, no look-ahead into the window itself
                if entry_px is None:
                    continue
                exit_px = px["close"].iloc[exit_loc]
                ret = exit_px / entry_px - 1
                events.append({"date": px["date"].iloc[exit_loc], "ret": ret})
            all_window_returns[(N, M)] = pd.DataFrame(events)

    results = {"note": "diagonal N=M combos are primary/scored; off-diagonal are descriptive only"}
    train_dates_ref = None
    for N in WINDOWS:
        for M in WINDOWS:
            df = all_window_returns[(N, M)]
            if df.empty:
                continue
            df["ret_net"] = df["ret"] - cost_bps / 10_000
            key = f"N{N}_M{M}"
            is_primary = (N == M)
            if is_primary:
                train_dates, holdout_dates = stats.train_holdout_split(df["date"], 0.3)
                split = train_dates.max()
                is_df = df[df["date"] <= split]
                ho_df = df[df["date"] > split]
                gross_m = _sharpe_block(df["ret"].values)
                net_m = _sharpe_block(df["ret_net"].values)
                is_m = _sharpe_block(is_df["ret_net"].values)
                ho_m = _sharpe_block(ho_df["ret_net"].values)
                p_is = stats.one_sided_pvalue(is_df["ret_net"].values)
                p_ho = stats.one_sided_pvalue(ho_df["ret_net"].values)
                results[key] = {"gross": gross_m, "net": net_m, "net_is": is_m, "net_holdout": ho_m,
                                 "p_is": round(p_is, 5), "p_holdout": round(p_ho, 5), "primary": True}
                stats.register_test(f"S4_tom_{key}", "S4_turn_of_month", key, "forced flow (pension/payroll)",
                                     len(df), sharpe_is=is_m["sharpe_ann"], p_is=p_is,
                                     sharpe_holdout=ho_m["sharpe_ann"], p_holdout=p_ho, registry_path=stats.REGISTRY_PATH_V5)
                df.to_csv(f"results/s4_tom_{key}_events.csv", index=False)
            else:
                net_m = _sharpe_block(df["ret_net"].values)
                results[key] = {"net": net_m, "primary": False}
                stats.register_test(f"S4_tom_{key}", "S4_turn_of_month_offdiag", key, "forced flow (pension/payroll) -- descriptive only",
                                     len(df), sharpe_is=net_m["sharpe_ann"], registry_path=stats.REGISTRY_PATH_V5,
                                     note="off-diagonal, descriptive only, not promoted to holdout")
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=2, default=str))
