"""Run the macro-regime conditioned crypto exposure study."""
from __future__ import annotations

import argparse

from src.crypto_mlsystem.data import DataIngestion
from src.crypto_mlsystem.macro_regime_strategy import (
    load_macro_features,
    load_volatility_probability,
    run_macro_regime_strategy_study,
    write_macro_regime_strategy_reports,
)
from src.crypto_mlsystem.public_crypto_data import load_processed_public_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Macro-regime conditioned crypto exposure strategy")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--macro-features", default="data/processed/wrds_macro_features/wrds_macro_features_daily.csv")
    parser.add_argument("--public-data-dir", default="data/processed/public_crypto")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--output-dir", default="reports/macro_regime_strategy")
    args = parser.parse_args()

    print("loading crypto panel", flush=True)
    panel = DataIngestion().load_csv(args.data)
    print("loading fixed WRDS macro Tier-1 features", flush=True)
    macro = load_macro_features(args.macro_features)
    print("loading existing public crypto-native features", flush=True)
    public_data = load_processed_public_data(args.public_data_dir)
    probability = load_volatility_probability(args.volatility_predictions)
    print("running macro-regime strategy study", flush=True)
    result = run_macro_regime_strategy_study(panel, macro, public_data, probability)
    print(f"selected candidate: {result['winner'].name}", flush=True)
    print("writing reports", flush=True)
    write_macro_regime_strategy_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
