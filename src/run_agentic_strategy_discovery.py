"""CLI entrypoint for agentic deterministic strategy discovery."""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

from crypto_mlsystem.agentic_strategy_discovery import (
    run_agentic_strategy_discovery,
    write_agentic_strategy_discovery_reports,
)
from crypto_mlsystem.macro_regime_benchmark_analysis import load_default_inputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic agentic strategy discovery without modifying the frozen macro strategy.",
    )
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv", help="Crypto OHLCV panel CSV.")
    parser.add_argument(
        "--macro-features",
        default="data/processed/wrds_macro_features/wrds_macro_features_daily.csv",
        help="Daily WRDS macro feature CSV.",
    )
    parser.add_argument(
        "--public-data-dir",
        default="data/processed/public_crypto",
        help="Processed public crypto-native data directory.",
    )
    parser.add_argument(
        "--volatility-predictions",
        default="reports/volatility_expansion/predictions.csv",
        help="Existing fixed volatility-expansion probability CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/agentic_strategy_discovery",
        help="Output report directory.",
    )
    return parser.parse_args()


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    args = parse_args()
    panel, macro, public_data, probability = load_default_inputs(
        data_path=args.data,
        macro_path=args.macro_features,
        public_data_dir=args.public_data_dir,
        volatility_predictions=args.volatility_predictions,
    )
    result = run_agentic_strategy_discovery(panel, macro, public_data, probability)
    write_agentic_strategy_discovery_reports(Path(args.output_dir), result)
    print(f"Agentic strategy discovery reports written to {Path(args.output_dir)}")
    print(f"Selected candidate: {result['winner'].candidate_name}")
    print(f"Final conclusion: {result['final_conclusion']}")


if __name__ == "__main__":
    main()
