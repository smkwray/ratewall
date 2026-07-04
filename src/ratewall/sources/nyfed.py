"""NY Fed Markets API adapter."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable
from urllib.request import urlopen

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


class NyFedAdapter:
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

    def pull_endpoint(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "ny_fed":
            raise ValueError(f"{series_id} is registered to {spec.source}, not ny_fed")
        with open_with_timeout(self.opener, spec.endpoint) as response:
            payload = json.loads(response.read().decode("utf-8"))
        records = _records_from_payload(payload)
        if not isinstance(records, list):
            raise ValueError("NY Fed response could not be represented as records")
        source_release_at = _first_date(records)
        metadata = RetrievalMetadata(
            source_id="ny_fed",
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=source_release_at,
        )
        return SourceSnapshot(metadata=metadata, records=records)


def _records_from_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    if isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload.get("refRates"), list):
        return payload["refRates"]
    soma = payload.get("soma")
    if isinstance(soma, dict) and isinstance(soma.get("summary"), list):
        return soma["summary"]
    return [payload]


def _first_date(records: list) -> str | None:
    dates: list[str] = []
    for record in records:
        if isinstance(record, dict):
            for key in ("asOfDate", "as_of_date", "effectiveDate", "date"):
                if record.get(key):
                    dates.append(str(record[key]))
                    break
    return max(dates) if dates else None
