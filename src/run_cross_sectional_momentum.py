"""Execute the ML-enhanced cross-sectional momentum research study."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.crypto_mlsystem.cross_sectional_momentum import (
    COST_LEVELS,
    HOLDOUT_END,
    HOLDOUT_START,
    Candidate,
    MomentumStudyResult,
    benchmark_portfolio,
    block_bootstrap_sharpe_ci,
    build_momentum_dataset,
    deflated_sharpe_probability,
    momentum_baseline_scores,
    paired_sharpe_delta_ci,
    period_metrics,
    primary_candidates,
    probability_backtest_overfitting,
    scores_to_portfolio,
    walk_forward_candidate_scores,
)
from src.crypto_mlsystem.data import DataIngestion


SUBPERIODS = {
    "2020-2021": ("2020-01-01", "2021-12-31"),
    "2022": ("2022-01-01", "2022-12-31"),
    "2023-2024": ("2023-01-01", "2024-12-31"),
    "2025-2026_holdout": ("2025-01-01", "2026-06-22"),
}


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


def _merge_funding(panel: pd.DataFrame, path: str | None) -> pd.DataFrame:
    if not path or not Path(path).exists():
        return panel
    funding = pd.read_csv(path, parse_dates=["date"])
    return panel.merge(funding, on=["date", "symbol"], how="left", validate="one_to_one")


def _load_volatility_probability(path: str | None) -> pd.Series | None:
    if not path or not Path(path).exists():
        return None
    predictions = pd.read_csv(path, parse_dates=["date"])
    selected = predictions[
        (predictions.model == "elastic_net") & (predictions.feature_set == "price_only")
    ]
    if selected.empty or selected.duplicated("date").any():
        return None
    return selected.set_index("date").probability.astype(float).sort_index()


def _candidate_dependencies(candidate: Candidate, feature_set: str | None = None) -> list[Candidate]:
    feature_set = feature_set or candidate.feature_set
    if candidate.model != "ensemble":
        return [Candidate(f"{candidate.model}__{candidate.target}__{feature_set}", candidate.model, candidate.target, feature_set)]
    return [
        Candidate(f"elastic_net__{candidate.target}__{feature_set}", "elastic_net", candidate.target, feature_set),
        Candidate(f"gradient_boosting__{candidate.target}__{feature_set}", "gradient_boosting", candidate.target, feature_set),
        Candidate(f"ensemble__{candidate.target}__{feature_set}", "ensemble", candidate.target, feature_set),
    ]


def _score_for(scores: pd.DataFrame, candidate_name: str) -> pd.DataFrame:
    return scores[scores.candidate == candidate_name].copy()


def _metric_row(name: str, candidate: Candidate | None, split: str, result, start, end, cost: int, category: str):
    return {
        "name": name,
        "candidate": candidate.name if candidate else name,
        "model": candidate.model if candidate else category,
        "target": candidate.target if candidate else "benchmark",
        "feature_set": candidate.feature_set if candidate else "N/A",
        "category": category,
        "split": split,
        "cost_bps": cost,
        **period_metrics(result, start, end),
    }


def _run_primary(dataset, scores, candidates, common_start):
    rows, returns, results = [], {}, {}
    baseline_scores = scores[scores.candidate == "pure_momentum"]
    all_candidates = [Candidate("pure_momentum", "baseline", "momentum_90_ex_7", "price_only")] + candidates
    for candidate in all_candidates:
        candidate_scores = baseline_scores if candidate.name == "pure_momentum" else _score_for(scores, candidate.name)
        if candidate_scores.empty:
            continue
        result = scores_to_portfolio(dataset, candidate_scores, top_k=5, cost_bps=25)
        results[candidate.name] = result
        returns[candidate.name] = result.returns.loc[common_start:"2024-12-31"]
        rows.append(_metric_row(candidate.name, candidate, "development", result, common_start, "2024-12-31", 25, "model" if candidate.model != "baseline" else "baseline"))
        rows.append(_metric_row(candidate.name, candidate, "holdout", result, "2025-01-01", "2026-06-22", 25, "model" if candidate.model != "baseline" else "baseline"))
    return pd.DataFrame(rows), pd.DataFrame(returns), results


def _robustness_for_scores(dataset, scores, universe_n: int, candidate_name: str):
    rows = []
    for top_k, frequency, cost in product((3, 5, 10), ("weekly", "biweekly"), COST_LEVELS):
        if top_k > universe_n:
            continue
        result = scores_to_portfolio(dataset, scores, top_k=top_k, cost_bps=cost, rebalance=frequency)
        rows.append({
            "universe": universe_n, "top_k": top_k, "rebalance": frequency,
            "cost_bps": cost, "candidate": candidate_name,
            "development": period_metrics(result, result.returns.index.min(), "2024-12-31"),
            "holdout": period_metrics(result, "2025-01-01", "2026-06-22"),
        })
    return rows


def _write_reports(output_dir: Path, result: MomentumStudyResult) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = result.metrics
    champion = result.champion
    holdout = metrics[(metrics.split == "holdout") & (metrics.cost_bps == 25)].sort_values("Sharpe", ascending=False)
    development = metrics[(metrics.split == "development") & (metrics.cost_bps == 25)].sort_values("Sharpe", ascending=False)
    baseline_holdout = holdout[holdout.name == "pure_momentum"].iloc[0]
    champion_holdout = holdout[holdout.name == champion.name].iloc[0]
    paired = result.statistics["paired_holdout_sharpe_delta_ci"]
    improves = (
        champion_holdout.Sharpe > baseline_holdout.Sharpe
        and champion_holdout.CAGR > baseline_holdout.CAGR
        and paired["lower"] > 0
    )
    survives = champion_holdout.Sharpe > 0 and champion_holdout.CAGR > 0
    suitable = improves and survives and result.statistics["deflated_sharpe_probability"] >= 0.50
    metric_columns = [
        ("name", "Name"), ("model", "Model"), ("target", "Target"),
        ("CAGR", "CAGR"), ("Sharpe", "Sharpe"), ("Sortino", "Sortino"),
        ("Maximum Drawdown", "Max DD"), ("Calmar", "Calmar"),
        ("Turnover", "Turnover"), ("Exposure", "Exposure"),
        ("Average Holdings", "Holdings"),
    ]
    percent = {"CAGR", "Maximum Drawdown", "Turnover", "Exposure"}

    data = result.dataset.metadata
    (output_dir / "results_summary.md").write_text(
        f"""# ML-enhanced cross-sectional crypto momentum

## Dataset and locked protocol

- Data: Binance daily spot panel, {data['start']} to {data['end']}.
- Primary universe: point-in-time top {data['top_n']} by trailing 90-day median dollar volume.
- Weekly cross-sectional observations: {data['rebalance_observations']}.
- Asset/weekly event rows: {data['event_rows']}.
- Unique historical universe members: {data['unique_historical_members']}.
- Full price-matrix missingness: {data['missingness_full_price_matrix']:.2%}.
- Derivatives: {'daily Binance funding included' if data['derivatives_available'] else 'unavailable'}.
- Locked holdout: 2025-01-01 onward; no holdout model, feature, target, or portfolio selection.
- Primary portfolio: top 5, weekly, equal weight subject to 20% cap, 75% turnover cap, 25 bps.

The source market catalogue cannot recover pairs Binance has removed, so the universe remains subject to delisting survivorship bias. Target B is mathematically rank-equivalent to Target A because subtracting the same weekly universe return does not change cross-sectional ranks; the implementation reports this rather than treating it as independent evidence.

## Development comparison

{_table(development, metric_columns, percent)}

## Locked holdout comparison

{_table(holdout, metric_columns, percent)}

## Development-selected champion

- Candidate: **{champion.name}**
- Model: **{champion.model}**
- Target: **{champion.target}**
- Feature set: **{champion.feature_set}**
- Configurations counted: {result.statistics['tested_configurations']}
""", encoding="utf-8")

    (output_dir / "holdout_results.md").write_text(
        f"""# Locked holdout results

The champion was selected using development performance only. All candidates are shown to expose selection risk; none was substituted after viewing holdout results.

{_table(holdout, metric_columns + [('Transaction Costs', 'Total costs'), ('Best Month', 'Best month'), ('Worst Month', 'Worst month')], percent | {'Transaction Costs', 'Best Month', 'Worst Month'})}

## Paired comparison with pure momentum

- Sharpe delta 95% block-bootstrap interval: [{paired['lower']:.3f}, {paired['upper']:.3f}]
- Median Sharpe delta: {paired['median']:.3f}
- Holdout survives with positive Sharpe and CAGR: **{'Yes' if survives else 'No'}**
""", encoding="utf-8")

    model_view = metrics[(metrics.cost_bps == 25) & (metrics.category.isin(["model", "baseline"]))].sort_values(["split", "Sharpe"], ascending=[True, False])
    (output_dir / "model_comparison.md").write_text(
        f"""# Model and target comparison

Hyperparameters were tuned by date-group CPCV inside each expanding training window. Quarterly refits use no future labels; holdout models are fitted once using labels ending before 2025-01-01.

{_table(model_view, [('split', 'Split')] + metric_columns, percent)}

Target A and Target B have identical cross-sectional ranks by construction. Target C is a top-quintile classifier. Target D ranks forward return divided by trailing volatility.
""", encoding="utf-8")

    robust_flat = pd.json_normalize(result.robustness.to_dict("records"), sep="_")
    (output_dir / "robustness.md").write_text(
        f"""# Robustness tests

These configurations are exploratory and did not replace the development-selected champion.

## Universe, holdings, frequency, and cost grid

{_table(robust_flat, [('universe', 'Universe'), ('top_k', 'Top K'), ('rebalance', 'Rebalance'), ('cost_bps', 'Cost'), ('development_Sharpe', 'Dev Sharpe'), ('holdout_Sharpe', 'Holdout Sharpe'), ('holdout_CAGR', 'Holdout CAGR'), ('holdout_Maximum Drawdown', 'Holdout Max DD')], {'holdout_CAGR', 'holdout_Maximum Drawdown'})}

## Feature and risk-control ablation

{_table(result.ablation, [('feature_set', 'Feature/risk variant'), ('development_sharpe', 'Dev Sharpe'), ('holdout_sharpe', 'Holdout Sharpe'), ('holdout_cagr', 'Holdout CAGR'), ('holdout_max_drawdown', 'Holdout Max DD')], {'holdout_cagr', 'holdout_max_drawdown'})}

## Subperiods

{_table(result.subperiods, [('period', 'Period'), ('strategy', 'Strategy'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Turnover', 'Turnover')], {'CAGR', 'Maximum Drawdown', 'Turnover'})}
""", encoding="utf-8")

    importance_candidates = [champion.name]
    if champion.model == "ensemble":
        importance_candidates = [
            f"elastic_net__{champion.target}",
            f"gradient_boosting__{champion.target}",
        ]
    holdout_importance = result.feature_importance[
        (result.feature_importance.split == "holdout")
        & (result.feature_importance.candidate.isin(importance_candidates))
    ].copy()
    holdout_importance = holdout_importance.groupby("feature", as_index=False).importance.mean()
    importance_total = holdout_importance.importance.sum()
    holdout_importance["normalized_importance"] = (
        holdout_importance.importance / importance_total if importance_total > 0 else np.nan
    )
    holdout_importance = holdout_importance.sort_values("normalized_importance", ascending=False).head(25)
    (output_dir / "feature_importance.md").write_text(
        f"""# Champion feature importance

Importance is taken from the model fitted on pre-holdout data. Coefficient magnitudes and tree split importance are descriptive, not causal.

{_table(holdout_importance, [('feature', 'Feature'), ('normalized_importance', 'Normalized importance')])}
""", encoding="utf-8")

    failure = []
    if not improves:
        failure.append("the development-selected ML score did not deliver a statistically supported holdout Sharpe/CAGR improvement over pure momentum")
    if not survives:
        failure.append("the champion did not retain both positive holdout Sharpe and CAGR")
    if champion_holdout.Turnover > baseline_holdout.Turnover:
        failure.append("turnover was higher than the pure-momentum reference")
    failure_text = "; ".join(failure) if failure else "no material failure under the predeclared criteria"
    (output_dir / "final_recommendation.md").write_text(
        f"""# Final recommendation

1. **Does ML improve cross-sectional momentum?** {'Yes' if improves else 'No, not under the locked economic-value criterion.'}
2. **Does it survive the locked holdout?** {'Yes' if survives else 'No.'}
3. **Best target selected on development:** {champion.target}.
4. **Best model selected on development:** {champion.model}.
5. **Does it beat pure momentum after 25 bps?** {'Yes' if improves else 'No robust improvement.'}
6. **Suitable for paper trading?** {'Yes, as a frozen monitored experiment.' if suitable else 'No.'}
7. **What failed?** {failure_text}.

## Statistical controls

- Champion holdout Sharpe CI: {result.statistics['champion_holdout_sharpe_ci']}.
- Pure momentum holdout Sharpe CI: {result.statistics['baseline_holdout_sharpe_ci']}.
- Paired Sharpe delta CI: {paired}.
- Deflated-Sharpe probability: {result.statistics['deflated_sharpe_probability']:.2%}.
- Approximate probability of backtest overfitting: {result.statistics['probability_backtest_overfitting']:.2%}.
- Tested configurations: {result.statistics['tested_configurations']}.

The recommendation is based on the locked champion, not the best holdout cell in the robustness grid.
""", encoding="utf-8")

    payload = {
        "protocol": result.protocol,
        "data": result.dataset.metadata,
        "champion": asdict(champion),
        "metrics": result.metrics.to_dict("records"),
        "robustness": result.robustness.to_dict("records"),
        "ablation": result.ablation.to_dict("records"),
        "subperiods": result.subperiods.to_dict("records"),
        "statistics": result.statistics,
        "conclusion": {
            "ml_improves": bool(improves), "survives_holdout": bool(survives),
            "paper_trading": bool(suitable), "failure": failure_text,
        },
    }
    (output_dir / "results.json").write_text(json.dumps(_plain(payload), indent=2), encoding="utf-8")
    result.metrics.to_csv(output_dir / "model_metrics.csv", index=False)
    result.robustness.to_json(output_dir / "robustness.json", orient="records", indent=2)
    result.ablation.to_csv(output_dir / "ablation.csv", index=False)
    result.subperiods.to_csv(output_dir / "subperiods.csv", index=False)
    result.scores.to_csv(output_dir / "walk_forward_scores.csv", index=False)
    selection = result.selection_history.copy()
    selection["parameters"] = selection.parameters.map(json.dumps)
    selection.to_csv(output_dir / "cpcv_selection.csv", index=False)
    result.feature_importance.to_csv(output_dir / "feature_importance.csv", index=False)
    result.primary_returns.to_csv(output_dir / "primary_returns.csv", index_label="date")


def main() -> None:
    parser = argparse.ArgumentParser(description="ML-enhanced cross-sectional crypto momentum study")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--funding-data", default="data/binance_funding_daily.csv")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--output-dir", default="reports/cross_sectional_momentum")
    parser.add_argument(
        "--reports-only",
        action="store_true",
        help="Regenerate portfolios/reports from saved walk-forward model artifacts without refitting models",
    )
    args = parser.parse_args()

    panel = _merge_funding(DataIngestion().load_csv(args.data), args.funding_data)
    volatility_probability = _load_volatility_probability(args.volatility_predictions)
    print("building primary point-in-time top-30 cross-sectional dataset", flush=True)
    dataset = build_momentum_dataset(panel, 30, volatility_probability)
    candidates = primary_candidates("all_features")
    output_dir = Path(args.output_dir)
    if args.reports_only:
        required = [
            "walk_forward_scores.csv", "cpcv_selection.csv", "feature_importance.csv",
            "robustness.json", "ablation.csv", "subperiods.csv", "results.json",
        ]
        missing = [name for name in required if not (output_dir / name).exists()]
        if missing:
            raise FileNotFoundError(f"Missing saved artifacts for --reports-only: {missing}")
        scores = pd.read_csv(output_dir / "walk_forward_scores.csv", parse_dates=["date", "label_end"])
        selection = pd.read_csv(
            output_dir / "cpcv_selection.csv",
            parse_dates=["refit_date", "test_end", "max_train_label_end"],
        )
        selection["parameters"] = selection.parameters.map(json.loads)
        importance = pd.read_csv(output_dir / "feature_importance.csv", parse_dates=["refit_date"])
        common_start = max(
            scores.loc[(scores.candidate != "pure_momentum") & (scores.split == "development")]
            .groupby("candidate").date.min()
        )
        primary_metrics, development_returns, primary_results = _run_primary(
            dataset, scores, candidates, common_start
        )
        development_model_rows = primary_metrics[
            (primary_metrics.split == "development") & (primary_metrics.category == "model")
        ]
        champion_name = development_model_rows.sort_values(["Sharpe", "CAGR"], ascending=False).iloc[0]["name"]
        champion = next(candidate for candidate in candidates if candidate.name == champion_name)
        extra_rows = []
        baseline_scores = _score_for(scores, "pure_momentum")
        for cost in COST_LEVELS:
            for top_k in (3, 5, 10):
                portfolio = scores_to_portfolio(dataset, baseline_scores, top_k=top_k, cost_bps=cost)
                name = f"pure_momentum_top{top_k}"
                extra_rows.extend([
                    _metric_row(name, None, "development", portfolio, common_start, "2024-12-31", cost, "baseline"),
                    _metric_row(name, None, "holdout", portfolio, "2025-01-01", "2026-06-22", cost, "baseline"),
                ])
            for benchmark in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top30"):
                portfolio = benchmark_portfolio(dataset, benchmark, common_start, HOLDOUT_END, cost)
                extra_rows.extend([
                    _metric_row(benchmark, None, "development", portfolio, common_start, "2024-12-31", cost, "benchmark"),
                    _metric_row(benchmark, None, "holdout", portfolio, "2025-01-01", "2026-06-22", cost, "benchmark"),
                ])
            if cost != 25:
                portfolio = scores_to_portfolio(
                    dataset, _score_for(scores, champion.name), top_k=5, cost_bps=cost
                )
                extra_rows.extend([
                    _metric_row(champion.name, champion, "development", portfolio, common_start, "2024-12-31", cost, "model"),
                    _metric_row(champion.name, champion, "holdout", portfolio, "2025-01-01", "2026-06-22", cost, "model"),
                ])
        stored = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        result = MomentumStudyResult(
            dataset=dataset,
            scores=scores,
            selection_history=selection,
            feature_importance=importance,
            metrics=pd.concat([primary_metrics, pd.DataFrame(extra_rows)], ignore_index=True),
            primary_returns=development_returns,
            champion=champion,
            robustness=pd.read_json(output_dir / "robustness.json"),
            ablation=pd.read_csv(output_dir / "ablation.csv"),
            subperiods=pd.read_csv(output_dir / "subperiods.csv"),
            statistics=stored["statistics"],
            protocol=stored["protocol"],
        )
        _write_reports(output_dir, result)
        print(f"regenerated reports from saved predictions in {output_dir}", flush=True)
        return
    print(f"running {len(candidates)} primary walk-forward candidates", flush=True)
    model_scores, selection, importance, final_params = walk_forward_candidate_scores(dataset, candidates)
    baseline_scores = momentum_baseline_scores(dataset)
    scores = pd.concat([baseline_scores, model_scores], ignore_index=True)
    common_start = max(
        scores.loc[(scores.candidate != "pure_momentum") & (scores.split == "development")].groupby("candidate").date.min()
    )
    primary_metrics, development_returns, primary_results = _run_primary(dataset, scores, candidates, common_start)
    development_model_rows = primary_metrics[
        (primary_metrics.split == "development") & (primary_metrics.category == "model")
    ]
    champion_name = development_model_rows.sort_values(["Sharpe", "CAGR"], ascending=False).iloc[0]["name"]
    champion = next(candidate for candidate in candidates if candidate.name == champion_name)
    print(f"development-locked champion: {champion.name}", flush=True)

    # Requested baseline portfolios and cost sensitivity.
    extra_rows = []
    for cost in COST_LEVELS:
        for top_k in (3, 5, 10):
            result_ = scores_to_portfolio(dataset, baseline_scores, top_k=top_k, cost_bps=cost)
            name = f"pure_momentum_top{top_k}"
            extra_rows.extend([
                _metric_row(name, None, "development", result_, common_start, "2024-12-31", cost, "baseline"),
                _metric_row(name, None, "holdout", result_, "2025-01-01", "2026-06-22", cost, "baseline"),
            ])
        for benchmark in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top30"):
            result_ = benchmark_portfolio(dataset, benchmark, common_start, HOLDOUT_END, cost)
            extra_rows.extend([
                _metric_row(benchmark, None, "development", result_, common_start, "2024-12-31", cost, "benchmark"),
                _metric_row(benchmark, None, "holdout", result_, "2025-01-01", "2026-06-22", cost, "benchmark"),
            ])
        champion_result = scores_to_portfolio(dataset, _score_for(scores, champion.name), top_k=5, cost_bps=cost)
        if cost != 25:
            extra_rows.extend([
                _metric_row(champion.name, champion, "development", champion_result, common_start, "2024-12-31", cost, "model"),
                _metric_row(champion.name, champion, "holdout", champion_result, "2025-01-01", "2026-06-22", cost, "model"),
            ])
    metrics = pd.concat([primary_metrics, pd.DataFrame(extra_rows)], ignore_index=True)

    # Robustness: reuse the locked champion form; non-primary universes refit without holdout selection.
    robustness_rows = []
    universe_scores = {30: (dataset, _score_for(scores, champion.name))}
    dependencies = _candidate_dependencies(champion)
    fixed = {name: params for name, params in final_params.items() if name in {item.name for item in dependencies}}
    for universe_n in (10, 20, 50):
        print(f"robustness universe top {universe_n}", flush=True)
        robust_dataset = build_momentum_dataset(panel, universe_n, volatility_probability)
        robust_scores, _, _, _ = walk_forward_candidate_scores(
            robust_dataset, dependencies, fixed_parameters=fixed
        )
        universe_scores[universe_n] = (robust_dataset, _score_for(robust_scores, dependencies[-1].name))
    for universe_n, (robust_dataset, robust_score) in universe_scores.items():
        robustness_rows.extend(_robustness_for_scores(robust_dataset, robust_score, universe_n, champion.name))

    # Feature ablation on the primary universe, plus weighting/risk controls.
    ablation_rows = []
    for feature_set in dataset.feature_sets:
        print(f"feature ablation: {feature_set}", flush=True)
        ablation_dependencies = _candidate_dependencies(champion, feature_set)
        ablation_scores, _, _, _ = walk_forward_candidate_scores(dataset, ablation_dependencies)
        selected_name = ablation_dependencies[-1].name
        portfolio = scores_to_portfolio(dataset, _score_for(ablation_scores, selected_name), top_k=5, cost_bps=25)
        dev = period_metrics(portfolio, common_start, "2024-12-31")
        hold = period_metrics(portfolio, "2025-01-01", "2026-06-22")
        ablation_rows.append({
            "feature_set": feature_set, "development_sharpe": dev["Sharpe"],
            "holdout_sharpe": hold["Sharpe"], "holdout_cagr": hold["CAGR"],
            "holdout_max_drawdown": hold["Maximum Drawdown"],
        })
    champion_scores = _score_for(scores, champion.name)
    for name, options in {
        "volatility_scaled_weights": {"weighting": "volatility_scaled"},
        "volatility_targeting": {"volatility_targeting": True},
        "drawdown_brake": {"drawdown_brake": True},
        "vol_target_and_brake": {"volatility_targeting": True, "drawdown_brake": True},
    }.items():
        portfolio = scores_to_portfolio(dataset, champion_scores, top_k=5, cost_bps=25, **options)
        dev, hold = period_metrics(portfolio, common_start, "2024-12-31"), period_metrics(portfolio, "2025-01-01", "2026-06-22")
        ablation_rows.append({
            "feature_set": name, "development_sharpe": dev["Sharpe"],
            "holdout_sharpe": hold["Sharpe"], "holdout_cagr": hold["CAGR"],
            "holdout_max_drawdown": hold["Maximum Drawdown"],
        })
    ablation = pd.DataFrame(ablation_rows)

    champion_primary = primary_results[champion.name]
    baseline_primary = primary_results["pure_momentum"]
    subperiod_rows = []
    for period, (start, end) in SUBPERIODS.items():
        for strategy, portfolio in (("pure_momentum", baseline_primary), (champion.name, champion_primary)):
            subperiod_rows.append({"period": period, "strategy": strategy, **period_metrics(portfolio, start, end)})
    subperiods = pd.DataFrame(subperiod_rows)

    holdout_champion_returns = champion_primary.returns.loc["2025-01-01":"2026-06-22"]
    holdout_baseline_returns = baseline_primary.returns.loc["2025-01-01":"2026-06-22"]
    tested_configurations = len(candidates) + len(robustness_rows) + len(ablation_rows) + 3
    statistics = {
        "champion_holdout_sharpe_ci": block_bootstrap_sharpe_ci(holdout_champion_returns),
        "baseline_holdout_sharpe_ci": block_bootstrap_sharpe_ci(holdout_baseline_returns),
        "paired_holdout_sharpe_delta_ci": paired_sharpe_delta_ci(holdout_baseline_returns, holdout_champion_returns),
        "deflated_sharpe_probability": deflated_sharpe_probability(holdout_champion_returns, tested_configurations),
        "probability_backtest_overfitting": probability_backtest_overfitting(development_returns),
        "tested_configurations": tested_configurations,
    }
    protocol = {
        "primary_universe": 30, "primary_top_k": 5, "primary_cost_bps": 25,
        "rebalance": "weekly", "model_refit": "quarterly", "cpcv_tuning": "yearly inside training window",
        "holdout_start": "2025-01-01", "holdout_end": "2026-06-22",
        "holdout_selection": False, "max_asset_weight": 0.20, "turnover_cap": 0.75,
    }
    result = MomentumStudyResult(
        dataset, scores, selection, importance, metrics, development_returns,
        champion, pd.DataFrame(robustness_rows), ablation, subperiods, statistics, protocol,
    )
    _write_reports(output_dir, result)
    print(metrics[(metrics.split == "holdout") & (metrics.cost_bps == 25)].sort_values("Sharpe", ascending=False).head(20).to_string(index=False), flush=True)
    print(f"wrote cross-sectional momentum study to {output_dir}", flush=True)


if __name__ == "__main__":
    main()
