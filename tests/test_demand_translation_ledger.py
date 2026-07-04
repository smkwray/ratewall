from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from ratewall.databook.demand_translation_ledger import (
    DEMAND_TRANSLATION_LEDGER_FIELDS,
    OBJECT_ROLE_MATRIX_FIELDS,
    REGISTRY_FIELDS,
    DemandTranslationLedgerError,
    build_all,
    demand_translation_rows,
    object_role_rows,
    registry_rows,
    validate_demand_translation_ledger,
    validate_object_role_matrix,
    validate_registry,
    write_demand_translation_outputs,
)


def test_registry_exact_family_vector() -> None:
    rows = registry_rows()

    assert {field for row in rows for field in row} == set(REGISTRY_FIELDS)
    by_family = {row["family_id"]: row for row in rows}
    assert by_family["direct_private_cash_income"]["demand_translation_low"] == "0.05"
    assert by_family["direct_private_cash_income"]["demand_translation_base"] == "0.12"
    assert by_family["direct_private_cash_income"]["demand_translation_high"] == "0.25"
    assert by_family["intermediated_financial_income"]["demand_translation_low"] == "0.00"
    assert by_family["intermediated_financial_income"]["demand_translation_base"] == "0.03"
    assert by_family["intermediated_financial_income"]["demand_translation_high"] == "0.10"
    assert by_family["market_safe_yield_income"]["demand_translation_low"] == "0.02"
    assert by_family["market_safe_yield_income"]["demand_translation_base"] == "0.06"
    assert by_family["market_safe_yield_income"]["demand_translation_high"] == "0.12"
    assert by_family["spendable_liquidity_inflow"]["demand_translation_low"] == "0.03"
    assert by_family["spendable_liquidity_inflow"]["demand_translation_base"] == "0.07"
    assert by_family["spendable_liquidity_inflow"]["demand_translation_high"] == "0.12"
    assert by_family["realized_household_safe_yield_income"]["demand_translation_low"] == "0.04"
    assert by_family["realized_household_safe_yield_income"]["demand_translation_base"] == "0.08"
    assert by_family["realized_household_safe_yield_income"]["demand_translation_high"] == "0.13"
    assert by_family["wealth_revaluation"]["demand_translation_low"] == ""
    assert by_family["wealth_revaluation"]["demand_translation_base"] == ""
    assert by_family["wealth_revaluation"]["demand_translation_high"] == ""
    assert by_family["firm_liquidity_cushion"]["demand_translation_low"] == "0.03"
    assert by_family["firm_liquidity_cushion"]["demand_translation_base"] == "0.10"
    assert by_family["firm_liquidity_cushion"]["demand_translation_high"] == "0.20"
    assert {row["headline_selector_id"] for row in rows} == {
        "demand_translation_strength"
    }


def test_required_schema_columns_present_and_inventory() -> None:
    tables = build_all()
    registry = tables["registry_rows"]
    object_rows = tables["object_role_rows"]
    ledger = tables["demand_translation_rows"]

    assert {field for row in object_rows for field in row} == set(
        OBJECT_ROLE_MATRIX_FIELDS
    )
    assert {field for row in ledger for field in row} == set(
        DEMAND_TRANSLATION_LEDGER_FIELDS
    )
    assert len(object_rows) == len(ledger)
    by_id = {row["ledger_row_id"]: row for row in object_rows}
    required = {
        "forecast_public_interest_net_block",
        "forecast_tdc_ex_overlap_beta_chi",
        "forecast_conventional_D",
        "current_assumption_benchmark_2026",
        "current_runtime_public_interest_benchmark_component",
        "current_runtime_legacy_tdc_benchmark_component",
        "current_conventional_D",
        "current_r38_public_interest_candidate",
        "current_r38_tdc_beta_chi_candidate",
        "current_d1_safe_yield_bounded_fallback",
        "historical_public_interest_context",
        "historical_tdc_mechanism_context",
        "historical_direct_treasury_decomposition",
        "historical_conventional_D_context",
        "deposit_realized_safe_yield_required_theory",
        "mmf_realized_safe_yield_diagnostic",
        "tbill_realized_safe_yield_diagnostic",
        "safe_asset_allocation_drag_sidecar",
        "firm_cash_attenuation_sensitivity",
        "firm_liquid_asset_cushion_replacement",
        "firm_rollover_pressure_credit_sidecar",
        "zero_low_apr_credit_diagnostic",
    }
    assert required <= set(by_id)
    assert {row["period_object"] for row in object_rows} == {
        "forecast",
        "current",
        "historical",
    }
    assert len(registry) == 7


def test_selected_value_recast_does_not_drift_and_tdc_locks_hold() -> None:
    ledger = demand_translation_rows()
    by_id = {row["ledger_row_id"]: row for row in ledger}

    current = by_id["current_assumption_benchmark_2026"]
    assert current["selected_value_bil"] == "83.542224868775"
    assert current["selected_d_bil"] == "247.55956656"
    assert current["selected_rw"] == "0.337463124652"
    assert by_id["current_runtime_public_interest_benchmark_component"][
        "selected_value_bil"
    ] == "56.03251655775289810515522913"
    assert by_id["current_runtime_legacy_tdc_benchmark_component"][
        "selected_value_bil"
    ] == "27.50970831102218887944538608"
    assert by_id["current_r38_tdc_beta_chi_candidate"]["selected_value_bil"] == (
        "19.25679581771553221561177026"
    )
    assert by_id["forecast_tdc_ex_overlap_beta_chi"]["support_formula"] == (
        "tdc_change_ex_overlap_bil * beta * chi"
    )
    assert by_id["historical_tdc_mechanism_context"]["support_formula"] == (
        "tdc_ex_overlap_support_bil + public_interest_net_block_partial_bil"
    )


def test_gate_and_role_guardrails() -> None:
    object_rows = object_role_rows()
    ledger = demand_translation_rows(object_rows=object_rows)

    assert [
        row["ledger_row_id"]
        for row in object_rows
        if row["period_object"] == "current"
        and row["selected_n_inclusion"] == "true"
    ] == ["current_assumption_benchmark_2026"]
    assert all(
        row["selected_historical_n_includes_tdc"] == "false"
        for row in object_rows
        if row["period_object"] == "historical"
    )
    assert all(
        row["classifier_allowed"] == "false"
        for row in object_rows
        if row["period_object"] == "historical"
    )
    assert all(
        row["selected_n_inclusion"] == "false"
        for row in object_rows
        if "direct_treasury" in row["source_channel_id"]
    )
    assert all(
        row["central_n_delta_bil_allowed"] == "false"
        for row in ledger
        if row["source_channel_id"] == "safe_asset_allocation_drag"
    )
    assert all("base_mpc_10pct" not in row["demand_translation_family_id"] for row in ledger)


def test_outputs_are_written(tmp_path: Path) -> None:
    tables = build_all()

    outputs = write_demand_translation_outputs(
        tmp_path / "out",
        registry_rows=tables["registry_rows"],
        object_role_rows=tables["object_role_rows"],
        demand_translation_rows=tables["demand_translation_rows"],
    )

    assert outputs["registry_csv"].read_text(encoding="utf-8").startswith(
        "family_id,"
    )
    assert outputs["object_role_matrix_csv"].read_text(encoding="utf-8").startswith(
        "ledger_row_id,"
    )
    assert outputs["ledger_csv"].read_text(encoding="utf-8").startswith(
        "demand_translation_ledger_row_id,"
    )


def test_bad_fixture_rejects_full_value_tdc_support() -> None:
    rows = demand_translation_rows()
    bad = deepcopy(rows)
    row = _row_by_id(bad, "forecast_tdc_ex_overlap_beta_chi")
    row["support_formula"] = "tdc_full_bil * beta * chi"

    with pytest.raises(DemandTranslationLedgerError, match="full TDC"):
        validate_demand_translation_ledger(bad)


def test_bad_fixture_rejects_generic_mpc_registry_family() -> None:
    rows = registry_rows()
    bad = deepcopy(rows)
    bad[0] = dict(bad[0], family_id="base_mpc_10pct")

    with pytest.raises(DemandTranslationLedgerError, match="family mismatch"):
        validate_registry(bad)


def test_bad_fixture_rejects_stock_only_selected_support() -> None:
    rows = object_role_rows()
    bad = deepcopy(rows)
    row = _row_by_id(bad, "forecast_public_interest_net_block")
    row["inflow_kind"] = "stock_context"

    with pytest.raises(DemandTranslationLedgerError, match="stock-only"):
        validate_object_role_matrix(bad)


def test_bad_fixture_rejects_direct_treasury_double_count() -> None:
    rows = demand_translation_rows()
    bad = deepcopy(rows)
    row = _row_by_id(bad, "historical_tdc_mechanism_context")
    row["support_formula"] = (
        "tdc_ex_overlap_support_bil + direct_treasury_interest_support_bil + "
        "public_interest_net_block_partial_bil"
    )

    with pytest.raises(DemandTranslationLedgerError, match="direct Treasury"):
        validate_demand_translation_ledger(bad)


def test_bad_fixture_rejects_hybrid_current_rows() -> None:
    rows = object_role_rows()
    bad = deepcopy(rows)
    row = _row_by_id(bad, "current_r38_tdc_beta_chi_candidate")
    row["selected_n_inclusion"] = "true"
    row["rate_or_scenario_attribution_status"] = "pass_bad_fixture"
    row["flow_basis_status"] = "pass_bad_fixture"
    row["same_period_denominator_status"] = "pass_bad_fixture"
    row["overlap_status"] = "pass_bad_fixture"
    row["selection_gate_status"] = "pass_bad_fixture"

    with pytest.raises(DemandTranslationLedgerError, match="selected current"):
        validate_object_role_matrix(bad)


def test_bad_fixture_rejects_wealth_and_safe_asset_support() -> None:
    rows = demand_translation_rows()
    wealth_bad = deepcopy(rows)
    _row_by_id(wealth_bad, "firm_rollover_pressure_credit_sidecar")[
        "selected_value_bil"
    ] = "1"
    with pytest.raises(DemandTranslationLedgerError, match="wealth revaluation"):
        validate_demand_translation_ledger(wealth_bad)

    safe_asset_bad = deepcopy(rows)
    _row_by_id(safe_asset_bad, "safe_asset_allocation_drag_sidecar")[
        "central_n_delta_bil_allowed"
    ] = "true"
    with pytest.raises(DemandTranslationLedgerError, match="safe-asset"):
        validate_demand_translation_ledger(safe_asset_bad)


def test_bad_fixture_rejects_independent_headline_sliders() -> None:
    rows = registry_rows()
    bad = deepcopy(rows)
    bad[0]["headline_selector_id"] = "tdc_demand_slider"

    with pytest.raises(DemandTranslationLedgerError, match="headline selector"):
        validate_registry(bad)


def _row_by_id(rows: list[dict[str, str]], row_id: str) -> dict[str, str]:
    return next(row for row in rows if row["ledger_row_id"] == row_id)
