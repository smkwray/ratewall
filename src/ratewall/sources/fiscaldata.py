"""Treasury FiscalData API adapter."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, Mapping
from urllib.parse import urlencode
from urllib.request import urlopen

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


class FiscalDataAdapter:
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

    def build_url(
        self,
        series_id: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> str:
        spec = self.registry.series_definition(series_id)
        if spec.source != "treasury_fiscaldata":
            raise ValueError(
                f"{series_id} is registered to {spec.source}, not treasury_fiscaldata"
            )
        query = urlencode(dict(params or {}))
        return spec.endpoint if not query else f"{spec.endpoint}?{query}"

    def pull_table(
        self,
        series_id: str,
        *,
        params: Mapping[str, str] | None = None,
        paginate: bool = False,
    ) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        url = self.build_url(series_id, params=params)
        records = (
            _paginated_records(self.opener, self, series_id, params or {})
            if paginate
            else _records_from_url(self.opener, url)
        )
        if not isinstance(records, list):
            raise ValueError("FiscalData response did not contain a list at data")
        source_release_at = _first_record_date(records)
        metadata = RetrievalMetadata(
            source_id="treasury_fiscaldata",
            series_id=series_id,
            source_url=url,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=source_release_at,
        )
        return SourceSnapshot(metadata=metadata, records=records)


def _paginated_records(
    opener: Callable,
    adapter: FiscalDataAdapter,
    series_id: str,
    params: Mapping[str, str],
) -> list[dict]:
    first_params = dict(params)
    first_params.setdefault("page[number]", "1")
    first_url = adapter.build_url(series_id, params=first_params)
    with open_with_timeout(opener, first_url, timeout=30) as response:
        first_payload = json.loads(response.read().decode("utf-8"))
    records = first_payload.get("data", [])
    total_pages = int(first_payload.get("meta", {}).get("total-pages", 1))
    for page_number in range(2, total_pages + 1):
        page_params = dict(params)
        page_params["page[number]"] = str(page_number)
        page_url = adapter.build_url(series_id, params=page_params)
        records.extend(_records_from_url(opener, page_url))
    return records


def _records_from_url(opener: Callable, url: str) -> list[dict]:
    with open_with_timeout(opener, url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    records = payload.get("data", [])
    if not isinstance(records, list):
        raise ValueError("FiscalData response did not contain a list at data")
    return records


def _first_record_date(records: list) -> str | None:
    for record in records:
        if isinstance(record, dict):
            for key in ("record_date", "reporting_date", "effective_date", "index_date"):
                if record.get(key):
                    return str(record[key])
    return None
