"""YAML-backed source registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


REQUIRED_SOURCE_FIELDS = {
    "name",
    "publisher",
    "role",
    "access",
    "base_url",
    "documentation_url",
    "update_cadence",
    "timestamp_rule",
}

REQUIRED_SERIES_FIELDS = {
    "source",
    "name",
    "endpoint",
    "units",
    "frequency",
    "transform",
    "update_cadence",
}


@dataclass(frozen=True)
class TimestampPolicy:
    retrieval_timezone: str
    retrieval_timestamp_field: str
    retrieval_timestamp_format: str
    source_release_timestamp_field: str
    source_release_timestamp_rule: str
    required_snapshot_fields: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "TimestampPolicy":
        return cls(
            retrieval_timezone=str(data["retrieval_timezone"]),
            retrieval_timestamp_field=str(data["retrieval_timestamp_field"]),
            retrieval_timestamp_format=str(data["retrieval_timestamp_format"]),
            source_release_timestamp_field=str(data["source_release_timestamp_field"]),
            source_release_timestamp_rule=str(data["source_release_timestamp_rule"]),
            required_snapshot_fields=tuple(data["required_snapshot_fields"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval_timezone": self.retrieval_timezone,
            "retrieval_timestamp_field": self.retrieval_timestamp_field,
            "retrieval_timestamp_format": self.retrieval_timestamp_format,
            "source_release_timestamp_field": self.source_release_timestamp_field,
            "source_release_timestamp_rule": self.source_release_timestamp_rule,
            "required_snapshot_fields": list(self.required_snapshot_fields),
        }


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    name: str
    publisher: str
    role: str
    access: str
    base_url: str
    documentation_url: str
    update_cadence: str
    timestamp_rule: str

    @classmethod
    def from_mapping(
        cls,
        source_id: str,
        data: Mapping[str, Any],
    ) -> "SourceDefinition":
        missing = REQUIRED_SOURCE_FIELDS - data.keys()
        if missing:
            joined = ", ".join(sorted(missing))
            raise ValueError(f"source {source_id} missing fields: {joined}")
        return cls(source_id=source_id, **{field: str(data[field]) for field in REQUIRED_SOURCE_FIELDS})

    def to_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "publisher": self.publisher,
            "role": self.role,
            "access": self.access,
            "base_url": self.base_url,
            "documentation_url": self.documentation_url,
            "update_cadence": self.update_cadence,
            "timestamp_rule": self.timestamp_rule,
        }


@dataclass(frozen=True)
class SeriesDefinition:
    series_id: str
    source: str
    name: str
    endpoint: str
    units: str
    frequency: str
    transform: str
    update_cadence: str
    release: str | None = None
    liability_channel: str | None = None

    @classmethod
    def from_mapping(
        cls,
        series_id: str,
        data: Mapping[str, Any],
    ) -> "SeriesDefinition":
        missing = REQUIRED_SERIES_FIELDS - data.keys()
        if missing:
            joined = ", ".join(sorted(missing))
            raise ValueError(f"series {series_id} missing fields: {joined}")
        return cls(
            series_id=series_id,
            source=str(data["source"]),
            name=str(data["name"]),
            endpoint=str(data["endpoint"]),
            units=str(data["units"]),
            frequency=str(data["frequency"]),
            transform=str(data["transform"]),
            update_cadence=str(data["update_cadence"]),
            release=str(data["release"]) if data.get("release") else None,
            liability_channel=(
                str(data["liability_channel"]) if data.get("liability_channel") else None
            ),
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "series_id": self.series_id,
            "source": self.source,
            "name": self.name,
            "endpoint": self.endpoint,
            "units": self.units,
            "frequency": self.frequency,
            "transform": self.transform,
            "update_cadence": self.update_cadence,
            "release": self.release,
            "liability_channel": self.liability_channel,
        }


@dataclass(frozen=True)
class SourceRegistry:
    timestamp_policy: TimestampPolicy
    sources: dict[str, SourceDefinition]
    series: dict[str, SeriesDefinition]

    @classmethod
    def from_path(cls, path: Path | str) -> "SourceRegistry":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("source registry YAML must contain a mapping")
        policy = TimestampPolicy.from_mapping(payload["timestamp_policy"])
        sources = {
            source_id: SourceDefinition.from_mapping(source_id, data)
            for source_id, data in payload.get("sources", {}).items()
        }
        series = {
            series_id: SeriesDefinition.from_mapping(series_id, data)
            for series_id, data in payload.get("series", {}).items()
        }
        registry = cls(timestamp_policy=policy, sources=sources, series=series)
        errors = registry.validate()
        if errors:
            raise ValueError("invalid source registry: " + "; ".join(errors))
        return registry

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.timestamp_policy.retrieval_timezone != "UTC":
            errors.append("timestamp_policy.retrieval_timezone must be UTC")
        required = set(self.timestamp_policy.required_snapshot_fields)
        missing_snapshot_fields = {
            "source_id",
            "series_id",
            "source_url",
            "units",
            "frequency",
            "transform",
            "retrieved_at",
        } - required
        for field in sorted(missing_snapshot_fields):
            errors.append(f"timestamp_policy missing required snapshot field {field}")
        for series_id, definition in self.series.items():
            if definition.source not in self.sources:
                errors.append(f"series {series_id} references unknown source")
        return errors

    def source(self, source_id: str) -> SourceDefinition:
        try:
            return self.sources[source_id]
        except KeyError as exc:
            raise KeyError(f"unknown source {source_id}") from exc

    def series_definition(self, series_id: str) -> SeriesDefinition:
        try:
            return self.series[series_id]
        except KeyError as exc:
            raise KeyError(f"unknown series {series_id}") from exc

    def series_for_source(self, source_id: str) -> list[SeriesDefinition]:
        self.source(source_id)
        return [
            definition
            for definition in self.series.values()
            if definition.source == source_id
        ]

