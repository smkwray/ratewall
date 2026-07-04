"""Compatibility shim for the legacy RateWall databook builder.

The Phase-4 spine split keeps the historical implementation in
``ratewall.databook.build_legacy`` while preserving existing imports from
``ratewall.databook.build``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from ratewall.databook import build_legacy as _legacy


build_databook = _legacy.build_databook
DatabookArtifacts = _legacy.DatabookArtifacts
DatabookTableWriteSpec = _legacy.DatabookTableWriteSpec
DEFAULT_KEEP_TABLES_MANIFEST = Path("configs/ratewall_keep_tables_20260607.yml")
DEFAULT_FREEZE_MANIFEST = Path("configs/ratewall_freeze_manifest_20260607.csv")

__all__ = [name for name in dir(_legacy) if not name.startswith("__")]


def _artifact_name(value: str) -> str:
    return Path(value).name


def load_keep_table_names(
    manifest_path: Path = DEFAULT_KEEP_TABLES_MANIFEST,
) -> set[str]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    keep_names: set[str] = set()
    for entries in manifest.get("tiers", {}).values():
        for entry in entries:
            output_name = entry.get("output_name") or _artifact_name(
                entry["artifact_path"]
            )
            keep_names.add(output_name)
    return keep_names


def load_frozen_table_names(
    freeze_manifest_path: Path = DEFAULT_FREEZE_MANIFEST,
) -> set[str]:
    with freeze_manifest_path.open(newline="", encoding="utf-8") as handle:
        return {
            _artifact_name(row["artifact_path"])
            for row in csv.DictReader(handle)
            if row.get("artifact_path", "").endswith(".csv")
        }


def default_table_names(
    *,
    include_frozen: bool = False,
    extra_allowed_names: set[str] | None = None,
    keep_manifest_path: Path = DEFAULT_KEEP_TABLES_MANIFEST,
    freeze_manifest_path: Path = DEFAULT_FREEZE_MANIFEST,
) -> set[str]:
    allowed = load_keep_table_names(keep_manifest_path)
    if include_frozen:
        allowed.update(load_frozen_table_names(freeze_manifest_path))
    if extra_allowed_names:
        allowed.update(extra_allowed_names)
    return allowed


def assert_default_table_outputs(
    output_dir: Path,
    *,
    include_frozen: bool = False,
    extra_allowed_names: set[str] | None = None,
    keep_manifest_path: Path = DEFAULT_KEEP_TABLES_MANIFEST,
    freeze_manifest_path: Path = DEFAULT_FREEZE_MANIFEST,
) -> set[Path]:
    tables_dir = output_dir / "tables"
    current = set(tables_dir.glob("*.csv")) if tables_dir.exists() else set()
    current_names = {path.name for path in current}
    keep_names = load_keep_table_names(keep_manifest_path)
    allowed_names = default_table_names(
        include_frozen=include_frozen,
        extra_allowed_names=extra_allowed_names,
        keep_manifest_path=keep_manifest_path,
        freeze_manifest_path=freeze_manifest_path,
    )
    extra = sorted(current_names - allowed_names)
    missing = sorted(keep_names - current_names)
    if extra or missing:
        messages = []
        if extra:
            messages.append(f"extra default tables: {', '.join(extra)}")
        if missing:
            messages.append(f"missing default tables: {', '.join(missing)}")
        raise RuntimeError("; ".join(messages))
    return current


def apply_default_table_output_policy(
    output_dir: Path,
    *,
    include_frozen: bool = False,
    forbid_extra_default_tables: bool = False,
    extra_allowed_names: set[str] | None = None,
    keep_manifest_path: Path = DEFAULT_KEEP_TABLES_MANIFEST,
    freeze_manifest_path: Path = DEFAULT_FREEZE_MANIFEST,
) -> set[Path]:
    tables_dir = output_dir / "tables"
    allowed_names = default_table_names(
        include_frozen=include_frozen,
        extra_allowed_names=extra_allowed_names,
        keep_manifest_path=keep_manifest_path,
        freeze_manifest_path=freeze_manifest_path,
    )
    if tables_dir.exists():
        for table_path in tables_dir.glob("*.csv"):
            if table_path.name not in allowed_names:
                table_path.unlink()
    if forbid_extra_default_tables:
        return assert_default_table_outputs(
            output_dir,
            include_frozen=include_frozen,
            extra_allowed_names=extra_allowed_names,
            keep_manifest_path=keep_manifest_path,
            freeze_manifest_path=freeze_manifest_path,
        )
    return set(tables_dir.glob("*.csv")) if tables_dir.exists() else set()


def refresh_build_census_written_tables(output_dir: Path) -> dict[str, Any] | None:
    census_path = output_dir / "build_census.json"
    tables_dir = output_dir / "tables"
    if not census_path.exists():
        return None
    census = json.loads(census_path.read_text(encoding="utf-8"))
    table_records = []
    if tables_dir.exists():
        for table_path in sorted(tables_dir.glob("*.csv")):
            table_records.append(
                {"name": table_path.name, "bytes": table_path.stat().st_size}
            )
    census["written_tables"] = table_records
    census["written_table_names"] = [record["name"] for record in table_records]
    census["written_table_count"] = len(table_records)
    census["bytes_written"] = sum(int(record["bytes"]) for record in table_records)
    census["census_refreshed_after_output_policy"] = True
    census_path.write_text(
        json.dumps(census, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return census


def __getattr__(name: str) -> Any:
    return getattr(_legacy, name)


def __dir__() -> list[str]:
    return sorted({*globals(), *dir(_legacy)})
