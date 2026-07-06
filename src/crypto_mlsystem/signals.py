"""Leak-free, long-only asset-level strategy signals.

Every weight stamped at date t is derived from market data available no later than
t-1.  Weights are only refreshed on the requested rebalance schedule and are held
between rebalances.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import UniverseBuilder
from .strategies import price_matrix


@dataclass
class SignalBundle:
    weights: dict[str, pd.DataFrame]
    strengths: dict[str, pd.DataFrame]
    eligible: pd.DataFrame
    asset_returns: pd.DataFrame
    rebalance_dates: pd.DatetimeIndex


def _capped_long_only(raw: pd.DataFrame, max_weight: float) -> pd.DataFrame:
    """Normalize positive scores with iterative redistribution under an asset cap."""
    def cap_row(row: pd.Series) -> pd.Series:
        values = row.clip(lower=0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        if values.sum() <= 0:
            return values
        weights = pd.Series(0.0, index=values.index)
        active = values > 0
        remaining = 1.0
        for _ in range(len(weights) + 1):
            if not active.any() or remaining <= 0:
                break
            proposal = values.loc[active] / values.loc[active].sum() * remaining
            over = proposal > max_weight
            if not over.any():
                weights.loc[active] = proposal
                break
            capped = proposal.index[over]
            weights.loc[capped] = max_weight
            active.loc[capped] = False
            remaining = 1.0 - float(weights.sum())
        return weights

    return raw.apply(cap_row, axis=1)


def _rebalance(weights: pd.DataFrame, frequency: str) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    scheduled = weights.resample(frequency).last().index.intersection(weights.index)
    held = pd.DataFrame(np.nan, index=weights.index, columns=weights.columns)
    held.loc[scheduled] = weights.loc[scheduled]
    return held.ffill().fillna(0.0), scheduled


def build_signal_bundle(
    panel: pd.DataFrame,
    universes: dict[pd.Timestamp, list[str]],
    rebalance_frequency: str = "W-FRI",
    max_asset_weight: float = 0.10,
) -> SignalBundle:
    px = price_matrix(panel)
    high = panel.pivot(index="date", columns="symbol", values="high").reindex_like(px)
    ret = px.pct_change(fill_method=None)
    eligible = UniverseBuilder.membership_mask(panel, universes).reindex_like(px).fillna(False)

    mom_7 = px.pct_change(7, fill_method=None).shift(1)
    mom_30 = px.pct_change(30, fill_method=None).shift(1)
    mom_90 = px.pct_change(90, fill_method=None).shift(1)
    ma_20 = px.rolling(20).mean().shift(1)
    ma_100 = px.rolling(100).mean().shift(1)
    vol_20 = ret.rolling(20).std().shift(1)
    vol_60 = ret.rolling(60).std().shift(1)

    trend_strength = mom_30.clip(lower=0) * (ma_20 > ma_100).astype(float)
    momentum_rank = mom_90.where(eligible).rank(axis=1, pct=True)
    momentum_strength = mom_90.clip(lower=0) * (momentum_rank >= 0.70).astype(float)

    short_mean = ret.rolling(20).mean().shift(1)
    short_std = ret.rolling(20).std().shift(1).replace(0, np.nan)
    reversal_z = (mom_7 - short_mean * 7) / (short_std * np.sqrt(7))
    mean_reversion_strength = (-reversal_z - 1.0).clip(lower=0) * (mom_30 > -0.20).astype(float)

    prior_high = high.rolling(20).max().shift(2)
    breakout_margin = (px.shift(1) / prior_high - 1).clip(lower=0)
    breakout_strength = breakout_margin * (vol_20 > vol_60).astype(float)

    btc = px["BTC"] if "BTC" in px else px.iloc[:, 0]
    market_ret = ret.where(eligible).mean(axis=1)
    market_vol = market_ret.rolling(30).std().shift(1) * np.sqrt(365)
    breadth = ((mom_30 > 0) & eligible).sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)
    risk_on = (btc.pct_change(30, fill_method=None).shift(1) > 0) & (market_vol < 0.80) & (breadth > 0.45)
    defensive_strength = (1 / vol_20.replace(0, np.nan)).mul(risk_on.astype(float), axis=0)

    raw = {
        "trend_following": trend_strength,
        "cross_sectional_momentum": momentum_strength,
        "mean_reversion": mean_reversion_strength,
        "volatility_breakout": breakout_strength,
        "defensive_cash": defensive_strength,
    }
    weights: dict[str, pd.DataFrame] = {}
    strengths: dict[str, pd.DataFrame] = {}
    rebalance_dates = pd.DatetimeIndex([])
    for name, strength in raw.items():
        clean_strength = strength.where(eligible).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        target = _capped_long_only(clean_strength, max_asset_weight)
        held, dates = _rebalance(target, rebalance_frequency)
        # Eligibility is sampled when the target is formed. Holdings then remain
        # unchanged until the next scheduled rebalance.
        weights[name] = held
        strengths[name] = clean_strength
        rebalance_dates = dates

    return SignalBundle(weights, strengths, eligible, ret.fillna(0.0), rebalance_dates)


def strategy_gross_returns(bundle: SignalBundle) -> pd.DataFrame:
    return pd.DataFrame({
        name: (weights.shift(1).fillna(0.0) * bundle.asset_returns).sum(axis=1)
        for name, weights in bundle.weights.items()
    })
