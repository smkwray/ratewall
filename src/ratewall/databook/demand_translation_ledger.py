"""Demand-translation registry and object-role ledger for RateWall D9."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from ratewall.databook.table_io import write_rows

DEFAULT_REGISTRY_PATH = Path("configs/ratewall_demand_translation_registry.yml")

APPROVED_REGISTRY = {
    "direct_private_cash_income": ("0.05", "0.12", "0.25"),
    "intermediated_financial_income": ("0.00", "0.03", "0.10"),
    "market_safe_yield_income": ("0.02", "0.06", "0.12"),
    "spendable_liquidity_inflow": ("0.03", "0.07", "0.12"),
    "realized_household_safe_yield_income": ("0.04", "0.08", "0.13"),
    "wealth_revaluation": ("", "", ""),
    "firm_liquidity_cushion": ("0.03", "0.10", "0.20"),
}

ALLOWED_OBJECT_ROLES = {
    "selected_n",
    "selected_block_input",
    "selected_benchmark_recast",
    "candidate_replacement",
    "diagnostic_context",
    "sensitivity_only",
    "blocked_source_or_method",
    "denominator_only",
    "not_applicable",
}

REGISTRY_FIELDS = [
    "family_id",
    "family_label",
    "demand_translation_low",
    "demand_translation_base",
    "demand_translation_high",
    "selected_use_rule",
    "blocked_use",
    "headline_selector_id",
]

OBJECT_ROLE_MATRIX_FIELDS = [
    "ledger_row_id",
    "surface_id",
    "period_object",
    "scenario_id",
    "source_channel_id",
    "channel_label",
    "object_role",
    "selected_n_inclusion",
    "selected_block_input",
    "source_object",
    "source_artifact",
    "inflow_kind",
    "stock_to_flow_rule",
    "recipient_basis",
    "demand_translation_family_id",
    "demand_translation_status",
    "materialization_or_pass_through_policy",
    "current_demand_conversion_policy",
    "rate_or_scenario_attribution_status",
    "flow_basis_status",
    "same_period_denominator_status",
    "overlap_status",
    "selection_gate_status",
    "promotion_requirements_remaining",
    "selected_historical_n_includes_tdc",
    "classifier_allowed",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DEMAND_TRANSLATION_LEDGER_FIELDS = [
    "demand_translation_ledger_row_id",
    "ledger_row_id",
    "period_object",
    "surface_id",
    "scenario_id",
    "source_channel_id",
    "object_role",
    "selected_n_inclusion",
    "support_formula",
    "source_flow_bil",
    "demand_translation_family_id",
    "demand_translation_low",
    "demand_translation_base",
    "demand_translation_high",
    "translated_support_low_bil",
    "translated_support_base_bil",
    "translated_support_high_bil",
    "selected_value_bil",
    "selected_d_bil",
    "selected_rw",
    "rate_or_scenario_attribution_status",
    "flow_basis_status",
    "demand_translation_status",
    "same_period_denominator_status",
    "overlap_status",
    "selection_gate_status",
    "central_n_delta_bil_allowed",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class DemandTranslationLedgerError(ValueError):
    """Raised when D9 registry or ledger rows violate the object contract."""


def load_registry(path: str | Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    """Load the demand-translation registry YAML."""

    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise DemandTranslationLedgerError("registry payload must be a mapping")
    return payload


def registry_rows(path: str | Path = DEFAULT_REGISTRY_PATH) -> list[dict[str, str]]:
    """Return normalized registry family rows."""

    payload = load_registry(path)
    selector = _clean(payload.get("demand_translation_strength", "base"))
    rows = [
        {
            "family_id": _clean(row.get("family_id")),
            "family_label": _clean(row.get("family_label")),
            "demand_translation_low": _decimal_text(row.get("demand_translation_low")),
            "demand_translation_base": _decimal_text(
                row.get("demand_translation_base")
            ),
            "demand_translation_high": _decimal_text(
                row.get("demand_translation_high")
            ),
            "selected_use_rule": _clean(row.get("selected_use_rule")),
            "blocked_use": _clean(row.get("blocked_use")),
            "headline_selector_id": "demand_translation_strength",
        }
        for row in payload.get("families", [])
    ]
    if selector not in {"weak", "base", "strong"}:
        raise DemandTranslationLedgerError(
            f"invalid demand_translation_strength: {selector}"
        )
    validate_registry(rows)
    return rows


def object_role_rows() -> list[dict[str, str]]:
    """Return D9 object-role rows without changing model values."""

    rows = [
        _object_row(
            "forecast_public_interest_net_block",
            "forecast_central_tdcsim_cbo",
            "forecast",
            "central_forecast",
            "public_interest_net_block",
            "Forecast public-interest net block",
            "selected_n",
            "true",
            "false",
            "tdcsim_cbo_public_interest_block",
            "var/preliminary_scenario_results/forecast_10y/ratewall_forecast_public_interest_net_block.csv",
            "cash_flow",
            "",
            "domestic_private_and_financial_recipients_after_absorbers",
            "direct_private_cash_income",
            "pass_block_level_assumption_mode_translation",
            "net_public_interest_after_fiscal_tga_tax_absorbers",
            "block_level_current_demand_conversion",
            "pass_scenario_rate_path_attributed",
            "pass_flow_basis",
            "pass_forecast_selected_D",
            "pass_public_interest_block_xor",
            "pass_selected_forecast_surface",
            "none",
            "false",
            "false",
            "selected_forecast_n",
            "direct_treasury_or_iorb_or_on_rrp_standalone_addition",
            "forecast_public_interest_block_no_double_count",
        ),
        _object_row(
            "forecast_tdc_ex_overlap_beta_chi",
            "forecast_central_tdcsim_cbo",
            "forecast",
            "central_forecast",
            "tdc_ex_overlap_beta_chi",
            "Forecast TDC ex-overlap beta-chi support",
            "selected_n",
            "true",
            "false",
            "tdcsim_cbo_forecast_suite",
            "var/preliminary_scenario_results/core_support_parity/ratewall_tdc_ex_overlap_support_shared.csv",
            "accounting_flow_chain",
            "",
            "deposit_recipients_after_beta_chi",
            "spendable_liquidity_inflow",
            "pass_selected_chi_translation",
            "tdc_change_ex_overlap_bil_times_beta_times_chi",
            "chi_current_demand_share",
            "pass_scenario_tdc_generated_by_rate_path",
            "pass_ex_overlap_flow_basis",
            "pass_forecast_selected_D",
            "pass_tdc_ex_overlap_only",
            "pass_selected_forecast_surface",
            "none",
            "false",
            "false",
            "selected_forecast_n",
            "tdc_full_bil;current_or_historical_tdc_promotion",
            "forecast_tdc_selected_only_ex_overlap_beta_chi",
        ),
        _object_row(
            "forecast_conventional_D",
            "forecast_central_tdcsim_cbo",
            "forecast",
            "central_forecast",
            "forecast_conventional_denominator",
            "Forecast selected conventional demand drag",
            "denominator_only",
            "false",
            "false",
            "forecast_denominator_parity",
            "var/preliminary_scenario_results/denominator_parity/ratewall_denominator_parity_bridge.csv",
            "denominator_drag",
            "",
            "not_applicable",
            "",
            "not_applicable_denominator",
            "selected_D_surface",
            "not_applicable",
            "pass_scenario_rate_path_attributed",
            "not_applicable_denominator",
            "pass_forecast_selected_D",
            "not_applicable_denominator",
            "pass_selected_denominator_surface",
            "none",
            "false",
            "false",
            "selected_forecast_D",
            "numerator_support",
            "denominator_only_not_numerator_channel",
        ),
        _object_row(
            "forecast_direct_treasury_interest_block_input",
            "forecast_central_tdcsim_cbo",
            "forecast",
            "central_forecast",
            "direct_treasury_interest",
            "Direct Treasury interest block input",
            "selected_block_input",
            "false",
            "true",
            "tdcsim_cbo_public_interest_block",
            "var/preliminary_scenario_results/core_support_parity/ratewall_public_interest_net_block_shared.csv",
            "cash_flow",
            "",
            "treasury_security_recipients",
            "direct_private_cash_income",
            "pass_inside_public_interest_block",
            "nonadditive_block_input",
            "inherited_from_public_interest_block",
            "pass_scenario_rate_path_attributed",
            "pass_flow_basis",
            "pass_forecast_selected_D",
            "pass_nonadditive_public_interest_block_input",
            "blocked_standalone_selected_n",
            "must_remain_inside_public_interest_net_block",
            "false",
            "false",
            "public_interest_block_decomposition",
            "standalone_addition_above_public_interest_net_block",
            "direct_treasury_xor_public_interest_block",
        ),
        _object_row(
            "forecast_bank_treasury_split_block_input",
            "forecast_central_tdcsim_cbo",
            "forecast",
            "central_forecast",
            "bank_treasury_interest_split",
            "Bank Treasury interest split block input",
            "selected_block_input",
            "false",
            "true",
            "tdcsim_cbo_public_interest_block",
            "var/preliminary_scenario_results/core_support_parity/ratewall_public_interest_net_block_shared.csv",
            "cash_flow",
            "",
            "bank_recipients_inside_block",
            "intermediated_financial_income",
            "pass_inside_public_interest_block",
            "nonadditive_block_input",
            "inherited_from_public_interest_block",
            "pass_scenario_rate_path_attributed",
            "pass_flow_basis",
            "pass_forecast_selected_D",
            "pass_nonadditive_public_interest_block_input",
            "blocked_standalone_selected_n",
            "must_remain_inside_public_interest_net_block",
            "false",
            "false",
            "public_interest_block_decomposition",
            "standalone_addition_above_public_interest_net_block",
            "bank_treasury_split_nonadditive",
        ),
        _object_row(
            "forecast_iorb_block_input",
            "forecast_central_tdcsim_cbo",
            "forecast",
            "central_forecast",
            "iorb",
            "IORB block input",
            "selected_block_input",
            "false",
            "true",
            "fed_liability_context",
            "var/preliminary_scenario_results/forecast_10y/ratewall_forecast_fed_liability_sources.csv",
            "cash_flow",
            "",
            "bank_reserve_recipients_inside_block",
            "intermediated_financial_income",
            "pass_inside_public_interest_block",
            "nonadditive_block_input",
            "inherited_from_public_interest_block",
            "pass_scenario_rate_path_attributed",
            "pass_flow_basis",
            "pass_forecast_selected_D",
            "pass_nonadditive_public_interest_block_input",
            "blocked_standalone_selected_n",
            "must_remain_inside_public_interest_net_block",
            "false",
            "false",
            "public_interest_block_decomposition",
            "standalone_iorb_addition_above_public_interest_net_block",
            "iorb_nonadditive_public_interest_input",
        ),
        _object_row(
            "forecast_on_rrp_mmf_route_block_input",
            "forecast_central_tdcsim_cbo",
            "forecast",
            "central_forecast",
            "on_rrp_mmf_route",
            "ON RRP/MMF route block input",
            "selected_block_input",
            "false",
            "true",
            "fed_liability_context",
            "var/preliminary_scenario_results/forecast_10y/ratewall_forecast_fed_liability_sources.csv",
            "cash_flow",
            "",
            "mmf_recipients_inside_block",
            "market_safe_yield_income",
            "pass_inside_public_interest_block",
            "mmf_route_0_97_metadata_not_beta_or_chi",
            "inherited_from_public_interest_block",
            "pass_scenario_rate_path_attributed",
            "pass_flow_basis",
            "pass_forecast_selected_D",
            "pass_nonadditive_public_interest_block_input",
            "blocked_standalone_selected_n",
            "must_remain_inside_public_interest_net_block",
            "false",
            "false",
            "public_interest_block_decomposition",
            "standalone_mmf_or_on_rrp_addition_above_public_interest_net_block",
            "on_rrp_mmf_nonadditive_public_interest_input",
        ),
        _object_row(
            "forecast_remittance_context",
            "forecast_central_tdcsim_cbo",
            "forecast",
            "central_forecast",
            "remittance_cash_flow_context",
            "Federal Reserve remittance baseline context",
            "diagnostic_context",
            "false",
            "false",
            "cbo_revenue_projection_federal_reserve_remittances",
            "data/raw/cbo/51138-2026-02-Revenue-annual_fy.csv",
            "public_cash_receipt_context",
            "",
            "not_private_recipient_demand",
            "",
            "blocked_no_private_demand_translation",
            "baseline_context_central_delta_zero",
            "not_applicable",
            "blocked_no_clean_scenario_delta_model",
            "pass_cash_receipt_context",
            "not_applicable_context",
            "pass_not_private_income_overlap_guard",
            "blocked_source_or_method",
            "scenario_delta_model_and_private_recipient_mapping_missing",
            "false",
            "false",
            "budget_context_only",
            "private_demand_support_without_delta_model",
            "remittance_context_not_selected_n",
        ),
        _object_row(
            "current_assumption_benchmark_2026",
            "current_assumption_runtime",
            "current",
            "current_assumption_benchmark",
            "current_assumption_benchmark_2026",
            "Selected current assumption benchmark",
            "selected_benchmark_recast",
            "true",
            "false",
            "ratewall_assumption_engine",
            "outputs/tables/ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv",
            "frozen_runtime_recast",
            "",
            "current_runtime_assumption_mode",
            "direct_private_cash_income",
            "pass_frozen_runtime_recast",
            "public_interest_plus_legacy_runtime_tdc",
            "frozen_benchmark_current_demand_conversion",
            "pass_frozen_runtime_assumption",
            "pass_frozen_runtime_flow_basis",
            "pass_current_fixed_D",
            "pass_frozen_benchmark_no_silent_replacement",
            "pass_selected_current_benchmark",
            "none",
            "false",
            "false",
            "selected_current_benchmark_recast",
            "r38_or_d1_hybrid_replacement",
            "current_selected_values_frozen",
        ),
        _object_row(
            "current_runtime_public_interest_benchmark_component",
            "current_assumption_runtime",
            "current",
            "current_assumption_benchmark",
            "current_runtime_public_interest_component",
            "Current runtime public-interest benchmark component",
            "selected_block_input",
            "false",
            "true",
            "ratewall_assumption_engine",
            "var/preliminary_scenario_results/current_observed_overlay/ratewall_current_observed_overlay_admission.csv",
            "cash_flow",
            "",
            "current_runtime_assumption_mode",
            "direct_private_cash_income",
            "pass_inside_frozen_current_benchmark",
            "frozen_current_component",
            "inherited_from_current_benchmark",
            "pass_frozen_runtime_assumption",
            "pass_flow_basis",
            "pass_current_fixed_D",
            "pass_current_benchmark_component_identity",
            "blocked_standalone_current_selected_row",
            "must_remain_inside_frozen_benchmark_recast",
            "false",
            "false",
            "current_benchmark_component",
            "standalone_selected_current_row",
            "current_public_interest_component_nonstandalone",
        ),
        _object_row(
            "current_runtime_legacy_tdc_benchmark_component",
            "current_assumption_runtime",
            "current",
            "current_assumption_benchmark",
            "current_runtime_legacy_tdc_component",
            "Legacy/runtime current TDC benchmark component",
            "selected_benchmark_recast",
            "false",
            "true",
            "ratewall_assumption_engine",
            "var/preliminary_scenario_results/current_observed_overlay/ratewall_current_observed_overlay_admission.csv",
            "frozen_runtime_component",
            "",
            "current_runtime_assumption_mode",
            "spendable_liquidity_inflow",
            "pass_only_inside_frozen_current_benchmark",
            "legacy_runtime_component_not_source_led_promotion",
            "inherited_from_current_benchmark",
            "pass_frozen_runtime_assumption",
            "pass_frozen_runtime_component",
            "pass_current_fixed_D",
            "pass_no_source_led_tdc_promotion",
            "blocked_standalone_current_selected_row",
            "must_remain_inside_frozen_benchmark_recast",
            "false",
            "false",
            "current_benchmark_component",
            "observed_source_led_current_tdc_promotion",
            "legacy_tdc_only_inside_current_benchmark",
        ),
        _object_row(
            "current_conventional_D",
            "current_assumption_runtime",
            "current",
            "current_assumption_benchmark",
            "current_conventional_denominator",
            "Current fixed conventional demand drag",
            "denominator_only",
            "false",
            "false",
            "ratewall_assumption_engine_denominator",
            "configs/ratewall_parameter_packs.yml",
            "denominator_drag",
            "",
            "not_applicable",
            "",
            "not_applicable_denominator",
            "current_fixed_D",
            "not_applicable",
            "pass_frozen_runtime_assumption",
            "not_applicable_denominator",
            "pass_current_fixed_D",
            "not_applicable_denominator",
            "pass_selected_current_denominator",
            "none",
            "false",
            "false",
            "selected_current_D",
            "numerator_support",
            "current_denominator_only_not_numerator_channel",
        ),
        _object_row(
            "current_r38_public_interest_candidate",
            "current_observed_overlay",
            "current",
            "r38_observed_candidate",
            "current_r38_public_interest_candidate",
            "R38 public-interest observed candidate",
            "candidate_replacement",
            "false",
            "false",
            "current_observed_overlay",
            "var/preliminary_scenario_results/current_observed_overlay/ratewall_current_observed_overlay_admission.csv",
            "cash_flow",
            "",
            "source_led_current_context",
            "direct_private_cash_income",
            "pass_candidate_translation_not_selection",
            "source_led_candidate_component",
            "candidate_current_demand_conversion",
            "pass_observed_current_context",
            "pass_flow_basis",
            "pass_current_fixed_D",
            "pass_component_overlap_identity",
            "blocked_replacement_surface_not_admitted",
            "owner_replacement_gate",
            "false",
            "false",
            "current_candidate_replacement",
            "selected_current_benchmark_replacement_without_owner_gate",
            "r38_nonselected_candidate",
        ),
        _object_row(
            "current_r38_tdc_beta_chi_candidate",
            "current_observed_overlay",
            "current",
            "r38_observed_candidate",
            "current_r38_tdc_beta_chi_candidate",
            "R38 beta-chi TDC candidate",
            "candidate_replacement",
            "false",
            "false",
            "current_observed_overlay",
            "var/preliminary_scenario_results/current_observed_overlay/ratewall_current_observed_overlay_admission.csv",
            "accounting_flow_chain",
            "",
            "source_led_current_context",
            "spendable_liquidity_inflow",
            "pass_candidate_chi_translation_not_selection",
            "tdc_change_ex_overlap_bil_times_beta_times_chi",
            "chi_current_demand_share",
            "pass_observed_current_context",
            "pass_ex_overlap_flow_basis",
            "pass_current_fixed_D",
            "pass_tdc_ex_overlap_only",
            "blocked_replacement_surface_not_admitted",
            "owner_replacement_gate",
            "false",
            "false",
            "current_candidate_replacement",
            "selected_current_benchmark_replacement_without_owner_gate",
            "r38_tdc_nonselected_candidate",
        ),
        _object_row(
            "current_d1_safe_yield_bounded_fallback",
            "realized_safe_yield_income",
            "current",
            "d1_bounded_fallback",
            "deposit_realized_safe_yield_fallback",
            "D1 safe-yield bounded fallback",
            "sensitivity_only",
            "false",
            "false",
            "fred_fdic_constructed_safe_yield_fallback",
            "var/preliminary_scenario_results/realized_safe_yield_income/ratewall_realized_safe_yield_bounded_sensitivity.csv",
            "constructed_flow_sensitivity",
            "stock_to_flow_paid_rate_rule",
            "household_private_deposit_proxy",
            "realized_household_safe_yield_income",
            "pass_bounded_sensitivity_translation",
            "constructed_stock_rate_flow_diagnostic",
            "bounded_sensitivity_current_demand_conversion",
            "blocked_payer_flow_source_panels_missing",
            "pass_constructed_flow_basis_for_sensitivity",
            "pass_current_fixed_D_context",
            "blocked_overlap_and_replacement_gates",
            "blocked_central_admission",
            "ffiec_fdic_ncua_payer_flow_and_owner_gate",
            "false",
            "false",
            "bounded_sensitivity_only",
            "central_current_addition;stock_rate_fallback_headline",
            "d1_noncentral_until_all_gates_pass",
        ),
        _object_row(
            "historical_public_interest_context",
            "historical_path_context",
            "historical",
            "historical_context",
            "historical_public_interest_context",
            "Historical public-interest context",
            "diagnostic_context",
            "false",
            "false",
            "historical_public_finance_sources",
            "var/preliminary_scenario_results/historical_provisional_estimate/ratewall_historical_public_interest_net_block.csv",
            "cash_flow",
            "",
            "historical_public_interest_context",
            "direct_private_cash_income",
            "pass_context_translation_not_classifier",
            "historical_public_interest_context_only",
            "context_current_demand_conversion",
            "pass_historical_rate_context",
            "pass_flow_basis",
            "pass_same_quarter_context_D",
            "pass_public_interest_subchannel_guard",
            "blocked_final_classifier",
            "final_classifier_closed_nonclassifier",
            "false",
            "false",
            "historical_context_only",
            "final_wall_hit_classifier;selected_historical_n",
            "historical_public_interest_nonclassifier",
        ),
        _object_row(
            "historical_tdc_mechanism_context",
            "historical_path_context",
            "historical",
            "historical_context",
            "historical_tdc_mechanism_context",
            "Historical TDC mechanism context",
            "diagnostic_context",
            "false",
            "false",
            "historical_tdc_context_adapter",
            "var/preliminary_scenario_results/historical_provisional_estimate/ratewall_historical_provisional_numerator_ledger.csv",
            "accounting_flow_context",
            "",
            "historical_mechanism_context",
            "spendable_liquidity_inflow",
            "pass_context_translation_not_classifier",
            "tdc_ex_overlap_support_bil_plus_public_interest_net_block_partial_bil",
            "context_current_demand_conversion",
            "pass_historical_context",
            "pass_context_flow_basis",
            "pass_same_quarter_context_D",
            "pass_direct_treasury_inside_public_interest_context",
            "blocked_final_classifier",
            "selected_historical_tdc_gate_closed",
            "false",
            "false",
            "historical_tdc_mechanism_context",
            "selected_historical_n;direct_treasury_third_additive_term",
            "historical_tdc_nonclassifier_decomposition",
        ),
        _object_row(
            "historical_direct_treasury_decomposition",
            "historical_path_context",
            "historical",
            "historical_context",
            "historical_direct_treasury_interest_decomposition",
            "Historical direct Treasury decomposition",
            "selected_block_input",
            "false",
            "true",
            "historical_public_finance_sources",
            "var/preliminary_scenario_results/historical_provisional_estimate/ratewall_historical_public_interest_net_block.csv",
            "cash_flow",
            "",
            "historical_public_interest_context",
            "direct_private_cash_income",
            "pass_inside_public_interest_context",
            "nonadditive_decomposition_term",
            "inherited_from_historical_public_interest_context",
            "pass_historical_context",
            "pass_flow_basis",
            "pass_same_quarter_context_D",
            "pass_nonadditive_public_interest_context",
            "blocked_standalone_historical_selected_n",
            "must_remain_inside_public_interest_context",
            "false",
            "false",
            "historical_decomposition_only",
            "third_additive_term_in_historical_tdc_mechanism",
            "historical_direct_treasury_nonadditive",
        ),
        _object_row(
            "historical_conventional_D_context",
            "historical_path_context",
            "historical",
            "historical_context",
            "historical_denominator",
            "Historical conventional demand drag context",
            "denominator_only",
            "false",
            "false",
            "historical_denominator_source_panel",
            "var/preliminary_scenario_results/historical_provisional_estimate/ratewall_historical_provisional_denominator_panel.csv",
            "denominator_drag",
            "",
            "not_applicable",
            "",
            "not_applicable_denominator",
            "historical_context_D",
            "not_applicable",
            "pass_historical_context",
            "not_applicable_denominator",
            "pass_same_quarter_context_D",
            "not_applicable_denominator",
            "blocked_final_classifier",
            "final_classifier_closed_nonclassifier",
            "false",
            "false",
            "historical_denominator_context",
            "final_wall_hit_classifier",
            "historical_denominator_nonclassifier_context",
        ),
        _object_row(
            "historical_remittance_cash_flow_context",
            "historical_path_context",
            "historical",
            "historical_context",
            "historical_remittance_cash_flow_context",
            "Historical remittance cash-flow context",
            "diagnostic_context",
            "false",
            "false",
            "mts_table4_or_fiscaldata_remittance_cash_flow",
            "source_to_acquire",
            "public_cash_receipt_context",
            "",
            "not_private_recipient_demand",
            "",
            "blocked_no_private_demand_translation",
            "cash_flow_context_not_private_demand_support",
            "not_applicable",
            "blocked_source_to_acquire",
            "blocked_source_to_acquire",
            "not_applicable_context",
            "pass_remittance_not_private_income_overlap_guard",
            "blocked_source_or_method",
            "MTS_or_FiscalData_cash_flow_context_required",
            "false",
            "false",
            "historical_context_only",
            "private_demand_support_without_recipient_mapping",
            "remittance_context_not_selected_n",
        ),
        _object_row(
            "deposit_realized_safe_yield_required_theory",
            "realized_safe_yield_income",
            "current",
            "d1_required_theory",
            "deposit_realized_safe_yield",
            "Deposit realized safe-yield required theory",
            "blocked_source_or_method",
            "false",
            "false",
            "ffiec_fdic_ncua_payer_flow_panels",
            "FFIEC/FDIC RIAD4508+RIAD0093+RIADHK03+RIADHK04;NCUA 380+381",
            "payer_flow_required",
            "",
            "deposit_recipients",
            "realized_household_safe_yield_income",
            "blocked_until_payer_flow_and_recipient_gates",
            "payer_flow_required_not_stock_rate_fallback",
            "requires_approved_current_demand_conversion",
            "blocked_source_panels_missing",
            "blocked_payer_flow_source_panels_missing",
            "blocked_same_period_D_until_source_panels",
            "blocked_overlap_and_replacement_gates",
            "blocked_central_admission",
            "source_panels_recipient_tax_demand_D_overlap_replacement_owner",
            "false",
            "false",
            "theoretical_required_source_blocked",
            "stock_rate_fallback_headline;bea_personal_interest_substitution",
            "deposit_safe_yield_required_but_noncentral",
        ),
        _object_row(
            "mmf_realized_safe_yield_diagnostic",
            "realized_safe_yield_income",
            "current",
            "d1_required_theory",
            "mmf_realized_safe_yield",
            "MMF realized safe-yield diagnostic",
            "diagnostic_context",
            "false",
            "false",
            "SEC_N_MFP_OFR_ICI",
            "source_to_acquire",
            "payer_flow_or_distribution_context",
            "",
            "mmf_recipients",
            "market_safe_yield_income",
            "blocked_until_recipient_and_overlap_gates",
            "diagnostic_noncentral",
            "requires_approved_current_demand_conversion",
            "blocked_source_panels_missing",
            "blocked_source_to_acquire",
            "blocked_same_period_D_until_source_panels",
            "blocked_overlap_gates",
            "blocked_central_admission",
            "MMF_source_recipient_overlap_owner_gates",
            "false",
            "false",
            "diagnostic_context_only",
            "additive_row_above_public_interest_or_safe_yield",
            "mmf_safe_yield_noncentral_diagnostic",
        ),
        _object_row(
            "tbill_realized_safe_yield_diagnostic",
            "realized_safe_yield_income",
            "current",
            "d1_required_theory",
            "tbill_realized_safe_yield",
            "T-bill realized safe-yield diagnostic",
            "diagnostic_context",
            "false",
            "false",
            "Treasury_FiscalData_H15_Z1_DFA_WAMEST",
            "source_to_acquire",
            "payer_flow_or_distribution_context",
            "",
            "t_bill_recipients",
            "market_safe_yield_income",
            "blocked_until_recipient_and_overlap_gates",
            "diagnostic_noncentral",
            "requires_approved_current_demand_conversion",
            "blocked_source_panels_missing",
            "blocked_source_to_acquire",
            "blocked_same_period_D_until_source_panels",
            "blocked_overlap_gates",
            "blocked_central_admission",
            "T_bill_source_recipient_overlap_owner_gates",
            "false",
            "false",
            "diagnostic_context_only",
            "additive_row_above_public_interest_or_safe_yield",
            "tbill_safe_yield_noncentral_diagnostic",
        ),
        _object_row(
            "safe_asset_allocation_drag_sidecar",
            "forecast_sensitivity_tdcsim_cbo",
            "forecast",
            "safe_asset_drag_sidecar",
            "safe_asset_allocation_drag",
            "Safe-asset allocation drag sidecar",
            "denominator_only",
            "false",
            "false",
            "residual_safe_asset_gate",
            "var/preliminary_scenario_results/residual_channel_closure/ratewall_residual_safe_asset_drag_admission_gate.csv",
            "denominator_or_disjoint_basis_context",
            "",
            "not_applicable",
            "market_safe_yield_income",
            "blocked_same_basis_overlap",
            "central_n_delta_zero_until_disjoint_basis",
            "not_applicable",
            "blocked_disjoint_basis_missing",
            "blocked_same_basis_overlap",
            "not_applicable_denominator_sidecar",
            "blocked_overlaps_public_interest_tdc_safe_yield_or_moving_D",
            "blocked_source_or_method",
            "disjoint_stock_convenience_yield_basis_required",
            "false",
            "false",
            "denominator_sidecar_only",
            "same_basis_safe_asset_offset_on_top_of_recipient_channels",
            "safe_asset_drag_nonadditive_sidecar",
        ),
        _object_row(
            "firm_cash_attenuation_sensitivity",
            "forecast_sensitivity_tdcsim_cbo",
            "forecast",
            "firm_sensitivity",
            "firm_cash_attenuation",
            "Firm cash attenuation sensitivity",
            "sensitivity_only",
            "false",
            "false",
            "firm_liquid_asset_stock_context",
            "var/preliminary_scenario_results/residual_channel_closure/ratewall_residual_channel_admission_matrix.csv",
            "stock_context_with_assumption_conversion",
            "stock_times_rate_path_yield_basis",
            "firm_sector_context",
            "firm_liquidity_cushion",
            "pass_sensitivity_translation_not_selected",
            "firm_cash_rate_path_yield_basis_bil_times_attenuation",
            "sensitivity_conversion_only",
            "pass_forecast_sensitivity_context",
            "pass_assumption_flow_conversion_for_sensitivity",
            "not_applicable_sensitivity",
            "pass_not_selected_overlap_guard",
            "blocked_selected_surface",
            "owner_selected_surface_and_overlap_proof",
            "false",
            "false",
            "forecast_sensitivity_only",
            "selected_forecast_n;firm_liquidity_cushion_stack",
            "firm_cash_sensitivity_not_selected",
        ),
        _object_row(
            "firm_liquid_asset_cushion_replacement",
            "forecast_sensitivity_tdcsim_cbo",
            "forecast",
            "firm_replacement",
            "firm_liquid_asset_cushion",
            "Firm liquid-asset cushion replacement candidate",
            "candidate_replacement",
            "false",
            "false",
            "firm_liquid_asset_stock_context",
            "var/preliminary_scenario_results/residual_channel_closure/ratewall_firm_liquidity_replacement_decision.csv",
            "stock_context_with_replacement_rule",
            "replacement_only_stock_to_flow_required",
            "firm_sector_context",
            "firm_liquidity_cushion",
            "pass_replacement_translation_not_selected",
            "replacement_candidate_only_not_additive",
            "replacement_conversion_only",
            "pass_forecast_replacement_context",
            "blocked_replacement_flow_basis_missing",
            "not_applicable_replacement",
            "blocked_cannot_stack_with_firm_cash",
            "blocked_selected_surface",
            "demote_firm_cash_then_owner_selected_surface",
            "false",
            "false",
            "replacement_candidate_only",
            "selected_forecast_n;firm_cash_stack",
            "firm_liquidity_replacement_not_additive",
        ),
        _object_row(
            "firm_rollover_pressure_credit_sidecar",
            "research_appendix",
            "current",
            "credit_sidecar",
            "firm_rollover_pressure",
            "Firm rollover pressure credit sidecar",
            "denominator_only",
            "false",
            "false",
            "firm_credit_sidecar_candidate",
            "configs/ratewall_parameter_packs.yml",
            "credit_denominator_context",
            "",
            "firm_sector_context",
            "wealth_revaluation",
            "blocked_not_numerator_translation",
            "denominator_or_credit_sidecar_only",
            "not_applicable",
            "blocked_no_selected_n_surface",
            "blocked_not_numerator_flow",
            "not_applicable_denominator_sidecar",
            "blocked_denominator_drag_not_numerator",
            "blocked_source_or_method",
            "maturing_debt_stock_reset_wedge_activity_response_required",
            "false",
            "false",
            "denominator_credit_sidecar_only",
            "numerator_demand_support",
            "firm_rollover_not_numerator",
        ),
        _object_row(
            "zero_low_apr_credit_diagnostic",
            "research_appendix",
            "current",
            "credit_sidecar",
            "zero_low_apr_credit_insulation",
            "Zero/low-APR credit insulation diagnostic",
            "diagnostic_context",
            "false",
            "false",
            "zero_low_apr_product_screen",
            "var/preliminary_scenario_results/forecast_10y/ratewall_forecast_zero_low_apr_credit_materiality.csv",
            "credit_stock_context",
            "stock_duration_wedge_pass_through_rule_required",
            "household_credit_recipients",
            "intermediated_financial_income",
            "blocked_until_stock_duration_wedge_pass_through_materiality",
            "product_stock_screen_not_support",
            "diagnostic_conversion_only",
            "blocked_source_path_incomplete",
            "blocked_stock_duration_path_missing",
            "not_applicable_diagnostic",
            "blocked_materiality_and_overlap_gates",
            "blocked_source_or_method",
            "stock_duration_wedge_pass_through_materiality_required",
            "false",
            "false",
            "diagnostic_context_only",
            "selected_current_n;originations_only_shortcut",
            "zero_low_apr_noncentral_diagnostic",
        ),
        _object_row(
            "tax_timing_leakage_adjustment",
            "cross_surface_adjustment",
            "current",
            "adjustment_handle",
            "tax_timing_leakage",
            "Tax/timing leakage adjustment",
            "not_applicable",
            "false",
            "false",
            "assumption_parameter_pack",
            "configs/ratewall_parameter_packs.yml",
            "adjustment_handle",
            "",
            "recipient_specific",
            "",
            "not_a_standalone_demand_translation",
            "adjustment_to_channel_flow_after_source_gate",
            "not_applicable",
            "not_applicable_adjustment",
            "not_applicable_adjustment",
            "surface_specific_D_required",
            "not_applicable_adjustment",
            "not_applicable_adjustment",
            "must_attach_to_admitted_channel",
            "false",
            "false",
            "adjustment_handle_only",
            "standalone_numerator_channel",
            "tax_timing_not_channel",
        ),
        _object_row(
            "distribution_recipient_basis_adjustment",
            "cross_surface_adjustment",
            "current",
            "adjustment_handle",
            "recipient_distribution",
            "Recipient distribution adjustment",
            "not_applicable",
            "false",
            "false",
            "source_specific_recipient_panel",
            "source_to_acquire",
            "adjustment_handle",
            "",
            "recipient_specific",
            "",
            "not_a_standalone_demand_translation",
            "adjustment_to_channel_flow_after_source_gate",
            "not_applicable",
            "not_applicable_adjustment",
            "not_applicable_adjustment",
            "surface_specific_D_required",
            "not_applicable_adjustment",
            "not_applicable_adjustment",
            "must_attach_to_admitted_channel",
            "false",
            "false",
            "adjustment_handle_only",
            "standalone_numerator_channel",
            "recipient_distribution_not_channel",
        ),
    ]
    validate_object_role_matrix(rows)
    return rows


def demand_translation_rows(
    *,
    registry: Sequence[Mapping[str, str]] | None = None,
    object_rows: Sequence[Mapping[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Return ledger rows combining object roles with registry family values."""

    registry_rows_ = list(registry) if registry is not None else registry_rows()
    object_rows_ = list(object_rows) if object_rows is not None else object_role_rows()
    validate_registry(registry_rows_)
    validate_object_role_matrix(object_rows_)
    family_by_id = {row["family_id"]: row for row in registry_rows_}
    rows: list[dict[str, str]] = []
    for row in object_rows_:
        family = family_by_id.get(row["demand_translation_family_id"], {})
        support = _support_fields(row["ledger_row_id"])
        rows.append(
            {
                "demand_translation_ledger_row_id": (
                    f"demand_translation_ledger::{row['ledger_row_id']}"
                ),
                "ledger_row_id": row["ledger_row_id"],
                "period_object": row["period_object"],
                "surface_id": row["surface_id"],
                "scenario_id": row["scenario_id"],
                "source_channel_id": row["source_channel_id"],
                "object_role": row["object_role"],
                "selected_n_inclusion": row["selected_n_inclusion"],
                "support_formula": support["support_formula"],
                "source_flow_bil": support["source_flow_bil"],
                "demand_translation_family_id": row["demand_translation_family_id"],
                "demand_translation_low": family.get("demand_translation_low", ""),
                "demand_translation_base": family.get("demand_translation_base", ""),
                "demand_translation_high": family.get("demand_translation_high", ""),
                "translated_support_low_bil": support["translated_support_low_bil"],
                "translated_support_base_bil": support["translated_support_base_bil"],
                "translated_support_high_bil": support["translated_support_high_bil"],
                "selected_value_bil": support["selected_value_bil"],
                "selected_d_bil": support["selected_d_bil"],
                "selected_rw": support["selected_rw"],
                "rate_or_scenario_attribution_status": row[
                    "rate_or_scenario_attribution_status"
                ],
                "flow_basis_status": row["flow_basis_status"],
                "demand_translation_status": row["demand_translation_status"],
                "same_period_denominator_status": row[
                    "same_period_denominator_status"
                ],
                "overlap_status": row["overlap_status"],
                "selection_gate_status": row["selection_gate_status"],
                "central_n_delta_bil_allowed": _central_allowed(row),
                "allowed_use": row["allowed_use"],
                "blocked_use": row["blocked_use"],
                "claim_boundary": row["claim_boundary"],
            }
        )
    validate_demand_translation_ledger(rows)
    return rows


def build_all(
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, list[dict[str, str]]]:
    """Return all D9 tables."""

    registry = registry_rows(registry_path)
    object_rows_ = object_role_rows()
    ledger = demand_translation_rows(registry=registry, object_rows=object_rows_)
    return {
        "registry_rows": registry,
        "object_role_rows": object_rows_,
        "demand_translation_rows": ledger,
    }


def write_demand_translation_outputs(
    output_dir: str | Path,
    *,
    registry_rows: Sequence[Mapping[str, str]],
    object_role_rows: Sequence[Mapping[str, str]],
    demand_translation_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write D9 demand-translation outputs."""

    validate_registry(registry_rows)
    validate_object_role_matrix(object_role_rows)
    validate_demand_translation_ledger(demand_translation_rows)
    root = Path(output_dir)
    outputs = {
        "object_role_matrix_csv": root / "ratewall_object_role_matrix.csv",
        "registry_csv": root / "ratewall_demand_translation_registry.csv",
        "ledger_csv": root / "ratewall_demand_translation_ledger.csv",
    }
    write_rows(outputs["registry_csv"], list(registry_rows), REGISTRY_FIELDS)
    write_rows(
        outputs["object_role_matrix_csv"],
        list(object_role_rows),
        OBJECT_ROLE_MATRIX_FIELDS,
    )
    write_rows(
        outputs["ledger_csv"],
        list(demand_translation_rows),
        DEMAND_TRANSLATION_LEDGER_FIELDS,
    )
    return outputs


def validate_registry(rows: Sequence[Mapping[str, str]]) -> None:
    """Validate exact approved demand-translation families."""

    if not rows:
        raise DemandTranslationLedgerError("registry is empty")
    by_id = {row["family_id"]: row for row in rows}
    if set(by_id) != set(APPROVED_REGISTRY):
        raise DemandTranslationLedgerError(
            f"registry family mismatch: {sorted(set(by_id) ^ set(APPROVED_REGISTRY))}"
        )
    for family_id, expected in APPROVED_REGISTRY.items():
        row = by_id[family_id]
        got = (
            row["demand_translation_low"],
            row["demand_translation_base"],
            row["demand_translation_high"],
        )
        if got != expected:
            raise DemandTranslationLedgerError(
                f"bad vector for {family_id}: expected {expected}, got {got}"
            )
        if row["headline_selector_id"] != "demand_translation_strength":
            raise DemandTranslationLedgerError(
                f"bad headline selector for {family_id}"
            )
    if any("mpc" in row["family_id"].lower() for row in rows):
        raise DemandTranslationLedgerError("generic MPC registry family is forbidden")


def validate_object_role_matrix(rows: Sequence[Mapping[str, str]]) -> None:
    """Validate D9 object-role rows."""

    if not rows:
        raise DemandTranslationLedgerError("object-role matrix is empty")
    seen: set[str] = set()
    selected_current = []
    required = {
        "forecast_public_interest_net_block",
        "forecast_tdc_ex_overlap_beta_chi",
        "forecast_conventional_D",
        "current_assumption_benchmark_2026",
        "current_runtime_public_interest_benchmark_component",
        "current_runtime_legacy_tdc_benchmark_component",
        "current_conventional_D",
        "current_r38_public_interest_candidate",
        "current_r38_tdc_beta_chi_candidate",
        "current_d1_safe_yield_bounded_fallback",
        "historical_public_interest_context",
        "historical_tdc_mechanism_context",
        "historical_direct_treasury_decomposition",
        "historical_conventional_D_context",
        "deposit_realized_safe_yield_required_theory",
        "mmf_realized_safe_yield_diagnostic",
        "tbill_realized_safe_yield_diagnostic",
        "safe_asset_allocation_drag_sidecar",
        "firm_cash_attenuation_sensitivity",
        "firm_liquid_asset_cushion_replacement",
        "firm_rollover_pressure_credit_sidecar",
        "zero_low_apr_credit_diagnostic",
    }
    by_id = {row["ledger_row_id"]: row for row in rows}
    missing = required - set(by_id)
    if missing:
        raise DemandTranslationLedgerError(
            f"missing required object-role rows: {sorted(missing)}"
        )
    for row in rows:
        row_id = row["ledger_row_id"]
        if row_id in seen:
            raise DemandTranslationLedgerError(f"duplicate ledger_row_id: {row_id}")
        seen.add(row_id)
        if row["object_role"] not in ALLOWED_OBJECT_ROLES:
            raise DemandTranslationLedgerError(
                f"invalid object_role for {row_id}: {row['object_role']}"
            )
        if row["period_object"] not in {"forecast", "current", "historical"}:
            raise DemandTranslationLedgerError(
                f"invalid period_object for {row_id}: {row['period_object']}"
            )
        for flag in [
            "selected_n_inclusion",
            "selected_block_input",
            "selected_historical_n_includes_tdc",
            "classifier_allowed",
        ]:
            if row[flag] not in {"true", "false"}:
                raise DemandTranslationLedgerError(f"bad boolean {flag} for {row_id}")
        if row["selected_n_inclusion"] == "true":
            _require_pass(row_id, row, "rate_or_scenario_attribution_status")
            _require_pass(row_id, row, "flow_basis_status")
            _require_pass(row_id, row, "same_period_denominator_status")
            _require_pass(row_id, row, "overlap_status")
            _require_pass(row_id, row, "selection_gate_status")
            if row["period_object"] == "current":
                selected_current.append(row_id)
        if (
            row["period_object"] == "historical"
            and row["selected_historical_n_includes_tdc"] != "false"
        ):
            raise DemandTranslationLedgerError(
                f"historical TDC selected inclusion is forbidden: {row_id}"
            )
        if row["period_object"] == "historical" and row["classifier_allowed"] != "false":
            raise DemandTranslationLedgerError(
                f"historical classifier is forbidden: {row_id}"
            )
        if "direct_treasury" in row["source_channel_id"] and row[
            "selected_n_inclusion"
        ] == "true":
            raise DemandTranslationLedgerError(
                f"direct Treasury cannot be standalone selected N: {row_id}"
            )
        if row["demand_translation_family_id"] == "wealth_revaluation" and row[
            "selected_n_inclusion"
        ] == "true":
            raise DemandTranslationLedgerError(
                f"wealth revaluation cannot be selected demand support: {row_id}"
            )
        if row["source_channel_id"] == "safe_asset_allocation_drag" and row[
            "selected_n_inclusion"
        ] == "true":
            raise DemandTranslationLedgerError(
                "safe-asset allocation drag cannot be selected N"
            )
        if (
            row["selected_n_inclusion"] == "true"
            and row["inflow_kind"].startswith("stock")
        ):
            raise DemandTranslationLedgerError(
                f"selected demand support cannot be stock-only: {row_id}"
            )
    if selected_current != ["current_assumption_benchmark_2026"]:
        raise DemandTranslationLedgerError(
            f"exactly one selected current row required, got {selected_current}"
        )


def validate_demand_translation_ledger(rows: Sequence[Mapping[str, str]]) -> None:
    """Validate ledger formulas and recast values."""

    if not rows:
        raise DemandTranslationLedgerError("demand-translation ledger is empty")
    by_id = {row["ledger_row_id"]: row for row in rows}
    selected = by_id["current_assumption_benchmark_2026"]
    if (
        selected["selected_value_bil"] != "83.542224868775"
        or selected["selected_d_bil"] != "247.55956656"
        or selected["selected_rw"] != "0.337463124652"
    ):
        raise DemandTranslationLedgerError("selected current benchmark drifted")
    for row in rows:
        row_id = row["ledger_row_id"]
        formula = row["support_formula"]
        if row["selected_n_inclusion"] == "true" and "tdc_full_bil" in formula:
            raise DemandTranslationLedgerError(
                f"selected TDC formula uses full TDC value: {row_id}"
            )
        if row["selected_n_inclusion"] == "true" and "tdc" in row[
            "source_channel_id"
        ] and "tdc_change_ex_overlap_bil" not in formula:
            raise DemandTranslationLedgerError(
                f"selected TDC formula must use ex-overlap TDC: {row_id}"
            )
        if row_id == "historical_tdc_mechanism_context" and (
            "direct_treasury" in formula
            or formula
            != "tdc_ex_overlap_support_bil + public_interest_net_block_partial_bil"
        ):
            raise DemandTranslationLedgerError(
                "historical TDC mechanism formula must not add direct Treasury"
            )
        if row["demand_translation_family_id"] == "wealth_revaluation" and any(
            row[field]
            for field in [
                "translated_support_low_bil",
                "translated_support_base_bil",
                "translated_support_high_bil",
                "selected_value_bil",
            ]
        ):
            raise DemandTranslationLedgerError(
                f"wealth revaluation cannot create demand support: {row_id}"
            )
        if row["source_channel_id"] == "safe_asset_allocation_drag" and row[
            "central_n_delta_bil_allowed"
        ] == "true":
            raise DemandTranslationLedgerError(
                "safe-asset allocation drag cannot have central N delta"
            )
        if (
            row["selected_n_inclusion"] == "true"
            and row["flow_basis_status"].startswith("pass") is False
        ):
            raise DemandTranslationLedgerError(
                f"selected row lacks flow basis: {row_id}"
            )
    central_allowed_by_role = Counter(
        row["object_role"]
        for row in rows
        if row["central_n_delta_bil_allowed"] == "true"
    )
    if central_allowed_by_role["selected_n"] != 2:
        raise DemandTranslationLedgerError(
            "only selected forecast N rows should have central N delta allowed"
        )


def _object_row(
    ledger_row_id: str,
    surface_id: str,
    period_object: str,
    scenario_id: str,
    source_channel_id: str,
    channel_label: str,
    object_role: str,
    selected_n_inclusion: str,
    selected_block_input: str,
    source_object: str,
    source_artifact: str,
    inflow_kind: str,
    stock_to_flow_rule: str,
    recipient_basis: str,
    demand_translation_family_id: str,
    demand_translation_status: str,
    materialization_or_pass_through_policy: str,
    current_demand_conversion_policy: str,
    rate_or_scenario_attribution_status: str,
    flow_basis_status: str,
    same_period_denominator_status: str,
    overlap_status: str,
    selection_gate_status: str,
    promotion_requirements_remaining: str,
    selected_historical_n_includes_tdc: str,
    classifier_allowed: str,
    allowed_use: str,
    blocked_use: str,
    claim_boundary: str,
) -> dict[str, str]:
    return {
        "ledger_row_id": ledger_row_id,
        "surface_id": surface_id,
        "period_object": period_object,
        "scenario_id": scenario_id,
        "source_channel_id": source_channel_id,
        "channel_label": channel_label,
        "object_role": object_role,
        "selected_n_inclusion": selected_n_inclusion,
        "selected_block_input": selected_block_input,
        "source_object": source_object,
        "source_artifact": source_artifact,
        "inflow_kind": inflow_kind,
        "stock_to_flow_rule": stock_to_flow_rule,
        "recipient_basis": recipient_basis,
        "demand_translation_family_id": demand_translation_family_id,
        "demand_translation_status": demand_translation_status,
        "materialization_or_pass_through_policy": (
            materialization_or_pass_through_policy
        ),
        "current_demand_conversion_policy": current_demand_conversion_policy,
        "rate_or_scenario_attribution_status": rate_or_scenario_attribution_status,
        "flow_basis_status": flow_basis_status,
        "same_period_denominator_status": same_period_denominator_status,
        "overlap_status": overlap_status,
        "selection_gate_status": selection_gate_status,
        "promotion_requirements_remaining": promotion_requirements_remaining,
        "selected_historical_n_includes_tdc": selected_historical_n_includes_tdc,
        "classifier_allowed": classifier_allowed,
        "allowed_use": allowed_use,
        "blocked_use": blocked_use,
        "claim_boundary": claim_boundary,
    }


def _support_fields(row_id: str) -> dict[str, str]:
    support_by_id = {
        "forecast_public_interest_net_block": {
            "support_formula": "public_interest_net_block",
            "central_n_delta_bil_allowed": "true",
        },
        "forecast_tdc_ex_overlap_beta_chi": {
            "support_formula": "tdc_change_ex_overlap_bil * beta * chi",
            "central_n_delta_bil_allowed": "true",
        },
        "current_assumption_benchmark_2026": {
            "support_formula": "current_runtime_public_interest_component + current_runtime_legacy_tdc_component",
            "source_flow_bil": "83.542224868775",
            "selected_value_bil": "83.542224868775",
            "selected_d_bil": "247.55956656",
            "selected_rw": "0.337463124652",
        },
        "current_runtime_public_interest_benchmark_component": {
            "support_formula": "frozen_current_public_interest_component",
            "selected_value_bil": "56.03251655775289810515522913",
        },
        "current_runtime_legacy_tdc_benchmark_component": {
            "support_formula": "legacy_runtime_tdc_component_inside_frozen_benchmark",
            "selected_value_bil": "27.50970831102218887944538608",
        },
        "current_conventional_D": {
            "support_formula": "current_fixed_D",
            "selected_d_bil": "247.55956656",
        },
        "current_r38_tdc_beta_chi_candidate": {
            "support_formula": "tdc_change_ex_overlap_bil * beta * chi",
            "selected_value_bil": "19.25679581771553221561177026",
        },
        "current_r38_public_interest_candidate": {
            "support_formula": "R38_public_interest_candidate_component",
            "selected_value_bil": "56.03251655775289810515522913",
        },
        "current_d1_safe_yield_bounded_fallback": {
            "support_formula": "bounded_safe_yield_sensitivity_only;central_delta=0",
            "translated_support_base_bil": "0",
            "selected_value_bil": "0",
        },
        "historical_public_interest_context": {
            "support_formula": "historical_public_interest_net_block_partial_bil",
        },
        "historical_tdc_mechanism_context": {
            "support_formula": "tdc_ex_overlap_support_bil + public_interest_net_block_partial_bil",
        },
        "historical_conventional_D_context": {
            "support_formula": "historical_context_D",
        },
        "safe_asset_allocation_drag_sidecar": {
            "support_formula": "central_n_delta_bil=0_until_disjoint_basis",
        },
        "firm_rollover_pressure_credit_sidecar": {
            "support_formula": "",
        },
    }
    base = {
        "support_formula": "",
        "source_flow_bil": "",
        "translated_support_low_bil": "",
        "translated_support_base_bil": "",
        "translated_support_high_bil": "",
        "selected_value_bil": "",
        "selected_d_bil": "",
        "selected_rw": "",
        "central_n_delta_bil_allowed": "false",
    }
    base.update(support_by_id.get(row_id, {}))
    return base


def _central_allowed(row: Mapping[str, str]) -> str:
    return _support_fields(row["ledger_row_id"])["central_n_delta_bil_allowed"]


def _require_pass(row_id: str, row: Mapping[str, str], field: str) -> None:
    if not row[field].startswith("pass"):
        raise DemandTranslationLedgerError(
            f"selected row {row_id} lacks passing {field}: {row[field]}"
        )


def _clean(value: object) -> str:
    return "" if value is None else str(value)


def _decimal_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if "." not in text:
        return text
    return f"{float(text):.2f}"
