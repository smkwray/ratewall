from decimal import Decimal

import pytest

from ratewall.accounting.tdc_deposit_channel import (
    DEFAULT_TDC_SCENARIOS,
    DepositUserTdcInputs,
    RateHikeTdcImpulseInputs,
    ReserveSideTdcInputs,
    TdcCurrentDemandSupportInputs,
    TreasuryAttributedDepositInputs,
    apply_tdc_scenario,
    compute_deposit_user_tdc,
    compute_rate_hike_tdc_impulse,
    compute_reserve_side_tdc,
    compute_tdc_current_demand_support,
    compute_treasury_attributed_deposit_component,
)
from ratewall.accounting.ratewall_threshold import (
    DEFAULT_THRESHOLD_SCENARIOS,
    ThresholdScenarioAssumption,
    compute_threshold_row,
)


def test_deposit_user_identity_keeps_du_ru_security_flows_explicit() -> None:
    result = compute_deposit_user_tdc(
        DepositUserTdcInputs(
            treasury_outlays_to_du="500",
            treasury_receipts_from_du="410",
            treasury_debt_service_to_du="30",
            treasury_security_sales_du_to_ru="25",
            treasury_security_sales_ru_to_du="40",
        )
    )

    assert result == Decimal("105")


def test_reserve_side_identity_subtracts_treasury_operating_cash_change() -> None:
    result = compute_reserve_side_tdc(
        ReserveSideTdcInputs(
            net_treasury_sales_du_to_ru="15",
            treasury_issuance_proceeds="200",
            treasury_receipts_from_ru="10",
            fed_remittances_to_treasury="-5",
            treasury_outlays_to_ru="20",
            treasury_debt_service_to_ru="25",
            delta_treasury_operating_cash="40",
        )
    )

    assert result == Decimal("135")


def test_rate_hike_deposit_impulse_can_be_positive_or_negative() -> None:
    positive = compute_rate_hike_tdc_impulse(
        RateHikeTdcImpulseInputs(
            extra_interest_outlays_to_du="20",
            extra_debt_financing_by_ru_used_for_du_outlays="80",
            du_financed_treasury_absorption="10",
            delta_tga_or_toc="5",
        )
    )
    negative = compute_rate_hike_tdc_impulse(
        RateHikeTdcImpulseInputs(
            extra_interest_outlays_to_du="5",
            extra_debt_financing_by_ru_used_for_du_outlays="10",
            du_financed_treasury_absorption="40",
            delta_tga_or_toc="5",
            leakage_or_unclassified_ru_flows="5",
        )
    )

    assert positive == Decimal("5")
    assert negative == Decimal("-45")


def test_treasury_attributed_deposit_component_handles_secondary_purchase() -> None:
    result = compute_treasury_attributed_deposit_component(
        TreasuryAttributedDepositInputs(
            ru_secondary_treasury_purchase_from_du="100",
            ru_primary_treasury_purchase="0",
            treasury_spend_to_du_from_ru_financing="0",
            treasury_spend_to_ru_from_ru_financing="0",
            delta_tga_from_ru_financing="0",
            du_direct_treasury_absorption="0",
            bank_treasury_interest_income="0",
            deposit_pass_through_beta="0",
            tdc_deposit_rate_bps="500",
            deposit_interest_current_spend_share="0.2",
        )
    )

    assert result["secondary_purchase_deposit_creation_bil"] == Decimal("100")
    assert result["tdc_deposit_quantity_component_bil"] == Decimal("100")
    assert result["tdc_deposit_interest_on_quantity_bil"] == Decimal("5.00")
    assert result["deposit_interest_current_demand_support_bil"] == Decimal("1.000")


def test_treasury_attributed_deposit_component_tracks_primary_purchase_spend_tga() -> None:
    result = compute_treasury_attributed_deposit_component(
        TreasuryAttributedDepositInputs(
            ru_secondary_treasury_purchase_from_du="0",
            ru_primary_treasury_purchase="100",
            treasury_spend_to_du_from_ru_financing="70",
            treasury_spend_to_ru_from_ru_financing="10",
            delta_tga_from_ru_financing="20",
            du_direct_treasury_absorption="0",
            bank_treasury_interest_income="0",
            deposit_pass_through_beta="0",
            tdc_deposit_rate_bps="400",
            deposit_interest_current_spend_share="0.1",
        )
    )

    assert result["primary_purchase_bil"] == Decimal("100")
    assert result["treasury_spend_to_du_deposit_creation_bil"] == Decimal("70")
    assert result["treasury_spend_to_ru_bil"] == Decimal("10")
    assert result["delta_tga_from_ru_financing_bil"] == Decimal("20")
    assert result["primary_purchase_unspent_or_unclassified_bil"] == Decimal("0")
    assert result["tdc_deposit_quantity_component_bil"] == Decimal("70")


def test_treasury_attributed_deposit_component_splits_bank_interest() -> None:
    result = compute_treasury_attributed_deposit_component(
        TreasuryAttributedDepositInputs(
            ru_secondary_treasury_purchase_from_du="0",
            ru_primary_treasury_purchase="0",
            treasury_spend_to_du_from_ru_financing="0",
            treasury_spend_to_ru_from_ru_financing="0",
            delta_tga_from_ru_financing="0",
            du_direct_treasury_absorption="0",
            bank_treasury_interest_income="40",
            deposit_pass_through_beta="0.5",
            tdc_deposit_rate_bps="0",
            deposit_interest_current_spend_share="0.2",
            bank_retained_margin_current_spend_share="0.05",
        )
    )

    assert result["bank_interest_passed_to_deposits_bil"] == Decimal("20.0")
    assert result["bank_retained_margin_bil"] == Decimal("20.0")
    assert result["deposit_interest_current_demand_support_bil"] == Decimal("4.00")
    assert result["bank_retained_margin_current_demand_support_bil"] == Decimal("1.000")
    assert result["total_tdc_current_demand_support_bil"] == Decimal("5.000")
    assert result["empirical_claim_enabled"] == "false"
    assert result["policy_failure_claim_enabled"] == "false"
    assert result["pricing_output_enabled"] == "false"
    assert result["incidence_claim_enabled"] == "false"
    assert result["welfare_claim_enabled"] == "false"
    assert result["tax_output_enabled"] == "false"
    assert result["mpc_output_enabled"] == "false"
    assert result["holder_allocation_enabled"] == "false"
    assert result["reset_calendar_construction_enabled"] == "false"
    assert result["raw_rate_shock_enabled"] == "false"
    assert result["causal_financialization_claim_enabled"] == "false"


def test_tdc_current_demand_support_uses_ex_overlap_beta_times_chi() -> None:
    result = compute_tdc_current_demand_support(
        TdcCurrentDemandSupportInputs(
            tdc_change_ex_overlap_bil=Decimal("1299.17"),
            tdc_materialization_beta=Decimal("0.342"),
            deposit_current_demand_share=Decimal("0.12"),
        )
    )

    assert result["tdc_net_materialized_deposits_bil"] == Decimal("444.31614")
    assert result["tdc_current_demand_support_bil"] == Decimal("53.3179368")
    assert result["tdc_current_demand_support_bil"] != Decimal("193.5804")
    assert result["tdc_current_demand_support_bil"] != Decimal("444.31614")
    assert result["tdc_materialization_beta_above_unit_interval"] == "false"
    assert result["pricing_output_enabled"] == "false"
    assert result["incidence_claim_enabled"] == "false"
    assert result["mpc_output_enabled"] == "false"


def test_tdc_current_demand_support_flags_beta_above_one_and_rejects_switches() -> None:
    result = compute_tdc_current_demand_support(
        TdcCurrentDemandSupportInputs(
            tdc_change_ex_overlap_bil="-10",
            tdc_materialization_beta="1.2",
            deposit_current_demand_share="0.5",
        )
    )

    assert result["tdc_current_demand_support_bil"] == Decimal("-6.00")
    assert result["tdc_materialization_beta_above_unit_interval"] == "true"
    with pytest.raises(ValueError, match="between 0 and 1"):
        compute_tdc_current_demand_support(
            TdcCurrentDemandSupportInputs(
                tdc_change_ex_overlap_bil="10",
                tdc_materialization_beta="0.3",
                deposit_current_demand_share="1.01",
            )
        )
    with pytest.raises(ValueError, match="forbids promoted switches"):
        compute_tdc_current_demand_support(
            TdcCurrentDemandSupportInputs(
                tdc_change_ex_overlap_bil="10",
                tdc_materialization_beta="0.3",
                deposit_current_demand_share="0.1",
                pricing_output_enabled=True,
            )
        )


def test_tdc_scenarios_are_non_causal_and_fail_on_bad_shares() -> None:
    rows = [
        apply_tdc_scenario(
            period_public_interest_impulse_bil=Decimal("100"),
            assumption=assumption,
        )
        for assumption in DEFAULT_TDC_SCENARIOS
    ]

    assert {row["pricing_output_enabled"] for row in rows} == {"false"}
    assert {row["incidence_claim_enabled"] for row in rows} == {"false"}
    assert {row["welfare_claim_enabled"] for row in rows} == {"false"}
    assert {
        Decimal(str(row["tdc_deposit_channel_impulse_bil"])) > 0 for row in rows
    } == {True, False}

    bad = DEFAULT_TDC_SCENARIOS[0].__class__(
        name="bad",
        description="bad",
        du_interest_recipient_share="1.1",
        ru_financing_for_du_outlay_share="0",
        du_financed_absorption_share="0",
        tga_toc_offset_share="0",
    )
    with pytest.raises(ValueError, match="between 0 and 1"):
        apply_tdc_scenario(period_public_interest_impulse_bil="100", assumption=bad)


def test_ratewall_threshold_rows_are_conditional_and_fail_closed() -> None:
    hit_row = compute_threshold_row(
        scenario=DEFAULT_THRESHOLD_SCENARIOS[0],
        horizon="1y",
        months="12",
        gdp_bil="1000",
        period_public_interest_impulse_bil="100",
        period_treasury_interest_impulse_bil="80",
        period_fed_interest_impulse_bil="20",
        source_status="unit_fixture",
    )
    low_offset = ThresholdScenarioAssumption(
        name="low_offset",
        description="low offset fixture",
        maturity_mix="mixed",
        ru_absorption_share="0.1",
        du_outlay_share="0.1",
        du_direct_absorption_share="0.8",
        tga_offset_share="0.1",
        fiscal_offset_share="0.5",
        financial_retention_share="0.2",
        contractionary_drag_gdp_share="0.01",
    )
    nonhit_row = compute_threshold_row(
        scenario=low_offset,
        horizon="1y",
        months="12",
        gdp_bil="1000",
        period_public_interest_impulse_bil="100",
        period_treasury_interest_impulse_bil="20",
        period_fed_interest_impulse_bil="80",
        source_status="unit_fixture",
    )

    assert hit_row["threshold_hit_under_assumptions"] == "true"
    assert nonhit_row["threshold_hit_under_assumptions"] == "false"
    assert hit_row["ru_financing_condition_not_additive_bil"] == "52.0000"
    assert hit_row["deposit_pricing_income_context_bil"] == "0"
    assert hit_row["assumed_contractionary_drag_bil"] == "7.76000"
    assert hit_row["dominant_public_channel"] == "treasury_interest_outlays"
    assert nonhit_row["dominant_public_channel"] == "fed_interest_payments"
    assert {
        hit_row["pricing_output_enabled"],
        hit_row["incidence_claim_enabled"],
        hit_row["welfare_claim_enabled"],
        hit_row["financialization_causal_claim_enabled"],
    } == {"false"}
    assert (
        hit_row["claim_boundary"]
        == "conditional_threshold_simulation_not_policy_failure_or_causal_claim"
    )


def test_ratewall_threshold_scenarios_reject_invalid_shares() -> None:
    bad = ThresholdScenarioAssumption(
        name="bad",
        description="bad",
        maturity_mix="mixed",
        ru_absorption_share="1.1",
        du_outlay_share="0",
        du_direct_absorption_share="0",
        tga_offset_share="0",
        fiscal_offset_share="0",
        financial_retention_share="0",
        contractionary_drag_gdp_share="0.01",
    )

    with pytest.raises(ValueError, match="between 0 and 1"):
        compute_threshold_row(
            scenario=bad,
            horizon="1y",
            months="12",
            gdp_bil="1000",
            period_public_interest_impulse_bil="100",
            period_treasury_interest_impulse_bil="100",
            period_fed_interest_impulse_bil="0",
            source_status="unit_fixture",
        )
