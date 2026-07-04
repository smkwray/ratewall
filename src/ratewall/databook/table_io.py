"""Shared CSV table-writing helpers for RateWall databook outputs."""

from __future__ import annotations

import csv
import math
from decimal import Decimal
from pathlib import Path
from typing import Any


_WRITE_TABLE_NAMES: set[str] | None = None


def set_write_table_filter(table_names: set[str] | None) -> None:
    """Restrict CSV writes to a named table set, or clear the filter."""

    global _WRITE_TABLE_NAMES
    _WRITE_TABLE_NAMES = table_names


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return format(value, "f") if value.is_finite() else str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return format(Decimal(str(value)).normalize(), "f")
    return str(value)


def _normalize_row(row: dict[str, Any], fields: list[str]) -> dict[str, str]:
    extra_fields = sorted(set(row) - set(fields))
    if extra_fields:
        raise ValueError(f"extra CSV fields for {fields}: {', '.join(extra_fields)}")
    return {field: _csv_value(row.get(field)) for field in fields}


def write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    """Write dictionaries with the explicit field order used by databook tables."""
    if _WRITE_TABLE_NAMES is not None and path.name not in _WRITE_TABLE_NAMES:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(_normalize_row(row, fields) for row in rows)
