"""Materialize official D1 deposit payer-flow source panels."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests

from ratewall.databook.deposit_payer_flow_source_panel import (
    DEFAULT_RAW_DIR,
    FFIEC_PANEL_RELATIVE_PATH,
    NCUA_PANEL_RELATIVE_PATH,
)
from ratewall.databook.table_io import write_rows

FFIEC_BULK_DOWNLOAD_URL = "https://cdr.ffiec.gov/public/pws/downloadbulkdata.aspx"
FFIEC_PRODUCT_SINGLE_PERIOD = "ReportingSeriesSinglePeriod"
FFIEC_TAB_DELIMITED = "TSVRadioButton"
NCUA_QUARTERLY_BASE_URL = (
    "https://www.ncua.gov/files/publications/analysis/call-report-data-{yyyy}-{mm}.zip"
)

FFIEC_OUTPUT_FIELDS = [
    "report_date",
    "rssd_id",
    "institution_name",
    "RIAD4508",
    "RIAD0093",
    "RIADHK03",
    "RIADHK04",
    "RIAD4172",
    "source_url",
    "source_archive",
]
NCUA_OUTPUT_FIELDS = [
    "report_date",
    "charter_number",
    "credit_union_name",
    "380",
    "381",
    "340",
    "350",
    "source_url",
    "source_archive",
]

_FFIEC_DATE_TOKEN = re.compile(r"(\d{8})")


@dataclass(frozen=True)
class MaterializedDepositPayerFlowSources:
    """Paths written by the D1 source materializer."""

    ffiec_archive: Path
    ncua_archive: Path
    ffiec_panel: Path
    ncua_panel: Path


class _BulkDownloadPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden_inputs: dict[str, str] = {}
        self.select_options: dict[str, list[tuple[str, str]]] = {}
        self._active_select: str | None = None
        self._active_option_value: str | None = None
        self._option_text_parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attr_map = dict(attrs)
        if tag == "input" and attr_map.get("type") == "hidden" and attr_map.get(
            "name"
        ):
            self.hidden_inputs[str(attr_map["name"])] = str(
                attr_map.get("value") or ""
            )
            return
        if tag == "select" and attr_map.get("id"):
            self._active_select = str(attr_map["id"])
            self.select_options.setdefault(self._active_select, [])
            return
        if tag == "option" and self._active_select is not None:
            self._active_option_value = str(attr_map.get("value") or "")
            self._option_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._active_option_value is not None:
            self._option_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if (
            tag == "option"
            and self._active_select is not None
            and self._active_option_value is not None
        ):
            text = "".join(self._option_text_parts).strip()
            self.select_options.setdefault(self._active_select, []).append(
                (text, self._active_option_value)
            )
            self._active_option_value = None
            self._option_text_parts = []
            return
        if tag == "select":
            self._active_select = None


def materialize_deposit_payer_flow_sources(
    *,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    report_date: str = "03/31/2026",
    ffiec_archive: str | Path | None = None,
    ncua_archive: str | Path | None = None,
) -> MaterializedDepositPayerFlowSources:
    """Acquire and materialize official FFIEC and NCUA D1 panels."""

    raw = Path(raw_dir)
    parsed_report_date = _parse_report_date(report_date)
    archive_date = parsed_report_date.strftime("%m%d%Y")
    ncua_month = parsed_report_date.strftime("%m")
    ncua_year = parsed_report_date.strftime("%Y")

    ffiec_zip = Path(ffiec_archive) if ffiec_archive else raw / (
        "ffiec_fdic/official/"
        f"FFIEC-CDR-Call-Bulk-All-Schedules-{archive_date}.zip"
    )
    ncua_zip = Path(ncua_archive) if ncua_archive else raw / (
        "ncua/official/" f"call-report-data-{ncua_year}-{ncua_month}.zip"
    )
    if ffiec_archive is None:
        download_ffiec_call_report_bulk_zip(report_date, ffiec_zip)
    if ncua_archive is None:
        download_ncua_call_report_zip(ncua_year, ncua_month, ncua_zip)

    ffiec_panel = raw / FFIEC_PANEL_RELATIVE_PATH
    ncua_panel = raw / NCUA_PANEL_RELATIVE_PATH
    materialize_ffiec_deposit_interest_panel(
        ffiec_zip,
        ffiec_panel,
        source_url=FFIEC_BULK_DOWNLOAD_URL,
    )
    materialize_ncua_share_interest_panel(
        ncua_zip,
        ncua_panel,
        source_url=NCUA_QUARTERLY_BASE_URL.format(yyyy=ncua_year, mm=ncua_month),
    )
    return MaterializedDepositPayerFlowSources(
        ffiec_archive=ffiec_zip,
        ncua_archive=ncua_zip,
        ffiec_panel=ffiec_panel,
        ncua_panel=ncua_panel,
    )


def download_ffiec_call_report_bulk_zip(
    report_date: str,
    output_path: str | Path,
    *,
    timeout: int = 120,
) -> Path:
    """Download one FFIEC CDR Call Report single-period TSV ZIP."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
    )
    landing = session.get(FFIEC_BULK_DOWNLOAD_URL, timeout=timeout)
    landing.raise_for_status()
    landing_page = _parse_bulk_page(landing.text)
    selection_payload = dict(landing_page.hidden_inputs)
    selection_payload.update(
        {
            "__EVENTTARGET": "ctl00$MainContentHolder$ListBox1",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            "ctl00$MainContentHolder$ListBox1": FFIEC_PRODUCT_SINGLE_PERIOD,
        }
    )
    selection = session.post(
        FFIEC_BULK_DOWNLOAD_URL,
        data=selection_payload,
        timeout=timeout,
    )
    selection.raise_for_status()
    selection_page = _parse_bulk_page(selection.text)
    report_date_value = _date_option_value(selection_page, report_date)

    download_payload = dict(selection_page.hidden_inputs)
    download_payload.update(
        {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            "ctl00$MainContentHolder$ListBox1": FFIEC_PRODUCT_SINGLE_PERIOD,
            "ctl00$MainContentHolder$DatesDropDownList": report_date_value,
            "ctl00$MainContentHolder$FormatType": FFIEC_TAB_DELIMITED,
            FFIEC_TAB_DELIMITED: FFIEC_TAB_DELIMITED,
            "ctl00$MainContentHolder$TabStrip1$Download_0": "Download",
        }
    )
    response = session.post(
        FFIEC_BULK_DOWNLOAD_URL,
        data=download_payload,
        timeout=timeout,
    )
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise ValueError("FFIEC bulk response was not a ZIP archive.")
    destination.write_bytes(response.content)
    return destination


def download_ncua_call_report_zip(
    year: str,
    month: str,
    output_path: str | Path,
    *,
    timeout: int = 120,
) -> Path:
    """Download one NCUA quarterly Call Report ZIP."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = NCUA_QUARTERLY_BASE_URL.format(yyyy=year, mm=month)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise ValueError("NCUA quarterly response was not a ZIP archive.")
    destination.write_bytes(response.content)
    return destination


def materialize_ffiec_deposit_interest_panel(
    zip_path: str | Path,
    output_path: str | Path,
    *,
    source_url: str,
) -> Path:
    """Extract D1 FFIEC deposit-interest expense fields from a bulk ZIP."""

    archive = Path(zip_path)
    report_date = _report_date_from_ffiec_archive(archive)
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        ri_member = _single_member(names, "FFIEC CDR Call Schedule RI ")
        por_member = _single_member(names, "FFIEC CDR Call Bulk POR ")
        ri_rows = _read_ffiec_tsv_member(zf, ri_member, skip_descriptor=True)
        por_rows = _read_ffiec_tsv_member(zf, por_member, skip_descriptor=False)

    names_by_rssd = {
        row.get("IDRSSD", "").strip(): row.get("Financial Institution Name", "").strip()
        for row in por_rows
        if row.get("IDRSSD", "").strip()
    }
    rows = []
    for row in ri_rows:
        rssd = row.get("IDRSSD", "").strip()
        if not rssd:
            continue
        rows.append(
            {
                "report_date": report_date,
                "rssd_id": rssd,
                "institution_name": names_by_rssd.get(rssd, ""),
                "RIAD4508": _numeric_text(row.get("RIAD4508")),
                "RIAD0093": _numeric_text(row.get("RIAD0093")),
                "RIADHK03": _numeric_text(row.get("RIADHK03")),
                "RIADHK04": _numeric_text(row.get("RIADHK04")),
                "RIAD4172": _numeric_text(row.get("RIAD4172")),
                "source_url": source_url,
                "source_archive": str(archive),
            }
        )
    write_rows(Path(output_path), rows, FFIEC_OUTPUT_FIELDS)
    return Path(output_path)


def materialize_ncua_share_interest_panel(
    zip_path: str | Path,
    output_path: str | Path,
    *,
    source_url: str,
) -> Path:
    """Extract D1 NCUA share/deposit interest fields from a quarterly ZIP."""

    archive = Path(zip_path)
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        fs220_member = _member_named(names, "FS220.txt")
        fs220a_member = _member_named(names, "FS220A.txt")
        profile_member = _member_named(names, "FOICU.txt")
        fs220_rows = _read_csv_member(zf, fs220_member)
        fs220a_rows = _read_csv_member(zf, fs220a_member)
        profile_rows = _read_csv_member(zf, profile_member)

    names_by_cu = {
        row.get("CU_NUMBER", "").strip(): row.get("CU_NAME", "").strip()
        for row in profile_rows
        if row.get("CU_NUMBER", "").strip()
    }
    fs220a_by_cu = {
        row.get("CU_NUMBER", "").strip(): row
        for row in fs220a_rows
        if row.get("CU_NUMBER", "").strip()
    }
    rows = []
    for row in fs220_rows:
        cu_number = row.get("CU_NUMBER", "").strip()
        if not cu_number:
            continue
        report_date = _parse_ncua_cycle_date(row.get("CYCLE_DATE"))
        if not report_date:
            continue
        rows.append(
            {
                "report_date": report_date,
                "charter_number": cu_number,
                "credit_union_name": names_by_cu.get(cu_number, ""),
                "380": _numeric_text(row.get("ACCT_380")),
                "381": _numeric_text(fs220a_by_cu.get(cu_number, {}).get("ACCT_381")),
                "340": _numeric_text(row.get("ACCT_340")),
                "350": _numeric_text(fs220a_by_cu.get(cu_number, {}).get("ACCT_350")),
                "source_url": source_url,
                "source_archive": str(archive),
            }
        )
    write_rows(Path(output_path), rows, NCUA_OUTPUT_FIELDS)
    return Path(output_path)


def _parse_bulk_page(html: str) -> _BulkDownloadPageParser:
    parser = _BulkDownloadPageParser()
    parser.feed(html)
    return parser


def _date_option_value(page: _BulkDownloadPageParser, report_date: str) -> str:
    for label, value in page.select_options.get("DatesDropDownList", []):
        if label == report_date:
            return value
    raise ValueError(f"Could not find FFIEC report date option {report_date}.")


def _parse_report_date(raw: str) -> datetime:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m%d%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported report date: {raw}")


def _report_date_from_ffiec_archive(path: Path) -> str:
    match = _FFIEC_DATE_TOKEN.search(path.name)
    if not match:
        raise ValueError(f"Could not infer FFIEC report date from {path.name}")
    return datetime.strptime(match.group(1), "%m%d%Y").date().isoformat()


def _single_member(names: list[str], token: str) -> str:
    matches = [name for name in names if token.lower() in name.lower()]
    if len(matches) != 1:
        raise ValueError(f"Expected one ZIP member containing {token!r}; found {matches}")
    return matches[0]


def _member_named(names: list[str], filename: str) -> str:
    requested = filename.lower()
    for name in names:
        if Path(name).name.lower() == requested:
            return name
    raise ValueError(f"Could not locate ZIP member {filename!r}.")


def _read_ffiec_tsv_member(
    archive: zipfile.ZipFile,
    member: str,
    *,
    skip_descriptor: bool,
) -> list[dict[str, str]]:
    with archive.open(member) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8-sig", newline="")
        rows = list(csv.reader(text, delimiter="\t"))
    if not rows:
        return []
    header = [cell.strip().strip('"') for cell in rows[0]]
    data_rows = rows[2:] if skip_descriptor else rows[1:]
    return [
        {header[index]: value.strip().strip('"') for index, value in enumerate(row)}
        for row in data_rows
        if any(cell.strip() for cell in row)
    ]


def _read_csv_member(archive: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    with archive.open(member) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8-sig", newline="")
        return list(csv.DictReader(text))


def _parse_ncua_cycle_date(raw: str | None) -> str:
    if raw is None:
        return ""
    text = raw.strip()
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _numeric_text(raw: Any) -> str:
    text = "" if raw is None else str(raw).strip().replace(",", "")
    return text if text not in {"", "."} else "0"
