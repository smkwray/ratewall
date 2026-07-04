"""Federal Reserve H.4.1 adapter."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from html import unescape
from typing import Callable
from urllib.request import Request, urlopen

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


class FedH41Adapter:
    """Fetch and lightly parse H.4.1 release pages with provenance."""

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

    def pull_release(self, series_id: str = "h41_current") -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "fed_h41":
            raise ValueError(f"{series_id} is registered to {spec.source}, not fed_h41")
        with open_with_timeout(self.opener, _request(spec.endpoint)) as response:
            body = response.read().decode("utf-8", errors="replace")
        release_date = _release_date(body)
        deferred_asset = _deferred_asset_from_table(body)
        metadata = RetrievalMetadata(
            source_id="fed_h41",
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=release_date,
        )
        return SourceSnapshot(
            metadata=metadata,
            records=[
                {
                    "content_type": "html_release",
                    "release_date": release_date,
                    "deferred_asset_amt": str(deferred_asset)
                    if deferred_asset is not None
                    else "0",
                    "remittances_to_treasury_amt": "0",
                    "text_excerpt": _clean_text(body)[:4000],
                }
            ],
        )


def _release_date(body: str) -> str | None:
    for pattern in (
        r"Release Date:\s*</[^>]+>\s*<[^>]+>\s*([^<]+)",
        r"Release Date:\s*([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})",
        r"([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})",
    ):
        match = re.search(pattern, body, flags=re.I)
        if match:
            return _clean_text(match.group(1))
    return None


def _number_near(body: str, phrase: str) -> Decimal | None:
    clean = _clean_text(body).lower()
    index = clean.find(phrase)
    if index < 0:
        return None
    window = clean[index : index + 500]
    match = re.search(r"(-?[0-9][0-9,]*(?:\.[0-9]+)?)", window)
    if not match:
        return None
    return Decimal(match.group(1).replace(",", ""))


def _deferred_asset_from_table(body: str) -> Decimal | None:
    for row in re.findall(r"<tr[\s\S]*?</tr>", body, flags=re.I):
        clean = _clean_text(row)
        if "Earnings remittances due to the U.S. Treasury" not in clean:
            continue
        values = re.findall(r"-?[0-9][0-9,]*(?:\.[0-9]+)?", clean)
        # First value is the footnote marker; second is the consolidated total.
        if len(values) >= 2:
            total = Decimal(values[1].replace(",", ""))
            return abs(total) if total < 0 else Decimal("0")
    return _number_near(body, "deferred asset")


def _clean_text(value: str) -> str:
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "Mozilla/5.0 ratewall-research"})
