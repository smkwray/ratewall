from __future__ import annotations

import pytest
import csv
from pathlib import Path




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
ARTIFACT = "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv"


def _rows() -> list[dict[str, str]]:
    with (OUTPUT_TABLES / ARTIFACT).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_benchmark_overlay_materializes_one_runtime_context_row_per_forecast_year() -> None:
    rows = _rows()
    assert len(rows) == 11
    assert {row["overlay_status"] for row in rows} == {
        "pass_runtime_default_plus_review_only_benchmark_context_materialized"
    }


def test_benchmark_overlay_keeps_runtime_default_and_overlay_boundaries_explicit() -> None:
    row = next(item for item in _rows() if item["forecast_year"] == "2026")
    assert row["default_runtime_family_source_id"] == (
        "literature_annual_flow_bridge_candidate"
    )
    assert row["default_runtime_reference_support_offset_100bp_year_equivalent"] != ""
    assert row["default_runtime_reference_denominator_center_pp_gdp"] == "0.776"
    assert row["legacy_base_reference_support_offset_100bp_year_equivalent"] != ""
    assert row["legacy_high_reference_support_offset_100bp_year_equivalent"] != ""
    assert row["bounded_h8_direct_runtime_ratio_status"] == (
        "blocked_not_timing_commensurate_for_support_offset"
    )
    assert row["bounded_h8_review_center_pp_gdp_per_100bp_year"] == "12.849970703281"
    assert (
        row["bounded_h8_weak_iv_safe_ci_low_pp_gdp_per_100bp_year"]
        == "5.114248607059"
    )
    assert (
        row["bounded_h8_weak_iv_safe_ci_high_pp_gdp_per_100bp_year"]
        == "20.864248607059"
    )
    assert row["frbus_h4_benchmark_pp_gdp_per_100bp_year"] == "0.93761147007"
    assert row["frbus_h8_benchmark_pp_gdp_per_100bp_year"] == "1.37015915961"
    assert row["frbus_h12_benchmark_pp_gdp_per_100bp_year"] == "1.160770865"
    assert row["low_scale_cluster_status"] == (
        "pass_runtime_family_in_same_low_scale_neighborhood_as_frbus_h4"
    )
    assert row["scale_conflict_status"] == (
        "warn_bounded_h8_above_literature_runtime_and_frbus_review_cluster"
    )
