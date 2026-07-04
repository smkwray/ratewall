#!/usr/bin/env python3
"""Acquire official FRED/BEA component source CSVs for FSPDP review."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = (
    ROOT
    / "data"
    / "raw"
    / "current_demand_gdp_share"
    / "fspdp_official_component_sources"
    / "fred_csv"
)
MANIFEST_PATH = RAW_DIR.parent / "fspdp_official_component_sources_manifest.json"


@dataclass(frozen=True)
class SeriesSpec:
    component_id: str
    component_label: str
    parent_component_id: str
    measure_role: str
    series_id: str
    source_table_or_family: str
    expected_unit: str
    frequency: str


SERIES_SPECS = [
    SeriesSpec(
        "pce_durable_goods",
        "PCE durable goods",
        "pce",
        "current_dollar_saar",
        "PCDG",
        "BEA NIPA PCE major type / FRED",
        "Billions of Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "pce_durable_goods",
        "PCE durable goods",
        "pce",
        "real_quantity_index",
        "DDURRA3M086SBEA",
        "BEA NIPA real PCE major type / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "monthly",
    ),
    SeriesSpec(
        "pce_durable_goods",
        "PCE durable goods",
        "pce",
        "price_index",
        "DDURRG3M086SBEA",
        "BEA NIPA PCE major type price index / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "monthly",
    ),
    SeriesSpec(
        "pce_nondurable_goods",
        "PCE nondurable goods",
        "pce",
        "current_dollar_saar",
        "PCND",
        "BEA NIPA PCE major type / FRED",
        "Billions of Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "pce_nondurable_goods",
        "PCE nondurable goods",
        "pce",
        "real_quantity_index",
        "DNDGRA3M086SBEA",
        "BEA NIPA real PCE major type / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "monthly",
    ),
    SeriesSpec(
        "pce_nondurable_goods",
        "PCE nondurable goods",
        "pce",
        "price_index",
        "DNDGRG3M086SBEA",
        "BEA NIPA PCE major type price index / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "monthly",
    ),
    SeriesSpec(
        "pce_services",
        "PCE services",
        "pce",
        "current_dollar_saar",
        "PCES",
        "BEA NIPA PCE major type / FRED",
        "Billions of Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "pce_services",
        "PCE services",
        "pce",
        "real_quantity_index",
        "DSERRA3M086SBEA",
        "BEA NIPA real PCE major type / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "monthly",
    ),
    SeriesSpec(
        "pce_services",
        "PCE services",
        "pce",
        "price_index",
        "DSERRG3M086SBEA",
        "BEA NIPA PCE major type price index / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "monthly",
    ),
    SeriesSpec(
        "private_residential_fixed_investment",
        "Private residential fixed investment",
        "private_fixed_investment",
        "current_dollar_saar",
        "PRFI",
        "BEA NIPA private fixed investment / FRED",
        "Billions of Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_residential_fixed_investment",
        "Private residential fixed investment",
        "private_fixed_investment",
        "real_chained_dollars",
        "PRFIC1",
        "BEA NIPA real private residential fixed investment / FRED",
        "Billions of Chained 2017 Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_residential_fixed_investment",
        "Private residential fixed investment",
        "private_fixed_investment",
        "price_index",
        "B011RG3Q086SBEA",
        "BEA NIPA residential fixed investment price index / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_nonresidential_structures",
        "Private nonresidential structures",
        "private_fixed_investment",
        "current_dollar_saar",
        "B009RC1Q027SBEA",
        "BEA NIPA table 5.3.5 / FRED",
        "Billions of Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_nonresidential_structures",
        "Private nonresidential structures",
        "private_fixed_investment",
        "real_chained_dollars",
        "B009RX1Q020SBEA",
        "BEA NIPA table 5.3.6 / FRED",
        "Billions of Chained 2017 Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_nonresidential_structures",
        "Private nonresidential structures",
        "private_fixed_investment",
        "price_index",
        "B009RG3Q086SBEA",
        "BEA NIPA table 5.3.4 / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_equipment",
        "Private equipment investment",
        "private_fixed_investment",
        "current_dollar_saar",
        "Y033RC1Q027SBEA",
        "BEA NIPA table 5.3.5 / FRED",
        "Billions of Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_equipment",
        "Private equipment investment",
        "private_fixed_investment",
        "real_chained_dollars",
        "Y033RX1Q020SBEA",
        "BEA NIPA table 5.3.6 / FRED",
        "Billions of Chained 2017 Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_equipment",
        "Private equipment investment",
        "private_fixed_investment",
        "price_index",
        "Y033RG3Q086SBEA",
        "BEA NIPA table 5.3.4 / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_intellectual_property_products",
        "Private intellectual property products",
        "private_fixed_investment",
        "current_dollar_saar",
        "Y001RC1Q027SBEA",
        "BEA NIPA table 5.3.5 / FRED",
        "Billions of Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_intellectual_property_products",
        "Private intellectual property products",
        "private_fixed_investment",
        "real_chained_dollars",
        "Y001RX1Q020SBEA",
        "BEA NIPA table 5.3.6 / FRED",
        "Billions of Chained 2017 Dollars, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
    SeriesSpec(
        "private_intellectual_property_products",
        "Private intellectual property products",
        "private_fixed_investment",
        "price_index",
        "Y001RG3Q086SBEA",
        "BEA NIPA table 5.3.4 / FRED",
        "Index 2017=100, Seasonally Adjusted Annual Rate",
        "quarterly",
    ),
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(spec: SeriesSpec) -> tuple[str, str, Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output = RAW_DIR / f"{spec.series_id}.csv"
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={spec.series_id}"
    tmp = output.with_suffix(".csv.tmp")
    try:
        completed = subprocess.run(
            [
                "curl",
                "--http1.1",
                "-L",
                "--fail",
                "--silent",
                "--show-error",
                "--max-time",
                "20",
                "-o",
                str(tmp),
                url,
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            if output.exists():
                return (
                    f"blocked_download_error_using_existing_file:curl_{completed.returncode}",
                    url,
                    output,
                )
            return f"blocked_download_error:curl_{completed.returncode}", url, output
        payload = tmp.read_bytes()
        if not payload.startswith(b"observation_date,"):
            tmp.unlink(missing_ok=True)
            return "blocked_unexpected_fred_csv_payload", url, output
        tmp.replace(output)
        return "downloaded", url, output
    except (OSError, subprocess.SubprocessError) as exc:
        tmp.unlink(missing_ok=True)
        if output.exists():
            return f"blocked_download_error_using_existing_file:{type(exc).__name__}", url, output
        return f"blocked_download_error:{type(exc).__name__}", url, output


def _observation_bounds(path: Path, series_id: str) -> tuple[int, str, str]:
    if not path.exists():
        return 0, "", ""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("observation_date") and row.get(series_id) not in {"", "."}
        ]
    if not rows:
        return 0, "", ""
    return len(rows), rows[0]["observation_date"], rows[-1]["observation_date"]


def main() -> None:
    manifest = []
    for spec in SERIES_SPECS:
        status, url, path = _download(spec)
        count, first, last = _observation_bounds(path, spec.series_id)
        manifest.append(
            {
                "component_id": spec.component_id,
                "component_label": spec.component_label,
                "parent_component_id": spec.parent_component_id,
                "measure_role": spec.measure_role,
                "series_id": spec.series_id,
                "source_table_or_family": spec.source_table_or_family,
                "expected_unit": spec.expected_unit,
                "frequency": spec.frequency,
                "source_url": url,
                "raw_source_path": str(path.relative_to(ROOT)),
                "raw_source_sha256": _sha256(path) if path.exists() else "",
                "raw_source_size_bytes": str(path.stat().st_size) if path.exists() else "",
                "source_record_count": str(count),
                "first_observation_date": first,
                "last_observation_date": last,
                "download_attempt_status": status,
            }
        )
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest": str(MANIFEST_PATH.relative_to(ROOT)),
                "series_count": len(manifest),
                "downloaded": sum(
                    1 for row in manifest if row["download_attempt_status"] == "downloaded"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
