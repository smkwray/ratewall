"""Federal Reserve Board FEDS research-data adapters."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Callable
from urllib.request import Request
from urllib.request import urlopen

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


class FedFedsAdapter:
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

    def pull_brw_shocks(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "fed_feds":
            raise ValueError(f"{series_id} is registered to {spec.source}, not fed_feds")
        with open_with_timeout(self.opener, _request(spec.endpoint)) as response:
            text = response.read().decode("utf-8-sig")

        records: list[dict[str, str]] = []
        for row in csv.DictReader(io.StringIO(text)):
            month = _month_to_iso(str(row.get("month", "")).strip())
            fomc_date = _date_to_iso(str(row.get("date_fomc", "")).strip())
            monthly = str(row.get("BRW_monthly (updated)", "")).strip()
            fomc = str(row.get("BRW_fomc (updated)", "")).strip()
            if not month and not fomc_date:
                continue
            records.append(
                {
                    "month": month,
                    "monthly_shock_pctpt": monthly,
                    "fomc_date": fomc_date,
                    "fomc_shock_pctpt": fomc,
                    "source_variant": "updated_2021_03_04",
                }
            )
        if not records:
            raise ValueError("Federal Reserve BRW shock CSV was empty")

        latest_month = max(record["month"] for record in records if record["month"])
        metadata = RetrievalMetadata(
            source_id="fed_feds",
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at="2021-03-04",
            note=f"Latest monthly observation in source file: {latest_month}",
        )
        return SourceSnapshot(metadata=metadata, records=records)


def _month_to_iso(value: str) -> str:
    if not value:
        return ""
    try:
        year, month = value.split("m", maxsplit=1)
        return f"{int(year):04d}-{int(month):02d}-01"
    except ValueError:
        return ""


def _date_to_iso(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%d-%b-%y").date().isoformat()
    except ValueError:
        return ""


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "Mozilla/5.0 ratewall-research"})
