from __future__ import annotations

import pytest
import csv
from decimal import Decimal
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
BRIDGE_ARTIFACT = "ratewall_forecast_holder_tdc_consistency_bridge.csv"
CONTRACT_ARTIFACT = "ratewall_annual_support_numerator_contract.csv"
ARTIFACT = "ratewall_runtime_annual_flow_support_offset_scenarios.csv"
READINESS_ARTIFACT = "ratewall_runtime_annual_flow_support_offset_readiness_registry.csv"


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_runtime_support_offset_surface_materializes_default_sensitivity_and_blocked_rows() -> None:
    bridge_rows = _rows(BRIDGE_ARTIFACT)
    contract_rows = _rows(CONTRACT_ARTIFACT)
    rows = _rows(ARTIFACT)

    assert len(contract_rows) == len(bridge_rows)
    assert len(rows) == 6 * len(contract_rows)

    default_rows = [row for row in rows if row["default_runtime_anchor"] == "true"]
    assert len(default_rows) == len(contract_rows)
    assert {row["denominator_source_id"] for row in default_rows} == {
        "literature_annual_flow_bridge_candidate"
    }


def test_runtime_support_offset_surface_uses_literature_default_and_keeps_h8_family_blocked() -> None:
    rows = _rows(ARTIFACT)
    target_default = next(
        row
        for row in rows
        if row["forecast_year"] == "2026"
        and row["mpc_scenario"] == "base_mpc_10pct"
        and row["maturity_scenario"] == "current_wam_cbo_rate_path"
        and row["holder_scenario"] == "current_holder_distribution"
        and row["denominator_source_id"] == "literature_annual_flow_bridge_candidate"
    )
    support_pct = Decimal(target_default["support_gdp_pct"])
    center = Decimal(target_default["denominator_center_pp_gdp"])
    ci_low = Decimal(target_default["denominator_ci95_low_pp_gdp"])
    ci_high = Decimal(target_default["denominator_ci95_high_pp_gdp"])

    assert target_default["runtime_pairing_status"] == (
        "pass_default_runtime_support_offset_materialized"
    )
    assert target_default["numerator_runtime_allowed"] == "true"
    assert target_default["numerator_source_gate_status"] == (
        "pass_all_direct_runtime_components_source_classified"
    )
    assert target_default["denominator_runtime_allowed"] == "true"
    assert target_default["effective_runtime_output_allowed"] == "true"
    assert target_default["scenario_runtime_allowed"] == "true"
    assert target_default["numerator_uncertainty_artifact"] == (
        "ratewall_annual_support_numerator_uncertainty_envelope.csv"
    )
    expected_center = (support_pct / center).quantize(Decimal("0.000000000001"))
    expected_low = (support_pct / ci_high).quantize(Decimal("0.000000000001"))
    expected_high = (support_pct / ci_low).quantize(Decimal("0.000000000001"))
    assert (
        abs(
            Decimal(target_default["support_offset_100bp_year_equivalent"])
            - expected_center
        )
        <= Decimal("1e-12")
    )
    assert (
        abs(
            Decimal(target_default["support_offset_100bp_year_equivalent_lower_bound"])
            - expected_low
        )
        <= Decimal("1e-12")
    )
    assert (
        abs(
            Decimal(target_default["support_offset_100bp_year_equivalent_upper_bound"])
            - expected_high
        )
        <= Decimal("1e-12")
    )

    legacy = next(
        row
        for row in rows
        if row["forecast_year"] == "2026"
        and row["mpc_scenario"] == "base_mpc_10pct"
        and row["maturity_scenario"] == "current_wam_cbo_rate_path"
        and row["holder_scenario"] == "current_holder_distribution"
        and row["denominator_source_id"] == "legacy_assumption_anchor_base_current_100bps"
    )
    assert legacy["sensitivity_only"] == "true"
    assert legacy["runtime_pairing_status"] == (
        "pass_sensitivity_runtime_support_offset_materialized"
    )
    assert legacy["effective_runtime_output_allowed"] == "true"

    for source_id in (
        "bounded_h8_overlay_review_center",
        "literature_h8_mapped_review_only",
        "frbus_h8_component_proxy",
    ):
        blocked = next(
            row
            for row in rows
            if row["forecast_year"] == "2026"
            and row["mpc_scenario"] == "base_mpc_10pct"
            and row["maturity_scenario"] == "current_wam_cbo_rate_path"
            and row["holder_scenario"] == "current_holder_distribution"
            and row["denominator_source_id"] == source_id
        )
        assert blocked["scenario_runtime_allowed"] == "false"
        assert blocked["numerator_runtime_allowed"] == "true"
        assert blocked["numerator_source_gate_status"] == (
            "pass_all_direct_runtime_components_source_classified"
        )
        assert blocked["denominator_runtime_allowed"] == "false"
        assert blocked["effective_runtime_output_allowed"] == "false"
        assert blocked["runtime_pairing_status"] == (
            "blocked_not_timing_commensurate_for_support_offset"
        )
        assert blocked["support_offset_100bp_year_equivalent"] == ""
        assert blocked["support_offset_bp_year_equivalent"] == ""
        assert blocked["support_offset_100bp_year_equivalent_numerator_lower_bound"] == ""
        assert blocked["support_offset_bp_year_equivalent_numerator_upper_bound"] == ""


def test_runtime_support_offset_surface_keeps_forbidden_switches_false() -> None:
    for row in _rows(ARTIFACT):
        assert row["canonical_ratio_entry"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        for field in FORBIDDEN_SWITCH_FIELDS:
            assert row[field] == "false"


def test_runtime_support_offset_readiness_registry_joins_1_to_1_with_surface() -> None:
    scenario_rows = _rows(ARTIFACT)
    readiness_rows = _rows(READINESS_ARTIFACT)
    assert len(readiness_rows) == len(scenario_rows)

    readiness_by_id = {
        row["runtime_support_offset_row_id"]: row for row in readiness_rows
    }
    target = next(
        row
        for row in scenario_rows
        if row["forecast_year"] == "2026"
        and row["mpc_scenario"] == "base_mpc_10pct"
        and row["maturity_scenario"] == "current_wam_cbo_rate_path"
        and row["holder_scenario"] == "current_holder_distribution"
        and row["denominator_source_id"] == "literature_annual_flow_bridge_candidate"
    )
    readiness = readiness_by_id[target["runtime_support_offset_row_id"]]
    assert readiness["effective_runtime_output_allowed"] == "true"
    assert readiness["numerator_reconciliation_status"] == (
        "pass_direct_components_reconcile_to_runtime_numerator"
    )
    assert readiness["numerator_source_gate_status"] == (
        "pass_all_direct_runtime_components_source_classified"
    )
    assert readiness["scenario_runtime_allowed"] == "true"


def test_combined_tdcsim_contract_supports_runtime_support_offset_after_export() -> None:
    scenario_rows = _rows(ARTIFACT)
    readiness_rows = _rows(READINESS_ARTIFACT)
    readiness_by_id = {
        row["runtime_support_offset_row_id"]: row for row in readiness_rows
    }
    target = next(
        row
        for row in scenario_rows
        if row["forecast_year"] == "2026"
        and row["mpc_scenario"] == "base_mpc_10pct"
        and row["maturity_scenario"] == "higher_wam_slower_repricing"
        and row["holder_scenario"] == "shift_to_domestic_nonbanks"
        and row["denominator_source_id"] == "literature_annual_flow_bridge_candidate"
    )

    assert target["numerator_runtime_allowed"] == "true"
    assert target["numerator_source_gate_status"] == (
        "pass_all_direct_runtime_components_source_classified"
    )
    assert target["denominator_runtime_allowed"] == "true"
    assert target["effective_runtime_output_allowed"] == "true"
    assert target["scenario_runtime_allowed"] == "true"
    assert target["runtime_pairing_status"] == (
        "pass_default_runtime_support_offset_materialized"
    )
    assert target["support_offset_100bp_year_equivalent"] != ""
    assert target["exact_blocker"] == ""

    readiness = readiness_by_id[target["runtime_support_offset_row_id"]]
    assert readiness["readiness_tier"] == (
        "reportable_runtime_support_offset"
    )
    assert readiness["effective_runtime_output_allowed"] == "true"
