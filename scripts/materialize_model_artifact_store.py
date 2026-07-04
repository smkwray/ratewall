#!/usr/bin/env python3
"""Manage local RateWall model artifact manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from ratewall.databook.model_artifact_store import (
    DEFAULT_ARTIFACT_MANIFEST_FILENAME,
    ArtifactManifestStats,
    estimate_artifact_store_stats,
    materialize_artifact_manifest,
    verify_artifact_manifest,
    write_artifact_manifest,
)


def _stats_payload(stats: ArtifactManifestStats) -> dict[str, int]:
    return {
        "entry_count": stats.entry_count,
        "total_logical_size_bytes": stats.total_logical_size_bytes,
        "unique_object_count": stats.unique_object_count,
        "unique_object_size_bytes": stats.unique_object_size_bytes,
        "duplicate_savings_bytes": stats.duplicate_savings_bytes,
    }


def _print_stats(stats: ArtifactManifestStats) -> None:
    print(json.dumps(_stats_payload(stats), indent=2, sort_keys=True))


def _cmd_estimate(args: argparse.Namespace) -> int:
    _print_stats(estimate_artifact_store_stats(args.source_root))
    return 0


def _cmd_write_manifest(args: argparse.Namespace) -> int:
    _print_stats(
        write_artifact_manifest(
            args.source_root,
            object_store_root=args.object_store_root,
            manifest_path=args.manifest_path,
        )
    )
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    _print_stats(verify_artifact_manifest(args.manifest_path))
    return 0


def _cmd_materialize(args: argparse.Namespace) -> int:
    _print_stats(
        materialize_artifact_manifest(
            args.manifest_path,
            args.target_root,
            link_mode=args.link_mode,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate, store, verify, and materialize model artifact trees."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    estimate = subparsers.add_parser("estimate")
    estimate.add_argument("source_root", type=Path)
    estimate.set_defaults(func=_cmd_estimate)

    write_manifest = subparsers.add_parser("write-manifest")
    write_manifest.add_argument("source_root", type=Path)
    write_manifest.add_argument("--object-store-root", type=Path, required=True)
    write_manifest.add_argument(
        "--manifest-path",
        type=Path,
        default=Path(DEFAULT_ARTIFACT_MANIFEST_FILENAME),
    )
    write_manifest.set_defaults(func=_cmd_write_manifest)

    verify = subparsers.add_parser("verify")
    verify.add_argument("manifest_path", type=Path)
    verify.set_defaults(func=_cmd_verify)

    materialize = subparsers.add_parser("materialize")
    materialize.add_argument("manifest_path", type=Path)
    materialize.add_argument("target_root", type=Path)
    materialize.add_argument(
        "--link-mode",
        choices=("hardlink", "copy"),
        default="hardlink",
    )
    materialize.set_defaults(func=_cmd_materialize)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
