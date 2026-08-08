"""Cost model for 1h crypto perp trading. Independently testable (Section 3).

Every constant is either a venue-published figure or an explicitly-labelled
ASSUMPTION. Nothing here is tuned to make results look better.

Components, charged PER SIDE unless stated:
  taker fee      4.5 bps   (spec default; OKX/Binance-class retail taker)
  maker fee      1.5 bps   (positive cost, not a rebate -- we do not assume the venue pays us)
  half-spread    estimated per-bar from Corwin-Schultz high/low estimator, floor 1.0 bp
  slippage       k * (order_notional / bar_quote_volume)^0.5 * (ATR/price) * 1e4, floor 2.0 bps
  funding        REAL historical funding charged/credited at each 00/08/16 UTC settlement
                 for any open position. Never an average.

ON CALIBRATING k: the spec says "calibrate k". That cannot be honestly done here --
calibration requires realized fill-vs-arrival-price data, which we do not have and
cannot obtain from public OHLCV. k = 1.0 is used as the base case, which corresponds to
"consuming 100% of a bar's volume costs about one ATR of slippage" -- a standard
square-root market-impact parameterisation. It is an ASSUMPTION, not a calibration, and
`slippage_k_sensitivity()` reports what happens at k = 0.5 / 1.0 / 2.0 / 4.0.
At the order sizes in this study (<= a few thousand USD vs. multi-million-dollar hourly
bar volume) the participation term is tiny and the 2bp floor binds almost everywhere,
so results are near-insensitive to k -- which is itself reported rather than assumed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TAKER_FEE_BPS = 4.5
MAKER_FEE_BPS = 1.5
HALF_SPREAD_FLOOR_BPS = 1.0
SLIPPAGE_FLOOR_BPS = 2.0
SLIPPAGE_K = 1.0  # ASSUMPTION, not calibrated -- see module docstring

COST_LEVELS = {"optimistic": 1.0, "base": 1.5, "pessimistic": 2.5}


@dataclass
class CostConfig:
    taker_fee_bps: float = TAKER_FEE_BPS
    maker_fee_bps: float = MAKER_FEE_BPS
    half_spread_floor_bps: float = HALF_SPREAD_FLOOR_BPS
    slippage_floor_bps: float = SLIPPAGE_FLOOR_BPS
    slippage_k: float = SLIPPAGE_K
    multiplier: float = 1.0            # 1.0 optimistic / 1.5 base / 2.5 pessimistic
    use_maker: bool = False            # this strategy crosses the spread; taker by default
    extra: dict = field(default_factory=dict)

    @property
    def fee_bps(self) -> float:
        return self.maker_fee_bps if self.use_maker else self.taker_fee_bps


# ---------------------------------------------------------------------------
# Spread estimation
# ---------------------------------------------------------------------------

# --- Liquidity-tiered half-spread (PRIMARY spread model) ---------------------
# WHY NOT CORWIN-SCHULTZ AS PRIMARY: CS (2012) is calibrated for DAILY EQUITY bars,
# where the high-low range is dominated by bid-ask bounce. On 1h crypto perp bars the
# range is dominated by genuine volatility, so CS massively overestimates. Measured on
# this dataset, CS returns a MEDIAN half-spread of 5.0 bps on BTC perp and 7.2 bps on
# ETH perp; the true quoted half-spread on those instruments is on the order of
# 0.5 bp. Using CS as the primary model would have inflated round-trip costs ~4-5x and
# produced a REJECT verdict driven by a measurement artifact rather than by the
# strategy. That would be just as much a failure of this exercise as an inflated PASS.
#
# PRIMARY model: a half-spread assumption tiered on the instrument's own median hourly
# quote volume. These are ASSUMPTIONS informed by typical quoted depth on OKX-class
# perp books, not exchange-published figures.
# CS is retained and reported as an explicit PESSIMISTIC SENSITIVITY, so the report can
# state whether the verdict depends on the spread assumption at all.
SPREAD_TIERS_BPS = [
    (1e8, 0.5),    # >= $100M median hourly quote volume (BTC, ETH)  -> 0.5 bp half-spread
    (2e7, 1.0),    # >= $20M   (SOL, XRP, DOGE-class)                -> 1.0 bp
    (5e6, 2.0),    # >= $5M                                          -> 2.0 bp
    (0.0, 4.0),    # thinner                                         -> 4.0 bp
]


def tiered_half_spread_bps(median_quote_volume: float) -> float:
    for threshold, bps in SPREAD_TIERS_BPS:
        if median_quote_volume >= threshold:
            return bps
    return SPREAD_TIERS_BPS[-1][1]


def corwin_schultz_half_spread_bps(high: pd.Series, low: pd.Series,
                                    floor_bps: float = HALF_SPREAD_FLOOR_BPS) -> pd.Series:
    """Corwin & Schultz (2012) high-low spread estimator, returned as HALF-spread in bps.

    RETAINED AS A PESSIMISTIC SENSITIVITY ONLY -- see SPREAD_TIERS_BPS above for why it
    is not the primary model on 1h crypto bars.

    Uses only bars t-1,t (trailing) -- no lookahead. Negative estimates (which the
    estimator can produce in low-vol bars) are floored, as in the original paper.
    """
    h, l = high.astype(float), low.astype(float)
    beta = (np.log(h / l) ** 2) + (np.log(h.shift(1) / l.shift(1)) ** 2)
    h2 = pd.concat([h, h.shift(1)], axis=1).max(axis=1)
    l2 = pd.concat([l, l.shift(1)], axis=1).min(axis=1)
    gamma = np.log(h2 / l2) ** 2

    denom = 3 - 2 * np.sqrt(2)
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / denom - np.sqrt(gamma / denom)
    alpha = alpha.replace([np.inf, -np.inf], np.nan)
    spread = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))   # proportional FULL spread
    half_bps = (spread / 2.0) * 1e4
    half_bps = half_bps.where(np.isfinite(half_bps))
    return half_bps.clip(lower=floor_bps).fillna(floor_bps)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Trailing ATR. Uses only data through the current bar; consumers must still
    shift before using it for a decision."""
    h, l, c = df["high"].astype(float), df["low"].astype(float), df["close"].astype(float)
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


# ---------------------------------------------------------------------------
# Per-fill cost
# ---------------------------------------------------------------------------

def slippage_bps(order_notional: float, bar_quote_volume: float, atr_value: float,
                  price: float, cfg: CostConfig) -> float:
    if bar_quote_volume is None or bar_quote_volume <= 0 or price <= 0 or not np.isfinite(atr_value):
        return cfg.slippage_floor_bps * cfg.multiplier
    participation = max(order_notional, 0.0) / bar_quote_volume
    raw = cfg.slippage_k * np.sqrt(participation) * (atr_value / price) * 1e4
    return max(raw, cfg.slippage_floor_bps) * cfg.multiplier


def one_way_cost_bps(order_notional: float, bar_quote_volume: float, atr_value: float,
                      price: float, half_spread_bps_value: float, cfg: CostConfig) -> dict:
    """Total one-side cost in bps, itemised so the report can attribute it."""
    fee = cfg.fee_bps * cfg.multiplier
    spread = max(half_spread_bps_value, cfg.half_spread_floor_bps) * cfg.multiplier
    slip = slippage_bps(order_notional, bar_quote_volume, atr_value, price, cfg)
    return {"fee_bps": fee, "half_spread_bps": spread, "slippage_bps": slip,
            "total_bps": fee + spread + slip}


def round_trip_cost_bps(order_notional: float, bar_quote_volume: float, atr_value: float,
                         price: float, half_spread_bps_value: float, cfg: CostConfig) -> float:
    return 2 * one_way_cost_bps(order_notional, bar_quote_volume, atr_value, price,
                                 half_spread_bps_value, cfg)["total_bps"]


# ---------------------------------------------------------------------------
# Funding
# ---------------------------------------------------------------------------

def funding_settlements_between(funding: pd.DataFrame, t0: pd.Timestamp, t1: pd.Timestamp) -> pd.DataFrame:
    """Real funding prints strictly after entry and at/before exit."""
    if funding is None or funding.empty:
        return pd.DataFrame(columns=["timestamp", "fundingRate"])
    m = (funding["timestamp"] > t0) & (funding["timestamp"] <= t1)
    return funding.loc[m, ["timestamp", "fundingRate"]]


def funding_cost_usd(position_notional_signed: float, funding: pd.DataFrame,
                      t0: pd.Timestamp, t1: pd.Timestamp) -> float:
    """Longs PAY positive funding; shorts RECEIVE it. Returns a COST (positive = you paid)."""
    sets_ = funding_settlements_between(funding, t0, t1)
    if sets_.empty:
        return 0.0
    return float(position_notional_signed * sets_["fundingRate"].sum())


# ---------------------------------------------------------------------------
# Diagnostics required by the spec
# ---------------------------------------------------------------------------

def cost_to_stop_ratio(median_stop_distance_bps: float, median_round_trip_cost_bps: float) -> dict:
    ratio = median_stop_distance_bps / median_round_trip_cost_bps if median_round_trip_cost_bps > 0 else np.inf
    return {"median_stop_distance_bps": round(median_stop_distance_bps, 2),
            "median_round_trip_cost_bps": round(median_round_trip_cost_bps, 2),
            "stop_to_cost_ratio": round(ratio, 2),
            "structurally_fee_bound": bool(ratio < 20),
            "note": ("FLAG: stop distance < 20x round-trip cost -- strategy is structurally "
                     "fee-bound regardless of signal quality" if ratio < 20 else
                     "stop distance >= 20x round-trip cost")}


def slippage_k_sensitivity(order_notional: float, bar_quote_volume: float,
                            atr_value: float, price: float) -> dict:
    out = {}
    for k in (0.5, 1.0, 2.0, 4.0):
        cfg = CostConfig(slippage_k=k)
        out[f"k={k}"] = round(slippage_bps(order_notional, bar_quote_volume, atr_value, price, cfg), 3)
    return out
