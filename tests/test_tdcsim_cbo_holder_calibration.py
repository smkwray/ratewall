from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ratewall.databook.tdcsim_cbo_holder_calibration import (
    HOLDER_CALIBRATION_SECURITY_TYPES,
    HolderCalibrationSpec,
    holder_preference_rows_from_source_path,
    source_backed_holder_scenario_payload,
)


def _write_source_path(path: Path) -> None:
    fieldnames = [
        "scenario_id",
        "quarter",
        "holder_type",
        "holder_subbucket",
        "bills_pct",
        "notes_pct",
        "bonds_pct",
        "tips_pct",
        "frn_pct",
    ]
    rows = [
        {
            "scenario_id": "current_mix_baseline",
            "quarter": "2026Q1",
            "holder_type": "Banks",
            "holder_subbucket": "",
            "bills_pct": "0.10",
            "notes_pct": "0.20",
            "bonds_pct": "0.20",
            "tips_pct": "0.20",
            "frn_pct": "0.20",
        },
        {
            "scenario_id": "current_mix_baseline",
            "quarter": "2026Q1",
            "holder_type": "CB",
            "holder_subbucket": "",
            "bills_pct": "0.20",
            "notes_pct": "0.10",
            "bonds_pct": "0.10",
            "tips_pct": "0.10",
            "frn_pct": "0.10",
        },
        {
            "scenario_id": "current_mix_baseline",
            "quarter": "2026Q1",
            "holder_type": "Foreign",
            "holder_subbucket": "",
            "bills_pct": "0.30",
            "notes_pct": "0.30",
            "bonds_pct": "0.30",
            "tips_pct": "0.30",
            "frn_pct": "0.30",
        },
        {
            "scenario_id": "current_mix_baseline",
            "quarter": "2026Q1",
            "holder_type": "Private",
            "holder_subbucket": "domestic_nonbank_deposit_funded",
            "bills_pct": "0.25",
            "notes_pct": "0.20",
            "bonds_pct": "0.20",
            "tips_pct": "0.20",
            "frn_pct": "0.20",
        },
        {
            "scenario_id": "current_mix_baseline",
            "quarter": "2026Q1",
            "holder_type": "Private",
            "holder_subbucket": "mmf_cash_fund_route",
            "bills_pct": "0.15",
            "notes_pct": "0.20",
            "bonds_pct": "0.20",
            "tips_pct": "0.20",
            "frn_pct": "0.20",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_holder_preference_rows_combine_private_and_exclude_cb(tmp_path: Path) -> None:
    path = tmp_path / "holder_path.csv"
    _write_source_path(path)

    rows = holder_preference_rows_from_source_path(
        path,
        source_scenario_id="current_mix_baseline",
        quarter="2026Q1",
        effective_date="2026-06-21",
    )

    assert [row["security_type"] for row in rows] == list(
        HOLDER_CALIBRATION_SECURITY_TYPES
    )
    bill_shares = rows[0]["shares"]
    assert bill_shares["CB"] == 0.0
    assert bill_shares["FedInternal"] == 0.0
    assert bill_shares["TrustFunds"] == 0.0
    assert bill_shares["Banks"] == pytest.approx(0.125)
    assert bill_shares["Foreign"] == pytest.approx(0.375)
    assert bill_shares["Private"] == pytest.approx(0.5)
    for row in rows:
        assert sum(row["shares"].values()) == pytest.approx(1.0)


def test_source_backed_holder_scenario_payload_keeps_baseline_contract(
    tmp_path: Path,
) -> None:
    path = tmp_path / "holder_path.csv"
    _write_source_path(path)
    base = {
        "schema_version": "tdcsim_cbo_scenario_v1",
        "scenario_id": "cbo_baseline_noop_v1",
        "title": "Baseline",
        "baseline": {"package_id": "pkg"},
        "simulation": {"start_date": "2026-06-21", "end_date": "2027-09-30"},
        "coupling": {"primary_deficit_to_debt_target": "independent_no_plug"},
        "output": {"profile": "compact"},
    }

    payload = source_backed_holder_scenario_payload(
        base_scenario=base,
        source_path=path,
        spec=HolderCalibrationSpec(
            source_scenario_id="current_mix_baseline",
            output_scenario_id="tdcsim_holder_current_mix_source_v1",
            title="Source-backed current holder mix",
            label="Current holder mix",
        ),
    )

    assert payload["scenario_id"] == "tdcsim_holder_current_mix_source_v1"
    assert payload["baseline"] == {"package_id": "pkg"}
    assert payload["overrides"]["holder_preferences"]["mode"] == "dated_static_shares"
    assert payload["provenance"]["kind"] == "external_source_assumption"
    assert payload["provenance"]["external_sources"][0]["label"] == (
        "TDCSim source-backed holder absorption path"
    )
    assert len(payload["provenance"]["external_sources"][0]["sha256"]) == 64
    assert "source_scenario_id=current_mix_baseline" in payload["provenance"]["notes"]
    assert "renormalize_banks_foreign_private" in payload["provenance"]["notes"]


def test_holder_preference_rows_fail_when_source_scenario_missing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "holder_path.csv"
    _write_source_path(path)

    with pytest.raises(ValueError, match="has no rows"):
        holder_preference_rows_from_source_path(
            path,
            source_scenario_id="missing",
            quarter="2026Q1",
            effective_date="2026-06-21",
        )
