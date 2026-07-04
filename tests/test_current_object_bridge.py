from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path

import pytest

from ratewall.databook.current_object_bridge import (
    CURRENT_OBJECT_BRIDGE_FIELDS,
    CURRENT_OBJECT_FREEZE_DECISION_FIELDS,
    CURRENT_OBJECT_INPUT_MANIFEST_FIELDS,
    CurrentObjectBridgeError,
    current_object_bridge_readout_markdown,
    current_object_bridge_rows,
    current_object_freeze_decision_rows,
    current_object_input_manifest_rows,
    validate_current_object_bridge,
    validate_current_object_freeze_decision,
    write_current_object_bridge_outputs,
)


def test_current_object_bridge_outputs_exist(tmp_path: Path) -> None:
    dirs = _write_fixture(tmp_path)
    bridge = current_object_bridge_rows(
        current_overlay_dir=dirs["current_overlay"],
        safe_yield_dir=dirs["safe_yield"],
        runtime_table_dir=dirs["runtime"],
    )
    freeze = current_object_freeze_decision_rows(bridge)
    manifest = current_object_input_manifest_rows(runtime_table_dir=dirs["runtime"])
    readout = current_object_bridge_readout_markdown(
        bridge_rows=bridge,
        freeze_decision_rows=freeze,
        input_manifest_rows=manifest,
    )

    outputs = write_current_object_bridge_outputs(
        tmp_path / "out",
        bridge_rows=bridge,
        freeze_decision_rows=freeze,
        input_manifest_rows=manifest,
        readout_markdown=readout,
    )

    assert outputs["bridge_csv"].read_text(encoding="utf-8").startswith(
        "current_object_bridge_row_id,"
    )
    assert outputs["freeze_decision_csv"].read_text(encoding="utf-8").startswith(
        "freeze_decision_row_id,"
    )
    assert outputs["input_manifest_csv"].read_text(encoding="utf-8").startswith(
        "input_manifest_row_id,"
    )
    assert "does not change selected N, D, RW" in outputs["readout_md"].read_text(
        encoding="utf-8"
    )


def test_current_object_bridge_has_required_rows(tmp_path: Path) -> None:
    rows = _bridge_rows(tmp_path)

    assert {field for row in rows for field in row} == set(
        CURRENT_OBJECT_BRIDGE_FIELDS
    )
    by_id = {row["current_object_bridge_row_id"]: row for row in rows}
    assert {
        "current_object_bridge::legacy_static_lane",
        "current_object_bridge::selected_runtime_benchmark",
        "current_object_bridge::selected_public_interest_component",
        "current_object_bridge::selected_legacy_runtime_tdc_component",
        "current_object_bridge::r38_public_interest_candidate",
        "current_object_bridge::r38_beta_chi_tdc_candidate",
        "current_object_bridge::r38_composite_candidate",
        "current_object_bridge::d1_safe_yield_bounded_low",
        "current_object_bridge::d1_safe_yield_bounded_base",
        "current_object_bridge::d1_safe_yield_bounded_high",
    } <= set(by_id)


def test_current_bridge_selected_current_row_singleton(tmp_path: Path) -> None:
    rows = _bridge_rows(tmp_path)

    selected = [row for row in rows if row["selected_current_row"] == "true"]
    assert len(selected) == 1
    assert selected[0]["current_object_id"] == "current_assumption_benchmark::2026"


def test_current_bridge_selected_values_exact_decimal_strings(tmp_path: Path) -> None:
    rows = _bridge_rows(tmp_path)
    selected = _row(rows, "current_object_bridge::selected_runtime_benchmark")

    assert selected["n_bil"] == "83.542224868775"
    assert selected["d_bil"] == "247.55956656"
    assert selected["rw"] == "0.337463124652"
    assert selected["current_object_role"] == "selected_benchmark_recast"


def test_current_bridge_selected_components_sum_to_locked_n(tmp_path: Path) -> None:
    rows = _bridge_rows(tmp_path)
    selected = _row(rows, "current_object_bridge::selected_runtime_benchmark")

    assert selected["public_interest_component_bil"] == (
        "56.03251655775289810515522913"
    )
    assert selected["legacy_runtime_tdc_component_bil"] == (
        "27.50970831102218887944538608"
    )


def test_current_bridge_component_rows_are_not_selected_current_rows(
    tmp_path: Path,
) -> None:
    rows = _bridge_rows(tmp_path)

    assert all(
        row["selected_current_row"] == "false"
        for row in rows
        if row["selected_current_component"] == "true"
    )
    assert {
        row["current_object_role"]
        for row in rows
        if row["selected_current_component"] == "true"
    } == {"selected_block_input"}


def test_current_bridge_legacy_static_lane_reference_only(tmp_path: Path) -> None:
    rows = _bridge_rows(tmp_path)
    legacy = _row(rows, "current_object_bridge::legacy_static_lane")

    assert legacy["rw"] == "0.04157132893140423351153088093"
    assert legacy["current_object_role"] == "sensitivity_only"
    assert legacy["selected_current_row"] == "false"


def test_current_bridge_r38_overlay_nonselected_and_replacement_blocked(
    tmp_path: Path,
) -> None:
    rows = _bridge_rows(tmp_path)

    for row_id in [
        "current_object_bridge::r38_public_interest_candidate",
        "current_object_bridge::r38_beta_chi_tdc_candidate",
        "current_object_bridge::r38_composite_candidate",
    ]:
        row = _row(rows, row_id)
        assert row["selected_current_row"] == "false"
        assert "blocked" in row["replacement_gate_status"]
        assert row["current_object_role"] == "candidate_replacement"


def test_current_bridge_r38_tdc_uses_ex_overlap_beta_chi(tmp_path: Path) -> None:
    rows = _bridge_rows(tmp_path)
    row = _row(rows, "current_object_bridge::r38_beta_chi_tdc_candidate")

    assert row["r38_beta_chi_tdc_candidate_bil"] == (
        "19.25679581771553221561177026"
    )
    assert row["tdc_formula_basis"] == "tdc_change_ex_overlap_bil * beta * chi"
    assert "tdc_full_bil" in row["blocked_use"]


def test_current_bridge_r38_composite_not_selected(tmp_path: Path) -> None:
    rows = _bridge_rows(tmp_path)
    row = _row(rows, "current_object_bridge::r38_composite_candidate")

    assert row["n_bil"] == "75.28931237546843032076699939"
    assert row["d_bil"] == "247.55956656"
    assert row["rw"] == "0.3041260470021903496128297608"
    assert row["selected_current_row"] == "false"


def test_current_bridge_d1_safe_yield_noncentral_low_base_high(tmp_path: Path) -> None:
    rows = _bridge_rows(tmp_path)
    d1_rows = [row for row in rows if row["safe_yield_scenario"]]

    assert {row["safe_yield_scenario"] for row in d1_rows} == {"low", "base", "high"}
    assert all(row["selected_current_row"] == "false" for row in d1_rows)
    assert all(row["current_object_role"] == "sensitivity_only" for row in d1_rows)
    assert all(row["central_n_delta_bil_allowed"] == "false" for row in d1_rows)
    assert all(row["central_n_delta_bil"] == "0" for row in d1_rows)


def test_current_bridge_no_benchmark_r38_d1_hybrid_object(tmp_path: Path) -> None:
    rows = _bridge_rows(tmp_path)

    assert all("hybrid" not in row["current_object_id"] for row in rows)
    bad = deepcopy(rows)
    bad.append(dict(rows[0], current_object_id="benchmark_r38_d1_hybrid"))
    with pytest.raises(CurrentObjectBridgeError, match="hybrid"):
        validate_current_object_bridge(bad)


def test_current_bridge_freeze_decision_preserves_selected_values(
    tmp_path: Path,
) -> None:
    rows = _bridge_rows(tmp_path)
    freeze = current_object_freeze_decision_rows(rows)

    assert {field for row in freeze for field in row} == set(
        CURRENT_OBJECT_FREEZE_DECISION_FIELDS
    )
    assert freeze[0]["selected_current_object_id"] == (
        "current_assumption_benchmark::2026"
    )
    assert freeze[0]["selected_n_bil"] == "83.542224868775"
    assert freeze[0]["selected_d_bil"] == "247.55956656"
    assert freeze[0]["selected_rw"] == "0.337463124652"
    assert "hybrid" in freeze[0]["no_hybrid_rule"]
    validate_current_object_freeze_decision(freeze, bridge_rows=rows)


def test_current_bridge_input_manifest_records_runtime_replay_status(
    tmp_path: Path,
) -> None:
    dirs = _write_fixture(tmp_path)

    rows = current_object_input_manifest_rows(runtime_table_dir=dirs["runtime"])

    assert {field for row in rows for field in row} == set(
        CURRENT_OBJECT_INPUT_MANIFEST_FIELDS
    )
    assert len(rows) == 3
    assert all(row["exists"] == "true" for row in rows)
    assert all(row["runtime_replay_status"] == "runtime_replay_input_present" for row in rows)
    missing = current_object_input_manifest_rows(runtime_table_dir=tmp_path / "missing")
    assert all(
        row["runtime_replay_status"]
        == "generated_output_backed_not_runtime_replay_backed"
        for row in missing
    )


def _bridge_rows(tmp_path: Path) -> list[dict[str, str]]:
    dirs = _write_fixture(tmp_path)
    return current_object_bridge_rows(
        current_overlay_dir=dirs["current_overlay"],
        safe_yield_dir=dirs["safe_yield"],
        runtime_table_dir=dirs["runtime"],
    )


def _write_fixture(tmp_path: Path) -> dict[str, Path]:
    current = tmp_path / "current"
    safe_yield = tmp_path / "safe_yield"
    runtime = tmp_path / "runtime"
    for path in [current, safe_yield, runtime]:
        path.mkdir()
    _write_csv(
        current / "ratewall_current_assumption_benchmark.csv",
        [
            {
                "current_benchmark_row_id": "current_assumption_benchmark::2026",
                "benchmark_numerator_bil": "83.542224868775",
                "fixed_D_bil": "247.55956656",
                "benchmark_ratewall_ratio": "0.337463124652",
            }
        ],
    )
    _write_csv(
        current / "ratewall_current_observed_overlay_admission.csv",
        [
            {
                "public_interest_support_bil": "56.03251655775289810515522913",
                "legacy_runtime_tdc_support_bil": "27.50970831102218887944538608",
                "selected_beta_chi_tdc_support_bil": (
                    "19.25679581771553221561177026"
                ),
                "selected_overlay_candidate_n_bil": (
                    "75.28931237546843032076699939"
                ),
                "benchmark_D_bil": "247.55956656",
                "selected_overlay_candidate_ratewall_ratio": (
                    "0.3041260470021903496128297608"
                ),
                "replacement_gate_status": (
                    "blocked_candidate_changes_current_N_requires_R40_current_object_decision"
                ),
            }
        ],
    )
    _write_csv(
        safe_yield / "ratewall_realized_safe_yield_bounded_sensitivity.csv",
        [
            _safe_yield_row("low", "0.6"),
            _safe_yield_row("base", "8.3"),
            _safe_yield_row("high", "18.9"),
        ],
    )
    for filename in [
        "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv",
        "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv",
        "ratewall_runtime_annual_flow_support_offset_scenarios.csv",
    ]:
        _write_csv(runtime / filename, [{"row_id": filename, "value": "1"}])
    return {"current_overlay": current, "safe_yield": safe_yield, "runtime": runtime}


def _safe_yield_row(scenario: str, support: str) -> dict[str, str]:
    return {
        "scenario": scenario,
        "safe_yield_support_bil": support,
        "current_D_bil": "247.55956656",
        "support_to_current_D_ratio": "0.01",
        "central_n_delta_bil_allowed": "false",
        "central_n_delta_bil": "0",
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _row(rows: list[dict[str, str]], row_id: str) -> dict[str, str]:
    return next(row for row in rows if row["current_object_bridge_row_id"] == row_id)
