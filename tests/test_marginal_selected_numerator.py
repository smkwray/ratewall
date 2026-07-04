from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path

import pytest

from ratewall.databook.marginal_selected_numerator import (
    MARGINAL_OVERLAP_AUDIT_FIELDS,
    MARGINAL_SELECTED_NUMERATOR_SURFACE_FIELDS,
    MarginalSelectedNumeratorError,
    marginal_overlap_audit_rows,
    marginal_selected_numerator_rows,
    validate_marginal_selected_numerator_rows,
    write_marginal_selected_numerator_outputs,
)


def test_selected_numerator_fails_closed_without_complete_inputs(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=False)

    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
    )
    overlap = marginal_overlap_audit_rows(rows)

    assert {field for row in rows for field in row} == set(
        MARGINAL_SELECTED_NUMERATOR_SURFACE_FIELDS
    )
    assert {row["selected_marginal_n_allowed"] for row in rows} == {"false"}
    assert "public_interest_delta" in rows[0]["missing_components"]
    assert "tdc_marginal_pair" in rows[0]["missing_components"]
    assert "safe_yield_delta" in rows[0]["missing_components"]
    assert "admitted_disjoint_residual_delta" in rows[0]["missing_components"]
    assert {field for row in overlap for field in row} == set(
        MARGINAL_OVERLAP_AUDIT_FIELDS
    )
    assert overlap[0]["overall_overlap_status"] == "fail_closed"


def test_selected_numerator_can_pass_when_all_delta_inputs_exist(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=True)

    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
    )

    assert rows[0]["selected_marginal_n_allowed"] == "true"
    assert rows[0]["selected_marginal_n_bil"] == "6.5"
    assert rows[0]["demand_conversion_case"] == "central"
    assert rows[0]["missing_components"] == ""
    assert rows[0]["delta_safe_yield_bil"] == "2"
    assert rows[0]["delta_other_admitted_disjoint_bil"] == "0.5"


def test_selected_numerator_outputs_are_written(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=False)
    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
    )
    outputs = write_marginal_selected_numerator_outputs(
        tmp_path / "out",
        selected_rows=rows,
        overlap_rows=marginal_overlap_audit_rows(rows),
    )

    assert outputs["selected_numerator_csv"].read_text(encoding="utf-8").startswith(
        "marginal_selected_numerator_row_id,"
    )


def test_bad_selected_numerator_rejects_missing_component_promotion(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=False)
    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
    )
    bad = deepcopy(rows)
    bad[0]["selected_marginal_n_allowed"] = "true"

    with pytest.raises(MarginalSelectedNumeratorError, match="missing"):
        validate_marginal_selected_numerator_rows(bad)


def test_selected_numerator_requires_tdc_full_marginal_key(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=True)
    tdc_rows = _read_csv(paths["tdc"])
    tdc_rows[0]["shock_path_id"] = "wrong_path"
    _write_csv(paths["tdc"], tdc_rows)

    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
    )

    assert rows[0]["selected_marginal_n_allowed"] == "false"
    assert "tdc_marginal_pair" in rows[0]["missing_components"]


def test_selected_numerator_rejects_tdc_selected_formula_with_entry_flag_false(
    tmp_path: Path,
) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=True)
    tdc_rows = _read_csv(paths["tdc"])
    tdc_rows[0]["enters_selected_rw_m"] = "false"
    _write_csv(paths["tdc"], tdc_rows)

    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
    )

    assert rows[0]["selected_marginal_n_allowed"] == "false"
    assert "tdc_marginal_pair" in rows[0]["missing_components"]


def test_selected_numerator_rejects_duplicate_tdc_full_key(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=True)
    tdc_rows = _read_csv(paths["tdc"])
    tdc_rows.append(dict(tdc_rows[0]))
    _write_csv(paths["tdc"], tdc_rows)

    with pytest.raises(MarginalSelectedNumeratorError, match="duplicate"):
        marginal_selected_numerator_rows(
            denominator_path=paths["d"],
            public_interest_path=paths["pi"],
            tdc_support_path=paths["tdc"],
            safe_yield_path=paths["safe"],
            admitted_residual_path=paths["residual"],
        )


def test_selected_n_rejects_blank_safe_yield_with_complete_status(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=True)
    safe_rows = _read_csv(paths["safe"])
    safe_rows[0]["delta_safe_yield_bil"] = ""
    _write_csv(paths["safe"], safe_rows)

    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
    )

    assert rows[0]["selected_marginal_n_allowed"] == "false"
    assert "safe_yield_delta" in rows[0]["missing_components"]


def test_selected_n_allows_explicit_fail_closed_zero_safe_yield(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=True)
    safe_rows = _read_csv(paths["safe"])
    safe_rows[0]["selected_safe_yield_delta_allowed"] = "false"
    safe_rows[0]["selection_gate_status"] = "fail_closed_named_blocker_zero"
    safe_rows[0]["delta_safe_yield_bil"] = "0"
    _write_csv(paths["safe"], safe_rows)

    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
    )

    assert rows[0]["selected_marginal_n_allowed"] == "true"
    assert rows[0]["selected_marginal_n_bil"] == "4.5"
    assert rows[0]["safe_yield_component_status"] == "fail_closed_named_blocker_zero"


def test_selected_n_rejects_fail_closed_nonzero_safe_yield(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=True)
    safe_rows = _read_csv(paths["safe"])
    safe_rows[0]["selected_safe_yield_delta_allowed"] = "false"
    safe_rows[0]["selection_gate_status"] = "fail_closed_named_blocker_zero"
    safe_rows[0]["delta_safe_yield_bil"] = "9"
    _write_csv(paths["safe"], safe_rows)

    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
    )

    assert rows[0]["selected_marginal_n_allowed"] == "false"
    assert rows[0]["safe_yield_component_status"] == "fail_closed_nonzero_component_rejected"
    assert "safe_yield_delta" in rows[0]["missing_components"]


def test_selected_n_missing_admitted_residual_status_fails_closed(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, include_inputs=True)
    residual_rows = _read_csv(paths["residual"])
    residual_rows[0]["selected_admitted_disjoint_delta_allowed"] = "false"
    residual_rows[0]["selection_gate_status"] = ""
    _write_csv(paths["residual"], residual_rows)

    rows = marginal_selected_numerator_rows(
        denominator_path=paths["d"],
        public_interest_path=paths["pi"],
        tdc_support_path=paths["tdc"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
    )

    assert rows[0]["selected_marginal_n_allowed"] == "false"
    assert "admitted_disjoint_residual_delta" in rows[0]["missing_components"]


def _write_fixtures(tmp_path: Path, *, include_inputs: bool) -> dict[str, Path]:
    d = tmp_path / "d.csv"
    _write_csv(
        d,
        [
            {
                "period_object": "forecast",
                "period": "2036",
                "horizon": "annual_h1_100bp_year",
                "state_id": "forecast_state::2036::plus",
                "shock_path_id": "plus_100bp_year",
                "selected_marginal_D": "true",
            }
        ],
    )
    pi = tmp_path / "pi.csv"
    tdc = tmp_path / "tdc.csv"
    safe = tmp_path / "safe.csv"
    residual = tmp_path / "residual.csv"
    if include_inputs:
        _write_csv(
            pi,
            [
                {
                    "period": "2036",
                    "horizon": "annual_h1_100bp_year",
                    "state_id": "forecast_state::2036::plus",
                    "shock_path_id": "plus_100bp_year",
                    "selected_pi_delta_allowed": "true",
                    "delta_public_interest_net_block_bil": "3",
                }
            ],
        )
        _write_csv(
            tdc,
            [
                {
                    "period": "2036",
                    "horizon": "annual_h1_100bp_year",
                    "state_id": "forecast_state::2036::plus",
                    "shock_path_id": "plus_100bp_year",
                    "demand_conversion_case": "central",
                    "selected_tdc_formula_pass": "true",
                    "enters_selected_rw_m": "true",
                    "marginal_tdc_support_bil": "1",
                }
            ],
        )
        _write_csv(
            safe,
            [
                {
                    "period": "2036",
                    "horizon": "annual_h1_100bp_year",
                    "state_id": "forecast_state::2036::plus",
                    "shock_path_id": "plus_100bp_year",
                    "selected_safe_yield_delta_allowed": "true",
                    "selection_gate_status": "pass_selected_marginal_safe_yield_delta",
                    "delta_safe_yield_bil": "2",
                }
            ],
        )
        _write_csv(
            residual,
            [
                {
                    "period": "2036",
                    "horizon": "annual_h1_100bp_year",
                    "state_id": "forecast_state::2036::plus",
                    "shock_path_id": "plus_100bp_year",
                    "selected_admitted_disjoint_delta_allowed": "true",
                    "selection_gate_status": "pass_selected_admitted_disjoint_delta",
                    "delta_other_admitted_disjoint_bil": "0.5",
                }
            ],
        )
    else:
        _write_csv(pi, [{"period": "2036", "selected_pi_delta_allowed": "false"}])
        _write_csv(tdc, [{"period": "2036", "selected_tdc_formula_pass": "false"}])
        _write_csv(safe, [{"period": "2036", "selected_safe_yield_delta_allowed": "false"}])
        _write_csv(residual, [{"period": "2036", "selected_admitted_disjoint_delta_allowed": "false"}])
    return {"d": d, "pi": pi, "tdc": tdc, "safe": safe, "residual": residual}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
