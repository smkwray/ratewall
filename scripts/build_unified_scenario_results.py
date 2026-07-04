#!/usr/bin/env python3
"""Build unified RateWall scenario diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.unified_scenario_results import (
    DEFAULT_UNIFIED_SUITE_DIR,
    apply_moving_d_beta_chi_claim_gate,
    unified_scenario_result_rows_from_directory,
    write_unified_scenario_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite-dir",
        default=str(DEFAULT_UNIFIED_SUITE_DIR),
        help="TDCSim/CBO suite directory with manifest-backed scenario outputs.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/unified",
        help="Directory for unified scenario CSV, PNG, and Markdown outputs.",
    )
    args = parser.parse_args()

    rows = unified_scenario_result_rows_from_directory(args.suite_dir)
    from ratewall.databook.beta_chi_assumption_discipline import (
        beta_chi_claim_gate_rows_from_directory,
    )

    rows = apply_moving_d_beta_chi_claim_gate(
        rows,
        beta_chi_claim_gate_rows_from_directory(args.suite_dir),
    )
    outputs = write_unified_scenario_outputs(Path(args.output_dir), rows=rows)
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
