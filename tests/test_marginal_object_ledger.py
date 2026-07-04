from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from ratewall.databook.marginal_object_ledger import (
    COMPLETE_MARGINAL_CHANNEL_INVENTORY_FIELDS,
    MARGINAL_CHANNEL_STATUS_FIELDS,
    MARGINAL_OBJECT_CONTRACT_FIELDS,
    MARGINAL_ROW_ROLE_RESET_FIELDS,
    MarginalObjectLedgerError,
    build_all,
    complete_marginal_channel_inventory_rows,
    marginal_channel_status_rows,
    marginal_object_contract_rows,
    marginal_row_role_reset_rows,
    validate_complete_marginal_channel_inventory,
    validate_marginal_channel_status,
    validate_marginal_object_contract,
    validate_marginal_row_role_reset,
    write_marginal_object_ledger_outputs,
)


def test_marginal_object_contract_locks_rw_m_formula() -> None:
    rows = marginal_object_contract_rows()

    assert {field for row in rows for field in row} == set(
        MARGINAL_OBJECT_CONTRACT_FIELDS
    )
    assert {row["period_object"] for row in rows} == {
        "historical",
        "current",
        "forecast",
    }
    for row in rows:
        assert row["marginal_object_id"] == "RW_M_PLUS_100BP_YEAR"
        assert row["rw_m_formula"] == (
            "Delta_N[t,h](+100bp-year | S_t) / Delta_D_conv[t,h](+100bp-year | S_t)"
        )
        assert row["shock_path_id"] == "plus_100bp_year"
        assert row["shock_bps_year"] == "100"
        assert row["same_state_pair_required"] == "true"
        assert row["selected_rw_m"] == "false"
        assert "same_state_shock_minus_baseline_delta_N_required" in row["selected_n_basis"]
        assert "select_old_current_benchmark" in row["blocked_use"]


def test_marginal_channel_registry_keeps_channels_but_demotes_old_forms() -> None:
    rows = marginal_channel_status_rows()

    assert {field for row in rows for field in row} == set(
        MARGINAL_CHANNEL_STATUS_FIELDS
    )
    by_id = {row["channel_id"]: row for row in rows}
    assert {
        "public_interest_net_block",
        "tdc_ex_overlap_beta_chi",
        "conventional_demand_drag",
        "deposit_safe_yield_payer_flow",
        "legacy_current_benchmark",
        "legacy_forecast_ratio",
        "historical_classifier",
        "old_historical_path_d",
        "old_exposure_ratio_generic",
        "remittance_state",
        "firm_cash_liquidity",
        "zero_low_apr_credit",
    } <= set(by_id)
    assert {row["fail_closed_label"] for row in rows} >= {
        "fail_closed_non_marginal_selected_n",
        "fail_closed_non_marginal_selected_d",
        "fail_closed_old_exposure_ratio_promoted",
        "fail_closed_previous_current_benchmark_selected_as_rw_m",
        "fail_closed_forecast_v1_ratio_selected_as_rw_m",
        "fail_closed_historical_classifier_without_marginal_n",
        "fail_closed_block_input_used_as_standalone_n",
        "fail_closed_denominator_drag_booked_as_n",
    }
    assert by_id["tdc_ex_overlap_beta_chi"]["numerator_formula"] == (
        "delta_tdc_ex_overlap_bil * beta * chi"
    )
    assert "full_tdc_level" in by_id["tdc_ex_overlap_beta_chi"]["blocked_use"]
    assert by_id["conventional_demand_drag"]["final_role"] == "selected_marginal_d"
    assert "numerator_support" in by_id["conventional_demand_drag"]["blocked_use"]
    assert by_id["legacy_current_benchmark"]["promotion_status"] == (
        "blocked_old_exposure_ratio"
    )
    assert by_id["legacy_forecast_ratio"]["promotion_status"] == (
        "blocked_old_exposure_ratio"
    )
    assert by_id["deposit_safe_yield_payer_flow"]["viability_status"].startswith(
        "viable_if_payer_flow"
    )
    assert by_id["remittance_state"]["final_role"] == "selected_marginal_block_input"
    assert by_id["firm_cash_liquidity"]["final_role"] == "denominator_only"
    assert by_id["zero_low_apr_credit"]["final_role"] == "denominator_only"


def test_row_role_reset_classifies_existing_selected_exposure_rows(tmp_path: Path) -> None:
    paths = _write_row_reset_fixtures(tmp_path)

    rows = marginal_row_role_reset_rows(
        current_bridge_path=paths["current"],
        forecast_surface_path=paths["forecast"],
        historical_root_path=paths["historical_root"],
        historical_denominator_path=paths["historical_denominator"],
    )

    assert {field for row in rows for field in row} == set(
        MARGINAL_ROW_ROLE_RESET_FIELDS
    )
    assert {row["fail_closed_label"] for row in rows} >= {
        "fail_closed_non_marginal_selected_n",
        "fail_closed_non_marginal_selected_d",
        "fail_closed_old_exposure_ratio_promoted",
        "fail_closed_previous_current_benchmark_selected_as_rw_m",
        "fail_closed_forecast_v1_ratio_selected_as_rw_m",
        "fail_closed_historical_classifier_without_marginal_n",
        "fail_closed_block_input_used_as_standalone_n",
        "fail_closed_denominator_drag_booked_as_n",
    }
    assert {row["selected_final_rw_m_allowed"] for row in rows} == {"false"}
    assert {
        "selected_marginal_block_input",
        "candidate_marginal_replacement",
        "diagnostic_exposure_only",
        "sensitivity_only",
        "denominator_only",
    } <= {row["marginal_role"] for row in rows}


def test_complete_inventory_covers_required_marginal_channels(tmp_path: Path) -> None:
    paths = _write_row_reset_fixtures(tmp_path)
    channel_rows = marginal_channel_status_rows()
    reset_rows = marginal_row_role_reset_rows(
        current_bridge_path=paths["current"],
        forecast_surface_path=paths["forecast"],
        historical_root_path=paths["historical_root"],
        historical_denominator_path=paths["historical_denominator"],
    )

    rows = complete_marginal_channel_inventory_rows(
        channel_status_rows=channel_rows,
        row_role_reset_rows=reset_rows,
    )

    assert {field for row in rows for field in row} == set(
        COMPLETE_MARGINAL_CHANNEL_INVENTORY_FIELDS
    )
    by_id = {row["prior_channel_id"]: row for row in rows}
    assert {
        "public_interest_direct_treasury_interest",
        "public_interest_bank_treasury_interest",
        "public_interest_iorb_reserves",
        "public_interest_on_rrp",
        "public_interest_remittance_deferred_asset",
        "public_interest_tax_timing",
        "public_interest_fiscal_tga_liquidity",
        "public_interest_foreign_holder_leakage",
        "tdc_ex_overlap_beta_chi",
        "tdcsim_rate25_derivative_proxy",
        "deposit_safe_yield_payer_flow",
        "deposit_safe_yield_stock_rate_fallback",
        "zero_low_apr_credit",
        "credit_card_promo_bnpl",
        "firm_rollover_pressure",
        "residual_safe_asset_drag",
        "conventional_demand_drag",
    } <= set(by_id)
    assert by_id["tdc_ex_overlap_beta_chi"]["required_formula"] == (
        "delta_tdc_ex_overlap_bil * beta * chi"
    )
    assert "full_tdc_level" in by_id["tdc_ex_overlap_beta_chi"]["blocked_use"]
    assert "current_overlay_support" in by_id["tdc_ex_overlap_beta_chi"]["blocked_use"]
    assert by_id["tdcsim_rate25_derivative_proxy"]["marginal_status"] == (
        "sensitivity_only"
    )
    assert by_id["conventional_demand_drag"]["required_formula"] == (
        "nominal_gdp_bil * c_D * (shock_bps_year / 100) * state_multiplier"
    )
    for blocked in [
        "current_rate_level",
        "old_path_D",
        "tdc_stock",
        "deposit_stock",
        "beta",
        "chi",
        "numerator_size",
        "scenario_label",
    ]:
        assert blocked in by_id["conventional_demand_drag"]["blocked_use"]


def test_marginal_ledger_outputs_are_written(tmp_path: Path) -> None:
    tables = build_all()

    outputs = write_marginal_object_ledger_outputs(
        tmp_path / "out",
        contract_rows=tables["contract_rows"],
        channel_status_rows=tables["channel_status_rows"],
        row_role_reset_rows=tables["row_role_reset_rows"],
        complete_inventory_rows=tables["complete_inventory_rows"],
    )

    assert outputs["contract_csv"].read_text(encoding="utf-8").startswith(
        "marginal_object_contract_row_id,"
    )
    assert outputs["channel_status_csv"].read_text(encoding="utf-8").startswith(
        "marginal_channel_status_row_id,"
    )
    assert outputs["row_role_reset_csv"].read_text(encoding="utf-8").startswith(
        "marginal_row_role_reset_row_id,"
    )
    assert outputs["complete_inventory_csv"].read_text(encoding="utf-8").startswith(
        "prior_channel_id,"
    )


def test_bad_contract_rejects_selected_old_ratio() -> None:
    rows = marginal_object_contract_rows()
    bad = deepcopy(rows)
    bad[0]["selected_rw_m"] = "true"

    with pytest.raises(MarginalObjectLedgerError, match="cannot be selected"):
        validate_marginal_object_contract(bad)


def test_bad_channel_rejects_full_tdc_formula() -> None:
    rows = marginal_channel_status_rows()
    bad = deepcopy(rows)
    for row in bad:
        if row["channel_id"] == "tdc_ex_overlap_beta_chi":
            row["numerator_formula"] = "tdc_full_bil * beta * chi"

    with pytest.raises(MarginalObjectLedgerError, match="TDC must use marginal"):
        validate_marginal_channel_status(bad)


def test_bad_channel_rejects_legacy_ratio_promotion() -> None:
    rows = marginal_channel_status_rows()
    bad = deepcopy(rows)
    for row in bad:
        if row["channel_id"] == "legacy_current_benchmark":
            row["promotion_status"] = "selected_rw_m"

    with pytest.raises(MarginalObjectLedgerError, match="legacy exposure"):
        validate_marginal_channel_status(bad)


def test_bad_row_role_reset_rejects_old_row_promotion(tmp_path: Path) -> None:
    paths = _write_row_reset_fixtures(tmp_path)
    rows = marginal_row_role_reset_rows(
        current_bridge_path=paths["current"],
        forecast_surface_path=paths["forecast"],
        historical_root_path=paths["historical_root"],
        historical_denominator_path=paths["historical_denominator"],
    )
    bad = deepcopy(rows)
    bad[0]["selected_final_rw_m_allowed"] = "true"

    with pytest.raises(MarginalObjectLedgerError, match="cannot enter"):
        validate_marginal_row_role_reset(bad)


def test_bad_complete_inventory_rejects_missing_denominator_blocker() -> None:
    rows = complete_marginal_channel_inventory_rows()
    bad = deepcopy(rows)
    for row in bad:
        if row["prior_channel_id"] == "conventional_demand_drag":
            row["blocked_use"] = row["blocked_use"].replace(";beta", "")

    with pytest.raises(MarginalObjectLedgerError, match="denominator inventory"):
        validate_complete_marginal_channel_inventory(bad)


def _write_row_reset_fixtures(tmp_path: Path) -> dict[str, Path]:
    current = tmp_path / "current.csv"
    _write_csv(
        current,
        [
            {
                "current_object_bridge_row_id": "current_object_bridge::selected_runtime_benchmark",
                "current_object_id": "current_assumption_benchmark::2026",
                "period_object": "current",
                "source_surface": "current_assumption_runtime",
                "selected_current_row": "true",
                "selected_current_component": "false",
                "current_object_role": "selected_benchmark_recast",
            },
            {
                "current_object_bridge_row_id": "current_object_bridge::selected_public_interest_component",
                "current_object_id": "current_runtime_public_interest_component",
                "period_object": "current",
                "source_surface": "current_assumption_runtime",
                "selected_current_row": "false",
                "selected_current_component": "true",
                "current_object_role": "selected_block_input",
            },
            {
                "current_object_bridge_row_id": "current_object_bridge::selected_legacy_runtime_tdc_component",
                "current_object_id": "current_runtime_legacy_tdc_component",
                "period_object": "current",
                "source_surface": "current_assumption_runtime",
                "selected_current_row": "false",
                "selected_current_component": "true",
                "current_object_role": "selected_block_input",
            },
            {
                "current_object_bridge_row_id": "current_object_bridge::r38_beta_chi_tdc_candidate",
                "current_object_id": "r38_beta_chi_tdc_candidate",
                "period_object": "current",
                "source_surface": "current_observed_overlay",
                "selected_current_row": "false",
                "selected_current_component": "false",
                "current_object_role": "candidate_replacement",
            },
            {
                "current_object_bridge_row_id": "current_object_bridge::d1_safe_yield_bounded_base",
                "current_object_id": "d1_safe_yield_bounded_base",
                "period_object": "current",
                "source_surface": "realized_safe_yield_income",
                "selected_current_row": "false",
                "selected_current_component": "false",
                "current_object_role": "sensitivity_only",
            },
            {
                "current_object_bridge_row_id": "current_object_bridge::legacy_static_lane",
                "current_object_id": "rw_legacy_static_assumption_mode",
                "period_object": "current",
                "source_surface": "legacy_static_reference",
                "selected_current_row": "false",
                "selected_current_component": "false",
                "current_object_role": "sensitivity_only",
            },
        ],
    )
    forecast = tmp_path / "forecast.csv"
    _write_csv(
        forecast,
        [
            {
                "central_forecast_surface_row_id": "central_forecast_surface::2027::baseline",
                "fiscal_year": "2027",
                "scenario_id": "baseline",
                "central_choice_status": "selected_model_surface",
            }
        ],
    )
    historical_root = tmp_path / "historical_root.csv"
    _write_csv(
        historical_root,
        [
            {
                "historical_root_public_interest_rw_row_id": "historical_root::2021Q4::base",
                "period": "2021Q4",
                "assumption_case": "base",
                "series_role": "historical_root_public_interest_context",
            }
        ],
    )
    historical_denominator = tmp_path / "historical_denominator.csv"
    _write_csv(
        historical_denominator,
        [
            {
                "historical_denominator_convention_row_id": "historical_denominator::2021Q4",
                "period": "2021Q4",
                "selected_convention": "cbo_quarterly_fed_funds_rate_path_D",
            }
        ],
    )
    return {
        "current": current,
        "forecast": forecast,
        "historical_root": historical_root,
        "historical_denominator": historical_denominator,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        import csv

        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
