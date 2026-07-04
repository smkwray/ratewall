"""SEC Form N-MFP data-set adapter."""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from zipfile import ZipFile

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


SEC_NMFP_PAGE = (
    "https://www.sec.gov/data-research/sec-markets-data/dera-form-n-mfp-data-sets"
)
RAW_DIR = Path("data/raw/sec_nmfp")
SEC_USER_AGENT = "RateWall research prototype ratewall@example.com"
HISTORICAL_ZIP_LIMIT = 6
SEC_NMFP_SOURCE_RATE_LIMIT = "bounded_to_6_monthly_zip_files_per_live_snapshot"


class SecNmfpAdapter:
    def __init__(
        self,
        registry: SourceRegistry,
        *,
        opener: Callable = urlopen,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.registry = registry
        self.opener = opener
        self.clock = clock

    def pull_treasury_holdings(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "sec_nmfp":
            raise ValueError(f"{series_id} is registered to {spec.source}, not sec_nmfp")
        source_urls = _nmfp_zip_urls(
            self.opener,
            spec.endpoint,
            limit=HISTORICAL_ZIP_LIMIT,
        )
        raw_paths = [_download_zip(self.opener, source_url) for source_url in source_urls]
        records = []
        for period_index, raw_path in enumerate(raw_paths):
            records.extend(
                _aggregate_nmfp_treasury_rows(
                    raw_path,
                    period_role="latest" if period_index == 0 else "historical",
                )
            )
        metadata = RetrievalMetadata(
            source_id="sec_nmfp",
            series_id=series_id,
            source_url=source_urls[0],
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=_latest_report_date(records),
            note=(
                f"raw_zips={';'.join(str(path) for path in raw_paths)};"
                f"historical_zip_count={len(raw_paths)};"
                f"historical_zip_limit={HISTORICAL_ZIP_LIMIT};"
                f"source_rate_limit={SEC_NMFP_SOURCE_RATE_LIMIT};"
                "history_scope=latest_6_official_monthly_zip_files;"
                "source_size_rationale=bounded_live_snapshot_avoids_unbounded_sec_bulk_downloads"
            ),
        )
        return SourceSnapshot(metadata=metadata, records=records)


def _nmfp_zip_urls(opener: Callable, endpoint: str, *, limit: int) -> list[str]:
    request = Request(
        endpoint or SEC_NMFP_PAGE,
        headers={"User-Agent": SEC_USER_AGENT},
    )
    with open_with_timeout(opener, request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    matches = re.findall(r'href="(?P<href>[^"]+_nmfp\.zip)"', html, re.IGNORECASE)
    if not matches:
        raise ValueError("SEC Form N-MFP page did not expose a monthly zip link")
    return [urljoin(endpoint or SEC_NMFP_PAGE, href) for href in matches[:limit]]


def _download_zip(opener: Callable, source_url: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    filename = source_url.rstrip("/").split("/")[-1]
    path = RAW_DIR / filename
    request = Request(
        source_url,
        headers={"User-Agent": SEC_USER_AGENT},
    )
    with open_with_timeout(opener, request, timeout=120) as response:
        data = response.read()
    path.write_bytes(data)
    return path


def _aggregate_nmfp_treasury_rows(
    path: Path,
    *,
    period_role: str,
) -> list[dict[str, str]]:
    with ZipFile(path) as archive:
        submissions = _submission_context(archive)
        direct_rows = _direct_treasury_rows(archive, submissions)
        collateral_rows = _treasury_collateral_rows(archive, submissions)
    records = _aggregate_records(direct_rows, "direct_security", period_role)
    records.extend(_aggregate_records(collateral_rows, "repo_collateral", period_role))
    records.extend(_top_cusip_records(direct_rows, "direct_security", period_role))
    records.extend(_top_cusip_records(collateral_rows, "repo_collateral", period_role))
    return records


def _submission_context(archive: ZipFile) -> dict[str, dict[str, str]]:
    with archive.open("NMFP_SUBMISSION.tsv") as handle:
        reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"), delimiter="\t")
        return {
            row["ACCESSION_NUMBER"]: {
                "report_date": _sec_date(row.get("REPORTDATE", "")),
                "series_name": row.get("SERIES_NAME") or row.get("NAMEOFSERIES", ""),
                "series_id": row.get("SERIESID", ""),
            }
            for row in reader
        }


def _direct_treasury_rows(
    archive: ZipFile, submissions: dict[str, dict[str, str]]
) -> list[dict[str, str | Decimal]]:
    rows: list[dict[str, str | Decimal]] = []
    with archive.open("NMFP_SCHPORTFOLIOSECURITIES.tsv") as handle:
        reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"), delimiter="\t")
        for row in reader:
            if not _is_treasury_security(row):
                continue
            accession = row.get("ACCESSION_NUMBER", "")
            context = submissions.get(accession, {})
            value = _decimal(row.get("INCLUDINGVALUEOFANYSPONSORSUPP"))
            rows.append(
                {
                    "report_date": context.get("report_date", ""),
                    "series_name": context.get("series_name", ""),
                    "series_id": context.get("series_id", ""),
                    "cusip": row.get("CUSIP_NUMBER", ""),
                    "issuer": row.get("NAMEOFISSUER", ""),
                    "title": row.get("TITLEOFISSUER", ""),
                    "investment_category": row.get("INVESTMENTCATEGORY", ""),
                    "maturity_date": _sec_date(
                        row.get("FINALLEGALINVESTMENTMATURITYDA", "")
                    ),
                    "security_bucket": _treasury_bucket(row),
                    "value": value,
                }
            )
    return rows


def _treasury_collateral_rows(
    archive: ZipFile, submissions: dict[str, dict[str, str]]
) -> list[dict[str, str | Decimal]]:
    rows: list[dict[str, str | Decimal]] = []
    with archive.open("NMFP_COLLATERALISSUERS.tsv") as handle:
        reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"), delimiter="\t")
        for row in reader:
            if not _is_treasury_collateral(row):
                continue
            accession = row.get("ACCESSION_NUMBER", "")
            context = submissions.get(accession, {})
            value = _decimal(row.get("VALUEOFCOLLATERALTOTHENEARESTC"))
            rows.append(
                {
                    "report_date": context.get("report_date", ""),
                    "series_name": context.get("series_name", ""),
                    "series_id": context.get("series_id", ""),
                    "cusip": row.get("CUSIPMEMBER", ""),
                    "issuer": row.get("NAMEOFCOLLATERALISSUER", ""),
                    "title": row.get("CTGRYINVESTMENTSRPRSNTSCOLLATE", ""),
                    "investment_category": row.get(
                        "CTGRYINVESTMENTSRPRSNTSCOLLATE", ""
                    ),
                    "maturity_date": _sec_date(row.get("COLLATERALMATURITYDATE", "")),
                    "security_bucket": _collateral_bucket(row),
                    "value": value,
                }
            )
    return rows


def _aggregate_records(
    rows: list[dict],
    record_type: str,
    period_role: str,
) -> list[dict[str, str]]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    report_dates = [str(row.get("report_date", "")) for row in rows if row.get("report_date")]
    for row in rows:
        totals[str(row.get("security_bucket", "other"))] += row["value"]
        totals["total"] += row["value"]
    report_date = max(report_dates) if report_dates else ""
    return [
        {
            "record_type": "aggregate",
            "period_role": period_role,
            "channel": record_type,
            "security_bucket": bucket,
            "report_date": report_date,
            "value": str(value),
            "value_bil": str(value / Decimal("1000000000")),
            "cusip": "",
            "issuer": "",
            "title": "",
            "maturity_date": "",
            "series_name": "",
            "source_note": (
                "SEC N-MFP monthly flat file aggregated from fund portfolio "
                "security and collateral CUSIP fields; as-filed fund data, "
                "not final investor incidence."
            ),
        }
        for bucket, value in sorted(totals.items())
    ]


def _top_cusip_records(
    rows: list[dict],
    record_type: str,
    period_role: str,
) -> list[dict[str, str]]:
    by_cusip: dict[str, dict[str, str | Decimal]] = {}
    for row in rows:
        cusip = str(row.get("cusip", ""))
        if not cusip:
            continue
        if cusip not in by_cusip:
            by_cusip[cusip] = dict(row)
        else:
            by_cusip[cusip]["value"] += row["value"]
    top_rows = sorted(
        by_cusip.values(),
        key=lambda row: row["value"],
        reverse=True,
    )[:50]
    return [
        {
            "record_type": "cusip",
            "period_role": period_role,
            "channel": record_type,
            "security_bucket": str(row.get("security_bucket", "")),
            "report_date": str(row.get("report_date", "")),
            "value": str(row["value"]),
            "value_bil": str(row["value"] / Decimal("1000000000")),
            "cusip": str(row.get("cusip", "")),
            "issuer": str(row.get("issuer", "")),
            "title": str(row.get("title", "")),
            "maturity_date": str(row.get("maturity_date", "")),
            "series_name": str(row.get("series_name", "")),
            "source_note": (
                "Top SEC N-MFP Treasury CUSIP rows retained for downstream "
                "matching; aggregate rows should be used for OFR reconciliation."
            ),
        }
        for row in top_rows
    ]


def _is_treasury_security(row: dict[str, str]) -> bool:
    text = " ".join(
        [
            row.get("NAMEOFISSUER", ""),
            row.get("TITLEOFISSUER", ""),
            row.get("INVESTMENTCATEGORY", ""),
        ]
    ).upper()
    return row.get("CUSIP_NUMBER", "").startswith("912") or "TREASURY" in text


def _is_treasury_collateral(row: dict[str, str]) -> bool:
    text = " ".join(
        [
            row.get("NAMEOFCOLLATERALISSUER", ""),
            row.get("CTGRYINVESTMENTSRPRSNTSCOLLATE", ""),
        ]
    ).upper()
    return row.get("CUSIPMEMBER", "").startswith("912") or "TREASUR" in text


def _treasury_bucket(row: dict[str, str]) -> str:
    text = " ".join(
        [
            row.get("NAMEOFISSUER", ""),
            row.get("TITLEOFISSUER", ""),
            row.get("INVESTMENTCATEGORY", ""),
        ]
    ).lower()
    if "bill" in text:
        return "bill"
    if "floating" in text or "frn" in text:
        return "frn"
    if "inflation" in text or "tips" in text:
        return "tips"
    if "bond" in text:
        return "bond"
    if "note" in text:
        return "note"
    return "other_treasury"


def _collateral_bucket(row: dict[str, str]) -> str:
    text = " ".join(
        [
            row.get("NAMEOFCOLLATERALISSUER", ""),
            row.get("CTGRYINVESTMENTSRPRSNTSCOLLATE", ""),
        ]
    ).lower()
    if "inflation" in text or "tips" in text:
        return "tips_collateral"
    if "bill" in text:
        return "bill_collateral"
    if "note" in text or "bond" in text:
        return "coupon_collateral"
    return "treasury_collateral"


def _decimal(value: str | None) -> Decimal:
    if value in (None, "", ".", "n.a."):
        return Decimal("0")
    return Decimal(str(value).replace(",", "").strip())


def _sec_date(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return value


def _latest_report_date(records: list[dict[str, str]]) -> str | None:
    dates = [record["report_date"] for record in records if record.get("report_date")]
    return max(dates) if dates else None
