from __future__ import annotations

import csv
import gzip
from pathlib import Path

from ratewall.databook.direct_beta_chi_panel import (
    DIRECT_BETA_CHI_PANEL_FIELDS,
    DIRECT_BETA_CHI_PANEL_STATUS_FIELDS,
    DirectBetaChiPanelPaths,
    direct_beta_chi_panel_rows,
    direct_beta_chi_panel_source_candidate_rows,
    direct_beta_chi_panel_status_rows,
    write_direct_beta_chi_panel_outputs,
)


def test_direct_beta_chi_panel_matches_tdc_treatment_to_observed_outcomes(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path, treatment_quarter="2026Q1")

    rows = direct_beta_chi_panel_rows(paths=paths, horizons=(0,))

    assert {field for row in rows for field in row} == set(
        DIRECT_BETA_CHI_PANEL_FIELDS
    )
    assert len(rows) == 2
    pcec = [row for row in rows if row["outcome_series_key"] == "PCEC"][0]
    assert pcec["scenario_id"] == "scenario_a"
    assert pcec["quarter"] == "2026Q1"
    assert pcec["period_row_count"] == "2"
    assert pcec["tdc_change_ex_overlap_bil"] == "12"
    assert pcec["gdp_bil"] == "100"
    assert pcec["tdc_change_ex_overlap_share_of_gdp"] == "0.12"
    assert pcec["outcome_change_share_of_gdp"] == "0.02"
    assert pcec["matched_outcome_status"] == "matched_observed_outcome"
    assert pcec["identification_status"] == (
        "missing_no_external_or_predetermined_variation"
    )
    assert pcec["admission_status"] == "not_admitted_candidate_panel_only"


def test_direct_beta_chi_panel_status_blocks_without_identification(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path, treatment_quarter="2026Q1")
    rows = direct_beta_chi_panel_rows(paths=paths, horizons=(0,))

    status = direct_beta_chi_panel_status_rows(rows, paths=paths)

    assert {field for row in status for field in row} == set(
        DIRECT_BETA_CHI_PANEL_STATUS_FIELDS
    )
    assert status[0]["treatment_quarter_count"] == "1"
    assert status[0]["candidate_panel_rows"] == "2"
    assert status[0]["matched_panel_rows"] == "2"
    assert status[0]["identified_panel_rows"] == "0"
    assert status[0]["panel_status"] == "blocked_missing_identification_strategy"

    candidates = direct_beta_chi_panel_source_candidate_rows(status)
    assert len(candidates) == 1
    assert candidates[0]["source_family"] == "ratewall_direct_beta_chi_candidate_panel"
    assert candidates[0]["has_tdc_ex_overlap_treatment"] == "true"
    assert candidates[0]["has_current_demand_outcome"] == "true"
    assert candidates[0]["has_identification_strategy"] == "false"
    assert candidates[0]["admissibility_status"] == (
        "not_admitted_missing_identification_strategy"
    )


def test_direct_beta_chi_panel_status_blocks_forecast_without_observed_outcome(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path, treatment_quarter="2026Q3")
    rows = direct_beta_chi_panel_rows(paths=paths, horizons=(0,))

    status = direct_beta_chi_panel_status_rows(rows, paths=paths)

    assert status[0]["treatment_quarter_count"] == "1"
    assert status[0]["candidate_panel_rows"] == "2"
    assert status[0]["matched_panel_rows"] == "0"
    assert status[0]["panel_status"] == "blocked_no_observed_outcome_match"
    assert status[0]["estimator_blocker"] == (
        "tdcsim_forecast_treatment_quarters_do_not_overlap_observed_outcomes"
    )


def test_direct_beta_chi_panel_outputs_write_csvs(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, treatment_quarter="2026Q1")
    rows = direct_beta_chi_panel_rows(paths=paths, horizons=(0,))
    status = direct_beta_chi_panel_status_rows(rows, paths=paths)

    outputs = write_direct_beta_chi_panel_outputs(
        tmp_path / "out",
        panel_rows=rows,
        status_rows=status,
    )

    assert outputs["direct_beta_chi_panel_csv"].read_text(
        encoding="utf-8"
    ).startswith("direct_beta_chi_panel_row_id,")
    assert outputs["direct_beta_chi_panel_status_csv"].read_text(
        encoding="utf-8"
    ).startswith("direct_beta_chi_panel_status_row_id,")


def _write_fixture(tmp_path: Path, *, treatment_quarter: str) -> DirectBetaChiPanelPaths:
    tdc_root = tmp_path / "tdcsim"
    output_root = tdc_root / "outputs"
    output_root.mkdir(parents=True)
    current = tmp_path / "current"
    current.mkdir()
    if treatment_quarter == "2026Q1":
        period_rows = [
            {
                "scenario_id": "scenario_a",
                "period_end": "2026-01-15",
                "tdc_change_ex_overlap_bil": "5",
            },
            {
                "scenario_id": "scenario_a",
                "period_end": "2026-02-15",
                "tdc_change_ex_overlap_bil": "7",
            },
        ]
    else:
        period_rows = [
            {
                "scenario_id": "scenario_a",
                "period_end": "2026-07-15",
                "tdc_change_ex_overlap_bil": "5",
            }
        ]
    _write_gzip_csv(output_root / "tdcsim_period_tdc_summary.csv.gz", period_rows)
    _write_series(current / "GDP.csv", "GDP", [100, 110, 120])
    _write_series(current / "PCEC.csv", "PCEC", [60, 62, 65])
    _write_series(current / "LA0000031Q027SBEA.csv", "LA0000031Q027SBEA", [80, 83, 87])
    return DirectBetaChiPanelPaths(
        tdcsim_period_tdc_dir=tdc_root,
        local_current_demand_dir=current,
    )


def _write_series(path: Path, field: str, values: list[int]) -> None:
    dates = ["2026-01-01", "2026-04-01", "2026-07-01"]
    rows = [
        {"observation_date": date, field: str(value)}
        for date, value in zip(dates, values, strict=True)
    ]
    _write_csv(path, rows)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_gzip_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
