"""Curve and issuance-policy path logic for Treasury cashflow scenarios."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from ratewall.accounting.numbers import NumberLike, require_nonnegative, to_decimal
from ratewall.accounting.treasury_cashflow_types import (
    AccountingBasis,
    EventType,
    InstrumentType,
    IssuancePolicyBucket,
    TreasuryCurveScenario,
    TreasuryFlowEvent,
    TreasuryIssuancePolicy,
    TreasuryScenario,
)


@dataclass(frozen=True, slots=True)
class DebtStockConstraint:
    """Face-stock target used to solve future gross issuance.

    CBO debt stock is a closing-stock constraint. Deficit financing needs can be
    retained for reconciliation, but they are not added on top of the stock
    identity when solving gross issuance.
    """

    constraint_id: str
    opening_face_bil: NumberLike
    scheduled_principal_redemptions_bil: NumberLike
    target_closing_face_bil: NumberLike
    source_status: str
    deficit_financing_need_bil: NumberLike | None = None

    def __post_init__(self) -> None:
        if not self.constraint_id:
            raise ValueError("constraint_id is required")
        if not self.source_status:
            raise ValueError("source_status is required")
        _set_decimal(
            self,
            "opening_face_bil",
            _nonnegative(self.opening_face_bil, "opening_face_bil"),
        )
        _set_decimal(
            self,
            "scheduled_principal_redemptions_bil",
            _nonnegative(
                self.scheduled_principal_redemptions_bil,
                "scheduled_principal_redemptions_bil",
            ),
        )
        _set_decimal(
            self,
            "target_closing_face_bil",
            _nonnegative(self.target_closing_face_bil, "target_closing_face_bil"),
        )
        if self.deficit_financing_need_bil is not None:
            _set_decimal(
                self,
                "deficit_financing_need_bil",
                _nonnegative(
                    self.deficit_financing_need_bil,
                    "deficit_financing_need_bil",
                ),
            )

    @property
    def gross_issuance_required_bil(self) -> Decimal:
        return (
            self.target_closing_face_bil
            - self.opening_face_bil
            + self.scheduled_principal_redemptions_bil
        )


@dataclass(frozen=True, slots=True)
class IssuancePolicyConstraints:
    """Optional guardrails for a full issuance vector."""

    short_maturity_cutoff_months: int = 12
    max_bill_share: NumberLike | None = None
    max_short_maturity_share: NumberLike | None = None
    min_weighted_average_maturity_months: NumberLike | None = None
    max_weighted_average_maturity_months: NumberLike | None = None

    def __post_init__(self) -> None:
        if self.short_maturity_cutoff_months <= 0:
            raise ValueError("short_maturity_cutoff_months must be positive")
        for field_name in ("max_bill_share", "max_short_maturity_share"):
            value = getattr(self, field_name)
            if value is None:
                continue
            parsed = _nonnegative(value, field_name)
            if parsed > Decimal("1"):
                raise ValueError(f"{field_name} cannot exceed 1")
            _set_decimal(self, field_name, parsed)
        for field_name in (
            "min_weighted_average_maturity_months",
            "max_weighted_average_maturity_months",
        ):
            value = getattr(self, field_name)
            if value is not None:
                _set_decimal(self, field_name, _nonnegative(value, field_name))
        if (
            self.min_weighted_average_maturity_months is not None
            and self.max_weighted_average_maturity_months is not None
            and self.min_weighted_average_maturity_months
            > self.max_weighted_average_maturity_months
        ):
            raise ValueError(
                "min_weighted_average_maturity_months cannot exceed "
                "max_weighted_average_maturity_months"
            )


@dataclass(frozen=True, slots=True)
class TreasuryIssuanceCohort:
    """Future issuance cohort generated from a policy bucket and curve node."""

    cohort_id: str
    scenario_id: str
    curve_scenario_id: str
    issuance_policy_id: str
    bucket_id: str
    instrument_type: InstrumentType
    issue_date: date
    maturity_date: date
    tenor_months: int
    face_amount_bil: Decimal
    pricing_rate: Decimal
    bucket_weight: Decimal
    coupon_frequency_months: int


@dataclass(frozen=True, slots=True)
class TreasuryPathMetrics:
    """Derived outputs for a curve/policy path."""

    gross_issuance_bil: Decimal
    scheduled_principal_redemptions_bil: Decimal
    opening_face_bil: Decimal
    closing_face_bil: Decimal
    weighted_average_maturity_months: Decimal
    weighted_average_new_rate: Decimal
    bill_share: Decimal
    short_maturity_share: Decimal


@dataclass(frozen=True, slots=True)
class TreasuryCashflowPath:
    """Generated future path for one separated curve/policy scenario."""

    scenario: TreasuryScenario
    curve: TreasuryCurveScenario
    issuance_policy: TreasuryIssuancePolicy
    debt_stock_constraint: DebtStockConstraint
    cohorts: tuple[TreasuryIssuanceCohort, ...]
    events: tuple[TreasuryFlowEvent, ...]
    metrics: TreasuryPathMetrics


@dataclass(frozen=True, slots=True)
class TreasuryPathDeltas:
    """Scenario-minus-reference deltas over derived path outputs."""

    gross_issuance_bil: Decimal
    closing_face_bil: Decimal
    weighted_average_maturity_months: Decimal
    weighted_average_new_rate: Decimal
    bill_share: Decimal
    short_maturity_share: Decimal


def build_issuance_cashflow_path(
    *,
    scenario: TreasuryScenario,
    curve: TreasuryCurveScenario,
    issuance_policy: TreasuryIssuancePolicy,
    debt_stock_constraint: DebtStockConstraint,
    issue_date: date,
    constraints: IssuancePolicyConstraints | None = None,
) -> TreasuryCashflowPath:
    """Generate issuance cohorts and stock/cash events for a path scenario."""

    _validate_scenario_axes(
        scenario=scenario,
        curve=curve,
        issuance_policy=issuance_policy,
    )
    constraints = constraints or IssuancePolicyConstraints()
    _validate_policy_shape(issuance_policy)
    gross_issuance = debt_stock_constraint.gross_issuance_required_bil
    if gross_issuance < 0:
        raise ValueError("negative gross issuance requires an explicit buyback path")

    rates_by_bucket = {
        bucket.bucket_id: _required_bucket_rate(curve, bucket)
        for bucket in issuance_policy.buckets
        if bucket.weight > 0
    }
    metrics = _derive_metrics(
        issuance_policy=issuance_policy,
        rates_by_bucket=rates_by_bucket,
        stock_constraint=debt_stock_constraint,
        constraints=constraints,
    )

    cohorts: list[TreasuryIssuanceCohort] = []
    events: list[TreasuryFlowEvent] = []
    reference_lineage_id = scenario.reference_scenario_id or scenario.scenario_id
    redemptions = debt_stock_constraint.scheduled_principal_redemptions_bil
    if redemptions > 0:
        events.extend(
            _principal_redemption_events(
                scenario=scenario,
                reference_lineage_id=reference_lineage_id,
                event_date=issue_date,
                amount_bil=redemptions,
                source_status=debt_stock_constraint.source_status,
            )
        )

    for bucket in issuance_policy.buckets:
        if bucket.weight == 0:
            continue
        face_amount = gross_issuance * bucket.weight
        rate = rates_by_bucket[bucket.bucket_id]
        cohort = TreasuryIssuanceCohort(
            cohort_id=_cohort_id(scenario.scenario_id, bucket.bucket_id, issue_date),
            scenario_id=scenario.scenario_id,
            curve_scenario_id=curve.scenario_id,
            issuance_policy_id=issuance_policy.policy_id,
            bucket_id=bucket.bucket_id,
            instrument_type=bucket.instrument_type,
            issue_date=issue_date,
            maturity_date=_add_months(issue_date, bucket.tenor_months),
            tenor_months=bucket.tenor_months,
            face_amount_bil=face_amount,
            pricing_rate=rate,
            bucket_weight=bucket.weight,
            coupon_frequency_months=bucket.coupon_frequency_months,
        )
        cohorts.append(cohort)
        events.extend(
            _issuance_events(
                cohort=cohort,
                scenario=scenario,
                reference_lineage_id=reference_lineage_id,
                source_status=issuance_policy.source_status,
            )
        )

    _assert_face_stock_identity(
        opening_face_bil=debt_stock_constraint.opening_face_bil,
        target_closing_face_bil=debt_stock_constraint.target_closing_face_bil,
        events=events,
    )
    return TreasuryCashflowPath(
        scenario=scenario,
        curve=curve,
        issuance_policy=issuance_policy,
        debt_stock_constraint=debt_stock_constraint,
        cohorts=tuple(cohorts),
        events=tuple(events),
        metrics=metrics,
    )


def path_deltas(
    *, candidate: TreasuryCashflowPath, reference: TreasuryCashflowPath
) -> TreasuryPathDeltas:
    """Return candidate-minus-reference derived-output deltas."""

    return TreasuryPathDeltas(
        gross_issuance_bil=(
            candidate.metrics.gross_issuance_bil - reference.metrics.gross_issuance_bil
        ),
        closing_face_bil=(
            candidate.metrics.closing_face_bil - reference.metrics.closing_face_bil
        ),
        weighted_average_maturity_months=(
            candidate.metrics.weighted_average_maturity_months
            - reference.metrics.weighted_average_maturity_months
        ),
        weighted_average_new_rate=(
            candidate.metrics.weighted_average_new_rate
            - reference.metrics.weighted_average_new_rate
        ),
        bill_share=candidate.metrics.bill_share - reference.metrics.bill_share,
        short_maturity_share=(
            candidate.metrics.short_maturity_share
            - reference.metrics.short_maturity_share
        ),
    )


def assert_track1_denominator_frozen(
    *, reference_denominator_bil: NumberLike, candidate_denominator_bil: NumberLike
) -> Decimal:
    """Pure firewall assertion for Track 1 denominator independence."""

    reference = to_decimal(reference_denominator_bil, field="reference_denominator_bil")
    candidate = to_decimal(candidate_denominator_bil, field="candidate_denominator_bil")
    if candidate != reference:
        raise ValueError("Track 1 curve/issuance path cannot change denominator D")
    return reference


def _validate_scenario_axes(
    *,
    scenario: TreasuryScenario,
    curve: TreasuryCurveScenario,
    issuance_policy: TreasuryIssuancePolicy,
) -> None:
    if scenario.curve_scenario_id != curve.scenario_id:
        raise ValueError("scenario curve_scenario_id does not match curve")
    if scenario.issuance_policy_id != issuance_policy.policy_id:
        raise ValueError("scenario issuance_policy_id does not match issuance policy")


def _validate_policy_shape(policy: TreasuryIssuancePolicy) -> None:
    seen: set[str] = set()
    weight_sum = Decimal("0")
    for bucket in policy.buckets:
        if bucket.bucket_id in seen:
            raise ValueError(f"duplicate issuance bucket_id: {bucket.bucket_id}")
        seen.add(bucket.bucket_id)
        weight_sum += bucket.weight
    if weight_sum != Decimal("1"):
        raise ValueError("issuance weights must sum to 1")


def _derive_metrics(
    *,
    issuance_policy: TreasuryIssuancePolicy,
    rates_by_bucket: dict[str, Decimal],
    stock_constraint: DebtStockConstraint,
    constraints: IssuancePolicyConstraints,
) -> TreasuryPathMetrics:
    wam_months = sum(
        (Decimal(bucket.tenor_months) * bucket.weight for bucket in issuance_policy.buckets),
        Decimal("0"),
    )
    wanrr = sum(
        (
            rates_by_bucket.get(bucket.bucket_id, Decimal("0")) * bucket.weight
            for bucket in issuance_policy.buckets
        ),
        Decimal("0"),
    )
    bill_share = sum(
        (
            bucket.weight
            for bucket in issuance_policy.buckets
            if bucket.instrument_type == InstrumentType.BILL
        ),
        Decimal("0"),
    )
    short_share = sum(
        (
            bucket.weight
            for bucket in issuance_policy.buckets
            if bucket.tenor_months <= constraints.short_maturity_cutoff_months
        ),
        Decimal("0"),
    )
    metrics = TreasuryPathMetrics(
        gross_issuance_bil=stock_constraint.gross_issuance_required_bil,
        scheduled_principal_redemptions_bil=(
            stock_constraint.scheduled_principal_redemptions_bil
        ),
        opening_face_bil=stock_constraint.opening_face_bil,
        closing_face_bil=stock_constraint.target_closing_face_bil,
        weighted_average_maturity_months=wam_months,
        weighted_average_new_rate=wanrr,
        bill_share=bill_share,
        short_maturity_share=short_share,
    )
    _validate_constraints(metrics=metrics, constraints=constraints)
    return metrics


def _validate_constraints(
    *, metrics: TreasuryPathMetrics, constraints: IssuancePolicyConstraints
) -> None:
    if (
        constraints.max_bill_share is not None
        and metrics.bill_share > constraints.max_bill_share
    ):
        raise ValueError("bill share exceeds issuance-policy constraint")
    if (
        constraints.max_short_maturity_share is not None
        and metrics.short_maturity_share > constraints.max_short_maturity_share
    ):
        raise ValueError("short-maturity share exceeds issuance-policy constraint")
    if (
        constraints.min_weighted_average_maturity_months is not None
        and metrics.weighted_average_maturity_months
        < constraints.min_weighted_average_maturity_months
    ):
        raise ValueError("weighted average maturity is below issuance-policy constraint")
    if (
        constraints.max_weighted_average_maturity_months is not None
        and metrics.weighted_average_maturity_months
        > constraints.max_weighted_average_maturity_months
    ):
        raise ValueError("weighted average maturity exceeds issuance-policy constraint")


def _required_bucket_rate(
    curve: TreasuryCurveScenario, bucket: IssuancePolicyBucket
) -> Decimal:
    if bucket.instrument_type == InstrumentType.BILL:
        return curve.require_rate(bucket.tenor_months, curve="bill")
    if bucket.instrument_type == InstrumentType.TIPS:
        return curve.require_rate(bucket.tenor_months, curve="real")
    if bucket.instrument_type == InstrumentType.FRN:
        return curve.require_rate(bucket.tenor_months, curve="frn_index")
    return curve.require_rate(bucket.tenor_months, curve="nominal")


def _issuance_events(
    *,
    cohort: TreasuryIssuanceCohort,
    scenario: TreasuryScenario,
    reference_lineage_id: str,
    source_status: str,
) -> tuple[TreasuryFlowEvent, TreasuryFlowEvent]:
    cash_proceeds = _issuance_cash_proceeds_bil(cohort)
    common = {
        "scenario_id": scenario.scenario_id,
        "reference_lineage_id": reference_lineage_id,
        "position_or_cohort_id": cohort.cohort_id,
        "cusip": "FUTURE_COHORT",
        "instrument_type": cohort.instrument_type,
        "event_type": EventType.ISSUANCE_PROCEEDS,
        "contractual_date": cohort.issue_date,
        "cash_settlement_date": cohort.issue_date,
        "accrual_start": None,
        "accrual_end": None,
        "source_as_of": cohort.issue_date,
        "source_status": source_status,
    }
    return (
        TreasuryFlowEvent(
            event_id=f"{cohort.cohort_id}::issuance_cash",
            accounting_basis=AccountingBasis.CASH,
            signed_amount_bil=-cash_proceeds,
            **common,
        ),
        TreasuryFlowEvent(
            event_id=f"{cohort.cohort_id}::issuance_face",
            accounting_basis=AccountingBasis.FACE_STOCK,
            signed_amount_bil=cohort.face_amount_bil,
            **common,
        ),
    )


def _principal_redemption_events(
    *,
    scenario: TreasuryScenario,
    reference_lineage_id: str,
    event_date: date,
    amount_bil: Decimal,
    source_status: str,
) -> tuple[TreasuryFlowEvent, TreasuryFlowEvent]:
    common = {
        "scenario_id": scenario.scenario_id,
        "reference_lineage_id": reference_lineage_id,
        "position_or_cohort_id": "opening_book_scheduled_redemptions",
        "cusip": "AGGREGATE",
        "instrument_type": InstrumentType.OTHER_UNKNOWN,
        "event_type": EventType.PRINCIPAL_REDEMPTION,
        "contractual_date": event_date,
        "cash_settlement_date": event_date,
        "accrual_start": None,
        "accrual_end": None,
        "source_as_of": event_date,
        "source_status": source_status,
    }
    return (
        TreasuryFlowEvent(
            event_id=f"{scenario.scenario_id}::scheduled_redemption_cash",
            accounting_basis=AccountingBasis.CASH,
            signed_amount_bil=amount_bil,
            **common,
        ),
        TreasuryFlowEvent(
            event_id=f"{scenario.scenario_id}::scheduled_redemption_face",
            accounting_basis=AccountingBasis.FACE_STOCK,
            signed_amount_bil=-amount_bil,
            **common,
        ),
    )


def _issuance_cash_proceeds_bil(cohort: TreasuryIssuanceCohort) -> Decimal:
    if cohort.instrument_type != InstrumentType.BILL:
        return cohort.face_amount_bil
    year_fraction = Decimal(cohort.tenor_months) / Decimal("12")
    discount = cohort.pricing_rate * year_fraction
    if discount >= Decimal("1"):
        raise ValueError("bill discount rate implies nonpositive issuance proceeds")
    return cohort.face_amount_bil * (Decimal("1") - discount)


def _assert_face_stock_identity(
    *,
    opening_face_bil: Decimal,
    target_closing_face_bil: Decimal,
    events: Iterable[TreasuryFlowEvent],
) -> None:
    face_delta = sum(
        (
            event.signed_amount_bil
            for event in events
            if event.accounting_basis == AccountingBasis.FACE_STOCK
        ),
        Decimal("0"),
    )
    closing_face = opening_face_bil + face_delta
    if closing_face != target_closing_face_bil:
        raise ValueError("face/principal stock identity failed")


def _cohort_id(scenario_id: str, bucket_id: str, issue_date: date) -> str:
    return f"{scenario_id}::{bucket_id}::{issue_date.isoformat()}"


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _decimal(value: NumberLike, field: str) -> Decimal:
    return to_decimal(value, field=field)


def _nonnegative(value: NumberLike, field: str) -> Decimal:
    return require_nonnegative(_decimal(value, field), field=field)


def _set_decimal(instance: object, field: str, value: Decimal) -> None:
    object.__setattr__(instance, field, value)
