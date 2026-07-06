"""Run portfolio overlays driven by the frozen volatility-expansion forecast."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.crypto_mlsystem.data import DataIngestion
from src.crypto_mlsystem.forecast_portfolio import run_forecast_portfolio_study


def _plain(value: Any):
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value)
    return value


def _format(value: Any, percent: bool = False) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "N/A"
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if value else "No"
    if isinstance(value, (float, np.floating)):
        return f"{value:.2%}" if percent else f"{value:.3f}"
    return str(value)


def _table(frame: pd.DataFrame, columns: list[tuple[str, str]], percent: set[str] | None = None) -> str:
    percent = percent or set()
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in frame.to_dict("records"):
        lines.append("| " + " | ".join(_format(row.get(key), key in percent) for key, _ in columns) + " |")
    return "\n".join(lines)


def _load_universes(path: str | Path) -> dict[pd.Timestamp, list[str]]:
    membership = pd.read_csv(path, parse_dates=["effective_date"]).sort_values(
        ["effective_date", "rank"]
    )
    return {
        pd.Timestamp(date_): group.symbol.astype(str).tolist()
        for date_, group in membership.groupby("effective_date", sort=True)
    }


def _rule_table(result) -> pd.DataFrame:
    return pd.DataFrame([
        {"portfolio": portfolio, **asdict(rule)}
        for portfolio, rule in result.selected_rules.items()
        if not portfolio.startswith("standalone")
    ])


def _economic_conclusion(result) -> tuple[bool, str, pd.DataFrame]:
    holdout = result.comparisons[
        (result.comparisons.split == "holdout") & (result.comparisons.cost_bps == 25)
    ].merge(result.bootstrap, on=["portfolio", "reference"], how="left")
    holdout["passes_point_estimates"] = (
        (holdout.delta_sharpe > 0)
        & (holdout.delta_cagr > 0)
        & (holdout.delta_max_drawdown >= 0)
        & (holdout.delta_calmar > 0)
    )
    holdout["statistically_supported"] = holdout.lower > 0
    holdout["economic_value"] = holdout.passes_point_estimates & holdout.statistically_supported
    winners = holdout.loc[holdout.economic_value, "portfolio"].tolist()
    if winners:
        conclusion = (
            "The frozen volatility forecast improves after-cost portfolio outcomes for **"
            + ", ".join(winners)
            + "** at the 25 bps baseline, including a positive paired block-bootstrap Sharpe difference."
        )
        return True, conclusion, holdout
    positive = holdout.loc[holdout.delta_sharpe > 0, "portfolio"].tolist()
    detail = (
        " Some overlays have higher point-estimate Sharpe (" + ", ".join(positive) + "), but fail the full drawdown/growth/bootstrap criterion."
        if positive else " No overlay has a higher holdout Sharpe at 25 bps."
    )
    conclusion = (
        "The volatility forecast predicts volatility well but does **not** demonstrate robust economic value "
        "under the predeclared after-cost criterion." + detail
    )
    return False, conclusion, holdout


def write_reports(result, output_dir: Path, forecast_hash: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    has_value, conclusion, decision = _economic_conclusion(result)
    rules = _rule_table(result)
    metric_columns = [
        ("portfolio", "Portfolio"), ("cost_bps", "Cost bps"),
        ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Sortino", "Sortino"),
        ("Maximum Drawdown", "Max drawdown"), ("Calmar", "Calmar"),
        ("Turnover", "Turnover"), ("Exposure", "Exposure"),
    ]
    percent = {"CAGR", "Maximum Drawdown", "Turnover", "Exposure"}
    development_25 = result.metrics[
        (result.metrics.split == "development") & (result.metrics.cost_bps == 25)
    ].sort_values(["category", "portfolio"])
    holdout_25 = result.metrics[
        (result.metrics.split == "holdout") & (result.metrics.cost_bps == 25)
    ].sort_values(["category", "portfolio"])
    overlay_holdout = result.metrics[
        (result.metrics.split == "holdout") & (result.metrics.category == "forecast_overlay")
    ].sort_values(["portfolio", "cost_bps"])

    (output_dir / "economic_value_summary.md").write_text(
        f"""# Economic value of the fixed volatility-expansion forecast

## Locked design

- Forecast: Elastic Net, price-only, seven-day volatility-expansion probability.
- Forecast artifact SHA-256: `{forecast_hash}`.
- Prediction model refit or recalibration in this study: **No**.
- Portfolio-rule selection: {result.protocol['portfolio_selection']}.
- Selection cost: 25 bps; cost sensitivity reuses the same frozen rules.
- Locked holdout: {result.protocol['holdout_start']} to {result.protocol['holdout_end']}.
- Holdout threshold searches: {result.protocol['holdout_threshold_searches']}.
- Rebalance: weekly Friday; forecast at Friday close affects subsequent returns.

## Selected development-only rules

{_table(rules, [('portfolio', 'Portfolio'), ('method', 'Method'), ('floor', 'Floor'), ('threshold', 'Threshold'), ('target_probability', 'Target probability'), ('low_threshold', 'Low'), ('high_threshold', 'High'), ('low_regime', 'Low regime')])}

## Development results at 25 bps

{_table(development_25, metric_columns, percent)}

## Locked holdout results at 25 bps

{_table(holdout_25, metric_columns, percent)}

## Answer

{conclusion}

Economic value requires higher Sharpe, CAGR and Calmar, no worse maximum drawdown, and a positive 95% paired block-bootstrap lower bound for Sharpe improvement versus the relevant standalone strategy.
""",
        encoding="utf-8",
    )

    (output_dir / "holdout_results.md").write_text(
        f"""# Locked holdout results

Rules and thresholds were frozen using development CPCV at 25 bps. The table below applies those unchanged rules at every requested cost level.

## Forecast overlays

{_table(overlay_holdout, metric_columns, percent)}

## All benchmarks and standalone strategies at 25 bps

{_table(holdout_25, metric_columns, percent)}

## Holdout boundary

The trading study reads saved probabilities only. It does not access volatility labels, fit prediction models, recalibrate probabilities, or select any threshold from holdout returns.
""",
        encoding="utf-8",
    )

    comparison_columns = [
        ("cost_bps", "Cost bps"), ("portfolio", "Overlay"), ("reference", "Reference"),
        ("delta_sharpe", "Delta Sharpe"), ("delta_sortino", "Delta Sortino"),
        ("delta_cagr", "Delta CAGR"), ("delta_max_drawdown", "Delta max DD"),
        ("delta_calmar", "Delta Calmar"), ("delta_turnover", "Delta turnover"),
    ]
    holdout_comparison = result.comparisons[result.comparisons.split == "holdout"].sort_values(
        ["portfolio", "cost_bps"]
    )
    (output_dir / "overlay_comparison.md").write_text(
        f"""# Overlay comparison

Positive delta maximum drawdown means a less severe drawdown. Each overlay is compared with its standalone base; regime switching uses standalone volatility breakout as its declared reference.

## Holdout deltas across costs

{_table(holdout_comparison, comparison_columns, {'delta_cagr', 'delta_max_drawdown', 'delta_turnover'})}

## Paired holdout Sharpe uncertainty at 25 bps

{_table(result.bootstrap, [('portfolio', 'Overlay'), ('reference', 'Reference'), ('lower', '2.5%'), ('median', 'Median'), ('upper', '97.5%')])}

## Development-only CPCV selection audit

`overlay_selection.csv` contains every predeclared candidate, its CPCV score, and the selected flag. There are no holdout-return columns in that file.
""",
        encoding="utf-8",
    )

    if has_value:
        recommendation = (
            "The qualifying overlay may proceed to a paper-trading execution study with its rule frozen. "
            "No live capital is justified until slippage and operational behavior are observed."
        )
    else:
        recommendation = (
            "Do not promote a volatility-forecast trading overlay. Retain the volatility model for forecasting and risk monitoring, "
            "but keep the standalone strategies unchanged."
        )
    (output_dir / "final_recommendation.md").write_text(
        f"""# Final recommendation

## Conclusion

{conclusion}

## Recommendation

{recommendation}

This conclusion is about economic value after costs, not predictive accuracy. A model can forecast volatility expansion accurately and still fail to improve a long-only strategy because direction, timing, exposure loss, and turnover determine portfolio outcomes.
""",
        encoding="utf-8",
    )

    payload = {
        "protocol": result.protocol,
        "forecast_sha256": forecast_hash,
        "selected_rules": {key: asdict(value) for key, value in result.selected_rules.items()},
        "metrics": result.metrics.to_dict("records"),
        "comparisons": result.comparisons.to_dict("records"),
        "bootstrap": result.bootstrap.to_dict("records"),
        "economic_value": has_value,
        "conclusion": conclusion,
    }
    (output_dir / "results.json").write_text(json.dumps(_plain(payload), indent=2), encoding="utf-8")
    result.metrics.to_csv(output_dir / "portfolio_metrics.csv", index=False)
    result.comparisons.to_csv(output_dir / "overlay_deltas.csv", index=False)
    result.selection_history.to_csv(output_dir / "overlay_selection.csv", index=False)
    result.returns.to_csv(output_dir / "portfolio_returns.csv", index_label="date")
    result.bootstrap.to_csv(output_dir / "holdout_sharpe_bootstrap.csv", index=False)
    decision.to_csv(output_dir / "economic_value_decision.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test economic value of a fixed volatility forecast")
    parser.add_argument("--data", required=True)
    parser.add_argument("--forecast-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--universe-membership", default="reports/volatility_expansion/universe_membership.csv")
    parser.add_argument("--output-dir", default="reports/volatility_expansion_trading")
    args = parser.parse_args()

    panel = DataIngestion().load_csv(args.data)
    forecast_path = Path(args.forecast_predictions)
    predictions = pd.read_csv(forecast_path, parse_dates=["date", "label_end", "train_end"])
    universes = _load_universes(args.universe_membership)
    forecast_hash = hashlib.sha256(forecast_path.read_bytes()).hexdigest()
    result = run_forecast_portfolio_study(panel, predictions, universes)
    output_dir = Path(args.output_dir)
    write_reports(result, output_dir, forecast_hash)
    print(result.metrics[result.metrics.split == "holdout"].to_string(index=False), flush=True)
    print(f"wrote economic-value study to {output_dir}", flush=True)


if __name__ == "__main__":
    main()
