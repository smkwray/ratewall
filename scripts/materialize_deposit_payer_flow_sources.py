#!/usr/bin/env python3
"""Materialize official D1 deposit payer-flow source panels."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.deposit_payer_flow_source_materializer import (
    DEFAULT_RAW_DIR,
    materialize_deposit_payer_flow_sources,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Raw source directory where official archives and panels are written.",
    )
    parser.add_argument(
        "--report-date",
        default="03/31/2026",
        help="Common FFIEC/NCUA report date, e.g. 03/31/2026.",
    )
    parser.add_argument(
        "--ffiec-archive",
        default=None,
        help="Optional existing FFIEC CDR bulk ZIP to parse instead of downloading.",
    )
    parser.add_argument(
        "--ncua-archive",
        default=None,
        help="Optional existing NCUA quarterly ZIP to parse instead of downloading.",
    )
    args = parser.parse_args()

    outputs = materialize_deposit_payer_flow_sources(
        raw_dir=Path(args.raw_dir),
        report_date=args.report_date,
        ffiec_archive=Path(args.ffiec_archive) if args.ffiec_archive else None,
        ncua_archive=Path(args.ncua_archive) if args.ncua_archive else None,
    )
    print(f"ffiec_archive: {outputs.ffiec_archive}")
    print(f"ncua_archive: {outputs.ncua_archive}")
    print(f"ffiec_panel: {outputs.ffiec_panel}")
    print(f"ncua_panel: {outputs.ncua_panel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
