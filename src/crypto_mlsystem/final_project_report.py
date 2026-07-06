"""Final robustness, explainability, and report pack for the fixed strategy.

The selected strategy remains fixed as ``btc_eth_macro_gate_balanced``.  This
module does not tune thresholds, select a new strategy, or alter allocation
logic.  It creates diagnostics that explain when and why the fixed strategy is
in cash, BTC, ETH, or BTC/ETH, plus simplified-gate and stress-period analysis.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cross_sectional_momentum import HOLDOUT_END, HOLDOUT_START
from .cpcv import combinatorial_purged_splits
from .macro_regime_benchmark_analysis import (
    FIXED_SELECTED,
    load_default_inputs,
    run_macro_regime_benchmark_analysis,
)
from .macro_regime_strategy import (
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    MACRO_NEGATIVE_FEATURES,
    MACRO_POSITIVE_FEATURES,
    MACRO_TIER1_FEATURES,
    MacroRegimeDataset,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
)
from .public_crypto_data import PublicDataBundle


SIMPLE_GATE_DEFINITIONS = {
    "full_selected_strategy": {
        "positive": tuple(MACRO_POSITIVE_FEATURES),
        "negative": tuple(MACRO_NEGATIVE_FEATURES),
        "risk_on_votes": 4,
        "neutral_votes": 3,
    },
    "vix_only_gate": {
        "positive": ("vix_level",),
        "negative": ("vix_change_5d", "vix_change_21d"),
        "risk_on_votes": 2,
        "neutral_votes": 1,
    },
    "equity_momentum_only_gate": {
        "positive": ("equity_momentum_21d",),
        "negative": (),
        "risk_on_votes": 1,
        "neutral_votes": 1,
    },
    "vix_plus_equity_momentum_gate": {
        "positive": ("vix_level", "equity_momentum_21d"),
        "negative": ("vix_change_5d", "vix_change_21d"),
        "risk_on_votes": 3,
        "neutral_votes": 2,
    },
    "equity_volatility_plus_vix_gate": {
        "positive": ("equity_realized_vol_21d", "vix_level"),
        "negative": ("vix_change_5d", "vix_change_21d"),
        "risk_on_votes": 3,
        "neutral_votes": 2,
    },
}


FEATURE_INTERPRETATIONS = {
    "equity_realized_vol_21d": {
        "plain_name": "21-day equity realized volatility",
        "economic_rationale": (
            "Equity realized volatility proxies cross-asset risk stress and the price of bearing risk. "
            "For crypto, it can matter because BTC/ETH often behave as high-beta liquidity assets."
        ),
        "selected_orientation_note": (
            "The selected empirical gate treats higher values as favourable. This is not the usual defensive interpretation; "
            "it likely captures post-stress rebound or elevated risk-premium conditions and should be monitored carefully."
        ),
    },
    "equity_momentum_21d": {
        "plain_name": "21-day equity momentum",
        "economic_rationale": (
            "Positive equity momentum indicates broad risk appetite, easier financing conditions, and better demand for high-beta assets."
        ),
        "selected_orientation_note": "Higher values are favourable, matching the risk-on interpretation.",
    },
    "dow_vol_level": {
        "plain_name": "Dow volatility level",
        "economic_rationale": (
            "Dow volatility captures stress in large-cap US equities. Crypto allocation can be sensitive to this because institutional "
            "risk budgets often adjust across risky assets together."
        ),
        "selected_orientation_note": (
            "The selected empirical gate treats higher values as favourable. This is potentially counterintuitive and may reflect "
            "risk-premium/rebound timing rather than a stable causal effect."
        ),
    },
    "vix_level": {
        "plain_name": "VIX level",
        "economic_rationale": (
            "VIX measures expected US equity volatility and is a common global risk-aversion proxy. It affects crypto through "
            "deleveraging, liquidity demand, and broad risk appetite."
        ),
        "selected_orientation_note": (
            "The selected empirical gate treats higher VIX levels as favourable. This should not be read as a general claim that "
            "high VIX is always good for crypto; it may capture rebound windows when stress is elevated but no longer worsening."
        ),
    },
    "vix_change_5d": {
        "plain_name": "5-day VIX change",
        "economic_rationale": (
            "Short-term VIX changes capture whether risk stress is accelerating or easing. A falling/non-rising VIX is typically "
            "more supportive for crypto exposure."
        ),
        "selected_orientation_note": "Lower values are favourable, matching the stress-easing interpretation.",
    },
    "vix_change_21d": {
        "plain_name": "21-day VIX change",
        "economic_rationale": (
            "Monthly VIX change captures persistent changes in macro risk aversion. Easing volatility over this horizon can support "
            "risk-on allocation."
        ),
        "selected_orientation_note": "Lower values are favourable, matching the medium-term stress-easing interpretation.",
    },
}


def run_final_project_analysis(
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
    selected_weights, macro_regime, crypto_regime, combined_regime = build_candidate_weights(dataset, FIXED_SELECTED)
    selected = backtest_weights(
        dataset,
        selected_weights,
        macro_regime,
        crypto_regime,
        combined_regime,
        cost_bps=25,
        turnover_cap=FIXED_SELECTED.turnover_cap,
    )

    explanations = explain_selected_strategy(dataset, selected_weights, macro_regime, selected)
    economic = economic_interpretation_analysis(dataset, selected_weights, macro_regime, selected, explanations)
    simple_gates = run_simple_gate_diagnostics(dataset)
    rolling = rolling_performance(selected)
    stress = stress_period_analysis(dataset, selected)
    development_holdout = development_vs_holdout_analysis(selected)
    benchmark = run_macro_regime_benchmark_analysis(panel, macro_features, public_data, volatility_probability)
    return {
        "dataset": dataset,
        "selected": selected,
        "selected_weights": selected_weights,
        "macro_regime": macro_regime,
        "crypto_regime": crypto_regime,
        "combined_regime": combined_regime,
        "explainability": explanations,
        "economic_interpretation": economic,
        "simple_gates": simple_gates,
        "rolling": rolling,
        "stress": stress,
        "development_holdout": development_holdout,
        "benchmark": benchmark,
    }


def economic_interpretation_analysis(
    dataset: MacroRegimeDataset,
    weekly_target_weights: pd.DataFrame,
    macro_regime: pd.Series,
    selected: Any,
    explanations: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Explain selected macro features without changing strategy decisions.

    The future-return columns are diagnostic labels only. They are not used to
    select thresholds, alter weights, or modify the strategy.
    """
    close = dataset.close
    forward_btc = close["BTC"].shift(-7) / close["BTC"] - 1.0 if "BTC" in close else pd.Series(np.nan, index=close.index)
    forward_eth = close["ETH"].shift(-7) / close["ETH"] - 1.0 if "ETH" in close else pd.Series(np.nan, index=close.index)
    forward_mix = 0.50 * forward_btc + 0.50 * forward_eth

    weights = weekly_target_weights.copy()
    weekly_index = pd.DatetimeIndex(weights.index)
    weekly = pd.DataFrame(index=weekly_index)
    weekly["forward_btc_7d"] = forward_btc.reindex(weekly_index)
    weekly["forward_eth_7d"] = forward_eth.reindex(weekly_index)
    weekly["forward_btc_eth_50_50_7d"] = forward_mix.reindex(weekly_index)
    weekly["target_btc_weight"] = weights.get("BTC", pd.Series(0.0, index=weekly_index)).reindex(weekly_index).fillna(0.0)
    weekly["target_eth_weight"] = weights.get("ETH", pd.Series(0.0, index=weekly_index)).reindex(weekly_index).fillna(0.0)
    weekly["target_exposure"] = weights.sum(axis=1).reindex(weekly_index).fillna(0.0)
    weekly["target_cash_weight"] = 1.0 - weekly["target_exposure"]
    weekly["macro_regime"] = macro_regime.reindex(weekly_index).ffill().fillna("missing")
    weekly["selected_forward_return_7d"] = selected.returns.reindex(dataset.close.index).fillna(0.0).rolling(7).apply(
        lambda values: np.prod(1.0 + values) - 1.0,
        raw=True,
    ).shift(-6).reindex(weekly_index)

    votes = explanations["feature_votes"].copy()
    votes = votes[votes["date"].isin(weekly_index)].merge(
        weekly.reset_index(names="date"),
        on="date",
        how="left",
    )
    state_rows = []
    for (feature, favorable), group in votes.groupby(["feature", "favorable"]):
        state_rows.append({
            "feature": feature,
            "feature_name": FEATURE_INTERPRETATIONS.get(feature, {}).get("plain_name", feature),
            "state": "favourable" if favorable else "unfavourable",
            "weeks": int(len(group)),
            "frequency": float(len(group) / max(len(weekly_index), 1)),
            "average_forward_btc_7d": float(group["forward_btc_7d"].mean()),
            "average_forward_eth_7d": float(group["forward_eth_7d"].mean()),
            "average_forward_btc_eth_50_50_7d": float(group["forward_btc_eth_50_50_7d"].mean()),
            "hit_rate_btc_eth_50_50_7d": float((group["forward_btc_eth_50_50_7d"] > 0).mean()),
            "average_target_btc_weight": float(group["target_btc_weight"].mean()),
            "average_target_eth_weight": float(group["target_eth_weight"].mean()),
            "average_target_cash_weight": float(group["target_cash_weight"].mean()),
            "average_target_exposure": float(group["target_exposure"].mean()),
            "exposure_contribution": float(group["target_exposure"].sum() / max(len(weekly_index), 1)),
        })
    state = pd.DataFrame(state_rows)

    summary_rows = []
    for feature in MACRO_TIER1_FEATURES:
        fav = state[(state.feature == feature) & (state.state == "favourable")]
        unfav = state[(state.feature == feature) & (state.state == "unfavourable")]
        fav_row = fav.iloc[0].to_dict() if not fav.empty else {}
        unfav_row = unfav.iloc[0].to_dict() if not unfav.empty else {}
        info = FEATURE_INTERPRETATIONS.get(feature, {})
        summary_rows.append({
            "feature": feature,
            "feature_name": info.get("plain_name", feature),
            "selected_rule": _selected_rule_for_feature(feature),
            "economic_rationale": info.get("economic_rationale", ""),
            "selected_orientation_note": info.get("selected_orientation_note", ""),
            "favourable_frequency": fav_row.get("frequency", np.nan),
            "unfavourable_frequency": unfav_row.get("frequency", np.nan),
            "favourable_forward_btc_eth_7d": fav_row.get("average_forward_btc_eth_50_50_7d", np.nan),
            "unfavourable_forward_btc_eth_7d": unfav_row.get("average_forward_btc_eth_50_50_7d", np.nan),
            "favourable_minus_unfavourable_forward_7d": (
                fav_row.get("average_forward_btc_eth_50_50_7d", np.nan)
                - unfav_row.get("average_forward_btc_eth_50_50_7d", np.nan)
            ),
            "favourable_exposure": fav_row.get("average_target_exposure", np.nan),
            "unfavourable_exposure": unfav_row.get("average_target_exposure", np.nan),
            "favourable_cash": fav_row.get("average_target_cash_weight", np.nan),
            "unfavourable_cash": unfav_row.get("average_target_cash_weight", np.nan),
            "favourable_btc_weight": fav_row.get("average_target_btc_weight", np.nan),
            "unfavourable_btc_weight": unfav_row.get("average_target_btc_weight", np.nan),
            "favourable_eth_weight": fav_row.get("average_target_eth_weight", np.nan),
            "unfavourable_eth_weight": unfav_row.get("average_target_eth_weight", np.nan),
        })
    feature_summary = pd.DataFrame(summary_rows)

    regime_rows = []
    for regime, group in weekly.groupby("macro_regime"):
        regime_rows.append({
            "macro_regime": regime,
            "weeks": int(len(group)),
            "frequency": float(len(group) / max(len(weekly), 1)),
            "average_forward_btc_eth_50_50_7d": float(group["forward_btc_eth_50_50_7d"].mean()),
            "hit_rate_btc_eth_50_50_7d": float((group["forward_btc_eth_50_50_7d"] > 0).mean()),
            "average_target_btc_weight": float(group["target_btc_weight"].mean()),
            "average_target_eth_weight": float(group["target_eth_weight"].mean()),
            "average_target_cash_weight": float(group["target_cash_weight"].mean()),
            "average_target_exposure": float(group["target_exposure"].mean()),
        })
    regime_summary = pd.DataFrame(regime_rows)

    allocation = explanations["allocation_explanations"].copy()
    allocation = allocation.merge(
        weekly[["forward_btc_eth_50_50_7d", "forward_btc_7d", "forward_eth_7d"]].reset_index(names="date"),
        on="date",
        how="left",
    )
    allocation_summary = allocation.groupby("allocation").agg(
        weeks=("date", "count"),
        average_forward_btc_eth_50_50_7d=("forward_btc_eth_50_50_7d", "mean"),
        hit_rate_btc_eth_50_50_7d=("forward_btc_eth_50_50_7d", lambda values: float((values > 0).mean())),
        average_target_btc_weight=("target_btc_weight", "mean"),
        average_target_eth_weight=("target_eth_weight", "mean"),
        average_target_cash_weight=("target_cash_weight", "mean"),
        average_target_exposure=("target_exposure", "mean"),
    ).reset_index()
    allocation_summary["frequency"] = allocation_summary["weeks"] / max(len(allocation), 1)

    return {
        "weekly_decision_context": weekly.reset_index(names="date"),
        "feature_state_conditioning": state,
        "feature_summary": feature_summary,
        "regime_summary": regime_summary,
        "allocation_summary": allocation_summary,
    }


def _threshold_table(dataset: MacroRegimeDataset) -> pd.DataFrame:
    thresholds = dataset.thresholds[FIXED_SELECTED.gate_profile]["thresholds"]
    rows = []
    for feature in MACRO_TIER1_FEATURES:
        orientation = "high is favourable" if feature in MACRO_POSITIVE_FEATURES else "low/rising less is favourable"
        rows.append({
            "feature": feature,
            "threshold": thresholds.get(feature, np.nan),
            "orientation": orientation,
            "gate_profile": FIXED_SELECTED.gate_profile,
        })
    return pd.DataFrame(rows)


def _feature_votes(dataset: MacroRegimeDataset) -> pd.DataFrame:
    thresholds = dataset.thresholds[FIXED_SELECTED.gate_profile]["thresholds"]
    rows = []
    for date, values in dataset.regime_features[list(MACRO_TIER1_FEATURES)].iterrows():
        for feature in MACRO_TIER1_FEATURES:
            threshold = thresholds.get(feature, np.nan)
            value = values.get(feature, np.nan)
            if feature in MACRO_POSITIVE_FEATURES:
                favorable = bool(pd.notna(value) and np.isfinite(threshold) and value >= threshold)
                rule = ">="
            else:
                favorable = bool(pd.notna(value) and np.isfinite(threshold) and value <= threshold)
                rule = "<="
            rows.append({
                "date": date,
                "feature": feature,
                "value": value,
                "threshold": threshold,
                "rule": rule,
                "favorable": favorable,
            })
    return pd.DataFrame(rows)


def explain_selected_strategy(
    dataset: MacroRegimeDataset,
    weekly_target_weights: pd.DataFrame,
    macro_regime: pd.Series,
    selected: Any,
) -> dict[str, pd.DataFrame]:
    votes = _feature_votes(dataset)
    weekly_dates = pd.DatetimeIndex(weekly_target_weights.index)
    weekly_votes = votes[votes.date.isin(weekly_dates)].copy()
    activation = weekly_votes.groupby("feature").agg(
        activation_rate=("favorable", "mean"),
        favourable_weeks=("favorable", "sum"),
        total_weeks=("favorable", "count"),
        average_value=("value", "mean"),
        threshold=("threshold", "first"),
    ).reset_index()

    contribution_rows = []
    for date in weekly_dates:
        current_votes = weekly_votes[weekly_votes.date == date].copy()
        favourable = current_votes[current_votes.favorable].feature.tolist()
        blocking = current_votes[~current_votes.favorable].feature.tolist()
        vote_count = int(len(favourable))
        regime = str(macro_regime.reindex([date]).ffill().iloc[0]) if date in macro_regime.index else "missing"
        target = weekly_target_weights.loc[date].copy()
        btc = float(target.get("BTC", 0.0))
        eth = float(target.get("ETH", 0.0))
        exposure = float(target.sum())
        if exposure <= 1e-9:
            allocation = "cash"
            reason = f"cash because macro regime is {regime}; only {vote_count}/6 macro features were favourable"
        elif btc > 0 and eth > 0:
            allocation = "BTC/ETH"
            reason = f"{allocation} because macro regime is {regime}; {vote_count}/6 macro features were favourable"
        elif btc > 0:
            allocation = "BTC"
            reason = f"BTC because ETH was not eligible while macro regime is {regime}"
        elif eth > 0:
            allocation = "ETH"
            reason = f"ETH because BTC was not eligible while macro regime is {regime}"
        else:
            allocation = "other"
            reason = f"non-BTC/ETH allocation unexpected for fixed BTC/ETH strategy"
        contribution_rows.append({
            "date": date,
            "macro_regime": regime,
            "favourable_feature_count": vote_count,
            "favourable_features": ", ".join(favourable),
            "blocking_features": ", ".join(blocking),
            "target_btc_weight": btc,
            "target_eth_weight": eth,
            "target_cash_weight": 1.0 - exposure,
            "target_exposure": exposure,
            "allocation": allocation,
            "reason": reason,
        })
    allocation = pd.DataFrame(contribution_rows)
    regime_activation = allocation.groupby(["macro_regime", "allocation"]).agg(
        weeks=("date", "count"),
        average_exposure=("target_exposure", "mean"),
        average_cash=("target_cash_weight", "mean"),
        average_favourable_features=("favourable_feature_count", "mean"),
    ).reset_index()
    daily_allocation = selected.weights.copy()
    daily_exposure = daily_allocation.sum(axis=1).rename("executed_exposure")
    daily = pd.DataFrame({
        "date": daily_exposure.index,
        "executed_btc_weight": daily_allocation.get("BTC", pd.Series(0.0, index=daily_allocation.index)),
        "executed_eth_weight": daily_allocation.get("ETH", pd.Series(0.0, index=daily_allocation.index)),
        "executed_exposure": daily_exposure,
        "executed_cash_weight": 1.0 - daily_exposure,
        "macro_regime": selected.macro_regime.reindex(daily_exposure.index).ffill().values,
    })
    return {
        "thresholds": _threshold_table(dataset),
        "feature_votes": votes,
        "feature_activation": activation,
        "allocation_explanations": allocation,
        "regime_activation": regime_activation,
        "daily_exposure": daily,
    }


def _simple_regime(dataset: MacroRegimeDataset, definition: dict[str, Any]) -> pd.Series:
    thresholds = dataset.thresholds[FIXED_SELECTED.gate_profile]["thresholds"]
    votes = pd.Series(0.0, index=dataset.regime_features.index)
    for feature in definition["positive"]:
        votes += (dataset.regime_features[feature] >= thresholds.get(feature, np.nan)).astype(float)
    for feature in definition["negative"]:
        votes += (dataset.regime_features[feature] <= thresholds.get(feature, np.nan)).astype(float)
    regimes = pd.Series("risk_off", index=votes.index, dtype=object)
    regimes.loc[votes >= definition["neutral_votes"]] = "neutral"
    regimes.loc[votes >= definition["risk_on_votes"]] = "risk_on"
    return regimes


def _btc_eth_weights_from_regime(dataset: MacroRegimeDataset, regimes: pd.Series) -> pd.DataFrame:
    dates = pd.DatetimeIndex(dataset.close.index[dataset.close.index.weekday == 4])
    if dates.empty:
        dates = pd.DatetimeIndex(dataset.close.index[::7])
    weights = pd.DataFrame(0.0, index=dates, columns=dataset.close.columns)
    for date in dates:
        regime = regimes.reindex([date]).ffill().iloc[0] if date in regimes.index else "risk_off"
        if regime == "risk_off":
            continue
        exposure = 1.0 if regime == "risk_on" else 0.50
        eligible = dataset.universe_weights.columns[dataset.universe_weights.loc[date] > 0]
        assets = [symbol for symbol in ("BTC", "ETH") if symbol in weights.columns and symbol in eligible]
        if assets:
            weights.loc[date, assets] = min(0.50, exposure / len(assets))
    return weights


def run_simple_gate_diagnostics(dataset: MacroRegimeDataset) -> pd.DataFrame:
    rows = []
    for name, definition in SIMPLE_GATE_DEFINITIONS.items():
        if name == "full_selected_strategy":
            weights, macro, crypto, combined = build_candidate_weights(dataset, FIXED_SELECTED)
            result = backtest_weights(dataset, weights, macro, crypto, combined, 25, FIXED_SELECTED.turnover_cap)
            regimes = macro
        else:
            regimes = _simple_regime(dataset, definition)
            weights = _btc_eth_weights_from_regime(dataset, regimes)
            crypto = pd.Series("not_used", index=regimes.index, dtype=object)
            result = backtest_weights(dataset, weights, regimes, crypto, regimes, 25, FIXED_SELECTED.turnover_cap)
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
            metrics = period_metrics(result, start, end)
            period_regime = regimes.loc[pd.Timestamp(start):pd.Timestamp(end)]
            rows.append({
                "gate": name,
                "split": split,
                "features": ", ".join((*definition["positive"], *definition["negative"])),
                "risk_on_fraction": float((period_regime == "risk_on").mean()) if len(period_regime) else np.nan,
                "neutral_fraction": float((period_regime == "neutral").mean()) if len(period_regime) else np.nan,
                "risk_off_fraction": float((period_regime == "risk_off").mean()) if len(period_regime) else np.nan,
                **metrics,
            })
    return pd.DataFrame(rows)


def rolling_performance(selected: Any) -> pd.DataFrame:
    rows = []
    returns = selected.returns.fillna(0.0)
    exposure = selected.weights.sum(axis=1).clip(0, 1)
    for window, label in ((90, "3_month"), (180, "6_month")):
        for date in returns.index:
            start = date - pd.Timedelta(days=window - 1)
            r = returns.loc[start:date]
            if len(r) < max(30, window // 3):
                continue
            wealth = (1 + r).cumprod()
            dd = wealth / wealth.cummax() - 1.0
            std = r.std()
            rows.append({
                "date": date,
                "window": label,
                "rolling_sharpe": float(r.mean() / std * np.sqrt(365)) if std and np.isfinite(std) else np.nan,
                "rolling_max_drawdown": float(dd.min()) if len(dd) else np.nan,
                "rolling_exposure": float(exposure.loc[start:date].mean()),
                "rolling_annual_turnover": float(selected.turnover.loc[start:date].sum() / max(window / 365.0, 1 / 365.0)),
            })
    return pd.DataFrame(rows)


def _weekly_metrics(weekly_returns: pd.Series) -> dict[str, float]:
    r = weekly_returns.replace([np.inf, -np.inf], np.nan).dropna()
    if r.empty:
        return {"weeks": 0, "cagr": np.nan, "sharpe": np.nan, "max_drawdown": np.nan, "worst_week": np.nan, "mean_weekly_return": np.nan}
    wealth = (1 + r).cumprod()
    dd = wealth / wealth.cummax() - 1
    std = r.std()
    return {
        "weeks": int(len(r)),
        "cagr": float(wealth.iloc[-1] ** (52 / max(len(r), 1)) - 1),
        "sharpe": float(r.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan,
        "max_drawdown": float(dd.min()),
        "worst_week": float(r.min()),
        "mean_weekly_return": float(r.mean()),
    }


def stress_period_analysis(dataset: MacroRegimeDataset, selected: Any) -> pd.DataFrame:
    selected_weekly = selected.returns.resample("W-FRI").apply(lambda values: (1 + values).prod() - 1)
    btc_weekly = dataset.returns["BTC"].reindex(selected.returns.index).fillna(0.0).resample("W-FRI").apply(lambda values: (1 + values).prod() - 1)
    eth_weekly = dataset.returns["ETH"].reindex(selected.returns.index).fillna(0.0).resample("W-FRI").apply(lambda values: (1 + values).prod() - 1)
    fifty_weekly = 0.50 * btc_weekly + 0.50 * eth_weekly
    features_weekly = dataset.regime_features.resample("W-FRI").last().reindex(selected_weekly.index).ffill()
    btc_close_weekly = dataset.close["BTC"].resample("W-FRI").last().reindex(selected_weekly.index).ffill()
    btc_drawdown = btc_close_weekly / btc_close_weekly.rolling(26, min_periods=8).max() - 1.0
    development = features_weekly.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    stress_masks = {
        "worst_btc_drawdown_weeks": btc_weekly <= btc_weekly.loc[DEVELOPMENT_START:DEVELOPMENT_END].quantile(0.10),
        "high_vix_periods": features_weekly["vix_level"] >= development["vix_level"].quantile(0.80),
        "rising_vix_periods": features_weekly["vix_change_21d"] >= development["vix_change_21d"].quantile(0.80),
        "negative_equity_momentum_periods": features_weekly["equity_momentum_21d"] < 0,
        "crypto_bear_weeks": btc_drawdown <= -0.20,
    }
    rows = []
    for stress_name, mask in stress_masks.items():
        for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END), ("full", selected_weekly.index.min(), selected_weekly.index.max())):
            period_mask = mask.loc[pd.Timestamp(start):pd.Timestamp(end)].fillna(False)
            idx = period_mask.index[period_mask]
            metrics = _weekly_metrics(selected_weekly.reindex(idx))
            btc_metrics = _weekly_metrics(btc_weekly.reindex(idx))
            fifty_metrics = _weekly_metrics(fifty_weekly.reindex(idx))
            rows.append({
                "stress_period": stress_name,
                "split": split,
                **{f"selected_{key}": value for key, value in metrics.items()},
                "btc_mean_weekly_return": btc_metrics["mean_weekly_return"],
                "btc_sharpe": btc_metrics["sharpe"],
                "btc_max_drawdown": btc_metrics["max_drawdown"],
                "btc_eth_50_50_mean_weekly_return": fifty_metrics["mean_weekly_return"],
                "btc_eth_50_50_sharpe": fifty_metrics["sharpe"],
                "btc_eth_50_50_max_drawdown": fifty_metrics["max_drawdown"],
            })
    return pd.DataFrame(rows)


def _weekly_sharpe(values: pd.Series) -> float:
    data = values.replace([np.inf, -np.inf], np.nan).dropna()
    std = data.std()
    return float(data.mean() / std * np.sqrt(52)) if std and np.isfinite(std) else np.nan


def _retention_label(value: float) -> str:
    if not np.isfinite(value):
        return "N/A"
    if value > 0.80:
        return "Excellent"
    if value >= 0.60:
        return "Good"
    if value >= 0.40:
        return "Moderate"
    return "Weak"


def development_vs_holdout_analysis(selected: Any) -> dict[str, Any]:
    development = period_metrics(selected, DEVELOPMENT_START, DEVELOPMENT_END)
    holdout = period_metrics(selected, HOLDOUT_START, HOLDOUT_END)
    sharpe_retention = holdout["Sharpe"] / development["Sharpe"] if development["Sharpe"] else np.nan
    cagr_retention = holdout["CAGR"] / development["CAGR"] if development["CAGR"] else np.nan
    daily_dev = selected.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END]
    weekly_dev = daily_dev.resample("W-FRI").apply(lambda values: (1 + values).prod() - 1).dropna()
    fold_rows = []
    if len(weekly_dev) >= 20:
        splits = combinatorial_purged_splits(len(weekly_dev), n_groups=6, n_test_groups=2, label_horizon=1, embargo=1)
        for number, split in enumerate(splits):
            fold_rows.append({
                "fold": number,
                "fold_sharpe": _weekly_sharpe(weekly_dev.iloc[list(split.test_indices)]),
                "test_groups": ",".join(str(group) for group in split.test_groups),
                "n_test_weeks": len(split.test_indices),
            })
    folds = pd.DataFrame(fold_rows)
    holdout_weekly = selected.returns.loc[HOLDOUT_START:HOLDOUT_END].resample("W-FRI").apply(lambda values: (1 + values).prod() - 1).dropna()
    holdout_weekly_sharpe = _weekly_sharpe(holdout_weekly)
    fold_values = folds.fold_sharpe.dropna() if not folds.empty else pd.Series(dtype=float)
    holdout_percentile = float((fold_values <= holdout_weekly_sharpe).mean()) if len(fold_values) and np.isfinite(holdout_weekly_sharpe) else np.nan
    summary = {
        "development": development,
        "holdout": holdout,
        "sharpe_retention": float(sharpe_retention) if np.isfinite(sharpe_retention) else np.nan,
        "sharpe_retention_label": _retention_label(sharpe_retention),
        "cagr_retention": float(cagr_retention) if np.isfinite(cagr_retention) else np.nan,
        "cagr_retention_label": _retention_label(cagr_retention),
        "drawdown_change": float(holdout["Maximum Drawdown"] - development["Maximum Drawdown"]),
        "turnover_change": float(holdout["Annual Turnover"] - development["Annual Turnover"]),
        "exposure_change": float(holdout["Exposure"] - development["Exposure"]),
        "holdout_weekly_sharpe": holdout_weekly_sharpe,
        "best_fold_sharpe": float(fold_values.max()) if len(fold_values) else np.nan,
        "median_fold_sharpe": float(fold_values.median()) if len(fold_values) else np.nan,
        "worst_fold_sharpe": float(fold_values.min()) if len(fold_values) else np.nan,
        "positive_fold_fraction": float((fold_values > 0).mean()) if len(fold_values) else np.nan,
        "holdout_percentile_vs_cpcv": holdout_percentile,
    }
    substantial_overfit = (
        (np.isfinite(sharpe_retention) and sharpe_retention < 0.40)
        or (np.isfinite(cagr_retention) and cagr_retention < 0.40)
        or (np.isfinite(holdout_percentile) and holdout_percentile < 0.25)
    )
    plausible_from_development = bool(
        np.isfinite(holdout_weekly_sharpe)
        and len(fold_values)
        and holdout_weekly_sharpe >= fold_values.quantile(0.25)
    )
    robust_degradation = bool(
        holdout["Sharpe"] > 0
        and holdout["CAGR"] > 0
        and sharpe_retention >= 0.40
        and cagr_retention >= 0.40
        and holdout["Maximum Drawdown"] > development["Maximum Drawdown"]
    )
    if np.isfinite(sharpe_retention) and np.isfinite(cagr_retention) and sharpe_retention >= 1.0 and cagr_retention >= 1.0:
        degradation_note = "No material degradation: holdout Sharpe and CAGR exceeded development-period values."
    elif robust_degradation:
        degradation_note = "Performance degraded but remained within a moderate-to-excellent retention range."
    else:
        degradation_note = "Performance degradation is too large to treat as robust without prospective monitoring."
    summary.update({
        "performance_degradation_consistent_with_robust_strategy": robust_degradation,
        "performance_degradation_note": degradation_note,
        "substantial_overfitting_suggested": substantial_overfit,
        "holdout_plausibly_explained_by_development": plausible_from_development,
        "final_generalization_conclusion": (
            "appears to generalize reasonably from development to holdout"
            if robust_degradation and plausible_from_development and not substantial_overfit
            else "generalization evidence is mixed and requires paper monitoring"
        ),
    })
    return {"summary": summary, "folds": folds}


def write_final_project_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    explain = result["explainability"]
    economic = result["economic_interpretation"]
    simple_gates: pd.DataFrame = result["simple_gates"]
    rolling: pd.DataFrame = result["rolling"]
    stress: pd.DataFrame = result["stress"]
    development_holdout = result["development_holdout"]
    benchmark_metrics: pd.DataFrame = result["benchmark"]["metrics"]
    comparisons: pd.DataFrame = result["benchmark"]["comparisons"]
    selected = result["selected"]

    explain["thresholds"].to_csv(output / "macro_gate_thresholds.csv", index=False)
    explain["feature_votes"].to_csv(output / "feature_contribution_daily.csv", index=False)
    explain["feature_activation"].to_csv(output / "feature_activation.csv", index=False)
    explain["allocation_explanations"].to_csv(output / "allocation_explanations_weekly.csv", index=False)
    explain["regime_activation"].to_csv(output / "regime_activation.csv", index=False)
    explain["daily_exposure"].to_csv(output / "daily_exposure.csv", index=False)
    simple_gates.to_csv(output / "simpler_gate_diagnostics.csv", index=False)
    rolling.to_csv(output / "rolling_performance.csv", index=False)
    stress.to_csv(output / "stress_periods.csv", index=False)
    development_holdout["folds"].to_csv(output / "development_cpcv_folds.csv", index=False)
    economic["weekly_decision_context"].to_csv(output / "weekly_decision_context.csv", index=False)
    economic["feature_state_conditioning"].to_csv(output / "feature_state_conditioning.csv", index=False)
    economic["feature_summary"].to_csv(output / "feature_economic_interpretation.csv", index=False)
    economic["regime_summary"].to_csv(output / "regime_return_allocation_summary.csv", index=False)
    economic["allocation_summary"].to_csv(output / "allocation_return_summary.csv", index=False)

    selected_holdout = period_metrics(selected, HOLDOUT_START, HOLDOUT_END)
    selected_dev = period_metrics(selected, DEVELOPMENT_START, DEVELOPMENT_END)
    holdout_bench = benchmark_metrics[(benchmark_metrics.split == "holdout") & (benchmark_metrics.cost_bps == 25)].sort_values("Sharpe", ascending=False)
    simple_holdout = simple_gates[(simple_gates.split == "holdout")].sort_values("Sharpe", ascending=False)
    activation = explain["feature_activation"].sort_values("activation_rate", ascending=False)
    allocation_summary = explain["allocation_explanations"].groupby("allocation").agg(
        weeks=("date", "count"),
        average_exposure=("target_exposure", "mean"),
        average_cash=("target_cash_weight", "mean"),
    ).reset_index()
    favourable_counts = _feature_list_counts(explain["allocation_explanations"], "favourable_features", "favourable_weeks")
    blocking_counts = _feature_list_counts(explain["allocation_explanations"], "blocking_features", "blocking_weeks")
    favourable_counts.to_csv(output / "favourable_feature_counts.csv", index=False)
    blocking_counts.to_csv(output / "blocking_feature_counts.csv", index=False)
    rolling_summary = rolling.groupby("window").agg(
        median_sharpe=("rolling_sharpe", "median"),
        worst_sharpe=("rolling_sharpe", "min"),
        median_drawdown=("rolling_max_drawdown", "median"),
        worst_drawdown=("rolling_max_drawdown", "min"),
        median_exposure=("rolling_exposure", "median"),
        median_annual_turnover=("rolling_annual_turnover", "median"),
    ).reset_index()
    stress_holdout = stress[stress.split == "holdout"]
    dev_holdout_summary = development_holdout["summary"]
    dev_holdout_table = pd.DataFrame([
        {"split": "development", **dev_holdout_summary["development"]},
        {"split": "holdout", **dev_holdout_summary["holdout"]},
    ])
    macro_strategy_payload = _load_optional_json(Path("reports/macro_regime_strategy/results.json"))
    macro_statistics = macro_strategy_payload.get("statistics", {})
    selected_costs = benchmark_metrics[
        (benchmark_metrics.name == FIXED_SELECTED.name)
        & (benchmark_metrics.split == "holdout")
    ].sort_values("cost_bps")
    v3_payload = _load_optional_json(Path("reports/macro_regime_strategy_v3/results.json"))
    v3_recommendation = v3_payload.get("recommendation", {})
    v3_dev_holdout = _load_optional_csv(Path("reports/macro_regime_strategy_v3/development_vs_holdout.csv"))
    feature_summary = economic["feature_summary"].copy()
    feature_state = economic["feature_state_conditioning"].copy()
    regime_summary = economic["regime_summary"].copy()
    allocation_return_summary = economic["allocation_summary"].copy()

    (output / "executive_summary.md").write_text(f"""# Executive summary

The final candidate is **{FIXED_SELECTED.name}**, a BTC/ETH/cash macro-risk gate.
The strategy is unchanged in this final stage. The work here is interpretation,
robustness, and documentation only.

## Final locked-holdout result at 25 bps

- CAGR: {_fmt(selected_holdout['CAGR'], True)}
- Sharpe: {_fmt(selected_holdout['Sharpe'])}
- Sortino: {_fmt(selected_holdout['Sortino'])}
- Max drawdown: {_fmt(selected_holdout['Maximum Drawdown'], True)}
- Calmar: {_fmt(selected_holdout['Calmar'])}
- Annual turnover: {_fmt(selected_holdout['Annual Turnover'])}x
- Exposure: {_fmt(selected_holdout['Exposure'], True)}
- Worst month: {_fmt(selected_holdout['Worst Month'], True)}

## Bottom line

`{FIXED_SELECTED.name}` is a strong **paper-monitoring** candidate. It is not
proven live alpha. The result is economically interesting because it avoided
much of the 2025-2026 crypto beta drawdown, but statistical controls from the
prior strategy report remain weak.
""", encoding="utf-8")

    (output / "client_specification.md").write_text(f"""# Client specification trace

## Requested final work

- Explain which macro features drive risk-on/risk-off weeks.
- Report gate activations and allocation reasons.
- Compare the fixed selected strategy with simpler diagnostic gates.
- Add rolling 3-month and 6-month Sharpe, drawdown, exposure, and turnover diagnostics.
- Add stress-period interpretation.
- Create a final report pack.

## Scope controls

- Selected strategy was not changed.
- No new model was selected.
- No benchmark tuning was used.
- Simplified gates are explanatory only.
- Final recommendation frames the strategy as paper-monitoring, not live alpha.
""", encoding="utf-8")

    (output / "methodology.md").write_text(f"""# Methodology

## Fixed strategy

The fixed strategy is `{FIXED_SELECTED.name}`:

- Universe: BTC/ETH/cash.
- Rebalance: weekly.
- Gate profile: balanced macro gate selected previously by development-only CPCV.
- Allocation: risk-on holds BTC/ETH, neutral reduces exposure, risk-off holds cash.
- Cost baseline: 25 bps, with prior cost sensitivity at 10/25/50/100 bps.

## Macro gate

The gate uses only Tier 1 WRDS macro features:

{_table(explain['thresholds'], [('feature', 'Feature'), ('orientation', 'Orientation'), ('threshold', 'Development threshold'), ('gate_profile', 'Gate profile')])}

Risk-on/risk-off classification is based on favourable-feature vote counts. The
thresholds were fixed from the development period; holdout was not used for
threshold selection.

## Diagnostic-only simplified gates

{_table(simple_holdout, [('gate', 'Gate'), ('features', 'Features'), ('risk_on_fraction', 'Risk-on fraction'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'risk_on_fraction', 'CAGR', 'Maximum Drawdown', 'Exposure'})}
""", encoding="utf-8")

    (output / "data_and_features.md").write_text(f"""# Data and features

## Data sources

- Crypto panel: Binance OHLCV research dataset.
- Macro features: WRDS CRSP/CBOE/FRB targeted daily series.
- Public crypto-native features were available in prior modules but the final
  selected strategy uses macro features only.

## Feature activation

{_table(activation, [('feature', 'Feature'), ('activation_rate', 'Activation rate'), ('favourable_weeks', 'Favourable weeks'), ('total_weeks', 'Total weeks'), ('average_value', 'Average value'), ('threshold', 'Threshold')], {'activation_rate'})}

## Most common favourable gate drivers

{_table(favourable_counts, [('feature', 'Feature'), ('favourable_weeks', 'Favourable weeks'), ('fraction_weeks', 'Fraction weeks')], {'fraction_weeks'})}

## Most common risk-off / reduced-risk blockers

{_table(blocking_counts, [('feature', 'Feature'), ('blocking_weeks', 'Blocking weeks'), ('fraction_weeks', 'Fraction weeks')], {'fraction_weeks'})}

## Regime and allocation activation

{_table(explain['regime_activation'], [('macro_regime', 'Macro regime'), ('allocation', 'Allocation'), ('weeks', 'Weeks'), ('average_exposure', 'Average exposure'), ('average_cash', 'Average cash'), ('average_favourable_features', 'Avg favourable features')], {'average_exposure', 'average_cash'})}

## Allocation explanations

The strategy target allocation is cash when the macro gate is risk-off, reduced
BTC/ETH exposure when neutral, and full BTC/ETH exposure when risk-on. Weekly
target explanations are written to `allocation_explanations_weekly.csv`.

{_table(allocation_summary, [('allocation', 'Allocation'), ('weeks', 'Weeks'), ('average_exposure', 'Average exposure'), ('average_cash', 'Average cash')], {'average_exposure', 'average_cash'})}
""", encoding="utf-8")

    (output / "results_and_benchmarks.md").write_text(f"""# Results and benchmarks

## Development and holdout

| Split | CAGR | Sharpe | Sortino | Max DD | Calmar | Annual turnover | Exposure | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Development | {_fmt(selected_dev['CAGR'], True)} | {_fmt(selected_dev['Sharpe'])} | {_fmt(selected_dev['Sortino'])} | {_fmt(selected_dev['Maximum Drawdown'], True)} | {_fmt(selected_dev['Calmar'])} | {_fmt(selected_dev['Annual Turnover'])}x | {_fmt(selected_dev['Exposure'], True)} | {_fmt(selected_dev['Worst Month'], True)} |
| Holdout | {_fmt(selected_holdout['CAGR'], True)} | {_fmt(selected_holdout['Sharpe'])} | {_fmt(selected_holdout['Sortino'])} | {_fmt(selected_holdout['Maximum Drawdown'], True)} | {_fmt(selected_holdout['Calmar'])} | {_fmt(selected_holdout['Annual Turnover'])}x | {_fmt(selected_holdout['Exposure'], True)} | {_fmt(selected_holdout['Worst Month'], True)} |

## Holdout benchmark comparison at 25 bps

{_table(holdout_bench, [('name', 'Strategy'), ('benchmark_group', 'Group'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure'), ('Worst Month', 'Worst month')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'Worst Month'})}

## Benchmark-group result

{_table(comparisons, [('benchmark_group', 'Benchmark group'), ('best_benchmark', 'Best benchmark'), ('selected_sharpe', 'Selected Sharpe'), ('best_benchmark_sharpe', 'Best benchmark Sharpe'), ('selected_cagr', 'Selected CAGR'), ('best_benchmark_cagr', 'Best benchmark CAGR'), ('beats_on_sharpe', 'Beats Sharpe'), ('beats_on_cagr', 'Beats CAGR'), ('beats_on_drawdown', 'Beats DD')], {'selected_cagr', 'best_benchmark_cagr'})}
""", encoding="utf-8")

    (output / "development_vs_holdout.md").write_text(f"""# Development vs holdout analysis

The selected strategy is fixed as **{FIXED_SELECTED.name}**. This analysis does
not retune thresholds or select a new strategy.

## Development and holdout metrics

{_table(dev_holdout_table, [('split', 'Split'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Retention and change

| Diagnostic | Value | Classification |
|---|---:|---|
| Sharpe retention | {_fmt(dev_holdout_summary['sharpe_retention'], True)} | {dev_holdout_summary['sharpe_retention_label']} |
| CAGR retention | {_fmt(dev_holdout_summary['cagr_retention'], True)} | {dev_holdout_summary['cagr_retention_label']} |
| Drawdown change | {_fmt(dev_holdout_summary['drawdown_change'], True)} | less negative is better |
| Turnover change | {_fmt(dev_holdout_summary['turnover_change'])}x | lower is better |
| Exposure change | {_fmt(dev_holdout_summary['exposure_change'], True)} | lower exposure may indicate defensive behavior |

Retention labels: Excellent >80%, Good 60-80%, Moderate 40-60%, Weak <40%.

## CPCV fold distribution

| Fold statistic | Value |
|---|---:|
| Best fold Sharpe | {_fmt(dev_holdout_summary['best_fold_sharpe'])} |
| Median fold Sharpe | {_fmt(dev_holdout_summary['median_fold_sharpe'])} |
| Worst fold Sharpe | {_fmt(dev_holdout_summary['worst_fold_sharpe'])} |
| Positive CPCV folds | {_fmt(dev_holdout_summary['positive_fold_fraction'], True)} |
| Holdout weekly Sharpe | {_fmt(dev_holdout_summary['holdout_weekly_sharpe'])} |
| Holdout percentile vs CPCV folds | {_fmt(dev_holdout_summary['holdout_percentile_vs_cpcv'], True)} |

Full fold-level diagnostics are saved to `development_cpcv_folds.csv`.

## Interpretation

- Performance degradation assessment: {dev_holdout_summary['performance_degradation_note']}
- Retention/degradation consistent with a robust strategy: {_fmt(dev_holdout_summary['performance_degradation_consistent_with_robust_strategy'])}.
- Substantial overfitting suggested: {_fmt(dev_holdout_summary['substantial_overfitting_suggested'])}.
- Holdout Sharpe plausibly explained by development performance: {_fmt(dev_holdout_summary['holdout_plausibly_explained_by_development'])}.

Final conclusion: **{dev_holdout_summary['final_generalization_conclusion']}**.
""", encoding="utf-8")

    (output / "robustness_and_limitations.md").write_text(f"""# Robustness and limitations

## Rolling diagnostics

Rolling diagnostics are saved to `rolling_performance.csv`.

{_table(rolling_summary, [('window', 'Window'), ('median_sharpe', 'Median Sharpe'), ('worst_sharpe', 'Worst Sharpe'), ('median_drawdown', 'Median drawdown'), ('worst_drawdown', 'Worst drawdown'), ('median_exposure', 'Median exposure'), ('median_annual_turnover', 'Median annual turnover')], {'median_drawdown', 'worst_drawdown', 'median_exposure'})}

## Stress-period diagnostics

{_table(stress_holdout, [('stress_period', 'Stress period'), ('selected_weeks', 'Weeks'), ('selected_cagr', 'Selected CAGR'), ('selected_sharpe', 'Selected Sharpe'), ('selected_max_drawdown', 'Selected max DD'), ('btc_mean_weekly_return', 'BTC mean weekly'), ('btc_eth_50_50_mean_weekly_return', '50/50 mean weekly')], {'selected_cagr', 'selected_max_drawdown', 'btc_mean_weekly_return', 'btc_eth_50_50_mean_weekly_return'})}

## Limitations

- The selected strategy passed mechanical holdout criteria, but prior PBO and
  deflated-Sharpe controls were weak.
- WRDS macro data availability is imperfect; some FRB fields stop before the
  full 2026 holdout.
- The Binance panel is point-in-time within the available dataset, but it may
  omit assets that were not collected historically.
- The strategy was tested retrospectively. It needs prospective paper monitoring
  before any capital decision.
- Gate orientation is empirical from the prior feature-research/selection
  process. In particular, higher VIX level being favourable should be monitored
  carefully because it may be capturing crisis-rebound conditions rather than a
  stable causal relationship.
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Recommendation

Treat **{FIXED_SELECTED.name}** as a strong paper-monitoring candidate, not
proven live alpha.

## Why it is worth monitoring

- It beat BTC, ETH, 50/50 BTC/ETH, equal-weight top-universe exposure, pure
  momentum, and the prior Tier-1 regime-momentum strategy in the locked holdout.
- It kept exposure low in hostile regimes and reduced drawdown materially.
- It survived 10, 25, 50, and 100 bps costs in the prior benchmark report.
- The rule is simple enough to paper trade manually or with a lightweight bot.

## Why it is not capital-ready

- PBO and deflated Sharpe controls from the prior report were weak.
- The holdout period contains one major regime where crypto beta performed
  poorly, which may favour cash-heavy risk gates.
- The VIX-level relationship needs prospective validation.

## Practical next step

Paper monitor the exact fixed rule for at least 3-6 months. Track:

- daily target weights;
- executed paper weights;
- macro feature values versus thresholds;
- slippage and realistic trading costs;
- divergence versus BTC/ETH and 50/50 BTC/ETH;
- whether risk-on weeks continue to show better forward returns than neutral or
  risk-off weeks.

Do not treat the current result as proven live alpha.
""", encoding="utf-8")

    _write_final_thesis_report_pack({
        "output": output,
        "selected_holdout": selected_holdout,
        "selected_dev": selected_dev,
        "holdout_bench": holdout_bench,
        "comparisons": comparisons,
        "selected_costs": selected_costs,
        "dev_holdout_table": dev_holdout_table,
        "dev_holdout_summary": dev_holdout_summary,
        "feature_summary": feature_summary,
        "feature_state": feature_state,
        "activation": activation,
        "favourable_counts": favourable_counts,
        "blocking_counts": blocking_counts,
        "regime_summary": regime_summary,
        "allocation_return_summary": allocation_return_summary,
        "thresholds": explain["thresholds"],
        "regime_activation": explain["regime_activation"],
        "rolling_summary": rolling_summary,
        "stress_holdout": stress_holdout,
        "macro_statistics": macro_statistics,
        "v3_recommendation": v3_recommendation,
        "v3_dev_holdout": v3_dev_holdout,
    })

    payload = {
        "selected_holdout": _json_safe(selected_holdout),
        "selected_development": _json_safe(selected_dev),
        "development_vs_holdout": _json_safe(development_holdout["summary"]),
        "economic_interpretation": _json_safe({
            key: value.to_dict("records") for key, value in economic.items()
        }),
        "simple_gates": _json_safe(simple_gates.to_dict("records")),
        "rolling_summary": _json_safe(rolling_summary.to_dict("records")),
        "stress": _json_safe(stress.to_dict("records")),
        "benchmark_comparisons": _json_safe(comparisons.to_dict("records")),
    }
    (output / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_final_thesis_report_pack(ctx: dict[str, Any]) -> None:
    output: Path = ctx["output"]
    selected_holdout = ctx["selected_holdout"]
    selected_dev = ctx["selected_dev"]
    holdout_bench: pd.DataFrame = ctx["holdout_bench"]
    comparisons: pd.DataFrame = ctx["comparisons"]
    selected_costs: pd.DataFrame = ctx["selected_costs"]
    dev_holdout_table: pd.DataFrame = ctx["dev_holdout_table"]
    dev_holdout_summary = ctx["dev_holdout_summary"]
    feature_summary: pd.DataFrame = ctx["feature_summary"]
    feature_state: pd.DataFrame = ctx["feature_state"]
    activation: pd.DataFrame = ctx["activation"]
    favourable_counts: pd.DataFrame = ctx["favourable_counts"]
    blocking_counts: pd.DataFrame = ctx["blocking_counts"]
    regime_summary: pd.DataFrame = ctx["regime_summary"]
    allocation_return_summary: pd.DataFrame = ctx["allocation_return_summary"]
    thresholds: pd.DataFrame = ctx["thresholds"]
    regime_activation: pd.DataFrame = ctx["regime_activation"]
    rolling_summary: pd.DataFrame = ctx["rolling_summary"]
    stress_holdout: pd.DataFrame = ctx["stress_holdout"]
    macro_statistics = ctx["macro_statistics"]
    v3_recommendation = ctx["v3_recommendation"]
    v3_dev_holdout: pd.DataFrame = ctx["v3_dev_holdout"]

    (output / "executive_summary.md").write_text(f"""# Executive summary

Project title: **Macro-Regime Conditioning for Systematic Cryptocurrency
Allocation: A Robust Out-of-Sample Evaluation**.

The selected strategy is **{FIXED_SELECTED.name}**, a fixed BTC/ETH/cash
macro-risk gate. This final stage does not change the strategy, search for new
strategies, or tune on holdout.

## Locked-holdout result at 25 bps

- CAGR: {_fmt(selected_holdout['CAGR'], True)}
- Sharpe: {_fmt(selected_holdout['Sharpe'])}
- Sortino: {_fmt(selected_holdout['Sortino'])}
- Max drawdown: {_fmt(selected_holdout['Maximum Drawdown'], True)}
- Calmar: {_fmt(selected_holdout['Calmar'])}
- Annual turnover: {_fmt(selected_holdout['Annual Turnover'])}x
- Exposure: {_fmt(selected_holdout['Exposure'], True)}
- Worst month: {_fmt(selected_holdout['Worst Month'], True)}

## Final conclusion

`{FIXED_SELECTED.name}` is a strong **paper-monitoring** candidate and a robust
research result in the limited sense that it survived the locked holdout and
beat simple crypto-beta benchmarks after costs. It is **not** proven live alpha,
and it is not guaranteed profitable.

The main caution is statistical: original macro-regime PBO is
{_fmt(macro_statistics.get('pbo'), True)} and deflated Sharpe probability is
{_fmt(macro_statistics.get('deflated_sharpe_probability'), True)}.
""", encoding="utf-8")

    (output / "client_specification.md").write_text(f"""# Client specification

## Final task

Create the final interpretation and project report pack for:

**Macro-Regime Conditioning for Systematic Cryptocurrency Allocation: A Robust
Out-of-Sample Evaluation**

## Fixed selected strategy

- Strategy: `{FIXED_SELECTED.name}`
- Do not modify the strategy.
- Do not search for new strategies.
- Do not add backtests or strategy variants.
- Explain economic interpretation, strategy mechanics, validation, benchmarks,
  cost sensitivity, PBO, deflated Sharpe, CPCV folds, simplification study, and
  limitations.

## Compliance

- Strategy logic is unchanged.
- Holdout is not used for tuning or selection.
- This report pack is interpretation and documentation only.
- Final recommendation explicitly avoids claiming guaranteed profitability.
""", encoding="utf-8")

    (output / "literature_and_motivation.md").write_text("""# Literature and motivation

Crypto allocation research often starts with asset-level return prediction.
The evidence in this project pushed in a different direction: many supervised
ML, meta-labeling, volatility-overlay, and cross-sectional momentum tests did
not produce a sufficiently robust paper-trading candidate.

The final useful hypothesis is macro-regime conditioning. BTC and ETH often
trade as high-beta liquidity assets. Their risk/reward can change when equity
momentum, equity volatility, VIX level, and VIX changes signal shifts in global
risk appetite, risk budgets, and deleveraging pressure.

The selected strategy therefore does not try to forecast every coin. It asks a
simpler question: when is it reasonable to hold BTC/ETH beta, and when should
the portfolio hold cash?
""", encoding="utf-8")

    (output / "data_and_feature_engineering.md").write_text(f"""# Data and feature engineering

## Data sources

- Crypto panel: Binance OHLCV research dataset.
- Macro features: WRDS-derived CRSP/CBOE/FRB daily features.
- Final strategy features: Tier 1 macro features only.

## Tier 1 macro features

{_table(feature_summary, [('feature', 'Feature'), ('feature_name', 'Name'), ('selected_rule', 'Selected rule'), ('economic_rationale', 'Economic rationale'), ('selected_orientation_note', 'Interpretation note')])}

## Feature activation

{_table(activation, [('feature', 'Feature'), ('activation_rate', 'Activation rate'), ('favourable_weeks', 'Favourable weeks'), ('total_weeks', 'Total weeks'), ('average_value', 'Average value'), ('threshold', 'Threshold')], {'activation_rate'})}

## Common favourable and blocking features

{_table(favourable_counts, [('feature', 'Feature'), ('favourable_weeks', 'Favourable weeks'), ('fraction_weeks', 'Fraction weeks')], {'fraction_weeks'})}

{_table(blocking_counts, [('feature', 'Feature'), ('blocking_weeks', 'Blocking weeks'), ('fraction_weeks', 'Fraction weeks')], {'fraction_weeks'})}

## Forward-return conditioning

Future returns below are next-7-day BTC/ETH 50/50 returns after weekly decision
dates. They are diagnostic labels only and are not used in live decision
features.

{_table(feature_summary, [('feature', 'Feature'), ('favourable_forward_btc_eth_7d', 'Favourable return'), ('unfavourable_forward_btc_eth_7d', 'Unfavourable return'), ('favourable_minus_unfavourable_forward_7d', 'Spread'), ('favourable_exposure', 'Favourable exposure'), ('unfavourable_exposure', 'Unfavourable exposure')], {'favourable_forward_btc_eth_7d', 'unfavourable_forward_btc_eth_7d', 'favourable_minus_unfavourable_forward_7d', 'favourable_exposure', 'unfavourable_exposure'})}
""", encoding="utf-8")

    (output / "methodology.md").write_text(f"""# Methodology

## Protocol

- Development period: {DEVELOPMENT_START.date()} to {DEVELOPMENT_END.date()}.
- Locked holdout: {HOLDOUT_START.date()} to {HOLDOUT_END.date()}.
- Candidate selection occurred in the prior macro-regime module using
  development-only CPCV.
- This final report does not introduce new strategy variants.

## Macro gate

The fixed gate uses these development-period thresholds:

{_table(thresholds, [('feature', 'Feature'), ('orientation', 'Orientation'), ('threshold', 'Threshold'), ('gate_profile', 'Gate profile')])}

Risk-on/risk-off classification is based on favourable-feature vote counts. The
thresholds are fixed before holdout evaluation.

## Evaluation metrics

The report uses CAGR, Sharpe, Sortino, max drawdown, Calmar, turnover, exposure,
cost sensitivity, CPCV fold distribution, PBO, and deflated Sharpe probability.
""", encoding="utf-8")

    (output / "strategy_design.md").write_text(f"""# Strategy design

## Allocation rule

`{FIXED_SELECTED.name}` is a BTC/ETH/cash allocation strategy.

- **Risk-on:** target BTC/ETH exposure, usually 50% BTC and 50% ETH when both
  are eligible.
- **Neutral:** target reduced BTC/ETH exposure, usually 25% BTC and 25% ETH
  with 50% cash.
- **Risk-off:** hold cash.
- If only one of BTC/ETH is eligible, the single-asset weight is capped at 50%.

## Why it de-risks

The strategy de-risks when the macro feature vote count is insufficient. The
economic idea is that crypto beta should be held only when cross-asset risk
conditions are supportive enough.

## Turnover and costs

- Rebalance: weekly.
- Turnover cap: {FIXED_SELECTED.turnover_cap:.2f}.
- Baseline transaction cost: 25 bps.
- Cost sensitivity: 10, 25, 50, and 100 bps.
- Costs are deducted as turnover multiplied by the bps cost rate.

## Regime frequency and allocation contribution

{_table(regime_summary, [('macro_regime', 'Regime'), ('weeks', 'Weeks'), ('frequency', 'Frequency'), ('average_forward_btc_eth_50_50_7d', 'Forward BTC/ETH 7d'), ('average_target_btc_weight', 'BTC weight'), ('average_target_eth_weight', 'ETH weight'), ('average_target_cash_weight', 'Cash weight'), ('average_target_exposure', 'Exposure')], {'frequency', 'average_forward_btc_eth_50_50_7d', 'average_target_btc_weight', 'average_target_eth_weight', 'average_target_cash_weight', 'average_target_exposure'})}

{_table(allocation_return_summary, [('allocation', 'Allocation'), ('weeks', 'Weeks'), ('frequency', 'Frequency'), ('average_forward_btc_eth_50_50_7d', 'Forward BTC/ETH 7d'), ('average_target_btc_weight', 'BTC weight'), ('average_target_eth_weight', 'ETH weight'), ('average_target_cash_weight', 'Cash weight'), ('average_target_exposure', 'Exposure')], {'frequency', 'average_forward_btc_eth_50_50_7d', 'average_target_btc_weight', 'average_target_eth_weight', 'average_target_cash_weight', 'average_target_exposure'})}
""", encoding="utf-8")

    (output / "results_and_benchmarks.md").write_text(f"""# Results and benchmarks

## Development and holdout

{_table(dev_holdout_table, [('split', 'Split'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Holdout benchmark comparison at 25 bps

{_table(holdout_bench, [('name', 'Strategy'), ('benchmark_group', 'Group'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure'), ('Worst Month', 'Worst month')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'Worst Month'})}

## Benchmark-group result

{_table(comparisons, [('benchmark_group', 'Benchmark group'), ('best_benchmark', 'Best benchmark'), ('selected_sharpe', 'Selected Sharpe'), ('best_benchmark_sharpe', 'Best benchmark Sharpe'), ('selected_cagr', 'Selected CAGR'), ('best_benchmark_cagr', 'Best benchmark CAGR'), ('beats_on_sharpe', 'Beats Sharpe'), ('beats_on_cagr', 'Beats CAGR'), ('beats_on_drawdown', 'Beats drawdown')], {'selected_cagr', 'best_benchmark_cagr'})}

## Cost sensitivity

{_table(selected_costs, [('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Sortino', 'Sortino'), ('Maximum Drawdown', 'Max DD'), ('Calmar', 'Calmar'), ('Annual Turnover', 'Turnover'), ('Exposure', 'Exposure'), ('Transaction Costs', 'Transaction costs')], {'CAGR', 'Maximum Drawdown', 'Exposure', 'Transaction Costs'})}
""", encoding="utf-8")

    (output / "robustness_and_statistical_validation.md").write_text(f"""# Robustness and statistical validation

## Development vs holdout retention

| Diagnostic | Value | Classification |
|---|---:|---|
| Sharpe retention | {_fmt(dev_holdout_summary['sharpe_retention'], True)} | {dev_holdout_summary['sharpe_retention_label']} |
| CAGR retention | {_fmt(dev_holdout_summary['cagr_retention'], True)} | {dev_holdout_summary['cagr_retention_label']} |
| Drawdown change | {_fmt(dev_holdout_summary['drawdown_change'], True)} | less negative is better |
| Turnover change | {_fmt(dev_holdout_summary['turnover_change'])}x | lower is better |
| Exposure change | {_fmt(dev_holdout_summary['exposure_change'], True)} | lower exposure may indicate defensive behaviour |

## CPCV fold distribution

| Statistic | Value |
|---|---:|
| Best fold Sharpe | {_fmt(dev_holdout_summary['best_fold_sharpe'])} |
| Median fold Sharpe | {_fmt(dev_holdout_summary['median_fold_sharpe'])} |
| Worst fold Sharpe | {_fmt(dev_holdout_summary['worst_fold_sharpe'])} |
| Positive CPCV folds | {_fmt(dev_holdout_summary['positive_fold_fraction'], True)} |
| Holdout weekly Sharpe | {_fmt(dev_holdout_summary['holdout_weekly_sharpe'])} |
| Holdout percentile vs CPCV folds | {_fmt(dev_holdout_summary['holdout_percentile_vs_cpcv'], True)} |

## PBO and deflated Sharpe

- Original macro-regime tested configurations: {macro_statistics.get('tested_configurations', 'N/A')}
- PBO: {_fmt(macro_statistics.get('pbo'), True)}
- Deflated Sharpe probability: {_fmt(macro_statistics.get('deflated_sharpe_probability'), True)}

These controls are material. They prevent the holdout result from being treated
as proof of live alpha.

## Simplification study

The v3 simplification study tested only four small macro gates plus the current
strategy. It did not search for unrelated strategies. Its final decision was:
**{v3_recommendation.get('decision', 'N/A')}**.

{_table(v3_dev_holdout, [('candidate', 'Candidate'), ('development_sharpe', 'Dev Sharpe'), ('holdout_sharpe', 'Holdout Sharpe'), ('sharpe_retention', 'Retention'), ('development_cagr', 'Dev CAGR'), ('holdout_cagr', 'Holdout CAGR'), ('development_max_drawdown', 'Dev max DD'), ('holdout_max_drawdown', 'Holdout max DD')], {'sharpe_retention', 'development_cagr', 'holdout_cagr', 'development_max_drawdown', 'holdout_max_drawdown'})}

## Rolling and stress diagnostics

{_table(rolling_summary, [('window', 'Window'), ('median_sharpe', 'Median Sharpe'), ('worst_sharpe', 'Worst Sharpe'), ('median_drawdown', 'Median DD'), ('worst_drawdown', 'Worst DD'), ('median_exposure', 'Median exposure'), ('median_annual_turnover', 'Median turnover')], {'median_drawdown', 'worst_drawdown', 'median_exposure'})}

{_table(stress_holdout, [('stress_period', 'Stress period'), ('selected_weeks', 'Weeks'), ('selected_cagr', 'Selected CAGR'), ('selected_sharpe', 'Selected Sharpe'), ('selected_max_drawdown', 'Selected max DD'), ('btc_mean_weekly_return', 'BTC mean weekly'), ('btc_eth_50_50_mean_weekly_return', '50/50 mean weekly')], {'selected_cagr', 'selected_max_drawdown', 'btc_mean_weekly_return', 'btc_eth_50_50_mean_weekly_return'})}
""", encoding="utf-8")

    (output / "economic_interpretation.md").write_text(f"""# Economic interpretation

The strategy uses macro variables to decide whether the market environment is
favourable enough to hold BTC/ETH exposure. It does not directly predict
individual coin returns.

## Feature-level interpretation

{_table(feature_summary, [('feature', 'Feature'), ('selected_rule', 'Selected rule'), ('economic_rationale', 'Economic rationale'), ('selected_orientation_note', 'Orientation caveat')])}

## Favourable vs unfavourable future crypto returns

The table uses next-7-day BTC/ETH 50/50 returns after weekly decision dates.
These returns are diagnostic only.

{_table(feature_summary, [('feature', 'Feature'), ('favourable_frequency', 'Favourable frequency'), ('favourable_forward_btc_eth_7d', 'Favourable return'), ('unfavourable_forward_btc_eth_7d', 'Unfavourable return'), ('favourable_minus_unfavourable_forward_7d', 'Spread'), ('favourable_exposure', 'Favourable exposure'), ('unfavourable_exposure', 'Unfavourable exposure')], {'favourable_frequency', 'favourable_forward_btc_eth_7d', 'unfavourable_forward_btc_eth_7d', 'favourable_minus_unfavourable_forward_7d', 'favourable_exposure', 'unfavourable_exposure'})}

## Cash/BTC/ETH allocation contribution

{_table(feature_state, [('feature', 'Feature'), ('state', 'State'), ('weeks', 'Weeks'), ('frequency', 'Frequency'), ('average_target_btc_weight', 'BTC weight'), ('average_target_eth_weight', 'ETH weight'), ('average_target_cash_weight', 'Cash weight'), ('average_target_exposure', 'Exposure'), ('exposure_contribution', 'Exposure contribution')], {'frequency', 'average_target_btc_weight', 'average_target_eth_weight', 'average_target_cash_weight', 'average_target_exposure', 'exposure_contribution'}, limit=20)}

## Risk-on/risk-off frequency and forward returns

{_table(regime_summary, [('macro_regime', 'Regime'), ('weeks', 'Weeks'), ('frequency', 'Frequency'), ('average_forward_btc_eth_50_50_7d', 'Forward BTC/ETH 7d'), ('hit_rate_btc_eth_50_50_7d', 'Hit rate'), ('average_target_btc_weight', 'BTC weight'), ('average_target_eth_weight', 'ETH weight'), ('average_target_cash_weight', 'Cash weight'), ('average_target_exposure', 'Exposure')], {'frequency', 'average_forward_btc_eth_50_50_7d', 'hit_rate_btc_eth_50_50_7d', 'average_target_btc_weight', 'average_target_eth_weight', 'average_target_cash_weight', 'average_target_exposure'})}

## Interpretation caveat

Positive equity momentum and falling VIX changes have clear risk-on
interpretations. Higher VIX level and higher Dow volatility level are more
empirical. They should be interpreted as conditional rebound/risk-premium
signals, not as a universal claim that high volatility is good for crypto.
""", encoding="utf-8")

    (output / "limitations.md").write_text(f"""# Limitations

- The strategy is a retrospective research result, not proven live alpha.
- Original macro-regime PBO is {_fmt(macro_statistics.get('pbo'), True)}, which is high enough to require caution.
- Deflated Sharpe probability is {_fmt(macro_statistics.get('deflated_sharpe_probability'), True)}, so statistical confidence is limited.
- The 2025-2026 holdout was favourable to cash-heavy risk gates because simple crypto beta performed poorly.
- Some feature orientations are empirical rather than structural, especially high VIX level and high Dow volatility level.
- WRDS macro data coverage can be imperfect near the end of the sample.
- The Binance panel is point-in-time within the collected dataset but may omit assets not collected historically.
- Live slippage, spreads, funding constraints, API outages, tax effects, and operational errors are not fully captured.
- The next step is paper monitoring, not capital deployment.
""", encoding="utf-8")

    (output / "final_recommendation.md").write_text(f"""# Final recommendation

## Recommendation

Treat **{FIXED_SELECTED.name}** as a strong paper-monitoring candidate and a
robust research result, but **not** as proven live alpha.

## Why it is worth monitoring

- Locked-holdout Sharpe is {_fmt(selected_holdout['Sharpe'])}.
- Locked-holdout CAGR is {_fmt(selected_holdout['CAGR'], True)}.
- Locked-holdout max drawdown is {_fmt(selected_holdout['Maximum Drawdown'], True)}.
- It beat BTC, ETH, 50/50 BTC/ETH, equal-weight top-universe exposure, pure
  momentum, and the prior Tier-1 regime-momentum strategy in the locked holdout.
- It survived 10, 25, 50, and 100 bps transaction-cost assumptions.
- The rule is simple enough to paper monitor.

## Why it is not capital-ready

- PBO is {_fmt(macro_statistics.get('pbo'), True)}.
- Deflated Sharpe probability is {_fmt(macro_statistics.get('deflated_sharpe_probability'), True)}.
- The simplification study did not find a cleaner replacement; the simpler
  development-selected gate failed the locked holdout.
- The holdout period penalized long-only crypto beta, which may have favoured a
  cash-heavy gate.

## Practical next step

Paper monitor the exact fixed rule for at least 3-6 months. Track target
weights, executed paper weights, macro feature values versus thresholds,
slippage, realised costs, benchmark divergence, and whether risk-on weeks
continue to deliver better forward BTC/ETH returns than neutral/risk-off weeks.

Do not claim guaranteed profitability. Do not allocate capital until prospective
paper results support the retrospective evidence.
""", encoding="utf-8")


def _selected_rule_for_feature(feature: str) -> str:
    if feature in MACRO_POSITIVE_FEATURES:
        return "value >= development threshold"
    if feature in MACRO_NEGATIVE_FEATURES:
        return "value <= development threshold"
    return "not used"


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


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


def _feature_list_counts(frame: pd.DataFrame, column: str, count_name: str) -> pd.DataFrame:
    if frame.empty or column not in frame:
        return pd.DataFrame(columns=["feature", count_name, "fraction_weeks"])
    values = (
        frame[column]
        .fillna("")
        .astype(str)
        .str.split(", ")
        .explode()
        .replace("", np.nan)
        .dropna()
    )
    if values.empty:
        return pd.DataFrame(columns=["feature", count_name, "fraction_weeks"])
    counts = values.value_counts().rename_axis("feature").reset_index(name=count_name)
    counts["fraction_weeks"] = counts[count_name] / max(len(frame), 1)
    return counts


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, pd.Series):
        return _json_safe(value.to_dict())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value)
    return value


def run_default_final_project_report(output_dir: str | Path = "reports/final_project") -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_final_project_analysis(panel, macro, public_data, probability)
    write_final_project_reports(output_dir, result)
    return result


__all__ = [
    "run_final_project_analysis",
    "write_final_project_reports",
    "run_default_final_project_report",
    "SIMPLE_GATE_DEFINITIONS",
    "development_vs_holdout_analysis",
]
