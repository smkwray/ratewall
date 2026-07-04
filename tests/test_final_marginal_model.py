from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path

import pytest

from ratewall.databook.final_marginal_model import (
    EXPOSURE_DIAGNOSTICS_SNAPSHOT_FIELDS,
    FINAL_MARGINAL_READINESS_FIELDS,
    FINAL_MARGINAL_RW_RATIO_FIELDS,
    FinalMarginalModelError,
    exposure_diagnostics_snapshot_rows,
    final_marginal_readiness_rows,
    final_marginal_rw_ratio_rows,
    validate_final_marginal_rw_ratio_rows,
    write_final_marginal_model_outputs,
)


def test_final_marginal_model_fails_closed_without_selected_n(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, selected_n=False)

    rows = final_marginal_rw_ratio_rows(
        selected_numerator_path=paths["n"],
        denominator_path=paths["d"],
    )
    readiness = final_marginal_readiness_rows(rows)
    diagnostics = exposure_diagnostics_snapshot_rows()

    assert {field for row in rows for field in row} == set(FINAL_MARGINAL_RW_RATIO_FIELDS)
    assert rows[0]["final_rw_m_selected"] == "false"
    assert rows[0]["final_rw_m"] == ""
    assert "selected_marginal_n" in rows[0]["blocked_reason"]
    assert {field for row in readiness for field in row} == set(
        FINAL_MARGINAL_READINESS_FIELDS
    )
    assert {field for row in diagnostics for field in row} == set(
        EXPOSURE_DIAGNOSTICS_SNAPSHOT_FIELDS
    )


def test_final_marginal_model_can_select_when_n_and_d_pass(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, selected_n=True)

    rows = final_marginal_rw_ratio_rows(
        selected_numerator_path=paths["n"],
        denominator_path=paths["d"],
    )

    assert rows[0]["final_rw_m_selected"] == "true"
    assert rows[0]["final_rw_m"] == "0.25"
    assert rows[0]["demand_conversion_case"] == "central"


def test_final_marginal_outputs_are_written(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, selected_n=False)
    rows = final_marginal_rw_ratio_rows(
        selected_numerator_path=paths["n"],
        denominator_path=paths["d"],
    )
    outputs = write_final_marginal_model_outputs(
        tmp_path / "out",
        ratio_rows=rows,
        readiness_rows=final_marginal_readiness_rows(rows),
        diagnostic_rows=exposure_diagnostics_snapshot_rows(),
    )

    assert outputs["ratio_snapshot_csv"].read_text(encoding="utf-8").startswith(
        "final_marginal_rw_row_id,"
    )


def test_bad_final_marginal_model_rejects_nonselected_ratio(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, selected_n=False)
    rows = final_marginal_rw_ratio_rows(
        selected_numerator_path=paths["n"],
        denominator_path=paths["d"],
    )
    bad = deepcopy(rows)
    bad[0]["final_rw_m"] = "0.1"

    with pytest.raises(FinalMarginalModelError, match="nonselected"):
        validate_final_marginal_rw_ratio_rows(bad)


def _write_fixtures(tmp_path: Path, *, selected_n: bool) -> dict[str, Path]:
    n = tmp_path / "n.csv"
    _write_csv(
        n,
        [
            {
                "period_object": "forecast",
                "period": "2036",
                "horizon": "annual_h1_100bp_year",
                "state_id": "forecast_state::2036::plus",
                "shock_path_id": "plus_100bp_year",
                "demand_conversion_case": "central",
                "selected_marginal_n_allowed": str(selected_n).lower(),
                "selected_marginal_n_bil": "2" if selected_n else "",
            }
        ],
    )
    d = tmp_path / "d.csv"
    _write_csv(
        d,
        [
            {
                "period": "2036",
                "horizon": "annual_h1_100bp_year",
                "state_id": "forecast_state::2036::plus",
                "shock_path_id": "plus_100bp_year",
                "selected_marginal_D": "true",
                "marginal_denominator_bil": "8",
            }
        ],
    )
    return {"n": n, "d": d}


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
