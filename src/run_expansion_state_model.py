"""CLI entrypoint for crypto expansion-state detection research."""
from __future__ import annotations

import argparse
from pathlib import Path

from crypto_mlsystem.expansion_state_model import run_expansion_state_model, write_expansion_state_reports
from crypto_mlsystem.macro_regime_benchmark_analysis import load_default_inputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run expansion-state ML research around the frozen macro-regime allocation strategy."
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
        default="reports/expansion_state_model",
        help="Output report directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel, macro, public_data, probability = load_default_inputs(
        data_path=args.data,
        macro_path=args.macro_features,
        public_data_dir=args.public_data_dir,
        volatility_predictions=args.volatility_predictions,
    )
    result = run_expansion_state_model(panel, macro, public_data, probability)
    write_expansion_state_reports(args.output_dir, result)
    print(f"Expansion-state reports written to {Path(args.output_dir)}")
    print(f"Final conclusion: {result['final_conclusion']}")


if __name__ == "__main__":
    main()
