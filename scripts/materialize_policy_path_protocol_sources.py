"""Materialize reviewed policy-path protocol source-context artifacts."""

from __future__ import annotations

import argparse
import csv
import html
import hashlib
import json
import math
import re
import urllib.request
import zipfile
from datetime import UTC, datetime
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET


USER_AGENT = "ratewall policy-path source-admission shanewray@example.invalid"
SF_FED_LANDING_URL = (
    "https://www.frbsf.org/research-and-insights/data-and-indicators/"
    "monetary-policy-surprises/"
)
SF_FED_CHART_CSV_URL = (
    "https://www.frbsf.org/wp-content/uploads/"
    "chart1-monetary-policy-surprises.csv?2026-05-21="
)
SF_FED_DATA_XLSX_URL = (
    "https://www.frbsf.org/wp-content/uploads/"
    "monetary-policy-surprises-data.xlsx?2026-05-21="
)
USMPD_LANDING_URL = (
    "https://www.frbsf.org/research-and-insights/data-and-indicators/"
    "us-monetary-policy-event-study-database/"
)
USMPD_XLSX_URL = "https://www.frbsf.org/wp-content/uploads/USMPD.xlsx"
USMPD_MONETARY_POLICY_SURPRISES_ZIP_URL = (
    "https://www.frbsf.org/wp-content/uploads/monetary-policy-surprises.zip"
)
USMPD_CHART1_CSV_URL = (
    "https://www.frbsf.org/wp-content/uploads/usmpd-chart1-fomc.csv?2026-05-22"
)
USMPD_CHART2_CSV_URL = (
    "https://www.frbsf.org/wp-content/uploads/usmpd-chart2-time-series.csv?2026-05-22"
)
FEDS_SOFR_LANDING_URL = (
    "https://www.federalreserve.gov/econres/feds/"
    "constructing-high-frequency-monetary-policy-surprises-from-sofr-futures.htm"
)
FEDS_SOFR_PDF_URL = (
    "https://www.federalreserve.gov/econres/feds/files/2024034pap.pdf"
)
FEDS_SOFR_ACCESSIBLE_ZIP_URL = (
    "https://www.federalreserve.gov/econres/feds/files/feds2024034.zip"
)
ACOSTA_RESEARCH_URL = "https://www.acostamiguel.com/research.html"
ACOSTA_DATAVERSE_API_URL = (
    "https://dataverse.harvard.edu/api/datasets/:persistentId"
    "?persistentId=doi:10.7910/DVN/WUXWHS"
)
ACOSTA_DATAVERSE_FILE_URL = (
    "https://dataverse.harvard.edu/api/access/datafile/10390956"
)
ACOSTA_DATAVERSE_PERSISTENT_URL = (
    "https://dataverse.harvard.edu/dataset.xhtml"
    "?persistentId=doi:10.7910/DVN/WUXWHS"
)
SF_FED_CANDIDATE_VECTOR_FIELDS = [
    "candidate_vector_source_row_id",
    "candidate_vector_row_id",
    "source_context_id",
    "source_context_row_id",
    "applicable_shock_source_id",
    "source_handle",
    "source_publisher",
    "source_data_xlsx_path",
    "source_data_xlsx_sha256",
    "sheet_name",
    "source_sheet_name",
    "sheet_role",
    "source_sheet_vintage",
    "sheet_sha256",
    "source_row_number",
    "event_sequence",
    "event_id",
    "event_date",
    "event_time",
    "raw_excel_date_serial",
    "unscheduled",
    "instrument_code",
    "instrument_family",
    "instrument_contract_slot",
    "source_horizon_label",
    "source_workbook_cell",
    "raw_workbook_value",
    "source_reported_value_raw",
    "numeric_value_available",
    "candidate_value_available",
    "source_reported_value_numeric",
    "candidate_policy_rate_change_value",
    "extraction_status",
    "candidate_vector_extraction_status",
    "unit_conversion_status",
    "horizon_mapping_status",
    "bps_year_integral_status",
    "replication_status",
    "source_admission_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "pricing_output_enabled",
    "holder_allocation_enabled",
]
SF_FED_EVENT_VECTOR_COLUMNS = ("FF1", "FF2", "ED1", "ED2", "ED3", "ED4")
POLICY_PATH_PROTOCOL_SOURCE_ACQUISITION_FIELDS = [
    "source_acquisition_row_id",
    "source_handle",
    "artifact_handle",
    "artifact_role",
    "publisher",
    "source_family",
    "source_url",
    "local_path",
    "sha256",
    "file_size_bytes",
    "content_type",
    "source_updated_date",
    "retrieved_at_utc",
    "artifact_summary",
    "artifact_inspection_summary",
    "source_protocol_relevance",
    "source_provenance_status",
    "parse_status",
    "unit_conversion_status",
    "horizon_mapping_status",
    "bps_year_integral_status",
    "replication_status",
    "source_admission_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "pricing_output_enabled",
    "holder_allocation_enabled",
    "raw_rate_shock_enabled",
    "empirical_threshold_claim_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "reset_calendar_construction_enabled",
    "source_status",
    "claim_boundary",
]
POLICY_PATH_PROTOCOL_REVIEW_INVENTORY_FIELDS = [
    "protocol_review_row_id",
    "source_handle",
    "artifact_handle",
    "source_artifact_path",
    "source_artifact_sha256",
    "review_surface",
    "review_field_name",
    "review_field_role",
    "source_sheet_or_file",
    "source_columns_or_variables",
    "source_row_count",
    "source_date_start",
    "source_date_end",
    "source_unit_text",
    "source_horizon_text",
    "source_construction_text",
    "source_replication_text",
    "source_provenance_status",
    "unit_conversion_review_status",
    "horizon_mapping_review_status",
    "bps_year_integral_review_status",
    "replication_review_status",
    "source_admission_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "current_protocol_value",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "pricing_output_enabled",
    "holder_allocation_enabled",
    "raw_rate_shock_enabled",
    "empirical_threshold_claim_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "reset_calendar_construction_enabled",
    "source_status",
    "exact_blocker",
    "evidence_needed_before_mapping",
    "evidence_needed_before_promotion",
    "next_backend_action",
    "claim_boundary",
]
USMPD_MPS_SCALAR_REPLICATION_FIELDS = [
    "replication_row_id",
    "source_handle",
    "artifact_handle",
    "source_artifact_path",
    "source_artifact_sha256",
    "source_output_file",
    "replication_target",
    "event_surface",
    "source_sheet_name",
    "source_variables",
    "selected_row_count",
    "pca_input_row_count",
    "source_output_row_count",
    "replicated_output_row_count",
    "comparable_row_count",
    "first_date",
    "last_date",
    "max_abs_diff",
    "mean_abs_diff",
    "tolerance",
    "replication_status",
    "unit_conversion_review_status",
    "horizon_mapping_review_status",
    "loadings_back_transform_status",
    "event_date_horizon_weight_status",
    "bps_year_integral_status",
    "source_admission_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "current_protocol_value",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "pricing_output_enabled",
    "holder_allocation_enabled",
    "raw_rate_shock_enabled",
    "empirical_threshold_claim_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "reset_calendar_construction_enabled",
    "source_status",
    "exact_blocker",
    "evidence_needed_before_mapping",
    "evidence_needed_before_promotion",
    "next_backend_action",
    "claim_boundary",
]
POLICY_PATH_BPS_YEAR_BLOCKER_DECISION_FIELDS = [
    "blocker_decision_row_id",
    "source_handle",
    "artifact_handle",
    "source_artifact_path",
    "source_artifact_sha256",
    "reviewed_surface",
    "reviewed_source_file_or_sheet",
    "required_bridge_field",
    "reviewed_evidence_summary",
    "reviewed_bridge_evidence_status",
    "scalar_replication_status",
    "loadings_back_transform_status",
    "event_date_horizon_weight_status",
    "bps_year_integral_status",
    "bps_year_route_decision",
    "source_admission_status",
    "protocol_admission_status",
    "policy_path_100bp_year_normalization_status",
    "current_protocol_value",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "pricing_output_enabled",
    "holder_allocation_enabled",
    "raw_rate_shock_enabled",
    "empirical_threshold_claim_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "reset_calendar_construction_enabled",
    "source_status",
    "exact_blocker",
    "evidence_needed_before_mapping",
    "evidence_needed_before_promotion",
    "next_backend_action",
    "claim_boundary",
]
XLSX_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XLSX_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XLSX_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _write_bytes(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha256(payload)


def _updated_date(page_text: str) -> str:
    match = re.search(r"Updated\s+([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", page_text)
    if not match:
        return ""
    parsed = datetime.strptime(match.group(1), "%m/%d/%Y").date()
    return parsed.isoformat()


def _csv_record_count(csv_text: str) -> int:
    lines = [line for line in csv_text.splitlines() if line.strip()]
    return max(len(lines) - 1, 0)


def _strip_html(raw: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _text_window(text: str, pattern: str, *, width: int = 420) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return ""
    start = max(0, match.start() - int(width / 3))
    end = min(len(text), match.end() + width)
    return text[start:end].strip()


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    namespace = {"m": XLSX_MAIN_NS}
    values: list[str] = []
    for item in root.findall("m:si", namespace):
        values.append("".join(text.text or "" for text in item.findall(".//m:t", namespace)))
    return values


def _column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    value = 0
    for char in letters:
        value = value * 26 + ord(char.upper()) - ord("A") + 1
    return value - 1


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(
            text.text or "" for text in cell.findall(f".//{{{XLSX_MAIN_NS}}}t")
        )
    value = cell.find(f"{{{XLSX_MAIN_NS}}}v")
    if value is None or value.text is None:
        return ""
    raw = value.text
    if cell.attrib.get("t") == "s":
        return shared_strings[int(raw)]
    return raw


def _worksheet_rows(
    archive: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]
) -> list[list[tuple[str, str]]]:
    root = ET.fromstring(archive.read(sheet_path))
    rows: list[list[tuple[str, str]]] = []
    for row in root.findall(f".//{{{XLSX_MAIN_NS}}}row"):
        cells: list[tuple[str, str]] = []
        for cell in row.findall(f"{{{XLSX_MAIN_NS}}}c"):
            ref = cell.attrib.get("r", "")
            cells.append((ref, _cell_text(cell, shared_strings)))
        rows.append(cells)
    return rows


def _sheet_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relmap = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(f"{{{XLSX_PACKAGE_REL_NS}}}Relationship")
    }
    sheets = {}
    for sheet in workbook.find(f"{{{XLSX_MAIN_NS}}}sheets") or []:
        rel_id = sheet.attrib.get(f"{{{XLSX_REL_NS}}}id", "")
        target = relmap.get(rel_id, "")
        if target:
            normalized = target.lstrip("/")
            sheets[sheet.attrib["name"]] = (
                normalized if normalized.startswith("xl/") else f"xl/{normalized}"
            )
    return sheets


def _worksheet_matrix(
    archive: zipfile.ZipFile, sheet_name: str
) -> list[dict[str, str]]:
    shared_strings = _xlsx_shared_strings(archive)
    sheet_targets = _sheet_targets(archive)
    sheet_path = sheet_targets.get(sheet_name, "")
    if not sheet_path:
        return []
    rows = []
    for row in _worksheet_rows(archive, sheet_path, shared_strings):
        rows.append({"".join(ch for ch in ref if ch.isalpha()): value for ref, value in row})
    return rows


def _xlsx_header_stats(path: Path, sheet_name: str) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        rows = _worksheet_matrix(archive, sheet_name)
    if not rows:
        return {
            "headers": "",
            "row_count": "0",
            "first_date": "",
            "last_date": "",
        }
    headers = rows[0]
    header_by_col = {col: value for col, value in headers.items() if value}
    date_col = next(
        (col for col, value in header_by_col.items() if value in {"Date", "date"}),
        "",
    )
    dates = []
    for row in rows[1:]:
        raw_date = row.get(date_col, "")
        parsed = _excel_serial_date(raw_date) if raw_date else ""
        if parsed:
            dates.append(parsed)
    return {
        "headers": ";".join(header_by_col.values()),
        "row_count": str(max(0, len(rows) - 1)),
        "first_date": min(dates) if dates else "",
        "last_date": max(dates) if dates else "",
    }


def _excel_serial_date(raw: str) -> str:
    try:
        serial = int(float(raw))
    except ValueError:
        return raw
    return (date(1899, 12, 30) + timedelta(days=serial)).isoformat()


def _numeric_or_blank(raw: str) -> str:
    if raw.upper() == "NA" or raw == "":
        return ""
    try:
        return f"{float(raw):.12g}"
    except ValueError:
        return ""


def _source_horizon_label(instrument: str) -> str:
    labels = {
        "FF1": "current_month_federal_funds_futures",
        "FF2": "next_month_federal_funds_futures",
        "ED1": "current_quarter_money_market_futures",
        "ED2": "next_quarter_money_market_futures",
        "ED3": "two_quarter_ahead_money_market_futures",
        "ED4": "three_quarter_ahead_money_market_futures",
    }
    return labels.get(instrument, "")


def _candidate_vector_rows(xlsx_path: Path, *, xlsx_sha: str) -> list[dict[str, str]]:
    source_context_id = "sf_fed_monetary_policy_surprises_policy_path_protocol_context"
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(xlsx_path) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        sheet_targets = _sheet_targets(archive)
        for sheet_name, sheet_role, sheet_vintage in [
            ("FOMC (update 2023)", "updated_fomc_event_workbook_sheet", "update_2023"),
            ("FOMC (original)", "original_fomc_event_workbook_sheet", "original"),
        ]:
            sheet_path = sheet_targets.get(sheet_name, "")
            if not sheet_path:
                raise ValueError(f"required SF Fed workbook sheet missing: {sheet_name}")
            sheet_payload = archive.read(sheet_path)
            sheet_sha = _sha256(sheet_payload)
            worksheet_rows = _worksheet_rows(archive, sheet_path, shared_strings)
            if not worksheet_rows:
                raise ValueError(f"required SF Fed workbook sheet is empty: {sheet_name}")
            header_cells = worksheet_rows[0]
            header_by_column = {
                _column_index(ref): value for ref, value in header_cells if value
            }
            column_by_header = {value: index for index, value in header_by_column.items()}
            required_headers = {
                "Date",
                "Time",
                "Unscheduled",
                *SF_FED_EVENT_VECTOR_COLUMNS,
            }
            missing_headers = sorted(required_headers - set(column_by_header))
            if missing_headers:
                raise ValueError(
                    f"required SF Fed workbook headers missing from {sheet_name}: "
                    + ",".join(missing_headers)
                )
            selected_columns = [
                (instrument, column_by_header[instrument])
                for instrument in SF_FED_EVENT_VECTOR_COLUMNS
            ]
            for event_sequence, row in enumerate(worksheet_rows[1:], start=1):
                values = {_column_index(ref): (ref, value) for ref, value in row}
                date_value = values.get(column_by_header.get("Date", -1), ("", ""))[1]
                time_value = values.get(column_by_header.get("Time", -1), ("", ""))[1]
                unscheduled = values.get(
                    column_by_header.get("Unscheduled", -1), ("", "")
                )[1]
                event_date = _excel_serial_date(date_value)
                if not event_date:
                    continue
                for instrument, column_index in selected_columns:
                    cell_ref, raw_value = values.get(column_index, ("", ""))
                    numeric_candidate = _numeric_or_blank(raw_value)
                    extraction_status = (
                        "pass_source_workbook_cell_extracted"
                        if numeric_candidate
                        else "blocked_source_value_missing_or_na"
                    )
                    row_id = (
                        "sf_fed_candidate_event_vector::"
                        f"{sheet_vintage}::{event_sequence:04d}::{instrument}"
                    )
                    rows.append(
                        {
                            "candidate_vector_source_row_id": row_id,
                            "candidate_vector_row_id": row_id,
                            "source_context_id": source_context_id,
                            "source_context_row_id": source_context_id,
                            "applicable_shock_source_id": (
                                "sf_fed_monetary_policy_surprises"
                            ),
                            "source_handle": "sf_fed_monetary_policy_surprises",
                            "source_publisher": (
                                "Federal Reserve Bank of San Francisco"
                            ),
                            "source_data_xlsx_path": str(xlsx_path),
                            "source_data_xlsx_sha256": xlsx_sha,
                            "sheet_name": sheet_name,
                            "source_sheet_name": sheet_name,
                            "sheet_role": sheet_role,
                            "source_sheet_vintage": sheet_vintage,
                            "sheet_sha256": sheet_sha,
                            "source_row_number": str(event_sequence + 1),
                            "event_sequence": str(event_sequence),
                            "event_id": (
                                f"{sheet_vintage}::{event_sequence:04d}::{event_date}"
                            ),
                            "event_date": event_date,
                            "event_time": time_value,
                            "raw_excel_date_serial": date_value,
                            "unscheduled": unscheduled,
                            "instrument_code": instrument,
                            "instrument_family": (
                                "federal_funds_futures"
                                if instrument.startswith("FF")
                                else "sofr_futures_source_labeled_ed_columns"
                                if event_date >= "2023-01-01"
                                else "eurodollar_futures"
                            ),
                            "instrument_contract_slot": instrument[2:],
                            "source_horizon_label": _source_horizon_label(instrument),
                            "source_workbook_cell": cell_ref,
                            "raw_workbook_value": raw_value,
                            "source_reported_value_raw": raw_value,
                            "numeric_value_available": (
                                "true" if numeric_candidate else "false"
                            ),
                            "candidate_value_available": (
                                "true" if numeric_candidate else "false"
                            ),
                            "source_reported_value_numeric": numeric_candidate,
                            "candidate_policy_rate_change_value": numeric_candidate,
                            "extraction_status": extraction_status,
                            "candidate_vector_extraction_status": extraction_status,
                            "unit_conversion_status": (
                                "blocked_no_reviewed_source_unit_conversion"
                            ),
                            "horizon_mapping_status": (
                                "blocked_no_reviewed_event_date_specific_horizon_grid"
                            ),
                            "bps_year_integral_status": (
                                "blocked_no_reviewed_bps_year_integral_formula"
                            ),
                            "replication_status": "blocked_no_independent_replication",
                            "source_admission_status": (
                                "blocked_diagnostic_candidate_vector_only"
                            ),
                            "protocol_admission_status": (
                                "blocked_candidate_vector_missing_unit_horizon_"
                                "integral_replication"
                            ),
                            "policy_path_100bp_year_normalization_status": (
                                "blocked_no_admitted_bps_year_policy_path"
                            ),
                            "enters_main_ratio": "false",
                            "evidence_mode_enabled": "false",
                            "pricing_output_enabled": "false",
                            "holder_allocation_enabled": "false",
                        }
                    )
    return rows


def _write_description_sheet_csv(path: Path, xlsx_path: Path) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(xlsx_path) as archive:
        rows = _worksheet_matrix(archive, "Description")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["description_row_number", "column_a", "column_b"]
        )
        writer.writeheader()
        for idx, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "description_row_number": idx,
                    "column_a": row.get("A", ""),
                    "column_b": row.get("B", ""),
                }
            )
    return _sha256(path.read_bytes()), len(rows)


def _write_candidate_vector_csv(path: Path, rows: list[dict[str, str]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SF_FED_CANDIDATE_VECTOR_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return _sha256(path.read_bytes())


def _zip_entries_summary(path: Path) -> str:
    if path.suffix.lower() != ".zip":
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            entries = sorted(
                name for name in archive.namelist() if not name.endswith("/")
            )
    except zipfile.BadZipFile:
        return "zip_unreadable"
    sample = ";".join(entries[:12])
    return f"entry_count={len(entries)};sample={sample}"


def _xlsx_sheets_summary(path: Path) -> str:
    if path.suffix.lower() != ".xlsx":
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            sheets = sorted(_sheet_targets(archive))
    except (KeyError, zipfile.BadZipFile, ET.ParseError):
        return "xlsx_unreadable"
    return f"sheet_count={len(sheets)};sheets={';'.join(sheets[:16])}"


def _json_summary(path: Path) -> str:
    if path.suffix.lower() != ".json":
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "json_unreadable"
    if isinstance(payload, dict):
        status = payload.get("status", "")
        latest = payload.get("data", {}).get("latestVersion", {})
        files = latest.get("files", []) if isinstance(latest, dict) else []
        return f"json_object_keys={len(payload)};status={status};file_count={len(files)}"
    return f"json_type={type(payload).__name__}"


def _artifact_inspection_summary(path: Path) -> str:
    return (
        _zip_entries_summary(path)
        or _xlsx_sheets_summary(path)
        or _json_summary(path)
        or "inspection_not_required_for_raw_provenance"
    )


def _source_acquisition_specs() -> list[dict[str, str]]:
    return [
        {
            "source_handle": "sf_fed_usmpd",
            "artifact_handle": "sf_fed_usmpd_landing_page",
            "artifact_role": "landing_page_html",
            "publisher": "Federal Reserve Bank of San Francisco",
            "source_family": "usmpd_event_study_database",
            "source_url": USMPD_LANDING_URL,
            "filename": "sf_fed_usmpd_landing_page.html",
            "content_type": "text/html",
            "source_protocol_relevance": (
                "USMPD landing page documents event-study windows, instruments, "
                "percentage-point units for charted rate changes, and downloadable "
                "data/code artifacts."
            ),
        },
        {
            "source_handle": "sf_fed_usmpd",
            "artifact_handle": "sf_fed_usmpd_xlsx",
            "artifact_role": "event_study_database_xlsx",
            "publisher": "Federal Reserve Bank of San Francisco",
            "source_family": "usmpd_event_study_database",
            "source_url": USMPD_XLSX_URL,
            "filename": "sf_fed_usmpd.xlsx",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "source_protocol_relevance": (
                "Raw USMPD event-study workbook candidate for future unit, "
                "horizon, and replication review."
            ),
        },
        {
            "source_handle": "sf_fed_usmpd",
            "artifact_handle": "sf_fed_usmpd_monetary_policy_surprises_zip",
            "artifact_role": "construction_code_and_output_zip",
            "publisher": "Federal Reserve Bank of San Francisco",
            "source_family": "usmpd_policy_surprise_construction",
            "source_url": USMPD_MONETARY_POLICY_SURPRISES_ZIP_URL,
            "filename": "sf_fed_usmpd_monetary_policy_surprises.zip",
            "content_type": "application/zip",
            "source_protocol_relevance": (
                "R code/output bundle for constructing monetary-policy surprises "
                "from USMPD; candidate replication material only."
            ),
        },
        {
            "source_handle": "sf_fed_usmpd",
            "artifact_handle": "sf_fed_usmpd_chart1_csv",
            "artifact_role": "landing_page_chart_csv",
            "publisher": "Federal Reserve Bank of San Francisco",
            "source_family": "usmpd_context_chart",
            "source_url": USMPD_CHART1_CSV_URL,
            "filename": "sf_fed_usmpd_chart1_fomc.csv",
            "content_type": "text/csv",
            "source_protocol_relevance": (
                "Small public chart context; not a protocol input or bps-year output."
            ),
        },
        {
            "source_handle": "sf_fed_usmpd",
            "artifact_handle": "sf_fed_usmpd_chart2_csv",
            "artifact_role": "landing_page_chart_csv",
            "publisher": "Federal Reserve Bank of San Francisco",
            "source_family": "usmpd_context_chart",
            "source_url": USMPD_CHART2_CSV_URL,
            "filename": "sf_fed_usmpd_chart2_time_series.csv",
            "content_type": "text/csv",
            "source_protocol_relevance": (
                "Small public chart context; not a protocol input or bps-year output."
            ),
        },
        {
            "source_handle": "fed_sofr_continuity",
            "artifact_handle": "fed_sofr_continuity_landing_page",
            "artifact_role": "feds_note_html",
            "publisher": "Board of Governors of the Federal Reserve System",
            "source_family": "sofr_continuity_research_note",
            "source_url": FEDS_SOFR_LANDING_URL,
            "filename": "fed_sofr_continuity_landing_page.html",
            "content_type": "text/html",
            "source_protocol_relevance": (
                "FEDS page documenting Eurodollar-to-SOFR continuity and "
                "recommended SOFR use from January 2022 onward."
            ),
        },
        {
            "source_handle": "fed_sofr_continuity",
            "artifact_handle": "fed_sofr_continuity_pdf",
            "artifact_role": "feds_note_pdf",
            "publisher": "Board of Governors of the Federal Reserve System",
            "source_family": "sofr_continuity_research_note",
            "source_url": FEDS_SOFR_PDF_URL,
            "filename": "fed_sofr_continuity_2024034pap.pdf",
            "content_type": "application/pdf",
            "source_protocol_relevance": (
                "Research note for continuity review; not parsed into a "
                "RateWall bps-year protocol this tranche."
            ),
        },
        {
            "source_handle": "fed_sofr_continuity",
            "artifact_handle": "fed_sofr_continuity_accessible_zip",
            "artifact_role": "feds_accessible_materials_zip",
            "publisher": "Board of Governors of the Federal Reserve System",
            "source_family": "sofr_continuity_research_note",
            "source_url": FEDS_SOFR_ACCESSIBLE_ZIP_URL,
            "filename": "fed_sofr_continuity_accessible_materials.zip",
            "content_type": "application/zip",
            "source_protocol_relevance": (
                "Accessible materials bundle for SOFR continuity review; "
                "candidate replication/provenance material only."
            ),
        },
        {
            "source_handle": "acosta_sofr_gss_updates",
            "artifact_handle": "acosta_research_page",
            "artifact_role": "research_page_html",
            "publisher": "Miguel Acosta",
            "source_family": "sofr_gss_ns_update_pointer",
            "source_url": ACOSTA_RESEARCH_URL,
            "filename": "acosta_research_page.html",
            "content_type": "text/html",
            "source_protocol_relevance": (
                "Author page pointer to updated GSS/Nakamura-Steinsson shocks "
                "on Harvard Dataverse."
            ),
        },
        {
            "source_handle": "acosta_sofr_gss_updates",
            "artifact_handle": "acosta_dataverse_metadata_json",
            "artifact_role": "dataverse_metadata_json",
            "publisher": "Harvard Dataverse",
            "source_family": "sofr_gss_ns_update_replication",
            "source_url": ACOSTA_DATAVERSE_API_URL,
            "filename": "acosta_sofr_gss_dataverse_metadata.json",
            "content_type": "application/json",
            "source_protocol_relevance": (
                "Dataverse metadata for updated GSS/Nakamura-Steinsson shocks; "
                "metadata only until file contents are reviewed."
            ),
        },
        {
            "source_handle": "acosta_sofr_gss_updates",
            "artifact_handle": "acosta_abj_2024_monetary_policy_surprises_xlsx",
            "artifact_role": "dataverse_updated_shocks_xlsx",
            "publisher": "Harvard Dataverse",
            "source_family": "sofr_gss_ns_update_replication",
            "source_url": ACOSTA_DATAVERSE_FILE_URL,
            "filename": "acosta_abj_2024_monetary_policy_surprises.xlsx",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "source_protocol_relevance": (
                "Updated shocks workbook from Dataverse; blocked replication "
                "target until units, loadings/back-transform, horizon mapping, "
                "and bps-year formula are reviewed."
            ),
        },
    ]


def _write_source_acquisition_registry(
    output_dir: Path,
    *,
    retrieved_at: str,
) -> tuple[Path, str, list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    for rank, spec in enumerate(_source_acquisition_specs(), start=1):
        payload = _fetch(spec["source_url"])
        local_path = output_dir / spec["filename"]
        sha = _write_bytes(local_path, payload)
        text = payload.decode("utf-8", errors="ignore")
        source_updated_date = _updated_date(text)
        if spec["artifact_handle"] == "acosta_dataverse_metadata_json":
            try:
                metadata = json.loads(text)
                source_updated_date = (
                    metadata.get("data", {})
                    .get("latestVersion", {})
                    .get("releaseTime", "")
                    .split("T")[0]
                )
            except json.JSONDecodeError:
                source_updated_date = ""
        rows.append(
            {
                "source_acquisition_row_id": (
                    f"policy_path_protocol_source_acquisition::{rank:02d}_"
                    f"{spec['artifact_handle']}"
                ),
                "source_handle": spec["source_handle"],
                "artifact_handle": spec["artifact_handle"],
                "artifact_role": spec["artifact_role"],
                "publisher": spec["publisher"],
                "source_family": spec["source_family"],
                "source_url": spec["source_url"],
                "local_path": str(local_path),
                "sha256": sha,
                "file_size_bytes": str(len(payload)),
                "content_type": spec["content_type"],
                "source_updated_date": source_updated_date,
                "retrieved_at_utc": retrieved_at,
                "artifact_summary": spec["source_protocol_relevance"],
                "artifact_inspection_summary": _artifact_inspection_summary(local_path),
                "source_protocol_relevance": spec["source_protocol_relevance"],
                "source_provenance_status": "source_artifact_acquired_with_hash",
                "parse_status": "blocked_not_parsed_for_bps_year_protocol",
                "unit_conversion_status": "blocked_no_reviewed_source_unit_conversion",
                "horizon_mapping_status": (
                    "blocked_no_reviewed_event_date_specific_horizon_grid"
                ),
                "bps_year_integral_status": (
                    "blocked_no_reviewed_bps_year_integral_formula"
                ),
                "replication_status": "blocked_no_independent_replication",
                "source_admission_status": (
                    "blocked_raw_protocol_source_artifact_review_only"
                ),
                "protocol_admission_status": (
                    "blocked_acquired_artifact_missing_unit_horizon_integral_replication"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                "denominator_prior_update_allowed": "false",
                "prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_offset_ratio_changed_this_tranche": "false",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "pricing_output_enabled": "false",
                "holder_allocation_enabled": "false",
                "raw_rate_shock_enabled": "false",
                "empirical_threshold_claim_enabled": "false",
                "empirical_claim_enabled": "false",
                "policy_failure_claim_enabled": "false",
                "causal_financialization_claim_enabled": "false",
                "incidence_claim_enabled": "false",
                "welfare_claim_enabled": "false",
                "tax_output_enabled": "false",
                "mpc_output_enabled": "false",
                "reset_calendar_construction_enabled": "false",
                "source_status": "policy_path_protocol_source_acquisition_fail_closed",
                "claim_boundary": (
                    "policy_path_protocol_source_acquisition_not_bps_year_or_runtime_input"
                ),
            }
        )
    registry_path = output_dir / "policy_path_protocol_source_acquisition_registry.csv"
    with registry_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=POLICY_PATH_PROTOCOL_SOURCE_ACQUISITION_FIELDS
        )
        writer.writeheader()
        writer.writerows(rows)
    return registry_path, _sha256(registry_path.read_bytes()), rows


def _protocol_review_false_fields() -> dict[str, str]:
    return {
        "denominator_prior_update_allowed": "false",
        "prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_offset_ratio_changed_this_tranche": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "canonical_ratio_entry": "false",
        "pricing_output_enabled": "false",
        "holder_allocation_enabled": "false",
        "raw_rate_shock_enabled": "false",
        "empirical_threshold_claim_enabled": "false",
        "empirical_claim_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "causal_financialization_claim_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
        "tax_output_enabled": "false",
        "mpc_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
    }


def _protocol_review_row(
    *,
    rank: int,
    source_handle: str,
    artifact_handle: str,
    source_artifact_path: str,
    source_artifact_sha256: str,
    review_surface: str,
    review_field_name: str,
    review_field_role: str,
    source_sheet_or_file: str = "",
    source_columns_or_variables: str = "",
    source_row_count: str = "",
    source_date_start: str = "",
    source_date_end: str = "",
    source_unit_text: str = "",
    source_horizon_text: str = "",
    source_construction_text: str = "",
    source_replication_text: str = "",
    unit_conversion_review_status: str = "blocked_no_reviewed_source_unit_conversion",
    horizon_mapping_review_status: str = (
        "blocked_no_reviewed_event_date_specific_horizon_grid"
    ),
    bps_year_integral_review_status: str = (
        "blocked_no_reviewed_bps_year_integral_formula"
    ),
    replication_review_status: str = "blocked_no_independent_replication",
    exact_blocker: str,
    evidence_needed_before_mapping: str,
    evidence_needed_before_promotion: str,
    next_backend_action: str,
) -> dict[str, str]:
    return {
        "protocol_review_row_id": (
            f"policy_path_protocol_review::{rank:02d}_{review_surface}_"
            f"{review_field_name}"
        ),
        "source_handle": source_handle,
        "artifact_handle": artifact_handle,
        "source_artifact_path": source_artifact_path,
        "source_artifact_sha256": source_artifact_sha256,
        "review_surface": review_surface,
        "review_field_name": review_field_name,
        "review_field_role": review_field_role,
        "source_sheet_or_file": source_sheet_or_file,
        "source_columns_or_variables": source_columns_or_variables,
        "source_row_count": source_row_count,
        "source_date_start": source_date_start,
        "source_date_end": source_date_end,
        "source_unit_text": source_unit_text,
        "source_horizon_text": source_horizon_text,
        "source_construction_text": source_construction_text,
        "source_replication_text": source_replication_text,
        "source_provenance_status": "source_artifact_acquired_with_hash",
        "unit_conversion_review_status": unit_conversion_review_status,
        "horizon_mapping_review_status": horizon_mapping_review_status,
        "bps_year_integral_review_status": bps_year_integral_review_status,
        "replication_review_status": replication_review_status,
        "source_admission_status": "blocked_protocol_review_inventory_only",
        "protocol_admission_status": (
            "blocked_reviewed_context_missing_bps_year_admission_fields"
        ),
        "policy_path_100bp_year_normalization_status": (
            "blocked_no_admitted_bps_year_policy_path"
        ),
        "current_protocol_value": "",
        "bps_year_exposure_output": "",
        "candidate_gdp_share_drag_per_100bp_year": "",
        **_protocol_review_false_fields(),
        "source_status": "policy_path_protocol_review_inventory_fail_closed",
        "exact_blocker": exact_blocker,
        "evidence_needed_before_mapping": evidence_needed_before_mapping,
        "evidence_needed_before_promotion": evidence_needed_before_promotion,
        "next_backend_action": next_backend_action,
        "claim_boundary": (
            "policy_path_protocol_review_inventory_not_bps_year_or_runtime_input"
        ),
    }


def _write_protocol_review_inventory(
    output_dir: Path,
    *,
    source_acquisition_rows: list[dict[str, str]],
) -> tuple[Path, str, list[dict[str, str]]]:
    by_artifact = {row["artifact_handle"]: row for row in source_acquisition_rows}

    def artifact(handle: str) -> tuple[str, str]:
        row = by_artifact[handle]
        return row["local_path"], row["sha256"]

    rows: list[dict[str, str]] = []
    rank = 1

    usmpd_page_path, usmpd_page_sha = artifact("sf_fed_usmpd_landing_page")
    usmpd_page_text = _strip_html(Path(usmpd_page_path).read_text(encoding="utf-8"))
    rows.append(
        _protocol_review_row(
            rank=rank,
            source_handle="sf_fed_usmpd",
            artifact_handle="sf_fed_usmpd_landing_page",
            source_artifact_path=usmpd_page_path,
            source_artifact_sha256=usmpd_page_sha,
            review_surface="usmpd_landing_page",
            review_field_name="money_market_futures_one_year_path_context",
            review_field_role="horizon_and_construction_context",
            source_sheet_or_file="landing_page_html",
            source_horizon_text=_text_window(
                usmpd_page_text, r"covering approximately a one-year horizon"
            ),
            source_construction_text=_text_window(
                usmpd_page_text, r"first principal component"
            ),
            unit_conversion_review_status="blocked_landing_page_unit_context_not_column_protocol",
            horizon_mapping_review_status=(
                "blocked_approximately_one_year_context_not_event_date_weights"
            ),
            replication_review_status=(
                "blocked_landing_page_references_code_without_local_replication"
            ),
            exact_blocker=(
                "USMPD landing page gives one-year-path and first-PC context, "
                "but not event-date-specific horizon weights or a bps-year "
                "integration formula."
            ),
            evidence_needed_before_mapping=(
                "Review construction code and workbook fields into a source-backed "
                "unit, horizon, and integral contract."
            ),
            evidence_needed_before_promotion=(
                "Independent replication and a separate promotion gate are still "
                "required before denominator-prior or runtime use."
            ),
            next_backend_action="parse_usmpd_workbook_and_mps_code_protocol_fields",
        )
    )
    rank += 1
    rows.append(
        _protocol_review_row(
            rank=rank,
            source_handle="sf_fed_usmpd",
            artifact_handle="sf_fed_usmpd_landing_page",
            source_artifact_path=usmpd_page_path,
            source_artifact_sha256=usmpd_page_sha,
            review_surface="usmpd_landing_page",
            review_field_name="percentage_point_units_context",
            review_field_role="unit_context",
            source_sheet_or_file="landing_page_html",
            source_unit_text=_text_window(
                usmpd_page_text, r"measured in percentage points"
            ),
            unit_conversion_review_status=(
                "reviewed_source_text_percentage_points_context_only"
            ),
            exact_blocker=(
                "The page states percentage-point units for charted rate changes "
                "and surprises, but RateWall still lacks a column-by-column "
                "unit-to-bps-year mapping."
            ),
            evidence_needed_before_mapping=(
                "Tie source unit text to each workbook/code field used in the "
                "path protocol."
            ),
            evidence_needed_before_promotion=(
                "Unit mapping must combine with horizon weights, integral, and "
                "replication before promotion."
            ),
            next_backend_action="map_usmpd_unit_text_to_candidate_fields",
        )
    )
    rank += 1

    usmpd_xlsx_path, usmpd_xlsx_sha = artifact("sf_fed_usmpd_xlsx")
    for sheet in ["Statements", "Press Conferences", "Monetary Events", "Minutes"]:
        stats = _xlsx_header_stats(Path(usmpd_xlsx_path), sheet)
        rows.append(
            _protocol_review_row(
                rank=rank,
                source_handle="sf_fed_usmpd",
                artifact_handle="sf_fed_usmpd_xlsx",
                source_artifact_path=usmpd_xlsx_path,
                source_artifact_sha256=usmpd_xlsx_sha,
                review_surface="usmpd_workbook_schema",
                review_field_name=f"{sheet.lower().replace(' ', '_')}_headers",
                review_field_role="event_level_market_data_schema",
                source_sheet_or_file=sheet,
                source_columns_or_variables=stats["headers"],
                source_row_count=stats["row_count"],
                source_date_start=stats["first_date"],
                source_date_end=stats["last_date"],
                source_unit_text="workbook cells require external data-dictionary unit review",
                source_horizon_text="MP/FF/ED/OIS/UST/TIPS instrument columns; no row-specific horizon weights",
                unit_conversion_review_status=(
                    "blocked_workbook_schema_has_rate_change_columns_without_unit_contract"
                ),
                horizon_mapping_review_status=(
                    "blocked_workbook_schema_has_instrument_slots_without_event_date_weights"
                ),
                exact_blocker=(
                    f"USMPD sheet {sheet} exposes event-level instrument columns, "
                    "but the schema alone does not provide a bps-year path "
                    "integral."
                ),
                evidence_needed_before_mapping=(
                    "Review source documentation/code to map each selected "
                    "instrument field to units and event-date horizon weights."
                ),
                evidence_needed_before_promotion=(
                    "A replicated bps-year conversion must pass before any "
                    "runtime use."
                ),
                next_backend_action="derive_review_contract_from_usmpd_code_not_schema_alone",
            )
        )
        rank += 1

    mps_zip_path, mps_zip_sha = artifact("sf_fed_usmpd_monetary_policy_surprises_zip")
    with zipfile.ZipFile(mps_zip_path) as archive:
        readme_text = archive.read("README.md").decode("utf-8", errors="ignore")
        code_text = archive.read("mps.R").decode("utf-8", errors="ignore")
        mps_rows = archive.read("mps.csv").decode("utf-8", errors="ignore")
        minutes_rows = archive.read("mps_minutes.csv").decode("utf-8", errors="ignore")
    rows.append(
        _protocol_review_row(
            rank=rank,
            source_handle="sf_fed_usmpd",
            artifact_handle="sf_fed_usmpd_monetary_policy_surprises_zip",
            source_artifact_path=mps_zip_path,
            source_artifact_sha256=mps_zip_sha,
            review_surface="usmpd_mps_readme",
            review_field_name="mps_percentage_point_units_and_y1_normalization",
            review_field_role="unit_and_normalization_context",
            source_sheet_or_file="README.md",
            source_unit_text=_text_window(readme_text, r"percentage points"),
            source_construction_text=_text_window(readme_text, r"one-for-one impact"),
            unit_conversion_review_status=(
                "reviewed_source_text_percentage_points_for_underlying_changes"
            ),
            horizon_mapping_review_status=(
                "blocked_mps_scalar_normalization_not_bps_year_horizon_grid"
            ),
            exact_blocker=(
                "README provides percentage-point unit context and one-year "
                "Treasury-yield normalization for scalar MPS outputs, not a "
                "bps-year exposure vector."
            ),
            evidence_needed_before_mapping=(
                "Map selected input futures columns to event-specific horizons "
                "and convert scalar normalization into an admitted bps-year rule, "
                "if a source supports that conversion."
            ),
            evidence_needed_before_promotion=(
                "Independent replication plus bps-year admission gates must pass."
            ),
            next_backend_action="review_mps_code_for_replicable_scalar_construction_only",
        )
    )
    rank += 1
    rows.append(
        _protocol_review_row(
            rank=rank,
            source_handle="sf_fed_usmpd",
            artifact_handle="sf_fed_usmpd_monetary_policy_surprises_zip",
            source_artifact_path=mps_zip_path,
            source_artifact_sha256=mps_zip_sha,
            review_surface="usmpd_mps_code",
            review_field_name="mps_r_selected_variables",
            review_field_role="construction_method_context",
            source_sheet_or_file="mps.R",
            source_columns_or_variables="Date;MP1;MP2;ED2;ED3;ED4;PC1;SVENY01;dy1;MPS",
            source_construction_text=_text_window(code_text, r"MP1, MP2, ED2, ED3, ED4"),
            source_replication_text=_text_window(code_text, r"write_csv"),
            unit_conversion_review_status=(
                "reviewed_with_readme_percentage_point_context_for_inputs"
            ),
            horizon_mapping_review_status=(
                "blocked_selected_ed_slots_not_event_date_horizon_weights"
            ),
            replication_review_status=(
                "blocked_source_code_and_output_present_not_independent_replication"
            ),
            exact_blocker=(
                "mps.R documents a scalar first-PC construction normalized to "
                "the one-year Treasury yield, but it does not output a bps-year "
                "path vector."
            ),
            evidence_needed_before_mapping=(
                "Run/replicate the code and decide whether any source-backed "
                "back-transform to horizon exposures exists."
            ),
            evidence_needed_before_promotion=(
                "Scalar MPS replication is not enough; bps-year path exposure "
                "and promotion gates are required."
            ),
            next_backend_action="replicate_mps_scalar_outputs_then_assess_back_transform_blocker",
        )
    )
    rank += 1
    for file_name, text in [("mps.csv", mps_rows), ("mps_minutes.csv", minutes_rows)]:
        rows.append(
            _protocol_review_row(
                rank=rank,
                source_handle="sf_fed_usmpd",
                artifact_handle="sf_fed_usmpd_monetary_policy_surprises_zip",
                source_artifact_path=mps_zip_path,
                source_artifact_sha256=mps_zip_sha,
                review_surface="usmpd_mps_output",
                review_field_name=f"{file_name.replace('.', '_')}_scalar_outputs",
                review_field_role="replication_target_context",
                source_sheet_or_file=file_name,
                source_columns_or_variables=";".join(text.splitlines()[0].split(",")),
                source_row_count=str(_csv_record_count(text)),
                source_date_start=text.splitlines()[1].split(",")[0]
                if len(text.splitlines()) > 1
                else "",
                source_date_end=text.splitlines()[-1].split(",")[0]
                if len(text.splitlines()) > 1
                else "",
                source_replication_text=(
                    "source-provided scalar surprise CSV available as replication target"
                ),
                unit_conversion_review_status=(
                    "reviewed_with_readme_percentage_point_context_for_scalar_outputs"
                ),
                horizon_mapping_review_status=(
                    "blocked_scalar_output_not_horizon_grid"
                ),
                replication_review_status=(
                    "blocked_source_output_present_not_independent_replication"
                ),
                exact_blocker=(
                    f"{file_name} is a source-provided scalar MPS output, not a "
                    "bps-year event-horizon vector."
                ),
                evidence_needed_before_mapping=(
                    "Replicate scalar output and find source-backed vector "
                    "loadings/horizon conversion before mapping."
                ),
                evidence_needed_before_promotion=(
                    "A scalar replication target cannot enter denominator priors "
                    "without bps-year conversion and promotion gates."
                ),
                next_backend_action="replicate_source_mps_csv_without_runtime_promotion",
            )
        )
        rank += 1

    sofr_path, sofr_sha = artifact("fed_sofr_continuity_accessible_zip")
    with zipfile.ZipFile(sofr_path) as archive:
        sofr_text = _strip_html(
            archive.read("index.html").decode("utf-8", errors="ignore")
        )
    for field_name, pattern, role in [
        (
            "sofr_switch_date_recommendation",
            r"recommend using SOFR futures starting in January 2022",
            "continuity_switch_context",
        ),
        (
            "sofr_eurodollar_contract_substitution",
            r"third-, fourth-, and fifth-outstanding SOFR contracts",
            "contract_mapping_context",
        ),
    ]:
        rows.append(
            _protocol_review_row(
                rank=rank,
                source_handle="fed_sofr_continuity",
                artifact_handle="fed_sofr_continuity_accessible_zip",
                source_artifact_path=sofr_path,
                source_artifact_sha256=sofr_sha,
                review_surface="fed_sofr_continuity_accessible_text",
                review_field_name=field_name,
                review_field_role=role,
                source_sheet_or_file="index.html",
                source_horizon_text=_text_window(sofr_text, pattern),
                source_construction_text=_text_window(sofr_text, r"GSS and NS series"),
                unit_conversion_review_status=(
                    "blocked_sofr_note_context_not_rate_change_unit_protocol"
                ),
                horizon_mapping_review_status=(
                    "reviewed_sofr_eurodollar_contract_mapping_context_only"
                ),
                replication_review_status=(
                    "blocked_updated_factor_series_present_elsewhere_not_replicated"
                ),
                exact_blocker=(
                    "SOFR continuity text supplies substitution context for "
                    "Eurodollar futures, but not RateWall bps-year weights or "
                    "integral output."
                ),
                evidence_needed_before_mapping=(
                    "Combine SOFR substitution with event-date contract intervals "
                    "and source-backed rate-change units."
                ),
                evidence_needed_before_promotion=(
                    "Replicated bps-year exposure remains required before runtime use."
                ),
                next_backend_action="map_sofr_substitution_context_to_blocked_protocol_requirements",
            )
        )
        rank += 1

    acosta_xlsx_path, acosta_xlsx_sha = artifact(
        "acosta_abj_2024_monetary_policy_surprises_xlsx"
    )
    acosta_stats = _xlsx_header_stats(Path(acosta_xlsx_path), "Data")
    rows.append(
        _protocol_review_row(
            rank=rank,
            source_handle="acosta_sofr_gss_updates",
            artifact_handle="acosta_abj_2024_monetary_policy_surprises_xlsx",
            source_artifact_path=acosta_xlsx_path,
            source_artifact_sha256=acosta_xlsx_sha,
            review_surface="acosta_abj_updated_shocks_workbook",
            review_field_name="updated_gss_ns_factor_series",
            review_field_role="factor_series_replication_target_context",
            source_sheet_or_file="Data",
            source_columns_or_variables=acosta_stats["headers"],
            source_row_count=acosta_stats["row_count"],
            source_date_start=acosta_stats["first_date"],
            source_date_end=acosta_stats["last_date"],
            source_construction_text=(
                "Info sheet describes three series as factors of an instrument "
                "set containing intraday changes around FOMC announcements of "
                "federal funds futures, Eurodollar futures, and SOFR futures."
            ),
            source_replication_text="Data columns: date;GSS_target;GSS_path;NS",
            unit_conversion_review_status=(
                "blocked_factor_series_not_rate_change_unit_protocol"
            ),
            horizon_mapping_review_status=(
                "blocked_factor_series_lacks_loadings_and_horizon_weights"
            ),
            replication_review_status=(
                "blocked_factor_series_target_present_not_independently_replicated"
            ),
            exact_blocker=(
                "Acosta/GSS workbook provides updated scalar factor series, but "
                "not loadings/back-transform or horizon weights needed for a "
                "bps-year RateWall input."
            ),
            evidence_needed_before_mapping=(
                "Obtain or derive reviewed loadings/back-transform and event-date "
                "horizon weights before any bps-year mapping."
            ),
            evidence_needed_before_promotion=(
                "Replicate factors and pass bps-year source-backed promotion gates."
            ),
            next_backend_action="review_acosta_factor_series_for_loadings_back_transform_blocker",
        )
    )

    inventory_path = output_dir / "policy_path_protocol_review_inventory.csv"
    with inventory_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=POLICY_PATH_PROTOCOL_REVIEW_INVENTORY_FIELDS
        )
        writer.writeheader()
        writer.writerows(rows)
    return inventory_path, _sha256(inventory_path.read_bytes()), rows


def _csv_rows_from_zip(zip_path: Path, member_name: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as archive:
        text = archive.read(member_name).decode("utf-8-sig", errors="ignore")
    return list(csv.DictReader(text.splitlines()))


def _float_or_none(raw: str) -> float | None:
    if raw == "" or raw.upper() == "NA":
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return value


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.12g}"


def _worksheet_records(xlsx_path: Path, sheet_name: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(xlsx_path) as archive:
        rows = _worksheet_matrix(archive, sheet_name)
    if not rows:
        raise ValueError(f"required USMPD sheet missing or empty: {sheet_name}")
    headers_by_col = {column: value for column, value in rows[0].items() if value}
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        records.append(
            {
                header: row.get(column, "")
                for column, header in headers_by_col.items()
                if header
            }
        )
    return records


def _usmpd_pca_input_rows(
    xlsx_path: Path,
    sheet_name: str,
    variables: list[str],
    *,
    year_min: int | None = None,
) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for record in _worksheet_records(xlsx_path, sheet_name):
        raw_date = record.get("date_time", "") or record.get("Date", "")
        event_date = _excel_serial_date(raw_date) if raw_date else ""
        if not event_date:
            continue
        if year_min is not None and int(event_date[:4]) < year_min:
            continue
        values: dict[str, str | float] = {"Date": event_date}
        missing = False
        for variable in variables:
            parsed = _float_or_none(record.get(variable, ""))
            if parsed is None:
                missing = True
                break
            values[variable] = parsed
        if not missing:
            rows.append(values)
    return rows


def _first_pc_scores(rows: list[dict[str, str | float]], variables: list[str]) -> list[float]:
    import numpy as np

    matrix = np.array(
        [[float(row[variable]) for variable in variables] for row in rows],
        dtype=float,
    )
    means = matrix.mean(axis=0)
    stds = matrix.std(axis=0, ddof=1)
    if np.any(stds == 0):
        raise ValueError("USMPD PCA input contains a zero-variance column")
    standardized = (matrix - means) / stds
    u_matrix, singular_values, _ = np.linalg.svd(standardized, full_matrices=False)
    return list(u_matrix[:, 0] * singular_values[0])


def _load_y1_deltas(zip_path: Path) -> dict[str, float]:
    y1_rows = _csv_rows_from_zip(zip_path, "y1.csv")
    deltas: dict[str, float] = {}
    previous: float | None = None
    for row in y1_rows:
        date_value = row.get("Date", "")
        level = _float_or_none(row.get("SVENY01", ""))
        if date_value and level is not None and previous is not None:
            deltas[date_value] = level - previous
        previous = level
    return deltas


def _ols_slope_with_intercept(x_values: list[float], y_values: list[float]) -> float:
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    if denominator == 0:
        raise ValueError("USMPD replication regression has zero PC1 variance")
    return numerator / denominator


def _replicated_mps_by_date(
    *,
    xlsx_path: Path,
    zip_path: Path,
    sheet_name: str,
    variables: list[str],
    year_min: int | None = None,
) -> tuple[list[dict[str, str | float]], dict[str, float]]:
    rows = _usmpd_pca_input_rows(
        xlsx_path, sheet_name, variables, year_min=year_min
    )
    pc1 = _first_pc_scores(rows, variables)
    y1_deltas = _load_y1_deltas(zip_path)
    regression_x: list[float] = []
    regression_y: list[float] = []
    for row, score in zip(rows, pc1):
        event_date = str(row["Date"])
        if event_date in y1_deltas:
            regression_x.append(score)
            regression_y.append(y1_deltas[event_date])
    slope = _ols_slope_with_intercept(regression_x, regression_y)
    return rows, {str(row["Date"]): slope * score for row, score in zip(rows, pc1)}


def _source_mps_values(
    zip_path: Path, member_name: str, target_column: str
) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in _csv_rows_from_zip(zip_path, member_name):
        parsed = _float_or_none(row.get(target_column, ""))
        if parsed is not None:
            values[row["Date"]] = parsed
    return values


def _write_usmpd_mps_scalar_replication_diagnostic(
    output_dir: Path,
    *,
    source_acquisition_rows: list[dict[str, str]],
) -> tuple[Path, str, list[dict[str, str]]]:
    artifact_by_handle = {
        row["artifact_handle"]: row for row in source_acquisition_rows
    }
    xlsx_artifact = artifact_by_handle["sf_fed_usmpd_xlsx"]
    zip_artifact = artifact_by_handle["sf_fed_usmpd_monetary_policy_surprises_zip"]
    xlsx_path = Path(xlsx_artifact["local_path"])
    zip_path = Path(zip_artifact["local_path"])
    tolerance = 1e-8
    targets = [
        ("STMT", "statement", "Statements", "mps.csv", ["MP1", "MP2", "ED2", "ED3", "ED4"], None),
        ("PC", "press_conference", "Press Conferences", "mps.csv", ["MP1", "MP2", "ED2", "ED3", "ED4"], None),
        ("ME", "monetary_event", "Monetary Events", "mps.csv", ["MP1", "MP2", "ED2", "ED3", "ED4"], None),
        ("MIN", "minutes", "Minutes", "mps_minutes.csv", ["MP2", "ED2", "ED3", "ED4"], 2005),
    ]
    rows: list[dict[str, str]] = []
    for rank, (
        target,
        event_surface,
        sheet_name,
        source_output_file,
        variables,
        year_min,
    ) in enumerate(targets, start=1):
        pca_rows, replicated_values = _replicated_mps_by_date(
            xlsx_path=xlsx_path,
            zip_path=zip_path,
            sheet_name=sheet_name,
            variables=variables,
            year_min=year_min,
        )
        source_values = _source_mps_values(zip_path, source_output_file, target)
        comparable_dates = sorted(set(source_values) & set(replicated_values))
        abs_diffs = [
            abs(source_values[event_date] - replicated_values[event_date])
            for event_date in comparable_dates
        ]
        max_abs_diff = max(abs_diffs) if abs_diffs else None
        mean_abs_diff = (
            sum(abs_diffs) / len(abs_diffs) if abs_diffs else None
        )
        date_values = sorted(source_values)
        replication_passed = (
            bool(comparable_dates)
            and len(source_values) == len(replicated_values)
            and len(source_values) == len(comparable_dates)
            and max_abs_diff is not None
            and max_abs_diff <= tolerance
        )
        rows.append(
            {
                "replication_row_id": (
                    "usmpd_mps_scalar_replication::"
                    f"{rank:02d}_{target.lower()}"
                ),
                "source_handle": "sf_fed_usmpd",
                "artifact_handle": "sf_fed_usmpd_monetary_policy_surprises_zip",
                "source_artifact_path": str(zip_path),
                "source_artifact_sha256": zip_artifact["sha256"],
                "source_output_file": f"{zip_path}::{source_output_file}",
                "replication_target": target,
                "event_surface": event_surface,
                "source_sheet_name": sheet_name,
                "source_variables": ";".join(variables),
                "selected_row_count": str(len(pca_rows)),
                "pca_input_row_count": str(len(pca_rows)),
                "source_output_row_count": str(len(source_values)),
                "replicated_output_row_count": str(len(replicated_values)),
                "comparable_row_count": str(len(comparable_dates)),
                "first_date": date_values[0] if date_values else "",
                "last_date": date_values[-1] if date_values else "",
                "max_abs_diff": _format_float(max_abs_diff),
                "mean_abs_diff": _format_float(mean_abs_diff),
                "tolerance": _format_float(tolerance),
                "replication_status": (
                    "pass_scalar_mps_replication_within_tolerance"
                    if replication_passed
                    else "fail_scalar_mps_replication_mismatch"
                ),
                "unit_conversion_review_status": (
                    "reviewed_source_readme_reports_underlying_rate_changes_"
                    "in_percentage_points"
                ),
                "horizon_mapping_review_status": (
                    "blocked_scalar_mps_output_not_event_date_horizon_grid"
                ),
                "loadings_back_transform_status": (
                    "blocked_no_reviewed_loadings_back_transform"
                ),
                "event_date_horizon_weight_status": (
                    "blocked_no_reviewed_event_date_horizon_weights"
                ),
                "bps_year_integral_status": (
                    "blocked_no_reviewed_bps_year_integral_formula"
                ),
                "source_admission_status": (
                    "blocked_scalar_replication_diagnostic_only"
                ),
                "protocol_admission_status": (
                    "blocked_scalar_replication_not_bps_year_protocol"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "current_protocol_value": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                **_protocol_review_false_fields(),
                "source_status": "usmpd_mps_scalar_replication_diagnostic_fail_closed",
                "exact_blocker": (
                    "USMPD scalar MPS output is a replicated scalar surprise "
                    "diagnostic, not a reviewed event-level bps-year policy "
                    "path; loadings/back-transform and horizon weights remain "
                    "missing."
                ),
                "evidence_needed_before_mapping": (
                    "Reviewed loadings/back-transform, event-date horizon "
                    "weights, and an explicit bps-year integration formula."
                ),
                "evidence_needed_before_promotion": (
                    "A replicated bps-year exposure output plus source-backing "
                    "and promotion gates before any denominator-prior use."
                ),
                "next_backend_action": (
                    "review_usmpd_or_acosta_materials_for_loadings_back_transform_"
                    "and_horizon_weights"
                ),
                "claim_boundary": (
                    "usmpd_mps_scalar_replication_not_bps_year_or_runtime_input"
                ),
            }
        )
    diagnostic_path = output_dir / "usmpd_mps_scalar_replication_diagnostic.csv"
    with diagnostic_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=USMPD_MPS_SCALAR_REPLICATION_FIELDS
        )
        writer.writeheader()
        writer.writerows(rows)
    return diagnostic_path, _sha256(diagnostic_path.read_bytes()), rows


def _workbook_sheet_text(path: Path, sheet_name: str) -> str:
    with zipfile.ZipFile(path) as archive:
        rows = _worksheet_matrix(archive, sheet_name)
    parts: list[str] = []
    for row in rows:
        for _, value in sorted(row.items()):
            if value:
                parts.append(value)
    return " ".join(parts)


def _write_policy_path_bps_year_blocker_decision(
    output_dir: Path,
    *,
    source_acquisition_rows: list[dict[str, str]],
    mps_replication_rows: list[dict[str, str]],
) -> tuple[Path, str, list[dict[str, str]]]:
    artifact_by_handle = {
        row["artifact_handle"]: row for row in source_acquisition_rows
    }
    mps_zip = artifact_by_handle["sf_fed_usmpd_monetary_policy_surprises_zip"]
    usmpd_xlsx = artifact_by_handle["sf_fed_usmpd_xlsx"]
    acosta_xlsx = artifact_by_handle["acosta_abj_2024_monetary_policy_surprises_xlsx"]
    fed_sofr_zip = artifact_by_handle["fed_sofr_continuity_accessible_zip"]
    scalar_statuses = sorted({row["replication_status"] for row in mps_replication_rows})
    scalar_status = ";".join(scalar_statuses)
    acosta_info = _workbook_sheet_text(Path(acosta_xlsx["local_path"]), "Info")
    with zipfile.ZipFile(Path(fed_sofr_zip["local_path"])) as archive:
        sofr_accessible_text = _strip_html(
            archive.read("accessible_figures.html").decode("utf-8", errors="ignore")
        )
    specs = [
        {
            "source_handle": "sf_fed_usmpd",
            "artifact": mps_zip,
            "reviewed_surface": "usmpd_mps_r_scalar_replication",
            "reviewed_source_file_or_sheet": "mps.R;mps.csv;mps_minutes.csv",
            "required_bridge_field": "loadings_back_transform",
            "reviewed_evidence_summary": (
                "mps.R computes first-principal-component scores and writes "
                "Date/MPS scalar outputs; it does not write PCA loadings, "
                "score back-transforms, or horizon-level path components."
            ),
            "reviewed_bridge_evidence_status": (
                "blocked_scalar_code_outputs_mps_only_no_loadings_back_transform"
            ),
        },
        {
            "source_handle": "sf_fed_usmpd",
            "artifact": usmpd_xlsx,
            "reviewed_surface": "usmpd_workbook_event_level_schema",
            "reviewed_source_file_or_sheet": (
                "Statements;Press Conferences;Monetary Events;Minutes"
            ),
            "required_bridge_field": "event_date_horizon_weights",
            "reviewed_evidence_summary": (
                "USMPD workbook sheets expose event-level MP/FF/ED/OIS/UST/TIPS "
                "market-rate columns, but no row-specific contract intervals, "
                "year weights, or bps-year integration grid."
            ),
            "reviewed_bridge_evidence_status": (
                "blocked_workbook_schema_has_instruments_without_horizon_weights"
            ),
        },
        {
            "source_handle": "acosta_sofr_gss_updates",
            "artifact": acosta_xlsx,
            "reviewed_surface": "acosta_gss_ns_updated_factor_workbook",
            "reviewed_source_file_or_sheet": "Info;Data",
            "required_bridge_field": "factor_loadings_and_horizon_back_transform",
            "reviewed_evidence_summary": _text_window(
                acosta_info,
                r"All three series.*?SOFR futures",
                width=700,
            )
            or (
                "Acosta workbook Info sheet describes updated GSS_target, "
                "GSS_path, and NS factor series, not the loadings or "
                "event-date horizon weights needed for bps-year conversion."
            ),
            "reviewed_bridge_evidence_status": (
                "blocked_factor_series_scaled_outputs_no_loadings_or_weights"
            ),
        },
        {
            "source_handle": "fed_sofr_continuity",
            "artifact": fed_sofr_zip,
            "reviewed_surface": "fed_sofr_accessible_figures_and_text",
            "reviewed_source_file_or_sheet": "index.html;accessible_figures.html",
            "required_bridge_field": "sofr_eurodollar_horizon_weight_mapping",
            "reviewed_evidence_summary": _text_window(
                sofr_accessible_text,
                r"second-, third-, and fourth-outstanding Eurodollar futures",
                width=700,
            )
            or (
                "SOFR continuity material describes matching outstanding "
                "Eurodollar/SOFR contracts and series updates, but not a "
                "RateWall bps-year horizon grid."
            ),
            "reviewed_bridge_evidence_status": (
                "blocked_sofr_substitution_context_not_bps_year_weights"
            ),
        },
        {
            "source_handle": "policy_path_bps_year_route",
            "artifact": mps_zip,
            "reviewed_surface": "combined_local_protocol_materials_decision",
            "reviewed_source_file_or_sheet": (
                "USMPD.xlsx;mps.R;mps.csv;mps_minutes.csv;"
                "ABJ-2024-monetary-policy-surprises.xlsx;FEDS SOFR text"
            ),
            "required_bridge_field": "admitted_bps_year_policy_path_protocol",
            "reviewed_evidence_summary": (
                "The local reviewed materials support scalar replication and "
                "SOFR/GSS context, but not an admitted event-level bps-year "
                "policy path. The next backend route is a reviewed "
                "research-parameterization contract if a source supplies "
                "GDP-share demand drag per 100bp-year."
            ),
            "reviewed_bridge_evidence_status": (
                "terminal_blocked_no_reviewed_bps_year_bridge_in_local_sources"
            ),
        },
    ]
    rows: list[dict[str, str]] = []
    for rank, spec in enumerate(specs, start=1):
        artifact = spec["artifact"]
        rows.append(
            {
                "blocker_decision_row_id": (
                    "policy_path_bps_year_blocker_decision::"
                    f"{rank:02d}_{spec['required_bridge_field']}"
                ),
                "source_handle": spec["source_handle"],
                "artifact_handle": artifact["artifact_handle"],
                "source_artifact_path": artifact["local_path"],
                "source_artifact_sha256": artifact["sha256"],
                "reviewed_surface": spec["reviewed_surface"],
                "reviewed_source_file_or_sheet": spec["reviewed_source_file_or_sheet"],
                "required_bridge_field": spec["required_bridge_field"],
                "reviewed_evidence_summary": spec["reviewed_evidence_summary"],
                "reviewed_bridge_evidence_status": spec[
                    "reviewed_bridge_evidence_status"
                ],
                "scalar_replication_status": scalar_status,
                "loadings_back_transform_status": (
                    "blocked_no_reviewed_loadings_back_transform"
                ),
                "event_date_horizon_weight_status": (
                    "blocked_no_reviewed_event_date_horizon_weights"
                ),
                "bps_year_integral_status": (
                    "blocked_no_reviewed_bps_year_integral_formula"
                ),
                "bps_year_route_decision": (
                    "terminal_blocked_scalar_replication_not_bps_year_path"
                ),
                "source_admission_status": "blocked_bps_year_blocker_decision_only",
                "protocol_admission_status": (
                    "blocked_no_reviewed_bps_year_policy_path_bridge"
                ),
                "policy_path_100bp_year_normalization_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "current_protocol_value": "",
                "bps_year_exposure_output": "",
                "candidate_gdp_share_drag_per_100bp_year": "",
                **_protocol_review_false_fields(),
                "source_status": "policy_path_bps_year_blocker_decision_fail_closed",
                "exact_blocker": (
                    "Local USMPD/Acosta/SOFR materials do not provide reviewed "
                    "loadings/back-transform, event-date horizon weights, and "
                    "bps-year integration required for RateWall admission."
                ),
                "evidence_needed_before_mapping": (
                    "A source artifact or construction protocol with path-vector "
                    "loadings/back-transform, event-date weights, unit mapping, "
                    "and bps-year formula."
                ),
                "evidence_needed_before_promotion": (
                    "Replicated bps-year exposure plus source-backing, invariant, "
                    "and promotion gates before any denominator-prior use."
                ),
                "next_backend_action": (
                    "pivot_to_reviewed_research_parameterization_contract_source"
                ),
                "claim_boundary": (
                    "policy_path_bps_year_blocker_decision_not_bps_year_or_runtime_input"
                ),
            }
        )
    decision_path = output_dir / "policy_path_bps_year_blocker_decision.csv"
    with decision_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=POLICY_PATH_BPS_YEAR_BLOCKER_DECISION_FIELDS
        )
        writer.writeheader()
        writer.writerows(rows)
    return decision_path, _sha256(decision_path.read_bytes()), rows


def _candidate_schema_manifest(
    *,
    xlsx_path: Path,
    xlsx_sha: str,
    candidate_vector_path: Path,
    candidate_csv_sha: str,
    candidate_rows: list[dict[str, str]],
) -> dict[str, object]:
    by_sheet: dict[str, list[dict[str, str]]] = {}
    by_instrument: dict[str, list[dict[str, str]]] = {}
    for row in candidate_rows:
        by_sheet.setdefault(row["source_sheet_vintage"], []).append(row)
        by_instrument.setdefault(row["instrument_code"], []).append(row)
    sheet_names = {
        vintage: rows[0]["source_sheet_name"]
        for vintage, rows in by_sheet.items()
        if rows
    }
    instrument_column_letters: dict[str, dict[str, str]] = {}
    for vintage, rows in by_sheet.items():
        instrument_column_letters[vintage] = {
            instrument: "".join(
                char
                for char in next(
                    row["source_workbook_cell"]
                    for row in rows
                    if row["instrument_code"] == instrument
                )
                if char.isalpha()
            )
            for instrument in SF_FED_EVENT_VECTOR_COLUMNS
        }
    return {
        "schema": "ratewall.sf_fed_policy_path_workbook_schema_manifest.v1",
        "parser": "scripts/materialize_policy_path_protocol_sources.py",
        "parser_version": "2026-05-22.event_level_candidate_vector.v2",
        "workbook_path": str(xlsx_path),
        "workbook_sha256": xlsx_sha,
        "sheet_names": sheet_names,
        "candidate_vector_csv_path": str(candidate_vector_path),
        "candidate_vector_csv_sha256": candidate_csv_sha,
        "output_table_hash": candidate_csv_sha,
        "candidate_vector_row_count": len(candidate_rows),
        "required_fomc_sheets_found": sorted(by_sheet),
        "required_fomc_sheet_names_found": [
            sheet_names[vintage] for vintage in sorted(sheet_names)
        ],
        "required_headers": [
            "Date",
            "Time",
            "Unscheduled",
            *SF_FED_EVENT_VECTOR_COLUMNS,
        ],
        "required_headers_found": {
            vintage: [
                "Date",
                "Time",
                "Unscheduled",
                *SF_FED_EVENT_VECTOR_COLUMNS,
            ]
            for vintage in sorted(by_sheet)
        },
        "candidate_instrument_columns": list(SF_FED_EVENT_VECTOR_COLUMNS),
        "candidate_instrument_column_letters": instrument_column_letters,
        "unit_conversion_status": "blocked_no_reviewed_source_unit_conversion",
        "horizon_mapping_status": "blocked_no_reviewed_event_date_specific_horizon_grid",
        "bps_year_integral_status": "blocked_no_reviewed_bps_year_integral_formula",
        "replication_status": "blocked_no_independent_replication",
        "post_2023_sofr_transition_note": (
            "ED1-ED4 are source-labeled workbook columns; 2023 onward rows are "
            "classified as sofr_futures_source_labeled_ed_columns for review "
            "only, without unit conversion or horizon-weight inference."
        ),
        "sheet_summaries": {
            sheet_role: {
                "candidate_row_count": len(rows),
                "event_row_count": len({row["event_sequence"] for row in rows}),
                "first_event_date": min(row["event_date"] for row in rows),
                "last_event_date": max(row["event_date"] for row in rows),
                "numeric_candidate_count": sum(
                    1 for row in rows if row["numeric_value_available"] == "true"
                ),
                "missing_candidate_count": sum(
                    1 for row in rows if row["numeric_value_available"] != "true"
                ),
            }
            for sheet_role, rows in sorted(by_sheet.items())
        },
        "event_row_counts_by_sheet": {
            sheet_names[vintage]: len({row["event_sequence"] for row in rows})
            for vintage, rows in sorted(by_sheet.items())
        },
        "date_bounds_by_sheet": {
            sheet_names[vintage]: {
                "first_event_date": min(row["event_date"] for row in rows),
                "last_event_date": max(row["event_date"] for row in rows),
            }
            for vintage, rows in sorted(by_sheet.items())
        },
        "numeric_counts_by_sheet_instrument": {
            vintage: {
                instrument: sum(
                    1
                    for row in rows
                    if row["instrument_code"] == instrument
                    and row["numeric_value_available"] == "true"
                )
                for instrument in SF_FED_EVENT_VECTOR_COLUMNS
            }
            for vintage, rows in sorted(by_sheet.items())
        },
        "missing_counts_by_sheet_instrument": {
            vintage: {
                instrument: sum(
                    1
                    for row in rows
                    if row["instrument_code"] == instrument
                    and row["numeric_value_available"] != "true"
                )
                for instrument in SF_FED_EVENT_VECTOR_COLUMNS
            }
            for vintage, rows in sorted(by_sheet.items())
        },
        "instrument_summaries": {
            instrument: {
                "candidate_row_count": len(rows),
                "numeric_candidate_count": sum(
                    1 for row in rows if row["numeric_value_available"] == "true"
                ),
                "missing_candidate_count": sum(
                    1 for row in rows if row["numeric_value_available"] != "true"
                ),
            }
            for instrument, rows in sorted(by_instrument.items())
        },
        "claim_boundary": (
            "sf_fed_workbook_schema_manifest_not_bps_year_or_runtime_input"
        ),
    }


def materialize(output_dir: Path) -> Path:
    retrieved_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    page_path = output_dir / "sf_fed_monetary_policy_surprises_page.html"
    csv_path = output_dir / "sf_fed_monetary_policy_surprises_chart.csv"
    xlsx_path = output_dir / "sf_fed_monetary_policy_surprises_data.xlsx"
    candidate_vector_path = (
        output_dir / "sf_fed_monetary_policy_surprises_candidate_event_vector.csv"
    )
    description_sheet_path = (
        output_dir / "sf_fed_monetary_policy_surprises_description_sheet.csv"
    )
    workbook_schema_manifest_path = (
        output_dir / "sf_fed_monetary_policy_surprises_workbook_schema_manifest.json"
    )
    source_acquisition_manifest_path = (
        output_dir / "policy_path_protocol_source_acquisition_manifest.json"
    )
    manifest_path = (
        output_dir / "sf_fed_monetary_policy_surprises_protocol_context_manifest.json"
    )

    page_payload = _fetch(SF_FED_LANDING_URL)
    csv_payload = _fetch(SF_FED_CHART_CSV_URL)
    xlsx_payload = _fetch(SF_FED_DATA_XLSX_URL)

    page_sha = _write_bytes(page_path, page_payload)
    csv_sha = _write_bytes(csv_path, csv_payload)
    xlsx_sha = _write_bytes(xlsx_path, xlsx_payload)
    page_text = page_payload.decode("utf-8", errors="ignore")
    csv_text = csv_payload.decode("utf-8-sig", errors="ignore")
    candidate_rows = _candidate_vector_rows(xlsx_path, xlsx_sha=xlsx_sha)
    candidate_csv_sha = _write_candidate_vector_csv(candidate_vector_path, candidate_rows)
    description_sheet_sha, description_sheet_row_count = _write_description_sheet_csv(
        description_sheet_path, xlsx_path
    )
    workbook_schema_manifest = _candidate_schema_manifest(
        xlsx_path=xlsx_path,
        xlsx_sha=xlsx_sha,
        candidate_vector_path=candidate_vector_path,
        candidate_csv_sha=candidate_csv_sha,
        candidate_rows=candidate_rows,
    )
    workbook_schema_manifest["description_sheet_csv_path"] = str(description_sheet_path)
    workbook_schema_manifest["description_sheet_csv_sha256"] = description_sheet_sha
    workbook_schema_manifest["description_sheet_row_count"] = description_sheet_row_count
    workbook_schema_manifest_path.write_text(
        json.dumps(workbook_schema_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    workbook_schema_manifest_sha = _sha256(workbook_schema_manifest_path.read_bytes())
    (
        source_acquisition_registry_path,
        source_acquisition_registry_sha,
        source_acquisition_rows,
    ) = _write_source_acquisition_registry(output_dir, retrieved_at=retrieved_at)
    (
        protocol_review_inventory_path,
        protocol_review_inventory_sha,
        protocol_review_inventory_rows,
    ) = _write_protocol_review_inventory(
        output_dir, source_acquisition_rows=source_acquisition_rows
    )
    (
        mps_replication_diagnostic_path,
        mps_replication_diagnostic_sha,
        mps_replication_diagnostic_rows,
    ) = _write_usmpd_mps_scalar_replication_diagnostic(
        output_dir, source_acquisition_rows=source_acquisition_rows
    )
    (
        bps_year_blocker_decision_path,
        bps_year_blocker_decision_sha,
        bps_year_blocker_decision_rows,
    ) = _write_policy_path_bps_year_blocker_decision(
        output_dir,
        source_acquisition_rows=source_acquisition_rows,
        mps_replication_rows=mps_replication_diagnostic_rows,
    )
    source_acquisition_manifest = {
        "schema": "ratewall.policy_path_protocol_source_acquisition_manifest.v1",
        "parser": "scripts/materialize_policy_path_protocol_sources.py",
        "parser_version": "2026-05-22.usmpd_mps_scalar_replication.v1",
        "retrieved_at_utc": retrieved_at,
        "source_acquisition_registry_path": str(source_acquisition_registry_path),
        "source_acquisition_registry_sha256": source_acquisition_registry_sha,
        "source_artifact_count": len(source_acquisition_rows),
        "protocol_review_inventory_path": str(protocol_review_inventory_path),
        "protocol_review_inventory_sha256": protocol_review_inventory_sha,
        "protocol_review_inventory_row_count": len(protocol_review_inventory_rows),
        "mps_scalar_replication_diagnostic_path": str(
            mps_replication_diagnostic_path
        ),
        "mps_scalar_replication_diagnostic_sha256": mps_replication_diagnostic_sha,
        "mps_scalar_replication_diagnostic_row_count": len(
            mps_replication_diagnostic_rows
        ),
        "mps_scalar_replication_statuses": sorted(
            {
                row["replication_status"]
                for row in mps_replication_diagnostic_rows
            }
        ),
        "bps_year_blocker_decision_path": str(bps_year_blocker_decision_path),
        "bps_year_blocker_decision_sha256": bps_year_blocker_decision_sha,
        "bps_year_blocker_decision_row_count": len(bps_year_blocker_decision_rows),
        "bps_year_route_decisions": sorted(
            {row["bps_year_route_decision"] for row in bps_year_blocker_decision_rows}
        ),
        "source_handles": sorted(
            {row["source_handle"] for row in source_acquisition_rows}
        ),
        "artifact_handles": [row["artifact_handle"] for row in source_acquisition_rows],
        "unit_conversion_status": "blocked_no_reviewed_source_unit_conversion",
        "horizon_mapping_status": "blocked_no_reviewed_event_date_specific_horizon_grid",
        "bps_year_integral_status": "blocked_no_reviewed_bps_year_integral_formula",
        "replication_status": "blocked_no_independent_replication",
        "source_admission_status": "blocked_raw_protocol_source_artifact_review_only",
        "protocol_admission_status": (
            "blocked_acquired_artifact_missing_unit_horizon_integral_replication"
        ),
        "claim_boundary": (
            "policy_path_protocol_source_acquisition_manifest_not_bps_year_or_runtime_input"
        ),
    }
    source_acquisition_manifest_path.write_text(
        json.dumps(source_acquisition_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    source_acquisition_manifest_sha = _sha256(
        source_acquisition_manifest_path.read_bytes()
    )
    numeric_candidate_count = sum(
        1 for row in candidate_rows if row["numeric_value_available"] == "true"
    )

    manifest = {
        "source_context_id": (
            "sf_fed_monetary_policy_surprises_policy_path_protocol_context"
        ),
        "applicable_shock_source_id": "sf_fed_monetary_policy_surprises",
        "registry_series_id": "gurkaynak_sack_swanson_2005",
        "source_handle": "sf_fed_monetary_policy_surprises",
        "publisher": "Federal Reserve Bank of San Francisco",
        "source_landing_page_url": SF_FED_LANDING_URL,
        "source_chart_csv_url": SF_FED_CHART_CSV_URL,
        "source_data_xlsx_url": SF_FED_DATA_XLSX_URL,
        "local_landing_page_path": str(page_path),
        "local_chart_csv_path": str(csv_path),
        "local_data_xlsx_path": str(xlsx_path),
        "local_candidate_event_vector_csv_path": str(candidate_vector_path),
        "local_description_sheet_csv_path": str(description_sheet_path),
        "local_workbook_schema_manifest_path": str(workbook_schema_manifest_path),
        "local_protocol_source_acquisition_registry_path": str(
            source_acquisition_registry_path
        ),
        "local_protocol_source_acquisition_manifest_path": str(
            source_acquisition_manifest_path
        ),
        "local_protocol_review_inventory_path": str(protocol_review_inventory_path),
        "local_mps_scalar_replication_diagnostic_path": str(
            mps_replication_diagnostic_path
        ),
        "local_bps_year_blocker_decision_path": str(
            bps_year_blocker_decision_path
        ),
        "local_manifest_path": str(manifest_path),
        "landing_page_sha256": page_sha,
        "chart_csv_sha256": csv_sha,
        "data_xlsx_sha256": xlsx_sha,
        "candidate_event_vector_csv_sha256": candidate_csv_sha,
        "description_sheet_csv_sha256": description_sheet_sha,
        "description_sheet_row_count": str(description_sheet_row_count),
        "workbook_schema_manifest_sha256": workbook_schema_manifest_sha,
        "protocol_source_acquisition_registry_sha256": (
            source_acquisition_registry_sha
        ),
        "protocol_source_acquisition_manifest_sha256": (
            source_acquisition_manifest_sha
        ),
        "protocol_review_inventory_sha256": protocol_review_inventory_sha,
        "protocol_review_inventory_row_count": str(len(protocol_review_inventory_rows)),
        "mps_scalar_replication_diagnostic_sha256": mps_replication_diagnostic_sha,
        "mps_scalar_replication_diagnostic_row_count": str(
            len(mps_replication_diagnostic_rows)
        ),
        "mps_scalar_replication_statuses": ";".join(
            sorted(
                {
                    row["replication_status"]
                    for row in mps_replication_diagnostic_rows
                }
            )
        ),
        "bps_year_blocker_decision_sha256": bps_year_blocker_decision_sha,
        "bps_year_blocker_decision_row_count": str(
            len(bps_year_blocker_decision_rows)
        ),
        "bps_year_route_decisions": ";".join(
            sorted(
                {
                    row["bps_year_route_decision"]
                    for row in bps_year_blocker_decision_rows
                }
            )
        ),
        "protocol_source_acquisition_artifact_count": str(len(source_acquisition_rows)),
        "protocol_source_acquisition_handles": ";".join(
            sorted({row["source_handle"] for row in source_acquisition_rows})
        ),
        "source_updated_date": _updated_date(page_text),
        "retrieved_at_utc": retrieved_at,
        "chart_csv_record_count": str(_csv_record_count(csv_text)),
        "candidate_event_vector_row_count": str(len(candidate_rows)),
        "candidate_event_vector_numeric_count": str(numeric_candidate_count),
        "candidate_event_vector_sheet_roles": (
            "updated_fomc_event_workbook_sheet;original_fomc_event_workbook_sheet"
        ),
        "candidate_event_vector_instrument_columns": ";".join(
            SF_FED_EVENT_VECTOR_COLUMNS
        ),
        "event_window_context": (
            "30-minute changes around FOMC announcements"
            if "30-minute changes" in page_text
            else ""
        ),
        "horizon_context": (
            "futures contracts covering the next four quarters"
            if "next four quarters" in page_text
            else ""
        ),
        "factor_context": (
            "weighted average first principal component of futures-rate changes"
            if "first principal component" in page_text
            else ""
        ),
        "orthogonalization_context": (
            "orthogonalized surprises are regression residuals"
            if "residuals from a regression" in page_text
            else ""
        ),
        "event_level_vector_status": (
            "candidate_event_level_futures_columns_extracted_fail_closed"
            if candidate_rows
            else "blocked_downloaded_artifacts_do_not_expose_event_level_"
            "futures_columns"
        ),
        "bps_year_integral_status": (
            "blocked_candidate_vector_lacks_reviewed_horizon_mapping_and_bps_"
            "year_integral"
        ),
        "replication_status": (
            "blocked_no_independent_bps_year_replication_artifact"
        ),
        "source_admission_status": (
            "candidate_event_level_vector_extracted_not_bps_year_protocol"
            if candidate_rows
            else "partial_reviewed_policy_path_context_only_not_bps_year_protocol"
        ),
        "claim_boundary": (
            "policy_path_reviewed_source_context_not_prior_narrowing_or_raw_rate_shock"
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="data/raw/policy_path_protocol_sources",
        type=Path,
    )
    args = parser.parse_args()
    print(materialize(args.output_dir))


if __name__ == "__main__":
    main()
