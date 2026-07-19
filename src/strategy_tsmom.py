"""S1: time-series momentum / trend-following, multi-market futures.

Structural cause: persistent under-reaction + hedging/rebalancing flows; the
most out-of-sample-replicated systematic effect in the literature. Includes
a deliberately obscure market (lean hogs) alongside liquid ones, since lower
crowding is the entire structural argument for including it.

Rule: trailing {63,126,252}-day return sign, position sized to a 10%
annualized ex-ante vol target using a trailing 60-day realized-vol scalar,
monthly rebalance. No look-ahead: signal computed through day t's close,
applied starting day t+1 (shift pattern reused from Run 1/2's crypto
momentum code, which was itself validated there against look-ahead bugs).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import data_tradfi as dt
from . import tradfi_costs as tc
from . import stats

MARKETS = {"ES": "ES=F", "ZN": "ZN=F", "6E": "6E=F", "GC": "GC=F", "CL": "CL=F", "HE": "HE=F"}
LOOKBACKS = [63, 126, 252]
VOL_TARGET_ANN = 0.10
VOL_LOOKBACK_DAYS = 60
MAX_LEVERAGE = 3.0
REBAL_FREQ_DAYS = 21  # ~monthly in trading days


def load_market_series() -> dict:
    out = {}
    for name, ticker in MARKETS.items():
        df = dt.fetch_yahoo_history(ticker)
        if df.empty:
            continue
        s = df.set_index("timestamp")["close"].sort_index()
        s.index = s.index.tz_localize(None).normalize()
        s = s[~s.index.duplicated(keep="last")]
        out[name] = s
    return out


def backtest_single_market(close: pd.Series, lookback: int, market_name: str) -> tuple[pd.Series, pd.Series, int]:
    """Returns (gross_daily_returns, net_daily_returns, n_rebalances)."""
    daily_ret = close.pct_change()
    trailing_ret = close.pct_change(lookback)
    realized_vol = daily_ret.rolling(VOL_LOOKBACK_DAYS).std() * np.sqrt(252)

    idx = close.index
    rebal_mask = np.zeros(len(idx), dtype=bool)
    rebal_mask[::REBAL_FREQ_DAYS] = True

    position = pd.Series(0.0, index=idx)
    current_pos = 0.0
    for i in range(len(idx)):
        if rebal_mask[i]:
            sig = trailing_ret.iloc[i]
            vol = realized_vol.iloc[i]
            if pd.notna(sig) and pd.notna(vol) and vol > 0:
                raw = np.sign(sig) * VOL_TARGET_ANN / vol
                current_pos = float(np.clip(raw, -MAX_LEVERAGE, MAX_LEVERAGE))
        position.iloc[i] = current_pos

    applied_pos = position.shift(1).fillna(0.0)  # no look-ahead: use yesterday's locked-in position
    gross_ret = applied_pos * daily_ret

    # costs: charge a round-trip whenever the applied position changes materially
    pos_changes = applied_pos.diff().fillna(applied_pos.iloc[0])
    cost_bps_series = pd.Series(0.0, index=idx)
    n_rebal = 0
    for i in range(len(idx)):
        if abs(pos_changes.iloc[i]) > 1e-6:
            price = close.iloc[i]
            if pd.isna(price) or price <= 0:
                continue
            contract = tc.FUTURES_CONTRACTS[market_name]
            notional_per_contract = price * contract.notional_per_point_micro
            rt_cost_usd = tc.futures_round_trip_cost_usd(market_name, use_micro=True)
            cost_bps = rt_cost_usd / notional_per_contract * 10000 if notional_per_contract > 0 else 0
            cost_bps_series.iloc[i] = cost_bps * abs(pos_changes.iloc[i])
            n_rebal += 1
    net_ret = gross_ret - cost_bps_series / 10000
    return gross_ret.dropna(), net_ret.dropna(), n_rebal


def run_all() -> dict:
    series = load_market_series()
    train_dates, holdout_dates = None, None
    results = {}
    blend_by_lookback = {}

    for lookback in LOOKBACKS:
        market_net_rets = {}
        for name, close in series.items():
            gross, net, n_rebal = backtest_single_market(close, lookback, name)
            if len(net) < 500:
                results[f"{name}_lb{lookback}"] = {"error": "insufficient history"}
                continue
            if train_dates is None:
                train_dates, holdout_dates = stats.train_holdout_split(net.index, 0.3)
            split_date = train_dates.max()
            is_ret = net[net.index <= split_date]
            ho_ret = net[net.index > split_date]

            m_gross = _sharpe_block(gross)
            m_net = _sharpe_block(net)
            m_is = _sharpe_block(is_ret)
            m_ho = _sharpe_block(ho_ret)
            p_is = stats.one_sided_pvalue(is_ret.values)
            p_ho = stats.one_sided_pvalue(ho_ret.values)
            dsr = stats.deflated_sharpe_ratio(is_ret.values, n_trials=len(LOOKBACKS) * len(MARKETS) + len(LOOKBACKS))

            key = f"{name}_lb{lookback}"
            results[key] = {"gross": m_gross, "net": m_net, "net_is": m_is, "net_holdout": m_ho,
                             "n_rebalances": n_rebal, "p_is": round(p_is, 5), "p_holdout": round(p_ho, 5),
                             "dsr": dsr}
            stats.register_test(f"S1_tsmom_{key}", "S1_tsmom", f"market={name},lookback={lookback}",
                                 "none (well-replicated in literature)", n_rebal,
                                 sharpe_is=m_is["sharpe_ann"], p_is=p_is, sharpe_holdout=m_ho["sharpe_ann"], p_holdout=p_ho,
                                 registry_path=stats.REGISTRY_PATH_V5)
            net.to_frame("ret").to_csv(f"results/s1_tsmom_{key}_net_returns.csv")
            market_net_rets[name] = net

        if market_net_rets:
            aligned = pd.DataFrame(market_net_rets).fillna(0.0)
            blend = aligned.mean(axis=1)
            blend_by_lookback[lookback] = blend
            split_date = train_dates.max()
            is_ret = blend[blend.index <= split_date]
            ho_ret = blend[blend.index > split_date]
            m_net = _sharpe_block(blend)
            m_is = _sharpe_block(is_ret)
            m_ho = _sharpe_block(ho_ret)
            p_is = stats.one_sided_pvalue(is_ret.values)
            p_ho = stats.one_sided_pvalue(ho_ret.values)
            key = f"BLEND_lb{lookback}"
            results[key] = {"net": m_net, "net_is": m_is, "net_holdout": m_ho, "p_is": round(p_is, 5), "p_holdout": round(p_ho, 5)}
            stats.register_test(f"S1_tsmom_{key}", "S1_tsmom", f"blend,lookback={lookback}",
                                 "none (well-replicated in literature)", len(blend), registry_path=stats.REGISTRY_PATH_V5,
                                 sharpe_is=m_is["sharpe_ann"],
                                 p_is=p_is, sharpe_holdout=m_ho["sharpe_ann"], p_holdout=p_ho)
            blend.to_frame("ret").to_csv(f"results/s1_tsmom_{key}_net_returns.csv")

    return results


def _sharpe_block(ret: pd.Series) -> dict:
    ret = ret.dropna()
    if len(ret) < 5:
        return {"sharpe_ann": None, "total_return_pct": None, "max_dd_pct": None, "n": len(ret)}
    mean, std = ret.mean(), ret.std(ddof=1)
    sharpe = float(mean / std * np.sqrt(252)) if std > 0 else 0.0
    equity = (1 + ret).cumprod()
    dd = equity / equity.cummax() - 1
    return {"sharpe_ann": round(sharpe, 3), "total_return_pct": round(float(equity.iloc[-1] - 1) * 100, 1),
            "max_dd_pct": round(float(dd.min()) * 100, 1), "n": len(ret)}


if __name__ == "__main__":
    import json
    out = run_all()
    print(json.dumps(out, indent=2, default=str))
