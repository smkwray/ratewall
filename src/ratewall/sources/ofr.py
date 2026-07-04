"""OFR Short-Term Funding Monitor adapter."""

from __future__ import annotations

import gzip
import json
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


MMF_SERIES = {
    "MMF-MMF_TOT-M": "total_investments",
    "MMF-MMF_T_TOT-M": "us_treasury_securities",
    "MMF-MMF_RP_T_TOT-M": "treasury_repo_total",
    "MMF-MMF_RP_T_OO-M": "treasury_repo_open_maturity",
    "MMF-MMF_RP_T_LE30-M": "treasury_repo_30_days_or_less",
    "MMF-MMF_RP_T_G30-M": "treasury_repo_more_than_30_days",
}


class OfrMmfAdapter:
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

    def pull_dataset(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "ofr_stfm":
            raise ValueError(f"{series_id} is registered to {spec.source}, not ofr_stfm")
        request = Request(
            spec.endpoint,
            headers={
                "User-Agent": "ratewall research prototype",
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
            },
        )
        with open_with_timeout(self.opener, request, timeout=30) as response:
            raw = response.read()
            if str(response.headers.get("Content-Encoding", "")).lower() == "gzip":
                raw = gzip.decompress(raw)
        payload = json.loads(raw.decode("utf-8"))
        records = _flatten_mmf_timeseries(payload)
        metadata = RetrievalMetadata(
            source_id="ofr_stfm",
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=_latest_record_date(records),
        )
        return SourceSnapshot(metadata=metadata, records=records)


def _flatten_mmf_timeseries(payload: dict) -> list[dict[str, str]]:
    series_map = payload.get("timeseries", {})
    records: list[dict[str, str]] = []
    for mnemonic, channel in MMF_SERIES.items():
        item = series_map.get(mnemonic, {})
        metadata = item.get("metadata", {})
        latest = _latest_observation(item)
        if latest is None:
            continue
        date, value = latest
        records.append(
            {
                "mnemonic": mnemonic,
                "channel": channel,
                "date": date,
                "value": value,
                "short_name": str(metadata.get("short_name", "")),
                "long_name": str(metadata.get("long_name", "")),
                "unit": str(metadata.get("unit", "USD")),
                "frequency": str(metadata.get("frequency", "Monthly")),
            }
        )
    return records


def _latest_observation(item: dict) -> tuple[str, str] | None:
    timeseries = item.get("timeseries", {})
    observations = timeseries.get("aggregation") or timeseries.get("observations") or []
    for observation in reversed(observations):
        if not isinstance(observation, list | tuple) or len(observation) < 2:
            continue
        date = str(observation[0])
        value = observation[1]
        if value in (None, "", "."):
            continue
        return date, str(value)
    return None


def _latest_record_date(records: list[dict[str, str]]) -> str | None:
    dates = [record["date"] for record in records if record.get("date")]
    return max(dates) if dates else None
