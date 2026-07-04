from __future__ import annotations

import pytest
import csv
from pathlib import Path

from ratewall.databook.denominator_bridge_program import (

    _annual_support_numerator_contract_rows,
    _annual_support_numerator_source_gate_rows,
    _annual_support_numerator_uncertainty_envelope_rows,
    _runtime_annual_flow_support_offset_readiness_registry_rows,
    _runtime_annual_flow_support_offset_scenario_rows,
)



pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_failing_component_reconciliation_blocks_numerator_contract_runtime_use() -> None:
    component_rows = _rows("ratewall_annual_support_numerator_component_registry.csv")
    bridge_rows = _rows("ratewall_forecast_holder_tdc_consistency_bridge.csv")

    target_key = (
        "2026",
        "base_mpc_10pct",
        "current_wam_cbo_rate_path",
        "current_holder_distribution",
    )
    mutated_rows: list[dict[str, str]] = []
    for row in component_rows:
        mutated = dict(row)
        if (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
            row["component_id"],
        ) == (*target_key, "tdc_deposit_current_demand_support"):
            mutated["component_value_bil"] = "9999"
        mutated_rows.append(mutated)

    contract_rows = _annual_support_numerator_contract_rows(
        annual_support_numerator_component_registry_rows=mutated_rows,
        forecast_holder_tdc_consistency_bridge_rows=bridge_rows,
    )
    target = next(
        row
        for row in contract_rows
        if (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
        )
        == target_key
    )
    assert target["runtime_allowed"] == "false"
    assert target["reconciliation_status"] == (
        "blocked_runtime_direct_components_fail_to_reconcile"
    )
    assert "reconcile exactly" in target["exact_blocker"]


def test_failing_numerator_contract_blanks_runtime_offsets_but_preserves_denominator_policy() -> None:
    component_rows = _rows("ratewall_annual_support_numerator_component_registry.csv")
    bridge_rows = _rows("ratewall_forecast_holder_tdc_consistency_bridge.csv")
    contract_rows = _rows("ratewall_annual_support_numerator_contract.csv")
    anchor_rows = _rows("ratewall_annual_flow_denominator_anchor_registry.csv")
    runtime_family_rows = _rows("ratewall_annual_flow_runtime_family_registry.csv")
    compatibility_rows = _rows(
        "ratewall_annual_support_denominator_compatibility_registry.csv"
    )

    target_key = (
        "2026",
        "base_mpc_10pct",
        "current_wam_cbo_rate_path",
        "current_holder_distribution",
    )
    failing_contract_rows: list[dict[str, str]] = []
    for row in contract_rows:
        mutated = dict(row)
        if (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
        ) == target_key:
            mutated["runtime_allowed"] = "false"
            mutated["reconciliation_status"] = (
                "blocked_runtime_direct_components_fail_to_reconcile"
            )
            mutated["exact_blocker"] = (
                "Synthetic failing contract row for regression coverage."
            )
        failing_contract_rows.append(mutated)

    source_gate_rows = _annual_support_numerator_source_gate_rows(
        annual_support_numerator_component_registry_rows=component_rows,
        forecast_holder_tdc_consistency_bridge_rows=bridge_rows,
    )
    uncertainty_envelope_rows = _annual_support_numerator_uncertainty_envelope_rows(
        annual_support_numerator_contract_rows=failing_contract_rows,
        annual_support_numerator_source_gate_rows=source_gate_rows,
    )
    scenario_rows = _runtime_annual_flow_support_offset_scenario_rows(
        annual_support_numerator_contract_rows=failing_contract_rows,
        annual_support_numerator_source_gate_rows=source_gate_rows,
        annual_support_numerator_uncertainty_envelope_rows=uncertainty_envelope_rows,
        annual_flow_anchor_registry_rows=anchor_rows,
        annual_flow_runtime_family_registry_rows=runtime_family_rows,
        annual_support_denominator_compatibility_registry_rows=compatibility_rows,
    )
    default_row = next(
        row
        for row in scenario_rows
        if (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
            row["denominator_source_id"],
        )
        == (*target_key, "literature_annual_flow_bridge_candidate")
    )
    assert default_row["numerator_runtime_allowed"] == "false"
    assert default_row["numerator_source_gate_status"] == (
        "pass_all_direct_runtime_components_source_classified"
    )
    assert default_row["denominator_runtime_allowed"] == "true"
    assert default_row["effective_runtime_output_allowed"] == "false"
    assert default_row["scenario_runtime_allowed"] == "false"
    assert default_row["runtime_pairing_status"] == (
        "blocked_numerator_contract_not_runtime_usable"
    )
    assert default_row["support_offset_100bp_year_equivalent"] == ""
    assert default_row["support_offset_bp_year_equivalent"] == ""

    blocked_h8 = next(
        row
        for row in scenario_rows
        if (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
            row["denominator_source_id"],
        )
        == (*target_key, "bounded_h8_overlay_review_center")
    )
    assert blocked_h8["denominator_runtime_allowed"] == "false"
    assert blocked_h8["runtime_pairing_status"] == (
        "blocked_numerator_contract_not_runtime_usable"
    )

    readiness_rows = _runtime_annual_flow_support_offset_readiness_registry_rows(
        runtime_annual_flow_support_offset_scenario_rows=scenario_rows
    )
    readiness = next(
        row
        for row in readiness_rows
        if row["runtime_support_offset_row_id"]
        == default_row["runtime_support_offset_row_id"]
    )
    assert readiness["effective_runtime_output_allowed"] == "false"
    assert readiness["readiness_tier"] == (
        "blocked_runtime_support_offset_numerator_contract"
    )


def test_failing_numerator_source_gate_blanks_runtime_offsets_but_preserves_contract() -> None:
    source_gate_rows = _rows("ratewall_annual_support_numerator_source_gate.csv")
    contract_rows = _rows("ratewall_annual_support_numerator_contract.csv")
    anchor_rows = _rows("ratewall_annual_flow_denominator_anchor_registry.csv")
    runtime_family_rows = _rows("ratewall_annual_flow_runtime_family_registry.csv")
    compatibility_rows = _rows(
        "ratewall_annual_support_denominator_compatibility_registry.csv"
    )

    target_key = (
        "2026",
        "base_mpc_10pct",
        "higher_wam_slower_repricing",
        "shift_to_domestic_nonbanks",
    )
    failing_source_gate_rows: list[dict[str, str]] = []
    for row in source_gate_rows:
        mutated = dict(row)
        if (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
            row["component_id"],
        ) == (*target_key, "tdc_deposit_current_demand_support"):
            mutated["source_gate_status"] = (
                "blocked_missing_combined_tdcsim_contract_scenario"
            )
            mutated["exact_blocker"] = (
                "Synthetic missing combined maturity/holder scenario for regression coverage."
            )
        failing_source_gate_rows.append(mutated)

    uncertainty_envelope_rows = _annual_support_numerator_uncertainty_envelope_rows(
        annual_support_numerator_contract_rows=contract_rows,
        annual_support_numerator_source_gate_rows=failing_source_gate_rows,
    )
    scenario_rows = _runtime_annual_flow_support_offset_scenario_rows(
        annual_support_numerator_contract_rows=contract_rows,
        annual_support_numerator_source_gate_rows=failing_source_gate_rows,
        annual_support_numerator_uncertainty_envelope_rows=uncertainty_envelope_rows,
        annual_flow_anchor_registry_rows=anchor_rows,
        annual_flow_runtime_family_registry_rows=runtime_family_rows,
        annual_support_denominator_compatibility_registry_rows=compatibility_rows,
    )
    default_row = next(
        row
        for row in scenario_rows
        if (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
            row["denominator_source_id"],
        )
        == (*target_key, "literature_annual_flow_bridge_candidate")
    )
    assert default_row["numerator_runtime_allowed"] == "true"
    assert default_row["numerator_source_gate_status"] == (
        "blocked_missing_combined_tdcsim_contract_scenario"
    )
    assert default_row["denominator_runtime_allowed"] == "true"
    assert default_row["effective_runtime_output_allowed"] == "false"
    assert default_row["scenario_runtime_allowed"] == "false"
    assert default_row["runtime_pairing_status"] == (
        "blocked_numerator_source_gate_not_runtime_usable"
    )
    assert default_row["support_offset_100bp_year_equivalent"] == ""
    assert default_row["support_offset_bp_year_equivalent"] == ""

    readiness_rows = _runtime_annual_flow_support_offset_readiness_registry_rows(
        runtime_annual_flow_support_offset_scenario_rows=scenario_rows
    )
    readiness = next(
        row
        for row in readiness_rows
        if row["runtime_support_offset_row_id"]
        == default_row["runtime_support_offset_row_id"]
    )
    assert readiness["effective_runtime_output_allowed"] == "false"
    assert readiness["readiness_tier"] == (
        "blocked_runtime_support_offset_numerator_source_gate"
    )
