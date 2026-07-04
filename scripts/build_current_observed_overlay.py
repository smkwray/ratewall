#!/usr/bin/env python3
"""Build current benchmark and observed-overlay gate artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.current_observed_overlay import (
    DEFAULT_HOLDER_TDC_BRIDGE_PATH,
    DEFAULT_RUNTIME_TABLE_DIR,
    DEFAULT_SOURCE_METHOD_DIR,
    DEFAULT_TDC_CHANNEL_PATH,
    current_assumption_benchmark_rows,
    current_observed_overlay_admission_rows,
    current_observed_overlay_audit_rows,
    current_observed_overlay_candidate_rows,
    current_observed_overlay_map_rows,
    write_current_observed_overlay_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime-table-dir",
        default=str(DEFAULT_RUNTIME_TABLE_DIR),
        help="Directory containing existing runtime annual-flow tables.",
    )
    parser.add_argument(
        "--source-method-dir",
        default=str(DEFAULT_SOURCE_METHOD_DIR),
        help="Directory containing source/method matrix outputs.",
    )
    parser.add_argument(
        "--holder-tdc-bridge-path",
        default=str(DEFAULT_HOLDER_TDC_BRIDGE_PATH),
        help="Current holder/TDC consistency bridge table.",
    )
    parser.add_argument(
        "--tdc-channel-path",
        default=str(DEFAULT_TDC_CHANNEL_PATH),
        help="TDC assumption-mode channel table.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/current_observed_overlay",
        help="Directory for current benchmark and observed-overlay outputs.",
    )
    args = parser.parse_args()

    benchmark_rows = current_assumption_benchmark_rows(
        runtime_table_dir=Path(args.runtime_table_dir)
    )
    overlay_rows = current_observed_overlay_map_rows(
        source_method_dir=Path(args.source_method_dir)
    )
    admission_rows = current_observed_overlay_admission_rows(
        benchmark_rows=benchmark_rows,
        holder_tdc_bridge_path=Path(args.holder_tdc_bridge_path),
        tdc_channel_path=Path(args.tdc_channel_path),
    )
    candidate_rows = current_observed_overlay_candidate_rows(
        benchmark_rows=benchmark_rows,
        overlay_rows=overlay_rows,
        admission_rows=admission_rows,
    )
    audit_rows = current_observed_overlay_audit_rows(
        benchmark_rows=benchmark_rows,
        overlay_rows=overlay_rows,
        candidate_rows=candidate_rows,
        admission_rows=admission_rows,
    )
    outputs = write_current_observed_overlay_outputs(
        Path(args.output_dir),
        benchmark_rows=benchmark_rows,
        overlay_rows=overlay_rows,
        candidate_rows=candidate_rows,
        admission_rows=admission_rows,
        audit_rows=audit_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"benchmark_rows: {len(benchmark_rows)}")
    print(f"overlay_rows: {len(overlay_rows)}")
    print(f"candidate_rows: {len(candidate_rows)}")
    print(f"admission_rows: {len(admission_rows)}")
    print(f"audit_rows: {len(audit_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
