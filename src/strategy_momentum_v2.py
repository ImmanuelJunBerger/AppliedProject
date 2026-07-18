"""Track A1: point-in-time cross-sectional momentum.

Fixes Run 1's structural bug: Run 1 ranked the universe by TODAY's volume and
applied it retroactively (0/50 symbols had 90%+ history over the window).
Here, universe membership at each rebalance is decided using only trailing
volume data available *as of that date*, drawn from a broad pool of all
currently-listed non-stablecoin USDT pairs (440 symbols) so that tokens which
were prominent earlier in the window but smaller today are not excluded by
construction the way a top-50-today filter would exclude them.

Residual, uncorrectable bias (disclosed, not hidden): tokens that fully
DELISTED from Binance are invisible to this method too, since we can only
enumerate currently-trading symbols. This fixes the ranking-date look-ahead;
it does not fix delisted-token survivorship. Both are named explicitly in
RESULTS_V2.md.
"""
from __future__ import annotations

import re
import time
import numpy as np
import pandas as pd

from . import data, engine, stats

LOOKBACKS = [7, 14, 30]
REBAL_FREQ_DAYS = 7
TOP_N_BY_VOLUME = 50   # eligible pool size at each rebalance, point-in-time
QUINTILE_FRAC = 0.2
MIN_HISTORY_DAYS = 20  # must have this much trailing history to be eligible
HOLDOUT_FRAC = 0.3


def full_non_stable_usdt_universe() -> list[str]:
    raw = data._get(f"{data.BINANCE_VISION}/api/v3/exchangeInfo")
    syms = [s["symbol"] for s in raw["symbols"] if s["symbol"].endswith("USDT") and s["status"] == "TRADING"]
    syms = [s for s in syms if re.match(r"^[A-Z0-9]+USDT$", s) and not any(x in s for x in ("UP", "DOWN", "BEAR", "BULL"))]
    non_crypto = data.NON_CRYPTO_BASES | data.TOKENIZED_EQUITY_BASES
    return [s for s in syms if s[:-4] not in non_crypto]


def load_broad_panel(days: int = 750) -> tuple[pd.DataFrame, pd.DataFrame]:
    symbols = full_non_stable_usdt_universe()
    closes, vols = {}, {}
    for i, sym in enumerate(symbols):
        try:
            df = data.fetch_binance_spot_klines(sym, "1d", days)
        except Exception:
            continue
        if df.empty:
            continue
        closes[sym] = df.set_index("timestamp")["close"]
        vols[sym] = df.set_index("timestamp")["quote_volume"]
        if i % 100 == 0:
            time.sleep(0.05)
    price_panel = pd.DataFrame(closes).sort_index()
    vol_panel = pd.DataFrame(vols).sort_index()
    return price_panel, vol_panel


def backtest_pit_momentum(price_panel: pd.DataFrame, vol_panel: pd.DataFrame,
                           lookback: int, allow_short: bool) -> tuple[pd.Series, pd.Series, int, float, list]:
    daily_index = price_panel.index
    daily_rets = price_panel.pct_change()
    trailing_ret = price_panel.pct_change(lookback)
    trailing_vol_7d = vol_panel.rolling(7).mean()

    min_history_days = max(MIN_HISTORY_DAYS, lookback + 5)
    rebal_dates = set(daily_index[::REBAL_FREQ_DAYS])
    gross_equity = [engine.CAPITAL_EUR]
    net_equity = [engine.CAPITAL_EUR]
    dates_out = [daily_index[0]]
    current_weights = pd.Series(dtype=float)
    trades = 0
    turnover = 0.0
    trade_returns = []  # per-rebalance-period portfolio return, for pooled stats

    for i in range(1, len(daily_index)):
        d = daily_index[i]
        prev_d = daily_index[i - 1]
        if d in rebal_dates and prev_d in trailing_vol_7d.index:
            # point-in-time eligibility: enough trailing history as of prev_d
            hist_counts = price_panel.loc[:prev_d].notna().sum()
            eligible = hist_counts[hist_counts >= min_history_days].index
            vol_now = trailing_vol_7d.loc[prev_d, eligible].dropna()
            top_pool = vol_now.sort_values(ascending=False).head(TOP_N_BY_VOLUME).index
            sig = trailing_ret.loc[prev_d, top_pool].dropna()
            sig = sig[price_panel.loc[prev_d, sig.index].notna()]
            n = len(sig)
            if n >= 10:
                k = max(1, int(n * QUINTILE_FRAC))
                ranked = sig.sort_values(ascending=False)
                longs = ranked.index[:k]
                shorts = ranked.index[-k:] if allow_short else []
                w = pd.Series(0.0, index=sig.index)
                w.loc[longs] = 1.0 / k
                if allow_short:
                    w.loc[shorts] = -1.0 / k
                new_weights = w
            else:
                new_weights = current_weights
        else:
            new_weights = current_weights

        day_ret = daily_rets.loc[d]
        port_ret = float((current_weights.reindex(day_ret.index).fillna(0) * day_ret.fillna(0)).sum())
        g = gross_equity[-1] * (1 + port_ret)
        n_e = net_equity[-1] * (1 + port_ret)
        if d in rebal_dates:
            trade_returns.append({"date": d, "port_ret": port_ret, "universe_size": len(current_weights[current_weights != 0])})

        if not new_weights.equals(current_weights):
            all_syms = set(new_weights.index) | set(current_weights.index)
            cost_frac = 0.0
            traded_notional = 0.0
            for sym in all_syms:
                dw = abs(new_weights.get(sym, 0.0) - current_weights.get(sym, 0.0))
                if dw < 1e-9:
                    continue
                notional = dw * n_e
                traded_notional += notional
                adv = float(vol_panel[sym].reindex([prev_d]).iloc[0]) if sym in vol_panel.columns and prev_d in vol_panel.index else None
                cost_frac += engine.trade_cost_eur(sym, notional, "spot", adv)
            if traded_notional > 1e-6:
                n_e -= cost_frac
                trades += 1
                turnover += traded_notional
            current_weights = new_weights

        gross_equity.append(g)
        net_equity.append(n_e)
        dates_out.append(d)

    return (pd.Series(gross_equity, index=dates_out), pd.Series(net_equity, index=dates_out),
            trades, turnover, trade_returns)


def run_all() -> dict:
    import os
    cache_p, cache_v = "data/cache/_broad_price_panel.parquet", "data/cache/_broad_vol_panel.parquet"
    if os.path.exists(cache_p) and os.path.exists(cache_v):
        price_panel = pd.read_parquet(cache_p)
        vol_panel = pd.read_parquet(cache_v)
    else:
        price_panel, vol_panel = load_broad_panel()
        price_panel.to_parquet(cache_p)
        vol_panel.to_parquet(cache_v)
    n_syms = price_panel.shape[1]
    train_dates, holdout_dates = stats.train_holdout_split(price_panel.index, HOLDOUT_FRAC)
    results = {"universe_size_total_pool": n_syms, "train_span": [str(train_dates.min()), str(train_dates.max())],
               "holdout_span": [str(holdout_dates.min()), str(holdout_dates.max())]}
    for lb in LOOKBACKS:
        for allow_short in (True, False):
            gross, net, trades, turnover, trade_rets = backtest_pit_momentum(price_panel, vol_panel, lb, allow_short)
            tag = f"pit_momentum_{lb}d_{'ls' if allow_short else 'lo'}"

            net_is = net.loc[net.index.isin(train_dates) | (net.index <= train_dates.max())]
            net_ho_base = net.loc[net.index >= train_dates.max()]
            net_ho = net_ho_base / net_ho_base.iloc[0] * engine.CAPITAL_EUR if len(net_ho_base) else net_ho_base

            m_gross = engine.compute_metrics(gross, 365, trades, turnover)
            m_net_full = engine.compute_metrics(net, 365, trades, turnover)
            m_net_is = engine.compute_metrics(net_is, 365, trades, turnover)
            m_net_ho = engine.compute_metrics(net_ho, 365, trades, turnover) if len(net_ho) > 2 else {"error": "insufficient holdout"}

            tr_df = pd.DataFrame(trade_rets)
            is_rets = tr_df[tr_df["date"] <= train_dates.max()]["port_ret"].values if len(tr_df) else np.array([])
            ho_rets = tr_df[tr_df["date"] > train_dates.max()]["port_ret"].values if len(tr_df) else np.array([])
            p_is = stats.one_sided_pvalue(is_rets) if len(is_rets) else 1.0
            p_ho = stats.one_sided_pvalue(ho_rets) if len(ho_rets) else 1.0
            dsr = stats.deflated_sharpe_ratio(is_rets, n_trials=6) if len(is_rets) else {"error": "no_data"}

            stats.register_test(tag, "A1_pit_momentum", f"lookback={lb}d,short={allow_short}",
                                 "none (extra scrutiny)", trades,
                                 sharpe_is=m_net_is.get("sharpe_annualized"), p_is=p_is,
                                 sharpe_holdout=m_net_ho.get("sharpe_annualized"), p_holdout=p_ho,
                                 note=f"n_rebalances={len(tr_df)}")

            results[tag] = {"gross": m_gross, "net_full": m_net_full, "net_is": m_net_is,
                             "net_holdout": m_net_ho, "p_is": p_is, "p_holdout": p_ho, "dsr": dsr}
            net.to_frame("equity_eur").to_csv(f"results/{tag}_net_equity.csv")
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run_all(), indent=2, default=str))
