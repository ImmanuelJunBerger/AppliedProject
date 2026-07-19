"""S8: volatility risk premium (systematic short-vol proxy).

Structural cause: implied volatility carries a well-documented, persistent
premium over subsequently realized volatility (insurance-buyer demand
exceeds compensated risk) -- the standard "sell insurance" risk premium.

Proxy: CBOE S&P 500 PutWrite Index (^PUT, Yahoo), a genuine published CBOE
benchmark (not a constructed/synthetic series -- constructing one would have
violated the no-fabrication rule) with clean daily history back to 1996.
SVXY (2011+, a real tradeable ETF) used as a shorter-history cross-check.

WARNING taken seriously per the pre-registration: this return stream is
negatively skewed by construction. Sharpe is reported, but skew, kurtosis,
max drawdown, and worst single-day/month loss are reported with equal or
greater prominence -- this file and RESULTS_V5.md both say so explicitly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

from . import data_tradfi as dt
from . import stats

ASSUMED_ANNUAL_WRAPPER_DRAG = 0.005  # ASSUMPTION: ETF-wrapper expense-ratio-style cost, applied daily


def _full_block(ret: pd.Series, periods_per_year: float = 252) -> dict:
    ret = ret.dropna()
    if len(ret) < 30:
        return {"error": "insufficient data", "n": len(ret)}
    mean, std = ret.mean(), ret.std(ddof=1)
    sharpe = float(mean / std * np.sqrt(periods_per_year)) if std > 0 else 0.0
    equity = (1 + ret).cumprod()
    dd = equity / equity.cummax() - 1
    worst_day = float(ret.min())
    monthly = (1 + ret).resample("ME").prod() - 1 if hasattr(ret.index, "freq") or True else None
    worst_month = float(monthly.min()) if monthly is not None and len(monthly) else None
    return {
        "sharpe_ann": round(sharpe, 3), "total_return_pct": round(float(equity.iloc[-1] - 1) * 100, 1),
        "max_dd_pct": round(float(dd.min()) * 100, 1), "skew": round(float(skew(ret)), 3),
        "excess_kurtosis": round(float(kurtosis(ret)), 3), "worst_day_pct": round(worst_day * 100, 2),
        "worst_month_pct": round(worst_month * 100, 2) if worst_month is not None else None,
        "n": len(ret),
    }


def run_all() -> dict:
    results = {}
    px = dt.fetch_yahoo_history("^PUT")
    if px.empty:
        results["PUT"] = {"error": "insufficient data"}
    else:
        px = px.sort_values("timestamp").reset_index(drop=True)
        px["date"] = px["timestamp"].dt.tz_convert(None).dt.normalize()
        s = px.set_index("date")["close"]

        # DATA-QUALITY BUG CAUGHT BEFORE PUBLISHING: Yahoo's ^PUT print for
        # 2020-03-13 shows the index up +35% in one day while SPX itself was up
        # +9.3% that day -- implausible for a passive monthly put-write index,
        # which mechanically produced an equally implausible -28% "correction"
        # on 2020-03-16 when the series reverted. Cross-checked against ^GSPC's
        # real (and itself extreme) daily moves that week; the magnitude
        # mismatch is the tell. Disclosed and excluded rather than silently
        # smoothed: the single suspect print is dropped and 2020-03-16's return
        # is computed against the last trusted close (2020-03-12) instead.
        s = s.drop(pd.Timestamp("2020-03-13"), errors="ignore")
        gross_ret = s.pct_change().dropna()
        net_ret = gross_ret - ASSUMED_ANNUAL_WRAPPER_DRAG / 252

        m_gross = _full_block(gross_ret)
        m_net = _full_block(net_ret)

        train_dates, holdout_dates = stats.train_holdout_split(net_ret.index, 0.3)
        split = train_dates.max()
        is_ret = net_ret[net_ret.index <= split]
        ho_ret = net_ret[net_ret.index > split]
        m_is = _full_block(is_ret)
        m_ho = _full_block(ho_ret)
        p_is = stats.one_sided_pvalue(is_ret.values)
        p_ho = stats.one_sided_pvalue(ho_ret.values)

        regimes = {}
        for label, lo, hi in (("pre_2008", None, "2007-12-31"), ("2008_2015", "2008-01-01", "2015-12-31"),
                               ("post_2015", "2016-01-01", None)):
            sub = net_ret
            if lo:
                sub = sub[sub.index >= lo]
            if hi:
                sub = sub[sub.index <= hi]
            regimes[label] = _full_block(sub)

        results["PUT"] = {"gross": m_gross, "net": m_net, "net_is": m_is, "net_holdout": m_ho,
                           "p_is": round(p_is, 5), "p_holdout": round(p_ho, 5), "regimes": regimes}
        stats.register_test("S8_volpremium_PUT", "S8_vol_risk_premium", "CBOE_PutWrite_Index",
                             "implied>realized vol premium (negatively skewed -- Sharpe is misleading)",
                             len(net_ret), sharpe_is=m_is["sharpe_ann"], p_is=p_is,
                             sharpe_holdout=m_ho["sharpe_ann"], p_holdout=p_ho, registry_path=stats.REGISTRY_PATH_V5,
                             note=f"skew={m_net.get('skew')}, max_dd_pct={m_net.get('max_dd_pct')}, worst_day_pct={m_net.get('worst_day_pct')}")
        net_ret.to_frame("ret").to_csv("results/s8_volpremium_PUT_net_returns.csv")

    svxy = dt.fetch_yahoo_history("SVXY")
    if not svxy.empty:
        svxy = svxy.sort_values("timestamp").reset_index(drop=True)
        svxy["date"] = svxy["timestamp"].dt.tz_convert(None).dt.normalize()
        s2 = svxy.set_index("date")["close"]
        ret2 = s2.pct_change().dropna()
        results["SVXY_cross_check_2011plus"] = _full_block(ret2)
        stats.register_test("S8_volpremium_SVXY", "S8_vol_risk_premium", "SVXY_ETF_cross_check",
                             "implied>realized vol premium (negatively skewed -- Sharpe is misleading)",
                             len(ret2), sharpe_is=results["SVXY_cross_check_2011plus"].get("sharpe_ann"),
                             registry_path=stats.REGISTRY_PATH_V5, note="shorter-history real-ETF cross-check, not primary")
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=2, default=str))
