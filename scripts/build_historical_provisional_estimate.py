#!/usr/bin/env python3
"""Build historical provisional RateWall estimate artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.historical_provisional_estimate import (
    DEFAULT_CBO_HISTORICAL_ECONOMIC_ZIP,
    DEFAULT_CBO_REVENUE_PATH,
    DEFAULT_FRED_SOURCE_DIR,
    DEFAULT_HISTORICAL_COMPARABLE_DIR,
    historical_denominator_convention_rows,
    historical_overlap_gate_rows,
    historical_public_interest_net_block_rows,
    historical_provisional_audit_rows,
    historical_provisional_denominator_rows,
    historical_provisional_gate_rows,
    historical_provisional_numerator_rows,
    historical_provisional_rw_rows,
    historical_root_public_interest_rw_rows,
    write_historical_provisional_estimate_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--historical-comparable-dir",
        default=str(DEFAULT_HISTORICAL_COMPARABLE_DIR),
        help="Directory containing historical comparable adapter CSVs.",
    )
    parser.add_argument(
        "--cbo-historical-economic-zip",
        default=str(DEFAULT_CBO_HISTORICAL_ECONOMIC_ZIP),
        help="CBO historical economic data zip with Quarterly_February2026.csv.",
    )
    parser.add_argument(
        "--fred-source-dir",
        default=str(DEFAULT_FRED_SOURCE_DIR),
        help="Directory containing local FRED source CSVs.",
    )
    parser.add_argument(
        "--cbo-revenue-path",
        default=str(DEFAULT_CBO_REVENUE_PATH),
        help="CBO revenue CSV containing rev_fed_reserve rows.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/historical_provisional_estimate",
        help="Directory for historical provisional estimate outputs.",
    )
    args = parser.parse_args()

    denominator_rows = historical_provisional_denominator_rows(
        historical_comparable_dir=Path(args.historical_comparable_dir),
        cbo_historical_economic_zip=Path(args.cbo_historical_economic_zip),
    )
    public_interest_rows = historical_public_interest_net_block_rows(
        historical_comparable_dir=Path(args.historical_comparable_dir),
        denominator_rows=denominator_rows,
        fred_source_dir=Path(args.fred_source_dir),
        cbo_revenue_path=Path(args.cbo_revenue_path),
    )
    root_public_interest_rw_rows = historical_root_public_interest_rw_rows(
        cbo_historical_economic_zip=Path(args.cbo_historical_economic_zip),
        fred_source_dir=Path(args.fred_source_dir),
        historical_public_interest_rows=public_interest_rows,
    )
    denominator_convention_rows = historical_denominator_convention_rows(
        denominator_rows=denominator_rows,
    )
    numerator_rows = historical_provisional_numerator_rows(
        historical_comparable_dir=Path(args.historical_comparable_dir),
        historical_public_interest_rows=public_interest_rows,
    )
    overlap_gate_rows = historical_overlap_gate_rows(
        public_interest_rows=public_interest_rows,
        numerator_rows=numerator_rows,
    )
    rw_rows = historical_provisional_rw_rows(
        denominator_rows=denominator_rows,
        numerator_rows=numerator_rows,
    )
    gate_rows = historical_provisional_gate_rows(
        denominator_rows=denominator_rows,
        numerator_rows=numerator_rows,
        public_interest_rows=public_interest_rows,
        denominator_convention_rows=denominator_convention_rows,
        overlap_gate_rows=overlap_gate_rows,
    )
    audit_rows = historical_provisional_audit_rows(
        denominator_rows=denominator_rows,
        numerator_rows=numerator_rows,
        rw_rows=rw_rows,
        gate_rows=gate_rows,
        public_interest_rows=public_interest_rows,
        denominator_convention_rows=denominator_convention_rows,
        overlap_gate_rows=overlap_gate_rows,
    )
    outputs = write_historical_provisional_estimate_outputs(
        Path(args.output_dir),
        denominator_rows=denominator_rows,
        public_interest_rows=public_interest_rows,
        root_public_interest_rw_rows=root_public_interest_rw_rows,
        denominator_convention_rows=denominator_convention_rows,
        overlap_gate_rows=overlap_gate_rows,
        numerator_rows=numerator_rows,
        rw_rows=rw_rows,
        gate_rows=gate_rows,
        audit_rows=audit_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"denominator_rows: {len(denominator_rows)}")
    print(f"public_interest_rows: {len(public_interest_rows)}")
    print(f"root_public_interest_rw_rows: {len(root_public_interest_rw_rows)}")
    print(f"denominator_convention_rows: {len(denominator_convention_rows)}")
    print(f"overlap_gate_rows: {len(overlap_gate_rows)}")
    print(f"numerator_rows: {len(numerator_rows)}")
    print(f"rw_rows: {len(rw_rows)}")
    print(f"gate_rows: {len(gate_rows)}")
    print(f"audit_rows: {len(audit_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
