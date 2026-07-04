from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.rwtas.hysteresis import (
    INTEREST_BEARING_DEPOSIT_FAMILIES,
    build_hysteresis_experiment,
    measure_wall_from_state,
    run_engine_records,
    write_hysteresis_outputs,
)
from ratewall.rwtas.v1 import build_v1


PACK_DIR = Path("configs/rwtas/packs")


@pytest.fixture(scope="module")
def hysteresis_output_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("rwtas_hysteresis_redo")


@pytest.fixture(scope="module")
def hysteresis_result(hysteresis_output_root: Path):
    return build_hysteresis_experiment(
        PACK_DIR,
        full_grid=False,
        output_root=hysteresis_output_root,
    )


def test_measure_wall_from_opening_state_reproduces_default_headline_byte_exact(
    tmp_path: Path,
) -> None:
    expected = [
        row
        for row in build_v1(PACK_DIR).rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]

    records = run_engine_records(PACK_DIR, pulse_size_bp=Decimal("0"), enabled_mechanisms=frozenset())
    measured = measure_wall_from_state(records, 0, PACK_DIR, output_root=tmp_path)

    comparable = {key: value for key, value in measured.headline_row.items() if key != "source_rollup_path"}
    assert comparable == expected


def test_r1_export_gate_and_mutation_probe_are_real(hysteresis_result) -> None:
    gates = {row["check_id"]: row for row in hysteresis_result.rows("out_hysteresis_r1_gate")}
    assert gates["R1_month0_export_build_v1_byte_exact"]["status"] == "pass"
    assert gates["R1_mutation_probe_fails"]["status"] == "pass"
    assert gates["R1_mutation_probe_fails"]["expected_RW_ratio"] != gates["R1_mutation_probe_fails"]["mutated_RW_ratio"]


def test_hysteresis_grid_wires_evidence_bands_and_definition_pin(hysteresis_result) -> None:
    params = {row["parameter_id"]: row for row in hysteresis_result.rows("out_hysteresis_parameter_rows")}
    assert params["reversal_share"]["low"] == "0"
    assert params["reversal_share"]["base"] == "0.05"
    assert params["reversal_share"]["high"] == "0.15"
    assert params["deposit_beta_competition_elasticity"]["low"] == "0.5"
    assert params["deposit_beta_competition_elasticity"]["base"] == "1.5"
    assert params["deposit_beta_competition_elasticity"]["high"] == "3"
    for family in INTEREST_BEARING_DEPOSIT_FAMILIES:
        assert family in params["deposit_beta_competition_elasticity"]["definition_pin"]
    assert "deposits_checkable" not in params["deposit_beta_competition_elasticity"]["definition_pin"]

    caveats = {row["caveat_id"]: row for row in hysteresis_result.rows("out_hysteresis_caveats")}
    assert caveats["non_identification_caveat"]["claim_grade_label"] == "scenario_diagnostic_non_claim"


def test_hysteresis_experiment_grid_and_conditions_surface(hysteresis_result, tmp_path: Path) -> None:
    rows = hysteresis_result.rows("out_hysteresis_experiment")
    assert len(rows) == 2 * 1 * 1 * 2
    assert {row["remeasure_month_index"] for row in rows} == {"24", "120"}
    assert all(row["claim_grade_label"] == "engine_loop_scenario" for row in rows)
    assert all("interaction_residual_delta_RW" in row for row in rows)
    assert all("migration_plus_beta_delta_RW" in row for row in rows)
    assert all("beta_uplift_only_delta_RW" not in row for row in rows)
    assert all(row["migration_inactive_below_threshold"] == "true" for row in rows if row["pulse_size_bp"] == "100")
    assert any(Decimal(row["delta_RW_ratio"]) > 0 for row in rows if row["remeasure_month_index"] == "120")

    conditions = hysteresis_result.rows("out_hysteresis_conditions")
    assert len(conditions) == 2
    assert any(row["hysteresis_holds_delta_RW_120_gt_0"] == "true" for row in conditions)

    paths = write_hysteresis_outputs(hysteresis_result, tmp_path)
    assert paths["out_hysteresis_experiment_required"].exists()
    assert paths["out_response_curve_required"].exists()
    with paths["out_hysteresis_experiment_required"].open(encoding="utf-8", newline="") as handle:
        written = list(csv.DictReader(handle))
    assert len(written) == len(rows)

    comparison = hysteresis_result.rows("out_hysteresis_old_vs_new_comparison")
    assert comparison
    assert all("classification" in row for row in comparison)

    closure = hysteresis_result.rows("out_hysteresis_migration_t49_monthly")
    assert any(row["probe_id"] == "engine_loop" and row["status"] == "pass" for row in closure)
    assert any(
        row["probe_id"] == "mis_tagged_migration_row_probe"
        and row["status"] == "fail"
        and row["expected_status"] == "fail"
        for row in closure
    )


def test_response_curve_is_labeled_and_turns_convex_negative(hysteresis_result) -> None:
    rows = hysteresis_result.rows("out_response_curve")

    assert len(rows) == 2 * 2 * 2
    assert {row["distress_on"] for row in rows} == {"true"}
    assert {row["holder_stress_on"] for row in rows} == {"true"}

    high_100 = next(
        row
        for row in rows
        if row["state_id"] == "high_wall_state"
        and row["horizon"] == "annual"
        and row["shock_bp"] == "100"
    )
    high_500 = next(
        row
        for row in rows
        if row["state_id"] == "high_wall_state"
        and row["horizon"] == "annual"
        and row["shock_bp"] == "500"
    )
    assert Decimal(high_100["net_demand_effect_bil"]) > Decimal(high_500["net_demand_effect_bil"])
    assert Decimal(high_500["deadweight_bil"]) > 0

    thresholds = hysteresis_result.rows("out_response_crash_threshold")
    assert {row["threshold_rule"] for row in thresholds} == {
        "nd_negative_throughout_no_interior_threshold"
    }
    assert all("D is about 20x N" in row["threshold_explanation"] for row in thresholds)
