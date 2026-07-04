"""Fail-closed TDCSim CBO handoff reader for RateWall model inputs."""

from __future__ import annotations

import csv
import gzip
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from decimal import localcontext
from pathlib import Path
from typing import Any

from ratewall.accounting.ratewall_threshold import (
    CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
)
from ratewall.accounting.tdc_deposit_channel import (
    TdcCurrentDemandSupportInputs,
    compute_tdc_current_demand_support,
)
from ratewall.databook.model_artifact_store import (
    ArtifactManifestView,
    artifact_manifest_exists,
)
from ratewall.sources.cbo_workbook import parse_cbo_budget_projection_rows

TDCSIM_CBO_SCENARIO_RUNS_DIR = Path(
    "data/raw/ratewall_sibling_calibration/tdcsim_cbo_scenarios"
)
TDCSIM_CBO_FROZEN_DENOMINATOR_FILENAME = "frozen_denominator_by_fiscal_year.csv"
TDCSIM_CBO_FROZEN_DENOMINATOR_SCOPE = "external_frozen_by_fiscal_year"
TDCSIM_CBO_CBO_GDP_SCALED_DENOMINATOR_SCOPE = (
    "external_frozen_anchor_scaled_by_cbo_nominal_gdp_fiscal_year"
)

TDCSIM_CBO_TABLES = (
    "tdcsim_period_issuance_flows",
    "tdcsim_period_principal_flows",
    "tdcsim_period_payment_flows",
    "tdcsim_holder_stocks",
    "tdcsim_tdc_principal_route_stocks",
    "tdcsim_tdc_principal_route_stock_closure",
    "tdcsim_debt_target_bridge",
    "tdcsim_scenario_metrics",
    "tdcsim_period_tdc_summary",
    "tdcsim_period_tdc_components",
)

CBO_FISCAL_YEAR_RATIO_INPUT_FIELDS = [
    "tdcsim_cbo_ratio_input_row_id",
    "scenario_id",
    "run_id",
    "package_id",
    "source_vintage",
    "actuals_available_as_of",
    "fiscal_year",
    "period_count",
    "tdc_change_ex_overlap_bil",
    "tdc_current_demand_support_bil",
    "direct_treasury_interest_basis_bil",
    "direct_treasury_current_demand_support_bil",
    "bank_treasury_interest_basis_bil",
    "bank_treasury_current_demand_support_bil",
    "total_current_demand_support_bil",
    "frozen_denominator_bil",
    "ratewall_ratio",
    "denominator_scope",
    "denominator_invariance_status",
    "tdc_amount_basis",
    "mmf_deposit_pass_through",
    "fiscal_incidence_basis",
    "allowed_use",
    "blocked_use",
    "source_status",
    "canonical_ratio_entry",
]

CBO_SCENARIO_EFFECT_FIELDS = [
    "tdcsim_cbo_scenario_effect_row_id",
    "scenario_id",
    "baseline_scenario_id",
    "fiscal_year",
    "scenario_role",
    "scenario_label",
    "scenario_interpretation_status",
    "core_scenario_entry",
    "level_ratewall_ratio",
    "delta_ratewall_ratio_vs_baseline",
    "total_current_demand_support_bil",
    "delta_total_current_demand_support_bil",
    "tdc_current_demand_support_bil",
    "delta_tdc_current_demand_support_bil",
    "direct_treasury_current_demand_support_bil",
    "delta_direct_treasury_current_demand_support_bil",
    "bank_treasury_current_demand_support_bil",
    "delta_bank_treasury_current_demand_support_bil",
    "tdc_fiscal_flow_bil",
    "delta_tdc_fiscal_flow_bil",
    "tdc_debt_service_principal_to_du_bil",
    "delta_tdc_debt_service_principal_to_du_bil",
    "gross_principal_cash_paid_to_du_bil",
    "delta_gross_principal_cash_paid_to_du_bil",
    "du_bill_discount_interest_bil",
    "delta_du_bill_discount_interest_bil",
    "tdc_debt_service_interest_to_du_bil",
    "delta_tdc_debt_service_interest_to_du_bil",
    "tdc_auction_absorption_du_bil",
    "delta_tdc_auction_absorption_du_bil",
    "tdc_secondary_trades_bil",
    "delta_tdc_secondary_trades_bil",
    "tdc_other_bil",
    "delta_tdc_other_bil",
    "overlap_cashflow_bil",
    "delta_overlap_cashflow_bil",
    "tdc_change_ex_overlap_bil",
    "delta_tdc_change_ex_overlap_bil",
    "frozen_denominator_bil",
    "denominator_scope",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_SETTLEMENT_ACCRUAL_BRIDGE_FIELDS = [
    "tdcsim_cbo_settlement_accrual_bridge_row_id",
    "scenario_id",
    "fiscal_year",
    "bridge_family",
    "holder_sector",
    "holder_subsector",
    "instrument_type",
    "payment_type",
    "accounting_basis",
    "is_additive_to_cash_total",
    "settlement_cash_bil",
    "principal_component_bil",
    "interest_or_accrual_component_bil",
    "budget_accrual_bil",
    "ratewall_current_demand_basis_bil",
    "cbo_reconciliation_basis_bil",
    "treatment_note",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_CORE_SCENARIO_INTERPRETATION_FIELDS = [
    "tdcsim_cbo_core_scenario_interpretation_row_id",
    "scenario_id",
    "baseline_scenario_id",
    "fiscal_year",
    "point_calibration_rank",
    "scenario_role",
    "scenario_label",
    "level_ratewall_ratio",
    "delta_ratewall_ratio_vs_baseline",
    "delta_direction_vs_baseline",
    "wall_hit_status",
    "total_current_demand_support_bil",
    "delta_total_current_demand_support_bil",
    "tdc_current_demand_support_bil",
    "delta_tdc_current_demand_support_bil",
    "direct_treasury_current_demand_support_bil",
    "delta_direct_treasury_current_demand_support_bil",
    "bank_treasury_current_demand_support_bil",
    "delta_bank_treasury_current_demand_support_bil",
    "dominant_delta_support_component",
    "dominant_delta_support_component_bil",
    "denominator_bil",
    "interpretation_basis",
    "ranking_stability",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_ROUTE_STOCK_CLOSURE_FIELDS = [
    "tdcsim_cbo_route_stock_closure_row_id",
    "scenario_id",
    "fiscal_year",
    "period_start",
    "period_end",
    "route_holder_sector",
    "route_holder_subsector",
    "instrument_type",
    "maturity_bucket",
    "debt_scope",
    "opening_route_stock_bil",
    "route_face_issued_bil",
    "route_face_redeemed_bil",
    "route_stock_residual_or_indexation_bil",
    "closing_route_stock_bil",
    "closure_identity_error_bil",
    "route_stock_basis",
    "residual_basis",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_MATCHED_RESPONSE_COEFFICIENT_FIELDS = [
    "tdcsim_cbo_matched_response_coefficient_row_id",
    "fiscal_year",
    "response_axis",
    "response_axis_label",
    "x_measure",
    "x_unit",
    "outcome_name",
    "baseline_scenario_id",
    "low_scenario_id",
    "high_scenario_id",
    "baseline_x",
    "low_x",
    "high_x",
    "baseline_outcome",
    "low_outcome",
    "high_outcome",
    "low_delta_vs_baseline",
    "high_delta_vs_baseline",
    "signed_slope_per_x",
    "midpoint_outcome",
    "midpoint_delta_vs_baseline",
    "symmetry_status",
    "sample_design",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_MATCHED_PERIOD_RESPONSE_FIELDS = [
    "tdcsim_cbo_matched_period_response_row_id",
    "response_axis",
    "outcome_name",
    "period_start",
    "period_end",
    "fiscal_year",
    "lag_days_from_fiscal_year_start",
    "baseline_scenario_id",
    "low_scenario_id",
    "high_scenario_id",
    "baseline_outcome",
    "low_outcome",
    "high_outcome",
    "low_delta_vs_baseline",
    "high_delta_vs_baseline",
    "central_difference_delta",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_SCENARIO_LEVER_DIAGNOSTIC_FIELDS = [
    "tdcsim_cbo_scenario_lever_diagnostic_row_id",
    "scenario_id",
    "baseline_scenario_id",
    "fiscal_year",
    "lever_name",
    "scenario_override",
    "intended_x_measure",
    "intended_x_value",
    "response_status",
    "interpretation_status",
    "level_ratewall_ratio",
    "delta_ratewall_ratio_vs_baseline",
    "delta_total_current_demand_support_bil",
    "delta_tdc_current_demand_support_bil",
    "delta_tdc_fiscal_flow_bil",
    "delta_tdc_change_ex_overlap_bil",
    "delta_direct_treasury_current_demand_support_bil",
    "delta_bank_treasury_current_demand_support_bil",
    "delta_controlled_debt_post_issuance_bil",
    "delta_route_face_issued_bil",
    "delta_route_face_redeemed_bil",
    "delta_gross_issuance_cash_proceeds_bil",
    "delta_gross_issuance_proceeds_absorbed_by_du_bil",
    "activation_evidence",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_EMPIRICAL_TERM_PREMIUM_COMPARISON_FIELDS = [
    "tdcsim_cbo_empirical_term_premium_comparison_row_id",
    "fiscal_year",
    "issuance_direction",
    "term_premium_tier",
    "ten_year_nominal_rate_shock_bp",
    "baseline_scenario_id",
    "issuance_only_scenario_id",
    "coupled_scenario_id",
    "issuance_only_delta_ratewall_ratio",
    "coupled_delta_ratewall_ratio",
    "rate_overlay_delta_ratewall_ratio",
    "offset_fraction_of_abs_issuance_effect",
    "net_effect_fraction_remaining",
    "issuance_only_delta_total_current_demand_support_bil",
    "coupled_delta_total_current_demand_support_bil",
    "rate_overlay_delta_total_current_demand_support_bil",
    "interpretation_status",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_EMPIRICAL_SCENARIO_INTERPRETATION_FIELDS = [
    "tdcsim_cbo_empirical_scenario_interpretation_row_id",
    "fiscal_year",
    "scenario_set_role",
    "issuance_direction",
    "term_premium_tier",
    "ten_year_nominal_rate_shock_bp",
    "scenario_id",
    "baseline_scenario_id",
    "paired_issuance_only_scenario_id",
    "level_ratewall_ratio",
    "delta_ratewall_ratio_vs_baseline",
    "total_current_demand_support_bil",
    "delta_total_current_demand_support_bil",
    "delta_tdc_current_demand_support_bil",
    "delta_direct_treasury_current_demand_support_bil",
    "delta_bank_treasury_current_demand_support_bil",
    "delta_tdc_fiscal_flow_bil",
    "delta_tdc_debt_service_principal_to_du_bil",
    "delta_tdc_debt_service_interest_to_du_bil",
    "delta_tdc_auction_absorption_du_bil",
    "rate_overlay_delta_ratewall_ratio",
    "offset_fraction_of_abs_issuance_effect",
    "net_effect_fraction_remaining",
    "dominant_delta_support_component",
    "dominant_delta_support_component_bil",
    "model_interpretation",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_MODEL_SCENARIO_SUMMARY_FIELDS = [
    "tdcsim_cbo_model_scenario_summary_row_id",
    "fiscal_year",
    "summary_role",
    "comparison_group",
    "scenario_id",
    "baseline_scenario_id",
    "paired_issuance_only_scenario_id",
    "term_premium_tier",
    "ten_year_nominal_rate_shock_bp",
    "level_ratewall_ratio",
    "delta_ratewall_ratio_vs_baseline",
    "delta_total_current_demand_support_bil",
    "delta_tdc_current_demand_support_bil",
    "delta_direct_treasury_current_demand_support_bil",
    "delta_bank_treasury_current_demand_support_bil",
    "component_delta_sum_check_bil",
    "component_delta_sum_status",
    "tdc_delta_abs_contribution_share",
    "direct_treasury_delta_abs_contribution_share",
    "bank_treasury_delta_abs_contribution_share",
    "support_mechanism_profile",
    "rate_overlay_delta_ratewall_ratio",
    "offset_fraction_of_abs_issuance_effect",
    "primary_deficit_up_1pct_delta_ratewall_ratio",
    "abs_delta_vs_primary_deficit_up_1pct",
    "dominant_delta_support_component",
    "dominant_delta_support_component_bil",
    "model_interpretation",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]

CBO_MODEL_SCENARIO_BETA_CHI_ROBUSTNESS_FIELDS = [
    "tdcsim_cbo_model_scenario_beta_chi_robustness_row_id",
    "source_model_scenario_summary_row_id",
    "source_scenario_effect_row_id",
    "fiscal_year",
    "summary_role",
    "comparison_group",
    "scenario_id",
    "baseline_scenario_id",
    "paired_issuance_only_scenario_id",
    "term_premium_tier",
    "ten_year_nominal_rate_shock_bp",
    "model_interpretation",
    "tdc_materialization_beta_scenario",
    "tdc_materialization_beta",
    "deposit_current_demand_share_profile",
    "deposit_current_demand_share",
    "derived_beta_times_chi",
    "profile_is_current_point_calibration",
    "tdc_materialization_beta_source_status",
    "deposit_current_demand_share_source_status",
    "tdc_change_ex_overlap_bil",
    "baseline_tdc_change_ex_overlap_bil",
    "delta_tdc_change_ex_overlap_bil",
    "direct_treasury_current_demand_support_bil_fixed",
    "baseline_direct_treasury_current_demand_support_bil_fixed",
    "delta_direct_treasury_current_demand_support_bil_fixed",
    "bank_treasury_current_demand_support_bil_fixed",
    "baseline_bank_treasury_current_demand_support_bil_fixed",
    "delta_bank_treasury_current_demand_support_bil_fixed",
    "direct_treasury_current_demand_share_fixed",
    "bank_treasury_current_demand_share_fixed",
    "frozen_denominator_bil",
    "denominator_scope",
    "tdc_current_demand_support_bil_recomputed",
    "delta_tdc_current_demand_support_bil_recomputed",
    "total_current_demand_support_bil_recomputed",
    "delta_total_current_demand_support_bil_recomputed",
    "level_ratewall_ratio_recomputed",
    "delta_ratewall_ratio_vs_baseline_recomputed",
    "wall_hit_under_assumptions",
    "rate_overlay_delta_ratewall_ratio_recomputed",
    "offset_fraction_of_abs_issuance_effect_recomputed",
    "net_effect_fraction_remaining_recomputed",
    "primary_deficit_up_1pct_delta_ratewall_ratio_recomputed",
    "abs_delta_vs_primary_deficit_up_1pct_recomputed",
    "abs_delta_vs_current_point_primary_deficit_up_1pct",
    "delta_sign_vs_baseline_recomputed",
    "same_sign_as_current_point_calibration",
    "dominant_delta_support_component_recomputed",
    "dominant_delta_support_component_bil_recomputed",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "denominator_prior_update_allowed",
    "evidence_mode_enabled",
    "empirical_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "holder_allocation_enabled",
    "causal_financialization_claim_enabled",
]

CBO_MODEL_SCENARIO_BETA_CHI_SIGN_STABILITY_FIELDS = [
    "tdcsim_cbo_beta_chi_sign_stability_row_id",
    "fiscal_year",
    "scenario_id",
    "summary_role",
    "comparison_group",
    "point_calibration_delta_ratewall_ratio",
    "min_delta_ratewall_ratio_over_beta_chi_grid",
    "max_delta_ratewall_ratio_over_beta_chi_grid",
    "min_abs_delta_ratewall_ratio_over_beta_chi_grid",
    "max_abs_delta_ratewall_ratio_over_beta_chi_grid",
    "point_calibration_sign",
    "signs_observed_over_grid",
    "same_sign_cell_count",
    "grid_cell_count",
    "sign_stability_status",
    "zero_crossing_beta_times_chi",
    "zero_crossing_status",
    "min_abs_delta_vs_same_profile_primary_deficit_up_1pct",
    "max_abs_delta_vs_same_profile_primary_deficit_up_1pct",
    "min_abs_delta_vs_current_point_primary_deficit_up_1pct",
    "max_abs_delta_vs_current_point_primary_deficit_up_1pct",
    "dominant_component_stability_status",
    "wall_hit_any_grid_cell",
    "min_level_ratewall_ratio_over_grid",
    "max_level_ratewall_ratio_over_grid",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
]

CBO_CURVE_DENOMINATOR_INPUT_FIELDS = [
    "tdcsim_cbo_curve_denominator_input_row_id",
    "source_model_scenario_summary_row_id",
    "source_scenario_effect_row_id",
    "fiscal_year",
    "summary_role",
    "comparison_group",
    "scenario_id",
    "baseline_scenario_id",
    "paired_issuance_only_scenario_id",
    "term_premium_tier",
    "ten_year_nominal_rate_shock_bp",
    "curve_overlay_key_rate_source_id",
    "curve_overlay_key_rate_source_status",
    "curve_overlay_5y_bp",
    "curve_overlay_10y_bp",
    "curve_overlay_30y_bp",
    "curve_weight_5y",
    "curve_weight_10y",
    "curve_weight_30y",
    "curve_weight_sum_status",
    "effective_curve_overlay_bp",
    "denominator_response_model_id",
    "denominator_response_intensity",
    "denominator_response_coefficient_status",
    "frozen_denominator_bil",
    "delta_denominator_bil_from_curve",
    "moving_denominator_bil",
    "denominator_positive_guard_status",
    "total_current_demand_support_bil",
    "frozen_ratewall_ratio",
    "moving_ratewall_ratio",
    "frozen_delta_ratewall_ratio_vs_baseline",
    "moving_delta_ratewall_ratio_vs_baseline",
    "moving_minus_frozen_ratewall_ratio",
    "denominator_response_direction",
    "denominator_scope",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
    "formula_replacement_allowed",
    "causal_market_yield_estimate_enabled",
    "notes",
]

CBO_CURVE_SENSITIVE_DENOMINATOR_ASSUMPTION_BOUND_FIELDS = [
    "tdcsim_cbo_curve_sensitive_denominator_assumption_bound_row_id",
    "source_curve_denominator_input_row_id",
    "source_model_scenario_summary_row_id",
    "source_scenario_effect_row_id",
    "fiscal_year",
    "summary_role",
    "comparison_group",
    "scenario_id",
    "baseline_scenario_id",
    "paired_issuance_only_scenario_id",
    "term_premium_tier",
    "curve_overlay_key_rate_source_status",
    "curve_overlay_5y_bp",
    "curve_overlay_10y_bp",
    "curve_overlay_30y_bp",
    "curve_weight_5y",
    "curve_weight_10y",
    "curve_weight_30y",
    "curve_weight_status",
    "effective_curve_overlay_bp",
    "denominator_response_profile_tier",
    "denominator_response_profile_id",
    "denominator_response_profile_label",
    "theta_curve_relative_to_policy_anchor",
    "gamma_curve_gdp_share_per_100bp",
    "bil_per_bp_effective_curve",
    "coefficient_admission_status",
    "coefficient_source_status",
    "coefficient_empirical_claim_allowed",
    "shock_object_scope",
    "response_horizon",
    "transport_rule",
    "frozen_denominator_bil",
    "delta_denominator_bil_from_curve",
    "moving_denominator_bil",
    "denominator_positive_guard_status",
    "total_current_demand_support_bil",
    "frozen_ratewall_ratio",
    "moving_ratewall_ratio",
    "frozen_delta_ratewall_ratio_vs_baseline",
    "moving_delta_ratewall_ratio_vs_baseline",
    "moving_minus_frozen_ratewall_ratio",
    "denominator_response_direction",
    "denominator_scope",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
    "formula_replacement_allowed",
    "causal_market_yield_estimate_enabled",
    "notes",
]

CBO_MODEL_SCENARIO_INTERPRETATION_SYNTHESIS_FIELDS = [
    "tdcsim_cbo_model_scenario_interpretation_synthesis_row_id",
    "source_model_scenario_summary_row_id",
    "source_beta_chi_sign_stability_row_id",
    "fiscal_year",
    "summary_role",
    "comparison_group",
    "scenario_id",
    "baseline_scenario_id",
    "paired_issuance_only_scenario_id",
    "term_premium_tier",
    "point_calibration_delta_ratewall_ratio",
    "point_calibration_sign",
    "point_calibration_level_ratewall_ratio",
    "beta_chi_sign_stability_status",
    "beta_chi_signs_observed",
    "beta_chi_min_delta_ratewall_ratio",
    "beta_chi_max_delta_ratewall_ratio",
    "beta_chi_wall_hit_any_grid_cell",
    "curve_effective_overlay_bp",
    "denominator_bound_theta_values",
    "denominator_bound_min_delta_denominator_bil",
    "denominator_bound_max_delta_denominator_bil",
    "denominator_bound_min_moving_delta_ratewall_ratio_vs_baseline",
    "denominator_bound_max_moving_delta_ratewall_ratio_vs_baseline",
    "denominator_bound_signs_observed",
    "denominator_bound_sign_stability_status",
    "selected_denominator_response_profile_id",
    "selected_denominator_response_coefficient",
    "selected_denominator_response_coefficient_unit",
    "selected_delta_denominator_bil",
    "selected_moving_denominator_bil",
    "selected_moving_ratewall_ratio",
    "selected_moving_delta_ratewall_ratio_vs_baseline",
    "selected_denominator_response_status",
    "primary_deficit_up_1pct_delta_ratewall_ratio",
    "abs_delta_vs_primary_deficit_up_1pct",
    "primary_deficit_scale_bucket",
    "dominant_delta_support_component",
    "dominant_delta_support_component_bil",
    "component_delta_sum_check_bil",
    "component_delta_sum_status",
    "tdc_delta_abs_contribution_share",
    "direct_treasury_delta_abs_contribution_share",
    "bank_treasury_delta_abs_contribution_share",
    "support_mechanism_profile",
    "model_interpretation",
    "final_interpretation",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
    "formula_replacement_allowed",
    "causal_market_yield_estimate_enabled",
]

CBO_CURVE_DENOMINATOR_EMPIRICAL_STATUS_FIELDS = [
    "tdcsim_cbo_curve_denominator_empirical_status_row_id",
    "source_model_scenario_interpretation_synthesis_row_id",
    "fiscal_year",
    "summary_role",
    "comparison_group",
    "scenario_id",
    "baseline_scenario_id",
    "term_premium_tier",
    "curve_effective_overlay_bp",
    "point_calibration_delta_ratewall_ratio",
    "denominator_bound_theta_values",
    "denominator_bound_min_delta_denominator_bil",
    "denominator_bound_max_delta_denominator_bil",
    "denominator_bound_min_moving_delta_ratewall_ratio_vs_baseline",
    "denominator_bound_max_moving_delta_ratewall_ratio_vs_baseline",
    "selected_denominator_response_profile_id",
    "selected_denominator_response_coefficient",
    "selected_moving_denominator_bil",
    "selected_moving_delta_ratewall_ratio_vs_baseline",
    "selected_denominator_response_status",
    "empirical_denominator_coefficient_status",
    "literature_calibrated_coefficient_status",
    "econometric_estimate_status",
    "admitted_curve_response_coefficient",
    "admitted_curve_response_coefficient_unit",
    "admitted_response_horizon",
    "current_denominator_profile_status",
    "current_denominator_profile_used_for_scenarios",
    "linked_assumption_bound_row_ids",
    "candidate_econometric_surface_status",
    "candidate_econometric_surface_blocker",
    "denominator_model_decision",
    "next_model_requirement",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
    "formula_replacement_allowed",
    "causal_market_yield_estimate_enabled",
]

CBO_MODEL_SCENARIO_MATERIALITY_CLASSIFICATION_FIELDS = [
    "tdcsim_cbo_model_scenario_materiality_classification_row_id",
    "source_model_scenario_interpretation_synthesis_row_id",
    "fiscal_year",
    "materiality_rank_abs_delta",
    "scenario_family",
    "summary_role",
    "comparison_group",
    "scenario_id",
    "baseline_scenario_id",
    "point_calibration_delta_ratewall_ratio",
    "point_calibration_abs_delta_ratewall_ratio",
    "point_calibration_sign",
    "primary_deficit_up_1pct_delta_ratewall_ratio",
    "abs_delta_vs_primary_deficit_up_1pct",
    "materiality_tier_vs_primary_deficit_up_1pct",
    "beta_chi_sign_stability_status",
    "beta_chi_robustness_class",
    "denominator_bound_sign_stability_status",
    "denominator_bound_sensitivity_class",
    "curve_effective_overlay_bp",
    "denominator_recompute_readiness",
    "dominant_delta_support_component",
    "dominant_delta_support_component_bil",
    "support_mechanism_profile",
    "component_delta_sum_status",
    "model_interpretation",
    "final_interpretation",
    "model_relevance_class",
    "recommended_use",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
    "formula_replacement_allowed",
    "causal_market_yield_estimate_enabled",
]

CBO_CANONICAL_ENTRY_DECISION_FIELDS = [
    "tdcsim_cbo_canonical_entry_decision_row_id",
    "fiscal_year",
    "canonical_entry_scope",
    "baseline_scenario_id",
    "baseline_ratewall_ratio",
    "baseline_total_current_demand_support_bil",
    "frozen_denominator_bil",
    "denominator_scope",
    "baseline_source_status",
    "baseline_mmf_deposit_pass_through",
    "canonical_forward_baseline_entry",
    "runtime_canonical_ratio_object_id",
    "runtime_canonical_replacement_allowed",
    "runtime_canonical_replacement_decision",
    "scenario_rows_reviewed_count",
    "nonbaseline_rows_entering_forward_baseline_count",
    "scenario_comparison_entry_decision",
    "denominator_decision",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
    "formula_replacement_allowed",
    "causal_market_yield_estimate_enabled",
]

BETA_CHI_ROBUSTNESS_BETA_PROFILES = (
    (
        "normal_forward_lower95",
        Decimal("0.11550407481239519"),
        "ea_tdc_import_contract::normal_forward::lower95",
    ),
    (
        "tga_drawdown_liquidity_event",
        Decimal("0.16074367600134148"),
        "ea_tdc_import_contract::tga_drawdown_liquidity_event::point",
    ),
    (
        "pandemic_exclusion_drop_2020",
        Decimal("0.2478871263682468"),
        "ea_tdc_import_contract::pandemic_exclusion_drop_2020::point",
    ),
    (
        "low_rate_liquidity_state",
        Decimal("0.3199260352703432"),
        "ea_tdc_import_contract::low_rate_liquidity_state::point",
    ),
    (
        "normal_forward",
        Decimal("0.34201759129420367"),
        "ea_tdc_import_contract::normal_forward::point",
    ),
    (
        "high_liquidity_event",
        Decimal("0.38586509440810274"),
        "ea_tdc_import_contract::high_liquidity_event::point",
    ),
    (
        "pandemic_exclusion_drop_2020q1_2021q4",
        Decimal("0.4462798011574685"),
        "ea_tdc_import_contract::pandemic_exclusion_drop_2020q1_2021q4::point",
    ),
    (
        "latest_rolling_persistence",
        Decimal("0.5307509589554447"),
        "ea_tdc_import_contract::latest_rolling_persistence::point",
    ),
    (
        "normal_forward_upper95",
        Decimal("0.5685311077760121"),
        "ea_tdc_import_contract::normal_forward::upper95",
    ),
    (
        "pooled_full_sample",
        Decimal("0.6163494354563133"),
        "ea_tdc_import_contract::pooled_full_sample::point_review_only",
    ),
    (
        "pandemic_exclusion_drop_2021",
        Decimal("0.7431033707535825"),
        "ea_tdc_import_contract::pandemic_exclusion_drop_2021::point",
    ),
)
BETA_CHI_ROBUSTNESS_CHI_PROFILES = (
    ("conservative", Decimal("0.03")),
    ("base", Decimal("0.07")),
    ("demand_active", Decimal("0.12")),
)

MODEL_SUMMARY_HOLDER_SCENARIOS = (
    (
        "tdcsim_private_holder_low_v1",
        "private_holder_low_reserve_user_private_route_comparator",
    ),
    (
        "tdcsim_private_holder_high_v1",
        "private_holder_high_reserve_user_private_route_comparator",
    ),
    (
        "tdcsim_holder_source_reserve_user_absorption_v1",
        "holder_source_reserve_user_absorption_low_private_comparator",
    ),
    (
        "tdcsim_holder_source_current_mix_v1",
        "holder_source_current_mix_central_comparator",
    ),
    (
        "tdcsim_holder_source_domestic_nonbank_absorption_v1",
        "holder_source_domestic_nonbank_absorption_high_private_comparator",
    ),
)

MODEL_SUMMARY_RATE_SCENARIOS = (
    (
        "tdcsim_rate_down_25bp_v1",
        "parallel_nominal_rate_down_25bp_comparator",
    ),
    (
        "tdcsim_rate_up_25bp_v1",
        "parallel_nominal_rate_up_25bp_comparator",
    ),
)

MODEL_SUMMARY_MMF_SCENARIOS = (
    (
        "tdcsim_mmf_pass_through_90_v1",
        "mmf_pass_through_low_90_comparator",
    ),
    (
        "tdcsim_mmf_pass_through_99_v1",
        "mmf_pass_through_high_99_comparator",
    ),
)

MODEL_SUMMARY_COMBINED_SCENARIOS = (
    (
        "tdcsim_combo_high_pressure_v1",
        "combined_high_pressure_deficit_reserve_shorter_rate_down",
    ),
    (
        "tdcsim_combo_lower_pressure_v1",
        "combined_lower_pressure_deficit_down_domestic_longer_rate_up",
    ),
    (
        "tdcsim_combo_fiscal_stress_market_offset_v1",
        "combined_fiscal_stress_with_market_offset",
    ),
    (
        "tdcsim_combo_fiscal_relief_holder_stress_v1",
        "combined_fiscal_relief_with_holder_stress",
    ),
)

EMPIRICAL_SCENARIO_INTERPRETATION_SPECS = (
    {
        "scenario_set_role": "baseline_anchor",
        "issuance_direction": "baseline",
        "term_premium_tier": "none",
        "ten_year_nominal_rate_shock_bp": Decimal("0"),
        "scenario_id": "cbo_baseline_noop_v1",
        "paired_issuance_only_scenario_id": "",
        "model_interpretation": "cbo_baseline_anchor",
    },
    {
        "scenario_set_role": "issuance_only_control",
        "issuance_direction": "shorter",
        "term_premium_tier": "none",
        "ten_year_nominal_rate_shock_bp": Decimal("0"),
        "scenario_id": "tdcsim_issuance_empirical_shorter_uncoupled_v1",
        "paired_issuance_only_scenario_id": "tdcsim_issuance_empirical_shorter_uncoupled_v1",
        "model_interpretation": "shorter_issuance_accounting_effect_before_rate_overlay",
    },
    {
        "scenario_set_role": "issuance_only_control",
        "issuance_direction": "longer",
        "term_premium_tier": "none",
        "ten_year_nominal_rate_shock_bp": Decimal("0"),
        "scenario_id": "tdcsim_issuance_empirical_longer_uncoupled_v1",
        "paired_issuance_only_scenario_id": "tdcsim_issuance_empirical_longer_uncoupled_v1",
        "model_interpretation": "longer_issuance_accounting_effect_before_rate_overlay",
    },
)

EMPIRICAL_TERM_PREMIUM_COMPARISONS = (
    {
        "issuance_direction": "shorter",
        "issuance_only_scenario_id": "tdcsim_issuance_empirical_shorter_uncoupled_v1",
        "coupled_scenarios": (
            (
                "conservative",
                Decimal("-5"),
                "tdcsim_issuance_empirical_shorter_termprem_down_cons_v1",
            ),
            (
                "central",
                Decimal("-8"),
                "tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            ),
            (
                "high",
                Decimal("-10"),
                "tdcsim_issuance_empirical_shorter_termprem_down_high_v1",
            ),
        ),
    },
    {
        "issuance_direction": "longer",
        "issuance_only_scenario_id": "tdcsim_issuance_empirical_longer_uncoupled_v1",
        "coupled_scenarios": (
            (
                "conservative",
                Decimal("5"),
                "tdcsim_issuance_empirical_longer_termprem_up_cons_v1",
            ),
            (
                "central",
                Decimal("8"),
                "tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            ),
            (
                "high",
                Decimal("10"),
                "tdcsim_issuance_empirical_longer_termprem_up_high_v1",
            ),
        ),
    },
)

MATCHED_RESPONSE_AXES = (
    {
        "response_axis": "nominal_rate_parallel",
        "response_axis_label": "Nominal-rate parallel +/-25bp",
        "x_measure": "parallel_rate_shock_bp",
        "x_unit": "basis_points",
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "scenario_ids": (
            "tdcsim_rate_down_25bp_v1",
            "tdcsim_rate_up_25bp_v1",
        ),
        "x_values": {
            "cbo_baseline_noop_v1": Decimal("0"),
            "tdcsim_rate_down_25bp_v1": Decimal("-25"),
            "tdcsim_rate_up_25bp_v1": Decimal("25"),
        },
    },
    {
        "response_axis": "issuance_maturity_mix",
        "response_axis_label": "Shorter/longer issuance WAM",
        "x_measure": "fy_weighted_average_issuance_maturity_years",
        "x_unit": "years",
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "scenario_ids": (
            "tdcsim_issuance_shorter_v1",
            "tdcsim_issuance_longer_v1",
        ),
    },
    {
        "response_axis": "source_grounded_private_du_issuance_share",
        "response_axis_label": "Source-grounded private DU issuance absorption share",
        "x_measure": "fy_du_absorbed_issuance_proceeds_share",
        "x_unit": "share",
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "scenario_ids": (
            "tdcsim_holder_source_reserve_user_absorption_v1",
            "tdcsim_holder_source_domestic_nonbank_absorption_v1",
        ),
    },
    {
        "response_axis": "mmf_deposit_pass_through",
        "response_axis_label": "MMF deposit pass-through",
        "x_measure": "mmf_deposit_pass_through",
        "x_unit": "share",
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "scenario_ids": (
            "tdcsim_mmf_pass_through_90_v1",
            "tdcsim_mmf_pass_through_99_v1",
        ),
        "x_values": {
            "cbo_baseline_noop_v1": Decimal("0.97"),
            "tdcsim_mmf_pass_through_90_v1": Decimal("0.90"),
            "tdcsim_mmf_pass_through_99_v1": Decimal("0.99"),
        },
    },
    {
        "response_axis": "primary_deficit_scale",
        "response_axis_label": "Primary-deficit scale +/-1pct",
        "x_measure": "primary_deficit_scale",
        "x_unit": "scale",
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "scenario_ids": (
            "tdcsim_primary_deficit_down_1pct_v1",
            "tdcsim_primary_deficit_up_1pct_v1",
        ),
        "x_values": {
            "cbo_baseline_noop_v1": Decimal("1.00"),
            "tdcsim_primary_deficit_down_1pct_v1": Decimal("0.99"),
            "tdcsim_primary_deficit_up_1pct_v1": Decimal("1.01"),
        },
    },
)

SCENARIO_LEVER_DIAGNOSTICS = (
    {
        "scenario_id": "tdcsim_primary_deficit_up_1pct_v1",
        "lever_name": "primary_deficit",
        "intended_x_measure": "primary_deficit_scale",
        "intended_x_value": "1.01",
    },
    {
        "scenario_id": "tdcsim_operating_cash_inflation_beta_50_v1",
        "lever_name": "operating_cash",
        "intended_x_measure": "operating_cash_inflation_beta",
        "intended_x_value": "0.5",
    },
    {
        "scenario_id": "tdcsim_fed_holdings_scale_1_v1",
        "lever_name": "fed_holdings",
        "intended_x_measure": "fed_holdings_scale",
        "intended_x_value": "1.0",
    },
)

_SCENARIO_INTERPRETATION_BY_ID = {
    "cbo_baseline_noop_v1": (
        "baseline",
        "CBO baseline",
        "core",
        "true",
    ),
    "cbo_rates_inflation_frn_tips_v1": (
        "joint_macro_stress",
        "Joint nominal-rate, inflation, FRN and TIPS stress",
        "diagnostic_only_not_one_factor",
        "false",
    ),
    "cbo_issuance_maturity_mix_v1": (
        "mixed_issuance_bundle",
        "Longish mixed-issuance bundle",
        "diagnostic_drop_from_core",
        "false",
    ),
    "cbo_sector_holders_v1": (
        "high_private_new_issuance",
        "High-Private new-issuance allocation",
        "core_stress",
        "true",
    ),
    "cbo_fiscal_fed_cash_v1": (
        "fiscal_incidence_cash_composite",
        "Fiscal/incidence/cash composite",
        "split_required_not_one_factor",
        "false",
    ),
    "tdcsim_rate_down_25bp_v1": (
        "rate_down_sensitivity",
        "Nominal-rate-down linked-FRN sensitivity",
        "core_provisional",
        "true",
    ),
    "tdcsim_rate_up_25bp_v1": (
        "rate_up_sensitivity",
        "Nominal-rate-up linked-FRN sensitivity",
        "core_provisional",
        "true",
    ),
    "tdcsim_issuance_shorter_v1": (
        "short_duration_issuance_bundle",
        "Short-duration issuance bundle",
        "core_stress",
        "true",
    ),
    "tdcsim_issuance_longer_v1": (
        "long_duration_issuance_bundle",
        "Long-duration issuance bundle",
        "core_stress",
        "true",
    ),
    "tdcsim_private_holder_high_v1": (
        "high_private_new_issuance",
        "High-Private new-issuance allocation",
        "core_stress",
        "true",
    ),
    "tdcsim_private_holder_low_v1": (
        "low_private_new_issuance",
        "Low-Private new-issuance allocation",
        "core_stress",
        "true",
    ),
    "tdcsim_holder_source_current_mix_v1": (
        "source_grounded_current_holder_mix",
        "Source-grounded current holder mix",
        "core_source_grounded_assumption",
        "true",
    ),
    "tdcsim_holder_source_reserve_user_absorption_v1": (
        "source_grounded_reserve_user_absorption",
        "Source-grounded reserve-user absorption holder mix",
        "core_source_grounded_assumption",
        "true",
    ),
    "tdcsim_holder_source_domestic_nonbank_absorption_v1": (
        "source_grounded_domestic_nonbank_absorption",
        "Source-grounded domestic-nonbank absorption holder mix",
        "core_source_grounded_assumption",
        "true",
    ),
    "tdcsim_mmf_pass_through_90_v1": (
        "low_mmf_deposit_pass_through",
        "Low MMF deposit pass-through",
        "core_stress",
        "true",
    ),
    "tdcsim_mmf_pass_through_99_v1": (
        "high_mmf_deposit_pass_through",
        "High MMF deposit pass-through",
        "core_stress",
        "true",
    ),
    "tdcsim_issuance_empirical_shorter_uncoupled_v1": (
        "empirical_shorter_issuance_control",
        "Empirical shorter issuance control",
        "core_empirical_control",
        "true",
    ),
    "tdcsim_issuance_empirical_longer_uncoupled_v1": (
        "empirical_longer_issuance_control",
        "Empirical longer issuance control",
        "core_empirical_control",
        "true",
    ),
    "tdcsim_issuance_empirical_shorter_termprem_down_cons_v1": (
        "empirical_shorter_issuance_term_premium_conservative",
        "Empirical shorter issuance plus conservative long-rate decline",
        "core_empirical_coupled_scenario",
        "true",
    ),
    "tdcsim_issuance_empirical_shorter_termprem_down_central_v1": (
        "empirical_shorter_issuance_term_premium_central",
        "Empirical shorter issuance plus central long-rate decline",
        "core_empirical_coupled_scenario",
        "true",
    ),
    "tdcsim_issuance_empirical_shorter_termprem_down_high_v1": (
        "empirical_shorter_issuance_term_premium_high",
        "Empirical shorter issuance plus high long-rate decline",
        "core_empirical_coupled_scenario",
        "true",
    ),
    "tdcsim_issuance_empirical_longer_termprem_up_cons_v1": (
        "empirical_longer_issuance_term_premium_conservative",
        "Empirical longer issuance plus conservative long-rate rise",
        "core_empirical_coupled_scenario",
        "true",
    ),
    "tdcsim_issuance_empirical_longer_termprem_up_central_v1": (
        "empirical_longer_issuance_term_premium_central",
        "Empirical longer issuance plus central long-rate rise",
        "core_empirical_coupled_scenario",
        "true",
    ),
    "tdcsim_issuance_empirical_longer_termprem_up_high_v1": (
        "empirical_longer_issuance_term_premium_high",
        "Empirical longer issuance plus high long-rate rise",
        "core_empirical_coupled_scenario",
        "true",
    ),
    "tdcsim_combo_high_pressure_v1": (
        "combined_high_pressure",
        "Combined high-pressure scenario",
        "core_combined_composite_assumption",
        "true",
    ),
    "tdcsim_combo_lower_pressure_v1": (
        "combined_lower_pressure",
        "Combined lower-pressure scenario",
        "core_combined_composite_assumption",
        "true",
    ),
    "tdcsim_combo_fiscal_stress_market_offset_v1": (
        "combined_fiscal_stress_market_offset",
        "Combined fiscal stress with market offset",
        "core_combined_composite_assumption",
        "true",
    ),
    "tdcsim_combo_fiscal_relief_holder_stress_v1": (
        "combined_fiscal_relief_holder_stress",
        "Combined fiscal relief with holder stress",
        "core_combined_composite_assumption",
        "true",
    ),
    "ratewall_rate_down_25bp_v1": (
        "rate_down_sensitivity",
        "Nominal-rate-down linked-FRN sensitivity",
        "core_provisional",
        "true",
    ),
    "ratewall_shorter_issuance_v1": (
        "short_duration_issuance_bundle",
        "Short-duration issuance bundle",
        "core_stress_not_pure_wam",
        "true",
    ),
    "ratewall_longer_issuance_v1": (
        "long_duration_issuance_bundle",
        "Long-duration issuance bundle",
        "core_stress_not_pure_wam",
        "true",
    ),
    "ratewall_holder_away_private_v1": (
        "low_private_new_issuance",
        "Low-Private new-issuance allocation",
        "core_stress",
        "true",
    ),
}

COMMON_METADATA_FIELDS = {
    "schema_version",
    "scenario_id",
    "run_id",
    "package_id",
    "source_vintage",
    "actuals_available_as_of",
    "scenario_config_sha256",
    "compiled_inputs_digest",
    "mmf_deposit_pass_through",
    "mmf_deposit_pass_through_status",
    "fiscal_incidence_policy_id",
    "fiscal_incidence_basis",
    "fiscal_incidence_du_share",
    "fiscal_incidence_ru_share",
    "fiscal_incidence_foreign_share",
    "fiscal_incidence_other_share",
}

TABLE_REQUIRED_FIELDS: dict[str, set[str]] = {
    "tdcsim_period_issuance_flows": {
        "period_start",
        "period_end",
        "flow_id",
        "security_id",
        "holder_sector",
        "holder_subsector",
        "instrument_type",
        "maturity_bucket",
        "face_issued_bil",
        "cash_proceeds_bil",
    },
    "tdcsim_period_principal_flows": {
        "period_start",
        "period_end",
        "flow_id",
        "security_id",
        "holder_sector",
        "holder_subsector",
        "instrument_type",
        "maturity_bucket",
        "face_redeemed_bil",
        "principal_redeemed_bil",
        "cash_paid_bil",
    },
    "tdcsim_period_payment_flows": {
        "period_start",
        "period_end",
        "flow_id",
        "security_id",
        "holder_sector",
        "holder_subsector",
        "instrument_type",
        "maturity_bucket",
        "payment_type",
        "accounting_basis",
        "amount_bil",
        "is_additive_to_cash_total",
    },
    "tdcsim_holder_stocks": {
        "date",
        "holder_sector",
        "holder_subsector",
        "instrument_type",
        "maturity_bucket",
        "debt_held_bil",
        "valuation_basis",
        "debt_scope",
    },
    "tdcsim_tdc_principal_route_stocks": {
        "date",
        "route_holder_sector",
        "route_holder_subsector",
        "instrument_type",
        "maturity_bucket",
        "route_debt_held_bil",
        "debt_scope",
        "route_stock_basis",
    },
    "tdcsim_tdc_principal_route_stock_closure": {
        "period_start",
        "period_end",
        "route_holder_sector",
        "route_holder_subsector",
        "instrument_type",
        "maturity_bucket",
        "debt_scope",
        "opening_route_stock_bil",
        "route_face_issued_bil",
        "route_face_redeemed_bil",
        "route_stock_residual_or_indexation_bil",
        "closing_route_stock_bil",
        "closure_identity_error_bil",
        "route_stock_basis",
        "residual_basis",
    },
    "tdcsim_debt_target_bridge": {
        "date",
        "cbo_public_debt_target_bil",
        "controlled_public_marketable_target_bil",
        "controlled_debt_pre_issuance_bil",
        "face_issued_bil",
        "face_retired_bil",
        "controlled_debt_post_issuance_bil",
        "target_error_bil",
        "funding_mode",
    },
    "tdcsim_scenario_metrics": {
        "date",
        "new_issuance_wam_years",
        "outstanding_controlled_wam_years",
        "new_issuance_bill_share",
        "outstanding_controlled_bill_share",
        "new_issuance_short_maturity_share",
        "outstanding_controlled_short_maturity_share",
    },
    "tdcsim_period_tdc_summary": {
        "period_start",
        "period_end",
        "tdc_change_bil",
        "tdc_fiscal_flow_bil",
        "tdc_debt_service_bil",
        "tdc_auction_absorption_du_bil",
        "tdc_secondary_trades_bil",
        "tdc_other_bil",
        "overlap_cashflow_bil",
        "tdc_change_ex_overlap_bil",
        "component_sum_bil",
        "component_sum_error_bil",
        "tdc_amount_basis",
        "overlap_policy",
    },
    "tdcsim_period_tdc_components": {
        "period_start",
        "period_end",
        "component_id",
        "component_key",
        "component_family",
        "holder_sector",
        "holder_subsector",
        "instrument_type",
        "payment_type",
        "accounting_basis",
        "amount_bil",
        "is_additive_to_tdc_change",
        "enters_direct_interest_support",
        "enters_tdc_deposit_support_default",
        "tdc_amount_basis",
        "overlap_policy",
    },
}

EXPECTED_TDC_AMOUNT_BASIS = "post_mmf_route_pass_through_pre_ratewall_beta_chi"
EXPECTED_TDC_OVERLAP_POLICY = (
    "domestic_nonbank_nominal_interest_components_enter_direct_support_not_default_"
    "tdc_support"
)
DEFAULT_TDC_BETA = Decimal("0.34201759129420367")
DEFAULT_TDC_DEPOSIT_CURRENT_DEMAND_SHARE = Decimal("0.07")
DEFAULT_DIRECT_TREASURY_CURRENT_DEMAND_SHARE = Decimal("0.10")
DEFAULT_BANK_TREASURY_CURRENT_DEMAND_SHARE = Decimal("0.01")
DIRECT_SUPPORT_PAYMENT_TYPES = {
    "bill_discount",
    "bill_discount_interest",
    "fixed_coupon",
    "coupon_interest",
    "frn_interest",
    "tips_coupon",
    "tips_coupon_interest",
}
_ANNUAL_RESPONSE_OUTCOMES = (
    "ratewall_ratio",
    "total_current_demand_support_bil",
    "tdc_current_demand_support_bil",
    "direct_treasury_current_demand_support_bil",
    "bank_treasury_current_demand_support_bil",
)
_PERIOD_RESPONSE_OUTCOMES = (
    "total_current_demand_support_bil",
    "tdc_current_demand_support_bil",
    "direct_treasury_current_demand_support_bil",
    "bank_treasury_current_demand_support_bil",
)
_LEVER_DELTA_FIELDS = (
    "ratewall_ratio",
    "total_current_demand_support_bil",
    "tdc_current_demand_support_bil",
    "tdc_fiscal_flow_bil",
    "tdc_change_ex_overlap_bil",
    "direct_treasury_current_demand_support_bil",
    "bank_treasury_current_demand_support_bil",
    "controlled_debt_post_issuance_bil",
    "route_face_issued_bil",
    "route_face_redeemed_bil",
    "gross_issuance_cash_proceeds_bil",
    "gross_issuance_proceeds_absorbed_by_du_bil",
)
_LEVER_ACTIVE_TOLERANCE = Decimal("0.000000001")


class TdcsimCboContractError(ValueError):
    """Raised when a TDCSim CBO handoff package cannot be trusted."""


@dataclass(frozen=True)
class TdcsimCboRun:
    """Loaded TDCSim CBO handoff package."""

    root: Path
    outputs_dir: Path
    manifest: Mapping[str, Any]
    metadata: Mapping[str, str]
    tables: Mapping[str, tuple[Mapping[str, str], ...]]


@dataclass(frozen=True)
class CboNumeratorProfile:
    """RateWall conversion assumptions applied after TDCSim export."""

    tdc_materialization_beta: Decimal = DEFAULT_TDC_BETA
    tdc_deposit_current_demand_share: Decimal = DEFAULT_TDC_DEPOSIT_CURRENT_DEMAND_SHARE
    direct_treasury_current_demand_share: Decimal = (
        DEFAULT_DIRECT_TREASURY_CURRENT_DEMAND_SHARE
    )
    bank_treasury_current_demand_share: Decimal = DEFAULT_BANK_TREASURY_CURRENT_DEMAND_SHARE


@dataclass(frozen=True)
class CboFiscalYearNumerator:
    """Annual RateWall numerator inputs assembled from one TDCSim CBO run."""

    fiscal_year: int
    scenario_id: str
    period_count: int
    tdc_change_ex_overlap_bil: Decimal
    tdc_current_demand_support_bil: Decimal
    direct_treasury_interest_basis_bil: Decimal
    direct_treasury_current_demand_support_bil: Decimal
    bank_treasury_interest_basis_bil: Decimal
    bank_treasury_current_demand_support_bil: Decimal
    total_current_demand_support_bil: Decimal
    tdc_amount_basis: str
    denominator_scope: str = "external_frozen_by_fiscal_year"


@dataclass(frozen=True)
class CboRatioInput:
    """Numerator plus frozen denominator for a fiscal year."""

    fiscal_year: int
    scenario_id: str
    total_current_demand_support_bil: Decimal
    frozen_denominator: Decimal
    ratio: Decimal
    denominator_scope: str = TDCSIM_CBO_FROZEN_DENOMINATOR_SCOPE


@dataclass(frozen=True)
class CboDenominatorBridge:
    """Fiscal-year denominator map plus explicit source/scope labels."""

    denominator_by_fiscal_year: Mapping[int, Decimal]
    denominator_scope: str
    denominator_invariance_status: str


@dataclass(frozen=True)
class CboPeriodSupport:
    """One period's RateWall support components assembled from TDCSim rows."""

    fiscal_year: int
    period_start: str
    period_end: str
    scenario_id: str
    tdc_current_demand_support_bil: Decimal
    direct_treasury_current_demand_support_bil: Decimal
    bank_treasury_current_demand_support_bil: Decimal
    total_current_demand_support_bil: Decimal


def load_tdcsim_cbo_run(
    run_dir: str | Path,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
    tolerance: Decimal = Decimal("0.000000001"),
) -> TdcsimCboRun:
    """Load and validate a TDCSim CBO handoff package."""

    root = Path(run_dir)
    outputs_dir = root / "outputs" if (root / "outputs").is_dir() else root
    manifest = _read_manifest(root)
    tables = {name: tuple(_read_table(outputs_dir, name)) for name in TDCSIM_CBO_TABLES}
    metadata = _validate_handoff_tables(
        tables,
        manifest,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        tolerance=tolerance,
    )
    return TdcsimCboRun(
        root=root,
        outputs_dir=outputs_dir,
        manifest=manifest,
        metadata=metadata,
        tables=tables,
    )


def fiscal_year_for_date(value: str | date) -> int:
    """Return the federal fiscal year containing the date."""

    parsed = value if isinstance(value, date) else date.fromisoformat(value)
    return parsed.year + 1 if parsed.month >= 10 else parsed.year


def fiscal_year_coverage(run: TdcsimCboRun, fiscal_year: int) -> tuple[date, date]:
    """Return the period coverage for rows assigned to one fiscal year."""

    rows = _rows_for_fiscal_year(run.tables["tdcsim_period_tdc_summary"], fiscal_year)
    if not rows:
        raise TdcsimCboContractError(f"no TDC summary rows for FY{fiscal_year}")
    starts = [date.fromisoformat(row["period_start"]) for row in rows]
    ends = [date.fromisoformat(row["period_end"]) for row in rows]
    return min(starts), max(ends)


def require_complete_fiscal_year(run: TdcsimCboRun, fiscal_year: int) -> None:
    """Fail unless the TDCSim package covers a full federal fiscal year."""

    start, end = fiscal_year_coverage(run, fiscal_year)
    required_start = date(fiscal_year - 1, 10, 1)
    required_end = date(fiscal_year, 9, 30)
    if start > required_start or end < required_end:
        raise TdcsimCboContractError(
            f"FY{fiscal_year} coverage is incomplete: "
            f"{start.isoformat()} to {end.isoformat()}"
        )


def assemble_cbo_fiscal_year_numerator(
    run: TdcsimCboRun,
    fiscal_year: int,
    *,
    profile: CboNumeratorProfile = CboNumeratorProfile(),
    require_complete_year: bool = True,
) -> CboFiscalYearNumerator:
    """Assemble one annual numerator row from TDCSim CBO handoff tables."""

    if require_complete_year:
        require_complete_fiscal_year(run, fiscal_year)

    summary_rows = _rows_for_fiscal_year(
        run.tables["tdcsim_period_tdc_summary"],
        fiscal_year,
    )
    tdc_change_ex_overlap = sum(
        (_decimal(row["tdc_change_ex_overlap_bil"]) for row in summary_rows),
        Decimal("0"),
    )
    tdc_support = compute_tdc_current_demand_support(
        TdcCurrentDemandSupportInputs(
            tdc_change_ex_overlap_bil=tdc_change_ex_overlap,
            tdc_materialization_beta=profile.tdc_materialization_beta,
            deposit_current_demand_share=profile.tdc_deposit_current_demand_share,
        )
    )
    direct_interest = _sum_components(
        run.tables["tdcsim_period_tdc_components"],
        fiscal_year,
        direct_interest=True,
        holder_sector="Private",
        holder_subsector="domestic_nonbank_deposit_funded",
    )
    bank_interest = _sum_payment_flows(
        run.tables["tdcsim_period_payment_flows"],
        fiscal_year,
        holder_sector="Banks",
    )
    direct_support = direct_interest * profile.direct_treasury_current_demand_share
    bank_support = bank_interest * profile.bank_treasury_current_demand_share
    tdc_current_support = _decimal(tdc_support["tdc_current_demand_support_bil"])
    return CboFiscalYearNumerator(
        fiscal_year=fiscal_year,
        scenario_id=run.metadata["scenario_id"],
        period_count=len(summary_rows),
        tdc_change_ex_overlap_bil=tdc_change_ex_overlap,
        tdc_current_demand_support_bil=tdc_current_support,
        direct_treasury_interest_basis_bil=direct_interest,
        direct_treasury_current_demand_support_bil=direct_support,
        bank_treasury_interest_basis_bil=bank_interest,
        bank_treasury_current_demand_support_bil=bank_support,
        total_current_demand_support_bil=tdc_current_support
        + direct_support
        + bank_support,
        tdc_amount_basis=EXPECTED_TDC_AMOUNT_BASIS,
    )


def attach_frozen_denominators(
    rows: Iterable[CboFiscalYearNumerator],
    denominator_by_fiscal_year: Mapping[int, Decimal | str | int | float],
    *,
    denominator_scope: str = TDCSIM_CBO_FROZEN_DENOMINATOR_SCOPE,
) -> tuple[CboRatioInput, ...]:
    """Attach an externally supplied fiscal-year denominator to numerator rows."""

    ratio_rows: list[CboRatioInput] = []
    for row in rows:
        if row.fiscal_year not in denominator_by_fiscal_year:
            raise TdcsimCboContractError(
                f"missing frozen denominator for FY{row.fiscal_year}"
            )
        denominator = _decimal(denominator_by_fiscal_year[row.fiscal_year])
        if denominator <= 0:
            raise TdcsimCboContractError(
                f"frozen denominator must be positive for FY{row.fiscal_year}"
            )
        ratio_rows.append(
            CboRatioInput(
                fiscal_year=row.fiscal_year,
                scenario_id=row.scenario_id,
                total_current_demand_support_bil=row.total_current_demand_support_bil,
                frozen_denominator=denominator,
                ratio=row.total_current_demand_support_bil / denominator,
                denominator_scope=denominator_scope,
            )
        )
    return tuple(ratio_rows)


def tdcsim_cbo_fiscal_year_ratio_input_rows(
    run_dirs: Iterable[str | Path],
    *,
    fiscal_years: Iterable[int],
    denominator_by_fiscal_year: Mapping[int, Decimal | str | int | float],
    profile: CboNumeratorProfile = CboNumeratorProfile(),
    expected_mmf_deposit_pass_through: Decimal | None = None,
    denominator_scope: str = TDCSIM_CBO_FROZEN_DENOMINATOR_SCOPE,
    denominator_invariance_status: str = (
        "pass_external_fiscal_year_denominator_reused_across_scenarios"
    ),
) -> list[dict[str, str]]:
    """Build fiscal-year ratio input rows from validated TDCSim CBO runs."""

    numerators: list[CboFiscalYearNumerator] = []
    run_by_scenario: dict[str, TdcsimCboRun] = {}
    for run_dir in run_dirs:
        run = load_tdcsim_cbo_run(
            run_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
        run_by_scenario[run.metadata["scenario_id"]] = run
        for fiscal_year in fiscal_years:
            numerators.append(
                assemble_cbo_fiscal_year_numerator(
                    run,
                    fiscal_year,
                    profile=profile,
                )
            )
    ratio_rows = attach_frozen_denominators(
        numerators,
        denominator_by_fiscal_year,
        denominator_scope=denominator_scope,
    )
    numerator_by_key = {
        (row.scenario_id, row.fiscal_year): row for row in numerators
    }
    out: list[dict[str, str]] = []
    for row in ratio_rows:
        numerator = numerator_by_key[(row.scenario_id, row.fiscal_year)]
        run = run_by_scenario[row.scenario_id]
        out.append(
            {
                "tdcsim_cbo_ratio_input_row_id": (
                    f"tdcsim_cbo_ratio_input::{row.fiscal_year}::{row.scenario_id}"
                ),
                "scenario_id": row.scenario_id,
                "run_id": run.metadata["run_id"],
                "package_id": run.metadata["package_id"],
                "source_vintage": run.metadata["source_vintage"],
                "actuals_available_as_of": run.metadata["actuals_available_as_of"],
                "fiscal_year": str(row.fiscal_year),
                "period_count": str(numerator.period_count),
                "tdc_change_ex_overlap_bil": _fmt(numerator.tdc_change_ex_overlap_bil),
                "tdc_current_demand_support_bil": _fmt(
                    numerator.tdc_current_demand_support_bil
                ),
                "direct_treasury_interest_basis_bil": _fmt(
                    numerator.direct_treasury_interest_basis_bil
                ),
                "direct_treasury_current_demand_support_bil": _fmt(
                    numerator.direct_treasury_current_demand_support_bil
                ),
                "bank_treasury_interest_basis_bil": _fmt(
                    numerator.bank_treasury_interest_basis_bil
                ),
                "bank_treasury_current_demand_support_bil": _fmt(
                    numerator.bank_treasury_current_demand_support_bil
                ),
                "total_current_demand_support_bil": _fmt(
                    row.total_current_demand_support_bil
                ),
                "frozen_denominator_bil": _fmt(row.frozen_denominator),
                "ratewall_ratio": _fmt(row.ratio),
                "denominator_scope": row.denominator_scope,
                "denominator_invariance_status": denominator_invariance_status,
                "tdc_amount_basis": numerator.tdc_amount_basis,
                "mmf_deposit_pass_through": run.metadata["mmf_deposit_pass_through"],
                "fiscal_incidence_basis": run.metadata["fiscal_incidence_basis"],
                "allowed_use": "tdcsim_cbo_forward_numerator_input",
                "blocked_use": (
                    "denominator_recalibration;maturity_curve_holder_specific_D;"
                    "ratewall_native_treasury_tdc_fallback"
                ),
                "source_status": "pass_tdcsim_cbo_contract_materialized",
                "canonical_ratio_entry": "false",
            }
        )
    return out


def tdcsim_cbo_fiscal_year_ratio_input_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load CBO scenario run folders from a local suite directory."""

    root = Path(suite_dir)
    if not root.exists():
        return []
    run_dirs = _scenario_run_dirs(root)
    if not run_dirs:
        return []
    bridge = _denominator_bridge_from_directory(
        root,
        run_dirs,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )
    return tdcsim_cbo_fiscal_year_ratio_input_rows(
        run_dirs,
        fiscal_years=sorted(bridge.denominator_by_fiscal_year),
        denominator_by_fiscal_year=bridge.denominator_by_fiscal_year,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        denominator_scope=bridge.denominator_scope,
        denominator_invariance_status=bridge.denominator_invariance_status,
    )


def tdcsim_cbo_scenario_effect_rows(
    run_dirs: Iterable[str | Path],
    *,
    fiscal_years: Iterable[int],
    denominator_by_fiscal_year: Mapping[int, Decimal | str | int | float],
    profile: CboNumeratorProfile = CboNumeratorProfile(),
    expected_mmf_deposit_pass_through: Decimal | None = None,
    baseline_scenario_id: str | None = None,
    denominator_scope: str = TDCSIM_CBO_FROZEN_DENOMINATOR_SCOPE,
) -> list[dict[str, str]]:
    """Build scenario level and baseline-delta rows with component decomposition."""

    records: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        run = load_tdcsim_cbo_run(
            run_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
        for fiscal_year in fiscal_years:
            numerator = assemble_cbo_fiscal_year_numerator(
                run,
                fiscal_year,
                profile=profile,
            )
            ratio = attach_frozen_denominators(
                [numerator],
                denominator_by_fiscal_year,
                denominator_scope=denominator_scope,
            )[0]
            summary = _summary_totals(run, fiscal_year)
            interpretation = _scenario_interpretation(numerator.scenario_id)
            records.append(
                {
                    "scenario_id": numerator.scenario_id,
                    "fiscal_year": fiscal_year,
                    "scenario_role": interpretation[0],
                    "scenario_label": interpretation[1],
                    "scenario_interpretation_status": interpretation[2],
                    "core_scenario_entry": interpretation[3],
                    "level_ratewall_ratio": ratio.ratio,
                    "total_current_demand_support_bil": (
                        numerator.total_current_demand_support_bil
                    ),
                    "tdc_current_demand_support_bil": (
                        numerator.tdc_current_demand_support_bil
                    ),
                    "direct_treasury_current_demand_support_bil": (
                        numerator.direct_treasury_current_demand_support_bil
                    ),
                    "bank_treasury_current_demand_support_bil": (
                        numerator.bank_treasury_current_demand_support_bil
                    ),
                    "frozen_denominator_bil": ratio.frozen_denominator,
                    "denominator_scope": ratio.denominator_scope,
                    **summary,
                }
            )
    baseline_by_year = _baseline_records_by_year(records, baseline_scenario_id)
    delta_fields = (
        "level_ratewall_ratio",
        "total_current_demand_support_bil",
        "tdc_current_demand_support_bil",
        "direct_treasury_current_demand_support_bil",
        "bank_treasury_current_demand_support_bil",
        "tdc_fiscal_flow_bil",
        "tdc_debt_service_principal_to_du_bil",
        "gross_principal_cash_paid_to_du_bil",
        "du_bill_discount_interest_bil",
        "tdc_debt_service_interest_to_du_bil",
        "tdc_auction_absorption_du_bil",
        "tdc_secondary_trades_bil",
        "tdc_other_bil",
        "overlap_cashflow_bil",
        "tdc_change_ex_overlap_bil",
    )
    out: list[dict[str, str]] = []
    for record in records:
        baseline = baseline_by_year[record["fiscal_year"]]
        row = {
            "tdcsim_cbo_scenario_effect_row_id": (
                "tdcsim_cbo_scenario_effect::"
                f"{record['fiscal_year']}::{record['scenario_id']}"
            ),
            "scenario_id": record["scenario_id"],
            "baseline_scenario_id": baseline["scenario_id"],
            "fiscal_year": str(record["fiscal_year"]),
            "scenario_role": record["scenario_role"],
            "scenario_label": record["scenario_label"],
            "scenario_interpretation_status": record[
                "scenario_interpretation_status"
            ],
            "core_scenario_entry": record["core_scenario_entry"],
        }
        for field in delta_fields:
            row[field] = _fmt(record[field])
            delta_name = (
                "delta_ratewall_ratio_vs_baseline"
                if field == "level_ratewall_ratio"
                else f"delta_{field}"
            )
            row[delta_name] = _fmt(record[field] - baseline[field])
        row.update(
            {
                "frozen_denominator_bil": _fmt(record["frozen_denominator_bil"]),
                "denominator_scope": record["denominator_scope"],
                "allowed_use": "provisional_model_interpretation_point_calibration",
                "blocked_use": (
                    "canonical_headline_promotion;coefficient_robust_ranking;"
                    "causal_one_factor_claim_for_composite_rows;denominator_change"
                ),
                "canonical_ratio_entry": "false",
            }
        )
        out.append(row)
    return out


def tdcsim_cbo_scenario_effect_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load scenario-effect rows from a local TDCSim CBO suite directory."""

    root = Path(suite_dir)
    if not root.exists():
        return []
    run_dirs = _scenario_run_dirs(root)
    if not run_dirs:
        return []
    bridge = _denominator_bridge_from_directory(
        root,
        run_dirs,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )
    return tdcsim_cbo_scenario_effect_rows(
        run_dirs,
        fiscal_years=sorted(bridge.denominator_by_fiscal_year),
        denominator_by_fiscal_year=bridge.denominator_by_fiscal_year,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        denominator_scope=bridge.denominator_scope,
    )


def tdcsim_cbo_empirical_term_premium_comparison_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Compare empirical issuance-only rows with coupled long-rate overlays."""

    rows_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row
        for row in scenario_effect_rows
    }
    fiscal_years = sorted({row["fiscal_year"] for row in scenario_effect_rows})
    out: list[dict[str, str]] = []
    for fiscal_year in fiscal_years:
        for spec in EMPIRICAL_TERM_PREMIUM_COMPARISONS:
            issuance_only_id = str(spec["issuance_only_scenario_id"])
            issuance_only = rows_by_key.get((issuance_only_id, fiscal_year))
            if issuance_only is None:
                continue
            issuance_delta_rw = _decimal(
                issuance_only["delta_ratewall_ratio_vs_baseline"]
            )
            issuance_delta_support = _decimal(
                issuance_only["delta_total_current_demand_support_bil"]
            )
            for tier, ten_year_shock_bp, coupled_id in spec["coupled_scenarios"]:
                coupled = rows_by_key.get((str(coupled_id), fiscal_year))
                if coupled is None:
                    continue
                coupled_delta_rw = _decimal(
                    coupled["delta_ratewall_ratio_vs_baseline"]
                )
                coupled_delta_support = _decimal(
                    coupled["delta_total_current_demand_support_bil"]
                )
                overlay_delta_rw = coupled_delta_rw - issuance_delta_rw
                overlay_delta_support = (
                    coupled_delta_support - issuance_delta_support
                )
                out.append(
                    {
                        "tdcsim_cbo_empirical_term_premium_comparison_row_id": (
                            "tdcsim_cbo_empirical_term_premium_comparison::"
                            f"{fiscal_year}::{spec['issuance_direction']}::{tier}"
                        ),
                        "fiscal_year": fiscal_year,
                        "issuance_direction": str(spec["issuance_direction"]),
                        "term_premium_tier": str(tier),
                        "ten_year_nominal_rate_shock_bp": _fmt(ten_year_shock_bp),
                        "baseline_scenario_id": coupled["baseline_scenario_id"],
                        "issuance_only_scenario_id": issuance_only_id,
                        "coupled_scenario_id": str(coupled_id),
                        "issuance_only_delta_ratewall_ratio": _fmt(
                            issuance_delta_rw
                        ),
                        "coupled_delta_ratewall_ratio": _fmt(coupled_delta_rw),
                        "rate_overlay_delta_ratewall_ratio": _fmt(
                            overlay_delta_rw
                        ),
                        "offset_fraction_of_abs_issuance_effect": _fmt(
                            _safe_abs_ratio(
                                overlay_delta_rw,
                                issuance_delta_rw,
                            )
                        ),
                        "net_effect_fraction_remaining": _fmt(
                            _safe_ratio(coupled_delta_rw, issuance_delta_rw)
                        ),
                        "issuance_only_delta_total_current_demand_support_bil": (
                            _fmt(issuance_delta_support)
                        ),
                        "coupled_delta_total_current_demand_support_bil": _fmt(
                            coupled_delta_support
                        ),
                        "rate_overlay_delta_total_current_demand_support_bil": (
                            _fmt(overlay_delta_support)
                        ),
                        "interpretation_status": (
                            "external_term_premium_overlay_on_empirical_"
                            "issuance_control"
                        ),
                        "allowed_use": (
                            "assumption_mode_empirical_scenario_decomposition"
                        ),
                        "blocked_use": (
                            "causal_market_yield_estimate;canonical_headline_"
                            "promotion;denominator_change"
                        ),
                        "canonical_ratio_entry": "false",
                    }
                )
    return out


def tdcsim_cbo_empirical_term_premium_comparison_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load empirical term-premium comparison rows from a local TDCSim suite."""

    return tdcsim_cbo_empirical_term_premium_comparison_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
    )


def tdcsim_cbo_empirical_scenario_interpretation_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Build compact model-facing rows for empirical issuance scenarios."""

    effect_rows = list(scenario_effect_rows)
    effects_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row
        for row in effect_rows
    }
    comparisons = tdcsim_cbo_empirical_term_premium_comparison_rows(effect_rows)
    comparison_by_key = {
        (
            row["coupled_scenario_id"],
            row["fiscal_year"],
        ): row
        for row in comparisons
    }
    fiscal_years = sorted({row["fiscal_year"] for row in effect_rows})
    out: list[dict[str, str]] = []
    for fiscal_year in fiscal_years:
        for spec in EMPIRICAL_SCENARIO_INTERPRETATION_SPECS:
            effect = effects_by_key.get((str(spec["scenario_id"]), fiscal_year))
            if effect is None:
                continue
            out.append(
                _empirical_scenario_interpretation_row(
                    effect,
                    scenario_set_role=str(spec["scenario_set_role"]),
                    issuance_direction=str(spec["issuance_direction"]),
                    term_premium_tier=str(spec["term_premium_tier"]),
                    ten_year_nominal_rate_shock_bp=spec[
                        "ten_year_nominal_rate_shock_bp"
                    ],
                    paired_issuance_only_scenario_id=str(
                        spec["paired_issuance_only_scenario_id"]
                    ),
                    comparison=None,
                    model_interpretation=str(spec["model_interpretation"]),
                )
            )
        for comparison in comparisons:
            if comparison["fiscal_year"] != fiscal_year:
                continue
            effect = effects_by_key.get(
                (comparison["coupled_scenario_id"], fiscal_year)
            )
            if effect is None:
                continue
            tier = comparison["term_premium_tier"]
            role = (
                "coupled_central_empirical_scenario"
                if tier == "central"
                else "coupled_bound_empirical_scenario"
            )
            out.append(
                _empirical_scenario_interpretation_row(
                    effect,
                    scenario_set_role=role,
                    issuance_direction=comparison["issuance_direction"],
                    term_premium_tier=tier,
                    ten_year_nominal_rate_shock_bp=_decimal(
                        comparison["ten_year_nominal_rate_shock_bp"]
                    ),
                    paired_issuance_only_scenario_id=comparison[
                        "issuance_only_scenario_id"
                    ],
                    comparison=comparison_by_key[
                        (comparison["coupled_scenario_id"], fiscal_year)
                    ],
                    model_interpretation=(
                        "coupled_external_term_premium_overlay_central"
                        if tier == "central"
                        else "coupled_external_term_premium_overlay_bound"
                    ),
                )
            )
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            _empirical_interpretation_sort_key(row),
        ),
    )


def tdcsim_cbo_empirical_scenario_interpretation_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load empirical scenario interpretation rows from a local TDCSim suite."""

    return tdcsim_cbo_empirical_scenario_interpretation_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
    )


def tdcsim_cbo_model_scenario_summary_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Build the compact Assumption-Mode scenario set for model interpretation."""

    effect_rows = list(scenario_effect_rows)
    empirical_rows = tdcsim_cbo_empirical_scenario_interpretation_rows(effect_rows)
    effects_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row for row in effect_rows
    }
    fiscal_years = sorted({row["fiscal_year"] for row in effect_rows})
    primary_up_delta_by_year = {
        fiscal_year: abs(
            _decimal(
                effects_by_key.get(
                    ("tdcsim_primary_deficit_up_1pct_v1", fiscal_year), {}
                ).get("delta_ratewall_ratio_vs_baseline", "0")
            )
        )
        for fiscal_year in fiscal_years
    }
    out = [
        _model_scenario_summary_row(
            row,
            summary_role=row["scenario_set_role"],
            comparison_group=_model_summary_comparison_group(row),
            model_interpretation=row["model_interpretation"],
            primary_deficit_up_delta=primary_up_delta_by_year[row["fiscal_year"]],
        )
        for row in empirical_rows
    ]
    for fiscal_year in fiscal_years:
        for scenario_id, interpretation in (
            (
                "tdcsim_primary_deficit_down_1pct_v1",
                "primary_deficit_down_1pct_scale_comparator",
            ),
            (
                "tdcsim_primary_deficit_up_1pct_v1",
                "primary_deficit_up_1pct_scale_comparator",
            ),
        ):
            effect = effects_by_key.get((scenario_id, fiscal_year))
            if effect is None:
                continue
            out.append(
                _model_scenario_summary_row(
                    _summary_source_from_effect(effect),
                    summary_role="fiscal_scale_comparator",
                    comparison_group="primary_deficit",
                    model_interpretation=interpretation,
                    primary_deficit_up_delta=primary_up_delta_by_year[
                        fiscal_year
                    ],
                )
            )
        for scenario_id, interpretation in MODEL_SUMMARY_HOLDER_SCENARIOS:
            effect = effects_by_key.get((scenario_id, fiscal_year))
            if effect is None:
                continue
            out.append(
                _model_scenario_summary_row(
                    _summary_source_from_effect(effect),
                    summary_role="holder_preference_comparator",
                    comparison_group="holder_preference",
                    model_interpretation=interpretation,
                    primary_deficit_up_delta=primary_up_delta_by_year[
                        fiscal_year
                    ],
                )
            )
        for scenario_id, interpretation in MODEL_SUMMARY_RATE_SCENARIOS:
            effect = effects_by_key.get((scenario_id, fiscal_year))
            if effect is None:
                continue
            out.append(
                _model_scenario_summary_row(
                    _summary_source_from_effect(effect),
                    summary_role="rate_curve_comparator",
                    comparison_group="rate_curve",
                    model_interpretation=interpretation,
                    primary_deficit_up_delta=primary_up_delta_by_year[
                        fiscal_year
                    ],
                )
            )
        for scenario_id, interpretation in MODEL_SUMMARY_MMF_SCENARIOS:
            effect = effects_by_key.get((scenario_id, fiscal_year))
            if effect is None:
                continue
            out.append(
                _model_scenario_summary_row(
                    _summary_source_from_effect(effect),
                    summary_role="mmf_pass_through_comparator",
                    comparison_group="mmf_pass_through",
                    model_interpretation=interpretation,
                    primary_deficit_up_delta=primary_up_delta_by_year[
                        fiscal_year
                    ],
                )
            )
        for scenario_id, interpretation in MODEL_SUMMARY_COMBINED_SCENARIOS:
            effect = effects_by_key.get((scenario_id, fiscal_year))
            if effect is None:
                continue
            out.append(
                _model_scenario_summary_row(
                    _summary_source_from_effect(effect),
                    summary_role="combined_narrative_scenario",
                    comparison_group="combined_narrative",
                    model_interpretation=interpretation,
                    primary_deficit_up_delta=primary_up_delta_by_year[
                        fiscal_year
                    ],
                )
            )
    return sorted(out, key=_model_summary_sort_key)


def tdcsim_cbo_model_scenario_summary_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load compact model scenario summary rows from a local TDCSim suite."""

    return tdcsim_cbo_model_scenario_summary_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
    )


def tdcsim_cbo_model_scenario_beta_chi_robustness_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Recompute the model-summary scenarios over the existing beta x chi grid."""

    effect_rows = list(scenario_effect_rows)
    effect_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row for row in effect_rows
    }
    summary_rows = tdcsim_cbo_model_scenario_summary_rows(effect_rows)
    base_primary_delta_by_year = _primary_deficit_up_delta_by_year(
        effect_by_key,
        _current_beta_times_chi(),
    )
    out: list[dict[str, str]] = []
    for beta_label, beta, beta_source_status in BETA_CHI_ROBUSTNESS_BETA_PROFILES:
        for chi_label, chi in BETA_CHI_ROBUSTNESS_CHI_PROFILES:
            beta_chi = beta * chi
            primary_delta_by_year = _primary_deficit_up_delta_by_year(
                effect_by_key,
                beta_chi,
            )
            recomputed_by_key = {
                (row["scenario_id"], row["fiscal_year"]): _recomputed_support(
                    _required_effect_row(effect_by_key, row),
                    _required_effect_row(
                        effect_by_key,
                        {
                            "scenario_id": row["baseline_scenario_id"],
                            "fiscal_year": row["fiscal_year"],
                        },
                    ),
                    beta_chi,
                )
                for row in summary_rows
            }
            for summary in summary_rows:
                effect = _required_effect_row(effect_by_key, summary)
                baseline = _required_effect_row(
                    effect_by_key,
                    {
                        "scenario_id": summary["baseline_scenario_id"],
                        "fiscal_year": summary["fiscal_year"],
                    },
                )
                recomputed = recomputed_by_key[
                    (summary["scenario_id"], summary["fiscal_year"])
                ]
                paired_recomputed = recomputed_by_key.get(
                    (
                        summary["paired_issuance_only_scenario_id"],
                        summary["fiscal_year"],
                    )
                )
                out.append(
                    _beta_chi_robustness_row(
                        summary,
                        effect=effect,
                        baseline=baseline,
                        recomputed=recomputed,
                        paired_recomputed=paired_recomputed,
                        beta_label=beta_label,
                        beta=beta,
                        beta_source_status=beta_source_status,
                        chi_label=chi_label,
                        chi=chi,
                        primary_deficit_up_delta=primary_delta_by_year[
                            summary["fiscal_year"]
                        ],
                        current_point_primary_deficit_up_delta=(
                            base_primary_delta_by_year[summary["fiscal_year"]]
                        ),
                    )
                )
    return sorted(out, key=_beta_chi_robustness_sort_key)


def tdcsim_cbo_model_scenario_beta_chi_robustness_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load beta x chi robustness rows from a local TDCSim suite."""

    return tdcsim_cbo_model_scenario_beta_chi_robustness_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
    )


def tdcsim_cbo_model_scenario_beta_chi_sign_stability_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Summarize sign and scale stability across the beta x chi robustness grid."""

    effect_rows = list(scenario_effect_rows)
    robustness_rows = tdcsim_cbo_model_scenario_beta_chi_robustness_rows(
        effect_rows
    )
    effects_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row for row in effect_rows
    }
    rows_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in robustness_rows:
        rows_by_key.setdefault((row["scenario_id"], row["fiscal_year"]), []).append(
            row
        )
    out = [
        _beta_chi_sign_stability_row(
            rows,
            _required_effect_row(
                effects_by_key,
                {"scenario_id": scenario_id, "fiscal_year": fiscal_year},
            ),
        )
        for (scenario_id, fiscal_year), rows in rows_by_key.items()
    ]
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            _model_summary_sort_key(row),
        ),
    )


def tdcsim_cbo_model_scenario_beta_chi_sign_stability_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load beta x chi sign-stability rows from a local TDCSim suite."""

    return tdcsim_cbo_model_scenario_beta_chi_sign_stability_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
    )


def tdcsim_cbo_curve_denominator_input_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
    *,
    scenario_config_dir: str | Path | None = None,
) -> list[dict[str, str]]:
    """Build a noncanonical curve-vector sidecar without moving denominator math."""

    effect_rows = list(scenario_effect_rows)
    effect_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row for row in effect_rows
    }
    scenario_configs = (
        _scenario_configs_by_id(scenario_config_dir)
        if scenario_config_dir is not None
        else {}
    )
    out: list[dict[str, str]] = []
    for summary in tdcsim_cbo_model_scenario_summary_rows(effect_rows):
        effect = _required_effect_row(effect_by_key, summary)
        out.append(
            _curve_denominator_input_row(
                summary,
                effect=effect,
                scenario_configs=scenario_configs,
            )
        )
    return sorted(out, key=_model_summary_sort_key)


def tdcsim_cbo_curve_denominator_input_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load the noncanonical curve-vector sidecar from a local TDCSim suite."""

    suite_path = Path(suite_dir)
    return tdcsim_cbo_curve_denominator_input_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_path,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        ),
        scenario_config_dir=suite_path / "scenarios",
    )


def tdcsim_cbo_curve_sensitive_denominator_assumption_bound_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
    *,
    scenario_config_dir: str | Path | None = None,
) -> list[dict[str, str]]:
    """Compute noncanonical moving-D bounds from explicit assumption profiles."""

    input_rows = tdcsim_cbo_curve_denominator_input_rows(
        scenario_effect_rows,
        scenario_config_dir=scenario_config_dir,
    )
    out: list[dict[str, str]] = []
    for tier, theta, label in CURVE_DENOMINATOR_ASSUMPTION_PROFILES:
        profile_rows = [
            _curve_sensitive_denominator_assumption_bound_row(
                row,
                tier=tier,
                theta=theta,
                label=label,
            )
            for row in input_rows
        ]
        baseline_by_year = {
            row["fiscal_year"]: row
            for row in profile_rows
            if row["scenario_id"] == row["baseline_scenario_id"]
        }
        for row in profile_rows:
            baseline = baseline_by_year.get(row["fiscal_year"])
            if baseline is None:
                raise TdcsimCboContractError(
                    "curve denominator bounds require baseline row for "
                    f"fiscal year {row['fiscal_year']}"
                )
            moving_delta = _decimal(row["moving_ratewall_ratio"]) - _decimal(
                baseline["moving_ratewall_ratio"]
            )
            row["moving_delta_ratewall_ratio_vs_baseline"] = _fmt(moving_delta)
            out.append(row)
    return sorted(out, key=_curve_assumption_bound_sort_key)


def tdcsim_cbo_curve_sensitive_denominator_assumption_bound_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load noncanonical moving-D assumption bounds from a TDCSim CBO suite."""

    suite_path = Path(suite_dir)
    return tdcsim_cbo_curve_sensitive_denominator_assumption_bound_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_path,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        ),
        scenario_config_dir=suite_path / "scenarios",
    )


def tdcsim_cbo_model_scenario_interpretation_synthesis_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
    *,
    scenario_config_dir: str | Path | None = None,
) -> list[dict[str, str]]:
    """Combine point, beta x chi, denominator bounds, and selected moving-D rows."""

    from ratewall.databook.denominator_response_application import (
        denominator_response_application_rows,
    )
    from ratewall.databook.denominator_response_coefficient import (
        selected_frbus_structural_curve_denominator_response_profile,
    )

    effect_rows = list(scenario_effect_rows)
    summary_rows = tdcsim_cbo_model_scenario_summary_rows(effect_rows)
    beta_rows = tdcsim_cbo_model_scenario_beta_chi_sign_stability_rows(effect_rows)
    bound_rows = tdcsim_cbo_curve_sensitive_denominator_assumption_bound_rows(
        effect_rows,
        scenario_config_dir=scenario_config_dir,
    )
    selected_moving_rows = denominator_response_application_rows(
        tdcsim_cbo_curve_denominator_input_rows(
            effect_rows,
            scenario_config_dir=scenario_config_dir,
        ),
        coefficient_profile=selected_frbus_structural_curve_denominator_response_profile(
            diagnostic_rows=[],
            path_object_rows=[],
        ),
    )
    beta_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row for row in beta_rows
    }
    selected_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row for row in selected_moving_rows
    }
    bounds_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in bound_rows:
        bounds_by_key.setdefault((row["scenario_id"], row["fiscal_year"]), []).append(
            row
        )
    out: list[dict[str, str]] = []
    for summary in summary_rows:
        key = (summary["scenario_id"], summary["fiscal_year"])
        try:
            beta = beta_by_key[key]
            bounds = bounds_by_key[key]
            selected = selected_by_key[key]
        except KeyError as exc:
            raise TdcsimCboContractError(
                "model interpretation synthesis requires summary, beta x chi, "
                f"denominator-bound, and selected moving-D rows for {key}"
            ) from exc
        out.append(
            _model_scenario_interpretation_synthesis_row(
                summary,
                beta=beta,
                bounds=bounds,
                selected=selected,
            )
        )
    return sorted(out, key=_model_summary_sort_key)


def tdcsim_cbo_model_scenario_interpretation_synthesis_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load combined model-scenario interpretation rows from a TDCSim suite."""

    suite_path = Path(suite_dir)
    return tdcsim_cbo_model_scenario_interpretation_synthesis_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_path,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        ),
        scenario_config_dir=suite_path / "scenarios",
    )


def tdcsim_cbo_curve_denominator_empirical_status_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
    *,
    scenario_config_dir: str | Path | None = None,
) -> list[dict[str, str]]:
    """State whether the current scenario suite has an admitted moving-D estimate."""

    effect_rows = list(scenario_effect_rows)
    synthesis_rows = tdcsim_cbo_model_scenario_interpretation_synthesis_rows(
        effect_rows,
        scenario_config_dir=scenario_config_dir,
    )
    bound_rows = tdcsim_cbo_curve_sensitive_denominator_assumption_bound_rows(
        effect_rows,
        scenario_config_dir=scenario_config_dir,
    )
    bounds_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in bound_rows:
        bounds_by_key.setdefault((row["scenario_id"], row["fiscal_year"]), []).append(
            row
        )
    out: list[dict[str, str]] = []
    for synthesis in synthesis_rows:
        key = (synthesis["scenario_id"], synthesis["fiscal_year"])
        try:
            bounds = bounds_by_key[key]
        except KeyError as exc:
            raise TdcsimCboContractError(
                "curve denominator empirical status requires assumption-bound "
                f"rows for {key}"
            ) from exc
        out.append(
            _curve_denominator_empirical_status_row(
                synthesis,
                bounds=bounds,
            )
        )
    return sorted(out, key=_model_summary_sort_key)


def tdcsim_cbo_curve_denominator_empirical_status_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load moving-D empirical status rows from a local TDCSim suite."""

    suite_path = Path(suite_dir)
    return tdcsim_cbo_curve_denominator_empirical_status_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_path,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        ),
        scenario_config_dir=suite_path / "scenarios",
    )


def tdcsim_cbo_model_scenario_materiality_classification_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
    *,
    scenario_config_dir: str | Path | None = None,
) -> list[dict[str, str]]:
    """Rank and classify model-scenario rows by materiality and robustness."""

    synthesis_rows = tdcsim_cbo_model_scenario_interpretation_synthesis_rows(
        scenario_effect_rows,
        scenario_config_dir=scenario_config_dir,
    )
    rows_by_year: dict[str, list[dict[str, str]]] = {}
    for row in synthesis_rows:
        rows_by_year.setdefault(row["fiscal_year"], []).append(row)

    out: list[dict[str, str]] = []
    for fiscal_year, rows in sorted(rows_by_year.items()):
        ranked = sorted(
            (
                row
                for row in rows
                if row["summary_role"] != "baseline_anchor"
            ),
            key=lambda row: (
                -abs(_decimal(row["point_calibration_delta_ratewall_ratio"])),
                row["scenario_id"],
            ),
        )
        rank_by_scenario = {
            row["scenario_id"]: str(index)
            for index, row in enumerate(ranked, start=1)
        }
        for row in rows:
            out.append(
                _model_scenario_materiality_classification_row(
                    row,
                    rank=rank_by_scenario.get(row["scenario_id"], "0"),
                )
            )
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            int(row["materiality_rank_abs_delta"]),
            row["scenario_id"],
        ),
    )


def tdcsim_cbo_model_scenario_materiality_classification_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load materiality classification rows from a local TDCSim suite."""

    suite_path = Path(suite_dir)
    return tdcsim_cbo_model_scenario_materiality_classification_rows(
        tdcsim_cbo_scenario_effect_rows_from_directory(
            suite_path,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        ),
        scenario_config_dir=suite_path / "scenarios",
    )


def tdcsim_cbo_canonical_entry_decision_rows(
    fiscal_year_ratio_rows: Iterable[Mapping[str, str]],
    *,
    baseline_scenario_id: str = "cbo_baseline_noop_v1",
) -> list[dict[str, str]]:
    """Select the TDCSim/CBO row that enters the forward model baseline."""

    rows = list(fiscal_year_ratio_rows)
    if not rows:
        return []
    by_year: dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        by_year.setdefault(row["fiscal_year"], []).append(row)

    out: list[dict[str, str]] = []
    for fiscal_year, year_rows in sorted(by_year.items(), key=lambda item: int(item[0])):
        baseline_rows = [
            row for row in year_rows if row["scenario_id"] == baseline_scenario_id
        ]
        if len(baseline_rows) != 1:
            raise TdcsimCboContractError(
                f"expected exactly one canonical-entry baseline for FY{fiscal_year}, "
                f"found {len(baseline_rows)}"
            )
        baseline = baseline_rows[0]
        if baseline["denominator_scope"] != "external_frozen_by_fiscal_year":
            raise TdcsimCboContractError(
                "TDCSim/CBO canonical forward baseline requires frozen external "
                f"denominator scope, found {baseline['denominator_scope']}"
            )
        if baseline["source_status"] != "pass_tdcsim_cbo_contract_materialized":
            raise TdcsimCboContractError(
                "TDCSim/CBO canonical forward baseline source is not materialized"
            )
        nonbaseline_rows = [
            row for row in year_rows if row["scenario_id"] != baseline_scenario_id
        ]
        nonbaseline_entering = [
            row
            for row in nonbaseline_rows
            if row.get("canonical_forward_baseline_entry") == "true"
            or row.get("canonical_ratio_entry") == "true"
        ]
        if nonbaseline_entering:
            raise TdcsimCboContractError(
                "nonbaseline TDCSim/CBO scenario attempted canonical entry: "
                f"{[row['scenario_id'] for row in nonbaseline_entering]}"
            )
        out.append(
            {
                "tdcsim_cbo_canonical_entry_decision_row_id": (
                    "tdcsim_cbo_canonical_entry_decision::"
                    f"{fiscal_year}::{baseline_scenario_id}"
                ),
                "fiscal_year": fiscal_year,
                "canonical_entry_scope": "current_forward_model_baseline_case",
                "baseline_scenario_id": baseline_scenario_id,
                "baseline_ratewall_ratio": _fmt_display_28(
                    baseline["ratewall_ratio"]
                ),
                "baseline_total_current_demand_support_bil": baseline[
                    "total_current_demand_support_bil"
                ],
                "frozen_denominator_bil": baseline["frozen_denominator_bil"],
                "denominator_scope": baseline["denominator_scope"],
                "baseline_source_status": baseline["source_status"],
                "baseline_mmf_deposit_pass_through": baseline[
                    "mmf_deposit_pass_through"
                ],
                "canonical_forward_baseline_entry": "true",
                "runtime_canonical_ratio_object_id": (
                    "rw_runtime_support_offset_af_fixed"
                ),
                "runtime_canonical_replacement_allowed": "false",
                "runtime_canonical_replacement_decision": (
                    "no_tdcsim_cbo_forward_fy_path_is_not_the_runtime_"
                    "annual_flow_100bp_year_object"
                ),
                "scenario_rows_reviewed_count": str(len(nonbaseline_rows)),
                "nonbaseline_rows_entering_forward_baseline_count": "0",
                "scenario_comparison_entry_decision": (
                    "all_nonbaseline_tdcsim_cbo_rows_remain_assumption_mode_"
                    "scenario_comparisons"
                ),
                "denominator_decision": (
                    "use_existing_frozen_fy_denominator_no_curve_sensitive_D"
                ),
                "allowed_use": (
                    "current_forward_model_baseline_selection;"
                    "scenario_surface_anchor"
                ),
                "blocked_use": (
                    "runtime_canonical_ratio_replacement;"
                    "nonbaseline_scenario_canonical_entry;denominator_change;"
                    "evidence_mode_claim;release_headline_promotion"
                ),
                "claim_boundary": (
                    "CBO_TDCSim_baseline_enters_as_forward_model_baseline_only;"
                    "scenario_rows_are_comparisons;runtime_canonical_object_"
                    "is_not_replaced"
                ),
                "canonical_ratio_entry": "false",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "denominator_prior_update_allowed": "false",
                "formula_replacement_allowed": "false",
                "causal_market_yield_estimate_enabled": "false",
            }
        )
    return out


def tdcsim_cbo_canonical_entry_decision_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load the TDCSim/CBO canonical-entry decision from a local suite."""

    return tdcsim_cbo_canonical_entry_decision_rows(
        tdcsim_cbo_fiscal_year_ratio_input_rows_from_directory(
            suite_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
    )


def tdcsim_cbo_settlement_accrual_bridge_rows(
    run_dirs: Iterable[str | Path],
    *,
    fiscal_years: Iterable[int],
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Build settlement-cash vs budget-accrual bridge rows from TDCSim tables."""

    out: list[dict[str, str]] = []
    for run_dir in run_dirs:
        run = load_tdcsim_cbo_run(
            run_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
        for fiscal_year in fiscal_years:
            require_complete_fiscal_year(run, fiscal_year)
            out.extend(_du_maturity_cash_bridge_rows(run, fiscal_year))
            out.extend(_payment_flow_accounting_bridge_rows(run, fiscal_year))
            out.extend(_direct_interest_component_bridge_rows(run, fiscal_year))
    return out


def tdcsim_cbo_settlement_accrual_bridge_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load settlement/accrual bridge rows from a local suite directory."""

    root = Path(suite_dir)
    if not root.exists():
        return []
    run_dirs = _scenario_run_dirs(root)
    if not run_dirs:
        return []
    denominator_by_fiscal_year = _read_frozen_denominator_map(
        root / TDCSIM_CBO_FROZEN_DENOMINATOR_FILENAME
    )
    return tdcsim_cbo_settlement_accrual_bridge_rows(
        run_dirs,
        fiscal_years=sorted(denominator_by_fiscal_year),
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )


def tdcsim_cbo_core_scenario_interpretation_rows(
    scenario_effect_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Build the model-facing core scenario interpretation table."""

    core_rows = [
        row
        for row in scenario_effect_rows
        if _bool(row["core_scenario_entry"])
    ]
    ranked_rows = sorted(
        core_rows,
        key=lambda row: (
            int(row["fiscal_year"]),
            -_decimal(row["level_ratewall_ratio"]),
            row["scenario_id"],
        ),
    )
    out: list[dict[str, str]] = []
    current_year: int | None = None
    rank = 0
    for row in ranked_rows:
        fiscal_year = int(row["fiscal_year"])
        if fiscal_year != current_year:
            current_year = fiscal_year
            rank = 1
        else:
            rank += 1
        dominant_component, dominant_value = _dominant_delta_support_component(row)
        out.append(
            {
                "tdcsim_cbo_core_scenario_interpretation_row_id": (
                    "tdcsim_cbo_core_scenario_interpretation::"
                    f"{row['fiscal_year']}::{row['scenario_id']}"
                ),
                "scenario_id": row["scenario_id"],
                "baseline_scenario_id": row["baseline_scenario_id"],
                "fiscal_year": row["fiscal_year"],
                "point_calibration_rank": str(rank),
                "scenario_role": row["scenario_role"],
                "scenario_label": row["scenario_label"],
                "level_ratewall_ratio": row["level_ratewall_ratio"],
                "delta_ratewall_ratio_vs_baseline": row[
                    "delta_ratewall_ratio_vs_baseline"
                ],
                "delta_direction_vs_baseline": _delta_direction(
                    _decimal(row["delta_ratewall_ratio_vs_baseline"])
                ),
                "wall_hit_status": (
                    "hit" if _decimal(row["level_ratewall_ratio"]) >= 1 else "no_hit"
                ),
                "total_current_demand_support_bil": row[
                    "total_current_demand_support_bil"
                ],
                "delta_total_current_demand_support_bil": row[
                    "delta_total_current_demand_support_bil"
                ],
                "tdc_current_demand_support_bil": row[
                    "tdc_current_demand_support_bil"
                ],
                "delta_tdc_current_demand_support_bil": row[
                    "delta_tdc_current_demand_support_bil"
                ],
                "direct_treasury_current_demand_support_bil": row[
                    "direct_treasury_current_demand_support_bil"
                ],
                "delta_direct_treasury_current_demand_support_bil": row[
                    "delta_direct_treasury_current_demand_support_bil"
                ],
                "bank_treasury_current_demand_support_bil": row[
                    "bank_treasury_current_demand_support_bil"
                ],
                "delta_bank_treasury_current_demand_support_bil": row[
                    "delta_bank_treasury_current_demand_support_bil"
                ],
                "dominant_delta_support_component": dominant_component,
                "dominant_delta_support_component_bil": _fmt(dominant_value),
                "denominator_bil": row["frozen_denominator_bil"],
                "interpretation_basis": (
                    "scenario_level_for_wall_test;scenario_minus_baseline_for_"
                    "scenario_effect"
                ),
                "ranking_stability": "point_calibration_only_not_coefficient_robust",
                "allowed_use": "model_facing_core_scenario_interpretation",
                "blocked_use": (
                    "canonical_headline_promotion;coefficient_robust_ranking;"
                    "diagnostic_composite_one_factor_claim;denominator_change"
                ),
                "canonical_ratio_entry": "false",
            }
        )
    return out


def tdcsim_cbo_core_scenario_interpretation_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load core scenario interpretation rows from a local suite directory."""

    scenario_effect_rows = tdcsim_cbo_scenario_effect_rows_from_directory(
        suite_dir,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )
    return tdcsim_cbo_core_scenario_interpretation_rows(scenario_effect_rows)


def tdcsim_cbo_route_stock_closure_rows(
    runs: Iterable[str | Path | TdcsimCboRun],
    *,
    fiscal_years: Iterable[int],
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Expose TDCSim principal-route stock closure rows for model diagnostics."""

    out: list[dict[str, str]] = []
    years = tuple(fiscal_years)
    for item in runs:
        run = (
            item
            if isinstance(item, TdcsimCboRun)
            else load_tdcsim_cbo_run(
                item,
                expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
            )
        )
        for fiscal_year in years:
            for row in _rows_for_fiscal_year(
                run.tables["tdcsim_tdc_principal_route_stock_closure"],
                fiscal_year,
            ):
                out.append(_route_stock_closure_row(run, fiscal_year, row))
    return out


def tdcsim_cbo_route_stock_closure_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    fiscal_years: Iterable[int] = (2027,),
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load route-stock closure rows from a local TDCSim CBO suite directory."""

    root = Path(suite_dir)
    return tdcsim_cbo_route_stock_closure_rows(
        _scenario_run_dirs(root),
        fiscal_years=fiscal_years,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )


def tdcsim_cbo_matched_response_coefficient_rows(
    run_dirs: Iterable[str | Path],
    *,
    fiscal_years: Iterable[int],
    denominator_by_fiscal_year: Mapping[int, Decimal | str | int | float],
    profile: CboNumeratorProfile = CboNumeratorProfile(),
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Build signed response rows from matched TDCSim scenario pairs."""

    runs = _load_runs_by_scenario(
        run_dirs,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )
    years = tuple(fiscal_years)
    numerators: dict[tuple[str, int], CboFiscalYearNumerator] = {}
    ratios: dict[tuple[str, int], Decimal] = {}
    for run in runs.values():
        for fiscal_year in years:
            numerator = assemble_cbo_fiscal_year_numerator(
                run,
                fiscal_year,
                profile=profile,
            )
            numerators[(run.metadata["scenario_id"], fiscal_year)] = numerator
            ratios[(run.metadata["scenario_id"], fiscal_year)] = (
                attach_frozen_denominators(
                    [numerator],
                    denominator_by_fiscal_year,
                )[0].ratio
            )
    out: list[dict[str, str]] = []
    for axis in MATCHED_RESPONSE_AXES:
        scenario_ids = (
            axis["baseline_scenario_id"],
            *axis["scenario_ids"],
        )
        _require_scenarios(runs, scenario_ids, str(axis["response_axis"]))
        for fiscal_year in years:
            x_by_scenario = _axis_x_values(axis, runs, fiscal_year)
            baseline_scenario_id = str(axis["baseline_scenario_id"])
            endpoint_ids = tuple(str(value) for value in axis["scenario_ids"])
            low_scenario_id, high_scenario_id = sorted(
                endpoint_ids,
                key=lambda scenario_id: (
                    x_by_scenario[scenario_id],
                    scenario_id,
                ),
            )
            baseline_x = x_by_scenario[baseline_scenario_id]
            low_x = x_by_scenario[low_scenario_id]
            high_x = x_by_scenario[high_scenario_id]
            if high_x == low_x:
                raise TdcsimCboContractError(
                    f"matched response axis {axis['response_axis']} has equal endpoints"
                )
            annual_outcomes = _annual_response_outcomes(
                numerators,
                ratios,
                fiscal_year,
            )
            for outcome_name, values_by_scenario in annual_outcomes.items():
                baseline_outcome = values_by_scenario[baseline_scenario_id]
                low_outcome = values_by_scenario[low_scenario_id]
                high_outcome = values_by_scenario[high_scenario_id]
                midpoint = (low_outcome + high_outcome) / Decimal("2")
                midpoint_delta = midpoint - baseline_outcome
                out.append(
                    {
                        "tdcsim_cbo_matched_response_coefficient_row_id": (
                            "tdcsim_cbo_matched_response_coefficient::"
                            f"{fiscal_year}::{axis['response_axis']}::{outcome_name}"
                        ),
                        "fiscal_year": str(fiscal_year),
                        "response_axis": str(axis["response_axis"]),
                        "response_axis_label": str(axis["response_axis_label"]),
                        "x_measure": str(axis["x_measure"]),
                        "x_unit": str(axis["x_unit"]),
                        "outcome_name": outcome_name,
                        "baseline_scenario_id": baseline_scenario_id,
                        "low_scenario_id": low_scenario_id,
                        "high_scenario_id": high_scenario_id,
                        "baseline_x": _fmt(baseline_x),
                        "low_x": _fmt(low_x),
                        "high_x": _fmt(high_x),
                        "baseline_outcome": _fmt(baseline_outcome),
                        "low_outcome": _fmt(low_outcome),
                        "high_outcome": _fmt(high_outcome),
                        "low_delta_vs_baseline": _fmt(
                            low_outcome - baseline_outcome
                        ),
                        "high_delta_vs_baseline": _fmt(
                            high_outcome - baseline_outcome
                        ),
                        "signed_slope_per_x": _fmt(
                            (high_outcome - low_outcome) / (high_x - low_x)
                        ),
                        "midpoint_outcome": _fmt(midpoint),
                        "midpoint_delta_vs_baseline": _fmt(midpoint_delta),
                        "symmetry_status": _matched_symmetry_status(midpoint_delta),
                        "sample_design": (
                            "baseline_plus_two_matched_tdcsim_endpoint_scenarios;"
                            "endpoint_order_by_actual_x"
                        ),
                        "allowed_use": "matched_tdcsim_response_surface_model_diagnostic",
                        "blocked_use": (
                            "canonical_headline_promotion;denominator_change;"
                            "causal_claim_without_stability_check"
                        ),
                        "canonical_ratio_entry": "false",
                    }
                )
    return out


def tdcsim_cbo_matched_response_coefficient_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load matched annual response rows from a local TDCSim CBO suite."""

    root = Path(suite_dir)
    if not root.exists():
        return []
    run_dirs = _scenario_run_dirs(root)
    if not run_dirs:
        return []
    denominator_by_fiscal_year = _read_frozen_denominator_map(
        root / TDCSIM_CBO_FROZEN_DENOMINATOR_FILENAME
    )
    return tdcsim_cbo_matched_response_coefficient_rows(
        run_dirs,
        fiscal_years=sorted(denominator_by_fiscal_year),
        denominator_by_fiscal_year=denominator_by_fiscal_year,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )


def tdcsim_cbo_matched_period_response_rows(
    run_dirs: Iterable[str | Path],
    *,
    fiscal_years: Iterable[int],
    profile: CboNumeratorProfile = CboNumeratorProfile(),
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Build period timing rows from matched TDCSim scenario pairs."""

    runs = _load_runs_by_scenario(
        run_dirs,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )
    period_rows: dict[tuple[str, int], tuple[CboPeriodSupport, ...]] = {}
    for run in runs.values():
        for fiscal_year in fiscal_years:
            period_rows[(run.metadata["scenario_id"], fiscal_year)] = (
                _period_support_rows(run, fiscal_year, profile=profile)
            )
    out: list[dict[str, str]] = []
    for axis in MATCHED_RESPONSE_AXES:
        scenario_ids = (
            axis["baseline_scenario_id"],
            *axis["scenario_ids"],
        )
        _require_scenarios(runs, scenario_ids, str(axis["response_axis"]))
        for fiscal_year in fiscal_years:
            x_by_scenario = _axis_x_values(axis, runs, fiscal_year)
            endpoint_ids = tuple(str(value) for value in axis["scenario_ids"])
            low_scenario_id, high_scenario_id = sorted(
                endpoint_ids,
                key=lambda scenario_id: (
                    x_by_scenario[scenario_id],
                    scenario_id,
                ),
            )
            baseline_scenario_id = str(axis["baseline_scenario_id"])
            baseline_by_period = {
                row.period_end: row
                for row in period_rows[(baseline_scenario_id, fiscal_year)]
            }
            low_by_period = {
                row.period_end: row for row in period_rows[(low_scenario_id, fiscal_year)]
            }
            high_by_period = {
                row.period_end: row
                for row in period_rows[(high_scenario_id, fiscal_year)]
            }
            period_ends = sorted(
                set(baseline_by_period) & set(low_by_period) & set(high_by_period)
            )
            if not period_ends:
                raise TdcsimCboContractError(
                    f"matched response axis {axis['response_axis']} has no shared periods"
                )
            for period_end in period_ends:
                baseline = baseline_by_period[period_end]
                low = low_by_period[period_end]
                high = high_by_period[period_end]
                for outcome_name in _PERIOD_RESPONSE_OUTCOMES:
                    baseline_outcome = getattr(baseline, outcome_name)
                    low_outcome = getattr(low, outcome_name)
                    high_outcome = getattr(high, outcome_name)
                    out.append(
                        {
                            "tdcsim_cbo_matched_period_response_row_id": (
                                "tdcsim_cbo_matched_period_response::"
                                f"{axis['response_axis']}::{outcome_name}::{period_end}"
                            ),
                            "response_axis": str(axis["response_axis"]),
                            "outcome_name": outcome_name,
                            "period_start": baseline.period_start,
                            "period_end": period_end,
                            "fiscal_year": str(fiscal_year),
                            "lag_days_from_fiscal_year_start": str(
                                (
                                    date.fromisoformat(period_end)
                                    - date(fiscal_year - 1, 10, 1)
                                ).days
                            ),
                            "baseline_scenario_id": baseline_scenario_id,
                            "low_scenario_id": low_scenario_id,
                            "high_scenario_id": high_scenario_id,
                            "baseline_outcome": _fmt(baseline_outcome),
                            "low_outcome": _fmt(low_outcome),
                            "high_outcome": _fmt(high_outcome),
                            "low_delta_vs_baseline": _fmt(
                                low_outcome - baseline_outcome
                            ),
                            "high_delta_vs_baseline": _fmt(
                                high_outcome - baseline_outcome
                            ),
                            "central_difference_delta": _fmt(
                                (high_outcome - low_outcome) / Decimal("2")
                            ),
                            "allowed_use": "matched_tdcsim_period_timing_model_diagnostic",
                            "blocked_use": (
                                "canonical_headline_promotion;denominator_change;"
                                "annual_ratio_replacement"
                            ),
                            "canonical_ratio_entry": "false",
                        }
                    )
    return out


def tdcsim_cbo_matched_period_response_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    fiscal_years: Iterable[int] = (2027,),
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load matched period response rows from a local TDCSim CBO suite."""

    root = Path(suite_dir)
    if not root.exists():
        return []
    return tdcsim_cbo_matched_period_response_rows(
        _scenario_run_dirs(root),
        fiscal_years=fiscal_years,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )


def tdcsim_cbo_scenario_lever_diagnostic_rows(
    run_dirs: Iterable[str | Path],
    *,
    fiscal_years: Iterable[int],
    denominator_by_fiscal_year: Mapping[int, Decimal | str | int | float],
    profile: CboNumeratorProfile = CboNumeratorProfile(),
    expected_mmf_deposit_pass_through: Decimal | None = None,
    baseline_scenario_id: str = "cbo_baseline_noop_v1",
) -> list[dict[str, str]]:
    """Classify candidate single-lever scenarios by observed RateWall effect."""

    runs = _load_runs_by_scenario(
        run_dirs,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )
    _require_scenarios(
        runs,
        (baseline_scenario_id, *(spec["scenario_id"] for spec in SCENARIO_LEVER_DIAGNOSTICS)),
        "scenario_lever_diagnostic",
    )
    out: list[dict[str, str]] = []
    for fiscal_year in fiscal_years:
        baseline_record = _lever_record(
            runs[baseline_scenario_id],
            fiscal_year,
            denominator_by_fiscal_year,
            profile,
        )
        for spec in SCENARIO_LEVER_DIAGNOSTICS:
            scenario_id = str(spec["scenario_id"])
            record = _lever_record(
                runs[scenario_id],
                fiscal_year,
                denominator_by_fiscal_year,
                profile,
            )
            deltas = {
                field: record[field] - baseline_record[field]
                for field in _LEVER_DELTA_FIELDS
            }
            status = _lever_response_status(
                str(spec["lever_name"]),
                deltas,
            )
            out.append(
                {
                    "tdcsim_cbo_scenario_lever_diagnostic_row_id": (
                        "tdcsim_cbo_scenario_lever_diagnostic::"
                        f"{fiscal_year}::{scenario_id}"
                    ),
                    "scenario_id": scenario_id,
                    "baseline_scenario_id": baseline_scenario_id,
                    "fiscal_year": str(fiscal_year),
                    "lever_name": str(spec["lever_name"]),
                    "scenario_override": _scenario_override(
                        runs[scenario_id],
                        str(spec["lever_name"]),
                    ),
                    "intended_x_measure": str(spec["intended_x_measure"]),
                    "intended_x_value": str(spec["intended_x_value"]),
                    "response_status": status,
                    "interpretation_status": _lever_interpretation_status(status),
                    "level_ratewall_ratio": _fmt(record["ratewall_ratio"]),
                    "delta_ratewall_ratio_vs_baseline": _fmt(
                        deltas["ratewall_ratio"]
                    ),
                    "delta_total_current_demand_support_bil": _fmt(
                        deltas["total_current_demand_support_bil"]
                    ),
                    "delta_tdc_current_demand_support_bil": _fmt(
                        deltas["tdc_current_demand_support_bil"]
                    ),
                    "delta_tdc_fiscal_flow_bil": _fmt(
                        deltas["tdc_fiscal_flow_bil"]
                    ),
                    "delta_tdc_change_ex_overlap_bil": _fmt(
                        deltas["tdc_change_ex_overlap_bil"]
                    ),
                    "delta_direct_treasury_current_demand_support_bil": _fmt(
                        deltas["direct_treasury_current_demand_support_bil"]
                    ),
                    "delta_bank_treasury_current_demand_support_bil": _fmt(
                        deltas["bank_treasury_current_demand_support_bil"]
                    ),
                    "delta_controlled_debt_post_issuance_bil": _fmt(
                        deltas["controlled_debt_post_issuance_bil"]
                    ),
                    "delta_route_face_issued_bil": _fmt(
                        deltas["route_face_issued_bil"]
                    ),
                    "delta_route_face_redeemed_bil": _fmt(
                        deltas["route_face_redeemed_bil"]
                    ),
                    "delta_gross_issuance_cash_proceeds_bil": _fmt(
                        deltas["gross_issuance_cash_proceeds_bil"]
                    ),
                    "delta_gross_issuance_proceeds_absorbed_by_du_bil": _fmt(
                        deltas["gross_issuance_proceeds_absorbed_by_du_bil"]
                    ),
                    "activation_evidence": _lever_activation_evidence(deltas),
                    "allowed_use": "tdcsim_cbo_candidate_lever_model_diagnostic",
                    "blocked_use": (
                        "canonical_headline_promotion;denominator_change;"
                        "matched_response_surface_without_active_endpoint"
                    ),
                    "canonical_ratio_entry": "false",
                }
            )
    return out


def tdcsim_cbo_scenario_lever_diagnostic_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
    *,
    expected_mmf_deposit_pass_through: Decimal | None = None,
) -> list[dict[str, str]]:
    """Load candidate-lever diagnostic rows from a TDCSim CBO suite."""

    root = Path(suite_dir)
    if not root.exists():
        return []
    run_dirs = _scenario_run_dirs(root)
    if not run_dirs:
        return []
    denominator_by_fiscal_year = _read_frozen_denominator_map(
        root / TDCSIM_CBO_FROZEN_DENOMINATOR_FILENAME
    )
    return tdcsim_cbo_scenario_lever_diagnostic_rows(
        run_dirs,
        fiscal_years=sorted(denominator_by_fiscal_year),
        denominator_by_fiscal_year=denominator_by_fiscal_year,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )


def _artifact_view_for_path(path: Path) -> ArtifactManifestView | None:
    for candidate in (path, *path.parents):
        if artifact_manifest_exists(candidate):
            return ArtifactManifestView.from_root(candidate)
    return None


def _artifact_logical_path(artifact: ArtifactManifestView, path: Path) -> str:
    try:
        return path.relative_to(artifact.root).as_posix()
    except ValueError as exc:
        raise TdcsimCboContractError(
            f"path is not inside artifact manifest root: {path}"
        ) from exc


def _read_manifest(root: Path) -> Mapping[str, Any]:
    artifact = _artifact_view_for_path(root)
    if artifact is not None:
        logical_path = _artifact_logical_path(artifact, root / "tdcsim_cbo_run_manifest.json")
        return json.loads(artifact.read_text(logical_path))
    manifest_path = root / "tdcsim_cbo_run_manifest.json"
    if not manifest_path.exists():
        raise TdcsimCboContractError(
            f"missing required TDCSim CBO manifest: {manifest_path}"
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _read_table(outputs_dir: Path, table_name: str) -> list[dict[str, str]]:
    artifact = _artifact_view_for_path(outputs_dir)
    if artifact is not None:
        csv_logical_path = _artifact_logical_path(artifact, outputs_dir / f"{table_name}.csv")
        gzip_logical_path = _artifact_logical_path(
            artifact,
            outputs_dir / f"{table_name}.csv.gz",
        )
        if not artifact.has_file(csv_logical_path):
            csv_logical_path = _artifact_logical_path(
                artifact,
                outputs_dir / "outputs" / f"{table_name}.csv",
            )
            gzip_logical_path = _artifact_logical_path(
                artifact,
                outputs_dir / "outputs" / f"{table_name}.csv.gz",
            )
        if artifact.has_file(csv_logical_path):
            with artifact.open_text(csv_logical_path) as handle:
                rows = list(csv.DictReader(handle))
            path_label = csv_logical_path
        elif artifact.has_file(gzip_logical_path):
            with gzip.open(
                artifact.object_path(gzip_logical_path),
                "rt",
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
            path_label = gzip_logical_path
        else:
            raise TdcsimCboContractError(
                f"missing required TDCSim CBO table: {table_name}"
            )
        if not rows:
            raise TdcsimCboContractError(
                f"required TDCSim CBO table is empty: {path_label}"
            )
        return rows
    csv_path = outputs_dir / f"{table_name}.csv"
    gzip_path = outputs_dir / f"{table_name}.csv.gz"
    if csv_path.exists():
        path = csv_path
        handle_cm = csv_path.open("rt", encoding="utf-8", newline="")
    elif gzip_path.exists():
        path = gzip_path
        handle_cm = gzip.open(gzip_path, "rt", encoding="utf-8", newline="")
    else:
        raise TdcsimCboContractError(f"missing required TDCSim CBO table: {table_name}")
    with handle_cm as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise TdcsimCboContractError(f"required TDCSim CBO table is empty: {path}")
    return rows


def _scenario_run_dirs(root: Path) -> tuple[Path, ...]:
    if artifact_manifest_exists(root):
        artifact = ArtifactManifestView.from_root(root)
        run_dirs = {
            Path(path).parent
            for path in artifact.list_files(prefix="runs/", suffix="/tdcsim_cbo_run_manifest.json")
        }
        return tuple(sorted(root / run_dir for run_dir in run_dirs))
    candidates = root / "runs" if (root / "runs").is_dir() else root
    return tuple(
        sorted(
            path
            for path in candidates.iterdir()
            if path.is_dir() and (path / "tdcsim_cbo_run_manifest.json").exists()
        )
    )


def _load_runs_by_scenario(
    run_dirs: Iterable[str | Path],
    *,
    expected_mmf_deposit_pass_through: Decimal | None,
) -> dict[str, TdcsimCboRun]:
    runs: dict[str, TdcsimCboRun] = {}
    for run_dir in run_dirs:
        run = load_tdcsim_cbo_run(
            run_dir,
            expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
        )
        scenario_id = run.metadata["scenario_id"]
        if scenario_id in runs:
            raise TdcsimCboContractError(f"duplicate scenario_id in suite: {scenario_id}")
        runs[scenario_id] = run
    return runs


def _require_scenarios(
    runs: Mapping[str, TdcsimCboRun],
    scenario_ids: Iterable[object],
    response_axis: str,
) -> None:
    missing = sorted(str(scenario_id) for scenario_id in scenario_ids if str(scenario_id) not in runs)
    if missing:
        raise TdcsimCboContractError(
            f"matched response axis {response_axis} missing scenarios: {missing}"
        )


def _axis_x_values(
    axis: Mapping[str, object],
    runs: Mapping[str, TdcsimCboRun],
    fiscal_year: int,
) -> dict[str, Decimal]:
    x_values = axis.get("x_values")
    scenario_ids = (
        str(axis["baseline_scenario_id"]),
        *(str(scenario_id) for scenario_id in axis["scenario_ids"]),
    )
    if isinstance(x_values, Mapping):
        return {
            scenario_id: _decimal(x_values[scenario_id])
            for scenario_id in scenario_ids
        }
    measure = str(axis["x_measure"])
    if measure == "fy_weighted_average_issuance_maturity_years":
        return {
            scenario_id: _issuance_weighted_average_term_years(
                runs[scenario_id],
                fiscal_year,
            )
            for scenario_id in scenario_ids
        }
    if measure == "fy_du_absorbed_issuance_proceeds_share":
        return {
            scenario_id: _du_absorbed_issuance_proceeds_share(
                runs[scenario_id],
                fiscal_year,
            )
            for scenario_id in scenario_ids
        }
    raise TdcsimCboContractError(f"unsupported matched response x_measure: {measure}")


def _issuance_weighted_average_term_years(
    run: TdcsimCboRun,
    fiscal_year: int,
) -> Decimal:
    rows = _rows_for_fiscal_year(run.tables["tdcsim_period_issuance_flows"], fiscal_year)
    numerator = Decimal("0")
    denominator = Decimal("0")
    for row in rows:
        if "weighted_original_term_years" not in row:
            raise TdcsimCboContractError(
                "issuance response axis requires weighted_original_term_years"
            )
        face = _decimal(row["face_issued_bil"])
        numerator += face * _decimal(row["weighted_original_term_years"])
        denominator += face
    if denominator == 0:
        raise TdcsimCboContractError(
            f"issuance response axis has zero FY{fiscal_year} issuance face"
        )
    return numerator / denominator


def _du_absorbed_issuance_proceeds_share(
    run: TdcsimCboRun,
    fiscal_year: int,
) -> Decimal:
    rows = _rows_for_fiscal_year(run.tables["tdcsim_period_tdc_summary"], fiscal_year)
    absorbed = sum(
        (_decimal(row["gross_issuance_proceeds_absorbed_by_du_bil"]) for row in rows),
        Decimal("0"),
    )
    proceeds = sum(
        (_decimal(row["gross_issuance_cash_proceeds_bil"]) for row in rows),
        Decimal("0"),
    )
    if proceeds == 0:
        raise TdcsimCboContractError(
            f"private DU response axis has zero FY{fiscal_year} issuance proceeds"
        )
    return absorbed / proceeds


def _annual_response_outcomes(
    numerators: Mapping[tuple[str, int], CboFiscalYearNumerator],
    ratios: Mapping[tuple[str, int], Decimal],
    fiscal_year: int,
) -> dict[str, dict[str, Decimal]]:
    scenario_ids = {
        scenario_id
        for scenario_id, year in numerators
        if year == fiscal_year
    }
    out: dict[str, dict[str, Decimal]] = {
        outcome_name: {} for outcome_name in _ANNUAL_RESPONSE_OUTCOMES
    }
    for scenario_id in scenario_ids:
        numerator = numerators[(scenario_id, fiscal_year)]
        out["ratewall_ratio"][scenario_id] = ratios[(scenario_id, fiscal_year)]
        out["total_current_demand_support_bil"][scenario_id] = (
            numerator.total_current_demand_support_bil
        )
        out["tdc_current_demand_support_bil"][scenario_id] = (
            numerator.tdc_current_demand_support_bil
        )
        out["direct_treasury_current_demand_support_bil"][scenario_id] = (
            numerator.direct_treasury_current_demand_support_bil
        )
        out["bank_treasury_current_demand_support_bil"][scenario_id] = (
            numerator.bank_treasury_current_demand_support_bil
        )
    return out


def _period_support_rows(
    run: TdcsimCboRun,
    fiscal_year: int,
    *,
    profile: CboNumeratorProfile,
) -> tuple[CboPeriodSupport, ...]:
    require_complete_fiscal_year(run, fiscal_year)
    out: list[CboPeriodSupport] = []
    for row in _rows_for_fiscal_year(run.tables["tdcsim_period_tdc_summary"], fiscal_year):
        tdc_support = compute_tdc_current_demand_support(
            TdcCurrentDemandSupportInputs(
                tdc_change_ex_overlap_bil=_decimal(row["tdc_change_ex_overlap_bil"]),
                tdc_materialization_beta=profile.tdc_materialization_beta,
                deposit_current_demand_share=profile.tdc_deposit_current_demand_share,
            )
        )
        direct_interest = _sum_components_for_period(
            run.tables["tdcsim_period_tdc_components"],
            row["period_start"],
            row["period_end"],
            direct_interest=True,
            holder_sector="Private",
            holder_subsector="domestic_nonbank_deposit_funded",
        )
        bank_interest = _sum_payment_flows_for_period(
            run.tables["tdcsim_period_payment_flows"],
            row["period_start"],
            row["period_end"],
            holder_sector="Banks",
        )
        tdc_current_support = _decimal(tdc_support["tdc_current_demand_support_bil"])
        direct_support = direct_interest * profile.direct_treasury_current_demand_share
        bank_support = bank_interest * profile.bank_treasury_current_demand_share
        out.append(
            CboPeriodSupport(
                fiscal_year=fiscal_year,
                period_start=row["period_start"],
                period_end=row["period_end"],
                scenario_id=run.metadata["scenario_id"],
                tdc_current_demand_support_bil=tdc_current_support,
                direct_treasury_current_demand_support_bil=direct_support,
                bank_treasury_current_demand_support_bil=bank_support,
                total_current_demand_support_bil=(
                    tdc_current_support + direct_support + bank_support
                ),
            )
        )
    return tuple(sorted(out, key=lambda item: item.period_end))


def _sum_components_for_period(
    rows: Iterable[Mapping[str, str]],
    period_start: str,
    period_end: str,
    *,
    direct_interest: bool,
    holder_sector: str,
    holder_subsector: str,
) -> Decimal:
    total = Decimal("0")
    for row in rows:
        if row["period_start"] != period_start or row["period_end"] != period_end:
            continue
        if _bool(row["enters_direct_interest_support"]) != direct_interest:
            continue
        if row["holder_sector"] != holder_sector:
            continue
        if row["holder_subsector"] != holder_subsector:
            continue
        if row["payment_type"] not in DIRECT_SUPPORT_PAYMENT_TYPES:
            continue
        total += _decimal(row["amount_bil"])
    return total


def _sum_payment_flows_for_period(
    rows: Iterable[Mapping[str, str]],
    period_start: str,
    period_end: str,
    *,
    holder_sector: str,
) -> Decimal:
    total = Decimal("0")
    for row in rows:
        if row["period_start"] != period_start or row["period_end"] != period_end:
            continue
        if row["holder_sector"] != holder_sector:
            continue
        if row["payment_type"] not in DIRECT_SUPPORT_PAYMENT_TYPES:
            continue
        total += _decimal(row["amount_bil"])
    return total


def _matched_symmetry_status(midpoint_delta_vs_baseline: Decimal) -> str:
    if abs(midpoint_delta_vs_baseline) <= Decimal("0.000000001"):
        return "locally_symmetric_around_baseline"
    return "midpoint_differs_from_baseline"


def _denominator_bridge_from_directory(
    root: Path,
    run_dirs: tuple[Path, ...],
    *,
    expected_mmf_deposit_pass_through: Decimal | None,
) -> CboDenominatorBridge:
    frozen = _read_frozen_denominator_map(
        root / TDCSIM_CBO_FROZEN_DENOMINATOR_FILENAME
    )
    if len(frozen) != 1:
        return CboDenominatorBridge(
            denominator_by_fiscal_year=frozen,
            denominator_scope=TDCSIM_CBO_FROZEN_DENOMINATOR_SCOPE,
            denominator_invariance_status=(
                "pass_external_fiscal_year_denominator_reused_across_scenarios"
            ),
        )
    gdp_by_year = _cbo_nominal_gdp_by_fiscal_year_from_directory(root)
    if not gdp_by_year:
        return CboDenominatorBridge(
            denominator_by_fiscal_year=frozen,
            denominator_scope=TDCSIM_CBO_FROZEN_DENOMINATOR_SCOPE,
            denominator_invariance_status=(
                "pass_external_fiscal_year_denominator_reused_across_scenarios"
            ),
        )
    complete_years = _complete_fiscal_years_from_run_dirs(
        run_dirs,
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )
    derived = _denominator_map_from_cbo_gdp_anchor(
        frozen,
        gdp_by_year,
        fiscal_years=complete_years,
    )
    if tuple(sorted(derived)) == tuple(sorted(frozen)):
        return CboDenominatorBridge(
            denominator_by_fiscal_year=frozen,
            denominator_scope=TDCSIM_CBO_FROZEN_DENOMINATOR_SCOPE,
            denominator_invariance_status=(
                "pass_external_fiscal_year_denominator_reused_across_scenarios"
            ),
        )
    return CboDenominatorBridge(
        denominator_by_fiscal_year=derived,
        denominator_scope=TDCSIM_CBO_CBO_GDP_SCALED_DENOMINATOR_SCOPE,
        denominator_invariance_status=(
            "pass_fy2027_frozen_anchor_scaled_by_cbo_nominal_gdp_and_reused_"
            "across_scenarios"
        ),
    )


def _denominator_map_from_cbo_gdp_anchor(
    frozen_anchor: Mapping[int, Decimal],
    gdp_by_fiscal_year: Mapping[int, Decimal],
    *,
    fiscal_years: Iterable[int],
) -> dict[int, Decimal]:
    if len(frozen_anchor) != 1:
        raise TdcsimCboContractError("CBO GDP denominator bridge requires one anchor")
    anchor_year, anchor_denominator = next(iter(frozen_anchor.items()))
    try:
        anchor_gdp = gdp_by_fiscal_year[anchor_year]
    except KeyError as exc:
        raise TdcsimCboContractError(
            f"CBO GDP denominator bridge missing anchor GDP for FY{anchor_year}"
        ) from exc
    if anchor_gdp <= 0:
        raise TdcsimCboContractError(
            f"CBO GDP denominator bridge anchor GDP must be positive for FY{anchor_year}"
        )
    denominator_share = anchor_denominator / anchor_gdp
    out: dict[int, Decimal] = {}
    for fiscal_year in sorted(set(fiscal_years)):
        gdp = gdp_by_fiscal_year.get(fiscal_year)
        if gdp is None:
            continue
        if gdp <= 0:
            raise TdcsimCboContractError(
                f"CBO GDP denominator bridge GDP must be positive for FY{fiscal_year}"
            )
        out[fiscal_year] = gdp * denominator_share
    if anchor_year not in out:
        out[anchor_year] = anchor_denominator
    if not out:
        raise TdcsimCboContractError("CBO GDP denominator bridge produced no years")
    out[anchor_year] = anchor_denominator
    return dict(sorted(out.items()))


def _complete_fiscal_years_from_run_dirs(
    run_dirs: tuple[Path, ...],
    *,
    expected_mmf_deposit_pass_through: Decimal | None,
) -> tuple[int, ...]:
    if not run_dirs:
        return ()
    run = load_tdcsim_cbo_run(
        run_dirs[0],
        expected_mmf_deposit_pass_through=expected_mmf_deposit_pass_through,
    )
    fiscal_years = {
        fiscal_year_for_date(row["period_end"])
        for row in run.tables["tdcsim_period_tdc_summary"]
    }
    complete: list[int] = []
    for fiscal_year in sorted(fiscal_years):
        try:
            require_complete_fiscal_year(run, fiscal_year)
        except TdcsimCboContractError:
            continue
        complete.append(fiscal_year)
    return tuple(complete)


def _cbo_nominal_gdp_by_fiscal_year_from_directory(root: Path) -> dict[int, Decimal]:
    path = _cbo_budget_projection_workbook_path(root)
    if path is None:
        return {}
    rows = parse_cbo_budget_projection_rows(path)
    out: dict[int, Decimal] = {}
    for row in rows:
        if row.get("metric") != "gdp_bil":
            continue
        fiscal_year = int(row["fiscal_year"])
        value = _decimal(row["value"])
        prior = out.setdefault(fiscal_year, value)
        if prior != value:
            raise TdcsimCboContractError(
                f"CBO GDP denominator bridge found conflicting GDP for FY{fiscal_year}"
            )
    return dict(sorted(out.items()))


def _cbo_budget_projection_workbook_path(root: Path) -> Path | None:
    artifact = _artifact_view_for_path(root)
    if artifact is not None:
        matches = [
            path
            for path in artifact.list_files(prefix="runs/", suffix=".xlsx")
            if "budget-projections" in Path(path).name.lower()
        ]
        if not matches:
            return None
        return artifact.object_path(sorted(matches)[0])
    matches = sorted(
        path
        for path in root.glob("runs/**/*.xlsx")
        if "budget-projections" in path.name.lower()
    )
    return matches[0] if matches else None


def _read_frozen_denominator_map(path: Path) -> dict[int, Decimal]:
    artifact = _artifact_view_for_path(path)
    if artifact is not None:
        logical_path = _artifact_logical_path(artifact, path)
        if not artifact.has_file(logical_path):
            raise TdcsimCboContractError(
                "missing frozen denominator map for TDCSim CBO scenario suite: "
                f"{path}"
            )
        with artifact.open_text(logical_path) as handle:
            rows = list(csv.DictReader(handle))
        return _frozen_denominator_map_from_rows(rows)
    if not path.exists():
        raise TdcsimCboContractError(
            f"missing frozen denominator map for TDCSim CBO scenario suite: {path}"
        )
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return _frozen_denominator_map_from_rows(rows)


def _frozen_denominator_map_from_rows(rows: list[dict[str, str]]) -> dict[int, Decimal]:
    if not rows:
        raise TdcsimCboContractError("frozen denominator map must not be empty")
    required = {"fiscal_year", "frozen_denominator_bil"}
    missing = required - set(rows[0])
    if missing:
        raise TdcsimCboContractError(
            f"frozen denominator map missing fields: {sorted(missing)}"
        )
    out: dict[int, Decimal] = {}
    for row in rows:
        fiscal_year = int(row["fiscal_year"])
        denominator = _decimal(row["frozen_denominator_bil"])
        if fiscal_year in out:
            raise TdcsimCboContractError(
                f"duplicate frozen denominator fiscal year: {fiscal_year}"
            )
        if denominator <= 0:
            raise TdcsimCboContractError(
                f"frozen denominator must be positive for FY{fiscal_year}"
            )
        out[fiscal_year] = denominator
    return out


def _validate_handoff_tables(
    tables: Mapping[str, tuple[Mapping[str, str], ...]],
    manifest: Mapping[str, Any],
    *,
    expected_mmf_deposit_pass_through: Decimal | None,
    tolerance: Decimal,
) -> dict[str, str]:
    metadata: dict[str, str] | None = None
    for table_name, rows in tables.items():
        fields = set(rows[0])
        missing = TABLE_REQUIRED_FIELDS[table_name] - fields
        if missing:
            raise TdcsimCboContractError(
                f"{table_name} missing required fields: {sorted(missing)}"
            )
        meta_missing = COMMON_METADATA_FIELDS - fields
        if meta_missing:
            raise TdcsimCboContractError(
                f"{table_name} missing metadata fields: {sorted(meta_missing)}"
            )
        table_metadata = _constant_metadata(table_name, rows)
        if metadata is None:
            metadata = table_metadata
        elif table_metadata != metadata:
            raise TdcsimCboContractError(
                f"{table_name} metadata differs from other handoff tables"
            )
    assert metadata is not None
    _validate_manifest_metadata(manifest, metadata)
    _validate_mmf(metadata, expected_mmf_deposit_pass_through)
    _validate_flow_ids(tables)
    _validate_tdc_summary(tables["tdcsim_period_tdc_summary"], tolerance)
    _validate_tdc_components(tables["tdcsim_period_tdc_components"])
    _validate_component_sums(
        tables["tdcsim_period_tdc_summary"],
        tables["tdcsim_period_tdc_components"],
        tolerance,
    )
    _validate_route_stock_closure(
        tables["tdcsim_tdc_principal_route_stocks"],
        tables["tdcsim_tdc_principal_route_stock_closure"],
        tolerance,
    )
    return metadata


def _constant_metadata(
    table_name: str,
    rows: tuple[Mapping[str, str], ...],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in COMMON_METADATA_FIELDS:
        distinct = {row.get(field, "") for row in rows}
        if len(distinct) != 1 or "" in distinct:
            raise TdcsimCboContractError(
                f"{table_name} field {field} must be present and constant"
            )
        values[field] = next(iter(distinct))
    return values


def _validate_manifest_metadata(
    manifest: Mapping[str, Any],
    metadata: Mapping[str, str],
) -> None:
    manifest_scenario = _nested_manifest_value(manifest, "scenario", "scenario_id")
    if manifest_scenario and manifest_scenario != metadata["scenario_id"]:
        raise TdcsimCboContractError(
            "manifest scenario_id does not match handoff metadata"
        )
    manifest_run = _nested_manifest_value(manifest, "run_id")
    if manifest_run and manifest_run != metadata["run_id"]:
        raise TdcsimCboContractError("manifest run_id does not match handoff metadata")


def _nested_manifest_value(manifest: Mapping[str, Any], *keys: str) -> str:
    value: Any = manifest
    for key in keys:
        if not isinstance(value, Mapping) or key not in value:
            return ""
        value = value[key]
    return str(value) if value not in (None, "") else ""


def _validate_mmf(
    metadata: Mapping[str, str],
    expected_mmf_deposit_pass_through: Decimal | None,
) -> None:
    pass_through = _decimal(metadata["mmf_deposit_pass_through"])
    if pass_through < 0 or pass_through > 1:
        raise TdcsimCboContractError("mmf_deposit_pass_through must be in [0, 1]")
    if (
        expected_mmf_deposit_pass_through is not None
        and pass_through != expected_mmf_deposit_pass_through
    ):
        raise TdcsimCboContractError(
            "mmf_deposit_pass_through differs from expected scenario value"
        )


def _validate_flow_ids(
    tables: Mapping[str, tuple[Mapping[str, str], ...]],
) -> None:
    for table_name in (
        "tdcsim_period_issuance_flows",
        "tdcsim_period_principal_flows",
        "tdcsim_period_payment_flows",
    ):
        seen: set[str] = set()
        for row in tables[table_name]:
            flow_id = row.get("flow_id", "")
            security_id = row.get("security_id", "")
            if not flow_id or not security_id:
                raise TdcsimCboContractError(
                    f"{table_name} requires nonempty flow_id and security_id"
                )
            if flow_id in seen:
                raise TdcsimCboContractError(f"{table_name} duplicate flow_id {flow_id}")
            seen.add(flow_id)


def _validate_tdc_summary(
    rows: tuple[Mapping[str, str], ...],
    tolerance: Decimal,
) -> None:
    for row in rows:
        identity = (
            _decimal(row["tdc_fiscal_flow_bil"])
            + _decimal(row["tdc_debt_service_bil"])
            + _decimal(row["tdc_auction_absorption_du_bil"])
            + _decimal(row["tdc_secondary_trades_bil"])
            + _decimal(row["tdc_other_bil"])
        )
        _require_close(identity, _decimal(row["tdc_change_bil"]), tolerance)
        ex_overlap = _decimal(row["tdc_change_bil"]) - _decimal(
            row["overlap_cashflow_bil"]
        )
        _require_close(ex_overlap, _decimal(row["tdc_change_ex_overlap_bil"]), tolerance)
        if abs(_decimal(row["component_sum_error_bil"])) > tolerance:
            raise TdcsimCboContractError("TDC component sum error exceeds tolerance")
        if row["tdc_amount_basis"] != EXPECTED_TDC_AMOUNT_BASIS:
            raise TdcsimCboContractError("unexpected TDC amount basis")
        if row["overlap_policy"] != EXPECTED_TDC_OVERLAP_POLICY:
            raise TdcsimCboContractError("unexpected TDC overlap policy")


def _validate_tdc_components(rows: tuple[Mapping[str, str], ...]) -> None:
    for row in rows:
        direct = _bool(row["enters_direct_interest_support"])
        default_tdc = _bool(row["enters_tdc_deposit_support_default"])
        if direct and default_tdc:
            raise TdcsimCboContractError(
                "TDC component cannot enter direct support and default TDC support"
            )
        if row["tdc_amount_basis"] != EXPECTED_TDC_AMOUNT_BASIS:
            raise TdcsimCboContractError("unexpected component TDC amount basis")
        if row["overlap_policy"] != EXPECTED_TDC_OVERLAP_POLICY:
            raise TdcsimCboContractError("unexpected component overlap policy")
        if direct and row.get("holder_subsector") != "domestic_nonbank_deposit_funded":
            raise TdcsimCboContractError(
                "direct-interest support must be domestic nonbank deposit funded"
            )
        if row.get("payment_type") == "tips_indexation":
            if _bool(row["is_additive_to_tdc_change"]) or direct:
                raise TdcsimCboContractError(
                    "TIPS indexation cannot be additive direct-interest support"
                )


def _validate_component_sums(
    summary_rows: tuple[Mapping[str, str], ...],
    component_rows: tuple[Mapping[str, str], ...],
    tolerance: Decimal,
) -> None:
    component_sums: dict[tuple[str, str], Decimal] = {}
    for row in component_rows:
        if not _bool(row["is_additive_to_tdc_change"]):
            continue
        key = (row["period_start"], row["period_end"])
        component_sums[key] = component_sums.get(key, Decimal("0")) + _decimal(
            row["amount_bil"]
        )
    for row in summary_rows:
        key = (row["period_start"], row["period_end"])
        component_sum = component_sums.get(key)
        if component_sum is None:
            raise TdcsimCboContractError(
                f"missing additive TDC component rows for period {key}"
            )
        _require_close(component_sum, _decimal(row["component_sum_bil"]), tolerance)


def _validate_route_stock_closure(
    stock_rows: tuple[Mapping[str, str], ...],
    closure_rows: tuple[Mapping[str, str], ...],
    tolerance: Decimal,
) -> None:
    if not stock_rows:
        raise TdcsimCboContractError("missing TDC principal route stock rows")
    if not closure_rows:
        raise TdcsimCboContractError("missing TDC principal route stock closure rows")
    for row in stock_rows:
        if row["route_stock_basis"] != "tdc_principal_settlement_route":
            raise TdcsimCboContractError("unexpected route stock basis")
    for row in closure_rows:
        if row["route_stock_basis"] != "tdc_principal_settlement_route":
            raise TdcsimCboContractError("unexpected route closure stock basis")
        identity = (
            _decimal(row["opening_route_stock_bil"])
            + _decimal(row["route_face_issued_bil"])
            - _decimal(row["route_face_redeemed_bil"])
            + _decimal(row["route_stock_residual_or_indexation_bil"])
        )
        _require_close(identity, _decimal(row["closing_route_stock_bil"]), tolerance)
        if abs(_decimal(row["closure_identity_error_bil"])) > tolerance:
            raise TdcsimCboContractError("route stock closure identity error exceeds tolerance")


def _rows_for_fiscal_year(
    rows: Iterable[Mapping[str, str]],
    fiscal_year: int,
) -> tuple[Mapping[str, str], ...]:
    return tuple(
        row
        for row in rows
        if fiscal_year_for_date(row.get("period_end") or row.get("date", ""))
        == fiscal_year
    )


def _scenario_interpretation(scenario_id: str) -> tuple[str, str, str, str]:
    if scenario_id in _SCENARIO_INTERPRETATION_BY_ID:
        return _SCENARIO_INTERPRETATION_BY_ID[scenario_id]
    if "baseline" in scenario_id and "noop" in scenario_id:
        return ("baseline", "Baseline", "core", "true")
    return (
        "unclassified_scenario",
        scenario_id,
        "diagnostic_unclassified_pending_review",
        "false",
    )


def _baseline_records_by_year(
    records: Iterable[Mapping[str, Any]],
    baseline_scenario_id: str | None,
) -> dict[int, Mapping[str, Any]]:
    records_by_year: dict[int, list[Mapping[str, Any]]] = {}
    for record in records:
        records_by_year.setdefault(record["fiscal_year"], []).append(record)
    baseline_by_year: dict[int, Mapping[str, Any]] = {}
    for fiscal_year, year_records in records_by_year.items():
        if baseline_scenario_id is not None:
            candidates = [
                row for row in year_records if row["scenario_id"] == baseline_scenario_id
            ]
        else:
            candidates = [
                row for row in year_records if row["scenario_role"] == "baseline"
            ]
        if len(candidates) != 1:
            raise TdcsimCboContractError(
                f"expected exactly one baseline scenario for FY{fiscal_year}, "
                f"found {len(candidates)}"
            )
        baseline_by_year[fiscal_year] = candidates[0]
    return baseline_by_year


def _summary_totals(run: TdcsimCboRun, fiscal_year: int) -> dict[str, Decimal]:
    rows = _rows_for_fiscal_year(run.tables["tdcsim_period_tdc_summary"], fiscal_year)
    fields = (
        "tdc_fiscal_flow_bil",
        "tdc_debt_service_principal_to_du_bil",
        "gross_principal_cash_paid_to_du_bil",
        "tdc_debt_service_interest_to_du_bil",
        "tdc_auction_absorption_du_bil",
        "tdc_secondary_trades_bil",
        "tdc_other_bil",
        "overlap_cashflow_bil",
        "tdc_change_ex_overlap_bil",
        "gross_issuance_cash_proceeds_bil",
        "gross_issuance_proceeds_absorbed_by_du_bil",
    )
    totals = {
        field: sum((_decimal(row.get(field)) for row in rows), Decimal("0"))
        for field in fields
    }
    totals["du_bill_discount_interest_bil"] = (
        totals["gross_principal_cash_paid_to_du_bil"]
        - totals["tdc_debt_service_principal_to_du_bil"]
    )
    return totals


def _lever_record(
    run: TdcsimCboRun,
    fiscal_year: int,
    denominator_by_fiscal_year: Mapping[int, Decimal | str | int | float],
    profile: CboNumeratorProfile,
) -> dict[str, Decimal]:
    numerator = assemble_cbo_fiscal_year_numerator(
        run,
        fiscal_year,
        profile=profile,
    )
    ratio = attach_frozen_denominators([numerator], denominator_by_fiscal_year)[0]
    summary = _summary_totals(run, fiscal_year)
    debt = _debt_target_totals(run, fiscal_year)
    route = _route_stock_totals(run, fiscal_year)
    return {
        "ratewall_ratio": ratio.ratio,
        "total_current_demand_support_bil": numerator.total_current_demand_support_bil,
        "tdc_current_demand_support_bil": numerator.tdc_current_demand_support_bil,
        "tdc_fiscal_flow_bil": summary["tdc_fiscal_flow_bil"],
        "tdc_change_ex_overlap_bil": summary["tdc_change_ex_overlap_bil"],
        "direct_treasury_current_demand_support_bil": (
            numerator.direct_treasury_current_demand_support_bil
        ),
        "bank_treasury_current_demand_support_bil": (
            numerator.bank_treasury_current_demand_support_bil
        ),
        "controlled_debt_post_issuance_bil": debt[
            "controlled_debt_post_issuance_bil"
        ],
        "route_face_issued_bil": route["route_face_issued_bil"],
        "route_face_redeemed_bil": route["route_face_redeemed_bil"],
        "gross_issuance_cash_proceeds_bil": summary[
            "gross_issuance_cash_proceeds_bil"
        ],
        "gross_issuance_proceeds_absorbed_by_du_bil": summary[
            "gross_issuance_proceeds_absorbed_by_du_bil"
        ],
    }


def _debt_target_totals(run: TdcsimCboRun, fiscal_year: int) -> dict[str, Decimal]:
    rows = _rows_for_fiscal_year(run.tables["tdcsim_debt_target_bridge"], fiscal_year)
    fields = (
        "controlled_debt_post_issuance_bil",
    )
    return {
        field: sum((_decimal(row.get(field)) for row in rows), Decimal("0"))
        for field in fields
    }


def _route_stock_totals(run: TdcsimCboRun, fiscal_year: int) -> dict[str, Decimal]:
    rows = _rows_for_fiscal_year(
        run.tables["tdcsim_tdc_principal_route_stock_closure"],
        fiscal_year,
    )
    fields = (
        "route_face_issued_bil",
        "route_face_redeemed_bil",
    )
    return {
        field: sum((_decimal(row.get(field)) for row in rows), Decimal("0"))
        for field in fields
    }


def _scenario_override(run: TdcsimCboRun, lever_name: str) -> str:
    scenario_path = run.root / "scenario.json"
    artifact = _artifact_view_for_path(scenario_path)
    if artifact is not None:
        logical_path = _artifact_logical_path(artifact, scenario_path)
        if not artifact.has_file(logical_path):
            return ""
        scenario = json.loads(artifact.read_text(logical_path))
        override = scenario.get("overrides", {}).get(lever_name, {})
        return json.dumps(override, sort_keys=True, separators=(",", ":"))
    if not scenario_path.exists():
        return ""
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    override = scenario.get("overrides", {}).get(lever_name, {})
    return json.dumps(override, sort_keys=True, separators=(",", ":"))


def _lever_response_status(
    lever_name: str,
    deltas: Mapping[str, Decimal],
) -> str:
    active_fields = [
        field
        for field, value in deltas.items()
        if abs(value) > _LEVER_ACTIVE_TOLERANCE
    ]
    if lever_name == "primary_deficit":
        debt_and_route_fields = (
            "controlled_debt_post_issuance_bil",
            "route_face_issued_bil",
            "route_face_redeemed_bil",
            "gross_issuance_cash_proceeds_bil",
            "gross_issuance_proceeds_absorbed_by_du_bil",
        )
        debt_route_changed = any(
            abs(deltas[field]) > _LEVER_ACTIVE_TOLERANCE
            for field in debt_and_route_fields
        )
        if (
            abs(deltas["tdc_fiscal_flow_bil"]) > _LEVER_ACTIVE_TOLERANCE
            and not debt_route_changed
        ):
            return "active_tdc_fiscal_flow_only_debt_path_fixed"
    if lever_name == "operating_cash" and not active_fields:
        return "no_exported_ratewall_numerator_effect"
    if lever_name == "fed_holdings" and not active_fields:
        return "baseline_equivalent_scale_value"
    if not active_fields:
        return "no_observed_effect"
    return "active_mixed_or_unclassified_effect"


def _lever_interpretation_status(response_status: str) -> str:
    if response_status == "active_tdc_fiscal_flow_only_debt_path_fixed":
        return "usable_as_tdc_fiscal_incidence_sensitivity_not_debt_sizing_shock"
    if response_status in {
        "no_exported_ratewall_numerator_effect",
        "baseline_equivalent_scale_value",
        "no_observed_effect",
    }:
        return "do_not_promote_to_active_model_shock"
    return "diagnostic_only_requires_matched_endpoint_design"


def _lever_activation_evidence(deltas: Mapping[str, Decimal]) -> str:
    evidence_fields = (
        "delta_tdc_fiscal_flow_bil",
        "delta_tdc_change_ex_overlap_bil",
        "delta_total_current_demand_support_bil",
        "delta_controlled_debt_post_issuance_bil",
        "delta_route_face_issued_bil",
        "delta_gross_issuance_cash_proceeds_bil",
    )
    source = {
        f"delta_{field}": value
        for field, value in deltas.items()
    }
    return ";".join(
        f"{field}={_fmt(source[field])}"
        for field in evidence_fields
    )


def _sum_components(
    rows: Iterable[Mapping[str, str]],
    fiscal_year: int,
    *,
    direct_interest: bool,
    holder_sector: str,
    holder_subsector: str,
) -> Decimal:
    total = Decimal("0")
    for row in _rows_for_fiscal_year(rows, fiscal_year):
        if _bool(row["enters_direct_interest_support"]) != direct_interest:
            continue
        if row["holder_sector"] != holder_sector:
            continue
        if row["holder_subsector"] != holder_subsector:
            continue
        if row["payment_type"] not in DIRECT_SUPPORT_PAYMENT_TYPES:
            continue
        total += _decimal(row["amount_bil"])
    return total


def _sum_payment_flows(
    rows: Iterable[Mapping[str, str]],
    fiscal_year: int,
    *,
    holder_sector: str,
) -> Decimal:
    total = Decimal("0")
    for row in _rows_for_fiscal_year(rows, fiscal_year):
        if row["holder_sector"] != holder_sector:
            continue
        if row["payment_type"] not in DIRECT_SUPPORT_PAYMENT_TYPES:
            continue
        total += _decimal(row["amount_bil"])
    return total


def _du_maturity_cash_bridge_rows(
    run: TdcsimCboRun,
    fiscal_year: int,
) -> list[dict[str, str]]:
    totals = _summary_totals(run, fiscal_year)
    gross_cash = totals["gross_principal_cash_paid_to_du_bil"]
    principal = totals["tdc_debt_service_principal_to_du_bil"]
    bill_discount = totals["du_bill_discount_interest_bil"]
    return [
        _settlement_bridge_row(
            run,
            fiscal_year,
            bridge_family="du_maturity_cash_decomposition",
            holder_sector="Private",
            holder_subsector="domestic_ultimate_route",
            instrument_type="aggregate_treasury",
            payment_type="gross_maturity_cash",
            accounting_basis="settlement_cash_decomposed",
            is_additive_to_cash_total="true",
            settlement_cash_bil=gross_cash,
            principal_component_bil=principal,
            interest_or_accrual_component_bil=bill_discount,
            budget_accrual_bil=bill_discount,
            ratewall_current_demand_basis_bil=Decimal("0"),
            cbo_reconciliation_basis_bil=gross_cash,
            treatment_note=(
                "gross DU maturity cash equals principal component plus bill-discount "
                "interest; do not use gross cash as principal while retaining discount "
                "interest separately"
            ),
        )
    ]


def _payment_flow_accounting_bridge_rows(
    run: TdcsimCboRun,
    fiscal_year: int,
) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str, str, str, str], Decimal] = {}
    for row in _rows_for_fiscal_year(
        run.tables["tdcsim_period_payment_flows"],
        fiscal_year,
    ):
        key = (
            row["holder_sector"],
            row["holder_subsector"],
            row["instrument_type"],
            row["payment_type"],
            row["accounting_basis"],
            str(_bool(row["is_additive_to_cash_total"])).lower(),
        )
        groups[key] = groups.get(key, Decimal("0")) + _decimal(row["amount_bil"])
    out: list[dict[str, str]] = []
    for (
        holder_sector,
        holder_subsector,
        instrument_type,
        payment_type,
        accounting_basis,
        is_additive,
    ), amount in sorted(groups.items()):
        additive = is_additive == "true"
        ratewall_basis = (
            amount
            if holder_sector == "Banks" and payment_type in DIRECT_SUPPORT_PAYMENT_TYPES
            else Decimal("0")
        )
        out.append(
            _settlement_bridge_row(
                run,
                fiscal_year,
                bridge_family="payment_flow_accounting_basis",
                holder_sector=holder_sector,
                holder_subsector=holder_subsector,
                instrument_type=instrument_type,
                payment_type=payment_type,
                accounting_basis=accounting_basis,
                is_additive_to_cash_total=is_additive,
                settlement_cash_bil=amount if additive else Decimal("0"),
                principal_component_bil=Decimal("0"),
                interest_or_accrual_component_bil=amount,
                budget_accrual_bil=amount if not additive else Decimal("0"),
                ratewall_current_demand_basis_bil=ratewall_basis,
                cbo_reconciliation_basis_bil=amount,
                treatment_note=(
                    "payment-flow basis row; noncash budget-accrual amounts may be "
                    "included in interest decomposition without being additive cash"
                ),
            )
        )
    return out


def _direct_interest_component_bridge_rows(
    run: TdcsimCboRun,
    fiscal_year: int,
) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str, str, str], Decimal] = {}
    for row in _rows_for_fiscal_year(
        run.tables["tdcsim_period_tdc_components"],
        fiscal_year,
    ):
        if not _bool(row["enters_direct_interest_support"]):
            continue
        key = (
            row["holder_sector"],
            row["holder_subsector"],
            row["instrument_type"],
            row["payment_type"],
            row["accounting_basis"],
        )
        groups[key] = groups.get(key, Decimal("0")) + _decimal(row["amount_bil"])
    out: list[dict[str, str]] = []
    for (
        holder_sector,
        holder_subsector,
        instrument_type,
        payment_type,
        accounting_basis,
    ), amount in sorted(groups.items()):
        out.append(
            _settlement_bridge_row(
                run,
                fiscal_year,
                bridge_family="direct_interest_component_basis",
                holder_sector=holder_sector,
                holder_subsector=holder_subsector,
                instrument_type=instrument_type,
                payment_type=payment_type,
                accounting_basis=accounting_basis,
                is_additive_to_cash_total="component",
                settlement_cash_bil=(
                    amount if accounting_basis == "cash" else Decimal("0")
                ),
                principal_component_bil=Decimal("0"),
                interest_or_accrual_component_bil=amount,
                budget_accrual_bil=(
                    amount if accounting_basis != "cash" else Decimal("0")
                ),
                ratewall_current_demand_basis_bil=amount,
                cbo_reconciliation_basis_bil=amount,
                treatment_note=(
                    "direct domestic-nonbank interest component removed from default "
                    "TDC support and added once through direct-interest support"
                ),
            )
        )
    return out


def _settlement_bridge_row(
    run: TdcsimCboRun,
    fiscal_year: int,
    *,
    bridge_family: str,
    holder_sector: str,
    holder_subsector: str,
    instrument_type: str,
    payment_type: str,
    accounting_basis: str,
    is_additive_to_cash_total: str,
    settlement_cash_bil: Decimal,
    principal_component_bil: Decimal,
    interest_or_accrual_component_bil: Decimal,
    budget_accrual_bil: Decimal,
    ratewall_current_demand_basis_bil: Decimal,
    cbo_reconciliation_basis_bil: Decimal,
    treatment_note: str,
) -> dict[str, str]:
    row_id = "::".join(
        (
            "tdcsim_cbo_settlement_accrual_bridge",
            str(fiscal_year),
            run.metadata["scenario_id"],
            bridge_family,
            holder_sector or "none",
            holder_subsector or "none",
            instrument_type or "none",
            payment_type or "none",
            accounting_basis or "none",
            is_additive_to_cash_total or "none",
        )
    )
    return {
        "tdcsim_cbo_settlement_accrual_bridge_row_id": row_id,
        "scenario_id": run.metadata["scenario_id"],
        "fiscal_year": str(fiscal_year),
        "bridge_family": bridge_family,
        "holder_sector": holder_sector,
        "holder_subsector": holder_subsector,
        "instrument_type": instrument_type,
        "payment_type": payment_type,
        "accounting_basis": accounting_basis,
        "is_additive_to_cash_total": is_additive_to_cash_total,
        "settlement_cash_bil": _fmt(settlement_cash_bil),
        "principal_component_bil": _fmt(principal_component_bil),
        "interest_or_accrual_component_bil": _fmt(interest_or_accrual_component_bil),
        "budget_accrual_bil": _fmt(budget_accrual_bil),
        "ratewall_current_demand_basis_bil": _fmt(ratewall_current_demand_basis_bil),
        "cbo_reconciliation_basis_bil": _fmt(cbo_reconciliation_basis_bil),
        "treatment_note": treatment_note,
        "allowed_use": "settlement_cash_budget_accrual_measurement_bridge",
        "blocked_use": (
            "direct_denominator_change;principal_double_count;"
            "canonical_headline_promotion"
        ),
        "canonical_ratio_entry": "false",
    }


def _delta_direction(value: Decimal) -> str:
    if value > 0:
        return "above_baseline"
    if value < 0:
        return "below_baseline"
    return "baseline"


def _route_stock_closure_row(
    run: TdcsimCboRun,
    fiscal_year: int,
    source: Mapping[str, str],
) -> dict[str, str]:
    row_id = "::".join(
        (
            "tdcsim_cbo_route_stock_closure",
            str(fiscal_year),
            run.metadata["scenario_id"],
            source["period_start"],
            source["period_end"],
            source["route_holder_sector"] or "none",
            source["route_holder_subsector"] or "none",
            source["instrument_type"] or "none",
            source["maturity_bucket"] or "none",
            source["debt_scope"] or "none",
        )
    )
    return {
        "tdcsim_cbo_route_stock_closure_row_id": row_id,
        "scenario_id": run.metadata["scenario_id"],
        "fiscal_year": str(fiscal_year),
        "period_start": source["period_start"],
        "period_end": source["period_end"],
        "route_holder_sector": source["route_holder_sector"],
        "route_holder_subsector": source["route_holder_subsector"],
        "instrument_type": source["instrument_type"],
        "maturity_bucket": source["maturity_bucket"],
        "debt_scope": source["debt_scope"],
        "opening_route_stock_bil": _fmt(_decimal(source["opening_route_stock_bil"])),
        "route_face_issued_bil": _fmt(_decimal(source["route_face_issued_bil"])),
        "route_face_redeemed_bil": _fmt(_decimal(source["route_face_redeemed_bil"])),
        "route_stock_residual_or_indexation_bil": _fmt(
            _decimal(source["route_stock_residual_or_indexation_bil"])
        ),
        "closing_route_stock_bil": _fmt(_decimal(source["closing_route_stock_bil"])),
        "closure_identity_error_bil": _fmt(
            _decimal(source["closure_identity_error_bil"])
        ),
        "route_stock_basis": source["route_stock_basis"],
        "residual_basis": source["residual_basis"],
        "allowed_use": "tdcsim_principal_route_stock_closure_diagnostic",
        "blocked_use": "denominator_replacement_or_canonical_ratio_math",
        "canonical_ratio_entry": "false",
    }


def _dominant_delta_support_component(row: Mapping[str, str]) -> tuple[str, Decimal]:
    components = {
        "tdc_current_demand_support": _decimal(
            row["delta_tdc_current_demand_support_bil"]
        ),
        "direct_treasury_current_demand_support": _decimal(
            row["delta_direct_treasury_current_demand_support_bil"]
        ),
        "bank_treasury_current_demand_support": _decimal(
            row["delta_bank_treasury_current_demand_support_bil"]
        ),
    }
    component, value = max(
        components.items(),
        key=lambda item: (abs(item[1]), item[0]),
    )
    return component, value


def _empirical_scenario_interpretation_row(
    effect: Mapping[str, str],
    *,
    scenario_set_role: str,
    issuance_direction: str,
    term_premium_tier: str,
    ten_year_nominal_rate_shock_bp: Decimal | str | int | float,
    paired_issuance_only_scenario_id: str,
    comparison: Mapping[str, str] | None,
    model_interpretation: str,
) -> dict[str, str]:
    dominant_component, dominant_value = _dominant_delta_support_component(effect)
    overlay_delta = (
        comparison["rate_overlay_delta_ratewall_ratio"]
        if comparison is not None
        else "0"
    )
    offset_fraction = (
        comparison["offset_fraction_of_abs_issuance_effect"]
        if comparison is not None
        else "0"
    )
    remaining_fraction = (
        comparison["net_effect_fraction_remaining"]
        if comparison is not None
        else "1"
    )
    return {
        "tdcsim_cbo_empirical_scenario_interpretation_row_id": (
            "tdcsim_cbo_empirical_scenario_interpretation::"
            f"{effect['fiscal_year']}::{effect['scenario_id']}"
        ),
        "fiscal_year": effect["fiscal_year"],
        "scenario_set_role": scenario_set_role,
        "issuance_direction": issuance_direction,
        "term_premium_tier": term_premium_tier,
        "ten_year_nominal_rate_shock_bp": _fmt(
            _decimal(ten_year_nominal_rate_shock_bp)
        ),
        "scenario_id": effect["scenario_id"],
        "baseline_scenario_id": effect["baseline_scenario_id"],
        "paired_issuance_only_scenario_id": paired_issuance_only_scenario_id,
        "level_ratewall_ratio": effect["level_ratewall_ratio"],
        "delta_ratewall_ratio_vs_baseline": effect[
            "delta_ratewall_ratio_vs_baseline"
        ],
        "total_current_demand_support_bil": effect[
            "total_current_demand_support_bil"
        ],
        "delta_total_current_demand_support_bil": effect[
            "delta_total_current_demand_support_bil"
        ],
        "delta_tdc_current_demand_support_bil": effect[
            "delta_tdc_current_demand_support_bil"
        ],
        "delta_direct_treasury_current_demand_support_bil": effect[
            "delta_direct_treasury_current_demand_support_bil"
        ],
        "delta_bank_treasury_current_demand_support_bil": effect[
            "delta_bank_treasury_current_demand_support_bil"
        ],
        "delta_tdc_fiscal_flow_bil": effect["delta_tdc_fiscal_flow_bil"],
        "delta_tdc_debt_service_principal_to_du_bil": effect[
            "delta_tdc_debt_service_principal_to_du_bil"
        ],
        "delta_tdc_debt_service_interest_to_du_bil": effect[
            "delta_tdc_debt_service_interest_to_du_bil"
        ],
        "delta_tdc_auction_absorption_du_bil": effect[
            "delta_tdc_auction_absorption_du_bil"
        ],
        "rate_overlay_delta_ratewall_ratio": overlay_delta,
        "offset_fraction_of_abs_issuance_effect": offset_fraction,
        "net_effect_fraction_remaining": remaining_fraction,
        "dominant_delta_support_component": dominant_component,
        "dominant_delta_support_component_bil": _fmt(dominant_value),
        "model_interpretation": model_interpretation,
        "allowed_use": "assumption_mode_empirical_scenario_interpretation",
        "blocked_use": (
            "causal_market_yield_estimate;canonical_headline_promotion;"
            "denominator_change"
        ),
        "canonical_ratio_entry": "false",
    }


def _empirical_interpretation_sort_key(row: Mapping[str, str]) -> tuple[int, int, str]:
    direction_order = {
        "baseline": 0,
        "shorter": 1,
        "longer": 2,
    }
    role_order = {
        "baseline_anchor": 0,
        "issuance_only_control": 1,
        "coupled_bound_empirical_scenario": 2,
        "coupled_central_empirical_scenario": 2,
    }
    tier_order = {
        "none": 0,
        "conservative": 1,
        "central": 2,
        "high": 3,
    }
    return (
        direction_order.get(row["issuance_direction"], 99),
        role_order.get(row["scenario_set_role"], 99) * 10
        + tier_order.get(row["term_premium_tier"], 9),
        row["scenario_id"],
    )


def _model_scenario_summary_row(
    source: Mapping[str, str],
    *,
    summary_role: str,
    comparison_group: str,
    model_interpretation: str,
    primary_deficit_up_delta: Decimal,
) -> dict[str, str]:
    delta_rw = _decimal(source["delta_ratewall_ratio_vs_baseline"])
    primary_scale = (
        _safe_abs_ratio(delta_rw, primary_deficit_up_delta)
        if primary_deficit_up_delta
        else Decimal("0")
    )
    mechanism = _support_mechanism_attribution(source)
    return {
        "tdcsim_cbo_model_scenario_summary_row_id": (
            "tdcsim_cbo_model_scenario_summary::"
            f"{source['fiscal_year']}::{source['scenario_id']}"
        ),
        "fiscal_year": source["fiscal_year"],
        "summary_role": summary_role,
        "comparison_group": comparison_group,
        "scenario_id": source["scenario_id"],
        "baseline_scenario_id": source["baseline_scenario_id"],
        "paired_issuance_only_scenario_id": source[
            "paired_issuance_only_scenario_id"
        ],
        "term_premium_tier": source["term_premium_tier"],
        "ten_year_nominal_rate_shock_bp": source[
            "ten_year_nominal_rate_shock_bp"
        ],
        "level_ratewall_ratio": source["level_ratewall_ratio"],
        "delta_ratewall_ratio_vs_baseline": source[
            "delta_ratewall_ratio_vs_baseline"
        ],
        "delta_total_current_demand_support_bil": source[
            "delta_total_current_demand_support_bil"
        ],
        "delta_tdc_current_demand_support_bil": source[
            "delta_tdc_current_demand_support_bil"
        ],
        "delta_direct_treasury_current_demand_support_bil": source[
            "delta_direct_treasury_current_demand_support_bil"
        ],
        "delta_bank_treasury_current_demand_support_bil": source[
            "delta_bank_treasury_current_demand_support_bil"
        ],
        "component_delta_sum_check_bil": mechanism[
            "component_delta_sum_check_bil"
        ],
        "component_delta_sum_status": mechanism["component_delta_sum_status"],
        "tdc_delta_abs_contribution_share": mechanism[
            "tdc_delta_abs_contribution_share"
        ],
        "direct_treasury_delta_abs_contribution_share": mechanism[
            "direct_treasury_delta_abs_contribution_share"
        ],
        "bank_treasury_delta_abs_contribution_share": mechanism[
            "bank_treasury_delta_abs_contribution_share"
        ],
        "support_mechanism_profile": mechanism["support_mechanism_profile"],
        "rate_overlay_delta_ratewall_ratio": source[
            "rate_overlay_delta_ratewall_ratio"
        ],
        "offset_fraction_of_abs_issuance_effect": source[
            "offset_fraction_of_abs_issuance_effect"
        ],
        "primary_deficit_up_1pct_delta_ratewall_ratio": _fmt(
            primary_deficit_up_delta
        ),
        "abs_delta_vs_primary_deficit_up_1pct": _fmt_display_28(primary_scale),
        "dominant_delta_support_component": source[
            "dominant_delta_support_component"
        ],
        "dominant_delta_support_component_bil": source[
            "dominant_delta_support_component_bil"
        ],
        "model_interpretation": model_interpretation,
        "allowed_use": "assumption_mode_model_scenario_summary",
        "blocked_use": (
            "causal_market_yield_estimate;canonical_headline_promotion;"
            "denominator_change;evidence_mode_claim"
        ),
        "canonical_ratio_entry": "false",
    }


def _support_mechanism_attribution(row: Mapping[str, str]) -> dict[str, str]:
    components = {
        "tdc": _decimal(row["delta_tdc_current_demand_support_bil"]),
        "direct_treasury": _decimal(
            row["delta_direct_treasury_current_demand_support_bil"]
        ),
        "bank_treasury": _decimal(
            row["delta_bank_treasury_current_demand_support_bil"]
        ),
    }
    total = _decimal(row["delta_total_current_demand_support_bil"])
    component_sum = sum(components.values(), Decimal("0"))
    check = component_sum - total
    if abs(check) > _LEVER_ACTIVE_TOLERANCE:
        raise TdcsimCboContractError(
            "model scenario support components do not reconcile to total "
            f"delta for {row['scenario_id']}: {component_sum} vs {total}"
        )
    absolute_total = sum((abs(value) for value in components.values()), Decimal("0"))
    shares = {
        key: _safe_ratio(abs(value), absolute_total)
        for key, value in components.items()
    }
    dominant_key, dominant_value = max(
        components.items(),
        key=lambda item: (abs(item[1]), item[0]),
    )
    dominant_share = shares[dominant_key]
    return {
        "component_delta_sum_check_bil": _fmt(check),
        "component_delta_sum_status": (
            "pass_zero_delta"
            if absolute_total <= _LEVER_ACTIVE_TOLERANCE
            else "pass_components_sum_to_total_support_delta"
        ),
        "tdc_delta_abs_contribution_share": _fmt(shares["tdc"]),
        "direct_treasury_delta_abs_contribution_share": _fmt(
            shares["direct_treasury"]
        ),
        "bank_treasury_delta_abs_contribution_share": _fmt(
            shares["bank_treasury"]
        ),
        "support_mechanism_profile": _support_mechanism_profile(
            components,
            total=total,
            dominant_key=dominant_key,
            dominant_value=dominant_value,
            dominant_share=dominant_share,
        ),
    }


def _support_mechanism_profile(
    components: Mapping[str, Decimal],
    *,
    total: Decimal,
    dominant_key: str,
    dominant_value: Decimal,
    dominant_share: Decimal,
) -> str:
    if sum((abs(value) for value in components.values()), Decimal("0")) <= (
        _LEVER_ACTIVE_TOLERANCE
    ):
        return "baseline_or_zero_delta"
    has_offsetting_component = any(
        _sign_label(value) not in {"zero", _sign_label(total)}
        for value in components.values()
    )
    if has_offsetting_component:
        return "offsetting_mixed_support"
    if dominant_share >= Decimal("0.8"):
        if dominant_key == "tdc":
            return "tdc_support_dominant"
        if dominant_key == "direct_treasury":
            return "direct_treasury_interest_support_dominant"
        return "bank_treasury_interest_support_dominant"
    if abs(dominant_value) <= _LEVER_ACTIVE_TOLERANCE:
        return "baseline_or_zero_delta"
    return "mixed_support"


def _summary_source_from_effect(effect: Mapping[str, str]) -> dict[str, str]:
    dominant_component, dominant_value = _dominant_delta_support_component(effect)
    return {
        "fiscal_year": effect["fiscal_year"],
        "scenario_id": effect["scenario_id"],
        "baseline_scenario_id": effect["baseline_scenario_id"],
        "paired_issuance_only_scenario_id": "",
        "term_premium_tier": "none",
        "ten_year_nominal_rate_shock_bp": "0",
        "level_ratewall_ratio": effect["level_ratewall_ratio"],
        "delta_ratewall_ratio_vs_baseline": effect[
            "delta_ratewall_ratio_vs_baseline"
        ],
        "delta_total_current_demand_support_bil": effect[
            "delta_total_current_demand_support_bil"
        ],
        "delta_tdc_current_demand_support_bil": effect[
            "delta_tdc_current_demand_support_bil"
        ],
        "delta_direct_treasury_current_demand_support_bil": effect[
            "delta_direct_treasury_current_demand_support_bil"
        ],
        "delta_bank_treasury_current_demand_support_bil": effect[
            "delta_bank_treasury_current_demand_support_bil"
        ],
        "rate_overlay_delta_ratewall_ratio": "0",
        "offset_fraction_of_abs_issuance_effect": "0",
        "dominant_delta_support_component": dominant_component,
        "dominant_delta_support_component_bil": _fmt(dominant_value),
    }


def _model_summary_comparison_group(row: Mapping[str, str]) -> str:
    if row["issuance_direction"] in {"shorter", "longer"}:
        return f"{row['issuance_direction']}_issuance"
    return row["issuance_direction"]


def _model_summary_sort_key(row: Mapping[str, str]) -> tuple[int, int, int, str]:
    group_order = {
        "baseline": 0,
        "shorter_issuance": 1,
        "longer_issuance": 2,
        "rate_curve": 3,
        "primary_deficit": 4,
        "holder_preference": 5,
        "mmf_pass_through": 6,
        "combined_narrative": 7,
    }
    role_order = {
        "baseline_anchor": 0,
        "issuance_only_control": 1,
        "coupled_bound_empirical_scenario": 2,
        "coupled_central_empirical_scenario": 2,
        "rate_curve_comparator": 3,
        "fiscal_scale_comparator": 4,
        "holder_preference_comparator": 5,
        "mmf_pass_through_comparator": 6,
        "combined_narrative_scenario": 7,
    }
    return (
        int(row["fiscal_year"]),
        group_order.get(row["comparison_group"], 99),
        role_order.get(row["summary_role"], 99),
        row["scenario_id"],
    )


CURVE_DENOMINATOR_INPUT_WEIGHTS = {
    "5y": Decimal("0.25"),
    "10y": Decimal("0.5"),
    "30y": Decimal("0.25"),
}
CURVE_DENOMINATOR_ASSUMPTION_PROFILES = (
    (
        "low",
        Decimal("0"),
        "frozen_D_no_curve_denominator_response_bound",
    ),
    (
        "base",
        Decimal("0.125"),
        "small_curve_response_assumption_bound_not_empirical",
    ),
    (
        "high",
        Decimal("0.25"),
        "aggressive_small_curve_response_assumption_bound_not_empirical",
    ),
)


def _scenario_configs_by_id(
    scenario_config_dir: str | Path,
) -> dict[str, tuple[Path, Mapping[str, Any]]]:
    path = Path(scenario_config_dir)
    artifact = _artifact_view_for_path(path)
    if artifact is not None:
        prefix = _artifact_logical_path(artifact, path)
        if prefix and not prefix.endswith("/"):
            prefix = f"{prefix}/"
        out: dict[str, tuple[Path, Mapping[str, Any]]] = {}
        for scenario_logical_path in artifact.list_files(prefix=prefix, suffix=".json"):
            payload = json.loads(artifact.read_text(scenario_logical_path))
            if not isinstance(payload, Mapping):
                raise TdcsimCboContractError(
                    f"scenario config is not a JSON object: {scenario_logical_path}"
                )
            scenario_id = str(payload.get("scenario_id", ""))
            if not scenario_id:
                raise TdcsimCboContractError(
                    f"scenario config missing scenario_id: {scenario_logical_path}"
                )
            if scenario_id in out:
                raise TdcsimCboContractError(
                    f"duplicate scenario config for scenario_id {scenario_id}"
                )
            out[scenario_id] = (artifact.root / scenario_logical_path, payload)
        return out
    if not path.exists():
        return {}
    out: dict[str, tuple[Path, Mapping[str, Any]]] = {}
    for scenario_path in sorted(path.glob("*.json")):
        with scenario_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, Mapping):
            raise TdcsimCboContractError(
                f"scenario config is not a JSON object: {scenario_path}"
            )
        scenario_id = str(payload.get("scenario_id", ""))
        if not scenario_id:
            raise TdcsimCboContractError(
                f"scenario config missing scenario_id: {scenario_path}"
            )
        if scenario_id in out:
            raise TdcsimCboContractError(
                f"duplicate scenario config for scenario_id {scenario_id}"
            )
        out[scenario_id] = (scenario_path, payload)
    return out


def _curve_denominator_input_row(
    summary: Mapping[str, str],
    *,
    effect: Mapping[str, str],
    scenario_configs: Mapping[str, tuple[Path, Mapping[str, Any]]],
) -> dict[str, str]:
    overlay, source_id, source_status = _curve_overlay_for_summary(
        summary,
        scenario_configs,
    )
    weight_sum = sum(CURVE_DENOMINATOR_INPUT_WEIGHTS.values(), Decimal("0"))
    effective_overlay = (
        overlay["5y"] * CURVE_DENOMINATOR_INPUT_WEIGHTS["5y"]
        + overlay["10y"] * CURVE_DENOMINATOR_INPUT_WEIGHTS["10y"]
        + overlay["30y"] * CURVE_DENOMINATOR_INPUT_WEIGHTS["30y"]
    )
    return {
        "tdcsim_cbo_curve_denominator_input_row_id": (
            "tdcsim_cbo_curve_denominator_input::"
            f"{summary['fiscal_year']}::{summary['scenario_id']}"
        ),
        "source_model_scenario_summary_row_id": summary[
            "tdcsim_cbo_model_scenario_summary_row_id"
        ],
        "source_scenario_effect_row_id": effect[
            "tdcsim_cbo_scenario_effect_row_id"
        ],
        "fiscal_year": summary["fiscal_year"],
        "summary_role": summary["summary_role"],
        "comparison_group": summary["comparison_group"],
        "scenario_id": summary["scenario_id"],
        "baseline_scenario_id": summary["baseline_scenario_id"],
        "paired_issuance_only_scenario_id": summary[
            "paired_issuance_only_scenario_id"
        ],
        "term_premium_tier": summary["term_premium_tier"],
        "ten_year_nominal_rate_shock_bp": summary[
            "ten_year_nominal_rate_shock_bp"
        ],
        "curve_overlay_key_rate_source_id": source_id,
        "curve_overlay_key_rate_source_status": source_status,
        "curve_overlay_5y_bp": _fmt(overlay["5y"]),
        "curve_overlay_10y_bp": _fmt(overlay["10y"]),
        "curve_overlay_30y_bp": _fmt(overlay["30y"]),
        "curve_weight_5y": _fmt(CURVE_DENOMINATOR_INPUT_WEIGHTS["5y"]),
        "curve_weight_10y": _fmt(CURVE_DENOMINATOR_INPUT_WEIGHTS["10y"]),
        "curve_weight_30y": _fmt(CURVE_DENOMINATOR_INPUT_WEIGHTS["30y"]),
        "curve_weight_sum_status": (
            "pass_sum_to_one" if weight_sum == Decimal("1") else "fail_weight_sum"
        ),
        "effective_curve_overlay_bp": _fmt(effective_overlay),
        "denominator_response_model_id": "not_admitted_no_numeric_moving_d",
        "denominator_response_intensity": "",
        "denominator_response_coefficient_status": "not_admitted",
        "frozen_denominator_bil": effect["frozen_denominator_bil"],
        "delta_denominator_bil_from_curve": "",
        "moving_denominator_bil": "",
        "denominator_positive_guard_status": "not_evaluated_no_moving_d",
        "total_current_demand_support_bil": effect[
            "total_current_demand_support_bil"
        ],
        "frozen_ratewall_ratio": summary["level_ratewall_ratio"],
        "moving_ratewall_ratio": "",
        "frozen_delta_ratewall_ratio_vs_baseline": summary[
            "delta_ratewall_ratio_vs_baseline"
        ],
        "moving_delta_ratewall_ratio_vs_baseline": "",
        "moving_minus_frozen_ratewall_ratio": "",
        "denominator_response_direction": "not_admitted",
        "denominator_scope": "noncanonical_curve_vector_input_sidecar_only",
        "allowed_use": "assumption_mode_curve_vector_denominator_input_sidecar",
        "blocked_use": (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "path_ratio_denominator_replacement;"
            "maturity_curve_holder_specific_D_claim;release_headline_claim;"
            "numeric_moving_denominator_claim_without_response_profile"
        ),
        "claim_boundary": (
            "records_curve_overlay_inputs_only;"
            "does_not_estimate_denominator_response;"
            "does_not_change_frozen_ratewall_ratio"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
        "notes": (
            "curve vector is prepared for a later denominator response model; "
            "moving denominator fields are intentionally blank"
        ),
    }


def _curve_overlay_for_summary(
    summary: Mapping[str, str],
    scenario_configs: Mapping[str, tuple[Path, Mapping[str, Any]]],
) -> tuple[dict[str, Decimal], str, str]:
    scenario_id = summary["scenario_id"]
    ten_year_shock = _decimal(summary["ten_year_nominal_rate_shock_bp"])
    config = scenario_configs.get(scenario_id)
    if config is not None:
        path, payload = config
        overlay = _curve_overlay_from_scenario_config(payload, path)
        if _curve_overlay_has_nonzero(overlay):
            return overlay, str(path), "pass_explicit_key_rates"
        if ten_year_shock:
            raise TdcsimCboContractError(
                "scenario config has no usable curve overlay for nonzero "
                f"summary shock: {scenario_id}"
            )
        return overlay, str(path), "pass_zero_overlay_from_scenario_json"
    if ten_year_shock:
        return (
            {
                "5y": ten_year_shock / Decimal("2"),
                "10y": ten_year_shock,
                "30y": ten_year_shock,
            },
            "project_design_ladder",
            "project_design_ladder_not_scenario_json_verified",
        )
    return (
        {"5y": Decimal("0"), "10y": Decimal("0"), "30y": Decimal("0")},
        "",
        "not_applicable_zero_overlay",
    )


def _curve_overlay_from_scenario_config(
    payload: Mapping[str, Any],
    path: Path,
) -> dict[str, Decimal]:
    overrides = payload.get("overrides", {})
    if not isinstance(overrides, Mapping):
        raise TdcsimCboContractError(f"scenario overrides are invalid: {path}")
    curve = overrides.get("nominal_yield_curve")
    if curve is None:
        return {"5y": Decimal("0"), "10y": Decimal("0"), "30y": Decimal("0")}
    if not isinstance(curve, Mapping):
        raise TdcsimCboContractError(f"nominal_yield_curve is invalid: {path}")
    if curve.get("mode") == "parallel_bp":
        shock = _decimal(curve.get("shock_bp"))
        return {"5y": shock, "10y": shock, "30y": shock}
    if curve.get("mode") != "key_rate_bp":
        raise TdcsimCboContractError(
            f"unsupported nominal_yield_curve mode in {path}: {curve.get('mode')}"
        )
    shocks = curve.get("shocks")
    if not isinstance(shocks, list):
        raise TdcsimCboContractError(f"missing curve shocks list: {path}")
    by_tenor: dict[Decimal, Decimal] = {}
    for shock in shocks:
        if not isinstance(shock, Mapping):
            raise TdcsimCboContractError(f"invalid curve shock row: {path}")
        by_tenor[_decimal(shock.get("tenor_years"))] = _decimal(
            shock.get("shock_bp")
        )
    required = (Decimal("5"), Decimal("10"), Decimal("30"))
    missing = [tenor for tenor in required if tenor not in by_tenor]
    if missing:
        raise TdcsimCboContractError(
            f"missing required curve key-rate nodes in {path}: {missing}"
        )
    return {
        "5y": by_tenor[Decimal("5")],
        "10y": by_tenor[Decimal("10")],
        "30y": by_tenor[Decimal("30")],
    }


def _curve_overlay_has_nonzero(overlay: Mapping[str, Decimal]) -> bool:
    return any(value != Decimal("0") for value in overlay.values())


def _curve_sensitive_denominator_assumption_bound_row(
    input_row: Mapping[str, str],
    *,
    tier: str,
    theta: Decimal,
    label: str,
) -> dict[str, str]:
    effective_overlay = _decimal(input_row["effective_curve_overlay_bp"])
    frozen_denominator = _decimal(input_row["frozen_denominator_bil"])
    total_support = _decimal(input_row["total_current_demand_support_bil"])
    gamma = theta * CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE
    bil_per_bp = frozen_denominator * theta / Decimal("100")
    delta_denominator = bil_per_bp * effective_overlay
    moving_denominator = frozen_denominator + delta_denominator
    if moving_denominator <= 0:
        raise TdcsimCboContractError(
            "curve-sensitive denominator assumption produced nonpositive "
            f"moving denominator for {input_row['scenario_id']}::{tier}"
        )
    moving_ratewall_ratio = _safe_ratio(total_support, moving_denominator)
    frozen_ratewall_ratio = _decimal(input_row["frozen_ratewall_ratio"])
    return {
        "tdcsim_cbo_curve_sensitive_denominator_assumption_bound_row_id": (
            "tdcsim_cbo_curve_sensitive_denominator_assumption_bound::"
            f"{input_row['fiscal_year']}::{input_row['scenario_id']}::{tier}"
        ),
        "source_curve_denominator_input_row_id": input_row[
            "tdcsim_cbo_curve_denominator_input_row_id"
        ],
        "source_model_scenario_summary_row_id": input_row[
            "source_model_scenario_summary_row_id"
        ],
        "source_scenario_effect_row_id": input_row[
            "source_scenario_effect_row_id"
        ],
        "fiscal_year": input_row["fiscal_year"],
        "summary_role": input_row["summary_role"],
        "comparison_group": input_row["comparison_group"],
        "scenario_id": input_row["scenario_id"],
        "baseline_scenario_id": input_row["baseline_scenario_id"],
        "paired_issuance_only_scenario_id": input_row[
            "paired_issuance_only_scenario_id"
        ],
        "term_premium_tier": input_row["term_premium_tier"],
        "curve_overlay_key_rate_source_status": input_row[
            "curve_overlay_key_rate_source_status"
        ],
        "curve_overlay_5y_bp": input_row["curve_overlay_5y_bp"],
        "curve_overlay_10y_bp": input_row["curve_overlay_10y_bp"],
        "curve_overlay_30y_bp": input_row["curve_overlay_30y_bp"],
        "curve_weight_5y": input_row["curve_weight_5y"],
        "curve_weight_10y": input_row["curve_weight_10y"],
        "curve_weight_30y": input_row["curve_weight_30y"],
        "curve_weight_status": (
            "fixed_review_effective_key_rate_weights_not_empirical"
        ),
        "effective_curve_overlay_bp": input_row["effective_curve_overlay_bp"],
        "denominator_response_profile_tier": tier,
        "denominator_response_profile_id": (
            f"curve_denominator_assumption_bound_{tier}_20260626"
        ),
        "denominator_response_profile_label": label,
        "theta_curve_relative_to_policy_anchor": _fmt(theta),
        "gamma_curve_gdp_share_per_100bp": _fmt(gamma),
        "bil_per_bp_effective_curve": _fmt(bil_per_bp),
        "coefficient_admission_status": (
            "noncanonical_assumption_bound_only_not_estimated"
        ),
        "coefficient_source_status": (
            "not_literature_calibrated_not_econometrically_estimated"
        ),
        "coefficient_empirical_claim_allowed": "false",
        "shock_object_scope": (
            "nominal_treasury_key_rate_overlay_not_policy_rate_shock_"
            "not_private_real_rate_claim"
        ),
        "response_horizon": "annual_flow_h4_approximately_one_year",
        "transport_rule": (
            "gamma_curve_equals_theta_curve_times_frozen_policy_drag_anchor"
        ),
        "frozen_denominator_bil": input_row["frozen_denominator_bil"],
        "delta_denominator_bil_from_curve": _fmt(delta_denominator),
        "moving_denominator_bil": _fmt(moving_denominator),
        "denominator_positive_guard_status": "pass_positive_moving_denominator",
        "total_current_demand_support_bil": input_row[
            "total_current_demand_support_bil"
        ],
        "frozen_ratewall_ratio": input_row["frozen_ratewall_ratio"],
        "moving_ratewall_ratio": _fmt(moving_ratewall_ratio),
        "frozen_delta_ratewall_ratio_vs_baseline": input_row[
            "frozen_delta_ratewall_ratio_vs_baseline"
        ],
        "moving_delta_ratewall_ratio_vs_baseline": "",
        "moving_minus_frozen_ratewall_ratio": _fmt(
            moving_ratewall_ratio - frozen_ratewall_ratio
        ),
        "denominator_response_direction": _denominator_response_direction(
            delta_denominator
        ),
        "denominator_scope": (
            "noncanonical_curve_sensitive_denominator_assumption_bounds_only"
        ),
        "allowed_use": (
            "assumption_mode_curve_sensitive_denominator_bounds_sidecar"
        ),
        "blocked_use": (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "path_ratio_denominator_replacement;"
            "maturity_curve_holder_specific_D_claim;release_headline_claim;"
            "empirical_denominator_response_claim"
        ),
        "claim_boundary": (
            "nonempirical_assumption_bounds_only;frozen_D_summary_unchanged;"
            "not_literature_calibrated;not_econometrically_estimated"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
        "notes": (
            "2026-06-26 external calibration verdict: "
            "CONDITIONAL assumption-bounds-only; "
            "reject theta=1 full transport absent later econometric tranche"
        ),
    }


def _denominator_response_direction(delta_denominator: Decimal) -> str:
    if delta_denominator > 0:
        return "positive_curve_overlay_increases_denominator"
    if delta_denominator < 0:
        return "negative_curve_overlay_decreases_denominator"
    return "zero_curve_overlay_or_zero_theta_keeps_denominator_frozen"


def _curve_assumption_bound_sort_key(row: Mapping[str, str]) -> tuple[int, int, int, str]:
    tier_order = {"low": 0, "base": 1, "high": 2}
    return (
        _model_summary_sort_key(row)[0],
        _model_summary_sort_key(row)[1],
        _model_summary_sort_key(row)[2],
        tier_order.get(row["denominator_response_profile_tier"], 99),
        row["scenario_id"],
    )


def _model_scenario_interpretation_synthesis_row(
    summary: Mapping[str, str],
    *,
    beta: Mapping[str, str],
    bounds: list[dict[str, str]],
    selected: Mapping[str, str],
) -> dict[str, str]:
    if len(bounds) != len(CURVE_DENOMINATOR_ASSUMPTION_PROFILES):
        raise TdcsimCboContractError(
            "model interpretation synthesis requires one denominator-bound "
            f"row per profile for {summary['scenario_id']}"
        )
    point_delta = _decimal(summary["delta_ratewall_ratio_vs_baseline"])
    point_sign = _sign_label(point_delta)
    bound_delta_denominators = [
        _decimal(row["delta_denominator_bil_from_curve"]) for row in bounds
    ]
    bound_moving_deltas = [
        _decimal(row["moving_delta_ratewall_ratio_vs_baseline"])
        for row in bounds
    ]
    bound_signs = sorted({_sign_label(value) for value in bound_moving_deltas})
    denominator_status = _denominator_bound_sign_stability_status(
        point_sign,
        bound_signs,
    )
    interpretation = _final_model_interpretation(
        summary,
        beta["sign_stability_status"],
        denominator_status,
    )
    return {
        "tdcsim_cbo_model_scenario_interpretation_synthesis_row_id": (
            "tdcsim_cbo_model_scenario_interpretation_synthesis::"
            f"{summary['fiscal_year']}::{summary['scenario_id']}"
        ),
        "source_model_scenario_summary_row_id": summary[
            "tdcsim_cbo_model_scenario_summary_row_id"
        ],
        "source_beta_chi_sign_stability_row_id": beta[
            "tdcsim_cbo_beta_chi_sign_stability_row_id"
        ],
        "fiscal_year": summary["fiscal_year"],
        "summary_role": summary["summary_role"],
        "comparison_group": summary["comparison_group"],
        "scenario_id": summary["scenario_id"],
        "baseline_scenario_id": summary["baseline_scenario_id"],
        "paired_issuance_only_scenario_id": summary[
            "paired_issuance_only_scenario_id"
        ],
        "term_premium_tier": summary["term_premium_tier"],
        "point_calibration_delta_ratewall_ratio": summary[
            "delta_ratewall_ratio_vs_baseline"
        ],
        "point_calibration_sign": point_sign,
        "point_calibration_level_ratewall_ratio": summary[
            "level_ratewall_ratio"
        ],
        "beta_chi_sign_stability_status": beta["sign_stability_status"],
        "beta_chi_signs_observed": beta["signs_observed_over_grid"],
        "beta_chi_min_delta_ratewall_ratio": beta[
            "min_delta_ratewall_ratio_over_beta_chi_grid"
        ],
        "beta_chi_max_delta_ratewall_ratio": beta[
            "max_delta_ratewall_ratio_over_beta_chi_grid"
        ],
        "beta_chi_wall_hit_any_grid_cell": beta["wall_hit_any_grid_cell"],
        "curve_effective_overlay_bp": _shared_bound_field(
            bounds,
            "effective_curve_overlay_bp",
        ),
        "denominator_bound_theta_values": ";".join(
            row["theta_curve_relative_to_policy_anchor"]
            for row in sorted(bounds, key=_curve_assumption_bound_sort_key)
        ),
        "denominator_bound_min_delta_denominator_bil": _fmt(
            min(bound_delta_denominators)
        ),
        "denominator_bound_max_delta_denominator_bil": _fmt(
            max(bound_delta_denominators)
        ),
        "denominator_bound_min_moving_delta_ratewall_ratio_vs_baseline": _fmt(
            min(bound_moving_deltas)
        ),
        "denominator_bound_max_moving_delta_ratewall_ratio_vs_baseline": _fmt(
            max(bound_moving_deltas)
        ),
        "denominator_bound_signs_observed": ";".join(bound_signs),
        "denominator_bound_sign_stability_status": denominator_status,
        "selected_denominator_response_profile_id": selected[
            "denominator_response_profile_id"
        ],
        "selected_denominator_response_coefficient": selected[
            "denominator_response_coefficient"
        ],
        "selected_denominator_response_coefficient_unit": selected[
            "denominator_response_coefficient_unit"
        ],
        "selected_delta_denominator_bil": selected["delta_denominator_bil"],
        "selected_moving_denominator_bil": selected["moving_denominator_bil"],
        "selected_moving_ratewall_ratio": selected["moving_ratewall_ratio"],
        "selected_moving_delta_ratewall_ratio_vs_baseline": selected[
            "moving_delta_ratewall_ratio_vs_baseline"
        ],
        "selected_denominator_response_status": selected[
            "denominator_response_requirement_status"
        ],
        "primary_deficit_up_1pct_delta_ratewall_ratio": summary[
            "primary_deficit_up_1pct_delta_ratewall_ratio"
        ],
        "abs_delta_vs_primary_deficit_up_1pct": summary[
            "abs_delta_vs_primary_deficit_up_1pct"
        ],
        "primary_deficit_scale_bucket": _primary_deficit_scale_bucket(
            _decimal(summary["abs_delta_vs_primary_deficit_up_1pct"])
        ),
        "dominant_delta_support_component": summary[
            "dominant_delta_support_component"
        ],
        "dominant_delta_support_component_bil": summary[
            "dominant_delta_support_component_bil"
        ],
        "component_delta_sum_check_bil": summary["component_delta_sum_check_bil"],
        "component_delta_sum_status": summary["component_delta_sum_status"],
        "tdc_delta_abs_contribution_share": summary[
            "tdc_delta_abs_contribution_share"
        ],
        "direct_treasury_delta_abs_contribution_share": summary[
            "direct_treasury_delta_abs_contribution_share"
        ],
        "bank_treasury_delta_abs_contribution_share": summary[
            "bank_treasury_delta_abs_contribution_share"
        ],
        "support_mechanism_profile": summary["support_mechanism_profile"],
        "model_interpretation": summary["model_interpretation"],
        "final_interpretation": interpretation,
        "allowed_use": "assumption_mode_model_scenario_interpretation_synthesis",
        "blocked_use": (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "path_ratio_denominator_replacement;release_headline_claim;"
            "statistical_significance_claim;empirical_denominator_response_claim"
        ),
        "claim_boundary": (
            "combines_existing_noncanonical_model_surfaces_only;"
            "point_calibration_not_statistical_significance;"
            "denominator_bounds_are_nonempirical"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
    }


def _curve_denominator_empirical_status_row(
    synthesis: Mapping[str, str],
    *,
    bounds: list[dict[str, str]],
) -> dict[str, str]:
    if len(bounds) != len(CURVE_DENOMINATOR_ASSUMPTION_PROFILES):
        raise TdcsimCboContractError(
            "curve denominator empirical status requires one bound row per "
            f"profile for {synthesis['scenario_id']}"
        )
    coefficient_statuses = {
        row["coefficient_admission_status"] for row in bounds
    }
    source_statuses = {row["coefficient_source_status"] for row in bounds}
    empirical_allowed = {row["coefficient_empirical_claim_allowed"] for row in bounds}
    if coefficient_statuses != {"noncanonical_assumption_bound_only_not_estimated"}:
        raise TdcsimCboContractError(
            "unexpected admitted or mixed curve denominator coefficient status: "
            f"{coefficient_statuses}"
        )
    if source_statuses != {"not_literature_calibrated_not_econometrically_estimated"}:
        raise TdcsimCboContractError(
            "unexpected curve denominator coefficient source status: "
            f"{source_statuses}"
        )
    if empirical_allowed != {"false"}:
        raise TdcsimCboContractError(
            "curve denominator empirical status cannot allow empirical claims "
            f"from assumption-bound rows: {empirical_allowed}"
        )
    return {
        "tdcsim_cbo_curve_denominator_empirical_status_row_id": (
            "tdcsim_cbo_curve_denominator_empirical_status::"
            f"{synthesis['fiscal_year']}::{synthesis['scenario_id']}"
        ),
        "source_model_scenario_interpretation_synthesis_row_id": synthesis[
            "tdcsim_cbo_model_scenario_interpretation_synthesis_row_id"
        ],
        "fiscal_year": synthesis["fiscal_year"],
        "summary_role": synthesis["summary_role"],
        "comparison_group": synthesis["comparison_group"],
        "scenario_id": synthesis["scenario_id"],
        "baseline_scenario_id": synthesis["baseline_scenario_id"],
        "term_premium_tier": synthesis["term_premium_tier"],
        "curve_effective_overlay_bp": synthesis["curve_effective_overlay_bp"],
        "point_calibration_delta_ratewall_ratio": synthesis[
            "point_calibration_delta_ratewall_ratio"
        ],
        "denominator_bound_theta_values": synthesis[
            "denominator_bound_theta_values"
        ],
        "denominator_bound_min_delta_denominator_bil": synthesis[
            "denominator_bound_min_delta_denominator_bil"
        ],
        "denominator_bound_max_delta_denominator_bil": synthesis[
            "denominator_bound_max_delta_denominator_bil"
        ],
        "denominator_bound_min_moving_delta_ratewall_ratio_vs_baseline": synthesis[
            "denominator_bound_min_moving_delta_ratewall_ratio_vs_baseline"
        ],
        "denominator_bound_max_moving_delta_ratewall_ratio_vs_baseline": synthesis[
            "denominator_bound_max_moving_delta_ratewall_ratio_vs_baseline"
        ],
        "selected_denominator_response_profile_id": synthesis[
            "selected_denominator_response_profile_id"
        ],
        "selected_denominator_response_coefficient": synthesis[
            "selected_denominator_response_coefficient"
        ],
        "selected_moving_denominator_bil": synthesis[
            "selected_moving_denominator_bil"
        ],
        "selected_moving_delta_ratewall_ratio_vs_baseline": synthesis[
            "selected_moving_delta_ratewall_ratio_vs_baseline"
        ],
        "selected_denominator_response_status": synthesis[
            "selected_denominator_response_status"
        ],
        "empirical_denominator_coefficient_status": (
            "admitted_structural_curve_denominator_response_coefficient"
        ),
        "literature_calibrated_coefficient_status": (
            "admitted_frbus_structural_curve_to_denominator_coefficient"
        ),
        "econometric_estimate_status": (
            "no_econometrically_admitted_curve_to_denominator_coefficient"
        ),
        "admitted_curve_response_coefficient": synthesis[
            "selected_denominator_response_coefficient"
        ],
        "admitted_curve_response_coefficient_unit": (
            "fraction_of_frozen_denominator_per_100bp_year"
        ),
        "admitted_response_horizon": "annual_h4_one_year",
        "current_denominator_profile_status": (
            "frbus_structural_profile_selected_with_assumption_bounds_retained"
        ),
        "current_denominator_profile_used_for_scenarios": (
            synthesis["selected_denominator_response_profile_id"]
        ),
        "linked_assumption_bound_row_ids": ";".join(
            row["tdcsim_cbo_curve_sensitive_denominator_assumption_bound_row_id"]
            for row in sorted(bounds, key=_curve_assumption_bound_sort_key)
        ),
        "candidate_econometric_surface_status": (
            "not_available_in_current_tdcsim_cbo_suite"
        ),
        "candidate_econometric_surface_blocker": (
            "existing local FSPDP sensitivity rows are noncanonical and explicitly "
            "not admitted as nominal GDP or denominator estimates"
        ),
        "denominator_model_decision": (
            "use_frbus_structural_moving_D_for_rate_changing_model_scenarios"
        ),
        "next_model_requirement": (
            "optional_same_axis_local_econometric_cross_check_only_if_stronger"
        ),
        "allowed_use": "assumption_mode_curve_denominator_empirical_status",
        "blocked_use": (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "path_ratio_denominator_replacement;release_headline_claim;"
            "empirical_denominator_response_claim"
        ),
        "claim_boundary": (
            "selected_structural_profile_moves_D_for_rate_changing_scenarios;"
            "not_local_econometric_estimate;assumption_bounds_retained_for_sensitivity"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
    }


def _shared_bound_field(bounds: list[dict[str, str]], field: str) -> str:
    values = {row[field] for row in bounds}
    if len(values) != 1:
        raise TdcsimCboContractError(
            f"denominator-bound rows disagree on field {field}: {values}"
        )
    return next(iter(values))


def _model_scenario_materiality_classification_row(
    row: Mapping[str, str],
    *,
    rank: str,
) -> dict[str, str]:
    point_delta = _decimal(row["point_calibration_delta_ratewall_ratio"])
    abs_delta = abs(point_delta)
    materiality = _materiality_tier_vs_primary_deficit(
        _decimal(row["abs_delta_vs_primary_deficit_up_1pct"])
    )
    beta_class = _beta_chi_robustness_class(row)
    denominator_class = _denominator_bound_sensitivity_class(row)
    relevance = _model_relevance_class(row, materiality, beta_class)
    return {
        "tdcsim_cbo_model_scenario_materiality_classification_row_id": (
            "tdcsim_cbo_model_scenario_materiality_classification::"
            f"{row['fiscal_year']}::{row['scenario_id']}"
        ),
        "source_model_scenario_interpretation_synthesis_row_id": row[
            "tdcsim_cbo_model_scenario_interpretation_synthesis_row_id"
        ],
        "fiscal_year": row["fiscal_year"],
        "materiality_rank_abs_delta": rank,
        "scenario_family": _scenario_family(row),
        "summary_role": row["summary_role"],
        "comparison_group": row["comparison_group"],
        "scenario_id": row["scenario_id"],
        "baseline_scenario_id": row["baseline_scenario_id"],
        "point_calibration_delta_ratewall_ratio": row[
            "point_calibration_delta_ratewall_ratio"
        ],
        "point_calibration_abs_delta_ratewall_ratio": _fmt(abs_delta),
        "point_calibration_sign": row["point_calibration_sign"],
        "primary_deficit_up_1pct_delta_ratewall_ratio": row[
            "primary_deficit_up_1pct_delta_ratewall_ratio"
        ],
        "abs_delta_vs_primary_deficit_up_1pct": row[
            "abs_delta_vs_primary_deficit_up_1pct"
        ],
        "materiality_tier_vs_primary_deficit_up_1pct": materiality,
        "beta_chi_sign_stability_status": row["beta_chi_sign_stability_status"],
        "beta_chi_robustness_class": beta_class,
        "denominator_bound_sign_stability_status": row[
            "denominator_bound_sign_stability_status"
        ],
        "denominator_bound_sensitivity_class": denominator_class,
        "curve_effective_overlay_bp": row["curve_effective_overlay_bp"],
        "denominator_recompute_readiness": _denominator_recompute_readiness(row),
        "dominant_delta_support_component": row["dominant_delta_support_component"],
        "dominant_delta_support_component_bil": row[
            "dominant_delta_support_component_bil"
        ],
        "support_mechanism_profile": row["support_mechanism_profile"],
        "component_delta_sum_status": row["component_delta_sum_status"],
        "model_interpretation": row["model_interpretation"],
        "final_interpretation": row["final_interpretation"],
        "model_relevance_class": relevance,
        "recommended_use": _recommended_materiality_use(row, relevance),
        "allowed_use": "assumption_mode_materiality_and_robustness_ranking",
        "blocked_use": (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "one_factor_coefficient_claim;statistical_significance_claim"
        ),
        "claim_boundary": (
            "classification_of_existing_scenario_surface_only;"
            "not_new_economic_identification;not_denominator_admission"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
    }


def _denominator_bound_sign_stability_status(
    point_sign: str,
    bound_signs: list[str],
) -> str:
    nonzero = [sign for sign in bound_signs if sign != "zero"]
    if not nonzero:
        return "zero_or_baseline_only"
    if len(set(nonzero)) > 1:
        return "denominator_bounds_mixed_sign"
    if point_sign == "zero":
        return "denominator_bounds_create_nonzero_sign"
    if nonzero[0] == point_sign:
        return "denominator_bounds_preserve_point_sign"
    return "denominator_bounds_flip_point_sign"


def _primary_deficit_scale_bucket(scale: Decimal) -> str:
    if not scale:
        return "zero_vs_primary_deficit_up_1pct"
    if scale < Decimal("0.25"):
        return "less_than_quarter_primary_deficit_up_1pct"
    if scale < Decimal("0.75"):
        return "quarter_to_three_quarters_primary_deficit_up_1pct"
    if scale < Decimal("1.25"):
        return "near_primary_deficit_up_1pct"
    return "larger_than_primary_deficit_up_1pct"


def _materiality_tier_vs_primary_deficit(scale: Decimal) -> str:
    if not scale:
        return "baseline_or_zero_effect"
    if scale < Decimal("0.25"):
        return "small_less_than_quarter_primary_deficit_up_1pct"
    if scale < Decimal("0.75"):
        return "moderate_quarter_to_three_quarters_primary_deficit_up_1pct"
    if scale < Decimal("1.25"):
        return "benchmark_like_near_primary_deficit_up_1pct"
    return "large_above_primary_deficit_up_1pct"


def _scenario_family(row: Mapping[str, str]) -> str:
    role = row["summary_role"]
    if role == "baseline_anchor":
        return "baseline"
    if role == "combined_narrative_scenario":
        return "composite_assumption"
    if role in {
        "issuance_only_control",
        "coupled_bound_empirical_scenario",
        "coupled_central_empirical_scenario",
    }:
        return "issuance_rate_assumption"
    return "single_channel_assumption"


def _beta_chi_robustness_class(row: Mapping[str, str]) -> str:
    status = row["beta_chi_sign_stability_status"]
    if row["summary_role"] == "baseline_anchor":
        return "baseline_no_delta"
    if status.startswith("stable_"):
        return "sign_stable_over_beta_chi_grid"
    if status == "mixed_sign":
        return "point_calibration_only_beta_chi_mixed_sign"
    return "beta_chi_robustness_unclassified"


def _denominator_bound_sensitivity_class(row: Mapping[str, str]) -> str:
    status = row["denominator_bound_sign_stability_status"]
    if status == "zero_or_baseline_only":
        return "no_denominator_bound_sign_effect"
    if status == "denominator_bounds_preserve_point_sign":
        return "denominator_bounds_preserve_point_sign"
    if status == "denominator_bounds_mixed_sign":
        return "denominator_bounds_mixed_sign"
    if status == "denominator_bounds_flip_point_sign":
        return "denominator_bounds_flip_point_sign"
    return "denominator_bound_sensitivity_unclassified"


def _denominator_recompute_readiness(row: Mapping[str, str]) -> str:
    if _decimal(row["curve_effective_overlay_bp"]) == 0:
        return "no_curve_overlay_needed_for_denominator_recompute"
    if row.get("selected_denominator_response_status") == (
        "pass_moving_D_computed_from_admitted_profile"
    ):
        return "curve_metadata_present_frbus_coefficient_admitted"
    return "curve_metadata_present_coefficient_not_admitted"


def _model_relevance_class(
    row: Mapping[str, str],
    materiality: str,
    beta_class: str,
) -> str:
    if row["summary_role"] == "baseline_anchor":
        return "baseline_anchor"
    if beta_class == "sign_stable_over_beta_chi_grid":
        return f"{materiality};sign_stable"
    return f"{materiality};point_calibration_only"


def _recommended_materiality_use(row: Mapping[str, str], relevance: str) -> str:
    if row["summary_role"] == "baseline_anchor":
        return "baseline_reference_only"
    if "point_calibration_only" in relevance:
        return "scenario_mode_interpretation_only_not_canonical"
    return "scenario_mode_sign_stable_comparator_not_canonical"


def _final_model_interpretation(
    summary: Mapping[str, str],
    beta_status: str,
    denominator_status: str,
) -> str:
    if summary["summary_role"] == "baseline_anchor":
        return "baseline_anchor_no_delta"
    if beta_status == "mixed_sign":
        return "point_calibration_not_beta_chi_sign_robust"
    if denominator_status == "denominator_bounds_mixed_sign":
        return "denominator_bounds_change_sign_under_assumptions"
    if denominator_status == "denominator_bounds_flip_point_sign":
        return "denominator_bounds_flip_point_sign"
    if beta_status.startswith("stable_"):
        return "sign_stable_over_beta_chi_and_denominator_bounds"
    return "bounded_noncanonical_interpretation_only"


def _current_beta_times_chi() -> Decimal:
    return DEFAULT_TDC_BETA * DEFAULT_TDC_DEPOSIT_CURRENT_DEMAND_SHARE


def _required_effect_row(
    effect_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    row: Mapping[str, str],
) -> Mapping[str, str]:
    key = (row["scenario_id"], row["fiscal_year"])
    try:
        return effect_by_key[key]
    except KeyError as exc:
        raise TdcsimCboContractError(
            "existing TDCSim CBO exports are insufficient for beta x chi "
            f"robustness: missing scenario_effect row {key}"
        ) from exc


def _primary_deficit_up_delta_by_year(
    effect_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    beta_chi: Decimal,
) -> dict[str, Decimal]:
    years = sorted({fiscal_year for _, fiscal_year in effect_by_key})
    out: dict[str, Decimal] = {}
    for fiscal_year in years:
        primary = effect_by_key.get(("tdcsim_primary_deficit_up_1pct_v1", fiscal_year))
        baseline = effect_by_key.get(("cbo_baseline_noop_v1", fiscal_year))
        if primary is None or baseline is None:
            out[fiscal_year] = Decimal("0")
            continue
        out[fiscal_year] = _recomputed_support(
            primary,
            baseline,
            beta_chi,
        )["delta_ratewall_ratio"]
    return out


def _recomputed_support(
    effect: Mapping[str, str],
    baseline: Mapping[str, str],
    beta_chi: Decimal,
) -> dict[str, Decimal]:
    required_fields = (
        "tdc_change_ex_overlap_bil",
        "direct_treasury_current_demand_support_bil",
        "bank_treasury_current_demand_support_bil",
        "frozen_denominator_bil",
    )
    for field in required_fields:
        if field not in effect:
            raise TdcsimCboContractError(
                "existing TDCSim CBO exports are insufficient for beta x chi "
                f"robustness: missing field {field}"
            )
    tdc = _decimal(effect["tdc_change_ex_overlap_bil"]) * beta_chi
    direct = _decimal(effect["direct_treasury_current_demand_support_bil"])
    bank = _decimal(effect["bank_treasury_current_demand_support_bil"])
    total = tdc + direct + bank
    baseline_tdc = _decimal(baseline["tdc_change_ex_overlap_bil"]) * beta_chi
    baseline_direct = _decimal(
        baseline["direct_treasury_current_demand_support_bil"]
    )
    baseline_bank = _decimal(baseline["bank_treasury_current_demand_support_bil"])
    baseline_total = baseline_tdc + baseline_direct + baseline_bank
    denominator = _decimal(effect["frozen_denominator_bil"])
    if denominator != _decimal(baseline["frozen_denominator_bil"]):
        raise TdcsimCboContractError(
            "mixed frozen denominators within one fiscal-year robustness cell"
        )
    return {
        "tdc": tdc,
        "baseline_tdc": baseline_tdc,
        "delta_tdc": tdc - baseline_tdc,
        "direct": direct,
        "baseline_direct": baseline_direct,
        "delta_direct": direct - baseline_direct,
        "bank": bank,
        "baseline_bank": baseline_bank,
        "delta_bank": bank - baseline_bank,
        "total": total,
        "baseline_total": baseline_total,
        "delta_total": total - baseline_total,
        "ratewall_ratio": _safe_ratio(total, denominator),
        "delta_ratewall_ratio": _safe_ratio(total - baseline_total, denominator),
        "denominator": denominator,
    }


def _beta_chi_robustness_row(
    summary: Mapping[str, str],
    *,
    effect: Mapping[str, str],
    baseline: Mapping[str, str],
    recomputed: Mapping[str, Decimal],
    paired_recomputed: Mapping[str, Decimal] | None,
    beta_label: str,
    beta: Decimal,
    beta_source_status: str,
    chi_label: str,
    chi: Decimal,
    primary_deficit_up_delta: Decimal,
    current_point_primary_deficit_up_delta: Decimal,
) -> dict[str, str]:
    beta_chi = beta * chi
    paired_id = summary["paired_issuance_only_scenario_id"]
    has_distinct_pair = paired_id and paired_id != summary["scenario_id"]
    paired_delta = (
        paired_recomputed["delta_ratewall_ratio"]
        if has_distinct_pair and paired_recomputed is not None
        else Decimal("0")
    )
    overlay_delta = (
        recomputed["delta_ratewall_ratio"] - paired_delta
        if has_distinct_pair
        else Decimal("0")
    )
    net_remaining = (
        _safe_ratio(recomputed["delta_ratewall_ratio"], paired_delta)
        if has_distinct_pair
        else Decimal("1")
    )
    dominant_component, dominant_value = _dominant_component_from_values(
        recomputed["delta_tdc"],
        recomputed["delta_direct"],
        recomputed["delta_bank"],
    )
    current_sign = _sign_label(_decimal(summary["delta_ratewall_ratio_vs_baseline"]))
    recomputed_sign = _sign_label(recomputed["delta_ratewall_ratio"])
    return {
        "tdcsim_cbo_model_scenario_beta_chi_robustness_row_id": (
            "tdcsim_cbo_model_scenario_beta_chi_robustness::"
            f"{summary['fiscal_year']}::{summary['scenario_id']}::"
            f"{beta_label}::{chi_label}"
        ),
        "source_model_scenario_summary_row_id": summary[
            "tdcsim_cbo_model_scenario_summary_row_id"
        ],
        "source_scenario_effect_row_id": effect[
            "tdcsim_cbo_scenario_effect_row_id"
        ],
        "fiscal_year": summary["fiscal_year"],
        "summary_role": summary["summary_role"],
        "comparison_group": summary["comparison_group"],
        "scenario_id": summary["scenario_id"],
        "baseline_scenario_id": summary["baseline_scenario_id"],
        "paired_issuance_only_scenario_id": paired_id,
        "term_premium_tier": summary["term_premium_tier"],
        "ten_year_nominal_rate_shock_bp": summary[
            "ten_year_nominal_rate_shock_bp"
        ],
        "model_interpretation": summary["model_interpretation"],
        "tdc_materialization_beta_scenario": beta_label,
        "tdc_materialization_beta": _fmt(beta),
        "deposit_current_demand_share_profile": chi_label,
        "deposit_current_demand_share": _fmt(chi),
        "derived_beta_times_chi": _fmt(beta_chi),
        "profile_is_current_point_calibration": str(
            beta == DEFAULT_TDC_BETA
            and chi == DEFAULT_TDC_DEPOSIT_CURRENT_DEMAND_SHARE
        ).lower(),
        "tdc_materialization_beta_source_status": beta_source_status,
        "deposit_current_demand_share_source_status": (
            "existing_assumption_mode_grid"
        ),
        "tdc_change_ex_overlap_bil": effect["tdc_change_ex_overlap_bil"],
        "baseline_tdc_change_ex_overlap_bil": baseline[
            "tdc_change_ex_overlap_bil"
        ],
        "delta_tdc_change_ex_overlap_bil": effect[
            "delta_tdc_change_ex_overlap_bil"
        ],
        "direct_treasury_current_demand_support_bil_fixed": effect[
            "direct_treasury_current_demand_support_bil"
        ],
        "baseline_direct_treasury_current_demand_support_bil_fixed": baseline[
            "direct_treasury_current_demand_support_bil"
        ],
        "delta_direct_treasury_current_demand_support_bil_fixed": _fmt(
            recomputed["delta_direct"]
        ),
        "bank_treasury_current_demand_support_bil_fixed": effect[
            "bank_treasury_current_demand_support_bil"
        ],
        "baseline_bank_treasury_current_demand_support_bil_fixed": baseline[
            "bank_treasury_current_demand_support_bil"
        ],
        "delta_bank_treasury_current_demand_support_bil_fixed": _fmt(
            recomputed["delta_bank"]
        ),
        "direct_treasury_current_demand_share_fixed": _fmt(
            DEFAULT_DIRECT_TREASURY_CURRENT_DEMAND_SHARE
        ),
        "bank_treasury_current_demand_share_fixed": _fmt(
            DEFAULT_BANK_TREASURY_CURRENT_DEMAND_SHARE
        ),
        "frozen_denominator_bil": _fmt(recomputed["denominator"]),
        "denominator_scope": effect["denominator_scope"],
        "tdc_current_demand_support_bil_recomputed": _fmt(recomputed["tdc"]),
        "delta_tdc_current_demand_support_bil_recomputed": _fmt(
            recomputed["delta_tdc"]
        ),
        "total_current_demand_support_bil_recomputed": _fmt(
            recomputed["total"]
        ),
        "delta_total_current_demand_support_bil_recomputed": _fmt(
            recomputed["delta_total"]
        ),
        "level_ratewall_ratio_recomputed": _fmt(recomputed["ratewall_ratio"]),
        "delta_ratewall_ratio_vs_baseline_recomputed": _fmt(
            recomputed["delta_ratewall_ratio"]
        ),
        "wall_hit_under_assumptions": str(
            recomputed["ratewall_ratio"] >= Decimal("1")
        ).lower(),
        "rate_overlay_delta_ratewall_ratio_recomputed": _fmt(overlay_delta),
        "offset_fraction_of_abs_issuance_effect_recomputed": _fmt(
            _safe_abs_ratio(overlay_delta, paired_delta)
        ),
        "net_effect_fraction_remaining_recomputed": _fmt(net_remaining),
        "primary_deficit_up_1pct_delta_ratewall_ratio_recomputed": _fmt(
            primary_deficit_up_delta
        ),
        "abs_delta_vs_primary_deficit_up_1pct_recomputed": _fmt(
            _safe_abs_ratio(
                recomputed["delta_ratewall_ratio"],
                primary_deficit_up_delta,
            )
        ),
        "abs_delta_vs_current_point_primary_deficit_up_1pct": _fmt(
            _safe_abs_ratio(
                recomputed["delta_ratewall_ratio"],
                current_point_primary_deficit_up_delta,
            )
        ),
        "delta_sign_vs_baseline_recomputed": recomputed_sign,
        "same_sign_as_current_point_calibration": str(
            recomputed_sign == current_sign
        ).lower(),
        "dominant_delta_support_component_recomputed": dominant_component,
        "dominant_delta_support_component_bil_recomputed": _fmt(dominant_value),
        "allowed_use": "assumption_mode_ratewall_only_beta_chi_robustness",
        "blocked_use": (
            "causal_market_yield_estimate;canonical_headline_promotion;"
            "denominator_change;evidence_mode_claim;posterior_beta_claim;"
            "statistical_significance_claim;runtime_default;prior_narrowing;"
            "coefficient_robust_claim_outside_reported_grid"
        ),
        "claim_boundary": (
            "ratewall_only_assumption_mode_beta_chi_robustness;"
            "frozen_denominator;existing_tdcsim_cashflows_only"
        ),
        "canonical_ratio_entry": "false",
        "denominator_prior_update_allowed": "false",
        "evidence_mode_enabled": "false",
        "empirical_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
        "tax_output_enabled": "false",
        "mpc_output_enabled": "false",
        "holder_allocation_enabled": "false",
        "causal_financialization_claim_enabled": "false",
    }


def _beta_chi_robustness_sort_key(row: Mapping[str, str]) -> tuple[int, int, int, int, str]:
    beta_order = {
        label: index
        for index, (label, _beta, _source_status) in enumerate(
            BETA_CHI_ROBUSTNESS_BETA_PROFILES
        )
    }
    chi_order = {"conservative": 0, "base": 1, "demand_active": 2}
    return (
        int(row["fiscal_year"]),
        _model_summary_sort_key(row)[1],
        beta_order.get(row["tdc_materialization_beta_scenario"], 99),
        chi_order.get(row["deposit_current_demand_share_profile"], 99),
        row["scenario_id"],
    )


def _beta_chi_sign_stability_row(
    rows: list[dict[str, str]],
    effect: Mapping[str, str],
) -> dict[str, str]:
    point = next(row for row in rows if row["profile_is_current_point_calibration"] == "true")
    deltas = [_decimal(row["delta_ratewall_ratio_vs_baseline_recomputed"]) for row in rows]
    abs_deltas = [abs(delta) for delta in deltas]
    levels = [_decimal(row["level_ratewall_ratio_recomputed"]) for row in rows]
    same_profile_scales = [
        _decimal(row["abs_delta_vs_primary_deficit_up_1pct_recomputed"])
        for row in rows
    ]
    current_scales = [
        _decimal(row["abs_delta_vs_current_point_primary_deficit_up_1pct"])
        for row in rows
    ]
    signs = sorted({_sign_label(delta) for delta in deltas})
    point_sign = _sign_label(
        _decimal(point["delta_ratewall_ratio_vs_baseline_recomputed"])
    )
    same_sign_count = sum(1 for delta in deltas if _sign_label(delta) == point_sign)
    zero_crossing, zero_status = _zero_crossing_beta_chi(effect)
    components = {
        row["dominant_delta_support_component_recomputed"] for row in rows
    }
    return {
        "tdcsim_cbo_beta_chi_sign_stability_row_id": (
            "tdcsim_cbo_beta_chi_sign_stability::"
            f"{point['fiscal_year']}::{point['scenario_id']}"
        ),
        "fiscal_year": point["fiscal_year"],
        "scenario_id": point["scenario_id"],
        "summary_role": point["summary_role"],
        "comparison_group": point["comparison_group"],
        "point_calibration_delta_ratewall_ratio": point[
            "delta_ratewall_ratio_vs_baseline_recomputed"
        ],
        "min_delta_ratewall_ratio_over_beta_chi_grid": _fmt(min(deltas)),
        "max_delta_ratewall_ratio_over_beta_chi_grid": _fmt(max(deltas)),
        "min_abs_delta_ratewall_ratio_over_beta_chi_grid": _fmt(min(abs_deltas)),
        "max_abs_delta_ratewall_ratio_over_beta_chi_grid": _fmt(max(abs_deltas)),
        "point_calibration_sign": point_sign,
        "signs_observed_over_grid": ";".join(signs),
        "same_sign_cell_count": str(same_sign_count),
        "grid_cell_count": str(len(rows)),
        "sign_stability_status": _sign_stability_status(signs),
        "zero_crossing_beta_times_chi": _fmt(zero_crossing),
        "zero_crossing_status": zero_status,
        "min_abs_delta_vs_same_profile_primary_deficit_up_1pct": _fmt(
            min(same_profile_scales)
        ),
        "max_abs_delta_vs_same_profile_primary_deficit_up_1pct": _fmt(
            max(same_profile_scales)
        ),
        "min_abs_delta_vs_current_point_primary_deficit_up_1pct": _fmt(
            min(current_scales)
        ),
        "max_abs_delta_vs_current_point_primary_deficit_up_1pct": _fmt(
            max(current_scales)
        ),
        "dominant_component_stability_status": (
            "stable_" + next(iter(components))
            if len(components) == 1
            else "mixed_dominant_component"
        ),
        "wall_hit_any_grid_cell": str(any(level >= Decimal("1") for level in levels)).lower(),
        "min_level_ratewall_ratio_over_grid": _fmt(min(levels)),
        "max_level_ratewall_ratio_over_grid": _fmt(max(levels)),
        "allowed_use": "assumption_mode_beta_chi_sign_stability_summary",
        "blocked_use": (
            "causal_market_yield_estimate;canonical_headline_promotion;"
            "denominator_change;evidence_mode_claim;posterior_beta_claim;"
            "statistical_significance_claim;runtime_default;prior_narrowing"
        ),
        "claim_boundary": (
            "sign_and_scale_stability_over_existing_beta_chi_grid_only;"
            "not_statistical_significance"
        ),
        "canonical_ratio_entry": "false",
    }


def _zero_crossing_beta_chi(effect: Mapping[str, str]) -> tuple[Decimal, str]:
    slope = _decimal(effect["delta_tdc_change_ex_overlap_bil"])
    intercept = (
        _decimal(effect["delta_direct_treasury_current_demand_support_bil"])
        + _decimal(effect["delta_bank_treasury_current_demand_support_bil"])
    )
    if not slope:
        if not intercept:
            return Decimal("0"), "identically_zero"
        return Decimal("0"), "no_tdc_slope"
    crossing = -intercept / slope
    grid = [
        beta * chi
        for _, beta, _source_status in BETA_CHI_ROBUSTNESS_BETA_PROFILES
        for _, chi in BETA_CHI_ROBUSTNESS_CHI_PROFILES
    ]
    if crossing < 0:
        return crossing, "outside_positive_grid"
    if min(grid) <= crossing <= max(grid):
        return crossing, "inside_grid"
    return crossing, "outside_grid"


def _dominant_component_from_values(
    tdc: Decimal,
    direct: Decimal,
    bank: Decimal,
) -> tuple[str, Decimal]:
    components = {
        "tdc_current_demand_support": tdc,
        "direct_treasury_current_demand_support": direct,
        "bank_treasury_current_demand_support": bank,
    }
    return max(components.items(), key=lambda item: (abs(item[1]), item[0]))


def _sign_label(value: Decimal) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def _sign_stability_status(signs: list[str]) -> str:
    if signs == ["zero"]:
        return "zero_baseline"
    nonzero = [sign for sign in signs if sign != "zero"]
    if len(set(nonzero)) > 1:
        return "mixed_sign"
    if nonzero == ["positive"]:
        return "stable_positive"
    if nonzero == ["negative"]:
        return "stable_negative"
    return "mixed_with_zero"


def _decimal(value: str | Decimal | int | float | Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _fmt(value: Decimal) -> str:
    if not value:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _fmt_display_28(value: str | Decimal | int | float | Any) -> str:
    decimal_value = _decimal(value)
    if not decimal_value:
        return "0"
    with localcontext() as ctx:
        ctx.prec = max(60, len(decimal_value.as_tuple().digits) + 30)
        return _fmt(decimal_value.quantize(Decimal("1e-28")))


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if not denominator:
        return Decimal("0")
    return numerator / denominator


def _safe_abs_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if not denominator:
        return Decimal("0")
    return abs(numerator) / abs(denominator)


def _bool(value: str | bool | int) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no", ""}:
        return False
    raise TdcsimCboContractError(f"invalid boolean value: {value}")


def _require_close(left: Decimal, right: Decimal, tolerance: Decimal) -> None:
    if abs(left - right) > tolerance:
        raise TdcsimCboContractError(
            f"TDC identity failed: {left} differs from {right}"
        )
