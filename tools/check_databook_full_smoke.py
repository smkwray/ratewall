#!/usr/bin/env python3
"""Smoke-check a full RateWall databook output directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_MIN_TABLE_COUNT = 693
FULL_ONLY_SENTINELS = {
    "ratewall_assumption_source_backing_ledger.csv",
    "ratewall_backend_artifact_claim_boundary_manifest.csv",
    "ratewall_backend_surface_schema_contract.csv",
    "ratewall_generated_text_claim_boundary_scan.csv",
    "ratewall_release_archive_reproducibility_audit.csv",
}
FULL_SURFACE_SENTINELS = {
    "holder_allocation_design_ledger_disabled.csv",
    "holder_allocation_gate.csv",
    "ratewall_blocker_resolution_ledger.csv",
    "ratewall_final_blocker_ledger.csv",
    "ratewall_path_ratio_numerator_ledger.csv",
    "ratewall_release_16_no_further_promotion_ledger.csv",
    "ratewall_tdc_deposit_channel_ledger.csv",
    "treasury_frn_reset_cusip_coverage_ledger.csv",
    "treasury_frn_reset_fixture_readiness_ledger.csv",
    "treasury_frn_reset_method_design_ledger.csv",
    "treasury_frn_reset_method_frontier_ledger.csv",
}
REQUIRED_FULL_TABLES = FULL_ONLY_SENTINELS | FULL_SURFACE_SENTINELS


def _read_census(output_dir: Path) -> dict[str, Any]:
    path = output_dir / "build_census.json"
    if not path.exists():
        raise RuntimeError(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_full_smoke(
    *,
    output_dir: Path,
    min_table_count: int = DEFAULT_MIN_TABLE_COUNT,
    required_tables: set[str] | None = None,
) -> dict[str, Any]:
    tables_dir = output_dir / "tables"
    if not tables_dir.exists():
        raise RuntimeError(f"missing {tables_dir}")
    actual_names = {path.name for path in tables_dir.glob("*.csv")}
    if len(actual_names) < min_table_count:
        raise RuntimeError(
            f"full databook wrote {len(actual_names)} CSVs, expected at least "
            f"{min_table_count}"
        )
    required = required_tables or REQUIRED_FULL_TABLES
    missing = sorted(required - actual_names)
    if missing:
        raise RuntimeError("missing full-surface sentinel tables: " + ", ".join(missing))

    census = _read_census(output_dir)
    if census.get("mode") != "full":
        raise RuntimeError(f"build_census mode is {census.get('mode')!r}, not full")
    if int(census.get("written_table_count", -1)) < min_table_count:
        raise RuntimeError("build_census written_table_count is below the full minimum")
    if not FULL_ONLY_SENTINELS <= set(census.get("executed_full_only_specs", [])):
        missing_executed = sorted(
            FULL_ONLY_SENTINELS - set(census.get("executed_full_only_specs", []))
        )
        raise RuntimeError(
            "build_census did not execute full-only specs: "
            + ", ".join(missing_executed)
        )
    return {
        "table_count": len(actual_names),
        "bytes_total": sum(path.stat().st_size for path in tables_dir.glob("*.csv")),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--min-table-count", type=int, default=DEFAULT_MIN_TABLE_COUNT)
    args = parser.parse_args(argv)
    result = check_full_smoke(
        output_dir=args.output_dir,
        min_table_count=args.min_table_count,
    )
    print(
        "full databook smoke passed: "
        f"{result['table_count']} tables / {result['bytes_total']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
