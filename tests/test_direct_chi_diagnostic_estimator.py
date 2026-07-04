from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.direct_chi_diagnostic_estimator import (
    DIRECT_CHI_DIAGNOSTIC_ESTIMATOR_FIELDS,
    DirectChiDiagnosticEstimatorPaths,
    direct_chi_diagnostic_estimator_rows,
    direct_chi_diagnostic_source_candidate_rows,
    write_direct_chi_diagnostic_estimator_outputs,
)


def test_diagnostic_estimator_computes_but_admits_no_floor(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, quarter_count=18, treatment_count=16)

    rows = direct_chi_diagnostic_estimator_rows(paths=paths)

    assert len(rows) == 12
    assert {field for row in rows for field in row} == set(
        DIRECT_CHI_DIAGNOSTIC_ESTIMATOR_FIELDS
    )
    assert {row["admissibility_status"] for row in rows} == {
        "not_admitted_diagnostic_only_no_identification"
    }
    assert {row["reports_chi_lower_bound"] for row in rows} == {"false"}
    assert {row["reports_beta_chi_lower_bound"] for row in rows} == {"false"}
    assert all(row["coefficient"] for row in rows)
    assert all(row["standard_error"] for row in rows)
    assert all("canonical_headline_promotion" in row["blocked_use"] for row in rows)


def test_diagnostic_source_candidates_are_not_direct_evidence(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path, quarter_count=18, treatment_count=16)
    rows = direct_chi_diagnostic_estimator_rows(paths=paths)

    candidates = direct_chi_diagnostic_source_candidate_rows(rows)

    assert len(candidates) == len(rows)
    assert {row["source_family"] for row in candidates} == {
        "ratewall_direct_chi_diagnostic_estimator"
    }
    assert {row["has_materialized_tdc_treatment"] for row in candidates} == {"true"}
    assert {row["has_current_demand_outcome"] for row in candidates} == {"true"}
    assert {row["has_tdc_ex_overlap_treatment"] for row in candidates} == {"false"}
    assert {row["has_identification_strategy"] for row in candidates} == {"false"}
    assert {row["reports_chi_lower_bound"] for row in candidates} == {"false"}
    assert {row["reported_chi_lower_bound"] for row in candidates} == {""}


def test_diagnostic_estimator_blocks_short_samples(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, quarter_count=8, treatment_count=6)

    rows = direct_chi_diagnostic_estimator_rows(paths=paths)

    assert len(rows) == 12
    assert {row["admissibility_status"] for row in rows} == {
        "not_admitted_blocked_diagnostic_estimator"
    }
    assert {row["coefficient"] for row in rows} == {""}
    assert {row["admissibility_obstacle"] for row in rows} == {
        "insufficient_overlap_sample_for_diagnostic_ols"
    }


def test_diagnostic_outputs_write_csv_and_memo(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, quarter_count=18, treatment_count=16)
    rows = direct_chi_diagnostic_estimator_rows(paths=paths)

    outputs = write_direct_chi_diagnostic_estimator_outputs(tmp_path / "out", rows=rows)

    assert outputs["diagnostic_estimator_csv"].read_text(
        encoding="utf-8"
    ).startswith("direct_chi_diagnostic_estimator_row_id,")
    memo = outputs["diagnostic_estimator_memo_md"].read_text(encoding="utf-8")
    assert "does not admit" in memo
    assert "Estimator rows: `12`." in memo
    assert "Admitted lower-bound rows: `0`." in memo


def _write_fixture(
    tmp_path: Path,
    *,
    quarter_count: int,
    treatment_count: int,
) -> DirectChiDiagnosticEstimatorPaths:
    current = tmp_path / "current"
    current.mkdir()
    tdc_path = tmp_path / "tdcest_tdc_estimates.csv"
    quarters = _quarters(quarter_count)
    treatments = _quarters(treatment_count)
    treatment_fields = [
        "tdc_tier2_interest_corrected_bank_only_ru_flow",
        "tdc_tier2_canonical_depository_institution_mmf_rrp_prop_ru_flow",
        "tdc_tier3_fiscal_corrected_bank_only_ru_flow",
    ]
    with tdc_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", *treatment_fields])
        writer.writeheader()
        for index, date in enumerate(treatments):
            writer.writerow(
                {
                    "date": date,
                    treatment_fields[0]: str(900 + index * 20),
                    treatment_fields[1]: str(1000 + index * 30),
                    treatment_fields[2]: str(1100 + index * 40),
                }
            )
    _write_series(current / "GDP.csv", "GDP", quarters, base=20000, step=250)
    _write_series(current / "PCEC.csv", "PCEC", quarters, base=13000, step=175)
    _write_series(
        current / "LA0000031Q027SBEA.csv",
        "LA0000031Q027SBEA",
        quarters,
        base=9500,
        step=140,
    )
    return DirectChiDiagnosticEstimatorPaths(
        tdcest_estimates_path=tdc_path,
        local_current_demand_dir=current,
    )


def _write_series(
    path: Path,
    field: str,
    dates: list[str],
    *,
    base: int,
    step: int,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["observation_date", field])
        writer.writeheader()
        for index, date in enumerate(dates):
            writer.writerow({"observation_date": date, field: str(base + index * step)})


def _quarters(count: int) -> list[str]:
    dates: list[str] = []
    year = 2020
    month = 3
    for _ in range(count):
        dates.append(f"{year:04d}-{month:02d}-31")
        month += 3
        if month > 12:
            year += 1
            month = 3
    return dates
