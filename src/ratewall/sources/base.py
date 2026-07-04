"""Shared source-adapter models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence


Clock = Callable[[], datetime]


def utc_now_iso(clock: Clock | None = None) -> str:
    now = clock() if clock is not None else datetime.now(timezone.utc)
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def open_with_timeout(opener: Callable, request, *, timeout: int = 8):
    try:
        return opener(request, timeout=timeout)
    except TypeError:
        return opener(request)


@dataclass(frozen=True)
class RetrievalMetadata:
    source_id: str
    series_id: str
    source_url: str
    units: str
    frequency: str
    transform: str
    retrieved_at: str
    source_release_at: str | None = None
    snapshot_kind: str = "live"
    note: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "series_id": self.series_id,
            "source_url": self.source_url,
            "units": self.units,
            "frequency": self.frequency,
            "transform": self.transform,
            "retrieved_at": self.retrieved_at,
            "source_release_at": self.source_release_at,
            "snapshot_kind": self.snapshot_kind,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RetrievalMetadata":
        return cls(
            source_id=str(data["source_id"]),
            series_id=str(data["series_id"]),
            source_url=str(data["source_url"]),
            units=str(data["units"]),
            frequency=str(data["frequency"]),
            transform=str(data["transform"]),
            retrieved_at=str(data["retrieved_at"]),
            source_release_at=(
                str(data["source_release_at"])
                if data.get("source_release_at") is not None
                else None
            ),
            snapshot_kind=str(data.get("snapshot_kind", "live")),
            note=str(data["note"]) if data.get("note") is not None else None,
        )


@dataclass(frozen=True)
class SourceSnapshot:
    metadata: RetrievalMetadata
    records: Sequence[Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "records": list(self.records),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SourceSnapshot":
        return cls(
            metadata=RetrievalMetadata.from_dict(data["metadata"]),
            records=list(data.get("records", [])),
        )
