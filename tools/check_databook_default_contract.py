#!/usr/bin/env python3
"""Validate the default RateWall databook de-bloat contract."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml


DEFAULT_KEEP_MANIFEST = Path("configs/ratewall_keep_tables_20260607.yml")
DEFAULT_MAX_BYTES = 60_000_000
DEFAULT_STATIC_RATEWALL_RATIO = "0.04157132893140423351153088093"
STATIC_SCENARIO_TABLE = "ratewall_paper_canonical_scenario_results.csv"
STATIC_SCENARIO_ID = "base_current_100bps"


def _keeper_names(manifest_path: Path) -> set[str]:
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "ratewall.keep_tables.v1":
        raise RuntimeError(f"{manifest_path} must use schema ratewall.keep_tables.v1")
    names: set[str] = set()
    for entries in payload.get("tiers", {}).values():
        for entry in entries:
            names.add(str(entry["output_name"]))
    return names


def _read_census(output_dir: Path) -> dict[str, Any]:
    path = output_dir / "build_census.json"
    if not path.exists():
        raise RuntimeError(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _table_paths(output_dir: Path) -> list[Path]:
    tables_dir = output_dir / "tables"
    if not tables_dir.exists():
        raise RuntimeError(f"missing {tables_dir}")
    return sorted(tables_dir.glob("*.csv"))


def _assert_static_base_row(
    *,
    output_dir: Path,
    expected_static_ratewall_ratio: str,
) -> None:
    path = output_dir / "tables" / STATIC_SCENARIO_TABLE
    if not path.exists():
        raise RuntimeError(f"missing static base table: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("assumption_set") == STATIC_SCENARIO_ID
        ]
    if len(rows) != 1:
        raise RuntimeError(
            f"{STATIC_SCENARIO_TABLE} must contain exactly one {STATIC_SCENARIO_ID} row"
        )
    row = rows[0]
    if row.get("ratewall_offset_ratio") != expected_static_ratewall_ratio:
        raise RuntimeError(
            f"{STATIC_SCENARIO_ID} ratewall_offset_ratio "
            f"{row.get('ratewall_offset_ratio')} != {expected_static_ratewall_ratio}"
        )


def check_contract(
    *,
    output_dir: Path,
    keep_manifest: Path = DEFAULT_KEEP_MANIFEST,
    max_bytes: int = DEFAULT_MAX_BYTES,
    expected_static_ratewall_ratio: str = DEFAULT_STATIC_RATEWALL_RATIO,
) -> dict[str, Any]:
    table_paths = _table_paths(output_dir)
    actual_names = {path.name for path in table_paths}
    keeper_names = _keeper_names(keep_manifest)
    extra = sorted(actual_names - keeper_names)
    missing = sorted(keeper_names - actual_names)
    if extra or missing:
        details = []
        if extra:
            details.append("extra tables: " + ", ".join(extra))
        if missing:
            details.append("missing keeper tables: " + ", ".join(missing))
        raise RuntimeError("; ".join(details))

    bytes_total = sum(path.stat().st_size for path in table_paths)
    if bytes_total >= max_bytes:
        raise RuntimeError(f"default table bytes {bytes_total} >= {max_bytes}")

    census = _read_census(output_dir)
    if census.get("mode") != "default":
        raise RuntimeError(f"build_census mode is {census.get('mode')!r}, not default")
    if census.get("executed_full_only_specs") != []:
        raise RuntimeError(
            "default build executed full-only specs: "
            + ", ".join(census.get("executed_full_only_specs", []))
        )
    if census.get("executed_full_only_row_factories") != []:
        raise RuntimeError(
            "default build executed full-only row factories: "
            + ", ".join(census.get("executed_full_only_row_factories", []))
        )
    if set(census.get("written_table_names", [])) != actual_names:
        raise RuntimeError("build_census written_table_names do not match disk")
    if int(census.get("written_table_count", -1)) != len(actual_names):
        raise RuntimeError("build_census written_table_count does not match disk")
    if int(census.get("bytes_written", -1)) != bytes_total:
        raise RuntimeError("build_census bytes_written does not match disk")

    _assert_static_base_row(
        output_dir=output_dir,
        expected_static_ratewall_ratio=expected_static_ratewall_ratio,
    )
    return {
        "table_count": len(actual_names),
        "bytes_total": bytes_total,
        "static_ratewall_ratio": expected_static_ratewall_ratio,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--keep-manifest", type=Path, default=DEFAULT_KEEP_MANIFEST)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument(
        "--expected-static-ratewall-ratio",
        default=DEFAULT_STATIC_RATEWALL_RATIO,
    )
    args = parser.parse_args(argv)
    result = check_contract(
        output_dir=args.output_dir,
        keep_manifest=args.keep_manifest,
        max_bytes=args.max_bytes,
        expected_static_ratewall_ratio=args.expected_static_ratewall_ratio,
    )
    print(
        "default databook contract passed: "
        f"{result['table_count']} tables / {result['bytes_total']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
