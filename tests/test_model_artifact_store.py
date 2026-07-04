from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.databook.model_artifact_store import (
    ARTIFACT_MANIFEST_SCHEMA_VERSION,
    DEFAULT_ARTIFACT_MANIFEST_FILENAME,
    ModelArtifactStoreError,
    artifact_manifest_stats,
    estimate_artifact_store_stats,
    materialize_artifact_manifest,
    verify_artifact_manifest,
    write_artifact_manifest,
)
from ratewall.databook.tdcsim_cbo_contracts import tdcsim_cbo_scenario_effect_rows
from ratewall.databook.tdcsim_cbo_contracts import (
    tdcsim_cbo_scenario_effect_rows_from_directory,
)
from test_tdcsim_cbo_contract_ingest import _package


def test_manifest_collapses_duplicate_files_and_materializes_layout(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    (source / "nested").mkdir()
    (source / "nested" / "b.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    (source / "nested" / "c.json").write_text('{"ok": true}\n', encoding="utf-8")

    manifest_path = tmp_path / "manifest" / DEFAULT_ARTIFACT_MANIFEST_FILENAME
    stats = write_artifact_manifest(
        source,
        object_store_root=tmp_path / "objects",
        manifest_path=manifest_path,
    )

    assert stats.entry_count == 3
    assert stats.unique_object_count == 2
    assert stats.duplicate_savings_bytes == len("x,y\n1,2\n".encode())
    assert estimate_artifact_store_stats(source) == stats
    assert verify_artifact_manifest(manifest_path) == stats

    target = tmp_path / "materialized"
    materialized_stats = materialize_artifact_manifest(manifest_path, target)

    assert materialized_stats == stats
    assert (target / "a.csv").read_text(encoding="utf-8") == "x,y\n1,2\n"
    assert (target / "nested" / "b.csv").read_text(encoding="utf-8") == "x,y\n1,2\n"
    assert json.loads((target / "nested" / "c.json").read_text(encoding="utf-8")) == {
        "ok": True
    }


def test_manifest_materialization_fails_closed_on_corrupt_object(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "table.csv").write_text("a\n1\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    write_artifact_manifest(
        source,
        object_store_root=tmp_path / "objects",
        manifest_path=manifest_path,
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    object_path = (
        manifest_path.parent
        / payload["object_store_root"]
        / payload["entries"][0]["object_path"]
    )
    object_path.write_text("corrupt\n", encoding="utf-8")

    with pytest.raises(ModelArtifactStoreError, match="size mismatch|hash mismatch"):
        materialize_artifact_manifest(manifest_path, tmp_path / "materialized")


def test_manifest_rejects_unsafe_paths(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
                "object_store_root": "objects",
                "entries": [
                    {
                        "logical_path": "../escape.csv",
                        "sha256": "0" * 64,
                        "size_bytes": 0,
                        "object_path": "objects/00/" + ("0" * 64),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ModelArtifactStoreError, match="unsafe"):
        artifact_manifest_stats(manifest_path)


def test_tdcsim_cbo_model_rows_are_identical_after_materialization(
    tmp_path: Path,
) -> None:
    original_run = _package(
        tmp_path / "suite",
        scenario_id="cbo_baseline_noop_v1",
    )
    manifest_path = tmp_path / "manifest" / "run_manifest.json"
    write_artifact_manifest(
        original_run,
        object_store_root=tmp_path / "objects",
        manifest_path=manifest_path,
    )
    materialized_run = tmp_path / "materialized" / original_run.name
    materialize_artifact_manifest(manifest_path, materialized_run)

    denominator = {2027: Decimal("126.1995153634877105572719155")}
    original_rows = tdcsim_cbo_scenario_effect_rows(
        [original_run],
        fiscal_years=(2027,),
        denominator_by_fiscal_year=denominator,
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )
    materialized_rows = tdcsim_cbo_scenario_effect_rows(
        [materialized_run],
        fiscal_years=(2027,),
        denominator_by_fiscal_year=denominator,
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    assert materialized_rows == original_rows


def test_tdcsim_cbo_directory_reader_accepts_manifest_only_suite(
    tmp_path: Path,
) -> None:
    source_suite = tmp_path / "source_suite"
    run_root = _package(
        source_suite / "runs",
        scenario_id="cbo_baseline_noop_v1",
    )
    (source_suite / "frozen_denominator_by_fiscal_year.csv").write_text(
        "fiscal_year,frozen_denominator_bil\n"
        "2027,126.1995153634877105572719155\n",
        encoding="utf-8",
    )
    packed_suite = tmp_path / "packed_suite"
    packed_suite.mkdir()
    manifest_path = packed_suite / DEFAULT_ARTIFACT_MANIFEST_FILENAME
    write_artifact_manifest(
        source_suite,
        object_store_root=tmp_path / "objects",
        manifest_path=manifest_path,
    )

    direct_rows = tdcsim_cbo_scenario_effect_rows(
        [run_root],
        fiscal_years=(2027,),
        denominator_by_fiscal_year={2027: Decimal("126.1995153634877105572719155")},
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )
    manifest_rows = tdcsim_cbo_scenario_effect_rows_from_directory(
        packed_suite,
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    assert manifest_rows == direct_rows
