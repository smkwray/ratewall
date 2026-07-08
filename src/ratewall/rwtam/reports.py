"""CSV output helpers for RWTAM result tables."""

from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.contract import OUTPUT_TABLES
from ratewall.rwtam.engine import RwtamResult


def write_outputs(result: RwtamResult, output_dir: Path) -> dict[str, Path]:
    """Write all RWTAM output tables to CSV files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name in OUTPUT_TABLES:
        rows = result.rows(table_name)
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
