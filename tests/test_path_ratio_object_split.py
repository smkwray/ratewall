from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ratewall.databook.path_ratio_program import (
    LITERATURE_ANNUAL_FLOW_RUNTIME_ANCHOR_PP_STR,
)
from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS


pytestmark = pytest.mark.full_surface

OUTPUTS = Path("outputs/tables")
TABLE_PLATE = Path("outputs/reports/ratewall_table_plate.md")
RELEASE_INDEX = Path("outputs/reports/ratewall_release_artifact_index.md")


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def test_ratio_object_registry_splits_runtime_from_path_ratio_program() -> None:
    rows = _rows("ratewall_ratio_object_registry.csv")
    assert rows
    for row in rows:
        expected_canonical = (
            "true"
            if row["ratio_object_id"] == "rw_runtime_support_offset_af_fixed"
            else "false"
        )
        assert row["canonical_ratio_entry"] == expected_canonical
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"

    by_id = {row["ratio_object_id"]: row for row in rows}
    assert set(by_id) == {
        "rw_legacy_static_assumption_mode",
        "rw_runtime_support_offset_af_fixed",
        "rw_historical_wall_ratio_path",
        "rw_forecast_wall_ratio_path",
        "rw_forecast_tdc_family_bridge",
        "rw_policy_path_review_only",
        "rw_distance_to_wall_state_surface",
    }

    static = by_id["rw_legacy_static_assumption_mode"]
    assert static["object_family"] == "legacy_static_assumption_mode_sensitivity"
    assert static["denominator_rule"] == (
        "legacy_static_current_canonical_gdp_share_not_empirical_runtime_anchor;"
        f"center_pp_gdp={LITERATURE_ANNUAL_FLOW_RUNTIME_ANCHOR_PP_STR}"
    )
    assert "0.006" not in static["denominator_rule"]
    assert "0.006" not in static["forbidden_sentence"]
    assert static["fixed_runtime_anchor_role"] == (
        "not_runtime_anchor_static_sensitivity"
    )

    runtime = by_id["rw_runtime_support_offset_af_fixed"]
    assert runtime["object_family"] == "canonical_annual_flow_100bp_year"
    assert runtime["default_consumer_status"] == (
        "pass_canonical_assumption_mode_object"
    )
    assert runtime["denominator_rule"] == (
        "fixed_literature_annual_flow_h4_endpoint_proxy_only;"
        "interval_pp_gdp=[0.35,1.30]"
    )
    assert runtime["fixed_runtime_anchor_role"] == "canonical_annual_flow_default"
    assert runtime["current_materialization_status"] == (
        "pass_canonical_assumption_mode_runtime"
    )

    historical = by_id["rw_historical_wall_ratio_path"]
    assert historical["default_consumer_status"] == (
        "pass_materialized_default_historical_object"
    )
    assert historical["fixed_runtime_anchor_role"] == "comparison_lane_only"
    assert historical["current_materialization_status"] == (
        "pass_historical_incremental_path_ratio_materialized"
    )
    assert historical["numerator_contract_status"] == (
        "pass_shared_path_ratio_numerator_ledger_materialized"
    )
    assert historical["denominator_contract_status"] == (
        "pass_historical_path_denominator_v1_materialized"
    )
    assert historical["exact_blocker"] == ""

    forecast = by_id["rw_forecast_wall_ratio_path"]
    assert forecast["default_consumer_status"] == (
        "pass_materialized_default_forecast_object"
    )
    assert forecast["fixed_runtime_anchor_role"] == "comparison_lane_only"
    assert forecast["current_materialization_status"] == (
        "pass_forecast_incremental_path_ratio_materialized"
    )
    assert forecast["numerator_contract_status"] == (
        "pass_shared_path_ratio_numerator_ledger_materialized"
    )
    assert forecast["denominator_contract_status"] == (
        "pass_forecast_path_denominator_v1_materialized"
    )
    assert forecast["exact_blocker"] == ""

    forecast_tdc = by_id["rw_forecast_tdc_family_bridge"]
    assert forecast_tdc["object_family"] == "forecast_tdc_family_scenario_object"
    assert forecast_tdc["denominator_rule"] == (
        "forecast_scenario_drag_not_runtime_empirical_anchor"
    )
    assert forecast_tdc["fixed_runtime_anchor_role"] == (
        "not_runtime_anchor_forecast_tdc_family"
    )

    policy_path = by_id["rw_policy_path_review_only"]
    assert policy_path["object_family"] == "review_only_policy_path_bps_year"
    assert policy_path["exact_blocker"] == "review_only_policy_path_not_denominator"
    assert policy_path["blocked_use"] == (
        "main_ratio;denominator_prior;Evidence_Mode;"
        "raw_rate_shock_runtime_promotion"
    )

    state_sidecar = by_id["rw_distance_to_wall_state_surface"]
    assert state_sidecar["default_consumer_status"] == (
        "pass_materialized_state_sidecar_noncanonical"
    )
    assert state_sidecar["current_materialization_status"] == (
        "pass_state_distance_sidecar_materialized"
    )
    assert state_sidecar["numerator_contract_status"] == (
        "pass_state_sidecar_uses_materialized_path_ratio_frontiers"
    )
    assert state_sidecar["denominator_contract_status"] == (
        "pass_state_sidecar_uses_materialized_path_denominator_lineage"
    )
    assert state_sidecar["exact_blocker"] == ""


def test_wall_denominator_contract_blocks_silent_runtime_anchor_reuse() -> None:
    rows = _rows("ratewall_wall_denominator_path_contract.csv")
    _assert_fail_closed(rows)

    runtime_primary = [
        row
        for row in rows
        if row["ratio_object_id"] == "rw_runtime_support_offset_af_fixed"
        and row["row_role"] == "runtime_default_primary"
    ]
    assert len(runtime_primary) == 1
    assert runtime_primary[0]["denominator_object_id"] == (
        "literature_annual_flow_bridge_candidate"
    )
    assert runtime_primary[0]["runtime_direct_ratio_allowed"] == "true"

    historical_primary = [
        row
        for row in rows
        if row["ratio_object_id"] == "rw_historical_wall_ratio_path"
        and row["historical_primary_allowed"] == "true"
    ]
    assert len(historical_primary) == 1
    assert historical_primary[0]["denominator_object_id"] == (
        "historical_path_denominator_v1_required"
    )
    assert historical_primary[0]["comparison_lane_only"] == "false"
    assert historical_primary[0]["source_status"] == (
        "pass_historical_path_denominator_v1_materialized"
    )

    forecast_primary = [
        row
        for row in rows
        if row["ratio_object_id"] == "rw_forecast_wall_ratio_path"
        and row["forecast_primary_allowed"] == "true"
    ]
    assert len(forecast_primary) == 1
    assert forecast_primary[0]["denominator_object_id"] == (
        "forecast_path_denominator_v1_required"
    )
    assert forecast_primary[0]["comparison_lane_only"] == "false"
    assert forecast_primary[0]["source_status"] == (
        "pass_forecast_path_denominator_v1_materialized"
    )

    bad_primary = [
        row
        for row in rows
        if row["ratio_object_id"] in {
            "rw_historical_wall_ratio_path",
            "rw_forecast_wall_ratio_path",
        }
        and row["denominator_object_id"] == "fixed_runtime_comparison_lane"
        and (
            row["historical_primary_allowed"] == "true"
            or row["forecast_primary_allowed"] == "true"
        )
    ]
    assert not bad_primary

    state_sidecar = [
        row
        for row in rows
        if row["ratio_object_id"] == "rw_distance_to_wall_state_surface"
    ]
    assert len(state_sidecar) == 1
    assert state_sidecar[0]["denominator_object_id"] == (
        "state_distance_denominator_sidecar"
    )
    assert state_sidecar[0]["source_status"] == (
        "pass_materialized_state_sidecar_denominator_lineage"
    )
    assert state_sidecar[0]["exact_blocker"] == ""


def test_release_surfaces_list_path_ratio_split_artifacts() -> None:
    for path in (TABLE_PLATE, RELEASE_INDEX):
        text = path.read_text(encoding="utf-8")
        assert "ratewall_ratio_object_registry.csv" in text
        assert "ratewall_active_output_index.csv" in text
        assert "ratewall_reference_scenario_object_crosswalk.csv" in text
        assert "ratewall_wall_denominator_path_contract.csv" in text
        assert "ratewall_path_ratio_denominator_v1.csv" in text
        assert "ratewall_path_ratio_tdc_adjustment_layer.csv" in text
        assert "ratewall_historical_incremental_path_ratio.csv" in text
        assert "ratewall_historical_incremental_path_ratio_tdc_comparison.csv" in text
        assert "ratewall_historical_tdc_path_admission.csv" in text
        assert "ratewall_historical_tdc_source_hardening_audit.csv" in text
        assert "ratewall_historical_tdc_source_admission_targeting.csv" in text
        assert "ratewall_historical_tdc_component_gap_registry.csv" in text
        assert "ratewall_historical_tdc_source_backed_only_eligibility.csv" in text
        assert "ratewall_historical_tdc_selected_series_bridge_alignment.csv" in text
        assert "ratewall_historical_tdc_admission_feasibility_summary.csv" in text
        assert "ratewall_historical_tdc_source_backed_companion_candidate.csv" in text
        assert "ratewall_historical_tdc_selected_series_bridge_remediation_matrix.csv" in text
        assert "ratewall_historical_tdc_du_ru_sensitive_panel_blocker_registry.csv" in text
        assert "ratewall_historical_tdc_admission_candidate_matrix.csv" in text
        assert "ratewall_historical_tdc_post_bridge_admission_status.csv" in text
        assert "ratewall_historical_tdc_du_ru_methodology_panel.csv" in text
        assert "ratewall_historical_tdc_bridge_candidate_priority_queue.csv" in text
        assert "ratewall_historical_tdc_post_bridge_blocker_queue.csv" in text
        assert "ratewall_historical_tdc_source_work_queue.csv" in text
        assert "ratewall_historical_tdc_exact_du_ru_closure_contract.csv" in text
        assert "ratewall_historical_tdc_overlap_identity_closure_contract.csv" in text
        assert "ratewall_historical_tdc_primary_bridge_target_registry.csv" in text
        assert "ratewall_historical_tdc_selected_series_primary_target_mapping_plan.csv" in text
        assert "ratewall_historical_tdc_selected_series_bridge_execution.csv" in text
        assert "ratewall_historical_tdc_bridge_implementation_prep.csv" in text
        assert "ratewall_historical_incremental_path_ratio_frontier_summary.csv" in text
        assert "ratewall_forecast_incremental_path_ratio.csv" in text
        assert "ratewall_forecast_incremental_path_ratio_tdc_comparison.csv" in text
        assert "ratewall_forecast_incremental_path_ratio_frontier_summary.csv" in text
        assert "ratewall_historical_forecast_wall_ratio_comparison_matrix.csv" in text
        assert "ratewall_distance_to_wall_state_surface.csv" in text
        assert "ratewall_closest_to_wall_frontier.csv" in text
