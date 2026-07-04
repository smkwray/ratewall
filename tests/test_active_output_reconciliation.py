from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import yaml

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS


OUTPUTS = Path("outputs/tables")
KEEP_MANIFEST = Path("configs/ratewall_keep_tables_20260607.yml")


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _single(
    rows: list[dict[str, str]], **criteria: str
) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if all(row.get(field) == value for field, value in criteria.items())
    ]
    assert len(matches) == 1
    return matches[0]


def _keeper_artifact_names() -> set[str]:
    manifest = yaml.safe_load(KEEP_MANIFEST.read_text(encoding="utf-8"))
    keepers: set[str] = set()
    for entries in manifest["tiers"].values():
        keepers.update(entry["output_name"] for entry in entries)
    return keepers


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def test_active_output_index_separates_static_runtime_forecast_policy_objects() -> None:
    rows = _rows("ratewall_active_output_index.csv")
    _assert_fail_closed(rows)

    by_artifact = {Path(row["artifact_path"]).name: row for row in rows}
    required = {
        "ratewall_paper_canonical_scenario_results.csv",
        "ratewall_scenario_ladder.csv",
        "ratewall_runtime_annual_flow_support_offset_scenarios.csv",
        "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv",
        "ratewall_forecast_holder_tdc_consistency_bridge.csv",
        "ratewall_forecast_path_ratio_scenario_frontier.csv",
        "ratewall_policy_path_exposure_vector_design_gate.csv",
        "ratewall_policy_path_full_protocol_admission_gate_summary.csv",
        "ratewall_policy_path_project_authored_bps_year_exposure_admission_consumer.csv",
        "ratewall_noncanonical_current_demand_support_ratio_consumer.csv",
        "ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv",
        "ratewall_conventional_drag_denominator_status_compact.csv",
        "ratewall_conventional_drag_denominator_promotion_rule_evaluation.csv",
        "ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv",
        "ratewall_conventional_drag_current_demand_ratio_gate.csv",
        "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv",
        "ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv",
        "ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv",
        "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv",
        "ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv",
        "ratewall_conventional_drag_fspdp_lp_sample_share_closeout_decision.csv",
    }
    assert required <= set(by_artifact)

    static = by_artifact["ratewall_paper_canonical_scenario_results.csv"]
    assert static["ratio_object_id"] == "rw_legacy_static_assumption_mode"
    assert static["denominator_anchor_id"] == (
        "legacy_assumption_anchor_base_current_100bps"
    )
    assert static["active_status"] == "active_sensitivity"
    assert static["comparison_class"] == "not_commensurate_without_crosswalk"
    assert "Two-headline crosswalk" in static["safe_sentence"]
    assert "0.04157132893140423351153088093" in static["safe_sentence"]

    runtime = by_artifact["ratewall_runtime_annual_flow_support_offset_scenarios.csv"]
    assert runtime["ratio_object_id"] == "rw_runtime_support_offset_af_fixed"
    assert runtime["denominator_anchor_id"] == "literature_annual_flow_bridge_candidate"
    assert runtime["denominator_status"] == "primary_empirical_runtime_anchor"
    assert runtime["active_status"] == "active_main"

    forecast_tdc = by_artifact["ratewall_forecast_holder_tdc_consistency_bridge.csv"]
    assert forecast_tdc["ratio_object_id"] == "rw_forecast_tdc_family_bridge"
    assert forecast_tdc["ratio_object_family"] == "forecast_tdc_family_scenario_object"
    assert forecast_tdc["active_status"] == "active_main"
    assert forecast_tdc["paper_use"] == "component_bridge_or_methods_guardrail"
    assert "identified_current_demand_conversion" in forecast_tdc["blocked_use"]
    assert "headline_wall_ratio_claim" in forecast_tdc["blocked_use"]

    tdc_channel = by_artifact["ratewall_tdc_assumption_mode_channel.csv"]
    assert tdc_channel["ratio_object_id"] == "rw_tdc_forward_headline_assumption_mode"
    assert "Two-headline crosswalk" in tdc_channel["safe_sentence"]
    assert "state-neutral legacy static conventional-drag denominator" in (
        tdc_channel["claim_boundary"]
    )
    assert "0.7999562733566150813589606680" in (
        tdc_channel["claim_boundary"]
    )
    assert "tdcsim 0.3.0 re-pin/crosswalk closure" in (
        tdc_channel["claim_boundary"]
    )
    assert "scenario handle, and claim boundary" in (
        tdc_channel["claim_boundary"]
    )

    full_protocol = by_artifact[
        "ratewall_policy_path_full_protocol_admission_gate_summary.csv"
    ]
    project_authored = by_artifact[
        "ratewall_policy_path_project_authored_bps_year_exposure_admission_consumer.csv"
    ]
    assert full_protocol["policy_path_admission_status"] == (
        "blocked_full_policy_path_protocol_not_admitted"
    )
    assert project_authored["policy_path_admission_status"] == (
        "pass_project_authored_exposure_protocol_conjunction_admitted_nonpromotional"
    )
    assert full_protocol["comparison_class"] == "review_only_not_commensurate_denominator"
    assert project_authored["comparison_class"] == (
        "different_object_from_full_source_protocol"
    )
    assert project_authored["denominator_status"] == (
        "admitted_nonpromotional_review_only"
    )
    assert "does not contradict the blocked full source-owned protocol" in (
        project_authored["safe_sentence"]
    )
    assert "unblock denominator/HQM use" in project_authored["safe_sentence"]
    assert "GDP_share_drag" in project_authored["blocked_use"]

    support_consumer = by_artifact[
        "ratewall_noncanonical_current_demand_support_ratio_consumer.csv"
    ]
    endpoint_decision = by_artifact[
        "ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv"
    ]
    assert support_consumer["active_status"] == "review_only"
    assert endpoint_decision["active_status"] == "review_only"
    assert support_consumer["policy_path_admission_status"] == "not_policy_path"
    assert endpoint_decision["policy_path_admission_status"] == "not_policy_path"
    assert support_consumer["comparison_class"] == (
        "noncanonical_current_demand_consumer_not_runtime_or_forecast_primary"
    )
    assert endpoint_decision["comparison_class"] == (
        "noncanonical_current_demand_endpoint_not_runtime_or_forecast_primary"
    )
    assert support_consumer["claim_boundary"] == (
        "active_output_noncanonical_current_demand_consumer_review_only"
    )
    assert endpoint_decision["claim_boundary"] == (
        "active_output_noncanonical_current_demand_endpoint_review_only"
    )
    for indexed in (support_consumer, endpoint_decision):
        assert "current_demand_admission" in indexed["blocked_use"]
        assert "Evidence_Mode" in indexed["blocked_use"]
        assert indexed["paper_use"] == "not_for_paper_main"

    h8_status = by_artifact["ratewall_conventional_drag_denominator_status_compact.csv"]
    h8_rule = by_artifact[
        "ratewall_conventional_drag_denominator_promotion_rule_evaluation.csv"
    ]
    frbus = by_artifact["ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv"]
    demand_gate = by_artifact[
        "ratewall_conventional_drag_current_demand_ratio_gate.csv"
    ]
    overlay = by_artifact[
        "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv"
    ]
    conversion_boundary = by_artifact[
        "ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv"
    ]
    conversion_design = by_artifact[
        "ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv"
    ]
    conversion_sensitivity = by_artifact[
        "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv"
    ]
    lp_sample_share_join = by_artifact[
        "ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv"
    ]
    lp_sample_share_closeout = by_artifact[
        "ratewall_conventional_drag_fspdp_lp_sample_share_closeout_decision.csv"
    ]
    assert h8_status["active_status"] == "review_only"
    assert h8_status["denominator_status"] == (
        "review_only_controlled_lp_h8_candidate_not_admitted"
    )
    assert h8_rule["source_status"] == "blocked_bounded_h8_promotion_rule_indexed"
    assert "weak review context" in h8_rule["safe_sentence"]
    assert frbus["source_status"] == "review_only_frbus_100bp_year_benchmark_indexed"
    assert "1.591604679633" in frbus["notes"]
    assert demand_gate["denominator_status"] == "review_only_h8_candidate_not_admitted"
    assert overlay["backend_use"] == "runtime_support_offset_benchmark_overlay"
    for indexed in (h8_status, h8_rule, frbus, demand_gate, overlay):
        assert indexed["paper_use"] != "forecast_scenario_product"
        assert indexed["canonical_ratio_entry"] == "false"
        assert indexed["enters_main_ratio"] == "false"
        assert indexed["evidence_mode_enabled"] == "false"
    assert conversion_boundary["active_status"] == "review_only"
    assert conversion_boundary["denominator_status"] == (
        "blocked_value_bearing_lp_support_not_gdp_share_denominator"
    )
    assert conversion_boundary["source_status"] == (
        "blocked_fspdp_conversion_uncertainty_boundary_indexed"
    )
    assert "GDP-share conversion" in conversion_boundary["safe_sentence"]
    assert "D_Y" in conversion_boundary["blocked_use"]
    assert conversion_boundary["canonical_ratio_entry"] == "false"
    assert conversion_boundary["enters_main_ratio"] == "false"
    assert conversion_boundary["evidence_mode_enabled"] == "false"
    assert conversion_design["active_status"] == "review_only"
    assert conversion_design["denominator_status"] == (
        "blocked_fspdp_gdp_share_conversion_design_not_admitted"
    )
    assert conversion_design["source_status"] == (
        "blocked_fspdp_gdp_share_conversion_design_gate_indexed"
    )
    assert "source-backed FSPDP nominal GDP-share inputs" in conversion_design[
        "safe_sentence"
    ]
    assert "GDP_share_drag" in conversion_design["blocked_use"]
    assert conversion_design["canonical_ratio_entry"] == "false"
    assert conversion_design["enters_main_ratio"] == "false"
    assert conversion_design["evidence_mode_enabled"] == "false"
    assert conversion_sensitivity["active_status"] == "sensitivity_noncanonical"
    assert conversion_sensitivity["denominator_status"] == (
        "admitted_noncanonical_sensitivity_not_d_y"
    )
    assert conversion_sensitivity["source_status"] == (
        "admitted_noncanonical_fspdp_gdp_share_conversion_sensitivity_indexed"
    )
    assert "bounded sensitivity rows" in conversion_sensitivity["notes"]
    assert "D_Y" in conversion_sensitivity["blocked_use"]
    assert conversion_sensitivity["paper_use"] == "not_for_paper_main"
    assert conversion_sensitivity["canonical_ratio_entry"] == "false"
    assert conversion_sensitivity["enters_main_ratio"] == "false"
    assert conversion_sensitivity["evidence_mode_enabled"] == "false"
    assert lp_sample_share_join["active_status"] == "review_only"
    assert lp_sample_share_join["denominator_status"] == (
        "pass_lp_sample_base_quarter_share_join_materialized"
    )
    assert lp_sample_share_join["source_status"] == (
        "active_fspdp_lp_sample_base_share_join_indexed"
    )
    assert "bounded sensitivity input" in lp_sample_share_join["notes"]
    assert "D_Y" in lp_sample_share_join["blocked_use"]
    assert lp_sample_share_join["paper_use"] == "not_for_paper_main"
    assert lp_sample_share_join["canonical_ratio_entry"] == "false"
    assert lp_sample_share_join["enters_main_ratio"] == "false"
    assert lp_sample_share_join["evidence_mode_enabled"] == "false"
    assert lp_sample_share_closeout["active_status"] == "review_only"
    assert lp_sample_share_closeout["denominator_status"] == (
        "closed_noncanonical_sensitivity_only_until_new_evidence"
    )
    assert lp_sample_share_closeout["source_status"] == (
        "active_fspdp_lp_sample_share_closeout_indexed"
    )
    assert "closeout records" in lp_sample_share_closeout["safe_sentence"]
    assert "D_Y" in lp_sample_share_closeout["blocked_use"]
    assert lp_sample_share_closeout["paper_use"] == "not_for_paper_main"
    assert lp_sample_share_closeout["canonical_ratio_entry"] == "false"
    assert lp_sample_share_closeout["enters_main_ratio"] == "false"
    assert lp_sample_share_closeout["evidence_mode_enabled"] == "false"


def test_reference_scenario_crosswalk_preserves_current_values_and_boundaries() -> None:
    rows = _rows("ratewall_reference_scenario_object_crosswalk.csv")
    _assert_fail_closed(rows)

    by_family = {row["object_family"]: row for row in rows}
    assert set(by_family) == {
        "legacy_static_assumption_mode_sensitivity",
        "runtime_empirical_annual_flow",
        "forecast_tdc_family_interest_only",
        "forecast_tdc_family_ex_overlap_support",
        "review_only_bounded_h8_overlay",
    }

    static = by_family["legacy_static_assumption_mode_sensitivity"]
    assert static["denominator_anchor_id"] == (
        "legacy_assumption_anchor_base_current_100bps"
    )
    static_source = _single(
        _rows("ratewall_paper_canonical_scenario_results.csv"),
        assumption_set="base_current_100bps",
    )
    assert Decimal(static["wall_ratio_or_offset"]) == Decimal(
        static_source["ratewall_offset_ratio"]
    )
    assert static["hit_status"] == "static_not_hit"

    runtime = by_family["runtime_empirical_annual_flow"]
    assert runtime["denominator_anchor_id"] == "literature_annual_flow_bridge_candidate"
    assert Decimal(runtime["denominator_value"]) == Decimal("0.776")
    assert "canonical_rw_y" in runtime["blocked_use"]
    assert "denominator_prior" in runtime["blocked_use"]
    assert "Evidence_Mode" in runtime["blocked_use"]
    assert "support-offset diagnostics" in runtime["safe_sentence"]
    assert "not the static headline" in runtime["safe_sentence"]
    assert "not the" in runtime["safe_sentence"]
    runtime_source = _single(
        _rows("ratewall_runtime_annual_flow_support_offset_frontier_summary.csv"),
        forecast_year="2026",
        denominator_source_id="literature_annual_flow_bridge_candidate",
    )
    assert Decimal(runtime["wall_ratio_or_offset"]) == Decimal(
        runtime_source["reference_support_offset_100bp_year_equivalent"]
    )
    assert runtime["hit_status"] == "runtime_not_hit"

    forecast_interest = by_family["forecast_tdc_family_interest_only"]
    forecast_tdc = by_family["forecast_tdc_family_ex_overlap_support"]
    forecast_source = _single(
        _rows("ratewall_forecast_holder_tdc_consistency_bridge.csv"),
        forecast_year="2026",
        mpc_scenario="base_mpc_10pct",
        maturity_scenario="current_wam_cbo_rate_path",
        holder_scenario="current_holder_distribution",
    )
    assert Decimal(forecast_interest["wall_ratio_or_offset"]) == Decimal(
        forecast_source["interest_only_wall_ratio"]
    )
    assert Decimal(forecast_tdc["wall_ratio_or_offset"]) == Decimal(
        forecast_source["holder_tdc_consistent_wall_ratio"]
    )
    assert forecast_tdc["hit_status"] == "forecast_tdc_not_hit"
    assert "identified_demand_conversion" in forecast_tdc["blocked_use"]

    h8 = by_family["review_only_bounded_h8_overlay"]
    assert h8["denominator_anchor_id"] == "bounded_h8_overlay_review_center"
    assert h8["hit_status"] == "review_only_not_wall_ratio"
    assert h8["comparison_class"] == (
        "review_only_not_commensurate_without_unit_netting_crosswalk"
    )


def test_active_output_index_paths_exist() -> None:
    rows = _rows("ratewall_active_output_index.csv")
    keeper_artifacts = _keeper_artifact_names()
    missing = [
        row["artifact_path"]
        for row in rows
        if Path(row["artifact_path"]).name in keeper_artifacts
        and not Path(row["artifact_path"]).exists()
    ]
    assert not missing
