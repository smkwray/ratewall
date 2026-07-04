from __future__ import annotations

import pytest
import csv
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
PRUNING_ARTIFACT = "ratewall_conventional_drag_route_pruning_audit.csv"
GATE_ARTIFACT = "ratewall_conventional_drag_response_design_gate.csv"


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["candidate_bps_year_exposure"] == ""
        assert row["candidate_gdp_share_drag_per_100bp_year"] == ""
        assert row["candidate_ci_lower"] == ""
        assert row["candidate_ci_upper"] == ""
        assert row["denominator_prior_update_allowed"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        assert row["prior_narrowing_allowed"] == "false"
        assert row["split_denominator_promotion_allowed"] == "false"
        assert row["formula_replacement_allowed"] == "false"
        for field in FORBIDDEN_SWITCH_FIELDS:
            assert row[field] == "false"


def test_route_pruning_audit_row_grain_and_route_decisions() -> None:
    rows = _rows(PRUNING_ARTIFACT)
    _assert_fail_closed(rows)

    assert len(rows) == 6
    assert len({row["conventional_drag_route_pruning_audit_row_id"] for row in rows}) == 6

    by_route = {row["route_id"]: row for row in rows}
    assert by_route["canonical_fspdp_current_demand_drag_100bp_year"][
        "pruning_decision"
    ] == "retain_preferred_fspdp_target_but_block_admission"
    assert by_route["frbus_official_model_benchmark_route"]["pruning_decision"] == (
        "prune_to_benchmark_only"
    )
    assert by_route["houst_permit_residential_activity_proxy_route"][
        "pruning_decision"
    ] == "prune_to_proxy_only_diagnostic"
    assert by_route["mir_gk_research_parameterization_route"][
        "pruning_decision"
    ] == "prune_to_research_parameterization_only"
    assert by_route["local_lp_proxy_svar_diagnostic_route"]["pruning_decision"] == (
        "retain_as_diagnostic_response_design_only"
    )
    assert by_route["official_fspdp_component_share_context"]["pruning_decision"] == (
        "retain_as_component_share_context_only"
    )


def test_route_pruning_audit_preserves_denominator_gate_blockers() -> None:
    rows = _rows(PRUNING_ARTIFACT)

    for row in rows:
        assert row["pruning_status"].startswith("blocked")
        assert row["admission_status"] != "admitted_denominator"
        assert "policy_path_100bp_year_normalization" in row["failed_gate_stack"]
        assert "promotion_rule" in row["failed_gate_stack"]
        assert row["required_gate_stack"] == (
            "policy_path_100bp_year_normalization;current_demand_mapping;"
            "gdp_share_conversion;uncertainty;replication;robustness;promotion_rule"
        )

    frbus = next(row for row in rows if row["benchmark_only"] == "true")
    assert frbus["retained_backend_role"] == "official_model_benchmark_context"
    assert "main_ratio" in frbus["excluded_from_roles"]

    proxy = next(row for row in rows if row["proxy_only"] == "true")
    assert proxy["retained_backend_role"] == "housing_activity_proxy_diagnostic"
    assert "direct_pfi_component" in proxy["excluded_from_roles"]


def test_response_design_gate_stack_has_eight_gates_per_route() -> None:
    rows = _rows(GATE_ARTIFACT)
    _assert_fail_closed(rows)

    expected_gates = {
        "policy_path_100bp_year_normalization",
        "source_unit_or_model_boundary",
        "current_demand_mapping",
        "gdp_share_conversion",
        "uncertainty_interval",
        "independent_replication",
        "robustness_transport",
        "promotion_rule",
    }
    assert len(rows) == 48
    assert {row["design_gate"] for row in rows} == expected_gates

    by_route: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_route.setdefault(row["route_id"], []).append(row)
        assert row["response_design_status"] == (
            "blocked_response_design_gate_stack_incomplete"
        )
        assert row["route_admission_status"] != "admitted_denominator"
        assert row["disallowed_shortcut_evidence"]

    assert len(by_route) == 6
    assert {len(route_rows) for route_rows in by_route.values()} == {8}


def test_response_design_gate_blocks_shortcuts_and_key_gates() -> None:
    rows = _rows(GATE_ARTIFACT)

    policy_path_rows = [
        row
        for row in rows
        if row["design_gate"] == "policy_path_100bp_year_normalization"
    ]
    assert len(policy_path_rows) == 6
    assert {
        row["gate_pass_status"] for row in policy_path_rows
    } == {"blocked_gate_not_admitted"}
    assert all(
        "scalar shocks" in row["disallowed_shortcut_evidence"]
        for row in policy_path_rows
    )

    promotion_rows = [row for row in rows if row["design_gate"] == "promotion_rule"]
    assert len(promotion_rows) == 6
    assert {row["gate_pass_status"] for row in promotion_rows} == {
        "blocked_gate_not_admitted"
    }
    assert all(
        "external recommendation" in row["disallowed_shortcut_evidence"]
        for row in promotion_rows
    )


def test_route_pruning_and_response_gate_ledger_and_audit_invariants() -> None:
    pruning_rows = _rows(PRUNING_ARTIFACT)
    gate_rows = _rows(GATE_ARTIFACT)
    ledger_rows = [
        row
        for row in _rows("ratewall_assumption_source_backing_ledger.csv")
        if row["artifact_or_surface"] in {PRUNING_ARTIFACT, GATE_ARTIFACT}
    ]
    assert len(ledger_rows) == len(pruning_rows) + len(gate_rows)
    assert {row["source_backing_class"] for row in ledger_rows} == {
        "blocked_or_diagnostic_only"
    }
    assert {row["enters_canonical_ratio"] for row in ledger_rows} == {"false"}
    assert {row["prior_narrowing_allowed"] for row in ledger_rows} == {"false"}

    backend = {
        row["audit_item"]: row
        for row in _rows("ratewall_backend_invariant_guardrail_audit.csv")
    }
    assert backend["conventional_drag_route_pruning_audit_fail_closed"][
        "audit_status"
    ] == "pass"
    assert backend["conventional_drag_response_design_gate_fail_closed"][
        "audit_status"
    ] == "pass"

    source_backing = {
        row["audit_item"]: row
        for row in _rows("ratewall_assumption_source_backing_invariant_audit.csv")
    }
    assert source_backing["conventional_drag_route_pruning_audit_fail_closed"][
        "audit_status"
    ] == "pass"
    assert source_backing["conventional_drag_response_design_gate_fail_closed"][
        "audit_status"
    ] == "pass"
