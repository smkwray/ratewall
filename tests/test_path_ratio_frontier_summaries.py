from __future__ import annotations

import pytest
import csv
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUTS = Path("outputs/tables")


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def test_historical_tdc_admission_registry_keeps_reduced_form_tdc_nonheadline() -> None:
    admission_rows = _rows("ratewall_historical_tdc_path_admission.csv")
    frontier_rows = _rows("ratewall_historical_incremental_path_ratio_frontier_summary.csv")
    default_rows = _rows("ratewall_historical_incremental_path_ratio.csv")

    _assert_fail_closed(admission_rows)
    _assert_fail_closed(frontier_rows)

    assert len(admission_rows) == 19
    assert len(frontier_rows) == 19
    assert {
        row["historical_tdc_default_headline_admission_status"] for row in admission_rows
    } == {"blocked_source_coverage_limited_overlap_unproved_selected_series_empty"}
    assert {
        row["selected_series_quarter_count"] for row in admission_rows
    } == {"0"}
    assert all(
        row["historical_tdc_comparison_status"]
        in {
            "comparison_only_historical_reduced_form_tdc_missing_overlap_proof",
            "comparison_only_historical_reduced_form_tdc_overlap_bridge_materialized",
            "blocked_missing_historical_tdc_sidecar_for_quarter",
        }
        for row in admission_rows
    )

    default_quarters = {row["quarter"] for row in default_rows}
    assert {row["quarter"] for row in admission_rows} == default_quarters
    assert {row["linked_historical_tdc_admission_status"] for row in frontier_rows} == {
        "blocked_source_coverage_limited_overlap_unproved_selected_series_empty"
    }
    assert {
        row["frontier_status"] for row in frontier_rows
    } == {
        "reportable_historical_default_frontier",
        "transition_context_only_historical_frontier",
        "blocked_zero_exposure_historical_frontier",
    }


def test_forecast_frontier_summary_is_deterministic_and_stays_on_default_rows() -> None:
    forecast_rows = _rows("ratewall_forecast_incremental_path_ratio.csv")
    comparison_rows = _rows("ratewall_forecast_incremental_path_ratio_tdc_comparison.csv")
    frontier_rows = _rows("ratewall_forecast_incremental_path_ratio_frontier_summary.csv")

    _assert_fail_closed(frontier_rows)

    forecast_by_id = {
        row["forecast_incremental_path_ratio_row_id"]: row for row in forecast_rows
    }
    comparison_by_id = {
        row["forecast_incremental_path_ratio_row_id"]: row for row in comparison_rows
    }

    assert len(frontier_rows) == 11
    assert {row["frontier_status"] for row in frontier_rows} == {
        "reportable_forecast_default_frontier"
    }

    for row in frontier_rows:
        assert row["scenario_row_count"] == "27"
        assert row["reference_mpc_scenario"] == "base_mpc_10pct"
        assert row["reference_maturity_scenario"] == "current_wam_cbo_rate_path"
        assert row["reference_holder_scenario"] == "current_holder_distribution"

        reference = forecast_by_id[row["reference_row_id"]]
        minimum = forecast_by_id[row["minimum_row_id"]]
        maximum = forecast_by_id[row["maximum_row_id"]]
        assert reference["forecast_year"] == row["forecast_year"]
        assert minimum["forecast_year"] == row["forecast_year"]
        assert maximum["forecast_year"] == row["forecast_year"]
        assert row["linked_reference_tdc_comparison_row_id"] == comparison_by_id[
            row["reference_row_id"]
        ]["forecast_incremental_path_ratio_tdc_comparison_row_id"]
        assert row["linked_maximum_tdc_comparison_row_id"] == comparison_by_id[
            row["maximum_row_id"]
        ]["forecast_incremental_path_ratio_tdc_comparison_row_id"]
