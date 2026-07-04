"""Historical TDC source-route registry for RateWall T3."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_SIBLING_CALIBRATION_DIR = Path("data/raw/ratewall_sibling_calibration")
DEFAULT_HISTORICAL_PROVISIONAL_DIR = Path(
    "var/preliminary_scenario_results/historical_provisional_estimate"
)

HISTORICAL_TDC_SOURCE_REGISTRY_FIELDS = [
    "tdc_source_registry_row_id",
    "route_id",
    "route_role",
    "expected_window_start",
    "expected_window_end",
    "upstream_path",
    "upstream_selected_column",
    "upstream_file_status",
    "upstream_column_status",
    "upstream_selected_column_nonnull_start",
    "upstream_selected_column_nonnull_end",
    "downstream_path",
    "downstream_selected_column",
    "downstream_file_status",
    "downstream_column_status",
    "downstream_selected_column_nonnull_start",
    "downstream_selected_column_nonnull_end",
    "tdc_source_basis_chosen",
    "selected_column_coverage_status",
    "method_tier_status",
    "unit_basis",
    "route_status",
    "fail_closed_label",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class HistoricalTdcSourceRegistryError(ValueError):
    """Raised when historical TDC source-route rows are inconsistent."""


def historical_tdc_source_registry_rows(
    *,
    sibling_calibration_dir: str | Path = DEFAULT_SIBLING_CALIBRATION_DIR,
    historical_provisional_dir: str | Path = DEFAULT_HISTORICAL_PROVISIONAL_DIR,
) -> list[dict[str, str]]:
    """Return route-level source-shape checks for historical TDC."""

    sibling_dir = Path(sibling_calibration_dir)
    provisional_dir = Path(historical_provisional_dir)
    tdcest = sibling_dir / "tdcest_tdc_estimates.csv"
    tdcpass = sibling_dir / "tdcpass_quarterly_panel.csv"
    numerator = provisional_dir / "ratewall_historical_provisional_numerator_ledger.csv"
    rows = [
        _implemented_short_panel_row(numerator),
        _route_row(
            route_id="main_long_history_bank_scope",
            route_role="main_long_history_tdc_mechanism_context",
            expected_start="2002Q1",
            expected_end="2025Q4",
            upstream_path=tdcest,
            upstream_column="tdc_tier2_regression_mmf_rrp_prop_bank_only_ru_flow",
            downstream_path=tdcpass,
            downstream_column="tdc_tier2_regression_mmf_rrp_prop_bank_only_qoq",
            source_basis="external_regression_series_required_compare_to_vendored",
            unit_basis="ru_flow_upstream_qoq_downstream_billions_check_required",
            method_tier_status="fail_closed_method_tier_metadata_missing",
        ),
        _route_row(
            route_id="strict_modern_bank_scope",
            route_role="strict_modern_tdc_benchmark_context",
            expected_start="2022Q1",
            expected_end="2025Q4",
            upstream_path=tdcest,
            upstream_column="tdc_tier2_mmf_rrp_prop_bank_only_ru_flow",
            downstream_path=tdcpass,
            downstream_column="tdc_tier2_mmf_rrp_prop_bank_only_qoq",
            source_basis="vendored_tdcest_tdcpass_bank_only_mmf_rrp_prop",
            unit_basis="ru_flow_upstream_qoq_downstream_billions",
            method_tier_status="method_tier_context_available_not_runtime_selector",
        ),
        _route_row(
            route_id="level_splice_1990_appendix",
            route_role="appendix_level_splice_sensitivity",
            expected_start="1990Q1",
            expected_end="2001Q4",
            upstream_path=tdcest,
            upstream_column="tdc_bank_only_extended_1990",
            downstream_path=tdcpass,
            downstream_column="tdc_bank_only_extended_1990_qoq",
            source_basis="vendored_accounting_level_splice_appendix",
            unit_basis="appendix_sensitivity_units_not_main_history",
            method_tier_status="appendix_sensitivity_not_main_method_tier",
        ),
    ]
    validate_historical_tdc_source_registry(rows)
    return rows


def write_historical_tdc_source_registry_outputs(
    output_dir: str | Path,
    *,
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write historical TDC source registry outputs."""

    validate_historical_tdc_source_registry(rows)
    root = Path(output_dir)
    outputs = {
        "source_registry_csv": root / "ratewall_historical_tdc_source_registry.csv",
    }
    write_rows(
        outputs["source_registry_csv"],
        list(rows),
        HISTORICAL_TDC_SOURCE_REGISTRY_FIELDS,
    )
    return outputs


def validate_historical_tdc_source_registry(
    rows: Sequence[Mapping[str, str]],
) -> None:
    """Validate route-source rows."""

    if not rows:
        raise HistoricalTdcSourceRegistryError("historical TDC registry is empty")
    required = {
        "implemented_short_panel",
        "main_long_history_bank_scope",
        "strict_modern_bank_scope",
        "level_splice_1990_appendix",
    }
    by_id = {row["route_id"]: row for row in rows}
    missing = required - set(by_id)
    if missing:
        raise HistoricalTdcSourceRegistryError(f"missing routes: {sorted(missing)}")
    for row in rows:
        if row["route_status"].startswith("pass") and row["fail_closed_label"]:
            raise HistoricalTdcSourceRegistryError(
                f"passing route has fail label: {row['route_id']}"
            )
        if row["route_status"].startswith("fail_closed") and not row[
            "fail_closed_label"
        ]:
            raise HistoricalTdcSourceRegistryError(
                f"failing route lacks fail label: {row['route_id']}"
            )
        if row["expected_window_end"] > "2025Q4" and row[
            "route_id"
        ] != "implemented_short_panel":
            raise HistoricalTdcSourceRegistryError(
                f"TDC route extends after 2025Q4: {row['route_id']}"
            )


def _implemented_short_panel_row(path: Path) -> dict[str, str]:
    if not path.exists():
        return _registry_row(
            "implemented_short_panel",
            "implemented_context_panel",
            "2021Q4",
            "2026Q2",
            path,
            "tdc_ex_overlap_support_bil",
            "fail_closed_source_file_missing",
            "fail_closed_source_file_missing",
            "",
            "",
            path,
            "tdc_ex_overlap_support_bil",
            "fail_closed_source_file_missing",
            "fail_closed_source_file_missing",
            "",
            "",
            "implemented_historical_provisional_outputs",
            "fail_closed_source_file_missing",
            "implemented_output_context",
            "billions_once",
            "fail_closed_source_file_missing",
            "fail_closed_source_file_missing",
        )
    rows = _read(path)
    base_rows = [row for row in rows if row.get("assumption_case") == "base"]
    quarters = [row["quarter"] for row in base_rows if row.get("tdc_ex_overlap_support_bil")]
    start, end = _bounds(quarters)
    status = (
        "pass_implemented_context_panel_present"
        if start == "2021Q4" and end == "2026Q2"
        else "fail_closed_selected_tdc_column_coverage_gap"
    )
    fail = "" if status.startswith("pass") else status
    return _registry_row(
        "implemented_short_panel",
        "implemented_context_panel",
        "2021Q4",
        "2026Q2",
        path,
        "tdc_ex_overlap_support_bil",
        "present_local",
        "present",
        start,
        end,
        path,
        "tdc_ex_overlap_support_bil",
        "present_local",
        "present",
        start,
        end,
        "implemented_historical_provisional_outputs",
        status,
        "implemented_output_context",
        "billions_once",
        status,
        fail,
    )


def _route_row(
    *,
    route_id: str,
    route_role: str,
    expected_start: str,
    expected_end: str,
    upstream_path: Path,
    upstream_column: str,
    downstream_path: Path,
    downstream_column: str,
    source_basis: str,
    unit_basis: str,
    method_tier_status: str,
) -> dict[str, str]:
    up = _column_status(upstream_path, upstream_column, date_column="date")
    down = _column_status(downstream_path, downstream_column, date_column="quarter")
    coverage = _coverage_status(
        up["status"],
        down["status"],
        up["start"],
        up["end"],
        down["start"],
        down["end"],
        expected_start,
        expected_end,
    )
    fail = "" if coverage.startswith("pass") else coverage
    route_status = (
        "pass_source_shape_context_route"
        if coverage.startswith("pass") and not method_tier_status.startswith("fail")
        else fail or method_tier_status
    )
    if method_tier_status.startswith("fail") and route_status.startswith("pass"):
        route_status = method_tier_status
        fail = method_tier_status
    return _registry_row(
        route_id,
        route_role,
        expected_start,
        expected_end,
        upstream_path,
        upstream_column,
        up["file_status"],
        up["column_status"],
        up["start"],
        up["end"],
        downstream_path,
        downstream_column,
        down["file_status"],
        down["column_status"],
        down["start"],
        down["end"],
        source_basis,
        coverage,
        method_tier_status,
        unit_basis,
        route_status,
        fail,
    )


def _registry_row(
    route_id: str,
    route_role: str,
    expected_start: str,
    expected_end: str,
    upstream_path: Path,
    upstream_column: str,
    upstream_file_status: str,
    upstream_column_status: str,
    upstream_start: str,
    upstream_end: str,
    downstream_path: Path,
    downstream_column: str,
    downstream_file_status: str,
    downstream_column_status: str,
    downstream_start: str,
    downstream_end: str,
    source_basis: str,
    coverage_status: str,
    method_tier_status: str,
    unit_basis: str,
    route_status: str,
    fail_closed_label: str,
) -> dict[str, str]:
    return {
        "tdc_source_registry_row_id": f"historical_tdc_source::{route_id}",
        "route_id": route_id,
        "route_role": route_role,
        "expected_window_start": expected_start,
        "expected_window_end": expected_end,
        "upstream_path": str(upstream_path),
        "upstream_selected_column": upstream_column,
        "upstream_file_status": upstream_file_status,
        "upstream_column_status": upstream_column_status,
        "upstream_selected_column_nonnull_start": upstream_start,
        "upstream_selected_column_nonnull_end": upstream_end,
        "downstream_path": str(downstream_path),
        "downstream_selected_column": downstream_column,
        "downstream_file_status": downstream_file_status,
        "downstream_column_status": downstream_column_status,
        "downstream_selected_column_nonnull_start": downstream_start,
        "downstream_selected_column_nonnull_end": downstream_end,
        "tdc_source_basis_chosen": source_basis,
        "selected_column_coverage_status": coverage_status,
        "method_tier_status": method_tier_status,
        "unit_basis": unit_basis,
        "route_status": route_status,
        "fail_closed_label": fail_closed_label,
        "allowed_use": "historical_tdc_source_shape_and_route_context",
        "blocked_use": "selected_historical_n;final_classifier;post_2025q4_tdc_extension",
        "claim_boundary": "historical_tdc_source_registry_nonclassifier",
    }


def _column_status(path: Path, column: str, *, date_column: str) -> dict[str, str]:
    if not path.exists():
        return {
            "file_status": "fail_closed_source_file_missing",
            "column_status": "fail_closed_source_file_missing",
            "status": "fail_closed_source_file_missing",
            "start": "",
            "end": "",
        }
    rows = _read(path)
    if not rows or column not in rows[0]:
        return {
            "file_status": "present_local",
            "column_status": "fail_closed_selected_tdc_column_missing",
            "status": "fail_closed_selected_tdc_column_missing",
            "start": "",
            "end": "",
        }
    quarters = [
        _quarter(row[date_column])
        for row in rows
        if row.get(column) not in {"", None} and row.get(date_column)
    ]
    start, end = _bounds(quarters)
    status = "pass_selected_tdc_column_present" if start and end else (
        "fail_closed_tdc_selected_column_coverage_gap"
    )
    return {
        "file_status": "present_local",
        "column_status": "present",
        "status": status,
        "start": start,
        "end": end,
    }


def _coverage_status(
    up_status: str,
    down_status: str,
    up_start: str,
    up_end: str,
    down_start: str,
    down_end: str,
    expected_start: str,
    expected_end: str,
) -> str:
    for status in [up_status, down_status]:
        if status.startswith("fail"):
            return status
    if not (
        up_start <= expected_start <= expected_end <= up_end
        and down_start <= expected_start <= expected_end <= down_end
    ):
        return "fail_closed_tdc_selected_column_coverage_gap"
    return "pass_selected_column_nonnull_coverage"


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _quarter(value: str) -> str:
    if "Q" in value:
        return value
    parsed = date.fromisoformat(value[:10])
    return f"{parsed.year}Q{((parsed.month - 1) // 3) + 1}"


def _bounds(values: Sequence[str]) -> tuple[str, str]:
    if not values:
        return "", ""
    return min(values), max(values)
