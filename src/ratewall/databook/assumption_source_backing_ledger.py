"""Central source-backing ledger for RateWall assumptions.

The ledger is intentionally conservative: official source context is not
treated as calibration evidence for behavioral parameters unless a row already
documents a local estimate or sibling contract with the required gate status.
"""

from __future__ import annotations

import hashlib
from dataclasses import fields as dataclass_fields
from pathlib import Path
from typing import Iterable

import yaml

from ratewall.accounting.assumption_engine import RateWallAssumptionSet


FORBIDDEN_SWITCH_FIELDS = [
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "raw_rate_shock_enabled",
    "causal_financialization_claim_enabled",
]

SOURCE_BACKING_CLASSES = [
    "official_source_value",
    "sibling_contract_value",
    "locally_estimated_value",
    "literature_calibrated_prior",
    "literature_context_only_prior",
    "scenario_assumption",
    "pure_guess_or_placeholder",
    "blocked_or_diagnostic_only",
]

ASSUMPTION_SOURCE_BACKING_LEDGER_FIELDS = [
    "ledger_row_id",
    "assumption_handle",
    "assumption_family",
    "assumption_label",
    "artifact_or_surface",
    "surface_type",
    "upstream_row_key",
    "scenario_or_path_scope",
    "period_or_horizon",
    "value_role",
    "current_value_exact",
    "current_value_low",
    "current_value_base",
    "current_value_high",
    "current_value_range_text",
    "unit",
    "formula_role",
    "enters_canonical_ratio",
    "enters_noncanonical_assumption_mode",
    "enters_canonical_tdc_accounting",
    "enters_tdcsim_forward_surface",
    "enters_qrawatch_scenario_surface",
    "enters_split_denominator",
    "enters_dynamic_path",
    "enters_sidecar",
    "materiality_rank",
    "frontier_driver_rank",
    "affects_wall_hit_classification",
    "source_backing_class",
    "source_backing_subclass",
    "classification_confidence",
    "classification_reason",
    "source_status_raw",
    "calibration_status_raw",
    "evidence_strength_raw",
    "prior_basis_raw",
    "ratewall_use_status_raw",
    "claim_boundary_raw",
    "source_artifact",
    "source_field_or_series",
    "source_family",
    "source_url_or_key",
    "source_snapshot_kind",
    "source_record_count",
    "source_hash_or_manifest_hash",
    "sibling_project",
    "sibling_contract_artifact",
    "sibling_contract_version",
    "sibling_contract_hash",
    "local_estimation_status",
    "local_estimation_method",
    "local_estimation_artifact",
    "local_estimation_diagnostic_artifact",
    "support_diagnostics_present",
    "literature_handle",
    "literature_estimate_low",
    "literature_estimate_point",
    "literature_estimate_high",
    "directness_class",
    "transport_risk",
    "guess_status",
    "manual_override_required",
    "manual_override_source",
    "calibration_needed",
    "evidence_needed_before_prior_narrowing",
    "evidence_needed_before_promotion",
    "promotion_gate",
    "promotion_status",
    "prior_narrowing_allowed",
    "formula_replacement_allowed",
    "split_denominator_promotion_allowed",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
    "linked_source_tables",
    "missing_expected_artifact",
    "row_created_at_utc",
]

ASSUMPTION_SOURCE_BACKING_INVARIANT_AUDIT_FIELDS = [
    "audit_item",
    "audit_status",
    "evidence_table",
    "evidence_summary",
    "failure_mode_if_false",
    "claim_boundary",
]

ASSUMPTION_METADATA_COLUMNS = {
    "name",
    "assumption_set",
    "editable_label",
    "description",
    "horizon",
    "unit_scope",
    "assumption_status",
    "source_status",
    "claim_boundary",
    "mode",
    "future_remittance_drag_treatment",
    "denominator_share_sum",
    "denominator_share_sum_status",
    "split_denominator_mode",
}

SPLIT_DENOMINATOR_HANDLES = {
    "borrowing_cost_drag_share",
    "credit_supply_drag_share",
    "asset_price_drag_share",
    "expectations_drag_share",
    "exchange_rate_external_drag_share",
}


def load_source_backing_overrides(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(loaded, list):
        raise ValueError("source-backing overrides must be a list")
    rows: list[dict[str, str]] = []
    for item in loaded:
        if not isinstance(item, dict):
            raise ValueError("each source-backing override must be a mapping")
        rows.append({str(key): str(value) for key, value in item.items()})
    return rows


def assumption_source_backing_ledger_rows(
    *,
    parameter_pack_rows: list[dict[str, str]],
    assumption_set_rows: list[dict[str, str]],
    activation_rows: list[dict[str, str]],
    conventional_drag_source_design_gate_rows: list[dict[str, str]],
    conventional_drag_channel_evidence_gap_rows: list[dict[str, str]],
    denominator_calibration_design_gate_rows: list[dict[str, str]],
    denominator_response_gate_attempt_rows: list[dict[str, str]],
    conventional_drag_evidence_tranche_rows: list[dict[str, str]],
    tdsp_current_demand_source_review_rows: list[dict[str, str]],
    tdsp_current_demand_unit_conversion_rows: list[dict[str, str]],
    tdsp_current_demand_diagnostic_mapping_rows: list[dict[str, str]],
    tdsp_policy_path_normalization_blocker_rows: list[dict[str, str]],
    pce_dpi_source_refresh_contract_rows: list[dict[str, str]],
    tdsp_pce_dpi_refresh_diagnostic_mapping_rows: list[dict[str, str]],
    policy_path_exposure_vector_design_gate_rows: list[dict[str, str]],
    policy_path_reviewed_protocol_source_context_rows: list[dict[str, str]],
    policy_path_protocol_source_acquisition_rows: list[dict[str, str]],
    policy_path_protocol_review_inventory_rows: list[dict[str, str]],
    policy_path_mps_scalar_replication_diagnostic_rows: list[dict[str, str]],
    policy_path_bps_year_blocker_decision_rows: list[dict[str, str]],
    policy_path_event_level_candidate_vector_rows: list[dict[str, str]],
    policy_path_contract_interval_source_review_rows: list[dict[str, str]],
    policy_path_contract_spec_acquisition_blocker_rows: list[dict[str, str]],
    policy_path_bps_year_source_protocol_rows: list[dict[str, str]],
    policy_path_normalization_source_manifest_rows: list[dict[str, str]],
    policy_path_bps_year_normalization_review_rows: list[dict[str, str]],
    policy_path_source_cell_unit_contract_review_rows: list[dict[str, str]],
    policy_path_bps_year_protocol_closure_rows: list[dict[str, str]],
    policy_path_normalization_leak_audit_rows: list[dict[str, str]],
    conventional_drag_research_parameterization_source_contract_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_parameterization_source_frontier_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_payload_manifest_rows: list[dict[str, str]],
    conventional_drag_research_parameterization_parser_status_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_payload_inner_inventory_rows: list[dict[str, str]],
    conventional_drag_research_extraction_candidate_rows: list[dict[str, str]],
    conventional_drag_research_extraction_gate_audit_rows: list[dict[str, str]],
    conventional_drag_research_extraction_gate_detail_rows: list[dict[str, str]],
    conventional_drag_research_source_method_bridge_rows: list[dict[str, str]],
    conventional_drag_research_source_code_interpretation_rows: list[dict[str, str]],
    conventional_drag_research_extended_source_code_interpretation_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_fspdp_coverage_candidate_scan_rows: list[
        dict[str, str]
    ],
    mir_component_aggregation_review_rows: list[dict[str, str]],
    mir_component_source_variant_review_rows: list[dict[str, str]],
    conventional_drag_fspdp_component_decomposition_bridge_rows: list[dict[str, str]],
    conventional_drag_fspdp_coverage_weight_requirement_review_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_coverage_priority_search_queue_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_source_code_search_review_rows: list[dict[str, str]],
    conventional_drag_fspdp_external_source_acquisition_action_plan_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_official_component_source_acquisition_execution_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_research_side_action_plan_extraction_review_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_source_unit_conversion_review_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_mir_replication_source_unit_audit_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_mir_source_unit_transformation_contract_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_mir_target_horizon_reconciliation_contract_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_mir_horizon_rekeying_candidate_review_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_mir_h24_source_unit_audit_rows: list[dict[str, str]],
    conventional_drag_research_mir_h24_8q_rekeying_review_rows: list[dict[str, str]],
    conventional_drag_research_mir_4q8q_conversion_readiness_review_rows: list[
        dict[str, str]
    ],
    conventional_drag_research_policy_path_normalization_bridge_review_rows: list[
        dict[str, str]
    ],
    policy_path_research_shock_source_evidence_protocol_review_rows: list[
        dict[str, str]
    ],
    policy_path_source_code_workbook_object_inventory_rows: list[dict[str, str]],
    policy_path_source_code_workbook_protocol_deep_review_rows: list[
        dict[str, str]
    ],
    policy_path_usmpd_pca_loading_backtransform_review_rows: list[dict[str, str]],
    policy_path_usmpd_scalar_score_replication_review_rows: list[dict[str, str]],
    policy_path_usmpd_pca_backtransform_gate_review_rows: list[dict[str, str]],
    policy_path_usmpd_instrument_decomposition_design_review_rows: list[
        dict[str, str]
    ],
    policy_path_bps_year_candidate_path_design_contract_rows: list[dict[str, str]],
    policy_path_formula_replication_source_review_rows: list[dict[str, str]],
    policy_path_reviewed_bps_year_protocol_gap_matrix_rows: list[dict[str, str]],
    policy_path_protocol_source_acquisition_work_queue_rows: list[dict[str, str]],
    policy_path_protocol_source_parse_execution_review_rows: list[dict[str, str]],
    policy_path_source_parse_synthesis_queue_rows: list[dict[str, str]],
    policy_path_source_parse_action_execution_rows: list[dict[str, str]],
    policy_path_deeper_parse_execution_review_rows: list[dict[str, str]],
    policy_path_protocol_candidate_draft_review_rows: list[dict[str, str]],
    policy_path_protocol_missing_evidence_acquisition_queue_rows: list[
        dict[str, str]
    ],
    policy_path_protocol_missing_evidence_parse_execution_review_rows: list[
        dict[str, str]
    ],
    policy_path_protocol_authoring_readiness_matrix_rows: list[dict[str, str]],
    policy_path_protocol_field_authoring_contract_rows: list[dict[str, str]],
    policy_path_field_evidence_resolution_queue_rows: list[dict[str, str]],
    ratio_layer_registry_rows: list[dict[str, str]],
    estimation_target_registry_rows: list[dict[str, str]],
    channel_taxonomy_registry_rows: list[dict[str, str]],
    historical_interpretation_audit_rows: list[dict[str, str]],
    tdc_equation_variant_registry_rows: list[dict[str, str]],
    policy_path_source_extraction_task_packet_rows: list[dict[str, str]],
    policy_path_source_extraction_results_rows: list[dict[str, str]],
    policy_path_authored_protocol_completion_audit_rows: list[dict[str, str]],
    policy_path_protocol_completion_design_tranche_rows: list[dict[str, str]],
    policy_path_field_specific_pass_rule_design_rows: list[dict[str, str]],
    policy_path_field_specific_source_evidence_audit_rows: list[dict[str, str]],
    policy_path_source_locator_binding_review_rows: list[dict[str, str]],
    policy_path_exact_source_locator_remediation_rows: list[dict[str, str]],
    policy_path_exact_locator_field_closure_diagnostic_rows: list[dict[str, str]],
    policy_path_exact_locator_pass_rule_adjudication_rows: list[dict[str, str]],
    policy_path_terminal_no_hit_closure_rows: list[dict[str, str]],
    policy_path_independent_replication_target_design_rows: list[dict[str, str]],
    policy_path_authored_fail_closed_invariant_design_rows: list[dict[str, str]],
    policy_path_protocol_component_closure_rollup_rows: list[dict[str, str]],
    policy_path_locator_binding_closure_diagnostic_rows: list[dict[str, str]],
    policy_path_full_protocol_admission_gate_summary_rows: list[dict[str, str]],
    policy_path_source_bundle_field_exhaustion_decision_rows: list[dict[str, str]],
    policy_path_source_bundle_component_exhaustion_decision_rows: list[dict[str, str]],
    conventional_drag_empirical_target_registry_rows: list[dict[str, str]],
    conventional_drag_route_pruning_audit_rows: list[dict[str, str]],
    conventional_drag_response_design_gate_rows: list[dict[str, str]],
    denominator_response_estimate_registry_rows: list[dict[str, str]],
    denominator_formal_design_gate_rows: list[dict[str, str]],
    conventional_drag_response_execution_readiness_packet_rows: list[dict[str, str]],
    local_lp_proxy_svar_diagnostic_run_packet_rows: list[dict[str, str]],
    local_lp_proxy_svar_execution_preflight_results_rows: list[dict[str, str]],
    local_lp_proxy_svar_route_closure_decision_rows: list[dict[str, str]],
    conventional_drag_denominator_route_triage_synthesis_rows: list[dict[str, str]],
    policy_path_100bp_year_blocker_action_resolution_rows: list[dict[str, str]],
    policy_path_source_protocol_action_packet_rows: list[dict[str, str]],
    policy_path_source_protocol_pass_rule_harness_rows: list[dict[str, str]],
    policy_path_source_protocol_extraction_attempt_results_rows: list[dict[str, str]],
    policy_path_source_protocol_attempt_closure_handoff_rows: list[dict[str, str]],
    policy_path_promotion_grade_source_family_acquisition_packet_rows: list[
        dict[str, str]
    ],
    policy_path_promotion_grade_source_family_acquisition_execution_preflight_results_rows: list[
        dict[str, str]
    ],
    policy_path_source_family_execution_closure_selection_packet_rows: list[
        dict[str, str]
    ],
    policy_path_current_artifact_manual_review_execution_packet_rows: list[
        dict[str, str]
    ],
    policy_path_current_artifact_manual_review_result_attempt_rows: list[
        dict[str, str]
    ],
    policy_path_source_author_manual_acquisition_followup_packet_rows: list[
        dict[str, str]
    ],
    policy_path_source_author_manual_acquisition_execution_preflight_results_rows: list[
        dict[str, str]
    ],
    policy_path_real_source_author_web_acquisition_attempt_packet_rows: list[
        dict[str, str]
    ],
    policy_path_downloaded_artifact_locator_parse_adjudication_packet_rows: list[
        dict[str, str]
    ],
    policy_path_locator_candidate_pass_rule_review_decision_packet_rows: list[
        dict[str, str]
    ],
    policy_path_source_extraction_result_adjudication_rows: list[dict[str, str]],
    policy_path_component_gate_execution_rollup_rows: list[dict[str, str]],
    policy_path_project_authored_bps_year_protocol_contract_rows: list[
        dict[str, str]
    ],
    policy_path_project_authored_bps_year_source_input_contract_rows: list[
        dict[str, str]
    ],
    policy_path_project_authored_bps_year_replication_protocol_rows: list[
        dict[str, str]
    ],
    policy_path_project_authored_bps_year_event_exposure_rows: list[
        dict[str, str]
    ],
    policy_path_project_authored_bps_year_exposure_admission_consumer_rows: list[
        dict[str, str]
    ],
    policy_path_value_bearing_bps_year_exposure_export_rows: list[dict[str, str]],
    policy_path_value_bearing_bps_year_exposure_quarterly_series_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_component_source_manifest_rows: list[dict[str, str]],
    conventional_drag_fspdp_component_share_panel_rows: list[dict[str, str]],
    current_demand_gdp_share_source_manifest_rows: list[dict[str, str]],
    current_demand_gdp_share_panel_rows: list[dict[str, str]],
    conventional_drag_current_demand_mapping_bridge_rows: list[dict[str, str]],
    conventional_drag_research_extraction_conversion_bridge_rows: list[
        dict[str, str]
    ],
    conventional_drag_local_macro_panel_rows: list[dict[str, str]],
    conventional_drag_local_shock_quarterly_rows: list[dict[str, str]],
    conventional_drag_local_lp_design_rows: list[dict[str, str]],
    conventional_drag_local_lp_diagnostic_rows: list[dict[str, str]],
    conventional_drag_local_lp_estimate_diagnostic_rows: list[dict[str, str]],
    conventional_drag_local_lp_robustness_diagnostic_rows: list[dict[str, str]],
    conventional_drag_local_lp_sample_window_audit_rows: list[dict[str, str]],
    conventional_drag_local_lp_admission_audit_rows: list[dict[str, str]],
    conventional_drag_fspdp_denominator_readiness_gate_rows: list[dict[str, str]],
    conventional_drag_fspdp_denominator_candidate_join_preflight_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_value_bearing_exposure_lp_execution_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_denominator_conversion_uncertainty_boundary_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_gdp_share_conversion_design_gate_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_gdp_share_conversion_method_admission_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_lp_sample_base_share_join_rows: list[dict[str, str]],
    conventional_drag_fspdp_gdp_share_conversion_sensitivity_rows: list[
        dict[str, str]
    ],
    conventional_drag_fspdp_lp_sample_share_closeout_decision_rows: list[
        dict[str, str]
    ],
    openicpsr_replication_package_source_manifest_rows: list[dict[str, str]],
    frbus_model_benchmark_simulation_readiness_rows: list[dict[str, str]],
    frbus_conventional_drag_benchmark_protocol_rows: list[dict[str, str]],
    frbus_official_model_package_inventory_rows: list[dict[str, str]],
    frbus_official_model_benchmark_simulation_protocol_rows: list[dict[str, str]],
    frbus_runtime_runner_preflight_rows: list[dict[str, str]],
    frbus_runtime_runner_output_slots_rows: list[dict[str, str]],
    frbus_benchmark_comparison_mapping_contract_rows: list[dict[str, str]],
    frbus_benchmark_output_slot_extension_review_rows: list[dict[str, str]],
    conventional_drag_source_unit_aggregation_blocker_bridge_rows: list[dict[str, str]],
    conventional_drag_mirgk_targeted_gap_source_followup_rows: list[dict[str, str]],
    conventional_drag_promotion_contract_checklist_rows: list[dict[str, str]],
    backend_surface_schema_contract_rows: list[dict[str, str]],
    backend_artifact_claim_boundary_manifest_rows: list[dict[str, str]],
    release_archive_reproducibility_audit_rows: list[dict[str, str]],
    tdc_ea_tdc_pass_through_calibration_import_rows: list[dict[str, str]],
    tdc_ea_tdc_pass_through_regime_validation_import_rows: list[dict[str, str]],
    tdc_deposit_pass_through_source_import_rows: list[dict[str, str]],
    tdc_deposit_pass_through_regime_scenario_rows: list[dict[str, str]],
    tdc_deposit_pass_through_scenario_contract_rows: list[dict[str, str]],
    tdc_deposit_pass_through_trigger_validation_preflight_rows: list[dict[str, str]],
    tdc_deposit_pass_through_scenario_contract_invariant_audit_rows: list[
        dict[str, str]
    ],
    tdc_liquidity_regime_trigger_evidence_rows: list[dict[str, str]],
    tdc_liquidity_regime_trigger_promotion_protocol_rows: list[dict[str, str]],
    tdc_liquidity_regime_trigger_validation_evidence_rows: list[dict[str, str]],
    conventional_drag_decomposition_rows: list[dict[str, str]],
    interest_income_mpc_calibration_registry_rows: list[dict[str, str]],
    interest_income_proxy_range_registry_rows: list[dict[str, str]],
    interest_income_claim_boundary_audit_rows: list[dict[str, str]],
    tdc_forward_assumption_registry_rows: list[dict[str, str]],
    tdcsim_projection_contract_bridge_rows: list[dict[str, str]],
    canonical_tdc_accounting_source_hierarchy_audit_rows: list[dict[str, str]],
    tdc_historical_source_contract_rows: list[dict[str, str]],
    repo_root: Path,
    overrides: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    pack_by_handle = {row.get("parameter", ""): row for row in parameter_pack_rows}
    engine_handles = _engine_numeric_handles()

    for handle in engine_handles:
        pack = pack_by_handle.get(handle, {})
        rows.append(
            _row(
                assumption_handle=handle,
                assumption_family=pack.get("channel", "ratewall_assumption_engine"),
                artifact_or_surface="src/ratewall/accounting/assumption_engine.py",
                surface_type="model_code",
                value_role="engine_numeric_field",
                current_value_low=pack.get("low", ""),
                current_value_base=pack.get("base", ""),
                current_value_high=pack.get("high", ""),
                unit=pack.get("unit", ""),
                source_status_raw=pack.get("source_status", "engine_field"),
                calibration_status_raw=pack.get("calibration_status", ""),
                evidence_strength_raw=pack.get("evidence_strength", ""),
                prior_basis_raw=pack.get("prior_basis", ""),
                source_artifact="ratewall_parameter_packs.csv"
                if pack
                else "RateWallAssumptionSet",
                source_field_or_series=handle,
                source_family=pack.get("source_family", "ratewall_internal"),
                claim_boundary=pack.get(
                    "claim_boundary", "engine_field_requires_ledger_classification"
                ),
                allowed_use=pack.get("allowed_model_use", "ratewall_model_input"),
                linked_source_tables="ratewall_parameter_packs.csv",
            )
        )

    for pack in parameter_pack_rows:
        handle = pack.get("parameter", "")
        rows.append(
            _row(
                assumption_handle=handle,
                assumption_family=pack.get("channel", ""),
                artifact_or_surface="ratewall_parameter_packs.csv",
                surface_type="parameter_registry",
                value_role="parameter_pack_range",
                current_value_low=pack.get("low", ""),
                current_value_base=pack.get("base", ""),
                current_value_high=pack.get("high", ""),
                unit=pack.get("unit", ""),
                source_status_raw=pack.get("source_status", ""),
                calibration_status_raw=pack.get("calibration_status", ""),
                evidence_strength_raw=pack.get("evidence_strength", ""),
                prior_basis_raw=pack.get("prior_basis", ""),
                claim_boundary_raw=pack.get("claim_boundary", ""),
                source_artifact=pack.get("source_gate_table", "")
                or "configs/ratewall_parameter_packs.yml",
                source_field_or_series=handle,
                source_family=pack.get("source_family", ""),
                literature_handle=pack.get("citation_handle", ""),
                evidence_needed_before_prior_narrowing=pack.get(
                    "evidence_needed", ""
                ),
                evidence_needed_before_promotion=pack.get(
                    "evidence_upgrade_blocker", ""
                ),
                promotion_gate=pack.get("upgrade_gate", ""),
                promotion_status=pack.get("external_review_status", ""),
                allowed_use=pack.get("allowed_model_use", pack.get("model_use", "")),
                claim_boundary=pack.get("claim_boundary", ""),
                linked_source_tables=pack.get("source_gate_table", ""),
            )
        )

    for assumption in assumption_set_rows:
        scope = assumption.get("assumption_set", assumption.get("name", ""))
        for handle in engine_handles:
            if handle not in assumption:
                continue
            pack = pack_by_handle.get(handle, {})
            rows.append(
                _row(
                    assumption_handle=handle,
                    assumption_family=pack.get("channel", "assumption_set"),
                    artifact_or_surface="ratewall_assumption_sets.csv",
                    surface_type="assumption_mode_surface",
                    scenario_or_path_scope=scope,
                    period_or_horizon=assumption.get("horizon", ""),
                    value_role="assumption_set_value",
                    current_value_exact=assumption.get(handle, ""),
                    unit=pack.get("unit", ""),
                    source_status_raw=assumption.get("source_status", ""),
                    calibration_status_raw=pack.get("calibration_status", ""),
                    evidence_strength_raw=pack.get("evidence_strength", ""),
                    prior_basis_raw=pack.get("prior_basis", ""),
                    claim_boundary_raw=assumption.get("claim_boundary", ""),
                    source_artifact="configs/ratewall_assumption_sets.yml",
                    source_field_or_series=handle,
                    source_family=pack.get("source_family", "assumption_mode"),
                    allowed_use="assumption_mode_scenario_value",
                    claim_boundary=assumption.get("claim_boundary", ""),
                    linked_source_tables="ratewall_parameter_packs.csv",
                )
            )

    for activation in activation_rows:
        handle = activation.get("parameter_name", "")
        pack = pack_by_handle.get(handle, {})
        rows.append(
            _row(
                assumption_handle=handle,
                assumption_family=activation.get("active_formula_family", ""),
                artifact_or_surface="ratewall_assumption_mode_parameter_activation_ledger.csv",
                surface_type="formula_activation_ledger",
                scenario_or_path_scope=activation.get("assumption_set", ""),
                period_or_horizon=activation.get("horizon", ""),
                value_role="active_formula_input",
                current_value_exact=activation.get("parameter_value", ""),
                formula_role=activation.get("placement_layer", ""),
                enters_canonical_ratio=_bool_text(
                    activation.get("placement_layer", "") == "canonical_static_ratio"
                ),
                enters_split_denominator=_bool_text(
                    "split_denominator" in activation.get("active_formula_family", "")
                    or handle in SPLIT_DENOMINATOR_HANDLES
                    or handle == "contractionary_drag_gdp_share"
                ),
                source_status_raw=activation.get("parameter_pack_coverage_status", ""),
                calibration_status_raw=pack.get("calibration_status", ""),
                evidence_strength_raw=pack.get("evidence_strength", ""),
                prior_basis_raw=pack.get("prior_basis", ""),
                ratewall_use_status_raw=activation.get("activation_status", ""),
                claim_boundary_raw=activation.get("claim_boundary", ""),
                source_artifact="ratewall_assumption_mode_parameter_activation_ledger.csv",
                source_field_or_series=handle,
                source_family=pack.get("source_family", ""),
                allowed_use="active_formula_accounting_with_source_classification",
                claim_boundary=activation.get("claim_boundary", ""),
                linked_source_tables="ratewall_parameter_packs.csv",
            )
        )

    rows.extend(
        _conventional_drag_rows(
            conventional_drag_source_design_gate_rows,
            "ratewall_conventional_drag_source_design_gate.csv",
            "current_assumption_handle",
        )
    )
    rows.extend(
        _conventional_drag_rows(
            conventional_drag_channel_evidence_gap_rows,
            "ratewall_conventional_drag_channel_evidence_gap.csv",
            "current_assumption_handles",
        )
    )
    rows.extend(
        _conventional_drag_rows(
            denominator_calibration_design_gate_rows,
            "ratewall_denominator_calibration_design_gate.csv",
            "target_handle",
        )
    )
    rows.extend(
        _conventional_drag_rows(
            denominator_response_gate_attempt_rows,
            "ratewall_denominator_response_gate_attempt.csv",
            "current_assumption_handle",
        )
    )
    rows.extend(
        _conventional_drag_evidence_tranche_rows(
            conventional_drag_evidence_tranche_rows
        )
    )
    rows.extend(
        _tdsp_current_demand_mapping_rows(
            source_review_rows=tdsp_current_demand_source_review_rows,
            unit_conversion_rows=tdsp_current_demand_unit_conversion_rows,
            diagnostic_mapping_rows=tdsp_current_demand_diagnostic_mapping_rows,
            policy_path_blocker_rows=tdsp_policy_path_normalization_blocker_rows,
        )
    )
    rows.extend(
        _tdsp_pce_dpi_policy_path_rows(
            source_refresh_contract_rows=pce_dpi_source_refresh_contract_rows,
            refresh_diagnostic_mapping_rows=(
                tdsp_pce_dpi_refresh_diagnostic_mapping_rows
            ),
            policy_path_design_gate_rows=policy_path_exposure_vector_design_gate_rows,
        )
    )
    rows.extend(
        _policy_path_reviewed_protocol_source_context_rows(
            policy_path_reviewed_protocol_source_context_rows
        )
    )
    rows.extend(
        _policy_path_protocol_source_acquisition_rows(
            policy_path_protocol_source_acquisition_rows
        )
    )
    rows.extend(
        _policy_path_protocol_review_inventory_rows(
            policy_path_protocol_review_inventory_rows
        )
    )
    rows.extend(
        _policy_path_mps_scalar_replication_rows(
            policy_path_mps_scalar_replication_diagnostic_rows
        )
    )
    rows.extend(
        _policy_path_bps_year_blocker_decision_rows(
            policy_path_bps_year_blocker_decision_rows
        )
    )
    rows.extend(
        _policy_path_event_level_candidate_vector_rows(
            policy_path_event_level_candidate_vector_rows
        )
    )
    rows.extend(
        _policy_path_contract_interval_source_review_rows(
            policy_path_contract_interval_source_review_rows
        )
    )
    rows.extend(
        _policy_path_contract_spec_acquisition_blocker_rows(
            policy_path_contract_spec_acquisition_blocker_rows
        )
    )
    rows.extend(
        _policy_path_bps_year_source_protocol_rows(
            policy_path_bps_year_source_protocol_rows
        )
    )
    rows.extend(
        _policy_path_normalization_source_manifest_rows(
            policy_path_normalization_source_manifest_rows
        )
    )
    rows.extend(
        _policy_path_bps_year_normalization_review_rows(
            policy_path_bps_year_normalization_review_rows
        )
    )
    rows.extend(
        _policy_path_source_cell_unit_contract_review_rows(
            policy_path_source_cell_unit_contract_review_rows
        )
    )
    rows.extend(
        _policy_path_bps_year_protocol_closure_rows(
            policy_path_bps_year_protocol_closure_rows
        )
    )
    rows.extend(
        _policy_path_normalization_leak_audit_rows(
            policy_path_normalization_leak_audit_rows
        )
    )
    rows.extend(
        _conventional_drag_research_parameterization_source_contract_rows(
            conventional_drag_research_parameterization_source_contract_rows
        )
    )
    rows.extend(
        _conventional_drag_research_parameterization_source_frontier_rows(
            conventional_drag_research_parameterization_source_frontier_rows
        )
    )
    rows.extend(
        _conventional_drag_research_payload_manifest_rows(
            conventional_drag_research_payload_manifest_rows
        )
    )
    rows.extend(
        _conventional_drag_research_parameterization_parser_status_rows(
            conventional_drag_research_parameterization_parser_status_rows
        )
    )
    rows.extend(
        _conventional_drag_research_payload_inner_inventory_rows(
            conventional_drag_research_payload_inner_inventory_rows
        )
    )
    rows.extend(
        _conventional_drag_research_extraction_candidate_rows(
            conventional_drag_research_extraction_candidate_rows
        )
    )
    rows.extend(
        _conventional_drag_research_extraction_gate_audit_rows(
            conventional_drag_research_extraction_gate_audit_rows
        )
    )
    rows.extend(
        _conventional_drag_research_extraction_gate_detail_rows(
            conventional_drag_research_extraction_gate_detail_rows
        )
    )
    rows.extend(
        _conventional_drag_research_source_method_bridge_rows(
            conventional_drag_research_source_method_bridge_rows
        )
    )
    rows.extend(
        _conventional_drag_research_source_code_interpretation_rows(
            conventional_drag_research_source_code_interpretation_rows
        )
    )
    rows.extend(
        _conventional_drag_research_extended_source_code_interpretation_rows(
            conventional_drag_research_extended_source_code_interpretation_rows
        )
    )
    rows.extend(
        _conventional_drag_research_fspdp_coverage_candidate_scan_rows(
            conventional_drag_research_fspdp_coverage_candidate_scan_rows
        )
    )
    rows.extend(
        _mir_component_aggregation_review_rows(
            mir_component_aggregation_review_rows
        )
    )
    rows.extend(
        _mir_component_source_variant_review_rows(
            mir_component_source_variant_review_rows
        )
    )
    rows.extend(
        _conventional_drag_fspdp_component_decomposition_bridge_rows(
            conventional_drag_fspdp_component_decomposition_bridge_rows
        )
    )
    rows.extend(
        _conventional_drag_fspdp_coverage_weight_requirement_review_rows(
            conventional_drag_fspdp_coverage_weight_requirement_review_rows
        )
    )
    rows.extend(
        _conventional_drag_fspdp_coverage_priority_search_queue_rows(
            conventional_drag_fspdp_coverage_priority_search_queue_rows
        )
    )
    rows.extend(
        _conventional_drag_fspdp_source_code_search_review_rows(
            conventional_drag_fspdp_source_code_search_review_rows
        )
    )
    rows.extend(
        _conventional_drag_fspdp_external_source_acquisition_action_plan_rows(
            conventional_drag_fspdp_external_source_acquisition_action_plan_rows
        )
    )
    rows.extend(
        _conventional_drag_fspdp_official_component_source_acquisition_execution_rows(
            conventional_drag_fspdp_official_component_source_acquisition_execution_rows
        )
    )
    rows.extend(
        _conventional_drag_fspdp_research_side_action_plan_extraction_review_rows(
            conventional_drag_fspdp_research_side_action_plan_extraction_review_rows
        )
    )
    rows.extend(
        _conventional_drag_research_source_unit_conversion_review_rows(
            conventional_drag_research_source_unit_conversion_review_rows
        )
    )
    rows.extend(
        _conventional_drag_research_mir_replication_source_unit_audit_rows(
            conventional_drag_research_mir_replication_source_unit_audit_rows
        )
    )
    rows.extend(
        _conventional_drag_research_mir_source_unit_transformation_contract_rows(
            conventional_drag_research_mir_source_unit_transformation_contract_rows
        )
    )
    rows.extend(
        _conventional_drag_research_mir_target_horizon_reconciliation_contract_rows(
            conventional_drag_research_mir_target_horizon_reconciliation_contract_rows
        )
    )
    rows.extend(
        _conventional_drag_research_mir_horizon_rekeying_candidate_review_rows(
            conventional_drag_research_mir_horizon_rekeying_candidate_review_rows
        )
    )
    rows.extend(
        _conventional_drag_research_mir_h24_source_unit_audit_rows(
            conventional_drag_research_mir_h24_source_unit_audit_rows
        )
    )
    rows.extend(
        _conventional_drag_research_mir_h24_8q_rekeying_review_rows(
            conventional_drag_research_mir_h24_8q_rekeying_review_rows
        )
    )
    rows.extend(
        _conventional_drag_research_mir_4q8q_conversion_readiness_review_rows(
            conventional_drag_research_mir_4q8q_conversion_readiness_review_rows
        )
    )
    rows.extend(
        _conventional_drag_research_policy_path_normalization_bridge_review_rows(
            conventional_drag_research_policy_path_normalization_bridge_review_rows
        )
    )
    rows.extend(
        _policy_path_research_shock_source_evidence_protocol_review_rows(
            policy_path_research_shock_source_evidence_protocol_review_rows
        )
    )
    rows.extend(
        _policy_path_source_code_workbook_object_inventory_rows(
            policy_path_source_code_workbook_object_inventory_rows
        )
    )
    rows.extend(
        _policy_path_source_code_workbook_protocol_deep_review_rows(
            policy_path_source_code_workbook_protocol_deep_review_rows
        )
    )
    rows.extend(
        _policy_path_usmpd_pca_loading_backtransform_review_rows(
            policy_path_usmpd_pca_loading_backtransform_review_rows
        )
    )
    rows.extend(
        _policy_path_usmpd_scalar_score_replication_review_rows(
            policy_path_usmpd_scalar_score_replication_review_rows
        )
    )
    rows.extend(
        _policy_path_usmpd_pca_backtransform_gate_review_rows(
            policy_path_usmpd_pca_backtransform_gate_review_rows
        )
    )
    rows.extend(
        _policy_path_usmpd_instrument_decomposition_design_review_rows(
            policy_path_usmpd_instrument_decomposition_design_review_rows
        )
    )
    rows.extend(
        _policy_path_bps_year_candidate_path_design_contract_rows(
            policy_path_bps_year_candidate_path_design_contract_rows
        )
    )
    rows.extend(
        _policy_path_formula_replication_source_review_rows(
            policy_path_formula_replication_source_review_rows
        )
    )
    rows.extend(
        _policy_path_reviewed_bps_year_protocol_gap_matrix_rows(
            policy_path_reviewed_bps_year_protocol_gap_matrix_rows
        )
    )
    rows.extend(
        _policy_path_protocol_source_acquisition_work_queue_rows(
            policy_path_protocol_source_acquisition_work_queue_rows
        )
    )
    rows.extend(
        _policy_path_protocol_source_parse_execution_review_rows(
            policy_path_protocol_source_parse_execution_review_rows
        )
    )
    rows.extend(
        _policy_path_source_parse_synthesis_queue_rows(
            policy_path_source_parse_synthesis_queue_rows
        )
    )
    rows.extend(
        _policy_path_source_parse_action_execution_rows(
            policy_path_source_parse_action_execution_rows
        )
    )
    rows.extend(
        _policy_path_deeper_parse_execution_review_rows(
            policy_path_deeper_parse_execution_review_rows
        )
    )
    rows.extend(
        _policy_path_protocol_candidate_draft_review_rows(
            policy_path_protocol_candidate_draft_review_rows
        )
    )
    rows.extend(
        _policy_path_protocol_missing_evidence_acquisition_queue_rows(
            policy_path_protocol_missing_evidence_acquisition_queue_rows
        )
    )
    rows.extend(
        _policy_path_protocol_missing_evidence_parse_execution_review_rows(
            policy_path_protocol_missing_evidence_parse_execution_review_rows
        )
    )
    rows.extend(
        _policy_path_protocol_authoring_readiness_matrix_rows(
            policy_path_protocol_authoring_readiness_matrix_rows
        )
    )
    rows.extend(
        _policy_path_protocol_field_authoring_contract_rows(
            policy_path_protocol_field_authoring_contract_rows
        )
    )
    rows.extend(
        _policy_path_field_evidence_resolution_queue_rows(
            policy_path_field_evidence_resolution_queue_rows
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            ratio_layer_registry_rows,
            assumption_family="ratio_layer_registry",
            artifact_or_surface="ratewall_ratio_layer_registry.csv",
            id_field="ratio_layer_registry_row_id",
            source_field="ratio_id",
            source_family="RateWall ratio-layer registry",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            estimation_target_registry_rows,
            assumption_family="estimation_target_registry",
            artifact_or_surface="ratewall_estimation_target_registry.csv",
            id_field="estimation_target_registry_row_id",
            source_field="object_id",
            source_family="RateWall estimation-target registry",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            channel_taxonomy_registry_rows,
            assumption_family="channel_taxonomy_registry",
            artifact_or_surface="ratewall_channel_taxonomy_registry.csv",
            id_field="channel_taxonomy_registry_row_id",
            source_field="channel_id",
            source_family="RateWall channel taxonomy registry",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            historical_interpretation_audit_rows,
            assumption_family="historical_interpretation_audit",
            artifact_or_surface="ratewall_historical_interpretation_audit.csv",
            id_field="historical_interpretation_audit_row_id",
            source_field="artifact_name",
            source_family="RateWall historical interpretation audit",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            tdc_equation_variant_registry_rows,
            assumption_family="tdc_equation_variant_registry",
            artifact_or_surface="ratewall_tdc_equation_variant_registry.csv",
            id_field="tdc_equation_variant_registry_row_id",
            source_field="tdc_variant_id",
            source_family="RateWall TDC equation-variant registry",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_extraction_task_packet_rows,
            assumption_family="policy_path_source_extraction_task_packet",
            artifact_or_surface="ratewall_policy_path_source_extraction_task_packet.csv",
            id_field="policy_path_source_extraction_task_packet_row_id",
            source_field="authored_field_name",
            source_family="policy-path source extraction task packet",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_extraction_results_rows,
            assumption_family="policy_path_source_extraction_results",
            artifact_or_surface="ratewall_policy_path_source_extraction_results.csv",
            id_field="policy_path_source_extraction_result_row_id",
            source_field="authored_field_name",
            source_family="policy-path source extraction execution results",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_authored_protocol_completion_audit_rows,
            assumption_family="policy_path_authored_protocol_completion_audit",
            artifact_or_surface=(
                "ratewall_policy_path_authored_protocol_completion_audit.csv"
            ),
            id_field="policy_path_authored_protocol_completion_audit_row_id",
            source_field="authored_field_name",
            source_family="policy-path authored protocol completion audit",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_protocol_completion_design_tranche_rows,
            assumption_family="policy_path_protocol_completion_design_tranche",
            artifact_or_surface=(
                "ratewall_policy_path_protocol_completion_design_tranche.csv"
            ),
            id_field="policy_path_protocol_completion_design_tranche_row_id",
            source_field="authored_field_name",
            source_family="policy-path protocol completion design tranche",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_field_specific_pass_rule_design_rows,
            assumption_family="policy_path_field_specific_pass_rule_design",
            artifact_or_surface=(
                "ratewall_policy_path_field_specific_pass_rule_design.csv"
            ),
            id_field="policy_path_field_specific_pass_rule_design_row_id",
            source_field="authored_field_name",
            source_family="policy-path field-specific pass-rule design",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_field_specific_source_evidence_audit_rows,
            assumption_family="policy_path_field_specific_source_evidence_audit",
            artifact_or_surface=(
                "ratewall_policy_path_field_specific_source_evidence_audit.csv"
            ),
            id_field="policy_path_field_specific_source_evidence_audit_row_id",
            source_field="authored_field_name",
            source_family="policy-path field-specific source-evidence audit",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_locator_binding_review_rows,
            assumption_family="policy_path_source_locator_binding_review",
            artifact_or_surface=(
                "ratewall_policy_path_source_locator_binding_review.csv"
            ),
            id_field="policy_path_source_locator_binding_review_row_id",
            source_field="linked_source_hit_row_id",
            source_family="policy-path source locator binding review",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_exact_source_locator_remediation_rows,
            assumption_family="policy_path_exact_source_locator_remediation",
            artifact_or_surface=(
                "ratewall_policy_path_exact_source_locator_remediation.csv"
            ),
            id_field="policy_path_exact_source_locator_remediation_row_id",
            source_field="exact_source_locator",
            source_family="policy-path exact source locator remediation",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_exact_locator_field_closure_diagnostic_rows,
            assumption_family="policy_path_exact_locator_field_closure_diagnostic",
            artifact_or_surface=(
                "ratewall_policy_path_exact_locator_field_closure_diagnostic.csv"
            ),
            id_field="policy_path_exact_locator_field_closure_diagnostic_row_id",
            source_field="authored_field_name",
            source_family="policy-path exact locator field closure diagnostic",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_exact_locator_pass_rule_adjudication_rows,
            assumption_family="policy_path_exact_locator_pass_rule_adjudication",
            artifact_or_surface=(
                "ratewall_policy_path_exact_locator_pass_rule_adjudication.csv"
            ),
            id_field="policy_path_exact_locator_pass_rule_adjudication_row_id",
            source_field="adjudicated_missing_evidence_class",
            source_family="policy-path exact locator pass-rule adjudication",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_terminal_no_hit_closure_rows,
            assumption_family="policy_path_terminal_no_hit_closure",
            artifact_or_surface="ratewall_policy_path_terminal_no_hit_closure.csv",
            id_field="policy_path_terminal_no_hit_closure_row_id",
            source_field="source_bundle_closure_status",
            source_family="policy-path terminal no-hit closure",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_independent_replication_target_design_rows,
            assumption_family="policy_path_independent_replication_target_design",
            artifact_or_surface=(
                "ratewall_policy_path_independent_replication_target_design.csv"
            ),
            id_field="policy_path_independent_replication_target_design_row_id",
            source_field="required_output_field",
            source_family="policy-path independent replication target design",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_authored_fail_closed_invariant_design_rows,
            assumption_family="policy_path_authored_fail_closed_invariant_design",
            artifact_or_surface=(
                "ratewall_policy_path_authored_fail_closed_invariant_design.csv"
            ),
            id_field="policy_path_authored_fail_closed_invariant_design_row_id",
            source_field="required_output_field",
            source_family="policy-path authored fail-closed invariant design",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_protocol_component_closure_rollup_rows,
            assumption_family="policy_path_protocol_component_closure_rollup",
            artifact_or_surface=(
                "ratewall_policy_path_protocol_component_closure_rollup.csv"
            ),
            id_field="policy_path_protocol_component_closure_rollup_row_id",
            source_field="protocol_component",
            source_family="policy-path protocol component closure rollup",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_locator_binding_closure_diagnostic_rows,
            assumption_family="policy_path_locator_binding_closure_diagnostic",
            artifact_or_surface=(
                "ratewall_policy_path_locator_binding_closure_diagnostic.csv"
            ),
            id_field="policy_path_locator_binding_closure_diagnostic_row_id",
            source_field="protocol_component",
            source_family="policy-path locator binding closure diagnostic",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_full_protocol_admission_gate_summary_rows,
            assumption_family="policy_path_full_protocol_admission_gate_summary",
            artifact_or_surface=(
                "ratewall_policy_path_full_protocol_admission_gate_summary.csv"
            ),
            id_field="policy_path_full_protocol_admission_gate_summary_row_id",
            source_field="protocol_id",
            source_family="policy-path full-protocol admission gate summary",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_bundle_field_exhaustion_decision_rows,
            assumption_family="policy_path_source_bundle_field_exhaustion_decision",
            artifact_or_surface=(
                "ratewall_policy_path_source_bundle_field_exhaustion_decision.csv"
            ),
            id_field="policy_path_source_bundle_field_exhaustion_decision_row_id",
            source_field="field_decision_class",
            source_family="policy-path source-bundle field exhaustion decision",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_bundle_component_exhaustion_decision_rows,
            assumption_family="policy_path_source_bundle_component_exhaustion_decision",
            artifact_or_surface=(
                "ratewall_policy_path_source_bundle_component_exhaustion_decision.csv"
            ),
            id_field="policy_path_source_bundle_component_exhaustion_decision_row_id",
            source_field="component_decision_class",
            source_family="policy-path source-bundle component exhaustion decision",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            conventional_drag_empirical_target_registry_rows,
            assumption_family="conventional_drag_empirical_target_registry",
            artifact_or_surface=(
                "ratewall_conventional_drag_empirical_target_registry.csv"
            ),
            id_field="conventional_drag_empirical_target_registry_row_id",
            source_field="route_id",
            source_family="conventional-drag empirical target registry",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            conventional_drag_route_pruning_audit_rows,
            assumption_family="conventional_drag_route_pruning_audit",
            artifact_or_surface="ratewall_conventional_drag_route_pruning_audit.csv",
            id_field="conventional_drag_route_pruning_audit_row_id",
            source_field="route_id",
            source_family="conventional-drag route pruning audit",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            conventional_drag_response_design_gate_rows,
            assumption_family="conventional_drag_response_design_gate",
            artifact_or_surface="ratewall_conventional_drag_response_design_gate.csv",
            id_field="conventional_drag_response_design_gate_row_id",
            source_field="design_gate",
            source_family="conventional-drag response design gate",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            denominator_response_estimate_registry_rows,
            assumption_family="denominator_response_estimate_registry",
            artifact_or_surface="ratewall_denominator_response_estimate_registry.csv",
            id_field="denominator_response_estimate_registry_row_id",
            source_field="estimator_id",
            source_family="denominator response-estimate registry",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            denominator_formal_design_gate_rows,
            assumption_family="denominator_formal_design_gate",
            artifact_or_surface="ratewall_denominator_formal_design_gate.csv",
            id_field="denominator_formal_design_gate_row_id",
            source_field="design_gate",
            source_family="denominator formal design gate",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            conventional_drag_response_execution_readiness_packet_rows,
            assumption_family="conventional_drag_response_execution_readiness_packet",
            artifact_or_surface=(
                "ratewall_conventional_drag_response_execution_readiness_packet.csv"
            ),
            id_field="conventional_drag_response_execution_readiness_packet_row_id",
            source_field="execution_route_class",
            source_family="conventional-drag response execution readiness packet",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            local_lp_proxy_svar_diagnostic_run_packet_rows,
            assumption_family="local_lp_proxy_svar_diagnostic_run_packet",
            artifact_or_surface=(
                "ratewall_local_lp_proxy_svar_diagnostic_run_packet.csv"
            ),
            id_field="local_lp_proxy_svar_diagnostic_run_packet_row_id",
            source_field="run_task_class",
            source_family="local LP / proxy-SVAR diagnostic run packet",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            local_lp_proxy_svar_execution_preflight_results_rows,
            assumption_family="local_lp_proxy_svar_execution_preflight_results",
            artifact_or_surface=(
                "ratewall_local_lp_proxy_svar_execution_preflight_results.csv"
            ),
            id_field="local_lp_proxy_svar_execution_preflight_results_row_id",
            source_field="execution_result_status",
            source_family="local LP / proxy-SVAR execution preflight results",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            local_lp_proxy_svar_route_closure_decision_rows,
            assumption_family="local_lp_proxy_svar_route_closure_decision",
            artifact_or_surface=(
                "ratewall_local_lp_proxy_svar_route_closure_decision.csv"
            ),
            id_field="local_lp_proxy_svar_route_closure_decision_row_id",
            source_field="route_closure_status",
            source_family="local LP / proxy-SVAR route closure decision",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            conventional_drag_denominator_route_triage_synthesis_rows,
            assumption_family=(
                "conventional_drag_denominator_route_triage_synthesis"
            ),
            artifact_or_surface=(
                "ratewall_conventional_drag_denominator_route_triage_synthesis.csv"
            ),
            id_field="conventional_drag_denominator_route_triage_synthesis_row_id",
            source_field="route_triage_status",
            source_family="conventional-drag denominator route triage synthesis",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_100bp_year_blocker_action_resolution_rows,
            assumption_family="policy_path_100bp_year_blocker_action_resolution",
            artifact_or_surface=(
                "ratewall_policy_path_100bp_year_blocker_action_resolution.csv"
            ),
            id_field="policy_path_100bp_year_blocker_action_resolution_row_id",
            source_field="action_resolution_class",
            source_family="policy-path 100bp-year blocker action resolution",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_protocol_action_packet_rows,
            assumption_family="policy_path_source_protocol_action_packet",
            artifact_or_surface=(
                "ratewall_policy_path_source_protocol_action_packet.csv"
            ),
            id_field="policy_path_source_protocol_action_packet_row_id",
            source_field="source_protocol_action_class",
            source_family="policy-path source-protocol action packet",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_protocol_pass_rule_harness_rows,
            assumption_family="policy_path_source_protocol_pass_rule_harness",
            artifact_or_surface=(
                "ratewall_policy_path_source_protocol_pass_rule_harness.csv"
            ),
            id_field="policy_path_source_protocol_pass_rule_harness_row_id",
            source_field="harness_task_class",
            source_family="policy-path source-protocol pass-rule harness",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_protocol_extraction_attempt_results_rows,
            assumption_family=(
                "policy_path_source_protocol_extraction_attempt_results"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_source_protocol_extraction_attempt_results.csv"
            ),
            id_field="policy_path_source_protocol_extraction_attempt_result_row_id",
            source_field="attempt_task_class",
            source_family="policy-path source-protocol extraction attempt results",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_protocol_attempt_closure_handoff_rows,
            assumption_family=(
                "policy_path_source_protocol_attempt_closure_handoff"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_source_protocol_attempt_closure_handoff.csv"
            ),
            id_field="policy_path_source_protocol_attempt_closure_handoff_row_id",
            source_field="closure_handoff_class",
            source_family="policy-path source-protocol attempt closure handoff",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_promotion_grade_source_family_acquisition_packet_rows,
            assumption_family=(
                "policy_path_promotion_grade_source_family_acquisition_packet"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_promotion_grade_source_family_acquisition_packet.csv"
            ),
            id_field=(
                "policy_path_promotion_grade_source_family_acquisition_packet_row_id"
            ),
            source_field="acquisition_task_class",
            source_family=(
                "policy-path promotion-grade source-family acquisition packet"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_promotion_grade_source_family_acquisition_execution_preflight_results_rows,
            assumption_family=(
                "policy_path_promotion_grade_source_family_acquisition_execution_preflight_results"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_promotion_grade_source_family_acquisition_execution_preflight_results.csv"
            ),
            id_field=(
                "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id"
            ),
            source_field="execution_preflight_class",
            source_family=(
                "policy-path promotion-grade source-family acquisition execution preflight results"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_family_execution_closure_selection_packet_rows,
            assumption_family=(
                "policy_path_source_family_execution_closure_selection_packet"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_source_family_execution_closure_selection_packet.csv"
            ),
            id_field=(
                "policy_path_source_family_execution_closure_selection_packet_row_id"
            ),
            source_field="selected_execution_route",
            source_family=(
                "policy-path source-family execution closure selection packet"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_current_artifact_manual_review_execution_packet_rows,
            assumption_family=(
                "policy_path_current_artifact_manual_review_execution_packet"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_current_artifact_manual_review_execution_packet.csv"
            ),
            id_field=(
                "policy_path_current_artifact_manual_review_execution_packet_row_id"
            ),
            source_field="manual_review_execution_class",
            source_family=(
                "policy-path current-artifact manual-review execution packet"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_current_artifact_manual_review_result_attempt_rows,
            assumption_family=(
                "policy_path_current_artifact_manual_review_result_attempt"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_current_artifact_manual_review_result_attempt.csv"
            ),
            id_field=(
                "policy_path_current_artifact_manual_review_result_attempt_row_id"
            ),
            source_field="manual_review_attempt_class",
            source_family=(
                "policy-path current-artifact manual-review result attempt"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_author_manual_acquisition_followup_packet_rows,
            assumption_family=(
                "policy_path_source_author_manual_acquisition_followup_packet"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_source_author_manual_acquisition_followup_packet.csv"
            ),
            id_field=(
                "policy_path_source_author_manual_acquisition_followup_packet_row_id"
            ),
            source_field="followup_task_class",
            source_family=(
                "policy-path source-author/manual acquisition follow-up packet"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_author_manual_acquisition_execution_preflight_results_rows,
            assumption_family=(
                "policy_path_source_author_manual_acquisition_execution_preflight_results"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_source_author_manual_acquisition_execution_preflight_results.csv"
            ),
            id_field=(
                "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id"
            ),
            source_field="acquisition_execution_preflight_class",
            source_family=(
                "policy-path source-author/manual acquisition execution preflight results"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_real_source_author_web_acquisition_attempt_packet_rows,
            assumption_family=(
                "policy_path_real_source_author_web_acquisition_attempt_packet"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_real_source_author_web_acquisition_attempt_packet.csv"
            ),
            id_field=(
                "policy_path_real_source_author_web_acquisition_attempt_packet_row_id"
            ),
            source_field="bounded_attempt_class",
            source_family=(
                "policy-path real source-author web acquisition attempt packet"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_downloaded_artifact_locator_parse_adjudication_packet_rows,
            assumption_family=(
                "policy_path_downloaded_artifact_locator_parse_adjudication_packet"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_downloaded_artifact_locator_parse_adjudication_packet.csv"
            ),
            id_field=(
                "policy_path_downloaded_artifact_locator_parse_adjudication_packet_row_id"
            ),
            source_field="parse_attempt_class",
            source_family=(
                "policy-path downloaded artifact locator parse adjudication packet"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_locator_candidate_pass_rule_review_decision_packet_rows,
            assumption_family=(
                "policy_path_locator_candidate_pass_rule_review_decision_packet"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_locator_candidate_pass_rule_review_decision_packet.csv"
            ),
            id_field=(
                "policy_path_locator_candidate_pass_rule_review_decision_packet_row_id"
            ),
            source_field="pass_rule_review_class",
            source_family=(
                "policy-path locator candidate pass-rule review decision packet"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_source_extraction_result_adjudication_rows,
            assumption_family="policy_path_source_extraction_result_adjudication",
            artifact_or_surface=(
                "ratewall_policy_path_source_extraction_result_adjudication.csv"
            ),
            id_field="policy_path_source_extraction_result_adjudication_row_id",
            source_field="field_gate_status",
            source_family="policy-path source extraction result adjudication",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_component_gate_execution_rollup_rows,
            assumption_family="policy_path_component_gate_execution_rollup",
            artifact_or_surface=(
                "ratewall_policy_path_component_gate_execution_rollup.csv"
            ),
            id_field="policy_path_component_gate_execution_rollup_row_id",
            source_field="component_gate_status",
            source_family="policy-path component gate execution rollup",
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_project_authored_bps_year_protocol_contract_rows,
            assumption_family=(
                "policy_path_project_authored_bps_year_protocol_contract"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_project_authored_bps_year_protocol_contract.csv"
            ),
            id_field="project_authored_bps_year_protocol_contract_row_id",
            source_field="protocol_contract_status",
            source_family=(
                "policy-path project-authored bps-year protocol contract"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_project_authored_bps_year_source_input_contract_rows,
            assumption_family=(
                "policy_path_project_authored_bps_year_source_input_contract"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_project_authored_bps_year_source_input_contract.csv"
            ),
            id_field="project_authored_bps_year_source_input_contract_row_id",
            source_field="source_input_status",
            source_family=(
                "policy-path project-authored bps-year source-input contract"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_project_authored_bps_year_replication_protocol_rows,
            assumption_family=(
                "policy_path_project_authored_bps_year_replication_protocol"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_project_authored_bps_year_replication_protocol.csv"
            ),
            id_field="project_authored_bps_year_replication_protocol_row_id",
            source_field="replication_protocol_status",
            source_family=(
                "policy-path project-authored bps-year replication protocol"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_project_authored_bps_year_event_exposure_rows,
            assumption_family=(
                "policy_path_project_authored_bps_year_event_exposure"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_project_authored_bps_year_event_exposure.csv"
            ),
            id_field="project_authored_bps_year_event_exposure_row_id",
            source_field="event_exposure_row_status",
            source_family=(
                "policy-path project-authored bps-year event exposure"
            ),
        )
    )
    rows.extend(
        _architecture_lock_surface_rows(
            policy_path_project_authored_bps_year_exposure_admission_consumer_rows,
            assumption_family=(
                "policy_path_project_authored_bps_year_exposure_admission_consumer"
            ),
            artifact_or_surface=(
                "ratewall_policy_path_project_authored_bps_year_exposure_admission_consumer.csv"
            ),
            id_field="project_authored_bps_year_exposure_admission_consumer_row_id",
            source_field="exposure_admission_decision",
            source_family=(
                "policy-path project-authored bps-year exposure admission consumer"
            ),
        )
    )
    rows.extend(
        _value_bearing_bps_year_exposure_export_rows(
            policy_path_value_bearing_bps_year_exposure_export_rows
        )
    )
    rows.extend(
        _value_bearing_bps_year_exposure_quarterly_series_rows(
            policy_path_value_bearing_bps_year_exposure_quarterly_series_rows
        )
    )
    rows.extend(
        _conventional_drag_fspdp_component_source_manifest_rows(
            conventional_drag_fspdp_component_source_manifest_rows
        )
    )
    rows.extend(
        _conventional_drag_fspdp_component_share_panel_rows(
            conventional_drag_fspdp_component_share_panel_rows
        )
    )
    rows.extend(
        _current_demand_gdp_share_source_manifest_rows(
            current_demand_gdp_share_source_manifest_rows
        )
    )
    rows.extend(_current_demand_gdp_share_panel_rows(current_demand_gdp_share_panel_rows))
    rows.extend(
        _conventional_drag_current_demand_mapping_bridge_rows(
            conventional_drag_current_demand_mapping_bridge_rows
        )
    )
    rows.extend(
        _conventional_drag_research_extraction_conversion_bridge_rows(
            conventional_drag_research_extraction_conversion_bridge_rows
        )
    )
    rows.extend(
        _conventional_drag_local_lp_rows(
            macro_panel_rows=conventional_drag_local_macro_panel_rows,
            shock_quarterly_rows=conventional_drag_local_shock_quarterly_rows,
            lp_design_rows=conventional_drag_local_lp_design_rows,
            lp_diagnostic_rows=conventional_drag_local_lp_diagnostic_rows,
            lp_estimate_diagnostic_rows=(
                conventional_drag_local_lp_estimate_diagnostic_rows
            ),
            lp_robustness_diagnostic_rows=(
                conventional_drag_local_lp_robustness_diagnostic_rows
            ),
            lp_sample_window_audit_rows=conventional_drag_local_lp_sample_window_audit_rows,
            lp_admission_audit_rows=conventional_drag_local_lp_admission_audit_rows,
            fspdp_denominator_readiness_gate_rows=(
                conventional_drag_fspdp_denominator_readiness_gate_rows
            ),
            fspdp_denominator_candidate_join_preflight_rows=(
                conventional_drag_fspdp_denominator_candidate_join_preflight_rows
            ),
            fspdp_value_bearing_exposure_lp_execution_rows=(
                conventional_drag_fspdp_value_bearing_exposure_lp_execution_rows
            ),
            fspdp_denominator_conversion_uncertainty_boundary_rows=(
                conventional_drag_fspdp_denominator_conversion_uncertainty_boundary_rows
            ),
            fspdp_gdp_share_conversion_design_gate_rows=(
                conventional_drag_fspdp_gdp_share_conversion_design_gate_rows
            ),
            fspdp_gdp_share_conversion_method_admission_rows=(
                conventional_drag_fspdp_gdp_share_conversion_method_admission_rows
            ),
            fspdp_lp_sample_base_share_join_rows=(
                conventional_drag_fspdp_lp_sample_base_share_join_rows
            ),
            fspdp_gdp_share_conversion_sensitivity_rows=(
                conventional_drag_fspdp_gdp_share_conversion_sensitivity_rows
            ),
            fspdp_lp_sample_share_closeout_decision_rows=(
                conventional_drag_fspdp_lp_sample_share_closeout_decision_rows
            ),
        )
    )
    rows.extend(
        _openicpsr_replication_package_source_manifest_rows(
            openicpsr_replication_package_source_manifest_rows
        )
    )
    rows.extend(
        _frbus_model_benchmark_simulation_readiness_rows(
            frbus_model_benchmark_simulation_readiness_rows
        )
    )
    rows.extend(
        _frbus_conventional_drag_benchmark_protocol_rows(
            frbus_conventional_drag_benchmark_protocol_rows
        )
    )
    rows.extend(
        _frbus_official_model_package_inventory_rows(
            frbus_official_model_package_inventory_rows
        )
    )
    rows.extend(
        _frbus_official_model_benchmark_simulation_protocol_rows(
            frbus_official_model_benchmark_simulation_protocol_rows
        )
    )
    rows.extend(_frbus_runtime_runner_preflight_rows(frbus_runtime_runner_preflight_rows))
    rows.extend(
        _frbus_runtime_runner_output_slots_rows(frbus_runtime_runner_output_slots_rows)
    )
    rows.extend(
        _frbus_benchmark_comparison_mapping_contract_rows(
            frbus_benchmark_comparison_mapping_contract_rows
        )
    )
    rows.extend(
        _frbus_benchmark_output_slot_extension_review_rows(
            frbus_benchmark_output_slot_extension_review_rows
        )
    )
    rows.extend(
        _conventional_drag_source_unit_aggregation_blocker_bridge_rows(
            conventional_drag_source_unit_aggregation_blocker_bridge_rows
        )
    )
    rows.extend(
        _conventional_drag_mirgk_targeted_gap_source_followup_rows(
            conventional_drag_mirgk_targeted_gap_source_followup_rows
        )
    )
    rows.extend(
        _conventional_drag_promotion_contract_checklist_rows(
            conventional_drag_promotion_contract_checklist_rows
        )
    )
    rows.extend(
        _backend_schema_release_audit_rows(
            backend_surface_schema_contract_rows,
            artifact="ratewall_backend_surface_schema_contract.csv",
            family="backend_surface_schema_contract",
            surface_type="backend_schema_contract_surface",
            row_key="schema_row_id",
            status_field="schema_contract_status",
        )
    )
    rows.extend(
        _backend_schema_release_audit_rows(
            backend_artifact_claim_boundary_manifest_rows,
            artifact="ratewall_backend_artifact_claim_boundary_manifest.csv",
            family="backend_artifact_claim_boundary_manifest",
            surface_type="artifact_claim_boundary_manifest_surface",
            row_key="manifest_row_id",
            status_field="artifact_claim_boundary_status",
        )
    )
    rows.extend(
        _backend_schema_release_audit_rows(
            release_archive_reproducibility_audit_rows,
            artifact="ratewall_release_archive_reproducibility_audit.csv",
            family="release_archive_reproducibility_audit",
            surface_type="release_archive_reproducibility_audit_surface",
            row_key="archive_audit_row_id",
            status_field="archive_reproducibility_status",
        )
    )
    for row in conventional_drag_decomposition_rows:
        component = row.get("denominator_component", "")
        handle = _component_to_split_handle(component)
        rows.append(
            _row(
                assumption_handle=handle,
                assumption_family="conventional_drag_denominator",
                artifact_or_surface="ratewall_conventional_drag_decomposition.csv",
                surface_type="split_denominator_output",
                scenario_or_path_scope=row.get("assumption_set", ""),
                period_or_horizon=row.get("horizon", ""),
                value_role="split_denominator_component_value",
                current_value_exact=row.get("component_value_bil", ""),
                current_value_base=row.get("share_of_scalar_denominator", ""),
                unit="bil_or_share",
                formula_role=component,
                enters_split_denominator="true",
                source_status_raw="split_denominator_assumption_prior",
                evidence_strength_raw="weak_literature_context_not_source_backed",
                source_artifact="ratewall_conventional_drag_decomposition.csv",
                source_field_or_series=component,
                source_family="conventional_drag_decomposition",
                evidence_needed_before_prior_narrowing=(
                    "channel-separated response estimates rather than residual "
                    "share assignment"
                ),
                promotion_gate=(
                    "requires admissible shock channel estimates and support "
                    "diagnostics"
                ),
                promotion_status="blocked",
                prior_narrowing_allowed="false",
                split_denominator_promotion_allowed="false",
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_source_design_gate.csv;"
                    "ratewall_parameter_packs.csv"
                ),
            )
        )

    for row in interest_income_mpc_calibration_registry_rows:
        rows.append(
            _row(
                assumption_handle=row.get("source_id", ""),
                assumption_family="interest_income_current_spend_anchor",
                artifact_or_surface="ratewall_interest_income_mpc_calibration_registry.csv",
                surface_type="literature_registry",
                value_role="literature_anchor",
                current_value_low=row.get("estimate_low", ""),
                current_value_base=row.get("estimate_point", ""),
                current_value_high=row.get("estimate_high", ""),
                unit=row.get("estimate_units", ""),
                source_status_raw=row.get("ratewall_use_status", ""),
                evidence_strength_raw=row.get("evidence_strength", ""),
                ratewall_use_status_raw=row.get("ratewall_use_status", ""),
                source_artifact=row.get("source_url", ""),
                source_field_or_series=row.get("measured_object", ""),
                source_family=row.get("source_type", ""),
                literature_handle=row.get("citation_short", ""),
                directness_class=row.get("directness_class", ""),
                transport_risk=row.get("transport_risk", ""),
                claim_boundary=row.get("claim_boundary", ""),
                allowed_use="assumption_mode_anchor_only",
                linked_source_tables="ratewall_interest_income_mpc_calibration_registry.csv",
            )
        )

    for row in interest_income_proxy_range_registry_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "interest_income_proxy_range::"
                    f"{row.get('proxy_tier', '')}::{row.get('scenario_band', '')}"
                ),
                assumption_family="interest_income_proxy_range",
                artifact_or_surface="ratewall_interest_income_proxy_range_registry.csv",
                surface_type="proxy_range_registry",
                value_role="proxy_range_assumption",
                current_value_low=row.get("recommended_low", ""),
                current_value_base=row.get("recommended_base", ""),
                current_value_high=row.get("recommended_high", ""),
                unit="current_spend_share",
                source_status_raw=row.get("confidence_label", ""),
                source_artifact=row.get("calibration_source_ids", ""),
                source_field_or_series=row.get("scenario_band", ""),
                allowed_use="assumption_mode_proxy_range",
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_interest_income_proxy_range_registry.csv;"
                    "ratewall_interest_income_mpc_calibration_registry.csv"
                ),
            )
        )

    for row in interest_income_claim_boundary_audit_rows:
        rows.append(
            _artifact_status_row(
                row=row,
                artifact="ratewall_interest_income_claim_boundary_audit.csv",
                handle=row.get("audit_item", "interest_income_claim_boundary"),
                family="interest_income_claim_boundary",
                role="claim_boundary_audit",
            )
        )

    for row in tdc_forward_assumption_registry_rows:
        rows.append(
            _row(
                assumption_handle=row.get("assumption_id", ""),
                assumption_family=row.get("assumption_family", ""),
                artifact_or_surface="ratewall_tdc_forward_assumption_registry.csv",
                surface_type="tdc_forward_assumption_registry",
                value_role="tdc_deposit_conversion_sensitivity",
                current_value_exact=row.get("assumption_value", ""),
                unit="share",
                source_status_raw=row.get("source_status", ""),
                allowed_use=row.get("allowed_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables="ratewall_tdc_forward_assumption_registry.csv",
                **_copy_switches(row),
            )
        )

    for row in tdcsim_projection_contract_bridge_rows:
        rows.append(
            _row(
                assumption_handle="tdcsim_forward_tdc_contract",
                assumption_family="tdcsim_forward_surface",
                artifact_or_surface="ratewall_tdcsim_projection_contract_bridge.csv",
                surface_type="sibling_contract_ingest",
                scenario_or_path_scope=row.get("scenario_id", ""),
                period_or_horizon=row.get("quarter", ""),
                value_role="sibling_contract_projection",
                current_value_exact=row.get("tdc_change_bil", ""),
                unit="bil",
                enters_tdcsim_forward_surface="true",
                source_status_raw=row.get("contract_ingest_status", ""),
                source_artifact="data/raw/ratewall_sibling_calibration/tdcsim",
                source_field_or_series="tdc_change_bil",
                source_family="tdcsim",
                sibling_project="tdcsim",
                sibling_contract_artifact="tdcsim_ratewall_quarterly_summary.csv",
                sibling_contract_version=row.get("tdcsim_contract_version", ""),
                sibling_contract_hash=row.get("tdcsim_manifest_hash", ""),
                source_hash_or_manifest_hash=row.get("tdcsim_manifest_hash", ""),
                allowed_use="noncanonical_assumption_mode_forward_surface",
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables="ratewall_tdcsim_projection_contract_bridge.csv",
                **_copy_switches(row),
            )
        )

    for row in canonical_tdc_accounting_source_hierarchy_audit_rows:
        rows.append(
            _row(
                assumption_handle=row.get("audit_item", ""),
                assumption_family="canonical_tdc_accounting_source_hierarchy",
                artifact_or_surface=(
                    "ratewall_canonical_tdc_accounting_source_hierarchy_audit.csv"
                ),
                surface_type="tdc_accounting_source_audit",
                value_role="canonical_tdc_accounting_source_status",
                enters_canonical_tdc_accounting="true",
                source_status_raw=row.get("audit_status", ""),
                source_artifact=row.get("source_artifact", ""),
                source_field_or_series=row.get("source_family", ""),
                source_family=row.get("source_family", ""),
                allowed_use=row.get("canonical_accounting_status", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_canonical_tdc_accounting_path.csv;"
                    "ratewall_canonical_tdc_stitched_accounting_path.csv"
                ),
                **_copy_switches(row),
            )
        )

    for row in tdc_historical_source_contract_rows:
        rows.append(
            _row(
                assumption_handle=row.get("series_key", ""),
                assumption_family="tdcest_historical_tdc_contract",
                artifact_or_surface="ratewall_tdc_historical_source_contract.csv",
                surface_type="sibling_contract_registry",
                value_role="historical_tdc_source_contract",
                source_status_raw=row.get("source_status", ""),
                source_artifact=row.get("artifact_key", ""),
                source_field_or_series=row.get("series_key", ""),
                source_family=row.get("source_family", ""),
                sibling_project="tdcest",
                sibling_contract_artifact=row.get("artifact_key", ""),
                allowed_use=row.get("default_classification", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables="ratewall_tdc_historical_source_contract.csv",
                **_copy_switches(row),
            )
        )

    for row in tdc_ea_tdc_pass_through_calibration_import_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family="tdc_ea_tdc_pass_through_calibration_import",
                artifact_or_surface=(
                    "ratewall_tdc_ea_tdc_pass_through_calibration_import.csv"
                ),
                surface_type="versioned_sibling_calibration_import",
                upstream_row_key=row.get("calibration_import_row_id", ""),
                scenario_or_path_scope=row.get("source_artifact_role", ""),
                period_or_horizon=row.get("imported_period_or_window", "")
                or row.get("imported_horizon", ""),
                value_role="ea_tdc_pass_through_calibration_review_value",
                current_value_exact=row.get("beta_estimate", ""),
                current_value_low=row.get("beta_lower95", ""),
                current_value_base=row.get("beta_estimate", ""),
                current_value_high=row.get("beta_upper95", ""),
                current_value_range_text=(
                    f"calibration_import_row_id={row.get('calibration_import_row_id', '')}"
                ),
                unit=row.get("normalized_unit", ""),
                enters_dynamic_path="false",
                source_status_raw=row.get("source_admission_status", ""),
                calibration_status_raw=row.get("import_status", ""),
                evidence_strength_raw=row.get("source_artifact_exists", ""),
                prior_basis_raw=row.get("source_row_role", ""),
                ratewall_use_status_raw=row.get("allowed_use", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=row.get("source_artifact_path", ""),
                source_field_or_series="::".join(
                    part
                    for part in [
                        row.get("source_row_key", ""),
                        row.get("beta_field", ""),
                    ]
                    if part
                ),
                source_family="ea_tdc_pass_through_calibration_import",
                source_hash_or_manifest_hash=row.get("source_artifact_sha256", ""),
                sibling_project=row.get("source_project", ""),
                sibling_contract_artifact=row.get("source_artifact_path", ""),
                sibling_contract_hash=row.get("source_artifact_sha256", ""),
                local_estimation_status=row.get("import_status", ""),
                local_estimation_artifact=row.get("source_artifact_path", ""),
                allowed_use=row.get("allowed_use", ""),
                blocked_use=row.get("blocked_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdc_ea_tdc_pass_through_calibration_import.csv"
                ),
                **_copy_switches(row),
            )
        )

    for row in tdc_ea_tdc_pass_through_regime_validation_import_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family=(
                    "tdc_ea_tdc_pass_through_regime_validation_import"
                ),
                artifact_or_surface=(
                    "ratewall_tdc_ea_tdc_pass_through_regime_validation_import.csv"
                ),
                surface_type="sibling_regime_validation_import",
                upstream_row_key=row.get("regime_validation_import_row_id", ""),
                scenario_or_path_scope=row.get("regime_id", ""),
                period_or_horizon="::".join(
                    part
                    for part in [row.get("sample_start", ""), row.get("sample_end", "")]
                    if part
                ),
                value_role="ea_tdc_regime_validation_review_value",
                current_value_exact=row.get("candidate_pass_through_runtime_value", ""),
                unit="deposit_pass_through_beta_review_only",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "ea_tdc_regime_validation_import_not_runtime_selector"
                ),
                source_status_raw=row.get("admission_status", ""),
                calibration_status_raw=row.get("import_status", ""),
                ratewall_use_status_raw=row.get("allowed_use", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=row.get("contract_artifact_path", ""),
                source_field_or_series=row.get("source_row_key", ""),
                source_family="ea_tdc_pass_through_regime_validation",
                source_record_count=row.get("contract_row_count", ""),
                source_hash_or_manifest_hash=row.get("contract_artifact_sha256", ""),
                sibling_project="ea-tdc",
                sibling_contract_artifact=row.get("contract_artifact_path", ""),
                sibling_contract_hash=row.get("contract_artifact_sha256", ""),
                local_estimation_status=row.get("import_status", ""),
                local_estimation_artifact=row.get("validation_artifact_path", ""),
                support_diagnostics_present="true",
                directness_class="tdc_regime_validation_import_review_only",
                transport_risk="high_until_oos_and_false_positive_controls_pass",
                manual_override_required="true",
                calibration_needed="trigger_validation_and_runtime_selector_protocol",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=row.get("allowed_use", ""),
                blocked_use=row.get("blocked_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdc_ea_tdc_pass_through_regime_validation_import.csv"
                ),
                **_copy_switches(row),
            )
        )

    for row in tdc_deposit_pass_through_source_import_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family="tdc_deposit_pass_through_regime_bridge",
                artifact_or_surface="ratewall_tdc_deposit_pass_through_source_import.csv",
                surface_type="sibling_source_import",
                upstream_row_key=row.get("source_import_row_id", ""),
                scenario_or_path_scope=row.get("source_row_role", ""),
                period_or_horizon=row.get("horizon", ""),
                value_role="ea_tdc_pass_through_source_import",
                current_value_exact=row.get("pass_through_point", ""),
                current_value_low=row.get("pass_through_lower95", ""),
                current_value_base=row.get("pass_through_point", ""),
                current_value_high=row.get("pass_through_upper95", ""),
                unit=row.get("normalized_unit", ""),
                source_status_raw=row.get("source_admission_status", ""),
                calibration_status_raw=row.get("protocol_admission_status", ""),
                evidence_strength_raw=row.get("source_artifact_backed", ""),
                prior_basis_raw=row.get("source_row_role", ""),
                ratewall_use_status_raw=row.get("scenario_default_role", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=row.get("source_artifact_path", ""),
                source_field_or_series=row.get("source_artifact_row_key", ""),
                source_family="ea_tdc_deposit_pass_through",
                source_hash_or_manifest_hash=row.get("source_artifact_sha256", ""),
                sibling_project=row.get("source_project", ""),
                sibling_contract_artifact=row.get("source_artifact_path", ""),
                sibling_contract_hash=row.get("source_artifact_sha256", ""),
                local_estimation_status=row.get("source_admission_status", ""),
                local_estimation_artifact=row.get("source_artifact_path", ""),
                allowed_use="dynamic_tdc_liquidity_state_scenario_review_only",
                blocked_use=(
                    "main_ratio;canonical_ratio;Evidence_Mode;denominator_prior;"
                    "pricing_output;holder_allocation;raw_rate_shock"
                ),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdc_deposit_pass_through_source_import.csv"
                ),
                **_copy_switches(row),
            )
        )

    for row in tdc_deposit_pass_through_regime_scenario_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family="tdc_deposit_pass_through_regime_bridge",
                artifact_or_surface=(
                    "ratewall_tdc_deposit_pass_through_regime_scenarios.csv"
                ),
                surface_type="regime_scenario_surface",
                upstream_row_key=row.get("regime_scenario_row_id", ""),
                scenario_or_path_scope=row.get("regime_scenario_id", ""),
                period_or_horizon=row.get("period_label", ""),
                value_role="tdc_pass_through_regime_scenario_value",
                current_value_exact=row.get("pass_through_value", ""),
                unit="dollars_per_dollar_tdc",
                enters_dynamic_path=(
                    "true"
                    if row.get("dynamic_path_default_candidate") == "true"
                    else "false"
                ),
                source_status_raw=row.get("pass_through_source_status", ""),
                calibration_status_raw=row.get("scenario_admission_status", ""),
                evidence_strength_raw=row.get("scenario_only_status", ""),
                prior_basis_raw=row.get("scenario_role", ""),
                ratewall_use_status_raw=row.get("allowed_use", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=(
                    row.get("pass_through_value_source_artifact_path")
                    or row.get("source_artifacts", "")
                ),
                source_field_or_series="::".join(
                    part
                    for part in [
                        row.get("pass_through_source_import_row_id", ""),
                        row.get("pass_through_value_source_field", ""),
                        row.get("pass_through_value_source_artifact_row_key", ""),
                    ]
                    if part
                ),
                source_family="ea_tdc_deposit_pass_through",
                source_hash_or_manifest_hash=(
                    row.get("pass_through_value_source_artifact_sha256")
                    or row.get("source_artifact_hashes", "")
                ),
                sibling_project="ea-tdc",
                sibling_contract_artifact=(
                    row.get("pass_through_value_source_artifact_path")
                    or row.get("source_artifacts", "")
                ),
                sibling_contract_hash=(
                    row.get("pass_through_value_source_artifact_sha256")
                    or row.get("source_artifact_hashes", "")
                ),
                allowed_use=row.get("allowed_use", ""),
                blocked_use=row.get("blocked_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdc_deposit_pass_through_source_import.csv;"
                    "ratewall_tdc_deposit_pass_through_regime_scenarios.csv"
                ),
                **_copy_switches(row),
            )
        )

    for row in tdc_deposit_pass_through_scenario_contract_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family="tdc_deposit_pass_through_scenario_contract",
                artifact_or_surface=(
                    "ratewall_tdc_deposit_pass_through_scenario_contract.csv"
                ),
                surface_type="scenario_contract_surface",
                upstream_row_key=row.get("scenario_contract_row_id", ""),
                scenario_or_path_scope=row.get("regime_scenario_id", ""),
                period_or_horizon=row.get("period_label", ""),
                value_role=row.get("contract_field", ""),
                current_value_exact=row.get("contract_value", ""),
                unit=row.get("contract_unit", ""),
                enters_dynamic_path=row.get(
                    "source_backed_dynamic_reference_allowed", "false"
                ),
                source_status_raw=row.get("source_join_status", ""),
                calibration_status_raw=row.get("admission_status", ""),
                evidence_strength_raw=row.get("value_role", ""),
                prior_basis_raw=row.get("trigger_validation_status", ""),
                ratewall_use_status_raw=row.get("allowed_use", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=(
                    row.get("source_import_artifact_path", "")
                    or row.get("calibration_import_artifact_paths", "")
                    or row.get("trigger_evidence_artifact_paths", "")
                ),
                source_field_or_series="::".join(
                    part
                    for part in [
                        row.get("source_import_row_id", ""),
                        row.get("source_import_source_field", ""),
                        row.get("source_import_artifact_row_key", ""),
                    ]
                    if part
                ),
                source_family="ea_tdc_deposit_pass_through",
                source_hash_or_manifest_hash=(
                    row.get("source_import_artifact_sha256", "")
                    or row.get("calibration_import_artifact_sha256s", "")
                    or row.get("trigger_evidence_artifact_sha256s", "")
                ),
                sibling_project="ea-tdc",
                sibling_contract_artifact=(
                    row.get("source_import_artifact_path", "")
                    or row.get("calibration_import_artifact_paths", "")
                    or row.get("trigger_evidence_artifact_paths", "")
                ),
                sibling_contract_hash=(
                    row.get("source_import_artifact_sha256", "")
                    or row.get("calibration_import_artifact_sha256s", "")
                    or row.get("trigger_evidence_artifact_sha256s", "")
                ),
                allowed_use=row.get("allowed_use", ""),
                blocked_use=row.get("blocked_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdc_deposit_pass_through_source_import.csv;"
                    "ratewall_tdc_ea_tdc_pass_through_calibration_import.csv;"
                    "ratewall_tdc_deposit_pass_through_regime_scenarios.csv;"
                    "ratewall_tdc_liquidity_regime_trigger_evidence.csv;"
                    "ratewall_tdc_liquidity_regime_trigger_promotion_protocol.csv;"
                    "ratewall_tdc_liquidity_regime_trigger_validation_evidence.csv"
                ),
                **_copy_switches(row),
            )
        )

    for row in tdc_deposit_pass_through_trigger_validation_preflight_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family="tdc_deposit_pass_through_trigger_validation_preflight",
                artifact_or_surface=(
                    "ratewall_tdc_deposit_pass_through_trigger_validation_preflight.csv"
                ),
                surface_type="trigger_validation_preflight_surface",
                upstream_row_key=row.get("preflight_row_id", ""),
                scenario_or_path_scope=row.get("regime_scenario_id", ""),
                period_or_horizon=row.get("validation_requirement", ""),
                value_role="tdc_trigger_validation_preflight_status",
                current_value_exact="",
                current_value_range_text=(
                    f"preflight_row_id={row.get('preflight_row_id', '')}"
                ),
                unit="review_status",
                enters_dynamic_path="false",
                source_status_raw=row.get("ea_tdc_artifact_hash_status", ""),
                calibration_status_raw=row.get("admission_status", ""),
                evidence_strength_raw=row.get("promotion_protocol_status", ""),
                prior_basis_raw=row.get("runtime_selector_status", ""),
                ratewall_use_status_raw=row.get("allowed_use", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=row.get("source_artifact_paths", ""),
                source_field_or_series="::".join(
                    part
                    for part in [
                        row.get("trigger_candidate_id", ""),
                        row.get("validation_requirement", ""),
                        row.get("source_row_keys_sample", ""),
                    ]
                    if part
                ),
                source_family="ea_tdc_deposit_pass_through",
                source_hash_or_manifest_hash=row.get("source_artifact_sha256s", ""),
                sibling_project="ea-tdc;tdcsim",
                sibling_contract_artifact=(
                    row.get("source_artifact_paths", "")
                    + ";ratewall_tdcsim_projection_contract_bridge.csv"
                ),
                sibling_contract_hash=(
                    row.get("source_artifact_sha256s", "")
                    + ";"
                    + row.get("tdcsim_manifest_hash", "")
                ),
                allowed_use=row.get("allowed_use", ""),
                blocked_use=row.get("blocked_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdc_deposit_pass_through_scenario_contract.csv;"
                    "ratewall_tdc_liquidity_regime_trigger_evidence.csv;"
                    "ratewall_tdc_liquidity_regime_trigger_promotion_protocol.csv;"
                    "ratewall_tdc_liquidity_regime_trigger_validation_evidence.csv;"
                    "ratewall_tdcsim_projection_contract_bridge.csv"
                ),
                **_copy_switches(row),
            )
        )

    for row in tdc_deposit_pass_through_scenario_contract_invariant_audit_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family="tdc_deposit_pass_through_scenario_contract_invariant_audit",
                artifact_or_surface=(
                    "ratewall_tdc_deposit_pass_through_scenario_contract_invariant_audit.csv"
                ),
                surface_type="scenario_contract_invariant_audit_surface",
                upstream_row_key=row.get("audit_row_id", ""),
                scenario_or_path_scope=row.get("audit_item", ""),
                period_or_horizon=row.get("forbidden_switch_family", ""),
                value_role="tdc_scenario_contract_invariant_status",
                current_value_exact="",
                current_value_range_text=f"audit_row_id={row.get('audit_row_id', '')}",
                unit="audit_status",
                enters_dynamic_path="false",
                source_status_raw=row.get("audit_status", ""),
                calibration_status_raw=(
                    "blocked_invariant_audit_not_runtime_selector"
                ),
                evidence_strength_raw=row.get(
                    "scenario_contract_block_dominates_source_import_status", ""
                ),
                prior_basis_raw=row.get("tdcsim_runtime_selector_status", ""),
                ratewall_use_status_raw=row.get("allowed_use", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=row.get("evidence_surface", ""),
                source_field_or_series=row.get("audit_item", ""),
                source_family="ratewall_invariant_audit",
                source_hash_or_manifest_hash="",
                sibling_project="ea-tdc;tdcsim",
                sibling_contract_artifact=row.get("evidence_surface", ""),
                sibling_contract_hash="",
                allowed_use=row.get("allowed_use", ""),
                blocked_use=row.get("blocked_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=row.get("evidence_surface", ""),
                **_copy_switches(row),
            )
        )

    for row in tdc_liquidity_regime_trigger_evidence_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family="tdc_liquidity_regime_trigger_evidence",
                artifact_or_surface=(
                    "ratewall_tdc_liquidity_regime_trigger_evidence.csv"
                ),
                surface_type="trigger_evidence_surface",
                upstream_row_key=row.get("trigger_evidence_row_id", ""),
                scenario_or_path_scope=row.get("linked_regime_scenario_id", ""),
                period_or_horizon=row.get("observed_window_end", ""),
                value_role="tdc_liquidity_regime_trigger_review_value",
                current_value_exact=row.get("observed_value", ""),
                unit=row.get("observed_value_unit", ""),
                enters_dynamic_path="false",
                source_status_raw=row.get("trigger_evidence_status", ""),
                calibration_status_raw=row.get("trigger_admission_status", ""),
                evidence_strength_raw=row.get("trigger_runtime_status", ""),
                prior_basis_raw=row.get("trigger_variable_family", ""),
                ratewall_use_status_raw=row.get("allowed_use", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=row.get("trigger_source_artifact_path", ""),
                source_field_or_series="::".join(
                    part
                    for part in [
                        row.get("trigger_variable_id", ""),
                        row.get("trigger_statistic", ""),
                        row.get("trigger_source_field", ""),
                        row.get("trigger_source_artifact_row_key", ""),
                    ]
                    if part
                ),
                source_family="ea_tdc_liquidity_regime_diagnostics",
                source_hash_or_manifest_hash=row.get(
                    "trigger_source_artifact_sha256", ""
                ),
                sibling_project="ea-tdc",
                sibling_contract_artifact=row.get("trigger_source_artifact_path", ""),
                sibling_contract_hash=row.get("trigger_source_artifact_sha256", ""),
                allowed_use=row.get("allowed_use", ""),
                blocked_use=row.get("blocked_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdc_liquidity_regime_trigger_evidence.csv;"
                    "ratewall_tdc_deposit_pass_through_source_import.csv;"
                    "ratewall_tdc_deposit_pass_through_regime_scenarios.csv"
                ),
                **_copy_switches(row),
            )
        )

    for row in tdc_liquidity_regime_trigger_promotion_protocol_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family="tdc_liquidity_regime_trigger_promotion_protocol",
                artifact_or_surface=(
                    "ratewall_tdc_liquidity_regime_trigger_promotion_protocol.csv"
                ),
                surface_type="promotion_protocol_surface",
                upstream_row_key=row.get("promotion_protocol_row_id", ""),
                scenario_or_path_scope=row.get("linked_regime_scenario_id", ""),
                period_or_horizon=row.get("required_promotion_field", ""),
                value_role="tdc_liquidity_regime_trigger_promotion_required_field",
                current_value_exact=row.get("current_protocol_value", ""),
                current_value_range_text=(
                    f"protocol_row_id={row.get('promotion_protocol_row_id', '')}"
                ),
                unit="protocol_field_value",
                enters_dynamic_path="false",
                source_status_raw=row.get("current_protocol_value_source_status", ""),
                calibration_status_raw=row.get(
                    "promotion_protocol_admission_status", ""
                ),
                evidence_strength_raw=row.get("promotion_protocol_runtime_status", ""),
                prior_basis_raw=row.get("required_promotion_field_role", ""),
                ratewall_use_status_raw=row.get("allowed_use", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=row.get(
                    "current_protocol_value_source_artifact_path", ""
                ),
                source_field_or_series="::".join(
                    part
                    for part in [
                        row.get("required_promotion_field", ""),
                        row.get("current_protocol_value_source_field", ""),
                        row.get("current_protocol_value_source_row_key", ""),
                    ]
                    if part
                ),
                source_family="ea_tdc_liquidity_regime_diagnostics",
                source_hash_or_manifest_hash=row.get(
                    "current_protocol_value_source_artifact_sha256", ""
                ),
                sibling_project="ea-tdc",
                sibling_contract_artifact=row.get(
                    "current_protocol_value_source_artifact_path", ""
                ),
                sibling_contract_hash=row.get(
                    "current_protocol_value_source_artifact_sha256", ""
                ),
                allowed_use=row.get("allowed_use", ""),
                blocked_use=row.get("blocked_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdc_liquidity_regime_trigger_promotion_protocol.csv;"
                    "ratewall_tdc_liquidity_regime_trigger_evidence.csv"
                ),
                **_copy_switches(row),
            )
        )

    for row in tdc_liquidity_regime_trigger_validation_evidence_rows:
        rows.append(
            _row(
                assumption_handle="tdc_deposit_pass_through_share",
                assumption_family="tdc_liquidity_regime_trigger_validation_evidence",
                artifact_or_surface=(
                    "ratewall_tdc_liquidity_regime_trigger_validation_evidence.csv"
                ),
                surface_type="trigger_validation_evidence_surface",
                upstream_row_key=row.get("trigger_validation_evidence_row_id", ""),
                scenario_or_path_scope=row.get("linked_regime_scenario_id", ""),
                period_or_horizon=row.get("required_promotion_field", ""),
                value_role="tdc_liquidity_regime_trigger_validation_blocker",
                current_value_exact=row.get("current_protocol_value", ""),
                current_value_range_text=(
                    "trigger_validation_evidence_row_id="
                    f"{row.get('trigger_validation_evidence_row_id', '')}"
                ),
                unit="validation_protocol_field_value",
                enters_dynamic_path="false",
                source_status_raw=row.get("validation_evidence_status", ""),
                calibration_status_raw=row.get(
                    "trigger_validation_admission_status", ""
                ),
                evidence_strength_raw=row.get("trigger_validation_runtime_status", ""),
                prior_basis_raw=row.get("validation_evidence_role", ""),
                ratewall_use_status_raw=row.get("allowed_use", ""),
                claim_boundary_raw=row.get("claim_boundary", ""),
                source_artifact=row.get("source_artifact_paths", ""),
                source_field_or_series="::".join(
                    part
                    for part in [
                        row.get("required_promotion_field", ""),
                        row.get("source_artifact_roles_reviewed", ""),
                        row.get("source_row_keys_sample", ""),
                    ]
                    if part
                ),
                source_family="ea_tdc_liquidity_regime_validation_evidence",
                source_hash_or_manifest_hash=row.get("source_artifact_sha256s", ""),
                sibling_project="ea-tdc",
                sibling_contract_artifact=row.get("source_artifact_paths", ""),
                sibling_contract_hash=row.get("source_artifact_sha256s", ""),
                local_estimation_status=row.get("validation_evidence_status", ""),
                local_estimation_artifact=row.get("source_artifact_paths", ""),
                allowed_use=row.get("allowed_use", ""),
                blocked_use=row.get("blocked_use", ""),
                claim_boundary=row.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdc_liquidity_regime_trigger_validation_evidence.csv;"
                    "ratewall_tdc_ea_tdc_pass_through_calibration_import.csv;"
                    "ratewall_tdc_liquidity_regime_trigger_promotion_protocol.csv"
                ),
                **_copy_switches(row),
            )
        )

    rows.extend(_sibling_input_rows(repo_root))
    rows.extend(_qrawatch_rows(repo_root))
    rows.extend(_expected_artifact_rows(repo_root))

    rows = [_apply_classification(row) for row in rows]
    rows = [_apply_overrides(row, overrides) for row in rows]
    return _dedupe_and_finalize(rows)


def assumption_source_backing_invariant_audit_rows(
    *,
    ledger_rows: list[dict[str, str]],
    parameter_pack_rows: list[dict[str, str]],
    assumption_set_rows: list[dict[str, str]],
    activation_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    by_role = _rows_by_role(ledger_rows)
    handles = {row["assumption_handle"] for row in ledger_rows}
    parameter_handles = {row.get("parameter", "") for row in parameter_pack_rows}
    engine_handles = set(_engine_numeric_handles())
    assumption_value_handles = {
        key
        for row in assumption_set_rows
        for key in row
        if key in engine_handles
    }
    active_handles = {
        row.get("parameter_name", "")
        for row in activation_rows
        if row.get("parameter_name")
    }
    valid_classes = set(SOURCE_BACKING_CLASSES)
    forbidden_promoted = {
        "official_source_value",
        "locally_estimated_value",
    }
    source_context_bad = [
        row
        for row in ledger_rows
        if _is_source_context_only(row)
        and row["source_backing_class"] in forbidden_promoted
    ]
    nonpromoted_rows = [
        row
        for row in ledger_rows
        if row["source_backing_class"]
        not in {"official_source_value", "locally_estimated_value"}
    ]
    audit_specs = [
        (
            "ledger_materialized",
            bool(ledger_rows),
            f"{len(ledger_rows)} ledger rows",
            "source-backing ledger is empty or missing",
        ),
        (
            "all_engine_fields_covered",
            engine_handles <= handles
            and engine_handles
            <= {
                row["assumption_handle"]
                for row in by_role.get("engine_numeric_field", [])
            },
            f"{len(engine_handles)} engine numeric fields checked",
            "at least one RateWallAssumptionSet numeric field lacks a ledger row",
        ),
        (
            "all_parameter_pack_rows_covered",
            parameter_handles
            <= {
                row["assumption_handle"]
                for row in by_role.get("parameter_pack_range", [])
            },
            f"{len(parameter_handles)} parameter-pack handles checked",
            "at least one parameter-pack handle lacks a ledger row",
        ),
        (
            "all_assumption_set_values_covered",
            assumption_value_handles
            <= {
                row["assumption_handle"]
                for row in by_role.get("assumption_set_value", [])
            },
            f"{len(assumption_value_handles)} assumption-set fields checked",
            "at least one assumption-set value lacks a ledger row",
        ),
        (
            "all_active_formula_inputs_covered",
            active_handles
            <= {
                row["assumption_handle"]
                for row in by_role.get("active_formula_input", [])
            },
            f"{len(active_handles)} active formula handles checked",
            "at least one active formula input lacks a ledger row",
        ),
        (
            "all_source_backing_classes_valid",
            {row["source_backing_class"] for row in ledger_rows} <= valid_classes,
            "all classes checked against enum",
            "unknown source_backing_class value present",
        ),
        (
            "no_unclassified_model_surface_rows",
            all(row["source_backing_class"] for row in ledger_rows),
            "all ledger rows have source_backing_class",
            "at least one model surface row is unclassified",
        ),
        (
            "no_source_context_promoted_to_calibration",
            not source_context_bad,
            f"{len(source_context_bad)} source-context rows promoted",
            "source context was classified as official or local estimate",
        ),
        (
            "conventional_drag_denominator_unpromoted",
            all(
                row["source_backing_class"] == "literature_context_only_prior"
                and row["prior_narrowing_allowed"] == "false"
                for row in ledger_rows
                if row["assumption_handle"] == "contractionary_drag_gdp_share"
            ),
            "contractionary_drag_gdp_share rows checked",
            "conventional drag denominator was promoted or can narrow priors",
        ),
        (
            "split_denominator_share_rows_are_not_calibrated",
            all(
                row["source_backing_class"] == "literature_context_only_prior"
                and row["split_denominator_promotion_allowed"] == "false"
                for row in ledger_rows
                if row["assumption_handle"] in SPLIT_DENOMINATOR_HANDLES
            ),
            "split-denominator share rows checked",
            "split-denominator shares look calibrated or promotable",
        ),
        (
            "tdc_conversion_not_mpc_output",
            all(
                row["mpc_output_enabled"] == "false"
                and row["source_backing_class"] == "scenario_assumption"
                for row in ledger_rows
                if row["artifact_or_surface"]
                == "ratewall_tdc_forward_assumption_registry.csv"
            ),
            "TDC conversion rows checked",
            "TDC conversion row has mpc_output_enabled not false or wrong class",
        ),
        (
            "tdc_deposit_pass_through_regime_bridge_noncanonical",
            any(
                row["assumption_family"] == "tdc_deposit_pass_through_regime_bridge"
                for row in ledger_rows
            )
            and all(
                row["enters_canonical_ratio"] == "false"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["pricing_output_enabled"] == "false"
                and row["holder_allocation_enabled"] == "false"
                and row["raw_rate_shock_enabled"] == "false"
                and row["source_backing_class"]
                in {
                    "sibling_contract_value",
                    "scenario_assumption",
                    "blocked_or_diagnostic_only",
                }
                for row in ledger_rows
                if row["assumption_family"] == "tdc_deposit_pass_through_regime_bridge"
            ),
            "EA-TDC pass-through bridge rows checked",
            "TDC pass-through bridge entered canonical ratio, prior narrowing, pricing, holder allocation, raw shocks, or an unexpected class",
        ),
        (
            "tdc_ea_tdc_pass_through_calibration_import_fail_closed",
            any(
                row["assumption_family"]
                == "tdc_ea_tdc_pass_through_calibration_import"
                for row in ledger_rows
            )
            and all(
                row["enters_dynamic_path"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["pricing_output_enabled"] == "false"
                and row["holder_allocation_enabled"] == "false"
                and row["raw_rate_shock_enabled"] == "false"
                and row["source_backing_class"] == "blocked_or_diagnostic_only"
                for row in ledger_rows
                if row["assumption_family"]
                == "tdc_ea_tdc_pass_through_calibration_import"
            ),
            "EA-TDC pass-through calibration import rows checked",
            "EA-TDC pass-through calibration import entered runtime, promotion, pricing, holder allocation, raw shocks, or a non-blocked class",
        ),
        (
            "tdc_ea_tdc_pass_through_regime_validation_import_fail_closed",
            any(
                row["assumption_family"]
                == "tdc_ea_tdc_pass_through_regime_validation_import"
                for row in ledger_rows
            )
            and all(
                row["enters_dynamic_path"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["pricing_output_enabled"] == "false"
                and row["holder_allocation_enabled"] == "false"
                and row["raw_rate_shock_enabled"] == "false"
                and row["source_backing_class"] == "blocked_or_diagnostic_only"
                for row in ledger_rows
                if row["assumption_family"]
                == "tdc_ea_tdc_pass_through_regime_validation_import"
            ),
            "EA-TDC pass-through regime-validation import rows checked",
            "EA-TDC regime-validation import entered runtime, promotion, pricing, holder allocation, raw shocks, or a non-blocked class",
        ),
        (
            "tdc_liquidity_regime_trigger_evidence_fail_closed",
            any(
                row["assumption_family"] == "tdc_liquidity_regime_trigger_evidence"
                for row in ledger_rows
            )
            and all(
                row["enters_dynamic_path"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["pricing_output_enabled"] == "false"
                and row["holder_allocation_enabled"] == "false"
                and row["raw_rate_shock_enabled"] == "false"
                and row["source_backing_class"] == "blocked_or_diagnostic_only"
                for row in ledger_rows
                if row["assumption_family"]
                == "tdc_liquidity_regime_trigger_evidence"
            ),
            "TDC liquidity-regime trigger evidence rows checked",
            "TDC liquidity-regime trigger evidence entered runtime, promotion, pricing, holder allocation, raw shocks, or a non-blocked class",
        ),
        (
            "tdc_deposit_pass_through_scenario_contract_fail_closed",
            any(
                row["assumption_family"]
                == "tdc_deposit_pass_through_scenario_contract"
                for row in ledger_rows
            )
            and all(
                row["enters_canonical_ratio"] == "false"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["pricing_output_enabled"] == "false"
                and row["holder_allocation_enabled"] == "false"
                and row["raw_rate_shock_enabled"] == "false"
                and row["source_backing_class"] == "blocked_or_diagnostic_only"
                for row in ledger_rows
                if row["assumption_family"]
                == "tdc_deposit_pass_through_scenario_contract"
            ),
            "TDC pass-through scenario-contract rows checked",
            "TDC pass-through scenario contract entered canonical ratio, prior narrowing, pricing, holder allocation, raw shocks, or a non-blocked class",
        ),
        (
            "tdc_deposit_pass_through_trigger_validation_preflight_fail_closed",
            any(
                row["assumption_family"]
                == "tdc_deposit_pass_through_trigger_validation_preflight"
                for row in ledger_rows
            )
            and all(
                row["enters_dynamic_path"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["pricing_output_enabled"] == "false"
                and row["holder_allocation_enabled"] == "false"
                and row["raw_rate_shock_enabled"] == "false"
                and row["source_backing_class"] == "blocked_or_diagnostic_only"
                for row in ledger_rows
                if row["assumption_family"]
                == "tdc_deposit_pass_through_trigger_validation_preflight"
            ),
            "TDC trigger-validation preflight rows checked",
            "TDC trigger-validation preflight entered runtime, canonical ratio, prior narrowing, pricing, holder allocation, raw shocks, or a non-blocked class",
        ),
        (
            "tdc_deposit_pass_through_scenario_contract_invariant_audit_fail_closed",
            any(
                row["assumption_family"]
                == "tdc_deposit_pass_through_scenario_contract_invariant_audit"
                for row in ledger_rows
            )
            and all(
                row["enters_dynamic_path"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["pricing_output_enabled"] == "false"
                and row["holder_allocation_enabled"] == "false"
                and row["raw_rate_shock_enabled"] == "false"
                and row["source_backing_class"] == "blocked_or_diagnostic_only"
                for row in ledger_rows
                if row["assumption_family"]
                == "tdc_deposit_pass_through_scenario_contract_invariant_audit"
            ),
            "TDC scenario-contract invariant audit rows checked",
            "TDC scenario-contract invariant audit entered runtime, canonical ratio, prior narrowing, pricing, holder allocation, raw shocks, or a non-blocked class",
        ),
        (
            "tdc_liquidity_regime_trigger_promotion_protocol_fail_closed",
            any(
                row["assumption_family"]
                == "tdc_liquidity_regime_trigger_promotion_protocol"
                for row in ledger_rows
            )
            and all(
                row["enters_dynamic_path"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["pricing_output_enabled"] == "false"
                and row["holder_allocation_enabled"] == "false"
                and row["raw_rate_shock_enabled"] == "false"
                and row["source_backing_class"] == "blocked_or_diagnostic_only"
                for row in ledger_rows
                if row["assumption_family"]
                == "tdc_liquidity_regime_trigger_promotion_protocol"
            ),
            "TDC liquidity-regime trigger promotion protocol rows checked",
            "TDC liquidity-regime trigger promotion protocol entered runtime, promotion, pricing, holder allocation, raw shocks, or a non-blocked class",
        ),
        (
            "tdc_liquidity_regime_trigger_validation_evidence_fail_closed",
            any(
                row["assumption_family"]
                == "tdc_liquidity_regime_trigger_validation_evidence"
                for row in ledger_rows
            )
            and all(
                row["enters_dynamic_path"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["pricing_output_enabled"] == "false"
                and row["holder_allocation_enabled"] == "false"
                and row["raw_rate_shock_enabled"] == "false"
                and row["source_backing_class"] == "blocked_or_diagnostic_only"
                for row in ledger_rows
                if row["assumption_family"]
                == "tdc_liquidity_regime_trigger_validation_evidence"
            ),
            "TDC liquidity-regime trigger validation evidence rows checked",
            "TDC liquidity-regime trigger validation evidence entered runtime, promotion, pricing, holder allocation, raw shocks, or a non-blocked class",
        ),
        (
            "tdcsim_holder_paths_not_holder_allocation",
            all(
                row["holder_allocation_enabled"] == "false"
                for row in ledger_rows
                if "holder_absorption" in row["artifact_or_surface"]
                or "holder_absorption" in row["assumption_handle"]
            ),
            "TDCSim holder/prior rows checked",
            "TDCSim holder prior row has holder_allocation_enabled not false",
        ),
        (
            "qrawatch_pricing_not_ratewall_calibration",
            all(
                row["source_backing_class"]
                in {"scenario_assumption", "blocked_or_diagnostic_only"}
                and row["pricing_output_enabled"] == "false"
                for row in ledger_rows
                if "pricing_scenario_translation" in row["artifact_or_surface"]
            ),
            "QRA pricing translation rows checked",
            "QRA reduced-form rows lost their blocked non-pricing boundary",
        ),
        (
            "qrawatch_rows_remain_nonpromotional",
            any(row["source_family"] == "qrawatch" for row in ledger_rows)
            and all(
                row["enters_canonical_ratio"] == "false"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["source_family"] == "qrawatch"
            ),
            "QRA Watch source rows checked",
            "QRA source row enabled pricing, holder allocation, Evidence Mode, or canonical ratio entry",
        ),
        (
            "qrawatch_holder_allocation_blocked_until_investor_allotments",
            all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["holder_allocation_enabled"] == "false"
                for row in ledger_rows
                if row["assumption_handle"] == "qrawatch_investor_allotments_summary"
            ),
            "QRA investor-allotment row checked",
            "QRA investor-allotment placeholder was not blocked before holder allocation use",
        ),
        (
            "tdsp_current_demand_rows_remain_diagnostic_only",
            any(
                row["assumption_family"] == "tdsp_current_demand_mapping"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "tdsp_current_demand_mapping"
            ),
            "TDSP/current-demand mapping rows checked",
            "TDSP/current-demand row was promoted or enabled a forbidden claim switch",
        ),
        (
            "tdsp_pce_dpi_policy_path_rows_remain_diagnostic_only",
            any(
                row["assumption_family"] == "tdsp_pce_dpi_policy_path_gate"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "tdsp_pce_dpi_policy_path_gate"
            ),
            "TDSP/PCE/DPI refresh and policy-path gate rows checked",
            "TDSP/PCE/DPI policy-path row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_reviewed_protocol_source_context_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_reviewed_protocol_source_context"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_reviewed_protocol_source_context"
            ),
            "policy-path reviewed source-context rows checked",
            "policy-path source-context row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_event_level_candidate_vector_fail_closed",
            any(
                row["assumption_family"] == "policy_path_event_level_candidate_vector"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "policy_path_event_level_candidate_vector"
            ),
            "policy-path candidate event-vector rows checked",
            "policy-path candidate event-vector row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_contract_interval_source_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_contract_interval_source_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_contract_interval_source_review"
            ),
            "policy-path contract interval review rows checked",
            "policy-path contract interval review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_protocol_source_acquisition_fail_closed",
            any(
                row["assumption_family"] == "policy_path_protocol_source_acquisition"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "policy_path_protocol_source_acquisition"
            ),
            "policy-path protocol source-acquisition rows checked",
            "policy-path protocol source-acquisition row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_protocol_review_inventory_fail_closed",
            any(
                row["assumption_family"] == "policy_path_protocol_review_inventory"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "policy_path_protocol_review_inventory"
            ),
            "policy-path protocol review inventory rows checked",
            "policy-path protocol review inventory row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_mps_scalar_replication_diagnostic_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_mps_scalar_replication_diagnostic"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_mps_scalar_replication_diagnostic"
            ),
            "policy-path MPS scalar replication diagnostic rows checked",
            "policy-path MPS scalar replication diagnostic row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_bps_year_blocker_decision_fail_closed",
            any(
                row["assumption_family"] == "policy_path_bps_year_blocker_decision"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "policy_path_bps_year_blocker_decision"
            ),
            "policy-path bps-year blocker decision rows checked",
            "policy-path bps-year blocker decision row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_bps_year_source_protocol_fail_closed",
            any(
                row["assumption_family"] == "policy_path_bps_year_source_protocol"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "policy_path_bps_year_source_protocol"
            ),
            "policy-path bps-year source protocol rows checked",
            "policy-path bps-year source protocol row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_normalization_source_manifest_fail_closed",
            any(
                row["assumption_family"] == "policy_path_normalization_source_manifest"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_normalization_source_manifest"
            ),
            "policy-path normalization source-manifest rows checked",
            "policy-path normalization source manifest row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_bps_year_normalization_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_bps_year_normalization_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_bps_year_normalization_review"
            ),
            "policy-path bps-year normalization review rows checked",
            "policy-path bps-year normalization review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_source_cell_unit_contract_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_source_cell_unit_contract_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_source_cell_unit_contract_review"
            ),
            "policy-path source-cell unit contract-review rows checked",
            "policy-path source-cell unit contract-review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_bps_year_protocol_closure_fail_closed",
            any(
                row["assumption_family"] == "policy_path_bps_year_protocol_closure"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "policy_path_bps_year_protocol_closure"
            ),
            "policy-path bps-year protocol-closure rows checked",
            "policy-path bps-year protocol-closure row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_normalization_leak_audit_fail_closed",
            any(
                row["assumption_family"] == "policy_path_normalization_leak_audit"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "policy_path_normalization_leak_audit"
            ),
            "policy-path normalization leak-audit rows checked",
            "policy-path normalization leak-audit row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_parameterization_contract_fail_closed",
            all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_parameterization_source_contract"
            ),
            "conventional-drag research parameterization contract rows checked",
            "research parameterization contract row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_parameterization_source_frontier_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_parameterization_source_frontier"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_parameterization_source_frontier"
            ),
            "conventional-drag research parameterization source frontier rows checked",
            "research parameterization source frontier row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_payload_manifest_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_payload_manifest"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_payload_manifest"
            ),
            "conventional-drag research payload manifest rows checked",
            "research payload manifest row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_parameterization_parser_status_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_parameterization_parser_status"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_parameterization_parser_status"
            ),
            "conventional-drag research parameterization parser-status rows checked",
            "research parameterization parser-status row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_payload_inner_inventory_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_payload_inner_inventory"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_payload_inner_inventory"
            ),
            "conventional-drag research payload inner-inventory rows checked",
            "research payload inner-inventory row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_extraction_candidate_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_extraction_candidate"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_extraction_candidate"
            ),
            "conventional-drag research extraction-candidate rows checked",
            "research extraction-candidate row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_extraction_gate_audit_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_extraction_gate_audit"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_extraction_gate_audit"
            ),
            "conventional-drag research extraction gate-audit rows checked",
            "research extraction gate-audit row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_extraction_gate_detail_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_extraction_gate_detail"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_extraction_gate_detail"
            ),
            "conventional-drag research extraction gate-detail rows checked",
            "research extraction gate-detail row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_source_method_bridge_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_source_method_bridge"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_source_method_bridge"
            ),
            "conventional-drag research source-method bridge rows checked",
            "research source-method bridge row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_source_code_interpretation_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_source_code_interpretation"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_source_code_interpretation"
            ),
            "conventional-drag research source-code interpretation rows checked",
            "research source-code interpretation row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_extended_source_code_interpretation_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_extended_source_code_interpretation"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_extended_source_code_interpretation"
            ),
            "conventional-drag research extended source-code interpretation rows checked",
            "extended source-code interpretation row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_fspdp_coverage_candidate_scan_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_fspdp_coverage_candidate_scan"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_fspdp_coverage_candidate_scan"
            ),
            "conventional-drag research FSPDP coverage-candidate scan rows checked",
            "FSPDP coverage-candidate scan row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_mir_component_aggregation_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_mir_component_aggregation_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_mir_component_aggregation_review"
            ),
            "MIR component aggregation review rows checked",
            "MIR component aggregation review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_mir_component_source_variant_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_mir_component_source_variant_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_mir_component_source_variant_review"
            ),
            "MIR component source-variant review rows checked",
            "MIR component source-variant review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_fspdp_component_decomposition_bridge_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_fspdp_component_decomposition_bridge"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_fspdp_component_decomposition_bridge"
            ),
            "FSPDP component decomposition bridge rows checked",
            "FSPDP decomposition bridge row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_fspdp_coverage_weight_requirement_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_fspdp_coverage_weight_requirement_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_fspdp_coverage_weight_requirement_review"
            ),
            "FSPDP coverage weight-requirement review rows checked",
            "FSPDP coverage weight-requirement row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_fspdp_coverage_priority_search_queue_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_fspdp_coverage_priority_search_queue"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_fspdp_coverage_priority_search_queue"
            ),
            "FSPDP coverage priority search queue rows checked",
            "FSPDP coverage priority search queue row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_fspdp_source_code_search_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_fspdp_source_code_search_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_fspdp_source_code_search_review"
            ),
            "FSPDP source-code search review rows checked",
            "FSPDP source-code search review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_fspdp_external_source_acquisition_action_plan_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_fspdp_external_source_acquisition_action_plan"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_fspdp_external_source_acquisition_action_plan"
            ),
            "FSPDP external source-acquisition action-plan rows checked",
            "FSPDP external source-acquisition action-plan row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_fspdp_official_component_source_acquisition_execution_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_fspdp_official_component_source_acquisition_execution"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_fspdp_official_component_source_acquisition_execution"
            ),
            "FSPDP official component-source acquisition execution rows checked",
            "FSPDP official component-source acquisition row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_fspdp_research_side_action_plan_extraction_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_fspdp_research_side_action_plan_extraction_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_fspdp_research_side_action_plan_extraction_review"
            ),
            "FSPDP research-side action-plan extraction review rows checked",
            "FSPDP research-side action-plan extraction row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_source_unit_conversion_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_source_unit_conversion_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_source_unit_conversion_review"
            ),
            "research source-unit conversion review rows checked",
            "source-unit conversion review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_mir_replication_source_unit_audit_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_mir_replication_source_unit_audit"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_mir_replication_source_unit_audit"
            ),
            "MIR replication/source-unit audit rows checked",
            "MIR replication/source-unit audit row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_mir_source_unit_transformation_contract_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_mir_source_unit_transformation_contract"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_mir_source_unit_transformation_contract"
            ),
            "MIR source-unit transformation/sign contract rows checked",
            "MIR source-unit transformation contract row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_mir_target_horizon_reconciliation_contract_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_mir_target_horizon_reconciliation_contract"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_mir_target_horizon_reconciliation_contract"
            ),
            "MIR target-horizon reconciliation contract rows checked",
            "MIR target-horizon reconciliation contract row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_mir_horizon_rekeying_candidate_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_mir_horizon_rekeying_candidate_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_mir_horizon_rekeying_candidate_review"
            ),
            "MIR horizon rekeying candidate review rows checked",
            "MIR horizon rekeying candidate review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_mir_h24_source_unit_audit_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_mir_h24_source_unit_audit"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_mir_h24_source_unit_audit"
            ),
            "MIR h24 source-unit audit rows checked",
            "MIR h24 source-unit audit row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_mir_h24_8q_rekeying_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_mir_h24_8q_rekeying_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_mir_h24_8q_rekeying_review"
            ),
            "MIR h24-to-8q rekeying review rows checked",
            "MIR h24-to-8q rekeying review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_mir_4q8q_conversion_readiness_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_mir_4q8q_conversion_readiness_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_mir_4q8q_conversion_readiness_review"
            ),
            "MIR 4q/8q conversion readiness review rows checked",
            "MIR 4q/8q conversion readiness review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_research_policy_path_normalization_bridge_review_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_policy_path_normalization_bridge_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_policy_path_normalization_bridge_review"
            ),
            "research policy-path normalization bridge review rows checked",
            "research policy-path normalization bridge review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_research_shock_source_evidence_protocol_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_research_shock_source_evidence_protocol_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_research_shock_source_evidence_protocol_review"
            ),
            "policy-path research shock source evidence protocol review rows checked",
            "policy-path research shock source evidence protocol review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_source_code_workbook_object_inventory_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_source_code_workbook_object_inventory"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_source_code_workbook_object_inventory"
            ),
            "policy-path source-code/workbook object inventory rows checked",
            "policy-path source-code/workbook object inventory row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_source_code_workbook_protocol_deep_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_source_code_workbook_protocol_deep_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_source_code_workbook_protocol_deep_review"
            ),
            "policy-path source-code/workbook protocol deep-review rows checked",
            "policy-path source-code/workbook protocol deep-review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_usmpd_pca_loading_backtransform_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_usmpd_pca_loading_backtransform_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_usmpd_pca_loading_backtransform_review"
            ),
            "USMPD PCA loading/back-transform review rows checked",
            "USMPD PCA loading/back-transform review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_usmpd_scalar_score_replication_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_usmpd_scalar_score_replication_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_usmpd_scalar_score_replication_review"
            ),
            "USMPD scalar-score replication review rows checked",
            "USMPD scalar-score replication review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_usmpd_pca_backtransform_gate_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_usmpd_pca_backtransform_gate_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_usmpd_pca_backtransform_gate_review"
            ),
            "USMPD PCA back-transform gate-review rows checked",
            "USMPD PCA back-transform gate-review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_usmpd_instrument_decomposition_design_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_usmpd_instrument_decomposition_design_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_usmpd_instrument_decomposition_design_review"
            ),
            "USMPD instrument-decomposition design-review rows checked",
            "USMPD instrument-decomposition design-review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_bps_year_candidate_path_design_contract_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_bps_year_candidate_path_design_contract"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_bps_year_candidate_path_design_contract"
            ),
            "policy-path bps-year candidate path design-contract rows checked",
            "policy-path bps-year candidate path design-contract row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_formula_replication_source_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_formula_replication_source_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_formula_replication_source_review"
            ),
            "policy-path formula/replication source-review rows checked",
            "policy-path formula/replication source-review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_reviewed_bps_year_protocol_gap_matrix_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_reviewed_bps_year_protocol_gap_matrix"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_reviewed_bps_year_protocol_gap_matrix"
            ),
            "policy-path reviewed bps-year protocol gap-matrix rows checked",
            "policy-path reviewed bps-year protocol gap-matrix row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_protocol_source_acquisition_work_queue_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_protocol_source_acquisition_work_queue"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_protocol_source_acquisition_work_queue"
            ),
            "policy-path protocol source-acquisition work-queue rows checked",
            "policy-path protocol source-acquisition work-queue row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_protocol_source_parse_execution_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_protocol_source_parse_execution_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_protocol_source_parse_execution_review"
            ),
            "policy-path protocol source parse-execution review rows checked",
            "policy-path protocol source parse-execution row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_source_parse_synthesis_queue_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_source_parse_synthesis_queue"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_source_parse_synthesis_queue"
            ),
            "policy-path source-parse synthesis queue rows checked",
            "policy-path source-parse synthesis queue row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_source_parse_action_execution_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_source_parse_action_execution"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_source_parse_action_execution"
            ),
            "policy-path source-parse action-execution rows checked",
            "policy-path source-parse action-execution row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_deeper_parse_execution_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_deeper_parse_execution_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_deeper_parse_execution_review"
            ),
            "policy-path deeper-parse execution-review rows checked",
            "policy-path deeper-parse execution-review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_protocol_candidate_draft_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_protocol_candidate_draft_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_protocol_candidate_draft_review"
            ),
            "policy-path protocol-candidate draft-review rows checked",
            "policy-path protocol-candidate draft-review row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_protocol_missing_evidence_acquisition_queue_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_protocol_missing_evidence_acquisition_queue"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_protocol_missing_evidence_acquisition_queue"
            ),
            "policy-path protocol missing-evidence acquisition-queue rows checked",
            "policy-path protocol missing-evidence acquisition-queue row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_protocol_missing_evidence_parse_execution_review_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_protocol_missing_evidence_parse_execution_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_protocol_missing_evidence_parse_execution_review"
            ),
            "policy-path protocol missing-evidence parse-execution rows checked",
            "policy-path protocol missing-evidence parse-execution row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_protocol_authoring_readiness_matrix_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_protocol_authoring_readiness_matrix"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_protocol_authoring_readiness_matrix"
            ),
            "policy-path protocol authoring/readiness matrix rows checked",
            "policy-path protocol authoring/readiness matrix row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_protocol_field_authoring_contract_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_protocol_field_authoring_contract"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_protocol_field_authoring_contract"
            ),
            "policy-path protocol field-authoring contract rows checked",
            "policy-path protocol field-authoring contract row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_field_evidence_resolution_queue_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_field_evidence_resolution_queue"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_field_evidence_resolution_queue"
            ),
            "policy-path field evidence resolution queue rows checked",
            "policy-path field evidence resolution queue row was promoted or enabled a forbidden claim switch",
        ),
        *[
            (
                f"{family}_fail_closed",
                any(row["assumption_family"] == family for row in ledger_rows)
                and all(
                    row["source_backing_class"] == "blocked_or_diagnostic_only"
                    and row["prior_narrowing_allowed"] == "false"
                    and row["formula_replacement_allowed"] == "false"
                    and row["split_denominator_promotion_allowed"] == "false"
                    and row["enters_canonical_ratio"] == "false"
                    and row["enters_noncanonical_assumption_mode"] == "true"
                    and all(
                        row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS
                    )
                    for row in ledger_rows
                    if row["assumption_family"] == family
                ),
                f"{label} rows checked",
                f"{label} row was promoted or enabled a forbidden claim switch",
            )
            for family, label in [
                ("ratio_layer_registry", "ratio-layer registry"),
                ("estimation_target_registry", "estimation-target registry"),
                ("channel_taxonomy_registry", "channel taxonomy registry"),
                ("historical_interpretation_audit", "historical interpretation audit"),
                ("tdc_equation_variant_registry", "TDC equation-variant registry"),
                (
                    "policy_path_source_extraction_task_packet",
                    "policy-path source extraction task packet",
                ),
                (
                    "policy_path_source_extraction_results",
                    "policy-path source extraction results",
                ),
                (
                    "policy_path_source_extraction_result_adjudication",
                    "policy-path source extraction result adjudication",
                ),
                (
                    "policy_path_authored_protocol_completion_audit",
                    "policy-path authored protocol completion audit",
                ),
                (
                    "policy_path_protocol_completion_design_tranche",
                    "policy-path protocol completion design tranche",
                ),
                (
                    "policy_path_field_specific_pass_rule_design",
                    "policy-path field-specific pass-rule design",
                ),
                (
                    "policy_path_field_specific_source_evidence_audit",
                    "policy-path field-specific source-evidence audit",
                ),
                (
                    "policy_path_source_locator_binding_review",
                    "policy-path source locator binding review",
                ),
                (
                    "policy_path_exact_source_locator_remediation",
                    "policy-path exact source locator remediation",
                ),
                (
                    "policy_path_exact_locator_field_closure_diagnostic",
                    "policy-path exact locator field closure diagnostic",
                ),
                (
                    "policy_path_exact_locator_pass_rule_adjudication",
                    "policy-path exact locator pass-rule adjudication",
                ),
                (
                    "policy_path_terminal_no_hit_closure",
                    "policy-path terminal no-hit closure",
                ),
                (
                    "policy_path_independent_replication_target_design",
                    "policy-path independent replication target design",
                ),
                (
                    "policy_path_authored_fail_closed_invariant_design",
                    "policy-path authored fail-closed invariant design",
                ),
                (
                    "policy_path_protocol_component_closure_rollup",
                    "policy-path protocol component closure rollup",
                ),
                (
                    "policy_path_component_gate_execution_rollup",
                    "policy-path component gate execution rollup",
                ),
                (
                    "policy_path_locator_binding_closure_diagnostic",
                    "policy-path locator binding closure diagnostic",
                ),
                (
                    "policy_path_full_protocol_admission_gate_summary",
                    "policy-path full-protocol admission gate summary",
                ),
                (
                    "policy_path_source_bundle_field_exhaustion_decision",
                    "policy-path source-bundle field exhaustion decision",
                ),
                (
                    "policy_path_source_bundle_component_exhaustion_decision",
                    "policy-path source-bundle component exhaustion decision",
                ),
                (
                    "conventional_drag_empirical_target_registry",
                    "conventional-drag empirical target registry",
                ),
                (
                    "conventional_drag_route_pruning_audit",
                    "conventional-drag route pruning audit",
                ),
                (
                    "conventional_drag_response_design_gate",
                    "conventional-drag response design gate",
                ),
                (
                    "denominator_response_estimate_registry",
                    "denominator response-estimate registry",
                ),
                (
                    "denominator_formal_design_gate",
                    "denominator formal design gate",
                ),
                (
                    "conventional_drag_response_execution_readiness_packet",
                    "conventional-drag response execution readiness packet",
                ),
                (
                    "local_lp_proxy_svar_diagnostic_run_packet",
                    "local LP / proxy-SVAR diagnostic run packet",
                ),
                (
                    "local_lp_proxy_svar_execution_preflight_results",
                    "local LP / proxy-SVAR execution preflight results",
                ),
                (
                    "local_lp_proxy_svar_route_closure_decision",
                    "local LP / proxy-SVAR route closure decision",
                ),
                (
                    "conventional_drag_denominator_route_triage_synthesis",
                    "conventional-drag denominator route triage synthesis",
                ),
                (
                    "policy_path_100bp_year_blocker_action_resolution",
                    "policy-path 100bp-year blocker action resolution",
                ),
                (
                    "policy_path_source_protocol_action_packet",
                    "policy-path source-protocol action packet",
                ),
                (
                    "policy_path_source_protocol_pass_rule_harness",
                    "policy-path source-protocol pass-rule harness",
                ),
                (
                    "policy_path_source_protocol_extraction_attempt_results",
                    "policy-path source-protocol extraction attempt results",
                ),
                (
                    "policy_path_source_protocol_attempt_closure_handoff",
                    "policy-path source-protocol attempt closure handoff",
                ),
                (
                    "policy_path_promotion_grade_source_family_acquisition_packet",
                    "policy-path promotion-grade source-family acquisition packet",
                ),
                (
                    "policy_path_promotion_grade_source_family_acquisition_execution_preflight_results",
                    "policy-path promotion-grade source-family acquisition execution preflight results",
                ),
                (
                    "policy_path_source_family_execution_closure_selection_packet",
                    "policy-path source-family execution closure selection packet",
                ),
                (
                    "policy_path_current_artifact_manual_review_execution_packet",
                    "policy-path current-artifact manual-review execution packet",
                ),
                (
                    "policy_path_current_artifact_manual_review_result_attempt",
                    "policy-path current-artifact manual-review result attempt",
                ),
                (
                    "policy_path_source_author_manual_acquisition_followup_packet",
                    "policy-path source-author/manual acquisition follow-up packet",
                ),
                (
                    "policy_path_source_author_manual_acquisition_execution_preflight_results",
                    "policy-path source-author/manual acquisition execution preflight results",
                ),
                (
                    "policy_path_real_source_author_web_acquisition_attempt_packet",
                    "policy-path real source-author web acquisition attempt packet",
                ),
                (
                    "policy_path_downloaded_artifact_locator_parse_adjudication_packet",
                    "policy-path downloaded artifact locator parse adjudication packet",
                ),
                (
                    "policy_path_locator_candidate_pass_rule_review_decision_packet",
                    "policy-path locator candidate pass-rule review decision packet",
                ),
                (
                    "policy_path_value_bearing_bps_year_exposure_export",
                    "policy-path value-bearing bps-year exposure export",
                ),
                (
                    "policy_path_value_bearing_bps_year_exposure_quarterly_series",
                    "policy-path value-bearing bps-year quarterly exposure series",
                ),
            ]
        ],
        (
            "current_demand_gdp_share_conversion_inputs_no_drag",
            any(
                row["assumption_family"]
                in {
                    "current_demand_gdp_share_source_manifest",
                    "current_demand_gdp_share_panel",
                }
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "official_source_value"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                in {
                    "current_demand_gdp_share_source_manifest",
                    "current_demand_gdp_share_panel",
                }
            ),
            "current-demand GDP-share conversion rows checked",
            "current-demand conversion row entered runtime, prior narrowing, pricing, holder allocation, raw shocks, or a non-official source class",
        ),
        (
            "fspdp_component_source_panel_no_drag",
            any(
                row["assumption_family"]
                in {
                    "conventional_drag_fspdp_component_source_manifest",
                    "conventional_drag_fspdp_component_share_panel",
                }
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "official_source_value"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                in {
                    "conventional_drag_fspdp_component_source_manifest",
                    "conventional_drag_fspdp_component_share_panel",
                }
            ),
            "FSPDP component source/share rows checked",
            "FSPDP component source/share row entered runtime, prior narrowing, pricing, holder allocation, raw shocks, or a non-official source class",
        ),
        (
            "conventional_drag_current_demand_bridge_no_drag",
            any(
                row["assumption_family"]
                == "conventional_drag_current_demand_mapping_bridge"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "official_source_value"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_current_demand_mapping_bridge"
            ),
            "conventional-drag current-demand mapping bridge rows checked",
            "current-demand mapping bridge row entered runtime, prior narrowing, pricing, holder allocation, raw shocks, or a non-official source class",
        ),
        (
            "conventional_drag_research_extraction_conversion_bridge_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_research_extraction_conversion_bridge"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_research_extraction_conversion_bridge"
            ),
            "conventional-drag research extraction conversion bridge rows checked",
            "research extraction conversion bridge row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_local_lp_diagnostic_fail_closed",
            any(
                row["assumption_family"].startswith("conventional_drag_local_")
                or row["assumption_family"]
                == "conventional_drag_fspdp_denominator_readiness_gate"
                or row["assumption_family"]
                == "conventional_drag_fspdp_denominator_candidate_join_preflight"
                or row["assumption_family"]
                == "conventional_drag_fspdp_value_bearing_exposure_lp_execution"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"].startswith("conventional_drag_local_")
                or row["assumption_family"]
                == "conventional_drag_fspdp_denominator_readiness_gate"
                or row["assumption_family"]
                == "conventional_drag_fspdp_denominator_candidate_join_preflight"
                or row["assumption_family"]
                == "conventional_drag_fspdp_value_bearing_exposure_lp_execution"
            ),
            "conventional-drag local LP diagnostic rows checked",
            "local LP diagnostic row was promoted, reclassified as source-backed calibration, or enabled a forbidden claim switch",
        ),
        (
            "frbus_model_benchmark_simulation_readiness_fail_closed",
            any(
                row["assumption_family"]
                == "frbus_model_benchmark_simulation_readiness"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "frbus_model_benchmark_simulation_readiness"
            ),
            "FRB/US model benchmark simulation-readiness rows checked",
            "FRB/US readiness row was promoted or enabled a forbidden claim switch",
        ),
        (
            "frbus_conventional_drag_benchmark_protocol_fail_closed",
            any(
                row["assumption_family"]
                == "frbus_conventional_drag_benchmark_protocol"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "frbus_conventional_drag_benchmark_protocol"
            ),
            "FRB/US conventional-drag benchmark-protocol rows checked",
            "FRB/US benchmark protocol row was promoted or enabled a forbidden claim switch",
        ),
        (
            "frbus_official_model_package_inventory_fail_closed",
            any(
                row["assumption_family"]
                == "frbus_official_model_package_inventory"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "frbus_official_model_package_inventory"
            ),
            "FRB/US official-model package-inventory rows checked",
            "FRB/US package inventory row was promoted or enabled a forbidden claim switch",
        ),
        (
            "frbus_official_model_benchmark_simulation_protocol_fail_closed",
            any(
                row["assumption_family"]
                == "frbus_official_model_benchmark_simulation_protocol"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "frbus_official_model_benchmark_simulation_protocol"
            ),
            "FRB/US official-model simulation-protocol rows checked",
            "FRB/US simulation protocol row was promoted or enabled a forbidden claim switch",
        ),
        (
            "frbus_runtime_runner_preflight_fail_closed",
            any(
                row["assumption_family"] == "frbus_runtime_runner_preflight"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "frbus_runtime_runner_preflight"
            ),
            "FRB/US runtime-runner preflight rows checked",
            "FRB/US runtime preflight row was promoted or enabled a forbidden claim switch",
        ),
        (
            "frbus_runtime_runner_output_slots_fail_closed",
            any(
                row["assumption_family"] == "frbus_runtime_runner_output_slots"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"] == "frbus_runtime_runner_output_slots"
            ),
            "FRB/US runtime-runner output-slot rows checked",
            "FRB/US runtime output-slot row was promoted or enabled a forbidden claim switch",
        ),
        (
            "frbus_benchmark_comparison_mapping_contract_fail_closed",
            any(
                row["assumption_family"]
                == "frbus_benchmark_comparison_mapping_contract"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "frbus_benchmark_comparison_mapping_contract"
            ),
            "FRB/US benchmark comparison/mapping contract rows checked",
            "FRB/US benchmark comparison/mapping row was promoted or enabled a forbidden claim switch",
        ),
        (
            "frbus_benchmark_output_slot_extension_review_fail_closed",
            any(
                row["assumption_family"]
                == "frbus_benchmark_output_slot_extension_review"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "frbus_benchmark_output_slot_extension_review"
            ),
            "FRB/US benchmark output-slot extension-review rows checked",
            "FRB/US output-slot extension row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_source_unit_aggregation_blocker_bridge_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_source_unit_aggregation_blocker_bridge"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_source_unit_aggregation_blocker_bridge"
            ),
            "source-unit aggregation blocker bridge rows checked",
            "source-unit aggregation blocker row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_mirgk_targeted_gap_source_followup_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_mirgk_targeted_gap_source_followup"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_mirgk_targeted_gap_source_followup"
            ),
            "MIR/GK targeted gap source-followup rows checked",
            "MIR/GK targeted gap source-followup row was promoted or enabled a forbidden claim switch",
        ),
        (
            "conventional_drag_promotion_contract_checklist_fail_closed",
            any(
                row["assumption_family"]
                == "conventional_drag_promotion_contract_checklist"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "conventional_drag_promotion_contract_checklist"
            ),
            "promotion-contract checklist rows checked",
            "promotion-contract checklist row was promoted or enabled a forbidden claim switch",
        ),
        (
            "backend_schema_release_anti_overclaim_surfaces_fail_closed",
            any(
                row["assumption_family"]
                in {
                    "backend_surface_schema_contract",
                    "backend_artifact_claim_boundary_manifest",
                    "release_archive_reproducibility_audit",
                }
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["split_denominator_promotion_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                in {
                    "backend_surface_schema_contract",
                    "backend_artifact_claim_boundary_manifest",
                    "release_archive_reproducibility_audit",
                }
            ),
            "backend schema/release anti-overclaim rows checked",
            "backend schema/release audit row was promoted or enabled a forbidden claim switch",
        ),
        (
            "openicpsr_replication_package_source_manifest_fail_closed",
            any(
                row["assumption_family"]
                == "openicpsr_replication_package_source_manifest"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "openicpsr_replication_package_source_manifest"
            ),
            "openICPSR replication-package manifest rows checked",
            "openICPSR manifest row was promoted or enabled a forbidden claim switch",
        ),
        (
            "policy_path_contract_spec_acquisition_blocker_fail_closed",
            any(
                row["assumption_family"]
                == "policy_path_contract_spec_acquisition_blocker"
                for row in ledger_rows
            )
            and all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                and row["prior_narrowing_allowed"] == "false"
                and row["formula_replacement_allowed"] == "false"
                and row["enters_canonical_ratio"] == "false"
                and row["enters_noncanonical_assumption_mode"] == "true"
                and all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
                for row in ledger_rows
                if row["assumption_family"]
                == "policy_path_contract_spec_acquisition_blocker"
            ),
            "policy-path contract-spec acquisition blocker rows checked",
            "contract-spec blocker row was promoted or enabled a forbidden claim switch",
        ),
        (
            "blocked_rows_have_evidence_needed",
            all(
                row["evidence_needed_before_promotion"]
                or row["blocked_use"]
                or row["classification_reason"]
                for row in ledger_rows
                if row["source_backing_class"] == "blocked_or_diagnostic_only"
            ),
            "blocked/diagnostic rows checked",
            "blocked row lacks evidence-needed or blocker text",
        ),
        (
            "official_or_local_rows_have_source_artifact_and_field_or_method",
            all(
                row["source_artifact"]
                and (row["source_field_or_series"] or row["local_estimation_method"])
                for row in ledger_rows
                if row["source_backing_class"]
                in {"official_source_value", "locally_estimated_value"}
            ),
            "official/local rows checked",
            "official/local row lacks source artifact and field/method",
        ),
        (
            "forbidden_switches_disabled_for_nonpromoted_rows",
            all(
                row[field] == "false"
                for row in nonpromoted_rows
                for field in FORBIDDEN_SWITCH_FIELDS
            ),
            f"{len(nonpromoted_rows)} non-promoted rows checked",
            "a non-promoted row enabled a forbidden claim switch",
        ),
        (
            "missing_expected_artifacts_flagged",
            all(
                row["source_backing_class"] == "blocked_or_diagnostic_only"
                for row in ledger_rows
                if row["missing_expected_artifact"] == "true"
            ),
            "missing expected artifact rows checked",
            "missing artifact row is not blocked/diagnostic",
        ),
        (
            "release_archive_contains_ledger",
            True,
            "release manifest/archive membership checked by release tests",
            "release package omitted ledger or invariant audit",
        ),
    ]
    return [
        _audit_row(
            audit_item=item,
            passed=passed,
            evidence_summary=summary,
            failure_mode_if_false=failure,
        )
        for item, passed, summary, failure in audit_specs
    ]


def _engine_numeric_handles() -> list[str]:
    return [
        field.name
        for field in dataclass_fields(RateWallAssumptionSet)
        if field.name not in ASSUMPTION_METADATA_COLUMNS
    ]


def _row(**kwargs: str) -> dict[str, str]:
    row = {field: "" for field in ASSUMPTION_SOURCE_BACKING_LEDGER_FIELDS}
    row.update(
        {
            "scenario_or_path_scope": "all",
            "period_or_horizon": "all",
            "enters_canonical_ratio": "false",
            "enters_noncanonical_assumption_mode": "true",
            "enters_canonical_tdc_accounting": "false",
            "enters_tdcsim_forward_surface": "false",
            "enters_qrawatch_scenario_surface": "false",
            "enters_split_denominator": "false",
            "enters_dynamic_path": "false",
            "enters_sidecar": "false",
            "affects_wall_hit_classification": "false",
            "source_backing_class": "",
            "classification_confidence": "rule_based",
            "manual_override_required": "false",
            "prior_narrowing_allowed": "false",
            "formula_replacement_allowed": "false",
            "split_denominator_promotion_allowed": "false",
            "row_created_at_utc": "deterministic_build_no_runtime_timestamp",
        }
    )
    row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
    row.update({key: str(value) for key, value in kwargs.items() if key in row})
    if not row["claim_boundary"]:
        row["claim_boundary"] = (
            row["claim_boundary_raw"] or "assumption_source_backing_ledger"
        )
    return row


def _conventional_drag_rows(
    source_rows: list[dict[str, str]],
    artifact: str,
    handle_field: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in source_rows:
        for handle in _handles_from_field(item.get(handle_field, "")):
            rows.append(
                _row(
                    assumption_handle=handle,
                    assumption_family="conventional_drag_denominator",
                    artifact_or_surface=artifact,
                    surface_type="denominator_source_gate",
                    upstream_row_key=(
                        item.get("gate_id")
                        or item.get("attempt_id")
                        or item.get("denominator_component")
                        or item.get("channel_component")
                    ),
                    scenario_or_path_scope=item.get("denominator_component", "")
                    or item.get("channel_component", ""),
                    period_or_horizon=item.get("horizon", "")
                    or item.get("horizon_bucket", ""),
                    value_role="denominator_source_gate_status",
                    source_status_raw=item.get("source_status", ""),
                    calibration_status_raw=item.get("response_estimate_layer_status", ""),
                    evidence_strength_raw=item.get("source_specific_evidence_status", ""),
                    claim_boundary_raw=item.get("claim_boundary", ""),
                    source_artifact=item.get("source_specific_artifacts", "")
                    or item.get("source_artifacts", ""),
                    source_field_or_series=item.get("source_specific_series_or_table_ids", "")
                    or item.get("source_ids", ""),
                    source_family=item.get("source_family", ""),
                    source_url_or_key=item.get("source_specific_urls_or_docs", ""),
                    evidence_needed_before_prior_narrowing=item.get(
                        "evidence_needed_before_prior_narrowing", ""
                    )
                    or item.get("evidence_needed", ""),
                    evidence_needed_before_promotion=item.get(
                        "evidence_needed_before_promotion", ""
                    ),
                    promotion_gate=item.get("promotion_gate", ""),
                    promotion_status=item.get("promotion_readiness", "")
                    or item.get("promotion_decision", ""),
                    prior_narrowing_allowed=item.get(
                        "prior_narrowing_allowed",
                        item.get("denominator_prior_can_narrow", "false"),
                    ),
                    formula_replacement_allowed=item.get(
                        "formula_replacement_allowed", "false"
                    ),
                    split_denominator_promotion_allowed=item.get(
                        "split_denominator_promotion_allowed",
                        item.get(
                            "split_denominator_can_promote_to_main_classifier",
                            "false",
                        ),
                    ),
                    allowed_use=item.get("allowed_current_use", ""),
                    claim_boundary=item.get("claim_boundary", ""),
                    linked_source_tables=artifact,
                    **_copy_switches(item),
                )
            )
    return rows


def _conventional_drag_evidence_tranche_rows(
    source_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in source_rows:
        component = item.get("denominator_component", "")
        outcome = item.get("outcome_series_id", "")
        shock = item.get("shock_source_id", "")
        handle = f"{component}_{outcome}_{shock}_diagnostic_tranche"
        rows.append(
            _row(
                assumption_handle=handle,
                assumption_family="conventional_drag_diagnostic_tranche",
                artifact_or_surface="ratewall_conventional_drag_evidence_tranche.csv",
                surface_type="diagnostic_estimate_or_blocker",
                upstream_row_key=item.get("evidence_tranche_id", ""),
                scenario_or_path_scope=component,
                period_or_horizon=item.get("horizon_bucket", ""),
                value_role="diagnostic_outcome_change_per_100bp",
                current_value_exact=item.get(
                    "mechanical_outcome_change_per_100bp", ""
                ),
                unit=item.get("outcome_units", ""),
                formula_role=(
                    "diagnostic_input_only_not_gdp_share_demand_drag_conversion"
                ),
                source_status_raw=item.get("source_status", ""),
                calibration_status_raw=item.get("estimate_status", ""),
                evidence_strength_raw=item.get(
                    "source_specific_evidence_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get(
                    "source_specific_series_or_table_ids", ""
                ),
                source_family="conventional_drag_evidence_tranche",
                source_url_or_key=item.get("source_specific_urls_or_docs", ""),
                local_estimation_status=item.get("estimate_status", ""),
                local_estimation_method=item.get("estimation_method", ""),
                local_estimation_artifact=(
                    "ratewall_conventional_drag_evidence_tranche.csv"
                ),
                local_estimation_diagnostic_artifact=(
                    "ratewall_denominator_aligned_response_panel_scaffold.csv"
                ),
                support_diagnostics_present=item.get("estimate_available", "false"),
                directness_class=(
                    "financial_outcome_diagnostic_not_gdp_share_demand_drag"
                ),
                transport_risk="high_requires_reviewed_demand_mapping",
                calibration_needed="gdp_share_per_100bp_year_conversion",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_prior_narrowing", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_gate=item.get("promotion_gate_status", ""),
                promotion_status="blocked",
                prior_narrowing_allowed=item.get(
                    "prior_narrowing_allowed", "false"
                ),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="diagnostic_input_to_fail_closed_admission_review",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "empirical_threshold_claim;raw_rate_shock"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_evidence_tranche.csv;"
                    "ratewall_denominator_evidence_upgrade_tier1_workplan.csv;"
                    "source_provenance.json"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _tdsp_current_demand_mapping_rows(
    *,
    source_review_rows: list[dict[str, str]],
    unit_conversion_rows: list[dict[str, str]],
    diagnostic_mapping_rows: list[dict[str, str]],
    policy_path_blocker_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in source_review_rows:
        source_id = item.get("source_id", "")
        rows.append(
            _row(
                assumption_handle=f"tdsp_current_demand_source_review_{source_id}",
                assumption_family="tdsp_current_demand_mapping",
                artifact_or_surface="ratewall_tdsp_current_demand_source_review.csv",
                surface_type="source_review_or_blocker",
                upstream_row_key=item.get("source_review_id", ""),
                scenario_or_path_scope=item.get("required_input_role", ""),
                value_role="source_review_input_gate",
                unit=item.get("source_units", ""),
                formula_role="input_admission_review_not_runtime_conversion",
                source_backing_class="blocked_or_diagnostic_only",
                source_status_raw=item.get("source_admission_status", ""),
                evidence_strength_raw=item.get(
                    "source_specific_evidence_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get(
                    "source_specific_series_or_table_ids", ""
                ),
                source_family=item.get("source_family", ""),
                source_url_or_key=item.get("source_url_or_key", ""),
                source_snapshot_kind=item.get("source_snapshot_kind", ""),
                source_record_count=item.get("source_record_count", ""),
                directness_class=item.get("current_demand_role_status", ""),
                transport_risk="high_until_current_demand_bridge_admitted",
                calibration_needed="tdsp_to_current_demand_mapping",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                promotion_status="blocked",
                prior_narrowing_allowed=item.get(
                    "prior_narrowing_allowed", "false"
                ),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="diagnostic_input_review_only",
                blocked_use="denominator_prior_narrowing;main_ratio;Evidence_Mode",
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables="ratewall_tdsp_current_demand_source_review.csv",
                **_copy_switches(item),
            )
        )
    for item in unit_conversion_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "tdsp_current_demand_unit_conversion_"
                    + item.get("conversion_input_role", "")
                ),
                assumption_family="tdsp_current_demand_mapping",
                artifact_or_surface=(
                    "ratewall_tdsp_current_demand_unit_conversion.csv"
                ),
                surface_type="unit_conversion_blocker",
                upstream_row_key=item.get("unit_conversion_id", ""),
                scenario_or_path_scope=item.get("conversion_input_role", ""),
                value_role="unit_conversion_candidate_blocked",
                unit=item.get("target_units", ""),
                formula_role=item.get("conversion_formula_candidate", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_status_raw=item.get("mechanical_conversion_status", ""),
                calibration_status_raw=item.get(
                    "source_backing_requirement_status", ""
                ),
                evidence_strength_raw=item.get(
                    "source_specific_evidence_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get(
                    "source_specific_series_or_table_ids", ""
                ),
                source_family="tdsp_current_demand_unit_conversion",
                local_estimation_status=item.get("mechanical_conversion_status", ""),
                support_diagnostics_present="false",
                directness_class="blocked_unit_conversion_not_runtime_input",
                transport_risk="high_requires_mapping_and_uncertainty",
                calibration_needed="source_backed_unit_conversion",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                promotion_status="blocked",
                prior_narrowing_allowed=item.get(
                    "prior_narrowing_allowed", "false"
                ),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="diagnostic_conversion_review_only",
                blocked_use="denominator_prior_narrowing;main_ratio;Evidence_Mode",
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdsp_current_demand_unit_conversion.csv"
                ),
                **_copy_switches(item),
            )
        )
    for item in diagnostic_mapping_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "tdsp_current_demand_diagnostic_mapping_"
                    + item.get("current_demand_candidate_source_id", "")
                    + "_"
                    + item.get("horizon_bucket", "")
                ),
                assumption_family="tdsp_current_demand_mapping",
                artifact_or_surface=(
                    "ratewall_tdsp_current_demand_diagnostic_mapping.csv"
                ),
                surface_type="diagnostic_mapping_estimate_or_blocker",
                upstream_row_key=item.get("diagnostic_mapping_id", ""),
                scenario_or_path_scope=item.get(
                    "current_demand_candidate_source_id", ""
                ),
                period_or_horizon=item.get("horizon_bucket", ""),
                value_role="diagnostic_tdsp_to_current_demand_mapping",
                current_value_exact=item.get("diagnostic_coefficient", ""),
                current_value_low=item.get("diagnostic_ci_95_lower", ""),
                current_value_high=item.get("diagnostic_ci_95_upper", ""),
                unit=item.get("diagnostic_units", ""),
                formula_role="observational_diagnostic_mapping_not_conversion",
                source_backing_class="blocked_or_diagnostic_only",
                source_status_raw=item.get("source_status", ""),
                calibration_status_raw=item.get("estimate_status", ""),
                evidence_strength_raw=item.get(
                    "source_specific_evidence_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get(
                    "source_specific_series_or_table_ids", ""
                ),
                source_family="tdsp_current_demand_diagnostic_mapping",
                local_estimation_status=item.get("estimate_status", ""),
                local_estimation_method="diagnostic_ols_with_newey_west_hac",
                local_estimation_artifact=(
                    "ratewall_tdsp_current_demand_diagnostic_mapping.csv"
                ),
                support_diagnostics_present=item.get("estimate_available", "false"),
                directness_class="diagnostic_mapping_not_gdp_share_demand_drag",
                transport_risk="high_observational_mapping",
                calibration_needed="promotion_grade_current_demand_bridge",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_prior_narrowing", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_status="blocked",
                prior_narrowing_allowed=item.get(
                    "prior_narrowing_allowed", "false"
                ),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="diagnostic_mapping_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "empirical_threshold_claim;raw_rate_shock"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdsp_current_demand_diagnostic_mapping.csv"
                ),
                **_copy_switches(item),
            )
        )
    for item in policy_path_blocker_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "tdsp_policy_path_normalization_"
                    + item.get("shock_source_id", "")
                ),
                assumption_family="tdsp_current_demand_mapping",
                artifact_or_surface=(
                    "ratewall_tdsp_policy_path_normalization_blocker.csv"
                ),
                surface_type="policy_path_normalization_blocker",
                upstream_row_key=item.get("policy_path_blocker_id", ""),
                scenario_or_path_scope=item.get("shock_source_id", ""),
                value_role="policy_path_100bp_year_normalization_blocker",
                current_value_exact=item.get(
                    "tdsp_mechanical_outcome_change_per_100bp", ""
                ),
                unit=item.get("tdsp_mechanical_unit_status", ""),
                formula_role=item.get("normalization_formula_candidate", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                calibration_status_raw=item.get("policy_path_source_status", ""),
                evidence_strength_raw=item.get(
                    "source_specific_evidence_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get(
                    "source_specific_series_or_table_ids", ""
                ),
                source_family="tdsp_policy_path_normalization_blocker",
                support_diagnostics_present="false",
                directness_class="blocked_policy_path_not_100bp_year",
                transport_risk="high_without_path_exposure_vector",
                calibration_needed="policy_path_bps_year_normalization",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                promotion_status="blocked",
                prior_narrowing_allowed=item.get(
                    "prior_narrowing_allowed", "false"
                ),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_blocker_review_only",
                blocked_use="denominator_prior_narrowing;main_ratio;Evidence_Mode",
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdsp_policy_path_normalization_blocker.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _tdsp_pce_dpi_policy_path_rows(
    *,
    source_refresh_contract_rows: list[dict[str, str]],
    refresh_diagnostic_mapping_rows: list[dict[str, str]],
    policy_path_design_gate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in source_refresh_contract_rows:
        series_id = item.get("series_id", "")
        rows.append(
            _row(
                assumption_handle=f"pce_dpi_source_refresh_contract_{series_id}",
                assumption_family="tdsp_pce_dpi_policy_path_gate",
                artifact_or_surface="ratewall_pce_dpi_source_refresh_contract.csv",
                surface_type="source_refresh_contract",
                upstream_row_key=item.get("source_refresh_contract_id", ""),
                scenario_or_path_scope=series_id,
                value_role="pce_dpi_source_refresh_contract_not_source_admission",
                unit=item.get("source_registry_units", ""),
                formula_role="source_refresh_contract_only_not_runtime_input",
                source_backing_class="blocked_or_diagnostic_only",
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get("source_refresh_contract_status", ""),
                evidence_strength_raw=item.get(
                    "source_specific_evidence_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get(
                    "source_specific_series_or_table_ids", ""
                ),
                source_family=item.get("source_family", ""),
                source_url_or_key=item.get("source_registry_endpoint", ""),
                source_snapshot_kind=item.get("current_snapshot_status", ""),
                source_record_count=item.get("current_snapshot_record_count", ""),
                support_diagnostics_present="false",
                directness_class="source_refresh_contract_not_materialized_snapshot",
                transport_risk="high_until_snapshot_materialized_and_audited",
                calibration_needed="materialized_pce_dpi_snapshot",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                promotion_status="blocked",
                prior_narrowing_allowed=item.get(
                    "prior_narrowing_allowed", "false"
                ),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="source_refresh_contract_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "current_demand_conversion"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_pce_dpi_source_refresh_contract.csv;"
                    "configs/sources.yml;src/ratewall/data/build.py"
                ),
                **_copy_switches(item),
            )
        )
    for item in refresh_diagnostic_mapping_rows:
        outcome_id = item.get("current_demand_candidate_source_id", "")
        horizon = item.get("horizon_bucket", "")
        rows.append(
            _row(
                assumption_handle=(
                    f"tdsp_pce_dpi_refresh_diagnostic_mapping_{outcome_id}_{horizon}"
                ),
                assumption_family="tdsp_pce_dpi_policy_path_gate",
                artifact_or_surface=(
                    "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv"
                ),
                surface_type="refresh_diagnostic_mapping",
                upstream_row_key=item.get("refresh_diagnostic_mapping_id", ""),
                scenario_or_path_scope=outcome_id,
                period_or_horizon=horizon,
                value_role="tdsp_pce_dpi_refresh_diagnostic_mapping_not_conversion",
                current_value_exact=item.get("diagnostic_coefficient", ""),
                unit=item.get("diagnostic_units", ""),
                formula_role="observational_tdsp_change_to_refreshed_pce_dpi_outcome",
                source_backing_class="blocked_or_diagnostic_only",
                source_status_raw=item.get("estimate_status", ""),
                calibration_status_raw=item.get(
                    "diagnostic_admission_status", ""
                ),
                evidence_strength_raw=item.get(
                    "source_specific_evidence_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get(
                    "source_specific_series_or_table_ids", ""
                ),
                source_family="FRED refreshed PCE/DPI bundle plus FRED TDSP",
                source_url_or_key=item.get("source_specific_urls_or_docs", ""),
                source_snapshot_kind=item.get(
                    "refresh_snapshot_validation_status", ""
                ),
                source_record_count=item.get("refresh_snapshot_record_count", ""),
                source_hash_or_manifest_hash=item.get(
                    "refresh_snapshot_records_sha256", ""
                ),
                support_diagnostics_present="true",
                local_estimation_status="diagnostic_only_not_conversion",
                local_estimation_method="OLS_with_HAC_review_only",
                local_estimation_artifact=(
                    "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv"
                ),
                directness_class="refreshed_source_observational_mapping",
                transport_risk="high_without_policy_path_or_conversion_gate",
                calibration_needed="tdsp_to_current_demand_conversion_gate",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_prior_narrowing", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_status="blocked",
                prior_narrowing_allowed=item.get(
                    "prior_narrowing_allowed", "false"
                ),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="refresh_diagnostic_mapping_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "current_demand_conversion"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv;"
                    "data/raw/ratewall_pce_dpi_source_refresh_snapshot.json;"
                    "data/raw/ratewall_snapshot.json"
                ),
                **_copy_switches(item),
            )
        )
    for item in policy_path_design_gate_rows:
        shock_id = item.get("shock_source_id", "")
        rows.append(
            _row(
                assumption_handle=f"policy_path_exposure_vector_design_gate_{shock_id}",
                assumption_family="tdsp_pce_dpi_policy_path_gate",
                artifact_or_surface=(
                    "ratewall_policy_path_exposure_vector_design_gate.csv"
                ),
                surface_type="policy_path_exposure_vector_design_gate",
                upstream_row_key=item.get("policy_path_design_gate_id", ""),
                scenario_or_path_scope=shock_id,
                value_role="policy_path_exposure_vector_design_gate",
                current_value_exact=item.get("bps_year_exposure_output", ""),
                unit="bps_year",
                formula_role=item.get("bps_year_normalization_formula", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_status_raw=item.get("design_gate_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get(
                    "source_specific_evidence_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get(
                    "source_specific_series_or_table_ids", ""
                ),
                source_family=item.get("shock_source_family", ""),
                source_snapshot_kind=item.get("shock_snapshot_status", ""),
                source_record_count=item.get("shock_record_count", ""),
                support_diagnostics_present="false",
                directness_class="scalar_shock_not_policy_path_exposure",
                transport_risk="high_without_reviewed_path_vector",
                calibration_needed="policy_path_bps_year_exposure_vector",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                promotion_status="blocked",
                prior_narrowing_allowed=item.get(
                    "prior_narrowing_allowed", "false"
                ),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_design_gate_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "raw_rate_shock"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_exposure_vector_design_gate.csv;"
                    "configs/sources.yml;data/raw/ratewall_snapshot.json"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_bps_year_source_protocol_rows(
    protocol_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in protocol_rows:
        shock_id = item.get("shock_source_id", "")
        field_name = item.get("required_protocol_field_name", "")
        rows.append(
            _row(
                assumption_handle=(
                    f"policy_path_bps_year_source_protocol_{shock_id}_{field_name}"
                ),
                assumption_family="policy_path_bps_year_source_protocol",
                artifact_or_surface="ratewall_policy_path_bps_year_source_protocol.csv",
                surface_type="source_protocol_contract",
                upstream_row_key=item.get("protocol_row_id", ""),
                scenario_or_path_scope=shock_id,
                period_or_horizon=item.get("required_horizon_scope", ""),
                value_role=field_name,
                current_value_exact=item.get("current_protocol_value", ""),
                unit=item.get("required_unit", ""),
                formula_role=item.get("required_formula_or_method", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="required_policy_path_protocol_field_missing",
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get("source_backing_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("current_source_artifact", "")
                or item.get("admissible_source_artifact_type", ""),
                source_field_or_series=item.get("required_source_fields", ""),
                source_family=item.get("shock_source_family", ""),
                source_snapshot_kind=item.get("shock_snapshot_status", ""),
                source_record_count=item.get("shock_record_count", ""),
                support_diagnostics_present="false",
                directness_class="scalar_shock_protocol_requirement_not_populated",
                transport_risk="high_until_reviewed_policy_path_protocol_populated",
                manual_override_required="false",
                calibration_needed="policy_path_bps_year_source_protocol",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_gate=item.get("promotion_gate", ""),
                promotion_status=item.get("promotion_status", "blocked"),
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_source_protocol_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_bps_year_source_protocol.csv;"
                    "ratewall_policy_path_exposure_vector_design_gate.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_normalization_source_manifest_rows(
    manifest_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in manifest_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_normalization_source_manifest_"
                    f"{item.get('source_family', '')}"
                ),
                assumption_family="policy_path_normalization_source_manifest",
                artifact_or_surface=(
                    "ratewall_policy_path_normalization_source_manifest.csv"
                ),
                surface_type="normalization_source_manifest",
                upstream_row_key=item.get("normalization_source_manifest_row_id", ""),
                scenario_or_path_scope=item.get("source_family", ""),
                period_or_horizon=item.get("source_role", ""),
                value_role="normalization_source_review_status",
                current_value_exact="",
                unit="not_admitted_bps_year_value",
                formula_role=item.get("bps_year_formula_source_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "normalization_source_manifest_not_bps_year_protocol"
                ),
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("source_file_or_surface", ""),
                source_family=item.get("source_family", ""),
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count=item.get("source_surface_row_count", ""),
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class="source_manifest_without_admitted_bps_year_bridge",
                transport_risk="high_until_unit_horizon_formula_replication_pass",
                manual_override_required="false",
                calibration_needed="policy_path_bps_year_normalization_review",
                evidence_needed_before_prior_narrowing=item.get("exact_blocker", ""),
                evidence_needed_before_promotion=item.get("exact_blocker", ""),
                promotion_gate="policy_path_normalization_source_manifest_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_normalization_source_review_only",
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_normalization_source_manifest.csv;"
                    "ratewall_policy_path_bps_year_source_protocol.csv;"
                    "ratewall_policy_path_event_level_candidate_vector.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_bps_year_normalization_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        source_family = item.get("source_family", "")
        review_key = item.get("normalization_review_row_id", "")
        review_key_short = hashlib.sha256(review_key.encode("utf-8")).hexdigest()[:16]
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_bps_year_normalization_review_"
                    f"{source_family}_{review_key_short}"
                ),
                assumption_family="policy_path_bps_year_normalization_review",
                artifact_or_surface=(
                    "ratewall_policy_path_bps_year_normalization_review.csv"
                ),
                surface_type="bps_year_normalization_review",
                upstream_row_key=item.get("normalization_review_row_id", ""),
                scenario_or_path_scope=source_family,
                period_or_horizon=item.get("event_date", ""),
                value_role=item.get("formula_step", ""),
                current_value_exact="",
                unit="not_admitted_bps_year_value",
                formula_role=item.get("bps_year_formula_source_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "bps_year_normalization_review_not_admitted_exposure"
                ),
                source_status_raw=item.get("admission_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get(
                    "independent_replication_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get("instrument_or_factor", ""),
                source_family=source_family,
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count="1",
                support_diagnostics_present="true",
                directness_class="normalization_review_without_bps_year_output",
                transport_risk="high_until_all_formula_steps_and_replication_pass",
                manual_override_required="false",
                calibration_needed="admitted_bps_year_policy_path_bridge",
                evidence_needed_before_prior_narrowing=item.get("exact_blocker", ""),
                evidence_needed_before_promotion=item.get("exact_blocker", ""),
                promotion_gate="policy_path_bps_year_normalization_review_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_bps_year_normalization_review.csv;"
                    "ratewall_policy_path_normalization_source_manifest.csv;"
                    "ratewall_policy_path_bps_year_source_protocol.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_source_cell_unit_contract_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        key = item.get("unit_contract_review_row_id", "")
        key_short = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_source_cell_unit_contract_review_"
                    f"{item.get('source_instrument_code', '')}_{key_short}"
                ),
                assumption_family="policy_path_source_cell_unit_contract_review",
                artifact_or_surface=(
                    "ratewall_policy_path_source_cell_unit_contract_review.csv"
                ),
                surface_type="source_cell_unit_contract_review",
                upstream_row_key=key,
                scenario_or_path_scope=item.get("effective_contract_family", ""),
                period_or_horizon=item.get("era_bucket", ""),
                value_role=item.get("required_unit_claim", ""),
                current_value_exact="",
                unit="not_admitted_source_cell_rate_unit",
                formula_role=item.get("bps_year_integral_formula_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "contract_quote_metadata_not_source_cell_unit_or_bps_year"
                ),
                source_status_raw=item.get("source_cell_unit_admission_status", ""),
                calibration_status_raw=item.get("protocol_closure_status", ""),
                evidence_strength_raw=item.get("quote_rule_review_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("source_instrument_code", ""),
                source_family=item.get("source_family", ""),
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count=item.get("covered_candidate_row_count", ""),
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class="quote_context_not_source_cell_unit_admission",
                transport_risk="high_until_unit_sign_horizon_formula_replication_pass",
                manual_override_required="false",
                calibration_needed="admitted_bps_year_policy_path_protocol",
                evidence_needed_before_prior_narrowing=item.get("exact_blocker", ""),
                evidence_needed_before_promotion=item.get("exact_blocker", ""),
                promotion_gate="policy_path_source_cell_unit_contract_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_source_cell_unit_contract_review.csv;"
                    "ratewall_policy_path_contract_interval_source_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_bps_year_protocol_closure_rows(
    closure_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in closure_rows:
        key = item.get("protocol_closure_row_id", "")
        key_short = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_bps_year_protocol_closure_"
                    f"{item.get('source_family', '')}_{key_short}"
                ),
                assumption_family="policy_path_bps_year_protocol_closure",
                artifact_or_surface="ratewall_policy_path_bps_year_protocol_closure.csv",
                surface_type="bps_year_protocol_closure",
                upstream_row_key=key,
                scenario_or_path_scope=item.get("source_family", ""),
                period_or_horizon=item.get("admission_gate", ""),
                value_role=item.get("formula_step", ""),
                current_value_exact="",
                unit="not_admitted_bps_year_value",
                formula_role=item.get("bps_year_integral_formula_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "incomplete_policy_path_bps_year_protocol_gate"
                ),
                source_status_raw=item.get("source_support_status", ""),
                calibration_status_raw=item.get("protocol_closure_status", ""),
                evidence_strength_raw=item.get("independent_replication_target_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("admission_gate", ""),
                source_family=item.get("source_family", ""),
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class="protocol_closure_without_complete_bps_year_chain",
                transport_risk="high_until_full_gate_conjunction_passes",
                manual_override_required="false",
                calibration_needed="complete_source_backed_bps_year_protocol",
                evidence_needed_before_prior_narrowing=item.get(
                    "required_evidence_before_promotion", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "required_evidence_before_promotion", ""
                ),
                promotion_gate="policy_path_bps_year_protocol_closure_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_bps_year_protocol_closure.csv;"
                    "ratewall_policy_path_normalization_source_manifest.csv;"
                    "ratewall_policy_path_source_cell_unit_contract_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_normalization_leak_audit_rows(
    audit_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in audit_rows:
        key = item.get("leak_audit_row_id", "")
        key_short = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        rows.append(
            _row(
                assumption_handle=f"policy_path_normalization_leak_audit_{key_short}",
                assumption_family="policy_path_normalization_leak_audit",
                artifact_or_surface="ratewall_policy_path_normalization_leak_audit.csv",
                surface_type="normalization_leak_audit",
                upstream_row_key=key,
                scenario_or_path_scope=item.get("surface_name", ""),
                period_or_horizon=item.get("field_name", ""),
                value_role=item.get("leak_rule", ""),
                current_value_exact="",
                unit="audit_violation_count",
                formula_role=item.get("audit_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="leak_audit_not_calibration_evidence",
                source_status_raw=item.get("audit_status", ""),
                calibration_status_raw="blocked_policy_path_leak_audit_only",
                evidence_strength_raw=item.get("observed_violation_count", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("surface_name", ""),
                source_field_or_series=item.get("field_name", ""),
                source_family="policy_path_normalization_closure",
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count=item.get("observed_row_count", ""),
                support_diagnostics_present="true",
                directness_class="leak_audit_not_source_evidence",
                transport_risk="high_if_any_leak_violation_nonzero",
                manual_override_required="false",
                calibration_needed="repair_policy_path_normalization_leak_before_promotion",
                evidence_needed_before_prior_narrowing=item.get("exact_blocker", ""),
                evidence_needed_before_promotion=item.get("exact_blocker", ""),
                promotion_gate="policy_path_normalization_leak_audit_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_normalization_leak_audit.csv;"
                    "ratewall_policy_path_bps_year_protocol_closure.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_reviewed_protocol_source_context_rows(
    context_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in context_rows:
        shock_id = item.get("applicable_shock_source_id", "")
        subclass = (
            "candidate_event_vector_missing_bps_year_protocol"
            if item.get("event_level_vector_status")
            == "candidate_event_level_futures_columns_extracted_fail_closed"
            else "partial_policy_path_context_missing_bps_year_vector"
        )
        rows.append(
            _row(
                assumption_handle=(
                    f"policy_path_reviewed_protocol_source_context_{shock_id}"
                ),
                assumption_family="policy_path_reviewed_protocol_source_context",
                artifact_or_surface=(
                    "ratewall_policy_path_reviewed_protocol_source_context.csv"
                ),
                surface_type="reviewed_source_context",
                upstream_row_key=item.get("source_context_row_id", ""),
                scenario_or_path_scope=shock_id,
                value_role="partial_policy_path_protocol_context",
                current_value_exact=item.get("horizon_context", ""),
                unit="source_context",
                formula_role=item.get("factor_context", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=subclass,
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get(
                    "protocol_context_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("local_manifest_path", ""),
                source_field_or_series=item.get("registry_series_id", ""),
                source_family=item.get("publisher", ""),
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count=item.get("chart_csv_record_count", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "reviewed_context_not_event_level_bps_year_protocol"
                ),
                transport_risk=(
                    "high_until_event_level_vector_integral_replication_populated"
                ),
                manual_override_required="false",
                calibration_needed="policy_path_bps_year_source_protocol",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_gate="policy_path_reviewed_source_context_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_source_context_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_reviewed_protocol_source_context.csv;"
                    "ratewall_policy_path_bps_year_source_protocol.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_event_level_candidate_vector_rows(
    candidate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in candidate_rows:
        shock_id = item.get("applicable_shock_source_id", "")
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_event_level_candidate_vector_"
                    f"{item.get('sheet_role', '')}_"
                    f"{item.get('event_sequence', '')}_"
                    f"{item.get('instrument_code', '')}"
                ),
                assumption_family="policy_path_event_level_candidate_vector",
                artifact_or_surface="ratewall_policy_path_event_level_candidate_vector.csv",
                surface_type="source_extracted_candidate_vector",
                upstream_row_key=item.get("candidate_vector_row_id", ""),
                scenario_or_path_scope=shock_id,
                period_or_horizon=item.get("instrument_code", ""),
                value_role="candidate_event_level_futures_response",
                current_value_exact=item.get("candidate_policy_rate_change_value", ""),
                unit="source_reported_rate_change_unconverted",
                formula_role=item.get("candidate_unit_interpretation_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="source_extracted_candidate_vector_only",
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get("source_backing_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get("instrument_code", ""),
                source_family=item.get("instrument_family", ""),
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count="1",
                support_diagnostics_present=item.get("numeric_value_available", ""),
                directness_class=(
                    "event_level_futures_candidate_not_bps_year_protocol"
                ),
                transport_risk="high_until_horizon_unit_integral_replication_pass",
                manual_override_required="false",
                calibration_needed="policy_path_bps_year_source_protocol",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_gate="policy_path_event_level_candidate_vector_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_candidate_vector_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_event_level_candidate_vector.csv;"
                    "ratewall_policy_path_bps_year_source_protocol.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_contract_interval_source_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_contract_interval_source_review_"
                    f"{item.get('source_sheet_vintage', '')}_"
                    f"{item.get('event_id', '')}_"
                    f"{item.get('candidate_instrument_code', '')}"
                ),
                assumption_family="policy_path_contract_interval_source_review",
                artifact_or_surface=(
                    "ratewall_policy_path_contract_interval_source_review.csv"
                ),
                surface_type="contract_interval_review",
                upstream_row_key=item.get("contract_review_row_id", ""),
                scenario_or_path_scope=item.get("source_sheet_vintage", ""),
                period_or_horizon=item.get("candidate_delivery_month", ""),
                value_role="contract_interval_candidate_not_bps_year",
                current_value_exact=item.get("source_cell_value_numeric", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="contract_interval_candidate_not_bps_year",
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("official_spec_artifact_path", ""),
                source_field_or_series=item.get("candidate_instrument_code", ""),
                source_family=item.get("instrument_family", ""),
                support_diagnostics_present="true",
                directness_class="contract_interval_review_only",
                transport_risk="high_until_bps_year_formula_and_replication_pass",
                manual_override_required="false",
                calibration_needed="policy_path_bps_year_integration_protocol",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use="policy_path_contract_interval_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_contract_interval_source_review.csv;"
                    "ratewall_policy_path_event_level_candidate_vector.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_contract_spec_acquisition_blocker_rows(
    blocker_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in blocker_rows:
        artifact_hashed = bool(item.get("local_artifact_sha256", ""))
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_contract_spec_acquisition_blocker_"
                    f"{item.get('artifact_handle', '')}"
                ),
                assumption_family="policy_path_contract_spec_acquisition_blocker",
                artifact_or_surface=(
                    "ratewall_policy_path_contract_spec_acquisition_blocker.csv"
                ),
                surface_type="contract_spec_acquisition_blocker",
                upstream_row_key=item.get("blocker_row_id", ""),
                scenario_or_path_scope=item.get("official_spec_source_handle", ""),
                value_role=(
                    "official_contract_spec_artifact_hashed_review_only"
                    if artifact_hashed
                    else "missing_official_contract_spec_artifact"
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "official_contract_spec_hashed_not_bps_year_protocol"
                    if artifact_hashed
                    else "official_contract_spec_not_acquired"
                ),
                source_status_raw=item.get("acquisition_status", ""),
                calibration_status_raw=item.get("fallback_path_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("local_artifact_path", ""),
                source_field_or_series=item.get("affected_candidate_instrument_codes", ""),
                source_family="policy_path_contract_interval_sources",
                support_diagnostics_present="true",
                directness_class=(
                    "contract_spec_hash_review_only"
                    if artifact_hashed
                    else "contract_spec_acquisition_blocker"
                ),
                transport_risk=(
                    "high_until_unit_formula_replication_pass"
                    if artifact_hashed
                    else "high_until_official_spec_artifact_hash_present"
                ),
                manual_override_required="false",
                calibration_needed=(
                    "policy_path_bps_year_integration_protocol"
                    if artifact_hashed
                    else "official_contract_spec_source_acquisition"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use="policy_path_contract_spec_acquisition_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_contract_spec_acquisition_blocker.csv;"
                    "ratewall_policy_path_contract_interval_source_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_protocol_source_acquisition_rows(
    acquisition_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in acquisition_rows:
        source_handle = item.get("source_handle", "")
        artifact_handle = item.get("artifact_handle", "")
        rows.append(
            _row(
                assumption_handle=(
                    f"policy_path_protocol_source_acquisition_{artifact_handle}"
                ),
                assumption_family="policy_path_protocol_source_acquisition",
                artifact_or_surface=(
                    "ratewall_policy_path_protocol_source_acquisition_registry.csv"
                ),
                surface_type="raw_protocol_source_provenance_registry",
                upstream_row_key=item.get("source_acquisition_row_id", ""),
                scenario_or_path_scope=source_handle,
                period_or_horizon=item.get("artifact_role", ""),
                value_role="raw_policy_path_protocol_source_artifact",
                current_value_exact="",
                unit="not_protocol_value",
                formula_role=item.get("parse_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "raw_protocol_source_artifact_not_reviewed_bps_year_protocol"
                ),
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get("source_provenance_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=artifact_handle,
                source_family=item.get("source_family", ""),
                source_url_or_key=item.get("source_url", ""),
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("sha256", ""),
                support_diagnostics_present=item.get(
                    "artifact_inspection_summary", ""
                ),
                directness_class="raw_protocol_source_artifact_not_bps_year_output",
                transport_risk="high_until_unit_horizon_integral_replication_pass",
                manual_override_required="false",
                calibration_needed="policy_path_bps_year_source_protocol_review",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_gate="policy_path_protocol_source_acquisition_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_protocol_source_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_source_acquisition_registry.csv;"
                    "ratewall_policy_path_bps_year_source_protocol.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_protocol_review_inventory_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_protocol_review_"
                    f"{item.get('review_surface', '')}_"
                    f"{item.get('review_field_name', '')}"
                ),
                assumption_family="policy_path_protocol_review_inventory",
                artifact_or_surface="ratewall_policy_path_protocol_review_inventory.csv",
                surface_type="blocked_protocol_review_inventory",
                upstream_row_key=item.get("protocol_review_row_id", ""),
                scenario_or_path_scope=item.get("source_handle", ""),
                period_or_horizon=item.get("review_field_name", ""),
                value_role=item.get("review_field_role", ""),
                current_value_exact=item.get("current_protocol_value", ""),
                unit="not_admitted_protocol_value",
                formula_role=item.get("bps_year_integral_review_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="reviewed_protocol_context_not_bps_year_value",
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get("source_provenance_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get("source_columns_or_variables", ""),
                source_family=item.get("review_surface", ""),
                source_url_or_key=item.get("source_artifact_path", ""),
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count=item.get("source_row_count", "1") or "1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "protocol_review_context_without_bps_year_integral"
                ),
                transport_risk="high_until_bps_year_integral_replication_pass",
                manual_override_required="false",
                calibration_needed="policy_path_bps_year_protocol_completion",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_gate="policy_path_protocol_review_inventory_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_protocol_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_review_inventory.csv;"
                    "ratewall_policy_path_bps_year_source_protocol.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_mps_scalar_replication_rows(
    diagnostic_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in diagnostic_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_mps_scalar_replication_"
                    f"{item.get('replication_target', '').lower()}"
                ),
                assumption_family="policy_path_mps_scalar_replication_diagnostic",
                artifact_or_surface=(
                    "ratewall_policy_path_mps_scalar_replication_diagnostic.csv"
                ),
                surface_type="scalar_replication_diagnostic",
                upstream_row_key=item.get("replication_row_id", ""),
                scenario_or_path_scope=item.get("source_handle", ""),
                period_or_horizon=item.get("replication_target", ""),
                value_role="replicated_scalar_mps_not_bps_year_path",
                current_value_exact=item.get("current_protocol_value", ""),
                unit="not_admitted_protocol_value",
                formula_role=item.get("bps_year_integral_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "scalar_mps_replication_not_bps_year_protocol"
                ),
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get("replication_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get("source_variables", ""),
                source_family=item.get("event_surface", ""),
                source_url_or_key=item.get("source_output_file", ""),
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count=item.get("source_output_row_count", "1") or "1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class="scalar_replication_without_bps_year_path",
                transport_risk="high_until_bps_year_integral_replication_pass",
                manual_override_required="false",
                calibration_needed="policy_path_bps_year_protocol_completion",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_gate="policy_path_mps_scalar_replication_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_scalar_replication_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_mps_scalar_replication_diagnostic.csv;"
                    "ratewall_policy_path_bps_year_source_protocol.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_bps_year_blocker_decision_rows(
    decision_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in decision_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_bps_year_blocker_decision_"
                    f"{item.get('required_bridge_field', '')}"
                ),
                assumption_family="policy_path_bps_year_blocker_decision",
                artifact_or_surface="ratewall_policy_path_bps_year_blocker_decision.csv",
                surface_type="terminal_blocker_decision",
                upstream_row_key=item.get("blocker_decision_row_id", ""),
                scenario_or_path_scope=item.get("source_handle", ""),
                period_or_horizon=item.get("required_bridge_field", ""),
                value_role="blocked_bps_year_bridge_requirement",
                current_value_exact=item.get("current_protocol_value", ""),
                unit="not_admitted_protocol_value",
                formula_role=item.get("bps_year_integral_status", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "terminal_bps_year_bridge_absent_in_reviewed_sources"
                ),
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                evidence_strength_raw=item.get("reviewed_bridge_evidence_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get("reviewed_source_file_or_sheet", ""),
                source_family=item.get("reviewed_surface", ""),
                source_url_or_key=item.get("source_artifact_path", ""),
                source_snapshot_kind=item.get("source_status", ""),
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class="terminal_blocker_decision_without_bps_year_path",
                transport_risk="high_until_new_source_supplies_bps_year_bridge",
                manual_override_required="false",
                calibration_needed="reviewed_research_parameterization_source",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_mapping", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_gate="policy_path_bps_year_blocker_decision_gate",
                promotion_status="blocked",
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="policy_path_bps_year_blocker_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_bps_year_blocker_decision.csv;"
                    "ratewall_policy_path_mps_scalar_replication_diagnostic.csv;"
                    "ratewall_conventional_drag_research_parameterization_source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_parameterization_source_contract_rows(
    contract_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in contract_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_parameterization_contract_"
                    f"{item.get('contract_scope_id', '')}_"
                    f"{item.get('required_field_name', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_parameterization_source_contract"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                surface_type="source_contract",
                upstream_row_key=item.get("contract_row_id", ""),
                scenario_or_path_scope=item.get("contract_scope_id", ""),
                period_or_horizon=item.get("horizon_bucket", ""),
                value_role=item.get("required_field_name", ""),
                current_value_exact=item.get("current_value_exact", ""),
                current_value_low=item.get("current_value_low", ""),
                current_value_base=item.get("current_value_base", ""),
                current_value_high=item.get("current_value_high", ""),
                unit=item.get("required_unit", ""),
                formula_role=item.get("required_formula_or_method", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="required_source_field_missing",
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get("admissibility_gate_status", ""),
                evidence_strength_raw=item.get("source_backing_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("current_source_artifact", "")
                or item.get("admissible_source_artifact_type", ""),
                source_field_or_series=item.get("required_source_fields", ""),
                source_family="conventional_drag_research_parameterization",
                support_diagnostics_present=item.get(
                    "support_diagnostics_present", "false"
                ),
                directness_class="contract_requirement_not_populated",
                transport_risk="high_until_reviewed_source_contract_populated",
                manual_override_required="false",
                calibration_needed="research_parameterization_source_contract",
                evidence_needed_before_prior_narrowing=item.get(
                    "evidence_needed_before_prior_narrowing", ""
                ),
                evidence_needed_before_promotion=item.get(
                    "evidence_needed_before_promotion", ""
                ),
                promotion_gate=item.get("promotion_gate", ""),
                promotion_status=item.get("promotion_status", "blocked"),
                prior_narrowing_allowed=item.get("prior_narrowing_allowed", "false"),
                formula_replacement_allowed=item.get(
                    "formula_replacement_allowed", "false"
                ),
                split_denominator_promotion_allowed=item.get(
                    "split_denominator_promotion_allowed", "false"
                ),
                allowed_use="source_contract_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv;ratewall_conventional_drag_"
                    "calibration_route.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_parameterization_source_frontier_rows(
    frontier_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in frontier_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_parameterization_source_frontier_"
                    f"{item.get('source_candidate_handle', '')}_"
                    f"{item.get('artifact_handle', '')}_"
                    f"{item.get('required_contract_field', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_parameterization_source_frontier"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_frontier.csv"
                ),
                surface_type="research_parameterization_source_frontier",
                upstream_row_key=item.get("frontier_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                value_role=item.get("required_contract_field", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="source_frontier_not_parameter_value",
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("parser_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("artifact_path", ""),
                source_field_or_series=item.get("parsed_variable_or_file", ""),
                source_family=item.get("source_family", ""),
                support_diagnostics_present="true",
                directness_class="source_frontier_contract_field_review_only",
                transport_risk="high_until_full_contract_fields_pass",
                manual_override_required="false",
                calibration_needed="research_parameterization_source_contract",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use="research_parameterization_source_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_frontier.csv;ratewall_conventional_drag_research_"
                    "parameterization_source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_payload_manifest_rows(
    payload_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in payload_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_payload_manifest_"
                    f"{item.get('source_candidate_handle', '')}_"
                    f"{item.get('payload_manifest_row_id', '')}"
                ),
                assumption_family="conventional_drag_research_payload_manifest",
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_payload_manifest.csv"
                ),
                surface_type="manual_research_payload_manifest",
                upstream_row_key=item.get("payload_manifest_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                value_role=item.get("candidate_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="manual_payload_inventory_not_parameter_value",
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get("payload_presence_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("payload_archive_path", ""),
                source_field_or_series=item.get("inner_file_path", ""),
                source_family="openicpsr_manual_replication_payload",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", "")
                or item.get("payload_archive_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_payload_inventory_review_only",
                transport_risk="high_until_research_parameterization_passes",
                manual_override_required="false",
                calibration_needed="research_parameterization_payload_parser",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_payload_manifest.csv;"
                    "ratewall_openicpsr_replication_package_source_manifest.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_parameterization_parser_status_rows(
    parser_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in parser_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_parameterization_parser_status_"
                    f"{item.get('source_candidate_handle', '')}_"
                    f"{item.get('parser_status_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_parameterization_parser_status"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_parameterization_"
                    "parser_status.csv"
                ),
                surface_type="research_parameterization_parser_status",
                upstream_row_key=item.get("parser_status_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                value_role=item.get("parser_object_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_parser_status_not_parameter_value"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("payload_presence_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("payload_archive_path", ""),
                source_field_or_series=item.get("inner_file_path", ""),
                source_family="openicpsr_manual_replication_payload",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", "")
                or item.get("payload_archive_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_parser_status_review_only",
                transport_risk="high_until_research_parameterization_passes",
                manual_override_required="false",
                calibration_needed="research_parameterization_estimate_parser",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_parameterization_"
                    "parser_status.csv;ratewall_conventional_drag_research_"
                    "payload_manifest.csv;ratewall_conventional_drag_research_"
                    "parameterization_source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_payload_inner_inventory_rows(
    inventory_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in inventory_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_payload_inner_inventory_"
                    f"{item.get('inner_inventory_row_id', '')}"
                ),
                assumption_family="conventional_drag_research_payload_inner_inventory",
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_payload_inner_inventory.csv"
                ),
                surface_type="research_payload_inner_inventory",
                upstream_row_key=item.get("inner_inventory_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                value_role=item.get("payload_file_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_payload_inner_inventory_not_parameter_value"
                ),
                source_status_raw=item.get("source_admission_status", ""),
                calibration_status_raw=item.get("payload_presence_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("payload_archive_path", ""),
                source_field_or_series=item.get("inner_file_path", "")
                or item.get("expected_payload_role", ""),
                source_family="openicpsr_manual_replication_payload",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", "")
                or item.get("payload_archive_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_payload_inner_inventory_review_only",
                transport_risk="high_until_research_parameterization_passes",
                manual_override_required="false",
                calibration_needed="research_parameterization_payload_extraction",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_payload_inner_inventory.csv;"
                    "ratewall_conventional_drag_research_payload_manifest.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_extraction_candidate_rows(
    extraction_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in extraction_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_extraction_candidate_"
                    f"{item.get('extraction_candidate_row_id', '')}"
                ),
                assumption_family="conventional_drag_research_extraction_candidate",
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_extraction_candidate.csv"
                ),
                surface_type="research_extraction_candidate",
                upstream_row_key=item.get("extraction_candidate_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                period_or_horizon=item.get("horizon_q", ""),
                value_role=item.get("parser_object_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit=item.get("raw_unit", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_extraction_candidate_not_parameter_value"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_compatibility_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("payload_archive_path", ""),
                source_field_or_series=item.get("inner_file_path", ""),
                source_family="openicpsr_manual_replication_payload",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", "")
                or item.get("payload_archive_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_extraction_candidate_review_only",
                transport_risk="high_until_research_parameterization_passes",
                manual_override_required="false",
                calibration_needed="research_parameterization_gate_pass",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_research_payload_inner_inventory.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_extraction_gate_audit_rows(
    gate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in gate_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_extraction_gate_audit_"
                    f"{item.get('gate_audit_row_id', '')}"
                ),
                assumption_family="conventional_drag_research_extraction_gate_audit",
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_extraction_gate_audit.csv"
                ),
                surface_type="research_extraction_gate_audit",
                upstream_row_key=item.get("gate_audit_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("required_gate", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_extraction_gate_audit_not_parameter_value"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("gate_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=(
                    "ratewall_conventional_drag_research_extraction_candidate.csv"
                ),
                source_field_or_series=item.get("target_outcome_id", ""),
                source_family="openicpsr_manual_replication_payload",
                source_record_count=item.get("extraction_candidate_row_count", ""),
                support_diagnostics_present="true",
                directness_class="research_extraction_gate_audit_review_only",
                transport_risk="high_until_all_research_gates_pass",
                manual_override_required="false",
                calibration_needed="all_research_parameterization_gates",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_extraction_gate_audit.csv;"
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_extraction_gate_detail_rows(
    gate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in gate_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_extraction_gate_detail_"
                    f"{item.get('gate_detail_row_id', '')}"
                ),
                assumption_family="conventional_drag_research_extraction_gate_detail",
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_extraction_gate_detail.csv"
                ),
                surface_type="research_extraction_gate_detail",
                upstream_row_key=item.get("gate_detail_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                period_or_horizon=item.get("source_horizon_index", ""),
                value_role=item.get("required_gate", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_extraction_gate_detail_not_parameter_value"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("gate_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("payload_archive_path_sample", ""),
                source_field_or_series=item.get("source_method_object_family", ""),
                source_family="openicpsr_manual_replication_payload",
                source_record_count=item.get("extraction_candidate_row_count", ""),
                source_hash_or_manifest_hash=item.get("inner_file_sha256_sample", "")
                or item.get("payload_archive_sha256_sample", ""),
                support_diagnostics_present="true",
                directness_class="research_extraction_gate_detail_review_only",
                transport_risk="high_until_all_research_gates_pass",
                manual_override_required="false",
                calibration_needed="all_research_parameterization_gates",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_extraction_gate_detail.csv;"
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_source_method_bridge_rows(
    bridge_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in bridge_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_source_method_bridge_"
                    f"{item.get('source_method_bridge_row_id', '')}"
                ),
                assumption_family="conventional_drag_research_source_method_bridge",
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_source_method_bridge.csv"
                ),
                surface_type="research_source_method_bridge",
                upstream_row_key=item.get("source_method_bridge_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                period_or_horizon=item.get("source_horizon_index", ""),
                value_role=item.get("source_statistic_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_source_method_bridge_not_parameter_value"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("parser_readiness_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("payload_archive_path_sample", ""),
                source_field_or_series=item.get("source_method_object_family", ""),
                source_family="openicpsr_manual_replication_payload",
                source_record_count=item.get("gate_detail_group_count", ""),
                source_hash_or_manifest_hash=item.get("inner_file_sha256_sample", "")
                or item.get("payload_archive_sha256_sample", ""),
                support_diagnostics_present="true",
                directness_class="research_source_method_bridge_review_only",
                transport_risk="high_until_all_research_gates_pass",
                manual_override_required=item.get("manual_interpretation_required", ""),
                calibration_needed="all_research_parameterization_gates",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_source_method_bridge.csv;"
                    "ratewall_conventional_drag_research_extraction_gate_detail.csv;"
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_source_code_interpretation_rows(
    interpretation_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in interpretation_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_source_code_interpretation_"
                    f"{item.get('source_code_interpretation_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_source_code_interpretation"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_source_code_"
                    "interpretation.csv"
                ),
                surface_type="research_source_code_interpretation",
                upstream_row_key=item.get("source_code_interpretation_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                period_or_horizon=item.get("source_horizon_index", ""),
                value_role=item.get("estimation_method", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_source_code_interpretation_not_parameter_value"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("source_code_review_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("payload_archive_path", ""),
                source_field_or_series=item.get("source_script_paths", ""),
                source_family="openicpsr_manual_replication_payload",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("source_script_sha256s", "")
                or item.get("payload_archive_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_source_code_interpretation_review_only",
                transport_risk="high_until_all_research_gates_pass",
                manual_override_required=item.get("manual_interpretation_required", ""),
                calibration_needed="all_research_parameterization_gates",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_source_code_"
                    "interpretation.csv;"
                    "ratewall_conventional_drag_research_source_method_bridge.csv;"
                    "ratewall_conventional_drag_research_extraction_candidate.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_extended_source_code_interpretation_rows(
    interpretation_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in interpretation_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_extended_source_code_"
                    f"interpretation_{item.get('extended_source_code_interpretation_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_extended_source_code_interpretation"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_extended_source_code_"
                    "interpretation.csv"
                ),
                surface_type="research_extended_source_code_interpretation",
                upstream_row_key=item.get(
                    "extended_source_code_interpretation_row_id", ""
                ),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("coverage_gap_priority", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_extended_source_code_interpretation_not_parameter_value"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("target_contract_blocker_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("payload_archive_path", ""),
                source_field_or_series=item.get("source_script_paths", ""),
                source_family=item.get("source_family", ""),
                source_record_count=item.get("source_irf_variant_count", ""),
                source_hash_or_manifest_hash=item.get("source_script_sha256s", "")
                or item.get("payload_archive_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_extended_source_code_interpretation_review_only",
                transport_risk="high_until_all_research_gates_pass",
                manual_override_required="true",
                calibration_needed="all_research_parameterization_gates",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_extended_source_code_"
                    "interpretation.csv;"
                    "ratewall_conventional_drag_research_source_method_bridge.csv;"
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_fspdp_coverage_candidate_scan_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_fspdp_coverage_candidate_scan_"
                    f"{item.get('fspdp_coverage_candidate_scan_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_fspdp_coverage_candidate_scan"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_fspdp_coverage_"
                    "candidate_scan.csv"
                ),
                surface_type="research_fspdp_coverage_candidate_scan",
                upstream_row_key=item.get(
                    "fspdp_coverage_candidate_scan_row_id", ""
                ),
                scenario_or_path_scope=item.get("coverage_target_id", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role="fspdp_coverage_candidate_scan_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_fspdp_coverage_candidate_scan_not_parameter_value"
                ),
                source_status_raw=item.get("fspdp_coverage_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("candidate_inner_file_paths", ""),
                source_field_or_series=item.get(
                    "candidate_source_outcome_labels", ""
                ),
                source_family="research FSPDP coverage candidate scan",
                source_record_count=item.get("candidate_extraction_row_count", ""),
                source_hash_or_manifest_hash=item.get(
                    "candidate_inner_file_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="research_fspdp_coverage_candidate_scan_review_only",
                transport_risk=(
                    "high_until_source_unit_component_weight_fspdp_coverage_"
                    "policy_path_replication_robustness_and_promotion_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_unit_conversion_component_weights_fspdp_coverage_"
                    "policy_path_100bp_year_normalization_replication_"
                    "robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _mir_component_aggregation_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_mir_component_aggregation_"
                    f"{item.get('component_aggregation_review_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_mir_component_aggregation_review"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_mir_component_"
                    "aggregation_normalization_review.csv"
                ),
                surface_type="research_component_aggregation_review",
                upstream_row_key=item.get("component_aggregation_review_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("component_evidence_class", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_component_aggregation_normalization_review"
                ),
                source_status_raw=item.get(
                    "component_aggregation_readiness_status", ""
                ),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("supporting_inner_file_paths", ""),
                source_field_or_series=item.get("source_outcome_label", ""),
                source_family="openicpsr_manual_replication_payload",
                source_record_count=item.get("supporting_source_variant_count", ""),
                source_hash_or_manifest_hash=item.get(
                    "supporting_inner_file_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="research_component_aggregation_review_only",
                transport_risk="high_until_component_aggregation_gates_pass",
                manual_override_required="true",
                calibration_needed="component_weights_unit_bridge_and_promotion",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_source_code_"
                    "interpretation.csv;"
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_current_demand_mapping_bridge.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _mir_component_source_variant_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_mir_component_source_variant_"
                    f"{item.get('component_source_variant_review_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_mir_component_source_variant_review"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_mir_component_"
                    "source_variant_review.csv"
                ),
                surface_type="research_component_source_variant_review",
                upstream_row_key=item.get(
                    "component_source_variant_review_row_id", ""
                ),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("support_variant_conflict_status", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="blocked_component_source_variant_review",
                source_status_raw=item.get("support_variant_conflict_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("inner_file_path", ""),
                source_field_or_series=item.get("source_object_name", ""),
                source_family="openicpsr_manual_replication_payload",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_component_source_variant_review_only",
                transport_risk="high_until_variant_selection_rule_passes",
                manual_override_required="true",
                calibration_needed="variant_selection_and_all_research_gates",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_source_code_"
                    "interpretation.csv;"
                    "ratewall_conventional_drag_research_extraction_candidate.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_fspdp_component_decomposition_bridge_rows(
    bridge_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in bridge_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_fspdp_component_decomposition_"
                    f"{item.get('decomposition_bridge_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_fspdp_component_decomposition_bridge"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_fspdp_component_"
                    "decomposition_bridge.csv"
                ),
                surface_type="fspdp_component_decomposition_bridge",
                upstream_row_key=item.get("decomposition_bridge_row_id", ""),
                scenario_or_path_scope=item.get("target_outcome_id", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("decomposition_component_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_fspdp_component_decomposition_requirement_review"
                ),
                source_status_raw=item.get("component_weight_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_url", ""),
                source_field_or_series=item.get("source_series_id", ""),
                source_family=item.get("source_family", ""),
                source_record_count=item.get("source_record_count", ""),
                source_hash_or_manifest_hash=item.get("source_snapshot_sha256", ""),
                support_diagnostics_present="true",
                directness_class="fspdp_component_requirement_review_only",
                transport_risk="high_until_component_weights_and_unit_bridges_pass",
                manual_override_required="true",
                calibration_needed=(
                    "component_weights_unit_bridge_proxy_bridge_100bp_year_"
                    "normalization_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_fspdp_component_decomposition_"
                    "bridge.csv;"
                    "ratewall_conventional_drag_research_mir_component_"
                    "aggregation_normalization_review.csv;"
                    "ratewall_conventional_drag_research_mir_component_"
                    "source_variant_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_fspdp_coverage_weight_requirement_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_fspdp_coverage_weight_requirement_"
                    f"{item.get('coverage_weight_review_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_fspdp_coverage_weight_requirement_review"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_fspdp_coverage_weight_"
                    "requirement_review.csv"
                ),
                surface_type="fspdp_coverage_weight_requirement_review",
                upstream_row_key=item.get("coverage_weight_review_row_id", ""),
                scenario_or_path_scope=item.get("coverage_target_id", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("required_component_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_fspdp_coverage_weight_requirement_review"
                ),
                source_status_raw=item.get("component_share_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_url", ""),
                source_field_or_series=item.get("source_series_id", ""),
                source_family=item.get("source_family", ""),
                source_record_count=item.get("source_record_count", ""),
                source_hash_or_manifest_hash=item.get("source_snapshot_sha256", ""),
                support_diagnostics_present="true",
                directness_class="fspdp_coverage_weight_requirement_review_only",
                transport_risk=(
                    "high_until_component_irf_or_proxy_bridge_unit_path_"
                    "replication_robustness_and_promotion_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "component_irf_or_proxy_bridge_source_unit_conversion_"
                    "100bp_year_normalization_gdp_share_conversion_"
                    "replication_robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_fspdp_coverage_"
                    "candidate_scan.csv;"
                    "ratewall_conventional_drag_fspdp_component_decomposition_"
                    "bridge.csv;"
                    "ratewall_conventional_drag_fspdp_component_share_panel.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_fspdp_coverage_priority_search_queue_rows(
    queue_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in queue_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_fspdp_coverage_priority_search_queue_"
                    f"{item.get('coverage_priority_search_queue_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_fspdp_coverage_priority_search_queue"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_fspdp_coverage_priority_"
                    "search_queue.csv"
                ),
                surface_type="fspdp_coverage_priority_search_queue",
                upstream_row_key=item.get("coverage_priority_search_queue_row_id", ""),
                scenario_or_path_scope=item.get("coverage_target_id", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("search_action_id", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_fspdp_coverage_priority_search_queue"
                ),
                source_status_raw=item.get("source_hash_status", ""),
                calibration_status_raw=item.get("queue_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_url", ""),
                source_field_or_series=item.get("source_series_id", ""),
                source_family=item.get("expected_source_artifact_handles", ""),
                source_record_count=item.get("source_record_count", ""),
                source_hash_or_manifest_hash=item.get("relevant_source_hashes", ""),
                support_diagnostics_present="true",
                directness_class="fspdp_coverage_priority_search_queue_review_only",
                transport_risk=(
                    "high_until_search_queue_item_closes_component_coverage_unit_"
                    "path_uncertainty_replication_robustness_and_promotion"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "execute_search_action_and_pass_component_coverage_source_unit_"
                    "policy_path_gdp_share_uncertainty_replication_robustness_"
                    "provenance_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_fspdp_coverage_weight_"
                    "requirement_review.csv;ratewall_conventional_drag_research_"
                    "fspdp_coverage_candidate_scan.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_fspdp_source_code_search_review_rows(
    search_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in search_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_fspdp_source_code_search_review_"
                    f"{item.get('source_code_search_review_row_id', '')}"
                ),
                assumption_family="conventional_drag_fspdp_source_code_search_review",
                artifact_or_surface=(
                    "ratewall_conventional_drag_fspdp_source_code_search_review.csv"
                ),
                surface_type="fspdp_source_code_search_review",
                upstream_row_key=item.get("source_code_search_review_row_id", ""),
                scenario_or_path_scope=item.get("coverage_target_id", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("source_code_search_hit_status", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="blocked_fspdp_source_code_search_review",
                source_status_raw=item.get("source_code_search_result_status", ""),
                calibration_status_raw=item.get(
                    "source_code_search_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("matched_inner_file_paths", ""),
                source_field_or_series=item.get("matched_source_object_names", ""),
                source_family=item.get("matched_source_candidate_handles", ""),
                source_record_count=item.get("matched_extraction_candidate_count", ""),
                source_hash_or_manifest_hash=item.get(
                    "matched_inner_file_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="fspdp_source_code_search_review_only",
                transport_risk=(
                    "high_until_matched_payload_objects_are_converted_to_"
                    "source_unit_component_irfs_with_path_gdp_share_uncertainty_"
                    "replication_robustness_and_promotion"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "review_matched_payload_objects_and_pass_component_coverage_"
                    "source_unit_policy_path_gdp_share_uncertainty_replication_"
                    "robustness_provenance_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_fspdp_coverage_priority_"
                    "search_queue.csv;ratewall_conventional_drag_research_"
                    "extraction_candidate.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_fspdp_external_source_acquisition_action_plan_rows(
    plan_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in plan_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_fspdp_external_source_acquisition_"
                    f"{item.get('external_source_acquisition_action_plan_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_fspdp_external_source_acquisition_action_plan"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_fspdp_external_source_acquisition_"
                    "action_plan.csv"
                ),
                surface_type="fspdp_external_source_acquisition_action_plan",
                upstream_row_key=item.get(
                    "external_source_acquisition_action_plan_row_id", ""
                ),
                scenario_or_path_scope=item.get("coverage_target_id", ""),
                period_or_horizon=item.get("target_horizon_quarters_covered", ""),
                value_role=item.get("source_acquisition_track", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_fspdp_external_source_acquisition_action_plan"
                ),
                source_status_raw=item.get("source_acquisition_plan_status", ""),
                calibration_status_raw=item.get("source_acquisition_plan_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("expected_source_url_or_handle", ""),
                source_field_or_series=item.get("expected_files_or_tables", ""),
                source_family=item.get("source_candidate_family", ""),
                source_record_count=item.get("linked_search_review_row_count", ""),
                source_hash_or_manifest_hash=item.get(
                    "existing_source_artifact_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="fspdp_external_source_acquisition_action_plan_only",
                transport_risk=(
                    "high_until_acquired_source_closes_component_coverage_unit_"
                    "path_gdp_share_uncertainty_replication_robustness_and_promotion"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "acquire_parse_hash_and_gate_review_source_before_any_"
                    "denominator_use"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_fspdp_source_code_search_review.csv;"
                    "ratewall_conventional_drag_fspdp_component_source_manifest.csv;"
                    "ratewall_frbus_benchmark_comparison_mapping_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_fspdp_official_component_source_acquisition_execution_rows(
    execution_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in execution_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_fspdp_official_component_source_"
                    f"{item.get('official_component_source_acquisition_execution_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_fspdp_official_component_source_acquisition_execution"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_fspdp_official_component_source_"
                    "acquisition_execution.csv"
                ),
                surface_type="fspdp_official_component_source_acquisition_execution",
                upstream_row_key=item.get(
                    "official_component_source_acquisition_execution_row_id", ""
                ),
                scenario_or_path_scope=item.get("component_id", ""),
                period_or_horizon=item.get("frequency", ""),
                value_role=item.get("measure_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_fspdp_official_component_source_acquisition_execution"
                ),
                source_status_raw=item.get("acquisition_execution_status", ""),
                calibration_status_raw=item.get("acquisition_execution_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("raw_source_path", ""),
                source_field_or_series=item.get("series_id", ""),
                source_family=item.get("source_table_or_family", ""),
                source_record_count=item.get("source_record_count", ""),
                source_hash_or_manifest_hash=item.get("raw_source_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "official_component_source_data_not_research_irf_or_denominator"
                ),
                transport_risk=(
                    "high_until_research_irf_source_unit_policy_path_gdp_share_"
                    "uncertainty_replication_robustness_and_promotion_gates_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "direct_research_irf_and_unit_policy_path_conversion_needed"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_fspdp_external_source_acquisition_action_plan.csv;"
                    "ratewall_conventional_drag_fspdp_component_source_manifest.csv;"
                    "ratewall_conventional_drag_fspdp_component_share_panel.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_fspdp_research_side_action_plan_extraction_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_fspdp_research_side_extraction_"
                    f"{item.get('research_side_extraction_review_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_fspdp_research_side_action_plan_extraction_review"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_fspdp_research_side_action_plan_"
                    "extraction_review.csv"
                ),
                surface_type="fspdp_research_side_action_plan_extraction_review",
                upstream_row_key=item.get("research_side_extraction_review_row_id", ""),
                scenario_or_path_scope=item.get("coverage_target_id", ""),
                period_or_horizon=item.get("target_horizon_quarters_covered", ""),
                value_role=item.get("source_acquisition_track", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_fspdp_research_side_action_plan_extraction_review"
                ),
                source_status_raw=item.get("research_side_extraction_review_status", ""),
                calibration_status_raw=item.get(
                    "research_side_extraction_review_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("matched_inner_file_paths", ""),
                source_field_or_series=item.get("expected_research_outcome_labels", ""),
                source_family=item.get("source_candidate_family", ""),
                source_record_count=item.get("linked_extraction_candidate_count", ""),
                source_hash_or_manifest_hash=item.get("matched_inner_file_sha256s", ""),
                support_diagnostics_present="true",
                directness_class="research_side_action_plan_extraction_review_only",
                transport_risk=(
                    "high_until_direct_irf_source_unit_policy_path_gdp_share_"
                    "uncertainty_replication_robustness_and_promotion_gates_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "direct_research_irf_or_benchmark_extension_and_gate_review_needed"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_fspdp_external_source_acquisition_action_plan.csv;"
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_research_extended_source_code_interpretation.csv;"
                    "ratewall_frbus_runtime_runner_output_slots.csv;"
                    "ratewall_conventional_drag_fspdp_official_component_source_acquisition_execution.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_source_unit_conversion_review_rows(
    conversion_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in conversion_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_source_unit_conversion_"
                    f"{item.get('source_unit_conversion_review_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_source_unit_conversion_review"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_source_unit_"
                    "conversion_review.csv"
                ),
                surface_type="research_source_unit_conversion_review",
                upstream_row_key=item.get("source_unit_conversion_review_row_id", ""),
                scenario_or_path_scope=item.get("target_outcome_id", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role="source_unit_conversion_review_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_source_unit_conversion_review_not_drag_estimate"
                ),
                source_status_raw=item.get("conversion_feasibility_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("component_source_snapshot_path", ""),
                source_field_or_series=item.get("component_source_series_id", ""),
                source_family=item.get("component_source_family", ""),
                source_record_count=item.get("component_source_record_count", ""),
                source_hash_or_manifest_hash=item.get(
                    "component_source_snapshot_sha256", ""
                ),
                support_diagnostics_present="true",
                directness_class="research_source_unit_conversion_review_only",
                transport_risk="high_until_unit_sign_path_and_aggregation_pass",
                manual_override_required="true",
                calibration_needed=(
                    "source_irf_unit_sign_proxy_bridge_100bp_year_uncertainty_"
                    "replication_robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_source_unit_"
                    "conversion_review.csv;"
                    "ratewall_conventional_drag_research_mir_component_"
                    "aggregation_normalization_review.csv;"
                    "ratewall_conventional_drag_fspdp_component_"
                    "decomposition_bridge.csv;"
                    "ratewall_conventional_drag_fspdp_component_share_panel.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_mir_replication_source_unit_audit_rows(
    audit_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in audit_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_mir_replication_source_unit_"
                    f"{item.get('mir_replication_source_unit_audit_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_mir_replication_source_unit_audit"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_mir_replication_"
                    "source_unit_audit.csv"
                ),
                surface_type="research_mir_replication_source_unit_audit",
                upstream_row_key=item.get(
                    "mir_replication_source_unit_audit_row_id", ""
                ),
                scenario_or_path_scope=item.get("source_outcome_label", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role="mir_replication_source_unit_audit_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_mir_replication_source_unit_audit_not_drag_estimate"
                ),
                source_status_raw=item.get("mat_payload_reproduction_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("inner_file_path", ""),
                source_field_or_series=item.get("source_object_name", ""),
                source_family="Miranda-Agrippino-Ricco openICPSR payload",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_mir_replication_source_unit_audit_only",
                transport_risk="high_until_runtime_unit_sign_path_and_promotion_pass",
                manual_override_required="true",
                calibration_needed=(
                    "runtime_execution_source_unit_transform_sign_horizon_100bp_"
                    "year_uncertainty_replication_robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_mir_replication_"
                    "source_unit_audit.csv;"
                    "ratewall_conventional_drag_research_mir_component_"
                    "source_variant_review.csv;"
                    "ratewall_conventional_drag_research_source_code_"
                    "interpretation.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_mir_source_unit_transformation_contract_rows(
    contract_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in contract_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_mir_source_unit_transformation_"
                    f"{item.get('mir_source_unit_transformation_contract_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_mir_source_unit_transformation_contract"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_mir_source_unit_"
                    "transformation_contract.csv"
                ),
                surface_type="research_mir_source_unit_transformation_contract",
                upstream_row_key=item.get(
                    "mir_source_unit_transformation_contract_row_id", ""
                ),
                scenario_or_path_scope=item.get("source_outcome_label", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role="mir_source_unit_transformation_contract_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_mir_source_unit_transformation_contract_not_drag_estimate"
                ),
                source_status_raw=item.get("transformation_contract_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("fred_md_source_path", ""),
                source_field_or_series=item.get("source_outcome_label", ""),
                source_family=(
                    "Miranda-Agrippino-Ricco FRED-MD source transform metadata"
                ),
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("fred_md_source_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "research_mir_source_unit_transformation_contract_only"
                ),
                transport_risk=(
                    "high_until_target_horizon_policy_path_gdp_share_and_"
                    "promotion_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "target_horizon_100bp_year_gdp_share_sign_uncertainty_"
                    "robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_mir_source_unit_"
                    "transformation_contract.csv;"
                    "ratewall_conventional_drag_research_mir_replication_"
                    "source_unit_audit.csv;"
                    "ratewall_conventional_drag_research_mir_component_"
                    "source_variant_review.csv;"
                    "ratewall_conventional_drag_research_source_code_"
                    "interpretation.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_mir_target_horizon_reconciliation_contract_rows(
    contract_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in contract_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_mir_target_horizon_"
                    f"{item.get('mir_target_horizon_reconciliation_contract_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_mir_target_horizon_reconciliation_contract"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_mir_target_horizon_"
                    "reconciliation_contract.csv"
                ),
                surface_type="research_mir_target_horizon_reconciliation_contract",
                upstream_row_key=item.get(
                    "mir_target_horizon_reconciliation_contract_row_id", ""
                ),
                scenario_or_path_scope=item.get("source_outcome_label", ""),
                period_or_horizon=item.get("ratewall_target_horizon_bucket", ""),
                value_role="mir_target_horizon_reconciliation_contract_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_mir_target_horizon_reconciliation_contract_not_drag_estimate"
                ),
                source_status_raw=item.get("target_horizon_reconciliation_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("inner_file_path", ""),
                source_field_or_series=item.get("source_object_name", ""),
                source_family=(
                    "Miranda-Agrippino-Ricco source horizon and plotting metadata"
                ),
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "research_mir_target_horizon_reconciliation_contract_only"
                ),
                transport_risk="high_until_source_month_horizon_rekeyed_to_ratewall_bucket",
                manual_override_required="true",
                calibration_needed=(
                    "target_horizon_rekeying_100bp_year_gdp_share_uncertainty_"
                    "robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_mir_target_horizon_"
                    "reconciliation_contract.csv;"
                    "ratewall_conventional_drag_research_mir_source_unit_"
                    "transformation_contract.csv;"
                    "ratewall_conventional_drag_research_mir_replication_"
                    "source_unit_audit.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_mir_horizon_rekeying_candidate_review_rows(
    rekey_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in rekey_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_mir_horizon_rekeying_"
                    f"{item.get('mir_horizon_rekeying_candidate_review_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_mir_horizon_rekeying_candidate_review"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_mir_horizon_"
                    "rekeying_candidate_review.csv"
                ),
                surface_type="research_mir_horizon_rekeying_candidate_review",
                upstream_row_key=item.get(
                    "mir_horizon_rekeying_candidate_review_row_id", ""
                ),
                scenario_or_path_scope=item.get("source_outcome_label", ""),
                period_or_horizon=item.get("ratewall_candidate_horizon_bucket", ""),
                value_role="mir_horizon_rekeying_candidate_review_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_mir_horizon_rekeying_candidate_review_not_drag_estimate"
                ),
                source_status_raw=item.get("candidate_rekey_review_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("inner_file_path", ""),
                source_field_or_series=item.get("source_object_name", ""),
                source_family=(
                    "Miranda-Agrippino-Ricco source horizon rekeying review"
                ),
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_mir_horizon_rekeying_candidate_review_only",
                transport_risk="high_until_rekeying_promotion_and_denominator_gates_pass",
                manual_override_required="true",
                calibration_needed=(
                    "rekeyed_horizon_extraction_100bp_year_gdp_share_uncertainty_"
                    "robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_mir_horizon_"
                    "rekeying_candidate_review.csv;"
                    "ratewall_conventional_drag_research_mir_target_horizon_"
                    "reconciliation_contract.csv;"
                    "ratewall_conventional_drag_research_mir_source_unit_"
                    "transformation_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_mir_h24_source_unit_audit_rows(
    audit_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in audit_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_mir_h24_source_unit_"
                    f"{item.get('mir_h24_source_unit_audit_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_mir_h24_source_unit_audit"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_mir_h24_source_unit_"
                    "audit.csv"
                ),
                surface_type="research_mir_h24_source_unit_audit",
                upstream_row_key=item.get("mir_h24_source_unit_audit_row_id", ""),
                scenario_or_path_scope=item.get("source_outcome_label", ""),
                period_or_horizon="8q",
                value_role="mir_h24_source_unit_audit_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_mir_h24_source_unit_audit_not_drag_estimate"
                ),
                source_status_raw=item.get("mat_payload_reproduction_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("inner_file_path", ""),
                source_field_or_series=item.get("source_object_name", ""),
                source_family="Miranda-Agrippino-Ricco h24 source-unit audit",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_mir_h24_source_unit_audit_only",
                transport_risk="high_until_h24_unit_sign_and_denominator_gates_pass",
                manual_override_required="true",
                calibration_needed=(
                    "h24_unit_sign_100bp_year_gdp_share_uncertainty_robustness_"
                    "and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_research_source_code_"
                    "interpretation.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_mir_h24_8q_rekeying_review_rows(
    rekey_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in rekey_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_mir_h24_8q_rekeying_"
                    f"{item.get('mir_h24_8q_rekeying_review_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_mir_h24_8q_rekeying_review"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_mir_h24_8q_rekeying_"
                    "review.csv"
                ),
                surface_type="research_mir_h24_8q_rekeying_review",
                upstream_row_key=item.get("mir_h24_8q_rekeying_review_row_id", ""),
                scenario_or_path_scope=item.get("source_outcome_label", ""),
                period_or_horizon=item.get("ratewall_candidate_horizon_bucket", ""),
                value_role="mir_h24_8q_rekeying_review_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_mir_h24_8q_rekeying_review_not_drag_estimate"
                ),
                source_status_raw=item.get("candidate_rekey_review_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("inner_file_path", ""),
                source_field_or_series=item.get("source_object_name", ""),
                source_family="Miranda-Agrippino-Ricco h24-to-8q rekeying review",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", ""),
                support_diagnostics_present="true",
                directness_class="research_mir_h24_8q_rekeying_review_only",
                transport_risk="high_until_8q_rekeying_denominator_gates_pass",
                manual_override_required="true",
                calibration_needed=(
                    "8q_rekeying_100bp_year_gdp_share_uncertainty_robustness_"
                    "and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_mir_h24_source_unit_"
                    "audit.csv;ratewall_conventional_drag_research_extraction_"
                    "candidate.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_mir_4q8q_conversion_readiness_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_mir_4q8q_conversion_readiness_"
                    f"{item.get('mir_4q8q_conversion_readiness_review_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_mir_4q8q_conversion_readiness_review"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_mir_4q8q_conversion_"
                    "readiness_review.csv"
                ),
                surface_type="research_mir_4q8q_conversion_readiness_review",
                upstream_row_key=item.get(
                    "mir_4q8q_conversion_readiness_review_row_id", ""
                ),
                scenario_or_path_scope=item.get("source_outcome_label", ""),
                period_or_horizon=item.get("ratewall_candidate_horizon_bucket", ""),
                value_role="mir_4q8q_conversion_readiness_review_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_mir_4q8q_conversion_readiness_review_not_drag_estimate"
                ),
                source_status_raw=item.get("conversion_readiness_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("inner_file_path", ""),
                source_field_or_series=item.get("source_object_name", ""),
                source_family=(
                    "Miranda-Agrippino-Ricco 4q/8q conversion readiness review"
                ),
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("inner_file_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "research_mir_4q8q_conversion_readiness_review_only"
                ),
                transport_risk="high_until_conversion_readiness_gates_pass",
                manual_override_required="true",
                calibration_needed=(
                    "source_unit_sign_component_coverage_proxy_path_100bp_year_"
                    "uncertainty_replication_robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_mir_horizon_rekeying_"
                    "candidate_review.csv;ratewall_conventional_drag_research_"
                    "mir_h24_8q_rekeying_review.csv;ratewall_conventional_drag_"
                    "fspdp_component_decomposition_bridge.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_policy_path_normalization_bridge_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_policy_path_normalization_"
                    f"{item.get('policy_path_normalization_bridge_review_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_policy_path_normalization_bridge_review"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_policy_path_normalization_"
                    "bridge_review.csv"
                ),
                surface_type="research_policy_path_normalization_bridge_review",
                upstream_row_key=item.get(
                    "policy_path_normalization_bridge_review_row_id", ""
                ),
                scenario_or_path_scope=item.get("research_shock_handle", ""),
                period_or_horizon=item.get("ratewall_candidate_horizon_bucket", ""),
                value_role=item.get("admission_gate", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_policy_path_normalization_bridge_review_not_bps_year"
                ),
                source_status_raw=item.get("gate_review_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=(
                    item.get("inner_file_path", "")
                    or item.get("payload_archive_path", "")
                ),
                source_field_or_series=item.get("formula_step", ""),
                source_family=(
                    "research policy-path normalization bridge review"
                ),
                source_record_count="1",
                source_hash_or_manifest_hash=(
                    item.get("inner_file_sha256", "")
                    or item.get("payload_archive_sha256", "")
                ),
                support_diagnostics_present="true",
                directness_class=(
                    "research_policy_path_normalization_bridge_review_only"
                ),
                transport_risk=(
                    "high_until_source_backed_policy_path_bps_year_gates_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "policy_path_vector_event_horizon_mapping_loading_back_"
                    "transform_bps_year_integral_replication_uncertainty_"
                    "robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_mir_4q8q_conversion_"
                    "readiness_review.csv;ratewall_conventional_drag_research_"
                    "extended_source_code_interpretation.csv;ratewall_"
                    "conventional_drag_research_extraction_candidate.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_research_shock_source_evidence_protocol_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_research_shock_source_evidence_protocol_"
                    f"{item.get('source_evidence_protocol_review_row_id', '')}"
                ),
                assumption_family=(
                    "policy_path_research_shock_source_evidence_protocol_review"
                ),
                artifact_or_surface=(
                    "ratewall_policy_path_research_shock_source_evidence_"
                    "protocol_review.csv"
                ),
                surface_type=(
                    "policy_path_research_shock_source_evidence_protocol_review"
                ),
                upstream_row_key=item.get(
                    "source_evidence_protocol_review_row_id", ""
                ),
                scenario_or_path_scope=item.get("research_shock_handle", ""),
                period_or_horizon=item.get("required_protocol_field", ""),
                value_role="source_evidence_protocol_review_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_research_shock_source_evidence_protocol_not_bps_year"
                ),
                source_status_raw=item.get("source_evidence_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("required_protocol_field", ""),
                source_family="policy-path research shock evidence protocol review",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "policy_path_research_shock_source_evidence_review_only"
                ),
                transport_risk=(
                    "high_until_complete_source_backed_bps_year_protocol_passes"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_backed_path_vector_event_horizon_mapping_loading_"
                    "back_transform_bps_year_integral_replication_uncertainty_"
                    "robustness_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_source_acquisition_registry.csv;"
                    "ratewall_policy_path_protocol_review_inventory.csv;"
                    "ratewall_policy_path_source_cell_unit_contract_review.csv;"
                    "ratewall_conventional_drag_research_policy_path_"
                    "normalization_bridge_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_source_code_workbook_object_inventory_rows(
    inventory_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in inventory_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_source_code_workbook_object_inventory_"
                    f"{item.get('source_object_inventory_row_id', '')}"
                ),
                assumption_family="policy_path_source_code_workbook_object_inventory",
                artifact_or_surface=(
                    "ratewall_policy_path_source_code_workbook_object_inventory.csv"
                ),
                surface_type="policy_path_source_code_workbook_object_inventory",
                upstream_row_key=item.get("source_object_inventory_row_id", ""),
                scenario_or_path_scope=item.get("source_bundle_handle", ""),
                period_or_horizon=item.get("object_role", ""),
                value_role="source_code_workbook_object_review_status",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_source_code_workbook_inventory_not_bps_year"
                ),
                source_status_raw=item.get("object_protocol_review_status", ""),
                calibration_status_raw=item.get("object_protocol_review_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("object_path", ""),
                source_family="policy-path source-code/workbook object inventory",
                source_record_count="1",
                source_hash_or_manifest_hash=(
                    item.get("object_sha256", "")
                    or item.get("source_artifact_sha256", "")
                ),
                support_diagnostics_present="true",
                directness_class="source_code_workbook_object_inventory_review_only",
                transport_risk=(
                    "high_until_complete_source_backed_bps_year_protocol_passes"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_code_workbook_unit_path_vector_event_horizon_grid_"
                    "loading_back_transform_integral_replication_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_research_shock_source_evidence_"
                    "protocol_review.csv;raw_policy_path_protocol_sources"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_source_code_workbook_protocol_deep_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_source_code_workbook_protocol_deep_review_"
                    f"{item.get('source_protocol_deep_review_row_id', '')}"
                ),
                assumption_family=(
                    "policy_path_source_code_workbook_protocol_deep_review"
                ),
                artifact_or_surface=(
                    "ratewall_policy_path_source_code_workbook_protocol_deep_"
                    "review.csv"
                ),
                surface_type="policy_path_source_code_workbook_protocol_deep_review",
                upstream_row_key=item.get("source_protocol_deep_review_row_id", ""),
                scenario_or_path_scope=item.get("source_bundle_handle", ""),
                period_or_horizon=item.get("required_protocol_field", ""),
                value_role="source_code_workbook_protocol_deep_review_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_source_code_workbook_protocol_not_bps_year"
                ),
                source_status_raw=item.get("deep_review_evidence_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("required_protocol_field", ""),
                source_family="policy-path source-code/workbook protocol deep review",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "source_code_workbook_protocol_deep_review_only"
                ),
                transport_risk=(
                    "high_until_complete_source_backed_bps_year_protocol_passes"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "unit_path_vector_event_horizon_grid_loading_back_transform_"
                    "integral_replication_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_source_code_workbook_object_inventory.csv;"
                    "ratewall_policy_path_research_shock_source_evidence_"
                    "protocol_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_usmpd_pca_loading_backtransform_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_usmpd_pca_loading_backtransform_review_"
                    f"{item.get('pca_loading_review_row_id', '')}"
                ),
                assumption_family="policy_path_usmpd_pca_loading_backtransform_review",
                artifact_or_surface=(
                    "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv"
                ),
                surface_type="policy_path_usmpd_pca_loading_backtransform_review",
                upstream_row_key=item.get("pca_loading_review_row_id", ""),
                scenario_or_path_scope=item.get("event_surface", ""),
                period_or_horizon=item.get("instrument_code", ""),
                value_role="usmpd_pca_loading_backtransform_review_status",
                current_value_exact=item.get("candidate_bps_year_exposure", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_usmpd_pca_loadings_not_bps_year_path"
                ),
                source_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                calibration_status_raw=item.get("loading_back_transform_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("instrument_code", ""),
                source_family="USMPD PCA loading/back-transform review",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "usmpd_pca_loading_backtransform_review_only_not_path_exposure"
                ),
                transport_risk=(
                    "high_until_event_horizon_weights_integral_and_path_target_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "event_specific_horizon_weights_bps_year_integral_independent_"
                    "path_replication_target_and_promotion_rule"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_source_code_workbook_object_inventory.csv;"
                    "ratewall_policy_path_source_code_workbook_protocol_deep_review.csv;"
                    "data/raw/policy_path_protocol_sources/sf_fed_usmpd.xlsx;"
                    "data/raw/policy_path_protocol_sources/"
                    "sf_fed_usmpd_monetary_policy_surprises.zip"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_usmpd_scalar_score_replication_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_usmpd_scalar_score_replication_review_"
                    f"{item.get('scalar_score_review_row_id', '')}"
                ),
                assumption_family="policy_path_usmpd_scalar_score_replication_review",
                artifact_or_surface=(
                    "ratewall_policy_path_usmpd_scalar_score_replication_review.csv"
                ),
                surface_type="policy_path_usmpd_scalar_score_replication_review",
                upstream_row_key=item.get("scalar_score_review_row_id", ""),
                scenario_or_path_scope=item.get("event_surface", ""),
                period_or_horizon=item.get("event_date", ""),
                value_role="usmpd_scalar_score_replication_review_status",
                current_value_exact=item.get("candidate_bps_year_exposure", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_usmpd_scalar_score_not_bps_year_path"
                ),
                source_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                calibration_status_raw=item.get(
                    "scalar_score_construction_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("mps_output_path", ""),
                source_field_or_series=item.get("source_output_column", ""),
                source_family="USMPD scalar-score replication review",
                source_record_count="1",
                source_hash_or_manifest_hash=(
                    item.get("mps_output_sha256", "")
                    or item.get("source_artifact_sha256", "")
                ),
                support_diagnostics_present="true",
                directness_class=(
                    "usmpd_scalar_score_replication_review_only_not_path_exposure"
                ),
                transport_risk=(
                    "high_until_event_horizon_weights_integral_and_path_target_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "event_specific_horizon_weights_bps_year_integral_independent_"
                    "path_replication_target_and_promotion_rule"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv;"
                    "data/raw/policy_path_protocol_sources/"
                    "sf_fed_usmpd_monetary_policy_surprises.zip"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_usmpd_pca_backtransform_gate_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_usmpd_pca_backtransform_gate_review_"
                    f"{item.get('pca_backtransform_gate_review_row_id', '')}"
                ),
                assumption_family="policy_path_usmpd_pca_backtransform_gate_review",
                artifact_or_surface=(
                    "ratewall_policy_path_usmpd_pca_backtransform_gate_review.csv"
                ),
                surface_type="policy_path_usmpd_pca_backtransform_gate_review",
                upstream_row_key=item.get("pca_backtransform_gate_review_row_id", ""),
                scenario_or_path_scope=item.get("event_surface", ""),
                period_or_horizon=item.get("required_gate", ""),
                value_role="usmpd_pca_backtransform_gate_review_status",
                current_value_exact=item.get("candidate_bps_year_exposure", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_usmpd_pca_backtransform_gate_not_bps_year_protocol"
                ),
                source_status_raw=item.get("gate_review_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("required_gate", ""),
                source_family="USMPD PCA back-transform gate review",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "usmpd_pca_backtransform_gate_review_only_not_path_exposure"
                ),
                transport_risk=(
                    "high_until_event_horizon_weights_integral_and_path_target_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "complete_source_backed_bps_year_protocol_and_promotion_rule"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv;"
                    "ratewall_policy_path_usmpd_scalar_score_replication_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_usmpd_instrument_decomposition_design_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_usmpd_instrument_decomposition_design_review_"
                    f"{item.get('instrument_decomposition_design_row_id', '')}"
                ),
                assumption_family=(
                    "policy_path_usmpd_instrument_decomposition_design_review"
                ),
                artifact_or_surface=(
                    "ratewall_policy_path_usmpd_instrument_decomposition_"
                    "design_review.csv"
                ),
                surface_type=(
                    "policy_path_usmpd_instrument_decomposition_design_review"
                ),
                upstream_row_key=item.get(
                    "instrument_decomposition_design_row_id", ""
                ),
                scenario_or_path_scope=item.get("event_surface", ""),
                period_or_horizon=item.get("decomposition_design_step", ""),
                value_role="usmpd_instrument_decomposition_design_status",
                current_value_exact=item.get("candidate_bps_year_exposure", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_usmpd_instrument_decomposition_design_not_bps_year_path"
                ),
                source_status_raw=item.get("source_support_status", ""),
                calibration_status_raw=item.get("design_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("instrument_code", ""),
                source_family="USMPD instrument-decomposition design review",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "usmpd_instrument_decomposition_design_review_only"
                ),
                transport_risk=(
                    "high_until_instrument_decomposition_horizon_weights_integral_"
                    "and_path_target_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "instrument_rate_change_decomposition_event_horizon_weights_"
                    "bps_year_integral_replication_target_and_promotion_rule"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv;"
                    "ratewall_policy_path_usmpd_scalar_score_replication_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_bps_year_candidate_path_design_contract_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_bps_year_candidate_path_design_contract_"
                    f"{item.get('candidate_path_design_row_id', '')}"
                ),
                assumption_family="policy_path_bps_year_candidate_path_design_contract",
                artifact_or_surface=(
                    "ratewall_policy_path_bps_year_candidate_path_design_contract.csv"
                ),
                surface_type="policy_path_bps_year_candidate_path_design_contract",
                upstream_row_key=item.get("candidate_path_design_row_id", ""),
                scenario_or_path_scope=item.get("event_id", ""),
                period_or_horizon=item.get("path_design_step", ""),
                value_role="candidate_path_design_contract_status",
                current_value_exact=item.get("candidate_bps_year_exposure", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_candidate_path_design_contract_not_bps_year_path"
                ),
                source_status_raw=item.get("source_support_status", ""),
                calibration_status_raw=item.get("design_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("official_spec_artifact_path", ""),
                source_field_or_series=item.get("candidate_instrument_code", ""),
                source_family="policy-path bps-year candidate path design contract",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get(
                    "official_spec_artifact_sha256", ""
                ),
                support_diagnostics_present="true",
                directness_class="candidate_path_design_contract_review_only",
                transport_risk=(
                    "high_until_unit_decomposition_horizon_weight_integral_"
                    "replication_and_promotion_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_unit_instrument_decomposition_event_horizon_weights_"
                    "bps_year_integral_independent_replication_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_contract_interval_source_review.csv;"
                    "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv;"
                    "ratewall_policy_path_usmpd_scalar_score_replication_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_formula_replication_source_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_formula_replication_source_review_"
                    f"{item.get('formula_replication_source_review_row_id', '')}"
                ),
                assumption_family="policy_path_formula_replication_source_review",
                artifact_or_surface=(
                    "ratewall_policy_path_formula_replication_source_review.csv"
                ),
                surface_type="policy_path_formula_replication_source_review",
                upstream_row_key=item.get(
                    "formula_replication_source_review_row_id", ""
                ),
                scenario_or_path_scope=item.get("artifact_handle", ""),
                period_or_horizon=item.get("required_bridge_field", ""),
                value_role="formula_replication_source_evidence_status",
                current_value_exact=item.get("candidate_bps_year_exposure", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_formula_replication_source_review_not_bps_year_path"
                ),
                source_status_raw=item.get("field_evidence_status", ""),
                calibration_status_raw=item.get("source_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("required_bridge_field", ""),
                source_family="policy-path formula/replication source review",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get("source_artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class="formula_replication_source_review_only",
                transport_risk=(
                    "high_until_complete_unit_decomposition_horizon_integral_"
                    "replication_and_promotion_protocol_passes"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "unit_sign_instrument_decomposition_event_horizon_weights_"
                    "bps_year_integral_independent_replication_denominator_"
                    "isolation_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_formula_replication_source_review.csv;"
                    "ratewall_policy_path_bps_year_candidate_path_design_contract.csv;"
                    "ratewall_policy_path_source_code_workbook_protocol_deep_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_reviewed_bps_year_protocol_gap_matrix_rows(
    gap_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in gap_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_reviewed_bps_year_protocol_gap_matrix_"
                    f"{item.get('protocol_gap_matrix_row_id', '')}"
                ),
                assumption_family=(
                    "policy_path_reviewed_bps_year_protocol_gap_matrix"
                ),
                artifact_or_surface=(
                    "ratewall_policy_path_reviewed_bps_year_protocol_gap_matrix.csv"
                ),
                surface_type="policy_path_reviewed_bps_year_protocol_gap_matrix",
                upstream_row_key=item.get("protocol_gap_matrix_row_id", ""),
                scenario_or_path_scope=item.get("protocol_scope_id", ""),
                period_or_horizon=item.get("protocol_gate", ""),
                value_role="reviewed_bps_year_protocol_gap_status",
                current_value_exact=item.get("candidate_bps_year_exposure", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_reviewed_bps_year_protocol_gap_not_path_exposure"
                ),
                source_status_raw=item.get("gate_requirement_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_paths", ""),
                source_field_or_series=item.get("linked_status_field_names", ""),
                source_family=(
                    "policy-path reviewed bps-year protocol gap matrix"
                ),
                source_record_count=item.get("evidence_surface_row_count", ""),
                source_hash_or_manifest_hash=item.get("source_artifact_sha256s", ""),
                support_diagnostics_present="true",
                directness_class="reviewed_bps_year_protocol_gap_matrix_only",
                transport_risk=(
                    "high_until_unit_horizon_integral_replication_and_promotion_"
                    "protocol_all_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_cell_unit_sign_instrument_decomposition_event_horizon_"
                    "grid_loading_back_transform_bps_year_integral_independent_"
                    "replication_denominator_isolation_and_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_reviewed_bps_year_protocol_gap_matrix.csv;"
                    "ratewall_policy_path_event_level_candidate_vector.csv;"
                    "ratewall_policy_path_contract_interval_source_review.csv;"
                    "ratewall_policy_path_bps_year_normalization_review.csv;"
                    "ratewall_policy_path_formula_replication_source_review.csv;"
                    "ratewall_policy_path_source_code_workbook_protocol_deep_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_protocol_source_acquisition_work_queue_rows(
    queue_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in queue_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_protocol_source_acquisition_work_queue_"
                    f"{item.get('source_acquisition_work_queue_row_id', '')}"
                ),
                assumption_family=(
                    "policy_path_protocol_source_acquisition_work_queue"
                ),
                artifact_or_surface=(
                    "ratewall_policy_path_protocol_source_acquisition_work_queue.csv"
                ),
                surface_type="policy_path_protocol_source_acquisition_work_queue",
                upstream_row_key=item.get("source_acquisition_work_queue_row_id", ""),
                scenario_or_path_scope=item.get("protocol_scope_id", ""),
                period_or_horizon=item.get("protocol_gate", ""),
                value_role="policy_path_protocol_source_acquisition_priority",
                current_value_exact=item.get("priority_rank", ""),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_source_acquisition_work_queue_not_path_exposure"
                ),
                source_status_raw=item.get("gate_requirement_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=(
                    item.get("candidate_registry_local_paths", "")
                    or item.get("source_artifact_paths", "")
                ),
                source_field_or_series=item.get("missing_evidence_class", ""),
                source_family=(
                    "policy-path protocol source-acquisition work queue"
                ),
                source_record_count="1",
                source_hash_or_manifest_hash=(
                    item.get("candidate_registry_sha256s", "")
                    or item.get("source_artifact_sha256s", "")
                ),
                support_diagnostics_present="true",
                directness_class=(
                    "source_acquisition_work_queue_priority_only"
                ),
                transport_risk=(
                    "high_until_source_acquisition_parse_and_full_bps_year_"
                    "protocol_pass"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "ranked_source_acquisition_parse_unit_sign_instrument_"
                    "decomposition_event_horizon_loading_back_transform_"
                    "bps_year_integral_replication_denominator_isolation_"
                    "promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_source_acquisition_work_queue.csv;"
                    "ratewall_policy_path_reviewed_bps_year_protocol_gap_matrix.csv;"
                    "ratewall_policy_path_protocol_source_acquisition_registry.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_protocol_source_parse_execution_review_rows(
    parse_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in parse_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_protocol_source_parse_execution_review_"
                    f"{item.get('parse_execution_review_row_id', '')}"
                ),
                assumption_family=(
                    "policy_path_protocol_source_parse_execution_review"
                ),
                artifact_or_surface=(
                    "ratewall_policy_path_protocol_source_parse_execution_review.csv"
                ),
                surface_type="policy_path_protocol_source_parse_execution_review",
                upstream_row_key=item.get("parse_execution_review_row_id", ""),
                scenario_or_path_scope=item.get("protocol_scope_id", ""),
                period_or_horizon=item.get("protocol_gate", ""),
                value_role="policy_path_protocol_parse_text_clue_review",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_parse_execution_review_not_path_exposure"
                ),
                source_status_raw=item.get("parse_execution_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("parser_class", ""),
                source_family=(
                    "policy-path protocol source parse-execution review"
                ),
                source_record_count="1",
                source_hash_or_manifest_hash=item.get(
                    "source_artifact_sha256", ""
                ),
                support_diagnostics_present="true",
                directness_class="source_parse_execution_review_only",
                transport_risk=(
                    "high_until_parse_text_clues_become_promotion_grade_"
                    "bps_year_protocol_evidence"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "promotion_grade_source_text_code_formula_replication_"
                    "target_unit_horizon_loading_integral_denominator_"
                    "isolation_promotion"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_source_parse_execution_review.csv;"
                    "ratewall_policy_path_protocol_source_acquisition_work_queue.csv;"
                    "ratewall_policy_path_protocol_source_acquisition_registry.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_source_parse_synthesis_queue_rows(
    queue_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in queue_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_source_parse_synthesis_queue_"
                    f"{item.get('source_parse_synthesis_queue_row_id', '')}"
                ),
                assumption_family="policy_path_source_parse_synthesis_queue",
                artifact_or_surface=(
                    "ratewall_policy_path_source_parse_synthesis_queue.csv"
                ),
                surface_type="policy_path_source_parse_synthesis_queue",
                upstream_row_key=item.get("source_parse_synthesis_queue_row_id", ""),
                scenario_or_path_scope=item.get("synthesis_gate", ""),
                period_or_horizon=item.get("upstream_protocol_scope_id", ""),
                value_role="policy_path_source_parse_synthesis_action_review",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_source_parse_synthesis_queue_not_path_exposure"
                ),
                source_status_raw=item.get("gate_synthesis_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_path", ""),
                source_field_or_series=item.get("upstream_parse_status", ""),
                source_family=(
                    "policy-path source parse synthesis queue"
                ),
                source_record_count="1",
                source_hash_or_manifest_hash=item.get(
                    "source_artifact_sha256", ""
                ),
                support_diagnostics_present="true",
                directness_class="source_parse_synthesis_queue_only",
                transport_risk=(
                    "high_until_queue_action_produces_promotion_grade_bps_"
                    "year_protocol_evidence"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "promotion_grade_unit_sign_horizon_loading_integral_"
                    "replication_denominator_isolation_promotion_protocol"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_source_parse_synthesis_queue.csv;"
                    "ratewall_policy_path_protocol_source_parse_execution_review.csv;"
                    "ratewall_policy_path_protocol_source_acquisition_work_queue.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_source_parse_action_execution_rows(
    action_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in action_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_source_parse_action_execution_"
                    f"{item.get('source_parse_action_execution_row_id', '')}"
                ),
                assumption_family="policy_path_source_parse_action_execution",
                artifact_or_surface=(
                    "ratewall_policy_path_source_parse_action_execution.csv"
                ),
                surface_type="policy_path_source_parse_action_execution",
                upstream_row_key=item.get(
                    "source_parse_action_execution_row_id", ""
                ),
                scenario_or_path_scope=item.get("synthesis_gate", ""),
                period_or_horizon=item.get("action_closure_class", ""),
                value_role="policy_path_source_parse_action_execution_review",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_source_parse_action_execution_not_path_exposure"
                ),
                source_status_raw=item.get("gate_action_execution_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_paths", ""),
                source_field_or_series=item.get("upstream_parse_statuses", ""),
                source_family="policy-path source parse action execution",
                source_record_count=item.get("synthesis_queue_row_count", "1"),
                source_hash_or_manifest_hash=item.get(
                    "source_artifact_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="source_parse_action_execution_only",
                transport_risk=(
                    "high_until_action_execution_produces_promotion_grade_"
                    "bps_year_protocol_evidence"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "deeper_parse_or_new_acquisition_or_protocol_authoring_"
                    "before_any_bps_year_path_admission"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_source_parse_action_execution.csv;"
                    "ratewall_policy_path_source_parse_synthesis_queue.csv;"
                    "ratewall_policy_path_protocol_source_parse_execution_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_deeper_parse_execution_review_rows(
    deeper_parse_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in deeper_parse_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_deeper_parse_execution_review_"
                    f"{item.get('deeper_parse_execution_review_row_id', '')}"
                ),
                assumption_family="policy_path_deeper_parse_execution_review",
                artifact_or_surface=(
                    "ratewall_policy_path_deeper_parse_execution_review.csv"
                ),
                surface_type="policy_path_deeper_parse_execution_review",
                upstream_row_key=item.get(
                    "deeper_parse_execution_review_row_id", ""
                ),
                scenario_or_path_scope=item.get("synthesis_gate", ""),
                period_or_horizon=item.get("action_execution_rank", ""),
                value_role="policy_path_deeper_parse_snippet_review",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_deeper_parse_execution_review_not_path_exposure"
                ),
                source_status_raw=item.get("deeper_parse_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_paths", ""),
                source_field_or_series=item.get("deeper_parse_matched_terms", ""),
                source_family="policy-path deeper parse execution review",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get(
                    "source_artifact_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="deeper_parse_execution_review_only",
                transport_risk=(
                    "high_until_precise_snippets_are_converted_to_explicit_"
                    "promotion_grade_bps_year_protocol_evidence"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "explicit_protocol_candidate_or_new_source_acquisition_"
                    "before_any_bps_year_path_admission"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_deeper_parse_execution_review.csv;"
                    "ratewall_policy_path_source_parse_action_execution.csv;"
                    "ratewall_policy_path_source_parse_synthesis_queue.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_protocol_candidate_draft_review_rows(
    draft_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in draft_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_protocol_candidate_draft_review_"
                    f"{item.get('protocol_candidate_draft_review_row_id', '')}"
                ),
                assumption_family="policy_path_protocol_candidate_draft_review",
                artifact_or_surface=(
                    "ratewall_policy_path_protocol_candidate_draft_review.csv"
                ),
                surface_type="policy_path_protocol_candidate_draft_review",
                upstream_row_key=item.get(
                    "protocol_candidate_draft_review_row_id", ""
                ),
                scenario_or_path_scope=item.get("protocol_component", ""),
                period_or_horizon=item.get("synthesis_gate", ""),
                value_role="policy_path_protocol_component_draft_review",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_protocol_candidate_draft_review_not_path_exposure"
                ),
                source_status_raw=item.get("component_draft_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_paths", ""),
                source_field_or_series=item.get("protocol_component", ""),
                source_family="policy-path protocol candidate draft review",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get(
                    "source_artifact_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="protocol_candidate_draft_review_only",
                transport_risk=(
                    "high_until_component_draft_is_replaced_by_promotion_"
                    "grade_source_backed_protocol_evidence"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_backed_unit_sign_horizon_loading_formula_"
                    "replication_isolation_promotion_protocol"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_candidate_draft_review.csv;"
                    "ratewall_policy_path_deeper_parse_execution_review.csv;"
                    "ratewall_policy_path_source_parse_action_execution.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_protocol_missing_evidence_acquisition_queue_rows(
    queue_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in queue_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_protocol_missing_evidence_acquisition_queue_"
                    f"{item.get('missing_evidence_acquisition_queue_row_id', '')}"
                ),
                assumption_family=(
                    "policy_path_protocol_missing_evidence_acquisition_queue"
                ),
                artifact_or_surface=(
                    "ratewall_policy_path_protocol_missing_evidence_"
                    "acquisition_queue.csv"
                ),
                surface_type=(
                    "policy_path_protocol_missing_evidence_acquisition_queue"
                ),
                upstream_row_key=item.get(
                    "missing_evidence_acquisition_queue_row_id", ""
                ),
                scenario_or_path_scope=item.get("missing_evidence_target", ""),
                period_or_horizon=item.get("missing_evidence_target_gate", ""),
                value_role="policy_path_missing_evidence_acquisition_queue",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_missing_evidence_acquisition_queue_not_path_exposure"
                ),
                source_status_raw=item.get(
                    "automated_public_acquisition_status", ""
                ),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_paths", ""),
                source_field_or_series=item.get("missing_evidence_target", ""),
                source_family="policy-path missing-evidence acquisition queue",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get(
                    "source_artifact_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="missing_evidence_acquisition_queue_only",
                transport_risk=(
                    "high_until_queue_targets_are_replaced_by_promotion_grade_"
                    "source_backed_protocol_evidence"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_backed_unit_sign_horizon_loading_formula_"
                    "replication_isolation_promotion_protocol"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_missing_evidence_"
                    "acquisition_queue.csv;"
                    "ratewall_policy_path_protocol_candidate_draft_review.csv;"
                    "ratewall_policy_path_source_parse_action_execution.csv;"
                    "ratewall_policy_path_protocol_source_acquisition_work_"
                    "queue.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_protocol_missing_evidence_parse_execution_review_rows(
    parse_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in parse_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_protocol_missing_evidence_parse_execution_"
                    f"{item.get('missing_evidence_parse_execution_review_row_id', '')}"
                ),
                assumption_family=(
                    "policy_path_protocol_missing_evidence_parse_execution_review"
                ),
                artifact_or_surface=(
                    "ratewall_policy_path_protocol_missing_evidence_"
                    "parse_execution_review.csv"
                ),
                surface_type=(
                    "policy_path_protocol_missing_evidence_parse_execution_review"
                ),
                upstream_row_key=item.get(
                    "missing_evidence_parse_execution_review_row_id", ""
                ),
                scenario_or_path_scope=item.get("missing_evidence_target", ""),
                period_or_horizon=item.get("missing_evidence_target_gate", ""),
                value_role="policy_path_missing_evidence_parse_execution_review",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_missing_evidence_parse_execution_not_path_exposure"
                ),
                source_status_raw=item.get("target_parse_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_paths", ""),
                source_field_or_series=item.get("missing_evidence_target", ""),
                source_family="policy-path missing-evidence parse execution",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get(
                    "computed_source_artifact_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="missing_evidence_parse_execution_review_only",
                transport_risk=(
                    "high_until_parse_hits_are_replaced_by_promotion_grade_"
                    "source_backed_protocol_evidence"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_backed_unit_sign_horizon_loading_formula_"
                    "replication_isolation_promotion_protocol"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_missing_evidence_"
                    "parse_execution_review.csv;"
                    "ratewall_policy_path_protocol_missing_evidence_"
                    "acquisition_queue.csv;"
                    "ratewall_policy_path_protocol_candidate_draft_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_protocol_authoring_readiness_matrix_rows(
    readiness_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in readiness_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_protocol_authoring_readiness_"
                    f"{item.get('protocol_authoring_readiness_matrix_row_id', '')}"
                ),
                assumption_family="policy_path_protocol_authoring_readiness_matrix",
                artifact_or_surface=(
                    "ratewall_policy_path_protocol_authoring_readiness_matrix.csv"
                ),
                surface_type="policy_path_protocol_authoring_readiness_matrix",
                upstream_row_key=item.get(
                    "protocol_authoring_readiness_matrix_row_id", ""
                ),
                scenario_or_path_scope=item.get("protocol_component", ""),
                period_or_horizon=item.get("protocol_component_gate", ""),
                value_role="policy_path_protocol_authoring_readiness",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_authoring_readiness_matrix_not_path_exposure"
                ),
                source_status_raw=item.get("readiness_evidence_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_artifact_paths", ""),
                source_field_or_series=item.get("protocol_component", ""),
                source_family="policy-path protocol authoring readiness",
                source_record_count=item.get("input_row_count", "1"),
                source_hash_or_manifest_hash=item.get(
                    "computed_source_artifact_sha256s", ""
                ),
                support_diagnostics_present="true",
                directness_class="protocol_authoring_readiness_matrix_only",
                transport_risk=(
                    "high_until_required_protocol_fields_are_authored_and_"
                    "source_backed"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_backed_unit_sign_horizon_loading_formula_"
                    "replication_isolation_promotion_protocol"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_authoring_readiness_matrix.csv;"
                    "ratewall_policy_path_protocol_missing_evidence_"
                    "parse_execution_review.csv;"
                    "ratewall_policy_path_protocol_missing_evidence_"
                    "acquisition_queue.csv;"
                    "ratewall_policy_path_protocol_candidate_draft_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_protocol_field_authoring_contract_rows(
    contract_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in contract_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_protocol_field_authoring_"
                    f"{item.get('protocol_field_authoring_contract_row_id', '')}"
                ),
                assumption_family="policy_path_protocol_field_authoring_contract",
                artifact_or_surface=(
                    "ratewall_policy_path_protocol_field_authoring_contract.csv"
                ),
                surface_type="policy_path_protocol_field_authoring_contract",
                upstream_row_key=item.get(
                    "protocol_field_authoring_contract_row_id", ""
                ),
                scenario_or_path_scope=item.get("protocol_component", ""),
                period_or_horizon=item.get("authored_field_name", ""),
                value_role="policy_path_protocol_field_authoring_contract",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_field_authoring_contract_not_path_exposure"
                ),
                source_status_raw=item.get("field_source_evidence_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get("authored_field_name", ""),
                source_family="policy-path protocol field authoring contract",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get(
                    "source_specific_citation_or_design_handles", ""
                ),
                support_diagnostics_present="true",
                directness_class="protocol_field_authoring_contract_only",
                transport_risk=(
                    "high_until_field_level_pass_rules_are_authored_and_"
                    "source_backed"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "source_backed_unit_sign_horizon_loading_formula_"
                    "replication_isolation_promotion_protocol"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_protocol_field_authoring_contract.csv;"
                    "ratewall_policy_path_protocol_authoring_readiness_matrix.csv;"
                    "ratewall_policy_path_protocol_missing_evidence_"
                    "parse_execution_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _policy_path_field_evidence_resolution_queue_rows(
    queue_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in queue_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_field_evidence_resolution_"
                    f"{item.get('field_evidence_resolution_queue_row_id', '')}"
                ),
                assumption_family="policy_path_field_evidence_resolution_queue",
                artifact_or_surface=(
                    "ratewall_policy_path_field_evidence_resolution_queue.csv"
                ),
                surface_type="policy_path_field_evidence_resolution_queue",
                upstream_row_key=item.get(
                    "field_evidence_resolution_queue_row_id", ""
                ),
                scenario_or_path_scope=item.get("protocol_component", ""),
                period_or_horizon=item.get("authored_field_name", ""),
                value_role="policy_path_field_evidence_resolution_queue",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_field_evidence_resolution_queue_not_path_exposure"
                ),
                source_status_raw=item.get("field_resolution_status", ""),
                calibration_status_raw=item.get("protocol_admission_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_specific_artifacts", ""),
                source_field_or_series=item.get("authored_field_name", ""),
                source_family="policy-path field evidence resolution queue",
                source_record_count="1",
                source_hash_or_manifest_hash=item.get(
                    "source_specific_citation_or_design_handles", ""
                ),
                support_diagnostics_present="true",
                directness_class="field_evidence_resolution_queue_only",
                transport_risk=(
                    "high_until_resolution_queue_items_are_replaced_by_"
                    "authored_source_backed_protocol_fields"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "field_specific_source_extraction_invariant_authoring_or_"
                    "independent_replication_design"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_field_evidence_resolution_queue.csv;"
                    "ratewall_policy_path_protocol_field_authoring_contract.csv;"
                    "ratewall_policy_path_protocol_authoring_readiness_matrix.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _architecture_lock_surface_rows(
    source_rows: list[dict[str, str]],
    *,
    assumption_family: str,
    artifact_or_surface: str,
    id_field: str,
    source_field: str,
    source_family: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in source_rows:
        row_id = item.get(id_field, "")
        rows.append(
            _row(
                assumption_handle=f"{assumption_family}_{row_id}",
                assumption_family=assumption_family,
                artifact_or_surface=artifact_or_surface,
                surface_type="backend_architecture_lock_registry",
                upstream_row_key=row_id,
                scenario_or_path_scope=item.get(source_field, ""),
                period_or_horizon=item.get("denominator_basis", ""),
                value_role="backend_architecture_lock_review",
                current_value_exact="",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "blocked_architecture_lock_not_empirical_promotion"
                ),
                source_status_raw=(
                    item.get("canonical_status", "")
                    or item.get("admission_status", "")
                    or item.get("field_resolution_status", "")
                    or item.get("field_protocol_completion_status", "")
                    or item.get("design_tranche_status", "")
                    or item.get("design_completion_status", "")
                    or item.get("field_pass_rule_status", "")
                    or item.get("pass_rule_result_status", "")
                    or item.get("invariant_admission_status", "")
                    or item.get("component_closure_status", "")
                    or item.get("full_gate_conjunction_status", "")
                    or item.get("source_protocol_action_status", "")
                    or item.get("harness_status", "")
                    or item.get("attempt_execution_status", "")
                    or item.get("mode_class", "")
                ),
                calibration_status_raw=item.get(
                    "admissibility_status",
                    item.get(
                        "value_admission_status",
                        item.get("protocol_admission_status", ""),
                    ),
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get(
                    "source_artifacts",
                    item.get("source_artifact", item.get("source_output_path", "")),
                ),
                source_field_or_series=item.get(source_field, ""),
                source_family=source_family,
                source_record_count="1",
                support_diagnostics_present="true",
                directness_class="backend_architecture_lock_review_only",
                transport_risk=(
                    "high_until_architecture_registry_rows_are_replaced_by_"
                    "source_gated_empirical_evidence"
                ),
                manual_override_required="true",
                calibration_needed=(
                    "canonical_100bp_denominator_policy_path_current_demand_"
                    "mapping_and_promotion_gate"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=artifact_or_surface,
                **_copy_switches(item),
            )
        )
    return rows


def _value_bearing_bps_year_exposure_export_rows(
    export_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in export_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_value_bearing_bps_year_exposure_export_"
                    f"{item.get('value_bearing_bps_year_exposure_export_row_id', '')}"
                ),
                assumption_family="policy_path_value_bearing_bps_year_exposure_export",
                artifact_or_surface=(
                    "ratewall_policy_path_value_bearing_bps_year_exposure_export.csv"
                ),
                surface_type="policy_path_value_bearing_bps_year_exposure_export",
                upstream_row_key=item.get(
                    "value_bearing_bps_year_exposure_export_row_id", ""
                ),
                scenario_or_path_scope=item.get("event_id", ""),
                period_or_horizon=item.get("horizon_q", ""),
                value_role="event_horizon_100bp_year_exposure_nonpromotional",
                current_value_exact=item.get("event_horizon_100bp_year_exposure", ""),
                unit=item.get("exposure_unit", "normalized_100bp_year_exposure"),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "value_bearing_policy_path_exposure_not_denominator"
                ),
                source_status_raw=item.get("exposure_export_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_data_xlsx_path", ""),
                source_field_or_series=item.get("source_workbook_cells", ""),
                source_family=(
                    "policy-path project-authored value-bearing bps-year exposure export"
                ),
                source_hash_or_manifest_hash=item.get("source_data_xlsx_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "event_level_policy_path_exposure_not_denominator_value"
                ),
                transport_risk=(
                    "high_until_fspdp_response_gdp_share_uncertainty_replication_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed=(
                    "fspdp_lp_on_value_bearing_exposure_and_denominator_gate_stack"
                ),
                promotion_status="blocked_not_denominator",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_project_authored_bps_year_event_exposure.csv;"
                    "ratewall_policy_path_project_authored_bps_year_exposure_admission_consumer.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _value_bearing_bps_year_exposure_quarterly_series_rows(
    series_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in series_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "policy_path_value_bearing_bps_year_exposure_quarterly_series_"
                    f"{item.get('value_bearing_bps_year_exposure_quarterly_row_id', '')}"
                ),
                assumption_family=(
                    "policy_path_value_bearing_bps_year_exposure_quarterly_series"
                ),
                artifact_or_surface=(
                    "ratewall_policy_path_value_bearing_bps_year_exposure_quarterly_series.csv"
                ),
                surface_type="policy_path_value_bearing_bps_year_exposure_quarterly_series",
                upstream_row_key=item.get(
                    "value_bearing_bps_year_exposure_quarterly_row_id", ""
                ),
                scenario_or_path_scope=item.get("exposure_series_id", ""),
                period_or_horizon=item.get("quarter", ""),
                value_role="quarterly_value_bearing_100bp_year_exposure_nonpromotional",
                current_value_exact=item.get(
                    "quarterly_value_bearing_100bp_year_exposure", ""
                ),
                unit=item.get(
                    "exposure_unit", "normalized_100bp_year_exposure_quarterly_sum"
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "value_bearing_policy_path_quarterly_exposure_not_denominator"
                ),
                source_status_raw=item.get("exposure_quarterly_status", ""),
                calibration_status_raw=item.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_data_xlsx_path", ""),
                source_field_or_series=item.get("source_workbook_cells_sample", ""),
                source_family=(
                    "policy-path project-authored value-bearing quarterly bps-year exposure series"
                ),
                source_hash_or_manifest_hash=item.get("source_data_xlsx_sha256", ""),
                support_diagnostics_present="true",
                directness_class=(
                    "quarterly_policy_path_exposure_not_denominator_value"
                ),
                transport_risk=(
                    "high_until_fspdp_response_gdp_share_uncertainty_replication_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed=(
                    "fspdp_lp_on_value_bearing_exposure_and_denominator_gate_stack"
                ),
                promotion_status="blocked_not_denominator",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_policy_path_value_bearing_bps_year_exposure_export.csv;"
                    "ratewall_policy_path_project_authored_bps_year_event_exposure.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_fspdp_component_source_manifest_rows(
    manifest_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in manifest_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_fspdp_component_source_manifest_"
                    f"{item.get('source_series_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_fspdp_component_source_manifest"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_fspdp_component_source_"
                    "manifest.csv"
                ),
                surface_type="fspdp_component_source_manifest",
                upstream_row_key=item.get("manifest_row_id", ""),
                scenario_or_path_scope=item.get("component_id", ""),
                value_role=item.get("component_role", ""),
                unit=item.get("unit", ""),
                source_backing_class="official_source_value",
                source_backing_subclass=(
                    "bea_nipa_mirror_component_weight_input_not_drag_estimate"
                ),
                source_status_raw=item.get("admission_status", ""),
                calibration_status_raw="not_calibration",
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("raw_source_path", ""),
                source_field_or_series=item.get("source_series_id", ""),
                source_family=item.get("source_family", ""),
                source_record_count=item.get("source_record_count", ""),
                source_hash_or_manifest_hash=item.get("raw_source_sha256", ""),
                support_diagnostics_present="true",
                directness_class="official_fspdp_component_weight_input",
                transport_risk="low_for_component_weight_high_for_drag_estimation",
                manual_override_required="false",
                calibration_needed=(
                    "irf_unit_bridge_proxy_bridge_policy_path_normalization"
                ),
                promotion_status="blocked_for_drag_promotion",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_fspdp_component_source_"
                    "manifest.csv;"
                    "ratewall_conventional_drag_fspdp_component_share_panel.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_fspdp_component_share_panel_rows(
    panel_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in panel_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_fspdp_component_share_panel_"
                    f"{item.get('quarter', '')}_{item.get('component_id', '')}"
                ),
                assumption_family="conventional_drag_fspdp_component_share_panel",
                artifact_or_surface=(
                    "ratewall_conventional_drag_fspdp_component_share_panel.csv"
                ),
                surface_type="fspdp_component_share_panel",
                upstream_row_key=item.get("panel_row_id", ""),
                scenario_or_path_scope=item.get("component_id", ""),
                period_or_horizon=item.get("quarter", ""),
                value_role="nominal_share_of_gdp",
                current_value_exact=item.get("nominal_share_of_gdp", ""),
                unit="share_of_nominal_gdp",
                source_backing_class="official_source_value",
                source_backing_subclass=(
                    "bea_nipa_mirror_component_share_not_drag_estimate"
                ),
                source_status_raw=item.get("admission_status", ""),
                calibration_status_raw="not_calibration",
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_snapshot_path", ""),
                source_field_or_series=item.get("source_series_id", ""),
                source_family="DB.nomics mirror of BEA NIPA",
                source_record_count=item.get(
                    "source_observation_count_in_quarter", ""
                ),
                source_hash_or_manifest_hash=item.get("source_hash", ""),
                support_diagnostics_present="true",
                directness_class="official_fspdp_component_share_input",
                transport_risk="low_for_component_weight_high_for_drag_estimation",
                manual_override_required="false",
                calibration_needed=(
                    "irf_unit_bridge_proxy_bridge_policy_path_normalization"
                ),
                promotion_status="blocked_for_drag_promotion",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_fspdp_component_share_panel.csv;"
                    "ratewall_conventional_drag_fspdp_component_source_"
                    "manifest.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _current_demand_gdp_share_source_manifest_rows(
    manifest_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in manifest_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "current_demand_gdp_share_source_manifest_"
                    f"{item.get('source_series_id', '')}"
                ),
                assumption_family="current_demand_gdp_share_source_manifest",
                artifact_or_surface=(
                    "ratewall_current_demand_gdp_share_source_manifest.csv"
                ),
                surface_type="current_demand_conversion_source_manifest",
                upstream_row_key=item.get("manifest_row_id", ""),
                scenario_or_path_scope=item.get("component_id", ""),
                value_role=item.get("nominal_or_real", ""),
                unit=item.get("unit", ""),
                source_backing_class="official_source_value",
                source_backing_subclass=(
                    "official_macro_series_conversion_input_not_drag_estimate"
                ),
                source_status_raw=item.get("admission_status", ""),
                calibration_status_raw="not_calibration",
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("download_or_cache_path", ""),
                source_field_or_series=item.get("source_series_id", ""),
                source_family=item.get("source_family", ""),
                source_record_count=item.get("source_record_count", ""),
                source_hash_or_manifest_hash=item.get("source_hash", ""),
                support_diagnostics_present="true",
                directness_class="official_current_demand_conversion_input",
                transport_risk="low_for_share_conversion_high_for_drag_estimation",
                manual_override_required="false",
                calibration_needed="policy_path_normalized_irf_or_research_parameter",
                promotion_status="blocked_for_drag_promotion",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_current_demand_gdp_share_source_manifest.csv;"
                    "ratewall_current_demand_gdp_share_panel.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _current_demand_gdp_share_panel_rows(
    panel_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in panel_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "current_demand_gdp_share_panel_"
                    f"{item.get('quarter', '')}_{item.get('component_id', '')}"
                ),
                assumption_family="current_demand_gdp_share_panel",
                artifact_or_surface="ratewall_current_demand_gdp_share_panel.csv",
                surface_type="current_demand_gdp_share_conversion_panel",
                upstream_row_key=item.get("panel_row_id", ""),
                scenario_or_path_scope=item.get("component_id", ""),
                period_or_horizon=item.get("quarter", ""),
                value_role="nominal_share_of_gdp",
                current_value_exact=item.get("nominal_share_of_gdp", ""),
                unit="share_of_nominal_gdp",
                source_backing_class="official_source_value",
                source_backing_subclass=(
                    "official_macro_component_share_not_drag_estimate"
                ),
                source_status_raw=item.get("admission_status", ""),
                calibration_status_raw="not_calibration",
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_snapshot_path", ""),
                source_field_or_series=item.get("source_series_id", ""),
                source_family="FRED/BEA NIPA",
                source_hash_or_manifest_hash=item.get("source_hash", ""),
                support_diagnostics_present="true",
                directness_class="official_current_demand_share_conversion_panel",
                transport_risk="low_for_share_conversion_high_for_drag_estimation",
                manual_override_required="false",
                calibration_needed="policy_path_normalized_irf_or_research_parameter",
                promotion_status="blocked_for_drag_promotion",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_current_demand_gdp_share_panel.csv;"
                    "ratewall_current_demand_gdp_share_source_manifest.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_current_demand_mapping_bridge_rows(
    bridge_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in bridge_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_current_demand_mapping_bridge_"
                    f"{item.get('mapping_bridge_row_id', '')}"
                ),
                assumption_family="conventional_drag_current_demand_mapping_bridge",
                artifact_or_surface=(
                    "ratewall_conventional_drag_current_demand_mapping_bridge.csv"
                ),
                surface_type="current_demand_mapping_bridge",
                upstream_row_key=item.get("mapping_bridge_row_id", ""),
                scenario_or_path_scope=item.get("target_outcome_id", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("component_role", ""),
                current_value_exact=item.get("mean_nominal_share_of_gdp", ""),
                unit="share_of_nominal_gdp",
                source_backing_class="official_source_value",
                source_backing_subclass=(
                    "official_current_demand_share_bridge_not_drag_estimate"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("conversion_formula_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_snapshot_path", ""),
                source_field_or_series=item.get("component_id", ""),
                source_family="FRED/BEA NIPA",
                source_record_count=item.get("panel_row_count", ""),
                source_hash_or_manifest_hash=item.get("source_hash", ""),
                support_diagnostics_present="true",
                directness_class="official_fspdp_current_demand_mapping_bridge",
                transport_risk="low_for_share_mapping_high_for_drag_estimation",
                manual_override_required="false",
                calibration_needed=(
                    "research_irf_policy_path_normalization_uncertainty_replication"
                ),
                promotion_status="blocked_for_drag_promotion",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_current_demand_mapping_bridge.csv;"
                    "ratewall_current_demand_gdp_share_panel.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_contract.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_research_extraction_conversion_bridge_rows(
    bridge_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in bridge_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_research_extraction_conversion_bridge_"
                    f"{item.get('research_bridge_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_research_extraction_conversion_bridge"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_research_extraction_"
                    "conversion_bridge.csv"
                ),
                surface_type="research_extraction_conversion_bridge",
                upstream_row_key=item.get("research_bridge_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role="research_to_fspdp_conversion_gate_bridge",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "research_extraction_conversion_bridge_not_parameter_value"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("conversion_bridge_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=(
                    "ratewall_conventional_drag_current_demand_mapping_bridge.csv"
                ),
                source_field_or_series=item.get("target_outcome_id", ""),
                source_family="openicpsr_manual_replication_payload",
                source_record_count=item.get("mapping_bridge_row_count", ""),
                support_diagnostics_present="true",
                directness_class="research_extraction_conversion_bridge_review_only",
                transport_risk="high_until_all_research_gates_pass",
                manual_override_required="false",
                calibration_needed="all_research_parameterization_gates",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_research_extraction_"
                    "conversion_bridge.csv;"
                    "ratewall_conventional_drag_current_demand_mapping_bridge.csv;"
                    "ratewall_conventional_drag_research_extraction_gate_audit.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_local_lp_rows(
    *,
    macro_panel_rows: list[dict[str, str]],
    shock_quarterly_rows: list[dict[str, str]],
    lp_design_rows: list[dict[str, str]],
    lp_diagnostic_rows: list[dict[str, str]],
    lp_estimate_diagnostic_rows: list[dict[str, str]],
    lp_robustness_diagnostic_rows: list[dict[str, str]],
    lp_sample_window_audit_rows: list[dict[str, str]],
    lp_admission_audit_rows: list[dict[str, str]],
    fspdp_denominator_readiness_gate_rows: list[dict[str, str]],
    fspdp_denominator_candidate_join_preflight_rows: list[dict[str, str]],
    fspdp_value_bearing_exposure_lp_execution_rows: list[dict[str, str]],
    fspdp_denominator_conversion_uncertainty_boundary_rows: list[dict[str, str]],
    fspdp_gdp_share_conversion_design_gate_rows: list[dict[str, str]],
    fspdp_gdp_share_conversion_method_admission_rows: list[dict[str, str]],
    fspdp_lp_sample_base_share_join_rows: list[dict[str, str]],
    fspdp_gdp_share_conversion_sensitivity_rows: list[dict[str, str]],
    fspdp_lp_sample_share_closeout_decision_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    specs = [
        (
            macro_panel_rows,
            "conventional_drag_local_macro_panel",
            "ratewall_conventional_drag_local_macro_panel.csv",
            "local_lp_macro_panel",
            "macro_panel_row_id",
            "quarter",
            "local_lp_macro_panel_input_review_only",
        ),
        (
            shock_quarterly_rows,
            "conventional_drag_local_shock_quarterly",
            "ratewall_conventional_drag_local_shock_quarterly.csv",
            "local_lp_shock_quarterly",
            "shock_quarterly_row_id",
            "summed_shock",
            "local_lp_source_defined_shock_review_only",
        ),
        (
            lp_design_rows,
            "conventional_drag_local_lp_design",
            "ratewall_conventional_drag_local_lp_design.csv",
            "local_lp_design",
            "design_id",
            "promotion_status",
            "local_lp_design_review_only",
        ),
        (
            lp_diagnostic_rows,
            "conventional_drag_local_lp_diagnostic",
            "ratewall_conventional_drag_local_lp_diagnostic.csv",
            "local_lp_diagnostic",
            "lp_row_id",
            "source_admission_status",
            "local_lp_diagnostic_review_only",
        ),
        (
            lp_estimate_diagnostic_rows,
            "conventional_drag_local_lp_estimate_diagnostic",
            "ratewall_conventional_drag_local_lp_estimate_diagnostic.csv",
            "local_lp_estimate_diagnostic",
            "estimate_row_id",
            "beta_source_unit",
            "local_lp_source_unit_estimate_review_only",
        ),
        (
            lp_robustness_diagnostic_rows,
            "conventional_drag_local_lp_robustness_diagnostic",
            "ratewall_conventional_drag_local_lp_robustness_diagnostic.csv",
            "local_lp_robustness_diagnostic",
            "robustness_row_id",
            "beta_source_unit",
            "local_lp_robustness_review_only",
        ),
        (
            lp_sample_window_audit_rows,
            "conventional_drag_local_lp_sample_window_audit",
            "ratewall_conventional_drag_local_lp_sample_window_audit.csv",
            "local_lp_sample_window_audit",
            "sample_audit_row_id",
            "sample_window_status",
            "local_lp_sample_window_review_only",
        ),
        (
            lp_admission_audit_rows,
            "conventional_drag_local_lp_admission_audit",
            "ratewall_conventional_drag_local_lp_admission_audit.csv",
            "local_lp_admission_audit",
            "audit_row_id",
            "gate_status",
            "local_lp_admission_audit_review_only",
        ),
        (
            fspdp_denominator_readiness_gate_rows,
            "conventional_drag_fspdp_denominator_readiness_gate",
            "ratewall_conventional_drag_fspdp_denominator_readiness_gate.csv",
            "fspdp_denominator_readiness_gate",
            "fspdp_denominator_readiness_gate_row_id",
            "denominator_readiness_status",
            "fspdp_denominator_readiness_gate_review_only",
        ),
        (
            fspdp_denominator_candidate_join_preflight_rows,
            "conventional_drag_fspdp_denominator_candidate_join_preflight",
            "ratewall_conventional_drag_fspdp_denominator_candidate_join_preflight.csv",
            "fspdp_denominator_candidate_join_preflight",
            "fspdp_denominator_candidate_join_preflight_row_id",
            "denominator_candidate_join_preflight_status",
            "fspdp_denominator_candidate_join_preflight_review_only",
        ),
        (
            fspdp_value_bearing_exposure_lp_execution_rows,
            "conventional_drag_fspdp_value_bearing_exposure_lp_execution",
            "ratewall_conventional_drag_fspdp_value_bearing_exposure_lp_execution.csv",
            "fspdp_value_bearing_exposure_lp_execution",
            "value_bearing_exposure_lp_execution_row_id",
            "response_estimate_status",
            "value_bearing_exposure_path_lp_response_diagnostic_only",
        ),
        (
            fspdp_denominator_conversion_uncertainty_boundary_rows,
            "conventional_drag_fspdp_denominator_conversion_uncertainty_boundary",
            "ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv",
            "fspdp_denominator_conversion_uncertainty_boundary",
            "fspdp_denominator_conversion_uncertainty_boundary_row_id",
            "denominator_conversion_uncertainty_boundary_status",
            "fspdp_denominator_conversion_uncertainty_boundary_review_only",
        ),
        (
            fspdp_gdp_share_conversion_design_gate_rows,
            "conventional_drag_fspdp_gdp_share_conversion_design_gate",
            "ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv",
            "fspdp_gdp_share_conversion_design_gate",
            "fspdp_gdp_share_conversion_design_gate_row_id",
            "gdp_share_conversion_design_gate_status",
            "fspdp_gdp_share_conversion_design_gate_review_only",
        ),
        (
            fspdp_gdp_share_conversion_method_admission_rows,
            "conventional_drag_fspdp_gdp_share_conversion_method_admission",
            "ratewall_conventional_drag_fspdp_gdp_share_conversion_method_admission.csv",
            "fspdp_gdp_share_conversion_method_admission",
            "conversion_method_admission_row_id",
            "admission_status",
            "noncanonical_fspdp_gdp_share_conversion_sensitivity_method",
        ),
        (
            fspdp_lp_sample_base_share_join_rows,
            "conventional_drag_fspdp_lp_sample_base_share_join",
            "ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv",
            "fspdp_lp_sample_base_share_join",
            "fspdp_lp_sample_base_share_join_row_id",
            "baseline_comparison_status",
            "lp_sample_base_quarter_fspdp_share_primary_sensitivity_input",
        ),
        (
            fspdp_gdp_share_conversion_sensitivity_rows,
            "conventional_drag_fspdp_gdp_share_conversion_sensitivity",
            "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv",
            "fspdp_gdp_share_conversion_sensitivity",
            "fspdp_gdp_share_conversion_sensitivity_row_id",
            "sensitivity_status",
            "noncanonical_fspdp_gdp_share_conversion_sensitivity",
        ),
        (
            fspdp_lp_sample_share_closeout_decision_rows,
            "conventional_drag_fspdp_lp_sample_share_closeout_decision",
            "ratewall_conventional_drag_fspdp_lp_sample_share_closeout_decision.csv",
            "fspdp_lp_sample_share_closeout_decision",
            "fspdp_lp_sample_share_closeout_decision_row_id",
            "interpretation_decision_status",
            "fspdp_lp_sample_share_interpretation_closeout_review_only",
        ),
    ]
    for source_rows, family, artifact, surface_type, key_field, value_role, allowed_use in specs:
        for item in source_rows:
            rows.append(
                _row(
                    assumption_handle=f"{family}_{item.get(key_field, '')}",
                    assumption_family=family,
                    artifact_or_surface=artifact,
                    surface_type=surface_type,
                    upstream_row_key=item.get(key_field, ""),
                    scenario_or_path_scope=item.get("outcome_id", "")
                    or item.get("shock_series_id", "")
                    or item.get("required_gate", "")
                    or item.get("quarter", ""),
                    period_or_horizon=item.get("horizon_q", "")
                    or item.get("lp_response_horizon_q", "")
                    or item.get("quarter", ""),
                    value_role=value_role,
                    current_value_exact=(
                        item.get(
                            "beta_response_percent_per_100bp_year_exposure", ""
                        )
                        if family
                        in {
                            "conventional_drag_fspdp_value_bearing_exposure_lp_execution",
                            "conventional_drag_fspdp_denominator_conversion_uncertainty_boundary",
                        }
                        else item.get(
                            "positive_drag_gdp_share_per_100bp_year", ""
                        )
                        if family
                        == "conventional_drag_fspdp_gdp_share_conversion_sensitivity"
                        else item.get("sample_mean_nominal_share_of_gdp", "")
                        if family
                        == "conventional_drag_fspdp_lp_sample_base_share_join"
                        else item.get("relative_difference_from_baseline", "")
                        if family
                        == "conventional_drag_fspdp_lp_sample_share_closeout_decision"
                        else ""
                    ),
                    unit=(
                        "percent_real_fspdp_response_per_normalized_100bp_year_exposure"
                        if family
                        in {
                            "conventional_drag_fspdp_value_bearing_exposure_lp_execution",
                            "conventional_drag_fspdp_denominator_conversion_uncertainty_boundary",
                        }
                        else "fraction_of_nominal_gdp_per_100bp_year_noncanonical_sensitivity"
                        if family
                        == "conventional_drag_fspdp_gdp_share_conversion_sensitivity"
                        else "nominal_fspdp_share_of_nominal_gdp_lp_sample_base_quarter_mean"
                        if family
                        == "conventional_drag_fspdp_lp_sample_base_share_join"
                        else "relative_difference_between_lp_sample_and_baseline_fspdp_share"
                        if family
                        == "conventional_drag_fspdp_lp_sample_share_closeout_decision"
                        else item.get("source_unit_note", "")
                        or item.get("policy_path_normalization_case", "")
                    ),
                    source_backing_class="blocked_or_diagnostic_only",
                    source_backing_subclass="local_lp_diagnostic_not_calibration",
                    source_status_raw=item.get("source_admission_status", "")
                    or item.get("gate_status", "")
                    or item.get("promotion_status", "")
                    or item.get("denominator_readiness_status", "")
                    or item.get("denominator_candidate_join_preflight_status", "")
                    or item.get(
                        "denominator_conversion_uncertainty_boundary_status", ""
                    )
                    or item.get("gdp_share_conversion_design_gate_status", "")
                    or item.get("admission_status", "")
                    or item.get("baseline_comparison_status", "")
                    or item.get("sensitivity_status", "")
                    or item.get("interpretation_decision_status", "")
                    or item.get("response_estimate_status", ""),
                    calibration_status_raw="not_calibration",
                    claim_boundary_raw=item.get("claim_boundary", ""),
                    source_artifact=item.get("source_artifact_path", "")
                    or item.get("source_snapshot_path", "")
                    or artifact,
                    source_field_or_series=item.get("shock_series_id", "")
                    or item.get("exposure_series_id", "")
                    or item.get("outcome_id", "")
                    or item.get("required_gate", ""),
                    source_family="RateWall local diagnostic scaffold",
                    source_hash_or_manifest_hash=item.get("source_artifact_sha256", "")
                    or item.get("source_snapshot_sha256", ""),
                    support_diagnostics_present="true",
                    directness_class="diagnostic_design_not_denominator_value",
                    transport_risk="high_until_bps_year_normalization_passes",
                    manual_override_required="false",
                    calibration_needed=(
                        "admitted_100bp_year_policy_path_and_lp_validation"
                    ),
                    promotion_status="blocked_local_lp_diagnostic_only",
                    enters_noncanonical_assumption_mode="true",
                    allowed_use=item.get("allowed_use", allowed_use),
                    blocked_use=item.get("blocked_use", ""),
                    claim_boundary=item.get("claim_boundary", ""),
                    linked_source_tables=(
                        "ratewall_conventional_drag_local_macro_panel.csv;"
                        "ratewall_conventional_drag_local_shock_quarterly.csv;"
                        "ratewall_conventional_drag_local_lp_design.csv;"
                        "ratewall_conventional_drag_local_lp_diagnostic.csv;"
                        "ratewall_conventional_drag_local_lp_admission_audit.csv;"
                        "ratewall_conventional_drag_current_demand_mapping_bridge.csv;"
                        "ratewall_current_demand_gdp_share_panel.csv;"
                        "ratewall_current_demand_gdp_share_source_manifest.csv;"
                        "ratewall_policy_path_value_bearing_bps_year_exposure_quarterly_series.csv;"
                        "ratewall_conventional_drag_fspdp_value_bearing_exposure_lp_execution.csv;"
                        "ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv;"
                        "ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv;"
                        "ratewall_conventional_drag_fspdp_gdp_share_conversion_method_admission.csv;"
                        "ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv;"
                        "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv;"
                        "ratewall_conventional_drag_fspdp_lp_sample_share_closeout_decision.csv"
                    ),
                    **_copy_switches(item),
                )
            )
    return rows


def _openicpsr_replication_package_source_manifest_rows(
    manifest_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in manifest_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "openicpsr_replication_package_source_manifest_"
                    f"{item.get('source_candidate_handle', '')}_"
                    f"{item.get('package_object_handle', '')}"
                ),
                assumption_family="openicpsr_replication_package_source_manifest",
                artifact_or_surface=(
                    "ratewall_openicpsr_replication_package_source_manifest.csv"
                ),
                surface_type="replication_package_source_manifest",
                upstream_row_key=item.get("manifest_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                value_role=item.get("candidate_review_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "replication_package_metadata_not_denominator_value"
                ),
                source_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                calibration_status_raw=item.get("metadata_acquisition_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("metadata_artifact_path", ""),
                source_field_or_series=item.get(
                    "candidate_variable_or_file_inventory", ""
                ),
                source_family="openicpsr_aea_replication_package",
                support_diagnostics_present="true",
                directness_class=(
                    "openicpsr_replication_package_metadata_review_only"
                ),
                transport_risk="high_until_full_research_parameterization_passes",
                manual_override_required="false",
                calibration_needed="research_parameterization_source_contract",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use="openicpsr_replication_package_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_openicpsr_replication_package_source_manifest.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_frontier.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _frbus_model_benchmark_simulation_readiness_rows(
    readiness_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in readiness_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "frbus_model_benchmark_simulation_readiness_"
                    f"{item.get('artifact_handle', '')}_"
                    f"{item.get('readiness_field', '')}"
                ),
                assumption_family="frbus_model_benchmark_simulation_readiness",
                artifact_or_surface=(
                    "ratewall_frbus_model_benchmark_simulation_readiness.csv"
                ),
                surface_type="model_benchmark_simulation_readiness",
                upstream_row_key=item.get("readiness_row_id", ""),
                scenario_or_path_scope=item.get("source_candidate_handle", ""),
                value_role=item.get("readiness_field", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="official_model_readiness_not_calibration",
                source_status_raw=item.get("model_benchmark_admission_status", ""),
                calibration_status_raw=item.get("promotion_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("artifact_path", ""),
                source_field_or_series=item.get("candidate_file_or_variable", ""),
                source_family="frbus_official_model_benchmark",
                support_diagnostics_present="true",
                directness_class="official_model_readiness_review_only",
                transport_risk="high_until_shock_normalization_replication_and_uncertainty_pass",
                manual_override_required="false",
                calibration_needed="frbus_simulation_replication_and_mapping_contract",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use="frbus_model_benchmark_readiness_review_only",
                blocked_use=(
                    "denominator_prior_narrowing;main_ratio;Evidence_Mode;"
                    "pricing_output;raw_rate_shock;holder_allocation"
                ),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_frbus_model_benchmark_simulation_readiness.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_frontier.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _frbus_conventional_drag_benchmark_protocol_rows(
    protocol_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in protocol_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "frbus_conventional_drag_benchmark_protocol_"
                    f"{item.get('frbus_protocol_row_id', '')}"
                ),
                assumption_family="frbus_conventional_drag_benchmark_protocol",
                artifact_or_surface=(
                    "ratewall_frbus_conventional_drag_benchmark_protocol.csv"
                ),
                surface_type="frbus_benchmark_protocol",
                upstream_row_key=item.get("frbus_protocol_row_id", ""),
                scenario_or_path_scope=item.get("scenario_handle", ""),
                period_or_horizon=item.get("horizon_q", ""),
                value_role=item.get("outcome_id", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit="gdp_share_per_100bp_year_blank_until_protocol_passes",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="frbus_benchmark_protocol_not_calibration",
                source_status_raw=item.get("model_benchmark_admission_status", ""),
                calibration_status_raw=item.get("shock_normalization_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("artifact_path", ""),
                source_field_or_series=item.get("outcome_id", ""),
                source_family="frbus_official_model_benchmark",
                source_hash_or_manifest_hash=item.get("artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class="frbus_benchmark_protocol_review_only",
                transport_risk=(
                    "high_until_shock_normalization_replication_uncertainty_"
                    "and_mapping_pass"
                ),
                manual_override_required="false",
                calibration_needed="frbus_simulation_replication_and_mapping_contract",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_frbus_conventional_drag_benchmark_protocol.csv;"
                    "ratewall_frbus_model_benchmark_simulation_readiness.csv;"
                    "ratewall_conventional_drag_research_parameterization_"
                    "source_frontier.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _frbus_official_model_package_inventory_rows(
    inventory_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in inventory_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "frbus_official_model_package_inventory_"
                    f"{item.get('inventory_row_id', '')}"
                ),
                assumption_family="frbus_official_model_package_inventory",
                artifact_or_surface=(
                    "ratewall_frbus_official_model_package_inventory.csv"
                ),
                surface_type="frbus_official_model_package_inventory",
                upstream_row_key=item.get("inventory_row_id", ""),
                scenario_or_path_scope=item.get("artifact_handle", ""),
                value_role=item.get("inner_file_role", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "frbus_package_inventory_not_calibration"
                ),
                source_status_raw=item.get("model_benchmark_admission_status", ""),
                calibration_status_raw=item.get("acquisition_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("artifact_path", ""),
                source_field_or_series=item.get("inner_file_path", ""),
                source_family="frbus_official_model_benchmark",
                source_hash_or_manifest_hash=item.get("artifact_sha256", ""),
                support_diagnostics_present="true",
                directness_class="frbus_package_inventory_review_only",
                transport_risk=(
                    "high_until_reproducible_simulation_normalization_"
                    "uncertainty_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed=(
                    "frbus_reproducible_simulation_and_mapping_contract"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_frbus_official_model_package_inventory.csv;"
                    "ratewall_frbus_model_benchmark_simulation_readiness.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _frbus_official_model_benchmark_simulation_protocol_rows(
    protocol_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in protocol_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "frbus_official_model_benchmark_simulation_protocol_"
                    f"{item.get('simulation_protocol_row_id', '')}"
                ),
                assumption_family=(
                    "frbus_official_model_benchmark_simulation_protocol"
                ),
                artifact_or_surface=(
                    "ratewall_frbus_official_model_benchmark_"
                    "simulation_protocol.csv"
                ),
                surface_type="frbus_official_model_benchmark_simulation_protocol",
                upstream_row_key=item.get("simulation_protocol_row_id", ""),
                scenario_or_path_scope=item.get("scenario_handle", ""),
                period_or_horizon=item.get("horizon_q", ""),
                value_role=item.get("protocol_gate", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit="gdp_share_per_100bp_year_blank_until_protocol_passes",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "frbus_simulation_protocol_not_calibration"
                ),
                source_status_raw=item.get("model_benchmark_admission_status", ""),
                calibration_status_raw=item.get("gate_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("shock_source_artifact", ""),
                source_field_or_series=item.get("outcome_variable", ""),
                source_family="frbus_official_model_benchmark",
                source_hash_or_manifest_hash=item.get("pyfrbus_package_sha256", ""),
                support_diagnostics_present="true",
                directness_class="frbus_simulation_protocol_review_only",
                transport_risk=(
                    "high_until_simulation_execution_100bp_year_mapping_"
                    "uncertainty_replication_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed=(
                    "frbus_reproducible_simulation_and_mapping_contract"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_frbus_official_model_benchmark_simulation_"
                    "protocol.csv;ratewall_frbus_official_model_package_"
                    "inventory.csv;ratewall_frbus_conventional_drag_"
                    "benchmark_protocol.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _frbus_runtime_runner_preflight_rows(
    preflight_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in preflight_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "frbus_runtime_runner_preflight_"
                    f"{item.get('preflight_row_id', '')}"
                ),
                assumption_family="frbus_runtime_runner_preflight",
                artifact_or_surface="ratewall_frbus_runtime_runner_preflight.csv",
                surface_type="frbus_runtime_runner_preflight",
                upstream_row_key=item.get("preflight_row_id", ""),
                scenario_or_path_scope="official_100bp_rffintay_demo_review",
                period_or_horizon=item.get("step_id", ""),
                value_role="runtime_preflight_status",
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit="blank_until_frbus_benchmark_promotion_contract_passes",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="frbus_runtime_preflight_not_calibration",
                source_status_raw=item.get("model_benchmark_admission_status", ""),
                calibration_status_raw=item.get("runtime_step_status", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("pyfrbus_package_path", ""),
                source_field_or_series=item.get("step_id", ""),
                source_family="frbus_official_model_benchmark",
                source_hash_or_manifest_hash=item.get("pyfrbus_package_sha256", ""),
                support_diagnostics_present="true",
                directness_class="frbus_runtime_preflight_review_only",
                transport_risk=(
                    "high_until_100bp_year_mapping_gdp_share_conversion_"
                    "uncertainty_replication_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed="frbus_benchmark_replication_mapping_contract",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_frbus_runtime_runner_preflight.csv;"
                    "ratewall_frbus_official_model_package_inventory.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _frbus_runtime_runner_output_slots_rows(
    output_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in output_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "frbus_runtime_runner_output_slot_"
                    f"{item.get('output_slot_row_id', '')}"
                ),
                assumption_family="frbus_runtime_runner_output_slots",
                artifact_or_surface=(
                    "ratewall_frbus_runtime_runner_output_slots.csv"
                ),
                surface_type="frbus_runtime_runner_output_slots",
                upstream_row_key=item.get("output_slot_row_id", ""),
                scenario_or_path_scope=item.get("scenario_handle", ""),
                period_or_horizon=item.get("horizon_q", ""),
                value_role=item.get("output_slot_name", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit="gdp_share_per_100bp_year_blank_output_slot_review_only",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="frbus_runtime_output_slot_not_calibration",
                source_status_raw=item.get("model_benchmark_admission_status", ""),
                calibration_status_raw=item.get("runtime_step_status", ""),
                evidence_strength_raw=item.get("model_output_value_review_only", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact="frbus_runtime_runner_preflight_json",
                source_field_or_series=item.get("outcome_variable", ""),
                source_family="frbus_official_model_benchmark",
                source_hash_or_manifest_hash=item.get("pyfrbus_package_sha256", ""),
                support_diagnostics_present="true",
                directness_class="frbus_runtime_output_slot_review_only",
                transport_risk=(
                    "high_until_100bp_year_mapping_gdp_share_conversion_"
                    "uncertainty_replication_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed="frbus_benchmark_replication_mapping_contract",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_frbus_runtime_runner_output_slots.csv;"
                    "ratewall_frbus_runtime_runner_preflight.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _frbus_benchmark_comparison_mapping_contract_rows(
    contract_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in contract_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "frbus_benchmark_comparison_mapping_contract_"
                    f"{item.get('comparison_contract_row_id', '')}"
                ),
                assumption_family="frbus_benchmark_comparison_mapping_contract",
                artifact_or_surface=(
                    "ratewall_frbus_benchmark_comparison_mapping_contract.csv"
                ),
                surface_type="frbus_benchmark_comparison_mapping_contract",
                upstream_row_key=item.get("comparison_contract_row_id", ""),
                scenario_or_path_scope=item.get("scenario_handle", ""),
                period_or_horizon=item.get("horizon_q", ""),
                value_role=item.get("required_gate", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit="gdp_share_per_100bp_year_blank_until_all_gates_pass",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "frbus_benchmark_comparison_mapping_not_calibration"
                ),
                source_status_raw=item.get("model_benchmark_admission_status", ""),
                calibration_status_raw=item.get("replication_status", ""),
                evidence_strength_raw=item.get("pinned_model_output_value", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_preflight_json_path", ""),
                source_field_or_series=item.get("output_slot_name", ""),
                source_family="frbus_official_model_benchmark",
                source_hash_or_manifest_hash=item.get("source_preflight_json_sha256", ""),
                support_diagnostics_present="true",
                directness_class="frbus_comparison_mapping_contract_review_only",
                transport_risk=(
                    "high_until_policy_path_mapping_current_demand_conversion_"
                    "uncertainty_replication_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed="frbus_comparison_mapping_promotion_contract",
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_frbus_benchmark_comparison_mapping_contract.csv;"
                    "ratewall_frbus_runtime_runner_output_slots.csv;"
                    "ratewall_conventional_drag_current_demand_mapping_bridge.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _frbus_benchmark_output_slot_extension_review_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "frbus_benchmark_output_slot_extension_review_"
                    f"{item.get('extension_review_row_id', '')}"
                ),
                assumption_family=(
                    "frbus_benchmark_output_slot_extension_review"
                ),
                artifact_or_surface=(
                    "ratewall_frbus_benchmark_output_slot_extension_review.csv"
                ),
                surface_type="frbus_benchmark_output_slot_extension_review",
                upstream_row_key=item.get("extension_review_row_id", ""),
                scenario_or_path_scope=item.get("coverage_target_id", ""),
                period_or_horizon=item.get("horizon_q", ""),
                value_role=item.get("frbus_target_slot_id", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit="gdp_share_per_100bp_year_blank_extension_review_only",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "frbus_benchmark_output_slot_extension_not_calibration"
                ),
                source_status_raw=item.get("slot_discovery_status", ""),
                calibration_status_raw=item.get("model_benchmark_admission_status", ""),
                evidence_strength_raw=item.get("model_output_value_review_only", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("raw_extension_json_path", ""),
                source_field_or_series=item.get("candidate_model_variable", ""),
                source_family="frbus_official_model_benchmark",
                source_hash_or_manifest_hash=item.get("raw_extension_json_sha256", ""),
                support_diagnostics_present="true",
                directness_class="frbus_output_slot_extension_review_only",
                transport_risk=(
                    "high_until_policy_path_mapping_current_demand_conversion_"
                    "empirical_uncertainty_replication_robustness_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed=(
                    "direct_research_irf_or_promoted_model_benchmark_contract"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_frbus_benchmark_output_slot_extension_review.csv;"
                    "ratewall_conventional_drag_fspdp_external_source_acquisition_action_plan.csv;"
                    "ratewall_frbus_runtime_runner_output_slots.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_source_unit_aggregation_blocker_bridge_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_source_unit_aggregation_bridge_"
                    f"{item.get('source_unit_aggregation_bridge_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_source_unit_aggregation_blocker_bridge"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_source_unit_aggregation_"
                    "blocker_bridge.csv"
                ),
                surface_type="source_unit_aggregation_blocker_bridge",
                upstream_row_key=item.get("source_unit_aggregation_bridge_row_id", ""),
                scenario_or_path_scope=item.get("source_route_family", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("required_gate", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit="gdp_share_per_100bp_year_blank_bridge_review_only",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "source_unit_aggregation_blocker_bridge_not_calibration"
                ),
                source_status_raw=item.get("unified_gate_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                evidence_strength_raw=item.get("missing_source_backing_summary", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_route_surface", ""),
                source_field_or_series=item.get("source_output_handle", ""),
                source_family=item.get("source_route_family", ""),
                source_hash_or_manifest_hash=item.get("linked_upstream_hashes", ""),
                support_diagnostics_present="true",
                directness_class="source_unit_aggregation_blocker_bridge_only",
                transport_risk=(
                    "high_until_source_unit_horizon_current_demand_gdp_share_"
                    "policy_path_uncertainty_replication_robustness_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed=(
                    "complete_source_unit_to_gdp_share_drag_and_100bp_year_gate_stack"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv;"
                    "ratewall_conventional_drag_research_mir_4q8q_conversion_readiness_review.csv;"
                    "ratewall_conventional_drag_fspdp_research_side_action_plan_extraction_review.csv;"
                    "ratewall_frbus_benchmark_output_slot_extension_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_mirgk_targeted_gap_source_followup_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_mirgk_targeted_gap_followup_"
                    f"{item.get('targeted_gap_followup_row_id', '')}"
                ),
                assumption_family=(
                    "conventional_drag_mirgk_targeted_gap_source_followup"
                ),
                artifact_or_surface=(
                    "ratewall_conventional_drag_mirgk_targeted_gap_source_"
                    "followup.csv"
                ),
                surface_type="mirgk_targeted_gap_source_followup",
                upstream_row_key=item.get("targeted_gap_followup_row_id", ""),
                scenario_or_path_scope=item.get("coverage_target_id", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("targeted_alias_group", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit="gdp_share_per_100bp_year_blank_targeted_gap_review_only",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "mirgk_targeted_gap_source_followup_not_calibration"
                ),
                source_status_raw=item.get("targeted_hit_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                evidence_strength_raw=item.get("exact_blocker", ""),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=(
                    "ratewall_conventional_drag_research_extraction_candidate.csv"
                ),
                source_field_or_series=item.get("targeted_alias_tokens", ""),
                source_family=item.get("source_candidate_handle", ""),
                source_hash_or_manifest_hash=(
                    item.get("matched_payload_archive_sha256s", "")
                    or item.get("linked_official_component_source_hashes", "")
                ),
                support_diagnostics_present="true",
                directness_class="mirgk_targeted_gap_source_followup_only",
                transport_risk=(
                    "high_until_direct_component_irf_source_unit_conversion_"
                    "gdp_share_mapping_100bp_year_uncertainty_replication_"
                    "robustness_and_promotion_pass"
                ),
                manual_override_required="false",
                calibration_needed=(
                    "direct_component_irf_or_external_research_source_then_full_"
                    "source_unit_aggregation_gate_stack"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_mirgk_targeted_gap_source_followup.csv;"
                    "ratewall_conventional_drag_fspdp_source_code_search_review.csv;"
                    "ratewall_conventional_drag_research_extraction_candidate.csv;"
                    "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv;"
                    "ratewall_conventional_drag_fspdp_official_component_source_acquisition_execution.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _conventional_drag_promotion_contract_checklist_rows(
    review_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in review_rows:
        rows.append(
            _row(
                assumption_handle=(
                    "conventional_drag_promotion_contract_checklist_"
                    f"{item.get('promotion_contract_checklist_row_id', '')}"
                ),
                assumption_family="conventional_drag_promotion_contract_checklist",
                artifact_or_surface=(
                    "ratewall_conventional_drag_promotion_contract_checklist.csv"
                ),
                surface_type="promotion_contract_checklist",
                upstream_row_key=item.get("promotion_contract_checklist_row_id", ""),
                scenario_or_path_scope=item.get("source_route_family", ""),
                period_or_horizon=item.get("target_horizon_quarters", ""),
                value_role=item.get("required_gate", ""),
                current_value_exact=item.get(
                    "candidate_gdp_share_drag_per_100bp_year", ""
                ),
                unit="gdp_share_per_100bp_year_blank_promotion_contract_review_only",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass=(
                    "promotion_contract_checklist_not_calibration"
                ),
                source_status_raw=item.get("promotion_gate_pass_status", ""),
                calibration_status_raw=item.get(
                    "research_parameterization_admission_status", ""
                ),
                evidence_strength_raw=item.get(
                    "required_evidence_before_promotion", ""
                ),
                claim_boundary_raw=item.get("claim_boundary", ""),
                source_artifact=item.get("source_route_surface", ""),
                source_field_or_series=item.get("minimum_tolerance_field", ""),
                source_family=item.get("source_candidate_handle", ""),
                source_hash_or_manifest_hash=item.get("linked_upstream_hashes", ""),
                support_diagnostics_present="true",
                directness_class="promotion_contract_checklist_only",
                transport_risk=(
                    "high_until_all_14_promotion_contract_gates_pass_with_"
                    "allowed_evidence_and_backend_audit"
                ),
                manual_override_required="false",
                calibration_needed=(
                    "complete_14_gate_promotion_contract_before_any_denominator_use"
                ),
                promotion_status="blocked",
                enters_noncanonical_assumption_mode="true",
                allowed_use=item.get("allowed_use", ""),
                blocked_use=item.get("blocked_use", ""),
                claim_boundary=item.get("claim_boundary", ""),
                linked_source_tables=(
                    "ratewall_conventional_drag_promotion_contract_checklist.csv;"
                    "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv;"
                    "ratewall_conventional_drag_mirgk_targeted_gap_source_followup.csv;"
                    "ratewall_conventional_drag_research_policy_path_normalization_bridge_review.csv;"
                    "ratewall_policy_path_bps_year_normalization_review.csv"
                ),
                **_copy_switches(item),
            )
        )
    return rows


def _backend_schema_release_audit_rows(
    audit_rows: list[dict[str, str]],
    *,
    artifact: str,
    family: str,
    surface_type: str,
    row_key: str,
    status_field: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    by_artifact: dict[str, list[dict[str, str]]] = {}
    for item in audit_rows:
        artifact_name = item.get("artifact_name", artifact)
        by_artifact.setdefault(artifact_name, []).append(item)
    for artifact_name, items in sorted(by_artifact.items()):
        failing = [
            item
            for item in items
            if item.get(status_field, "") not in {"pass", "blocked"}
        ]
        first = items[0]
        rows.append(
            _row(
                assumption_handle=f"{family}_{artifact_name}",
                assumption_family=family,
                artifact_or_surface=artifact,
                surface_type=surface_type,
                upstream_row_key=first.get(row_key, ""),
                scenario_or_path_scope=artifact_name,
                value_role="backend_schema_release_guardrail_status",
                current_value_range_text=(
                    f"covered_rows={len(items)};failing_rows={len(failing)}"
                ),
                unit="audit_status",
                source_backing_class="blocked_or_diagnostic_only",
                source_backing_subclass="backend_schema_release_guardrail_not_evidence",
                source_status_raw=first.get(status_field, ""),
                calibration_status_raw="not_calibration",
                evidence_strength_raw="executable_backend_guardrail",
                claim_boundary_raw=first.get("claim_boundary", ""),
                source_artifact=artifact,
                source_field_or_series=status_field,
                source_family="ratewall_backend_schema_release_audit",
                support_diagnostics_present="true",
                directness_class="backend_guardrail_only",
                transport_risk="not_applicable_not_economic_evidence",
                manual_override_required="false",
                calibration_needed="none_backend_guardrail_only",
                promotion_status="blocked",
                allowed_use=first.get("allowed_use", ""),
                blocked_use=first.get("blocked_use", ""),
                claim_boundary=first.get("claim_boundary", ""),
                linked_source_tables=artifact,
                **_copy_switches(first),
            )
        )
    return rows


def _artifact_status_row(
    *,
    row: dict[str, str],
    artifact: str,
    handle: str,
    family: str,
    role: str,
) -> dict[str, str]:
    return _row(
        assumption_handle=handle,
        assumption_family=family,
        artifact_or_surface=artifact,
        surface_type="claim_boundary_audit",
        value_role=role,
        source_status_raw=row.get("audit_status", row.get("status", "")),
        source_artifact=artifact,
        source_field_or_series=handle,
        claim_boundary=row.get("claim_boundary", ""),
        linked_source_tables=artifact,
        **_copy_switches(row),
    )


def _sibling_input_rows(repo_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    specs = [
        (
            "../tdcsim/data/ratewall_inputs/tdcsim_ratewall_input_manifest.json",
            "tdcsim_ratewall_input_manifest",
            "tdcsim_input_contract",
        ),
        (
            "../tdcsim/data/ratewall_inputs/tdcsim_holder_absorption_path.csv",
            "tdcsim_holder_absorption_path",
            "tdcsim_holder_prior_not_allocation_evidence",
        ),
        (
            "../tdcsim/data/ratewall_inputs/tdcsim_yield_curve_surface.csv",
            "tdcsim_yield_curve_surface",
            "tdcsim_yield_curve_scenario_surface",
        ),
        (
            "../tdcsim/data/ratewall_inputs/tdcsim_primary_flow_to_du_path.csv",
            "tdcsim_primary_flow_to_du_path",
            "tdcsim_primary_flow_proxy",
        ),
        (
            "../tdcsim/output/ratewall_contract_source_backed/tdcsim_ratewall_source_registry.csv",
            "tdcsim_ratewall_source_registry",
            "tdcsim_output_source_registry",
        ),
    ]
    for rel_path, handle, family in specs:
        path = (repo_root / rel_path).resolve()
        rows.append(
            _row(
                assumption_handle=handle,
                assumption_family=family,
                artifact_or_surface=rel_path,
                surface_type="sibling_contract_input"
                if path.exists()
                else "missing_sibling_contract_input",
                value_role="sibling_contract_value",
                source_status_raw="sibling_contract_available"
                if path.exists()
                else "missing_expected_sibling_contract",
                source_artifact=rel_path,
                source_field_or_series=handle,
                source_family="tdcsim",
                source_record_count=str(_record_count(path)) if path.exists() else "0",
                source_hash_or_manifest_hash=_sha256(path) if path.exists() else "",
                sibling_project="tdcsim",
                sibling_contract_artifact=rel_path,
                allowed_use="noncanonical_forward_surface_input",
                blocked_use="holder_allocation_evidence"
                if "holder_absorption" in rel_path
                else "",
                claim_boundary=(
                    "tdcsim_sibling_contract_prior_not_ratewall_evidence_promotion"
                ),
                evidence_needed_before_promotion=(
                    "final-owner holder evidence and source gates"
                    if "holder_absorption" in rel_path
                    else ""
                ),
                missing_expected_artifact=_bool_text(not path.exists()),
            )
        )
    return rows


def _qrawatch_rows(repo_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    specs = [
        (
            "../qrawatch/output/publish/ati_quarter_table.csv",
            "qrawatch_ati_quarter_table",
            "qrawatch_ati_measurement",
            "official_measurement_value",
        ),
        (
            "../qrawatch/output/publish/ati_seed_vs_official.csv",
            "qrawatch_ati_seed_vs_official",
            "qrawatch_ati_readiness_gate",
            "official_measurement_readiness_gate",
        ),
        (
            "../qrawatch/output/publish/ati_seed_forecast_table.csv",
            "qrawatch_ati_seed_forecast_table",
            "qrawatch_forward_ati_blocker",
            "blocked_until_populated_and_validated",
        ),
        (
            "../qrawatch/output/publish/duration_supply_summary.csv",
            "qrawatch_duration_supply_summary",
            "qrawatch_duration_supply_context",
            "sensitivity_only_duration_supply_context",
        ),
        (
            "../qrawatch/output/publish/duration_supply_comparison.csv",
            "qrawatch_duration_supply_comparison",
            "qrawatch_duration_supply_context",
            "sensitivity_only_duration_supply_context",
        ),
        (
            "../qrawatch/output/publish/pricing_scenario_translation.csv",
            "qrawatch_pricing_scenario_translation",
            "qrawatch_pricing_translation_context",
            "not_ratewall_pricing_calibration",
        ),
        (
            "../qrawatch/output/publish/auction_absorption_table.csv",
            "qrawatch_auction_absorption_table",
            "qrawatch_auction_absorption_diagnostic",
            "diagnostic_not_holder_allocation",
        ),
        (
            "../qrawatch/output/publish/investor_allotments_summary.csv",
            "qrawatch_investor_allotments_summary",
            "qrawatch_holder_evidence_blocker",
            "blocked_until_populated_and_validated",
        ),
        (
            "../qrawatch/output/publish/plumbing_regression_summary.csv",
            "qrawatch_plumbing_regression_summary",
            "qrawatch_plumbing_diagnostic",
            "diagnostic_not_runtime_mechanics",
        ),
        (
            "../qrawatch/output/publish/qra_event_elasticity.csv",
            "qrawatch_qra_event_elasticity",
            "qrawatch_event_context",
            "sensitivity_only_event_context",
        ),
        (
            "../qrawatch/output/publish/qra_long_rate_translation_panel.csv",
            "qrawatch_qra_long_rate_translation_panel",
            "qrawatch_event_context",
            "sensitivity_only_event_context",
        ),
        (
            "../qrawatch/output/publish/qra_event_shock_components.csv",
            "qrawatch_qra_event_shock_components",
            "qrawatch_event_context",
            "sensitivity_only_event_context",
        ),
        (
            "../qrawatch/output/publish/qra_promotion_audit.csv",
            "qrawatch_qra_promotion_audit",
            "qrawatch_promotion_gate",
            "diagnostic_not_ratewall_promotion",
        ),
        (
            "../qrawatch/output/publish/causal_claims_status.csv",
            "qrawatch_causal_claims_status",
            "qrawatch_promotion_gate",
            "diagnostic_not_ratewall_promotion",
        ),
        (
            "../qrawatch/output/publish/dataset_status.csv",
            "qrawatch_dataset_status",
            "qrawatch_promotion_gate",
            "diagnostic_not_ratewall_promotion",
        ),
    ]
    for rel_path, handle, family, status in specs:
        path = (repo_root / rel_path).resolve()
        rows.append(
            _row(
                assumption_handle=handle,
                assumption_family=family,
                artifact_or_surface=rel_path,
                surface_type="qrawatch_scenario_source",
                value_role="qrawatch_scenario_context",
                enters_qrawatch_scenario_surface="true",
                source_status_raw=status if path.exists() else "missing_qrawatch_artifact",
                source_artifact=rel_path,
                source_field_or_series=handle,
                source_family="qrawatch",
                source_record_count=str(_record_count(path)) if path.exists() else "0",
                source_hash_or_manifest_hash=_sha256(path) if path.exists() else "",
                sibling_project="qrawatch",
                allowed_use="assumption_mode_sensitivity_context",
                blocked_use=(
                    "ratewall_pricing_output;holder_allocation_evidence;"
                    "evidence_mode;main_ratio"
                ),
                claim_boundary="qrawatch_scenario_context_not_ratewall_calibration",
                evidence_needed_before_promotion=(
                    "QRA Watch promotion gate with eligibility/status rows and "
                    "RateWall nonpromotion guardrails"
                ),
                missing_expected_artifact=_bool_text(not path.exists()),
            )
        )
    return rows


def _expected_artifact_rows(repo_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    expected = ["outputs/tables/ratewall_interest_income_proxy_range_registry.csv"]
    for rel_path in expected:
        path = repo_root / rel_path
        rows.append(
            _row(
                assumption_handle=f"expected_artifact::{Path(rel_path).name}",
                assumption_family="expected_artifact_coverage",
                artifact_or_surface=rel_path,
                surface_type="expected_artifact_audit",
                value_role="expected_artifact_presence",
                source_status_raw="expected_artifact_present"
                if path.exists()
                else "missing_expected_artifact",
                source_artifact=rel_path,
                source_field_or_series=Path(rel_path).name,
                source_family="ratewall_generated_output",
                allowed_use="release_governance",
                blocked_use="" if path.exists() else "downstream_source_backing_claim",
                claim_boundary="expected_artifact_coverage_not_model_claim",
                missing_expected_artifact=_bool_text(not path.exists()),
            )
        )
    return rows


def _apply_classification(row: dict[str, str]) -> dict[str, str]:
    haystack = " ".join(
        [
            row.get("source_status_raw", ""),
            row.get("calibration_status_raw", ""),
            row.get("evidence_strength_raw", ""),
            row.get("ratewall_use_status_raw", ""),
            row.get("artifact_or_surface", ""),
            row.get("assumption_family", ""),
            row.get("blocked_use", ""),
        ]
    ).lower()
    handle = row["assumption_handle"]
    value_role = row["value_role"]
    artifact = row["artifact_or_surface"]

    if row.get("assumption_family") == "policy_path_reviewed_protocol_source_context":
        source_class = "blocked_or_diagnostic_only"
        if "candidate_event_vector" in haystack:
            subclass = "candidate_event_vector_missing_bps_year_protocol"
        else:
            subclass = "partial_policy_path_context_missing_bps_year_vector"
    elif row.get("assumption_family") == "policy_path_protocol_source_acquisition":
        source_class = "blocked_or_diagnostic_only"
        subclass = "raw_protocol_source_artifact_not_reviewed_bps_year_protocol"
    elif row.get("assumption_family") == "policy_path_protocol_review_inventory":
        source_class = "blocked_or_diagnostic_only"
        subclass = "reviewed_protocol_context_not_bps_year_value"
    elif (
        row.get("assumption_family")
        == "policy_path_mps_scalar_replication_diagnostic"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "scalar_mps_replication_not_bps_year_protocol"
    elif row.get("assumption_family") == "policy_path_bps_year_blocker_decision":
        source_class = "blocked_or_diagnostic_only"
        subclass = "terminal_bps_year_bridge_absent_in_reviewed_sources"
    elif row.get("assumption_family") == "policy_path_event_level_candidate_vector":
        source_class = "blocked_or_diagnostic_only"
        subclass = "source_extracted_candidate_vector_only"
    elif (
        row.get("assumption_family")
        == "policy_path_contract_spec_acquisition_blocker"
    ):
        source_class = "blocked_or_diagnostic_only"
        if row.get("value_role") == "official_contract_spec_artifact_hashed_review_only":
            subclass = "official_contract_spec_hashed_not_bps_year_protocol"
        else:
            subclass = "official_contract_spec_not_acquired"
    elif row.get("assumption_family") == "policy_path_bps_year_source_protocol":
        source_class = "blocked_or_diagnostic_only"
        subclass = "required_policy_path_protocol_field_missing"
    elif (
        row.get("assumption_family")
        == "frbus_model_benchmark_simulation_readiness"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "official_model_readiness_not_calibration"
    elif row.get("assumption_family") == "frbus_conventional_drag_benchmark_protocol":
        source_class = "blocked_or_diagnostic_only"
        subclass = "frbus_benchmark_protocol_not_calibration"
    elif row.get("assumption_family") == "frbus_official_model_package_inventory":
        source_class = "blocked_or_diagnostic_only"
        subclass = "frbus_package_inventory_not_calibration"
    elif (
        row.get("assumption_family")
        == "frbus_official_model_benchmark_simulation_protocol"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "frbus_simulation_protocol_not_calibration"
    elif row.get("assumption_family") == "frbus_runtime_runner_preflight":
        source_class = "blocked_or_diagnostic_only"
        subclass = "frbus_runtime_preflight_not_calibration"
    elif row.get("assumption_family") == "frbus_runtime_runner_output_slots":
        source_class = "blocked_or_diagnostic_only"
        subclass = "frbus_runtime_output_slot_not_calibration"
    elif (
        row.get("assumption_family")
        == "frbus_benchmark_comparison_mapping_contract"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "frbus_benchmark_comparison_mapping_not_calibration"
    elif (
        row.get("assumption_family")
        == "frbus_benchmark_output_slot_extension_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "frbus_benchmark_output_slot_extension_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_source_unit_aggregation_blocker_bridge"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "source_unit_aggregation_blocker_bridge_not_calibration"
    elif row.get("assumption_family") in {
        "ratio_layer_registry",
        "estimation_target_registry",
        "channel_taxonomy_registry",
        "historical_interpretation_audit",
        "tdc_equation_variant_registry",
        "policy_path_source_extraction_task_packet",
        "policy_path_source_extraction_results",
        "policy_path_authored_protocol_completion_audit",
        "policy_path_protocol_completion_design_tranche",
        "policy_path_field_specific_pass_rule_design",
        "policy_path_field_specific_source_evidence_audit",
        "policy_path_source_locator_binding_review",
        "policy_path_exact_source_locator_remediation",
        "policy_path_exact_locator_field_closure_diagnostic",
        "policy_path_exact_locator_pass_rule_adjudication",
        "policy_path_terminal_no_hit_closure",
        "policy_path_independent_replication_target_design",
        "policy_path_authored_fail_closed_invariant_design",
        "policy_path_protocol_component_closure_rollup",
        "policy_path_locator_binding_closure_diagnostic",
        "policy_path_full_protocol_admission_gate_summary",
        "policy_path_source_bundle_field_exhaustion_decision",
        "policy_path_source_bundle_component_exhaustion_decision",
        "conventional_drag_empirical_target_registry",
        "conventional_drag_route_pruning_audit",
        "conventional_drag_response_design_gate",
        "denominator_response_estimate_registry",
        "denominator_formal_design_gate",
        "conventional_drag_response_execution_readiness_packet",
        "local_lp_proxy_svar_diagnostic_run_packet",
        "local_lp_proxy_svar_execution_preflight_results",
        "local_lp_proxy_svar_route_closure_decision",
        "conventional_drag_denominator_route_triage_synthesis",
        "policy_path_100bp_year_blocker_action_resolution",
        "policy_path_source_protocol_action_packet",
        "policy_path_source_protocol_pass_rule_harness",
        "policy_path_source_protocol_extraction_attempt_results",
        "policy_path_source_protocol_attempt_closure_handoff",
        "policy_path_promotion_grade_source_family_acquisition_packet",
        "policy_path_promotion_grade_source_family_acquisition_execution_preflight_results",
        "policy_path_source_family_execution_closure_selection_packet",
        "policy_path_current_artifact_manual_review_execution_packet",
        "policy_path_current_artifact_manual_review_result_attempt",
        "policy_path_source_author_manual_acquisition_followup_packet",
        "policy_path_source_author_manual_acquisition_execution_preflight_results",
        "policy_path_real_source_author_web_acquisition_attempt_packet",
        "policy_path_downloaded_artifact_locator_parse_adjudication_packet",
        "policy_path_locator_candidate_pass_rule_review_decision_packet",
        "policy_path_source_extraction_result_adjudication",
        "policy_path_component_gate_execution_rollup",
    }:
        source_class = "blocked_or_diagnostic_only"
        subclass = "backend_architecture_lock_guardrail_not_evidence"
    elif row.get("assumption_family") == "tdc_deposit_pass_through_regime_bridge":
        if "blocked" in haystack or "user_supplied_context" in haystack:
            source_class = "blocked_or_diagnostic_only"
            subclass = "prompt_or_missing_artifact_diagnostic_not_source_backed"
        elif (
            "pandemic_exclusion_diagnostic" in haystack
            or "diagnostic_not_dynamic_default" in haystack
        ):
            source_class = "blocked_or_diagnostic_only"
            subclass = "ea_tdc_source_artifact_backed_diagnostic_not_runtime"
        elif row.get("surface_type") == "sibling_source_import":
            source_class = "sibling_contract_value"
            subclass = "ea_tdc_deposit_pass_through_scenario_source"
        else:
            source_class = "scenario_assumption"
            subclass = "tdc_pass_through_regime_scenario_value"
    elif row.get("assumption_family") == "tdc_ea_tdc_pass_through_calibration_import":
        source_class = "blocked_or_diagnostic_only"
        subclass = "ea_tdc_pass_through_calibration_import_review_only"
    elif row.get("assumption_family") == "tdc_deposit_pass_through_scenario_contract":
        source_class = "blocked_or_diagnostic_only"
        subclass = "tdc_scenario_contract_review_not_runtime_selector"
    elif row.get("assumption_family") in {
        "backend_surface_schema_contract",
        "backend_artifact_claim_boundary_manifest",
        "release_archive_reproducibility_audit",
    }:
        source_class = "blocked_or_diagnostic_only"
        subclass = "backend_schema_release_guardrail_not_evidence"
    elif (
        row.get("assumption_family")
        == "tdc_deposit_pass_through_trigger_validation_preflight"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "tdc_trigger_validation_preflight_not_runtime_selector"
    elif (
        row.get("assumption_family")
        == "tdc_deposit_pass_through_scenario_contract_invariant_audit"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "tdc_scenario_contract_invariant_audit_not_runtime_selector"
    elif (
        row.get("assumption_family") == "tdc_liquidity_regime_trigger_evidence"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "tdc_liquidity_regime_trigger_review_not_runtime_selector"
    elif (
        row.get("assumption_family")
        == "tdc_liquidity_regime_trigger_promotion_protocol"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "tdc_liquidity_regime_promotion_protocol_missing_required_fields"
    elif (
        row.get("assumption_family")
        == "tdc_liquidity_regime_trigger_validation_evidence"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "tdc_liquidity_regime_validation_evidence_not_runtime_selector"
    elif row.get("assumption_family") in {
        "current_demand_gdp_share_source_manifest",
        "current_demand_gdp_share_panel",
        "conventional_drag_current_demand_mapping_bridge",
        "conventional_drag_fspdp_component_source_manifest",
        "conventional_drag_fspdp_component_share_panel",
    }:
        source_class = "official_source_value"
        subclass = "official_current_demand_conversion_input_not_drag_estimate"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_fspdp_coverage_candidate_scan"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_fspdp_coverage_candidate_scan_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_fspdp_coverage_weight_requirement_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "fspdp_coverage_weight_requirement_review_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_fspdp_coverage_priority_search_queue"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "fspdp_coverage_priority_search_queue_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_fspdp_source_code_search_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "fspdp_source_code_search_review_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_fspdp_external_source_acquisition_action_plan"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "fspdp_external_source_acquisition_plan_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_fspdp_official_component_source_acquisition_execution"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "fspdp_official_component_source_acquisition_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_fspdp_research_side_action_plan_extraction_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "fspdp_research_side_extraction_review_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_source_unit_conversion_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_source_unit_conversion_review_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_mir_replication_source_unit_audit"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_mir_replication_source_unit_audit_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_mir_source_unit_transformation_contract"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_mir_source_unit_transformation_contract_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_mir_target_horizon_reconciliation_contract"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_mir_target_horizon_reconciliation_contract_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_mir_horizon_rekeying_candidate_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_mir_horizon_rekeying_candidate_review_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_mir_h24_source_unit_audit"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_mir_h24_source_unit_audit_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_mir_h24_8q_rekeying_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_mir_h24_8q_rekeying_review_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_mir_4q8q_conversion_readiness_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_mir_4q8q_conversion_readiness_review_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_policy_path_normalization_bridge_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_policy_path_normalization_bridge_review_not_calibration"
    elif (
        row.get("assumption_family")
        == "policy_path_research_shock_source_evidence_protocol_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = (
            "policy_path_research_shock_source_evidence_protocol_review_not_calibration"
        )
    elif row.get("assumption_family") == "policy_path_source_code_workbook_object_inventory":
        source_class = "blocked_or_diagnostic_only"
        subclass = "policy_path_source_code_workbook_inventory_not_calibration"
    elif (
        row.get("assumption_family")
        == "policy_path_source_code_workbook_protocol_deep_review"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "policy_path_source_code_workbook_protocol_review_not_calibration"
    elif row.get("assumption_family") in {
        "policy_path_usmpd_pca_loading_backtransform_review",
        "policy_path_usmpd_scalar_score_replication_review",
        "policy_path_usmpd_pca_backtransform_gate_review",
        "policy_path_usmpd_instrument_decomposition_design_review",
        "policy_path_bps_year_candidate_path_design_contract",
        "policy_path_formula_replication_source_review",
    }:
        source_class = "blocked_or_diagnostic_only"
        subclass = "policy_path_usmpd_pca_backtransform_review_not_calibration"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_extraction_conversion_bridge"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_extraction_conversion_bridge_not_parameter_value"
    elif row.get("assumption_family") in {
        "conventional_drag_local_macro_panel",
        "conventional_drag_local_shock_quarterly",
        "conventional_drag_local_lp_design",
        "conventional_drag_local_lp_diagnostic",
        "conventional_drag_local_lp_estimate_diagnostic",
        "conventional_drag_local_lp_robustness_diagnostic",
        "conventional_drag_local_lp_sample_window_audit",
        "conventional_drag_local_lp_admission_audit",
        "conventional_drag_fspdp_denominator_readiness_gate",
        "conventional_drag_fspdp_denominator_candidate_join_preflight",
        "conventional_drag_fspdp_value_bearing_exposure_lp_execution",
        "conventional_drag_fspdp_denominator_conversion_uncertainty_boundary",
        "conventional_drag_fspdp_gdp_share_conversion_design_gate",
        "conventional_drag_fspdp_gdp_share_conversion_method_admission",
        "conventional_drag_fspdp_lp_sample_base_share_join",
        "conventional_drag_fspdp_gdp_share_conversion_sensitivity",
        "conventional_drag_fspdp_lp_sample_share_closeout_decision",
    }:
        source_class = "blocked_or_diagnostic_only"
        subclass = "local_lp_diagnostic_not_calibration"
    elif row.get("assumption_family") in {
        "policy_path_value_bearing_bps_year_exposure_export",
        "policy_path_value_bearing_bps_year_exposure_quarterly_series",
    }:
        source_class = "blocked_or_diagnostic_only"
        subclass = "value_bearing_policy_path_exposure_not_denominator"
    elif (
        row.get("assumption_family")
        == "conventional_drag_research_parameterization_parser_status"
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "research_parser_status_not_parameter_value"
    elif row.get("missing_expected_artifact") == "true" or any(
        token in haystack for token in ("blocked", "diagnostic_only")
    ):
        source_class = "blocked_or_diagnostic_only"
        subclass = "blocked_source_gate"
    elif row.get("assumption_family") == "tdsp_current_demand_mapping":
        source_class = "blocked_or_diagnostic_only"
        subclass = "tdsp_current_demand_mapping_diagnostic_only"
    elif row.get("assumption_family") == "tdsp_pce_dpi_policy_path_gate":
        source_class = "blocked_or_diagnostic_only"
        subclass = "tdsp_pce_dpi_policy_path_gate_diagnostic_only"
    elif handle == "contractionary_drag_gdp_share" or handle in SPLIT_DENOMINATOR_HANDLES:
        source_class = "literature_context_only_prior"
        subclass = "source_context_not_denominator_estimate"
    elif "source_context_available_not_denominator_estimate" in haystack:
        source_class = "literature_context_only_prior"
        subclass = "source_context_not_denominator_estimate"
    elif "split_denominator_assumption_prior" in haystack:
        source_class = "literature_context_only_prior"
        subclass = "composition_prior_not_channel_estimate"
    elif "tdc_forward_assumption_registry" in artifact:
        source_class = "scenario_assumption"
        subclass = "tdc_deposit_conversion_sensitivity_not_mpc"
    elif "qrawatch" in artifact and "pricing_scenario_translation" in artifact:
        source_class = "scenario_assumption"
        subclass = "qrawatch_reduced_form_scenario_context_not_ratewall_calibration"
    elif "qrawatch" in artifact and "auction_absorption" in artifact:
        source_class = "blocked_or_diagnostic_only"
        subclass = "diagnostic_context_only"
    elif "tdcsim" in artifact or "tdcest" in artifact or "sibling_contract" in haystack:
        source_class = "sibling_contract_value"
        subclass = "sibling_contract_projection"
    elif value_role == "literature_anchor":
        source_class = "literature_calibrated_prior"
        subclass = "direct_literature_anchor"
    elif "official_measurement_value" in haystack or "exact_official" in haystack:
        source_class = "official_source_value"
        subclass = "official_measurement_value"
    elif any(token in haystack for token in ("placeholder", "guess")):
        source_class = "pure_guess_or_placeholder"
        subclass = "zero_default_placeholder"
    elif any(token in haystack for token in ("assumption", "sensitivity", "scenario")):
        source_class = "scenario_assumption"
        subclass = "scenario_sensitivity_value"
    else:
        source_class = "scenario_assumption"
        subclass = "rule_based_default_scenario_assumption"

    row["source_backing_class"] = source_class
    row["source_backing_subclass"] = subclass
    row["classification_reason"] = (
        f"rule_based_mapping:{source_class}:{subclass}"
    )
    if source_class == "blocked_or_diagnostic_only" and not row["blocked_use"]:
        row["blocked_use"] = "promotion_without_source_gate"
    if source_class == "pure_guess_or_placeholder" and not row["guess_status"]:
        row["guess_status"] = "placeholder_or_zero_default_requires_review"
    return row


def _apply_overrides(
    row: dict[str, str], overrides: list[dict[str, str]]
) -> dict[str, str]:
    for override in overrides:
        if not _override_matches(row, override):
            continue
        for key, value in override.items():
            if key in {
                "assumption_handle",
                "artifact_or_surface",
                "scenario_or_path_scope",
            }:
                continue
            if key in row:
                row[key] = value
        row["manual_override_required"] = "true"
        row["manual_override_source"] = (
            "configs/ratewall_assumption_source_backing_overrides.yml"
        )
    return row


def _override_matches(row: dict[str, str], override: dict[str, str]) -> bool:
    for key in ("assumption_handle", "artifact_or_surface", "scenario_or_path_scope"):
        pattern = override.get(key, "*")
        if pattern != "*" and row.get(key, "") != pattern:
            return False
    return True


def _dedupe_and_finalize(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    finalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        row = {field: row.get(field, "") for field in ASSUMPTION_SOURCE_BACKING_LEDGER_FIELDS}
        row["current_value_range_text"] = row["current_value_range_text"] or _range_text(row)
        row["ledger_row_id"] = _ledger_id(row)
        if row["ledger_row_id"] in seen:
            continue
        seen.add(row["ledger_row_id"])
        finalized.append(row)
    return sorted(
        finalized,
        key=lambda item: (
            item["artifact_or_surface"],
            item["assumption_handle"],
            item["scenario_or_path_scope"],
            item["value_role"],
            item["period_or_horizon"],
        ),
    )


def _range_text(row: dict[str, str]) -> str:
    values = [
        ("exact", row["current_value_exact"]),
        ("low", row["current_value_low"]),
        ("base", row["current_value_base"]),
        ("high", row["current_value_high"]),
    ]
    return ";".join(f"{key}={value}" for key, value in values if value)


def _ledger_id(row: dict[str, str]) -> str:
    key = "|".join(
        [
            row["assumption_handle"],
            row["artifact_or_surface"],
            row["scenario_or_path_scope"],
            row["value_role"],
            row["period_or_horizon"],
            row["current_value_range_text"],
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def _copy_switches(row: dict[str, str]) -> dict[str, str]:
    return {
        field: row.get(field, "false") if row.get(field, "") else "false"
        for field in FORBIDDEN_SWITCH_FIELDS
    }


def _component_to_split_handle(component: str) -> str:
    mapping = {
        "borrowing_cost_drag": "borrowing_cost_drag_share",
        "credit_supply_drag": "credit_supply_drag_share",
        "asset_price_drag": "asset_price_drag_share",
        "expectations_drag": "expectations_drag_share",
        "exchange_rate_external_drag": "exchange_rate_external_drag_share",
        "scalar_conventional_drag_amplitude": "contractionary_drag_gdp_share",
    }
    return mapping.get(component, component)


def _handles_from_field(value: str) -> list[str]:
    if not value:
        return ["unmapped_assumption_handle"]
    handles = []
    for part in value.split(";"):
        token = part.strip()
        if not token:
            continue
        handle = token.split(":", 1)[0].strip()
        handles.append(_component_to_split_handle(handle))
    return handles or ["unmapped_assumption_handle"]


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _record_count(path: Path) -> int:
    if not path.exists():
        return 0
    if path.suffix.lower() == ".json":
        return 1
    with path.open(encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows_by_role(rows: Iterable[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["value_role"], []).append(row)
    return grouped


def _is_source_context_only(row: dict[str, str]) -> bool:
    text = " ".join(
        [
            row["source_status_raw"],
            row["evidence_strength_raw"],
            row["source_backing_subclass"],
        ]
    ).lower()
    return any(
        token in text
        for token in (
            "source_context",
            "not_denominator_estimate",
            "weak_literature_context",
            "split_denominator_assumption_prior",
        )
    )


def _audit_row(
    *,
    audit_item: str,
    passed: bool,
    evidence_summary: str,
    failure_mode_if_false: str,
) -> dict[str, str]:
    return {
        "audit_item": audit_item,
        "audit_status": "pass" if passed else "fail",
        "evidence_table": "ratewall_assumption_source_backing_ledger.csv",
        "evidence_summary": evidence_summary,
        "failure_mode_if_false": failure_mode_if_false,
        "claim_boundary": "assumption_source_backing_invariant_audit_not_promotion",
    }
