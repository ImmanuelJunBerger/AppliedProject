"""Execute the Tier-1 regime-gated cross-sectional momentum study."""
from __future__ import annotations

import argparse

from src.crypto_mlsystem.data import DataIngestion
from src.crypto_mlsystem.public_crypto_data import load_processed_public_data
from src.crypto_mlsystem.tier1_regime_momentum import (
    load_volatility_probability,
    run_tier1_regime_momentum_study,
    write_tier1_regime_momentum_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tier-1 regime-gated cross-sectional crypto momentum")
    parser.add_argument("--data", default="data/binance_usdt_broad_2019.csv")
    parser.add_argument("--public-data-dir", default="data/processed/public_crypto")
    parser.add_argument("--volatility-predictions", default="reports/volatility_expansion/predictions.csv")
    parser.add_argument("--output-dir", default="reports/tier1_regime_momentum")
    args = parser.parse_args()

    print("loading daily crypto panel and processed public data", flush=True)
    panel = DataIngestion().load_csv(args.data)
    public_data = load_processed_public_data(args.public_data_dir)
    probability = load_volatility_probability(args.volatility_predictions)
    print("running Tier-1 regime-gated momentum study", flush=True)
    result = run_tier1_regime_momentum_study(panel, public_data, probability)
    print(f"selected candidate: {result['winner'].name}", flush=True)
    print("writing reports", flush=True)
    write_tier1_regime_momentum_reports(args.output_dir, result)
    print(f"reports written to {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
