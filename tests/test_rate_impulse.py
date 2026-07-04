from decimal import Decimal

import pytest

from ratewall.accounting.fed_remittances import estimate_remittance_impact
from ratewall.accounting.rate_impulse import (
    HorizonRepricing,
    RateImpulseInputs,
    compute_rate_impulse,
)
from ratewall.accounting.treasury_repricing import (
    RepricingBucket,
    debt_repricing_within,
)


def test_one_hundred_bps_impulse_splits_public_interest_flows() -> None:
    results = compute_rate_impulse(
        RateImpulseInputs(
            reserves="3000",
            on_rrp="200",
            gdp="25000",
            horizons=[
                HorizonRepricing(label="1q", months="3", debt_repricing="500"),
                HorizonRepricing(label="1y", months="12", debt_repricing="1000"),
            ],
        ),
        bps="100",
    )

    one_year = results["1y"]
    assert one_year.delta_rate == Decimal("0.01")
    assert one_year.annualized_treasury_interest == Decimal("10.00")
    assert one_year.annualized_iorb_payments == Decimal("30.00")
    assert one_year.annualized_on_rrp_payments == Decimal("2.00")
    assert one_year.annualized_fed_remittance_change == Decimal("0.00")
    assert one_year.annualized_fed_remittance_leakage == Decimal("0")
    assert one_year.annualized_fed_future_remittance_drag == Decimal("32.00")
    assert one_year.annualized_gross_interest_income == Decimal("42.00")
    assert one_year.annualized_private_recipient_cashflow_impulse == Decimal("42.00")
    assert (
        one_year.annualized_treasury_financing_impulse_current_cash
        == Decimal("10.00")
    )
    assert (
        one_year.annualized_component_display_total_not_macro_impulse
        == Decimal("42.00")
    )
    assert one_year.annualized_public_interest_impulse == Decimal("42.00")
    assert one_year.annualized_public_interest_impulse_gdp_share == Decimal("0.00168")

    one_quarter = results["1q"]
    assert one_quarter.annualized_treasury_interest == Decimal("5.00")
    assert one_quarter.period_public_interest_impulse == Decimal("9.25")


def test_rate_impulse_can_turn_off_remittance_offset() -> None:
    results = compute_rate_impulse(
        RateImpulseInputs(
            reserves="3000",
            on_rrp="200",
            gdp="25000",
            horizons=[HorizonRepricing(label="1y", months="12", debt_repricing="1000")],
            fed_remittance_offset="0",
        ),
        bps="100",
    )

    assert results["1y"].annualized_fed_remittance_change == Decimal("0.00")
    assert results["1y"].annualized_public_interest_impulse == Decimal("42.00")


def test_rate_impulse_rejects_pass_through_above_one() -> None:
    with pytest.raises(ValueError, match="reserve_pass_through"):
        compute_rate_impulse(
            RateImpulseInputs(
                reserves="1",
                on_rrp="1",
                gdp="100",
                horizons=[
                    HorizonRepricing(label="1y", months="12", debt_repricing="1")
                ],
                reserve_pass_through="1.01",
            )
        )


def test_remittance_impact_tracks_deferred_asset_addition() -> None:
    impact = estimate_remittance_impact(
        iorb_payments="30",
        on_rrp_payments="2",
        offset_share="1",
        existing_remittance_capacity="10",
    )

    assert impact.current_remittance_reduction == Decimal("10")
    assert impact.remittance_change == Decimal("-10")
    assert impact.remittance_leakage == Decimal("10")
    assert impact.future_remittance_drag == Decimal("22")
    assert impact.deferred_asset_addition == Decimal("22")


def test_treasury_repricing_sums_buckets_inside_horizon() -> None:
    buckets = [
        RepricingBucket(label="bill", months_to_reprice="3", amount="100"),
        RepricingBucket(label="note", months_to_reprice="18", amount="300"),
        RepricingBucket(label="frn", months_to_reprice="1", amount="50"),
    ]

    assert debt_repricing_within(buckets, months="12") == Decimal("150")
