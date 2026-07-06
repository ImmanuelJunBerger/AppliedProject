"""CLI entrypoint for the final new-data extension study."""
from __future__ import annotations

import argparse
from pathlib import Path

from crypto_mlsystem.new_data_extension import run_default_new_data_extension


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run new-data inventory, feature research, and strategy gate without modifying the frozen macro strategy.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/new_data_extension",
        help="Directory where new-data extension reports should be written.",
    )
    args = parser.parse_args()
    result = run_default_new_data_extension(Path(args.output_dir))
    print(f"New-data extension reports written to {args.output_dir}")
    print(f"New Data Tier-1 features: {len(result['tier1_features'])}")
    print(f"Strategy ran: {result['strategy_ran']}")
    print(f"Final conclusion: {result['final_conclusion']}")


if __name__ == "__main__":
    main()
