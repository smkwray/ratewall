"""Materialize FDIC bank income/dividend retention context.

The panel is a source-backed aggregate route context only. It can show how
bank net income is split between cash dividends and retained earnings, but it
does not identify IORB-specific retained margin or current-demand timing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.parse
import urllib.request
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


API_URL = "https://api.fdic.gov/banks/financials"
DEFAULT_OUTPUT = Path(
    "data/raw/fdic_bank_margin_distribution/fdic_bank_margin_distribution_panel.csv"
)
DEFAULT_MANIFEST = Path(
    "data/raw/fdic_bank_margin_distribution/fdic_bank_margin_distribution_manifest.json"
)
FIELDS = [
    "REPDTE",
    "CERT",
    "NETINCQ",
    "EQCDIVQ",
    "EQCDIVC",
    "EQCDIVP",
    "EQCDIV",
]
OUTPUT_FIELDS = [
    "quarter",
    "report_date",
    "fdic_source_rows",
    "fdic_reporting_institutions",
    "net_income_q_mil",
    "cash_dividends_q_mil",
    "common_cash_dividends_q_mil",
    "preferred_cash_dividends_q_mil",
    "retained_earnings_proxy_mil",
    "retention_share_proxy",
    "dividend_payout_share_proxy",
    "source_url",
    "source_fields",
    "source_status",
    "current_demand_bridge_status",
    "missing_fields_for_admission",
]


def _quarter_dates(start_year: int, end_year: int) -> list[str]:
    dates: list[str] = []
    for year in range(start_year, end_year + 1):
        for suffix in ("0331", "0630", "0930", "1231"):
            dates.append(f"{year}{suffix}")
    return dates


def _quarter_label(repdate: str) -> str:
    month = repdate[4:6]
    quarter = {"03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4"}[month]
    return f"{repdate[:4]}{quarter}"


def _iso_date(repdate: str) -> str:
    return f"{repdate[:4]}-{repdate[4:6]}-{repdate[6:8]}"


def _decimal(value: Any) -> Decimal:
    if value in {"", None}:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal("0")


def _format_decimal(value: Decimal, places: str = "0.000001") -> str:
    return str(value.quantize(Decimal(places))).rstrip("0").rstrip(".")


def _fetch_quarter(repdate: str) -> tuple[list[dict[str, Any]], str]:
    params = {
        "filters": f"REPDTE:{repdate}",
        "fields": ",".join(FIELDS),
        "limit": "10000",
        "format": "json",
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ratewall research source-admission shanewray@example.invalid"
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return [item.get("data", {}) for item in payload.get("data", [])], url


def _build_rows(quarter_records: Iterable[tuple[str, list[dict[str, Any]], str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for repdate, records, source_url in quarter_records:
        if not records:
            continue
        net_income_q_thous = sum(_decimal(row.get("NETINCQ")) for row in records)
        cash_div_q_thous = sum(_decimal(row.get("EQCDIVQ")) for row in records)
        common_cash_div_ytd_thous = sum(_decimal(row.get("EQCDIVC")) for row in records)
        preferred_cash_div_ytd_thous = sum(_decimal(row.get("EQCDIVP")) for row in records)
        retained_q_thous = net_income_q_thous - cash_div_q_thous
        retention_share = (
            retained_q_thous / net_income_q_thous
            if net_income_q_thous != 0
            else Decimal("0")
        )
        payout_share = (
            cash_div_q_thous / net_income_q_thous
            if net_income_q_thous != 0
            else Decimal("0")
        )
        rows.append(
            {
                "quarter": _quarter_label(repdate),
                "report_date": _iso_date(repdate),
                "fdic_source_rows": str(len(records)),
                "fdic_reporting_institutions": str(
                    len({str(row.get("CERT", "")) for row in records if row.get("CERT")})
                ),
                "net_income_q_mil": _format_decimal(net_income_q_thous / Decimal("1000")),
                "cash_dividends_q_mil": _format_decimal(cash_div_q_thous / Decimal("1000")),
                "common_cash_dividends_q_mil": _format_decimal(
                    common_cash_div_ytd_thous / Decimal("1000")
                ),
                "preferred_cash_dividends_q_mil": _format_decimal(
                    preferred_cash_div_ytd_thous / Decimal("1000")
                ),
                "retained_earnings_proxy_mil": _format_decimal(
                    retained_q_thous / Decimal("1000")
                ),
                "retention_share_proxy": _format_decimal(retention_share),
                "dividend_payout_share_proxy": _format_decimal(payout_share),
                "source_url": source_url,
                "source_fields": "REPDTE;CERT;NETINCQ;EQCDIVQ;EQCDIVC;EQCDIVP;EQCDIV",
                "source_status": "fdic_financials_source_backed_aggregate_distribution_route_context",
                "current_demand_bridge_status": (
                    "blocked_no_iorb_specific_retention_or_depositor_borrower_current_demand_timing"
                ),
                "missing_fields_for_admission": (
                    "iorb_specific_retention_share;depositor_or_borrower_cashflow_response;"
                    "current_demand_timing;nonadditivity_check"
                ),
            }
        )
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2021)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--start-quarter", default="2021Q4")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    quarter_records = []
    for repdate in _quarter_dates(args.start_year, args.end_year):
        if _quarter_label(repdate) < args.start_quarter:
            continue
        records, source_url = _fetch_quarter(repdate)
        quarter_records.append((repdate, records, source_url))
    rows = _build_rows(quarter_records)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "source": "FDIC BankFind Suite Financials API",
        "source_url": API_URL,
        "source_docs": "https://api.fdic.gov/banks/docs/",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "output_path": str(args.output),
        "output_sha256": _sha256(args.output),
        "row_count": len(rows),
        "first_quarter": rows[0]["quarter"] if rows else "",
        "latest_quarter": rows[-1]["quarter"] if rows else "",
        "claim_boundary": (
            "aggregate_bank_income_dividend_retention_route_context_not_current_demand_bridge"
        ),
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
