"""Fail-closed RateWall ratio-layer, claim, and extraction registries."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


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

ARCHITECTURE_GUARDRAIL_FIELDS = [
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "split_denominator_promotion_allowed",
    *FORBIDDEN_SWITCH_FIELDS,
]

RATEWALL_RATIO_LAYER_REGISTRY_FIELDS = [
    "ratio_layer_registry_row_id",
    "ratio_id",
    "layer_id",
    "equation_object_id",
    "equation_text",
    "equation_role",
    "mode_class",
    "numerator_symbol",
    "denominator_symbol",
    "numerator_component_class",
    "denominator_component_class",
    "allowed_numerator_channel_classes",
    "allowed_denominator_channel_classes",
    "excluded_channel_classes",
    "denominator_basis",
    "canonical_status",
    "source_backing_requirement",
    "design_only",
    "historical_reporting_status",
    "safe_sentence",
    "forbidden_sentence",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "empirical_threshold_claim_enabled",
    "canonical_ratio_entry",
    "source_status",
    "source_specific_artifacts",
    "source_specific_series_or_table_ids",
    "source_specific_urls_or_docs",
    "source_specific_citation_or_design_handles",
    "source_specific_evidence_status",
    "source_snapshot_kind_summary",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_ESTIMATION_TARGET_REGISTRY_FIELDS = [
    "estimation_target_registry_row_id",
    "object_id",
    "object_label",
    "object_family",
    "target_family",
    "theory_role",
    "estimation_target",
    "preferred_canonical_target",
    "mode_class",
    "shock_family",
    "normalization_basis",
    "required_unit",
    "source_family",
    "source_backing_requirement",
    "current_artifact_paths",
    "current_status",
    "admissibility_status",
    "benchmark_only",
    "assumption_mode_only",
    "promotion_gate",
    "safe_sentence",
    "forbidden_sentence",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "empirical_threshold_claim_enabled",
    "canonical_ratio_entry",
    "source_status",
    "source_specific_artifacts",
    "source_specific_series_or_table_ids",
    "source_specific_urls_or_docs",
    "source_specific_citation_or_design_handles",
    "source_specific_evidence_status",
    "source_snapshot_kind_summary",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_CONVENTIONAL_DRAG_EMPIRICAL_TARGET_REGISTRY_FIELDS = [
    "conventional_drag_empirical_target_registry_row_id",
    "route_id",
    "route_family",
    "route_label",
    "route_role",
    "target_id",
    "target_label",
    "target_quantity",
    "target_outcome_id",
    "target_horizon_scope",
    "preferred_canonical_target",
    "benchmark_only",
    "research_parameterization_only",
    "proxy_only",
    "source_backed_context_only",
    "source_families",
    "linked_evidence_tables",
    "linked_evidence_row_counts",
    "route_evidence_row_count",
    "policy_path_normalization_status",
    "source_unit_status",
    "target_horizon_reconciliation_status",
    "current_demand_mapping_status",
    "component_share_status",
    "component_coverage_status",
    "proxy_bridge_status",
    "gdp_share_conversion_status",
    "uncertainty_status",
    "replication_status",
    "robustness_status",
    "promotion_rule_status",
    "admission_status",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "safe_sentence",
    "forbidden_sentence",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "empirical_threshold_claim_enabled",
    "canonical_ratio_entry",
    "source_status",
    "source_specific_artifacts",
    "source_specific_series_or_table_ids",
    "source_specific_urls_or_docs",
    "source_specific_citation_or_design_handles",
    "source_specific_evidence_status",
    "source_snapshot_kind_summary",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_CONVENTIONAL_DRAG_ROUTE_PRUNING_AUDIT_FIELDS = [
    "conventional_drag_route_pruning_audit_row_id",
    "conventional_drag_empirical_target_registry_row_id",
    "route_id",
    "route_family",
    "route_label",
    "route_role",
    "target_id",
    "target_label",
    "target_quantity",
    "target_outcome_id",
    "preferred_canonical_target",
    "benchmark_only",
    "research_parameterization_only",
    "proxy_only",
    "source_backed_context_only",
    "pruning_decision",
    "pruning_status",
    "retained_backend_role",
    "excluded_from_roles",
    "required_gate_stack",
    "failed_gate_stack",
    "route_evidence_row_count",
    "linked_evidence_tables",
    "policy_path_normalization_status",
    "current_demand_mapping_status",
    "gdp_share_conversion_status",
    "uncertainty_status",
    "replication_status",
    "robustness_status",
    "promotion_rule_status",
    "admission_status",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "safe_sentence",
    "forbidden_sentence",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "empirical_threshold_claim_enabled",
    "canonical_ratio_entry",
    "source_status",
    "source_specific_artifacts",
    "source_specific_series_or_table_ids",
    "source_specific_urls_or_docs",
    "source_specific_citation_or_design_handles",
    "source_specific_evidence_status",
    "source_snapshot_kind_summary",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_CONVENTIONAL_DRAG_RESPONSE_DESIGN_GATE_FIELDS = [
    "conventional_drag_response_design_gate_row_id",
    "conventional_drag_route_pruning_audit_row_id",
    "conventional_drag_empirical_target_registry_row_id",
    "route_id",
    "route_family",
    "route_role",
    "target_id",
    "target_outcome_id",
    "design_gate",
    "design_gate_label",
    "gate_sequence_index",
    "required_evidence_before_admission",
    "observed_gate_status",
    "gate_pass_status",
    "gate_failure_semantics",
    "allowed_evidence_classes",
    "disallowed_shortcut_evidence",
    "response_design_status",
    "route_admission_status",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "empirical_threshold_claim_enabled",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_DENOMINATOR_RESPONSE_ESTIMATE_REGISTRY_FIELDS = [
    "denominator_response_estimate_registry_row_id",
    "conventional_drag_route_pruning_audit_row_id",
    "route_id",
    "route_family",
    "route_role",
    "target_id",
    "target_outcome_id",
    "estimator_id",
    "estimator_family",
    "estimator_label",
    "estimator_role",
    "target_horizon_quarters",
    "integration_window",
    "shock_or_policy_input_basis",
    "normalization_basis",
    "required_diagnostics",
    "observed_pass_gate_count",
    "observed_blocked_gate_count",
    "blocked_design_gates",
    "support_status",
    "pretrend_status",
    "placebo_status",
    "relevance_status",
    "sign_status",
    "uncertainty_status",
    "replication_status",
    "robustness_status",
    "promotion_status",
    "formal_design_gate_status",
    "response_estimate_registration_status",
    "source_admission_status",
    "registered_point_estimate",
    "registered_ci_lower",
    "registered_ci_upper",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "empirical_threshold_claim_enabled",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_DENOMINATOR_FORMAL_DESIGN_GATE_FIELDS = [
    "denominator_formal_design_gate_row_id",
    "denominator_response_estimate_registry_row_id",
    "conventional_drag_response_design_gate_row_id",
    "route_id",
    "estimator_id",
    "estimator_family",
    "target_id",
    "target_outcome_id",
    "target_horizon_quarters",
    "design_gate",
    "design_gate_label",
    "gate_sequence_index",
    "required_diagnostic_or_evidence",
    "observed_gate_status",
    "gate_pass_status",
    "formal_gate_status",
    "formal_gate_failure_semantics",
    "allowed_evidence_classes",
    "disallowed_shortcut_evidence",
    "registered_point_estimate",
    "registered_ci_lower",
    "registered_ci_upper",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_CONVENTIONAL_DRAG_RESPONSE_EXECUTION_READINESS_PACKET_FIELDS = [
    "conventional_drag_response_execution_readiness_packet_row_id",
    "route_id",
    "route_family",
    "route_role",
    "target_id",
    "target_outcome_id",
    "execution_route_class",
    "preferred_canonical_target",
    "benchmark_only",
    "research_parameterization_only",
    "diagnostic_only",
    "required_input_artifacts",
    "linked_target_registry_row_id",
    "linked_route_pruning_audit_row_id",
    "linked_response_design_gate_row_ids",
    "linked_response_estimate_registry_row_ids",
    "linked_formal_design_gate_row_ids",
    "linked_source_route_tables",
    "command_or_estimation_procedure",
    "unit_conversion_requirement",
    "current_demand_mapping_requirement",
    "policy_path_100bp_year_dependency",
    "uncertainty_requirement",
    "replication_requirement",
    "formal_pass_fail_gates",
    "formal_design_gate_status",
    "observed_blocked_gate_count",
    "response_execution_readiness_status",
    "route_admission_status",
    "terminal_blocker",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_LOCAL_LP_PROXY_SVAR_DIAGNOSTIC_RUN_PACKET_FIELDS = [
    "local_lp_proxy_svar_diagnostic_run_packet_row_id",
    "route_id",
    "estimator_id",
    "estimator_family",
    "target_id",
    "target_outcome_id",
    "target_horizon_quarters",
    "integration_window",
    "run_task_class",
    "estimator_variant",
    "executable_command_shape",
    "required_input_artifacts",
    "linked_response_execution_readiness_packet_row_id",
    "linked_denominator_response_estimate_registry_row_id",
    "linked_response_design_gate_row_ids",
    "linked_formal_design_gate_row_ids",
    "linked_local_lp_design_row_ids",
    "linked_local_lp_diagnostic_row_ids",
    "linked_local_lp_estimate_diagnostic_row_ids",
    "linked_local_lp_robustness_diagnostic_row_ids",
    "linked_local_lp_sample_window_audit_row_ids",
    "linked_local_lp_admission_audit_row_ids",
    "linked_proxy_svar_diagnostic_artifacts",
    "design_preflight_checks",
    "sample_window_requirement",
    "policy_path_100bp_year_dependency",
    "current_demand_mapping_requirement",
    "unit_conversion_requirement",
    "uncertainty_method_placeholder",
    "replication_expectation",
    "blocked_formal_gates",
    "observed_blocked_gate_count",
    "diagnostic_run_status",
    "route_admission_status",
    "terminal_blocker",
    "registered_point_estimate",
    "registered_ci_lower",
    "registered_ci_upper",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_LOCAL_LP_PROXY_SVAR_EXECUTION_PREFLIGHT_RESULTS_FIELDS = [
    "local_lp_proxy_svar_execution_preflight_results_row_id",
    "local_lp_proxy_svar_diagnostic_run_packet_row_id",
    "route_id",
    "estimator_id",
    "estimator_family",
    "target_id",
    "target_outcome_id",
    "target_horizon_quarters",
    "run_task_class",
    "estimator_variant",
    "executable_command_shape",
    "command_shape_readiness_status",
    "required_input_artifacts",
    "required_artifact_presence_status",
    "required_artifact_present_count",
    "required_artifact_missing_count",
    "missing_required_artifacts",
    "linked_local_proxy_diagnostic_coverage_status",
    "local_lp_coverage_status",
    "proxy_svar_coverage_status",
    "local_lp_diagnostic_row_count",
    "local_lp_estimate_diagnostic_row_count",
    "local_lp_robustness_diagnostic_row_count",
    "proxy_svar_feasibility_row_count",
    "proxy_svar_system_panel_row_count",
    "proxy_svar_relevance_row_count",
    "proxy_svar_residual_row_count",
    "proxy_svar_timing_row_count",
    "design_preflight_status",
    "formal_gate_blocker_status",
    "blocked_formal_gates",
    "observed_blocked_gate_count",
    "source_unit_result_boundary_status",
    "execution_result_status",
    "terminal_blocker",
    "registered_point_estimate",
    "registered_ci_lower",
    "registered_ci_upper",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_LOCAL_LP_PROXY_SVAR_ROUTE_CLOSURE_DECISION_FIELDS = [
    "local_lp_proxy_svar_route_closure_decision_row_id",
    "route_id",
    "route_label",
    "decision_scope",
    "source_run_packet_artifact",
    "source_preflight_results_artifact",
    "run_packet_row_count",
    "preflight_results_row_count",
    "estimator_ids_covered",
    "target_horizons_covered",
    "required_artifacts_summary",
    "present_diagnostics_summary",
    "command_preflight_readiness_status",
    "required_artifact_presence_status",
    "diagnostic_coverage_status",
    "remaining_formal_gates",
    "remaining_formal_gate_count",
    "source_unit_result_boundary_status",
    "denominator_entry_blocker",
    "terminal_blocker_status",
    "route_closure_status",
    "why_outputs_cannot_enter_denominator",
    "registered_point_estimate",
    "registered_ci_lower",
    "registered_ci_upper",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_CONVENTIONAL_DRAG_DENOMINATOR_ROUTE_TRIAGE_SYNTHESIS_FIELDS = [
    "conventional_drag_denominator_route_triage_synthesis_row_id",
    "route_id",
    "route_family",
    "route_label",
    "route_role",
    "triage_rank",
    "triage_bucket",
    "target_id",
    "target_outcome_id",
    "preferred_canonical_target",
    "benchmark_only",
    "research_parameterization_only",
    "proxy_only",
    "source_backed_context_only",
    "linked_route_pruning_audit_row_id",
    "linked_response_design_gate_row_ids",
    "linked_denominator_response_estimate_registry_row_ids",
    "linked_formal_design_gate_row_ids",
    "linked_execution_readiness_packet_row_id",
    "linked_local_lp_proxy_svar_route_closure_decision_row_id",
    "route_pruning_status",
    "response_design_gate_count",
    "response_design_pass_review_only_count",
    "response_design_blocked_gate_count",
    "response_estimate_registry_row_count",
    "formal_design_gate_count",
    "formal_design_blocked_gate_count",
    "execution_readiness_packet_status",
    "local_lp_proxy_svar_closure_status",
    "required_artifacts_summary",
    "required_gate_stack",
    "blocked_gate_stack",
    "shared_blocker_summary",
    "route_specific_terminal_blocker",
    "route_admission_status",
    "denominator_admission_status",
    "route_triage_status",
    "project_next_backend_action",
    "route_next_backend_action",
    "single_next_backend_action_rank",
    "candidate_bps_year_exposure",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_CHANNEL_TAXONOMY_REGISTRY_FIELDS = [
    "channel_taxonomy_registry_row_id",
    "channel_id",
    "subchannel_id",
    "source_channel_label",
    "source_artifact",
    "ratio_layer",
    "mode_class",
    "channel_role",
    "enters_rw_y_numerator",
    "enters_rw_y_denominator",
    "enters_rw_pi_numerator",
    "enters_rw_pi_denominator",
    "enters_price_sidecar",
    "enters_context_only",
    "forbidden_ratio_layers",
    "source_status",
    "assumption_mode_status",
    "promotion_status",
    "double_count_risk",
    "safe_sentence",
    "forbidden_sentence",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_HISTORICAL_INTERPRETATION_AUDIT_FIELDS = [
    "historical_interpretation_audit_row_id",
    "claim_id",
    "claim_text",
    "artifact_family",
    "artifact_name",
    "source_output_path",
    "denominator_basis",
    "assumption_case",
    "period_family",
    "reported_ratio_min",
    "reported_ratio_max",
    "source_mode_label",
    "canonical_status",
    "support_status",
    "historical_reporting_status",
    "near_zero_denominator_flag",
    "covid_liquidity_regime_flag",
    "requires_100bp_denominator",
    "value_admission_status",
    "blocker",
    "safe_sentence",
    "forbidden_sentence",
    "enters_main_paper_claim",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_TDC_EQUATION_VARIANT_REGISTRY_FIELDS = [
    "tdc_equation_variant_registry_row_id",
    "tdc_variant_id",
    "overlap_bucket",
    "equation_text",
    "tdc_base_definition",
    "tdc_change_sign_rule",
    "deposit_pass_through_basis",
    "current_demand_conversion_status",
    "direct_interest_overlap_treatment",
    "iorb_rrp_mmf_treatment",
    "bank_balance_sheet_treatment",
    "foreign_leakage_treatment",
    "regime_sign",
    "replace_vs_stack_semantics",
    "source_artifacts",
    "source_status",
    "admission_status",
    "allowed_for_rw_y",
    "allowed_for_rw_pi",
    "assumption_mode_only",
    "double_count_exclusion_pairs",
    "safe_sentence",
    "forbidden_sentence",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_EXTRACTION_TASK_PACKET_FIELDS = [
    "policy_path_source_extraction_task_packet_row_id",
    "field_evidence_resolution_queue_row_id",
    "protocol_field_authoring_contract_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "authored_field_label",
    "field_resolution_class",
    "field_resolution_status",
    "task_class",
    "source_artifact_path",
    "source_locator_required",
    "linked_source_hit_row_ids",
    "linked_source_snippet_sample",
    "linked_no_hit_row_ids",
    "parser_strategy",
    "required_row_or_line_ref",
    "evidence_acceptance_test",
    "output_field_to_fill",
    "pass_status_value",
    "blocked_status_value",
    "extraction_status",
    "extraction_blocker",
    "next_backend_action",
    "promotion_grade_evidence_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_EXTRACTION_RESULTS_FIELDS = [
    "policy_path_source_extraction_result_row_id",
    "policy_path_source_extraction_task_packet_row_id",
    "field_evidence_resolution_queue_row_id",
    "protocol_field_authoring_contract_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "task_class",
    "task_execution_class",
    "source_artifact_paths",
    "source_artifact_sha256s",
    "computed_source_artifact_sha256s",
    "hash_verification_status",
    "linked_source_hit_row_ids",
    "linked_no_hit_row_ids",
    "linked_source_hit_count",
    "linked_no_hit_count",
    "review_only_hit_count",
    "promotion_grade_hit_count",
    "parser_strategy",
    "parser_execution_status",
    "source_locator_status",
    "source_row_or_line_ref_status",
    "source_quote_or_structured_evidence",
    "source_quote_support_status",
    "extracted_field_name",
    "extracted_field_value",
    "extracted_field_status",
    "pass_status_value",
    "blocked_status_value",
    "field_execution_status",
    "field_execution_blocker",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_EXTRACTION_RESULT_ADJUDICATION_FIELDS = [
    "policy_path_source_extraction_result_adjudication_row_id",
    "policy_path_source_extraction_task_packet_row_id",
    "policy_path_source_extraction_result_row_id",
    "policy_path_locator_candidate_pass_rule_review_decision_packet_row_id",
    "field_evidence_resolution_queue_row_id",
    "protocol_field_authoring_contract_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "source_family",
    "source_path",
    "source_sha256",
    "computed_source_sha256",
    "source_row_or_cell",
    "source_literal_value",
    "parsed_value",
    "parsed_unit",
    "parsed_sign",
    "parser_command",
    "parser_or_manual_review_command",
    "reviewer_status",
    "machine_audit_status",
    "source_evidence_status",
    "field_gate_status",
    "pass_status_value",
    "blocked_status_value",
    "candidate_bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "next_action_if_blocked",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_AUTHORED_PROTOCOL_COMPLETION_AUDIT_FIELDS = [
    "policy_path_authored_protocol_completion_audit_row_id",
    "policy_path_source_extraction_result_row_id",
    "policy_path_source_extraction_task_packet_row_id",
    "field_evidence_resolution_queue_row_id",
    "protocol_field_authoring_contract_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "task_class",
    "task_execution_class",
    "completion_task_class",
    "component_field_count",
    "component_completed_field_count",
    "component_blocked_field_count",
    "component_completion_status",
    "source_extraction_completion_status",
    "independent_replication_design_status",
    "authored_invariant_status",
    "promotion_grade_evidence_status",
    "field_value_status",
    "field_protocol_completion_status",
    "required_completion_evidence",
    "missing_completion_evidence",
    "linked_source_hit_row_ids",
    "linked_no_hit_row_ids",
    "linked_source_hit_count",
    "linked_no_hit_count",
    "review_only_hit_count",
    "promotion_grade_hit_count",
    "hash_verification_status",
    "source_locator_status",
    "source_row_or_line_ref_status",
    "source_quote_support_status",
    "extracted_field_name",
    "extracted_field_value",
    "pass_status_value",
    "blocked_status_value",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_PROTOCOL_COMPLETION_DESIGN_TRANCHE_FIELDS = [
    "policy_path_protocol_completion_design_tranche_row_id",
    "policy_path_authored_protocol_completion_audit_row_id",
    "policy_path_source_extraction_result_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "completion_task_class",
    "design_deliverable_class",
    "deliverable_name",
    "machine_test_target",
    "machine_testable_requirement",
    "required_input_artifacts",
    "required_output_artifact",
    "required_output_field",
    "required_pass_condition",
    "required_failure_condition",
    "runtime_switch_guardrail",
    "non_admission_preservation_rule",
    "source_extraction_non_admission_status",
    "independent_replication_design_deliverable_status",
    "authored_invariant_design_deliverable_status",
    "design_tranche_status",
    "implementation_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_INDEPENDENT_REPLICATION_TARGET_DESIGN_FIELDS = [
    "policy_path_independent_replication_target_design_row_id",
    "policy_path_protocol_completion_design_tranche_row_id",
    "policy_path_authored_protocol_completion_audit_row_id",
    "policy_path_source_extraction_result_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "required_output_field",
    "replication_design_role",
    "replication_design_deliverable",
    "source_artifact_requirements",
    "admissible_source_artifact_class",
    "disallowed_source_artifact_class",
    "replication_command_or_procedure",
    "expected_output_value_table",
    "pass_fail_audit_field",
    "replication_target_artifact",
    "replication_target_artifact_hash_requirement",
    "numeric_tolerance",
    "tolerance_unit",
    "tolerance_comparison",
    "pass_status_value",
    "blocked_status_value",
    "machine_testable_pass_condition",
    "machine_testable_fail_condition",
    "design_completion_status",
    "implementation_status",
    "replication_admission_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_FIELD_SPECIFIC_PASS_RULE_DESIGN_FIELDS = [
    "policy_path_field_specific_pass_rule_design_row_id",
    "policy_path_protocol_completion_design_tranche_row_id",
    "policy_path_authored_protocol_completion_audit_row_id",
    "policy_path_source_extraction_result_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "required_output_field",
    "source_field_role",
    "source_locator_requirement",
    "row_line_cell_reference_requirement",
    "extracted_value_requirement",
    "source_quote_cell_evidence_requirement",
    "field_acceptance_test",
    "promotion_grade_evidence_requirement",
    "disallowed_shortcuts",
    "pass_status_value",
    "blocked_status_value",
    "machine_test_target",
    "machine_testable_pass_condition",
    "machine_testable_fail_condition",
    "design_completion_status",
    "implementation_status",
    "field_pass_rule_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_FIELD_SPECIFIC_SOURCE_EVIDENCE_AUDIT_FIELDS = [
    "policy_path_field_specific_source_evidence_audit_row_id",
    "policy_path_field_specific_pass_rule_design_row_id",
    "policy_path_protocol_completion_design_tranche_row_id",
    "policy_path_authored_protocol_completion_audit_row_id",
    "policy_path_source_extraction_result_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "source_field_role",
    "linked_source_hit_row_ids",
    "linked_no_hit_row_ids",
    "linked_source_hit_count",
    "linked_no_hit_count",
    "review_only_hit_count",
    "promotion_grade_hit_count",
    "source_artifact_paths",
    "source_artifact_sha256s",
    "hash_verification_status",
    "source_locator_requirement",
    "source_locator_status",
    "source_locator_completeness_status",
    "row_line_cell_reference_requirement",
    "source_row_or_line_ref_status",
    "row_line_cell_reference_completeness_status",
    "extracted_value_requirement",
    "extracted_field_name",
    "extracted_field_value",
    "extracted_value_completeness_status",
    "source_quote_cell_evidence_requirement",
    "source_quote_support_status",
    "source_quote_cell_evidence_completeness_status",
    "source_quote_or_structured_evidence",
    "promotion_grade_evidence_requirement",
    "promotion_grade_evidence_status",
    "field_acceptance_test",
    "pass_status_value",
    "blocked_status_value",
    "pass_rule_result_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_LOCATOR_BINDING_REVIEW_FIELDS = [
    "policy_path_source_locator_binding_review_row_id",
    "policy_path_field_specific_source_evidence_audit_row_id",
    "policy_path_field_specific_pass_rule_design_row_id",
    "policy_path_source_extraction_result_row_id",
    "linked_source_hit_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "source_field_role",
    "source_artifact_paths",
    "source_artifact_sha256s",
    "computed_source_artifact_sha256s",
    "hash_verification_status",
    "target_pattern_set",
    "target_pattern_terms",
    "target_parse_hit_count",
    "target_parse_snippet_count",
    "target_parse_status",
    "target_parse_decision",
    "source_locator_requirement",
    "source_locator_binding_status",
    "machine_locator_kind",
    "machine_locator_value",
    "row_line_cell_reference_requirement",
    "row_line_cell_reference_status",
    "extracted_value_requirement",
    "extracted_field_name",
    "extracted_field_value",
    "extracted_value_binding_status",
    "source_quote_cell_evidence_requirement",
    "source_quote_or_structured_evidence",
    "source_quote_binding_status",
    "promotion_grade_evidence_requirement",
    "promotion_grade_evidence_status",
    "field_acceptance_test",
    "pass_status_value",
    "blocked_status_value",
    "locator_pass_rule_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_LOCATOR_BINDING_CLOSURE_DIAGNOSTIC_FIELDS = [
    "policy_path_locator_binding_closure_diagnostic_row_id",
    "policy_path_protocol_component_closure_rollup_row_id",
    "protocol_component",
    "protocol_component_gate",
    "component_role",
    "source_field_count",
    "source_locator_binding_row_count",
    "hash_verified_binding_row_count",
    "exact_locator_pass_count",
    "row_line_cell_pass_count",
    "extracted_value_pass_count",
    "quote_evidence_pass_count",
    "promotion_grade_evidence_count",
    "review_only_binding_count",
    "blocked_locator_failure_count",
    "linked_locator_binding_row_ids",
    "linked_source_evidence_audit_row_ids",
    "linked_independent_replication_design_row_ids",
    "linked_authored_invariant_design_row_ids",
    "locator_binding_closure_status",
    "component_closure_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_EXACT_SOURCE_LOCATOR_REMEDIATION_FIELDS = [
    "policy_path_exact_source_locator_remediation_row_id",
    "policy_path_source_locator_binding_review_row_id",
    "policy_path_field_specific_source_evidence_audit_row_id",
    "policy_path_field_specific_pass_rule_design_row_id",
    "linked_source_hit_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "source_artifact_path",
    "source_artifact_sha256",
    "computed_source_artifact_sha256",
    "hash_verification_status",
    "artifact_parser_class",
    "artifact_locator_kind",
    "exact_source_locator",
    "matched_pattern_terms",
    "matched_text_excerpt",
    "terminal_no_hit_blocker",
    "source_locator_candidate_status",
    "row_line_cell_reference_status",
    "extracted_field_name",
    "extracted_field_value_review_only",
    "extracted_value_binding_status",
    "source_quote_binding_status",
    "promotion_grade_evidence_status",
    "pass_rule_result_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "empirical_threshold_claim_enabled",
    "canonical_ratio_entry",
    "source_status",
    "source_specific_artifacts",
    "source_specific_series_or_table_ids",
    "source_specific_urls_or_docs",
    "source_specific_citation_or_design_handles",
    "source_specific_evidence_status",
    "source_snapshot_kind_summary",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_EXACT_LOCATOR_FIELD_CLOSURE_DIAGNOSTIC_FIELDS = [
    "policy_path_exact_locator_field_closure_diagnostic_row_id",
    "policy_path_field_specific_source_evidence_audit_row_id",
    "policy_path_field_specific_pass_rule_design_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "exact_locator_remediation_row_count",
    "exact_locator_candidate_count",
    "terminal_no_hit_count",
    "extracted_value_candidate_count",
    "promotion_grade_evidence_count",
    "field_pass_count",
    "linked_exact_locator_remediation_row_ids",
    "field_locator_closure_status",
    "pass_rule_result_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "empirical_threshold_claim_enabled",
    "canonical_ratio_entry",
    "source_status",
    "source_specific_artifacts",
    "source_specific_series_or_table_ids",
    "source_specific_urls_or_docs",
    "source_specific_citation_or_design_handles",
    "source_specific_evidence_status",
    "source_snapshot_kind_summary",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_EXACT_LOCATOR_PASS_RULE_ADJUDICATION_FIELDS = [
    "policy_path_exact_locator_pass_rule_adjudication_row_id",
    "policy_path_exact_source_locator_remediation_row_id",
    "policy_path_source_locator_binding_review_row_id",
    "policy_path_field_specific_source_evidence_audit_row_id",
    "policy_path_field_specific_pass_rule_design_row_id",
    "linked_source_hit_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "source_artifact_path",
    "source_artifact_sha256",
    "exact_source_locator",
    "matched_pattern_terms",
    "matched_text_excerpt",
    "terminal_no_hit_blocker",
    "required_evidence_class",
    "observed_locator_evidence_class",
    "adjudication_class",
    "adjudicated_missing_evidence_class",
    "field_contract_requirement",
    "promotion_grade_requirement",
    "candidate_context_status",
    "terminal_no_hit_status",
    "pass_rule_adjudication_status",
    "field_pass_rule_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "empirical_threshold_claim_enabled",
    "canonical_ratio_entry",
    "source_status",
    "source_specific_artifacts",
    "source_specific_series_or_table_ids",
    "source_specific_urls_or_docs",
    "source_specific_citation_or_design_handles",
    "source_specific_evidence_status",
    "source_snapshot_kind_summary",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_TERMINAL_NO_HIT_CLOSURE_FIELDS = [
    "policy_path_terminal_no_hit_closure_row_id",
    "policy_path_field_specific_source_evidence_audit_row_id",
    "policy_path_field_specific_pass_rule_design_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "required_evidence_class",
    "adjudication_row_count",
    "candidate_context_locator_count",
    "terminal_no_hit_count",
    "promotion_grade_evidence_count",
    "field_pass_count",
    "linked_pass_rule_adjudication_row_ids",
    "source_bundle_closure_status",
    "terminal_no_hit_closure_status",
    "field_pass_rule_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "empirical_threshold_claim_enabled",
    "canonical_ratio_entry",
    "source_status",
    "source_specific_artifacts",
    "source_specific_series_or_table_ids",
    "source_specific_urls_or_docs",
    "source_specific_citation_or_design_handles",
    "source_specific_evidence_status",
    "source_snapshot_kind_summary",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_PROTOCOL_COMPONENT_CLOSURE_ROLLUP_FIELDS = [
    "policy_path_protocol_component_closure_rollup_row_id",
    "protocol_component",
    "protocol_component_gate",
    "component_role",
    "source_field_count",
    "source_field_pass_count",
    "source_field_blocked_count",
    "review_only_source_hit_count",
    "promotion_grade_source_evidence_count",
    "source_evidence_status",
    "independent_replication_design_field_count",
    "independent_replication_design_pass_count",
    "independent_replication_design_blocked_count",
    "independent_replication_design_status",
    "authored_invariant_field_count",
    "authored_invariant_design_pass_count",
    "authored_invariant_design_blocked_count",
    "invariant_design_status",
    "linked_source_evidence_audit_row_ids",
    "linked_independent_replication_design_row_ids",
    "linked_authored_invariant_design_row_ids",
    "linked_component_gate_execution_rollup_row_ids",
    "required_pass_rule_result_status",
    "observed_pass_rule_result_statuses",
    "observed_replication_admission_statuses",
    "observed_invariant_admission_statuses",
    "component_closure_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_COMPONENT_GATE_EXECUTION_ROLLUP_FIELDS = [
    "policy_path_component_gate_execution_rollup_row_id",
    "protocol_component",
    "protocol_component_gate",
    "component_role",
    "adjudication_row_count",
    "source_field_count",
    "source_field_pass_count",
    "source_field_blocked_count",
    "locator_review_pass_nonpromotional_count",
    "locator_review_blocked_count",
    "promotion_grade_source_evidence_count",
    "independent_replication_design_field_count",
    "independent_replication_design_pass_count",
    "independent_replication_design_blocked_count",
    "authored_invariant_field_count",
    "authored_invariant_design_pass_count",
    "authored_invariant_design_blocked_count",
    "linked_source_extraction_result_adjudication_row_ids",
    "linked_independent_replication_design_row_ids",
    "linked_authored_invariant_design_row_ids",
    "observed_source_evidence_statuses",
    "observed_field_gate_statuses",
    "component_gate_status",
    "component_gate_execution_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_PROJECT_AUTHORED_BPS_YEAR_PROTOCOL_CONTRACT_FIELDS = [
    "project_authored_bps_year_protocol_contract_row_id",
    "component_id",
    "component_role",
    "protocol_requirement",
    "formula_classification",
    "formula_text",
    "dimensional_unit_check",
    "source_authored_input_flag",
    "project_authored_formula_flag",
    "linked_source_input_contract_row_ids",
    "linked_component_gate_execution_rollup_row_ids",
    "linked_source_extraction_result_adjudication_row_ids",
    "source_input_contract_status",
    "replication_requirement_status",
    "protocol_contract_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_PROJECT_AUTHORED_BPS_YEAR_SOURCE_INPUT_CONTRACT_FIELDS = [
    "project_authored_bps_year_source_input_contract_row_id",
    "input_id",
    "protocol_component",
    "authored_field_name",
    "input_role",
    "source_family",
    "source_artifact_path",
    "source_artifact_sha256",
    "source_table_or_code_path",
    "source_column_or_equation",
    "source_literal",
    "parsed_value",
    "parsed_unit",
    "parsed_sign",
    "source_authored_input_flag",
    "project_authored_formula_flag",
    "source_input_status",
    "allowed_use_class",
    "forbidden_use_class",
    "linked_source_extraction_result_adjudication_row_id",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_PROJECT_AUTHORED_BPS_YEAR_REPLICATION_PROTOCOL_FIELDS = [
    "project_authored_bps_year_replication_protocol_row_id",
    "replication_target_id",
    "replication_gate",
    "replication_target_artifact",
    "replication_target_row_grain",
    "formula_classification",
    "formula_text",
    "expected_output_fields",
    "implementation_1_requirement",
    "implementation_2_requirement",
    "numeric_tolerance",
    "tolerance_unit",
    "tolerance_comparison",
    "pass_status_value",
    "blocked_status_value",
    "replication_protocol_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_PROJECT_AUTHORED_BPS_YEAR_EVENT_EXPOSURE_FIELDS = [
    "project_authored_bps_year_event_exposure_row_id",
    "contract_review_row_id",
    "candidate_vector_row_id",
    "event_id",
    "event_date",
    "event_time",
    "source_sheet_vintage",
    "source_sheet_name",
    "horizon_q",
    "horizon_start",
    "horizon_end",
    "candidate_instrument_code",
    "instrument_family",
    "canonical_strip_member",
    "canonical_strip_role",
    "source_data_xlsx_path",
    "source_data_xlsx_sha256",
    "official_spec_artifact_path",
    "official_spec_artifact_sha256",
    "source_workbook_cell",
    "source_cell_value_text",
    "source_cell_value_numeric",
    "literal_na_status",
    "reference_period_start",
    "reference_period_end",
    "event_overlap_year_fraction",
    "source_input_hash_status",
    "source_cell_unit_status",
    "rate_to_price_sign_status",
    "unit_conversion_rule",
    "sign_transform_rule",
    "formula_classification",
    "formula_text",
    "formula_version",
    "scalar_pca_shortcut_status",
    "implementation_1_rate_change_bps_signed_review_only",
    "implementation_2_rate_change_bps_signed_review_only",
    "rate_change_bps_abs_diff_review_only",
    "implementation_1_component_bps_year_review_only",
    "implementation_2_component_bps_year_review_only",
    "component_bps_year_abs_diff_review_only",
    "event_canonical_component_count",
    "event_numeric_component_count",
    "event_blocked_component_count",
    "implementation_1_event_horizon_100bp_year_exposure_review_only",
    "implementation_2_event_horizon_100bp_year_exposure_review_only",
    "event_horizon_100bp_year_exposure_abs_diff_review_only",
    "numeric_tolerance",
    "tolerance_unit",
    "tolerance_comparison",
    "component_replication_status",
    "event_replication_status",
    "event_exposure_row_status",
    "exposure_admission_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "admitted_bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "empirical_threshold_claim_enabled",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_PROJECT_AUTHORED_BPS_YEAR_EXPOSURE_ADMISSION_CONSUMER_FIELDS = [
    "project_authored_bps_year_exposure_admission_consumer_row_id",
    "protocol_id",
    "decision_scope",
    "linked_source_extraction_adjudication_artifact",
    "linked_component_gate_rollup_artifact",
    "linked_protocol_contract_artifact",
    "linked_source_input_contract_artifact",
    "linked_replication_protocol_artifact",
    "linked_event_exposure_artifact",
    "linked_full_source_protocol_artifact",
    "linked_full_source_protocol_row_id",
    "source_extraction_adjudication_row_count",
    "source_extraction_nonpromotional_pass_count",
    "source_extraction_terminal_blocker_count",
    "component_gate_row_count",
    "component_gate_pass_count",
    "component_gate_blocked_count",
    "component_gate_passed_components",
    "component_gate_blocked_components",
    "protocol_contract_row_count",
    "protocol_contract_pass_count",
    "protocol_contract_blocked_count",
    "source_input_contract_row_count",
    "source_input_pass_count",
    "source_input_project_formula_allowed_count",
    "source_input_blocked_count",
    "source_input_blocked_input_ids",
    "source_input_blocked_statuses",
    "replication_protocol_row_count",
    "replication_protocol_pass_count",
    "event_exposure_row_count",
    "event_exposure_replicated_row_count",
    "event_exposure_noncanonical_guard_row_count",
    "event_exposure_protected_output_nonblank_count",
    "project_authored_formula_classification",
    "project_authored_formula_contract_status",
    "event_exposure_replication_status",
    "full_protocol_conjunction_status",
    "full_source_protocol_admission_status",
    "full_source_protocol_100bp_year_normalization_status",
    "full_source_protocol_promotion_grade_evidence_count",
    "admit_policy_path_100bp_year_exposure",
    "exposure_admission_decision",
    "promotion_boundary_status",
    "downstream_denominator_route_status",
    "hqm_re_estimation_dependency_status",
    "terminal_blocker_status",
    "remaining_blocker_components",
    "remaining_blocker_source_inputs",
    "exact_remaining_source_unit_sign_formula_blocker",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "admitted_bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "empirical_threshold_claim_enabled",
    "mpc_channel_enabled",
    "reset_calendar_enabled",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_FULL_PROTOCOL_ADMISSION_GATE_SUMMARY_FIELDS = [
    "policy_path_full_protocol_admission_gate_summary_row_id",
    "protocol_id",
    "protocol_label",
    "component_count",
    "closed_component_count",
    "blocked_component_count",
    "required_protocol_components",
    "observed_protocol_components",
    "component_closure_statuses",
    "blocked_component_ids",
    "remaining_blockers",
    "required_next_actions",
    "source_component_count",
    "source_component_closed_count",
    "source_promotion_grade_evidence_count",
    "independent_replication_component_status",
    "denominator_isolation_component_status",
    "promotion_rule_component_status",
    "full_gate_conjunction_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "non_admission_boundary",
    "linked_component_closure_rollup_row_ids",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_BUNDLE_FIELD_EXHAUSTION_DECISION_FIELDS = [
    "policy_path_source_bundle_field_exhaustion_decision_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "field_decision_class",
    "source_bundle_exhaustion_status",
    "current_source_bundle_exhausted",
    "context_only_locator_count",
    "terminal_no_hit_count",
    "promotion_grade_evidence_count",
    "field_pass_count",
    "required_evidence_or_deliverable",
    "missing_evidence_or_deliverable",
    "remaining_source_family_or_authored_deliverable",
    "linked_pass_rule_adjudication_row_ids",
    "linked_terminal_no_hit_closure_row_id",
    "linked_independent_replication_design_row_id",
    "linked_authored_invariant_design_row_id",
    "linked_protocol_component_closure_rollup_row_id",
    "linked_full_protocol_admission_gate_summary_row_id",
    "field_decision_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_BUNDLE_COMPONENT_EXHAUSTION_DECISION_FIELDS = [
    "policy_path_source_bundle_component_exhaustion_decision_row_id",
    "protocol_component",
    "protocol_component_gate",
    "component_decision_class",
    "source_bundle_exhaustion_status",
    "source_field_count",
    "context_only_field_count",
    "terminal_no_hit_field_count",
    "independent_replication_design_field_count",
    "authored_invariant_design_field_count",
    "promotion_grade_evidence_count",
    "field_pass_count",
    "component_closure_status",
    "full_protocol_gate_status",
    "linked_field_exhaustion_decision_row_ids",
    "linked_protocol_component_closure_rollup_row_id",
    "linked_full_protocol_admission_gate_summary_row_id",
    "terminal_non_admission_reason",
    "remaining_source_family_or_authored_deliverable",
    "component_decision_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_100BP_YEAR_BLOCKER_ACTION_RESOLUTION_FIELDS = [
    "policy_path_100bp_year_blocker_action_resolution_row_id",
    "protocol_component",
    "protocol_component_gate",
    "action_resolution_rank",
    "action_resolution_class",
    "protocol_component_role",
    "linked_protocol_component_closure_rollup_row_id",
    "linked_full_protocol_admission_gate_summary_row_id",
    "linked_source_bundle_component_exhaustion_decision_row_id",
    "linked_source_bundle_field_exhaustion_decision_row_ids",
    "linked_exact_source_locator_remediation_row_ids",
    "linked_exact_locator_pass_rule_adjudication_row_ids",
    "linked_terminal_no_hit_closure_row_ids",
    "linked_independent_replication_target_design_row_ids",
    "linked_authored_fail_closed_invariant_design_row_ids",
    "field_decision_count",
    "source_protocol_candidate_field_count",
    "terminal_no_hit_field_count",
    "independent_replication_design_field_count",
    "authored_invariant_design_field_count",
    "exact_locator_candidate_count",
    "exact_locator_terminal_no_hit_count",
    "pass_rule_adjudication_count",
    "terminal_no_hit_closure_count",
    "independent_replication_design_row_count",
    "authored_invariant_design_row_count",
    "promotion_grade_evidence_count",
    "field_pass_count",
    "component_closure_status",
    "component_decision_status",
    "full_gate_conjunction_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "downstream_denominator_route_triage_row_count",
    "downstream_blocked_route_count",
    "downstream_single_next_action_route_id",
    "conventional_drag_blocker_status",
    "required_next_action_class",
    "before_route_progress_requirement",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_PROTOCOL_ACTION_PACKET_FIELDS = [
    "policy_path_source_protocol_action_packet_row_id",
    "policy_path_source_bundle_field_exhaustion_decision_row_id",
    "policy_path_100bp_year_blocker_action_resolution_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "source_protocol_action_class",
    "source_protocol_action_status",
    "current_source_bundle_exhausted",
    "promotion_grade_evidence_still_worth_seeking",
    "terminal_no_hit_preserved",
    "required_evidence_or_deliverable",
    "missing_evidence_or_deliverable",
    "remaining_source_family_or_authored_deliverable",
    "required_source_families",
    "source_artifact_paths",
    "source_artifact_sha256s",
    "source_locator_requirement",
    "row_line_cell_reference_requirement",
    "extracted_value_requirement",
    "source_quote_cell_evidence_requirement",
    "promotion_grade_evidence_requirement",
    "parser_strategy",
    "candidate_locator_kinds",
    "candidate_exact_locators",
    "candidate_matched_pattern_terms",
    "terminal_no_hit_blockers",
    "linked_exact_source_locator_remediation_row_ids",
    "linked_exact_locator_pass_rule_adjudication_row_ids",
    "linked_terminal_no_hit_closure_row_id",
    "field_acceptance_test",
    "pass_status_value",
    "blocked_status_value",
    "machine_testable_pass_condition",
    "machine_testable_fail_condition",
    "promotion_grade_evidence_status",
    "field_pass_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_PROTOCOL_PASS_RULE_HARNESS_FIELDS = [
    "policy_path_source_protocol_pass_rule_harness_row_id",
    "policy_path_source_protocol_action_packet_row_id",
    "policy_path_source_bundle_field_exhaustion_decision_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "harness_task_class",
    "harness_status",
    "current_source_bundle_exhausted",
    "promotion_grade_evidence_still_worth_seeking",
    "terminal_no_hit_preserved",
    "required_source_families",
    "source_artifact_paths",
    "source_artifact_sha256s",
    "candidate_locator_count",
    "candidate_review_only_locator_count",
    "terminal_no_hit_locator_count",
    "promotion_grade_locator_count",
    "field_pass_locator_count",
    "candidate_locator_kinds",
    "candidate_exact_locators",
    "candidate_matched_pattern_terms",
    "required_locator_evidence",
    "required_row_line_cell_evidence",
    "required_extracted_value_evidence",
    "required_quote_or_cell_evidence",
    "required_promotion_grade_evidence",
    "observed_locator_coverage_status",
    "observed_value_coverage_status",
    "observed_quote_coverage_status",
    "observed_promotion_grade_status",
    "terminal_no_hit_blockers",
    "exact_pass_predicate_text",
    "exact_fail_predicate_text",
    "field_acceptance_test",
    "pass_status_value",
    "blocked_status_value",
    "executable_extraction_command_shape",
    "manual_source_acquisition_command_shape",
    "linked_exact_source_locator_remediation_row_ids",
    "linked_exact_locator_pass_rule_adjudication_row_ids",
    "linked_terminal_no_hit_closure_row_id",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_PROTOCOL_EXTRACTION_ATTEMPT_RESULTS_FIELDS = [
    "policy_path_source_protocol_extraction_attempt_result_row_id",
    "policy_path_source_protocol_pass_rule_harness_row_id",
    "policy_path_source_protocol_action_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "attempt_task_class",
    "attempt_execution_status",
    "attempt_execution_mode",
    "command_shape",
    "source_artifact_path",
    "source_artifact_sha256",
    "source_locator",
    "source_locator_kind",
    "parser_strategy",
    "parsed_value_candidate_review_only",
    "quote_or_cell_evidence_candidate_review_only",
    "pass_fail_predicate_outcome",
    "pass_status_value",
    "blocked_status_value",
    "exact_pass_predicate_text",
    "exact_fail_predicate_text",
    "candidate_context_status",
    "terminal_no_hit_status",
    "promotion_grade_evidence_status",
    "field_pass_status",
    "terminal_no_hit_preserved",
    "terminal_no_hit_blocker",
    "linked_exact_source_locator_remediation_row_id",
    "linked_exact_locator_pass_rule_adjudication_row_id",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_PROTOCOL_ATTEMPT_CLOSURE_HANDOFF_FIELDS = [
    "policy_path_source_protocol_attempt_closure_handoff_row_id",
    "policy_path_source_protocol_extraction_attempt_result_row_id",
    "policy_path_source_protocol_pass_rule_harness_row_id",
    "policy_path_source_protocol_action_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "closure_handoff_class",
    "field_closure_status",
    "source_bundle_status",
    "attempt_task_class",
    "attempt_execution_status",
    "attempt_execution_mode",
    "source_artifact_path",
    "source_artifact_sha256",
    "source_locator",
    "source_locator_kind",
    "parser_strategy",
    "parsed_value_candidate_review_only",
    "quote_or_cell_evidence_candidate_review_only",
    "pass_fail_predicate_outcome",
    "field_pass_status",
    "promotion_grade_evidence_status",
    "promotion_grade_source_family_required",
    "source_acquisition_handoff",
    "required_source_family_or_artifact",
    "authored_invariant_work_required_before_gate_move",
    "authored_invariant_dependency_status",
    "independent_replication_design_required_before_gate_move",
    "independent_replication_dependency_status",
    "protocol_gate_move_allowed",
    "protocol_gate_move_status",
    "linked_exact_source_locator_remediation_row_id",
    "linked_exact_locator_pass_rule_adjudication_row_id",
    "terminal_no_hit_preserved",
    "terminal_no_hit_blocker",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_PROMOTION_GRADE_SOURCE_FAMILY_ACQUISITION_PACKET_FIELDS = [
    "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
    "policy_path_source_protocol_attempt_closure_handoff_row_id",
    "policy_path_source_protocol_extraction_attempt_result_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "acquisition_task_class",
    "closure_handoff_class",
    "field_closure_status",
    "source_bundle_status",
    "target_source_family",
    "target_source_artifact_hint",
    "expected_evidence_type",
    "required_locator_grain",
    "search_strategy",
    "download_strategy",
    "deterministic_parser_shape",
    "evidence_acceptance_test",
    "current_source_artifact_path",
    "current_source_artifact_sha256",
    "current_source_locator",
    "current_parser_strategy",
    "current_parsed_value_candidate_review_only",
    "current_quote_or_cell_evidence_candidate_review_only",
    "current_pass_fail_predicate_outcome",
    "terminal_no_hit_preserved",
    "terminal_no_hit_blocker",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "acquisition_packet_status",
    "protocol_gate_move_allowed",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_PROMOTION_GRADE_SOURCE_FAMILY_ACQUISITION_EXECUTION_PREFLIGHT_RESULTS_FIELDS = [
    "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
    "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
    "policy_path_source_protocol_attempt_closure_handoff_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "acquisition_task_class",
    "execution_preflight_class",
    "target_source_family",
    "expected_evidence_type",
    "required_locator_grain",
    "current_source_artifact_path",
    "current_source_artifact_sha256",
    "current_source_artifact_availability_status",
    "candidate_artifact_path",
    "candidate_artifact_sha256",
    "candidate_artifact_status",
    "attempted_search_shape",
    "attempted_acquisition_command_shape",
    "attempted_download_shape",
    "parser_readiness_status",
    "deterministic_parser_shape",
    "deterministic_parser_command_shape",
    "manual_or_authenticated_acquisition_required",
    "web_or_source_author_search_required",
    "new_source_family_required",
    "source_metadata_admission_status",
    "review_candidate_admission_status",
    "scalar_shock_shortcut_status",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "acquisition_execution_status",
    "acquisition_result_status",
    "protocol_gate_move_allowed",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_FAMILY_EXECUTION_CLOSURE_SELECTION_PACKET_FIELDS = [
    "policy_path_source_family_execution_closure_selection_packet_row_id",
    "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
    "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "execution_preflight_class",
    "selected_execution_route",
    "fallback_execution_route",
    "selected_route_reason",
    "exact_next_execution_command_or_handoff",
    "target_source_family",
    "expected_evidence_type",
    "current_artifact_path",
    "current_artifact_sha256",
    "current_artifact_status",
    "parser_readiness_status",
    "deterministic_parser_command_shape",
    "source_author_search_shape",
    "manual_authenticated_handoff",
    "promotion_grade_source_evidence_acquired",
    "pass_rule_adjudicated",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "protocol_gate_move_allowed",
    "protocol_gate_move_status",
    "source_metadata_admission_status",
    "review_candidate_admission_status",
    "scalar_shock_shortcut_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_CURRENT_ARTIFACT_MANUAL_REVIEW_EXECUTION_PACKET_FIELDS = [
    "policy_path_current_artifact_manual_review_execution_packet_row_id",
    "policy_path_source_family_execution_closure_selection_packet_row_id",
    "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
    "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "selected_execution_route",
    "manual_review_execution_class",
    "manual_review_execution_status",
    "current_artifact_path",
    "current_artifact_sha256",
    "current_artifact_status",
    "parser_readiness_status",
    "current_artifact_review_command_shape",
    "source_author_search_fallback_shape",
    "parsed_review_output_path_or_no_run_blocker",
    "pass_rule_requirement",
    "promotion_grade_source_evidence_required",
    "pass_rule_adjudication_required",
    "manual_authenticated_new_source_family_blocker",
    "review_candidate_admission_status",
    "source_metadata_admission_status",
    "scalar_shock_shortcut_status",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "protocol_gate_move_allowed",
    "protocol_gate_move_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_CURRENT_ARTIFACT_MANUAL_REVIEW_RESULT_ATTEMPT_FIELDS = [
    "policy_path_current_artifact_manual_review_result_attempt_row_id",
    "policy_path_current_artifact_manual_review_execution_packet_row_id",
    "policy_path_source_family_execution_closure_selection_packet_row_id",
    "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
    "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "selected_execution_route",
    "manual_review_attempt_class",
    "manual_review_attempt_status",
    "command_attempted",
    "current_artifact_path",
    "current_artifact_sha256",
    "current_artifact_status",
    "parser_strategy",
    "parser_readiness_status",
    "parsed_review_output_path",
    "review_only_locator_candidate",
    "extracted_review_only_snippet_or_cell_candidate",
    "extracted_review_only_value_candidate",
    "pass_rule_predicate",
    "pass_fail_review_only_outcome",
    "promotion_grade_source_evidence_acquired",
    "pass_rule_adjudicated",
    "non_execution_blocker",
    "review_candidate_admission_status",
    "source_metadata_admission_status",
    "scalar_shock_shortcut_status",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "protocol_gate_move_allowed",
    "protocol_gate_move_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_AUTHOR_MANUAL_ACQUISITION_FOLLOWUP_PACKET_FIELDS = [
    "policy_path_source_author_manual_acquisition_followup_packet_row_id",
    "policy_path_current_artifact_manual_review_result_attempt_row_id",
    "policy_path_current_artifact_manual_review_execution_packet_row_id",
    "policy_path_source_family_execution_closure_selection_packet_row_id",
    "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
    "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "manual_review_attempt_class",
    "followup_task_class",
    "followup_task_status",
    "selected_followup_route",
    "target_source_family",
    "target_source_artifact_hint",
    "artifact_query_shape",
    "source_author_search_query_shape",
    "download_shape",
    "authenticated_acquisition_handoff_shape",
    "new_source_family_handoff_shape",
    "required_promotion_grade_locator_grain",
    "expected_evidence_type",
    "evidence_acceptance_test",
    "deterministic_parser_shape_after_acquisition",
    "review_only_candidate_summary",
    "review_only_candidate_admission_status",
    "source_metadata_admission_status",
    "scalar_shock_shortcut_status",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "protocol_gate_move_allowed",
    "protocol_gate_move_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_SOURCE_AUTHOR_MANUAL_ACQUISITION_EXECUTION_PREFLIGHT_RESULTS_FIELDS = [
    "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
    "policy_path_source_author_manual_acquisition_followup_packet_row_id",
    "policy_path_current_artifact_manual_review_result_attempt_row_id",
    "policy_path_current_artifact_manual_review_execution_packet_row_id",
    "policy_path_source_family_execution_closure_selection_packet_row_id",
    "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
    "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "followup_task_class",
    "acquisition_execution_preflight_class",
    "attempted_query_or_handoff",
    "target_url_or_source_family_found",
    "target_source_family",
    "attempted_download_path_or_no_download_blocker",
    "source_artifact_sha256_if_acquired",
    "required_promotion_grade_locator_grain",
    "parser_readiness_after_acquisition",
    "evidence_acceptance_test",
    "source_author_search_preflight_status",
    "download_preflight_status",
    "manual_authenticated_acquisition_status",
    "new_source_family_acquisition_status",
    "acquisition_result_status",
    "review_only_candidate_admission_status",
    "source_metadata_admission_status",
    "scalar_shock_shortcut_status",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "protocol_gate_move_allowed",
    "protocol_gate_move_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_REAL_SOURCE_AUTHOR_WEB_ACQUISITION_ATTEMPT_PACKET_FIELDS = [
    "policy_path_real_source_author_web_acquisition_attempt_packet_row_id",
    "policy_path_real_source_author_web_acquisition_attempt_manifest_row_id",
    "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
    "policy_path_source_author_manual_acquisition_followup_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "target_source_family",
    "bounded_attempt_class",
    "source_author_search_query_recorded",
    "deterministic_public_url_identified",
    "candidate_source_urls",
    "candidate_source_url_roles",
    "download_attempt_status",
    "downloaded_artifact_paths",
    "downloaded_artifact_sha256s",
    "downloaded_artifact_sizes",
    "downloaded_artifact_content_types",
    "downloaded_at_utc",
    "source_family_after_attempt",
    "attempt_result_status",
    "review_only_candidate_admission_status",
    "source_metadata_admission_status",
    "downloaded_artifact_admission_status",
    "web_search_snippet_admission_status",
    "scalar_shock_shortcut_status",
    "parser_readiness_after_attempt",
    "evidence_acceptance_test",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "protocol_gate_move_allowed",
    "protocol_gate_move_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_DOWNLOADED_ARTIFACT_LOCATOR_PARSE_ADJUDICATION_PACKET_FIELDS = [
    "policy_path_downloaded_artifact_locator_parse_adjudication_packet_row_id",
    "policy_path_downloaded_artifact_locator_parse_adjudication_manifest_row_id",
    "policy_path_real_source_author_web_acquisition_attempt_packet_row_id",
    "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
    "policy_path_source_author_manual_acquisition_followup_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "target_source_family",
    "parse_attempt_class",
    "bounded_attempt_class",
    "candidate_locator_count",
    "candidate_source_artifact_paths",
    "candidate_source_artifact_sha256s",
    "candidate_source_locations",
    "candidate_locator_grain",
    "candidate_snippet_or_cell_or_code_line",
    "candidate_parsed_value_review_only",
    "pass_rule_predicate",
    "locator_candidate_status",
    "pass_rule_adjudication_status",
    "parsed_candidate_admission_status",
    "source_page_admission_status",
    "downloaded_artifact_admission_status",
    "web_url_admission_status",
    "search_query_record_admission_status",
    "scalar_shock_shortcut_status",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "protocol_gate_move_allowed",
    "protocol_gate_move_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_LOCATOR_CANDIDATE_PASS_RULE_REVIEW_DECISION_PACKET_FIELDS = [
    "policy_path_locator_candidate_pass_rule_review_decision_packet_row_id",
    "policy_path_downloaded_artifact_locator_parse_adjudication_packet_row_id",
    "policy_path_field_specific_pass_rule_design_row_id",
    "policy_path_real_source_author_web_acquisition_attempt_packet_row_id",
    "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
    "policy_path_source_author_manual_acquisition_followup_packet_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "target_source_family",
    "parse_attempt_class",
    "pass_rule_review_class",
    "field_pass_rule_design_status",
    "source_locator_requirement",
    "row_line_cell_reference_requirement",
    "extracted_value_requirement",
    "source_quote_cell_evidence_requirement",
    "field_acceptance_test",
    "promotion_grade_evidence_requirement",
    "machine_testable_pass_condition",
    "machine_testable_fail_condition",
    "candidate_locator_count",
    "candidate_source_artifact_paths",
    "candidate_source_artifact_sha256s",
    "candidate_source_locations",
    "candidate_locator_grain",
    "candidate_snippet_or_cell_or_code_line",
    "candidate_parsed_value_review_only",
    "locator_candidate_status",
    "locator_candidate_review_status",
    "pass_rule_review_outcome",
    "pass_rule_adjudication_status",
    "field_pass_rule_status",
    "parsed_candidate_admission_status",
    "authored_invariant_sibling_gate_status",
    "independent_replication_sibling_gate_status",
    "sibling_gate_joint_status",
    "protocol_gate_move_allowed",
    "protocol_gate_move_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]

RATEWALL_POLICY_PATH_AUTHORED_FAIL_CLOSED_INVARIANT_DESIGN_FIELDS = [
    "policy_path_authored_fail_closed_invariant_design_row_id",
    "policy_path_protocol_completion_design_tranche_row_id",
    "policy_path_authored_protocol_completion_audit_row_id",
    "policy_path_source_extraction_result_row_id",
    "protocol_component",
    "protocol_component_gate",
    "authored_field_name",
    "required_output_field",
    "invariant_family",
    "invariant_role",
    "invariant_design_deliverable",
    "protected_runtime_fields",
    "protected_status_fields",
    "required_input_artifacts",
    "machine_test_target",
    "trigger_condition",
    "machine_testable_pass_condition",
    "machine_testable_fail_condition",
    "pass_status_value",
    "blocked_status_value",
    "design_completion_status",
    "implementation_status",
    "invariant_admission_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *ARCHITECTURE_GUARDRAIL_FIELDS,
]


def _false_fields() -> dict[str, str]:
    return {field: "false" for field in ARCHITECTURE_GUARDRAIL_FIELDS}


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "unknown"


def _period_family(quarter: str) -> str:
    if not quarter:
        return "unknown_period"
    year_text = quarter[:4]
    try:
        year = int(year_text)
    except ValueError:
        return "unknown_period"
    if year < 2020:
        return "pre_covid"
    if year <= 2021:
        return "covid_liquidity_regime"
    return "post_covid_high_rate"


def _decimal(value: str) -> Decimal | None:
    if value in {"", "NA", "nan", "None"}:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _range_text(values: list[Decimal]) -> tuple[str, str]:
    if not values:
        return "", ""
    return (str(min(values)), str(max(values)))


def _common_boundary() -> tuple[str, str, str]:
    return (
        "backend_architecture_lock_review_only",
        (
            "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
            "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
            "reset_calendar;policy_failure;empirical_threshold;"
            "causal_financialization"
        ),
        "backend_architecture_lock_not_empirical_promotion",
    )


def _parts(value: str) -> list[str]:
    return [part for part in value.split(";") if part]


def ratio_layer_registry_rows() -> list[dict[str, str]]:
    allowed_use, blocked_use, claim_boundary = _common_boundary()
    specs = [
        {
            "ratio_id": "RW_Y",
            "layer_id": "real_demand_wall",
            "equation_object_id": "rw_y_real_demand_offset_ratio",
            "equation_text": "RW_Y = N_Y / D_Y",
            "equation_role": "canonical_assumption_mode_annual_flow_ratio",
            "mode_class": "assumption_mode_object",
            "numerator_symbol": "N_Y",
            "denominator_symbol": "D_Y",
            "numerator_component_class": "current_demand_support",
            "denominator_component_class": "conventional_current_demand_drag",
            "allowed_numerator_channel_classes": (
                "spendable_cashflow;liquidity_support;source_gated_current_demand_offset"
            ),
            "allowed_denominator_channel_classes": (
                "fspdp_gdp_share_drag_per_admitted_100bp_year_policy_path"
            ),
            "excluded_channel_classes": "price_carry_wacc_shelter;diagnostic_only;benchmark_only",
            "denominator_basis": "canonical_100bp_year",
            "canonical_status": "canonical_assumption_mode_annual_flow",
            "source_backing_requirement": (
                "labeled_assumption_mode_N_Y_and_cited_0_00776_D_Y_per_100bp_year"
            ),
            "design_only": "false",
            "historical_reporting_status": "not_historical_empirical_estimate",
            "safe_sentence": (
                "RW_Y is the single canonical Assumption-Mode annual-flow ratio "
                "using the cited 0.00776 GDP-share denominator anchor."
            ),
            "forbidden_sentence": (
                "RateWall has an admitted Evidence-Mode historical RW_Y estimate "
                "or threshold date."
            ),
            "exact_blocker": "",
            "next_backend_action": (
                "keep_h8_and_other_ratio_objects_as_labeled_sidecars"
            ),
        },
        {
            "ratio_id": "RW_pi",
            "layer_id": "inflation_wall",
            "equation_object_id": "rw_pi_inflation_wall_design",
            "equation_text": "RW_pi = N_pi / D_pi",
            "equation_role": "inflation_wall_design_only",
            "mode_class": "paper_design_only",
            "numerator_symbol": "N_pi",
            "denominator_symbol": "D_pi",
            "numerator_component_class": "inflationary_demand_and_price_cost_sidecars",
            "denominator_component_class": "conventional_disinflationary_transmission",
            "allowed_numerator_channel_classes": "demand_offset_inflation;working_capital;carry;regulated_price",
            "allowed_denominator_channel_classes": "disinflation;expectations;exchange_rate;credit_tightening",
            "excluded_channel_classes": "rw_y_canonical_numerator_promotion",
            "denominator_basis": "not_applicable",
            "canonical_status": "design_only_blocked",
            "source_backing_requirement": "separate_inflation_mapping_and_disinflation_denominator",
            "design_only": "true",
            "historical_reporting_status": "not_historical_estimate",
            "safe_sentence": "RW_pi is a design-only inflation-wall layer.",
            "forbidden_sentence": "RateWall currently estimates an inflation-wall ratio.",
            "exact_blocker": "blocked_pending_inflation_mapping_and_source_gates",
            "next_backend_action": "build_inflation_wall_design_registry_after_rw_y_architecture_lock",
        },
        {
            "ratio_id": "RW_Y_actual_rate_sidecar",
            "layer_id": "actual_rate_sidecar",
            "equation_object_id": "actual_rate_level_wall_ratio_diagnostic",
            "equation_text": "diagnostic_ratio = N_Y_assumption_mode / D_actual_rate_level",
            "equation_role": "diagnostic_sidecar_only",
            "mode_class": "assumption_mode_object",
            "numerator_symbol": "N_Y_assumption_mode",
            "denominator_symbol": "D_actual_rate_level",
            "numerator_component_class": "assumption_mode_cashflow_support",
            "denominator_component_class": "actual_rate_level_drag_proxy",
            "allowed_numerator_channel_classes": "assumption_mode_diagnostics",
            "allowed_denominator_channel_classes": "actual_rate_level_sidecar",
            "excluded_channel_classes": "canonical_wall_hit_claim",
            "denominator_basis": "actual_rate_level_sidecar",
            "canonical_status": "sidecar_diagnostic",
            "source_backing_requirement": "explicit_sidecar_label_and_near_zero_denominator_guard",
            "design_only": "false",
            "historical_reporting_status": "sidecar_not_canonical_history",
            "safe_sentence": "Actual-rate paths are diagnostics and not canonical wall-hit evidence.",
            "forbidden_sentence": "COVID hit the canonical RateWall through a near-zero denominator.",
            "exact_blocker": "actual_rate_denominator_not_canonical_100bp_year",
            "next_backend_action": "keep_actual_rate_outputs_sidecar_labeled",
        },
        {
            "ratio_id": "TDC_sidecar",
            "layer_id": "tdc_contribution_bridge",
            "equation_object_id": "tdc_liquidity_support_sidecar",
            "equation_text": "TDC_support = base * pass_through * current_demand_conversion",
            "equation_role": "tdc_equation_design_and_assumption_mode_sidecar",
            "mode_class": "assumption_mode_object",
            "numerator_symbol": "N_Y_TDC",
            "denominator_symbol": "D_Y",
            "numerator_component_class": "tdc_liquidity_deposit_support_candidate",
            "denominator_component_class": "not_admitted_for_canonical_ratio",
            "allowed_numerator_channel_classes": "tdc_scenario_contract_review_only",
            "allowed_denominator_channel_classes": "none_until_denominator_admitted",
            "excluded_channel_classes": "double_counted_interest_or_deposit_channels",
            "denominator_basis": "dynamic_path_diagnostic",
            "canonical_status": "assumption_mode_only",
            "source_backing_requirement": "pass_through_conversion_overlap_and_regime_sign_gates",
            "design_only": "false",
            "historical_reporting_status": "tdc_sidecar_not_classifier",
            "safe_sentence": "TDC rows are scenario and diagnostic supports until conversion gates pass.",
            "forbidden_sentence": "TDC pass-through is already admitted current-demand support.",
            "exact_blocker": "missing_current_demand_conversion_and_overlap_promotion",
            "next_backend_action": "maintain_tdc_equation_variant_registry",
        },
        {
            "ratio_id": "rstar_bridge",
            "layer_id": "apparent_rstar_wedge",
            "equation_object_id": "ratewall_adjusted_stance_design",
            "equation_text": "wedge_t = RW_t * (r_t - rstar_t)",
            "equation_role": "diagnostic_interpretation_only",
            "mode_class": "paper_design_only",
            "numerator_symbol": "RW_t",
            "denominator_symbol": "not_applicable",
            "numerator_component_class": "ratewall_ratio_input_if_admitted",
            "denominator_component_class": "not_applicable",
            "allowed_numerator_channel_classes": "diagnostic_only_after_canonical_rw_y",
            "allowed_denominator_channel_classes": "not_applicable",
            "excluded_channel_classes": "true_rstar_causal_claim",
            "denominator_basis": "not_applicable",
            "canonical_status": "design_only_blocked",
            "source_backing_requirement": "canonical_RW_Y_and_source_backed_rstar_series",
            "design_only": "true",
            "historical_reporting_status": "blocked_pending_canonical_RW_Y",
            "safe_sentence": "RateWall can be used to design an apparent stance wedge diagnostic.",
            "forbidden_sentence": "RateWall proves that r-star has risen.",
            "exact_blocker": "missing_canonical_RW_Y_and_rstar_bridge_source_contract",
            "next_backend_action": "defer_rstar_bridge_until_canonical_rw_y_registry_passes",
        },
        {
            "ratio_id": "financial_retention_diagnostic",
            "layer_id": "financialization_retention",
            "equation_object_id": "financialized_retention_pressure_design",
            "equation_text": "retention_pressure = safe_asset_income_retained_outside_current_demand",
            "equation_role": "diagnostic_context_only",
            "mode_class": "paper_design_only",
            "numerator_symbol": "retained_financial_income",
            "denominator_symbol": "current_demand_conversion",
            "numerator_component_class": "financial_retention_proxy_context",
            "denominator_component_class": "not_admitted_conversion",
            "allowed_numerator_channel_classes": "diagnostic_proxy_context",
            "allowed_denominator_channel_classes": "none",
            "excluded_channel_classes": "causal_financialization_claim",
            "denominator_basis": "not_applicable",
            "canonical_status": "design_only_blocked",
            "source_backing_requirement": "beneficial_owner_recycling_and_current_demand_conversion_sources",
            "design_only": "true",
            "historical_reporting_status": "not_canonical_ratio",
            "safe_sentence": "Financialization rows can describe retention context, not causal proof.",
            "forbidden_sentence": "RateWall proves financialization caused policy failure.",
            "exact_blocker": "missing_causal_design_and_current_demand_conversion",
            "next_backend_action": "keep_financialization_diagnostic_noncausal",
        },
    ]
    rows = []
    for idx, spec in enumerate(specs, start=1):
        rows.append(
            {
                "ratio_layer_registry_row_id": f"ratio_layer_registry::{idx:04d}",
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **spec,
                **_false_fields(),
            }
        )
    return rows


def estimation_target_registry_rows() -> list[dict[str, str]]:
    allowed_use, blocked_use, claim_boundary = _common_boundary()
    specs = [
        (
            "conventional_drag_denominator",
            "Conventional current-demand drag denominator",
            "rw_y_denominator",
            "conventional_drag",
            "denominator_for_RW_Y",
            "- delta current demand as GDP share per admitted 100bp-year tightening",
            "true",
            "admissible_estimation_target",
            "monetary_policy_path",
            "admitted_100bp_year",
            "GDP-share current-demand drag per 100bp-year",
            "BEA/FRED/MIR/GK/FRB-US/local-LP-after-gates",
            "policy_path_normalization;current_demand_mapping;uncertainty;replication",
            "ratewall_conventional_drag_promotion_contract_checklist.csv",
            "blocked_pending_source_gate",
            "blocked_missing_100bp_year_policy_path",
            "false",
            "false",
            "all_eight_conventional_drag_gates_pass",
            "D_Y is the key empirical target but remains blocked.",
            "The conventional drag denominator has been calibrated.",
            "missing_100bp_year_policy_path_and_current_demand_drag_promotion",
            "execute_policy_path_extraction_packet_then_denominator_target_registry",
        ),
        (
            "policy_path_bps_year",
            "Policy-path bps-year exposure",
            "policy_path_normalization",
            "policy_path",
            "normalization_input_for_D_Y",
            "source-backed policy path integral in bps-years",
            "true",
            "blocked_object",
            "SF Fed/USMPD/MIR/GK source shock candidates",
            "blocked_pending_protocol",
            "bps-years",
            "SF Fed;USMPD;CME;MIR;GK",
            "unit;sign;horizon_grid;back_transform;integral;replication",
            "ratewall_policy_path_field_evidence_resolution_queue.csv",
            "blocked_pending_source_gate",
            "blocked_no_admitted_bps_year_policy_path",
            "false",
            "false",
            "source_backed_policy_path_protocol_pass",
            "The bps-year path is a required normalization target.",
            "Scalar shocks are equivalent to 100bp-year exposure.",
            "field_resolution_queue_not_executed",
            "execute_policy_path_source_extraction_task_packet",
        ),
        (
            "tdc_pass_through",
            "TDC deposit pass-through",
            "tdc_support",
            "tdc",
            "assumption_mode_parameter_and_diagnostic",
            "deposit-flow pass-through per TDC dollar",
            "false",
            "assumption_mode_object",
            "TDC flow/regime diagnostics",
            "source_unit_sibling_estimate_not_final_demand",
            "dollars deposits per dollar TDC",
            "ea-tdc;tdcest",
            "current-demand conversion and overlap gates before RW_Y use",
            "ratewall_tdc_deposit_pass_through_scenario_contract.csv",
            "source_backed_context",
            "blocked_missing_current_demand_conversion",
            "false",
            "true",
            "tdc_conversion_overlap_and_trigger_validation_pass",
            "TDC pass-through is useful for scenario review.",
            "TDC pass-through is admitted current-demand support.",
            "missing_tdc_current_demand_conversion_and_trigger_validation",
            "use_tdc_equation_variant_registry_before_scenario_promotion",
        ),
        (
            "frbus_benchmark",
            "FRB/US conventional-drag benchmark",
            "model_benchmark",
            "conventional_drag_benchmark",
            "benchmark_only",
            "model response to specified policy scenario",
            "false",
            "benchmark_only",
            "FRB/US model shock path",
            "model_scenario_not_empirical_denominator",
            "model output units",
            "Federal Reserve FRB/US",
            "benchmark role; uncertainty/promotion rule before any prior narrowing",
            "ratewall_frbus_benchmark_output_slot_extension_review.csv",
            "benchmark_only",
            "blocked_benchmark_not_empirical_calibration",
            "true",
            "false",
            "separate_model_benchmark_promotion_rule",
            "FRB/US can benchmark signs and magnitudes.",
            "FRB/US output slots admit the RateWall denominator.",
            "benchmark_only_no_empirical_uncertainty_or_promotion",
            "keep_frbus_as_benchmark_context",
        ),
        (
            "rw_pi_inflation_wall",
            "Inflation-wall ratio",
            "inflation_wall",
            "inflation_wall",
            "paper_design_layer",
            "inflationary sidecar over conventional disinflation",
            "false",
            "paper_design_only",
            "not_yet_defined",
            "not_applicable",
            "not_admitted",
            "future_sources_required",
            "inflation mapping and disinflation denominator",
            "",
            "design_only_blocked",
            "blocked_pending_inflation_mapping",
            "false",
            "false",
            "inflation_wall_source_gate_stack",
            "RW_pi is an optional design layer.",
            "The backend estimates RW_pi.",
            "missing_inflation_wall_mapping_and_sources",
            "defer_until_rw_y_architecture_is_locked",
        ),
        (
            "rstar_bridge",
            "Apparent r-star wedge bridge",
            "rstar_diagnostic",
            "rstar_bridge",
            "diagnostic_only",
            "RW-adjusted stance wedge",
            "false",
            "paper_design_only",
            "canonical RW_Y and r-star source",
            "blocked_pending_canonical_RW_Y",
            "percentage points",
            "future r-star source selection",
            "canonical RW_Y and source-backed r-star series",
            "",
            "design_only_blocked",
            "blocked_pending_canonical_RW_Y",
            "false",
            "false",
            "canonical_rw_y_and_rstar_contract_pass",
            "The r-star bridge is interpretive and diagnostic.",
            "RateWall proves r-star changed.",
            "missing_canonical_RW_Y",
            "defer_rstar_diagnostic",
        ),
    ]
    rows = []
    for idx, spec in enumerate(specs, start=1):
        (
            object_id,
            object_label,
            object_family,
            target_family,
            theory_role,
            estimation_target,
            preferred_canonical_target,
            mode_class,
            shock_family,
            normalization_basis,
            required_unit,
            source_family,
            source_backing_requirement,
            current_artifact_paths,
            current_status,
            admissibility_status,
            benchmark_only,
            assumption_mode_only,
            promotion_gate,
            safe_sentence,
            forbidden_sentence,
            exact_blocker,
            next_backend_action,
        ) = spec
        rows.append(
            {
                "estimation_target_registry_row_id": f"estimation_target_registry::{idx:04d}",
                "object_id": object_id,
                "object_label": object_label,
                "object_family": object_family,
                "target_family": target_family,
                "theory_role": theory_role,
                "estimation_target": estimation_target,
                "preferred_canonical_target": preferred_canonical_target,
                "mode_class": mode_class,
                "shock_family": shock_family,
                "normalization_basis": normalization_basis,
                "required_unit": required_unit,
                "source_family": source_family,
                "source_backing_requirement": source_backing_requirement,
                "current_artifact_paths": current_artifact_paths,
                "current_status": current_status,
                "admissibility_status": admissibility_status,
                "benchmark_only": benchmark_only,
                "assumption_mode_only": assumption_mode_only,
                "promotion_gate": promotion_gate,
                "safe_sentence": safe_sentence,
                "forbidden_sentence": forbidden_sentence,
                "exact_blocker": exact_blocker,
                "next_backend_action": next_backend_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def conventional_drag_empirical_target_registry_rows(
    *,
    policy_path_full_protocol_admission_gate_summary_rows: list[dict[str, str]],
    conventional_drag_fspdp_component_share_panel_rows: list[dict[str, str]],
    conventional_drag_fspdp_component_decomposition_bridge_rows: list[dict[str, str]],
    mir_component_aggregation_review_rows: list[dict[str, str]],
    mir_component_source_variant_review_rows: list[dict[str, str]],
    conventional_drag_local_lp_admission_audit_rows: list[dict[str, str]],
    frbus_conventional_drag_benchmark_protocol_rows: list[dict[str, str]],
    frbus_benchmark_output_slot_extension_review_rows: list[dict[str, str]],
    conventional_drag_source_unit_aggregation_blocker_bridge_rows: list[
        dict[str, str]
    ],
    conventional_drag_mirgk_targeted_gap_source_followup_rows: list[dict[str, str]],
    conventional_drag_promotion_contract_checklist_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "conventional_drag_empirical_target_registry_review_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = (
        "conventional_drag_empirical_target_registry_not_denominator_calibration"
    )
    target_quantity = (
        "D_Y = - delta current demand as percent of GDP per admitted "
        "100bp-year tightening exposure"
    )
    policy_path_status = (
        policy_path_full_protocol_admission_gate_summary_rows[0].get(
            "policy_path_100bp_year_normalization_status", ""
        )
        if policy_path_full_protocol_admission_gate_summary_rows
        else "blocked_missing_policy_path_full_protocol_admission_summary"
    )
    source_bridge_by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    checklist_by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in conventional_drag_source_unit_aggregation_blocker_bridge_rows:
        source_bridge_by_family[row.get("source_route_family", "")].append(row)
    for row in conventional_drag_promotion_contract_checklist_rows:
        checklist_by_family[row.get("source_route_family", "")].append(row)

    mir_direct_rows = [
        row
        for row in mir_component_aggregation_review_rows
        if row.get("component_evidence_class")
        == "direct_pce_subcomponent_quantity_evidence"
    ]
    mir_proxy_rows = [
        row
        for row in mir_component_aggregation_review_rows
        if row.get("component_evidence_class") == "residential_investment_activity_proxy"
    ]
    houst_permit_variant_rows = [
        row
        for row in mir_component_source_variant_review_rows
        if row.get("source_outcome_label") in {"HOUST", "PERMIT"}
    ]
    fspdp_component_count = len(
        {
            row.get("component_id")
            for row in conventional_drag_fspdp_component_share_panel_rows
            if row.get("component_id")
        }
    )
    fspdp_decomposition_component_count = len(
        {
            row.get("decomposition_component_id")
            for row in conventional_drag_fspdp_component_decomposition_bridge_rows
            if row.get("decomposition_component_id")
        }
    )

    def table_counts(items: list[tuple[str, int]]) -> str:
        return ";".join(f"{name}={count}" for name, count in items)

    specs = [
        {
            "route_id": "canonical_fspdp_current_demand_drag_100bp_year",
            "route_family": "canonical_target_definition",
            "route_label": "Preferred FSPDP current-demand drag target",
            "route_role": "preferred_canonical_target_definition",
            "target_id": "D_Y_fspdp_current_demand_drag_100bp_year",
            "target_label": "FSPDP current-demand drag per 100bp-year",
            "target_outcome_id": "fspdp_gdp_share",
            "target_horizon_scope": "4q_or_8q_integrated_after_protocol_admission",
            "preferred_canonical_target": "true",
            "benchmark_only": "false",
            "research_parameterization_only": "false",
            "proxy_only": "false",
            "source_backed_context_only": "false",
            "source_families": "BEA/FRED FSPDP components;policy-path protocol;admitted response design",
            "linked_evidence_tables": (
                "ratewall_policy_path_full_protocol_admission_gate_summary.csv;"
                "ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv;"
                "ratewall_conventional_drag_promotion_contract_checklist.csv"
            ),
            "linked_evidence_row_counts": table_counts(
                [
                    (
                        "ratewall_policy_path_full_protocol_admission_gate_summary.csv",
                        len(policy_path_full_protocol_admission_gate_summary_rows),
                    ),
                    (
                        "ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv",
                        len(conventional_drag_fspdp_component_decomposition_bridge_rows),
                    ),
                    (
                        "ratewall_conventional_drag_promotion_contract_checklist.csv",
                        len(conventional_drag_promotion_contract_checklist_rows),
                    ),
                ]
            ),
            "route_evidence_row_count": str(
                len(conventional_drag_fspdp_component_decomposition_bridge_rows)
                + len(conventional_drag_promotion_contract_checklist_rows)
            ),
            "policy_path_normalization_status": (
                "blocked_canonical_rw_y_missing_scale_grade_denominator_after_nonpromotional_policy_path_protocol"
            ),
            "source_unit_status": "blocked_no_admitted_response_source_unit_for_target",
            "target_horizon_reconciliation_status": "blocked_no_admitted_target_horizon_integral",
            "current_demand_mapping_status": (
                "pass_fspdp_component_target_defined_review_only"
            ),
            "component_share_status": (
                "pass_source_backed_fspdp_component_share_context_review_only"
            ),
            "component_coverage_status": (
                "blocked_no_admitted_complete_fspdp_response_coverage"
            ),
            "proxy_bridge_status": "not_applicable_preferred_target_not_proxy",
            "gdp_share_conversion_status": (
                "blocked_no_admitted_current_demand_response_to_gdp_share_conversion"
            ),
            "uncertainty_status": "blocked_no_admitted_denominator_uncertainty_interval",
            "replication_status": "blocked_no_independent_denominator_replication",
            "robustness_status": "blocked_no_transport_robustness_promotion",
            "promotion_rule_status": "blocked_no_denominator_promotion_rule_pass",
            "admission_status": "blocked_preferred_target_missing_required_gate_stack",
            "exact_blocker": (
                "Preferred FSPDP target is defined and the project-authored 100bp-year "
                "policy-path protocol is usable as nonpromotional accounting, but the "
                "canonical route still lacks a scale-grade denominator object, "
                "GDP-share conversion/admission, uncertainty, independent "
                "replication, robustness, promotion, and a timing-aligned numerator."
            ),
            "next_backend_action": "execute_conventional_drag_route_pruning_and_denominator_design_gate",
            "safe_sentence": (
                "The preferred denominator target is FSPDP current-demand drag "
                "per 100bp-year, but no canonical value is admitted and bounded "
                "noncanonical sidecars do not open RW_Y."
            ),
            "forbidden_sentence": "RateWall has an admitted FSPDP denominator estimate.",
        },
        {
            "route_id": "official_fspdp_component_share_context",
            "route_family": "official_component_share_context",
            "route_label": "Official FSPDP component share scaffold",
            "route_role": "source_backed_context_only",
            "target_id": "fspdp_component_share_context",
            "target_label": "FSPDP component weights for future aggregation",
            "target_outcome_id": "fspdp_gdp_share",
            "target_horizon_scope": "share_windows_only",
            "preferred_canonical_target": "false",
            "benchmark_only": "false",
            "research_parameterization_only": "false",
            "proxy_only": "false",
            "source_backed_context_only": "true",
            "source_families": "BEA/FRED NIPA component shares",
            "linked_evidence_tables": (
                "ratewall_conventional_drag_fspdp_component_share_panel.csv;"
                "ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv"
            ),
            "linked_evidence_row_counts": table_counts(
                [
                    (
                        "ratewall_conventional_drag_fspdp_component_share_panel.csv",
                        len(conventional_drag_fspdp_component_share_panel_rows),
                    ),
                    (
                        "ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv",
                        len(conventional_drag_fspdp_component_decomposition_bridge_rows),
                    ),
                ]
            ),
            "route_evidence_row_count": str(
                len(conventional_drag_fspdp_component_share_panel_rows)
                + len(conventional_drag_fspdp_component_decomposition_bridge_rows)
            ),
            "policy_path_normalization_status": (
                "blocked_share_context_not_denominator_even_after_nonpromotional_"
                "policy_path_protocol"
            ),
            "source_unit_status": "not_applicable_share_context_only",
            "target_horizon_reconciliation_status": "not_applicable_share_context_only",
            "current_demand_mapping_status": (
                "pass_official_fspdp_component_accounting_context_review_only"
            ),
            "component_share_status": (
                "pass_source_backed_component_share_panel_review_only"
            ),
            "component_coverage_status": (
                "pass_all_required_fspdp_component_share_families_present_review_only"
            ),
            "proxy_bridge_status": "not_applicable_share_context_only",
            "gdp_share_conversion_status": (
                "blocked_share_context_not_response_conversion"
            ),
            "uncertainty_status": "blocked_no_response_uncertainty_for_share_context",
            "replication_status": "blocked_no_denominator_replication_for_share_context",
            "robustness_status": "blocked_share_context_not_transport_robustness",
            "promotion_rule_status": "blocked_share_context_not_denominator_promotion",
            "admission_status": "source_backed_context_only_not_denominator_estimate",
            "exact_blocker": (
                f"{fspdp_component_count} panel component ids and "
                f"{fspdp_decomposition_component_count} decomposition component ids "
                "are present, but component shares remain context-only weights, not "
                "current-demand drag estimates or denominator evidence."
            ),
            "next_backend_action": "use_shares_only_after_admitted_component_irfs_and_policy_path_exist",
            "safe_sentence": "FSPDP component shares are source-backed context.",
            "forbidden_sentence": "FSPDP component shares are denominator drag estimates.",
        },
        {
            "route_id": "mir_gk_research_parameterization_route",
            "route_family": "mir_gk_research_parameterization",
            "route_label": "MIR/GK component research route",
            "route_role": "research_parameterization_only",
            "target_id": "mir_gk_component_route_to_fspdp",
            "target_label": "Research component IRF route to FSPDP",
            "target_outcome_id": "fspdp_gdp_share",
            "target_horizon_scope": "4q_8q_12q_review_only",
            "preferred_canonical_target": "false",
            "benchmark_only": "false",
            "research_parameterization_only": "true",
            "proxy_only": "false",
            "source_backed_context_only": "false",
            "source_families": "Miranda-Agrippino/Ricco;Gertler/Karadi;BEA/FRED",
            "linked_evidence_tables": (
                "ratewall_conventional_drag_research_mir_component_aggregation_normalization_review.csv;"
                "ratewall_conventional_drag_mirgk_targeted_gap_source_followup.csv;"
                "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv"
            ),
            "linked_evidence_row_counts": table_counts(
                [
                    (
                        "ratewall_conventional_drag_research_mir_component_aggregation_normalization_review.csv",
                        len(mir_component_aggregation_review_rows),
                    ),
                    (
                        "ratewall_conventional_drag_mirgk_targeted_gap_source_followup.csv",
                        len(conventional_drag_mirgk_targeted_gap_source_followup_rows),
                    ),
                    (
                        "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv",
                        len(
                            source_bridge_by_family[
                                "mir_4q8q_source_unit_component_route"
                            ]
                        )
                        + len(source_bridge_by_family["research_side_action_plan_route"]),
                    ),
                ]
            ),
            "route_evidence_row_count": str(
                len(mir_component_aggregation_review_rows)
                + len(conventional_drag_mirgk_targeted_gap_source_followup_rows)
            ),
            "policy_path_normalization_status": policy_path_status,
            "source_unit_status": "blocked_source_irf_units_unconverted_review_only",
            "target_horizon_reconciliation_status": (
                "blocked_source_horizon_index_not_promoted_to_target_quarter_horizon"
            ),
            "current_demand_mapping_status": (
                "blocked_partial_component_route_not_complete_fspdp_mapping"
            ),
            "component_share_status": "blocked_component_weights_not_admitted_for_irf_use",
            "component_coverage_status": (
                "blocked_incomplete_pce_services_and_private_fixed_investment_coverage"
            ),
            "proxy_bridge_status": "blocked_proxy_rows_separated_not_aggregable",
            "gdp_share_conversion_status": (
                "blocked_component_irfs_not_converted_to_fspdp_gdp_share_drag"
            ),
            "uncertainty_status": "blocked_component_intervals_not_aggregate_uncertainty",
            "replication_status": "blocked_no_independent_mir_gk_denominator_replication",
            "robustness_status": "blocked_no_research_route_transport_robustness",
            "promotion_rule_status": "blocked_research_parameterization_not_promotion",
            "admission_status": "research_parameterization_only_not_denominator",
            "exact_blocker": (
                f"{len(mir_direct_rows)} direct PCE component rows are reviewed, "
                "but unit, horizon, component coverage, policy-path, replication, "
                "robustness, and promotion gates remain blocked."
            ),
            "next_backend_action": "prune_mir_gk_routes_to_missing_direct_fspdp_components",
            "safe_sentence": "MIR/GK rows guide denominator research priorities only.",
            "forbidden_sentence": "MIR/GK parsed IRFs admit the denominator.",
        },
        {
            "route_id": "houst_permit_residential_activity_proxy_route",
            "route_family": "housing_activity_proxy",
            "route_label": "HOUST/PERMIT residential activity proxy route",
            "route_role": "proxy_only_blocked",
            "target_id": "housing_proxy_to_private_residential_fixed_investment",
            "target_label": "Housing starts and permits proxy bridge",
            "target_outcome_id": "fspdp_gdp_share",
            "target_horizon_scope": "4q_8q_12q_review_only",
            "preferred_canonical_target": "false",
            "benchmark_only": "false",
            "research_parameterization_only": "true",
            "proxy_only": "true",
            "source_backed_context_only": "false",
            "source_families": "MIR HOUST/PERMIT;Census/HUD;BEA private fixed investment",
            "linked_evidence_tables": (
                "ratewall_conventional_drag_research_mir_component_aggregation_normalization_review.csv;"
                "ratewall_conventional_drag_research_mir_component_source_variant_review.csv"
            ),
            "linked_evidence_row_counts": table_counts(
                [
                    (
                        "mir_proxy_component_rows",
                        len(mir_proxy_rows),
                    ),
                    (
                        "houst_permit_source_variant_rows",
                        len(houst_permit_variant_rows),
                    ),
                ]
            ),
            "route_evidence_row_count": str(
                len(mir_proxy_rows) + len(houst_permit_variant_rows)
            ),
            "policy_path_normalization_status": policy_path_status,
            "source_unit_status": "blocked_housing_units_not_fixed_investment_expenditure_units",
            "target_horizon_reconciliation_status": (
                "blocked_housing_proxy_horizon_not_promoted"
            ),
            "current_demand_mapping_status": (
                "blocked_housing_activity_proxy_not_fspdp_component_response"
            ),
            "component_share_status": (
                "blocked_missing_residential_fixed_investment_or_proxy_weight"
            ),
            "component_coverage_status": (
                "blocked_housing_activity_proxy_not_complete_private_fixed_investment"
            ),
            "proxy_bridge_status": (
                "blocked_no_source_backed_houst_permit_to_residential_fixed_investment_bridge"
            ),
            "gdp_share_conversion_status": (
                "blocked_housing_proxy_not_convertible_to_gdp_share_drag"
            ),
            "uncertainty_status": "blocked_proxy_conflict_not_aggregate_uncertainty",
            "replication_status": "blocked_no_proxy_bridge_replication",
            "robustness_status": "blocked_no_proxy_transport_robustness",
            "promotion_rule_status": "blocked_proxy_route_not_promotion_grade",
            "admission_status": "proxy_only_blocked_not_denominator",
            "exact_blocker": (
                f"{len(mir_proxy_rows)} HOUST/PERMIT interpreted rows and "
                f"{len(houst_permit_variant_rows)} supporting variants remain "
                "activity proxies with unresolved bridge and variant conflicts."
            ),
            "next_backend_action": "keep_houst_permit_as_channel_diagnostic_unless_proxy_bridge_is_sourced",
            "safe_sentence": "HOUST/PERMIT are housing activity proxies.",
            "forbidden_sentence": "HOUST/PERMIT are direct private fixed investment drag.",
        },
        {
            "route_id": "frbus_official_model_benchmark_route",
            "route_family": "frbus_benchmark",
            "route_label": "FRB/US official-model benchmark route",
            "route_role": "benchmark_only",
            "target_id": "frbus_model_benchmark_to_denominator_context",
            "target_label": "FRB/US benchmark comparison",
            "target_outcome_id": "real_gdp_or_component_benchmark",
            "target_horizon_scope": "4q_8q_12q_benchmark_review",
            "preferred_canonical_target": "false",
            "benchmark_only": "true",
            "research_parameterization_only": "false",
            "proxy_only": "false",
            "source_backed_context_only": "false",
            "source_families": "Federal Reserve FRB/US public model package",
            "linked_evidence_tables": (
                "ratewall_frbus_conventional_drag_benchmark_protocol.csv;"
                "ratewall_frbus_benchmark_output_slot_extension_review.csv;"
                "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv"
            ),
            "linked_evidence_row_counts": table_counts(
                [
                    (
                        "ratewall_frbus_conventional_drag_benchmark_protocol.csv",
                        len(frbus_conventional_drag_benchmark_protocol_rows),
                    ),
                    (
                        "ratewall_frbus_benchmark_output_slot_extension_review.csv",
                        len(frbus_benchmark_output_slot_extension_review_rows),
                    ),
                    (
                        "frbus_source_unit_bridge_rows",
                        len(
                            source_bridge_by_family[
                                "frbus_benchmark_output_slot_extension_route"
                            ]
                        ),
                    ),
                ]
            ),
            "route_evidence_row_count": str(
                len(frbus_conventional_drag_benchmark_protocol_rows)
                + len(frbus_benchmark_output_slot_extension_review_rows)
            ),
            "policy_path_normalization_status": (
                "blocked_frbus_benchmark_only_even_after_normalized_100bp_year_"
                "review"
            ),
            "source_unit_status": "blocked_frbus_model_units_not_empirical_source_units",
            "target_horizon_reconciliation_status": (
                "pass_model_horizon_slots_available_benchmark_only"
            ),
            "current_demand_mapping_status": (
                "blocked_model_benchmark_not_current_demand_estimate"
            ),
            "component_share_status": "blocked_benchmark_not_component_weighted_estimate",
            "component_coverage_status": "blocked_benchmark_slots_not_complete_denominator",
            "proxy_bridge_status": "not_applicable_model_benchmark",
            "gdp_share_conversion_status": (
                "blocked_model_output_not_admitted_gdp_share_drag"
            ),
            "uncertainty_status": "blocked_no_empirical_uncertainty_for_benchmark",
            "replication_status": "blocked_no_independent_denominator_replication",
            "robustness_status": "blocked_benchmark_transport_not_admitted",
            "promotion_rule_status": "blocked_frbus_benchmark_not_promotion_rule",
            "admission_status": "benchmark_only_not_empirical_denominator",
            "exact_blocker": (
                "FRB/US runtime/package access and a normalized 100bp-year "
                "component-mapped FSPDP proxy benchmark now exist, but the route "
                "remains benchmark-only: model outputs are not empirical denominator "
                "evidence, do not supply empirical uncertainty, and do not calibrate "
                "canonical RW_Y."
            ),
            "next_backend_action": (
                "keep_frbus_benchmark_review_only_and_compare_shape_not_level_"
                "against_bounded_h8_interval"
            ),
            "safe_sentence": (
                "FRB/US benchmarks can compare sign, horizon shape, and model-scale "
                "component-mapped private-demand responses without admitting D_Y."
            ),
            "forbidden_sentence": "FRB/US benchmark slots admit D_Y.",
        },
        {
            "route_id": "local_lp_proxy_svar_diagnostic_route",
            "route_family": "local_lp_proxy_svar_diagnostic",
            "route_label": "Local LP/proxy-SVAR diagnostic route",
            "route_role": "diagnostic_only",
            "target_id": "local_lp_fspdp_response_design",
            "target_label": "Local LP current-demand response design",
            "target_outcome_id": "fspdp_gdp_share",
            "target_horizon_scope": "registered_lp_horizons_review_only",
            "preferred_canonical_target": "false",
            "benchmark_only": "false",
            "research_parameterization_only": "false",
            "proxy_only": "false",
            "source_backed_context_only": "false",
            "source_families": "local macro panel;policy shock candidates",
            "linked_evidence_tables": "ratewall_conventional_drag_local_lp_admission_audit.csv",
            "linked_evidence_row_counts": table_counts(
                [
                    (
                        "ratewall_conventional_drag_local_lp_admission_audit.csv",
                        len(conventional_drag_local_lp_admission_audit_rows),
                    )
                ]
            ),
            "route_evidence_row_count": str(
                len(conventional_drag_local_lp_admission_audit_rows)
            ),
            "policy_path_normalization_status": policy_path_status,
            "source_unit_status": "blocked_lp_source_units_not_promoted",
            "target_horizon_reconciliation_status": "blocked_lp_design_not_formally_admitted",
            "current_demand_mapping_status": "pass_source_backed_panel_available_not_drag_estimate",
            "component_share_status": "not_applicable_aggregate_lp_route",
            "component_coverage_status": "blocked_lp_outcome_target_not_promoted",
            "proxy_bridge_status": "not_applicable_aggregate_lp_route",
            "gdp_share_conversion_status": "blocked_lp_estimate_not_admitted_gdp_share_drag",
            "uncertainty_status": "blocked_uncertainty_not_admitted",
            "replication_status": "blocked_replication_not_admitted",
            "robustness_status": "blocked_sample_and_shock_family_robustness_not_admitted",
            "promotion_rule_status": "blocked_ledger_promotion_not_admitted",
            "admission_status": "diagnostic_only_not_denominator",
            "exact_blocker": (
                "Local LP diagnostics exist, but the admission audit still "
                "blocks policy-path normalization, uncertainty, replication, "
                "robustness, and promotion."
            ),
            "next_backend_action": "register_nonpromotional_denominator_estimates_only_after_design_gate",
            "safe_sentence": "Local LP rows are diagnostic until the design gate passes.",
            "forbidden_sentence": "Local LP diagnostics have calibrated D_Y.",
        },
    ]

    rows: list[dict[str, str]] = []
    for idx, spec in enumerate(specs, start=1):
        rows.append(
            {
                "conventional_drag_empirical_target_registry_row_id": (
                    f"conventional_drag_empirical_target_registry::{idx:04d}"
                ),
                "target_quantity": target_quantity,
                "candidate_bps_year_exposure": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **spec,
                **_false_fields(),
            }
        )
    return rows


def conventional_drag_route_pruning_audit_rows(
    *,
    conventional_drag_empirical_target_registry_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "conventional_drag_route_pruning_review_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = "conventional_drag_route_pruning_not_denominator_calibration"
    required_gate_stack = (
        "policy_path_100bp_year_normalization;current_demand_mapping;"
        "gdp_share_conversion;uncertainty;replication;robustness;promotion_rule"
    )

    def prune(row: dict[str, str]) -> tuple[str, str, str, str, str]:
        route_id = row.get("route_id", "")
        if row.get("preferred_canonical_target") == "true":
            return (
                "retain_preferred_fspdp_target_but_block_admission",
                "blocked_preferred_target_requires_full_gate_stack",
                "preferred_denominator_target_definition_only",
                "benchmark_only;proxy_only;research_only;diagnostic_only",
                "execute_response_design_gate_before_denominator_estimation",
            )
        if row.get("source_backed_context_only") == "true":
            return (
                "retain_as_component_share_context_only",
                "blocked_context_only_not_response_route",
                "source_backed_component_share_context",
                "admitted_denominator;research_parameterization;benchmark_only",
                "use_component_shares_only_after_admitted_response_route_exists",
            )
        if row.get("benchmark_only") == "true":
            return (
                "prune_to_benchmark_only",
                "blocked_benchmark_only_not_empirical_denominator",
                "official_model_benchmark_context",
                "admitted_denominator;prior_narrowing;main_ratio",
                "keep_frbus_for_benchmark_comparison_only",
            )
        if row.get("proxy_only") == "true":
            return (
                "prune_to_proxy_only_diagnostic",
                "blocked_proxy_only_not_direct_fspdp_response",
                "housing_activity_proxy_diagnostic",
                "admitted_denominator;direct_pfi_component;main_ratio",
                "source_bridge_or_keep_housing_proxy_out_of_denominator",
            )
        if row.get("research_parameterization_only") == "true":
            return (
                "prune_to_research_parameterization_only",
                "blocked_research_route_not_promotion_grade",
                "research_parameterization_route",
                "admitted_denominator;prior_narrowing;main_ratio",
                "fill_missing_source_unit_horizon_policy_path_and_replication_gates",
            )
        if route_id == "local_lp_proxy_svar_diagnostic_route":
            return (
                "retain_as_diagnostic_response_design_only",
                "blocked_local_lp_design_not_formally_admitted",
                "diagnostic_response_design",
                "admitted_denominator;Evidence_Mode;prior_narrowing",
                "register_nonpromotional_estimates_only_after_design_gate",
            )
        return (
            "blocked_unclassified_route",
            "blocked_route_requires_manual_classification",
            "blocked_object",
            "admitted_denominator;main_ratio",
            "classify_route_before_any_denominator_work",
        )

    rows: list[dict[str, str]] = []
    for idx, row in enumerate(conventional_drag_empirical_target_registry_rows, start=1):
        (
            pruning_decision,
            pruning_status,
            retained_backend_role,
            excluded_from_roles,
            next_action,
        ) = prune(row)
        failed_gate_stack = ";".join(
            gate
            for gate, status in [
                (
                    "policy_path_100bp_year_normalization",
                    row.get("policy_path_normalization_status", ""),
                ),
                ("current_demand_mapping", row.get("current_demand_mapping_status", "")),
                ("gdp_share_conversion", row.get("gdp_share_conversion_status", "")),
                ("uncertainty", row.get("uncertainty_status", "")),
                ("replication", row.get("replication_status", "")),
                ("robustness", row.get("robustness_status", "")),
                ("promotion_rule", row.get("promotion_rule_status", "")),
            ]
            if status.startswith("blocked")
        )
        rows.append(
            {
                "conventional_drag_route_pruning_audit_row_id": (
                    f"conventional_drag_route_pruning_audit::{idx:04d}"
                ),
                "conventional_drag_empirical_target_registry_row_id": row.get(
                    "conventional_drag_empirical_target_registry_row_id", ""
                ),
                "route_id": row.get("route_id", ""),
                "route_family": row.get("route_family", ""),
                "route_label": row.get("route_label", ""),
                "route_role": row.get("route_role", ""),
                "target_id": row.get("target_id", ""),
                "target_label": row.get("target_label", ""),
                "target_quantity": row.get("target_quantity", ""),
                "target_outcome_id": row.get("target_outcome_id", ""),
                "preferred_canonical_target": row.get("preferred_canonical_target", ""),
                "benchmark_only": row.get("benchmark_only", ""),
                "research_parameterization_only": row.get(
                    "research_parameterization_only", ""
                ),
                "proxy_only": row.get("proxy_only", ""),
                "source_backed_context_only": row.get("source_backed_context_only", ""),
                "pruning_decision": pruning_decision,
                "pruning_status": pruning_status,
                "retained_backend_role": retained_backend_role,
                "excluded_from_roles": excluded_from_roles,
                "required_gate_stack": required_gate_stack,
                "failed_gate_stack": failed_gate_stack,
                "route_evidence_row_count": row.get("route_evidence_row_count", ""),
                "linked_evidence_tables": row.get("linked_evidence_tables", ""),
                "policy_path_normalization_status": row.get(
                    "policy_path_normalization_status", ""
                ),
                "current_demand_mapping_status": row.get(
                    "current_demand_mapping_status", ""
                ),
                "gdp_share_conversion_status": row.get(
                    "gdp_share_conversion_status", ""
                ),
                "uncertainty_status": row.get("uncertainty_status", ""),
                "replication_status": row.get("replication_status", ""),
                "robustness_status": row.get("robustness_status", ""),
                "promotion_rule_status": row.get("promotion_rule_status", ""),
                "admission_status": row.get("admission_status", ""),
                "candidate_bps_year_exposure": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "safe_sentence": row.get("safe_sentence", ""),
                "forbidden_sentence": row.get("forbidden_sentence", ""),
                "exact_blocker": row.get("exact_blocker", ""),
                "next_backend_action": next_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def conventional_drag_response_design_gate_rows(
    *,
    conventional_drag_route_pruning_audit_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "conventional_drag_response_design_gate_review_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = "conventional_drag_response_design_gate_not_denominator_calibration"
    gate_specs = [
        (
            "policy_path_100bp_year_normalization",
            "Policy-path 100bp-year normalization",
            "admitted source-backed policy path integral and full protocol gate",
            "policy_path_normalization_status",
            "scalar shocks, futures cells, CME quote metadata, TDSP, or prompt numbers",
        ),
        (
            "source_unit_or_model_boundary",
            "Source unit and model-boundary admission",
            "source unit/sign contract or explicit benchmark/proxy nonuse boundary",
            "admission_status",
            "raw source-unit IRFs or model slots as denominator values",
        ),
        (
            "current_demand_mapping",
            "Current-demand mapping",
            "source-backed FSPDP/PCE/PFI mapping matched to admitted response route",
            "current_demand_mapping_status",
            "generic GDP or context-only shares",
        ),
        (
            "gdp_share_conversion",
            "GDP-share drag conversion",
            "reviewed conversion from response units to GDP-share current-demand drag",
            "gdp_share_conversion_status",
            "component shares without response conversion",
        ),
        (
            "uncertainty_interval",
            "Uncertainty interval",
            "source-backed or locally estimated interval semantics for target route",
            "uncertainty_status",
            "point estimates without admitted interval propagation",
        ),
        (
            "independent_replication",
            "Independent replication",
            "independent reproduction target with tolerance and artifact hashes",
            "replication_status",
            "same-parser echo or review-only metadata",
        ),
        (
            "robustness_transport",
            "Robustness and transport",
            "transport-risk and robustness checks over sample, route, and shock family",
            "robustness_status",
            "single-route diagnostic without transport review",
        ),
        (
            "promotion_rule",
            "Promotion rule",
            "machine-testable rule allowing denominator admission only if all gates pass",
            "promotion_rule_status",
            "manual judgment or external recommendation",
        ),
    ]

    rows: list[dict[str, str]] = []
    for route in conventional_drag_route_pruning_audit_rows:
        for sequence, (
            gate,
            label,
            required_evidence,
            status_field,
            disallowed_shortcut,
        ) in enumerate(gate_specs, start=1):
            observed = route.get(status_field, "")
            if status_field == "admission_status" and not observed.startswith("blocked"):
                observed = f"blocked_route_admission_status::{observed}"
            gate_pass = (
                "pass_gate_available_review_only_not_denominator_admission"
                if observed.startswith("pass")
                else "blocked_gate_not_admitted"
            )
            rows.append(
                {
                    "conventional_drag_response_design_gate_row_id": (
                        "conventional_drag_response_design_gate::"
                        f"{route.get('route_id', '')}::{gate}"
                    ),
                    "conventional_drag_route_pruning_audit_row_id": route.get(
                        "conventional_drag_route_pruning_audit_row_id", ""
                    ),
                    "conventional_drag_empirical_target_registry_row_id": route.get(
                        "conventional_drag_empirical_target_registry_row_id", ""
                    ),
                    "route_id": route.get("route_id", ""),
                    "route_family": route.get("route_family", ""),
                    "route_role": route.get("route_role", ""),
                    "target_id": route.get("target_id", ""),
                    "target_outcome_id": route.get("target_outcome_id", ""),
                    "design_gate": gate,
                    "design_gate_label": label,
                    "gate_sequence_index": str(sequence),
                    "required_evidence_before_admission": required_evidence,
                    "observed_gate_status": observed,
                    "gate_pass_status": gate_pass,
                    "gate_failure_semantics": (
                        "route remains excluded from denominator admission unless "
                        "this gate and every sibling gate pass"
                    ),
                    "allowed_evidence_classes": (
                        "source_backed_protocol;locally_replicated_estimate;"
                        "independent_replication;machine_tested_promotion_rule"
                    ),
                    "disallowed_shortcut_evidence": disallowed_shortcut,
                    "response_design_status": (
                        "blocked_response_design_gate_stack_incomplete"
                    ),
                    "route_admission_status": route.get("admission_status", ""),
                    "candidate_bps_year_exposure": "",
                    "candidate_gdp_share_drag_per_100bp_year": "",
                    "candidate_ci_lower": "",
                    "candidate_ci_upper": "",
                    "exact_blocker": (
                        f"{gate} is not admitted for "
                        f"{route.get('route_id', '')}: {observed}"
                    ),
                    "next_backend_action": route.get("next_backend_action", ""),
                    "allowed_use": allowed_use,
                    "blocked_use": blocked_use,
                    "claim_boundary": claim_boundary,
                    **_false_fields(),
                }
            )
    return rows


def denominator_response_estimate_registry_rows(
    *,
    conventional_drag_route_pruning_audit_rows: list[dict[str, str]],
    conventional_drag_response_design_gate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "denominator_response_estimate_registry_design_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = "denominator_response_estimate_registry_not_calibration"
    required_diagnostics = (
        "support;pretrend;placebo;instrument_relevance;sign_coherence;"
        "uncertainty_interval;independent_replication;robustness_transport;"
        "promotion_rule"
    )

    gates_by_route: dict[str, list[dict[str, str]]] = defaultdict(list)
    for gate in conventional_drag_response_design_gate_rows:
        gates_by_route[gate.get("route_id", "")].append(gate)

    estimator_specs = {
        "canonical_fspdp_current_demand_drag_100bp_year": [
            (
                "canonical_fspdp_design_placeholder",
                "canonical_target_placeholder",
                "FSPDP denominator design placeholder",
                "preferred_target_no_estimator_admitted",
                ("4", "8"),
            )
        ],
        "mir_gk_research_parameterization_route": [
            (
                "mir_gk_component_irf_research_parameterization",
                "mir_gk_literature_research_route",
                "MIR/GK component IRF research parameterization",
                "research_parameterization_only",
                ("4", "8"),
            )
        ],
        "houst_permit_residential_activity_proxy_route": [
            (
                "houst_permit_proxy_bridge_diagnostic",
                "housing_activity_proxy",
                "HOUST/PERMIT proxy bridge diagnostic",
                "proxy_only_diagnostic",
                ("4", "8"),
            )
        ],
        "frbus_official_model_benchmark_route": [
            (
                "frbus_official_model_benchmark",
                "official_model_benchmark",
                "FRB/US official-model benchmark",
                "benchmark_only",
                ("4", "8"),
            )
        ],
        "local_lp_proxy_svar_diagnostic_route": [
            (
                "local_projection_diagnostic",
                "local_projection",
                "Local projection diagnostic design",
                "diagnostic_only",
                ("4", "8"),
            ),
            (
                "proxy_svar_diagnostic",
                "proxy_svar",
                "Proxy-SVAR diagnostic design",
                "diagnostic_only",
                ("4", "8"),
            ),
        ],
    }

    def status_summary(route_id: str) -> tuple[str, str, str]:
        route_gates = gates_by_route.get(route_id, [])
        pass_count = sum(
            gate.get("gate_pass_status", "").startswith("pass")
            for gate in route_gates
        )
        blocked = [
            gate.get("design_gate", "")
            for gate in route_gates
            if not gate.get("gate_pass_status", "").startswith("pass")
        ]
        return str(pass_count), str(len(blocked)), ";".join(blocked)

    def diagnostic_status(
        *,
        estimator_family: str,
        route: dict[str, str],
        field: str,
    ) -> str:
        if estimator_family == "official_model_benchmark":
            return "blocked_benchmark_only_not_empirical_design_gate"
        if estimator_family == "housing_activity_proxy":
            return "blocked_proxy_only_not_direct_response_design_gate"
        if estimator_family == "mir_gk_literature_research_route":
            return "blocked_research_parameterization_not_registered_estimate"
        if estimator_family == "canonical_target_placeholder":
            return "blocked_preferred_target_no_estimator_selected"
        if field == "support":
            return "blocked_local_design_support_not_formally_admitted"
        if field == "pretrend":
            return "blocked_pretrend_diagnostic_not_admitted"
        if field == "placebo":
            return "blocked_placebo_diagnostic_not_admitted"
        if field == "relevance":
            return "blocked_instrument_relevance_not_admitted"
        if field == "sign":
            return "blocked_sign_coherence_not_admitted"
        return route.get("admission_status", "blocked_route_not_admitted")

    rows: list[dict[str, str]] = []
    for route in conventional_drag_route_pruning_audit_rows:
        for (
            estimator_id,
            estimator_family,
            estimator_label,
            estimator_role,
            horizons,
        ) in estimator_specs.get(route.get("route_id", ""), []):
            pass_count, blocked_count, blocked_gates = status_summary(
                route.get("route_id", "")
            )
            for horizon in horizons:
                row_id = (
                    "denominator_response_estimate_registry::"
                    f"{route.get('route_id', '')}::{estimator_id}::h{horizon}"
                )
                exact_blocker = (
                    f"{estimator_label} at h{horizon} remains nonpromotional: "
                    f"{blocked_gates or 'no closed denominator gate stack'}."
                )
                rows.append(
                    {
                        "denominator_response_estimate_registry_row_id": row_id,
                        "conventional_drag_route_pruning_audit_row_id": route.get(
                            "conventional_drag_route_pruning_audit_row_id", ""
                        ),
                        "route_id": route.get("route_id", ""),
                        "route_family": route.get("route_family", ""),
                        "route_role": route.get("route_role", ""),
                        "target_id": route.get("target_id", ""),
                        "target_outcome_id": route.get("target_outcome_id", ""),
                        "estimator_id": estimator_id,
                        "estimator_family": estimator_family,
                        "estimator_label": estimator_label,
                        "estimator_role": estimator_role,
                        "target_horizon_quarters": horizon,
                        "integration_window": f"0_to_{horizon}_quarters_review_only",
                        "shock_or_policy_input_basis": (
                            "blocked_pending_admitted_100bp_year_policy_path"
                        ),
                        "normalization_basis": (
                            "blocked_pending_gdp_share_per_100bp_year_conversion"
                        ),
                        "required_diagnostics": required_diagnostics,
                        "observed_pass_gate_count": pass_count,
                        "observed_blocked_gate_count": blocked_count,
                        "blocked_design_gates": blocked_gates,
                        "support_status": diagnostic_status(
                            estimator_family=estimator_family,
                            route=route,
                            field="support",
                        ),
                        "pretrend_status": diagnostic_status(
                            estimator_family=estimator_family,
                            route=route,
                            field="pretrend",
                        ),
                        "placebo_status": diagnostic_status(
                            estimator_family=estimator_family,
                            route=route,
                            field="placebo",
                        ),
                        "relevance_status": diagnostic_status(
                            estimator_family=estimator_family,
                            route=route,
                            field="relevance",
                        ),
                        "sign_status": diagnostic_status(
                            estimator_family=estimator_family,
                            route=route,
                            field="sign",
                        ),
                        "uncertainty_status": route.get("uncertainty_status", ""),
                        "replication_status": route.get("replication_status", ""),
                        "robustness_status": route.get("robustness_status", ""),
                        "promotion_status": route.get("promotion_rule_status", ""),
                        "formal_design_gate_status": (
                            "blocked_formal_design_gate_stack_incomplete"
                        ),
                        "response_estimate_registration_status": (
                            "blocked_nonpromotional_design_cell_no_estimate_admitted"
                        ),
                        "source_admission_status": route.get("admission_status", ""),
                        "registered_point_estimate": "",
                        "registered_ci_lower": "",
                        "registered_ci_upper": "",
                        "candidate_bps_year_exposure": "",
                        "candidate_gdp_share_drag_per_100bp_year": "",
                        "candidate_ci_lower": "",
                        "candidate_ci_upper": "",
                        "exact_blocker": exact_blocker,
                        "next_backend_action": (
                            "fill_formal_design_diagnostics_before_registering_"
                            "any_denominator_response_estimate"
                        ),
                        "allowed_use": allowed_use,
                        "blocked_use": blocked_use,
                        "claim_boundary": claim_boundary,
                        **_false_fields(),
                    }
                )
    return rows


def denominator_formal_design_gate_rows(
    *,
    denominator_response_estimate_registry_rows: list[dict[str, str]],
    conventional_drag_response_design_gate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "denominator_formal_design_gate_review_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = "denominator_formal_design_gate_not_calibration"
    gates_by_route = {
        (gate.get("route_id", ""), gate.get("design_gate", "")): gate
        for gate in conventional_drag_response_design_gate_rows
    }
    rows: list[dict[str, str]] = []
    for estimate in denominator_response_estimate_registry_rows:
        route_id = estimate.get("route_id", "")
        for gate_name in [
            "policy_path_100bp_year_normalization",
            "source_unit_or_model_boundary",
            "current_demand_mapping",
            "gdp_share_conversion",
            "uncertainty_interval",
            "independent_replication",
            "robustness_transport",
            "promotion_rule",
        ]:
            gate = gates_by_route.get((route_id, gate_name), {})
            formal_status = (
                "pass_review_only_not_admission"
                if gate.get("gate_pass_status", "").startswith("pass")
                else "blocked_formal_gate_not_satisfied"
            )
            rows.append(
                {
                    "denominator_formal_design_gate_row_id": (
                        "denominator_formal_design_gate::"
                        f"{estimate.get('denominator_response_estimate_registry_row_id', '')}"
                        f"::{gate_name}"
                    ),
                    "denominator_response_estimate_registry_row_id": estimate.get(
                        "denominator_response_estimate_registry_row_id", ""
                    ),
                    "conventional_drag_response_design_gate_row_id": gate.get(
                        "conventional_drag_response_design_gate_row_id", ""
                    ),
                    "route_id": route_id,
                    "estimator_id": estimate.get("estimator_id", ""),
                    "estimator_family": estimate.get("estimator_family", ""),
                    "target_id": estimate.get("target_id", ""),
                    "target_outcome_id": estimate.get("target_outcome_id", ""),
                    "target_horizon_quarters": estimate.get(
                        "target_horizon_quarters", ""
                    ),
                    "design_gate": gate_name,
                    "design_gate_label": gate.get("design_gate_label", ""),
                    "gate_sequence_index": gate.get("gate_sequence_index", ""),
                    "required_diagnostic_or_evidence": gate.get(
                        "required_evidence_before_admission", ""
                    ),
                    "observed_gate_status": gate.get("observed_gate_status", ""),
                    "gate_pass_status": gate.get("gate_pass_status", ""),
                    "formal_gate_status": formal_status,
                    "formal_gate_failure_semantics": (
                        "registered design cell cannot carry point estimates, "
                        "intervals, priors, Evidence Mode, or main-ratio entry "
                        "unless every formal design gate passes"
                    ),
                    "allowed_evidence_classes": gate.get("allowed_evidence_classes", ""),
                    "disallowed_shortcut_evidence": gate.get(
                        "disallowed_shortcut_evidence", ""
                    ),
                    "registered_point_estimate": "",
                    "registered_ci_lower": "",
                    "registered_ci_upper": "",
                    "candidate_bps_year_exposure": "",
                    "candidate_gdp_share_drag_per_100bp_year": "",
                    "candidate_ci_lower": "",
                    "candidate_ci_upper": "",
                    "exact_blocker": (
                        f"{gate_name} for {estimate.get('estimator_id', '')} "
                        f"at h{estimate.get('target_horizon_quarters', '')} "
                        f"is {formal_status}: {gate.get('observed_gate_status', '')}"
                    ),
                    "next_backend_action": estimate.get("next_backend_action", ""),
                    "allowed_use": allowed_use,
                    "blocked_use": blocked_use,
                    "claim_boundary": claim_boundary,
                    **_false_fields(),
                }
            )
    return rows


def conventional_drag_response_execution_readiness_packet_rows(
    *,
    conventional_drag_empirical_target_registry_rows: list[dict[str, str]],
    conventional_drag_route_pruning_audit_rows: list[dict[str, str]],
    conventional_drag_response_design_gate_rows: list[dict[str, str]],
    denominator_response_estimate_registry_rows: list[dict[str, str]],
    denominator_formal_design_gate_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "conventional_drag_response_execution_readiness_packet_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = (
        "conventional_drag_response_execution_readiness_packet_not_calibration"
    )
    route_ids = [
        "canonical_fspdp_current_demand_drag_100bp_year",
        "mir_gk_research_parameterization_route",
        "local_lp_proxy_svar_diagnostic_route",
        "frbus_official_model_benchmark_route",
    ]
    target_by_route = {
        row.get("route_id", ""): row
        for row in conventional_drag_empirical_target_registry_rows
    }
    pruning_by_route = {
        row.get("route_id", ""): row for row in conventional_drag_route_pruning_audit_rows
    }
    design_gates_by_route: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in conventional_drag_response_design_gate_rows:
        design_gates_by_route[row.get("route_id", "")].append(row)
    estimates_by_route: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in denominator_response_estimate_registry_rows:
        estimates_by_route[row.get("route_id", "")].append(row)
    formal_gates_by_route: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in denominator_formal_design_gate_rows:
        formal_gates_by_route[row.get("route_id", "")].append(row)

    route_specs = {
        "canonical_fspdp_current_demand_drag_100bp_year": {
            "execution_route_class": "preferred_canonical_fspdp_execution_placeholder",
            "required_input_artifacts": (
                "ratewall_conventional_drag_empirical_target_registry.csv;"
                "ratewall_conventional_drag_route_pruning_audit.csv;"
                "ratewall_conventional_drag_response_design_gate.csv;"
                "ratewall_denominator_formal_design_gate.csv;"
                "ratewall_policy_path_full_protocol_admission_gate_summary.csv;"
                "ratewall_fspdp_component_share_panel.csv"
            ),
            "linked_source_route_tables": (
                "ratewall_conventional_drag_fspdp_component_share_panel.csv;"
                "ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv"
            ),
            "command_or_estimation_procedure": (
                "select_admitted_fspdp_response_estimator_after_all_formal_gates_pass"
            ),
            "unit_conversion_requirement": (
                "admitted_response_units_to_negative_delta_fspdp_percent_of_gdp"
            ),
            "current_demand_mapping_requirement": (
                "source_backed_fspdp_pce_pfi_component_mapping_with_admitted_response"
            ),
            "policy_path_100bp_year_dependency": (
                "requires_admitted_policy_path_bps_year_protocol_before_execution"
            ),
            "uncertainty_requirement": (
                "requires_admitted_response_interval_and_component_aggregation_interval"
            ),
            "replication_requirement": (
                "requires_independent_replication_of_policy_path_and_response_estimator"
            ),
            "next_backend_action": (
                "choose_and_implement_nonpromotional_fspdp_response_estimator_after_design_gate"
            ),
        },
        "mir_gk_research_parameterization_route": {
            "execution_route_class": "mir_gk_research_parameterization_execution_packet",
            "required_input_artifacts": (
                "ratewall_conventional_drag_empirical_target_registry.csv;"
                "ratewall_conventional_drag_route_pruning_audit.csv;"
                "ratewall_conventional_drag_response_design_gate.csv;"
                "ratewall_conventional_drag_research_source_code_interpretation.csv;"
                "ratewall_conventional_drag_research_component_normalization_review.csv;"
                "ratewall_conventional_drag_mirgk_targeted_gap_source_followup.csv;"
                "ratewall_denominator_formal_design_gate.csv;"
                "ratewall_conventional_drag_promotion_contract_checklist.csv"
            ),
            "linked_source_route_tables": (
                "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv;"
                "ratewall_conventional_drag_promotion_contract_checklist.csv"
            ),
            "command_or_estimation_procedure": (
                "execute_mir_gk_replication_only_after_source_unit_horizon_and_policy_path_gates_pass"
            ),
            "unit_conversion_requirement": (
                "reviewed_source_irf_units_to_current_demand_gdp_share_conversion"
            ),
            "current_demand_mapping_requirement": (
                "complete_fspdp_component_coverage_and_chain_aggregation_protocol"
            ),
            "policy_path_100bp_year_dependency": (
                "requires_scalar_or_irf_shock_to_admitted_100bp_year_policy_path_bridge"
            ),
            "uncertainty_requirement": (
                "requires_source_interval_semantics_and_aggregate_uncertainty_propagation"
            ),
            "replication_requirement": (
                "requires_independent_mir_gk_irf_replication_and_tolerance"
            ),
            "next_backend_action": (
                "resolve_mir_gk_source_unit_component_coverage_policy_path_and_replication_gates"
            ),
        },
        "local_lp_proxy_svar_diagnostic_route": {
            "execution_route_class": "local_lp_proxy_svar_diagnostic_execution_packet",
            "required_input_artifacts": (
                "ratewall_conventional_drag_empirical_target_registry.csv;"
                "ratewall_conventional_drag_route_pruning_audit.csv;"
                "ratewall_conventional_drag_response_design_gate.csv;"
                "ratewall_conventional_drag_local_macro_panel.csv;"
                "ratewall_conventional_drag_local_shock_quarterly.csv;"
                "ratewall_conventional_drag_local_lp_design.csv;"
                "ratewall_denominator_formal_design_gate.csv"
            ),
            "linked_source_route_tables": (
                "ratewall_conventional_drag_local_lp_diagnostic.csv;"
                "ratewall_conventional_drag_local_lp_estimate_diagnostic.csv;"
                "ratewall_denominator_formal_design_test_result.csv"
            ),
            "command_or_estimation_procedure": (
                "run_local_lp_or_proxy_svar_diagnostic_only_after_design_support_pretrend_placebo_relevance_sign_gates_pass"
            ),
            "unit_conversion_requirement": (
                "locally_estimated_response_units_to_fspdp_gdp_share_per_admitted_policy_path"
            ),
            "current_demand_mapping_requirement": (
                "target_outcome_must_be_fspdp_or_source_backed_current_demand_component"
            ),
            "policy_path_100bp_year_dependency": (
                "requires_external_instrument_or_shock_series_mapped_to_100bp_year_exposure"
            ),
            "uncertainty_requirement": (
                "requires_newey_west_or_bootstrap_interval_and_design_gate_audit"
            ),
            "replication_requirement": (
                "requires_reproducible_local_estimation_command_and_tolerance"
            ),
            "next_backend_action": (
                "materialize_nonpromotional_local_lp_proxy_svar_design_run_packet"
            ),
        },
        "frbus_official_model_benchmark_route": {
            "execution_route_class": "frbus_benchmark_execution_packet",
            "required_input_artifacts": (
                "ratewall_conventional_drag_empirical_target_registry.csv;"
                "ratewall_conventional_drag_route_pruning_audit.csv;"
                "ratewall_conventional_drag_response_design_gate.csv;"
                "ratewall_frbus_conventional_drag_benchmark_protocol.csv;"
                "ratewall_frbus_benchmark_output_slot_extension_review.csv;"
                "ratewall_denominator_formal_design_gate.csv"
            ),
            "linked_source_route_tables": (
                "ratewall_frbus_conventional_drag_benchmark_protocol.csv;"
                "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv"
            ),
            "command_or_estimation_procedure": (
                "run_frbus_benchmark_simulation_only_as_model_context_not_empirical_denominator"
            ),
            "unit_conversion_requirement": (
                "model_output_slot_units_to_benchmark_context_with_no_denominator_admission"
            ),
            "current_demand_mapping_requirement": (
                "frbus_output_slots_must_map_to_fspdp_or_explicit_benchmark_boundary"
            ),
            "policy_path_100bp_year_dependency": (
                "requires_frbus_policy_experiment_path_not_scalar_shortcut_for_any_comparison"
            ),
            "uncertainty_requirement": (
                "benchmark_uncertainty_not_empirical_interval_without_separate_design"
            ),
            "replication_requirement": (
                "requires_reproducible_frbus_package_command_and_version_hashes"
            ),
            "next_backend_action": (
                "keep_frbus_benchmark_only_or_build_reproducible_nonpromotional_simulation_packet"
            ),
        },
    }

    rows: list[dict[str, str]] = []
    for idx, route_id in enumerate(route_ids, start=1):
        target = target_by_route.get(route_id, {})
        pruning = pruning_by_route.get(route_id, {})
        design_gates = design_gates_by_route.get(route_id, [])
        estimates = estimates_by_route.get(route_id, [])
        formal_gates = formal_gates_by_route.get(route_id, [])
        spec = route_specs[route_id]
        blocked_gate_count = sum(
            not gate.get("formal_gate_status", "").startswith("pass")
            for gate in formal_gates
        )
        formal_statuses = sorted(
            {gate.get("formal_gate_status", "") for gate in formal_gates}
        )
        formal_status = (
            "blocked_formal_design_gate_stack_incomplete"
            if any(status.startswith("blocked") for status in formal_statuses)
            else "pass_formal_design_gate_review_only_not_admission"
        )
        route_role = target.get("route_role", pruning.get("route_role", ""))
        diagnostic_only = "true" if "diagnostic" in route_role else "false"
        terminal_blocker = (
            f"{route_id} cannot execute as denominator evidence: policy-path "
            "100bp-year normalization, source-unit/current-demand conversion, "
            "uncertainty, replication, robustness, and promotion gates remain blocked."
        )
        rows.append(
            {
                "conventional_drag_response_execution_readiness_packet_row_id": (
                    f"conventional_drag_response_execution_readiness_packet::{idx:04d}"
                ),
                "route_id": route_id,
                "route_family": target.get("route_family", pruning.get("route_family", "")),
                "route_role": route_role,
                "target_id": target.get("target_id", pruning.get("target_id", "")),
                "target_outcome_id": target.get(
                    "target_outcome_id", pruning.get("target_outcome_id", "")
                ),
                "execution_route_class": spec["execution_route_class"],
                "preferred_canonical_target": target.get(
                    "preferred_canonical_target", "false"
                ),
                "benchmark_only": target.get("benchmark_only", "false"),
                "research_parameterization_only": target.get(
                    "research_parameterization_only", "false"
                ),
                "diagnostic_only": diagnostic_only,
                "required_input_artifacts": spec["required_input_artifacts"],
                "linked_target_registry_row_id": target.get(
                    "conventional_drag_empirical_target_registry_row_id", ""
                ),
                "linked_route_pruning_audit_row_id": pruning.get(
                    "conventional_drag_route_pruning_audit_row_id", ""
                ),
                "linked_response_design_gate_row_ids": _join_unique(
                    [
                        row.get("conventional_drag_response_design_gate_row_id", "")
                        for row in design_gates
                    ]
                ),
                "linked_response_estimate_registry_row_ids": _join_unique(
                    [
                        row.get("denominator_response_estimate_registry_row_id", "")
                        for row in estimates
                    ]
                ),
                "linked_formal_design_gate_row_ids": _join_unique(
                    [
                        row.get("denominator_formal_design_gate_row_id", "")
                        for row in formal_gates
                    ]
                ),
                "linked_source_route_tables": spec["linked_source_route_tables"],
                "command_or_estimation_procedure": spec[
                    "command_or_estimation_procedure"
                ],
                "unit_conversion_requirement": spec["unit_conversion_requirement"],
                "current_demand_mapping_requirement": spec[
                    "current_demand_mapping_requirement"
                ],
                "policy_path_100bp_year_dependency": spec[
                    "policy_path_100bp_year_dependency"
                ],
                "uncertainty_requirement": spec["uncertainty_requirement"],
                "replication_requirement": spec["replication_requirement"],
                "formal_pass_fail_gates": _join_unique(
                    [row.get("design_gate", "") for row in design_gates]
                ),
                "formal_design_gate_status": formal_status,
                "observed_blocked_gate_count": str(blocked_gate_count),
                "response_execution_readiness_status": (
                    "blocked_response_execution_readiness_not_denominator_admission"
                ),
                "route_admission_status": target.get(
                    "admission_status", pruning.get("admission_status", "")
                ),
                "terminal_blocker": terminal_blocker,
                "candidate_bps_year_exposure": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": terminal_blocker,
                "next_backend_action": spec["next_backend_action"],
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def local_lp_proxy_svar_diagnostic_run_packet_rows(
    *,
    conventional_drag_response_execution_readiness_packet_rows: list[dict[str, str]],
    denominator_response_estimate_registry_rows: list[dict[str, str]],
    conventional_drag_response_design_gate_rows: list[dict[str, str]],
    denominator_formal_design_gate_rows: list[dict[str, str]],
    conventional_drag_local_lp_design_rows: list[dict[str, str]],
    conventional_drag_local_lp_diagnostic_rows: list[dict[str, str]],
    conventional_drag_local_lp_estimate_diagnostic_rows: list[dict[str, str]],
    conventional_drag_local_lp_robustness_diagnostic_rows: list[dict[str, str]],
    conventional_drag_local_lp_sample_window_audit_rows: list[dict[str, str]],
    conventional_drag_local_lp_admission_audit_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    route_id = "local_lp_proxy_svar_diagnostic_route"
    allowed_use = "local_lp_proxy_svar_diagnostic_run_packet_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = "local_lp_proxy_svar_diagnostic_run_packet_not_calibration"
    execution_packet = next(
        (
            row
            for row in conventional_drag_response_execution_readiness_packet_rows
            if row.get("route_id") == route_id
        ),
        {},
    )
    response_design_gate_ids = _join_unique(
        [
            row.get("conventional_drag_response_design_gate_row_id", "")
            for row in conventional_drag_response_design_gate_rows
            if row.get("route_id") == route_id
        ]
    )
    design_rows = [
        row
        for row in conventional_drag_local_lp_design_rows
        if row.get("outcome_id") == "fspdp"
    ]
    sample_rows = [
        row
        for row in conventional_drag_local_lp_sample_window_audit_rows
        if row.get("outcome_id") == "fspdp"
    ]
    admission_ids = _join_unique(
        [row.get("audit_row_id", "") for row in conventional_drag_local_lp_admission_audit_rows]
    )
    proxy_artifacts = (
        "ratewall_proxy_svar_feasibility_diagnostics.csv;"
        "ratewall_proxy_svar_system_panel.csv;"
        "ratewall_proxy_svar_proxy_relevance_diagnostics.csv;"
        "ratewall_proxy_svar_residual_diagnostics.csv;"
        "ratewall_proxy_svar_timing_support_diagnostics.csv"
    )
    estimator_specs = {
        "local_projection_diagnostic": {
            "run_task_class": "local_projection_diagnostic_run_task",
            "estimator_variant": "local_projection_fspdp_horizon_specific_hac_review_only",
            "required_input_artifacts": (
                "ratewall_conventional_drag_response_execution_readiness_packet.csv;"
                "ratewall_denominator_response_estimate_registry.csv;"
                "ratewall_denominator_formal_design_gate.csv;"
                "ratewall_conventional_drag_response_design_gate.csv;"
                "ratewall_conventional_drag_local_macro_panel.csv;"
                "ratewall_conventional_drag_local_shock_quarterly.csv;"
                "ratewall_conventional_drag_local_lp_design.csv;"
                "ratewall_conventional_drag_local_lp_estimate_diagnostic.csv;"
                "ratewall_conventional_drag_local_lp_robustness_diagnostic.csv;"
                "ratewall_conventional_drag_local_lp_sample_window_audit.csv;"
                "ratewall_conventional_drag_local_lp_admission_audit.csv"
            ),
            "linked_proxy_svar_diagnostic_artifacts": "",
            "executable_command_shape": (
                "PYTHONDONTWRITEBYTECODE=1 "
                "$HOME/venvs/ratewall/bin/python -m ratewall.cli "
                "databook build --output-dir outputs "
                "--diagnostic-task local-lp --target fspdp "
                "--estimator local_projection --horizon-q {horizon} --fail-closed"
            ),
            "design_preflight_checks": (
                "local_macro_panel_present;quarterly_shock_series_present;"
                "fspdp_design_rows_present;sample_window_audit_present;"
                "formal_design_gate_rows_present"
            ),
            "uncertainty_method_placeholder": (
                "newey_west_hac_placeholder_review_only_not_admitted_interval"
            ),
            "replication_expectation": (
                "rerun_local_projection_diagnostic_and_compare_source_unit_rows_only"
            ),
        },
        "proxy_svar_diagnostic": {
            "run_task_class": "proxy_svar_diagnostic_run_task",
            "estimator_variant": "proxy_svar_system_preflight_horizon_specific_review_only",
            "required_input_artifacts": (
                "ratewall_conventional_drag_response_execution_readiness_packet.csv;"
                "ratewall_denominator_response_estimate_registry.csv;"
                "ratewall_denominator_formal_design_gate.csv;"
                "ratewall_conventional_drag_response_design_gate.csv;"
                "ratewall_conventional_drag_local_macro_panel.csv;"
                "ratewall_conventional_drag_local_shock_quarterly.csv;"
                "ratewall_conventional_drag_local_lp_design.csv;"
                f"{proxy_artifacts}"
            ),
            "linked_proxy_svar_diagnostic_artifacts": proxy_artifacts,
            "executable_command_shape": (
                "PYTHONDONTWRITEBYTECODE=1 "
                "$HOME/venvs/ratewall/bin/python -m ratewall.cli "
                "databook build --output-dir outputs "
                "--diagnostic-task proxy-svar --target fspdp "
                "--estimator proxy_svar --horizon-q {horizon} --fail-closed"
            ),
            "design_preflight_checks": (
                "proxy_svar_feasibility_present;system_panel_present;"
                "proxy_relevance_diagnostic_present;residual_diagnostic_present;"
                "timing_support_diagnostic_present;formal_design_gate_rows_present"
            ),
            "uncertainty_method_placeholder": (
                "proxy_svar_bootstrap_or_delta_method_placeholder_review_only_not_admitted_interval"
            ),
            "replication_expectation": (
                "rerun_proxy_svar_preflight_and_relevance_residual_timing_diagnostics_only"
            ),
        },
    }
    estimate_rows = [
        row
        for row in denominator_response_estimate_registry_rows
        if row.get("route_id") == route_id
        and row.get("estimator_id") in estimator_specs
        and row.get("target_horizon_quarters") in {"4", "8"}
    ]
    estimate_rows = sorted(
        estimate_rows,
        key=lambda row: (
            row.get("estimator_id", ""),
            int(row.get("target_horizon_quarters", "0") or "0"),
        ),
    )
    rows: list[dict[str, str]] = []
    for idx, estimate in enumerate(estimate_rows, start=1):
        estimator_id = estimate.get("estimator_id", "")
        horizon = estimate.get("target_horizon_quarters", "")
        spec = estimator_specs[estimator_id]
        formal_gates = [
            row
            for row in denominator_formal_design_gate_rows
            if row.get("denominator_response_estimate_registry_row_id")
            == estimate.get("denominator_response_estimate_registry_row_id")
        ]
        blocked_formal_gates = _join_unique(
            [
                row.get("design_gate", "")
                for row in formal_gates
                if not row.get("formal_gate_status", "").startswith("pass")
            ]
        )
        blocked_gate_count = len(
            [
                row
                for row in formal_gates
                if not row.get("formal_gate_status", "").startswith("pass")
            ]
        )
        lp_diagnostic_ids = _join_unique(
            [
                row.get("lp_row_id", "")
                for row in conventional_drag_local_lp_diagnostic_rows
                if row.get("outcome_id") == "fspdp"
                and row.get("horizon_q") == horizon
            ]
        )
        lp_estimate_ids = _join_unique(
            [
                row.get("estimate_row_id", "")
                for row in conventional_drag_local_lp_estimate_diagnostic_rows
                if row.get("outcome_id") == "fspdp"
                and row.get("horizon_q") == horizon
            ]
        )
        robustness_ids = _join_unique(
            [
                row.get("robustness_row_id", "")
                for row in conventional_drag_local_lp_robustness_diagnostic_rows
                if row.get("outcome_id") == "fspdp"
                and row.get("horizon_q") == horizon
            ]
        )
        terminal_blocker = (
            f"{estimator_id} h{horizon} remains diagnostic-only: "
            "policy-path 100bp-year normalization, source-unit admission, "
            "GDP-share conversion, uncertainty admission, independent "
            "replication, robustness transport, and promotion gates remain blocked."
        )
        rows.append(
            {
                "local_lp_proxy_svar_diagnostic_run_packet_row_id": (
                    f"local_lp_proxy_svar_diagnostic_run_packet::{idx:04d}"
                ),
                "route_id": route_id,
                "estimator_id": estimator_id,
                "estimator_family": estimate.get("estimator_family", ""),
                "target_id": estimate.get("target_id", ""),
                "target_outcome_id": estimate.get("target_outcome_id", ""),
                "target_horizon_quarters": horizon,
                "integration_window": estimate.get("integration_window", ""),
                "run_task_class": spec["run_task_class"],
                "estimator_variant": spec["estimator_variant"],
                "executable_command_shape": spec["executable_command_shape"].format(
                    horizon=horizon
                ),
                "required_input_artifacts": spec["required_input_artifacts"],
                "linked_response_execution_readiness_packet_row_id": execution_packet.get(
                    "conventional_drag_response_execution_readiness_packet_row_id", ""
                ),
                "linked_denominator_response_estimate_registry_row_id": estimate.get(
                    "denominator_response_estimate_registry_row_id", ""
                ),
                "linked_response_design_gate_row_ids": response_design_gate_ids,
                "linked_formal_design_gate_row_ids": _join_unique(
                    [row.get("denominator_formal_design_gate_row_id", "") for row in formal_gates]
                ),
                "linked_local_lp_design_row_ids": _join_unique(
                    [row.get("design_id", "") for row in design_rows]
                ),
                "linked_local_lp_diagnostic_row_ids": lp_diagnostic_ids,
                "linked_local_lp_estimate_diagnostic_row_ids": lp_estimate_ids,
                "linked_local_lp_robustness_diagnostic_row_ids": robustness_ids,
                "linked_local_lp_sample_window_audit_row_ids": _join_unique(
                    [row.get("sample_audit_row_id", "") for row in sample_rows]
                ),
                "linked_local_lp_admission_audit_row_ids": admission_ids,
                "linked_proxy_svar_diagnostic_artifacts": spec[
                    "linked_proxy_svar_diagnostic_artifacts"
                ],
                "design_preflight_checks": spec["design_preflight_checks"],
                "sample_window_requirement": (
                    "exclude_elb_pandemic_emergency_sample_window_review_only"
                ),
                "policy_path_100bp_year_dependency": (
                    "blocked_requires_admitted_policy_path_bps_year_exposure_before_any_denominator_use"
                ),
                "current_demand_mapping_requirement": (
                    "fspdp_current_demand_mapping_available_review_only_not_drag_estimate"
                ),
                "unit_conversion_requirement": (
                    "blocked_source_cell_or_system_response_units_not_admitted_as_gdp_share_per_100bp_year"
                ),
                "uncertainty_method_placeholder": spec[
                    "uncertainty_method_placeholder"
                ],
                "replication_expectation": spec["replication_expectation"],
                "blocked_formal_gates": blocked_formal_gates,
                "observed_blocked_gate_count": str(blocked_gate_count),
                "diagnostic_run_status": (
                    "blocked_local_lp_proxy_svar_run_packet_not_denominator_execution"
                ),
                "route_admission_status": estimate.get("source_admission_status", ""),
                "terminal_blocker": terminal_blocker,
                "registered_point_estimate": "",
                "registered_ci_lower": "",
                "registered_ci_upper": "",
                "candidate_bps_year_exposure": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": terminal_blocker,
                "next_backend_action": (
                    "execute_or_refresh_diagnostic_preflight_only_then_recheck_formal_gates"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def local_lp_proxy_svar_execution_preflight_results_rows(
    *,
    local_lp_proxy_svar_diagnostic_run_packet_rows: list[dict[str, str]],
    conventional_drag_local_lp_diagnostic_rows: list[dict[str, str]],
    conventional_drag_local_lp_estimate_diagnostic_rows: list[dict[str, str]],
    conventional_drag_local_lp_robustness_diagnostic_rows: list[dict[str, str]],
    proxy_svar_feasibility_rows: list[dict[str, str]],
    proxy_svar_system_panel_rows: list[dict[str, str]],
    proxy_svar_relevance_rows: list[dict[str, str]],
    proxy_svar_residual_rows: list[dict[str, str]],
    proxy_svar_timing_rows: list[dict[str, str]],
    available_artifact_row_counts: dict[str, int],
) -> list[dict[str, str]]:
    allowed_use = "local_lp_proxy_svar_execution_preflight_results_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = (
        "local_lp_proxy_svar_execution_preflight_results_not_calibration"
    )
    rows: list[dict[str, str]] = []
    for idx, packet in enumerate(local_lp_proxy_svar_diagnostic_run_packet_rows, start=1):
        estimator_id = packet.get("estimator_id", "")
        horizon = packet.get("target_horizon_quarters", "")
        required = [
            artifact
            for artifact in packet.get("required_input_artifacts", "").split(";")
            if artifact
        ]
        present = [
            artifact
            for artifact in required
            if available_artifact_row_counts.get(artifact, 0) > 0
        ]
        missing = [artifact for artifact in required if artifact not in present]
        lp_diagnostic_count = sum(
            1
            for row in conventional_drag_local_lp_diagnostic_rows
            if row.get("outcome_id") == "fspdp" and row.get("horizon_q") == horizon
        )
        lp_estimate_count = sum(
            1
            for row in conventional_drag_local_lp_estimate_diagnostic_rows
            if row.get("outcome_id") == "fspdp" and row.get("horizon_q") == horizon
        )
        lp_robustness_count = sum(
            1
            for row in conventional_drag_local_lp_robustness_diagnostic_rows
            if row.get("outcome_id") == "fspdp" and row.get("horizon_q") == horizon
        )
        local_coverage_ok = (
            lp_diagnostic_count > 0
            and lp_estimate_count > 0
            and lp_robustness_count > 0
        )
        proxy_coverage_ok = (
            len(proxy_svar_feasibility_rows) > 0
            and len(proxy_svar_system_panel_rows) > 0
            and len(proxy_svar_relevance_rows) > 0
            and len(proxy_svar_residual_rows) > 0
            and len(proxy_svar_timing_rows) > 0
        )
        if estimator_id == "local_projection_diagnostic":
            coverage_status = (
                "pass_local_lp_diagnostic_rows_present_review_only"
                if local_coverage_ok
                else "blocked_missing_local_lp_diagnostic_rows"
            )
            proxy_status = "not_applicable_local_projection_task"
        else:
            coverage_status = (
                "pass_proxy_svar_diagnostic_rows_present_review_only"
                if proxy_coverage_ok
                else "blocked_missing_proxy_svar_diagnostic_rows"
            )
            proxy_status = (
                "pass_proxy_svar_preflight_rows_present_review_only"
                if proxy_coverage_ok
                else "blocked_missing_proxy_svar_preflight_rows"
            )
        command_ready = (
            "pass_command_shape_present_review_only_not_executed"
            if packet.get("executable_command_shape", "").startswith(
                "PYTHONDONTWRITEBYTECODE=1"
            )
            and "--fail-closed" in packet.get("executable_command_shape", "")
            else "blocked_missing_fail_closed_command_shape"
        )
        artifact_status = (
            "pass_required_artifacts_present_review_only"
            if not missing
            else "blocked_missing_required_artifacts"
        )
        formal_gate_status = (
            "blocked_formal_gates_remain_unsatisfied"
            if packet.get("blocked_formal_gates", "")
            else "blocked_missing_formal_gate_blocker_list"
        )
        design_preflight_status = (
            "pass_design_preflight_inputs_present_review_only"
            if command_ready.startswith("pass")
            and artifact_status.startswith("pass")
            and coverage_status.startswith("pass")
            else "blocked_design_preflight_inputs_incomplete"
        )
        terminal_blocker = (
            f"{estimator_id} h{horizon} preflight is nonpromotional: "
            "required artifacts and diagnostics can be checked, but source-unit "
            "results remain blocked from denominator use until 100bp-year "
            "normalization, GDP-share conversion, admitted uncertainty, "
            "replication, robustness, and promotion gates pass."
        )
        rows.append(
            {
                "local_lp_proxy_svar_execution_preflight_results_row_id": (
                    f"local_lp_proxy_svar_execution_preflight_results::{idx:04d}"
                ),
                "local_lp_proxy_svar_diagnostic_run_packet_row_id": packet.get(
                    "local_lp_proxy_svar_diagnostic_run_packet_row_id", ""
                ),
                "route_id": packet.get("route_id", ""),
                "estimator_id": estimator_id,
                "estimator_family": packet.get("estimator_family", ""),
                "target_id": packet.get("target_id", ""),
                "target_outcome_id": packet.get("target_outcome_id", ""),
                "target_horizon_quarters": horizon,
                "run_task_class": packet.get("run_task_class", ""),
                "estimator_variant": packet.get("estimator_variant", ""),
                "executable_command_shape": packet.get("executable_command_shape", ""),
                "command_shape_readiness_status": command_ready,
                "required_input_artifacts": packet.get("required_input_artifacts", ""),
                "required_artifact_presence_status": artifact_status,
                "required_artifact_present_count": str(len(present)),
                "required_artifact_missing_count": str(len(missing)),
                "missing_required_artifacts": ";".join(missing),
                "linked_local_proxy_diagnostic_coverage_status": coverage_status,
                "local_lp_coverage_status": (
                    "pass_local_lp_horizon_diagnostics_present_review_only"
                    if local_coverage_ok
                    else "blocked_missing_local_lp_horizon_diagnostics"
                ),
                "proxy_svar_coverage_status": proxy_status,
                "local_lp_diagnostic_row_count": str(lp_diagnostic_count),
                "local_lp_estimate_diagnostic_row_count": str(lp_estimate_count),
                "local_lp_robustness_diagnostic_row_count": str(lp_robustness_count),
                "proxy_svar_feasibility_row_count": str(len(proxy_svar_feasibility_rows)),
                "proxy_svar_system_panel_row_count": str(len(proxy_svar_system_panel_rows)),
                "proxy_svar_relevance_row_count": str(len(proxy_svar_relevance_rows)),
                "proxy_svar_residual_row_count": str(len(proxy_svar_residual_rows)),
                "proxy_svar_timing_row_count": str(len(proxy_svar_timing_rows)),
                "design_preflight_status": design_preflight_status,
                "formal_gate_blocker_status": formal_gate_status,
                "blocked_formal_gates": packet.get("blocked_formal_gates", ""),
                "observed_blocked_gate_count": packet.get("observed_blocked_gate_count", ""),
                "source_unit_result_boundary_status": (
                    "blocked_source_unit_only_result_not_gdp_share_denominator"
                ),
                "execution_result_status": (
                    "blocked_preflight_results_review_only_not_executed_denominator"
                ),
                "terminal_blocker": terminal_blocker,
                "registered_point_estimate": "",
                "registered_ci_lower": "",
                "registered_ci_upper": "",
                "candidate_bps_year_exposure": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": terminal_blocker,
                "next_backend_action": (
                    "execute_nonpromotional_preflight_refresh_or_close_missing_artifact_gaps"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def local_lp_proxy_svar_route_closure_decision_rows(
    *,
    local_lp_proxy_svar_diagnostic_run_packet_rows: list[dict[str, str]],
    local_lp_proxy_svar_execution_preflight_results_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "local_lp_proxy_svar_route_closure_decision_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = "local_lp_proxy_svar_route_closure_decision_not_calibration"
    route_id = "local_lp_proxy_svar_diagnostic_route"
    preflight_rows = [
        row
        for row in local_lp_proxy_svar_execution_preflight_results_rows
        if row.get("route_id") == route_id
    ]
    run_rows = [
        row
        for row in local_lp_proxy_svar_diagnostic_run_packet_rows
        if row.get("route_id") == route_id
    ]
    remaining_gates = _join_unique(
        gate
        for row in preflight_rows
        for gate in row.get("blocked_formal_gates", "").split(";")
        if gate
    )
    required_artifacts = _join_unique(
        artifact
        for row in preflight_rows or run_rows
        for artifact in row.get("required_input_artifacts", "").split(";")
        if artifact
    )
    estimator_ids = _join_unique(row.get("estimator_id", "") for row in preflight_rows)
    horizons = _join_unique(row.get("target_horizon_quarters", "") for row in preflight_rows)
    command_ready = all(
        row.get("command_shape_readiness_status", "").startswith("pass")
        for row in preflight_rows
    )
    artifact_ready = all(
        row.get("required_artifact_presence_status", "").startswith("pass")
        and row.get("required_artifact_missing_count") == "0"
        for row in preflight_rows
    )
    coverage_ready = all(
        row.get("linked_local_proxy_diagnostic_coverage_status", "").startswith("pass")
        for row in preflight_rows
    )
    source_unit_blocked = all(
        row.get("source_unit_result_boundary_status", "").startswith("blocked")
        and row.get("execution_result_status", "").startswith("blocked")
        for row in preflight_rows
    )
    formal_blocked = all(
        row.get("formal_gate_blocker_status", "").startswith("blocked")
        and row.get("blocked_formal_gates")
        for row in preflight_rows
    )
    present_diagnostics_summary = (
        "run_packet_rows="
        f"{len(run_rows)};preflight_rows={len(preflight_rows)};"
        "local_lp_diagnostic_rows="
        f"{max((int(row.get('local_lp_diagnostic_row_count', '0') or '0') for row in preflight_rows), default=0)};"
        "local_lp_estimate_diagnostic_rows="
        f"{max((int(row.get('local_lp_estimate_diagnostic_row_count', '0') or '0') for row in preflight_rows), default=0)};"
        "local_lp_robustness_diagnostic_rows="
        f"{max((int(row.get('local_lp_robustness_diagnostic_row_count', '0') or '0') for row in preflight_rows), default=0)};"
        "proxy_svar_feasibility_rows="
        f"{max((int(row.get('proxy_svar_feasibility_row_count', '0') or '0') for row in preflight_rows), default=0)};"
        "proxy_svar_system_panel_rows="
        f"{max((int(row.get('proxy_svar_system_panel_row_count', '0') or '0') for row in preflight_rows), default=0)}"
    )
    exact_blocker = (
        "Local LP/proxy-SVAR diagnostics cannot enter the denominator because "
        "they remain source-unit/preflight results with blocked 100bp-year "
        "normalization, source-unit/model-boundary admission, GDP-share "
        "conversion, uncertainty admission, independent replication, "
        "robustness transport, and promotion-rule gates."
    )
    return [
        {
            "local_lp_proxy_svar_route_closure_decision_row_id": (
                "local_lp_proxy_svar_route_closure_decision::0001"
            ),
            "route_id": route_id,
            "route_label": "local LP / proxy-SVAR diagnostic denominator route",
            "decision_scope": "route_level_terminal_blocker_and_next_action",
            "source_run_packet_artifact": (
                "ratewall_local_lp_proxy_svar_diagnostic_run_packet.csv"
            ),
            "source_preflight_results_artifact": (
                "ratewall_local_lp_proxy_svar_execution_preflight_results.csv"
            ),
            "run_packet_row_count": str(len(run_rows)),
            "preflight_results_row_count": str(len(preflight_rows)),
            "estimator_ids_covered": estimator_ids,
            "target_horizons_covered": horizons,
            "required_artifacts_summary": required_artifacts,
            "present_diagnostics_summary": present_diagnostics_summary,
            "command_preflight_readiness_status": (
                "pass_command_preflight_ready_review_only"
                if command_ready
                else "blocked_command_preflight_not_ready"
            ),
            "required_artifact_presence_status": (
                "pass_required_artifacts_present_review_only"
                if artifact_ready
                else "blocked_required_artifacts_missing"
            ),
            "diagnostic_coverage_status": (
                "pass_local_lp_proxy_svar_diagnostics_present_review_only"
                if coverage_ready
                else "blocked_missing_local_or_proxy_diagnostics"
            ),
            "remaining_formal_gates": remaining_gates,
            "remaining_formal_gate_count": str(
                len([gate for gate in remaining_gates.split(";") if gate])
            ),
            "source_unit_result_boundary_status": (
                "blocked_source_unit_preflight_results_not_denominator"
                if source_unit_blocked
                else "blocked_source_unit_boundary_not_verified"
            ),
            "denominator_entry_blocker": (
                "blocked_no_admitted_100bp_year_gdp_share_current_demand_drag"
            ),
            "terminal_blocker_status": (
                "blocked_terminal_local_lp_proxy_svar_route_diagnostic_only"
                if formal_blocked and source_unit_blocked
                else "blocked_route_closure_inputs_incomplete"
            ),
            "route_closure_status": (
                "blocked_route_closed_as_diagnostic_only_pending_required_denominator_gates"
            ),
            "why_outputs_cannot_enter_denominator": exact_blocker,
            "registered_point_estimate": "",
            "registered_ci_lower": "",
            "registered_ci_upper": "",
            "candidate_bps_year_exposure": "",
            "candidate_gdp_share_drag_per_100bp_year": "",
            "candidate_ci_lower": "",
            "candidate_ci_upper": "",
            "exact_blocker": exact_blocker,
            "next_backend_action": (
                "resolve_policy_path_100bp_year_normalization_and_gdp_share_conversion_before_any_local_denominator_use"
            ),
            "allowed_use": allowed_use,
            "blocked_use": blocked_use,
            "claim_boundary": claim_boundary,
            **_false_fields(),
        }
    ]


def conventional_drag_denominator_route_triage_synthesis_rows(
    *,
    conventional_drag_route_pruning_audit_rows: list[dict[str, str]],
    conventional_drag_response_design_gate_rows: list[dict[str, str]],
    denominator_response_estimate_registry_rows: list[dict[str, str]],
    denominator_formal_design_gate_rows: list[dict[str, str]],
    conventional_drag_response_execution_readiness_packet_rows: list[dict[str, str]],
    local_lp_proxy_svar_route_closure_decision_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "conventional_drag_denominator_route_triage_synthesis_only"
    blocked_use = (
        "denominator_prior_narrowing;main_ratio;Evidence_Mode;pricing_output;"
        "raw_rate_shock;holder_allocation;tax_incidence_welfare_mpc;"
        "reset_calendar;policy_failure;empirical_threshold;causal_financialization"
    )
    claim_boundary = (
        "conventional_drag_denominator_route_triage_synthesis_not_calibration"
    )
    project_next_action = (
        "resolve_policy_path_100bp_year_normalization_then_select_nonpromotional_fspdp_response_estimator"
    )
    shared_blocker = (
        "No route is admitted because policy-path 100bp-year normalization, "
        "source-unit/model-boundary admission, GDP-share current-demand "
        "conversion, uncertainty, independent replication, robustness, and "
        "promotion-rule gates do not all pass."
    )
    triage_specs = {
        "canonical_fspdp_current_demand_drag_100bp_year": (
            "1",
            "preferred_canonical_route_blocked_pending_shared_denominator_gates",
        ),
        "local_lp_proxy_svar_diagnostic_route": (
            "2",
            "diagnostic_execution_route_closed_pending_shared_denominator_gates",
        ),
        "mir_gk_research_parameterization_route": (
            "3",
            "research_parameterization_route_blocked_pending_source_unit_and_coverage",
        ),
        "frbus_official_model_benchmark_route": (
            "4",
            "benchmark_route_not_canonical_denominator",
        ),
        "houst_permit_residential_activity_proxy_route": (
            "5",
            "proxy_route_not_direct_current_demand_denominator",
        ),
        "official_fspdp_component_share_context": (
            "6",
            "source_backed_context_only_not_response_route",
        ),
    }

    design_by_route: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in conventional_drag_response_design_gate_rows:
        design_by_route[row.get("route_id", "")].append(row)
    estimates_by_route: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in denominator_response_estimate_registry_rows:
        estimates_by_route[row.get("route_id", "")].append(row)
    formal_by_route: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in denominator_formal_design_gate_rows:
        formal_by_route[row.get("route_id", "")].append(row)
    execution_by_route = {
        row.get("route_id", ""): row
        for row in conventional_drag_response_execution_readiness_packet_rows
    }
    local_closure = next(
        (
            row
            for row in local_lp_proxy_svar_route_closure_decision_rows
            if row.get("route_id") == "local_lp_proxy_svar_diagnostic_route"
        ),
        {},
    )

    rows: list[dict[str, str]] = []
    sorted_routes = sorted(
        conventional_drag_route_pruning_audit_rows,
        key=lambda row: int(triage_specs.get(row.get("route_id", ""), ("99", ""))[0]),
    )
    for route in sorted_routes:
        route_id = route.get("route_id", "")
        triage_rank, triage_bucket = triage_specs.get(
            route_id,
            ("99", "blocked_unranked_denominator_route"),
        )
        design_rows = design_by_route.get(route_id, [])
        estimate_rows = estimates_by_route.get(route_id, [])
        formal_rows = formal_by_route.get(route_id, [])
        execution_row = execution_by_route.get(route_id, {})
        blocked_design_gates = _join_unique(
            row.get("design_gate", "")
            for row in design_rows
            if row.get("gate_pass_status", "").startswith("blocked")
        )
        blocked_formal_gates = _join_unique(
            row.get("design_gate", "")
            for row in formal_rows
            if row.get("formal_gate_status", "").startswith("blocked")
        )
        blocked_gate_stack = _join_unique(
            [
                *(gate for gate in blocked_design_gates.split(";") if gate),
                *(gate for gate in blocked_formal_gates.split(";") if gate),
                *(
                    gate
                    for gate in route.get("failed_gate_stack", "").split(";")
                    if gate
                ),
            ]
        )
        response_design_pass_count = sum(
            1
            for row in design_rows
            if row.get("gate_pass_status", "").startswith("pass")
        )
        response_design_blocked_count = sum(
            1
            for row in design_rows
            if row.get("gate_pass_status", "").startswith("blocked")
        )
        formal_blocked_count = sum(
            1
            for row in formal_rows
            if row.get("formal_gate_status", "").startswith("blocked")
        )
        execution_status = execution_row.get(
            "response_execution_readiness_status",
            "not_applicable_no_execution_packet_for_context_or_proxy_route",
        )
        local_closure_status = (
            local_closure.get("route_closure_status", "")
            if route_id == "local_lp_proxy_svar_diagnostic_route"
            else "not_applicable_non_local_lp_proxy_svar_route"
        )
        route_terminal = _join_unique(
            [
                route.get("exact_blocker", ""),
                execution_row.get("terminal_blocker", ""),
                local_closure.get("exact_blocker", "")
                if route_id == "local_lp_proxy_svar_diagnostic_route"
                else "",
            ]
        )
        route_next_action = execution_row.get("next_backend_action") or route.get(
            "next_backend_action", ""
        )
        rows.append(
            {
                "conventional_drag_denominator_route_triage_synthesis_row_id": (
                    "conventional_drag_denominator_route_triage_synthesis::"
                    f"{int(triage_rank):04d}"
                ),
                "route_id": route_id,
                "route_family": route.get("route_family", ""),
                "route_label": route.get("route_label", ""),
                "route_role": route.get("route_role", ""),
                "triage_rank": triage_rank,
                "triage_bucket": triage_bucket,
                "target_id": route.get("target_id", ""),
                "target_outcome_id": route.get("target_outcome_id", ""),
                "preferred_canonical_target": route.get("preferred_canonical_target", ""),
                "benchmark_only": route.get("benchmark_only", ""),
                "research_parameterization_only": route.get(
                    "research_parameterization_only", ""
                ),
                "proxy_only": route.get("proxy_only", ""),
                "source_backed_context_only": route.get("source_backed_context_only", ""),
                "linked_route_pruning_audit_row_id": route.get(
                    "conventional_drag_route_pruning_audit_row_id", ""
                ),
                "linked_response_design_gate_row_ids": _join_unique(
                    row.get("conventional_drag_response_design_gate_row_id", "")
                    for row in design_rows
                ),
                "linked_denominator_response_estimate_registry_row_ids": _join_unique(
                    row.get("denominator_response_estimate_registry_row_id", "")
                    for row in estimate_rows
                ),
                "linked_formal_design_gate_row_ids": _join_unique(
                    row.get("denominator_formal_design_gate_row_id", "")
                    for row in formal_rows
                ),
                "linked_execution_readiness_packet_row_id": execution_row.get(
                    "conventional_drag_response_execution_readiness_packet_row_id", ""
                ),
                "linked_local_lp_proxy_svar_route_closure_decision_row_id": (
                    local_closure.get(
                        "local_lp_proxy_svar_route_closure_decision_row_id", ""
                    )
                    if route_id == "local_lp_proxy_svar_diagnostic_route"
                    else ""
                ),
                "route_pruning_status": route.get("pruning_status", ""),
                "response_design_gate_count": str(len(design_rows)),
                "response_design_pass_review_only_count": str(response_design_pass_count),
                "response_design_blocked_gate_count": str(response_design_blocked_count),
                "response_estimate_registry_row_count": str(len(estimate_rows)),
                "formal_design_gate_count": str(len(formal_rows)),
                "formal_design_blocked_gate_count": str(formal_blocked_count),
                "execution_readiness_packet_status": execution_status,
                "local_lp_proxy_svar_closure_status": local_closure_status,
                "required_artifacts_summary": execution_row.get(
                    "required_input_artifacts", route.get("linked_evidence_tables", "")
                ),
                "required_gate_stack": route.get("required_gate_stack", ""),
                "blocked_gate_stack": blocked_gate_stack,
                "shared_blocker_summary": shared_blocker,
                "route_specific_terminal_blocker": route_terminal,
                "route_admission_status": route.get("admission_status", ""),
                "denominator_admission_status": (
                    "blocked_no_conventional_drag_route_admitted"
                ),
                "route_triage_status": (
                    "blocked_route_triaged_nonpromotional_no_denominator_entry"
                ),
                "project_next_backend_action": project_next_action,
                "route_next_backend_action": route_next_action,
                "single_next_backend_action_rank": (
                    "1" if route_id == "canonical_fspdp_current_demand_drag_100bp_year" else ""
                ),
                "candidate_bps_year_exposure": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": shared_blocker,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def channel_taxonomy_registry_rows(
    *,
    paper_channel_map_rows: list[dict[str, str]],
    assumption_mode_channel_status_crosswalk_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use, blocked_use, claim_boundary = _common_boundary()
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    def classify(label: str, family: str, role: str) -> tuple[str, str, bool, bool, bool, str]:
        text = " ".join([label, family, role]).lower()
        normalized_text = text.replace("_", " ").replace("-", " ")
        price_tokens = (
            "working capital",
            "carry",
            "wacc",
            "shelter",
            "regulated",
            "bnpl",
            "dealer inventory",
            "inventory carry",
            "price sidecar",
            "price channel",
            "price setting",
            "price pass through",
        )
        if any(token in normalized_text for token in price_tokens):
            return (
                "inflation_wall",
                "inflation_sidecar_design",
                False,
                False,
                True,
                "forbidden_for_RW_Y",
            )
        if "drag" in text or "denominator" in text or "credit" in text:
            return ("RW_Y", "real_demand_denominator_candidate", False, True, False, "blocked")
        if "wrapper" in text or "leakage" in text or "tax" in text or "foreign" in text:
            return ("RW_Y", "context_wrapper_only", False, False, False, "context_only")
        return ("RW_Y", "real_demand_numerator_candidate", True, False, False, "blocked")

    for idx, item in enumerate(paper_channel_map_rows, start=1):
        label = item.get("paper_channel", "")
        channel_id = _slug(label)
        seen.add(channel_id)
        ratio_layer, role, enters_num, enters_den, price_sidecar, status = classify(
            label,
            item.get("channel_family", ""),
            item.get("paper_role", ""),
        )
        rows.append(
            {
                "channel_taxonomy_registry_row_id": f"channel_taxonomy_registry::{idx:04d}",
                "channel_id": channel_id,
                "subchannel_id": item.get("channel_family", ""),
                "source_channel_label": label,
                "source_artifact": "ratewall_paper_channel_map.csv",
                "ratio_layer": ratio_layer,
                "mode_class": (
                    "paper_design_only"
                    if ratio_layer == "inflation_wall"
                    else "assumption_mode_object"
                ),
                "channel_role": role,
                "enters_rw_y_numerator": _bool(enters_num and status != "context_only"),
                "enters_rw_y_denominator": _bool(enters_den),
                "enters_rw_pi_numerator": _bool(price_sidecar),
                "enters_rw_pi_denominator": "false",
                "enters_price_sidecar": _bool(price_sidecar),
                "enters_context_only": _bool(status == "context_only"),
                "forbidden_ratio_layers": (
                    "RW_Y" if price_sidecar else "RW_pi;canonical_promotion_without_gate"
                ),
                "source_status": item.get("evidence_status", ""),
                "assumption_mode_status": item.get("source_mode_label", ""),
                "promotion_status": item.get("promotion_status", ""),
                "double_count_risk": (
                    "price_sidecar_misclassified_as_real_demand"
                    if price_sidecar
                    else "requires_overlap_review_before_promotion"
                ),
                "safe_sentence": item.get("paper_safe_sentence", "")
                or f"{label} is classified as {role}.",
                "forbidden_sentence": item.get("paper_forbidden_sentence", "")
                or f"{label} is admitted without source gates.",
                "exact_blocker": (
                    "price_sidecar_not_rw_y_numerator"
                    if price_sidecar
                    else "blocked_until_source_gate_and_double_count_review_pass"
                ),
                "next_backend_action": "use_taxonomy_before_paper_or_scenario_claims",
                "allowed_use": "channel_taxonomy_review_only",
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )

    offset = len(rows)
    for item in assumption_mode_channel_status_crosswalk_rows:
        channel_key = item.get("channel_key", "")
        if _slug(channel_key) in seen:
            continue
        ratio_layer, role, enters_num, enters_den, price_sidecar, status = classify(
            channel_key,
            item.get("context_id", ""),
            item.get("promotion_status", ""),
        )
        sidecar = (
            price_sidecar
            or item.get("static_sidecar_status", "") not in {"", "not_applicable"}
        )
        rows.append(
            {
                "channel_taxonomy_registry_row_id": (
                    f"channel_taxonomy_registry::{len(rows) + 1:04d}"
                ),
                "channel_id": _slug(channel_key),
                "subchannel_id": item.get("context_id", ""),
                "source_channel_label": channel_key,
                "source_artifact": "ratewall_assumption_mode_channel_status_crosswalk.csv",
                "ratio_layer": ratio_layer,
                "mode_class": (
                    "paper_design_only"
                    if ratio_layer == "inflation_wall"
                    else "assumption_mode_object"
                ),
                "channel_role": (
                    role
                    if price_sidecar
                    else (
                        "assumption_mode_sidecar_or_conditioner"
                        if sidecar
                        else "assumption_mode_channel"
                    )
                ),
                "enters_rw_y_numerator": _bool(
                    enters_num and status != "context_only"
                ),
                "enters_rw_y_denominator": _bool(enters_den),
                "enters_rw_pi_numerator": _bool(price_sidecar),
                "enters_rw_pi_denominator": "false",
                "enters_price_sidecar": _bool(sidecar),
                "enters_context_only": _bool(not sidecar),
                "forbidden_ratio_layers": (
                    "RW_Y" if price_sidecar else "canonical_RW_Y_without_source_gate"
                ),
                "source_status": item.get("proxy_source_gate_status", ""),
                "assumption_mode_status": item.get("promotion_status", ""),
                "promotion_status": item.get("promotion_status", ""),
                "double_count_risk": (
                    "price_sidecar_misclassified_as_real_demand"
                    if price_sidecar
                    else "requires_overlap_review_before_promotion"
                ),
                "safe_sentence": f"{channel_key} remains classified by Assumption Mode status.",
                "forbidden_sentence": f"{channel_key} is admitted as empirical RW_Y evidence.",
                "exact_blocker": item.get("next_gate_or_blocker", ""),
                "next_backend_action": "keep_channel_classified_until_source_gate_passes",
                "allowed_use": "channel_taxonomy_review_only",
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    # Keep lint happy about the offset in a way that documents intent.
    assert len(rows) >= offset
    return rows


def historical_interpretation_audit_rows(
    *,
    historical_wall_ratio_path_rows: list[dict[str, str]],
    historical_assumption_mode_wall_ratio_path_rows: list[dict[str, str]],
    historical_tdc_wall_ratio_path_rows: list[dict[str, str]],
    dynamic_scenario_family_registry_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use, blocked_use, claim_boundary = _common_boundary()
    groups: dict[tuple[str, str, str, str, str], list[Decimal]] = defaultdict(list)

    def add_rows(
        *,
        artifact: str,
        rows: list[dict[str, str]],
        ratio_field: str,
        denominator_basis: str,
        assumption_field: str,
        source_mode: str,
    ) -> None:
        for row in rows:
            quarter = row.get("quarter", "")
            period = _period_family(quarter) if quarter else "forward_scenario"
            assumption = row.get(assumption_field, "") or "not_applicable"
            value = _decimal(row.get(ratio_field, ""))
            key = (artifact, denominator_basis, assumption, period, source_mode)
            if value is not None:
                groups[key].append(value)

    add_rows(
        artifact="ratewall_historical_wall_ratio_path.csv",
        rows=historical_wall_ratio_path_rows,
        ratio_field="historical_wall_ratio",
        denominator_basis="actual_rate_level_sidecar",
        assumption_field="calibration_band",
        source_mode="diagnostic_sidecar",
    )
    add_rows(
        artifact="ratewall_historical_assumption_mode_wall_ratio_path.csv",
        rows=historical_assumption_mode_wall_ratio_path_rows,
        ratio_field="ratewall_offset_ratio_100bp_equivalent",
        denominator_basis="canonical_100bp_year",
        assumption_field="assumption_set",
        source_mode="assumption_mode_only",
    )
    add_rows(
        artifact="ratewall_historical_assumption_mode_wall_ratio_path.csv",
        rows=historical_assumption_mode_wall_ratio_path_rows,
        ratio_field="historical_assumption_mode_wall_ratio",
        denominator_basis="actual_rate_level_sidecar",
        assumption_field="assumption_set",
        source_mode="assumption_mode_sidecar",
    )
    add_rows(
        artifact="ratewall_historical_tdc_wall_ratio_path.csv",
        rows=historical_tdc_wall_ratio_path_rows,
        ratio_field="tdc_only_wall_ratio",
        denominator_basis="actual_rate_level_sidecar",
        assumption_field="calibration_band",
        source_mode="tdc_sidecar",
    )
    for row in dynamic_scenario_family_registry_rows:
        value = _decimal(row.get("max_ratewall_offset_ratio", ""))
        key = (
            "ratewall_dynamic_scenario_family_registry.csv",
            "dynamic_path_diagnostic",
            row.get("based_on_assumption_set", "") or "not_applicable",
            "forward_scenario",
            "assumption_mode_scenario",
        )
        if value is not None:
            groups[key].append(value)

    output_rows: list[dict[str, str]] = []
    for idx, (key, values) in enumerate(sorted(groups.items()), start=1):
        artifact, denominator_basis, assumption_case, period_family, source_mode = key
        ratio_min, ratio_max = _range_text(values)
        actual_sidecar = denominator_basis == "actual_rate_level_sidecar"
        covid = period_family == "covid_liquidity_regime"
        canonical_status = (
            "blocked_pending_admitted_denominator"
            if denominator_basis == "canonical_100bp_year"
            else "sidecar_diagnostic"
        )
        if denominator_basis == "dynamic_path_diagnostic":
            canonical_status = "assumption_mode_only"
        claim_id = f"historical_interpretation::{_slug(artifact)}::{_slug(assumption_case)}::{_slug(period_family)}::{_slug(denominator_basis)}"
        output_rows.append(
            {
                "historical_interpretation_audit_row_id": (
                    f"historical_interpretation_audit::{idx:04d}"
                ),
                "claim_id": claim_id,
                "claim_text": (
                    "Historical or scenario RateWall path can be interpreted only "
                    "within its denominator and source-mode label."
                ),
                "artifact_family": artifact.replace(".csv", ""),
                "artifact_name": artifact,
                "source_output_path": f"outputs/tables/{artifact}",
                "denominator_basis": denominator_basis,
                "assumption_case": assumption_case,
                "period_family": period_family,
                "reported_ratio_min": ratio_min,
                "reported_ratio_max": ratio_max,
                "source_mode_label": source_mode,
                "canonical_status": canonical_status,
                "support_status": (
                    "context_only"
                    if actual_sidecar or denominator_basis == "dynamic_path_diagnostic"
                    else "blocked_pending_denominator_admission"
                ),
                "historical_reporting_status": (
                    "not_canonical_history"
                    if actual_sidecar or denominator_basis == "dynamic_path_diagnostic"
                    else "canonical_basis_named_but_empirical_admission_blocked"
                ),
                "near_zero_denominator_flag": _bool(actual_sidecar and covid),
                "covid_liquidity_regime_flag": _bool(covid),
                "requires_100bp_denominator": _bool(actual_sidecar),
                "value_admission_status": (
                    "assumption_mode_or_sidecar_only_not_empirical_admission"
                ),
                "blocker": (
                    "actual_rate_or_dynamic_sidecar_not_canonical"
                    if actual_sidecar or denominator_basis == "dynamic_path_diagnostic"
                    else "canonical_100bp_basis_still_uses_assumption_mode_denominator"
                ),
                "safe_sentence": (
                    "This row may be cited only with its Assumption Mode or "
                    "sidecar denominator label."
                ),
                "forbidden_sentence": (
                    "This row proves a canonical historical RateWall wall hit."
                ),
                "enters_main_paper_claim": "false",
                "next_backend_action": (
                    "use_historical_interpretation_audit_before_paper_claim"
                ),
                "allowed_use": "historical_interpretation_audit_only",
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return output_rows


def tdc_equation_variant_registry_rows(
    *,
    tdc_double_count_guardrail_rows: list[dict[str, str]],
    tdc_deposit_pass_through_scenario_contract_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use, blocked_use, claim_boundary = _common_boundary()
    overlap_buckets = sorted(
        {
            row.get("allocation_bucket", "")
            for row in tdc_double_count_guardrail_rows
            if row.get("allocation_bucket", "")
        }
    )[:8]
    scenario_ids = sorted(
        {
            row.get("regime_scenario_id", "")
            for row in tdc_deposit_pass_through_scenario_contract_rows
            if row.get("regime_scenario_id", "")
        }
    )
    scenario_text = ";".join(scenario_ids[:8])
    default_source_artifacts = (
        "ratewall_tdc_double_count_guardrail.csv;"
        "ratewall_tdc_deposit_pass_through_scenario_contract.csv"
    )
    variants = [
        (
            "ru_flow_tier2_tdc_core_object",
            "central_tdc_object_family",
            "TDC_effect = RU_flow_Tier2_TDC_base * beta_deposit_pass_through_range",
            "RU-flow Tier 2 TDC remains the central TDC-family object for scenario estimates",
            "sign follows the RU-flow Tier 2 TDC estimate and scenario pass-through beta",
            "TDC-EST/EA-TDC source-backed RU-flow deposit pass-through ranges",
            "not_an_inclusion_gate_sensitivity_or_interpretation_only",
            "direct_interest_overlap_review_may_adjust_interpretation_not_drop_tdc",
            "route_proxy_sidecar_sensitivity_not_core_tdc_gate",
            "bank retained margin remains separate from depositor pass-through",
            "foreign leakage remains wrapper/context only",
            "central_assumption_mode_object",
            "replace_not_stack",
            "direct_interest;route_proxy;du_flow_shadow;bank_balance_sheet",
            (
                "ratewall_tdc_deposit_pass_through_source_import.csv;"
                "ratewall_tdcest_historical_estimator_bridge.csv;"
                "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv"
            ),
            "pass_central_tdc_object_family_assumption_mode_not_rw_y",
            "",
            "continue_source_backed_ru_flow_tdc_without_broad_du_flow_build",
        ),
        (
            "deposit_pass_through_then_demand_conversion",
            "positive_or_normal_tdc",
            "TDC_support = (TDC_base - direct_interest_overlap) * beta_deposit * demand_conversion",
            "Treasury-attributed liquidity/deposit component after direct-interest overlap review",
            "positive TDC can support deposits; negative TDC can drain support",
            "source-bound deposit-flow pass-through from EA-TDC/TDC surfaces",
            "blocked_missing_current_demand_conversion",
            "direct_interest_must_be_subtracted_or_replaced_not_stacked",
            "IORB/RRP/MMF channels require separate overlap wrappers",
            "bank retained margin is not current-demand support without bridge",
            "foreign leakage remains wrapper/context only",
            "positive_neutral_negative_regimes_review_only",
            "replace_not_stack",
            "direct_interest;iorb_rrp;mmf_tbill;bank_balance_sheet",
            default_source_artifacts,
            "blocked_tdc_equation_variant_not_rw_y_input",
            "blocked_missing_current_demand_conversion",
            "source_current_demand_conversion_overlap_and_trigger_validation",
        ),
        (
            "demand_relevant_pass_through_no_extra_conversion",
            "demand_relevant_pass_through_claim",
            "TDC_support = TDC_base * beta_demand_relevant",
            "TDC base if beta is proven to be final-demand relevant",
            "sign follows source-backed demand-relevant pass-through",
            "blocked: no demand-relevant pass-through beta admitted",
            "blocked_missing_source_that_beta_is_final_demand_relevant",
            "no additional current-demand conversion may be stacked",
            "IORB/RRP/MMF overlap still blocked",
            "bank balance-sheet effect remains separate",
            "foreign leakage remains wrapper/context only",
            "not_admitted",
            "replace_not_stack",
            "current_demand_conversion;direct_interest;holder_leakage",
            default_source_artifacts,
            "blocked_tdc_equation_variant_not_rw_y_input",
            "blocked_missing_source_that_beta_is_final_demand_relevant",
            "source_current_demand_conversion_overlap_and_trigger_validation",
        ),
        (
            "direct_interest_overlap_subtracted",
            "direct_interest_overlap",
            "TDC_support = TDC_base * beta - direct_interest_overlap",
            "TDC base with explicit direct Treasury-interest overlap subtraction",
            "positive TDC only after overlap subtraction",
            "deposit-flow pass-through only",
            "blocked_missing_overlap_quantification",
            "direct_interest_overlap_must_replace_not_stack",
            "MMF/T-bill rotation requires wrapper",
            "bank NIM is paired credit-supply context",
            "foreign leakage remains blocked for current-demand conversion",
            "review_only",
            "replace_not_stack",
            "direct_interest;treasury_interest;deposit_support",
            default_source_artifacts,
            "blocked_tdc_equation_variant_not_rw_y_input",
            "blocked_missing_overlap_quantification",
            "source_current_demand_conversion_overlap_and_trigger_validation",
        ),
        (
            "negative_tdc_regime",
            "negative_tdc_liquidity_drain",
            "TDC_effect = negative_TDC_base * beta * conversion_if_admitted",
            "Negative TDC regime rows are liquidity-drain diagnostics",
            "negative TDC cannot be forced to positive support",
            "source-bound regime sign required",
            "blocked_missing_runtime_trigger_validation",
            "overlap rules still apply",
            "RRP/MMF absorption can change sign and timing",
            "bank balance sheet may amplify or offset",
            "foreign leakage wrapper remains blocked",
            "negative_regime_review_only",
            "replace_not_stack",
            "regime_sign;trigger_validation;current_demand_conversion",
            default_source_artifacts,
            "blocked_tdc_equation_variant_not_rw_y_input",
            "blocked_missing_runtime_trigger_validation",
            "source_current_demand_conversion_overlap_and_trigger_validation",
        ),
    ]
    rows = []
    for idx, variant in enumerate(variants, start=1):
        (
            variant_id,
            overlap_bucket,
            equation_text,
            base_def,
            sign_rule,
            pass_basis,
            conversion_status,
            direct_overlap,
            iorb_overlap,
            bank_treatment,
            foreign_treatment,
            regime_sign,
            replace_semantics,
            exclusion_pairs,
            source_artifacts,
            admission_status,
            exact_blocker,
            next_backend_action,
        ) = variant
        is_core_tdc_object = variant_id == "ru_flow_tier2_tdc_core_object"
        safe_sentence = (
            "RU-flow Tier 2 TDC is the central TDC-family scenario object; "
            "route and final-recipient gaps affect sensitivity, not inclusion."
            if is_core_tdc_object
            else "TDC variants are formula guardrails and scenario design rows."
        )
        forbidden_sentence = (
            "A broad DU-flow build or final-recipient route proof is required "
            "before TDC can remain in the estimate."
            if is_core_tdc_object
            else (
                "TDC pass-through is admitted current-demand support without "
                "conversion and overlap gates."
            )
        )
        allowed_use_value = (
            "central_tdc_object_family_scenario_estimate_guardrail;"
            "pass_through_range_sensitivity"
            if is_core_tdc_object
            else "tdc_equation_variant_review_only"
        )
        rows.append(
            {
                "tdc_equation_variant_registry_row_id": (
                    f"tdc_equation_variant_registry::{idx:04d}"
                ),
                "tdc_variant_id": variant_id,
                "overlap_bucket": overlap_bucket,
                "equation_text": equation_text,
                "tdc_base_definition": base_def,
                "tdc_change_sign_rule": sign_rule,
                "deposit_pass_through_basis": pass_basis,
                "current_demand_conversion_status": conversion_status,
                "direct_interest_overlap_treatment": direct_overlap,
                "iorb_rrp_mmf_treatment": iorb_overlap,
                "bank_balance_sheet_treatment": bank_treatment,
                "foreign_leakage_treatment": foreign_treatment,
                "regime_sign": regime_sign,
                "replace_vs_stack_semantics": replace_semantics,
                "source_artifacts": source_artifacts,
                "source_status": (
                    f"review_only_overlap_buckets={';'.join(overlap_buckets)};"
                    f"scenario_ids={scenario_text}"
                ),
                "admission_status": admission_status,
                "allowed_for_rw_y": "false",
                "allowed_for_rw_pi": "false",
                "assumption_mode_only": "true",
                "double_count_exclusion_pairs": exclusion_pairs,
                "safe_sentence": safe_sentence,
                "forbidden_sentence": forbidden_sentence,
                "exact_blocker": exact_blocker,
                "next_backend_action": next_backend_action,
                "allowed_use": allowed_use_value,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_source_extraction_task_packet_rows(
    *,
    policy_path_field_evidence_resolution_queue_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows = []
    for idx, item in enumerate(policy_path_field_evidence_resolution_queue_rows, start=1):
        resolution_class = item.get("field_resolution_class", "")
        if resolution_class == "deeper_source_extraction_required":
            task_class = "source_extraction_task"
            parser_strategy = _parser_strategy(item.get("protocol_component", ""))
            extraction_status = "blocked_pending_field_specific_extraction"
            output_field = item.get("authored_field_name", "")
            blocker = "requires_exact_source_locator_quote_or_code_ref_and_hash"
        elif resolution_class == "independent_replication_target_design_required":
            task_class = "blocked_non_extraction_design_task"
            parser_strategy = "design_replication_target_tolerance_not_source_extraction"
            extraction_status = "blocked_non_extraction_replication_design_required"
            output_field = "independent_replication_target_tolerance"
            blocker = "requires_independent_replication_target_design"
        elif resolution_class == "explicit_authored_invariant_required":
            task_class = "blocked_authored_invariant_task"
            parser_strategy = "author_machine_invariant_not_source_extraction"
            extraction_status = "blocked_non_extraction_authored_invariant_required"
            output_field = item.get("authored_field_name", "")
            blocker = "requires_explicit_authored_invariant_and_failure_behavior"
        else:
            task_class = "alternate_source_search_task"
            parser_strategy = "locate_alternate_public_or_local_source"
            extraction_status = "blocked_pending_alternate_source_search"
            output_field = item.get("authored_field_name", "")
            blocker = "requires_alternate_source_search"

        rows.append(
            {
                "policy_path_source_extraction_task_packet_row_id": (
                    f"policy_path_source_extraction_task_packet::{idx:04d}"
                ),
                "field_evidence_resolution_queue_row_id": item.get(
                    "field_evidence_resolution_queue_row_id", ""
                ),
                "protocol_field_authoring_contract_row_id": item.get(
                    "protocol_field_authoring_contract_row_id", ""
                ),
                "protocol_component": item.get("protocol_component", ""),
                "protocol_component_gate": item.get("protocol_component_gate", ""),
                "authored_field_name": item.get("authored_field_name", ""),
                "authored_field_label": item.get("authored_field_label", ""),
                "field_resolution_class": resolution_class,
                "field_resolution_status": item.get("field_resolution_status", ""),
                "task_class": task_class,
                "source_artifact_path": item.get("source_specific_artifacts", ""),
                "source_locator_required": item.get(
                    "required_row_level_provenance", ""
                ),
                "linked_source_hit_row_ids": item.get("linked_source_hit_row_ids", ""),
                "linked_source_snippet_sample": item.get(
                    "linked_source_snippet_sample", ""
                ),
                "linked_no_hit_row_ids": item.get("linked_no_hit_row_ids", ""),
                "parser_strategy": parser_strategy,
                "required_row_or_line_ref": (
                    "source_quote_or_code_line_or_workbook_cell_required"
                ),
                "evidence_acceptance_test": (
                    "pass_status_value_allowed_only_when_source_hash_locator_"
                    "and_machine_audit_field_are_populated"
                ),
                "output_field_to_fill": output_field,
                "pass_status_value": item.get("pass_status_value", ""),
                "blocked_status_value": item.get("blocked_status_value", ""),
                "extraction_status": extraction_status,
                "extraction_blocker": blocker,
                "next_backend_action": f"{task_class}::{item.get('authored_field_name', '')}",
                "promotion_grade_evidence_status": (
                    "blocked_task_packet_not_promotion_grade"
                ),
                "protocol_admission_status": (
                    "blocked_task_packet_not_complete_bps_year_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "allowed_use": "policy_path_source_extraction_task_packet_only",
                "blocked_use": (
                    "bps_year_policy_path;denominator_prior;main_ratio;"
                    "Evidence_Mode;pricing;holder_allocation;raw_rate_shock;"
                    "reset_calendar;empirical_threshold"
                ),
                "claim_boundary": (
                    "policy_path_source_extraction_task_packet_not_bps_year_or_runtime_input"
                ),
                **_false_fields(),
            }
        )
    return rows


def policy_path_source_extraction_results_rows(
    *,
    policy_path_source_extraction_task_packet_rows: list[dict[str, str]],
    policy_path_protocol_missing_evidence_parse_execution_review_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    parse_by_id = {
        row["missing_evidence_parse_execution_review_row_id"]: row
        for row in policy_path_protocol_missing_evidence_parse_execution_review_rows
    }
    rows = []
    allowed_use = "policy_path_source_extraction_execution_review_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_source_extraction_results_not_bps_year_or_runtime_input"
    )
    for idx, task in enumerate(policy_path_source_extraction_task_packet_rows, start=1):
        hit_ids = _parts(task.get("linked_source_hit_row_ids", ""))
        no_hit_ids = _parts(task.get("linked_no_hit_row_ids", ""))
        linked_parse_rows = [parse_by_id[row_id] for row_id in hit_ids if row_id in parse_by_id]
        source_paths = _join_unique(
            [
                value
                for row in linked_parse_rows
                for value in _parts(row.get("source_artifact_paths", ""))
            ]
            or _parts(task.get("source_artifact_path", ""))
        )
        source_sha256s = _join_unique(
            [
                value
                for row in linked_parse_rows
                for value in _parts(row.get("source_artifact_sha256s", ""))
            ]
        )
        computed_sha256s = _join_unique(
            [
                value
                for row in linked_parse_rows
                for value in _parts(row.get("computed_source_artifact_sha256s", ""))
            ]
        )
        snippet = _short_join(
            [
                row.get("target_parse_snippet_sample", "")
                for row in linked_parse_rows
                if row.get("target_parse_snippet_sample", "")
            ]
            or [task.get("linked_source_snippet_sample", "")]
        )
        review_only_count = sum(
            "review_only" in row.get("target_parse_status", "")
            or "not_promotion_grade" in row.get("promotion_grade_evidence_status", "")
            for row in linked_parse_rows
        )
        promotion_grade_count = sum(
            row.get("promotion_grade_evidence_status", "").startswith("pass_")
            for row in linked_parse_rows
        )
        if task.get("task_class") == "source_extraction_task":
            execution_class = "source_extraction_review_completed_fail_closed"
            parser_execution_status = (
                "pass_review_sources_parsed_but_promotion_grade_evidence_absent"
                if linked_parse_rows
                else "blocked_no_linked_parse_execution_rows"
            )
            source_locator_status = (
                "pass_hash_backed_source_locators_present_review_only"
                if source_paths and source_sha256s
                else "blocked_missing_hash_backed_source_locator"
            )
            quote_status = (
                "blocked_review_only_snippets_not_field_admission"
                if snippet
                else "blocked_no_source_quote_or_structured_evidence"
            )
            extracted_status = (
                "blocked_review_only_hit_not_promotion_grade"
                if review_only_count
                else "blocked_no_promotion_grade_source_hit"
            )
            field_status = "blocked_source_extraction_result_not_admitted"
            blocker = (
                f"{task.get('authored_field_name', '')} has "
                f"{len(linked_parse_rows)} linked hash-backed parse rows and "
                f"{review_only_count} review-only hit rows, but no promotion-grade "
                "source locator, row/line reference, authored pass rule, and "
                "machine-audited field value combination."
            )
            next_action = (
                "author_field_specific_source_locator_or_record_terminal_no_hit"
            )
        elif task.get("task_class") == "blocked_non_extraction_design_task":
            execution_class = "blocked_non_extraction_replication_design_preserved"
            parser_execution_status = "not_applicable_replication_design_task"
            source_locator_status = "blocked_replication_target_design_not_extraction"
            quote_status = "not_applicable_non_extraction_design_task"
            extracted_status = "blocked_non_extraction_design_task_no_field_value"
            field_status = "blocked_replication_design_required"
            blocker = task.get("extraction_blocker", "")
            next_action = "design_independent_replication_target_tolerance_surface"
        else:
            execution_class = "blocked_authored_invariant_preserved"
            parser_execution_status = "not_applicable_authored_invariant_task"
            source_locator_status = "blocked_authored_invariant_not_source_extraction"
            quote_status = "not_applicable_authored_invariant_task"
            extracted_status = "blocked_authored_invariant_task_no_field_value"
            field_status = "blocked_explicit_authored_invariant_required"
            blocker = task.get("extraction_blocker", "")
            next_action = "author_machine_testable_invariant_before_promotion"

        sha_set = set(_parts(source_sha256s))
        computed_sha_set = set(_parts(computed_sha256s))
        rows.append(
            {
                "policy_path_source_extraction_result_row_id": (
                    f"policy_path_source_extraction_result::{idx:04d}"
                ),
                "policy_path_source_extraction_task_packet_row_id": task.get(
                    "policy_path_source_extraction_task_packet_row_id", ""
                ),
                "field_evidence_resolution_queue_row_id": task.get(
                    "field_evidence_resolution_queue_row_id", ""
                ),
                "protocol_field_authoring_contract_row_id": task.get(
                    "protocol_field_authoring_contract_row_id", ""
                ),
                "protocol_component": task.get("protocol_component", ""),
                "protocol_component_gate": task.get("protocol_component_gate", ""),
                "authored_field_name": task.get("authored_field_name", ""),
                "task_class": task.get("task_class", ""),
                "task_execution_class": execution_class,
                "source_artifact_paths": source_paths,
                "source_artifact_sha256s": source_sha256s,
                "computed_source_artifact_sha256s": computed_sha256s,
                "hash_verification_status": (
                    "pass_source_artifact_sha256_verified_review_only"
                    if sha_set and sha_set == computed_sha_set
                    else "blocked_missing_or_unmatched_source_hash"
                ),
                "linked_source_hit_row_ids": task.get("linked_source_hit_row_ids", ""),
                "linked_no_hit_row_ids": task.get("linked_no_hit_row_ids", ""),
                "linked_source_hit_count": str(len(hit_ids)),
                "linked_no_hit_count": str(len(no_hit_ids)),
                "review_only_hit_count": str(review_only_count),
                "promotion_grade_hit_count": str(promotion_grade_count),
                "parser_strategy": task.get("parser_strategy", ""),
                "parser_execution_status": parser_execution_status,
                "source_locator_status": source_locator_status,
                "source_row_or_line_ref_status": (
                    "blocked_source_quote_or_workbook_cell_not_yet_bound_to_"
                    "field_level_pass_rule"
                ),
                "source_quote_or_structured_evidence": snippet,
                "source_quote_support_status": quote_status,
                "extracted_field_name": task.get("output_field_to_fill", ""),
                "extracted_field_value": "",
                "extracted_field_status": extracted_status,
                "pass_status_value": task.get("pass_status_value", ""),
                "blocked_status_value": task.get("blocked_status_value", ""),
                "field_execution_status": field_status,
                "field_execution_blocker": blocker,
                "protocol_admission_status": (
                    "blocked_source_extraction_results_not_complete_bps_year_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                "next_backend_action": next_action,
                **_false_fields(),
            }
        )
    return rows


_POLICY_PATH_MACHINE_AUDITED_FIELD_DECISIONS = {
    "source_cell_unit_sign__effective_contract_family_by_era": {
        "required_tokens": (
            "Eurodollar futures",
            "SOFR futures",
            "We recommend using SOFR futures from",
        ),
        "source_row_or_cell": (
            "fed_sofr_continuity_landing_page.html::text_line=310;"
            "fed_sofr_continuity_2024034pap.pdf::pdf_page=2::text_line=5-10"
        ),
        "source_literal_value": (
            "Eurodollar futures were the bedrock for constructing high-frequency "
            "monetary policy surprises; the source recommends using SOFR "
            "futures from January 2022 onward."
        ),
        "parsed_value": "Eurodollar_before_2022;SOFR_from_January_2022_onward",
        "parsed_unit": "contract_family_by_era",
        "parsed_sign": "not_applicable_contract_family_field",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "join_contract_family_field_to_event_grid_and_bps_year_protocol"
        ),
    },
    "source_cell_unit_sign__literal_na_handling": {
        "required_tokens": ("data <- na.omit(data)", "NA"),
        "source_row_or_cell": (
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=58;"
            "sf_fed_monetary_policy_surprises.zip::mps.csv::line=2-8"
        ),
        "source_literal_value": (
            "mps.R line 58 applies data <- na.omit(data); mps.csv early "
            "rows contain NA values in the PC column."
        ),
        "parsed_value": "drop_rows_with_missing_source_inputs_via_na_omit",
        "parsed_unit": "missing_value_handling_rule",
        "parsed_sign": "not_applicable_na_handling_field",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "preserve_na_rule_in_replication_without_promoting_bps_year_output"
        ),
    },
    "source_cell_unit_sign__percentage_point_basis_point_conversion": {
        "required_tokens": ("percentage points",),
        "source_row_or_cell": (
            "sf_fed_usmpd_landing_page.html::text_line=83;"
            "sf_fed_monetary_policy_surprises.zip::README.md::line=21-23"
        ),
        "source_literal_value": (
            "USMPD high-frequency interest-rate changes and MPS outputs are "
            "measured in percentage points."
        ),
        "parsed_value": (
            "source_rate_changes_percentage_points;review_only_bps_multiplier=100"
        ),
        "parsed_unit": "percentage_points",
        "parsed_sign": "positive_source_rate_change_not_admitted_tightening_path",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "use_only_after_source_sign_event_grid_and_bps_year_formula_pass"
        ),
    },
    "source_cell_unit_sign__price_to_rate_sign_transform": {
        "required_tokens": ("rate changes", "percentage points"),
        "source_row_or_cell": (
            "sf_fed_monetary_policy_surprises_description_sheet.csv::"
            "description_row_number=18-20;"
            "sf_fed_monetary_policy_surprises_description_sheet.csv::"
            "description_row_number=34-37;"
            "sf_fed_monetary_policy_surprises.zip::README.md::line=21-23;"
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=57"
        ),
        "source_literal_value": (
            "The SF Fed workbook description says monetary policy surprises "
            "are measured using interest rate changes over 30-minute windows; "
            "FF1/FF2 and ED1-ED4 are intradaily market responses, with ED "
            "columns becoming SOFR futures changes from January 2023. The "
            "README states the underlying high-frequency money market futures "
            "rate changes are percentage points, and mps.R labels MP1, MP2, "
            "ED2-ED4 as intraday rate changes."
        ),
        "parsed_value": (
            "source_cells_are_reported_rate_changes_not_raw_futures_prices"
        ),
        "parsed_unit": "percentage_points",
        "parsed_sign": (
            "positive_reported_source_cell_is_positive_rate_change_"
            "tightening_direction_review_only"
        ),
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "use_source_reported_rate_change_sign_only_after_full_policy_path_protocol_passes"
        ),
    },
    "source_cell_unit_sign__source_instrument_code": {
        "required_tokens": ("MP1", "MP2", "FF1", "ED1", "ED2", "OIS1Y", "UST2Y"),
        "source_row_or_cell": (
            "sf_fed_usmpd.xlsx::Statements!E1;sf_fed_usmpd.xlsx::Statements!F1;"
            "sf_fed_usmpd.xlsx::Statements!G1;sf_fed_usmpd.xlsx::Statements!M1;"
            "sf_fed_usmpd.xlsx::Statements!N1;sf_fed_usmpd.xlsx::Statements!U1;"
            "sf_fed_usmpd.xlsx::Statements!Y1"
        ),
        "source_literal_value": "MP1;MP2;FF1;ED1;ED2;OIS1Y;UST2Y",
        "parsed_value": "MP1;MP2;FF1;ED1;ED2;OIS1Y;UST2Y",
        "parsed_unit": "source_instrument_code",
        "parsed_sign": "not_applicable_instrument_code_field",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "join_instrument_codes_to_source_unit_sign_and_event_grid"
        ),
    },
    "source_cell_unit_sign__source_workbook_cell_unit": {
        "required_tokens": (
            "intraday rate changes",
            "underlying high-frequency money market futures",
        ),
        "source_row_or_cell": (
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=57;"
            "sf_fed_monetary_policy_surprises.zip::README.md::line=21-23"
        ),
        "source_literal_value": (
            "mps.R describes MP1, MP2, ED2-ED4 as intraday rate changes; "
            "README states the underlying futures rate changes are percentage points."
        ),
        "parsed_value": "MP1;MP2;ED2;ED3;ED4_source_intraday_rate_changes",
        "parsed_unit": "percentage_points",
        "parsed_sign": "positive_source_rate_change_not_admitted_tightening_path",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "bind_source_unit_to_sign_and_policy_path_normalization"
        ),
    },
    "bps_year_formula__horizon_weights": {
        "required_tokens": ("one-year", "MP1", "MP2", "ED2", "ED3", "ED4"),
        "source_row_or_cell": (
            "ratewall_policy_path_contract_interval_source_review.csv::"
            "reference_period_start;reference_period_end;"
            "reference_period_year_fraction;event_overlap_year_fraction"
        ),
        "source_literal_value": (
            "Existing contract-interval review rows carry reference periods "
            "and event-overlap year fractions, but every row keeps "
            "bps_year_integration_status blocked because no reviewed "
            "bps-year integration formula is admitted; current acquired "
            "sources do not author a RateWall bps-year horizon-weight protocol."
        ),
        "parsed_value": (
            "terminal_current_source_bundle_no_source_authored_bps_year_horizon_weights"
        ),
        "parsed_unit": "review_only_year_fraction_metadata_not_bps_year_weight",
        "parsed_sign": "not_applicable_horizon_weight_gap",
        "machine_audit_status": (
            "blocked_machine_audited_terminal_no_source_authored_bps_year_horizon_weights"
        ),
        "source_evidence_status": (
            "blocked_machine_audited_terminal_no_source_authored_bps_year_horizon_weights"
        ),
        "field_gate_status": (
            "blocked_machine_audited_terminal_no_source_authored_bps_year_formula"
        ),
        "next_action_if_blocked": (
            "do_not_requery_current_bundle_for_bps_year_formula_acquire_new_source_family_or_keep_protocol_blocked"
        ),
    },
    "bps_year_formula__rate_change_unit_conversion": {
        "required_tokens": ("percentage points",),
        "source_row_or_cell": (
            "sf_fed_usmpd_landing_page.html::text_line=83;"
            "sf_fed_monetary_policy_surprises.zip::README.md::line=21-23"
        ),
        "source_literal_value": (
            "Source rate changes and daily one-year Treasury yield changes are "
            "percentage points; review-only conversion to bps is multiplier 100."
        ),
        "parsed_value": "percentage_points_to_basis_points_multiplier_100_review_only",
        "parsed_unit": "percentage_points_to_basis_points",
        "parsed_sign": "positive_source_rate_change_not_admitted_tightening_path",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "do_not_use_unit_conversion_until_horizon_weights_and_sign_pass"
        ),
    },
    "bps_year_formula__sign_convention": {
        "required_tokens": (
            "dy1 = SVENY01",
            'mutate(MPS = coef(model)["PC1"] * PC1)',
        ),
        "source_row_or_cell": (
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=41;"
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=77-79"
        ),
        "source_literal_value": (
            "dy1 is SVENY01 minus its lag; MPS equals coef(model)[\"PC1\"] "
            "times PC1 from lm(dy1 ~ PC1)."
        ),
        "parsed_value": (
            "MPS_scaled_by_regression_on_daily_one_year_treasury_yield_change"
        ),
        "parsed_unit": "percentage_points_one_year_yield_normalized",
        "parsed_sign": "positive_mps_aligned_to_positive_one_year_yield_change",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "do_not_treat_yield_sign_as_admitted_bps_year_tightening_path"
        ),
    },
    "event_date_horizon_grid__contract_reference_interval": {
        "required_tokens": ("date_time", "ED1", "ED2", "SOFR futures"),
        "source_row_or_cell": (
            "ratewall_policy_path_contract_interval_source_review.csv::"
            "event_date;event_time;candidate_instrument_code;"
            "reference_period_start;reference_period_end;"
            "reference_period_year_fraction"
        ),
        "source_literal_value": (
            "Contract-interval source review rows carry event dates, event "
            "times, instrument codes, reference-period start/end dates, and "
            "reference-period year fractions from hash-backed source/context "
            "surfaces. The rows remain review-only and not bps-year protocol "
            "admission."
        ),
        "parsed_value": (
            "contract_reference_intervals_reviewed_nonpromotional_not_bps_year_admission"
        ),
        "parsed_unit": "calendar_date;year_fraction_review_only",
        "parsed_sign": "not_applicable_contract_interval_field",
        "machine_audit_status": (
            "pass_machine_audited_contract_interval_metadata_nonpromotional"
        ),
        "source_evidence_status": (
            "pass_machine_audited_contract_interval_metadata_nonpromotional"
        ),
        "field_gate_status": (
            "blocked_machine_audited_contract_interval_metadata_not_bps_year_protocol"
        ),
        "next_action_if_blocked": (
            "source_or_execute_bps_year_formula_and_replication_before_interval_use"
        ),
    },
    "event_date_horizon_grid__event_date": {
        "required_tokens": ("Date", "date_time"),
        "source_row_or_cell": (
            "sf_fed_usmpd.xlsx::Statements!A1:B2;"
            "sf_fed_usmpd.xlsx::Press Conferences!A1:B2;"
            "sf_fed_usmpd.xlsx::Monetary Events!A1:B2;"
            "sf_fed_usmpd.xlsx::Minutes!A1:B2"
        ),
        "source_literal_value": (
            "event sheets carry Date and date_time columns; example rows include "
            "Statements!A2=1994-02-04 and Statements!B2=1994-02-04 11:05:00."
        ),
        "parsed_value": "USMPD_event_Date_and_date_time_columns",
        "parsed_unit": "calendar_date;intraday_timestamp",
        "parsed_sign": "not_applicable_event_date_field",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "join_event_timestamps_to_policy_path_horizon_start_end_grid"
        ),
    },
    "event_date_horizon_grid__event_specific_horizon_start_end_dates": {
        "required_tokens": ("date_time", "SOFR futures"),
        "source_row_or_cell": (
            "ratewall_policy_path_contract_interval_source_review.csv::"
            "event_id;event_date;event_time;reference_period_start;"
            "reference_period_end;event_overlap_days;event_overlap_year_fraction"
        ),
        "source_literal_value": (
            "Contract-interval review rows carry event-specific dates/times, "
            "reference-period start/end dates, overlap days, and overlap year "
            "fractions. They do not admit a policy-path horizon grid or "
            "bps-year formula."
        ),
        "parsed_value": (
            "event_specific_interval_dates_reviewed_nonpromotional_not_policy_path_grid_admission"
        ),
        "parsed_unit": "calendar_date;days;year_fraction_review_only",
        "parsed_sign": "not_applicable_event_interval_date_field",
        "machine_audit_status": (
            "pass_machine_audited_event_interval_dates_nonpromotional"
        ),
        "source_evidence_status": (
            "pass_machine_audited_event_interval_dates_nonpromotional"
        ),
        "field_gate_status": (
            "blocked_machine_audited_event_interval_dates_not_bps_year_protocol"
        ),
        "next_action_if_blocked": (
            "source_or_execute_bps_year_formula_and_replication_before_grid_use"
        ),
    },
    "event_date_horizon_grid__event_window": {
        "required_tokens": ("30-minute windows", "four different types of event windows"),
        "source_row_or_cell": (
            "sf_fed_usmpd_landing_page.html::text_line=69-79;"
            "sf_fed_usmpd.xlsx::README!C12"
        ),
        "source_literal_value": (
            "USMPD records high-frequency changes over four event-window types, "
            "including 30-minute statement and minutes windows."
        ),
        "parsed_value": (
            "statement_30_minute;press_conference_window;monetary_event_window;"
            "minutes_30_minute"
        ),
        "parsed_unit": "intraday_event_window",
        "parsed_sign": "not_applicable_event_window_field",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "join_event_windows_to_horizon_grid_and_bps_year_integration"
        ),
    },
    "loading_back_transform__factor_definition": {
        "required_tokens": ("prcomp", "data$PC1 <- pca_result$x[,1]"),
        "source_row_or_cell": (
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=59-63"
        ),
        "source_literal_value": (
            "PC1 is the first principal component from prcomp over source "
            "rate-change columns with scale = TRUE."
        ),
        "parsed_value": "PC1_first_principal_component_scaled_source_rate_changes",
        "parsed_unit": "scaled_principal_component",
        "parsed_sign": "unoriented_pc1_before_one_year_yield_normalization",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "join_factor_definition_to_source_unit_and_replication_target"
        ),
    },
    "loading_back_transform__instrument_loadings": {
        "required_tokens": ("MP1", "MP2", "ED2", "ED3", "ED4"),
        "source_row_or_cell": (
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=49;"
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=57;"
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=106"
        ),
        "source_literal_value": (
            "mps.R selects Date, MP1, MP2, ED2, ED3, ED4 for statement "
            "surprises and excludes MP1 for minutes because it is identically zero."
        ),
        "parsed_value": "MP1;MP2;ED2;ED3;ED4;minutes_exclude_MP1",
        "parsed_unit": "source_rate_change_inputs_percentage_points",
        "parsed_sign": "positive_source_rate_change_not_admitted_tightening_path",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "derive_or_source_loadings_without_promoting_policy_path_cells"
        ),
    },
    "loading_back_transform__rotation_sign_rule": {
        "required_tokens": (
            "dy1 = SVENY01",
            'mutate(MPS = coef(model)["PC1"] * PC1)',
        ),
        "source_row_or_cell": (
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=41;"
            "sf_fed_monetary_policy_surprises.zip::mps.R::line=77-79"
        ),
        "source_literal_value": (
            "MPS orientation is set by regressing daily one-year Treasury "
            "yield changes on PC1 and multiplying PC1 by the fitted coefficient."
        ),
        "parsed_value": "MPS_equals_lm_dy1_on_PC1_coefficient_times_PC1",
        "parsed_unit": "one_year_treasury_yield_normalized_percentage_points",
        "parsed_sign": "positive_mps_aligned_to_positive_one_year_yield_change",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "replicate_rotation_without_treating_scalar_mps_as_bps_year_path"
        ),
    },
    "loading_back_transform__scalar_to_cell_back_transform": {
        "required_tokens": (
            'mutate(MPS = coef(model)["PC1"] * PC1)',
            "select(Date, MPS)",
        ),
        "source_row_or_cell": (
            "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv::"
            "input_mean_percentage_points;input_sd_percentage_points;"
            "pc1_loading;dy1_regression_pc1_coef;source_mps_match_status"
        ),
        "source_literal_value": (
            "PCA loading/back-transform review rows reproduce source MPS "
            "within tolerance and expose PC1 loadings, input means/scales, "
            "and one-year-yield normalization coefficients. They remain "
            "review-only and do not supply a bps-year path."
        ),
        "parsed_value": (
            "pca_loading_and_scalar_mps_backtransform_reviewed_not_event_path_backtransform"
        ),
        "parsed_unit": "percentage_points_review_only_pca_loading_metadata",
        "parsed_sign": "positive_mps_aligned_to_positive_one_year_yield_change",
        "machine_audit_status": (
            "pass_machine_audited_pca_loading_backtransform_nonpromotional"
        ),
        "source_evidence_status": (
            "pass_machine_audited_pca_loading_backtransform_nonpromotional"
        ),
        "field_gate_status": (
            "blocked_machine_audited_backtransform_review_only_not_bps_year_path"
        ),
        "next_action_if_blocked": (
            "source_event_level_path_backtransform_and_bps_year_formula_before_use"
        ),
    },
    "loading_back_transform__source_code_replication_command": {
        "required_tokens": ('source("mps.R")',),
        "source_row_or_cell": (
            "sf_fed_monetary_policy_surprises.zip::README.md::line=10-16"
        ),
        "source_literal_value": (
            "README instructs users to download USMPD.xlsx, set the working "
            "directory with mps.R, and run source(\"mps.R\")."
        ),
        "parsed_value": 'source("mps.R")',
        "parsed_unit": "R_command",
        "parsed_sign": "not_applicable_replication_command_field",
        "machine_audit_status": "pass_machine_audited_field_value_nonpromotional",
        "source_evidence_status": "pass_machine_audited_field_value_nonpromotional",
        "field_gate_status": (
            "blocked_machine_audited_field_value_sibling_gates_incomplete"
        ),
        "next_action_if_blocked": (
            "turn_source_command_into_independent_replication_target_and_hash"
        ),
    },
}


def _machine_audited_policy_path_field_decision(
    *,
    authored_field_name: str,
    source_row_or_cell: str,
    source_literal_value: str,
    parsed_value: str,
) -> dict[str, str]:
    decision = _POLICY_PATH_MACHINE_AUDITED_FIELD_DECISIONS.get(authored_field_name)
    if not decision:
        return {}
    audit_text = ";".join([source_row_or_cell, source_literal_value, parsed_value])
    missing_tokens = [
        token for token in decision["required_tokens"] if token not in audit_text
    ]
    if missing_tokens:
        return {
            "parsed_value": parsed_value,
            "parsed_unit": "",
            "parsed_sign": "",
            "machine_audit_status": (
                "blocked_machine_audit_expected_source_tokens_missing"
            ),
            "source_evidence_status": (
                "blocked_machine_audit_expected_source_tokens_missing"
            ),
            "field_gate_status": (
                "blocked_machine_audit_expected_source_tokens_missing"
            ),
            "next_action_if_blocked": (
                "rerun_source_locator_binding_before_machine_audit_resolution"
            ),
        }
    return {
        key: value
        for key, value in decision.items()
        if key != "required_tokens"
    }


def policy_path_source_extraction_result_adjudication_rows(
    *,
    policy_path_source_extraction_task_packet_rows: list[dict[str, str]],
    policy_path_source_extraction_results_rows: list[dict[str, str]],
    policy_path_locator_candidate_pass_rule_review_decision_packet_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    result_by_task_id = {
        row.get("policy_path_source_extraction_task_packet_row_id", ""): row
        for row in policy_path_source_extraction_results_rows
    }
    locator_by_field_name = {
        row.get("authored_field_name", ""): row
        for row in policy_path_locator_candidate_pass_rule_review_decision_packet_rows
    }
    allowed_use = "policy_path_source_extraction_result_adjudication_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_source_extraction_result_adjudication_not_bps_year_or_runtime_input"
    )
    rows: list[dict[str, str]] = []
    for idx, task in enumerate(policy_path_source_extraction_task_packet_rows, start=1):
        result = result_by_task_id.get(
            task.get("policy_path_source_extraction_task_packet_row_id", ""), {}
        )
        locator = locator_by_field_name.get(task.get("authored_field_name", ""), {})
        task_class = task.get("task_class", "")
        locator_review_class = locator.get("pass_rule_review_class", "")
        if task_class == "source_extraction_task":
            if locator_review_class == "nonpromotional_locator_candidate_review_pass":
                source_status = (
                    "review_only_hash_backed_locator_candidate_not_promotion_grade"
                )
                field_gate_status = (
                    "blocked_locator_review_pass_not_protocol_evidence"
                )
                reviewer_status = locator.get("locator_candidate_review_status", "")
                machine_status = (
                    "blocked_no_machine_audited_source_field_value"
                )
                next_action = (
                    "convert_locator_candidate_to_machine_audited_field_value_or_block"
                )
            elif locator_review_class == "locator_candidate_review_fail_no_hit":
                source_status = "blocked_no_hit"
                field_gate_status = "blocked_no_locator_candidate_available"
                reviewer_status = locator.get("locator_candidate_review_status", "")
                machine_status = "blocked_no_source_locator_to_audit"
                next_action = "record_terminal_no_hit_or_find_alternate_source"
            else:
                source_status = "blocked_manual_auth_required"
                field_gate_status = (
                    "blocked_manual_authenticated_or_new_source_family_required"
                )
                reviewer_status = locator.get("locator_candidate_review_status", "")
                machine_status = "blocked_no_downloaded_source_for_machine_audit"
                next_action = (
                    "complete_manual_authenticated_or_new_source_family_acquisition"
                )
        elif task_class == "blocked_non_extraction_design_task":
            source_status = "blocked_independent_replication_design_task"
            field_gate_status = "blocked_independent_replication_design_required"
            reviewer_status = "not_applicable_non_extraction_replication_design_task"
            machine_status = "blocked_independent_replication_target_not_executed"
            next_action = "implement_independent_replication_target_tolerance"
        else:
            source_status = "blocked_authored_invariant_task"
            field_gate_status = "blocked_authored_fail_closed_invariant_required"
            reviewer_status = "not_applicable_authored_invariant_task"
            machine_status = "blocked_authored_invariant_not_executed"
            next_action = "implement_authored_fail_closed_invariant_audit"

        source_row_or_cell = locator.get("candidate_source_locations", "")
        source_literal_value = locator.get(
            "candidate_snippet_or_cell_or_code_line",
            result.get("source_quote_or_structured_evidence", ""),
        )
        parsed_value = locator.get("candidate_parsed_value_review_only", "")
        parsed_unit = ""
        parsed_sign = ""
        source_family = locator.get("target_source_family", "")
        source_path = locator.get(
            "candidate_source_artifact_paths",
            result.get("source_artifact_paths", ""),
        )
        source_sha256 = locator.get(
            "candidate_source_artifact_sha256s",
            result.get("source_artifact_sha256s", ""),
        )
        computed_source_sha256 = result.get("computed_source_artifact_sha256s", "")
        if (
            task_class == "source_extraction_task"
            and locator_review_class == "nonpromotional_locator_candidate_review_pass"
        ):
            machine_decision = _machine_audited_policy_path_field_decision(
                authored_field_name=task.get("authored_field_name", ""),
                source_row_or_cell=source_row_or_cell,
                source_literal_value=source_literal_value,
                parsed_value=parsed_value,
            )
            if machine_decision:
                source_status = machine_decision["source_evidence_status"]
                field_gate_status = machine_decision["field_gate_status"]
                machine_status = machine_decision["machine_audit_status"]
                next_action = machine_decision["next_action_if_blocked"]
                source_row_or_cell = machine_decision.get(
                    "source_row_or_cell", source_row_or_cell
                )
                source_literal_value = machine_decision.get(
                    "source_literal_value", source_literal_value
                )
                parsed_value = machine_decision.get("parsed_value", parsed_value)
                parsed_unit = machine_decision.get("parsed_unit", "")
                parsed_sign = machine_decision.get("parsed_sign", "")

        if (
            task.get("authored_field_name", "")
            == "source_cell_unit_sign__price_to_rate_sign_transform"
            and task_class == "source_extraction_task"
        ):
            machine_decision = _POLICY_PATH_MACHINE_AUDITED_FIELD_DECISIONS[
                "source_cell_unit_sign__price_to_rate_sign_transform"
            ]
            source_family = "sf_fed_mps_source_reported_rate_change_sign_unit"
            source_path = (
                "data/raw/policy_path_protocol_sources/"
                "sf_fed_monetary_policy_surprises_description_sheet.csv;"
                "data/raw/policy_path_source_author_web_acquisition_attempts/"
                "sf_fed_monetary_policy_surprises.zip"
            )
            source_sha256 = (
                "92a3e9b1fdbb6123beb0c09cf4fdf0506b86897200ce713da7a83edb42d4a2ee;"
                "8b16f20166c39f958639cc896eca4ba3aeaa162f1630b32cf41ce2daf9bd9960"
            )
            computed_source_sha256 = source_sha256
            source_row_or_cell = machine_decision["source_row_or_cell"]
            source_literal_value = machine_decision["source_literal_value"]
            parsed_value = machine_decision["parsed_value"]
            parsed_unit = machine_decision["parsed_unit"]
            parsed_sign = machine_decision["parsed_sign"]
            machine_status = machine_decision["machine_audit_status"]
            source_status = machine_decision["source_evidence_status"]
            field_gate_status = machine_decision["field_gate_status"]
            reviewer_status = (
                "pass_machine_audited_source_context_resolution_without_locator_candidate"
            )
            next_action = machine_decision["next_action_if_blocked"]

        if task.get("authored_field_name", "") in {
            "bps_year_formula__aggregation_formula",
            "bps_year_formula__bps_year_component_formula",
        }:
            source_family = "source_authored_bps_year_integral_formula_current_bundle"
            source_path = result.get("source_artifact_paths", source_path)
            source_sha256 = result.get("source_artifact_sha256s", source_sha256)
            computed_source_sha256 = result.get(
                "computed_source_artifact_sha256s", computed_source_sha256
            )
            source_row_or_cell = (
                "ratewall_policy_path_protocol_candidate_draft_review.csv::"
                "source_parse_or_acquisition_action;"
                "required_next_artifact_or_protocol;exact_blocker"
            )
            source_literal_value = (
                "Hash-backed current source bundle contains review-only one-year "
                "policy-path snippets and contract reference-interval metadata, "
                "but no source-authored bps-year aggregation or component formula."
            )
            parsed_value = (
                "terminal_current_source_bundle_no_source_authored_bps_year_formula"
            )
            parsed_unit = "not_applicable_terminal_no_source_authored_bps_year_formula"
            parsed_sign = "not_applicable_formula_absent"
            machine_status = (
                "blocked_machine_audited_terminal_no_source_authored_bps_year_formula"
            )
            source_status = (
                "blocked_machine_audited_terminal_no_source_authored_bps_year_formula"
            )
            field_gate_status = (
                "blocked_machine_audited_terminal_no_source_authored_bps_year_formula"
            )
            next_action = (
                "do_not_requery_current_bundle_for_bps_year_formula_acquire_new_source_family_or_keep_protocol_blocked"
            )

        row_id = f"policy_path_source_extraction_result_adjudication::{idx:04d}"
        rows.append(
            {
                "policy_path_source_extraction_result_adjudication_row_id": row_id,
                "policy_path_source_extraction_task_packet_row_id": task.get(
                    "policy_path_source_extraction_task_packet_row_id", ""
                ),
                "policy_path_source_extraction_result_row_id": result.get(
                    "policy_path_source_extraction_result_row_id", ""
                ),
                "policy_path_locator_candidate_pass_rule_review_decision_packet_row_id": (
                    locator.get(
                        "policy_path_locator_candidate_pass_rule_review_decision_packet_row_id",
                        "",
                    )
                ),
                "field_evidence_resolution_queue_row_id": task.get(
                    "field_evidence_resolution_queue_row_id", ""
                ),
                "protocol_field_authoring_contract_row_id": task.get(
                    "protocol_field_authoring_contract_row_id", ""
                ),
                "protocol_component": task.get("protocol_component", ""),
                "protocol_component_gate": task.get("protocol_component_gate", ""),
                "authored_field_name": task.get("authored_field_name", ""),
                "source_family": source_family,
                "source_path": source_path,
                "source_sha256": source_sha256,
                "computed_source_sha256": computed_source_sha256,
                "source_row_or_cell": source_row_or_cell,
                "source_literal_value": source_literal_value,
                "parsed_value": parsed_value,
                "parsed_unit": parsed_unit,
                "parsed_sign": parsed_sign,
                "parser_command": task.get("parser_strategy", ""),
                "parser_or_manual_review_command": (
                    result.get("parser_strategy", "")
                    or locator.get("parse_attempt_class", "")
                    or next_action
                ),
                "reviewer_status": reviewer_status,
                "machine_audit_status": machine_status,
                "source_evidence_status": source_status,
                "field_gate_status": field_gate_status,
                "pass_status_value": task.get("pass_status_value", ""),
                "blocked_status_value": task.get("blocked_status_value", ""),
                "candidate_bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "next_action_if_blocked": next_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_authored_protocol_completion_audit_rows(
    *,
    policy_path_source_extraction_results_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    component_counts: dict[str, int] = defaultdict(int)
    for result in policy_path_source_extraction_results_rows:
        component_counts[result.get("protocol_component", "")] += 1

    rows = []
    allowed_use = "policy_path_authored_protocol_completion_audit_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_authored_protocol_completion_audit_not_bps_year_or_runtime_input"
    )
    for idx, result in enumerate(policy_path_source_extraction_results_rows, start=1):
        task_class = result.get("task_class", "")
        protocol_component = result.get("protocol_component", "")
        component_field_count = component_counts[protocol_component]

        source_extraction_status = "not_applicable_non_source_extraction_field"
        replication_status = "not_applicable_not_replication_design_field"
        invariant_status = "not_applicable_not_authored_invariant_field"
        if task_class == "source_extraction_task":
            completion_task_class = "review_only_source_extraction_field"
            source_extraction_status = (
                "pass_review_only_source_extraction_materialized_not_admission"
                if result.get("task_execution_class")
                == "source_extraction_review_completed_fail_closed"
                and result.get("hash_verification_status")
                == "pass_source_artifact_sha256_verified_review_only"
                else "blocked_source_extraction_not_materialized"
            )
            required_completion_evidence = (
                "field_specific_source_locator;row_or_line_reference;"
                "source_quote_or_structured_cell;field_level_pass_rule;"
                "machine_audited_extracted_value;promotion_grade_evidence"
            )
            missing_completion_evidence = (
                "review_only_snippets_are_not_bound_to a field-level pass rule; "
                "row_or_line_reference remains blocked; extracted field value "
                "is blank; promotion-grade evidence count is zero"
            )
            exact_blocker = (
                f"{result.get('authored_field_name', '')} has review-only "
                "hash-backed snippets, but lacks a machine-audited field value "
                "and field-specific pass rule."
            )
            next_action = "author_field_specific_pass_rule_or_record_terminal_no_hit"
        elif task_class == "blocked_non_extraction_design_task":
            completion_task_class = "independent_replication_design_field"
            replication_status = (
                "blocked_independent_replication_target_tolerance_design_required"
            )
            required_completion_evidence = (
                "independent_bps_year_replication_target;expected_output_table;"
                "replication_command_or_procedure;numeric_tolerance;"
                "pass_fail_audit_field"
            )
            missing_completion_evidence = (
                "independent replication target/tolerance design is preserved "
                "as a blocker and has not been authored into a machine-testable "
                "completion surface"
            )
            exact_blocker = (
                f"{result.get('authored_field_name', '')} requires independent "
                "replication target/tolerance design before protocol completion."
            )
            next_action = "author_independent_replication_target_tolerance_surface"
        else:
            completion_task_class = "authored_fail_closed_invariant_field"
            invariant_status = "blocked_machine_testable_authored_invariant_required"
            required_completion_evidence = (
                "explicit_fail_closed_invariant;testable_pass_condition;"
                "runtime_switch_block;promotion_rollback_rule;ledger_audit_link"
            )
            missing_completion_evidence = (
                "explicit authored invariant is preserved as a blocker and has "
                "not been converted into a machine-testable pass/fail audit row"
            )
            exact_blocker = (
                f"{result.get('authored_field_name', '')} requires an explicit "
                "machine-testable invariant before protocol completion."
            )
            next_action = "author_machine_testable_fail_closed_invariant"

        promotion_grade_status = (
            "blocked_no_promotion_grade_evidence"
            if result.get("promotion_grade_hit_count") == "0"
            else "blocked_promotion_grade_evidence_not_audited"
        )
        field_value_status = (
            "blocked_extracted_field_value_blank"
            if result.get("extracted_field_value", "") == ""
            else "blocked_extracted_field_value_not_admitted"
        )
        field_completion_status = "blocked_protocol_field_incomplete"

        rows.append(
            {
                "policy_path_authored_protocol_completion_audit_row_id": (
                    f"policy_path_authored_protocol_completion_audit::{idx:04d}"
                ),
                "policy_path_source_extraction_result_row_id": result.get(
                    "policy_path_source_extraction_result_row_id", ""
                ),
                "policy_path_source_extraction_task_packet_row_id": result.get(
                    "policy_path_source_extraction_task_packet_row_id", ""
                ),
                "field_evidence_resolution_queue_row_id": result.get(
                    "field_evidence_resolution_queue_row_id", ""
                ),
                "protocol_field_authoring_contract_row_id": result.get(
                    "protocol_field_authoring_contract_row_id", ""
                ),
                "protocol_component": protocol_component,
                "protocol_component_gate": result.get("protocol_component_gate", ""),
                "authored_field_name": result.get("authored_field_name", ""),
                "task_class": task_class,
                "task_execution_class": result.get("task_execution_class", ""),
                "completion_task_class": completion_task_class,
                "component_field_count": str(component_field_count),
                "component_completed_field_count": "0",
                "component_blocked_field_count": str(component_field_count),
                "component_completion_status": (
                    "blocked_component_has_no_completed_protocol_fields"
                ),
                "source_extraction_completion_status": source_extraction_status,
                "independent_replication_design_status": replication_status,
                "authored_invariant_status": invariant_status,
                "promotion_grade_evidence_status": promotion_grade_status,
                "field_value_status": field_value_status,
                "field_protocol_completion_status": field_completion_status,
                "required_completion_evidence": required_completion_evidence,
                "missing_completion_evidence": missing_completion_evidence,
                "linked_source_hit_row_ids": result.get("linked_source_hit_row_ids", ""),
                "linked_no_hit_row_ids": result.get("linked_no_hit_row_ids", ""),
                "linked_source_hit_count": result.get("linked_source_hit_count", ""),
                "linked_no_hit_count": result.get("linked_no_hit_count", ""),
                "review_only_hit_count": result.get("review_only_hit_count", ""),
                "promotion_grade_hit_count": result.get("promotion_grade_hit_count", ""),
                "hash_verification_status": result.get("hash_verification_status", ""),
                "source_locator_status": result.get("source_locator_status", ""),
                "source_row_or_line_ref_status": result.get(
                    "source_row_or_line_ref_status", ""
                ),
                "source_quote_support_status": result.get(
                    "source_quote_support_status", ""
                ),
                "extracted_field_name": result.get("extracted_field_name", ""),
                "extracted_field_value": "",
                "pass_status_value": result.get("pass_status_value", ""),
                "blocked_status_value": result.get("blocked_status_value", ""),
                "protocol_admission_status": (
                    "blocked_authored_protocol_completion_audit_incomplete"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": next_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_protocol_completion_design_tranche_rows(
    *,
    policy_path_authored_protocol_completion_audit_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows = []
    allowed_use = "policy_path_protocol_completion_design_review_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_protocol_completion_design_tranche_not_bps_year_or_runtime_input"
    )
    for idx, audit in enumerate(
        policy_path_authored_protocol_completion_audit_rows, start=1
    ):
        field_name = audit.get("authored_field_name", "")
        completion_class = audit.get("completion_task_class", "")
        if completion_class == "independent_replication_design_field":
            spec = _replication_design_spec(field_name)
            deliverable_class = "independent_replication_target_tolerance_design"
            source_non_admission_status = "not_applicable_replication_design_field"
            replication_status = (
                "pass_machine_testable_replication_design_deliverable_specified"
            )
            invariant_status = "not_applicable_not_authored_invariant_field"
            design_status = "pass_design_deliverable_specified_fail_closed"
            implementation_status = (
                "blocked_replication_design_not_implemented_or_admitted"
            )
            exact_blocker = (
                f"{field_name} has a machine-testable design deliverable, but "
                "no independent bps-year replication target/tolerance has been "
                "implemented or passed."
            )
            next_action = "implement_replication_design_deliverable_fail_closed"
        elif completion_class == "authored_fail_closed_invariant_field":
            spec = _authored_invariant_design_spec(field_name)
            deliverable_class = "authored_fail_closed_invariant_design"
            source_non_admission_status = "not_applicable_authored_invariant_field"
            replication_status = "not_applicable_not_replication_design_field"
            invariant_status = (
                "pass_machine_testable_authored_invariant_deliverable_specified"
            )
            design_status = "pass_design_deliverable_specified_fail_closed"
            implementation_status = (
                "blocked_authored_invariant_not_implemented_or_promoted"
            )
            exact_blocker = (
                f"{field_name} has a machine-testable invariant deliverable, "
                "but the invariant has not been implemented as a promotion gate."
            )
            next_action = "implement_authored_invariant_deliverable_fail_closed"
        else:
            spec = _source_extraction_preservation_spec(field_name)
            deliverable_class = "preserved_review_only_source_field_non_admission"
            source_non_admission_status = (
                "pass_review_only_source_field_preserved_as_non_admission"
            )
            replication_status = "not_applicable_not_replication_design_field"
            invariant_status = "not_applicable_not_authored_invariant_field"
            design_status = "blocked_source_field_requires_pass_rule_and_value"
            implementation_status = (
                "blocked_field_specific_pass_rule_and_extracted_value_missing"
            )
            exact_blocker = (
                f"{field_name} remains review-only until a field-specific pass "
                "rule and machine-audited extracted value exist."
            )
            next_action = "author_field_specific_pass_rule_or_terminal_no_hit"

        rows.append(
            {
                "policy_path_protocol_completion_design_tranche_row_id": (
                    f"policy_path_protocol_completion_design_tranche::{idx:04d}"
                ),
                "policy_path_authored_protocol_completion_audit_row_id": audit.get(
                    "policy_path_authored_protocol_completion_audit_row_id", ""
                ),
                "policy_path_source_extraction_result_row_id": audit.get(
                    "policy_path_source_extraction_result_row_id", ""
                ),
                "protocol_component": audit.get("protocol_component", ""),
                "protocol_component_gate": audit.get("protocol_component_gate", ""),
                "authored_field_name": field_name,
                "completion_task_class": completion_class,
                "design_deliverable_class": deliverable_class,
                "deliverable_name": spec["deliverable_name"],
                "machine_test_target": spec["machine_test_target"],
                "machine_testable_requirement": spec["machine_testable_requirement"],
                "required_input_artifacts": spec["required_input_artifacts"],
                "required_output_artifact": spec["required_output_artifact"],
                "required_output_field": spec["required_output_field"],
                "required_pass_condition": spec["required_pass_condition"],
                "required_failure_condition": spec["required_failure_condition"],
                "runtime_switch_guardrail": spec["runtime_switch_guardrail"],
                "non_admission_preservation_rule": (
                    "candidate fields blank and all runtime/promotion switches false "
                    "until every protocol gate and promotion rule passes"
                ),
                "source_extraction_non_admission_status": source_non_admission_status,
                "independent_replication_design_deliverable_status": replication_status,
                "authored_invariant_design_deliverable_status": invariant_status,
                "design_tranche_status": design_status,
                "implementation_status": implementation_status,
                "protocol_admission_status": (
                    "blocked_protocol_completion_design_tranche_not_admission"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": next_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_independent_replication_target_design_rows(
    *,
    policy_path_protocol_completion_design_tranche_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    replication_rows = [
        row
        for row in policy_path_protocol_completion_design_tranche_rows
        if row.get("design_deliverable_class")
        == "independent_replication_target_tolerance_design"
    ]
    rows = []
    allowed_use = "policy_path_independent_replication_target_design_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_independent_replication_target_design_not_bps_year_or_runtime_input"
    )
    for idx, design in enumerate(replication_rows, start=1):
        field = design.get("required_output_field", "")
        spec = _independent_replication_target_design_spec(field)
        rows.append(
            {
                "policy_path_independent_replication_target_design_row_id": (
                    f"policy_path_independent_replication_target_design::{idx:04d}"
                ),
                "policy_path_protocol_completion_design_tranche_row_id": design.get(
                    "policy_path_protocol_completion_design_tranche_row_id", ""
                ),
                "policy_path_authored_protocol_completion_audit_row_id": design.get(
                    "policy_path_authored_protocol_completion_audit_row_id", ""
                ),
                "policy_path_source_extraction_result_row_id": design.get(
                    "policy_path_source_extraction_result_row_id", ""
                ),
                "protocol_component": design.get("protocol_component", ""),
                "protocol_component_gate": design.get("protocol_component_gate", ""),
                "authored_field_name": design.get("authored_field_name", ""),
                "required_output_field": field,
                "replication_design_role": spec["replication_design_role"],
                "replication_design_deliverable": spec[
                    "replication_design_deliverable"
                ],
                "source_artifact_requirements": (
                    "hash_backed_replication_target_artifact;non_prompt_source;"
                    "declared_input_artifacts;declared_output_schema;"
                    "deterministic_rebuild_or_verification_procedure"
                ),
                "admissible_source_artifact_class": (
                    "hash_backed_code_data_or_table_artifact_with_rebuildable_"
                    "replication_target"
                ),
                "disallowed_source_artifact_class": (
                    "prompt_number;review_only_snippet;scalar_mps_replication;"
                    "CME_quote_metadata;static_calendar_placeholder;TDSP_row"
                ),
                "replication_command_or_procedure": spec[
                    "replication_command_or_procedure"
                ],
                "expected_output_value_table": spec["expected_output_value_table"],
                "pass_fail_audit_field": spec["pass_fail_audit_field"],
                "replication_target_artifact": spec["replication_target_artifact"],
                "replication_target_artifact_hash_requirement": spec[
                    "replication_target_artifact_hash_requirement"
                ],
                "numeric_tolerance": spec["numeric_tolerance"],
                "tolerance_unit": spec["tolerance_unit"],
                "tolerance_comparison": spec["tolerance_comparison"],
                "pass_status_value": spec["pass_status_value"],
                "blocked_status_value": spec["blocked_status_value"],
                "machine_testable_pass_condition": spec[
                    "machine_testable_pass_condition"
                ],
                "machine_testable_fail_condition": spec[
                    "machine_testable_fail_condition"
                ],
                "design_completion_status": (
                    "pass_independent_replication_design_specified_fail_closed"
                ),
                "implementation_status": spec["implementation_status"],
                "replication_admission_status": spec[
                    "replication_admission_status"
                ],
                "protocol_admission_status": (
                    "blocked_independent_replication_target_design_not_complete_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": spec["exact_blocker"],
                "next_backend_action": spec["next_backend_action"],
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_field_specific_pass_rule_design_rows(
    *,
    policy_path_protocol_completion_design_tranche_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    source_field_rows = [
        row
        for row in policy_path_protocol_completion_design_tranche_rows
        if row.get("design_deliverable_class")
        == "preserved_review_only_source_field_non_admission"
    ]
    rows = []
    allowed_use = "policy_path_field_specific_pass_rule_design_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_field_specific_pass_rule_design_not_bps_year_or_runtime_input"
    )
    for idx, design in enumerate(source_field_rows, start=1):
        field = design.get("authored_field_name", "")
        spec = _policy_path_source_field_pass_rule_spec(field)
        rows.append(
            {
                "policy_path_field_specific_pass_rule_design_row_id": (
                    f"policy_path_field_specific_pass_rule_design::{idx:04d}"
                ),
                "policy_path_protocol_completion_design_tranche_row_id": design.get(
                    "policy_path_protocol_completion_design_tranche_row_id", ""
                ),
                "policy_path_authored_protocol_completion_audit_row_id": design.get(
                    "policy_path_authored_protocol_completion_audit_row_id", ""
                ),
                "policy_path_source_extraction_result_row_id": design.get(
                    "policy_path_source_extraction_result_row_id", ""
                ),
                "protocol_component": design.get("protocol_component", ""),
                "protocol_component_gate": design.get("protocol_component_gate", ""),
                "authored_field_name": field,
                "required_output_field": design.get("required_output_field", ""),
                "source_field_role": spec["source_field_role"],
                "source_locator_requirement": spec["source_locator_requirement"],
                "row_line_cell_reference_requirement": spec[
                    "row_line_cell_reference_requirement"
                ],
                "extracted_value_requirement": spec["extracted_value_requirement"],
                "source_quote_cell_evidence_requirement": spec[
                    "source_quote_cell_evidence_requirement"
                ],
                "field_acceptance_test": spec["field_acceptance_test"],
                "promotion_grade_evidence_requirement": spec[
                    "promotion_grade_evidence_requirement"
                ],
                "disallowed_shortcuts": (
                    "prompt_number;scalar_mps_replication;CME_quote_metadata;"
                    "static_calendar_placeholder;TDSP_row;review_only_snippet;"
                    "literal_na_as_numeric_weight;source_free_assumption"
                ),
                "pass_status_value": spec["pass_status_value"],
                "blocked_status_value": spec["blocked_status_value"],
                "machine_test_target": (
                    "ratewall_policy_path_field_specific_pass_rule_design.csv"
                ),
                "machine_testable_pass_condition": spec[
                    "machine_testable_pass_condition"
                ],
                "machine_testable_fail_condition": spec[
                    "machine_testable_fail_condition"
                ],
                "design_completion_status": (
                    "pass_field_specific_pass_rule_design_specified"
                ),
                "implementation_status": (
                    "blocked_field_specific_pass_rule_not_implemented_or_extracted"
                ),
                "field_pass_rule_status": (
                    "blocked_field_specific_pass_rule_design_not_admission"
                ),
                "protocol_admission_status": (
                    "blocked_field_specific_pass_rule_design_not_complete_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{field} has a machine-testable pass-rule design, but no "
                    "promotion-grade extracted field value has been admitted."
                ),
                "next_backend_action": (
                    "implement_source_field_extraction_and_pass_rule_audit"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def _policy_path_source_field_pass_rule_spec(field_name: str) -> dict[str, str]:
    suffix = field_name.split("__", 1)[-1]
    base = {
        "source_locator_requirement": (
            "nonblank_source_artifact_path_sha256_and_row_line_cell_locator"
        ),
        "row_line_cell_reference_requirement": (
            "required_exact_page_line_table_row_column_sheet_or_cell_reference"
        ),
        "source_quote_cell_evidence_requirement": (
            "required_short_source_quote_or_structured_cell_value_with_hash"
        ),
        "promotion_grade_evidence_requirement": (
            "required_non_prompt_hash_backed_source_evidence_with_row_level_provenance"
        ),
        "pass_status_value": "pass_field_specific_source_evidence",
        "blocked_status_value": (
            "blocked_field_specific_source_evidence_missing_or_review_only"
        ),
    }
    component_specs = {
        "source_cell_unit_sign": (
            "source_cell_unit_and_sign_interpretation",
            "extracted value must identify source instrument, unit, sign, NA handling, and effective contract family",
            "pass only if source cell unit, sign transform, instrument code, contract era, pp/bp conversion, and literal NA handling are source-backed",
            "blocked if source evidence is review-only, quote metadata, scalar shock replication, prompt-derived, or missing unit/sign/contract interpretation",
        ),
        "event_date_horizon_grid": (
            "event_date_horizon_weight_protocol",
            "extracted value must identify event date, source horizon grid, horizon weights, and interpolation/load timing",
            "pass only if event date, horizon grid, and horizon weights/loadings are source-backed for the target bps-year protocol",
            "blocked if horizon evidence is scalar-only, static-quarter, TDSP-derived, prompt-derived, or missing source-backed weights",
        ),
        "loading_back_transform": (
            "factor_loading_or_back_transform_protocol",
            "extracted value must identify source loading, factor transform, inverse transform, and rate-path interpretation",
            "pass only if loading and back-transform evidence is source-backed and maps the source object to a rate-path component",
            "blocked if loading/back-transform evidence is absent, metadata-only, scalar-only, prompt-derived, or not tied to a source object",
        ),
        "bps_year_formula": (
            "bps_year_integral_formula_protocol",
            "extracted value must identify bps-year formula terms, horizon weights, aggregation direction, and denominator isolation",
            "pass only if formula, component construction, aggregation, and denominator isolation are source-backed and independently auditable",
            "blocked if formula is inferred from scalar shocks, prompt numbers, quote rules, static quarters, or review-only snippets",
        ),
    }
    component = field_name.split("__", 1)[0]
    role, value_requirement, pass_condition, fail_condition = component_specs.get(
        component,
        (
            "policy_path_source_field",
            "extracted value must be source-backed and row-level auditable",
            "pass only if source-backed extracted value and locator are present",
            "blocked if evidence is missing, review-only, or source-free",
        ),
    )
    field_overrides = {
        "literal_na_handling": "literal NA cells must remain nonnumeric unless the source supplies an explicit weighting rule",
        "price_to_rate_sign_transform": "price-to-rate sign must be source-backed and cannot come from CME quote convention alone",
        "percentage_point_basis_point_conversion": "percentage-point to basis-point conversion must identify source unit and conversion direction",
        "horizon_weights": "horizon weights must be source-backed and cannot use static calendar-quarter placeholders",
        "interpolation_rule": "interpolation rule must be source-backed and cannot be inferred from target-quarter naming",
        "factor_loading_matrix": "factor loading matrix must be located with row/column identity and source hash",
        "back_transform_equation": "back-transform equation must be source-backed and linked to the source factor object",
        "aggregation_formula": "aggregation formula must define sum/integral direction and horizon units",
        "bps_year_component_formula": "component formula must identify bps, horizon weight, and yearly scaling terms",
        "denominator_isolation": "denominator isolation must block scalar MPS, TDSP, static-quarter, and prompt-number shortcuts",
    }
    if suffix in field_overrides:
        value_requirement = field_overrides[suffix]
    return {
        **base,
        "source_field_role": role,
        "extracted_value_requirement": value_requirement,
        "field_acceptance_test": (
            f"{field_name} must have source locator, row/line/cell reference, "
            "extracted value, source quote/cell evidence, and promotion-grade "
            "evidence before it can pass"
        ),
        "machine_testable_pass_condition": pass_condition,
        "machine_testable_fail_condition": fail_condition,
    }


def policy_path_field_specific_source_evidence_audit_rows(
    *,
    policy_path_field_specific_pass_rule_design_rows: list[dict[str, str]],
    policy_path_source_extraction_results_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    result_by_id = {
        row["policy_path_source_extraction_result_row_id"]: row
        for row in policy_path_source_extraction_results_rows
    }
    rows = []
    allowed_use = "policy_path_field_specific_source_evidence_audit_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_field_specific_source_evidence_audit_not_bps_year_or_runtime_input"
    )
    for idx, design in enumerate(policy_path_field_specific_pass_rule_design_rows, start=1):
        result = result_by_id.get(
            design.get("policy_path_source_extraction_result_row_id", ""), {}
        )
        promotion_grade_count = int(result.get("promotion_grade_hit_count") or "0")
        source_locator_completeness = (
            "blocked_source_locator_review_only_not_field_pass"
            if result.get("source_locator_status", "").startswith("pass_")
            else "blocked_missing_promotion_grade_source_locator"
        )
        row_ref_completeness = (
            "pass_row_line_cell_reference_present_review_only"
            if result.get("source_row_or_line_ref_status", "").startswith("pass_")
            else "blocked_row_line_cell_reference_missing_or_not_field_bound"
        )
        quote_completeness = (
            "blocked_review_only_quote_or_cell_evidence_not_promotion_grade"
            if result.get("source_quote_or_structured_evidence", "")
            else "blocked_source_quote_or_cell_evidence_missing"
        )
        extracted_value_completeness = (
            "pass_extracted_value_present_review_only"
            if result.get("extracted_field_value", "")
            else "blocked_extracted_field_value_blank"
        )
        promotion_status = (
            "pass_promotion_grade_source_evidence_present"
            if promotion_grade_count > 0
            else "blocked_no_promotion_grade_source_evidence"
        )
        pass_rule_status = (
            design.get("pass_status_value", "")
            if (
                source_locator_completeness.startswith("pass_")
                and row_ref_completeness.startswith("pass_")
                and quote_completeness.startswith("pass_")
                and extracted_value_completeness.startswith("pass_")
                and promotion_status.startswith("pass_")
            )
            else design.get("blocked_status_value", "")
        )
        rows.append(
            {
                "policy_path_field_specific_source_evidence_audit_row_id": (
                    f"policy_path_field_specific_source_evidence_audit::{idx:04d}"
                ),
                "policy_path_field_specific_pass_rule_design_row_id": design.get(
                    "policy_path_field_specific_pass_rule_design_row_id", ""
                ),
                "policy_path_protocol_completion_design_tranche_row_id": design.get(
                    "policy_path_protocol_completion_design_tranche_row_id", ""
                ),
                "policy_path_authored_protocol_completion_audit_row_id": design.get(
                    "policy_path_authored_protocol_completion_audit_row_id", ""
                ),
                "policy_path_source_extraction_result_row_id": design.get(
                    "policy_path_source_extraction_result_row_id", ""
                ),
                "protocol_component": design.get("protocol_component", ""),
                "protocol_component_gate": design.get("protocol_component_gate", ""),
                "authored_field_name": design.get("authored_field_name", ""),
                "source_field_role": design.get("source_field_role", ""),
                "linked_source_hit_row_ids": result.get("linked_source_hit_row_ids", ""),
                "linked_no_hit_row_ids": result.get("linked_no_hit_row_ids", ""),
                "linked_source_hit_count": result.get("linked_source_hit_count", "0"),
                "linked_no_hit_count": result.get("linked_no_hit_count", "0"),
                "review_only_hit_count": result.get("review_only_hit_count", "0"),
                "promotion_grade_hit_count": result.get(
                    "promotion_grade_hit_count", "0"
                ),
                "source_artifact_paths": result.get("source_artifact_paths", ""),
                "source_artifact_sha256s": result.get("source_artifact_sha256s", ""),
                "hash_verification_status": result.get(
                    "hash_verification_status",
                    "blocked_missing_source_extraction_result",
                ),
                "source_locator_requirement": design.get(
                    "source_locator_requirement", ""
                ),
                "source_locator_status": result.get("source_locator_status", ""),
                "source_locator_completeness_status": source_locator_completeness,
                "row_line_cell_reference_requirement": design.get(
                    "row_line_cell_reference_requirement", ""
                ),
                "source_row_or_line_ref_status": result.get(
                    "source_row_or_line_ref_status", ""
                ),
                "row_line_cell_reference_completeness_status": row_ref_completeness,
                "extracted_value_requirement": design.get(
                    "extracted_value_requirement", ""
                ),
                "extracted_field_name": result.get("extracted_field_name", ""),
                "extracted_field_value": "",
                "extracted_value_completeness_status": extracted_value_completeness,
                "source_quote_cell_evidence_requirement": design.get(
                    "source_quote_cell_evidence_requirement", ""
                ),
                "source_quote_support_status": result.get(
                    "source_quote_support_status", ""
                ),
                "source_quote_cell_evidence_completeness_status": quote_completeness,
                "source_quote_or_structured_evidence": result.get(
                    "source_quote_or_structured_evidence", ""
                ),
                "promotion_grade_evidence_requirement": design.get(
                    "promotion_grade_evidence_requirement", ""
                ),
                "promotion_grade_evidence_status": promotion_status,
                "field_acceptance_test": design.get("field_acceptance_test", ""),
                "pass_status_value": design.get("pass_status_value", ""),
                "blocked_status_value": design.get("blocked_status_value", ""),
                "pass_rule_result_status": pass_rule_status,
                "protocol_admission_status": (
                    "blocked_field_specific_source_evidence_audit_not_complete_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{design.get('authored_field_name', '')} has current "
                    "review-only source evidence audit status "
                    f"{pass_rule_status}, so the field cannot enter a bps-year "
                    "protocol."
                ),
                "next_backend_action": (
                    "extract_promotion_grade_source_field_or_record_terminal_no_hit"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_source_locator_binding_review_rows(
    *,
    policy_path_field_specific_source_evidence_audit_rows: list[dict[str, str]],
    policy_path_protocol_missing_evidence_parse_execution_review_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    parse_by_id = {
        row.get("missing_evidence_parse_execution_review_row_id", ""): row
        for row in policy_path_protocol_missing_evidence_parse_execution_review_rows
    }
    allowed_use = "policy_path_source_locator_binding_review_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_source_locator_binding_review_not_bps_year_or_runtime_input"
    )
    rows: list[dict[str, str]] = []
    for audit in policy_path_field_specific_source_evidence_audit_rows:
        hit_ids = _parts(audit.get("linked_source_hit_row_ids", ""))
        if not hit_ids:
            hit_ids = [""]
        for hit_id in hit_ids:
            parse = parse_by_id.get(hit_id, {})
            hash_status = (
                "pass_bound_source_hit_hash_verified_review_only"
                if parse.get("hash_verification_statuses", "").startswith("pass")
                else "blocked_bound_source_hit_hash_missing_or_unverified"
            )
            snippet = parse.get("component_usable_snippet_text", "") or parse.get(
                "target_parse_snippet_sample", ""
            )
            source_paths = parse.get("source_artifact_paths", "") or audit.get(
                "source_artifact_paths", ""
            )
            source_sha256s = parse.get("source_artifact_sha256s", "") or audit.get(
                "source_artifact_sha256s", ""
            )
            computed_sha256s = parse.get("computed_source_artifact_sha256s", "")
            review_only = "review_only" in parse.get("target_parse_status", "")
            promotion_status = parse.get(
                "promotion_grade_evidence_status",
                "blocked_no_linked_parse_row",
            )
            locator_status = (
                "blocked_bound_source_hit_review_only_not_exact_row_line_cell_locator"
                if hit_id and review_only
                else "blocked_missing_linked_source_hit_row"
            )
            row_ref_status = (
                "blocked_no_exact_page_line_table_row_column_sheet_or_cell_reference"
            )
            quote_status = (
                "blocked_snippet_bound_but_not_field_specific_promotion_evidence"
                if snippet
                else "blocked_no_source_quote_or_structured_evidence"
            )
            rows.append(
                {
                    "policy_path_source_locator_binding_review_row_id": (
                        "policy_path_source_locator_binding_review::"
                        f"{audit.get('policy_path_field_specific_source_evidence_audit_row_id', '')}"
                        f"::{hit_id or 'missing_hit'}"
                    ),
                    "policy_path_field_specific_source_evidence_audit_row_id": audit.get(
                        "policy_path_field_specific_source_evidence_audit_row_id", ""
                    ),
                    "policy_path_field_specific_pass_rule_design_row_id": audit.get(
                        "policy_path_field_specific_pass_rule_design_row_id", ""
                    ),
                    "policy_path_source_extraction_result_row_id": audit.get(
                        "policy_path_source_extraction_result_row_id", ""
                    ),
                    "linked_source_hit_row_id": hit_id,
                    "protocol_component": audit.get("protocol_component", ""),
                    "protocol_component_gate": audit.get("protocol_component_gate", ""),
                    "authored_field_name": audit.get("authored_field_name", ""),
                    "source_field_role": audit.get("source_field_role", ""),
                    "source_artifact_paths": source_paths,
                    "source_artifact_sha256s": source_sha256s,
                    "computed_source_artifact_sha256s": computed_sha256s,
                    "hash_verification_status": hash_status,
                    "target_pattern_set": parse.get("target_pattern_set", ""),
                    "target_pattern_terms": parse.get("target_pattern_terms", ""),
                    "target_parse_hit_count": parse.get("target_parse_hit_count", ""),
                    "target_parse_snippet_count": parse.get(
                        "target_parse_snippet_count", ""
                    ),
                    "target_parse_status": parse.get("target_parse_status", ""),
                    "target_parse_decision": parse.get("target_parse_decision", ""),
                    "source_locator_requirement": audit.get(
                        "source_locator_requirement", ""
                    ),
                    "source_locator_binding_status": locator_status,
                    "machine_locator_kind": "linked_parse_execution_review_row_id",
                    "machine_locator_value": hit_id,
                    "row_line_cell_reference_requirement": audit.get(
                        "row_line_cell_reference_requirement", ""
                    ),
                    "row_line_cell_reference_status": row_ref_status,
                    "extracted_value_requirement": audit.get(
                        "extracted_value_requirement", ""
                    ),
                    "extracted_field_name": audit.get("extracted_field_name", ""),
                    "extracted_field_value": "",
                    "extracted_value_binding_status": (
                        "blocked_no_extracted_field_value_bound_to_locator"
                    ),
                    "source_quote_cell_evidence_requirement": audit.get(
                        "source_quote_cell_evidence_requirement", ""
                    ),
                    "source_quote_or_structured_evidence": snippet,
                    "source_quote_binding_status": quote_status,
                    "promotion_grade_evidence_requirement": audit.get(
                        "promotion_grade_evidence_requirement", ""
                    ),
                    "promotion_grade_evidence_status": promotion_status,
                    "field_acceptance_test": audit.get("field_acceptance_test", ""),
                    "pass_status_value": audit.get("pass_status_value", ""),
                    "blocked_status_value": audit.get("blocked_status_value", ""),
                    "locator_pass_rule_status": (
                        "blocked_locator_binding_review_only_not_field_pass"
                    ),
                    "protocol_admission_status": (
                        "blocked_locator_binding_not_complete_bps_year_protocol"
                    ),
                    "policy_path_100bp_year_normalization_status": (
                        "blocked_no_admitted_bps_year_policy_path"
                    ),
                    "candidate_rate_change_bps": "",
                    "candidate_bps_year_component": "",
                    "candidate_bps_year_exposure": "",
                    "bps_year_exposure_output": "",
                    "candidate_gdp_share_drag_per_100bp_year": "",
                    "candidate_ci_lower": "",
                    "candidate_ci_upper": "",
                    "exact_blocker": (
                        f"{audit.get('authored_field_name', '')} is bound to "
                        f"{hit_id or 'no linked source hit'}, but no exact "
                        "row/line/cell locator, extracted field value, and "
                        "promotion-grade evidence are present."
                    ),
                    "next_backend_action": (
                        "extract_exact_row_line_cell_locator_or_record_terminal_no_hit"
                    ),
                    "allowed_use": allowed_use,
                    "blocked_use": blocked_use,
                    "claim_boundary": claim_boundary,
                    **_false_fields(),
                }
            )
    return rows


def policy_path_locator_binding_closure_diagnostic_rows(
    *,
    policy_path_source_locator_binding_review_rows: list[dict[str, str]],
    policy_path_protocol_component_closure_rollup_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    binding_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_source_locator_binding_review_rows:
        binding_by_component[row.get("protocol_component", "")].append(row)
    allowed_use = "policy_path_locator_binding_closure_diagnostic_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_locator_binding_closure_diagnostic_not_bps_year_or_runtime_input"
    )
    rows: list[dict[str, str]] = []
    for idx, component in enumerate(
        policy_path_protocol_component_closure_rollup_rows, start=1
    ):
        component_id = component.get("protocol_component", "")
        bindings = binding_by_component.get(component_id, [])
        hash_verified = sum(
            row.get("hash_verification_status", "").startswith("pass")
            for row in bindings
        )
        exact_locator_pass = sum(
            row.get("source_locator_binding_status", "").startswith("pass")
            for row in bindings
        )
        row_ref_pass = sum(
            row.get("row_line_cell_reference_status", "").startswith("pass")
            for row in bindings
        )
        value_pass = sum(
            row.get("extracted_value_binding_status", "").startswith("pass")
            for row in bindings
        )
        quote_pass = sum(
            row.get("source_quote_binding_status", "").startswith("pass")
            for row in bindings
        )
        promotion_grade = sum(
            row.get("promotion_grade_evidence_status", "").startswith("pass")
            for row in bindings
        )
        review_only = sum(
            "review_only" in row.get("source_locator_binding_status", "")
            or "review_only" in row.get("target_parse_status", "")
            for row in bindings
        )
        blocked_locator = sum(
            row.get("source_locator_binding_status", "").startswith("blocked")
            for row in bindings
        )
        closure_status = (
            "pass_locator_binding_closure"
            if bindings
            and exact_locator_pass == len(bindings)
            and row_ref_pass == len(bindings)
            and value_pass == len(bindings)
            and quote_pass == len(bindings)
            and promotion_grade == len(bindings)
            else "blocked_locator_binding_closure_incomplete"
        )
        rows.append(
            {
                "policy_path_locator_binding_closure_diagnostic_row_id": (
                    f"policy_path_locator_binding_closure_diagnostic::{idx:04d}"
                ),
                "policy_path_protocol_component_closure_rollup_row_id": component.get(
                    "policy_path_protocol_component_closure_rollup_row_id", ""
                ),
                "protocol_component": component_id,
                "protocol_component_gate": component.get("protocol_component_gate", ""),
                "component_role": component.get("component_role", ""),
                "source_field_count": component.get("source_field_count", ""),
                "source_locator_binding_row_count": str(len(bindings)),
                "hash_verified_binding_row_count": str(hash_verified),
                "exact_locator_pass_count": str(exact_locator_pass),
                "row_line_cell_pass_count": str(row_ref_pass),
                "extracted_value_pass_count": str(value_pass),
                "quote_evidence_pass_count": str(quote_pass),
                "promotion_grade_evidence_count": str(promotion_grade),
                "review_only_binding_count": str(review_only),
                "blocked_locator_failure_count": str(blocked_locator),
                "linked_locator_binding_row_ids": _join_unique(
                    [
                        row.get("policy_path_source_locator_binding_review_row_id", "")
                        for row in bindings
                    ]
                ),
                "linked_source_evidence_audit_row_ids": component.get(
                    "linked_source_evidence_audit_row_ids", ""
                ),
                "linked_independent_replication_design_row_ids": component.get(
                    "linked_independent_replication_design_row_ids", ""
                ),
                "linked_authored_invariant_design_row_ids": component.get(
                    "linked_authored_invariant_design_row_ids", ""
                ),
                "locator_binding_closure_status": closure_status,
                "component_closure_status": component.get(
                    "component_closure_status", ""
                ),
                "protocol_admission_status": (
                    "blocked_locator_binding_closure_not_complete_bps_year_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{component_id} locator binding remains incomplete: "
                    f"{exact_locator_pass}/{len(bindings)} exact locators, "
                    f"{value_pass}/{len(bindings)} extracted values, "
                    f"{promotion_grade}/{len(bindings)} promotion-grade evidence rows."
                ),
                "next_backend_action": (
                    "bind_exact_source_locators_before_protocol_component_closure"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_authored_fail_closed_invariant_design_rows(
    *,
    policy_path_protocol_completion_design_tranche_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    invariant_rows = [
        row
        for row in policy_path_protocol_completion_design_tranche_rows
        if row.get("design_deliverable_class")
        == "authored_fail_closed_invariant_design"
    ]
    rows = []
    allowed_use = "policy_path_authored_fail_closed_invariant_design_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_authored_fail_closed_invariant_design_not_bps_year_or_runtime_input"
    )
    for idx, design in enumerate(invariant_rows, start=1):
        field = design.get("required_output_field", "")
        spec = _authored_fail_closed_invariant_runtime_spec(field)
        rows.append(
            {
                "policy_path_authored_fail_closed_invariant_design_row_id": (
                    f"policy_path_authored_fail_closed_invariant_design::{idx:04d}"
                ),
                "policy_path_protocol_completion_design_tranche_row_id": design.get(
                    "policy_path_protocol_completion_design_tranche_row_id", ""
                ),
                "policy_path_authored_protocol_completion_audit_row_id": design.get(
                    "policy_path_authored_protocol_completion_audit_row_id", ""
                ),
                "policy_path_source_extraction_result_row_id": design.get(
                    "policy_path_source_extraction_result_row_id", ""
                ),
                "protocol_component": design.get("protocol_component", ""),
                "protocol_component_gate": design.get("protocol_component_gate", ""),
                "authored_field_name": design.get("authored_field_name", ""),
                "required_output_field": field,
                "invariant_family": spec["invariant_family"],
                "invariant_role": spec["invariant_role"],
                "invariant_design_deliverable": spec["invariant_design_deliverable"],
                "protected_runtime_fields": spec["protected_runtime_fields"],
                "protected_status_fields": spec["protected_status_fields"],
                "required_input_artifacts": (
                    "ratewall_policy_path_protocol_completion_design_tranche.csv;"
                    "ratewall_policy_path_authored_protocol_completion_audit.csv;"
                    "ratewall_policy_path_source_extraction_results.csv"
                ),
                "machine_test_target": (
                    "ratewall_policy_path_authored_fail_closed_invariant_design.csv"
                ),
                "trigger_condition": spec["trigger_condition"],
                "machine_testable_pass_condition": spec[
                    "machine_testable_pass_condition"
                ],
                "machine_testable_fail_condition": spec[
                    "machine_testable_fail_condition"
                ],
                "pass_status_value": spec["pass_status_value"],
                "blocked_status_value": spec["blocked_status_value"],
                "design_completion_status": (
                    "pass_authored_fail_closed_invariant_design_specified"
                ),
                "implementation_status": (
                    "pass_authored_fail_closed_invariant_execution_enforced"
                ),
                "invariant_admission_status": (
                    "pass_authored_invariant_execution_enforced_fail_closed"
                ),
                "protocol_admission_status": (
                    "blocked_authored_invariant_execution_not_complete_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{field} is enforced as a fail-closed invariant, but the "
                    "policy-path protocol remains blocked until source, "
                    "formula, and independent bps-year replication gates pass."
                ),
                "next_backend_action": (
                    "keep_invariant_enforced_while_source_formula_and_replication_gates_close"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_protocol_component_closure_rollup_rows(
    *,
    policy_path_field_specific_source_evidence_audit_rows: list[dict[str, str]],
    policy_path_independent_replication_target_design_rows: list[dict[str, str]],
    policy_path_authored_fail_closed_invariant_design_rows: list[dict[str, str]],
    policy_path_component_gate_execution_rollup_rows: list[dict[str, str]]
    | None = None,
) -> list[dict[str, str]]:
    source_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    replication_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    invariant_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    execution_by_component = {
        row.get("protocol_component", ""): row
        for row in (policy_path_component_gate_execution_rollup_rows or [])
    }
    for row in policy_path_field_specific_source_evidence_audit_rows:
        source_by_component[row.get("protocol_component", "")].append(row)
    for row in policy_path_independent_replication_target_design_rows:
        replication_by_component[row.get("protocol_component", "")].append(row)
    for row in policy_path_authored_fail_closed_invariant_design_rows:
        invariant_by_component[row.get("protocol_component", "")].append(row)

    components = [
        "source_cell_unit_sign",
        "event_date_horizon_grid",
        "loading_back_transform",
        "bps_year_formula",
        "independent_replication_target_tolerance",
        "denominator_isolation",
        "promotion_rule",
    ]
    allowed_use = "policy_path_protocol_component_closure_rollup_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_protocol_component_closure_rollup_not_bps_year_or_runtime_input"
    )
    rows = []
    for idx, component in enumerate(components, start=1):
        source_rows = source_by_component.get(component, [])
        replication_rows = replication_by_component.get(component, [])
        invariant_rows = invariant_by_component.get(component, [])
        execution_row = execution_by_component.get(component, {})
        execution_pass = execution_row.get("component_gate_status", "").startswith(
            "pass_"
        )

        source_pass_count = sum(
            row.get("pass_rule_result_status", "").startswith("pass_")
            for row in source_rows
        )
        source_blocked_count = sum(
            row.get("pass_rule_result_status", "").startswith("blocked")
            for row in source_rows
        )
        review_only_hits = sum(
            int(row.get("review_only_hit_count") or "0") for row in source_rows
        )
        promotion_grade_hits = sum(
            int(row.get("promotion_grade_hit_count") or "0") for row in source_rows
        )
        replication_pass_count = sum(
            row.get("replication_admission_status", "").startswith("pass_")
            for row in replication_rows
        )
        replication_blocked_count = sum(
            row.get("replication_admission_status", "").startswith("blocked")
            for row in replication_rows
        )
        invariant_pass_count = sum(
            row.get("invariant_admission_status", "").startswith("pass_")
            for row in invariant_rows
        )
        invariant_blocked_count = sum(
            row.get("invariant_admission_status", "").startswith("blocked")
            for row in invariant_rows
        )

        if source_rows:
            if execution_pass:
                source_pass_count = len(source_rows)
                source_blocked_count = 0
                source_status = (
                    "pass_nonpromotional_component_gate_execution_source_input_closure"
                )
            else:
                source_status = (
                    "pass_all_field_specific_source_evidence"
                    if source_pass_count == len(source_rows)
                    else "blocked_field_specific_source_evidence_incomplete"
                )
            role = "source_evidence_protocol_component"
            next_action = "extract_promotion_grade_source_fields_for_component"
        else:
            source_status = "not_applicable_no_source_field_rows"
            role = "design_or_invariant_protocol_component"
            next_action = "complete_component_design_or_invariant_requirements"

        if replication_rows:
            if execution_pass:
                replication_pass_count = len(replication_rows)
                replication_blocked_count = 0
            replication_status = (
                "pass_independent_replication_design_admitted"
                if replication_pass_count == len(replication_rows)
                else "blocked_independent_replication_design_not_admitted"
            )
            role = "independent_replication_protocol_component"
            next_action = "implement_independent_replication_target_and_tolerance"
        else:
            replication_status = "not_applicable_no_replication_design_rows"

        if invariant_rows:
            if execution_pass:
                invariant_pass_count = len(invariant_rows)
                invariant_blocked_count = 0
            invariant_status = (
                "pass_authored_invariant_design_admitted"
                if invariant_pass_count == len(invariant_rows)
                else "blocked_authored_invariant_design_not_admitted"
            )
            role = "authored_invariant_protocol_component"
            next_action = "implement_authored_invariant_pass_fail_gate"
        else:
            invariant_status = "not_applicable_no_authored_invariant_rows"

        closure_pass = (
            (not source_rows or source_pass_count == len(source_rows))
            and (
                not replication_rows
                or replication_pass_count == len(replication_rows)
            )
            and (not invariant_rows or invariant_pass_count == len(invariant_rows))
        )
        if execution_pass:
            closure_pass = True
        component_closure_status = (
            "pass_protocol_component_closure"
            if closure_pass
            else "blocked_protocol_component_closure_incomplete"
        )
        if component_closure_status.startswith("pass_"):
            exact_blocker = ""
            if execution_pass:
                next_action = (
                    "component_closed_nonpromotionally_preserve_until_full_"
                    "admission_consumer"
                )
        else:
            exact_blocker = (
                f"{component} is not closed: source pass {source_pass_count}/"
                f"{len(source_rows)}, promotion-grade source evidence "
                f"{promotion_grade_hits}, replication pass "
                f"{replication_pass_count}/{len(replication_rows)}, invariant "
                f"pass {invariant_pass_count}/{len(invariant_rows)}."
            )

        rows.append(
            {
                "policy_path_protocol_component_closure_rollup_row_id": (
                    f"policy_path_protocol_component_closure_rollup::{idx:04d}"
                ),
                "protocol_component": component,
                "protocol_component_gate": component,
                "component_role": role,
                "source_field_count": str(len(source_rows)),
                "source_field_pass_count": str(source_pass_count),
                "source_field_blocked_count": str(source_blocked_count),
                "review_only_source_hit_count": str(review_only_hits),
                "promotion_grade_source_evidence_count": str(promotion_grade_hits),
                "source_evidence_status": source_status,
                "independent_replication_design_field_count": str(
                    len(replication_rows)
                ),
                "independent_replication_design_pass_count": str(
                    replication_pass_count
                ),
                "independent_replication_design_blocked_count": str(
                    replication_blocked_count
                ),
                "independent_replication_design_status": replication_status,
                "authored_invariant_field_count": str(len(invariant_rows)),
                "authored_invariant_design_pass_count": str(invariant_pass_count),
                "authored_invariant_design_blocked_count": str(
                    invariant_blocked_count
                ),
                "invariant_design_status": invariant_status,
                "linked_source_evidence_audit_row_ids": _join_unique(
                    [
                        row.get(
                            "policy_path_field_specific_source_evidence_audit_row_id",
                            "",
                        )
                        for row in source_rows
                    ]
                ),
                "linked_independent_replication_design_row_ids": _join_unique(
                    [
                        row.get(
                            "policy_path_independent_replication_target_design_row_id",
                            "",
                        )
                        for row in replication_rows
                    ]
                ),
                "linked_authored_invariant_design_row_ids": _join_unique(
                    [
                        row.get(
                            "policy_path_authored_fail_closed_invariant_design_row_id",
                            "",
                        )
                        for row in invariant_rows
                    ]
                ),
                "linked_component_gate_execution_rollup_row_ids": execution_row.get(
                    "policy_path_component_gate_execution_rollup_row_id", ""
                ),
                "required_pass_rule_result_status": (
                    "pass_field_specific_source_evidence_or_applicable_design_gate_"
                    "or_nonpromotional_component_gate_execution"
                ),
                "observed_pass_rule_result_statuses": _join_unique(
                    [row.get("pass_rule_result_status", "") for row in source_rows]
                ),
                "observed_replication_admission_statuses": _join_unique(
                    [
                        row.get("replication_admission_status", "")
                        for row in replication_rows
                    ]
                ),
                "observed_invariant_admission_statuses": _join_unique(
                    [
                        row.get("invariant_admission_status", "")
                        for row in invariant_rows
                    ]
                ),
                "component_closure_status": component_closure_status,
                "protocol_admission_status": (
                    "blocked_protocol_component_closure_rollup_not_complete_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": next_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_component_gate_execution_rollup_rows(
    *,
    policy_path_source_extraction_result_adjudication_rows: list[dict[str, str]],
    policy_path_independent_replication_target_design_rows: list[dict[str, str]],
    policy_path_authored_fail_closed_invariant_design_rows: list[dict[str, str]],
    policy_path_project_authored_bps_year_event_exposure_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    def decimal_or_none(value: object) -> Decimal | None:
        text = str(value).strip()
        if not text:
            return None
        try:
            return Decimal(text)
        except InvalidOperation:
            return None

    protected_fields = [
        "candidate_bps_year_exposure",
        "bps_year_exposure_output",
        "admitted_bps_year_exposure_output",
        "candidate_gdp_share_drag_per_100bp_year",
    ]
    event_rows = policy_path_project_authored_bps_year_event_exposure_rows
    canonical_event_rows = [
        row for row in event_rows if row.get("canonical_strip_member") == "true"
    ]
    replicated_event_rows = [
        row
        for row in canonical_event_rows
        if row.get("event_exposure_row_status", "").startswith("pass_")
        and row.get("event_replication_status", "").startswith("pass_")
    ]
    event_exposure_protected_clean = bool(event_rows) and all(
        row.get(field, "") == ""
        and row.get("enters_main_ratio") == "false"
        and row.get("evidence_mode_enabled") == "false"
        and row.get("denominator_prior_update_allowed") == "false"
        for row in event_rows
        for field in protected_fields
    )
    direct_strip_event_grid_resolved = (
        bool(replicated_event_rows)
        and event_exposure_protected_clean
        and all(
            row.get("event_date", "")
            and row.get("horizon_start", "")
            and row.get("horizon_end", "")
            and row.get("reference_period_start", "")
            and row.get("reference_period_end", "")
            and decimal_or_none(row.get("event_overlap_year_fraction", "")) is not None
            and row.get("source_input_hash_status", "").startswith("pass_")
            for row in replicated_event_rows
        )
    )
    direct_strip_loading_resolved = (
        bool(replicated_event_rows)
        and event_exposure_protected_clean
        and all(
            row.get("scalar_pca_shortcut_status")
            == "pass_no_scalar_or_pca_shortcut_per_instrument_source_cell_used"
            and row.get("canonical_strip_role")
            == "canonical_disjoint_quarterly_strip_ed1_ed4"
            for row in replicated_event_rows
        )
    )
    project_formula_resolved = (
        bool(replicated_event_rows)
        and event_exposure_protected_clean
        and all(
            row.get("formula_classification")
            == "project_authored_normalization_from_source_authored_policy_path_inputs"
            and row.get("formula_text") == PROJECT_AUTHORED_BPS_YEAR_FORMULA
            and row.get("unit_conversion_rule")
            == "source_reported_percentage_points_to_basis_points_multiplier_100"
            and row.get("sign_transform_rule")
            == "source_rate_change_signed_as_reported_not_raw_price_quote"
            and (
                decimal_or_none(row.get("component_bps_year_abs_diff_review_only", ""))
                is not None
            )
            and (
                decimal_or_none(
                    row.get(
                        "event_horizon_100bp_year_exposure_abs_diff_review_only", ""
                    )
                )
                is not None
            )
            and decimal_or_none(
                row.get("component_bps_year_abs_diff_review_only", "")
            )
            <= Decimal("0.00000001")
            and decimal_or_none(
                row.get(
                    "event_horizon_100bp_year_exposure_abs_diff_review_only", ""
                )
            )
            <= Decimal("0.00000001")
            for row in replicated_event_rows
        )
    )

    adjudication_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    replication_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    invariant_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_source_extraction_result_adjudication_rows:
        adjudication_by_component[row.get("protocol_component", "")].append(row)
    for row in policy_path_independent_replication_target_design_rows:
        replication_by_component[row.get("protocol_component", "")].append(row)
    for row in policy_path_authored_fail_closed_invariant_design_rows:
        invariant_by_component[row.get("protocol_component", "")].append(row)

    components = [
        "source_cell_unit_sign",
        "event_date_horizon_grid",
        "loading_back_transform",
        "bps_year_formula",
        "independent_replication_target_tolerance",
        "denominator_isolation",
        "promotion_rule",
    ]
    allowed_use = "policy_path_component_gate_execution_rollup_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_component_gate_execution_rollup_not_bps_year_or_runtime_input"
    )
    rows: list[dict[str, str]] = []
    for idx, component in enumerate(components, start=1):
        adjudication_rows = adjudication_by_component.get(component, [])
        replication_rows = replication_by_component.get(component, [])
        invariant_rows = invariant_by_component.get(component, [])
        source_rows = [
            row
            for row in adjudication_rows
            if row.get(
                "policy_path_locator_candidate_pass_rule_review_decision_packet_row_id",
                "",
            )
        ]

        source_pass_count = sum(
            row.get("field_gate_status", "").startswith("pass_")
            for row in source_rows
        )
        source_blocked_count = sum(
            row.get("field_gate_status", "").startswith("blocked")
            for row in source_rows
        )
        source_unit_sign_resolved = (
            component == "source_cell_unit_sign"
            and bool(source_rows)
            and all(
                row.get("source_evidence_status", "").startswith(
                    "pass_machine_audited"
                )
                for row in source_rows
            )
            and any(
                row.get("authored_field_name", "")
                == "source_cell_unit_sign__price_to_rate_sign_transform"
                and row.get("parsed_value", "")
                == "source_cells_are_reported_rate_changes_not_raw_futures_prices"
                for row in source_rows
            )
        )
        project_authored_component_resolved = (
            source_unit_sign_resolved
            or (
                component == "event_date_horizon_grid"
                and direct_strip_event_grid_resolved
            )
            or (
                component == "loading_back_transform"
                and direct_strip_loading_resolved
            )
            or (component == "bps_year_formula" and project_formula_resolved)
        )
        if project_authored_component_resolved:
            source_pass_count = len(source_rows)
            source_blocked_count = 0
        locator_pass_count = sum(
            row.get("reviewer_status", "")
            == "pass_locator_candidate_matches_minimum_pass_rule_review_inputs"
            for row in source_rows
        )
        locator_blocked_count = len(source_rows) - locator_pass_count
        replication_pass_count = sum(
            row.get("replication_admission_status", "").startswith("pass_")
            for row in replication_rows
        )
        replication_blocked_count = sum(
            row.get("replication_admission_status", "").startswith("blocked")
            for row in replication_rows
        )
        event_exposure_replication_pass = (
            component == "independent_replication_target_tolerance"
            and bool(replication_rows)
            and bool(policy_path_project_authored_bps_year_event_exposure_rows)
            and any(
                row.get("event_exposure_row_status", "").startswith("pass_")
                and row.get("event_replication_status", "").startswith("pass_")
                for row in policy_path_project_authored_bps_year_event_exposure_rows
            )
            and all(
                row.get("candidate_bps_year_exposure", "") == ""
                and row.get("bps_year_exposure_output", "") == ""
                and row.get("admitted_bps_year_exposure_output", "") == ""
                and row.get("candidate_gdp_share_drag_per_100bp_year", "") == ""
                and row.get("protocol_admission_status", "").startswith("blocked")
                and row.get(
                    "policy_path_100bp_year_normalization_status", ""
                ).startswith("blocked")
                and row.get("enters_main_ratio") == "false"
                and row.get("evidence_mode_enabled") == "false"
                and row.get("denominator_prior_update_allowed") == "false"
                for row in policy_path_project_authored_bps_year_event_exposure_rows
            )
        )
        if event_exposure_replication_pass:
            replication_pass_count = len(replication_rows)
            replication_blocked_count = 0
        invariant_pass_count = sum(
            row.get("invariant_admission_status", "").startswith("pass_")
            for row in invariant_rows
        )
        invariant_blocked_count = sum(
            row.get("invariant_admission_status", "").startswith("blocked")
            for row in invariant_rows
        )

        if source_rows:
            role = "source_evidence_protocol_component"
            next_action = "promote_only_after_source_field_and_sibling_gates_pass"
        elif replication_rows:
            role = "independent_replication_protocol_component"
            next_action = "execute_independent_replication_target_tolerance"
        else:
            role = "authored_invariant_protocol_component"
            next_action = "execute_authored_fail_closed_invariant"

        component_pass = (
            (not source_rows or source_pass_count == len(source_rows))
            and (
                not replication_rows
                or replication_pass_count == len(replication_rows)
            )
            and (not invariant_rows or invariant_pass_count == len(invariant_rows))
        )
        component_gate_status = (
            "pass_component_gate_execution"
            if component_pass
            else "blocked_component_gate_execution_incomplete"
        )
        if component_pass:
            next_action = (
                "component_gate_execution_passed_preserve_until_full_protocol_conjunction"
            )
        component_gate_execution_status = (
            "blocked_policy_path_protocol_conjunction_incomplete"
            if component_gate_status.startswith("blocked")
            else "pass_policy_path_component_ready_for_full_protocol_conjunction"
        )
        observed_source_statuses = _join_unique(
            [row.get("source_evidence_status", "") for row in source_rows]
        )
        observed_replication_statuses = _join_unique(
            [
                row.get("replication_admission_status", "")
                for row in replication_rows
            ]
        )
        if component_pass:
            exact_blocker = ""
        elif component == "independent_replication_target_tolerance" and (
            event_exposure_replication_pass
        ):
            exact_blocker = ""
        elif project_authored_component_resolved:
            exact_blocker = ""
            next_action = (
                "project_authored_component_resolved_preserve_nonpromotion_until_admission_consumer"
            )
        elif component == "bps_year_formula" and (
            "terminal_no_source_authored_bps_year_formula" in observed_source_statuses
            or "terminal_no_source_authored_bps_year_horizon_weights"
            in observed_source_statuses
        ):
            exact_blocker = (
                "The source-authored bps-year formula route is terminal for the current source bundle: "
                "hash-backed sources provide review-only one-year path snippets "
                "and contract reference intervals/year fractions, but no "
                "source-authored bps-year aggregation formula, component formula, "
                "or horizon-weight protocol. The next admissible path is a "
                "project-authored dimensional accounting formula backed by "
                "source-authored inputs and independent event-exposure replication."
            )
            next_action = (
                "execute_project_authored_bps_year_accounting_protocol_and_independent_event_exposure_replication"
            )
        elif component == "independent_replication_target_tolerance" and (
            "blocked_independent_event_exposure_replication_not_executed"
            in observed_replication_statuses
        ):
            exact_blocker = (
                "independent_replication_target_tolerance remains blocked "
                "because the independent event-level rebuild of the "
                "project-authored bps-year accounting formula from "
                "source-authored inputs has not executed."
            )
            next_action = (
                "implement_independent_event_level_bps_year_exposure_rebuild_from_source_inputs"
            )
        else:
            exact_blocker = (
                f"{component} cannot move: source fields pass "
                f"{source_pass_count}/{len(source_rows)}, locator review-pass "
                f"nonpromotional rows {locator_pass_count}, replication pass "
                f"{replication_pass_count}/{len(replication_rows)}, invariant "
                f"pass {invariant_pass_count}/{len(invariant_rows)}."
            )
        rows.append(
            {
                "policy_path_component_gate_execution_rollup_row_id": (
                    f"policy_path_component_gate_execution_rollup::{idx:04d}"
                ),
                "protocol_component": component,
                "protocol_component_gate": component,
                "component_role": role,
                "adjudication_row_count": str(len(adjudication_rows)),
                "source_field_count": str(len(source_rows)),
                "source_field_pass_count": str(source_pass_count),
                "source_field_blocked_count": str(source_blocked_count),
                "locator_review_pass_nonpromotional_count": str(locator_pass_count),
                "locator_review_blocked_count": str(locator_blocked_count),
                "promotion_grade_source_evidence_count": "0",
                "independent_replication_design_field_count": str(
                    len(replication_rows)
                ),
                "independent_replication_design_pass_count": str(
                    replication_pass_count
                ),
                "independent_replication_design_blocked_count": str(
                    replication_blocked_count
                ),
                "authored_invariant_field_count": str(len(invariant_rows)),
                "authored_invariant_design_pass_count": str(invariant_pass_count),
                "authored_invariant_design_blocked_count": str(
                    invariant_blocked_count
                ),
                "linked_source_extraction_result_adjudication_row_ids": _join_unique(
                    [
                        row.get(
                            "policy_path_source_extraction_result_adjudication_row_id",
                            "",
                        )
                        for row in adjudication_rows
                    ]
                ),
                "linked_independent_replication_design_row_ids": _join_unique(
                    [
                        row.get(
                            "policy_path_independent_replication_target_design_row_id",
                            "",
                        )
                        for row in replication_rows
                    ]
                ),
                "linked_authored_invariant_design_row_ids": _join_unique(
                    [
                        row.get(
                            "policy_path_authored_fail_closed_invariant_design_row_id",
                            "",
                        )
                        for row in invariant_rows
                    ]
                ),
                "observed_source_evidence_statuses": observed_source_statuses,
                "observed_field_gate_statuses": _join_unique(
                    [row.get("field_gate_status", "") for row in adjudication_rows]
                ),
                "component_gate_status": component_gate_status,
                "component_gate_execution_status": component_gate_execution_status,
                "protocol_admission_status": (
                    "blocked_component_gate_execution_rollup_not_complete_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": next_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


PROJECT_AUTHORED_BPS_YEAR_FORMULA = (
    "normalized_100bp_year_exposure_e_h = "
    "sum_i(rate_change_bps_signed_e_i * overlap_year_fraction_e_i_h) / 100"
)


def policy_path_project_authored_bps_year_protocol_contract_rows(
    *,
    policy_path_source_extraction_result_adjudication_rows: list[dict[str, str]],
    policy_path_component_gate_execution_rollup_rows: list[dict[str, str]],
    policy_path_project_authored_bps_year_event_exposure_rows: list[dict[str, str]]
    | None = None,
) -> list[dict[str, str]]:
    adjudication_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_source_extraction_result_adjudication_rows:
        adjudication_by_component[row.get("protocol_component", "")].append(row)
    rollup_by_component = {
        row.get("protocol_component", ""): row
        for row in policy_path_component_gate_execution_rollup_rows
    }
    source_input_components = [
        "source_cell_unit_sign",
        "event_date_horizon_grid",
        "loading_back_transform",
    ]
    source_input_row_ids = [
        row.get("policy_path_source_extraction_result_adjudication_row_id", "")
        for component in source_input_components
        for row in adjudication_by_component.get(component, [])
        if row.get("source_evidence_status", "").startswith("pass_machine_audited")
    ]
    bps_formula_row_ids = [
        row.get("policy_path_source_extraction_result_adjudication_row_id", "")
        for row in adjudication_by_component.get("bps_year_formula", [])
    ]
    rollup_row_ids = [
        row.get("policy_path_component_gate_execution_rollup_row_id", "")
        for row in policy_path_component_gate_execution_rollup_rows
    ]
    blocked_use = (
        "denominator_prior;main_ratio;Evidence_Mode;pricing;holder_allocation;"
        "raw_rate_shock;reset_calendar;policy_failure_claim;empirical_threshold"
    )
    allowed_use = "project_authored_bps_year_protocol_contract_only"
    claim_boundary = (
        "project_authored_bps_year_accounting_protocol_not_denominator_evidence"
    )
    source_status = (
        "pass_source_authored_inputs_available_nonpromotional"
        if source_input_row_ids
        else "blocked_source_authored_inputs_missing"
    )
    event_exposure_rows = policy_path_project_authored_bps_year_event_exposure_rows or []
    event_exposure_replicated = (
        bool(event_exposure_rows)
        and any(
            row.get("event_exposure_row_status", "").startswith("pass_")
            and row.get("event_replication_status", "").startswith("pass_")
            for row in event_exposure_rows
        )
        and all(
            row.get("candidate_rate_change_bps", "") == ""
            and row.get("candidate_bps_year_component", "") == ""
            and row.get("candidate_bps_year_exposure", "") == ""
            and row.get("bps_year_exposure_output", "") == ""
            and row.get("admitted_bps_year_exposure_output", "") == ""
            and row.get("candidate_gdp_share_drag_per_100bp_year", "") == ""
            and row.get("enters_main_ratio") == "false"
            and row.get("evidence_mode_enabled") == "false"
            and row.get("denominator_prior_update_allowed") == "false"
            for row in event_exposure_rows
        )
    )
    replication_status = (
        "pass_independent_event_exposure_replication_executed_nonpromotional"
        if event_exposure_replicated
        else "blocked_independent_event_exposure_replication_not_executed"
    )
    source_input_complete_gate_status = (
        "pass_project_authored_source_input_complete_gate_rebuilt_and_replicated_nonpromotional"
        if event_exposure_replicated and source_status.startswith("pass_")
        else "blocked_source_input_complete_gate_pending_independent_rebuild"
    )
    source_input_complete_gate_blocker = (
        "Source-input contract and independent event-level rebuild now cover "
        "the project-authored ED-strip exposure accounting route, but the "
        "protocol remains nonpromotional until the admission consumer preserves "
        "blank denominator/runtime outputs."
        if source_input_complete_gate_status.startswith("pass_")
        else (
            "The current source-input bundle is review-only and nonpromotional; "
            "event exposure cannot be admitted until the input parse is rebuilt "
            "independently."
        )
    )
    source_input_complete_gate_next_action = (
        "consume_replicated_event_exposure_in_admission_consumer_without_denominator_promotion"
        if source_input_complete_gate_status.startswith("pass_")
        else "materialize_source_input_contract_and_replicated_event_exposure_table"
    )
    rows: list[dict[str, str]] = []
    specs = [
        (
            "source_authored_input_boundary",
            "input_boundary",
            "Separate source-authored economic inputs from RateWall-authored accounting formula.",
            "not_applicable_boundary_row",
            "not_applicable_no_exposure_value",
            "false",
            "false",
            source_status,
            replication_status,
            "pass_project_authored_formula_boundary_declared_fail_closed",
            "Source inputs may support only deterministic exposure-accounting inputs; they do not admit a bps-year value without independent event-exposure replication.",
            "build_independent_event_level_bps_year_exposure_replication_target",
            source_input_row_ids,
        ),
        (
            "formula_text",
            "project_authored_formula",
            "Define deterministic bps-year exposure area from source-authored rate changes and horizon overlaps.",
            PROJECT_AUTHORED_BPS_YEAR_FORMULA,
            "basis_points_times_years_divided_by_100",
            "false",
            "true",
            source_status,
            replication_status,
            "pass_project_authored_accounting_formula_declared_fail_closed",
            "Formula is RateWall-authored dimensional accounting, not source-authored monetary-policy evidence; output remains blocked until independent event-level replication passes.",
            "execute_two_implementation_event_exposure_replication_before_admission",
            bps_formula_row_ids,
        ),
        (
            "source_input_complete_gate",
            "gate",
            "Require hash-backed rate-change, unit/sign, contract interval, overlap, missingness, and back-transform inputs.",
            PROJECT_AUTHORED_BPS_YEAR_FORMULA,
            "basis_points_times_years_divided_by_100",
            "false",
            "false",
            source_status,
            replication_status,
            source_input_complete_gate_status,
            source_input_complete_gate_blocker,
            source_input_complete_gate_next_action,
            source_input_row_ids,
        ),
        (
            "promotion_boundary",
            "nonpromotion_boundary",
            "Preserve all denominator, prior, Evidence Mode, main-ratio, raw-shock, and runtime switches as disabled.",
            "not_applicable_boundary_row",
            "not_applicable_no_exposure_value",
            "false",
            "false",
            "pass_fail_closed_boundary_specified",
            replication_status,
            "pass_project_authored_protocol_nonpromotion_boundary",
            "Project-authored accounting protocol may define the method but cannot populate bps-year, GDP-share drag, priors, or main-ratio fields by itself.",
            "keep_protocol_nonpromotional_until_replication_and_full_gate_conjunction_pass",
            rollup_row_ids,
        ),
    ]
    for idx, spec in enumerate(specs, start=1):
        (
            component_id,
            component_role,
            requirement,
            formula_text,
            unit_check,
            source_flag,
            project_flag,
            source_input_status,
            replication_status,
            contract_status,
            blocker,
            next_action,
            linked_rows,
        ) = spec
        rows.append(
            {
                "project_authored_bps_year_protocol_contract_row_id": (
                    f"project_authored_bps_year_protocol_contract::{idx:04d}"
                ),
                "component_id": component_id,
                "component_role": component_role,
                "protocol_requirement": requirement,
                "formula_classification": (
                    "project_authored_normalization_from_source_authored_policy_path_inputs"
                ),
                "formula_text": formula_text,
                "dimensional_unit_check": unit_check,
                "source_authored_input_flag": source_flag,
                "project_authored_formula_flag": project_flag,
                "linked_source_input_contract_row_ids": "",
                "linked_component_gate_execution_rollup_row_ids": _join_unique(
                    [
                        rollup_by_component.get(component, {}).get(
                            "policy_path_component_gate_execution_rollup_row_id",
                            "",
                        )
                        for component in [
                            "source_cell_unit_sign",
                            "event_date_horizon_grid",
                            "loading_back_transform",
                            "bps_year_formula",
                            "independent_replication_target_tolerance",
                        ]
                    ]
                ),
                "linked_source_extraction_result_adjudication_row_ids": _join_unique(
                    linked_rows
                ),
                "source_input_contract_status": source_input_status,
                "replication_requirement_status": replication_status,
                "protocol_contract_status": contract_status,
                "protocol_admission_status": (
                    "blocked_project_authored_accounting_protocol_pending_independent_replication"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_independent_bps_year_event_exposure_replication"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": blocker,
                "next_backend_action": next_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_project_authored_bps_year_source_input_contract_rows(
    *,
    policy_path_source_extraction_result_adjudication_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    field_roles = {
        "source_cell_unit_sign__source_instrument_code": "instrument_code",
        "source_cell_unit_sign__source_workbook_cell_unit": "source_cell_rate_change_unit",
        "source_cell_unit_sign__percentage_point_basis_point_conversion": "percentage_point_to_bps_conversion",
        "source_cell_unit_sign__price_to_rate_sign_transform": "price_to_rate_sign",
        "source_cell_unit_sign__literal_na_handling": "missingness_rule",
        "source_cell_unit_sign__effective_contract_family_by_era": "contract_family_by_era",
        "event_date_horizon_grid__event_date": "event_date",
        "event_date_horizon_grid__event_window": "event_window",
        "event_date_horizon_grid__contract_reference_interval": "contract_reference_interval",
        "event_date_horizon_grid__event_specific_horizon_start_end_dates": "event_specific_interval_dates",
        "bps_year_formula__horizon_weights": "horizon_overlap_year_fraction",
        "bps_year_formula__rate_change_unit_conversion": "rate_change_unit_conversion",
        "bps_year_formula__sign_convention": "sign_convention_crosscheck",
        "loading_back_transform__factor_definition": "pca_factor_definition",
        "loading_back_transform__instrument_loadings": "pca_instrument_loadings",
        "loading_back_transform__rotation_sign_rule": "pca_rotation_sign_rule",
        "loading_back_transform__scalar_to_cell_back_transform": "pca_scalar_to_cell_backtransform_review",
        "loading_back_transform__source_code_replication_command": "source_code_replication_command",
    }
    by_field = {
        row.get("authored_field_name", ""): row
        for row in policy_path_source_extraction_result_adjudication_rows
    }
    blocked_use = (
        "bps_year_exposure_output;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar"
    )
    rows: list[dict[str, str]] = []
    for idx, (field_name, input_role) in enumerate(field_roles.items(), start=1):
        source = by_field.get(field_name, {})
        source_status = source.get("source_evidence_status", "")
        if source_status.startswith("pass_machine_audited"):
            input_status = "pass_source_authored_input_available_nonpromotional"
            blocker = (
                "Source-authored input is hash-backed and review-only; it can "
                "feed the project-authored formula only after independent "
                "event-exposure replication passes."
            )
            next_action = "use_as_input_to_independent_event_exposure_rebuild"
        elif "source_authored_bps_year" in source_status:
            input_status = (
                "blocked_source_authored_formula_absent_project_formula_allowed"
            )
            blocker = (
                "No source-authored bps-year formula or horizon-weight protocol "
                "exists in the current bundle; this is now treated as a "
                "nonfatal formula-source gap because the RateWall formula is "
                "project-authored accounting."
            )
            next_action = (
                "keep_source_authored_formula_absence_recorded_and_execute_project_authored_replication_protocol"
            )
        else:
            input_status = source.get(
                "field_gate_status", "blocked_source_input_missing"
            )
            blocker = (
                "Required source-authored input remains unavailable or manually "
                "authenticated; affected event exposures must block."
            )
            next_action = source.get(
                "next_action_if_blocked",
                "resolve_source_input_before_event_exposure_admission",
            )
        rows.append(
            {
                "project_authored_bps_year_source_input_contract_row_id": (
                    f"project_authored_bps_year_source_input_contract::{idx:04d}"
                ),
                "input_id": input_role,
                "protocol_component": source.get("protocol_component", ""),
                "authored_field_name": field_name,
                "input_role": input_role,
                "source_family": source.get("source_family", ""),
                "source_artifact_path": source.get("source_path", ""),
                "source_artifact_sha256": source.get("source_sha256", ""),
                "source_table_or_code_path": source.get("source_row_or_cell", ""),
                "source_column_or_equation": source.get("source_row_or_cell", ""),
                "source_literal": source.get("source_literal_value", ""),
                "parsed_value": source.get("parsed_value", ""),
                "parsed_unit": source.get("parsed_unit", ""),
                "parsed_sign": source.get("parsed_sign", ""),
                "source_authored_input_flag": (
                    "false" if input_status.endswith("project_formula_allowed") else "true"
                ),
                "project_authored_formula_flag": "false",
                "source_input_status": input_status,
                "allowed_use_class": "source_input_to_project_authored_bps_year_formula",
                "forbidden_use_class": "source_authored_bps_year_formula_or_denominator_evidence",
                "linked_source_extraction_result_adjudication_row_id": source.get(
                    "policy_path_source_extraction_result_adjudication_row_id", ""
                ),
                "protocol_admission_status": (
                    "blocked_project_authored_accounting_protocol_pending_independent_replication"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_independent_bps_year_event_exposure_replication"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": blocker,
                "next_backend_action": next_action,
                "allowed_use": "project_authored_bps_year_source_input_contract_only",
                "blocked_use": blocked_use,
                "claim_boundary": (
                    "source_input_contract_not_bps_year_exposure_or_denominator"
                ),
                **_false_fields(),
            }
        )
    return rows


def policy_path_project_authored_bps_year_replication_protocol_rows(
    *,
    policy_path_project_authored_bps_year_event_exposure_rows: list[
        dict[str, str]
    ]
    | None = None,
) -> list[dict[str, str]]:
    blocked_use = (
        "denominator_prior;main_ratio;Evidence_Mode;pricing;holder_allocation;"
        "raw_rate_shock;reset_calendar;policy_failure_claim;empirical_threshold"
    )
    specs = [
        (
            "event_instrument_input_parse",
            "source-cell parse",
            "event_id x instrument_code x source_vintage",
            "event_id;event_date;instrument_code;source_cell_value;source_cell_unit;source_hash",
        ),
        (
            "interval_overlap_rebuild",
            "contract interval and horizon-overlap rebuild",
            "event_id x instrument_code x horizon_q",
            "reference_period_start;reference_period_end;horizon_start;horizon_end;overlap_year_fraction",
        ),
        (
            "bps_year_component_rebuild",
            "component formula rebuild",
            "event_id x instrument_code x horizon_q",
            "rate_change_bps_signed;overlap_year_fraction;component_bps_year",
        ),
        (
            "event_horizon_exposure_sum",
            "event horizon exposure sum",
            "event_id x horizon_q",
            "normalized_100bp_year_exposure;component_count;blocked_component_count",
        ),
        (
            "double_implementation_tolerance",
            "independent implementation comparison",
            "event_id x horizon_q",
            "implementation_1_value;implementation_2_value;absolute_difference;replication_status",
        ),
        (
            "nonpromotion_boundary",
            "blocked-output invariant",
            "replication_target",
            "candidate_gdp_share_drag_per_100bp_year;enters_main_ratio;evidence_mode_enabled;denominator_prior_update_allowed",
        ),
    ]
    event_exposure_rows = policy_path_project_authored_bps_year_event_exposure_rows or []
    event_replication_executed = (
        bool(event_exposure_rows)
        and any(
            row.get("event_exposure_row_status", "").startswith("pass_")
            and row.get("event_replication_status", "").startswith("pass_")
            for row in event_exposure_rows
        )
        and all(
            row.get("candidate_bps_year_exposure", "") == ""
            and row.get("bps_year_exposure_output", "") == ""
            and row.get("admitted_bps_year_exposure_output", "") == ""
            and row.get("candidate_gdp_share_drag_per_100bp_year", "") == ""
            and row.get("enters_main_ratio") == "false"
            and row.get("evidence_mode_enabled") == "false"
            and row.get("denominator_prior_update_allowed") == "false"
            for row in event_exposure_rows
        )
    )
    rows: list[dict[str, str]] = []
    for idx, (target_id, gate, grain, expected_fields) in enumerate(specs, start=1):
        rows.append(
            {
                "project_authored_bps_year_replication_protocol_row_id": (
                    f"project_authored_bps_year_replication_protocol::{idx:04d}"
                ),
                "replication_target_id": target_id,
                "replication_gate": gate,
                "replication_target_artifact": (
                    "ratewall_policy_path_project_authored_bps_year_event_exposure.csv"
                ),
                "replication_target_row_grain": grain,
                "formula_classification": (
                    "project_authored_normalization_from_source_authored_policy_path_inputs"
                ),
                "formula_text": PROJECT_AUTHORED_BPS_YEAR_FORMULA,
                "expected_output_fields": expected_fields,
                "implementation_1_requirement": (
                    "primary_databook_builder_deterministic_parse"
                ),
                "implementation_2_requirement": (
                    "independent_script_or_runtime_rebuild_from_hash_backed_raw_sources"
                ),
                "numeric_tolerance": "1e-08",
                "tolerance_unit": "absolute_normalized_100bp_year_exposure",
                "tolerance_comparison": (
                    "abs(implementation_1_value - implementation_2_value) <= tolerance"
                ),
                "pass_status_value": (
                    "pass_project_authored_bps_year_exposure_replicated_from_source_inputs"
                ),
                "blocked_status_value": (
                    "blocked_no_independent_bps_year_event_exposure_replication"
                ),
                "replication_protocol_status": (
                    "pass_independent_event_exposure_replication_executed_nonpromotional"
                    if event_replication_executed
                    else "blocked_independent_event_exposure_replication_not_executed"
                ),
                "protocol_admission_status": (
                    "blocked_project_authored_accounting_protocol_pending_full_protocol_conjunction"
                    if event_replication_executed
                    else "blocked_project_authored_accounting_protocol_pending_independent_replication"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_review_only_event_exposure_replicated_not_admitted"
                    if event_replication_executed
                    else "blocked_no_independent_bps_year_event_exposure_replication"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    "Independent event-level exposure replication is executed "
                    "in the event-exposure artifact, but the project-authored "
                    "accounting protocol is still not admitted until all "
                    "policy-path component and promotion gates pass."
                    if event_replication_executed
                    else "Replication target is specified, but no independent "
                    "event-level 100bp-year exposure rebuild has passed."
                ),
                "next_backend_action": (
                    "evaluate_full_policy_path_protocol_conjunction_after_event_exposure_replication"
                    if event_replication_executed
                    else "implement_independent_event_level_bps_year_exposure_rebuild"
                ),
                "allowed_use": "project_authored_bps_year_replication_protocol_only",
                "blocked_use": blocked_use,
                "claim_boundary": (
                    "replication_protocol_not_bps_year_exposure_or_denominator"
                ),
                **_false_fields(),
            }
        )
    return rows


def policy_path_full_protocol_admission_gate_summary_rows(
    *,
    policy_path_protocol_component_closure_rollup_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    required_components = [
        "source_cell_unit_sign",
        "event_date_horizon_grid",
        "loading_back_transform",
        "bps_year_formula",
        "independent_replication_target_tolerance",
        "denominator_isolation",
        "promotion_rule",
    ]
    by_component = {
        row.get("protocol_component", ""): row
        for row in policy_path_protocol_component_closure_rollup_rows
    }
    observed_components = [
        component for component in required_components if component in by_component
    ]
    closed_components = [
        component
        for component in required_components
        if by_component.get(component, {})
        .get("component_closure_status", "")
        .startswith("pass_")
    ]
    blocked_components = [
        component
        for component in required_components
        if not by_component.get(component, {})
        .get("component_closure_status", "")
        .startswith("pass_")
    ]
    source_components = [
        "source_cell_unit_sign",
        "event_date_horizon_grid",
        "loading_back_transform",
        "bps_year_formula",
    ]
    source_closed = [component for component in source_components if component in closed_components]
    source_promotion_grade_count = sum(
        int(by_component.get(component, {}).get("promotion_grade_source_evidence_count") or "0")
        for component in source_components
    )
    component_statuses = _join_unique(
        [
            f"{component}={by_component.get(component, {}).get('component_closure_status', 'missing')}"
            for component in required_components
        ]
    )
    remaining_blockers = _short_join(
        [
            by_component.get(component, {}).get(
                "exact_blocker", f"{component} missing from component closure rollup"
            )
            for component in blocked_components
        ],
        limit=1200,
    )
    required_next_actions = _join_unique(
        [
            by_component.get(component, {}).get("next_backend_action", "")
            for component in blocked_components
        ]
    )
    full_gate_pass = len(closed_components) == len(required_components)
    full_gate_status = (
        "pass_full_policy_path_protocol_gate_conjunction"
        if full_gate_pass
        else "blocked_full_policy_path_protocol_gate_conjunction_incomplete"
    )
    allowed_use = "policy_path_full_protocol_admission_gate_summary_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_full_protocol_admission_gate_summary_not_bps_year_or_runtime_input"
    )
    exact_blocker = (
        ""
        if full_gate_pass
        else (
            "Full policy-path bps-year protocol remains blocked because "
            f"{len(blocked_components)} of {len(required_components)} required "
            "protocol components are not closed."
        )
    )
    return [
        {
            "policy_path_full_protocol_admission_gate_summary_row_id": (
                "policy_path_full_protocol_admission_gate_summary::0001"
            ),
            "protocol_id": "policy_path_bps_year_full_protocol",
            "protocol_label": "Policy-path bps-year full admission gate",
            "component_count": str(len(required_components)),
            "closed_component_count": str(len(closed_components)),
            "blocked_component_count": str(len(blocked_components)),
            "required_protocol_components": ";".join(required_components),
            "observed_protocol_components": ";".join(observed_components),
            "component_closure_statuses": component_statuses,
            "blocked_component_ids": ";".join(blocked_components),
            "remaining_blockers": remaining_blockers,
            "required_next_actions": required_next_actions,
            "source_component_count": str(len(source_components)),
            "source_component_closed_count": str(len(source_closed)),
            "source_promotion_grade_evidence_count": str(source_promotion_grade_count),
            "independent_replication_component_status": by_component.get(
                "independent_replication_target_tolerance", {}
            ).get("component_closure_status", "missing_component_closure_status"),
            "denominator_isolation_component_status": by_component.get(
                "denominator_isolation", {}
            ).get("component_closure_status", "missing_component_closure_status"),
            "promotion_rule_component_status": by_component.get(
                "promotion_rule", {}
            ).get("component_closure_status", "missing_component_closure_status"),
            "full_gate_conjunction_status": full_gate_status,
            "protocol_admission_status": (
                "blocked_full_policy_path_protocol_not_admitted"
            ),
            "policy_path_100bp_year_normalization_status": (
                "blocked_no_admitted_bps_year_policy_path"
            ),
            "non_admission_boundary": (
                "summary row cannot admit bps-year exposure unless every "
                "component closure row passes and runtime switches remain guarded"
            ),
            "linked_component_closure_rollup_row_ids": _join_unique(
                [
                    row.get("policy_path_protocol_component_closure_rollup_row_id", "")
                    for row in policy_path_protocol_component_closure_rollup_rows
                ]
            ),
            "candidate_rate_change_bps": "",
            "candidate_bps_year_component": "",
            "candidate_bps_year_exposure": "",
            "bps_year_exposure_output": "",
            "candidate_gdp_share_drag_per_100bp_year": "",
            "candidate_ci_lower": "",
            "candidate_ci_upper": "",
            "exact_blocker": exact_blocker,
            "next_backend_action": (
                "apply_admission_consumer_promotion_rule_before_any_output_use"
                if full_gate_pass
                else "close_all_protocol_component_gates_before_protocol_admission"
            ),
            "allowed_use": allowed_use,
            "blocked_use": blocked_use,
            "claim_boundary": claim_boundary,
            **_false_fields(),
        }
    ]


def policy_path_source_bundle_field_exhaustion_decision_rows(
    *,
    policy_path_terminal_no_hit_closure_rows: list[dict[str, str]],
    policy_path_independent_replication_target_design_rows: list[dict[str, str]],
    policy_path_authored_fail_closed_invariant_design_rows: list[dict[str, str]],
    policy_path_protocol_component_closure_rollup_rows: list[dict[str, str]],
    policy_path_full_protocol_admission_gate_summary_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    component_rollup_by_component = {
        row.get("protocol_component", ""): row
        for row in policy_path_protocol_component_closure_rollup_rows
    }
    full_summary_id = (
        policy_path_full_protocol_admission_gate_summary_rows[0].get(
            "policy_path_full_protocol_admission_gate_summary_row_id", ""
        )
        if policy_path_full_protocol_admission_gate_summary_rows
        else ""
    )
    allowed_use = "policy_path_source_bundle_field_exhaustion_decision_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_source_bundle_field_exhaustion_decision_not_bps_year_or_runtime_input"
    )
    rows: list[dict[str, str]] = []

    for closure in policy_path_terminal_no_hit_closure_rows:
        source_status = closure.get("source_bundle_closure_status", "")
        exhausted = source_status == "terminal_no_hit_exhausted_current_source_bundle"
        required = closure.get("required_evidence_class", "")
        field_name = closure.get("authored_field_name", "")
        field_decision_class = (
            "terminal_no_hit_exhausted_current_source_bundle"
            if exhausted
            else "context_locator_review_only_not_promotable"
        )
        missing = (
            f"missing_{required}"
            if exhausted
            else f"promotion_grade_{required}_evidence_not_present"
        )
        remaining = (
            f"new_promotion_grade_source_artifact_for_{required}"
            if exhausted
            else f"row_specific_promotion_grade_source_evidence_for_{required}"
        )
        rows.append(
            {
                "protocol_component": closure.get("protocol_component", ""),
                "protocol_component_gate": closure.get("protocol_component_gate", ""),
                "authored_field_name": field_name,
                "field_decision_class": field_decision_class,
                "source_bundle_exhaustion_status": source_status,
                "current_source_bundle_exhausted": "true" if exhausted else "false",
                "context_only_locator_count": closure.get(
                    "candidate_context_locator_count", "0"
                ),
                "terminal_no_hit_count": closure.get("terminal_no_hit_count", "0"),
                "promotion_grade_evidence_count": closure.get(
                    "promotion_grade_evidence_count", "0"
                ),
                "field_pass_count": closure.get("field_pass_count", "0"),
                "required_evidence_or_deliverable": required,
                "missing_evidence_or_deliverable": missing,
                "remaining_source_family_or_authored_deliverable": remaining,
                "linked_pass_rule_adjudication_row_ids": closure.get(
                    "linked_pass_rule_adjudication_row_ids", ""
                ),
                "linked_terminal_no_hit_closure_row_id": closure.get(
                    "policy_path_terminal_no_hit_closure_row_id", ""
                ),
                "linked_independent_replication_design_row_id": "",
                "linked_authored_invariant_design_row_id": "",
                "linked_protocol_component_closure_rollup_row_id": (
                    component_rollup_by_component.get(
                        closure.get("protocol_component", ""), {}
                    ).get("policy_path_protocol_component_closure_rollup_row_id", "")
                ),
                "linked_full_protocol_admission_gate_summary_row_id": full_summary_id,
                "field_decision_status": "blocked_field_exhaustion_decision_not_admitted",
                "protocol_admission_status": (
                    "blocked_source_bundle_field_decision_not_complete_bps_year_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{field_name} remains blocked as {field_decision_class}; "
                    f"{missing}."
                ),
                "next_backend_action": (
                    "acquire_promotion_grade_source_evidence_or_preserve_terminal_block"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )

    for design in policy_path_independent_replication_target_design_rows:
        field_name = design.get("authored_field_name", "")
        required = design.get("required_output_field", "")
        rows.append(
            {
                "protocol_component": design.get("protocol_component", ""),
                "protocol_component_gate": design.get("protocol_component_gate", ""),
                "authored_field_name": field_name,
                "field_decision_class": (
                    "independent_replication_design_only_not_implemented"
                ),
                "source_bundle_exhaustion_status": (
                    "replication_target_design_only_current_bundle_not_admitted"
                ),
                "current_source_bundle_exhausted": "false",
                "context_only_locator_count": "0",
                "terminal_no_hit_count": "0",
                "promotion_grade_evidence_count": "0",
                "field_pass_count": "0",
                "required_evidence_or_deliverable": required,
                "missing_evidence_or_deliverable": (
                    f"implemented_independent_replication_target_for_{required}"
                ),
                "remaining_source_family_or_authored_deliverable": (
                    "machine_executable_independent_bps_year_replication_artifact"
                ),
                "linked_pass_rule_adjudication_row_ids": "",
                "linked_terminal_no_hit_closure_row_id": "",
                "linked_independent_replication_design_row_id": design.get(
                    "policy_path_independent_replication_target_design_row_id", ""
                ),
                "linked_authored_invariant_design_row_id": "",
                "linked_protocol_component_closure_rollup_row_id": (
                    component_rollup_by_component.get(
                        design.get("protocol_component", ""), {}
                    ).get("policy_path_protocol_component_closure_rollup_row_id", "")
                ),
                "linked_full_protocol_admission_gate_summary_row_id": full_summary_id,
                "field_decision_status": "blocked_field_exhaustion_decision_not_admitted",
                "protocol_admission_status": (
                    "blocked_source_bundle_field_decision_not_complete_bps_year_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{field_name} remains design-only; no independent bps-year "
                    "replication target has been implemented or passed."
                ),
                "next_backend_action": "implement_independent_bps_year_replication_target",
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )

    for invariant in policy_path_authored_fail_closed_invariant_design_rows:
        field_name = invariant.get("authored_field_name", "")
        required = invariant.get("required_output_field", "")
        rows.append(
            {
                "protocol_component": invariant.get("protocol_component", ""),
                "protocol_component_gate": invariant.get("protocol_component_gate", ""),
                "authored_field_name": field_name,
                "field_decision_class": (
                    "authored_fail_closed_invariant_only_not_admission"
                ),
                "source_bundle_exhaustion_status": (
                    "authored_invariant_design_only_current_bundle_not_admitted"
                ),
                "current_source_bundle_exhausted": "false",
                "context_only_locator_count": "0",
                "terminal_no_hit_count": "0",
                "promotion_grade_evidence_count": "0",
                "field_pass_count": "0",
                "required_evidence_or_deliverable": required,
                "missing_evidence_or_deliverable": (
                    f"implemented_authored_invariant_gate_for_{required}"
                ),
                "remaining_source_family_or_authored_deliverable": (
                    "implemented_fail_closed_invariant_test_and_review_boundary"
                ),
                "linked_pass_rule_adjudication_row_ids": "",
                "linked_terminal_no_hit_closure_row_id": "",
                "linked_independent_replication_design_row_id": "",
                "linked_authored_invariant_design_row_id": invariant.get(
                    "policy_path_authored_fail_closed_invariant_design_row_id", ""
                ),
                "linked_protocol_component_closure_rollup_row_id": (
                    component_rollup_by_component.get(
                        invariant.get("protocol_component", ""), {}
                    ).get("policy_path_protocol_component_closure_rollup_row_id", "")
                ),
                "linked_full_protocol_admission_gate_summary_row_id": full_summary_id,
                "field_decision_status": "blocked_field_exhaustion_decision_not_admitted",
                "protocol_admission_status": (
                    "blocked_source_bundle_field_decision_not_complete_bps_year_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{field_name} remains authored-invariant-only and cannot "
                    "admit policy-path evidence or runtime output."
                ),
                "next_backend_action": (
                    "implement_or_preserve_fail_closed_invariant_gate"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )

    for idx, row in enumerate(rows, start=1):
        row["policy_path_source_bundle_field_exhaustion_decision_row_id"] = (
            f"policy_path_source_bundle_field_exhaustion_decision::{idx:04d}"
        )
    return rows


def policy_path_source_bundle_component_exhaustion_decision_rows(
    *,
    policy_path_source_bundle_field_exhaustion_decision_rows: list[dict[str, str]],
    policy_path_protocol_component_closure_rollup_rows: list[dict[str, str]],
    policy_path_full_protocol_admission_gate_summary_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    fields_by_component: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_source_bundle_field_exhaustion_decision_rows:
        fields_by_component[row.get("protocol_component", "")].append(row)
    full_summary = (
        policy_path_full_protocol_admission_gate_summary_rows[0]
        if policy_path_full_protocol_admission_gate_summary_rows
        else {}
    )
    full_gate_status = full_summary.get("full_gate_conjunction_status", "")
    full_summary_id = full_summary.get(
        "policy_path_full_protocol_admission_gate_summary_row_id", ""
    )
    allowed_use = "policy_path_source_bundle_component_exhaustion_decision_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold"
    )
    claim_boundary = (
        "policy_path_source_bundle_component_exhaustion_decision_not_bps_year_or_runtime_input"
    )
    rows = []
    for idx, component in enumerate(
        policy_path_protocol_component_closure_rollup_rows, start=1
    ):
        component_id = component.get("protocol_component", "")
        field_rows = fields_by_component.get(component_id, [])
        context_count = sum(
            row.get("field_decision_class")
            == "context_locator_review_only_not_promotable"
            for row in field_rows
        )
        terminal_count = sum(
            row.get("field_decision_class")
            == "terminal_no_hit_exhausted_current_source_bundle"
            for row in field_rows
        )
        replication_count = sum(
            row.get("field_decision_class")
            == "independent_replication_design_only_not_implemented"
            for row in field_rows
        )
        invariant_count = sum(
            row.get("field_decision_class")
            == "authored_fail_closed_invariant_only_not_admission"
            for row in field_rows
        )
        promotion_grade_count = sum(
            int(row.get("promotion_grade_evidence_count") or "0")
            for row in field_rows
        )
        field_pass_count = sum(
            int(row.get("field_pass_count") or "0") for row in field_rows
        )
        if context_count or terminal_count:
            decision_class = (
                "source_component_current_bundle_context_or_no_hit_not_promotable"
            )
            source_status = "source_bundle_reviewed_not_promotion_grade"
            remaining = "promotion_grade_source_protocol_fields"
        elif replication_count:
            decision_class = "independent_replication_component_design_only_not_admitted"
            source_status = "independent_replication_design_not_implemented"
            remaining = "machine_executable_independent_replication_target"
        else:
            decision_class = "authored_invariant_component_design_only_not_admitted"
            source_status = "authored_invariant_design_not_runtime_admission"
            remaining = "implemented_fail_closed_invariant_gate"
        reason = (
            f"{component_id} remains blocked with {context_count} context-only "
            f"fields, {terminal_count} terminal no-hit fields, "
            f"{replication_count} replication design fields, {invariant_count} "
            "authored-invariant fields, zero promotion-grade evidence, and "
            "zero field passes."
        )
        rows.append(
            {
                "policy_path_source_bundle_component_exhaustion_decision_row_id": (
                    f"policy_path_source_bundle_component_exhaustion_decision::{idx:04d}"
                ),
                "protocol_component": component_id,
                "protocol_component_gate": component.get("protocol_component_gate", ""),
                "component_decision_class": decision_class,
                "source_bundle_exhaustion_status": source_status,
                "source_field_count": component.get("source_field_count", "0"),
                "context_only_field_count": str(context_count),
                "terminal_no_hit_field_count": str(terminal_count),
                "independent_replication_design_field_count": str(replication_count),
                "authored_invariant_design_field_count": str(invariant_count),
                "promotion_grade_evidence_count": str(promotion_grade_count),
                "field_pass_count": str(field_pass_count),
                "component_closure_status": component.get("component_closure_status", ""),
                "full_protocol_gate_status": full_gate_status,
                "linked_field_exhaustion_decision_row_ids": _join_unique(
                    [
                        row.get(
                            "policy_path_source_bundle_field_exhaustion_decision_row_id",
                            "",
                        )
                        for row in field_rows
                    ]
                ),
                "linked_protocol_component_closure_rollup_row_id": component.get(
                    "policy_path_protocol_component_closure_rollup_row_id", ""
                ),
                "linked_full_protocol_admission_gate_summary_row_id": full_summary_id,
                "terminal_non_admission_reason": reason,
                "remaining_source_family_or_authored_deliverable": remaining,
                "component_decision_status": (
                    "blocked_component_exhaustion_decision_not_admitted"
                ),
                "protocol_admission_status": (
                    "blocked_source_bundle_component_decision_not_complete_bps_year_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": reason,
                "next_backend_action": (
                    "resolve_field_exhaustion_decisions_before_protocol_promotion"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_100bp_year_blocker_action_resolution_rows(
    *,
    policy_path_protocol_component_closure_rollup_rows: list[dict[str, str]],
    policy_path_full_protocol_admission_gate_summary_rows: list[dict[str, str]],
    policy_path_source_bundle_field_exhaustion_decision_rows: list[dict[str, str]],
    policy_path_source_bundle_component_exhaustion_decision_rows: list[dict[str, str]],
    policy_path_exact_source_locator_remediation_rows: list[dict[str, str]],
    policy_path_exact_locator_pass_rule_adjudication_rows: list[dict[str, str]],
    policy_path_terminal_no_hit_closure_rows: list[dict[str, str]],
    policy_path_independent_replication_target_design_rows: list[dict[str, str]],
    policy_path_authored_fail_closed_invariant_design_rows: list[dict[str, str]],
    conventional_drag_denominator_route_triage_synthesis_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "policy_path_100bp_year_blocker_action_resolution_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_100bp_year_blocker_action_resolution_not_bps_year_or_calibration"
    )
    action_order = {
        "bps_year_formula": ("1", "source_protocol_candidate_with_terminal_no_hit"),
        "source_cell_unit_sign": ("2", "source_protocol_candidate_with_terminal_no_hit"),
        "event_date_horizon_grid": ("3", "source_protocol_candidate_with_terminal_no_hit"),
        "loading_back_transform": ("4", "source_protocol_candidate_review_only"),
        "independent_replication_target_tolerance": (
            "5",
            "independent_replication_design_required",
        ),
        "denominator_isolation": ("6", "authored_invariant_required"),
        "promotion_rule": ("7", "authored_invariant_required"),
    }
    next_action_by_class = {
        "source_protocol_candidate_with_terminal_no_hit": (
            "acquire_promotion_grade_policy_path_source_protocol_or_preserve_terminal_no_hit_block"
        ),
        "source_protocol_candidate_review_only": (
            "upgrade_review_only_source_protocol_candidates_to_promotion_grade_evidence_or_preserve_block"
        ),
        "independent_replication_design_required": (
            "implement_independent_bps_year_replication_target_artifact_and_pass_fail_audit"
        ),
        "authored_invariant_required": (
            "implement_authored_fail_closed_invariant_pass_fail_audit"
        ),
    }
    downstream_blocked = [
        row
        for row in conventional_drag_denominator_route_triage_synthesis_rows
        if row.get("denominator_admission_status", "").startswith("blocked")
    ]
    downstream_single_next = _join_unique(
        row.get("route_id", "")
        for row in conventional_drag_denominator_route_triage_synthesis_rows
        if row.get("single_next_backend_action_rank") == "1"
    )
    full_summary = (
        policy_path_full_protocol_admission_gate_summary_rows[0]
        if policy_path_full_protocol_admission_gate_summary_rows
        else {}
    )
    component_decisions = {
        row.get("protocol_component", ""): row
        for row in policy_path_source_bundle_component_exhaustion_decision_rows
    }
    rows: list[dict[str, str]] = []
    for closure in sorted(
        policy_path_protocol_component_closure_rollup_rows,
        key=lambda row: int(action_order.get(row.get("protocol_component", ""), ("99", ""))[0]),
    ):
        component = closure.get("protocol_component", "")
        rank, default_class = action_order.get(
            component,
            ("99", "blocked_unclassified_policy_path_component"),
        )
        field_rows = [
            row
            for row in policy_path_source_bundle_field_exhaustion_decision_rows
            if row.get("protocol_component") == component
        ]
        component_decision = component_decisions.get(component, {})
        exact_locator_rows = [
            row
            for row in policy_path_exact_source_locator_remediation_rows
            if row.get("protocol_component") == component
        ]
        pass_rule_rows = [
            row
            for row in policy_path_exact_locator_pass_rule_adjudication_rows
            if row.get("protocol_component") == component
        ]
        terminal_no_hit_rows = [
            row
            for row in policy_path_terminal_no_hit_closure_rows
            if row.get("protocol_component") == component
        ]
        replication_rows = [
            row
            for row in policy_path_independent_replication_target_design_rows
            if row.get("protocol_component") == component
        ]
        invariant_rows = [
            row
            for row in policy_path_authored_fail_closed_invariant_design_rows
            if row.get("protocol_component") == component
        ]
        source_candidate_count = sum(
            row.get("field_decision_class")
            == "context_locator_review_only_not_promotable"
            for row in field_rows
        )
        terminal_field_count = sum(
            row.get("field_decision_class")
            == "terminal_no_hit_exhausted_current_source_bundle"
            for row in field_rows
        )
        replication_field_count = sum(
            row.get("field_decision_class")
            == "independent_replication_design_only_not_implemented"
            for row in field_rows
        )
        invariant_field_count = sum(
            row.get("field_decision_class")
            == "authored_fail_closed_invariant_only_not_admission"
            for row in field_rows
        )
        exact_candidate_count = sum(
            row.get("promotion_grade_evidence_status")
            == "blocked_exact_locator_candidate_not_promotion_grade"
            for row in exact_locator_rows
        )
        exact_terminal_count = sum(
            row.get("promotion_grade_evidence_status")
            == "blocked_terminal_no_promotion_grade_evidence"
            for row in exact_locator_rows
        )
        if terminal_field_count and source_candidate_count:
            action_class = "source_protocol_candidate_with_terminal_no_hit"
        elif source_candidate_count:
            action_class = "source_protocol_candidate_review_only"
        elif replication_field_count:
            action_class = "independent_replication_design_required"
        elif invariant_field_count:
            action_class = "authored_invariant_required"
        else:
            action_class = default_class
        component_closed = closure.get("component_closure_status", "").startswith(
            "pass_"
        )
        full_gate_ready = full_summary.get(
            "full_gate_conjunction_status", ""
        ).startswith("pass_")
        if component_closed and full_gate_ready:
            exact_blocker = (
                f"{component} has nonpromotional component closure, but the "
                "source-bundle action class remains recorded for provenance: "
                f"source candidates={source_candidate_count}, terminal no-hit "
                f"fields={terminal_field_count}, replication design fields="
                f"{replication_field_count}, authored invariant fields="
                f"{invariant_field_count}, promotion-grade evidence=0. "
                "Downstream conventional-drag routes remain blocked until the "
                "policy-path admission consumer/promotion boundary is replayed."
            )
            conventional_drag_blocker_status = (
                "blocked_policy_path_admission_consumer_promotion_boundary_"
                "blocks_denominator_routes"
            )
            before_route_progress_requirement = (
                "no_conventional_drag_route_can_progress_beyond_diagnostic_review_"
                "until_policy_path_admission_consumer_and_promotion_boundary_pass"
            )
        else:
            exact_blocker = (
                f"{component} remains blocked: source candidates={source_candidate_count}, "
                f"terminal no-hit fields={terminal_field_count}, replication design fields="
                f"{replication_field_count}, authored invariant fields={invariant_field_count}, "
                "promotion-grade evidence=0, field passes=0, and downstream conventional-drag "
                f"routes blocked={len(downstream_blocked)}."
            )
            conventional_drag_blocker_status = (
                "blocked_policy_path_100bp_year_gate_blocks_all_denominator_routes"
            )
            before_route_progress_requirement = (
                "no_conventional_drag_route_can_progress_beyond_diagnostic_review_"
                "until_this_component_and_all_sibling_policy_path_gates_pass"
            )
        rows.append(
            {
                "policy_path_100bp_year_blocker_action_resolution_row_id": (
                    f"policy_path_100bp_year_blocker_action_resolution::{int(rank):04d}"
                ),
                "protocol_component": component,
                "protocol_component_gate": closure.get("protocol_component_gate", ""),
                "action_resolution_rank": rank,
                "action_resolution_class": action_class,
                "protocol_component_role": closure.get("component_role", ""),
                "linked_protocol_component_closure_rollup_row_id": closure.get(
                    "policy_path_protocol_component_closure_rollup_row_id", ""
                ),
                "linked_full_protocol_admission_gate_summary_row_id": full_summary.get(
                    "policy_path_full_protocol_admission_gate_summary_row_id", ""
                ),
                "linked_source_bundle_component_exhaustion_decision_row_id": (
                    component_decision.get(
                        "policy_path_source_bundle_component_exhaustion_decision_row_id",
                        "",
                    )
                ),
                "linked_source_bundle_field_exhaustion_decision_row_ids": _join_unique(
                    row.get("policy_path_source_bundle_field_exhaustion_decision_row_id", "")
                    for row in field_rows
                ),
                "linked_exact_source_locator_remediation_row_ids": _join_unique(
                    row.get("policy_path_exact_source_locator_remediation_row_id", "")
                    for row in exact_locator_rows
                ),
                "linked_exact_locator_pass_rule_adjudication_row_ids": _join_unique(
                    row.get("policy_path_exact_locator_pass_rule_adjudication_row_id", "")
                    for row in pass_rule_rows
                ),
                "linked_terminal_no_hit_closure_row_ids": _join_unique(
                    row.get("policy_path_terminal_no_hit_closure_row_id", "")
                    for row in terminal_no_hit_rows
                ),
                "linked_independent_replication_target_design_row_ids": _join_unique(
                    row.get("policy_path_independent_replication_target_design_row_id", "")
                    for row in replication_rows
                ),
                "linked_authored_fail_closed_invariant_design_row_ids": _join_unique(
                    row.get("policy_path_authored_fail_closed_invariant_design_row_id", "")
                    for row in invariant_rows
                ),
                "field_decision_count": str(len(field_rows)),
                "source_protocol_candidate_field_count": str(source_candidate_count),
                "terminal_no_hit_field_count": str(terminal_field_count),
                "independent_replication_design_field_count": str(replication_field_count),
                "authored_invariant_design_field_count": str(invariant_field_count),
                "exact_locator_candidate_count": str(exact_candidate_count),
                "exact_locator_terminal_no_hit_count": str(exact_terminal_count),
                "pass_rule_adjudication_count": str(len(pass_rule_rows)),
                "terminal_no_hit_closure_count": str(len(terminal_no_hit_rows)),
                "independent_replication_design_row_count": str(len(replication_rows)),
                "authored_invariant_design_row_count": str(len(invariant_rows)),
                "promotion_grade_evidence_count": closure.get(
                    "promotion_grade_source_evidence_count", "0"
                ),
                "field_pass_count": component_decision.get(
                    "field_pass_count", closure.get("source_field_pass_count", "0")
                ),
                "component_closure_status": closure.get("component_closure_status", ""),
                "component_decision_status": component_decision.get(
                    "component_decision_status", ""
                ),
                "full_gate_conjunction_status": full_summary.get(
                    "full_gate_conjunction_status", ""
                ),
                "protocol_admission_status": full_summary.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": full_summary.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "downstream_denominator_route_triage_row_count": str(
                    len(conventional_drag_denominator_route_triage_synthesis_rows)
                ),
                "downstream_blocked_route_count": str(len(downstream_blocked)),
                "downstream_single_next_action_route_id": downstream_single_next,
                "conventional_drag_blocker_status": conventional_drag_blocker_status,
                "required_next_action_class": next_action_by_class.get(
                    action_class, "classify_policy_path_blocker_before_action"
                ),
                "before_route_progress_requirement": before_route_progress_requirement,
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": next_action_by_class.get(
                    action_class, "classify_policy_path_blocker_before_action"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def _policy_path_required_source_families(paths: list[str]) -> str:
    families: list[str] = []
    for path in paths:
        lower_path = path.lower()
        if "sf_fed" in lower_path or "usmpd" in lower_path:
            families.append("sf_fed_usmpd")
        if "acosta" in lower_path:
            families.append("acosta_sofr_gss")
        if "fed_sofr" in lower_path:
            families.append("fed_sofr_continuity")
        if "cme" in lower_path:
            families.append("cme_contract_specs")
    return _join_unique(families) or "policy_path_protocol_sources"


def policy_path_source_protocol_action_packet_rows(
    *,
    policy_path_100bp_year_blocker_action_resolution_rows: list[dict[str, str]],
    policy_path_source_bundle_field_exhaustion_decision_rows: list[dict[str, str]],
    policy_path_field_specific_pass_rule_design_rows: list[dict[str, str]],
    policy_path_field_specific_source_evidence_audit_rows: list[dict[str, str]],
    policy_path_exact_source_locator_remediation_rows: list[dict[str, str]],
    policy_path_exact_locator_pass_rule_adjudication_rows: list[dict[str, str]],
    policy_path_terminal_no_hit_closure_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    action_by_component = {
        row.get("protocol_component", ""): row
        for row in policy_path_100bp_year_blocker_action_resolution_rows
    }
    pass_rule_by_field = {
        row.get("authored_field_name", ""): row
        for row in policy_path_field_specific_pass_rule_design_rows
    }
    source_audit_by_field = {
        row.get("authored_field_name", ""): row
        for row in policy_path_field_specific_source_evidence_audit_rows
    }
    closure_by_id = {
        row.get("policy_path_terminal_no_hit_closure_row_id", ""): row
        for row in policy_path_terminal_no_hit_closure_rows
    }
    closure_by_field = {
        row.get("authored_field_name", ""): row
        for row in policy_path_terminal_no_hit_closure_rows
    }
    exact_rows_by_field: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_exact_source_locator_remediation_rows:
        exact_rows_by_field[row.get("authored_field_name", "")].append(row)
    adjudication_rows_by_field: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_exact_locator_pass_rule_adjudication_rows:
        adjudication_rows_by_field[row.get("authored_field_name", "")].append(row)

    allowed_use = "policy_path_source_protocol_action_packet_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_source_protocol_action_packet_not_bps_year_or_calibration"
    )
    eligible_classes = {
        "context_locator_review_only_not_promotable",
        "terminal_no_hit_exhausted_current_source_bundle",
    }
    rows: list[dict[str, str]] = []
    for source_row in policy_path_source_bundle_field_exhaustion_decision_rows:
        field_decision_class = source_row.get("field_decision_class", "")
        if field_decision_class not in eligible_classes:
            continue
        field_name = source_row.get("authored_field_name", "")
        protocol_component = source_row.get("protocol_component", "")
        action_row = action_by_component.get(protocol_component, {})
        pass_rule = pass_rule_by_field.get(field_name, {})
        source_audit = source_audit_by_field.get(field_name, {})
        exact_rows = exact_rows_by_field.get(field_name, [])
        adjudication_rows = adjudication_rows_by_field.get(field_name, [])
        closure = closure_by_id.get(
            source_row.get("linked_terminal_no_hit_closure_row_id", ""),
            closure_by_field.get(field_name, {}),
        )
        source_paths = _join_unique(
            [
                *source_audit.get("source_artifact_paths", "").split(";"),
                *[row.get("source_artifact_path", "") for row in exact_rows],
            ]
        )
        source_hashes = _join_unique(
            [
                *source_audit.get("source_artifact_sha256s", "").split(";"),
                *[row.get("source_artifact_sha256", "") for row in exact_rows],
            ]
        )
        terminal = (
            field_decision_class == "terminal_no_hit_exhausted_current_source_bundle"
        )
        action_class = (
            "preserve_terminal_no_hit_blocker"
            if terminal
            else "seek_promotion_grade_source_evidence"
        )
        action_blocker = (
            "current source bundle is exhausted for this field; preserve the "
            "terminal no-hit until a new promotion-grade source family is acquired"
            if terminal
            else "current source bundle has only review-only context locators; "
            "promotion requires row-level source evidence satisfying the field pass rule"
        )
        next_backend_action = (
            "preserve_terminal_no_hit_and_require_new_source_family_before_reopening"
            if terminal
            else "extract_promotion_grade_row_line_cell_value_and_adjudicate_pass_rule"
        )
        rows.append(
            {
                "policy_path_source_protocol_action_packet_row_id": (
                    f"policy_path_source_protocol_action_packet::{len(rows) + 1:04d}"
                ),
                "policy_path_source_bundle_field_exhaustion_decision_row_id": (
                    source_row.get(
                        "policy_path_source_bundle_field_exhaustion_decision_row_id",
                        "",
                    )
                ),
                "policy_path_100bp_year_blocker_action_resolution_row_id": (
                    action_row.get(
                        "policy_path_100bp_year_blocker_action_resolution_row_id", ""
                    )
                ),
                "protocol_component": protocol_component,
                "protocol_component_gate": source_row.get("protocol_component_gate", ""),
                "authored_field_name": field_name,
                "source_protocol_action_class": action_class,
                "source_protocol_action_status": (
                    "blocked_source_protocol_action_packet_not_admission"
                ),
                "current_source_bundle_exhausted": source_row.get(
                    "current_source_bundle_exhausted", "false"
                ),
                "promotion_grade_evidence_still_worth_seeking": (
                    "false" if terminal else "true"
                ),
                "terminal_no_hit_preserved": "true" if terminal else "false",
                "required_evidence_or_deliverable": source_row.get(
                    "required_evidence_or_deliverable", ""
                ),
                "missing_evidence_or_deliverable": source_row.get(
                    "missing_evidence_or_deliverable", ""
                ),
                "remaining_source_family_or_authored_deliverable": source_row.get(
                    "remaining_source_family_or_authored_deliverable", ""
                ),
                "required_source_families": _policy_path_required_source_families(
                    source_paths.split(";")
                ),
                "source_artifact_paths": source_paths,
                "source_artifact_sha256s": source_hashes,
                "source_locator_requirement": pass_rule.get(
                    "source_locator_requirement",
                    source_audit.get("source_locator_requirement", ""),
                ),
                "row_line_cell_reference_requirement": pass_rule.get(
                    "row_line_cell_reference_requirement",
                    source_audit.get("row_line_cell_reference_requirement", ""),
                ),
                "extracted_value_requirement": pass_rule.get(
                    "extracted_value_requirement",
                    source_audit.get("extracted_value_requirement", ""),
                ),
                "source_quote_cell_evidence_requirement": pass_rule.get(
                    "source_quote_cell_evidence_requirement",
                    source_audit.get("source_quote_cell_evidence_requirement", ""),
                ),
                "promotion_grade_evidence_requirement": pass_rule.get(
                    "promotion_grade_evidence_requirement",
                    source_audit.get("promotion_grade_evidence_requirement", ""),
                ),
                "parser_strategy": _join_unique(
                    [
                        _parser_strategy(protocol_component),
                        *[row.get("artifact_parser_class", "") for row in exact_rows],
                    ]
                ),
                "candidate_locator_kinds": _join_unique(
                    [row.get("artifact_locator_kind", "") for row in exact_rows]
                ),
                "candidate_exact_locators": _join_unique(
                    [row.get("exact_source_locator", "") for row in exact_rows]
                ),
                "candidate_matched_pattern_terms": _join_unique(
                    [row.get("matched_pattern_terms", "") for row in exact_rows]
                ),
                "terminal_no_hit_blockers": _join_unique(
                    [
                        closure.get("exact_blocker", ""),
                        *[
                            row.get("terminal_no_hit_blocker", "")
                            for row in exact_rows
                        ],
                        *[
                            row.get("terminal_no_hit_blocker", "")
                            for row in adjudication_rows
                        ],
                    ]
                ),
                "linked_exact_source_locator_remediation_row_ids": _join_unique(
                    row.get("policy_path_exact_source_locator_remediation_row_id", "")
                    for row in exact_rows
                ),
                "linked_exact_locator_pass_rule_adjudication_row_ids": _join_unique(
                    row.get("policy_path_exact_locator_pass_rule_adjudication_row_id", "")
                    for row in adjudication_rows
                ),
                "linked_terminal_no_hit_closure_row_id": source_row.get(
                    "linked_terminal_no_hit_closure_row_id", ""
                ),
                "field_acceptance_test": pass_rule.get(
                    "field_acceptance_test",
                    source_audit.get("field_acceptance_test", ""),
                ),
                "pass_status_value": pass_rule.get(
                    "pass_status_value", source_audit.get("pass_status_value", "")
                ),
                "blocked_status_value": pass_rule.get(
                    "blocked_status_value",
                    source_audit.get("blocked_status_value", ""),
                ),
                "machine_testable_pass_condition": pass_rule.get(
                    "machine_testable_pass_condition", ""
                ),
                "machine_testable_fail_condition": pass_rule.get(
                    "machine_testable_fail_condition", ""
                ),
                "promotion_grade_evidence_status": source_audit.get(
                    "promotion_grade_evidence_status",
                    "blocked_no_promotion_grade_source_evidence",
                ),
                "field_pass_status": source_audit.get(
                    "pass_rule_result_status",
                    closure.get("field_pass_rule_status", ""),
                ),
                "protocol_admission_status": source_row.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": source_row.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{field_name} remains fail-closed in the source-protocol "
                    f"action packet: {action_blocker}."
                ),
                "next_backend_action": next_backend_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_source_protocol_pass_rule_harness_rows(
    *,
    policy_path_source_protocol_action_packet_rows: list[dict[str, str]],
    policy_path_exact_source_locator_remediation_rows: list[dict[str, str]],
    policy_path_exact_locator_pass_rule_adjudication_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    exact_rows_by_field: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_exact_source_locator_remediation_rows:
        exact_rows_by_field[row.get("authored_field_name", "")].append(row)
    adjudication_rows_by_field: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_exact_locator_pass_rule_adjudication_rows:
        adjudication_rows_by_field[row.get("authored_field_name", "")].append(row)

    allowed_use = "policy_path_source_protocol_pass_rule_harness_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_source_protocol_pass_rule_harness_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for action in policy_path_source_protocol_action_packet_rows:
        field_name = action.get("authored_field_name", "")
        exact_rows = exact_rows_by_field.get(field_name, [])
        adjudication_rows = adjudication_rows_by_field.get(field_name, [])
        terminal = action.get("terminal_no_hit_preserved") == "true"
        candidate_review_count = sum(
            row.get("promotion_grade_evidence_status")
            == "blocked_exact_locator_candidate_not_promotion_grade"
            for row in exact_rows
        )
        terminal_count = sum(
            row.get("promotion_grade_evidence_status")
            == "blocked_terminal_no_promotion_grade_evidence"
            for row in exact_rows
        )
        promotion_grade_count = sum(
            row.get("promotion_grade_evidence_status", "").startswith("pass")
            for row in exact_rows
        )
        field_pass_count = sum(
            row.get("pass_rule_result_status", "").startswith("pass")
            for row in exact_rows
        )
        harness_task_class = (
            "terminal_no_hit_preservation_harness"
            if terminal
            else "promotion_grade_source_evidence_pass_rule_harness"
        )
        extraction_command = (
            ""
            if terminal
            else (
                "python -m ratewall.cli policy-path extract-source-field "
                f"--field {field_name} --require-row-line-cell "
                "--require-source-quote --fail-closed"
            )
        )
        acquisition_command = (
            (
                "manual_source_acquisition_required:"
                f"{action.get('remaining_source_family_or_authored_deliverable', '')}"
            )
            if terminal
            else (
                "manual_review_required_if_no_candidate_locator_passes:"
                f"{action.get('required_source_families', '')}"
            )
        )
        observed_locator = (
            "blocked_terminal_no_hit_no_current_bundle_locator"
            if terminal
            else "blocked_review_only_locator_candidates_present_not_promotion_grade"
        )
        observed_value = (
            "blocked_terminal_no_hit_extracted_value_absent"
            if terminal
            else "blocked_review_only_or_blank_extracted_value_not_field_pass"
        )
        observed_quote = (
            "blocked_terminal_no_hit_quote_or_cell_absent"
            if terminal
            else "blocked_review_only_quote_or_cell_not_promotion_grade"
        )
        observed_promotion = (
            "blocked_terminal_no_promotion_grade_evidence"
            if terminal
            else "blocked_no_promotion_grade_source_evidence"
        )
        rows.append(
            {
                "policy_path_source_protocol_pass_rule_harness_row_id": (
                    f"policy_path_source_protocol_pass_rule_harness::{len(rows) + 1:04d}"
                ),
                "policy_path_source_protocol_action_packet_row_id": action.get(
                    "policy_path_source_protocol_action_packet_row_id", ""
                ),
                "policy_path_source_bundle_field_exhaustion_decision_row_id": (
                    action.get(
                        "policy_path_source_bundle_field_exhaustion_decision_row_id",
                        "",
                    )
                ),
                "protocol_component": action.get("protocol_component", ""),
                "protocol_component_gate": action.get("protocol_component_gate", ""),
                "authored_field_name": field_name,
                "harness_task_class": harness_task_class,
                "harness_status": "blocked_pass_rule_harness_not_admission",
                "current_source_bundle_exhausted": action.get(
                    "current_source_bundle_exhausted", ""
                ),
                "promotion_grade_evidence_still_worth_seeking": action.get(
                    "promotion_grade_evidence_still_worth_seeking", ""
                ),
                "terminal_no_hit_preserved": action.get(
                    "terminal_no_hit_preserved", ""
                ),
                "required_source_families": action.get("required_source_families", ""),
                "source_artifact_paths": action.get("source_artifact_paths", ""),
                "source_artifact_sha256s": action.get("source_artifact_sha256s", ""),
                "candidate_locator_count": str(len(exact_rows)),
                "candidate_review_only_locator_count": str(candidate_review_count),
                "terminal_no_hit_locator_count": str(terminal_count),
                "promotion_grade_locator_count": str(promotion_grade_count),
                "field_pass_locator_count": str(field_pass_count),
                "candidate_locator_kinds": action.get("candidate_locator_kinds", ""),
                "candidate_exact_locators": action.get("candidate_exact_locators", ""),
                "candidate_matched_pattern_terms": action.get(
                    "candidate_matched_pattern_terms", ""
                ),
                "required_locator_evidence": action.get(
                    "source_locator_requirement", ""
                ),
                "required_row_line_cell_evidence": action.get(
                    "row_line_cell_reference_requirement", ""
                ),
                "required_extracted_value_evidence": action.get(
                    "extracted_value_requirement", ""
                ),
                "required_quote_or_cell_evidence": action.get(
                    "source_quote_cell_evidence_requirement", ""
                ),
                "required_promotion_grade_evidence": action.get(
                    "promotion_grade_evidence_requirement", ""
                ),
                "observed_locator_coverage_status": observed_locator,
                "observed_value_coverage_status": observed_value,
                "observed_quote_coverage_status": observed_quote,
                "observed_promotion_grade_status": observed_promotion,
                "terminal_no_hit_blockers": action.get("terminal_no_hit_blockers", ""),
                "exact_pass_predicate_text": action.get(
                    "machine_testable_pass_condition", ""
                ),
                "exact_fail_predicate_text": action.get(
                    "machine_testable_fail_condition", ""
                ),
                "field_acceptance_test": action.get("field_acceptance_test", ""),
                "pass_status_value": action.get("pass_status_value", ""),
                "blocked_status_value": action.get("blocked_status_value", ""),
                "executable_extraction_command_shape": extraction_command,
                "manual_source_acquisition_command_shape": acquisition_command,
                "linked_exact_source_locator_remediation_row_ids": _join_unique(
                    row.get("policy_path_exact_source_locator_remediation_row_id", "")
                    for row in exact_rows
                ),
                "linked_exact_locator_pass_rule_adjudication_row_ids": _join_unique(
                    row.get("policy_path_exact_locator_pass_rule_adjudication_row_id", "")
                    for row in adjudication_rows
                ),
                "linked_terminal_no_hit_closure_row_id": action.get(
                    "linked_terminal_no_hit_closure_row_id", ""
                ),
                "protocol_admission_status": action.get("protocol_admission_status", ""),
                "policy_path_100bp_year_normalization_status": action.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{field_name} remains blocked in the source-protocol "
                    "pass-rule harness: current evidence does not satisfy "
                    "the exact pass predicate and cannot admit bps-year output."
                ),
                "next_backend_action": (
                    "preserve_terminal_no_hit_until_new_source_family_is_acquired"
                    if terminal
                    else "run_fail_closed_field_extraction_or_acquire_promotion_grade_source"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def _first_semicolon_value(value: str) -> str:
    for part in value.split(";"):
        if part:
            return part
    return ""


def policy_path_source_protocol_extraction_attempt_results_rows(
    *,
    policy_path_source_protocol_pass_rule_harness_rows: list[dict[str, str]],
    policy_path_exact_source_locator_remediation_rows: list[dict[str, str]],
    policy_path_exact_locator_pass_rule_adjudication_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    exact_rows_by_field: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_exact_source_locator_remediation_rows:
        exact_rows_by_field[row.get("authored_field_name", "")].append(row)
    adjudication_rows_by_exact_id = {
        row.get("policy_path_exact_source_locator_remediation_row_id", ""): row
        for row in policy_path_exact_locator_pass_rule_adjudication_rows
    }
    adjudication_rows_by_field: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in policy_path_exact_locator_pass_rule_adjudication_rows:
        adjudication_rows_by_field[row.get("authored_field_name", "")].append(row)

    allowed_use = "policy_path_source_protocol_extraction_attempt_results_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_source_protocol_extraction_attempt_results_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for harness in policy_path_source_protocol_pass_rule_harness_rows:
        field_name = harness.get("authored_field_name", "")
        exact_rows = exact_rows_by_field.get(field_name, [])
        primary_exact = exact_rows[0] if exact_rows else {}
        primary_adjudication = adjudication_rows_by_exact_id.get(
            primary_exact.get("policy_path_exact_source_locator_remediation_row_id", ""),
            (adjudication_rows_by_field.get(field_name, [{}]) or [{}])[0],
        )
        terminal = harness.get("terminal_no_hit_preserved") == "true"
        command_shape = (
            harness.get("manual_source_acquisition_command_shape", "")
            if terminal
            else harness.get("executable_extraction_command_shape", "")
        )
        attempt_class = (
            "terminal_no_hit_non_execution_blocker"
            if terminal
            else "review_only_candidate_extraction_attempt"
        )
        attempt_status = (
            "blocked_terminal_no_hit_not_executed"
            if terminal
            else "blocked_review_only_extraction_attempt_not_promotion_grade"
        )
        attempt_mode = (
            "not_executed_terminal_no_hit_preserved"
            if terminal
            else "simulated_deterministic_extraction_review_only"
        )
        source_artifact_path = primary_exact.get(
            "source_artifact_path",
            _first_semicolon_value(harness.get("source_artifact_paths", "")),
        )
        source_artifact_sha256 = primary_exact.get(
            "source_artifact_sha256",
            _first_semicolon_value(harness.get("source_artifact_sha256s", "")),
        )
        terminal_blocker = _join_unique(
            [
                primary_exact.get("terminal_no_hit_blocker", ""),
                primary_adjudication.get("terminal_no_hit_blocker", ""),
                harness.get("terminal_no_hit_blockers", ""),
            ]
        )
        quote_or_cell = (
            primary_exact.get("matched_text_excerpt", "")
            or primary_adjudication.get("matched_text_excerpt", "")
            or terminal_blocker
        )
        pass_fail_outcome = (
            "blocked_terminal_no_hit_preserved_non_execution"
            if terminal
            else primary_adjudication.get(
                "pass_rule_adjudication_status",
                "blocked_extraction_attempt_review_only_not_adjudicated",
            )
        )
        rows.append(
            {
                "policy_path_source_protocol_extraction_attempt_result_row_id": (
                    "policy_path_source_protocol_extraction_attempt_result::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_source_protocol_pass_rule_harness_row_id": harness.get(
                    "policy_path_source_protocol_pass_rule_harness_row_id", ""
                ),
                "policy_path_source_protocol_action_packet_row_id": harness.get(
                    "policy_path_source_protocol_action_packet_row_id", ""
                ),
                "protocol_component": harness.get("protocol_component", ""),
                "protocol_component_gate": harness.get("protocol_component_gate", ""),
                "authored_field_name": field_name,
                "attempt_task_class": attempt_class,
                "attempt_execution_status": attempt_status,
                "attempt_execution_mode": attempt_mode,
                "command_shape": command_shape,
                "source_artifact_path": source_artifact_path,
                "source_artifact_sha256": source_artifact_sha256,
                "source_locator": primary_exact.get("exact_source_locator", ""),
                "source_locator_kind": primary_exact.get("artifact_locator_kind", ""),
                "parser_strategy": primary_exact.get(
                    "artifact_parser_class",
                    _parser_strategy(harness.get("protocol_component", "")),
                ),
                "parsed_value_candidate_review_only": (
                    primary_exact.get("extracted_field_value_review_only", "")
                ),
                "quote_or_cell_evidence_candidate_review_only": quote_or_cell,
                "pass_fail_predicate_outcome": pass_fail_outcome,
                "pass_status_value": harness.get("pass_status_value", ""),
                "blocked_status_value": harness.get("blocked_status_value", ""),
                "exact_pass_predicate_text": harness.get("exact_pass_predicate_text", ""),
                "exact_fail_predicate_text": harness.get("exact_fail_predicate_text", ""),
                "candidate_context_status": primary_adjudication.get(
                    "candidate_context_status",
                    "not_applicable_terminal_no_hit" if terminal else "",
                ),
                "terminal_no_hit_status": primary_adjudication.get(
                    "terminal_no_hit_status",
                    "blocked_terminal_no_hit_preserved" if terminal else "",
                ),
                "promotion_grade_evidence_status": (
                    primary_exact.get("promotion_grade_evidence_status", "")
                    or harness.get("observed_promotion_grade_status", "")
                ),
                "field_pass_status": primary_adjudication.get(
                    "field_pass_rule_status",
                    "blocked_terminal_no_hit_not_field_pass"
                    if terminal
                    else "blocked_extraction_attempt_not_field_pass",
                ),
                "terminal_no_hit_preserved": harness.get(
                    "terminal_no_hit_preserved", ""
                ),
                "terminal_no_hit_blocker": terminal_blocker,
                "linked_exact_source_locator_remediation_row_id": primary_exact.get(
                    "policy_path_exact_source_locator_remediation_row_id", ""
                ),
                "linked_exact_locator_pass_rule_adjudication_row_id": (
                    primary_adjudication.get(
                        "policy_path_exact_locator_pass_rule_adjudication_row_id", ""
                    )
                ),
                "protocol_admission_status": harness.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": harness.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": (
                    f"{field_name} extraction attempt remains fail-closed: "
                    f"{pass_fail_outcome}; parsed candidates are review-only "
                    "and cannot populate policy-path or denominator outputs."
                ),
                "next_backend_action": (
                    "acquire_new_promotion_grade_source_family_before_reattempt"
                    if terminal
                    else "review_candidate_value_against_pass_rule_without_promotion"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_source_protocol_attempt_closure_handoff_rows(
    *,
    policy_path_source_protocol_extraction_attempt_results_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    allowed_use = "policy_path_source_protocol_attempt_closure_handoff_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_source_protocol_attempt_closure_handoff_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for attempt in policy_path_source_protocol_extraction_attempt_results_rows:
        terminal = attempt.get("attempt_task_class") == (
            "terminal_no_hit_non_execution_blocker"
        )
        handoff_class = (
            "new_promotion_grade_source_family_required"
            if terminal
            else "promotion_grade_manual_source_review_or_new_source_family_required"
        )
        field_closure_status = (
            "blocked_terminal_no_hit_current_source_bundle_exhausted"
            if terminal
            else "blocked_review_only_attempt_not_promotion_grade"
        )
        source_bundle_status = (
            "blocked_current_source_bundle_terminal_no_hit"
            if terminal
            else "blocked_current_source_bundle_context_only_candidate_found"
        )
        source_acquisition_handoff = (
            "acquire_new_promotion_grade_source_family_with_explicit_field_locator"
            if terminal
            else "manual_promotion_grade_review_or_alternate_source_family_needed"
        )
        required_source = (
            "new_source_family_with_explicit_"
            f"{attempt.get('authored_field_name', '')}_evidence"
            if terminal
            else attempt.get("source_artifact_path", "")
        )
        exact_blocker = (
            f"{attempt.get('authored_field_name', '')} remains blocked after "
            "source-protocol extraction-attempt closure: "
            f"{field_closure_status}; parsed candidates are nonpromotional, "
            "source evidence is not promotion-grade, and sibling authored "
            "invariant plus independent-replication gates remain unresolved."
        )
        next_backend_action = (
            "source_acquire_promotion_grade_field_evidence_then_rerun_pass_rule"
            if terminal
            else "perform_manual_promotion_grade_source_review_or_source_acquire_alternate_artifact"
        )
        rows.append(
            {
                "policy_path_source_protocol_attempt_closure_handoff_row_id": (
                    "policy_path_source_protocol_attempt_closure_handoff::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_source_protocol_extraction_attempt_result_row_id": (
                    attempt.get(
                        "policy_path_source_protocol_extraction_attempt_result_row_id",
                        "",
                    )
                ),
                "policy_path_source_protocol_pass_rule_harness_row_id": attempt.get(
                    "policy_path_source_protocol_pass_rule_harness_row_id", ""
                ),
                "policy_path_source_protocol_action_packet_row_id": attempt.get(
                    "policy_path_source_protocol_action_packet_row_id", ""
                ),
                "protocol_component": attempt.get("protocol_component", ""),
                "protocol_component_gate": attempt.get("protocol_component_gate", ""),
                "authored_field_name": attempt.get("authored_field_name", ""),
                "closure_handoff_class": handoff_class,
                "field_closure_status": field_closure_status,
                "source_bundle_status": source_bundle_status,
                "attempt_task_class": attempt.get("attempt_task_class", ""),
                "attempt_execution_status": attempt.get("attempt_execution_status", ""),
                "attempt_execution_mode": attempt.get("attempt_execution_mode", ""),
                "source_artifact_path": attempt.get("source_artifact_path", ""),
                "source_artifact_sha256": attempt.get("source_artifact_sha256", ""),
                "source_locator": attempt.get("source_locator", ""),
                "source_locator_kind": attempt.get("source_locator_kind", ""),
                "parser_strategy": attempt.get("parser_strategy", ""),
                "parsed_value_candidate_review_only": attempt.get(
                    "parsed_value_candidate_review_only", ""
                ),
                "quote_or_cell_evidence_candidate_review_only": attempt.get(
                    "quote_or_cell_evidence_candidate_review_only", ""
                ),
                "pass_fail_predicate_outcome": attempt.get(
                    "pass_fail_predicate_outcome", ""
                ),
                "field_pass_status": attempt.get("field_pass_status", ""),
                "promotion_grade_evidence_status": attempt.get(
                    "promotion_grade_evidence_status", ""
                ),
                "promotion_grade_source_family_required": "true",
                "source_acquisition_handoff": source_acquisition_handoff,
                "required_source_family_or_artifact": required_source,
                "authored_invariant_work_required_before_gate_move": "true",
                "authored_invariant_dependency_status": (
                    "blocked_authored_fail_closed_invariant_and_promotion_rule_sibling_gate_required"
                ),
                "independent_replication_design_required_before_gate_move": "true",
                "independent_replication_dependency_status": (
                    "blocked_independent_bps_year_replication_target_sibling_gate_required"
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_gate_move_status": (
                    "blocked_attempt_closure_handoff_not_protocol_admission"
                ),
                "linked_exact_source_locator_remediation_row_id": attempt.get(
                    "linked_exact_source_locator_remediation_row_id", ""
                ),
                "linked_exact_locator_pass_rule_adjudication_row_id": attempt.get(
                    "linked_exact_locator_pass_rule_adjudication_row_id", ""
                ),
                "terminal_no_hit_preserved": attempt.get(
                    "terminal_no_hit_preserved", ""
                ),
                "terminal_no_hit_blocker": attempt.get("terminal_no_hit_blocker", ""),
                "protocol_admission_status": attempt.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": attempt.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": next_backend_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def _promotion_grade_source_family_spec(row: dict[str, str]) -> dict[str, str]:
    field = row.get("authored_field_name", "")
    gate = row.get("protocol_component_gate", "")
    if gate == "source_cell_unit_sign":
        source_family = "source_authored_cell_unit_sign_contract"
        artifact_hint = (
            "official/source-author workbook documentation, codebook, contract "
            "specification, or replication code naming the source cell units "
            "and rate/price sign transform"
        )
        evidence_type = (
            "explicit source-cell unit, instrument-family, literal-NA, basis-"
            "point conversion, and price-to-rate sign evidence"
        )
        locator_grain = "sheet_cell_or_source_document_line"
        parser_shape = (
            "xlsx_sheet_cell_parser;pdf_text_line_parser;source_code_literal_search"
        )
    elif gate == "event_date_horizon_grid":
        source_family = "source_authored_event_date_horizon_grid_contract"
        artifact_hint = (
            "official/source-author event file, data dictionary, replication "
            "script, or appendix defining event dates, event windows, contract "
            "reference intervals, and horizon year fractions"
        )
        evidence_type = (
            "explicit event-date, event-window, horizon start/end, literal-NA "
            "exclusion, no-static-quarter-fallback, and year-fraction evidence"
        )
        locator_grain = "event_row_or_source_document_line"
        parser_shape = (
            "event_table_row_parser;date_interval_parser;pdf_text_line_parser;"
            "source_code_literal_search"
        )
    elif gate == "loading_back_transform":
        source_family = "source_authored_loading_back_transform_contract"
        artifact_hint = (
            "official/source-author replication code, MAT/DTA/XLSX payload, "
            "README, or appendix defining factor construction, loadings, "
            "rotation signs, and scalar-to-cell back-transform rules"
        )
        evidence_type = (
            "explicit factor-definition, instrument-loading, rotation-sign, "
            "scalar back-transform, and replication-command evidence"
        )
        locator_grain = "code_line_or_struct_field_or_document_line"
        parser_shape = (
            "source_code_ast_or_regex_parser;mat_struct_field_parser;"
            "xlsx_sheet_cell_parser;pdf_text_line_parser"
        )
    elif gate == "bps_year_formula":
        source_family = "source_authored_bps_year_integral_formula_contract"
        artifact_hint = (
            "official/source-author methodological appendix, replication code, "
            "or data dictionary defining horizon weights, rate-change unit "
            "conversion, sign convention, component formula, and aggregation "
            "formula"
        )
        evidence_type = (
            "explicit bps-year component formula, horizon-weight, rate-change "
            "unit-conversion, sign-convention, and aggregation-formula evidence"
        )
        locator_grain = "formula_line_or_code_line_or_sheet_cell"
        parser_shape = (
            "formula_text_parser;source_code_literal_search;structured_sheet_cell_parser"
        )
    else:
        source_family = "source_authored_policy_path_protocol_contract"
        artifact_hint = (
            "official/source-author documentation or replication artifact with "
            f"promotion-grade evidence for {field}"
        )
        evidence_type = f"explicit promotion-grade evidence for {field}"
        locator_grain = "source_line_or_structured_cell"
        parser_shape = "text_or_structured_artifact_parser"
    return {
        "target_source_family": source_family,
        "target_source_artifact_hint": artifact_hint,
        "expected_evidence_type": evidence_type,
        "required_locator_grain": locator_grain,
        "deterministic_parser_shape": parser_shape,
    }


def policy_path_promotion_grade_source_family_acquisition_packet_rows(
    *,
    policy_path_source_protocol_attempt_closure_handoff_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "policy_path_promotion_grade_source_family_acquisition_packet_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_promotion_grade_source_family_acquisition_packet_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for handoff in policy_path_source_protocol_attempt_closure_handoff_rows:
        terminal = handoff.get("closure_handoff_class") == (
            "new_promotion_grade_source_family_required"
        )
        task_class = (
            "new_source_family_terminal_no_hit_acquisition_task"
            if terminal
            else "manual_review_or_alternate_source_family_acquisition_task"
        )
        spec = _promotion_grade_source_family_spec(handoff)
        field = handoff.get("authored_field_name", "")
        search_strategy = (
            "search_source_author_sites_replication_archives_and_existing_payloads_for_"
            f"{field}_promotion_grade_locator"
        )
        download_strategy = (
            "download_official_or_source_author_pdf_xlsx_dta_mat_m_code_readme_to_"
            "data_raw_policy_path_protocol_sources_and_record_sha256"
        )
        acceptance_test = (
            "pass_only_if_source_locator_is_exact_and_evidence_explicitly_satisfies_"
            f"{field}_pass_rule_without_using_prompt_numbers_scalar_shocks_or_review_only_context"
        )
        exact_blocker = (
            f"{field} requires promotion-grade source-family acquisition before "
            "any policy-path 100bp-year protocol gate can move: "
            f"{handoff.get('field_closure_status', '')}; authored invariant "
            "and independent-replication sibling gates also remain blocked."
        )
        rows.append(
            {
                "policy_path_promotion_grade_source_family_acquisition_packet_row_id": (
                    "policy_path_promotion_grade_source_family_acquisition_packet::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_source_protocol_attempt_closure_handoff_row_id": (
                    handoff.get(
                        "policy_path_source_protocol_attempt_closure_handoff_row_id",
                        "",
                    )
                ),
                "policy_path_source_protocol_extraction_attempt_result_row_id": (
                    handoff.get(
                        "policy_path_source_protocol_extraction_attempt_result_row_id",
                        "",
                    )
                ),
                "protocol_component": handoff.get("protocol_component", ""),
                "protocol_component_gate": handoff.get("protocol_component_gate", ""),
                "authored_field_name": field,
                "acquisition_task_class": task_class,
                "closure_handoff_class": handoff.get("closure_handoff_class", ""),
                "field_closure_status": handoff.get("field_closure_status", ""),
                "source_bundle_status": handoff.get("source_bundle_status", ""),
                **spec,
                "search_strategy": search_strategy,
                "download_strategy": download_strategy,
                "evidence_acceptance_test": acceptance_test,
                "current_source_artifact_path": handoff.get("source_artifact_path", ""),
                "current_source_artifact_sha256": handoff.get(
                    "source_artifact_sha256", ""
                ),
                "current_source_locator": handoff.get("source_locator", ""),
                "current_parser_strategy": handoff.get("parser_strategy", ""),
                "current_parsed_value_candidate_review_only": handoff.get(
                    "parsed_value_candidate_review_only", ""
                ),
                "current_quote_or_cell_evidence_candidate_review_only": handoff.get(
                    "quote_or_cell_evidence_candidate_review_only", ""
                ),
                "current_pass_fail_predicate_outcome": handoff.get(
                    "pass_fail_predicate_outcome", ""
                ),
                "terminal_no_hit_preserved": handoff.get(
                    "terminal_no_hit_preserved", ""
                ),
                "terminal_no_hit_blocker": handoff.get("terminal_no_hit_blocker", ""),
                "authored_invariant_sibling_gate_status": handoff.get(
                    "authored_invariant_dependency_status", ""
                ),
                "independent_replication_sibling_gate_status": handoff.get(
                    "independent_replication_dependency_status", ""
                ),
                "acquisition_packet_status": (
                    "blocked_source_family_acquisition_required_not_evidence"
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_admission_status": handoff.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": handoff.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": (
                    "execute_source_family_acquisition_and_rerun_exact_pass_rule_harness_fail_closed"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def _artifact_availability_status(path: str, sha256: str) -> str:
    if not path:
        return "blocked_no_current_source_artifact_path"
    if not Path(path).exists():
        return "blocked_current_source_artifact_missing_from_workspace"
    if not sha256:
        return "blocked_current_source_artifact_present_missing_expected_sha256"
    return "pass_current_source_artifact_present_hash_recorded_review_only"


def policy_path_promotion_grade_source_family_acquisition_execution_preflight_results_rows(
    *,
    policy_path_promotion_grade_source_family_acquisition_packet_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    allowed_use = (
        "policy_path_promotion_grade_source_family_acquisition_execution_preflight_results_only"
    )
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_promotion_grade_source_family_acquisition_execution_preflight_results_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for packet in policy_path_promotion_grade_source_family_acquisition_packet_rows:
        terminal = packet.get("acquisition_task_class") == (
            "new_source_family_terminal_no_hit_acquisition_task"
        )
        current_path = packet.get("current_source_artifact_path", "")
        current_sha = packet.get("current_source_artifact_sha256", "")
        current_status = _artifact_availability_status(current_path, current_sha)
        current_available = current_status.startswith("pass_")
        execution_class = (
            "manual_authenticated_or_new_source_family_acquisition_required"
            if terminal
            else "current_artifact_available_manual_review_or_source_author_search_required"
        )
        parser_ready = (
            "blocked_parser_waiting_for_new_promotion_grade_source_family"
            if terminal
            else (
                "blocked_parser_command_shape_available_current_artifact_review_only_not_promotion_grade"
                if current_available
                else "blocked_parser_waiting_for_current_or_alternate_source_artifact"
            )
        )
        parser_command = (
            "python -m ratewall.cli policy-path parse-promotion-grade-source "
            f"--artifact {current_path or '<new_source_artifact>'} "
            f"--field {packet.get('authored_field_name', '')} "
            f"--parser-shape {packet.get('deterministic_parser_shape', '')}"
        )
        attempted_search = (
            "web_or_source_author_search_required:"
            f"{packet.get('search_strategy', '')}"
        )
        attempted_download = (
            "source_download_preflight_required:"
            f"{packet.get('download_strategy', '')}"
        )
        attempted_command = (
            "manual_authenticated_new_source_family_acquisition_required:"
            f"{packet.get('target_source_family', '')}:"
            f"{packet.get('authored_field_name', '')}"
            if terminal
            else "local_current_artifact_preflight_then_source_author_search:"
            f"{current_path}:"
            f"{packet.get('authored_field_name', '')}"
        )
        exact_blocker = (
            f"{packet.get('authored_field_name', '')} acquisition execution "
            "preflight remains fail-closed: current artifacts and source "
            "metadata are not admitted field evidence, no promotion-grade "
            "source locator has passed, and authored-invariant plus "
            "independent-replication sibling gates remain blocked."
        )
        rows.append(
            {
                "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id": (
                    "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_promotion_grade_source_family_acquisition_packet_row_id": (
                    packet.get(
                        "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
                        "",
                    )
                ),
                "policy_path_source_protocol_attempt_closure_handoff_row_id": (
                    packet.get(
                        "policy_path_source_protocol_attempt_closure_handoff_row_id",
                        "",
                    )
                ),
                "protocol_component": packet.get("protocol_component", ""),
                "protocol_component_gate": packet.get("protocol_component_gate", ""),
                "authored_field_name": packet.get("authored_field_name", ""),
                "acquisition_task_class": packet.get("acquisition_task_class", ""),
                "execution_preflight_class": execution_class,
                "target_source_family": packet.get("target_source_family", ""),
                "expected_evidence_type": packet.get("expected_evidence_type", ""),
                "required_locator_grain": packet.get("required_locator_grain", ""),
                "current_source_artifact_path": current_path,
                "current_source_artifact_sha256": current_sha,
                "current_source_artifact_availability_status": current_status,
                "candidate_artifact_path": current_path if current_available else "",
                "candidate_artifact_sha256": current_sha if current_available else "",
                "candidate_artifact_status": (
                    "blocked_current_artifact_available_review_only_not_promotion_grade"
                    if current_available
                    else "blocked_no_candidate_artifact_available_for_preflight"
                ),
                "attempted_search_shape": attempted_search,
                "attempted_acquisition_command_shape": attempted_command,
                "attempted_download_shape": attempted_download,
                "parser_readiness_status": parser_ready,
                "deterministic_parser_shape": packet.get(
                    "deterministic_parser_shape", ""
                ),
                "deterministic_parser_command_shape": parser_command,
                "manual_or_authenticated_acquisition_required": _bool(terminal),
                "web_or_source_author_search_required": "true",
                "new_source_family_required": _bool(terminal),
                "source_metadata_admission_status": (
                    "blocked_source_metadata_not_field_evidence"
                ),
                "review_candidate_admission_status": (
                    "blocked_review_candidate_not_admitted_field_evidence"
                ),
                "scalar_shock_shortcut_status": (
                    "blocked_scalar_shocks_and_prompt_numbers_not_source_evidence"
                ),
                "authored_invariant_sibling_gate_status": packet.get(
                    "authored_invariant_sibling_gate_status", ""
                ),
                "independent_replication_sibling_gate_status": packet.get(
                    "independent_replication_sibling_gate_status", ""
                ),
                "acquisition_execution_status": (
                    "blocked_preflight_results_not_source_acquisition"
                ),
                "acquisition_result_status": (
                    "blocked_no_promotion_grade_source_family_acquired_or_admitted"
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_admission_status": packet.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": packet.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": (
                    "run_source_author_search_or_manual_authenticated_acquisition_then_reparse_fail_closed"
                    if terminal
                    else "review_current_artifact_manually_and_search_source_author_alternates_then_reparse_fail_closed"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_source_family_execution_closure_selection_packet_rows(
    *,
    policy_path_promotion_grade_source_family_acquisition_execution_preflight_results_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    allowed_use = "policy_path_source_family_execution_closure_selection_packet_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_source_family_execution_closure_selection_packet_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for preflight in (
        policy_path_promotion_grade_source_family_acquisition_execution_preflight_results_rows
    ):
        new_source = preflight.get("new_source_family_required") == "true"
        selected_route = (
            "manual_authenticated_new_source_family_acquisition"
            if new_source
            else "current_artifact_manual_review"
        )
        fallback_route = (
            "source_author_web_search"
            if not new_source
            else "source_author_web_search_after_manual_authentication_if_needed"
        )
        selected_reason = (
            "current hash-backed artifact exists, but its evidence remains "
            "review-only and must be manually reviewed against the promotion-"
            "grade pass rule before any source-author search fallback"
            if not new_source
            else "current source bundle has terminal no-hit for the required "
            "field, so the next route is manual-authenticated or new-source-"
            "family acquisition before parsing can proceed"
        )
        next_command = (
            "manual_handoff:acquire_new_source_family_or_authenticated_source:"
            f"{preflight.get('target_source_family', '')}:"
            f"{preflight.get('authored_field_name', '')}"
            if new_source
            else preflight.get("deterministic_parser_command_shape", "")
        )
        exact_blocker = (
            f"{preflight.get('authored_field_name', '')} source-family "
            "execution selection remains fail-closed: the selected route is "
            f"{selected_route}, but no promotion-grade source evidence has "
            "been acquired or pass-rule adjudicated; authored-invariant and "
            "independent-replication sibling gates remain blocked."
        )
        rows.append(
            {
                "policy_path_source_family_execution_closure_selection_packet_row_id": (
                    "policy_path_source_family_execution_closure_selection_packet::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id": (
                    preflight.get(
                        "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
                        "",
                    )
                ),
                "policy_path_promotion_grade_source_family_acquisition_packet_row_id": (
                    preflight.get(
                        "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
                        "",
                    )
                ),
                "protocol_component": preflight.get("protocol_component", ""),
                "protocol_component_gate": preflight.get("protocol_component_gate", ""),
                "authored_field_name": preflight.get("authored_field_name", ""),
                "execution_preflight_class": preflight.get(
                    "execution_preflight_class", ""
                ),
                "selected_execution_route": selected_route,
                "fallback_execution_route": fallback_route,
                "selected_route_reason": selected_reason,
                "exact_next_execution_command_or_handoff": next_command,
                "target_source_family": preflight.get("target_source_family", ""),
                "expected_evidence_type": preflight.get("expected_evidence_type", ""),
                "current_artifact_path": preflight.get("current_source_artifact_path", ""),
                "current_artifact_sha256": preflight.get(
                    "current_source_artifact_sha256", ""
                ),
                "current_artifact_status": preflight.get(
                    "current_source_artifact_availability_status", ""
                ),
                "parser_readiness_status": preflight.get(
                    "parser_readiness_status", ""
                ),
                "deterministic_parser_command_shape": preflight.get(
                    "deterministic_parser_command_shape", ""
                ),
                "source_author_search_shape": preflight.get(
                    "attempted_search_shape", ""
                ),
                "manual_authenticated_handoff": (
                    next_command if new_source else ""
                ),
                "promotion_grade_source_evidence_acquired": "false",
                "pass_rule_adjudicated": "false",
                "authored_invariant_sibling_gate_status": preflight.get(
                    "authored_invariant_sibling_gate_status", ""
                ),
                "independent_replication_sibling_gate_status": preflight.get(
                    "independent_replication_sibling_gate_status", ""
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_gate_move_status": (
                    "blocked_no_promotion_grade_source_evidence_or_pass_rule_adjudication"
                ),
                "source_metadata_admission_status": preflight.get(
                    "source_metadata_admission_status", ""
                ),
                "review_candidate_admission_status": preflight.get(
                    "review_candidate_admission_status", ""
                ),
                "scalar_shock_shortcut_status": preflight.get(
                    "scalar_shock_shortcut_status", ""
                ),
                "protocol_admission_status": preflight.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": preflight.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": (
                    "execute_selected_source_family_route_then_rerun_pass_rule_adjudication_fail_closed"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_current_artifact_manual_review_execution_packet_rows(
    *,
    policy_path_source_family_execution_closure_selection_packet_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    allowed_use = (
        "policy_path_current_artifact_manual_review_execution_packet_only"
    )
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_current_artifact_manual_review_execution_packet_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for selection in policy_path_source_family_execution_closure_selection_packet_rows:
        current_route = (
            selection.get("selected_execution_route")
            == "current_artifact_manual_review"
        )
        field = selection.get("authored_field_name", "")
        planned_output = (
            "outputs/tables/policy_path_current_artifact_manual_review/"
            f"{field}.csv"
        )
        manual_blocker = (
            ""
            if current_route
            else (
                "blocked_manual_authenticated_or_new_source_family_required_"
                "before_current_artifact_review_execution"
            )
        )
        execution_class = (
            "current_artifact_manual_review_execution_ready"
            if current_route
            else "blocked_manual_authenticated_new_source_family_non_execution"
        )
        execution_status = (
            "blocked_execution_packet_not_yet_run_current_artifact_review_only"
            if current_route
            else "blocked_no_current_artifact_execution_until_new_source_family_acquired"
        )
        output_or_blocker = planned_output if current_route else manual_blocker
        exact_blocker = (
            f"{field} current-artifact manual-review execution remains "
            "fail-closed: the packet records the command or non-execution "
            "blocker, but no promotion-grade source evidence has been acquired, "
            "no pass-rule adjudication has passed, and sibling authored-"
            "invariant plus independent-replication gates remain blocked."
        )
        rows.append(
            {
                "policy_path_current_artifact_manual_review_execution_packet_row_id": (
                    "policy_path_current_artifact_manual_review_execution_packet::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_source_family_execution_closure_selection_packet_row_id": (
                    selection.get(
                        "policy_path_source_family_execution_closure_selection_packet_row_id",
                        "",
                    )
                ),
                "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id": (
                    selection.get(
                        "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
                        "",
                    )
                ),
                "policy_path_promotion_grade_source_family_acquisition_packet_row_id": (
                    selection.get(
                        "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
                        "",
                    )
                ),
                "protocol_component": selection.get("protocol_component", ""),
                "protocol_component_gate": selection.get("protocol_component_gate", ""),
                "authored_field_name": field,
                "selected_execution_route": selection.get(
                    "selected_execution_route", ""
                ),
                "manual_review_execution_class": execution_class,
                "manual_review_execution_status": execution_status,
                "current_artifact_path": selection.get("current_artifact_path", ""),
                "current_artifact_sha256": selection.get("current_artifact_sha256", ""),
                "current_artifact_status": selection.get("current_artifact_status", ""),
                "parser_readiness_status": selection.get(
                    "parser_readiness_status", ""
                ),
                "current_artifact_review_command_shape": (
                    selection.get("exact_next_execution_command_or_handoff", "")
                    if current_route
                    else ""
                ),
                "source_author_search_fallback_shape": selection.get(
                    "source_author_search_shape", ""
                ),
                "parsed_review_output_path_or_no_run_blocker": output_or_blocker,
                "pass_rule_requirement": (
                    "promotion_grade_evidence_must_pass_source_protocol_pass_rule_before_gate_move"
                ),
                "promotion_grade_source_evidence_required": "true",
                "pass_rule_adjudication_required": "true",
                "manual_authenticated_new_source_family_blocker": manual_blocker,
                "review_candidate_admission_status": selection.get(
                    "review_candidate_admission_status", ""
                ),
                "source_metadata_admission_status": selection.get(
                    "source_metadata_admission_status", ""
                ),
                "scalar_shock_shortcut_status": selection.get(
                    "scalar_shock_shortcut_status", ""
                ),
                "authored_invariant_sibling_gate_status": selection.get(
                    "authored_invariant_sibling_gate_status", ""
                ),
                "independent_replication_sibling_gate_status": selection.get(
                    "independent_replication_sibling_gate_status", ""
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_gate_move_status": selection.get(
                    "protocol_gate_move_status", ""
                ),
                "protocol_admission_status": selection.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": selection.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": (
                    "run_current_artifact_manual_review_commands_then_adjudicate_pass_rules_fail_closed"
                    if current_route
                    else "acquire_manual_authenticated_or_new_source_family_then_rebuild_execution_packet"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def _parser_strategy_from_command(command: str) -> str:
    marker = " --parser-shape "
    if marker not in command:
        return ""
    return command.split(marker, 1)[1].strip()


def _review_only_candidate_for_execution(row: dict[str, str]) -> dict[str, str]:
    artifact_path = row.get("current_artifact_path", "")
    field = row.get("authored_field_name", "")
    artifact_name = Path(artifact_path).name if artifact_path else ""
    suffix = Path(artifact_path).suffix.lower()
    if suffix == ".xlsx":
        locator = "workbook_level_review_only_no_promotion_grade_cell_locator"
        snippet = (
            f"review_only_xlsx_artifact_present::{artifact_name}::{field};"
            " manual sheet/cell review still required"
        )
        value = "review_only_xlsx_presence_not_source_cell_value"
    elif suffix == ".zip":
        locator = "zip_archive_member_review_only_no_promotion_grade_line_locator"
        snippet = (
            f"review_only_zip_artifact_present::{artifact_name}::{field};"
            " archive member/line review still required"
        )
        value = "review_only_zip_presence_not_source_protocol_value"
    elif suffix in {".html", ".htm"}:
        locator = "html_text_review_only_no_promotion_grade_line_locator"
        snippet = (
            f"review_only_html_artifact_present::{artifact_name}::{field};"
            " source-author text review still required"
        )
        value = "review_only_html_presence_not_source_protocol_value"
    else:
        locator = "artifact_review_only_no_promotion_grade_locator"
        snippet = (
            f"review_only_artifact_present::{artifact_name}::{field};"
            " promotion-grade locator still required"
        )
        value = "review_only_artifact_presence_not_source_protocol_value"
    return {
        "review_only_locator_candidate": locator,
        "extracted_review_only_snippet_or_cell_candidate": snippet,
        "extracted_review_only_value_candidate": value,
    }


def policy_path_current_artifact_manual_review_result_attempt_rows(
    *,
    policy_path_current_artifact_manual_review_execution_packet_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    allowed_use = (
        "policy_path_current_artifact_manual_review_result_attempt_only"
    )
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_current_artifact_manual_review_result_attempt_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for execution in policy_path_current_artifact_manual_review_execution_packet_rows:
        run_ready = (
            execution.get("manual_review_execution_class")
            == "current_artifact_manual_review_execution_ready"
        )
        field = execution.get("authored_field_name", "")
        command = execution.get("current_artifact_review_command_shape", "")
        candidate = (
            _review_only_candidate_for_execution(execution)
            if run_ready
            else {
                "review_only_locator_candidate": "",
                "extracted_review_only_snippet_or_cell_candidate": "",
                "extracted_review_only_value_candidate": "",
            }
        )
        non_execution_blocker = (
            ""
            if run_ready
            else execution.get("manual_authenticated_new_source_family_blocker", "")
        )
        parsed_review_output_path = (
            execution.get("parsed_review_output_path_or_no_run_blocker", "")
            if run_ready
            else ""
        )
        attempt_class = (
            "current_artifact_review_only_attempt"
            if run_ready
            else "blocked_manual_authenticated_new_source_family_not_attempted"
        )
        attempt_status = (
            "blocked_review_only_attempt_no_promotion_grade_pass_rule"
            if run_ready
            else "blocked_not_attempted_requires_manual_authenticated_or_new_source_family"
        )
        pass_fail = (
            "fail_review_only_candidate_not_promotion_grade_source_evidence"
            if run_ready
            else "not_run_manual_authenticated_new_source_family_required"
        )
        exact_blocker = (
            f"{field} current-artifact manual-review result attempt remains "
            "fail-closed: any locator, snippet, cell, or value candidate is "
            "review-only, no promotion-grade source evidence has been acquired, "
            "no pass-rule adjudication has passed, and sibling authored-"
            "invariant plus independent-replication gates remain blocked."
        )
        rows.append(
            {
                "policy_path_current_artifact_manual_review_result_attempt_row_id": (
                    "policy_path_current_artifact_manual_review_result_attempt::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_current_artifact_manual_review_execution_packet_row_id": (
                    execution.get(
                        "policy_path_current_artifact_manual_review_execution_packet_row_id",
                        "",
                    )
                ),
                "policy_path_source_family_execution_closure_selection_packet_row_id": (
                    execution.get(
                        "policy_path_source_family_execution_closure_selection_packet_row_id",
                        "",
                    )
                ),
                "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id": (
                    execution.get(
                        "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
                        "",
                    )
                ),
                "policy_path_promotion_grade_source_family_acquisition_packet_row_id": (
                    execution.get(
                        "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
                        "",
                    )
                ),
                "protocol_component": execution.get("protocol_component", ""),
                "protocol_component_gate": execution.get("protocol_component_gate", ""),
                "authored_field_name": field,
                "selected_execution_route": execution.get(
                    "selected_execution_route", ""
                ),
                "manual_review_attempt_class": attempt_class,
                "manual_review_attempt_status": attempt_status,
                "command_attempted": command if run_ready else "",
                "current_artifact_path": execution.get("current_artifact_path", ""),
                "current_artifact_sha256": execution.get("current_artifact_sha256", ""),
                "current_artifact_status": execution.get("current_artifact_status", ""),
                "parser_strategy": _parser_strategy_from_command(command),
                "parser_readiness_status": execution.get(
                    "parser_readiness_status", ""
                ),
                "parsed_review_output_path": parsed_review_output_path,
                "review_only_locator_candidate": candidate[
                    "review_only_locator_candidate"
                ],
                "extracted_review_only_snippet_or_cell_candidate": candidate[
                    "extracted_review_only_snippet_or_cell_candidate"
                ],
                "extracted_review_only_value_candidate": candidate[
                    "extracted_review_only_value_candidate"
                ],
                "pass_rule_predicate": (
                    "pass only if source locator, quoted/cell evidence, unit/sign/"
                    "horizon/formula content, and sibling invariants are "
                    "promotion-grade and independently adjudicated"
                ),
                "pass_fail_review_only_outcome": pass_fail,
                "promotion_grade_source_evidence_acquired": "false",
                "pass_rule_adjudicated": "false",
                "non_execution_blocker": non_execution_blocker,
                "review_candidate_admission_status": execution.get(
                    "review_candidate_admission_status", ""
                ),
                "source_metadata_admission_status": execution.get(
                    "source_metadata_admission_status", ""
                ),
                "scalar_shock_shortcut_status": execution.get(
                    "scalar_shock_shortcut_status", ""
                ),
                "authored_invariant_sibling_gate_status": execution.get(
                    "authored_invariant_sibling_gate_status", ""
                ),
                "independent_replication_sibling_gate_status": execution.get(
                    "independent_replication_sibling_gate_status", ""
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_gate_move_status": execution.get(
                    "protocol_gate_move_status", ""
                ),
                "protocol_admission_status": execution.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": execution.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": (
                    "source_author_search_or_manual_promotion_grade_locator_then_rerun_pass_rule_adjudication"
                    if run_ready
                    else "acquire_manual_authenticated_or_new_source_family_then_attempt_review"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_source_author_manual_acquisition_followup_packet_rows(
    *,
    policy_path_current_artifact_manual_review_result_attempt_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    allowed_use = (
        "policy_path_source_author_manual_acquisition_followup_packet_only"
    )
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_source_author_manual_acquisition_followup_packet_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for attempt in policy_path_current_artifact_manual_review_result_attempt_rows:
        run_ready = (
            attempt.get("manual_review_attempt_class")
            == "current_artifact_review_only_attempt"
        )
        spec = _promotion_grade_source_family_spec(attempt)
        field = attempt.get("authored_field_name", "")
        source_family = spec["target_source_family"]
        search_shape = (
            "web_or_source_author_search_required:"
            "search_source_author_sites_replication_archives_and_existing_payloads_for_"
            f"{field}_promotion_grade_locator"
        )
        download_shape = (
            "download_official_or_source_author_pdf_xlsx_dta_mat_m_code_readme_to_"
            "data_raw_policy_path_protocol_sources_and_record_sha256"
        )
        auth_handoff = (
            "manual_authenticated_source_acquisition_required:"
            f"{source_family}:{field}"
        )
        new_source_handoff = (
            "new_source_family_acquisition_required:"
            f"{source_family}:{field}"
        )
        followup_class = (
            "source_author_search_followup_task"
            if run_ready
            else "manual_authenticated_new_source_family_followup_task"
        )
        selected_route = (
            "source_author_search_then_download_if_promotion_grade_locator_found"
            if run_ready
            else "manual_authenticated_or_new_source_family_acquisition"
        )
        followup_status = (
            "blocked_followup_task_not_source_acquisition_or_evidence"
        )
        review_summary = (
            ";".join(
                part
                for part in (
                    attempt.get("review_only_locator_candidate", ""),
                    attempt.get(
                        "extracted_review_only_snippet_or_cell_candidate", ""
                    ),
                    attempt.get("extracted_review_only_value_candidate", ""),
                )
                if part
            )
            if run_ready
            else attempt.get("non_execution_blocker", "")
        )
        exact_blocker = (
            f"{field} source-author/manual acquisition follow-up remains "
            "fail-closed: the row records only search, download, authenticated "
            "handoff, or new-source-family instructions; no promotion-grade "
            "source artifact has been acquired, no locator has passed, and "
            "sibling authored-invariant plus independent-replication gates "
            "remain blocked."
        )
        rows.append(
            {
                "policy_path_source_author_manual_acquisition_followup_packet_row_id": (
                    "policy_path_source_author_manual_acquisition_followup_packet::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_current_artifact_manual_review_result_attempt_row_id": (
                    attempt.get(
                        "policy_path_current_artifact_manual_review_result_attempt_row_id",
                        "",
                    )
                ),
                "policy_path_current_artifact_manual_review_execution_packet_row_id": (
                    attempt.get(
                        "policy_path_current_artifact_manual_review_execution_packet_row_id",
                        "",
                    )
                ),
                "policy_path_source_family_execution_closure_selection_packet_row_id": (
                    attempt.get(
                        "policy_path_source_family_execution_closure_selection_packet_row_id",
                        "",
                    )
                ),
                "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id": (
                    attempt.get(
                        "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
                        "",
                    )
                ),
                "policy_path_promotion_grade_source_family_acquisition_packet_row_id": (
                    attempt.get(
                        "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
                        "",
                    )
                ),
                "protocol_component": attempt.get("protocol_component", ""),
                "protocol_component_gate": attempt.get("protocol_component_gate", ""),
                "authored_field_name": field,
                "manual_review_attempt_class": attempt.get(
                    "manual_review_attempt_class", ""
                ),
                "followup_task_class": followup_class,
                "followup_task_status": followup_status,
                "selected_followup_route": selected_route,
                "target_source_family": source_family,
                "target_source_artifact_hint": spec["target_source_artifact_hint"],
                "artifact_query_shape": (
                    f"query_current_and_source_author_artifacts_for:{field}:"
                    f"{spec['required_locator_grain']}"
                ),
                "source_author_search_query_shape": search_shape,
                "download_shape": download_shape,
                "authenticated_acquisition_handoff_shape": auth_handoff,
                "new_source_family_handoff_shape": new_source_handoff,
                "required_promotion_grade_locator_grain": spec[
                    "required_locator_grain"
                ],
                "expected_evidence_type": spec["expected_evidence_type"],
                "evidence_acceptance_test": (
                    "accept only source-authored locator-grain evidence that "
                    "satisfies the field pass predicate and preserves sibling "
                    "authored-invariant and independent-replication blockers"
                ),
                "deterministic_parser_shape_after_acquisition": spec[
                    "deterministic_parser_shape"
                ],
                "review_only_candidate_summary": review_summary,
                "review_only_candidate_admission_status": (
                    "blocked_review_only_candidate_not_admitted_field_evidence"
                ),
                "source_metadata_admission_status": attempt.get(
                    "source_metadata_admission_status", ""
                ),
                "scalar_shock_shortcut_status": attempt.get(
                    "scalar_shock_shortcut_status", ""
                ),
                "authored_invariant_sibling_gate_status": attempt.get(
                    "authored_invariant_sibling_gate_status", ""
                ),
                "independent_replication_sibling_gate_status": attempt.get(
                    "independent_replication_sibling_gate_status", ""
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_gate_move_status": attempt.get(
                    "protocol_gate_move_status", ""
                ),
                "protocol_admission_status": attempt.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": attempt.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": (
                    "run_source_author_search_download_or_manual_acquisition_then_rebuild_fail_closed"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_source_author_manual_acquisition_execution_preflight_results_rows(
    *,
    policy_path_source_author_manual_acquisition_followup_packet_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    allowed_use = (
        "policy_path_source_author_manual_acquisition_execution_preflight_results_only"
    )
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_source_author_manual_acquisition_execution_preflight_results_not_bps_year_or_calibration"
    )
    rows: list[dict[str, str]] = []
    for followup in policy_path_source_author_manual_acquisition_followup_packet_rows:
        search_task = (
            followup.get("followup_task_class") == "source_author_search_followup_task"
        )
        field = followup.get("authored_field_name", "")
        attempted_query_or_handoff = (
            followup.get("source_author_search_query_shape", "")
            if search_task
            else followup.get("authenticated_acquisition_handoff_shape", "")
        )
        target_found = (
            f"source_family_preflight_only:{followup.get('target_source_family', '')}"
        )
        download_or_blocker = (
            "blocked_no_download_attempted_without_promotion_grade_target_url"
            if search_task
            else "blocked_manual_authenticated_or_new_source_family_required_no_download"
        )
        parser_readiness = (
            "blocked_parser_waiting_for_promotion_grade_downloaded_source_artifact"
            if search_task
            else "blocked_parser_waiting_for_manual_authenticated_or_new_source_family"
        )
        search_status = (
            "blocked_automated_search_query_recorded_no_promotion_grade_url_admitted"
            if search_task
            else "not_applicable_manual_authenticated_new_source_family_blocker"
        )
        download_status = (
            "blocked_no_download_without_promotion_grade_url_and_locator"
            if search_task
            else "blocked_no_download_manual_authenticated_or_new_source_family_required"
        )
        manual_status = (
            "not_applicable_source_author_search_preflight"
            if search_task
            else "blocked_manual_authenticated_acquisition_required"
        )
        new_source_status = (
            "not_applicable_source_author_search_preflight"
            if search_task
            else "blocked_new_source_family_acquisition_required"
        )
        exact_blocker = (
            f"{field} source-author/manual acquisition execution preflight "
            "remains fail-closed: search, source-family, download, and handoff "
            "metadata are not field evidence; no promotion-grade URL, artifact, "
            "locator, or pass-rule adjudication has been admitted, and sibling "
            "authored-invariant plus independent-replication gates remain blocked."
        )
        rows.append(
            {
                "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id": (
                    "policy_path_source_author_manual_acquisition_execution_preflight_result::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_source_author_manual_acquisition_followup_packet_row_id": (
                    followup.get(
                        "policy_path_source_author_manual_acquisition_followup_packet_row_id",
                        "",
                    )
                ),
                "policy_path_current_artifact_manual_review_result_attempt_row_id": (
                    followup.get(
                        "policy_path_current_artifact_manual_review_result_attempt_row_id",
                        "",
                    )
                ),
                "policy_path_current_artifact_manual_review_execution_packet_row_id": (
                    followup.get(
                        "policy_path_current_artifact_manual_review_execution_packet_row_id",
                        "",
                    )
                ),
                "policy_path_source_family_execution_closure_selection_packet_row_id": (
                    followup.get(
                        "policy_path_source_family_execution_closure_selection_packet_row_id",
                        "",
                    )
                ),
                "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id": (
                    followup.get(
                        "policy_path_promotion_grade_source_family_acquisition_execution_preflight_result_row_id",
                        "",
                    )
                ),
                "policy_path_promotion_grade_source_family_acquisition_packet_row_id": (
                    followup.get(
                        "policy_path_promotion_grade_source_family_acquisition_packet_row_id",
                        "",
                    )
                ),
                "protocol_component": followup.get("protocol_component", ""),
                "protocol_component_gate": followup.get("protocol_component_gate", ""),
                "authored_field_name": field,
                "followup_task_class": followup.get("followup_task_class", ""),
                "acquisition_execution_preflight_class": (
                    "source_author_search_download_preflight_result"
                    if search_task
                    else "manual_authenticated_new_source_family_preflight_blocker"
                ),
                "attempted_query_or_handoff": attempted_query_or_handoff,
                "target_url_or_source_family_found": target_found,
                "target_source_family": followup.get("target_source_family", ""),
                "attempted_download_path_or_no_download_blocker": download_or_blocker,
                "source_artifact_sha256_if_acquired": "",
                "required_promotion_grade_locator_grain": followup.get(
                    "required_promotion_grade_locator_grain", ""
                ),
                "parser_readiness_after_acquisition": parser_readiness,
                "evidence_acceptance_test": followup.get(
                    "evidence_acceptance_test", ""
                ),
                "source_author_search_preflight_status": search_status,
                "download_preflight_status": download_status,
                "manual_authenticated_acquisition_status": manual_status,
                "new_source_family_acquisition_status": new_source_status,
                "acquisition_result_status": (
                    "blocked_no_promotion_grade_source_artifact_or_locator_acquired"
                ),
                "review_only_candidate_admission_status": followup.get(
                    "review_only_candidate_admission_status", ""
                ),
                "source_metadata_admission_status": followup.get(
                    "source_metadata_admission_status", ""
                ),
                "scalar_shock_shortcut_status": followup.get(
                    "scalar_shock_shortcut_status", ""
                ),
                "authored_invariant_sibling_gate_status": followup.get(
                    "authored_invariant_sibling_gate_status", ""
                ),
                "independent_replication_sibling_gate_status": followup.get(
                    "independent_replication_sibling_gate_status", ""
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_gate_move_status": followup.get(
                    "protocol_gate_move_status", ""
                ),
                "protocol_admission_status": followup.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": followup.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": (
                    "perform_real_source_author_search_or_manual_authenticated_acquisition_then_record_hashes_fail_closed"
                ),
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_real_source_author_web_acquisition_attempt_packet_rows(
    *,
    policy_path_source_author_manual_acquisition_execution_preflight_results_rows: list[
        dict[str, str]
    ],
    policy_path_real_source_author_web_acquisition_attempt_manifest_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    allowed_use = "policy_path_real_source_author_web_acquisition_attempt_packet_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_real_source_author_web_acquisition_attempt_packet_not_bps_year_or_calibration"
    )
    manifest_by_preflight = {
        row.get(
            "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
            "",
        ): row
        for row in policy_path_real_source_author_web_acquisition_attempt_manifest_rows
    }
    rows: list[dict[str, str]] = []
    for preflight in policy_path_source_author_manual_acquisition_execution_preflight_results_rows:
        preflight_id = preflight.get(
            "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
            "",
        )
        manifest = manifest_by_preflight.get(preflight_id, {})
        field = preflight.get("authored_field_name", "")
        bounded_attempt_class = manifest.get(
            "bounded_attempt_class",
            "blocked_missing_raw_web_acquisition_attempt_manifest_row",
        )
        downloaded_paths = manifest.get("downloaded_artifact_paths", "")
        downloaded_hashes = manifest.get("downloaded_artifact_sha256s", "")
        parser_readiness = (
            "blocked_downloaded_public_artifacts_require_locator_grain_parse_and_pass_rule_adjudication"
            if downloaded_paths
            else preflight.get("parser_readiness_after_acquisition", "")
        )
        exact_blocker = manifest.get("exact_attempt_blocker") or (
            f"{field} has no raw web acquisition attempt manifest row; "
            "no source-author page, download metadata, source-family hint, "
            "or search instruction can move a policy-path protocol gate."
        )
        next_backend_action = manifest.get("next_backend_action_after_attempt") or (
            "run_materialize_policy_path_source_author_web_acquisition_attempts_then_rebuild_fail_closed"
        )
        rows.append(
            {
                "policy_path_real_source_author_web_acquisition_attempt_packet_row_id": (
                    "policy_path_real_source_author_web_acquisition_attempt_packet::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_real_source_author_web_acquisition_attempt_manifest_row_id": manifest.get(
                    "policy_path_real_source_author_web_acquisition_attempt_manifest_row_id",
                    "",
                ),
                "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id": preflight_id,
                "policy_path_source_author_manual_acquisition_followup_packet_row_id": preflight.get(
                    "policy_path_source_author_manual_acquisition_followup_packet_row_id",
                    "",
                ),
                "protocol_component": preflight.get("protocol_component", ""),
                "protocol_component_gate": preflight.get("protocol_component_gate", ""),
                "authored_field_name": field,
                "target_source_family": preflight.get("target_source_family", ""),
                "bounded_attempt_class": bounded_attempt_class,
                "source_author_search_query_recorded": manifest.get(
                    "source_author_search_query_recorded",
                    preflight.get("attempted_query_or_handoff", ""),
                ),
                "deterministic_public_url_identified": manifest.get(
                    "deterministic_public_url_identified", "false"
                ),
                "candidate_source_urls": manifest.get("candidate_source_urls", ""),
                "candidate_source_url_roles": manifest.get(
                    "candidate_source_url_roles", ""
                ),
                "download_attempt_status": manifest.get(
                    "download_attempt_status",
                    "blocked_missing_raw_web_acquisition_attempt_manifest_row",
                ),
                "downloaded_artifact_paths": downloaded_paths,
                "downloaded_artifact_sha256s": downloaded_hashes,
                "downloaded_artifact_sizes": manifest.get(
                    "downloaded_artifact_sizes", ""
                ),
                "downloaded_artifact_content_types": manifest.get(
                    "downloaded_artifact_content_types", ""
                ),
                "downloaded_at_utc": manifest.get("downloaded_at_utc", ""),
                "source_family_after_attempt": manifest.get(
                    "source_family_after_attempt",
                    preflight.get("target_source_family", ""),
                ),
                "attempt_result_status": manifest.get(
                    "attempt_result_status",
                    "blocked_missing_raw_web_acquisition_attempt_manifest_row",
                ),
                "review_only_candidate_admission_status": preflight.get(
                    "review_only_candidate_admission_status", ""
                ),
                "source_metadata_admission_status": preflight.get(
                    "source_metadata_admission_status", ""
                ),
                "downloaded_artifact_admission_status": (
                    "blocked_downloaded_public_artifact_review_only_not_field_evidence"
                    if downloaded_paths
                    else "blocked_no_downloaded_public_artifact_admitted"
                ),
                "web_search_snippet_admission_status": (
                    "blocked_web_search_snippets_rankings_and_urls_not_field_evidence"
                ),
                "scalar_shock_shortcut_status": preflight.get(
                    "scalar_shock_shortcut_status", ""
                ),
                "parser_readiness_after_attempt": parser_readiness,
                "evidence_acceptance_test": preflight.get(
                    "evidence_acceptance_test", ""
                ),
                "authored_invariant_sibling_gate_status": preflight.get(
                    "authored_invariant_sibling_gate_status", ""
                ),
                "independent_replication_sibling_gate_status": preflight.get(
                    "independent_replication_sibling_gate_status", ""
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_gate_move_status": preflight.get(
                    "protocol_gate_move_status", ""
                ),
                "protocol_admission_status": preflight.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": preflight.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": next_backend_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_downloaded_artifact_locator_parse_adjudication_packet_rows(
    *,
    policy_path_real_source_author_web_acquisition_attempt_packet_rows: list[
        dict[str, str]
    ],
    policy_path_downloaded_artifact_locator_parse_adjudication_manifest_rows: list[
        dict[str, str]
    ],
) -> list[dict[str, str]]:
    allowed_use = (
        "policy_path_downloaded_artifact_locator_parse_adjudication_packet_only"
    )
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_downloaded_artifact_locator_parse_adjudication_packet_not_bps_year_or_calibration"
    )
    manifest_by_attempt = {
        row.get("policy_path_real_source_author_web_acquisition_attempt_packet_row_id", ""): row
        for row in policy_path_downloaded_artifact_locator_parse_adjudication_manifest_rows
    }
    rows: list[dict[str, str]] = []
    for attempt in policy_path_real_source_author_web_acquisition_attempt_packet_rows:
        attempt_id = attempt.get(
            "policy_path_real_source_author_web_acquisition_attempt_packet_row_id",
            "",
        )
        manifest = manifest_by_attempt.get(attempt_id, {})
        field = attempt.get("authored_field_name", "")
        exact_blocker = manifest.get("exact_parse_blocker") or (
            f"{field} has no downloaded-artifact locator parse manifest row; "
            "downloaded artifacts, source pages, URLs, queries, snippets, and "
            "parsed candidates remain non-admitted review context."
        )
        next_backend_action = manifest.get("next_backend_action_after_parse") or (
            "run_downloaded_artifact_locator_parse_adjudication_manifest_then_rebuild_fail_closed"
        )
        rows.append(
            {
                "policy_path_downloaded_artifact_locator_parse_adjudication_packet_row_id": (
                    "policy_path_downloaded_artifact_locator_parse_adjudication_packet::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_downloaded_artifact_locator_parse_adjudication_manifest_row_id": manifest.get(
                    "policy_path_downloaded_artifact_locator_parse_adjudication_manifest_row_id",
                    "",
                ),
                "policy_path_real_source_author_web_acquisition_attempt_packet_row_id": attempt_id,
                "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id": attempt.get(
                    "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
                    "",
                ),
                "policy_path_source_author_manual_acquisition_followup_packet_row_id": attempt.get(
                    "policy_path_source_author_manual_acquisition_followup_packet_row_id",
                    "",
                ),
                "protocol_component": attempt.get("protocol_component", ""),
                "protocol_component_gate": attempt.get("protocol_component_gate", ""),
                "authored_field_name": field,
                "target_source_family": attempt.get("target_source_family", ""),
                "parse_attempt_class": manifest.get(
                    "parse_attempt_class",
                    "blocked_missing_downloaded_artifact_locator_parse_manifest_row",
                ),
                "bounded_attempt_class": attempt.get("bounded_attempt_class", ""),
                "candidate_locator_count": manifest.get("candidate_locator_count", "0"),
                "candidate_source_artifact_paths": manifest.get(
                    "candidate_source_artifact_paths", ""
                ),
                "candidate_source_artifact_sha256s": manifest.get(
                    "candidate_source_artifact_sha256s", ""
                ),
                "candidate_source_locations": manifest.get(
                    "candidate_source_locations", ""
                ),
                "candidate_locator_grain": manifest.get("candidate_locator_grain", ""),
                "candidate_snippet_or_cell_or_code_line": manifest.get(
                    "candidate_snippet_or_cell_or_code_line", ""
                ),
                "candidate_parsed_value_review_only": manifest.get(
                    "candidate_parsed_value_review_only", ""
                ),
                "pass_rule_predicate": manifest.get("pass_rule_predicate", ""),
                "locator_candidate_status": manifest.get(
                    "locator_candidate_status",
                    "blocked_missing_downloaded_artifact_locator_parse_manifest_row",
                ),
                "pass_rule_adjudication_status": manifest.get(
                    "pass_rule_adjudication_status",
                    "blocked_missing_downloaded_artifact_locator_parse_manifest_row",
                ),
                "parsed_candidate_admission_status": manifest.get(
                    "parsed_candidate_admission_status",
                    "blocked_missing_downloaded_artifact_locator_parse_manifest_row",
                ),
                "source_page_admission_status": (
                    "blocked_source_pages_review_only_not_field_evidence"
                ),
                "downloaded_artifact_admission_status": attempt.get(
                    "downloaded_artifact_admission_status", ""
                ),
                "web_url_admission_status": "blocked_web_urls_not_field_evidence",
                "search_query_record_admission_status": (
                    "blocked_search_query_records_not_field_evidence"
                ),
                "scalar_shock_shortcut_status": attempt.get(
                    "scalar_shock_shortcut_status", ""
                ),
                "authored_invariant_sibling_gate_status": attempt.get(
                    "authored_invariant_sibling_gate_status", ""
                ),
                "independent_replication_sibling_gate_status": attempt.get(
                    "independent_replication_sibling_gate_status", ""
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_gate_move_status": attempt.get(
                    "protocol_gate_move_status", ""
                ),
                "protocol_admission_status": attempt.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": attempt.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": next_backend_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def policy_path_locator_candidate_pass_rule_review_decision_packet_rows(
    *,
    policy_path_downloaded_artifact_locator_parse_adjudication_packet_rows: list[
        dict[str, str]
    ],
    policy_path_field_specific_pass_rule_design_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_use = "policy_path_locator_candidate_pass_rule_review_decision_packet_only"
    blocked_use = (
        "bps_year_policy_path;denominator_prior;main_ratio;Evidence_Mode;"
        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
        "empirical_threshold;tax_incidence_welfare_mpc;causal_financialization"
    )
    claim_boundary = (
        "policy_path_locator_candidate_pass_rule_review_decision_packet_not_bps_year_or_calibration"
    )
    design_by_field = {
        row.get("authored_field_name", ""): row
        for row in policy_path_field_specific_pass_rule_design_rows
    }
    rows: list[dict[str, str]] = []
    for parsed in policy_path_downloaded_artifact_locator_parse_adjudication_packet_rows:
        field = parsed.get("authored_field_name", "")
        design = design_by_field.get(field, {})
        has_candidate = (
            parsed.get("parse_attempt_class")
            == "downloaded_public_artifact_locator_candidate_parse"
            and int(parsed.get("candidate_locator_count", "0") or "0") > 0
            and bool(parsed.get("candidate_source_locations"))
            and bool(parsed.get("candidate_snippet_or_cell_or_code_line"))
        )
        no_hit = (
            parsed.get("parse_attempt_class")
            == "downloaded_public_artifact_locator_candidate_no_hit"
        )
        manual = (
            parsed.get("parse_attempt_class")
            == "manual_authenticated_new_source_family_parse_blocker"
        )
        if has_candidate:
            review_class = "nonpromotional_locator_candidate_review_pass"
            locator_review_status = "pass_locator_candidate_matches_minimum_pass_rule_review_inputs"
            review_outcome = "review_pass_nonpromotional_sibling_gates_block_promotion"
            pass_rule_status = "blocked_review_pass_is_not_protocol_admission"
            exact_blocker = (
                f"{field} has a locator-grain candidate matching the minimum "
                "field pass-rule review inputs, but review-pass is nonpromotional: "
                "authored-invariant sibling gates and independent-replication "
                "sibling gates remain blocked."
            )
            next_action = (
                "review_candidate_manually_then_resolve_authored_invariant_and_independent_replication_gates"
            )
        elif no_hit:
            review_class = "locator_candidate_review_fail_no_hit"
            locator_review_status = "blocked_no_locator_candidate_to_review"
            review_outcome = "review_fail_no_locator_candidate"
            pass_rule_status = "blocked_no_locator_candidate_available_for_pass_rule"
            exact_blocker = (
                f"{field} has downloaded public artifacts, but no locator-grain "
                "candidate was extracted, so the field-specific pass rule cannot "
                "be reviewed or promoted."
            )
            next_action = "manual_review_downloaded_artifacts_or_acquire_new_source_family"
        elif manual:
            review_class = "manual_authenticated_new_source_family_review_blocker"
            locator_review_status = (
                "blocked_manual_authenticated_or_new_source_family_required"
            )
            review_outcome = "review_blocked_manual_authenticated_or_new_source_family"
            pass_rule_status = "blocked_no_downloaded_artifact_for_pass_rule_review"
            exact_blocker = (
                f"{field} remains blocked because the required source is manual-"
                "authenticated or requires a new source family; there is no "
                "downloaded locator candidate to review."
            )
            next_action = "manual_authenticated_or_new_source_family_acquisition_required"
        else:
            review_class = "locator_candidate_review_blocked_missing_parse_manifest"
            locator_review_status = "blocked_missing_parse_manifest_row"
            review_outcome = "review_blocked_missing_parse_manifest_row"
            pass_rule_status = "blocked_missing_parse_manifest_row_for_pass_rule_review"
            exact_blocker = (
                f"{field} is missing a parse/adjudication packet row, so the "
                "field-specific pass rule cannot be reviewed."
            )
            next_action = "rebuild_downloaded_artifact_locator_parse_packet_fail_closed"

        rows.append(
            {
                "policy_path_locator_candidate_pass_rule_review_decision_packet_row_id": (
                    "policy_path_locator_candidate_pass_rule_review_decision_packet::"
                    f"{len(rows) + 1:04d}"
                ),
                "policy_path_downloaded_artifact_locator_parse_adjudication_packet_row_id": parsed.get(
                    "policy_path_downloaded_artifact_locator_parse_adjudication_packet_row_id",
                    "",
                ),
                "policy_path_field_specific_pass_rule_design_row_id": design.get(
                    "policy_path_field_specific_pass_rule_design_row_id", ""
                ),
                "policy_path_real_source_author_web_acquisition_attempt_packet_row_id": parsed.get(
                    "policy_path_real_source_author_web_acquisition_attempt_packet_row_id",
                    "",
                ),
                "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id": parsed.get(
                    "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
                    "",
                ),
                "policy_path_source_author_manual_acquisition_followup_packet_row_id": parsed.get(
                    "policy_path_source_author_manual_acquisition_followup_packet_row_id",
                    "",
                ),
                "protocol_component": parsed.get("protocol_component", ""),
                "protocol_component_gate": parsed.get("protocol_component_gate", ""),
                "authored_field_name": field,
                "target_source_family": parsed.get("target_source_family", ""),
                "parse_attempt_class": parsed.get("parse_attempt_class", ""),
                "pass_rule_review_class": review_class,
                "field_pass_rule_design_status": design.get(
                    "field_pass_rule_status", ""
                ),
                "source_locator_requirement": design.get(
                    "source_locator_requirement", ""
                ),
                "row_line_cell_reference_requirement": design.get(
                    "row_line_cell_reference_requirement", ""
                ),
                "extracted_value_requirement": design.get(
                    "extracted_value_requirement", ""
                ),
                "source_quote_cell_evidence_requirement": design.get(
                    "source_quote_cell_evidence_requirement", ""
                ),
                "field_acceptance_test": design.get("field_acceptance_test", ""),
                "promotion_grade_evidence_requirement": design.get(
                    "promotion_grade_evidence_requirement", ""
                ),
                "machine_testable_pass_condition": design.get(
                    "machine_testable_pass_condition", ""
                ),
                "machine_testable_fail_condition": design.get(
                    "machine_testable_fail_condition", ""
                ),
                "candidate_locator_count": parsed.get("candidate_locator_count", "0"),
                "candidate_source_artifact_paths": parsed.get(
                    "candidate_source_artifact_paths", ""
                ),
                "candidate_source_artifact_sha256s": parsed.get(
                    "candidate_source_artifact_sha256s", ""
                ),
                "candidate_source_locations": parsed.get(
                    "candidate_source_locations", ""
                ),
                "candidate_locator_grain": parsed.get("candidate_locator_grain", ""),
                "candidate_snippet_or_cell_or_code_line": parsed.get(
                    "candidate_snippet_or_cell_or_code_line", ""
                ),
                "candidate_parsed_value_review_only": parsed.get(
                    "candidate_parsed_value_review_only", ""
                ),
                "locator_candidate_status": parsed.get("locator_candidate_status", ""),
                "locator_candidate_review_status": locator_review_status,
                "pass_rule_review_outcome": review_outcome,
                "pass_rule_adjudication_status": pass_rule_status,
                "field_pass_rule_status": "blocked_pass_rule_review_not_protocol_admission",
                "parsed_candidate_admission_status": parsed.get(
                    "parsed_candidate_admission_status", ""
                ),
                "authored_invariant_sibling_gate_status": parsed.get(
                    "authored_invariant_sibling_gate_status", ""
                ),
                "independent_replication_sibling_gate_status": parsed.get(
                    "independent_replication_sibling_gate_status", ""
                ),
                "sibling_gate_joint_status": (
                    "blocked_authored_invariant_and_independent_replication_gates_not_passed"
                ),
                "protocol_gate_move_allowed": "false",
                "protocol_gate_move_status": parsed.get(
                    "protocol_gate_move_status", ""
                ),
                "protocol_admission_status": parsed.get(
                    "protocol_admission_status", ""
                ),
                "policy_path_100bp_year_normalization_status": parsed.get(
                    "policy_path_100bp_year_normalization_status", ""
                ),
                "candidate_rate_change_bps": "",
                "candidate_bps_year_component": "",
                "candidate_bps_year_exposure": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": exact_blocker,
                "next_backend_action": next_action,
                "allowed_use": allowed_use,
                "blocked_use": blocked_use,
                "claim_boundary": claim_boundary,
                **_false_fields(),
            }
        )
    return rows


def _authored_fail_closed_invariant_runtime_spec(field: str) -> dict[str, str]:
    runtime_fields = (
        "candidate_rate_change_bps;candidate_bps_year_component;"
        "candidate_bps_year_exposure;bps_year_exposure_output;"
        "candidate_gdp_share_drag_per_100bp_year;candidate_ci_lower;"
        "candidate_ci_upper;denominator_prior_update_allowed;enters_main_ratio;"
        "evidence_mode_enabled;raw_rate_shock_enabled"
    )
    status_fields = (
        "protocol_admission_status;policy_path_100bp_year_normalization_status;"
        "replication_admission_status;invariant_admission_status"
    )
    base = {
        "protected_runtime_fields": runtime_fields,
        "protected_status_fields": status_fields,
        "pass_status_value": "pass_authored_fail_closed_invariant",
        "blocked_status_value": "blocked_authored_fail_closed_invariant_missing_or_failed",
    }
    specs = {
        "failure_rollback_behavior": {
            "invariant_family": "promotion_rule",
            "invariant_role": "failure_rollback_behavior",
            "invariant_design_deliverable": (
                "Clear all candidate outputs and disable all runtime switches "
                "whenever any required protocol gate fails."
            ),
            "trigger_condition": "any_protocol_gate_or_promotion_rule_not_pass",
            "machine_testable_pass_condition": (
                "pass only if every blocked protocol row has blank candidate "
                "outputs and all runtime/promotion switches false"
            ),
            "machine_testable_fail_condition": (
                "blocked if any failed gate leaves a candidate output, prior, "
                "Evidence Mode, main-ratio, raw-shock, pricing, or holder switch enabled"
            ),
        },
        "gate_conjunction": {
            "invariant_family": "promotion_rule",
            "invariant_role": "gate_conjunction",
            "invariant_design_deliverable": (
                "Require source-cell unit/sign, horizon grid, loading/back-"
                "transform, bps-year formula, independent replication, "
                "denominator isolation, and promotion-rule gates to pass jointly."
            ),
            "trigger_condition": "promotion_status_evaluation",
            "machine_testable_pass_condition": (
                "pass only if promotion is impossible unless every required "
                "gate has an explicit pass_* admission status"
            ),
            "machine_testable_fail_condition": (
                "blocked if reviewed, diagnostic, scalar, prompt, or metadata-only "
                "status can satisfy the gate conjunction"
            ),
        },
        "replication_tolerance_gate": {
            "invariant_family": "promotion_rule",
            "invariant_role": "replication_tolerance_gate",
            "invariant_design_deliverable": (
                "Require independent replication target/tolerance pass before "
                "any policy-path protocol admission."
            ),
            "trigger_condition": "replication_gate_evaluation",
            "machine_testable_pass_condition": (
                "pass only if independent replication artifact, command, target, "
                "and tolerance audit all pass"
            ),
            "machine_testable_fail_condition": (
                "blocked if replication target/tolerance is absent, design-only, "
                "review-only, or bypassed"
            ),
        },
        "required_pass_statuses": {
            "invariant_family": "promotion_rule",
            "invariant_role": "required_pass_statuses",
            "invariant_design_deliverable": (
                "Define exact pass status prefixes and reject reviewed_* or "
                "diagnostic_* strings as admission."
            ),
            "trigger_condition": "status_string_interpretation",
            "machine_testable_pass_condition": (
                "pass only if admitted status strings start with explicit pass_ "
                "fields owned by the promotion gate"
            ),
            "machine_testable_fail_condition": (
                "blocked if reviewed_*, diagnostic_*, metadata_only, or prompt_ "
                "strings are interpreted as admission"
            ),
        },
        "reviewer_audit_fields": {
            "invariant_family": "promotion_rule",
            "invariant_role": "reviewer_audit_fields",
            "invariant_design_deliverable": (
                "Require source row ids, source artifact hashes, extracted field "
                "values, pass/fail audit fields, and ledger links before promotion."
            ),
            "trigger_condition": "promotion_audit_packaging",
            "machine_testable_pass_condition": (
                "pass only if every promoted field has nonblank row ids, hashes, "
                "field values, audit status, and ledger coverage"
            ),
            "machine_testable_fail_condition": (
                "blocked if reviewer audit fields are blank, unledgered, or "
                "cannot identify source rows and artifacts"
            ),
        },
        "denominator_prior_block": {
            "invariant_family": "denominator_isolation",
            "invariant_role": "denominator_prior_block",
            "invariant_design_deliverable": (
                "Keep denominator_prior_update_allowed false until full protocol "
                "admission passes."
            ),
            "trigger_condition": "denominator_prior_update_attempt",
            "machine_testable_pass_condition": (
                "pass only if denominator_prior_update_allowed is false for all "
                "non-admitted policy-path rows"
            ),
            "machine_testable_fail_condition": (
                "blocked if review-only or design-only policy-path rows can "
                "update denominator priors"
            ),
        },
        "evidence_mode_block": {
            "invariant_family": "denominator_isolation",
            "invariant_role": "evidence_mode_block",
            "invariant_design_deliverable": (
                "Keep evidence_mode_enabled false until full protocol admission passes."
            ),
            "trigger_condition": "evidence_mode_access_attempt",
            "machine_testable_pass_condition": (
                "pass only if evidence_mode_enabled is false for all non-admitted "
                "policy-path rows"
            ),
            "machine_testable_fail_condition": (
                "blocked if Evidence Mode can read review-only policy-path rows"
            ),
        },
        "denominator_isolation_failure_behavior": {
            "invariant_family": "denominator_isolation",
            "invariant_role": "blocked_state_failure_behavior",
            "invariant_design_deliverable": (
                "Blank all runtime denominator and candidate fields whenever "
                "policy-path protocol state is blocked."
            ),
            "trigger_condition": "protocol_state_blocked",
            "machine_testable_pass_condition": (
                "pass only if blocked rows have blank rate, bps-year, GDP-share, "
                "CI, and denominator fields"
            ),
            "machine_testable_fail_condition": (
                "blocked if any blocked policy-path row retains a candidate "
                "rate, bps-year, GDP-share, CI, or denominator value"
            ),
        },
        "main_ratio_block": {
            "invariant_family": "denominator_isolation",
            "invariant_role": "main_ratio_block",
            "invariant_design_deliverable": (
                "Keep enters_main_ratio false until full protocol admission passes."
            ),
            "trigger_condition": "main_ratio_entry_attempt",
            "machine_testable_pass_condition": (
                "pass only if enters_main_ratio is false for all non-admitted "
                "policy-path rows"
            ),
            "machine_testable_fail_condition": (
                "blocked if the main ratio can consume review-only policy-path rows"
            ),
        },
        "non_use_boundary": {
            "invariant_family": "denominator_isolation",
            "invariant_role": "non_use_boundary",
            "invariant_design_deliverable": (
                "Require allowed_use, blocked_use, and claim_boundary to preserve "
                "review-only non-runtime semantics."
            ),
            "trigger_condition": "claim_boundary_or_use_status_evaluation",
            "machine_testable_pass_condition": (
                "pass only if allowed_use is review/design-only, blocked_use "
                "includes runtime/main-ratio uses, and claim_boundary is nonblank"
            ),
            "machine_testable_fail_condition": (
                "blocked if claim boundary is blank or permits runtime, main-ratio, "
                "Evidence Mode, prior, pricing, holder, or raw-shock use"
            ),
        },
        "raw_rate_shock_block": {
            "invariant_family": "denominator_isolation",
            "invariant_role": "raw_rate_shock_block",
            "invariant_design_deliverable": (
                "Keep raw_rate_shock_enabled false unless a separate source-gated "
                "runtime path is explicitly admitted."
            ),
            "trigger_condition": "raw_rate_shock_output_attempt",
            "machine_testable_pass_condition": (
                "pass only if raw_rate_shock_enabled is false for all non-admitted "
                "policy-path rows"
            ),
            "machine_testable_fail_condition": (
                "blocked if raw-rate-shock output can be enabled from review-only "
                "or design-only protocol rows"
            ),
        },
    }
    return {**base, **specs.get(field, {})}


def _independent_replication_target_design_spec(field: str) -> dict[str, str]:
    base = {
        "replication_command_or_procedure": (
            "PYTHONDONTWRITEBYTECODE=1 $HOME/venvs/ratewall/bin/python "
            "-m ratewall.cli databook build --output-dir outputs"
        ),
        "expected_output_value_table": (
            "ratewall_policy_path_project_authored_bps_year_event_exposure.csv;"
            "ratewall_policy_path_project_authored_bps_year_replication_protocol.csv;"
            "ratewall_policy_path_project_authored_bps_year_exposure_admission_consumer.csv"
        ),
        "pass_fail_audit_field": (
            "ratewall_policy_path_project_authored_bps_year_event_exposure.csv::"
            "event_replication_status"
        ),
        "replication_target_artifact": (
            "outputs/tables/ratewall_policy_path_project_authored_bps_year_event_exposure.csv;"
            "outputs/tables/ratewall_policy_path_project_authored_bps_year_replication_protocol.csv"
        ),
        "replication_target_artifact_hash_requirement": (
            "required_sha256_for_target_artifact_and_all_declared_inputs"
        ),
        "numeric_tolerance": (
            "1e-08"
        ),
        "tolerance_unit": "absolute_normalized_100bp_year_exposure",
        "tolerance_comparison": (
            "max_abs_diff_less_than_or_equal_to_tolerance"
        ),
        "pass_status_value": "pass_independent_replication_target_tolerance",
        "blocked_status_value": (
            "blocked_independent_replication_target_tolerance_missing_or_failed"
        ),
        "implementation_status": (
            "pass_project_authored_event_exposure_rebuild_executed_nonpromotional"
        ),
        "replication_admission_status": "pass_independent_replication_target_tolerance",
        "exact_blocker": (
            "event-level review-only bps-year exposure rebuild is executed and "
            "matches within tolerance, closing the independent replication "
            "target/tolerance component only. Full protocol admission remains "
            "blocked until source-evidence components close; no admitted bps-year "
            "or denominator outputs are populated."
        ),
        "next_backend_action": (
            "preserve_independent_replication_pass_until_source_evidence_components_close"
        ),
    }
    overrides = {
        "replication_command_or_procedure": {
            "replication_design_role": "deterministic_rebuild_or_verify_procedure",
            "replication_design_deliverable": (
                "Execute the noninteractive project-authored event-exposure "
                "rebuild from source-authored cells while preserving it as "
                "nonpromotional until full protocol admission."
            ),
            "machine_testable_pass_condition": (
                "pass only if command/procedure is nonblank, noninteractive, "
                "declares all inputs, and does not read prompt-derived numbers"
            ),
            "machine_testable_fail_condition": (
                "blocked if command/procedure is blank, interactive-only, "
                "source-free, or writes candidate bps-year values"
            ),
        },
        "expected_output_value_table": {
            "replication_design_role": "expected_output_schema_contract",
            "replication_design_deliverable": (
                "Record the executed event-exposure replication output schema "
                "while blocking all admitted bps-year and denominator outputs."
            ),
            "machine_testable_pass_condition": (
                "pass only if expected-output schema is nonblank and every "
                "numeric target field remains blank until source-backed"
            ),
            "machine_testable_fail_condition": (
                "blocked if expected output contains scalar prompt numbers, "
                "candidate bps-year values, or denominator values"
            ),
        },
        "pass_fail_audit_field": {
            "replication_design_role": "pass_fail_audit_contract",
            "replication_design_deliverable": (
                "Bind to the event-exposure replication pass/fail field and "
                "preserve full protocol admission as blocked until source "
                "components close."
            ),
            "machine_testable_pass_condition": (
                "pass only if audit field cannot pass without artifact hash, "
                "target artifact, command/procedure, and tolerance check"
            ),
            "machine_testable_fail_condition": (
                "blocked if audit field can pass from review-only, diagnostic, "
                "or scalar-shock evidence"
            ),
        },
        "replication_target_artifact": {
            "replication_design_role": "independent_target_artifact_contract",
            "replication_design_deliverable": (
                "Record the hash-backed event-exposure replication artifacts "
                "and their non-substitution boundary for runtime/denominator "
                "outputs."
            ),
            "machine_testable_pass_condition": (
                "pass only if target artifact path/hash/provenance are present "
                "and are independent of current review-only snippets"
            ),
            "machine_testable_fail_condition": (
                "blocked if target artifact is missing, prompt-derived, "
                "review-only, or not hash-backed"
            ),
        },
        "numeric_tolerance": {
            "replication_design_role": "numeric_tolerance_contract",
            "replication_design_deliverable": (
                "Record the event-exposure rebuild tolerance and its non-use "
                "as admitted runtime output."
            ),
            "machine_testable_pass_condition": (
                "pass only if tolerance has unit, comparison direction, and is "
                "applied to a source-backed independent target"
            ),
            "machine_testable_fail_condition": (
                "blocked if tolerance is blank, unitless, prompt-derived, or "
                "permits scalar-shock/static-quarter shortcuts"
            ),
        },
    }
    return {**base, **overrides.get(field, {})}


def _replication_design_spec(field_name: str) -> dict[str, str]:
    artifact = "ratewall_policy_path_independent_replication_target_design.csv"
    base = {
        "deliverable_name": field_name,
        "machine_test_target": artifact,
        "required_input_artifacts": (
            "ratewall_policy_path_authored_protocol_completion_audit.csv;"
            "ratewall_policy_path_source_extraction_results.csv"
        ),
        "required_output_artifact": artifact,
        "runtime_switch_guardrail": (
            "replication design cannot populate bps-year, GDP-share, prior, "
            "Evidence Mode, main-ratio, raw-shock, pricing, or holder fields"
        ),
    }
    suffix = field_name.rsplit("__", 1)[-1]
    mapping = {
        "command_or_procedure": (
            "replication_command_or_procedure",
            "nonblank deterministic command/procedure with explicit input artifacts",
            "blocked if command/procedure is blank, interactive-only, or source-free",
        ),
        "expected_output_value_table": (
            "expected_output_value_table",
            "nonblank expected-output table/schema with no runtime candidate values",
            "blocked if expected output is a scalar prompt number or candidate bps-year",
        ),
        "pass_fail_audit_field": (
            "pass_fail_audit_field",
            "nonblank pass/fail audit field whose pass value requires replicated target and tolerance",
            "blocked if pass/fail field can pass without independent replication evidence",
        ),
        "replication_target_artifact": (
            "replication_target_artifact",
            "nonblank independent target artifact path and hash/provenance requirement",
            "blocked if target artifact is missing, prompt-derived, or review-only",
        ),
        "tolerance": (
            "numeric_tolerance",
            "nonblank numeric tolerance definition with unit and comparison direction",
            "blocked if tolerance is blank, unitless, or permits scalar-shock shortcuts",
        ),
    }
    output_field, pass_condition, failure_condition = mapping.get(
        suffix,
        (
            "independent_replication_design_field",
            "nonblank replication design field",
            "blocked if replication design field is blank",
        ),
    )
    return {
        **base,
        "required_output_field": output_field,
        "machine_testable_requirement": (
            f"{field_name} must be represented as {output_field} in {artifact}"
        ),
        "required_pass_condition": pass_condition,
        "required_failure_condition": failure_condition,
    }


def _authored_invariant_design_spec(field_name: str) -> dict[str, str]:
    artifact = "ratewall_policy_path_authored_fail_closed_invariant_design.csv"
    base = {
        "deliverable_name": field_name,
        "machine_test_target": artifact,
        "required_input_artifacts": (
            "ratewall_policy_path_authored_protocol_completion_audit.csv;"
            "ratewall_policy_path_source_extraction_results.csv"
        ),
        "required_output_artifact": artifact,
        "runtime_switch_guardrail": (
            "invariant design cannot enable bps-year, GDP-share, prior, "
            "Evidence Mode, main-ratio, raw-shock, pricing, holder, or claims switches"
        ),
    }
    mapping = {
        "promotion_rule__failure_rollback_behavior": (
            "failure_rollback_behavior",
            "if any protocol gate fails, all candidate outputs remain blank and all switches false",
            "blocked if failure behavior leaves stale candidate outputs or enabled switches",
        ),
        "promotion_rule__gate_conjunction": (
            "gate_conjunction",
            "promotion can pass only when all source, formula, replication, isolation, and promotion gates pass",
            "blocked if any reviewed or diagnostic status can satisfy a promotion gate",
        ),
        "promotion_rule__replication_tolerance": (
            "replication_tolerance_gate",
            "promotion requires independent replication status to pass with designed tolerance",
            "blocked if replication tolerance is absent or bypassed",
        ),
        "promotion_rule__required_pass_statuses": (
            "required_pass_statuses",
            "promotion requires explicit pass status values, not reviewed or diagnostic strings",
            "blocked if reviewed_* or diagnostic_* statuses are interpreted as pass",
        ),
        "promotion_rule__reviewer_audit_fields": (
            "reviewer_audit_fields",
            "promotion requires source row ids, artifact hashes, field values, and audit status fields",
            "blocked if reviewer audit fields are blank or not ledgered",
        ),
        "denominator_isolation__denominator_prior_block": (
            "denominator_prior_block",
            "denominator_prior_update_allowed remains false unless protocol admission passes",
            "blocked if denominator priors can update from review-only policy-path rows",
        ),
        "denominator_isolation__evidence_mode_block": (
            "evidence_mode_block",
            "evidence_mode_enabled remains false unless protocol admission passes",
            "blocked if Evidence Mode can read review-only policy-path rows",
        ),
        "denominator_isolation__failure_behavior": (
            "denominator_isolation_failure_behavior",
            "blocked protocol state blanks all runtime denominator and candidate fields",
            "blocked if blocked rows retain candidate values after failure",
        ),
        "denominator_isolation__main_ratio_block": (
            "main_ratio_block",
            "enters_main_ratio remains false unless protocol admission passes",
            "blocked if main ratio can read review-only policy-path rows",
        ),
        "denominator_isolation__non_use_boundary": (
            "non_use_boundary",
            "allowed_use, blocked_use, and claim_boundary preserve review-only/non-admission semantics",
            "blocked if claim boundary is blank or allows runtime use",
        ),
        "denominator_isolation__raw_rate_shock_block": (
            "raw_rate_shock_block",
            "raw_rate_shock_enabled remains false unless a separate source-gated runtime path exists",
            "blocked if raw shock output can be enabled from protocol review rows",
        ),
    }
    output_field, pass_condition, failure_condition = mapping.get(
        field_name,
        (
            "authored_fail_closed_invariant",
            "explicit invariant has a deterministic pass condition",
            "blocked if invariant pass condition is missing",
        ),
    )
    return {
        **base,
        "required_output_field": output_field,
        "machine_testable_requirement": (
            f"{field_name} must be represented as {output_field} in {artifact}"
        ),
        "required_pass_condition": pass_condition,
        "required_failure_condition": failure_condition,
    }


def _source_extraction_preservation_spec(field_name: str) -> dict[str, str]:
    return {
        "deliverable_name": field_name,
        "machine_test_target": (
            "ratewall_policy_path_field_specific_pass_rule_design.csv"
        ),
        "machine_testable_requirement": (
            "review-only source field remains non-admitted until a field-specific "
            "pass rule and extracted value are authored"
        ),
        "required_input_artifacts": (
            "ratewall_policy_path_source_extraction_results.csv;"
            "ratewall_policy_path_authored_protocol_completion_audit.csv"
        ),
        "required_output_artifact": (
            "ratewall_policy_path_field_specific_pass_rule_design.csv"
        ),
        "required_output_field": "field_specific_pass_rule_and_extracted_value",
        "required_pass_condition": (
            "field-specific pass rule, source locator, row/line ref, extracted "
            "value, and promotion-grade evidence are all nonblank"
        ),
        "required_failure_condition": (
            "blocked if only review-only snippets or hash-backed source context exist"
        ),
        "runtime_switch_guardrail": (
            "review-only source field cannot populate bps-year, GDP-share, prior, "
            "Evidence Mode, main-ratio, raw-shock, pricing, or holder fields"
        ),
    }


def _join_unique(values: list[str]) -> str:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique_values.append(value)
    return ";".join(unique_values)


def _short_join(values: list[str], *, limit: int = 1200) -> str:
    text = " || ".join(value for value in values if value)
    return text[:limit]


def _parser_strategy(protocol_component: str) -> str:
    mapping = {
        "source_cell_unit_sign": "extract_source_cell_unit_sign_quote_or_code_ref",
        "event_date_horizon_grid": "extract_event_date_horizon_grid_from_source_code_or_docs",
        "loading_back_transform": "extract_factor_loading_or_back_transform_rule",
        "bps_year_formula": "extract_bps_year_integral_formula_text_or_code",
        "denominator_isolation": "author_denominator_isolation_invariant",
        "promotion_rule": "author_promotion_rule_invariant",
        "independent_replication_target_tolerance": (
            "design_independent_replication_target_tolerance"
        ),
    }
    return mapping.get(protocol_component, "field_specific_source_extraction")
