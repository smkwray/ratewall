"""FRED CSV adapter."""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
from datetime import datetime
from typing import Callable
from urllib.parse import urlencode
from urllib.request import urlopen

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


class FredAdapter:
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

    def build_url(self, series_id: str) -> str:
        spec = self.registry.series_definition(series_id)
        if spec.source != "fred":
            raise ValueError(f"{series_id} is registered to {spec.source}, not fred")
        return spec.endpoint

    def pull_series(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        url = self.build_url(series_id)
        api_key = os.environ.get("FRED_API_KEY")
        if self.opener is urlopen and api_key:
            records = _api_records(series_id, api_key)
            source_url = _api_url(series_id, api_key=None)
        elif self.opener is urlopen:
            text = _curl_text(url)
            records = _csv_records(text)
            source_url = url
        else:
            with open_with_timeout(self.opener, url) as response:
                text = response.read().decode("utf-8")
            records = _csv_records(text)
            source_url = url
        metadata = RetrievalMetadata(
            source_id="fred",
            series_id=series_id,
            source_url=source_url,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=_latest_record_date(records),
        )
        return SourceSnapshot(metadata=metadata, records=records)


def _csv_records(text: str) -> list[dict[str, str | None]]:
    rows = csv.DictReader(io.StringIO(text))
    if not rows.fieldnames or "observation_date" not in rows.fieldnames:
        raise ValueError("FRED CSV response missing observation_date column")
    records: list[dict[str, str | None]] = []
    value_column: str | None = None
    for row in rows:
        if value_column is None:
            value_column = next(
                (key for key in row.keys() if key != "observation_date"),
                None,
            )
            if value_column is None:
                raise ValueError("FRED CSV response missing value column")
        raw_value = row.get(value_column, "")
        date_value = str(row.get("observation_date", "")).strip()
        if not date_value:
            raise ValueError("FRED CSV response contained blank observation_date")
        records.append(
            {
                "date": date_value,
                "value": None if raw_value in {"", "."} else raw_value,
            }
        )
    if not records:
        raise ValueError("FRED CSV returned no observations")
    return records


def _latest_record_date(records: list[dict[str, str | None]]) -> str | None:
    dates = [str(record.get("date", "")) for record in records if record.get("date")]
    return max(dates) if dates else None


def _api_records(series_id: str, api_key: str) -> list[dict[str, str | None]]:
    payload = _json_payload(_curl_text(_api_url(series_id, api_key=api_key)))
    observations = payload.get("observations", [])
    if not isinstance(observations, list) or not observations:
        message = payload.get("error_message") or "FRED API returned no observations"
        raise ValueError(f"{series_id}: {message}")
    records: list[dict[str, str | None]] = []
    for observation in observations:
        if not isinstance(observation, dict):
            raise ValueError(f"{series_id}: FRED API observation was not an object")
        if not observation.get("date"):
            raise ValueError(f"{series_id}: FRED API observation missing date")
        raw_value = observation.get("value", "")
        records.append(
            {
                "date": str(observation["date"]),
                "value": None if raw_value in {"", "."} else str(raw_value),
            }
        )
    return records


def _json_payload(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise ValueError("FRED API response did not contain a JSON object")
    decoder = json.JSONDecoder()
    try:
        payload, _end = decoder.raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ValueError("FRED API response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("FRED API response was not a JSON object")
    return payload


def _api_url(series_id: str, api_key: str | None) -> str:
    params = {
        "series_id": series_id,
        "file_type": "json",
        "sort_order": "asc",
    }
    if api_key is not None:
        params["api_key"] = api_key
    return "https://api.stlouisfed.org/fred/series/observations?" + urlencode(params)


def _curl_text(url: str) -> str:
    connect_timeout = _env_int("RATEWALL_FRED_CONNECT_TIMEOUT_SECONDS", 10, minimum=1)
    max_time = _env_int("RATEWALL_FRED_MAX_TIME_SECONDS", 40, minimum=1)
    result = subprocess.run(
        [
            "curl",
            "-L",
            "-s",
            "--fail-with-body",
            "--retry",
            "2",
            "--connect-timeout",
            str(connect_timeout),
            "--max-time",
            str(max_time),
            url,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return max(minimum, parsed)
