"""Run public crypto-native data discovery and feature research.

This runner deliberately stops before executing a new strategy.  The mandatory
feature research phase must classify predictors before any liquidity-conditioned
strategy is allowed to run.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.crypto_mlsystem.data import DataIngestion
from src.crypto_mlsystem.feature_research import run_feature_research
from src.crypto_mlsystem.public_crypto_data import (
    download_public_crypto_data,
    load_processed_public_data,
    write_public_crypto_reports,
)


def _load_volatility_probability(path: str | Path) -> pd.Series | None:
    path = Path(path)
    if not path.exists():
        return None
    predictions = pd.read_csv(path, parse_dates=["date"])
    selected = predictions[
        (predictions.model == "elastic_net") & (predictions.feature_set == "price_only")
    ]
    if selected.empty or selected.duplicated("date").any():
        return None
    return selected.set_index("date").probability.astype(float).sort_index()


def main() -> None:
    parser = argparse.ArgumentParser(description="Public crypto-native data and feature research phase")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--raw-dir", default="data/raw/public_crypto")
    parser.add_argument("--processed-dir", default="data/processed/public_crypto")
    parser.add_argument("--reports-dir", default="reports/public_crypto_data")
    parser.add_argument("--feature-reports-dir", default="reports/feature_research")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--token-unlocks-csv", default=None)
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--end", default="2026-06-22")
    parser.add_argument("--refresh-data", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if args.refresh_data:
        print("downloading public crypto-native datasets", flush=True)
        public_data = download_public_crypto_data(
            raw_dir=args.raw_dir,
            processed_dir=args.processed_dir,
            start=args.start,
            end=args.end,
            token_unlocks_csv=args.token_unlocks_csv,
        )
    else:
        print("loading existing processed public crypto-native datasets", flush=True)
        public_data = load_processed_public_data(args.processed_dir)

    print("writing public crypto data reports", flush=True)
    write_public_crypto_reports(args.reports_dir, public_data, strategy_result={
        "available": False,
        "reason": "strategy intentionally deferred until feature research tiers are reviewed",
    })

    print("running feature research and engineering phase", flush=True)
    panel = DataIngestion().load_csv(args.data)
    probability = _load_volatility_probability(args.volatility_predictions)
    result = run_feature_research(
        panel,
        public_data=public_data,
        volatility_probability=probability,
        output_dir=args.feature_reports_dir,
    )
    tier_counts = result.tiers.feature_tier.value_counts().to_dict()
    tier1 = result.tiers[result.tiers.feature_tier == "Tier 1"].feature.tolist()
    blocked = [
        feature for feature in (
            "market_drawdown",
            "distance_to_200dma",
            "trend_4h_7d",
            "drawdown_4h_30d",
            "stablecoin_supply_change_30d",
        )
        if feature in set(result.tiers[result.tiers.feature_tier == "Tier 3"].feature)
    ]
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "strategy_results.md").write_text(
        "# Stablecoin and market-liquidity conditioned strategy results\n\n"
        "The strategy was **not run**.\n\n"
        "Reason: the mandatory feature research phase completed first, and the originally "
        "specified strategy uses features that are currently classified as Tier 3. The "
        "new rule says Tier 3 features must not be used in subsequent strategy design.\n\n"
        "## Tier gate decision\n\n"
        "Tier 1 features that can motivate a future redesigned public-data strategy:\n\n"
        + "\n".join(f"- `{feature}`" for feature in tier1)
        + "\n\nFeatures in the requested rule that cannot be used as written:\n\n"
        + ("\n".join(f"- `{feature}`: Tier 3" for feature in blocked) if blocked else "- None")
        + "\n\nPublic data integration and feature research are complete. Strategy execution is "
        "blocked until a new candidate is specified using Tier 1 features as its economic "
        "motivation and excluding Tier 3 inputs.\n\nNo trading strategy was run and no data was fabricated.\n",
        encoding="utf-8",
    )
    print(
        "feature research complete: "
        f"{tier_counts.get('Tier 1', 0)} Tier 1, "
        f"{tier_counts.get('Tier 2', 0)} Tier 2, "
        f"{tier_counts.get('Tier 3', 0)} Tier 3 features",
        flush=True,
    )
    print("strategy execution deferred; no new trading strategy was run", flush=True)


if __name__ == "__main__":
    main()
