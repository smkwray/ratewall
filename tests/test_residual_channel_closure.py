from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.residual_channel_closure import (
    FIRM_LIQUIDITY_REPLACEMENT_FIELDS,
    RESIDUAL_CHANNEL_ADMISSION_MATRIX_FIELDS,
    RESIDUAL_NUMERATOR_SURFACE_FIELDS,
    SAFE_ASSET_DRAG_GATE_FIELDS,
    firm_liquidity_replacement_rows,
    residual_channel_admission_matrix_rows,
    residual_numerator_surface_rows,
    residual_safe_asset_drag_gate_rows,
    write_residual_channel_closure_outputs,
)


def test_residual_closure_gates_firm_and_safe_asset_channels(tmp_path: Path) -> None:
    root = _write_forecast_fixture(tmp_path)

    firm_rows = firm_liquidity_replacement_rows(forecast_readout_dir=root)
    safe_asset_rows = residual_safe_asset_drag_gate_rows(forecast_readout_dir=root)
    matrix_rows = residual_channel_admission_matrix_rows(forecast_readout_dir=root)
    surface_rows = residual_numerator_surface_rows(forecast_readout_dir=root)

    assert {field for row in firm_rows for field in row} == set(
        FIRM_LIQUIDITY_REPLACEMENT_FIELDS
    )
    assert {field for row in safe_asset_rows for field in row} == set(
        SAFE_ASSET_DRAG_GATE_FIELDS
    )
    assert {field for row in matrix_rows for field in row} == set(
        RESIDUAL_CHANNEL_ADMISSION_MATRIX_FIELDS
    )
    assert {field for row in surface_rows for field in row} == set(
        RESIDUAL_NUMERATOR_SURFACE_FIELDS
    )
    firm = firm_rows[0]
    assert firm["basis_conflict_status"] == "pass_no_firm_cash_and_cushion_stack"
    assert firm["firm_cushion_active_row_count"] == "0"
    assert firm["blocked_use"] == "additive_firm_cash_plus_firm_liquid_asset_cushion"

    safe_asset = safe_asset_rows[0]
    assert safe_asset["residual_safe_asset_stock_bil"] == "0"
    assert safe_asset["admission_status"] == (
        "rejected_no_disjoint_residual_safe_asset_basis"
    )
    assert safe_asset["central_N_treatment"] == "not_in_central_N"

    matrix = {row["channel_id"]: row for row in matrix_rows}
    assert matrix["deposit_mmf_substitution_offset"]["sensitivity_treatment"] == (
        "admitted_only_with_paired_drag"
    )
    assert matrix["deposit_mmf_substitution_drag"]["nonoverlap_guard"] == (
        "must_not_double_count_selected_moving_D_credit_drag"
    )
    assert matrix["firm_liquid_asset_cushion"]["forecast_treatment"] == (
        "replacement_candidate_only"
    )
    assert matrix["safe_asset_allocation_drag"]["admission_status"] == (
        "rejected_no_disjoint_residual_safe_asset_basis"
    )

    surface = surface_rows[0]
    assert surface["firm_liquid_asset_cushion_bil"] == "0"
    assert surface["safe_asset_allocation_drag_bil"] == "0"
    assert surface["zero_low_apr_credit_attenuation_bil"] == "0"
    assert surface["firm_rollover_pressure_drag_bil"] == "0"
    assert surface["central_N_delta_bil"] == "0"


def test_residual_closure_outputs_are_written(tmp_path: Path) -> None:
    root = _write_forecast_fixture(tmp_path)
    outputs = write_residual_channel_closure_outputs(
        tmp_path / "out",
        firm_rows=firm_liquidity_replacement_rows(forecast_readout_dir=root),
        safe_asset_rows=residual_safe_asset_drag_gate_rows(forecast_readout_dir=root),
        matrix_rows=residual_channel_admission_matrix_rows(forecast_readout_dir=root),
        residual_surface_rows=residual_numerator_surface_rows(
            forecast_readout_dir=root
        ),
    )

    assert outputs["firm_liquidity_csv"].read_text(encoding="utf-8").startswith(
        "firm_liquidity_replacement_row_id,"
    )
    assert outputs["safe_asset_gate_csv"].read_text(encoding="utf-8").startswith(
        "safe_asset_drag_gate_row_id,"
    )
    assert outputs["admission_matrix_csv"].read_text(encoding="utf-8").startswith(
        "residual_channel_admission_row_id,"
    )
    assert outputs["residual_surface_csv"].read_text(encoding="utf-8").startswith(
        "residual_numerator_surface_row_id,"
    )


def _write_forecast_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "forecast"
    root.mkdir()
    _write_csv(
        root / "ratewall_forecast_residual_numerator_sensitivity.csv",
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "rate_down",
                "baseline_scenario_id": "baseline",
                "assumption_set": "assumption_mode_deposit_mmf_paired_entry",
                "firm_liquid_asset_stock_gdp_share": "0.12",
                "firm_liquid_asset_stock_source_status": "source_backed",
                "firm_cash_attenuation_bil": "-1.2",
                "delta_firm_cash_attenuation_vs_baseline_bil": "-1.2",
                "public_interest_already_demand_converted_bil": "40",
                "household_safe_yield_capture_bil": "2",
                "deposit_mmf_substitution_offset_bil": "3",
                "deposit_mmf_substitution_drag_bil": "-1",
                "paired_deposit_mmf_net_sensitivity_bil": "2",
                "selected_delta_denominator_bil": "-10",
                "total_residual_sensitivity_bil": "2.8",
                "delta_total_residual_sensitivity_vs_baseline_bil": "2.8",
            }
        ],
    )
    _write_csv(
        root / "ratewall_forecast_numerator_channel_plan.csv",
        [
            _plan(
                "safe_asset_allocation_drag",
                final_status="not_admitted_pending_disjoint_basis",
                calibration="needs_disjoint_safe_asset_basis",
                guard="must_not_overlap_household_safe_yield_capture_public_interest_block_or_moving_D",
                action="seek_literature_calibrated_bound_or_keep_as_sidecar_limitation",
                blocked="same_basis_safe_asset_drag_subtracted_from_central_N",
            ),
            _plan(
                "zero_interest_credit_attenuation",
                final_status="not_admitted_pending_product_stock_path",
                calibration="needs_product_stock_duration_path",
                guard="requires_product_specific_outstanding_stock",
                action="run_product_specific_zero_low_apr_credit_materiality_screen",
                blocked="originations_or_denominator_overlap_as_numerator_relief",
            ),
            _plan(
                "firm_liquid_asset_cushion",
                final_status="replacement_candidate_not_additive",
                calibration="needs_firm_cushion_share",
                guard="cannot_enter_together_with_firm_cash_attenuation_on_same_asset_basis",
                action="keep_as_replacement_case_unless_firm_cash_attenuation_is_demoted",
                blocked="additive_firm_cash_plus_firm_cushion",
            ),
            _plan(
                "firm_rollover_pressure_drag",
                final_status="not_a_current_numerator_channel_without_new_credit_model",
                calibration="needs_credit_reallocation_model",
                guard="belongs_in_denominator_or_credit_sidecar",
                action="park_until_credit_sidecar_exists",
                blocked="current_n_subtraction_from_denominator_credit_basis",
            ),
        ],
    )
    _write_csv(
        root / "ratewall_forecast_zero_low_apr_credit_materiality.csv",
        [
            {
                "product_segment": "credit_card_introductory_promo_apr_balances",
                "screen_status": "potentially_material_but_historical_share_not_current_path",
            }
        ],
    )
    return root


def _plan(
    channel_id: str,
    *,
    final_status: str,
    calibration: str,
    guard: str,
    action: str,
    blocked: str,
) -> dict[str, str]:
    return {
        "channel_id": channel_id,
        "final_central_status": final_status,
        "calibration_need": calibration,
        "double_count_guard": guard,
        "next_model_action": action,
        "blocked_use": blocked,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
