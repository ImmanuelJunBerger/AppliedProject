"""CLI entrypoint for the advanced alpha research roadmap."""
from __future__ import annotations

import argparse
from pathlib import Path

from crypto_mlsystem.advanced_alpha_roadmap import run_default_advanced_alpha_roadmap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write the advanced alpha research roadmap report pack.")
    parser.add_argument(
        "--output-dir",
        default="reports/advanced_alpha_research_roadmap",
        help="Output report directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_default_advanced_alpha_roadmap(args.output_dir)
    print(f"Advanced alpha roadmap reports written to {Path(args.output_dir)}")


if __name__ == "__main__":
    main()
