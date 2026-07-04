"""Materialize FSPDP component-weight source snapshots from public BEA mirrors."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence


DEFAULT_OUTPUT = Path(
    "data/raw/current_demand_gdp_share/fspdp_component_decomposition_snapshot.json"
)
DBNOMICS_SERIES_URL = (
    "https://api.db.nomics.world/v22/series/BEA/{dataset}/{series_code}"
    "?observations=1"
)


@dataclass(frozen=True)
class SeriesSpec:
    source_series_id: str
    dataset: str
    series_code: str
    component_id: str
    component_label: str
    parent_component_id: str
    parent_component_label: str
    role: str
    frequency: str
    units: str
    transform: str = "level"


SERIES_SPECS: tuple[SeriesSpec, ...] = (
    SeriesSpec(
        "GDP",
        "NIPA-T10105",
        "A191RC-Q",
        "gdp",
        "Gross domestic product",
        "gdp",
        "Gross domestic product",
        "denominator",
        "quarterly",
        "billions_of_dollars_saar",
    ),
    SeriesSpec(
        "PCDG",
        "NIPA-T20305",
        "DDURRC-Q",
        "pce_durable_goods",
        "PCE durable goods",
        "pce",
        "Personal consumption expenditures",
        "fspdp_pce_component_weight",
        "quarterly",
        "billions_of_dollars_saar",
    ),
    SeriesSpec(
        "PCND",
        "NIPA-T20305",
        "DNDGRC-Q",
        "pce_nondurable_goods",
        "PCE nondurable goods",
        "pce",
        "Personal consumption expenditures",
        "fspdp_pce_component_weight",
        "quarterly",
        "billions_of_dollars_saar",
    ),
    SeriesSpec(
        "PCES",
        "NIPA-T20305",
        "DSERRC-Q",
        "pce_services",
        "PCE services",
        "pce",
        "Personal consumption expenditures",
        "fspdp_pce_component_weight",
        "quarterly",
        "billions_of_dollars_saar",
    ),
    SeriesSpec(
        "PRFI",
        "NIPA-T50305",
        "A011RC-Q",
        "private_residential_fixed_investment",
        "Private residential fixed investment",
        "private_fixed_investment",
        "Private fixed investment",
        "fspdp_private_fixed_investment_component_weight",
        "quarterly",
        "billions_of_dollars_saar",
    ),
    SeriesSpec(
        "B009RC1Q027SBEA",
        "NIPA-T50305",
        "B009RC-Q",
        "private_nonresidential_structures",
        "Private nonresidential structures",
        "private_fixed_investment",
        "Private fixed investment",
        "fspdp_private_fixed_investment_component_weight",
        "quarterly",
        "billions_of_dollars_saar",
    ),
    SeriesSpec(
        "Y033RC1Q027SBEA",
        "NIPA-T50305",
        "Y033RC-Q",
        "private_equipment",
        "Private equipment investment",
        "private_fixed_investment",
        "Private fixed investment",
        "fspdp_private_fixed_investment_component_weight",
        "quarterly",
        "billions_of_dollars_saar",
    ),
    SeriesSpec(
        "Y001RC1Q027SBEA",
        "NIPA-T50305",
        "Y001RC-Q",
        "private_intellectual_property_products",
        "Private intellectual property products",
        "private_fixed_investment",
        "Private fixed investment",
        "fspdp_private_fixed_investment_component_weight",
        "quarterly",
        "billions_of_dollars_saar",
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _quarter_to_date(period: str) -> str:
    year, quarter = period.split("-Q")
    month = {"1": "01", "2": "04", "3": "07", "4": "10"}[quarter]
    return f"{year}-{month}-01"


def _billions_from_millions(value: object) -> str | None:
    if value in {None, "", "."}:
        return None
    try:
        decimal_value = Decimal(str(value)) / Decimal("1000")
    except (InvalidOperation, ValueError):
        return None
    return format(decimal_value.normalize(), "f")


def _records_from_dbnomics(
    spec: SeriesSpec,
    payload: dict,
) -> list[dict[str, str | None]]:
    docs = payload.get("series", {}).get("docs", [])
    if len(docs) != 1:
        raise ValueError(f"{spec.source_series_id}: expected one DB.nomics series")
    doc = docs[0]
    periods = doc.get("period", [])
    values = doc.get("value", [])
    if not isinstance(periods, list) or not isinstance(values, list):
        raise ValueError(f"{spec.source_series_id}: malformed DB.nomics payload")
    if len(periods) != len(values):
        raise ValueError(f"{spec.source_series_id}: period/value length mismatch")
    records = [
        {
            "date": _quarter_to_date(str(period)),
            "value": _billions_from_millions(value),
            "source_period": str(period),
            "source_value_millions": None if value is None else str(value),
        }
        for period, value in zip(periods, values)
    ]
    if not records:
        raise ValueError(f"{spec.source_series_id}: no observations")
    return records


def _download_series(
    spec: SeriesSpec,
    raw_dir: Path,
) -> tuple[Path, str, int, list[dict[str, str | None]], str]:
    url = DBNOMICS_SERIES_URL.format(
        dataset=spec.dataset,
        series_code=spec.series_code,
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ratewall-fspdp-component-source/24.0"},
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                raw_payload = response.read()
            payload = json.loads(raw_payload.decode("utf-8"))
            records = _records_from_dbnomics(spec, payload)
            raw_path = raw_dir / f"{spec.source_series_id}.json"
            raw_path.write_bytes(raw_payload)
            return (
                raw_path,
                _sha256_bytes(raw_payload),
                len(raw_payload),
                records,
                url,
            )
        except Exception as exc:  # pragma: no cover - exercised by network failures.
            last_error = exc
            if attempt < 3:
                time.sleep(2 * attempt)
    raise RuntimeError(f"{spec.source_series_id}: download failed") from last_error


def materialize(*, output: Path = DEFAULT_OUTPUT) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = output.parent / "fspdp_component_decomposition_dbnomics"
    raw_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = _utc_now()
    snapshots = []
    for spec in SERIES_SPECS:
        raw_path, raw_hash, raw_size, records, source_url = _download_series(
            spec,
            raw_dir,
        )
        dates = sorted(str(record["date"]) for record in records if record.get("date"))
        snapshots.append(
            {
                "metadata": {
                    "component_id": spec.component_id,
                    "component_label": spec.component_label,
                    "parent_component_id": spec.parent_component_id,
                    "parent_component_label": spec.parent_component_label,
                    "component_role": spec.role,
                    "series_id": spec.source_series_id,
                    "source_id": "dbnomics_bea_nipa_mirror",
                    "source_family": "DB.nomics mirror of BEA NIPA",
                    "source_dataset": spec.dataset,
                    "source_series_code": spec.series_code,
                    "source_url": source_url,
                    "final_url": source_url,
                    "frequency": spec.frequency,
                    "units": spec.units,
                    "source_raw_units": "millions_of_current_dollars_saar",
                    "unit_transform": "source_millions_divided_by_1000_to_billions",
                    "transform": spec.transform,
                    "retrieved_at": retrieved_at,
                    "source_release_at": dates[-1] if dates else None,
                    "raw_csv_path": str(raw_path),
                    "raw_csv_sha256": raw_hash,
                    "raw_csv_size_bytes": str(raw_size),
                    "snapshot_kind": "live_dbnomics_bea_nipa_json",
                    "note": (
                        "DB.nomics public mirror of BEA NIPA source rows for "
                        "FSPDP component decomposition weight review; not a "
                        "drag estimate."
                    ),
                },
                "records": records,
            }
        )
    output.write_text(
        json.dumps(
            {
                "schema": "ratewall.fspdp_component_decomposition_snapshot.v1",
                "retrieved_at": retrieved_at,
                "source_boundary": (
                    "bea_nipa_mirror_component_weight_inputs_only_not_drag_estimates"
                ),
                "snapshots": snapshots,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = materialize(output=args.output)
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
