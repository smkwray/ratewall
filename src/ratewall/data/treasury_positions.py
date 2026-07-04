"""Normalize MSPD-like Treasury records into contractual opening positions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Literal, Mapping

from ratewall.accounting.numbers import NumberLike, require_nonnegative, to_decimal
from ratewall.accounting.treasury_cashflow_types import (
    AccountingBasis,
    EventType,
    InstrumentType,
    TreasuryAuctionLot,
    TreasuryPosition,
)

AmountUnit = Literal["millions", "billions"]

_EMPTY_VALUES = {None, "", ".", "null", "None"}
_AMOUNT_DIVISORS: dict[AmountUnit, Decimal] = {
    "millions": Decimal("1000"),
    "billions": Decimal("1"),
}
_CUSIP_FIELDS = (
    "cusip",
    "cusip_cd",
    "cusip_number",
    "security_id",
    "series_cd",
    "security_class2_desc",
)
_ROW_ID_FIELDS = ("source_row_id", "src_line_nbr", "row_id", "line_number")


@dataclass(frozen=True, slots=True)
class TreasuryPositionReconciliation:
    """Same-date opening-book reconciliation against an explicit stock total."""

    source_as_of: date
    normalized_outstanding_face_bil: Decimal
    debt_held_public_bil: Decimal | None
    residual_bil: Decimal | None
    included_source_row_ids: tuple[str, ...]
    excluded_source_row_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TreasuryPositionBook:
    """Normalized opening Treasury book plus source-row audit metadata."""

    source_as_of: date
    positions: tuple[TreasuryPosition, ...]
    auction_lots: tuple[TreasuryAuctionLot, ...]
    reconciliation: TreasuryPositionReconciliation

    @property
    def total_outstanding_face_bil(self) -> Decimal:
        return self.reconciliation.normalized_outstanding_face_bil


@dataclass(frozen=True, slots=True)
class SourceLotFaceStockChange:
    """Signed face-stock issue/redemption semantics for one source auction lot."""

    lot_id: str
    event_type: EventType
    accounting_basis: AccountingBasis
    signed_amount_bil: Decimal


def normalize_mspd_positions(
    records: Iterable[Mapping[str, object]],
    *,
    debt_held_public_bil: NumberLike | None = None,
    source_as_of: date | str | None = None,
    source_status: str = "normalized_mspd_opening_book",
    amount_unit: AmountUnit = "millions",
) -> TreasuryPositionBook:
    """Normalize compact MSPD-like rows into positions and reopening lots.

    MSPD amount fields are in millions by default. The normalizer keeps only one
    explicit source date, excludes subtotal rows before CUSIP grouping, and raises
    on impossible stock reconciliation instead of capping values to DHP.
    """

    divisor = _amount_divisor(amount_unit)
    rows = tuple(dict(record) for record in records)
    if not rows:
        raise ValueError("at least one MSPD record is required")

    as_of = _resolve_single_source_date(rows, source_as_of)
    included: list[_PreparedRow] = []
    excluded_row_ids: list[str] = []
    seen_row_ids: set[str] = set()
    for row in rows:
        row_id = _source_row_id(row)
        if row_id in seen_row_ids:
            raise ValueError(f"duplicate MSPD source row id: {row_id}")
        seen_row_ids.add(row_id)
        if _is_subtotal_row(row) or not _is_marketable_row(row):
            excluded_row_ids.append(row_id)
            continue
        prepared = _prepare_row(
            row,
            row_id=row_id,
            divisor=divisor,
        )
        if prepared.lot.outstanding_face_bil == Decimal("0"):
            excluded_row_ids.append(row_id)
            continue
        included.append(prepared)

    if not included:
        raise ValueError("no non-subtotal marketable MSPD records remained")

    positions = _build_positions(included, source_as_of=as_of, source_status=source_status)
    lots = tuple(prepared.lot for prepared in sorted(included, key=_prepared_sort_key))
    normalized_total = sum(
        (position.outstanding_face_bil for position in positions), Decimal("0")
    )
    dhp = (
        require_nonnegative(
            to_decimal(debt_held_public_bil, field="debt_held_public_bil"),
            field="debt_held_public_bil",
        )
        if debt_held_public_bil is not None
        else None
    )
    residual = None if dhp is None else dhp - normalized_total
    if residual is not None and residual < Decimal("0"):
        raise ValueError(
            "normalized outstanding face exceeds debt_held_public_bil; "
            "refusing to cap impossible aggregate"
        )

    included_ids = tuple(
        prepared.row_id for prepared in sorted(included, key=_prepared_sort_key)
    )
    excluded_ids = tuple(sorted(excluded_row_ids))
    reconciliation = TreasuryPositionReconciliation(
        source_as_of=as_of,
        normalized_outstanding_face_bil=normalized_total,
        debt_held_public_bil=dhp,
        residual_bil=residual,
        included_source_row_ids=included_ids,
        excluded_source_row_ids=excluded_ids,
    )
    return TreasuryPositionBook(
        source_as_of=as_of,
        positions=positions,
        auction_lots=lots,
        reconciliation=reconciliation,
    )


def lot_face_stock_changes(
    lot: TreasuryAuctionLot,
) -> tuple[SourceLotFaceStockChange, ...]:
    """Return explicit signed face-stock issue and redemption changes for a lot."""

    changes = [
        SourceLotFaceStockChange(
            lot_id=lot.lot_id,
            event_type=EventType.ISSUANCE_PROCEEDS,
            accounting_basis=AccountingBasis.FACE_STOCK,
            signed_amount_bil=lot.issued_face_bil,
        )
    ]
    if lot.redeemed_face_bil:
        changes.append(
            SourceLotFaceStockChange(
                lot_id=lot.lot_id,
                event_type=EventType.PRINCIPAL_REDEMPTION,
                accounting_basis=AccountingBasis.FACE_STOCK,
                signed_amount_bil=-lot.redeemed_face_bil,
            )
        )
    return tuple(changes)


@dataclass(frozen=True, slots=True)
class _PreparedRow:
    row_id: str
    cusip: str
    instrument_type: InstrumentType
    coupon_rate: Decimal | None
    inflation_index_ratio: Decimal | None
    frn_spread_bps: Decimal | None
    frn_index_name: str | None
    next_reset_date: date | None
    coupon_frequency_months: int
    lot: TreasuryAuctionLot


def _build_positions(
    prepared_rows: Iterable[_PreparedRow],
    *,
    source_as_of: date,
    source_status: str,
) -> tuple[TreasuryPosition, ...]:
    groups: dict[str, list[_PreparedRow]] = {}
    for prepared in prepared_rows:
        groups.setdefault(prepared.cusip, []).append(prepared)

    positions: list[TreasuryPosition] = []
    for cusip in sorted(groups):
        rows = sorted(groups[cusip], key=_prepared_sort_key)
        first = rows[0]
        for row in rows[1:]:
            _require_same(row.instrument_type, first.instrument_type, cusip, "instrument_type")
            _require_same(row.lot.issue_date, first.lot.issue_date, cusip, "issue_date")
            _require_same(row.lot.maturity_date, first.lot.maturity_date, cusip, "maturity_date")
            _require_same(row.coupon_rate, first.coupon_rate, cusip, "coupon_rate")

        original_face = sum((row.lot.issued_face_bil for row in rows), Decimal("0"))
        outstanding_face = sum(
            (row.lot.outstanding_face_bil for row in rows), Decimal("0")
        )
        lot_ids = tuple(row.lot.lot_id for row in rows)
        positions.append(
            TreasuryPosition(
                position_id=_position_id(cusip),
                cusip=cusip,
                instrument_type=first.instrument_type,
                issue_date=first.lot.issue_date,
                maturity_date=first.lot.maturity_date,
                original_face_bil=original_face,
                outstanding_face_bil=outstanding_face,
                source_as_of=source_as_of,
                source_status=source_status,
                coupon_rate=first.coupon_rate,
                issue_price_per_100=first.lot.issue_price_per_100,
                inflation_index_ratio=first.inflation_index_ratio,
                frn_spread_bps=first.frn_spread_bps,
                frn_index_name=first.frn_index_name,
                next_reset_date=first.next_reset_date,
                coupon_frequency_months=first.coupon_frequency_months,
                lot_ids=lot_ids,
            )
        )
    return tuple(positions)


def _prepare_row(
    row: Mapping[str, object],
    *,
    row_id: str,
    divisor: Decimal,
) -> _PreparedRow:
    cusip = _required_text(row, _CUSIP_FIELDS, field_name="cusip")
    instrument_type = _instrument_type(row)
    issue_date = _required_date(row, "issue_date")
    maturity_date = _required_date(row, "maturity_date")
    issued = _required_amount_bil(
        row,
        ("issued_amt", "issue_amt", "original_face_amt", "face_amt"),
        divisor=divisor,
        field_name="issued_amt",
    )
    redeemed = _optional_amount_bil(
        row,
        ("redeemed_amt", "redemption_amt"),
        divisor=divisor,
    ) or Decimal("0")
    if redeemed > issued:
        raise ValueError(f"row {row_id} redeemed_amt exceeds issued_amt")

    outstanding = _optional_amount_bil(
        row,
        ("current_month_outstanding_amt", "outstanding_amt"),
        divisor=divisor,
    )
    if outstanding is not None and outstanding != issued - redeemed:
        raise ValueError(
            f"row {row_id} outstanding_amt must equal issued_amt less redeemed_amt"
        )

    lot = TreasuryAuctionLot(
        lot_id=_lot_id(cusip, row_id, _optional_date(row, "settlement_date") or issue_date),
        position_id=_position_id(cusip),
        cusip=cusip,
        instrument_type=instrument_type,
        auction_date=_optional_date(row, "auction_date") or issue_date,
        issue_date=issue_date,
        settlement_date=_optional_date(row, "settlement_date") or issue_date,
        maturity_date=maturity_date,
        issued_face_bil=issued,
        redeemed_face_bil=redeemed,
        issue_price_per_100=_optional_decimal(row, ("issue_price_per_100",)),
        source_row_ids=(row_id,),
    )
    return _PreparedRow(
        row_id=row_id,
        cusip=cusip,
        instrument_type=instrument_type,
        coupon_rate=_coupon_rate(row),
        inflation_index_ratio=_inflation_index_ratio(row, issued, divisor),
        frn_spread_bps=_optional_decimal(row, ("frn_spread_bps",)),
        frn_index_name=_optional_text(row, ("frn_index_name", "frn_index")),
        next_reset_date=_optional_date(row, "next_reset_date"),
        coupon_frequency_months=_coupon_frequency_months(row, instrument_type),
        lot=lot,
    )


def _resolve_single_source_date(
    rows: Iterable[Mapping[str, object]],
    requested_as_of: date | str | None,
) -> date:
    row_dates = {_required_date(row, "record_date") for row in rows}
    if requested_as_of is not None:
        as_of = _coerce_date(requested_as_of, field="source_as_of")
        if row_dates != {as_of}:
            raise ValueError("MSPD records must all match explicit source_as_of")
        return as_of
    if len(row_dates) != 1:
        raise ValueError("MSPD records must share exactly one record_date")
    return next(iter(row_dates))


def _is_marketable_row(row: Mapping[str, object]) -> bool:
    value = row.get("security_type_desc")
    if _is_empty(value):
        return True
    return str(value).strip().lower() == "marketable"


def _is_subtotal_row(row: Mapping[str, object]) -> bool:
    descriptor_fields = (
        "security_class1_desc",
        "security_class2_desc",
        "security_class3_desc",
        "security_class_desc",
        "security_desc",
        "description",
    )
    for field in descriptor_fields:
        value = row.get(field)
        if _is_empty(value):
            continue
        text = str(value).strip().lower()
        if text.startswith("total") or "subtotal" in text:
            return True
    return False


def _instrument_type(row: Mapping[str, object]) -> InstrumentType:
    text = " ".join(
        str(row.get(field, ""))
        for field in (
            "security_class1_desc",
            "security_class2_desc",
            "security_class3_desc",
            "security_class_desc",
            "instrument_type",
        )
    ).lower()
    if "floating rate" in text or "frn" in text:
        return InstrumentType.FRN
    if "inflation" in text or "tips" in text:
        return InstrumentType.TIPS
    if "bill" in text:
        return InstrumentType.BILL
    if "bond" in text:
        return InstrumentType.BOND
    if "note" in text:
        return InstrumentType.NOTE
    return InstrumentType.OTHER_UNKNOWN


def _coupon_rate(row: Mapping[str, object]) -> Decimal | None:
    coupon = _optional_decimal(row, ("coupon_rate",))
    if coupon is not None:
        return require_nonnegative(coupon, field="coupon_rate")
    interest_rate_pct = _optional_decimal(row, ("interest_rate_pct",))
    if interest_rate_pct is None:
        return None
    return require_nonnegative(interest_rate_pct / Decimal("100"), field="coupon_rate")


def _inflation_index_ratio(
    row: Mapping[str, object],
    issued_face_bil: Decimal,
    divisor: Decimal,
) -> Decimal | None:
    explicit = _optional_decimal(row, ("inflation_index_ratio",))
    if explicit is not None:
        return require_nonnegative(explicit, field="inflation_index_ratio")
    inflation_adj = _optional_amount_bil(row, ("inflation_adj_amt",), divisor=divisor)
    if inflation_adj is None or issued_face_bil == Decimal("0"):
        return None
    return Decimal("1") + (inflation_adj / issued_face_bil)


def _coupon_frequency_months(
    row: Mapping[str, object],
    instrument_type: InstrumentType,
) -> int:
    populated_pay_dates = sum(
        not _is_empty(row.get(field))
        for field in (
            "interest_pay_date_1",
            "interest_pay_date_2",
            "interest_pay_date_3",
            "interest_pay_date_4",
        )
    )
    if populated_pay_dates >= 4:
        return 3
    if populated_pay_dates >= 2:
        return 6
    if instrument_type == InstrumentType.FRN:
        return 3
    return 6


def _required_text(
    row: Mapping[str, object],
    fields: tuple[str, ...],
    *,
    field_name: str,
) -> str:
    value = _optional_text(row, fields)
    if value is None:
        raise ValueError(f"{field_name} is required")
    return value


def _optional_text(row: Mapping[str, object], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = row.get(field)
        if not _is_empty(value):
            return str(value).strip()
    return None


def _required_date(row: Mapping[str, object], field: str) -> date:
    value = _optional_date(row, field)
    if value is None:
        raise ValueError(f"{field} is required")
    return value


def _optional_date(row: Mapping[str, object], field: str) -> date | None:
    value = row.get(field)
    if _is_empty(value):
        return None
    return _coerce_date(value, field=field)


def _coerce_date(value: object, *, field: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def _required_amount_bil(
    row: Mapping[str, object],
    fields: tuple[str, ...],
    *,
    divisor: Decimal,
    field_name: str,
) -> Decimal:
    amount = _optional_amount_bil(row, fields, divisor=divisor)
    if amount is None:
        raise ValueError(f"{field_name} is required")
    return amount


def _optional_amount_bil(
    row: Mapping[str, object],
    fields: tuple[str, ...],
    *,
    divisor: Decimal,
) -> Decimal | None:
    parsed = _optional_decimal(row, fields)
    if parsed is None:
        return None
    return require_nonnegative(parsed / divisor, field=fields[0])


def _optional_decimal(row: Mapping[str, object], fields: tuple[str, ...]) -> Decimal | None:
    for field in fields:
        value = row.get(field)
        if _is_empty(value):
            continue
        return to_decimal(str(value).replace(",", ""), field=field)
    return None


def _source_row_id(row: Mapping[str, object]) -> str:
    value = _optional_text(row, _ROW_ID_FIELDS)
    if value is not None:
        return value
    fingerprint = repr(tuple(sorted((str(key), str(value)) for key, value in row.items())))
    digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:12]
    return f"row-unlabeled-{digest}"


def _amount_divisor(amount_unit: AmountUnit) -> Decimal:
    try:
        return _AMOUNT_DIVISORS[amount_unit]
    except KeyError as exc:
        raise ValueError(f"unknown amount_unit: {amount_unit}") from exc


def _position_id(cusip: str) -> str:
    return f"position-{_slug(cusip)}"


def _lot_id(cusip: str, row_id: str, settlement_date: date) -> str:
    return f"lot-{_slug(cusip)}-{settlement_date.isoformat()}-{_slug(row_id)}"


def _slug(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value)


def _prepared_sort_key(prepared: _PreparedRow) -> tuple[str, date, str]:
    return (prepared.cusip, prepared.lot.settlement_date, prepared.row_id)


def _require_same(left: object, right: object, cusip: str, field: str) -> None:
    if left != right:
        raise ValueError(f"reopened CUSIP {cusip} has conflicting {field}")


def _is_empty(value: object) -> bool:
    return value in _EMPTY_VALUES
