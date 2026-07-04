from __future__ import annotations

import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from ratewall.databook.build import apply_default_table_output_policy
from ratewall.databook.table_io import write_rows


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


debloat_manifests = _load_tool("debloat_manifests")
map_databook_outputs = _load_tool("map_databook_outputs")
build_callgraph = _load_tool("build_callgraph")
hash_keep_tables = _load_tool("hash_keep_tables")
check_databook_default_contract = _load_tool("check_databook_default_contract")
check_databook_full_smoke = _load_tool("check_databook_full_smoke")


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        ",".join(header)
        + "\n"
        + "\n".join(",".join(row) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def _write_default_policy_manifests(tmp_path: Path) -> tuple[Path, Path]:
    keep_manifest = tmp_path / "keep.yml"
    freeze_manifest = tmp_path / "freeze.csv"
    keep_manifest.write_text(
        yaml.safe_dump(
            {
                "schema": "ratewall.keep_tables.v1",
                "tiers": {"tier1": [{"output_name": "ratewall_keeper.csv"}]},
            }
        ),
        encoding="utf-8",
    )
    freeze_manifest.write_text(
        "artifact_path,freeze_reason\n"
        "outputs/tables/ratewall_frozen.csv,review_only\n",
        encoding="utf-8",
    )
    return keep_manifest, freeze_manifest


def _write_build_census(output_dir: Path, payload: dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "build_census.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_debloat_manifests_keep_wins_over_freeze_and_cut(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    tables = output_dir / "tables"
    paper_header = [
        "output_name",
        "path",
        "canonical_ratio_entry",
        "enters_main_ratio",
        "evidence_mode_enabled",
    ]
    active_header = [
        "artifact_path",
        "canonical_ratio_entry",
        "enters_main_ratio",
        "evidence_mode_enabled",
    ]
    _write_csv(
        tables / "ratewall_paper_core_results_index.csv",
        paper_header,
        [
            [
                "ratewall_release_99_keeper_gate.csv",
                "outputs/tables/ratewall_release_99_keeper_gate.csv",
                "false",
                "false",
                "false",
            ]
        ],
    )
    _write_csv(
        tables / "ratewall_active_output_index.csv",
        active_header,
        [
            [
                "outputs/tables/ratewall_context_sidecar.csv",
                "false",
                "false",
                "false",
            ],
            [
                "outputs/tables/ratewall_release_88_cut.csv",
                "false",
                "false",
                "false",
            ],
        ],
    )
    for filename in [
        "ratewall_release_99_keeper_gate.csv",
        "ratewall_context_sidecar.csv",
        "ratewall_release_88_cut.csv",
    ]:
        _write_csv(tables / filename, ["col"], [["value"]])

    keep, freeze, cut = debloat_manifests.build_manifests(output_dir)
    keep_names = {
        entry["output_name"]
        for entries in keep["tiers"].values()
        for entry in entries
    }

    assert "ratewall_release_99_keeper_gate.csv" in keep_names
    assert all(
        "ratewall_release_99_keeper_gate.csv" not in row["artifact_path"]
        for row in [*freeze, *cut]
    )
    assert any("ratewall_context_sidecar.csv" in row["artifact_path"] for row in freeze)
    assert any("ratewall_release_88_cut.csv" in row["artifact_path"] for row in cut)


def test_debloat_manifests_freeze_volatile_frbus_review_table(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    tables = output_dir / "tables"
    _write_csv(
        tables / "ratewall_paper_core_results_index.csv",
        ["output_name", "path"],
        [],
    )
    _write_csv(
        tables / "ratewall_active_output_index.csv",
        [
            "artifact_path",
            "canonical_ratio_entry",
            "enters_main_ratio",
            "evidence_mode_enabled",
        ],
        [
            [
                "outputs/tables/ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv",
                "false",
                "false",
                "false",
            ]
        ],
    )
    _write_csv(
        tables / "ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv",
        ["col"],
        [["value"]],
    )

    keep, freeze, _cut = debloat_manifests.build_manifests(output_dir)
    keep_names = {
        entry["output_name"]
        for entries in keep["tiers"].values()
        for entry in entries
    }

    assert "ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv" not in keep_names
    assert any(
        row["artifact_path"].endswith("ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv")
        and "nondeterministic" in row["freeze_reason"]
        for row in freeze
    )


def test_output_writer_map_resolves_parallel_and_direct_writes() -> None:
    rows = map_databook_outputs.build_mapping(
        ROOT / "src/ratewall/databook/build_legacy.py"
    )
    by_output = {row.output_csv: row for row in rows}

    assert by_output["ratewall_paper_core_results_index.csv"].writer_function == (
        "_write_rows"
    )
    assert by_output["ratewall_active_output_index.csv"].source_module.endswith(
        "src/ratewall/databook/table_io.py"
    )
    assert by_output["ratewall_tdc_double_count_guardrail.csv"].source_module.endswith(
        "src/ratewall/databook/spine_tdc.py"
    )
    assert by_output[
        "ratewall_forecast_holder_tdc_consistency_bridge.csv"
    ].source_module.endswith("src/ratewall/databook/spine_tdc.py")
    assert by_output[
        "ratewall_tdc_materialization_semantic_summary.csv"
    ].source_module.endswith("src/ratewall/databook/spine_tdc.py")
    for output_csv in [
        "ratewall_calibration_parameter_recommendations.csv",
        "ratewall_denominator_literature_matrix.csv",
        "ratewall_denominator_sensitivity.csv",
        "ratewall_parameter_packs.csv",
    ]:
        assert by_output[output_csv].source_module.endswith(
            "src/ratewall/databook/spine_calibration.py"
        )
    for output_csv in [
        "ratewall_minimum_conditions_to_hit_wall.csv",
        "ratewall_paper_canonical_scenario_results.csv",
        "ratewall_publication_claim_decision.csv",
        "ratewall_wall_hit_scenarios.csv",
    ]:
        assert by_output[output_csv].source_module.endswith(
            "src/ratewall/databook/spine_scenarios.py"
        )
    for output_csv in [
        "holder_allocation_design_ledger_disabled.csv",
        "holder_allocation_gate.csv",
        "ratewall_assumption_source_backing_ledger.csv",
        "ratewall_backend_artifact_claim_boundary_manifest.csv",
        "ratewall_backend_surface_schema_contract.csv",
        "ratewall_generated_text_claim_boundary_scan.csv",
        "ratewall_path_ratio_numerator_ledger.csv",
        "ratewall_release_archive_reproducibility_audit.csv",
        "treasury_frn_reset_method_design_ledger.csv",
    ]:
        assert output_csv in by_output
    assert len(rows) > 400


def test_keeper_writers_route_through_deterministic_sink_or_spine_wrappers() -> None:
    keep_manifest = yaml.safe_load(
        (ROOT / "configs/ratewall_keep_tables_20260607.yml").read_text(
            encoding="utf-8"
        )
    )
    keepers = {
        entry["output_name"]
        for entries in keep_manifest["tiers"].values()
        for entry in entries
    }
    mapping = {
        row.output_csv: row
        for row in map_databook_outputs.build_mapping(
            ROOT / "src/ratewall/databook/build_legacy.py"
        )
    }
    missing = sorted(keepers - set(mapping))
    assert missing == []

    approved_sources = (
        "src/ratewall/databook/table_io.py",
        "src/ratewall/databook/spine_calibration.py",
        "src/ratewall/databook/spine_scenarios.py",
        "src/ratewall/databook/spine_tdc.py",
    )
    bypasses = [
        (name, mapping[name].writer_function, mapping[name].source_module)
        for name in sorted(keepers)
        if not mapping[name].source_module.endswith(approved_sources)
    ]
    assert bypasses == []


def test_callgraph_keeper_closure_excludes_cut_pattern_functions() -> None:
    payload = build_callgraph.graph_payload(
        build_path=ROOT / "src/ratewall/databook/build_legacy.py",
        manifest_path=ROOT / "configs/ratewall_keep_tables_20260607.yml",
        include_build_databook=False,
    )

    assert "_write_rows" in payload["roots"]
    assert "_write_rows" in payload["external_roots"]
    assert "_write_tdc_double_count_guardrail_table" in payload["roots"]
    assert "_write_tdc_double_count_guardrail_table" in payload["external_roots"]
    assert "_write_tdc_double_count_guardrail_table" not in payload["closure"]
    assert "_write_forecast_holder_tdc_consistency_bridge_table" in payload["roots"]
    assert "_write_forecast_holder_tdc_consistency_bridge_table" in payload[
        "external_roots"
    ]
    assert "_write_forecast_holder_tdc_consistency_bridge_table" not in payload[
        "closure"
    ]
    assert "_write_ratewall_tdc_materialization_semantic_summary_table" in payload[
        "roots"
    ]
    assert "_write_ratewall_tdc_materialization_semantic_summary_table" in payload[
        "external_roots"
    ]
    assert "_write_ratewall_tdc_materialization_semantic_summary_table" not in payload[
        "closure"
    ]
    for writer in [
        "_write_ratewall_calibration_parameter_recommendations_table",
        "_write_ratewall_denominator_literature_matrix_table",
        "_write_ratewall_denominator_sensitivity_table",
        "_write_ratewall_parameter_packs_table",
        "_write_publication_claim_decision_table",
        "_write_ratewall_minimum_conditions_to_hit_wall_table",
        "_write_ratewall_paper_canonical_scenario_results_table",
        "_write_ratewall_wall_hit_scenarios_table",
    ]:
        assert writer in payload["roots"]
        assert writer in payload["external_roots"]
        assert writer not in payload["closure"]
    assert payload["closure"] == []
    assert not [
        name
        for name in payload["closure"]
        if any(token in name for token in ("_release_", "holder_allocation"))
    ]


def test_hash_keep_tables_records_csv_bytes_rows_and_header(tmp_path: Path) -> None:
    manifest = tmp_path / "keep.yml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema": "ratewall.keep_tables.v1",
                "tiers": {
                    "tier1": [
                        {"output_name": "ratewall_keeper.csv"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    _write_csv(tmp_path / "outputs/tables/ratewall_keeper.csv", ["a", "b"], [["1", "2"]])

    rows = hash_keep_tables.hash_rows(
        output_dir=tmp_path / "outputs",
        manifest_path=manifest,
    )

    assert rows == [
        {
            "filename": "ratewall_keeper.csv",
            "sha256": rows[0]["sha256"],
            "byte_count": "8",
            "row_count": "1",
            "header": "a,b",
        }
    ]
    assert len(rows[0]["sha256"]) == 64


def test_table_io_write_rows_canonicalizes_fields_newlines_and_scalars(
    tmp_path: Path,
) -> None:
    path = tmp_path / "tables" / "fixture.csv"

    write_rows(
        path,
        [
            {
                "row_id": "first",
                "float_value": 1e-7,
                "decimal_value": Decimal("1E+3"),
                "blank_value": None,
            },
            {
                "row_id": "second",
                "float_value": 0.30000000000000004,
                "decimal_value": Decimal("0.0100"),
                "blank_value": "",
            },
        ],
        ["row_id", "float_value", "decimal_value", "blank_value"],
    )

    assert path.read_text(encoding="utf-8") == (
        "row_id,float_value,decimal_value,blank_value\n"
        "first,0.0000001,1000,\n"
        "second,0.30000000000000004,0.0100,\n"
    )
    assert b"\r\n" not in path.read_bytes()


def test_table_io_write_rows_rejects_extra_fields(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="extra CSV fields"):
        write_rows(
            tmp_path / "tables" / "fixture.csv",
            [{"declared": "ok", "extra": "bad"}],
            ["declared"],
        )


def test_hash_keep_tables_compares_repeat_build_hashes(tmp_path: Path) -> None:
    manifest = tmp_path / "keep.yml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema": "ratewall.keep_tables.v1",
                "tiers": {
                    "tier1": [
                        {"output_name": "ratewall_keeper.csv"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    left = tmp_path / "left"
    right = tmp_path / "right"
    for output_dir in (left, right):
        _write_csv(output_dir / "tables/ratewall_keeper.csv", ["a", "b"], [["1", "2"]])

    result = hash_keep_tables.check_repeat_hashes(
        output_dir=left,
        compare_to=right,
        manifest_path=manifest,
    )

    assert result == {"table_count": 1, "mismatches": []}


def test_hash_keep_tables_rejects_repeat_build_mismatch(tmp_path: Path) -> None:
    manifest = tmp_path / "keep.yml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema": "ratewall.keep_tables.v1",
                "tiers": {
                    "tier1": [
                        {"output_name": "ratewall_keeper.csv"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    left = tmp_path / "left"
    right = tmp_path / "right"
    _write_csv(left / "tables/ratewall_keeper.csv", ["a", "b"], [["1", "2"]])
    _write_csv(right / "tables/ratewall_keeper.csv", ["a", "b"], [["1", "3"]])

    with pytest.raises(RuntimeError, match="keeper hash mismatch: ratewall_keeper.csv"):
        hash_keep_tables.check_repeat_hashes(
            output_dir=left,
            compare_to=right,
            manifest_path=manifest,
        )


def test_default_databook_contract_checker_accepts_clean_keeper_surface(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    tables = output_dir / "tables"
    keep_manifest = tmp_path / "keep.yml"
    keep_manifest.write_text(
        yaml.safe_dump(
            {
                "schema": "ratewall.keep_tables.v1",
                "tiers": {
                    "tier1": [
                        {
                            "output_name": (
                                "ratewall_paper_canonical_scenario_results.csv"
                            )
                        },
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    _write_csv(
        tables / "ratewall_paper_canonical_scenario_results.csv",
        ["assumption_set", "ratewall_offset_ratio"],
        [
            [
                "base_current_100bps",
                check_databook_default_contract.DEFAULT_STATIC_RATEWALL_RATIO,
            ]
        ],
    )
    table_bytes = sum(path.stat().st_size for path in tables.glob("*.csv"))
    _write_build_census(
        output_dir,
        {
            "mode": "default",
            "written_table_names": ["ratewall_paper_canonical_scenario_results.csv"],
            "written_table_count": 1,
            "bytes_written": table_bytes,
            "executed_full_only_specs": [],
            "executed_full_only_row_factories": [],
        },
    )

    result = check_databook_default_contract.check_contract(
        output_dir=output_dir,
        keep_manifest=keep_manifest,
    )

    assert result["table_count"] == 1
    assert result["bytes_total"] == table_bytes


def test_default_databook_contract_checker_rejects_full_only_execution(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    tables = output_dir / "tables"
    keep_manifest = tmp_path / "keep.yml"
    keep_manifest.write_text(
        yaml.safe_dump(
            {
                "schema": "ratewall.keep_tables.v1",
                "tiers": {
                    "tier1": [
                        {
                            "output_name": (
                                "ratewall_paper_canonical_scenario_results.csv"
                            )
                        },
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    _write_csv(
        tables / "ratewall_paper_canonical_scenario_results.csv",
        ["assumption_set", "ratewall_offset_ratio"],
        [
            [
                "base_current_100bps",
                check_databook_default_contract.DEFAULT_STATIC_RATEWALL_RATIO,
            ]
        ],
    )
    table_bytes = sum(path.stat().st_size for path in tables.glob("*.csv"))
    _write_build_census(
        output_dir,
        {
            "mode": "default",
            "written_table_names": ["ratewall_paper_canonical_scenario_results.csv"],
            "written_table_count": 1,
            "bytes_written": table_bytes,
            "executed_full_only_specs": [
                "ratewall_assumption_source_backing_ledger.csv"
            ],
            "executed_full_only_row_factories": [],
        },
    )

    with pytest.raises(RuntimeError, match="full-only specs"):
        check_databook_default_contract.check_contract(
            output_dir=output_dir,
            keep_manifest=keep_manifest,
        )


def test_full_databook_smoke_checker_requires_sentinels(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    tables = output_dir / "tables"
    required = set(check_databook_full_smoke.REQUIRED_FULL_TABLES)
    for filename in required:
        _write_csv(tables / filename, ["col"], [["value"]])
    _write_build_census(
        output_dir,
        {
            "mode": "full",
            "written_table_count": len(required),
            "executed_full_only_specs": sorted(
                check_databook_full_smoke.FULL_ONLY_SENTINELS
            ),
        },
    )

    result = check_databook_full_smoke.check_full_smoke(
        output_dir=output_dir,
        min_table_count=len(required),
        required_tables=required,
    )

    assert result["table_count"] == len(required)


def test_default_table_output_policy_keeps_only_manifest_tables(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    tables = output_dir / "tables"
    keep_manifest, freeze_manifest = _write_default_policy_manifests(tmp_path)
    for filename in [
        "ratewall_keeper.csv",
        "ratewall_frozen.csv",
        "ratewall_extra.csv",
    ]:
        _write_csv(tables / filename, ["col"], [["value"]])

    remaining = apply_default_table_output_policy(
        output_dir,
        forbid_extra_default_tables=True,
        keep_manifest_path=keep_manifest,
        freeze_manifest_path=freeze_manifest,
    )

    assert {path.name for path in remaining} == {"ratewall_keeper.csv"}
    assert sorted(path.name for path in tables.glob("*.csv")) == [
        "ratewall_keeper.csv"
    ]


def test_default_table_output_policy_can_retain_frozen_tables(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    tables = output_dir / "tables"
    keep_manifest, freeze_manifest = _write_default_policy_manifests(tmp_path)
    for filename in [
        "ratewall_keeper.csv",
        "ratewall_frozen.csv",
        "ratewall_extra.csv",
    ]:
        _write_csv(tables / filename, ["col"], [["value"]])

    remaining = apply_default_table_output_policy(
        output_dir,
        include_frozen=True,
        forbid_extra_default_tables=True,
        keep_manifest_path=keep_manifest,
        freeze_manifest_path=freeze_manifest,
    )

    assert {path.name for path in remaining} == {
        "ratewall_frozen.csv",
        "ratewall_keeper.csv",
    }
    assert sorted(path.name for path in tables.glob("*.csv")) == [
        "ratewall_frozen.csv",
        "ratewall_keeper.csv",
    ]


def test_default_table_output_policy_can_retain_named_release_tables(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    tables = output_dir / "tables"
    keep_manifest, freeze_manifest = _write_default_policy_manifests(tmp_path)
    for filename in [
        "ratewall_keeper.csv",
        "ratewall_release_archive_reproducibility_audit.csv",
        "ratewall_frozen.csv",
        "ratewall_extra.csv",
    ]:
        _write_csv(tables / filename, ["col"], [["value"]])

    remaining = apply_default_table_output_policy(
        output_dir,
        forbid_extra_default_tables=True,
        extra_allowed_names={"ratewall_release_archive_reproducibility_audit.csv"},
        keep_manifest_path=keep_manifest,
        freeze_manifest_path=freeze_manifest,
    )

    assert {path.name for path in remaining} == {
        "ratewall_keeper.csv",
        "ratewall_release_archive_reproducibility_audit.csv",
    }
    assert sorted(path.name for path in tables.glob("*.csv")) == [
        "ratewall_keeper.csv",
        "ratewall_release_archive_reproducibility_audit.csv",
    ]


def test_default_table_output_policy_requires_keeper_tables(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    tables = output_dir / "tables"
    keep_manifest, freeze_manifest = _write_default_policy_manifests(tmp_path)
    _write_csv(tables / "ratewall_extra.csv", ["col"], [["value"]])

    with pytest.raises(RuntimeError, match="missing default tables"):
        apply_default_table_output_policy(
            output_dir,
            forbid_extra_default_tables=True,
            keep_manifest_path=keep_manifest,
            freeze_manifest_path=freeze_manifest,
        )
