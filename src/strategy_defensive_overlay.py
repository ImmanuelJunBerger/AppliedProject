"""S9: defensive/regime overlay.

Not a standalone return source -- a risk switch. Tested on the PRIMARY
constructed portfolio (S2+S4+S8, simple-risk-parity, vol-targeted), not as
an isolated return stream, per the pre-registration. Two candidate filters:
(a) trend: SPX above/below its own 200-day moving average, (b) yield curve:
10Y-3M spread (FRED T10Y3M) negative = defensive. Each tested at two
intensities: cut exposure to 0% or to 50% when the filter is "risk-off".
Signal from month-end t-1 applied to month t (no look-ahead).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data_tradfi as dt
from . import portfolio as port
from . import stats


def _ann_stats(monthly_ret: pd.Series) -> dict:
    return port._ann_stats(monthly_ret)


def run_all() -> dict:
    candidates = port.load_candidate_returns()
    primary = {k: v for k, v in candidates.items() if "SENSITIVITY" not in k}
    weights = port.build_weights(primary)["simple_risk_parity"]
    base_port = port.vol_target(port.combine_portfolio(primary, weights))
    base_stats = _ann_stats(base_port)

    spx = dt.fetch_yahoo_history("^GSPC").sort_values("timestamp").reset_index(drop=True)
    spx["date"] = spx["timestamp"].dt.tz_convert(None).dt.normalize()
    spx = spx.set_index("date")
    spx["sma200"] = spx["close"].rolling(200).mean()
    trend_signal_daily = (spx["close"] > spx["sma200"]).astype(float)
    trend_signal_monthly = trend_signal_daily.resample("ME").last().shift(1)  # last trading day of PRIOR month, no look-ahead

    t10y3m = dt.fetch_fred_series("T10Y3M")
    t10y3m = t10y3m.set_index("date")["T10Y3M"]
    t10y3m.index = t10y3m.index.tz_localize(None) if t10y3m.index.tz is not None else t10y3m.index
    curve_signal_daily = (t10y3m > 0).astype(float)
    curve_signal_monthly = curve_signal_daily.resample("ME").last().shift(1)

    results = {"base_portfolio": base_stats}
    for filt_name, sig in (("trend_200dma", trend_signal_monthly), ("yield_curve_10y3m", curve_signal_monthly)):
        for floor in (0.0, 0.5):
            sig_aligned = sig.reindex(base_port.index).ffill()
            exposure = sig_aligned.clip(lower=floor)  # 1.0 when risk-on, `floor` when risk-off
            overlaid = base_port * exposure
            m = _ann_stats(overlaid)
            key = f"{filt_name}_floor{floor}"
            results[key] = m
            stats.register_test(f"S9_overlay_{key}", "S9_defensive_overlay", key,
                                 "risk-off regime filter (not a new return source)",
                                 m.get("n_months", 0), sharpe_is=m.get("sharpe_ann"),
                                 registry_path=stats.REGISTRY_PATH_V5,
                                 note=f"base_portfolio_sharpe={base_stats.get('sharpe_ann')}")
            overlaid.to_frame("ret").to_csv(f"results/s9_overlay_{key}_monthly_returns.csv")
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=2, default=str))
