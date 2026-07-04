"""Marginal RateWall object contract and channel-role ledger."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from ratewall.databook.table_io import write_rows

DEFAULT_OBJECT_CONFIG_PATH = Path("configs/ratewall_marginal_object.yml")
DEFAULT_CHANNEL_REGISTRY_PATH = Path("configs/ratewall_marginal_channel_registry.yml")
DEFAULT_TRUE_V1_CHANNEL_INVENTORY_PATH = Path(
    "configs/ratewall_marginal_channel_inventory.yml"
)
DEFAULT_CURRENT_BRIDGE_PATH = Path(
    "var/preliminary_scenario_results/current_object_bridge/"
    "ratewall_current_object_bridge.csv"
)
DEFAULT_FORECAST_SURFACE_PATH = Path(
    "var/preliminary_scenario_results/forecast_10y/"
    "ratewall_forecast_central_scenario_surface.csv"
)
DEFAULT_HISTORICAL_ROOT_PATH = Path(
    "var/preliminary_scenario_results/historical_provisional_estimate/"
    "ratewall_historical_root_public_interest_rw_panel.csv"
)
DEFAULT_HISTORICAL_DENOMINATOR_PATH = Path(
    "var/preliminary_scenario_results/historical_provisional_estimate/"
    "ratewall_historical_denominator_convention_review.csv"
)

MARGINAL_OBJECT_CONTRACT_FIELDS = [
    "marginal_object_contract_row_id",
    "marginal_object_id",
    "period_object",
    "rw_m_formula",
    "shock_path_id",
    "shock_bps_year",
    "same_state_pair_required",
    "selected_rw_m",
    "selected_n_basis",
    "selected_d_basis",
    "tdc_inclusion_rule",
    "current_legacy_benchmark_status",
    "forecast_legacy_ratio_status",
    "historical_classifier_status",
    "selection_gate_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_CHANNEL_STATUS_FIELDS = [
    "marginal_channel_status_row_id",
    "channel_id",
    "channel_family",
    "period_scope",
    "final_role",
    "numerator_formula",
    "marginal_delta_required",
    "same_state_pair_required",
    "source_status",
    "viability_status",
    "promotion_status",
    "fail_closed_label",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_ROW_ROLE_RESET_FIELDS = [
    "marginal_row_role_reset_row_id",
    "source_artifact",
    "source_row_id",
    "period_object",
    "period",
    "scenario_id",
    "old_selected_or_exposure_fields",
    "old_role",
    "marginal_role",
    "selected_final_rw_m_allowed",
    "fail_closed_label",
    "required_rebuild",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

COMPLETE_MARGINAL_CHANNEL_INVENTORY_FIELDS = [
    "prior_channel_id",
    "prior_source_surface",
    "marginal_status",
    "selected_role",
    "theory_reason",
    "required_formula",
    "source_or_assumption_route",
    "overlap_policy",
    "demand_conversion_policy",
    "output_table",
    "gate_id",
    "test_id",
    "promotion_rule",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_ROLES = {
    "selected_marginal_n",
    "selected_marginal_d",
    "selected_marginal_block_input",
    "candidate_marginal_replacement",
    "diagnostic_exposure_only",
    "sensitivity_only",
    "denominator_only",
    "blocked_source_or_method",
    "not_applicable_adjustment",
    "cut_nonviable_form",
}

INVENTORY_STATUSES = {
    "selected_central_after_gate",
    "included_inside_public_interest_net_block",
    "sensitivity_only",
    "sidecar_only",
    "replacement_only",
    "diagnostic_only",
    "blocked_non_marginal_form",
}

FAIL_CLOSED_LABELS = {
    "fail_closed_non_marginal_selected_n",
    "fail_closed_non_marginal_selected_d",
    "fail_closed_old_exposure_ratio_promoted",
    "fail_closed_previous_current_benchmark_selected_as_rw_m",
    "fail_closed_forecast_v1_ratio_selected_as_rw_m",
    "fail_closed_historical_classifier_without_marginal_n",
    "fail_closed_block_input_used_as_standalone_n",
    "fail_closed_denominator_drag_booked_as_n",
}

COMPLETE_CHANNEL_REQUIREMENTS = [
    {
        "prior_channel_id": "public_interest_net_block",
        "prior_source_surface": "marginal_public_interest;forecast_10y;core_support_parity;historical_provisional_estimate",
        "marginal_status": "selected_central_after_gate",
        "selected_role": "selected_marginal_n_net_block",
        "theory_reason": "public interest receipts and absorbers are direct marginal support channels only after netting",
        "required_formula": "delta_public_interest_net_block_bil",
        "source_or_assumption_route": "component_same_state_plus_100bp_year_current_forecast_and_optional_historical",
        "overlap_policy": "single_net_block_prevents_component_double_counting",
        "demand_conversion_policy": "component_specific_tax_fiscal_tga_leakage_then_net_current_demand",
        "output_table": "ratewall_marginal_public_interest_net_block.csv",
        "gate_id": "phase2_public_interest_component_net_gate",
        "test_id": "test_complete_inventory_requires_full_public_interest_components",
        "promotion_rule": "selected_when_all_required_components_have_source_or_assumption_rows_and_net_identity_passes",
        "blocked_use": "legacy_public_interest_level;standalone_component_addition",
        "claim_boundary": "public_interest_selected_only_as_same_state_marginal_net_block",
    },
    {
        "prior_channel_id": "public_interest_direct_treasury_interest",
        "prior_source_surface": "forecast_10y;historical_provisional_estimate;core_support_parity",
        "marginal_status": "included_inside_public_interest_net_block",
        "selected_role": "public_interest_block_input",
        "theory_reason": "higher Treasury interest paid to domestic nonbanks can support demand but only inside the net public-interest block",
        "required_formula": "delta_direct_treasury_interest_to_domestic_nonbanks_bil",
        "source_or_assumption_route": "debt_service_duration_and_holder_split_component",
        "overlap_policy": "net_against_foreign_leakage_tax_fiscal_tga_and_tdcsim_overlap",
        "demand_conversion_policy": "recipient_current_demand_share_inside_public_interest_block",
        "output_table": "ratewall_marginal_public_interest_components.csv",
        "gate_id": "public_interest_direct_treasury_component_gate",
        "test_id": "test_public_interest_components_do_not_enter_standalone_selected_n",
        "promotion_rule": "component_enters_only_when_net_block_identity_passes",
        "blocked_use": "standalone_selected_marginal_n;legacy_interest_support_bil",
        "claim_boundary": "direct_treasury_interest_is_block_input_not_standalone_selected_channel",
    },
    {
        "prior_channel_id": "public_interest_bank_treasury_interest",
        "prior_source_surface": "forecast_10y;core_support_parity",
        "marginal_status": "included_inside_public_interest_net_block",
        "selected_role": "public_interest_block_input",
        "theory_reason": "bank Treasury income can affect support through retained or passed-through bank income but must be netted",
        "required_formula": "delta_bank_treasury_interest_after_pass_through_bil",
        "source_or_assumption_route": "holder_split_and_bank_pass_through_component",
        "overlap_policy": "remove_overlap_with_tdcsim_deposit_and_safe_yield_routes",
        "demand_conversion_policy": "bank_income_pass_through_current_demand_policy",
        "output_table": "ratewall_marginal_public_interest_components.csv",
        "gate_id": "public_interest_bank_treasury_component_gate",
        "test_id": "test_public_interest_components_do_not_enter_standalone_selected_n",
        "promotion_rule": "component_enters_only_when_net_block_identity_passes",
        "blocked_use": "standalone_bank_interest_support;tdcsim_double_count",
        "claim_boundary": "bank_treasury_interest_is_public_interest_block_input",
    },
    {
        "prior_channel_id": "public_interest_iorb_reserves",
        "prior_source_surface": "marginal_public_interest;forecast_10y;historical_provisional_estimate",
        "marginal_status": "included_inside_public_interest_net_block",
        "selected_role": "public_interest_block_input",
        "theory_reason": "reserve remuneration is a public-sector interest flow that can alter support after pass-through and absorbers",
        "required_formula": "delta_iorb_interest_bil",
        "source_or_assumption_route": "reserve_stock_times_plus_100bp_year_rate_delta_with_pass_through_controls",
        "overlap_policy": "remove_overlap_with_remittance_and_bank_income_rows",
        "demand_conversion_policy": "bank_pass_through_or_retention_policy_inside_net_block",
        "output_table": "ratewall_marginal_public_interest_components.csv",
        "gate_id": "public_interest_iorb_component_gate",
        "test_id": "test_public_interest_components_do_not_enter_standalone_selected_n",
        "promotion_rule": "component_enters_only_when_net_block_identity_passes",
        "blocked_use": "iorb_level_as_standalone_selected_n",
        "claim_boundary": "iorb_is_public_interest_block_input",
    },
    {
        "prior_channel_id": "public_interest_on_rrp",
        "prior_source_surface": "marginal_public_interest;forecast_10y;historical_provisional_estimate",
        "marginal_status": "included_inside_public_interest_net_block",
        "selected_role": "public_interest_block_input",
        "theory_reason": "ON RRP interest is a public-sector interest flow to eligible counterparties and must be netted",
        "required_formula": "delta_on_rrp_interest_bil",
        "source_or_assumption_route": "on_rrp_stock_times_plus_100bp_year_rate_delta_with_counterparty_controls",
        "overlap_policy": "remove_overlap_with_mmf_safe_yield_and_remittance_rows",
        "demand_conversion_policy": "counterparty_current_demand_policy_inside_net_block",
        "output_table": "ratewall_marginal_public_interest_components.csv",
        "gate_id": "public_interest_on_rrp_component_gate",
        "test_id": "test_public_interest_components_do_not_enter_standalone_selected_n",
        "promotion_rule": "component_enters_only_when_net_block_identity_passes",
        "blocked_use": "on_rrp_level_as_standalone_selected_n",
        "claim_boundary": "on_rrp_is_public_interest_block_input",
    },
    {
        "prior_channel_id": "public_interest_remittance_deferred_asset",
        "prior_source_surface": "forecast_hardening;source_method_matrix;marginal_channel_registry",
        "marginal_status": "included_inside_public_interest_net_block",
        "selected_role": "public_interest_block_input",
        "theory_reason": "Fed remittances and deferred-asset timing absorb or defer public-interest support",
        "required_formula": "delta_remittance_or_deferred_asset_timing_bil",
        "source_or_assumption_route": "remittance_state_component_inside_public_interest_net_block",
        "overlap_policy": "net_inside_public_interest_block_only",
        "demand_conversion_policy": "absorber_timing_row_not_standalone_demand_support",
        "output_table": "ratewall_marginal_public_interest_components.csv",
        "gate_id": "public_interest_remittance_component_gate",
        "test_id": "test_remittance_state_is_block_input_only",
        "promotion_rule": "component_enters_only_when_net_block_identity_passes",
        "blocked_use": "standalone_selected_marginal_n",
        "claim_boundary": "remittance_timing_adjusts_public_interest_net_block",
    },
    {
        "prior_channel_id": "remittance_state",
        "prior_source_surface": "forecast_hardening;source_method_matrix;marginal_channel_registry",
        "marginal_status": "included_inside_public_interest_net_block",
        "selected_role": "public_interest_block_input",
        "theory_reason": "legacy remittance-state rows are retained as the remittance/deferred-asset component of the public-interest net block",
        "required_formula": "delta_remittance_or_deferred_asset_timing_bil",
        "source_or_assumption_route": "remittance_state_component_inside_public_interest_net_block",
        "overlap_policy": "net_inside_public_interest_block_only",
        "demand_conversion_policy": "absorber_timing_row_not_standalone_demand_support",
        "output_table": "ratewall_marginal_public_interest_components.csv",
        "gate_id": "public_interest_remittance_component_gate",
        "test_id": "test_remittance_state_is_block_input_only",
        "promotion_rule": "component_enters_only_when_net_block_identity_passes",
        "blocked_use": "standalone_selected_marginal_n",
        "claim_boundary": "remittance_state_is_legacy_id_for_public_interest_remittance_component",
    },
    {
        "prior_channel_id": "public_interest_tax_timing",
        "prior_source_surface": "core_support_parity;forecast_10y",
        "marginal_status": "included_inside_public_interest_net_block",
        "selected_role": "public_interest_absorber_input",
        "theory_reason": "tax timing changes the current-demand value of interest receipts",
        "required_formula": "delta_tax_timing_absorber_bil",
        "source_or_assumption_route": "tax_timing_absorber_component",
        "overlap_policy": "net_inside_public_interest_block_only",
        "demand_conversion_policy": "tax_absorber_reduces_current_demand_support",
        "output_table": "ratewall_marginal_public_interest_components.csv",
        "gate_id": "public_interest_tax_timing_component_gate",
        "test_id": "test_public_interest_components_do_not_enter_standalone_selected_n",
        "promotion_rule": "component_enters_only_when_net_block_identity_passes",
        "blocked_use": "tax_absorber_as_positive_standalone_support",
        "claim_boundary": "tax_timing_is_public_interest_absorber",
    },
    {
        "prior_channel_id": "public_interest_fiscal_tga_liquidity",
        "prior_source_surface": "core_support_parity;forecast_10y",
        "marginal_status": "included_inside_public_interest_net_block",
        "selected_role": "public_interest_absorber_input",
        "theory_reason": "fiscal offset, TGA, and liquidity routing can absorb public-interest cash-flow support",
        "required_formula": "delta_fiscal_tga_liquidity_absorber_bil",
        "source_or_assumption_route": "fiscal_tga_liquidity_component",
        "overlap_policy": "net_inside_public_interest_block_and_remove_tdcsim_overlap",
        "demand_conversion_policy": "absorber_reduces_current_demand_support",
        "output_table": "ratewall_marginal_public_interest_components.csv",
        "gate_id": "public_interest_fiscal_tga_component_gate",
        "test_id": "test_public_interest_components_do_not_enter_standalone_selected_n",
        "promotion_rule": "component_enters_only_when_net_block_identity_passes",
        "blocked_use": "tga_or_fiscal_absorber_as_positive_standalone_support",
        "claim_boundary": "fiscal_tga_liquidity_rows_are_public_interest_absorbers",
    },
    {
        "prior_channel_id": "public_interest_foreign_holder_leakage",
        "prior_source_surface": "forecast_10y;historical_coverage_contract",
        "marginal_status": "included_inside_public_interest_net_block",
        "selected_role": "public_interest_leakage_input",
        "theory_reason": "foreign-holder receipts are leakage from domestic current-demand support",
        "required_formula": "delta_foreign_holder_leakage_bil",
        "source_or_assumption_route": "holder_split_component",
        "overlap_policy": "net_inside_public_interest_block_only",
        "demand_conversion_policy": "foreign_leakage_excluded_from_domestic_current_demand",
        "output_table": "ratewall_marginal_public_interest_components.csv",
        "gate_id": "public_interest_holder_leakage_gate",
        "test_id": "test_public_interest_components_do_not_enter_standalone_selected_n",
        "promotion_rule": "component_enters_only_when_net_block_identity_passes",
        "blocked_use": "foreign_interest_as_domestic_support",
        "claim_boundary": "foreign_holder_receipts_are_leakage_rows",
    },
    {
        "prior_channel_id": "tdc_ex_overlap_beta_chi",
        "prior_source_surface": "marginal_tdcsim;core_support_parity;current_observed_overlay",
        "marginal_status": "selected_central_after_gate",
        "selected_role": "selected_marginal_n_candidate",
        "theory_reason": "TDC belongs only to the extent the standardized rate shock creates extra non-overlapping support in the same state",
        "required_formula": "delta_tdc_ex_overlap_bil * beta * chi",
        "source_or_assumption_route": "tdcsim_same_state_baseline_shock_source_pair",
        "overlap_policy": "subtract_overlap_before_beta_chi",
        "demand_conversion_policy": "beta_times_chi_applied_after_ex_overlap_delta",
        "output_table": "ratewall_marginal_tdc_support_panel.csv",
        "gate_id": "tdcsim_source_pair_gate",
        "test_id": "test_selected_numerator_uses_delta_tdc_ex_overlap_beta_chi_only",
        "promotion_rule": "selected_when_v0p4_pair_verifies_with_same_state_inputs_and_component_overlap_identity",
        "blocked_use": "full_tdc_level;deposit_stock_level;legacy_runtime_tdc_support;current_overlay_support;core_support_parity_support;cross_state_subtraction",
        "claim_boundary": "tdc_selected_only_as_marginal_ex_overlap_response_to_plus_100bp_year",
    },
    {
        "prior_channel_id": "tdcsim_rate25_derivative_proxy",
        "prior_source_surface": "core_support_parity",
        "marginal_status": "sensitivity_only",
        "selected_role": "tdc_nonselected_proxy",
        "theory_reason": "old up/down rate25 rows can bound a local derivative but are not source-grade same-state v0p4 pairs by default",
        "required_formula": "2 * (tdcsim_rate_up_25bp_v1 - tdcsim_rate_down_25bp_v1) * beta * chi",
        "source_or_assumption_route": "rate25_symmetric_derivative_existing_tdcsim_diagnostic_rows",
        "overlap_policy": "nonselected_unless_overlap_audit_promotes",
        "demand_conversion_policy": "beta_times_chi_proxy_only",
        "output_table": "ratewall_marginal_tdc_proxy_sensitivity.csv",
        "gate_id": "tdcsim_rate25_proxy_gate",
        "test_id": "test_current_overlay_tdc_support_remains_blocked",
        "promotion_rule": "can_promote_only_after_same_state_same_input_same_overlap_audit",
        "blocked_use": "selected_rw_m;canonical_headline_promotion;source_grade_tdcsim_pair_claim;full_tdc_level",
        "claim_boundary": "rate25_proxy_is_nonselected_sensitivity_until_promoted",
    },
    {
        "prior_channel_id": "deposit_safe_yield_payer_flow",
        "prior_source_surface": "realized_safe_yield_income;TSDABSHNO;assumption_mode",
        "marginal_status": "selected_central_after_gate",
        "selected_role": "selected_marginal_n_candidate",
        "theory_reason": "deposit safe-yield belongs as extra recipient safe-yield support caused by the shock after beta, overlap, tax timing, and spend controls",
        "required_formula": "delta_safe_yield_bil",
        "source_or_assumption_route": "household_npish_time_savings_stock_beta_proxy_assumption_mode",
        "overlap_policy": "remove_overlap_with_tdcsim_deposit_public_interest_and_mmf_routes",
        "demand_conversion_policy": "recipient_share_times_current_spend_share_after_tax_timing",
        "output_table": "ratewall_marginal_safe_yield_delta.csv",
        "gate_id": "d1_safe_yield_household_npish_stock_beta_proxy_gate",
        "test_id": "test_deposit_safe_yield_requires_all_marginal_gates",
        "promotion_rule": "selected_current_forecast_when_assumption_row_passes_source_recipient_denominator_tax_overlap_owner_gates",
        "blocked_use": "stock_rate_fallback;deposit_rate_level_times_stock;source_panel_only_promotion",
        "claim_boundary": "safe_yield_selected_only_as_same_state_marginal_support_after_beta_overlap_tax_and_spend_controls",
    },
    {
        "prior_channel_id": "deposit_safe_yield_stock_rate_fallback",
        "prior_source_surface": "realized_safe_yield_income",
        "marginal_status": "sensitivity_only",
        "selected_role": "nonselected_bounded_sensitivity",
        "theory_reason": "stock/rate fallback lacks the full marginal payer-flow recipient and overlap proof",
        "required_formula": "bounded_stock_rate_delta_sensitivity",
        "source_or_assumption_route": "existing_deposit_safe_yield_fallback_basis",
        "overlap_policy": "not_selected_without_overlap_gate",
        "demand_conversion_policy": "bounded_assumption_only",
        "output_table": "ratewall_realized_safe_yield_bounded_sensitivity.csv",
        "gate_id": "d1_fallback_sensitivity_gate",
        "test_id": "test_safe_yield_fallback_remains_noncentral",
        "promotion_rule": "convert_to_payer_flow_and_pass_full_D1_gate",
        "blocked_use": "selected_central_n;canonical_headline_promotion",
        "claim_boundary": "fallback_is_sensitivity_until_rebuilt_as_marginal_payer_flow",
    },
    {
        "prior_channel_id": "firm_cash_attenuation",
        "prior_source_surface": "residual_channel_closure;forecast_hardening",
        "marginal_status": "sensitivity_only",
        "selected_role": "nonselected_residual_candidate",
        "theory_reason": "firm cash can attenuate pressure but lacks selected disjoint marginal support proof",
        "required_formula": "delta_firm_cash_attenuation_bil",
        "source_or_assumption_route": "residual_sidecar_only",
        "overlap_policy": "xor_with_firm_liquid_asset_cushion",
        "demand_conversion_policy": "not_selected_without_disjoint_current_demand_conversion",
        "output_table": "ratewall_residual_numerator_surface.csv",
        "gate_id": "residual_firm_cash_gate",
        "test_id": "test_residual_channels_do_not_enter_selected_n_without_gate",
        "promotion_rule": "selected_only_with_disjoint_marginal_flow_and_demand_conversion",
        "blocked_use": "stock_only_support;double_count_with_firm_liquid_asset_cushion",
        "claim_boundary": "firm_cash_is_visible_noncentral_residual_candidate",
    },
    {
        "prior_channel_id": "firm_cash_liquidity",
        "prior_source_surface": "residual_channel_closure;forecast_hardening;marginal_channel_registry",
        "marginal_status": "sensitivity_only",
        "selected_role": "nonselected_residual_candidate",
        "theory_reason": "legacy firm-cash-liquidity rows stay visible but do not become selected support without a disjoint marginal flow",
        "required_formula": "delta_firm_cash_attenuation_bil",
        "source_or_assumption_route": "residual_sidecar_only",
        "overlap_policy": "xor_with_firm_liquid_asset_cushion",
        "demand_conversion_policy": "not_selected_without_disjoint_current_demand_conversion",
        "output_table": "ratewall_residual_numerator_surface.csv",
        "gate_id": "residual_firm_cash_gate",
        "test_id": "test_residual_channels_do_not_enter_selected_n_without_gate",
        "promotion_rule": "selected_only_with_disjoint_marginal_flow_and_demand_conversion",
        "blocked_use": "stock_only_support;double_count_with_firm_liquid_asset_cushion",
        "claim_boundary": "firm_cash_liquidity_is_legacy_id_for_nonselected_residual_candidate",
    },
    {
        "prior_channel_id": "firm_liquid_asset_cushion",
        "prior_source_surface": "residual_channel_closure",
        "marginal_status": "replacement_only",
        "selected_role": "xor_replacement_candidate",
        "theory_reason": "liquid-asset cushion can replace but not add to firm cash attenuation",
        "required_formula": "delta_firm_liquid_asset_cushion_bil",
        "source_or_assumption_route": "firm_liquidity_replacement_decision",
        "overlap_policy": "xor_replacement_for_firm_cash_attenuation",
        "demand_conversion_policy": "not_selected_without_disjoint_current_demand_conversion",
        "output_table": "ratewall_firm_liquidity_replacement_decision.csv",
        "gate_id": "firm_liquidity_replacement_gate",
        "test_id": "test_firm_cash_and_liquid_asset_cushion_are_xor",
        "promotion_rule": "may_replace_firm_cash_only_after_xor_decision",
        "blocked_use": "additive_selected_n_with_firm_cash_attenuation",
        "claim_boundary": "firm_liquid_asset_cushion_is_replacement_only",
    },
    {
        "prior_channel_id": "residual_household_safe_yield",
        "prior_source_surface": "forecast_hardening;residual_channel_closure",
        "marginal_status": "sensitivity_only",
        "selected_role": "nonselected_residual_candidate",
        "theory_reason": "residual household safe-yield capture is plausible but not disjoint from D1/MMF/T-bill routes by default",
        "required_formula": "delta_residual_household_safe_yield_bil",
        "source_or_assumption_route": "residual_sidecar_only",
        "overlap_policy": "not_selected_without_disjointness_from_D1_mmf_tbill",
        "demand_conversion_policy": "not_selected_without_current_demand_conversion",
        "output_table": "ratewall_forecast_residual_safe_yield_level_bound.csv",
        "gate_id": "residual_household_safe_yield_gate",
        "test_id": "test_residual_channels_do_not_enter_selected_n_without_gate",
        "promotion_rule": "selected_only_with_disjoint_marginal_basis",
        "blocked_use": "selected_central_n_without_disjointness",
        "claim_boundary": "residual_safe_yield_is_sensitivity_until_disjoint",
    },
    {
        "prior_channel_id": "deposit_mmf_substitution_offset_drag",
        "prior_source_surface": "forecast_10y;residual_channel_closure",
        "marginal_status": "sensitivity_only",
        "selected_role": "nonselected_offset_drag_candidate",
        "theory_reason": "substitution can offset or drag support but must be paired and disjoint",
        "required_formula": "delta_deposit_mmf_substitution_offset_or_drag_bil",
        "source_or_assumption_route": "paired_substitution_sidecar",
        "overlap_policy": "not_selected_without_pairing_and_nonoverlap",
        "demand_conversion_policy": "not_selected_without_current_demand_conversion",
        "output_table": "ratewall_residual_channel_admission_matrix.csv",
        "gate_id": "deposit_mmf_substitution_gate",
        "test_id": "test_residual_channels_do_not_enter_selected_n_without_gate",
        "promotion_rule": "selected_only_with_paired_disjoint_marginal_flow",
        "blocked_use": "unpaired_offset_or_drag_as_selected_n",
        "claim_boundary": "deposit_mmf_substitution_is_nonselected_until_paired",
    },
    {
        "prior_channel_id": "mmf_tbill_realized_yield",
        "prior_source_surface": "forecast_10y;realized_safe_yield_income;ICI_retail_prime_MMF_assumption_mode",
        "marginal_status": "selected_central_after_gate",
        "selected_role": "selected_marginal_n_candidate",
        "theory_reason": "retail prime MMF safe-yield support is selected only through the narrowed admitted-disjoint residual route after private-asset, recipient, overlap, tax, spend, and payer-drag controls",
        "required_formula": "delta_other_admitted_disjoint_bil",
        "source_or_assumption_route": "residual_private_retail_prime_mmf_safe_yield_assumption_mode",
        "overlap_policy": "nonoverlap_factor_against_D1_TDCSim_and_public_interest",
        "demand_conversion_policy": "tax_timing_current_spend_and_private_payer_drag_controls",
        "output_table": "ratewall_marginal_admitted_disjoint_delta.csv",
        "gate_id": "residual_private_retail_prime_mmf_safe_yield_gate",
        "test_id": "test_mmf_tbill_yield_remains_nonselected_without_recipient_gate",
        "promotion_rule": "selected_current_forecast_when_admitted_disjoint_assumption_row_passes_source_overlap_and_demand_gates",
        "blocked_use": "raw_mmf_or_tbill_yield_level_as_selected_n;broader_mmf_tbill_without_retail_prime_scope",
        "claim_boundary": "retail_prime_mmf_safe_yield_selected_only_as_admitted_disjoint_marginal_support",
    },
    {
        "prior_channel_id": "zero_low_apr_credit",
        "prior_source_surface": "forecast_10y;residual_channel_closure;source_method_matrix",
        "marginal_status": "sidecar_only",
        "selected_role": "denominator_credit_sidecar",
        "theory_reason": "zero or low APR credit changes insulation/drag rather than direct selected support absent a source-backed marginal flow",
        "required_formula": "credit_insulation_or_drag_sidecar_metric",
        "source_or_assumption_route": "credit_sidecar_materiality_screen",
        "overlap_policy": "not_selected_n",
        "demand_conversion_policy": "sidecar_only_until_rate_sensitive_payment_flow_identified",
        "output_table": "ratewall_forecast_zero_low_apr_credit_materiality.csv",
        "gate_id": "zero_low_apr_credit_sidecar_gate",
        "test_id": "test_credit_sidecars_do_not_enter_selected_n",
        "promotion_rule": "requires_stock_duration_wedge_pass_through_demand_conversion_and_materiality",
        "blocked_use": "selected_marginal_n;stock_only_support",
        "claim_boundary": "zero_low_apr_credit_is_sidecar_until_payment_flow_gate",
    },
    {
        "prior_channel_id": "credit_card_promo_bnpl",
        "prior_source_surface": "source_method_matrix;forecast_10y",
        "marginal_status": "sidecar_only",
        "selected_role": "denominator_credit_sidecar",
        "theory_reason": "promo balances and BNPL may insulate borrowers but are not selected support without marginal payment-flow evidence",
        "required_formula": "credit_card_promo_bnpl_insulation_metric",
        "source_or_assumption_route": "credit_sidecar_materiality_screen",
        "overlap_policy": "not_selected_n",
        "demand_conversion_policy": "sidecar_only_until_rate_sensitive_payment_flow_identified",
        "output_table": "ratewall_residual_channel_admission_matrix.csv",
        "gate_id": "credit_card_bnpl_sidecar_gate",
        "test_id": "test_credit_sidecars_do_not_enter_selected_n",
        "promotion_rule": "requires_product_stock_duration_wedge_pass_through_and_materiality",
        "blocked_use": "selected_marginal_n;stock_only_support",
        "claim_boundary": "credit_card_promo_bnpl_is_sidecar_until_payment_flow_gate",
    },
    {
        "prior_channel_id": "firm_rollover_pressure",
        "prior_source_surface": "source_method_matrix;residual_channel_closure",
        "marginal_status": "sidecar_only",
        "selected_role": "denominator_credit_sidecar",
        "theory_reason": "firm rollover pressure is primarily drag/denominator context unless a disjoint support flow is built",
        "required_formula": "firm_rollover_pressure_sidecar_metric",
        "source_or_assumption_route": "credit_sidecar_materiality_screen",
        "overlap_policy": "not_selected_n",
        "demand_conversion_policy": "sidecar_only_until_disjoint_support_flow_identified",
        "output_table": "ratewall_residual_channel_admission_matrix.csv",
        "gate_id": "firm_rollover_sidecar_gate",
        "test_id": "test_credit_sidecars_do_not_enter_selected_n",
        "promotion_rule": "requires_disjoint_marginal_support_flow_and_demand_conversion",
        "blocked_use": "selected_marginal_n;denominator_drag_booked_as_n",
        "claim_boundary": "firm_rollover_pressure_is_sidecar_until_disjoint_flow_gate",
    },
    {
        "prior_channel_id": "residual_safe_asset_drag",
        "prior_source_surface": "residual_channel_closure",
        "marginal_status": "sidecar_only",
        "selected_role": "nonselected_drag_candidate",
        "theory_reason": "safe-asset drag is not positive selected support unless a disjoint residual numerator basis is built",
        "required_formula": "delta_residual_safe_asset_drag_bil",
        "source_or_assumption_route": "residual_safe_asset_drag_admission_gate",
        "overlap_policy": "not_selected_without_disjoint_residual_basis",
        "demand_conversion_policy": "not_selected_without_current_demand_conversion",
        "output_table": "ratewall_residual_safe_asset_drag_admission_gate.csv",
        "gate_id": "residual_safe_asset_drag_gate",
        "test_id": "test_residual_channels_do_not_enter_selected_n_without_gate",
        "promotion_rule": "selected_only_with_disjoint_residual_numerator_basis",
        "blocked_use": "safe_asset_drag_as_positive_support;selected_n_without_disjointness",
        "claim_boundary": "residual_safe_asset_drag_is_sidecar_until_disjoint_basis",
    },
    {
        "prior_channel_id": "conventional_demand_drag",
        "prior_source_surface": "marginal_denominator;denominator_parity;historical_provisional_estimate",
        "marginal_status": "selected_central_after_gate",
        "selected_role": "selected_marginal_d",
        "theory_reason": "the denominator is the standardized conventional-demand drag from the +100bp-year shock",
        "required_formula": "nominal_gdp_bil * c_D * (shock_bps_year / 100) * state_multiplier",
        "source_or_assumption_route": "denominator_state_multiplier_neutral_selected_default",
        "overlap_policy": "not_applicable_denominator",
        "demand_conversion_policy": "denominator_threshold_scale_not_numerator_support",
        "output_table": "ratewall_denominator_state_multiplier.csv",
        "gate_id": "denominator_state_multiplier_gate",
        "test_id": "test_denominator_state_multiplier_blocks_mechanical_rate_drivers",
        "promotion_rule": "selected_with_state_multiplier_1_until_admitted_state_transmission_model",
        "blocked_use": "numerator_support;current_rate_level;old_path_D;tdc_stock;deposit_stock;beta;chi;numerator_size;scenario_label",
        "claim_boundary": "selected_D_is_standardized_threshold_scale_not_current_rate_level",
    },
    {
        "prior_channel_id": "legacy_current_benchmark",
        "prior_source_surface": "current_object_bridge;current_observed_overlay",
        "marginal_status": "diagnostic_only",
        "selected_role": "comparison_context_only",
        "theory_reason": "the frozen current benchmark is a level ratio, not shock-minus-baseline marginal support",
        "required_formula": "not_selected_old_level_ratio",
        "source_or_assumption_route": "comparison_context_only",
        "overlap_policy": "not_selected",
        "demand_conversion_policy": "not_selected",
        "output_table": "ratewall_marginal_row_role_reset.csv",
        "gate_id": "legacy_current_blocker_gate",
        "test_id": "test_bad_row_role_reset_rejects_old_row_promotion",
        "promotion_rule": "never_promote_without_same_state_delta_rebuild",
        "blocked_use": "selected_rw_m;selected_marginal_n;selected_marginal_d",
        "claim_boundary": "legacy_current_benchmark_is_diagnostic_only",
    },
    {
        "prior_channel_id": "legacy_forecast_ratio",
        "prior_source_surface": "forecast_10y",
        "marginal_status": "diagnostic_only",
        "selected_role": "comparison_context_only",
        "theory_reason": "old forecast ratios are level/scenario surfaces, not same-state marginal threshold rows",
        "required_formula": "not_selected_old_forecast_ratio",
        "source_or_assumption_route": "comparison_context_only",
        "overlap_policy": "not_selected",
        "demand_conversion_policy": "not_selected",
        "output_table": "ratewall_marginal_row_role_reset.csv",
        "gate_id": "legacy_forecast_blocker_gate",
        "test_id": "test_bad_channel_rejects_legacy_ratio_promotion",
        "promotion_rule": "never_promote_without_same_state_delta_rebuild",
        "blocked_use": "selected_rw_m;selected_marginal_n;selected_marginal_d",
        "claim_boundary": "legacy_forecast_ratio_is_diagnostic_only",
    },
    {
        "prior_channel_id": "historical_classifier",
        "prior_source_surface": "historical_provisional_estimate;historical_coverage_contract",
        "marginal_status": "diagnostic_only",
        "selected_role": "historical_context_only_until_delta_rebuild",
        "theory_reason": "historical context lacks selected same-quarter +100bp-year marginal deltas",
        "required_formula": "historical_same_quarter_delta_N_required",
        "source_or_assumption_route": "historical_marginal_delta_builder_required",
        "overlap_policy": "not_selected_until_historical_overlap_gate",
        "demand_conversion_policy": "not_selected_until_historical_current_demand_policy",
        "output_table": "ratewall_marginal_row_role_reset.csv",
        "gate_id": "historical_classifier_blocker_gate",
        "test_id": "test_row_role_reset_classifies_existing_selected_exposure_rows",
        "promotion_rule": "selected_only_after_historical_same_quarter_marginal_delta_build",
        "blocked_use": "selected_rw_m_without_delta_n;classifier_as_final_ratio",
        "claim_boundary": "historical_rows_are_context_until_rebuilt_as_marginal_object",
    },
    {
        "prior_channel_id": "old_historical_path_d",
        "prior_source_surface": "historical_provisional_estimate;historical_comparable_adapter",
        "marginal_status": "blocked_non_marginal_form",
        "selected_role": "diagnostic_denominator_context",
        "theory_reason": "old path-D is a rate-environment exposure denominator, not the standardized marginal denominator",
        "required_formula": "not_selected_old_path_D",
        "source_or_assumption_route": "fixed_D_or_marginal_denominator_rebuild_only",
        "overlap_policy": "not_applicable_denominator",
        "demand_conversion_policy": "not_selected",
        "output_table": "ratewall_rate_environment_exposure_diagnostic.csv",
        "gate_id": "old_path_d_blocker_gate",
        "test_id": "test_bad_surface_rejects_formula_drift",
        "promotion_rule": "never_promote_old_path_D_as_selected_marginal_D",
        "blocked_use": "selected_marginal_d;selected_rw_m;current_rate_level",
        "claim_boundary": "old_path_D_is_diagnostic_not_final_D",
    },
    {
        "prior_channel_id": "old_exposure_ratio_generic",
        "prior_source_surface": "current_object_bridge;forecast_10y;historical_provisional_estimate;final_model_readout",
        "marginal_status": "diagnostic_only",
        "selected_role": "comparison_context_only",
        "theory_reason": "old exposure ratios do not measure the same-state +100bp-year marginal object",
        "required_formula": "not_selected_old_exposure_ratio",
        "source_or_assumption_route": "comparison_context_only",
        "overlap_policy": "not_selected",
        "demand_conversion_policy": "not_selected",
        "output_table": "ratewall_marginal_row_role_reset.csv",
        "gate_id": "old_exposure_ratio_blocker_gate",
        "test_id": "test_bad_channel_rejects_legacy_ratio_promotion",
        "promotion_rule": "never_promote_without_same_state_delta_rebuild",
        "blocked_use": "selected_rw_m;canonical_headline_promotion",
        "claim_boundary": "old_exposure_ratios_are_diagnostic_only",
    },
]


class MarginalObjectLedgerError(ValueError):
    """Raised when marginal object rows violate the RW_M contract."""


def load_object_config(path: str | Path = DEFAULT_OBJECT_CONFIG_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise MarginalObjectLedgerError("marginal object config must be a mapping")
    return payload


def load_channel_registry(
    path: str | Path = DEFAULT_CHANNEL_REGISTRY_PATH,
) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise MarginalObjectLedgerError("marginal channel registry must be a mapping")
    return payload


def load_true_v1_channel_inventory(
    path: str | Path = DEFAULT_TRUE_V1_CHANNEL_INVENTORY_PATH,
) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise MarginalObjectLedgerError("true V1 channel inventory must be a mapping")
    validate_true_v1_channel_inventory(payload)
    return payload


def marginal_object_contract_rows(
    *,
    object_config_path: str | Path = DEFAULT_OBJECT_CONFIG_PATH,
) -> list[dict[str, str]]:
    """Return the period-level final-object contract rows."""

    config = load_object_config(object_config_path)
    object_id = _clean(config.get("marginal_object_id"))
    formula = _clean(config.get("rw_m_formula"))
    shock_path_id = _clean(config.get("shock_path_id"))
    shock_bps_year = _clean(config.get("shock_bps_year"))
    same_state_pair_required = _bool_text(config.get("same_state_pair_required"))
    selection_status = _clean(config.get("selected_ratio_status"))
    rows = [
        {
            "marginal_object_contract_row_id": f"marginal_object_contract::{period}",
            "marginal_object_id": object_id,
            "period_object": period,
            "rw_m_formula": formula,
            "shock_path_id": shock_path_id,
            "shock_bps_year": shock_bps_year,
            "same_state_pair_required": same_state_pair_required,
            "selected_rw_m": "false",
            "selected_n_basis": (
                "same_state_shock_minus_baseline_delta_N_required"
            ),
            "selected_d_basis": (
                "Delta_D_conv_from_nominal_gdp_times_c_D_times_100bp_year"
            ),
            "tdc_inclusion_rule": (
                "delta_tdc_ex_overlap_bil_times_beta_times_chi_only_after_tdcsim_pair"
            ),
            "current_legacy_benchmark_status": (
                "blocked_as_final_rw_m_comparison_context_only"
            ),
            "forecast_legacy_ratio_status": (
                "blocked_as_final_rw_m_comparison_context_only"
            ),
            "historical_classifier_status": (
                "blocked_until_same_state_marginal_n_exists"
            ),
            "selection_gate_status": selection_status,
            "allowed_use": "marginal_object_contract_and_builder_gate",
            "blocked_use": (
                "select_old_current_benchmark;select_old_forecast_ratio;"
                "select_historical_classifier_without_delta_n"
            ),
            "claim_boundary": (
                "final_rw_m_requires_plus_100bp_year_same_state_marginal_n_over_marginal_d"
            ),
        }
        for period in ["historical", "current", "forecast"]
    ]
    validate_marginal_object_contract(rows)
    return rows


def marginal_channel_status_rows(
    *,
    channel_registry_path: str | Path = DEFAULT_CHANNEL_REGISTRY_PATH,
) -> list[dict[str, str]]:
    """Return channel reclassification rows under the marginal object."""

    registry = load_channel_registry(channel_registry_path)
    rows = []
    for channel in registry.get("channels", []):
        channel_id = _clean(channel.get("channel_id"))
        rows.append(
            {
                "marginal_channel_status_row_id": (
                    f"marginal_channel_status::{channel_id}"
                ),
                "channel_id": channel_id,
                "channel_family": _clean(channel.get("channel_family")),
                "period_scope": _clean(channel.get("period_scope")),
                "final_role": _clean(channel.get("final_role")),
                "numerator_formula": _clean(channel.get("numerator_formula")),
                "marginal_delta_required": _bool_text(
                    channel.get("marginal_delta_required")
                ),
                "same_state_pair_required": _bool_text(
                    channel.get("same_state_pair_required")
                ),
                "source_status": _clean(channel.get("source_status")),
                "viability_status": _clean(channel.get("viability_status")),
                "promotion_status": _clean(channel.get("promotion_status")),
                "fail_closed_label": _clean(channel.get("fail_closed_label")),
                "allowed_use": _clean(channel.get("allowed_use")),
                "blocked_use": _clean(channel.get("blocked_use")),
                "claim_boundary": _clean(channel.get("claim_boundary")),
            }
        )
    validate_marginal_channel_status(rows)
    return rows


def marginal_row_role_reset_rows(
    *,
    current_bridge_path: str | Path = DEFAULT_CURRENT_BRIDGE_PATH,
    forecast_surface_path: str | Path = DEFAULT_FORECAST_SURFACE_PATH,
    historical_root_path: str | Path = DEFAULT_HISTORICAL_ROOT_PATH,
    historical_denominator_path: str | Path = DEFAULT_HISTORICAL_DENOMINATOR_PATH,
) -> list[dict[str, str]]:
    """Classify old selected/exposure rows under the marginal object vocabulary."""

    rows: list[dict[str, str]] = []
    rows.extend(_current_bridge_reset_rows(Path(current_bridge_path)))
    rows.extend(_forecast_surface_reset_rows(Path(forecast_surface_path)))
    rows.extend(_historical_root_reset_rows(Path(historical_root_path)))
    rows.extend(_historical_denominator_reset_rows(Path(historical_denominator_path)))
    validate_marginal_row_role_reset(rows)
    return rows


def complete_marginal_channel_inventory_rows(
    *,
    channel_status_rows: Sequence[Mapping[str, str]] | None = None,
    row_role_reset_rows: Sequence[Mapping[str, str]] | None = None,
    true_v1_inventory_path: str | Path = DEFAULT_TRUE_V1_CHANNEL_INVENTORY_PATH,
) -> list[dict[str, str]]:
    """Return the channel-completeness inventory for the final marginal roadmap."""

    load_true_v1_channel_inventory(true_v1_inventory_path)
    rows = [dict(row) for row in COMPLETE_CHANNEL_REQUIREMENTS]
    validate_complete_marginal_channel_inventory(
        rows,
        channel_status_rows=channel_status_rows,
        row_role_reset_rows=row_role_reset_rows,
    )
    return rows


def validate_true_v1_channel_inventory(payload: Mapping[str, Any]) -> None:
    if payload.get("object_id") != "RW_M_PLUS_100BP_YEAR":
        raise MarginalObjectLedgerError("true V1 inventory object_id failed")
    channels = payload.get("channels")
    if not isinstance(channels, list) or not channels:
        raise MarginalObjectLedgerError("true V1 inventory channels are empty")
    by_id = {
        _clean(channel.get("channel_id")): channel
        for channel in channels
        if isinstance(channel, Mapping)
    }
    required = {
        "public_interest_net_block",
        "direct_treasury_interest",
        "bank_treasury_interest",
        "iorb_ioer_reserves",
        "on_rrp",
        "remittances_deferred_asset",
        "taxes",
        "tga_liquidity_absorbers",
        "foreign_leakage",
        "tdc_ex_overlap_beta_chi",
        "d1_safe_yield_payer_flow",
        "residual_mmf_tbill_sidecars",
        "credit_zero_low_apr_insulation",
        "denominator_conventional_drag",
    }
    missing = required - set(by_id)
    if missing:
        raise MarginalObjectLedgerError(
            f"true V1 inventory missing channels: {sorted(missing)}"
        )
    for channel_id, channel in by_id.items():
        scope = channel.get("period_scope")
        if not isinstance(scope, list):
            raise MarginalObjectLedgerError(
                f"{channel_id} period_scope must be a list"
            )
        if channel_id in required and set(scope) != {"historical", "current", "forecast"}:
            raise MarginalObjectLedgerError(
                f"{channel_id} must cover historical/current/forecast"
            )
        formula_id = _clean(channel.get("formula_id"))
        if not formula_id:
            raise MarginalObjectLedgerError(f"{channel_id} missing formula_id")
    if by_id["tdc_ex_overlap_beta_chi"].get("selected_slot") != "Delta_N_selected":
        raise MarginalObjectLedgerError("TDC must enter Delta_N_selected after pair gate")
    if by_id["credit_zero_low_apr_insulation"].get("selected_slot") != "none_in_v1":
        raise MarginalObjectLedgerError("credit sidecar cannot enter selected V1 N")
    if by_id["denominator_conventional_drag"].get("selected_slot") != "Delta_D_conv":
        raise MarginalObjectLedgerError("denominator channel must enter Delta_D_conv")


def build_all(
    *,
    object_config_path: str | Path = DEFAULT_OBJECT_CONFIG_PATH,
    channel_registry_path: str | Path = DEFAULT_CHANNEL_REGISTRY_PATH,
    current_bridge_path: str | Path = DEFAULT_CURRENT_BRIDGE_PATH,
    forecast_surface_path: str | Path = DEFAULT_FORECAST_SURFACE_PATH,
    historical_root_path: str | Path = DEFAULT_HISTORICAL_ROOT_PATH,
    historical_denominator_path: str | Path = DEFAULT_HISTORICAL_DENOMINATOR_PATH,
) -> dict[str, list[dict[str, str]]]:
    contract = marginal_object_contract_rows(object_config_path=object_config_path)
    channel_status = marginal_channel_status_rows(
        channel_registry_path=channel_registry_path
    )
    row_role_reset = marginal_row_role_reset_rows(
        current_bridge_path=current_bridge_path,
        forecast_surface_path=forecast_surface_path,
        historical_root_path=historical_root_path,
        historical_denominator_path=historical_denominator_path,
    )
    complete_inventory = complete_marginal_channel_inventory_rows(
        channel_status_rows=channel_status,
        row_role_reset_rows=row_role_reset,
    )
    return {
        "contract_rows": contract,
        "channel_status_rows": channel_status,
        "row_role_reset_rows": row_role_reset,
        "complete_inventory_rows": complete_inventory,
    }


def write_marginal_object_ledger_outputs(
    output_dir: str | Path,
    *,
    contract_rows: Sequence[Mapping[str, str]],
    channel_status_rows: Sequence[Mapping[str, str]],
    row_role_reset_rows: Sequence[Mapping[str, str]],
    complete_inventory_rows: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Path]:
    """Write marginal-object ledger outputs."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "contract_csv": out / "ratewall_marginal_object_contract.csv",
        "channel_status_csv": out / "ratewall_marginal_channel_status.csv",
        "row_role_reset_csv": out / "ratewall_marginal_row_role_reset.csv",
        "complete_inventory_csv": out / "ratewall_marginal_channel_inventory.csv",
    }
    write_rows(
        paths["contract_csv"],
        [dict(row) for row in contract_rows],
        MARGINAL_OBJECT_CONTRACT_FIELDS,
    )
    write_rows(
        paths["channel_status_csv"],
        [dict(row) for row in channel_status_rows],
        MARGINAL_CHANNEL_STATUS_FIELDS,
    )
    write_rows(
        paths["row_role_reset_csv"],
        [dict(row) for row in row_role_reset_rows],
        MARGINAL_ROW_ROLE_RESET_FIELDS,
    )
    if complete_inventory_rows is None:
        complete_inventory_rows = complete_marginal_channel_inventory_rows(
            channel_status_rows=channel_status_rows,
            row_role_reset_rows=row_role_reset_rows,
        )
    write_rows(
        paths["complete_inventory_csv"],
        [dict(row) for row in complete_inventory_rows],
        COMPLETE_MARGINAL_CHANNEL_INVENTORY_FIELDS,
    )
    return paths


def validate_marginal_object_contract(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalObjectLedgerError("marginal object contract rows are empty")
    periods = {row.get("period_object", "") for row in rows}
    if periods != {"historical", "current", "forecast"}:
        raise MarginalObjectLedgerError(f"unexpected period set: {sorted(periods)}")
    for row in rows:
        if set(row) != set(MARGINAL_OBJECT_CONTRACT_FIELDS):
            raise MarginalObjectLedgerError("marginal object contract schema mismatch")
        if row["marginal_object_id"] != "RW_M_PLUS_100BP_YEAR":
            raise MarginalObjectLedgerError("unexpected marginal object id")
        if row["shock_path_id"] != "plus_100bp_year":
            raise MarginalObjectLedgerError("unexpected marginal shock path id")
        if row["selected_rw_m"] != "false":
            raise MarginalObjectLedgerError("RW_M cannot be selected before delta N exists")
        if "Delta_N" not in row["rw_m_formula"] or "Delta_D_conv" not in row["rw_m_formula"]:
            raise MarginalObjectLedgerError("RW_M formula must use Delta_N over Delta_D_conv")
        if row["shock_bps_year"] != "100":
            raise MarginalObjectLedgerError("RW_M contract requires 100bp-year shock")
        if row["same_state_pair_required"] != "true":
            raise MarginalObjectLedgerError("same-state pairing is required")
        blocked = row["blocked_use"]
        if "select_old_current_benchmark" not in blocked:
            raise MarginalObjectLedgerError("old current benchmark blocker missing")


def validate_marginal_channel_status(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalObjectLedgerError("marginal channel status rows are empty")
    by_id = {row["channel_id"]: row for row in rows}
    required = {
        "public_interest_net_block",
        "tdc_ex_overlap_beta_chi",
        "conventional_demand_drag",
        "deposit_safe_yield_payer_flow",
        "legacy_current_benchmark",
        "legacy_forecast_ratio",
        "historical_classifier",
        "old_historical_path_d",
        "old_exposure_ratio_generic",
        "remittance_state",
        "firm_cash_liquidity",
        "zero_low_apr_credit",
    }
    if not required <= set(by_id):
        raise MarginalObjectLedgerError(
            f"missing marginal channel rows: {sorted(required - set(by_id))}"
        )
    labels = {row["fail_closed_label"] for row in rows}
    if not labels <= FAIL_CLOSED_LABELS:
        raise MarginalObjectLedgerError(
            f"unknown fail-closed labels: {sorted(labels - FAIL_CLOSED_LABELS)}"
        )
    missing_labels = FAIL_CLOSED_LABELS - labels
    if missing_labels:
        raise MarginalObjectLedgerError(
            f"missing fail-closed labels: {sorted(missing_labels)}"
        )
    for row in rows:
        if set(row) != set(MARGINAL_CHANNEL_STATUS_FIELDS):
            raise MarginalObjectLedgerError("marginal channel status schema mismatch")
        if row["final_role"] not in MARGINAL_ROLES:
            raise MarginalObjectLedgerError(
                f"unknown marginal role: {row['final_role']}"
            )
        if row["marginal_delta_required"] != "true":
            raise MarginalObjectLedgerError("all marginal channels must require deltas")
        if row["same_state_pair_required"] != "true":
            raise MarginalObjectLedgerError("all marginal channels require same-state pairs")
    for channel_id in ["legacy_current_benchmark", "legacy_forecast_ratio"]:
        row = by_id[channel_id]
        if row["promotion_status"] != "blocked_old_exposure_ratio":
            raise MarginalObjectLedgerError("legacy exposure ratios must be blocked")
        if "selected_rw_m" not in row["blocked_use"]:
            raise MarginalObjectLedgerError("legacy exposure ratio selected_rw_m blocker missing")
    tdc = by_id["tdc_ex_overlap_beta_chi"]
    if tdc["numerator_formula"] != "delta_tdc_ex_overlap_bil * beta * chi":
        raise MarginalObjectLedgerError("TDC must use marginal ex-overlap beta chi formula")
    if "full_tdc_level" not in tdc["blocked_use"]:
        raise MarginalObjectLedgerError("full TDC level blocker missing")
    d_row = by_id["conventional_demand_drag"]
    if d_row["final_role"] != "selected_marginal_d":
        raise MarginalObjectLedgerError(
            "conventional demand drag must be selected marginal D"
        )
    if "numerator_support" not in d_row["blocked_use"]:
        raise MarginalObjectLedgerError("denominator-as-numerator blocker missing")


def validate_marginal_row_role_reset(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalObjectLedgerError("marginal row-role reset rows are empty")
    labels = {row["fail_closed_label"] for row in rows if row["fail_closed_label"]}
    required_labels = {
        "fail_closed_non_marginal_selected_n",
        "fail_closed_non_marginal_selected_d",
        "fail_closed_old_exposure_ratio_promoted",
        "fail_closed_previous_current_benchmark_selected_as_rw_m",
        "fail_closed_forecast_v1_ratio_selected_as_rw_m",
        "fail_closed_historical_classifier_without_marginal_n",
        "fail_closed_block_input_used_as_standalone_n",
        "fail_closed_denominator_drag_booked_as_n",
    }
    missing = required_labels - labels
    if missing:
        raise MarginalObjectLedgerError(
            f"row-role reset missing fail-closed labels: {sorted(missing)}"
        )
    for row in rows:
        if set(row) != set(MARGINAL_ROW_ROLE_RESET_FIELDS):
            raise MarginalObjectLedgerError("marginal row-role reset schema mismatch")
        if row["marginal_role"] not in MARGINAL_ROLES:
            raise MarginalObjectLedgerError(
                f"unknown row marginal role: {row['marginal_role']}"
            )
        if row["selected_final_rw_m_allowed"] != "false":
            raise MarginalObjectLedgerError(
                "old selected/exposure rows cannot enter final RW_M"
            )
        if "selected_final_rw_m" not in row["blocked_use"]:
            raise MarginalObjectLedgerError("selected final RW_M blocker missing")


def validate_complete_marginal_channel_inventory(
    rows: Sequence[Mapping[str, str]],
    *,
    channel_status_rows: Sequence[Mapping[str, str]] | None = None,
    row_role_reset_rows: Sequence[Mapping[str, str]] | None = None,
) -> None:
    if not rows:
        raise MarginalObjectLedgerError("complete marginal channel inventory is empty")
    by_id = {row["prior_channel_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise MarginalObjectLedgerError("duplicate complete inventory channel id")
    required = {
        "public_interest_net_block",
        "public_interest_direct_treasury_interest",
        "public_interest_bank_treasury_interest",
        "public_interest_iorb_reserves",
        "public_interest_on_rrp",
        "public_interest_remittance_deferred_asset",
        "public_interest_tax_timing",
        "public_interest_fiscal_tga_liquidity",
        "public_interest_foreign_holder_leakage",
        "tdc_ex_overlap_beta_chi",
        "tdcsim_rate25_derivative_proxy",
        "deposit_safe_yield_payer_flow",
        "deposit_safe_yield_stock_rate_fallback",
        "firm_cash_attenuation",
        "firm_liquid_asset_cushion",
        "residual_household_safe_yield",
        "deposit_mmf_substitution_offset_drag",
        "mmf_tbill_realized_yield",
        "zero_low_apr_credit",
        "credit_card_promo_bnpl",
        "firm_rollover_pressure",
        "residual_safe_asset_drag",
        "conventional_demand_drag",
        "legacy_current_benchmark",
        "legacy_forecast_ratio",
        "historical_classifier",
        "old_historical_path_d",
        "old_exposure_ratio_generic",
    }
    missing = required - set(by_id)
    if missing:
        raise MarginalObjectLedgerError(
            f"complete inventory missing required channels: {sorted(missing)}"
        )
    if channel_status_rows is not None:
        registry_ids = {row["channel_id"] for row in channel_status_rows}
        missing_registry = registry_ids - set(by_id)
        if missing_registry:
            raise MarginalObjectLedgerError(
                f"complete inventory missing registry rows: {sorted(missing_registry)}"
            )
    if row_role_reset_rows is not None:
        source_families = {
            _source_family(row["source_artifact"]) for row in row_role_reset_rows
        }
        inventory_sources = {
            source
            for row in rows
            for source in row["prior_source_surface"].split(";")
            if source
        }
        missing_sources = source_families - inventory_sources
        if missing_sources:
            raise MarginalObjectLedgerError(
                f"complete inventory missing prior source families: {sorted(missing_sources)}"
            )
    for row in rows:
        if set(row) != set(COMPLETE_MARGINAL_CHANNEL_INVENTORY_FIELDS):
            raise MarginalObjectLedgerError("complete inventory schema mismatch")
        if row["marginal_status"] not in INVENTORY_STATUSES:
            raise MarginalObjectLedgerError(
                f"unknown complete inventory status: {row['marginal_status']}"
            )
        for field in COMPLETE_MARGINAL_CHANNEL_INVENTORY_FIELDS:
            if not row[field]:
                raise MarginalObjectLedgerError(
                    f"complete inventory blank field {field} for {row['prior_channel_id']}"
                )
        if row["marginal_status"] == "selected_central_after_gate":
            formula = row["required_formula"]
            if (
                "delta" not in formula.lower()
                and "nominal_gdp_bil * c_D" not in formula
            ):
                raise MarginalObjectLedgerError(
                    "selected central inventory rows must use marginal delta or D formula"
                )
        if row["prior_channel_id"] == "tdc_ex_overlap_beta_chi":
            if row["required_formula"] != "delta_tdc_ex_overlap_bil * beta * chi":
                raise MarginalObjectLedgerError("TDC inventory formula drift")
            for blocker in [
                "full_tdc_level",
                "deposit_stock_level",
                "legacy_runtime_tdc_support",
                "current_overlay_support",
                "core_support_parity_support",
                "cross_state_subtraction",
            ]:
                if blocker not in row["blocked_use"]:
                    raise MarginalObjectLedgerError(
                        f"TDC inventory missing blocker: {blocker}"
                    )
        if row["prior_channel_id"] == "conventional_demand_drag":
            for blocker in [
                "current_rate_level",
                "old_path_D",
                "tdc_stock",
                "deposit_stock",
                "beta",
                "chi",
                "numerator_size",
                "scenario_label",
            ]:
                if blocker not in row["blocked_use"]:
                    raise MarginalObjectLedgerError(
                        f"denominator inventory missing blocker: {blocker}"
                    )


def _current_bridge_reset_rows(path: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in _read_csv_if_exists(path):
        row_id = row.get("current_object_bridge_row_id", "")
        current_object_id = row.get("current_object_id", "")
        role = row.get("current_object_role", "")
        if row.get("selected_current_row") == "true":
            marginal_role = "diagnostic_exposure_only"
            label = "fail_closed_previous_current_benchmark_selected_as_rw_m"
            rebuild = "current_state_same_state_delta_N_required"
        elif row.get("selected_current_component") == "true":
            if "legacy_tdc" in current_object_id:
                marginal_role = "diagnostic_exposure_only"
                label = "fail_closed_non_marginal_selected_n"
                rebuild = "tdcsim_marginal_pair_delta_tdc_required"
            else:
                marginal_role = "selected_marginal_block_input"
                label = "fail_closed_block_input_used_as_standalone_n"
                rebuild = "wrap_inside_delta_public_interest_net_block"
        elif "d1_safe_yield" in row_id:
            marginal_role = "sensitivity_only"
            label = "fail_closed_non_marginal_selected_n"
            rebuild = "marginal_payer_flow_delta_and_overlap_gates_required"
        elif "r38" in row_id:
            marginal_role = "candidate_marginal_replacement"
            label = "fail_closed_non_marginal_selected_n"
            rebuild = "same_state_delta_rebuild_required"
        else:
            marginal_role = "sensitivity_only"
            label = "fail_closed_old_exposure_ratio_promoted"
            rebuild = "comparison_only_no_rebuild_selected"
        out.append(
            _row_reset(
                source_artifact=str(path),
                source_row_id=row_id,
                period_object=row.get("period_object", "current"),
                period=row.get("current_object_id", ""),
                scenario_id=row.get("source_surface", ""),
                fields="n_bil;d_bil;rw;public_interest_component_bil;legacy_runtime_tdc_component_bil",
                old_role=role,
                marginal_role=marginal_role,
                label=label,
                rebuild=rebuild,
            )
        )
    return out


def _forecast_surface_reset_rows(path: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in _read_csv_if_exists(path):
        out.append(
            _row_reset(
                source_artifact=str(path),
                source_row_id=row.get("central_forecast_surface_row_id", ""),
                period_object="forecast",
                period=row.get("fiscal_year", ""),
                scenario_id=row.get("scenario_id", ""),
                fields=(
                    "central_n_bil;central_moving_denominator_bil;"
                    "central_ratewall_ratio;delta_central_n_vs_baseline_bil"
                ),
                old_role=row.get("central_choice_status", "old_forecast_surface"),
                marginal_role="diagnostic_exposure_only",
                label="fail_closed_forecast_v1_ratio_selected_as_rw_m",
                rebuild="forecast_same_state_delta_N_and_delta_D_required",
            )
        )
    return out


def _historical_root_reset_rows(path: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in _read_csv_if_exists(path):
        out.append(
            _row_reset(
                source_artifact=str(path),
                source_row_id=row.get("historical_root_public_interest_rw_row_id", ""),
                period_object="historical",
                period=row.get("period", ""),
                scenario_id=row.get("assumption_case", ""),
                fields=(
                    "root_public_interest_n_bil;root_public_interest_ratewall_ratio;"
                    "fixed_D_comparison_ratio"
                ),
                old_role=row.get("series_role", "historical_root_context"),
                marginal_role="diagnostic_exposure_only",
                label="fail_closed_historical_classifier_without_marginal_n",
                rebuild="historical_same_quarter_delta_N_required",
            )
        )
    return out


def _historical_denominator_reset_rows(path: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in _read_csv_if_exists(path):
        out.append(
            _row_reset(
                source_artifact=str(path),
                source_row_id=row.get("historical_denominator_convention_row_id", ""),
                period_object="historical",
                period=row.get("period", ""),
                scenario_id=row.get("selected_convention", ""),
                fields="selected_historical_path_D_bil;fixed_D_comparison_bil",
                old_role="old_historical_path_D",
                marginal_role="diagnostic_exposure_only",
                label="fail_closed_non_marginal_selected_d",
                rebuild="use_fixed_D_comparison_if_audits_to_nominal_gdp_times_0p00776",
            )
        )
    if out:
        out.append(
            _row_reset(
                source_artifact=str(path),
                source_row_id="historical_denominator_drag_not_numerator",
                period_object="historical",
                period="all",
                scenario_id="denominator_only",
                fields="fixed_D_comparison_bil",
                old_role="denominator_drag",
                marginal_role="denominator_only",
                label="fail_closed_denominator_drag_booked_as_n",
                rebuild="selected_marginal_D_only_never_numerator_support",
            )
        )
    return out


def _row_reset(
    *,
    source_artifact: str,
    source_row_id: str,
    period_object: str,
    period: str,
    scenario_id: str,
    fields: str,
    old_role: str,
    marginal_role: str,
    label: str,
    rebuild: str,
) -> dict[str, str]:
    return {
        "marginal_row_role_reset_row_id": (
            f"marginal_row_role_reset::{Path(source_artifact).stem}::{source_row_id}"
        ),
        "source_artifact": source_artifact,
        "source_row_id": source_row_id,
        "period_object": period_object,
        "period": period,
        "scenario_id": scenario_id,
        "old_selected_or_exposure_fields": fields,
        "old_role": old_role,
        "marginal_role": marginal_role,
        "selected_final_rw_m_allowed": "false",
        "fail_closed_label": label,
        "required_rebuild": rebuild,
        "allowed_use": "marginal_row_role_reset_audit",
        "blocked_use": "selected_final_rw_m;canonical_headline_promotion",
        "claim_boundary": "old_selected_or_exposure_row_reclassified_not_promoted",
    }


def _read_csv_if_exists(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _source_family(path: str) -> str:
    parts = Path(path).parts
    if "preliminary_scenario_results" in parts:
        idx = parts.index("preliminary_scenario_results")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    fixture_family = {
        "current": "current_object_bridge",
        "forecast": "forecast_10y",
        "historical_root": "historical_provisional_estimate",
        "historical_denominator": "historical_provisional_estimate",
    }
    if Path(path).stem in fixture_family:
        return fixture_family[Path(path).stem]
    return Path(path).stem


def _bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return _clean(value).lower()


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
