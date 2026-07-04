from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ratewall.databook.marginal_residual_sidecars import (
    CREDIT_INSULATION_SIDECAR_FIELDS,
    MARGINAL_ADMITTED_DISJOINT_DELTA_FIELDS,
    RESIDUAL_SAFE_YIELD_SIDECAR_FIELDS,
    credit_insulation_sidecar_rows,
    marginal_admitted_disjoint_delta_rows,
    residual_safe_yield_sidecar_rows,
    validate_credit_insulation_sidecar_rows,
    validate_residual_safe_yield_sidecar_rows,
    write_marginal_residual_sidecar_outputs,
)


def test_admitted_disjoint_residual_can_select_when_gates_pass(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_assumption=True)

    rows = marginal_admitted_disjoint_delta_rows(
        denominator_path=paths["d"],
        assumptions_path=paths["assumptions"],
    )

    assert {field for row in rows for field in row} == set(
        MARGINAL_ADMITTED_DISJOINT_DELTA_FIELDS
    )
    assert rows[0]["selected_admitted_disjoint_delta_allowed"] == "true"
    assert rows[0]["delta_other_admitted_disjoint_bil"] == "1.25"


def test_admitted_disjoint_residual_fails_closed_without_assumption(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_assumption=False)

    rows = marginal_admitted_disjoint_delta_rows(
        denominator_path=paths["d"],
        assumptions_path=paths["assumptions"],
    )

    assert rows[0]["selected_admitted_disjoint_delta_allowed"] == "false"
    assert rows[0]["delta_other_admitted_disjoint_bil"] == "0"
    assert "source_route_status" in rows[0]["missing_gates"]


def test_admitted_disjoint_residual_fails_closed_with_explicit_zero_assumption(
    tmp_path: Path,
) -> None:
    paths = _write_fixtures(tmp_path, include_assumption=True)
    assumptions = _read_csv(paths["assumptions"])
    assumptions[0]["delta_other_admitted_disjoint_bil"] = "0"
    assumptions[0]["selected_admitted_disjoint_delta_allowed"] = "false"
    assumptions[0]["source_route_status"] = "blocked_source_route"
    assumptions[0]["overlap_gate"] = "blocked_overlap"
    assumptions[0]["demand_conversion_gate"] = "blocked_demand_conversion"
    assumptions[0]["blocked_reason"] = "explicit_zero_route_present_no_admitted_value"
    _write_csv(paths["assumptions"], assumptions)

    rows = marginal_admitted_disjoint_delta_rows(
        denominator_path=paths["d"],
        assumptions_path=paths["assumptions"],
    )

    assert rows[0]["selected_admitted_disjoint_delta_allowed"] == "false"
    assert rows[0]["delta_other_admitted_disjoint_bil"] == "0"
    assert rows[0]["claim_boundary"].endswith("explicit_zero_route_present_no_admitted_value")


def test_admitted_disjoint_residual_rejects_fail_closed_nonzero_assumption(
    tmp_path: Path,
) -> None:
    paths = _write_fixtures(tmp_path, include_assumption=True)
    assumptions = _read_csv(paths["assumptions"])
    assumptions[0]["selected_admitted_disjoint_delta_allowed"] = "false"
    assumptions[0]["source_route_status"] = "blocked_source_route"
    _write_csv(paths["assumptions"], assumptions)

    rows = marginal_admitted_disjoint_delta_rows(
        denominator_path=paths["d"],
        assumptions_path=paths["assumptions"],
    )

    assert rows[0]["selected_admitted_disjoint_delta_allowed"] == "false"
    assert rows[0]["delta_other_admitted_disjoint_bil"] == "0"
    assert "nonselected_nonzero_delta" in rows[0]["missing_gates"]
    assert rows[0]["claim_boundary"].endswith(
        "nonselected_admitted_disjoint_nonzero_assumption_rejected"
    )


def test_residual_sidecar_outputs_are_written(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_assumption=False)
    admitted = marginal_admitted_disjoint_delta_rows(
        denominator_path=paths["d"],
        assumptions_path=paths["assumptions"],
    )
    safe = residual_safe_yield_sidecar_rows(admitted)
    credit = credit_insulation_sidecar_rows(admitted)
    outputs = write_marginal_residual_sidecar_outputs(
        tmp_path / "out",
        admitted_rows=admitted,
        safe_yield_sidecar_rows=safe,
        credit_sidecar_rows=credit,
    )

    assert {field for row in safe for field in row} == set(RESIDUAL_SAFE_YIELD_SIDECAR_FIELDS)
    assert {field for row in credit for field in row} == set(CREDIT_INSULATION_SIDECAR_FIELDS)
    validate_residual_safe_yield_sidecar_rows(safe)
    validate_credit_insulation_sidecar_rows(credit)
    assert safe[0]["delta_gross_residual_flow_bil"] == "0"
    assert safe[0]["delta_residual_safe_yield_support_bil"] == "0"
    assert safe[0]["selected_n_addition_allowed"] == "false"
    assert credit[0]["insulated_payment_flow_bil"] == "0"
    assert credit[0]["current_demand_support_sidecar_bil"] == "0"
    assert credit[0]["selected_n_addition_allowed"] == "false"
    assert outputs["admitted_disjoint_delta_csv"].read_text(encoding="utf-8").startswith(
        "marginal_admitted_disjoint_delta_row_id,"
    )


def test_residual_sidecars_never_enter_selected_n_directly(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_assumption=False)
    admitted = marginal_admitted_disjoint_delta_rows(
        denominator_path=paths["d"],
        assumptions_path=paths["assumptions"],
    )
    safe = residual_safe_yield_sidecar_rows(admitted)
    credit = credit_insulation_sidecar_rows(admitted)
    safe[0]["selected_n_addition_allowed"] = "true"
    credit[0]["selected_n_addition_allowed"] = "true"

    with pytest.raises(Exception, match="cannot directly select N"):
        validate_residual_safe_yield_sidecar_rows(safe)
    with pytest.raises(Exception, match="cannot directly select N"):
        validate_credit_insulation_sidecar_rows(credit)


def _write_fixtures(tmp_path: Path, *, include_assumption: bool) -> dict[str, Path]:
    d = tmp_path / "d.csv"
    _write_csv(
        d,
        [
            {
                "period_object": "forecast",
                "period": "2036",
                "horizon": "annual_h1_100bp_year",
                "state_id": "cbo_baseline_state::2036",
                "shock_path_id": "plus_100bp_year",
                "selected_marginal_D": "true",
            }
        ],
    )
    assumptions = tmp_path / "assumptions.csv"
    if include_assumption:
        _write_csv(
            assumptions,
            [
                {
                    "period": "2036",
                    "horizon": "annual_h1_100bp_year",
                    "state_id": "cbo_baseline_state::2036",
                    "shock_path_id": "plus_100bp_year",
                    "delta_other_admitted_disjoint_bil": "1.25",
                    "selected_admitted_disjoint_delta_allowed": "true",
                    "source_route_status": "pass_source_route",
                    "overlap_gate": "pass_overlap",
                    "demand_conversion_gate": "pass_demand_conversion",
                    "blocked_reason": "",
                }
            ],
        )
    else:
        _write_csv(assumptions, [{"period": "1900"}])
    return {"d": d, "assumptions": assumptions}


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
