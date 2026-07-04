"""Speculative RateWall assumption-mode solver."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import yaml

from ratewall.accounting.numbers import NumberLike, require_nonnegative, to_decimal


SPLIT_DENOMINATOR_ROBUSTNESS_CLAIM_BOUNDARY = (
    "split_denominator_robustness_lane_non_load_bearing_for_headline_hit_verdict_"
    "assumption_mode_not_empirical_estimate"
)
SPLIT_DENOMINATOR_ROBUSTNESS_ALLOWED_USE = "robustness_decomposition_only"
SPLIT_DENOMINATOR_ROBUSTNESS_BLOCKED_USE = (
    "headline_hit_verdict;canonical_rw_y;evidence_mode"
)
CONVENTIONAL_DRAG_DECOMPOSITION_STATUS = (
    "fixed_total_denominator_allocation_not_incremental_drag"
)
CONVENTIONAL_DRAG_COMPONENT_VALUE_BASIS = (
    "split_denominator_robustness_value_not_headline_denominator_addition"
)
CONVENTIONAL_DRAG_COMPONENT_EVIDENCE_STATUS = (
    "assumption_mode_share_not_independently_estimated_component"
)
TDSP_BORROWING_COST_DIAGNOSTIC_LENS_ROLE = (
    "tdsp_current_demand_diagnostic_lens_candidate_for_household_debt_service_"
    "subcomponent"
)
TDSP_BORROWING_COST_OVERLAP_RULE = (
    "tdsp_may_only_reallocate_or_decompose_existing_borrowing_cost_drag_not_add_"
    "to_denominator"
)
DENOMINATOR_REPLACEMENT_RESEARCH_STATUS = (
    "blocked_requires_source_backed_replacement_or_reallocation_design"
)
DENOMINATOR_REPLACEMENT_MAIN_RATIO_RULE = (
    "main_ratio_effect_requires_source_backed_denominator_replacement_or_"
    "reallocation_not_addition"
)
DENOMINATOR_REPLACEMENT_EVIDENCE_STATUS = (
    "no_independently_admitted_component_replacement_or_reallocation_evidence"
)
DENOMINATOR_REPLACEMENT_ALLOWED_USE = (
    "model_research_contract_only_not_runtime_denominator_input"
)
DENOMINATOR_REPLACEMENT_BLOCKED_USE = (
    "additive_drag;denominator_prior_update;canonical_ratio;evidence_mode"
)
DENOMINATOR_REPLACEMENT_REQUIRED_EVIDENCE = (
    "component_scope;current_demand_mapping;policy_path_timing;"
    "source_uncertainty;nonadditivity_overlap_review;"
    "sidecar_subbase_impact_review;replacement_weight_or_reallocation_rule"
)
DENOMINATOR_REPLACEMENT_CURRENT_MODEL_ROLE = (
    "assumption_mode_fixed_allocation_component_not_empirical_subchannel_estimate"
)
DENOMINATOR_REALLOCATION_SIDECAR_BOUNDARY = (
    "share_reallocation_can_change_borrowing_credit_sidecar_bases_even_when_"
    "headline_denominator_is_unchanged"
)
DENOMINATOR_REPLACEMENT_IMPACT_STATUS = (
    "blocked_no_source_backed_component_replacement_or_reallocation_admitted"
)
DENOMINATOR_REPLACEMENT_IMPACT_ALLOWED_USE = (
    "source_review_design_only_not_runtime_or_denominator_input"
)
DENOMINATOR_REPLACEMENT_IMPACT_BLOCKED_USE = (
    "runtime_denominator_effect;main_ratio_effect;denominator_prior_update;"
    "canonical_ratio;evidence_mode;additive_drag"
)
DENOMINATOR_REALLOCATION_SIDECAR_IMPACT_RULE = (
    "share_reallocation_requires_sidecar_subbase_review_before_any_ratio_effect"
)
TDSP_IMPACT_CANDIDATE_LENS = "tdsp_current_demand"
TDSP_IMPACT_REQUIRED_EVIDENCE = (
    "core_tdsp_current_demand_response;policy_path_normalization;"
    "component_scope_mapping;source_uncertainty;nonadditivity_overlap_review;"
    "sidecar_subbase_impact_review"
)

DENOMINATOR_COMPONENT_REPLACEMENT_SPECS = {
    "borrowing_cost_drag": {
        "research_target": "household_firm_debt_service_and_borrowing_cost_cashflow",
        "candidate_diagnostic_lens": (
            "tdsp_household_debt_service_context_only_for_borrowing_cost_subcomponent"
        ),
        "required_source_family": (
            "source_backed_required_payment_or_spread_cashflow_current_demand_"
            "mapping_with_nonadditivity_review"
        ),
        "tdsp_role": (
            "tdsp_may_reallocate_borrowing_cost_subcomponent_only_after_core_"
            "current_demand_bridge_and_policy_path_admission"
        ),
    },
    "credit_supply_drag": {
        "research_target": "bank_and_nonbank_credit_supply_quantity_constraint",
        "candidate_diagnostic_lens": (
            "bank_credit_private_credit_context_not_tdsp_payment_channel"
        ),
        "required_source_family": (
            "source_backed_credit_supply_quantity_or_spread_design_with_current_"
            "demand_mapping_and_overlap_review"
        ),
        "tdsp_role": "tdsp_not_assigned_to_credit_supply_component",
    },
    "asset_price_drag": {
        "research_target": "asset_price_wealth_and_collateral_channel",
        "candidate_diagnostic_lens": (
            "asset_price_wealth_context_not_tdsp_payment_channel"
        ),
        "required_source_family": (
            "source_backed_asset_price_wealth_current_demand_design_with_overlap_"
            "review"
        ),
        "tdsp_role": "tdsp_not_assigned_to_asset_price_component",
    },
    "expectations_drag": {
        "research_target": "confidence_expectations_intertemporal_demand_channel",
        "candidate_diagnostic_lens": (
            "expectations_context_not_tdsp_payment_channel"
        ),
        "required_source_family": (
            "source_backed_expectations_shock_current_demand_design_with_overlap_"
            "review"
        ),
        "tdsp_role": "tdsp_not_assigned_to_expectations_component",
    },
    "exchange_rate_external_drag": {
        "research_target": "exchange_rate_and_external_demand_channel",
        "candidate_diagnostic_lens": (
            "external_demand_context_not_tdsp_payment_channel"
        ),
        "required_source_family": (
            "source_backed_exchange_rate_external_demand_design_with_overlap_review"
        ),
        "tdsp_role": "tdsp_not_assigned_to_exchange_external_component",
    },
}


def _conventional_drag_component_replacement_contract(
    component: str,
) -> dict[str, str]:
    """Return fail-closed component policy for denominator replacement research."""

    spec = DENOMINATOR_COMPONENT_REPLACEMENT_SPECS[component]
    is_borrowing_cost = component == "borrowing_cost_drag"
    return {
        "denominator_component": component,
        "research_target": spec["research_target"],
        "candidate_diagnostic_lens": spec["candidate_diagnostic_lens"],
        "tdsp_role": spec["tdsp_role"],
        "tdsp_current_demand_lens_role": (
            TDSP_BORROWING_COST_DIAGNOSTIC_LENS_ROLE
            if is_borrowing_cost
            else "not_tdsp_current_demand_lens_component"
        ),
        "tdsp_current_demand_overlap_rule": (
            TDSP_BORROWING_COST_OVERLAP_RULE
            if is_borrowing_cost
            else "tdsp_not_assigned_to_this_denominator_component"
        ),
        "required_source_family": spec["required_source_family"],
        "required_evidence": DENOMINATOR_REPLACEMENT_REQUIRED_EVIDENCE,
        "current_model_role": DENOMINATOR_REPLACEMENT_CURRENT_MODEL_ROLE,
        "replacement_reallocation_status": DENOMINATOR_REPLACEMENT_RESEARCH_STATUS,
        "component_replacement_evidence_status": (
            DENOMINATOR_REPLACEMENT_EVIDENCE_STATUS
        ),
        "share_reallocation_behaviorally_neutral": "false",
        "sidecar_subbase_impact_review_required": "true",
        "sidecar_subbase_impact_boundary": DENOMINATOR_REALLOCATION_SIDECAR_BOUNDARY,
        "additive_drag_allowed": "false",
        "replacement_denominator_admitted": "false",
        "reallocation_admitted": "false",
        "main_ratio_effect_rule": DENOMINATOR_REPLACEMENT_MAIN_RATIO_RULE,
        "denominator_prior_update_allowed": "false",
        "enters_main_ratio": "false",
        "canonical_ratio_entry": "false",
        "evidence_mode_enabled": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_offset_ratio_changed_this_tranche": "false",
        "dynamic_equation_changed_this_tranche": "false",
        "allowed_use": DENOMINATOR_REPLACEMENT_ALLOWED_USE,
        "blocked_use": DENOMINATOR_REPLACEMENT_BLOCKED_USE,
        "claim_boundary": (
            "denominator_replacement_reallocation_research_contract_"
            "not_runtime_admission"
        ),
    }


@dataclass(frozen=True)
class RateWallAssumptionSet:
    """Explicit speculative assumptions for a RateWall hit calculation."""

    name: str
    description: str
    horizon: str
    policy_rate_bps: NumberLike
    public_impulse_multiplier: NumberLike
    treasury_interest_demand_share: NumberLike
    fed_interest_demand_share: NumberLike
    iorb_recipient_demand_share: NumberLike
    on_rrp_recipient_demand_share: NumberLike
    current_remittance_demand_share: NumberLike
    future_remittance_drag_demand_share: NumberLike
    fiscal_offset_share: NumberLike
    tga_liquidity_offset_share: NumberLike
    firm_cash_attenuation_share: NumberLike
    safe_asset_allocation_offset_share: NumberLike
    safe_asset_allocation_drag_share: NumberLike
    zero_interest_credit_attenuation_share: NumberLike
    contractionary_drag_gdp_share: NumberLike
    borrowing_cost_drag_share: NumberLike
    credit_supply_drag_share: NumberLike
    asset_price_drag_share: NumberLike
    expectations_drag_share: NumberLike
    exchange_rate_external_drag_share: NumberLike
    split_denominator_total_drag_multiplier: NumberLike
    benchmark_uncertainty_share: NumberLike
    assumption_status: str
    source_status: str
    editable_label: str = ""
    unit_scope: str = "share_or_multiplier_unless_noted"
    claim_boundary: str = "assumption_mode_speculative_not_empirical_threshold_date"
    public_debt_stock_scale: NumberLike = Decimal("1")
    debt_state_drag_multiplier: NumberLike = Decimal("1")
    treasury_repricing_speed_share: NumberLike = Decimal("1")
    rate_path_bps_year: NumberLike = Decimal("100")
    treasury_repricing_pass_through: NumberLike = Decimal("1")
    fed_liability_stock_scale: NumberLike = Decimal("1")
    iorb_pass_through_scale: NumberLike = Decimal("1")
    on_rrp_pass_through_scale: NumberLike = Decimal("1")
    current_remittance_timing_share: NumberLike = Decimal("1")
    future_remittance_drag_timing_share: NumberLike = Decimal("1")
    future_remittance_drag_treatment: str = "future_public_finance_memo"
    household_safe_asset_stock_share: NumberLike = Decimal("0")
    household_safe_asset_access_conditioner: NumberLike = Decimal("0")
    retail_safe_yield_pass_through_beta: NumberLike = Decimal("0")
    household_safe_yield_current_spend_share: NumberLike = Decimal("0")
    deposit_mmf_substitution_conditioner: NumberLike = Decimal("0")
    deposit_mmf_substitution_drag_share: NumberLike = Decimal("0")
    firm_liquid_asset_stock_share_gdp: NumberLike = Decimal("0.27")
    zero_interest_credit_stock_share_gdp: NumberLike = Decimal("0.005")
    firm_liquid_asset_cushion_share: NumberLike = Decimal("0")
    firm_rollover_pressure_share: NumberLike = Decimal("0")
    foreign_treasury_holder_leakage_share: NumberLike = Decimal("0")
    interest_income_tax_timing_leakage_share: NumberLike = Decimal("0")
    rate_sensitive_consumer_credit_stock_share_gdp: NumberLike = Decimal("0")
    consumer_credit_reprice_beta: NumberLike = Decimal("0")
    consumer_credit_cashflow_drag_conversion: NumberLike = Decimal("0")
    cre_refi_drag_gdp_share_per_100bp_year: NumberLike = Decimal("0")
    private_credit_ndfi_credit_drag_share: NumberLike = Decimal("0")
    denominator_sidecar_overlap_discount_share: NumberLike = Decimal("0")
    fixed_mortgage_payment_shield_share_of_household_borrowing_drag: NumberLike = (
        Decimal("0")
    )
    pension_contribution_relief_gdp_share_per_100bp_year: NumberLike = Decimal("0")
    retirement_insurance_yield_spend_conversion_share: NumberLike = Decimal("0")
    pension_insurance_pass_through_lag_years: NumberLike = Decimal("0")




def assumption_set_row(assumption: RateWallAssumptionSet) -> dict[str, str]:
    """Serialize one assumption set."""

    return {
        "assumption_set": assumption.name,
        "editable_label": assumption.editable_label or assumption.name,
        "description": assumption.description,
        "horizon": assumption.horizon,
        "policy_rate_bps": str(_nonnegative(assumption.policy_rate_bps, "policy_rate_bps")),
        "public_impulse_multiplier": str(
            _nonnegative(assumption.public_impulse_multiplier, "public_impulse_multiplier")
        ),
        "public_debt_stock_scale": str(
            _nonnegative(assumption.public_debt_stock_scale, "public_debt_stock_scale")
        ),
        "debt_state_drag_multiplier": str(
            _nonnegative(
                assumption.debt_state_drag_multiplier,
                "debt_state_drag_multiplier",
            )
        ),
        "treasury_repricing_speed_share": str(
            _share(
                assumption.treasury_repricing_speed_share,
                "treasury_repricing_speed_share",
            )
        ),
        "rate_path_bps_year": str(
            _nonnegative(assumption.rate_path_bps_year, "rate_path_bps_year")
        ),
        "treasury_repricing_pass_through": str(
            _share(
                assumption.treasury_repricing_pass_through,
                "treasury_repricing_pass_through",
            )
        ),
        "fed_liability_stock_scale": str(
            _nonnegative(
                assumption.fed_liability_stock_scale,
                "fed_liability_stock_scale",
            )
        ),
        "iorb_pass_through_scale": str(
            _share(assumption.iorb_pass_through_scale, "iorb_pass_through_scale")
        ),
        "on_rrp_pass_through_scale": str(
            _share(
                assumption.on_rrp_pass_through_scale,
                "on_rrp_pass_through_scale",
            )
        ),
        "current_remittance_timing_share": str(
            _share(
                assumption.current_remittance_timing_share,
                "current_remittance_timing_share",
            )
        ),
        "future_remittance_drag_timing_share": str(
            _share(
                assumption.future_remittance_drag_timing_share,
                "future_remittance_drag_timing_share",
            )
        ),
        "future_remittance_drag_treatment": assumption.future_remittance_drag_treatment,
        "treasury_interest_demand_share": str(
            _share(assumption.treasury_interest_demand_share, "treasury_interest_demand_share")
        ),
        "fed_interest_demand_share": str(
            _share(assumption.fed_interest_demand_share, "fed_interest_demand_share")
        ),
        "iorb_recipient_demand_share": str(
            _share(
                assumption.iorb_recipient_demand_share,
                "iorb_recipient_demand_share",
            )
        ),
        "on_rrp_recipient_demand_share": str(
            _share(
                assumption.on_rrp_recipient_demand_share,
                "on_rrp_recipient_demand_share",
            )
        ),
        "current_remittance_demand_share": str(
            _share(
                assumption.current_remittance_demand_share,
                "current_remittance_demand_share",
            )
        ),
        "future_remittance_drag_demand_share": str(
            _share(
                assumption.future_remittance_drag_demand_share,
                "future_remittance_drag_demand_share",
            )
        ),
        "fiscal_offset_share": str(_share(assumption.fiscal_offset_share, "fiscal_offset_share")),
        "tga_liquidity_offset_share": str(
            _share(assumption.tga_liquidity_offset_share, "tga_liquidity_offset_share")
        ),
        "firm_cash_attenuation_share": str(
            _share(assumption.firm_cash_attenuation_share, "firm_cash_attenuation_share")
        ),
        "safe_asset_allocation_offset_share": str(
            _share(
                assumption.safe_asset_allocation_offset_share,
                "safe_asset_allocation_offset_share",
            )
        ),
        "safe_asset_allocation_drag_share": str(
            _share(
                assumption.safe_asset_allocation_drag_share,
                "safe_asset_allocation_drag_share",
            )
        ),
        "zero_interest_credit_attenuation_share": str(
            _share(
                assumption.zero_interest_credit_attenuation_share,
                "zero_interest_credit_attenuation_share",
            )
        ),
        "firm_liquid_asset_stock_share_gdp": str(
            _share(
                assumption.firm_liquid_asset_stock_share_gdp,
                "firm_liquid_asset_stock_share_gdp",
            )
        ),
        "zero_interest_credit_stock_share_gdp": str(
            _share(
                assumption.zero_interest_credit_stock_share_gdp,
                "zero_interest_credit_stock_share_gdp",
            )
        ),
        "household_safe_asset_stock_share": str(
            _share(
                assumption.household_safe_asset_stock_share,
                "household_safe_asset_stock_share",
            )
        ),
        "household_safe_asset_access_conditioner": str(
            _share(
                assumption.household_safe_asset_access_conditioner,
                "household_safe_asset_access_conditioner",
            )
        ),
        "retail_safe_yield_pass_through_beta": str(
            _share(
                assumption.retail_safe_yield_pass_through_beta,
                "retail_safe_yield_pass_through_beta",
            )
        ),
        "household_safe_yield_current_spend_share": str(
            _share(
                assumption.household_safe_yield_current_spend_share,
                "household_safe_yield_current_spend_share",
            )
        ),
        "deposit_mmf_substitution_conditioner": str(
            _share(
                assumption.deposit_mmf_substitution_conditioner,
                "deposit_mmf_substitution_conditioner",
            )
        ),
        "deposit_mmf_substitution_drag_share": str(
            _share(
                assumption.deposit_mmf_substitution_drag_share,
                "deposit_mmf_substitution_drag_share",
            )
        ),
        "firm_liquid_asset_cushion_share": str(
            _share(
                assumption.firm_liquid_asset_cushion_share,
                "firm_liquid_asset_cushion_share",
            )
        ),
        "firm_rollover_pressure_share": str(
            _share(
                assumption.firm_rollover_pressure_share,
                "firm_rollover_pressure_share",
            )
        ),
        "foreign_treasury_holder_leakage_share": str(
            _share(
                assumption.foreign_treasury_holder_leakage_share,
                "foreign_treasury_holder_leakage_share",
            )
        ),
        "interest_income_tax_timing_leakage_share": str(
            _share(
                assumption.interest_income_tax_timing_leakage_share,
                "interest_income_tax_timing_leakage_share",
            )
        ),
        "rate_sensitive_consumer_credit_stock_share_gdp": str(
            _share(
                assumption.rate_sensitive_consumer_credit_stock_share_gdp,
                "rate_sensitive_consumer_credit_stock_share_gdp",
            )
        ),
        "consumer_credit_reprice_beta": str(
            _share(assumption.consumer_credit_reprice_beta, "consumer_credit_reprice_beta")
        ),
        "consumer_credit_cashflow_drag_conversion": str(
            _share(
                assumption.consumer_credit_cashflow_drag_conversion,
                "consumer_credit_cashflow_drag_conversion",
            )
        ),
        "cre_refi_drag_gdp_share_per_100bp_year": str(
            _nonnegative(
                assumption.cre_refi_drag_gdp_share_per_100bp_year,
                "cre_refi_drag_gdp_share_per_100bp_year",
            )
        ),
        "private_credit_ndfi_credit_drag_share": str(
            _share(
                assumption.private_credit_ndfi_credit_drag_share,
                "private_credit_ndfi_credit_drag_share",
            )
        ),
        "denominator_sidecar_overlap_discount_share": str(
            _share(
                assumption.denominator_sidecar_overlap_discount_share,
                "denominator_sidecar_overlap_discount_share",
            )
        ),
        "fixed_mortgage_payment_shield_share_of_household_borrowing_drag": str(
            _share(
                assumption.fixed_mortgage_payment_shield_share_of_household_borrowing_drag,
                "fixed_mortgage_payment_shield_share_of_household_borrowing_drag",
            )
        ),
        "pension_contribution_relief_gdp_share_per_100bp_year": str(
            _nonnegative(
                assumption.pension_contribution_relief_gdp_share_per_100bp_year,
                "pension_contribution_relief_gdp_share_per_100bp_year",
            )
        ),
        "retirement_insurance_yield_spend_conversion_share": str(
            _share(
                assumption.retirement_insurance_yield_spend_conversion_share,
                "retirement_insurance_yield_spend_conversion_share",
            )
        ),
        "pension_insurance_pass_through_lag_years": str(
            _nonnegative(
                assumption.pension_insurance_pass_through_lag_years,
                "pension_insurance_pass_through_lag_years",
            )
        ),
        "contractionary_drag_gdp_share": str(
            _nonnegative(
                assumption.contractionary_drag_gdp_share,
                "contractionary_drag_gdp_share",
            )
        ),
        "borrowing_cost_drag_share": str(
            _share(assumption.borrowing_cost_drag_share, "borrowing_cost_drag_share")
        ),
        "credit_supply_drag_share": str(
            _share(assumption.credit_supply_drag_share, "credit_supply_drag_share")
        ),
        "asset_price_drag_share": str(
            _share(assumption.asset_price_drag_share, "asset_price_drag_share")
        ),
        "expectations_drag_share": str(
            _share(assumption.expectations_drag_share, "expectations_drag_share")
        ),
        "exchange_rate_external_drag_share": str(
            _share(
                assumption.exchange_rate_external_drag_share,
                "exchange_rate_external_drag_share",
            )
        ),
        "denominator_share_sum": str(_denominator_share_sum(assumption)),
        "denominator_share_sum_status": _denominator_share_sum_status(
            _denominator_share_sum(assumption)
        ),
        "split_denominator_total_drag_multiplier": str(
            _nonnegative(
                assumption.split_denominator_total_drag_multiplier,
                "split_denominator_total_drag_multiplier",
            )
        ),
        "split_denominator_mode": _split_denominator_mode(assumption),
        "benchmark_uncertainty_share": str(
            _share(assumption.benchmark_uncertainty_share, "benchmark_uncertainty_share")
        ),
        "unit_scope": assumption.unit_scope,
        "assumption_status": assumption.assumption_status,
        "source_status": assumption.source_status,
        "claim_boundary": assumption.claim_boundary,
        "mode": "assumption_mode",
    }


def solve_assumption(
    *,
    assumption: RateWallAssumptionSet,
    gdp_bil: NumberLike,
    treasury_interest_impulse_bil: NumberLike,
    iorb_interest_impulse_bil: NumberLike,
    on_rrp_interest_impulse_bil: NumberLike,
    current_remittance_reduction_bil: NumberLike,
    future_remittance_drag_bil: NumberLike,
    current_remittance_state_bil: NumberLike | None = None,
) -> dict[str, str]:
    """Compute RateWall hit status under one explicit assumption set."""

    gdp = _positive(gdp_bil, "gdp_bil")
    treasury_impulse = _nonnegative(
        treasury_interest_impulse_bil, "treasury_interest_impulse_bil"
    )
    iorb_impulse = _nonnegative(iorb_interest_impulse_bil, "iorb_interest_impulse_bil")
    on_rrp_impulse = _nonnegative(
        on_rrp_interest_impulse_bil,
        "on_rrp_interest_impulse_bil",
    )
    current_remittance_state = _signed_decimal(
        current_remittance_state_bil
        if current_remittance_state_bil is not None
        else current_remittance_reduction_bil,
        "current_remittance_state_bil"
        if current_remittance_state_bil is not None
        else "current_remittance_reduction_bil",
    )
    future_drag = _nonnegative(future_remittance_drag_bil, "future_remittance_drag_bil")
    multiplier = _nonnegative(
        assumption.public_impulse_multiplier, "public_impulse_multiplier"
    )
    if multiplier != Decimal("1.00"):
        raise ValueError(
            "public_impulse_multiplier is deprecated compatibility metadata and "
            "must remain neutral at 1.00; use factored public-liability handles "
            "instead"
        )
    public_debt_stock_scale = _nonnegative(
        assumption.public_debt_stock_scale, "public_debt_stock_scale"
    )
    treasury_repricing_speed_share = _share(
        assumption.treasury_repricing_speed_share,
        "treasury_repricing_speed_share",
    )
    rate_path_bps_year = _nonnegative(
        assumption.rate_path_bps_year, "rate_path_bps_year"
    )
    rate_path_scale = rate_path_bps_year / Decimal("100")
    treasury_repricing_pass_through = _share(
        assumption.treasury_repricing_pass_through,
        "treasury_repricing_pass_through",
    )
    fed_liability_stock_scale = _nonnegative(
        assumption.fed_liability_stock_scale, "fed_liability_stock_scale"
    )
    iorb_pass_through_scale = _share(
        assumption.iorb_pass_through_scale, "iorb_pass_through_scale"
    )
    on_rrp_pass_through_scale = _share(
        assumption.on_rrp_pass_through_scale, "on_rrp_pass_through_scale"
    )
    current_remittance_timing_share = _share(
        assumption.current_remittance_timing_share,
        "current_remittance_timing_share",
    )
    future_remittance_drag_timing_share = _share(
        assumption.future_remittance_drag_timing_share,
        "future_remittance_drag_timing_share",
    )
    treasury_demand_share = _share(
        assumption.treasury_interest_demand_share, "treasury_interest_demand_share"
    )
    iorb_demand_share = _share(
        assumption.iorb_recipient_demand_share, "iorb_recipient_demand_share"
    )
    on_rrp_demand_share = _share(
        assumption.on_rrp_recipient_demand_share,
        "on_rrp_recipient_demand_share",
    )
    current_remittance_demand_share = _share(
        assumption.current_remittance_demand_share,
        "current_remittance_demand_share",
    )
    future_drag_demand_share = _share(
        assumption.future_remittance_drag_demand_share,
        "future_remittance_drag_demand_share",
    )
    fiscal_offset_share = _share(assumption.fiscal_offset_share, "fiscal_offset_share")
    tga_offset_share = _share(
        assumption.tga_liquidity_offset_share, "tga_liquidity_offset_share"
    )
    firm_cash_share = _share(
        assumption.firm_cash_attenuation_share, "firm_cash_attenuation_share"
    )
    configured_safe_asset_share = _share(
        assumption.safe_asset_allocation_offset_share,
        "safe_asset_allocation_offset_share",
    )
    safe_asset_drag_share = _share(
        assumption.safe_asset_allocation_drag_share,
        "safe_asset_allocation_drag_share",
    )
    zero_credit_share = _share(
        assumption.zero_interest_credit_attenuation_share,
        "zero_interest_credit_attenuation_share",
    )
    firm_liquid_asset_stock_share_gdp = _share(
        assumption.firm_liquid_asset_stock_share_gdp,
        "firm_liquid_asset_stock_share_gdp",
    )
    zero_interest_credit_stock_share_gdp = _share(
        assumption.zero_interest_credit_stock_share_gdp,
        "zero_interest_credit_stock_share_gdp",
    )
    household_safe_asset_stock_share = _share(
        assumption.household_safe_asset_stock_share,
        "household_safe_asset_stock_share",
    )
    household_safe_asset_access_conditioner = _share(
        assumption.household_safe_asset_access_conditioner,
        "household_safe_asset_access_conditioner",
    )
    retail_safe_yield_pass_through_beta = _share(
        assumption.retail_safe_yield_pass_through_beta,
        "retail_safe_yield_pass_through_beta",
    )
    household_safe_yield_current_spend_share = _share(
        assumption.household_safe_yield_current_spend_share,
        "household_safe_yield_current_spend_share",
    )
    deposit_mmf_substitution_conditioner = _share(
        assumption.deposit_mmf_substitution_conditioner,
        "deposit_mmf_substitution_conditioner",
    )
    deposit_mmf_substitution_drag_share = _share(
        assumption.deposit_mmf_substitution_drag_share,
        "deposit_mmf_substitution_drag_share",
    )
    firm_liquid_asset_cushion_share = _share(
        assumption.firm_liquid_asset_cushion_share,
        "firm_liquid_asset_cushion_share",
    )
    firm_rollover_pressure_share = _share(
        assumption.firm_rollover_pressure_share,
        "firm_rollover_pressure_share",
    )
    foreign_treasury_holder_leakage_share = _share(
        assumption.foreign_treasury_holder_leakage_share,
        "foreign_treasury_holder_leakage_share",
    )
    interest_income_tax_timing_leakage_share = _share(
        assumption.interest_income_tax_timing_leakage_share,
        "interest_income_tax_timing_leakage_share",
    )
    rate_sensitive_consumer_credit_stock_share_gdp = _share(
        assumption.rate_sensitive_consumer_credit_stock_share_gdp,
        "rate_sensitive_consumer_credit_stock_share_gdp",
    )
    consumer_credit_reprice_beta = _share(
        assumption.consumer_credit_reprice_beta,
        "consumer_credit_reprice_beta",
    )
    consumer_credit_cashflow_drag_conversion = _share(
        assumption.consumer_credit_cashflow_drag_conversion,
        "consumer_credit_cashflow_drag_conversion",
    )
    cre_refi_drag_gdp_share_per_100bp_year = _nonnegative(
        assumption.cre_refi_drag_gdp_share_per_100bp_year,
        "cre_refi_drag_gdp_share_per_100bp_year",
    )
    private_credit_ndfi_credit_drag_share = _share(
        assumption.private_credit_ndfi_credit_drag_share,
        "private_credit_ndfi_credit_drag_share",
    )
    denominator_sidecar_overlap_discount_share = _share(
        assumption.denominator_sidecar_overlap_discount_share,
        "denominator_sidecar_overlap_discount_share",
    )
    fixed_mortgage_payment_shield_share = _share(
        assumption.fixed_mortgage_payment_shield_share_of_household_borrowing_drag,
        "fixed_mortgage_payment_shield_share_of_household_borrowing_drag",
    )
    pension_contribution_relief_gdp_share_per_100bp_year = _nonnegative(
        assumption.pension_contribution_relief_gdp_share_per_100bp_year,
        "pension_contribution_relief_gdp_share_per_100bp_year",
    )
    retirement_insurance_yield_spend_conversion_share = _share(
        assumption.retirement_insurance_yield_spend_conversion_share,
        "retirement_insurance_yield_spend_conversion_share",
    )
    pension_insurance_pass_through_lag_years = _nonnegative(
        assumption.pension_insurance_pass_through_lag_years,
        "pension_insurance_pass_through_lag_years",
    )
    drag_share = _nonnegative(
        assumption.contractionary_drag_gdp_share,
        "contractionary_drag_gdp_share",
    )
    debt_state_drag_multiplier = _nonnegative(
        assumption.debt_state_drag_multiplier,
        "debt_state_drag_multiplier",
    )
    borrowing_drag_share = _share(
        assumption.borrowing_cost_drag_share, "borrowing_cost_drag_share"
    )
    credit_drag_share = _share(
        assumption.credit_supply_drag_share, "credit_supply_drag_share"
    )
    asset_price_drag_share = _share(
        assumption.asset_price_drag_share, "asset_price_drag_share"
    )
    expectations_drag_share = _share(
        assumption.expectations_drag_share, "expectations_drag_share"
    )
    exchange_drag_share = _share(
        assumption.exchange_rate_external_drag_share,
        "exchange_rate_external_drag_share",
    )
    denominator_share_sum = (
        borrowing_drag_share
        + credit_drag_share
        + asset_price_drag_share
        + expectations_drag_share
        + exchange_drag_share
    )
    denominator_share_sum_status = _denominator_share_sum_status(denominator_share_sum)
    if denominator_share_sum_status != "shares_sum_to_one":
        raise ValueError(
            "split-denominator component shares must sum to 1; use "
            "split_denominator_total_drag_multiplier for total-drag scaling"
        )
    total_drag_multiplier = _nonnegative(
        assumption.split_denominator_total_drag_multiplier,
        "split_denominator_total_drag_multiplier",
    )
    uncertainty_share = _share(
        assumption.benchmark_uncertainty_share, "benchmark_uncertainty_share"
    )
    policy_rate_bps = _nonnegative(assumption.policy_rate_bps, "policy_rate_bps")
    treasury_factor_multiplier = (
        public_debt_stock_scale
        * treasury_repricing_speed_share
        * rate_path_scale
        * treasury_repricing_pass_through
    )
    iorb_factor_multiplier = (
        fed_liability_stock_scale * rate_path_scale * iorb_pass_through_scale
    )
    on_rrp_factor_multiplier = (
        fed_liability_stock_scale * rate_path_scale * on_rrp_pass_through_scale
    )
    remittance_current_factor_multiplier = (
        fed_liability_stock_scale * rate_path_scale * current_remittance_timing_share
    )
    remittance_future_factor_multiplier = (
        fed_liability_stock_scale
        * rate_path_scale
        * future_remittance_drag_timing_share
    )
    adjusted_treasury_impulse = treasury_impulse * treasury_factor_multiplier
    adjusted_iorb_impulse = iorb_impulse * iorb_factor_multiplier
    adjusted_on_rrp_impulse = on_rrp_impulse * on_rrp_factor_multiplier
    adjusted_current_remittance = (
        current_remittance_state * remittance_current_factor_multiplier
    )
    current_remittance_positive_support = max(adjusted_current_remittance, Decimal("0"))
    current_remittance_negative_drag = min(adjusted_current_remittance, Decimal("0"))
    adjusted_future_drag = future_drag * remittance_future_factor_multiplier
    private_recipient_cashflow_impulse = (
        adjusted_treasury_impulse + adjusted_iorb_impulse + adjusted_on_rrp_impulse
    )
    component_display_total = (
        adjusted_treasury_impulse
        + adjusted_iorb_impulse
        + adjusted_on_rrp_impulse
        + adjusted_current_remittance
        + adjusted_future_drag
    )
    adjusted_fed_impulse = adjusted_iorb_impulse + adjusted_on_rrp_impulse
    gross_public_impulse = private_recipient_cashflow_impulse
    foreign_treasury_holder_leakage_drag = (
        adjusted_treasury_impulse * foreign_treasury_holder_leakage_share
    )
    treasury_domestic_impulse = max(
        adjusted_treasury_impulse - foreign_treasury_holder_leakage_drag,
        Decimal("0"),
    )
    treasury_demand_offset = treasury_domestic_impulse * treasury_demand_share
    iorb_demand_offset = adjusted_iorb_impulse * iorb_demand_share
    on_rrp_demand_offset = adjusted_on_rrp_impulse * on_rrp_demand_share
    current_remittance_offset = (
        adjusted_current_remittance * current_remittance_demand_share
    )
    future_public_finance_drag = adjusted_future_drag * (
        Decimal("1") - future_drag_demand_share
    )
    future_drag_offset = -(adjusted_future_drag * future_drag_demand_share)
    gross_current_interest_offset = (
        treasury_demand_offset
        + iorb_demand_offset
        + on_rrp_demand_offset
        + current_remittance_offset
        + future_drag_offset
    )
    interest_income_tax_timing_base = max(gross_current_interest_offset, Decimal("0"))
    interest_income_tax_timing_drag = (
        interest_income_tax_timing_base * interest_income_tax_timing_leakage_share
    )
    interest_demand_offset = gross_current_interest_offset
    net_interest_before_fiscal_tga = max(
        gross_current_interest_offset - interest_income_tax_timing_drag,
        Decimal("0"),
    )
    fiscal_offset = net_interest_before_fiscal_tga * fiscal_offset_share
    tga_offset = net_interest_before_fiscal_tga * tga_offset_share
    net_interest_demand_offset = max(
        net_interest_before_fiscal_tga - fiscal_offset - tga_offset,
        Decimal("0"),
    )
    absorber_basis = "tax_adjusted_recipient_demand_converted_interest_offset"
    conventional_drag_anchor = gdp * drag_share * rate_path_scale
    conventional_drag = conventional_drag_anchor * debt_state_drag_multiplier
    scalar_borrowing_cost_drag = conventional_drag * borrowing_drag_share
    scalar_credit_supply_drag = conventional_drag * credit_drag_share
    composition_only_split_drag = conventional_drag
    split_denominator_drag = conventional_drag * total_drag_multiplier
    borrowing_cost_drag = split_denominator_drag * borrowing_drag_share
    credit_supply_drag = split_denominator_drag * credit_drag_share
    asset_price_drag = split_denominator_drag * asset_price_drag_share
    expectations_drag = split_denominator_drag * expectations_drag_share
    exchange_rate_external_drag = split_denominator_drag * exchange_drag_share
    scalar_borrowing_credit_drag = (
        scalar_borrowing_cost_drag + scalar_credit_supply_drag
    )
    borrowing_credit_drag = borrowing_cost_drag + credit_supply_drag
    firm_cash_applicable_drag_share = Decimal("0")
    split_denominator_drag = (
        borrowing_cost_drag
        + credit_supply_drag
        + asset_price_drag
        + expectations_drag
        + exchange_rate_external_drag
    )
    firm_cash_yield_base = (
        gdp * firm_liquid_asset_stock_share_gdp * (rate_path_bps_year / Decimal("10000"))
    )
    scalar_firm_cash_offset = firm_cash_yield_base * firm_cash_share
    total_scaled_firm_cash_offset = scalar_firm_cash_offset
    domestic_safe_interest_impulse = (
        treasury_domestic_impulse
        + adjusted_iorb_impulse * retail_safe_yield_pass_through_beta
        + adjusted_on_rrp_impulse
    )
    same_basis_recipient_demand_active = any(
        share > 0
        for share in (
            treasury_demand_share,
            iorb_demand_share,
            on_rrp_demand_share,
        )
    )
    exp1_same_basis_safe_yield_active = (
        retail_safe_yield_pass_through_beta > 0
        and household_safe_yield_current_spend_share > 0
        and (
            household_safe_asset_stock_share * household_safe_asset_access_conditioner
            > 0
            or deposit_mmf_substitution_conditioner > 0
        )
    )
    safe_asset_share = (
        Decimal("0")
        if same_basis_recipient_demand_active or exp1_same_basis_safe_yield_active
        else configured_safe_asset_share
    )
    safe_asset_offset = domestic_safe_interest_impulse * safe_asset_share
    safe_asset_drag = domestic_safe_interest_impulse * safe_asset_drag_share
    zero_credit_base = (
        gdp
        * zero_interest_credit_stock_share_gdp
        * (rate_path_bps_year / Decimal("10000"))
    )
    scalar_zero_credit_offset = zero_credit_base * zero_credit_share
    total_scaled_zero_credit_offset = scalar_zero_credit_offset
    household_safe_yield_capture_offset = (
        private_recipient_cashflow_impulse
        * household_safe_asset_stock_share
        * household_safe_asset_access_conditioner
        * retail_safe_yield_pass_through_beta
        * household_safe_yield_current_spend_share
    )
    baseline_safe_yield_access_share = (
        household_safe_asset_stock_share * household_safe_asset_access_conditioner
    )
    deposit_mmf_incremental_access_share = (
        max(Decimal("0"), Decimal("1") - baseline_safe_yield_access_share)
        * deposit_mmf_substitution_conditioner
    )
    deposit_mmf_substitution_offset = (
        private_recipient_cashflow_impulse
        * deposit_mmf_incremental_access_share
        * retail_safe_yield_pass_through_beta
        * household_safe_yield_current_spend_share
    )
    scalar_deposit_mmf_substitution_drag = (
        scalar_credit_supply_drag
        * deposit_mmf_incremental_access_share
        * deposit_mmf_substitution_drag_share
    )
    total_scaled_deposit_mmf_substitution_drag = (
        credit_supply_drag
        * deposit_mmf_incremental_access_share
        * deposit_mmf_substitution_drag_share
    )
    scalar_firm_liquid_asset_cushion_offset = (
        firm_cash_yield_base * firm_liquid_asset_cushion_share
    )
    total_scaled_firm_liquid_asset_cushion_offset = (
        firm_cash_yield_base * firm_liquid_asset_cushion_share
    )
    scalar_firm_rollover_pressure_drag = (
        scalar_borrowing_credit_drag * firm_rollover_pressure_share
    )
    total_scaled_firm_rollover_pressure_drag = (
        borrowing_credit_drag * firm_rollover_pressure_share
    )
    treasury_after_foreign_leakage_offset = max(
        adjusted_treasury_impulse - foreign_treasury_holder_leakage_drag,
        Decimal("0"),
    )
    recipient_leakage_sidecar_drag_total = (
        foreign_treasury_holder_leakage_drag + interest_income_tax_timing_drag
    )
    consumer_credit_drag_sidecar = (
        gdp
        * rate_sensitive_consumer_credit_stock_share_gdp
        * (rate_path_bps_year / Decimal("10000"))
        * consumer_credit_reprice_beta
        * consumer_credit_cashflow_drag_conversion
    )
    cre_refi_drag_sidecar = (
        gdp
        * cre_refi_drag_gdp_share_per_100bp_year
        * (rate_path_bps_year / Decimal("100"))
    )
    private_credit_ndfi_drag_sidecar = (
        scalar_credit_supply_drag * private_credit_ndfi_credit_drag_share
    )
    housing_lockin_payment_shield_sidecar = (
        scalar_borrowing_cost_drag * fixed_mortgage_payment_shield_share
    )
    denominator_sidecar_positive_drag_total = (
        consumer_credit_drag_sidecar
        + cre_refi_drag_sidecar
        + private_credit_ndfi_drag_sidecar
    )
    denominator_sidecar_active_drag_count = sum(
        int(value > 0)
        for value in (
            consumer_credit_drag_sidecar,
            cre_refi_drag_sidecar,
            private_credit_ndfi_drag_sidecar,
        )
    )
    denominator_sidecar_overlap_discount = (
        denominator_sidecar_positive_drag_total
        * denominator_sidecar_overlap_discount_share
        if denominator_sidecar_active_drag_count >= 2
        else Decimal("0")
    )
    denominator_sidecar_overlap_discount_status = (
        "active_multi_channel_discount"
        if denominator_sidecar_overlap_discount
        else (
            "configured_but_not_applied_single_or_zero_channel"
            if denominator_sidecar_overlap_discount_share
            else "inactive_zero_discount"
        )
    )
    denominator_sidecar_drag_adjustment = (
        denominator_sidecar_positive_drag_total
        - denominator_sidecar_overlap_discount
        - housing_lockin_payment_shield_sidecar
    )
    denominator_sidecar_adjusted_conventional_drag = max(
        conventional_drag + denominator_sidecar_drag_adjustment,
        Decimal("0"),
    )
    pension_contribution_relief_sidecar = (
        gdp
        * pension_contribution_relief_gdp_share_per_100bp_year
        * (rate_path_bps_year / Decimal("100"))
    )
    retirement_insurance_yield_spend_sidecar = (
        private_recipient_cashflow_impulse
        * retirement_insurance_yield_spend_conversion_share
    )
    assumption_mode_promoted_offset_total = (
        household_safe_yield_capture_offset
        + deposit_mmf_substitution_offset
    )
    assumption_mode_promoted_drag_total = scalar_deposit_mmf_substitution_drag
    total_scaled_assumption_mode_promoted_offset_total = (
        household_safe_yield_capture_offset
        + deposit_mmf_substitution_offset
    )
    total_scaled_assumption_mode_promoted_drag_total = total_scaled_deposit_mmf_substitution_drag
    scalar_countervailing_total = (
        net_interest_demand_offset
        + scalar_firm_cash_offset
        + safe_asset_offset
        + scalar_zero_credit_offset
        + assumption_mode_promoted_offset_total
        - safe_asset_drag
        - assumption_mode_promoted_drag_total
    )
    composition_only_countervailing_total = scalar_countervailing_total
    total_scaled_countervailing_total = (
        net_interest_demand_offset
        + total_scaled_firm_cash_offset
        + safe_asset_offset
        + total_scaled_zero_credit_offset
        + total_scaled_assumption_mode_promoted_offset_total
        - safe_asset_drag
        - total_scaled_assumption_mode_promoted_drag_total
    )
    denominator_sidecar_offset_ratio = (
        scalar_countervailing_total / denominator_sidecar_adjusted_conventional_drag
        if denominator_sidecar_adjusted_conventional_drag
        else Decimal("0")
    )
    recipient_leakage_sidecar_countervailing_total = scalar_countervailing_total
    recipient_leakage_sidecar_offset_ratio = (
        recipient_leakage_sidecar_countervailing_total / conventional_drag
        if conventional_drag
        else Decimal("0")
    )
    ratio = (
        scalar_countervailing_total / conventional_drag
        if conventional_drag
        else Decimal("0")
    )
    split_ratio = (
        total_scaled_countervailing_total / split_denominator_drag
        if split_denominator_drag
        else Decimal("0")
    )
    composition_only_split_ratio = (
        composition_only_countervailing_total / composition_only_split_drag
        if composition_only_split_drag
        else Decimal("0")
    )
    lower_denominator = conventional_drag * (Decimal("1") + uncertainty_share)
    lower_ratio = (
        scalar_countervailing_total / lower_denominator
        if lower_denominator
        else Decimal("0")
    )
    upper_denominator = conventional_drag * (Decimal("1") - uncertainty_share)
    upper_ratio = (
        scalar_countervailing_total / upper_denominator
        if upper_denominator
        else Decimal("0")
    )
    classification = _classification(ratio)
    composition_only_classification = _classification(composition_only_split_ratio)
    split_classification = _classification(split_ratio)
    dominant_gross_interest_subchannel = _dominant_channel(
        {
            "treasury_interest_demand_offset": treasury_demand_offset,
            "iorb_demand_offset": iorb_demand_offset,
            "on_rrp_demand_offset": on_rrp_demand_offset,
            "current_remittance_demand_offset": current_remittance_offset,
            "future_remittance_drag_demand_offset": future_drag_offset,
        }
    )
    dominant_net_countervailing_channel = _dominant_channel(
        {
            "net_interest_after_fiscal_tga_offsets": net_interest_demand_offset,
            "firm_cash_attenuation": scalar_firm_cash_offset,
            "safe_asset_allocation_offset": safe_asset_offset,
            "zero_interest_credit_attenuation": scalar_zero_credit_offset,
            "household_safe_yield_capture": household_safe_yield_capture_offset,
            "deposit_mmf_substitution_offset": deposit_mmf_substitution_offset,
        }
    )
    why = _why_label(
        hit=ratio >= Decimal("1"),
        dominant_channel=dominant_net_countervailing_channel,
        ratio=ratio,
    )
    return {
        "assumption_set": assumption.name,
        "description": assumption.description,
        "horizon": assumption.horizon,
        "mode": "assumption_mode",
        "policy_rate_bps": str(policy_rate_bps),
        "public_impulse_multiplier": str(multiplier),
        "public_impulse_multiplier_status": (
            "deprecated_compatibility_field_derived_from_factored_public_impulse_handles"
        ),
        "public_debt_stock_scale": str(public_debt_stock_scale),
        "debt_state_drag_multiplier": str(debt_state_drag_multiplier),
        "treasury_repricing_speed_share": str(treasury_repricing_speed_share),
        "rate_path_bps_year": str(_nonnegative(assumption.rate_path_bps_year, "rate_path_bps_year")),
        "treasury_repricing_pass_through": str(treasury_repricing_pass_through),
        "fed_liability_stock_scale": str(fed_liability_stock_scale),
        "iorb_pass_through_scale": str(iorb_pass_through_scale),
        "on_rrp_pass_through_scale": str(on_rrp_pass_through_scale),
        "current_remittance_timing_share": str(current_remittance_timing_share),
        "future_remittance_drag_timing_share": str(future_remittance_drag_timing_share),
        "future_remittance_drag_treatment": assumption.future_remittance_drag_treatment,
        "treasury_factor_multiplier": str(treasury_factor_multiplier),
        "iorb_factor_multiplier": str(iorb_factor_multiplier),
        "on_rrp_factor_multiplier": str(on_rrp_factor_multiplier),
        "remittance_current_factor_multiplier": str(
            remittance_current_factor_multiplier
        ),
        "remittance_future_factor_multiplier": str(
            remittance_future_factor_multiplier
        ),
        "treasury_interest_demand_share": str(treasury_demand_share),
        "iorb_recipient_demand_share": str(iorb_demand_share),
        "on_rrp_recipient_demand_share": str(on_rrp_demand_share),
        "current_remittance_demand_share": str(current_remittance_demand_share),
        "future_remittance_drag_demand_share": str(future_drag_demand_share),
        "fiscal_offset_share": str(fiscal_offset_share),
        "tga_liquidity_offset_share": str(tga_offset_share),
        "firm_cash_attenuation_share": str(firm_cash_share),
        "safe_asset_allocation_offset_share": str(safe_asset_share),
        "safe_asset_allocation_drag_share": str(safe_asset_drag_share),
        "zero_interest_credit_attenuation_share": str(zero_credit_share),
        "firm_liquid_asset_stock_share_gdp": str(firm_liquid_asset_stock_share_gdp),
        "zero_interest_credit_stock_share_gdp": str(
            zero_interest_credit_stock_share_gdp
        ),
        "household_safe_asset_stock_share": str(household_safe_asset_stock_share),
        "household_safe_asset_access_conditioner": str(
            household_safe_asset_access_conditioner
        ),
        "retail_safe_yield_pass_through_beta": str(retail_safe_yield_pass_through_beta),
        "household_safe_yield_current_spend_share": str(
            household_safe_yield_current_spend_share
        ),
        "deposit_mmf_substitution_conditioner": str(
            deposit_mmf_substitution_conditioner
        ),
        "deposit_mmf_substitution_drag_share": str(
            deposit_mmf_substitution_drag_share
        ),
        "firm_liquid_asset_cushion_share": str(firm_liquid_asset_cushion_share),
        "firm_rollover_pressure_share": str(firm_rollover_pressure_share),
        "foreign_treasury_holder_leakage_share": str(
            foreign_treasury_holder_leakage_share
        ),
        "interest_income_tax_timing_leakage_share": str(
            interest_income_tax_timing_leakage_share
        ),
        "rate_sensitive_consumer_credit_stock_share_gdp": str(
            rate_sensitive_consumer_credit_stock_share_gdp
        ),
        "consumer_credit_reprice_beta": str(consumer_credit_reprice_beta),
        "consumer_credit_cashflow_drag_conversion": str(
            consumer_credit_cashflow_drag_conversion
        ),
        "cre_refi_drag_gdp_share_per_100bp_year": str(
            cre_refi_drag_gdp_share_per_100bp_year
        ),
        "private_credit_ndfi_credit_drag_share": str(
            private_credit_ndfi_credit_drag_share
        ),
        "denominator_sidecar_overlap_discount_share": str(
            denominator_sidecar_overlap_discount_share
        ),
        "fixed_mortgage_payment_shield_share_of_household_borrowing_drag": str(
            fixed_mortgage_payment_shield_share
        ),
        "pension_contribution_relief_gdp_share_per_100bp_year": str(
            pension_contribution_relief_gdp_share_per_100bp_year
        ),
        "retirement_insurance_yield_spend_conversion_share": str(
            retirement_insurance_yield_spend_conversion_share
        ),
        "pension_insurance_pass_through_lag_years": str(
            pension_insurance_pass_through_lag_years
        ),
        "gdp_bil": str(gdp),
        "treasury_interest_impulse_bil": str(adjusted_treasury_impulse),
        "fed_interest_impulse_bil": str(adjusted_fed_impulse),
        "iorb_interest_impulse_bil": str(adjusted_iorb_impulse),
        "on_rrp_interest_impulse_bil": str(adjusted_on_rrp_impulse),
        "current_remittance_state_bil": str(adjusted_current_remittance),
        "signed_current_remittance_impact_bil": str(adjusted_current_remittance),
        "current_remittance_positive_support_bil": str(
            current_remittance_positive_support
        ),
        "current_remittance_negative_drag_bil": str(current_remittance_negative_drag),
        "current_remittance_reduction_bil": str(current_remittance_positive_support),
        "future_remittance_drag_bil": str(adjusted_future_drag),
        "private_recipient_cashflow_impulse_bil": str(
            private_recipient_cashflow_impulse
        ),
        "component_display_public_impulse_total_bil": str(component_display_total),
        "current_treasury_remittance_gap_bil": str(adjusted_current_remittance),
        "future_public_finance_drag_bil": str(future_public_finance_drag),
        "net_public_finance_adjustment_bil": str(
            adjusted_current_remittance - future_public_finance_drag
        ),
        "gross_public_interest_impulse_bil": str(gross_public_impulse),
        "treasury_domestic_impulse_bil": str(treasury_domestic_impulse),
        "treasury_interest_demand_offset_bil": str(treasury_demand_offset),
        "iorb_demand_offset_bil": str(iorb_demand_offset),
        "on_rrp_demand_offset_bil": str(on_rrp_demand_offset),
        "current_remittance_demand_offset_bil": str(current_remittance_offset),
        "future_remittance_drag_demand_offset_bil": str(future_drag_offset),
        "interest_demand_offset_bil": str(interest_demand_offset),
        "absorber_basis": absorber_basis,
        "fiscal_offset_bil": str(fiscal_offset),
        "tga_liquidity_offset_bil": str(tga_offset),
        "net_interest_before_fiscal_tga_offsets_bil": str(
            net_interest_before_fiscal_tga
        ),
        "net_interest_demand_offset_bil": str(net_interest_demand_offset),
        "net_interest_after_fiscal_tga_offsets_bil": str(net_interest_demand_offset),
        "firm_cash_yield_base_bil": str(firm_cash_yield_base),
        "firm_cash_attenuation_bil": str(scalar_firm_cash_offset),
        "firm_cash_applicable_drag_share": str(firm_cash_applicable_drag_share),
        "total_scaled_firm_cash_attenuation_bil": str(total_scaled_firm_cash_offset),
        "domestic_safe_interest_impulse_bil": str(domestic_safe_interest_impulse),
        "safe_asset_allocation_offset_bil": str(safe_asset_offset),
        "safe_asset_allocation_drag_bil": str(safe_asset_drag),
        "zero_interest_credit_base_bil": str(zero_credit_base),
        "zero_interest_credit_attenuation_bil": str(scalar_zero_credit_offset),
        "total_scaled_zero_interest_credit_attenuation_bil": str(
            total_scaled_zero_credit_offset
        ),
        "household_safe_yield_capture_offset_bil": str(
            household_safe_yield_capture_offset
        ),
        "baseline_safe_yield_access_share": str(baseline_safe_yield_access_share),
        "deposit_mmf_incremental_access_share": str(
            deposit_mmf_incremental_access_share
        ),
        "deposit_mmf_substitution_offset_bil": str(deposit_mmf_substitution_offset),
        "deposit_mmf_substitution_drag_bil": str(
            scalar_deposit_mmf_substitution_drag
        ),
        "total_scaled_deposit_mmf_substitution_drag_bil": str(
            total_scaled_deposit_mmf_substitution_drag
        ),
        "firm_liquid_asset_cushion_offset_bil": str(
            scalar_firm_liquid_asset_cushion_offset
        ),
        "total_scaled_firm_liquid_asset_cushion_offset_bil": str(
            total_scaled_firm_liquid_asset_cushion_offset
        ),
        "firm_rollover_pressure_drag_bil": str(scalar_firm_rollover_pressure_drag),
        "total_scaled_firm_rollover_pressure_drag_bil": str(
            total_scaled_firm_rollover_pressure_drag
        ),
        "assumption_mode_promoted_offset_total_bil": str(
            assumption_mode_promoted_offset_total
        ),
        "assumption_mode_promoted_drag_total_bil": str(
            assumption_mode_promoted_drag_total
        ),
        "assumption_mode_promoted_net_effect_bil": str(
            assumption_mode_promoted_offset_total - assumption_mode_promoted_drag_total
        ),
        "assumption_mode_promotion_status": (
            "active_assumption_mode_terms"
            if assumption_mode_promoted_offset_total
            or assumption_mode_promoted_drag_total
            else "inactive_zero_assumption_mode_terms"
        ),
        "foreign_treasury_holder_leakage_drag_bil": str(
            foreign_treasury_holder_leakage_drag
        ),
        "treasury_after_foreign_leakage_offset_bil": str(
            treasury_after_foreign_leakage_offset
        ),
        "interest_income_tax_timing_base_bil": str(interest_income_tax_timing_base),
        "interest_income_tax_timing_drag_bil": str(interest_income_tax_timing_drag),
        "recipient_leakage_sidecar_drag_total_bil": str(
            recipient_leakage_sidecar_drag_total
        ),
        "recipient_leakage_sidecar_countervailing_total_bil": str(
            recipient_leakage_sidecar_countervailing_total
        ),
        "recipient_leakage_sidecar_offset_ratio": str(
            recipient_leakage_sidecar_offset_ratio
        ),
        "consumer_credit_drag_sidecar_bil": str(consumer_credit_drag_sidecar),
        "cre_refi_drag_sidecar_bil": str(cre_refi_drag_sidecar),
        "private_credit_ndfi_drag_sidecar_bil": str(private_credit_ndfi_drag_sidecar),
        "denominator_sidecar_positive_drag_total_bil": str(
            denominator_sidecar_positive_drag_total
        ),
        "denominator_sidecar_overlap_discount_bil": str(
            denominator_sidecar_overlap_discount
        ),
        "denominator_sidecar_overlap_discount_status": (
            denominator_sidecar_overlap_discount_status
        ),
        "housing_lockin_payment_shield_sidecar_bil": str(
            housing_lockin_payment_shield_sidecar
        ),
        "denominator_sidecar_drag_adjustment_bil": str(
            denominator_sidecar_drag_adjustment
        ),
        "denominator_sidecar_adjusted_conventional_drag_bil": str(
            denominator_sidecar_adjusted_conventional_drag
        ),
        "denominator_sidecar_offset_ratio": str(denominator_sidecar_offset_ratio),
        "pension_contribution_relief_sidecar_bil": str(
            pension_contribution_relief_sidecar
        ),
        "retirement_insurance_yield_spend_sidecar_bil": str(
            retirement_insurance_yield_spend_sidecar
        ),
        "pension_insurance_pass_through_lag_years_output": str(
            pension_insurance_pass_through_lag_years
        ),
        "assumption_mode_sidecar_status": (
            "active_sidecar_terms"
            if recipient_leakage_sidecar_drag_total
            or denominator_sidecar_drag_adjustment
            or pension_contribution_relief_sidecar
            or retirement_insurance_yield_spend_sidecar
            else "inactive_zero_sidecar_terms"
        ),
        "countervailing_total_bil": str(scalar_countervailing_total),
        "scalar_countervailing_total_bil": str(scalar_countervailing_total),
        "composition_only_countervailing_total_bil": str(
            composition_only_countervailing_total
        ),
        "total_scaled_countervailing_total_bil": str(total_scaled_countervailing_total),
        "targeted_attenuation_drag_basis": (
            "debt_state_drag_multiplier_scales_conventional_denominator_only;"
            "firm_cash_uses_firm_liquid_asset_stock_share_gdp;"
            "safe_asset_offset_uses_domestic_safe_interest_impulse;"
            "safe_asset_drag_uses_domestic_safe_interest_impulse;"
            "zero_credit_uses_zero_interest_credit_stock_share_gdp;"
            "safe_asset_drag_excluded_from_denominator_basis"
        ),
        "scalar_baseline_uses_split_targeted_attenuation": "false",
        "conventional_contractionary_anchor_bil": str(conventional_drag_anchor),
        "conventional_contractionary_effect_bil": str(conventional_drag),
        "borrowing_cost_drag_bil": str(borrowing_cost_drag),
        "credit_supply_drag_bil": str(credit_supply_drag),
        "asset_price_drag_bil": str(asset_price_drag),
        "expectations_drag_bil": str(expectations_drag),
        "exchange_rate_external_drag_bil": str(exchange_rate_external_drag),
        "denominator_share_sum": str(denominator_share_sum),
        "denominator_share_sum_status": denominator_share_sum_status,
        "split_denominator_total_drag_multiplier": str(total_drag_multiplier),
        "split_denominator_mode": (
            "composition_only"
            if total_drag_multiplier == Decimal("1")
            else "total_scaled"
        ),
        "composition_only_split_ratio": str(composition_only_split_ratio),
        "total_scaled_split_ratio": str(split_ratio),
        "split_denominator_conventional_drag_bil": str(split_denominator_drag),
        "ratewall_offset_ratio": str(ratio),
        "split_denominator_offset_ratio": str(split_ratio),
        "ratewall_offset_ratio_low_drag_sensitivity": str(upper_ratio),
        "ratewall_offset_ratio_high_drag_sensitivity": str(lower_ratio),
        "wall_hit_under_assumptions": "true" if ratio >= Decimal("1") else "false",
        "split_denominator_wall_hit_under_assumptions": (
            "true" if split_ratio >= Decimal("1") else "false"
        ),
        "wall_classification": classification,
        "split_denominator_wall_classification": split_classification,
        "denominator_model_comparison": (
            "classification_changes_under_split_denominator"
            if split_classification != classification
            else "classification_unchanged_under_split_denominator"
        ),
        "classification_change_driver": _classification_change_driver(
            scalar_classification=classification,
            composition_only_classification=composition_only_classification,
            split_classification=split_classification,
            total_drag_multiplier=total_drag_multiplier,
        ),
        "why_hit_or_nonhit": why,
        "decisive_margin_bil": str(scalar_countervailing_total - conventional_drag),
        "dominant_gross_interest_subchannel": dominant_gross_interest_subchannel,
        "dominant_net_countervailing_channel": dominant_net_countervailing_channel,
        "dominant_countervailing_channel": dominant_net_countervailing_channel,
        "required_countervailing_for_hit_bil": str(conventional_drag),
        "remaining_gap_to_wall_bil": str(
            max(conventional_drag - scalar_countervailing_total, Decimal("0"))
        ),
        "excess_over_wall_bil": str(
            max(scalar_countervailing_total - conventional_drag, Decimal("0"))
        ),
        "assumption_status": assumption.assumption_status,
        "source_status": assumption.source_status,
        "treasury_recipient_map_status": "assumption_mode_component_recipient_share",
        "iorb_recipient_map_status": "assumption_mode_component_recipient_share",
        "on_rrp_recipient_map_status": _on_rrp_recipient_map_status(
            on_rrp_demand_offset
        ),
        "current_remittance_capacity_status": _current_remittance_capacity_status(
            current_remittance_offset
        ),
        "future_remittance_timing_status": _future_remittance_timing_status(
            future_drag_offset
        ),
        "component_recipient_map_status": (
            "component_recipient_maps_assumption_mode_incomplete_not_incidence"
        ),
        "claim_boundary": "speculative_assumption_mode_not_empirical_threshold_date",
        "empirical_claim_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
    }


def frontier_row(result: dict[str, str]) -> dict[str, str]:
    """Summarize how close one assumption set is to the wall."""

    ratio = Decimal(result["ratewall_offset_ratio"])
    required_multiplier = (
        Decimal("1") / ratio if ratio > 0 else Decimal("0")
    )
    return {
        "assumption_set": result["assumption_set"],
        "horizon": result["horizon"],
        "wall_classification": result["wall_classification"],
        "wall_hit_under_assumptions": result["wall_hit_under_assumptions"],
        "ratewall_offset_ratio": result["ratewall_offset_ratio"],
        "required_countervailing_for_hit_bil": result[
            "required_countervailing_for_hit_bil"
        ],
        "remaining_gap_to_wall_bil": result["remaining_gap_to_wall_bil"],
        "excess_over_wall_bil": result["excess_over_wall_bil"],
        "required_countervailing_multiplier_for_hit": str(required_multiplier),
        "frontier_status": (
            "at_or_beyond_wall_under_assumptions"
            if ratio >= Decimal("1")
            else "below_wall_under_assumptions"
        ),
        "claim_boundary": result["claim_boundary"],
    }


def decomposition_rows(result: dict[str, str]) -> list[dict[str, str]]:
    """Return component rows for one solved assumption set."""

    component_map = {
        "treasury_interest_demand_offset": result[
            "treasury_interest_demand_offset_bil"
        ],
        "iorb_demand_offset": result["iorb_demand_offset_bil"],
        "on_rrp_demand_offset": result["on_rrp_demand_offset_bil"],
        "current_remittance_demand_offset": result[
            "current_remittance_demand_offset_bil"
        ],
        "future_remittance_drag_demand_offset": result[
            "future_remittance_drag_demand_offset_bil"
        ],
        "net_interest_demand_after_fiscal_tga_offsets": result[
            "net_interest_demand_offset_bil"
        ],
        "firm_cash_attenuation": result["firm_cash_attenuation_bil"],
        "safe_asset_allocation_offset": result["safe_asset_allocation_offset_bil"],
        "safe_asset_allocation_drag": result["safe_asset_allocation_drag_bil"],
        "zero_interest_credit_attenuation": result[
            "zero_interest_credit_attenuation_bil"
        ],
        "conventional_contractionary_effect": result[
            "conventional_contractionary_effect_bil"
        ],
    }
    countervailing_total = Decimal(result["countervailing_total_bil"])
    conventional_drag = Decimal(result["conventional_contractionary_effect_bil"])
    decisive_margin = Decimal(result["decisive_margin_bil"])
    return [
        {
            "assumption_set": result["assumption_set"],
            "horizon": result["horizon"],
            "component": component,
            "component_value_bil": value,
            "share_of_countervailing_total": str(
                Decimal(value) / countervailing_total
                if countervailing_total and component != "conventional_contractionary_effect"
                else Decimal("0")
            ),
            "share_of_conventional_drag": str(
                Decimal(value) / conventional_drag if conventional_drag else Decimal("0")
            ),
            "share_of_wall_gap_or_excess": str(
                Decimal(value) / abs(decisive_margin)
                if decisive_margin and component != "conventional_contractionary_effect"
                else Decimal("0")
            ),
            "component_role": (
                "benchmark_contractionary_effect"
                if component == "conventional_contractionary_effect"
                else (
                    "countervailing_drag"
                    if component == "safe_asset_allocation_drag"
                    else "countervailing_effect"
                )
            ),
            "decisive_channel_label": (
                "dominant_countervailing_channel"
                if component == result["dominant_net_countervailing_channel"]
                else "supporting_channel"
            ),
            "additivity_scope": (
                "denominator_benchmark"
                if component == "conventional_contractionary_effect"
                else (
                    "gross_subchannel_nonadditive"
                    if component
                    in {
                        "treasury_interest_demand_offset",
                        "iorb_demand_offset",
                        "on_rrp_demand_offset",
                        "current_remittance_demand_offset",
                        "future_remittance_drag_demand_offset",
                    }
                    else "net_additive_countervailing"
                )
            ),
            "claim_boundary": result["claim_boundary"],
        }
        for component, value in component_map.items()
    ]


def public_impulse_factorization_row(result: dict[str, str]) -> dict[str, str]:
    """Expose the factored public-impulse handles behind the compatibility field."""

    return {
        "assumption_set": result["assumption_set"],
        "horizon": result["horizon"],
        "public_impulse_multiplier": result["public_impulse_multiplier"],
        "public_impulse_multiplier_status": result["public_impulse_multiplier_status"],
        "public_debt_stock_scale": result["public_debt_stock_scale"],
        "treasury_repricing_speed_share": result["treasury_repricing_speed_share"],
        "rate_path_bps_year": result["rate_path_bps_year"],
        "treasury_repricing_pass_through": result[
            "treasury_repricing_pass_through"
        ],
        "fed_liability_stock_scale": result["fed_liability_stock_scale"],
        "iorb_pass_through_scale": result["iorb_pass_through_scale"],
        "on_rrp_pass_through_scale": result["on_rrp_pass_through_scale"],
        "current_remittance_timing_share": result["current_remittance_timing_share"],
        "future_remittance_drag_timing_share": result[
            "future_remittance_drag_timing_share"
        ],
        "future_remittance_drag_treatment": result[
            "future_remittance_drag_treatment"
        ],
        "treasury_factor_multiplier": result["treasury_factor_multiplier"],
        "iorb_factor_multiplier": result["iorb_factor_multiplier"],
        "on_rrp_factor_multiplier": result["on_rrp_factor_multiplier"],
        "remittance_current_factor_multiplier": result[
            "remittance_current_factor_multiplier"
        ],
        "remittance_future_factor_multiplier": result[
            "remittance_future_factor_multiplier"
        ],
        "treasury_interest_impulse_bil": result["treasury_interest_impulse_bil"],
        "iorb_interest_impulse_bil": result["iorb_interest_impulse_bil"],
        "on_rrp_interest_impulse_bil": result["on_rrp_interest_impulse_bil"],
        "current_remittance_state_bil": result["current_remittance_state_bil"],
        "current_remittance_positive_support_bil": result[
            "current_remittance_positive_support_bil"
        ],
        "current_remittance_negative_drag_bil": result[
            "current_remittance_negative_drag_bil"
        ],
        "current_remittance_reduction_bil": result[
            "current_remittance_reduction_bil"
        ],
        "future_remittance_drag_bil": result["future_remittance_drag_bil"],
        "private_recipient_cashflow_impulse_bil": result[
            "private_recipient_cashflow_impulse_bil"
        ],
        "claim_boundary": "public_impulse_factorization_assumption_mode_not_live_security_level_repricing",
    }


def flow_stage_decomposition_rows(result: dict[str, str]) -> list[dict[str, str]]:
    """Stage public cashflows, demand conversion, absorbers, and private attenuation."""

    staged = [
        (
            "mechanical_public_cashflows",
            "treasury_interest_impulse",
            result["treasury_interest_impulse_bil"],
            result["treasury_interest_impulse_bil"],
            result["treasury_interest_impulse_bil"],
            "factored_public_liability_cashflow",
            "gross_subchannel_nonadditive",
            "gross_nonadditive",
        ),
        (
            "mechanical_public_cashflows",
            "iorb_interest_impulse",
            result["iorb_interest_impulse_bil"],
            result["iorb_interest_impulse_bil"],
            result["iorb_interest_impulse_bil"],
            "factored_fed_liability_cashflow",
            "gross_subchannel_nonadditive",
            "gross_nonadditive",
        ),
        (
            "mechanical_public_cashflows",
            "on_rrp_interest_impulse",
            result["on_rrp_interest_impulse_bil"],
            result["on_rrp_interest_impulse_bil"],
            result["on_rrp_interest_impulse_bil"],
            "factored_fed_liability_cashflow",
            "gross_subchannel_nonadditive",
            "gross_nonadditive",
        ),
        (
            "recipient_demand_conversion",
            "treasury_interest_demand_offset",
            result["treasury_interest_demand_offset_bil"],
            result["treasury_interest_demand_offset_bil"],
            result["treasury_interest_demand_offset_bil"],
            "treasury_cashflow_times_recipient_demand_share",
            "gross_subchannel_nonadditive",
            "gross_nonadditive",
        ),
        (
            "recipient_demand_conversion",
            "iorb_demand_offset",
            result["iorb_demand_offset_bil"],
            result["iorb_demand_offset_bil"],
            result["iorb_demand_offset_bil"],
            "iorb_cashflow_times_recipient_demand_share",
            "gross_subchannel_nonadditive",
            "gross_nonadditive",
        ),
        (
            "recipient_demand_conversion",
            "on_rrp_demand_offset",
            result["on_rrp_demand_offset_bil"],
            result["on_rrp_demand_offset_bil"],
            result["on_rrp_demand_offset_bil"],
            "on_rrp_cashflow_times_recipient_demand_share",
            "gross_subchannel_nonadditive",
            "gross_nonadditive",
        ),
        (
            "recipient_demand_conversion",
            "current_remittance_demand_offset",
            result["current_remittance_demand_offset_bil"],
            result["current_remittance_demand_offset_bil"],
            result["current_remittance_demand_offset_bil"],
            "current_remittance_cashflow_times_current_demand_share",
            "gross_subchannel_nonadditive",
            "gross_nonadditive",
        ),
        (
            "recipient_demand_conversion",
            "future_remittance_drag_demand_offset",
            result["future_remittance_drag_demand_offset_bil"],
            result["future_remittance_drag_demand_offset_bil"],
            result["future_remittance_drag_demand_offset_bil"],
            "future_drag_demand_share_current_negative_offset",
            "net_interest_stage_subtraction",
            "included_via_net_interest_block",
        ),
        (
            "recipient_demand_conversion",
            "interest_demand_offset",
            result["interest_demand_offset_bil"],
            result["interest_demand_offset_bil"],
            result["interest_demand_offset_bil"],
            "recipient_demand_converted_interest_offset",
            "net_stage_basis",
            "included_via_net_interest_block",
        ),
        (
            "absorber_block",
            "fiscal_offset",
            result["fiscal_offset_bil"],
            result["fiscal_offset_bil"],
            result["fiscal_offset_bil"],
            result["absorber_basis"],
            "net_additive_countervailing_subtraction",
            "included_via_net_interest_block",
        ),
        (
            "absorber_block",
            "tga_liquidity_offset",
            result["tga_liquidity_offset_bil"],
            result["tga_liquidity_offset_bil"],
            result["tga_liquidity_offset_bil"],
            result["absorber_basis"],
            "net_additive_countervailing_subtraction",
            "included_via_net_interest_block",
        ),
        (
            "absorber_block",
            "net_interest_after_fiscal_tga_offsets",
            result["net_interest_after_fiscal_tga_offsets_bil"],
            result["net_interest_after_fiscal_tga_offsets_bil"],
            result["net_interest_after_fiscal_tga_offsets_bil"],
            "recipient_demand_converted_interest_offset_after_absorbers",
            "net_additive_countervailing",
            "direct_addition",
        ),
        (
            "private_attenuation_block",
            "firm_cash_attenuation",
            result["firm_cash_attenuation_bil"],
            result["firm_cash_attenuation_bil"],
            result["total_scaled_firm_cash_attenuation_bil"],
            "firm_liquid_asset_stock_share_gdp_rate_path_base",
            "net_additive_countervailing",
            "direct_addition",
        ),
        (
            "private_attenuation_block",
            "safe_asset_allocation_offset",
            result["safe_asset_allocation_offset_bil"],
            result["safe_asset_allocation_offset_bil"],
            result["safe_asset_allocation_offset_bil"],
            "domestic_safe_interest_impulse",
            "net_additive_countervailing",
            "direct_addition",
        ),
        (
            "private_attenuation_block",
            "safe_asset_allocation_drag",
            result["safe_asset_allocation_drag_bil"],
            result["safe_asset_allocation_drag_bil"],
            result["safe_asset_allocation_drag_bil"],
            "domestic_safe_interest_impulse",
            "net_additive_countervailing_subtraction",
            "included_as_subtraction",
        ),
        (
            "private_attenuation_block",
            "zero_interest_credit_attenuation",
            result["zero_interest_credit_attenuation_bil"],
            result["zero_interest_credit_attenuation_bil"],
            result["total_scaled_zero_interest_credit_attenuation_bil"],
            "zero_interest_credit_stock_share_gdp_rate_path_base",
            "net_additive_countervailing",
            "direct_addition",
        ),
    ]
    scalar_total = Decimal(result["scalar_countervailing_total_bil"])
    split_total = Decimal(result["total_scaled_countervailing_total_bil"])
    rows: list[dict[str, str]] = []
    for (
        stage,
        component,
        value,
        scalar_value,
        split_value,
        basis,
        scope,
        inclusion_scope,
    ) in staged:
        scalar_signed_value = Decimal(scalar_value)
        split_signed_value = Decimal(split_value)
        if inclusion_scope == "included_as_subtraction":
            scalar_signed_value = -scalar_signed_value
            split_signed_value = -split_signed_value
        elif inclusion_scope != "direct_addition":
            scalar_signed_value = Decimal("0")
            split_signed_value = Decimal("0")
        rows.append(
            {
            "assumption_set": result["assumption_set"],
            "horizon": result["horizon"],
            "stage": stage,
            "component": component,
            "component_value_bil": value,
            "reported_component_value_bil_default_scalar": value,
            "scalar_component_value_bil": scalar_value,
            "split_component_value_bil": split_value,
            "scalar_countervailing_total_bil": result["scalar_countervailing_total_bil"],
            "split_countervailing_total_bil": result[
                "total_scaled_countervailing_total_bil"
            ],
            "share_of_scalar_countervailing_total": str(
                scalar_signed_value / scalar_total if scalar_total else Decimal("0")
            ),
            "share_of_split_countervailing_total": str(
                split_signed_value / split_total if split_total else Decimal("0")
            ),
            "stage_basis": basis,
            "additivity_scope": scope,
            "numerator_inclusion_scope": inclusion_scope,
            "included_in_scalar_numerator": (
                "true"
                if inclusion_scope in {"direct_addition", "included_as_subtraction"}
                else "false"
            ),
            "included_in_split_numerator": (
                "true"
                if inclusion_scope in {"direct_addition", "included_as_subtraction"}
                else "false"
            ),
            "directly_added_to_final_numerator": (
                "true"
                if inclusion_scope in {"direct_addition", "included_as_subtraction"}
                else "false"
            ),
            "indirectly_enters_via_net_interest_block": (
                "true" if inclusion_scope == "included_via_net_interest_block" else "false"
            ),
            "memo_only_public_finance_timing": (
                "true"
                if inclusion_scope == "memo_only"
                or "memo" in basis
                or component == "future_public_finance_drag"
                else "false"
            ),
            "can_be_added_to_net_countervailing_total": (
                "true"
                if inclusion_scope in {"direct_addition", "included_as_subtraction"}
                else "false"
            ),
            "sign_convention": (
                "subtracts_from_countervailing_total"
                if inclusion_scope == "included_as_subtraction"
                else "adds_to_countervailing_total"
                if inclusion_scope == "direct_addition"
                else "subtracted_before_net_interest_floor"
                if inclusion_scope == "included_via_net_interest_block"
                and (
                    "subtraction" in scope
                    or component == "future_remittance_drag_demand_offset"
                )
                else "nonadditive_stage_basis"
            ),
            "floor_or_cap_applied": (
                "net_interest_floor_at_zero"
                if component == "net_interest_after_fiscal_tga_offsets"
                else "none"
            ),
            "claim_boundary": "flow_stage_decomposition_assumption_mode_not_incidence_or_fiscal_reaction_estimate",
        }
        )
    return rows


def gross_interest_subchannel_rows(result: dict[str, str]) -> list[dict[str, str]]:
    """Gross interest subchannels before net fiscal/TGA absorber staging."""

    rows = [
        (
            "treasury_interest",
            result["treasury_interest_impulse_bil"],
            result["treasury_interest_demand_share"],
            result["treasury_interest_demand_offset_bil"],
        ),
        (
            "iorb_interest",
            result["iorb_interest_impulse_bil"],
            result["iorb_recipient_demand_share"],
            result["iorb_demand_offset_bil"],
        ),
        (
            "on_rrp_interest",
            result["on_rrp_interest_impulse_bil"],
            result["on_rrp_recipient_demand_share"],
            result["on_rrp_demand_offset_bil"],
        ),
        (
            "current_remittance_reduction",
            result["current_remittance_state_bil"],
            result["current_remittance_demand_share"],
            result["current_remittance_demand_offset_bil"],
        ),
        (
            "future_remittance_drag",
            result["future_remittance_drag_bil"],
            result["future_remittance_drag_demand_share"],
            result["future_remittance_drag_demand_offset_bil"],
        ),
    ]
    return [
        {
            "assumption_set": result["assumption_set"],
            "horizon": result["horizon"],
            "gross_subchannel": name,
            "cashflow_bil": cashflow,
            "demand_conversion_share": share,
            "demand_offset_bil": offset,
            "additivity_scope": "gross_subchannel_nonadditive",
            "numerator_inclusion_scope": (
                "included_via_net_interest_block"
                if name == "future_remittance_drag"
                else "gross_nonadditive"
            ),
            "included_in_scalar_numerator": "false",
            "included_in_split_numerator": "false",
            "directly_added_to_final_numerator": "false",
            "indirectly_enters_via_net_interest_block": "true",
            "memo_only_public_finance_timing": (
                "true"
                if name in {"current_remittance_reduction", "future_remittance_drag"}
                else "false"
            ),
            "can_be_added_to_net_countervailing_total": "false",
            "sign_convention": (
                "subtracts_from_interest_demand_stage"
                if name == "future_remittance_drag"
                else "signed_remittance_state_positive_support_or_negative_drag"
                if name == "current_remittance_reduction"
                else "gross_positive_cashflow_before_absorbers"
            ),
            "floor_or_cap_applied": "none",
            "claim_boundary": "gross_interest_subchannels_not_final_countervailing_driver",
        }
        for name, cashflow, share, offset in rows
    ]


def public_finance_adjustment_rows(result: dict[str, str]) -> list[dict[str, str]]:
    """Fiscal, TGA, and remittance timing rows separated from gross subchannels."""

    rows = [
        (
            "fiscal_offset",
            result["fiscal_offset_bil"],
            result["fiscal_offset_share"],
            "included_via_net_interest_block",
        ),
        (
            "tga_liquidity_offset",
            result["tga_liquidity_offset_bil"],
            result["tga_liquidity_offset_share"],
            "included_via_net_interest_block",
        ),
        (
            "current_remittance_reduction",
            result["current_remittance_state_bil"],
            result["current_remittance_demand_share"],
            "memo_only",
        ),
        (
            "future_remittance_drag_demand_offset",
            result["future_remittance_drag_demand_offset_bil"],
            result["future_remittance_drag_demand_share"],
            "included_via_net_interest_block",
        ),
        (
            "future_public_finance_drag_residual_memo",
            result["future_public_finance_drag_bil"],
            str(Decimal("1") - Decimal(result["future_remittance_drag_demand_share"])),
            "memo_only",
        ),
        (
            "net_public_finance_adjustment",
            result["net_public_finance_adjustment_bil"],
            "not_a_current_numerator_share",
            "memo_only",
        ),
    ]
    return [
        {
            "assumption_set": result["assumption_set"],
            "horizon": result["horizon"],
            "adjustment_component": component,
            "adjustment_value_bil": value,
            "absorber_basis": result["absorber_basis"],
            "future_remittance_drag_treatment": result[
                "future_remittance_drag_treatment"
            ],
            "additivity_scope": "public_finance_timing_or_absorber_adjustment",
            "numerator_inclusion_scope": inclusion_scope,
            "current_numerator_share": current_numerator_share,
            "memo_residual_description": (
                "future_drag_residual_after_demand_share_is_memo_only"
                if component == "future_public_finance_drag_residual_memo"
                else "demand_share_portion_enters_current_offset_as_negative_term"
                if component == "future_remittance_drag_demand_offset"
                else "not_future_remittance_residual"
            ),
            "included_in_scalar_numerator": (
                "false"
            ),
            "included_in_split_numerator": (
                "false"
            ),
            "directly_added_to_final_numerator": "false",
            "indirectly_enters_via_net_interest_block": (
                "true"
                if inclusion_scope == "included_via_net_interest_block"
                else "false"
            ),
            "memo_only_public_finance_timing": (
                "true" if inclusion_scope == "memo_only" else "false"
            ),
            "can_be_added_to_net_countervailing_total": "false",
            "sign_convention": (
                "negative_current_demand_offset_inside_interest_stage"
                if component == "future_remittance_drag_demand_offset"
                else "signed_current_remittance_state_positive_or_negative"
                if component == "current_remittance_reduction"
                else "absorber_subtraction"
                if component in {"fiscal_offset", "tga_liquidity_offset"}
                else "memo_public_finance_timing"
            ),
            "floor_or_cap_applied": (
                "net_interest_floor_applied_after_fiscal_tga_absorbers"
                if component in {"fiscal_offset", "tga_liquidity_offset"}
                else "none"
            ),
            "claim_boundary": "public_finance_adjustment_assumption_mode_not_fiscal_reaction_estimate",
        }
        for component, value, current_numerator_share, inclusion_scope in rows
    ]


def net_countervailing_channel_rows(result: dict[str, str]) -> list[dict[str, str]]:
    """Final additive channels used in the scalar numerator."""

    scalar_total = Decimal(result["scalar_countervailing_total_bil"])
    split_total = Decimal(result["total_scaled_countervailing_total_bil"])
    rows = [
        (
            "net_interest_after_fiscal_tga_offsets",
            result["net_interest_after_fiscal_tga_offsets_bil"],
            result["net_interest_after_fiscal_tga_offsets_bil"],
        ),
        (
            "firm_cash_attenuation",
            result["firm_cash_attenuation_bil"],
            result["total_scaled_firm_cash_attenuation_bil"],
        ),
        (
            "safe_asset_allocation_offset",
            result["safe_asset_allocation_offset_bil"],
            result["safe_asset_allocation_offset_bil"],
        ),
        (
            "safe_asset_allocation_drag",
            str(-Decimal(result["safe_asset_allocation_drag_bil"])),
            str(-Decimal(result["safe_asset_allocation_drag_bil"])),
        ),
        (
            "zero_interest_credit_attenuation",
            result["zero_interest_credit_attenuation_bil"],
            result["total_scaled_zero_interest_credit_attenuation_bil"],
        ),
        (
            "household_safe_yield_capture",
            result["household_safe_yield_capture_offset_bil"],
            result["household_safe_yield_capture_offset_bil"],
        ),
        (
            "deposit_mmf_substitution_offset",
            result["deposit_mmf_substitution_offset_bil"],
            result["deposit_mmf_substitution_offset_bil"],
        ),
        (
            "deposit_mmf_substitution_drag",
            str(-Decimal(result["deposit_mmf_substitution_drag_bil"])),
            str(-Decimal(result["total_scaled_deposit_mmf_substitution_drag_bil"])),
        ),
        (
            "firm_liquid_asset_cushion",
            result["firm_liquid_asset_cushion_offset_bil"],
            result["total_scaled_firm_liquid_asset_cushion_offset_bil"],
        ),
        (
            "firm_rollover_pressure_drag",
            str(-Decimal(result["firm_rollover_pressure_drag_bil"])),
            str(-Decimal(result["total_scaled_firm_rollover_pressure_drag_bil"])),
        ),
    ]
    diagnostic_only_channels = {
        "firm_liquid_asset_cushion",
        "firm_rollover_pressure_drag",
    }
    output_rows: list[dict[str, str]] = []
    for channel, value, split_value in rows:
        diagnostic_only = channel in diagnostic_only_channels
        scalar_additive_value = "0" if diagnostic_only else value
        split_additive_value = "0" if diagnostic_only else split_value
        output_rows.append(
            {
                "assumption_set": result["assumption_set"],
                "horizon": result["horizon"],
                "net_channel": channel,
                "channel_value_bil": value,
                "reported_component_value_bil_default_scalar": value,
                "scalar_channel_value_bil": scalar_additive_value,
                "split_channel_value_bil": split_additive_value,
                "scalar_countervailing_total_bil": result[
                    "scalar_countervailing_total_bil"
                ],
                "split_countervailing_total_bil": result[
                    "total_scaled_countervailing_total_bil"
                ],
                "share_of_countervailing_total": str(
                    Decimal(scalar_additive_value) / scalar_total
                    if scalar_total
                    else Decimal("0")
                ),
                "share_of_scalar_countervailing_total": str(
                    Decimal(scalar_additive_value) / scalar_total
                    if scalar_total
                    else Decimal("0")
                ),
                "share_of_split_countervailing_total": str(
                    Decimal(split_additive_value) / split_total
                    if split_total
                    else Decimal("0")
                ),
                "additivity_scope": (
                    "diagnostic_owner_gated_nonadditive"
                    if diagnostic_only
                    else "net_additive_countervailing"
                ),
                "numerator_inclusion_scope": (
                    "diagnostic_only_owner_gated"
                    if diagnostic_only
                    else (
                        "included_as_subtraction"
                        if channel == "safe_asset_allocation_drag"
                        else "direct_addition"
                    )
                ),
                "dominant_net_channel_flag": (
                    "dominant_net_countervailing_channel"
                    if not diagnostic_only
                    and channel == result["dominant_net_countervailing_channel"]
                    else "supporting_net_channel"
                ),
                "directly_added_to_final_numerator": (
                    "false" if diagnostic_only else "true"
                ),
                "indirectly_enters_via_net_interest_block": (
                    "true"
                    if channel == "net_interest_after_fiscal_tga_offsets"
                    else "false"
                ),
                "memo_only_public_finance_timing": "false",
                "claim_boundary": (
                    "net_countervailing_channels_assumption_mode_not_empirical_incidence"
                ),
            }
        )
    return output_rows


def conventional_drag_decomposition_rows(result: dict[str, str]) -> list[dict[str, str]]:
    """Return split-denominator conventional-drag components."""

    scalar_drag = Decimal(result["conventional_contractionary_effect_bil"])
    split_drag = Decimal(result["split_denominator_conventional_drag_bil"])
    components = {
        "borrowing_cost_drag": result["borrowing_cost_drag_bil"],
        "credit_supply_drag": result["credit_supply_drag_bil"],
        "asset_price_drag": result["asset_price_drag_bil"],
        "expectations_drag": result["expectations_drag_bil"],
        "exchange_rate_external_drag": result["exchange_rate_external_drag_bil"],
    }
    rows: list[dict[str, str]] = []
    for component, value in components.items():
        contract = _conventional_drag_component_replacement_contract(component)
        scalar_component_value = (
            Decimal(value) * scalar_drag / split_drag if split_drag else Decimal("0")
        )
        rows.append(
            {
                "assumption_set": result["assumption_set"],
                "horizon": result["horizon"],
                "denominator_component": component,
                "component_value_bil": value,
                "component_value_basis": CONVENTIONAL_DRAG_COMPONENT_VALUE_BASIS,
                "headline_denominator_component_value_bil": str(
                    scalar_component_value
                ),
                "share_of_scalar_denominator": str(
                    scalar_component_value / scalar_drag
                    if scalar_drag
                    else Decimal("0")
                ),
                "share_of_split_denominator": str(
                    Decimal(value) / split_drag if split_drag else Decimal("0")
                ),
                "scalar_conventional_drag_bil": str(scalar_drag),
                "split_conventional_drag_bil": str(split_drag),
                "component_sum_check_bil": str(split_drag),
                "denominator_share_sum": result["denominator_share_sum"],
                "denominator_share_sum_status": result[
                    "denominator_share_sum_status"
                ],
                "split_denominator_total_drag_multiplier": result[
                    "split_denominator_total_drag_multiplier"
                ],
                "split_denominator_mode": result["split_denominator_mode"],
                "denominator_allocation_status": (
                    CONVENTIONAL_DRAG_DECOMPOSITION_STATUS
                ),
                "component_evidence_status": (
                    CONVENTIONAL_DRAG_COMPONENT_EVIDENCE_STATUS
                ),
                "incremental_drag_allowed": "false",
                "main_ratio_effect_requires_denominator_replacement": "true",
                "tdsp_current_demand_lens_role": contract[
                    "tdsp_current_demand_lens_role"
                ],
                "tdsp_current_demand_incremental_drag_allowed": "false",
                "tdsp_current_demand_overlap_rule": contract[
                    "tdsp_current_demand_overlap_rule"
                ],
                "enters_main_ratio": "false",
                "split_denominator_promotion_allowed": "false",
                "allowed_use": SPLIT_DENOMINATOR_ROBUSTNESS_ALLOWED_USE,
                "blocked_use": SPLIT_DENOMINATOR_ROBUSTNESS_BLOCKED_USE,
                "claim_boundary": SPLIT_DENOMINATOR_ROBUSTNESS_CLAIM_BOUNDARY,
            }
        )
    return rows


def conventional_drag_replacement_reallocation_contract_rows(
    result: dict[str, str],
) -> list[dict[str, str]]:
    """Return fail-closed research contracts for denominator component replacement."""

    rows: list[dict[str, str]] = []
    for decomposition in conventional_drag_decomposition_rows(result):
        component = decomposition["denominator_component"]
        contract = _conventional_drag_component_replacement_contract(component)
        rows.append(
            {
                "assumption_set": result["assumption_set"],
                "horizon": result["horizon"],
                "denominator_component": component,
                "research_target": contract["research_target"],
                "candidate_diagnostic_lens": contract["candidate_diagnostic_lens"],
                "headline_denominator_component_value_bil": decomposition[
                    "headline_denominator_component_value_bil"
                ],
                "split_denominator_component_value_bil": decomposition[
                    "component_value_bil"
                ],
                "share_of_scalar_denominator": decomposition[
                    "share_of_scalar_denominator"
                ],
                "share_of_split_denominator": decomposition[
                    "share_of_split_denominator"
                ],
                "current_model_role": contract["current_model_role"],
                "replacement_reallocation_status": contract[
                    "replacement_reallocation_status"
                ],
                "component_replacement_evidence_status": contract[
                    "component_replacement_evidence_status"
                ],
                "required_source_family": contract["required_source_family"],
                "required_evidence": contract["required_evidence"],
                "tdsp_role": contract["tdsp_role"],
                "share_reallocation_behaviorally_neutral": contract[
                    "share_reallocation_behaviorally_neutral"
                ],
                "sidecar_subbase_impact_review_required": contract[
                    "sidecar_subbase_impact_review_required"
                ],
                "sidecar_subbase_impact_boundary": contract[
                    "sidecar_subbase_impact_boundary"
                ],
                "additive_drag_allowed": contract["additive_drag_allowed"],
                "replacement_denominator_admitted": contract[
                    "replacement_denominator_admitted"
                ],
                "reallocation_admitted": contract["reallocation_admitted"],
                "main_ratio_effect_rule": contract["main_ratio_effect_rule"],
                "denominator_prior_update_allowed": contract[
                    "denominator_prior_update_allowed"
                ],
                "enters_main_ratio": contract["enters_main_ratio"],
                "canonical_ratio_entry": contract["canonical_ratio_entry"],
                "evidence_mode_enabled": contract["evidence_mode_enabled"],
                "split_denominator_promotion_allowed": contract[
                    "split_denominator_promotion_allowed"
                ],
                "formula_replacement_allowed": contract[
                    "formula_replacement_allowed"
                ],
                "main_offset_ratio_changed_this_tranche": contract[
                    "main_offset_ratio_changed_this_tranche"
                ],
                "dynamic_equation_changed_this_tranche": contract[
                    "dynamic_equation_changed_this_tranche"
                ],
                "allowed_use": contract["allowed_use"],
                "blocked_use": contract["blocked_use"],
                "claim_boundary": contract["claim_boundary"],
            }
        )
    return rows


def conventional_drag_replacement_reallocation_impact_rows(
    result: dict[str, str],
    *,
    candidate_lens: str = TDSP_IMPACT_CANDIDATE_LENS,
    proposed_effect: str = "reallocation",
) -> list[dict[str, str]]:
    """Return fail-closed impact rows for proposed denominator replacement work."""

    if candidate_lens != TDSP_IMPACT_CANDIDATE_LENS:
        raise ValueError(f"unsupported denominator replacement candidate: {candidate_lens}")
    if proposed_effect not in {"diagnostic", "replacement", "reallocation"}:
        raise ValueError(f"unsupported denominator replacement effect: {proposed_effect}")

    rows: list[dict[str, str]] = []
    for contract in conventional_drag_replacement_reallocation_contract_rows(result):
        component = contract["denominator_component"]
        is_borrowing_cost = component == "borrowing_cost_drag"
        rows.append(
            {
                "assumption_set": contract["assumption_set"],
                "horizon": contract["horizon"],
                "candidate_lens": candidate_lens,
                "proposed_effect": proposed_effect,
                "denominator_component": component,
                "component_scope_status": (
                    "candidate_lens_matches_borrowing_cost_drag_diagnostic_only"
                    if is_borrowing_cost
                    else "blocked_candidate_lens_outside_component_scope"
                ),
                "candidate_lens_scope_match": "true" if is_borrowing_cost else "false",
                "candidate_diagnostic_lens": contract["candidate_diagnostic_lens"],
                "research_target": contract["research_target"],
                "required_source_family": contract["required_source_family"],
                "required_evidence_before_effect": TDSP_IMPACT_REQUIRED_EVIDENCE,
                "impact_status": DENOMINATOR_REPLACEMENT_IMPACT_STATUS,
                "replacement_denominator_admitted": "false",
                "reallocation_admitted": "false",
                "additive_drag_allowed": "false",
                "headline_denominator_delta_bil": "0",
                "split_denominator_delta_bil": "0",
                "main_ratio_delta_bil": "0",
                "runtime_denominator_effect_allowed": "false",
                "main_ratio_effect_allowed": "false",
                "denominator_prior_update_allowed": "false",
                "enters_main_ratio": "false",
                "canonical_ratio_entry": "false",
                "evidence_mode_enabled": "false",
                "formula_replacement_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "main_offset_ratio_changed_this_tranche": "false",
                "dynamic_equation_changed_this_tranche": "false",
                "share_reallocation_behaviorally_neutral": "false",
                "sidecar_subbase_impact_review_required": (
                    "true" if proposed_effect == "reallocation" else "false"
                ),
                "sidecar_subbase_impact_rule": (
                    DENOMINATOR_REALLOCATION_SIDECAR_IMPACT_RULE
                    if proposed_effect == "reallocation"
                    else "not_applicable_no_share_reallocation_requested"
                ),
                "allowed_use": DENOMINATOR_REPLACEMENT_IMPACT_ALLOWED_USE,
                "blocked_use": DENOMINATOR_REPLACEMENT_IMPACT_BLOCKED_USE,
                "claim_boundary": (
                    "denominator_replacement_reallocation_impact_model_"
                    "not_runtime_admission"
                ),
            }
        )
    return rows


def split_denominator_comparison_row(result: dict[str, str]) -> dict[str, str]:
    """Compare scalar and split denominator classifications."""

    scalar_ratio = Decimal(result["ratewall_offset_ratio"])
    split_ratio = Decimal(result["split_denominator_offset_ratio"])
    driver = result["classification_change_driver"]
    driver_type = _classification_change_driver_type(driver)
    return {
        "assumption_set": result["assumption_set"],
        "horizon": result["horizon"],
        "scalar_conventional_drag_bil": result["conventional_contractionary_effect_bil"],
        "split_conventional_drag_bil": result[
            "split_denominator_conventional_drag_bil"
        ],
        "denominator_share_sum": result["denominator_share_sum"],
        "denominator_share_sum_status": result["denominator_share_sum_status"],
        "split_denominator_total_drag_multiplier": result[
            "split_denominator_total_drag_multiplier"
        ],
        "split_denominator_mode": result["split_denominator_mode"],
        "countervailing_total_bil": result["countervailing_total_bil"],
        "scalar_countervailing_total_bil": result["scalar_countervailing_total_bil"],
        "composition_only_countervailing_total_bil": result[
            "composition_only_countervailing_total_bil"
        ],
        "total_scaled_countervailing_total_bil": result[
            "total_scaled_countervailing_total_bil"
        ],
        "targeted_attenuation_drag_basis": result["targeted_attenuation_drag_basis"],
        "scalar_baseline_uses_split_targeted_attenuation": result[
            "scalar_baseline_uses_split_targeted_attenuation"
        ],
        "conventional_contractionary_anchor_bil": result[
            "conventional_contractionary_anchor_bil"
        ],
        "scalar_offset_ratio": result["ratewall_offset_ratio"],
        "composition_only_split_ratio": result["composition_only_split_ratio"],
        "total_scaled_split_ratio": result["total_scaled_split_ratio"],
        "split_denominator_offset_ratio": result["split_denominator_offset_ratio"],
        "scalar_wall_classification": result["wall_classification"],
        "split_denominator_wall_classification": result[
            "split_denominator_wall_classification"
        ],
        "scalar_wall_hit_under_assumptions": result["wall_hit_under_assumptions"],
        "split_denominator_wall_hit_under_assumptions": result[
            "split_denominator_wall_hit_under_assumptions"
        ],
        "ratio_change_split_minus_scalar": str(split_ratio - scalar_ratio),
        "classification_change_flag": result["denominator_model_comparison"],
        "classification_change_driver": driver,
        "classification_change_driver_type": driver_type,
        "promotion_status": "prototype_robustness_only",
        "dominant_denominator_component": _dominant_channel(
            {
                "borrowing_cost_drag": Decimal(result["borrowing_cost_drag_bil"]),
                "credit_supply_drag": Decimal(result["credit_supply_drag_bil"]),
                "asset_price_drag": Decimal(result["asset_price_drag_bil"]),
                "expectations_drag": Decimal(result["expectations_drag_bil"]),
                "exchange_rate_external_drag": Decimal(
                    result["exchange_rate_external_drag_bil"]
                ),
            }
        ),
        "interpretation": _split_denominator_interpretation(result),
        "enters_main_ratio": "false",
        "split_denominator_promotion_allowed": "false",
        "allowed_use": SPLIT_DENOMINATOR_ROBUSTNESS_ALLOWED_USE,
        "blocked_use": SPLIT_DENOMINATOR_ROBUSTNESS_BLOCKED_USE,
        "claim_boundary": SPLIT_DENOMINATOR_ROBUSTNESS_CLAIM_BOUNDARY,
        "empirical_claim_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
        "causal_financialization_claim_enabled": "false",
    }


def denominator_sensitivity_rows(result: dict[str, str]) -> list[dict[str, str]]:
    """Summarize denominator component sensitivity against scalar mode."""

    scalar_drag = Decimal(result["conventional_contractionary_effect_bil"])
    split_drag = Decimal(result["split_denominator_conventional_drag_bil"])
    change_driver = result["classification_change_driver"]
    change_driver_type = _classification_change_driver_type(change_driver)
    if change_driver_type == "total_drag_amplitude":
        decisive_channel = "split_denominator_total_drag_multiplier"
        component_interpretation = (
            "classification_change_is_total_drag_amplitude; component_rows_are_decomposition_only"
        )
    elif change_driver_type == "mixed_component_composition_and_total_amplitude":
        decisive_channel = "mixed_total_drag_amplitude_and_component_composition"
        component_interpretation = "mixed_amplitude_and_component_share_review"
    elif change_driver_type == "component_composition_or_targeted_attenuation":
        decisive_channel = "component_composition_or_targeted_attenuation"
        component_interpretation = "component_share_or_targeted_attenuation_review"
    else:
        decisive_channel = "no_classification_change"
        component_interpretation = "no_classification_change_component_rows_are_decomposition_only"
    components = {
        "borrowing_cost_drag_share": result["borrowing_cost_drag_bil"],
        "credit_supply_drag_share": result["credit_supply_drag_bil"],
        "asset_price_drag_share": result["asset_price_drag_bil"],
        "expectations_drag_share": result["expectations_drag_bil"],
        "exchange_rate_external_drag_share": result["exchange_rate_external_drag_bil"],
    }
    return [
        {
            "assumption_set": result["assumption_set"],
            "denominator_parameter": parameter,
            "component_value_bil": value,
            "component_share_of_scalar_drag": str(
                Decimal(value) / scalar_drag if scalar_drag else Decimal("0")
            ),
        "split_minus_scalar_drag_bil": str(split_drag - scalar_drag),
        "denominator_share_sum": result["denominator_share_sum"],
        "denominator_share_sum_status": result["denominator_share_sum_status"],
        "split_denominator_total_drag_multiplier": result[
            "split_denominator_total_drag_multiplier"
        ],
            "split_denominator_offset_ratio": result["split_denominator_offset_ratio"],
            "scalar_offset_ratio": result["ratewall_offset_ratio"],
            "classification_change_flag": result["denominator_model_comparison"],
            "classification_change_driver": change_driver,
            "classification_change_driver_type": change_driver_type,
            "decisive_denominator_channel": decisive_channel,
            "component_share_interpretation": component_interpretation,
            "claim_boundary": "denominator_sensitivity_assumption_mode_not_empirical_estimate",
        }
        for parameter, value in components.items()
    ]


def sensitivity_rows(
    *, assumption: RateWallAssumptionSet, solved: dict[str, str]
) -> list[dict[str, str]]:
    """Report low/base/high sensitivity handles for decisive assumptions."""

    handles = {
        "public_debt_stock_scale": assumption.public_debt_stock_scale,
        "treasury_repricing_speed_share": assumption.treasury_repricing_speed_share,
        "rate_path_bps_year": assumption.rate_path_bps_year,
        "treasury_repricing_pass_through": assumption.treasury_repricing_pass_through,
        "fed_liability_stock_scale": assumption.fed_liability_stock_scale,
        "iorb_pass_through_scale": assumption.iorb_pass_through_scale,
        "on_rrp_pass_through_scale": assumption.on_rrp_pass_through_scale,
        "treasury_interest_demand_share": assumption.treasury_interest_demand_share,
        "fiscal_offset_share": assumption.fiscal_offset_share,
        "firm_cash_attenuation_share": assumption.firm_cash_attenuation_share,
        "safe_asset_allocation_offset_share": (
            assumption.safe_asset_allocation_offset_share
        ),
        "safe_asset_allocation_drag_share": (
            assumption.safe_asset_allocation_drag_share
        ),
        "household_safe_asset_stock_share": assumption.household_safe_asset_stock_share,
        "household_safe_asset_access_conditioner": (
            assumption.household_safe_asset_access_conditioner
        ),
        "retail_safe_yield_pass_through_beta": assumption.retail_safe_yield_pass_through_beta,
        "household_safe_yield_current_spend_share": (
            assumption.household_safe_yield_current_spend_share
        ),
        "deposit_mmf_substitution_conditioner": (
            assumption.deposit_mmf_substitution_conditioner
        ),
        "deposit_mmf_substitution_drag_share": (
            assumption.deposit_mmf_substitution_drag_share
        ),
        "firm_liquid_asset_cushion_share": assumption.firm_liquid_asset_cushion_share,
        "firm_rollover_pressure_share": assumption.firm_rollover_pressure_share,
        "contractionary_drag_gdp_share": assumption.contractionary_drag_gdp_share,
        "debt_state_drag_multiplier": assumption.debt_state_drag_multiplier,
    }
    rows = []
    for parameter, value in handles.items():
        base = _nonnegative(value, parameter)
        low = max(base * Decimal("0.75"), Decimal("0"))
        high = base * Decimal("1.25")
        if parameter.endswith("_share"):
            high = min(high, Decimal("1"))
        rows.append(
            {
                "assumption_set": assumption.name,
                "parameter": parameter,
                "low_value": str(low),
                "base_value": str(base),
                "high_value": str(high),
                "base_wall_classification": solved["wall_classification"],
                "base_ratewall_offset_ratio": solved["ratewall_offset_ratio"],
                "claim_boundary": "sensitivity_handles_not_empirical_estimates",
            }
        )
    return rows


def parameter_frontier_rows(
    *,
    assumption: RateWallAssumptionSet,
    gdp_bil: NumberLike,
    treasury_interest_impulse_bil: NumberLike,
    iorb_interest_impulse_bil: NumberLike,
    on_rrp_interest_impulse_bil: NumberLike,
    current_remittance_reduction_bil: NumberLike,
    future_remittance_drag_bil: NumberLike,
) -> list[dict[str, str]]:
    """Solve one-parameter wall frontiers holding other assumptions fixed."""

    inputs = {
        "gdp_bil": gdp_bil,
        "treasury_interest_impulse_bil": treasury_interest_impulse_bil,
        "iorb_interest_impulse_bil": iorb_interest_impulse_bil,
        "on_rrp_interest_impulse_bil": on_rrp_interest_impulse_bil,
        "current_remittance_reduction_bil": current_remittance_reduction_bil,
        "future_remittance_drag_bil": future_remittance_drag_bil,
    }
    specs = (
        ("public_debt_stock_scale", Decimal("0"), Decimal("6"), "at_or_above"),
        ("treasury_repricing_speed_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("rate_path_bps_year", Decimal("0"), Decimal("400"), "at_or_above"),
        ("treasury_repricing_pass_through", Decimal("0"), Decimal("1"), "at_or_above"),
        ("fed_liability_stock_scale", Decimal("0"), Decimal("6"), "at_or_above"),
        ("iorb_pass_through_scale", Decimal("0"), Decimal("1"), "at_or_above"),
        ("on_rrp_pass_through_scale", Decimal("0"), Decimal("1"), "at_or_above"),
        ("treasury_interest_demand_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("iorb_recipient_demand_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("on_rrp_recipient_demand_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("current_remittance_timing_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("future_remittance_drag_timing_share", Decimal("0"), Decimal("1"), "at_or_below"),
        ("firm_cash_attenuation_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("safe_asset_allocation_offset_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("safe_asset_allocation_drag_share", Decimal("0"), Decimal("1"), "at_or_below"),
        ("household_safe_asset_stock_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("household_safe_asset_access_conditioner", Decimal("0"), Decimal("1"), "at_or_above"),
        ("retail_safe_yield_pass_through_beta", Decimal("0"), Decimal("1"), "at_or_above"),
        ("household_safe_yield_current_spend_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("deposit_mmf_substitution_conditioner", Decimal("0"), Decimal("1"), "at_or_above"),
        ("deposit_mmf_substitution_drag_share", Decimal("0"), Decimal("1"), "at_or_below"),
        ("firm_liquid_asset_cushion_share", Decimal("0"), Decimal("1"), "at_or_above"),
        ("firm_rollover_pressure_share", Decimal("0"), Decimal("1"), "at_or_below"),
        ("fiscal_offset_share", Decimal("0"), Decimal("1"), "at_or_below"),
        ("tga_liquidity_offset_share", Decimal("0"), Decimal("1"), "at_or_below"),
        ("contractionary_drag_gdp_share", Decimal("0.0001"), Decimal("0.02"), "at_or_below"),
        ("debt_state_drag_multiplier", Decimal("0.01"), Decimal("1"), "at_or_below"),
    )
    base = solve_assumption(assumption=assumption, **inputs)
    packs = {row["parameter"]: row for row in parameter_pack_rows()}
    rows = []
    for parameter, lower, upper, relation in specs:
        base_value = _parameter_value(assumption, parameter)
        threshold, status = _solve_parameter_threshold(
            assumption=assumption,
            parameter=parameter,
            lower=lower,
            upper=upper,
            relation=relation,
            inputs=inputs,
        )
        pack_low, pack_base, pack_high = _parameter_pack_bounds(parameter, packs)
        pack_status, within_pack = _threshold_pack_status(
            frontier_status=status,
            threshold=threshold,
            pack_low=pack_low,
            pack_high=pack_high,
        )
        gap = (
            abs(base_value - threshold)
            if threshold is not None
            else Decimal("999")
        )
        rows.append(
            {
                "assumption_set": assumption.name,
                "parameter": parameter,
                "base_value": str(base_value),
                "threshold_value": str(threshold) if threshold is not None else "",
                "condition_relation": relation,
                "frontier_status": status,
                "parameter_pack_low": str(pack_low) if pack_low is not None else "",
                "parameter_pack_base": str(pack_base) if pack_base is not None else "",
                "parameter_pack_high": str(pack_high) if pack_high is not None else "",
                "threshold_within_parameter_pack": (
                    "true" if within_pack else "false"
                ),
                "threshold_pack_status": pack_status,
                "base_ratewall_offset_ratio": base["ratewall_offset_ratio"],
                "wall_hit_under_base_assumptions": base["wall_hit_under_assumptions"],
                "distance_from_base_to_threshold": str(gap),
                "driver_rank_score": str(gap),
                "claim_boundary": "parameter_frontier_assumption_mode_not_empirical_estimate",
            }
        )
    return rows


def hit_fragility_frontier_rows(
    *,
    assumption: RateWallAssumptionSet,
    gdp_bil: NumberLike,
    treasury_interest_impulse_bil: NumberLike,
    iorb_interest_impulse_bil: NumberLike,
    on_rrp_interest_impulse_bil: NumberLike,
    current_remittance_reduction_bil: NumberLike,
    future_remittance_drag_bil: NumberLike,
) -> list[dict[str, str]]:
    """For hit rows, solve how far each assumption can relax before non-hit."""

    inputs = {
        "gdp_bil": gdp_bil,
        "treasury_interest_impulse_bil": treasury_interest_impulse_bil,
        "iorb_interest_impulse_bil": iorb_interest_impulse_bil,
        "on_rrp_interest_impulse_bil": on_rrp_interest_impulse_bil,
        "current_remittance_reduction_bil": current_remittance_reduction_bil,
        "future_remittance_drag_bil": future_remittance_drag_bil,
    }
    specs = (
        ("public_debt_stock_scale", Decimal("0"), "minimum_value_still_hits"),
        ("treasury_repricing_speed_share", Decimal("0"), "minimum_value_still_hits"),
        ("rate_path_bps_year", Decimal("0"), "minimum_value_still_hits"),
        ("treasury_repricing_pass_through", Decimal("0"), "minimum_value_still_hits"),
        ("fed_liability_stock_scale", Decimal("0"), "minimum_value_still_hits"),
        ("iorb_pass_through_scale", Decimal("0"), "minimum_value_still_hits"),
        ("on_rrp_pass_through_scale", Decimal("0"), "minimum_value_still_hits"),
        ("treasury_interest_demand_share", Decimal("0"), "minimum_value_still_hits"),
        ("iorb_recipient_demand_share", Decimal("0"), "minimum_value_still_hits"),
        ("on_rrp_recipient_demand_share", Decimal("0"), "minimum_value_still_hits"),
        ("current_remittance_timing_share", Decimal("0"), "minimum_value_still_hits"),
        ("future_remittance_drag_timing_share", Decimal("1"), "maximum_value_still_hits"),
        ("firm_cash_attenuation_share", Decimal("0"), "minimum_value_still_hits"),
        ("safe_asset_allocation_offset_share", Decimal("0"), "minimum_value_still_hits"),
        ("safe_asset_allocation_drag_share", Decimal("1"), "maximum_value_still_hits"),
        ("household_safe_asset_stock_share", Decimal("0"), "minimum_value_still_hits"),
        ("household_safe_asset_access_conditioner", Decimal("0"), "minimum_value_still_hits"),
        ("retail_safe_yield_pass_through_beta", Decimal("0"), "minimum_value_still_hits"),
        ("household_safe_yield_current_spend_share", Decimal("0"), "minimum_value_still_hits"),
        ("deposit_mmf_substitution_conditioner", Decimal("0"), "minimum_value_still_hits"),
        ("deposit_mmf_substitution_drag_share", Decimal("1"), "maximum_value_still_hits"),
        ("firm_liquid_asset_cushion_share", Decimal("0"), "minimum_value_still_hits"),
        ("firm_rollover_pressure_share", Decimal("1"), "maximum_value_still_hits"),
        ("fiscal_offset_share", Decimal("1"), "maximum_value_still_hits"),
        ("tga_liquidity_offset_share", Decimal("1"), "maximum_value_still_hits"),
        ("contractionary_drag_gdp_share", Decimal("0.02"), "maximum_value_still_hits"),
        ("debt_state_drag_multiplier", Decimal("1"), "maximum_value_still_hits"),
    )
    base = solve_assumption(assumption=assumption, **inputs)
    packs = {row["parameter"]: row for row in parameter_pack_rows()}
    rows: list[dict[str, str]] = []
    if base["wall_hit_under_assumptions"] != "true":
        return rows
    for parameter, stress_bound, frontier_direction in specs:
        base_value = _parameter_value(assumption, parameter)
        threshold, status = _solve_hit_fragility_threshold(
            assumption=assumption,
            parameter=parameter,
            base_value=base_value,
            stress_bound=stress_bound,
            inputs=inputs,
        )
        pack_low, pack_base, pack_high = _parameter_pack_bounds(parameter, packs)
        pack_status, within_pack = _threshold_pack_status(
            frontier_status=status,
            threshold=threshold,
            pack_low=pack_low,
            pack_high=pack_high,
        )
        rows.append(
            {
                "assumption_set": assumption.name,
                "parameter": parameter,
                "base_value": str(base_value),
                "fragility_threshold_value": (
                    str(threshold) if threshold is not None else ""
                ),
                "frontier_direction": frontier_direction,
                "frontier_status": status,
                "parameter_pack_low": str(pack_low) if pack_low is not None else "",
                "parameter_pack_base": str(pack_base) if pack_base is not None else "",
                "parameter_pack_high": str(pack_high) if pack_high is not None else "",
                "threshold_within_parameter_pack": (
                    "true" if within_pack else "false"
                ),
                "threshold_pack_status": pack_status,
                "base_ratewall_offset_ratio": base["ratewall_offset_ratio"],
                "distance_from_base_to_threshold": (
                    str(abs(base_value - threshold)) if threshold is not None else ""
                ),
                "claim_boundary": (
                    "hit_fragility_frontier_assumption_mode_not_empirical_threshold"
                ),
            }
        )
    return rows


def minimum_condition_rows(
    parameter_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Filter frontier rows to the most actionable conditions."""

    return [
        {
            "assumption_set": row["assumption_set"],
            "condition_parameter": row["parameter"],
            "condition_relation": row["condition_relation"],
            "minimum_or_maximum_value_to_hit_wall": row["threshold_value"],
            "frontier_status": row["frontier_status"],
            "parameter_pack_low": row["parameter_pack_low"],
            "parameter_pack_base": row["parameter_pack_base"],
            "parameter_pack_high": row["parameter_pack_high"],
            "threshold_within_parameter_pack": row[
                "threshold_within_parameter_pack"
            ],
            "threshold_pack_status": row["threshold_pack_status"],
            "base_ratewall_offset_ratio": row["base_ratewall_offset_ratio"],
            "claim_boundary": row["claim_boundary"],
        }
        for row in parameter_rows
        if row["frontier_status"]
        not in {"not_reachable_within_bounds", "already_hits_at_base"}
    ]


def frontier_driver_ranking_rows(
    parameter_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Rank frontier parameters by distance from the current assumption."""

    grouped: dict[str, list[dict[str, str]]] = {}
    for row in parameter_rows:
        if row["frontier_status"] == "already_hits_at_base":
            continue
        grouped.setdefault(row["assumption_set"], []).append(row)
    ranked = []
    for assumption_set, rows in grouped.items():
        ordered = sorted(
            rows,
            key=lambda row: (
                _threshold_pack_rank(row["threshold_pack_status"]),
                Decimal(row["driver_rank_score"] or "0"),
            ),
        )
        for rank, row in enumerate(ordered, start=1):
            ranked.append(
                {
                    "assumption_set": assumption_set,
                    "rank": str(rank),
                    "parameter": row["parameter"],
                    "base_value": row["base_value"],
                    "threshold_value": row["threshold_value"],
                    "distance_from_base_to_threshold": row[
                        "distance_from_base_to_threshold"
                    ],
                    "frontier_status": row["frontier_status"],
                    "parameter_pack_low": row["parameter_pack_low"],
                    "parameter_pack_base": row["parameter_pack_base"],
                    "parameter_pack_high": row["parameter_pack_high"],
                    "threshold_within_parameter_pack": row[
                        "threshold_within_parameter_pack"
                    ],
                    "threshold_pack_status": row["threshold_pack_status"],
                    "claim_boundary": row["claim_boundary"],
                }
            )
    return ranked


def regime_map_row(result: dict[str, str]) -> dict[str, str]:
    """Return a professor-facing regime grouping for one solved row."""

    ratio = Decimal(result["ratewall_offset_ratio"])
    if ratio >= Decimal("1"):
        regime_group = "wall_hit"
        narrative = "Countervailing effects equal or exceed conventional drag under assumptions."
    elif ratio >= Decimal("0.75"):
        regime_group = "near_wall"
        narrative = "Countervailing effects are close enough that small assumption changes can hit the wall."
    elif ratio >= Decimal("0.5"):
        regime_group = "materially_attenuated"
        narrative = "Conventional tightening still dominates, but the offset is economically material."
    else:
        regime_group = "robust_non_hit"
        narrative = "Conventional tightening dominates under this assumption set."
    return {
        "assumption_set": result["assumption_set"],
        "regime_group": regime_group,
        "chapter_regime_use_label": f"scalar_{regime_group}",
        "ratewall_offset_ratio": result["ratewall_offset_ratio"],
        "wall_hit_under_assumptions": result["wall_hit_under_assumptions"],
        "dominant_countervailing_channel": result["dominant_countervailing_channel"],
        "dominant_gross_interest_subchannel": result[
            "dominant_gross_interest_subchannel"
        ],
        "dominant_net_countervailing_channel": result[
            "dominant_net_countervailing_channel"
        ],
        "remaining_gap_to_wall_bil": result["remaining_gap_to_wall_bil"],
        "excess_over_wall_bil": result["excess_over_wall_bil"],
        "why_hit_or_nonhit": result["why_hit_or_nonhit"],
        "professor_facing_summary": narrative,
        "claim_boundary": result["claim_boundary"],
    }


def frontier_summary_rows(
    *,
    solved_rows: list[dict[str, str]],
    minimum_rows: list[dict[str, str]],
    driver_rows: list[dict[str, str]],
    hit_fragility_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Summarize the frontier in compact rows for writing and review."""

    driver_by_assumption = {
        row["assumption_set"]: row
        for row in driver_rows
        if row["rank"] == "1"
    }
    minimum_count: dict[str, int] = {}
    for row in minimum_rows:
        minimum_count[row["assumption_set"]] = (
            minimum_count.get(row["assumption_set"], 0) + 1
        )
    fragility_by_assumption: dict[str, dict[str, str]] = {}
    for row in hit_fragility_rows or []:
        if row["frontier_status"] not in {
            "fragility_threshold_found",
            "still_hits_at_solver_bound",
        }:
            continue
        current = fragility_by_assumption.get(row["assumption_set"])
        current_distance = (
            Decimal(current["distance_from_base_to_threshold"])
            if current and current.get("distance_from_base_to_threshold")
            else Decimal("999")
        )
        candidate_distance = (
            Decimal(row["distance_from_base_to_threshold"])
            if row.get("distance_from_base_to_threshold")
            else Decimal("999")
        )
        candidate_status_rank = (
            0 if row["frontier_status"] == "fragility_threshold_found" else 1
        )
        current_status_rank = (
            0
            if current and current.get("frontier_status") == "fragility_threshold_found"
            else 1
        )
        if current is None or (candidate_status_rank, candidate_distance) < (
            current_status_rank,
            current_distance,
        ):
            fragility_by_assumption[row["assumption_set"]] = row
    rows = []
    for result in solved_rows:
        is_hit = result["wall_hit_under_assumptions"] == "true"
        top_driver = (
            fragility_by_assumption.get(result["assumption_set"], {})
            if is_hit
            else driver_by_assumption.get(result["assumption_set"], {})
        )
        frontier_reference = (
            "ratewall_hit_fragility_frontier"
            if is_hit
            else "ratewall_parameter_frontier"
        )
        rows.append(
            {
                "assumption_set": result["assumption_set"],
                "wall_classification": result["wall_classification"],
                "prose_regime_group": _regime_group_from_ratio(
                    Decimal(result["ratewall_offset_ratio"])
                ),
                "ratewall_offset_ratio": result["ratewall_offset_ratio"],
                "wall_hit_under_assumptions": result["wall_hit_under_assumptions"],
                "dominant_countervailing_channel": result[
                    "dominant_countervailing_channel"
                ],
                "dominant_gross_interest_subchannel": result[
                    "dominant_gross_interest_subchannel"
                ],
                "dominant_net_countervailing_channel": result[
                    "dominant_net_countervailing_channel"
                ],
                "frontier_reference_table": frontier_reference,
                "top_frontier_parameter": top_driver.get("parameter", ""),
                "top_frontier_threshold": (
                    top_driver.get("fragility_threshold_value", "")
                    if is_hit
                    else top_driver.get("threshold_value", "")
                ),
                "top_frontier_status": top_driver.get("frontier_status", ""),
                "parameter_pack_low": top_driver.get("parameter_pack_low", ""),
                "parameter_pack_base": top_driver.get("parameter_pack_base", ""),
                "parameter_pack_high": top_driver.get("parameter_pack_high", ""),
                "threshold_within_parameter_pack": top_driver.get(
                    "threshold_within_parameter_pack", ""
                ),
                "threshold_pack_status": top_driver.get("threshold_pack_status", ""),
                "reachable_minimum_condition_count": str(
                    minimum_count.get(result["assumption_set"], 0)
                ),
                "why_hit_or_nonhit": result["why_hit_or_nonhit"],
                "claim_boundary": result["claim_boundary"],
            }
        )
    return rows


def parameter_pack_rows(path: Path | None = None) -> list[dict[str, str]]:
    """Load source/literature parameter packs for assumption-mode priors."""

    payload = _load_yaml(path or _default_parameter_pack_path())
    if payload.get("schema") != "ratewall.parameter_packs.v1":
        raise ValueError("parameter pack config must use schema ratewall.parameter_packs.v1")
    rows = payload.get("parameter_packs")
    if not isinstance(rows, list) or not rows:
        raise ValueError("parameter pack config must include parameter_packs")
    required = {
        "parameter",
        "channel",
        "unit",
        "low",
        "base",
        "high",
        "source_status",
        "rationale",
        "source_note",
        "literature_context",
        "evidence_needed",
        "review_priority",
        "model_use",
        "review_question",
        "plausibility_status",
    }
    out = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"parameter pack row {index} must be a mapping")
        missing = sorted(required - set(row))
        if missing:
            raise ValueError(
                f"parameter pack row {index} missing fields: {', '.join(missing)}"
            )
        parameter = str(row["parameter"])
        if parameter in seen:
            raise ValueError(f"duplicate parameter pack: {parameter}")
        seen.add(parameter)
        low = _nonnegative(row["low"], f"{parameter}.low")
        base = _nonnegative(row["base"], f"{parameter}.base")
        high = _nonnegative(row["high"], f"{parameter}.high")
        calibration_order = str(row.get("calibration_order", "ascending"))
        if calibration_order == "descending_attenuation":
            if not (low >= base >= high):
                raise ValueError(
                    f"parameter pack {parameter} must satisfy low >= base >= high"
                )
        elif not (low <= base <= high):
            raise ValueError(f"parameter pack {parameter} must satisfy low <= base <= high")
        if str(row["unit"]) == "share":
            for label, value in (("low", low), ("base", base), ("high", high)):
                _share(value, f"{parameter}.{label}")
        if parameter == "public_impulse_multiplier" and not (
            low == base == high == Decimal("1.00")
        ):
            raise ValueError(
                "public_impulse_multiplier is deprecated compatibility metadata; "
                "its parameter-pack low/base/high values must all be 1.00"
            )
        out.append(
            {
                "parameter": parameter,
                "channel": str(row["channel"]),
                "unit": str(row["unit"]),
                "low": str(low),
                "base": str(base),
                "high": str(high),
                "source_status": str(row["source_status"]),
                "rationale": str(row["rationale"]),
                "source_note": str(row.get("source_note", "")),
                "literature_context": str(row.get("literature_context", "")),
                "evidence_needed": str(row.get("evidence_needed", "")),
                "review_priority": str(row.get("review_priority", "medium")),
                "model_use": str(row.get("model_use", "")),
                "review_question": str(row.get("review_question", "")),
                "candidate_source_literature": str(
                    row.get("candidate_source_literature", "")
                ),
                "citation_handle": str(row.get("citation_handle", "")),
                "source_family": str(row.get("source_family", "")),
                "identification_design": str(row.get("identification_design", "")),
                "horizon_relevance": str(row.get("horizon_relevance", "")),
                "uncertainty_status": str(row.get("uncertainty_status", "")),
                "evidence_strength": str(
                    row.get("evidence_strength", "review_prior_not_source_backed")
                ),
                "prior_basis": str(
                    row.get(
                        "prior_basis",
                        "assumption_mode_range_pending_external_evidence_review",
                    )
                ),
                "external_review_status": str(
                    row.get("external_review_status", "not_externally_reviewed")
                ),
                "upgrade_gate": str(
                    row.get(
                        "upgrade_gate",
                        "requires_explicit_source_method_gate_and_fail_closed_tests",
                    )
                ),
                "evidence_upgrade_blocker": str(
                    row.get(
                        "evidence_upgrade_blocker",
                        "requires_explicit_source_method_gate_and_fail_closed_tests",
                    )
                ),
                "calibration_status": str(
                    row.get("calibration_status", "uncalibrated_assumption_context")
                ),
                "calibration_order": calibration_order,
                "calibration_distribution_shape": str(
                    row.get("calibration_distribution", {}).get("shape", "")
                    if isinstance(row.get("calibration_distribution"), dict)
                    else ""
                ),
                "calibration_low": str(
                    row.get("calibration_distribution", {}).get("low", "")
                    if isinstance(row.get("calibration_distribution"), dict)
                    else ""
                ),
                "calibration_base": str(
                    row.get("calibration_distribution", {}).get("base", "")
                    if isinstance(row.get("calibration_distribution"), dict)
                    else ""
                ),
                "calibration_high": str(
                    row.get("calibration_distribution", {}).get("high", "")
                    if isinstance(row.get("calibration_distribution"), dict)
                    else ""
                ),
                "calibration_formula": str(
                    row.get("calibration_distribution", {}).get("formula", "")
                    if isinstance(row.get("calibration_distribution"), dict)
                    else ""
                ),
                "source_gate_table": str(row.get("source_gate_table", "")),
                "allowed_model_use": str(row.get("allowed_model_use", row.get("model_use", ""))),
                "scenario_implied_only": str(
                    row.get("scenario_implied_only", "true")
                ).lower(),
                "forbidden_claim_risk": str(row.get("forbidden_claim_risk", "medium")),
                "plausibility_status": str(row["plausibility_status"]),
                "claim_boundary": str(
                    payload.get(
                        "claim_boundary",
                        "parameter_pack_context_not_empirical_threshold",
                    )
                ),
            }
        )
    return out


def _classification(ratio: Decimal) -> str:
    if ratio >= Decimal("1"):
        return "ratewall_hit_under_assumptions"
    if ratio >= Decimal("0.5"):
        return "materially_attenuated_under_assumptions"
    return "tightening_mostly_works_under_assumptions"


def _regime_group_from_ratio(ratio: Decimal) -> str:
    if ratio >= Decimal("1"):
        return "wall_hit"
    if ratio >= Decimal("0.75"):
        return "near_wall"
    if ratio >= Decimal("0.5"):
        return "materially_attenuated"
    return "robust_non_hit"


def _parameter_pack_bounds(
    parameter: str, packs: dict[str, dict[str, str]]
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    pack = packs.get(parameter)
    if not pack:
        return None, None, None
    return (
        Decimal(pack["low"]),
        Decimal(pack["base"]),
        Decimal(pack["high"]),
    )


def _threshold_pack_status(
    *,
    frontier_status: str,
    threshold: Decimal | None,
    pack_low: Decimal | None,
    pack_high: Decimal | None,
) -> tuple[str, bool]:
    if frontier_status == "already_hits_at_base":
        return "already_hits_at_base", True
    if frontier_status == "not_reachable_within_bounds" or threshold is None:
        return "not_reachable_even_at_solver_bound", False
    if pack_low is None or pack_high is None:
        return "no_parameter_pack", False
    if pack_low <= threshold <= pack_high:
        return "within_prior_pack", True
    return "mathematically_reachable_outside_prior_pack", False


def _threshold_pack_rank(status: str) -> int:
    order = {
        "already_hits_at_base": 0,
        "within_prior_pack": 1,
        "mathematically_reachable_outside_prior_pack": 2,
        "no_parameter_pack": 3,
        "not_reachable_even_at_solver_bound": 4,
    }
    return order.get(status, 5)


def _dominant_channel(values: dict[str, Decimal]) -> str:
    return max(values.items(), key=lambda item: item[1])[0]


def _on_rrp_recipient_map_status(on_rrp_demand_offset: Decimal) -> str:
    if abs(on_rrp_demand_offset) <= Decimal("0.001"):
        return "conditionally_active_on_rrp_reinflation"
    return "assumption_mode_component_recipient_share"


def _current_remittance_capacity_status(
    current_remittance_offset: Decimal,
) -> str:
    if current_remittance_offset == 0:
        return "conditionally_active_remittances_resume"
    return "signed_remittance_state_positive_support_live"


def _future_remittance_timing_status(future_drag_offset: Decimal) -> str:
    if future_drag_offset != 0:
        return "load_bearing_future_drag_current_demand_offset"
    return "conditionally_active_future_drag_timing"


def _why_label(*, hit: bool, dominant_channel: str, ratio: Decimal) -> str:
    clean_channel = dominant_channel.replace("_", " ")
    if hit:
        return (
            "The wall hits under this assumption set because "
            f"{clean_channel} and supporting offsets lift the offset ratio "
            f"to {ratio}."
        )
    return (
        "The wall does not hit under this assumption set because the "
        f"countervailing ratio is {ratio}; {clean_channel} is the largest "
        "offset, but conventional drag still dominates."
    )


def _split_denominator_interpretation(result: dict[str, str]) -> str:
    if (
        result["denominator_model_comparison"]
        == "classification_changes_under_split_denominator"
    ):
        return (
            "The split-denominator model changes the wall classification under "
            f"this assumption set through `{result['classification_change_driver']}`; "
            "review whether this is a total-drag-amplitude, component-composition, "
            "targeted-attenuation, or mixed robustness result before using the row "
            "in professor-facing prose."
        )
    return (
        "The split-denominator model leaves the wall classification unchanged "
        "under this assumption set; denominator composition affects the ratio "
        "but not the current regime label."
    )


def _denominator_share_sum(assumption: RateWallAssumptionSet) -> Decimal:
    return (
        _share(assumption.borrowing_cost_drag_share, "borrowing_cost_drag_share")
        + _share(assumption.credit_supply_drag_share, "credit_supply_drag_share")
        + _share(assumption.asset_price_drag_share, "asset_price_drag_share")
        + _share(assumption.expectations_drag_share, "expectations_drag_share")
        + _share(
            assumption.exchange_rate_external_drag_share,
            "exchange_rate_external_drag_share",
        )
    )


def _denominator_share_sum_status(share_sum: Decimal) -> str:
    return "shares_sum_to_one" if abs(share_sum - Decimal("1")) <= Decimal("0.0005") else "invalid_share_sum"


def _split_denominator_mode(assumption: RateWallAssumptionSet) -> str:
    total_multiplier = _nonnegative(
        assumption.split_denominator_total_drag_multiplier,
        "split_denominator_total_drag_multiplier",
    )
    return "composition_only" if total_multiplier == Decimal("1") else "total_scaled"


def _classification_change_driver(
    *,
    scalar_classification: str,
    composition_only_classification: str,
    split_classification: str,
    total_drag_multiplier: Decimal,
) -> str:
    if scalar_classification == split_classification:
        return "no_classification_change"
    composition_changes = composition_only_classification != scalar_classification
    total_scaled = total_drag_multiplier != Decimal("1")
    if composition_changes and total_scaled:
        return "composition_plus_total_drag"
    if total_scaled:
        return "total_drag_amplitude"
    if composition_changes:
        return "denominator_composition_or_targeted_attenuation"
    if split_classification != scalar_classification:
        return "denominator_composition_or_targeted_attenuation"
    return "no_classification_change"


def _classification_change_driver_type(driver: str) -> str:
    if driver == "no_classification_change":
        return "no_classification_change"
    if driver == "total_drag_amplitude":
        return "total_drag_amplitude"
    if driver == "composition_plus_total_drag":
        return "mixed_component_composition_and_total_amplitude"
    if driver == "denominator_composition_or_targeted_attenuation":
        return "component_composition_or_targeted_attenuation"
    return "unclassified_denominator_driver"


def _parameter_value(assumption: RateWallAssumptionSet, parameter: str) -> Decimal:
    return _nonnegative(getattr(assumption, parameter), parameter)


def _with_parameter(
    assumption: RateWallAssumptionSet,
    parameter: str,
    value: Decimal,
) -> RateWallAssumptionSet:
    updates = {parameter: value}
    if parameter == "fed_interest_demand_share":
        updates = {
            "fed_interest_demand_share": value,
            "iorb_recipient_demand_share": value,
            "on_rrp_recipient_demand_share": value,
            "current_remittance_demand_share": value,
            "future_remittance_drag_demand_share": value,
        }
    return replace(assumption, **updates)


def _solve_parameter_threshold(
    *,
    assumption: RateWallAssumptionSet,
    parameter: str,
    lower: Decimal,
    upper: Decimal,
    relation: str,
    inputs: dict[str, NumberLike],
) -> tuple[Decimal | None, str]:
    base = solve_assumption(assumption=assumption, **inputs)
    base_hit = base["wall_hit_under_assumptions"] == "true"
    if base_hit:
        return _parameter_value(assumption, parameter), "already_hits_at_base"
    if relation == "at_or_above" or relation == "context_only":
        high_result = solve_assumption(
            assumption=_with_parameter(assumption, parameter, upper),
            **inputs,
        )
        if high_result["wall_hit_under_assumptions"] != "true":
            return None, "not_reachable_within_bounds"
        lo = lower
        hi = upper
        for _ in range(48):
            mid = (lo + hi) / Decimal("2")
            result = solve_assumption(
                assumption=_with_parameter(assumption, parameter, mid),
                **inputs,
            )
            if result["wall_hit_under_assumptions"] == "true":
                hi = mid
            else:
                lo = mid
        return hi, "threshold_found"
    low_result = solve_assumption(
        assumption=_with_parameter(assumption, parameter, lower),
        **inputs,
    )
    if low_result["wall_hit_under_assumptions"] != "true":
        return None, "not_reachable_within_bounds"
    lo = lower
    hi = upper
    for _ in range(48):
        mid = (lo + hi) / Decimal("2")
        result = solve_assumption(
            assumption=_with_parameter(assumption, parameter, mid),
            **inputs,
        )
        if result["wall_hit_under_assumptions"] == "true":
            lo = mid
        else:
            hi = mid
    return lo, "threshold_found"


def _solve_hit_fragility_threshold(
    *,
    assumption: RateWallAssumptionSet,
    parameter: str,
    base_value: Decimal,
    stress_bound: Decimal,
    inputs: dict[str, NumberLike],
) -> tuple[Decimal | None, str]:
    base = solve_assumption(assumption=assumption, **inputs)
    if base["wall_hit_under_assumptions"] != "true":
        return None, "base_does_not_hit"
    stressed = solve_assumption(
        assumption=_with_parameter(assumption, parameter, stress_bound),
        **inputs,
    )
    if stressed["wall_hit_under_assumptions"] == "true":
        return stress_bound, "still_hits_at_solver_bound"
    lo = min(base_value, stress_bound)
    hi = max(base_value, stress_bound)
    if stress_bound < base_value:
        for _ in range(48):
            mid = (lo + hi) / Decimal("2")
            result = solve_assumption(
                assumption=_with_parameter(assumption, parameter, mid),
                **inputs,
            )
            if result["wall_hit_under_assumptions"] == "true":
                hi = mid
            else:
                lo = mid
        return hi, "fragility_threshold_found"
    for _ in range(48):
        mid = (lo + hi) / Decimal("2")
        result = solve_assumption(
            assumption=_with_parameter(assumption, parameter, mid),
            **inputs,
        )
        if result["wall_hit_under_assumptions"] == "true":
            lo = mid
        else:
            hi = mid
    return lo, "fragility_threshold_found"


def _nonnegative(value: NumberLike, field: str) -> Decimal:
    return require_nonnegative(to_decimal(value, field=field), field=field)


def _signed_decimal(value: NumberLike, field: str) -> Decimal:
    return to_decimal(value, field=field)


def _positive(value: NumberLike, field: str) -> Decimal:
    parsed = _nonnegative(value, field)
    if parsed <= 0:
        raise ValueError(f"{field} must be positive")
    return parsed


def _share(value: NumberLike, field: str) -> Decimal:
    parsed = _nonnegative(value, field)
    if parsed > Decimal("1"):
        raise ValueError(f"{field} must be between 0 and 1")
    return parsed


def load_ratewall_assumption_sets(path: Path | None = None) -> tuple[RateWallAssumptionSet, ...]:
    """Load editable assumption sets from YAML and validate schema/ranges."""

    payload = _load_yaml(path or _default_assumption_set_path())
    if payload.get("schema") != "ratewall.assumption_sets.v1":
        raise ValueError("assumption config must use schema ratewall.assumption_sets.v1")
    rows = payload.get("assumption_sets")
    if not isinstance(rows, list) or not rows:
        raise ValueError("assumption config must include assumption_sets")
    required = {
        "name",
        "description",
        "horizon",
        "policy_rate_bps",
        "public_impulse_multiplier",
        "public_debt_stock_scale",
        "treasury_repricing_speed_share",
        "rate_path_bps_year",
        "treasury_repricing_pass_through",
        "fed_liability_stock_scale",
        "iorb_pass_through_scale",
        "on_rrp_pass_through_scale",
        "current_remittance_timing_share",
        "future_remittance_drag_timing_share",
        "future_remittance_drag_treatment",
        "treasury_interest_demand_share",
        "fed_interest_demand_share",
        "iorb_recipient_demand_share",
        "on_rrp_recipient_demand_share",
        "current_remittance_demand_share",
        "future_remittance_drag_demand_share",
        "fiscal_offset_share",
        "tga_liquidity_offset_share",
        "firm_cash_attenuation_share",
        "safe_asset_allocation_offset_share",
        "safe_asset_allocation_drag_share",
        "zero_interest_credit_attenuation_share",
        "contractionary_drag_gdp_share",
        "borrowing_cost_drag_share",
        "credit_supply_drag_share",
        "asset_price_drag_share",
        "expectations_drag_share",
        "exchange_rate_external_drag_share",
        "split_denominator_total_drag_multiplier",
        "benchmark_uncertainty_share",
        "assumption_status",
        "source_status",
    }
    share_fields = {
        "treasury_interest_demand_share",
        "fed_interest_demand_share",
        "treasury_repricing_speed_share",
        "treasury_repricing_pass_through",
        "iorb_pass_through_scale",
        "on_rrp_pass_through_scale",
        "current_remittance_timing_share",
        "future_remittance_drag_timing_share",
        "iorb_recipient_demand_share",
        "on_rrp_recipient_demand_share",
        "current_remittance_demand_share",
        "future_remittance_drag_demand_share",
        "fiscal_offset_share",
        "tga_liquidity_offset_share",
        "firm_cash_attenuation_share",
        "safe_asset_allocation_offset_share",
        "safe_asset_allocation_drag_share",
        "zero_interest_credit_attenuation_share",
        "household_safe_asset_stock_share",
        "household_safe_asset_access_conditioner",
        "retail_safe_yield_pass_through_beta",
        "household_safe_yield_current_spend_share",
        "deposit_mmf_substitution_conditioner",
        "deposit_mmf_substitution_drag_share",
        "firm_liquid_asset_stock_share_gdp",
        "zero_interest_credit_stock_share_gdp",
        "firm_liquid_asset_cushion_share",
        "firm_rollover_pressure_share",
        "foreign_treasury_holder_leakage_share",
        "interest_income_tax_timing_leakage_share",
        "rate_sensitive_consumer_credit_stock_share_gdp",
        "consumer_credit_reprice_beta",
        "consumer_credit_cashflow_drag_conversion",
        "private_credit_ndfi_credit_drag_share",
        "denominator_sidecar_overlap_discount_share",
        "fixed_mortgage_payment_shield_share_of_household_borrowing_drag",
        "retirement_insurance_yield_spend_conversion_share",
        "borrowing_cost_drag_share",
        "credit_supply_drag_share",
        "asset_price_drag_share",
        "expectations_drag_share",
        "exchange_rate_external_drag_share",
        "benchmark_uncertainty_share",
    }
    nonnegative_fields = {
        "policy_rate_bps",
        "public_impulse_multiplier",
        "public_debt_stock_scale",
        "debt_state_drag_multiplier",
        "rate_path_bps_year",
        "fed_liability_stock_scale",
        "cre_refi_drag_gdp_share_per_100bp_year",
        "pension_contribution_relief_gdp_share_per_100bp_year",
        "pension_insurance_pass_through_lag_years",
        "contractionary_drag_gdp_share",
        "split_denominator_total_drag_multiplier",
    }
    assumptions: list[RateWallAssumptionSet] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"assumption row {index} must be a mapping")
        missing = sorted(required - set(row))
        if missing:
            raise ValueError(
                f"assumption row {index} missing fields: {', '.join(missing)}"
            )
        name = str(row["name"])
        if name in seen:
            raise ValueError(f"duplicate assumption set: {name}")
        seen.add(name)
        values: dict[str, object] = {
            "name": name,
            "description": str(row["description"]),
            "horizon": str(row["horizon"]),
            "assumption_status": str(row["assumption_status"]),
            "source_status": str(row["source_status"]),
            "future_remittance_drag_treatment": str(
                row["future_remittance_drag_treatment"]
            ),
            "editable_label": str(row.get("editable_label", name)),
            "unit_scope": str(row.get("unit_scope", "share_or_multiplier_unless_noted")),
            "claim_boundary": str(
                row.get(
                    "claim_boundary",
                    payload.get(
                        "claim_boundary",
                        "assumption_mode_speculative_not_empirical_threshold_date",
                    ),
                )
            ),
        }
        for field in share_fields:
            values[field] = _share(row.get(field, Decimal("0")), field)
        for field in nonnegative_fields:
            default = (
                Decimal("1")
                if field == "debt_state_drag_multiplier"
                else Decimal("0")
            )
            values[field] = _nonnegative(row.get(field, default), field)
        if values["public_impulse_multiplier"] != Decimal("1.00"):
            raise ValueError(
                f"assumption row {index} public_impulse_multiplier is deprecated "
                "compatibility metadata and must remain neutral at 1.00"
            )
        share_sum = (
            values["borrowing_cost_drag_share"]
            + values["credit_supply_drag_share"]
            + values["asset_price_drag_share"]
            + values["expectations_drag_share"]
            + values["exchange_rate_external_drag_share"]
        )
        if _denominator_share_sum_status(share_sum) != "shares_sum_to_one":
            raise ValueError(
                f"assumption row {index} denominator shares must sum to 1; "
                "use split_denominator_total_drag_multiplier for total-drag scaling"
            )
        assumptions.append(RateWallAssumptionSet(**values))
    return tuple(assumptions)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f"required RateWall config is missing: {path}")
    resolved = path.resolve()
    stat = resolved.stat()
    payload = _load_yaml_cached(str(resolved), stat.st_mtime_ns, stat.st_size)
    if not isinstance(payload, dict):
        raise ValueError(f"RateWall config must be a mapping: {path}")
    return payload


@lru_cache(maxsize=32)
def _load_yaml_cached(path: str, _mtime_ns: int, _size: int) -> object:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_config_path(filename: str) -> Path:
    repo_path = _repo_root() / "configs" / filename
    if repo_path.exists():
        return repo_path
    return Path(__file__).resolve().parents[1] / "configs" / filename


def _default_assumption_set_path() -> Path:
    return _default_config_path("ratewall_assumption_sets.yml")


def _default_parameter_pack_path() -> Path:
    return _default_config_path("ratewall_parameter_packs.yml")


DEFAULT_RATEWALL_ASSUMPTIONS: tuple[
    RateWallAssumptionSet, ...
] = load_ratewall_assumption_sets()
