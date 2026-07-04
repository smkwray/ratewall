#!/usr/bin/env python3
"""Build current/forecast/historical methodology parity outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.methodology_parity import (
    DEFAULT_DENOMINATOR_CONTRACT_PATH,
    DEFAULT_FORECAST_READOUT_DIR,
    methodology_parity_channel_rows,
    methodology_parity_denominator_rows,
    methodology_parity_roadmap_rows,
    write_methodology_parity_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--forecast-readout-dir",
        default=str(DEFAULT_FORECAST_READOUT_DIR),
        help="Directory containing 10-year forecast readout CSVs.",
    )
    parser.add_argument(
        "--denominator-contract-path",
        default=str(DEFAULT_DENOMINATOR_CONTRACT_PATH),
        help="Current denominator contract CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/methodology_parity",
        help="Directory for methodology parity outputs.",
    )
    args = parser.parse_args()

    channel_rows = methodology_parity_channel_rows(
        forecast_readout_dir=Path(args.forecast_readout_dir)
    )
    denominator_rows = methodology_parity_denominator_rows(
        denominator_contract_path=Path(args.denominator_contract_path)
    )
    roadmap_rows = methodology_parity_roadmap_rows(
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
    )
    outputs = write_methodology_parity_outputs(
        Path(args.output_dir),
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
        roadmap_rows=roadmap_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"channel_rows: {len(channel_rows)}")
    print(f"denominator_rows: {len(denominator_rows)}")
    print(f"roadmap_rows: {len(roadmap_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
