from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.historical_comparable_adapter import (
    HISTORICAL_CHANNEL_ADAPTER_STATUS_FIELDS,
    HISTORICAL_COMPARABLE_SURFACE_FIELDS,
    HISTORICAL_DENOMINATOR_VARIANT_BRIDGE_FIELDS,
    historical_channel_adapter_status_rows,
    historical_comparable_surface_rows,
    historical_denominator_variant_bridge_rows,
    write_historical_comparable_adapter_outputs,
)


def test_historical_adapter_uses_only_source_backed_component_columns(
    tmp_path: Path,
) -> None:
    methodology_dir, historical_path = _write_fixture(tmp_path)

    status_rows = historical_channel_adapter_status_rows(
        methodology_parity_dir=methodology_dir,
        historical_clean_path=historical_path,
    )
    surface_rows = historical_comparable_surface_rows(
        methodology_parity_dir=methodology_dir,
        historical_clean_path=historical_path,
    )

    assert {field for row in status_rows for field in row} == set(
        HISTORICAL_CHANNEL_ADAPTER_STATUS_FIELDS
    )
    assert {field for row in surface_rows for field in row} == set(
        HISTORICAL_COMPARABLE_SURFACE_FIELDS
    )
    status = {row["channel_id"]: row for row in status_rows}
    assert status["tdc_ex_overlap_current_demand_support"][
        "historical_source_column"
    ] == "tdc_current_demand_support_bil"
    assert status["tdc_ex_overlap_current_demand_support"][
        "historical_adapter_status"
    ] == "source_backed_component_context_not_classifier"
    assert status["direct_treasury_interest_support"][
        "historical_adapter_status"
    ] == "source_backed_legacy_component_not_final_parity"
    assert status["bank_treasury_interest_support"]["source_status"] == (
        "not_source_backed_in_current_adapter"
    )
    assert status["net_interest_after_fiscal_tga_offsets"][
        "historical_adapter_status"
    ] == "context_only_no_explicit_component_column"

    assert len(surface_rows) == 4
    assert {row["channel_id"] for row in surface_rows} == {
        "tdc_ex_overlap_current_demand_support",
        "direct_treasury_interest_support",
    }
    assert all(row["historical_ratio_not_classifier"] == "true" for row in surface_rows)
    assert all(row["historical_path_D_bil"] == "" for row in surface_rows)
    assert all(row["fixed_D_comparison_bil"] == "" for row in surface_rows)
    assert all(row["historical_rate_gap_pct_points"] == "" for row in surface_rows)
    assert all("forecast_assumption_backfill" in row["blocked_use"] for row in surface_rows)


def test_historical_denominator_bridge_keeps_variants_separate(tmp_path: Path) -> None:
    methodology_dir, _historical_path = _write_fixture(tmp_path)

    rows = historical_denominator_variant_bridge_rows(
        methodology_parity_dir=methodology_dir,
    )

    assert {field for row in rows for field in row} == set(
        HISTORICAL_DENOMINATOR_VARIANT_BRIDGE_FIELDS
    )
    by_variant = {row["denominator_variant"]: row for row in rows}
    assert set(by_variant) == {
        "fixed_D_comparison",
        "historical_path_D",
        "moving_D_not_applicable",
    }
    assert by_variant["historical_path_D"]["selected_variant"] == "true"
    assert by_variant["fixed_D_comparison"]["selected_variant"] == "false"
    assert by_variant["moving_D_not_applicable"]["variant_role"] == (
        "not_applicable_to_historical_context"
    )
    assert all(row["historical_ratio_not_classifier"] == "true" for row in rows)


def test_historical_adapter_outputs_are_written(tmp_path: Path) -> None:
    methodology_dir, historical_path = _write_fixture(tmp_path)
    outputs = write_historical_comparable_adapter_outputs(
        tmp_path / "out",
        status_rows=historical_channel_adapter_status_rows(
            methodology_parity_dir=methodology_dir,
            historical_clean_path=historical_path,
        ),
        surface_rows=historical_comparable_surface_rows(
            methodology_parity_dir=methodology_dir,
            historical_clean_path=historical_path,
        ),
        denominator_rows=historical_denominator_variant_bridge_rows(
            methodology_parity_dir=methodology_dir,
        ),
    )

    assert outputs["status_csv"].read_text(encoding="utf-8").startswith(
        "historical_channel_adapter_status_row_id,"
    )
    assert outputs["surface_csv"].read_text(encoding="utf-8").startswith(
        "historical_comparable_surface_row_id,"
    )
    assert outputs["denominator_csv"].read_text(encoding="utf-8").startswith(
        "historical_denominator_variant_bridge_row_id,"
    )


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    methodology_dir = tmp_path / "methodology"
    methodology_dir.mkdir()
    _write_csv(
        methodology_dir / "ratewall_methodology_parity_channels.csv",
        [
            _channel(
                "tdc_ex_overlap_current_demand_support",
                "TDC ex-overlap support",
                centrality="context",
            ),
            _channel(
                "direct_treasury_interest_support",
                "Direct Treasury interest support",
                centrality="not_ready",
            ),
            _channel(
                "bank_treasury_interest_support",
                "Bank Treasury interest support",
                centrality="not_ready",
            ),
            _channel(
                "net_interest_after_fiscal_tga_offsets",
                "net interest after fiscal tga offsets",
                centrality="context",
            ),
        ],
    )
    _write_csv(
        methodology_dir / "ratewall_methodology_parity_denominators.csv",
        [
            {
                "surface_id": "historical_path_context",
                "surface_label": "Historical path/context surface",
                "denominator_object_id": "historical_path_denominator_v1_required",
                "denominator_role": "primary_historical_path_denominator",
                "fixed_anchor_component": "0.77600",
            }
        ],
    )
    historical_path = tmp_path / "historical.csv"
    _write_csv(
        historical_path,
        [
            _historical("2024Q1", "base", "11", "2", "0.10"),
            _historical("2024Q2", "high", "13", "3", "0.12"),
        ],
    )
    return methodology_dir, historical_path


def _channel(channel_id: str, label: str, *, centrality: str) -> dict[str, str]:
    return {
        "methodology_parity_channel_row_id": f"method::{channel_id}",
        "surface_id": "historical_path_context",
        "channel_id": channel_id,
        "channel_label": label,
        "centrality": centrality,
    }


def _historical(
    period: str,
    assumption_case: str,
    tdc_value: str,
    direct_value: str,
    ratio: str,
) -> dict[str, str]:
    return {
        "historical_closest_approach_clean_row_id": (
            f"historical::{period}::{assumption_case}"
        ),
        "period": period,
        "quarter": period,
        "assumption_case": assumption_case,
        "ratio_object_id": "rw_historical_wall_ratio_path",
        "tdc_current_demand_support_bil": tdc_value,
        "direct_interest_support_bil": direct_value,
        "ratewall_ratio": ratio,
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
