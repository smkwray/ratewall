"""SF Fed monetary policy surprise adapter."""

from __future__ import annotations

import csv
import io
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


class SfFedAdapter:
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

    def pull_surprises(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "sf_fed":
            raise ValueError(f"{series_id} is registered to {spec.source}, not sf_fed")
        with open_with_timeout(self.opener, spec.endpoint) as response:
            text = response.read().decode("utf-8-sig")
        records: list[dict[str, str]] = []
        for row in csv.DictReader(io.StringIO(text)):
            if row.get("Date"):
                records.append(
                    {
                        "date": str(row["Date"]),
                        "raw_surprise_bps": str(row.get("Surprise", "")),
                        "orthogonalized_surprise_bps": str(
                            row.get("Orthogonalized Surprise", "")
                        ),
                    }
                )
        if not records:
            raise ValueError("SF Fed monetary policy surprise CSV was empty")
        metadata = RetrievalMetadata(
            source_id="sf_fed",
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=records[-1]["date"],
        )
        return SourceSnapshot(metadata=metadata, records=records)
