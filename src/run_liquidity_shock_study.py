"""Run the crypto liquidity shock research study."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from crypto_mlsystem.liquidity_shock import (
    load_volatility_probability,
    run_liquidity_shock_study,
    write_liquidity_shock_reports,
)
from crypto_mlsystem.public_crypto_data import load_processed_public_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run liquidity shock crypto research.")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv", help="Daily OHLCV CSV.")
    parser.add_argument("--public-data-dir", default="data/processed/public_crypto", help="Processed public crypto data directory.")
    parser.add_argument("--output-dir", default="reports/liquidity_shock", help="Report output directory.")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv", help="Fixed volatility-expansion probability CSV.")
    args = parser.parse_args()

    print("loading daily crypto panel and processed public crypto data")
    panel = pd.read_csv(Path(args.data), parse_dates=["date"])
    public_data = load_processed_public_data(args.public_data_dir)
    volatility_probability = load_volatility_probability(args.volatility_predictions)

    print("running liquidity shock study")
    result = run_liquidity_shock_study(panel, public_data, volatility_probability)
    print(f"selected candidate: {result['winner'].name}")

    print("writing reports")
    write_liquidity_shock_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}")


if __name__ == "__main__":
    main()
