from __future__ import annotations

import csv
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.databook.marginal_denominator import (
    DENOMINATOR_STATE_MULTIPLIER_FIELDS,
    MARGINAL_DENOMINATOR_AUDIT_FIELDS,
    MARGINAL_DENOMINATOR_SEED_FIELDS,
    MARGINAL_DENOMINATOR_SURFACE_FIELDS,
    RATE_ENVIRONMENT_EXPOSURE_DIAGNOSTIC_FIELDS,
    MarginalDenominatorError,
    denominator_state_multiplier_rows,
    marginal_denominator_audit_rows,
    marginal_denominator_surface_rows,
    rate_environment_exposure_diagnostic_rows,
    validate_denominator_state_multiplier,
    validate_marginal_denominator_surface,
    write_marginal_denominator_outputs,
)


def test_marginal_denominator_formula_and_selected_base_case(tmp_path: Path) -> None:
    gdp_path, current_path, historical_path = _write_fixtures(tmp_path)

    rows = marginal_denominator_surface_rows(
        gdp_path=gdp_path,
        current_benchmark_path=current_path,
        historical_denominator_path=historical_path,
    )

    assert {field for row in rows for field in row} == set(
        MARGINAL_DENOMINATOR_SURFACE_FIELDS
    )
    selected = [row for row in rows if row["selected_marginal_D"] == "true"]
    assert {row["c_D_case"] for row in selected} == {"base"}
    by_key = {
        (row["period_object"], row["period"], row["c_D_case"]): row
        for row in rows
    }
    historical = by_key[("historical", "2021Q1", "base")]
    assert historical["nominal_gdp_bil"] == "1000"
    assert historical["c_D"] == "0.00776"
    assert historical["marginal_denominator_bil"] == "7.76"
    assert historical["horizon"] == "annual_h1_100bp_year"
    assert historical["state_id"] == "historical_actual_state::2021Q1"
    assert historical["fixed_D_comparison_bil"] == "7.76"
    assert historical["historical_path_D_bil"] == "1.552"
    assert historical["fixed_D_audit_status"] == (
        "pass_fixed_D_equals_nominal_gdp_times_c_D"
    )
    current = by_key[("current", "2026", "base")]
    assert current["marginal_denominator_bil"] == "15.52"
    forecast = by_key[("forecast", "2027", "base")]
    assert forecast["marginal_denominator_bil"] == "23.28"
    assert all(row["shock_bps_year"] == "100" for row in rows)
    assert all("old_rate_path_D_scaled_by_observed_short_rate" in row["blocked_use"] for row in rows)


def test_marginal_denominator_audit_and_diagnostic_rows(tmp_path: Path) -> None:
    gdp_path, current_path, historical_path = _write_fixtures(tmp_path)
    rows = marginal_denominator_surface_rows(
        gdp_path=gdp_path,
        current_benchmark_path=current_path,
        historical_denominator_path=historical_path,
    )
    audit = marginal_denominator_audit_rows(rows)
    diagnostic = rate_environment_exposure_diagnostic_rows()

    assert {field for row in audit for field in row} == set(
        MARGINAL_DENOMINATOR_AUDIT_FIELDS
    )
    assert {row["check_status"] for row in audit} == {"pass"}
    assert {row["check_id"] for row in audit} >= {
        "one_selected_base_case_per_period",
        "historical_fixed_D_audit_recorded",
    }
    assert {field for row in diagnostic for field in row} == set(
        RATE_ENVIRONMENT_EXPOSURE_DIAGNOSTIC_FIELDS
    )
    assert {row["rate_environment_moves_d"] for row in diagnostic} == {"false"}
    assert all(
        "D_M_uses_state_nominal_gdp" in row["marginal_denominator_rule"]
        for row in diagnostic
    )


def test_denominator_seed_reproduces_existing_final_d_values(tmp_path: Path) -> None:
    seed = tmp_path / "seed.csv"
    _write_csv(
        seed,
        [
            {
                "period_object": "current",
                "period": "2026",
                "horizon": "annual_h1_100bp_year",
                "state_id": "current_state::2026",
                "fiscal_year": "2026",
                "scenario_id": "current_state",
                "shock_path_id": "plus_100bp_year",
                "shock_bps_year": "100",
                "selected_marginal_D_bil": "15.52",
                "nominal_gdp_bil": "2000",
                "fixed_D_comparison_bil": "",
                "historical_path_D_bil": "",
                "source_status": "output_reconstruction_from_existing_final_snapshot_not_external_gdp",
                "allowed_use": "marginal_denominator_rebuild_seed_for_v1_closeout",
                "blocked_use": "evidence_mode_gdp_source_claim;new_denominator_method_change",
                "claim_boundary": "seed_reproduces_existing_selected_D_values_without_value_change",
            }
        ],
    )

    rows = marginal_denominator_surface_rows(seed_path=seed)

    assert set(_read_csv(seed)[0]) == set(MARGINAL_DENOMINATOR_SEED_FIELDS)
    selected = [row for row in rows if row["selected_marginal_D"] == "true"]
    assert len(rows) == 3
    assert selected[0]["marginal_denominator_bil"] == "15.52"
    assert selected[0]["source_status"] == (
        "output_reconstruction_from_existing_final_snapshot_not_external_gdp"
    )


def test_denominator_state_multiplier_blocks_mechanical_rate_drivers(
    tmp_path: Path,
) -> None:
    gdp_path, current_path, historical_path = _write_fixtures(tmp_path)
    surface_rows = marginal_denominator_surface_rows(
        gdp_path=gdp_path,
        current_benchmark_path=current_path,
        historical_denominator_path=historical_path,
    )

    rows = denominator_state_multiplier_rows(surface_rows)

    assert {field for row in rows for field in row} == set(
        DENOMINATOR_STATE_MULTIPLIER_FIELDS
    )
    assert {row["state_multiplier_case"] for row in rows} == {"neutral"}
    assert {row["state_multiplier"] for row in rows} == {"1"}
    assert {row["selected_state_multiplier"] for row in rows} == {"true"}
    assert {
        (row["period_object"], row["period"]) for row in rows
    } == {
        ("historical", "2021Q1"),
        ("current", "2026"),
        ("forecast", "2027"),
    }
    for row in rows:
        for blocked in [
            "current_rate_level",
            "old_path_D",
            "numerator_size",
            "tdc_stock",
            "deposit_stock",
            "beta",
            "chi",
            "scenario_label",
        ]:
            assert blocked in row["blocked_drivers"]


def test_marginal_denominator_outputs_are_written(tmp_path: Path) -> None:
    gdp_path, current_path, historical_path = _write_fixtures(tmp_path)
    rows = marginal_denominator_surface_rows(
        gdp_path=gdp_path,
        current_benchmark_path=current_path,
        historical_denominator_path=historical_path,
    )
    audit = marginal_denominator_audit_rows(rows)
    diagnostic = rate_environment_exposure_diagnostic_rows()
    state_multiplier = denominator_state_multiplier_rows(rows)

    outputs = write_marginal_denominator_outputs(
        tmp_path / "out",
        surface_rows=rows,
        audit_rows=audit,
        diagnostic_rows=diagnostic,
        state_multiplier_rows=state_multiplier,
    )

    assert outputs["surface_csv"].read_text(encoding="utf-8").startswith(
        "marginal_denominator_row_id,"
    )
    assert outputs["audit_csv"].read_text(encoding="utf-8").startswith(
        "marginal_denominator_audit_row_id,"
    )
    assert outputs["diagnostic_csv"].read_text(encoding="utf-8").startswith(
        "rate_environment_exposure_diagnostic_row_id,"
    )
    assert outputs["state_multiplier_csv"].read_text(encoding="utf-8").startswith(
        "denominator_state_multiplier_row_id,"
    )


def test_bad_surface_rejects_nonstandard_shock(tmp_path: Path) -> None:
    gdp_path, current_path, historical_path = _write_fixtures(tmp_path)
    rows = marginal_denominator_surface_rows(
        gdp_path=gdp_path,
        current_benchmark_path=current_path,
        historical_denominator_path=historical_path,
    )
    bad = deepcopy(rows)
    bad[0]["shock_bps_year"] = "75"

    with pytest.raises(MarginalDenominatorError, match="100bp-year"):
        validate_marginal_denominator_surface(bad)


def test_bad_surface_rejects_formula_drift(tmp_path: Path) -> None:
    gdp_path, current_path, historical_path = _write_fixtures(tmp_path)
    rows = marginal_denominator_surface_rows(
        gdp_path=gdp_path,
        current_benchmark_path=current_path,
        historical_denominator_path=historical_path,
    )
    bad = deepcopy(rows)
    bad[0]["marginal_denominator_bil"] = str(
        Decimal(bad[0]["marginal_denominator_bil"]) + Decimal("1")
    )

    with pytest.raises(MarginalDenominatorError, match="formula mismatch"):
        validate_marginal_denominator_surface(bad)


def test_bad_state_multiplier_rejects_stock_or_rate_driver(tmp_path: Path) -> None:
    gdp_path, current_path, historical_path = _write_fixtures(tmp_path)
    surface_rows = marginal_denominator_surface_rows(
        gdp_path=gdp_path,
        current_benchmark_path=current_path,
        historical_denominator_path=historical_path,
    )
    rows = denominator_state_multiplier_rows(surface_rows)
    bad = deepcopy(rows)
    bad[0]["state_multiplier"] = "1.1"

    with pytest.raises(MarginalDenominatorError, match="must remain 1"):
        validate_denominator_state_multiplier(bad)

    bad = deepcopy(rows)
    bad[0]["blocked_drivers"] = bad[0]["blocked_drivers"].replace(";tdc_stock", "")

    with pytest.raises(MarginalDenominatorError, match="blocked drivers"):
        validate_denominator_state_multiplier(bad)


def _write_fixtures(tmp_path: Path) -> tuple[Path, Path, Path]:
    gdp_path = tmp_path / "GDP.csv"
    _write_csv(
        gdp_path,
        [
            {"observation_date": "1999-10-01", "GDP": "900"},
            {"observation_date": "2021-01-01", "GDP": "1000"},
        ],
    )
    current_path = tmp_path / "current.csv"
    _write_csv(
        current_path,
        [
            {"forecast_year": "2026", "nominal_gdp_bil": "2000"},
            {"forecast_year": "2027", "nominal_gdp_bil": "3000"},
        ],
    )
    historical_path = tmp_path / "historical_denominator.csv"
    _write_csv(
        historical_path,
        [
            {
                "period": "2021Q1",
                "nominal_gdp_bil": "1000",
                "selected_historical_path_D_bil": "1.552",
                "fixed_D_comparison_bil": "7.76",
            }
        ],
    )
    return gdp_path, current_path, historical_path


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
