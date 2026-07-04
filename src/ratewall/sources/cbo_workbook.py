"""Parse official CBO XLSX workbooks into normalized projection rows."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile
import re
import xml.etree.ElementTree as ET


XML_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XML_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


BILLION_METRICS = {
    "net interest": ("net_interest_bil", "billions_of_dollars"),
    "total deficit (-)": ("deficit_bil", "billions_of_dollars"),
    "debt held by the public": ("debt_held_public_bil", "billions_of_dollars"),
    "gdp": ("gdp_bil", "billions_of_dollars"),
}

GDP_PERCENT_METRICS = {
    "net interest": ("net_interest_gdp_pct", "percent_of_gdp"),
    "total deficit (-)": ("deficit_gdp_pct", "percent_of_gdp"),
    "debt held by the public": ("debt_held_public_gdp_pct", "percent_of_gdp"),
}

INTEREST_RATE_LABEL = "average interest rate on debt held by the public (percent)"


def parse_cbo_budget_projection_rows(path: Path) -> list[dict[str, str]]:
    """Return long-form projection rows from CBO's budget projections workbook."""

    workbook = _read_workbook(path)
    records: list[dict[str, str]] = []
    records.extend(_parse_table_1_1(workbook.get("Table 1-1", []), path.name))
    records.extend(_parse_table_1_3(workbook.get("Table 1-3", []), path.name))
    return records


def _parse_table_1_1(rows: list[list[str]], source_file: str) -> list[dict[str, str]]:
    year_cols = _year_columns(rows)
    records: list[dict[str, str]] = []
    section = ""

    for row in rows:
        label = _clean(row[0] if row else "")
        joined = _clean(" ".join(row))
        if "In billions of dollars" in joined:
            section = "billions_of_dollars"
            continue
        if "As a percentage of GDP" in joined:
            section = "percent_of_gdp"
            continue

        normalized_label = _label_key(label)
        if section == "billions_of_dollars" and normalized_label in BILLION_METRICS:
            metric, units = BILLION_METRICS[normalized_label]
        elif section == "percent_of_gdp" and normalized_label in GDP_PERCENT_METRICS:
            metric, units = GDP_PERCENT_METRICS[normalized_label]
        else:
            continue

        records.extend(
            _projection_records(
                row=row,
                year_cols=year_cols,
                source_file=source_file,
                source_table="Table 1-1",
                source_row_label=label,
                metric=metric,
                units=units,
            )
        )
    return records


def _parse_table_1_3(rows: list[list[str]], source_file: str) -> list[dict[str, str]]:
    year_cols = _year_columns(rows)
    records: list[dict[str, str]] = []

    for row in rows:
        label = _clean(row[0] if row else "")
        if _label_key(label) != INTEREST_RATE_LABEL:
            continue
        records.extend(
            _projection_records(
                row=row,
                year_cols=year_cols,
                source_file=source_file,
                source_table="Table 1-3",
                source_row_label=label,
                metric="average_interest_rate_debt_public_pct",
                units="percent",
            )
        )
    return records


def _projection_records(
    *,
    row: list[str],
    year_cols: dict[int, str],
    source_file: str,
    source_table: str,
    source_row_label: str,
    metric: str,
    units: str,
) -> Iterable[dict[str, str]]:
    for col_idx, fiscal_year in sorted(year_cols.items()):
        value = _clean(row[col_idx] if col_idx < len(row) else "")
        if not value:
            continue
        yield {
            "record_type": "cbo_projection",
            "release_date": "2026-02",
            "source_file": source_file,
            "source_table": source_table,
            "source_row_label": source_row_label,
            "metric": metric,
            "fiscal_year": fiscal_year,
            "value": _normalize_numeric(value),
            "units": units,
        }


def _read_workbook(path: Path) -> dict[str, list[list[str]]]:
    with ZipFile(path) as workbook_zip:
        shared_strings = _shared_strings(workbook_zip)
        sheet_paths = _sheet_paths(workbook_zip)
        return {
            sheet_name: _sheet_rows(workbook_zip, sheet_path, shared_strings)
            for sheet_name, sheet_path in sheet_paths.items()
        }


def _shared_strings(workbook_zip: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook_zip.namelist():
        return []
    root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall(f"{{{XML_MAIN_NS}}}si"):
        parts = [node.text or "" for node in item.iter(f"{{{XML_MAIN_NS}}}t")]
        strings.append(_clean("".join(parts)))
    return strings


def _sheet_paths(workbook_zip: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
    rels = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
    }

    paths: dict[str, str] = {}
    for sheet in workbook.findall(f".//{{{XML_MAIN_NS}}}sheet"):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib[f"{{{XML_REL_NS}}}id"]
        target = rel_targets[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        paths[name] = target
    return paths


def _sheet_rows(
    workbook_zip: ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> list[list[str]]:
    root = ET.fromstring(workbook_zip.read(sheet_path))
    rows: list[list[str]] = []
    for row_node in root.findall(f".//{{{XML_MAIN_NS}}}row"):
        values: dict[int, str] = {}
        max_col = -1
        for cell in row_node.findall(f"{{{XML_MAIN_NS}}}c"):
            col_idx = _cell_col_index(cell.attrib.get("r", ""))
            if col_idx < 0:
                continue
            values[col_idx] = _cell_value(cell, shared_strings)
            max_col = max(max_col, col_idx)
        rows.append([values.get(idx, "") for idx in range(max_col + 1)])
    return rows


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        parts = [node.text or "" for node in cell.iter(f"{{{XML_MAIN_NS}}}t")]
        return _clean("".join(parts))

    value_node = cell.find(f"{{{XML_MAIN_NS}}}v")
    if value_node is None or value_node.text is None:
        return ""
    raw_value = value_node.text.strip()
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (IndexError, ValueError):
            return raw_value
    return _clean(raw_value)


def _year_columns(rows: list[list[str]]) -> dict[int, str]:
    for row in rows:
        years = {
            col_idx: _clean(value)
            for col_idx, value in enumerate(row)
            if re.fullmatch(r"20[0-9]{2}", _clean(value))
        }
        if "2026" in years.values() and "2036" in years.values():
            return years
    return {}


def _cell_col_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return -1
    col_idx = 0
    for char in match.group(1):
        col_idx = col_idx * 26 + (ord(char) - ord("A") + 1)
    return col_idx - 1


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def _label_key(value: str) -> str:
    return _clean(value).lower()


def _normalize_numeric(value: str) -> str:
    raw = value.replace(",", "")
    try:
        decimal = Decimal(raw)
    except InvalidOperation:
        return raw
    rounded = decimal.quantize(Decimal("0.000001")).normalize()
    return format(rounded, "f")
