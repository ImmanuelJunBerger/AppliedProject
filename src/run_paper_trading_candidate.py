"""Execute the predeclared defensive-momentum paper-trading study."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.crypto_mlsystem.cross_sectional_momentum import COST_LEVELS, HOLDOUT_END, HOLDOUT_START, build_momentum_dataset
from src.crypto_mlsystem.data import DataIngestion
from src.crypto_mlsystem.paper_trading_candidate import (
    DefensiveCandidate,
    backtest_weights,
    benchmark_weights,
    candidate_weights,
    cpcv_candidate_selection,
    paper_trading_acceptance,
    period_metrics,
    predeclared_candidates,
)


DEVELOPMENT_START = pd.Timestamp("2020-01-01")
DEVELOPMENT_END = pd.Timestamp("2024-12-31")


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


def _metric_row(name: str, category: str, split: str, cost: int, metrics: dict[str, float]) -> dict[str, Any]:
    return {"name": name, "category": category, "split": split, "cost_bps": cost, **metrics}


def _write_reports(
    output: Path,
    primary_dataset,
    candidates: list[DefensiveCandidate],
    selection: pd.DataFrame,
    folds: pd.DataFrame,
    family_winners: dict[str, str],
    primary_name: str,
    metrics: pd.DataFrame,
    acceptance: pd.DataFrame,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    candidate_by_name = {candidate.name: candidate for candidate in candidates}
    finalists = list(family_winners.values())
    development = metrics[
        (metrics.split == "development") & (metrics.cost_bps == 25)
        & (metrics.name.isin(finalists + ["btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top10"]))
    ].sort_values("Sharpe", ascending=False)
    holdout = metrics[
        (metrics.split == "holdout") & (metrics.cost_bps == 25)
        & (metrics.name.isin(finalists + ["btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top10"]))
    ].sort_values("Sharpe", ascending=False)
    cost_view = metrics[
        (metrics.split == "holdout") & (metrics.name.isin(finalists))
    ].sort_values(["name", "cost_bps"])
    primary_acceptance = acceptance[acceptance.name == primary_name].iloc[0]
    if primary_acceptance.passes:
        decision = "1. Recommend one strategy for paper trading."
        recommendation = f"Use **{primary_name}** as the frozen paper-trading candidate."
    elif (
        primary_acceptance.holdout_sharpe > 0
        and primary_acceptance.holdout_cagr > 0
        and primary_acceptance.annual_turnover <= 12
    ):
        decision = "2. Recommend paper trading only as monitoring with no capital."
        recommendation = "The primary candidate is directionally viable but does not clear every risk criterion."
    else:
        decision = "3. Recommend stopping because no preselected candidate passes the criteria."
        recommendation = "Do not paper trade these rules; return to research only with a new predeclared hypothesis."

    columns = [
        ("name", "Strategy"), ("CAGR", "CAGR"), ("Sharpe", "Sharpe"),
        ("Sortino", "Sortino"), ("Maximum Drawdown", "Max DD"),
        ("Calmar", "Calmar"), ("Annual Turnover", "Annual turnover"),
        ("Exposure", "Exposure"), ("Cash Allocation", "Cash"),
        ("Worst Month", "Worst month"),
    ]
    percent = {"CAGR", "Maximum Drawdown", "Exposure", "Cash Allocation", "Worst Month"}
    metadata = primary_dataset.metadata
    (output / "results_summary.md").write_text(f"""# Defensive momentum paper-trading candidates

## Locked protocol

- Data: Binance daily spot data, {metadata['start']} to {metadata['end']}.
- Universe: point-in-time top 30 for momentum and top 10 for the market-breadth gate.
- Selection sample: 2020-01-01 through 2024-12-31 only.
- Locked holdout: 2025-01-01 through 2026-06-22.
- Candidate selection: median Sharpe across development-only CPCV folds; worst-fold Sharpe and then lower turnover break ties.
- Primary candidate frozen before holdout: **{primary_name}**.
- Candidate configurations tested: {len(candidates)}.
- No holdout result was used to select a rule, threshold, family winner, or primary candidate.

## Development results

{_table(development, columns, percent)}

## Locked holdout results

{_table(holdout, columns, percent)}

## Decision

**{decision}** {recommendation}
""", encoding="utf-8")

    (output / "candidate_selection.md").write_text(f"""# Development-only candidate selection

The grid below was declared in code before evaluation. CPCV uses five chronological groups with two held-out groups per path, one-week label purging, and one-week embargo. Only development returns enter the ranking.

Rule families are fixed as follows:

- A requires BTC above its lagged 200-day average, positive BTC 30-day momentum, top-10 breadth above 50%, acceptable market drawdown, and volatility probability below its declared gate; otherwise it holds cash.
- B selects only BTC or ETH when lagged 30/90-day trends and drawdown are acceptable, then volatility-scales the selected asset.
- C holds the top momentum assets at 0%, 50%, or 100% confidence exposure before volatility targeting and the declared drawdown brake.
- D trades only BTC/ETH on biweekly or four-week intervals. The volatility forecast is used as a continuous sizing multiplier only; no forecast threshold filters trades.

Family winners:

{chr(10).join(f'- **{family}:** {name}' for family, name in family_winners.items())}

Overall primary candidate: **{primary_name}**.

{_table(selection.sort_values(['family', 'median_fold_sharpe'], ascending=[True, False]), [
    ('candidate', 'Candidate'), ('family', 'Family'), ('median_fold_sharpe', 'Median CPCV Sharpe'),
    ('worst_fold_sharpe', 'Worst fold'), ('positive_fold_fraction', 'Positive folds'),
    ('development_sharpe', 'Development Sharpe'), ('development_cagr', 'Development CAGR'),
    ('development_max_drawdown', 'Development max DD'), ('development_exposure', 'Exposure'),
    ('family_winner', 'Family winner'), ('primary_candidate', 'Primary'),
], {'positive_fold_fraction', 'development_cagr', 'development_max_drawdown', 'development_exposure'})}
""", encoding="utf-8")

    acceptance_view = acceptance.copy()
    (output / "holdout_results.md").write_text(f"""# Locked holdout evaluation

Acceptance requires all of the following: Sharpe above 0.5, positive CAGR, max drawdown better than BTC buy-and-hold, positive Sharpe and CAGR at 50 bps, and annual turnover no higher than 12x.

## Finalists and benchmarks at 25 bps

{_table(holdout, columns, percent)}

## Cost sensitivity of development-selected family winners

{_table(cost_view, [('name', 'Strategy'), ('cost_bps', 'Cost bps'), ('CAGR', 'CAGR'), ('Sharpe', 'Sharpe'), ('Maximum Drawdown', 'Max DD'), ('Annual Turnover', 'Annual turnover'), ('Exposure', 'Exposure')], {'CAGR', 'Maximum Drawdown', 'Exposure'})}

## Acceptance decisions

{_table(acceptance_view, [('name', 'Candidate'), ('primary', 'Primary'), ('holdout_sharpe', 'Sharpe'), ('holdout_cagr', 'CAGR'), ('holdout_max_drawdown', 'Max DD'), ('annual_turnover', 'Annual turnover'), ('passes', 'Passes'), ('failures', 'Failures')], {'holdout_cagr', 'holdout_max_drawdown'})}
""", encoding="utf-8")

    primary_spec = candidate_by_name[primary_name]
    (output / "final_recommendation.md").write_text(f"""# Final recommendation

**{decision}**

{recommendation}

The primary rule was selected before opening the holdout:

- Strategy: **{primary_name}**
- Family: {primary_spec.family}
- Parameters: `{json.dumps(asdict(primary_spec), sort_keys=True)}`
- For family D, only `rebalance_weeks` and `volatility_target` are grid parameters; volatility probability is a fixed continuous sizing input.
- Holdout Sharpe: {primary_acceptance.holdout_sharpe:.3f}
- Holdout CAGR: {primary_acceptance.holdout_cagr:.2%}
- Holdout max drawdown: {primary_acceptance.holdout_max_drawdown:.2%}
- Holdout annual turnover: {primary_acceptance.annual_turnover:.2f}x
- Acceptance failures: {primary_acceptance.failures or 'None'}

No alternative is promoted because it happened to look better in the locked holdout.
""", encoding="utf-8")

    selection.to_csv(output / "candidate_selection.csv", index=False)
    folds.to_csv(output / "cpcv_folds.csv", index=False)
    metrics.to_csv(output / "metrics.csv", index=False)
    acceptance.to_csv(output / "acceptance.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Predeclared defensive momentum paper-trading study")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--funding-data", default="data/binance_funding_daily.csv")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--output-dir", default="reports/paper_trading_candidate")
    args = parser.parse_args()

    panel = _merge_funding(DataIngestion().load_csv(args.data), args.funding_data)
    probability = _load_volatility_probability(args.volatility_predictions)
    print("building point-in-time top-30 and top-10 datasets", flush=True)
    primary = build_momentum_dataset(panel, 30, probability)
    top10 = build_momentum_dataset(panel, 10, probability)
    candidates = predeclared_candidates()
    print(f"backtesting {len(candidates)} predeclared candidates", flush=True)
    candidate_weight_map = {
        candidate.name: candidate_weights(primary, top10, candidate) for candidate in candidates
    }
    results_25 = {
        candidate.name: backtest_weights(
            primary, candidate_weight_map[candidate.name], 25,
            drawdown_brake=candidate.drawdown_brake,
        )
        for candidate in candidates
    }
    selection, folds, family_winners, primary_name = cpcv_candidate_selection(
        candidates, results_25, DEVELOPMENT_START
    )
    print(f"development-locked primary candidate: {primary_name}", flush=True)

    finalists = list(family_winners.values())
    candidate_by_name = {candidate.name: candidate for candidate in candidates}
    results_by_cost: dict[tuple[str, int], Any] = {}
    metric_rows: list[dict[str, Any]] = []
    for name in finalists:
        candidate = candidate_by_name[name]
        for cost in COST_LEVELS:
            result = results_25[name] if cost == 25 else backtest_weights(
                primary, candidate_weight_map[name], cost, drawdown_brake=candidate.drawdown_brake
            )
            results_by_cost[(name, cost)] = result
            metric_rows.extend([
                _metric_row(name, "candidate", "development", cost, period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)),
                _metric_row(name, "candidate", "holdout", cost, period_metrics(result, HOLDOUT_START, HOLDOUT_END)),
            ])

    benchmark_results: dict[tuple[str, int], Any] = {}
    for name in ("btc_buy_hold", "eth_buy_hold", "btc_eth_50_50", "equal_weight_top10"):
        dataset = top10 if name == "equal_weight_top10" else primary
        weights = benchmark_weights(dataset, name)
        for cost in COST_LEVELS:
            result = backtest_weights(dataset, weights, cost, turnover_cap=1.0)
            benchmark_results[(name, cost)] = result
            metric_rows.extend([
                _metric_row(name, "benchmark", "development", cost, period_metrics(result, DEVELOPMENT_START, DEVELOPMENT_END)),
                _metric_row(name, "benchmark", "holdout", cost, period_metrics(result, HOLDOUT_START, HOLDOUT_END)),
            ])
    metrics = pd.DataFrame(metric_rows)

    btc_holdout = period_metrics(benchmark_results[("btc_buy_hold", 25)], HOLDOUT_START, HOLDOUT_END)
    acceptance_rows = []
    for name in finalists:
        holdout_25 = period_metrics(results_by_cost[(name, 25)], HOLDOUT_START, HOLDOUT_END)
        holdout_50 = period_metrics(results_by_cost[(name, 50)], HOLDOUT_START, HOLDOUT_END)
        passes, failures = paper_trading_acceptance(holdout_25, holdout_50, btc_holdout)
        acceptance_rows.append({
            "name": name, "family": candidate_by_name[name].family, "primary": name == primary_name,
            "holdout_sharpe": holdout_25["Sharpe"], "holdout_cagr": holdout_25["CAGR"],
            "holdout_max_drawdown": holdout_25["Maximum Drawdown"],
            "annual_turnover": holdout_25["Annual Turnover"], "passes": passes,
            "failures": "; ".join(failures),
        })
    acceptance = pd.DataFrame(acceptance_rows)
    output = Path(args.output_dir)
    _write_reports(
        output, primary, candidates, selection, folds, family_winners,
        primary_name, metrics, acceptance,
    )
    print(acceptance.to_string(index=False), flush=True)
    print(f"wrote reports to {output}", flush=True)


if __name__ == "__main__":
    main()
