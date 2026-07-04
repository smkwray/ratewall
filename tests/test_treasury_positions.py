from datetime import date
from decimal import Decimal

import pytest

from ratewall.accounting.treasury_cashflow_types import (
    AccountingBasis,
    EventType,
    InstrumentType,
)
from ratewall.data.treasury_positions import (
    lot_face_stock_changes,
    normalize_mspd_positions,
)


def _note_row(**overrides) -> dict[str, object]:
    row: dict[str, object] = {
        "record_date": "2026-05-31",
        "security_type_desc": "Marketable",
        "security_class1_desc": "Notes",
        "security_class2_desc": "91282CXX",
        "issue_date": "2026-01-31",
        "maturity_date": "2028-01-31",
        "interest_rate_pct": "4.25",
        "interest_pay_date_1": "01/31",
        "interest_pay_date_2": "07/31",
        "issued_amt": "75000",
        "redeemed_amt": "5000",
        "outstanding_amt": "70000",
        "src_line_nbr": "row-note-1",
    }
    row.update(overrides)
    return row


def test_reopened_cusips_roll_into_one_contractual_position_with_lots() -> None:
    book = normalize_mspd_positions(
        (
            _note_row(),
            _note_row(
                issued_amt="25000",
                redeemed_amt="0",
                outstanding_amt="25000",
                src_line_nbr="row-note-2",
            ),
        ),
        debt_held_public_bil="125",
    )

    assert len(book.positions) == 1
    position = book.positions[0]
    assert position.position_id == "position-91282CXX"
    assert position.cusip == "91282CXX"
    assert position.instrument_type is InstrumentType.NOTE
    assert position.original_face_bil == Decimal("100")
    assert position.outstanding_face_bil == Decimal("95")
    assert position.coupon_rate == Decimal("0.0425")
    assert position.lot_ids == (
        "lot-91282CXX-2026-01-31-row-note-1",
        "lot-91282CXX-2026-01-31-row-note-2",
    )

    assert len(book.auction_lots) == 2
    assert [lot.issued_face_bil for lot in book.auction_lots] == [
        Decimal("75"),
        Decimal("25"),
    ]
    assert book.reconciliation.normalized_outstanding_face_bil == Decimal("95")
    assert book.reconciliation.residual_bil == Decimal("30")


def test_subtotal_rows_including_frn_totals_are_excluded() -> None:
    book = normalize_mspd_positions(
        (
            {
                "record_date": "2026-05-31",
                "security_type_desc": "Marketable",
                "security_class1_desc": "Floating Rate Notes",
                "security_class2_desc": "91282DFF",
                "issue_date": "2026-04-30",
                "maturity_date": "2028-04-30",
                "interest_rate_pct": "4.37",
                "interest_pay_date_1": "01/31",
                "interest_pay_date_2": "04/30",
                "interest_pay_date_3": "07/31",
                "interest_pay_date_4": "10/31",
                "issued_amt": "10000",
                "redeemed_amt": "0",
                "outstanding_amt": "10000",
                "src_line_nbr": "row-frn",
            },
            {
                "record_date": "2026-05-31",
                "security_type_desc": "Marketable",
                "security_class1_desc": "Floating Rate Notes",
                "security_class2_desc": "Total Floating Rate Notes",
                "issue_date": "2026-04-30",
                "maturity_date": "2028-04-30",
                "issued_amt": "99000",
                "redeemed_amt": "0",
                "outstanding_amt": "99000",
                "src_line_nbr": "row-frn-total",
            },
        ),
        debt_held_public_bil="20",
    )

    assert [position.cusip for position in book.positions] == ["91282DFF"]
    assert book.positions[0].instrument_type is InstrumentType.FRN
    assert book.positions[0].coupon_frequency_months == 3
    assert book.reconciliation.normalized_outstanding_face_bil == Decimal("10")
    assert book.reconciliation.excluded_source_row_ids == ("row-frn-total",)


def test_signed_issue_and_redemption_face_stock_semantics_are_explicit() -> None:
    book = normalize_mspd_positions(
        (_note_row(issued_amt="10000", redeemed_amt="4000", outstanding_amt="6000"),)
    )

    changes = lot_face_stock_changes(book.auction_lots[0])

    assert changes[0].event_type is EventType.ISSUANCE_PROCEEDS
    assert changes[0].accounting_basis is AccountingBasis.FACE_STOCK
    assert changes[0].signed_amount_bil == Decimal("10")
    assert changes[1].event_type is EventType.PRINCIPAL_REDEMPTION
    assert changes[1].accounting_basis is AccountingBasis.FACE_STOCK
    assert changes[1].signed_amount_bil == Decimal("-4")


def test_impossible_aggregate_fails_loudly_without_debt_cap() -> None:
    with pytest.raises(ValueError, match="refusing to cap impossible aggregate"):
        normalize_mspd_positions(
            (
                _note_row(
                    issued_amt="120000",
                    redeemed_amt="0",
                    outstanding_amt="120000",
                ),
            ),
            debt_held_public_bil="100",
        )


def test_inconsistent_signed_source_amounts_fail_before_normalization() -> None:
    with pytest.raises(ValueError, match="outstanding_amt must equal"):
        normalize_mspd_positions(
            (_note_row(issued_amt="10000", redeemed_amt="2500", outstanding_amt="9000"),)
        )


def test_duplicate_source_row_ids_fail_loudly() -> None:
    with pytest.raises(ValueError, match="duplicate MSPD source row id"):
        normalize_mspd_positions(
            (
                _note_row(src_line_nbr="duplicate-row"),
                _note_row(
                    issued_amt="25000",
                    redeemed_amt="0",
                    outstanding_amt="25000",
                    src_line_nbr="duplicate-row",
                ),
            )
        )


def test_source_row_order_does_not_change_normalized_output() -> None:
    records = (
        _note_row(src_line_nbr="row-b"),
        _note_row(
            security_class2_desc="91282CYY",
            issued_amt="50000",
            redeemed_amt="10000",
            outstanding_amt="40000",
            src_line_nbr="row-a",
        ),
        _note_row(
            issued_amt="25000",
            redeemed_amt="0",
            outstanding_amt="25000",
            src_line_nbr="row-c",
        ),
    )

    forward = normalize_mspd_positions(records, debt_held_public_bil="150")
    reverse = normalize_mspd_positions(tuple(reversed(records)), debt_held_public_bil="150")

    assert forward.positions == reverse.positions
    assert forward.auction_lots == reverse.auction_lots
    assert forward.reconciliation == reverse.reconciliation

    unlabeled_records = (
        _note_row(src_line_nbr=None),
        _note_row(
            issued_amt="25000",
            redeemed_amt="0",
            outstanding_amt="25000",
            src_line_nbr=None,
        ),
    )
    unlabeled_forward = normalize_mspd_positions(unlabeled_records)
    unlabeled_reverse = normalize_mspd_positions(tuple(reversed(unlabeled_records)))

    assert unlabeled_forward.positions == unlabeled_reverse.positions
    assert unlabeled_forward.auction_lots == unlabeled_reverse.auction_lots


def test_same_date_reconciliation_is_explicit_and_mixed_dates_fail() -> None:
    book = normalize_mspd_positions(
        (_note_row(),),
        source_as_of=date(2026, 5, 31),
        debt_held_public_bil="100",
    )

    assert book.source_as_of == date(2026, 5, 31)
    assert book.reconciliation.source_as_of == date(2026, 5, 31)
    assert book.reconciliation.debt_held_public_bil == Decimal("100")
    assert book.reconciliation.residual_bil == Decimal("30")
    assert book.reconciliation.included_source_row_ids == ("row-note-1",)

    with pytest.raises(ValueError, match="share exactly one record_date"):
        normalize_mspd_positions(
            (
                _note_row(),
                _note_row(record_date="2026-04-30", src_line_nbr="row-prior"),
            )
        )
