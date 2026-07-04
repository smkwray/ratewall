"""Treasury Deposit Component deposit-channel accounting.

This module keeps the TDC layer as accounting.  It does not estimate a
structural fiscal multiplier, a monetary-policy threshold, or final incidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ratewall.accounting.numbers import NumberLike, require_nonnegative, to_decimal


@dataclass(frozen=True)
class DepositUserTdcInputs:
    """Deposit-user perimeter identity inputs, in billions of dollars."""

    treasury_outlays_to_du: NumberLike
    treasury_receipts_from_du: NumberLike
    treasury_debt_service_to_du: NumberLike
    treasury_security_sales_du_to_ru: NumberLike
    treasury_security_sales_ru_to_du: NumberLike


@dataclass(frozen=True)
class ReserveSideTdcInputs:
    """Estimable reserve-side identity inputs, in billions of dollars."""

    net_treasury_sales_du_to_ru: NumberLike
    treasury_issuance_proceeds: NumberLike
    treasury_receipts_from_ru: NumberLike
    fed_remittances_to_treasury: NumberLike
    treasury_outlays_to_ru: NumberLike
    treasury_debt_service_to_ru: NumberLike
    delta_treasury_operating_cash: NumberLike


@dataclass(frozen=True)
class RateHikeTdcImpulseInputs:
    """Non-causal deposit-channel impulse assumptions, in billions of dollars."""

    extra_interest_outlays_to_du: NumberLike
    extra_debt_financing_by_ru_used_for_du_outlays: NumberLike
    du_financed_treasury_absorption: NumberLike
    delta_tga_or_toc: NumberLike
    leakage_or_unclassified_ru_flows: NumberLike = Decimal("0")


@dataclass(frozen=True)
class TreasuryAttributedDepositInputs:
    """Core TDC transaction perimeter inputs, in billions of dollars.

    RU means reserve user. DU means domestic nonbank deposit user. The identity
    separates deposit quantity creation from later deposit-interest demand
    conversion so bank Treasury income and deposit interest are not double
    counted.
    """

    ru_secondary_treasury_purchase_from_du: NumberLike
    ru_primary_treasury_purchase: NumberLike
    treasury_spend_to_du_from_ru_financing: NumberLike
    treasury_spend_to_ru_from_ru_financing: NumberLike
    delta_tga_from_ru_financing: NumberLike
    du_direct_treasury_absorption: NumberLike
    bank_treasury_interest_income: NumberLike
    deposit_pass_through_beta: NumberLike
    tdc_deposit_rate_bps: NumberLike
    deposit_interest_current_spend_share: NumberLike
    bank_retained_margin_current_spend_share: NumberLike = Decimal("0")


@dataclass(frozen=True)
class TdcCurrentDemandSupportInputs:
    """Canonical TDC current-demand support chain inputs, in billions."""

    tdc_change_ex_overlap_bil: NumberLike
    tdc_materialization_beta: NumberLike
    deposit_current_demand_share: NumberLike
    empirical_claim_enabled: bool = False
    policy_failure_claim_enabled: bool = False
    pricing_output_enabled: bool = False
    incidence_claim_enabled: bool = False
    welfare_claim_enabled: bool = False
    tax_output_enabled: bool = False
    mpc_output_enabled: bool = False
    holder_allocation_enabled: bool = False
    reset_calendar_construction_enabled: bool = False
    raw_rate_shock_enabled: bool = False
    causal_financialization_claim_enabled: bool = False


@dataclass(frozen=True)
class TdcScenarioAssumption:
    """Scenario shares applied to a public-interest impulse."""

    name: str
    description: str
    du_interest_recipient_share: NumberLike
    ru_financing_for_du_outlay_share: NumberLike
    du_financed_absorption_share: NumberLike
    tga_toc_offset_share: NumberLike
    leakage_share: NumberLike = Decimal("0")


DEFAULT_TDC_SCENARIOS: tuple[TdcScenarioAssumption, ...] = (
    TdcScenarioAssumption(
        name="ru_finances_du_outlays",
        description=(
            "Illustrative accounting case: RU absorption avoids DU direct "
            "Treasury absorption while DU outlays and operating cash are explicit."
        ),
        du_interest_recipient_share=Decimal("0.50"),
        ru_financing_for_du_outlay_share=Decimal("1.00"),
        du_financed_absorption_share=Decimal("0.00"),
        tga_toc_offset_share=Decimal("0.00"),
    ),
    TdcScenarioAssumption(
        name="mixed_financing_partial_du_absorption",
        description=(
            "Mixed accounting case: some DU interest receipts, RU absorption "
            "is tracked as a financing condition, and some DU absorption of "
            "Treasury securities offsets deposits."
        ),
        du_interest_recipient_share=Decimal("0.50"),
        ru_financing_for_du_outlay_share=Decimal("0.50"),
        du_financed_absorption_share=Decimal("0.25"),
        tga_toc_offset_share=Decimal("0.00"),
    ),
    TdcScenarioAssumption(
        name="tga_build_offsets_ru_financing",
        description=(
            "Offset case: RU absorption exists as a financing condition, but "
            "a Treasury operating-cash build absorbs the deposit effect."
        ),
        du_interest_recipient_share=Decimal("0.50"),
        ru_financing_for_du_outlay_share=Decimal("0.50"),
        du_financed_absorption_share=Decimal("0.00"),
        tga_toc_offset_share=Decimal("0.50"),
    ),
    TdcScenarioAssumption(
        name="du_absorption_dominates",
        description=(
            "Negative accounting case: DU absorption and leakage exceed the "
            "RU-financed DU outlay leg."
        ),
        du_interest_recipient_share=Decimal("0.25"),
        ru_financing_for_du_outlay_share=Decimal("0.25"),
        du_financed_absorption_share=Decimal("0.75"),
        tga_toc_offset_share=Decimal("0.00"),
        leakage_share=Decimal("0.10"),
    ),
)


def compute_deposit_user_tdc(inputs: DepositUserTdcInputs) -> Decimal:
    """Compute the DU TDC identity.

    Positive values mean the measured Treasury-attributed component adds to
    domestic nonbank deposits on this perimeter.
    """

    outlays_to_du = _nonnegative(inputs.treasury_outlays_to_du, "treasury_outlays_to_du")
    receipts_from_du = _nonnegative(
        inputs.treasury_receipts_from_du, "treasury_receipts_from_du"
    )
    debt_service_to_du = _nonnegative(
        inputs.treasury_debt_service_to_du, "treasury_debt_service_to_du"
    )
    sales_du_to_ru = _nonnegative(
        inputs.treasury_security_sales_du_to_ru, "treasury_security_sales_du_to_ru"
    )
    sales_ru_to_du = _nonnegative(
        inputs.treasury_security_sales_ru_to_du, "treasury_security_sales_ru_to_du"
    )
    return outlays_to_du - receipts_from_du + debt_service_to_du + sales_du_to_ru - sales_ru_to_du


def compute_reserve_side_tdc(inputs: ReserveSideTdcInputs) -> Decimal:
    """Compute the reserve-side TDC identity."""

    return (
        _decimal(inputs.net_treasury_sales_du_to_ru, "net_treasury_sales_du_to_ru")
        + _nonnegative(inputs.treasury_issuance_proceeds, "treasury_issuance_proceeds")
        + _nonnegative(inputs.treasury_receipts_from_ru, "treasury_receipts_from_ru")
        + _decimal(inputs.fed_remittances_to_treasury, "fed_remittances_to_treasury")
        - _nonnegative(inputs.treasury_outlays_to_ru, "treasury_outlays_to_ru")
        - _nonnegative(inputs.treasury_debt_service_to_ru, "treasury_debt_service_to_ru")
        - _decimal(inputs.delta_treasury_operating_cash, "delta_treasury_operating_cash")
    )


def compute_rate_hike_tdc_impulse(inputs: RateHikeTdcImpulseInputs) -> Decimal:
    """Compute the non-causal rate-hike TDC deposit-channel impulse."""

    _decimal(
        inputs.extra_debt_financing_by_ru_used_for_du_outlays,
        "extra_debt_financing_by_ru_used_for_du_outlays",
    )
    return (
        _decimal(inputs.extra_interest_outlays_to_du, "extra_interest_outlays_to_du")
        - _decimal(inputs.du_financed_treasury_absorption, "du_financed_treasury_absorption")
        - _decimal(inputs.delta_tga_or_toc, "delta_tga_or_toc")
        - _decimal(
            inputs.leakage_or_unclassified_ru_flows,
            "leakage_or_unclassified_ru_flows",
        )
    )


def compute_treasury_attributed_deposit_component(
    inputs: TreasuryAttributedDepositInputs,
) -> dict[str, Decimal | str]:
    """Compute the canonical TDC transaction identity.

    The returned terms distinguish:
    * bank/RU secondary Treasury purchases from DU sellers, which credit DU
      deposits immediately;
    * bank/RU primary issuance purchases, which create DU deposits only when
      Treasury subsequently spends to DU rather than retaining proceeds in TGA
      or spending to RU;
    * bank-held Treasury interest, split between deposit pass-through and bank
      retained margin.
    """

    secondary_purchase = _nonnegative(
        inputs.ru_secondary_treasury_purchase_from_du,
        "ru_secondary_treasury_purchase_from_du",
    )
    primary_purchase = _nonnegative(
        inputs.ru_primary_treasury_purchase,
        "ru_primary_treasury_purchase",
    )
    spend_to_du = _nonnegative(
        inputs.treasury_spend_to_du_from_ru_financing,
        "treasury_spend_to_du_from_ru_financing",
    )
    spend_to_ru = _nonnegative(
        inputs.treasury_spend_to_ru_from_ru_financing,
        "treasury_spend_to_ru_from_ru_financing",
    )
    delta_tga = _nonnegative(
        inputs.delta_tga_from_ru_financing,
        "delta_tga_from_ru_financing",
    )
    du_absorption = _nonnegative(
        inputs.du_direct_treasury_absorption,
        "du_direct_treasury_absorption",
    )
    bank_interest = _nonnegative(
        inputs.bank_treasury_interest_income,
        "bank_treasury_interest_income",
    )
    deposit_beta = _share(inputs.deposit_pass_through_beta, "deposit_pass_through_beta")
    deposit_rate = _nonnegative(inputs.tdc_deposit_rate_bps, "tdc_deposit_rate_bps") / Decimal(
        "10000"
    )
    current_spend_share = _share(
        inputs.deposit_interest_current_spend_share,
        "deposit_interest_current_spend_share",
    )
    retained_spend_share = _share(
        inputs.bank_retained_margin_current_spend_share,
        "bank_retained_margin_current_spend_share",
    )
    primary_purchase_residual = primary_purchase - spend_to_du - spend_to_ru - delta_tga
    primary_deposit_component = spend_to_du
    tdc_deposit_quantity = secondary_purchase + primary_deposit_component - du_absorption
    deposit_interest_from_tdc_quantity = max(tdc_deposit_quantity, Decimal("0")) * deposit_rate
    bank_interest_passed_to_deposits = bank_interest * deposit_beta
    bank_retained_margin = bank_interest - bank_interest_passed_to_deposits
    deposit_interest_current_demand = (
        deposit_interest_from_tdc_quantity + bank_interest_passed_to_deposits
    ) * current_spend_share
    bank_retained_margin_current_demand = bank_retained_margin * retained_spend_share
    total_current_demand_support = (
        deposit_interest_current_demand + bank_retained_margin_current_demand
    )
    return {
        "secondary_purchase_deposit_creation_bil": secondary_purchase,
        "primary_purchase_bil": primary_purchase,
        "treasury_spend_to_du_deposit_creation_bil": primary_deposit_component,
        "treasury_spend_to_ru_bil": spend_to_ru,
        "delta_tga_from_ru_financing_bil": delta_tga,
        "primary_purchase_unspent_or_unclassified_bil": primary_purchase_residual,
        "du_direct_treasury_absorption_bil": du_absorption,
        "tdc_deposit_quantity_component_bil": tdc_deposit_quantity,
        "tdc_deposit_interest_on_quantity_bil": deposit_interest_from_tdc_quantity,
        "bank_treasury_interest_income_bil": bank_interest,
        "bank_interest_passed_to_deposits_bil": bank_interest_passed_to_deposits,
        "bank_retained_margin_bil": bank_retained_margin,
        "deposit_interest_current_demand_support_bil": deposit_interest_current_demand,
        "bank_retained_margin_current_demand_support_bil": (
            bank_retained_margin_current_demand
        ),
        "total_tdc_current_demand_support_bil": total_current_demand_support,
        "deposit_pass_through_beta": deposit_beta,
        "tdc_deposit_rate_bps": deposit_rate * Decimal("10000"),
        "deposit_interest_current_spend_share": current_spend_share,
        "bank_retained_margin_current_spend_share": retained_spend_share,
        "claim_boundary": "tdc_canonical_accounting_component_not_incidence_or_mpc_output",
        "empirical_claim_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
        "tax_output_enabled": "false",
        "mpc_output_enabled": "false",
        "holder_allocation_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "raw_rate_shock_enabled": "false",
        "causal_financialization_claim_enabled": "false",
    }


def compute_tdc_current_demand_support(
    inputs: TdcCurrentDemandSupportInputs,
) -> dict[str, Decimal | str]:
    """Compute N_TDC = delta TDC ex overlap times beta times chi."""

    forbidden_switches = {
        "empirical_claim_enabled": inputs.empirical_claim_enabled,
        "policy_failure_claim_enabled": inputs.policy_failure_claim_enabled,
        "pricing_output_enabled": inputs.pricing_output_enabled,
        "incidence_claim_enabled": inputs.incidence_claim_enabled,
        "welfare_claim_enabled": inputs.welfare_claim_enabled,
        "tax_output_enabled": inputs.tax_output_enabled,
        "mpc_output_enabled": inputs.mpc_output_enabled,
        "holder_allocation_enabled": inputs.holder_allocation_enabled,
        "reset_calendar_construction_enabled": inputs.reset_calendar_construction_enabled,
        "raw_rate_shock_enabled": inputs.raw_rate_shock_enabled,
        "causal_financialization_claim_enabled": (
            inputs.causal_financialization_claim_enabled
        ),
    }
    enabled = [name for name, value in forbidden_switches.items() if value]
    if enabled:
        raise ValueError(
            "TDC current-demand support forbids promoted switches: " + ",".join(enabled)
        )

    ex_overlap = _decimal(
        inputs.tdc_change_ex_overlap_bil,
        "tdc_change_ex_overlap_bil",
    )
    beta = _nonnegative(inputs.tdc_materialization_beta, "tdc_materialization_beta")
    chi = _share(inputs.deposit_current_demand_share, "deposit_current_demand_share")
    net_deposits = ex_overlap * beta
    support = net_deposits * chi
    return {
        "tdc_change_ex_overlap_bil": ex_overlap,
        "tdc_materialization_beta": beta,
        "deposit_current_demand_share": chi,
        "derived_beta_times_chi": beta * chi,
        "tdc_net_materialized_deposits_bil": net_deposits,
        "tdc_current_demand_support_bil": support,
        "tdc_materialization_beta_above_unit_interval": str(beta > 1).lower(),
        "claim_boundary": (
            "tdc_support_labeled_assumption_mode_prior_chain_not_causal_"
            "incidence_welfare_tax_or_runtime_regime_classifier"
        ),
        **{name: "false" for name in forbidden_switches},
    }


def apply_tdc_scenario(
    *,
    period_public_interest_impulse_bil: NumberLike,
    assumption: TdcScenarioAssumption,
) -> dict[str, Decimal | str]:
    """Apply transparent scenario shares to a period public-interest impulse."""

    base = _nonnegative(
        period_public_interest_impulse_bil,
        "period_public_interest_impulse_bil",
    )
    du_interest_share = _share(
        assumption.du_interest_recipient_share,
        "du_interest_recipient_share",
    )
    ru_financing_share = _share(
        assumption.ru_financing_for_du_outlay_share,
        "ru_financing_for_du_outlay_share",
    )
    du_absorption_share = _share(
        assumption.du_financed_absorption_share,
        "du_financed_absorption_share",
    )
    tga_share = _share(assumption.tga_toc_offset_share, "tga_toc_offset_share")
    leakage_share = _share(assumption.leakage_share, "leakage_share")
    impulse_inputs = RateHikeTdcImpulseInputs(
        extra_interest_outlays_to_du=base * du_interest_share,
        extra_debt_financing_by_ru_used_for_du_outlays=base * ru_financing_share,
        du_financed_treasury_absorption=base * du_absorption_share,
        delta_tga_or_toc=base * tga_share,
        leakage_or_unclassified_ru_flows=base * leakage_share,
    )
    deposit_impulse = compute_rate_hike_tdc_impulse(impulse_inputs)
    return {
        "scenario": assumption.name,
        "scenario_description": assumption.description,
        "period_public_interest_impulse_bil": base,
        "extra_interest_outlays_to_du_bil": impulse_inputs.extra_interest_outlays_to_du,
        "extra_debt_financing_by_ru_used_for_du_outlays_bil": (
            impulse_inputs.extra_debt_financing_by_ru_used_for_du_outlays
        ),
        "ru_financing_condition_not_additive_bil": (
            impulse_inputs.extra_debt_financing_by_ru_used_for_du_outlays
        ),
        "du_financed_treasury_absorption_bil": (
            impulse_inputs.du_financed_treasury_absorption
        ),
        "delta_tga_or_toc_bil": impulse_inputs.delta_tga_or_toc,
        "leakage_or_unclassified_ru_flows_bil": (
            impulse_inputs.leakage_or_unclassified_ru_flows
        ),
        "tdc_deposit_channel_impulse_bil": deposit_impulse,
        "claim_boundary": "tdc_accounting_scenario_not_causal_or_incidence_claim",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
    }


def _decimal(value: NumberLike, field: str) -> Decimal:
    return to_decimal(value, field=field)


def _nonnegative(value: NumberLike, field: str) -> Decimal:
    return require_nonnegative(to_decimal(value, field=field), field=field)


def _share(value: NumberLike, field: str) -> Decimal:
    parsed = _nonnegative(value, field)
    if parsed > 1:
        raise ValueError(f"{field} must be between 0 and 1")
    return parsed
