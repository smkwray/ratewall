"""Snapshot helpers for source-backed raw pulls."""

from __future__ import annotations

import json
from pathlib import Path

from ratewall.sources.base import SourceSnapshot


def write_json_snapshot(snapshot: SourceSnapshot, path: Path) -> Path:
    """Write a consolidated JSON snapshot.

    Callers choose paths under ignored project data directories such as
    `data/raw`. The helper writes one JSON payload per pull to avoid many small
    sidecar metadata files.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_snapshot_bundle(snapshots: list[SourceSnapshot], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "ratewall.snapshot_bundle.v1",
        "snapshots": [snapshot.to_dict() for snapshot in snapshots],
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def read_snapshot_bundle(path: Path) -> list[SourceSnapshot]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    snapshots = payload.get("snapshots", [])
    if not isinstance(snapshots, list):
        raise ValueError("snapshot bundle must contain a list at snapshots")
    return [SourceSnapshot.from_dict(snapshot) for snapshot in snapshots]
