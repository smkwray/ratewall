from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from collections.abc import Iterable
from copy import deepcopy
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from ratewall.databook.final_marginal_model import (
    EXPOSURE_DIAGNOSTICS_SNAPSHOT_FIELDS,
    FINAL_MARGINAL_READINESS_FIELDS,
    FINAL_MARGINAL_RW_RATIO_FIELDS,
    SELECTED_RW_M_CLAIM_BOUNDARY,
    SELECTED_RW_M_RWTAM_BLOCKED_USE,
    FinalMarginalModelError,
    exposure_diagnostics_snapshot_rows,
    final_marginal_readiness_rows,
    final_marginal_rw_ratio_rows,
    validate_final_marginal_rw_ratio_rows,
    write_final_marginal_model_outputs,
)
from ratewall.databook.marginal_residual_sidecars import (
    marginal_admitted_disjoint_delta_rows,
)
from ratewall.databook.marginal_safe_yield import marginal_safe_yield_delta_rows
from ratewall.databook.marginal_selected_numerator import marginal_selected_numerator_rows


def test_final_marginal_model_fails_closed_without_selected_n(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, selected_n=False)

    rows = final_marginal_rw_ratio_rows(
        selected_numerator_path=paths["n"],
        denominator_path=paths["d"],
    )
    readiness = final_marginal_readiness_rows(rows)
    diagnostics = exposure_diagnostics_snapshot_rows()

    assert {field for row in rows for field in row} == set(FINAL_MARGINAL_RW_RATIO_FIELDS)
    assert rows[0]["final_rw_m_selected"] == "false"
    assert rows[0]["final_rw_m"] == ""
    assert "selected_marginal_n" in rows[0]["blocked_reason"]
    assert {field for row in readiness for field in row} == set(
        FINAL_MARGINAL_READINESS_FIELDS
    )
    assert {field for row in diagnostics for field in row} == set(
        EXPOSURE_DIAGNOSTICS_SNAPSHOT_FIELDS
    )


def test_final_marginal_model_can_select_when_n_and_d_pass(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, selected_n=True)

    rows = final_marginal_rw_ratio_rows(
        selected_numerator_path=paths["n"],
        denominator_path=paths["d"],
    )

    assert rows[0]["final_rw_m_selected"] == "true"
    assert rows[0]["final_rw_m"] == "0.25"
    assert rows[0]["demand_conversion_case"] == "central"
    assert SELECTED_RW_M_RWTAM_BLOCKED_USE in rows[0]["blocked_use"]
    assert rows[0]["claim_boundary"] == SELECTED_RW_M_CLAIM_BOUNDARY


def test_production_final_rw_m_selected_row_values_are_pinned() -> None:
    """Pins production RW_M inputs; legitimate future assumption changes update this test in the same disclosed wave."""

    with localcontext() as context:
        context.prec = 200
        numerator_rows = marginal_selected_numerator_rows()
        ratio_rows = final_marginal_rw_ratio_rows()
    selected_n = _single(
        row for row in numerator_rows if row["selected_marginal_n_allowed"] == "true"
    )
    selected_ratio = _single(
        row for row in ratio_rows if row["final_rw_m_selected"] == "true"
    )

    assert selected_n["period_object"] == "current"
    assert selected_n["period"] == "2026"
    assert selected_n["state_id"] == "current_state::2026"
    assert Decimal(selected_n["delta_public_interest_net_block_bil"]) == Decimal(
        "3.396099850035526154"
    )
    assert Decimal(selected_n["marginal_tdc_support_bil"]) == Decimal(
        "0.005429282741146583401930310445"
    )
    assert Decimal(selected_n["delta_safe_yield_bil"]) == Decimal("2.04231728224")
    assert Decimal(selected_n["delta_other_admitted_disjoint_bil"]) == Decimal(
        "0.1289220072"
    )
    assert Decimal(selected_n["selected_marginal_n_bil"]) == Decimal(
        "5.572768422216672737401930310445"
    )
    assert Decimal(selected_ratio["selected_marginal_D_bil"]) == Decimal("247.55956656")
    assert Decimal(selected_ratio["final_rw_m"]) == Decimal(
        "0.022510818303868792883711091556533867603973074269224879838551935781027003265245981936574610554609786678243406922856263705036921599625537815855190274170594750777947880084541702390351769567260467092328553"
    )
    assert selected_ratio["readiness_status"] == "pass_final_marginal_rw_selected"
    assert SELECTED_RW_M_RWTAM_BLOCKED_USE in selected_ratio["blocked_use"]
    assert selected_ratio["claim_boundary"] == SELECTED_RW_M_CLAIM_BOUNDARY


def test_production_assumption_mode_component_values_are_pinned() -> None:
    """Pins live config-backed component builders so silent assumption CSV edits fail fast."""

    pi = _current_public_interest_delta_from_builder()
    safe_yield = _single(
        row
        for row in marginal_safe_yield_delta_rows()
        if row["period"] == "2026"
        and row["state_id"] == "current_state::2026"
        and row["selected_safe_yield_delta_allowed"] == "true"
    )
    residual = _single(
        row
        for row in marginal_admitted_disjoint_delta_rows()
        if row["period"] == "2026"
        and row["state_id"] == "current_state::2026"
        and row["selected_admitted_disjoint_delta_allowed"] == "true"
    )
    tdc = _single(
        row
        for row in _read_csv(
            Path(
                "var/preliminary_scenario_results/marginal_tdcsim/"
                "ratewall_marginal_tdc_support_panel.csv"
            )
        )
        if row["period"] == "2026" and row["state_id"] == "current_state::2026"
    )

    assert Decimal(pi["delta_public_interest_net_block_bil"]) == Decimal(
        "3.396099850035526154"
    )
    assert Decimal(safe_yield["delta_safe_yield_bil"]) == Decimal("2.04231728224")
    assert Decimal(residual["delta_other_admitted_disjoint_bil"]) == Decimal(
        "0.1289220072"
    )
    assert Decimal(tdc["marginal_tdc_support_bil"]) == Decimal(
        "0.005429282741146583401930310445"
    )
    assert tdc["selected_tdc_formula_pass"] == "true"
    assert tdc["enters_selected_rw_m"] == "true"
    assert "tdc_income_addendum_split_admissible" in tdc["support_formula"]
    assert "legacy_chi_support" in tdc["blocked_use"]


def test_production_final_rw_m_fail_closed_reasons_are_pinned() -> None:
    rows = marginal_selected_numerator_rows()
    forecast_rows = [row for row in rows if row["period_object"] == "forecast"]
    historical_selected_window_rows = [
        row
        for row in rows
        if row["period_object"] == "historical"
        and "2022Q1" <= row["period"] <= "2025Q4"
    ]

    assert forecast_rows
    assert historical_selected_window_rows
    assert {row["missing_components"] for row in forecast_rows} == {
        "public_interest_delta"
    }
    assert {row["missing_components"] for row in historical_selected_window_rows} == {
        "tdc_marginal_pair"
    }
    assert all(row["selected_marginal_n_allowed"] == "false" for row in forecast_rows)
    assert all(
        row["selected_marginal_n_allowed"] == "false"
        for row in historical_selected_window_rows
    )


def test_final_marginal_outputs_are_written(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, selected_n=False)
    rows = final_marginal_rw_ratio_rows(
        selected_numerator_path=paths["n"],
        denominator_path=paths["d"],
    )
    outputs = write_final_marginal_model_outputs(
        tmp_path / "out",
        ratio_rows=rows,
        readiness_rows=final_marginal_readiness_rows(rows),
        diagnostic_rows=exposure_diagnostics_snapshot_rows(),
    )

    assert outputs["ratio_snapshot_csv"].read_text(encoding="utf-8").startswith(
        "final_marginal_rw_row_id,"
    )


def test_bad_final_marginal_model_rejects_nonselected_ratio(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path, selected_n=False)
    rows = final_marginal_rw_ratio_rows(
        selected_numerator_path=paths["n"],
        denominator_path=paths["d"],
    )
    bad = deepcopy(rows)
    bad[0]["final_rw_m"] = "0.1"

    with pytest.raises(FinalMarginalModelError, match="nonselected"):
        validate_final_marginal_rw_ratio_rows(bad)


def _write_fixtures(tmp_path: Path, *, selected_n: bool) -> dict[str, Path]:
    n = tmp_path / "n.csv"
    _write_csv(
        n,
        [
            {
                "period_object": "forecast",
                "period": "2036",
                "horizon": "annual_h1_100bp_year",
                "state_id": "forecast_state::2036::plus",
                "shock_path_id": "plus_100bp_year",
                "demand_conversion_case": "central",
                "selected_marginal_n_allowed": str(selected_n).lower(),
                "selected_marginal_n_bil": "2" if selected_n else "",
            }
        ],
    )
    d = tmp_path / "d.csv"
    _write_csv(
        d,
        [
            {
                "period": "2036",
                "horizon": "annual_h1_100bp_year",
                "state_id": "forecast_state::2036::plus",
                "shock_path_id": "plus_100bp_year",
                "selected_marginal_D": "true",
                "marginal_denominator_bil": "8",
            }
        ],
    )
    return {"n": n, "d": d}


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _single(rows: Iterable[dict[str, str]]) -> dict[str, str]:
    materialized = list(rows)
    assert len(materialized) == 1
    return materialized[0]


def _current_public_interest_delta_from_builder() -> dict[str, str]:
    code = """
import json
from ratewall.databook.marginal_public_interest import marginal_public_interest_delta_rows
row = [
    row
    for row in marginal_public_interest_delta_rows()
    if row["period"] == "2026"
    and row["state_id"] == "current_state::2026"
    and row["selected_pi_delta_allowed"] == "true"
]
assert len(row) == 1
print(json.dumps(row[0], sort_keys=True))
"""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        env=env,
        text=True,
    )
    return json.loads(result.stdout)
