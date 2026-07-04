"""Residual and replacement-channel closure for RateWall forecast rows."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_FORECAST_READOUT_DIR = Path("var/preliminary_scenario_results/forecast_10y")

FIRM_LIQUIDITY_REPLACEMENT_FIELDS = [
    "firm_liquidity_replacement_row_id",
    "selected_method_id",
    "selected_method_role",
    "replacement_candidate_id",
    "replacement_candidate_role",
    "shared_basis",
    "firm_liquid_asset_stock_gdp_share",
    "firm_liquid_asset_stock_source_status",
    "max_abs_firm_cash_delta_bil",
    "firm_cash_active_row_count",
    "firm_cushion_active_row_count",
    "basis_conflict_status",
    "central_N_treatment",
    "allowed_use",
    "blocked_use",
]

SAFE_ASSET_DRAG_GATE_FIELDS = [
    "safe_asset_drag_gate_row_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "assumption_set",
    "candidate_safe_asset_stock_bil",
    "excluded_public_interest_cashflow_bil",
    "excluded_household_safe_yield_basis_bil",
    "excluded_deposit_mmf_basis_bil",
    "excluded_tdc_holder_flow_basis_bil",
    "excluded_moving_D_overlap_basis_bil",
    "residual_safe_asset_stock_bil",
    "duration_or_revaluation_basis",
    "wealth_or_liquidity_response_coefficient",
    "current_year_timing_share",
    "admission_status",
    "central_N_treatment",
    "allowed_use",
    "blocked_use",
]

RESIDUAL_CHANNEL_ADMISSION_MATRIX_FIELDS = [
    "residual_channel_admission_row_id",
    "channel_id",
    "channel_label",
    "forecast_treatment",
    "central_N_treatment",
    "sensitivity_treatment",
    "replacement_group",
    "nonoverlap_guard",
    "admission_status",
    "source_or_calibration_status",
    "next_model_action",
    "allowed_use",
    "blocked_use",
]

RESIDUAL_NUMERATOR_SURFACE_FIELDS = [
    "residual_numerator_surface_row_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "assumption_set",
    "firm_cash_attenuation_bil",
    "firm_liquid_asset_cushion_bil",
    "household_safe_yield_capture_bil",
    "deposit_mmf_substitution_offset_bil",
    "deposit_mmf_substitution_drag_bil",
    "paired_deposit_mmf_net_sensitivity_bil",
    "safe_asset_allocation_drag_bil",
    "zero_low_apr_credit_attenuation_bil",
    "firm_rollover_pressure_drag_bil",
    "total_residual_sensitivity_bil",
    "delta_total_residual_sensitivity_vs_baseline_bil",
    "central_N_delta_bil",
    "central_N_treatment",
    "admission_matrix_status",
    "allowed_use",
    "blocked_use",
]


class ResidualChannelClosureError(ValueError):
    """Raised when residual closure inputs are missing or inconsistent."""


def firm_liquidity_replacement_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Return the firm cash versus firm cushion replacement decision."""

    residual_rows = _read_required(
        Path(forecast_readout_dir) / "ratewall_forecast_residual_numerator_sensitivity.csv"
    )
    if not residual_rows:
        raise ResidualChannelClosureError("missing residual sensitivity rows")
    max_abs_firm_cash = max(
        abs(Decimal(row["delta_firm_cash_attenuation_vs_baseline_bil"]))
        for row in residual_rows
    )
    active_firm_cash_rows = sum(
        Decimal(row["firm_cash_attenuation_bil"]) != 0 for row in residual_rows
    )
    first = residual_rows[0]
    return [
        {
            "firm_liquidity_replacement_row_id": "firm_liquidity_replacement::v1",
            "selected_method_id": "firm_cash_attenuation",
            "selected_method_role": "bounded_sensitivity_not_central",
            "replacement_candidate_id": "firm_liquid_asset_cushion",
            "replacement_candidate_role": "replacement_candidate_not_active",
            "shared_basis": "firm_liquid_asset_stock_context",
            "firm_liquid_asset_stock_gdp_share": first[
                "firm_liquid_asset_stock_gdp_share"
            ],
            "firm_liquid_asset_stock_source_status": first[
                "firm_liquid_asset_stock_source_status"
            ],
            "max_abs_firm_cash_delta_bil": _fmt(max_abs_firm_cash),
            "firm_cash_active_row_count": str(active_firm_cash_rows),
            "firm_cushion_active_row_count": "0",
            "basis_conflict_status": "pass_no_firm_cash_and_cushion_stack",
            "central_N_treatment": "not_in_central_N_sensitivity_or_replacement_only",
            "allowed_use": "firm_liquidity_replacement_decision",
            "blocked_use": "additive_firm_cash_plus_firm_liquid_asset_cushion",
        }
    ]


def residual_safe_asset_drag_gate_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Fail closed on safe-asset drag until a disjoint residual basis exists."""

    residual_rows = _read_required(
        Path(forecast_readout_dir) / "ratewall_forecast_residual_numerator_sensitivity.csv"
    )
    rows: list[dict[str, str]] = []
    for row in residual_rows:
        deposit_mmf_basis = abs(Decimal(row["deposit_mmf_substitution_offset_bil"])) + abs(
            Decimal(row["deposit_mmf_substitution_drag_bil"])
        )
        rows.append(
            {
                "safe_asset_drag_gate_row_id": (
                    "residual_safe_asset_drag_gate::"
                    f"{row['assumption_set']}::{row['fiscal_year']}::{row['scenario_id']}"
                ),
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "baseline_scenario_id": row["baseline_scenario_id"],
                "assumption_set": row["assumption_set"],
                "candidate_safe_asset_stock_bil": "",
                "excluded_public_interest_cashflow_bil": row[
                    "public_interest_already_demand_converted_bil"
                ],
                "excluded_household_safe_yield_basis_bil": row[
                    "household_safe_yield_capture_bil"
                ],
                "excluded_deposit_mmf_basis_bil": _fmt(deposit_mmf_basis),
                "excluded_tdc_holder_flow_basis_bil": "",
                "excluded_moving_D_overlap_basis_bil": row[
                    "selected_delta_denominator_bil"
                ],
                "residual_safe_asset_stock_bil": "0",
                "duration_or_revaluation_basis": "not_built",
                "wealth_or_liquidity_response_coefficient": "not_admitted",
                "current_year_timing_share": "0",
                "admission_status": "rejected_no_disjoint_residual_safe_asset_basis",
                "central_N_treatment": "not_in_central_N",
                "allowed_use": "safe_asset_drag_admission_gate",
                "blocked_use": (
                    "same_cashflow_dollar_subtracted_after_public_interest_or_"
                    "household_or_deposit_mmf_or_moving_D_conversion"
                ),
            }
        )
    return rows


def residual_channel_admission_matrix_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Return final forecast treatment for residual/replacement channels."""

    root = Path(forecast_readout_dir)
    plan_rows = _read_required(root / "ratewall_forecast_numerator_channel_plan.csv")
    zero_low_apr_rows = _read_required(
        root / "ratewall_forecast_zero_low_apr_credit_materiality.csv"
    )
    plan_by_channel = {row["channel_id"]: row for row in plan_rows}
    zero_low_apr_status = _zero_low_apr_status(zero_low_apr_rows)
    specs = [
        _matrix_spec(
            "firm_cash_attenuation",
            "firm cash attenuation",
            forecast_treatment="bounded_projected_sensitivity",
            central="not_in_central_N",
            sensitivity="admitted_as_bounded_sensitivity",
            replacement_group="firm_liquidity",
            guard="cannot_stack_with_firm_liquid_asset_cushion",
            status="admitted_sensitivity_not_central",
            source="source_backed_z1_firm_liquid_asset_context_weak_link_assumption",
            action="keep_as_bounded_sensitivity_until_replaced_or_demoted",
            blocked="additive_firm_cash_plus_firm_liquid_asset_cushion",
        ),
        _matrix_spec(
            "firm_liquid_asset_cushion",
            "firm liquid-asset cushion",
            forecast_treatment="replacement_candidate_only",
            central="not_in_central_N",
            sensitivity="not_active",
            replacement_group="firm_liquidity",
            guard="can_replace_firm_cash_only_after_demotion_rule",
            status=plan_by_channel["firm_liquid_asset_cushion"][
                "final_central_status"
            ],
            source=plan_by_channel["firm_liquid_asset_cushion"]["calibration_need"],
            action=plan_by_channel["firm_liquid_asset_cushion"]["next_model_action"],
            blocked=plan_by_channel["firm_liquid_asset_cushion"]["blocked_use"],
        ),
        _matrix_spec(
            "household_safe_yield_capture",
            "household safe-yield capture",
            forecast_treatment="bounded_residual_sensitivity",
            central="not_in_central_N",
            sensitivity="admitted_as_residual_sensitivity",
            replacement_group="safe_yield_residual",
            guard="residual_to_public_interest_block",
            status="admitted_sensitivity_not_central",
            source="assumption_mode_residual_safe_yield_conversion",
            action="carry_as_sensitivity_pending_stronger_spend_conversion_evidence",
            blocked="same_cashflow_dollar_converted_twice",
        ),
        _matrix_spec(
            "deposit_mmf_substitution_offset",
            "deposit/MMF substitution offset",
            forecast_treatment="paired_bounded_sensitivity",
            central="not_in_central_N",
            sensitivity="admitted_only_with_paired_drag",
            replacement_group="deposit_mmf_pair",
            guard="offset_cannot_enter_without_drag_row_present",
            status="admitted_paired_sensitivity_not_central",
            source="assumption_mode_residual_access_path",
            action="keep_paired_with_deposit_mmf_substitution_drag",
            blocked="unpaired_mmf_offset",
        ),
        _matrix_spec(
            "deposit_mmf_substitution_drag",
            "deposit/MMF substitution drag",
            forecast_treatment="paired_credit_drag_sensitivity",
            central="not_in_central_N",
            sensitivity="admitted_only_with_offset_and_D_overlap_guard",
            replacement_group="deposit_mmf_pair",
            guard="must_not_double_count_selected_moving_D_credit_drag",
            status="admitted_paired_sensitivity_not_central",
            source="assumption_mode_credit_drag_pair",
            action="keep_paired_and_report_denominator_overlap_status",
            blocked="credit_drag_double_count_against_moving_D",
        ),
        _matrix_spec(
            "safe_asset_allocation_drag",
            "safe-asset allocation drag",
            forecast_treatment="sidecar_until_disjoint_basis_exists",
            central="not_in_central_N",
            sensitivity="not_admitted",
            replacement_group="safe_asset_drag",
            guard=plan_by_channel["safe_asset_allocation_drag"]["double_count_guard"],
            status="rejected_no_disjoint_residual_safe_asset_basis",
            source=plan_by_channel["safe_asset_allocation_drag"]["calibration_need"],
            action=plan_by_channel["safe_asset_allocation_drag"]["next_model_action"],
            blocked=plan_by_channel["safe_asset_allocation_drag"]["blocked_use"],
        ),
        _matrix_spec(
            "zero_interest_credit_attenuation",
            "zero/low-APR credit attenuation",
            forecast_treatment="product_screen_context_only",
            central="not_in_central_N",
            sensitivity="not_admitted",
            replacement_group="credit_sidecar",
            guard="requires_outstanding_stock_duration_and_D_overlap_proof",
            status=zero_low_apr_status,
            source=plan_by_channel["zero_interest_credit_attenuation"][
                "calibration_need"
            ],
            action=plan_by_channel["zero_interest_credit_attenuation"][
                "next_model_action"
            ],
            blocked=plan_by_channel["zero_interest_credit_attenuation"][
                "blocked_use"
            ],
        ),
        _matrix_spec(
            "firm_rollover_pressure_drag",
            "firm rollover pressure drag",
            forecast_treatment="denominator_or_credit_sidecar",
            central="not_in_central_N",
            sensitivity="not_admitted",
            replacement_group="credit_sidecar",
            guard="requires_D_or_credit_reallocation_not_N_subtraction",
            status=plan_by_channel["firm_rollover_pressure_drag"][
                "final_central_status"
            ],
            source=plan_by_channel["firm_rollover_pressure_drag"]["calibration_need"],
            action=plan_by_channel["firm_rollover_pressure_drag"]["next_model_action"],
            blocked=plan_by_channel["firm_rollover_pressure_drag"]["blocked_use"],
        ),
    ]
    return specs


def residual_numerator_surface_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Return the residual sensitivity surface with non-admitted channels zeroed."""

    residual_rows = _read_required(
        Path(forecast_readout_dir) / "ratewall_forecast_residual_numerator_sensitivity.csv"
    )
    out: list[dict[str, str]] = []
    for row in residual_rows:
        out.append(
            {
                "residual_numerator_surface_row_id": (
                    "residual_numerator_surface::"
                    f"{row['assumption_set']}::{row['fiscal_year']}::{row['scenario_id']}"
                ),
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "baseline_scenario_id": row["baseline_scenario_id"],
                "assumption_set": row["assumption_set"],
                "firm_cash_attenuation_bil": row["firm_cash_attenuation_bil"],
                "firm_liquid_asset_cushion_bil": "0",
                "household_safe_yield_capture_bil": row[
                    "household_safe_yield_capture_bil"
                ],
                "deposit_mmf_substitution_offset_bil": row[
                    "deposit_mmf_substitution_offset_bil"
                ],
                "deposit_mmf_substitution_drag_bil": row[
                    "deposit_mmf_substitution_drag_bil"
                ],
                "paired_deposit_mmf_net_sensitivity_bil": row[
                    "paired_deposit_mmf_net_sensitivity_bil"
                ],
                "safe_asset_allocation_drag_bil": "0",
                "zero_low_apr_credit_attenuation_bil": "0",
                "firm_rollover_pressure_drag_bil": "0",
                "total_residual_sensitivity_bil": row["total_residual_sensitivity_bil"],
                "delta_total_residual_sensitivity_vs_baseline_bil": row[
                    "delta_total_residual_sensitivity_vs_baseline_bil"
                ],
                "central_N_delta_bil": "0",
                "central_N_treatment": "not_in_central_N_sensitivity_surface_only",
                "admission_matrix_status": (
                    "firm_cash_household_safe_yield_and_deposit_mmf_pair_are_"
                    "sensitivity_only;unsafe_drag_channels_zeroed"
                ),
                "allowed_use": "residual_numerator_sensitivity_surface",
                "blocked_use": (
                    "canonical_headline_promotion;central_N_addition_without_"
                    "admission;unpaired_mmf_offset;safe_asset_drag_without_disjoint_basis"
                ),
            }
        )
    return out


def write_residual_channel_closure_outputs(
    output_dir: str | Path,
    *,
    firm_rows: Sequence[Mapping[str, str]],
    safe_asset_rows: Sequence[Mapping[str, str]],
    matrix_rows: Sequence[Mapping[str, str]],
    residual_surface_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write residual/replacement closure artifacts."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "firm_liquidity_csv": out / "ratewall_firm_liquidity_replacement_decision.csv",
        "safe_asset_gate_csv": out / "ratewall_residual_safe_asset_drag_admission_gate.csv",
        "admission_matrix_csv": out / "ratewall_residual_channel_admission_matrix.csv",
        "residual_surface_csv": out / "ratewall_residual_numerator_surface.csv",
    }
    write_rows(
        paths["firm_liquidity_csv"],
        [dict(row) for row in firm_rows],
        FIRM_LIQUIDITY_REPLACEMENT_FIELDS,
    )
    write_rows(
        paths["safe_asset_gate_csv"],
        [dict(row) for row in safe_asset_rows],
        SAFE_ASSET_DRAG_GATE_FIELDS,
    )
    write_rows(
        paths["admission_matrix_csv"],
        [dict(row) for row in matrix_rows],
        RESIDUAL_CHANNEL_ADMISSION_MATRIX_FIELDS,
    )
    write_rows(
        paths["residual_surface_csv"],
        [dict(row) for row in residual_surface_rows],
        RESIDUAL_NUMERATOR_SURFACE_FIELDS,
    )
    return paths


def _matrix_spec(
    channel_id: str,
    label: str,
    *,
    forecast_treatment: str,
    central: str,
    sensitivity: str,
    replacement_group: str,
    guard: str,
    status: str,
    source: str,
    action: str,
    blocked: str,
) -> dict[str, str]:
    return {
        "residual_channel_admission_row_id": (
            f"residual_channel_admission::{channel_id}"
        ),
        "channel_id": channel_id,
        "channel_label": label,
        "forecast_treatment": forecast_treatment,
        "central_N_treatment": central,
        "sensitivity_treatment": sensitivity,
        "replacement_group": replacement_group,
        "nonoverlap_guard": guard,
        "admission_status": status,
        "source_or_calibration_status": source,
        "next_model_action": action,
        "allowed_use": "residual_channel_closure_matrix",
        "blocked_use": blocked,
    }


def _zero_low_apr_status(rows: Sequence[Mapping[str, str]]) -> str:
    material = [
        row
        for row in rows
        if row["screen_status"] == "potentially_material_but_historical_share_not_current_path"
    ]
    if material:
        return "not_admitted_product_specific_stock_path_missing"
    return "not_admitted_screened_low_materiality_or_missing_stock"


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ResidualChannelClosureError(f"missing required input: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _fmt(value: Decimal) -> str:
    return format(value, "f")
