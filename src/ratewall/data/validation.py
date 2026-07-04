"""Validation helpers for source snapshots."""

from __future__ import annotations

from ratewall.sources.base import SourceSnapshot


REQUIRED_SNAPSHOT_FIELDS = {
    "source_id",
    "series_id",
    "source_url",
    "units",
    "frequency",
    "transform",
    "retrieved_at",
}


def validate_snapshot_metadata(snapshot: SourceSnapshot) -> list[str]:
    metadata = snapshot.metadata.to_dict()
    return sorted(field for field in REQUIRED_SNAPSHOT_FIELDS if not metadata.get(field))

