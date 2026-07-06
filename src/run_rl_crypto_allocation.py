"""Run risk-aware RL crypto allocation study."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from crypto_mlsystem.public_crypto_data import load_processed_public_data
from crypto_mlsystem.rl_crypto_allocation import (
    load_volatility_probability,
    run_rl_crypto_allocation_study,
    write_rl_crypto_allocation_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run risk-aware RL crypto allocation study.")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv", help="Daily OHLCV CSV.")
    parser.add_argument("--public-data-dir", default="data/processed/public_crypto", help="Processed public crypto data directory.")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv", help="Fixed volatility-expansion predictions.")
    parser.add_argument("--output-dir", default="reports/rl_crypto_allocation", help="Report output directory.")
    args = parser.parse_args()

    print("loading daily crypto panel and processed public crypto data")
    panel = pd.read_csv(Path(args.data), parse_dates=["date"])
    public_data = load_processed_public_data(args.public_data_dir)
    volatility_probability = load_volatility_probability(args.volatility_predictions)

    print("running risk-aware RL allocation study")
    result = run_rl_crypto_allocation_study(panel, public_data, volatility_probability)
    print(f"selected RL candidate: {result['winner'].name}")

    print("writing reports")
    write_rl_crypto_allocation_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}")


if __name__ == "__main__":
    main()
