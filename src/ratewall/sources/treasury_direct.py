"""TreasuryDirect buyback operation adapter."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


BUYBACK_PAGE = "https://www.treasurydirect.gov/auctions/announcements-data-results/buy-backs/"


class TreasuryDirectBuybackAdapter:
    """Pull TreasuryDirect buyback operation records."""

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

    def pull_buybacks(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "treasury_direct":
            raise ValueError(
                f"{series_id} is registered to {spec.source}, not treasury_direct"
            )
        page_body = _read_text(self.opener, BUYBACK_PAGE)
        endpoint = _script_value(page_body, "hostLocation")
        headers = _page_headers(page_body)
        url = endpoint + "?" + urlencode(_current_year_window(self.clock))
        records = _json_records(_read_text(self.opener, Request(url, headers=headers)))
        return SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id="treasury_direct",
                series_id=series_id,
                source_url=url,
                units=spec.units,
                frequency=spec.frequency,
                transform=spec.transform,
                retrieved_at=utc_now_iso(self.clock),
                source_release_at=_latest_operation_date(records),
                note=(
                    "TreasuryDirect buyback JSON endpoint discovered from the "
                    "public buyback announcements/results page at runtime; "
                    "page-provided API headers are not stored in provenance."
                ),
            ),
            records=records,
        )


def _current_year_window(clock: Callable[[], datetime] | None) -> dict[str, str]:
    now = clock() if clock is not None else datetime.now()
    year = now.year
    return {
        "operationStartDTMBegin": f"{year}-01-01T00:00:00Z",
        "operationStartDTMEnd": f"{year}-12-31T23:59:00Z",
    }


def _page_headers(page_body: str) -> dict[str, str]:
    return {
        "client_id": _script_value(page_body, "client_id"),
        "client_secret": _script_value(page_body, "client_secret"),
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 ratewall-research",
    }


def _script_value(page_body: str, name: str) -> str:
    if name == "hostLocation":
        pattern = r"var\s+hostLocation\s*=\s*'([^']+)'"
    else:
        pattern = rf'"{name}"\s*:\s*\'([^\']+)\''
    match = re.search(pattern, page_body)
    if not match:
        raise ValueError(f"could not find TreasuryDirect {name} in page script")
    return match.group(1)


def _read_text(opener: Callable, request_or_url) -> str:
    with open_with_timeout(opener, request_or_url) as response:
        return response.read().decode("utf-8", errors="replace")


def _json_records(text: str) -> list[dict]:
    payload = json.loads(text)
    if not isinstance(payload, list):
        raise ValueError("TreasuryDirect buyback response was not a JSON array")
    return payload


def _latest_operation_date(records: list[dict]) -> str | None:
    dates = [
        str(record.get("operationStartDTM", ""))[:10]
        for record in records
        if record.get("operationStartDTM")
    ]
    parsed = []
    for value in dates:
        try:
            parsed.append(date.fromisoformat(value))
        except ValueError:
            continue
    return max(parsed).isoformat() if parsed else None
