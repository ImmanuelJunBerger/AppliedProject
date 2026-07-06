"""Execute the independent derivatives and market-structure research module."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.crypto_mlsystem.data import DataIngestion
from src.crypto_mlsystem.derivatives_data import download_public_derivatives, merge_existing_funding
from src.crypto_mlsystem.derivatives_features import build_derivatives_features
from src.crypto_mlsystem.derivatives_research import (
    COST_LEVELS,
    HOLDOUT_END,
    HOLDOUT_START,
    acceptance,
    backtest_spot_weights,
    period_metrics,
    predictive_candidates,
    predictive_metrics,
    strategy_weights,
    walk_forward_predictions,
)
from src.crypto_mlsystem.volatility_breakout import (
    deflated_sharpe_probability,
    probability_backtest_overfitting,
)


DEVELOPMENT_START = "2021-01-01"
DEVELOPMENT_END = "2024-12-31"


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
    if value is None or (isinstance(value, (float, np.floating)) and not np.isfinite(value)):
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


def _benchmark_weights(dates: pd.DatetimeIndex, name: str) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=dates, columns=["BTC", "ETH"])
    if name == "btc_buy_hold":
        weights.BTC = 1.0
    elif name == "eth_buy_hold":
        weights.ETH = 1.0
    elif name == "btc_eth_50_50":
        weights.loc[:, ["BTC", "ETH"]] = 0.50
    else:
        raise ValueError(name)
    return weights


def _write_reports(
    output: Path,
    coverage: pd.DataFrame,
    dataset,
    predictions: pd.DataFrame,
    model_metrics: pd.DataFrame,
    comparisons: pd.DataFrame,
    selection: pd.DataFrame,
    strategy_metrics: pd.DataFrame,
    availability: pd.DataFrame,
    acceptances: pd.DataFrame,
    statistics: dict[str, Any],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    usable = coverage[coverage.usable_for_locked_study]
    unavailable = coverage[~coverage.usable_for_locked_study]
    (output / "data_coverage.md").write_text(f"""# Derivatives data coverage

## Available data

{_table(coverage, [('dataset', 'Dataset'), ('symbol', 'Symbol'), ('start', 'Start'), ('end', 'End'), ('observations', 'N'), ('usable_for_locked_study', 'Usable'), ('limitation', 'Limitation')])}

Long-history realized funding and Binance premium-index klines are the only derivatives fields with enough development and evaluation coverage. The premium index is a basis proxy, not a directly executable cash-and-carry return.

## Unavailable for the locked study

- Open interest, global long/short ratio and taker buy/sell history were downloaded from public endpoints but retained only for recent dates. They are saved and audited, but excluded from model and strategy selection.
- Public/free liquidation history with consistent 2019–2026 coverage was unavailable. No synthetic liquidation series was substituted.
- No historical order-book imbalance or multi-venue derivatives aggregation was available.

The current 2025–2026 period has been examined in prior projects. It is reused here because requested, but cannot be described as untouched for a hypothesis designed in June 2026.
""", encoding="utf-8")

    inventory_rows = []
    for feature_set, columns in dataset.feature_sets.items():
        for column in columns:
            inventory_rows.append({"feature_set": feature_set, "feature": column, "lag_days": 1})
    inventory = pd.DataFrame(inventory_rows).drop_duplicates()
    (output / "feature_inventory.md").write_text(f"""# Derivatives feature inventory

All decision features are shifted one complete UTC day. Rolling z-scores and percentiles use trailing observations only.

{_table(inventory, [('feature_set', 'Feature set'), ('feature', 'Feature'), ('lag_days', 'Lag days')])}

## Implemented but excluded for low historical coverage

{chr(10).join(f'- `{name}`' for name in dataset.metadata['excluded_low_coverage_derivatives'])}

Funding features include the daily rate, 3/7/14-day means, one-day change, absolute rate, trailing z-score/percentile and positive/negative streaks. Basis features include level, z-score, change, compression and expansion. OI quadrants, crowding interactions, long/short ratio and taker imbalance activate automatically only when development coverage exceeds 20%.
""", encoding="utf-8")

    (output / "predictive_results.md").write_text(f"""# Predictive results

Models use annual expanding walk-forward evaluation. Hyperparameters are chosen by purged, embargoed CPCV inside each historical training window. The classification threshold is fixed at 0.50.

The requested risk-adjusted-return sign target is the sign of forward return after
division by a strictly positive trailing-volatility scale. It is therefore not an
independent directional target; the implementation and report retain the requested
name but make this equivalence explicit. The three drawdown thresholds are tracked
as separate target configurations.

## Metrics

{_table(model_metrics.sort_values(['target', 'split', 'brier']), [('target', 'Target'), ('model', 'Model'), ('feature_set', 'Features'), ('split', 'Split'), ('observations', 'N'), ('positive_rate', 'Positive rate'), ('auc', 'AUC'), ('brier', 'Brier'), ('precision', 'Precision'), ('recall', 'Recall')], {'positive_rate'})}

## Matched incremental comparisons

Positive AUC delta and negative Brier delta favor price plus derivatives.

{_table(comparisons, [('target', 'Target'), ('model', 'Model'), ('split', 'Split'), ('delta_auc', 'Delta AUC'), ('delta_brier', 'Delta Brier'), ('improves_both', 'Improves both')])}

No OI-dependent crowding-unwind model is reported because the target has no adequate development-era OI coverage.
""", encoding="utf-8")

    development = strategy_metrics[(strategy_metrics.split == "development") & (strategy_metrics.cost_bps == 25)]
    holdout = strategy_metrics[(strategy_metrics.split == "holdout") & (strategy_metrics.cost_bps == 25)]
    columns = [
        ("strategy", "Strategy"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"),
        ("Sortino", "Sortino"), ("Maximum Drawdown", "Max DD"),
        ("Annual Turnover", "Annual turnover"), ("Exposure", "Exposure"),
        ("Worst Month", "Worst month"),
    ]
    percent = {"CAGR", "Maximum Drawdown", "Exposure", "Worst Month"}
    (output / "strategy_results.md").write_text(f"""# Predeclared derivatives strategy results

No strategy or threshold was selected using holdout performance. OI-dependent strategies remain unavailable rather than being approximated.

## Availability

{_table(availability, [('strategy', 'Strategy'), ('available', 'Available'), ('reason', 'Reason')])}

## Development at 25 bps

{_table(development.sort_values('Sharpe', ascending=False), columns, percent)}

## Cost sensitivity

{_table(strategy_metrics[strategy_metrics.category == 'strategy'].sort_values(['strategy', 'split', 'cost_bps']), [('strategy', 'Strategy'), ('split', 'Split'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover')], {'CAGR', 'Maximum Drawdown'})}
""", encoding="utf-8")

    (output / "holdout_results.md").write_text(f"""# Reused 2025–2026 evaluation results

This period is held out from fitting and CPCV tuning in this module. Because its market outcomes were already inspected in earlier projects, it is not a pristine prospective holdout for the newly designed derivatives hypotheses.

{_table(holdout.sort_values('Sharpe', ascending=False), columns, percent)}

## Paper-trading acceptance

{_table(acceptances, [('strategy', 'Strategy'), ('passes', 'Passes'), ('failures', 'Failures')])}

- Tested configurations: {statistics['tested_configurations']}.
- Approximate PBO: {_format(statistics['pbo'], True)}.
- Deflated-Sharpe probability for the predeclared derivatives risk gate: {_format(statistics['derivatives_gate_dsr'], True)}.
""", encoding="utf-8")

    matched = comparisons.groupby(["target", "model"]).agg(
        development_improves=("improves_both", lambda values: bool(values.iloc[0]) if len(values) else False),
        consistent=("improves_both", "all"),
    ).reset_index() if len(comparisons) else pd.DataFrame()
    robust_predictive = bool(matched.consistent.any()) if len(matched) else False
    any_strategy = bool(acceptances.passes.any()) if len(acceptances) else False
    missing = "long-history open interest, liquidations, long/short positioning, taker imbalance, multi-venue basis and order-book data"
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

1. **Available derivatives data:** long-history realized funding and Binance premium-index basis for BTC/ETH. Recent OI, account-ratio and taker-ratio snapshots were not historically usable.
2. **Did derivatives improve prediction?** {'Yes, for at least one matched model in both reported splits.' if robust_predictive else 'No consistent matched development-and-evaluation improvement over price-only features.'}
3. **Did a derivatives strategy survive the reused evaluation period?** {'At least one passed the numerical criteria.' if any_strategy else 'No.'}
4. **Did it survive costs?** {'Yes under the stated 25/50-bps rule.' if any_strategy else 'No candidate passed the full 25/50-bps acceptance rule.'}
5. **Suitable for paper trading?** {'Only as a prospective zero-capital monitor because the historical holdout is consumed.' if any_strategy else 'No.'}
6. **Still missing:** {missing}.

Do not promote the best 2025–2026 cell. The next credible step is prospective collection of normalized OI, basis, liquidations and taker flow, followed by a newly registered forward holdout.
""", encoding="utf-8")

    payload = {
        "protocol": {
            "development": f"{DEVELOPMENT_START} to {DEVELOPMENT_END}",
            "evaluation": f"{HOLDOUT_START.date()} to {HOLDOUT_END.date()}",
            "evaluation_is_pristine": False,
            "feature_lag_days": 1,
            "random_split": False,
            "cpcv_inside_training": True,
        },
        "coverage": coverage.to_dict("records"), "dataset": dataset.metadata,
        "predictive_metrics": model_metrics.to_dict("records"),
        "comparisons": comparisons.to_dict("records"),
        "selection_history": selection.to_dict("records"),
        "strategy_metrics": strategy_metrics.to_dict("records"),
        "availability": availability.to_dict("records"),
        "acceptance": acceptances.to_dict("records"), "statistics": statistics,
    }
    (output / "results.json").write_text(json.dumps(_plain(payload), indent=2), encoding="utf-8")
    predictions.to_csv(output / "predictions.csv", index=False)
    selection_copy = selection.copy()
    selection_copy["parameters"] = selection_copy.parameters.map(json.dumps)
    selection_copy.to_csv(output / "selection_history.csv", index=False)
    model_metrics.to_csv(output / "predictive_metrics.csv", index=False)
    strategy_metrics.to_csv(output / "strategy_metrics.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Derivatives-based crypto signal research")
    parser.add_argument("--spot-data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--existing-funding", default="data/binance_funding_daily.csv")
    parser.add_argument("--raw-dir", default="data/raw/derivatives")
    parser.add_argument("--processed-dir", default="data/processed/derivatives")
    parser.add_argument("--output-dir", default="reports/derivatives_signals")
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()

    processed_path = Path(args.processed_dir) / "binance_derivatives_daily.csv"
    coverage_path = Path(args.processed_dir) / "coverage.csv"
    if args.refresh_data or not processed_path.exists():
        print("downloading Binance public derivatives datasets", flush=True)
        derivatives, coverage = download_public_derivatives(
            args.raw_dir, args.processed_dir, end=str(HOLDOUT_END.date())
        )
    else:
        derivatives = pd.read_csv(processed_path, parse_dates=["date"])
        coverage = pd.read_csv(coverage_path)
    derivatives = merge_existing_funding(derivatives, args.existing_funding)
    derivatives.to_csv(Path(args.processed_dir) / "derivatives_daily_merged.csv", index=False)

    spot = DataIngestion().load_csv(args.spot_data)
    dataset = build_derivatives_features(spot, derivatives)
    candidates = predictive_candidates(dataset)
    print(f"running {len(candidates)} predictive configurations", flush=True)
    predictions, selection = walk_forward_predictions(dataset, candidates)
    model_metrics = predictive_metrics(predictions)
    matched = model_metrics[model_metrics.model.isin(["logistic", "elastic_net"])].pivot_table(
        index=["target", "model", "split"], columns="feature_set", values=["auc", "brier"]
    )
    comparison_rows = []
    for index, row in matched.iterrows():
        if ("auc", "price_only") not in row.index or ("auc", "price_derivatives") not in row.index:
            continue
        delta_auc = row[("auc", "price_derivatives")] - row[("auc", "price_only")]
        delta_brier = row[("brier", "price_derivatives")] - row[("brier", "price_only")]
        comparison_rows.append({
            "target": index[0], "model": index[1], "split": index[2],
            "delta_auc": delta_auc, "delta_brier": delta_brier,
            "improves_both": bool(delta_auc > 0 and delta_brier < 0),
        })
    comparisons = pd.DataFrame(comparison_rows)

    strategy_names = [
        "price_only_trend", "funding_crowding_avoidance", "funding_mean_reversion",
        "oi_confirmed_trend", "oi_divergence_risk_off", "btc_eth_relative_value",
        "derivatives_risk_gate",
    ]
    weekly_dates = pd.DatetimeIndex(sorted(dataset.frame.date.unique()))
    weekly_dates = weekly_dates[weekly_dates.weekday == 4]
    weights_by_strategy, availability_rows = {}, []
    for name in strategy_names:
        weights, reason = strategy_weights(dataset, name)
        availability_rows.append({"strategy": name, "available": weights is not None, "reason": reason or "available"})
        if weights is not None:
            weights_by_strategy[name] = weights
    for benchmark in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50"):
        weights_by_strategy[benchmark] = _benchmark_weights(weekly_dates, benchmark)
        availability_rows.append({"strategy": benchmark, "available": True, "reason": "benchmark"})

    metric_rows, outcomes_25, development_returns = [], {}, {}
    for name, weights in weights_by_strategy.items():
        category = "benchmark" if name.endswith("buy_hold") or name == "btc_eth_50_50" else "strategy"
        for cost in COST_LEVELS:
            outcome = backtest_spot_weights(spot, weights, cost)
            if cost == 25:
                outcomes_25[name] = outcome
                development_returns[name] = outcome.returns.loc[DEVELOPMENT_START:DEVELOPMENT_END]
            for split, start, end in (
                ("development", DEVELOPMENT_START, DEVELOPMENT_END),
                ("holdout", str(HOLDOUT_START.date()), str(HOLDOUT_END.date())),
            ):
                metric_rows.append({
                    "strategy": name, "category": category, "split": split, "cost_bps": cost,
                    **period_metrics(outcome, start, end),
                })
    strategy_metrics = pd.DataFrame(metric_rows)
    btc_25 = period_metrics(outcomes_25["btc_buy_hold"], str(HOLDOUT_START.date()), str(HOLDOUT_END.date()))
    acceptance_rows = []
    for name in strategy_names:
        if name not in weights_by_strategy:
            continue
        row25 = strategy_metrics[(strategy_metrics.strategy == name) & (strategy_metrics.split == "holdout") & (strategy_metrics.cost_bps == 25)].iloc[0].to_dict()
        row50 = strategy_metrics[(strategy_metrics.strategy == name) & (strategy_metrics.split == "holdout") & (strategy_metrics.cost_bps == 50)].iloc[0].to_dict()
        passes, failures = acceptance(row25, row50, btc_25)
        acceptance_rows.append({"strategy": name, "passes": passes, "failures": "; ".join(failures)})
    acceptances = pd.DataFrame(acceptance_rows)
    tested = len(candidates) + len(strategy_names) * len(COST_LEVELS)
    gate_returns = outcomes_25.get("derivatives_risk_gate", outcomes_25["price_only_trend"]).returns.loc[str(HOLDOUT_START.date()):str(HOLDOUT_END.date())]
    statistics = {
        "tested_configurations": tested,
        "pbo": probability_backtest_overfitting(pd.DataFrame(development_returns)),
        "derivatives_gate_dsr": deflated_sharpe_probability(gate_returns, tested),
    }
    _write_reports(
        Path(args.output_dir), coverage, dataset, predictions, model_metrics,
        comparisons, selection, strategy_metrics, pd.DataFrame(availability_rows),
        acceptances, statistics,
    )
    print(acceptances.to_string(index=False), flush=True)
    print(f"wrote derivatives study to {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
