#!/usr/bin/env python3
"""Build historical comparable adapter artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.historical_comparable_adapter import (
    DEFAULT_HISTORICAL_CLEAN_PATH,
    DEFAULT_METHODOLOGY_PARITY_DIR,
    historical_channel_adapter_status_rows,
    historical_comparable_surface_rows,
    historical_denominator_variant_bridge_rows,
    write_historical_comparable_adapter_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--methodology-parity-dir",
        default=str(DEFAULT_METHODOLOGY_PARITY_DIR),
        help="Directory containing methodology parity CSVs.",
    )
    parser.add_argument(
        "--historical-clean-path",
        default=str(DEFAULT_HISTORICAL_CLEAN_PATH),
        help="Historical clean path CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/historical_comparable_adapter",
        help="Directory for historical comparable adapter outputs.",
    )
    args = parser.parse_args()
    methodology_dir = Path(args.methodology_parity_dir)
    historical_path = Path(args.historical_clean_path)

    status_rows = historical_channel_adapter_status_rows(
        methodology_parity_dir=methodology_dir,
        historical_clean_path=historical_path,
    )
    surface_rows = historical_comparable_surface_rows(
        methodology_parity_dir=methodology_dir,
        historical_clean_path=historical_path,
    )
    denominator_rows = historical_denominator_variant_bridge_rows(
        methodology_parity_dir=methodology_dir,
    )
    outputs = write_historical_comparable_adapter_outputs(
        Path(args.output_dir),
        status_rows=status_rows,
        surface_rows=surface_rows,
        denominator_rows=denominator_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"status_rows: {len(status_rows)}")
    print(f"surface_rows: {len(surface_rows)}")
    print(f"denominator_rows: {len(denominator_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
