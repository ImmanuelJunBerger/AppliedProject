"""Build targeted WRDS macro-regime features and run feature research only."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.crypto_mlsystem.data import DataIngestion
from src.crypto_mlsystem.wrds_macro_features import (
    DEFAULT_END,
    DEFAULT_START,
    download_wrds_macro_series,
    run_macro_feature_research,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download small WRDS macro series, create lagged features, and run feature research only."
    )
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv", help="Existing crypto daily panel.")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--no-env-file", action="store_true", help="Do not read a local .env file.")
    parser.add_argument("--processed-dir", default="data/processed/wrds_macro_features")
    parser.add_argument("--output-dir", default="reports/wrds_macro_features")
    parser.add_argument("--top-n", type=int, default=20, help="Point-in-time crypto universe size for feature research.")
    parser.add_argument(
        "--use-existing-macro",
        action="store_true",
        help="Skip WRDS download and use processed/wrds_macro_daily.csv if it exists.",
    )
    args = parser.parse_args()

    processed_dir = Path(args.processed_dir)
    macro_path = processed_dir / "wrds_macro_daily.csv"
    coverage_path = processed_dir / "coverage.csv"

    if args.use_existing_macro and macro_path.exists() and coverage_path.exists():
        print("loading existing WRDS macro series", flush=True)
        macro = pd.read_csv(macro_path, parse_dates=["date"])
        coverage = pd.read_csv(coverage_path)
    else:
        print("downloading targeted WRDS macro series", flush=True)
        macro, coverage = download_wrds_macro_series(
            start=args.start,
            end=args.end,
            env_file=None if args.no_env_file else args.env_file,
            processed_dir=processed_dir,
        )

    print("loading crypto panel", flush=True)
    panel = DataIngestion().load_csv(args.data)
    print("running WRDS macro feature research only", flush=True)
    result = run_macro_feature_research(
        crypto_panel=panel,
        macro_daily=macro,
        coverage=coverage,
        output_dir=args.output_dir,
        processed_dir=processed_dir,
        top_n=args.top_n,
    )
    tier_counts = result.tiers.feature_tier.value_counts().to_dict() if not result.tiers.empty else {}
    print(
        "WRDS macro feature research complete: "
        f"{len(result.metadata)} features, "
        f"{tier_counts.get('Tier 1', 0)} Tier 1, "
        f"{tier_counts.get('Tier 2', 0)} Tier 2, "
        f"{tier_counts.get('Tier 3', 0)} Tier 3.",
        flush=True,
    )
    print(f"Reports written to {args.output_dir}", flush=True)
    print("No trading strategy was run.", flush=True)


if __name__ == "__main__":
    main()
