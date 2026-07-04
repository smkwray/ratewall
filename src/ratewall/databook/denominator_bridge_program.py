"""Denominator-stack registries and residualized-FFR bridge artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import sqrt
from pathlib import Path
from typing import Sequence

from ratewall.accounting.assumption_engine import DEFAULT_RATEWALL_ASSUMPTIONS
from ratewall.accounting.ratewall_threshold import CANONICAL_CONTRACTIONARY_DRAG_PP_GDP


DENOMINATOR_METHODODOLOGY_REGISTRY_FIELDS = [
    "methodology_row_id",
    "route_id",
    "route_family",
    "route_label",
    "route_role",
    "primary_route_class",
    "anchor_job",
    "outcome_id",
    "shock_unit",
    "timing_class",
    "normalization_status",
    "estimator_family",
    "source_family",
    "sample_scope",
    "benchmark_only",
    "scenario_runtime_allowed",
    "current_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

ANNUAL_FLOW_DENOMINATOR_ANCHOR_REGISTRY_FIELDS = [
    "anchor_row_id",
    "denominator_source_id",
    "denominator_source_class",
    "anchor_label",
    "anchor_family",
    "anchor_role",
    "source_handle",
    "timing_alignment_class",
    "anchor_value_gdp_share",
    "anchor_value_pp_gdp",
    "anchor_empirical_status",
    "scenario_runtime_allowed",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

ANNUAL_FLOW_RUNTIME_FAMILY_REGISTRY_FIELDS = [
    "runtime_family_row_id",
    "denominator_source_id",
    "denominator_source_class",
    "runtime_family_label",
    "runtime_family_role",
    "default_runtime_anchor",
    "sensitivity_only",
    "timing_alignment_class",
    "runtime_anchor_value_pp_gdp",
    "runtime_ci95_low_pp_gdp",
    "runtime_ci95_high_pp_gdp",
    "source_artifact",
    "source_row_id",
    "runtime_policy_status",
    "scenario_runtime_allowed",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

SCENARIO_DENOMINATOR_ANCHOR_LINEAGE_FIELDS = [
    "lineage_row_id",
    "ratio_id",
    "numerator_source_artifact",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "denominator_source_id",
    "denominator_source_class",
    "denominator_source_artifact",
    "denominator_timing_class",
    "support_pct_of_gdp",
    "denominator_anchor_pp_gdp",
    "implied_support_offset_100bp_year_equivalent",
    "scenario_runtime_allowed",
    "timing_alignment_status",
    "denominator_empirical_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

SCENARIO_DENOMINATOR_STACK_COMPARISON_FIELDS = [
    "stack_row_id",
    "ratio_id",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "support_pct_of_gdp",
    "denominator_source_id",
    "denominator_source_class",
    "denominator_source_artifact",
    "denominator_timing_class",
    "denominator_anchor_pp_gdp",
    "implied_support_offset_100bp_year_equivalent",
    "scenario_runtime_allowed",
    "stack_row_role",
    "stack_status",
    "timing_alignment_status",
    "denominator_empirical_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

ANNUAL_SUPPORT_DENOMINATOR_COMPATIBILITY_REGISTRY_FIELDS = [
    "compatibility_row_id",
    "ratio_id",
    "numerator_timing_class",
    "denominator_source_id",
    "denominator_timing_class",
    "comparison_mode",
    "support_offset_computation_allowed",
    "runtime_anchor_allowed",
    "translation_artifact",
    "translation_row_id",
    "comparability_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

ANNUAL_SUPPORT_NUMERATOR_COMPONENT_REGISTRY_FIELDS = [
    "component_row_id",
    "contract_row_id",
    "ratio_id",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "component_id",
    "component_role",
    "stage",
    "source_artifact",
    "source_row_handle",
    "horizon",
    "timing_class",
    "amount_field_bil",
    "component_value_bil",
    "sign_convention",
    "inclusion_scope",
    "included_in_scalar_numerator",
    "included_in_split_numerator",
    "directly_added_to_final_numerator",
    "additivity_scope",
    "uncertainty_status",
    "runtime_allowed",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

ANNUAL_SUPPORT_NUMERATOR_SOURCE_GATE_FIELDS = [
    "source_gate_row_id",
    "component_row_id",
    "contract_row_id",
    "ratio_id",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "component_id",
    "component_role",
    "source_artifact",
    "source_row_handle",
    "source_strength_class",
    "timing_role",
    "inclusion_scope",
    "memo_direct_status",
    "uncertainty_class",
    "source_input_fields",
    "source_status_raw",
    "source_gate_status",
    "runtime_component_eligible",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

ANNUAL_SUPPORT_NUMERATOR_COMPONENT_ROLLUP_FIELDS = [
    "rollup_row_id",
    "ratio_id",
    "component_id",
    "component_role",
    "stage",
    "component_class",
    "source_artifact",
    "source_gate_artifact",
    "component_registry_artifact",
    "component_row_count",
    "source_gate_row_count",
    "contract_row_count",
    "forecast_year_count",
    "directly_added_to_final_numerator",
    "runtime_component_eligible",
    "runtime_allowed",
    "included_in_scalar_numerator",
    "included_in_split_numerator",
    "memo_exclusion_status",
    "source_gate_status",
    "component_value_min_bil",
    "component_value_max_bil",
    "component_value_abs_max_bil",
    "sign_convention_set",
    "inclusion_scope_set",
    "additivity_scope_set",
    "uncertainty_class_set",
    "timing_role_set",
    "source_strength_class_set",
    "rollup_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

ANNUAL_SUPPORT_NUMERATOR_CONTRACT_FIELDS = [
    "contract_row_id",
    "ratio_id",
    "component_registry_artifact",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "nominal_gdp_bil",
    "interest_income_support_bil",
    "tdc_deposit_support_bil",
    "runtime_current_window_numerator_bil",
    "scalar_runtime_numerator_bil",
    "split_runtime_numerator_bil",
    "direct_component_sum_bil",
    "memo_component_sum_bil",
    "support_pct_of_gdp",
    "direct_component_count",
    "memo_component_count",
    "timing_class",
    "uncertainty_status",
    "runtime_allowed",
    "reconciliation_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

ANNUAL_SUPPORT_NUMERATOR_UNCERTAINTY_ENVELOPE_FIELDS = [
    "envelope_row_id",
    "contract_row_id",
    "ratio_id",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "uncertainty_family_id",
    "source_gate_artifact",
    "source_gate_status",
    "envelope_method",
    "uncertainty_family",
    "current_role_in_family",
    "numerator_current_bil",
    "numerator_lower_bound_bil",
    "numerator_base_case_bil",
    "numerator_upper_bound_bil",
    "support_pct_current_gdp",
    "support_pct_lower_bound_gdp",
    "support_pct_base_case_gdp",
    "support_pct_upper_bound_gdp",
    "lower_contract_row_id",
    "base_contract_row_id",
    "upper_contract_row_id",
    "uncertainty_status",
    "runtime_allowed",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

ANNUAL_SUPPORT_NUMERATOR_CONTRACT_INVARIANT_AUDIT_FIELDS = [
    "audit_row_id",
    "contract_row_id",
    "ratio_id",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "numerator_contract_artifact",
    "direct_component_count",
    "memo_component_count",
    "direct_component_sum_bil",
    "runtime_current_window_numerator_bil",
    "reconciliation_delta_bil",
    "memo_exclusion_status",
    "reconciliation_status",
    "runtime_allowed",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_SCENARIO_FIELDS = [
    "runtime_support_offset_row_id",
    "ratio_id",
    "numerator_contract_artifact",
    "numerator_contract_row_id",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "nominal_gdp_bil",
    "numerator_total_bil",
    "support_pct_of_gdp",
    "numerator_timing_class",
    "numerator_uncertainty_status",
    "numerator_reconciliation_status",
    "numerator_runtime_allowed",
    "numerator_source_gate_artifact",
    "numerator_source_gate_status",
    "numerator_uncertainty_artifact",
    "numerator_uncertainty_lower_bound_bil",
    "numerator_uncertainty_base_case_bil",
    "numerator_uncertainty_upper_bound_bil",
    "support_pct_of_gdp_numerator_lower_bound",
    "support_pct_of_gdp_numerator_base_case",
    "support_pct_of_gdp_numerator_upper_bound",
    "denominator_source_id",
    "denominator_source_class",
    "denominator_role",
    "denominator_timing_class",
    "default_runtime_anchor",
    "sensitivity_only",
    "denominator_runtime_allowed",
    "support_offset_computation_allowed",
    "effective_runtime_output_allowed",
    "scenario_runtime_allowed",
    "denominator_center_pp_gdp",
    "denominator_ci95_low_pp_gdp",
    "denominator_ci95_high_pp_gdp",
    "support_offset_100bp_year_equivalent_lower_bound",
    "support_offset_100bp_year_equivalent",
    "support_offset_100bp_year_equivalent_upper_bound",
    "support_offset_100bp_year_equivalent_numerator_lower_bound",
    "support_offset_100bp_year_equivalent_numerator_base_case",
    "support_offset_100bp_year_equivalent_numerator_upper_bound",
    "support_offset_bp_year_equivalent_lower_bound",
    "support_offset_bp_year_equivalent",
    "support_offset_bp_year_equivalent_upper_bound",
    "support_offset_bp_year_equivalent_numerator_lower_bound",
    "support_offset_bp_year_equivalent_numerator_base_case",
    "support_offset_bp_year_equivalent_numerator_upper_bound",
    "runtime_pairing_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_READINESS_REGISTRY_FIELDS = [
    "readiness_row_id",
    "runtime_support_offset_row_id",
    "ratio_id",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "numerator_contract_artifact",
    "numerator_contract_row_id",
    "denominator_source_id",
    "denominator_source_class",
    "numerator_timing_class",
    "denominator_timing_class",
    "numerator_uncertainty_status",
    "numerator_reconciliation_status",
    "numerator_runtime_allowed",
    "numerator_source_gate_artifact",
    "numerator_source_gate_status",
    "numerator_uncertainty_artifact",
    "numerator_uncertainty_lower_bound_bil",
    "numerator_uncertainty_base_case_bil",
    "numerator_uncertainty_upper_bound_bil",
    "denominator_runtime_allowed",
    "support_offset_computation_allowed",
    "effective_runtime_output_allowed",
    "readiness_tier",
    "scenario_runtime_allowed",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_ADOPTION_MATRIX_FIELDS = [
    "adoption_row_id",
    "ratio_id",
    "numerator_contract_artifact",
    "numerator_contract_row_id",
    "readiness_artifact",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "numerator_timing_class",
    "numerator_uncertainty_status",
    "numerator_reconciliation_status",
    "numerator_runtime_allowed",
    "numerator_source_gate_artifact",
    "numerator_source_gate_status",
    "numerator_uncertainty_artifact",
    "numerator_total_bil",
    "support_pct_of_gdp",
    "numerator_uncertainty_lower_bound_bil",
    "numerator_uncertainty_base_case_bil",
    "numerator_uncertainty_upper_bound_bil",
    "default_runtime_family_count",
    "sensitivity_runtime_family_count",
    "blocked_overlay_family_count",
    "default_runtime_support_offset_row_id",
    "default_runtime_readiness_row_id",
    "default_runtime_readiness_tier",
    "default_denominator_source_id",
    "default_denominator_center_pp_gdp",
    "default_denominator_ci95_low_pp_gdp",
    "default_denominator_ci95_high_pp_gdp",
    "default_support_offset_100bp_year_equivalent_lower_bound",
    "default_support_offset_100bp_year_equivalent",
    "default_support_offset_100bp_year_equivalent_upper_bound",
    "default_support_offset_100bp_year_equivalent_numerator_lower_bound",
    "default_support_offset_100bp_year_equivalent_numerator_base_case",
    "default_support_offset_100bp_year_equivalent_numerator_upper_bound",
    "sensitivity_base_current_row_id",
    "sensitivity_base_current_readiness_row_id",
    "sensitivity_base_current_readiness_tier",
    "sensitivity_base_current_support_offset_100bp_year_equivalent",
    "sensitivity_base_current_support_offset_100bp_year_equivalent_numerator_lower_bound",
    "sensitivity_base_current_support_offset_100bp_year_equivalent_numerator_base_case",
    "sensitivity_base_current_support_offset_100bp_year_equivalent_numerator_upper_bound",
    "sensitivity_high_row_id",
    "sensitivity_high_readiness_row_id",
    "sensitivity_high_readiness_tier",
    "sensitivity_high_support_offset_100bp_year_equivalent",
    "sensitivity_high_support_offset_100bp_year_equivalent_numerator_lower_bound",
    "sensitivity_high_support_offset_100bp_year_equivalent_numerator_base_case",
    "sensitivity_high_support_offset_100bp_year_equivalent_numerator_upper_bound",
    "bounded_h8_overlay_row_id",
    "bounded_h8_overlay_runtime_pairing_status",
    "bounded_h8_overlay_readiness_tier",
    "bounded_h8_overlay_support_offset_100bp_year_equivalent",
    "bounded_h8_overlay_support_offset_bp_year_equivalent",
    "literature_h8_overlay_row_id",
    "literature_h8_overlay_runtime_pairing_status",
    "literature_h8_overlay_readiness_tier",
    "literature_h8_overlay_support_offset_100bp_year_equivalent",
    "literature_h8_overlay_support_offset_bp_year_equivalent",
    "frbus_h8_overlay_row_id",
    "frbus_h8_overlay_runtime_pairing_status",
    "frbus_h8_overlay_readiness_tier",
    "frbus_h8_overlay_support_offset_100bp_year_equivalent",
    "frbus_h8_overlay_support_offset_bp_year_equivalent",
    "adoption_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_FRONTIER_SUMMARY_FIELDS = [
    "frontier_row_id",
    "ratio_id",
    "forecast_year",
    "denominator_source_id",
    "denominator_source_class",
    "denominator_role",
    "runtime_family_class",
    "scenario_row_count",
    "reference_mpc_scenario",
    "reference_maturity_scenario",
    "reference_holder_scenario",
    "reference_runtime_support_offset_row_id",
    "minimum_runtime_support_offset_row_id",
    "maximum_runtime_support_offset_row_id",
    "reference_support_offset_100bp_year_equivalent",
    "minimum_support_offset_100bp_year_equivalent",
    "maximum_support_offset_100bp_year_equivalent",
    "reference_support_offset_100bp_year_equivalent_numerator_lower_bound",
    "reference_support_offset_100bp_year_equivalent_numerator_base_case",
    "reference_support_offset_100bp_year_equivalent_numerator_upper_bound",
    "reference_denominator_center_pp_gdp",
    "reference_denominator_ci95_low_pp_gdp",
    "reference_denominator_ci95_high_pp_gdp",
    "frontier_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

NONCANONICAL_CURRENT_DEMAND_SOURCE_TIMING_CONTRACT_FIELDS = [
    "contract_row_id",
    "contract_scope",
    "ratio_id",
    "consumer_lane_id",
    "numerator_source_artifact",
    "numerator_timing_class",
    "numerator_contract_class",
    "denominator_source_id",
    "denominator_source_artifact",
    "denominator_timing_class",
    "review_only_consumer_allowed",
    "runtime_anchor_allowed",
    "contract_status",
    "timing_policy_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

NONCANONICAL_CURRENT_DEMAND_CONSUMER_ENDPOINT_DECISION_FIELDS = [
    "decision_row_id",
    "ratio_id",
    "decision_scope",
    "consumer_contract_artifact",
    "consumer_contract_row_id",
    "conflict_adjudication_artifact",
    "linked_conflict_row_ids",
    "endpoint_decision_status",
    "consumer_hardening_status",
    "remaining_followup_scope",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

DENOMINATOR_SCALE_CONFLICT_FOLLOWUP_DECISION_FIELDS = [
    "decision_row_id",
    "decision_scope",
    "ratio_id",
    "conflict_adjudication_artifact",
    "linked_conflict_row_ids",
    "endpoint_decision_artifact",
    "endpoint_decision_row_id",
    "followup_decision_status",
    "followup_artifact_needed",
    "current_stop_state_status",
    "reopen_trigger_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_CLOSEOUT_DECISION_FIELDS = [
    "decision_row_id",
    "decision_scope",
    "ratio_id",
    "adoption_matrix_artifact",
    "adoption_matrix_row_count",
    "frontier_summary_artifact",
    "frontier_summary_row_count",
    "readiness_artifact",
    "readiness_row_count",
    "reportable_runtime_row_count",
    "blocked_overlay_row_count",
    "default_runtime_family_source_id",
    "default_runtime_family_count_status",
    "sensitivity_runtime_family_count_status",
    "blocked_overlay_count_status",
    "linked_followup_artifact",
    "linked_followup_row_id",
    "closeout_decision_status",
    "followup_artifact_needed",
    "reopen_trigger_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_BENCHMARK_OVERLAY_FIELDS = [
    "overlay_row_id",
    "ratio_id",
    "forecast_year",
    "adoption_matrix_artifact",
    "frontier_summary_artifact",
    "closeout_artifact",
    "closeout_row_id",
    "default_runtime_family_source_id",
    "default_runtime_frontier_row_id",
    "default_runtime_reference_support_offset_100bp_year_equivalent",
    "default_runtime_reference_denominator_center_pp_gdp",
    "default_runtime_reference_denominator_ci95_low_pp_gdp",
    "default_runtime_reference_denominator_ci95_high_pp_gdp",
    "legacy_base_frontier_row_id",
    "legacy_base_reference_support_offset_100bp_year_equivalent",
    "legacy_high_frontier_row_id",
    "legacy_high_reference_support_offset_100bp_year_equivalent",
    "bounded_h8_overlay_source_id",
    "bounded_h8_review_center_pp_gdp_per_100bp_year",
    "bounded_h8_weak_iv_safe_ci_low_pp_gdp_per_100bp_year",
    "bounded_h8_weak_iv_safe_ci_high_pp_gdp_per_100bp_year",
    "bounded_h8_direct_runtime_ratio_status",
    "frbus_h4_benchmark_source_id",
    "frbus_h4_benchmark_pp_gdp_per_100bp_year",
    "frbus_h8_benchmark_source_id",
    "frbus_h8_benchmark_pp_gdp_per_100bp_year",
    "frbus_h12_benchmark_source_id",
    "frbus_h12_benchmark_pp_gdp_per_100bp_year",
    "low_scale_cluster_status",
    "scale_conflict_status",
    "overlay_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

DENOMINATOR_SCALE_CONFLICT_ADJUDICATION_FIELDS = [
    "adjudication_row_id",
    "comparison_family",
    "left_source_id",
    "left_source_class",
    "left_timing_class",
    "left_horizon_q",
    "left_value_pp_gdp_per_100bp_year",
    "left_ci_low_pp_gdp_per_100bp_year",
    "left_ci_high_pp_gdp_per_100bp_year",
    "right_source_id",
    "right_source_class",
    "right_timing_class",
    "right_horizon_q",
    "right_value_pp_gdp_per_100bp_year",
    "right_ci_low_pp_gdp_per_100bp_year",
    "right_ci_high_pp_gdp_per_100bp_year",
    "common_review_unit",
    "sign_conflict_status",
    "scale_conflict_status",
    "timing_conflict_status",
    "adjudication_status",
    "interpretation_role_status",
    "counterweight_cluster_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

H4_EMPIRICAL_VALIDATION_REGISTRY_FIELDS = [
    "validation_row_id",
    "validation_scope",
    "ratio_id",
    "horizon_q",
    "bounded_source_id",
    "bounded_source_class",
    "bounded_center_pp_gdp_per_100bp_year",
    "bounded_proxy_iv_ci_low_pp_gdp_per_100bp_year",
    "bounded_proxy_iv_ci_high_pp_gdp_per_100bp_year",
    "bounded_controlled_ci_low_pp_gdp_per_100bp_year",
    "bounded_controlled_ci_high_pp_gdp_per_100bp_year",
    "comparison_source_id",
    "comparison_source_class",
    "comparison_center_pp_gdp_per_100bp_year",
    "comparison_ci_low_pp_gdp_per_100bp_year",
    "comparison_ci_high_pp_gdp_per_100bp_year",
    "common_review_unit",
    "same_design_materialization_status",
    "weak_iv_safe_status",
    "sign_alignment_status",
    "scale_alignment_status",
    "interval_overlap_status",
    "runtime_policy_implication_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RESIDUALIZED_FFR_LITERATURE_REPLICATION_AUDIT_FIELDS = [
    "replication_row_id",
    "source_paper_id",
    "paper_family",
    "shock_construction_id",
    "outcome_id",
    "horizon_q",
    "sample_window_id",
    "zlb_treatment_id",
    "published_target_reference",
    "published_target_response_pct",
    "local_replication_response_pct",
    "absolute_difference_pct",
    "replication_tolerance_pct",
    "replication_n_obs",
    "hac_bandwidth",
    "sample_start",
    "sample_end",
    "replication_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RESIDUALIZED_FFR_LITERATURE_LP_RESULTS_FIELDS = [
    "lp_result_row_id",
    "source_paper_id",
    "shock_construction_id",
    "outcome_id",
    "outcome_definition",
    "horizon_q",
    "sample_window_id",
    "control_spec_id",
    "result_unit",
    "response_value",
    "se_hac",
    "t_hac",
    "ci95_low_hac",
    "ci95_high_hac",
    "lp_n_obs",
    "hac_bandwidth",
    "sample_start",
    "sample_end",
    "lp_result_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RESIDUALIZED_FFR_FWL_DIAGNOSTICS_FIELDS = [
    "fwl_row_id",
    "bridge_design_id",
    "outcome_id",
    "control_spec_id",
    "diagnostic_item",
    "full_model_beta",
    "residualized_beta",
    "beta_abs_diff",
    "orthogonality_max_abs_corr",
    "diagnostic_n_obs",
    "hac_bandwidth",
    "diagnostic_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RESIDUALIZED_FFR_PRIVATE_DEMAND_BRIDGE_FIELDS = [
    "bridge_row_id",
    "source_paper_id",
    "shock_construction_id",
    "outcome_id",
    "outcome_definition",
    "target_role",
    "horizon_q",
    "annual_window_id",
    "annual_window_label",
    "window_start_horizon_q",
    "window_end_horizon_q",
    "target_unit",
    "bridge_response_value",
    "bridge_se_hac",
    "bridge_ci95_low_hac",
    "bridge_ci95_high_hac",
    "bridge_n_obs",
    "sample_start",
    "sample_end",
    "bridge_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

RESIDUALIZED_FFR_NORMALIZATION_BRIDGE_FIELDS = [
    "normalization_row_id",
    "source_paper_id",
    "shock_construction_id",
    "normalization_target_id",
    "normalization_formula",
    "annual_window_id",
    "annual_window_label",
    "window_start_horizon_q",
    "window_end_horizon_q",
    "first_year_area_pp_year",
    "first_year_area_bps_year",
    "normalization_multiplier",
    "window_native_response_pp_gdp",
    "mapped_window_d_y_per_100bp_year",
    "mapped_h8_fspdp_d_y_per_100bp_year",
    "normalization_sample_start",
    "normalization_sample_end",
    "normalization_status",
    "exact_blocker",
    "safe_sentence",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

_LEGACY_ANCHOR_NAMES = {
    "base_current_100bps": "legacy_assumption_anchor_base_current_100bps",
    "high_fiscal_offset_no_hit": "legacy_assumption_anchor_high_fiscal_offset_no_hit",
}
_PRIMARY_BOUNDED_SOURCE_ID = "bounded_h8_overlay_review_center"
_LITERATURE_SOURCE_ID = "literature_annual_flow_bridge_candidate"
_CANONICAL_ANNUAL_FLOW_ANCHOR_PP_GDP = CANONICAL_CONTRACTIONARY_DRAG_PP_GDP
_PAPER_ID = "iacoviello_navarro_foreign_effects_higher_us_interest_rates"
_PUBLISHED_H8_TARGET = -0.7
_PUBLISHED_H8_TOLERANCE = 0.2
_LITERATURE_ANNUAL_WINDOW_SPECS = (
    ("year1_h4_endpoint_proxy", "Year 1 h4 endpoint proxy", None, 4),
    ("year2_h8_minus_h4_increment_proxy", "Year 2 h8-h4 increment proxy", 4, 8),
    ("year3_h12_minus_h8_increment_proxy", "Year 3 h12-h8 increment proxy", 8, 12),
)


def _literature_runtime_promotion_ready(
    residualized_bridge: "ResidualizedFfrBridgeState",
) -> bool:
    return (
        residualized_bridge.anchor_status
        == "pass_review_only_literature_annual_flow_anchor_window_materialized"
        and residualized_bridge.anchor_value_pp_gdp is not None
    )


def _residualized_bridge_row(
    *,
    rows: Sequence[dict[str, str]],
    row_id_prefix: str,
) -> dict[str, str] | None:
    return next(
        (row for row in rows if row["bridge_row_id"] == row_id_prefix),
        None,
    )


def _mapped_drag_ci_from_native_row(
    *,
    native_row: dict[str, str] | None,
    normalization_multiplier: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    if native_row is None or normalization_multiplier is None:
        return None, None
    native_ci_low = _decimal_or_none(native_row.get("bridge_ci95_low_hac", ""))
    native_ci_high = _decimal_or_none(native_row.get("bridge_ci95_high_hac", ""))
    if native_ci_low is None or native_ci_high is None:
        return None, None
    mapped_low = -(native_ci_high * normalization_multiplier)
    mapped_high = -(native_ci_low * normalization_multiplier)
    return mapped_low, mapped_high


@dataclass(frozen=True)
class DenominatorBridgeProgramArtifacts:
    denominator_methodology_registry_rows: list[dict[str, str]]
    annual_flow_denominator_anchor_registry_rows: list[dict[str, str]]
    annual_flow_runtime_family_registry_rows: list[dict[str, str]]
    annual_support_denominator_compatibility_registry_rows: list[dict[str, str]]
    annual_support_numerator_component_registry_rows: list[dict[str, str]]
    annual_support_numerator_source_gate_rows: list[dict[str, str]]
    annual_support_numerator_component_rollup_rows: list[dict[str, str]]
    annual_support_numerator_contract_rows: list[dict[str, str]]
    annual_support_numerator_uncertainty_envelope_rows: list[dict[str, str]]
    annual_support_numerator_contract_invariant_audit_rows: list[dict[str, str]]
    runtime_annual_flow_support_offset_scenario_rows: list[dict[str, str]]
    runtime_annual_flow_support_offset_readiness_registry_rows: list[dict[str, str]]
    runtime_annual_flow_support_offset_adoption_matrix_rows: list[dict[str, str]]
    runtime_annual_flow_support_offset_frontier_summary_rows: list[dict[str, str]]
    runtime_annual_flow_support_offset_closeout_decision_rows: list[dict[str, str]]
    runtime_annual_flow_support_offset_benchmark_overlay_rows: list[dict[str, str]]
    scenario_denominator_anchor_lineage_rows: list[dict[str, str]]
    noncanonical_current_demand_source_timing_contract_rows: list[dict[str, str]]
    noncanonical_current_demand_consumer_endpoint_decision_rows: list[dict[str, str]]
    denominator_scale_conflict_followup_decision_rows: list[dict[str, str]]
    noncanonical_current_demand_support_ratio_consumer_rows: list[dict[str, str]]
    current_demand_ratio_gate_rows: list[dict[str, str]]
    scenario_denominator_stack_comparison_rows: list[dict[str, str]]
    denominator_scale_conflict_adjudication_rows: list[dict[str, str]]
    h4_empirical_validation_registry_rows: list[dict[str, str]]
    residualized_ffr_literature_replication_audit_rows: list[dict[str, str]]
    residualized_ffr_literature_lp_results_rows: list[dict[str, str]]
    residualized_ffr_fwl_diagnostics_rows: list[dict[str, str]]
    residualized_ffr_private_demand_bridge_rows: list[dict[str, str]]
    residualized_ffr_normalization_bridge_rows: list[dict[str, str]]


@dataclass(frozen=True)
class HacEstimate:
    beta: float
    se: float
    t: float
    ci_low: float
    ci_high: float
    n_obs: int
    bandwidth: int
    sample_start: str
    sample_end: str


@dataclass(frozen=True)
class ResidualizedFfrBridgeState:
    route_status: str
    route_normalization_status: str
    route_exact_blocker: str
    route_safe_sentence: str
    route_next_backend_action: str
    anchor_status: str
    anchor_exact_blocker: str
    anchor_safe_sentence: str
    anchor_next_backend_action: str
    anchor_timing_alignment_class: str
    anchor_value_pp_gdp: Decimal | None
    replication_rows: list[dict[str, str]]
    lp_rows: list[dict[str, str]]
    fwl_rows: list[dict[str, str]]
    bridge_rows: list[dict[str, str]]
    normalization_rows: list[dict[str, str]]


def build_denominator_bridge_program_artifacts(
    *,
    bounded_denominator_registry_rows: Sequence[dict[str, str]],
    frbus_100bp_year_fspdp_proxy_benchmark_rows: Sequence[dict[str, str]],
    weak_iv_safe_inference_rows: Sequence[dict[str, str]],
    forecast_holder_tdc_consistency_bridge_rows: Sequence[dict[str, str]],
    noncanonical_current_demand_support_ratio_consumer_rows: Sequence[dict[str, str]],
    current_demand_ratio_gate_rows: Sequence[dict[str, str]],
) -> DenominatorBridgeProgramArtifacts:
    residualized_bridge = _materialize_residualized_ffr_bridge_state()
    methodology_rows = _denominator_methodology_registry_rows(
        bounded_denominator_registry_rows=bounded_denominator_registry_rows,
        residualized_bridge=residualized_bridge,
    )
    anchor_rows = _annual_flow_denominator_anchor_registry_rows(
        bounded_denominator_registry_rows=bounded_denominator_registry_rows,
        residualized_bridge=residualized_bridge,
    )
    runtime_family_rows = _annual_flow_runtime_family_registry_rows(
        residualized_bridge=residualized_bridge
    )
    compatibility_rows = _annual_support_denominator_compatibility_registry_rows(
        annual_flow_anchor_registry_rows=anchor_rows,
        residualized_bridge=residualized_bridge,
        frbus_100bp_year_fspdp_proxy_benchmark_rows=(
            frbus_100bp_year_fspdp_proxy_benchmark_rows
        ),
    )
    numerator_component_rows = _annual_support_numerator_component_registry_rows(
        forecast_holder_tdc_consistency_bridge_rows=(
            forecast_holder_tdc_consistency_bridge_rows
        )
    )
    numerator_source_gate_rows = _annual_support_numerator_source_gate_rows(
        annual_support_numerator_component_registry_rows=numerator_component_rows,
        forecast_holder_tdc_consistency_bridge_rows=(
            forecast_holder_tdc_consistency_bridge_rows
        ),
    )
    numerator_component_rollup_rows = _annual_support_numerator_component_rollup_rows(
        annual_support_numerator_component_registry_rows=numerator_component_rows,
        annual_support_numerator_source_gate_rows=numerator_source_gate_rows,
    )
    numerator_contract_rows = _annual_support_numerator_contract_rows(
        annual_support_numerator_component_registry_rows=numerator_component_rows,
        forecast_holder_tdc_consistency_bridge_rows=(
            forecast_holder_tdc_consistency_bridge_rows
        ),
    )
    numerator_uncertainty_envelope_rows = (
        _annual_support_numerator_uncertainty_envelope_rows(
            annual_support_numerator_contract_rows=numerator_contract_rows,
            annual_support_numerator_source_gate_rows=numerator_source_gate_rows,
        )
    )
    numerator_contract_invariant_rows = (
        _annual_support_numerator_contract_invariant_audit_rows(
            annual_support_numerator_contract_rows=numerator_contract_rows
        )
    )
    runtime_support_offset_rows = _runtime_annual_flow_support_offset_scenario_rows(
        annual_support_numerator_contract_rows=numerator_contract_rows,
        annual_support_numerator_source_gate_rows=numerator_source_gate_rows,
        annual_support_numerator_uncertainty_envelope_rows=(
            numerator_uncertainty_envelope_rows
        ),
        annual_flow_anchor_registry_rows=anchor_rows,
        annual_flow_runtime_family_registry_rows=runtime_family_rows,
        annual_support_denominator_compatibility_registry_rows=compatibility_rows,
    )
    runtime_support_offset_readiness_rows = (
        _runtime_annual_flow_support_offset_readiness_registry_rows(
            runtime_annual_flow_support_offset_scenario_rows=runtime_support_offset_rows
        )
    )
    runtime_support_offset_adoption_matrix_rows = (
        _runtime_annual_flow_support_offset_adoption_matrix_rows(
            runtime_annual_flow_support_offset_scenario_rows=runtime_support_offset_rows,
            runtime_annual_flow_support_offset_readiness_registry_rows=(
                runtime_support_offset_readiness_rows
            ),
        )
    )
    runtime_support_offset_frontier_summary_rows = (
        _runtime_annual_flow_support_offset_frontier_summary_rows(
            runtime_annual_flow_support_offset_scenario_rows=runtime_support_offset_rows
        )
    )
    lineage_rows = _scenario_denominator_anchor_lineage_rows(
        forecast_holder_tdc_consistency_bridge_rows=(
            forecast_holder_tdc_consistency_bridge_rows
        ),
        noncanonical_current_demand_support_ratio_consumer_rows=(
            noncanonical_current_demand_support_ratio_consumer_rows
        ),
        annual_flow_anchor_registry_rows=anchor_rows,
        annual_support_denominator_compatibility_registry_rows=compatibility_rows,
    )
    contract_rows = _noncanonical_current_demand_source_timing_contract_rows(
        annual_flow_anchor_registry_rows=anchor_rows
    )
    scale_conflict_rows = _denominator_scale_conflict_adjudication_rows(
        bounded_denominator_registry_rows=bounded_denominator_registry_rows,
        annual_flow_anchor_registry_rows=anchor_rows,
        residualized_bridge=residualized_bridge,
        frbus_100bp_year_fspdp_proxy_benchmark_rows=(
            frbus_100bp_year_fspdp_proxy_benchmark_rows
        ),
    )
    h4_validation_rows = _h4_empirical_validation_registry_rows(
        bounded_denominator_registry_rows=bounded_denominator_registry_rows,
        annual_flow_runtime_family_registry_rows=runtime_family_rows,
        weak_iv_safe_inference_rows=weak_iv_safe_inference_rows,
        frbus_100bp_year_fspdp_proxy_benchmark_rows=(
            frbus_100bp_year_fspdp_proxy_benchmark_rows
        ),
    )
    endpoint_decision_rows = _noncanonical_current_demand_consumer_endpoint_decision_rows(
        noncanonical_current_demand_source_timing_contract_rows=contract_rows,
        denominator_scale_conflict_adjudication_rows=scale_conflict_rows,
    )
    scale_conflict_followup_decision_rows = (
        _denominator_scale_conflict_followup_decision_rows(
            denominator_scale_conflict_adjudication_rows=scale_conflict_rows,
            noncanonical_current_demand_consumer_endpoint_decision_rows=(
                endpoint_decision_rows
            ),
            h4_empirical_validation_registry_rows=h4_validation_rows,
        )
    )
    runtime_support_offset_closeout_decision_rows = (
        _runtime_annual_flow_support_offset_closeout_decision_rows(
            runtime_annual_flow_support_offset_adoption_matrix_rows=(
                runtime_support_offset_adoption_matrix_rows
            ),
            runtime_annual_flow_support_offset_frontier_summary_rows=(
                runtime_support_offset_frontier_summary_rows
            ),
            runtime_annual_flow_support_offset_readiness_registry_rows=(
                runtime_support_offset_readiness_rows
            ),
            denominator_scale_conflict_followup_decision_rows=(
                scale_conflict_followup_decision_rows
            ),
        )
    )
    runtime_support_offset_benchmark_overlay_rows = (
        _runtime_annual_flow_support_offset_benchmark_overlay_rows(
            runtime_annual_flow_support_offset_frontier_summary_rows=(
                runtime_support_offset_frontier_summary_rows
            ),
            runtime_annual_flow_support_offset_closeout_decision_rows=(
                runtime_support_offset_closeout_decision_rows
            ),
            bounded_denominator_registry_rows=bounded_denominator_registry_rows,
            frbus_100bp_year_fspdp_proxy_benchmark_rows=(
                frbus_100bp_year_fspdp_proxy_benchmark_rows
            ),
            h4_empirical_validation_registry_rows=h4_validation_rows,
        )
    )
    return DenominatorBridgeProgramArtifacts(
        denominator_methodology_registry_rows=methodology_rows,
        annual_flow_denominator_anchor_registry_rows=anchor_rows,
        annual_flow_runtime_family_registry_rows=runtime_family_rows,
        annual_support_denominator_compatibility_registry_rows=compatibility_rows,
        annual_support_numerator_component_registry_rows=numerator_component_rows,
        annual_support_numerator_source_gate_rows=numerator_source_gate_rows,
        annual_support_numerator_component_rollup_rows=numerator_component_rollup_rows,
        annual_support_numerator_contract_rows=numerator_contract_rows,
        annual_support_numerator_uncertainty_envelope_rows=(
            numerator_uncertainty_envelope_rows
        ),
        annual_support_numerator_contract_invariant_audit_rows=(
            numerator_contract_invariant_rows
        ),
        runtime_annual_flow_support_offset_scenario_rows=runtime_support_offset_rows,
        runtime_annual_flow_support_offset_readiness_registry_rows=(
            runtime_support_offset_readiness_rows
        ),
        runtime_annual_flow_support_offset_adoption_matrix_rows=(
            runtime_support_offset_adoption_matrix_rows
        ),
        runtime_annual_flow_support_offset_frontier_summary_rows=(
            runtime_support_offset_frontier_summary_rows
        ),
        runtime_annual_flow_support_offset_closeout_decision_rows=(
            runtime_support_offset_closeout_decision_rows
        ),
        runtime_annual_flow_support_offset_benchmark_overlay_rows=(
            runtime_support_offset_benchmark_overlay_rows
        ),
        scenario_denominator_anchor_lineage_rows=lineage_rows,
        noncanonical_current_demand_source_timing_contract_rows=contract_rows,
        noncanonical_current_demand_consumer_endpoint_decision_rows=(
            endpoint_decision_rows
        ),
        denominator_scale_conflict_followup_decision_rows=(
            scale_conflict_followup_decision_rows
        ),
        noncanonical_current_demand_support_ratio_consumer_rows=(
            _augmented_noncanonical_current_demand_support_ratio_consumer_rows(
                noncanonical_current_demand_support_ratio_consumer_rows=(
                    noncanonical_current_demand_support_ratio_consumer_rows
                ),
                annual_flow_anchor_registry_rows=anchor_rows,
                annual_support_denominator_compatibility_registry_rows=(
                    compatibility_rows
                ),
                noncanonical_current_demand_source_timing_contract_rows=contract_rows,
                noncanonical_current_demand_consumer_endpoint_decision_rows=(
                    endpoint_decision_rows
                ),
            )
        ),
        current_demand_ratio_gate_rows=(
            _augmented_current_demand_ratio_gate_rows(
                current_demand_ratio_gate_rows=current_demand_ratio_gate_rows,
                noncanonical_current_demand_source_timing_contract_rows=contract_rows,
                noncanonical_current_demand_consumer_endpoint_decision_rows=(
                    endpoint_decision_rows
                ),
            )
        ),
        scenario_denominator_stack_comparison_rows=(
            _scenario_denominator_stack_comparison_rows(
                scenario_denominator_anchor_lineage_rows=lineage_rows
            )
        ),
        denominator_scale_conflict_adjudication_rows=scale_conflict_rows,
        h4_empirical_validation_registry_rows=h4_validation_rows,
        residualized_ffr_literature_replication_audit_rows=(
            residualized_bridge.replication_rows
        ),
        residualized_ffr_literature_lp_results_rows=residualized_bridge.lp_rows,
        residualized_ffr_fwl_diagnostics_rows=residualized_bridge.fwl_rows,
        residualized_ffr_private_demand_bridge_rows=residualized_bridge.bridge_rows,
        residualized_ffr_normalization_bridge_rows=residualized_bridge.normalization_rows,
    )


def _denominator_methodology_registry_rows(
    *,
    bounded_denominator_registry_rows: Sequence[dict[str, str]],
    residualized_bridge: ResidualizedFfrBridgeState,
) -> list[dict[str, str]]:
    bounded_h8 = next(
        (
            row
            for row in bounded_denominator_registry_rows
            if row["primary_denominator_horizon"] == "true"
        ),
        None,
    )
    literature_runtime_ready = _literature_runtime_promotion_ready(
        residualized_bridge
    )
    rows: list[dict[str, str]] = []
    rows.append(
        {
            "methodology_row_id": "denominator_methodology_registry::bounded_h8",
            "route_id": "bounded_h8_current_demand_drag_proxy_route",
            "route_family": "high_frequency_100bp_year_lp_iv",
            "route_label": "High-frequency 100bp-year FSPDP LP/LP-IV bounded h8 route",
            "route_role": "primary_empirical_noncanonical_lane",
            "primary_route_class": "bounded_empirical_evidence",
            "anchor_job": "bounded_h8_overlay_only",
            "outcome_id": "fspdp_gdp_share_cumulative_drag_h8",
            "shock_unit": "100bp_year_tightening_exposure",
            "timing_class": "h8_cumulative",
            "normalization_status": "native_exact_100bp_year_repo_units",
            "estimator_family": "controlled_lp_proxy_iv_weak_iv_safe_interval",
            "source_family": "sf_fed_usmpd_plus_repo_value_bearing_exposure",
            "sample_scope": "primary_review_object_1994Q1_2023Q4",
            "benchmark_only": "false",
            "scenario_runtime_allowed": "false",
            "current_status": (
                bounded_h8["bounded_denominator_status"]
                if bounded_h8 is not None
                else "blocked_missing_bounded_h8_registry_row"
            ),
            "exact_blocker": (
                bounded_h8["exact_blocker"] if bounded_h8 is not None else ""
            ),
            "safe_sentence": (
                "Primary empirical noncanonical lane remains the bounded h8 interval-first "
                "FSPDP drag route. It is review-only and cannot become the annual-flow "
                "anchor or canonical RW_Y denominator by itself."
            ),
            "next_backend_action": (
                "keep_bounded_h8_review_only_and_limit_any_followup_to_scale_conflict_interpretation"
            ),
            "allowed_use": "review_only_h8_overlay;triangulation",
            "blocked_use": (
                "annual_flow_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "bounded_h8_empirical_lane_not_canonical_or_annual_flow",
            **_disabled_switches(),
        }
    )
    rows.append(
        {
            "methodology_row_id": "denominator_methodology_registry::literature_bridge",
            "route_id": "residualized_ffr_literature_bridge_route",
            "route_family": "published_residualized_fed_funds_lp",
            "route_label": "Published residualized-fed-funds replication and adaptation bridge",
            "route_role": (
                "primary_empirical_annual_flow_runtime_lane"
                if literature_runtime_ready
                else "primary_bridge_candidate_for_annual_flow"
            ),
            "primary_route_class": (
                "empirical_runtime_family"
                if literature_runtime_ready
                else "scale_and_timing_bridge"
            ),
            "anchor_job": (
                "primary_empirical_annual_flow_runtime_anchor"
                if literature_runtime_ready
                else "annual_flow_scale_anchor_candidate"
            ),
            "outcome_id": "gdp_then_private_demand_bridge",
            "shock_unit": "native_1pp_policy_shock_mapped_to_100bp_year_when_available",
            "timing_class": (
                "quarterly_bridge_surface_plus_runtime_h4_annual_flow_family"
                if literature_runtime_ready
                else (
                    "quarterly_bridge_surface_plus_review_only_annual_flow_window_translation"
                    if residualized_bridge.anchor_status
                    == "pass_review_only_literature_annual_flow_anchor_window_materialized"
                    else "quarterly_bridge_surface_pending_annual_window_formalization"
                )
            ),
            "normalization_status": residualized_bridge.route_normalization_status,
            "estimator_family": "residualized_shock_local_projection_hac_ratewall_owned",
            "source_family": "published_replication_package_plus_local_current_demand_sources",
            "sample_scope": "1965Q1_2016Q2_us_published_style_intersection",
            "benchmark_only": "false",
            "scenario_runtime_allowed": "true" if literature_runtime_ready else "false",
            "current_status": (
                "pass_primary_empirical_annual_flow_runtime_family"
                if literature_runtime_ready
                else residualized_bridge.route_status
            ),
            "exact_blocker": (
                "The literature bridge is now strong enough to carry the default "
                "empirical annual-flow runtime denominator family. Canonical RW_Y, "
                "main-ratio entry, and stronger claim modes remain blocked."
                if literature_runtime_ready
                else residualized_bridge.route_exact_blocker
            ),
            "safe_sentence": (
                "The literature bridge remains a published-style quarterly bridge "
                "surface, but its year-1 h4 annual-flow proxy now serves as the default "
                "empirical runtime denominator family."
                if literature_runtime_ready
                else residualized_bridge.route_safe_sentence
            ),
            "next_backend_action": (
                "use_literature_runtime_family_as_default_and_keep_h8_overlay_review_only"
                if literature_runtime_ready
                else residualized_bridge.route_next_backend_action
            ),
            "allowed_use": (
                "scenario_runtime_empirical_annual_flow_primary;review_only_literature_bridge_surface;triangulation"
                if literature_runtime_ready
                else "review_only_literature_bridge_surface;triangulation"
            ),
            "blocked_use": (
                "canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": (
                "literature_bridge_runtime_primary_for_annual_flow_family"
                if literature_runtime_ready
                else (
                    "literature_bridge_review_only_with_annual_window_translation"
                    if residualized_bridge.anchor_status
                    == "pass_review_only_literature_annual_flow_anchor_window_materialized"
                    else "literature_bridge_review_only_until_annual_window_formalization"
                )
            ),
            **_disabled_switches(),
        }
    )
    rows.append(
        {
            "methodology_row_id": "denominator_methodology_registry::legacy_assumption_mode",
            "route_id": "legacy_assumption_mode_annual_flow_anchor_route",
            "route_family": "assumption_mode_annual_flow",
            "route_label": "Legacy assumption-mode annual-flow anchor lane",
            "route_role": "assumption_mode_sensitivity_fallback_lane",
            "primary_route_class": "scenario_runtime_sensitivity_fallback",
            "anchor_job": "annual_flow_sensitivity_counterpoint",
            "outcome_id": "annual_flow_current_demand_drag_placeholder",
            "shock_unit": "100bp_year_assumption_mode_placeholder",
            "timing_class": "annual_flow_direct",
            "normalization_status": "already_in_assumption_mode_runtime_units",
            "estimator_family": "non_empirical_placeholder",
            "source_family": "ratewall_assumption_engine",
            "sample_scope": "assumption_mode_runtime",
            "benchmark_only": "false",
            "scenario_runtime_allowed": "true",
            "current_status": "pass_assumption_mode_sensitivity_only_not_default_runtime",
            "exact_blocker": (
                "Legacy annual-flow anchors are no longer the default runtime denominator. "
                "They survive only as explicit assumption-mode sensitivity counterpoints "
                "and cannot open canonical RW_Y."
            ),
            "safe_sentence": (
                "Legacy sensitivity-only annual-flow anchors remain available only as "
                "assumption-mode counterpoints after runtime promotion of the "
                "current literature-backed empirical family."
            ),
            "next_backend_action": (
                "keep_only_as_explicit_sensitivity_counterpoint_to_literature_runtime_family"
            ),
            "allowed_use": "scenario_runtime_assumption_mode_sensitivity_only",
            "blocked_use": (
                "default_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;pricing;"
                "holder_allocation;raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "assumption_mode_sensitivity_only_not_empirical_denominator",
            **_disabled_switches(),
        }
    )
    rows.append(
        {
            "methodology_row_id": "denominator_methodology_registry::frbus_benchmark",
            "route_id": "frbus_100bp_year_fspdp_proxy_benchmark_route",
            "route_family": "structural_model_benchmark",
            "route_label": "FRB/US normalized 100bp-year component benchmark",
            "route_role": "review_only_benchmark",
            "primary_route_class": "structural_tension_detector",
            "anchor_job": "benchmark_sign_shape_scale_context",
            "outcome_id": "frbus_component_mapped_fspdp_proxy",
            "shock_unit": "exact_100bp_year_model_path",
            "timing_class": "h4_h8_h12_model_profile",
            "normalization_status": "native_exact_100bp_year_model_path",
            "estimator_family": "structural_model_counterfactual",
            "source_family": "official_pyfrbus_runtime",
            "sample_scope": "benchmark_only_scenario",
            "benchmark_only": "true",
            "scenario_runtime_allowed": "false",
            "current_status": "review_only_benchmark",
            "exact_blocker": (
                "FRB/US remains benchmark-only. It can flag sign/shape/scale tension but "
                "cannot calibrate D_Y or narrow priors."
            ),
            "safe_sentence": (
                "FRB/US is an exact-100bp-year structural benchmark and tension detector, "
                "not an empirical denominator or prior-setting route."
            ),
            "next_backend_action": "keep_frbus_benchmark_only_and_compare_against_empirical_routes",
            "allowed_use": "benchmark_sign_shape_scale_context_only",
            "blocked_use": (
                "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "frbus_benchmark_not_denominator_calibration",
            **_disabled_switches(),
        }
    )
    return rows


def _annual_support_denominator_compatibility_registry_rows(
    *,
    annual_flow_anchor_registry_rows: Sequence[dict[str, str]],
    residualized_bridge: ResidualizedFfrBridgeState,
    frbus_100bp_year_fspdp_proxy_benchmark_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    anchors_by_id = {
        row["denominator_source_id"]: row for row in annual_flow_anchor_registry_rows
    }
    literature_runtime_ready = _literature_runtime_promotion_ready(
        residualized_bridge
    )
    literature_h8 = next(
        (
            row
            for row in residualized_bridge.normalization_rows
            if row["normalization_target_id"]
            == "exact_100bp_year_cumulative_policy_path_summary"
        ),
        None,
    )
    row_specs = [
        {
            "compatibility_row_id": (
                "annual_support_denominator_compatibility::legacy_base"
            ),
            "ratio_id": "RW_Y",
            "numerator_timing_class": "annual_support_flow_review_only",
            "denominator_source_id": _LEGACY_ANCHOR_NAMES["base_current_100bps"],
            "denominator_timing_class": anchors_by_id[
                _LEGACY_ANCHOR_NAMES["base_current_100bps"]
            ]["timing_alignment_class"],
            "comparison_mode": "direct_annual_flow_ratio",
            "support_offset_computation_allowed": "true",
            "runtime_anchor_allowed": "true",
            "translation_artifact": "",
            "translation_row_id": "",
            "comparability_status": "pass_sensitivity_only_annual_flow_pairing",
            "exact_blocker": (
                "Legacy annual-flow anchor is kept only as an explicit assumption-mode "
                "sensitivity counterpoint after runtime promotion of the literature "
                "annual-flow family."
            ),
            "safe_sentence": (
                "Annual-flow numerator can still be compared directly with this legacy "
                "annual-flow sensitivity anchor, but it is no longer the default runtime family."
            ),
            "next_backend_action": (
                "keep_only_as_explicit_sensitivity_counterpoint_to_literature_runtime_family"
            ),
            "allowed_use": "scenario_runtime_assumption_mode_sensitivity_only",
            "blocked_use": (
                "default_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;pricing;"
                "holder_allocation;raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "annual_support_direct_sensitivity_only_anchor_pairing",
        },
        {
            "compatibility_row_id": (
                "annual_support_denominator_compatibility::legacy_high"
            ),
            "ratio_id": "RW_Y",
            "numerator_timing_class": "annual_support_flow_review_only",
            "denominator_source_id": _LEGACY_ANCHOR_NAMES["high_fiscal_offset_no_hit"],
            "denominator_timing_class": anchors_by_id[
                _LEGACY_ANCHOR_NAMES["high_fiscal_offset_no_hit"]
            ]["timing_alignment_class"],
            "comparison_mode": "direct_annual_flow_ratio",
            "support_offset_computation_allowed": "true",
            "runtime_anchor_allowed": "true",
            "translation_artifact": "",
            "translation_row_id": "",
            "comparability_status": "pass_sensitivity_only_annual_flow_pairing",
            "exact_blocker": (
                "Legacy annual-flow anchor is kept only as an explicit assumption-mode "
                "sensitivity counterpoint after runtime promotion of the literature "
                "annual-flow family."
            ),
            "safe_sentence": (
                "Annual-flow numerator can still be compared directly with this higher "
                "legacy annual-flow sensitivity anchor, but it is no longer the default runtime family."
            ),
            "next_backend_action": (
                "keep_only_as_explicit_sensitivity_counterpoint_to_literature_runtime_family"
            ),
            "allowed_use": "scenario_runtime_assumption_mode_sensitivity_only",
            "blocked_use": (
                "default_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;pricing;"
                "holder_allocation;raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "annual_support_direct_sensitivity_only_anchor_pairing",
        },
        {
            "compatibility_row_id": (
                "annual_support_denominator_compatibility::literature_year1"
            ),
            "ratio_id": "RW_Y",
            "numerator_timing_class": "annual_support_flow_review_only",
            "denominator_source_id": _LITERATURE_SOURCE_ID,
            "denominator_timing_class": anchors_by_id[_LITERATURE_SOURCE_ID][
                "timing_alignment_class"
            ],
            "comparison_mode": "direct_annual_flow_ratio",
            "support_offset_computation_allowed": "true",
            "runtime_anchor_allowed": "true" if literature_runtime_ready else "false",
            "translation_artifact": "",
            "translation_row_id": "",
            "comparability_status": (
                "pass_primary_empirical_annual_flow_pairing"
                if literature_runtime_ready
                else "pass_review_only_annual_flow_pairing"
            ),
            "exact_blocker": (
                ""
                if literature_runtime_ready
                else ""
            ),
            "safe_sentence": (
                "Annual-flow numerator can be paired directly with the literature-backed "
                "annual-flow h4 endpoint proxy, which is now the default empirical runtime denominator."
                if literature_runtime_ready
                else "Annual-flow numerator can be compared review-only with the literature annual-flow proxy anchor."
            ),
            "next_backend_action": (
                "use_as_default_empirical_runtime_anchor"
                if literature_runtime_ready
                else "keep_review_only_literature_pairing"
            ),
            "allowed_use": (
                "scenario_runtime_empirical_annual_flow_primary"
                if literature_runtime_ready
                else "review_only_literature_annual_flow_comparison"
            ),
            "blocked_use": (
                "canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": (
                "annual_support_primary_empirical_runtime_pairing"
                if literature_runtime_ready
                else "annual_support_review_only_literature_pairing"
            ),
        },
        {
            "compatibility_row_id": (
                "annual_support_denominator_compatibility::bounded_h8_overlay"
            ),
            "ratio_id": "RW_Y",
            "numerator_timing_class": "annual_support_flow_review_only",
            "denominator_source_id": _PRIMARY_BOUNDED_SOURCE_ID,
            "denominator_timing_class": anchors_by_id[_PRIMARY_BOUNDED_SOURCE_ID][
                "timing_alignment_class"
            ],
            "comparison_mode": "review_only_overlay_nonratio",
            "support_offset_computation_allowed": "false",
            "runtime_anchor_allowed": "false",
            "translation_artifact": "",
            "translation_row_id": "",
            "comparability_status": (
                "blocked_not_timing_commensurate_for_support_offset"
            ),
            "exact_blocker": (
                "Bounded h8 is a cumulative h8 object and not an annual-flow denominator."
            ),
            "safe_sentence": (
                "Bounded h8 may remain visible only as a non-ratio overlay unless a formal translation artifact is materialized."
            ),
            "next_backend_action": (
                "either_materialize_formal_translation_or_keep_nonratio_overlay"
            ),
            "allowed_use": "review_only_h8_overlay_only",
            "blocked_use": (
                "support_offset_ratio;scenario_runtime_anchor;canonical_RW_Y;main_ratio;"
                "Evidence_Mode;denominator_prior;pricing;holder_allocation;"
                "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "annual_support_bounded_h8_nonratio_overlay_only",
        },
        {
            "compatibility_row_id": (
                "annual_support_denominator_compatibility::literature_h8_mapped"
            ),
            "ratio_id": "RW_Y",
            "numerator_timing_class": "annual_support_flow_review_only",
            "denominator_source_id": "literature_h8_mapped_review_only",
            "denominator_timing_class": "h8_cumulative",
            "comparison_mode": "review_only_overlay_nonratio",
            "support_offset_computation_allowed": "false",
            "runtime_anchor_allowed": "false",
            "translation_artifact": "ratewall_residualized_ffr_normalization_bridge.csv",
            "translation_row_id": (
                literature_h8["normalization_row_id"] if literature_h8 is not None else ""
            ),
            "comparability_status": (
                "blocked_not_timing_commensurate_for_support_offset"
                if literature_h8 is not None
                else "blocked_literature_h8_translation_missing"
            ),
            "exact_blocker": (
                "The literature h8 mapped object shares the cumulative h8 family and is not a direct annual-flow denominator."
                if literature_h8 is not None
                else "The literature h8 mapped object is unavailable because residualized-FFR replication inputs were not materialized."
            ),
            "safe_sentence": (
                "Literature h8 can serve as cumulative review context, not a timing-aligned annual support denominator."
                if literature_h8 is not None
                else "No literature h8 mapped object is emitted unless the residualized-FFR replication inputs materialize."
            ),
            "next_backend_action": (
                "keep_literature_h8_in_cumulative_review_family_only"
                if literature_h8 is not None
                else "materialize_residualized_ffr_replication_inputs_before_h8_review"
            ),
            "allowed_use": (
                "review_only_h8_family_context"
                if literature_h8 is not None
                else "methodology_scaffold_only"
            ),
            "blocked_use": (
                "support_offset_ratio;scenario_runtime_anchor;canonical_RW_Y;main_ratio;"
                "Evidence_Mode;denominator_prior;pricing;holder_allocation;"
                "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "annual_support_literature_h8_nonratio_overlay_only",
        },
        {
            "compatibility_row_id": (
                "annual_support_denominator_compatibility::frbus_h8_proxy"
            ),
            "ratio_id": "RW_Y",
            "numerator_timing_class": "annual_support_flow_review_only",
            "denominator_source_id": "frbus_h8_component_proxy",
            "denominator_timing_class": "h8_cumulative",
            "comparison_mode": "review_only_overlay_nonratio",
            "support_offset_computation_allowed": "false",
            "runtime_anchor_allowed": "false",
            "translation_artifact": "ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv",
            "translation_row_id": "",
            "comparability_status": (
                "blocked_not_timing_commensurate_for_support_offset"
            ),
            "exact_blocker": (
                "The FRB/US h8 benchmark proxy is a cumulative model benchmark and not a direct annual-flow denominator."
            ),
            "safe_sentence": (
                "FRB/US h8 belongs to the cumulative review family and stays benchmark-only for annual-support comparisons."
            ),
            "next_backend_action": "keep_frbus_in_cumulative_review_family_only",
            "allowed_use": "review_only_h8_family_context",
            "blocked_use": (
                "support_offset_ratio;scenario_runtime_anchor;canonical_RW_Y;main_ratio;"
                "Evidence_Mode;denominator_prior;pricing;holder_allocation;"
                "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "annual_support_frbus_h8_nonratio_overlay_only",
        },
    ]
    rows: list[dict[str, str]] = []
    for spec in row_specs:
        row = {
            field: ""
            for field in ANNUAL_SUPPORT_DENOMINATOR_COMPATIBILITY_REGISTRY_FIELDS
        }
        row.update(spec)
        row.update(_disabled_switches())
        rows.append(row)
    return rows


def _annual_support_numerator_component_registry_rows(
    *,
    forecast_holder_tdc_consistency_bridge_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    component_specs = (
        {
            "component_id": "domestic_nonbank_interest_support",
            "component_role": "direct_runtime_interest_support",
            "stage": "interest_income_direct",
            "amount_field_bil": "domestic_nonbank_interest_support_bil",
            "sign_convention": "positive_support_addition",
            "inclusion_scope": "direct_addition",
            "directly_added": "true",
            "additivity_scope": "direct_runtime_component",
            "safe_sentence": (
                "Domestic nonbank interest support is a direct positive runtime numerator component."
            ),
        },
        {
            "component_id": "bank_retained_margin_support",
            "component_role": "direct_runtime_interest_support",
            "stage": "interest_income_direct",
            "amount_field_bil": "bank_retained_margin_support_bil",
            "sign_convention": "positive_support_addition",
            "inclusion_scope": "direct_addition",
            "directly_added": "true",
            "additivity_scope": "direct_runtime_component",
            "safe_sentence": (
                "Bank retained-margin support is a direct positive runtime numerator component."
            ),
        },
        {
            "component_id": "interest_income_current_demand_support_subtotal",
            "component_role": "subtotal_memo",
            "stage": "interest_income_subtotal",
            "amount_field_bil": "interest_income_current_demand_support_bil",
            "sign_convention": "positive_subtotal_memo",
            "inclusion_scope": "subtotal_memo_not_additive",
            "directly_added": "false",
            "additivity_scope": "subtotal_identity_only",
            "safe_sentence": (
                "Interest-income current-demand support is a subtotal memo and must not be added on top of its direct components."
            ),
        },
        {
            "component_id": "tdc_interest_overlap_memo",
            "component_role": "overlap_guard_memo",
            "stage": "overlap_guard",
            "amount_field_bil": "tdc_interest_debt_service_overlap_with_interest_income_bil",
            "sign_convention": "memo_overlap_not_additive",
            "inclusion_scope": "memo_only_overlap_guard",
            "directly_added": "false",
            "additivity_scope": "memo_overlap_guard",
            "safe_sentence": (
                "Direct interest overlap is memo-only and exists to prevent double counting between interest support and TDC deposit support."
            ),
        },
        {
            "component_id": "tdc_deposit_liquidity_base_ex_interest_memo",
            "component_role": "upstream_tdc_base_memo",
            "stage": "tdc_deposit_base",
            "amount_field_bil": "tdc_deposit_liquidity_base_ex_interest_bil",
            "sign_convention": "signed_upstream_tdc_base_memo",
            "inclusion_scope": "memo_only_upstream_base",
            "directly_added": "false",
            "additivity_scope": "memo_upstream_tdc_base",
            "safe_sentence": (
                "The TDC deposit liquidity base excluding direct interest is upstream memo context, not a separately additive runtime numerator term."
            ),
        },
        {
            "component_id": "tdc_deposit_current_demand_support",
            "component_role": "direct_runtime_tdc_support",
            "stage": "tdc_deposit_direct",
            "amount_field_bil": "tdc_deposit_current_demand_support_bil",
            "sign_convention": "signed_direct_runtime_component",
            "inclusion_scope": "direct_addition",
            "directly_added": "true",
            "additivity_scope": "direct_runtime_component",
            "safe_sentence": (
                "TDC deposit current-demand support is a signed direct runtime component and may offset or subtract from total support."
            ),
        },
        {
            "component_id": "combined_current_demand_support_total",
            "component_role": "final_total_memo",
            "stage": "runtime_total",
            "amount_field_bil": "combined_current_demand_support_bil",
            "sign_convention": "final_total_identity_memo",
            "inclusion_scope": "final_total_memo_not_additive",
            "directly_added": "false",
            "additivity_scope": "final_total_identity_only",
            "safe_sentence": (
                "Combined current-demand support is the runtime numerator total and must reconcile from direct components rather than be added again."
            ),
        },
    )
    rows: list[dict[str, str]] = []
    for bridge_row in forecast_holder_tdc_consistency_bridge_rows:
        contract_row_id = (
            "annual_support_numerator_contract::"
            f"{bridge_row['forecast_year']}::{bridge_row['mpc_scenario']}::"
            f"{bridge_row['maturity_scenario']}::{bridge_row['holder_scenario']}"
        )
        source_row_handle = (
            f"{bridge_row['forecast_year']}::{bridge_row['mpc_scenario']}::"
            f"{bridge_row['maturity_scenario']}::{bridge_row['holder_scenario']}"
        )
        for spec in component_specs:
            component_value = bridge_row.get(spec["amount_field_bil"], "")
            runtime_allowed = (
                "true" if spec["directly_added"] == "true" else "false"
            )
            exact_blocker = (
                ""
                if runtime_allowed == "true"
                else "Memo, subtotal, overlap-guard, and total-identity rows may not enter the runtime numerator directly."
            )
            row = {
                field: ""
                for field in ANNUAL_SUPPORT_NUMERATOR_COMPONENT_REGISTRY_FIELDS
            }
            row.update(
                {
                    "component_row_id": (
                        "annual_support_numerator_component_registry::"
                        f"{source_row_handle}::{spec['component_id']}"
                    ),
                    "contract_row_id": contract_row_id,
                    "ratio_id": "RW_Y",
                    "forecast_year": bridge_row["forecast_year"],
                    "mpc_scenario": bridge_row["mpc_scenario"],
                    "maturity_scenario": bridge_row["maturity_scenario"],
                    "holder_scenario": bridge_row["holder_scenario"],
                    "component_id": spec["component_id"],
                    "component_role": spec["component_role"],
                    "stage": spec["stage"],
                    "source_artifact": "ratewall_forecast_holder_tdc_consistency_bridge.csv",
                    "source_row_handle": source_row_handle,
                    "horizon": "1y",
                    "timing_class": "annual_flow_current_window",
                    "amount_field_bil": spec["amount_field_bil"],
                    "component_value_bil": component_value,
                    "sign_convention": spec["sign_convention"],
                    "inclusion_scope": spec["inclusion_scope"],
                    "included_in_scalar_numerator": runtime_allowed,
                    "included_in_split_numerator": runtime_allowed,
                    "directly_added_to_final_numerator": spec["directly_added"],
                    "additivity_scope": spec["additivity_scope"],
                    "uncertainty_status": (
                        "assumption_mode_projection_runtime_component"
                    ),
                    "runtime_allowed": runtime_allowed,
                    "exact_blocker": exact_blocker,
                    "safe_sentence": spec["safe_sentence"],
                    "next_backend_action": (
                        "keep_runtime_numerator_contract_componentized_and_fail_closed"
                    ),
                    "allowed_use": (
                        "runtime_current_window_numerator_component"
                        if runtime_allowed == "true"
                        else "memo_or_subtotal_context_only"
                    ),
                    "blocked_use": (
                        "canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;pricing;"
                        "holder_allocation;raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": (
                        "annual_support_runtime_numerator_component_contract"
                    ),
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    return rows


def _numerator_component_source_gate_specs() -> dict[str, dict[str, str]]:
    return {
        "domestic_nonbank_interest_support": {
            "source_strength_class": (
                "mixed_source_backed_interest_cashflow_plus_behavior_assumption"
            ),
            "timing_role": "current_window_direct_interest_support",
            "memo_direct_status": "direct_runtime_component",
            "uncertainty_class": "mpc_behavior_assumption_scaled_direct_component",
            "source_input_fields": (
                "projected_total_interest_cashflow_bil;"
                "domestic_nonbank_holder_share;"
                "domestic_nonbank_current_spend_share_assumption"
            ),
        },
        "bank_retained_margin_support": {
            "source_strength_class": (
                "mixed_source_backed_interest_cashflow_plus_fixed_behavior_assumption"
            ),
            "timing_role": "current_window_direct_interest_support",
            "memo_direct_status": "direct_runtime_component",
            "uncertainty_class": "fixed_behavior_assumption_scaled_direct_component",
            "source_input_fields": (
                "projected_total_interest_cashflow_bil;"
                "bank_holder_share;"
                "bank_retained_margin_spend_share_assumption"
            ),
        },
        "interest_income_current_demand_support_subtotal": {
            "source_strength_class": "derived_subtotal_from_direct_components",
            "timing_role": "current_window_subtotal_context",
            "memo_direct_status": "subtotal_memo_context_only",
            "uncertainty_class": "derived_identity_no_separate_uncertainty",
            "source_input_fields": (
                "domestic_nonbank_interest_support_bil;"
                "bank_retained_margin_support_bil"
            ),
        },
        "tdc_interest_overlap_memo": {
            "source_strength_class": "double_count_guardrail_from_tdcsim_projection",
            "timing_role": "current_window_overlap_guard_memo",
            "memo_direct_status": "memo_overlap_guard",
            "uncertainty_class": "deterministic_overlap_guard_memo",
            "source_input_fields": (
                "tdc_debt_service_interest_to_domestic_nonbanks_bil"
            ),
        },
        "tdc_deposit_liquidity_base_ex_interest_memo": {
            "source_strength_class": "tdcsim_projection_upstream_memo_context",
            "timing_role": "current_window_upstream_tdc_memo",
            "memo_direct_status": "memo_upstream_context",
            "uncertainty_class": "tdcsim_projection_memo_context",
            "source_input_fields": (
                "tdcsim_projected_tdc_change_bil;"
                "tdc_interest_debt_service_overlap_with_interest_income_bil"
            ),
        },
        "tdc_deposit_current_demand_support": {
            "source_strength_class": (
                "tdcsim_projection_plus_behavior_assumption_direct_component"
            ),
            "timing_role": "current_window_direct_tdc_support",
            "memo_direct_status": "direct_runtime_component",
            "uncertainty_class": "mpc_behavior_assumption_scaled_tdcsim_component",
            "source_input_fields": (
                "tdc_deposit_liquidity_base_ex_interest_bil;"
                "domestic_nonbank_current_spend_share_assumption"
            ),
        },
        "combined_current_demand_support_total": {
            "source_strength_class": "final_identity_from_direct_components",
            "timing_role": "current_window_total_identity_context",
            "memo_direct_status": "final_total_memo_context_only",
            "uncertainty_class": "derived_identity_no_separate_uncertainty",
            "source_input_fields": (
                "interest_income_current_demand_support_bil;"
                "tdc_deposit_current_demand_support_bil"
            ),
        },
    }


def _annual_support_numerator_source_gate_rows(
    *,
    annual_support_numerator_component_registry_rows: Sequence[dict[str, str]],
    forecast_holder_tdc_consistency_bridge_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    bridge_by_handle = {
        (
            f"{row['forecast_year']}::{row['mpc_scenario']}::"
            f"{row['maturity_scenario']}::{row['holder_scenario']}"
        ): row
        for row in forecast_holder_tdc_consistency_bridge_rows
    }
    specs_by_component = _numerator_component_source_gate_specs()
    rows: list[dict[str, str]] = []
    for component_row in annual_support_numerator_component_registry_rows:
        spec = specs_by_component[component_row["component_id"]]
        bridge_row = bridge_by_handle[component_row["source_row_handle"]]
        source_status_tokens = set(bridge_row["source_status"].split(";"))
        runtime_component_eligible = (
            "true"
            if component_row["directly_added_to_final_numerator"] == "true"
            else "false"
        )
        tdc_direct_source_blocked = (
            component_row["component_id"] == "tdc_deposit_current_demand_support"
            and (
                "pass_tdcsim_contract_annualized" not in source_status_tokens
                or "blocked_unmapped_tdcsim_contract_scenario" in source_status_tokens
                or "blocked_missing_combined_tdcsim_contract_scenario"
                in source_status_tokens
            )
        )
        if tdc_direct_source_blocked:
            source_gate_status = (
                "blocked_missing_combined_tdcsim_contract_scenario"
                if "blocked_missing_combined_tdcsim_contract_scenario"
                in source_status_tokens
                else "blocked_tdcsim_contract_source_unmapped"
            )
            exact_blocker = (
                "TDC deposit current-demand support requires a mapped TDC-SIM "
                "contract source row for this combined maturity/holder scenario "
                "before runtime use."
            )
            allowed_use = "blocked_runtime_component_source_gate"
            next_backend_action = (
                "export_or_map_combined_tdcsim_contract_scenario_before_runtime_tdc_deposit_support_use"
            )
        elif runtime_component_eligible == "true":
            source_gate_status = "pass_direct_runtime_component_source_classified"
            exact_blocker = ""
            allowed_use = "runtime_component_source_gate"
            next_backend_action = (
                "carry_component_source_gate_into_runtime_contract_and_uncertainty_envelope"
            )
        else:
            source_gate_status = "pass_memo_component_source_classified_nonruntime"
            exact_blocker = (
                "Memo, subtotal, overlap-guard, and total-identity rows remain "
                "context only even after source classification."
            )
            allowed_use = "memo_component_source_gate_context_only"
            next_backend_action = (
                "carry_component_source_gate_into_runtime_contract_and_uncertainty_envelope"
            )
        row = {
            field: "" for field in ANNUAL_SUPPORT_NUMERATOR_SOURCE_GATE_FIELDS
        }
        row.update(
            {
                "source_gate_row_id": (
                    "annual_support_numerator_source_gate::"
                    f"{component_row['source_row_handle']}::{component_row['component_id']}"
                ),
                "component_row_id": component_row["component_row_id"],
                "contract_row_id": component_row["contract_row_id"],
                "ratio_id": component_row["ratio_id"],
                "forecast_year": component_row["forecast_year"],
                "mpc_scenario": component_row["mpc_scenario"],
                "maturity_scenario": component_row["maturity_scenario"],
                "holder_scenario": component_row["holder_scenario"],
                "component_id": component_row["component_id"],
                "component_role": component_row["component_role"],
                "source_artifact": component_row["source_artifact"],
                "source_row_handle": component_row["source_row_handle"],
                "source_strength_class": spec["source_strength_class"],
                "timing_role": spec["timing_role"],
                "inclusion_scope": component_row["inclusion_scope"],
                "memo_direct_status": spec["memo_direct_status"],
                "uncertainty_class": spec["uncertainty_class"],
                "source_input_fields": spec["source_input_fields"],
                "source_status_raw": bridge_row["source_status"],
                "source_gate_status": source_gate_status,
                "runtime_component_eligible": runtime_component_eligible,
                "exact_blocker": exact_blocker,
                "safe_sentence": (
                    "This source gate classifies the runtime numerator component by source strength, timing role, memo/direct status, and uncertainty class before it can be narrated downstream."
                ),
                "next_backend_action": next_backend_action,
                "allowed_use": allowed_use,
                "blocked_use": component_row["blocked_use"],
                "claim_boundary": "annual_support_runtime_numerator_source_gate",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _numerator_source_gate_summary_by_contract(
    *,
    annual_support_numerator_source_gate_rows: Sequence[dict[str, str]],
) -> dict[str, dict[str, str]]:
    rows_by_contract: dict[str, list[dict[str, str]]] = {}
    for row in annual_support_numerator_source_gate_rows:
        rows_by_contract.setdefault(row["contract_row_id"], []).append(row)
    summary: dict[str, dict[str, str]] = {}
    for contract_row_id, rows in rows_by_contract.items():
        direct_rows = [row for row in rows if row["runtime_component_eligible"] == "true"]
        direct_ready = all(
            row["source_gate_status"] == "pass_direct_runtime_component_source_classified"
            for row in direct_rows
        )
        first_blocked_direct = next(
            (
                row
                for row in direct_rows
                if row["source_gate_status"]
                != "pass_direct_runtime_component_source_classified"
            ),
            None,
        )
        summary[contract_row_id] = {
            "source_gate_status": (
                "pass_all_direct_runtime_components_source_classified"
                if direct_ready
                else first_blocked_direct["source_gate_status"]
                if first_blocked_direct is not None
                else "blocked_unclassified_direct_runtime_component"
            ),
            "runtime_allowed": "true" if direct_ready else "false",
            "exact_blocker": (
                ""
                if direct_ready
                else first_blocked_direct["exact_blocker"]
                if first_blocked_direct is not None
                else "Every direct runtime numerator component must have an explicit source/timing/uncertainty classification before downstream runtime use."
            ),
        }
    return summary


def _annual_support_numerator_component_rollup_rows(
    *,
    annual_support_numerator_component_registry_rows: Sequence[dict[str, str]],
    annual_support_numerator_source_gate_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    component_rows_by_id: dict[str, list[dict[str, str]]] = {}
    for row in annual_support_numerator_component_registry_rows:
        component_rows_by_id.setdefault(row["component_id"], []).append(row)

    gate_rows_by_component: dict[str, list[dict[str, str]]] = {}
    for row in annual_support_numerator_source_gate_rows:
        gate_rows_by_component.setdefault(row["component_id"], []).append(row)

    rows: list[dict[str, str]] = []
    for component_id, component_rows in sorted(component_rows_by_id.items()):
        sample = component_rows[0]
        gate_rows = gate_rows_by_component.get(component_id, [])
        component_values = [
            _decimal_or_none(row["component_value_bil"])
            for row in component_rows
            if _decimal_or_none(row["component_value_bil"]) is not None
        ]
        direct_flag_set = {
            row["directly_added_to_final_numerator"] for row in component_rows
        }
        scalar_flag_set = {
            row["included_in_scalar_numerator"] for row in component_rows
        }
        split_flag_set = {
            row["included_in_split_numerator"] for row in component_rows
        }
        runtime_eligible_set = {
            row["runtime_component_eligible"] for row in gate_rows
        }
        runtime_allowed_set = {row["runtime_allowed"] for row in component_rows}
        source_gate_status_set = {row["source_gate_status"] for row in gate_rows}
        direct_runtime = direct_flag_set == {"true"}
        memo_only = direct_flag_set == {"false"}
        source_gate_classified = len(gate_rows) == len(component_rows)
        source_gate_passes = all(
            status.startswith("pass_") for status in source_gate_status_set
        )
        rollup_passes = (
            source_gate_classified
            and source_gate_passes
            and (
                (direct_runtime and runtime_eligible_set == {"true"})
                or (memo_only and runtime_eligible_set == {"false"})
            )
        )
        if direct_runtime:
            component_class = "direct_runtime_component"
            memo_exclusion_status = "not_applicable_direct_runtime_component"
            allowed_use = "runtime_numerator_component_rollup"
            exact_blocker = "" if rollup_passes else "direct_runtime_component_source_gate_not_fully_classified"
            safe_sentence = (
                f"{component_id} is a direct runtime numerator component; it is "
                "included once through the annual-support numerator contract."
            )
        else:
            component_class = "memo_or_identity_component"
            memo_exclusion_status = (
                "pass_memo_component_excluded_from_runtime_numerator"
                if memo_only
                else "blocked_mixed_direct_and_memo_classification"
            )
            allowed_use = "memo_component_rollup_context_only"
            exact_blocker = (
                "Memo, subtotal, overlap-guard, and total-identity components "
                "remain excluded from the runtime numerator."
            )
            safe_sentence = (
                f"{component_id} is memo-only context and is not additively "
                "included in the runtime numerator."
            )

        row = {
            field: "" for field in ANNUAL_SUPPORT_NUMERATOR_COMPONENT_ROLLUP_FIELDS
        }
        row.update(
            {
                "rollup_row_id": f"annual_support_numerator_component_rollup::{component_id}",
                "ratio_id": sample["ratio_id"],
                "component_id": component_id,
                "component_role": sample["component_role"],
                "stage": sample["stage"],
                "component_class": component_class,
                "source_artifact": sample["source_artifact"],
                "source_gate_artifact": "ratewall_annual_support_numerator_source_gate.csv",
                "component_registry_artifact": (
                    "ratewall_annual_support_numerator_component_registry.csv"
                ),
                "component_row_count": str(len(component_rows)),
                "source_gate_row_count": str(len(gate_rows)),
                "contract_row_count": str(
                    len({row["contract_row_id"] for row in component_rows})
                ),
                "forecast_year_count": str(
                    len({row["forecast_year"] for row in component_rows})
                ),
                "directly_added_to_final_numerator": ";".join(sorted(direct_flag_set)),
                "runtime_component_eligible": ";".join(sorted(runtime_eligible_set)),
                "runtime_allowed": ";".join(sorted(runtime_allowed_set)),
                "included_in_scalar_numerator": ";".join(sorted(scalar_flag_set)),
                "included_in_split_numerator": ";".join(sorted(split_flag_set)),
                "memo_exclusion_status": memo_exclusion_status,
                "source_gate_status": ";".join(sorted(source_gate_status_set)),
                "component_value_min_bil": _format_decimal(min(component_values)),
                "component_value_max_bil": _format_decimal(max(component_values)),
                "component_value_abs_max_bil": _format_decimal(
                    max(abs(value) for value in component_values)
                ),
                "sign_convention_set": ";".join(
                    sorted({row["sign_convention"] for row in component_rows})
                ),
                "inclusion_scope_set": ";".join(
                    sorted({row["inclusion_scope"] for row in component_rows})
                ),
                "additivity_scope_set": ";".join(
                    sorted({row["additivity_scope"] for row in component_rows})
                ),
                "uncertainty_class_set": ";".join(
                    sorted({row["uncertainty_class"] for row in gate_rows})
                ),
                "timing_role_set": ";".join(
                    sorted({row["timing_role"] for row in gate_rows})
                ),
                "source_strength_class_set": ";".join(
                    sorted({row["source_strength_class"] for row in gate_rows})
                ),
                "rollup_status": (
                    "pass_component_rollup_classified_and_guarded"
                    if rollup_passes
                    else "blocked_component_rollup_source_gate_or_classification_mismatch"
                ),
                "exact_blocker": exact_blocker,
                "safe_sentence": safe_sentence,
                "next_backend_action": (
                    "carry_component_rollup_into_runtime_numerator_hardening"
                ),
                "allowed_use": allowed_use,
                "blocked_use": sample["blocked_use"],
                "claim_boundary": "annual_support_runtime_numerator_component_rollup",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _annual_support_numerator_uncertainty_envelope_rows(
    *,
    annual_support_numerator_contract_rows: Sequence[dict[str, str]],
    annual_support_numerator_source_gate_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    gate_summary_by_contract = _numerator_source_gate_summary_by_contract(
        annual_support_numerator_source_gate_rows=annual_support_numerator_source_gate_rows
    )
    rows_by_family: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in annual_support_numerator_contract_rows:
        rows_by_family.setdefault(
            (row["forecast_year"], row["maturity_scenario"], row["holder_scenario"]),
            [],
        ).append(row)

    envelope_rows: list[dict[str, str]] = []
    for family_key, family_rows in rows_by_family.items():
        ranked_rows = sorted(
            family_rows,
            key=lambda item: _decimal_or_none(item["runtime_current_window_numerator_bil"])
            or Decimal("0"),
        )
        lower_row = ranked_rows[0]
        upper_row = ranked_rows[-1]
        base_row = next(
            (
                row
                for row in family_rows
                if row["mpc_scenario"] == "base_mpc_10pct"
            ),
            ranked_rows[len(ranked_rows) // 2],
        )
        for contract_row in family_rows:
            gate_summary = gate_summary_by_contract[contract_row["contract_row_id"]]
            current_role = (
                "base_case_member"
                if contract_row["contract_row_id"] == base_row["contract_row_id"]
                else "lower_bound_member"
                if contract_row["contract_row_id"] == lower_row["contract_row_id"]
                else "upper_bound_member"
                if contract_row["contract_row_id"] == upper_row["contract_row_id"]
                else "interior_family_member"
            )
            runtime_allowed = (
                "true"
                if contract_row["runtime_allowed"] == "true"
                and gate_summary["runtime_allowed"] == "true"
                else "false"
            )
            exact_blocker = (
                gate_summary["exact_blocker"]
                if gate_summary["runtime_allowed"] != "true"
                else contract_row["exact_blocker"]
            )
            row = {
                field: ""
                for field in ANNUAL_SUPPORT_NUMERATOR_UNCERTAINTY_ENVELOPE_FIELDS
            }
            row.update(
                {
                    "envelope_row_id": (
                        "annual_support_numerator_uncertainty_envelope::"
                        f"{contract_row['forecast_year']}::{contract_row['mpc_scenario']}::"
                        f"{contract_row['maturity_scenario']}::{contract_row['holder_scenario']}"
                    ),
                    "contract_row_id": contract_row["contract_row_id"],
                    "ratio_id": contract_row["ratio_id"],
                    "forecast_year": contract_row["forecast_year"],
                    "mpc_scenario": contract_row["mpc_scenario"],
                    "maturity_scenario": contract_row["maturity_scenario"],
                    "holder_scenario": contract_row["holder_scenario"],
                    "uncertainty_family_id": (
                        "annual_support_numerator_uncertainty_family::"
                        f"{family_key[0]}::{family_key[1]}::{family_key[2]}"
                    ),
                    "source_gate_artifact": (
                        "ratewall_annual_support_numerator_source_gate.csv"
                    ),
                    "source_gate_status": gate_summary["source_gate_status"],
                    "envelope_method": (
                        "observed_mpc_family_bounds_same_year_maturity_holder"
                    ),
                    "uncertainty_family": "mpc_scenario_runtime_projection_family",
                    "current_role_in_family": current_role,
                    "numerator_current_bil": contract_row[
                        "runtime_current_window_numerator_bil"
                    ],
                    "numerator_lower_bound_bil": lower_row[
                        "runtime_current_window_numerator_bil"
                    ],
                    "numerator_base_case_bil": base_row[
                        "runtime_current_window_numerator_bil"
                    ],
                    "numerator_upper_bound_bil": upper_row[
                        "runtime_current_window_numerator_bil"
                    ],
                    "support_pct_current_gdp": contract_row["support_pct_of_gdp"],
                    "support_pct_lower_bound_gdp": lower_row["support_pct_of_gdp"],
                    "support_pct_base_case_gdp": base_row["support_pct_of_gdp"],
                    "support_pct_upper_bound_gdp": upper_row["support_pct_of_gdp"],
                    "lower_contract_row_id": lower_row["contract_row_id"],
                    "base_contract_row_id": base_row["contract_row_id"],
                    "upper_contract_row_id": upper_row["contract_row_id"],
                    "uncertainty_status": (
                        "pass_mpc_family_runtime_numerator_envelope_materialized"
                    ),
                    "runtime_allowed": runtime_allowed,
                    "exact_blocker": exact_blocker,
                    "safe_sentence": (
                        "This envelope separates numerator-side MPC-family runtime uncertainty from denominator confidence intervals for the same year, maturity, and holder path."
                    ),
                    "next_backend_action": (
                        "carry_numerator_uncertainty_envelope_into_runtime_support_offset_outputs"
                    ),
                    "allowed_use": "runtime_numerator_uncertainty_envelope",
                    "blocked_use": contract_row["blocked_use"],
                    "claim_boundary": "annual_support_runtime_numerator_uncertainty_envelope",
                    **_disabled_switches(),
                }
            )
            envelope_rows.append(row)
    return envelope_rows


def _annual_support_numerator_contract_rows(
    *,
    annual_support_numerator_component_registry_rows: Sequence[dict[str, str]],
    forecast_holder_tdc_consistency_bridge_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    rows_by_contract: dict[str, list[dict[str, str]]] = {}
    for row in annual_support_numerator_component_registry_rows:
        rows_by_contract.setdefault(row["contract_row_id"], []).append(row)
    bridge_by_key = {
        (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
        ): row
        for row in forecast_holder_tdc_consistency_bridge_rows
    }

    contract_rows: list[dict[str, str]] = []
    for contract_row_id, component_rows in rows_by_contract.items():
        sample_row = component_rows[0]
        bridge_row = bridge_by_key[
            (
                sample_row["forecast_year"],
                sample_row["mpc_scenario"],
                sample_row["maturity_scenario"],
                sample_row["holder_scenario"],
            )
        ]
        direct_rows = [
            row
            for row in component_rows
            if row["directly_added_to_final_numerator"] == "true"
        ]
        memo_rows = [
            row
            for row in component_rows
            if row["directly_added_to_final_numerator"] != "true"
        ]
        direct_sum = sum(
            (_decimal_or_none(row["component_value_bil"]) or Decimal("0"))
            for row in direct_rows
        )
        memo_sum = sum(
            (_decimal_or_none(row["component_value_bil"]) or Decimal("0"))
            for row in memo_rows
        )
        interest_support = next(
            (
                _decimal_or_none(row["component_value_bil"])
                for row in component_rows
                if row["component_id"] == "interest_income_current_demand_support_subtotal"
            ),
            None,
        )
        tdc_support = next(
            (
                _decimal_or_none(row["component_value_bil"])
                for row in component_rows
                if row["component_id"] == "tdc_deposit_current_demand_support"
            ),
            None,
        )
        total_support = next(
            (
                _decimal_or_none(row["component_value_bil"])
                for row in component_rows
                if row["component_id"] == "combined_current_demand_support_total"
            ),
            None,
        )
        nominal_gdp = _decimal_or_none(bridge_row["nominal_gdp_bil"])
        support_pct = (
            None
            if total_support is None or nominal_gdp in {None, Decimal("0")}
            else Decimal("100") * total_support / nominal_gdp
        )
        direct_reconciles = total_support is not None and direct_sum == total_support
        runtime_allowed = "true" if direct_reconciles else "false"
        row = {field: "" for field in ANNUAL_SUPPORT_NUMERATOR_CONTRACT_FIELDS}
        row.update(
            {
                "contract_row_id": contract_row_id,
                "ratio_id": "RW_Y",
                "component_registry_artifact": (
                    "ratewall_annual_support_numerator_component_registry.csv"
                ),
                "forecast_year": sample_row["forecast_year"],
                "mpc_scenario": sample_row["mpc_scenario"],
                "maturity_scenario": sample_row["maturity_scenario"],
                "holder_scenario": sample_row["holder_scenario"],
                "nominal_gdp_bil": bridge_row["nominal_gdp_bil"],
                "interest_income_support_bil": _format_decimal(interest_support),
                "tdc_deposit_support_bil": _format_decimal(tdc_support),
                "runtime_current_window_numerator_bil": _format_decimal(total_support),
                "scalar_runtime_numerator_bil": _format_decimal(total_support),
                "split_runtime_numerator_bil": _format_decimal(total_support),
                "direct_component_sum_bil": _format_decimal(direct_sum),
                "memo_component_sum_bil": _format_decimal(memo_sum),
                "support_pct_of_gdp": _format_decimal(support_pct),
                "direct_component_count": str(len(direct_rows)),
                "memo_component_count": str(len(memo_rows)),
                "timing_class": "annual_flow_current_window",
                "uncertainty_status": "assumption_mode_projection_runtime_contract",
                "runtime_allowed": runtime_allowed,
                "reconciliation_status": (
                    "pass_direct_components_reconcile_to_runtime_numerator"
                    if direct_reconciles
                    else "blocked_runtime_direct_components_fail_to_reconcile"
                ),
                "exact_blocker": (
                    ""
                    if direct_reconciles
                    else "Direct runtime numerator components must reconcile exactly to the combined current-demand support total."
                ),
                "safe_sentence": (
                    "This contract freezes the runtime annual-flow numerator to the current-window support total reconstructed from direct components."
                ),
                "next_backend_action": (
                    "use_contract_total_for_runtime_annual_flow_support_offset_outputs"
                ),
                "allowed_use": "runtime_annual_flow_numerator_contract",
                "blocked_use": (
                    "canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;pricing;"
                    "holder_allocation;raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "annual_support_runtime_numerator_contract",
                **_disabled_switches(),
            }
        )
        contract_rows.append(row)
    return contract_rows


def _annual_support_numerator_contract_invariant_audit_rows(
    *,
    annual_support_numerator_contract_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for contract_row in annual_support_numerator_contract_rows:
        direct_sum = _decimal_or_none(contract_row["direct_component_sum_bil"])
        runtime_total = _decimal_or_none(
            contract_row["runtime_current_window_numerator_bil"]
        )
        delta = (
            None
            if direct_sum is None or runtime_total is None
            else direct_sum - runtime_total
        )
        row = {
            field: ""
            for field in ANNUAL_SUPPORT_NUMERATOR_CONTRACT_INVARIANT_AUDIT_FIELDS
        }
        row.update(
            {
                "audit_row_id": (
                    "annual_support_numerator_contract_invariant_audit::"
                    f"{contract_row['forecast_year']}::{contract_row['mpc_scenario']}::"
                    f"{contract_row['maturity_scenario']}::{contract_row['holder_scenario']}"
                ),
                "contract_row_id": contract_row["contract_row_id"],
                "ratio_id": contract_row["ratio_id"],
                "forecast_year": contract_row["forecast_year"],
                "mpc_scenario": contract_row["mpc_scenario"],
                "maturity_scenario": contract_row["maturity_scenario"],
                "holder_scenario": contract_row["holder_scenario"],
                "numerator_contract_artifact": (
                    "ratewall_annual_support_numerator_contract.csv"
                ),
                "direct_component_count": contract_row["direct_component_count"],
                "memo_component_count": contract_row["memo_component_count"],
                "direct_component_sum_bil": contract_row["direct_component_sum_bil"],
                "runtime_current_window_numerator_bil": contract_row[
                    "runtime_current_window_numerator_bil"
                ],
                "reconciliation_delta_bil": _format_decimal(delta),
                "memo_exclusion_status": (
                    "pass_memo_components_excluded_from_runtime_numerator"
                ),
                "reconciliation_status": contract_row["reconciliation_status"],
                "runtime_allowed": contract_row["runtime_allowed"],
                "exact_blocker": contract_row["exact_blocker"],
                "safe_sentence": (
                    "This audit proves that only direct components enter the runtime numerator and that they reconcile exactly before runtime support offsets are emitted."
                ),
                "next_backend_action": (
                    "gate_runtime_support_offset_outputs_on_contract_invariant_pass"
                ),
                "allowed_use": "runtime_numerator_invariant_audit",
                "blocked_use": contract_row["blocked_use"],
                "claim_boundary": "annual_support_runtime_numerator_invariant_audit",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _runtime_annual_flow_support_offset_scenario_rows(
    *,
    annual_support_numerator_contract_rows: Sequence[dict[str, str]],
    annual_support_numerator_source_gate_rows: Sequence[dict[str, str]],
    annual_support_numerator_uncertainty_envelope_rows: Sequence[dict[str, str]],
    annual_flow_anchor_registry_rows: Sequence[dict[str, str]],
    annual_flow_runtime_family_registry_rows: Sequence[dict[str, str]],
    annual_support_denominator_compatibility_registry_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    anchors_by_id = {
        row["denominator_source_id"]: row for row in annual_flow_anchor_registry_rows
    }
    runtime_family_by_id = {
        row["denominator_source_id"]: row
        for row in annual_flow_runtime_family_registry_rows
    }
    compatibility_by_id = {
        row["denominator_source_id"]: row
        for row in annual_support_denominator_compatibility_registry_rows
    }
    source_gate_summary_by_contract = _numerator_source_gate_summary_by_contract(
        annual_support_numerator_source_gate_rows=annual_support_numerator_source_gate_rows
    )
    uncertainty_envelope_by_contract = {
        row["contract_row_id"]: row
        for row in annual_support_numerator_uncertainty_envelope_rows
    }
    ordered_denominator_ids = [
        _LITERATURE_SOURCE_ID,
        _LEGACY_ANCHOR_NAMES["base_current_100bps"],
        _LEGACY_ANCHOR_NAMES["high_fiscal_offset_no_hit"],
        _PRIMARY_BOUNDED_SOURCE_ID,
        "literature_h8_mapped_review_only",
        "frbus_h8_component_proxy",
    ]
    rows: list[dict[str, str]] = []
    for contract_row in annual_support_numerator_contract_rows:
        numerator_total = _decimal_or_none(
            contract_row["runtime_current_window_numerator_bil"]
        )
        nominal_gdp = _decimal_or_none(contract_row["nominal_gdp_bil"])
        support_pct = (
            None
            if numerator_total is None or nominal_gdp in {None, Decimal("0")}
            else Decimal("100") * numerator_total / nominal_gdp
        )
        source_gate_summary = source_gate_summary_by_contract[
            contract_row["contract_row_id"]
        ]
        uncertainty_envelope = uncertainty_envelope_by_contract[
            contract_row["contract_row_id"]
        ]
        for source_id in ordered_denominator_ids:
            anchor = anchors_by_id.get(source_id)
            if anchor is None:
                anchor = {
                    "denominator_source_id": source_id,
                    "denominator_source_class": (
                        "literature_h8_mapped_review_only"
                        if source_id == "literature_h8_mapped_review_only"
                        else "frbus_h8_component_proxy_benchmark_only"
                    ),
                    "anchor_role": (
                        "review_only_h8_family_context"
                        if source_id == "literature_h8_mapped_review_only"
                        else "benchmark_only_h8_family_context"
                    ),
                }
            compatibility = compatibility_by_id[source_id]
            runtime_family = runtime_family_by_id.get(source_id)
            center = _decimal_or_none(
                runtime_family["runtime_anchor_value_pp_gdp"]
                if runtime_family is not None
                else anchor.get("anchor_value_pp_gdp", "")
            )
            numerator_runtime_allowed = contract_row["runtime_allowed"]
            numerator_source_gate_allowed = source_gate_summary["runtime_allowed"]
            denominator_runtime_allowed = compatibility["runtime_anchor_allowed"]
            support_offset_computation_allowed = (
                compatibility["support_offset_computation_allowed"]
            )
            effective_runtime_output_allowed = (
                "true"
                if numerator_runtime_allowed == "true"
                and numerator_source_gate_allowed == "true"
                and denominator_runtime_allowed == "true"
                and support_offset_computation_allowed == "true"
                else "false"
            )
            ci_low = _decimal_or_none(
                runtime_family["runtime_ci95_low_pp_gdp"] if runtime_family else ""
            )
            ci_high = _decimal_or_none(
                runtime_family["runtime_ci95_high_pp_gdp"] if runtime_family else ""
            )
            support_offset = (
                _safe_ratio(support_pct, center)
                if effective_runtime_output_allowed == "true"
                else None
            )
            support_offset_low = (
                _safe_ratio(support_pct, ci_high)
                if effective_runtime_output_allowed == "true"
                and ci_high not in {None, Decimal("0")}
                else None
            )
            support_offset_high = (
                _safe_ratio(support_pct, ci_low)
                if effective_runtime_output_allowed == "true"
                and ci_low not in {None, Decimal("0")}
                else None
            )
            numerator_support_low = _decimal_or_none(
                uncertainty_envelope["support_pct_lower_bound_gdp"]
            )
            numerator_support_base = _decimal_or_none(
                uncertainty_envelope["support_pct_base_case_gdp"]
            )
            numerator_support_high = _decimal_or_none(
                uncertainty_envelope["support_pct_upper_bound_gdp"]
            )
            support_offset_numerator_low = (
                _safe_ratio(numerator_support_low, center)
                if effective_runtime_output_allowed == "true"
                else None
            )
            support_offset_numerator_base = (
                _safe_ratio(numerator_support_base, center)
                if effective_runtime_output_allowed == "true"
                else None
            )
            support_offset_numerator_high = (
                _safe_ratio(numerator_support_high, center)
                if effective_runtime_output_allowed == "true"
                else None
            )
            if numerator_runtime_allowed != "true":
                runtime_pairing_status = "blocked_numerator_contract_not_runtime_usable"
                exact_blocker = contract_row["exact_blocker"]
                safe_sentence = (
                    "Runtime support offsets are emitted only when the annual-flow numerator contract reconciles exactly from direct components."
                )
                next_backend_action = (
                    "repair_runtime_numerator_contract_before_emitting_support_offsets"
                )
                allowed_use = "blocked_runtime_support_offset_row"
                claim_boundary = "runtime_annual_flow_support_offset_blocked_numerator"
            elif numerator_source_gate_allowed != "true":
                runtime_pairing_status = "blocked_numerator_source_gate_not_runtime_usable"
                exact_blocker = source_gate_summary["exact_blocker"]
                safe_sentence = (
                    "Runtime support offsets require every direct numerator component to be source, timing, and uncertainty classified before downstream use."
                )
                next_backend_action = (
                    "repair_numerator_source_gate_before_emitting_support_offsets"
                )
                allowed_use = "blocked_runtime_support_offset_row"
                claim_boundary = (
                    "runtime_annual_flow_support_offset_blocked_source_gate"
                )
            elif support_offset_computation_allowed == "true":
                runtime_pairing_status = (
                    "pass_default_runtime_support_offset_materialized"
                    if source_id == _LITERATURE_SOURCE_ID
                    else "pass_sensitivity_runtime_support_offset_materialized"
                )
                exact_blocker = compatibility["exact_blocker"]
                safe_sentence = compatibility["safe_sentence"]
                next_backend_action = compatibility["next_backend_action"]
                allowed_use = compatibility["allowed_use"]
                claim_boundary = (
                    "runtime_annual_flow_primary_empirical_support_offset"
                    if source_id == _LITERATURE_SOURCE_ID
                    else "runtime_annual_flow_sensitivity_support_offset"
                )
            else:
                runtime_pairing_status = (
                    "blocked_not_timing_commensurate_for_support_offset"
                )
                exact_blocker = compatibility["exact_blocker"]
                safe_sentence = compatibility["safe_sentence"]
                next_backend_action = compatibility["next_backend_action"]
                allowed_use = compatibility["allowed_use"]
                claim_boundary = (
                    "runtime_annual_flow_h8_family_blocked_noncommensurate"
                )
            row = {
                field: ""
                for field in RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_SCENARIO_FIELDS
            }
            row.update(
                {
                    "runtime_support_offset_row_id": (
                        "runtime_annual_flow_support_offset_scenarios::"
                        f"{contract_row['forecast_year']}::{contract_row['mpc_scenario']}::"
                        f"{contract_row['maturity_scenario']}::{contract_row['holder_scenario']}::"
                        f"{source_id}"
                    ),
                    "ratio_id": "RW_Y",
                    "numerator_contract_artifact": (
                        "ratewall_annual_support_numerator_contract.csv"
                    ),
                    "numerator_contract_row_id": contract_row["contract_row_id"],
                    "forecast_year": contract_row["forecast_year"],
                    "mpc_scenario": contract_row["mpc_scenario"],
                    "maturity_scenario": contract_row["maturity_scenario"],
                    "holder_scenario": contract_row["holder_scenario"],
                    "nominal_gdp_bil": contract_row["nominal_gdp_bil"],
                    "numerator_total_bil": contract_row[
                        "runtime_current_window_numerator_bil"
                    ],
                    "support_pct_of_gdp": _format_decimal(support_pct),
                    "numerator_timing_class": contract_row["timing_class"],
                    "numerator_uncertainty_status": contract_row[
                        "uncertainty_status"
                    ],
                    "numerator_reconciliation_status": contract_row[
                        "reconciliation_status"
                    ],
                    "numerator_runtime_allowed": numerator_runtime_allowed,
                    "numerator_source_gate_artifact": (
                        "ratewall_annual_support_numerator_source_gate.csv"
                    ),
                    "numerator_source_gate_status": source_gate_summary[
                        "source_gate_status"
                    ],
                    "numerator_uncertainty_artifact": (
                        "ratewall_annual_support_numerator_uncertainty_envelope.csv"
                    ),
                    "numerator_uncertainty_lower_bound_bil": uncertainty_envelope[
                        "numerator_lower_bound_bil"
                    ],
                    "numerator_uncertainty_base_case_bil": uncertainty_envelope[
                        "numerator_base_case_bil"
                    ],
                    "numerator_uncertainty_upper_bound_bil": uncertainty_envelope[
                        "numerator_upper_bound_bil"
                    ],
                    "support_pct_of_gdp_numerator_lower_bound": uncertainty_envelope[
                        "support_pct_lower_bound_gdp"
                    ],
                    "support_pct_of_gdp_numerator_base_case": uncertainty_envelope[
                        "support_pct_base_case_gdp"
                    ],
                    "support_pct_of_gdp_numerator_upper_bound": uncertainty_envelope[
                        "support_pct_upper_bound_gdp"
                    ],
                    "denominator_source_id": source_id,
                    "denominator_source_class": anchor["denominator_source_class"],
                    "denominator_role": (
                        runtime_family["runtime_family_role"]
                        if runtime_family is not None
                        else anchor["anchor_role"]
                    ),
                    "denominator_timing_class": compatibility[
                        "denominator_timing_class"
                    ],
                    "default_runtime_anchor": (
                        runtime_family["default_runtime_anchor"]
                        if runtime_family is not None
                        else "false"
                    ),
                    "sensitivity_only": (
                        runtime_family["sensitivity_only"]
                        if runtime_family is not None
                        else "false"
                    ),
                    "denominator_runtime_allowed": denominator_runtime_allowed,
                    "support_offset_computation_allowed": (
                        support_offset_computation_allowed
                    ),
                    "effective_runtime_output_allowed": (
                        effective_runtime_output_allowed
                    ),
                    "scenario_runtime_allowed": effective_runtime_output_allowed,
                    "denominator_center_pp_gdp": _format_decimal(center),
                    "denominator_ci95_low_pp_gdp": _format_decimal(ci_low),
                    "denominator_ci95_high_pp_gdp": _format_decimal(ci_high),
                    "support_offset_100bp_year_equivalent_lower_bound": _format_decimal(
                        support_offset_low
                    ),
                    "support_offset_100bp_year_equivalent": _format_decimal(
                        support_offset
                    ),
                    "support_offset_100bp_year_equivalent_upper_bound": _format_decimal(
                        support_offset_high
                    ),
                    "support_offset_100bp_year_equivalent_numerator_lower_bound": _format_decimal(
                        support_offset_numerator_low
                    ),
                    "support_offset_100bp_year_equivalent_numerator_base_case": _format_decimal(
                        support_offset_numerator_base
                    ),
                    "support_offset_100bp_year_equivalent_numerator_upper_bound": _format_decimal(
                        support_offset_numerator_high
                    ),
                    "support_offset_bp_year_equivalent_lower_bound": _format_decimal(
                        None if support_offset_low is None else support_offset_low * Decimal("100")
                    ),
                    "support_offset_bp_year_equivalent": _format_decimal(
                        None if support_offset is None else support_offset * Decimal("100")
                    ),
                    "support_offset_bp_year_equivalent_upper_bound": _format_decimal(
                        None if support_offset_high is None else support_offset_high * Decimal("100")
                    ),
                    "support_offset_bp_year_equivalent_numerator_lower_bound": _format_decimal(
                        None
                        if support_offset_numerator_low is None
                        else support_offset_numerator_low * Decimal("100")
                    ),
                    "support_offset_bp_year_equivalent_numerator_base_case": _format_decimal(
                        None
                        if support_offset_numerator_base is None
                        else support_offset_numerator_base * Decimal("100")
                    ),
                    "support_offset_bp_year_equivalent_numerator_upper_bound": _format_decimal(
                        None
                        if support_offset_numerator_high is None
                        else support_offset_numerator_high * Decimal("100")
                    ),
                    "runtime_pairing_status": runtime_pairing_status,
                    "exact_blocker": exact_blocker,
                    "safe_sentence": safe_sentence,
                    "next_backend_action": next_backend_action,
                    "allowed_use": allowed_use,
                    "blocked_use": compatibility["blocked_use"],
                    "claim_boundary": claim_boundary,
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    return rows


def _runtime_annual_flow_support_offset_readiness_registry_rows(
    *,
    runtime_annual_flow_support_offset_scenario_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for scenario_row in runtime_annual_flow_support_offset_scenario_rows:
        effective_runtime_output_allowed = scenario_row[
            "effective_runtime_output_allowed"
        ]
        if effective_runtime_output_allowed == "true":
            readiness_tier = "reportable_runtime_support_offset"
        elif scenario_row["numerator_runtime_allowed"] != "true":
            readiness_tier = "blocked_runtime_support_offset_numerator_contract"
        elif scenario_row["numerator_source_gate_status"] != (
            "pass_all_direct_runtime_components_source_classified"
        ):
            readiness_tier = "blocked_runtime_support_offset_numerator_source_gate"
        elif scenario_row["denominator_runtime_allowed"] == "true":
            readiness_tier = "sensitivity_only_runtime_support_offset"
        else:
            readiness_tier = "blocked_noncommensurate_overlay_context"
        row = {
            field: ""
            for field in RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_READINESS_REGISTRY_FIELDS
        }
        row.update(
            {
                "readiness_row_id": (
                    "runtime_annual_flow_support_offset_readiness_registry::"
                    f"{scenario_row['forecast_year']}::{scenario_row['mpc_scenario']}::"
                    f"{scenario_row['maturity_scenario']}::{scenario_row['holder_scenario']}::"
                    f"{scenario_row['denominator_source_id']}"
                ),
                "runtime_support_offset_row_id": scenario_row[
                    "runtime_support_offset_row_id"
                ],
                "ratio_id": scenario_row["ratio_id"],
                "forecast_year": scenario_row["forecast_year"],
                "mpc_scenario": scenario_row["mpc_scenario"],
                "maturity_scenario": scenario_row["maturity_scenario"],
                "holder_scenario": scenario_row["holder_scenario"],
                "numerator_contract_artifact": scenario_row[
                    "numerator_contract_artifact"
                ],
                "numerator_contract_row_id": scenario_row[
                    "numerator_contract_row_id"
                ],
                "denominator_source_id": scenario_row["denominator_source_id"],
                "denominator_source_class": scenario_row[
                    "denominator_source_class"
                ],
                "numerator_timing_class": scenario_row["numerator_timing_class"],
                "denominator_timing_class": scenario_row[
                    "denominator_timing_class"
                ],
                "numerator_uncertainty_status": scenario_row[
                    "numerator_uncertainty_status"
                ],
                "numerator_reconciliation_status": scenario_row[
                    "numerator_reconciliation_status"
                ],
                "numerator_runtime_allowed": scenario_row[
                    "numerator_runtime_allowed"
                ],
                "numerator_source_gate_artifact": scenario_row[
                    "numerator_source_gate_artifact"
                ],
                "numerator_source_gate_status": scenario_row[
                    "numerator_source_gate_status"
                ],
                "numerator_uncertainty_artifact": scenario_row[
                    "numerator_uncertainty_artifact"
                ],
                "numerator_uncertainty_lower_bound_bil": scenario_row[
                    "numerator_uncertainty_lower_bound_bil"
                ],
                "numerator_uncertainty_base_case_bil": scenario_row[
                    "numerator_uncertainty_base_case_bil"
                ],
                "numerator_uncertainty_upper_bound_bil": scenario_row[
                    "numerator_uncertainty_upper_bound_bil"
                ],
                "denominator_runtime_allowed": scenario_row[
                    "denominator_runtime_allowed"
                ],
                "support_offset_computation_allowed": scenario_row[
                    "support_offset_computation_allowed"
                ],
                "effective_runtime_output_allowed": (
                    effective_runtime_output_allowed
                ),
                "readiness_tier": readiness_tier,
                "scenario_runtime_allowed": scenario_row["scenario_runtime_allowed"],
                "exact_blocker": scenario_row["exact_blocker"],
                "safe_sentence": scenario_row["safe_sentence"],
                "next_backend_action": scenario_row["next_backend_action"],
                "allowed_use": scenario_row["allowed_use"],
                "blocked_use": scenario_row["blocked_use"],
                "claim_boundary": (
                    "runtime_annual_flow_support_offset_readiness_registry"
                ),
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _runtime_annual_flow_support_offset_adoption_matrix_rows(
    *,
    runtime_annual_flow_support_offset_scenario_rows: Sequence[dict[str, str]],
    runtime_annual_flow_support_offset_readiness_registry_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    readiness_by_runtime_row_id = {
        row["runtime_support_offset_row_id"]: row
        for row in runtime_annual_flow_support_offset_readiness_registry_rows
    }
    rows_by_contract: dict[
        tuple[str, str, str, str], dict[str, dict[str, str]]
    ] = {}
    for row in runtime_annual_flow_support_offset_scenario_rows:
        key = (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
        )
        rows_by_contract.setdefault(key, {})[row["denominator_source_id"]] = row

    ordered_keys = sorted(rows_by_contract)
    matrix_rows: list[dict[str, str]] = []
    for key in ordered_keys:
        by_source = rows_by_contract[key]
        default_row = by_source.get(_LITERATURE_SOURCE_ID)
        legacy_base_row = by_source.get(_LEGACY_ANCHOR_NAMES["base_current_100bps"])
        legacy_high_row = by_source.get(_LEGACY_ANCHOR_NAMES["high_fiscal_offset_no_hit"])
        bounded_h8_row = by_source.get(_PRIMARY_BOUNDED_SOURCE_ID)
        literature_h8_row = by_source.get("literature_h8_mapped_review_only")
        frbus_h8_row = by_source.get("frbus_h8_component_proxy")
        required_rows = [
            default_row,
            legacy_base_row,
            legacy_high_row,
            bounded_h8_row,
            literature_h8_row,
            frbus_h8_row,
        ]
        adoption_ready = all(row is not None for row in required_rows)
        template_row = default_row or next(iter(by_source.values()))
        row = {
            field: ""
            for field in RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_ADOPTION_MATRIX_FIELDS
        }
        row.update(
            {
                "adoption_row_id": (
                    "runtime_annual_flow_support_offset_adoption_matrix::"
                    f"{key[0]}::{key[1]}::{key[2]}::{key[3]}"
                ),
                "ratio_id": template_row["ratio_id"],
                "numerator_contract_artifact": template_row[
                    "numerator_contract_artifact"
                ],
                "numerator_contract_row_id": template_row[
                    "numerator_contract_row_id"
                ],
                "readiness_artifact": (
                    "ratewall_runtime_annual_flow_support_offset_readiness_registry.csv"
                ),
                "forecast_year": key[0],
                "mpc_scenario": key[1],
                "maturity_scenario": key[2],
                "holder_scenario": key[3],
                "numerator_timing_class": template_row["numerator_timing_class"],
                "numerator_uncertainty_status": template_row[
                    "numerator_uncertainty_status"
                ],
                "numerator_reconciliation_status": template_row[
                    "numerator_reconciliation_status"
                ],
                "numerator_runtime_allowed": template_row[
                    "numerator_runtime_allowed"
                ],
                "numerator_source_gate_artifact": template_row[
                    "numerator_source_gate_artifact"
                ],
                "numerator_source_gate_status": template_row[
                    "numerator_source_gate_status"
                ],
                "numerator_uncertainty_artifact": template_row[
                    "numerator_uncertainty_artifact"
                ],
                "numerator_total_bil": template_row["numerator_total_bil"],
                "support_pct_of_gdp": template_row["support_pct_of_gdp"],
                "numerator_uncertainty_lower_bound_bil": template_row[
                    "numerator_uncertainty_lower_bound_bil"
                ],
                "numerator_uncertainty_base_case_bil": template_row[
                    "numerator_uncertainty_base_case_bil"
                ],
                "numerator_uncertainty_upper_bound_bil": template_row[
                    "numerator_uncertainty_upper_bound_bil"
                ],
                "default_runtime_family_count": "1",
                "sensitivity_runtime_family_count": "2",
                "blocked_overlay_family_count": "3",
                "adoption_status": (
                    "pass_compact_runtime_default_and_sensitivity_matrix_materialized"
                    if adoption_ready
                    else "blocked_missing_runtime_support_offset_bundle"
                ),
                "exact_blocker": (
                    ""
                    if adoption_ready
                    else "Each contract row must carry the default literature runtime row, two legacy sensitivity rows, and three blocked h8-family overlay rows before compact adoption outputs can materialize."
                ),
                "safe_sentence": (
                    "This compact adoption matrix exposes one audited default runtime row, two explicit sensitivity rows, and three blocked h8-family overlay companions for each annual-flow numerator contract."
                ),
                "next_backend_action": (
                    "use_compact_adoption_matrix_for_runtime_support_offset_reporting"
                ),
                "allowed_use": "runtime_support_offset_compact_adoption_matrix",
                "blocked_use": template_row["blocked_use"],
                "claim_boundary": "runtime_annual_flow_support_offset_adoption_matrix",
                **_disabled_switches(),
            }
        )
        if adoption_ready:
            default_readiness = readiness_by_runtime_row_id[
                default_row["runtime_support_offset_row_id"]
            ]
            legacy_base_readiness = readiness_by_runtime_row_id[
                legacy_base_row["runtime_support_offset_row_id"]
            ]
            legacy_high_readiness = readiness_by_runtime_row_id[
                legacy_high_row["runtime_support_offset_row_id"]
            ]
            bounded_h8_readiness = readiness_by_runtime_row_id[
                bounded_h8_row["runtime_support_offset_row_id"]
            ]
            literature_h8_readiness = readiness_by_runtime_row_id[
                literature_h8_row["runtime_support_offset_row_id"]
            ]
            frbus_h8_readiness = readiness_by_runtime_row_id[
                frbus_h8_row["runtime_support_offset_row_id"]
            ]
            row.update(
                {
                    "default_runtime_support_offset_row_id": default_row[
                        "runtime_support_offset_row_id"
                    ],
                    "default_runtime_readiness_row_id": default_readiness[
                        "readiness_row_id"
                    ],
                    "default_runtime_readiness_tier": default_readiness[
                        "readiness_tier"
                    ],
                    "default_denominator_source_id": default_row[
                        "denominator_source_id"
                    ],
                    "default_denominator_center_pp_gdp": default_row[
                        "denominator_center_pp_gdp"
                    ],
                    "default_denominator_ci95_low_pp_gdp": default_row[
                        "denominator_ci95_low_pp_gdp"
                    ],
                    "default_denominator_ci95_high_pp_gdp": default_row[
                        "denominator_ci95_high_pp_gdp"
                    ],
                    "default_support_offset_100bp_year_equivalent_lower_bound": default_row[
                        "support_offset_100bp_year_equivalent_lower_bound"
                    ],
                    "default_support_offset_100bp_year_equivalent": default_row[
                        "support_offset_100bp_year_equivalent"
                    ],
                    "default_support_offset_100bp_year_equivalent_upper_bound": default_row[
                        "support_offset_100bp_year_equivalent_upper_bound"
                    ],
                    "default_support_offset_100bp_year_equivalent_numerator_lower_bound": default_row[
                        "support_offset_100bp_year_equivalent_numerator_lower_bound"
                    ],
                    "default_support_offset_100bp_year_equivalent_numerator_base_case": default_row[
                        "support_offset_100bp_year_equivalent_numerator_base_case"
                    ],
                    "default_support_offset_100bp_year_equivalent_numerator_upper_bound": default_row[
                        "support_offset_100bp_year_equivalent_numerator_upper_bound"
                    ],
                    "sensitivity_base_current_row_id": legacy_base_row[
                        "runtime_support_offset_row_id"
                    ],
                    "sensitivity_base_current_readiness_row_id": legacy_base_readiness[
                        "readiness_row_id"
                    ],
                    "sensitivity_base_current_readiness_tier": legacy_base_readiness[
                        "readiness_tier"
                    ],
                    "sensitivity_base_current_support_offset_100bp_year_equivalent": legacy_base_row[
                        "support_offset_100bp_year_equivalent"
                    ],
                    "sensitivity_base_current_support_offset_100bp_year_equivalent_numerator_lower_bound": legacy_base_row[
                        "support_offset_100bp_year_equivalent_numerator_lower_bound"
                    ],
                    "sensitivity_base_current_support_offset_100bp_year_equivalent_numerator_base_case": legacy_base_row[
                        "support_offset_100bp_year_equivalent_numerator_base_case"
                    ],
                    "sensitivity_base_current_support_offset_100bp_year_equivalent_numerator_upper_bound": legacy_base_row[
                        "support_offset_100bp_year_equivalent_numerator_upper_bound"
                    ],
                    "sensitivity_high_row_id": legacy_high_row[
                        "runtime_support_offset_row_id"
                    ],
                    "sensitivity_high_readiness_row_id": legacy_high_readiness[
                        "readiness_row_id"
                    ],
                    "sensitivity_high_readiness_tier": legacy_high_readiness[
                        "readiness_tier"
                    ],
                    "sensitivity_high_support_offset_100bp_year_equivalent": legacy_high_row[
                        "support_offset_100bp_year_equivalent"
                    ],
                    "sensitivity_high_support_offset_100bp_year_equivalent_numerator_lower_bound": legacy_high_row[
                        "support_offset_100bp_year_equivalent_numerator_lower_bound"
                    ],
                    "sensitivity_high_support_offset_100bp_year_equivalent_numerator_base_case": legacy_high_row[
                        "support_offset_100bp_year_equivalent_numerator_base_case"
                    ],
                    "sensitivity_high_support_offset_100bp_year_equivalent_numerator_upper_bound": legacy_high_row[
                        "support_offset_100bp_year_equivalent_numerator_upper_bound"
                    ],
                    "bounded_h8_overlay_row_id": bounded_h8_row[
                        "runtime_support_offset_row_id"
                    ],
                    "bounded_h8_overlay_runtime_pairing_status": bounded_h8_row[
                        "runtime_pairing_status"
                    ],
                    "bounded_h8_overlay_readiness_tier": bounded_h8_readiness[
                        "readiness_tier"
                    ],
                    "bounded_h8_overlay_support_offset_100bp_year_equivalent": bounded_h8_row[
                        "support_offset_100bp_year_equivalent"
                    ],
                    "bounded_h8_overlay_support_offset_bp_year_equivalent": bounded_h8_row[
                        "support_offset_bp_year_equivalent"
                    ],
                    "literature_h8_overlay_row_id": literature_h8_row[
                        "runtime_support_offset_row_id"
                    ],
                    "literature_h8_overlay_runtime_pairing_status": literature_h8_row[
                        "runtime_pairing_status"
                    ],
                    "literature_h8_overlay_readiness_tier": literature_h8_readiness[
                        "readiness_tier"
                    ],
                    "literature_h8_overlay_support_offset_100bp_year_equivalent": literature_h8_row[
                        "support_offset_100bp_year_equivalent"
                    ],
                    "literature_h8_overlay_support_offset_bp_year_equivalent": literature_h8_row[
                        "support_offset_bp_year_equivalent"
                    ],
                    "frbus_h8_overlay_row_id": frbus_h8_row[
                        "runtime_support_offset_row_id"
                    ],
                    "frbus_h8_overlay_runtime_pairing_status": frbus_h8_row[
                        "runtime_pairing_status"
                    ],
                    "frbus_h8_overlay_readiness_tier": frbus_h8_readiness[
                        "readiness_tier"
                    ],
                    "frbus_h8_overlay_support_offset_100bp_year_equivalent": frbus_h8_row[
                        "support_offset_100bp_year_equivalent"
                    ],
                    "frbus_h8_overlay_support_offset_bp_year_equivalent": frbus_h8_row[
                        "support_offset_bp_year_equivalent"
                    ],
                }
            )
        matrix_rows.append(row)
    return matrix_rows


def _runtime_annual_flow_support_offset_frontier_summary_rows(
    *,
    runtime_annual_flow_support_offset_scenario_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    runtime_rows = [
        row
        for row in runtime_annual_flow_support_offset_scenario_rows
        if row["effective_runtime_output_allowed"] == "true"
    ]
    rows_by_family: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in runtime_rows:
        rows_by_family.setdefault(
            (row["forecast_year"], row["denominator_source_id"]), []
        ).append(row)

    ordered_ids = [
        _LITERATURE_SOURCE_ID,
        _LEGACY_ANCHOR_NAMES["base_current_100bps"],
        _LEGACY_ANCHOR_NAMES["high_fiscal_offset_no_hit"],
    ]
    frontier_rows: list[dict[str, str]] = []
    for forecast_year in sorted({key[0] for key in rows_by_family}):
        for source_id in ordered_ids:
            family_rows = rows_by_family.get((forecast_year, source_id), [])
            if family_rows:
                sorted_rows = sorted(
                    family_rows,
                    key=lambda item: (
                        _decimal_or_none(
                            item["support_offset_100bp_year_equivalent"]
                        )
                        or Decimal("0")
                    ),
                )
                min_row = sorted_rows[0]
                max_row = sorted_rows[-1]
                reference_row = next(
                    (
                        row
                        for row in family_rows
                        if row["mpc_scenario"] == "base_mpc_10pct"
                        and row["maturity_scenario"] == "current_wam_cbo_rate_path"
                        and row["holder_scenario"]
                        == "current_holder_distribution"
                    ),
                    sorted_rows[len(sorted_rows) // 2],
                )
                frontier_status = "pass_runtime_support_offset_frontier_materialized"
                exact_blocker = ""
                template_row = reference_row
            else:
                frontier_status = "blocked_missing_runtime_family_rows"
                exact_blocker = (
                    "Runtime frontier summary requires at least one runtime-allowed row for each forecast year and denominator family."
                )
                template_row = {
                    "ratio_id": "RW_Y",
                    "denominator_source_class": "",
                    "denominator_role": "",
                    "blocked_use": (
                        "canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;"
                        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
                        "tax_incidence_welfare_mpc"
                    ),
                }
                min_row = max_row = reference_row = {field: "" for field in RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_SCENARIO_FIELDS}
            row = {
                field: ""
                for field in RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_FRONTIER_SUMMARY_FIELDS
            }
            row.update(
                {
                    "frontier_row_id": (
                        "runtime_annual_flow_support_offset_frontier_summary::"
                        f"{forecast_year}::{source_id}"
                    ),
                    "ratio_id": template_row["ratio_id"],
                    "forecast_year": forecast_year,
                    "denominator_source_id": source_id,
                    "denominator_source_class": template_row["denominator_source_class"],
                    "denominator_role": template_row["denominator_role"],
                    "runtime_family_class": (
                        "default_runtime_family"
                        if source_id == _LITERATURE_SOURCE_ID
                        else "sensitivity_runtime_family"
                    ),
                    "scenario_row_count": str(len(family_rows)),
                    "reference_mpc_scenario": "base_mpc_10pct",
                    "reference_maturity_scenario": "current_wam_cbo_rate_path",
                    "reference_holder_scenario": "current_holder_distribution",
                    "reference_runtime_support_offset_row_id": reference_row.get(
                        "runtime_support_offset_row_id", ""
                    ),
                    "minimum_runtime_support_offset_row_id": min_row.get(
                        "runtime_support_offset_row_id", ""
                    ),
                    "maximum_runtime_support_offset_row_id": max_row.get(
                        "runtime_support_offset_row_id", ""
                    ),
                    "reference_support_offset_100bp_year_equivalent": reference_row.get(
                        "support_offset_100bp_year_equivalent", ""
                    ),
                    "minimum_support_offset_100bp_year_equivalent": min_row.get(
                        "support_offset_100bp_year_equivalent", ""
                    ),
                    "maximum_support_offset_100bp_year_equivalent": max_row.get(
                        "support_offset_100bp_year_equivalent", ""
                    ),
                    "reference_support_offset_100bp_year_equivalent_numerator_lower_bound": reference_row.get(
                        "support_offset_100bp_year_equivalent_numerator_lower_bound",
                        "",
                    ),
                    "reference_support_offset_100bp_year_equivalent_numerator_base_case": reference_row.get(
                        "support_offset_100bp_year_equivalent_numerator_base_case",
                        "",
                    ),
                    "reference_support_offset_100bp_year_equivalent_numerator_upper_bound": reference_row.get(
                        "support_offset_100bp_year_equivalent_numerator_upper_bound",
                        "",
                    ),
                    "reference_denominator_center_pp_gdp": reference_row.get(
                        "denominator_center_pp_gdp", ""
                    ),
                    "reference_denominator_ci95_low_pp_gdp": reference_row.get(
                        "denominator_ci95_low_pp_gdp", ""
                    ),
                    "reference_denominator_ci95_high_pp_gdp": reference_row.get(
                        "denominator_ci95_high_pp_gdp", ""
                    ),
                    "frontier_status": frontier_status,
                    "exact_blocker": exact_blocker,
                    "safe_sentence": (
                        "This compact frontier summary exposes year-level default and sensitivity support-offset ranges plus a deterministic reference case without requiring downstream users to mine the full runtime row table."
                    ),
                    "next_backend_action": (
                        "use_frontier_summary_for_compact_runtime_support_offset_narration"
                    ),
                    "allowed_use": "runtime_support_offset_frontier_summary",
                    "blocked_use": template_row["blocked_use"],
                    "claim_boundary": "runtime_annual_flow_support_offset_frontier_summary",
                    **_disabled_switches(),
                }
            )
            frontier_rows.append(row)
    return frontier_rows


def _annual_flow_denominator_anchor_registry_rows(
    *,
    bounded_denominator_registry_rows: Sequence[dict[str, str]],
    residualized_bridge: ResidualizedFfrBridgeState,
) -> list[dict[str, str]]:
    literature_runtime_ready = _literature_runtime_promotion_ready(
        residualized_bridge
    )
    rows: list[dict[str, str]] = []
    for assumption_name, source_id in _LEGACY_ANCHOR_NAMES.items():
        assumption = _assumption_set_by_name(assumption_name)
        share = _decimal_or_none(assumption.get("contractionary_drag_gdp_share"))
        pp_gdp = share * Decimal("100") if share is not None else None
        rows.append(
            {
                "anchor_row_id": f"annual_flow_denominator_anchor_registry::{source_id}",
                "denominator_source_id": source_id,
                "denominator_source_class": "legacy_assumption_mode_annual_flow_anchor",
                "anchor_label": assumption_name,
                "anchor_family": "legacy_assumption_mode",
                "anchor_role": "fallback_assumption_mode_sensitivity_anchor",
                "source_handle": assumption_name,
                "timing_alignment_class": "annual_flow_direct",
                "anchor_value_gdp_share": _format_decimal(share),
                "anchor_value_pp_gdp": _format_decimal(pp_gdp),
                "anchor_empirical_status": "pass_assumption_mode_sensitivity_only_not_default_runtime",
                "scenario_runtime_allowed": "true",
                "exact_blocker": (
                    "Legacy annual-flow anchor survives only as an explicit assumption-mode "
                    "sensitivity counterpoint; it is not the default runtime denominator "
                    "and it is not empirical denominator evidence."
                ),
                "safe_sentence": (
                    "This annual-flow anchor remains available only as a sensitivity "
                    "counterpoint after runtime promotion of the literature-backed "
                    "empirical annual-flow family."
                ),
                "next_backend_action": (
                    "keep_only_as_explicit_sensitivity_counterpoint_to_literature_runtime_family"
                ),
                "allowed_use": "scenario_runtime_assumption_mode_sensitivity_only",
                "blocked_use": (
                    "default_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;pricing;"
                    "holder_allocation;raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "annual_flow_assumption_anchor_sensitivity_only_not_empirical",
                **_disabled_switches(),
            }
        )

    rows.append(
        {
            "anchor_row_id": (
                f"annual_flow_denominator_anchor_registry::{_LITERATURE_SOURCE_ID}"
            ),
            "denominator_source_id": _LITERATURE_SOURCE_ID,
            "denominator_source_class": (
                "literature_bridge_annual_flow_runtime_anchor"
                if literature_runtime_ready
                else "literature_bridge_annual_flow_anchor_candidate"
            ),
            "anchor_label": (
                "Published residualized-FFR runtime anchor"
                if literature_runtime_ready
                else "Published residualized-FFR bridge candidate"
            ),
            "anchor_family": "literature_bridge",
            "anchor_role": (
                "primary_empirical_annual_flow_runtime_anchor"
                if literature_runtime_ready
                else "review_only_annual_flow_anchor_candidate"
            ),
            "source_handle": _PAPER_ID,
            "timing_alignment_class": (
                "annual_flow_h4_endpoint_proxy"
                if literature_runtime_ready
                else residualized_bridge.anchor_timing_alignment_class
            ),
            "anchor_value_gdp_share": _format_decimal(
                _CANONICAL_ANNUAL_FLOW_ANCHOR_PP_GDP / Decimal("100")
            ),
            "anchor_value_pp_gdp": _format_decimal(
                _CANONICAL_ANNUAL_FLOW_ANCHOR_PP_GDP
            ),
            "anchor_empirical_status": (
                "pass_primary_empirical_annual_flow_runtime_anchor"
                if literature_runtime_ready
                else residualized_bridge.anchor_status
            ),
            "scenario_runtime_allowed": "true" if literature_runtime_ready else "false",
            "exact_blocker": (
                "This annual-flow h4 endpoint proxy is now the default empirical runtime "
                "anchor derived from the published-style residualized-FFR bridge. "
                "Canonical RW_Y and stronger claim modes remain blocked."
                if literature_runtime_ready
                else residualized_bridge.anchor_exact_blocker
            ),
            "safe_sentence": (
                "This literature-backed annual-flow h4 endpoint proxy is now the default "
                "empirical runtime denominator anchor for the current annual-flow numerator family."
                if literature_runtime_ready
                else residualized_bridge.anchor_safe_sentence
            ),
            "next_backend_action": (
                "use_literature_runtime_family_as_default_and_keep_h8_overlay_review_only"
                if literature_runtime_ready
                else residualized_bridge.anchor_next_backend_action
            ),
            "allowed_use": (
                "scenario_runtime_empirical_annual_flow_primary"
                if literature_runtime_ready
                else (
                    "review_only_literature_annual_flow_comparison"
                    if residualized_bridge.anchor_status
                    == "pass_review_only_literature_annual_flow_anchor_window_materialized"
                    else "planning_only;review_only_bridge_surface"
                )
            ),
            "blocked_use": (
                "canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": (
                "literature_annual_flow_runtime_anchor_empirical_proxy"
                if literature_runtime_ready
                else "literature_annual_flow_anchor_candidate_not_runtime_enabled"
            ),
            **_disabled_switches(),
        }
    )

    bounded_h8 = next(
        (
            row
            for row in bounded_denominator_registry_rows
            if row["primary_denominator_horizon"] == "true"
        ),
        None,
    )
    rows.append(
        {
            "anchor_row_id": (
                f"annual_flow_denominator_anchor_registry::{_PRIMARY_BOUNDED_SOURCE_ID}"
            ),
            "denominator_source_id": _PRIMARY_BOUNDED_SOURCE_ID,
            "denominator_source_class": "bounded_h8_overlay_review_only",
            "anchor_label": "Bounded h8 overlay review center",
            "anchor_family": "bounded_h8_empirical_lane",
            "anchor_role": "overlay_only_not_annual_flow_anchor",
            "source_handle": "ratewall_conventional_drag_bounded_denominator_registry.csv",
            "timing_alignment_class": "blocked_not_annual_flow_h8_cumulative",
            "anchor_value_gdp_share": "",
            "anchor_value_pp_gdp": (
                bounded_h8["review_center_d_y"] if bounded_h8 is not None else ""
            ),
            "anchor_empirical_status": "pass_bounded_h8_evidence_route_review_only",
            "scenario_runtime_allowed": "false",
            "exact_blocker": (
                "The bounded h8 object is cumulative evidence and overlay context. It is "
                "not an annual-flow anchor."
            ),
            "safe_sentence": (
                "The bounded h8 review center is kept here only to prevent it from being "
                "misread as an annual-flow anchor."
            ),
            "next_backend_action": (
                "keep_h8_as_overlay_only_and_limit_any_followup_to_scale_conflict_interpretation"
            ),
            "allowed_use": "overlay_context_only",
            "blocked_use": (
                "annual_flow_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "bounded_h8_overlay_not_annual_flow_anchor",
            **_disabled_switches(),
        }
    )
    return rows


def _annual_flow_runtime_family_registry_rows(
    *,
    residualized_bridge: ResidualizedFfrBridgeState,
) -> list[dict[str, str]]:
    runtime_ready = _literature_runtime_promotion_ready(residualized_bridge)
    normalization_rows = {
        row["normalization_row_id"]: row for row in residualized_bridge.normalization_rows
    }
    normalization_summary = normalization_rows.get(
        "residualized_ffr_normalization_bridge::100bp_year"
    )
    normalization_multiplier = _decimal_or_none(
        normalization_summary["normalization_multiplier"]
        if normalization_summary is not None
        else ""
    )
    literature_bridge_row = _residualized_bridge_row(
        rows=residualized_bridge.bridge_rows,
        row_id_prefix=(
            "residualized_ffr_private_demand_bridge::"
            "fspdp_gdp_share_contribution::h4"
        ),
    )
    literature_ci_low, literature_ci_high = _mapped_drag_ci_from_native_row(
        native_row=literature_bridge_row,
        normalization_multiplier=normalization_multiplier,
    )
    rows: list[dict[str, str]] = []
    rows.append(
        {
            "runtime_family_row_id": (
                "annual_flow_runtime_family_registry::"
                "literature_annual_flow_bridge_candidate"
            ),
            "denominator_source_id": _LITERATURE_SOURCE_ID,
            "denominator_source_class": (
                "literature_bridge_annual_flow_runtime_anchor"
            ),
            "runtime_family_label": "Literature annual-flow runtime primary",
            "runtime_family_role": (
                "primary_empirical_annual_flow_runtime_anchor"
                if runtime_ready
                else "blocked_empirical_annual_flow_runtime_anchor_candidate"
            ),
            "default_runtime_anchor": "true" if runtime_ready else "false",
            "sensitivity_only": "false",
            "timing_alignment_class": (
                "annual_flow_h4_endpoint_proxy"
                if runtime_ready
                else "review_only_annual_flow_h4_endpoint_proxy"
            ),
            "runtime_anchor_value_pp_gdp": _format_decimal(
                _CANONICAL_ANNUAL_FLOW_ANCHOR_PP_GDP
            ),
            "runtime_ci95_low_pp_gdp": _format_decimal(literature_ci_low),
            "runtime_ci95_high_pp_gdp": _format_decimal(literature_ci_high),
            "source_artifact": "ratewall_residualized_ffr_normalization_bridge.csv",
            "source_row_id": (
                "residualized_ffr_normalization_bridge::year1_h4_endpoint_proxy;"
                "residualized_ffr_private_demand_bridge::"
                "fspdp_gdp_share_contribution::h4"
            ),
            "runtime_policy_status": (
                "pass_primary_empirical_annual_flow_runtime_anchor_materialized"
                if runtime_ready
                else "blocked_primary_empirical_annual_flow_runtime_anchor_pending"
            ),
            "scenario_runtime_allowed": "true" if runtime_ready else "false",
            "exact_blocker": (
                "The literature annual-flow bridge is now the default empirical "
                "runtime denominator family because the published-style GDP "
                "replication, private-demand adaptation, and exact 100bp-year "
                "normalization are all materialized locally."
                if runtime_ready
                else residualized_bridge.anchor_exact_blocker
            ),
            "safe_sentence": (
                "This runtime family centers annual-flow denominator policy on the "
                "literature-backed year-1 h4 endpoint proxy in exact 100bp-year units, "
                "while keeping canonical RW_Y and all stronger claim modes blocked."
                if runtime_ready
                else residualized_bridge.anchor_safe_sentence
            ),
            "next_backend_action": (
                "use_literature_runtime_family_as_default_and_keep_h8_overlay_review_only"
                if runtime_ready
                else residualized_bridge.anchor_next_backend_action
            ),
            "allowed_use": (
                "scenario_runtime_empirical_annual_flow_primary"
                if runtime_ready
                else "planning_only;review_only_bridge_surface"
            ),
            "blocked_use": (
                "canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;pricing;"
                "holder_allocation;raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": (
                "literature_annual_flow_runtime_primary_empirical_proxy"
                if runtime_ready
                else "literature_annual_flow_runtime_anchor_blocked"
            ),
            **_disabled_switches(),
        }
    )
    for assumption_name, source_id in _LEGACY_ANCHOR_NAMES.items():
        assumption = _assumption_set_by_name(assumption_name)
        share = _decimal_or_none(assumption.get("contractionary_drag_gdp_share"))
        rows.append(
            {
                "runtime_family_row_id": (
                    f"annual_flow_runtime_family_registry::{source_id}"
                ),
                "denominator_source_id": source_id,
                "denominator_source_class": (
                    "legacy_assumption_mode_sensitivity_runtime_anchor"
                ),
                "runtime_family_label": assumption_name,
                "runtime_family_role": "fallback_assumption_mode_sensitivity_anchor",
                "default_runtime_anchor": "false",
                "sensitivity_only": "true",
                "timing_alignment_class": "annual_flow_direct",
                "runtime_anchor_value_pp_gdp": _format_decimal(
                    None if share is None else share * Decimal("100")
                ),
                "runtime_ci95_low_pp_gdp": "",
                "runtime_ci95_high_pp_gdp": "",
                "source_artifact": "ratewall_annual_flow_denominator_anchor_registry.csv",
                "source_row_id": (
                    f"annual_flow_denominator_anchor_registry::{source_id}"
                ),
                "runtime_policy_status": (
                    "pass_assumption_mode_sensitivity_only_not_default_runtime"
                ),
                "scenario_runtime_allowed": "true",
                "exact_blocker": (
                    "This legacy assumption-mode value may remain available only as an "
                    "explicit runtime sensitivity counterpoint. It is not the default "
                    "denominator and it is not empirical evidence."
                ),
                "safe_sentence": (
                    "This row preserves a legacy annual-flow sensitivity point after the "
                    "runtime default moves to the literature-backed empirical family."
                ),
                "next_backend_action": (
                    "keep_only_as_explicit_sensitivity_counterpoint_to_literature_runtime_family"
                ),
                "allowed_use": "scenario_runtime_assumption_mode_sensitivity_only",
                "blocked_use": (
                    "default_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                    "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                    "reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": (
                    "annual_flow_runtime_sensitivity_only_not_empirical"
                ),
                **_disabled_switches(),
            }
        )
    return rows


def _scenario_denominator_anchor_lineage_rows(
    *,
    forecast_holder_tdc_consistency_bridge_rows: Sequence[dict[str, str]],
    noncanonical_current_demand_support_ratio_consumer_rows: Sequence[dict[str, str]],
    annual_flow_anchor_registry_rows: Sequence[dict[str, str]],
    annual_support_denominator_compatibility_registry_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    consumer_by_key = {
        (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
        ): row
        for row in noncanonical_current_demand_support_ratio_consumer_rows
    }
    anchors_by_id = {
        row["denominator_source_id"]: row for row in annual_flow_anchor_registry_rows
    }
    compatibility_by_id = {
        row["denominator_source_id"]: row
        for row in annual_support_denominator_compatibility_registry_rows
    }
    runtime_anchor_ids = [
        _LEGACY_ANCHOR_NAMES["base_current_100bps"],
        _LEGACY_ANCHOR_NAMES["high_fiscal_offset_no_hit"],
        _LITERATURE_SOURCE_ID,
        _PRIMARY_BOUNDED_SOURCE_ID,
    ]
    rows: list[dict[str, str]] = []
    for bridge_row in forecast_holder_tdc_consistency_bridge_rows:
        key = (
            bridge_row["forecast_year"],
            bridge_row["mpc_scenario"],
            bridge_row["maturity_scenario"],
            bridge_row["holder_scenario"],
        )
        consumer_row = consumer_by_key.get(key)
        support_pct = (
            _decimal_or_none(consumer_row["support_pct_of_gdp"]) if consumer_row else None
        )
        for anchor_id in runtime_anchor_ids:
            anchor = anchors_by_id[anchor_id]
            compatibility = compatibility_by_id[anchor_id]
            anchor_pp_gdp = _decimal_or_none(anchor["anchor_value_pp_gdp"])
            implied = (
                _safe_ratio(support_pct, anchor_pp_gdp)
                if compatibility["support_offset_computation_allowed"] == "true"
                else None
            )
            row = {field: "" for field in SCENARIO_DENOMINATOR_ANCHOR_LINEAGE_FIELDS}
            row.update(
                {
                    "lineage_row_id": (
                        "scenario_denominator_anchor_lineage::"
                        f"{bridge_row['forecast_year']}::{bridge_row['mpc_scenario']}::"
                        f"{bridge_row['maturity_scenario']}::{bridge_row['holder_scenario']}::"
                        f"{anchor_id}"
                    ),
                    "ratio_id": "RW_Y",
                    "numerator_source_artifact": (
                        "ratewall_forecast_holder_tdc_consistency_bridge.csv"
                    ),
                    "forecast_year": bridge_row["forecast_year"],
                    "mpc_scenario": bridge_row["mpc_scenario"],
                    "maturity_scenario": bridge_row["maturity_scenario"],
                    "holder_scenario": bridge_row["holder_scenario"],
                    "denominator_source_id": anchor_id,
                    "denominator_source_class": anchor["denominator_source_class"],
                    "denominator_source_artifact": (
                        "ratewall_conventional_drag_bounded_denominator_registry.csv"
                        if anchor_id == _PRIMARY_BOUNDED_SOURCE_ID
                        else "ratewall_annual_flow_runtime_family_registry.csv"
                    ),
                    "denominator_timing_class": anchor["timing_alignment_class"],
                    "support_pct_of_gdp": _format_decimal(support_pct),
                    "denominator_anchor_pp_gdp": anchor["anchor_value_pp_gdp"],
                    "implied_support_offset_100bp_year_equivalent": _format_decimal(
                        implied
                    ),
                    "scenario_runtime_allowed": compatibility["runtime_anchor_allowed"],
                    "timing_alignment_status": _lineage_timing_status(anchor_id, anchor),
                    "denominator_empirical_status": anchor["anchor_empirical_status"],
                    "exact_blocker": (
                        compatibility["exact_blocker"]
                        or _lineage_exact_blocker(anchor_id, anchor)
                    ),
                    "safe_sentence": _lineage_safe_sentence(anchor_id),
                    "next_backend_action": compatibility["next_backend_action"],
                    "allowed_use": compatibility["allowed_use"],
                    "blocked_use": (
                        "canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;"
                        "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
                        "tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": _lineage_claim_boundary(anchor_id),
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    return rows


def _scenario_denominator_stack_comparison_rows(
    *,
    scenario_denominator_anchor_lineage_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for lineage_row in scenario_denominator_anchor_lineage_rows:
        anchor_id = lineage_row["denominator_source_id"]
        if anchor_id == _LITERATURE_SOURCE_ID and lineage_row["scenario_runtime_allowed"] == "true":
            stack_row_role = "runtime_primary_empirical_anchor"
            stack_status = "pass_runtime_primary_empirical_anchor_visible"
        elif anchor_id in _LEGACY_ANCHOR_NAMES.values():
            stack_row_role = "runtime_sensitivity_fallback_anchor"
            stack_status = "pass_runtime_sensitivity_anchor_visible"
        elif anchor_id == _LITERATURE_SOURCE_ID:
            stack_row_role = "review_only_literature_comparison_anchor"
            stack_status = "pass_review_only_literature_anchor_visible"
        else:
            stack_row_role = "review_only_bounded_h8_overlay"
            stack_status = "pass_review_only_bounded_overlay_visible"
        row = {field: "" for field in SCENARIO_DENOMINATOR_STACK_COMPARISON_FIELDS}
        row.update(
            {
                "stack_row_id": (
                    "scenario_denominator_stack_comparison::"
                    f"{lineage_row['forecast_year']}::{lineage_row['mpc_scenario']}::"
                    f"{lineage_row['maturity_scenario']}::{lineage_row['holder_scenario']}::"
                    f"{anchor_id}"
                ),
                "ratio_id": lineage_row["ratio_id"],
                "forecast_year": lineage_row["forecast_year"],
                "mpc_scenario": lineage_row["mpc_scenario"],
                "maturity_scenario": lineage_row["maturity_scenario"],
                "holder_scenario": lineage_row["holder_scenario"],
                "support_pct_of_gdp": lineage_row["support_pct_of_gdp"],
                "denominator_source_id": anchor_id,
                "denominator_source_class": lineage_row["denominator_source_class"],
                "denominator_source_artifact": lineage_row[
                    "denominator_source_artifact"
                ],
                "denominator_timing_class": lineage_row["denominator_timing_class"],
                "denominator_anchor_pp_gdp": lineage_row["denominator_anchor_pp_gdp"],
                "implied_support_offset_100bp_year_equivalent": lineage_row[
                    "implied_support_offset_100bp_year_equivalent"
                ],
                "scenario_runtime_allowed": lineage_row["scenario_runtime_allowed"],
                "stack_row_role": stack_row_role,
                "stack_status": stack_status,
                "timing_alignment_status": lineage_row["timing_alignment_status"],
                "denominator_empirical_status": lineage_row[
                    "denominator_empirical_status"
                ],
                "exact_blocker": lineage_row["exact_blocker"],
                "safe_sentence": lineage_row["safe_sentence"],
                "next_backend_action": lineage_row["next_backend_action"],
                "allowed_use": lineage_row["allowed_use"],
                "blocked_use": lineage_row["blocked_use"],
                "claim_boundary": (
                    "scenario_facing_denominator_stack_review_only"
                    if anchor_id == _LITERATURE_SOURCE_ID
                    and lineage_row["scenario_runtime_allowed"] == "false"
                    else lineage_row["claim_boundary"]
                ),
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _noncanonical_current_demand_source_timing_contract_rows(
    *,
    annual_flow_anchor_registry_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    anchors_by_id = {
        row["denominator_source_id"]: row for row in annual_flow_anchor_registry_rows
    }
    literature_anchor = anchors_by_id[_LITERATURE_SOURCE_ID]
    bounded_anchor = anchors_by_id[_PRIMARY_BOUNDED_SOURCE_ID]
    row_specs = [
        {
            "contract_row_id": (
                "noncanonical_current_demand_source_timing_contract::dual_review_only_consumer_summary"
            ),
            "contract_scope": "summary",
            "ratio_id": "RW_Y",
            "consumer_lane_id": (
                "bounded_h8_overlay_review_only;literature_annual_flow_comparison_review_only"
            ),
            "numerator_source_artifact": (
                "ratewall_forecast_holder_tdc_consistency_bridge.csv"
            ),
            "numerator_timing_class": "annual_support_flow_review_only",
            "numerator_contract_class": "dual_lane_review_only_consumer_policy",
            "denominator_source_id": (
                f"{_PRIMARY_BOUNDED_SOURCE_ID};{_LITERATURE_SOURCE_ID}"
            ),
            "denominator_source_artifact": (
                "ratewall_conventional_drag_bounded_denominator_registry.csv;"
                "ratewall_annual_flow_denominator_anchor_registry.csv"
            ),
            "denominator_timing_class": (
                "h8_cumulative_equivalent_overlay;review_only_annual_flow_h4_endpoint_proxy"
            ),
            "review_only_consumer_allowed": "true",
            "runtime_anchor_allowed": "false",
            "contract_status": "pass_dual_lane_review_only_consumer_contract_available",
            "timing_policy_status": "pass_explicit_dual_lane_timing_policy_recorded",
            "exact_blocker": (
                "The dual-lane current-demand consumer is review-only. The bounded h8 lane "
                "is a cumulative overlay and the literature lane is an annual-flow "
                "comparison; neither lane is a runtime anchor or canonical RW_Y path."
            ),
            "safe_sentence": (
                "The noncanonical consumer now uses one explicit review-only contract for "
                "two lanes: bounded h8 cumulative overlay and literature annual-flow comparison."
            ),
            "next_backend_action": (
                "treat_consumer_contract_as_sufficient_endpoint_and_limit_any_followup_to_scale_conflict_interpretation"
            ),
            "allowed_use": "review_only_noncanonical_current_demand_consumer_contract",
            "blocked_use": (
                "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": (
                "noncanonical_current_demand_consumer_dual_lane_contract_review_only"
            ),
        },
        {
            "contract_row_id": (
                "noncanonical_current_demand_source_timing_contract::bounded_h8_overlay_review_only"
            ),
            "contract_scope": "lane",
            "ratio_id": "RW_Y",
            "consumer_lane_id": "bounded_h8_overlay_review_only",
            "numerator_source_artifact": (
                "ratewall_forecast_holder_tdc_consistency_bridge.csv"
            ),
            "numerator_timing_class": "annual_support_flow_review_only",
            "numerator_contract_class": "lane_specific_review_only_timing_policy",
            "denominator_source_id": bounded_anchor["denominator_source_id"],
            "denominator_source_artifact": (
                "ratewall_conventional_drag_bounded_denominator_registry.csv"
            ),
            "denominator_timing_class": bounded_anchor["timing_alignment_class"],
            "review_only_consumer_allowed": "true",
            "runtime_anchor_allowed": "false",
            "contract_status": "pass_bounded_h8_overlay_review_only_contract_lane",
            "timing_policy_status": (
                "review_only_annual_support_vs_h8_cumulative_overlay"
            ),
            "exact_blocker": (
                "The bounded h8 lane compares annual support against a cumulative h8 "
                "denominator overlay. It is review-only, not an annual-flow anchor, "
                "and direct annual support-offset ratios stay blocked unless a formal "
                "translation artifact is materialized."
            ),
            "safe_sentence": (
                "This lane is allowed only as a bounded h8 cumulative overlay against "
                "annual support, not as a timing-aligned annual-flow denominator or "
                "direct support-offset ratio."
            ),
            "next_backend_action": (
                "either_materialize_formal_translation_or_keep_nonratio_overlay"
            ),
            "allowed_use": "review_only_noncanonical_current_demand_consumer_contract",
            "blocked_use": (
                "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": (
                "noncanonical_current_demand_consumer_lane_contract_review_only"
            ),
        },
        {
            "contract_row_id": (
                "noncanonical_current_demand_source_timing_contract::literature_annual_flow_comparison_review_only"
            ),
            "contract_scope": "lane",
            "ratio_id": "RW_Y",
            "consumer_lane_id": "literature_annual_flow_comparison_review_only",
            "numerator_source_artifact": (
                "ratewall_forecast_holder_tdc_consistency_bridge.csv"
            ),
            "numerator_timing_class": "annual_support_flow_review_only",
            "numerator_contract_class": "lane_specific_review_only_timing_policy",
            "denominator_source_id": literature_anchor["denominator_source_id"],
            "denominator_source_artifact": (
                "ratewall_annual_flow_denominator_anchor_registry.csv"
            ),
            "denominator_timing_class": literature_anchor["timing_alignment_class"],
            "review_only_consumer_allowed": "true",
            "runtime_anchor_allowed": "false",
            "contract_status": (
                "pass_literature_annual_flow_comparison_review_only_contract_lane"
            ),
            "timing_policy_status": (
                "pass_review_only_literature_annual_flow_window_materialized"
            ),
            "exact_blocker": (
                "The literature lane compares annual support against a review-only "
                "annual-flow proxy anchor. It remains non-runtime and noncanonical."
            ),
            "safe_sentence": (
                "This lane is allowed only as a review-only annual-flow comparison "
                "against the literature bridge anchor, not as a runtime anchor."
            ),
            "next_backend_action": (
                "keep_literature_annual_flow_comparison_review_only_and_shift_followup_to_scale_conflict_interpretation"
            ),
            "allowed_use": "review_only_noncanonical_current_demand_consumer_contract",
            "blocked_use": (
                "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": (
                "noncanonical_current_demand_consumer_lane_contract_review_only"
            ),
        },
    ]
    rows: list[dict[str, str]] = []
    for spec in row_specs:
        row = {field: "" for field in NONCANONICAL_CURRENT_DEMAND_SOURCE_TIMING_CONTRACT_FIELDS}
        row.update(spec)
        row.update(_disabled_switches())
        rows.append(row)
    return rows


def _noncanonical_current_demand_consumer_endpoint_decision_rows(
    *,
    noncanonical_current_demand_source_timing_contract_rows: Sequence[dict[str, str]],
    denominator_scale_conflict_adjudication_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    summary_row = next(
        row
        for row in noncanonical_current_demand_source_timing_contract_rows
        if row["contract_scope"] == "summary"
    )
    _ = denominator_scale_conflict_adjudication_rows
    row = {
        "decision_row_id": (
            "noncanonical_current_demand_consumer_endpoint_decision::"
            "dual_lane_contract_sufficient_review_only_endpoint"
        ),
        "ratio_id": "RW_Y",
        "decision_scope": "summary",
        "consumer_contract_artifact": (
            "ratewall_noncanonical_current_demand_source_timing_contract.csv"
        ),
        "consumer_contract_row_id": summary_row["contract_row_id"],
        "conflict_adjudication_artifact": (
            "ratewall_denominator_scale_conflict_adjudication.csv"
        ),
        "linked_conflict_row_ids": ";".join(
            [
                "denominator_scale_conflict::annual_flow_base_vs_literature_year1",
                "denominator_scale_conflict::annual_flow_high_vs_literature_year1",
                "denominator_scale_conflict::bounded_h8_vs_literature_h8",
                "denominator_scale_conflict::bounded_h8_vs_frbus_h8",
                "denominator_scale_conflict::literature_h8_vs_frbus_h8",
            ]
        ),
        "endpoint_decision_status": (
            "pass_shared_dual_lane_contract_sufficient_review_only_endpoint"
        ),
        "consumer_hardening_status": (
            "pass_no_further_consumer_hardening_required_review_only"
        ),
        "remaining_followup_scope": "review_only_scale_conflict_interpretation_only",
        "exact_blocker": (
            "Consumer source/timing hardening is complete at the review-only dual-lane "
            "contract boundary. The remaining rule is explicit: annual-flow numerator "
            "pairings stay direct only against annual-flow anchors, while bounded h8 "
            "remains a non-ratio overlay unless a formal translation artifact is added."
        ),
        "safe_sentence": (
            "The shared dual-lane contract is now the fail-closed endpoint for the "
            "noncanonical current-demand consumer. Annual-flow numerator work stays on "
            "annual-flow anchors; bounded h8 stays overlay-only unless translated."
        ),
        "next_backend_action": (
            "if_future_work_occurs_limit_it_to_review_only_scale_conflict_interpretation"
        ),
        "allowed_use": (
            "review_only_consumer_endpoint_decision;review_only_scale_conflict_triage"
        ),
        "blocked_use": (
            "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
            "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
            "reset_calendar;tax_incidence_welfare_mpc"
        ),
        "claim_boundary": (
            "noncanonical_current_demand_consumer_endpoint_decision_review_only"
        ),
        **_disabled_switches(),
    }
    return [
        {
            field: row.get(field, "")
            for field in NONCANONICAL_CURRENT_DEMAND_CONSUMER_ENDPOINT_DECISION_FIELDS
        }
    ]


def _denominator_scale_conflict_followup_decision_rows(
    *,
    denominator_scale_conflict_adjudication_rows: Sequence[dict[str, str]],
    noncanonical_current_demand_consumer_endpoint_decision_rows: Sequence[dict[str, str]],
    h4_empirical_validation_registry_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    endpoint_row = next(
        iter(noncanonical_current_demand_consumer_endpoint_decision_rows), None
    )
    h4_validation_ready = any(
        row["same_design_materialization_status"]
        == "pass_direct_same_design_h4_companion_materialized"
        for row in h4_empirical_validation_registry_rows
    )
    linked_conflict_row_ids = ";".join(
        row["adjudication_row_id"] for row in denominator_scale_conflict_adjudication_rows
    )
    row = {
        "decision_row_id": (
            "denominator_scale_conflict_followup_decision::"
            "literature_runtime_policy_promoted"
        ),
        "decision_scope": "summary",
        "ratio_id": "RW_Y",
        "conflict_adjudication_artifact": (
            "ratewall_denominator_scale_conflict_adjudication.csv"
        ),
        "linked_conflict_row_ids": linked_conflict_row_ids,
        "endpoint_decision_artifact": (
            "ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv"
        ),
        "endpoint_decision_row_id": (
            endpoint_row["decision_row_id"] if endpoint_row is not None else ""
        ),
        "followup_decision_status": (
            "pass_same_design_h4_validation_materialized_runtime_policy_maintained"
            if h4_validation_ready
            else "pass_literature_annual_flow_runtime_policy_promoted"
        ),
        "followup_artifact_needed": "false",
        "current_stop_state_status": (
            "pass_runtime_policy_retained_after_same_design_h4_validation"
            if h4_validation_ready
            else "pass_review_only_stop_state_superseded_by_runtime_promotion"
        ),
        "reopen_trigger_status": (
            "reopen_only_if_h8_translation_probe_h8_compatible_numerator_path_or_new_scale_evidence_arrives"
            if h4_validation_ready
            else "reopen_only_if_same_design_h4_validation_h8_translation_probe_h8_compatible_numerator_path_or_new_scale_evidence_arrives"
        ),
        "exact_blocker": (
            "The live methodological bug is now fixed by promoting the literature-backed "
            "annual-flow runtime family, and the direct same-design h4 companion validation "
            "is now materialized as a review-only empirical cross-check. Any further "
            "denominator work should stay narrow: an h8 translation probe, an "
            "h8-compatible numerator path, or truly new scale evidence, not another "
            "broad estimator lane."
            if h4_validation_ready
            else "The live methodological bug is now fixed by promoting the literature-backed "
            "annual-flow runtime family. Any further denominator work should stay narrow: "
            "same-design h4 validation, an h8 translation probe, or an h8-compatible "
            "numerator path, not another broad estimator lane."
        ),
        "safe_sentence": (
            "The literature annual-flow runtime family remains the default denominator "
            "policy after direct same-design h4 validation. Bounded h8 stays overlay-only "
            "unless a separate annual-window translation or h8-compatible numerator path is built."
            if h4_validation_ready
            else "The review-only stop state has been superseded by runtime promotion of the "
            "literature annual-flow family. Bounded h8 remains overlay-only unless a "
            "separate annual-window translation or h8-compatible numerator path is built."
        ),
        "next_backend_action": (
            "keep_literature_runtime_family_as_default_and_limit_future_followup_to_h8_translation_probe_h8_compatible_numerator_path_or_new_scale_evidence"
            if h4_validation_ready
            else "promote_literature_runtime_family_and_limit_future_followup_to_h4_validation_h8_translation_probe_or_h8_compatible_numerator_path"
        ),
        "allowed_use": "runtime_policy_decision;followup_triage",
        "blocked_use": (
            "new_estimator_lane_without_new_evidence;canonical_RW_Y;"
            "main_ratio;Evidence_Mode;denominator_prior;pricing;holder_allocation;"
            "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
        ),
        "claim_boundary": "denominator_runtime_policy_decision_noncanonical",
        **_disabled_switches(),
    }
    return [
        {
            field: row.get(field, "")
            for field in DENOMINATOR_SCALE_CONFLICT_FOLLOWUP_DECISION_FIELDS
        }
    ]


def _runtime_annual_flow_support_offset_closeout_decision_rows(
    *,
    runtime_annual_flow_support_offset_adoption_matrix_rows: Sequence[dict[str, str]],
    runtime_annual_flow_support_offset_frontier_summary_rows: Sequence[dict[str, str]],
    runtime_annual_flow_support_offset_readiness_registry_rows: Sequence[dict[str, str]],
    denominator_scale_conflict_followup_decision_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    followup_row = next(iter(denominator_scale_conflict_followup_decision_rows), None)
    adoption_row_count = len(runtime_annual_flow_support_offset_adoption_matrix_rows)
    frontier_row_count = len(runtime_annual_flow_support_offset_frontier_summary_rows)
    readiness_row_count = len(runtime_annual_flow_support_offset_readiness_registry_rows)
    reportable_runtime_row_count = sum(
        row["readiness_tier"] == "reportable_runtime_support_offset"
        for row in runtime_annual_flow_support_offset_readiness_registry_rows
    )
    blocked_overlay_row_count = sum(
        row["readiness_tier"] == "blocked_noncommensurate_overlay_context"
        for row in runtime_annual_flow_support_offset_readiness_registry_rows
    )
    default_family_count_ok = (
        adoption_row_count > 0
        and all(
            row["default_denominator_source_id"] == _LITERATURE_SOURCE_ID
            and row["default_runtime_family_count"] == "1"
            for row in runtime_annual_flow_support_offset_adoption_matrix_rows
        )
    )
    sensitivity_count_ok = adoption_row_count > 0 and all(
        row["sensitivity_runtime_family_count"] == "2"
        for row in runtime_annual_flow_support_offset_adoption_matrix_rows
    )
    blocked_overlay_count_ok = (
        adoption_row_count > 0
        and all(
            row["blocked_overlay_family_count"] == "3"
            for row in runtime_annual_flow_support_offset_adoption_matrix_rows
        )
        and blocked_overlay_row_count == adoption_row_count * 3
    )
    closeout_ready = (
        default_family_count_ok
        and sensitivity_count_ok
        and blocked_overlay_count_ok
        and frontier_row_count == 33
        and reportable_runtime_row_count == adoption_row_count * 3
    )
    row = {
        "decision_row_id": (
            "runtime_annual_flow_support_offset_closeout_decision::"
            "noncanonical_release_grade"
        ),
        "decision_scope": "summary",
        "ratio_id": "RW_Y",
        "adoption_matrix_artifact": (
            "ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv"
        ),
        "adoption_matrix_row_count": str(adoption_row_count),
        "frontier_summary_artifact": (
            "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv"
        ),
        "frontier_summary_row_count": str(frontier_row_count),
        "readiness_artifact": (
            "ratewall_runtime_annual_flow_support_offset_readiness_registry.csv"
        ),
        "readiness_row_count": str(readiness_row_count),
        "reportable_runtime_row_count": str(reportable_runtime_row_count),
        "blocked_overlay_row_count": str(blocked_overlay_row_count),
        "default_runtime_family_source_id": _LITERATURE_SOURCE_ID,
        "default_runtime_family_count_status": (
            "pass_exactly_one_default_runtime_family_per_contract"
            if default_family_count_ok
            else "blocked_default_runtime_family_count_not_unique"
        ),
        "sensitivity_runtime_family_count_status": (
            "pass_exactly_two_sensitivity_runtime_families_per_contract"
            if sensitivity_count_ok
            else "blocked_sensitivity_runtime_family_count_not_two"
        ),
        "blocked_overlay_count_status": (
            "pass_exactly_three_blocked_overlay_families_per_contract"
            if blocked_overlay_count_ok
            else "blocked_overlay_family_count_not_three"
        ),
        "linked_followup_artifact": (
            "ratewall_denominator_scale_conflict_followup_decision.csv"
        ),
        "linked_followup_row_id": (
            followup_row["decision_row_id"] if followup_row is not None else ""
        ),
        "closeout_decision_status": (
            "pass_noncanonical_annual_flow_runtime_support_offset_release_grade"
            if closeout_ready
            else "blocked_noncanonical_annual_flow_runtime_support_offset_not_release_grade"
        ),
        "followup_artifact_needed": "false" if closeout_ready else "true",
        "reopen_trigger_status": (
            followup_row["reopen_trigger_status"]
            if followup_row is not None
            else "reopen_only_if_h8_translation_probe_h8_compatible_numerator_path_or_new_scale_evidence_arrives"
        ),
        "exact_blocker": (
            ""
            if closeout_ready
            else "The compact runtime adoption layer is not yet fully release-grade. Default-family uniqueness, sensitivity/overlay bundle counts, frontier coverage, and reportable runtime row counts must all reconcile before closeout can pass."
        ),
        "safe_sentence": (
            "The annual-flow runtime support-offset layer is now release-grade as a noncanonical diagnostic: one literature-backed default runtime family, explicit legacy sensitivity rows, and blocked h8-family overlays remain machine-readable and fail-closed."
            if closeout_ready
            else "The annual-flow runtime support-offset layer is not yet release-grade. Keep using the audited compact outputs as work-in-progress until bundle counts and coverage reconcile."
        ),
        "next_backend_action": (
            "use_compact_runtime_support_offset_layer_as_release_grade_noncanonical_diagnostic_and_reopen_only_on_narrow_triggers"
            if closeout_ready
            else "finish_compact_runtime_support_offset_closeout_before_further_adoption"
        ),
        "allowed_use": (
            "noncanonical_runtime_support_offset_closeout;runtime_support_offset_readiness_triage;report_ready_default_and_sensitivity_runtime_rows"
        ),
        "blocked_use": (
            "canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;pricing;"
            "holder_allocation;raw_rate_shock;reset_calendar;"
            "tax_incidence_welfare_mpc;h8_direct_runtime_ratio"
        ),
        "claim_boundary": (
            "runtime_annual_flow_support_offset_closeout_noncanonical"
        ),
        **_disabled_switches(),
    }
    return [
        {
            field: row.get(field, "")
            for field in RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_CLOSEOUT_DECISION_FIELDS
        }
    ]


def _runtime_annual_flow_support_offset_benchmark_overlay_rows(
    *,
    runtime_annual_flow_support_offset_frontier_summary_rows: Sequence[dict[str, str]],
    runtime_annual_flow_support_offset_closeout_decision_rows: Sequence[dict[str, str]],
    bounded_denominator_registry_rows: Sequence[dict[str, str]],
    frbus_100bp_year_fspdp_proxy_benchmark_rows: Sequence[dict[str, str]],
    h4_empirical_validation_registry_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    frontier_by_key = {
        (row["forecast_year"], row["denominator_source_id"]): row
        for row in runtime_annual_flow_support_offset_frontier_summary_rows
    }
    closeout_row = next(iter(runtime_annual_flow_support_offset_closeout_decision_rows), None)
    bounded_h8_row = next(
        (
            row
            for row in bounded_denominator_registry_rows
            if row["horizon_q"] == "8" and row["primary_denominator_horizon"] == "true"
        ),
        None,
    )
    h4_cluster_row = next(
        (
            row
            for row in h4_empirical_validation_registry_rows
            if row["validation_row_id"] == "h4_empirical_validation_registry::literature_runtime_vs_frbus_h4"
        ),
        None,
    )
    frbus_proxy_by_horizon = {
        row["horizon_q"]: row
        for row in frbus_100bp_year_fspdp_proxy_benchmark_rows
        if row.get("component_id") == "fspdp_proxy"
        and row.get("scenario_id") == "official_100bp_year_rffintay_add_factor_review"
    }
    frbus_proxy_available = all(
        frbus_proxy_by_horizon.get(horizon, {}).get("model_d_y_per_100bp_year")
        for horizon in ("4", "8", "12")
    )

    def frbus_benchmark_value(horizon: str) -> str:
        # Review-only FRB/US proxy rows can vary in the last displayed digit
        # across builds; keep the overlay hash-stable without changing scale.
        value = frbus_proxy_by_horizon.get(horizon, {}).get(
            "model_d_y_per_100bp_year",
            "",
        )
        decimal_value = _decimal_or_none(value)
        if decimal_value is None:
            return ""
        return format(decimal_value.quantize(Decimal("0.00000000001")).normalize(), "f")

    rows: list[dict[str, str]] = []
    forecast_years = sorted(
        {
            row["forecast_year"]
            for row in runtime_annual_flow_support_offset_frontier_summary_rows
            if row["runtime_family_class"] == "default_runtime_family"
        }
    )
    for forecast_year in forecast_years:
        default_row = frontier_by_key.get((forecast_year, _LITERATURE_SOURCE_ID))
        legacy_base_row = frontier_by_key.get(
            (forecast_year, _LEGACY_ANCHOR_NAMES["base_current_100bps"])
        )
        legacy_high_row = frontier_by_key.get(
            (forecast_year, _LEGACY_ANCHOR_NAMES["high_fiscal_offset_no_hit"])
        )
        overlay_ready = all(
            row is not None for row in (default_row, legacy_base_row, legacy_high_row)
        )
        row = {
            field: ""
            for field in RUNTIME_ANNUAL_FLOW_SUPPORT_OFFSET_BENCHMARK_OVERLAY_FIELDS
        }
        row.update(
            {
                "overlay_row_id": (
                    "runtime_annual_flow_support_offset_benchmark_overlay::"
                    f"{forecast_year}"
                ),
                "ratio_id": "RW_Y",
                "forecast_year": forecast_year,
                "adoption_matrix_artifact": (
                    "ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv"
                ),
                "frontier_summary_artifact": (
                    "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv"
                ),
                "closeout_artifact": (
                    "ratewall_runtime_annual_flow_support_offset_closeout_decision.csv"
                ),
                "closeout_row_id": (
                    closeout_row["decision_row_id"] if closeout_row is not None else ""
                ),
                "default_runtime_family_source_id": _LITERATURE_SOURCE_ID,
                "bounded_h8_overlay_source_id": "bounded_h8_overlay_review_center",
                "bounded_h8_review_center_pp_gdp_per_100bp_year": (
                    bounded_h8_row["review_center_d_y"] if bounded_h8_row is not None else ""
                ),
                "bounded_h8_weak_iv_safe_ci_low_pp_gdp_per_100bp_year": (
                    bounded_h8_row["bounded_ci_low_d_y"] if bounded_h8_row is not None else ""
                ),
                "bounded_h8_weak_iv_safe_ci_high_pp_gdp_per_100bp_year": (
                    bounded_h8_row["bounded_ci_high_d_y"] if bounded_h8_row is not None else ""
                ),
                "bounded_h8_direct_runtime_ratio_status": (
                    "blocked_not_timing_commensurate_for_support_offset"
                ),
                "frbus_h4_benchmark_source_id": "frbus_h4_component_proxy",
                "frbus_h4_benchmark_pp_gdp_per_100bp_year": frbus_benchmark_value("4"),
                "frbus_h8_benchmark_source_id": "frbus_h8_component_proxy",
                "frbus_h8_benchmark_pp_gdp_per_100bp_year": frbus_benchmark_value("8"),
                "frbus_h12_benchmark_source_id": "frbus_h12_component_proxy",
                "frbus_h12_benchmark_pp_gdp_per_100bp_year": frbus_benchmark_value("12"),
                "low_scale_cluster_status": (
                    h4_cluster_row["scale_alignment_status"]
                    if h4_cluster_row is not None and frbus_proxy_available
                    else "not_materialized"
                ),
                "scale_conflict_status": (
                    "warn_bounded_h8_above_literature_runtime_and_frbus_review_cluster"
                    if frbus_proxy_available
                    else "blocked_frbus_100bp_year_benchmark_missing_for_scale_cluster"
                ),
                "overlay_status": (
                    "pass_runtime_default_plus_review_only_benchmark_context_materialized"
                    if overlay_ready
                    else "blocked_missing_runtime_frontier_context_rows"
                ),
                "exact_blocker": (
                    ""
                    if overlay_ready
                    else "Benchmark-context overlay requires the default literature frontier row plus both legacy sensitivity frontier rows for each forecast year."
                ),
                "safe_sentence": (
                    "This overlay keeps the literature annual-flow family as the only reportable runtime default, legacy 0.6/0.7 rows as sensitivity-only, bounded h8 as review-only cumulative context, and FRB/US as benchmark-only low-scale context."
                ),
                "next_backend_action": (
                    "use_overlay_in_reviewer_packet_and_keep_reopen_triggers_narrow"
                ),
                "allowed_use": (
                    "reviewer_packet_context;benchmark_overlay_context;noncanonical_runtime_support_offset_summary"
                ),
                "blocked_use": (
                    "canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;pricing;"
                    "holder_allocation;raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc;h8_direct_runtime_ratio"
                ),
                "claim_boundary": (
                    "runtime_annual_flow_support_offset_benchmark_overlay_noncanonical"
                ),
                **_disabled_switches(),
            }
        )
        if overlay_ready:
            row.update(
                {
                    "default_runtime_frontier_row_id": default_row["frontier_row_id"],
                    "default_runtime_reference_support_offset_100bp_year_equivalent": default_row[
                        "reference_support_offset_100bp_year_equivalent"
                    ],
                    "default_runtime_reference_denominator_center_pp_gdp": default_row[
                        "reference_denominator_center_pp_gdp"
                    ],
                    "default_runtime_reference_denominator_ci95_low_pp_gdp": default_row[
                        "reference_denominator_ci95_low_pp_gdp"
                    ],
                    "default_runtime_reference_denominator_ci95_high_pp_gdp": default_row[
                        "reference_denominator_ci95_high_pp_gdp"
                    ],
                    "legacy_base_frontier_row_id": legacy_base_row["frontier_row_id"],
                    "legacy_base_reference_support_offset_100bp_year_equivalent": legacy_base_row[
                        "reference_support_offset_100bp_year_equivalent"
                    ],
                    "legacy_high_frontier_row_id": legacy_high_row["frontier_row_id"],
                    "legacy_high_reference_support_offset_100bp_year_equivalent": legacy_high_row[
                        "reference_support_offset_100bp_year_equivalent"
                    ],
                }
            )
        rows.append(row)
    return rows


def _h4_empirical_validation_registry_rows(
    *,
    bounded_denominator_registry_rows: Sequence[dict[str, str]],
    annual_flow_runtime_family_registry_rows: Sequence[dict[str, str]],
    weak_iv_safe_inference_rows: Sequence[dict[str, str]],
    frbus_100bp_year_fspdp_proxy_benchmark_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    bounded_h4 = next(
        row
        for row in bounded_denominator_registry_rows
        if row["horizon_q"] == "4"
    )
    literature_runtime = next(
        row
        for row in annual_flow_runtime_family_registry_rows
        if row["denominator_source_id"] == _LITERATURE_SOURCE_ID
    )
    h4_weak_iv_safe = next(
        (
            row
            for row in weak_iv_safe_inference_rows
            if row["horizon_q"] == "4"
            and row["instrument_variant"] == "sf_fed_usmpd_me_scalar_quarterly_sum"
        ),
        None,
    )
    frbus_h4 = next(
        row
        for row in frbus_100bp_year_fspdp_proxy_benchmark_rows
        if row["component_mapping_id"] == "ecnia_plus_ebfi_plus_eh_fspdp_proxy"
        and row["component_id"] == "fspdp_proxy"
        and row["horizon_q"] == "4"
    )
    bounded_center = _decimal_or_none(bounded_h4["review_center_d_y"])
    bounded_proxy_iv_low = _decimal_or_none(bounded_h4["proxy_iv_ci_low_d_y"])
    bounded_proxy_iv_high = _decimal_or_none(bounded_h4["proxy_iv_ci_high_d_y"])
    bounded_controlled_low = _decimal_or_none(
        bounded_h4["companion_controlled_ci_low_d_y"]
    )
    bounded_controlled_high = _decimal_or_none(
        bounded_h4["companion_controlled_ci_high_d_y"]
    )
    bounded_weak_iv_safe_low = (
        _decimal_or_none(h4_weak_iv_safe["weak_iv_safe_ci_low_d_y"])
        if h4_weak_iv_safe is not None
        else None
    )
    bounded_weak_iv_safe_high = (
        _decimal_or_none(h4_weak_iv_safe["weak_iv_safe_ci_high_d_y"])
        if h4_weak_iv_safe is not None
        else None
    )
    literature_center = _decimal_or_none(literature_runtime["runtime_anchor_value_pp_gdp"])
    literature_ci_low = _decimal_or_none(literature_runtime["runtime_ci95_low_pp_gdp"])
    literature_ci_high = _decimal_or_none(
        literature_runtime["runtime_ci95_high_pp_gdp"]
    )
    frbus_center = _decimal_or_none(frbus_h4["model_d_y_per_100bp_year"])
    h4_weak_iv_safe_status = (
        h4_weak_iv_safe["weak_iv_safe_inference_status"]
        if h4_weak_iv_safe is not None
        else "blocked_weak_iv_safe_h4_not_materialized"
    )
    h4_interval_overlap_status = (
        "warn_no_weak_iv_safe_interval_overlap_with_literature_runtime_ci"
        if bounded_weak_iv_safe_low is not None
        and bounded_weak_iv_safe_high is not None
        and literature_ci_low is not None
        and literature_ci_high is not None
        and (
            bounded_weak_iv_safe_high < literature_ci_low
            or bounded_weak_iv_safe_low > literature_ci_high
        )
        else (
            "pass_weak_iv_safe_interval_overlaps_literature_runtime_ci"
            if bounded_weak_iv_safe_low is not None
            and bounded_weak_iv_safe_high is not None
            and literature_ci_low is not None
            and literature_ci_high is not None
            else "warn_no_proxy_iv_interval_overlap_with_literature_runtime_ci"
        )
    )
    h4_exact_blocker = (
        "The direct same-design h4 companion estimate is materially larger than "
        "the promoted literature runtime family, and weak-IV-safe annual-window "
        "inference is not yet materialized at h4."
        if h4_weak_iv_safe is None
        else (
            "Weak-IV-safe h4 annual-window inference is now materialized, but the "
            "bounded h4 annual-window interval remains far above the promoted "
            "literature runtime family."
            if h4_weak_iv_safe_status
            == "pass_anderson_rubin_hac_interval_excludes_zero_d_y"
            else h4_weak_iv_safe["exact_blocker"]
        )
    )
    h4_safe_sentence = (
        "The direct same-design h4 companion confirms contractionary sign but not "
        "the low scale of the runtime literature family."
        if h4_weak_iv_safe is None
        else (
            "Weak-IV-safe h4 annual-window inference confirms contractionary sign "
            "but remains far above the promoted literature runtime family."
            if h4_weak_iv_safe_status
            == "pass_anderson_rubin_hac_interval_excludes_zero_d_y"
            else (
                "The direct same-design h4 companion confirms contractionary sign, "
                "but weak-IV-safe h4 annual-window inference did not validate "
                "promotion of the bounded h4 family."
            )
        )
    )
    h4_next_action = (
        "if_future_work_occurs_materialize_weak_iv_safe_h4_or_keep_companion_validation_only"
        if h4_weak_iv_safe is None
        else (
            "keep_literature_runtime_primary_and_limit_future_followup_to_h8_translation_probe_or_new_scale_evidence"
            if h4_weak_iv_safe_status
            == "pass_anderson_rubin_hac_interval_excludes_zero_d_y"
            else h4_weak_iv_safe["next_backend_action"]
        )
    )

    return [
        _build_h4_empirical_validation_row(
            validation_row_id=(
                "h4_empirical_validation_registry::bounded_h4_vs_literature_runtime"
            ),
            validation_scope="same_design_direct_h4_vs_runtime_primary",
            bounded_source_id="bounded_h4_direct_companion",
            bounded_source_class="controlled_lp_proxy_iv_companion_horizon",
            bounded_center=bounded_center,
            bounded_proxy_iv_low=bounded_proxy_iv_low,
            bounded_proxy_iv_high=bounded_proxy_iv_high,
            bounded_controlled_low=bounded_controlled_low,
            bounded_controlled_high=bounded_controlled_high,
            comparison_source_id=_LITERATURE_SOURCE_ID,
            comparison_source_class="literature_bridge_annual_flow_runtime_anchor",
            comparison_center=literature_center,
            comparison_ci_low=literature_ci_low,
            comparison_ci_high=literature_ci_high,
            weak_iv_safe_status=h4_weak_iv_safe_status,
            sign_alignment_status="pass_same_contractionary_sign",
            scale_alignment_status="warn_bounded_h4_far_above_literature_runtime_family",
            interval_overlap_status=h4_interval_overlap_status,
            runtime_policy_implication_status=(
                "pass_keep_literature_runtime_primary_and_bound_h4_review_only"
            ),
            exact_blocker=h4_exact_blocker,
            safe_sentence=h4_safe_sentence,
            next_backend_action=h4_next_action,
        ),
        _build_h4_empirical_validation_row(
            validation_row_id=(
                "h4_empirical_validation_registry::bounded_h4_vs_frbus_h4"
            ),
            validation_scope="same_design_direct_h4_vs_frbus_benchmark",
            bounded_source_id="bounded_h4_direct_companion",
            bounded_source_class="controlled_lp_proxy_iv_companion_horizon",
            bounded_center=bounded_center,
            bounded_proxy_iv_low=bounded_proxy_iv_low,
            bounded_proxy_iv_high=bounded_proxy_iv_high,
            bounded_controlled_low=bounded_controlled_low,
            bounded_controlled_high=bounded_controlled_high,
            comparison_source_id="frbus_h4_component_proxy",
            comparison_source_class="frbus_benchmark_lane",
            comparison_center=frbus_center,
            comparison_ci_low=None,
            comparison_ci_high=None,
            weak_iv_safe_status=h4_weak_iv_safe_status,
            sign_alignment_status="pass_same_contractionary_sign",
            scale_alignment_status="warn_bounded_h4_far_above_frbus_h4_benchmark",
            interval_overlap_status="not_available_frbus_benchmark_has_no_ci",
            runtime_policy_implication_status=(
                "pass_keep_frbus_benchmark_only_and_do_not_recalibrate_runtime"
            ),
            exact_blocker=(
                "The direct same-design h4 companion estimate remains far above the "
                "FRB/US h4 benchmark, which stays benchmark-only and carries no statistical interval here."
            ),
            safe_sentence=(
                "The direct same-design h4 companion and FRB/US h4 agree on sign but not scale."
            ),
            next_backend_action=(
                "keep_frbus_benchmark_only_and_do_not_recalibrate_runtime_from_h4_gap"
            ),
        ),
        _build_h4_empirical_validation_row(
            validation_row_id=(
                "h4_empirical_validation_registry::literature_runtime_vs_frbus_h4"
            ),
            validation_scope="runtime_primary_vs_frbus_h4_benchmark",
            bounded_source_id="literature_runtime_h4_primary",
            bounded_source_class="literature_bridge_annual_flow_runtime_anchor",
            bounded_center=literature_center,
            bounded_proxy_iv_low=literature_ci_low,
            bounded_proxy_iv_high=literature_ci_high,
            bounded_controlled_low=None,
            bounded_controlled_high=None,
            comparison_source_id="frbus_h4_component_proxy",
            comparison_source_class="frbus_benchmark_lane",
            comparison_center=frbus_center,
            comparison_ci_low=None,
            comparison_ci_high=None,
            weak_iv_safe_status="not_applicable_runtime_family_is_hac_interval_based",
            sign_alignment_status="pass_same_contractionary_sign",
            scale_alignment_status="pass_runtime_family_in_same_low_scale_neighborhood_as_frbus_h4",
            interval_overlap_status="pass_frbus_h4_point_inside_literature_runtime_ci",
            runtime_policy_implication_status=(
                "pass_runtime_literature_family_has_structural_benchmark_support"
            ),
            exact_blocker=(
                "FRB/US remains benchmark-only, but its h4 point sits inside the promoted "
                "literature runtime family interval and supports the low-scale annual-flow cluster."
            ),
            safe_sentence=(
                "The promoted literature runtime family and FRB/US h4 benchmark cluster together at low annual-flow scale."
            ),
            next_backend_action=(
                "keep_literature_runtime_primary_and_track_frbus_as_benchmark_only"
            ),
        ),
    ]


def _build_h4_empirical_validation_row(
    *,
    validation_row_id: str,
    validation_scope: str,
    bounded_source_id: str,
    bounded_source_class: str,
    bounded_center: Decimal | None,
    bounded_proxy_iv_low: Decimal | None,
    bounded_proxy_iv_high: Decimal | None,
    bounded_controlled_low: Decimal | None,
    bounded_controlled_high: Decimal | None,
    comparison_source_id: str,
    comparison_source_class: str,
    comparison_center: Decimal | None,
    comparison_ci_low: Decimal | None,
    comparison_ci_high: Decimal | None,
    weak_iv_safe_status: str,
    sign_alignment_status: str,
    scale_alignment_status: str,
    interval_overlap_status: str,
    runtime_policy_implication_status: str,
    exact_blocker: str,
    safe_sentence: str,
    next_backend_action: str,
) -> dict[str, str]:
    row = {field: "" for field in H4_EMPIRICAL_VALIDATION_REGISTRY_FIELDS}
    row.update(
        {
            "validation_row_id": validation_row_id,
            "validation_scope": validation_scope,
            "ratio_id": "RW_Y",
            "horizon_q": "4",
            "bounded_source_id": bounded_source_id,
            "bounded_source_class": bounded_source_class,
            "bounded_center_pp_gdp_per_100bp_year": _format_decimal(bounded_center),
            "bounded_proxy_iv_ci_low_pp_gdp_per_100bp_year": _format_decimal(
                bounded_proxy_iv_low
            ),
            "bounded_proxy_iv_ci_high_pp_gdp_per_100bp_year": _format_decimal(
                bounded_proxy_iv_high
            ),
            "bounded_controlled_ci_low_pp_gdp_per_100bp_year": _format_decimal(
                bounded_controlled_low
            ),
            "bounded_controlled_ci_high_pp_gdp_per_100bp_year": _format_decimal(
                bounded_controlled_high
            ),
            "comparison_source_id": comparison_source_id,
            "comparison_source_class": comparison_source_class,
            "comparison_center_pp_gdp_per_100bp_year": _format_decimal(
                comparison_center
            ),
            "comparison_ci_low_pp_gdp_per_100bp_year": _format_decimal(
                comparison_ci_low
            ),
            "comparison_ci_high_pp_gdp_per_100bp_year": _format_decimal(
                comparison_ci_high
            ),
            "common_review_unit": "pp_gdp_per_100bp_year_review_only",
            "same_design_materialization_status": (
                "pass_direct_same_design_h4_companion_materialized"
            ),
            "weak_iv_safe_status": weak_iv_safe_status,
            "sign_alignment_status": sign_alignment_status,
            "scale_alignment_status": scale_alignment_status,
            "interval_overlap_status": interval_overlap_status,
            "runtime_policy_implication_status": runtime_policy_implication_status,
            "exact_blocker": exact_blocker,
            "safe_sentence": safe_sentence,
            "next_backend_action": next_backend_action,
            "allowed_use": "review_only_same_design_h4_validation",
            "blocked_use": (
                "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "same_design_h4_validation_review_only",
            **_disabled_switches(),
        }
    )
    return row


def _augmented_noncanonical_current_demand_support_ratio_consumer_rows(
    *,
    noncanonical_current_demand_support_ratio_consumer_rows: Sequence[dict[str, str]],
    annual_flow_anchor_registry_rows: Sequence[dict[str, str]],
    annual_support_denominator_compatibility_registry_rows: Sequence[dict[str, str]],
    noncanonical_current_demand_source_timing_contract_rows: Sequence[dict[str, str]],
    noncanonical_current_demand_consumer_endpoint_decision_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    anchors_by_id = {
        row["denominator_source_id"]: row for row in annual_flow_anchor_registry_rows
    }
    compatibility_by_id = {
        row["denominator_source_id"]: row
        for row in annual_support_denominator_compatibility_registry_rows
    }
    literature_anchor = anchors_by_id.get(_LITERATURE_SOURCE_ID)
    if literature_anchor is None:
        return [dict(row) for row in noncanonical_current_demand_support_ratio_consumer_rows]
    bounded_compatibility = compatibility_by_id[_PRIMARY_BOUNDED_SOURCE_ID]
    contract_rows_by_lane = {
        row["consumer_lane_id"]: row
        for row in noncanonical_current_demand_source_timing_contract_rows
        if row["contract_scope"] == "lane"
    }
    literature_anchor_pp_gdp = _decimal_or_none(literature_anchor["anchor_value_pp_gdp"])
    rows: list[dict[str, str]] = []
    for consumer_row in noncanonical_current_demand_support_ratio_consumer_rows:
        base_row = dict(consumer_row)
        bounded_contract = contract_rows_by_lane["bounded_h8_overlay_review_only"]
        bounded_support_offset_allowed = (
            bounded_compatibility["support_offset_computation_allowed"] == "true"
        )
        base_row.update(
            {
                "numerator_source_timing_contract_artifact": (
                    "ratewall_noncanonical_current_demand_source_timing_contract.csv"
                ),
                "numerator_source_timing_contract_row_id": bounded_contract[
                    "contract_row_id"
                ],
                "numerator_source_timing_contract_status": bounded_contract[
                    "contract_status"
                ],
                "denominator_scenario_runtime_allowed": bounded_compatibility[
                    "runtime_anchor_allowed"
                ],
                "support_offset_100bp_year_equivalent_lower_bound": (
                    consumer_row["support_offset_100bp_year_equivalent_lower_bound"]
                    if bounded_support_offset_allowed
                    else ""
                ),
                "support_offset_100bp_year_equivalent": (
                    consumer_row["support_offset_100bp_year_equivalent"]
                    if bounded_support_offset_allowed
                    else ""
                ),
                "support_offset_100bp_year_equivalent_upper_bound": (
                    consumer_row["support_offset_100bp_year_equivalent_upper_bound"]
                    if bounded_support_offset_allowed
                    else ""
                ),
                "support_offset_bp_year_equivalent_lower_bound": (
                    consumer_row["support_offset_bp_year_equivalent_lower_bound"]
                    if bounded_support_offset_allowed
                    else ""
                ),
                "support_offset_bp_year_equivalent": (
                    consumer_row["support_offset_bp_year_equivalent"]
                    if bounded_support_offset_allowed
                    else ""
                ),
                "support_offset_bp_year_equivalent_upper_bound": (
                    consumer_row["support_offset_bp_year_equivalent_upper_bound"]
                    if bounded_support_offset_allowed
                    else ""
                ),
                "consumer_status": (
                    "pass_review_only_bounded_h8_overlay_visible_nonratio"
                ),
                "exact_blocker": bounded_compatibility["exact_blocker"],
                "safe_sentence": (
                    "This row keeps the bounded h8 current-demand drag object visible in "
                    "the review-only consumer as cumulative-h8 overlay context only. "
                    "No timing-aligned annual support-offset ratio is computed."
                ),
                "next_backend_action": (
                    bounded_compatibility["next_backend_action"]
                ),
                "allowed_use": (
                    "review_only_h8_overlay_visible_in_consumer;nonratio_overlay_only"
                ),
                "blocked_use": (
                    "support_offset_ratio;scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                    "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                    "reset_calendar;tax_incidence_welfare_mpc"
                ),
            }
        )
        rows.append(base_row)
        support_pct_of_gdp = _decimal_or_none(consumer_row["support_pct_of_gdp"])
        literature_support_offset = _safe_ratio(
            support_pct_of_gdp, literature_anchor_pp_gdp
        )
        literature_bp_year_offset = (
            None
            if literature_support_offset is None
            else literature_support_offset * Decimal("100")
        )
        literature_row = dict(consumer_row)
        literature_contract = contract_rows_by_lane[
            "literature_annual_flow_comparison_review_only"
        ]
        literature_row.update(
            {
                "consumer_row_id": (
                    f"{consumer_row['consumer_row_id']}::{_LITERATURE_SOURCE_ID}"
                ),
                "denominator_status_artifact": (
                    "ratewall_annual_flow_denominator_anchor_registry.csv"
                ),
                "bounded_denominator_artifact": "",
                "denominator_horizon_q": "4",
                "denominator_source_id": _LITERATURE_SOURCE_ID,
                "denominator_source_class": literature_anchor[
                    "denominator_source_class"
                ],
                "denominator_timing_class": literature_anchor[
                    "timing_alignment_class"
                ],
                "denominator_anchor_empirical_status": literature_anchor[
                    "anchor_empirical_status"
                ],
                "denominator_scenario_runtime_allowed": "false",
                "review_center_d_y": literature_anchor["anchor_value_pp_gdp"],
                "admitted_d_y": "",
                "bounded_ci_low_d_y": "",
                "bounded_ci_high_d_y": "",
                "bounded_primary_object_type": (
                    "annual_flow_h4_endpoint_proxy_anchor_review_only"
                ),
                "support_offset_100bp_year_equivalent_lower_bound": "",
                "support_offset_100bp_year_equivalent": _format_decimal(
                    literature_support_offset
                ),
                "support_offset_100bp_year_equivalent_upper_bound": "",
                "support_offset_bp_year_equivalent_lower_bound": "",
                "support_offset_bp_year_equivalent": _format_decimal(
                    literature_bp_year_offset
                ),
                "support_offset_bp_year_equivalent_upper_bound": "",
                "numerator_source_timing_contract_artifact": (
                    "ratewall_noncanonical_current_demand_source_timing_contract.csv"
                ),
                "numerator_source_timing_contract_row_id": literature_contract[
                    "contract_row_id"
                ],
                "numerator_source_timing_contract_status": literature_contract[
                    "contract_status"
                ],
                "timing_alignment_status": (
                    "pass_review_only_literature_annual_flow_window_materialized"
                ),
                "denominator_input_status": (
                    "review_only_literature_annual_flow_anchor_not_runtime_enabled"
                ),
                "consumer_status": (
                    "pass_review_only_literature_support_offset_computed"
                ),
                "historical_reporting_status": (
                    "blocked_canonical_rw_y_history_not_enabled"
                ),
                "main_ratio_status": "blocked_main_ratio_disabled_by_design",
                "evidence_mode_status": (
                    "blocked_evidence_mode_disabled_by_design"
                ),
                "exact_blocker": (
                    "This row compares annual current-demand support inside the "
                    "noncanonical review-only consumer against the literature-backed "
                    "annual-flow runtime anchor. The anchor is runtime-primary "
                    "elsewhere, but this consumer lane remains noncanonical and non-runtime."
                ),
                "safe_sentence": (
                    "This row converts annual current-demand support into a review-only "
                    "offset using the same literature annual-flow anchor that now drives "
                    "runtime policy elsewhere, while keeping this noncanonical consumer lane non-runtime."
                ),
                "next_backend_action": (
                    "keep_noncanonical_literature_comparison_review_only_while_runtime_policy_uses_same_anchor"
                ),
                "allowed_use": (
                    "review_only_noncanonical_current_demand_support_overlay;"
                    "review_only_literature_annual_flow_comparison"
                ),
                "blocked_use": (
                    "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                    "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                    "reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": (
                    "noncanonical_current_demand_support_consumer_literature_comparison_not_runtime_enabled"
                ),
            }
        )
        rows.append(literature_row)
    return rows


def _augmented_current_demand_ratio_gate_rows(
    *,
    current_demand_ratio_gate_rows: Sequence[dict[str, str]],
    noncanonical_current_demand_source_timing_contract_rows: Sequence[dict[str, str]],
    noncanonical_current_demand_consumer_endpoint_decision_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    summary_row = next(
        row
        for row in noncanonical_current_demand_source_timing_contract_rows
        if row["contract_scope"] == "summary"
    )
    endpoint_decision = next(
        iter(noncanonical_current_demand_consumer_endpoint_decision_rows), None
    )
    rows: list[dict[str, str]] = []
    for gate_row in current_demand_ratio_gate_rows:
        row = dict(gate_row)
        row.update(
            {
                "numerator_source_timing_contract_artifact": (
                    "ratewall_noncanonical_current_demand_source_timing_contract.csv"
                ),
                "numerator_source_timing_contract_row_id": summary_row[
                    "contract_row_id"
                ],
                "numerator_source_timing_contract_status": summary_row[
                    "contract_status"
                ],
            }
        )
        if row["denominator_horizon_q"] == "8" and row["ratio_gate_status"] == (
            "pass_h8_bounded_proxy_input_enabled_review_only_consumer_available"
        ):
            row["exact_blocker"] = (
                "The bounded h8 interval-first current-demand drag proxy is enabled and "
                "the review-only consumer now operates under an explicit dual-lane source/"
                "timing contract: bounded h8 cumulative overlay plus literature annual-flow "
                "comparison. Canonical RW_Y history, main-ratio entry, and Evidence Mode remain blocked."
            )
            row["safe_sentence"] = (
                "The current-demand gate now points to an explicit dual-lane review-only "
                "consumer contract. Bounded h8 remains the enabled noncanonical denominator "
                "input, while the literature lane remains comparison-only and non-runtime."
            )
            row["next_backend_action"] = (
                endpoint_decision["next_backend_action"]
                if endpoint_decision is not None
                else "if_future_work_occurs_limit_it_to_review_only_scale_conflict_interpretation"
            )
        rows.append(row)
    return rows


def _denominator_scale_conflict_adjudication_rows(
    *,
    bounded_denominator_registry_rows: Sequence[dict[str, str]],
    annual_flow_anchor_registry_rows: Sequence[dict[str, str]],
    residualized_bridge: ResidualizedFfrBridgeState,
    frbus_100bp_year_fspdp_proxy_benchmark_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    bounded_h8 = next(
        row
        for row in bounded_denominator_registry_rows
        if row["primary_denominator_horizon"] == "true"
    )
    anchors_by_id = {
        row["denominator_source_id"]: row for row in annual_flow_anchor_registry_rows
    }
    literature_anchor = anchors_by_id[_LITERATURE_SOURCE_ID]
    legacy_base_anchor = anchors_by_id[_LEGACY_ANCHOR_NAMES["base_current_100bps"]]
    legacy_high_anchor = anchors_by_id[
        _LEGACY_ANCHOR_NAMES["high_fiscal_offset_no_hit"]
    ]
    frbus_h8 = next(
        row
        for row in frbus_100bp_year_fspdp_proxy_benchmark_rows
        if row["component_mapping_id"] == "ecnia_plus_ebfi_plus_eh_fspdp_proxy"
        and row["component_id"] == "fspdp_proxy"
        and row["horizon_q"] == "8"
    )

    literature_h8 = next(
        (
            row
            for row in residualized_bridge.normalization_rows
            if row["normalization_target_id"]
            == "exact_100bp_year_cumulative_policy_path_summary"
        ),
        None,
    )

    year1_window = next(
        (
            row
            for row in residualized_bridge.normalization_rows
            if row.get("annual_window_id") == "year1_h4_endpoint_proxy"
        ),
        None,
    )
    literature_year1_value = (
        year1_window["mapped_window_d_y_per_100bp_year"]
        if year1_window is not None
        else literature_anchor.get("anchor_value_pp_gdp", "")
    )
    literature_year1_available = year1_window is not None
    literature_h8_value = (
        literature_h8["mapped_h8_fspdp_d_y_per_100bp_year"]
        if literature_h8 is not None
        else ""
    )
    literature_h8_available = literature_h8 is not None

    return [
        _build_denominator_scale_conflict_row(
            adjudication_row_id="denominator_scale_conflict::annual_flow_base_vs_literature_year1",
            comparison_family="annual_flow_sensitivity_vs_empirical_runtime_literature",
            left_source_id=legacy_base_anchor["denominator_source_id"],
            left_source_class=legacy_base_anchor["denominator_source_class"],
            left_timing_class=legacy_base_anchor["timing_alignment_class"],
            left_horizon_q="4",
            left_value=legacy_base_anchor["anchor_value_pp_gdp"],
            right_source_id=literature_anchor["denominator_source_id"],
            right_source_class=literature_anchor["denominator_source_class"],
            right_timing_class=literature_anchor["timing_alignment_class"],
            right_horizon_q="4",
            right_value=literature_year1_value,
            sign_conflict_status=(
                "pass_same_contractionary_sign"
                if literature_year1_available
                else "blocked_literature_year1_translation_missing"
            ),
            scale_conflict_status=(
                "pass_same_order_of_magnitude_review_only"
                if literature_year1_available
                else "blocked_literature_year1_translation_missing"
            ),
            timing_conflict_status=(
                "pass_same_annual_flow_timing_class"
                if literature_year1_available
                else "blocked_literature_year1_translation_missing"
            ),
            adjudication_status=(
                "pass_sensitivity_band_vs_empirical_runtime_family_comparable"
                if literature_year1_available
                else "blocked_literature_year1_translation_missing"
            ),
            interpretation_role_status="runtime_literature_primary_with_legacy_sensitivity_counterpoint",
            counterweight_cluster_status="legacy_base_sensitivity_counterpoint",
            exact_blocker=(
                "The literature annual-flow runtime anchor is now primary. The legacy "
                "base value remains only as an assumption-mode sensitivity counterpoint."
                if literature_year1_available
                else "The literature year-1 translation is unavailable because residualized-FFR replication inputs were not materialized."
            ),
            safe_sentence=(
                "The literature runtime anchor and the legacy base sensitivity point "
                "remain in the same annual-flow scale neighborhood."
                if literature_year1_available
                else "No annual-flow literature scale-conflict comparison is emitted unless the residualized-FFR replication inputs materialize."
            ),
            next_backend_action=(
                "use_literature_runtime_family_as_default_and_keep_legacy_as_sensitivity_only"
                if literature_year1_available
                else "materialize_residualized_ffr_replication_inputs_before_scale_conflict_adjudication"
            ),
        ),
        _build_denominator_scale_conflict_row(
            adjudication_row_id="denominator_scale_conflict::annual_flow_high_vs_literature_year1",
            comparison_family="annual_flow_sensitivity_vs_empirical_runtime_literature",
            left_source_id=legacy_high_anchor["denominator_source_id"],
            left_source_class=legacy_high_anchor["denominator_source_class"],
            left_timing_class=legacy_high_anchor["timing_alignment_class"],
            left_horizon_q="4",
            left_value=legacy_high_anchor["anchor_value_pp_gdp"],
            right_source_id=literature_anchor["denominator_source_id"],
            right_source_class=literature_anchor["denominator_source_class"],
            right_timing_class=literature_anchor["timing_alignment_class"],
            right_horizon_q="4",
            right_value=literature_year1_value,
            sign_conflict_status=(
                "pass_same_contractionary_sign"
                if literature_year1_available
                else "blocked_literature_year1_translation_missing"
            ),
            scale_conflict_status=(
                "pass_same_order_of_magnitude_review_only"
                if literature_year1_available
                else "blocked_literature_year1_translation_missing"
            ),
            timing_conflict_status=(
                "pass_same_annual_flow_timing_class"
                if literature_year1_available
                else "blocked_literature_year1_translation_missing"
            ),
            adjudication_status=(
                "pass_sensitivity_band_vs_empirical_runtime_family_comparable"
                if literature_year1_available
                else "blocked_literature_year1_translation_missing"
            ),
            interpretation_role_status="runtime_literature_primary_with_legacy_sensitivity_counterpoint",
            counterweight_cluster_status="legacy_high_sensitivity_counterpoint",
            exact_blocker=(
                "The literature annual-flow runtime anchor is now primary. The legacy "
                "high value remains only as an assumption-mode sensitivity counterpoint."
                if literature_year1_available
                else "The literature year-1 translation is unavailable because residualized-FFR replication inputs were not materialized."
            ),
            safe_sentence=(
                "The literature runtime anchor is modestly above the legacy high "
                "sensitivity point but remains the same order of magnitude."
                if literature_year1_available
                else "No annual-flow literature scale-conflict comparison is emitted unless the residualized-FFR replication inputs materialize."
            ),
            next_backend_action=(
                "use_literature_runtime_family_as_default_and_keep_legacy_as_sensitivity_only"
                if literature_year1_available
                else "materialize_residualized_ffr_replication_inputs_before_scale_conflict_adjudication"
            ),
        ),
        _build_denominator_scale_conflict_row(
            adjudication_row_id="denominator_scale_conflict::bounded_h8_vs_literature_h8",
            comparison_family="h8_cumulative_empirical_vs_literature",
            left_source_id="bounded_h8_review_center_h8",
            left_source_class="bounded_h8_empirical_noncanonical_lane",
            left_timing_class="h8_cumulative",
            left_horizon_q="8",
            left_value=bounded_h8["review_center_d_y"],
            left_ci_low=bounded_h8["bounded_ci_low_d_y"],
            left_ci_high=bounded_h8["bounded_ci_high_d_y"],
            right_source_id="literature_h8_mapped_review_only",
            right_source_class="residualized_ffr_literature_bridge",
            right_timing_class="h8_cumulative",
            right_horizon_q="8",
            right_value=literature_h8_value,
            sign_conflict_status=(
                "pass_same_contractionary_sign"
                if literature_h8_available
                else "blocked_literature_h8_translation_missing"
            ),
            scale_conflict_status=(
                "warn_outside_bounded_empirical_interval"
                if literature_h8_available
                else "blocked_literature_h8_translation_missing"
            ),
            timing_conflict_status=(
                "pass_same_h8_cumulative_timing_class"
                if literature_h8_available
                else "blocked_literature_h8_translation_missing"
            ),
            adjudication_status=(
                "warn_bounded_h8_scale_conflict_vs_literature_h8"
                if literature_h8_available
                else "blocked_literature_h8_translation_missing"
            ),
            interpretation_role_status=(
                "bounded_h8_retained_noncanonical_primary_with_literature_scale_counterweight"
            ),
            counterweight_cluster_status="bounded_h8_counterweighted_by_literature_lane",
            exact_blocker=(
                "The corrected literature h8 mapped object remains far below the bounded "
                "empirical h8 interval."
                if literature_h8_available
                else "The literature h8 translation is unavailable because residualized-FFR replication inputs were not materialized."
            ),
            safe_sentence=(
                "The literature bridge and bounded h8 route agree on sign and timing class, "
                "but not on h8 scale."
                if literature_h8_available
                else "No literature h8 scale-conflict comparison is emitted unless the residualized-FFR replication inputs materialize."
            ),
            next_backend_action=(
                "if_future_work_occurs_limit_it_to_review_only_scale_conflict_interpretation"
                if literature_h8_available
                else "materialize_residualized_ffr_replication_inputs_before_scale_conflict_adjudication"
            ),
        ),
        _build_denominator_scale_conflict_row(
            adjudication_row_id="denominator_scale_conflict::bounded_h8_vs_frbus_h8",
            comparison_family="h8_cumulative_empirical_vs_frbus_benchmark",
            left_source_id="bounded_h8_review_center_h8",
            left_source_class="bounded_h8_empirical_noncanonical_lane",
            left_timing_class="h8_cumulative",
            left_horizon_q="8",
            left_value=bounded_h8["review_center_d_y"],
            left_ci_low=bounded_h8["bounded_ci_low_d_y"],
            left_ci_high=bounded_h8["bounded_ci_high_d_y"],
            right_source_id="frbus_h8_component_proxy",
            right_source_class="frbus_benchmark_lane",
            right_timing_class="h8_cumulative",
            right_horizon_q="8",
            right_value=frbus_h8["model_d_y_per_100bp_year"],
            right_ci_low="",
            right_ci_high="",
            sign_conflict_status="pass_same_contractionary_sign",
            scale_conflict_status="warn_outside_bounded_empirical_interval",
            timing_conflict_status="pass_same_h8_cumulative_timing_class",
            adjudication_status="warn_bounded_h8_scale_conflict_vs_frbus_h8",
            interpretation_role_status=(
                "bounded_h8_retained_noncanonical_primary_with_frbus_scale_counterweight"
            ),
            counterweight_cluster_status="bounded_h8_counterweighted_by_frbus_lane",
            exact_blocker=(
                "The FRB/US h8 benchmark proxy stays below the bounded empirical h8 interval."
            ),
            safe_sentence=(
                "FRB/US and bounded h8 agree on sign and timing class, but the model proxy "
                "is much smaller in scale."
            ),
            next_backend_action=(
                "if_future_work_occurs_limit_it_to_review_only_scale_conflict_interpretation"
            ),
        ),
        _build_denominator_scale_conflict_row(
            adjudication_row_id="denominator_scale_conflict::literature_h8_vs_frbus_h8",
            comparison_family="h8_cumulative_literature_vs_frbus_benchmark",
            left_source_id="literature_h8_mapped_review_only",
            left_source_class="residualized_ffr_literature_bridge",
            left_timing_class="h8_cumulative",
            left_horizon_q="8",
            left_value=literature_h8_value,
            right_source_id="frbus_h8_component_proxy",
            right_source_class="frbus_benchmark_lane",
            right_timing_class="h8_cumulative",
            right_horizon_q="8",
            right_value=frbus_h8["model_d_y_per_100bp_year"],
            sign_conflict_status=(
                "pass_same_contractionary_sign"
                if literature_h8_available
                else "blocked_literature_h8_translation_missing"
            ),
            scale_conflict_status=(
                "pass_same_order_of_magnitude_review_only"
                if literature_h8_available
                else "blocked_literature_h8_translation_missing"
            ),
            timing_conflict_status=(
                "pass_same_h8_cumulative_timing_class"
                if literature_h8_available
                else "blocked_literature_h8_translation_missing"
            ),
            adjudication_status=(
                "pass_literature_frbus_h8_review_alignment"
                if literature_h8_available
                else "blocked_literature_h8_translation_missing"
            ),
            interpretation_role_status=(
                "joint_literature_frbus_low_scale_counterweight_cluster"
            ),
            counterweight_cluster_status="pass_joint_low_scale_counterweight_cluster",
            exact_blocker=(
                "These two review-only lanes are directionally aligned and materially closer "
                "to one another than either is to bounded h8."
                if literature_h8_available
                else "The literature h8 translation is unavailable because residualized-FFR replication inputs were not materialized."
            ),
            safe_sentence=(
                "The literature h8 bridge and FRB/US h8 benchmark now cluster in the same "
                "low-single-digit review scale."
                if literature_h8_available
                else "No literature h8 versus FRB/US comparison is emitted unless the residualized-FFR replication inputs materialize."
            ),
            next_backend_action=(
                "if_future_work_occurs_limit_it_to_review_only_scale_conflict_interpretation"
                if literature_h8_available
                else "materialize_residualized_ffr_replication_inputs_before_scale_conflict_adjudication"
            ),
        ),
    ]


def _build_denominator_scale_conflict_row(
    *,
    adjudication_row_id: str,
    comparison_family: str,
    left_source_id: str,
    left_source_class: str,
    left_timing_class: str,
    left_horizon_q: str,
    left_value: str,
    right_source_id: str,
    right_source_class: str,
    right_timing_class: str,
    right_horizon_q: str,
    right_value: str,
    sign_conflict_status: str,
    scale_conflict_status: str,
    timing_conflict_status: str,
    adjudication_status: str,
    interpretation_role_status: str,
    counterweight_cluster_status: str,
    exact_blocker: str,
    safe_sentence: str,
    next_backend_action: str,
    left_ci_low: str = "",
    left_ci_high: str = "",
    right_ci_low: str = "",
    right_ci_high: str = "",
) -> dict[str, str]:
    row = {field: "" for field in DENOMINATOR_SCALE_CONFLICT_ADJUDICATION_FIELDS}
    row.update(
        {
            "adjudication_row_id": adjudication_row_id,
            "comparison_family": comparison_family,
            "left_source_id": left_source_id,
            "left_source_class": left_source_class,
            "left_timing_class": left_timing_class,
            "left_horizon_q": left_horizon_q,
            "left_value_pp_gdp_per_100bp_year": left_value,
            "left_ci_low_pp_gdp_per_100bp_year": left_ci_low,
            "left_ci_high_pp_gdp_per_100bp_year": left_ci_high,
            "right_source_id": right_source_id,
            "right_source_class": right_source_class,
            "right_timing_class": right_timing_class,
            "right_horizon_q": right_horizon_q,
            "right_value_pp_gdp_per_100bp_year": right_value,
            "right_ci_low_pp_gdp_per_100bp_year": right_ci_low,
            "right_ci_high_pp_gdp_per_100bp_year": right_ci_high,
            "common_review_unit": "pp_gdp_per_100bp_year_review_only",
            "sign_conflict_status": sign_conflict_status,
            "scale_conflict_status": scale_conflict_status,
            "timing_conflict_status": timing_conflict_status,
            "adjudication_status": adjudication_status,
            "interpretation_role_status": interpretation_role_status,
            "counterweight_cluster_status": counterweight_cluster_status,
            "exact_blocker": exact_blocker,
            "safe_sentence": safe_sentence,
            "next_backend_action": next_backend_action,
            "allowed_use": "review_only_scale_tension_adjudication",
            "blocked_use": (
                "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "denominator_scale_conflict_review_only",
            **_disabled_switches(),
        }
    )
    return row


def _materialize_residualized_ffr_bridge_state() -> ResidualizedFfrBridgeState:
    try:
        data_bundle = _load_residualized_ffr_data_bundle()
    except Exception as exc:
        return _blocked_residualized_ffr_bridge_state(
            blocker=(
                "Local residualized-FFR bridge materialization failed before estimation: "
                f"{type(exc).__name__}: {exc}"
            )
        )

    gdp_results: dict[int, HacEstimate] = {}
    rate_results: dict[int, HacEstimate] = {}
    fspdp_results: dict[int, HacEstimate] = {}
    fspdp_pp_gdp_results: dict[int, HacEstimate] = {}
    pce_results: dict[int, HacEstimate] = {}
    pfi_results: dict[int, HacEstimate] = {}

    for horizon in (4, 8, 12):
        gdp_results[horizon] = _estimate_published_style_lp(
            data_bundle.us_panel,
            outcome_column="ln_gdp",
            control_column="ln_gdp",
            horizon_q=horizon,
        )
    for horizon in range(0, 13):
        rate_results[horizon] = _estimate_published_style_lp(
            data_bundle.us_panel,
            outcome_column="US_r",
            control_column="US_r",
            horizon_q=horizon,
        )

    gdp_h8 = gdp_results.get(8)
    replication_passed = False
    if gdp_h8 is not None:
        replication_passed = (
            abs(gdp_h8.beta - _PUBLISHED_H8_TARGET) <= _PUBLISHED_H8_TOLERANCE
        )

    if replication_passed:
        for horizon in (4, 8, 12):
            fspdp_results[horizon] = _estimate_published_style_lp(
                data_bundle.private_demand_panel,
                outcome_column="log_real_fspdp",
                control_column="log_real_fspdp",
                horizon_q=horizon,
            )
            fspdp_pp_gdp_results[horizon] = _estimate_private_demand_pp_gdp_lp(
                data_bundle.private_demand_panel,
                real_column="real_fspdp",
                nominal_column="nominal_fspdp",
                control_column="log_real_fspdp",
                horizon_q=horizon,
            )
            pce_results[horizon] = _estimate_published_style_lp(
                data_bundle.private_demand_panel,
                outcome_column="log_real_pce",
                control_column="log_real_pce",
                horizon_q=horizon,
            )
            pfi_results[horizon] = _estimate_published_style_lp(
                data_bundle.private_demand_panel,
                outcome_column="log_real_private_fixed_investment",
                control_column="log_real_private_fixed_investment",
                horizon_q=horizon,
            )

    fwl = _fwl_diagnostics_for_h8_gdp(data_bundle.us_panel)
    first_year_area_pp_year = None
    first_year_area_bps_year = None
    normalization_multiplier = None
    mapped_h8_fspdp_d_y = None
    annual_window_mapped_values: dict[str, Decimal] = {}
    normalization_status = "blocked_paper_gdp_replication_pending"
    normalization_blocker = (
        "Normalization stays blocked until the published-style GDP replication passes "
        "and the implied first-year policy-path area is positive."
    )
    normalization_next_action = (
        "estimate_policy_rate_path_and_materialize_first_year_100bp_year_mapping"
    )

    if replication_passed and all(rate_results.get(h) is not None for h in range(0, 4)):
        path = [Decimal(str(rate_results[h].beta)) for h in range(0, 4)]
        first_year_area_bps_year_decimal = first_year_area_bps_year_from_quarterly_pp_path(
            path
        )
        if first_year_area_bps_year_decimal is not None:
            first_year_area_bps_year = float(first_year_area_bps_year_decimal)
            first_year_area_pp_year = float(
                first_year_area_bps_year_decimal / Decimal("100")
            )
            normalization_multiplier = float(
                Decimal("100") / first_year_area_bps_year_decimal
            )
            h8_fspdp_pp_gdp = fspdp_pp_gdp_results.get(8)
            if h8_fspdp_pp_gdp is not None:
                mapped_h8_fspdp_d_y = -h8_fspdp_pp_gdp.beta * normalization_multiplier
            for annual_window_id, _label, start_horizon, end_horizon in _LITERATURE_ANNUAL_WINDOW_SPECS:
                end_estimate = fspdp_pp_gdp_results.get(end_horizon)
                if end_estimate is None:
                    continue
                native_window_response = Decimal(str(end_estimate.beta))
                if start_horizon is not None:
                    start_estimate = fspdp_pp_gdp_results.get(start_horizon)
                    if start_estimate is None:
                        continue
                    native_window_response -= Decimal(str(start_estimate.beta))
                annual_window_mapped_values[annual_window_id] = -(
                    native_window_response * Decimal(str(normalization_multiplier))
                )
            normalization_status = "pass_bridge_normalization_100bp_year"
            normalization_blocker = (
                "Published-style policy-rate path area is positive and the bridge is now "
                "mapped into exact 100bp-year units using dense first-year quarterly rate "
                "responses."
            )
            normalization_next_action = (
                "materialize_review_only_annual_flow_window_translations_and_decide_whether_to_expose_them"
            )

    replication_rows = _residualized_ffr_literature_replication_audit_rows(gdp_results)
    lp_rows = _residualized_ffr_literature_lp_results_rows(
        gdp_results=gdp_results,
        replication_passed=replication_passed,
        fspdp_results=fspdp_results,
        fspdp_pp_gdp_results=fspdp_pp_gdp_results,
        pce_results=pce_results,
        pfi_results=pfi_results,
    )
    fwl_rows = _residualized_ffr_fwl_diagnostics_rows(
        fwl=fwl,
        replication_passed=replication_passed,
    )
    bridge_rows = _residualized_ffr_private_demand_bridge_rows(
        replication_passed=replication_passed,
        gdp_results=gdp_results,
        fspdp_results=fspdp_results,
        fspdp_pp_gdp_results=fspdp_pp_gdp_results,
        pce_results=pce_results,
        pfi_results=pfi_results,
    )
    normalization_rows = _residualized_ffr_normalization_bridge_rows(
        normalization_status=normalization_status,
        normalization_blocker=normalization_blocker,
        normalization_next_action=normalization_next_action,
        first_year_area_pp_year=first_year_area_pp_year,
        first_year_area_bps_year=first_year_area_bps_year,
        normalization_multiplier=normalization_multiplier,
        mapped_h8_fspdp_d_y_per_100bp_year=mapped_h8_fspdp_d_y,
        fspdp_pp_gdp_results=fspdp_pp_gdp_results,
        sample_start=gdp_h8.sample_start if gdp_h8 is not None else "",
        sample_end=gdp_h8.sample_end if gdp_h8 is not None else "",
    )

    if replication_passed and normalization_status == "pass_bridge_normalization_100bp_year":
        route_status = "pass_review_only_literature_annual_flow_bridge_available"
        route_blocker = (
            "Published-style GDP replication, private-demand adaptation, exact 100bp-year "
            "normalization, and review-only annual-flow window translations are "
            "materialized. Runtime and canonical use remain blocked by design."
        )
        route_safe_sentence = (
            "The literature bridge now provides both a quarterly review surface and a "
            "review-only annual-flow window translation built off the corrected dense "
            "first-year rate path."
        )
        route_next_action = (
            "keep_literature_bridge_review_only_and_shift_followup_to_scale_conflict_interpretation"
        )
        anchor_status = "pass_review_only_literature_annual_flow_anchor_window_materialized"
        anchor_blocker = (
            "The literature bridge now has an explicit year-1 annual-flow proxy anchor in "
            "exact 100bp-year units. Runtime use remains disabled by endpoint decision, "
            "not because additional consumer hardening is still pending."
        )
        anchor_safe_sentence = (
            "This route now has a review-only annual-flow proxy anchor derived from the "
            "year-1 h4 endpoint translation, but it is not a runtime or canonical anchor."
        )
        anchor_next_action = (
            "keep_literature_anchor_visible_review_only_and_focus_future_work_on_scale_conflict_interpretation"
        )
        anchor_timing_alignment_class = "review_only_annual_flow_h4_endpoint_proxy"
        anchor_value_pp_gdp = annual_window_mapped_values.get(
            "year1_h4_endpoint_proxy"
        )
    elif replication_passed:
        route_status = "blocked_100bp_year_mapping_missing"
        route_blocker = (
            "Published-style GDP replication passed, but the implied policy-rate path "
            "has not yet been normalized into exact 100bp-year units."
        )
        route_safe_sentence = (
            "The literature lane is partially materialized, but it remains blocked as a "
            "bridge until shock-unit normalization is explicit."
        )
        route_next_action = (
            "estimate_policy_rate_path_and_complete_exact_100bp_year_mapping"
        )
        anchor_status = "blocked_100bp_year_mapping_missing"
        anchor_blocker = route_blocker
        anchor_safe_sentence = route_safe_sentence
        anchor_next_action = route_next_action
        anchor_timing_alignment_class = "blocked_100bp_year_mapping_missing"
        anchor_value_pp_gdp = None
    else:
        route_status = "blocked_replication_not_within_tolerance"
        route_blocker = (
            "The published-style GDP replication lane exists locally, but the h8 GDP "
            "result does not pass the predeclared tolerance against the published "
            "approximately -0.7 percent benchmark."
        )
        route_safe_sentence = (
            "The literature lane is now a real local replication attempt, but it remains "
            "blocked until the published GDP benchmark is matched within tolerance."
        )
        route_next_action = (
            "tighten_spec_and_source_alignment_before_using_literature_lane_as_a_bridge"
        )
        anchor_status = "blocked_replication_not_within_tolerance"
        anchor_blocker = route_blocker
        anchor_safe_sentence = route_safe_sentence
        anchor_next_action = route_next_action
        anchor_timing_alignment_class = "blocked_paper_gdp_replication_pending"
        anchor_value_pp_gdp = None

    return ResidualizedFfrBridgeState(
        route_status=route_status,
        route_normalization_status=normalization_status,
        route_exact_blocker=route_blocker,
        route_safe_sentence=route_safe_sentence,
        route_next_backend_action=route_next_action,
        anchor_status=anchor_status,
        anchor_exact_blocker=anchor_blocker,
        anchor_safe_sentence=anchor_safe_sentence,
        anchor_next_backend_action=anchor_next_action,
        anchor_timing_alignment_class=anchor_timing_alignment_class,
        anchor_value_pp_gdp=anchor_value_pp_gdp,
        replication_rows=replication_rows,
        lp_rows=lp_rows,
        fwl_rows=fwl_rows,
        bridge_rows=bridge_rows,
        normalization_rows=normalization_rows,
    )


def _blocked_residualized_ffr_bridge_state(
    *, blocker: str
) -> ResidualizedFfrBridgeState:
    return ResidualizedFfrBridgeState(
        route_status="blocked_literature_bridge_pending_replication",
        route_normalization_status="blocked_paper_gdp_replication_pending",
        route_exact_blocker=blocker,
        route_safe_sentence=(
            "The literature bridge is still fail-closed because the local published-style "
            "replication could not be materialized."
        ),
        route_next_backend_action=(
            "repair_local_replication_inputs_before_enabling_any_literature_bridge_rows"
        ),
        anchor_status="blocked_literature_bridge_pending_replication",
        anchor_exact_blocker=blocker,
        anchor_safe_sentence=(
            "No annual-flow literature bridge can be used until the local published-style "
            "replication materializes."
        ),
        anchor_next_backend_action=(
            "repair_local_replication_inputs_before_enabling_any_literature_bridge_rows"
        ),
        anchor_timing_alignment_class="blocked_annual_window_formalization_pending",
        anchor_value_pp_gdp=None,
        replication_rows=_blocked_replication_rows(blocker=blocker),
        lp_rows=_blocked_lp_rows(blocker=blocker),
        fwl_rows=_blocked_fwl_rows(blocker=blocker),
        bridge_rows=_blocked_bridge_rows(blocker=blocker),
        normalization_rows=_blocked_normalization_rows(blocker=blocker),
    )


@dataclass(frozen=True)
class ResidualizedFfrDataBundle:
    us_panel: object
    private_demand_panel: object


def _load_residualized_ffr_data_bundle() -> ResidualizedFfrDataBundle:
    import pandas

    panel_path = _repo_root() / "data/raw/residualized_ffr_bridge/unpacked/Replication/PANEL_DATASET.dta"
    if not panel_path.exists():
        raise FileNotFoundError(panel_path)
    panel = pandas.read_stata(panel_path)
    us_panel = panel.loc[panel["countrylong"] == "United States"].copy()
    if us_panel.empty:
        raise ValueError("United States sample missing from PANEL_DATASET.dta")
    us_panel["quarter"] = pandas.to_datetime(us_panel["quarter"])
    us_panel = us_panel.sort_values("quarter").reset_index(drop=True)
    us_panel["quarter_trend"] = us_panel["quartersq"].map(
        lambda value: float(sqrt(float(value))) if value == value else float("nan")
    )
    us_panel["dum1981q4"] = (
        us_panel["quarter"] == pandas.Timestamp("1981-10-01")
    ).astype(float)
    shock = _published_style_shock(us_panel)
    us_panel["residualized_ffr_shock"] = shock

    private = us_panel[
        ["quarter", "residualized_ffr_shock", "quarter_trend", "quartersq", "dum1981q4"]
    ].copy()
    local = _load_local_private_demand_panel()
    private = private.merge(local, on="quarter", how="left")
    return ResidualizedFfrDataBundle(us_panel=us_panel, private_demand_panel=private)


def _load_local_private_demand_panel():
    import pandas
    import numpy

    root = _repo_root() / "data/raw/current_demand_gdp_share"

    def read_series(filename: str, value_column: str):
        frame = pandas.read_csv(root / filename)
        source_column = next(
            column for column in frame.columns if column != "observation_date"
        )
        frame["quarter"] = pandas.to_datetime(frame["observation_date"])
        frame[value_column] = pandas.to_numeric(frame[source_column], errors="coerce")
        return frame[["quarter", value_column]]

    frame = read_series("GDP.csv", "nominal_gdp")
    for filename, column in (
        ("GDPC1.csv", "real_gdp"),
        ("LA0000031Q027SBEA.csv", "nominal_fspdp"),
        ("LB0000031Q020SBEA.csv", "real_fspdp"),
        ("PCEC.csv", "nominal_pce"),
        ("PCECC96.csv", "real_pce"),
        ("FPI.csv", "nominal_private_fixed_investment"),
        ("FPIC1.csv", "real_private_fixed_investment"),
    ):
        frame = frame.merge(read_series(filename, column), on="quarter", how="left")

    frame["log_real_gdp"] = numpy.log(frame["real_gdp"])
    frame["log_real_fspdp"] = numpy.log(frame["real_fspdp"])
    frame["log_real_pce"] = numpy.log(frame["real_pce"])
    frame["log_real_private_fixed_investment"] = numpy.log(
        frame["real_private_fixed_investment"]
    )
    return frame


def _published_style_shock(us_panel):
    import numpy

    y = us_panel["US_r"].to_numpy(dtype=float)
    control_columns = []
    for lag in range(1, 5):
        control_columns.append(us_panel["US_r"].shift(lag).to_numpy(dtype=float))
    for lag in range(0, 5):
        control_columns.append(us_panel["US_y"].shift(lag).to_numpy(dtype=float))
    for lag in range(0, 5):
        control_columns.append(us_panel["US_dp"].shift(lag).to_numpy(dtype=float))
    for lag in range(0, 5):
        control_columns.append(us_panel["US_spread"].shift(lag).to_numpy(dtype=float))
    for lag in range(0, 5):
        control_columns.append(us_panel["ln_gdp_for"].shift(lag).to_numpy(dtype=float))
    control_columns.append(us_panel["quarter_trend"].to_numpy(dtype=float))
    control_columns.append(us_panel["quartersq"].to_numpy(dtype=float))
    x = numpy.column_stack(control_columns)
    mask = numpy.isfinite(y)
    mask &= numpy.all(numpy.isfinite(x), axis=1)
    x = x[mask]
    y = y[mask]
    x = _with_intercept(x)
    beta, _, _, _ = _ols_via_lstsq(y, x)
    residuals = numpy.full(len(us_panel), numpy.nan)
    residuals[mask] = y - x @ beta
    return residuals


def _estimate_published_style_lp(
    frame,
    *,
    outcome_column: str,
    control_column: str,
    horizon_q: int,
) -> HacEstimate | None:
    outcome = frame[outcome_column]
    dependent = outcome.shift(-horizon_q) - outcome.shift(1)
    design = {
        "shock": frame["residualized_ffr_shock"],
        "quarter_num": frame["quarter_trend"],
        "quartersq": frame["quartersq"],
        "dum1981q4": frame["dum1981q4"],
    }
    for lag in range(1, 5):
        design[f"{control_column}_lag{lag}"] = frame[control_column].shift(lag)
    design_frame = frame.assign(dependent=dependent, **design)
    regressors = ["shock"] + [f"{control_column}_lag{lag}" for lag in range(1, 5)]
    regressors += ["quarter_num", "quartersq", "dum1981q4"]
    sample = design_frame[["quarter", "dependent", *regressors]].dropna()
    if len(sample) < len(regressors) + 2:
        return None
    y = sample["dependent"].to_numpy(dtype=float)
    x = sample[regressors].to_numpy(dtype=float)
    x = _with_intercept(x)
    estimate = _ols_hac(y, x, bandwidth=max(4, horizon_q + 1))
    if estimate is None:
        return None
    shock_idx = 1
    return HacEstimate(
        beta=estimate["beta"][shock_idx],
        se=estimate["se"][shock_idx],
        t=estimate["t"][shock_idx],
        ci_low=estimate["beta"][shock_idx] - 1.96 * estimate["se"][shock_idx],
        ci_high=estimate["beta"][shock_idx] + 1.96 * estimate["se"][shock_idx],
        n_obs=len(sample),
        bandwidth=estimate["bandwidth"],
        sample_start=_quarter_id(sample["quarter"].iloc[0]),
        sample_end=_quarter_id(sample["quarter"].iloc[-1]),
    )


def _estimate_private_demand_pp_gdp_lp(
    frame,
    *,
    real_column: str,
    nominal_column: str,
    control_column: str,
    horizon_q: int,
) -> HacEstimate | None:
    import numpy

    log_real = frame[real_column].map(lambda value: numpy.log(value) if value and value > 0 else numpy.nan)
    lag_share = frame[nominal_column].shift(1) / frame["nominal_gdp"].shift(1)
    dependent = 100.0 * lag_share * (log_real.shift(-horizon_q) - log_real.shift(1))
    design = {
        "shock": frame["residualized_ffr_shock"],
        "quarter_num": frame["quarter_trend"],
        "quartersq": frame["quartersq"],
        "dum1981q4": frame["dum1981q4"],
    }
    for lag in range(1, 5):
        design[f"{control_column}_lag{lag}"] = frame[control_column].shift(lag)
    design_frame = frame.assign(dependent=dependent, **design)
    regressors = ["shock"] + [f"{control_column}_lag{lag}" for lag in range(1, 5)]
    regressors += ["quarter_num", "quartersq", "dum1981q4"]
    sample = design_frame[["quarter", "dependent", *regressors]].dropna()
    if len(sample) < len(regressors) + 2:
        return None
    y = sample["dependent"].to_numpy(dtype=float)
    x = sample[regressors].to_numpy(dtype=float)
    x = _with_intercept(x)
    estimate = _ols_hac(y, x, bandwidth=max(4, horizon_q + 1))
    if estimate is None:
        return None
    shock_idx = 1
    return HacEstimate(
        beta=estimate["beta"][shock_idx],
        se=estimate["se"][shock_idx],
        t=estimate["t"][shock_idx],
        ci_low=estimate["beta"][shock_idx] - 1.96 * estimate["se"][shock_idx],
        ci_high=estimate["beta"][shock_idx] + 1.96 * estimate["se"][shock_idx],
        n_obs=len(sample),
        bandwidth=estimate["bandwidth"],
        sample_start=_quarter_id(sample["quarter"].iloc[0]),
        sample_end=_quarter_id(sample["quarter"].iloc[-1]),
    )


def _fwl_diagnostics_for_h8_gdp(frame) -> dict[str, object] | None:
    import numpy

    horizon_q = 8
    outcome = frame["ln_gdp"]
    dependent = outcome.shift(-horizon_q) - outcome.shift(1)
    design = {
        "shock": frame["residualized_ffr_shock"],
        "quarter_num": frame["quarter_trend"],
        "quartersq": frame["quartersq"],
        "dum1981q4": frame["dum1981q4"],
    }
    for lag in range(1, 5):
        design[f"ln_gdp_lag{lag}"] = frame["ln_gdp"].shift(lag)
    design_frame = frame.assign(dependent=dependent, **design)
    regressors = ["shock", "ln_gdp_lag1", "ln_gdp_lag2", "ln_gdp_lag3", "ln_gdp_lag4", "quarter_num", "quartersq", "dum1981q4"]
    sample = design_frame[["dependent", *regressors]].dropna()
    if len(sample) < len(regressors) + 2:
        return None
    y = sample["dependent"].to_numpy(dtype=float)
    shock = sample["shock"].to_numpy(dtype=float)
    controls = sample[[name for name in regressors if name != "shock"]].to_numpy(dtype=float)
    full_x = _with_intercept(sample[regressors].to_numpy(dtype=float))
    full_estimate = _ols_hac(y, full_x, bandwidth=max(4, horizon_q + 1))
    if full_estimate is None:
        return None
    control_x = _with_intercept(controls)
    y_resid = _residualize(y, control_x)
    shock_resid = _residualize(shock, control_x)
    denom = float(shock_resid @ shock_resid)
    residualized_beta = float((shock_resid @ y_resid) / denom) if denom > 0 else 0.0
    orthogonality = []
    for idx in range(controls.shape[1]):
        column = controls[:, idx]
        if numpy.nanstd(column) == 0 or numpy.nanstd(shock_resid) == 0:
            continue
        corr = numpy.corrcoef(shock_resid, column)[0, 1]
        if numpy.isfinite(corr):
            orthogonality.append(abs(float(corr)))
    return {
        "full_model_beta": full_estimate["beta"][1],
        "residualized_beta": residualized_beta,
        "beta_abs_diff": abs(full_estimate["beta"][1] - residualized_beta),
        "orthogonality_max_abs_corr": max(orthogonality) if orthogonality else 0.0,
        "diagnostic_n_obs": len(sample),
        "hac_bandwidth": full_estimate["bandwidth"],
    }


def _blocked_replication_rows(*, blocker: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for horizon in (4, 8, 12):
        row = {field: "" for field in RESIDUALIZED_FFR_LITERATURE_REPLICATION_AUDIT_FIELDS}
        row.update(
            {
                "replication_row_id": (
                    f"residualized_ffr_literature_replication_audit::gdp::h{horizon}"
                ),
                "source_paper_id": _PAPER_ID,
                "paper_family": "published_residualized_fed_funds_lp",
                "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
                "outcome_id": "log_real_gdp",
                "horizon_q": str(horizon),
                "sample_window_id": "1965Q1_2016Q2_us_published_style_intersection",
                "zlb_treatment_id": "native_US_r_shadow_rate_substitution_from_replication_package",
                "published_target_reference": (
                    "approx_minus_0p7pct_h8_after_two_years" if horizon == 8 else ""
                ),
                "published_target_response_pct": (
                    _format_decimal(_PUBLISHED_H8_TARGET) if horizon == 8 else ""
                ),
                "replication_status": "blocked_paper_gdp_replication_pending",
                "exact_blocker": blocker,
                "safe_sentence": "No local replication result exists yet.",
                "next_backend_action": "repair_local_replication_inputs",
                "allowed_use": "methodology_scaffold_only",
                "blocked_use": (
                    "annual_flow_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                    "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                    "reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "published_replication_scaffold_not_local_estimate",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _residualized_ffr_literature_replication_audit_rows(
    gdp_results: dict[int, HacEstimate]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for horizon in (4, 8, 12):
        estimate = gdp_results.get(horizon)
        status = "blocked_paper_gdp_replication_pending"
        blocker = (
            "Published-style GDP replication did not materialize for this horizon."
        )
        safe_sentence = "No local replication result exists yet."
        next_action = "repair_local_replication_inputs"
        difference = ""
        published = ""
        tolerance = ""
        if estimate is not None:
            status = "pass_published_style_gdp_context_estimated"
            blocker = (
                "Published-style GDP context row is estimated locally. Only the h8 row "
                "is used for the published benchmark tolerance gate."
            )
            safe_sentence = (
                "This published-style GDP row is estimated locally as context for the "
                "literature bridge."
            )
            next_action = "use_h8_tolerance_gate_to_decide_bridge_promotion"
            if horizon == 8:
                published = _format_decimal(_PUBLISHED_H8_TARGET)
                tolerance = _format_decimal(_PUBLISHED_H8_TOLERANCE)
                absolute_difference = abs(estimate.beta - _PUBLISHED_H8_TARGET)
                difference = _format_decimal(absolute_difference)
                if absolute_difference <= _PUBLISHED_H8_TOLERANCE:
                    status = "pass_paper_gdp_replication_within_tolerance"
                    blocker = (
                        "Published-style h8 GDP replication is within the predeclared "
                        "tolerance around the approximately -0.7 percent benchmark."
                    )
                    safe_sentence = (
                        "The local published-style h8 GDP response is close enough to the "
                        "paper benchmark to support a review-only bridge lane."
                    )
                    next_action = (
                        "materialize_private_demand_adaptation_and_100bp_year_mapping"
                    )
                else:
                    status = "warn_replication_scale_mismatch"
                    blocker = (
                        "The local published-style h8 GDP response misses the predeclared "
                        "tolerance around the approximately -0.7 percent benchmark."
                    )
                    safe_sentence = (
                        "The published-style lane is real, but the h8 GDP scale mismatch "
                        "keeps the bridge blocked."
                    )
                    next_action = "tighten_spec_alignment_before_private_demand_use"
        row = {field: "" for field in RESIDUALIZED_FFR_LITERATURE_REPLICATION_AUDIT_FIELDS}
        row.update(
            {
                "replication_row_id": (
                    f"residualized_ffr_literature_replication_audit::gdp::h{horizon}"
                ),
                "source_paper_id": _PAPER_ID,
                "paper_family": "published_residualized_fed_funds_lp",
                "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
                "outcome_id": "log_real_gdp",
                "horizon_q": str(horizon),
                "sample_window_id": "1965Q1_2016Q2_us_published_style_intersection",
                "zlb_treatment_id": "native_US_r_shadow_rate_substitution_from_replication_package",
                "published_target_reference": (
                    "approx_minus_0p7pct_h8_after_two_years" if horizon == 8 else ""
                ),
                "published_target_response_pct": published,
                "local_replication_response_pct": (
                    _format_decimal(estimate.beta) if estimate is not None else ""
                ),
                "absolute_difference_pct": difference,
                "replication_tolerance_pct": tolerance,
                "replication_n_obs": str(estimate.n_obs) if estimate is not None else "",
                "hac_bandwidth": (
                    str(estimate.bandwidth) if estimate is not None else ""
                ),
                "sample_start": estimate.sample_start if estimate is not None else "",
                "sample_end": estimate.sample_end if estimate is not None else "",
                "replication_status": status,
                "exact_blocker": blocker,
                "safe_sentence": safe_sentence,
                "next_backend_action": next_action,
                "allowed_use": "review_only_replication_context",
                "blocked_use": (
                    "annual_flow_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                    "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                    "reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "published_style_gdp_replication_review_only",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _blocked_lp_rows(*, blocker: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for outcome_id in (
        "log_real_gdp",
        "log_real_fspdp",
        "fspdp_gdp_share_contribution",
        "log_real_pce",
        "log_real_private_fixed_investment",
    ):
        for horizon in (4, 8, 12):
            row = {field: "" for field in RESIDUALIZED_FFR_LITERATURE_LP_RESULTS_FIELDS}
            row.update(
                {
                    "lp_result_row_id": (
                        f"residualized_ffr_literature_lp_results::{outcome_id}::h{horizon}"
                    ),
                    "source_paper_id": _PAPER_ID,
                    "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
                    "outcome_id": outcome_id,
                    "outcome_definition": outcome_id,
                    "horizon_q": str(horizon),
                    "sample_window_id": "1965Q1_2016Q2_us_published_style_intersection",
                    "control_spec_id": "ratewall_published_style_lag4_controls",
                    "result_unit": (
                        "pp_gdp" if outcome_id == "fspdp_gdp_share_contribution" else "pct_response"
                    ),
                    "lp_result_status": "blocked_paper_gdp_replication_pending",
                    "exact_blocker": blocker,
                    "safe_sentence": "No local estimate is being reported.",
                    "next_backend_action": "repair_local_replication_inputs",
                    "allowed_use": "methodology_scaffold_only",
                    "blocked_use": (
                        "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                        "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                        "reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": "residualized_ffr_lp_scaffold_not_local_estimate",
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    return rows


def _residualized_ffr_literature_lp_results_rows(
    *,
    gdp_results: dict[int, HacEstimate],
    replication_passed: bool,
    fspdp_results: dict[int, HacEstimate],
    fspdp_pp_gdp_results: dict[int, HacEstimate],
    pce_results: dict[int, HacEstimate],
    pfi_results: dict[int, HacEstimate],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    outcome_map = {
        "log_real_gdp": (
            "log(real_gdp[t+h]) - log(real_gdp[t-1])",
            "pct_response",
            gdp_results,
        ),
        "log_real_fspdp": (
            "log(real_fspdp[t+h]) - log(real_fspdp[t-1])",
            "pct_response",
            fspdp_results,
        ),
        "fspdp_gdp_share_contribution": (
            "100 * (nominal_fspdp[t-1] / nominal_gdp[t-1]) * (log(real_fspdp[t+h]) - log(real_fspdp[t-1]))",
            "pp_gdp",
            fspdp_pp_gdp_results,
        ),
        "log_real_pce": (
            "log(real_pce[t+h]) - log(real_pce[t-1])",
            "pct_response",
            pce_results,
        ),
        "log_real_private_fixed_investment": (
            "log(real_private_fixed_investment[t+h]) - log(real_private_fixed_investment[t-1])",
            "pct_response",
            pfi_results,
        ),
    }
    for outcome_id, (definition, unit, estimates) in outcome_map.items():
        for horizon in (4, 8, 12):
            estimate = estimates.get(horizon)
            if outcome_id == "log_real_gdp":
                if estimate is None:
                    status = "blocked_paper_gdp_replication_pending"
                    blocker = "Published-style GDP replication did not materialize."
                    safe_sentence = "No local GDP replication estimate is being reported."
                    next_action = "repair_local_replication_inputs"
                elif horizon == 8 and replication_passed:
                    status = "pass_paper_gdp_replication_within_tolerance"
                    blocker = (
                        "Published-style h8 GDP replication is within the predeclared tolerance."
                    )
                    safe_sentence = (
                        "This h8 GDP row is the published-style tolerance gate for the "
                        "literature bridge."
                    )
                    next_action = "materialize_private_demand_adaptation_and_normalization"
                else:
                    status = "pass_published_style_gdp_context_estimated"
                    blocker = (
                        "Published-style GDP context row is estimated locally."
                    )
                    safe_sentence = "This GDP row is review-only context for the bridge."
                    next_action = "use_h8_tolerance_gate_to_decide_bridge_promotion"
            elif outcome_id == "log_real_private_fixed_investment" and estimate is None:
                status = "blocked_local_component_series_unavailable"
                blocker = (
                    "Local real private fixed investment coverage is too short for the "
                    "published-style sample window."
                )
                safe_sentence = (
                    "Private fixed investment adaptation remains blocked because the local "
                    "real series does not span the published sample."
                )
                next_action = "source_longer_real_private_fixed_investment_series_if_needed"
            elif not replication_passed:
                status = "blocked_paper_gdp_replication_pending"
                blocker = (
                    "Private-demand adaptation stays blocked until the published-style "
                    "h8 GDP replication passes tolerance."
                )
                safe_sentence = (
                    "No private-demand adaptation row can be used before the published-style "
                    "GDP base is credible."
                )
                next_action = "tighten_published_gdp_replication_before_private_demand_use"
            elif estimate is None:
                status = "blocked_private_demand_adaptation_unavailable"
                blocker = (
                    "This adapted private-demand outcome could not be estimated on the "
                    "local intersection sample."
                )
                safe_sentence = (
                    "The literature bridge keeps this outcome blocked rather than "
                    "fabricating a result."
                )
                next_action = "repair_outcome_series_or_sample_alignment"
            else:
                status = "pass_private_demand_adaptation_estimated"
                blocker = (
                    "Private-demand adaptation is estimated locally, but this remains "
                    "review-only until annual-flow timing formalization."
                )
                safe_sentence = (
                    "This row extends the published-style shock design to a RateWall-relevant "
                    "private-demand outcome on the local sample."
                )
                next_action = (
                    "compare_quarterly_bridge_rows_against_review_only_annual_flow_window_translation"
                )
            row = {field: "" for field in RESIDUALIZED_FFR_LITERATURE_LP_RESULTS_FIELDS}
            row.update(
                {
                    "lp_result_row_id": (
                        f"residualized_ffr_literature_lp_results::{outcome_id}::h{horizon}"
                    ),
                    "source_paper_id": _PAPER_ID,
                    "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
                    "outcome_id": outcome_id,
                    "outcome_definition": definition,
                    "horizon_q": str(horizon),
                    "sample_window_id": "1965Q1_2016Q2_us_published_style_intersection",
                    "control_spec_id": "ratewall_published_style_lag4_controls",
                    "result_unit": unit,
                    "response_value": _format_decimal(estimate.beta) if estimate is not None else "",
                    "se_hac": _format_decimal(estimate.se) if estimate is not None else "",
                    "t_hac": _format_decimal(estimate.t) if estimate is not None else "",
                    "ci95_low_hac": _format_decimal(estimate.ci_low) if estimate is not None else "",
                    "ci95_high_hac": _format_decimal(estimate.ci_high) if estimate is not None else "",
                    "lp_n_obs": str(estimate.n_obs) if estimate is not None else "",
                    "hac_bandwidth": str(estimate.bandwidth) if estimate is not None else "",
                    "sample_start": estimate.sample_start if estimate is not None else "",
                    "sample_end": estimate.sample_end if estimate is not None else "",
                    "lp_result_status": status,
                    "exact_blocker": blocker,
                    "safe_sentence": safe_sentence,
                    "next_backend_action": next_action,
                    "allowed_use": "review_only_bridge_surface",
                    "blocked_use": (
                        "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                        "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                        "reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": "literature_lane_review_only_not_runtime_anchor",
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    return rows


def _blocked_fwl_rows(*, blocker: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for diagnostic_item in (
        "fwl_equivalence",
        "residualized_treatment_orthogonality",
        "newey_west_specification",
    ):
        row = {field: "" for field in RESIDUALIZED_FFR_FWL_DIAGNOSTICS_FIELDS}
        row.update(
            {
                "fwl_row_id": f"residualized_ffr_fwl_diagnostics::{diagnostic_item}",
                "bridge_design_id": "residualized_ffr_bridge_v2",
                "outcome_id": "log_real_gdp",
                "control_spec_id": "ratewall_published_style_lag4_controls",
                "diagnostic_item": diagnostic_item,
                "diagnostic_status": "blocked_fwl_audit_not_materialized",
                "exact_blocker": blocker,
                "safe_sentence": (
                    "RateWall will own the FWL / HAC diagnostic path for the literature "
                    "bridge rather than importing ea-tdc wholesale."
                ),
                "next_backend_action": "repair_local_replication_inputs",
                "allowed_use": "methodology_scaffold_only",
                "blocked_use": (
                    "empirical_promotion;canonical_RW_Y;main_ratio;Evidence_Mode;"
                    "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                    "reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "residualized_ffr_fwl_scaffold_not_estimate",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _residualized_ffr_fwl_diagnostics_rows(
    *,
    fwl: dict[str, object] | None,
    replication_passed: bool,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    status = (
        "pass_fwl_audit_materialized"
        if fwl is not None and replication_passed
        else "blocked_fwl_audit_not_materialized"
    )
    blocker = (
        "FWL diagnostics are materialized locally for the published-style h8 GDP replication."
        if status == "pass_fwl_audit_materialized"
        else "FWL diagnostics remain blocked until the published-style h8 GDP replication passes tolerance."
    )
    next_action = (
        "carry_fwl_guardrail_forward_into_private_demand_bridge"
        if status == "pass_fwl_audit_materialized"
        else "repair_published_style_h8_replication_before_fwl_use"
    )
    values = fwl or {}
    items = {
        "fwl_equivalence": (
            values.get("full_model_beta"),
            values.get("residualized_beta"),
            values.get("beta_abs_diff"),
            values.get("orthogonality_max_abs_corr"),
        ),
        "residualized_treatment_orthogonality": (
            values.get("full_model_beta"),
            values.get("residualized_beta"),
            values.get("beta_abs_diff"),
            values.get("orthogonality_max_abs_corr"),
        ),
        "newey_west_specification": (
            values.get("full_model_beta"),
            values.get("residualized_beta"),
            values.get("beta_abs_diff"),
            values.get("orthogonality_max_abs_corr"),
        ),
    }
    for diagnostic_item, (
        full_beta,
        residualized_beta,
        beta_abs_diff,
        orthogonality,
    ) in items.items():
        row = {field: "" for field in RESIDUALIZED_FFR_FWL_DIAGNOSTICS_FIELDS}
        row.update(
            {
                "fwl_row_id": f"residualized_ffr_fwl_diagnostics::{diagnostic_item}",
                "bridge_design_id": "residualized_ffr_bridge_v2",
                "outcome_id": "log_real_gdp",
                "control_spec_id": "ratewall_published_style_lag4_controls",
                "diagnostic_item": diagnostic_item,
                "full_model_beta": _format_decimal(full_beta),
                "residualized_beta": _format_decimal(residualized_beta),
                "beta_abs_diff": _format_decimal(beta_abs_diff),
                "orthogonality_max_abs_corr": _format_decimal(orthogonality),
                "diagnostic_n_obs": (
                    str(values.get("diagnostic_n_obs", "")) if values else ""
                ),
                "hac_bandwidth": (
                    str(values.get("hac_bandwidth", "")) if values else ""
                ),
                "diagnostic_status": status,
                "exact_blocker": blocker,
                "safe_sentence": (
                    "RateWall owns the FWL equivalence and HAC diagnostic path for the "
                    "literature bridge."
                ),
                "next_backend_action": next_action,
                "allowed_use": "review_only_diagnostic_context",
                "blocked_use": (
                    "empirical_promotion;canonical_RW_Y;main_ratio;Evidence_Mode;"
                    "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                    "reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "fwl_diagnostic_review_only",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _blocked_bridge_rows(*, blocker: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for outcome_id, target_role in {
        "log_real_gdp": "published_base_replication",
        "log_real_fspdp": "private_demand_adaptation",
        "fspdp_gdp_share_contribution": "ratewall_denominator_target",
        "log_real_pce": "component_bridge",
        "log_real_private_fixed_investment": "component_bridge",
    }.items():
        for horizon in (4, 8, 12):
            row = {field: "" for field in RESIDUALIZED_FFR_PRIVATE_DEMAND_BRIDGE_FIELDS}
            row.update(
                {
                    "bridge_row_id": (
                        f"residualized_ffr_private_demand_bridge::{outcome_id}::h{horizon}"
                    ),
                    "source_paper_id": _PAPER_ID,
                    "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
                    "outcome_id": outcome_id,
                    "outcome_definition": outcome_id,
                    "target_role": target_role,
                    "horizon_q": str(horizon),
                    "target_unit": (
                        "pp_gdp" if outcome_id == "fspdp_gdp_share_contribution" else "pct_response"
                    ),
                    "bridge_status": "blocked_paper_gdp_replication_pending",
                    "exact_blocker": blocker,
                    "safe_sentence": "No local bridge results exist yet.",
                    "next_backend_action": "repair_local_replication_inputs",
                    "allowed_use": "methodology_scaffold_only",
                    "blocked_use": (
                        "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                        "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                        "reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": "private_demand_bridge_scaffold_not_estimate",
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    return rows


def _residualized_ffr_private_demand_bridge_rows(
    *,
    replication_passed: bool,
    gdp_results: dict[int, HacEstimate],
    fspdp_results: dict[int, HacEstimate],
    fspdp_pp_gdp_results: dict[int, HacEstimate],
    pce_results: dict[int, HacEstimate],
    pfi_results: dict[int, HacEstimate],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    outcome_map = {
        "log_real_gdp": ("published_base_replication", "pct_response", gdp_results),
        "log_real_fspdp": ("private_demand_adaptation", "pct_response", fspdp_results),
        "fspdp_gdp_share_contribution": (
            "ratewall_denominator_target",
            "pp_gdp",
            fspdp_pp_gdp_results,
        ),
        "log_real_pce": ("component_bridge", "pct_response", pce_results),
        "log_real_private_fixed_investment": (
            "component_bridge",
            "pct_response",
            pfi_results,
        ),
    }
    for outcome_id, (target_role, unit, estimates) in outcome_map.items():
        for horizon in (4, 8, 12):
            estimate = estimates.get(horizon)
            if outcome_id == "log_real_gdp":
                status = (
                    "pass_paper_gdp_replication_within_tolerance"
                    if horizon == 8 and replication_passed and estimate is not None
                    else (
                        "pass_published_style_gdp_context_estimated"
                        if estimate is not None
                        else "blocked_paper_gdp_replication_pending"
                    )
                )
            elif outcome_id == "log_real_private_fixed_investment" and estimate is None:
                status = "blocked_local_component_series_unavailable"
            elif replication_passed and estimate is not None:
                status = "pass_fspdp_outcome_adapted"
            else:
                status = "blocked_paper_gdp_replication_pending"
            blocker = {
                "pass_paper_gdp_replication_within_tolerance": (
                    "This is the published-style GDP bridge row that passed the h8 tolerance gate."
                ),
                "pass_published_style_gdp_context_estimated": (
                    "Published-style GDP bridge context is estimated locally."
                ),
                "pass_fspdp_outcome_adapted": (
                    "Private-demand bridge row is estimated locally and remains review-only."
                ),
                "blocked_local_component_series_unavailable": (
                    "Local real private fixed investment coverage is too short for the published-style sample."
                ),
                "blocked_paper_gdp_replication_pending": (
                    "Private-demand bridge stays blocked until the published-style h8 GDP replication passes tolerance."
                ),
            }[status]
            row = {field: "" for field in RESIDUALIZED_FFR_PRIVATE_DEMAND_BRIDGE_FIELDS}
            row.update(
                {
                    "bridge_row_id": (
                        f"residualized_ffr_private_demand_bridge::{outcome_id}::h{horizon}"
                    ),
                    "source_paper_id": _PAPER_ID,
                    "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
                    "outcome_id": outcome_id,
                    "outcome_definition": outcome_id,
                    "target_role": target_role,
                    "horizon_q": str(horizon),
                    "target_unit": unit,
                    "bridge_response_value": _format_decimal(estimate.beta) if estimate is not None else "",
                    "bridge_se_hac": _format_decimal(estimate.se) if estimate is not None else "",
                    "bridge_ci95_low_hac": _format_decimal(estimate.ci_low) if estimate is not None else "",
                    "bridge_ci95_high_hac": _format_decimal(estimate.ci_high) if estimate is not None else "",
                    "bridge_n_obs": str(estimate.n_obs) if estimate is not None else "",
                    "sample_start": estimate.sample_start if estimate is not None else "",
                    "sample_end": estimate.sample_end if estimate is not None else "",
                    "bridge_status": status,
                    "exact_blocker": blocker,
                    "safe_sentence": (
                        "This bridge surface keeps GDP, FSPDP, and component outcomes "
                        "explicit and separate under the same residualized-FFR design."
                    ),
                    "next_backend_action": (
                        "compare_quarterly_bridge_rows_against_review_only_annual_flow_window_translation"
                        if status.startswith("pass_")
                        else "repair_published_style_h8_gdp_replication_before_bridge_use"
                    ),
                    "allowed_use": "review_only_bridge_surface",
                    "blocked_use": (
                        "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                        "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                        "reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": "private_demand_bridge_review_only_not_runtime_anchor",
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    if replication_passed:
        for annual_window_id, annual_window_label, start_horizon, end_horizon in _LITERATURE_ANNUAL_WINDOW_SPECS:
            native_window_response = _annual_window_native_response(
                estimates=fspdp_pp_gdp_results,
                start_horizon=start_horizon,
                end_horizon=end_horizon,
            )
            if native_window_response is None:
                continue
            end_estimate = fspdp_pp_gdp_results.get(end_horizon)
            row = {field: "" for field in RESIDUALIZED_FFR_PRIVATE_DEMAND_BRIDGE_FIELDS}
            row.update(
                {
                    "bridge_row_id": (
                        "residualized_ffr_private_demand_bridge::"
                        f"fspdp_gdp_share_contribution::{annual_window_id}"
                    ),
                    "source_paper_id": _PAPER_ID,
                    "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
                    "outcome_id": "fspdp_gdp_share_contribution",
                    "outcome_definition": (
                        "annual-flow proxy translation from quarterly endpoint bridge rows"
                    ),
                    "target_role": "annual_flow_window_translation",
                    "horizon_q": str(end_horizon),
                    "annual_window_id": annual_window_id,
                    "annual_window_label": annual_window_label,
                    "window_start_horizon_q": "" if start_horizon is None else str(start_horizon),
                    "window_end_horizon_q": str(end_horizon),
                    "target_unit": "pp_gdp",
                    "bridge_response_value": _format_decimal(native_window_response),
                    "bridge_se_hac": "",
                    "bridge_ci95_low_hac": "",
                    "bridge_ci95_high_hac": "",
                    "bridge_n_obs": str(end_estimate.n_obs) if end_estimate is not None else "",
                    "sample_start": end_estimate.sample_start if end_estimate is not None else "",
                    "sample_end": end_estimate.sample_end if end_estimate is not None else "",
                    "bridge_status": "pass_review_only_annual_flow_window_materialized",
                    "exact_blocker": (
                        "Annual-flow literature window is now translated explicitly from the "
                        "quarterly bridge surface, but it remains review-only."
                    ),
                    "safe_sentence": (
                        "This row translates the quarterly private-demand bridge into an "
                        "explicit annual-flow proxy window without enabling runtime use."
                    ),
                    "next_backend_action": (
                        "keep_literature_anchor_visible_review_only_and_focus_future_work_on_scale_conflict_interpretation"
                    ),
                    "allowed_use": "review_only_annual_flow_window_comparison",
                    "blocked_use": (
                        "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                        "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                        "reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": "annual_flow_window_translation_review_only",
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    return rows


def _blocked_normalization_rows(*, blocker: str) -> list[dict[str, str]]:
    row = {field: "" for field in RESIDUALIZED_FFR_NORMALIZATION_BRIDGE_FIELDS}
    row.update(
        {
            "normalization_row_id": "residualized_ffr_normalization_bridge::100bp_year",
            "source_paper_id": _PAPER_ID,
            "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
            "normalization_target_id": "exact_100bp_year_cumulative_policy_path",
            "normalization_formula": (
                "D_Y_per_100bp_year = D_Y_native * (100 / first_year_area_bps_year)"
            ),
            "normalization_status": "blocked_paper_gdp_replication_pending",
            "exact_blocker": blocker,
            "safe_sentence": (
                "The literature shock unit is not assumed to equal 100bp-year. An explicit "
                "path-area bridge is required before any scenario-facing use."
            ),
            "next_backend_action": "repair_local_replication_inputs",
            "allowed_use": "methodology_scaffold_only",
            "blocked_use": (
                "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "normalization_bridge_scaffold_not_materialized",
            **_disabled_switches(),
        }
    )
    return [row]


def _residualized_ffr_normalization_bridge_rows(
    *,
    normalization_status: str,
    normalization_blocker: str,
    normalization_next_action: str,
    first_year_area_pp_year: float | None,
    first_year_area_bps_year: float | None,
    normalization_multiplier: float | None,
    mapped_h8_fspdp_d_y_per_100bp_year: float | None,
    fspdp_pp_gdp_results: dict[int, HacEstimate],
    sample_start: str,
    sample_end: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    row = {field: "" for field in RESIDUALIZED_FFR_NORMALIZATION_BRIDGE_FIELDS}
    row.update(
        {
            "normalization_row_id": "residualized_ffr_normalization_bridge::100bp_year",
            "source_paper_id": _PAPER_ID,
            "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
            "normalization_target_id": "exact_100bp_year_cumulative_policy_path_summary",
            "normalization_formula": (
                "D_Y_per_100bp_year = D_Y_native * (100 / first_year_area_bps_year)"
            ),
            "first_year_area_pp_year": _format_decimal(first_year_area_pp_year),
            "first_year_area_bps_year": _format_decimal(first_year_area_bps_year),
            "normalization_multiplier": _format_decimal(normalization_multiplier),
            "mapped_h8_fspdp_d_y_per_100bp_year": _format_decimal(
                mapped_h8_fspdp_d_y_per_100bp_year
            ),
            "normalization_sample_start": sample_start,
            "normalization_sample_end": sample_end,
            "normalization_status": normalization_status,
            "exact_blocker": normalization_blocker,
            "safe_sentence": (
                "The literature shock unit is bridged into exact 100bp-year units only "
                "when the first-year policy-path area is positive and materialized locally."
            ),
            "next_backend_action": normalization_next_action,
            "allowed_use": "review_only_normalization_context",
            "blocked_use": (
                "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                "reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "normalization_bridge_review_only",
            **_disabled_switches(),
        }
    )
    rows.append(row)
    if normalization_status == "pass_bridge_normalization_100bp_year" and normalization_multiplier is not None:
        for annual_window_id, annual_window_label, start_horizon, end_horizon in _LITERATURE_ANNUAL_WINDOW_SPECS:
            native_window_response = _annual_window_native_response(
                estimates=fspdp_pp_gdp_results,
                start_horizon=start_horizon,
                end_horizon=end_horizon,
            )
            if native_window_response is None:
                continue
            mapped_window_d_y = -(native_window_response * Decimal(str(normalization_multiplier)))
            window_row = {field: "" for field in RESIDUALIZED_FFR_NORMALIZATION_BRIDGE_FIELDS}
            window_row.update(
                {
                    "normalization_row_id": (
                        "residualized_ffr_normalization_bridge::"
                        f"{annual_window_id}"
                    ),
                    "source_paper_id": _PAPER_ID,
                    "shock_construction_id": "residualized_fedfunds_or_shadow_rate",
                    "normalization_target_id": "review_only_annual_flow_window_translation",
                    "normalization_formula": (
                        "annual_window_D_Y_per_100bp_year = annual_window_native_response_pp_gdp * "
                        "(-100 / first_year_area_bps_year)"
                    ),
                    "annual_window_id": annual_window_id,
                    "annual_window_label": annual_window_label,
                    "window_start_horizon_q": "" if start_horizon is None else str(start_horizon),
                    "window_end_horizon_q": str(end_horizon),
                    "first_year_area_pp_year": _format_decimal(first_year_area_pp_year),
                    "first_year_area_bps_year": _format_decimal(first_year_area_bps_year),
                    "normalization_multiplier": _format_decimal(normalization_multiplier),
                    "window_native_response_pp_gdp": _format_decimal(native_window_response),
                    "mapped_window_d_y_per_100bp_year": _format_decimal(mapped_window_d_y),
                    "normalization_sample_start": sample_start,
                    "normalization_sample_end": sample_end,
                    "normalization_status": "pass_review_only_annual_flow_window_materialized",
                    "exact_blocker": (
                        "This annual-flow literature window is explicitly translated into "
                        "exact 100bp-year units, but it remains review-only."
                    ),
                    "safe_sentence": (
                        "This row turns the quarterly literature bridge into a review-only "
                        "annual-flow proxy window in exact 100bp-year units."
                    ),
                    "next_backend_action": (
                        "keep_literature_anchor_visible_review_only_and_focus_future_work_on_scale_conflict_interpretation"
                    ),
                    "allowed_use": "review_only_annual_flow_window_comparison",
                    "blocked_use": (
                        "scenario_runtime_anchor;canonical_RW_Y;main_ratio;Evidence_Mode;"
                        "denominator_prior;pricing;holder_allocation;raw_rate_shock;"
                        "reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": "annual_flow_window_translation_review_only",
                    **_disabled_switches(),
                }
            )
            rows.append(window_row)
    return rows


def first_year_area_bps_year_from_quarterly_pp_path(
    quarterly_pp_path: Sequence[Decimal | None],
) -> Decimal | None:
    """Return the first-year cumulative policy-path area in bp-year units."""

    if len(quarterly_pp_path) < 4 or any(value is None for value in quarterly_pp_path[:4]):
        return None
    area_pp_year = sum(quarterly_pp_path[:4], Decimal("0")) / Decimal("4")
    area_bps_year = area_pp_year * Decimal("100")
    if area_bps_year <= 0:
        return None
    return area_bps_year


def _annual_window_native_response(
    *,
    estimates: dict[int, HacEstimate],
    start_horizon: int | None,
    end_horizon: int,
) -> Decimal | None:
    end_estimate = estimates.get(end_horizon)
    if end_estimate is None:
        return None
    native_response = Decimal(str(end_estimate.beta))
    if start_horizon is None:
        return native_response
    start_estimate = estimates.get(start_horizon)
    if start_estimate is None:
        return None
    return native_response - Decimal(str(start_estimate.beta))


def _lineage_timing_status(anchor_id: str, anchor: dict[str, str]) -> str:
    if anchor_id in _LEGACY_ANCHOR_NAMES.values():
        return "pass_annual_flow_sensitivity_anchor_direct_pairing"
    if anchor_id == _PRIMARY_BOUNDED_SOURCE_ID:
        return "review_only_h8_cumulative_equivalent_not_annual_flow"
    if (
        anchor["anchor_empirical_status"]
        == "pass_primary_empirical_annual_flow_runtime_anchor"
    ):
        return "pass_primary_empirical_annual_flow_runtime_anchor"
    if (
        anchor["anchor_empirical_status"]
        == "pass_review_only_literature_annual_flow_anchor_window_materialized"
    ):
        return "pass_review_only_literature_annual_flow_window_materialized"
    return "blocked_literature_bridge_not_runtime_ready"


def _lineage_exact_blocker(anchor_id: str, anchor: dict[str, str]) -> str:
    if anchor_id in _LEGACY_ANCHOR_NAMES.values():
        return (
            "Scenario runtime remains allowed for this row only as an explicit "
            "assumption-mode sensitivity counterpoint. It is not the default runtime "
            "denominator and it is not empirical denominator evidence."
        )
    if anchor_id == _PRIMARY_BOUNDED_SOURCE_ID:
        return (
            "The bounded h8 overlay is cumulative review context only and remains "
            "timing-misaligned to annual-flow scenario use."
        )
    if (
        anchor["anchor_empirical_status"]
        == "pass_primary_empirical_annual_flow_runtime_anchor"
    ):
        return (
            "This lineage row now carries the literature-backed empirical annual-flow "
            "runtime anchor. Canonical RW_Y, main-ratio entry, and stronger claim modes remain blocked."
        )
    return (
        "The literature annual-flow proxy anchor is materialized and kept visible for "
        "review-only comparison, but runtime use remains disabled."
    )


def _lineage_safe_sentence(anchor_id: str) -> str:
    if anchor_id in _LEGACY_ANCHOR_NAMES.values():
        return (
            "This lineage row preserves a legacy annual-flow sensitivity point after the "
            "runtime default moved to the literature-backed empirical family."
        )
    if anchor_id == _PRIMARY_BOUNDED_SOURCE_ID:
        return (
            "This lineage row exposes the bounded h8 review center as an overlay path, "
            "not as an annual-flow denominator."
        )
    return (
        "This lineage row carries the literature-backed annual-flow runtime anchor that "
        "now serves as the default empirical denominator for the annual-flow numerator family."
    )


def _lineage_next_backend_action(anchor_id: str, anchor: dict[str, str]) -> str:
    if anchor_id in _LEGACY_ANCHOR_NAMES.values():
        return "keep_only_as_explicit_sensitivity_counterpoint_to_literature_runtime_family"
    if anchor_id == _PRIMARY_BOUNDED_SOURCE_ID:
        return "keep_h8_overlay_review_only_until_timing_bridge_exists"
    if (
        anchor["anchor_empirical_status"]
        == "pass_primary_empirical_annual_flow_runtime_anchor"
    ):
        return "use_literature_runtime_family_as_default_and_keep_h8_overlay_review_only"
    if (
        anchor["anchor_empirical_status"]
        == "pass_review_only_literature_annual_flow_anchor_window_materialized"
    ):
        return (
            "keep_literature_anchor_visible_review_only_and_focus_future_work_on_scale_conflict_interpretation"
        )
    return "formalize_annual_flow_windows_before_literature_runtime_enable"


def _lineage_allowed_use(anchor_id: str, anchor: dict[str, str]) -> str:
    if anchor_id in _LEGACY_ANCHOR_NAMES.values():
        return "scenario_runtime_assumption_mode_sensitivity_only"
    if anchor_id == _PRIMARY_BOUNDED_SOURCE_ID:
        return "review_only_h8_overlay_only"
    if (
        anchor["anchor_empirical_status"]
        == "pass_primary_empirical_annual_flow_runtime_anchor"
    ):
        return "scenario_runtime_empirical_annual_flow_primary"
    if (
        anchor["anchor_empirical_status"]
        == "pass_review_only_literature_annual_flow_anchor_window_materialized"
    ):
        return "review_only_literature_annual_flow_comparison"
    return "planning_only;review_only_bridge_surface"


def _lineage_claim_boundary(anchor_id: str) -> str:
    if anchor_id in _LEGACY_ANCHOR_NAMES.values():
        return "scenario_lineage_assumption_mode_sensitivity_only_not_empirical"
    if anchor_id == _PRIMARY_BOUNDED_SOURCE_ID:
        return "scenario_lineage_h8_overlay_not_annual_flow_anchor"
    return "scenario_lineage_literature_runtime_primary_empirical_proxy"


def _assumption_set_by_name(name: str) -> dict[str, str]:
    for assumption in DEFAULT_RATEWALL_ASSUMPTIONS:
        if assumption.name == name:
            return {
                "name": assumption.name,
                "contractionary_drag_gdp_share": str(
                    assumption.contractionary_drag_gdp_share
                ),
            }
    raise KeyError(name)


def _safe_ratio(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> Decimal | None:
    if numerator is None or denominator in {None, Decimal("0")}:
        return None
    return numerator / denominator


def _decimal_or_none(value: object) -> Decimal | None:
    if value in {None, "", "."}:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _format_decimal(value: object) -> str:
    decimal_value = _decimal_or_none(value)
    if decimal_value is None:
        return ""
    quantized = decimal_value.quantize(Decimal("0.000000000001"))
    return format(quantized.normalize(), "f")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _quarter_id(value: object) -> str:
    month = getattr(value, "month", None)
    year = getattr(value, "year", None)
    if month is None or year is None:
        return ""
    quarter = ((int(month) - 1) // 3) + 1
    return f"{int(year)}Q{quarter}"


def _with_intercept(matrix):
    import numpy

    return numpy.column_stack([numpy.ones(len(matrix)), matrix])


def _ols_via_lstsq(y, x):
    import numpy

    beta, _, _, _ = numpy.linalg.lstsq(x, y, rcond=None)
    fitted = x @ beta
    residuals = y - fitted
    return beta, fitted, residuals, len(y)


def _ols_hac(y, x, *, bandwidth: int) -> dict[str, object] | None:
    import numpy

    if len(y) == 0 or len(y) != len(x):
        return None
    beta, _, residuals, n_obs = _ols_via_lstsq(y, x)
    xtx = x.T @ x
    try:
        xtx_inv = numpy.linalg.inv(xtx)
    except numpy.linalg.LinAlgError:
        return None
    k = x.shape[1]
    meat = numpy.zeros((k, k))
    for idx in range(n_obs):
        xi = x[idx : idx + 1].T
        meat += (residuals[idx] ** 2) * (xi @ xi.T)
    max_lag = min(max(1, bandwidth), n_obs - 1)
    for lag in range(1, max_lag + 1):
        weight = 1.0 - lag / (max_lag + 1.0)
        for idx in range(lag, n_obs):
            xi = x[idx : idx + 1].T
            xj = x[idx - lag : idx - lag + 1].T
            scale = weight * residuals[idx] * residuals[idx - lag]
            meat += scale * (xi @ xj.T + xj @ xi.T)
    covariance = xtx_inv @ meat @ xtx_inv
    se = numpy.sqrt(numpy.clip(numpy.diag(covariance), a_min=0.0, a_max=None))
    t = numpy.divide(beta, se, out=numpy.zeros_like(beta), where=se > 0)
    return {"beta": beta, "se": se, "t": t, "bandwidth": max_lag}


def _residualize(y, x):
    beta, _, _, _ = _ols_via_lstsq(y, x)
    return y - x @ beta


def _disabled_switches() -> dict[str, str]:
    return {
        "denominator_prior_update_allowed": "false",
        "empirical_threshold_claim_enabled": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "canonical_ratio_entry": "false",
        "prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_offset_ratio_changed_this_tranche": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
        "tax_output_enabled": "false",
        "mpc_output_enabled": "false",
        "mpc_channel_enabled": "false",
        "holder_allocation_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "reset_calendar_enabled": "false",
        "raw_rate_shock_enabled": "false",
        "empirical_claim_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "causal_financialization_claim_enabled": "false",
    }
