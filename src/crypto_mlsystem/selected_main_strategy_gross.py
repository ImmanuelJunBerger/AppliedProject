"""Exact gross and cost-sensitivity reporting for the frozen main strategy.

This module does not search for strategies, tune thresholds, or modify the
selected candidate.  It reruns the frozen ``btc_eth_macro_gate_balanced`` rule
with an explicit 0 bps transaction-cost assumption so gross performance is
available without estimating it from cost-sensitive rows.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START
from .macro_regime_benchmark_analysis import FIXED_SELECTED, load_default_inputs
from .macro_regime_strategy import (
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    MacroRegimeDataset,
    PortfolioResult,
    backtest_weights,
    build_candidate_weights,
    build_macro_regime_dataset,
    period_metrics,
)
from .public_crypto_data import PublicDataBundle


ANALYSIS_COST_LEVELS = (0, *COST_LEVELS)
SELECTED_STRATEGY_NAME = FIXED_SELECTED.name
REPORT_TITLE = "Selected Main Strategy Gross and Consolidated Performance"

METRIC_COLUMNS = [
    "CAGR",
    "Sharpe",
    "Sortino",
    "Calmar",
    "Annualized Volatility",
    "Maximum Drawdown",
    "Annual Turnover",
    "Turnover",
    "Exposure",
    "Cash Allocation",
    "Worst Month",
    "Best Month",
    "Hit Rate",
    "Average Holdings",
    "Transaction Costs",
]


def _metric_rows_for_result(result: PortfolioResult, cost_bps: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split, start, end in (
        ("development", DEVELOPMENT_START, DEVELOPMENT_END),
        ("holdout", HOLDOUT_START, HOLDOUT_END),
    ):
        rows.append({
            "strategy": SELECTED_STRATEGY_NAME,
            "family": FIXED_SELECTED.family,
            "split": split,
            "start": str(pd.Timestamp(start).date()),
            "end": str(pd.Timestamp(end).date()),
            "cost_bps": cost_bps,
            "performance_basis": (
                "exact_gross_0bps_no_transaction_costs"
                if cost_bps == 0
                else "net_after_transaction_costs"
            ),
            **period_metrics(result, start, end),
        })
    return rows


def _consolidated_table(metrics: pd.DataFrame) -> pd.DataFrame:
    id_cols = ["strategy", "family", "cost_bps", "performance_basis"]
    rows: list[dict[str, Any]] = []
    available_metrics = [column for column in METRIC_COLUMNS if column in metrics.columns]
    for keys, group in metrics.groupby(id_cols, dropna=False):
        row = dict(zip(id_cols, keys))
        for split in ("development", "holdout"):
            split_row = group[group["split"].astype(str).eq(split)]
            if split_row.empty:
                continue
            item = split_row.iloc[0]
            row[f"{split}_start"] = item.get("start")
            row[f"{split}_end"] = item.get("end")
            for column in available_metrics:
                row[f"{split}_{column}"] = item.get(column, np.nan)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("cost_bps").reset_index(drop=True)


def run_selected_main_strategy_gross_report(
    panel: pd.DataFrame,
    macro_features: pd.DataFrame,
    public_data: PublicDataBundle | None = None,
    volatility_probability: pd.Series | None = None,
) -> dict[str, Any]:
    """Rerun the frozen selected strategy at 0/10/25/50/100 bps."""
    dataset = build_macro_regime_dataset(
        panel,
        macro_features,
        public_data=public_data,
        volatility_probability=volatility_probability,
        universe_size=FIXED_SELECTED.universe_size,
    )
    weights, macro_regime, crypto_regime, combined_regime = build_candidate_weights(dataset, FIXED_SELECTED)

    results: dict[int, PortfolioResult] = {}
    rows: list[dict[str, Any]] = []
    for cost_bps in ANALYSIS_COST_LEVELS:
        result = backtest_weights(
            dataset,
            weights,
            macro_regime,
            crypto_regime,
            combined_regime,
            cost_bps=cost_bps,
            turnover_cap=FIXED_SELECTED.turnover_cap,
        )
        results[cost_bps] = result
        rows.extend(_metric_rows_for_result(result, cost_bps))

    metrics = pd.DataFrame(rows)
    consolidated = _consolidated_table(metrics)
    gross_0bps = metrics[metrics["cost_bps"].eq(0)].reset_index(drop=True)
    return {
        "dataset": dataset,
        "metrics": metrics,
        "gross_0bps": gross_0bps,
        "consolidated": consolidated,
        "results": results,
        "metadata": {
            "strategy": SELECTED_STRATEGY_NAME,
            "family": FIXED_SELECTED.family,
            "status": "frozen_selected_main_strategy",
            "strategy_modified": False,
            "selection_modified": False,
            "cost_levels_bps": list(ANALYSIS_COST_LEVELS),
            "development_period": [str(DEVELOPMENT_START.date()), str(DEVELOPMENT_END.date())],
            "holdout_period": [str(HOLDOUT_START.date()), str(HOLDOUT_END.date())],
            "dataset_start": str(dataset.close.index.min().date()),
            "dataset_end": str(dataset.close.index.max().date()),
        },
    }


def _fmt(value: Any, percent: bool = False) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, (float, int, np.floating, np.integer)):
        return f"{float(value):.2%}" if percent else f"{float(value):.3f}"
    return str(value)


def _table(
    frame: pd.DataFrame,
    columns: list[tuple[str, str]],
    percent: set[str] | None = None,
    integer: set[str] | None = None,
) -> str:
    percent = percent or set()
    integer = integer or set()
    if frame is None or frame.empty:
        return "_No rows._"
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in frame.to_dict("records"):
        formatted = []
        for key, _ in columns:
            value = row.get(key)
            if key in integer and value is not None and not pd.isna(value):
                formatted.append(str(int(float(value))))
            else:
                formatted.append(_fmt(value, key in percent))
        lines.append("| " + " | ".join(formatted) + " |")
    return "\n".join(lines)


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.replace({np.nan: None}).to_dict("records")
    if isinstance(value, pd.Series):
        return value.replace({np.nan: None}).to_dict()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items() if key != "results"}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def write_selected_main_strategy_gross_reports(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    metrics = result["metrics"]
    gross = result["gross_0bps"]
    consolidated = result["consolidated"]
    metadata = result["metadata"]

    gross.to_csv(output / "main_strategy_gross_0bps.csv", index=False)
    consolidated.to_csv(output / "main_strategy_consolidated_table.csv", index=False)
    metrics.to_csv(output / "main_strategy_cost_sensitivity_long.csv", index=False)

    gross_columns = [
        ("split", "Split"),
        ("start", "Start"),
        ("end", "End"),
        ("cost_bps", "Cost bps"),
        ("performance_basis", "Basis"),
        ("CAGR", "CAGR"),
        ("Sharpe", "Sharpe"),
        ("Sortino", "Sortino"),
        ("Calmar", "Calmar"),
        ("Maximum Drawdown", "Max DD"),
        ("Annual Turnover", "Annual turnover"),
        ("Exposure", "Exposure"),
        ("Cash Allocation", "Cash"),
        ("Worst Month", "Worst month"),
        ("Transaction Costs", "Transaction costs"),
    ]
    percent_gross = {
        "CAGR",
        "Maximum Drawdown",
        "Exposure",
        "Cash Allocation",
        "Worst Month",
        "Transaction Costs",
    }
    (output / "main_strategy_gross_0bps.md").write_text(f"""# {REPORT_TITLE}: exact 0 bps gross

Strategy: **{metadata['strategy']}**

This is an explicit no-transaction-cost rerun of the frozen selected main strategy. The strategy, thresholds, allocation rule, universe, and validation periods were not modified.

{_table(gross, gross_columns, percent_gross, {"cost_bps"})}
""", encoding="utf-8")

    consolidated_columns = [
        ("strategy", "Strategy"),
        ("cost_bps", "Cost bps"),
        ("performance_basis", "Basis"),
        ("development_CAGR", "Dev CAGR"),
        ("development_Sharpe", "Dev Sharpe"),
        ("development_Sortino", "Dev Sortino"),
        ("development_Calmar", "Dev Calmar"),
        ("development_Maximum Drawdown", "Dev Max DD"),
        ("development_Annual Turnover", "Dev turnover"),
        ("development_Exposure", "Dev exposure"),
        ("development_Worst Month", "Dev worst month"),
        ("development_Transaction Costs", "Dev costs"),
        ("holdout_CAGR", "Holdout CAGR"),
        ("holdout_Sharpe", "Holdout Sharpe"),
        ("holdout_Sortino", "Holdout Sortino"),
        ("holdout_Calmar", "Holdout Calmar"),
        ("holdout_Maximum Drawdown", "Holdout Max DD"),
        ("holdout_Annual Turnover", "Holdout turnover"),
        ("holdout_Exposure", "Holdout exposure"),
        ("holdout_Worst Month", "Holdout worst month"),
        ("holdout_Transaction Costs", "Holdout costs"),
    ]
    percent_consolidated = {
        column
        for column in consolidated.columns
        if any(token in column for token in ("CAGR", "Drawdown", "Exposure", "Worst Month", "Transaction Costs"))
    }
    (output / "main_strategy_consolidated_table.md").write_text(f"""# Final consolidated table: selected main strategy only

Strategy: **{metadata['strategy']}**

Rows with `cost_bps = 0` are exact gross/no-cost results. Rows with positive cost assumptions are net after transaction costs.

{_table(consolidated, consolidated_columns, percent_consolidated, {"cost_bps"})}
""", encoding="utf-8")

    payload = {
        "metadata": metadata,
        "gross_0bps": gross,
        "consolidated": consolidated,
        "metrics": metrics,
    }
    (output / "main_strategy_consolidated_results.json").write_text(
        json.dumps(_json_safe(payload), indent=2),
        encoding="utf-8",
    )


def run_default_selected_main_strategy_gross_report(
    output_dir: str | Path = "reports/final_project",
) -> dict[str, Any]:
    panel, macro, public_data, probability = load_default_inputs()
    result = run_selected_main_strategy_gross_report(panel, macro, public_data, probability)
    write_selected_main_strategy_gross_reports(output_dir, result)
    return result


__all__ = [
    "ANALYSIS_COST_LEVELS",
    "run_selected_main_strategy_gross_report",
    "write_selected_main_strategy_gross_reports",
    "run_default_selected_main_strategy_gross_report",
]
