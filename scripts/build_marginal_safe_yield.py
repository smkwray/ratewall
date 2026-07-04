#!/usr/bin/env python3
"""Build marginal D1 safe-yield fail-closed surface."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.marginal_safe_yield import (
    DEFAULT_D1_ADMISSION_PATH,
    DEFAULT_DENOMINATOR_PATH,
    DEFAULT_FORECAST_ASSUMPTIONS_PATH,
    marginal_safe_yield_delta_rows,
    marginal_safe_yield_overlap_audit_rows,
    write_marginal_safe_yield_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--denominator-path", default=str(DEFAULT_DENOMINATOR_PATH))
    parser.add_argument("--d1-admission-path", default=str(DEFAULT_D1_ADMISSION_PATH))
    parser.add_argument("--forecast-assumptions-path", default=str(DEFAULT_FORECAST_ASSUMPTIONS_PATH))
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/marginal_safe_yield",
    )
    args = parser.parse_args()

    rows = marginal_safe_yield_delta_rows(
        denominator_path=Path(args.denominator_path),
        d1_admission_path=Path(args.d1_admission_path),
        forecast_assumptions_path=Path(args.forecast_assumptions_path),
    )
    overlap = marginal_safe_yield_overlap_audit_rows(rows)
    outputs = write_marginal_safe_yield_outputs(
        Path(args.output_dir),
        delta_rows=rows,
        overlap_rows=overlap,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"safe_yield_rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
