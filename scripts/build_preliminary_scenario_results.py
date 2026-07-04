#!/usr/bin/env python3
"""Build preliminary RateWall scenario-result diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.preliminary_scenario_results import (
    preliminary_scenario_result_rows_from_directory,
    write_preliminary_scenario_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite-dir",
        default=None,
        help="TDCSim/CBO suite directory; defaults to RateWall's configured suite.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/frbus_structural",
        help="Directory for local preliminary CSV/SVG/Markdown outputs.",
    )
    args = parser.parse_args()

    rows = (
        preliminary_scenario_result_rows_from_directory(args.suite_dir)
        if args.suite_dir
        else preliminary_scenario_result_rows_from_directory()
    )
    outputs = write_preliminary_scenario_outputs(Path(args.output_dir), rows=rows)
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
