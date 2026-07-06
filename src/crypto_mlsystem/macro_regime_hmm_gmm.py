"""Unsupervised macro-regime models for BTC/ETH/cash allocation.

The selected strategy ``btc_eth_macro_gate_balanced`` is not modified here.
This module asks whether GMM/HMM/KMeans-style unsupervised regimes can explain
or improve the fixed BTC/ETH/cash macro-regime allocation under the existing
development/holdout protocol.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    CRYPTO_TIER1_FEATURES,
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    MACRO_TIER1_FEATURES,
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


CURRENT_STRATEGY_PBO_REFERENCE = 0.6142857142857143


@dataclass(frozen=True)
class RegimeModelSpec:
    name: str
    model_type: str
    feature_set: str
    features: tuple[str, ...]


@dataclass(frozen=True)
class OverlaySpec:
    name: str
    family: str
    model_name: str
    overlay: str
    cost_bps: int = 25
    turnover_cap: float = 0.75


@dataclass
class FittedRegimeModel:
    spec: RegimeModelSpec
    regimes: pd.Series
    raw_states: pd.Series
    thresholds_or_mapping: dict[str, Any]
    train_start: str
    train_end: str
    hmmlearn_available: bool


def available_feature_sets(dataset: MacroRegimeDataset) -> dict[str, tuple[str, ...]]:
    feature_sets = {"macro": tuple(MACRO_TIER1_FEATURES)}
    crypto = dataset.regime_features[list(CRYPTO_TIER1_FEATURES)].loc[DEVELOPMENT_START:DEVELOPMENT_END]
    if crypto.notna().mean().mean() > 0.50:
        feature_sets["macro_crypto"] = tuple(MACRO_TIER1_FEATURES + CRYPTO_TIER1_FEATURES)
    return feature_sets


def predeclared_regime_model_specs(dataset: MacroRegimeDataset) -> list[RegimeModelSpec]:
    feature_sets = available_feature_sets(dataset)
    hmm_available = importlib.util.find_spec("hmmlearn") is not None
    hmm_type = "hmm" if hmm_available else "markov_fallback"
    specs: list[RegimeModelSpec] = []
    for feature_set, features in feature_sets.items():
        specs.append(RegimeModelSpec(f"gmm_{feature_set}", "gmm", feature_set, tuple(features)))
        specs.append(RegimeModelSpec(f"kmeans_{feature_set}", "kmeans", feature_set, tuple(features)))
        specs.append(RegimeModelSpec(f"{hmm_type}_{feature_set}", hmm_type, feature_set, tuple(features)))
    return specs


def _prepare_features(dataset: MacroRegimeDataset, features: tuple[str, ...]) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, StandardScaler]:
    frame = dataset.regime_features[list(features)].replace([np.inf, -np.inf], np.nan).copy()
    development = frame.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    medians = development.median().fillna(0.0)
    clean = frame.ffill().fillna(medians).fillna(0.0)
    scaler = StandardScaler()
    dev_index = clean.loc[DEVELOPMENT_START:DEVELOPMENT_END].index
    x_dev = scaler.fit_transform(clean.loc[dev_index])
    x_all = scaler.transform(clean)
    return clean, clean.loc[dev_index], x_all, x_dev, scaler


def _risk_score_from_scaled(features: tuple[str, ...], x_scaled: np.ndarray) -> np.ndarray:
    columns = list(features)
    score = np.zeros(x_scaled.shape[0])
    positive = {"equity_momentum_21d", "stablecoin_supply_change_7d", "tvl_growth_30d"}
    negative = {
        "equity_realized_vol_21d",
        "dow_vol_level",
        "vix_level",
        "vix_change_5d",
        "vix_change_21d",
        "volatility_expansion_probability",
        "cross_sectional_dispersion",
    }
    for feature in positive:
        if feature in columns:
            score += x_scaled[:, columns.index(feature)]
    for feature in negative:
        if feature in columns:
            score -= x_scaled[:, columns.index(feature)]
    return score


def _map_states_to_regimes(
    raw_states: np.ndarray,
    dev_mask: np.ndarray,
    risk_score: np.ndarray,
) -> dict[int, str]:
    state_scores = []
    for state in sorted(set(raw_states)):
        mask = (raw_states == state) & dev_mask
        value = float(np.nanmean(risk_score[mask])) if mask.any() else -np.inf
        state_scores.append((state, value))
    ordered = [state for state, _ in sorted(state_scores, key=lambda item: item[1])]
    labels = ["risk_off", "neutral", "risk_on"]
    return {int(state): labels[min(i, 2)] for i, state in enumerate(ordered)}


def _logsumexp(values: np.ndarray) -> float:
    max_value = float(np.max(values))
    if not np.isfinite(max_value):
        return max_value
    return max_value + float(np.log(np.sum(np.exp(values - max_value))))


def _gaussian_logpdf(x: np.ndarray, mean: np.ndarray, cov: np.ndarray) -> float:
    cov = np.asarray(cov, dtype=float)
    if cov.ndim == 1:
        cov = np.diag(cov)
    cov = cov + np.eye(cov.shape[0]) * 1e-6
    diff = x - mean
    sign, logdet = np.linalg.slogdet(cov)
    if sign <= 0:
        cov = cov + np.eye(cov.shape[0]) * 1e-4
        sign, logdet = np.linalg.slogdet(cov)
    inv = np.linalg.pinv(cov)
    return float(-0.5 * (len(x) * np.log(2 * np.pi) + logdet + diff @ inv @ diff))


def _hmm_filtered_predict(model: Any, x_all: np.ndarray) -> np.ndarray:
    means = np.asarray(model.means_)
    covars = np.asarray(model.covars_)
    trans = np.asarray(model.transmat_) + 1e-12
    start = np.asarray(model.startprob_) + 1e-12
    n_states = means.shape[0]
    states = np.zeros(len(x_all), dtype=int)
    alpha = np.log(start)
    for t, row in enumerate(x_all):
        emissions = np.asarray([
            _gaussian_logpdf(row, means[state], covars[state])
            for state in range(n_states)
        ])
        if t == 0:
            alpha = np.log(start) + emissions
        else:
            alpha = np.asarray([
                emissions[state] + _logsumexp(alpha + np.log(trans[:, state]))
                for state in range(n_states)
            ])
        alpha = alpha - _logsumexp(alpha)
        states[t] = int(np.argmax(alpha))
    return states


def _markov_fallback_predict(x_dev: np.ndarray, x_all: np.ndarray, random_state: int = 11) -> tuple[np.ndarray, dict[str, Any]]:
    kmeans = KMeans(n_clusters=3, random_state=random_state, n_init=20)
    dev_labels = kmeans.fit_predict(x_dev)
    trans = np.ones((3, 3), dtype=float)
    for prev, nxt in zip(dev_labels[:-1], dev_labels[1:]):
        trans[int(prev), int(nxt)] += 1.0
    trans = trans / trans.sum(axis=1, keepdims=True)
    centers = kmeans.cluster_centers_
    alpha = np.log(np.ones(3) / 3)
    states = np.zeros(len(x_all), dtype=int)
    for t, row in enumerate(x_all):
        distances = -0.5 * np.sum((centers - row) ** 2, axis=1)
        if t == 0:
            alpha = alpha + distances
        else:
            alpha = np.asarray([
                distances[state] + _logsumexp(alpha + np.log(trans[:, state]))
                for state in range(3)
            ])
        alpha = alpha - _logsumexp(alpha)
        states[t] = int(np.argmax(alpha))
    return states, {"transition_matrix_raw": trans.tolist()}


def fit_regime_model(dataset: MacroRegimeDataset, spec: RegimeModelSpec) -> FittedRegimeModel:
    clean, dev_clean, x_all, x_dev, _ = _prepare_features(dataset, spec.features)
    hmmlearn_available = importlib.util.find_spec("hmmlearn") is not None
    extra: dict[str, Any] = {}
    if spec.model_type == "gmm":
        model = GaussianMixture(n_components=3, covariance_type="full", random_state=17, n_init=10, reg_covar=1e-6)
        model.fit(x_dev)
        raw = model.predict(x_all)
    elif spec.model_type == "kmeans":
        model = KMeans(n_clusters=3, random_state=17, n_init=20)
        model.fit(x_dev)
        raw = model.predict(x_all)
    elif spec.model_type == "hmm":
        try:
            from hmmlearn.hmm import GaussianHMM

            model = GaussianHMM(n_components=3, covariance_type="diag", n_iter=200, random_state=17)
            model.fit(x_dev)
            raw = _hmm_filtered_predict(model, x_all)
        except Exception:
            raw, extra = _markov_fallback_predict(x_dev, x_all)
            hmmlearn_available = False
    elif spec.model_type == "markov_fallback":
        raw, extra = _markov_fallback_predict(x_dev, x_all)
    else:
        raise ValueError(spec.model_type)
    risk_score = _risk_score_from_scaled(spec.features, x_all)
    index = clean.index
    dev_mask = (index >= DEVELOPMENT_START) & (index <= DEVELOPMENT_END)
    mapping = _map_states_to_regimes(raw, np.asarray(dev_mask), risk_score)
    regimes = pd.Series([mapping[int(state)] for state in raw], index=index, name=spec.name)
    raw_series = pd.Series(raw, index=index, name=f"{spec.name}_raw_state")
    return FittedRegimeModel(
        spec=spec,
        regimes=regimes,
        raw_states=raw_series,
        thresholds_or_mapping={"state_to_regime": mapping, **extra},
        train_start=str(dev_clean.index.min().date()),
        train_end=str(dev_clean.index.max().date()),
        hmmlearn_available=hmmlearn_available,
    )


def fit_all_regime_models(dataset: MacroRegimeDataset) -> dict[str, FittedRegimeModel]:
    return {spec.name: fit_regime_model(dataset, spec) for spec in predeclared_regime_model_specs(dataset)}


def _rebalance_dates(index: pd.DatetimeIndex, rebalance_days: int = 7) -> pd.DatetimeIndex:
    weekly = pd.DatetimeIndex(index[index.weekday == 4])
    if weekly.empty:
        weekly = pd.DatetimeIndex(index[::7])
    if rebalance_days <= 7:
        return weekly
    return weekly[:: max(1, rebalance_days // 7)]


def _btc_eth_weights_from_regime(dataset: MacroRegimeDataset, regimes: pd.Series, rebalance_days: int = 7) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index, rebalance_days)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    aligned = regimes.reindex(dataset.close.index).ffill().fillna("risk_off")
    for date in dates:
        regime = aligned.loc[date]
        if regime == "risk_off":
            continue
        exposure = 1.0 if regime == "risk_on" else 0.50
        eligible = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        assets = [symbol for symbol in ("BTC", "ETH") if symbol in weights.columns and symbol in eligible]
        if assets:
            weights.loc[date, assets] = min(0.50, exposure / len(assets))
    return weights


def _apply_confirmation_filter(current_weights: pd.DataFrame, regimes: pd.Series) -> pd.DataFrame:
    filtered = current_weights.copy()
    aligned = regimes.reindex(filtered.index).ffill().fillna("risk_off")
    filtered.loc[aligned == "risk_off"] = 0.0
    return filtered


def _apply_exposure_scaling(current_weights: pd.DataFrame, regimes: pd.Series) -> pd.DataFrame:
    scaled = current_weights.copy()
    aligned = regimes.reindex(scaled.index).ffill().fillna("risk_off")
    factor = aligned.map({"risk_on": 1.0, "neutral": 0.50, "risk_off": 0.0}).astype(float)
    return scaled.mul(factor, axis=0)


def _current_strategy_result(dataset: MacroRegimeDataset, cost_bps: int) -> tuple[PortfolioResult, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    weights, macro, crypto, combined = build_candidate_weights(dataset, FIXED_SELECTED)
    result = backtest_weights(
        dataset,
        weights,
        macro,
        crypto,
        combined,
        cost_bps=cost_bps,
        turnover_cap=FIXED_SELECTED.turnover_cap,
    )
    return result, weights, macro, crypto, combined


def build_overlay_result(
    dataset: MacroRegimeDataset,
    fitted: FittedRegimeModel | None,
    overlay: str,
    cost_bps: int,
) -> tuple[PortfolioResult, pd.DataFrame]:
    if overlay == "current":
        result, weights, *_ = _current_strategy_result(dataset, cost_bps)
        return result, weights
    assert fitted is not None
    regimes = fitted.regimes
    crypto = pd.Series("not_used", index=regimes.index, dtype=object)
    if overlay == "direct":
        weights = _btc_eth_weights_from_regime(dataset, regimes)
    else:
        _, current_weights, *_ = _current_strategy_result(dataset, 0)
        if overlay == "confirmation_filter":
            weights = _apply_confirmation_filter(current_weights, regimes)
        elif overlay == "exposure_scaling":
            weights = _apply_exposure_scaling(current_weights, regimes)
        else:
            raise ValueError(overlay)
    result = backtest_weights(
        dataset,
        weights,
        regimes,
        crypto,
        regimes,
        cost_bps=cost_bps,
        turnover_cap=FIXED_SELECTED.turnover_cap,
    )
    return result, weights


def _weekly_return(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0).dropna()


def _period_sharpe(values: pd.Series, indices: tuple[int, ...]) -> float:
    subset = values.iloc[list(indices)].replace([np.inf, -np.inf], np.nan).dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def _selection_score(row: dict[str, Any]) -> float:
    turnover_penalty = max(0.0, row["development_turnover"] - 12.0) * 0.05
    return float(
        row["median_fold_sharpe"]
        + 0.25 * row["worst_fold_sharpe"]
        + 0.50 * row["positive_fold_fraction"]
        - turnover_penalty
    )


def _strategy_candidates(fitted_models: dict[str, FittedRegimeModel]) -> list[OverlaySpec]:
    candidates = [
        OverlaySpec("btc_eth_macro_gate_balanced", "Current selected strategy", "current", "current")
    ]
    for name, fitted in fitted_models.items():
        label = fitted.spec.model_type.upper() if fitted.spec.model_type != "markov_fallback" else "Fallback Markov"
        candidates.extend([
            OverlaySpec(f"{name}_direct", f"{label} direct BTC/ETH/cash allocation", name, "direct"),
            OverlaySpec(f"{name}_confirmation_filter", f"Current strategy + {label} confirmation filter", name, "confirmation_filter"),
            OverlaySpec(f"{name}_exposure_scaling", f"Current strategy + {label} exposure scaling", name, "exposure_scaling"),
        ])
    return candidates


def select_overlay_cpcv(candidates: list[OverlaySpec], results_25: dict[str, PortfolioResult]) -> tuple[pd.DataFrame, pd.DataFrame, str, float]:
    rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    weekly_returns: dict[str, pd.Series] = {}
    for candidate in candidates:
        weekly = _weekly_return(results_25[candidate.name].returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        weekly_returns[candidate.name] = weekly
        if len(weekly) < 20:
            continue
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_sharpes = []
        for number, split in enumerate(splits):
            sharpe = _period_sharpe(weekly, split.test_indices)
            fold_sharpes.append(sharpe)
            fold_rows.append({
                "candidate": candidate.name,
                "fold": number,
                "test_groups": ",".join(str(group) for group in split.test_groups),
                "fold_sharpe": sharpe,
                "n_test_weeks": len(split.test_indices),
            })
        dev = period_metrics(results_25[candidate.name], DEVELOPMENT_START, DEVELOPMENT_END)
        row = {
            "candidate": candidate.name,
            "family": candidate.family,
            "model_name": candidate.model_name,
            "overlay": candidate.overlay,
            "median_fold_sharpe": float(np.nanmedian(fold_sharpes)),
            "worst_fold_sharpe": float(np.nanmin(fold_sharpes)),
            "best_fold_sharpe": float(np.nanmax(fold_sharpes)),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_sharpes) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
        }
        row["selection_score"] = _selection_score(row)
        rows.append(row)
    selection = pd.DataFrame(rows).sort_values(
        ["selection_score", "median_fold_sharpe", "worst_fold_sharpe", "development_turnover"],
        ascending=[False, False, False, True],
    )
    winner = str(selection.iloc[0].candidate)
    aligned = pd.concat(weekly_returns, axis=1).sort_index()
    pbo = probability_backtest_overfitting(aligned, blocks=8)
    return selection, pd.DataFrame(fold_rows), winner, pbo


def _max_drawdown(returns: pd.Series) -> float:
    r = returns.replace([np.inf, -np.inf], np.nan).dropna()
    if r.empty:
        return np.nan
    wealth = (1.0 + r).cumprod()
    return float((wealth / wealth.cummax() - 1.0).min())


def _average_duration(regimes: pd.Series, state: str, start: pd.Timestamp, end: pd.Timestamp) -> float:
    period = regimes.loc[start:end].dropna()
    if period.empty:
        return np.nan
    durations = []
    current_state = None
    current_len = 0
    for value in period:
        if value == current_state:
            current_len += 1
        else:
            if current_state == state:
                durations.append(current_len)
            current_state = value
            current_len = 1
    if current_state == state:
        durations.append(current_len)
    return float(np.mean(durations)) if durations else 0.0


def regime_interpretation(dataset: MacroRegimeDataset, fitted_models: dict[str, FittedRegimeModel]) -> tuple[pd.DataFrame, pd.DataFrame]:
    btc = dataset.returns.get("BTC", pd.Series(0.0, index=dataset.returns.index)).fillna(0.0)
    eth = dataset.returns.get("ETH", pd.Series(0.0, index=dataset.returns.index)).fillna(0.0)
    mix = 0.50 * btc + 0.50 * eth
    rows = []
    transition_rows = []
    periods = (
        ("development", DEVELOPMENT_START, DEVELOPMENT_END),
        ("holdout", HOLDOUT_START, HOLDOUT_END),
        ("full", dataset.returns.index.min(), min(HOLDOUT_END, dataset.returns.index.max())),
    )
    for name, fitted in fitted_models.items():
        regimes = fitted.regimes.reindex(dataset.returns.index).ffill()
        for split, start, end in periods:
            period_index = mix.loc[start:end].index
            period_regimes = regimes.reindex(period_index).ffill()
            for state in ("risk_on", "neutral", "risk_off"):
                idx = period_regimes.index[period_regimes == state]
                r_mix = mix.reindex(idx).fillna(0.0)
                rows.append({
                    "model": name,
                    "model_type": fitted.spec.model_type,
                    "feature_set": fitted.spec.feature_set,
                    "split": split,
                    "regime": state,
                    "days": int(len(idx)),
                    "frequency": float(len(idx) / max(len(period_index), 1)),
                    "average_btc_return": float(btc.reindex(idx).mean()) if len(idx) else np.nan,
                    "average_eth_return": float(eth.reindex(idx).mean()) if len(idx) else np.nan,
                    "average_btc_eth_50_50_return": float(r_mix.mean()) if len(idx) else np.nan,
                    "annualized_volatility": float(r_mix.std() * np.sqrt(365)) if len(idx) else np.nan,
                    "max_drawdown": _max_drawdown(r_mix),
                    "average_vix": float(dataset.regime_features["vix_level"].reindex(idx).mean()) if len(idx) else np.nan,
                    "average_equity_momentum": float(dataset.regime_features["equity_momentum_21d"].reindex(idx).mean()) if len(idx) else np.nan,
                    "average_equity_volatility": float(dataset.regime_features["equity_realized_vol_21d"].reindex(idx).mean()) if len(idx) else np.nan,
                    "average_duration_days": _average_duration(regimes, state, start, end),
                })
            shifted = period_regimes.shift(-1)
            transitions = pd.DataFrame({"from": period_regimes.iloc[:-1], "to": shifted.iloc[:-1]}).dropna()
            counts = transitions.groupby(["from", "to"]).size()
            from_counts = transitions.groupby("from").size()
            for (src, dst), count in counts.items():
                transition_rows.append({
                    "model": name,
                    "split": split,
                    "from_regime": src,
                    "to_regime": dst,
                    "count": int(count),
                    "probability": float(count / from_counts.loc[src]),
                })
    return pd.DataFrame(rows), pd.DataFrame(transition_rows)


def _metrics_table(candidates: list[OverlaySpec], results_by_cost: dict[tuple[str, int], PortfolioResult]) -> pd.DataFrame:
    rows = []
    for candidate in candidates:
        for cost in COST_LEVELS:
            result = results_by_cost[(candidate.name, cost)]
            for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
                rows.append({
                    "candidate": candidate.name,
                    "family": candidate.family,
                    "model_name": candidate.model_name,
                    "overlay": candidate.overlay,
                    "split": split,
                    "cost_bps": cost,
                    **period_metrics(result, start, end),
                })
    return pd.DataFrame(rows)


def _acceptance_decision(
    selected_name: str,
    selection: pd.DataFrame,
    metrics: pd.DataFrame,
    pbo: float,
) -> dict[str, Any]:
    current = metrics[
        (metrics.candidate == FIXED_SELECTED.name)
        & (metrics.split == "holdout")
        & (metrics.cost_bps == 25)
    ].iloc[0]
    selected = metrics[
        (metrics.candidate == selected_name)
        & (metrics.split == "holdout")
        & (metrics.cost_bps == 25)
    ].iloc[0]
    selected_50 = metrics[
        (metrics.candidate == selected_name)
        & (metrics.split == "holdout")
        & (metrics.cost_bps == 50)
    ].iloc[0]
    selected_row = selection[selection.candidate == selected_name].iloc[0]
    materially_better = selected["Sharpe"] >= current["Sharpe"] + 0.10
    passes = bool(
        selected_name != FIXED_SELECTED.name
        and materially_better
        and selected["CAGR"] > 0
        and selected["Maximum Drawdown"] >= current["Maximum Drawdown"]
        and selected_50["CAGR"] > 0
        and selected_50["Sharpe"] > 0
        and selected["Annual Turnover"] <= 12
        and np.isfinite(pbo)
        and pbo <= CURRENT_STRATEGY_PBO_REFERENCE
    )
    if passes:
        conclusion = "HMM/GMM regime overlay improves the strategy enough to consider replacement."
        decision = "replace current strategy with development-selected unsupervised overlay"
    elif selected_name == FIXED_SELECTED.name:
        conclusion = "Unsupervised regimes explain the environment but do not improve the selected strategy; keep the current rule."
        decision = "keep btc_eth_macro_gate_balanced"
    else:
        conclusion = "Development-selected unsupervised overlay fails locked-holdout replacement criteria; reject it as a replacement and use regimes only for explanation."
        decision = "keep btc_eth_macro_gate_balanced"
    return {
        "development_selected_candidate": selected_name,
        "development_selected_family": selected_row["family"],
        "decision": decision,
        "conclusion": conclusion,
        "passes_replacement_criteria": passes,
        "material_sharpe_improvement_required": 0.10,
        "current_holdout_sharpe": float(current["Sharpe"]),
        "selected_holdout_sharpe": float(selected["Sharpe"]),
        "selected_holdout_cagr": float(selected["CAGR"]),
        "selected_holdout_max_drawdown": float(selected["Maximum Drawdown"]),
        "selected_holdout_turnover": float(selected["Annual Turnover"]),
        "selected_50bps_holdout_sharpe": float(selected_50["Sharpe"]),
        "selected_50bps_holdout_cagr": float(selected_50["CAGR"]),
        "family_pbo": float(pbo) if np.isfinite(pbo) else np.nan,
        "pbo_reference": CURRENT_STRATEGY_PBO_REFERENCE,
    }


def run_macro_regime_hmm_gmm_study(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    fitted_models = fit_all_regime_models(dataset)
    candidates = _strategy_candidates(fitted_models)
    results_by_cost: dict[tuple[str, int], PortfolioResult] = {}
    weights_by_candidate: dict[str, pd.DataFrame] = {}
    for candidate in candidates:
        fitted = fitted_models.get(candidate.model_name)
        for cost in COST_LEVELS:
            result, weights = build_overlay_result(dataset, fitted, candidate.overlay, cost)
            results_by_cost[(candidate.name, cost)] = result
            if cost == 25:
                weights_by_candidate[candidate.name] = weights
    results_25 = {candidate.name: results_by_cost[(candidate.name, 25)] for candidate in candidates}
    selection, folds, winner_name, pbo = select_overlay_cpcv(candidates, results_25)
    metrics = _metrics_table(candidates, results_by_cost)
    interpretation, transitions = regime_interpretation(dataset, fitted_models)
    statistics_rows = []
    for candidate in candidates:
        holdout_returns = results_by_cost[(candidate.name, 25)].returns.loc[HOLDOUT_START:HOLDOUT_END]
        ci = block_bootstrap_sharpe_ci(holdout_returns, samples=500, block_length=14, seed=19)
        candidate_folds = folds[folds.candidate == candidate.name]
        statistics_rows.append({
            "candidate": candidate.name,
            "tested_configurations": len(candidates),
            "family_pbo": pbo,
            "deflated_sharpe_probability": deflated_sharpe_probability(holdout_returns, len(candidates)),
            "bootstrap_sharpe_lower": ci["lower"],
            "bootstrap_sharpe_median": ci["median"],
            "bootstrap_sharpe_upper": ci["upper"],
            "best_fold_sharpe": float(candidate_folds.fold_sharpe.max()) if not candidate_folds.empty else np.nan,
            "median_fold_sharpe": float(candidate_folds.fold_sharpe.median()) if not candidate_folds.empty else np.nan,
            "worst_fold_sharpe": float(candidate_folds.fold_sharpe.min()) if not candidate_folds.empty else np.nan,
            "positive_fold_fraction": float((candidate_folds.fold_sharpe > 0).mean()) if not candidate_folds.empty else np.nan,
        })
    statistics = pd.DataFrame(statistics_rows)
    recommendation = _acceptance_decision(winner_name, selection, metrics, pbo)
    model_rows = []
    for name, fitted in fitted_models.items():
        model_rows.append({
            "model": name,
            "model_type": fitted.spec.model_type,
            "feature_set": fitted.spec.feature_set,
            "features": ", ".join(fitted.spec.features),
            "train_start": fitted.train_start,
            "train_end": fitted.train_end,
            "hmmlearn_available": fitted.hmmlearn_available,
            "state_mapping": json.dumps(fitted.thresholds_or_mapping, default=str),
        })
    return {
        "dataset": dataset,
        "fitted_models": fitted_models,
        "candidates": candidates,
        "selection": selection,
        "folds": folds,
        "metrics": metrics,
        "regime_interpretation": interpretation,
        "transition_probabilities": transitions,
        "statistics": statistics,
        "recommendation": recommendation,
        "model_inventory": pd.DataFrame(model_rows),
        "protocol": {
            "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} to {HOLDOUT_END.date()}",
            "regime_model_fit": "Unsupervised models fit on development features only; future returns are not used for fitting or risk labels.",
            "holdout_use": "Holdout is used only for final validation and reporting.",
            "tested_configurations": len(candidates),
            "feature_sets": sorted({fitted.spec.feature_set for fitted in fitted_models.values()}),
        },
    }


def _fmt(value: Any, percent: bool = False) -> str:
    if value is None or (isinstance(value, (float, np.floating)) and not np.isfinite(value)):
        return "N/A"
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if value else "No"
    if isinstance(value, (float, np.floating)):
        return f"{value:.2%}" if percent else f"{value:.3f}"
    return str(value)


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]], percent: set[str] | None = None, limit: int | None = None) -> str:
    percent = percent or set()
    if frame is None or frame.empty:
        return "_No rows._"
    view = frame.head(limit) if limit else frame
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in view.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, pd.DataFrame):
        return _json_safe(value.to_dict("records"))
    if isinstance(value, pd.Series):
        return _json_safe(value.to_dict())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value)
    return value


def write_macro_regime_hmm_gmm_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    model_inventory = result["model_inventory"]
    selection = result["selection"]
    folds = result["folds"]
    metrics = result["metrics"]
    interpretation = result["regime_interpretation"]
    transitions = result["transition_probabilities"]
    statistics = result["statistics"]
    recommendation = result["recommendation"]

    model_inventory.to_csv(output / "model_inventory.csv", index=False)
    selection.to_csv(output / "selection_scores.csv", index=False)
    folds.to_csv(output / "cpcv_folds.csv", index=False)
    metrics.to_csv(output / "strategy_metrics.csv", index=False)
    interpretation.to_csv(output / "regime_interpretation.csv", index=False)
    transitions.to_csv(output / "transition_probabilities.csv", index=False)
    statistics.to_csv(output / "statistics.csv", index=False)

    holdout_25 = metrics[(metrics.split == "holdout") & (metrics.cost_bps == 25)].sort_values("Sharpe", ascending=False)
    selected_costs = metrics[(metrics.candidate == recommendation["development_selected_candidate"]) & (metrics.split == "holdout")].sort_values("cost_bps")
    direct_holdout = holdout_25[holdout_25.overlay.isin(["current", "direct"])]
    overlay_holdout = holdout_25[holdout_25.overlay.isin(["confirmation_filter", "exposure_scaling"])]
    full_interpretation = interpretation[interpretation.split == "full"]
    transition_full = transitions[transitions.split == "full"]
    selected_stats = statistics[statistics.candidate == recommendation["development_selected_candidate"]]
    selected_stats_row = selected_stats.iloc[0] if not selected_stats.empty else pd.Series(dtype=float)

    (output / "regime_model_results.md").write_text(f"""# HMM/GMM macro-regime model results

## Protocol

- Development period: {result['protocol']['development_period']}.
- Locked holdout: {result['protocol']['locked_holdout']}.
- Regime model fitting: {result['protocol']['regime_model_fit']}
- Holdout use: {result['protocol']['holdout_use']}
- Tested strategy configurations: {result['protocol']['tested_configurations']}

## Model inventory

{_table(model_inventory, [('model', 'Model'), ('model_type', 'Type'), ('feature_set', 'Feature set'), ('features', 'Features'), ('train_start', 'Train start'), ('train_end', 'Train end'), ('hmmlearn_available', 'hmmlearn available')])}

Regime labels are assigned by macro risk scores only. Future crypto returns are not used to label risk-on, neutral, or risk-off states.
""", encoding="utf-8")

    (output / "regime_interpretation.md").write_text(f"""# Regime interpretation

## Economic profile by regime

{_table(full_interpretation, [('model', 'Model'), ('feature_set', 'Feature set'), ('regime', 'Regime'), ('frequency', 'Frequency'), ('average_btc_return', 'Avg BTC daily'), ('average_eth_return', 'Avg ETH daily'), ('average_btc_eth_50_50_return', 'Avg 50/50 daily'), ('annualized_volatility', 'Ann vol'), ('max_drawdown', 'Max DD'), ('average_vix', 'Avg VIX'), ('average_equity_momentum', 'Avg equity mom'), ('average_equity_volatility', 'Avg equity vol'), ('average_duration_days', 'Avg duration')], {'frequency', 'average_btc_return', 'average_eth_return', 'average_btc_eth_50_50_return', 'annualized_volatility', 'max_drawdown'})}

## Transition probabilities

{_table(transition_full, [('model', 'Model'), ('from_regime', 'From'), ('to_regime', 'To'), ('probability', 'Probability'), ('count', 'Count')], {'probability'}, limit=80)}
""", encoding="utf-8")

    (output / "strategy_overlay_results.md").write_text(f"""# Strategy overlay results

The current strategy is not modified. HMM/GMM/KMeans regimes are tested as
separate direct allocation rules, confirmation filters, and exposure scalers.

## Development-only CPCV selection

{_table(selection, [('candidate', 'Candidate'), ('family', 'Family'), ('overlay', 'Overlay'), ('selection_score', 'Selection score'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds'), ('development_sharpe', 'Dev Sharpe'), ('development_turnover', 'Dev turnover')], {'positive_fold_fraction'}, limit=40)}

Development-selected candidate: **{recommendation['development_selected_candidate']}**.

## Direct regime models and current baseline, holdout at 25 bps

{_table(direct_holdout, [('candidate', 'Candidate'), ('family', 'Family'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Confirmation and scaling overlays, holdout at 25 bps

{_table(overlay_holdout, [('candidate', 'Candidate'), ('family', 'Family'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}
""", encoding="utf-8")

    (output / "holdout_results.md").write_text(f"""# Locked holdout results

Holdout results are reported after development-only model fitting and CPCV
selection. They are not used to choose the final model.

## Holdout ranking at 25 bps

{_table(holdout_25, [('candidate', 'Candidate'), ('family', 'Family'), ('overlay', 'Overlay'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure'), ('Worst Month', 'Worst month')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'Worst Month'}, limit=40)}

## Development-selected candidate cost sensitivity

{_table(selected_costs, [('candidate', 'Candidate'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Replacement criteria

- Holdout Sharpe must materially improve versus current strategy by at least {_fmt(recommendation['material_sharpe_improvement_required'])}.
- Holdout CAGR must remain positive.
- Max drawdown must not worsen.
- 50 bps result must remain positive.
- Annual turnover must remain <= 12x.
- PBO must not increase versus the current reference.
- Economic interpretation must be clearer.

Passes replacement criteria: **{_fmt(recommendation['passes_replacement_criteria'])}**.
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

## PBO and deflated Sharpe

- Tested configurations: {result['protocol']['tested_configurations']}
- Family PBO: {_fmt(recommendation['family_pbo'], True)}
- Current-strategy PBO reference: {_fmt(recommendation['pbo_reference'], True)}
- Development-selected candidate deflated Sharpe probability: {_fmt(selected_stats_row.get('deflated_sharpe_probability', np.nan), True)}
- Development-selected candidate bootstrap Sharpe CI: [{_fmt(selected_stats_row.get('bootstrap_sharpe_lower', np.nan))}, {_fmt(selected_stats_row.get('bootstrap_sharpe_upper', np.nan))}]

## Candidate statistics

{_table(statistics, [('candidate', 'Candidate'), ('family_pbo', 'Family PBO'), ('deflated_sharpe_probability', 'Deflated Sharpe probability'), ('bootstrap_sharpe_lower', 'Bootstrap lower'), ('bootstrap_sharpe_median', 'Bootstrap median'), ('bootstrap_sharpe_upper', 'Bootstrap upper'), ('best_fold_sharpe', 'Best fold'), ('median_fold_sharpe', 'Median fold'), ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds')], {'family_pbo', 'deflated_sharpe_probability', 'positive_fold_fraction'}, limit=40)}

## CPCV folds

{_table(folds, [('candidate', 'Candidate'), ('fold', 'Fold'), ('test_groups', 'Test groups'), ('fold_sharpe', 'Fold Sharpe'), ('n_test_weeks', 'Test weeks')], limit=60)}
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Decision

**{recommendation['decision']}**

## Conclusion

{recommendation['conclusion']}

## Summary

- Development-selected candidate: `{recommendation['development_selected_candidate']}`.
- Current holdout Sharpe: {_fmt(recommendation['current_holdout_sharpe'])}.
- Selected holdout Sharpe: {_fmt(recommendation['selected_holdout_sharpe'])}.
- Selected holdout CAGR: {_fmt(recommendation['selected_holdout_cagr'], True)}.
- Selected holdout max drawdown: {_fmt(recommendation['selected_holdout_max_drawdown'], True)}.
- Selected holdout turnover: {_fmt(recommendation['selected_holdout_turnover'])}x.
- Family PBO: {_fmt(recommendation['family_pbo'], True)}.
- Current PBO reference: {_fmt(recommendation['pbo_reference'], True)}.

HMM/GMM/KMeans regimes are useful for explanation if their states separate
high-risk from low-risk macro environments. They do **not** improve the selected
strategy in this run. The development-selected overlay is rejected as a
replacement because it fails locked-holdout performance criteria. This decision
does not select the best holdout cell.
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "recommendation": recommendation,
        "model_inventory": _json_safe(model_inventory),
        "selection": _json_safe(selection),
        "metrics": _json_safe(metrics),
        "regime_interpretation": _json_safe(interpretation),
        "transition_probabilities": _json_safe(transitions),
        "statistics": _json_safe(statistics),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_macro_regime_hmm_gmm(output_dir: str | Path = "reports/macro_regime_hmm_gmm") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_macro_regime_hmm_gmm_study(panel, macro, public_data, probability)
    write_macro_regime_hmm_gmm_reports(output_dir, result)
    return result


__all__ = [
    "RegimeModelSpec",
    "OverlaySpec",
    "FittedRegimeModel",
    "predeclared_regime_model_specs",
    "fit_regime_model",
    "run_macro_regime_hmm_gmm_study",
    "write_macro_regime_hmm_gmm_reports",
    "run_default_macro_regime_hmm_gmm",
]
