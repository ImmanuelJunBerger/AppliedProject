"""Economically motivated enhancements around the frozen macro-regime strategy.

The frozen benchmark remains ``btc_eth_macro_gate_balanced``.  This module does
not modify or reselect that strategy.  Each enhancement study is selected inside
the development period using CPCV, then evaluated on the locked holdout.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .cpcv import combinatorial_purged_splits
from .cross_sectional_momentum import HOLDOUT_END, HOLDOUT_START
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
)
from .public_crypto_data import PublicDataBundle
from .volatility_breakout import deflated_sharpe_probability, probability_backtest_overfitting


BASELINE_PBO_REFERENCE = 0.6142857142857143
BASELINE_DSR_REFERENCE = 0.4244907917328414
BASELINE_NAME = FIXED_SELECTED.name
ALL_FEATURES = tuple(MACRO_TIER1_FEATURES + CRYPTO_TIER1_FEATURES)
META_FEATURES = (
    "vix_level",
    "vix_change_5d",
    "vix_change_21d",
    "equity_momentum_21d",
    "equity_realized_vol_21d",
    "dow_vol_level",
    "volatility_expansion_probability",
    "cross_sectional_dispersion",
    "stablecoin_supply_change_7d",
    "tvl_growth_30d",
)


@dataclass(frozen=True)
class EnhancementCandidate:
    study: str
    name: str
    family: str
    description: str
    feature_drivers: str
    builder: Callable[[MacroRegimeDataset, pd.DataFrame, pd.DataFrame, PortfolioResult], pd.DataFrame]
    selectable: bool = True


def _rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(index[index.weekday == 4])
    return dates if len(dates) else pd.DatetimeIndex(index[::7])


def _feature_frame(dataset: MacroRegimeDataset, features: tuple[str, ...] = ALL_FEATURES) -> pd.DataFrame:
    frame = dataset.regime_features.reindex(columns=list(features)).replace([np.inf, -np.inf], np.nan).shift(1)
    development = frame.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    medians = development.median().fillna(0.0)
    return frame.ffill().fillna(medians).fillna(0.0)


def _standardized(frame: pd.DataFrame) -> pd.DataFrame:
    development = frame.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    mean = development.mean()
    std = development.std().replace(0.0, np.nan).fillna(1.0)
    return (frame - mean) / std


def _development_percentile(series: pd.Series) -> pd.Series:
    """Map values to percentiles using the development distribution only."""
    development = series.loc[DEVELOPMENT_START:DEVELOPMENT_END].replace([np.inf, -np.inf], np.nan).dropna()
    if development.empty:
        return pd.Series(0.50, index=series.index)
    ordered = np.sort(development.to_numpy(dtype=float))
    fill_value = float(np.nanmedian(ordered))
    values = series.replace([np.inf, -np.inf], np.nan).fillna(fill_value).to_numpy(dtype=float)
    percentiles = np.searchsorted(ordered, values, side="right") / len(ordered)
    return pd.Series(percentiles, index=series.index).clip(0.0, 1.0)


def _macro_risk_score(features: pd.DataFrame) -> pd.Series:
    z = _standardized(features)
    score = pd.Series(0.0, index=z.index)
    if "equity_momentum_21d" in z:
        score += z["equity_momentum_21d"]
    for feature in ("vix_level", "vix_change_5d", "vix_change_21d", "equity_realized_vol_21d"):
        if feature in z:
            score -= z[feature]
    return score.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def _signal_scores(dataset: MacroRegimeDataset, features: pd.DataFrame) -> pd.DataFrame:
    close = dataset.close
    momentum = close[["BTC", "ETH"]].pct_change(63, fill_method=None).mean(axis=1).shift(1)
    z = _standardized(features)
    rows = pd.DataFrame(index=features.index)
    rows["macro_regime"] = _macro_risk_score(features)
    rows["momentum"] = momentum.reindex(rows.index).fillna(0.0)
    rows["volatility_state"] = -z.get("volatility_expansion_probability", z.get("vix_level", pd.Series(0.0, index=rows.index)))
    rows["dispersion"] = -z.get("cross_sectional_dispersion", pd.Series(0.0, index=rows.index))
    rows["stablecoin_growth"] = z.get("stablecoin_supply_change_7d", pd.Series(0.0, index=rows.index))
    rows["tvl_growth"] = z.get("tvl_growth_30d", pd.Series(0.0, index=rows.index))
    return rows.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def _risk_buckets(score: pd.Series) -> pd.Series:
    dev = score.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    low = float(dev.quantile(0.33))
    high = float(dev.quantile(0.67))
    bucket = pd.Series("neutral", index=score.index, dtype=object)
    bucket.loc[score <= low] = "risk_off"
    bucket.loc[score >= high] = "risk_on"
    return bucket


def _btc_eth_weights(dataset: MacroRegimeDataset, exposure: pd.Series) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    aligned = exposure.reindex(dates).ffill().fillna(0.0).clip(0.0, 1.0)
    for date, value in aligned.items():
        eligible = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        assets = [symbol for symbol in ("BTC", "ETH") if symbol in weights.columns and symbol in eligible]
        if assets:
            weights.loc[date, assets] = min(0.50, float(value) / len(assets))
    return weights


def _asset_choice_weights(dataset: MacroRegimeDataset, choice: pd.Series) -> pd.DataFrame:
    dates = _rebalance_dates(dataset.close.index)
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    aligned = choice.reindex(dates).ffill().fillna("cash")
    for date, asset in aligned.items():
        eligible = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        if asset == "BTC" and "BTC" in weights.columns and "BTC" in eligible:
            weights.loc[date, "BTC"] = 1.0
        elif asset == "ETH" and "ETH" in weights.columns and "ETH" in eligible:
            weights.loc[date, "ETH"] = 1.0
        elif asset == "BTC_ETH":
            assets = [symbol for symbol in ("BTC", "ETH") if symbol in weights.columns and symbol in eligible]
            if assets:
                weights.loc[date, assets] = 1.0 / len(assets)
    return weights


def _apply_factor(base_weights: pd.DataFrame, factor: pd.Series) -> pd.DataFrame:
    aligned = factor.reindex(base_weights.index).ffill().fillna(0.0).clip(0.0, 1.0)
    return base_weights.mul(aligned, axis=0)


def _forward_strategy_return(base_result: PortfolioResult, dates: pd.DatetimeIndex) -> pd.Series:
    returns = base_result.returns.fillna(0.0)
    forward = returns.shift(-1).rolling(7).apply(lambda values: np.prod(1.0 + values) - 1.0, raw=True).shift(-6)
    return forward.reindex(dates)


def _forward_mix_return(dataset: MacroRegimeDataset, dates: pd.DatetimeIndex) -> pd.Series:
    btc = dataset.returns.get("BTC", pd.Series(0.0, index=dataset.returns.index))
    eth = dataset.returns.get("ETH", pd.Series(0.0, index=dataset.returns.index))
    mix = 0.50 * btc.fillna(0.0) + 0.50 * eth.fillna(0.0)
    forward = mix.shift(-1).rolling(7).apply(lambda values: np.prod(1.0 + values) - 1.0, raw=True).shift(-6)
    return forward.reindex(dates)


def _classifier(kind: str) -> Any:
    if kind == "logistic":
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced", random_state=17))
    if kind == "random_forest":
        return RandomForestClassifier(n_estimators=120, max_depth=3, min_samples_leaf=20, random_state=17, class_weight="balanced")
    if kind == "gradient_boosting":
        return GradientBoostingClassifier(n_estimators=80, max_depth=2, learning_rate=0.05, random_state=17)
    raise ValueError(kind)


def _cpcv_oof_probabilities(x: pd.DataFrame, y: pd.Series, kind: str) -> pd.Series:
    dev_mask = (x.index >= DEVELOPMENT_START) & (x.index <= DEVELOPMENT_END)
    x_dev = x.loc[dev_mask]
    y_dev = y.reindex(x_dev.index).fillna(False).astype(int)
    sums = pd.Series(0.0, index=x_dev.index)
    counts = pd.Series(0.0, index=x_dev.index)
    splits = combinatorial_purged_splits(len(x_dev), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
    for split in splits:
        train_index = x_dev.index[list(split.train_indices)]
        test_index = x_dev.index[list(split.test_indices)]
        if y_dev.loc[train_index].nunique() < 2:
            prob = pd.Series(float(y_dev.loc[train_index].mean()), index=test_index)
        else:
            model = _classifier(kind)
            model.fit(x_dev.loc[train_index], y_dev.loc[train_index])
            prob = pd.Series(model.predict_proba(x_dev.loc[test_index])[:, 1], index=test_index)
        sums.loc[test_index] += prob
        counts.loc[test_index] += 1.0
    return (sums / counts.replace(0, np.nan)).fillna(float(y_dev.mean()))


def _holdout_probabilities(x: pd.DataFrame, y: pd.Series, kind: str) -> pd.Series:
    dev_mask = (x.index >= DEVELOPMENT_START) & (x.index <= DEVELOPMENT_END)
    holdout_mask = (x.index >= HOLDOUT_START) & (x.index <= HOLDOUT_END)
    x_dev = x.loc[dev_mask]
    y_dev = y.reindex(x_dev.index).fillna(False).astype(int)
    x_holdout = x.loc[holdout_mask]
    if y_dev.nunique() < 2:
        return pd.Series(float(y_dev.mean()), index=x_holdout.index)
    model = _classifier(kind)
    model.fit(x_dev, y_dev)
    return pd.Series(model.predict_proba(x_holdout)[:, 1], index=x_holdout.index)


def _probability_factor(prob: pd.Series, threshold: float) -> pd.Series:
    lower = max(0.0, threshold - 0.15)
    factor = pd.Series(0.0, index=prob.index)
    factor.loc[prob >= lower] = 0.50
    factor.loc[prob >= threshold] = 1.0
    return factor


def _compose_oof_holdout_factor(x: pd.DataFrame, y: pd.Series, kind: str, threshold: float) -> pd.Series:
    oof = _cpcv_oof_probabilities(x, y, kind)
    holdout = _holdout_probabilities(x, y, kind)
    factor = pd.Series(0.50, index=x.index)
    factor.loc[oof.index] = _probability_factor(oof, threshold)
    factor.loc[holdout.index] = _probability_factor(holdout, threshold)
    factor.loc[factor.index < DEVELOPMENT_START] = 0.50
    return factor


def _study1_candidates() -> list[EnhancementCandidate]:
    def discrete(levels: tuple[float, ...], name: str, description: str) -> EnhancementCandidate:
        def build(dataset: MacroRegimeDataset, features: pd.DataFrame, base_weights: pd.DataFrame, base_result: PortfolioResult) -> pd.DataFrame:
            score = _macro_risk_score(features)
            dev = score.loc[DEVELOPMENT_START:DEVELOPMENT_END]
            ranks = _development_percentile(score)
            if len(levels) == 5:
                bins = pd.cut(ranks, [0, .2, .4, .6, .8, 1.0], labels=levels, include_lowest=True).astype(float)
            else:
                q1, q2, q3 = dev.quantile([0.25, 0.50, 0.75])
                bins = pd.Series(levels[1], index=score.index, dtype=float)
                bins.loc[score <= q1] = levels[0]
                bins.loc[(score > q2) & (score <= q3)] = levels[2]
                bins.loc[score > q3] = levels[3]
            return _btc_eth_weights(dataset, bins)
        return EnhancementCandidate("study_1_exposure_sizing", name, "Macro-conditioned exposure sizing", description, "vix_level, vix_change, equity_momentum, equity_volatility", build)

    def continuous(power: float, name: str) -> EnhancementCandidate:
        def build(dataset: MacroRegimeDataset, features: pd.DataFrame, base_weights: pd.DataFrame, base_result: PortfolioResult) -> pd.DataFrame:
            score = _macro_risk_score(features)
            percentile = _development_percentile(score)
            exposure = percentile.pow(power).clip(0.0, 1.0)
            return _btc_eth_weights(dataset, exposure)
        return EnhancementCandidate("study_1_exposure_sizing", name, "Macro-conditioned continuous sizing", f"Continuous exposure = percentile(macro risk score)^{power:g}.", "vix_level, vix_change, equity_momentum, equity_volatility", build)

    return [
        discrete((0.0, 0.25, 0.50, 0.75, 1.0), "discrete_balanced_0_25_50_75_100", "Discrete balanced sizing across 0/25/50/75/100%."),
        discrete((0.0, 0.25, 0.50, 0.75), "discrete_conservative", "Conservative discrete sizing; rarely reaches full exposure."),
        discrete((0.25, 0.50, 0.75, 1.0), "discrete_aggressive", "Aggressive discrete sizing with a 25% minimum exposure."),
        continuous(1.0, "continuous_linear_percentile"),
        continuous(1.5, "continuous_conservative_percentile"),
        continuous(0.7, "continuous_aggressive_percentile"),
    ]


def _study2_candidates() -> list[EnhancementCandidate]:
    candidates = []
    for kind in ("logistic", "random_forest", "gradient_boosting"):
        for threshold in (0.55, 0.60):
            def make(kind_: str = kind, threshold_: float = threshold) -> EnhancementCandidate:
                def build(dataset: MacroRegimeDataset, features: pd.DataFrame, base_weights: pd.DataFrame, base_result: PortfolioResult) -> pd.DataFrame:
                    dates = pd.DatetimeIndex(base_weights.index)
                    x = features.reindex(dates).ffill().fillna(0.0)
                    y = (_forward_strategy_return(base_result, dates) > 0).astype(int)
                    factor = _compose_oof_holdout_factor(x, y, kind_, threshold_)
                    return _apply_factor(base_weights, factor)
                return EnhancementCandidate("study_2_meta_labeling", f"meta_{kind_}_{int(threshold_ * 100)}", "Meta-labeling take/reduce/skip", f"{kind_} predicts whether the next frozen signal beats cash; threshold {threshold_}.", ", ".join(META_FEATURES), build)
            candidates.append(make())
    return candidates


def _study3_candidates() -> list[EnhancementCandidate]:
    def make(name: str, mode: str) -> EnhancementCandidate:
        def build(dataset: MacroRegimeDataset, features: pd.DataFrame, base_weights: pd.DataFrame, base_result: PortfolioResult) -> pd.DataFrame:
            score = _macro_risk_score(features)
            bucket = _risk_buckets(score)
            dev = score.loc[DEVELOPMENT_START:DEVELOPMENT_END]
            strong = float(dev.quantile(0.80))
            choice = pd.Series("cash", index=score.index, dtype=object)
            if mode == "speculative_eth":
                choice.loc[bucket == "neutral"] = "BTC"
                choice.loc[bucket == "risk_on"] = "BTC_ETH"
                choice.loc[score >= strong] = "ETH"
            elif mode == "conservative_btc":
                choice.loc[bucket == "neutral"] = "BTC"
                choice.loc[bucket == "risk_on"] = "BTC_ETH"
            elif mode == "eth_low_vol":
                low_vol = features["equity_realized_vol_21d"] <= features["equity_realized_vol_21d"].loc[DEVELOPMENT_START:DEVELOPMENT_END].median()
                choice.loc[bucket == "neutral"] = "BTC"
                choice.loc[(bucket == "risk_on") & low_vol] = "ETH"
                choice.loc[(bucket == "risk_on") & ~low_vol] = "BTC_ETH"
            elif mode == "btc_uncertain_eth_strong":
                choice.loc[bucket == "neutral"] = "BTC"
                choice.loc[bucket == "risk_on"] = "BTC"
                choice.loc[score >= strong] = "ETH"
            else:
                raise ValueError(mode)
            return _asset_choice_weights(dataset, choice)
        return EnhancementCandidate("study_3_asset_selection", name, "Regime-dependent BTC vs ETH allocation", f"Asset allocation mode: {mode}.", "lagged macro Tier 1 features", build)
    return [
        make("asset_speculative_eth", "speculative_eth"),
        make("asset_conservative_btc", "conservative_btc"),
        make("asset_eth_when_low_vol", "eth_low_vol"),
        make("asset_btc_uncertain_eth_strong", "btc_uncertain_eth_strong"),
    ]


def _study4_candidates() -> list[EnhancementCandidate]:
    def make(name: str, horizons: dict[str, int]) -> EnhancementCandidate:
        def build(dataset: MacroRegimeDataset, features: pd.DataFrame, base_weights: pd.DataFrame, base_result: PortfolioResult) -> pd.DataFrame:
            score = _macro_risk_score(features)
            bucket = _risk_buckets(score)
            choice = pd.Series("cash", index=score.index, dtype=object)
            for regime, lookback in horizons.items():
                btc_mom = dataset.close["BTC"].pct_change(lookback, fill_method=None).shift(1) if "BTC" in dataset.close else pd.Series(0.0, index=score.index)
                eth_mom = dataset.close["ETH"].pct_change(lookback, fill_method=None).shift(1) if "ETH" in dataset.close else pd.Series(0.0, index=score.index)
                mask = bucket == regime
                choice.loc[mask & (btc_mom >= eth_mom)] = "BTC"
                choice.loc[mask & (eth_mom > btc_mom)] = "ETH"
            return _asset_choice_weights(dataset, choice)
        return EnhancementCandidate("study_4_dynamic_horizon", name, "Regime-dependent momentum horizon", f"Momentum horizons by regime: {horizons}.", "macro regime score plus BTC/ETH momentum", build)
    return [
        make("fixed_momentum_21d", {"risk_on": 21, "neutral": 21}),
        make("fixed_momentum_42d", {"risk_on": 42, "neutral": 42}),
        make("fixed_momentum_63d", {"risk_on": 63, "neutral": 63}),
        make("fixed_momentum_126d", {"risk_on": 126, "neutral": 126}),
        make("dynamic_short_risk_on_long_neutral", {"risk_on": 21, "neutral": 126}),
        make("dynamic_medium_risk_on_long_neutral", {"risk_on": 42, "neutral": 126}),
        make("dynamic_short_risk_on_medium_neutral", {"risk_on": 21, "neutral": 63}),
    ]


def _study5_candidates() -> list[EnhancementCandidate]:
    def score_candidate(name: str, method: str) -> EnhancementCandidate:
        def build(dataset: MacroRegimeDataset, features: pd.DataFrame, base_weights: pd.DataFrame, base_result: PortfolioResult) -> pd.DataFrame:
            scores = _signal_scores(dataset, features)
            if method == "equal_weight":
                score = scores.mean(axis=1)
            elif method == "rank_average":
                score = pd.concat(
                    {column: _development_percentile(scores[column]) for column in scores.columns},
                    axis=1,
                ).mean(axis=1)
            elif method == "linear":
                score = (
                    0.30 * scores["macro_regime"]
                    + 0.25 * scores["momentum"]
                    + 0.15 * scores["volatility_state"]
                    + 0.10 * scores["dispersion"]
                    + 0.10 * scores["stablecoin_growth"]
                    + 0.10 * scores["tvl_growth"]
                )
            else:
                raise ValueError(method)
            percentile = _development_percentile(score)
            return _btc_eth_weights(dataset, percentile.clip(0, 1))
        return EnhancementCandidate("study_5_signal_ensemble", name, "Interpretable signal ensemble", f"{method} ensemble of macro/momentum/volatility/dispersion/liquidity signals.", "macro, momentum, volatility, dispersion, stablecoin growth, TVL growth", build)

    def logistic_candidate() -> EnhancementCandidate:
        def build(dataset: MacroRegimeDataset, features: pd.DataFrame, base_weights: pd.DataFrame, base_result: PortfolioResult) -> pd.DataFrame:
            dates = _rebalance_dates(dataset.close.index)
            x = _signal_scores(dataset, features).reindex(dates).ffill().fillna(0.0)
            y = (_forward_mix_return(dataset, dates) > 0).astype(int)
            factor = _compose_oof_holdout_factor(x, y, "logistic", 0.55)
            return _btc_eth_weights(dataset, factor)
        return EnhancementCandidate("study_5_signal_ensemble", "logistic_ensemble", "Interpretable logistic signal ensemble", "Logistic model using only predeclared ensemble signals.", "macro, momentum, volatility, dispersion, stablecoin growth, TVL growth", build)

    return [
        score_candidate("ensemble_equal_weight", "equal_weight"),
        score_candidate("ensemble_rank_average", "rank_average"),
        score_candidate("ensemble_linear_predeclared", "linear"),
        logistic_candidate(),
    ]


def all_study_candidates() -> dict[str, list[EnhancementCandidate]]:
    return {
        "study_1_exposure_sizing": _study1_candidates(),
        "study_2_meta_labeling": _study2_candidates(),
        "study_3_asset_selection": _study3_candidates(),
        "study_4_dynamic_horizon": _study4_candidates(),
        "study_5_signal_ensemble": _study5_candidates(),
    }


def _weekly_return(returns: pd.Series) -> pd.Series:
    return returns.resample("W-FRI").apply(lambda values: (1.0 + values).prod() - 1.0).dropna()


def _period_sharpe(values: pd.Series, indices: tuple[int, ...]) -> float:
    subset = values.iloc[list(indices)].replace([np.inf, -np.inf], np.nan).dropna()
    std = subset.std()
    return float(subset.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def _evaluate_cpcv(study: str, candidates: list[EnhancementCandidate], results: dict[str, PortfolioResult]) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    rows = []
    fold_rows = []
    weekly_returns = {}
    for candidate in candidates:
        weekly = _weekly_return(results[candidate.name].returns.loc[DEVELOPMENT_START:DEVELOPMENT_END])
        weekly_returns[candidate.name] = weekly
        splits = combinatorial_purged_splits(len(weekly), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        fold_values = []
        for number, split in enumerate(splits):
            sharpe = _period_sharpe(weekly, split.test_indices)
            fold_values.append(sharpe)
            fold_rows.append({
                "study": study,
                "candidate": candidate.name,
                "fold": number,
                "test_groups": ",".join(str(group) for group in split.test_groups),
                "fold_sharpe": sharpe,
                "n_test_weeks": len(split.test_indices),
            })
        dev = period_metrics(results[candidate.name], DEVELOPMENT_START, DEVELOPMENT_END)
        turnover_penalty = max(0.0, dev["Annual Turnover"] - 12.0) * 0.05
        row = {
            "study": study,
            "candidate": candidate.name,
            "family": candidate.family,
            "description": candidate.description,
            "feature_drivers": candidate.feature_drivers,
            "median_fold_sharpe": float(np.nanmedian(fold_values)),
            "worst_fold_sharpe": float(np.nanmin(fold_values)),
            "best_fold_sharpe": float(np.nanmax(fold_values)),
            "positive_fold_fraction": float(np.nanmean(np.asarray(fold_values) > 0)),
            "development_sharpe": dev["Sharpe"],
            "development_cagr": dev["CAGR"],
            "development_max_drawdown": dev["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "development_exposure": dev["Exposure"],
        }
        row["selection_score"] = float(
            row["median_fold_sharpe"]
            + 0.25 * row["worst_fold_sharpe"]
            + 0.50 * row["positive_fold_fraction"]
            - turnover_penalty
        )
        rows.append(row)
    pbo = probability_backtest_overfitting(pd.concat(weekly_returns, axis=1).sort_index(), blocks=8)
    return pd.DataFrame(rows).sort_values("selection_score", ascending=False), pd.DataFrame(fold_rows), pbo


def _metrics_for_candidates(study: str, candidates: list[EnhancementCandidate], results: dict[str, PortfolioResult]) -> pd.DataFrame:
    rows = []
    for candidate in candidates:
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            rows.append({
                "study": study,
                "candidate": candidate.name,
                "family": candidate.family,
                "split": split,
                "cost_bps": 25,
                **period_metrics(results[candidate.name], start, end),
            })
    return pd.DataFrame(rows)


def _retention_table(metrics: pd.DataFrame, selection: pd.DataFrame, pbo: float, frozen_holdout: dict[str, float]) -> pd.DataFrame:
    rows = []
    for candidate in metrics.candidate.unique():
        dev = metrics[(metrics.candidate == candidate) & (metrics.split == "development")].iloc[0]
        hold = metrics[(metrics.candidate == candidate) & (metrics.split == "holdout")].iloc[0]
        sel = selection[selection.candidate == candidate].iloc[0]
        rows.append({
            "study": dev.study,
            "candidate": candidate,
            "family": dev.family,
            "development_sharpe": dev.Sharpe,
            "holdout_sharpe": hold.Sharpe,
            "sharpe_retention": hold.Sharpe / dev.Sharpe if dev.Sharpe else np.nan,
            "development_cagr": dev.CAGR,
            "holdout_cagr": hold.CAGR,
            "cagr_retention": hold.CAGR / dev.CAGR if dev.CAGR else np.nan,
            "development_max_drawdown": dev["Maximum Drawdown"],
            "holdout_max_drawdown": hold["Maximum Drawdown"],
            "development_turnover": dev["Annual Turnover"],
            "holdout_turnover": hold["Annual Turnover"],
            "development_exposure": dev.Exposure,
            "holdout_exposure": hold.Exposure,
            "median_fold_sharpe": sel.median_fold_sharpe,
            "worst_fold_sharpe": sel.worst_fold_sharpe,
            "positive_fold_fraction": sel.positive_fold_fraction,
            "pbo": pbo,
            "deflated_sharpe_probability": deflated_sharpe_probability(
                pd.Series(dtype=float), 2
            ),
            "beats_frozen_holdout_sharpe": hold.Sharpe > frozen_holdout["Sharpe"],
            "beats_frozen_holdout_cagr": hold.CAGR > frozen_holdout["CAGR"],
            "drawdown_not_worse_than_frozen": hold["Maximum Drawdown"] >= frozen_holdout["Maximum Drawdown"],
        })
    return pd.DataFrame(rows)


def _study_decision(
    study: str,
    winner: str,
    retention: pd.DataFrame,
    results: dict[str, PortfolioResult],
    pbo: float,
    frozen_holdout: dict[str, float],
) -> dict[str, Any]:
    row = retention[retention.candidate == winner].iloc[0]
    dsr = deflated_sharpe_probability(results[winner].returns.loc[HOLDOUT_START:HOLDOUT_END], tested_configurations=len(retention))
    survives = bool(
        row.holdout_sharpe > frozen_holdout["Sharpe"] + 0.10
        and row.holdout_cagr > 0
        and row.holdout_max_drawdown >= frozen_holdout["Maximum Drawdown"]
        and row.holdout_turnover <= 12
        and np.isfinite(pbo)
        and pbo <= BASELINE_PBO_REFERENCE
    )
    if survives:
        status = "survives"
        conclusion = "Candidate improves frozen benchmark under the predeclared criteria; treat as a paper-monitoring enhancement, not a replacement."
    elif row.holdout_cagr <= 0 or row.holdout_sharpe <= 0:
        status = "failed_holdout"
        conclusion = "Candidate improves or ranks well in development but fails locked holdout economics."
    elif row.holdout_sharpe <= frozen_holdout["Sharpe"]:
        status = "explains_but_does_not_improve"
        conclusion = "Candidate is economically interpretable but does not improve risk-adjusted holdout performance versus frozen strategy."
    else:
        status = "partial"
        conclusion = "Candidate has some positive holdout evidence but fails at least one robustness criterion."
    return {
        "study": study,
        "selected_candidate": winner,
        "status": status,
        "conclusion": conclusion,
        "holdout_sharpe": float(row.holdout_sharpe),
        "holdout_cagr": float(row.holdout_cagr),
        "holdout_max_drawdown": float(row.holdout_max_drawdown),
        "holdout_turnover": float(row.holdout_turnover),
        "pbo": float(pbo) if np.isfinite(pbo) else np.nan,
        "deflated_sharpe_probability": dsr,
        "passes_predeclared_improvement_criteria": survives,
    }


def run_strategy_enhancement_research(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    dataset = build_macro_regime_dataset(panel, macro_features, public_data, volatility_probability, universe_size=10)
    features = _feature_frame(dataset)
    base_weights, base_macro, base_crypto, base_combined = build_candidate_weights(dataset, FIXED_SELECTED)
    frozen = backtest_weights(dataset, base_weights, base_macro, base_crypto, base_combined, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
    frozen_dev = period_metrics(frozen, DEVELOPMENT_START, DEVELOPMENT_END)
    frozen_holdout = period_metrics(frozen, HOLDOUT_START, HOLDOUT_END)

    studies: dict[str, dict[str, Any]] = {}
    all_candidates = all_study_candidates()
    all_selection = []
    all_folds = []
    all_metrics = []
    all_retention = []
    decisions = []
    for study, candidates in all_candidates.items():
        results: dict[str, PortfolioResult] = {}
        for candidate in candidates:
            weights = candidate.builder(dataset, features, base_weights, frozen)
            regime = pd.Series("custom", index=dataset.close.index, dtype=object)
            results[candidate.name] = backtest_weights(dataset, weights, regime, regime, regime, cost_bps=25, turnover_cap=FIXED_SELECTED.turnover_cap)
        selection, folds, pbo = _evaluate_cpcv(study, candidates, results)
        winner = str(selection.iloc[0].candidate)
        metrics = _metrics_for_candidates(study, candidates, results)
        retention = _retention_table(metrics, selection, pbo, frozen_holdout)
        for idx, row in retention.iterrows():
            retention.loc[idx, "deflated_sharpe_probability"] = deflated_sharpe_probability(
                results[row["candidate"]].returns.loc[HOLDOUT_START:HOLDOUT_END],
                tested_configurations=len(candidates),
            )
        decision = _study_decision(study, winner, retention, results, pbo, frozen_holdout)
        studies[study] = {
            "candidates": candidates,
            "results": results,
            "selection": selection,
            "folds": folds,
            "metrics": metrics,
            "retention": retention,
            "pbo": pbo,
            "winner": winner,
            "decision": decision,
        }
        all_selection.append(selection)
        all_folds.append(folds)
        all_metrics.append(metrics)
        all_retention.append(retention)
        decisions.append(decision)
    decision_frame = pd.DataFrame(decisions)
    surviving = decision_frame[decision_frame.passes_predeclared_improvement_criteria]
    final_decision = (
        "paper-monitor the strongest surviving enhancement without modifying the frozen strategy"
        if not surviving.empty
        else "keep frozen btc_eth_macro_gate_balanced; no enhancement survives all criteria"
    )
    return {
        "dataset": dataset,
        "frozen": frozen,
        "frozen_development": frozen_dev,
        "frozen_holdout": frozen_holdout,
        "studies": studies,
        "selection": pd.concat(all_selection, ignore_index=True),
        "folds": pd.concat(all_folds, ignore_index=True),
        "metrics": pd.concat(all_metrics, ignore_index=True),
        "retention": pd.concat(all_retention, ignore_index=True),
        "decisions": decision_frame,
        "final_decision": final_decision,
        "protocol": {
            "title": "Macro-Regime Conditioning for Systematic Cryptocurrency Allocation: A Robust Out-of-Sample Evaluation",
            "development_period": f"{DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}",
            "locked_holdout": f"{HOLDOUT_START.date()} to {HOLDOUT_END.date()}",
            "selection": "Each study selects candidates using development-only CPCV. Holdout is opened only after selection.",
            "frozen_strategy": BASELINE_NAME,
            "holdout_rule": "No holdout information is used for model or candidate selection.",
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


STUDY_TITLES = {
    "study_1_exposure_sizing": "Study 1: Macro-conditioned exposure sizing",
    "study_2_meta_labeling": "Study 2: Meta-labeling",
    "study_3_asset_selection": "Study 3: Regime-dependent BTC vs ETH allocation",
    "study_4_dynamic_horizon": "Study 4: Regime-dependent momentum horizon",
    "study_5_signal_ensemble": "Study 5: Signal ensemble",
}


def _interpretation_text(study: str, winner: str, winner_row: pd.Series, frozen_holdout: dict[str, float]) -> str:
    if study == "study_1_exposure_sizing":
        mechanics = (
            "Exposure rises when lagged equity momentum is stronger and volatility stress is lower "
            "(lower VIX, smaller VIX increases, and lower equity realized volatility). Exposure falls "
            "when those macro risk indicators deteriorate. The candidate does not change BTC versus ETH "
            "selection; it only changes total invested exposure."
        )
    elif study == "study_2_meta_labeling":
        mechanics = (
            "The primary frozen signal remains unchanged. The meta-model only decides whether to take, "
            "reduce, or skip that signal using lagged macro and crypto-native conditions. It increases "
            "exposure when the predicted probability that the next frozen signal beats cash clears the "
            "development-selected threshold, reduces exposure in the middle band, and holds cash when "
            "confidence is low. It does not independently prefer BTC over ETH; it scales the frozen "
            "BTC/ETH allocation."
        )
    elif study == "study_3_asset_selection":
        mechanics = (
            "The strategy holds cash in macro risk-off states, BTC in uncertain or moderate states, "
            "50/50 BTC/ETH in ordinary risk-on states, and ETH only in the strongest speculative macro "
            "states. The economic premise is that ETH should be favoured only when macro risk appetite "
            "is unusually strong."
        )
    elif study == "study_4_dynamic_horizon":
        mechanics = (
            "The strategy chooses BTC or ETH using lagged momentum, with the lookback horizon tied to "
            "macro regime. Shorter horizons are intended for strong risk-on environments, while longer "
            "horizons are intended for uncertain regimes. Cash is held in risk-off states."
        )
    else:
        mechanics = (
            "The ensemble raises exposure when multiple predeclared signals agree: favourable macro "
            "regime, positive BTC/ETH momentum, lower volatility stress, lower dispersion stress, "
            "positive stablecoin growth, and positive TVL growth. Exposure falls when signal agreement "
            "weakens. The ensemble does not independently choose BTC versus ETH."
        )

    caveat = ""
    if winner_row.holdout_exposure < 0.10:
        caveat = (
            "\n\nImportant caveat: the selected candidate's holdout exposure is below 10%. Its risk-adjusted "
            "performance is therefore driven substantially by risk avoidance and cash allocation, not by "
            "higher participation in crypto upside."
        )
    if winner_row.holdout_cagr < frozen_holdout["CAGR"]:
        caveat += (
            "\n\nThe selected candidate's holdout CAGR is below the frozen benchmark. Even when Sharpe or "
            "drawdown improves, it should be treated as a conservative overlay for paper monitoring rather "
            "than a replacement."
        )
    return mechanics + caveat


def _study_report(study: str, payload: dict[str, Any], frozen_holdout: dict[str, float]) -> str:
    selection = payload["selection"]
    retention = payload["retention"]
    decision = payload["decision"]
    winner = decision["selected_candidate"]
    winner_row = retention[retention.candidate == winner].iloc[0]
    interpretation = _interpretation_text(study, winner, winner_row, frozen_holdout)
    return f"""# {STUDY_TITLES[study]}

## Development-only selection

{_table(selection, [('candidate', 'Candidate'), ('family', 'Family'), ('selection_score', 'Selection score'), ('median_fold_sharpe', 'Median fold Sharpe'), ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds'), ('development_sharpe', 'Dev Sharpe'), ('development_turnover', 'Dev turnover')], {'positive_fold_fraction'})}

Selected by development-only CPCV: **{winner}**.

## Development vs holdout

{_table(retention, [('candidate', 'Candidate'), ('development_sharpe', 'Dev Sharpe'), ('holdout_sharpe', 'Holdout Sharpe'), ('sharpe_retention', 'Sharpe retention'), ('development_cagr', 'Dev CAGR'), ('holdout_cagr', 'Holdout CAGR'), ('cagr_retention', 'CAGR retention'), ('development_max_drawdown', 'Dev max DD'), ('holdout_max_drawdown', 'Holdout max DD'), ('holdout_turnover', 'Holdout turnover'), ('holdout_exposure', 'Holdout exposure')], {'sharpe_retention', 'development_cagr', 'holdout_cagr', 'cagr_retention', 'development_max_drawdown', 'holdout_max_drawdown', 'holdout_exposure'})}

## Statistical validation

- PBO: {_fmt(decision['pbo'], True)}
- Deflated Sharpe probability for selected candidate: {_fmt(decision['deflated_sharpe_probability'], True)}
- Worst CPCV fold: {_fmt(winner_row.worst_fold_sharpe)}
- Positive CPCV folds: {_fmt(winner_row.positive_fold_fraction, True)}

## Frozen benchmark comparison

- Frozen holdout Sharpe: {_fmt(frozen_holdout['Sharpe'])}
- Frozen holdout CAGR: {_fmt(frozen_holdout['CAGR'], True)}
- Frozen holdout max drawdown: {_fmt(frozen_holdout['Maximum Drawdown'], True)}
- Selected candidate holdout Sharpe: {_fmt(decision['holdout_sharpe'])}
- Selected candidate holdout CAGR: {_fmt(decision['holdout_cagr'], True)}
- Selected candidate holdout max drawdown: {_fmt(decision['holdout_max_drawdown'], True)}

## Interpretation

Status: **{decision['status']}**.

{decision['conclusion']}

Feature drivers: {selection[selection.candidate == winner].iloc[0].feature_drivers}.

### Economic interpretation and decision mechanics

{interpretation}
"""


def write_strategy_enhancement_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result["selection"].to_csv(output / "selection_scores.csv", index=False)
    result["folds"].to_csv(output / "cpcv_folds.csv", index=False)
    result["metrics"].to_csv(output / "candidate_metrics.csv", index=False)
    result["retention"].to_csv(output / "development_holdout_retention.csv", index=False)
    result["decisions"].to_csv(output / "study_decisions.csv", index=False)
    frozen_dev = result["frozen_development"]
    frozen_holdout = result["frozen_holdout"]
    decisions = result["decisions"]
    retention = result["retention"]

    (output / "executive_summary.md").write_text(f"""# Executive summary

Project: **{result['protocol']['title']}**

The frozen selected strategy remains **{BASELINE_NAME}**. It was not modified,
replaced, or reselected.

## Frozen benchmark

- Development Sharpe: {_fmt(frozen_dev['Sharpe'])}
- Holdout Sharpe: {_fmt(frozen_holdout['Sharpe'])}
- Holdout CAGR: {_fmt(frozen_holdout['CAGR'], True)}
- Holdout max drawdown: {_fmt(frozen_holdout['Maximum Drawdown'], True)}

## Enhancement decisions

{_table(decisions, [('study', 'Study'), ('selected_candidate', 'Development-selected candidate'), ('status', 'Status'), ('holdout_sharpe', 'Holdout Sharpe'), ('holdout_cagr', 'Holdout CAGR'), ('pbo', 'PBO'), ('deflated_sharpe_probability', 'Deflated Sharpe probability'), ('passes_predeclared_improvement_criteria', 'Passes criteria')], {'holdout_cagr', 'pbo', 'deflated_sharpe_probability'})}

Final decision: **{result['final_decision']}**.
""", encoding="utf-8")

    file_names = {
        "study_1_exposure_sizing": "study_1_exposure_sizing.md",
        "study_2_meta_labeling": "study_2_meta_labeling.md",
        "study_3_asset_selection": "study_3_asset_selection.md",
        "study_4_dynamic_horizon": "study_4_dynamic_horizon.md",
        "study_5_signal_ensemble": "study_5_signal_ensemble.md",
    }
    for study, file_name in file_names.items():
        (output / file_name).write_text(_study_report(study, result["studies"][study], frozen_holdout), encoding="utf-8")

    (output / "comparison_to_frozen_strategy.md").write_text(f"""# Comparison to frozen strategy

The frozen benchmark is **{BASELINE_NAME}** and remains unchanged.

## Frozen benchmark

| Split | CAGR | Sharpe | Sortino | Max DD | Calmar | Turnover | Exposure |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development | {_fmt(frozen_dev['CAGR'], True)} | {_fmt(frozen_dev['Sharpe'])} | {_fmt(frozen_dev['Sortino'])} | {_fmt(frozen_dev['Maximum Drawdown'], True)} | {_fmt(frozen_dev['Calmar'])} | {_fmt(frozen_dev['Annual Turnover'])} | {_fmt(frozen_dev['Exposure'], True)} |
| Holdout | {_fmt(frozen_holdout['CAGR'], True)} | {_fmt(frozen_holdout['Sharpe'])} | {_fmt(frozen_holdout['Sortino'])} | {_fmt(frozen_holdout['Maximum Drawdown'], True)} | {_fmt(frozen_holdout['Calmar'])} | {_fmt(frozen_holdout['Annual Turnover'])} | {_fmt(frozen_holdout['Exposure'], True)} |

## Candidate holdout comparison

{_table(retention.sort_values('holdout_sharpe', ascending=False), [('study', 'Study'), ('candidate', 'Candidate'), ('holdout_sharpe', 'Holdout Sharpe'), ('holdout_cagr', 'Holdout CAGR'), ('holdout_max_drawdown', 'Holdout max DD'), ('holdout_turnover', 'Holdout turnover'), ('beats_frozen_holdout_sharpe', 'Beats frozen Sharpe'), ('beats_frozen_holdout_cagr', 'Beats frozen CAGR'), ('drawdown_not_worse_than_frozen', 'DD not worse')], {'holdout_cagr', 'holdout_max_drawdown'})}
""", encoding="utf-8")

    (output / "statistical_validation.md").write_text(f"""# Statistical validation

All candidates were selected using development-only CPCV. Holdout metrics were
reported only after each study selected its candidate.

## Study-level statistics

{_table(decisions, [('study', 'Study'), ('selected_candidate', 'Selected candidate'), ('pbo', 'PBO'), ('deflated_sharpe_probability', 'Deflated Sharpe probability'), ('holdout_sharpe', 'Holdout Sharpe'), ('holdout_cagr', 'Holdout CAGR'), ('passes_predeclared_improvement_criteria', 'Passes criteria')], {'pbo', 'deflated_sharpe_probability', 'holdout_cagr'})}

## Candidate retention and fold summaries

{_table(retention, [('study', 'Study'), ('candidate', 'Candidate'), ('development_sharpe', 'Dev Sharpe'), ('holdout_sharpe', 'Holdout Sharpe'), ('sharpe_retention', 'Sharpe retention'), ('cagr_retention', 'CAGR retention'), ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds'), ('pbo', 'PBO'), ('deflated_sharpe_probability', 'DSR probability')], {'sharpe_retention', 'cagr_retention', 'positive_fold_fraction', 'pbo', 'deflated_sharpe_probability'}, limit=80)}
""", encoding="utf-8")

    best_survivors = decisions[decisions.passes_predeclared_improvement_criteria]
    if best_survivors.empty:
        recommendation = "No enhancement should replace or supersede the frozen strategy. Keep btc_eth_macro_gate_balanced as the paper-monitoring benchmark."
    else:
        survivor_names = ", ".join(best_survivors["selected_candidate"].astype(str))
        recommendation = (
            f"The following enhancement survived the predeclared criteria: {survivor_names}. "
            "Paper-monitor it separately as a conservative overlay, while keeping "
            "btc_eth_macro_gate_balanced frozen as the selected benchmark."
        )
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Recommendation

{recommendation}

## Rationale

The goal was not to maximize holdout Sharpe. The goal was to identify an
economically defensible enhancement that survives development-only CPCV and
locked holdout evaluation. Every hypothesis was evaluated independently and
failures are reported.

Final decision: **{result['final_decision']}**.

## Study outcomes

{_table(decisions, [('study', 'Study'), ('selected_candidate', 'Selected candidate'), ('status', 'Status'), ('conclusion', 'Conclusion')])}

The frozen selected strategy remains unchanged.
""", encoding="utf-8")

    payload = {
        "protocol": result["protocol"],
        "frozen_development": _json_safe(frozen_dev),
        "frozen_holdout": _json_safe(frozen_holdout),
        "decisions": _json_safe(decisions),
        "selection": _json_safe(result["selection"]),
        "retention": _json_safe(retention),
        "metrics": _json_safe(result["metrics"]),
        "final_decision": result["final_decision"],
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_default_strategy_enhancement_research(output_dir: str | Path = "reports/strategy_enhancement_research") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_strategy_enhancement_research(panel, macro, public_data, probability)
    write_strategy_enhancement_reports(output_dir, result)
    return result


__all__ = [
    "run_strategy_enhancement_research",
    "write_strategy_enhancement_reports",
    "run_default_strategy_enhancement_research",
    "all_study_candidates",
]
