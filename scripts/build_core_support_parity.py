#!/usr/bin/env python3
"""Build the core support numerator parity surface."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.core_support_parity import (
    DEFAULT_FORECAST_READOUT_DIR,
    core_support_numerator_rows,
    core_support_overlap_audit_rows,
    public_interest_net_block_shared_rows,
    tdc_ex_overlap_support_shared_rows,
    write_core_support_parity_outputs,
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
        default="var/preliminary_scenario_results/core_support_parity",
        help="Directory for core support parity outputs.",
    )
    args = parser.parse_args()

    public_interest_rows = public_interest_net_block_shared_rows(
        forecast_readout_dir=Path(args.forecast_readout_dir)
    )
    tdc_rows = tdc_ex_overlap_support_shared_rows(
        forecast_readout_dir=Path(args.forecast_readout_dir)
    )
    rows = core_support_numerator_rows(forecast_readout_dir=Path(args.forecast_readout_dir))
    audit_rows = core_support_overlap_audit_rows(rows)
    outputs = write_core_support_parity_outputs(
        Path(args.output_dir),
        public_interest_rows=public_interest_rows,
        tdc_rows=tdc_rows,
        rows=rows,
        audit_rows=audit_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"public_interest_rows: {len(public_interest_rows)}")
    print(f"tdc_rows: {len(tdc_rows)}")
    print(f"core_support_rows: {len(rows)}")
    print(f"overlap_audit_rows: {len(audit_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
