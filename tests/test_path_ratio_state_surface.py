from __future__ import annotations

import pytest
import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUTS = Path("outputs/tables")


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _rows_by(
    rows: list[dict[str, str]], field: str
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row[field]].append(row)
    return grouped


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def test_distance_to_wall_state_surface_materializes_historical_and_forecast_sidecar_rows() -> None:
    rows = _rows("ratewall_distance_to_wall_state_surface.csv")
    historical_frontier_rows = _rows(
        "ratewall_historical_incremental_path_ratio_frontier_summary.csv"
    )
    forecast_ratio_rows = _rows("ratewall_forecast_incremental_path_ratio.csv")
    _assert_fail_closed(rows)

    historical_rows = [
        row for row in rows if row["source_object_id"] == "rw_historical_wall_ratio_path"
    ]
    forecast_rows = [
        row for row in rows if row["source_object_id"] == "rw_forecast_wall_ratio_path"
    ]
    forecast_years = {row["forecast_year"] for row in forecast_ratio_rows}
    forecast_roles = {
        "forecast_reference_default",
        "forecast_minimum_default",
        "forecast_maximum_default",
    }

    assert len(historical_rows) == len(historical_frontier_rows)
    assert len(forecast_rows) == len(forecast_years) * len(forecast_roles)
    assert len(rows) == len(historical_rows) + len(forecast_rows)
    assert {row["source_frontier_row_id"] for row in historical_rows} == {
        row["historical_path_ratio_frontier_row_id"]
        for row in historical_frontier_rows
    }
    forecast_rows_by_year = _rows_by(forecast_rows, "forecast_year")
    assert set(forecast_rows_by_year) == forecast_years
    for year_rows in forecast_rows_by_year.values():
        assert {row["source_state_role"] for row in year_rows} == forecast_roles

    assert {
        row["source_state_role"] for row in historical_rows
    } == {"historical_frontier_default"}
    assert {
        row["source_state_role"] for row in forecast_rows
    } == {
        "forecast_reference_default",
        "forecast_minimum_default",
        "forecast_maximum_default",
    }
    assert any(
        row["state_distance_status"] == "transition_context_historical_state_distance_row"
        for row in historical_rows
    )
    assert any(
        row["state_distance_status"] == "reportable_forecast_maximum_state_distance_row"
        for row in forecast_rows
    )


def test_historical_forecast_comparison_matrix_anchors_forecast_years_to_historical_benchmarks() -> None:
    rows = _rows("ratewall_historical_forecast_wall_ratio_comparison_matrix.csv")
    forecast_ratio_rows = _rows("ratewall_forecast_incremental_path_ratio.csv")
    historical_frontier_rows = _rows(
        "ratewall_historical_incremental_path_ratio_frontier_summary.csv"
    )
    _assert_fail_closed(rows)

    years = {row["forecast_year"] for row in rows}
    assert years == {row["forecast_year"] for row in forecast_ratio_rows}
    historical_frontier_ids = {
        row["historical_path_ratio_frontier_row_id"]
        for row in historical_frontier_rows
    }
    assert {
        row["historical_reportable_frontier_row_id"] for row in rows
    } <= historical_frontier_ids
    assert {
        row["historical_peak_any_context_row_id"] for row in rows
    } <= historical_frontier_ids
    for row in rows:
        assert row["historical_reportable_quarter"] in {
            frontier_row["quarter"] for frontier_row in historical_frontier_rows
        }
        assert row["historical_peak_any_context_quarter"] in {
            frontier_row["quarter"] for frontier_row in historical_frontier_rows
        }
    assert {
        row["comparison_status"] for row in rows
    } == {"forecast_reference_exceeds_historical_peak_any_context"}


def test_closest_to_wall_frontier_ranks_state_surface_rows_deterministically() -> None:
    rows = _rows("ratewall_closest_to_wall_frontier.csv")
    _assert_fail_closed(rows)

    ranked_rows = [row for row in rows if row["frontier_rank"]]
    assert ranked_rows
    ordered = sorted(ranked_rows, key=lambda row: int(row["frontier_rank"]))
    assert ordered[0]["source_state_role"] == "forecast_maximum_default"
    assert ordered[0]["forecast_year"] == "2026"
    assert Decimal(ordered[0]["wall_ratio"]) > Decimal("1")

    ratios = [Decimal(row["wall_ratio"]) for row in ordered]
    assert ratios == sorted(ratios, reverse=True)
    assert any(row["quarter"] == "2022Q1" for row in ordered)


def test_historical_closest_approach_clean_flags_transition_and_tdc_limits() -> None:
    rows = _rows("ratewall_historical_closest_approach_clean.csv")
    historical_ratio_rows = _rows("ratewall_historical_incremental_path_ratio.csv")
    _assert_fail_closed(rows)

    assert len(rows) == len(historical_ratio_rows)
    assert {row["source_historical_incremental_path_ratio_row_id"] for row in rows} == {
        row["historical_incremental_path_ratio_row_id"]
        for row in historical_ratio_rows
    }
    assert {row["assumption_case"] for row in rows} == {
        row["calibration_band"] for row in historical_ratio_rows
    }
    clean_rows_by_quarter = _rows_by(rows, "quarter")
    historical_rows_by_quarter = _rows_by(historical_ratio_rows, "quarter")
    assert set(clean_rows_by_quarter) == set(historical_rows_by_quarter)
    for quarter, quarter_rows in clean_rows_by_quarter.items():
        assert {row["assumption_case"] for row in quarter_rows} == {
            row["calibration_band"] for row in historical_rows_by_quarter[quarter]
        }
    assert {row["headline_allowed"] for row in rows} == {"true", "false"}
    assert any(row["near_zero_drag_flag"] == "true" for row in rows)
    assert any(
        row["linked_historical_tdc_comparison_status"]
        == "blocked_missing_historical_tdc_sidecar_for_quarter"
        for row in rows
    )
    assert {row["covid_or_postcovid_flag"] for row in rows} >= {
        "post_covid_liftoff_transition_near_zero_drag",
        "post_covid_liftoff_full_hike_window",
    }

    ranked = [row for row in rows if row["closest_approach_rank"]]
    ordered = sorted(ranked, key=lambda row: int(row["closest_approach_rank"]))
    ratios = [Decimal(row["ratewall_ratio"]) for row in ordered]
    assert ratios == sorted(ratios, reverse=True)
    assert ordered[0]["near_zero_drag_flag"] == "true"

    clean_ranked = [row for row in rows if row["clean_reportable_rank"]]
    clean_ordered = sorted(
        clean_ranked, key=lambda row: int(row["clean_reportable_rank"])
    )
    assert clean_ordered[0]["headline_allowed"] == "true"
    assert clean_ordered[0]["near_zero_drag_flag"] == "false"
    assert "exact_wall_crossing_date" in clean_ordered[0]["blocked_use"]
