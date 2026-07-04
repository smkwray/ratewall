from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from ratewall.databook.deposit_payer_flow_source_panel import (
    DEPOSIT_PAYER_FLOW_SOURCE_DEFINITION_FIELDS,
    DEPOSIT_PAYER_FLOW_SOURCE_PANEL_FIELDS,
    SAFE_YIELD_SUBLANE_STATUS_FIELDS,
    deposit_payer_flow_source_definition_rows,
    deposit_payer_flow_source_panel_rows,
    safe_yield_sublane_status_rows,
    write_deposit_payer_flow_source_outputs,
)


def test_deposit_payer_flow_source_panel_periodizes_and_passes_gate(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    _write_ffiec_panel(raw / "ffiec_fdic/deposit_interest_expense_panel.csv")
    _write_ncua_panel(raw / "ncua/share_deposit_interest_panel.csv")

    panel = deposit_payer_flow_source_panel_rows(raw_dir=raw)
    definitions = deposit_payer_flow_source_definition_rows()
    status = safe_yield_sublane_status_rows(
        panel,
        raw_dir=raw,
        requested_period_ids=["2024Q1", "2024Q2"],
    )

    assert {field for row in panel for field in row} == set(
        DEPOSIT_PAYER_FLOW_SOURCE_PANEL_FIELDS
    )
    assert {field for row in definitions for field in row} == set(
        DEPOSIT_PAYER_FLOW_SOURCE_DEFINITION_FIELDS
    )
    assert {field for row in status for field in row} == set(
        SAFE_YIELD_SUBLANE_STATUS_FIELDS
    )
    by_row = {row["source_row_id"]: row for row in panel}
    ffiec_q2 = by_row[
        "ffiec_fdic_call_report_deposit_interest_expense::2024Q2::1001"
    ]
    ncua_q2 = by_row[
        "ncua_credit_union_share_deposit_interest_expense::2024Q2::2001"
    ]
    assert ffiec_q2["quarterly_interest_expense_bil"] == "7"
    assert ffiec_q2["object_role"] == "blocked_source_or_method"
    assert ffiec_q2["formula_fields_included"] == "RIAD4508|RIAD0093|RIADHK03|RIADHK04"
    assert ffiec_q2["excluded_fields_retained"] == "RIAD4172"
    assert ncua_q2["quarterly_interest_expense_bil"] == "7"
    assert ncua_q2["formula_fields_included"] == "380|381"
    assert ncua_q2["cross_check_fields_retained"] == "340|350"
    by_definition = {row["field_id"]: row for row in definitions}
    assert by_definition["350"]["included_in_formula"] == "false"
    assert by_definition["350"]["formula_role"] == (
        "cross_check_only_cannot_substitute_for_380_381"
    )
    gate = status[0]
    assert gate["object_role"] == "blocked_source_or_method"
    assert gate["source_gate_status"] == "pass_source_panels_shape_coverage_and_flow"
    assert gate["accepted_current_rows"] == "4"
    assert gate["accepted_current_row_share"] == "1"
    assert gate["blocked_current_ytd_share"] == "0"
    assert gate["exit_exposure_share"] == "0"
    assert gate["positive_flow_all_periods"] == "true"
    assert gate["gross_realized_income_bil"] == "27"
    assert gate["central_n_delta_bil_allowed"] == "false"


def test_ncua_350_cannot_substitute_for_missing_381(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    _write_ffiec_panel(raw / "ffiec_fdic/deposit_interest_expense_panel.csv")
    path = raw / "ncua/share_deposit_interest_panel.csv"
    path.parent.mkdir(parents=True)
    _write_csv(
        path,
        ["report_date", "charter_number", "credit_union_name", "380", "350"],
        [
            ["2024-03-31", "2001", "Fixture CU", "8000000", "999000000"],
            ["2024-06-30", "2001", "Fixture CU", "15000000", "999000000"],
        ],
    )

    panel = deposit_payer_flow_source_panel_rows(raw_dir=raw)
    status = safe_yield_sublane_status_rows(
        panel,
        raw_dir=raw,
        requested_period_ids=["2024Q1", "2024Q2"],
    )

    ncua_rows = [
        row
        for row in panel
        if row["source_family"] == "ncua_credit_union_share_deposit_interest_expense"
    ]
    assert len(ncua_rows) == 1
    assert ncua_rows[0]["source_shape_status"] == (
        "source_panel_shape_failed_missing_381"
    )
    assert "ncua_panel_not_success" in status[0]["source_gate_status"]
    assert status[0]["central_n_delta_bil_allowed"] == "false"


def test_blocked_current_ytd_share_uses_rejected_exposure_magnitude(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    (raw / "ffiec_fdic").mkdir(parents=True)
    _write_csv(
        raw / "ffiec_fdic/deposit_interest_expense_panel.csv",
        [
            "report_date",
            "rssd_id",
            "institution_name",
            "RIAD4508",
            "RIAD0093",
            "RIADHK03",
            "RIADHK04",
        ],
        [
            ["2024-03-31", "1001", "Fixture Bank", "1000000", "0", "0", "0"],
            ["2024-03-31", "1002", "Refund Bank", "-1", "0", "0", "0"],
        ],
    )
    _write_ncua_panel(raw / "ncua/share_deposit_interest_panel.csv")

    panel = deposit_payer_flow_source_panel_rows(raw_dir=raw)
    status = safe_yield_sublane_status_rows(
        panel,
        raw_dir=raw,
        requested_period_ids=["2024Q1"],
    )

    blocked_share = Decimal(status[0]["blocked_current_ytd_share"])
    assert blocked_share > 0
    assert blocked_share < Decimal("0.000001")


def test_missing_source_panels_emit_fail_closed_artifacts(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    outputs = write_deposit_payer_flow_source_outputs(
        tmp_path / "out",
        raw_dir=raw,
        requested_period_ids=["2024Q1"],
    )

    assert outputs["source_panel_csv"].exists()
    assert outputs["source_definitions_csv"].exists()
    assert outputs["sublane_status_csv"].exists()
    assert (
        raw / "ffiec_fdic/deposit_interest_expense_panel.FAIL_CLOSED.csv"
    ).exists()
    assert (raw / "ncua/share_deposit_interest_panel.FAIL_CLOSED.csv").exists()
    assert (
        raw / "safe_yield/deposit_payer_flow_source_acquisition_fail_closed.csv"
    ).exists()
    panel_rows = list(csv.DictReader(outputs["source_panel_csv"].open()))
    status_rows = list(csv.DictReader(outputs["sublane_status_csv"].open()))
    assert {row["accepted_current_row"] for row in panel_rows} == {"false"}
    assert status_rows[0]["source_gate_status"].startswith("blocked_")
    assert "ffiec_fdic_panel_not_success" in status_rows[0]["source_gate_status"]
    assert "ncua_panel_not_success" in status_rows[0]["source_gate_status"]


def _write_ffiec_panel(path: Path) -> None:
    path.parent.mkdir(parents=True)
    _write_csv(
        path,
        [
            "report_date",
            "rssd_id",
            "institution_name",
            "RIAD4508",
            "RIAD0093",
            "RIADHK03",
            "RIADHK04",
            "RIAD4172",
        ],
        [
            ["2024-03-31", "1001", "Fixture Bank", "2000000", "1000000", "1000000", "1000000", "999000000"],
            ["2024-06-30", "1001", "Fixture Bank", "6000000", "2000000", "2000000", "2000000", "999000000"],
        ],
    )


def _write_ncua_panel(path: Path) -> None:
    path.parent.mkdir(parents=True)
    _write_csv(
        path,
        ["report_date", "charter_number", "credit_union_name", "380", "381", "340", "350"],
        [
            ["2024-03-31", "2001", "Fixture CU", "5000000", "3000000", "111000000", "222000000"],
            ["2024-06-30", "2001", "Fixture CU", "9000000", "6000000", "111000000", "222000000"],
        ],
    )


def _write_csv(path: Path, fields: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)
