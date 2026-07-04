from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.methodology_parity import (
    METHODOLOGY_PARITY_CHANNEL_FIELDS,
    METHODOLOGY_PARITY_DENOMINATOR_FIELDS,
    METHODOLOGY_PARITY_ROADMAP_FIELDS,
    methodology_parity_channel_rows,
    methodology_parity_denominator_rows,
    methodology_parity_readout_markdown,
    methodology_parity_roadmap_rows,
    write_methodology_parity_outputs,
)


def test_methodology_parity_maps_channels_across_surfaces(tmp_path: Path) -> None:
    forecast_dir = _write_forecast_fixture(tmp_path)

    rows = methodology_parity_channel_rows(forecast_readout_dir=forecast_dir)

    assert {field for row in rows for field in row} == set(
        METHODOLOGY_PARITY_CHANNEL_FIELDS
    )
    assert len(rows) == 20
    by_key = {(row["channel_id"], row["surface_id"]): row for row in rows}
    tdc_forecast = by_key[
        ("tdc_ex_overlap_current_demand_support", "forecast_central_tdcsim_cbo")
    ]
    assert tdc_forecast["centrality"] == "central"
    assert tdc_forecast["numerator_treatment"] == "included_in_forecast_central_N"
    direct_forecast = by_key[
        ("direct_treasury_interest_support", "forecast_central_tdcsim_cbo")
    ]
    assert direct_forecast["centrality"] == "central_block_input"
    assert direct_forecast["surface_entry_role"] == (
        "replacement_block_input_not_standalone"
    )
    net_block = by_key[
        ("net_interest_after_fiscal_tga_offsets", "forecast_central_tdcsim_cbo")
    ]
    assert net_block["surface_entry_role"] == "standalone_final_n_term"
    firm_current = by_key[("firm_cash_attenuation", "current_assumption_runtime")]
    assert firm_current["centrality"] == "central"
    firm_forecast = by_key[("firm_cash_attenuation", "forecast_sensitivity_tdcsim_cbo")]
    assert firm_forecast["centrality"] == "sensitivity"
    safe_drag = by_key[("safe_asset_allocation_drag", "forecast_central_tdcsim_cbo")]
    assert safe_drag["centrality"] == "not_central"
    assert safe_drag["parity_status"] == "forecast_gap_or_deliberate_exclusion"


def test_methodology_parity_denominators_keep_fixed_and_moving_d_separate(
    tmp_path: Path,
) -> None:
    denom_path = _write_denominator_fixture(tmp_path)

    rows = methodology_parity_denominator_rows(denominator_contract_path=denom_path)

    assert {field for row in rows for field in row} == set(
        METHODOLOGY_PARITY_DENOMINATOR_FIELDS
    )
    by_surface = {row["surface_id"]: row for row in rows}
    assert by_surface["current_assumption_runtime"]["moving_rate_response"] == (
        "none_fixed_runtime_object"
    )
    assert "selected_frbus" in by_surface["forecast_central_tdcsim_cbo"][
        "moving_rate_response"
    ]
    assert by_surface["forecast_central_tdcsim_cbo"]["centrality"] == (
        "central_forecast_scenario_D"
    )
    assert by_surface["historical_path_context"]["path_component"] == (
        "historical_rate_gap_pct_points;near_zero_guard"
    )


def test_methodology_parity_roadmap_and_outputs(tmp_path: Path) -> None:
    forecast_dir = _write_forecast_fixture(tmp_path)
    denom_path = _write_denominator_fixture(tmp_path)
    channel_rows = methodology_parity_channel_rows(forecast_readout_dir=forecast_dir)
    denominator_rows = methodology_parity_denominator_rows(
        denominator_contract_path=denom_path
    )

    roadmap_rows = methodology_parity_roadmap_rows(
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
    )

    assert {field for row in roadmap_rows for field in row} == set(
        METHODOLOGY_PARITY_ROADMAP_FIELDS
    )
    assert [row["workstream_id"] for row in roadmap_rows[:3]] == [
        "core_support_numerator_parity",
        "denominator_comparability_bridge",
        "residual_replacement_channel_closure",
    ]
    assert len(roadmap_rows) == 4
    outputs = write_methodology_parity_outputs(
        tmp_path / "out",
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
        roadmap_rows=roadmap_rows,
    )
    assert outputs["channel_csv"].read_text(encoding="utf-8").startswith(
        "methodology_parity_channel_row_id,"
    )
    assert outputs["denominator_csv"].read_text(encoding="utf-8").startswith(
        "methodology_parity_denominator_row_id,"
    )
    assert outputs["roadmap_csv"].read_text(encoding="utf-8").startswith(
        "methodology_parity_roadmap_row_id,"
    )
    readout = methodology_parity_readout_markdown(
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
        roadmap_rows=roadmap_rows,
    )
    assert outputs["readout_md"].read_text(encoding="utf-8") == readout
    assert "not by deleting strong methods" in readout
    assert "core_support_numerator_parity" in readout
    assert "No row in this parity readout changes N, D, beta, chi" in readout


def _write_forecast_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "forecast"
    root.mkdir()
    _write_csv(
        root / "ratewall_forecast_channel_classification.csv",
        [
            _channel(
                "tdc_ex_overlap_current_demand_support",
                "TDC ex-overlap support",
                "included",
            ),
            _channel(
                "direct_treasury_interest_support",
                "Direct Treasury interest support",
                "included",
                selected_role="replacement_block_input_not_standalone",
            ),
            _channel(
                "net_interest_after_fiscal_tga_offsets",
                "net interest after fiscal tga offsets",
                "included_as_public_interest_replacement_block",
                selected_role="standalone_final_n_term",
            ),
            _channel(
                "firm_cash_attenuation",
                "firm cash attenuation",
                "projection_required_as_bounded_sensitivity",
            ),
            _channel(
                "safe_asset_allocation_drag",
                "safe asset allocation drag",
                "sidecar_until_disjoint_basis_exists",
            ),
        ],
    )
    _write_csv(
        root / "ratewall_forecast_numerator_channel_plan.csv",
        [
            {
                "channel_id": "safe_asset_allocation_drag",
                "next_model_action": "build_disjoint_basis_or_leave_sidecar",
            }
        ],
    )
    return root


def _channel(
    channel_id: str,
    label: str,
    classification: str,
    *,
    selected_role: str = "",
) -> dict[str, str]:
    return {
        "channel_id": channel_id,
        "channel_label": label,
        "classification": classification,
        "selected_central_entry_role": selected_role,
    }


def _write_denominator_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "denom.csv"
    _write_csv(
        path,
        [
            _denom(
                "rw_runtime_support_offset_af_fixed",
                "runtime_default_primary",
                "literature_annual_flow_bridge_candidate",
                "primary_runtime_default",
                "0.77600",
            ),
            _denom(
                "rw_forecast_wall_ratio_path",
                "forecast_primary_path_required",
                "forecast_path_denominator_v1_required",
                "primary_forecast_path_denominator",
                "0.77600",
            ),
            _denom(
                "rw_historical_wall_ratio_path",
                "historical_primary_path_required",
                "historical_path_denominator_v1_required",
                "primary_historical_path_denominator",
                "0.77600",
            ),
        ],
    )
    return path


def _denom(
    ratio_object_id: str,
    row_role: str,
    denominator_object_id: str,
    denominator_role: str,
    fixed_anchor: str,
) -> dict[str, str]:
    return {
        "ratio_object_id": ratio_object_id,
        "row_role": row_role,
        "denominator_object_id": denominator_object_id,
        "denominator_role": denominator_role,
        "fixed_anchor_component": fixed_anchor,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
