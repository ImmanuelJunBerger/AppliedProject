"""S6: CFTC Commitments of Traders positioning extremes.

Structural cause: commercial hedgers are argued to hold superior
informational/economic positioning versus speculators; extreme
net-positioning readings are a documented contrarian-ish signal in the
futures-positioning literature. Weekly resolution, low trade frequency.

Rule: commercial net position as % of open interest, z-scored over a
trailing 156-week (3yr) window; go WITH the commercials' direction when
|z| exceeds a threshold (2.0 primary, 1.5 sensitivity), flat otherwise.
Signal from report date t applied to the market's return over the
FOLLOWING reporting week (no look-ahead: COT data isn't public until ~3
days after the as-of date).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data_tradfi as dt
from . import tradfi_costs as tc
from . import stats

MARKETS = {
    # ES: CFTC renamed this contract's label from "...STOCK INDEX - CME" to
    # "E-MINI S&P 500 - CME" on 2022-02-08 (same underlying market, continuous
    # open interest before/after) -- both name variants are spliced together.
    "ES": (["E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE",
            "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE"], "ES=F"),
    "CL": (["CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE"], "CL=F"),
    "GC": (["GOLD - COMMODITY EXCHANGE INC."], "GC=F"),
}
Z_WINDOW_WEEKS = 156
THRESHOLDS = [2.0, 1.5]


def _sharpe_block(ret: np.ndarray, periods_per_year: float = 52) -> dict:
    ret = np.asarray(ret, dtype=float)
    ret = ret[~np.isnan(ret)]
    if len(ret) < 5:
        return {"sharpe_ann": None, "n": len(ret)}
    mean, std = ret.mean(), ret.std(ddof=1)
    sharpe = float(mean / std * np.sqrt(periods_per_year)) if std > 0 else 0.0
    return {"sharpe_ann": round(sharpe, 3), "mean_pct": round(float(mean) * 100, 4),
            "win_rate_pct": round(100 * float((ret > 0).mean()), 1), "n": len(ret)}


def run_all() -> dict:
    results = {}
    cost_bps = tc.equity_round_trip_cost_bps(liquid=True)  # rough proxy across the 3 liquid markets tested
    for name, (cftc_names, ticker) in MARKETS.items():
        frames = []
        for cftc_name in cftc_names:
            sub = dt.fetch_cftc_cot(cftc_name)
            sub = sub[sub["market_and_exchange_names"] == cftc_name]
            frames.append(sub)
        cot = pd.concat(frames).drop_duplicates(subset="report_date").sort_values("report_date")
        if cot.empty:
            results[name] = {"error": "insufficient COT data"}
            continue
        cot["comm_net"] = cot["comm_positions_long_all"] - cot["comm_positions_short_all"]
        cot["comm_net_pct_oi"] = cot["comm_net"] / cot["open_interest_all"]
        cot["z"] = ((cot["comm_net_pct_oi"] - cot["comm_net_pct_oi"].rolling(Z_WINDOW_WEEKS).mean()) /
                    cot["comm_net_pct_oi"].rolling(Z_WINDOW_WEEKS).std())
        cot["report_date"] = cot["report_date"].dt.tz_localize(None)
        cot = cot.set_index("report_date")

        px = dt.fetch_yahoo_history(ticker)
        if px.empty:
            results[name] = {"error": "insufficient price data"}
            continue
        px = px.sort_values("timestamp").reset_index(drop=True)
        px["date"] = px["timestamp"].dt.tz_convert(None).dt.normalize()
        close = px.set_index("date")["close"]

        for th in THRESHOLDS:
            trades = []
            report_dates = cot.index.tolist()
            for i in range(len(report_dates) - 1):
                z = cot["z"].iloc[i]
                if pd.isna(z) or abs(z) < th:
                    continue
                direction = 1 if z > 0 else -1
                entry_date, exit_date = report_dates[i], report_dates[i + 1]
                # snap to nearest available trading days on/after each report date
                entry_loc = close.index.searchsorted(entry_date)
                exit_loc = close.index.searchsorted(exit_date)
                if entry_loc >= len(close) or exit_loc >= len(close) or exit_loc <= entry_loc:
                    continue
                ret = direction * (close.iloc[exit_loc] / close.iloc[entry_loc] - 1)
                trades.append({"date": close.index[exit_loc], "ret": ret})
            tdf = pd.DataFrame(trades)
            key = f"{name}_z{th}"
            if tdf.empty or len(tdf) < 5:
                results[key] = {"error": "too few extreme-z events", "n": len(tdf)}
                stats.register_test(f"S6_cot_{key}", "S6_cot_positioning", key, "commercial hedger informational edge",
                                     len(tdf), registry_path=stats.REGISTRY_PATH_V5, note="too few events")
                continue
            tdf["ret_net"] = tdf["ret"] - cost_bps / 10_000
            train_dates, holdout_dates = stats.train_holdout_split(tdf["date"], 0.3)
            split = train_dates.max()
            is_df = tdf[tdf["date"] <= split]
            ho_df = tdf[tdf["date"] > split]
            net_m = _sharpe_block(tdf["ret_net"].values)
            is_m = _sharpe_block(is_df["ret_net"].values)
            ho_m = _sharpe_block(ho_df["ret_net"].values)
            p_is = stats.one_sided_pvalue(is_df["ret_net"].values)
            p_ho = stats.one_sided_pvalue(ho_df["ret_net"].values)
            results[key] = {"net": net_m, "net_is": is_m, "net_holdout": ho_m,
                             "p_is": round(p_is, 5), "p_holdout": round(p_ho, 5)}
            stats.register_test(f"S6_cot_{key}", "S6_cot_positioning", key, "commercial hedger informational edge",
                                 len(tdf), sharpe_is=is_m["sharpe_ann"], p_is=p_is,
                                 sharpe_holdout=ho_m["sharpe_ann"], p_holdout=p_ho, registry_path=stats.REGISTRY_PATH_V5)
            tdf.to_csv(f"results/s6_cot_{key}_trades.csv", index=False)
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=2, default=str))
