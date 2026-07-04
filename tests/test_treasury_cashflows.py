from datetime import date, timedelta
from decimal import Decimal

import pytest

from ratewall.accounting.treasury_cashflow_types import (
    AccountingBasis,
    EventType,
    InstrumentType,
    TreasuryCurveScenario,
    TreasuryPosition,
)
from ratewall.accounting.treasury_cashflows import (
    generate_contractual_cashflows,
    sum_signed_amounts,
)


def _position(**overrides) -> TreasuryPosition:
    values = {
        "position_id": "pos-note",
        "cusip": "91282CNOTE",
        "instrument_type": InstrumentType.NOTE,
        "issue_date": date(2026, 1, 15),
        "maturity_date": date(2027, 1, 15),
        "original_face_bil": "100",
        "outstanding_face_bil": "100",
        "coupon_rate": "0.06",
        "source_as_of": date(2026, 1, 31),
        "source_status": "normalized_fixture",
    }
    values.update(overrides)
    return TreasuryPosition(**values)


def _events_of(events, event_type, basis=None):
    return [
        event
        for event in events
        if event.event_type is event_type
        and (basis is None or event.accounting_basis is basis)
    ]


def test_fixed_note_coupon_and_principal_timing_are_contractual() -> None:
    position = _position()

    events = generate_contractual_cashflows([position], scenario_id="fixed")

    cash_coupons = _events_of(events, EventType.COUPON, AccountingBasis.CASH)
    accrual_coupons = _events_of(
        events, EventType.COUPON, AccountingBasis.BUDGET_ACCRUAL
    )
    principal_cash = _events_of(
        events, EventType.PRINCIPAL_REDEMPTION, AccountingBasis.CASH
    )
    principal_face = _events_of(
        events, EventType.PRINCIPAL_REDEMPTION, AccountingBasis.FACE_STOCK
    )

    assert [event.contractual_date for event in cash_coupons] == [
        date(2026, 7, 15),
        date(2027, 1, 15),
    ]
    assert [event.signed_amount_bil for event in cash_coupons] == [
        Decimal("3.00"),
        Decimal("3.00"),
    ]
    assert [event.accrual_start for event in accrual_coupons] == [
        date(2026, 1, 15),
        date(2026, 7, 15),
    ]
    assert [event.signed_amount_bil for event in principal_cash] == [Decimal("100")]
    assert [event.signed_amount_bil for event in principal_face] == [Decimal("-100")]


def test_bill_has_no_coupons_and_decomposes_discount_interest() -> None:
    bill = _position(
        position_id="pos-bill",
        cusip="91279BILL",
        instrument_type=InstrumentType.BILL,
        issue_date=date(2026, 1, 1),
        maturity_date=date(2026, 4, 1),
        coupon_rate=None,
        issue_price_per_100="98",
    )

    events = generate_contractual_cashflows(
        [bill],
        scenario_id="bill",
        include_issue_events=True,
    )

    assert _events_of(events, EventType.COUPON) == []
    assert _events_of(events, EventType.TIPS_COUPON) == []
    assert _events_of(events, EventType.FRN_INTEREST) == []
    assert [
        event.signed_amount_bil
        for event in _events_of(
            events, EventType.ISSUANCE_PROCEEDS, AccountingBasis.CASH
        )
    ] == [Decimal("-98")]
    assert [
        event.signed_amount_bil
        for event in _events_of(
            events, EventType.PRINCIPAL_REDEMPTION, AccountingBasis.CASH
        )
    ] == [Decimal("98")]
    assert [
        event.signed_amount_bil
        for event in _events_of(
            events, EventType.BILL_DISCOUNT_INTEREST, AccountingBasis.CASH
        )
    ] == [Decimal("2")]
    assert [
        event.signed_amount_bil
        for event in _events_of(
            events, EventType.BILL_DISCOUNT_INTEREST, AccountingBasis.BUDGET_ACCRUAL
        )
    ] == [Decimal("2")]
    assert sum_signed_amounts(events, accounting_basis=AccountingBasis.FACE_STOCK) == 0


def test_frn_weekly_accruals_and_quarterly_cash_payment_are_distinct() -> None:
    frn = _position(
        position_id="pos-frn",
        cusip="91282CFRN",
        instrument_type=InstrumentType.FRN,
        issue_date=date(2026, 1, 1),
        maturity_date=date(2026, 4, 1),
        coupon_rate=None,
        frn_spread_bps="12.5",
        frn_index_name="SOFR",
        next_reset_date=date(2026, 1, 1),
        coupon_frequency_months=3,
    )
    reset_rates = {}
    reset_date = frn.next_reset_date
    while reset_date < frn.maturity_date:
        reset_rates[reset_date] = "0.04"
        reset_date += timedelta(days=7)

    events = generate_contractual_cashflows(
        [frn],
        scenario_id="frn",
        frn_index_rates=reset_rates,
    )

    accruals = _events_of(
        events, EventType.FRN_INTEREST, AccountingBasis.BUDGET_ACCRUAL
    )
    cash_payments = _events_of(
        events, EventType.FRN_INTEREST, AccountingBasis.CASH
    )

    assert len(accruals) == 13
    assert {event.accrual_start for event in accruals} >= {
        date(2026, 1, 1),
        date(2026, 1, 8),
        date(2026, 3, 26),
    }
    assert {event.contractual_date for event in accruals} != {
        event.contractual_date for event in cash_payments
    }
    assert [event.cash_settlement_date for event in cash_payments] == [
        date(2026, 4, 1)
    ]
    assert sum(event.signed_amount_bil for event in accruals) == cash_payments[
        0
    ].signed_amount_bil


def test_frn_requires_reset_rate_for_each_reset_period() -> None:
    frn = _position(
        position_id="pos-frn-missing",
        cusip="91282CFR2",
        instrument_type=InstrumentType.FRN,
        issue_date=date(2026, 1, 1),
        maturity_date=date(2026, 1, 15),
        coupon_rate=None,
        frn_spread_bps="10",
        next_reset_date=date(2026, 1, 1),
        coupon_frequency_months=3,
    )

    with pytest.raises(ValueError, match="missing FRN index rate"):
        generate_contractual_cashflows(
            [frn],
            scenario_id="frn",
            frn_index_rates={date(2026, 1, 1): "0.04"},
        )


def test_tips_separates_coupon_indexation_and_maturity_floor() -> None:
    tips = _position(
        position_id="pos-tips",
        cusip="91282CTIPS",
        instrument_type=InstrumentType.TIPS,
        issue_date=date(2026, 1, 1),
        maturity_date=date(2027, 1, 1),
        coupon_rate="0.02",
        inflation_index_ratio="1",
    )

    events = generate_contractual_cashflows(
        [tips],
        scenario_id="tips",
        tips_index_ratios={
            date(2026, 7, 1): "1.10",
            date(2027, 1, 1): "0.95",
        },
    )

    cash_coupons = _events_of(events, EventType.TIPS_COUPON, AccountingBasis.CASH)
    indexation = _events_of(
        events, EventType.TIPS_INDEXATION, AccountingBasis.BUDGET_ACCRUAL
    )
    maturity_cash = _events_of(
        events, EventType.PRINCIPAL_REDEMPTION, AccountingBasis.CASH
    )

    assert [event.signed_amount_bil for event in cash_coupons] == [
        Decimal("1.100"),
        Decimal("0.950"),
    ]
    assert [event.signed_amount_bil for event in indexation] == [
        Decimal("10.00"),
        Decimal("-15.00"),
    ]
    assert _events_of(events, EventType.TIPS_INDEXATION, AccountingBasis.CASH) == []
    assert [event.signed_amount_bil for event in maturity_cash] == [Decimal("100")]
    assert sum_signed_amounts(
        events,
        accounting_basis=AccountingBasis.BUDGET_ACCRUAL,
        event_type=EventType.TIPS_INDEXATION,
    ) == Decimal("-5.00")


def test_reopened_position_generates_one_contractual_schedule() -> None:
    reopened = _position(
        position_id="pos-reopened",
        cusip="91282CREO",
        original_face_bil="100",
        outstanding_face_bil="95",
        lot_ids=("lot-2026-02", "lot-2026-01"),
    )

    events = generate_contractual_cashflows([reopened], scenario_id="reopened")

    cash_coupons = _events_of(events, EventType.COUPON, AccountingBasis.CASH)
    principal_cash = _events_of(
        events, EventType.PRINCIPAL_REDEMPTION, AccountingBasis.CASH
    )

    assert len(cash_coupons) == 2
    assert [event.signed_amount_bil for event in cash_coupons] == [
        Decimal("2.850"),
        Decimal("2.850"),
    ]
    assert [event.signed_amount_bil for event in principal_cash] == [Decimal("95")]
    assert {event.position_or_cohort_id for event in events} == {"pos-reopened"}


def test_existing_fixed_coupons_are_invariant_to_curve_changes() -> None:
    note = _position()
    low_curve = TreasuryCurveScenario(
        scenario_id="curve-low",
        as_of=date(2026, 1, 15),
        nominal_annual_rates={6: "0.01", 12: "0.012"},
    )
    high_curve = TreasuryCurveScenario(
        scenario_id="curve-high",
        as_of=date(2026, 1, 15),
        nominal_annual_rates={6: "0.06", 12: "0.065"},
    )

    low_events = generate_contractual_cashflows(
        [note],
        scenario_id="fixed",
        curve_scenario=low_curve,
    )
    high_events = generate_contractual_cashflows(
        [note],
        scenario_id="fixed",
        curve_scenario=high_curve,
    )

    assert [
        event
        for event in low_events
        if event.event_type is EventType.COUPON
    ] == [
        event
        for event in high_events
        if event.event_type is EventType.COUPON
    ]


def test_cash_budget_accrual_and_face_stock_ledgers_are_not_conflated() -> None:
    note = _position()

    events = generate_contractual_cashflows([note], scenario_id="ledger")

    assert sum_signed_amounts(events, accounting_basis=AccountingBasis.CASH) == Decimal(
        "106.00"
    )
    assert sum_signed_amounts(
        events, accounting_basis=AccountingBasis.BUDGET_ACCRUAL
    ) == Decimal("6.00")
    assert sum_signed_amounts(
        events, accounting_basis=AccountingBasis.FACE_STOCK
    ) == Decimal("-100")
    assert sum_signed_amounts(
        events,
        accounting_basis=AccountingBasis.CASH,
        event_type=EventType.PRINCIPAL_REDEMPTION,
    ) == Decimal("100")
