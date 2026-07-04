"""Conditional RateWall threshold and financialization-pressure accounting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ratewall.accounting.numbers import (
    NumberLike,
    require_nonnegative,
    require_positive,
    to_decimal,
)


CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE_LOW = Decimal("0.0035")
CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE = Decimal("0.00776")
CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE_HIGH = Decimal("0.0130")
CANONICAL_CONTRACTIONARY_DRAG_PP_GDP_LOW = (
    CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE_LOW * Decimal("100")
)
CANONICAL_CONTRACTIONARY_DRAG_PP_GDP = (
    CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE * Decimal("100")
)
CANONICAL_CONTRACTIONARY_DRAG_PP_GDP_HIGH = (
    CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE_HIGH * Decimal("100")
)


@dataclass(frozen=True)
class ThresholdScenarioAssumption:
    """Speculative scenario assumptions for threshold diagnostics.

    These inputs are intentionally explicit. They are not estimated behavioral
    parameters and must remain labeled as assumptions in generated artifacts.
    """

    name: str
    description: str
    maturity_mix: str
    ru_absorption_share: NumberLike
    du_outlay_share: NumberLike
    du_direct_absorption_share: NumberLike
    tga_offset_share: NumberLike
    fiscal_offset_share: NumberLike
    financial_retention_share: NumberLike
    contractionary_drag_gdp_share: NumberLike


DEFAULT_THRESHOLD_SCENARIOS: tuple[ThresholdScenarioAssumption, ...] = (
    ThresholdScenarioAssumption(
        name="short_bill_high_ru_absorption",
        description=(
            "Speculative fast-hit case: short financing, high RU absorption, "
            "high DU outlay pass-through, and low fiscal offset."
        ),
        maturity_mix="short_bill_financing",
        ru_absorption_share=Decimal("0.80"),
        du_outlay_share=Decimal("0.65"),
        du_direct_absorption_share=Decimal("0.10"),
        tga_offset_share=Decimal("0.05"),
        fiscal_offset_share=Decimal("0.10"),
        financial_retention_share=Decimal("0.70"),
        contractionary_drag_gdp_share=CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
    ),
    ThresholdScenarioAssumption(
        name="long_coupon_high_ru_absorption",
        description=(
            "Speculative locked-in burden case: longer issuance slows immediate "
            "repricing but keeps high RU absorption and persistent interest flows."
        ),
        maturity_mix="long_coupon_financing",
        ru_absorption_share=Decimal("0.70"),
        du_outlay_share=Decimal("0.55"),
        du_direct_absorption_share=Decimal("0.15"),
        tga_offset_share=Decimal("0.05"),
        fiscal_offset_share=Decimal("0.15"),
        financial_retention_share=Decimal("0.75"),
        contractionary_drag_gdp_share=CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
    ),
    ThresholdScenarioAssumption(
        name="high_du_absorption",
        description=(
            "Offsetting case: domestic nonbanks absorb more Treasury securities "
            "directly, reducing the RU-financed DU deposit channel."
        ),
        maturity_mix="mixed_financing",
        ru_absorption_share=Decimal("0.35"),
        du_outlay_share=Decimal("0.45"),
        du_direct_absorption_share=Decimal("0.45"),
        tga_offset_share=Decimal("0.05"),
        fiscal_offset_share=Decimal("0.20"),
        financial_retention_share=Decimal("0.45"),
        contractionary_drag_gdp_share=CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
    ),
    ThresholdScenarioAssumption(
        name="tga_build_offset",
        description=(
            "Operating-cash offset case: Treasury cash buildup absorbs a large "
            "share of the RU-financed deposit impulse."
        ),
        maturity_mix="mixed_financing",
        ru_absorption_share=Decimal("0.55"),
        du_outlay_share=Decimal("0.50"),
        du_direct_absorption_share=Decimal("0.10"),
        tga_offset_share=Decimal("0.45"),
        fiscal_offset_share=Decimal("0.20"),
        financial_retention_share=Decimal("0.50"),
        contractionary_drag_gdp_share=CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
    ),
    ThresholdScenarioAssumption(
        name="high_financial_retention",
        description=(
            "Financial-retention case: more interest income is retained in "
            "safe financial claims."
        ),
        maturity_mix="mixed_financing",
        ru_absorption_share=Decimal("0.60"),
        du_outlay_share=Decimal("0.55"),
        du_direct_absorption_share=Decimal("0.15"),
        tga_offset_share=Decimal("0.05"),
        fiscal_offset_share=Decimal("0.15"),
        financial_retention_share=Decimal("0.85"),
        contractionary_drag_gdp_share=CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
    ),
    ThresholdScenarioAssumption(
        name="high_fiscal_offset_low_retention",
        description=(
            "Delayed-hit case: high fiscal offset and lower financial retention "
            "reduce the expansionary public-liability channel."
        ),
        maturity_mix="mixed_financing",
        ru_absorption_share=Decimal("0.45"),
        du_outlay_share=Decimal("0.40"),
        du_direct_absorption_share=Decimal("0.20"),
        tga_offset_share=Decimal("0.10"),
        fiscal_offset_share=Decimal("0.55"),
        financial_retention_share=Decimal("0.25"),
        contractionary_drag_gdp_share=CANONICAL_CONTRACTIONARY_DRAG_GDP_SHARE,
    ),
)


def compute_threshold_row(
    *,
    scenario: ThresholdScenarioAssumption,
    horizon: str,
    months: NumberLike,
    gdp_bil: NumberLike,
    period_public_interest_impulse_bil: NumberLike,
    period_treasury_interest_impulse_bil: NumberLike,
    period_fed_interest_impulse_bil: NumberLike,
    source_status: str,
) -> dict[str, str]:
    """Compute one conditional RateWall threshold row."""

    months_dec = require_positive(to_decimal(months, field="months"), field="months")
    gdp = require_positive(to_decimal(gdp_bil, field="gdp_bil"), field="gdp_bil")
    public_impulse = require_nonnegative(
        to_decimal(
            period_public_interest_impulse_bil,
            field="period_public_interest_impulse_bil",
        ),
        field="period_public_interest_impulse_bil",
    )
    treasury_impulse = require_nonnegative(
        to_decimal(
            period_treasury_interest_impulse_bil,
            field="period_treasury_interest_impulse_bil",
        ),
        field="period_treasury_interest_impulse_bil",
    )
    fed_impulse = require_nonnegative(
        to_decimal(
            period_fed_interest_impulse_bil,
            field="period_fed_interest_impulse_bil",
        ),
        field="period_fed_interest_impulse_bil",
    )
    ru_share = _share(scenario.ru_absorption_share, "ru_absorption_share")
    du_share = _share(scenario.du_outlay_share, "du_outlay_share")
    du_absorption = _share(
        scenario.du_direct_absorption_share,
        "du_direct_absorption_share",
    )
    tga_offset = _share(scenario.tga_offset_share, "tga_offset_share")
    fiscal_offset = _share(scenario.fiscal_offset_share, "fiscal_offset_share")
    financial_retention = _share(
        scenario.financial_retention_share,
        "financial_retention_share",
    )
    contractionary_drag_share = require_nonnegative(
        to_decimal(
            scenario.contractionary_drag_gdp_share,
            field="contractionary_drag_gdp_share",
        ),
        field="contractionary_drag_gdp_share",
    )

    du_interest_outlays = public_impulse * du_share
    ru_financing_condition = public_impulse * ru_share * du_share
    du_absorption_offset = public_impulse * du_absorption
    tga_offset_amount = public_impulse * tga_offset
    fiscal_offset_amount = public_impulse * fiscal_offset
    deposit_pricing_income = Decimal("0")
    tdc_deposit_impulse = (
        du_interest_outlays
        - du_absorption_offset
        - tga_offset_amount
    )
    expansionary_offset = max(tdc_deposit_impulse, Decimal("0"))
    expansionary_offset_after_fiscal = max(
        expansionary_offset - fiscal_offset_amount,
        Decimal("0"),
    )
    contractionary_drag = gdp * contractionary_drag_share * months_dec / Decimal("12")
    offset_ratio = (
        expansionary_offset_after_fiscal / contractionary_drag
        if contractionary_drag
        else Decimal("0")
    )
    threshold_hit = offset_ratio >= Decimal("1")
    financial_retention_impulse = expansionary_offset_after_fiscal * financial_retention
    financialization_pressure = (
        financial_retention_impulse / gdp if gdp else Decimal("0")
    )
    dominant_channel = (
        "treasury_interest_outlays"
        if treasury_impulse >= fed_impulse
        else "fed_interest_payments"
    )
    return {
        "scenario": scenario.name,
        "scenario_description": scenario.description,
        "horizon": horizon,
        "months": str(months_dec),
        "horizon_years": str(months_dec / Decimal("12")),
        "maturity_mix_assumption": scenario.maturity_mix,
        "period_public_interest_impulse_bil": str(public_impulse),
        "period_treasury_interest_impulse_bil": str(treasury_impulse),
        "period_fed_interest_impulse_bil": str(fed_impulse),
        "assumed_contractionary_drag_gdp_share": str(contractionary_drag_share),
        "assumed_contractionary_drag_bil": str(contractionary_drag),
        "ru_absorption_share_assumption": str(ru_share),
        "du_outlay_share_assumption": str(du_share),
        "du_direct_absorption_share_assumption": str(du_absorption),
        "tga_offset_share_assumption": str(tga_offset),
        "ru_financing_condition_not_additive_bil": str(ru_financing_condition),
        "fiscal_offset_share_assumption": str(fiscal_offset),
        "financial_retention_share_assumption": str(financial_retention),
        "tdc_deposit_channel_impulse_bil": str(tdc_deposit_impulse),
        "deposit_pricing_income_context_bil": str(deposit_pricing_income),
        "fiscal_offset_amount_bil": str(fiscal_offset_amount),
        "expansionary_offset_after_fiscal_bil": str(expansionary_offset_after_fiscal),
        "offset_ratio_to_contractionary_benchmark": str(offset_ratio),
        "threshold_hit_under_assumptions": "true" if threshold_hit else "false",
        "dominant_public_channel": dominant_channel,
        "financial_retention_impulse_bil": str(financial_retention_impulse),
        "financialization_pressure_gdp_share": str(financialization_pressure),
        "source_status": source_status,
        "assumption_status": "speculative_scenario_assumptions",
        "claim_boundary": (
            "conditional_threshold_simulation_not_policy_failure_or_causal_claim"
        ),
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
        "financialization_causal_claim_enabled": "false",
    }


def _share(value: NumberLike, field: str) -> Decimal:
    parsed = require_nonnegative(to_decimal(value, field=field), field=field)
    if parsed > Decimal("1"):
        raise ValueError(f"{field} must be between 0 and 1")
    return parsed
