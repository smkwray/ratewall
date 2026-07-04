"""Pure contractual Treasury cashflow kernel.

The functions in this module consume normalized ``TreasuryPosition`` objects.
They do not read source files, allocate holders, compute RateWall denominators,
or convert flows into TDC/current-demand support.
"""

from __future__ import annotations

from collections import defaultdict
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Mapping

from ratewall.accounting.numbers import NumberLike, to_decimal
from ratewall.accounting.treasury_cashflow_types import (
    AccountingBasis,
    EventType,
    InstrumentType,
    TreasuryCurveScenario,
    TreasuryFlowEvent,
    TreasuryPosition,
)

_BPS_DENOMINATOR = Decimal("10000")
_DAYS_PER_YEAR = Decimal("365")
_MONTHS_PER_YEAR = Decimal("12")
_PAR_PRICE = Decimal("100")


def generate_contractual_cashflows(
    positions: Iterable[TreasuryPosition],
    *,
    scenario_id: str = "contractual",
    reference_lineage_id: str = "opening_book",
    curve_scenario: TreasuryCurveScenario | None = None,
    frn_index_rates: Mapping[date, NumberLike] | None = None,
    tips_index_ratios: Mapping[date, NumberLike] | None = None,
    include_issue_events: bool = False,
) -> tuple[TreasuryFlowEvent, ...]:
    """Emit dated contractual events for normalized Treasury positions.

    ``curve_scenario`` is intentionally unused for existing contractual coupons:
    curve paths can price future issuance, but they do not rewrite fixed coupons
    already present in the opening Treasury book.
    """

    _ = curve_scenario
    events: list[TreasuryFlowEvent] = []
    for position in positions:
        events.extend(
            generate_position_cashflows(
                position,
                scenario_id=scenario_id,
                reference_lineage_id=reference_lineage_id,
                frn_index_rates=frn_index_rates,
                tips_index_ratios=tips_index_ratios,
                include_issue_events=include_issue_events,
            )
        )
    return _sort_events(events)


def generate_position_cashflows(
    position: TreasuryPosition,
    *,
    scenario_id: str = "contractual",
    reference_lineage_id: str = "opening_book",
    frn_index_rates: Mapping[date, NumberLike] | None = None,
    tips_index_ratios: Mapping[date, NumberLike] | None = None,
    include_issue_events: bool = False,
) -> tuple[TreasuryFlowEvent, ...]:
    """Emit the contractual event schedule for one normalized position."""

    events: list[TreasuryFlowEvent] = []
    if include_issue_events:
        events.extend(
            _issue_events(
                position,
                scenario_id=scenario_id,
                reference_lineage_id=reference_lineage_id,
            )
        )

    match position.instrument_type:
        case InstrumentType.BILL:
            events.extend(
                _bill_events(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                )
            )
        case InstrumentType.NOTE | InstrumentType.BOND:
            events.extend(
                _fixed_coupon_events(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                )
            )
        case InstrumentType.FRN:
            events.extend(
                _frn_events(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                    frn_index_rates=frn_index_rates,
                )
            )
        case InstrumentType.TIPS:
            events.extend(
                _tips_events(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                    tips_index_ratios=tips_index_ratios,
                )
            )
        case InstrumentType.OTHER_UNKNOWN:
            raise ValueError("unsupported Treasury instrument type: other_unknown")

    return _sort_events(events)


def sum_signed_amounts(
    events: Iterable[TreasuryFlowEvent],
    *,
    accounting_basis: AccountingBasis | None = None,
    event_type: EventType | None = None,
) -> Decimal:
    """Sum signed event amounts without mixing accounting bases."""

    total = Decimal("0")
    for event in events:
        if accounting_basis is not None and event.accounting_basis is not accounting_basis:
            continue
        if event_type is not None and event.event_type is not event_type:
            continue
        total += event.signed_amount_bil
    return total


def _issue_events(
    position: TreasuryPosition,
    *,
    scenario_id: str,
    reference_lineage_id: str,
) -> tuple[TreasuryFlowEvent, ...]:
    issue_cash = _priced_face(position.original_face_bil, position.issue_price_per_100)
    return (
        _event(
            position,
            scenario_id=scenario_id,
            reference_lineage_id=reference_lineage_id,
            event_type=EventType.ISSUANCE_PROCEEDS,
            accounting_basis=AccountingBasis.CASH,
            contractual_date=position.issue_date,
            cash_settlement_date=position.issue_date,
            accrual_start=None,
            accrual_end=None,
            signed_amount_bil=-issue_cash,
            sequence=0,
        ),
        _event(
            position,
            scenario_id=scenario_id,
            reference_lineage_id=reference_lineage_id,
            event_type=EventType.ISSUANCE_PROCEEDS,
            accounting_basis=AccountingBasis.FACE_STOCK,
            contractual_date=position.issue_date,
            cash_settlement_date=position.issue_date,
            accrual_start=None,
            accrual_end=None,
            signed_amount_bil=position.original_face_bil,
            sequence=1,
        ),
    )


def _bill_events(
    position: TreasuryPosition,
    *,
    scenario_id: str,
    reference_lineage_id: str,
) -> tuple[TreasuryFlowEvent, ...]:
    principal_return = _priced_face(
        position.outstanding_face_bil, position.issue_price_per_100
    )
    discount_interest = position.outstanding_face_bil - principal_return
    events = [
        _event(
            position,
            scenario_id=scenario_id,
            reference_lineage_id=reference_lineage_id,
            event_type=EventType.PRINCIPAL_REDEMPTION,
            accounting_basis=AccountingBasis.CASH,
            contractual_date=position.maturity_date,
            cash_settlement_date=position.maturity_date,
            accrual_start=None,
            accrual_end=None,
            signed_amount_bil=principal_return,
            sequence=10,
        ),
        _event(
            position,
            scenario_id=scenario_id,
            reference_lineage_id=reference_lineage_id,
            event_type=EventType.PRINCIPAL_REDEMPTION,
            accounting_basis=AccountingBasis.FACE_STOCK,
            contractual_date=position.maturity_date,
            cash_settlement_date=position.maturity_date,
            accrual_start=None,
            accrual_end=None,
            signed_amount_bil=-position.outstanding_face_bil,
            sequence=11,
        ),
    ]
    if discount_interest != Decimal("0"):
        events.extend(
            (
                _event(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                    event_type=EventType.BILL_DISCOUNT_INTEREST,
                    accounting_basis=AccountingBasis.BUDGET_ACCRUAL,
                    contractual_date=position.maturity_date,
                    cash_settlement_date=position.maturity_date,
                    accrual_start=position.issue_date,
                    accrual_end=position.maturity_date,
                    signed_amount_bil=discount_interest,
                    sequence=12,
                ),
                _event(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                    event_type=EventType.BILL_DISCOUNT_INTEREST,
                    accounting_basis=AccountingBasis.CASH,
                    contractual_date=position.maturity_date,
                    cash_settlement_date=position.maturity_date,
                    accrual_start=position.issue_date,
                    accrual_end=position.maturity_date,
                    signed_amount_bil=discount_interest,
                    sequence=13,
                ),
            )
        )
    return tuple(events)


def _fixed_coupon_events(
    position: TreasuryPosition,
    *,
    scenario_id: str,
    reference_lineage_id: str,
) -> tuple[TreasuryFlowEvent, ...]:
    events: list[TreasuryFlowEvent] = []
    coupon_rate = _optional_decimal(position.coupon_rate, field="coupon_rate")
    coupon_dates = _scheduled_dates(
        position.issue_date,
        position.maturity_date,
        position.coupon_frequency_months,
    )
    if coupon_rate != Decimal("0"):
        coupon_amount = _period_interest(
            position.outstanding_face_bil,
            coupon_rate,
            position.coupon_frequency_months,
        )
        accrual_start = position.issue_date
        for index, coupon_date in enumerate(coupon_dates):
            events.append(
                _event(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                    event_type=EventType.COUPON,
                    accounting_basis=AccountingBasis.BUDGET_ACCRUAL,
                    contractual_date=coupon_date,
                    cash_settlement_date=coupon_date,
                    accrual_start=accrual_start,
                    accrual_end=coupon_date,
                    signed_amount_bil=coupon_amount,
                    sequence=100 + (index * 2),
                )
            )
            events.append(
                _event(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                    event_type=EventType.COUPON,
                    accounting_basis=AccountingBasis.CASH,
                    contractual_date=coupon_date,
                    cash_settlement_date=coupon_date,
                    accrual_start=accrual_start,
                    accrual_end=coupon_date,
                    signed_amount_bil=coupon_amount,
                    sequence=101 + (index * 2),
                )
            )
            accrual_start = coupon_date
    events.extend(
        _principal_redemption_events(
            position,
            scenario_id=scenario_id,
            reference_lineage_id=reference_lineage_id,
            cash_amount=position.outstanding_face_bil,
            sequence=900,
        )
    )
    return tuple(events)


def _frn_events(
    position: TreasuryPosition,
    *,
    scenario_id: str,
    reference_lineage_id: str,
    frn_index_rates: Mapping[date, NumberLike] | None,
) -> tuple[TreasuryFlowEvent, ...]:
    if position.frn_spread_bps is None:
        raise ValueError(f"{position.position_id} missing frn_spread_bps")
    rates = _decimal_date_mapping(
        frn_index_rates,
        field=f"{position.position_id}.frn_index_rates",
    )
    reset_start = position.next_reset_date or position.issue_date
    if reset_start < position.issue_date:
        reset_start = position.issue_date
    payment_dates = _scheduled_dates(
        position.issue_date,
        position.maturity_date,
        position.coupon_frequency_months,
    )
    spread = position.frn_spread_bps / _BPS_DENOMINATOR
    events: list[TreasuryFlowEvent] = []
    cash_by_payment: dict[date, Decimal] = defaultdict(Decimal)
    accrual_by_payment: dict[date, list[tuple[date, date]]] = defaultdict(list)
    sequence = 200

    while reset_start < position.maturity_date:
        if reset_start not in rates:
            raise ValueError(f"missing FRN index rate for {reset_start.isoformat()}")
        reset_end = min(reset_start + timedelta(days=7), position.maturity_date)
        days = Decimal((reset_end - reset_start).days)
        amount = position.outstanding_face_bil * (rates[reset_start] + spread)
        amount *= days / _DAYS_PER_YEAR
        payment_date = _next_payment_date(reset_end, payment_dates)
        events.append(
            _event(
                position,
                scenario_id=scenario_id,
                reference_lineage_id=reference_lineage_id,
                event_type=EventType.FRN_INTEREST,
                accounting_basis=AccountingBasis.BUDGET_ACCRUAL,
                contractual_date=reset_end,
                cash_settlement_date=reset_end,
                accrual_start=reset_start,
                accrual_end=reset_end,
                signed_amount_bil=amount,
                sequence=sequence,
            )
        )
        cash_by_payment[payment_date] += amount
        accrual_by_payment[payment_date].append((reset_start, reset_end))
        sequence += 1
        reset_start = reset_end

    for index, payment_date in enumerate(sorted(cash_by_payment)):
        periods = accrual_by_payment[payment_date]
        events.append(
            _event(
                position,
                scenario_id=scenario_id,
                reference_lineage_id=reference_lineage_id,
                event_type=EventType.FRN_INTEREST,
                accounting_basis=AccountingBasis.CASH,
                contractual_date=payment_date,
                cash_settlement_date=payment_date,
                accrual_start=periods[0][0],
                accrual_end=periods[-1][1],
                signed_amount_bil=cash_by_payment[payment_date],
                sequence=300 + index,
            )
        )

    events.extend(
        _principal_redemption_events(
            position,
            scenario_id=scenario_id,
            reference_lineage_id=reference_lineage_id,
            cash_amount=position.outstanding_face_bil,
            sequence=900,
        )
    )
    return tuple(events)


def _tips_events(
    position: TreasuryPosition,
    *,
    scenario_id: str,
    reference_lineage_id: str,
    tips_index_ratios: Mapping[date, NumberLike] | None,
) -> tuple[TreasuryFlowEvent, ...]:
    coupon_rate = _optional_decimal(position.coupon_rate, field="coupon_rate")
    ratios = _decimal_date_mapping(
        tips_index_ratios,
        field=f"{position.position_id}.tips_index_ratios",
    )
    base_ratio = _optional_decimal(
        position.inflation_index_ratio,
        field="inflation_index_ratio",
        default=Decimal("1"),
    )
    coupon_dates = _scheduled_dates(
        position.issue_date,
        position.maturity_date,
        position.coupon_frequency_months,
    )
    events: list[TreasuryFlowEvent] = []
    previous_date = position.issue_date
    previous_ratio = base_ratio

    for index, coupon_date in enumerate(coupon_dates):
        ratio = ratios.get(coupon_date, previous_ratio)
        indexed_face = position.outstanding_face_bil * ratio
        coupon_amount = _period_interest(
            indexed_face,
            coupon_rate,
            position.coupon_frequency_months,
        )
        indexation = position.outstanding_face_bil * (ratio - previous_ratio)
        if indexation != Decimal("0"):
            events.append(
                _event(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                    event_type=EventType.TIPS_INDEXATION,
                    accounting_basis=AccountingBasis.BUDGET_ACCRUAL,
                    contractual_date=coupon_date,
                    cash_settlement_date=coupon_date,
                    accrual_start=previous_date,
                    accrual_end=coupon_date,
                    signed_amount_bil=indexation,
                    sequence=400 + (index * 3),
                )
            )
        if coupon_amount != Decimal("0"):
            events.append(
                _event(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                    event_type=EventType.TIPS_COUPON,
                    accounting_basis=AccountingBasis.BUDGET_ACCRUAL,
                    contractual_date=coupon_date,
                    cash_settlement_date=coupon_date,
                    accrual_start=previous_date,
                    accrual_end=coupon_date,
                    signed_amount_bil=coupon_amount,
                    sequence=401 + (index * 3),
                )
            )
            events.append(
                _event(
                    position,
                    scenario_id=scenario_id,
                    reference_lineage_id=reference_lineage_id,
                    event_type=EventType.TIPS_COUPON,
                    accounting_basis=AccountingBasis.CASH,
                    contractual_date=coupon_date,
                    cash_settlement_date=coupon_date,
                    accrual_start=previous_date,
                    accrual_end=coupon_date,
                    signed_amount_bil=coupon_amount,
                    sequence=402 + (index * 3),
                )
            )
        previous_date = coupon_date
        previous_ratio = ratio

    final_ratio = ratios.get(position.maturity_date, previous_ratio)
    maturity_cash = max(
        position.outstanding_face_bil,
        position.outstanding_face_bil * final_ratio,
    )
    events.extend(
        _principal_redemption_events(
            position,
            scenario_id=scenario_id,
            reference_lineage_id=reference_lineage_id,
            cash_amount=maturity_cash,
            sequence=900,
        )
    )
    return tuple(events)


def _principal_redemption_events(
    position: TreasuryPosition,
    *,
    scenario_id: str,
    reference_lineage_id: str,
    cash_amount: Decimal,
    sequence: int,
) -> tuple[TreasuryFlowEvent, TreasuryFlowEvent]:
    return (
        _event(
            position,
            scenario_id=scenario_id,
            reference_lineage_id=reference_lineage_id,
            event_type=EventType.PRINCIPAL_REDEMPTION,
            accounting_basis=AccountingBasis.CASH,
            contractual_date=position.maturity_date,
            cash_settlement_date=position.maturity_date,
            accrual_start=None,
            accrual_end=None,
            signed_amount_bil=cash_amount,
            sequence=sequence,
        ),
        _event(
            position,
            scenario_id=scenario_id,
            reference_lineage_id=reference_lineage_id,
            event_type=EventType.PRINCIPAL_REDEMPTION,
            accounting_basis=AccountingBasis.FACE_STOCK,
            contractual_date=position.maturity_date,
            cash_settlement_date=position.maturity_date,
            accrual_start=None,
            accrual_end=None,
            signed_amount_bil=-position.outstanding_face_bil,
            sequence=sequence + 1,
        ),
    )


def _event(
    position: TreasuryPosition,
    *,
    scenario_id: str,
    reference_lineage_id: str,
    event_type: EventType,
    accounting_basis: AccountingBasis,
    contractual_date: date,
    cash_settlement_date: date,
    accrual_start: date | None,
    accrual_end: date | None,
    signed_amount_bil: NumberLike,
    sequence: int,
) -> TreasuryFlowEvent:
    event_id = (
        f"{scenario_id}:{position.position_id}:{accounting_basis.value}:"
        f"{event_type.value}:{contractual_date.isoformat()}:{sequence:04d}"
    )
    return TreasuryFlowEvent(
        event_id=event_id,
        scenario_id=scenario_id,
        reference_lineage_id=reference_lineage_id,
        position_or_cohort_id=position.position_id,
        cusip=position.cusip,
        instrument_type=position.instrument_type,
        event_type=event_type,
        accounting_basis=accounting_basis,
        contractual_date=contractual_date,
        cash_settlement_date=cash_settlement_date,
        accrual_start=accrual_start,
        accrual_end=accrual_end,
        signed_amount_bil=signed_amount_bil,
        source_as_of=position.source_as_of,
        source_status=position.source_status,
    )


def _period_interest(
    face_bil: Decimal,
    annual_rate: Decimal,
    frequency_months: int,
) -> Decimal:
    return face_bil * annual_rate * Decimal(frequency_months) / _MONTHS_PER_YEAR


def _priced_face(face_bil: Decimal, price_per_100: NumberLike | None) -> Decimal:
    if price_per_100 is None:
        return face_bil
    return face_bil * to_decimal(price_per_100, field="issue_price_per_100") / _PAR_PRICE


def _optional_decimal(
    value: NumberLike | None,
    *,
    field: str,
    default: Decimal = Decimal("0"),
) -> Decimal:
    if value is None:
        return default
    return to_decimal(value, field=field)


def _decimal_date_mapping(
    values: Mapping[date, NumberLike] | None,
    *,
    field: str,
) -> dict[date, Decimal]:
    if values is None:
        return {}
    return {
        key: to_decimal(value, field=f"{field}.{key.isoformat()}")
        for key, value in values.items()
    }


def _scheduled_dates(start: date, end: date, frequency_months: int) -> tuple[date, ...]:
    current = end
    dates: list[date] = []
    while current > start:
        dates.append(current)
        current = _add_months(current, -frequency_months)
    return tuple(reversed(dates))


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _next_payment_date(target: date, payment_dates: tuple[date, ...]) -> date:
    for payment_date in payment_dates:
        if payment_date >= target:
            return payment_date
    return payment_dates[-1]


def _sort_events(events: Iterable[TreasuryFlowEvent]) -> tuple[TreasuryFlowEvent, ...]:
    return tuple(
        sorted(
            events,
            key=lambda event: (
                event.contractual_date,
                event.cash_settlement_date,
                event.accounting_basis.value,
                event.event_type.value,
                event.event_id,
            ),
        )
    )


__all__ = [
    "generate_contractual_cashflows",
    "generate_position_cashflows",
    "sum_signed_amounts",
]
