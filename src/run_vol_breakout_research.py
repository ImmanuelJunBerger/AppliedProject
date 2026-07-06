from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.crypto_mlsystem.data import DataIngestion
from src.crypto_mlsystem.metrics import performance_metrics
from src.crypto_mlsystem.volatility_breakout import (
    MODEL_NAMES,
    block_bootstrap_sharpe_ci,
    build_breakout_context,
    deflated_sharpe_probability,
    execute_breakout,
    filtered_breakout_weights,
    nested_walk_forward_filter,
    probability_backtest_overfitting,
)


TRAIN = ("2019-01-01", "2021-12-31")
VALIDATION = ("2022-01-01", "2024-12-31")
HOLDOUT = ("2025-01-01", "2026-06-22")
SUBPERIODS = {
    "2020-2021 bull market": ("2020-01-01", "2021-12-31"),
    "2022 bear market": ("2022-01-01", "2022-12-31"),
    "2023 recovery": ("2023-01-01", "2023-12-31"),
    "2024-2026 recent period": ("2024-01-01", "2026-06-22"),
}
RISK_MODES = ("binary_filter", "probability_weighted", "drawdown_aware", "volatility_targeted")


def plain(value):
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value.date())
    return value


def period_result(result, period) -> dict:
    start, end = period
    returns = result.returns.loc[start:end]
    turnover = result.turnover.reindex(returns.index)
    costs = result.costs.reindex(returns.index)
    metrics = performance_metrics(returns, turnover, costs) if len(returns) else {}
    return {
        "start": start,
        "end": end,
        "observations": int(len(returns)),
        "metrics": plain(metrics),
        "diagnostics": {
            "hit_rate": float((returns > 0).mean()) if len(returns) else 0.0,
            "turnover": float(turnover.mean()) if len(turnover) else 0.0,
            "transaction_costs": float(costs.sum()) if len(costs) else 0.0,
        },
    }


def confidence_summary(predictions) -> dict:
    if predictions.events.empty:
        return {"count": 0}
    series = predictions.events.probability
    return {
        "count": int(len(series)), "mean": float(series.mean()),
        "p10": float(series.quantile(0.10)), "median": float(series.median()),
        "p90": float(series.quantile(0.90)),
    }


def rejection_summary(predictions, period=None) -> float:
    frame = predictions.events
    if period:
        frame = frame[(frame.date >= period[0]) & (frame.date <= period[1])]
    return float((~frame.accepted).mean()) if len(frame) else np.nan


def md_table(rows, columns, percent=None):
    percent = percent or set()
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in rows:
        cells = []
        for key, _ in columns:
            value = row.get(key, "")
            if isinstance(value, float):
                value = f"{value * 100:.2f}%" if key in percent else f"{value:.3f}"
            cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_reports(output_dir: Path, results: dict):
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_rows = []
    for period_name, values in results["production_candidate"]["periods"].items():
        baseline_rows.append({"period": period_name, **values["metrics"]})
    cost_rows = [{"cost": f"{cost} bps", **values["metrics"]} for cost, values in results["production_candidate"]["cost_sensitivity"].items()]
    subperiod_rows = []
    for period, configurations in results["subperiods"].items():
        for configuration, values in configurations.items():
            subperiod_rows.append({"period": period, "configuration": configuration, **values["metrics"]})
    universe_frequency_rows = []
    risk_control_rows = []
    for row in results["robustness"]:
        if row["cost_bps"] == 25 and row["volatility_scaling"] and row["drawdown_brake"]:
            universe_frequency_rows.append({
                "universe": row["top_n"], "frequency": row["frequency"],
                "validation_sharpe": row["validation"]["metrics"]["Sharpe"],
                "holdout_sharpe": row["holdout"]["metrics"]["Sharpe"],
                "holdout_CAGR": row["holdout"]["metrics"]["CAGR"],
                "note": "insufficient events; cash" if row["validation"]["metrics"]["Sharpe"] == 0 and row["holdout"]["metrics"]["Sharpe"] == 0 else "",
            })
        if row["top_n"] == 10 and row["frequency"] == "W-FRI" and row["cost_bps"] == 25:
            risk_control_rows.append({
                "volatility_scaling": row["volatility_scaling"], "drawdown_brake": row["drawdown_brake"],
                "validation_sharpe": row["validation"]["metrics"]["Sharpe"],
                "holdout_sharpe": row["holdout"]["metrics"]["Sharpe"],
            })
    (output_dir / "vol_breakout_production_candidate.md").write_text(
        f"""# Volatility-breakout production candidate

## Locked protocol

- Dataset: 2019-01-01 to 2026-06-22
- Universe: point-in-time top 10 by lagged dollar turnover
- Rebalance: weekly
- Portfolio: long-only spot, no leverage, 20% maximum asset weight
- Baseline execution: 25 bps costs, 35% volatility target, drawdown brake, cash when no signal exists
- Training: 2019–2021
- Validation/model selection: 2022–2024
- Untouched holdout: 2025-01-01 to 2026-06-22

The first two years are used as warm-up because the nested model requires 250 matured breakout events. Comparable strategy reporting therefore starts on {results['protocol']['evaluation_start']}; the “train” result covers the remaining part of the locked training segment.

## Baseline results

{md_table(baseline_rows, [('period', 'Period'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annualized Volatility', 'Volatility')], {'CAGR', 'Maximum Drawdown', 'Annualized Volatility'})}

## Cost sensitivity

{md_table(cost_rows, [('cost', 'Cost'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD')], {'CAGR', 'Maximum Drawdown'})}

## Subperiods: baseline versus validation-selected ML filter

{md_table(subperiod_rows, [('period', 'Period'), ('configuration', 'Configuration'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD')], {'CAGR', 'Maximum Drawdown'})}

## Universe and frequency robustness

These cells use the validation-selected ML method, 25 bps, volatility scaling, and the drawdown brake. They are exploratory and did not alter the locked champion.

{md_table(universe_frequency_rows, [('universe', 'Top N'), ('frequency', 'Frequency'), ('validation_sharpe', 'Validation Sharpe'), ('holdout_sharpe', 'Holdout Sharpe'), ('holdout_CAGR', 'Holdout CAGR'), ('note', 'Note')], {'holdout_CAGR'})}

## Risk-control ablation

{md_table(risk_control_rows, [('volatility_scaling', 'Vol scaling'), ('drawdown_brake', 'Drawdown brake'), ('validation_sharpe', 'Validation Sharpe'), ('holdout_sharpe', 'Holdout Sharpe')])}

Signals use only prior-close data. A breakout is a new 20-day closing high observed within the preceding seven days. The position is held to the next rebalance and otherwise remains in cash.
""", encoding="utf-8")

    validation_rows = []
    for configuration, values in results["ml_comparison"].items():
        validation_rows.append({
            "configuration": configuration,
            "train_CAGR": values["train"]["metrics"]["CAGR"],
            "train_Sharpe": values["train"]["metrics"]["Sharpe"],
            "CAGR": values["validation"]["metrics"]["CAGR"],
            "Sharpe": values["validation"]["metrics"]["Sharpe"],
            "Maximum Drawdown": values["validation"]["metrics"]["Maximum Drawdown"],
            "rejection": values["validation_rejection_rate"],
        })
    (output_dir / "ml_filter_results.md").write_text(
        f"""# False-breakout ML filter results

Every quarterly refit uses a trailing three-year training window. The last 25% of dates inside that window is an inner validation segment used to choose the raw-after-cost or volatility-adjusted label and a target rejection rate from 10% through 70%. Labels enter training only after their holding period ends.

Funding is not present in the Binance spot OHLCV file and was therefore not used. The runner will include a lagged funding feature when that column is supplied by a separate derivatives source.

## Locked 2022–2024 validation comparison

{md_table(validation_rows, [('configuration', 'Configuration'), ('train_CAGR', 'Train CAGR'), ('train_Sharpe', 'Train Sharpe'), ('CAGR', 'Validation CAGR'), ('Sharpe', 'Validation Sharpe'), ('Maximum Drawdown', 'Validation Max DD'), ('rejection', 'Rejected')], {'train_CAGR', 'CAGR', 'Maximum Drawdown', 'rejection'})}

Selected before holdout: **{results['selection']['champion_configuration']}**.

The minimum probability-weighted exposure multiplier is 20%, and binary filtering accepts at least 30% of available signals at every rebalance. This prevents recurrence of the prior 67.98% unconstrained over-filtering behavior.
""", encoding="utf-8")

    holdout_rows = []
    for name, values in results["holdout_comparison"].items():
        holdout_rows.append({"configuration": name, **values["metrics"]})
    (output_dir / "holdout_results.md").write_text(
        f"""# Untouched holdout results

The champion was selected using 2022–2024 validation only. No model, label, rejection, or risk-mode choice was changed after inspecting 2025–2026. The pre-specified model may refit quarterly using information whose labels had matured before each live decision.

{md_table(holdout_rows, [('configuration', 'Configuration'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annualized Volatility', 'Volatility')], {'CAGR', 'Maximum Drawdown', 'Annualized Volatility'})}

- Champion holdout rejection rate: {results['selection']['champion_holdout_rejection_rate']:.2%}
- Holdout start: 2025-01-01
- Holdout end: 2026-06-22
""", encoding="utf-8")

    stat_rows = []
    for name, periods in results["statistics"]["bootstrap_sharpe_ci"].items():
        for period, ci in periods.items():
            stat_rows.append({"configuration": name, "period": period, **ci})
    (output_dir / "statistical_significance.md").write_text(
        f"""# Statistical significance and selection-risk controls

## Block-bootstrap Sharpe intervals

Intervals use 1,000 deterministic 14-day block-bootstrap samples.

{md_table(stat_rows, [('configuration', 'Configuration'), ('period', 'Period'), ('lower', '2.5%'), ('median', 'Median'), ('upper', '97.5%')])}

- Number of explicitly evaluated configurations: {results['statistics']['tested_configurations']}
- Deflated-Sharpe probability, champion holdout: {results['statistics']['deflated_sharpe_probability']:.2%}
- CSCV-style probability of backtest overfitting on development configurations: {results['statistics']['probability_backtest_overfitting']:.2%}

These controls are approximate. The robustness grid is exploratory and was not used to replace the validation-selected champion. Multiple testing, venue survivorship bias, and the short holdout materially limit confidence.
""", encoding="utf-8")

    conclusion = results["final_conclusion"]
    (output_dir / "final_strategy_recommendation.md").write_text(
        f"""# Final strategy recommendation

- Volatility breakout remains above 0.8 Sharpe: **{conclusion['above_0_8_sharpe']}** ({conclusion['reference_sharpe']:.3f} on the stated reference period).
- ML effect: **{conclusion['ml_effect']}**.
- Untouched holdout survived: **{conclusion['holdout_survived']}**.
- Paper-trading recommendation: **{conclusion['paper_trading_recommendation']}**.

The production decision is based on the untouched holdout and statistical uncertainty, not on the best exploratory robustness cell. {conclusion['narrative']}
""", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Locked volatility-breakout ML-filter research.")
    parser.add_argument("--data", required=True)
    parser.add_argument("--output-dir", default="reports/real_data")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    panel = DataIngestion().load_csv(args.data)

    print("building locked top-10 weekly breakout context", flush=True)
    context = build_breakout_context(panel, 10, "W-FRI", 0.20, 90, 25)
    model_predictions = {}
    for model_name in MODEL_NAMES:
        print(f"nested walk-forward: {model_name}", flush=True)
        model_predictions[model_name] = nested_walk_forward_filter(context, model_name)

    first_dates = [prediction.first_prediction_date for prediction in model_predictions.values() if prediction.first_prediction_date is not None]
    evaluation_start = max(first_dates)
    baseline = execute_breakout(context, context.weights, 25, True, True, start_date=evaluation_start)
    configurations = {"no_ml_filter": baseline}
    configuration_meta = {"no_ml_filter": {"model": None, "mode": "no_ml_filter", "predictions": None}}
    for model_name, predictions in model_predictions.items():
        for mode in RISK_MODES:
            weights = filtered_breakout_weights(context, predictions, mode, 0.20, 0.20)
            volatility_scaling = mode != "drawdown_aware"
            drawdown_brake = mode != "volatility_targeted"
            result = execute_breakout(context, weights, 25, volatility_scaling, drawdown_brake, start_date=evaluation_start)
            key = f"{model_name}__{mode}"
            configurations[key] = result
            configuration_meta[key] = {"model": model_name, "mode": mode, "predictions": predictions}

    comparison = {}
    for name, result in configurations.items():
        metadata = configuration_meta[name]
        predictions = metadata["predictions"]
        comparison[name] = {
            "train": period_result(result, TRAIN),
            "validation": period_result(result, VALIDATION),
            "validation_rejection_rate": rejection_summary(predictions, VALIDATION) if predictions else 0.0,
            "confidence_distribution": confidence_summary(predictions) if predictions else {"count": 0},
        }

    eligible_champions = [name for name in configurations if name != "no_ml_filter"]
    champion = max(
        eligible_champions,
        key=lambda name: (
            comparison[name]["validation"]["metrics"]["Sharpe"],
            comparison[name]["validation"]["metrics"]["CAGR"],
        ),
    )
    champion_result = configurations[champion]
    champion_meta = configuration_meta[champion]
    print(f"validation-locked champion: {champion}", flush=True)

    production_periods = {
        "train_2019_2021": period_result(baseline, TRAIN),
        "validation_2022_2024": period_result(baseline, VALIDATION),
        "untouched_holdout_2025_2026": period_result(baseline, HOLDOUT),
        "full_walk_forward": period_result(baseline, (str(evaluation_start.date()), HOLDOUT[1])),
    }
    cost_sensitivity = {
        str(cost): period_result(execute_breakout(context, context.weights, cost, True, True, start_date=evaluation_start), (str(evaluation_start.date()), HOLDOUT[1]))
        for cost in [10, 25, 50, 100]
    }

    holdout_comparison = {
        "no_ml_filter": period_result(baseline, HOLDOUT),
        champion: period_result(champion_result, HOLDOUT),
    }
    subperiods = {}
    for period_name, period in SUBPERIODS.items():
        subperiods[period_name] = {
            "no_ml_filter": period_result(baseline, period),
            champion: period_result(champion_result, period),
        }

    print("running predefined robustness grid", flush=True)
    robustness = []
    robustness_returns = {}
    context_cache = {(10, "W-FRI"): (context, champion_meta["predictions"])}
    for top_n in [5, 10, 20]:
        for frequency in ["W-FRI", "2W-FRI"]:
            key = (top_n, frequency)
            if key not in context_cache:
                robust_context = build_breakout_context(panel, top_n, frequency, 0.20, 90, 25)
                robust_predictions = nested_walk_forward_filter(robust_context, champion_meta["model"])
                context_cache[key] = (robust_context, robust_predictions)
            robust_context, robust_predictions = context_cache[key]
            robust_weights = filtered_breakout_weights(robust_context, robust_predictions, champion_meta["mode"], 0.20, 0.20)
            robust_start = robust_predictions.first_prediction_date
            for cost in [10, 25, 50, 100]:
                for vol_scaling in [False, True]:
                    for brake in [False, True]:
                        result = execute_breakout(robust_context, robust_weights, cost, vol_scaling, brake, start_date=robust_start)
                        name = f"top{top_n}__{frequency}__cost{cost}__vol{int(vol_scaling)}__brake{int(brake)}"
                        validation = period_result(result, VALIDATION)
                        holdout = period_result(result, HOLDOUT)
                        robustness.append({
                            "configuration": name, "top_n": top_n, "frequency": frequency,
                            "cost_bps": cost, "volatility_scaling": vol_scaling,
                            "drawdown_brake": brake, "validation": validation, "holdout": holdout,
                        })
                        robustness_returns[name] = result.returns.loc[:VALIDATION[1]]

    tested_configurations = len(configurations) + len(robustness)
    bootstrap = {
        "no_ml_filter": {
            "validation": block_bootstrap_sharpe_ci(baseline.returns.loc[VALIDATION[0]:VALIDATION[1]]),
            "holdout": block_bootstrap_sharpe_ci(baseline.returns.loc[HOLDOUT[0]:HOLDOUT[1]]),
        },
        champion: {
            "validation": block_bootstrap_sharpe_ci(champion_result.returns.loc[VALIDATION[0]:VALIDATION[1]]),
            "holdout": block_bootstrap_sharpe_ci(champion_result.returns.loc[HOLDOUT[0]:HOLDOUT[1]]),
        },
    }
    development_matrix = pd.DataFrame({name: result.returns.loc[:VALIDATION[1]] for name, result in configurations.items()})
    pbo = probability_backtest_overfitting(development_matrix)
    holdout_returns = champion_result.returns.loc[HOLDOUT[0]:HOLDOUT[1]]
    dsr = deflated_sharpe_probability(holdout_returns, tested_configurations)

    baseline_full_sharpe = production_periods["full_walk_forward"]["metrics"]["Sharpe"]
    baseline_holdout_sharpe = holdout_comparison["no_ml_filter"]["metrics"]["Sharpe"]
    champion_holdout_sharpe = holdout_comparison[champion]["metrics"]["Sharpe"]
    ml_improves_validation = comparison[champion]["validation"]["metrics"]["Sharpe"] > comparison["no_ml_filter"]["validation"]["metrics"]["Sharpe"]
    ml_improves_holdout = champion_holdout_sharpe > baseline_holdout_sharpe
    holdout_survived = champion_holdout_sharpe > 0 and holdout_comparison[champion]["metrics"]["CAGR"] > 0
    ci_lower = bootstrap[champion]["holdout"]["lower"]
    paper_trade = holdout_survived and ci_lower > 0 and dsr >= 0.50

    results = {
        "protocol": {
            "training": TRAIN, "validation": VALIDATION, "untouched_holdout": HOLDOUT,
            "selection_rule": "highest validation Sharpe, tie-break validation CAGR; holdout excluded",
            "online_refit": "quarterly, labels must mature before decision",
            "evaluation_start": str(evaluation_start.date()),
        },
        "production_candidate": {"periods": production_periods, "cost_sensitivity": cost_sensitivity},
        "ml_comparison": comparison,
        "selection": {
            "champion_configuration": champion,
            "champion_model": champion_meta["model"],
            "champion_risk_mode": champion_meta["mode"],
            "champion_validation_rejection_rate": rejection_summary(champion_meta["predictions"], VALIDATION),
            "champion_holdout_rejection_rate": rejection_summary(champion_meta["predictions"], HOLDOUT),
            "feature_importance": plain(champion_meta["predictions"].feature_importance.head(20).to_dict()),
        },
        "holdout_comparison": holdout_comparison,
        "subperiods": subperiods,
        "robustness": robustness,
        "statistics": {
            "tested_configurations": tested_configurations,
            "bootstrap_sharpe_ci": bootstrap,
            "deflated_sharpe_probability": dsr,
            "probability_backtest_overfitting": pbo,
        },
        "final_conclusion": {
            "above_0_8_sharpe": bool(baseline_full_sharpe > 0.8),
            "reference_sharpe": baseline_full_sharpe,
            "ml_effect": "improves validation and holdout" if ml_improves_validation and ml_improves_holdout else "does not improve both validation and holdout",
            "holdout_survived": bool(holdout_survived),
            "paper_trading_recommendation": "suitable for a tightly monitored paper-trading trial" if paper_trade else "not yet suitable for paper trading",
            "narrative": "A positive point estimate is insufficient when the holdout confidence interval or deflated-Sharpe evidence is weak." if not paper_trade else "Paper trading should use frozen rules and no capital while execution assumptions are validated.",
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "vol_breakout_results.json").write_text(json.dumps(plain(results), indent=2), encoding="utf-8")
    champion_meta["predictions"].events.to_csv(output_dir / "vol_breakout_champion_predictions.csv", index=False)
    champion_meta["predictions"].selection_history.to_csv(output_dir / "vol_breakout_nested_selection.csv", index=False)
    pd.DataFrame(robustness).to_json(output_dir / "vol_breakout_robustness.json", orient="records", indent=2)
    write_reports(output_dir, results)
    print(json.dumps(plain({
        "selection": results["selection"],
        "production_candidate": results["production_candidate"],
        "holdout_comparison": results["holdout_comparison"],
        "statistics": results["statistics"],
        "final_conclusion": results["final_conclusion"],
    }), indent=2), flush=True)


if __name__ == "__main__":
    main()
