from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from ratewall.databook.forecast_hardening import (
    FORECAST_ASSUMPTION_LEDGER_FIELDS,
    FORECAST_DENOMINATOR_CD_ROBUSTNESS_FIELDS,
    FORECAST_HARDENING_AUDIT_FIELDS,
    FORECAST_PUBLIC_INTEREST_SENSITIVITY_FIELDS,
    FORECAST_REMITTANCE_BASELINE_FIELDS,
    FORECAST_RESIDUAL_SAFE_YIELD_LEVEL_BOUND_FIELDS,
    FORECAST_SELECTED_D_FIELDS,
    forecast_assumption_ledger_rows,
    forecast_denominator_cd_robustness_rows,
    forecast_hardening_audit_rows,
    forecast_public_interest_sensitivity_rows,
    forecast_remittance_baseline_rows,
    forecast_residual_safe_yield_level_bound_rows,
    forecast_selected_d_rows,
    write_forecast_hardening_outputs,
)


def test_forecast_hardening_selected_d_and_cd_robustness(tmp_path: Path) -> None:
    forecast_dir, denominator_dir = _write_fixture(tmp_path)

    selected_d = forecast_selected_d_rows(
        forecast_readout_dir=forecast_dir,
        denominator_parity_dir=denominator_dir,
    )
    cd_rows = forecast_denominator_cd_robustness_rows(
        forecast_readout_dir=forecast_dir,
        denominator_parity_dir=denominator_dir,
    )

    assert {field for row in selected_d for field in row} == set(
        FORECAST_SELECTED_D_FIELDS
    )
    assert {field for row in cd_rows for field in row} == set(
        FORECAST_DENOMINATOR_CD_ROBUSTNESS_FIELDS
    )
    assert all(row["selected_D_matches_denominator_parity"] == "true" for row in selected_d)
    by_case = {
        (row["scenario_id"], row["c_D_case_id"]): row
        for row in cd_rows
    }
    assert by_case[("rate_up", "zero_no_rate_response")]["robust_D_bil"] == "100"
    assert by_case[("rate_up", "low_legacy_0_125")]["robust_D_bil"] == "100.25"
    selected = by_case[("rate_up", "selected_frbus_structural")]
    assert Decimal(selected["robust_D_bil"]).quantize(Decimal("0.000001")) == Decimal(
        "102.239738"
    )


def test_forecast_hardening_sidecars_and_audit(tmp_path: Path) -> None:
    forecast_dir, denominator_dir = _write_fixture(tmp_path)
    selected_d = forecast_selected_d_rows(
        forecast_readout_dir=forecast_dir,
        denominator_parity_dir=denominator_dir,
    )
    assumption_rows = forecast_assumption_ledger_rows()
    cd_rows = forecast_denominator_cd_robustness_rows(
        forecast_readout_dir=forecast_dir,
        denominator_parity_dir=denominator_dir,
    )
    public_interest_rows = forecast_public_interest_sensitivity_rows(
        forecast_readout_dir=forecast_dir,
    )
    remittance_rows = forecast_remittance_baseline_rows(
        forecast_readout_dir=forecast_dir,
        cbo_revenue_path=tmp_path / "missing.xlsx",
    )
    residual_rows = forecast_residual_safe_yield_level_bound_rows(
        forecast_readout_dir=forecast_dir,
    )
    audit_rows = forecast_hardening_audit_rows(
        selected_d_rows=selected_d,
        cd_rows=cd_rows,
        remittance_rows=remittance_rows,
    )

    assert {field for row in assumption_rows for field in row} == set(
        FORECAST_ASSUMPTION_LEDGER_FIELDS
    )
    assert {field for row in public_interest_rows for field in row} == set(
        FORECAST_PUBLIC_INTEREST_SENSITIVITY_FIELDS
    )
    assert {field for row in remittance_rows for field in row} == set(
        FORECAST_REMITTANCE_BASELINE_FIELDS
    )
    assert {field for row in residual_rows for field in row} == set(
        FORECAST_RESIDUAL_SAFE_YIELD_LEVEL_BOUND_FIELDS
    )
    assert {field for row in audit_rows for field in row} == set(
        FORECAST_HARDENING_AUDIT_FIELDS
    )
    assert {row["check_status"] for row in audit_rows} == {"pass"}
    assert all(row["scenario_delta_admitted"] == "false" for row in remittance_rows)
    assert all(row["central_n_delta_bil"] == "0" for row in remittance_rows)
    assert all(
        row["central_n_delta_bil_allowed"] == "false"
        for row in residual_rows
    )
    by_case = {row["sensitivity_case_id"]: row for row in public_interest_rows if row["scenario_id"] == "baseline"}
    assert by_case["selected_net_after_tax_fiscal_tga"]["central_n_delta_bil_allowed"] == "true"
    assert by_case["gross_before_tax_fiscal_tga"]["public_interest_support_bil"] == "13"

    outputs = write_forecast_hardening_outputs(
        tmp_path / "out",
        selected_d_rows=selected_d,
        assumption_rows=assumption_rows,
        cd_rows=cd_rows,
        public_interest_rows=public_interest_rows,
        remittance_rows=remittance_rows,
        residual_rows=residual_rows,
        audit_rows=audit_rows,
    )
    assert outputs["selected_d_csv"].read_text(encoding="utf-8").startswith(
        "forecast_selected_d_row_id,"
    )
    assert outputs["audit_csv"].read_text(encoding="utf-8").startswith(
        "forecast_hardening_audit_row_id,"
    )


def test_forecast_remittance_baseline_extracts_cbo_open_data_csv(
    tmp_path: Path,
) -> None:
    forecast_dir, _ = _write_fixture(tmp_path)
    revenue_csv = tmp_path / "51138-2026-02-Revenue-annual_fy.csv"
    _write_csv(
        revenue_csv,
        [
            {
                "date": "FY2036",
                "variable": "rev_fed_reserve",
                "value": "176.402",
                "estimate_type": "actual",
            },
            {
                "date": "FY2036",
                "variable": "other_revenue",
                "value": "999",
                "estimate_type": "actual",
            },
        ],
    )

    rows = forecast_remittance_baseline_rows(
        forecast_readout_dir=forecast_dir,
        cbo_revenue_path=revenue_csv,
    )

    assert rows[0]["remittance_baseline_bil"] == "176.402"
    assert rows[0]["source_status"] == (
        "source_present_cbo_open_data_csv_rev_fed_reserve_extracted"
    )
    assert rows[0]["scenario_delta_admitted"] == "false"
    assert rows[0]["central_n_delta_bil"] == "0"


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    forecast = tmp_path / "forecast"
    denominator = tmp_path / "denominator"
    forecast.mkdir()
    denominator.mkdir()
    _write_csv(
        forecast / "ratewall_forecast_central_scenario_surface.csv",
        [
            _central("baseline", "baseline", "100", "10", "0.1"),
            _central("rate_up", "baseline", "102.2397384009499292", "10", "0.097810"),
        ],
    )
    _write_csv(
        denominator / "ratewall_denominator_parity_bridge.csv",
        [
            _denom("baseline", "baseline", "100", "100", "0", "false"),
            _denom("rate_up", "baseline", "100", "102.2397384009499292", "2", "true"),
        ],
    )
    _write_csv(
        forecast / "ratewall_forecast_public_interest_net_block.csv",
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "baseline",
                "baseline_scenario_id": "baseline",
                "net_interest_after_fiscal_tga_offsets_bil": "8",
                "net_interest_before_fiscal_tga_offsets_bil": "10",
                "gross_public_interest_current_demand_support_bil": "13",
                "legacy_interest_support_bil": "9",
            }
        ],
    )
    _write_csv(
        forecast / "ratewall_forecast_residual_numerator_sensitivity.csv",
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "baseline",
                "baseline_scenario_id": "baseline",
                "assumption_set": "residual",
                "household_safe_yield_capture_bil": "1",
                "paired_deposit_mmf_net_sensitivity_bil": "2",
                "firm_cash_attenuation_bil": "3",
                "total_residual_sensitivity_bil": "6",
            }
        ],
    )
    return forecast, denominator


def _central(
    scenario: str, baseline: str, d_value: str, n_value: str, ratio: str
) -> dict[str, str]:
    return {
        "fiscal_year": "2036",
        "scenario_id": scenario,
        "baseline_scenario_id": baseline,
        "central_moving_denominator_bil": d_value,
        "central_n_bil": n_value,
        "central_ratewall_ratio": ratio,
    }


def _denom(
    scenario: str,
    baseline: str,
    path_d: str,
    selected_d: str,
    overlay_bp: str,
    rate_flag: str,
) -> dict[str, str]:
    return {
        "surface_id": "forecast_central_tdcsim_cbo",
        "fiscal_year": "2036",
        "scenario_id": scenario,
        "baseline_scenario_id": baseline,
        "fixed_runtime_D_bil": "100",
        "path_D_bil": path_d,
        "moving_D_bil": selected_d,
        "selected_D_bil": selected_d,
        "selected_denominator_variant_role": (
            "selected_moving_D_for_rate_changing_forecast_scenario"
            if rate_flag == "true"
            else "selected_path_D_for_nonrate_forecast_scenario"
        ),
        "rate_changing_scenario_flag": rate_flag,
        "scenario_rate_overlay_bp": overlay_bp,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
