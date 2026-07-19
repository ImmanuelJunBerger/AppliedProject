"""S3: pre-FOMC announcement drift.

Structural cause: pre-scheduled resolution of monetary-policy uncertainty
(Lucca & Moench 2015 and follow-ups). Return window = close(t-1) -> close(t)
where t is the FOMC statement/announcement day (the last day of a scheduled
meeting), pooled across all meetings 1994-2026. Uses ^GSPC close-to-close
returns only (the open-field artifact found in S2 does not affect a
close-to-close test, so the full clean history is usable here).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data_tradfi as dt
from . import tradfi_costs as tc
from . import stats


def _sharpe_block(ret: np.ndarray) -> dict:
    ret = np.asarray(ret, dtype=float)
    ret = ret[~np.isnan(ret)]
    if len(ret) < 5:
        return {"sharpe_ann_8x_year": None, "mean_pct": None, "n": len(ret)}
    mean, std = ret.mean(), ret.std(ddof=1)
    sharpe = float(mean / std * np.sqrt(8)) if std > 0 else 0.0  # ~8 events/year
    return {"sharpe_ann_8x_year": round(sharpe, 3), "mean_pct": round(float(mean) * 100, 4),
            "win_rate_pct": round(100 * float((ret > 0).mean()), 1), "n": len(ret)}


def run_all() -> dict:
    meeting_dates = dt.fetch_fomc_meeting_dates(1994, 2026)
    px = dt.fetch_yahoo_history("^GSPC").sort_values("timestamp").reset_index(drop=True)
    px["date"] = px["timestamp"].dt.tz_convert(None).dt.normalize()
    close = px.set_index("date")["close"]
    trading_days = close.index

    cost_bps = tc.equity_round_trip_cost_bps(liquid=True)
    events = []
    for meeting_dt in meeting_dates:
        m = pd.Timestamp(meeting_dt).tz_localize(None).normalize()
        idx = trading_days.searchsorted(m)
        if idx >= len(trading_days) or trading_days[idx] != m:
            # if the parsed date isn't itself a trading day, use next available trading day as the statement close
            if idx >= len(trading_days):
                continue
        if idx == 0:
            continue
        t_close = close.iloc[idx] if idx < len(close) and trading_days[idx] == m else None
        if t_close is None:
            # snap to nearest trading day on/after m
            idx2 = trading_days.searchsorted(m)
            if idx2 >= len(trading_days):
                continue
            t_close = close.iloc[idx2]
            idx = idx2
        prev_close = close.iloc[idx - 1]
        ret = t_close / prev_close - 1
        events.append({"meeting_date": m, "close_date": trading_days[idx], "ret": ret})

    df = pd.DataFrame(events).drop_duplicates(subset="close_date").sort_values("close_date")
    df["ret_net"] = df["ret"] - cost_bps / 10_000

    train_dates, holdout_dates = stats.train_holdout_split(df["close_date"], 0.3)
    split = train_dates.max()
    is_df = df[df["close_date"] <= split]
    ho_df = df[df["close_date"] > split]

    results = {}
    for label, sub in (("full_sample", df), ("ex_2008_2009_crisis", df[~df["meeting_date"].dt.year.isin([2008, 2009])]),
                        ("ex_2020_covid", df[df["meeting_date"].dt.year != 2020])):
        gross_m = _sharpe_block(sub["ret"].values)
        net_m = _sharpe_block(sub["ret_net"].values)
        p_gross = stats.one_sided_pvalue(sub["ret"].values)
        p_net = stats.one_sided_pvalue(sub["ret_net"].values)
        results[label] = {"gross": gross_m, "net": net_m, "p_gross": round(p_gross, 5), "p_net": round(p_net, 5)}
        stats.register_test(f"S3_fomc_{label}", "S3_fomc_drift", label, "calendar-predictable uncertainty resolution",
                             len(sub), sharpe_is=net_m["sharpe_ann_8x_year"], p_is=p_net,
                             registry_path=stats.REGISTRY_PATH_V5)

    is_net = _sharpe_block(is_df["ret_net"].values)
    ho_net = _sharpe_block(ho_df["ret_net"].values)
    p_is = stats.one_sided_pvalue(is_df["ret_net"].values)
    p_ho = stats.one_sided_pvalue(ho_df["ret_net"].values)
    results["holdout_split"] = {"is": is_net, "holdout": ho_net, "p_is": round(p_is, 5), "p_holdout": round(p_ho, 5),
                                 "split_date": str(split)}
    stats.register_test("S3_fomc_holdout_split", "S3_fomc_drift", "full_sample_IS_holdout",
                         "calendar-predictable uncertainty resolution", len(df), sharpe_is=is_net["sharpe_ann_8x_year"],
                         p_is=p_is, sharpe_holdout=ho_net["sharpe_ann_8x_year"], p_holdout=p_ho,
                         registry_path=stats.REGISTRY_PATH_V5)

    df.to_csv("results/s3_fomc_events.csv", index=False)
    results["n_meetings_matched"] = len(df)
    results["n_meetings_parsed"] = len(meeting_dates)
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=2, default=str))
