"""Track B: structural edge hunt. One function per pre-registered hypothesis
(see HYPOTHESES.md for the exact rules committed before this code was run).
Every test registers itself via `stats.register_test` so N_TESTS is real.
"""
from __future__ import annotations

import time
import numpy as np
import pandas as pd

from . import data, engine, stats

CAPITAL = engine.CAPITAL_EUR


# ---------------------------------------------------------------------------
# B1: token unlock / vesting cliffs -- DATA CHECK
# ---------------------------------------------------------------------------

def b1_check_data() -> dict:
    """Pre-registered: skip cleanly if no free unlock calendar exists.
    DeFiLlama's /emissions endpoints returned HTTP 402 (paid plan required)
    when probed; token.unlocks.app has no documented free JSON API (301
    redirect to an app shell). No dates guessed."""
    checks = {}
    for name, url in {"defillama_emissions": "https://api.llama.fi/emissionsList",
                       "defillama_emission_btc": "https://api.llama.fi/emission/bitcoin"}.items():
        try:
            r = data.SESSION.get(url, timeout=10)
            checks[name] = r.status_code
        except Exception as e:  # noqa: BLE001
            checks[name] = f"ERROR:{e}"
    result = {"status": "SKIPPED — insufficient data", "probe_results": checks,
              "reason": "No free (non-paid) unlock/emissions calendar API found among reachable sources."}
    stats.register_test("B1_unlock_cliffs", "B1_unlock_cliffs", "n/a", "forced_flow",
                         0, note="SKIPPED: no free unlock calendar data source available")
    return result


# ---------------------------------------------------------------------------
# B2: cross-venue funding dispersion (HL vs OKX)
# ---------------------------------------------------------------------------

def b2_cross_venue_dispersion(lookback_days: int = 180) -> dict:
    coins = {"BTC": "BTC-USDT-SWAP", "ETH": "ETH-USDT-SWAP", "SOL": "SOL-USDT-SWAP"}
    start_ms = int((time.time() - lookback_days * 86400) * 1000)
    out = {}
    for coin, okx_inst in coins.items():
        hl = data.fetch_hl_funding_history(coin, start_ms)
        okx = data.fetch_okx_funding_history(okx_inst)
        if hl.empty or okx.empty:
            out[coin] = {"error": "missing funding data"}
            continue
        hl_s = hl.set_index("timestamp")["fundingRate"]
        okx_s = okx.set_index("timestamp")["fundingRate"]
        # aggregate HL hourly into OKX's 8h buckets (sum of hourly rates in each window)
        okx_times = okx_s.index.sort_values()
        disp_rows = []
        for t in okx_times:
            window = hl_s[(hl_s.index > t - pd.Timedelta(hours=8)) & (hl_s.index <= t)]
            if len(window) < 6:  # need most of the 8 hourly prints
                continue
            hl_8h = window.sum()
            okx_8h = okx_s.loc[t]
            disp_rows.append({"timestamp": t, "hl_8h": hl_8h, "okx_8h": okx_8h, "dispersion": hl_8h - okx_8h})
        if len(disp_rows) < 20:
            out[coin] = {"error": "insufficient overlapping funding data", "n_overlap": len(disp_rows)}
            continue
        disp_df = pd.DataFrame(disp_rows).set_index("timestamp")
        disp_df.to_csv(f"results/b2_dispersion_{coin}.csv")

        for transfer_buffer_bps in (0, 10):
            entry_th = 2 * engine.TAKER_FEE_PERP + transfer_buffer_bps / 10000.0  # 2 legs entry, symmetric exit assumed amortized via hysteresis
            exit_th = entry_th * 0.2
            sig = disp_df["dispersion"].rolling(3).mean()
            state = 0
            positions = []
            for i in range(len(disp_df)):
                s = sig.iloc[i]
                if pd.isna(s):
                    positions.append(state)
                    continue
                if state == 0 and abs(s) > entry_th:
                    state = 1 if s > 0 else -1
                elif state != 0 and abs(s) < exit_th:
                    state = 0
                positions.append(state)
            disp_df["position"] = positions
            applied_pos = pd.Series(positions, index=disp_df.index).shift(1).fillna(0)

            equity = [CAPITAL]
            trades = 0
            rets = []
            for i in range(1, len(disp_df)):
                pos = applied_pos.iloc[i]
                pnl = pos * disp_df["dispersion"].iloc[i] * CAPITAL if pos != 0 else 0.0
                e = equity[-1] + pnl
                if applied_pos.iloc[i] != applied_pos.iloc[i - 1]:
                    cost = 2 * engine.TAKER_FEE_PERP * CAPITAL + transfer_buffer_bps / 10000.0 * CAPITAL
                    e -= cost
                    trades += 1
                rets.append(e / equity[-1] - 1 if equity[-1] != 0 else 0.0)
                equity.append(e)
            eq = pd.Series(equity, index=disp_df.index)
            m = engine.compute_metrics(eq, 365 * 3, trade_count=trades)
            p = stats.one_sided_pvalue(np.array(rets)) if rets else 1.0
            key = f"{coin}_buffer{transfer_buffer_bps}bps"
            out[key] = m
            out[key]["p_value"] = round(p, 5)
            stats.register_test(f"B2_dispersion_{key}", "B2_cross_venue_dispersion",
                                 f"coin={coin},buffer={transfer_buffer_bps}bps", "too_small_to_matter",
                                 trades, sharpe_is=m.get("sharpe_annualized"), p_is=p)
    return out


# ---------------------------------------------------------------------------
# B3: newly-listed perp funding richness
# ---------------------------------------------------------------------------

def b3_new_listing_funding(n_coins_sample: int = 177) -> dict:
    meta = data.fetch_hl_meta()
    coins = [u["name"] for u in meta["universe"] if not u.get("isDelisted")]
    coins_sample = coins[:n_coins_sample]  # universe order, not volume/perf sorted -- avoids cherry-picking
    ages = {}
    for c in coins_sample:
        try:
            js = data._post(f"{data.HL}/info", {"type": "fundingHistory", "coin": c, "startTime": 1672531200000})  # 2023-01-01
            if js:
                first_ts = js[0]["time"]
                ages[c] = (time.time() * 1000 - first_ts) / 86400000.0
        except Exception:
            continue
        time.sleep(0.05)

    age_series = pd.Series(ages)
    buckets = {"0-30d": age_series[age_series <= 30].index.tolist(),
               "30-90d": age_series[(age_series > 30) & (age_series <= 90)].index.tolist(),
               "90d+": age_series[age_series > 90].index.tolist()}
    out = {"n_coins_probed": len(ages), "bucket_counts": {k: len(v) for k, v in buckets.items()}}

    start_ms = int((time.time() - 180 * 86400) * 1000)
    for bucket, coin_list in buckets.items():
        if not coin_list:
            out[bucket] = {"error": "empty bucket"}
            continue
        sample = coin_list[:5]  # fixed rule: first 5 in universe order within bucket, not cherry-picked
        mean_abs_funding = []
        for c in sample:
            f = data.fetch_hl_funding_history(c, start_ms)
            if not f.empty:
                mean_abs_funding.append(float(f["fundingRate"].abs().mean()) * 24 * 365)  # annualized
        out[bucket] = {"sample_coins": sample, "mean_abs_funding_ann_pct": round(100 * np.mean(mean_abs_funding), 2) if mean_abs_funding else None}
        stats.register_test(f"B3_meanfunding_{bucket}", "B3_new_listing_funding", f"bucket={bucket}",
                             "too_small_too_new", len(sample), note="descriptive pre-screen, not a scored finding")

    # backtested carry Sharpe for the youngest vs oldest bucket samples (the real test)
    from .strategy_funding_carry import _run_carry, ENTRY_TH_1H, EXIT_TH_1H
    for bucket in ("0-30d", "90d+"):
        sample = out.get(bucket, {}).get("sample_coins", [])
        for c in sample[:3]:
            f = data.fetch_hl_funding_history(c, start_ms)
            if len(f) < 48:
                continue
            fs = f.set_index("timestamp")["fundingRate"]
            eq, trades, turnover = _run_carry(fs, periods_per_year=365 * 24, k_lookback=24,
                                               entry_th=ENTRY_TH_1H, exit_th=EXIT_TH_1H,
                                               symbol_for_cost=c, adv_eur=None)
            m = engine.compute_metrics(eq, 365 * 24, trades, turnover)
            rets = eq.pct_change().dropna().values
            p = stats.one_sided_pvalue(rets) if len(rets) else 1.0
            stats.register_test(f"B3_carry_{bucket}_{c}", "B3_new_listing_funding", f"bucket={bucket},coin={c}",
                                 "too_small_too_new", trades, sharpe_is=m.get("sharpe_annualized"), p_is=p)
            out[f"carry_{bucket}_{c}"] = m
    return out


# ---------------------------------------------------------------------------
# B4: post-liquidation-cascade reversion (proxy via extreme range+volume)
# ---------------------------------------------------------------------------

def b4_cascade_reversion(price_panel: pd.DataFrame, vol_panel: pd.DataFrame) -> dict:
    daily_rets = price_panel.pct_change()
    daily_range = (price_panel.rolling(2).apply(lambda x: abs(x[1] - x[0]) / x[0], raw=True))
    trailing_vol = daily_rets.rolling(30).std()
    trailing_vol_avg_volume = vol_panel.rolling(30).mean()

    out = {}
    for holding in (1, 3):
        for direction_filter in ("down_only", "up_only", "both"):
            trade_returns = []
            for sym in price_panel.columns:
                r = daily_rets[sym]
                vol_z = (daily_range[sym] / trailing_vol[sym].replace(0, np.nan))
                vol_spike = vol_panel[sym] > 3 * trailing_vol_avg_volume[sym]
                cascade = (vol_z > 3) & vol_spike
                cascade_days = cascade[cascade].index
                for d in cascade_days:
                    loc = price_panel.index.get_indexer([d])[0]
                    if loc < 0 or loc + holding >= len(price_panel.index):
                        continue
                    was_down = r.loc[d] < 0
                    if direction_filter == "down_only" and not was_down:
                        continue
                    if direction_filter == "up_only" and was_down:
                        continue
                    entry_px = price_panel[sym].iloc[loc]
                    exit_px = price_panel[sym].iloc[loc + holding]
                    if pd.isna(entry_px) or pd.isna(exit_px):
                        continue
                    raw_ret = (exit_px / entry_px - 1)
                    signed_ret = -raw_ret if was_down else raw_ret  # reversion bet: fade the cascade
                    cost = 2 * (engine.TAKER_FEE_SPOT + 0.002)  # rough 2-sided cost incl slippage buffer
                    trade_returns.append(signed_ret - cost)
            key = f"hold{holding}d_{direction_filter}"
            if len(trade_returns) < 5:
                out[key] = {"error": "too few cascade events", "n": len(trade_returns)}
                continue
            arr = np.array(trade_returns)
            sharpe = float(arr.mean() / arr.std(ddof=1) * np.sqrt(252 / holding)) if arr.std(ddof=1) > 0 else 0.0
            p = stats.one_sided_pvalue(arr)
            out[key] = {"n_trades": len(arr), "mean_ret": round(float(arr.mean()), 5),
                        "sharpe_rough": round(sharpe, 2), "p_value": round(p, 5),
                        "win_rate_pct": round(100 * float((arr > 0).mean()), 1)}
            stats.register_test(f"B4_cascade_{key}", "B4_cascade_reversion", key, "forced_flow",
                                 len(arr), sharpe_is=sharpe, p_is=p)
    return out


# ---------------------------------------------------------------------------
# B5: open interest / price divergence
# ---------------------------------------------------------------------------

def b5_oi_price_divergence() -> dict:
    insts = {"BTC": "BTC-USDT-SWAP", "ETH": "ETH-USDT-SWAP", "SOL": "SOL-USDT-SWAP"}
    check = data.SESSION.get(f"{data.OKX}/api/v5/rubik/stat/contracts/open-interest-volume",
                              params={"ccy": "BTC", "period": "1D"}, timeout=10)
    if check.status_code != 200 or not check.json().get("data"):
        stats.register_test("B5_oi_divergence", "B5_oi_price_divergence", "n/a", "forced_flow_adjacent",
                             0, note="SKIPPED: OKX OI endpoint unreachable or empty")
        return {"status": "SKIPPED — insufficient data", "probe_status": check.status_code}

    out = {}
    for coin, inst in insts.items():
        js = data.SESSION.get(f"{data.OKX}/api/v5/rubik/stat/contracts/open-interest-volume",
                               params={"ccy": coin, "period": "1D"}, timeout=15).json()
        rows = js.get("data", [])
        if not rows:
            out[coin] = {"error": "no data"}
            continue
        oi_df = pd.DataFrame(rows, columns=["ts", "oi_ccy", "vol_ccy"])
        oi_df["timestamp"] = pd.to_datetime(oi_df["ts"].astype(float), unit="ms", utc=True)
        oi_df["oi_ccy"] = oi_df["oi_ccy"].astype(float)
        oi_df = oi_df.sort_values("timestamp").set_index("timestamp")
        px = data.fetch_okx_candles(inst, "1D", 300)
        if px.empty:
            out[coin] = {"error": "no price data"}
            continue
        px_s = px.set_index("timestamp")["close"]
        merged = pd.concat([oi_df["oi_ccy"], px_s], axis=1, join="inner").dropna()
        merged.columns = ["oi", "price"]
        merged.to_csv(f"results/b5_oi_{coin}.csv")
        if len(merged) < 30:
            out[coin] = {"error": "insufficient overlap", "n": len(merged)}
            continue
        oi_chg = merged["oi"].pct_change()
        px_chg = merged["price"].pct_change()
        for sign_convention in ("A_short_cover", "B_squeeze_continuation"):
            for holding in (1, 3):
                sig_up = (oi_chg > 0) & (px_chg < 0) if sign_convention == "A_short_cover" else (oi_chg < 0) & (px_chg > 0)
                sig_dates = merged.index[sig_up.shift(1).fillna(False)]
                rets = []
                for d in sig_dates:
                    loc = merged.index.get_indexer([d])[0]
                    if loc + holding >= len(merged):
                        continue
                    entry, exit_ = merged["price"].iloc[loc], merged["price"].iloc[loc + holding]
                    rets.append(entry and (exit_ / entry - 1) - 2 * engine.TAKER_FEE_PERP)
                key = f"{coin}_{sign_convention}_hold{holding}d"
                if len(rets) < 5:
                    out[key] = {"error": "too few signals", "n": len(rets)}
                    continue
                arr = np.array(rets)
                sharpe = float(arr.mean() / arr.std(ddof=1) * np.sqrt(252 / holding)) if arr.std(ddof=1) > 0 else 0.0
                p = stats.one_sided_pvalue(arr)
                out[key] = {"n": len(arr), "sharpe_rough": round(sharpe, 2), "p_value": round(p, 5)}
                stats.register_test(f"B5_oi_{key}", "B5_oi_price_divergence", key, "forced_flow_adjacent",
                                     len(arr), sharpe_is=sharpe, p_is=p)
    return out


# ---------------------------------------------------------------------------
# B6: funding-settlement microstructure
# ---------------------------------------------------------------------------

def b6_settlement_microstructure() -> dict:
    out = {}
    for venue, inst in (("OKX", "BTC-USDT-SWAP"), ("OKX_ETH", "ETH-USDT-SWAP")):
        candles = data.fetch_okx_history_candles(inst, "1H", target_days=400)
        if candles.empty:
            out[venue] = {"error": "no data"}
            continue
        c = candles.set_index("timestamp").sort_index()
        c["ret"] = c["close"].pct_change()
        c["hour"] = c.index.hour
        settlement_hours = {0, 8, 16}
        pre_settle = c[c["hour"].isin({(h - 1) % 24 for h in settlement_hours})]["ret"].dropna()
        post_settle = c[c["hour"].isin(settlement_hours)]["ret"].dropna()
        other = c[~c["hour"].isin(settlement_hours | {(h - 1) % 24 for h in settlement_hours})]["ret"].dropna()
        for label, series in (("pre_settlement_hour", pre_settle), ("post_settlement_hour", post_settle)):
            cost = 2 * engine.TAKER_FEE_PERP
            net_series = series - cost
            p = stats.one_sided_pvalue(net_series.values)
            sharpe = float(net_series.mean() / net_series.std(ddof=1) * np.sqrt(365 * 24)) if net_series.std(ddof=1) > 0 else 0.0
            out[f"{venue}_{label}"] = {"n": len(series), "mean_ret_gross": round(float(series.mean()), 6),
                                        "mean_ret_net_of_2x_taker": round(float(net_series.mean()), 6),
                                        "sharpe_net_annualized": round(sharpe, 2), "p_value_net": round(p, 5),
                                        "control_other_hours_mean": round(float(other.mean()), 6)}
            stats.register_test(f"B6_{venue}_{label}", "B6_settlement_microstructure", f"{venue}_{label}",
                                 "calendar_predictable", len(series), sharpe_is=sharpe, p_is=p)
    return out


# ---------------------------------------------------------------------------
# B7: hour-of-day / day-of-week seasonality
# ---------------------------------------------------------------------------

def b7_seasonality() -> dict:
    out = {}
    n_bucket_tests = 0
    for coin, inst in (("BTC", "BTC-USDT-SWAP"), ("ETH", "ETH-USDT-SWAP")):
        candles = data.fetch_okx_history_candles(inst, "1H", target_days=400)
        if candles.empty:
            out[coin] = {"error": "no data"}
            continue
        c = candles.set_index("timestamp").sort_index()
        c["ret"] = c["close"].pct_change()
        n = len(c)
        split = int(n * 0.7)
        is_c, ho_c = c.iloc[:split], c.iloc[split:]

        for axis, col_fn in (("hour", lambda idx: idx.hour), ("dow", lambda idx: idx.dayofweek)):
            is_c = is_c.copy()
            is_c["bucket"] = col_fn(is_c.index)
            bucket_means = is_c.groupby("bucket")["ret"].mean()
            n_buckets = len(bucket_means)
            n_bucket_tests += n_buckets
            best_bucket = bucket_means.idxmax()
            best_mean_is = bucket_means.max()

            ho_c2 = ho_c.copy()
            ho_c2["bucket"] = col_fn(ho_c2.index)
            ho_vals = ho_c2[ho_c2["bucket"] == best_bucket]["ret"].dropna()
            cost = 2 * engine.TAKER_FEE_PERP
            ho_net = ho_vals - cost
            p_ho = stats.one_sided_pvalue(ho_net.values) if len(ho_net) >= 5 else 1.0
            sharpe_ho = float(ho_net.mean() / ho_net.std(ddof=1) * np.sqrt(365 * 24)) if len(ho_net) > 1 and ho_net.std(ddof=1) > 0 else 0.0
            key = f"{coin}_{axis}_best_bucket{best_bucket}"
            out[key] = {"best_bucket_is": int(best_bucket), "mean_ret_is": round(float(best_mean_is), 6),
                        "n_buckets_tested_this_axis": n_buckets, "holdout_n": len(ho_net),
                        "holdout_sharpe_net": round(sharpe_ho, 2), "holdout_p_net": round(p_ho, 5)}
            stats.register_test(f"B7_{key}", "B7_seasonality", key, "none (highest false-positive risk)",
                                 len(ho_net), sharpe_holdout=sharpe_ho, p_holdout=p_ho,
                                 note=f"selected from {n_buckets} in-sample buckets")
    out["_total_bucket_comparisons_counted_in_N_TESTS"] = n_bucket_tests
    # register the raw bucket-level comparisons too (pre-registered: all 62 count)
    for i in range(n_bucket_tests):
        stats.register_test(f"B7_bucket_scan_{i}", "B7_seasonality_bucket_scan", f"bucket_{i}",
                             "none (highest false-positive risk)", 0, note="in-sample bucket mean, not individually holdout-tested")
    return out


# ---------------------------------------------------------------------------
# B8: exchange listing announcement drift -- DATA CHECK
# ---------------------------------------------------------------------------

def b8_check_data() -> dict:
    stats.register_test("B8_listing_announcements", "B8_listing_announcements", "n/a", "forced_flow_calendar",
                         0, note="SKIPPED: no free historical listing-announcement timestamp source among reachable APIs")
    return {"status": "SKIPPED — insufficient data",
            "reason": "Binance-vision/OKX/Hyperliquid/DexScreener are market-data APIs, not news/announcement feeds; no free announcement-timestamp source identified."}


# ---------------------------------------------------------------------------
# B9: stablecoin micro-depeg reversion
# ---------------------------------------------------------------------------

def b9_stablecoin_depeg() -> dict:
    pairs = ["USDCUSDT", "FDUSDUSDT", "TUSDUSDT"]
    out = {}
    for sym in pairs:
        try:
            df = data.fetch_binance_spot_klines(sym, "1h", 1000)
        except Exception as e:  # noqa: BLE001
            out[sym] = {"error": f"fetch_failed:{e}"}
            continue
        if df.empty:
            out[sym] = {"error": "no data"}
            continue
        c = df.set_index("timestamp")["close"]
        deviation = c - 1.0
        for buffer_bps in (0, 2):
            cost = 2 * engine.TAKER_FEE_SPOT + buffer_bps / 10000.0
            triggers = deviation[deviation.abs() > cost]
            if len(triggers) < 5:
                key = f"{sym}_buffer{buffer_bps}bps"
                out[key] = {"n_trigger_events": len(triggers), "verdict": "too few/no events clearing cost threshold"}
                stats.register_test(f"B9_{key}", "B9_stablecoin_depeg", key, "too_small_to_matter",
                                     len(triggers), note="insufficient trigger events to backtest")
                continue
            # non-overlapping trades only: can't open a new position while one
            # is already held (24h hold), otherwise 345 hourly triggers on a
            # near-constant deviation series produce near-duplicate "trades"
            # that collapse the return variance and blow up the Sharpe estimate
            rets = []
            trigger_list = list(triggers.index)
            i = 0
            while i < len(trigger_list):
                t = trigger_list[i]
                loc = c.index.get_indexer([t])[0]
                if loc + 24 >= len(c):
                    i += 1
                    continue
                entry = c.iloc[loc]
                exit_ = c.iloc[min(loc + 24, len(c) - 1)]
                signed_ret = -(exit_ - entry) if entry > 1 else (exit_ - entry)
                rets.append(signed_ret - cost)
                # skip any further triggers inside this trade's 24h hold window
                exit_time = c.index[min(loc + 24, len(c) - 1)]
                i += 1
                while i < len(trigger_list) and trigger_list[i] <= exit_time:
                    i += 1
            key = f"{sym}_buffer{buffer_bps}bps"
            if len(rets) < 5:
                out[key] = {"n_trigger_events": len(triggers), "n_nonoverlapping_trades": len(rets), "verdict": "too few non-overlapping trades"}
                stats.register_test(f"B9_{key}", "B9_stablecoin_depeg", key, "too_small_to_matter",
                                     len(rets), note="too few non-overlapping trades")
                continue
            arr = np.array(rets)
            # trades are now non-overlapping but still not evenly spaced in time;
            # report mean/win-rate/p-value as the primary evidence, and a rough
            # per-trade Sharpe (NOT annualized -- with irregular 24h-hold trades
            # an annualization factor is not well-defined) as a secondary stat.
            sharpe_per_trade = float(arr.mean() / arr.std(ddof=1)) if arr.std(ddof=1) > 0 else 0.0
            p = stats.one_sided_pvalue(arr)
            out[key] = {"n_trigger_events": len(triggers), "n_nonoverlapping_trades": len(arr),
                        "mean_ret_per_trade": round(float(arr.mean()), 6),
                        "win_rate_pct": round(100 * float((arr > 0).mean()), 1),
                        "sharpe_per_trade_not_annualized": round(sharpe_per_trade, 3), "p_value": round(p, 5)}
            stats.register_test(f"B9_{key}", "B9_stablecoin_depeg", key, "too_small_to_matter",
                                 len(arr), sharpe_is=sharpe_per_trade, p_is=p)
    return out


if __name__ == "__main__":
    import json
    results = {
        "B1": b1_check_data(),
        "B8": b8_check_data(),
        "B2": b2_cross_venue_dispersion(),
        "B9": b9_stablecoin_depeg(),
        "B6": b6_settlement_microstructure(),
        "B7": b7_seasonality(),
    }
    print(json.dumps(results, indent=2, default=str))
