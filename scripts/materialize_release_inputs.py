#!/usr/bin/env python3
"""Materialize required runtime inputs for backend audit/source packets.

This helper is fail-closed and intentionally narrow. It ensures that a top-level
source/audit tree has the runtime inputs required by the reproducibility tests:

* `data/raw/ratewall_snapshot.json`
* release-archived `data/raw/**` source inputs used by fresh databook builds
* the vendored sibling calibration extracts used by fresh databook builds

It does not download new data and does not change any model assumptions.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "outputs" / "release" / "ratewall_release_23_0_source_archive.zip"
SNAPSHOT = ROOT / "data" / "raw" / "ratewall_snapshot.json"

VENDOR_SPECS = (
    (
        ROOT.parent / "tdcmix" / "data" / "processed" / "holder_absorption_panel.csv",
        ROOT
        / "data"
        / "raw"
        / "ratewall_sibling_calibration"
        / "tdcmix_holder_absorption_panel.csv",
    ),
    (
        ROOT.parent / "tdcpass" / "data" / "derived" / "quarterly_panel.csv",
        ROOT
        / "data"
        / "raw"
        / "ratewall_sibling_calibration"
        / "tdcpass_quarterly_panel.csv",
    ),
    (
        ROOT.parent / "tdcest" / "data" / "processed" / "tdc_estimates.csv",
        ROOT
        / "data"
        / "raw"
        / "ratewall_sibling_calibration"
        / "tdcest_tdc_estimates.csv",
    ),
)


def _ensure_snapshot() -> None:
    archive_available = _ensure_archived_raw_inputs()
    if SNAPSHOT.exists():
        return
    if not archive_available:
        raise SystemExit(
            "missing both data/raw/ratewall_snapshot.json and the release source archive"
        )
    raise SystemExit("release source archive does not contain data/raw/ratewall_snapshot.json")


def _ensure_archived_raw_inputs() -> bool:
    if not ARCHIVE.exists():
        return False
    with zipfile.ZipFile(ARCHIVE) as archive:
        for member in archive.namelist():
            if not member.startswith("data/raw/") or member.endswith("/"):
                continue
            relative = Path(member)
            if relative.is_absolute() or ".." in relative.parts:
                raise SystemExit(f"unsafe release source archive member: {member}")
            target = ROOT / relative
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
    return True


def _ensure_vendors() -> None:
    missing = []
    for sibling_path, vendor_path in VENDOR_SPECS:
        if vendor_path.exists():
            continue
        if sibling_path.exists():
            vendor_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sibling_path, vendor_path)
            continue
        missing.append((sibling_path, vendor_path))
    if not missing:
        return
    formatted = "\n".join(
        f"- sibling: {source}\n  vendor:  {destination}"
        for source, destination in missing
    )
    raise SystemExit(
        "required sibling calibration inputs are missing; cannot mark the "
        "backend stage reproducible:\n"
        + formatted
    )


def main() -> int:
    _ensure_snapshot()
    _ensure_vendors()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
