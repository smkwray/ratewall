"""Controlled LP denominator surfaces for the value-bearing FSPDP path."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import math
from pathlib import Path
import sys
import tempfile
from typing import Sequence
import zipfile

from ratewall.sources.base import SourceSnapshot


CONTROL_PANEL_FIELDS = [
    "quarter",
    "real_fspdp",
    "nominal_fspdp",
    "nominal_gdp",
    "fspdp_share_of_gdp_lag1",
    "real_pce",
    "nominal_pce",
    "pce_implicit_price",
    "pce_implicit_inflation_qoq_pct",
    "unrate_quarter_avg",
    "fedfunds_quarter_avg",
    "quarterly_value_bearing_100bp_year_exposure_update_2023",
    "quarterly_value_bearing_100bp_year_exposure_original",
    "exposure_sign_multiplier",
    "tightening_exposure_update_2023",
    "tightening_exposure_original",
    "elb_flag",
    "pandemic_flag",
    "emergency_event_count",
    "primary_sample_flag",
    "control_source_status",
    "no_future_controls_status",
    "exact_blocker",
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

DESIGN_MATRIX_AUDIT_FIELDS = [
    "horizon_q",
    "exposure_vintage",
    "control_spec_id",
    "sample_window_id",
    "outcome_formula",
    "exposure_formula",
    "control_formula",
    "lag_count",
    "n_obs",
    "sample_start_q",
    "sample_end_q",
    "excluded_elb_count",
    "excluded_pandemic_count",
    "excluded_emergency_count",
    "missing_future_outcome_count",
    "missing_control_count",
    "missing_exposure_count",
    "design_matrix_rank",
    "design_matrix_condition_number",
    "design_matrix_status",
    "exact_blocker",
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

ESTIMATE_CANDIDATE_FIELDS = [
    "horizon_q",
    "exposure_vintage",
    "control_spec_id",
    "sample_window_id",
    "n_obs",
    "nw_bandwidth",
    "beta_response_gdp_share_pp_per_100bp_year",
    "se_hac",
    "ci95_low_hac",
    "ci95_high_hac",
    "d_y_candidate",
    "candidate_ci_low_d_y",
    "candidate_ci_high_d_y",
    "bootstrap_ci_low_d_y",
    "bootstrap_ci_high_d_y",
    "bootstrap_status",
    "response_estimate_status",
    "denominator_candidate_status",
    "promotion_rule_status",
    "exact_blocker",
    "next_backend_action",
    "admitted_d_y",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "prior_narrowing_allowed",
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "canonical_ratio_entry",
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
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

INDEPENDENT_REPLICATION_FIELDS = [
    "horizon_q",
    "primary_spec_id",
    "replication_engine",
    "n_obs",
    "nw_bandwidth",
    "beta_response_gdp_share_pp_per_100bp_year",
    "se_hac",
    "ci95_low_hac",
    "ci95_high_hac",
    "max_abs_beta_diff_vs_primary",
    "max_abs_se_diff_vs_primary",
    "replication_status",
    "exact_blocker",
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

ROBUSTNESS_FIELDS = [
    "horizon_q",
    "robustness_case",
    "exposure_vintage",
    "lag_count",
    "sample_window_id",
    "n_obs",
    "nw_bandwidth",
    "beta_response_gdp_share_pp_per_100bp_year",
    "d_y",
    "se_hac",
    "ci95_low_hac",
    "ci95_high_hac",
    "bootstrap_ci_low_d_y",
    "bootstrap_ci_high_d_y",
    "bootstrap_sign_probability_d_y_positive",
    "leave_one_out_median_d_y",
    "leave_one_out_positive_share",
    "max_influence_quarter",
    "max_abs_loo_shift",
    "robustness_status",
    "exact_blocker",
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

STATUS_COMPACT_FIELDS = [
    "horizon_q",
    "primary_denominator_horizon",
    "estimator_id",
    "outcome_transform",
    "exposure_series_id",
    "sample_window_id",
    "control_spec_id",
    "n_obs",
    "beta_response_gdp_share_pp",
    "review_center_d_y",
    "admitted_d_y",
    "bounded_ci_low_d_y",
    "bounded_ci_high_d_y",
    "bounded_primary_object_type",
    "bounded_primary_artifact",
    "ci95_low_d_y",
    "ci95_high_d_y",
    "bootstrap_ci_low_d_y",
    "bootstrap_ci_high_d_y",
    "bootstrap_sign_probability_d_y_positive",
    "replication_status",
    "robustness_status",
    "promotion_rule_status",
    "denominator_candidate_status",
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

CURRENT_DEMAND_RATIO_GATE_FIELDS = [
    "ratio_gate_row_id",
    "ratio_id",
    "ratio_layer_registry_row_id",
    "denominator_status_artifact",
    "bounded_denominator_artifact",
    "denominator_horizon_q",
    "primary_denominator_horizon",
    "denominator_estimator_id",
    "sample_window_id",
    "control_spec_id",
    "n_obs",
    "review_center_d_y",
    "admitted_d_y",
    "bounded_ci_low_d_y",
    "bounded_ci_high_d_y",
    "bounded_primary_object_type",
    "ci95_low_d_y",
    "ci95_high_d_y",
    "bootstrap_ci_low_d_y",
    "bootstrap_ci_high_d_y",
    "bootstrap_sign_probability_d_y_positive",
    "replication_status",
    "robustness_status",
    "promotion_rule_status",
    "denominator_candidate_status",
    "numerator_source_timing_contract_artifact",
    "numerator_source_timing_contract_row_id",
    "numerator_source_timing_contract_status",
    "downstream_current_demand_input_enabled",
    "denominator_input_status",
    "ratio_gate_status",
    "numerator_runtime_status",
    "historical_reporting_status",
    "main_ratio_status",
    "evidence_mode_status",
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

NONCANONICAL_CURRENT_DEMAND_SUPPORT_RATIO_CONSUMER_FIELDS = [
    "consumer_row_id",
    "ratio_id",
    "ratio_layer_registry_row_id",
    "numerator_source_artifact",
    "denominator_status_artifact",
    "bounded_denominator_artifact",
    "denominator_horizon_q",
    "forecast_year",
    "mpc_scenario",
    "maturity_scenario",
    "holder_scenario",
    "nominal_gdp_bil",
    "combined_current_demand_support_bil",
    "support_pct_of_gdp",
    "denominator_source_id",
    "denominator_source_class",
    "denominator_timing_class",
    "denominator_anchor_empirical_status",
    "denominator_scenario_runtime_allowed",
    "review_center_d_y",
    "admitted_d_y",
    "bounded_ci_low_d_y",
    "bounded_ci_high_d_y",
    "bounded_primary_object_type",
    "support_offset_100bp_year_equivalent_lower_bound",
    "support_offset_100bp_year_equivalent",
    "support_offset_100bp_year_equivalent_upper_bound",
    "support_offset_bp_year_equivalent_lower_bound",
    "support_offset_bp_year_equivalent",
    "support_offset_bp_year_equivalent_upper_bound",
    "legacy_holder_tdc_consistent_wall_ratio",
    "conventional_drag_bil",
    "gap_to_wall_holder_tdc_consistent_bil",
    "numerator_source_status",
    "double_count_prevention_rule",
    "numerator_source_timing_contract_artifact",
    "numerator_source_timing_contract_row_id",
    "numerator_source_timing_contract_status",
    "timing_alignment_status",
    "denominator_input_status",
    "consumer_status",
    "historical_reporting_status",
    "main_ratio_status",
    "evidence_mode_status",
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

IDENTIFICATION_VARIANT_QUARTERLY_FIELDS = [
    "quarter",
    "instrument_variant",
    "shock_source_id",
    "instrument_series_id",
    "instrument_class",
    "source_artifact_path",
    "source_artifact_entry",
    "source_artifact_sha256",
    "instrument_unit",
    "quarterly_instrument_value",
    "event_count",
    "matched_exposure_vintage",
    "matched_tightening_exposure_update_2023",
    "emergency_event_count",
    "elb_flag",
    "pandemic_flag",
    "first_event_date",
    "last_event_date",
    "identification_series_status",
    "exact_blocker",
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

IDENTIFICATION_CHECK_FIELDS = [
    "horizon_q",
    "instrument_variant",
    "shock_source_id",
    "instrument_series_id",
    "instrument_class",
    "sample_window_id",
    "control_spec_id",
    "n_obs",
    "sample_start_q",
    "sample_end_q",
    "instrument_missing_quarter_count",
    "nw_bandwidth",
    "first_stage_coef_exposure_per_instrument_unit",
    "first_stage_se_hac",
    "first_stage_ci95_low_hac",
    "first_stage_ci95_high_hac",
    "first_stage_t_hac",
    "first_stage_f_hac",
    "reduced_form_coef_outcome_per_instrument_unit",
    "reduced_form_se_hac",
    "reduced_form_ci95_low_hac",
    "reduced_form_ci95_high_hac",
    "iv_beta_response_gdp_share_pp_per_100bp_year",
    "iv_se_hac",
    "iv_ci95_low_hac",
    "iv_ci95_high_hac",
    "iv_d_y_candidate",
    "iv_candidate_ci_low_d_y",
    "iv_candidate_ci_high_d_y",
    "identification_check_status",
    "exact_blocker",
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

FRBUS_BENCHMARK_CROSSCHECK_FIELDS = [
    "horizon_q",
    "benchmark_outcome_id",
    "benchmark_outcome_variable",
    "benchmark_outcome_label",
    "frbus_scenario_handle",
    "frbus_shock_definition",
    "frbus_baseline_level",
    "frbus_shock_level",
    "frbus_delta_level",
    "frbus_pct_delta_from_baseline",
    "frbus_output_unit",
    "empirical_instrument_variant",
    "empirical_iv_d_y_candidate",
    "empirical_iv_ci_low_d_y",
    "empirical_iv_ci_high_d_y",
    "benchmark_crosscheck_status",
    "exact_blocker",
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

BOUNDED_DENOMINATOR_REGISTRY_FIELDS = [
    "bounded_denominator_row_id",
    "route_id",
    "ratio_id",
    "horizon_q",
    "primary_denominator_horizon",
    "bounded_primary_object_type",
    "bounded_primary_estimator_id",
    "review_center_estimator_id",
    "review_center_d_y",
    "bounded_ci_low_d_y",
    "bounded_ci_high_d_y",
    "companion_controlled_ci_low_d_y",
    "companion_controlled_ci_high_d_y",
    "proxy_iv_ci_low_d_y",
    "proxy_iv_ci_high_d_y",
    "sample_window_id",
    "control_spec_id",
    "bounded_primary_sample_start_q",
    "bounded_primary_sample_end_q",
    "bounded_primary_n_obs",
    "weak_iv_safe_method",
    "weak_iv_safe_inference_status",
    "promotion_rule_status",
    "bounded_denominator_status",
    "current_demand_overlay_input_enabled",
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

FRBUS_100BP_YEAR_FSPDP_PROXY_BENCHMARK_FIELDS = [
    "model_package_sha256",
    "data_package_sha256",
    "scenario_id",
    "path_normalization_id",
    "component_mapping_id",
    "component_mapping_label",
    "horizon_q",
    "component_id",
    "component_label",
    "model_variable",
    "component_role",
    "shock_path_quarters",
    "shock_path_pp",
    "exposure_bps_year",
    "baseline_level",
    "shock_level",
    "delta_level",
    "log_response_pct",
    "baseline_share_of_xgdp",
    "component_contribution_pp_gdp",
    "aggregate_proxy_contribution_pp_gdp",
    "model_d_y_per_100bp_year",
    "empirical_weak_iv_safe_ci_low_d_y",
    "empirical_weak_iv_safe_ci_high_d_y",
    "benchmark_support_status",
    "exact_blocker",
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

WEAK_IV_SAFE_INFERENCE_FIELDS = [
    "horizon_q",
    "primary_denominator_horizon",
    "instrument_variant",
    "shock_source_id",
    "instrument_series_id",
    "sample_window_id",
    "control_spec_id",
    "weak_iv_safe_method",
    "n_obs",
    "sample_start_q",
    "sample_end_q",
    "nw_bandwidth",
    "beta_grid_min",
    "beta_grid_max",
    "beta_grid_step",
    "accepted_grid_point_count",
    "acceptance_region_span_count",
    "ar_coef_z_at_beta_zero",
    "ar_se_hac_at_beta_zero",
    "ar_t_hac_at_beta_zero",
    "reject_beta_zero_hac",
    "weak_iv_safe_ci_low_beta",
    "weak_iv_safe_ci_high_beta",
    "weak_iv_safe_ci_low_d_y",
    "weak_iv_safe_ci_high_d_y",
    "weak_iv_safe_inference_status",
    "exact_blocker",
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

PROMOTION_RULE_EVALUATION_FIELDS = [
    "horizon_q",
    "primary_denominator_horizon",
    "promotion_rule_version",
    "estimator_id",
    "primary_controlled_gate_status",
    "bootstrap_review_gate_status",
    "replication_gate_status",
    "robustness_gate_status",
    "proxy_iv_gate_status",
    "orthogonalized_secondary_gate_status",
    "frbus_directional_benchmark_gate_status",
    "frbus_100bp_year_component_benchmark_gate_status",
    "weak_iv_safe_inference_gate_status",
    "promotion_rule_status",
    "denominator_candidate_status",
    "admitted_d_y",
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

PRIMARY_START = "1990Q1"
PRIMARY_END = "2023Q4"
CONTROL_SPEC_ID = "controlled_4lag_macro_exposure"
SAMPLE_WINDOW_ID = "exclude_elb_pandemic_emergency"
EXPOSURE_VINTAGE = "update_2023"
LAG_COUNT = 4
PRIMARY_HORIZONS = (0, 4, 8, 12)
STATUS_HORIZONS = (4, 8, 12)
PRIMARY_SPEC_ID = "controlled_lp_update_2023_4lag_exclude_elb_pandemic_emergency"
BOOTSTRAP_DRAWS = 999
BOOTSTRAP_SEED = 20260526
REPLICATION_TOLERANCE = 1e-8
MIN_PRIMARY_NOBS = 70
MIN_PRE_2008_ROBUSTNESS_NOBS = 40
MIN_IV_SAMPLE_NOBS = 20
FIRST_STAGE_F_THRESHOLD = 10.0
BOOTSTRAP_REVIEW_SIGN_PROB_THRESHOLD = 0.80
WEAK_IV_SAFE_GRID_STEP = 0.05
WEAK_IV_SAFE_MIN_SPREAD = 20.0
WEAK_IV_SAFE_MAX_GRID_EXPANSIONS = 4
WEAK_IV_SAFE_Z_CRITICAL_VALUE = 1.96
PROMOTION_RULE_VERSION = "h8_proxy_iv_frbus_100bp_year_component_benchmark_ar_v3"

SF_FED_PUBLIC_SURPRISE_CHART_PATH = Path(
    "data/raw/policy_path_protocol_sources/sf_fed_monetary_policy_surprises_chart.csv"
)
SF_FED_MPS_ZIP_PATH = Path(
    "data/raw/policy_path_source_author_web_acquisition_attempts/sf_fed_monetary_policy_surprises.zip"
)
FRBUS_PYFRBUS_ZIP_PATH = Path(
    "data/raw/conventional_drag_parameterization_sources/pyfrbus.zip"
)
FRBUS_DATA_ONLY_PACKAGE_ZIP_PATH = Path(
    "data/raw/conventional_drag_parameterization_sources/data_only_package.zip"
)

EXACT_BLOCKER_CANDIDATE_REVIEW = (
    "Controlled LP candidate estimated; see replication, robustness, and compact "
    "status artifacts for admission state."
)
EXACT_BLOCKER_MISSING_CONTROLS = (
    "Required official unemployment or policy-rate controls are unavailable; "
    "do not fall back to bivariate."
)
EXACT_BLOCKER_NOT_PROMOTED = (
    "Controlled LP h8 now has explicit proxy/orthogonalized identification review, "
    "but admission remains blocked until a predeclared LP-IV promotion rule, "
    "weak-IV-safe inference standard, and benchmark cross-check are implemented."
)
EXACT_BLOCKER_WEAK_IV_SAFE_PENDING = (
    "Controlled LP h8 now has proxy/orthogonalized identification review and a "
    "directional FRB/US benchmark cross-check, but admission remains blocked "
    "pending weak-IV-safe inference."
)


@dataclass(frozen=True)
class QuarterPanelRecord:
    quarter: str
    real_fspdp: Decimal | None
    nominal_fspdp: Decimal | None
    nominal_gdp: Decimal | None
    real_pce: Decimal | None
    nominal_pce: Decimal | None
    fspdp_share_of_gdp_lag1: Decimal | None
    pce_implicit_price: Decimal | None
    pce_implicit_inflation_qoq_pct: float | None
    unrate_quarter_avg: float | None
    fedfunds_quarter_avg: float | None
    quarterly_value_bearing_100bp_year_exposure_update_2023: float | None
    quarterly_value_bearing_100bp_year_exposure_original: float | None
    exposure_sign_multiplier: int
    tightening_exposure_update_2023: float | None
    tightening_exposure_original: float | None
    elb_flag: bool
    pandemic_flag: bool
    emergency_event_count: int
    primary_sample_flag: bool
    control_source_status: str
    no_future_controls_status: str
    fspdp_growth_qoq_pct: float | None


@dataclass(frozen=True)
class ControlledLpArtifacts:
    control_panel_rows: list[dict[str, str]]
    design_matrix_audit_rows: list[dict[str, str]]
    estimate_candidate_rows: list[dict[str, str]]
    independent_replication_rows: list[dict[str, str]]
    robustness_rows: list[dict[str, str]]
    identification_variant_quarterly_rows: list[dict[str, str]]
    identification_check_rows: list[dict[str, str]]
    frbus_benchmark_crosscheck_rows: list[dict[str, str]]
    bounded_denominator_registry_rows: list[dict[str, str]]
    frbus_100bp_year_fspdp_proxy_benchmark_rows: list[dict[str, str]]
    weak_iv_safe_inference_rows: list[dict[str, str]]
    promotion_rule_evaluation_rows: list[dict[str, str]]
    denominator_status_compact_rows: list[dict[str, str]]
    noncanonical_current_demand_support_ratio_consumer_rows: list[dict[str, str]]
    current_demand_ratio_gate_rows: list[dict[str, str]]


@dataclass(frozen=True)
class DesignMatrixResult:
    n_obs: int
    sample_start_q: str
    sample_end_q: str
    excluded_elb_count: int
    excluded_pandemic_count: int
    excluded_emergency_count: int
    missing_future_outcome_count: int
    missing_control_count: int
    missing_exposure_count: int
    design_matrix_rank: int | None
    design_matrix_condition_number: float | None
    design_matrix_status: str
    exact_blocker: str
    quarters: list[str]
    y: list[float]
    x_rows: list[list[float]]


@dataclass(frozen=True)
class ControlledLpSpec:
    case_id: str
    exposure_vintage: str
    lag_count: int
    include_emergency: bool
    sample_end_q: str
    sample_window_id: str
    control_spec_id: str


@dataclass(frozen=True)
class HacEstimate:
    beta: float
    se: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class BootstrapResult:
    ci_low_d_y: float | None
    ci_high_d_y: float | None
    sign_probability: float | None
    successful_draws: int
    status: str


@dataclass(frozen=True)
class ReplicationSummary:
    max_abs_beta_diff: float | None
    max_abs_se_diff: float | None
    replication_status: str
    exact_blocker: str


@dataclass(frozen=True)
class RobustnessOutcome:
    spec: ControlledLpSpec
    design_result: DesignMatrixResult
    estimate: HacEstimate | None
    bootstrap: BootstrapResult | None
    robustness_status: str
    exact_blocker: str
    next_backend_action: str
    leave_one_out_median_d_y: float | None = None
    leave_one_out_positive_share: float | None = None
    max_influence_quarter: str = ""
    max_abs_loo_shift: float | None = None


@dataclass(frozen=True)
class InstrumentQuarterRecord:
    quarter: str
    instrument_variant: str
    shock_source_id: str
    instrument_series_id: str
    instrument_class: str
    source_artifact_path: str
    source_artifact_entry: str
    source_artifact_sha256: str
    instrument_unit: str
    quarterly_instrument_value: float
    event_count: int
    first_event_date: str
    last_event_date: str
    matched_tightening_exposure_update_2023: float | None
    emergency_event_count: int
    elb_flag: bool
    pandemic_flag: bool


@dataclass(frozen=True)
class InstrumentVariantSpec:
    variant_id: str
    shock_source_id: str
    instrument_series_id: str
    instrument_class: str
    source_artifact_path: Path
    source_artifact_entry: str
    instrument_unit: str


@dataclass(frozen=True)
class IdentificationCheckOutcome:
    horizon_q: int
    instrument_variant: str
    shock_source_id: str
    instrument_series_id: str
    instrument_class: str
    n_obs: int
    sample_start_q: str
    sample_end_q: str
    instrument_missing_quarter_count: int
    bandwidth: int
    first_stage: HacEstimate | None
    reduced_form: HacEstimate | None
    iv_estimate: HacEstimate | None
    identification_check_status: str
    exact_blocker: str
    next_backend_action: str


@dataclass(frozen=True)
class FrbusBenchmarkCrosscheckOutcome:
    horizon_q: int
    benchmark_outcome_id: str
    benchmark_outcome_variable: str
    benchmark_outcome_label: str
    baseline_level: float | None
    shock_level: float | None
    delta_level: float | None
    pct_delta_from_baseline: float | None
    empirical_instrument_variant: str
    empirical_iv_d_y_candidate: float | None
    empirical_iv_ci_low_d_y: float | None
    empirical_iv_ci_high_d_y: float | None
    benchmark_crosscheck_status: str
    exact_blocker: str
    next_backend_action: str


@dataclass(frozen=True)
class Frbus100BpYearBenchmarkOutcome:
    horizon_q: int
    component_mapping_id: str
    component_mapping_label: str
    component_id: str
    component_label: str
    model_variable: str
    component_role: str
    model_package_sha256: str
    data_package_sha256: str
    scenario_id: str
    path_normalization_id: str
    shock_path_quarters: int
    shock_path_pp: float
    exposure_bps_year: float | None
    baseline_level: float | None
    shock_level: float | None
    delta_level: float | None
    log_response_pct: float | None
    baseline_share_of_xgdp: float | None
    component_contribution_pp_gdp: float | None
    aggregate_proxy_contribution_pp_gdp: float | None
    model_d_y_per_100bp_year: float | None
    empirical_weak_iv_safe_ci_low_d_y: float | None
    empirical_weak_iv_safe_ci_high_d_y: float | None
    benchmark_support_status: str
    exact_blocker: str
    next_backend_action: str


@dataclass(frozen=True)
class WeakIvSafeInferenceOutcome:
    horizon_q: int
    instrument_variant: str
    shock_source_id: str
    instrument_series_id: str
    weak_iv_safe_method: str
    n_obs: int
    sample_start_q: str
    sample_end_q: str
    bandwidth: int
    beta_grid_min: float | None
    beta_grid_max: float | None
    beta_grid_step: float | None
    accepted_grid_point_count: int
    acceptance_region_span_count: int
    ar_coef_z_at_beta_zero: float | None
    ar_se_hac_at_beta_zero: float | None
    ar_t_hac_at_beta_zero: float | None
    reject_beta_zero_hac: bool | None
    weak_iv_safe_ci_low_beta: float | None
    weak_iv_safe_ci_high_beta: float | None
    weak_iv_safe_ci_low_d_y: float | None
    weak_iv_safe_ci_high_d_y: float | None
    weak_iv_safe_inference_status: str
    exact_blocker: str
    next_backend_action: str


@dataclass(frozen=True)
class PromotionRuleEvaluationOutcome:
    horizon_q: int
    primary_controlled_gate_status: str
    bootstrap_review_gate_status: str
    replication_gate_status: str
    robustness_gate_status: str
    proxy_iv_gate_status: str
    orthogonalized_secondary_gate_status: str
    frbus_directional_benchmark_gate_status: str
    frbus_100bp_year_component_benchmark_gate_status: str
    weak_iv_safe_inference_gate_status: str
    promotion_rule_status: str
    denominator_candidate_status: str
    exact_blocker: str
    safe_sentence: str
    next_backend_action: str


@dataclass(frozen=True)
class BoundedDenominatorOutcome:
    horizon_q: int
    primary_denominator_horizon: bool
    bounded_primary_object_type: str
    bounded_primary_estimator_id: str
    review_center_estimator_id: str
    review_center_d_y: float | None
    bounded_ci_low_d_y: float | None
    bounded_ci_high_d_y: float | None
    companion_controlled_ci_low_d_y: float | None
    companion_controlled_ci_high_d_y: float | None
    proxy_iv_ci_low_d_y: float | None
    proxy_iv_ci_high_d_y: float | None
    sample_start_q: str
    sample_end_q: str
    n_obs: int
    weak_iv_safe_method: str
    weak_iv_safe_inference_status: str
    promotion_rule_status: str
    bounded_denominator_status: str
    current_demand_overlay_input_enabled: bool
    exact_blocker: str
    safe_sentence: str
    next_backend_action: str


def build_conventional_drag_fspdp_controlled_lp_artifacts(
    *,
    snapshots: Sequence[SourceSnapshot],
    macro_panel_rows: list[dict[str, str]],
    exposure_quarterly_rows: list[dict[str, str]],
    forecast_holder_tdc_consistency_bridge_rows: list[dict[str, str]],
) -> ControlledLpArtifacts:
    panel_records = _build_panel_records(
        snapshots=snapshots,
        macro_panel_rows=macro_panel_rows,
        exposure_quarterly_rows=exposure_quarterly_rows,
    )
    controls_complete = _controls_complete(panel_records)
    primary_spec = _primary_spec()
    primary_results = {
        horizon: _design_matrix_result(
            panel_records=panel_records,
            macro_panel_rows=macro_panel_rows,
            horizon_q=horizon,
            spec=primary_spec,
            controls_complete=controls_complete,
        )
        for horizon in PRIMARY_HORIZONS
    }
    primary_estimates = {
        horizon: (
            _ols_hac(
                primary_results[horizon].y,
                primary_results[horizon].x_rows,
                bandwidth=max(4, horizon + 1),
            )
            if primary_results[horizon].design_matrix_status
            == "pass_controlled_lp_design_matrix_available"
            else None
        )
        for horizon in PRIMARY_HORIZONS
    }
    independent_replication_rows, replication_summaries = (
        _independent_replication_rows(primary_results, primary_estimates)
    )
    robustness_outcomes = _robustness_outcomes(
        panel_records=panel_records,
        macro_panel_rows=macro_panel_rows,
        controls_complete=controls_complete,
    )
    identification_quarterly_rows, instrument_quarter_records = (
        _identification_variant_quarterly_rows(exposure_quarterly_rows)
    )
    identification_check_rows, identification_outcomes = _identification_check_rows(
        primary_results=primary_results,
        instrument_quarter_records=instrument_quarter_records,
    )
    (
        frbus_benchmark_crosscheck_rows,
        frbus_benchmark_crosscheck_outcomes,
    ) = _frbus_benchmark_crosscheck_rows(
        identification_outcomes=identification_outcomes,
    )
    weak_iv_safe_outcomes = {
        horizon: _weak_iv_safe_inference_rows(
            primary_result=primary_results[horizon],
            identification_outcome=identification_outcomes[horizon].get(
                "sf_fed_usmpd_me_scalar_quarterly_sum"
            ),
            quarter_records=instrument_quarter_records.get(
                "sf_fed_usmpd_me_scalar_quarterly_sum", {}
            ),
            horizon_q=horizon,
        )[1]
        for horizon in (4, 8)
    }
    weak_iv_safe_inference_rows = [
        _weak_iv_safe_inference_row(weak_iv_safe_outcomes[horizon])
        for horizon in (4, 8)
    ]
    weak_iv_safe_outcome = weak_iv_safe_outcomes[8]
    (
        frbus_100bp_year_fspdp_proxy_benchmark_rows,
        frbus_100bp_year_benchmark_outcomes,
    ) = _frbus_100bp_year_fspdp_proxy_benchmark_rows(
        weak_iv_safe_outcome=weak_iv_safe_outcome,
    )
    promotion_rule_evaluation_rows, promotion_rule_outcome = (
        _promotion_rule_evaluation_rows(
            primary_result=primary_results[8],
            primary_estimate=primary_estimates[8],
            primary_robustness=robustness_outcomes[8]["primary_update_2023_4lag"],
            replication_summary=replication_summaries[8],
            robustness_status=_overall_robustness_status(robustness_outcomes[8])[0],
            identification_outcomes=identification_outcomes.get(8, {}),
            frbus_benchmark_crosscheck_outcomes=frbus_benchmark_crosscheck_outcomes,
            frbus_100bp_year_benchmark_outcomes=frbus_100bp_year_benchmark_outcomes,
            weak_iv_safe_outcome=weak_iv_safe_outcome,
        )
    )
    bounded_denominator_registry_rows, bounded_denominator_outcomes = (
        _bounded_denominator_registry_rows(
            primary_results=primary_results,
            primary_estimates=primary_estimates,
            identification_outcomes=identification_outcomes,
            weak_iv_safe_outcome=weak_iv_safe_outcome,
            promotion_rule_outcome=promotion_rule_outcome,
        )
    )
    denominator_status_compact_rows = _compact_status_rows(
        primary_results=primary_results,
        primary_estimates=primary_estimates,
        replication_summaries=replication_summaries,
        robustness_outcomes=robustness_outcomes,
        promotion_rule_outcome=promotion_rule_outcome,
        identification_outcomes=identification_outcomes,
        weak_iv_safe_outcome=weak_iv_safe_outcome,
    )
    noncanonical_current_demand_support_ratio_consumer_rows = (
        _noncanonical_current_demand_support_ratio_consumer_rows(
            forecast_holder_tdc_consistency_bridge_rows=(
                forecast_holder_tdc_consistency_bridge_rows
            ),
            bounded_denominator_registry_rows=bounded_denominator_registry_rows,
        )
    )
    return ControlledLpArtifacts(
        control_panel_rows=_control_panel_rows(panel_records),
        design_matrix_audit_rows=_design_matrix_audit_rows(primary_results),
        estimate_candidate_rows=_estimate_candidate_rows(primary_results, primary_estimates),
        independent_replication_rows=independent_replication_rows,
        robustness_rows=_robustness_rows(robustness_outcomes),
        identification_variant_quarterly_rows=identification_quarterly_rows,
        identification_check_rows=identification_check_rows,
        frbus_benchmark_crosscheck_rows=frbus_benchmark_crosscheck_rows,
        bounded_denominator_registry_rows=bounded_denominator_registry_rows,
        frbus_100bp_year_fspdp_proxy_benchmark_rows=(
            frbus_100bp_year_fspdp_proxy_benchmark_rows
        ),
        weak_iv_safe_inference_rows=weak_iv_safe_inference_rows,
        promotion_rule_evaluation_rows=promotion_rule_evaluation_rows,
        denominator_status_compact_rows=denominator_status_compact_rows,
        noncanonical_current_demand_support_ratio_consumer_rows=(
            noncanonical_current_demand_support_ratio_consumer_rows
        ),
        current_demand_ratio_gate_rows=_current_demand_ratio_gate_rows(
            denominator_status_compact_rows,
            bounded_denominator_registry_rows,
            noncanonical_current_demand_support_ratio_consumer_rows,
        ),
    )


def _primary_spec() -> ControlledLpSpec:
    return ControlledLpSpec(
        case_id="primary_update_2023_4lag",
        exposure_vintage=EXPOSURE_VINTAGE,
        lag_count=LAG_COUNT,
        include_emergency=False,
        sample_end_q=PRIMARY_END,
        sample_window_id=SAMPLE_WINDOW_ID,
        control_spec_id=CONTROL_SPEC_ID,
    )


def _robustness_specs() -> list[ControlledLpSpec]:
    return [
        _primary_spec(),
        ControlledLpSpec(
            case_id="original_vintage_4lag",
            exposure_vintage="original",
            lag_count=4,
            include_emergency=False,
            sample_end_q=PRIMARY_END,
            sample_window_id=SAMPLE_WINDOW_ID,
            control_spec_id="controlled_4lag_macro_exposure",
        ),
        ControlledLpSpec(
            case_id="update_2023_2lag",
            exposure_vintage="update_2023",
            lag_count=2,
            include_emergency=False,
            sample_end_q=PRIMARY_END,
            sample_window_id=SAMPLE_WINDOW_ID,
            control_spec_id="controlled_2lag_macro_exposure",
        ),
        ControlledLpSpec(
            case_id="update_2023_6lag",
            exposure_vintage="update_2023",
            lag_count=6,
            include_emergency=False,
            sample_end_q=PRIMARY_END,
            sample_window_id=SAMPLE_WINDOW_ID,
            control_spec_id="controlled_6lag_macro_exposure",
        ),
        ControlledLpSpec(
            case_id="include_emergency_exclude_elb_pandemic",
            exposure_vintage="update_2023",
            lag_count=4,
            include_emergency=True,
            sample_end_q=PRIMARY_END,
            sample_window_id="exclude_elb_pandemic",
            control_spec_id="controlled_4lag_macro_exposure",
        ),
        ControlledLpSpec(
            case_id="pre_2008_conventional_if_nobs_usable",
            exposure_vintage="update_2023",
            lag_count=4,
            include_emergency=False,
            sample_end_q="2007Q4",
            sample_window_id="exclude_elb_pandemic_emergency_pre_2008",
            control_spec_id="controlled_4lag_macro_exposure",
        ),
    ]


def _build_panel_records(
    *,
    snapshots: Sequence[SourceSnapshot],
    macro_panel_rows: list[dict[str, str]],
    exposure_quarterly_rows: list[dict[str, str]],
) -> list[QuarterPanelRecord]:
    macro_by_quarter = {row["quarter"]: row for row in macro_panel_rows if row.get("quarter")}
    control_values = _quarterly_average_controls(snapshots)
    exposure_values = _exposure_by_vintage(exposure_quarterly_rows)
    quarters = sorted(
        {
            row.get("quarter", "")
            for row in exposure_quarterly_rows
            if row.get("quarter") and row.get("source_sheet_vintage") in {"update_2023", "original"}
        }
    )
    records: list[QuarterPanelRecord] = []
    for quarter in quarters:
        macro_row = macro_by_quarter.get(quarter, {})
        quarter_index = _quarter_index_from_label(quarter)
        lag_quarter = _quarter_label_from_index(quarter_index - 1) if quarter_index is not None else ""
        lag_row = macro_by_quarter.get(lag_quarter, {})

        real_fspdp = _decimal_or_none(macro_row.get("real_fspdp"))
        nominal_fspdp = _decimal_or_none(macro_row.get("nominal_fspdp"))
        nominal_gdp = _decimal_or_none(macro_row.get("nominal_gdp"))
        real_pce = _decimal_or_none(macro_row.get("real_pce"))
        nominal_pce = _decimal_or_none(macro_row.get("nominal_pce"))
        lag_nominal_fspdp = _decimal_or_none(lag_row.get("nominal_fspdp"))
        lag_nominal_gdp = _decimal_or_none(lag_row.get("nominal_gdp"))
        lag_real_fspdp = _decimal_or_none(lag_row.get("real_fspdp"))

        pce_implicit_price = _safe_ratio(nominal_pce, real_pce)
        lag_pce_implicit_price = _safe_ratio(
            _decimal_or_none(lag_row.get("nominal_pce")),
            _decimal_or_none(lag_row.get("real_pce")),
        )
        pce_implicit_inflation_qoq_pct = _log_change_pct(
            pce_implicit_price,
            lag_pce_implicit_price,
        )
        fspdp_growth_qoq_pct = _log_change_pct(real_fspdp, lag_real_fspdp)
        fspdp_share_of_gdp_lag1 = _safe_ratio(lag_nominal_fspdp, lag_nominal_gdp)

        unrate_quarter_avg = control_values.get("UNRATE", {}).get(quarter)
        fedfunds_quarter_avg = control_values.get("FEDFUNDS", {}).get(quarter)
        controls_available = (
            unrate_quarter_avg is not None and fedfunds_quarter_avg is not None
        )
        control_source_status = (
            "pass_official_unrate_and_policy_rate_controls_available"
            if controls_available
            else "blocked_missing_official_unrate_or_policy_rate_controls"
        )

        update_row = exposure_values["update_2023"].get(quarter, {})
        original_row = exposure_values["original"].get(quarter, {})
        update_exposure = _float_or_none(
            update_row.get("quarterly_value_bearing_100bp_year_exposure")
        )
        original_exposure = _float_or_none(
            original_row.get("quarterly_value_bearing_100bp_year_exposure")
        )
        emergency_event_count = max(
            _int_or_zero(update_row.get("emergency_event_count")),
            _int_or_zero(original_row.get("emergency_event_count")),
        )
        elb_flag = (
            update_row.get("elb_flag") == "true"
            or original_row.get("elb_flag") == "true"
        )
        pandemic_flag = (
            update_row.get("pandemic_flag") == "true"
            or original_row.get("pandemic_flag") == "true"
        )
        in_primary_window = PRIMARY_START <= quarter <= PRIMARY_END
        primary_sample_flag = (
            in_primary_window
            and not elb_flag
            and not pandemic_flag
            and emergency_event_count == 0
            and update_exposure is not None
            and controls_available
        )

        records.append(
            QuarterPanelRecord(
                quarter=quarter,
                real_fspdp=real_fspdp,
                nominal_fspdp=nominal_fspdp,
                nominal_gdp=nominal_gdp,
                real_pce=real_pce,
                nominal_pce=nominal_pce,
                fspdp_share_of_gdp_lag1=fspdp_share_of_gdp_lag1,
                pce_implicit_price=pce_implicit_price,
                pce_implicit_inflation_qoq_pct=pce_implicit_inflation_qoq_pct,
                unrate_quarter_avg=unrate_quarter_avg,
                fedfunds_quarter_avg=fedfunds_quarter_avg,
                quarterly_value_bearing_100bp_year_exposure_update_2023=update_exposure,
                quarterly_value_bearing_100bp_year_exposure_original=original_exposure,
                exposure_sign_multiplier=1,
                tightening_exposure_update_2023=update_exposure,
                tightening_exposure_original=original_exposure,
                elb_flag=elb_flag,
                pandemic_flag=pandemic_flag,
                emergency_event_count=emergency_event_count,
                primary_sample_flag=primary_sample_flag,
                control_source_status=control_source_status,
                no_future_controls_status="pass_controls_lagged_only_no_t_or_future_controls",
                fspdp_growth_qoq_pct=fspdp_growth_qoq_pct,
            )
        )
    return records


def _control_panel_rows(records: Sequence[QuarterPanelRecord]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        row = {field: "" for field in CONTROL_PANEL_FIELDS}
        row.update(
            {
                "quarter": record.quarter,
                "real_fspdp": _format_decimal(record.real_fspdp),
                "nominal_fspdp": _format_decimal(record.nominal_fspdp),
                "nominal_gdp": _format_decimal(record.nominal_gdp),
                "fspdp_share_of_gdp_lag1": _format_decimal(record.fspdp_share_of_gdp_lag1),
                "real_pce": _format_decimal(record.real_pce),
                "nominal_pce": _format_decimal(record.nominal_pce),
                "pce_implicit_price": _format_decimal(record.pce_implicit_price),
                "pce_implicit_inflation_qoq_pct": _format_float(
                    record.pce_implicit_inflation_qoq_pct
                ),
                "unrate_quarter_avg": _format_float(record.unrate_quarter_avg),
                "fedfunds_quarter_avg": _format_float(record.fedfunds_quarter_avg),
                "quarterly_value_bearing_100bp_year_exposure_update_2023": _format_float(
                    record.quarterly_value_bearing_100bp_year_exposure_update_2023
                ),
                "quarterly_value_bearing_100bp_year_exposure_original": _format_float(
                    record.quarterly_value_bearing_100bp_year_exposure_original
                ),
                "exposure_sign_multiplier": str(record.exposure_sign_multiplier),
                "tightening_exposure_update_2023": _format_float(
                    record.tightening_exposure_update_2023
                ),
                "tightening_exposure_original": _format_float(
                    record.tightening_exposure_original
                ),
                "elb_flag": _bool_text(record.elb_flag),
                "pandemic_flag": _bool_text(record.pandemic_flag),
                "emergency_event_count": str(record.emergency_event_count),
                "primary_sample_flag": _bool_text(record.primary_sample_flag),
                "control_source_status": record.control_source_status,
                "no_future_controls_status": record.no_future_controls_status,
                "exact_blocker": (
                    ""
                    if record.control_source_status.startswith("pass_")
                    else EXACT_BLOCKER_MISSING_CONTROLS
                ),
                "next_backend_action": (
                    "build_controlled_lp_design_matrix_and_follow_through_artifacts"
                    if record.control_source_status.startswith("pass_")
                    else "source_official_unrate_and_policy_rate_controls_without_fallback"
                ),
                "allowed_use": "controlled_lp_control_panel_input_only",
                "blocked_use": (
                    "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                    "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                    "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "controlled_lp_control_panel_not_denominator",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _controls_complete(records: Sequence[QuarterPanelRecord]) -> bool:
    relevant = [
        record
        for record in records
        if PRIMARY_START <= record.quarter <= PRIMARY_END
        and record.quarterly_value_bearing_100bp_year_exposure_update_2023 is not None
    ]
    return bool(relevant) and all(
        record.control_source_status.startswith("pass_") for record in relevant
    )


def _design_matrix_result(
    *,
    panel_records: Sequence[QuarterPanelRecord],
    macro_panel_rows: list[dict[str, str]],
    horizon_q: int,
    spec: ControlledLpSpec,
    controls_complete: bool,
) -> DesignMatrixResult:
    if not controls_complete:
        return DesignMatrixResult(
            n_obs=0,
            sample_start_q="",
            sample_end_q="",
            excluded_elb_count=0,
            excluded_pandemic_count=0,
            excluded_emergency_count=0,
            missing_future_outcome_count=0,
            missing_control_count=0,
            missing_exposure_count=0,
            design_matrix_rank=None,
            design_matrix_condition_number=None,
            design_matrix_status="blocked_missing_required_macro_controls",
            exact_blocker=EXACT_BLOCKER_MISSING_CONTROLS,
            quarters=[],
            y=[],
            x_rows=[],
        )

    macro_by_quarter = {row["quarter"]: row for row in macro_panel_rows if row.get("quarter")}
    panel_by_quarter = {record.quarter: record for record in panel_records}
    y_values: list[float] = []
    x_rows: list[list[float]] = []
    quarters: list[str] = []

    excluded_elb_count = 0
    excluded_pandemic_count = 0
    excluded_emergency_count = 0
    missing_future_outcome_count = 0
    missing_control_count = 0
    missing_exposure_count = 0

    for record in panel_records:
        if not (PRIMARY_START <= record.quarter <= spec.sample_end_q):
            continue
        exposure = _exposure_for_vintage(record, spec.exposure_vintage)
        if exposure is None:
            missing_exposure_count += 1
            continue
        if record.elb_flag:
            excluded_elb_count += 1
            continue
        if record.pandemic_flag:
            excluded_pandemic_count += 1
            continue
        if not spec.include_emergency and record.emergency_event_count > 0:
            excluded_emergency_count += 1
            continue

        quarter_index = _quarter_index_from_label(record.quarter)
        if quarter_index is None:
            missing_control_count += 1
            continue
        base_quarter = _quarter_label_from_index(quarter_index - 1)
        future_quarter = _quarter_label_from_index(quarter_index + horizon_q)
        base_real_fspdp = _decimal_or_none(macro_by_quarter.get(base_quarter, {}).get("real_fspdp"))
        future_real_fspdp = _decimal_or_none(
            macro_by_quarter.get(future_quarter, {}).get("real_fspdp")
        )
        if (
            base_real_fspdp is None
            or future_real_fspdp is None
            or base_real_fspdp <= 0
            or future_real_fspdp <= 0
        ):
            missing_future_outcome_count += 1
            continue
        if record.fspdp_share_of_gdp_lag1 is None:
            missing_control_count += 1
            continue

        controls: list[float] = []
        controls_valid = True
        for lag in range(1, spec.lag_count + 1):
            lag_quarter = _quarter_label_from_index(quarter_index - lag)
            lag_record = panel_by_quarter.get(lag_quarter)
            lag_exposure = (
                _exposure_for_vintage(lag_record, spec.exposure_vintage)
                if lag_record is not None
                else None
            )
            if (
                lag_record is None
                or lag_record.fspdp_growth_qoq_pct is None
                or lag_record.pce_implicit_inflation_qoq_pct is None
                or lag_record.unrate_quarter_avg is None
                or lag_record.fedfunds_quarter_avg is None
                or lag_exposure is None
            ):
                controls_valid = False
                break
            controls.extend(
                [
                    lag_record.fspdp_growth_qoq_pct,
                    lag_record.pce_implicit_inflation_qoq_pct,
                    lag_record.unrate_quarter_avg,
                    lag_record.fedfunds_quarter_avg,
                    lag_exposure,
                ]
            )
        if not controls_valid:
            missing_control_count += 1
            continue

        outcome = 100.0 * float(record.fspdp_share_of_gdp_lag1) * (
            math.log(float(future_real_fspdp)) - math.log(float(base_real_fspdp))
        )
        y_values.append(outcome)
        x_rows.append([1.0, exposure, *controls])
        quarters.append(record.quarter)

    if not y_values:
        return DesignMatrixResult(
            n_obs=0,
            sample_start_q="",
            sample_end_q="",
            excluded_elb_count=excluded_elb_count,
            excluded_pandemic_count=excluded_pandemic_count,
            excluded_emergency_count=excluded_emergency_count,
            missing_future_outcome_count=missing_future_outcome_count,
            missing_control_count=missing_control_count,
            missing_exposure_count=missing_exposure_count,
            design_matrix_rank=None,
            design_matrix_condition_number=None,
            design_matrix_status="blocked_missing_required_macro_controls",
            exact_blocker=EXACT_BLOCKER_MISSING_CONTROLS,
            quarters=[],
            y=[],
            x_rows=[],
        )

    import numpy as np

    x_array = np.array(x_rows, dtype=float)
    rank = int(np.linalg.matrix_rank(x_array))
    condition_number = float(np.linalg.cond(x_array))
    if rank < x_array.shape[1]:
        status = "blocked_rank_deficient_controlled_lp_design_matrix"
        exact_blocker = (
            "Controlled LP design matrix is rank-deficient for this horizon, so "
            "the candidate cannot be estimated without changing the design."
        )
    else:
        status = "pass_controlled_lp_design_matrix_available"
        exact_blocker = ""
    return DesignMatrixResult(
        n_obs=len(y_values),
        sample_start_q=quarters[0],
        sample_end_q=quarters[-1],
        excluded_elb_count=excluded_elb_count,
        excluded_pandemic_count=excluded_pandemic_count,
        excluded_emergency_count=excluded_emergency_count,
        missing_future_outcome_count=missing_future_outcome_count,
        missing_control_count=missing_control_count,
        missing_exposure_count=missing_exposure_count,
        design_matrix_rank=rank,
        design_matrix_condition_number=condition_number,
        design_matrix_status=status,
        exact_blocker=exact_blocker,
        quarters=quarters,
        y=y_values,
        x_rows=x_rows,
    )


def _design_matrix_audit_rows(results: dict[int, DesignMatrixResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for horizon in PRIMARY_HORIZONS:
        result = results[horizon]
        row = {field: "" for field in DESIGN_MATRIX_AUDIT_FIELDS}
        row.update(
            {
                "horizon_q": str(horizon),
                "exposure_vintage": EXPOSURE_VINTAGE,
                "control_spec_id": CONTROL_SPEC_ID,
                "sample_window_id": SAMPLE_WINDOW_ID,
                "outcome_formula": (
                    "100 * (nominal_fspdp[t-1] / nominal_gdp[t-1]) * "
                    "(log(real_fspdp[t+h]) - log(real_fspdp[t-1]))"
                ),
                "exposure_formula": (
                    "exposure_sign_multiplier * "
                    "quarterly_value_bearing_100bp_year_exposure_update_2023[t]"
                ),
                "control_formula": (
                    "lags_1_to_4[100 * (log(real_fspdp[t-l]) - log(real_fspdp[t-l-1])); "
                    "100 * (log(pce_implicit_price[t-l]) - log(pce_implicit_price[t-l-1])); "
                    "unrate_quarter_avg[t-l]; fedfunds_quarter_avg[t-l]; "
                    "tightening_exposure_update_2023[t-l]]"
                ),
                "lag_count": str(LAG_COUNT),
                "n_obs": str(result.n_obs),
                "sample_start_q": result.sample_start_q,
                "sample_end_q": result.sample_end_q,
                "excluded_elb_count": str(result.excluded_elb_count),
                "excluded_pandemic_count": str(result.excluded_pandemic_count),
                "excluded_emergency_count": str(result.excluded_emergency_count),
                "missing_future_outcome_count": str(result.missing_future_outcome_count),
                "missing_control_count": str(result.missing_control_count),
                "missing_exposure_count": str(result.missing_exposure_count),
                "design_matrix_rank": (
                    str(result.design_matrix_rank)
                    if result.design_matrix_rank is not None
                    else ""
                ),
                "design_matrix_condition_number": _format_float(
                    result.design_matrix_condition_number
                ),
                "design_matrix_status": result.design_matrix_status,
                "exact_blocker": result.exact_blocker,
                "allowed_use": "controlled_lp_design_matrix_audit_only",
                "blocked_use": (
                    "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                    "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                    "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "controlled_lp_design_matrix_not_denominator",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _estimate_candidate_rows(
    results: dict[int, DesignMatrixResult],
    estimates: dict[int, HacEstimate | None],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for horizon in PRIMARY_HORIZONS:
        result = results[horizon]
        row = {field: "" for field in ESTIMATE_CANDIDATE_FIELDS}
        estimate = estimates[horizon]
        if estimate is None:
            row.update(
                {
                    "horizon_q": str(horizon),
                    "exposure_vintage": EXPOSURE_VINTAGE,
                    "control_spec_id": CONTROL_SPEC_ID,
                    "sample_window_id": SAMPLE_WINDOW_ID,
                    "n_obs": str(result.n_obs),
                    "nw_bandwidth": str(max(4, horizon + 1)),
                    "bootstrap_status": "blocked_not_run_missing_estimate",
                    "response_estimate_status": "blocked_missing_required_macro_controls",
                    "denominator_candidate_status": "blocked_controlled_lp_not_estimated",
                    "promotion_rule_status": "blocked_not_yet_run",
                    "exact_blocker": result.exact_blocker or EXACT_BLOCKER_MISSING_CONTROLS,
                    "next_backend_action": (
                        "source_official_unrate_and_policy_rate_controls_without_fallback"
                    ),
                    "admitted_d_y": "",
                    "allowed_use": "controlled_lp_estimate_candidate_review_only",
                    "blocked_use": (
                        "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                        "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                        "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": "controlled_lp_estimate_candidate_not_denominator",
                    **_disabled_switches(),
                }
            )
            rows.append(row)
            continue

        row.update(
            {
                "horizon_q": str(horizon),
                "exposure_vintage": EXPOSURE_VINTAGE,
                "control_spec_id": CONTROL_SPEC_ID,
                "sample_window_id": SAMPLE_WINDOW_ID,
                "n_obs": str(result.n_obs),
                "nw_bandwidth": str(max(4, horizon + 1)),
                "beta_response_gdp_share_pp_per_100bp_year": _format_float(estimate.beta),
                "se_hac": _format_float(estimate.se),
                "ci95_low_hac": _format_float(estimate.ci_low),
                "ci95_high_hac": _format_float(estimate.ci_high),
                "d_y_candidate": _format_float(-estimate.beta),
                "candidate_ci_low_d_y": _format_float(-estimate.ci_high),
                "candidate_ci_high_d_y": _format_float(-estimate.ci_low),
                "bootstrap_ci_low_d_y": "",
                "bootstrap_ci_high_d_y": "",
                "bootstrap_status": "pass_reported_in_controlled_lp_robustness_artifact",
                "response_estimate_status": "pass_controlled_lp_candidate_estimated",
                "denominator_candidate_status": (
                    "review_only_candidate_status_deferred_to_compact_artifact"
                ),
                "promotion_rule_status": "pass_run_see_compact_status_artifact",
                "exact_blocker": EXACT_BLOCKER_CANDIDATE_REVIEW,
                "next_backend_action": (
                    "use_compact_status_artifact_for_admission_and_follow_on_gate_decisions"
                ),
                "admitted_d_y": "",
                "allowed_use": "controlled_lp_estimate_candidate_review_only",
                "blocked_use": (
                    "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                    "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                    "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "controlled_lp_estimate_candidate_not_denominator",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _independent_replication_rows(
    primary_results: dict[int, DesignMatrixResult],
    primary_estimates: dict[int, HacEstimate | None],
) -> tuple[list[dict[str, str]], dict[int, ReplicationSummary]]:
    rows: list[dict[str, str]] = []
    summaries: dict[int, ReplicationSummary] = {}
    for horizon in PRIMARY_HORIZONS:
        result = primary_results[horizon]
        primary_estimate = primary_estimates[horizon]
        bandwidth = max(4, horizon + 1)
        alt_estimate = (
            _ols_hac_lstsq(result.y, result.x_rows, bandwidth=bandwidth)
            if primary_estimate is not None
            else None
        )
        beta_diff = (
            abs(primary_estimate.beta - alt_estimate.beta)
            if primary_estimate is not None and alt_estimate is not None
            else None
        )
        se_diff = (
            abs(primary_estimate.se - alt_estimate.se)
            if primary_estimate is not None and alt_estimate is not None
            else None
        )
        if primary_estimate is None or alt_estimate is None:
            summary = ReplicationSummary(
                max_abs_beta_diff=beta_diff,
                max_abs_se_diff=se_diff,
                replication_status="blocked_primary_or_independent_estimate_missing",
                exact_blocker=result.exact_blocker or EXACT_BLOCKER_MISSING_CONTROLS,
            )
        elif beta_diff <= REPLICATION_TOLERANCE and se_diff <= REPLICATION_TOLERANCE:
            summary = ReplicationSummary(
                max_abs_beta_diff=beta_diff,
                max_abs_se_diff=se_diff,
                replication_status="pass_independent_replication_within_tolerance",
                exact_blocker="",
            )
        else:
            summary = ReplicationSummary(
                max_abs_beta_diff=beta_diff,
                max_abs_se_diff=se_diff,
                replication_status="blocked_independent_replication_mismatch_exceeds_tolerance",
                exact_blocker=(
                    "Independent closed-form OLS/HAC rebuild deviates from the primary "
                    "engine beyond tolerance."
                ),
            )
        summaries[horizon] = summary

        rows.extend(
            [
                _independent_replication_row(
                    horizon_q=horizon,
                    n_obs=result.n_obs,
                    bandwidth=bandwidth,
                    estimate=primary_estimate,
                    beta_diff=0.0 if primary_estimate is not None else None,
                    se_diff=0.0 if primary_estimate is not None else None,
                    replication_engine="current_solve_hac",
                    replication_status=(
                        "pass_primary_current_engine_recorded"
                        if primary_estimate is not None
                        else "blocked_primary_or_independent_estimate_missing"
                    ),
                    exact_blocker="",
                ),
                _independent_replication_row(
                    horizon_q=horizon,
                    n_obs=result.n_obs,
                    bandwidth=bandwidth,
                    estimate=alt_estimate,
                    beta_diff=beta_diff,
                    se_diff=se_diff,
                    replication_engine="numpy_lstsq_hac",
                    replication_status=summary.replication_status,
                    exact_blocker=summary.exact_blocker,
                ),
            ]
        )
    return rows, summaries


def _independent_replication_row(
    *,
    horizon_q: int,
    n_obs: int,
    bandwidth: int,
    estimate: HacEstimate | None,
    beta_diff: float | None,
    se_diff: float | None,
    replication_engine: str,
    replication_status: str,
    exact_blocker: str,
) -> dict[str, str]:
    row = {field: "" for field in INDEPENDENT_REPLICATION_FIELDS}
    row.update(
        {
            "horizon_q": str(horizon_q),
            "primary_spec_id": PRIMARY_SPEC_ID,
            "replication_engine": replication_engine,
            "n_obs": str(n_obs),
            "nw_bandwidth": str(bandwidth),
            "beta_response_gdp_share_pp_per_100bp_year": (
                _format_float(estimate.beta) if estimate is not None else ""
            ),
            "se_hac": _format_float(estimate.se) if estimate is not None else "",
            "ci95_low_hac": _format_float(estimate.ci_low) if estimate is not None else "",
            "ci95_high_hac": _format_float(estimate.ci_high) if estimate is not None else "",
            "max_abs_beta_diff_vs_primary": _format_float(beta_diff),
            "max_abs_se_diff_vs_primary": _format_float(se_diff),
            "replication_status": replication_status,
            "exact_blocker": exact_blocker,
            "allowed_use": "controlled_lp_independent_replication_review_only",
            "blocked_use": (
                "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "controlled_lp_independent_replication_not_denominator",
            **_disabled_switches(),
        }
    )
    return row


def _robustness_outcomes(
    *,
    panel_records: Sequence[QuarterPanelRecord],
    macro_panel_rows: list[dict[str, str]],
    controls_complete: bool,
) -> dict[int, dict[str, RobustnessOutcome]]:
    outcomes: dict[int, dict[str, RobustnessOutcome]] = {}
    for horizon in STATUS_HORIZONS:
        case_outcomes: dict[str, RobustnessOutcome] = {}
        for case_index, spec in enumerate(_robustness_specs()):
            result = _design_matrix_result(
                panel_records=panel_records,
                macro_panel_rows=macro_panel_rows,
                horizon_q=horizon,
                spec=spec,
                controls_complete=controls_complete,
            )
            estimate = (
                _ols_hac(result.y, result.x_rows, bandwidth=max(4, horizon + 1))
                if result.design_matrix_status == "pass_controlled_lp_design_matrix_available"
                else None
            )
            bootstrap = (
                _moving_block_bootstrap_d_y(
                    result.y,
                    result.x_rows,
                    bandwidth=max(4, horizon + 1),
                    block_length=max(4, horizon + 1),
                    seed=BOOTSTRAP_SEED + horizon * 100 + case_index,
                )
                if estimate is not None
                else None
            )
            robustness_status, exact_blocker = _robustness_case_status(
                spec=spec,
                result=result,
                estimate=estimate,
                bootstrap=bootstrap,
            )
            case_outcomes[spec.case_id] = RobustnessOutcome(
                spec=spec,
                design_result=result,
                estimate=estimate,
                bootstrap=bootstrap,
                robustness_status=robustness_status,
                exact_blocker=exact_blocker,
                next_backend_action=(
                    "pivot_to_residualized_or_proxy_iv_if_h8_sign_or_support_fails"
                    if robustness_status.startswith("blocked_")
                    else "keep_case_as_narrow_robustness_support_only"
                ),
            )

        primary = case_outcomes["primary_update_2023_4lag"]
        if primary.estimate is None:
            case_outcomes["leave_one_out_max_influence"] = RobustnessOutcome(
                spec=ControlledLpSpec(
                    case_id="leave_one_out_max_influence",
                    exposure_vintage="update_2023",
                    lag_count=4,
                    include_emergency=False,
                    sample_end_q=PRIMARY_END,
                    sample_window_id=SAMPLE_WINDOW_ID,
                    control_spec_id=CONTROL_SPEC_ID,
                ),
                design_result=primary.design_result,
                estimate=None,
                bootstrap=None,
                robustness_status="blocked_leave_one_out_missing_primary_estimate",
                exact_blocker=primary.exact_blocker or EXACT_BLOCKER_MISSING_CONTROLS,
                next_backend_action="restore_primary_estimate_before_leave_one_out_review",
            )
        else:
            loo_median, loo_positive_share, max_quarter, max_shift = _leave_one_out_metrics(
                primary.design_result.y,
                primary.design_result.x_rows,
                primary.design_result.quarters,
                bandwidth=max(4, horizon + 1),
            )
            primary_d_y = -primary.estimate.beta
            if loo_median <= 0:
                loo_status = "blocked_leave_one_out_median_sign_not_positive"
                loo_blocker = (
                    "Leave-one-out median sign is not positive, so the controlled denominator "
                    "is not stable enough for admission."
                )
            elif loo_positive_share <= 0.5:
                loo_status = "blocked_leave_one_out_positive_share_not_majority"
                loo_blocker = (
                    "Leave-one-out sign is not positive for a majority of subsamples."
                )
            elif max_shift >= abs(primary_d_y):
                loo_status = "blocked_leave_one_out_one_quarter_dominated"
                loo_blocker = (
                    "Removing one quarter can shift the controlled denominator by at least its "
                    "full baseline magnitude."
                )
            else:
                loo_status = "pass_leave_one_out_sign_stable_not_dominated"
                loo_blocker = ""
            case_outcomes["leave_one_out_max_influence"] = RobustnessOutcome(
                spec=ControlledLpSpec(
                    case_id="leave_one_out_max_influence",
                    exposure_vintage="update_2023",
                    lag_count=4,
                    include_emergency=False,
                    sample_end_q=PRIMARY_END,
                    sample_window_id=SAMPLE_WINDOW_ID,
                    control_spec_id=CONTROL_SPEC_ID,
                ),
                design_result=primary.design_result,
                estimate=primary.estimate,
                bootstrap=primary.bootstrap,
                robustness_status=loo_status,
                exact_blocker=loo_blocker,
                next_backend_action=(
                    "pivot_to_residualized_or_proxy_iv_if_h8_sign_or_support_fails"
                    if loo_status.startswith("blocked_")
                    else "report_leave_one_out_support_in_compact_status_only"
                ),
                leave_one_out_median_d_y=loo_median,
                leave_one_out_positive_share=loo_positive_share,
                max_influence_quarter=max_quarter,
                max_abs_loo_shift=max_shift,
            )
        outcomes[horizon] = case_outcomes
    return outcomes


def _robustness_case_status(
    *,
    spec: ControlledLpSpec,
    result: DesignMatrixResult,
    estimate: HacEstimate | None,
    bootstrap: BootstrapResult | None,
) -> tuple[str, str]:
    if result.design_matrix_status != "pass_controlled_lp_design_matrix_available" or estimate is None:
        return "blocked_robustness_case_missing_estimate", result.exact_blocker or EXACT_BLOCKER_MISSING_CONTROLS
    if spec.case_id == "pre_2008_conventional_if_nobs_usable" and result.n_obs < MIN_PRE_2008_ROBUSTNESS_NOBS:
        return (
            "review_only_pre_2008_nobs_not_usable",
            "Pre-2008 conventional-only sample is too small for the required narrow robustness case.",
        )
    if bootstrap is None or bootstrap.status != "pass_bootstrap_completed":
        return (
            "blocked_bootstrap_not_completed_for_robustness_case",
            "Moving-block bootstrap did not complete successfully for this robustness case.",
        )
    if -estimate.beta <= 0:
        return (
            "blocked_wrong_sign_in_robustness_case",
            "Controlled denominator is wrong-sign in this robustness case.",
        )
    if bootstrap.sign_probability is not None and bootstrap.sign_probability <= 0.5:
        return (
            "blocked_bootstrap_sign_probability_not_majority_positive",
            "Bootstrap sign probability is not positive in a majority of draws for this robustness case.",
        )
    return "pass_sign_preserved_in_robustness_case", ""


def _robustness_rows(
    outcomes: dict[int, dict[str, RobustnessOutcome]]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    ordered_cases = [
        "primary_update_2023_4lag",
        "original_vintage_4lag",
        "update_2023_2lag",
        "update_2023_6lag",
        "include_emergency_exclude_elb_pandemic",
        "pre_2008_conventional_if_nobs_usable",
        "leave_one_out_max_influence",
    ]
    for horizon in STATUS_HORIZONS:
        for case_id in ordered_cases:
            outcome = outcomes[horizon][case_id]
            estimate = outcome.estimate
            bootstrap = outcome.bootstrap
            row = {field: "" for field in ROBUSTNESS_FIELDS}
            row.update(
                {
                    "horizon_q": str(horizon),
                    "robustness_case": case_id,
                    "exposure_vintage": outcome.spec.exposure_vintage,
                    "lag_count": str(outcome.spec.lag_count),
                    "sample_window_id": outcome.spec.sample_window_id,
                    "n_obs": str(outcome.design_result.n_obs),
                    "nw_bandwidth": str(max(4, horizon + 1)),
                    "beta_response_gdp_share_pp_per_100bp_year": (
                        _format_float(estimate.beta) if estimate is not None else ""
                    ),
                    "d_y": _format_float(-estimate.beta) if estimate is not None else "",
                    "se_hac": _format_float(estimate.se) if estimate is not None else "",
                    "ci95_low_hac": _format_float(estimate.ci_low) if estimate is not None else "",
                    "ci95_high_hac": _format_float(estimate.ci_high) if estimate is not None else "",
                    "bootstrap_ci_low_d_y": (
                        _format_float(bootstrap.ci_low_d_y)
                        if bootstrap is not None
                        else ""
                    ),
                    "bootstrap_ci_high_d_y": (
                        _format_float(bootstrap.ci_high_d_y)
                        if bootstrap is not None
                        else ""
                    ),
                    "bootstrap_sign_probability_d_y_positive": (
                        _format_float(bootstrap.sign_probability)
                        if bootstrap is not None
                        else ""
                    ),
                    "leave_one_out_median_d_y": _format_float(
                        outcome.leave_one_out_median_d_y
                    ),
                    "leave_one_out_positive_share": _format_float(
                        outcome.leave_one_out_positive_share
                    ),
                    "max_influence_quarter": outcome.max_influence_quarter,
                    "max_abs_loo_shift": _format_float(outcome.max_abs_loo_shift),
                    "robustness_status": outcome.robustness_status,
                    "exact_blocker": outcome.exact_blocker,
                    "next_backend_action": outcome.next_backend_action,
                    "allowed_use": "controlled_lp_narrow_robustness_review_only",
                    "blocked_use": (
                        "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                        "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                        "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": "controlled_lp_robustness_not_main_ratio",
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    return rows


def _instrument_variant_specs() -> tuple[InstrumentVariantSpec, ...]:
    return (
        InstrumentVariantSpec(
            variant_id="sf_fed_usmpd_me_scalar_quarterly_sum",
            shock_source_id="sf_fed_usmpd",
            instrument_series_id="mps_csv_me_quarterly_sum",
            instrument_class="source_backed_scalar_proxy_instrument",
            source_artifact_path=SF_FED_MPS_ZIP_PATH,
            source_artifact_entry="mps.csv::ME",
            instrument_unit="source_scalar_surprise",
        ),
        InstrumentVariantSpec(
            variant_id="sf_fed_chart_raw_surprise_quarterly_sum",
            shock_source_id="sf_fed_monetary_policy_surprises",
            instrument_series_id="public_chart_raw_surprise_quarterly_sum",
            instrument_class="public_raw_surprise_instrument",
            source_artifact_path=SF_FED_PUBLIC_SURPRISE_CHART_PATH,
            source_artifact_entry="sf_fed_monetary_policy_surprises_chart.csv::Surprise",
            instrument_unit="basis_points",
        ),
        InstrumentVariantSpec(
            variant_id="sf_fed_chart_orthogonalized_surprise_quarterly_sum",
            shock_source_id="sf_fed_monetary_policy_surprises",
            instrument_series_id="public_chart_orthogonalized_surprise_quarterly_sum",
            instrument_class="public_orthogonalized_surprise_instrument",
            source_artifact_path=SF_FED_PUBLIC_SURPRISE_CHART_PATH,
            source_artifact_entry=(
                "sf_fed_monetary_policy_surprises_chart.csv::Orthogonalized Surprise"
            ),
            instrument_unit="basis_points",
        ),
    )


def _identification_variant_quarterly_rows(
    exposure_quarterly_rows: Sequence[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, dict[str, InstrumentQuarterRecord]]]:
    exposure_by_quarter = {
        row.get("quarter", ""): row
        for row in exposure_quarterly_rows
        if row.get("source_sheet_vintage") == "update_2023" and row.get("quarter")
    }
    instrument_records = _instrument_quarter_records(exposure_by_quarter)
    rows: list[dict[str, str]] = []
    for spec in _instrument_variant_specs():
        for quarter in sorted(instrument_records[spec.variant_id]):
            record = instrument_records[spec.variant_id][quarter]
            row = {field: "" for field in IDENTIFICATION_VARIANT_QUARTERLY_FIELDS}
            row.update(
                {
                    "quarter": record.quarter,
                    "instrument_variant": record.instrument_variant,
                    "shock_source_id": record.shock_source_id,
                    "instrument_series_id": record.instrument_series_id,
                    "instrument_class": record.instrument_class,
                    "source_artifact_path": record.source_artifact_path,
                    "source_artifact_entry": record.source_artifact_entry,
                    "source_artifact_sha256": record.source_artifact_sha256,
                    "instrument_unit": record.instrument_unit,
                    "quarterly_instrument_value": _format_float(
                        record.quarterly_instrument_value
                    ),
                    "event_count": str(record.event_count),
                    "matched_exposure_vintage": "update_2023",
                    "matched_tightening_exposure_update_2023": _format_float(
                        record.matched_tightening_exposure_update_2023
                    ),
                    "emergency_event_count": str(record.emergency_event_count),
                    "elb_flag": _bool_text(record.elb_flag),
                    "pandemic_flag": _bool_text(record.pandemic_flag),
                    "first_event_date": record.first_event_date,
                    "last_event_date": record.last_event_date,
                    "identification_series_status": (
                        "pass_source_backed_quarterly_identification_series_available"
                    ),
                    "exact_blocker": (
                        "Quarterly source-backed surprise/proxy instrument is "
                        "available for identification checks only. It is not the "
                        "bps-year treatment path, not D_Y, and not a main-ratio input."
                    ),
                    "next_backend_action": (
                        "use_as_excluded_instrument_or_identification_sensitivity_only"
                    ),
                    "allowed_use": "quarterly_identification_variant_review_only",
                    "blocked_use": (
                        "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                        "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                        "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
                    ),
                    "claim_boundary": "identification_variant_not_treatment_or_denominator",
                    **_disabled_switches(),
                }
            )
            rows.append(row)
    return rows, instrument_records


def _instrument_quarter_records(
    exposure_by_quarter: dict[str, dict[str, str]],
) -> dict[str, dict[str, InstrumentQuarterRecord]]:
    rows_by_variant = {
        spec.variant_id: {} for spec in _instrument_variant_specs()
    }
    rows_by_variant["sf_fed_usmpd_me_scalar_quarterly_sum"] = _quarterly_me_records(
        exposure_by_quarter
    )
    raw_rows, orth_rows = _quarterly_public_surprise_records(exposure_by_quarter)
    rows_by_variant["sf_fed_chart_raw_surprise_quarterly_sum"] = raw_rows
    rows_by_variant["sf_fed_chart_orthogonalized_surprise_quarterly_sum"] = orth_rows
    return rows_by_variant


def _quarterly_me_records(
    exposure_by_quarter: dict[str, dict[str, str]],
) -> dict[str, InstrumentQuarterRecord]:
    spec = next(
        item
        for item in _instrument_variant_specs()
        if item.variant_id == "sf_fed_usmpd_me_scalar_quarterly_sum"
    )
    grouped: dict[str, dict[str, object]] = {}
    with zipfile.ZipFile(spec.source_artifact_path) as archive:
        reader = csv.DictReader(
            archive.read("mps.csv").decode("utf-8-sig").splitlines()
        )
        for row in reader:
            value = _float_or_none(row.get("ME"))
            date_text = str(row.get("Date", ""))
            if value is None or not date_text:
                continue
            quarter = _quarter_label(date_text)
            bucket = grouped.setdefault(
                quarter,
                {
                    "value": 0.0,
                    "event_count": 0,
                    "first_event_date": date_text,
                    "last_event_date": date_text,
                },
            )
            bucket["value"] = float(bucket["value"]) + value
            bucket["event_count"] = int(bucket["event_count"]) + 1
            bucket["first_event_date"] = min(str(bucket["first_event_date"]), date_text)
            bucket["last_event_date"] = max(str(bucket["last_event_date"]), date_text)
    return _instrument_records_from_grouped(
        spec=spec,
        grouped=grouped,
        exposure_by_quarter=exposure_by_quarter,
    )


def _quarterly_public_surprise_records(
    exposure_by_quarter: dict[str, dict[str, str]],
) -> tuple[dict[str, InstrumentQuarterRecord], dict[str, InstrumentQuarterRecord]]:
    raw_spec = next(
        item
        for item in _instrument_variant_specs()
        if item.variant_id == "sf_fed_chart_raw_surprise_quarterly_sum"
    )
    orth_spec = next(
        item
        for item in _instrument_variant_specs()
        if item.variant_id == "sf_fed_chart_orthogonalized_surprise_quarterly_sum"
    )
    raw_grouped: dict[str, dict[str, object]] = {}
    orth_grouped: dict[str, dict[str, object]] = {}
    with raw_spec.source_artifact_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            date_text = str(row.get("Date", ""))
            if not date_text:
                continue
            quarter = _quarter_label(date_text)
            raw_value = _float_or_none(row.get("Surprise"))
            orth_value = _float_or_none(row.get("Orthogonalized Surprise"))
            if raw_value is not None:
                bucket = raw_grouped.setdefault(
                    quarter,
                    {
                        "value": 0.0,
                        "event_count": 0,
                        "first_event_date": date_text,
                        "last_event_date": date_text,
                    },
                )
                bucket["value"] = float(bucket["value"]) + raw_value
                bucket["event_count"] = int(bucket["event_count"]) + 1
                bucket["first_event_date"] = min(
                    str(bucket["first_event_date"]), date_text
                )
                bucket["last_event_date"] = max(str(bucket["last_event_date"]), date_text)
            if orth_value is not None:
                bucket = orth_grouped.setdefault(
                    quarter,
                    {
                        "value": 0.0,
                        "event_count": 0,
                        "first_event_date": date_text,
                        "last_event_date": date_text,
                    },
                )
                bucket["value"] = float(bucket["value"]) + orth_value
                bucket["event_count"] = int(bucket["event_count"]) + 1
                bucket["first_event_date"] = min(
                    str(bucket["first_event_date"]), date_text
                )
                bucket["last_event_date"] = max(str(bucket["last_event_date"]), date_text)
    return (
        _instrument_records_from_grouped(
            spec=raw_spec,
            grouped=raw_grouped,
            exposure_by_quarter=exposure_by_quarter,
        ),
        _instrument_records_from_grouped(
            spec=orth_spec,
            grouped=orth_grouped,
            exposure_by_quarter=exposure_by_quarter,
        ),
    )


def _instrument_records_from_grouped(
    *,
    spec: InstrumentVariantSpec,
    grouped: dict[str, dict[str, object]],
    exposure_by_quarter: dict[str, dict[str, str]],
) -> dict[str, InstrumentQuarterRecord]:
    artifact_sha = _file_sha256(spec.source_artifact_path)
    records: dict[str, InstrumentQuarterRecord] = {}
    for quarter, grouped_row in grouped.items():
        exposure_row = exposure_by_quarter.get(quarter, {})
        records[quarter] = InstrumentQuarterRecord(
            quarter=quarter,
            instrument_variant=spec.variant_id,
            shock_source_id=spec.shock_source_id,
            instrument_series_id=spec.instrument_series_id,
            instrument_class=spec.instrument_class,
            source_artifact_path=str(spec.source_artifact_path),
            source_artifact_entry=spec.source_artifact_entry,
            source_artifact_sha256=artifact_sha,
            instrument_unit=spec.instrument_unit,
            quarterly_instrument_value=float(grouped_row["value"]),
            event_count=int(grouped_row["event_count"]),
            first_event_date=str(grouped_row["first_event_date"]),
            last_event_date=str(grouped_row["last_event_date"]),
            matched_tightening_exposure_update_2023=_float_or_none(
                exposure_row.get("quarterly_value_bearing_100bp_year_exposure")
            ),
            emergency_event_count=_int_or_zero(exposure_row.get("emergency_event_count")),
            elb_flag=exposure_row.get("elb_flag") == "true",
            pandemic_flag=exposure_row.get("pandemic_flag") == "true",
        )
    return records


def _identification_check_rows(
    *,
    primary_results: dict[int, DesignMatrixResult],
    instrument_quarter_records: dict[str, dict[str, InstrumentQuarterRecord]],
) -> tuple[list[dict[str, str]], dict[int, dict[str, IdentificationCheckOutcome]]]:
    rows: list[dict[str, str]] = []
    outcomes: dict[int, dict[str, IdentificationCheckOutcome]] = {}
    ordered_variants = [spec.variant_id for spec in _instrument_variant_specs()]
    for horizon in STATUS_HORIZONS:
        result = primary_results[horizon]
        horizon_outcomes: dict[str, IdentificationCheckOutcome] = {}
        for variant_id in ordered_variants:
            outcome = _identification_check_outcome(
                horizon_q=horizon,
                primary_result=result,
                quarter_records=instrument_quarter_records[variant_id],
            )
            horizon_outcomes[variant_id] = outcome
            rows.append(_identification_check_row(outcome))
        outcomes[horizon] = horizon_outcomes
    return rows, outcomes


def _identification_check_outcome(
    *,
    horizon_q: int,
    primary_result: DesignMatrixResult,
    quarter_records: dict[str, InstrumentQuarterRecord],
) -> IdentificationCheckOutcome:
    exemplar = next(iter(quarter_records.values()), None)
    bandwidth = max(4, horizon_q + 1)
    if exemplar is None:
        return IdentificationCheckOutcome(
            horizon_q=horizon_q,
            instrument_variant="",
            shock_source_id="",
            instrument_series_id="",
            instrument_class="",
            n_obs=0,
            sample_start_q="",
            sample_end_q="",
            instrument_missing_quarter_count=primary_result.n_obs,
            bandwidth=bandwidth,
            first_stage=None,
            reduced_form=None,
            iv_estimate=None,
            identification_check_status="blocked_identification_series_missing",
            exact_blocker="Identification instrument series is missing for this variant.",
            next_backend_action="repair_instrument_source_bridge_before_identification_review",
        )
    if primary_result.design_matrix_status != "pass_controlled_lp_design_matrix_available":
        return IdentificationCheckOutcome(
            horizon_q=horizon_q,
            instrument_variant=exemplar.instrument_variant,
            shock_source_id=exemplar.shock_source_id,
            instrument_series_id=exemplar.instrument_series_id,
            instrument_class=exemplar.instrument_class,
            n_obs=0,
            sample_start_q="",
            sample_end_q="",
            instrument_missing_quarter_count=primary_result.n_obs,
            bandwidth=bandwidth,
            first_stage=None,
            reduced_form=None,
            iv_estimate=None,
            identification_check_status="blocked_primary_design_matrix_missing",
            exact_blocker=primary_result.exact_blocker or EXACT_BLOCKER_MISSING_CONTROLS,
            next_backend_action="restore_primary_controlled_design_matrix_before_identification_review",
        )

    matched_indexes = [
        index
        for index, quarter in enumerate(primary_result.quarters)
        if quarter in quarter_records
    ]
    if len(matched_indexes) < MIN_IV_SAMPLE_NOBS:
        return IdentificationCheckOutcome(
            horizon_q=horizon_q,
            instrument_variant=exemplar.instrument_variant,
            shock_source_id=exemplar.shock_source_id,
            instrument_series_id=exemplar.instrument_series_id,
            instrument_class=exemplar.instrument_class,
            n_obs=len(matched_indexes),
            sample_start_q="",
            sample_end_q="",
            instrument_missing_quarter_count=primary_result.n_obs - len(matched_indexes),
            bandwidth=bandwidth,
            first_stage=None,
            reduced_form=None,
            iv_estimate=None,
            identification_check_status="blocked_identification_overlap_too_short",
            exact_blocker=(
                "Quarterly overlap between the primary controlled sample and this "
                "instrument is too short for a bounded identification check."
            ),
            next_backend_action="use_longer_overlap_proxy_instrument_or_shorten_scope_explicitly",
        )

    matched_quarters = [primary_result.quarters[index] for index in matched_indexes]
    y_values = [primary_result.y[index] for index in matched_indexes]
    x_rows = [primary_result.x_rows[index] for index in matched_indexes]
    z_values = [
        quarter_records[primary_result.quarters[index]].quarterly_instrument_value
        for index in matched_indexes
    ]
    first_stage_x_rows = [
        [1.0, z_value, *x_row[2:]] for z_value, x_row in zip(z_values, x_rows)
    ]
    exposure_values = [x_row[1] for x_row in x_rows]
    first_stage = _ols_hac(exposure_values, first_stage_x_rows, bandwidth=bandwidth)
    reduced_form = _ols_hac(y_values, first_stage_x_rows, bandwidth=bandwidth)
    iv_estimate = _iv_2sls_hac(
        y_values=y_values,
        x_rows=x_rows,
        z_values=z_values,
        bandwidth=bandwidth,
    )
    first_stage_t = _safe_t_stat(first_stage)
    first_stage_f = first_stage_t * first_stage_t if first_stage_t is not None else None

    if iv_estimate is None:
        status = "blocked_iv_design_singular"
        exact_blocker = (
            "IV normal equations are singular for this instrument/sample overlap."
        )
        next_action = "keep_variant_as_bridge_only_and_compare_alternative_instruments"
    elif first_stage_f is None or first_stage_f < FIRST_STAGE_F_THRESHOLD:
        status = "blocked_first_stage_not_strong_enough_for_review"
        exact_blocker = (
            "First-stage support for this quarterly instrument is below the bounded "
            "review threshold, so the LP-IV row stays diagnostic only."
        )
        next_action = "prefer_me_scalar_proxy_or_stronger_short_overlap_instrument"
    elif -iv_estimate.beta <= 0:
        status = "blocked_proxy_iv_wrong_sign"
        exact_blocker = (
            "This LP-IV identification variant is wrong-sign for the denominator "
            "candidate after the audited tightening convention."
        )
        next_action = "do_not_promote_variant_and_compare_against_frbus_benchmark_only"
    elif exemplar.instrument_variant == "sf_fed_usmpd_me_scalar_quarterly_sum":
        status = "pass_long_sample_proxy_iv_sign_supported_review_only"
        exact_blocker = (
            "Long-sample USMPD ME proxy-IV check is sign-supportive and now feeds "
            "the bounded h8 review object, but this identification row itself "
            "remains review-only because the primary admitted noncanonical object "
            "lives in the bounded denominator registry rather than in the "
            "identification table."
        )
        next_action = (
            "keep_as_identification_support_and_reference_bounded_h8_registry"
        )
    elif exemplar.instrument_variant == "sf_fed_chart_orthogonalized_surprise_quarterly_sum":
        status = "pass_short_sample_orthogonalized_proxy_iv_sign_supported_review_only"
        exact_blocker = (
            "Short-overlap public orthogonalized-surprise LP-IV check is "
            "sign-supportive, but the overlap is too short for admission."
        )
        next_action = "keep_public_orthogonalized_check_as_secondary_support_only"
    else:
        status = "pass_short_sample_raw_proxy_iv_secondary_review_only"
        exact_blocker = (
            "Short-overlap public raw-surprise LP-IV check is secondary review "
            "support only and cannot by itself admit the denominator."
        )
        next_action = "keep_raw_variant_secondary_and_privilege_policy_only_checks"

    return IdentificationCheckOutcome(
        horizon_q=horizon_q,
        instrument_variant=exemplar.instrument_variant,
        shock_source_id=exemplar.shock_source_id,
        instrument_series_id=exemplar.instrument_series_id,
        instrument_class=exemplar.instrument_class,
        n_obs=len(matched_indexes),
        sample_start_q=matched_quarters[0],
        sample_end_q=matched_quarters[-1],
        instrument_missing_quarter_count=primary_result.n_obs - len(matched_indexes),
        bandwidth=bandwidth,
        first_stage=first_stage,
        reduced_form=reduced_form,
        iv_estimate=iv_estimate,
        identification_check_status=status,
        exact_blocker=exact_blocker,
        next_backend_action=next_action,
    )


def _identification_check_row(
    outcome: IdentificationCheckOutcome,
) -> dict[str, str]:
    first_stage_t = _safe_t_stat(outcome.first_stage)
    first_stage_f = first_stage_t * first_stage_t if first_stage_t is not None else None
    row = {field: "" for field in IDENTIFICATION_CHECK_FIELDS}
    row.update(
        {
            "horizon_q": str(outcome.horizon_q),
            "instrument_variant": outcome.instrument_variant,
            "shock_source_id": outcome.shock_source_id,
            "instrument_series_id": outcome.instrument_series_id,
            "instrument_class": outcome.instrument_class,
            "sample_window_id": SAMPLE_WINDOW_ID,
            "control_spec_id": CONTROL_SPEC_ID,
            "n_obs": str(outcome.n_obs),
            "sample_start_q": outcome.sample_start_q,
            "sample_end_q": outcome.sample_end_q,
            "instrument_missing_quarter_count": str(
                outcome.instrument_missing_quarter_count
            ),
            "nw_bandwidth": str(outcome.bandwidth),
            "first_stage_coef_exposure_per_instrument_unit": (
                _format_float(outcome.first_stage.beta)
                if outcome.first_stage is not None
                else ""
            ),
            "first_stage_se_hac": (
                _format_float(outcome.first_stage.se)
                if outcome.first_stage is not None
                else ""
            ),
            "first_stage_ci95_low_hac": (
                _format_float(outcome.first_stage.ci_low)
                if outcome.first_stage is not None
                else ""
            ),
            "first_stage_ci95_high_hac": (
                _format_float(outcome.first_stage.ci_high)
                if outcome.first_stage is not None
                else ""
            ),
            "first_stage_t_hac": _format_float(first_stage_t),
            "first_stage_f_hac": _format_float(first_stage_f),
            "reduced_form_coef_outcome_per_instrument_unit": (
                _format_float(outcome.reduced_form.beta)
                if outcome.reduced_form is not None
                else ""
            ),
            "reduced_form_se_hac": (
                _format_float(outcome.reduced_form.se)
                if outcome.reduced_form is not None
                else ""
            ),
            "reduced_form_ci95_low_hac": (
                _format_float(outcome.reduced_form.ci_low)
                if outcome.reduced_form is not None
                else ""
            ),
            "reduced_form_ci95_high_hac": (
                _format_float(outcome.reduced_form.ci_high)
                if outcome.reduced_form is not None
                else ""
            ),
            "iv_beta_response_gdp_share_pp_per_100bp_year": (
                _format_float(outcome.iv_estimate.beta)
                if outcome.iv_estimate is not None
                else ""
            ),
            "iv_se_hac": (
                _format_float(outcome.iv_estimate.se)
                if outcome.iv_estimate is not None
                else ""
            ),
            "iv_ci95_low_hac": (
                _format_float(outcome.iv_estimate.ci_low)
                if outcome.iv_estimate is not None
                else ""
            ),
            "iv_ci95_high_hac": (
                _format_float(outcome.iv_estimate.ci_high)
                if outcome.iv_estimate is not None
                else ""
            ),
            "iv_d_y_candidate": (
                _format_float(-outcome.iv_estimate.beta)
                if outcome.iv_estimate is not None
                else ""
            ),
            "iv_candidate_ci_low_d_y": (
                _format_float(-outcome.iv_estimate.ci_high)
                if outcome.iv_estimate is not None
                else ""
            ),
            "iv_candidate_ci_high_d_y": (
                _format_float(-outcome.iv_estimate.ci_low)
                if outcome.iv_estimate is not None
                else ""
            ),
            "identification_check_status": outcome.identification_check_status,
            "exact_blocker": outcome.exact_blocker,
            "next_backend_action": outcome.next_backend_action,
            "allowed_use": "controlled_lp_identification_check_review_only",
            "blocked_use": (
                "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "controlled_lp_identification_check_not_denominator",
            **_disabled_switches(),
        }
    )
    return row


def _frbus_benchmark_crosscheck_rows(
    *,
    identification_outcomes: dict[int, dict[str, IdentificationCheckOutcome]],
) -> tuple[list[dict[str, str]], dict[int, list[FrbusBenchmarkCrosscheckOutcome]]]:
    frbus_responses, response_blocker = _frbus_directional_benchmark_responses()
    rows: list[dict[str, str]] = []
    outcomes_by_horizon: dict[int, list[FrbusBenchmarkCrosscheckOutcome]] = {}
    for horizon in STATUS_HORIZONS:
        me_outcome = identification_outcomes.get(horizon, {}).get(
            "sf_fed_usmpd_me_scalar_quarterly_sum"
        )
        horizon_outcomes: list[FrbusBenchmarkCrosscheckOutcome] = []
        for benchmark_outcome_id, benchmark_outcome_variable, benchmark_outcome_label in (
            ("real_gdp", "XGDP", "Real GDP benchmark"),
            ("real_pce", "EC", "Real PCE benchmark"),
            (
                "real_private_fixed_investment",
                "EBFI",
                "Real private fixed investment benchmark",
            ),
        ):
            response = frbus_responses.get((horizon, benchmark_outcome_id))
            empirical_iv_d_y = (
                -me_outcome.iv_estimate.beta
                if me_outcome is not None and me_outcome.iv_estimate is not None
                else None
            )
            empirical_iv_ci_low = (
                -me_outcome.iv_estimate.ci_high
                if me_outcome is not None and me_outcome.iv_estimate is not None
                else None
            )
            empirical_iv_ci_high = (
                -me_outcome.iv_estimate.ci_low
                if me_outcome is not None and me_outcome.iv_estimate is not None
                else None
            )
            if response is None:
                outcome = FrbusBenchmarkCrosscheckOutcome(
                    horizon_q=horizon,
                    benchmark_outcome_id=benchmark_outcome_id,
                    benchmark_outcome_variable=benchmark_outcome_variable,
                    benchmark_outcome_label=benchmark_outcome_label,
                    baseline_level=None,
                    shock_level=None,
                    delta_level=None,
                    pct_delta_from_baseline=None,
                    empirical_instrument_variant=(
                        me_outcome.instrument_variant if me_outcome is not None else ""
                    ),
                    empirical_iv_d_y_candidate=empirical_iv_d_y,
                    empirical_iv_ci_low_d_y=empirical_iv_ci_low,
                    empirical_iv_ci_high_d_y=empirical_iv_ci_high,
                    benchmark_crosscheck_status="blocked_frbus_directional_benchmark_missing",
                    exact_blocker=response_blocker
                    or "FRB/US directional benchmark response is missing.",
                    next_backend_action=(
                        "repair_frbus_directional_benchmark_response_before_promotion_rule_review"
                    ),
                )
            elif me_outcome is None or me_outcome.iv_estimate is None:
                outcome = FrbusBenchmarkCrosscheckOutcome(
                    horizon_q=horizon,
                    benchmark_outcome_id=benchmark_outcome_id,
                    benchmark_outcome_variable=benchmark_outcome_variable,
                    benchmark_outcome_label=benchmark_outcome_label,
                    baseline_level=response["baseline_level"],
                    shock_level=response["shock_level"],
                    delta_level=response["delta_level"],
                    pct_delta_from_baseline=response["pct_delta_from_baseline"],
                    empirical_instrument_variant=(
                        me_outcome.instrument_variant if me_outcome is not None else ""
                    ),
                    empirical_iv_d_y_candidate=empirical_iv_d_y,
                    empirical_iv_ci_low_d_y=empirical_iv_ci_low,
                    empirical_iv_ci_high_d_y=empirical_iv_ci_high,
                    benchmark_crosscheck_status="blocked_empirical_proxy_iv_row_missing",
                    exact_blocker=(
                        "FRB/US benchmark response exists, but the long-sample proxy-IV "
                        "comparison row is missing for this horizon."
                    ),
                    next_backend_action=(
                        "restore_long_sample_proxy_iv_row_before_benchmark_crosscheck_review"
                    ),
                )
            elif response["delta_level"] < 0 and empirical_iv_d_y is not None and empirical_iv_d_y > 0:
                outcome = FrbusBenchmarkCrosscheckOutcome(
                    horizon_q=horizon,
                    benchmark_outcome_id=benchmark_outcome_id,
                    benchmark_outcome_variable=benchmark_outcome_variable,
                    benchmark_outcome_label=benchmark_outcome_label,
                    baseline_level=response["baseline_level"],
                    shock_level=response["shock_level"],
                    delta_level=response["delta_level"],
                    pct_delta_from_baseline=response["pct_delta_from_baseline"],
                    empirical_instrument_variant=me_outcome.instrument_variant,
                    empirical_iv_d_y_candidate=empirical_iv_d_y,
                    empirical_iv_ci_low_d_y=empirical_iv_ci_low,
                    empirical_iv_ci_high_d_y=empirical_iv_ci_high,
                    benchmark_crosscheck_status=(
                        "pass_directional_frbus_benchmark_consistent_with_positive_d_y"
                    ),
                    exact_blocker=(
                        "FRB/US benchmark remains directional context only; no scale or "
                        "100bp-year equivalence is implied."
                    ),
                    next_backend_action=(
                        "use_directional_frbus_context_inside_bounded_promotion_rule_only"
                    ),
                )
            else:
                outcome = FrbusBenchmarkCrosscheckOutcome(
                    horizon_q=horizon,
                    benchmark_outcome_id=benchmark_outcome_id,
                    benchmark_outcome_variable=benchmark_outcome_variable,
                    benchmark_outcome_label=benchmark_outcome_label,
                    baseline_level=response["baseline_level"],
                    shock_level=response["shock_level"],
                    delta_level=response["delta_level"],
                    pct_delta_from_baseline=response["pct_delta_from_baseline"],
                    empirical_instrument_variant=me_outcome.instrument_variant,
                    empirical_iv_d_y_candidate=empirical_iv_d_y,
                    empirical_iv_ci_low_d_y=empirical_iv_ci_low,
                    empirical_iv_ci_high_d_y=empirical_iv_ci_high,
                    benchmark_crosscheck_status=(
                        "blocked_directional_frbus_benchmark_inconsistent_with_positive_d_y"
                    ),
                    exact_blocker=(
                        "FRB/US benchmark directional response is not contractionary for "
                        "this horizon/outcome, so it does not support the positive D_Y sign."
                    ),
                    next_backend_action=(
                        "revisit_proxy_iv_horizon_choice_or_benchmark_mapping_before_promotion"
                    ),
                )
            horizon_outcomes.append(outcome)
            rows.append(_frbus_benchmark_crosscheck_row(outcome))
        outcomes_by_horizon[horizon] = horizon_outcomes
    return rows, outcomes_by_horizon


def _frbus_directional_benchmark_responses() -> tuple[
    dict[tuple[int, str], dict[str, float]],
    str,
]:
    baseline_sim, shock_sim, start, _package_sha, _data_sha, blocker = (
        _frbus_solve_review_scenario([1.0])
    )
    if blocker:
        return {}, blocker
    responses: dict[tuple[int, str], dict[str, float]] = {}
    for horizon, outcome_id, variable_name in (
        (4, "real_gdp", "xgdp"),
        (8, "real_gdp", "xgdp"),
        (12, "real_gdp", "xgdp"),
        (4, "real_pce", "ec"),
        (8, "real_pce", "ec"),
        (12, "real_pce", "ec"),
        (4, "real_private_fixed_investment", "ebfi"),
        (8, "real_private_fixed_investment", "ebfi"),
        (12, "real_private_fixed_investment", "ebfi"),
    ):
        baseline_level = float(baseline_sim.loc[start + horizon, variable_name])
        shock_level = float(shock_sim.loc[start + horizon, variable_name])
        delta_level = shock_level - baseline_level
        pct_delta = (
            (100.0 * delta_level / baseline_level)
            if baseline_level != 0.0
            else math.nan
        )
        responses[(horizon, outcome_id)] = {
            "baseline_level": baseline_level,
            "shock_level": shock_level,
            "delta_level": delta_level,
            "pct_delta_from_baseline": pct_delta,
        }
    return responses, ""


def _frbus_solve_review_scenario(
    shock_path_pp: Sequence[float],
) -> tuple[object | None, object | None, object | None, str, str, str]:
    if not FRBUS_PYFRBUS_ZIP_PATH.exists():
        return (
            None,
            None,
            None,
            "",
            "",
            f"Missing FRB/US Python package zip at {FRBUS_PYFRBUS_ZIP_PATH}.",
        )
    if not FRBUS_DATA_ONLY_PACKAGE_ZIP_PATH.exists():
        return (
            None,
            None,
            None,
            "",
            "",
            f"Missing FRB/US data package zip at {FRBUS_DATA_ONLY_PACKAGE_ZIP_PATH}.",
        )

    try:
        with tempfile.TemporaryDirectory(prefix="ratewall-frbus-benchmark-") as temp_dir:
            temp_path = Path(temp_dir)
            with zipfile.ZipFile(FRBUS_PYFRBUS_ZIP_PATH) as archive:
                archive.extractall(temp_path)
            with zipfile.ZipFile(FRBUS_DATA_ONLY_PACKAGE_ZIP_PATH) as archive:
                archive.extractall(temp_path)

            package_root = temp_path / "pyfrbus"
            if not (package_root / "pyfrbus" / "frbus.py").exists():
                return (
                    None,
                    None,
                    None,
                    "",
                    "",
                    "FRB/US runtime imports failed: extracted pyfrbus package "
                    "does not contain pyfrbus/frbus.py.",
                )
            import_root = str(package_root)
            previous_modules = {
                name: module
                for name, module in sys.modules.items()
                if name == "pyfrbus" or name.startswith("pyfrbus.")
            }
            for name in list(previous_modules):
                sys.modules.pop(name, None)
            sys.path.insert(0, import_root)
            try:
                import pandas
                from pyfrbus.frbus import Frbus
                from pyfrbus.load_data import load_data

                data = load_data(str(temp_path / "data_only_package" / "LONGBASE.TXT"))
                frbus = Frbus(str(package_root / "models" / "model.xml"))
                start = pandas.Period("2040Q1")
                end = start + 23
                data.loc[start:end, "dfpdbt"] = 0
                data.loc[start:end, "dfpsrp"] = 1

                baseline = frbus.init_trac(start, end, data)
                baseline_sim = frbus.solve(start, end, baseline)
                shock = frbus.init_trac(start, end, data)
                for offset, shock_pp in enumerate(shock_path_pp):
                    if shock_pp == 0:
                        continue
                    shock.loc[start + offset, "rffintay_aerr"] += shock_pp
                shock_sim = frbus.solve(start, end, shock)
            finally:
                if import_root in sys.path:
                    sys.path.remove(import_root)
                for name in [
                    name
                    for name in sys.modules
                    if name == "pyfrbus" or name.startswith("pyfrbus.")
                ]:
                    sys.modules.pop(name, None)
                sys.modules.update(previous_modules)
    except Exception as exc:  # pragma: no cover - solver/runtime exceptions are environment-specific
        return None, None, None, "", "", f"FRB/US benchmark rerun failed: {exc}"
    return (
        baseline_sim,
        shock_sim,
        start,
        _file_sha256(FRBUS_PYFRBUS_ZIP_PATH),
        _file_sha256(FRBUS_DATA_ONLY_PACKAGE_ZIP_PATH),
        "",
    )


def _frbus_path_exposure_bps_year(shock_path_pp: Sequence[float]) -> float:
    return 100.0 * sum(shock_path_pp) / 4.0


def _frbus_benchmark_crosscheck_row(
    outcome: FrbusBenchmarkCrosscheckOutcome,
) -> dict[str, str]:
    row = {field: "" for field in FRBUS_BENCHMARK_CROSSCHECK_FIELDS}
    row.update(
        {
            "horizon_q": str(outcome.horizon_q),
            "benchmark_outcome_id": outcome.benchmark_outcome_id,
            "benchmark_outcome_variable": outcome.benchmark_outcome_variable,
            "benchmark_outcome_label": outcome.benchmark_outcome_label,
            "frbus_scenario_handle": "official_100bp_rffintay_add_factor_demo_review",
            "frbus_shock_definition": "rffintay_aerr_plus_1_at_2040Q1_directional_context_only",
            "frbus_baseline_level": _format_float(outcome.baseline_level),
            "frbus_shock_level": _format_float(outcome.shock_level),
            "frbus_delta_level": _format_float(outcome.delta_level),
            "frbus_pct_delta_from_baseline": _format_float(
                outcome.pct_delta_from_baseline
            ),
            "frbus_output_unit": "frbus_percent_delta_from_baseline_directional_context_only",
            "empirical_instrument_variant": outcome.empirical_instrument_variant,
            "empirical_iv_d_y_candidate": _format_float(
                outcome.empirical_iv_d_y_candidate
            ),
            "empirical_iv_ci_low_d_y": _format_float(outcome.empirical_iv_ci_low_d_y),
            "empirical_iv_ci_high_d_y": _format_float(outcome.empirical_iv_ci_high_d_y),
            "benchmark_crosscheck_status": outcome.benchmark_crosscheck_status,
            "exact_blocker": outcome.exact_blocker,
            "next_backend_action": outcome.next_backend_action,
            "allowed_use": "frbus_directional_benchmark_crosscheck_review_only",
            "blocked_use": (
                "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "frbus_directional_benchmark_crosscheck_not_denominator",
            **_disabled_switches(),
        }
    )
    return row


def _frbus_100bp_year_fspdp_proxy_benchmark_rows(
    *,
    weak_iv_safe_outcome: WeakIvSafeInferenceOutcome,
) -> tuple[
    list[dict[str, str]],
    dict[int, Frbus100BpYearBenchmarkOutcome],
]:
    shock_path_pp = [1.0, 1.0, 1.0, 1.0]
    baseline_sim, shock_sim, start, model_sha, data_sha, blocker = (
        _frbus_solve_review_scenario(shock_path_pp)
    )
    exposure_bps_year = _frbus_path_exposure_bps_year(shock_path_pp)
    scenario_id = "official_100bp_year_rffintay_add_factor_review"
    path_normalization_id = "rffintay_aerr_plus_1pp_for_4_quarters_exact_100bp_year"
    empirical_low = weak_iv_safe_outcome.weak_iv_safe_ci_low_d_y
    empirical_high = weak_iv_safe_outcome.weak_iv_safe_ci_high_d_y
    mappings = [
        (
            "ecnia_plus_ebfi_plus_eh_fspdp_proxy",
            "NIPA PCE plus private fixed investment proxy",
            [("ecnia", "ECNIA", "nipa_pce"), ("ebfi", "EBFI", "private_fixed_investment"), ("eh", "EH", "residential_investment")],
        ),
        (
            "ec_plus_ebfi_plus_eh_fspdp_proxy",
            "FRB/US consumer spending plus private fixed investment proxy",
            [("ec", "EC", "frbus_consumer_spending"), ("ebfi", "EBFI", "private_fixed_investment"), ("eh", "EH", "residential_investment")],
        ),
    ]
    rows: list[dict[str, str]] = []
    aggregate_outcomes_by_mapping_horizon: dict[tuple[str, int], Frbus100BpYearBenchmarkOutcome] = {}
    if blocker:
        for horizon in STATUS_HORIZONS:
            outcome = Frbus100BpYearBenchmarkOutcome(
                horizon_q=horizon,
                component_mapping_id=mappings[0][0],
                component_mapping_label=mappings[0][1],
                component_id="fspdp_proxy",
                component_label="Aggregate FSPDP proxy",
                model_variable="ECNIA;EBFI;EH;XGDP",
                component_role="aggregate_fspdp_proxy",
                model_package_sha256=model_sha,
                data_package_sha256=data_sha,
                scenario_id=scenario_id,
                path_normalization_id=path_normalization_id,
                shock_path_quarters=len(shock_path_pp),
                shock_path_pp=1.0,
                exposure_bps_year=exposure_bps_year,
                baseline_level=None,
                shock_level=None,
                delta_level=None,
                log_response_pct=None,
                baseline_share_of_xgdp=None,
                component_contribution_pp_gdp=None,
                aggregate_proxy_contribution_pp_gdp=None,
                model_d_y_per_100bp_year=None,
                empirical_weak_iv_safe_ci_low_d_y=empirical_low,
                empirical_weak_iv_safe_ci_high_d_y=empirical_high,
                benchmark_support_status="blocked_frbus_100bp_year_component_benchmark_missing",
                exact_blocker=blocker,
                next_backend_action="repair_frbus_100bp_year_review_runner_before_benchmark_use",
            )
            rows.append(_frbus_100bp_year_fspdp_proxy_benchmark_row(outcome))
        return rows, {}

    available_variables = {str(column).lower() for column in baseline_sim.columns}
    preferred_mapping_id = (
        "ecnia_plus_ebfi_plus_eh_fspdp_proxy"
        if {"ecnia", "ebfi", "eh", "xgdp"} <= available_variables
        else "ec_plus_ebfi_plus_eh_fspdp_proxy"
    )
    for mapping_id, mapping_label, components in mappings:
        required = {component_id for component_id, _label, _role in components} | {"xgdp"}
        mapping_complete = required <= available_variables
        for horizon in STATUS_HORIZONS:
            base_xgdp = (
                float(baseline_sim.loc[start + horizon, "xgdp"])
                if "xgdp" in available_variables
                else None
            )
            aggregate_contribution = 0.0
            aggregate_ready = mapping_complete and base_xgdp not in {None, 0.0}
            for component_id, component_variable, component_role in components:
                if not mapping_complete:
                    outcome = Frbus100BpYearBenchmarkOutcome(
                        horizon_q=horizon,
                        component_mapping_id=mapping_id,
                        component_mapping_label=mapping_label,
                        component_id=component_id,
                        component_label=component_variable,
                        model_variable=component_variable,
                        component_role=component_role,
                        model_package_sha256=model_sha,
                        data_package_sha256=data_sha,
                        scenario_id=scenario_id,
                        path_normalization_id=path_normalization_id,
                        shock_path_quarters=len(shock_path_pp),
                        shock_path_pp=1.0,
                        exposure_bps_year=exposure_bps_year,
                        baseline_level=None,
                        shock_level=None,
                        delta_level=None,
                        log_response_pct=None,
                        baseline_share_of_xgdp=None,
                        component_contribution_pp_gdp=None,
                        aggregate_proxy_contribution_pp_gdp=None,
                        model_d_y_per_100bp_year=None,
                        empirical_weak_iv_safe_ci_low_d_y=empirical_low,
                        empirical_weak_iv_safe_ci_high_d_y=empirical_high,
                        benchmark_support_status="blocked_frbus_component_mapping_variable_missing",
                        exact_blocker=(
                            "FRB/US component-mapped FSPDP proxy is missing one or more "
                            f"required variables for {mapping_id}."
                        ),
                        next_backend_action="fallback_to_available_fspdp_proxy_mapping_or_recheck_frbus_variable_inventory",
                    )
                    rows.append(_frbus_100bp_year_fspdp_proxy_benchmark_row(outcome))
                    continue
                base_level = float(baseline_sim.loc[start + horizon, component_id])
                shock_level = float(shock_sim.loc[start + horizon, component_id])
                delta_level = shock_level - base_level
                log_response_pct = (
                    100.0 * math.log(shock_level / base_level)
                    if base_level > 0.0 and shock_level > 0.0
                    else None
                )
                share = (
                    base_level / base_xgdp
                    if base_xgdp not in {None, 0.0}
                    else None
                )
                contribution = (
                    100.0 * share * math.log(shock_level / base_level)
                    if share is not None and base_level > 0.0 and shock_level > 0.0
                    else None
                )
                if contribution is None:
                    aggregate_ready = False
                else:
                    aggregate_contribution += contribution
                outcome = Frbus100BpYearBenchmarkOutcome(
                    horizon_q=horizon,
                    component_mapping_id=mapping_id,
                    component_mapping_label=mapping_label,
                    component_id=component_id,
                    component_label=component_variable,
                    model_variable=component_variable,
                    component_role=component_role,
                    model_package_sha256=model_sha,
                    data_package_sha256=data_sha,
                    scenario_id=scenario_id,
                    path_normalization_id=path_normalization_id,
                    shock_path_quarters=len(shock_path_pp),
                    shock_path_pp=1.0,
                    exposure_bps_year=exposure_bps_year,
                    baseline_level=base_level,
                    shock_level=shock_level,
                    delta_level=delta_level,
                    log_response_pct=log_response_pct,
                    baseline_share_of_xgdp=share,
                    component_contribution_pp_gdp=contribution,
                    aggregate_proxy_contribution_pp_gdp=None,
                    model_d_y_per_100bp_year=None,
                    empirical_weak_iv_safe_ci_low_d_y=empirical_low,
                    empirical_weak_iv_safe_ci_high_d_y=empirical_high,
                    benchmark_support_status="pass_frbus_component_response_captured_review_only",
                    exact_blocker=(
                        "FRB/US component response is benchmark-only context and not a "
                        "denominator calibration."
                    ),
                    next_backend_action="use_component_response_inside_model_fspdp_proxy_benchmark_only",
                )
                rows.append(_frbus_100bp_year_fspdp_proxy_benchmark_row(outcome))
            aggregate_outcome = _frbus_100bp_year_aggregate_outcome(
                horizon_q=horizon,
                mapping_id=mapping_id,
                mapping_label=mapping_label,
                model_sha=model_sha,
                data_sha=data_sha,
                scenario_id=scenario_id,
                path_normalization_id=path_normalization_id,
                shock_path_pp=shock_path_pp,
                exposure_bps_year=exposure_bps_year,
                empirical_low=empirical_low,
                empirical_high=empirical_high,
                mapping_complete=mapping_complete,
                aggregate_ready=aggregate_ready,
                aggregate_contribution=aggregate_contribution if aggregate_ready else None,
            )
            rows.append(_frbus_100bp_year_fspdp_proxy_benchmark_row(aggregate_outcome))
            aggregate_outcomes_by_mapping_horizon[(mapping_id, horizon)] = aggregate_outcome
    preferred_outcomes = {
        horizon: aggregate_outcomes_by_mapping_horizon[(preferred_mapping_id, horizon)]
        for horizon in STATUS_HORIZONS
        if (preferred_mapping_id, horizon) in aggregate_outcomes_by_mapping_horizon
    }
    return rows, preferred_outcomes


def _frbus_100bp_year_aggregate_outcome(
    *,
    horizon_q: int,
    mapping_id: str,
    mapping_label: str,
    model_sha: str,
    data_sha: str,
    scenario_id: str,
    path_normalization_id: str,
    shock_path_pp: Sequence[float],
    exposure_bps_year: float,
    empirical_low: float | None,
    empirical_high: float | None,
    mapping_complete: bool,
    aggregate_ready: bool,
    aggregate_contribution: float | None,
) -> Frbus100BpYearBenchmarkOutcome:
    if abs(exposure_bps_year - 100.0) > 1e-9:
        status = "blocked_frbus_100bp_year_path_not_normalized"
        blocker = "FRB/US benchmark shock path does not normalize to exactly 100 bp-year."
        next_action = "repair_frbus_benchmark_path_normalization_before_review"
        model_d_y = None
    elif not mapping_complete or not aggregate_ready or aggregate_contribution is None:
        status = "blocked_frbus_component_mapping_variable_missing"
        blocker = (
            "FRB/US component-mapped FSPDP proxy is incomplete because one or more "
            "required levels or GDP-share inputs are unavailable."
        )
        next_action = "fallback_to_available_fspdp_proxy_mapping_or_recheck_frbus_variable_inventory"
        model_d_y = None
    else:
        model_d_y = -aggregate_contribution * (100.0 / exposure_bps_year)
        if model_d_y <= 0:
            status = "blocked_frbus_model_fspdp_proxy_wrong_sign"
            blocker = (
                "FRB/US 100bp-year component-mapped FSPDP proxy is not contractionary "
                "at this horizon, so it does not support the bounded h8 drag sign."
            )
            next_action = "revisit_frbus_component_mapping_or_hold_benchmark_support_review_only"
        elif (
            horizon_q == 8
            and empirical_low is not None
            and empirical_high is not None
            and empirical_low <= model_d_y <= empirical_high
        ):
            status = "pass_model_fspdp_proxy_scale_inside_empirical_ar_interval_review_only"
            blocker = (
                "FRB/US 100bp-year component-mapped FSPDP proxy is benchmark-only context; "
                "its h8 scale falls inside the empirical weak-IV-safe interval."
            )
            next_action = "use_as_review_only_structural_benchmark_context"
        elif horizon_q == 8 and empirical_low is not None and empirical_high is not None:
            status = "review_weak_model_fspdp_proxy_scale_outside_empirical_ar_interval"
            blocker = (
                "FRB/US 100bp-year component-mapped FSPDP proxy has the right sign but "
                "its h8 scale falls outside the empirical weak-IV-safe interval."
            )
            next_action = "keep_benchmark_review_only_and_compare_shape_not_level"
        else:
            status = "pass_model_fspdp_proxy_horizon_shape_review_only"
            blocker = (
                "FRB/US 100bp-year component-mapped FSPDP proxy is benchmark-only "
                "context for horizon shape and sign."
            )
            next_action = "use_as_review_only_structural_benchmark_context"
    return Frbus100BpYearBenchmarkOutcome(
        horizon_q=horizon_q,
        component_mapping_id=mapping_id,
        component_mapping_label=mapping_label,
        component_id="fspdp_proxy",
        component_label="Aggregate FSPDP proxy",
        model_variable="XGDP;consumption;private_fixed_investment",
        component_role="aggregate_fspdp_proxy",
        model_package_sha256=model_sha,
        data_package_sha256=data_sha,
        scenario_id=scenario_id,
        path_normalization_id=path_normalization_id,
        shock_path_quarters=len(shock_path_pp),
        shock_path_pp=1.0,
        exposure_bps_year=exposure_bps_year,
        baseline_level=None,
        shock_level=None,
        delta_level=None,
        log_response_pct=None,
        baseline_share_of_xgdp=None,
        component_contribution_pp_gdp=None,
        aggregate_proxy_contribution_pp_gdp=aggregate_contribution,
        model_d_y_per_100bp_year=model_d_y,
        empirical_weak_iv_safe_ci_low_d_y=empirical_low,
        empirical_weak_iv_safe_ci_high_d_y=empirical_high,
        benchmark_support_status=status,
        exact_blocker=blocker,
        next_backend_action=next_action,
    )


def _frbus_100bp_year_fspdp_proxy_benchmark_row(
    outcome: Frbus100BpYearBenchmarkOutcome,
) -> dict[str, str]:
    row = {field: "" for field in FRBUS_100BP_YEAR_FSPDP_PROXY_BENCHMARK_FIELDS}
    row.update(
        {
            "model_package_sha256": outcome.model_package_sha256,
            "data_package_sha256": outcome.data_package_sha256,
            "scenario_id": outcome.scenario_id,
            "path_normalization_id": outcome.path_normalization_id,
            "component_mapping_id": outcome.component_mapping_id,
            "component_mapping_label": outcome.component_mapping_label,
            "horizon_q": str(outcome.horizon_q),
            "component_id": outcome.component_id,
            "component_label": outcome.component_label,
            "model_variable": outcome.model_variable,
            "component_role": outcome.component_role,
            "shock_path_quarters": str(outcome.shock_path_quarters),
            "shock_path_pp": _format_float(outcome.shock_path_pp),
            "exposure_bps_year": _format_float(outcome.exposure_bps_year),
            "baseline_level": _format_float(outcome.baseline_level),
            "shock_level": _format_float(outcome.shock_level),
            "delta_level": _format_float(outcome.delta_level),
            "log_response_pct": _format_float(outcome.log_response_pct),
            "baseline_share_of_xgdp": _format_float(outcome.baseline_share_of_xgdp),
            "component_contribution_pp_gdp": _format_float(
                outcome.component_contribution_pp_gdp
            ),
            "aggregate_proxy_contribution_pp_gdp": _format_float(
                outcome.aggregate_proxy_contribution_pp_gdp
            ),
            "model_d_y_per_100bp_year": _format_float(outcome.model_d_y_per_100bp_year),
            "empirical_weak_iv_safe_ci_low_d_y": _format_float(
                outcome.empirical_weak_iv_safe_ci_low_d_y
            ),
            "empirical_weak_iv_safe_ci_high_d_y": _format_float(
                outcome.empirical_weak_iv_safe_ci_high_d_y
            ),
            "benchmark_support_status": outcome.benchmark_support_status,
            "exact_blocker": outcome.exact_blocker,
            "next_backend_action": outcome.next_backend_action,
            "allowed_use": "frbus_100bp_year_fspdp_proxy_benchmark_review_only",
            "blocked_use": (
                "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "frbus_100bp_year_fspdp_proxy_benchmark_not_denominator",
            **_disabled_switches(),
        }
    )
    return row


def _weak_iv_safe_inference_rows(
    *,
    primary_result: DesignMatrixResult,
    identification_outcome: IdentificationCheckOutcome | None,
    quarter_records: dict[str, InstrumentQuarterRecord],
    horizon_q: int,
) -> tuple[list[dict[str, str]], WeakIvSafeInferenceOutcome]:
    bandwidth = max(4, horizon_q + 1)
    exemplar = next(iter(quarter_records.values()), None)
    if (
        identification_outcome is None
        or exemplar is None
        or identification_outcome.iv_estimate is None
        or identification_outcome.first_stage is None
        or identification_outcome.reduced_form is None
    ):
        outcome = WeakIvSafeInferenceOutcome(
            horizon_q=horizon_q,
            instrument_variant=(
                identification_outcome.instrument_variant
                if identification_outcome is not None
                else ""
            ),
            shock_source_id=(
                identification_outcome.shock_source_id
                if identification_outcome is not None
                else ""
            ),
            instrument_series_id=(
                identification_outcome.instrument_series_id
                if identification_outcome is not None
                else ""
            ),
            weak_iv_safe_method="anderson_rubin_hac_grid_inversion",
            n_obs=0,
            sample_start_q="",
            sample_end_q="",
            bandwidth=bandwidth,
            beta_grid_min=None,
            beta_grid_max=None,
            beta_grid_step=None,
            accepted_grid_point_count=0,
            acceptance_region_span_count=0,
            ar_coef_z_at_beta_zero=None,
            ar_se_hac_at_beta_zero=None,
            ar_t_hac_at_beta_zero=None,
            reject_beta_zero_hac=None,
            weak_iv_safe_ci_low_beta=None,
            weak_iv_safe_ci_high_beta=None,
            weak_iv_safe_ci_low_d_y=None,
            weak_iv_safe_ci_high_d_y=None,
            weak_iv_safe_inference_status="blocked_weak_iv_safe_input_missing",
            exact_blocker=(
                "Weak-IV-safe inference cannot run because the long-sample proxy-IV "
                "identification row is missing or incomplete."
            ),
            next_backend_action=(
                "restore_long_sample_proxy_iv_identification_row_before_weak_iv_safe_review"
            ),
        )
        return [_weak_iv_safe_inference_row(outcome)], outcome

    matched_indexes = [
        index
        for index, quarter in enumerate(primary_result.quarters)
        if quarter in quarter_records
    ]
    if len(matched_indexes) < MIN_IV_SAMPLE_NOBS:
        outcome = WeakIvSafeInferenceOutcome(
            horizon_q=horizon_q,
            instrument_variant=identification_outcome.instrument_variant,
            shock_source_id=identification_outcome.shock_source_id,
            instrument_series_id=identification_outcome.instrument_series_id,
            weak_iv_safe_method="anderson_rubin_hac_grid_inversion",
            n_obs=len(matched_indexes),
            sample_start_q="",
            sample_end_q="",
            bandwidth=bandwidth,
            beta_grid_min=None,
            beta_grid_max=None,
            beta_grid_step=None,
            accepted_grid_point_count=0,
            acceptance_region_span_count=0,
            ar_coef_z_at_beta_zero=identification_outcome.reduced_form.beta,
            ar_se_hac_at_beta_zero=identification_outcome.reduced_form.se,
            ar_t_hac_at_beta_zero=_safe_t_stat(identification_outcome.reduced_form),
            reject_beta_zero_hac=None,
            weak_iv_safe_ci_low_beta=None,
            weak_iv_safe_ci_high_beta=None,
            weak_iv_safe_ci_low_d_y=None,
            weak_iv_safe_ci_high_d_y=None,
            weak_iv_safe_inference_status="blocked_weak_iv_safe_overlap_too_short",
            exact_blocker=(
                "Weak-IV-safe inference requires the same bounded overlap floor as "
                "the proxy-IV row, and the matched quarterly overlap is too short."
            ),
            next_backend_action=(
                "use_longer_overlap_proxy_instrument_before_weak_iv_safe_review"
            ),
        )
        return [_weak_iv_safe_inference_row(outcome)], outcome

    matched_quarters = [primary_result.quarters[index] for index in matched_indexes]
    y_values = [primary_result.y[index] for index in matched_indexes]
    x_rows = [primary_result.x_rows[index] for index in matched_indexes]
    z_values = [
        quarter_records[primary_result.quarters[index]].quarterly_instrument_value
        for index in matched_indexes
    ]
    ar_outcome = _anderson_rubin_hac_outcome(
        y_values=y_values,
        x_rows=x_rows,
        z_values=z_values,
        bandwidth=identification_outcome.bandwidth,
        horizon_q=horizon_q,
        instrument_variant=identification_outcome.instrument_variant,
        shock_source_id=identification_outcome.shock_source_id,
        instrument_series_id=identification_outcome.instrument_series_id,
        sample_start_q=matched_quarters[0],
        sample_end_q=matched_quarters[-1],
        reduced_form=identification_outcome.reduced_form,
        iv_estimate=identification_outcome.iv_estimate,
    )
    return [_weak_iv_safe_inference_row(ar_outcome)], ar_outcome


def _anderson_rubin_hac_outcome(
    *,
    y_values: Sequence[float],
    x_rows: Sequence[Sequence[float]],
    z_values: Sequence[float],
    bandwidth: int,
    horizon_q: int,
    instrument_variant: str,
    shock_source_id: str,
    instrument_series_id: str,
    sample_start_q: str,
    sample_end_q: str,
    reduced_form: HacEstimate,
    iv_estimate: HacEstimate,
) -> WeakIvSafeInferenceOutcome:
    horizon_label = f"h{horizon_q}"
    spread = max(
        WEAK_IV_SAFE_MIN_SPREAD,
        abs(iv_estimate.beta) * 2.0,
        abs(iv_estimate.se) * 10.0,
    )
    accepted_betas: list[float] = []
    spans: list[tuple[int, int]] = []
    grid_min: float | None = None
    grid_max: float | None = None
    last_grid: list[float] = []
    for expansion in range(WEAK_IV_SAFE_MAX_GRID_EXPANSIONS):
        grid_min = min(iv_estimate.beta - spread, -2.0)
        grid_max = max(iv_estimate.beta + spread, 2.0)
        grid = _float_grid(grid_min, grid_max, WEAK_IV_SAFE_GRID_STEP)
        accepted_flags = [
            _anderson_rubin_accepts_beta(
                y_values=y_values,
                x_rows=x_rows,
                z_values=z_values,
                bandwidth=bandwidth,
                beta_0=beta_0,
            )
            for beta_0 in grid
        ]
        last_grid = grid
        accepted_betas = [
            beta_0 for beta_0, accepted in zip(grid, accepted_flags) if accepted
        ]
        spans = _accepted_index_spans(accepted_flags)
        if spans and spans[0][0] > 0 and spans[-1][1] < len(grid) - 1:
            break
        spread *= 2.0

    ar_t_zero = _safe_t_stat(reduced_form)
    reject_beta_zero = (
        ar_t_zero is not None and abs(ar_t_zero) > WEAK_IV_SAFE_Z_CRITICAL_VALUE
    )

    if not accepted_betas or grid_min is None or grid_max is None:
        status = "blocked_anderson_rubin_hac_no_acceptance_region"
        exact_blocker = (
            "Anderson-Rubin HAC grid inversion returned no accepted beta region, so "
            "the weak-IV-safe gate cannot support admission."
        )
        next_action = (
            f"inspect_{horizon_label}_proxy_iv_design_and_grid_before_promotion"
        )
        ci_low_beta = None
        ci_high_beta = None
    elif len(spans) != 1:
        status = "blocked_anderson_rubin_hac_acceptance_region_nonconvex"
        exact_blocker = (
            "Anderson-Rubin HAC inversion produced a nonconvex acceptance region, so "
            "the bounded weak-IV-safe gate stays blocked."
        )
        next_action = f"do_not_promote_and_revisit_{horizon_label}_proxy_iv_design"
        ci_low_beta = min(accepted_betas)
        ci_high_beta = max(accepted_betas)
    elif spans[0][0] == 0 or spans[0][1] == len(last_grid) - 1:
        status = "blocked_anderson_rubin_hac_interval_unbounded_or_grid_truncated"
        exact_blocker = (
            "Anderson-Rubin HAC inversion still hits the grid boundary, so the "
            "weak-IV-safe interval is treated as unbounded or truncated."
        )
        next_action = f"keep_{horizon_label}_review_only_and_revisit_proxy_iv_scope"
        ci_low_beta = min(accepted_betas)
        ci_high_beta = max(accepted_betas)
    else:
        ci_low_beta = min(accepted_betas)
        ci_high_beta = max(accepted_betas)
        if ci_high_beta < 0.0:
            status = "pass_anderson_rubin_hac_interval_excludes_zero_d_y"
            exact_blocker = ""
            next_action = (
                f"allow_bounded_noncanonical_{horizon_label}_admission_but_keep_canonical_rw_y_blocked"
            )
        else:
            status = "blocked_anderson_rubin_hac_interval_includes_zero_d_y"
            exact_blocker = (
                "Anderson-Rubin HAC weak-IV-safe interval still includes zero D_Y, so "
                f"the {horizon_label} denominator remains review-only."
            )
            next_action = (
                f"keep_{horizon_label}_review_only_and_consider_stricter_iv_design"
            )

    ci_low_d_y = -ci_high_beta if ci_high_beta is not None else None
    ci_high_d_y = -ci_low_beta if ci_low_beta is not None else None
    return WeakIvSafeInferenceOutcome(
        horizon_q=horizon_q,
        instrument_variant=instrument_variant,
        shock_source_id=shock_source_id,
        instrument_series_id=instrument_series_id,
        weak_iv_safe_method="anderson_rubin_hac_grid_inversion",
        n_obs=len(y_values),
        sample_start_q=sample_start_q,
        sample_end_q=sample_end_q,
        bandwidth=bandwidth,
        beta_grid_min=grid_min,
        beta_grid_max=grid_max,
        beta_grid_step=WEAK_IV_SAFE_GRID_STEP,
        accepted_grid_point_count=len(accepted_betas),
        acceptance_region_span_count=len(spans),
        ar_coef_z_at_beta_zero=reduced_form.beta,
        ar_se_hac_at_beta_zero=reduced_form.se,
        ar_t_hac_at_beta_zero=ar_t_zero,
        reject_beta_zero_hac=reject_beta_zero,
        weak_iv_safe_ci_low_beta=ci_low_beta,
        weak_iv_safe_ci_high_beta=ci_high_beta,
        weak_iv_safe_ci_low_d_y=ci_low_d_y,
        weak_iv_safe_ci_high_d_y=ci_high_d_y,
        weak_iv_safe_inference_status=status,
        exact_blocker=exact_blocker,
        next_backend_action=next_action,
    )


def _anderson_rubin_accepts_beta(
    *,
    y_values: Sequence[float],
    x_rows: Sequence[Sequence[float]],
    z_values: Sequence[float],
    bandwidth: int,
    beta_0: float,
) -> bool:
    adjusted_y = [
        y_value - beta_0 * x_row[1] for y_value, x_row in zip(y_values, x_rows)
    ]
    instrument_rows = [
        [1.0, z_value, *x_row[2:]] for z_value, x_row in zip(z_values, x_rows)
    ]
    try:
        estimate = _ols_hac(adjusted_y, instrument_rows, bandwidth=bandwidth)
    except Exception:
        return False
    t_stat = _safe_t_stat(estimate)
    return t_stat is not None and abs(t_stat) <= WEAK_IV_SAFE_Z_CRITICAL_VALUE


def _accepted_index_spans(accepted_flags: Sequence[bool]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for index, accepted in enumerate(accepted_flags):
        if accepted and start is None:
            start = index
        elif not accepted and start is not None:
            spans.append((start, index - 1))
            start = None
    if start is not None:
        spans.append((start, len(accepted_flags) - 1))
    return spans


def _float_grid(start: float, stop: float, step: float) -> list[float]:
    points: list[float] = []
    current = start
    while current <= stop + (step * 0.5):
        points.append(round(current, 12))
        current += step
    return points


def _weak_iv_safe_inference_row(
    outcome: WeakIvSafeInferenceOutcome,
) -> dict[str, str]:
    row = {field: "" for field in WEAK_IV_SAFE_INFERENCE_FIELDS}
    row.update(
        {
            "horizon_q": str(outcome.horizon_q),
            "primary_denominator_horizon": _bool_text(outcome.horizon_q == 8),
            "instrument_variant": outcome.instrument_variant,
            "shock_source_id": outcome.shock_source_id,
            "instrument_series_id": outcome.instrument_series_id,
            "sample_window_id": SAMPLE_WINDOW_ID,
            "control_spec_id": CONTROL_SPEC_ID,
            "weak_iv_safe_method": outcome.weak_iv_safe_method,
            "n_obs": str(outcome.n_obs),
            "sample_start_q": outcome.sample_start_q,
            "sample_end_q": outcome.sample_end_q,
            "nw_bandwidth": str(outcome.bandwidth),
            "beta_grid_min": _format_float(outcome.beta_grid_min),
            "beta_grid_max": _format_float(outcome.beta_grid_max),
            "beta_grid_step": _format_float(outcome.beta_grid_step),
            "accepted_grid_point_count": str(outcome.accepted_grid_point_count),
            "acceptance_region_span_count": str(outcome.acceptance_region_span_count),
            "ar_coef_z_at_beta_zero": _format_float(outcome.ar_coef_z_at_beta_zero),
            "ar_se_hac_at_beta_zero": _format_float(outcome.ar_se_hac_at_beta_zero),
            "ar_t_hac_at_beta_zero": _format_float(outcome.ar_t_hac_at_beta_zero),
            "reject_beta_zero_hac": (
                _bool_text(outcome.reject_beta_zero_hac)
                if outcome.reject_beta_zero_hac is not None
                else ""
            ),
            "weak_iv_safe_ci_low_beta": _format_float(outcome.weak_iv_safe_ci_low_beta),
            "weak_iv_safe_ci_high_beta": _format_float(
                outcome.weak_iv_safe_ci_high_beta
            ),
            "weak_iv_safe_ci_low_d_y": _format_float(outcome.weak_iv_safe_ci_low_d_y),
            "weak_iv_safe_ci_high_d_y": _format_float(
                outcome.weak_iv_safe_ci_high_d_y
            ),
            "weak_iv_safe_inference_status": outcome.weak_iv_safe_inference_status,
            "exact_blocker": outcome.exact_blocker,
            "next_backend_action": outcome.next_backend_action,
            "allowed_use": "weak_iv_safe_inference_review_only",
            "blocked_use": (
                "main_ratio;Evidence_Mode;denominator_prior;pricing;"
                "holder_allocation;raw_rate_shock;reset_calendar;"
                "tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "weak_iv_safe_inference_not_canonical_denominator",
            **_disabled_switches(),
        }
    )
    return row


def _promotion_rule_evaluation_rows(
    *,
    primary_result: DesignMatrixResult,
    primary_estimate: HacEstimate | None,
    primary_robustness: RobustnessOutcome,
    replication_summary: ReplicationSummary,
    robustness_status: str,
    identification_outcomes: dict[str, IdentificationCheckOutcome],
    frbus_benchmark_crosscheck_outcomes: dict[int, list[FrbusBenchmarkCrosscheckOutcome]],
    frbus_100bp_year_benchmark_outcomes: dict[int, Frbus100BpYearBenchmarkOutcome],
    weak_iv_safe_outcome: WeakIvSafeInferenceOutcome,
) -> tuple[list[dict[str, str]], PromotionRuleEvaluationOutcome]:
    me_outcome = identification_outcomes.get("sf_fed_usmpd_me_scalar_quarterly_sum")
    orth_outcome = identification_outcomes.get(
        "sf_fed_chart_orthogonalized_surprise_quarterly_sum"
    )
    h8_crosschecks = frbus_benchmark_crosscheck_outcomes.get(8, [])
    h8_frbus_100bp_year = frbus_100bp_year_benchmark_outcomes.get(8)

    if primary_estimate is None:
        primary_gate_status = "blocked_primary_controlled_estimate_missing"
    elif primary_result.n_obs < MIN_PRIMARY_NOBS:
        primary_gate_status = "blocked_primary_controlled_nobs_below_floor"
    elif -primary_estimate.beta <= 0:
        primary_gate_status = "blocked_primary_controlled_wrong_sign"
    else:
        primary_gate_status = "pass_primary_controlled_sign_and_nobs"

    if (
        primary_robustness.bootstrap is None
        or primary_robustness.bootstrap.status != "pass_bootstrap_completed"
        or primary_robustness.bootstrap.sign_probability is None
    ):
        bootstrap_gate_status = "blocked_primary_bootstrap_missing"
    elif (
        primary_robustness.bootstrap.sign_probability
        < BOOTSTRAP_REVIEW_SIGN_PROB_THRESHOLD
    ):
        bootstrap_gate_status = (
            "blocked_bootstrap_sign_probability_below_review_threshold"
        )
    else:
        bootstrap_gate_status = "pass_bootstrap_review_support_threshold"

    replication_gate_status = (
        "pass_replication_gate"
        if replication_summary.replication_status
        == "pass_independent_replication_within_tolerance"
        else "blocked_replication_gate"
    )
    robustness_gate_status = (
        "pass_robustness_gate"
        if robustness_status == "pass_narrow_robustness_preserved"
        else "blocked_robustness_gate"
    )

    me_first_stage_t = _safe_t_stat(me_outcome.first_stage) if me_outcome is not None else None
    me_first_stage_f = (
        me_first_stage_t * me_first_stage_t if me_first_stage_t is not None else None
    )
    if (
        me_outcome is None
        or me_outcome.iv_estimate is None
        or not me_outcome.identification_check_status.startswith("pass_")
    ):
        proxy_iv_gate_status = "blocked_long_sample_proxy_iv_missing_or_failed"
    elif me_first_stage_f is None or me_first_stage_f < FIRST_STAGE_F_THRESHOLD:
        proxy_iv_gate_status = "blocked_long_sample_proxy_iv_first_stage_below_threshold"
    elif -me_outcome.iv_estimate.beta <= 0:
        proxy_iv_gate_status = "blocked_long_sample_proxy_iv_wrong_sign"
    else:
        proxy_iv_gate_status = "pass_long_sample_proxy_iv_support"

    if orth_outcome is None:
        orth_gate_status = "review_only_short_overlap_orthogonalized_check_missing"
    elif (
        orth_outcome.iv_estimate is not None
        and orth_outcome.identification_check_status.startswith("pass_")
        and -orth_outcome.iv_estimate.beta > 0
    ):
        orth_gate_status = "pass_short_overlap_orthogonalized_secondary_support"
    else:
        orth_gate_status = "review_only_short_overlap_orthogonalized_not_supportive"

    if h8_crosschecks and all(
        outcome.benchmark_crosscheck_status.startswith("pass_")
        for outcome in h8_crosschecks
    ):
        frbus_gate_status = "pass_directional_frbus_benchmark_context"
    else:
        frbus_gate_status = "blocked_directional_frbus_benchmark_context_missing_or_inconsistent"

    if h8_frbus_100bp_year is None:
        frbus_100bp_year_gate_status = (
            "blocked_frbus_100bp_year_component_benchmark_missing"
        )
    elif h8_frbus_100bp_year.benchmark_support_status == (
        "blocked_frbus_model_fspdp_proxy_wrong_sign"
    ):
        frbus_100bp_year_gate_status = (
            "blocked_frbus_100bp_year_component_benchmark_wrong_sign"
        )
    elif h8_frbus_100bp_year.benchmark_support_status.startswith("blocked_"):
        frbus_100bp_year_gate_status = (
            "blocked_frbus_100bp_year_component_benchmark_missing_or_incomplete"
        )
    elif h8_frbus_100bp_year.benchmark_support_status.startswith("review_weak_"):
        frbus_100bp_year_gate_status = (
            "review_weak_frbus_100bp_year_component_benchmark_support"
        )
    else:
        frbus_100bp_year_gate_status = (
            "pass_frbus_100bp_year_component_benchmark_support"
        )

    weak_iv_safe_gate_status = weak_iv_safe_outcome.weak_iv_safe_inference_status

    fatal_gates = [
        primary_gate_status,
        bootstrap_gate_status,
        replication_gate_status,
        robustness_gate_status,
        proxy_iv_gate_status,
        frbus_gate_status,
    ]
    if not frbus_100bp_year_gate_status.startswith("pass_"):
        fatal_gates.append(frbus_100bp_year_gate_status)
    if any(not gate.startswith("pass_") for gate in fatal_gates):
        failed_gate_summary = ";".join(
            gate for gate in fatal_gates if not gate.startswith("pass_")
        )
        promotion_rule_status = "blocked_promotion_rule_evaluated_review_only"
        exact_blocker = (
            "Bounded promotion-rule evaluation is now materialized, but one or more "
            f"review gates did not pass: {failed_gate_summary}."
        )
        if frbus_100bp_year_gate_status.startswith("review_weak_"):
            next_backend_action = (
                "keep_frbus_100bp_year_benchmark_review_only_and_compare_shape_not_level"
            )
            safe_sentence = (
                "Controlled LP h8 remains review-only because the normalized "
                "FRB/US 100bp-year component benchmark has the right sign but its "
                f"h8 scale is weak relative to the empirical interval: {failed_gate_summary}."
            )
        else:
            next_backend_action = (
                "repair_failed_review_gate_before_weak_iv_safe_inference_upgrade"
            )
            safe_sentence = (
                "Controlled LP h8 remains review-only because bounded review gate "
                f"failures remain: {failed_gate_summary}."
            )
    elif weak_iv_safe_gate_status == "pass_anderson_rubin_hac_interval_excludes_zero_d_y":
        promotion_rule_status = "pass_bounded_h8_current_demand_drag_proxy_input"
        exact_blocker = ""
        next_backend_action = (
            "keep_canonical_rw_y_blocked_and_use_h8_only_inside_noncanonical_current_demand_gate"
        )
        safe_sentence = (
            "Controlled LP h8 clears bounded sign, replication, robustness, proxy-IV, "
            "directional FRB/US context, normalized 100bp-year FRB/US component "
            "benchmark review, and Anderson-Rubin weak-IV-safe review gates. The "
            "primary admitted noncanonical object is the weak-IV-safe interval; any "
            "scalar center remains companion review context only."
        )
    else:
        promotion_rule_status = weak_iv_safe_gate_status
        exact_blocker = weak_iv_safe_outcome.exact_blocker or EXACT_BLOCKER_WEAK_IV_SAFE_PENDING
        next_backend_action = weak_iv_safe_outcome.next_backend_action
        safe_sentence = (
            "Controlled LP h8 clears bounded pre-weak-IV-safe review gates, but it "
            "remains review-only because the Anderson-Rubin weak-IV-safe gate did not "
            "produce a positive bounded D_Y interval."
        )

    outcome = PromotionRuleEvaluationOutcome(
        horizon_q=8,
        primary_controlled_gate_status=primary_gate_status,
        bootstrap_review_gate_status=bootstrap_gate_status,
        replication_gate_status=replication_gate_status,
        robustness_gate_status=robustness_gate_status,
        proxy_iv_gate_status=proxy_iv_gate_status,
        orthogonalized_secondary_gate_status=orth_gate_status,
        frbus_directional_benchmark_gate_status=frbus_gate_status,
        frbus_100bp_year_component_benchmark_gate_status=frbus_100bp_year_gate_status,
        weak_iv_safe_inference_gate_status=weak_iv_safe_gate_status,
        promotion_rule_status=promotion_rule_status,
        denominator_candidate_status=(
            "pass_bounded_h8_current_demand_drag_proxy_input"
            if promotion_rule_status
            == "pass_bounded_h8_current_demand_drag_proxy_input"
            else "review_only_controlled_lp_h8_candidate_not_admitted"
        ),
        exact_blocker=exact_blocker,
        safe_sentence=safe_sentence,
        next_backend_action=next_backend_action,
    )
    row = {field: "" for field in PROMOTION_RULE_EVALUATION_FIELDS}
    row.update(
        {
            "horizon_q": "8",
            "primary_denominator_horizon": "true",
            "promotion_rule_version": PROMOTION_RULE_VERSION,
            "estimator_id": "controlled_fspdp_lp_value_bearing_gdp_share_outcome",
            "primary_controlled_gate_status": primary_gate_status,
            "bootstrap_review_gate_status": bootstrap_gate_status,
            "replication_gate_status": replication_gate_status,
            "robustness_gate_status": robustness_gate_status,
            "proxy_iv_gate_status": proxy_iv_gate_status,
            "orthogonalized_secondary_gate_status": orth_gate_status,
            "frbus_directional_benchmark_gate_status": frbus_gate_status,
            "frbus_100bp_year_component_benchmark_gate_status": (
                frbus_100bp_year_gate_status
            ),
            "weak_iv_safe_inference_gate_status": weak_iv_safe_gate_status,
            "promotion_rule_status": promotion_rule_status,
            "denominator_candidate_status": outcome.denominator_candidate_status,
            "admitted_d_y": "",
            "exact_blocker": exact_blocker,
            "safe_sentence": safe_sentence,
            "next_backend_action": next_backend_action,
            "allowed_use": "bounded_promotion_rule_review_only",
            "blocked_use": (
                "D_Y;GDP_share_drag;denominator_CI;denominator_prior;"
                "Evidence_Mode;main_ratio;pricing;holder_allocation;"
                "raw_rate_shock;reset_calendar;tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "bounded_promotion_rule_not_denominator_admission",
            **_disabled_switches(),
        }
    )
    return [row], outcome


def _compact_status_rows(
    *,
    primary_results: dict[int, DesignMatrixResult],
    primary_estimates: dict[int, HacEstimate | None],
    replication_summaries: dict[int, ReplicationSummary],
    robustness_outcomes: dict[int, dict[str, RobustnessOutcome]],
    promotion_rule_outcome: PromotionRuleEvaluationOutcome,
    identification_outcomes: dict[int, dict[str, IdentificationCheckOutcome]],
    weak_iv_safe_outcome: WeakIvSafeInferenceOutcome,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for horizon in STATUS_HORIZONS:
        primary_result = primary_results[horizon]
        primary_estimate = primary_estimates[horizon]
        primary_robustness = robustness_outcomes[horizon]["primary_update_2023_4lag"]
        replication_summary = replication_summaries[horizon]
        robustness_status, _ = _overall_robustness_status(robustness_outcomes[horizon])
        me_outcome = identification_outcomes.get(horizon, {}).get(
            "sf_fed_usmpd_me_scalar_quarterly_sum"
        )
        review_center_d_y = (
            -me_outcome.iv_estimate.beta
            if me_outcome is not None and me_outcome.iv_estimate is not None
            else (-primary_estimate.beta if primary_estimate is not None else None)
        )
        row = {field: "" for field in STATUS_COMPACT_FIELDS}
        row.update(
            {
                "horizon_q": str(horizon),
                "primary_denominator_horizon": _bool_text(horizon == 8),
                "estimator_id": "controlled_fspdp_lp_value_bearing_gdp_share_outcome",
                "outcome_transform": (
                    "100 * (nominal_fspdp[t-1] / nominal_gdp[t-1]) * "
                    "(log(real_fspdp[t+h]) - log(real_fspdp[t-1]))"
                ),
                "exposure_series_id": "value_bearing_bps_year_exposure_update_2023_quarterly_sum",
                "sample_window_id": SAMPLE_WINDOW_ID,
                "control_spec_id": CONTROL_SPEC_ID,
                "n_obs": str(primary_result.n_obs),
                "beta_response_gdp_share_pp": (
                    _format_float(primary_estimate.beta)
                    if primary_estimate is not None
                    else ""
                ),
                "review_center_d_y": _format_float(review_center_d_y),
                "bounded_ci_low_d_y": (
                    _format_float(weak_iv_safe_outcome.weak_iv_safe_ci_low_d_y)
                    if horizon == 8
                    else ""
                ),
                "bounded_ci_high_d_y": (
                    _format_float(weak_iv_safe_outcome.weak_iv_safe_ci_high_d_y)
                    if horizon == 8
                    else ""
                ),
                "bounded_primary_object_type": (
                    "weak_iv_safe_interval_primary_proxy_iv_center_companion"
                    if horizon == 8
                    else "companion_horizon_context_only"
                ),
                "bounded_primary_artifact": (
                    "ratewall_conventional_drag_bounded_denominator_registry.csv"
                    if horizon == 8
                    else ""
                ),
                "ci95_low_d_y": (
                    _format_float(-primary_estimate.ci_high)
                    if primary_estimate is not None
                    else ""
                ),
                "ci95_high_d_y": (
                    _format_float(-primary_estimate.ci_low)
                    if primary_estimate is not None
                    else ""
                ),
                "bootstrap_ci_low_d_y": (
                    _format_float(primary_robustness.bootstrap.ci_low_d_y)
                    if primary_robustness.bootstrap is not None
                    else ""
                ),
                "bootstrap_ci_high_d_y": (
                    _format_float(primary_robustness.bootstrap.ci_high_d_y)
                    if primary_robustness.bootstrap is not None
                    else ""
                ),
                "bootstrap_sign_probability_d_y_positive": (
                    _format_float(primary_robustness.bootstrap.sign_probability)
                    if primary_robustness.bootstrap is not None
                    else ""
                ),
                "replication_status": replication_summary.replication_status,
                "robustness_status": robustness_status,
                "allowed_use": "controlled_lp_compact_status_only",
                "blocked_use": (
                    "GDP_share_drag;denominator_prior;Evidence_Mode;main_ratio;"
                    "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
                    "tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "controlled_lp_denominator_status_not_main_ratio",
                **_disabled_switches(),
            }
        )

        if horizon != 8:
            row.update(
                {
                    "admitted_d_y": "",
                    "promotion_rule_status": "not_primary_horizon_review_only",
                    "denominator_candidate_status": (
                        "pass_companion_horizon_estimated_review_only"
                        if primary_estimate is not None
                        else "blocked_companion_horizon_not_estimated"
                    ),
                    "exact_blocker": (
                        ""
                        if primary_estimate is not None
                        else primary_result.exact_blocker or EXACT_BLOCKER_MISSING_CONTROLS
                    ),
                    "safe_sentence": (
                        "Controlled companion-horizon estimate reported for context only; "
                        "h8 remains the primary review horizon in this tranche."
                    ),
                    "next_backend_action": "use_as_companion_context_only",
                }
            )
            rows.append(row)
            continue

        admission_passes = (
            promotion_rule_outcome.promotion_rule_status
            == "pass_bounded_h8_current_demand_drag_proxy_input"
        )
        if admission_passes:
            row.update(
                {
                    "admitted_d_y": "",
                    "promotion_rule_status": (
                        "pass_bounded_h8_current_demand_drag_proxy_input"
                    ),
                    "denominator_candidate_status": (
                        "pass_bounded_h8_current_demand_drag_proxy_input"
                    ),
                    "exact_blocker": "",
                    "safe_sentence": (
                        "The bounded h8 current-demand drag proxy is admitted review-only. "
                        "Its primary object is the weak-IV-safe interval in the bounded "
                        "denominator registry; the proxy-IV center is companion overlay "
                        "context and the controlled-LP OLS estimate remains diagnostic context."
                    ),
                    "next_backend_action": (
                        "keep_bounded_h8_review_only_and_compare_consumers_against_interval_not_canonical_rw_y"
                    ),
                }
            )
        else:
            row.update(
                {
                    "admitted_d_y": "",
                    "promotion_rule_status": promotion_rule_outcome.promotion_rule_status,
                    "denominator_candidate_status": (
                        "review_only_controlled_lp_h8_candidate_not_admitted"
                    ),
                    "exact_blocker": promotion_rule_outcome.exact_blocker,
                    "safe_sentence": promotion_rule_outcome.safe_sentence,
                    "next_backend_action": promotion_rule_outcome.next_backend_action,
                }
            )
        rows.append(row)
    return rows


def _bounded_denominator_registry_rows(
    *,
    primary_results: dict[int, DesignMatrixResult],
    primary_estimates: dict[int, HacEstimate | None],
    identification_outcomes: dict[int, dict[str, IdentificationCheckOutcome]],
    weak_iv_safe_outcome: WeakIvSafeInferenceOutcome,
    promotion_rule_outcome: PromotionRuleEvaluationOutcome,
) -> tuple[list[dict[str, str]], dict[int, BoundedDenominatorOutcome]]:
    rows: list[dict[str, str]] = []
    outcomes: dict[int, BoundedDenominatorOutcome] = {}
    for horizon in STATUS_HORIZONS:
        primary_estimate = primary_estimates[horizon]
        primary_result = primary_results[horizon]
        me_outcome = identification_outcomes.get(horizon, {}).get(
            "sf_fed_usmpd_me_scalar_quarterly_sum"
        )
        review_center_d_y = (
            -me_outcome.iv_estimate.beta
            if me_outcome is not None and me_outcome.iv_estimate is not None
            else (-primary_estimate.beta if primary_estimate is not None else None)
        )
        outcome = BoundedDenominatorOutcome(
            horizon_q=horizon,
            primary_denominator_horizon=horizon == 8,
            bounded_primary_object_type=(
                "weak_iv_safe_interval_primary_proxy_iv_center_companion"
                if horizon == 8
                else "companion_horizon_context_only"
            ),
            bounded_primary_estimator_id=(
                "sf_fed_usmpd_me_proxy_iv_anderson_rubin_hac_interval"
                if horizon == 8
                else "companion_horizon_context_only"
            ),
            review_center_estimator_id=(
                "sf_fed_usmpd_me_proxy_iv_center"
                if me_outcome is not None and me_outcome.iv_estimate is not None
                else "controlled_lp_ols_hac_center"
            ),
            review_center_d_y=review_center_d_y,
            bounded_ci_low_d_y=(
                weak_iv_safe_outcome.weak_iv_safe_ci_low_d_y if horizon == 8 else None
            ),
            bounded_ci_high_d_y=(
                weak_iv_safe_outcome.weak_iv_safe_ci_high_d_y if horizon == 8 else None
            ),
            companion_controlled_ci_low_d_y=(
                -primary_estimate.ci_high if primary_estimate is not None else None
            ),
            companion_controlled_ci_high_d_y=(
                -primary_estimate.ci_low if primary_estimate is not None else None
            ),
            proxy_iv_ci_low_d_y=(
                -me_outcome.iv_estimate.ci_high
                if me_outcome is not None and me_outcome.iv_estimate is not None
                else None
            ),
            proxy_iv_ci_high_d_y=(
                -me_outcome.iv_estimate.ci_low
                if me_outcome is not None and me_outcome.iv_estimate is not None
                else None
            ),
            sample_start_q=(
                weak_iv_safe_outcome.sample_start_q if horizon == 8 else primary_result.sample_start_q
            ),
            sample_end_q=(
                weak_iv_safe_outcome.sample_end_q if horizon == 8 else primary_result.sample_end_q
            ),
            n_obs=(weak_iv_safe_outcome.n_obs if horizon == 8 else primary_result.n_obs),
            weak_iv_safe_method=(
                weak_iv_safe_outcome.weak_iv_safe_method if horizon == 8 else ""
            ),
            weak_iv_safe_inference_status=(
                weak_iv_safe_outcome.weak_iv_safe_inference_status
                if horizon == 8
                else "not_primary_horizon_review_only"
            ),
            promotion_rule_status=(
                promotion_rule_outcome.promotion_rule_status
                if horizon == 8
                else "not_primary_horizon_review_only"
            ),
            bounded_denominator_status=(
                "pass_bounded_h8_current_demand_drag_proxy_input"
                if horizon == 8
                and promotion_rule_outcome.promotion_rule_status
                == "pass_bounded_h8_current_demand_drag_proxy_input"
                else (
                    "pass_companion_horizon_estimated_review_only"
                    if horizon != 8 and primary_estimate is not None
                    else "review_only_controlled_lp_h8_candidate_not_admitted"
                )
            ),
            current_demand_overlay_input_enabled=(
                horizon == 8
                and promotion_rule_outcome.promotion_rule_status
                == "pass_bounded_h8_current_demand_drag_proxy_input"
            ),
            exact_blocker=(
                ""
                if horizon == 8
                and promotion_rule_outcome.promotion_rule_status
                == "pass_bounded_h8_current_demand_drag_proxy_input"
                else (
                    promotion_rule_outcome.exact_blocker
                    if horizon == 8
                    else ""
                )
            ),
            safe_sentence=(
                "Primary bounded noncanonical object is the weak-IV-safe h8 interval; "
                "the proxy-IV center is available for review-only overlays."
                if horizon == 8
                and promotion_rule_outcome.promotion_rule_status
                == "pass_bounded_h8_current_demand_drag_proxy_input"
                else (
                    "Companion horizon context only."
                    if horizon != 8
                    else promotion_rule_outcome.safe_sentence
                )
            ),
            next_backend_action=(
                "keep_bounded_h8_review_only_and_compare_consumers_against_interval_not_canonical_rw_y"
                if horizon == 8
                and promotion_rule_outcome.promotion_rule_status
                == "pass_bounded_h8_current_demand_drag_proxy_input"
                else (
                    "use_as_companion_context_only"
                    if horizon != 8
                    else promotion_rule_outcome.next_backend_action
                )
            ),
        )
        outcomes[horizon] = outcome
        row = {field: "" for field in BOUNDED_DENOMINATOR_REGISTRY_FIELDS}
        row.update(
            {
                "bounded_denominator_row_id": (
                    f"bounded_denominator_registry::RW_Y::h{horizon}"
                ),
                "route_id": "bounded_h8_current_demand_drag_proxy_route",
                "ratio_id": "RW_Y",
                "horizon_q": str(horizon),
                "primary_denominator_horizon": _bool_text(outcome.primary_denominator_horizon),
                "bounded_primary_object_type": outcome.bounded_primary_object_type,
                "bounded_primary_estimator_id": outcome.bounded_primary_estimator_id,
                "review_center_estimator_id": outcome.review_center_estimator_id,
                "review_center_d_y": _format_float(outcome.review_center_d_y),
                "bounded_ci_low_d_y": _format_float(outcome.bounded_ci_low_d_y),
                "bounded_ci_high_d_y": _format_float(outcome.bounded_ci_high_d_y),
                "companion_controlled_ci_low_d_y": _format_float(
                    outcome.companion_controlled_ci_low_d_y
                ),
                "companion_controlled_ci_high_d_y": _format_float(
                    outcome.companion_controlled_ci_high_d_y
                ),
                "proxy_iv_ci_low_d_y": _format_float(outcome.proxy_iv_ci_low_d_y),
                "proxy_iv_ci_high_d_y": _format_float(outcome.proxy_iv_ci_high_d_y),
                "sample_window_id": SAMPLE_WINDOW_ID,
                "control_spec_id": CONTROL_SPEC_ID,
                "bounded_primary_sample_start_q": outcome.sample_start_q,
                "bounded_primary_sample_end_q": outcome.sample_end_q,
                "bounded_primary_n_obs": str(outcome.n_obs),
                "weak_iv_safe_method": outcome.weak_iv_safe_method,
                "weak_iv_safe_inference_status": outcome.weak_iv_safe_inference_status,
                "promotion_rule_status": outcome.promotion_rule_status,
                "bounded_denominator_status": outcome.bounded_denominator_status,
                "current_demand_overlay_input_enabled": _bool_text(
                    outcome.current_demand_overlay_input_enabled
                ),
                "exact_blocker": outcome.exact_blocker,
                "safe_sentence": outcome.safe_sentence,
                "next_backend_action": outcome.next_backend_action,
                "allowed_use": "bounded_h8_denominator_registry_review_only",
                "blocked_use": (
                    "canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;"
                    "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
                    "tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "bounded_h8_denominator_registry_not_canonical_denominator",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows, outcomes


def _overall_robustness_status(
    outcomes: dict[str, RobustnessOutcome]
) -> tuple[str, str]:
    required_cases = [
        "primary_update_2023_4lag",
        "original_vintage_4lag",
        "update_2023_2lag",
        "update_2023_6lag",
        "include_emergency_exclude_elb_pandemic",
        "leave_one_out_max_influence",
    ]
    pre_2008 = outcomes["pre_2008_conventional_if_nobs_usable"]
    if pre_2008.robustness_status != "review_only_pre_2008_nobs_not_usable":
        required_cases.append("pre_2008_conventional_if_nobs_usable")
    for case_id in required_cases:
        outcome = outcomes[case_id]
        if not outcome.robustness_status.startswith("pass_"):
            return outcome.robustness_status, outcome.exact_blocker
    return "pass_narrow_robustness_preserved", ""


def _overall_identification_status(
    outcomes: dict[str, IdentificationCheckOutcome],
) -> tuple[str, str]:
    me_outcome = outcomes.get("sf_fed_usmpd_me_scalar_quarterly_sum")
    orth_outcome = outcomes.get("sf_fed_chart_orthogonalized_surprise_quarterly_sum")
    if me_outcome is None:
        return (
            "blocked_identification_check_missing_long_sample_proxy",
            "Long-sample USMPD ME proxy-IV identification check is missing.",
        )
    if not me_outcome.identification_check_status.startswith("pass_"):
        return me_outcome.identification_check_status, me_outcome.exact_blocker
    if orth_outcome is None:
        return (
            "pass_long_sample_proxy_iv_review_only",
            (
                "Long-sample USMPD ME proxy-IV check is sign-supportive, but the "
                "public orthogonalized short-overlap comparison is missing."
            ),
        )
    if orth_outcome.identification_check_status.startswith("pass_"):
        return (
            "pass_proxy_iv_and_orthogonalized_checks_review_only",
            (
                "Long-sample USMPD ME proxy-IV and short-overlap public "
                "orthogonalized LP-IV checks are sign-supportive. They remain "
                "review-only support rows because the primary admitted noncanonical "
                "object is tracked separately in the bounded denominator registry."
            ),
        )
    return (
        "pass_long_sample_proxy_iv_review_only",
        (
            "Long-sample USMPD ME proxy-IV check is sign-supportive, but the public "
            "orthogonalized comparison is incomplete or too short. h8 remains "
            "review-only until the promotion rule is tightened."
        ),
    )


def _leave_one_out_metrics(
    y_values: Sequence[float],
    x_rows: Sequence[Sequence[float]],
    quarters: Sequence[str],
    *,
    bandwidth: int,
) -> tuple[float, float, str, float]:
    d_y_values: list[float] = []
    influence_pairs: list[tuple[str, float]] = []
    baseline = _ols_hac(y_values, x_rows, bandwidth=bandwidth)
    baseline_d_y = -baseline.beta
    for index, quarter in enumerate(quarters):
        y_subset = [value for i, value in enumerate(y_values) if i != index]
        x_subset = [row for i, row in enumerate(x_rows) if i != index]
        estimate = _ols_hac_lstsq(y_subset, x_subset, bandwidth=min(bandwidth, len(y_subset) - 1))
        d_y = -estimate.beta
        d_y_values.append(d_y)
        influence_pairs.append((quarter, abs(d_y - baseline_d_y)))
    sorted_d_y = sorted(d_y_values)
    mid = len(sorted_d_y) // 2
    if len(sorted_d_y) % 2 == 1:
        median = sorted_d_y[mid]
    else:
        median = 0.5 * (sorted_d_y[mid - 1] + sorted_d_y[mid])
    positive_share = sum(value > 0 for value in d_y_values) / len(d_y_values)
    max_quarter, max_shift = max(influence_pairs, key=lambda pair: pair[1])
    return median, positive_share, max_quarter, max_shift


def _moving_block_bootstrap_d_y(
    y_values: Sequence[float],
    x_rows: Sequence[Sequence[float]],
    *,
    bandwidth: int,
    block_length: int,
    seed: int,
) -> BootstrapResult:
    import numpy as np

    y = np.array(y_values, dtype=float)
    x = np.array(x_rows, dtype=float)
    if len(y) <= 1:
        return BootstrapResult(
            ci_low_d_y=None,
            ci_high_d_y=None,
            sign_probability=None,
            successful_draws=0,
            status="blocked_bootstrap_sample_too_small",
        )
    effective_block = min(max(1, block_length), len(y))
    max_lag = min(bandwidth, len(y) - 1)
    rng = np.random.default_rng(seed)
    boot_d_y: list[float] = []
    max_start = len(y) - effective_block
    attempts = 0
    max_attempts = BOOTSTRAP_DRAWS * 20
    while len(boot_d_y) < BOOTSTRAP_DRAWS and attempts < max_attempts:
        attempts += 1
        indices: list[int] = []
        while len(indices) < len(y):
            start = 0 if max_start <= 0 else int(rng.integers(0, max_start + 1))
            indices.extend(range(start, start + effective_block))
        indices = indices[: len(y)]
        x_sample = x[indices]
        if np.linalg.matrix_rank(x_sample) < x_sample.shape[1]:
            continue
        estimate = _ols_hac_lstsq(y[indices], x_sample, bandwidth=max_lag)
        boot_d_y.append(-estimate.beta)
    if len(boot_d_y) < max(100, BOOTSTRAP_DRAWS // 2):
        return BootstrapResult(
            ci_low_d_y=None,
            ci_high_d_y=None,
            sign_probability=None,
            successful_draws=len(boot_d_y),
            status="blocked_bootstrap_insufficient_successful_draws",
        )
    boot_array = np.array(boot_d_y, dtype=float)
    return BootstrapResult(
        ci_low_d_y=float(np.quantile(boot_array, 0.025)),
        ci_high_d_y=float(np.quantile(boot_array, 0.975)),
        sign_probability=float(np.mean(boot_array > 0)),
        successful_draws=len(boot_d_y),
        status="pass_bootstrap_completed",
    )


def _ols_hac(
    y_values: Sequence[float],
    x_rows: Sequence[Sequence[float]],
    *,
    bandwidth: int,
) -> HacEstimate:
    import numpy as np

    x = np.array(x_rows, dtype=float)
    y = np.array(y_values, dtype=float)
    xtx = x.T @ x
    beta = np.linalg.solve(xtx, x.T @ y)
    residuals = y - x @ beta
    covariance = _hac_covariance_from_residuals(x, residuals, bandwidth=bandwidth)
    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    beta_shock = float(beta[1])
    se_shock = float(se[1])
    return HacEstimate(
        beta=beta_shock,
        se=se_shock,
        ci_low=beta_shock - 1.96 * se_shock,
        ci_high=beta_shock + 1.96 * se_shock,
    )


def _ols_hac_lstsq(
    y_values: Sequence[float],
    x_rows: Sequence[Sequence[float]],
    *,
    bandwidth: int,
) -> HacEstimate:
    import numpy as np

    x = np.array(x_rows, dtype=float)
    y = np.array(y_values, dtype=float)
    beta, *_rest = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta
    xe = x * residuals[:, None]
    meat = xe.T @ xe
    max_lag = min(bandwidth, len(y) - 1)
    for lag in range(1, max_lag + 1):
        weight = 1.0 - (lag / (max_lag + 1))
        gamma = xe[lag:].T @ xe[:-lag]
        meat += weight * (gamma + gamma.T)
    xtx_inv = np.linalg.inv(x.T @ x)
    covariance = xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    beta_shock = float(beta[1])
    se_shock = float(se[1])
    return HacEstimate(
        beta=beta_shock,
        se=se_shock,
        ci_low=beta_shock - 1.96 * se_shock,
        ci_high=beta_shock + 1.96 * se_shock,
    )


def _iv_2sls_hac(
    *,
    y_values: Sequence[float],
    x_rows: Sequence[Sequence[float]],
    z_values: Sequence[float],
    bandwidth: int,
) -> HacEstimate | None:
    import numpy as np

    x = np.array(x_rows, dtype=float)
    y = np.array(y_values, dtype=float)
    z = np.array(z_values, dtype=float)
    instruments = np.column_stack([np.ones(len(y)), z, x[:, 2:]])
    try:
        zx = instruments.T @ x
        beta = np.linalg.solve(zx, instruments.T @ y)
        residuals = y - x @ beta
        g = instruments * residuals[:, None]
        max_lag = min(bandwidth, len(y) - 1)
        s = g.T @ g
        for lag in range(1, max_lag + 1):
            weight = 1.0 - (lag / (max_lag + 1))
            gamma = g[lag:].T @ g[:-lag]
            s += weight * (gamma + gamma.T)
        zx_inv = np.linalg.inv(zx)
        covariance = zx_inv @ s @ zx_inv.T
    except np.linalg.LinAlgError:
        return None
    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    beta_shock = float(beta[1])
    se_shock = float(se[1])
    return HacEstimate(
        beta=beta_shock,
        se=se_shock,
        ci_low=beta_shock - 1.96 * se_shock,
        ci_high=beta_shock + 1.96 * se_shock,
    )


def _hac_covariance_from_residuals(x, residuals, *, bandwidth: int):
    import numpy as np

    xtx_inv = np.linalg.inv(x.T @ x)
    max_lag = min(bandwidth, len(residuals) - 1)
    s = np.zeros((x.shape[1], x.shape[1]), dtype=float)
    for t in range(len(residuals)):
        row = x[t : t + 1].T
        s += residuals[t] * residuals[t] * (row @ row.T)
    for lag in range(1, max_lag + 1):
        weight = 1.0 - (lag / (max_lag + 1))
        gamma = np.zeros_like(s)
        for t in range(lag, len(residuals)):
            row_t = x[t : t + 1].T
            row_lag = x[t - lag : t - lag + 1].T
            gamma += residuals[t] * residuals[t - lag] * (row_t @ row_lag.T)
        s += weight * (gamma + gamma.T)
    return xtx_inv @ s @ xtx_inv


def _quarterly_average_controls(
    snapshots: Sequence[SourceSnapshot],
) -> dict[str, dict[str, float]]:
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in snapshots}
    required = ("UNRATE", "FEDFUNDS")
    result: dict[str, dict[str, float]] = {}
    for series_id in required:
        snapshot = by_series.get(series_id)
        if snapshot is None or snapshot.metadata.snapshot_kind == "fallback_stub":
            result[series_id] = {}
            continue
        grouped: dict[str, list[float]] = {}
        for record in snapshot.records:
            value = _float_or_none(record.get("value"))
            date_text = str(record.get("date", ""))
            if value is None or not date_text:
                continue
            quarter = _quarter_label(date_text)
            grouped.setdefault(quarter, []).append(value)
        result[series_id] = {
            quarter: sum(values) / len(values)
            for quarter, values in grouped.items()
            if values
        }
    return result


def _exposure_by_vintage(
    exposure_quarterly_rows: Sequence[dict[str, str]],
) -> dict[str, dict[str, dict[str, str]]]:
    grouped = {"update_2023": {}, "original": {}}
    for row in exposure_quarterly_rows:
        quarter = row.get("quarter", "")
        vintage = row.get("source_sheet_vintage", "")
        if quarter and vintage in grouped:
            grouped[vintage][quarter] = row
    return grouped


def _exposure_for_vintage(
    record: QuarterPanelRecord | None,
    exposure_vintage: str,
) -> float | None:
    if record is None:
        return None
    if exposure_vintage == "update_2023":
        return record.tightening_exposure_update_2023
    if exposure_vintage == "original":
        return record.tightening_exposure_original
    return None


def _quarter_label(date_text: str) -> str:
    year, month, _day = date_text.split("-")
    quarter = (int(month) - 1) // 3 + 1
    return f"{year}Q{quarter}"


def _quarter_index_from_label(quarter: str) -> int | None:
    if "Q" not in quarter:
        return None
    year_text, quarter_text = quarter.split("Q", 1)
    try:
        year = int(year_text)
        quarter_num = int(quarter_text)
    except ValueError:
        return None
    if quarter_num not in {1, 2, 3, 4}:
        return None
    return year * 4 + quarter_num - 1


def _quarter_label_from_index(index: int) -> str:
    year, quarter_zero = divmod(index, 4)
    return f"{year}Q{quarter_zero + 1}"


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


def _noncanonical_current_demand_support_ratio_consumer_rows(
    *,
    forecast_holder_tdc_consistency_bridge_rows: Sequence[dict[str, str]],
    bounded_denominator_registry_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    primary_status = next(
        (
            row
            for row in bounded_denominator_registry_rows
            if row["primary_denominator_horizon"] == "true"
        ),
        None,
    )
    review_center_d_y = (
        _decimal_or_none(primary_status["review_center_d_y"]) if primary_status else None
    )
    bounded_ci_low_d_y = (
        _decimal_or_none(primary_status["bounded_ci_low_d_y"]) if primary_status else None
    )
    bounded_ci_high_d_y = (
        _decimal_or_none(primary_status["bounded_ci_high_d_y"]) if primary_status else None
    )
    denominator_input_status = (
        "pass_bounded_h8_current_demand_drag_proxy_input"
        if primary_status
        and primary_status["bounded_denominator_status"]
        == "pass_bounded_h8_current_demand_drag_proxy_input"
        else "review_only_h8_candidate_not_admitted"
    )
    rows: list[dict[str, str]] = []
    for bridge_row in forecast_holder_tdc_consistency_bridge_rows:
        nominal_gdp = _decimal_or_none(bridge_row.get("nominal_gdp_bil"))
        combined_support = _decimal_or_none(
            bridge_row.get("combined_current_demand_support_bil")
        )
        support_pct_of_gdp = (
            Decimal("100") * combined_support / nominal_gdp
            if nominal_gdp not in {None, Decimal("0")} and combined_support is not None
            else None
        )
        support_offset_100bp_year_equivalent = _safe_ratio(
            support_pct_of_gdp, review_center_d_y
        )
        support_offset_100bp_year_equivalent_lower_bound = _safe_ratio(
            support_pct_of_gdp, bounded_ci_high_d_y
        )
        support_offset_100bp_year_equivalent_upper_bound = _safe_ratio(
            support_pct_of_gdp, bounded_ci_low_d_y
        )
        support_offset_bp_year_equivalent = (
            None
            if support_offset_100bp_year_equivalent is None
            else support_offset_100bp_year_equivalent * Decimal("100")
        )
        support_offset_bp_year_equivalent_lower_bound = (
            None
            if support_offset_100bp_year_equivalent_lower_bound is None
            else support_offset_100bp_year_equivalent_lower_bound * Decimal("100")
        )
        support_offset_bp_year_equivalent_upper_bound = (
            None
            if support_offset_100bp_year_equivalent_upper_bound is None
            else support_offset_100bp_year_equivalent_upper_bound * Decimal("100")
        )
        row = {
            field: ""
            for field in NONCANONICAL_CURRENT_DEMAND_SUPPORT_RATIO_CONSUMER_FIELDS
        }
        row.update(
            {
                "consumer_row_id": (
                    "noncanonical_current_demand_support_ratio_consumer::"
                    f"{bridge_row['forecast_year']}::{bridge_row['mpc_scenario']}::"
                    f"{bridge_row['maturity_scenario']}::{bridge_row['holder_scenario']}"
                ),
                "ratio_id": "RW_Y",
                "ratio_layer_registry_row_id": "ratio_layer_registry::0001",
                "numerator_source_artifact": (
                    "ratewall_forecast_holder_tdc_consistency_bridge.csv"
                ),
                "denominator_status_artifact": (
                    "ratewall_conventional_drag_denominator_status_compact.csv"
                ),
                "bounded_denominator_artifact": (
                    "ratewall_conventional_drag_bounded_denominator_registry.csv"
                ),
                "denominator_horizon_q": "8",
                "forecast_year": bridge_row["forecast_year"],
                "mpc_scenario": bridge_row["mpc_scenario"],
                "maturity_scenario": bridge_row["maturity_scenario"],
                "holder_scenario": bridge_row["holder_scenario"],
                "nominal_gdp_bil": bridge_row["nominal_gdp_bil"],
                "combined_current_demand_support_bil": bridge_row[
                    "combined_current_demand_support_bil"
                ],
                "support_pct_of_gdp": _format_decimal(support_pct_of_gdp),
                "denominator_source_id": "bounded_h8_overlay_review_center",
                "denominator_source_class": "bounded_h8_overlay_review_only",
                "denominator_timing_class": "h8_cumulative_equivalent_overlay",
                "denominator_anchor_empirical_status": (
                    "pass_bounded_h8_evidence_route_review_only"
                ),
                "denominator_scenario_runtime_allowed": "false",
                "review_center_d_y": _format_decimal(review_center_d_y),
                "admitted_d_y": "",
                "bounded_ci_low_d_y": _format_decimal(bounded_ci_low_d_y),
                "bounded_ci_high_d_y": _format_decimal(bounded_ci_high_d_y),
                "bounded_primary_object_type": (
                    primary_status["bounded_primary_object_type"]
                    if primary_status is not None
                    else ""
                ),
                "support_offset_100bp_year_equivalent_lower_bound": _format_decimal(
                    support_offset_100bp_year_equivalent_lower_bound
                ),
                "support_offset_100bp_year_equivalent": _format_decimal(
                    support_offset_100bp_year_equivalent
                ),
                "support_offset_100bp_year_equivalent_upper_bound": _format_decimal(
                    support_offset_100bp_year_equivalent_upper_bound
                ),
                "support_offset_bp_year_equivalent_lower_bound": _format_decimal(
                    support_offset_bp_year_equivalent_lower_bound
                ),
                "support_offset_bp_year_equivalent": _format_decimal(
                    support_offset_bp_year_equivalent
                ),
                "support_offset_bp_year_equivalent_upper_bound": _format_decimal(
                    support_offset_bp_year_equivalent_upper_bound
                ),
                "legacy_holder_tdc_consistent_wall_ratio": bridge_row[
                    "holder_tdc_consistent_wall_ratio"
                ],
                "conventional_drag_bil": bridge_row["conventional_drag_bil"],
                "gap_to_wall_holder_tdc_consistent_bil": bridge_row[
                    "gap_to_wall_holder_tdc_consistent_bil"
                ],
                "numerator_source_status": bridge_row["source_status"],
                "double_count_prevention_rule": bridge_row[
                    "double_count_prevention_rule"
                ],
                "denominator_input_status": denominator_input_status,
                "allowed_use": (
                    "review_only_noncanonical_current_demand_support_overlay"
                ),
                "blocked_use": (
                    "canonical_RW_Y;main_ratio;Evidence_Mode;denominator_prior;"
                    "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
                    "tax_incidence_welfare_mpc"
                ),
                "claim_boundary": (
                    "noncanonical_current_demand_support_ratio_consumer_review_only"
                ),
                **_disabled_switches(),
            }
        )
        if review_center_d_y is not None and bounded_ci_low_d_y is not None:
            row.update(
                {
                    "timing_alignment_status": (
                        "review_only_annual_support_overlay_vs_h8_cumulative_drag"
                    ),
                    "consumer_status": (
                        "pass_review_only_noncanonical_support_offset_computed"
                    ),
                    "historical_reporting_status": (
                        "blocked_canonical_rw_y_history_not_enabled"
                    ),
                    "main_ratio_status": "blocked_main_ratio_disabled_by_design",
                    "evidence_mode_status": (
                        "blocked_evidence_mode_disabled_by_design"
                    ),
                    "exact_blocker": (
                        "This consumer pairs an annual assumption-mode current-demand "
                        "support scaffold with the bounded h8 interval-first "
                        "noncanonical denominator object. It is review-only, not a "
                        "formally timing-aligned canonical RW_Y estimator."
                    ),
                    "safe_sentence": (
                        "This row converts annual current-demand support into a "
                        "bounded bps-year-equivalent overlay using the proxy-IV center "
                        "and weak-IV-safe h8 interval. It remains a scenario overlay, "
                        "not canonical RW_Y."
                    ),
                    "next_backend_action": (
                        "upgrade_numerator_source_gate_and_formalize_timing_alignment_before_any_canonical_use"
                    ),
                }
            )
        else:
            row.update(
                {
                    "timing_alignment_status": (
                        "blocked_primary_h8_denominator_not_admitted"
                    ),
                    "consumer_status": (
                        "blocked_primary_h8_denominator_not_admitted"
                    ),
                    "historical_reporting_status": (
                        "blocked_canonical_rw_y_history_not_enabled"
                    ),
                    "main_ratio_status": "blocked_main_ratio_disabled_by_design",
                    "evidence_mode_status": (
                        "blocked_evidence_mode_disabled_by_design"
                    ),
                    "exact_blocker": (
                        "No noncanonical support consumer can compute an offset while "
                        "the primary h8 denominator remains unadmitted."
                    ),
                    "safe_sentence": (
                        "The support overlay stays blocked until the noncanonical h8 "
                        "bounded denominator input is admitted."
                    ),
                    "next_backend_action": (
                        "keep_h8_denominator_gate_blocked_until_promotion_rule_passes"
                    ),
                }
            )
        rows.append(row)
    return rows


def _current_demand_ratio_gate_rows(
    denominator_status_compact_rows: Sequence[dict[str, str]],
    bounded_denominator_registry_rows: Sequence[dict[str, str]],
    noncanonical_current_demand_support_ratio_consumer_rows: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    consumer_available = any(
        row["consumer_status"]
        in {
            "pass_review_only_noncanonical_support_offset_computed",
            "pass_review_only_bounded_h8_overlay_visible_nonratio",
            "pass_review_only_literature_support_offset_computed",
        }
        for row in noncanonical_current_demand_support_ratio_consumer_rows
    )
    bounded_rows_by_horizon = {
        row["horizon_q"]: row for row in bounded_denominator_registry_rows
    }
    rows: list[dict[str, str]] = []
    for status_row in denominator_status_compact_rows:
        horizon = status_row["horizon_q"]
        bounded_row = bounded_rows_by_horizon.get(horizon, {})
        row = {field: "" for field in CURRENT_DEMAND_RATIO_GATE_FIELDS}
        row.update(
            {
                "ratio_gate_row_id": (
                    f"conventional_drag_current_demand_ratio_gate::RW_Y::h{horizon}"
                ),
                "ratio_id": "RW_Y",
                "ratio_layer_registry_row_id": "ratio_layer_registry::0001",
                "denominator_status_artifact": (
                    "ratewall_conventional_drag_denominator_status_compact.csv"
                ),
                "bounded_denominator_artifact": (
                    "ratewall_conventional_drag_bounded_denominator_registry.csv"
                ),
                "denominator_horizon_q": horizon,
                "primary_denominator_horizon": status_row["primary_denominator_horizon"],
                "denominator_estimator_id": status_row["estimator_id"],
                "sample_window_id": status_row["sample_window_id"],
                "control_spec_id": status_row["control_spec_id"],
                "n_obs": status_row["n_obs"],
                "review_center_d_y": bounded_row.get("review_center_d_y", ""),
                "admitted_d_y": "",
                "bounded_ci_low_d_y": bounded_row.get("bounded_ci_low_d_y", ""),
                "bounded_ci_high_d_y": bounded_row.get("bounded_ci_high_d_y", ""),
                "bounded_primary_object_type": bounded_row.get(
                    "bounded_primary_object_type", ""
                ),
                "ci95_low_d_y": status_row["ci95_low_d_y"],
                "ci95_high_d_y": status_row["ci95_high_d_y"],
                "bootstrap_ci_low_d_y": status_row["bootstrap_ci_low_d_y"],
                "bootstrap_ci_high_d_y": status_row["bootstrap_ci_high_d_y"],
                "bootstrap_sign_probability_d_y_positive": status_row[
                    "bootstrap_sign_probability_d_y_positive"
                ],
                "replication_status": status_row["replication_status"],
                "robustness_status": status_row["robustness_status"],
                "promotion_rule_status": status_row["promotion_rule_status"],
                "denominator_candidate_status": status_row[
                    "denominator_candidate_status"
                ],
                "allowed_use": "current_demand_ratio_gate_noncanonical_only",
                "blocked_use": (
                    "main_ratio;Evidence_Mode;denominator_prior;pricing;"
                    "holder_allocation;raw_rate_shock;reset_calendar;"
                    "tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "current_demand_ratio_gate_not_main_ratio",
                **_disabled_switches(),
            }
        )

        if status_row["primary_denominator_horizon"] == "true":
            if (
                bounded_row.get("bounded_denominator_status")
                == "pass_bounded_h8_current_demand_drag_proxy_input"
            ):
                if consumer_available:
                    row.update(
                        {
                            "downstream_current_demand_input_enabled": "true",
                            "denominator_input_status": (
                                "pass_bounded_h8_current_demand_drag_proxy_input"
                            ),
                            "ratio_gate_status": (
                                "pass_h8_bounded_proxy_input_enabled_review_only_consumer_available"
                            ),
                            "numerator_runtime_status": (
                                "pass_noncanonical_current_demand_support_ratio_consumer_review_only"
                            ),
                            "historical_reporting_status": (
                                "blocked_canonical_rw_y_history_not_enabled"
                            ),
                            "main_ratio_status": (
                                "blocked_main_ratio_disabled_by_design"
                            ),
                            "evidence_mode_status": (
                                "blocked_evidence_mode_disabled_by_design"
                            ),
                            "exact_blocker": (
                                "The bounded h8 interval-first current-demand drag proxy "
                                "is enabled and a separate review-only current-demand "
                                "support consumer exists, but canonical RW_Y history, "
                                "main-ratio entry, and Evidence Mode remain blocked."
                            ),
                            "safe_sentence": (
                                "The weak-IV-safe h8 interval is the primary admitted "
                                "noncanonical object, and the proxy-IV center can feed a "
                                "separate review-only current-demand support consumer. "
                                "Canonical RW_Y, main-ratio, and Evidence Mode remain blocked."
                            ),
                            "next_backend_action": (
                                "keep_consumer_review_only_or_upgrade_numerator_source_gate_and_timing_alignment_before_canonical_use"
                            ),
                        }
                    )
                else:
                    row.update(
                        {
                            "downstream_current_demand_input_enabled": "true",
                            "denominator_input_status": (
                                "pass_bounded_h8_current_demand_drag_proxy_input"
                            ),
                            "ratio_gate_status": (
                                "pass_h8_bounded_proxy_input_enabled_consumer_still_blocked"
                            ),
                            "numerator_runtime_status": (
                                "blocked_no_separate_current_demand_support_ratio_consumer"
                            ),
                            "historical_reporting_status": (
                                "blocked_canonical_rw_y_history_not_enabled"
                            ),
                            "main_ratio_status": (
                                "blocked_main_ratio_disabled_by_design"
                            ),
                            "evidence_mode_status": (
                                "blocked_evidence_mode_disabled_by_design"
                            ),
                            "exact_blocker": (
                                "The bounded h8 interval-first current-demand drag proxy is "
                                "enabled, but no separate current-demand support ratio "
                                "consumer is implemented and canonical RW_Y remains blocked."
                            ),
                            "safe_sentence": (
                                "The bounded h8 current-demand drag proxy is admitted only "
                                "as a noncanonical review input. No canonical RW_Y, "
                                "main-ratio, or Evidence Mode path is enabled."
                            ),
                            "next_backend_action": (
                                "define_separate_noncanonical_current_demand_support_ratio_consumer_or_leave_input_sealed"
                            ),
                        }
                    )
            else:
                row.update(
                    {
                        "downstream_current_demand_input_enabled": "false",
                        "denominator_input_status": "review_only_h8_candidate_not_admitted",
                        "ratio_gate_status": "blocked_h8_review_only_pending_bounded_object_admission",
                        "numerator_runtime_status": (
                            "pass_noncanonical_current_demand_support_ratio_consumer_review_only"
                            if consumer_available
                            else "blocked_no_separate_current_demand_support_ratio_consumer"
                        ),
                        "historical_reporting_status": (
                            "blocked_canonical_rw_y_history_not_enabled"
                        ),
                        "main_ratio_status": "blocked_main_ratio_disabled_by_design",
                        "evidence_mode_status": "blocked_evidence_mode_disabled_by_design",
                        "exact_blocker": status_row["exact_blocker"],
                        "safe_sentence": (
                            "Controlled LP h8 remains review-only after bounded promotion-rule "
                            "evaluation, so the noncanonical current-demand gate stays disabled "
                            "even when the separate support consumer is available."
                            if consumer_available
                            else (
                                "Controlled LP h8 remains review-only after bounded promotion-rule "
                                "evaluation, so the noncanonical current-demand gate stays disabled."
                            )
                        ),
                        "next_backend_action": status_row["next_backend_action"],
                    }
                )
        else:
            row.update(
                {
                    "downstream_current_demand_input_enabled": "false",
                    "denominator_input_status": "review_only_companion_horizon",
                    "ratio_gate_status": "blocked_companion_horizon_not_ratio_input",
                    "numerator_runtime_status": (
                        "blocked_companion_horizon_not_current_demand_input"
                    ),
                    "historical_reporting_status": (
                        "blocked_canonical_rw_y_history_not_enabled"
                    ),
                    "main_ratio_status": "blocked_main_ratio_disabled_by_design",
                    "evidence_mode_status": "blocked_evidence_mode_disabled_by_design",
                    "exact_blocker": (
                        "Only an admitted h8 controlled denominator could serve as a "
                        "non-main-ratio current-demand input in this gate."
                    ),
                    "safe_sentence": (
                        "Controlled h4 and h12 are companion horizons only; they do not "
                        "open a current-demand ratio input."
                    ),
                    "next_backend_action": "keep_h4_h12_as_companion_context_only",
                }
            )
        rows.append(row)
    return rows


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _safe_ratio(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> Decimal | None:
    if numerator is None or denominator in {None, Decimal("0")}:
        return None
    return numerator / denominator


def _log_change_pct(current: Decimal | None, previous: Decimal | None) -> float | None:
    if current is None or previous is None or current <= 0 or previous <= 0:
        return None
    return 100.0 * (math.log(float(current)) - math.log(float(previous)))


def _int_or_zero(value: object) -> int:
    try:
        return int(str(value or "0"))
    except ValueError:
        return 0


def _float_or_none(value: object) -> float | None:
    if value in {None, "", "."}:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def _decimal_or_none(value: object) -> Decimal | None:
    if value in {None, "", "."}:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _format_decimal(value: object) -> str:
    if value is None:
        return ""
    decimal_value = _decimal_or_none(value)
    if decimal_value is None:
        return ""
    quantized = decimal_value.quantize(Decimal("0.000000000001"))
    return format(quantized.normalize(), "f")


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    decimal_value = Decimal(str(value)).quantize(Decimal("0.00000001"))
    return format(decimal_value.normalize(), "f")


def _safe_t_stat(estimate: HacEstimate | None) -> float | None:
    if estimate is None or estimate.se in {None, 0.0}:
        return None
    return estimate.beta / estimate.se


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
