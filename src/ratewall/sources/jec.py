"""JEC/Treasury maturity-anchor adapter."""

from __future__ import annotations

import re
from datetime import datetime
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


class JecTreasuryAdapter:
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

    def pull_anchor(self, series_id: str = "treasury_repricing_anchor") -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "jec_treasury":
            raise ValueError(f"{series_id} is registered to {spec.source}, not jec_treasury")
        with open_with_timeout(self.opener, _request(spec.endpoint)) as response:
            body = response.read().decode("utf-8", errors="replace")
        text = _clean_text(body)
        as_of_date = _as_of_date(text)
        one_year_share = _share_near(text, r"matur(?:e|es|ing).*?12 months")
        average_maturity = _number_near(text, r"average maturity")
        if one_year_share is None:
            raise ValueError("could not parse Treasury share maturing within 12 months")
        records = [
            {
                "as_of_date": as_of_date,
                "matures_within_12m_share": one_year_share,
                "average_maturity_months": average_maturity or "",
                "one_quarter_share": "0.12",
                "three_year_share": "0.58",
                "ten_year_share": "1.00",
                "parser_note": (
                    "1y share parsed from live report; other horizon shares are "
                    "transparent anchors until a full maturity ladder is available."
                ),
            }
        ]
        metadata = RetrievalMetadata(
            source_id=spec.source,
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=as_of_date,
            snapshot_kind="live",
        )
        return SourceSnapshot(metadata=metadata, records=records)


def _clean_text(value: str) -> str:
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _as_of_date(text: str) -> str | None:
    match = re.search(r"as of ([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})", text, flags=re.I)
    return match.group(1) if match else None


def _share_near(text: str, phrase_pattern: str) -> str | None:
    phrase = re.search(phrase_pattern, text, flags=re.I)
    if phrase:
        window = text[max(0, phrase.start() - 180) : phrase.start()]
        matches = list(re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*percent", window, flags=re.I))
        if matches:
            return str(float(matches[-1].group(1)) / 100)
        forward = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*percent", text[phrase.end() : phrase.end() + 180], flags=re.I)
        if forward:
            return str(float(forward.group(1)) / 100)
    return None


def _number_near(text: str, phrase_pattern: str) -> str | None:
    match = re.search(rf"{phrase_pattern}[^.]*?([0-9]+(?:\.[0-9]+)?)", text, flags=re.I)
    return match.group(1) if match else None


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "Mozilla/5.0 ratewall-research"})
