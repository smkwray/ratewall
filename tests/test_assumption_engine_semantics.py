from dataclasses import replace
from decimal import Decimal

import pytest

from ratewall.accounting.assumption_engine import (
    DEFAULT_RATEWALL_ASSUMPTIONS,
    RateWallAssumptionSet,
    solve_assumption,
)

SOLVER_INPUTS = {
    "gdp_bil": Decimal("1000"),
    "treasury_interest_impulse_bil": Decimal("10"),
    "iorb_interest_impulse_bil": Decimal("5"),
    "on_rrp_interest_impulse_bil": Decimal("3"),
    "current_remittance_reduction_bil": Decimal("1"),
    "future_remittance_drag_bil": Decimal("1"),
}


def test_public_impulse_multiplier_is_neutral_compatibility_only() -> None:
    """The legacy public impulse multiplier is valid only as neutral metadata."""

    base_assumption = next(
        assumption
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
        if assumption.name == "base_current_100bps"
    )
    kwargs = {
        **SOLVER_INPUTS,
    }

    solved_one = solve_assumption(
        assumption=replace(base_assumption, public_impulse_multiplier=Decimal("1")),
        **kwargs,
    )
    assert solved_one["public_impulse_multiplier_status"].startswith(
        "deprecated_compatibility_field"
    )
    with pytest.raises(ValueError, match="public_impulse_multiplier"):
        solve_assumption(
            assumption=replace(
                base_assumption, public_impulse_multiplier=Decimal("9")
            ),
            **kwargs,
        )


def test_default_assumption_configs_keep_legacy_multiplier_neutral() -> None:
    """Configured v1 rows should not carry active-looking legacy multiplier values."""

    assert {
        Decimal(str(assumption.public_impulse_multiplier))
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
    } == {Decimal("1.00")}


def test_treasury_repricing_speed_and_pass_through_are_single_pass_factors() -> None:
    """Treasury timing speed and pass-through each enter the factor once."""

    base_assumption = next(
        assumption
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
        if assumption.name == "literature_calibrated_base"
    )
    assumption = replace(
        base_assumption,
        public_debt_stock_scale=Decimal("1.08"),
        treasury_repricing_speed_share=Decimal("0.55"),
        rate_path_bps_year=Decimal("100"),
        treasury_repricing_pass_through=Decimal("0.80"),
        treasury_interest_demand_share=Decimal("1"),
        foreign_treasury_holder_leakage_share=Decimal("0"),
        interest_income_tax_timing_leakage_share=Decimal("0"),
        fiscal_offset_share=Decimal("0"),
        tga_liquidity_offset_share=Decimal("0"),
        future_remittance_drag_demand_share=Decimal("0"),
        firm_cash_attenuation_share=Decimal("0"),
        safe_asset_allocation_offset_share=Decimal("0"),
        safe_asset_allocation_drag_share=Decimal("0"),
    )
    solved = solve_assumption(
        assumption=assumption,
        gdp_bil=Decimal("1000"),
        treasury_interest_impulse_bil=Decimal("10"),
        iorb_interest_impulse_bil=Decimal("0"),
        on_rrp_interest_impulse_bil=Decimal("0"),
        current_remittance_reduction_bil=Decimal("0"),
        future_remittance_drag_bil=Decimal("0"),
    )

    expected_factor = Decimal("1.08") * Decimal("0.55") * Decimal("1") * Decimal("0.80")
    assert Decimal(solved["treasury_factor_multiplier"]) == expected_factor
    assert Decimal(solved["treasury_interest_impulse_bil"]) == (
        Decimal("10") * expected_factor
    )
    assert Decimal(solved["treasury_interest_demand_offset_bil"]) == (
        Decimal("10") * expected_factor
    )


@pytest.mark.parametrize(
    ("rate_path_bps_year", "expected_scale"),
    (
        (Decimal("50"), Decimal("0.5")),
        (Decimal("100"), Decimal("1")),
        (Decimal("200"), Decimal("2")),
    ),
)
def test_rate_path_bps_year_scales_exposure_terms_and_denominator(
    rate_path_bps_year: Decimal,
    expected_scale: Decimal,
) -> None:
    """Bp-year exposure changes nominal flows, not the unit-normalized ratio."""

    base_assumption = next(
        assumption
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
        if assumption.name == "literature_calibrated_base"
    )
    assumption = replace(
        base_assumption,
        public_debt_stock_scale=Decimal("1"),
        treasury_repricing_speed_share=Decimal("1"),
        treasury_repricing_pass_through=Decimal("1"),
        fed_liability_stock_scale=Decimal("1"),
        iorb_pass_through_scale=Decimal("1"),
        on_rrp_pass_through_scale=Decimal("1"),
        current_remittance_timing_share=Decimal("1"),
        future_remittance_drag_timing_share=Decimal("1"),
        firm_liquid_asset_stock_share_gdp=Decimal("0.20"),
        zero_interest_credit_stock_share_gdp=Decimal("0.10"),
        rate_sensitive_consumer_credit_stock_share_gdp=Decimal("0.08"),
        consumer_credit_reprice_beta=Decimal("0.50"),
        consumer_credit_cashflow_drag_conversion=Decimal("0.25"),
        cre_refi_drag_gdp_share_per_100bp_year=Decimal("0.01"),
        pension_contribution_relief_gdp_share_per_100bp_year=Decimal("0.005"),
    )
    reference = solve_assumption(
        assumption=replace(assumption, rate_path_bps_year=Decimal("100")),
        **SOLVER_INPUTS,
    )
    solved = solve_assumption(
        assumption=replace(assumption, rate_path_bps_year=rate_path_bps_year),
        **SOLVER_INPUTS,
    )

    for field in (
        "treasury_interest_impulse_bil",
        "iorb_interest_impulse_bil",
        "on_rrp_interest_impulse_bil",
        "current_remittance_positive_support_bil",
        "future_remittance_drag_bil",
        "firm_cash_yield_base_bil",
        "zero_interest_credit_base_bil",
        "consumer_credit_drag_sidecar_bil",
        "cre_refi_drag_sidecar_bil",
        "pension_contribution_relief_sidecar_bil",
        "conventional_contractionary_anchor_bil",
        "conventional_contractionary_effect_bil",
        "split_denominator_conventional_drag_bil",
    ):
        assert Decimal(solved[field]) == Decimal(reference[field]) * expected_scale

    assert Decimal(solved["ratewall_offset_ratio"]) == Decimal(
        reference["ratewall_offset_ratio"]
    )


def test_policy_rate_bps_does_not_double_count_bps_year_exposure() -> None:
    """The integrated bp-year path is the model exposure scalar."""

    base_assumption = next(
        assumption
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
        if assumption.name == "literature_calibrated_base"
    )
    reference = solve_assumption(
        assumption=replace(
            base_assumption,
            policy_rate_bps=Decimal("100"),
            rate_path_bps_year=Decimal("100"),
        ),
        **SOLVER_INPUTS,
    )
    solved = solve_assumption(
        assumption=replace(
            base_assumption,
            policy_rate_bps=Decimal("200"),
            rate_path_bps_year=Decimal("100"),
        ),
        **SOLVER_INPUTS,
    )

    assert solved["policy_rate_bps"] == "200"
    for field in (
        "scalar_countervailing_total_bil",
        "conventional_contractionary_effect_bil",
        "ratewall_offset_ratio",
    ):
        assert Decimal(solved[field]) == Decimal(reference[field])


def test_zero_bps_year_exposure_is_zero_flow_not_division_error() -> None:
    """A zero integrated policy path has zero modeled flows."""

    base_assumption = next(
        assumption
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
        if assumption.name == "literature_calibrated_base"
    )
    solved = solve_assumption(
        assumption=replace(base_assumption, rate_path_bps_year=Decimal("0")),
        **SOLVER_INPUTS,
    )

    for field in (
        "scalar_countervailing_total_bil",
        "conventional_contractionary_effect_bil",
        "ratewall_offset_ratio",
        "ratewall_offset_ratio_low_drag_sensitivity",
        "ratewall_offset_ratio_high_drag_sensitivity",
    ):
        assert Decimal(solved[field]) == Decimal("0")


def test_signed_current_remittance_state_keeps_deferred_asset_negative() -> None:
    """Deferred-asset states must not become positive current support."""

    base_assumption = next(
        assumption
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
        if assumption.name == "base_current_100bps"
    )
    assumption = replace(
        base_assumption,
        current_remittance_demand_share=Decimal("0.03"),
        future_remittance_drag_demand_share=Decimal("0"),
        fiscal_offset_share=Decimal("0"),
        tga_liquidity_offset_share=Decimal("0"),
        interest_income_tax_timing_leakage_share=Decimal("0"),
    )
    solved = solve_assumption(
        assumption=assumption,
        gdp_bil=Decimal("1000"),
        treasury_interest_impulse_bil=Decimal("0"),
        iorb_interest_impulse_bil=Decimal("0"),
        on_rrp_interest_impulse_bil=Decimal("0"),
        current_remittance_reduction_bil=Decimal("0"),
        current_remittance_state_bil=Decimal("-1"),
        future_remittance_drag_bil=Decimal("0"),
    )

    assert Decimal(solved["current_remittance_state_bil"]) == Decimal("-1")
    assert Decimal(solved["signed_current_remittance_impact_bil"]) == Decimal("-1")
    assert Decimal(solved["current_remittance_positive_support_bil"]) == Decimal("0")
    assert Decimal(solved["current_remittance_negative_drag_bil"]) == Decimal("-1")
    assert Decimal(solved["current_remittance_reduction_bil"]) == Decimal("0")
    assert Decimal(solved["current_remittance_demand_offset_bil"]) == Decimal("-0.03")
    assert Decimal(solved["interest_demand_offset_bil"]) == Decimal("-0.03")
    assert Decimal(solved["net_interest_demand_offset_bil"]) == Decimal("0")


def test_positive_current_remittance_state_preserves_legacy_alias() -> None:
    base_assumption = next(
        assumption
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
        if assumption.name == "base_current_100bps"
    )
    assumption = replace(
        base_assumption,
        current_remittance_demand_share=Decimal("0.03"),
        future_remittance_drag_demand_share=Decimal("0"),
    )
    solved = solve_assumption(
        assumption=assumption,
        gdp_bil=Decimal("1000"),
        treasury_interest_impulse_bil=Decimal("0"),
        iorb_interest_impulse_bil=Decimal("0"),
        on_rrp_interest_impulse_bil=Decimal("0"),
        current_remittance_reduction_bil=Decimal("1"),
        future_remittance_drag_bil=Decimal("0"),
    )

    assert Decimal(solved["current_remittance_state_bil"]) == Decimal("1")
    assert Decimal(solved["current_remittance_positive_support_bil"]) == Decimal("1")
    assert Decimal(solved["current_remittance_negative_drag_bil"]) == Decimal("0")
    assert Decimal(solved["current_remittance_reduction_bil"]) == Decimal("1")
    assert Decimal(solved["current_remittance_demand_offset_bil"]) == Decimal("0.03")


def test_denominator_drag_change_does_not_create_countervailing_support() -> None:
    """Increasing only D must not mechanically add numerator support."""

    assumption = RateWallAssumptionSet(
        name="property_no_denominator_derived_offset",
        description="Property-test assumption.",
        horizon="1y",
        policy_rate_bps=Decimal("100"),
        public_impulse_multiplier=Decimal("1"),
        treasury_interest_demand_share=Decimal("0.05"),
        fed_interest_demand_share=Decimal("0"),
        iorb_recipient_demand_share=Decimal("0.03"),
        on_rrp_recipient_demand_share=Decimal("0.06"),
        current_remittance_demand_share=Decimal("0"),
        future_remittance_drag_demand_share=Decimal("0"),
        fiscal_offset_share=Decimal("0"),
        tga_liquidity_offset_share=Decimal("0"),
        firm_cash_attenuation_share=Decimal("0.10"),
        safe_asset_allocation_offset_share=Decimal("0.05"),
        safe_asset_allocation_drag_share=Decimal("0"),
        zero_interest_credit_attenuation_share=Decimal("0.20"),
        firm_liquid_asset_stock_share_gdp=Decimal("0.27"),
        zero_interest_credit_stock_share_gdp=Decimal("0.005"),
        contractionary_drag_gdp_share=Decimal("0.004"),
        borrowing_cost_drag_share=Decimal("0.35"),
        credit_supply_drag_share=Decimal("0.25"),
        asset_price_drag_share=Decimal("0.20"),
        expectations_drag_share=Decimal("0.10"),
        exchange_rate_external_drag_share=Decimal("0.10"),
        split_denominator_total_drag_multiplier=Decimal("1"),
        benchmark_uncertainty_share=Decimal("0"),
        assumption_status="assumption_mode_speculative",
        source_status="property_test",
    )
    low_drag = solve_assumption(assumption=assumption, **SOLVER_INPUTS)
    high_drag = solve_assumption(
        assumption=replace(
            assumption,
            contractionary_drag_gdp_share=Decimal("0.010"),
        ),
        **SOLVER_INPUTS,
    )

    assert Decimal(high_drag["conventional_contractionary_effect_bil"]) > Decimal(
        low_drag["conventional_contractionary_effect_bil"]
    )
    assert Decimal(high_drag["scalar_countervailing_total_bil"]) == Decimal(
        low_drag["scalar_countervailing_total_bil"]
    )
    assert Decimal(high_drag["ratewall_offset_ratio"]) < Decimal(
        low_drag["ratewall_offset_ratio"]
    )


def test_foreign_leakage_and_tax_timing_reduce_canonical_interest_support() -> None:
    """Recipient leakage should affect canonical net interest support, not only sidecars."""

    base_assumption = next(
        assumption
        for assumption in DEFAULT_RATEWALL_ASSUMPTIONS
        if assumption.name == "base_current_100bps"
    )
    clean = solve_assumption(
        assumption=replace(
            base_assumption,
            foreign_treasury_holder_leakage_share=Decimal("0"),
            interest_income_tax_timing_leakage_share=Decimal("0"),
        ),
        **SOLVER_INPUTS,
    )
    leaky = solve_assumption(
        assumption=replace(
            base_assumption,
            foreign_treasury_holder_leakage_share=Decimal("0.25"),
            interest_income_tax_timing_leakage_share=Decimal("0.10"),
        ),
        **SOLVER_INPUTS,
    )

    assert Decimal(leaky["net_interest_demand_offset_bil"]) < Decimal(
        clean["net_interest_demand_offset_bil"]
    )
    assert Decimal(leaky["scalar_countervailing_total_bil"]) < Decimal(
        clean["scalar_countervailing_total_bil"]
    )
    assert Decimal(leaky["ratewall_offset_ratio"]) < Decimal(
        clean["ratewall_offset_ratio"]
    )
