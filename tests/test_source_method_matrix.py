from __future__ import annotations

from pathlib import Path

from ratewall.databook.source_method_matrix import (
    SOURCE_METHOD_MATRIX_FIELDS,
    SOURCE_METHOD_SUMMARY_FIELDS,
    source_method_matrix_rows,
    source_method_summary_rows,
    write_source_method_matrix_outputs,
)


def test_source_method_matrix_has_required_blocks_and_guards(tmp_path: Path) -> None:
    missing_revenue = tmp_path / "missing.csv"

    rows = source_method_matrix_rows(cbo_revenue_path=missing_revenue)
    summary = source_method_summary_rows(rows)

    assert {field for row in rows for field in row} == set(
        SOURCE_METHOD_MATRIX_FIELDS
    )
    assert {field for row in summary for field in row} == set(
        SOURCE_METHOD_SUMMARY_FIELDS
    )
    by_block = {row["block_id"]: row for row in rows}
    required = {
        "forecast_tdc_support",
        "forecast_public_interest_net_block",
        "forecast_denominator",
        "forecast_remittance_baseline_path",
        "current_public_interest_runtime",
        "current_denominator",
        "historical_public_interest_net_block",
        "historical_denominator",
        "realized_safe_yield_income",
        "safe_asset_allocation_offset_drag",
        "firm_rollover_pressure_drag",
        "zero_low_apr_credit",
    }
    assert required <= set(by_block)
    assert by_block["forecast_tdc_support"]["central_n_delta_bil_allowed"] == "true"
    assert by_block["forecast_tdc_support"]["object_role"] == "selected_n"
    assert by_block["forecast_tdc_support"]["method_formula"] == (
        "tdc_current_demand_support_bil = tdc_change_ex_overlap_bil * beta * chi"
    )
    assert by_block["realized_safe_yield_income"][
        "central_n_delta_bil_allowed"
    ] == "false"
    assert by_block["realized_safe_yield_income"]["object_role"] == (
        "blocked_source_or_method"
    )
    assert by_block["realized_safe_yield_income"]["overlap_guard_id"] == (
        "bank_first_vs_recipient_flow_xor"
    )
    assert by_block["forecast_remittance_baseline_path"][
        "local_source_status"
    ] == "source_to_acquire"
    assert by_block["forecast_remittance_baseline_path"]["object_role"] == (
        "selected_block_input"
    )
    assert by_block["forecast_denominator"]["object_role"] == "denominator_only"
    assert by_block["historical_public_interest_net_block"][
        "local_source_status"
    ] == "present_local_context"
    assert by_block["historical_public_interest_net_block"]["evidence_status"] == (
        "source_backed_historical_public_interest_net_block_with_h41_remittance_guard"
    )
    assert by_block["historical_public_interest_net_block"][
        "admission_or_parking_rule"
    ] == "use_R37_historical_context_nonclassifier;do_not_promote"
    assert by_block["historical_public_interest_net_block"]["known_gap"] == (
        "none_R37_context_nonclassifier_decision"
    )
    assert all(
        row["central_n_delta_bil_allowed"] == "false"
        for row in rows
        if row["presentation_layer"] == "research_appendix"
    )


def test_source_method_matrix_marks_local_cbo_revenue_when_present(
    tmp_path: Path,
) -> None:
    revenue_path = tmp_path / "51138-2026-02-Revenue-annual_fy.csv"
    revenue_path.write_bytes(b"placeholder")

    rows = source_method_matrix_rows(cbo_revenue_path=revenue_path)

    by_block = {row["block_id"]: row for row in rows}
    assert by_block["forecast_remittance_baseline_path"][
        "local_source_status"
    ] == "present_local"
    assert by_block["forecast_remittance_baseline_path"]["method_formula"] == (
        "extract_rev_fed_reserve_by_fiscal_year_for_budget_context;central_n_delta_bil=0"
    )


def test_source_method_matrix_outputs_are_written(tmp_path: Path) -> None:
    rows = source_method_matrix_rows(cbo_revenue_path=tmp_path / "missing.csv")
    summary = source_method_summary_rows(rows)

    outputs = write_source_method_matrix_outputs(
        tmp_path / "out",
        rows=rows,
        summary_rows=summary,
    )

    assert outputs["matrix_csv"].read_text(encoding="utf-8").startswith(
        "source_method_matrix_row_id,"
    )
    assert outputs["summary_csv"].read_text(encoding="utf-8").startswith(
        "source_method_summary_row_id,"
    )
