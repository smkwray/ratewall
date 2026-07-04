from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.core_support_parity import (
    CORE_SUPPORT_NUMERATOR_FIELDS,
    CORE_SUPPORT_OVERLAP_AUDIT_FIELDS,
    PUBLIC_INTEREST_NET_BLOCK_SHARED_FIELDS,
    TDC_EX_OVERLAP_SUPPORT_SHARED_FIELDS,
    core_support_numerator_rows,
    core_support_overlap_audit_rows,
    public_interest_net_block_shared_rows,
    tdc_ex_overlap_support_shared_rows,
    write_core_support_parity_outputs,
)


def test_core_support_numerator_surface_keeps_replacement_inputs_nonadditive(
    tmp_path: Path,
) -> None:
    root = _write_forecast_fixture(tmp_path)

    rows = core_support_numerator_rows(forecast_readout_dir=root)
    audit_rows = core_support_overlap_audit_rows(rows)

    assert {field for row in rows for field in row} == set(
        CORE_SUPPORT_NUMERATOR_FIELDS
    )
    assert {field for row in audit_rows for field in row} == set(
        CORE_SUPPORT_OVERLAP_AUDIT_FIELDS
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["tdc_current_demand_support_bil"] == "2.5"
    assert row["public_interest_net_block_bil"] == "7.5"
    assert row["core_support_n_bil"] == "10.0"
    assert row["central_surface_n_bil"] == "10.0"
    assert row["identity_error_bil"] == "0.0"
    assert row["direct_treasury_entry_role"] == (
        "replacement_block_input_not_standalone"
    )
    assert row["bank_treasury_entry_role"] == (
        "replacement_block_input_not_standalone"
    )
    assert row["public_interest_entry_role"] == "standalone_final_n_term"
    assert row["tdc_entry_role"] == "standalone_final_n_term"
    assert {audit["check_status"] for audit in audit_rows} == {"pass"}


def test_shared_public_interest_and_tdc_component_rows(tmp_path: Path) -> None:
    root = _write_forecast_fixture(tmp_path)

    public_interest_rows = public_interest_net_block_shared_rows(
        forecast_readout_dir=root
    )
    tdc_rows = tdc_ex_overlap_support_shared_rows(forecast_readout_dir=root)

    assert {field for row in public_interest_rows for field in row} == set(
        PUBLIC_INTEREST_NET_BLOCK_SHARED_FIELDS
    )
    assert {field for row in tdc_rows for field in row} == set(
        TDC_EX_OVERLAP_SUPPORT_SHARED_FIELDS
    )
    public_interest = public_interest_rows[0]
    assert public_interest["direct_treasury_entry_role"] == (
        "replacement_block_input_not_standalone"
    )
    assert public_interest["net_interest_after_fiscal_tga_offsets_bil"] == "7.5"
    tdc = tdc_rows[0]
    assert tdc["support_formula"] == (
        "tdc_current_demand_support_bil=tdc_change_ex_overlap_bil*beta*chi"
    )
    assert tdc["tdcsim_mmf_routing_or_offset_coefficient"] == "0.97"
    assert tdc["tdcsim_mmf_routing_role"] == (
        "holder_route_correction_not_beta_not_chi"
    )


def test_core_support_outputs_are_written(tmp_path: Path) -> None:
    root = _write_forecast_fixture(tmp_path)
    public_interest_rows = public_interest_net_block_shared_rows(
        forecast_readout_dir=root
    )
    tdc_rows = tdc_ex_overlap_support_shared_rows(forecast_readout_dir=root)
    rows = core_support_numerator_rows(forecast_readout_dir=root)
    audit_rows = core_support_overlap_audit_rows(rows)

    outputs = write_core_support_parity_outputs(
        tmp_path / "out",
        public_interest_rows=public_interest_rows,
        tdc_rows=tdc_rows,
        rows=rows,
        audit_rows=audit_rows,
    )

    assert outputs["public_interest_csv"].read_text(encoding="utf-8").startswith(
        "public_interest_net_block_row_id,"
    )
    assert outputs["tdc_csv"].read_text(encoding="utf-8").startswith(
        "tdc_ex_overlap_support_row_id,"
    )
    assert outputs["core_support_csv"].read_text(encoding="utf-8").startswith(
        "core_support_numerator_row_id,"
    )
    assert outputs["overlap_audit_csv"].read_text(encoding="utf-8").startswith(
        "core_support_overlap_audit_row_id,"
    )


def _write_forecast_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "forecast"
    root.mkdir()
    _write_csv(
        root / "ratewall_forecast_timed_beta_paths.csv",
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "baseline",
                "baseline_scenario_id": "baseline",
                "beta_path_id": "normal_forward_constant",
                "tdc_materialization_beta_scenario": "normal_forward",
                "tdc_materialization_beta": "0.34201759129420367",
                "deposit_current_demand_share": "0.07",
                "derived_beta_times_chi": "0.0239412313905942569",
                "tdc_change_ex_overlap_bil": "104.421529",
                "tdc_current_demand_support_bil_recomputed": "2.5",
            }
        ],
    )
    _write_csv(
        root / "ratewall_forecast_public_interest_net_block.csv",
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "baseline",
                "baseline_scenario_id": "baseline",
                "legacy_interest_support_bil": "11",
                "direct_treasury_current_demand_support_bil": "10",
                "bank_treasury_current_demand_support_bil": "1",
                "projected_iorb_current_demand_support_bil": "1",
                "projected_on_rrp_current_demand_support_bil": "0.5",
                "projected_current_remittance_demand_offset_bil": "0",
                "projected_future_remittance_drag_demand_offset_bil": "0",
                "gross_public_interest_current_demand_support_bil": "12.5",
                "interest_income_tax_timing_drag_bil": "2",
                "fiscal_offset_bil": "2",
                "tga_liquidity_offset_bil": "1",
                "net_interest_after_fiscal_tga_offsets_bil": "7.5",
                "replacement_delta_vs_legacy_interest_support_bil": "-3.5",
                "composition_rule": (
                    "final_interest_block_replaces_legacy_direct_plus_bank_rows_"
                    "never_add_both"
                ),
            }
        ],
    )
    _write_csv(
        root / "ratewall_forecast_central_scenario_surface.csv",
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "baseline",
                "baseline_scenario_id": "baseline",
                "central_n_bil": "10.0",
                "central_moving_denominator_bil": "40",
                "central_ratewall_ratio": "0.25",
            }
        ],
    )
    _write_csv(
        root / "ratewall_forecast_channel_classification.csv",
        [
            _channel("tdc_ex_overlap_current_demand_support", "standalone_final_n_term"),
            _channel(
                "direct_treasury_interest_support",
                "replacement_block_input_not_standalone",
            ),
            _channel(
                "bank_treasury_interest_support",
                "replacement_block_input_not_standalone",
            ),
            _channel("net_interest_after_fiscal_tga_offsets", "standalone_final_n_term"),
        ],
    )
    return root


def _channel(channel_id: str, selected_role: str) -> dict[str, str]:
    return {
        "channel_id": channel_id,
        "selected_central_entry_role": selected_role,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
