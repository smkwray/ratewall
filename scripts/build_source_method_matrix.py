#!/usr/bin/env python3
"""Build source/method authority artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.source_method_matrix import (
    DEFAULT_CBO_REVENUE_PATH,
    source_method_matrix_rows,
    source_method_summary_rows,
    write_source_method_matrix_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cbo-revenue-path",
        default=str(DEFAULT_CBO_REVENUE_PATH),
        help="Optional local CBO revenue workbook path.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/source_method_matrix",
        help="Directory for source/method matrix outputs.",
    )
    args = parser.parse_args()

    rows = source_method_matrix_rows(cbo_revenue_path=Path(args.cbo_revenue_path))
    summary_rows = source_method_summary_rows(rows)
    outputs = write_source_method_matrix_outputs(
        Path(args.output_dir),
        rows=rows,
        summary_rows=summary_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"matrix_rows: {len(rows)}")
    print(f"summary_rows: {len(summary_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
