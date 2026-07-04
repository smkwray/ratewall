from __future__ import annotations

import pytest
import csv
from decimal import Decimal
from pathlib import Path




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
SCENARIO_ARTIFACT = "ratewall_runtime_annual_flow_support_offset_scenarios.csv"
ADOPTION_ARTIFACT = "ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv"
FRONTIER_ARTIFACT = "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv"


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_compact_adoption_matrix_materializes_one_row_per_runtime_contract() -> None:
    scenario_rows = _rows(SCENARIO_ARTIFACT)
    adoption_rows = _rows(ADOPTION_ARTIFACT)

    contract_keys = {
        (
            row["forecast_year"],
            row["mpc_scenario"],
            row["maturity_scenario"],
            row["holder_scenario"],
        )
        for row in scenario_rows
    }
    assert len(adoption_rows) == len(contract_keys)
    assert {row["adoption_status"] for row in adoption_rows} == {
        "pass_compact_runtime_default_and_sensitivity_matrix_materialized"
    }


def test_compact_adoption_matrix_keeps_default_sensitivity_and_blocked_overlay_roles_explicit() -> None:
    rows = _rows(ADOPTION_ARTIFACT)
    target = next(
        row
        for row in rows
        if row["forecast_year"] == "2026"
        and row["mpc_scenario"] == "base_mpc_10pct"
        and row["maturity_scenario"] == "current_wam_cbo_rate_path"
        and row["holder_scenario"] == "current_holder_distribution"
    )

    assert target["default_runtime_family_count"] == "1"
    assert target["sensitivity_runtime_family_count"] == "2"
    assert target["blocked_overlay_family_count"] == "3"
    assert target["default_denominator_source_id"] == (
        "literature_annual_flow_bridge_candidate"
    )
    assert target["default_runtime_readiness_tier"] == (
        "reportable_runtime_support_offset"
    )
    assert target["default_support_offset_100bp_year_equivalent"] != ""
    assert target["sensitivity_base_current_support_offset_100bp_year_equivalent"] != ""
    assert target["sensitivity_high_support_offset_100bp_year_equivalent"] != ""

    for prefix in ("bounded_h8_overlay", "literature_h8_overlay", "frbus_h8_overlay"):
        assert target[f"{prefix}_runtime_pairing_status"] == (
            "blocked_not_timing_commensurate_for_support_offset"
        )
        assert target[f"{prefix}_readiness_tier"] == (
            "blocked_noncommensurate_overlay_context"
        )
        assert target[f"{prefix}_support_offset_100bp_year_equivalent"] == ""
        assert target[f"{prefix}_support_offset_bp_year_equivalent"] == ""


def test_frontier_summary_materializes_runtime_families_by_year() -> None:
    rows = _rows(FRONTIER_ARTIFACT)
    assert len(rows) == 33
    assert {row["frontier_status"] for row in rows} == {
        "pass_runtime_support_offset_frontier_materialized"
    }

    target = next(
        row
        for row in rows
        if row["forecast_year"] == "2026"
        and row["denominator_source_id"] == "literature_annual_flow_bridge_candidate"
    )
    assert target["runtime_family_class"] == "default_runtime_family"
    assert target["scenario_row_count"] == "27"
    assert target["reference_mpc_scenario"] == "base_mpc_10pct"
    assert target["reference_maturity_scenario"] == "current_wam_cbo_rate_path"
    assert target["reference_holder_scenario"] == "current_holder_distribution"
    minimum = Decimal(target["minimum_support_offset_100bp_year_equivalent"])
    reference = Decimal(target["reference_support_offset_100bp_year_equivalent"])
    maximum = Decimal(target["maximum_support_offset_100bp_year_equivalent"])
    assert minimum <= reference <= maximum
    assert target["reference_runtime_support_offset_row_id"].endswith(
        "::base_mpc_10pct::current_wam_cbo_rate_path::current_holder_distribution::literature_annual_flow_bridge_candidate"
    )
