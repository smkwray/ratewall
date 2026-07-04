#!/usr/bin/env python3
"""Hash keeper CSVs for Phase-4 byte-identity checks."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import yaml


DEFAULT_KEEP_MANIFEST = Path("configs/ratewall_keep_tables_20260607.yml")
HASH_FIELDS = ["filename", "sha256", "byte_count", "row_count", "header"]


def keeper_names(manifest_path: Path) -> list[str]:
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "ratewall.keep_tables.v1":
        raise ValueError(f"{manifest_path} must use schema ratewall.keep_tables.v1")
    names: set[str] = set()
    for entries in payload["tiers"].values():
        for entry in entries:
            names.add(str(entry["output_name"]))
    return sorted(names)


def hash_rows(
    *,
    output_dir: Path,
    manifest_path: Path,
    allow_missing: bool = False,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    missing: list[str] = []
    for name in keeper_names(manifest_path):
        path = output_dir / "tables" / name
        if not path.exists():
            missing.append(name)
            if allow_missing:
                rows.append(
                    {
                        "filename": name,
                        "sha256": "",
                        "byte_count": "0",
                        "row_count": "0",
                        "header": "",
                    }
                )
            continue
        data = path.read_bytes()
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            row_count = sum(1 for _ in reader)
        rows.append(
            {
                "filename": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "byte_count": str(len(data)),
                "row_count": str(row_count),
                "header": ",".join(header),
            }
        )
    if missing and not allow_missing:
        raise FileNotFoundError("missing keeper tables: " + ", ".join(missing))
    return rows


def _rows_by_filename(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["filename"]: row for row in rows}


def compare_hash_rows(
    left_rows: list[dict[str, str]],
    right_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    left_by_name = _rows_by_filename(left_rows)
    right_by_name = _rows_by_filename(right_rows)
    names = sorted(set(left_by_name) | set(right_by_name))
    mismatches: list[dict[str, str]] = []
    for name in names:
        left = left_by_name.get(name, {})
        right = right_by_name.get(name, {})
        if left != right:
            mismatches.append(
                {
                    "filename": name,
                    "left_sha256": left.get("sha256", ""),
                    "right_sha256": right.get("sha256", ""),
                    "left_byte_count": left.get("byte_count", ""),
                    "right_byte_count": right.get("byte_count", ""),
                    "left_row_count": left.get("row_count", ""),
                    "right_row_count": right.get("row_count", ""),
                    "left_header": left.get("header", ""),
                    "right_header": right.get("header", ""),
                }
            )
    return mismatches


def check_repeat_hashes(
    *,
    output_dir: Path,
    compare_to: Path,
    manifest_path: Path,
) -> dict[str, object]:
    left_rows = hash_rows(output_dir=output_dir, manifest_path=manifest_path)
    right_rows = hash_rows(output_dir=compare_to, manifest_path=manifest_path)
    mismatches = compare_hash_rows(left_rows, right_rows)
    if mismatches:
        raise RuntimeError(
            "keeper hash mismatch: "
            + ", ".join(row["filename"] for row in mismatches)
        )
    return {"table_count": len(left_rows), "mismatches": mismatches}


def write_tsv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=HASH_FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--keep-manifest", type=Path, default=DEFAULT_KEEP_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args(argv)

    if args.compare_to:
        result = check_repeat_hashes(
            output_dir=args.output_dir,
            compare_to=args.compare_to,
            manifest_path=args.keep_manifest,
        )
        print(f"keeper hash repeat passed: {result['table_count']} tables")
        return 0

    rows = hash_rows(
        output_dir=args.output_dir,
        manifest_path=args.keep_manifest,
        allow_missing=args.allow_missing,
    )
    if args.output:
        write_tsv(rows, args.output)
        print(f"wrote {args.output} ({len(rows)} rows)")
    else:
        writer = csv.DictWriter(
            __import__("sys").stdout,
            fieldnames=HASH_FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
