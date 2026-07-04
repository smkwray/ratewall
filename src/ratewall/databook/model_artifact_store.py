"""Content-addressed storage for local model artifact trees."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ARTIFACT_MANIFEST_SCHEMA_VERSION = "ratewall_model_artifact_manifest_v1"
DEFAULT_ARTIFACT_MANIFEST_FILENAME = "ratewall_model_artifact_manifest.json"

LinkMode = Literal["hardlink", "copy"]


class ModelArtifactStoreError(RuntimeError):
    """Raised when artifact storage or materialization fails closed."""


@dataclass(frozen=True)
class ArtifactManifestStats:
    """Storage totals for one logical artifact manifest."""

    entry_count: int
    total_logical_size_bytes: int
    unique_object_count: int
    unique_object_size_bytes: int

    @property
    def duplicate_savings_bytes(self) -> int:
        return self.total_logical_size_bytes - self.unique_object_size_bytes


@dataclass(frozen=True)
class ArtifactManifestView:
    """Read files from a manifest/object-store artifact tree."""

    root: Path
    manifest_path: Path
    payload: dict[str, Any]
    entries_by_logical_path: dict[str, dict[str, Any]]

    @classmethod
    def from_root(cls, root: str | Path) -> "ArtifactManifestView":
        artifact_root = Path(root)
        manifest_path = artifact_root / DEFAULT_ARTIFACT_MANIFEST_FILENAME
        payload = _read_manifest(manifest_path)
        entries_by_logical_path = {
            str(entry["logical_path"]): entry for entry in payload["entries"]
        }
        return cls(
            root=artifact_root,
            manifest_path=manifest_path,
            payload=payload,
            entries_by_logical_path=entries_by_logical_path,
        )

    def has_file(self, logical_path: str | Path) -> bool:
        return _logical_key(logical_path) in self.entries_by_logical_path

    def list_files(
        self,
        *,
        prefix: str = "",
        suffix: str = "",
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                path
                for path in self.entries_by_logical_path
                if path.startswith(prefix) and path.endswith(suffix)
            )
        )

    def read_text(self, logical_path: str | Path) -> str:
        entry = self._entry(logical_path)
        object_path = _entry_object_path(entry, self.manifest_path.parent, self.payload)
        _verify_object(
            object_path,
            digest=str(entry["sha256"]),
            size_bytes=int(entry["size_bytes"]),
        )
        return object_path.read_text(encoding="utf-8")

    @contextmanager
    def open_text(self, logical_path: str | Path) -> Iterator[Any]:
        object_path = self.object_path(logical_path)
        with object_path.open("rt", encoding="utf-8", newline="") as handle:
            yield handle

    def object_path(self, logical_path: str | Path) -> Path:
        entry = self._entry(logical_path)
        object_path = _entry_object_path(entry, self.manifest_path.parent, self.payload)
        _verify_object(
            object_path,
            digest=str(entry["sha256"]),
            size_bytes=int(entry["size_bytes"]),
        )
        return object_path

    def _entry(self, logical_path: str | Path) -> dict[str, Any]:
        key = _logical_key(logical_path)
        try:
            return self.entries_by_logical_path[key]
        except KeyError as exc:
            raise ModelArtifactStoreError(
                f"artifact manifest missing logical file: {key}"
            ) from exc


def artifact_manifest_exists(root: str | Path) -> bool:
    return (Path(root) / DEFAULT_ARTIFACT_MANIFEST_FILENAME).exists()


def write_artifact_manifest(
    source_root: str | Path,
    *,
    object_store_root: str | Path,
    manifest_path: str | Path | None = None,
) -> ArtifactManifestStats:
    """Write a SHA-256 manifest and copy unique files into an object store.

    The source tree is not modified. The manifest records each logical path in the
    source tree and points it to exactly one immutable object keyed by content hash.
    """

    source = Path(source_root)
    if not source.is_dir():
        raise ModelArtifactStoreError(f"source artifact root does not exist: {source}")

    manifest = (
        Path(manifest_path)
        if manifest_path is not None
        else source / DEFAULT_ARTIFACT_MANIFEST_FILENAME
    )
    object_root = Path(object_store_root)
    object_root.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for path in _source_files(
        source,
        object_store_root=object_root,
        manifest_path=manifest,
    ):
        digest = _sha256_file(path)
        size_bytes = path.stat().st_size
        object_path = _object_path(object_root, digest)
        _store_object(path, object_path, digest=digest, size_bytes=size_bytes)
        entries.append(
            {
                "logical_path": path.relative_to(source).as_posix(),
                "sha256": digest,
                "size_bytes": size_bytes,
                "format": _artifact_format(path),
                "object_path": object_path.relative_to(object_root).as_posix(),
            }
        )

    payload = {
        "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "source_root_name": source.name,
        "object_store_root": _relative_path(object_root, manifest.parent),
        "entries": entries,
    }
    _write_json_atomic(manifest, payload)
    return artifact_manifest_stats(payload)


def estimate_artifact_store_stats(source_root: str | Path) -> ArtifactManifestStats:
    """Estimate dedupe savings for a source tree without writing objects."""

    source = Path(source_root)
    if not source.is_dir():
        raise ModelArtifactStoreError(f"source artifact root does not exist: {source}")
    unique_sizes: dict[str, int] = {}
    total_size = 0
    entry_count = 0
    for path in _source_files(
        source,
        object_store_root=source / ".ratewall-artifact-store-none",
        manifest_path=source / DEFAULT_ARTIFACT_MANIFEST_FILENAME,
    ):
        digest = _sha256_file(path)
        size_bytes = path.stat().st_size
        total_size += size_bytes
        entry_count += 1
        prior_size = unique_sizes.setdefault(digest, size_bytes)
        if prior_size != size_bytes:
            raise ModelArtifactStoreError(
                f"conflicting sizes for estimated object {digest}"
            )
    return ArtifactManifestStats(
        entry_count=entry_count,
        total_logical_size_bytes=total_size,
        unique_object_count=len(unique_sizes),
        unique_object_size_bytes=sum(unique_sizes.values()),
    )


def materialize_artifact_manifest(
    manifest_path: str | Path,
    target_root: str | Path,
    *,
    link_mode: LinkMode = "hardlink",
) -> ArtifactManifestStats:
    """Materialize a manifest into the original logical file layout."""

    manifest = Path(manifest_path)
    payload = _read_manifest(manifest)
    target = Path(target_root)
    target.mkdir(parents=True, exist_ok=True)

    for entry in payload["entries"]:
        logical_path = _safe_logical_path(str(entry["logical_path"]))
        source_object = _entry_object_path(entry, manifest.parent, payload)
        _verify_object(
            source_object,
            digest=str(entry["sha256"]),
            size_bytes=int(entry["size_bytes"]),
        )
        destination = target / logical_path
        if destination.exists():
            _verify_existing_destination(destination, entry)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if link_mode == "hardlink":
            try:
                os.link(source_object, destination)
            except OSError:
                shutil.copy2(source_object, destination)
        elif link_mode == "copy":
            shutil.copy2(source_object, destination)
        else:
            raise ModelArtifactStoreError(f"unsupported link mode: {link_mode}")

    return artifact_manifest_stats(payload)


def verify_artifact_manifest(manifest_path: str | Path) -> ArtifactManifestStats:
    """Verify manifest schema and object hashes without materializing files."""

    manifest = Path(manifest_path)
    payload = _read_manifest(manifest)
    for entry in payload["entries"]:
        _safe_logical_path(str(entry["logical_path"]))
        source_object = _entry_object_path(entry, manifest.parent, payload)
        _verify_object(
            source_object,
            digest=str(entry["sha256"]),
            size_bytes=int(entry["size_bytes"]),
        )
    return artifact_manifest_stats(payload)


def artifact_manifest_stats(
    manifest: str | Path | dict[str, Any],
) -> ArtifactManifestStats:
    """Compute logical and unique-object storage totals for a manifest."""

    payload = _read_manifest(Path(manifest)) if not isinstance(manifest, dict) else manifest
    _validate_manifest_payload(payload)
    unique_sizes: dict[str, int] = {}
    total_size = 0
    for entry in payload["entries"]:
        digest = str(entry["sha256"])
        size_bytes = int(entry["size_bytes"])
        total_size += size_bytes
        prior_size = unique_sizes.setdefault(digest, size_bytes)
        if prior_size != size_bytes:
            raise ModelArtifactStoreError(
                f"manifest has conflicting sizes for object {digest}"
            )
    return ArtifactManifestStats(
        entry_count=len(payload["entries"]),
        total_logical_size_bytes=total_size,
        unique_object_count=len(unique_sizes),
        unique_object_size_bytes=sum(unique_sizes.values()),
    )


def _source_files(
    source_root: Path,
    *,
    object_store_root: Path,
    manifest_path: Path,
) -> tuple[Path, ...]:
    paths: list[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        if path == manifest_path:
            continue
        if _is_relative_to(path, object_store_root):
            continue
        paths.append(path)
    return tuple(sorted(paths, key=lambda item: item.relative_to(source_root).as_posix()))


def _store_object(
    source_path: Path,
    object_path: Path,
    *,
    digest: str,
    size_bytes: int,
) -> None:
    if object_path.exists():
        _verify_object(object_path, digest=digest, size_bytes=size_bytes)
        return
    object_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = object_path.with_name(f".{object_path.name}.tmp")
    shutil.copy2(source_path, temp_path)
    _verify_object(temp_path, digest=digest, size_bytes=size_bytes)
    temp_path.replace(object_path)


def _verify_existing_destination(destination: Path, entry: dict[str, Any]) -> None:
    _verify_object(
        destination,
        digest=str(entry["sha256"]),
        size_bytes=int(entry["size_bytes"]),
    )


def _verify_object(path: Path, *, digest: str, size_bytes: int) -> None:
    if not path.exists():
        raise ModelArtifactStoreError(f"missing artifact object: {path}")
    actual_size = path.stat().st_size
    if actual_size != size_bytes:
        raise ModelArtifactStoreError(
            f"artifact object size mismatch for {path}: "
            f"expected {size_bytes}, found {actual_size}"
        )
    actual_digest = _sha256_file(path)
    if actual_digest != digest:
        raise ModelArtifactStoreError(
            f"artifact object hash mismatch for {path}: "
            f"expected {digest}, found {actual_digest}"
        )


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ModelArtifactStoreError(f"missing artifact manifest: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ModelArtifactStoreError(f"artifact manifest is not a JSON object: {path}")
    _validate_manifest_payload(payload)
    return payload


def _validate_manifest_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != ARTIFACT_MANIFEST_SCHEMA_VERSION:
        raise ModelArtifactStoreError(
            "unsupported artifact manifest schema version: "
            f"{payload.get('schema_version')}"
        )
    if not isinstance(payload.get("object_store_root"), str):
        raise ModelArtifactStoreError("artifact manifest object_store_root is required")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ModelArtifactStoreError("artifact manifest entries must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise ModelArtifactStoreError("artifact manifest entry must be an object")
        for field in ("logical_path", "sha256", "size_bytes", "object_path"):
            if field not in entry:
                raise ModelArtifactStoreError(
                    f"artifact manifest entry missing field: {field}"
                )
        _safe_logical_path(str(entry["logical_path"]))
        _safe_logical_path(str(entry["object_path"]))


def _safe_logical_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise ModelArtifactStoreError(f"unsafe artifact manifest path: {value}")
    if not value or value == ".":
        raise ModelArtifactStoreError("empty artifact manifest path")
    return path


def _logical_key(value: str | Path) -> str:
    return _safe_logical_path(str(value).replace(os.sep, "/")).as_posix()


def _entry_object_path(
    entry: dict[str, Any],
    manifest_dir: Path,
    payload: dict[str, Any],
) -> Path:
    object_store_root = Path(str(payload["object_store_root"]))
    root = object_store_root if object_store_root.is_absolute() else (
        manifest_dir / object_store_root
    )
    object_path = _safe_logical_path(str(entry["object_path"]))
    return root / object_path


def _object_path(object_store_root: Path, digest: str) -> Path:
    return object_store_root / digest[:2] / digest


def _relative_path(path: Path, base: Path) -> str:
    return os.path.relpath(path, base).replace(os.sep, "/")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_format(path: Path) -> str:
    suffixes = path.suffixes
    if suffixes[-2:] == [".csv", ".gz"]:
        return "csv.gz"
    if not suffixes:
        return "binary"
    return suffixes[-1].lstrip(".").lower() or "binary"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def _is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
    except ValueError:
        return False
    return True
