"""Materialize recipient/leakage source snapshots into RateWall raw bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_lib
import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Mapping, Sequence

from ratewall.data.snapshots import read_snapshot_bundle, write_snapshot_bundle
from ratewall.sources.fed_dfa import FedDfaAdapter
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot, utc_now_iso
from ratewall.sources.fred import FredAdapter
from ratewall.sources.registry import SourceRegistry


RECIPIENT_LEAKAGE_FRED_SERIES: Mapping[str, str] = {
    "PII": "recipient_leakage_tax_clawback_context_only",
    "W055RC1": "recipient_leakage_tax_clawback_context_only",
    "NA000309Q": (
        "recipient_leakage_federal_interest_to_persons_business_context_only"
    ),
    "NA000310Q": "recipient_leakage_foreign_treasury_interest_payment_context_only",
}

IRS_SOI_SERIES_ID = "irs_soi_taxable_interest"
IRS_SOI_DEFAULT_CSV = Path(
    "data/raw/irs_soi/irs_soi_2023_table_1_4_taxable_interest.csv"
)
IRS_SOI_DEFAULT_PROVENANCE = Path("data/raw/irs_soi/PROVENANCE.json")

IRS_IRA_SERIES_ID = "irs_soi_ira_type_agi"
IRS_IRA_DEFAULT_XLSX = Path("data/raw/irs_soi/22in03ira.xlsx")
IRS_IRA_DEFAULT_CSV = Path("data/raw/irs_soi/irs_soi_2022_ira_type_agi.csv")
IRS_IRA_DEFAULT_PROVENANCE = Path("data/raw/irs_soi/PROVENANCE_ira_type_agi.json")
IRS_AVERAGE_TAX_RATE_SERIES_ID = "irs_soi_average_tax_rate_percentile"
IRS_AVERAGE_TAX_RATE_DEFAULT_XLSX = Path("data/raw/irs_soi/23in41ts.xlsx")
IRS_AVERAGE_TAX_RATE_DEFAULT_CSV = Path(
    "data/raw/irs_soi/irs_soi_2001_2023_average_tax_rate_percentile.csv"
)
IRS_AVERAGE_TAX_RATE_DEFAULT_PROVENANCE = Path(
    "data/raw/irs_soi/PROVENANCE_average_tax_rate_percentile.json"
)
FED_DFA_ACCOUNT_TYPE_SERIES_ID = "fed_dfa_household_account_type_context"
FED_SCF_SAFE_ASSET_ACCOUNT_TAX_SERIES_ID = (
    "fed_scf_2022_safe_asset_account_tax_context"
)
FED_SCF_SUMMARY_EXTRACT_DEFAULT = Path("data/raw/fed_scf/scfp2022excel.zip")
FED_SCF_SUMMARY_EXTRACT_FILE = "SCFP2022.csv"
IRS_ESTIMATED_TAX_PAYMENT_TIMING_SERIES_ID = "irs_estimated_tax_payment_timing"
IRS_STATE_INTEREST_AGI_SERIES_ID = "irs_soi_state_interest_agi"
IRS_STATE_INTEREST_DEFAULT_SOURCE_CSV = Path("data/raw/irs_soi/22in55cmcsv.csv")
IRS_STATE_INTEREST_DEFAULT_CSV = Path(
    "data/raw/irs_soi/irs_soi_2022_state_interest_agi.csv"
)
IRS_STATE_INTEREST_DEFAULT_PROVENANCE = Path(
    "data/raw/irs_soi/PROVENANCE_state_interest_agi.json"
)
TREASURY_INTEREST_TAX_TREATMENT_SERIES_ID = (
    "treasury_security_interest_tax_treatment"
)
IRS_INTEREST_RECEIVED_TAX_TOPIC_SERIES_ID = "irs_interest_received_tax_topic_403"
IRS_PUBLICATION_550_INTEREST_TAXONOMY_SERIES_ID = (
    "irs_publication_550_interest_income_taxonomy"
)
IRS_1099_INT_DIV_REPORTING_TAXONOMY_SERIES_ID = (
    "irs_1099_int_div_reporting_taxonomy"
)
FTA_STATE_INCOME_TAX_RATES_SERIES_ID = "fta_state_individual_income_tax_rates"
TIC_CUSTODY_LIMITATION_SERIES_ID = (
    "tic_foreign_holder_custody_limitation_context"
)
FED_CROSS_BORDER_TREASURY_BASIS_TRADE_SERIES_ID = (
    "fed_cross_border_treasury_basis_trade_context"
)

IRS_PAYMENT_TIMING_MARKERS = (
    "Making quarterly estimated tax payments during the year",
    "interest, dividends",
    "Estimated tax payments are generally due",
    "April 15 for income earned January 1 to March 31",
    "June 15 for income earned April 1 to May 31",
    "September 15 for income earned June 1 to August 31",
    "January 15 of the following year for income earned September 1 to December 31",
)

TREASURY_INTEREST_TAX_TREATMENT_MARKERS = (
    "What you earn from your Treasury marketable securities is subject to federal tax but is exempt from state and local taxes",
    "interest you earn on notes, bonds, TIPS, and FRNs",
    'Bill "interest" (the difference between the price you pay and the face value you get when the bill matures)',
    "IRS Form 1099 tells the IRS about interest and gains that may be subject to federal tax",
)

IRS_INTEREST_RECEIVED_TAX_TOPIC_MARKERS = (
    "Most interest that you receive or that is credited to an account that you can withdraw from without penalty is taxable income",
    "Interest on bank accounts, money market accounts, certificates of deposit, corporate bonds",
    "Interest income from Treasury bills, notes and bonds",
    "subject to federal income tax but is exempt from all state and local income taxes",
    "Interest on some bonds used to finance government operations and issued by a state",
    "Reporting tax-exempt interest received during the tax year is an information-reporting requirement only",
)

IRS_PUBLICATION_550_INTEREST_TAXONOMY_MARKERS = (
    "Publication 550 (2025)",
    "Taxable Interest—General",
    "Taxable interest includes interest you receive from bank accounts",
    "Money market funds",
    "Certificates of deposit and other deferred interest accounts",
    "U.S. Treasury Bills, Notes, and Bonds",
    "Interest income from Treasury bills, notes, and bonds is subject to federal income tax but is exempt from all state and local income taxes",
    "State or Local Government Obligations",
    "Interest you receive on an obligation issued by a state or local government generally is not taxable",
    "Information reporting requirement",
)

IRS_1099_INT_REPORTING_MARKERS = (
    "Instructions for Forms 1099-INT and 1099-OID",
    "Box 1. Interest Income",
    "Interest on U.S. Savings Bonds and Treasury Obligations",
    "Box 8. Tax-Exempt Interest",
    "Do not include in box 1 interest on tax-free covenant bonds or dividends from money market funds",
    "which are reportable on Form 1099-DIV",
    "Exempt recipients.",
    "individual retirement arrangement (IRA)",
    "nominee or custodian",
    "Interest excluded from reporting.",
    "foreign beneficial owner or foreign payee",
)

IRS_1099_DIV_REPORTING_URL = "https://www.irs.gov/instructions/i1099div"
IRS_1099_DIV_REPORTING_MARKERS = (
    "Instructions for Form 1099-DIV",
    "Box 1a. Total Ordinary Dividends",
    "Enter dividends, including dividends from money market funds",
    "Box 12. Exempt-Interest Dividends",
)

FED_CROSS_BORDER_TREASURY_BASIS_TRADE_MARKERS = (
    "The Cross-Border Trail of the Treasury Basis Trade",
    "around $1.4 trillion as of the end of 2024",
    "reaching $1.85 trillion by the end of 2024",
    "TIC data are collected",
    "Financial Accounts of the United States",
    "Appendix A - Estimating Cayman Islands' Holdings",
    "confidential fund-level data from Form PF",
    "publicly available data from the Financial Accounts",
    "Enhanced Financial Accounts",
    "ultimate nationality basis",
)

FED_CROSS_BORDER_ACCESSIBLE_MARKERS = (
    "The Cross-Border Trail of the Treasury Basis Trade, Accessible Data",
    "Adjusted TIC data for Estimated Holdings of Treasury Securities",
    "Figure A1. Estimating Cayman Islands Hedge Funds",
    "Estimate using Z.1",
    "Cayman Hedge Funds",
)

TIC_CUSTODY_LIMITATION_MARKERS = (
    "What are the problems of geographic attribution for securities holdings and transactions in the TIC system?",
    "the MFH estimates are based primarily on custodial data from the TIC SLT",
    "they cannot attribute holdings of U.S. Treasury securities with complete accuracy",
    "if a U.S. Treasury security purchased by a foreign resident is held in a custodial account in a third country, the true country of ownership of the security will not be reflected in the data",
    "managed by foreign private portfolio managers who invest on behalf of residents of other countries",
)

FTA_STATE_INCOME_TAX_RATE_MARKERS = (
    "2024 STATE INDIVIDUAL INCOME TAX RATES",
    "Tax rates for tax year 2024",
    "as of January 1, 2025",
    "Source: The Federation of Tax Administrators from various sources",
    "No State Income Tax",
)

FED_SCF_SAFE_ASSET_ACCOUNT_FIELDS: tuple[tuple[str, str, str, str], ...] = (
    (
        "CHECKING",
        "checking_transaction_accounts",
        "deposit_or_transaction_account_context",
        "potentially_taxable_liquid_account_context",
    ),
    (
        "SAVING",
        "saving_accounts",
        "deposit_account_context",
        "potentially_taxable_liquid_account_context",
    ),
    (
        "MMDA",
        "money_market_deposit_accounts",
        "deposit_account_context",
        "potentially_taxable_liquid_account_context",
    ),
    (
        "MMMF",
        "money_market_mutual_funds",
        "money_fund_account_context",
        "potentially_taxable_fund_account_context",
    ),
    (
        "CALL",
        "call_accounts_at_brokerages",
        "brokerage_liquid_account_context",
        "potentially_taxable_liquid_account_context",
    ),
    (
        "CDS",
        "certificates_of_deposit",
        "deposit_account_context",
        "potentially_taxable_deferred_interest_context",
    ),
    (
        "NMMF",
        "pooled_investment_funds_excluding_money_market_funds",
        "pooled_fund_account_context",
        "potentially_taxable_or_tax_deferred_fund_context",
    ),
    (
        "BOND",
        "directly_held_bonds",
        "bond_account_context",
        "potentially_taxable_or_tax_exempt_bond_context",
    ),
    (
        "SAVBND",
        "us_savings_bonds",
        "treasury_savings_bond_context",
        "treasury_interest_tax_treatment_context",
    ),
    (
        "RETQLIQ",
        "quasi_liquid_retirement_accounts",
        "retirement_account_context",
        "tax_deferred_or_tax_preferred_account_context",
    ),
    (
        "CASHLI",
        "cash_value_life_insurance",
        "insurance_account_context",
        "tax_deferred_or_fiduciary_account_context",
    ),
    (
        "INTDIVINC",
        "interest_and_dividend_income",
        "income_flow_context",
        "mixed_interest_dividend_tax_context_not_source_specific",
    ),
)

STATE_NAME_TO_POSTAL = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
    "DIST. OF COLUMBIA": "DC",
}


def _records_sha256(records: Sequence[object]) -> str:
    payload = json.dumps(
        list(records),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _date_range(snapshot: SourceSnapshot) -> tuple[str, str]:
    dates = sorted(
        str(record.get("date", ""))
        for record in snapshot.records
        if record.get("date")
    )
    if not dates:
        return "", ""
    return dates[0], dates[-1]


def _annotated_leakage_context_snapshot(
    snapshot: SourceSnapshot, *, context_status: str
) -> SourceSnapshot:
    first_date, latest_date = _date_range(snapshot)
    records_hash = _records_sha256(snapshot.records)
    note = (
        f"{context_status};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(snapshot.records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "foreign_leakage_gate_passed=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "holder_allocation_enabled=false"
    )
    return SourceSnapshot(
        metadata=replace(snapshot.metadata, note=note),
        records=snapshot.records,
    )


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_float(value: str) -> float:
    if value == "":
        return math.nan
    try:
        return float(value)
    except ValueError:
        return math.nan


def _summary_number(value: float) -> str:
    if not math.isfinite(value):
        return ""
    normalized = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if normalized == "-0" else normalized


def _weighted_total(rows: Sequence[dict[str, str]], field: str) -> float:
    total = 0.0
    for row in rows:
        value = _source_float(row.get(field, ""))
        weight = _source_float(row.get("WGT", "")) / 5.0
        if not math.isfinite(value) or not math.isfinite(weight) or weight <= 0:
            continue
        total += value * weight
    return total


def _weighted_mean(rows: Sequence[dict[str, str]], field: str) -> float:
    numerator = 0.0
    denominator = 0.0
    for row in rows:
        value = _source_float(row.get(field, ""))
        weight = _source_float(row.get("WGT", "")) / 5.0
        if not math.isfinite(value) or not math.isfinite(weight) or weight <= 0:
            continue
        numerator += value * weight
        denominator += weight
    return numerator / denominator if denominator else math.nan


def _weighted_positive_share(rows: Sequence[dict[str, str]], field: str) -> float:
    numerator = 0.0
    denominator = 0.0
    for row in rows:
        value = _source_float(row.get(field, ""))
        weight = _source_float(row.get("WGT", "")) / 5.0
        if not math.isfinite(value) or not math.isfinite(weight) or weight <= 0:
            continue
        numerator += (1.0 if value > 0 else 0.0) * weight
        denominator += weight
    return numerator / denominator if denominator else math.nan


def _fed_scf_safe_asset_account_tax_records(
    source_zip: Path,
) -> list[dict[str, str]]:
    with zipfile.ZipFile(source_zip) as archive:
        names = archive.namelist()
        if FED_SCF_SUMMARY_EXTRACT_FILE not in names:
            raise ValueError(
                f"{source_zip} missing {FED_SCF_SUMMARY_EXTRACT_FILE}"
            )
        with archive.open(FED_SCF_SUMMARY_EXTRACT_FILE) as handle:
            source_rows = list(
                csv.DictReader(line.decode("utf-8-sig") for line in handle)
            )
    if not source_rows:
        raise ValueError("Fed SCF summary extract CSV had no records")
    required = {
        "YY1",
        "WGT",
        *(field for field, _, _, _ in FED_SCF_SAFE_ASSET_ACCOUNT_FIELDS),
    }
    missing = required - set(source_rows[0])
    if missing:
        raise ValueError(
            "Fed SCF safe-asset account context missing required fields: "
            + ",".join(sorted(missing))
        )
    source_family_count = len({row.get("YY1", "") for row in source_rows})
    weighted_family_count = 0.0
    for row in source_rows:
        weight = _source_float(row.get("WGT", ""))
        if math.isfinite(weight) and weight > 0:
            weighted_family_count += weight / 5.0
    records: list[dict[str, str]] = []
    for field, label, account_context, tax_context in FED_SCF_SAFE_ASSET_ACCOUNT_FIELDS:
        records.append(
            {
                "date": "2022-01-01",
                "survey_year": "2022",
                "source_file": FED_SCF_SUMMARY_EXTRACT_FILE,
                "source_field": field,
                "source_field_label": label,
                "source_public_extract_record_count": str(len(source_rows)),
                "source_public_family_count": str(source_family_count),
                "weighted_family_count": _summary_number(weighted_family_count),
                "summary_method": "weighted_descriptive_account_context_only",
                "weight_field": "WGT",
                "imputation_handling": "all_implicates_weight_divided_by_5",
                "field_unit": "2022_dollars_or_income_flow",
                "weighted_total_2022_dollars": _summary_number(
                    _weighted_total(source_rows, field)
                ),
                "weighted_mean_2022_dollars": _summary_number(
                    _weighted_mean(source_rows, field)
                ),
                "weighted_positive_family_share": _summary_number(
                    _weighted_positive_share(source_rows, field)
                ),
                "account_type_context": account_context,
                "tax_relevance_context": tax_context,
                "source_specific_recipient_mapping_available": "false",
                "source_specific_interest_payer_mapping_available": "false",
                "current_demand_conversion_available": "false",
                "tax_clawback_gate_passed": "false",
                "demand_conversion_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "holder_allocation_enabled": "false",
                "exact_blocker": (
                    "SCF public extract supplies household balance-sheet "
                    "account and instrument context, but not source-specific "
                    "Treasury/Fed/MMF/deposit interest payers, tax incidence, "
                    "or current-demand conversion."
                ),
            }
        )
    return records


def _fed_scf_safe_asset_account_tax_snapshot(
    *, registry: SourceRegistry, source_zip: Path
) -> SourceSnapshot:
    series = registry.series[FED_SCF_SAFE_ASSET_ACCOUNT_TAX_SERIES_ID]
    if not source_zip.exists():
        _download_source(series.endpoint, source_zip)
    records = _fed_scf_safe_asset_account_tax_records(source_zip)
    source_zip_hash = _file_sha256(source_zip)
    records_hash = _records_sha256(records)
    note = (
        "recipient_leakage_fed_scf_safe_asset_account_tax_context_only;"
        f"source_zip_sha256={source_zip_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"source_file={FED_SCF_SUMMARY_EXTRACT_FILE};"
        "survey_year=2022;"
        "schema=safe_asset_and_tax_account_weighted_summary;"
        "deposit_mmf_bond_retirement_account_context_available=true;"
        "source_specific_recipient_mapping_available=false;"
        "source_specific_interest_payer_mapping_available=false;"
        "current_demand_conversion_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "holder_allocation_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at="2024-04-03",
            snapshot_kind="live_zip_csv_weighted_summary_context",
            note=note,
        ),
        records=records,
    )


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _download_source(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ratewall-research-source-admission/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        output.write_bytes(response.read())


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ratewall-research-source-admission/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _fetch_public_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 ratewall-research"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _posted_date(html: str) -> str:
    match = re.search(r'"datePosted"\s*:\s*"(?P<date>\d{4}-\d{2}-\d{2})', html)
    if match:
        return match.group("date")
    update = re.search(
        r"Last Update:\s*(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})",
        _plain_text(html),
    )
    if not update:
        return ""
    month_names = {
        "January": "01",
        "February": "02",
        "March": "03",
        "April": "04",
        "May": "05",
        "June": "06",
        "July": "07",
        "August": "08",
        "September": "09",
        "October": "10",
        "November": "11",
        "December": "12",
    }
    month = month_names.get(update.group("month"))
    if month is None:
        return ""
    return f"{update.group('year')}-{month}-{int(update.group('day')):02d}"


def _clean_state_name(raw_state_name: str) -> str:
    return re.sub(r"\s+\([a-z0-9]+\)$", "", raw_state_name).strip()


def _clean_html_cell(cell_html: str) -> str:
    cleaned = re.sub(r"<br\s*/?>", " ", cell_html, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return html_lib.unescape(re.sub(r"\s+", " ", cleaned)).strip()


def _extract_fta_state_income_tax_rows(table_html: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.DOTALL):
        cells = [
            _clean_html_cell(cell_html)
            for cell_html in re.findall(
                r"<t[dh][^>]*>(.*?)</t[dh]>",
                row_html,
                flags=re.DOTALL,
            )
        ]
        if cells and cells[0] and cells[0] != "State":
            rows.append(cells[:13])
    return rows


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    strings: list[str] = []
    for item in root.findall("x:si", ns):
        parts = [node.text or "" for node in item.findall(".//x:t", ns)]
        strings.append("".join(parts).strip())
    return strings


def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char.upper()) - ord("A") + 1)
    return index


def _sheet_values(path: Path) -> dict[tuple[int, int], str]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    values: dict[tuple[int, int], str] = {}
    for row in root.findall(".//x:sheetData/x:row", ns):
        row_index = int(row.attrib["r"])
        for cell in row.findall("x:c", ns):
            ref = cell.attrib["r"]
            value_node = cell.find("x:v", ns)
            if value_node is None:
                continue
            raw_value = value_node.text or ""
            if cell.attrib.get("t") == "s":
                value = shared[int(raw_value)]
            else:
                value = raw_value
            values[(row_index, _column_index(ref))] = value.strip()
    return values


def _normalize_number(value: str) -> str:
    if value == "":
        return ""
    if re.fullmatch(r"-?\d+(?:\.0+)?", value):
        return str(int(float(value)))
    return value


def _normalize_csv_number(value: str) -> str:
    cleaned = value.replace(",", "").strip()
    if cleaned in {"", "d", "n/a", "**"}:
        return cleaned
    return _normalize_number(cleaned)


def _parse_ira_workbook(path: Path) -> list[dict[str, str]]:
    cells = _sheet_values(path)
    title = cells.get((1, 1), "")
    unit_note = cells.get((2, 1), "")
    source_note = cells.get((28, 1), "")
    if "Individual Retirement Arrangement (IRA) Plans" not in title:
        raise ValueError(f"{path} is not IRS SOI IRA Table 3")
    if "money amounts are in thousands" not in unit_note.lower():
        raise ValueError(f"{path} missing expected IRS SOI IRA unit note")
    if "Individual Retirement Arrangements Study" not in source_note:
        raise ValueError(f"{path} missing expected IRS SOI IRA source note")

    plan_columns = {
        "traditional_ira": (2, 3, 4, 5, 6, 7),
        "roth_ira": (8, 9, 10, 11, 12, 13),
        "sep_ira": (14, 15, 16, 17, 18, 19),
        "simple_ira": (20, 21, 22, 23, 24, 25),
    }
    source_rows = [8, *range(10, 25)]
    records: list[dict[str, str]] = []
    for row_index in source_rows:
        agi_class = cells.get((row_index, 1), "").strip()
        if not agi_class:
            raise ValueError(f"{path} missing AGI class in row {row_index}")
        for plan_type, columns in plan_columns.items():
            (
                contribution_taxpayers_col,
                contribution_amount_col,
                contribution_average_col,
                fmv_taxpayers_col,
                fmv_amount_col,
                fmv_average_col,
            ) = columns
            records.append(
                {
                    "date": "2022-01-01",
                    "tax_year": "2022",
                    "publication_month": "2025-02",
                    "source_table_id": "Table 3",
                    "source_sheet": "sheet1",
                    "source_row_index_one_based": str(row_index),
                    "agi_class": agi_class,
                    "ira_plan_type": plan_type,
                    "contribution_taxpayers": _normalize_number(
                        cells.get((row_index, contribution_taxpayers_col), "")
                    ),
                    "contribution_amount_thousand_usd": _normalize_number(
                        cells.get((row_index, contribution_amount_col), "")
                    ),
                    "contribution_average_usd": _normalize_number(
                        cells.get((row_index, contribution_average_col), "")
                    ),
                    "fair_market_value_taxpayers": _normalize_number(
                        cells.get((row_index, fmv_taxpayers_col), "")
                    ),
                    "fair_market_value_amount_thousand_usd": _normalize_number(
                        cells.get((row_index, fmv_amount_col), "")
                    ),
                    "fair_market_value_average_usd": _normalize_number(
                        cells.get((row_index, fmv_average_col), "")
                    ),
                    "account_type_context": (
                        "tax_deferred_or_tax_preferred_retirement_account_context"
                    ),
                    "evidence_role": "tax_clawback_account_type_context_only",
                    "tax_clawback_gate_passed": "false",
                    "demand_conversion_prior_narrowing_allowed": "false",
                    "formula_replacement_allowed": "false",
                    "main_ratio_admission_allowed": "false",
                    "incidence_output_enabled": "false",
                    "welfare_tax_mpc_output_enabled": "false",
                }
            )
    return records


def _parse_average_tax_rate_workbook(path: Path) -> list[dict[str, str]]:
    cells = _sheet_values(path)
    title = cells.get((1, 1), "")
    sample_note = cells.get((2, 1), "")
    source_note = cells.get((204, 1), "")
    if "Table 4.1" not in title or "Average" not in title:
        raise ValueError(f"{path} is not IRS SOI Table 4.1")
    if "estimates based on samples" not in sample_note.lower():
        raise ValueError(f"{path} missing expected IRS SOI sample note")
    if "IRS, Statistics of Income Division" not in source_note:
        raise ValueError(f"{path} missing expected IRS SOI source note")

    percentile_columns = {
        "total": 2,
        "top_0_001_percent": 3,
        "top_0_01_percent": 4,
        "top_0_1_percent": 5,
        "top_1_percent": 6,
        "top_2_percent": 7,
        "top_3_percent": 8,
        "top_4_percent": 9,
        "top_5_percent": 10,
        "top_10_percent": 11,
        "top_20_percent": 12,
        "top_25_percent": 13,
        "top_30_percent": 14,
        "top_40_percent": 15,
        "top_50_percent": 16,
    }
    sections = (
        ("number_of_returns", 7, "returns"),
        ("agi_floor_current_dollars", 31, "current_whole_dollars"),
        ("agi_floor_constant_dollars", 55, "constant_whole_dollars"),
        ("adjusted_gross_income", 79, "millions_of_dollars"),
        ("total_income_tax", 103, "millions_of_dollars"),
        ("average_tax_rate", 127, "percentage"),
        ("adjusted_gross_income_share", 151, "percentage"),
        ("total_income_tax_share", 175, "percentage"),
    )
    records: list[dict[str, str]] = []
    for measure, header_row, unit in sections:
        source_label = cells.get((header_row, 1), "")
        for row_index in range(header_row + 1, header_row + 24):
            tax_year = cells.get((row_index, 1), "")
            if not tax_year or not tax_year[:4].isdigit():
                raise ValueError(
                    f"{path} missing tax year for {measure} row {row_index}"
                )
            for percentile_group, column_index in percentile_columns.items():
                raw_value = cells.get((row_index, column_index), "")
                if raw_value == "":
                    raise ValueError(
                        f"{path} missing {measure} value in row {row_index}, "
                        f"column {column_index}"
                    )
                records.append(
                    {
                        "date": f"{tax_year}-01-01",
                        "tax_year": tax_year,
                        "publication_month": "2026-03",
                        "source_table_id": "Table 4.1",
                        "source_sheet": "sheet1",
                        "source_row_index_one_based": str(row_index),
                        "source_measure_label": source_label,
                        "measure": measure,
                        "percentile_group": percentile_group,
                        "value": _normalize_number(raw_value),
                        "unit": unit,
                        "tax_rate_distribution_context": "true",
                        "full_tax_incidence_available": "false",
                        "source_specific_recipient_mapping_available": "false",
                        "taxable_tax_deferred_source_mapping_available": "false",
                        "current_demand_conversion_available": "false",
                        "evidence_role": "tax_clawback_tax_rate_distribution_context_only",
                        "tax_clawback_gate_passed": "false",
                        "demand_conversion_prior_narrowing_allowed": "false",
                        "formula_replacement_allowed": "false",
                        "main_ratio_admission_allowed": "false",
                        "incidence_output_enabled": "false",
                        "welfare_tax_mpc_output_enabled": "false",
                    }
                )
    return records


def _write_csv(path: Path, records: Sequence[dict[str, str]]) -> None:
    if not records:
        raise ValueError(f"no rows available for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def _write_ira_artifacts_if_needed(
    *,
    registry: SourceRegistry,
    xlsx_path: Path,
    csv_path: Path,
    provenance_path: Path,
) -> None:
    series = registry.series[IRS_IRA_SERIES_ID]
    if not xlsx_path.exists():
        _download_source(series.endpoint, xlsx_path)
    records = _parse_ira_workbook(xlsx_path)
    if len(records) != 64:
        raise ValueError(f"{xlsx_path} produced {len(records)} rows, expected 64")
    _write_csv(csv_path, records)
    provenance = {
        "source_id": series.source,
        "series_id": series.series_id,
        "source_url": series.endpoint,
        "source_xlsx_sha256": _file_sha256(xlsx_path),
        "converted_csv_sha256": _file_sha256(csv_path),
        "source_record_count": len(records),
        "tax_year": "2022",
        "publication_month": "2025-02",
        "source_table_id": "Table 3",
        "source_schema": "ira_plan_type_contributions_and_fmv_by_agi",
        "units": series.units,
        "frequency": series.frequency,
        "retrieved_at": utc_now_iso(),
        "tax_clawback_gate_passed": False,
        "demand_conversion_prior_narrowing_allowed": False,
        "formula_replacement_allowed": False,
        "main_ratio_admission_allowed": False,
        "incidence_output_enabled": False,
        "welfare_tax_mpc_output_enabled": False,
    }
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_average_tax_rate_artifacts_if_needed(
    *,
    registry: SourceRegistry,
    xlsx_path: Path,
    csv_path: Path,
    provenance_path: Path,
) -> None:
    series = registry.series[IRS_AVERAGE_TAX_RATE_SERIES_ID]
    if not xlsx_path.exists():
        _download_source(series.endpoint, xlsx_path)
    records = _parse_average_tax_rate_workbook(xlsx_path)
    expected_count = 8 * 23 * 15
    if len(records) != expected_count:
        raise ValueError(
            f"{xlsx_path} produced {len(records)} rows, expected {expected_count}"
        )
    _write_csv(csv_path, records)
    provenance = {
        "source_id": series.source,
        "series_id": series.series_id,
        "source_url": series.endpoint,
        "source_xlsx_sha256": _file_sha256(xlsx_path),
        "converted_csv_sha256": _file_sha256(csv_path),
        "source_record_count": len(records),
        "first_date": "2001-01-01",
        "latest_date": "2023-01-01",
        "tax_years": "2001-2023",
        "publication_month": "2026-03",
        "source_table_id": "Table 4.1",
        "source_schema": "tax_year_percentile_measure_long",
        "units": series.units,
        "frequency": series.frequency,
        "retrieved_at": utc_now_iso(),
        "tax_rate_distribution_context": True,
        "full_tax_incidence_available": False,
        "source_specific_recipient_mapping_available": False,
        "taxable_tax_deferred_source_mapping_available": False,
        "current_demand_conversion_available": False,
        "tax_clawback_gate_passed": False,
        "demand_conversion_prior_narrowing_allowed": False,
        "formula_replacement_allowed": False,
        "main_ratio_admission_allowed": False,
        "incidence_output_enabled": False,
        "welfare_tax_mpc_output_enabled": False,
    }
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _parse_state_interest_csv(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    expected_columns = {
        "STATE",
        "AGI_STUB",
        "N1",
        "A00100",
        "N00300",
        "A00300",
        "N00400",
        "A00400",
        "N00600",
        "A00600",
        "N00650",
        "A00650",
        "N05800",
        "A05800",
        "N06500",
        "A06500",
    }
    if not rows:
        raise ValueError(f"{path} contains no IRS SOI state rows")
    missing = expected_columns - set(rows[0])
    if missing:
        raise ValueError(
            f"{path} missing IRS SOI state schema columns: "
            f"{', '.join(sorted(missing))}"
        )
    records: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        records.append(
            {
                "date": "2022-01-01",
                "tax_year": "2022",
                "publication_month": "2025-12",
                "source_table_id": "Historic Table 2",
                "source_row_index_one_based": str(index),
                "state_code": row["STATE"].strip(),
                "agi_stub": row["AGI_STUB"].strip(),
                "number_of_returns": _normalize_csv_number(row["N1"]),
                "adjusted_gross_income_amount_thousand_usd": (
                    _normalize_csv_number(row["A00100"])
                ),
                "taxable_interest_number_of_returns": _normalize_csv_number(
                    row["N00300"]
                ),
                "taxable_interest_amount_thousand_usd": _normalize_csv_number(
                    row["A00300"]
                ),
                "tax_exempt_interest_number_of_returns": _normalize_csv_number(
                    row["N00400"]
                ),
                "tax_exempt_interest_amount_thousand_usd": _normalize_csv_number(
                    row["A00400"]
                ),
                "ordinary_dividends_number_of_returns": _normalize_csv_number(
                    row["N00600"]
                ),
                "ordinary_dividends_amount_thousand_usd": _normalize_csv_number(
                    row["A00600"]
                ),
                "qualified_dividends_number_of_returns": _normalize_csv_number(
                    row["N00650"]
                ),
                "qualified_dividends_amount_thousand_usd": _normalize_csv_number(
                    row["A00650"]
                ),
                "income_tax_before_credits_number_of_returns": (
                    _normalize_csv_number(row["N05800"])
                ),
                "income_tax_before_credits_amount_thousand_usd": (
                    _normalize_csv_number(row["A05800"])
                ),
                "total_income_tax_number_of_returns": _normalize_csv_number(
                    row["N06500"]
                ),
                "total_income_tax_amount_thousand_usd": _normalize_csv_number(
                    row["A06500"]
                ),
                "state_agi_recipient_context_available": "true",
                "source_specific_recipient_mapping_available": "false",
                "state_tax_treatment_available": "false",
                "current_demand_conversion_available": "false",
                "tax_clawback_gate_passed": "false",
                "demand_conversion_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    return records


def _write_state_interest_artifacts_if_needed(
    *,
    registry: SourceRegistry,
    source_csv_path: Path,
    converted_csv_path: Path,
    provenance_path: Path,
) -> None:
    series = registry.series[IRS_STATE_INTEREST_AGI_SERIES_ID]
    if not source_csv_path.exists():
        _download_source(series.endpoint, source_csv_path)
    records = _parse_state_interest_csv(source_csv_path)
    if len(records) != 594:
        raise ValueError(
            f"{source_csv_path} produced {len(records)} rows, expected 594"
        )
    _write_csv(converted_csv_path, records)
    state_count = len({record["state_code"] for record in records})
    agi_stub_count = len({record["agi_stub"] for record in records})
    provenance = {
        "source_id": series.source,
        "series_id": series.series_id,
        "source_url": series.endpoint,
        "source_csv_sha256": _file_sha256(source_csv_path),
        "converted_csv_sha256": _file_sha256(converted_csv_path),
        "source_record_count": len(records),
        "state_or_area_count": state_count,
        "agi_stub_count": agi_stub_count,
        "tax_year": "2022",
        "publication_month": "2025-12",
        "source_table_id": "Historic Table 2",
        "source_schema": "taxable_interest_and_tax_context_by_state_and_agi",
        "units": series.units,
        "frequency": series.frequency,
        "retrieved_at": utc_now_iso(),
        "state_agi_recipient_context_available": True,
        "source_specific_recipient_mapping_available": False,
        "state_tax_treatment_available": False,
        "current_demand_conversion_available": False,
        "tax_clawback_gate_passed": False,
        "demand_conversion_prior_narrowing_allowed": False,
        "formula_replacement_allowed": False,
        "main_ratio_admission_allowed": False,
        "incidence_output_enabled": False,
        "welfare_tax_mpc_output_enabled": False,
    }
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _irs_soi_snapshot(
    *, registry: SourceRegistry, csv_path: Path, provenance_path: Path
) -> SourceSnapshot | None:
    if not csv_path.exists() or not provenance_path.exists():
        return None
    series = registry.series[IRS_SOI_SERIES_ID]
    provenance = _read_json(provenance_path)
    records = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    if not records:
        raise ValueError(f"{csv_path} contains no IRS SOI rows")
    expected_columns = {
        "date",
        "tax_year",
        "filing_year",
        "publication_month",
        "source_table_id",
        "source_sheet",
        "source_row_index_zero_based",
        "return_population",
        "agi_class",
        "number_of_returns",
        "taxable_interest_number_of_returns",
        "taxable_interest_amount_thousand_usd",
        "tax_exempt_interest_number_of_returns",
        "tax_exempt_interest_amount_thousand_usd",
        "taxable_income_number_of_returns",
        "taxable_income_amount_thousand_usd",
        "income_tax_before_credits_number_of_returns",
        "income_tax_before_credits_amount_thousand_usd",
    }
    missing = expected_columns - set(records[0])
    if missing:
        raise ValueError(
            f"{csv_path} missing IRS SOI schema columns: {', '.join(sorted(missing))}"
        )
    csv_sha = _file_sha256(csv_path)
    if provenance.get("converted_csv_sha256") != csv_sha:
        raise ValueError(f"{csv_path} hash does not match {provenance_path}")
    note = (
        "recipient_leakage_irs_soi_taxable_interest_context_only;"
        f"source_xls_sha256={provenance.get('source_xls_sha256', '')};"
        f"converted_csv_sha256={csv_sha};"
        f"source_record_count={len(records)};"
        f"tax_year={provenance.get('tax_year', '')};"
        f"filing_year={provenance.get('filing_year', '')};"
        f"publication_month={provenance.get('publication_month', '')};"
        "schema=taxable_interest_tax_exempt_interest_taxable_income_"
        "income_tax_before_credits_by_agi;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at=str(provenance.get("publication_month", "")),
            snapshot_kind="converted_source_snapshot",
            note=note,
        ),
        records=records,
    )


def _irs_ira_snapshot(
    *, registry: SourceRegistry, csv_path: Path, provenance_path: Path
) -> SourceSnapshot | None:
    if not csv_path.exists() or not provenance_path.exists():
        return None
    series = registry.series[IRS_IRA_SERIES_ID]
    provenance = _read_json(provenance_path)
    records = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    if not records:
        raise ValueError(f"{csv_path} contains no IRS SOI IRA rows")
    expected_columns = {
        "date",
        "tax_year",
        "publication_month",
        "source_table_id",
        "source_sheet",
        "source_row_index_one_based",
        "agi_class",
        "ira_plan_type",
        "contribution_taxpayers",
        "contribution_amount_thousand_usd",
        "contribution_average_usd",
        "fair_market_value_taxpayers",
        "fair_market_value_amount_thousand_usd",
        "fair_market_value_average_usd",
        "account_type_context",
        "evidence_role",
        "tax_clawback_gate_passed",
        "demand_conversion_prior_narrowing_allowed",
        "formula_replacement_allowed",
        "main_ratio_admission_allowed",
        "incidence_output_enabled",
        "welfare_tax_mpc_output_enabled",
    }
    missing = expected_columns - set(records[0])
    if missing:
        raise ValueError(
            f"{csv_path} missing IRS SOI IRA schema columns: "
            f"{', '.join(sorted(missing))}"
        )
    csv_sha = _file_sha256(csv_path)
    if provenance.get("converted_csv_sha256") != csv_sha:
        raise ValueError(f"{csv_path} hash does not match {provenance_path}")
    note = (
        "recipient_leakage_irs_soi_ira_account_type_context_only;"
        f"source_xlsx_sha256={provenance.get('source_xlsx_sha256', '')};"
        f"converted_csv_sha256={csv_sha};"
        f"source_record_count={len(records)};"
        f"tax_year={provenance.get('tax_year', '')};"
        f"publication_month={provenance.get('publication_month', '')};"
        "schema=ira_plan_type_contributions_and_fmv_by_agi;"
        "account_type_context_available=true;"
        "state_tax_context_available=false;"
        "payment_timing_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=str(provenance.get("retrieved_at", utc_now_iso())),
            source_release_at=str(provenance.get("publication_month", "")),
            snapshot_kind="converted_source_snapshot",
            note=note,
        ),
        records=records,
    )


def _irs_average_tax_rate_snapshot(
    *, registry: SourceRegistry, csv_path: Path, provenance_path: Path
) -> SourceSnapshot | None:
    if not csv_path.exists() or not provenance_path.exists():
        return None
    series = registry.series[IRS_AVERAGE_TAX_RATE_SERIES_ID]
    provenance = _read_json(provenance_path)
    records = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    if not records:
        raise ValueError(f"{csv_path} contains no IRS SOI average tax-rate rows")
    expected_columns = {
        "date",
        "tax_year",
        "publication_month",
        "source_table_id",
        "source_sheet",
        "source_row_index_one_based",
        "source_measure_label",
        "measure",
        "percentile_group",
        "value",
        "unit",
        "tax_rate_distribution_context",
        "full_tax_incidence_available",
        "source_specific_recipient_mapping_available",
        "taxable_tax_deferred_source_mapping_available",
        "current_demand_conversion_available",
        "evidence_role",
        "tax_clawback_gate_passed",
        "demand_conversion_prior_narrowing_allowed",
        "formula_replacement_allowed",
        "main_ratio_admission_allowed",
        "incidence_output_enabled",
        "welfare_tax_mpc_output_enabled",
    }
    missing = expected_columns - set(records[0])
    if missing:
        raise ValueError(
            f"{csv_path} missing IRS SOI average tax-rate schema columns: "
            f"{', '.join(sorted(missing))}"
        )
    csv_sha = _file_sha256(csv_path)
    if provenance.get("converted_csv_sha256") != csv_sha:
        raise ValueError(f"{csv_path} hash does not match {provenance_path}")
    note = (
        "recipient_leakage_irs_soi_average_tax_rate_percentile_context_only;"
        f"source_xlsx_sha256={provenance.get('source_xlsx_sha256', '')};"
        f"converted_csv_sha256={csv_sha};"
        f"source_record_count={len(records)};"
        f"tax_years={provenance.get('tax_years', '')};"
        f"publication_month={provenance.get('publication_month', '')};"
        "schema=tax_year_percentile_measure_long;"
        "tax_rate_distribution_context_available=true;"
        "full_tax_incidence_available=false;"
        "source_specific_recipient_mapping_available=false;"
        "taxable_tax_deferred_source_mapping_available=false;"
        "current_demand_conversion_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=str(provenance.get("retrieved_at", utc_now_iso())),
            source_release_at=str(provenance.get("publication_month", "")),
            snapshot_kind="converted_source_snapshot",
            note=note,
        ),
        records=records,
    )


def _irs_state_interest_snapshot(
    *, registry: SourceRegistry, csv_path: Path, provenance_path: Path
) -> SourceSnapshot | None:
    if not csv_path.exists() or not provenance_path.exists():
        return None
    series = registry.series[IRS_STATE_INTEREST_AGI_SERIES_ID]
    provenance = _read_json(provenance_path)
    records = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    if not records:
        raise ValueError(f"{csv_path} contains no IRS SOI state interest rows")
    expected_columns = {
        "date",
        "tax_year",
        "publication_month",
        "source_table_id",
        "source_row_index_one_based",
        "state_code",
        "agi_stub",
        "number_of_returns",
        "adjusted_gross_income_amount_thousand_usd",
        "taxable_interest_number_of_returns",
        "taxable_interest_amount_thousand_usd",
        "tax_exempt_interest_number_of_returns",
        "tax_exempt_interest_amount_thousand_usd",
        "ordinary_dividends_number_of_returns",
        "ordinary_dividends_amount_thousand_usd",
        "qualified_dividends_number_of_returns",
        "qualified_dividends_amount_thousand_usd",
        "income_tax_before_credits_number_of_returns",
        "income_tax_before_credits_amount_thousand_usd",
        "total_income_tax_number_of_returns",
        "total_income_tax_amount_thousand_usd",
        "state_agi_recipient_context_available",
        "source_specific_recipient_mapping_available",
        "state_tax_treatment_available",
        "current_demand_conversion_available",
        "tax_clawback_gate_passed",
        "demand_conversion_prior_narrowing_allowed",
        "formula_replacement_allowed",
        "main_ratio_admission_allowed",
        "incidence_output_enabled",
        "welfare_tax_mpc_output_enabled",
    }
    missing = expected_columns - set(records[0])
    if missing:
        raise ValueError(
            f"{csv_path} missing IRS SOI state interest schema columns: "
            f"{', '.join(sorted(missing))}"
        )
    csv_sha = _file_sha256(csv_path)
    if provenance.get("converted_csv_sha256") != csv_sha:
        raise ValueError(f"{csv_path} hash does not match {provenance_path}")
    note = (
        "recipient_leakage_irs_soi_state_agi_interest_context_only;"
        f"source_csv_sha256={provenance.get('source_csv_sha256', '')};"
        f"converted_csv_sha256={csv_sha};"
        f"source_record_count={len(records)};"
        f"state_or_area_count={provenance.get('state_or_area_count', '')};"
        f"agi_stub_count={provenance.get('agi_stub_count', '')};"
        f"tax_year={provenance.get('tax_year', '')};"
        f"publication_month={provenance.get('publication_month', '')};"
        "schema=taxable_interest_and_tax_context_by_state_and_agi;"
        "state_agi_recipient_context_available=true;"
        "source_specific_recipient_mapping_available=false;"
        "state_tax_treatment_available=false;"
        "current_demand_conversion_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=str(provenance.get("retrieved_at", utc_now_iso())),
            source_release_at=str(provenance.get("publication_month", "")),
            snapshot_kind="converted_source_snapshot",
            note=note,
        ),
        records=records,
    )


def _irs_payment_timing_snapshot(*, registry: SourceRegistry) -> SourceSnapshot:
    series = registry.series[IRS_ESTIMATED_TAX_PAYMENT_TIMING_SERIES_ID]
    html = _fetch_text(series.endpoint)
    text = _plain_text(html)
    missing = [marker for marker in IRS_PAYMENT_TIMING_MARKERS if marker not in text]
    if missing:
        raise ValueError(
            "IRS estimated-tax page missing expected markers: "
            + "; ".join(missing)
        )
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    posted_date = _posted_date(html)
    records = [
        {
            "date": "annual_recurring_q1",
            "period": "annual_recurring_q1",
            "income_period_start_month_day": "01-01",
            "income_period_end_month_day": "03-31",
            "estimated_tax_due_month_day": "04-15",
            "estimated_tax_due_year_relation": "same_year",
        },
        {
            "date": "annual_recurring_q2",
            "period": "annual_recurring_q2",
            "income_period_start_month_day": "04-01",
            "income_period_end_month_day": "05-31",
            "estimated_tax_due_month_day": "06-15",
            "estimated_tax_due_year_relation": "same_year",
        },
        {
            "date": "annual_recurring_q3",
            "period": "annual_recurring_q3",
            "income_period_start_month_day": "06-01",
            "income_period_end_month_day": "08-31",
            "estimated_tax_due_month_day": "09-15",
            "estimated_tax_due_year_relation": "same_year",
        },
        {
            "date": "annual_recurring_q4",
            "period": "annual_recurring_q4",
            "income_period_start_month_day": "09-01",
            "income_period_end_month_day": "12-31",
            "estimated_tax_due_month_day": "01-15",
            "estimated_tax_due_year_relation": "following_year",
        },
    ]
    for record in records:
        record.update(
            {
                "source_page_posted_date": posted_date,
                "source_marker_interest_income": "interest, dividends",
                "source_marker_quarterly_estimated_payments_verified": "true",
                "source_marker_due_dates_verified": "true",
                "payment_timing_context_available": "true",
                "source_specific_recipient_mapping_available": "false",
                "state_tax_treatment_available": "false",
                "current_demand_conversion_available": "false",
                "tax_clawback_gate_passed": "false",
                "demand_conversion_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    note = (
        "recipient_leakage_irs_estimated_tax_payment_timing_context_only;"
        f"source_html_sha256={html_sha};"
        f"source_record_count={len(records)};"
        f"source_page_posted_date={posted_date};"
        "interest_income_marker_verified=true;"
        "quarterly_payment_timing_markers_verified=true;"
        "payment_timing_available=true;"
        "state_tax_context_available=false;"
        "source_specific_recipient_mapping_available=false;"
        "current_demand_conversion_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at=posted_date or None,
            snapshot_kind="live_text_context",
            note=note,
        ),
        records=records,
    )


def _treasury_interest_tax_treatment_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[TREASURY_INTEREST_TAX_TREATMENT_SERIES_ID]
    html = _fetch_text(series.endpoint)
    text = _plain_text(html)
    missing = [
        marker for marker in TREASURY_INTEREST_TAX_TREATMENT_MARKERS if marker not in text
    ]
    if missing:
        raise ValueError(
            "TreasuryDirect tax-treatment page missing expected markers: "
            + "; ".join(missing)
        )
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    posted_date = _posted_date(html)
    records = [
        {
            "date": "guidance_page_current",
            "instrument_family": "treasury_marketable_securities",
            "cashflow_component": "treasury_interest",
            "covered_instruments": "bills;notes;bonds;tips;frns",
            "federal_income_tax_treatment": "subject_to_federal_income_tax",
            "state_local_income_tax_treatment": (
                "exempt_from_state_and_local_income_taxes"
            ),
            "source_marker_federal_tax_verified": "true",
            "source_marker_state_local_exemption_verified": "true",
            "source_marker_form_1099_verified": "true",
            "source_specific_tax_treatment_available": "true",
            "source_specific_recipient_mapping_available": "false",
            "state_tax_treatment_available": "treasury_interest_exemption_only",
            "current_demand_conversion_available": "false",
            "tax_clawback_gate_passed": "false",
            "demand_conversion_prior_narrowing_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_ratio_admission_allowed": "false",
            "incidence_output_enabled": "false",
            "welfare_tax_mpc_output_enabled": "false",
        }
    ]
    note = (
        "recipient_leakage_treasury_interest_tax_treatment_context_only;"
        f"source_html_sha256={html_sha};"
        f"source_record_count={len(records)};"
        f"source_page_posted_date={posted_date};"
        "treasury_interest_federal_tax_marker_verified=true;"
        "treasury_interest_state_local_exemption_marker_verified=true;"
        "treasury_interest_form_1099_marker_verified=true;"
        "source_specific_tax_treatment_available=true;"
        "source_specific_recipient_mapping_available=false;"
        "current_demand_conversion_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at=posted_date or None,
            snapshot_kind="live_text_context",
            note=note,
        ),
        records=records,
    )


def _irs_interest_received_tax_topic_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[IRS_INTEREST_RECEIVED_TAX_TOPIC_SERIES_ID]
    html = _fetch_text(series.endpoint)
    text = _plain_text(html)
    missing = [
        marker for marker in IRS_INTEREST_RECEIVED_TAX_TOPIC_MARKERS if marker not in text
    ]
    if missing:
        raise ValueError(
            "IRS Topic 403 page missing expected interest-tax markers: "
            + "; ".join(missing)
        )
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    posted_date = _posted_date(html)
    records = [
        {
            "date": "guidance_page_current",
            "instrument_family": "bank_mmf_cd_corporate_interest",
            "cashflow_component": "deposit_mmf_and_private_interest",
            "covered_instruments": "bank_accounts;money_market_accounts;certificates_of_deposit;corporate_bonds",
            "federal_income_tax_treatment": "generally_taxable_interest_income",
            "state_local_income_tax_treatment": "not_resolved_by_source",
            "source_marker_taxable_interest_verified": "true",
        },
        {
            "date": "guidance_page_current",
            "instrument_family": "treasury_marketable_securities",
            "cashflow_component": "treasury_interest",
            "covered_instruments": "treasury_bills;treasury_notes;treasury_bonds",
            "federal_income_tax_treatment": "subject_to_federal_income_tax",
            "state_local_income_tax_treatment": "exempt_from_state_and_local_income_taxes",
            "source_marker_taxable_interest_verified": "true",
        },
        {
            "date": "guidance_page_current",
            "instrument_family": "us_savings_bonds",
            "cashflow_component": "savings_bond_interest",
            "covered_instruments": "series_ee_bonds;series_i_bonds",
            "federal_income_tax_treatment": "generally_taxable_with_education_exclusion_context",
            "state_local_income_tax_treatment": "not_resolved_by_source",
            "source_marker_taxable_interest_verified": "true",
        },
        {
            "date": "guidance_page_current",
            "instrument_family": "state_local_government_bonds",
            "cashflow_component": "tax_exempt_interest_context",
            "covered_instruments": "state_bonds;local_bonds;district_of_columbia_bonds;us_territory_bonds",
            "federal_income_tax_treatment": "reportable_but_generally_not_federally_taxable",
            "state_local_income_tax_treatment": "not_resolved_by_source",
            "source_marker_taxable_interest_verified": "true",
        },
    ]
    for record in records:
        record.update(
            {
                "source_page_posted_date": posted_date,
                "source_specific_tax_treatment_available": "true",
                "source_specific_recipient_mapping_available": "false",
                "current_demand_conversion_available": "false",
                "tax_clawback_gate_passed": "false",
                "demand_conversion_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    note = (
        "recipient_leakage_irs_interest_received_tax_treatment_context_only;"
        f"source_html_sha256={html_sha};"
        f"source_record_count={len(records)};"
        f"source_page_posted_date={posted_date};"
        "deposit_mmf_cd_corporate_interest_tax_marker_verified=true;"
        "treasury_interest_tax_marker_verified=true;"
        "state_local_bond_tax_exempt_marker_verified=true;"
        "source_specific_tax_treatment_available=true;"
        "source_specific_recipient_mapping_available=false;"
        "current_demand_conversion_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at=posted_date or None,
            snapshot_kind="live_text_context",
            note=note,
        ),
        records=records,
    )


def _irs_publication_550_interest_taxonomy_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[IRS_PUBLICATION_550_INTEREST_TAXONOMY_SERIES_ID]
    html = _fetch_text(series.endpoint)
    text = _plain_text(html)
    missing = [
        marker
        for marker in IRS_PUBLICATION_550_INTEREST_TAXONOMY_MARKERS
        if marker not in text
    ]
    if missing:
        raise ValueError(
            "IRS Publication 550 page missing expected interest-income markers: "
            + "; ".join(missing)
        )
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    publication_year_match = re.search(r"Publication 550 \((?P<year>\d{4})\)", text)
    publication_year = (
        publication_year_match.group("year") if publication_year_match else ""
    )
    records = [
        {
            "date": "guidance_page_current",
            "instrument_family": "bank_accounts_and_private_loans",
            "cashflow_component": "deposit_and_private_interest",
            "covered_instruments": "bank_accounts;loans_made_to_others;other_taxable_interest_sources",
            "federal_income_tax_treatment": "generally_taxable_interest_income",
            "state_local_income_tax_treatment": "not_resolved_by_source",
            "source_marker_taxable_interest_verified": "true",
        },
        {
            "date": "guidance_page_current",
            "instrument_family": "money_market_funds",
            "cashflow_component": "mmf_distribution_tax_context",
            "covered_instruments": "money_market_funds_offered_by_nonbank_financial_institutions",
            "federal_income_tax_treatment": "generally_reported_as_dividends_not_interest",
            "state_local_income_tax_treatment": "not_resolved_by_source",
            "source_marker_mmf_dividend_classification_verified": "true",
        },
        {
            "date": "guidance_page_current",
            "instrument_family": "certificates_of_deposit_and_deferred_interest_accounts",
            "cashflow_component": "deposit_interest",
            "covered_instruments": "certificates_of_deposit;deferred_interest_accounts",
            "federal_income_tax_treatment": "generally_included_when_received_or_entitled_without_substantial_penalty",
            "state_local_income_tax_treatment": "not_resolved_by_source",
            "source_marker_cd_deferred_interest_verified": "true",
        },
        {
            "date": "guidance_page_current",
            "instrument_family": "treasury_marketable_securities",
            "cashflow_component": "treasury_interest",
            "covered_instruments": "treasury_bills;treasury_notes;treasury_bonds",
            "federal_income_tax_treatment": "subject_to_federal_income_tax",
            "state_local_income_tax_treatment": "exempt_from_all_state_and_local_income_taxes",
            "source_marker_treasury_tax_treatment_verified": "true",
        },
        {
            "date": "guidance_page_current",
            "instrument_family": "us_savings_bonds",
            "cashflow_component": "savings_bond_interest",
            "covered_instruments": "series_ee_bonds;series_i_bonds",
            "federal_income_tax_treatment": "generally_federally_taxable_with_specific_exclusion_context",
            "state_local_income_tax_treatment": "not_resolved_by_source",
            "source_marker_savings_bond_context_verified": "true",
        },
        {
            "date": "guidance_page_current",
            "instrument_family": "state_local_government_obligations",
            "cashflow_component": "tax_exempt_interest_context",
            "covered_instruments": "state_obligations;local_government_obligations;municipal_bonds",
            "federal_income_tax_treatment": "generally_not_federally_taxable",
            "state_local_income_tax_treatment": "issuer_specific_not_resolved_by_source",
            "source_marker_state_local_obligation_context_verified": "true",
        },
        {
            "date": "guidance_page_current",
            "instrument_family": "tax_exempt_interest_reporting",
            "cashflow_component": "tax_exempt_interest_reporting_context",
            "covered_instruments": "tax_exempt_interest;tax_exempt_oid_context",
            "federal_income_tax_treatment": "reporting_requirement_does_not_convert_to_taxable_interest",
            "state_local_income_tax_treatment": "not_resolved_by_source",
            "source_marker_information_reporting_verified": "true",
        },
    ]
    for record in records:
        record.update(
            {
                "source_publication_year": publication_year,
                "source_specific_tax_treatment_available": "true",
                "source_specific_recipient_mapping_available": "false",
                "state_tax_rate_mapping_available": "false",
                "current_demand_conversion_available": "false",
                "tax_clawback_gate_passed": "false",
                "demand_conversion_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    note = (
        "recipient_leakage_irs_publication_550_interest_income_taxonomy_context_only;"
        f"source_html_sha256={html_sha};"
        f"source_record_count={len(records)};"
        f"source_publication_year={publication_year};"
        "bank_cd_treasury_mmf_state_local_interest_markers_verified=true;"
        "source_specific_tax_treatment_available=true;"
        "source_specific_recipient_mapping_available=false;"
        "state_tax_rate_mapping_available=false;"
        "current_demand_conversion_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at=publication_year or None,
            snapshot_kind="live_text_context",
            note=note,
        ),
        records=records,
    )


def _irs_1099_int_div_reporting_taxonomy_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[IRS_1099_INT_DIV_REPORTING_TAXONOMY_SERIES_ID]
    int_html = _fetch_text(series.endpoint)
    div_html = _fetch_text(IRS_1099_DIV_REPORTING_URL)
    int_text = _plain_text(int_html)
    div_text = _plain_text(div_html)
    missing_int = [
        marker for marker in IRS_1099_INT_REPORTING_MARKERS if marker not in int_text
    ]
    missing_div = [
        marker for marker in IRS_1099_DIV_REPORTING_MARKERS if marker not in div_text
    ]
    if missing_int:
        raise ValueError(
            "IRS 1099-INT/OID instructions missing expected markers: "
            + "; ".join(missing_int)
        )
    if missing_div:
        raise ValueError(
            "IRS 1099-DIV instructions missing expected markers: "
            + "; ".join(missing_div)
        )
    int_html_sha = hashlib.sha256(int_html.encode("utf-8")).hexdigest()
    div_html_sha = hashlib.sha256(div_html.encode("utf-8")).hexdigest()
    int_posted_date = _posted_date(int_html)
    div_posted_date = _posted_date(div_html)
    records = [
        {
            "date": "guidance_page_current",
            "source_form": "1099-INT",
            "source_instruction_url": series.endpoint,
            "reporting_box": "box_1_interest_income",
            "cashflow_component": "deposit_and_private_interest",
            "covered_instruments": (
                "bank_deposits;credit_union_accounts;certificates_except_us_"
                "treasury;publicly_offered_registered_debt;private_interest"
            ),
            "recipient_reporting_context": (
                "file_for_each_person_paid_reportable_interest_at_or_above_"
                "threshold_or_withheld_tax"
            ),
            "federal_income_tax_reporting_context": (
                "taxable_interest_not_including_us_treasury_box_3_or_tax_"
                "exempt_box_8"
            ),
            "source_specific_reporting_available": "true",
            "source_specific_interest_payer_mapping_available": "reporting_box_context_only",
        },
        {
            "date": "guidance_page_current",
            "source_form": "1099-INT",
            "source_instruction_url": series.endpoint,
            "reporting_box": "box_3_us_savings_bonds_and_treasury_obligations",
            "cashflow_component": "treasury_interest",
            "covered_instruments": "us_savings_bonds;treasury_bills;treasury_notes;treasury_bonds;treasury_obligations",
            "recipient_reporting_context": (
                "file_for_each_person_paid_reportable_treasury_or_savings_bond_"
                "interest_at_or_above_threshold_or_withheld_tax"
            ),
            "federal_income_tax_reporting_context": (
                "treasury_obligations_interest_reported_separately_from_box_1"
            ),
            "source_specific_reporting_available": "true",
            "source_specific_interest_payer_mapping_available": "reporting_box_context_only",
        },
        {
            "date": "guidance_page_current",
            "source_form": "1099-INT",
            "source_instruction_url": series.endpoint,
            "reporting_box": "box_8_tax_exempt_interest",
            "cashflow_component": "tax_exempt_interest_context",
            "covered_instruments": "tax_exempt_interest;private_activity_bond_interest_context",
            "recipient_reporting_context": (
                "file_for_each_person_paid_reportable_tax_exempt_interest_at_"
                "or_above_threshold_or_withheld_tax"
            ),
            "federal_income_tax_reporting_context": (
                "tax_exempt_interest_reported_separately_from_taxable_interest"
            ),
            "source_specific_reporting_available": "true",
            "source_specific_interest_payer_mapping_available": "reporting_box_context_only",
        },
        {
            "date": "guidance_page_current",
            "source_form": "1099-DIV",
            "source_instruction_url": IRS_1099_DIV_REPORTING_URL,
            "reporting_box": "box_1a_total_ordinary_dividends",
            "cashflow_component": "money_market_fund_distribution_tax_context",
            "covered_instruments": "money_market_funds;mutual_fund_distributions;ordinary_dividends",
            "recipient_reporting_context": (
                "file_for_each_person_paid_reportable_dividends_or_"
                "distributions_at_or_above_threshold"
            ),
            "federal_income_tax_reporting_context": (
                "money_market_fund_payments_reported_as_ordinary_dividends"
            ),
            "source_specific_reporting_available": "true",
            "source_specific_interest_payer_mapping_available": "reporting_box_context_only",
        },
        {
            "date": "guidance_page_current",
            "source_form": "1099-DIV",
            "source_instruction_url": IRS_1099_DIV_REPORTING_URL,
            "reporting_box": "box_12_exempt_interest_dividends",
            "cashflow_component": "exempt_interest_dividend_context",
            "covered_instruments": "mutual_fund_or_ric_exempt_interest_dividends",
            "recipient_reporting_context": (
                "file_for_each_person_paid_reportable_exempt_interest_dividends"
            ),
            "federal_income_tax_reporting_context": (
                "exempt_interest_dividends_reported_separately_from_ordinary_dividends"
            ),
            "source_specific_reporting_available": "true",
            "source_specific_interest_payer_mapping_available": "reporting_box_context_only",
        },
        {
            "date": "guidance_page_current",
            "source_form": "1099-INT",
            "source_instruction_url": series.endpoint,
            "reporting_box": "reporting_exception_exempt_recipients",
            "cashflow_component": "tax_deferred_or_exempt_recipient_constraint",
            "covered_instruments": (
                "reportable_interest;original_issue_discount;tax_exempt_interest"
            ),
            "recipient_reporting_context": (
                "form_1099_int_generally_not_required_for_specified_exempt_"
                "recipients_including_corporations_tax_exempt_organizations_"
                "iras_msas_hsas_us_agencies_states_dealers_nominees_"
                "custodians_and_brokers"
            ),
            "federal_income_tax_reporting_context": (
                "reportability_constraint_for_tax_wrapper_not_tax_incidence_or_"
                "current_demand_conversion"
            ),
            "source_specific_reporting_available": "true",
            "source_specific_interest_payer_mapping_available": "reporting_exception_context_only",
            "recipient_tax_account_constraint_context_available": "true",
        },
        {
            "date": "guidance_page_current",
            "source_form": "1099-INT",
            "source_instruction_url": series.endpoint,
            "reporting_box": "reporting_exclusion_foreign_payee_or_foreign_source",
            "cashflow_component": "foreign_payee_reporting_exclusion_constraint",
            "covered_instruments": (
                "foreign_source_interest;portfolio_interest;international_"
                "organization_interest;foreign_beneficial_owner_payments"
            ),
            "recipient_reporting_context": (
                "form_1099_int_interest_excluded_from_reporting_for_foreign_"
                "beneficial_owner_or_foreign_payee_and_selected_non_us_"
                "source_or_non_us_middleman_payments"
            ),
            "federal_income_tax_reporting_context": (
                "foreign_reportability_constraint_for_tax_and_foreign_leakage_"
                "review_not_beneficial_owner_mapping"
            ),
            "source_specific_reporting_available": "true",
            "source_specific_interest_payer_mapping_available": "reporting_exclusion_context_only",
            "recipient_tax_account_constraint_context_available": "true",
        },
    ]
    for record in records:
        record.update(
            {
                "int_instruction_posted_date": int_posted_date,
                "div_instruction_posted_date": div_posted_date,
                "source_specific_recipient_mapping_available": "false",
                "source_specific_tax_account_mapping_available": (
                    record.get("recipient_tax_account_constraint_context_available")
                    or "false"
                ),
                "tax_incidence_available": "false",
                "current_demand_conversion_available": "false",
                "tax_clawback_gate_passed": "false",
                "demand_conversion_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    records_hash = _records_sha256(records)
    release_at = ";".join(
        part
        for part in (
            f"1099_int={int_posted_date}" if int_posted_date else "",
            f"1099_div={div_posted_date}" if div_posted_date else "",
        )
        if part
    )
    note = (
        "recipient_leakage_irs_1099_int_div_reporting_taxonomy_context_only;"
        f"source_1099_int_url={series.endpoint};"
        f"source_1099_div_url={IRS_1099_DIV_REPORTING_URL};"
        f"source_1099_int_html_sha256={int_html_sha};"
        f"source_1099_div_html_sha256={div_html_sha};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "deposit_private_interest_treasury_tax_exempt_mmf_dividend_reporting_"
        "and_reportability_constraint_markers_verified=true;"
        "source_specific_reporting_available=true;"
        "tax_deferred_exempt_and_foreign_payee_reportability_constraints_"
        "available=true;"
        "source_specific_recipient_mapping_available=false;"
        "source_specific_tax_account_mapping_available=false;"
        "tax_incidence_available=false;"
        "current_demand_conversion_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at=release_at or None,
            snapshot_kind="live_text_context",
            note=note,
        ),
        records=records,
    )


def _fta_state_income_tax_rates_snapshot(*, registry: SourceRegistry) -> SourceSnapshot:
    series = registry.series[FTA_STATE_INCOME_TAX_RATES_SERIES_ID]
    html = _fetch_public_text(series.endpoint)
    text = _plain_text(html)
    missing = [
        marker for marker in FTA_STATE_INCOME_TAX_RATE_MARKERS if marker not in text
    ]
    if missing:
        raise ValueError(
            "FTA state income-tax-rate page missing expected markers: "
            + "; ".join(missing)
        )
    table_match = re.search(
        r'(<table id="tablepress-60".*?</table>)',
        html,
        flags=re.DOTALL,
    )
    if table_match is None:
        raise ValueError("FTA state income-tax-rate page missing tablepress-60 table")
    source_rows = _extract_fta_state_income_tax_rows(table_match.group(1))
    if len(source_rows) != 51:
        raise ValueError(
            "FTA state income-tax-rate table expected 51 rows, found "
            f"{len(source_rows)}"
        )
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    records: list[dict[str, str]] = []
    for source_row in source_rows:
        raw_state_name = source_row[0]
        state_name = _clean_state_name(raw_state_name)
        postal_code = STATE_NAME_TO_POSTAL.get(state_name, "")
        if not postal_code:
            raise ValueError(f"FTA state income-tax-rate row has unknown state: {raw_state_name}")
        low_rate = source_row[2] if len(source_row) > 2 else ""
        high_rate = source_row[3] if len(source_row) > 3 else ""
        no_state_income_tax = "No State Income Tax" in " ".join(source_row)
        records.append(
            {
                "date": "2024-01-01",
                "tax_year": "2024",
                "as_of_date": "2025-01-01",
                "state_name": state_name,
                "state_postal_code": postal_code,
                "source_state_label": raw_state_name,
                "rate_change_code": source_row[1] if len(source_row) > 1 else "",
                "tax_rate_low_percent": "" if no_state_income_tax else low_rate,
                "tax_rate_high_percent": "" if no_state_income_tax else high_rate,
                "number_of_brackets": source_row[4] if len(source_row) > 4 else "",
                "lowest_income_bracket": source_row[5] if len(source_row) > 5 else "",
                "highest_income_bracket": source_row[6] if len(source_row) > 6 else "",
                "personal_exemption_single": (
                    source_row[7] if len(source_row) > 7 else ""
                ),
                "personal_exemption_married": (
                    source_row[8] if len(source_row) > 8 else ""
                ),
                "personal_exemption_dependents": (
                    source_row[9] if len(source_row) > 9 else ""
                ),
                "standard_deduction_single": (
                    source_row[10] if len(source_row) > 10 else ""
                ),
                "standard_deduction_married": (
                    source_row[11] if len(source_row) > 11 else ""
                ),
                "federal_income_tax_deductible": (
                    source_row[12] if len(source_row) > 12 else ""
                ),
                "no_state_individual_income_tax": str(no_state_income_tax).lower(),
                "state_tax_rate_mapping_available": "true",
                "source_specific_recipient_mapping_available": "false",
                "taxable_tax_deferred_source_mapping_available": "false",
                "current_demand_conversion_available": "false",
                "tax_clawback_gate_passed": "false",
                "demand_conversion_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    records_hash = _records_sha256(records)
    note = (
        "recipient_leakage_fta_state_individual_income_tax_rate_context_only;"
        f"source_html_sha256={html_sha};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "first_observation_date=2024-01-01;"
        "latest_observation_date=2024-01-01;"
        "source_as_of_date=2025-01-01;"
        "state_tax_rate_mapping_available=true;"
        "source_specific_recipient_mapping_available=false;"
        "taxable_tax_deferred_source_mapping_available=false;"
        "current_demand_conversion_available=false;"
        "tax_clawback_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at="2025-01-01",
            snapshot_kind="live_html_table_context",
            note=note,
        ),
        records=records,
    )


def _tic_custody_limitation_snapshot(*, registry: SourceRegistry) -> SourceSnapshot:
    series = registry.series[TIC_CUSTODY_LIMITATION_SERIES_ID]
    html = _fetch_text(series.endpoint)
    text = _plain_text(html)
    missing = [marker for marker in TIC_CUSTODY_LIMITATION_MARKERS if marker not in text]
    if missing:
        raise ValueError(
            "Treasury TIC FAQ page missing expected custody markers: "
            + "; ".join(missing)
        )
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    posted_date = _posted_date(html)
    records = [
        {
            "date": "guidance_page_current",
            "cashflow_component": "foreign_treasury_holder_leakage",
            "evidence_role": "foreign_holder_beneficial_owner_limitation_context",
            "tic_dataset_scope": "major_foreign_holders_and_slt_custodial_context",
            "custodial_data_basis_verified": "true",
            "beneficial_owner_complete_accuracy_available": "false",
            "third_country_custody_limitation_verified": "true",
            "portfolio_manager_attribution_limitation_verified": "true",
            "holder_allocation_promotion_allowed": "false",
            "recycling_to_current_us_demand_available": "false",
            "foreign_leakage_gate_passed": "false",
            "demand_conversion_prior_narrowing_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_ratio_admission_allowed": "false",
            "incidence_output_enabled": "false",
            "welfare_tax_mpc_output_enabled": "false",
        }
    ]
    note = (
        "recipient_leakage_tic_foreign_holder_custody_limitation_context_only;"
        f"source_html_sha256={html_sha};"
        f"source_record_count={len(records)};"
        f"source_page_posted_date={posted_date};"
        "custodial_data_basis_verified=true;"
        "beneficial_owner_complete_accuracy_available=false;"
        "third_country_custody_limitation_verified=true;"
        "portfolio_manager_attribution_limitation_verified=true;"
        "holder_allocation_promotion_allowed=false;"
        "recycling_to_current_us_demand_available=false;"
        "foreign_leakage_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at=posted_date or None,
            snapshot_kind="live_text_context",
            note=note,
        ),
        records=records,
    )


def _fed_cross_border_treasury_basis_trade_records(
    html: str,
    accessible_html: str,
) -> list[dict[str, str]]:
    text = _plain_text(html)
    accessible_text = _plain_text(accessible_html)
    missing = [
        marker
        for marker in FED_CROSS_BORDER_TREASURY_BASIS_TRADE_MARKERS
        if marker not in text
    ]
    missing_accessible = [
        marker
        for marker in FED_CROSS_BORDER_ACCESSIBLE_MARKERS
        if marker not in accessible_text
    ]
    if missing or missing_accessible:
        raise ValueError(
            "Fed Cross-Border Trail source missing expected markers: "
            + "; ".join([*missing, *missing_accessible])
        )

    common = {
        "cashflow_component": "foreign_treasury_holder_leakage",
        "source_artifact": FED_CROSS_BORDER_TREASURY_BASIS_TRADE_SERIES_ID,
        "source_inputs": (
            "TIC SLT;Form PF;Form ADV;FICC sponsored DVP;Financial Accounts Z1;"
            "Enhanced Financial Accounts"
        ),
        "beneficial_owner_scope": "cayman_hedge_fund_treasury_subcase_only",
        "confidential_dependency": "form_pf_fund_level_data_not_public",
        "public_proxy_available": "true",
        "domestic_demand_timing_bridge": "false",
        "recycling_to_current_us_demand": "false",
        "holder_allocation_enabled": "false",
        "promotion_gate_passed": "false",
        "prior_narrowing_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
    }
    return [
        {
            **common,
            "date": "2024-12-31",
            "review_dimension": "tic_undercount_estimate",
            "metric": "tic_undercount_estimate_end_2024",
            "metric_value": "1400",
            "metric_units": "billions_of_dollars_approximate",
            "method_bridge": (
                "Fed note estimates Cayman-domiciled hedge-fund Treasury "
                "holdings missing from TIC by comparing Form PF and TIC "
                "measures."
            ),
            "claim_boundary": (
                "method_bridge_only_not_beneficial_owner_allocation_or_demand_timing"
            ),
        },
        {
            **common,
            "date": "2024-12-31",
            "review_dimension": "cayman_holdings_estimate",
            "metric": "cayman_hedge_fund_treasury_holdings_end_2024",
            "metric_value": "1850",
            "metric_units": "billions_of_dollars_approximate",
            "method_bridge": (
                "Fed note reports Form PF-based Cayman-domiciled hedge-fund "
                "Treasury holdings estimate."
            ),
            "claim_boundary": (
                "method_bridge_only_not_beneficial_owner_allocation_or_demand_timing"
            ),
        },
        {
            **common,
            "date": "2024-12-31",
            "review_dimension": "public_proxy",
            "metric": "public_z1_efa_proxy_available",
            "metric_value": "true",
            "metric_units": "boolean",
            "method_bridge": (
                "Appendix A describes a public proxy: all hedge-fund Treasury "
                "holdings in Enhanced Financial Accounts minus U.S.-domiciled "
                "hedge-fund holdings in Financial Accounts."
            ),
            "claim_boundary": (
                "public_proxy_method_bridge_only_confidential_form_pf_remains_more_"
                "accurate"
            ),
        },
        {
            **common,
            "date": "2024-12-31",
            "review_dimension": "ultimate_nationality_caveat",
            "metric": "ultimate_nationality_caveat_available",
            "metric_value": "true",
            "metric_units": "boolean",
            "method_bridge": (
                "Fed note cautions that Cayman hedge-fund Treasury holdings "
                "would largely be attributed to the United States on an ultimate-"
                "nationality basis because U.S. nationals are likely major "
                "beneficial owners of fund shares."
            ),
            "claim_boundary": (
                "blocks_simple_foreign_leakage_inference_from_cayman_residency"
            ),
        },
        {
            **common,
            "date": "2024-12-31",
            "review_dimension": "accessible_figure_context",
            "metric": "accessible_data_context_available",
            "metric_value": "true",
            "metric_units": "boolean",
            "method_bridge": (
                "Fed accessible-data page summarizes figures for Cayman "
                "holdings, adjusted TIC, household balance-sheet effects, "
                "issuance absorption, and Z.1/EFA proxy comparison."
            ),
            "claim_boundary": (
                "accessible_figure_context_only_not_recycling_or_current_demand"
            ),
        },
    ]


def _fed_cross_border_treasury_basis_trade_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[FED_CROSS_BORDER_TREASURY_BASIS_TRADE_SERIES_ID]
    source_html = _fetch_text(series.endpoint)
    accessible_url = urllib.parse.urljoin(
        series.endpoint,
        "the-cross-border-trail-of-the-treasury-basis-trade-accessible-20251015.htm",
    )
    accessible_html = _fetch_text(accessible_url)
    records = _fed_cross_border_treasury_basis_trade_records(
        source_html,
        accessible_html,
    )
    source_sha = hashlib.sha256(source_html.encode("utf-8")).hexdigest()
    accessible_sha = hashlib.sha256(accessible_html.encode("utf-8")).hexdigest()
    posted_date = _posted_date(source_html) or _posted_date(accessible_html)
    note = (
        "foreign_treasury_leakage_cross_border_basis_trade_method_bridge_context_only;"
        f"source_html_sha256={source_sha};"
        f"accessible_html_sha256={accessible_sha};"
        f"source_record_count={len(records)};"
        f"source_page_posted_date={posted_date};"
        "tic_undercount_estimate_end_2024_about_1400_bil=true;"
        "cayman_holdings_estimate_end_2024_about_1850_bil=true;"
        "public_z1_efa_proxy_available=true;"
        "confidential_form_pf_dependency=true;"
        "ultimate_nationality_caveat_available=true;"
        "domestic_demand_timing_bridge=false;"
        "recycling_to_current_us_demand=false;"
        "holder_allocation_enabled=false;"
        "foreign_leakage_gate_passed=false;"
        "demand_conversion_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at=posted_date or None,
            snapshot_kind="live_html_and_accessible_context",
            note=note,
        ),
        records=records,
    )


def materialize(
    *,
    config: Path,
    snapshot_bundle: Path,
    output: Path,
    irs_soi_csv: Path = IRS_SOI_DEFAULT_CSV,
    irs_soi_provenance: Path = IRS_SOI_DEFAULT_PROVENANCE,
    irs_ira_xlsx: Path = IRS_IRA_DEFAULT_XLSX,
    irs_ira_csv: Path = IRS_IRA_DEFAULT_CSV,
    irs_ira_provenance: Path = IRS_IRA_DEFAULT_PROVENANCE,
    irs_average_tax_rate_xlsx: Path = IRS_AVERAGE_TAX_RATE_DEFAULT_XLSX,
    irs_average_tax_rate_csv: Path = IRS_AVERAGE_TAX_RATE_DEFAULT_CSV,
    irs_average_tax_rate_provenance: Path = (
        IRS_AVERAGE_TAX_RATE_DEFAULT_PROVENANCE
    ),
    irs_state_source_csv: Path = IRS_STATE_INTEREST_DEFAULT_SOURCE_CSV,
    irs_state_csv: Path = IRS_STATE_INTEREST_DEFAULT_CSV,
    irs_state_provenance: Path = IRS_STATE_INTEREST_DEFAULT_PROVENANCE,
    fed_scf_summary_extract_zip: Path = FED_SCF_SUMMARY_EXTRACT_DEFAULT,
) -> Path:
    registry = SourceRegistry.from_path(config)
    adapter = FredAdapter(registry)
    dfa_adapter = FedDfaAdapter(registry)
    existing = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in existing}
    for series_id, context_status in RECIPIENT_LEAKAGE_FRED_SERIES.items():
        by_series[series_id] = _annotated_leakage_context_snapshot(
            adapter.pull_series(series_id),
            context_status=context_status,
        )
    irs_snapshot = _irs_soi_snapshot(
        registry=registry,
        csv_path=irs_soi_csv,
        provenance_path=irs_soi_provenance,
    )
    if irs_snapshot is not None:
        by_series[irs_snapshot.metadata.series_id] = irs_snapshot
    _write_ira_artifacts_if_needed(
        registry=registry,
        xlsx_path=irs_ira_xlsx,
        csv_path=irs_ira_csv,
        provenance_path=irs_ira_provenance,
    )
    irs_ira_snapshot = _irs_ira_snapshot(
        registry=registry,
        csv_path=irs_ira_csv,
        provenance_path=irs_ira_provenance,
    )
    if irs_ira_snapshot is not None:
        by_series[irs_ira_snapshot.metadata.series_id] = irs_ira_snapshot
    _write_average_tax_rate_artifacts_if_needed(
        registry=registry,
        xlsx_path=irs_average_tax_rate_xlsx,
        csv_path=irs_average_tax_rate_csv,
        provenance_path=irs_average_tax_rate_provenance,
    )
    irs_average_tax_rate_snapshot = _irs_average_tax_rate_snapshot(
        registry=registry,
        csv_path=irs_average_tax_rate_csv,
        provenance_path=irs_average_tax_rate_provenance,
    )
    if irs_average_tax_rate_snapshot is not None:
        by_series[irs_average_tax_rate_snapshot.metadata.series_id] = (
            irs_average_tax_rate_snapshot
        )
    _write_state_interest_artifacts_if_needed(
        registry=registry,
        source_csv_path=irs_state_source_csv,
        converted_csv_path=irs_state_csv,
        provenance_path=irs_state_provenance,
    )
    irs_state_snapshot = _irs_state_interest_snapshot(
        registry=registry,
        csv_path=irs_state_csv,
        provenance_path=irs_state_provenance,
    )
    if irs_state_snapshot is not None:
        by_series[irs_state_snapshot.metadata.series_id] = irs_state_snapshot
    by_series[FED_DFA_ACCOUNT_TYPE_SERIES_ID] = (
        dfa_adapter.pull_distributional_exposure(FED_DFA_ACCOUNT_TYPE_SERIES_ID)
    )
    by_series[FED_SCF_SAFE_ASSET_ACCOUNT_TAX_SERIES_ID] = (
        _fed_scf_safe_asset_account_tax_snapshot(
            registry=registry,
            source_zip=fed_scf_summary_extract_zip,
        )
    )
    by_series[IRS_ESTIMATED_TAX_PAYMENT_TIMING_SERIES_ID] = (
        _irs_payment_timing_snapshot(registry=registry)
    )
    by_series[TREASURY_INTEREST_TAX_TREATMENT_SERIES_ID] = (
        _treasury_interest_tax_treatment_snapshot(registry=registry)
    )
    by_series[IRS_INTEREST_RECEIVED_TAX_TOPIC_SERIES_ID] = (
        _irs_interest_received_tax_topic_snapshot(registry=registry)
    )
    by_series[IRS_PUBLICATION_550_INTEREST_TAXONOMY_SERIES_ID] = (
        _irs_publication_550_interest_taxonomy_snapshot(registry=registry)
    )
    by_series[IRS_1099_INT_DIV_REPORTING_TAXONOMY_SERIES_ID] = (
        _irs_1099_int_div_reporting_taxonomy_snapshot(registry=registry)
    )
    by_series[FTA_STATE_INCOME_TAX_RATES_SERIES_ID] = (
        _fta_state_income_tax_rates_snapshot(registry=registry)
    )
    by_series[TIC_CUSTODY_LIMITATION_SERIES_ID] = (
        _tic_custody_limitation_snapshot(registry=registry)
    )
    by_series[FED_CROSS_BORDER_TREASURY_BASIS_TRADE_SERIES_ID] = (
        _fed_cross_border_treasury_basis_trade_snapshot(registry=registry)
    )
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
    parser.add_argument(
        "--output", type=Path, default=Path("data/raw/ratewall_snapshot.json")
    )
    parser.add_argument("--irs-soi-csv", type=Path, default=IRS_SOI_DEFAULT_CSV)
    parser.add_argument(
        "--irs-soi-provenance",
        type=Path,
        default=IRS_SOI_DEFAULT_PROVENANCE,
    )
    parser.add_argument("--irs-ira-xlsx", type=Path, default=IRS_IRA_DEFAULT_XLSX)
    parser.add_argument("--irs-ira-csv", type=Path, default=IRS_IRA_DEFAULT_CSV)
    parser.add_argument(
        "--irs-ira-provenance",
        type=Path,
        default=IRS_IRA_DEFAULT_PROVENANCE,
    )
    parser.add_argument(
        "--irs-average-tax-rate-xlsx",
        type=Path,
        default=IRS_AVERAGE_TAX_RATE_DEFAULT_XLSX,
    )
    parser.add_argument(
        "--irs-average-tax-rate-csv",
        type=Path,
        default=IRS_AVERAGE_TAX_RATE_DEFAULT_CSV,
    )
    parser.add_argument(
        "--irs-average-tax-rate-provenance",
        type=Path,
        default=IRS_AVERAGE_TAX_RATE_DEFAULT_PROVENANCE,
    )
    parser.add_argument(
        "--irs-state-source-csv",
        type=Path,
        default=IRS_STATE_INTEREST_DEFAULT_SOURCE_CSV,
    )
    parser.add_argument(
        "--irs-state-csv",
        type=Path,
        default=IRS_STATE_INTEREST_DEFAULT_CSV,
    )
    parser.add_argument(
        "--irs-state-provenance",
        type=Path,
        default=IRS_STATE_INTEREST_DEFAULT_PROVENANCE,
    )
    parser.add_argument(
        "--fed-scf-summary-extract-zip",
        type=Path,
        default=FED_SCF_SUMMARY_EXTRACT_DEFAULT,
    )
    args = parser.parse_args()
    output = materialize(
        config=args.config,
        snapshot_bundle=args.snapshot_bundle,
        output=args.output,
        irs_soi_csv=args.irs_soi_csv,
        irs_soi_provenance=args.irs_soi_provenance,
        irs_ira_xlsx=args.irs_ira_xlsx,
        irs_ira_csv=args.irs_ira_csv,
        irs_ira_provenance=args.irs_ira_provenance,
        irs_average_tax_rate_xlsx=args.irs_average_tax_rate_xlsx,
        irs_average_tax_rate_csv=args.irs_average_tax_rate_csv,
        irs_average_tax_rate_provenance=args.irs_average_tax_rate_provenance,
        irs_state_source_csv=args.irs_state_source_csv,
        irs_state_csv=args.irs_state_csv,
        irs_state_provenance=args.irs_state_provenance,
        fed_scf_summary_extract_zip=args.fed_scf_summary_extract_zip,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
