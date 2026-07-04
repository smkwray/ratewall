#!/usr/bin/env python3
"""Build D1 deposit payer-flow source panel artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.deposit_payer_flow_source_panel import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RAW_DIR,
    write_deposit_payer_flow_source_outputs,
    write_fail_closed_acquisition_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Raw source directory with FFIEC/FDIC and NCUA panel inputs.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for D1 payer-flow source panel outputs.",
    )
    parser.add_argument(
        "--requested-period-id",
        action="append",
        default=None,
        help="Required common quarter, e.g. 2024Q2. May be repeated.",
    )
    args = parser.parse_args()

    fail_closed = write_fail_closed_acquisition_artifacts(raw_dir=Path(args.raw_dir))
    outputs = write_deposit_payer_flow_source_outputs(
        Path(args.output_dir),
        raw_dir=Path(args.raw_dir),
        requested_period_ids=args.requested_period_id,
    )
    for name, path in {**fail_closed, **outputs}.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
