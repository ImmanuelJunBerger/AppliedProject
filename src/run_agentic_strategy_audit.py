"""CLI entrypoint for the FUGO-style agentic strategy audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from crypto_mlsystem.agentic_strategy_audit import run_default_agentic_strategy_audit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run agentic governance audit over completed crypto strategy reports.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/agentic_strategy_audit",
        help="Directory where audit Markdown/CSV/JSON reports should be written.",
    )
    args = parser.parse_args()
    result = run_default_agentic_strategy_audit(Path(args.output_dir))
    print(f"Agentic strategy audit reports written to {args.output_dir}")
    print(f"Selected by process reward: {result['selected_by_process_reward']}")
    print(f"Final recommendation: {result['final_recommendation']}")


if __name__ == "__main__":
    main()
