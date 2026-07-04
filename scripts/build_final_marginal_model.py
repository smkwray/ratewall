#!/usr/bin/env python3
"""Build final marginal RW_M gate artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.final_marginal_model import (
    DEFAULT_DENOMINATOR_PATH,
    DEFAULT_HISTORICAL_WINDOW_PATH,
    DEFAULT_SELECTED_NUMERATOR_PATH,
    exposure_diagnostics_snapshot_rows,
    final_marginal_readiness_rows,
    final_marginal_rw_ratio_rows,
    write_final_marginal_model_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-numerator-path", default=str(DEFAULT_SELECTED_NUMERATOR_PATH))
    parser.add_argument("--denominator-path", default=str(DEFAULT_DENOMINATOR_PATH))
    parser.add_argument("--historical-window-path", default=str(DEFAULT_HISTORICAL_WINDOW_PATH))
    parser.add_argument(
        "--full-test-suite-passed",
        action="store_true",
        help="Record the runtime full-pytest readiness check as passed.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/final_marginal_model",
    )
    args = parser.parse_args()

    ratio_rows = final_marginal_rw_ratio_rows(
        selected_numerator_path=Path(args.selected_numerator_path),
        denominator_path=Path(args.denominator_path),
    )
    readiness_rows = final_marginal_readiness_rows(
        ratio_rows,
        historical_window_path=Path(args.historical_window_path),
        full_test_suite_passed=args.full_test_suite_passed,
    )
    diagnostic_rows = exposure_diagnostics_snapshot_rows()
    outputs = write_final_marginal_model_outputs(
        Path(args.output_dir),
        ratio_rows=ratio_rows,
        readiness_rows=readiness_rows,
        diagnostic_rows=diagnostic_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"ratio_rows: {len(ratio_rows)}")
    print(f"readiness_rows: {len(readiness_rows)}")
    print(f"diagnostic_rows: {len(diagnostic_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
