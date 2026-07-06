"""Benchmark and universe comparison for the fixed macro-regime strategy.

The selected strategy is intentionally fixed as ``btc_eth_macro_gate_balanced``.
This module does not rerun model selection, tune thresholds, or choose a new
candidate.  It only compares the fixed strategy against simple beta, point-in-
time universe exposure, pure momentum, and the prior Tier-1 regime-gated
momentum result.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .macro_regime_strategy import (
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    MacroRegimeCandidate,
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    load_macro_features,
    load_volatility_probability,
    period_metrics,
)
from .public_crypto_data import PublicDataBundle


FIXED_SELECTED = MacroRegimeCandidate(
    name="btc_eth_macro_gate_balanced",
    family="BTC/ETH/cash macro risk gate",
    gate_profile="balanced",
    use_crypto_gate=False,
    allocation="btc_eth",
    rebalance_days=7,
    top_k=5,
    universe_size=10,
    max_asset_weight=0.20,
    turnover_cap=0.75,
)


def _all_risk_on(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series, pd.Series]:
    risk_on = pd.Series("risk_on", index=index, dtype=object)
    crypto = pd.Series("not_used", index=index, dtype=object)
    return risk_on, crypto, risk_on


def _equal_weight_top_n(dataset: MacroRegimeDataset) -> pd.DataFrame:
    active = dataset.universe_weights > 0
    denominator = active.sum(axis=1).replace(0, np.nan)
    return active.div(denominator, axis=0).fillna(0.0)


def _buy_hold_weights(dataset: MacroRegimeDataset, name: str) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=dataset.close.index, columns=dataset.close.columns)
    if name == "btc_buy_hold":
        if "BTC" in weights:
            weights["BTC"] = 1.0
    elif name == "eth_buy_hold":
        if "ETH" in weights:
            weights["ETH"] = 1.0
    elif name == "btc_eth_50_50":
        for symbol in ("BTC", "ETH"):
            if symbol in weights:
                weights[symbol] = 0.50
    else:
        raise ValueError(name)
    return weights


def _pure_momentum_weights(dataset: MacroRegimeDataset, top_k: int = 5) -> pd.DataFrame:
    candidate = MacroRegimeCandidate(
        name=f"pure_top{dataset.metadata['universe_size']}_momentum",
        family=f"Pure top-{dataset.metadata['universe_size']} momentum benchmark",
        gate_profile="balanced",
        use_crypto_gate=False,
        allocation="top10_momentum",
        rebalance_days=7,
        top_k=top_k,
        universe_size=int(dataset.metadata["universe_size"]),
        max_asset_weight=0.20,
        turnover_cap=0.75,
    )
    weights, _, _, _ = build_candidate_weights(dataset, candidate, combined_override="always_on")
    return weights


def _evaluate_target(
    dataset: MacroRegimeDataset,
    name: str,
    family: str,
    benchmark_group: str,
    weights: pd.DataFrame,
    cost_bps: int,
    universe_size: int | None = None,
    turnover_cap: float = 0.75,
) -> dict[str, Any]:
    macro, crypto, combined = _all_risk_on(dataset.close.index)
    result = backtest_weights(dataset, weights, macro, crypto, combined, cost_bps=cost_bps, turnover_cap=turnover_cap)
    rows = []
    for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
        rows.append({
            "name": name,
            "family": family,
            "benchmark_group": benchmark_group,
            "split": split,
            "cost_bps": cost_bps,
            "universe_size": universe_size,
            **period_metrics(result, start, end),
        })
    return {"result": result, "rows": rows}


def _evaluate_selected(dataset: MacroRegimeDataset, cost_bps: int) -> dict[str, Any]:
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
    rows = []
    for split, start, end in (("development", DEVELOPMENT_START, DEVELOPMENT_END), ("holdout", HOLDOUT_START, HOLDOUT_END)):
        rows.append({
            "name": FIXED_SELECTED.name,
            "family": FIXED_SELECTED.family,
            "benchmark_group": "selected_fixed_strategy",
            "split": split,
            "cost_bps": cost_bps,
            "universe_size": 10,
            **period_metrics(result, start, end),
        })
    return {"result": result, "rows": rows}


def _prior_tier1_rows(path: str | Path = "reports/tier1_regime_momentum/metrics.csv") -> pd.DataFrame:
    metrics_path = Path(path)
    if not metrics_path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(metrics_path)
    winner_name = None
    result_json = metrics_path.with_name("results.json")
    if result_json.exists():
        try:
            payload = json.loads(result_json.read_text(encoding="utf-8"))
            winner_name = payload.get("winner", {}).get("name")
        except Exception:
            winner_name = None
    if winner_name is None:
        candidates = frame[frame.category.astype(str).eq("strategy")]
        if not candidates.empty:
            winner_name = str(candidates.iloc[0]["name"])
    if winner_name is None:
        return pd.DataFrame()
    selected = frame[(frame.name == winner_name) & (frame.category.astype(str).eq("strategy"))].copy()
    if selected.empty:
        return pd.DataFrame()
    selected["family"] = "Prior best Tier-1 regime-gated momentum"
    selected["benchmark_group"] = "prior_tier1_regime_momentum"
    selected["universe_size"] = selected.get("universe_size", 10)
    return selected


def run_macro_regime_benchmark_analysis(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    """Evaluate fixed selected strategy against requested benchmarks."""
    datasets = {
        size: build_macro_regime_dataset(
            panel,
            macro_features,
            public_data=public_data,
            volatility_probability=volatility_probability,
            universe_size=size,
        )
        for size in (10, 20, 30)
    }
    rows: list[dict[str, Any]] = []
    results: dict[str, PortfolioResult] = {}

    selected_dataset = datasets[10]
    for cost in COST_LEVELS:
        evaluated = _evaluate_selected(selected_dataset, cost)
        rows.extend(evaluated["rows"])
        results[f"{FIXED_SELECTED.name}_{cost}"] = evaluated["result"]

    for name, family in (
        ("btc_buy_hold", "BTC buy-and-hold"),
        ("eth_buy_hold", "ETH buy-and-hold"),
        ("btc_eth_50_50", "50/50 BTC/ETH"),
    ):
        for cost in COST_LEVELS:
            evaluated = _evaluate_target(
                selected_dataset,
                name=name,
                family=family,
                benchmark_group="simple_crypto_beta",
                weights=_buy_hold_weights(selected_dataset, name),
                cost_bps=cost,
                universe_size=None,
                turnover_cap=10.0,
            )
            rows.extend(evaluated["rows"])
            results[f"{name}_{cost}"] = evaluated["result"]

    for universe_size, dataset in datasets.items():
        equal_weights = _equal_weight_top_n(dataset)
        momentum_weights = _pure_momentum_weights(dataset, top_k=5)
        for cost in COST_LEVELS:
            evaluated_equal = _evaluate_target(
                dataset,
                name=f"equal_weight_top{universe_size}",
                family=f"Equal-weight top {universe_size}",
                benchmark_group="point_in_time_top_universe",
                weights=equal_weights,
                cost_bps=cost,
                universe_size=universe_size,
            )
            rows.extend(evaluated_equal["rows"])
            results[f"equal_weight_top{universe_size}_{cost}"] = evaluated_equal["result"]
            evaluated_momentum = _evaluate_target(
                dataset,
                name=f"pure_top{universe_size}_momentum",
                family=f"Pure top-{universe_size} momentum",
                benchmark_group="point_in_time_momentum",
                weights=momentum_weights,
                cost_bps=cost,
                universe_size=universe_size,
            )
            rows.extend(evaluated_momentum["rows"])
            results[f"pure_top{universe_size}_momentum_{cost}"] = evaluated_momentum["result"]

    metrics = pd.DataFrame(rows)
    prior = _prior_tier1_rows()
    if not prior.empty:
        prior = prior.copy()
        prior["benchmark_group"] = "prior_tier1_regime_momentum"
        prior["family"] = "Prior best Tier-1 regime-gated momentum"
        prior["universe_size"] = prior.get("universe_size", 10)
        metrics = pd.concat([metrics, prior[metrics.columns.intersection(prior.columns)]], ignore_index=True, sort=False)

    selected_holdout_25 = metrics[
        (metrics.name == FIXED_SELECTED.name)
        & (metrics.split == "holdout")
        & (metrics.cost_bps == 25)
    ].iloc[0]
    holdout_25 = metrics[(metrics.split == "holdout") & (metrics.cost_bps == 25)].copy()
    comparisons = []
    for group in ("simple_crypto_beta", "point_in_time_top_universe", "point_in_time_momentum", "prior_tier1_regime_momentum"):
        subset = holdout_25[holdout_25.benchmark_group == group]
        if subset.empty:
            continue
        best = subset.sort_values("Sharpe", ascending=False).iloc[0]
        comparisons.append({
            "benchmark_group": group,
            "best_benchmark": best["name"],
            "selected_sharpe": selected_holdout_25["Sharpe"],
            "best_benchmark_sharpe": best["Sharpe"],
            "selected_cagr": selected_holdout_25["CAGR"],
            "best_benchmark_cagr": best["CAGR"],
            "selected_max_drawdown": selected_holdout_25["Maximum Drawdown"],
            "best_benchmark_max_drawdown": best["Maximum Drawdown"],
            "beats_on_sharpe": bool(selected_holdout_25["Sharpe"] > best["Sharpe"]),
            "beats_on_cagr": bool(selected_holdout_25["CAGR"] > best["CAGR"]),
            "beats_on_drawdown": bool(selected_holdout_25["Maximum Drawdown"] > best["Maximum Drawdown"]),
        })
    return {
        "metrics": metrics,
        "comparisons": pd.DataFrame(comparisons),
        "selected_candidate": asdict(FIXED_SELECTED),
        "survivorship_notes": {
            "point_in_time": "Top-universe benchmarks use lagged liquidity-based universe construction and exclude stable/wrapped assets.",
            "source_limitation": "The Binance panel itself contains only assets available in the existing research dataset; missing historical listings cannot be recovered.",
            "not_survivorship_biased": "The benchmark construction does not use today's top coins retroactively.",
        },
    }


def write_macro_regime_benchmark_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    metrics: pd.DataFrame = result["metrics"]
    comparisons: pd.DataFrame = result["comparisons"]
    metrics.to_csv(output / "benchmark_metrics.csv", index=False)
    comparisons.to_csv(output / "benchmark_group_comparisons.csv", index=False)

    holdout_25 = metrics[(metrics.split == "holdout") & (metrics.cost_bps == 25)].sort_values("Sharpe", ascending=False)
    selected_costs = metrics[
        (metrics.name == FIXED_SELECTED.name)
        & (metrics.split == "holdout")
    ].sort_values("cost_bps")
    simple_beta = holdout_25[holdout_25.benchmark_group.isin(["selected_fixed_strategy", "simple_crypto_beta", "prior_tier1_regime_momentum"])]
    universe = holdout_25[holdout_25.benchmark_group.isin(["selected_fixed_strategy", "point_in_time_top_universe", "point_in_time_momentum"])]
    cost_sensitivity = metrics[metrics.split == "holdout"].sort_values(["name", "cost_bps"])

    columns = [
        ("name", "Strategy"),
        ("benchmark_group", "Group"),
        ("CAGR", "CAGR"),
        ("Sharpe", "Sharpe"),
        ("Sortino", "Sortino"),
        ("Maximum Drawdown", "Max DD"),
        ("Calmar", "Calmar"),
        ("Annual Turnover", "Annual turnover"),
        ("Exposure", "Exposure"),
        ("Transaction Costs", "Transaction costs"),
        ("Worst Month", "Worst month"),
    ]
    percent = {"CAGR", "Maximum Drawdown", "Exposure", "Transaction Costs", "Worst Month"}
    comparison_text = _comparison_summary(comparisons)
    notes = result["survivorship_notes"]

    (output / "benchmark_comparison.md").write_text(f"""# Macro-regime selected strategy benchmark comparison

Selected strategy is fixed as **{FIXED_SELECTED.name}**. This report does not modify the selected strategy,
tune on benchmarks, or select a new model.

## Locked holdout at 25 bps

{_table(simple_beta, columns, percent)}

## Cost sensitivity for selected strategy

{_table(selected_costs, columns, percent)}

## All holdout cost sensitivity

{_table(cost_sensitivity, [("name", "Strategy"), ("cost_bps", "Cost bps"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Sortino", "Sortino"), ("Maximum Drawdown", "Max DD"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure"), ("Transaction Costs", "Transaction costs"), ("Worst Month", "Worst month")], percent)}

## Group comparison

{_table(comparisons, [("benchmark_group", "Benchmark group"), ("best_benchmark", "Best benchmark"), ("selected_sharpe", "Selected Sharpe"), ("best_benchmark_sharpe", "Best benchmark Sharpe"), ("selected_cagr", "Selected CAGR"), ("best_benchmark_cagr", "Best benchmark CAGR"), ("selected_max_drawdown", "Selected max DD"), ("best_benchmark_max_drawdown", "Best benchmark max DD"), ("beats_on_sharpe", "Beats Sharpe"), ("beats_on_cagr", "Beats CAGR"), ("beats_on_drawdown", "Beats DD")], {"selected_cagr", "best_benchmark_cagr", "selected_max_drawdown", "best_benchmark_max_drawdown"})}

## Conclusion

{comparison_text}
""", encoding="utf-8")

    (output / "universe_benchmark_comparison.md").write_text(f"""# Universe benchmark comparison

## Method

- Equal-weight top-universe benchmarks use point-in-time top 10, top 20, and top
  30 liquid universes.
- Pure momentum benchmarks use the same point-in-time universe construction,
  rank by lagged 63-day momentum, and hold the top 5 assets weekly.
- Stablecoins and wrapped assets are excluded.
- Universe membership uses lagged liquidity/history through the existing
  `point_in_time_liquid_universe` builder.
- This is not today's-top-coins retroactively applied.

## Survivorship and data limitations

- {notes['point_in_time']}
- {notes['source_limitation']}
- {notes['not_survivorship_biased']}

## Locked holdout at 25 bps

{_table(universe, columns, percent)}

## Universe benchmark cost sensitivity

{_table(cost_sensitivity[cost_sensitivity.benchmark_group.isin(["selected_fixed_strategy", "point_in_time_top_universe", "point_in_time_momentum"])], [("name", "Strategy"), ("cost_bps", "Cost bps"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Sortino", "Sortino"), ("Maximum Drawdown", "Max DD"), ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure"), ("Transaction Costs", "Transaction costs"), ("Worst Month", "Worst month")], percent)}

## Conclusion

{comparison_text}
""", encoding="utf-8")


def _comparison_summary(comparisons: pd.DataFrame) -> str:
    if comparisons.empty:
        return "Comparison table is empty; benchmark data was unavailable."
    pieces = []
    labels = {
        "simple_crypto_beta": "simple crypto beta",
        "point_in_time_top_universe": "top-universe exposure",
        "point_in_time_momentum": "pure momentum",
        "prior_tier1_regime_momentum": "the prior best Tier-1 regime-gated momentum strategy",
    }
    for row in comparisons.to_dict("records"):
        group = labels.get(row["benchmark_group"], row["benchmark_group"])
        if row["beats_on_sharpe"] and row["beats_on_cagr"] and row["beats_on_drawdown"]:
            pieces.append(f"- The selected strategy beats {group} after costs on Sharpe, CAGR, and max drawdown.")
        else:
            misses = []
            if not row["beats_on_sharpe"]:
                misses.append("Sharpe")
            if not row["beats_on_cagr"]:
                misses.append("CAGR")
            if not row["beats_on_drawdown"]:
                misses.append("max drawdown")
            pieces.append(
                f"- The selected strategy does not fully beat {group}; weaker dimensions: {', '.join(misses)}."
            )
    pieces.append("- Universe benchmarks are point-in-time within the available Binance research panel, but the panel may still omit assets not present in the collected historical dataset.")
    return "\n".join(pieces)


def _fmt(value: Any, percent: bool = False) -> str:
    if value is None or (isinstance(value, (float, np.floating)) and not np.isfinite(value)):
        return "N/A"
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if value else "No"
    if isinstance(value, (float, np.floating)):
        return f"{value:.2%}" if percent else f"{value:.3f}"
    return str(value)


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]], percent: set[str] | None = None) -> str:
    percent = percent or set()
    if frame is None or frame.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in frame.to_dict("records"):
        lines.append("| " + " | ".join(_fmt(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def load_default_inputs(
    data_path: str | Path = "data/binance_usdt_broad_2019.csv",
    macro_path: str | Path = "data/processed/wrds_macro_features/wrds_macro_features_daily.csv",
    public_data_dir: str | Path = "data/processed/public_crypto",
    volatility_predictions: str | Path = "reports/volatility_expansion/predictions.csv",
) -> tuple[pd.DataFrame, pd.DataFrame, PublicDataBundle | None, pd.Series | None]:
    from .data import DataIngestion
    from .public_crypto_data import load_processed_public_data

    panel = DataIngestion().load_csv(str(data_path))
    macro = load_macro_features(macro_path)
    public_data = load_processed_public_data(public_data_dir)
    probability = load_volatility_probability(volatility_predictions)
    return panel, macro, public_data, probability


__all__ = [
    "FIXED_SELECTED",
    "run_macro_regime_benchmark_analysis",
    "write_macro_regime_benchmark_reports",
    "load_default_inputs",
]
