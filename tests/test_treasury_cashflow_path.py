from dataclasses import astuple
from datetime import date
from decimal import Decimal

import pytest

from ratewall.accounting.treasury_cashflow_path import (
    DebtStockConstraint,
    IssuancePolicyConstraints,
    assert_track1_denominator_frozen,
    build_issuance_cashflow_path,
    path_deltas,
)
from ratewall.accounting.treasury_cashflow_types import (
    AccountingBasis,
    InstrumentType,
    IssuancePolicyBucket,
    TreasuryCurveScenario,
    TreasuryIssuancePolicy,
    TreasuryScenario,
)


ISSUE_DATE = date(2027, 1, 31)


def _stock_constraint() -> DebtStockConstraint:
    return DebtStockConstraint(
        constraint_id="cbo-dhp-2027-fixture",
        opening_face_bil="1000",
        scheduled_principal_redemptions_bil="90",
        target_closing_face_bil="1030",
        deficit_financing_need_bil="120",
        source_status="fixture_cbo_debt_stock_constraint",
    )


def _reference_curve(**overrides) -> TreasuryCurveScenario:
    values = {
        "scenario_id": "curve-reference",
        "as_of": date(2026, 12, 31),
        "nominal_annual_rates": {24: "0.0400"},
        "bill_discount_rates": {6: "0.0350"},
        "real_annual_rates": {120: "0.0180"},
        "frn_index_rates": {24: "0.0375"},
    }
    values.update(overrides)
    return TreasuryCurveScenario(**values)


def _base_policy(**overrides) -> TreasuryIssuancePolicy:
    values = {
        "policy_id": "policy-reference",
        "source_status": "fixture_issuance_policy",
        "buckets": (
            IssuancePolicyBucket(
                bucket_id="bill-6m",
                instrument_type=InstrumentType.BILL,
                tenor_months=6,
                weight="0.25",
            ),
            IssuancePolicyBucket(
                bucket_id="note-2y",
                instrument_type=InstrumentType.NOTE,
                tenor_months=24,
                weight="0.75",
            ),
        ),
    }
    values.update(overrides)
    return TreasuryIssuancePolicy(**values)


def _scenario(
    *,
    scenario_id: str = "reference",
    curve_id: str = "curve-reference",
    policy_id: str = "policy-reference",
) -> TreasuryScenario:
    return TreasuryScenario(
        scenario_id=scenario_id,
        curve_scenario_id=curve_id,
        issuance_policy_id=policy_id,
        reference_scenario_id="reference",
    )


def _path(
    *,
    scenario: TreasuryScenario | None = None,
    curve: TreasuryCurveScenario | None = None,
    policy: TreasuryIssuancePolicy | None = None,
):
    curve = curve or _reference_curve()
    policy = policy or _base_policy()
    scenario = scenario or _scenario(
        curve_id=curve.scenario_id,
        policy_id=policy.policy_id,
    )
    return build_issuance_cashflow_path(
        scenario=scenario,
        curve=curve,
        issuance_policy=policy,
        debt_stock_constraint=_stock_constraint(),
        issue_date=ISSUE_DATE,
        constraints=IssuancePolicyConstraints(
            max_bill_share="0.50",
            max_short_maturity_share="0.50",
            min_weighted_average_maturity_months="12",
            max_weighted_average_maturity_months="60",
        ),
    )


def test_generates_future_cohorts_events_and_derived_metrics() -> None:
    path = _path()

    assert [cohort.bucket_id for cohort in path.cohorts] == ["bill-6m", "note-2y"]
    assert path.cohorts[0].maturity_date == date(2027, 7, 31)
    assert path.cohorts[0].face_amount_bil == Decimal("30.00")
    assert path.cohorts[1].face_amount_bil == Decimal("90.00")

    metrics = path.metrics
    assert metrics.gross_issuance_bil == Decimal("120")
    assert metrics.weighted_average_maturity_months == Decimal("19.50")
    assert metrics.weighted_average_new_rate == Decimal("0.038750")
    assert metrics.bill_share == Decimal("0.25")
    assert metrics.short_maturity_share == Decimal("0.25")

    face_delta = sum(
        event.signed_amount_bil
        for event in path.events
        if event.accounting_basis == AccountingBasis.FACE_STOCK
    )
    assert metrics.opening_face_bil + face_delta == metrics.closing_face_bil

    cash_events = {
        event.event_id: event.signed_amount_bil
        for event in path.events
        if event.accounting_basis == AccountingBasis.CASH
    }
    assert cash_events["reference::scheduled_redemption_cash"] == Decimal("90")
    assert cash_events["reference::bill-6m::2027-01-31::issuance_cash"] == Decimal(
        "-29.475000"
    )
    assert cash_events["reference::note-2y::2027-01-31::issuance_cash"] == Decimal(
        "-90.00"
    )


def test_curve_and_issuance_policy_axes_are_independent() -> None:
    reference = _path()
    higher_curve = _reference_curve(
        scenario_id="curve-higher",
        nominal_annual_rates={24: "0.0600"},
        bill_discount_rates={6: "0.0550"},
    )
    curve_only = _path(
        scenario=_scenario(
            scenario_id="curve-only",
            curve_id=higher_curve.scenario_id,
            policy_id="policy-reference",
        ),
        curve=higher_curve,
    )
    policy_shorter = _base_policy(
        policy_id="policy-shorter",
        buckets=(
            IssuancePolicyBucket(
                bucket_id="bill-6m",
                instrument_type=InstrumentType.BILL,
                tenor_months=6,
                weight="0.50",
            ),
            IssuancePolicyBucket(
                bucket_id="note-2y",
                instrument_type=InstrumentType.NOTE,
                tenor_months=24,
                weight="0.50",
            ),
        ),
    )
    policy_only = _path(
        scenario=_scenario(
            scenario_id="policy-only",
            curve_id="curve-reference",
            policy_id=policy_shorter.policy_id,
        ),
        policy=policy_shorter,
    )

    curve_delta = path_deltas(candidate=curve_only, reference=reference)
    assert curve_delta.weighted_average_maturity_months == Decimal("0.00")
    assert curve_delta.bill_share == Decimal("0.00")
    assert curve_delta.short_maturity_share == Decimal("0.00")
    assert curve_delta.weighted_average_new_rate == Decimal("0.020000")

    policy_delta = path_deltas(candidate=policy_only, reference=reference)
    assert policy_delta.weighted_average_maturity_months == Decimal("-4.50")
    assert policy_delta.bill_share == Decimal("0.25")
    assert policy_delta.weighted_average_new_rate == Decimal("-0.001250")


def test_reference_curve_plus_reference_policy_produces_zero_deltas() -> None:
    reference = _path()
    deltas = path_deltas(candidate=reference, reference=reference)

    assert set(astuple(deltas)) == {Decimal("0.00")}


def test_missing_required_curve_nodes_fail_closed() -> None:
    curve = _reference_curve(bill_discount_rates=None)
    with pytest.raises(ValueError, match="missing bill curve node for 6 months"):
        _path(curve=curve)

    missing_note_node = _reference_curve(nominal_annual_rates={60: "0.04"})
    with pytest.raises(ValueError, match="missing nominal curve node for 24 months"):
        _path(curve=missing_note_node)


def test_issuance_weights_and_constraints_are_enforced() -> None:
    with pytest.raises(ValueError, match="issuance weights must sum to 1"):
        _base_policy(
            buckets=(
                IssuancePolicyBucket(
                    bucket_id="bill-6m",
                    instrument_type=InstrumentType.BILL,
                    tenor_months=6,
                    weight="0.90",
                ),
            )
        )

    with pytest.raises(ValueError, match="bill share exceeds"):
        build_issuance_cashflow_path(
            scenario=_scenario(),
            curve=_reference_curve(),
            issuance_policy=_base_policy(),
            debt_stock_constraint=_stock_constraint(),
            issue_date=ISSUE_DATE,
            constraints=IssuancePolicyConstraints(max_bill_share="0.20"),
        )


def test_cbo_stock_constraint_is_not_double_counted_with_deficit() -> None:
    constraint = _stock_constraint()
    path = _path()

    assert constraint.gross_issuance_required_bil == Decimal("120")
    assert constraint.deficit_financing_need_bil == Decimal("120")
    assert path.metrics.gross_issuance_bil == Decimal("120")
    assert path.metrics.opening_face_bil == Decimal("1000")
    assert path.metrics.closing_face_bil == Decimal("1030")


def test_denominator_firewall_is_small_and_pure() -> None:
    reference = _path()
    changed_curve = _reference_curve(
        scenario_id="curve-higher",
        nominal_annual_rates={24: "0.0600"},
        bill_discount_rates={6: "0.0550"},
    )
    candidate = _path(
        scenario=_scenario(
            scenario_id="curve-only",
            curve_id=changed_curve.scenario_id,
            policy_id="policy-reference",
        ),
        curve=changed_curve,
    )

    assert reference.metrics.weighted_average_new_rate != (
        candidate.metrics.weighted_average_new_rate
    )
    assert assert_track1_denominator_frozen(
        reference_denominator_bil="77.5",
        candidate_denominator_bil="77.5",
    ) == Decimal("77.5")
    with pytest.raises(ValueError, match="cannot change denominator D"):
        assert_track1_denominator_frozen(
            reference_denominator_bil="77.5",
            candidate_denominator_bil="77.6",
        )
