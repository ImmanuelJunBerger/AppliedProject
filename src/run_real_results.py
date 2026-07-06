from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.crypto_mlsystem.backtest import apply_allocations, benchmark_returns
from src.crypto_mlsystem.config import ResearchConfig
from src.crypto_mlsystem.data import DataIngestion, UniverseBuilder
from src.crypto_mlsystem.features import build_features, make_strategy_targets
from src.crypto_mlsystem.metrics import performance_metrics
from src.crypto_mlsystem.ml import walk_forward_allocations
from src.crypto_mlsystem.risk import reasoning_layer
from src.crypto_mlsystem.strategies import strategy_return_frame


def _plain_metrics(metrics: dict) -> dict[str, float]:
    return {name: float(value) for name, value in metrics.items()}


def run_experiments(data_path: str, sizes: list[int], model: str, cost_bps: int) -> dict:
    cfg = ResearchConfig.from_yaml("configs/default.yaml")
    full_panel = DataIngestion().load_csv(data_path)
    output = {
        "source": data_path,
        "rows": int(len(full_panel)),
        "assets_downloaded": int(full_panel.symbol.nunique()),
        "start": str(full_panel.date.min().date()),
        "end": str(full_panel.date.max().date()),
        "ranking": "prior-30-day median dollar turnover, formed monthly without look-ahead",
        "model": model,
        "cost_bps": cost_bps,
        "experiments": {},
    }

    membership_rows = []
    for top_n in sizes:
        builder = UniverseBuilder(set(cfg.exclude_symbols), cfg.min_history_days)
        universes = builder.monthly_universe(full_panel, top_n)
        selected = sorted(set().union(*universes.values()))
        panel = full_panel[full_panel.symbol.isin(selected)].copy()
        strategy_returns = strategy_return_frame(panel, universes)
        features = build_features(panel, strategy_returns, universes)
        targets = make_strategy_targets(strategy_returns)
        allocations = walk_forward_allocations(
            features,
            targets,
            list(strategy_returns.columns),
            cfg.train_min_days,
            cfg.prediction_frequency,
            model,
        )
        allocations = reasoning_layer(allocations, features, cfg.strategy_limit, cfg.turnover_limit)
        result = apply_allocations(strategy_returns, allocations, cost_bps)
        benchmarks = benchmark_returns(panel, strategy_returns, universes).loc[result["returns"].index]

        nonempty = {date: members for date, members in universes.items() if members}
        previous = None
        changes = 0
        for date, members in nonempty.items():
            member_set = set(members)
            if previous is not None:
                changes += len(member_set.symmetric_difference(previous))
            previous = member_set
            for rank, symbol in enumerate(members, start=1):
                membership_rows.append({"universe_size": top_n, "effective_date": date, "rank": rank, "symbol": symbol})

        benchmark_metrics = {
            name: _plain_metrics(performance_metrics(series))
            for name, series in benchmarks.items()
        }
        latest_date = max(nonempty) if nonempty else None
        output["experiments"][str(top_n)] = {
            "evaluation_start": str(result["returns"].index.min().date()),
            "evaluation_end": str(result["returns"].index.max().date()),
            "observations": int(len(result["returns"])),
            "monthly_reconstitutions": len(nonempty),
            "unique_historical_members": len(selected),
            "membership_additions_and_removals": changes,
            "latest_membership_date": str(latest_date.date()) if latest_date else None,
            "latest_members": nonempty.get(latest_date, []) if latest_date else [],
            "strategy_metrics": _plain_metrics(result["metrics"]),
            "benchmark_metrics": benchmark_metrics,
        }

    return output, pd.DataFrame(membership_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run point-in-time top-N real-data experiments.")
    parser.add_argument("--data", required=True)
    parser.add_argument("--sizes", nargs="+", type=int, default=[20, 50])
    parser.add_argument("--model", default="logistic_regression")
    parser.add_argument("--cost-bps", type=int, default=25)
    parser.add_argument("--output", default="reports/artifacts/real_data_results.json")
    args = parser.parse_args()

    results, membership = run_experiments(args.data, args.sizes, args.model, args.cost_bps)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    membership_path = output_path.with_name("real_data_membership.csv")
    membership.to_csv(membership_path, index=False)
    print(json.dumps(results, indent=2))
    print(f"Wrote {output_path} and {membership_path}")


if __name__ == "__main__":
    main()
