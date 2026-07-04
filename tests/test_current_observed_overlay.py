from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from ratewall.databook.current_observed_overlay import (
    CURRENT_BENCHMARK_FIELDS,
    CURRENT_OBSERVED_OVERLAY_AUDIT_FIELDS,
    CURRENT_OVERLAY_ADMISSION_FIELDS,
    CURRENT_OVERLAY_CANDIDATE_FIELDS,
    CURRENT_OVERLAY_MAP_FIELDS,
    current_assumption_benchmark_rows,
    current_observed_overlay_admission_rows,
    current_observed_overlay_audit_rows,
    current_observed_overlay_candidate_rows,
    current_observed_overlay_map_rows,
    write_current_observed_overlay_outputs,
)


def test_current_benchmark_reproduces_runtime_values(tmp_path: Path) -> None:
    runtime_dir = _write_runtime_fixture(tmp_path)

    rows = current_assumption_benchmark_rows(runtime_table_dir=runtime_dir)

    assert {field for row in rows for field in row} == set(CURRENT_BENCHMARK_FIELDS)
    assert len(rows) == 2
    selected = [row for row in rows if row["selected_current_row"] == "true"]
    assert len(selected) == 1
    assert selected[0]["forecast_year"] == "2026"
    assert selected[0]["benchmark_numerator_bil"] == "7.76"
    assert Decimal(selected[0]["fixed_D_bil"]) == Decimal("77.6")
    assert selected[0]["benchmark_ratewall_ratio"] == "0.1"
    assert selected[0]["exact_reproduction_of_runtime_ratio"] == "true"
    assert Decimal(selected[0]["ratio_recomputed_from_n_d"]) == Decimal("0.1")


def test_current_overlay_candidates_cannot_replace_benchmark(
    tmp_path: Path,
) -> None:
    runtime_dir = _write_runtime_fixture(tmp_path)
    source_dir = _write_source_method_fixture(tmp_path)
    bridge_path, tdc_path = _write_current_overlay_source_fixtures(tmp_path)
    benchmark = current_assumption_benchmark_rows(runtime_table_dir=runtime_dir)
    overlay = current_observed_overlay_map_rows(source_method_dir=source_dir)
    admission = current_observed_overlay_admission_rows(
        benchmark_rows=benchmark,
        holder_tdc_bridge_path=bridge_path,
        tdc_channel_path=tdc_path,
    )
    candidates = current_observed_overlay_candidate_rows(
        benchmark_rows=benchmark,
        overlay_rows=overlay,
        admission_rows=admission,
    )
    audit = current_observed_overlay_audit_rows(
        benchmark_rows=benchmark,
        overlay_rows=overlay,
        candidate_rows=candidates,
        admission_rows=admission,
    )

    assert {field for row in overlay for field in row} == set(
        CURRENT_OVERLAY_MAP_FIELDS
    )
    assert {field for row in candidates for field in row} == set(
        CURRENT_OVERLAY_CANDIDATE_FIELDS
    )
    assert {field for row in admission for field in row} == set(
        CURRENT_OVERLAY_ADMISSION_FIELDS
    )
    assert {field for row in audit for field in row} == set(
        CURRENT_OBSERVED_OVERLAY_AUDIT_FIELDS
    )
    assert {row["check_status"] for row in audit} == {"pass"}
    assert all(row["benchmark_replacement_allowed"] == "false" for row in overlay)
    assert all(row["central_current_value_changed"] == "false" for row in overlay)
    assert all(row["selected_current_row"] == "false" for row in candidates)
    by_candidate = {row["candidate_block_id"]: row for row in candidates}
    assert by_candidate["current_public_interest_runtime"][
        "benchmark_ratewall_ratio"
    ] == "0.1"
    assert by_candidate["current_public_interest_runtime"][
        "candidate_n_delta_bil"
    ] == "5"
    assert by_candidate["current_tdc_decomposition"]["candidate_n_delta_bil"] == "2.0"
    assert by_candidate["current_tdc_decomposition"]["candidate_status"] == (
        "pass_selected_beta_chi_ex_overlap_formula"
    )
    assert admission[0]["legacy_runtime_component_identity_error_bil"] == "0.00"
    assert admission[0]["selected_overlay_candidate_n_bil"] == "7.0"
    assert admission[0]["candidate_minus_benchmark_n_bil"] == "-0.76"
    assert admission[0]["replacement_gate_status"] == (
        "blocked_candidate_changes_current_N_requires_R40_current_object_decision"
    )


def test_current_overlay_outputs_are_written(tmp_path: Path) -> None:
    runtime_dir = _write_runtime_fixture(tmp_path)
    source_dir = _write_source_method_fixture(tmp_path)
    bridge_path, tdc_path = _write_current_overlay_source_fixtures(tmp_path)
    benchmark = current_assumption_benchmark_rows(runtime_table_dir=runtime_dir)
    overlay = current_observed_overlay_map_rows(source_method_dir=source_dir)
    admission = current_observed_overlay_admission_rows(
        benchmark_rows=benchmark,
        holder_tdc_bridge_path=bridge_path,
        tdc_channel_path=tdc_path,
    )
    candidates = current_observed_overlay_candidate_rows(
        benchmark_rows=benchmark,
        overlay_rows=overlay,
        admission_rows=admission,
    )
    audit = current_observed_overlay_audit_rows(
        benchmark_rows=benchmark,
        overlay_rows=overlay,
        candidate_rows=candidates,
        admission_rows=admission,
    )

    outputs = write_current_observed_overlay_outputs(
        tmp_path / "out",
        benchmark_rows=benchmark,
        overlay_rows=overlay,
        candidate_rows=candidates,
        admission_rows=admission,
        audit_rows=audit,
    )

    assert outputs["benchmark_csv"].read_text(encoding="utf-8").startswith(
        "current_benchmark_row_id,"
    )
    assert outputs["overlay_map_csv"].read_text(encoding="utf-8").startswith(
        "current_overlay_map_row_id,"
    )
    assert outputs["audit_csv"].read_text(encoding="utf-8").startswith(
        "current_observed_overlay_audit_row_id,"
    )
    assert outputs["admission_csv"].read_text(encoding="utf-8").startswith(
        "current_overlay_admission_row_id,"
    )


def _write_runtime_fixture(tmp_path: Path) -> Path:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    _write_csv(
        runtime_dir / "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv",
        [
            _overlay_row("2026", "scenario::2026", "0.1"),
            _overlay_row("2027", "scenario::2027", "0.2"),
        ],
    )
    _write_csv(
        runtime_dir / "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv",
        [
            _frontier_row("2026", "scenario::2026"),
            _frontier_row("2027", "scenario::2027"),
        ],
    )
    _write_csv(
        runtime_dir / "ratewall_runtime_annual_flow_support_offset_scenarios.csv",
        [
            _scenario_row("2026", "scenario::2026", "7.76", "0.776"),
            _scenario_row("2027", "scenario::2027", "15.52", "1.552"),
        ],
    )
    return runtime_dir


def _write_source_method_fixture(tmp_path: Path) -> Path:
    source_dir = tmp_path / "source_method"
    source_dir.mkdir()
    rows = []
    for block_id, central_allowed in [
        ("current_public_interest_runtime", "true"),
        ("current_tdc_decomposition", "false"),
        ("current_denominator", "false"),
        ("realized_safe_yield_income", "false"),
        ("zero_low_apr_credit", "false"),
    ]:
        rows.append(
            {
                "block_id": block_id,
                "surface_id": "current_assumption_runtime",
                "source_object": f"source::{block_id}",
                "source_artifact_or_candidate": f"artifact::{block_id}",
                "local_source_status": "present_local",
                "central_n_delta_bil_allowed": central_allowed,
                "overlap_guard_id": f"guard::{block_id}",
            }
        )
    _write_csv(source_dir / "ratewall_source_method_matrix.csv", rows)
    return source_dir


def _write_current_overlay_source_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    bridge_path = tmp_path / "holder_tdc_bridge.csv"
    tdc_path = tmp_path / "tdc_channel.csv"
    _write_csv(
        bridge_path,
        [
            {
                "forecast_year": "2026",
                "mpc_scenario": "base_mpc_10pct",
                "maturity_scenario": "current_wam_cbo_rate_path",
                "holder_scenario": "current_holder_distribution",
                "interest_income_current_demand_support_bil": "5",
                "tdc_deposit_current_demand_support_bil": "2.76",
            }
        ],
    )
    _write_csv(
        tdc_path,
        [
            {
                "tdc_assumption_mode_channel_row_id": "tdc::2026::base",
                "forecast_year": "2026",
                "channel_conversion_profile_id": "base",
                "maturity_scenario": "current_wam_cbo_rate_path",
                "holder_scenario": "current_holder_distribution",
                "tdc_change_bil": "120",
                "direct_interest_overlap_cashflow_bil": "20",
                "tdc_change_ex_overlap_bil": "100",
                "tdc_materialization_beta": "0.4",
                "deposit_current_demand_share": "0.05",
                "tdc_current_demand_support_bil": "2.0",
            }
        ],
    )
    return bridge_path, tdc_path


def _overlay_row(year: str, scenario_id: str, ratio: str) -> dict[str, str]:
    return {
        "forecast_year": year,
        "default_runtime_frontier_row_id": f"frontier::{year}",
        "default_runtime_reference_denominator_center_pp_gdp": "0.776",
        "default_runtime_reference_support_offset_100bp_year_equivalent": ratio,
        "overlay_status": "pass_runtime_overlay_materialized",
    }


def _frontier_row(year: str, scenario_id: str) -> dict[str, str]:
    return {
        "frontier_row_id": f"frontier::{year}",
        "reference_runtime_support_offset_row_id": scenario_id,
    }


def _scenario_row(
    year: str, row_id: str, numerator_bil: str, support_pct_gdp: str
) -> dict[str, str]:
    return {
        "runtime_support_offset_row_id": row_id,
        "forecast_year": year,
        "nominal_gdp_bil": "10000",
        "numerator_total_bil": numerator_bil,
        "support_pct_of_gdp": support_pct_gdp,
        "numerator_source_gate_status": "pass_fixture_source_gate",
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
