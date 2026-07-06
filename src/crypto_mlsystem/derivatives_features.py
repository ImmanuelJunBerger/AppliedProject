"""Lagged derivatives/market-structure features and aligned seven-day targets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class DerivativesResearchDataset:
    frame: pd.DataFrame
    feature_sets: dict[str, list[str]]
    target_columns: dict[str, str]
    metadata: dict[str, Any]


def _rolling_z(series: pd.Series, window: int, minimum: int) -> pd.Series:
    mean = series.rolling(window, min_periods=minimum).mean()
    std = series.rolling(window, min_periods=minimum).std().replace(0, np.nan)
    return (series - mean) / std


def _rolling_percentile(series: pd.Series, window: int = 252, minimum: int = 60) -> pd.Series:
    return series.rolling(window, min_periods=minimum).apply(
        lambda values: float(pd.Series(values).rank(pct=True).iloc[-1]), raw=False
    )


def _streak(series: pd.Series, positive: bool) -> pd.Series:
    condition = series.gt(0) if positive else series.lt(0)
    groups = (~condition).cumsum()
    return condition.groupby(groups).cumsum().astype(float)


def build_derivatives_features(
    spot_panel: pd.DataFrame,
    derivatives: pd.DataFrame,
    symbols: tuple[str, ...] = ("BTC", "ETH"),
    horizon: int = 7,
    holdout_start: str = "2025-01-01",
) -> DerivativesResearchDataset:
    spot = spot_panel[spot_panel.symbol.isin(symbols)].copy().sort_values(["symbol", "date"])
    spot["date"] = pd.to_datetime(spot.date)
    derivatives = derivatives.copy()
    derivatives["date"] = pd.to_datetime(derivatives.date)
    rows: list[pd.DataFrame] = []
    price_features = [
        "price_momentum_7", "price_momentum_30", "price_momentum_90",
        "price_realized_volatility_7", "price_realized_volatility_30",
        "price_drawdown_90", "price_volume_shock", "price_volatility_shock",
    ]
    funding_features = [
        "funding_rate", "funding_mean_3", "funding_mean_7", "funding_mean_14",
        "funding_change_1", "funding_abs", "funding_zscore_90",
        "funding_percentile_252", "funding_positive_streak", "funding_negative_streak",
    ]
    oi_features = [
        "open_interest_log", "open_interest_change_1", "open_interest_change_7",
        "open_interest_zscore_30", "open_interest_to_volume",
        "price_up_oi_up", "price_down_oi_up", "price_up_oi_down", "price_down_oi_down",
    ]
    basis_features = [
        "basis", "basis_zscore_90", "basis_change_1", "basis_compression", "basis_expansion",
    ]
    crowding_features = [
        "crowding_high_funding_high_oi", "crowding_high_funding_negative_momentum",
        "crowding_rising_oi_falling_price", "crowding_extreme_funding",
    ]
    structure_features = ["taker_imbalance", "long_short_ratio"]

    for symbol in symbols:
        asset = spot[spot.symbol == symbol].set_index("date").sort_index()
        deriv = derivatives[derivatives.symbol == symbol].set_index("date").sort_index()
        index = asset.index
        close = asset.close.astype(float)
        volume = asset.volume.astype(float)
        returns = close.pct_change(fill_method=None)
        frame = pd.DataFrame(index=index)
        def aligned(column: str) -> pd.Series:
            if column not in deriv.columns:
                return pd.Series(np.nan, index=index, dtype=float)
            return pd.to_numeric(deriv[column], errors="coerce").reindex(index)

        frame["price_momentum_7"] = close.pct_change(7, fill_method=None)
        frame["price_momentum_30"] = close.pct_change(30, fill_method=None)
        frame["price_momentum_90"] = close.pct_change(90, fill_method=None)
        frame["price_realized_volatility_7"] = returns.rolling(7).std() * np.sqrt(365)
        frame["price_realized_volatility_30"] = returns.rolling(30).std() * np.sqrt(365)
        frame["price_drawdown_90"] = close / close.rolling(90).max() - 1
        dollar_volume = close * volume
        frame["price_volume_shock"] = _rolling_z(np.log1p(dollar_volume), 60, 20)
        frame["price_volatility_shock"] = (
            frame.price_realized_volatility_7 / frame.price_realized_volatility_30.replace(0, np.nan) - 1
        )

        funding = aligned("funding_rate")
        frame["funding_rate"] = funding
        frame["funding_mean_3"] = funding.rolling(3).mean()
        frame["funding_mean_7"] = funding.rolling(7).mean()
        frame["funding_mean_14"] = funding.rolling(14).mean()
        frame["funding_change_1"] = funding.diff()
        frame["funding_abs"] = funding.abs()
        frame["funding_zscore_90"] = _rolling_z(funding, 90, 30)
        frame["funding_percentile_252"] = _rolling_percentile(funding)
        frame["funding_positive_streak"] = _streak(funding.fillna(0), True)
        frame["funding_negative_streak"] = _streak(funding.fillna(0), False)

        oi = aligned("open_interest")
        frame["open_interest_log"] = np.log1p(oi.clip(lower=0))
        frame["open_interest_change_1"] = frame.open_interest_log.diff()
        frame["open_interest_change_7"] = frame.open_interest_log.diff(7)
        frame["open_interest_zscore_30"] = _rolling_z(frame.open_interest_log, 30, 15)
        frame["open_interest_to_volume"] = oi / dollar_volume.replace(0, np.nan)
        price_up, oi_up = returns.gt(0), frame.open_interest_change_1.gt(0)
        frame["price_up_oi_up"] = (price_up & oi_up).astype(float).where(oi.notna())
        frame["price_down_oi_up"] = ((~price_up) & oi_up).astype(float).where(oi.notna())
        frame["price_up_oi_down"] = (price_up & (~oi_up)).astype(float).where(oi.notna())
        frame["price_down_oi_down"] = ((~price_up) & (~oi_up)).astype(float).where(oi.notna())

        basis = aligned("basis_close")
        frame["basis"] = basis
        frame["basis_zscore_90"] = _rolling_z(basis, 90, 30)
        frame["basis_change_1"] = basis.diff()
        frame["basis_compression"] = (-basis.abs().diff()).clip(lower=0)
        frame["basis_expansion"] = basis.abs().diff().clip(lower=0)

        frame["crowding_high_funding_high_oi"] = (
            (frame.funding_zscore_90 > 2) & (frame.open_interest_zscore_30 > 1)
        ).astype(float).where(oi.notna())
        frame["crowding_high_funding_negative_momentum"] = (
            (frame.funding_zscore_90 > 2) & (frame.price_momentum_30 < 0)
        ).astype(float)
        frame["crowding_rising_oi_falling_price"] = (
            (frame.open_interest_change_7 > 0) & (frame.price_momentum_7 < 0)
        ).astype(float).where(oi.notna())
        frame["crowding_extreme_funding"] = (frame.funding_zscore_90.abs() > 2).astype(float)
        for column in structure_features:
            frame[column] = aligned(column)

        # All decision features are shifted one full day.  Targets below remain unshifted/future.
        feature_columns = price_features + funding_features + oi_features + basis_features + crowding_features + structure_features
        frame[feature_columns] = frame[feature_columns].shift(1)

        forward_return = close.shift(-horizon) / close - 1
        forward_paths = pd.concat(
            [close.shift(-step) / close - 1 for step in range(1, horizon + 1)], axis=1
        )
        future_variance = sum(returns.shift(-step).pow(2) for step in range(1, horizon + 1))
        past_variance = returns.pow(2).rolling(horizon).sum()
        frame["forward_return_7"] = forward_return
        frame["target_risk_adjusted_sign"] = (forward_return > 0).astype(float).where(forward_return.notna())
        frame["target_drawdown_5"] = (forward_paths.min(axis=1) <= -0.05).astype(float).where(forward_return.notna())
        frame["target_drawdown_10"] = (forward_paths.min(axis=1) <= -0.10).astype(float).where(forward_return.notna())
        frame["target_drawdown_15"] = (forward_paths.min(axis=1) <= -0.15).astype(float).where(forward_return.notna())
        frame["target_volatility_expansion"] = (future_variance > past_variance).astype(float).where(forward_return.notna())
        extreme = frame.funding_zscore_90.abs() > 2
        reversion = np.where(frame.funding_zscore_90 > 2, forward_return < 0, forward_return > 0)
        frame["target_funding_mean_reversion"] = pd.Series(reversion, index=index).astype(float).where(extreme & forward_return.notna())
        high_crowding = frame.crowding_high_funding_high_oi.eq(1)
        unwind = (forward_return < 0) | frame.target_volatility_expansion.eq(1)
        frame["target_crowding_unwind"] = unwind.astype(float).where(high_crowding & forward_return.notna())
        frame["label_end"] = pd.Series(index, index=index).shift(-horizon)
        frame["symbol"] = symbol
        frame["date"] = index
        rows.append(frame.reset_index(drop=True))

    combined = pd.concat(rows, ignore_index=True).sort_values(["date", "symbol"])
    future_by_symbol = combined.pivot(index="date", columns="symbol", values="forward_return_7")
    relative = (future_by_symbol.get("ETH") > future_by_symbol.get("BTC")).astype(float)
    combined["target_eth_outperforms_btc"] = combined.date.map(relative)
    combined.loc[combined.forward_return_7.isna(), "target_eth_outperforms_btc"] = np.nan
    combined = combined.replace([np.inf, -np.inf], np.nan)

    development = combined.date < pd.Timestamp(holdout_start)
    derivative_candidates = funding_features + oi_features + basis_features + crowding_features + structure_features
    usable_derivatives = [
        column for column in derivative_candidates
        if combined.loc[development, column].notna().mean() >= 0.20
    ]
    feature_sets = {
        "price_only": price_features,
        "derivatives_only": usable_derivatives,
        "price_derivatives": price_features + usable_derivatives,
    }
    target_columns = {
        "risk_adjusted_sign": "target_risk_adjusted_sign",
        "drawdown_5": "target_drawdown_5",
        "drawdown_10": "target_drawdown_10",
        "drawdown_15": "target_drawdown_15",
        "volatility_expansion": "target_volatility_expansion",
        "funding_mean_reversion": "target_funding_mean_reversion",
        "eth_outperforms_btc": "target_eth_outperforms_btc",
        "crowding_unwind": "target_crowding_unwind",
    }
    metadata = {
        "start": str(combined.date.min().date()), "end": str(combined.date.max().date()),
        "rows": len(combined), "symbols": list(symbols), "horizon_days": horizon,
        "usable_derivatives": usable_derivatives,
        "excluded_low_coverage_derivatives": sorted(set(derivative_candidates) - set(usable_derivatives)),
        "feature_lag_days": 1,
    }
    return DerivativesResearchDataset(combined, feature_sets, target_columns, metadata)
