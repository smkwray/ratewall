from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
OUTPUT_REPORTS = Path("outputs/reports")
SOURCE_ARCHIVE = Path("outputs/release/ratewall_release_23_0_source_archive.zip")
SUPPORT_ARTIFACT = "ratewall_tdcsim_assumption_mode_support_ingest.csv"
GATE_ARTIFACT = "ratewall_tdcsim_assumption_mode_claim_gate.csv"
ENVELOPE_ARTIFACT = (
    "ratewall_tdcsim_assumption_mode_forecast_private_route_envelope.csv"
)
ENVELOPE_GATE_ARTIFACT = (
    "ratewall_tdcsim_assumption_mode_forecast_private_route_claim_gate.csv"
)
SUPPORT_PATH = f"outputs/tables/{SUPPORT_ARTIFACT}"
GATE_PATH = f"outputs/tables/{GATE_ARTIFACT}"
ENVELOPE_PATH = f"outputs/tables/{ENVELOPE_ARTIFACT}"
ENVELOPE_GATE_PATH = f"outputs/tables/{ENVELOPE_GATE_ARTIFACT}"
REGISTRY_MANIFEST_PATH = (
    "data/raw/ratewall_sibling_calibration/tdcsim_assumption_mode/"
    "tdcsim_assumption_mode_manifest.json"
)


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _source_scan_counts(scan: str) -> dict[str, int]:
    return {
        key: int(value)
        for item in scan.split(";")
        for key, value in [item.split("=", 1)]
    }


def _forbidden_enabled_row_count(rows: list[dict[str, str]]) -> int:
    return sum(
        any(row[field] == "true" for field in FORBIDDEN_SWITCH_FIELDS)
        for row in rows
    )


def test_tdcsim_assumption_mode_tables_are_indexed_without_promotion() -> None:
    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    assert {
        SUPPORT_ARTIFACT,
        GATE_ARTIFACT,
        ENVELOPE_ARTIFACT,
        ENVELOPE_GATE_ARTIFACT,
    } <= set(active)

    support_index = active[SUPPORT_ARTIFACT]
    gate_index = active[GATE_ARTIFACT]
    envelope_index = active[ENVELOPE_ARTIFACT]
    envelope_gate_index = active[ENVELOPE_GATE_ARTIFACT]
    assert support_index["active_status"] == "blocked_source_backed_context"
    assert gate_index["active_status"] == "blocked_source_backed_context"
    assert envelope_index["active_status"] == "blocked_source_backed_context"
    assert envelope_gate_index["active_status"] == "blocked_source_backed_context"
    assert support_index["canonical_ratio_entry"] == "false"
    assert gate_index["canonical_ratio_entry"] == "false"
    assert envelope_index["canonical_ratio_entry"] == "false"
    assert envelope_gate_index["canonical_ratio_entry"] == "false"
    assert "source_backed_private_bucket_split" in support_index["blocked_use"]
    assert "current_demand_admission" in gate_index["blocked_use"]
    assert "source_backed_private_bucket_split" in envelope_index["blocked_use"]
    assert "current_demand_admission" in envelope_gate_index["blocked_use"]
    assert support_index["claim_boundary"].endswith("_no_promotion")
    assert gate_index["claim_boundary"].endswith("_no_promotion")
    assert envelope_index["claim_boundary"].endswith("_no_promotion")
    assert envelope_gate_index["claim_boundary"].endswith("_no_promotion")


def test_tdcsim_assumption_mode_claim_gate_preserves_zero_private_split() -> None:
    support_rows = _rows(SUPPORT_ARTIFACT)
    gate_rows = _rows(GATE_ARTIFACT)
    assert len(gate_rows) == 1
    bounded_or_context_rows = [
        row for row in support_rows if row["bounded_or_context_support_row"] == "true"
    ]
    source_backed_private_split_rows = [
        row
        for row in support_rows
        if row["source_backed_private_bucket_split_row"] == "true"
    ]

    gate = gate_rows[0]
    source_scan_counts = _source_scan_counts(gate["source_scan_result"])
    assert gate["gate_status"] == "pass"
    assert gate["source_backed_private_bucket_split_rows"] == str(
        len(source_backed_private_split_rows)
    )
    assert source_scan_counts == {
        "support_rows": len(support_rows),
        "bounded_or_context_support_rows": len(bounded_or_context_rows),
        "source_backed_private_bucket_split_rows": len(
            source_backed_private_split_rows
        ),
        "forbidden_enabled_rows": _forbidden_enabled_row_count(support_rows),
    }
    assert gate["canonical_ratio_entry"] == "false"
    assert gate["current_demand_eligible"] == "false"
    assert gate["holder_allocation_enabled"] == "false"


def test_tdcsim_assumption_mode_release_surfaces_are_discoverable() -> None:
    manifest = json.loads(
        (OUTPUT_TABLES / "ratewall_release_manifest.json").read_text(encoding="utf-8")
    )
    manifest_paths = {
        path for paths in manifest["artifact_layers"].values() for path in paths
    }
    assert {SUPPORT_PATH, GATE_PATH, ENVELOPE_PATH, ENVELOPE_GATE_PATH} <= manifest_paths

    table_plate = (OUTPUT_REPORTS / "ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )
    artifact_index = (OUTPUT_REPORTS / "ratewall_release_artifact_index.md").read_text(
        encoding="utf-8"
    )
    assert SUPPORT_ARTIFACT in table_plate
    assert GATE_ARTIFACT in table_plate
    assert ENVELOPE_ARTIFACT in table_plate
    assert ENVELOPE_GATE_ARTIFACT in table_plate
    assert SUPPORT_PATH in artifact_index
    assert GATE_PATH in artifact_index
    assert ENVELOPE_PATH in artifact_index
    assert ENVELOPE_GATE_PATH in artifact_index

    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
    assert SUPPORT_PATH in names
    assert GATE_PATH in names
    assert ENVELOPE_PATH in names
    assert ENVELOPE_GATE_PATH in names
    assert REGISTRY_MANIFEST_PATH in names
