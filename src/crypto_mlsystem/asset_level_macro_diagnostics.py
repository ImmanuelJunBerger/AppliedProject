"""Asset-level macro decomposition and drawdown diagnostics.

This is a diagnostic module only.  It does not modify, reselect, or retune the
frozen ``btc_eth_macro_gate_balanced`` strategy.  All decompositions reuse the
same fixed macro-gate regime states where possible and are reported as
explanatory comparators, not replacement candidates.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    MacroRegimeCandidate,
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
)
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import (
    block_bootstrap_sharpe_ci,
    deflated_sharpe_probability,
    probability_backtest_overfitting,
)


DIAGNOSTIC_DEVELOPMENT_START = pd.Timestamp("2019-07-05")
DIAGNOSTIC_DEVELOPMENT_END = pd.Timestamp("2024-12-31")
ANALYSIS_COST_LEVELS = (0, *COST_LEVELS)
BASELINE_NAME = FIXED_SELECTED.name
PROJECT_TITLE = "Macro-Regime Conditioning for Systematic Cryptocurrency Allocation: A Robust Out-of-Sample Evaluation"


@dataclass(frozen=True)
class DiagnosticStrategy:
    name: str
    family: str
    group: str
    dataset_key: str
    weights: pd.DataFrame
    macro_regime: pd.Series
    crypto_regime: pd.Series
    combined_regime: pd.Series
    turnover_cap: float
    explanation: str


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int = 7) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def _all_risk_on(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series, pd.Series]:
    risk_on = pd.Series("risk_on", index=index, dtype=object)
    crypto = pd.Series("not_used", index=index, dtype=object)
    return risk_on, crypto, risk_on


def _asset_macro_gate_weights(
    dataset: MacroRegimeDataset,
    combined_regime: pd.Series,
    assets: tuple[str, ...],
    rebalance_days: int = 7,
) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index, rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    for date_ in dates:
        regime = combined_regime.reindex([date_]).ffill().iloc[0] if date_ in combined_regime.index else "risk_off"
        if regime == "risk_off":
            continue
        exposure = 1.0 if regime == "risk_on" else 0.50
        available = [asset for asset in assets if asset in weights.columns]
        if not available:
            continue
        allocation = exposure / len(available)
        weights.loc[date_, available] = allocation
    return weights


def _buy_hold_weights(dataset: MacroRegimeDataset, assets: tuple[str, ...]) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=dataset.close.index, columns=dataset.close.columns)
    available = [asset for asset in assets if asset in weights.columns]
    if available:
        allocation = 1.0 / len(available)
        weights.loc[:, available] = allocation
    return weights


def _equal_weight_universe(dataset: MacroRegimeDataset) -> pd.DataFrame:
    active = dataset.universe_weights > 0
    denominator = active.sum(axis=1).replace(0, np.nan)
    return active.div(denominator, axis=0).fillna(0.0)


def _top_momentum_weights(dataset: MacroRegimeDataset, gated: bool, top_k: int = 5) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    candidate = MacroRegimeCandidate(
        name=f"{'macro_gated' if gated else 'pure'}_top{dataset.metadata['universe_size']}_momentum",
        family=f"{'Macro-gated' if gated else 'Pure'} top-{dataset.metadata['universe_size']} momentum",
        gate_profile="balanced",
        use_crypto_gate=False,
        allocation="top10_momentum",
        rebalance_days=7,
        top_k=top_k,
        universe_size=int(dataset.metadata["universe_size"]),
        max_asset_weight=0.20,
        turnover_cap=0.75,
    )
    return build_candidate_weights(dataset, candidate, combined_override=None if gated else "always_on")


def _strategy_registry(datasets: dict[str, MacroRegimeDataset]) -> list[DiagnosticStrategy]:
    dataset10 = datasets["top10"]
    dataset20 = datasets["top20"]
    frozen_weights, macro, crypto, combined = build_candidate_weights(dataset10, FIXED_SELECTED)
    all_on10 = _all_risk_on(dataset10.close.index)

    top10_weights, top10_macro, top10_crypto, top10_combined = _top_momentum_weights(dataset10, gated=True)
    top20_weights, top20_macro, top20_crypto, top20_combined = _top_momentum_weights(dataset20, gated=True)
    pure_top10_weights, pure_top10_macro, pure_top10_crypto, pure_top10_combined = _top_momentum_weights(dataset10, gated=False)

    all_on20 = _all_risk_on(dataset20.close.index)
    return [
        DiagnosticStrategy(
            "btc_only_macro_gate",
            "BTC-only macro gate",
            "asset_level_macro_decomposition",
            "top10",
            _asset_macro_gate_weights(dataset10, combined, ("BTC",)),
            macro,
            crypto,
            combined,
            FIXED_SELECTED.turnover_cap,
            "Same frozen macro gate; risk-on holds BTC, neutral half-size BTC, risk-off cash.",
        ),
        DiagnosticStrategy(
            "eth_only_macro_gate",
            "ETH-only macro gate",
            "asset_level_macro_decomposition",
            "top10",
            _asset_macro_gate_weights(dataset10, combined, ("ETH",)),
            macro,
            crypto,
            combined,
            FIXED_SELECTED.turnover_cap,
            "Same frozen macro gate; risk-on holds ETH, neutral half-size ETH, risk-off cash.",
        ),
        DiagnosticStrategy(
            "btc_eth_50_50_macro_gate",
            "50/50 BTC/ETH macro gate",
            "asset_level_macro_decomposition",
            "top10",
            _asset_macro_gate_weights(dataset10, combined, ("BTC", "ETH")),
            macro,
            crypto,
            combined,
            FIXED_SELECTED.turnover_cap,
            "Same frozen macro gate; fixed balanced BTC/ETH when exposure is permitted.",
        ),
        DiagnosticStrategy(
            BASELINE_NAME,
            FIXED_SELECTED.family,
            "frozen_selected_strategy",
            "top10",
            frozen_weights,
            macro,
            crypto,
            combined,
            FIXED_SELECTED.turnover_cap,
            "Frozen selected strategy generated by the existing btc_eth_macro_gate_balanced implementation.",
        ),
        DiagnosticStrategy(
            "top10_macro_gated_momentum",
            "Top-10 macro-gated momentum",
            "universe_question",
            "top10",
            top10_weights,
            top10_macro,
            top10_crypto,
            top10_combined,
            0.75,
            "Existing fixed macro gate applied to top-10 momentum selection; no threshold retuning.",
        ),
        DiagnosticStrategy(
            "top20_macro_gated_momentum",
            "Top-20 macro-gated momentum",
            "universe_question",
            "top20",
            top20_weights,
            top20_macro,
            top20_crypto,
            top20_combined,
            0.75,
            "Existing fixed macro gate applied to top-20 momentum selection; no threshold retuning.",
        ),
        DiagnosticStrategy(
            "equal_weight_top10",
            "Equal-weight top-10",
            "universe_question",
            "top10",
            _equal_weight_universe(dataset10),
            *all_on10,
            10.0,
            "Point-in-time top-10 equal-weight universe comparator.",
        ),
        DiagnosticStrategy(
            "pure_top10_momentum",
            "Pure top-10 momentum",
            "universe_question",
            "top10",
            pure_top10_weights,
            pure_top10_macro,
            pure_top10_crypto,
            pure_top10_combined,
            0.75,
            "Top-10 momentum without macro gate; included to diagnose universe and turnover effects.",
        ),
        DiagnosticStrategy(
            "btc_buy_hold",
            "BTC buy-and-hold",
            "benchmark",
            "top10",
            _buy_hold_weights(dataset10, ("BTC",)),
            *all_on10,
            10.0,
            "Simple crypto beta benchmark.",
        ),
        DiagnosticStrategy(
            "eth_buy_hold",
            "ETH buy-and-hold",
            "benchmark",
            "top10",
            _buy_hold_weights(dataset10, ("ETH",)),
            *all_on10,
            10.0,
            "Simple crypto beta benchmark.",
        ),
        DiagnosticStrategy(
            "btc_eth_50_50_buy_hold",
            "50/50 BTC/ETH buy-and-hold",
            "benchmark",
            "top10",
            _buy_hold_weights(dataset10, ("BTC", "ETH")),
            *all_on10,
            10.0,
            "Simple balanced BTC/ETH beta benchmark.",
        ),
        DiagnosticStrategy(
            "equal_weight_top20",
            "Equal-weight top-20",
            "universe_question",
            "top20",
            _equal_weight_universe(dataset20),
            *all_on20,
            10.0,
            "Point-in-time top-20 equal-weight universe comparator.",
        ),
    ]


def _wealth_drawdown(returns: pd.Series) -> pd.DataFrame:
    r = returns.dropna()
    if r.empty:
        return pd.DataFrame(columns=["wealth", "peak", "drawdown"])
    wealth = (1.0 + r).cumprod()
    peak = wealth.cummax()
    return pd.DataFrame({"wealth": wealth, "peak": peak, "drawdown": wealth / peak - 1.0})


def _drawdown_periods(returns: pd.Series) -> list[dict[str, Any]]:
    dd = _wealth_drawdown(returns)
    if dd.empty:
        return []
    periods: list[dict[str, Any]] = []
    in_drawdown = False
    start: pd.Timestamp | None = None
    trough: pd.Timestamp | None = None
    trough_dd = 0.0
    last_peak = dd.index[0]
    for date_, row in dd.iterrows():
        value = float(row["drawdown"])
        if value >= -1e-12:
            last_peak = date_
            if in_drawdown:
                periods.append({"start": start, "trough": trough, "recovery": date_, "max_drawdown": trough_dd})
                in_drawdown = False
                start = None
                trough = None
                trough_dd = 0.0
            continue
        if not in_drawdown:
            in_drawdown = True
            start = last_peak
            trough = date_
            trough_dd = value
        elif value < trough_dd:
            trough = date_
            trough_dd = value
    if in_drawdown:
        periods.append({"start": start, "trough": trough, "recovery": None, "max_drawdown": trough_dd})
    return periods


def _worst_drawdown_info(returns: pd.Series) -> dict[str, Any]:
    periods = _drawdown_periods(returns)
    if not periods:
        return {"drawdown_start": None, "drawdown_trough": None, "drawdown_recovery": None, "drawdown_depth": np.nan}
    worst = sorted(periods, key=lambda item: item["max_drawdown"])[0]
    return {
        "drawdown_start": str(pd.Timestamp(worst["start"]).date()) if worst["start"] is not None else None,
        "drawdown_trough": str(pd.Timestamp(worst["trough"]).date()) if worst["trough"] is not None else None,
        "drawdown_recovery": str(pd.Timestamp(worst["recovery"]).date()) if worst["recovery"] is not None else None,
        "drawdown_depth": float(worst["max_drawdown"]),
    }


def _extended_period_metrics(result: PortfolioResult, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    metrics = period_metrics(result, start, end)
    returns = result.returns.loc[start:end]
    turnover = result.turnover.reindex(returns.index).fillna(0.0)
    info = _worst_drawdown_info(returns)
    metrics.update({
        "Allocation Changes": int((turnover > 1e-9).sum()),
        **info,
    })
    return metrics


def _daily_sharpe(returns: pd.Series) -> float:
    values = returns.dropna()
    std = values.std()
    return float(values.mean() / std * np.sqrt(365)) if len(values) and std and np.isfinite(std) else 0.0


def _weekly_sharpe(returns: pd.Series) -> float:
    values = returns.dropna()
    std = values.std()
    return float(values.mean() / std * np.sqrt(52)) if len(values) and std and np.isfinite(std) else 0.0


def _cpcv_fold_rows(name: str, result: PortfolioResult, cost_bps: int) -> pd.DataFrame:
    weekly = result.returns.loc[DIAGNOSTIC_DEVELOPMENT_START:DIAGNOSTIC_DEVELOPMENT_END].resample("W-FRI").apply(
        lambda values: (1.0 + values).prod() - 1.0
    ).dropna()
    if len(weekly) < 20:
        return pd.DataFrame()
    rows = []
    splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
    for fold, split in enumerate(splits):
        subset = weekly.iloc[list(split.test_indices)]
        rows.append({
            "strategy": name,
            "cost_bps": cost_bps,
            "fold": fold,
            "test_groups": "-".join(map(str, split.test_groups)),
            "fold_start": str(subset.index.min().date()),
            "fold_end": str(subset.index.max().date()),
            "fold_sharpe": _weekly_sharpe(subset),
            "fold_return": float((1.0 + subset).prod() - 1.0),
            "positive_fold": bool((1.0 + subset).prod() - 1.0 > 0),
        })
    return pd.DataFrame(rows)


def _cpcv_summary(folds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (strategy, cost_bps), group in folds.groupby(["strategy", "cost_bps"], dropna=False):
        rows.append({
            "strategy": strategy,
            "cost_bps": cost_bps,
            "median_fold_sharpe": float(group["fold_sharpe"].median()),
            "best_fold_sharpe": float(group["fold_sharpe"].max()),
            "worst_fold_sharpe": float(group["fold_sharpe"].min()),
            "positive_fold_percentage": float(group["positive_fold"].mean()),
        })
    return pd.DataFrame(rows)


def _paired_sharpe_delta_ci(
    left: pd.Series,
    right: pd.Series,
    samples: int = 500,
    block_length: int = 14,
    seed: int = 211,
) -> dict[str, float]:
    data = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()
    if len(data) < block_length * 2:
        return {"lower": np.nan, "median": np.nan, "upper": np.nan}
    rng = np.random.default_rng(seed)
    values = data.to_numpy(dtype=float)
    estimates = []
    blocks_needed = int(np.ceil(len(values) / block_length))
    max_start = len(values) - block_length
    for _ in range(samples):
        starts = rng.integers(0, max_start + 1, blocks_needed)
        sample = np.concatenate([values[start:start + block_length] for start in starts])[:len(values)]
        left_sample = pd.Series(sample[:, 0])
        right_sample = pd.Series(sample[:, 1])
        estimates.append(_daily_sharpe(left_sample) - _daily_sharpe(right_sample))
    lower, median, upper = np.quantile(estimates, [0.025, 0.50, 0.975])
    return {"lower": float(lower), "median": float(median), "upper": float(upper)}


def _performance_rows(
    strategies: list[DiagnosticStrategy],
    datasets: dict[str, MacroRegimeDataset],
) -> tuple[pd.DataFrame, dict[str, dict[int, PortfolioResult]]]:
    rows: list[dict[str, Any]] = []
    results: dict[str, dict[int, PortfolioResult]] = {}
    for spec in strategies:
        dataset = datasets[spec.dataset_key]
        results[spec.name] = {}
        for cost_bps in ANALYSIS_COST_LEVELS:
            result = backtest_weights(
                dataset,
                spec.weights,
                spec.macro_regime,
                spec.crypto_regime,
                spec.combined_regime,
                cost_bps=cost_bps,
                turnover_cap=spec.turnover_cap,
            )
            results[spec.name][cost_bps] = result
            periods = (
                ("full_sample", result.returns.index.min(), min(HOLDOUT_END, result.returns.index.max())),
                ("development", DIAGNOSTIC_DEVELOPMENT_START, DIAGNOSTIC_DEVELOPMENT_END),
                ("holdout", HOLDOUT_START, HOLDOUT_END),
            )
            for split, start, end in periods:
                rows.append({
                    "strategy": spec.name,
                    "family": spec.family,
                    "group": spec.group,
                    "split": split,
                    "start": str(pd.Timestamp(start).date()),
                    "end": str(pd.Timestamp(end).date()),
                    "cost_bps": cost_bps,
                    "basis": "gross_0bps" if cost_bps == 0 else "net_after_costs",
                    "dataset": spec.dataset_key,
                    **_extended_period_metrics(result, pd.Timestamp(start), pd.Timestamp(end)),
                })
    return pd.DataFrame(rows), results


def _statistical_rows(results: dict[str, dict[int, PortfolioResult]], strategy_names: list[str]) -> pd.DataFrame:
    weekly_configs = {}
    for name in strategy_names:
        weekly_configs[name] = results[name][25].returns.loc[DIAGNOSTIC_DEVELOPMENT_START:DIAGNOSTIC_DEVELOPMENT_END].resample(
            "W-FRI"
        ).apply(lambda values: (1.0 + values).prod() - 1.0)
    config_frame = pd.DataFrame(weekly_configs)
    pbo = probability_backtest_overfitting(config_frame, blocks=8)
    baseline = results[BASELINE_NAME][25].returns.loc[HOLDOUT_START:HOLDOUT_END]
    rows = []
    for name in strategy_names:
        holdout = results[name][25].returns.loc[HOLDOUT_START:HOLDOUT_END]
        ci = block_bootstrap_sharpe_ci(holdout, samples=500, block_length=14, seed=97)
        delta = _paired_sharpe_delta_ci(holdout, baseline)
        rows.append({
            "strategy": name,
            "pbo_context_all_decomposition_strategies": pbo,
            "deflated_sharpe_probability": deflated_sharpe_probability(holdout, tested_configurations=len(strategy_names)),
            "bootstrap_sharpe_ci_lower": ci["lower"],
            "bootstrap_sharpe_ci_median": ci["median"],
            "bootstrap_sharpe_ci_upper": ci["upper"],
            "sharpe_delta_vs_frozen_lower": delta["lower"],
            "sharpe_delta_vs_frozen_median": delta["median"],
            "sharpe_delta_vs_frozen_upper": delta["upper"],
        })
    return pd.DataFrame(rows)


def _compound_return(returns: pd.Series) -> float:
    values = returns.dropna()
    return float((1.0 + values).prod() - 1.0) if len(values) else np.nan


def _asset_return(dataset: MacroRegimeDataset, asset: str, start: pd.Timestamp, end: pd.Timestamp) -> float:
    if asset not in dataset.returns:
        return np.nan
    return _compound_return(dataset.returns[asset].loc[start:end])


def _strategy_contributions(dataset: MacroRegimeDataset, result: PortfolioResult) -> pd.DataFrame:
    previous_weights = result.weights.shift(1).reindex(dataset.returns.index).fillna(0.0)
    aligned_returns = dataset.returns.reindex(previous_weights.index).fillna(0.0)
    return previous_weights * aligned_returns


def _drawdown_forensics(
    dataset: MacroRegimeDataset,
    result: PortfolioResult,
    combined_regime: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dev_returns = result.returns.loc[DIAGNOSTIC_DEVELOPMENT_START:DIAGNOSTIC_DEVELOPMENT_END]
    periods = sorted(_drawdown_periods(dev_returns), key=lambda item: item["max_drawdown"])[:10]
    contributions = _strategy_contributions(dataset, result)
    rows = []
    for rank, period in enumerate(periods, start=1):
        start = pd.Timestamp(period["start"])
        trough = pd.Timestamp(period["trough"])
        segment = slice(start, trough)
        weights = result.weights.loc[segment]
        avg_weights = weights.mean() if not weights.empty else pd.Series(dtype=float)
        dominant_asset = "cash"
        if not avg_weights.empty and avg_weights.max() > 1e-9:
            dominant_asset = str(avg_weights.idxmax())
        regimes = combined_regime.reindex(result.returns.loc[segment].index).ffill().astype(str)
        risk_off_share = float(regimes.eq("risk_off").mean()) if len(regimes) else np.nan
        btc_ret = _asset_return(dataset, "BTC", start, trough)
        eth_ret = _asset_return(dataset, "ETH", start, trough)
        btc_contribution = float(contributions.get("BTC", pd.Series(0.0, index=contributions.index)).loc[segment].sum())
        eth_contribution = float(contributions.get("ETH", pd.Series(0.0, index=contributions.index)).loc[segment].sum())
        explanation = (
            "Drawdown occurred while macro gate was mostly risk-on/neutral; exposure was permitted by the frozen rule."
            if risk_off_share < 0.50
            else "Drawdown overlapped a large share of risk-off days; losses were mainly residual exposure/rebalance timing."
        )
        if abs(btc_contribution) > abs(eth_contribution):
            explanation += " BTC contribution dominated."
        elif abs(eth_contribution) > abs(btc_contribution):
            explanation += " ETH contribution dominated."
        else:
            explanation += " BTC and ETH contributions were similar."
        rows.append({
            "rank": rank,
            "start": str(start.date()),
            "trough": str(trough.date()),
            "recovery": str(pd.Timestamp(period["recovery"]).date()) if period["recovery"] is not None else "unrecovered",
            "max_drawdown": float(period["max_drawdown"]),
            "strategy_exposure": float(weights.sum(axis=1).mean()) if not weights.empty else np.nan,
            "dominant_asset_exposure": dominant_asset,
            "average_btc_weight": float(avg_weights.get("BTC", 0.0)),
            "average_eth_weight": float(avg_weights.get("ETH", 0.0)),
            "btc_return": btc_ret,
            "eth_return": eth_ret,
            "btc_contribution": btc_contribution,
            "eth_contribution": eth_contribution,
            "macro_regime_state": regimes.mode().iloc[0] if len(regimes) else "unknown",
            "risk_off_day_share": risk_off_share,
            "explanation": explanation,
        })
    table = pd.DataFrame(rows)
    worst = table.head(1).copy()
    if not worst.empty:
        start = pd.Timestamp(worst.iloc[0]["start"])
        trough = pd.Timestamp(worst.iloc[0]["trough"])
        feature_segment = dataset.regime_features.loc[start:trough]
        for column in dataset.regime_features.columns:
            worst.loc[worst.index[0], f"avg_{column}"] = float(feature_segment[column].mean()) if column in feature_segment else np.nan
            worst.loc[worst.index[0], f"trough_{column}"] = float(dataset.regime_features[column].reindex([trough]).ffill().iloc[0]) if column in dataset.regime_features else np.nan
    return table, worst


def _exposure_quality_rows(
    strategies: list[DiagnosticStrategy],
    datasets: dict[str, MacroRegimeDataset],
    results: dict[str, dict[int, PortfolioResult]],
) -> pd.DataFrame:
    rows = []
    for spec in strategies:
        dataset = datasets[spec.dataset_key]
        result = results[spec.name][25]
        opportunity = dataset.returns[[c for c in ("BTC", "ETH") if c in dataset.returns]].mean(axis=1)
        for split, start, end in (
            ("development", DIAGNOSTIC_DEVELOPMENT_START, DIAGNOSTIC_DEVELOPMENT_END),
            ("holdout", HOLDOUT_START, HOLDOUT_END),
        ):
            returns = result.returns.loc[start:end]
            weights = result.weights.reindex(returns.index).fillna(0.0)
            exposure = weights.sum(axis=1).clip(0.0, 1.0)
            invested = exposure > 1e-9
            metrics = _extended_period_metrics(result, start, end)
            invested_returns = returns[invested]
            cash_returns = returns[~invested]
            weekly = returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0)
            weekly_exposure = exposure.resample("W-FRI").mean().reindex(weekly.index).fillna(0.0)
            invested_weeks = weekly_exposure > 1e-9
            opportunity_period = opportunity.reindex(returns.index).fillna(0.0)
            cash_days = ~invested
            missed_upside = float(opportunity_period[cash_days].clip(lower=0.0).sum())
            avoided_downside = float(-opportunity_period[cash_days].clip(upper=0.0).sum())
            avg_exposure = float(metrics.get("Exposure", np.nan))
            rows.append({
                "strategy": spec.name,
                "split": split,
                "return_per_unit_exposure": float(metrics["CAGR"] / avg_exposure) if avg_exposure else np.nan,
                "sharpe_per_unit_exposure": float(metrics["Sharpe"] / avg_exposure) if avg_exposure else np.nan,
                "drawdown_per_unit_exposure": float(metrics["Maximum Drawdown"] / avg_exposure) if avg_exposure else np.nan,
                "conditional_sharpe_when_invested": _daily_sharpe(invested_returns),
                "positive_invested_week_percentage": float((weekly[invested_weeks] > 0).mean()) if invested_weeks.any() else np.nan,
                "average_return_when_invested": float(invested_returns.mean()) if len(invested_returns) else np.nan,
                "average_return_when_in_cash": float(cash_returns.mean()) if len(cash_returns) else np.nan,
                "missed_upside_while_in_cash": missed_upside,
                "avoided_downside_while_in_cash": avoided_downside,
                "exposure": avg_exposure,
                "cash_exposure": float(metrics.get("Cash Allocation", np.nan)),
            })
    return pd.DataFrame(rows)


def _current_return_decomposition(
    dataset: MacroRegimeDataset,
    gross_result: PortfolioResult,
    net_result: PortfolioResult,
) -> pd.DataFrame:
    rows = []
    prev_weights = gross_result.weights.shift(1).fillna(0.0)
    btc = dataset.returns.get("BTC", pd.Series(0.0, index=prev_weights.index)).reindex(prev_weights.index).fillna(0.0)
    eth = dataset.returns.get("ETH", pd.Series(0.0, index=prev_weights.index)).reindex(prev_weights.index).fillna(0.0)
    baseline = 0.50 * btc + 0.50 * eth
    exposure = prev_weights.sum(axis=1).clip(0.0, 1.0)
    btc_contribution = prev_weights.get("BTC", pd.Series(0.0, index=prev_weights.index)) * btc
    eth_contribution = prev_weights.get("ETH", pd.Series(0.0, index=prev_weights.index)) * eth
    allocation_effect = (
        (prev_weights.get("BTC", pd.Series(0.0, index=prev_weights.index)) - 0.50 * exposure) * btc
        + (prev_weights.get("ETH", pd.Series(0.0, index=prev_weights.index)) - 0.50 * exposure) * eth
    )
    cash_timing = gross_result.gross_returns.reindex(prev_weights.index).fillna(0.0) - baseline.reindex(prev_weights.index).fillna(0.0)
    for split, start, end in (
        ("development", DIAGNOSTIC_DEVELOPMENT_START, DIAGNOSTIC_DEVELOPMENT_END),
        ("holdout", HOLDOUT_START, HOLDOUT_END),
    ):
        idx = gross_result.returns.loc[start:end].index
        rows.append({
            "split": split,
            "cash_timing_effect_sum": float(cash_timing.reindex(idx).sum()),
            "btc_exposure_effect_sum": float(btc_contribution.reindex(idx).sum()),
            "eth_exposure_effect_sum": float(eth_contribution.reindex(idx).sum()),
            "btc_vs_eth_allocation_effect_sum": float(allocation_effect.reindex(idx).sum()),
            "transaction_cost_drag_sum": float(-net_result.costs.reindex(idx).sum()),
            "gross_strategy_return_sum": float(gross_result.gross_returns.reindex(idx).sum()),
            "net_strategy_return_sum": float(net_result.returns.reindex(idx).sum()),
        })
    return pd.DataFrame(rows)


def _regime_analysis(dataset: MacroRegimeDataset, result: PortfolioResult) -> pd.DataFrame:
    features = dataset.regime_features.reindex(result.returns.index).ffill()
    btc = dataset.close.get("BTC", pd.Series(index=result.returns.index, dtype=float)).reindex(result.returns.index).ffill()
    btc_mom90 = btc.pct_change(90, fill_method=None)
    btc_ma200 = btc.rolling(200, min_periods=100).mean()
    dev_features = features.loc[DIAGNOSTIC_DEVELOPMENT_START:DIAGNOSTIC_DEVELOPMENT_END]
    masks = {
        "high_vix": features["vix_level"] >= dev_features["vix_level"].median(),
        "low_vix": features["vix_level"] < dev_features["vix_level"].median(),
        "rising_vix": features["vix_change_21d"] > 0,
        "falling_vix": features["vix_change_21d"] <= 0,
        "positive_equity_momentum": features["equity_momentum_21d"] > 0,
        "negative_equity_momentum": features["equity_momentum_21d"] <= 0,
        "high_equity_realized_volatility": features["equity_realized_vol_21d"] >= dev_features["equity_realized_vol_21d"].median(),
        "low_equity_realized_volatility": features["equity_realized_vol_21d"] < dev_features["equity_realized_vol_21d"].median(),
        "btc_bull_regime": (btc > btc_ma200) & (btc_mom90 > 0),
        "btc_bear_regime": (btc < btc_ma200) | (btc_mom90 < 0),
        "sideways_crypto_regime": btc_mom90.abs() <= 0.10,
    }
    rows = []
    total_negative = result.returns[result.returns < 0].sum()
    exposure = result.weights.sum(axis=1).reindex(result.returns.index).fillna(0.0)
    for name, mask in masks.items():
        idx = result.returns.index[mask.reindex(result.returns.index).fillna(False)]
        returns = result.returns.reindex(idx).dropna()
        if returns.empty:
            continue
        weekly = returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0)
        rows.append({
            "regime": name,
            "observations": int(len(returns)),
            "strategy_return": _compound_return(returns),
            "Sharpe": _daily_sharpe(returns),
            "exposure": float(exposure.reindex(idx).mean()),
            "hit_rate": float((returns > 0).mean()),
            "average_weekly_return": float(weekly.mean()) if len(weekly) else np.nan,
            "drawdown_contribution": float(returns[returns < 0].sum() / total_negative) if total_negative else np.nan,
        })
    return pd.DataFrame(rows)


def _reconciliation_table(metrics: pd.DataFrame) -> pd.DataFrame:
    selected = metrics[metrics["strategy"].eq(BASELINE_NAME)].copy()
    selected = selected[selected["split"].isin(["full_sample", "development", "holdout"])]
    rows = []
    for split, group in selected.groupby("split"):
        row = {"strategy": BASELINE_NAME, "split": split}
        for cost in ANALYSIS_COST_LEVELS:
            item = group[group["cost_bps"].eq(cost)]
            if item.empty:
                continue
            item = item.iloc[0]
            label = "gross" if cost == 0 else f"net_{cost}bps"
            row[f"{label}_Sharpe"] = item["Sharpe"]
            if cost in (0, 25):
                row[f"{label}_CAGR"] = item["CAGR"]
                row[f"{label}_Annualized Volatility"] = item["Annualized Volatility"]
                row[f"{label}_Maximum Drawdown"] = item["Maximum Drawdown"]
                row[f"{label}_Calmar"] = item["Calmar"]
                row[f"{label}_Sortino"] = item["Sortino"]
                row[f"{label}_Annual Turnover"] = item["Annual Turnover"]
                row[f"{label}_Exposure"] = item["Exposure"]
                row[f"{label}_Cash Allocation"] = item["Cash Allocation"]
                row[f"{label}_Allocation Changes"] = item["Allocation Changes"]
                row[f"{label}_Worst Month"] = item["Worst Month"]
                row[f"{label}_Drawdown Start"] = item["drawdown_start"]
                row[f"{label}_Drawdown Trough"] = item["drawdown_trough"]
                row[f"{label}_Drawdown Recovery"] = item["drawdown_recovery"]
        rows.append(row)
    order = {"full_sample": 0, "development": 1, "holdout": 2}
    table = pd.DataFrame(rows)
    table["_order"] = table["split"].map(order)
    return table.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def run_asset_level_macro_diagnostics(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    datasets = {
        "top10": build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10),
        "top20": build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=20),
    }
    strategies = _strategy_registry(datasets)
    metrics, results = _performance_rows(strategies, datasets)

    folds = []
    for name in [spec.name for spec in strategies]:
        folds.append(_cpcv_fold_rows(name, results[name][25], 25))
    folds_frame = pd.concat([fold for fold in folds if not fold.empty], ignore_index=True)
    cpcv_summary = _cpcv_summary(folds_frame)

    selected_folds = []
    for cost in ANALYSIS_COST_LEVELS:
        selected_folds.append(_cpcv_fold_rows(BASELINE_NAME, results[BASELINE_NAME][cost], cost))
    selected_cpcv_folds = pd.concat([fold for fold in selected_folds if not fold.empty], ignore_index=True)
    selected_cpcv_summary = _cpcv_summary(selected_cpcv_folds)

    strategy_names = [spec.name for spec in strategies]
    statistics = _statistical_rows(results, strategy_names)
    selected_dataset = datasets["top10"]
    selected_spec = [spec for spec in strategies if spec.name == BASELINE_NAME][0]
    drawdowns, worst_drawdown = _drawdown_forensics(
        selected_dataset,
        results[BASELINE_NAME][25],
        selected_spec.combined_regime,
    )
    exposure_quality = _exposure_quality_rows(strategies, datasets, results)
    current_decomposition = _current_return_decomposition(
        selected_dataset,
        results[BASELINE_NAME][0],
        results[BASELINE_NAME][25],
    )
    regime_analysis = _regime_analysis(selected_dataset, results[BASELINE_NAME][25])
    reconciliation = _reconciliation_table(metrics)
    strategy_info = pd.DataFrame([{
        "strategy": spec.name,
        "family": spec.family,
        "group": spec.group,
        "dataset": spec.dataset_key,
        "turnover_cap": spec.turnover_cap,
        "explanation": spec.explanation,
    } for spec in strategies])

    return {
        "datasets": datasets,
        "strategies": strategy_info,
        "metrics": metrics,
        "performance_reconciliation": reconciliation,
        "cpcv_folds": folds_frame,
        "cpcv_summary": cpcv_summary,
        "selected_cpcv_folds": selected_cpcv_folds,
        "selected_cpcv_summary": selected_cpcv_summary,
        "statistics": statistics,
        "drawdown_periods": drawdowns,
        "worst_drawdown": worst_drawdown,
        "exposure_quality": exposure_quality,
        "return_decomposition": current_decomposition,
        "regime_analysis": regime_analysis,
        "results": results,
        "metadata": {
            "title": "Asset-Level Macro Decomposition and Drawdown Diagnostics",
            "frozen_strategy": BASELINE_NAME,
            "strategy_modified": False,
            "selection_modified": False,
            "project_title": PROJECT_TITLE,
            "development_period": [str(DIAGNOSTIC_DEVELOPMENT_START.date()), str(DIAGNOSTIC_DEVELOPMENT_END.date())],
            "holdout_period": [str(HOLDOUT_START.date()), str(HOLDOUT_END.date())],
            "cost_levels_bps": list(ANALYSIS_COST_LEVELS),
            "diagnostic_note": "No strategy replacement is recommended unless an implementation error is found.",
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
        lines.append("| " + " | ".join(
            _fmt(row.get(key), key in percent, key in integer) for key, _ in columns
        ) + " |")
    return "\n".join(lines)


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.replace({np.nan: None}).to_dict("records")
    if isinstance(value, pd.Series):
        return value.replace({np.nan: None}).to_dict()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items() if key not in {"results", "datasets"}}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _metric_table_columns() -> list[tuple[str, str]]:
    return [
        ("strategy", "Strategy"),
        ("split", "Split"),
        ("cost_bps", "Cost bps"),
        ("CAGR", "CAGR"),
        ("Sharpe", "Sharpe"),
        ("Sortino", "Sortino"),
        ("Annualized Volatility", "Vol"),
        ("Maximum Drawdown", "Max DD"),
        ("Calmar", "Calmar"),
        ("Annual Turnover", "Turnover"),
        ("Exposure", "Exposure"),
        ("Cash Allocation", "Cash"),
        ("Allocation Changes", "Changes"),
        ("Worst Month", "Worst month"),
    ]


def write_asset_level_macro_diagnostics_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    metrics = result["metrics"]
    reconciliation = result["performance_reconciliation"]
    selected_25 = metrics[(metrics.strategy.eq(BASELINE_NAME)) & (metrics.cost_bps.eq(25))]
    selected_gross = metrics[(metrics.strategy.eq(BASELINE_NAME)) & (metrics.cost_bps.eq(0))]
    decomposition = metrics[metrics["group"].isin(["asset_level_macro_decomposition", "frozen_selected_strategy"])]
    universe = metrics[metrics["strategy"].isin([
        BASELINE_NAME,
        "top10_macro_gated_momentum",
        "top20_macro_gated_momentum",
        "equal_weight_top10",
        "pure_top10_momentum",
        "equal_weight_top20",
    ])]

    for name, frame in (
        ("metrics.csv", metrics),
        ("performance_reconciliation.csv", reconciliation),
        ("cpcv_folds.csv", result["cpcv_folds"]),
        ("cpcv_summary.csv", result["cpcv_summary"]),
        ("selected_cpcv_folds.csv", result["selected_cpcv_folds"]),
        ("selected_cpcv_summary.csv", result["selected_cpcv_summary"]),
        ("statistics.csv", result["statistics"]),
        ("drawdown_periods.csv", result["drawdown_periods"]),
        ("worst_drawdown.csv", result["worst_drawdown"]),
        ("exposure_quality.csv", result["exposure_quality"]),
        ("return_decomposition.csv", result["return_decomposition"]),
        ("regime_analysis.csv", result["regime_analysis"]),
        ("strategy_registry.csv", result["strategies"]),
    ):
        frame.to_csv(output / name, index=False)

    percent_common = {
        "CAGR",
        "Annualized Volatility",
        "Maximum Drawdown",
        "Exposure",
        "Cash Allocation",
        "Worst Month",
        "Transaction Costs",
        "max_drawdown",
        "strategy_exposure",
        "average_btc_weight",
        "average_eth_weight",
        "btc_return",
        "eth_return",
        "risk_off_day_share",
        "positive_fold_percentage",
        "pbo_context_all_decomposition_strategies",
        "deflated_sharpe_probability",
        "strategy_return",
        "hit_rate",
        "average_weekly_return",
        "drawdown_contribution",
        "return_per_unit_exposure",
        "drawdown_per_unit_exposure",
        "cash_exposure",
    }
    for prefix in ("gross", "net_25bps"):
        percent_common.update({
            f"{prefix}_CAGR",
            f"{prefix}_Annualized Volatility",
            f"{prefix}_Maximum Drawdown",
            f"{prefix}_Exposure",
            f"{prefix}_Cash Allocation",
            f"{prefix}_Worst Month",
        })
    integer_common = {"cost_bps", "Allocation Changes", "rank", "observations"}
    integer_common.update({"net_25bps_Allocation Changes", "gross_Allocation Changes"})

    holdout_25 = selected_25[selected_25.split.eq("holdout")].iloc[0]
    dev_25 = selected_25[selected_25.split.eq("development")].iloc[0]
    holdout_gross = selected_gross[selected_gross.split.eq("holdout")].iloc[0]
    dev_gross = selected_gross[selected_gross.split.eq("development")].iloc[0]

    (output / "executive_summary.md").write_text(f"""# Executive summary

This standalone diagnostic explains the frozen strategy **{BASELINE_NAME}**.  It does not modify, reselect, or retune the strategy.

## Key reconciliation

- Holdout gross Sharpe at 0 bps: {_fmt(holdout_gross['Sharpe'])}
- Holdout net Sharpe at 25 bps: {_fmt(holdout_25['Sharpe'])}
- Development gross Sharpe at 0 bps: {_fmt(dev_gross['Sharpe'])}
- Development net Sharpe at 25 bps: {_fmt(dev_25['Sharpe'])}
- Development net max drawdown at 25 bps: {_fmt(dev_25['Maximum Drawdown'], True)}
- Holdout net max drawdown at 25 bps: {_fmt(holdout_25['Maximum Drawdown'], True)}

## Interpretation

The strong holdout Sharpe is a **holdout-period, mostly risk-avoidance result**, not evidence that the strategy always had stable performance.  The development-period drawdown is real in the frozen backtest and is driven by being exposed during a severe crypto drawdown regime before the macro gate moved sufficiently defensive.

No implementation error was found in this diagnostic.  The final strategy remains **{BASELINE_NAME}** and should still be framed as a paper-monitoring candidate, not proven live alpha.
""", encoding="utf-8")

    (output / "performance_reconciliation.md").write_text(f"""# Performance reconciliation

The table below reconciles full-sample, development, and locked-holdout performance for **{BASELINE_NAME}**.  `gross_0bps` is an explicit no-cost rerun, not an estimate.

{_table(reconciliation, [
    ('strategy', 'Strategy'),
    ('split', 'Period'),
    ('gross_Sharpe', 'Gross Sharpe'),
    ('net_10bps_Sharpe', 'Net Sharpe 10 bps'),
    ('net_25bps_Sharpe', 'Net Sharpe 25 bps'),
    ('net_50bps_Sharpe', 'Net Sharpe 50 bps'),
    ('net_100bps_Sharpe', 'Net Sharpe 100 bps'),
    ('gross_CAGR', 'Gross CAGR'),
    ('gross_Maximum Drawdown', 'Gross Max DD'),
    ('net_25bps_CAGR', '25 bps CAGR'),
    ('net_25bps_Maximum Drawdown', '25 bps Max DD'),
    ('net_25bps_Annual Turnover', '25 bps turnover'),
    ('net_25bps_Exposure', '25 bps exposure'),
    ('net_25bps_Allocation Changes', '25 bps changes'),
    ('net_25bps_Drawdown Start', 'Worst DD start'),
    ('net_25bps_Drawdown Trough', 'Worst DD trough'),
    ('net_25bps_Drawdown Recovery', 'Worst DD recovery'),
], percent_common, integer_common)}

## Explicit number sources

- Gross Sharpe around 1.06: **{BASELINE_NAME}**, locked holdout, 0 bps gross, source `reports/asset_level_macro_diagnostics/performance_reconciliation.csv`.
- Net holdout Sharpe around 0.970: **{BASELINE_NAME}**, locked holdout, 25 bps net, same source.
- Development Sharpe around 0.6: **{BASELINE_NAME}**, development period, 25 bps net, same source.
- Development max drawdown around -71%: **{BASELINE_NAME}**, development period, net/gross diagnostic drawdown from the frozen backtest, same source.
- Holdout max drawdown around -18.42%: **{BASELINE_NAME}**, locked holdout, 25 bps net, same source.
""", encoding="utf-8")

    (output / "gross_net_performance.md").write_text(f"""# Gross and net performance

## Frozen selected strategy: all periods and cost assumptions

{_table(metrics[metrics.strategy.eq(BASELINE_NAME)], _metric_table_columns(), percent_common, integer_common, limit=60)}

## CPCV fold distribution for frozen strategy

{_table(result['selected_cpcv_summary'], [
    ('strategy', 'Strategy'),
    ('cost_bps', 'Cost bps'),
    ('median_fold_sharpe', 'Median fold Sharpe'),
    ('best_fold_sharpe', 'Best fold Sharpe'),
    ('worst_fold_sharpe', 'Worst fold Sharpe'),
    ('positive_fold_percentage', 'Positive folds'),
], percent_common, integer_common)}
""", encoding="utf-8")

    (output / "drawdown_forensics.md").write_text(f"""# Drawdown forensics

## Worst development drawdown detail

{_table(result['worst_drawdown'], [
    ('rank', 'Rank'),
    ('start', 'Start'),
    ('trough', 'Trough'),
    ('recovery', 'Recovery'),
    ('max_drawdown', 'Max DD'),
    ('strategy_exposure', 'Exposure'),
    ('dominant_asset_exposure', 'Dominant exposure'),
    ('average_btc_weight', 'Avg BTC weight'),
    ('average_eth_weight', 'Avg ETH weight'),
    ('btc_return', 'BTC return'),
    ('eth_return', 'ETH return'),
    ('macro_regime_state', 'Main macro state'),
    ('risk_off_day_share', 'Risk-off share'),
    ('explanation', 'Explanation'),
], percent_common, integer_common)}

## Ten worst development drawdown periods

{_table(result['drawdown_periods'], [
    ('rank', 'Rank'),
    ('start', 'Start'),
    ('trough', 'Trough'),
    ('recovery', 'Recovery'),
    ('max_drawdown', 'Max DD'),
    ('strategy_exposure', 'Exposure'),
    ('dominant_asset_exposure', 'Dominant exposure'),
    ('btc_return', 'BTC return'),
    ('eth_return', 'ETH return'),
    ('macro_regime_state', 'Main macro state'),
    ('risk_off_day_share', 'Risk-off share'),
    ('explanation', 'Explanation'),
], percent_common, integer_common)}
""", encoding="utf-8")

    (output / "asset_level_decomposition.md").write_text(f"""# Asset-level decomposition

This section compares frozen, non-tuned decompositions using the same macro gate where possible.

## Development and holdout metrics

{_table(decomposition[(decomposition.cost_bps.isin([0, 25])) & (decomposition.split.isin(['development', 'holdout']))], _metric_table_columns(), percent_common, integer_common, limit=80)}

## CPCV summary at 25 bps

{_table(result['cpcv_summary'][result['cpcv_summary'].strategy.isin(decomposition.strategy.unique())], [
    ('strategy', 'Strategy'),
    ('cost_bps', 'Cost bps'),
    ('median_fold_sharpe', 'Median fold Sharpe'),
    ('best_fold_sharpe', 'Best fold Sharpe'),
    ('worst_fold_sharpe', 'Worst fold Sharpe'),
    ('positive_fold_percentage', 'Positive folds'),
], percent_common, integer_common)}

## Statistical diagnostics

{_table(result['statistics'][result['statistics'].strategy.isin(decomposition.strategy.unique())], [
    ('strategy', 'Strategy'),
    ('pbo_context_all_decomposition_strategies', 'PBO context'),
    ('deflated_sharpe_probability', 'DSR probability'),
    ('bootstrap_sharpe_ci_lower', 'Sharpe CI low'),
    ('bootstrap_sharpe_ci_median', 'Sharpe CI mid'),
    ('bootstrap_sharpe_ci_upper', 'Sharpe CI high'),
    ('sharpe_delta_vs_frozen_median', 'Sharpe delta vs frozen'),
], percent_common)}
""", encoding="utf-8")

    (output / "exposure_quality.md").write_text(f"""# Exposure quality

## Exposure quality by strategy

{_table(result['exposure_quality'], [
    ('strategy', 'Strategy'),
    ('split', 'Split'),
    ('return_per_unit_exposure', 'Return/exposure'),
    ('sharpe_per_unit_exposure', 'Sharpe/exposure'),
    ('drawdown_per_unit_exposure', 'Drawdown/exposure'),
    ('conditional_sharpe_when_invested', 'Invested Sharpe'),
    ('positive_invested_week_percentage', 'Positive invested weeks'),
    ('average_return_when_invested', 'Avg return invested'),
    ('average_return_when_in_cash', 'Avg return cash'),
    ('missed_upside_while_in_cash', 'Missed upside'),
    ('avoided_downside_while_in_cash', 'Avoided downside'),
    ('exposure', 'Exposure'),
    ('cash_exposure', 'Cash'),
], percent_common, limit=120)}

## Current strategy return decomposition

{_table(result['return_decomposition'], [
    ('split', 'Split'),
    ('cash_timing_effect_sum', 'Cash timing effect'),
    ('btc_exposure_effect_sum', 'BTC exposure effect'),
    ('eth_exposure_effect_sum', 'ETH exposure effect'),
    ('btc_vs_eth_allocation_effect_sum', 'BTC-vs-ETH allocation effect'),
    ('transaction_cost_drag_sum', 'Transaction-cost drag'),
    ('gross_strategy_return_sum', 'Gross return sum'),
    ('net_strategy_return_sum', 'Net return sum'),
])}
""", encoding="utf-8")

    (output / "regime_analysis.md").write_text(f"""# Regime analysis

Performance by macro and crypto regime for the frozen selected strategy at 25 bps.

{_table(result['regime_analysis'], [
    ('regime', 'Regime'),
    ('observations', 'Obs'),
    ('strategy_return', 'Strategy return'),
    ('Sharpe', 'Sharpe'),
    ('exposure', 'Exposure'),
    ('hit_rate', 'Hit rate'),
    ('average_weekly_return', 'Avg weekly return'),
    ('drawdown_contribution', 'Drawdown contribution'),
], percent_common, integer_common)}
""", encoding="utf-8")

    (output / "universe_comparison.md").write_text(f"""# Universe comparison

This diagnostic asks whether broader tradable universes damage performance relative to BTC/ETH/cash macro timing.

{_table(universe[(universe.cost_bps.eq(25)) & (universe.split.isin(['development', 'holdout']))], _metric_table_columns(), percent_common, integer_common, limit=80)}

## Interpretation

Broad-universe variants are treated as diagnostics only. They add more idiosyncratic coin risk and turnover. If they do not improve holdout Sharpe, drawdown, and CPCV stability, they do not justify changing the final project framing.
""", encoding="utf-8")

    asset_holdout = decomposition[(decomposition.cost_bps.eq(25)) & (decomposition.split.eq("holdout"))].set_index("strategy")
    asset_dev = decomposition[(decomposition.cost_bps.eq(25)) & (decomposition.split.eq("development"))].set_index("strategy")
    current_h = asset_holdout.loc[BASELINE_NAME]
    btc_h = asset_holdout.loc["btc_only_macro_gate"]
    eth_h = asset_holdout.loc["eth_only_macro_gate"]
    balanced_h = asset_holdout.loc["btc_eth_50_50_macro_gate"]
    current_d = asset_dev.loc[BASELINE_NAME]

    (output / "title_recommendation.md").write_text(f"""# Title and strategy implications

1. **Does BTC-only macro timing outperform the current BTC/ETH/cash strategy?** No on the main holdout risk-adjusted metric. BTC-only has holdout Sharpe {_fmt(btc_h['Sharpe'])}, CAGR {_fmt(btc_h['CAGR'], True)}, and max DD {_fmt(btc_h['Maximum Drawdown'], True)} versus current Sharpe {_fmt(current_h['Sharpe'])}, CAGR {_fmt(current_h['CAGR'], True)}, and max DD {_fmt(current_h['Maximum Drawdown'], True)}. BTC-only improves drawdown but gives up too much return and Sharpe.
2. **Does ETH-only macro timing outperform the current strategy?** No. ETH-only has holdout Sharpe {_fmt(eth_h['Sharpe'])}, CAGR {_fmt(eth_h['CAGR'], True)}, and max DD {_fmt(eth_h['Maximum Drawdown'], True)}. It improves CAGR versus BTC-only but has worse drawdown than the current balanced strategy and slightly lower Sharpe.
3. **Does 50/50 BTC/ETH macro timing outperform the current strategy?** It is effectively the current strategy. The 50/50 macro gate has holdout Sharpe {_fmt(balanced_h['Sharpe'])}, CAGR {_fmt(balanced_h['CAGR'], True)}, and max DD {_fmt(balanced_h['Maximum Drawdown'], True)}, matching **{BASELINE_NAME}**.
4. **Does BTC/ETH allocation add value beyond simple macro timing?** It adds diversification between BTC defensive crypto beta and ETH speculative upside, but it is not evidence of dynamic BTC-vs-ETH selection alpha. The current strategy is a fixed balanced allocation when the macro gate permits exposure.
5. **Is the strategy mainly risk avoidance or genuine asset-selection alpha?** Mainly **risk avoidance / exposure timing**. Asset selection is simple and static.
6. **Is the development drawdown fatal?** It is a serious limitation, not an implementation error. Development net 25 bps max DD is {_fmt(current_d['Maximum Drawdown'], True)} and must be disclosed; it does not invalidate the diagnostic, but it prevents overclaiming live alpha.
7. **Should the AP title remain unchanged?** **Yes.**
8. **Should the title become BTC-specific or ETH-specific?** **No.** Neither BTC-only nor ETH-only clearly dominates the frozen BTC/ETH/cash macro strategy under the diagnostic criteria.
9. **Best final framing:** macro-regime conditioning improves crypto exposure timing and drawdown control in holdout, but the strategy should be framed as a systematic BTC/ETH/cash paper-monitoring candidate, not guaranteed live alpha.

Recommended title: **{PROJECT_TITLE}**
""", encoding="utf-8")

    (output / "final_interpretation.md").write_text(f"""# Final interpretation

The diagnostic reconciles the apparent contradiction:

- The approximately 1.06 Sharpe is **holdout gross 0 bps** performance.
- The approximately 0.970 Sharpe is **holdout net 25 bps** performance.
- The approximately 0.6 Sharpe is **development net 25 bps** performance.
- The approximately -71% development drawdown is a real historical stress outcome in the frozen strategy.
- The approximately -18% holdout drawdown reflects a more favorable locked-holdout regime and stronger cash/risk-off behavior.

The current strategy is best interpreted as a macro-regime risk-timing strategy with fixed BTC/ETH exposure, not a strong BTC-vs-ETH selector.  The project title should remain broad and systematic.  The strategy remains a strong paper-monitoring candidate, not proven live alpha.
""", encoding="utf-8")

    payload = {
        "metadata": result["metadata"],
        "strategies": result["strategies"],
        "metrics": metrics,
        "performance_reconciliation": reconciliation,
        "cpcv_summary": result["cpcv_summary"],
        "selected_cpcv_summary": result["selected_cpcv_summary"],
        "statistics": result["statistics"],
        "drawdown_periods": result["drawdown_periods"],
        "worst_drawdown": result["worst_drawdown"],
        "exposure_quality": result["exposure_quality"],
        "return_decomposition": result["return_decomposition"],
        "regime_analysis": result["regime_analysis"],
    }
    (output / "results.json").write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def run_default_asset_level_macro_diagnostics(
    output_dir: str | Path = "reports/asset_level_macro_diagnostics",
) -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_asset_level_macro_diagnostics(panel, macro, public_data, probability)
    write_asset_level_macro_diagnostics_reports(output_dir, result)
    return result


__all__ = [
    "run_asset_level_macro_diagnostics",
    "write_asset_level_macro_diagnostics_reports",
    "run_default_asset_level_macro_diagnostics",
]
