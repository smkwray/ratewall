#!/usr/bin/env python3
"""Build the denominator comparability bridge."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.denominator_parity import (
    DEFAULT_FORECAST_READOUT_DIR,
    denominator_parity_bridge_rows,
    denominator_scenario_delta_audit_rows,
    denominator_variant_surface_rows,
    write_denominator_parity_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--forecast-readout-dir",
        default=str(DEFAULT_FORECAST_READOUT_DIR),
        help="Directory containing forecast readout CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/denominator_parity",
        help="Directory for denominator parity outputs.",
    )
    args = parser.parse_args()

    bridge_rows = denominator_parity_bridge_rows(
        forecast_readout_dir=Path(args.forecast_readout_dir)
    )
    variant_rows = denominator_variant_surface_rows(bridge_rows)
    audit_rows = denominator_scenario_delta_audit_rows(bridge_rows)
    outputs = write_denominator_parity_outputs(
        Path(args.output_dir),
        bridge_rows=bridge_rows,
        variant_rows=variant_rows,
        audit_rows=audit_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"bridge_rows: {len(bridge_rows)}")
    print(f"variant_rows: {len(variant_rows)}")
    print(f"audit_rows: {len(audit_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
