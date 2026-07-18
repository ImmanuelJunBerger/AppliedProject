"""Cost model + backtest primitives shared by every strategy.

Capital base: 1,000 EUR retail. All strategies must run their P&L through
`apply_costs` and report gross vs net — a strategy is not "profitable"
unless net survives.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CAPITAL_EUR = 1_000.0

# --- fees ---------------------------------------------------------------
TAKER_FEE_PERP = 0.0005     # 5 bps per side, perps (Binance/OKX/Hyperliquid-like)
TAKER_FEE_SPOT = 0.0010     # 10 bps per side, spot
MAKER_FEE_PERP = 0.0002     # 2 bps, used only when a strategy truly rests an order

# --- slippage: liquid majors cheap, alts scale up with size vs volume ---
SLIPPAGE_LIQUID_BPS = 0.0005          # BTC/ETH-class, 5 bps
SLIPPAGE_ALT_BASE_BPS = 0.0020        # 20 bps floor for a typical liquid alt
SLIPPAGE_ALT_MAX_BPS = 0.0100         # cap at 100 bps before we call it untradeable size
LIQUID_MAJORS = {"BTCUSDT", "ETHUSDT", "BTC", "ETH", "BTC-USDT-SWAP", "ETH-USDT-SWAP"}


def slippage_bps(symbol: str, order_notional_eur: float, avg_daily_quote_volume_eur: float | None) -> float:
    """Slippage estimate in bps, scaled by order size vs the token's own liquidity.

    Liquid majors get a flat 5bps. Everything else starts at a 20bps floor and
    scales up with participation rate (order size / daily volume), capped at
    100bps — beyond that the size is not realistically tradeable at 1k EUR scale
    anyway, but we still cap rather than let costs blow up to nonsense.
    """
    if symbol in LIQUID_MAJORS:
        return SLIPPAGE_LIQUID_BPS
    if not avg_daily_quote_volume_eur or avg_daily_quote_volume_eur <= 0:
        return SLIPPAGE_ALT_MAX_BPS
    participation = order_notional_eur / avg_daily_quote_volume_eur
    # 20bps floor, +100bps per 1% of daily volume consumed, capped
    bps = SLIPPAGE_ALT_BASE_BPS + participation * 100 * 0.01
    return float(min(bps, SLIPPAGE_ALT_MAX_BPS))


def trade_cost_eur(symbol: str, notional_eur: float, venue: str,
                    avg_daily_quote_volume_eur: float | None = None,
                    maker: bool = False) -> float:
    """Round-trip-agnostic single-fill cost in EUR (fee + slippage)."""
    if venue == "perp":
        fee = MAKER_FEE_PERP if maker else TAKER_FEE_PERP
    else:
        fee = TAKER_FEE_SPOT
    slip = slippage_bps(symbol, notional_eur, avg_daily_quote_volume_eur)
    return notional_eur * (fee + slip)


def apply_funding(position_notional_eur: float, funding_rate: float) -> float:
    """P&L impact (EUR) of holding `position_notional_eur` (signed, long +) through
    one funding interval at `funding_rate` (paid by longs to shorts when positive)."""
    return -position_notional_eur * funding_rate


# --- metrics --------------------------------------------------------------

def compute_metrics(equity: pd.Series, periods_per_year: int, trade_count: int,
                     turnover_eur: float = 0.0) -> dict:
    """equity: EUR equity curve indexed by time, starting at CAPITAL_EUR."""
    equity = equity.dropna()
    if len(equity) < 2:
        return {"error": "insufficient equity points"}
    rets = equity.pct_change().dropna()
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    ann_factor = periods_per_year
    mean_r = rets.mean()
    std_r = rets.std(ddof=1)
    sharpe = float(mean_r / std_r * np.sqrt(ann_factor)) if std_r > 0 else 0.0
    running_max = equity.cummax()
    dd = equity / running_max - 1
    max_dd = float(dd.min())
    win_rate = float((rets > 0).mean()) if len(rets) else np.nan
    return {
        "total_return_pct": round(total_return * 100, 2),
        "sharpe_annualized": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "win_rate_pct": round(win_rate * 100, 1) if not np.isnan(win_rate) else None,
        "n_periods": len(equity),
        "trade_count": trade_count,
        "turnover_eur": round(turnover_eur, 2),
        "net_profit_eur_on_1000": round(equity.iloc[-1] - equity.iloc[0], 2),
        "final_equity_eur": round(equity.iloc[-1], 2),
    }


def walk_forward_splits(index: pd.DatetimeIndex, train_days: int, test_days: int, step_days: int | None = None):
    """Yield (train_idx, test_idx) rolling windows. No look-ahead: test always
    strictly after train."""
    step_days = step_days or test_days
    dates = index.sort_values().unique()
    if len(dates) < train_days + test_days:
        return
    start = 0
    while True:
        train_end = start + train_days
        test_end = train_end + test_days
        if test_end > len(dates):
            break
        train_idx = dates[start:train_end]
        test_idx = dates[train_end:test_end]
        yield train_idx, test_idx
        start += step_days


def synthetic_ohlcv(symbol: str = "SYN", n: int = 500, seed: int = 7, drift: float = 0.0002,
                     vol: float = 0.02, start: str = "2024-01-01") -> pd.DataFrame:
    """Deterministic synthetic daily OHLCV for engine smoke-testing only.
    NEVER used for reported strategy results."""
    rng = np.random.default_rng(seed)
    ts = pd.date_range(start, periods=n, freq="D", tz="UTC")
    rets = rng.normal(drift, vol, n)
    close = 100 * np.cumprod(1 + rets)
    open_ = np.roll(close, 1)
    open_[0] = 100
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.002, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.002, n)))
    vol_ = rng.uniform(1e6, 5e6, n)
    df = pd.DataFrame({"timestamp": ts, "open": open_, "high": high, "low": low,
                        "close": close, "volume": vol_})
    df["symbol"] = symbol
    return df
