from __future__ import annotations

import pytest
import csv
import json
import zipfile
from decimal import Decimal
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
ARTIFACT = "ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv"
CLOSEOUT_ARTIFACT = (
    "ratewall_conventional_drag_fspdp_lp_sample_share_closeout_decision.csv"
)
RELEASE_ARTIFACTS = {
    "ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv",
    "ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv",
    "ratewall_conventional_drag_fspdp_gdp_share_conversion_method_admission.csv",
    ARTIFACT,
    "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv",
    CLOSEOUT_ARTIFACT,
}


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _join_rows() -> list[dict[str, str]]:
    return _rows(ARTIFACT)


def _rows_for_horizon(rows: list[dict[str, str]], horizon_q: str) -> list[dict[str, str]]:
    return [row for row in rows if row["horizon_q"] == horizon_q]


def test_lp_sample_base_share_join_row_grain_and_sample_window() -> None:
    rows = _join_rows()

    assert {row["horizon_q"] for row in rows} == {"4", "8"}
    assert len({row["fspdp_lp_sample_base_share_join_row_id"] for row in rows}) == len(
        rows
    )
    assert len({(row["horizon_q"], row["lp_sample_quarter"]) for row in rows}) == len(
        rows
    )
    sample_quarters_by_horizon = {
        horizon: {row["lp_sample_quarter"] for row in _rows_for_horizon(rows, horizon)}
        for horizon in {"4", "8"}
    }
    assert sample_quarters_by_horizon["4"] == sample_quarters_by_horizon["8"]
    assert {row["share_window_id"] for row in rows} == {
        "lp_sample_base_quarter_mean"
    }
    assert {row["share_window_role"] for row in rows} == {
        "primary_lp_sample_base_quarter_mean_sensitivity_center"
    }
    for row in rows:
        horizon_rows = _rows_for_horizon(rows, row["horizon_q"])
        assert int(row["lp_sample_row_count"]) == len(
            {candidate["lp_sample_quarter"] for candidate in horizon_rows}
        )
        assert int(row["matched_base_share_row_count"]) == len(
            {candidate["gdp_share_panel_row_id"] for candidate in horizon_rows}
        )
        assert row["first_lp_sample_quarter"] == min(
            candidate["lp_sample_quarter"] for candidate in horizon_rows
        )
        assert row["last_lp_sample_quarter"] == max(
            candidate["lp_sample_quarter"] for candidate in horizon_rows
        )
        assert row["first_lp_base_quarter"] == min(
            candidate["lp_base_quarter"] for candidate in horizon_rows
        )
        assert row["last_lp_base_quarter"] == max(
            candidate["lp_base_quarter"] for candidate in horizon_rows
        )

    first = rows[0]
    last = rows[-1]
    assert first["lp_sample_quarter"] == "1990Q1"
    assert first["lp_base_quarter"] == "1989Q4"
    assert first["lp_future_quarter"] == "1991Q1"
    assert first["gdp_share_panel_row_id"] == (
        "current_demand_gdp_share_panel::1989Q4::fspdp"
    )
    assert last["lp_sample_quarter"] == "2023Q4"
    assert last["lp_base_quarter"] == "2023Q3"
    assert last["lp_future_quarter"] == "2025Q4"
    assert last["gdp_share_panel_row_id"] == (
        "current_demand_gdp_share_panel::2023Q3::fspdp"
    )


def test_lp_sample_base_share_mean_is_close_to_baseline_fallback() -> None:
    rows = _join_rows()

    assert {row["sample_inclusion_status"] for row in rows} == {
        "pass_included_in_value_bearing_lp_and_base_share_join"
    }
    assert {row["sample_mean_nominal_share_of_gdp"] for row in rows} == {
        "0.84098657287"
    }
    assert {row["baseline_fallback_mean_nominal_share_of_gdp"] for row in rows} == {
        "0.841858678531"
    }
    assert {row["absolute_difference_from_baseline"] for row in rows} == {
        "0.000872105661"
    }
    assert {row["relative_difference_from_baseline"] for row in rows} == {
        "0.001035928812"
    }
    assert Decimal(rows[0]["relative_difference_from_baseline"]) < Decimal("0.01")
    assert {row["baseline_comparison_status"] for row in rows} == {
        "pass_lp_sample_share_close_to_baseline_fallback"
    }


def test_lp_sample_base_share_join_preserves_no_promotion_switches() -> None:
    for row in _join_rows():
        assert row["allowed_use"] == (
            "lp_sample_base_quarter_fspdp_share_primary_sensitivity_input"
        )
        assert row["claim_boundary"] == (
            "lp_sample_base_share_join_not_denominator_admission"
        )
        assert "D_Y" in row["blocked_use"]
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        assert row["canonical_ratio_entry"] == "false"
        assert row["denominator_prior_update_allowed"] == "false"
        for field in FORBIDDEN_SWITCH_FIELDS:
            assert row[field] == "false"


def test_lp_sample_base_share_join_ledger_active_output_and_invariant() -> None:
    ledger_rows = [
        row
        for row in _rows("ratewall_assumption_source_backing_ledger.csv")
        if row["assumption_family"]
        == "conventional_drag_fspdp_lp_sample_base_share_join"
    ]
    assert len(ledger_rows) == len(_join_rows())
    assert {row["artifact_or_surface"] for row in ledger_rows} == {ARTIFACT}
    assert {row["current_value_exact"] for row in ledger_rows} == {
        "0.84098657287"
    }
    assert {row["unit"] for row in ledger_rows} == {
        "nominal_fspdp_share_of_nominal_gdp_lp_sample_base_quarter_mean"
    }
    assert {row["source_backing_class"] for row in ledger_rows} == {
        "blocked_or_diagnostic_only"
    }
    assert {row["source_backing_subclass"] for row in ledger_rows} == {
        "local_lp_diagnostic_not_calibration"
    }
    assert {row["enters_canonical_ratio"] for row in ledger_rows} == {"false"}

    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    assert active[ARTIFACT]["active_status"] == "review_only"
    assert active[ARTIFACT]["denominator_status"] == (
        "pass_lp_sample_base_quarter_share_join_materialized"
    )
    assert active[ARTIFACT]["source_status"] == (
        "active_fspdp_lp_sample_base_share_join_indexed"
    )
    assert active[ARTIFACT]["canonical_ratio_entry"] == "false"

    backend = {
        row["audit_item"]: row
        for row in _rows("ratewall_backend_invariant_guardrail_audit.csv")
    }
    assert backend[
        "conventional_drag_fspdp_lp_sample_base_share_join_fail_closed"
    ]["audit_status"] == "pass"


def test_lp_sample_share_closeout_decision_closes_current_fspdp_lane_without_promotion() -> None:
    rows = _rows(CLOSEOUT_ARTIFACT)
    assert len(rows) == 1
    row = rows[0]

    join_rows = _join_rows()
    sensitivity_rows = _rows(
        "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv"
    )
    assert int(row["lp_sample_base_share_join_row_count"]) == len(join_rows)
    assert int(row["sensitivity_row_count"]) == len(sensitivity_rows)
    assert row["horizons_evaluated"] == ";".join(
        sorted({candidate["horizon_q"] for candidate in join_rows})
    )
    assert row["primary_share_window_id"] == "lp_sample_base_quarter_mean"
    assert row["fallback_share_window_id"] == "baseline_1994q1_2019q4"
    assert row["lp_sample_mean_nominal_share_of_gdp"] == "0.84098657287"
    assert row["baseline_fallback_mean_nominal_share_of_gdp"] == "0.841858678531"
    assert row["absolute_difference_from_baseline"] == "0.000872105661"
    assert row["relative_difference_from_baseline"] == "0.001035928812"
    assert Decimal(row["relative_difference_from_baseline"]) < Decimal("0.01")
    assert row["materiality_threshold_relative_to_baseline"] == "0.01"
    assert row["baseline_comparison_status"] == (
        "pass_lp_sample_share_close_to_baseline_fallback"
    )
    assert row["lp_sample_h4_positive_drag_gdp_share_per_100bp_year"] == (
        "-0.030484423878"
    )
    assert row["baseline_h4_positive_drag_gdp_share_per_100bp_year"] == (
        "-0.030516036319"
    )
    assert row["absolute_h4_positive_drag_difference"] == "0.000031612441"
    assert row["lp_sample_h8_positive_drag_gdp_share_per_100bp_year"] == (
        "0.048191248237"
    )
    assert row["baseline_h8_positive_drag_gdp_share_per_100bp_year"] == (
        "0.04824122271"
    )
    assert row["absolute_h8_positive_drag_difference"] == "0.000049974473"
    assert row["share_window_primary_decision"] == (
        "keep_lp_sample_base_quarter_mean_primary_noncanonical_sensitivity_center"
    )
    assert row["baseline_fallback_decision"] == (
        "retain_baseline_1994q1_2019q4_as_fallback_robustness_window"
    )
    assert row["interpretation_decision_status"] == (
        "pass_no_material_interpretation_change_relative_difference_under_1pct"
    )
    assert row["external_benchmark_decision_status"] == (
        "not_required_for_current_noncanonical_sensitivity_closeout"
    )
    assert row["denominator_upgrade_decision_status"] == (
        "blocked_no_promotion_grade_denominator_evidence"
    )
    assert row["evidence_upgrade_path_decision"] == (
        "do_not_expand_fspdp_denominator_lane_without_new_promotion_grade_source_contract"
    )
    assert row["current_fspdp_lane_status"] == (
        "closed_noncanonical_sensitivity_only_until_new_evidence"
    )
    assert row["allowed_use"] == (
        "fspdp_lp_sample_share_interpretation_closeout_review_only"
    )
    assert row["claim_boundary"] == (
        "lp_sample_share_closeout_decision_not_denominator_admission"
    )
    assert "D_Y" in row["blocked_use"]
    assert row["enters_main_ratio"] == "false"
    assert row["evidence_mode_enabled"] == "false"
    assert row["canonical_ratio_entry"] == "false"
    assert row["denominator_prior_update_allowed"] == "false"
    for field in FORBIDDEN_SWITCH_FIELDS:
        assert row[field] == "false"


def test_lp_sample_share_closeout_decision_ledger_active_output_and_invariant() -> None:
    ledger_rows = [
        row
        for row in _rows("ratewall_assumption_source_backing_ledger.csv")
        if row["assumption_family"]
        == "conventional_drag_fspdp_lp_sample_share_closeout_decision"
    ]
    assert len(ledger_rows) == 1
    ledger = ledger_rows[0]
    assert ledger["artifact_or_surface"] == CLOSEOUT_ARTIFACT
    assert ledger["current_value_exact"] == "0.001035928812"
    assert ledger["unit"] == (
        "relative_difference_between_lp_sample_and_baseline_fspdp_share"
    )
    assert ledger["source_backing_class"] == "blocked_or_diagnostic_only"
    assert ledger["source_backing_subclass"] == "local_lp_diagnostic_not_calibration"
    assert ledger["enters_canonical_ratio"] == "false"

    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    assert active[CLOSEOUT_ARTIFACT]["active_status"] == "review_only"
    assert active[CLOSEOUT_ARTIFACT]["denominator_status"] == (
        "closed_noncanonical_sensitivity_only_until_new_evidence"
    )
    assert active[CLOSEOUT_ARTIFACT]["source_status"] == (
        "active_fspdp_lp_sample_share_closeout_indexed"
    )
    assert active[CLOSEOUT_ARTIFACT]["canonical_ratio_entry"] == "false"

    backend = {
        row["audit_item"]: row
        for row in _rows("ratewall_backend_invariant_guardrail_audit.csv")
    }
    assert backend[
        "conventional_drag_fspdp_lp_sample_share_closeout_decision_no_promotion"
    ]["audit_status"] == "pass"


def test_lp_sample_base_share_join_release_membership() -> None:
    manifest = json.loads(
        (OUTPUT_TABLES / "ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    manifest_members = {
        Path(member).name
        for members in manifest["artifact_layers"].values()
        for member in members
    }
    table_plate = Path("outputs/reports/ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )
    artifact_index = Path(
        "outputs/reports/ratewall_release_artifact_index.md"
    ).read_text(encoding="utf-8")
    with zipfile.ZipFile("outputs/release/ratewall_release_23_0_source_archive.zip") as archive:
        archive_members = {Path(member).name for member in archive.namelist()}

    assert RELEASE_ARTIFACTS <= manifest_members
    assert RELEASE_ARTIFACTS <= archive_members
    for artifact in RELEASE_ARTIFACTS:
        assert artifact in table_plate
        assert artifact in artifact_index
