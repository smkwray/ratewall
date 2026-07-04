"""Treasury International Capital adapter."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from typing import Callable
from urllib.request import Request, urlopen

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


TRESSECT_PATTERN = re.compile(
    r"^\s*(?P<month>\d{4}-\d{2})\s+"
    r"(?P<total>[-\d,]+)\s+"
    r"(?P<official>[-\d,]+)\s+"
    r"(?P<other>[-\d,]+)\s+"
    r"(?P<international>[-\d,]+)\s*$"
)


class TicAdapter:
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

    def pull_treasury_sector_transactions(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "treasury_tic":
            raise ValueError(
                f"{series_id} is registered to {spec.source}, not treasury_tic"
            )
        request = Request(
            spec.endpoint,
            headers={"User-Agent": "ratewall research prototype"},
        )
        with open_with_timeout(self.opener, request, timeout=30) as response:
            text = response.read().decode("utf-8", errors="replace")
        records = _parse_tressect(text)
        metadata = RetrievalMetadata(
            source_id="treasury_tic",
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=records[0]["month"] if records else None,
        )
        return SourceSnapshot(metadata=metadata, records=records)

    def pull_foreign_treasury_stock_split(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "treasury_tic":
            raise ValueError(
                f"{series_id} is registered to {spec.source}, not treasury_tic"
            )
        request = Request(
            spec.endpoint,
            headers={"User-Agent": "ratewall research prototype"},
        )
        with open_with_timeout(self.opener, request, timeout=45) as response:
            text = response.read().decode("utf-8-sig", errors="replace")
        records = _parse_total_tic_liabilities(text)
        metadata = RetrievalMetadata(
            source_id="treasury_tic",
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=records[0]["as_of_quarter"] if records else None,
        )
        return SourceSnapshot(metadata=metadata, records=records)


def _parse_tressect(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for line in text.splitlines():
        match = TRESSECT_PATTERN.match(line)
        if not match:
            continue
        groups = match.groupdict()
        records.append(
            {
                "month": groups["month"],
                "total_net_foreign_purchases_mil": groups["total"].replace(",", ""),
                "foreign_official_institutions_mil": groups["official"].replace(
                    ",", ""
                ),
                "other_foreigners_mil": groups["other"].replace(",", ""),
                "international_regional_organizations_mil": groups[
                    "international"
                ].replace(",", ""),
                "scope_note": (
                    "TIC tressect reports net purchases of Treasury bonds and "
                    "notes by foreign sector; it is a transaction split, not a "
                    "stock-holder split."
                ),
            }
        )
    return sorted(records, key=lambda row: row["month"], reverse=True)


def _parse_total_tic_liabilities(text: str) -> list[dict[str, str]]:
    rows = list(csv.reader(text.splitlines()))
    as_of_quarter = _total_tic_as_of(rows)
    records: list[dict[str, str]] = []
    in_short_term = False
    treasury_count = 0
    for row in rows:
        label = " ".join(cell.strip() for cell in row[:1]).strip()
        if not label:
            continue
        normalized = re.sub(r"[.\s]+", " ", label).strip().lower()
        if normalized.startswith("short-term securities"):
            in_short_term = True
        if (
            "treasur" not in normalized
            or len(row) < 4
            or not all(_looks_numeric(cell) for cell in row[1:4])
        ):
            continue
        treasury_count += 1
        component = (
            "short_term_treasury_securities"
            if in_short_term or treasury_count > 1
            else "long_term_treasury_securities"
        )
        records.append(_total_tic_record(component, as_of_quarter, row))
    if len(records) >= 2:
        long_record = next(
            (
                record
                for record in records
                if record["component"] == "long_term_treasury_securities"
            ),
            None,
        )
        short_record = next(
            (
                record
                for record in records
                if record["component"] == "short_term_treasury_securities"
            ),
            None,
        )
        if long_record and short_record:
            records.insert(
                0,
                _summed_total_tic_record(
                    "total_treasury_securities",
                    as_of_quarter,
                    long_record,
                    short_record,
                ),
            )
    return records


def _total_tic_as_of(rows: list[list[str]]) -> str:
    for row in rows:
        cells = [cell.strip() for cell in row if cell.strip()]
        if len(cells) >= 2 and cells[0].startswith("December 202"):
            return f"{cells[0]}{cells[1]}"
        if cells and re.match(r"^[A-Za-z]+ \d{4}$", cells[0]):
            return cells[0]
    return ""


def _total_tic_record(
    component: str,
    as_of_quarter: str,
    row: list[str],
) -> dict[str, str]:
    all_foreign = _clean_number(row[1])
    official = _clean_number(row[2])
    other = _clean_number(row[3])
    return {
        "component": component,
        "as_of_quarter": as_of_quarter,
        "all_foreign_holders_mil": all_foreign,
        "foreign_official_holders_mil": official,
        "other_foreign_holders_mil": other,
        "official_share": _share(official, all_foreign),
        "other_share": _share(other, all_foreign),
        "source_note": (
            "TIC Total U.S. Banking and Securities Liabilities table reports "
            "foreign resident stock positions by all, foreign official, and "
            "other foreign holders; it is not a CUSIP-level holder allocation."
        ),
    }


def _summed_total_tic_record(
    component: str,
    as_of_quarter: str,
    long_record: dict[str, str],
    short_record: dict[str, str],
) -> dict[str, str]:
    all_foreign = str(
        int(long_record["all_foreign_holders_mil"])
        + int(short_record["all_foreign_holders_mil"])
    )
    official = str(
        int(long_record["foreign_official_holders_mil"])
        + int(short_record["foreign_official_holders_mil"])
    )
    other = str(
        int(long_record["other_foreign_holders_mil"])
        + int(short_record["other_foreign_holders_mil"])
    )
    return {
        "component": component,
        "as_of_quarter": as_of_quarter,
        "all_foreign_holders_mil": all_foreign,
        "foreign_official_holders_mil": official,
        "other_foreign_holders_mil": other,
        "official_share": _share(official, all_foreign),
        "other_share": _share(other, all_foreign),
        "source_note": (
            "Long- and short-term Treasury security stock rows summed from "
            "the official TIC total-liabilities table for holder split context."
        ),
    }


def _clean_number(value: str) -> str:
    return value.replace(",", "").strip()


def _looks_numeric(value: str) -> bool:
    try:
        int(_clean_number(value))
    except ValueError:
        return False
    return True


def _share(numerator: str, denominator: str) -> str:
    try:
        den = int(denominator)
        if den == 0:
            return ""
        return str(int(numerator) / den)
    except ValueError:
        return ""
