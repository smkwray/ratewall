#!/usr/bin/env python3
"""Build realized safe-yield income source and gate artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.deposit_payer_flow_source_panel import (
    deposit_payer_flow_source_panel_rows,
    safe_yield_sublane_status_rows,
    write_deposit_payer_flow_source_outputs,
)
from ratewall.databook.realized_safe_yield_income import (
    DEFAULT_RAW_DIR,
    DEFAULT_CURRENT_OVERLAY_DIR,
    DEFAULT_SAFE_YIELD_FRED_DIR,
    constructed_safe_yield_flow_diagnostic_rows,
    deposit_safe_yield_fallback_basis_rows,
    deposit_interest_payer_flow_candidate_rows,
    realized_safe_yield_bounded_sensitivity_rows,
    realized_safe_yield_audit_rows,
    realized_safe_yield_gap_rows,
    realized_safe_yield_lane_decision_rows,
    realized_safe_yield_payer_flow_admission_rows,
    realized_safe_yield_source_inventory_rows,
    write_realized_safe_yield_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Raw source directory used to detect available safe-yield artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/realized_safe_yield_income",
        help="Directory for realized safe-yield gate outputs.",
    )
    parser.add_argument(
        "--current-overlay-dir",
        default=str(DEFAULT_CURRENT_OVERLAY_DIR),
        help="Current overlay directory used for D-period alignment checks.",
    )
    parser.add_argument(
        "--safe-yield-fred-dir",
        default=str(DEFAULT_SAFE_YIELD_FRED_DIR),
        help="Directory with official FRED CSVs for the D1 bounded fallback.",
    )
    args = parser.parse_args()

    source_panel_outputs = write_deposit_payer_flow_source_outputs(
        Path(args.output_dir),
        raw_dir=Path(args.raw_dir),
    )
    source_panel_rows = deposit_payer_flow_source_panel_rows(raw_dir=Path(args.raw_dir))
    source_status_rows = safe_yield_sublane_status_rows(
        source_panel_rows,
        raw_dir=Path(args.raw_dir),
    )
    inventory_rows = realized_safe_yield_source_inventory_rows(
        raw_dir=Path(args.raw_dir)
    )
    decision_rows = realized_safe_yield_lane_decision_rows(inventory_rows)
    deposit_rows = deposit_interest_payer_flow_candidate_rows(inventory_rows)
    admission_rows = realized_safe_yield_payer_flow_admission_rows(
        inventory_rows,
        deposit_rows,
        raw_dir=Path(args.raw_dir),
        current_overlay_dir=Path(args.current_overlay_dir),
        payer_flow_source_gate=source_status_rows[0],
    )
    diagnostic_rows = constructed_safe_yield_flow_diagnostic_rows()
    gap_rows = realized_safe_yield_gap_rows()
    audit_rows = realized_safe_yield_audit_rows(
        decision_rows=decision_rows,
        deposit_rows=deposit_rows,
        admission_rows=admission_rows,
        diagnostic_rows=diagnostic_rows,
        gap_rows=gap_rows,
    )
    fallback_basis_rows = deposit_safe_yield_fallback_basis_rows(
        source_dir=Path(args.safe_yield_fred_dir),
        current_overlay_dir=Path(args.current_overlay_dir),
    )
    bounded_sensitivity_rows = realized_safe_yield_bounded_sensitivity_rows(
        fallback_basis_rows
    )
    outputs = write_realized_safe_yield_outputs(
        Path(args.output_dir),
        inventory_rows=inventory_rows,
        decision_rows=decision_rows,
        deposit_rows=deposit_rows,
        admission_rows=admission_rows,
        diagnostic_rows=diagnostic_rows,
        gap_rows=gap_rows,
        audit_rows=audit_rows,
        fallback_basis_rows=fallback_basis_rows,
        bounded_sensitivity_rows=bounded_sensitivity_rows,
    )
    for name, path in {**source_panel_outputs, **outputs}.items():
        print(f"{name}: {path}")
    print(f"source_panel_rows: {len(source_panel_rows)}")
    print(f"source_status_rows: {len(source_status_rows)}")
    print(f"inventory_rows: {len(inventory_rows)}")
    print(f"decision_rows: {len(decision_rows)}")
    print(f"deposit_rows: {len(deposit_rows)}")
    print(f"admission_rows: {len(admission_rows)}")
    print(f"diagnostic_rows: {len(diagnostic_rows)}")
    print(f"gap_rows: {len(gap_rows)}")
    print(f"audit_rows: {len(audit_rows)}")
    print(f"fallback_basis_rows: {len(fallback_basis_rows)}")
    print(f"bounded_sensitivity_rows: {len(bounded_sensitivity_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
