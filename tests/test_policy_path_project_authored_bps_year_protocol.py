from __future__ import annotations

import pytest
import csv
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
PROTOCOL_ARTIFACT = (
    "ratewall_policy_path_project_authored_bps_year_protocol_contract.csv"
)
SOURCE_INPUT_ARTIFACT = (
    "ratewall_policy_path_project_authored_bps_year_source_input_contract.csv"
)
REPLICATION_ARTIFACT = (
    "ratewall_policy_path_project_authored_bps_year_replication_protocol.csv"
)


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(row: dict[str, str]) -> None:
    for field in (
        "candidate_rate_change_bps",
        "candidate_bps_year_component",
        "candidate_bps_year_exposure",
        "bps_year_exposure_output",
        "candidate_gdp_share_drag_per_100bp_year",
        "candidate_ci_lower",
        "candidate_ci_upper",
    ):
        assert row[field] == ""
    assert row["protocol_admission_status"].startswith("blocked")
    assert row["policy_path_100bp_year_normalization_status"].startswith("blocked")
    assert row["enters_main_ratio"] == "false"
    assert row["evidence_mode_enabled"] == "false"
    assert row["denominator_prior_update_allowed"] == "false"
    assert row["prior_narrowing_allowed"] == "false"
    for field in FORBIDDEN_SWITCH_FIELDS:
        assert row[field] == "false"


def test_project_authored_bps_year_protocol_declares_formula_boundary() -> None:
    rows = _rows(PROTOCOL_ARTIFACT)
    assert len(rows) == 4
    by_component = {row["component_id"]: row for row in rows}
    assert set(by_component) == {
        "formula_text",
        "promotion_boundary",
        "source_authored_input_boundary",
        "source_input_complete_gate",
    }

    formula = by_component["formula_text"]
    assert formula["formula_classification"] == (
        "project_authored_normalization_from_source_authored_policy_path_inputs"
    )
    assert formula["project_authored_formula_flag"] == "true"
    assert formula["source_authored_input_flag"] == "false"
    assert formula["dimensional_unit_check"] == (
        "basis_points_times_years_divided_by_100"
    )
    assert "overlap_year_fraction" in formula["formula_text"]
    assert "/ 100" in formula["formula_text"]

    for row in rows:
        _assert_fail_closed(row)


def test_project_authored_bps_year_source_inputs_reuse_current_adjudication() -> None:
    rows = _rows(SOURCE_INPUT_ARTIFACT)
    assert len(rows) == 18
    by_input = {row["input_id"]: row for row in rows}
    assert {
        "contract_reference_interval",
        "event_date",
        "horizon_overlap_year_fraction",
        "instrument_code",
        "pca_scalar_to_cell_backtransform_review",
        "price_to_rate_sign",
        "source_cell_rate_change_unit",
    } <= set(by_input)

    source_backed = [
        row
        for row in rows
        if row["source_input_status"]
        == "pass_source_authored_input_available_nonpromotional"
    ]
    assert source_backed
    for row in source_backed:
        assert row["source_authored_input_flag"] == "true"
        assert row["project_authored_formula_flag"] == "false"
        assert row["source_artifact_path"]
        assert row["source_artifact_sha256"]
        assert row["source_table_or_code_path"]
        assert row["linked_source_extraction_result_adjudication_row_id"].startswith(
            "policy_path_source_extraction_result_adjudication::"
        )
        _assert_fail_closed(row)

    horizon = by_input["horizon_overlap_year_fraction"]
    assert horizon["source_input_status"] == (
        "blocked_source_authored_formula_absent_project_formula_allowed"
    )
    assert "project-authored accounting" in horizon["exact_blocker"]


def test_project_authored_bps_year_replication_protocol_targets_event_exposure() -> None:
    rows = _rows(REPLICATION_ARTIFACT)
    assert len(rows) == 6
    assert {row["replication_target_id"] for row in rows} == {
        "bps_year_component_rebuild",
        "double_implementation_tolerance",
        "event_horizon_exposure_sum",
        "event_instrument_input_parse",
        "interval_overlap_rebuild",
        "nonpromotion_boundary",
    }
    assert {row["replication_target_artifact"] for row in rows} == {
        "ratewall_policy_path_project_authored_bps_year_event_exposure.csv"
    }
    assert {row["numeric_tolerance"] for row in rows} == {"1e-08"}
    assert {row["replication_protocol_status"] for row in rows} == {
        "pass_independent_event_exposure_replication_executed_nonpromotional"
    }
    double_implementation = [
        row
        for row in rows
        if row["replication_target_id"] == "double_implementation_tolerance"
    ]
    assert all(
        "implementation_2_value" in row["expected_output_fields"]
        for row in double_implementation
    )
    for row in rows:
        assert row["formula_classification"] == (
            "project_authored_normalization_from_source_authored_policy_path_inputs"
        )
        assert "overlap_year_fraction" in row["formula_text"]
        assert "not admitted" in row["exact_blocker"]
        _assert_fail_closed(row)


def test_project_authored_bps_year_protocol_ledger_and_backend_invariant() -> None:
    ledger_rows = _rows("ratewall_assumption_source_backing_ledger.csv")
    expected_counts = {
        PROTOCOL_ARTIFACT: 4,
        SOURCE_INPUT_ARTIFACT: 18,
        REPLICATION_ARTIFACT: 6,
    }
    for artifact, expected_count in expected_counts.items():
        rows = [
            row for row in ledger_rows if row["artifact_or_surface"] == artifact
        ]
        assert len(rows) == expected_count
        assert {row["source_backing_class"] for row in rows} == {
            "blocked_or_diagnostic_only"
        }
        assert {row["enters_canonical_ratio"] for row in rows} == {"false"}

    backend = {
        row["audit_item"]: row
        for row in _rows("ratewall_backend_invariant_guardrail_audit.csv")
    }
    assert backend["policy_path_project_authored_bps_year_protocol_fail_closed"][
        "audit_status"
    ] == "pass"
