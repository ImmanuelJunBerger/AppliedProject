from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.crypto_mlsystem.data import DataIngestion, UniverseBuilder
from src.crypto_mlsystem.metrics import performance_metrics
from src.crypto_mlsystem.research_engine import (
    build_allocator_features,
    constant_strategy_allocations,
    execute_portfolio,
    walk_forward_strategy_allocator,
)
from src.crypto_mlsystem.signals import build_signal_bundle, strategy_gross_returns
from src.crypto_mlsystem.triple_barrier import (
    build_meta_features,
    triple_barrier_events,
    walk_forward_meta_filter,
)


SUBPERIODS = {
    "2020-2021 bull market": ("2020-01-01", "2021-12-31"),
    "2022 bear market": ("2022-01-01", "2022-12-31"),
    "2023 recovery": ("2023-01-01", "2023-12-31"),
    "2024-2026 recent period": ("2024-01-01", "2026-12-31"),
}


def plain(value):
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value.date())
    return value


def metric_subset(metrics: dict) -> dict:
    keys = ["CAGR", "Sharpe", "Maximum Drawdown", "Annualized Volatility", "Turnover", "Exposure", "Transaction Costs"]
    return {key: float(metrics[key]) for key in keys}


def coverage_diagnostics(panel: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    start, end = panel.date.min(), panel.date.max()
    calendar_days = len(pd.date_range(start, end, freq="D"))
    asset_rows = []
    missing_within = 0
    possible_within = 0
    for symbol, frame in panel.groupby("symbol"):
        asset_start, asset_end = frame.date.min(), frame.date.max()
        possible = len(pd.date_range(asset_start, asset_end, freq="D"))
        observations = frame.date.nunique()
        missing = possible - observations
        possible_within += possible
        missing_within += missing
        asset_rows.append({
            "symbol": symbol,
            "start": asset_start,
            "end": asset_end,
            "observations": observations,
            "missing_days_within_listing_span": missing,
            "missing_percentage_within_listing_span": missing / possible if possible else 0,
        })
    assets = panel.symbol.nunique()
    full_possible = calendar_days * assets
    summary = {
        "start_date": str(start.date()),
        "end_date": str(end.date()),
        "assets": int(assets),
        "observations": int(len(panel)),
        "calendar_days": calendar_days,
        "missing_percentage_full_rectangular_panel": float(1 - len(panel) / full_possible),
        "missing_percentage_within_listing_spans": float(missing_within / possible_within),
        "assets_available_2019": int(panel.loc[panel.date <= "2019-12-31", "symbol"].nunique()),
        "assets_available_2020": int(panel.loc[panel.date <= "2020-12-31", "symbol"].nunique()),
    }
    return summary, pd.DataFrame(asset_rows)


def build_context(full_panel: pd.DataFrame, top_n: int, frequency: str, with_meta: bool = True) -> dict:
    builder = UniverseBuilder(min_history_days=90)
    universes = builder.monthly_universe(full_panel, top_n)
    selected = sorted(set().union(*universes.values()))
    panel = full_panel[full_panel.symbol.isin(selected)].copy()
    bundle = build_signal_bundle(panel, universes, frequency, max_asset_weight=min(0.10, 1 / max(top_n, 1)))
    strategy_returns = strategy_gross_returns(bundle)
    features = build_allocator_features(panel, bundle, strategy_returns)
    allocator = walk_forward_strategy_allocator(
        features,
        strategy_returns,
        frequency,
        train_min_days=180,
        label_horizon_days=14,
        max_strategy_weight=0.45,
        confidence_floor=0.30,
    )
    context = {
        "top_n": top_n,
        "frequency": frequency,
        "universes": universes,
        "selected": selected,
        "panel": panel,
        "bundle": bundle,
        "strategy_returns": strategy_returns,
        "features": features,
        "allocator": allocator,
    }
    if with_meta:
        events = triple_barrier_events(panel, bundle, 1.5, 1.0, 14)
        meta_frame, meta_columns = build_meta_features(panel, bundle, strategy_returns, events)
        meta = walk_forward_meta_filter(bundle, meta_frame, meta_columns, 0.55, 250, 730)
        context.update({"events": events, "meta_frame": meta_frame, "meta_columns": meta_columns, "meta": meta})
    return context


def run_variants(context: dict, cost_bps: int = 25) -> tuple[dict, dict]:
    bundle = context["bundle"]
    strategies = list(bundle.weights)
    allocator = context["allocator"]
    meta = context["meta"]
    start_candidates = [date for date in [allocator.first_prediction_date, meta.first_prediction_date] if date is not None]
    common_start = max(start_candidates)
    constant = constant_strategy_allocations(bundle.asset_returns.index, strategies)
    variants = {
        "base_equal_strategy_mix": (bundle.weights, constant),
        "ml_strategy_allocation": (bundle.weights, allocator.weights),
        "triple_barrier_meta_labeling": (meta.weights, constant),
        "ml_plus_triple_barrier": (meta.weights, allocator.weights),
    }
    results = {}
    objects = {}
    for name, (weights, allocations) in variants.items():
        result = execute_portfolio(
            bundle, weights, allocations, cost_bps, 0.10, 0.35, 0.75, common_start
        )
        results[name] = {"metrics": metric_subset(result.metrics), "diagnostics": result.diagnostics}
        objects[name] = result
    return results, objects


def benchmark_results(context: dict, start_date: pd.Timestamp, cost_bps: int = 25) -> tuple[dict, dict]:
    bundle = context["bundle"]
    index, columns = bundle.asset_returns.index, bundle.asset_returns.columns
    strategies = list(bundle.weights)
    benchmark_weights = {}
    for symbol in ["BTC", "ETH"]:
        weights = pd.DataFrame(0.0, index=index, columns=columns)
        if symbol in columns:
            weights[symbol] = 1.0
        benchmark_weights[f"{symbol}_buy_and_hold"] = weights
    fifty = pd.DataFrame(0.0, index=index, columns=columns)
    for symbol in ["BTC", "ETH"]:
        if symbol in columns:
            fifty[symbol] = 0.5
    benchmark_weights["50_50_BTC_ETH"] = fifty
    equal_top = context["bundle"].eligible.astype(float)
    equal_top = equal_top.div(equal_top.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    benchmark_weights[f"equal_weight_top_{context['top_n']}"] = equal_top
    for strategy in strategies:
        benchmark_weights[f"standalone_{strategy}"] = bundle.weights[strategy]

    results, objects = {}, {}
    for name, weights in benchmark_weights.items():
        synthetic = {"benchmark": weights}
        allocations = pd.DataFrame({"benchmark": 1.0}, index=index)
        is_buy_hold = name in {"BTC_buy_and_hold", "ETH_buy_and_hold", "50_50_BTC_ETH", f"equal_weight_top_{context['top_n']}"}
        result = execute_portfolio(
            bundle,
            synthetic,
            allocations,
            cost_bps,
            1.0 if is_buy_hold else 0.10,
            99.0 if is_buy_hold else 0.35,
            2.0,
            start_date,
        )
        results[name] = {"metrics": metric_subset(result.metrics), "diagnostics": result.diagnostics}
        objects[name] = result
    equal_mix = execute_portfolio(
        bundle,
        bundle.weights,
        constant_strategy_allocations(index, strategies),
        cost_bps,
        0.10,
        0.35,
        0.75,
        start_date,
    )
    results["equal_weight_strategy_mix"] = {"metrics": metric_subset(equal_mix.metrics), "diagnostics": equal_mix.diagnostics}
    objects["equal_weight_strategy_mix"] = equal_mix
    return results, objects


def subperiod_results(result_objects: dict) -> dict:
    output = {}
    for period, (start, end) in SUBPERIODS.items():
        output[period] = {}
        for name, result in result_objects.items():
            returns = result.returns.loc[start:end]
            if returns.empty:
                output[period][name] = {"observations": 0}
                continue
            turnover = result.turnover.reindex(returns.index)
            costs = result.costs.reindex(returns.index)
            output[period][name] = {
                "observations": int(len(returns)),
                **metric_subset(performance_metrics(returns, turnover, costs)),
            }
    return output


def confidence_summary(series: pd.Series) -> dict:
    if series.empty:
        return {"count": 0}
    return {
        "count": int(len(series)),
        "mean": float(series.mean()),
        "p10": float(series.quantile(0.10)),
        "p25": float(series.quantile(0.25)),
        "median": float(series.median()),
        "p75": float(series.quantile(0.75)),
        "p90": float(series.quantile(0.90)),
    }


def md_table(rows: list[dict], columns: list[tuple[str, str]], percent: set[str] | None = None) -> str:
    percent = percent or set()
    header = "| " + " | ".join(label for _, label in columns) + " |"
    separator = "|" + "|".join("---" for _ in columns) + "|"
    lines = [header, separator]
    for row in rows:
        values = []
        for key, _ in columns:
            value = row.get(key, "")
            if isinstance(value, float):
                value = f"{value * 100:.2f}%" if key in percent else f"{value:.3f}"
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_reports(output_dir: Path, results: dict, main_context: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    coverage = results["coverage"]
    comparison_rows = []
    for name, values in {**results["main_experiments"], **results["benchmarks"]}.items():
        metrics = values["metrics"]
        comparison_rows.append({"experiment": name, **metrics})
    comparison = md_table(
        comparison_rows,
        [("experiment", "Experiment"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Maximum Drawdown", "Max DD"), ("Turnover", "Turnover")],
        {"CAGR", "Maximum Drawdown", "Turnover"},
    )
    best_ml = results["main_experiments"]["ml_plus_triple_barrier"]["metrics"]
    base = results["main_experiments"]["base_equal_strategy_mix"]["metrics"]
    improves = best_ml["Sharpe"] > base["Sharpe"] and best_ml["CAGR"] > base["CAGR"]
    conclusion = (
        "The combined ML and triple-barrier system improved both CAGR and Sharpe over the base signal mix."
        if improves else
        "The combined ML and triple-barrier system did not improve both CAGR and Sharpe over the base signal mix; the evidence does not support claiming ML value-add."
    )
    robustness_rows = []
    for dimension, cases in results["robustness"].items():
        for case, values in cases.items():
            robustness_rows.append({"dimension": dimension, "case": case, **values["metrics"]})
    robustness_table = md_table(
        robustness_rows,
        [("dimension", "Dimension"), ("case", "Case"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Maximum Drawdown", "Max DD")],
        {"CAGR", "Maximum Drawdown"},
    )
    (output_dir / "results_summary.md").write_text(
        f"""# Real-data results summary

## Dataset

- Source: Binance spot USDT OHLCV through ccxt
- Coverage: {coverage['start_date']} to {coverage['end_date']}
- Assets: {coverage['assets']}
- Observations: {coverage['observations']:,}
- Full-panel missingness: {coverage['missing_percentage_full_rectangular_panel']:.2%}
- Within-listing-span missingness: {coverage['missing_percentage_within_listing_spans']:.2%}

## Main comparison

All portfolios are long-only, rebalanced weekly, volatility-scaled, subject to asset/strategy caps and a turnover cap, and charged 25 bps on underlying asset turnover.

{comparison}

## Robustness tests

{robustness_table}

## Conclusion

{conclusion}
""", encoding="utf-8")

    sub_rows = []
    for period, experiments in results["subperiods"].items():
        for name, values in experiments.items():
            if values.get("observations", 0):
                sub_rows.append({"period": period, "experiment": name, **values})
    (output_dir / "subperiod_analysis.md").write_text(
        "# Subperiod analysis\n\n" + md_table(
            sub_rows,
            [("period", "Period"), ("experiment", "Experiment"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Maximum Drawdown", "Max DD"), ("observations", "Days")],
            {"CAGR", "Maximum Drawdown"},
        ) + "\n", encoding="utf-8")

    event_diag = results["triple_barrier"]["event_diagnostics"]
    event_rows = [{"strategy": name, **values} for name, values in event_diag.items()]
    (output_dir / "triple_barrier_results.md").write_text(
        f"""# Triple-barrier meta-labeling results

Profit-taking is 1.5 times trailing daily volatility, stop-loss is 1.0 times volatility, and the vertical barrier is 14 days. Barrier labels are only admitted to training after `label_end`; live features are lagged.

- Rejected trades: {results['triple_barrier']['rejected_percentage']:.2%}
- Meta-model confidence: {json.dumps(results['triple_barrier']['confidence_distribution'])}

{md_table(event_rows, [('strategy', 'Strategy'), ('events', 'Events'), ('positive_label_rate', 'Positive labels'), ('average_barrier_return', 'Average barrier return')], {'positive_label_rate', 'average_barrier_return'})}

## Experiment comparison

{comparison}
""", encoding="utf-8")

    diagnostics_rows = []
    for name, values in results["main_experiments"].items():
        diagnostics_rows.append({"experiment": name, **values["diagnostics"]})
    importance_rows = [{"feature": name, "importance": value} for name, value in results["diagnostics"]["allocator_feature_importance"].items()]
    (output_dir / "strategy_signal_diagnostics.md").write_text(
        "# Strategy signal diagnostics\n\n" + md_table(
            diagnostics_rows,
            [("experiment", "Experiment"), ("number_of_trades", "Trades"), ("hit_rate", "Hit rate"), ("average_win", "Average win"), ("average_loss", "Average loss"), ("turnover", "Turnover"), ("exposure", "Exposure"), ("transaction_costs", "Costs")],
            {"hit_rate", "average_win", "average_loss", "turnover", "exposure", "transaction_costs"},
        ) + "\n\n## Allocator feature importance\n\n" + md_table(importance_rows, [("feature", "Feature"), ("importance", "Mean absolute coefficient")]) + "\n", encoding="utf-8")

    (output_dir / "limitations.md").write_text(
        f"""# Real-data limitations

- ccxt returns Binance's current market catalogue. Markets that were fully delisted and removed cannot be reconstructed, so survivorship bias remains despite point-in-time monthly ranking.
- Binance began trading in 2017, but the requested consistent panel starts in 2019 and most assets list later. Full rectangular-panel missingness is {coverage['missing_percentage_full_rectangular_panel']:.2%}; within-listing-span missingness is {coverage['missing_percentage_within_listing_spans']:.2%}.
- Coinbase is supported as a fallback downloader, but histories are not automatically spliced across venues because doing so would mix liquidity, prices, fees, and listing rules.
- OHLCV supplies exchange turnover, not true circulating market capitalization. Universes are therefore ranked by lagged dollar turnover, not market cap.
- High/low daily bars do not reveal intraday ordering when both barriers are touched. The implementation conservatively assigns stop-loss first.
- Backtests do not model spread, market impact, order-book depth, taxes, funding, or exchange outages. Costs are linear sensitivity assumptions, not execution guarantees.
- Feature importance is mean absolute standardized logistic-regression coefficient, not causal importance.
- Multiple robustness comparisons increase selection risk. Results should be validated on another venue and a later untouched holdout before deployment.
""", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run extended real-data crypto signal and meta-label research.")
    parser.add_argument("--data", required=True)
    parser.add_argument("--output-dir", default="reports/real_data")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    full_panel = DataIngestion().load_csv(args.data)
    coverage, per_asset = coverage_diagnostics(full_panel)

    main_context = build_context(full_panel, 20, "W-FRI", with_meta=True)
    main_results, main_objects = run_variants(main_context, 25)
    common_start = max(main_context["allocator"].first_prediction_date, main_context["meta"].first_prediction_date)
    benchmarks, benchmark_objects = benchmark_results(main_context, common_start, 25)

    robustness = {"universe": {}, "frequency": {}, "cost": {}, "feature_ablation": {}, "strategy_ablation": {}}
    contexts = {(20, "W-FRI"): main_context}
    for top_n in [10, 50]:
        contexts[(top_n, "W-FRI")] = build_context(full_panel, top_n, "W-FRI", with_meta=True)
    for frequency in ["2W-FRI", "ME"]:
        contexts[(20, frequency)] = build_context(full_panel, 20, frequency, with_meta=True)
    for (top_n, frequency), context in contexts.items():
        variant_results, _ = run_variants(context, 25)
        combo = variant_results["ml_plus_triple_barrier"]
        if frequency == "W-FRI":
            robustness["universe"][str(top_n)] = combo
        if top_n == 20:
            robustness["frequency"][frequency] = combo
    for cost in [10, 25, 50, 100]:
        result = execute_portfolio(
            main_context["bundle"],
            main_context["meta"].weights,
            main_context["allocator"].weights,
            cost,
            0.10,
            0.35,
            0.75,
            common_start,
        )
        robustness["cost"][str(cost)] = {"metrics": metric_subset(result.metrics), "diagnostics": result.diagnostics}

    features = main_context["features"]
    ablations = {
        "all_features": list(features.columns),
        "without_market_state": [column for column in features if not column.startswith("market_")],
        "without_strategy_health": [column for column in features if not column.startswith("strategy_")],
    }
    for name, columns in ablations.items():
        allocation = walk_forward_strategy_allocator(features, main_context["strategy_returns"], "W-FRI", 180, 14, 0.45, 0.30, columns)
        result = execute_portfolio(main_context["bundle"], main_context["meta"].weights, allocation.weights, 25, 0.10, 0.35, 0.75, common_start)
        robustness["feature_ablation"][name] = {"metrics": metric_subset(result.metrics), "diagnostics": result.diagnostics}

    all_strategies = list(main_context["bundle"].weights)
    for removed in all_strategies:
        kept = [name for name in all_strategies if name != removed]
        columns = [column for column in features if not column.endswith(f"__{removed}")]
        allocation = walk_forward_strategy_allocator(features, main_context["strategy_returns"], "W-FRI", 180, 14, 0.45, 0.30, columns, kept)
        kept_weights = {name: main_context["meta"].weights[name] for name in kept}
        result = execute_portfolio(main_context["bundle"], kept_weights, allocation.weights, 25, 0.10, 0.35, 0.75, common_start)
        robustness["strategy_ablation"][f"without_{removed}"] = {"metrics": metric_subset(result.metrics), "diagnostics": result.diagnostics}

    event_diag = {}
    for strategy, frame in main_context["events"].groupby("strategy"):
        event_diag[strategy] = {
            "events": int(len(frame)),
            "positive_label_rate": float(frame.label.mean()),
            "average_barrier_return": float(frame.barrier_return.mean()),
        }
    combined_objects = {**main_objects, **{name: benchmark_objects[name] for name in ["BTC_buy_and_hold", "ETH_buy_and_hold", "50_50_BTC_ETH", "equal_weight_top_20"]}}
    results = {
        "coverage": coverage,
        "main_configuration": {
            "universe": 20,
            "rebalance": "W-FRI",
            "cost_bps": 25,
            "min_asset_history_days": 90,
            "allocator_train_days": 180,
            "triple_barrier": {"profit_taking": 1.5, "stop_loss": 1.0, "vertical_days": 14},
        },
        "main_experiments": main_results,
        "benchmarks": benchmarks,
        "subperiods": subperiod_results(combined_objects),
        "robustness": robustness,
        "triple_barrier": {
            "events": int(len(main_context["events"])),
            "rejected_percentage": main_context["meta"].rejected_percentage,
            "confidence_distribution": confidence_summary(main_context["meta"].confidences),
            "feature_importance": plain(main_context["meta"].feature_importance.head(20).to_dict()),
            "event_diagnostics": event_diag,
        },
        "diagnostics": {
            "allocator_confidence_distribution": confidence_summary(main_context["allocator"].confidences),
            "allocator_feature_importance": plain(main_context["allocator"].feature_importance.head(20).to_dict()),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    per_asset.to_csv(output_dir / "asset_coverage.csv", index=False)
    main_context["events"].to_csv(output_dir / "triple_barrier_events.csv", index=False)
    main_context["meta"].events.to_csv(output_dir / "meta_label_predictions.csv", index=False)
    (output_dir / "extended_results.json").write_text(json.dumps(plain(results), indent=2), encoding="utf-8")
    write_reports(output_dir, results, main_context)
    print(json.dumps(plain({
        "coverage": coverage,
        "main_experiments": main_results,
        "robustness": robustness,
        "triple_barrier": results["triple_barrier"],
    }), indent=2))


if __name__ == "__main__":
    main()
