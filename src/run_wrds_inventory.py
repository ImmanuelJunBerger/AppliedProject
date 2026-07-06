"""Run WRDS data-discovery and integration planning reports."""
from __future__ import annotations

import argparse

from src.crypto_mlsystem.wrds_inventory import run_wrds_inventory_with_optional_prompt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover WRDS libraries/tables relevant to crypto research without storing credentials."
    )
    parser.add_argument("--output-dir", default="reports/wrds_inventory", help="Directory for WRDS inventory reports.")
    parser.add_argument(
        "--scan-all-tables",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="If credentials are available, list tables for all accessible libraries. Disable to scan only likely relevant libraries.",
    )
    parser.add_argument(
        "--prompt-for-credentials",
        action="store_true",
        help="Prompt for missing WRDS credentials and hold them only in this Python process.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Optional local dotenv-style credential file. Defaults to .env, which is git-ignored.",
    )
    parser.add_argument(
        "--no-env-file",
        action="store_true",
        help="Do not read a local dotenv-style credential file.",
    )
    args = parser.parse_args()

    result = run_wrds_inventory_with_optional_prompt(
        args.output_dir,
        scan_all_tables=args.scan_all_tables,
        prompt=args.prompt_for_credentials,
        env_file=None if args.no_env_file else args.env_file,
    )
    if result.status == "credentials_missing":
        print("WRDS credentials missing; wrote setup instructions and non-live inventory reports.")
    elif result.status == "wrds_package_missing":
        print("Optional wrds package missing; wrote setup instructions and non-live inventory reports.")
    elif result.status == "queried":
        print(
            f"WRDS inventory queried: {len(result.libraries)} libraries, "
            f"{len(result.table_matches)} relevant table matches."
        )
    else:
        print(f"WRDS inventory status: {result.status}. Reports were still written.")
    print(f"Reports written to {args.output_dir}")


if __name__ == "__main__":
    main()
