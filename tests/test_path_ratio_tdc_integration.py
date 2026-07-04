from __future__ import annotations

import pytest
import csv
from decimal import Decimal
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUTS = Path("outputs/tables")


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _scenario_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row["forecast_year"],
        row["mpc_scenario"],
        row["maturity_scenario"],
        row["holder_scenario"],
    )


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def test_path_ratio_tdc_adjustment_layer_distinguishes_forecast_default_from_historical_sidecars() -> None:
    rows = _rows("ratewall_path_ratio_tdc_adjustment_layer.csv")
    _assert_fail_closed(rows)

    forecast_rows = [
        row for row in rows if row["source_variant_id"] == "forecast_holder_tdc_primary"
    ]
    historical_rows = [
        row
        for row in rows
        if row["source_variant_id"] == "historical_tdc_reduced_form_selected"
    ]
    assert forecast_rows
    assert historical_rows

    assert {row["tdc_adjustment_admission_status"] for row in forecast_rows} == {
        "pass_overlap_proved_forecast_tdc_adjustment_materialized"
    }
    assert {row["comparison_lane_only"] for row in forecast_rows} == {"false"}
    assert {row["overlap_subtracted_before_demand_conversion"] for row in forecast_rows} == {
        "true"
    }

    assert {row["tdc_adjustment_admission_status"] for row in historical_rows} == {
        "pass_historical_reduced_form_tdc_overlap_bridge_materialized_comparison_only"
    }
    assert {row["comparison_lane_only"] for row in historical_rows} == {"true"}
    assert {
        row["overlap_subtracted_before_demand_conversion"] for row in historical_rows
    } == {"true_direct_interest_overlap_bridge_materialized"}
    assert {row["tdc_pass_through_parameter_role"] for row in historical_rows} == {
        "reduced_form_deposit_pass_through_share"
    }
    assert all("runtime_default" in row["blocked_use"] for row in historical_rows)
    assert all("canonical_rw_y" in row["blocked_use"] for row in historical_rows)


def test_tdc_comparison_outputs_keep_historical_sidecars_non_headline_and_match_forecast_decomposition() -> None:
    historical_rows = _rows("ratewall_historical_incremental_path_ratio_tdc_comparison.csv")
    forecast_rows = _rows("ratewall_forecast_incremental_path_ratio_tdc_comparison.csv")
    default_forecast_rows = _rows("ratewall_forecast_incremental_path_ratio.csv")
    adoption_rows = _rows("ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv")
    frontier_rows = _rows("ratewall_runtime_annual_flow_support_offset_frontier_summary.csv")
    readiness_rows = _rows("ratewall_runtime_annual_flow_support_offset_readiness_registry.csv")

    _assert_fail_closed(historical_rows)
    _assert_fail_closed(forecast_rows)

    assert len(historical_rows) == len(_rows("ratewall_historical_incremental_path_ratio.csv"))
    assert len(forecast_rows) == len(_rows("ratewall_forecast_incremental_path_ratio.csv"))

    historical_matched = [row for row in historical_rows if row["linked_tdc_adjustment_row_id"]]
    historical_missing = [row for row in historical_rows if not row["linked_tdc_adjustment_row_id"]]
    assert historical_matched
    assert historical_missing
    assert {row["comparison_row_status"] for row in historical_matched} == {
        "comparison_only_historical_reduced_form_tdc_overlap_bridge_materialized"
    }
    assert {row["comparison_row_status"] for row in historical_missing} == {
        "blocked_missing_historical_tdc_sidecar_for_quarter"
    }
    assert all(
        row["candidate_tdc_adjusted_ratio"] or row["historical_incremental_path_ratio"] == ""
        for row in historical_matched
    )
    assert all(row["candidate_tdc_adjusted_ratio"] == "" for row in historical_missing)
    assert all(
        "historical_headline_default_replacement" in row["blocked_use"]
        for row in historical_rows
    )
    assert all("runtime_default" in row["blocked_use"] for row in historical_rows)
    assert all("canonical_rw_y" in row["blocked_use"] for row in historical_rows)

    assert {row["comparison_row_status"] for row in forecast_rows} == {
        "pass_forecast_tdc_comparison_materialized"
    }
    legacy_gaps = []
    for row in forecast_rows:
        default_ratio = Decimal(row["forecast_incremental_path_ratio"])
        without_tdc = Decimal(row["forecast_incremental_path_ratio_without_tdc"])
        tdc_delta = Decimal(row["tdc_adjustment_ratio_delta"])
        legacy_no_tdc = Decimal(row["quarterly_interest_only_ratio_reference"])
        assert abs(default_ratio - (without_tdc + tdc_delta)) <= Decimal("1e-12")
        legacy_gaps.append(abs(without_tdc - legacy_no_tdc))
    assert any(gap > Decimal("1e-6") for gap in legacy_gaps)

    forecast_scenario_keys = {_scenario_key(row) for row in default_forecast_rows}
    assert {_scenario_key(row) for row in adoption_rows} == forecast_scenario_keys
    assert {
        row["default_denominator_source_id"] for row in adoption_rows
    } == {"literature_annual_flow_bridge_candidate"}

    reportable_denominator_sources = {
        row["denominator_source_id"]
        for row in readiness_rows
        if row["readiness_tier"] == "reportable_runtime_support_offset"
    }
    forecast_years = {row["forecast_year"] for row in default_forecast_rows}
    assert {
        (row["forecast_year"], row["denominator_source_id"]) for row in frontier_rows
    } == {
        (year, denominator_source_id)
        for year in forecast_years
        for denominator_source_id in reportable_denominator_sources
    }
    for row in frontier_rows:
        assert int(row["scenario_row_count"]) == sum(
            1
            for readiness_row in readiness_rows
            if readiness_row["forecast_year"] == row["forecast_year"]
            and readiness_row["denominator_source_id"] == row["denominator_source_id"]
            and readiness_row["readiness_tier"] == "reportable_runtime_support_offset"
        )
