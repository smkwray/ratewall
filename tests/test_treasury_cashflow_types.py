from dataclasses import FrozenInstanceError, asdict
from datetime import date
from decimal import Decimal

import pytest

from ratewall.accounting.treasury_cashflow_types import (
    AccountingBasis,
    EventType,
    InstrumentType,
    IssuancePolicyBucket,
    TreasuryAuctionLot,
    TreasuryCurveScenario,
    TreasuryFlowEvent,
    TreasuryIssuancePolicy,
    TreasuryPosition,
    TreasuryScenario,
    treasury_flow_event_field_names,
)


def _event(**overrides) -> TreasuryFlowEvent:
    values = {
        "event_id": "event-1",
        "scenario_id": "scenario",
        "reference_lineage_id": "opening-book",
        "position_or_cohort_id": "pos-91282C",
        "cusip": "91282CXX",
        "instrument_type": InstrumentType.NOTE,
        "event_type": EventType.COUPON,
        "accounting_basis": AccountingBasis.CASH,
        "contractual_date": date(2026, 6, 30),
        "cash_settlement_date": date(2026, 6, 30),
        "accrual_start": date(2025, 12, 31),
        "accrual_end": date(2026, 6, 30),
        "signed_amount_bil": "1.25",
        "source_as_of": date(2026, 5, 31),
        "source_status": "fixture",
    }
    values.update(overrides)
    return TreasuryFlowEvent(**values)


def test_track1_enums_cover_frozen_interface_values() -> None:
    assert {item.value for item in InstrumentType} == {
        "bill",
        "note",
        "bond",
        "frn",
        "tips",
        "other_unknown",
    }
    assert {item.value for item in EventType} == {
        "coupon",
        "bill_discount_interest",
        "frn_interest",
        "tips_coupon",
        "tips_indexation",
        "principal_redemption",
        "issuance_proceeds",
        "accrued_interest_at_issue",
        "buyback",
    }
    assert {item.value for item in AccountingBasis} == {
        "cash",
        "budget_accrual",
        "face_stock",
    }


def test_flow_event_is_signed_and_free_of_ratewall_denominator_fields() -> None:
    coupon = _event(signed_amount_bil="3.5", event_type=EventType.COUPON)
    issuance = _event(
        event_id="issue",
        event_type=EventType.ISSUANCE_PROCEEDS,
        accounting_basis=AccountingBasis.CASH,
        signed_amount_bil="-99",
    )
    face_stock = _event(
        event_id="face-issue",
        event_type=EventType.ISSUANCE_PROCEEDS,
        accounting_basis=AccountingBasis.FACE_STOCK,
        signed_amount_bil="100",
    )
    redemption = _event(
        event_id="face-retire",
        event_type=EventType.PRINCIPAL_REDEMPTION,
        accounting_basis=AccountingBasis.FACE_STOCK,
        signed_amount_bil="-100",
    )

    assert coupon.signed_amount_bil == Decimal("3.5")
    assert issuance.signed_amount_bil == Decimal("-99")
    assert face_stock.signed_amount_bil == Decimal("100")
    assert redemption.signed_amount_bil == Decimal("-100")

    forbidden_fragments = (
        "mpc",
        "holder_share",
        "tdc",
        "denominator",
        "repricing_share",
        "one_year",
    )
    fields = treasury_flow_event_field_names()
    for fragment in forbidden_fragments:
        assert all(fragment not in field_name for field_name in fields)

    with pytest.raises(TypeError):
        TreasuryFlowEvent(mpc="forbidden", **asdict(coupon))
    with pytest.raises(FrozenInstanceError):
        coupon.signed_amount_bil = Decimal("0")  # type: ignore[misc]


def test_position_and_auction_lot_distinguish_contractual_cusip_from_reopening_lots() -> None:
    first_lot = TreasuryAuctionLot(
        lot_id="91282CXX-2026-01",
        position_id="position-91282CXX",
        cusip="91282CXX",
        instrument_type=InstrumentType.NOTE,
        auction_date=date(2026, 1, 15),
        issue_date=date(2026, 1, 31),
        settlement_date=date(2026, 1, 31),
        maturity_date=date(2028, 1, 31),
        issued_face_bil="75",
        redeemed_face_bil="5",
        source_row_ids=("row-2", "row-1"),
    )
    reopening = TreasuryAuctionLot(
        lot_id="91282CXX-2026-02",
        position_id="position-91282CXX",
        cusip="91282CXX",
        instrument_type=InstrumentType.NOTE,
        auction_date=date(2026, 2, 15),
        issue_date=date(2026, 1, 31),
        settlement_date=date(2026, 2, 28),
        maturity_date=date(2028, 1, 31),
        issued_face_bil="25",
        source_row_ids=("row-3",),
    )
    position = TreasuryPosition(
        position_id="position-91282CXX",
        cusip="91282CXX",
        instrument_type=InstrumentType.NOTE,
        issue_date=date(2026, 1, 31),
        maturity_date=date(2028, 1, 31),
        original_face_bil=first_lot.issued_face_bil + reopening.issued_face_bil,
        outstanding_face_bil=first_lot.outstanding_face_bil
        + reopening.outstanding_face_bil,
        coupon_rate="0.0425",
        source_as_of=date(2026, 2, 28),
        source_status="normalized_mspd_fixture",
        lot_ids=(reopening.lot_id, first_lot.lot_id),
    )

    assert first_lot.outstanding_face_bil == Decimal("70")
    assert position.original_face_bil == Decimal("100")
    assert position.outstanding_face_bil == Decimal("95")
    assert position.lot_ids == (first_lot.lot_id, reopening.lot_id)


def test_positions_reject_impossible_uncapped_source_aggregates() -> None:
    with pytest.raises(ValueError, match="outstanding_face_bil cannot exceed"):
        TreasuryPosition(
            position_id="bad-position",
            cusip="BAD",
            instrument_type=InstrumentType.BILL,
            issue_date=date(2026, 1, 1),
            maturity_date=date(2026, 4, 1),
            original_face_bil="10",
            outstanding_face_bil="11",
            source_as_of=date(2026, 1, 31),
            source_status="fixture_impossible_aggregate",
        )


def test_curve_and_issuance_policy_axes_are_separate_and_fail_closed() -> None:
    curve = TreasuryCurveScenario(
        scenario_id="curve-up",
        as_of=date(2026, 1, 1),
        nominal_annual_rates={24: "0.041", 120: "0.047"},
        bill_discount_rates={3: "0.039"},
    )
    policy = TreasuryIssuancePolicy(
        policy_id="bill-note-mix",
        source_status="fixture",
        buckets=(
            IssuancePolicyBucket(
                bucket_id="bill-3m",
                instrument_type=InstrumentType.BILL,
                tenor_months=3,
                weight="0.25",
            ),
            IssuancePolicyBucket(
                bucket_id="note-2y",
                instrument_type=InstrumentType.NOTE,
                tenor_months=24,
                weight="0.75",
            ),
        ),
    )
    scenario = TreasuryScenario(
        scenario_id="curve-up-policy-base",
        curve_scenario_id=curve.scenario_id,
        issuance_policy_id=policy.policy_id,
        reference_scenario_id="reference",
    )

    assert scenario.curve_scenario_id == "curve-up"
    assert scenario.issuance_policy_id == "bill-note-mix"
    assert curve.require_rate(24) == Decimal("0.041")
    assert curve.require_rate(3, curve="bill") == Decimal("0.039")
    with pytest.raises(ValueError, match="missing nominal curve node"):
        curve.require_rate(60)


def test_issuance_policy_requires_weights_to_sum_to_one() -> None:
    with pytest.raises(ValueError, match="issuance weights must sum to 1"):
        TreasuryIssuancePolicy(
            policy_id="bad-policy",
            source_status="fixture",
            buckets=(
                IssuancePolicyBucket(
                    bucket_id="bill",
                    instrument_type=InstrumentType.BILL,
                    tenor_months=3,
                    weight="0.3",
                ),
            ),
        )
