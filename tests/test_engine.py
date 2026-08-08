"""Section 6/10 tests: lookahead elimination and null-strategy cost calibration.

Run:  python -m tests.test_engine
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import backtest as B  # noqa: E402
from src import costs as C  # noqa: E402
from src import strategy as ST  # noqa: E402


def _synthetic_panel(n=4000, seed=0):
    """Deterministic synthetic OHLCV for engine unit tests only. Never used for results."""
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    ret = rng.normal(0, 0.004, n)
    close = 100 * np.cumprod(1 + ret)
    open_ = np.r_[100.0, close[:-1]]
    hi = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.001, n)))
    lo = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.001, n)))
    vol = rng.lognormal(10, 0.5, n)
    df = pd.DataFrame({"timestamp": ts, "open": open_, "high": hi, "low": lo,
                       "close": close, "volume": vol, "quote_volume": vol * close})
    return df


# ---------------------------------------------------------------------------

def test_no_lookahead_signal():
    """Truncating the future must not change a past signal value."""
    df = _synthetic_panel()
    p = ST.SignalParams()
    sig = ST.build_signal(df, p)
    res = B.assert_no_lookahead({"SYN": df}, {"SYN": sig})
    print(f"[assert_no_lookahead] passed={res['passed']} problems={res['n_problems']}")
    assert res["passed"], f"LOOKAHEAD DETECTED: {res['problems']}"
    return res


def test_fill_is_next_bar_open():
    """A signal on bar t must produce an entry price equal to bar t+1's OPEN."""
    df = _synthetic_panel(n=2000, seed=3)
    sig = pd.Series(0.0, index=df.index)
    trigger = 500
    sig.iloc[trigger] = 1.0
    cfg = B.BTConfig(max_concurrent=1, max_holding_bars=5)
    bt = B.Backtester({"SYN": df}, {"SYN": pd.DataFrame()}, cfg)
    out = bt.run({"SYN": sig})
    tr = out["trades"]
    assert len(tr) == 1, f"expected exactly 1 trade, got {len(tr)}"
    expected_price = float(df["open"].iloc[trigger + 1])
    got = float(tr.iloc[0]["entry_price"])
    print(f"[next_bar_open_fill] expected={expected_price:.6f} got={got:.6f}")
    assert np.isclose(got, expected_price), "FILL NOT AT NEXT BAR OPEN"
    assert tr.iloc[0]["entry_time"] == df["timestamp"].iloc[trigger + 1]
    return True


def test_stop_before_target_when_both_touched():
    """If a bar touches stop and target, the STOP must be assumed to fill (worse)."""
    n = 60
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    hi = np.full(n, 100.5)
    lo = np.full(n, 99.5)
    # bar 12: huge range touching both stop and target
    hi[22], lo[22] = 130.0, 70.0
    df = pd.DataFrame({"timestamp": ts, "open": open_, "high": hi, "low": lo, "close": close,
                       "volume": np.full(n, 1e6), "quote_volume": np.full(n, 1e8)})
    sig = pd.Series(0.0, index=df.index)
    sig.iloc[20] = 1.0
    cfg = B.BTConfig(max_concurrent=1, max_holding_bars=30, atr_multiple_stop=2.0,
                     target_take_profit_atr=3.0)
    bt = B.Backtester({"SYN": df}, {"SYN": pd.DataFrame()}, cfg)
    out = bt.run({"SYN": sig})
    tr = out["trades"]
    assert len(tr) == 1
    reason = tr.iloc[0]["exit_reason"]
    print(f"[stop_precedence] exit_reason={reason} pnl={tr.iloc[0]['net_pnl']:.2f}")
    assert reason in ("stop", "stop_gap"), f"expected stop to win precedence, got {reason}"
    return True


def test_gap_through_stop_fills_at_open():
    """If the bar OPENS beyond the stop, fill at the open (not the stop price)."""
    n = 60
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    close = np.full(n, 100.0); open_ = np.full(n, 100.0)
    hi = np.full(n, 100.5); lo = np.full(n, 99.5)
    # bar 12 gaps far below: open well beyond any plausible stop
    open_[22] = 50.0; hi[22] = 51.0; lo[22] = 49.0; close[22] = 50.0
    df = pd.DataFrame({"timestamp": ts, "open": open_, "high": hi, "low": lo, "close": close,
                       "volume": np.full(n, 1e6), "quote_volume": np.full(n, 1e8)})
    sig = pd.Series(0.0, index=df.index); sig.iloc[20] = 1.0
    cfg = B.BTConfig(max_concurrent=1, max_holding_bars=30)
    bt = B.Backtester({"SYN": df}, {"SYN": pd.DataFrame()}, cfg)
    out = bt.run({"SYN": sig})
    tr = out["trades"]
    assert len(tr) == 1
    assert tr.iloc[0]["exit_reason"] == "stop_gap", tr.iloc[0]["exit_reason"]
    assert np.isclose(float(tr.iloc[0]["exit_price"]), 50.0), tr.iloc[0]["exit_price"]
    print(f"[gap_risk] filled at open={tr.iloc[0]['exit_price']} (not the stop) OK")
    return True


def test_null_strategy_loses_by_cost():
    """Random entries must lose approximately the modelled cost. This validates
    that the cost plumbing is actually wired into P&L rather than decorative."""
    df = _synthetic_panel(n=8000, seed=11)
    cfg = B.BTConfig(max_concurrent=1, max_holding_bars=12)
    bt = B.Backtester({"SYN": df}, {"SYN": pd.DataFrame()}, cfg)
    sig = ST.random_signal(df, n_signals=400, seed=5)
    out = bt.run({"SYN": sig})
    tr = out["trades"]
    total_cost = tr["entry_cost"].sum() + tr["exit_cost"].sum() + tr["funding"].sum()
    gross = tr["gross_pnl"].sum()
    net = tr["net_pnl"].sum()
    print(f"[null_strategy] n={len(tr)} gross={gross:,.0f} cost={total_cost:,.0f} net={net:,.0f}")
    # net must equal gross minus costs (accounting identity), within float error
    assert np.isclose(net, gross - total_cost, rtol=1e-6), "cost accounting identity broken"
    # and on a driftless random series, net should be negative by roughly the cost
    assert net < 0, "null strategy did not lose money -- costs are not binding"
    return {"n_trades": int(len(tr)), "gross": float(gross), "cost": float(total_cost),
            "net": float(net)}


def test_cost_model_monotonic():
    """Pessimistic cost level must cost strictly more than optimistic."""
    vals = []
    for lvl, mult in C.COST_LEVELS.items():
        cfg = C.CostConfig(multiplier=mult)
        c = C.one_way_cost_bps(10_000, 5e7, 1.5, 100.0, 1.2, cfg)
        vals.append((lvl, c["total_bps"]))
    print(f"[cost_levels] {vals}")
    assert vals[0][1] < vals[1][1] < vals[2][1], vals
    return dict(vals)


def test_risk_limits_engage():
    """Kill switch must halt trading on a catastrophic path."""
    n = 3000
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    close = 100 * np.exp(np.linspace(0, -3, n))  # relentless downtrend
    open_ = np.r_[100.0, close[:-1]]
    df = pd.DataFrame({"timestamp": ts, "open": open_, "high": np.maximum(open_, close) * 1.001,
                       "low": np.minimum(open_, close) * 0.999, "close": close,
                       "volume": np.full(n, 1e6), "quote_volume": np.full(n, 1e8)})
    sig = pd.Series(0.0, index=df.index)
    sig.iloc[::10] = 1.0   # keep buying the falling knife
    cfg = B.BTConfig(max_concurrent=1, max_holding_bars=24, kill_switch_dd=0.20)
    bt = B.Backtester({"SYN": df}, {"SYN": pd.DataFrame()}, cfg)
    out = bt.run({"SYN": sig})
    print(f"[risk_limits] halted={out['halted']} final_equity={out['final_equity']:,.0f}")
    assert out["halted"], "kill switch never engaged on a -95% path"
    return True


if __name__ == "__main__":
    import json
    results = {}
    results["no_lookahead"] = test_no_lookahead_signal()
    results["next_bar_open_fill"] = test_fill_is_next_bar_open()
    results["stop_precedence"] = test_stop_before_target_when_both_touched()
    results["gap_risk"] = test_gap_through_stop_fills_at_open()
    results["cost_levels"] = test_cost_model_monotonic()
    results["null_strategy"] = test_null_strategy_loses_by_cost()
    results["risk_limits"] = test_risk_limits_engage()
    print("\nALL ENGINE TESTS PASSED")
    Path("results_v6").mkdir(exist_ok=True)
    json.dump(results, open("results_v6/engine_tests.json", "w"), indent=2, default=str)
