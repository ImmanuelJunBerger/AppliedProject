"""CLI entrypoint for the trend-scanning ML study."""
from __future__ import annotations

import argparse
from pathlib import Path

from crypto_mlsystem.trend_scanning_ml import run_default_trend_scanning_ml


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run trend-scanning labels and meta-model study without modifying the frozen macro strategy.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/trend_scanning_ml",
        help="Directory where Markdown/CSV/JSON reports should be written.",
    )
    args = parser.parse_args()
    result = run_default_trend_scanning_ml(Path(args.output_dir))
    print(f"Trend-scanning ML reports written to {args.output_dir}")
    print(f"Selected development-only candidate: {result['winner']}")
    print(f"Final conclusion: {result['final_conclusion']}")


if __name__ == "__main__":
    main()
