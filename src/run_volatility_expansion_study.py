"""Run the prediction-only volatility-expansion research study."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.crypto_mlsystem.data import DataIngestion
from src.crypto_mlsystem.volatility_expansion import run_volatility_expansion_study


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
        return f"{value:.2%}" if percent else f"{value:.4f}"
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


def _merge_alternative_data(panel: pd.DataFrame, path: str | None) -> pd.DataFrame:
    if not path:
        return panel
    alternative = pd.read_csv(path, parse_dates=["date"])
    keys = ["date", "symbol"] if "symbol" in alternative.columns else ["date"]
    if alternative.duplicated(keys).any():
        raise ValueError(f"Alternative-data input must be unique on {keys}")
    overlap = (set(panel.columns) & set(alternative.columns)) - set(keys)
    if overlap:
        raise ValueError(f"Alternative-data columns already exist in price input: {sorted(overlap)}")
    return panel.merge(alternative, on=keys, how="left", validate="many_to_one" if keys == ["date"] else "one_to_one")


def _calibration_svg(calibration: pd.DataFrame, output: Path) -> None:
    holdout = calibration[calibration.split == "holdout"]
    width, height, margin = 780, 560, 70
    plot_width, plot_height = width - 2 * margin, height - 2 * margin
    colors = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#d97706", "#0891b2"]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{margin}" y="32" font-family="sans-serif" font-size="20">Locked holdout calibration</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#111"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="#111"/>',
    ]
    for tick in np.linspace(0, 1, 6):
        x = margin + tick * plot_width
        y = height - margin - tick * plot_height
        lines.extend([
            f'<line x1="{x:.1f}" y1="{height-margin}" x2="{x:.1f}" y2="{height-margin+5}" stroke="#111"/>',
            f'<text x="{x:.1f}" y="{height-margin+22}" text-anchor="middle" font-family="sans-serif" font-size="12">{tick:.1f}</text>',
            f'<line x1="{margin-5}" y1="{y:.1f}" x2="{margin}" y2="{y:.1f}" stroke="#111"/>',
            f'<text x="{margin-10}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="12">{tick:.1f}</text>',
        ])
    lines.append(
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{margin}" stroke="#777" stroke-dasharray="6 5"/>'
    )
    legend_y = 52
    for color, ((model, feature_set), group) in zip(colors, holdout.groupby(["model", "feature_set"], sort=True)):
        points = []
        for row in group.sort_values("mean_predicted_probability").itertuples():
            x = margin + row.mean_predicted_probability * plot_width
            y = height - margin - row.observed_frequency * plot_height
            points.append(f"{x:.1f},{y:.1f}")
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
        if points:
            lines.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
            label = html.escape(f"{model} / {feature_set}")
            lines.append(f'<text x="{margin+180}" y="{legend_y}" font-family="sans-serif" font-size="11" fill="{color}">{label}</text>')
            legend_y += 15
    lines.extend([
        f'<text x="{width/2}" y="{height-12}" text-anchor="middle" font-family="sans-serif" font-size="14">Mean predicted probability</text>',
        f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" text-anchor="middle" font-family="sans-serif" font-size="14">Observed expansion frequency</text>',
        "</svg>",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")


def _write_reports(result, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = result.metrics.copy()
    holdout = metrics[metrics.split == "holdout"].sort_values(["model", "feature_set"])
    development = metrics[metrics.split == "development"].sort_values(["model", "feature_set"])
    comparisons = result.comparisons.copy()
    holdout_comparisons = comparisons[comparisons.split == "holdout"] if not comparisons.empty else comparisons

    tested_alternatives = comparisons[
        comparisons.alternative_feature_set != "price_liquidity"
    ] if not comparisons.empty else comparisons
    development_winners = set(
        zip(
            tested_alternatives.loc[
                (tested_alternatives.split == "development") & tested_alternatives.improves_both,
                "model",
            ],
            tested_alternatives.loc[
                (tested_alternatives.split == "development") & tested_alternatives.improves_both,
                "alternative_feature_set",
            ],
        )
    )
    holdout_winners = set(
        zip(
            tested_alternatives.loc[
                (tested_alternatives.split == "holdout") & tested_alternatives.improves_both,
                "model",
            ],
            tested_alternatives.loc[
                (tested_alternatives.split == "holdout") & tested_alternatives.improves_both,
                "alternative_feature_set",
            ],
        )
    )
    stable_winners = development_winners & holdout_winners
    if tested_alternatives.empty:
        alternative_conclusion = (
            "Derivatives/options improvement is **not yet testable**: the supplied dataset contains no usable "
            "derivatives or options columns. No proxy or synthetic substitute was used."
        )
    elif stable_winners:
        winners = [f"{model}/{features}" for model, features in sorted(stable_winners)]
        alternative_conclusion = (
            "Alternative data improved both AUC and Brier score in development and holdout for: "
            f"**{', '.join(winners)}**."
        )
    else:
        holdout_only = [f"{model}/{features}" for model, features in sorted(holdout_winners)]
        exception = (
            f" A holdout-only improvement occurred for {', '.join(holdout_only)}, but it failed the development consistency test."
            if holdout_only else ""
        )
        alternative_conclusion = (
            "No derivatives/options feature set improved both AUC and Brier score consistently in development and holdout."
            + exception
        )

    holdout_rate = float(holdout.positive_rate.iloc[0])
    no_skill_brier = holdout_rate * (1 - holdout_rate)
    best_price = holdout[holdout.feature_set == "price_only"].sort_values(
        ["brier_score", "auc"], ascending=[True, False]
    ).iloc[0]
    signal_conclusion = (
        f"The price-history volatility signal survives the untouched holdout: {best_price['model']} "
        f"achieves AUC {best_price['auc']:.3f} and Brier {best_price['brier_score']:.3f}, versus "
        f"AUC 0.500 and Brier {no_skill_brier:.3f} for a constant-rate forecast."
    )

    metadata = result.dataset.metadata
    availability_table = _table(
        result.availability,
        [("feature_set", "Feature set"), ("available", "Available"), ("feature_count", "Features"), ("reason", "Reason")],
    )
    metric_columns = [
        ("model", "Model"), ("feature_set", "Feature set"), ("observations", "N"),
        ("positive_rate", "Expansion rate"), ("auc", "AUC"), ("precision", "Precision"),
        ("recall", "Recall"), ("brier_score", "Brier"),
    ]
    comparison_columns = [
        ("split", "Split"), ("model", "Model"), ("alternative_feature_set", "Alternative set"),
        ("matched_observations", "N"), ("delta_auc", "Delta AUC"),
        ("delta_brier", "Delta Brier"), ("improves_both", "Improves both"),
    ]
    comparison_table = _table(comparisons, comparison_columns) if not comparisons.empty else "No matched comparisons available."

    (output_dir / "results_summary.md").write_text(
        f"""# Volatility-expansion signal study

## Scope

This is a prediction study only. It contains no return target, portfolio construction, position sizing, execution rule, or trading backtest.

- Target: {metadata['target']}
- Universe: weekly point-in-time top {metadata['top_n']} by trailing 90-day median dollar volume
- Observations: {metadata['observations']} from {metadata['start']} to {metadata['end']}
- Positive-class rate: {metadata['positive_rate']:.2%}
- Unique historical universe members: {metadata['unique_assets']}
- Development evaluation: expanding walk-forward six-month blocks
- Inner tuning: CPCV entirely inside each training window
- Locked holdout: {result.protocol['holdout_start']} to {result.protocol['holdout_end']}
- Holdout rule: {result.protocol['holdout_training_rule']}

## Feature availability

{availability_table}

## Walk-forward development performance

{_table(development, metric_columns, {'positive_rate'})}

## Locked holdout performance

{_table(holdout, metric_columns, {'positive_rate'})}

## Incremental feature-set comparison

Positive Delta AUC is better; negative Delta Brier is better. "Improves both" requires both conditions on matched dates.

{comparison_table}

## Conclusion

{signal_conclusion}

{alternative_conclusion}

This study establishes only predictive discrimination and calibration. Even a positive result is insufficient authorization to construct a trading strategy.

## Limitations

- Realized variance is estimated from daily closes because the available broad panel is daily, not intraday.
- Seven-day labels overlap, so the observation count is not an independent-sample count.
- Universe ranks are point-in-time within the downloaded Binance market catalog, but removed/delisted pairs absent from that catalog cannot be recovered.
- The derivatives block currently contains realized funding only; long-history open interest, basis, liquidations, and options were unavailable.
- Funding coverage follows currently mapped linear perpetual contracts and is lagged one day.
""",
        encoding="utf-8",
    )

    holdout_importance = result.feature_importance[result.feature_importance.split == "holdout"].copy()
    holdout_importance["normalized_importance"] = holdout_importance.groupby(
        ["model", "feature_set"]
    )["importance"].transform(lambda values: values / values.sum() if values.sum() else values)
    top_importance = holdout_importance.sort_values(
        ["model", "feature_set", "normalized_importance"], ascending=[True, True, False]
    ).groupby(["model", "feature_set"]).head(15)
    (output_dir / "holdout_performance.md").write_text(
        f"""# Locked holdout diagnostics

## Predictive metrics

{_table(holdout, metric_columns, {'positive_rate'})}

## Calibration curve

The machine-readable curve is in `calibration_curve.csv`; `calibration_curve.svg` plots observed frequency against predicted probability. Perfect calibration lies on the diagonal.

{_table(result.calibration[result.calibration.split == 'holdout'], [('model', 'Model'), ('feature_set', 'Feature set'), ('bin', 'Bin'), ('mean_predicted_probability', 'Predicted'), ('observed_frequency', 'Observed')])}

## Top holdout-fit feature importance

Importance is absolute standardized coefficient magnitude for HAR/Elastic Net and native split importance for the boosted-tree backend. It is descriptive, not causal.

{_table(top_importance, [('model', 'Model'), ('feature_set', 'Feature set'), ('feature', 'Feature'), ('normalized_importance', 'Normalized importance')])}

## Leakage boundary audit

- Maximum allowed training label end: before {result.protocol['holdout_start']}
- Actual maximum label end used in each fit is recorded in `selection_history.csv`.
- Alternative data are lagged {metadata['alternative_data_lag_days']} day(s).
- Hyperparameters are selected by training-window CPCV Brier score.
- No holdout outcome is used for tuning or refitting.
""",
        encoding="utf-8",
    )

    payload = {
        "protocol": result.protocol,
        "dataset": metadata,
        "availability": result.availability.to_dict("records"),
        "metrics": metrics.to_dict("records"),
        "comparisons": comparisons.to_dict("records"),
        "conclusion": alternative_conclusion,
    }
    (output_dir / "results.json").write_text(json.dumps(_plain(payload), indent=2), encoding="utf-8")
    result.predictions.to_csv(output_dir / "predictions.csv", index=False)
    result.metrics.to_csv(output_dir / "predictive_metrics.csv", index=False)
    result.calibration.to_csv(output_dir / "calibration_curve.csv", index=False)
    holdout_importance.to_csv(output_dir / "feature_importance.csv", index=False)
    selection = result.selection_history.copy()
    selection["parameters"] = selection.parameters.map(json.dumps)
    selection.to_csv(output_dir / "selection_history.csv", index=False)
    result.comparisons.to_csv(output_dir / "feature_set_comparison.csv", index=False)
    result.availability.to_csv(output_dir / "feature_availability.csv", index=False)
    memberships = [
        {"effective_date": date_, "rank": rank, "symbol": symbol}
        for date_, members in result.dataset.universes.items()
        for rank, symbol in enumerate(members, start=1)
    ]
    pd.DataFrame(memberships).to_csv(output_dir / "universe_membership.csv", index=False)
    _calibration_svg(result.calibration, output_dir / "calibration_curve.svg")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predict seven-day volatility expansion; no trading strategy is built."
    )
    parser.add_argument("--data", required=True, help="Daily OHLCV panel CSV")
    parser.add_argument(
        "--alternative-data",
        help="Optional point-in-time CSV keyed by date and optionally symbol with derivatives/options columns",
    )
    parser.add_argument("--output-dir", default="reports/volatility_expansion")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--holdout-start", default="2025-01-01")
    parser.add_argument("--holdout-end", default="2026-06-22")
    parser.add_argument("--alternative-data-lag-days", type=int, default=1)
    args = parser.parse_args()

    panel = DataIngestion().load_csv(args.data)
    panel = _merge_alternative_data(panel, args.alternative_data)
    print("building point-in-time universe and volatility-expansion labels", flush=True)
    result = run_volatility_expansion_study(
        panel,
        top_n=args.top_n,
        holdout_start=args.holdout_start,
        holdout_end=args.holdout_end,
        alternative_data_lag_days=args.alternative_data_lag_days,
    )
    output_dir = Path(args.output_dir)
    _write_reports(result, output_dir)
    print(result.metrics.to_string(index=False), flush=True)
    print(f"wrote prediction-only study to {output_dir}", flush=True)


if __name__ == "__main__":
    main()
