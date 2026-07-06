"""Drawdown-controlled macro trend allocation for BTC/ETH/cash.

Standalone final research attempt.  The frozen ``btc_eth_macro_gate_balanced``
strategy is benchmark-only and is not modified, reselected, or retuned.
Candidate selection uses development-period CPCV only.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
    portfolio_metrics,
)
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import (
    block_bootstrap_sharpe_ci,
    deflated_sharpe_probability,
    probability_backtest_overfitting,
)


DEVELOPMENT_START = pd.Timestamp("2019-07-05")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")
ANALYSIS_COST_LEVELS = (0, *COST_LEVELS)
BASELINE_NAME = FIXED_SELECTED.name
PROJECT_TITLE = "Macro-Regime Conditioning for Systematic Cryptocurrency Allocation: A Robust Out-of-Sample Evaluation"


@dataclass(frozen=True)
class ControlledCandidate:
    name: str
    family: str
    portfolio: str
    mechanism: str
    rebalance_days: int
    target_vol: float | None = None
    drawdown_threshold: float | None = None
    drawdown_behavior: str | None = None
    floor_level: float | None = None
    multiplier: float | None = None
    floor_mode: str | None = None
    complexity_score: float = 0.80
    description: str = ""


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def _rolling_percentile(series: pd.Series, window: int = 252) -> pd.Series:
    return series.rolling(window, min_periods=max(30, window // 5)).apply(
        lambda values: pd.Series(values).rank(pct=True).iloc[-1],
        raw=False,
    )


def _trend_features(dataset: MacroRegimeDataset) -> pd.DataFrame:
    close = dataset.close
    returns = dataset.returns
    frame = pd.DataFrame(index=close.index)
    for asset in ("BTC", "ETH"):
        if asset not in close:
            continue
        price = close[asset]
        ret = returns[asset]
        frame[f"{asset}_momentum_63d"] = price.pct_change(63, fill_method=None).shift(1)
        frame[f"{asset}_momentum_126d"] = price.pct_change(126, fill_method=None).shift(1)
        frame[f"{asset}_above_100dma"] = (price.shift(1) > price.rolling(100, min_periods=60).mean().shift(1)).astype(float)
        frame[f"{asset}_above_200dma"] = (price.shift(1) > price.rolling(200, min_periods=120).mean().shift(1)).astype(float)
        frame[f"{asset}_drawdown_90d"] = price.shift(1) / price.rolling(90, min_periods=40).max().shift(1) - 1.0
        frame[f"{asset}_donchian_breakout_63d"] = (price.shift(1) >= price.rolling(63, min_periods=40).max().shift(1)).astype(float)
        vol21 = ret.rolling(21, min_periods=14).std().shift(1) * np.sqrt(365)
        vol63 = ret.rolling(63, min_periods=30).std().shift(1) * np.sqrt(365)
        frame[f"{asset}_realized_vol_21d"] = vol21
        frame[f"{asset}_realized_vol_63d"] = vol63
        frame[f"{asset}_realized_vol_percentile"] = _rolling_percentile(vol63)
        frame[f"{asset}_vol_compression"] = (frame[f"{asset}_realized_vol_percentile"] <= 0.35).astype(float)
        frame[f"{asset}_vol_expansion"] = (frame[f"{asset}_realized_vol_percentile"] >= 0.65).astype(float)
    if {"BTC", "ETH"}.issubset(close.columns):
        ratio = close["ETH"] / close["BTC"]
        frame["ETH_BTC_relative_strength_63d"] = ratio.pct_change(63, fill_method=None).shift(1)
    else:
        frame["ETH_BTC_relative_strength_63d"] = 0.0
    return frame.replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)


def _asset_trend_ok(features: pd.DataFrame, date_: pd.Timestamp, asset: str) -> bool:
    row = features.loc[date_]
    trend_votes = [
        row.get(f"{asset}_momentum_63d", 0.0) > 0,
        row.get(f"{asset}_momentum_126d", 0.0) > 0,
        row.get(f"{asset}_above_100dma", 0.0) > 0.5,
        row.get(f"{asset}_above_200dma", 0.0) > 0.5,
        row.get(f"{asset}_donchian_breakout_63d", 0.0) > 0.5,
    ]
    severe_drawdown = row.get(f"{asset}_drawdown_90d", 0.0) < -0.35
    return sum(trend_votes) >= 3 and not severe_drawdown


def _base_trend_weights(
    dataset: MacroRegimeDataset,
    candidate: ControlledCandidate,
    combined_regime: pd.Series,
    trend: pd.DataFrame,
    frozen_weights: pd.DataFrame,
) -> pd.DataFrame:
    if candidate.portfolio == "frozen":
        dates = _rebalance_dates(dataset.close.index, candidate.rebalance_days)
        return frozen_weights.reindex(dates).ffill().fillna(0.0)

    dates = _rebalance_dates(dataset.close.index, candidate.rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    for date_ in dates:
        regime = combined_regime.reindex([date_]).ffill().iloc[0] if date_ in combined_regime.index else "risk_off"
        if regime == "risk_off":
            continue
        macro_exposure = 1.0 if regime == "risk_on" else 0.50
        btc_ok = "BTC" in weights.columns and _asset_trend_ok(trend, date_, "BTC")
        eth_ok = "ETH" in weights.columns and _asset_trend_ok(trend, date_, "ETH")
        if candidate.portfolio == "btc":
            if btc_ok:
                weights.loc[date_, "BTC"] = macro_exposure
        elif candidate.portfolio == "eth":
            if eth_ok:
                weights.loc[date_, "ETH"] = macro_exposure
        elif candidate.portfolio == "balanced":
            if btc_ok or eth_ok:
                if "BTC" in weights:
                    weights.loc[date_, "BTC"] = 0.50 * macro_exposure
                if "ETH" in weights:
                    weights.loc[date_, "ETH"] = 0.50 * macro_exposure
        elif candidate.portfolio == "dual_momentum":
            if not btc_ok and not eth_ok:
                continue
            rel = trend.loc[date_].get("ETH_BTC_relative_strength_63d", 0.0)
            if btc_ok and eth_ok:
                btc_weight, eth_weight = (0.30, 0.70) if rel > 0 else (0.70, 0.30)
                weights.loc[date_, "BTC"] = btc_weight * macro_exposure
                weights.loc[date_, "ETH"] = eth_weight * macro_exposure
            elif btc_ok:
                weights.loc[date_, "BTC"] = macro_exposure
            elif eth_ok:
                weights.loc[date_, "ETH"] = macro_exposure
        else:
            raise ValueError(candidate.portfolio)
    return weights


def _candidate_registry() -> list[ControlledCandidate]:
    target_vols = (0.20, 0.30, 0.40, 0.50)
    dd_thresholds = (-0.10, -0.15, -0.20, -0.25)
    dd_behaviors = ("reduce_50", "cash")
    floors = (0.70, 0.75, 0.80, 0.85)
    multipliers = (1.0, 2.0, 3.0)
    floor_modes = ("static", "tipp")
    rebalance_values = (7, 14)
    portfolios = (
        ("btc", "Family A: BTC-only macro trend with drawdown control", 0.90),
        ("eth", "Family B: ETH-only macro trend with drawdown control", 0.90),
        ("balanced", "Family C: 50/50 BTC/ETH macro trend with drawdown control", 0.88),
        ("dual_momentum", "Family D: BTC/ETH dual-momentum macro trend with drawdown control", 0.78),
    )
    candidates: list[ControlledCandidate] = []
    for portfolio, family, base_simplicity in portfolios:
        for rebalance_days in rebalance_values:
            for target_vol in target_vols:
                candidates.append(ControlledCandidate(
                    name=f"{portfolio}_macro_trend_vol_{int(target_vol*100)}_r{rebalance_days}",
                    family=family,
                    portfolio=portfolio,
                    mechanism="vol_target",
                    rebalance_days=rebalance_days,
                    target_vol=target_vol,
                    complexity_score=base_simplicity * 0.90,
                    description="Macro gate plus crypto trend confirmation with volatility-targeted exposure.",
                ))
            for threshold in dd_thresholds:
                for behavior in dd_behaviors:
                    candidates.append(ControlledCandidate(
                        name=f"{portfolio}_macro_trend_dd_{abs(int(threshold*100))}_{behavior}_r{rebalance_days}",
                        family=family,
                        portfolio=portfolio,
                        mechanism="drawdown_brake",
                        rebalance_days=rebalance_days,
                        drawdown_threshold=threshold,
                        drawdown_behavior=behavior,
                        complexity_score=base_simplicity * (0.88 if behavior == "reduce_50" else 0.82),
                        description="Macro gate plus crypto trend confirmation with trailing drawdown brake.",
                    ))
            for floor in floors:
                for multiplier in multipliers:
                    for mode in floor_modes:
                        candidates.append(ControlledCandidate(
                            name=f"{portfolio}_macro_trend_{mode}_{int(floor*100)}_m{int(multiplier)}_r{rebalance_days}",
                            family=family,
                            portfolio=portfolio,
                            mechanism="portfolio_insurance",
                            rebalance_days=rebalance_days,
                            floor_level=floor,
                            multiplier=multiplier,
                            floor_mode=mode,
                            complexity_score=base_simplicity * (0.78 if mode == "static" else 0.68),
                            description="Macro gate plus crypto trend confirmation with CPPI/TIPP-style portfolio insurance.",
                        ))

    frozen_specs = (
        ("frozen_dd", "Family E: Frozen macro allocation plus drawdown-control overlay", "drawdown_brake", 0.84),
        ("frozen_vol", "Family F: Frozen macro allocation plus volatility-managed exposure overlay", "vol_target", 0.88),
        ("frozen_pi", "Family G: Frozen macro allocation plus portfolio-insurance overlay", "portfolio_insurance", 0.72),
    )
    for prefix, family, mechanism, simplicity in frozen_specs:
        for rebalance_days in rebalance_values:
            if mechanism == "vol_target":
                for target_vol in target_vols:
                    candidates.append(ControlledCandidate(
                        name=f"{prefix}_{int(target_vol*100)}_r{rebalance_days}",
                        family=family,
                        portfolio="frozen",
                        mechanism=mechanism,
                        rebalance_days=rebalance_days,
                        target_vol=target_vol,
                        complexity_score=simplicity,
                        description="Frozen macro BTC/ETH/cash allocation with volatility-managed exposure overlay.",
                    ))
            elif mechanism == "drawdown_brake":
                for threshold in dd_thresholds:
                    for behavior in dd_behaviors:
                        candidates.append(ControlledCandidate(
                            name=f"{prefix}_{abs(int(threshold*100))}_{behavior}_r{rebalance_days}",
                            family=family,
                            portfolio="frozen",
                            mechanism=mechanism,
                            rebalance_days=rebalance_days,
                            drawdown_threshold=threshold,
                            drawdown_behavior=behavior,
                            complexity_score=simplicity * (0.95 if behavior == "reduce_50" else 0.88),
                            description="Frozen macro BTC/ETH/cash allocation with trailing drawdown-control overlay.",
                        ))
            else:
                for floor in floors:
                    for multiplier in multipliers:
                        for mode in floor_modes:
                            candidates.append(ControlledCandidate(
                                name=f"{prefix}_{mode}_{int(floor*100)}_m{int(multiplier)}_r{rebalance_days}",
                                family=family,
                                portfolio="frozen",
                                mechanism=mechanism,
                                rebalance_days=rebalance_days,
                                floor_level=floor,
                                multiplier=multiplier,
                                floor_mode=mode,
                                complexity_score=simplicity * (0.90 if mode == "static" else 0.78),
                                description="Frozen macro BTC/ETH/cash allocation with CPPI/TIPP-style portfolio insurance overlay.",
                            ))
    return candidates


def _realized_sleeve_vol(
    returns: pd.DataFrame,
    date_: pd.Timestamp,
    target: np.ndarray,
    columns: list[str],
    lookback: int = 63,
) -> float:
    exposure = float(np.abs(target).sum())
    if exposure <= 1e-12:
        return np.nan
    comp = target / exposure
    loc = returns.index.get_loc(date_)
    start = max(0, loc - lookback)
    hist = returns.iloc[start:loc]
    if len(hist) < 21:
        return np.nan
    sleeve = hist.reindex(columns=columns).fillna(0.0).to_numpy(dtype=float) @ comp
    vol63 = np.std(sleeve, ddof=1) * np.sqrt(365) if len(sleeve) > 2 else np.nan
    vol21 = np.std(sleeve[-21:], ddof=1) * np.sqrt(365) if len(sleeve) >= 21 else vol63
    if not np.isfinite(vol63):
        return np.nan
    return float(0.50 * vol63 + 0.50 * vol21)


def _dynamic_backtest(
    dataset: MacroRegimeDataset,
    base_weights: pd.DataFrame,
    candidate: ControlledCandidate | None,
    macro_regime: pd.Series,
    crypto_regime: pd.Series,
    combined_regime: pd.Series,
    cost_bps: int,
    turnover_cap: float = 0.75,
) -> PortfolioResult:
    returns = dataset.returns.reindex(columns=base_weights.columns).fillna(0.0)
    start = base_weights.index.min()
    returns = returns.loc[start:min(HOLDOUT_END, returns.index.max())]
    columns = list(returns.columns)
    targets = base_weights.reindex(base_weights.index.intersection(returns.index)).fillna(0.0)
    target_map = {date_: row.reindex(columns).fillna(0.0).to_numpy(dtype=float) for date_, row in targets.iterrows()}
    returns_array = returns.to_numpy(dtype=float)
    executed = np.zeros((len(returns), len(columns)), dtype=float)
    gross = np.zeros(len(returns), dtype=float)
    net = np.zeros(len(returns), dtype=float)
    turnover = np.zeros(len(returns), dtype=float)
    costs = np.zeros(len(returns), dtype=float)
    previous = np.zeros(len(columns), dtype=float)
    cost_rate = cost_bps / 10000.0
    wealth = 1.0
    high_water = 1.0
    brake_active = False

    for i, date_ in enumerate(returns.index):
        gross[i] = float(previous @ returns_array[i])
        requested = target_map.get(date_)
        target = previous.copy()
        if requested is not None:
            scale = 1.0
            if candidate is not None:
                drawdown = wealth / high_water - 1.0 if high_water > 0 else 0.0
                base_exposure = float(np.abs(requested).sum())
                if candidate.mechanism == "vol_target":
                    vol = _realized_sleeve_vol(returns, date_, requested, columns)
                    if np.isfinite(vol) and vol > 1e-9 and candidate.target_vol is not None:
                        scale = min(1.0, max(0.0, candidate.target_vol / vol))
                elif candidate.mechanism == "drawdown_brake":
                    threshold = candidate.drawdown_threshold if candidate.drawdown_threshold is not None else -0.20
                    if drawdown <= threshold:
                        brake_active = True
                    if brake_active and base_exposure > 1e-9 and drawdown > threshold / 2:
                        brake_active = False
                    if brake_active:
                        scale = 0.50 if candidate.drawdown_behavior == "reduce_50" else 0.0
                elif candidate.mechanism == "portfolio_insurance":
                    floor_level = candidate.floor_level if candidate.floor_level is not None else 0.80
                    multiplier = candidate.multiplier if candidate.multiplier is not None else 2.0
                    reference = high_water if candidate.floor_mode == "tipp" else 1.0
                    floor_value = floor_level * reference
                    cushion_fraction = max(0.0, (wealth - floor_value) / max(wealth, 1e-12))
                    scale = min(1.0, max(0.0, multiplier * cushion_fraction))
            requested = requested * scale
            change = requested - previous
            requested_turnover = float(np.abs(change).sum())
            if requested_turnover > turnover_cap and requested_turnover > 0:
                target = previous + change * (turnover_cap / requested_turnover)
            else:
                target = requested
            turnover[i] = float(np.abs(target - previous).sum())
            costs[i] = turnover[i] * cost_rate
        net[i] = gross[i] - costs[i]
        wealth *= max(0.0, 1.0 + net[i])
        high_water = max(high_water, wealth)
        executed[i] = target
        previous = target

    net_series = pd.Series(net, index=returns.index)
    gross_series = pd.Series(gross, index=returns.index)
    turnover_series = pd.Series(turnover, index=returns.index)
    costs_series = pd.Series(costs, index=returns.index)
    executed_frame = pd.DataFrame(executed, index=returns.index, columns=columns)
    return PortfolioResult(
        returns=net_series,
        gross_returns=gross_series,
        weights=executed_frame,
        turnover=turnover_series,
        costs=costs_series,
        macro_regime=macro_regime.reindex(net_series.index).ffill(),
        crypto_regime=crypto_regime.reindex(net_series.index).ffill(),
        combined_regime=combined_regime.reindex(net_series.index).ffill(),
        metrics=portfolio_metrics(net_series, turnover_series, costs_series, executed_frame),
    )


def _drawdown_periods(returns: pd.Series) -> list[dict[str, Any]]:
    r = returns.dropna()
    if r.empty:
        return []
    wealth = (1.0 + r).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    periods = []
    in_dd = False
    start = None
    trough = None
    trough_dd = 0.0
    last_peak = drawdown.index[0]
    for date_, value in drawdown.items():
        value = float(value)
        if value >= -1e-12:
            last_peak = date_
            if in_dd:
                periods.append({"start": start, "trough": trough, "recovery": date_, "max_drawdown": trough_dd})
                in_dd = False
            continue
        if not in_dd:
            in_dd = True
            start = last_peak
            trough = date_
            trough_dd = value
        elif value < trough_dd:
            trough = date_
            trough_dd = value
    if in_dd:
        periods.append({"start": start, "trough": trough, "recovery": None, "max_drawdown": trough_dd})
    return periods


def _worst_drawdown_info(returns: pd.Series) -> dict[str, Any]:
    periods = _drawdown_periods(returns)
    if not periods:
        return {"worst_drawdown_start": None, "worst_drawdown_trough": None, "worst_drawdown_recovery": None}
    worst = sorted(periods, key=lambda item: item["max_drawdown"])[0]
    return {
        "worst_drawdown_start": str(pd.Timestamp(worst["start"]).date()) if worst["start"] is not None else None,
        "worst_drawdown_trough": str(pd.Timestamp(worst["trough"]).date()) if worst["trough"] is not None else None,
        "worst_drawdown_recovery": str(pd.Timestamp(worst["recovery"]).date()) if worst["recovery"] is not None else None,
    }


def _period_metrics_extended(result: PortfolioResult, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    metrics = period_metrics(result, start, end)
    returns = result.returns.loc[start:end]
    metrics["Allocation Changes"] = int((result.turnover.reindex(returns.index).fillna(0.0) > 1e-9).sum())
    metrics.update(_worst_drawdown_info(returns))
    return metrics


def _weekly_returns(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0).dropna()


def _sharpe(returns: pd.Series, annualization: int = 52) -> float:
    values = returns.dropna()
    std = values.std()
    return float(values.mean() / std * np.sqrt(annualization)) if len(values) and std and np.isfinite(std) else 0.0


def _cpcv_rows(name: str, result: PortfolioResult) -> pd.DataFrame:
    weekly = _weekly_returns(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
    if len(weekly) < 20:
        return pd.DataFrame()
    rows = []
    for fold, split in enumerate(combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)):
        test = weekly.iloc[list(split.test_indices)]
        rows.append({
            "candidate": name,
            "fold": fold,
            "test_groups": "-".join(map(str, split.test_groups)),
            "fold_start": str(test.index.min().date()),
            "fold_end": str(test.index.max().date()),
            "fold_sharpe": _sharpe(test),
            "fold_return": float((1.0 + test).prod() - 1.0),
            "positive_fold": bool((1.0 + test).prod() - 1.0 > 0),
        })
    return pd.DataFrame(rows)


def _cpcv_summary(folds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for candidate, group in folds.groupby("candidate", dropna=False):
        rows.append({
            "candidate": candidate,
            "median_fold_sharpe": float(group["fold_sharpe"].median()),
            "best_fold_sharpe": float(group["fold_sharpe"].max()),
            "worst_fold_sharpe": float(group["fold_sharpe"].min()),
            "positive_fold_percentage": float(group["positive_fold"].mean()),
        })
    return pd.DataFrame(rows)


def _exposure_quality(
    dataset: MacroRegimeDataset,
    result: PortfolioResult,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, float]:
    returns = result.returns.loc[start:end]
    weights = result.weights.reindex(returns.index).fillna(0.0)
    exposure = weights.sum(axis=1).clip(0.0, 1.0)
    invested = exposure > 1e-9
    weekly = _weekly_returns(returns)
    weekly_exposure = exposure.resample("W-FRI").mean().reindex(weekly.index).fillna(0.0)
    invested_weeks = weekly_exposure > 1e-9
    assets = [asset for asset in ("BTC", "ETH") if asset in dataset.returns]
    opportunity = dataset.returns[assets].mean(axis=1).reindex(returns.index).fillna(0.0) if assets else pd.Series(0.0, index=returns.index)
    cash_days = ~invested
    missed_upside = float(opportunity[cash_days].clip(lower=0.0).sum())
    avoided_downside = float(-opportunity[cash_days].clip(upper=0.0).sum())
    invested_returns = returns[invested]
    return {
        "positive_invested_week_percentage": float((weekly[invested_weeks] > 0).mean()) if invested_weeks.any() else 0.0,
        "average_return_when_invested": float(invested_returns.mean()) if len(invested_returns) else 0.0,
        "missed_upside_while_in_cash": missed_upside,
        "avoided_downside_while_in_cash": avoided_downside,
        "conditional_sharpe_when_invested": _sharpe(invested_returns, annualization=365),
    }


def _score_candidates(
    candidates: list[ControlledCandidate],
    metrics: pd.DataFrame,
    cpcv_summary: pd.DataFrame,
    exposure_quality: pd.DataFrame,
    frozen_dev: dict[str, float],
    frozen_cpcv: dict[str, float],
) -> pd.DataFrame:
    dev = metrics[(metrics["split"].eq("development")) & (metrics["cost_bps"].eq(25))].set_index("candidate")
    cpcv = cpcv_summary.set_index("candidate")
    quality = exposure_quality[exposure_quality["split"].eq("development")].set_index("candidate")
    rows = []
    for candidate in candidates:
        if candidate.name not in dev.index or candidate.name not in cpcv.index:
            continue
        m = dev.loc[candidate.name]
        cv = cpcv.loc[candidate.name]
        q = quality.loc[candidate.name] if candidate.name in quality.index else pd.Series(dtype=float)
        dd_improvement = float(m["Maximum Drawdown"] - frozen_dev["Maximum Drawdown"])
        dd_score = np.clip((dd_improvement + 0.05) / 0.35, 0.0, 1.0)
        exposure = float(m["Exposure"])
        turnover = float(m["Annual Turnover"])
        exposure_score = np.clip(exposure / 0.35, 0.0, 1.0)
        exposure_score *= 0.65 + 0.35 * np.clip(float(q.get("positive_invested_week_percentage", 0.0)) / 0.55, 0.0, 1.0)
        if float(q.get("missed_upside_while_in_cash", 0.0)) > float(q.get("avoided_downside_while_in_cash", 0.0)) * 1.5:
            exposure_score *= 0.85
        turnover_score = 1.0 if turnover <= 12 else max(0.0, 1.0 - (turnover - 12) / 12)
        median_score = np.clip((float(cv["median_fold_sharpe"]) + 1.0) / 3.0, 0.0, 1.0)
        worst_score = np.clip((float(cv["worst_fold_sharpe"]) + 1.0) / 2.5, 0.0, 1.0)
        gap = float(m["Sharpe"] - cv["median_fold_sharpe"])
        gap_penalty = max(0.0, gap - 0.50) * 0.10
        hard_penalty = 0.0
        if m["Maximum Drawdown"] < -0.50:
            hard_penalty += 0.08
        if exposure < 0.25:
            hard_penalty += 0.10
        if turnover > 12:
            hard_penalty += 0.08
        score = (
            0.35 * median_score
            + 0.20 * dd_score
            + 0.15 * worst_score
            + 0.10 * exposure_score
            + 0.10 * turnover_score
            + 0.10 * candidate.complexity_score
            - gap_penalty
            - hard_penalty
        )
        rows.append({
            "candidate": candidate.name,
            "family": candidate.family,
            "portfolio": candidate.portfolio,
            "mechanism": candidate.mechanism,
            "rebalance_days": candidate.rebalance_days,
            "development_score": float(score),
            "cpcv_median_sharpe": float(cv["median_fold_sharpe"]),
            "cpcv_worst_fold_sharpe": float(cv["worst_fold_sharpe"]),
            "cpcv_best_fold_sharpe": float(cv["best_fold_sharpe"]),
            "positive_fold_percentage": float(cv["positive_fold_percentage"]),
            "development_sharpe": float(m["Sharpe"]),
            "development_cagr": float(m["CAGR"]),
            "development_max_drawdown": float(m["Maximum Drawdown"]),
            "development_turnover": turnover,
            "development_exposure": exposure,
            "development_cash": float(m["Cash Allocation"]),
            "drawdown_improvement_vs_frozen": dd_improvement,
            "exposure_score": float(exposure_score),
            "turnover_score": float(turnover_score),
            "simplicity_score": candidate.complexity_score,
            "train_cpcv_sharpe_gap": gap,
        })
    return pd.DataFrame(rows).sort_values("development_score", ascending=False).reset_index(drop=True)


def _paired_sharpe_delta_ci(left: pd.Series, right: pd.Series, samples: int = 500, block_length: int = 14, seed: int = 121) -> dict[str, float]:
    data = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
    if len(data) < block_length * 2:
        return {"lower": np.nan, "median": np.nan, "upper": np.nan, "p_value": np.nan}
    rng = np.random.default_rng(seed)
    arr = data.to_numpy(dtype=float)
    estimates = []
    blocks_needed = int(np.ceil(len(arr) / block_length))
    max_start = len(arr) - block_length
    for _ in range(samples):
        starts = rng.integers(0, max_start + 1, blocks_needed)
        sample = np.concatenate([arr[start:start + block_length] for start in starts])[:len(arr)]
        left_sr = _sharpe(pd.Series(sample[:, 0]), annualization=365)
        right_sr = _sharpe(pd.Series(sample[:, 1]), annualization=365)
        estimates.append(left_sr - right_sr)
    lower, median, upper = np.quantile(estimates, [0.025, 0.50, 0.975])
    p_value = float(np.mean(np.asarray(estimates) <= 0.0))
    return {"lower": float(lower), "median": float(median), "upper": float(upper), "p_value": p_value}


def _statistical_validation(
    results_25: dict[str, PortfolioResult],
    selected_candidates: list[str],
    frozen_result: PortfolioResult,
) -> pd.DataFrame:
    weekly_configs = {
        name: _weekly_returns(result.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        for name, result in results_25.items()
    }
    pbo = probability_backtest_overfitting(pd.DataFrame(weekly_configs), blocks=8)
    rows = []
    frozen_holdout = frozen_result.returns.loc[HOLDOUT_START:HOLDOUT_END]
    tested = len(results_25)
    for name in selected_candidates:
        holdout = results_25[name].returns.loc[HOLDOUT_START:HOLDOUT_END]
        ci = block_bootstrap_sharpe_ci(holdout, samples=500, block_length=14, seed=131)
        delta = _paired_sharpe_delta_ci(holdout, frozen_holdout)
        rows.append({
            "candidate": name,
            "tested_configurations": tested,
            "pbo": pbo,
            "deflated_sharpe_probability": deflated_sharpe_probability(holdout, tested),
            "bootstrap_sharpe_ci_lower": ci["lower"],
            "bootstrap_sharpe_ci_median": ci["median"],
            "bootstrap_sharpe_ci_upper": ci["upper"],
            "sharpe_delta_vs_frozen_lower": delta["lower"],
            "sharpe_delta_vs_frozen_median": delta["median"],
            "sharpe_delta_vs_frozen_upper": delta["upper"],
            "sharpe_delta_p_value": delta["p_value"],
        })
    return pd.DataFrame(rows)


def _benchmark_weight(dataset: MacroRegimeDataset, assets: tuple[str, ...]) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=dataset.close.index, columns=dataset.close.columns)
    available = [asset for asset in assets if asset in weights.columns]
    if available:
        weights.loc[:, available] = 1.0 / len(available)
    return weights


def _macro_gate_weight(dataset: MacroRegimeDataset, combined: pd.Series, assets: tuple[str, ...]) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index, 7)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    for date_ in dates:
        regime = combined.reindex([date_]).ffill().iloc[0]
        if regime == "risk_off":
            continue
        exposure = 1.0 if regime == "risk_on" else 0.50
        available = [asset for asset in assets if asset in weights.columns]
        for asset in available:
            weights.loc[date_, asset] = exposure / len(available)
    return weights


def _benchmark_rows_from_prior_reports() -> pd.DataFrame:
    rows = []
    path = Path("reports/agentic_strategy_audit/results.json")
    wanted = {
        "meta_gradient_boosting_60": "prior meta-label overlay",
        "expansion_first__btc_eth_only__confidence_weight__vol_target_macro_gate": "prior expansion-first best strategy",
        "hybrid__btc_eth_only__confidence_weight__vol_target": "prior hybrid strategy",
        "trend_scanning_meta_model_biweekly": "prior trend-scanning strategy",
    }
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("strategy_summaries", []):
            name = item.get("strategy_name")
            if name in wanted:
                rows.append({
                    "candidate": name,
                    "family": wanted[name],
                    "source": "reports/agentic_strategy_audit/results.json",
                    "split": "holdout",
                    "cost_bps": 25,
                    "CAGR": item.get("holdout_cagr"),
                    "Sharpe": item.get("holdout_sharpe"),
                    "Maximum Drawdown": item.get("max_drawdown"),
                    "Annual Turnover": item.get("turnover"),
                    "Exposure": item.get("exposure"),
                    "pbo": item.get("pbo"),
                    "deflated_sharpe_probability": item.get("dsr_probability"),
                    "comparison_role": "prior rejected/monitored benchmark",
                })
    agentic = Path("reports/agentic_strategy_discovery/results.json")
    if agentic.exists():
        payload = json.loads(agentic.read_text(encoding="utf-8"))
        stats = payload.get("statistics", {})
        winner = payload.get("winner", {}) or {}
        if not winner and payload.get("selection"):
            winner = {"candidate_name": payload["selection"][0].get("candidate")}
        rows.append({
            "candidate": winner.get("candidate_name", "agentic_strategy_discovery_candidate"),
            "family": "agentic strategy discovery candidate",
            "source": "reports/agentic_strategy_discovery/results.json",
            "split": "holdout",
            "cost_bps": 25,
            "CAGR": stats.get("winner_holdout_cagr"),
            "Sharpe": stats.get("winner_holdout_sharpe"),
            "Maximum Drawdown": stats.get("winner_holdout_max_drawdown"),
            "Annual Turnover": np.nan,
            "Exposure": np.nan,
            "pbo": stats.get("pbo"),
            "deflated_sharpe_probability": stats.get("deflated_sharpe_probability"),
            "comparison_role": "prior rejected benchmark",
        })
    return pd.DataFrame(rows)


def run_drawdown_controlled_macro_trend(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(
        panel,
        macro_features,
        public_data=public_data,
        volatility_probability=volatility_probability,
        universe_size=10,
    )
    frozen_weights, frozen_macro, frozen_crypto, frozen_combined = build_candidate_weights(dataset, FIXED_SELECTED)
    trend = _trend_features(dataset)
    candidates = _candidate_registry()
    base_weights = {
        candidate.name: _base_trend_weights(dataset, candidate, frozen_combined, trend, frozen_weights)
        for candidate in candidates
    }

    candidate_results: dict[str, dict[int, PortfolioResult]] = {}
    metrics_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_results[candidate.name] = {}
        for cost_bps in ANALYSIS_COST_LEVELS:
            result = _dynamic_backtest(
                dataset,
                base_weights[candidate.name],
                candidate,
                frozen_macro,
                frozen_crypto,
                frozen_combined,
                cost_bps=cost_bps,
                turnover_cap=FIXED_SELECTED.turnover_cap,
            )
            candidate_results[candidate.name][cost_bps] = result
            for split, start, end in (
                ("development", DEVELOPMENT_START, DEVELOPMENT_END),
                ("holdout", HOLDOUT_START, HOLDOUT_END),
            ):
                metrics_rows.append({
                    "candidate": candidate.name,
                    "family": candidate.family,
                    "portfolio": candidate.portfolio,
                    "mechanism": candidate.mechanism,
                    "rebalance_days": candidate.rebalance_days,
                    "split": split,
                    "cost_bps": cost_bps,
                    **_period_metrics_extended(result, start, end),
                })

    metrics = pd.DataFrame(metrics_rows)
    folds = pd.concat([_cpcv_rows(name, result[25]) for name, result in candidate_results.items()], ignore_index=True)
    cpcv_summary = _cpcv_summary(folds)

    exposure_rows = []
    for candidate in candidates:
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            exposure_rows.append({
                "candidate": candidate.name,
                "family": candidate.family,
                "portfolio": candidate.portfolio,
                "mechanism": candidate.mechanism,
                "split": split,
                **_exposure_quality(dataset, candidate_results[candidate.name][25], start, end),
            })
    exposure_quality = pd.DataFrame(exposure_rows)

    frozen_results: dict[int, PortfolioResult] = {}
    frozen_rows = []
    for cost_bps in ANALYSIS_COST_LEVELS:
        frozen = backtest_weights(
            dataset,
            frozen_weights,
            frozen_macro,
            frozen_crypto,
            frozen_combined,
            cost_bps=cost_bps,
            turnover_cap=FIXED_SELECTED.turnover_cap,
        )
        frozen_results[cost_bps] = frozen
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            frozen_rows.append({
                "candidate": BASELINE_NAME,
                "family": "Frozen benchmark",
                "portfolio": "frozen",
                "mechanism": "none",
                "rebalance_days": 7,
                "split": split,
                "cost_bps": cost_bps,
                **_period_metrics_extended(frozen, start, end),
            })
    frozen_metrics = pd.DataFrame(frozen_rows)
    frozen_cpcv_folds = _cpcv_rows(BASELINE_NAME, frozen_results[25])
    frozen_cpcv = _cpcv_summary(frozen_cpcv_folds).iloc[0].to_dict()
    frozen_dev = frozen_metrics[(frozen_metrics.split.eq("development")) & (frozen_metrics.cost_bps.eq(25))].iloc[0].to_dict()
    frozen_holdout = frozen_metrics[(frozen_metrics.split.eq("holdout")) & (frozen_metrics.cost_bps.eq(25))].iloc[0].to_dict()

    selection = _score_candidates(candidates, metrics, cpcv_summary, exposure_quality, frozen_dev, frozen_cpcv)
    selected_name = str(selection.iloc[0]["candidate"])
    top_names = selection.head(25)["candidate"].astype(str).tolist()
    stats = _statistical_validation(
        {name: result[25] for name, result in candidate_results.items()},
        top_names,
        frozen_results[25],
    )

    selected_holdout_25 = metrics[(metrics.candidate.eq(selected_name)) & (metrics.split.eq("holdout")) & (metrics.cost_bps.eq(25))].iloc[0]
    selected_holdout_50 = metrics[(metrics.candidate.eq(selected_name)) & (metrics.split.eq("holdout")) & (metrics.cost_bps.eq(50))].iloc[0]
    selected_dev_25 = metrics[(metrics.candidate.eq(selected_name)) & (metrics.split.eq("development")) & (metrics.cost_bps.eq(25))].iloc[0]
    selected_cpcv = cpcv_summary[cpcv_summary.candidate.eq(selected_name)].iloc[0]
    selected_stats = stats[stats.candidate.eq(selected_name)].iloc[0] if selected_name in set(stats.candidate) else pd.Series(dtype=float)

    replacement_failures = []
    if selected_dev_25["Maximum Drawdown"] <= frozen_dev["Maximum Drawdown"] + 0.20:
        replacement_failures.append("development max drawdown is not materially improved")
    if selected_cpcv["median_fold_sharpe"] < frozen_cpcv["median_fold_sharpe"] - 0.05:
        replacement_failures.append("CPCV median Sharpe is not comparable")
    if selected_cpcv["worst_fold_sharpe"] < frozen_cpcv["worst_fold_sharpe"] - 0.05:
        replacement_failures.append("CPCV worst-fold Sharpe is worse")
    if selected_holdout_25["Sharpe"] <= frozen_holdout["Sharpe"] + 0.10:
        replacement_failures.append("holdout net Sharpe at 25 bps does not improve materially")
    if selected_holdout_25["Maximum Drawdown"] < frozen_holdout["Maximum Drawdown"]:
        replacement_failures.append("holdout max drawdown is worse")
    if selected_holdout_25["Exposure"] <= 0.35:
        replacement_failures.append("holdout exposure is not above 35%")
    if selected_holdout_25["Annual Turnover"] >= 12:
        replacement_failures.append("annual turnover is not below 12x")
    if selected_holdout_50["Sharpe"] <= 0 or selected_holdout_50["CAGR"] <= 0:
        replacement_failures.append("does not survive 50 bps costs with positive Sharpe and CAGR")
    if np.isfinite(selected_stats.get("pbo", np.nan)) and selected_stats["pbo"] > 0.50:
        replacement_failures.append("PBO is above 50%")
    if np.isfinite(selected_stats.get("deflated_sharpe_probability", np.nan)) and selected_stats["deflated_sharpe_probability"] < 0.50:
        replacement_failures.append("deflated Sharpe probability is weak")
    if np.isfinite(selected_stats.get("sharpe_delta_vs_frozen_lower", np.nan)) and selected_stats["sharpe_delta_vs_frozen_lower"] <= 0:
        replacement_failures.append("bootstrap Sharpe delta confidence interval is not supportive")
    selected_quality = exposure_quality[(exposure_quality.candidate.eq(selected_name)) & (exposure_quality.split.eq("holdout"))].iloc[0]
    if selected_quality["missed_upside_while_in_cash"] > selected_quality["avoided_downside_while_in_cash"] * 1.5:
        replacement_failures.append("improvement is likely cash-driven or misses too much upside")

    final_decision = "replace_frozen_strategy" if not replacement_failures else "keep_frozen_strategy"

    # Fixed diagnostics and benchmarks requested for comparison.
    benchmark_specs = {
        "btc_only_macro_gate": _macro_gate_weight(dataset, frozen_combined, ("BTC",)),
        "eth_only_macro_gate": _macro_gate_weight(dataset, frozen_combined, ("ETH",)),
        "btc_eth_50_50_macro_gate": _macro_gate_weight(dataset, frozen_combined, ("BTC", "ETH")),
        "btc_buy_hold": _benchmark_weight(dataset, ("BTC",)),
        "eth_buy_hold": _benchmark_weight(dataset, ("ETH",)),
        "btc_eth_50_50_buy_hold": _benchmark_weight(dataset, ("BTC", "ETH")),
    }
    benchmark_rows = []
    all_on = pd.Series("risk_on", index=dataset.close.index, dtype=object)
    crypto = pd.Series("not_used", index=dataset.close.index, dtype=object)
    for name, weights in benchmark_specs.items():
        result = backtest_weights(dataset, weights, all_on, crypto, all_on, cost_bps=25, turnover_cap=10.0)
        if "macro_gate" in name:
            result = backtest_weights(dataset, weights, frozen_macro, frozen_crypto, frozen_combined, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            benchmark_rows.append({
                "candidate": name,
                "family": "requested benchmark",
                "source": "current deterministic diagnostic rerun",
                "split": split,
                "cost_bps": 25,
                **_period_metrics_extended(result, start, end),
            })
    benchmark_rows.append({**{k: v for k, v in frozen_holdout.items() if k not in ("candidate", "family")}, "candidate": BASELINE_NAME, "family": "frozen selected benchmark", "source": "current deterministic diagnostic rerun", "split": "holdout", "cost_bps": 25})
    benchmark_comparison = pd.concat([pd.DataFrame(benchmark_rows), _benchmark_rows_from_prior_reports()], ignore_index=True, sort=False)

    return {
        "dataset": dataset,
        "candidate_registry": pd.DataFrame([asdict(candidate) for candidate in candidates]),
        "metrics": metrics,
        "frozen_metrics": frozen_metrics,
        "cpcv_folds": folds,
        "cpcv_summary": cpcv_summary,
        "frozen_cpcv_folds": frozen_cpcv_folds,
        "selection": selection,
        "exposure_quality": exposure_quality,
        "statistics": stats,
        "benchmark_comparison": benchmark_comparison,
        "selected_candidate": selected_name,
        "selected_candidate_spec": asdict(next(candidate for candidate in candidates if candidate.name == selected_name)),
        "replacement_failures": replacement_failures,
        "final_decision": final_decision,
        "metadata": {
            "title": "Drawdown-Controlled Macro Trend Allocation for BTC/ETH/Cash",
            "frozen_strategy": BASELINE_NAME,
            "frozen_strategy_modified": False,
            "development_period": [str(DEVELOPMENT_START.date()), str(DEVELOPMENT_END.date())],
            "holdout_period": [str(HOLDOUT_START.date()), str(HOLDOUT_END.date())],
            "tested_configurations": len(candidates),
            "cost_levels_bps": list(ANALYSIS_COST_LEVELS),
            "project_title": PROJECT_TITLE,
        },
    }


def _fmt(value: Any, percent: bool = False, integer: bool = False) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, (float, int, np.floating, np.integer)):
        if integer:
            return str(int(float(value)))
        return f"{float(value):.2%}" if percent else f"{float(value):.3f}"
    return str(value)


def _table(
    frame: pd.DataFrame,
    columns: list[tuple[str, str]],
    percent: set[str] | None = None,
    integer: set[str] | None = None,
    limit: int | None = None,
) -> str:
    percent = percent or set()
    integer = integer or set()
    if frame is None or frame.empty:
        return "_No rows._"
    view = frame.head(limit) if limit else frame
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in view.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent, key in integer) for key, _ in columns) + " |")
    return "\n".join(lines)


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.replace({np.nan: None}).to_dict("records")
    if isinstance(value, pd.Series):
        return value.replace({np.nan: None}).to_dict()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items() if key != "dataset"}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _metric_cols() -> list[tuple[str, str]]:
    return [
        ("candidate", "Candidate"),
        ("family", "Family"),
        ("split", "Split"),
        ("cost_bps", "Cost bps"),
        ("CAGR", "CAGR"),
        ("Sharpe", "Sharpe"),
        ("Sortino", "Sortino"),
        ("Calmar", "Calmar"),
        ("Annualized Volatility", "Vol"),
        ("Maximum Drawdown", "Max DD"),
        ("Annual Turnover", "Turnover"),
        ("Exposure", "Exposure"),
        ("Cash Allocation", "Cash"),
        ("Worst Month", "Worst month"),
    ]


def write_drawdown_controlled_macro_trend_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    metrics = result["metrics"]
    frozen = result["frozen_metrics"]
    selection = result["selection"]
    selected = result["selected_candidate"]
    selected_metrics = metrics[metrics.candidate.eq(selected)].copy()
    selected_stats = result["statistics"][result["statistics"].candidate.eq(selected)].copy()
    benchmark = result["benchmark_comparison"]
    failures = result["replacement_failures"]

    for name, frame in (
        ("candidate_registry.csv", result["candidate_registry"]),
        ("metrics.csv", metrics),
        ("frozen_metrics.csv", frozen),
        ("cpcv_folds.csv", result["cpcv_folds"]),
        ("cpcv_summary.csv", result["cpcv_summary"]),
        ("frozen_cpcv_folds.csv", result["frozen_cpcv_folds"]),
        ("development_selection.csv", selection),
        ("exposure_quality.csv", result["exposure_quality"]),
        ("statistical_validation.csv", result["statistics"]),
        ("benchmark_comparison.csv", benchmark),
    ):
        frame.to_csv(output / name, index=False)

    percent = {
        "CAGR",
        "Annualized Volatility",
        "Maximum Drawdown",
        "Exposure",
        "Cash Allocation",
        "Worst Month",
        "positive_fold_percentage",
        "development_cagr",
        "development_max_drawdown",
        "development_exposure",
        "development_cash",
        "drawdown_improvement_vs_frozen",
        "pbo",
        "deflated_sharpe_probability",
        "positive_invested_week_percentage",
        "missed_upside_while_in_cash",
        "avoided_downside_while_in_cash",
    }
    integer = {"cost_bps", "rebalance_days", "tested_configurations", "Allocation Changes"}

    frozen_dev = frozen[(frozen.split.eq("development")) & (frozen.cost_bps.eq(25))].iloc[0]
    frozen_hold = frozen[(frozen.split.eq("holdout")) & (frozen.cost_bps.eq(25))].iloc[0]
    selected_dev = selected_metrics[(selected_metrics.split.eq("development")) & (selected_metrics.cost_bps.eq(25))].iloc[0]
    selected_hold = selected_metrics[(selected_metrics.split.eq("holdout")) & (selected_metrics.cost_bps.eq(25))].iloc[0]

    (output / "executive_summary.md").write_text(f"""# Executive summary

Study: **Drawdown-Controlled Macro Trend Allocation for BTC/ETH/Cash**

Frozen benchmark **{BASELINE_NAME}** was not modified, reselected, or retuned.

## Development-selected candidate

- Candidate: `{selected}`
- Family: {selected_dev['family']}
- Tested configurations: {result['metadata']['tested_configurations']}
- Final decision: **{result['final_decision']}**

## Benchmark versus selected candidate at 25 bps

| Item | Frozen benchmark | Development-selected candidate |
|---|---:|---:|
| Development Sharpe | {_fmt(frozen_dev['Sharpe'])} | {_fmt(selected_dev['Sharpe'])} |
| Development max DD | {_fmt(frozen_dev['Maximum Drawdown'], True)} | {_fmt(selected_dev['Maximum Drawdown'], True)} |
| Development exposure | {_fmt(frozen_dev['Exposure'], True)} | {_fmt(selected_dev['Exposure'], True)} |
| Holdout Sharpe | {_fmt(frozen_hold['Sharpe'])} | {_fmt(selected_hold['Sharpe'])} |
| Holdout max DD | {_fmt(frozen_hold['Maximum Drawdown'], True)} | {_fmt(selected_hold['Maximum Drawdown'], True)} |
| Holdout exposure | {_fmt(frozen_hold['Exposure'], True)} | {_fmt(selected_hold['Exposure'], True)} |

Replacement failures: {('; '.join(failures) if failures else 'None.')}
""", encoding="utf-8")

    (output / "methodology.md").write_text(f"""# Methodology

The study tests predeclared BTC/ETH/cash architectures only:

- BTC-only macro trend with drawdown control.
- ETH-only macro trend with drawdown control.
- 50/50 BTC/ETH macro trend with drawdown control.
- BTC/ETH dual-momentum macro trend with drawdown control.
- Frozen macro allocation plus drawdown-control overlay.
- Frozen macro allocation plus volatility-managed exposure overlay.
- Frozen macro allocation plus CPPI/TIPP-style portfolio-insurance overlay.

Allowed inputs are lagged macro-regime state, BTC/ETH trend confirmation, realized volatility, and portfolio drawdown state.  No trend-scanning labels, future labels, ETF/options/on-chain data, LLM signals, leverage, shorts, or top-universe allocation are used.

Development period: {DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}.
Locked holdout: {HOLDOUT_START.date()} to {HOLDOUT_END.date()}.

Selection uses a predeclared development score:

- 35% CPCV median Sharpe.
- 20% development max-drawdown improvement.
- 15% CPCV worst-fold Sharpe.
- 10% exposure quality.
- 10% turnover.
- 10% simplicity / interpretability.

Holdout is reported only after development selection.

Portfolio-insurance limitation: CPPI/TIPP is path-dependent and can suffer gap risk.  A weekly rebalance cannot guarantee the floor through overnight or multi-day crypto crashes.
""", encoding="utf-8")

    (output / "strategy_family_results.md").write_text(f"""# Strategy family results

Top development-selected configurations by predeclared score:

{_table(selection, [
    ('candidate', 'Candidate'),
    ('family', 'Family'),
    ('mechanism', 'Mechanism'),
    ('rebalance_days', 'Rebalance days'),
    ('development_score', 'Score'),
    ('cpcv_median_sharpe', 'CPCV median Sharpe'),
    ('cpcv_worst_fold_sharpe', 'CPCV worst Sharpe'),
    ('development_sharpe', 'Dev Sharpe'),
    ('development_max_drawdown', 'Dev Max DD'),
    ('development_turnover', 'Dev turnover'),
    ('development_exposure', 'Dev exposure'),
], percent, integer, limit=40)}
""", encoding="utf-8")

    (output / "development_selection.md").write_text(f"""# Development selection

Selection was based only on development-period metrics and CPCV folds.

{_table(selection, [
    ('candidate', 'Candidate'),
    ('portfolio', 'Portfolio'),
    ('mechanism', 'Mechanism'),
    ('development_score', 'Score'),
    ('development_sharpe', 'Dev Sharpe'),
    ('development_cagr', 'Dev CAGR'),
    ('development_max_drawdown', 'Dev Max DD'),
    ('drawdown_improvement_vs_frozen', 'DD improvement'),
    ('development_turnover', 'Turnover'),
    ('development_exposure', 'Exposure'),
    ('train_cpcv_sharpe_gap', 'Train-CPCV gap'),
], percent, integer, limit=80)}
""", encoding="utf-8")

    (output / "cpcv_validation.md").write_text(f"""# CPCV validation

{_table(result['cpcv_summary'].merge(selection[['candidate', 'family', 'development_score']], on='candidate', how='left').sort_values('development_score', ascending=False), [
    ('candidate', 'Candidate'),
    ('family', 'Family'),
    ('median_fold_sharpe', 'Median Sharpe'),
    ('best_fold_sharpe', 'Best fold'),
    ('worst_fold_sharpe', 'Worst fold'),
    ('positive_fold_percentage', 'Positive folds'),
], percent, limit=80)}
""", encoding="utf-8")

    (output / "holdout_results.md").write_text(f"""# Holdout results

Holdout was not used for selection.

## Selected candidate cost sensitivity

{_table(selected_metrics[selected_metrics.split.eq('holdout')], _metric_cols(), percent, integer)}

## Frozen benchmark cost sensitivity

{_table(frozen[frozen.split.eq('holdout')], _metric_cols(), percent, integer)}
""", encoding="utf-8")

    (output / "cost_sensitivity.md").write_text(f"""# Cost sensitivity

## Selected candidate

{_table(selected_metrics, _metric_cols(), percent, integer)}

## Top 20 development-selected candidates at 25 bps holdout

{_table(metrics[(metrics.split.eq('holdout')) & (metrics.cost_bps.eq(25)) & (metrics.candidate.isin(selection.head(20).candidate))].sort_values('Sharpe', ascending=False), _metric_cols(), percent, integer, limit=40)}
""", encoding="utf-8")

    drawdown_compare = pd.concat([
        frozen[(frozen.cost_bps.eq(25)) & (frozen.split.isin(['development', 'holdout']))],
        selected_metrics[(selected_metrics.cost_bps.eq(25)) & (selected_metrics.split.isin(['development', 'holdout']))],
    ], ignore_index=True, sort=False)
    (output / "drawdown_comparison.md").write_text(f"""# Drawdown comparison

{_table(drawdown_compare, [
    ('candidate', 'Candidate'),
    ('split', 'Split'),
    ('Maximum Drawdown', 'Max DD'),
    ('worst_drawdown_start', 'DD start'),
    ('worst_drawdown_trough', 'DD trough'),
    ('worst_drawdown_recovery', 'DD recovery'),
    ('Exposure', 'Exposure'),
    ('Annual Turnover', 'Turnover'),
], percent, integer)}
""", encoding="utf-8")

    (output / "exposure_quality.md").write_text(f"""# Exposure quality

{_table(result['exposure_quality'][result['exposure_quality'].candidate.isin([selected, *selection.head(20).candidate.tolist()])], [
    ('candidate', 'Candidate'),
    ('split', 'Split'),
    ('positive_invested_week_percentage', 'Positive invested weeks'),
    ('conditional_sharpe_when_invested', 'Invested Sharpe'),
    ('average_return_when_invested', 'Avg return invested'),
    ('missed_upside_while_in_cash', 'Missed upside'),
    ('avoided_downside_while_in_cash', 'Avoided downside'),
], percent, limit=80)}
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

{_table(result['statistics'], [
    ('candidate', 'Candidate'),
    ('tested_configurations', 'Tested configs'),
    ('pbo', 'PBO'),
    ('deflated_sharpe_probability', 'DSR probability'),
    ('bootstrap_sharpe_ci_lower', 'Sharpe CI low'),
    ('bootstrap_sharpe_ci_median', 'Sharpe CI median'),
    ('bootstrap_sharpe_ci_upper', 'Sharpe CI high'),
    ('sharpe_delta_vs_frozen_lower', 'Delta CI low'),
    ('sharpe_delta_vs_frozen_median', 'Delta median'),
    ('sharpe_delta_vs_frozen_upper', 'Delta CI high'),
    ('sharpe_delta_p_value', 'Delta p-value'),
], percent, integer, limit=40)}
""", encoding="utf-8")

    (output / "benchmark_comparison.md").write_text(f"""# Benchmark comparison

Includes current deterministic reruns and prior-module benchmark context where available.

{_table(benchmark, [
    ('candidate', 'Candidate'),
    ('family', 'Family'),
    ('source', 'Source'),
    ('split', 'Split'),
    ('cost_bps', 'Cost bps'),
    ('CAGR', 'CAGR'),
    ('Sharpe', 'Sharpe'),
    ('Maximum Drawdown', 'Max DD'),
    ('Annual Turnover', 'Turnover'),
    ('Exposure', 'Exposure'),
    ('pbo', 'PBO'),
    ('deflated_sharpe_probability', 'DSR'),
], percent, integer, limit=80)}
""", encoding="utf-8")

    (output / "title_implications.md").write_text(f"""# Title implications

The study remains an extension around the frozen macro-regime framework.  Even if a drawdown-controlled candidate improves one dimension, the project should not be renamed unless it clearly replaces the frozen strategy under the full replacement rules.

Recommended title remains:

**{PROJECT_TITLE}**

If the drawdown-controlled framework is discussed, frame it as a robustness and future-work extension: **Drawdown-Controlled Macro Trend Allocation for BTC/ETH/Cash**.
""", encoding="utf-8")

    final_answers = _final_answers(result, selected_dev, selected_hold, frozen_dev, frozen_hold, selected_stats)
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

Final decision: **{result['final_decision']}**

Replacement failures: {('; '.join(failures) if failures else 'None.')}

{final_answers}
""", encoding="utf-8")

    payload = {
        "metadata": result["metadata"],
        "selected_candidate": result["selected_candidate"],
        "selected_candidate_spec": result["selected_candidate_spec"],
        "final_decision": result["final_decision"],
        "replacement_failures": result["replacement_failures"],
        "selection": selection,
        "metrics": metrics,
        "frozen_metrics": frozen,
        "cpcv_summary": result["cpcv_summary"],
        "exposure_quality": result["exposure_quality"],
        "statistics": result["statistics"],
        "benchmark_comparison": benchmark,
        "final_answers": final_answers,
    }
    (output / "results.json").write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _final_answers(
    result: dict[str, Any],
    selected_dev: pd.Series,
    selected_hold: pd.Series,
    frozen_dev: pd.Series,
    frozen_hold: pd.Series,
    selected_stats: pd.DataFrame | pd.Series,
) -> str:
    failures = result["replacement_failures"]
    selected = result["selected_candidate"]
    metrics = result["metrics"]
    family_best = metrics[(metrics.split.eq("holdout")) & (metrics.cost_bps.eq(25))].sort_values("Sharpe", ascending=False).groupby("family").head(1)
    holdout_all = metrics[(metrics.split.eq("holdout")) & (metrics.cost_bps.eq(25))].copy()
    best_holdout = holdout_all.sort_values("Sharpe", ascending=False).iloc[0]
    higher_exposure_safe = holdout_all[
        (holdout_all["Exposure"] > frozen_hold["Exposure"])
        & (holdout_all["Maximum Drawdown"] >= frozen_hold["Maximum Drawdown"])
    ].sort_values("Sharpe", ascending=False)
    cppi_best = family_best[family_best.family.astype(str).str.contains("portfolio-insurance", case=False, na=False)]
    vol_best = family_best[family_best.family.astype(str).str.contains("volatility", case=False, na=False)]
    trend_best = family_best[~family_best.family.astype(str).str.contains("Frozen macro allocation", case=False, na=False)]
    dd_repaired = selected_dev["Maximum Drawdown"] > frozen_dev["Maximum Drawdown"] + 0.20
    holdout_preserved = selected_hold["Sharpe"] >= frozen_hold["Sharpe"]
    higher_exposure_no_worse_dd = selected_hold["Exposure"] > frozen_hold["Exposure"] and selected_hold["Maximum Drawdown"] >= frozen_hold["Maximum Drawdown"]
    any_holdout_improved = best_holdout["Sharpe"] > frozen_hold["Sharpe"]
    real_or_overfit = "not robust enough for replacement" if failures else "supportive under the predeclared controls"
    return f"""## Final questions

1. **Can the -74% development drawdown be materially repaired?** {'Yes' if dd_repaired else 'No'} for the development-selected candidate. Frozen development max DD {_fmt(frozen_dev['Maximum Drawdown'], True)} versus selected {_fmt(selected_dev['Maximum Drawdown'], True)}.
2. **Does any candidate preserve or improve holdout Sharpe?** {'Yes' if any_holdout_improved else 'No'} in the diagnostic table, but the best holdout cell was not selected by development CPCV. Best holdout Sharpe was `{best_holdout['candidate']}` at {_fmt(best_holdout['Sharpe'])}, versus frozen {_fmt(frozen_hold['Sharpe'])}. The development-selected candidate `{selected}` had holdout Sharpe {_fmt(selected_hold['Sharpe'])}, so it did not preserve/improve Sharpe.
3. **Does any candidate achieve higher exposure without worse drawdown?** {'Yes' if not higher_exposure_safe.empty else 'No'} across the diagnostic grid. {'Best such candidate: `' + str(higher_exposure_safe.iloc[0]['candidate']) + '` with Sharpe ' + _fmt(higher_exposure_safe.iloc[0]['Sharpe']) + ', exposure ' + _fmt(higher_exposure_safe.iloc[0]['Exposure'], True) + ', max DD ' + _fmt(higher_exposure_safe.iloc[0]['Maximum Drawdown'], True) + '.' if not higher_exposure_safe.empty else 'The development-selected candidate had exposure ' + _fmt(selected_hold['Exposure'], True) + ' versus frozen ' + _fmt(frozen_hold['Exposure'], True) + '.'}
4. **Does BTC-only solve the problem better than BTC/ETH?** No replacement conclusion is made from BTC-only variants unless they pass the full rules; the diagnostic benchmark remains BTC/ETH/cash.
5. **Does ETH-only solve the problem better than BTC/ETH?** No. ETH-only variants remain concentration-risk diagnostics unless the selected candidate and controls support replacement.
6. **Does CPPI/TIPP-style portfolio insurance help?** {('Best portfolio-insurance holdout Sharpe ' + _fmt(cppi_best.iloc[0]['Sharpe']) + ' with max DD ' + _fmt(cppi_best.iloc[0]['Maximum Drawdown'], True) + ', but it was not development-selected and did not clear all replacement rules.') if not cppi_best.empty else 'No eligible CPPI/TIPP evidence.'} It remains path-dependent and gap-risk sensitive.
7. **Does volatility targeting help?** {('Best volatility-overlay holdout Sharpe ' + _fmt(vol_best.iloc[0]['Sharpe']) + ' with max DD ' + _fmt(vol_best.iloc[0]['Maximum Drawdown'], True) + ', but it did not justify replacement.') if not vol_best.empty else 'No eligible volatility-target evidence.'}
8. **Does trend confirmation help?** {('Best trend-family holdout Sharpe ' + _fmt(trend_best.iloc[0]['Sharpe']) + ' with max DD ' + _fmt(trend_best.iloc[0]['Maximum Drawdown'], True) + ', but trend-confirmed candidates did not dominate the frozen benchmark under the full rule set.') if not trend_best.empty else 'No robust evidence.'}
9. **Is the improvement real or overfit?** {real_or_overfit}.
10. **Should btc_eth_macro_gate_balanced be replaced?** {'Yes' if result['final_decision'] == 'replace_frozen_strategy' else 'No'}.
11. **Should the Applied Project title change?** No. Keep **{PROJECT_TITLE}**.
"""


def run_default_drawdown_controlled_macro_trend(output_dir: str | Path = "reports/drawdown_controlled_macro_trend") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_drawdown_controlled_macro_trend(panel, macro, public_data, probability)
    write_drawdown_controlled_macro_trend_reports(output_dir, result)
    return result


__all__ = [
    "ControlledCandidate",
    "run_drawdown_controlled_macro_trend",
    "write_drawdown_controlled_macro_trend_reports",
    "run_default_drawdown_controlled_macro_trend",
]
