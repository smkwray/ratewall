#!/usr/bin/env python3
"""Build holder-mix RateWall scenario diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.holder_scenario_results import (
    holder_scenario_result_rows_from_directory,
    write_holder_scenario_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite-dir",
        default="var/tdcsim_cbo_suite_20260626_tdcsim72dc6c7_t1_t2",
        help="TDCSim/CBO suite directory with holder scenarios.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/holder_mix",
        help="Directory for holder scenario CSV, PNG, and Markdown outputs.",
    )
    args = parser.parse_args()

    rows = holder_scenario_result_rows_from_directory(args.suite_dir)
    outputs = write_holder_scenario_outputs(Path(args.output_dir), rows=rows)
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
