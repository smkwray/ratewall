"""Build TDCSim CBO holder-preference scenarios from source-backed paths."""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

HOLDER_CALIBRATION_SECURITY_TYPES = ("bills", "notes", "bonds", "tips", "frn")
TDCSIM_HOLDER_KEYS = ("Banks", "CB", "FedInternal", "Foreign", "Private", "TrustFunds")
MODEL_HOLDER_KEYS = ("Banks", "Foreign", "Private")
ZERO_HOLDER_KEYS = ("CB", "FedInternal", "TrustFunds")


@dataclass(frozen=True)
class HolderCalibrationSpec:
    """One TDCSim source-backed holder path promoted into a scenario JSON."""

    source_scenario_id: str
    output_scenario_id: str
    title: str
    label: str
    quarter: str = "2026Q1"
    effective_date: str = "2026-06-21"


def holder_preference_rows_from_source_path(
    source_path: str | Path,
    *,
    source_scenario_id: str,
    quarter: str,
    effective_date: str,
) -> list[dict[str, object]]:
    """Return TDCSim holder preference rows from a source-backed holder path.

    The source path can include central bank/Fed/trust shares. TDCSim's CBO lane
    controls Fed holdings separately, so these rows deliberately set those
    holders to zero and renormalize Banks/Foreign/Private to one.
    """

    selected = [
        row
        for row in _read_csv(source_path)
        if row.get("scenario_id") == source_scenario_id
        and row.get("quarter") == quarter
    ]
    if not selected:
        raise ValueError(
            "holder source path has no rows for "
            f"scenario_id={source_scenario_id!r}, quarter={quarter!r}"
        )

    rows: list[dict[str, object]] = []
    for security_type in HOLDER_CALIBRATION_SECURITY_TYPES:
        column = f"{security_type}_pct"
        aggregate = {
            holder: sum(
                _decimal(row.get(column, "0"))
                for row in selected
                if row.get("holder_type") == holder
            )
            for holder in MODEL_HOLDER_KEYS
        }
        denominator = sum(aggregate.values(), Decimal("0"))
        if denominator <= 0:
            raise ValueError(
                "holder source path has no positive Banks/Foreign/Private "
                f"mass for {source_scenario_id!r}, {quarter!r}, {security_type!r}"
            )
        shares = {
            holder: float(aggregate[holder] / denominator)
            for holder in MODEL_HOLDER_KEYS
        }
        shares.update({holder: 0.0 for holder in ZERO_HOLDER_KEYS})
        rows.append(
            {
                "effective_date": effective_date,
                "security_type": security_type,
                "shares": {holder: shares[holder] for holder in TDCSIM_HOLDER_KEYS},
            }
        )
    return rows


def source_backed_holder_scenario_payload(
    *,
    base_scenario: Mapping[str, Any],
    source_path: str | Path,
    spec: HolderCalibrationSpec,
) -> dict[str, Any]:
    """Build a TDCSim scenario payload using calibrated holder preferences."""

    payload = {
        "schema_version": base_scenario["schema_version"],
        "scenario_id": spec.output_scenario_id,
        "title": spec.title,
        "baseline": dict(base_scenario["baseline"]),
        "simulation": dict(base_scenario["simulation"]),
        "coupling": dict(base_scenario["coupling"]),
        "output": dict(base_scenario["output"]),
        "overrides": {
            "holder_preferences": {
                "mode": "dated_static_shares",
                "rows": holder_preference_rows_from_source_path(
                    source_path,
                    source_scenario_id=spec.source_scenario_id,
                    quarter=spec.quarter,
                    effective_date=spec.effective_date,
                ),
            }
        },
        "provenance": {
            "kind": "external_source_assumption",
            "label": spec.label,
            "external_sources": [
                {
                    "label": "TDCSim source-backed holder absorption path",
                    "locator": str(source_path),
                    "retrieved_at": f"{spec.effective_date}T00:00:00Z",
                    "sha256": _sha256(source_path),
                }
            ],
            "notes": (
                f"source_scenario_id={spec.source_scenario_id};"
                f"source_quarter={spec.quarter};"
                "combine_private_subbuckets;exclude_cb_fedinternal_trustfunds;"
                "renormalize_banks_foreign_private;"
                "tdcsim_ratewall_source_backed_input_contract_not_evidence_mode"
            ),
        },
    }
    return payload


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _decimal(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
