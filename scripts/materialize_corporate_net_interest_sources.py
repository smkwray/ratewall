"""Materialize corporate net-interest source snapshots into RateWall raw bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from typing import Sequence
from zipfile import ZipFile

from ratewall.data.snapshots import read_snapshot_bundle, write_snapshot_bundle
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot, utc_now_iso
from ratewall.sources.fred import FredAdapter
from ratewall.sources.registry import SourceRegistry


QFR_SOURCE_ID = "census_qfr_interest_expense"
QFR_SOURCE_URL = "https://www2.census.gov/econ/qfr/xls/qfr25q4f.xlsx"
QFR_RELEASE_QUARTER = "2025Q4"
QFR_RELEASE_DATE = "2026-03-23"
QFR_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

CORPORATE_NET_INTEREST_SERIES = (
    "BOGZ1FU106130001Q",
    "BOGZ1FU106130101Q",
    "NCBCDCA",
    "TSDABSNNCB",
    "TSABSNNCB",
    "BOGZ1FL103034000Q",
    "SRPSABSNNCB",
    "CBLBSNNCB",
    "NCBDBIQ027S",
    "NCBLL",
    "CPLBSNNCB",
)

QFR_FIELD_ROLES = {
    "interest_expense": ("interest expense",),
    "mixed_nonoperating_income_context": (
        "other recurring nonoperating income",
        "all other nonoperating income",
    ),
    "cash_demand_deposits": ("cash and demand deposits in the u s",),
    "time_deposits": ("time deposits in the u s",),
    "short_term_financial_investments": (
        "other short-term financial investments",
    ),
    "total_cash_us_government_other_securities": (
        "total cash, u s government and other securities",
    ),
    "short_term_debt_original_maturity": (
        "short-term debt, original maturity of 1 year or less",
    ),
    "current_long_term_debt_due_within_one_year": (
        "current portion of long-term debt, due in 1 year or less",
    ),
    "long_term_debt_due_more_than_one_year": (
        "long-term debt, due in more than 1 year",
    ),
    "short_term_debt_ratio": (
        "short-term debt, including current portion of long-term debt",
    ),
    "long_term_debt_ratio": ("long-term debt",),
}


def _records_sha256(records: Sequence[object]) -> str:
    payload = json.dumps(
        list(records),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _date_range(snapshot: SourceSnapshot) -> tuple[str, str]:
    dates = sorted(
        str(record.get("date", ""))
        for record in snapshot.records
        if record.get("date")
    )
    if not dates:
        return "", ""
    return dates[0], dates[-1]


def _download_qfr_workbook(*, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        QFR_SOURCE_URL,
        headers={"User-Agent": "ratewall-source-admission/23.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response, output.open(
        "wb"
    ) as handle:
        shutil.copyfileobj(response, handle)
    return output


def _annotated_snapshot(snapshot: SourceSnapshot) -> SourceSnapshot:
    first_date, latest_date = _date_range(snapshot)
    records_hash = _records_sha256(snapshot.records)
    spec = (
        "corporate_net_interest_cashflow_context_only"
        if snapshot.metadata.series_id.startswith("BOGZ1FU106130")
        else "corporate_balance_sheet_stock_context_only"
    )
    note = (
        f"{spec};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(snapshot.records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false"
    )
    return SourceSnapshot(
        metadata=replace(snapshot.metadata, note=note),
        records=snapshot.records,
    )


def _shared_strings(zip_file: ZipFile) -> list[str]:
    root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("main:si", QFR_NS):
        strings.append(
            "".join(
                text.text or ""
                for text in item.iter(
                    "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                )
            )
        )
    return strings


def _sheet_targets(zip_file: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
    rels = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    targets: dict[str, str] = {}
    for sheet in workbook.find("main:sheets", QFR_NS) or []:
        rel_id = sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        targets[sheet.attrib["name"]] = relmap[rel_id]
    return targets


def _cell_column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + ord(char.upper()) - 64
    return index


def _cell_row_index(cell_ref: str) -> int:
    return int("".join(char for char in cell_ref if char.isdigit()))


def _normalize_label(value: object) -> str:
    text = str(value or "").lower()
    text = text.replace("\n", " ")
    text = re.sub(r"[.…]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _field_role(label: str) -> str | None:
    normalized = _normalize_label(label)
    if not normalized:
        return None
    for role, needles in QFR_FIELD_ROLES.items():
        if any(needle in normalized for needle in needles):
            if role == "long_term_debt_ratio" and "due in more than" in normalized:
                return "long_term_debt_due_more_than_one_year"
            return role
    return None


def _worksheet_rows(
    *, zip_file: ZipFile, target: str, shared_strings: list[str]
) -> dict[int, dict[int, object]]:
    root = ET.fromstring(zip_file.read(f"xl/{target}"))
    rows: dict[int, dict[int, object]] = {}
    for cell in root.findall(".//main:c", QFR_NS):
        ref = cell.attrib.get("r", "")
        value_node = cell.find("main:v", QFR_NS)
        if value_node is None or not ref:
            continue
        value: object = value_node.text or ""
        if cell.attrib.get("t") == "s":
            value = shared_strings[int(str(value))]
        row = _cell_row_index(ref)
        col = _cell_column_index(ref)
        rows.setdefault(row, {})[col] = value
    return rows


def _filled_header(rows: dict[int, dict[int, object]], *, row: int, col: int) -> str:
    for candidate_col in range(col, 0, -1):
        value = rows.get(row, {}).get(candidate_col, "")
        if str(value).strip():
            return str(value)
    return ""


def _records_from_qfr_workbook(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with ZipFile(path) as zip_file:
        strings = _shared_strings(zip_file)
        targets = _sheet_targets(zip_file)
        for sheet_name, target in targets.items():
            if not re.match(r"T\d+_[01]-", sheet_name):
                continue
            rows = _worksheet_rows(
                zip_file=zip_file,
                target=target,
                shared_strings=strings,
            )
            table_title = str(rows.get(2, {}).get(1, "")).replace("\n", " ")
            statement_type = (
                "income_statement" if "_0-" in sheet_name else "balance_sheet"
            )
            active_debt_section: str | None = None
            for row_number, row in sorted(rows.items()):
                row_label = str(row.get(1, ""))
                role = _field_role(row_label)
                if role in {
                    "short_term_debt_original_maturity",
                    "current_long_term_debt_due_within_one_year",
                    "long_term_debt_due_more_than_one_year",
                }:
                    active_debt_section = role
                elif _normalize_label(row_label).startswith(("a ", "b ")):
                    role = active_debt_section
                elif role not in {
                    "short_term_debt_ratio",
                    "long_term_debt_ratio",
                }:
                    active_debt_section = None
                if role is None:
                    continue
                for col, value in sorted(row.items()):
                    if col == 1 or value in {"", None}:
                        continue
                    period = str(rows.get(5, {}).get(col, "")).replace("\n", " ")
                    if not period.strip():
                        continue
                    records.append(
                        {
                            "sheet_name": sheet_name,
                            "table_title": table_title,
                            "statement_type": statement_type,
                            "row_number": str(row_number),
                            "column_number": str(col),
                            "field_role": role,
                            "row_label": _normalize_label(row_label),
                            "column_group": _filled_header(
                                rows, row=4, col=col
                            ).replace("\n", " "),
                            "period": period,
                            "unit": _filled_header(rows, row=6, col=col).replace(
                                "\n", " "
                            ),
                            "value": str(value),
                            "source_release_quarter": QFR_RELEASE_QUARTER,
                        }
                    )
    return records


def _qfr_snapshot(*, workbook: Path) -> SourceSnapshot:
    records = _records_from_qfr_workbook(workbook)
    workbook_hash = _file_sha256(workbook)
    records_hash = _records_sha256(records)
    field_roles = sorted({record["field_role"] for record in records})
    note = (
        f"source_workbook_sha256={workbook_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"source_release_quarter={QFR_RELEASE_QUARTER};"
        f"field_roles={','.join(field_roles)};"
        "units=million_dollars_or_percent_as_published;"
        "source_use=aggregate_qfr_cash_debt_maturity_context_only;"
        "fixed_floating_direct_evidence=false;"
        "firm_level_overlap_evidence=false;"
        "prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id="census_qfr",
            series_id=QFR_SOURCE_ID,
            source_url=QFR_SOURCE_URL,
            units="million_dollars_or_percent_as_published",
            frequency="quarterly",
            transform="aggregate_cash_debt_maturity_context",
            retrieved_at=utc_now_iso(),
            source_release_at=QFR_RELEASE_DATE,
            snapshot_kind="live",
            note=note,
        ),
        records=records,
    )


def materialize(
    *,
    config: Path,
    snapshot_bundle: Path,
    output: Path,
    qfr_workbook_output: Path,
    skip_qfr: bool = False,
) -> Path:
    registry = SourceRegistry.from_path(config)
    adapter = FredAdapter(registry)
    existing = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in existing}
    for series_id in CORPORATE_NET_INTEREST_SERIES:
        by_series[series_id] = _annotated_snapshot(adapter.pull_series(series_id))
    if not skip_qfr:
        qfr_workbook = _download_qfr_workbook(output=qfr_workbook_output)
        by_series[QFR_SOURCE_ID] = _qfr_snapshot(workbook=qfr_workbook)
    ordered = [by_series[series_id] for series_id in sorted(by_series)]
    return write_snapshot_bundle(ordered, output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/sources.yml"))
    parser.add_argument(
        "--snapshot-bundle",
        type=Path,
        default=Path("data/raw/ratewall_snapshot.json"),
    )
    parser.add_argument("--output", type=Path, default=Path("data/raw/ratewall_snapshot.json"))
    parser.add_argument(
        "--qfr-workbook-output",
        type=Path,
        default=Path("data/raw/qfr/qfr25q4f.xlsx"),
    )
    parser.add_argument("--skip-qfr", action="store_true")
    args = parser.parse_args()
    output = materialize(
        config=args.config,
        snapshot_bundle=args.snapshot_bundle,
        output=args.output,
        qfr_workbook_output=args.qfr_workbook_output,
        skip_qfr=args.skip_qfr,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
