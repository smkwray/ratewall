#!/usr/bin/env python3
"""Guard retired restricted-data lanes against silent reactivation."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


DEFAULT_STATUS = Path("configs/restricted_lane_status.yml")
DEFAULT_SOURCES = Path("configs/sources.yml")
DEFAULT_CLOSURE_NOTE = Path("notes/restricted_data_lanes_retired_20260607.md")

EXPECTED_LANES = {
    "beneficial_owner_final_recipient_lookthrough",
    "bank_iorb_retention_to_depositor_timing",
    "security_level_reset_financialization",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--closure-note", type=Path, default=DEFAULT_CLOSURE_NOTE)
    return parser.parse_args()


def _load_status(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    lanes = data.get("lanes")
    if not isinstance(lanes, dict):
        raise ValueError(f"{path} must contain a lanes mapping")
    lane_names = set(lanes)
    if lane_names != EXPECTED_LANES:
        raise ValueError(
            f"{path} lanes must be exactly {sorted(EXPECTED_LANES)}, got {sorted(lane_names)}"
        )
    return data


def _source_block(source_text: str, source_key: str) -> str:
    pattern = re.compile(
        rf"(?ms)^  {re.escape(source_key)}:\n(?:^    .*\n|^\s*\n)*"
    )
    match = pattern.search(source_text)
    if match is None:
        raise ValueError(f"missing source key in {DEFAULT_SOURCES}: {source_key}")
    return match.group(0)


def _has_reopen_trigger_once(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return text.count("Reopen trigger:") == 1


def main() -> int:
    args = parse_args()
    try:
        status_data = _load_status(args.status)
        source_text = args.sources.read_text(encoding="utf-8")
        if not _has_reopen_trigger_once(args.closure_note):
            raise ValueError(f"{args.closure_note} must contain exactly one Reopen trigger")

        active_markers = [
            marker.lower()
            for marker in status_data.get("forbidden_active_markers", [])
        ]
        if not active_markers:
            raise ValueError(f"{args.status} must define forbidden_active_markers")

        failures: list[str] = []
        for lane_name, lane in status_data["lanes"].items():
            lane_status = str(lane.get("status", "")).strip().lower()
            if lane_status not in {"retired", "active"}:
                failures.append(f"{lane_name}: invalid status {lane_status!r}")
                continue
            source_keys = lane.get("source_keys") or []
            if not isinstance(source_keys, list) or not source_keys:
                failures.append(f"{lane_name}: source_keys must be a non-empty list")
                continue
            for source_key in source_keys:
                block = _source_block(source_text, str(source_key)).lower()
                matched = [marker for marker in active_markers if marker in block]
                if lane_status == "retired" and matched:
                    failures.append(
                        f"{lane_name}: retired lane has active marker(s) {matched} "
                        f"in source key {source_key}"
                    )
        if failures:
            for failure in failures:
                print(failure, file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"restricted lane check failed: {exc}", file=sys.stderr)
        return 1

    print("restricted lane check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
