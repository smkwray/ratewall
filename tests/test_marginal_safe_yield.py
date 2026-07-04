from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.marginal_safe_yield import (
    MARGINAL_SAFE_YIELD_DELTA_FIELDS,
    MARGINAL_SAFE_YIELD_OVERLAP_AUDIT_FIELDS,
    marginal_safe_yield_delta_rows,
    marginal_safe_yield_overlap_audit_rows,
    write_marginal_safe_yield_outputs,
)


def test_current_safe_yield_fails_closed_on_admission_gates(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path)

    rows = marginal_safe_yield_delta_rows(
        denominator_path=paths["d"],
        d1_admission_path=paths["admission"],
        forecast_assumptions_path=paths["assumptions"],
    )

    current = next(row for row in rows if row["period_object"] == "current")
    assert {field for row in rows for field in row} == set(MARGINAL_SAFE_YIELD_DELTA_FIELDS)
    assert current["selected_safe_yield_delta_allowed"] == "false"
    assert current["delta_safe_yield_bil"] == "0"
    assert "recipient_allocation_gate" in current["missing_gates"]
    assert current["current_candidate_gross_flow_bil"] == "100"


def test_forecast_safe_yield_formula_can_select_when_gates_pass(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path)

    rows = marginal_safe_yield_delta_rows(
        denominator_path=paths["d"],
        d1_admission_path=paths["admission"],
        forecast_assumptions_path=paths["assumptions"],
    )

    forecast = next(row for row in rows if row["period_object"] == "forecast")
    assert forecast["selected_safe_yield_delta_allowed"] == "true"
    assert forecast["delta_gross_deposit_payer_flow_bil"] == "10"
    assert forecast["delta_safe_yield_bil"] == "2.25"


def test_safe_yield_outputs_are_written(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path)
    rows = marginal_safe_yield_delta_rows(
        denominator_path=paths["d"],
        d1_admission_path=paths["admission"],
        forecast_assumptions_path=paths["assumptions"],
    )
    overlap = marginal_safe_yield_overlap_audit_rows(rows)
    outputs = write_marginal_safe_yield_outputs(
        tmp_path / "out",
        delta_rows=rows,
        overlap_rows=overlap,
    )

    assert {field for row in overlap for field in row} == set(
        MARGINAL_SAFE_YIELD_OVERLAP_AUDIT_FIELDS
    )
    assert outputs["safe_yield_delta_csv"].read_text(encoding="utf-8").startswith(
        "marginal_safe_yield_delta_row_id,"
    )


def _write_fixtures(tmp_path: Path) -> dict[str, Path]:
    d = tmp_path / "d.csv"
    _write_csv(
        d,
        [
            {
                "period_object": "current",
                "period": "2026",
                "horizon": "annual_h1_100bp_year",
                "state_id": "current_state::2026",
                "shock_path_id": "plus_100bp_year",
                "shock_bps_year": "100",
                "selected_marginal_D": "true",
            },
            {
                "period_object": "forecast",
                "period": "2036",
                "horizon": "annual_h1_100bp_year",
                "state_id": "cbo_baseline_state::2036",
                "shock_path_id": "plus_100bp_year",
                "shock_bps_year": "100",
                "selected_marginal_D": "true",
            },
        ],
    )
    admission = tmp_path / "admission.csv"
    _write_csv(
        admission,
        [
            {
                "candidate_family": "deposit_interest_payer_flow",
                "period_cashflow_gate": "pass_deposit_payer_flow_source_panel",
                "recipient_allocation_gate": "blocked_no_final_recipient_allocation",
                "denominator_alignment_gate": "blocked_candidate_cashflow_not_aligned_to_current_D_period",
                "tax_timing_gate": "pass_tax_timing",
                "demand_conversion_gate": "pass_demand_conversion",
                "overlap_gate": "blocked_overlap_unproven",
                "owner_gate": "blocked_owner_gate",
                "all_required_gates_pass": "false",
                "candidate_gross_flow_bil": "100",
                "central_n_delta_bil_allowed": "false",
                "central_n_delta_bil": "0",
                "blocked_reason": "blocked_no_final_recipient_allocation",
            }
        ],
    )
    assumptions = tmp_path / "assumptions.csv"
    _write_csv(
        assumptions,
        [
            {
                "period": "2036",
                "horizon": "annual_h1_100bp_year",
                "state_id": "cbo_baseline_state::2036",
                "shock_path_id": "plus_100bp_year",
                "eligible_deposit_stock_bil": "1000",
                "marginal_deposit_beta": "1",
                "recipient_share": "0.5",
                "coverage_alignment_factor": "0.75",
                "nonoverlap_factor": "0.8",
                "tax_timing_leakage_share": "0.25",
                "household_safe_yield_current_spend_share": "1",
                "selected_safe_yield_delta_allowed": "true",
                "source_panel_gate": "pass_forecast_assumption_source_panel",
                "recipient_allocation_gate": "pass_recipient_allocation",
                "denominator_alignment_gate": "pass_denominator_alignment",
                "tax_timing_gate": "pass_tax_timing",
                "demand_conversion_gate": "pass_demand_conversion",
                "overlap_gate": "pass_overlap",
                "owner_gate": "pass_owner",
                "blocked_reason": "",
            }
        ],
    )
    return {"d": d, "admission": admission, "assumptions": assumptions}


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
