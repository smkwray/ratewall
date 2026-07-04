"""Treasury HQM corporate bond yield curve source adapter."""

from __future__ import annotations

import calendar
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

import xlrd

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


LOCAL_HQM_DIR = Path("data/raw/treasury_hqm")


class TreasuryHqmAdapter:
    """Fetch and normalize Treasury HQM corporate bond yield curve workbooks."""

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

    def pull_series(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "treasury_hqm":
            raise ValueError(
                f"{series_id} is registered to {spec.source}, not treasury_hqm"
            )
        if series_id != "TREASURY_HQM_EOM_10Y_PAR":
            raise ValueError(f"unsupported Treasury HQM series {series_id}")

        path = _ensure_local_workbook(
            endpoint=spec.endpoint,
            target=LOCAL_HQM_DIR / "hqmeom_qh_pars.xls",
            opener=self.opener,
        )
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        records = _parse_hqm_eom_10y_par_records(path, source_sha256=sha256)
        latest = records[-1]["date"] if records else None
        return SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id="treasury_hqm",
                series_id=series_id,
                source_url=spec.endpoint,
                units=spec.units,
                frequency=spec.frequency,
                transform=spec.transform,
                retrieved_at=utc_now_iso(self.clock),
                source_release_at=latest,
                snapshot_kind="live_official_workbook",
                note=(
                    "Official Treasury HQM end-of-month par-yield workbook "
                    f"normalized to the 10-year maturity; source_xls_sha256={sha256}"
                ),
            ),
            records=records,
        )


def _ensure_local_workbook(
    *,
    endpoint: str,
    target: Path,
    opener: Callable,
) -> Path:
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with open_with_timeout(opener, _request(endpoint), timeout=30) as response:
        payload = response.read()
    if not payload.startswith(b"\xd0\xcf\x11\xe0"):
        raise ValueError("Treasury HQM endpoint did not return a legacy Excel file")
    target.write_bytes(payload)
    return target


def _parse_hqm_eom_10y_par_records(
    path: Path,
    *,
    source_sha256: str,
) -> list[dict[str, str]]:
    workbook = xlrd.open_workbook(path)
    sheet = workbook.sheet_by_index(0)
    records: list[dict[str, str]] = []
    for row_index in range(sheet.nrows):
        raw_date = str(sheet.cell_value(row_index, 0)).strip()
        if not raw_date or raw_date == "Date":
            continue
        parsed_date = _parse_month_end(raw_date)
        if parsed_date is None:
            continue
        value = sheet.cell_value(row_index, 4)
        if value in ("", None):
            continue
        records.append(
            {
                "date": parsed_date,
                "value": _format_numeric(value),
                "maturity_years": "10",
                "yield_measure": "end_of_month_par_yield",
                "source_workbook": path.name,
                "source_xls_sha256": source_sha256,
                "source_row_index": str(row_index),
            }
        )
    if not records:
        raise ValueError(f"{path} produced no Treasury HQM observations")
    return records


def _parse_month_end(value: str) -> str | None:
    try:
        parsed = datetime.strptime(value, "%b %Y")
    except ValueError:
        return None
    day = calendar.monthrange(parsed.year, parsed.month)[1]
    return f"{parsed.year:04d}-{parsed.month:02d}-{day:02d}"


def _format_numeric(value: object) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".")


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "Mozilla/5.0 ratewall-research"})
