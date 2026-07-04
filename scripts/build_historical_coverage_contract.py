#!/usr/bin/env python3
"""Build T3 historical coverage and extension contract artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.historical_coverage_contract import (
    DEFAULT_HISTORICAL_PROVISIONAL_DIR,
    DEFAULT_OUTPUT_DIR,
    historical_coverage_contract_rows,
    historical_extension_feasibility_rows,
    historical_extension_readout_markdown,
    historical_numerator_panel_rows,
    historical_tdc_mechanism_panel_rows,
    write_historical_coverage_contract_outputs,
)
from ratewall.databook.historical_tdc_source_registry import (
    DEFAULT_SIBLING_CALIBRATION_DIR,
    historical_tdc_source_registry_rows,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sibling-calibration-dir",
        default=str(DEFAULT_SIBLING_CALIBRATION_DIR),
        help="Directory containing vendored sibling TDC calibration CSVs.",
    )
    parser.add_argument(
        "--historical-provisional-dir",
        default=str(DEFAULT_HISTORICAL_PROVISIONAL_DIR),
        help="Directory containing implemented historical provisional outputs.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for T3 historical coverage outputs.",
    )
    args = parser.parse_args()

    source_rows = historical_tdc_source_registry_rows(
        sibling_calibration_dir=Path(args.sibling_calibration_dir),
        historical_provisional_dir=Path(args.historical_provisional_dir),
    )
    coverage_rows = historical_coverage_contract_rows(
        source_registry_rows=source_rows,
        historical_provisional_dir=Path(args.historical_provisional_dir),
    )
    feasibility_rows = historical_extension_feasibility_rows(
        coverage_rows=coverage_rows,
        source_registry_rows=source_rows,
    )
    numerator_rows = historical_numerator_panel_rows(
        historical_provisional_dir=Path(args.historical_provisional_dir)
    )
    tdc_rows = historical_tdc_mechanism_panel_rows(
        numerator_rows=numerator_rows,
    )
    readout = historical_extension_readout_markdown(
        coverage_rows=coverage_rows,
        feasibility_rows=feasibility_rows,
    )
    outputs = write_historical_coverage_contract_outputs(
        Path(args.output_dir),
        source_registry_rows=source_rows,
        coverage_rows=coverage_rows,
        feasibility_rows=feasibility_rows,
        numerator_panel_rows=numerator_rows,
        tdc_mechanism_panel_rows=tdc_rows,
        readout_markdown=readout,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"source_registry_rows: {len(source_rows)}")
    print(f"coverage_rows: {len(coverage_rows)}")
    print(f"feasibility_rows: {len(feasibility_rows)}")
    print(f"numerator_panel_rows: {len(numerator_rows)}")
    print(f"tdc_mechanism_panel_rows: {len(tdc_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
