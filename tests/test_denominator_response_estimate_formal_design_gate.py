from __future__ import annotations

import pytest
import csv
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
REGISTRY_ARTIFACT = "ratewall_denominator_response_estimate_registry.csv"
GATE_ARTIFACT = "ratewall_denominator_formal_design_gate.csv"


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row.get("registered_point_estimate", "") == ""
        assert row.get("registered_ci_lower", "") == ""
        assert row.get("registered_ci_upper", "") == ""
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


def test_response_estimate_registry_design_cell_counts_and_estimators() -> None:
    rows = _rows(REGISTRY_ARTIFACT)
    _assert_fail_closed(rows)

    assert len(rows) == 12
    assert len({row["denominator_response_estimate_registry_row_id"] for row in rows}) == 12
    assert {row["target_horizon_quarters"] for row in rows} == {"4", "8"}
    assert {row["estimator_id"] for row in rows} == {
        "canonical_fspdp_design_placeholder",
        "mir_gk_component_irf_research_parameterization",
        "houst_permit_proxy_bridge_diagnostic",
        "frbus_official_model_benchmark",
        "local_projection_diagnostic",
        "proxy_svar_diagnostic",
    }


def test_response_estimate_registry_preserves_route_roles() -> None:
    rows = _rows(REGISTRY_ARTIFACT)
    by_estimator = {row["estimator_id"]: row for row in rows}

    assert by_estimator["frbus_official_model_benchmark"]["estimator_role"] == (
        "benchmark_only"
    )
    assert by_estimator["houst_permit_proxy_bridge_diagnostic"]["estimator_role"] == (
        "proxy_only_diagnostic"
    )
    assert by_estimator["mir_gk_component_irf_research_parameterization"][
        "estimator_role"
    ] == "research_parameterization_only"
    assert by_estimator["local_projection_diagnostic"]["estimator_family"] == (
        "local_projection"
    )
    assert by_estimator["proxy_svar_diagnostic"]["estimator_family"] == "proxy_svar"

    for row in rows:
        assert row["formal_design_gate_status"] == (
            "blocked_formal_design_gate_stack_incomplete"
        )
        assert row["response_estimate_registration_status"] == (
            "blocked_nonpromotional_design_cell_no_estimate_admitted"
        )
        assert row["source_admission_status"] != "admitted_denominator"
        assert int(row["observed_blocked_gate_count"]) >= 1
        assert "policy_path_100bp_year_normalization" in row["blocked_design_gates"]
        assert "promotion_rule" in row["blocked_design_gates"]


def test_formal_design_gate_has_eight_gates_per_design_cell() -> None:
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
    assert len(rows) == 96
    assert {row["design_gate"] for row in rows} == expected_gates

    by_cell: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_cell.setdefault(row["denominator_response_estimate_registry_row_id"], []).append(
            row
        )
        assert row["conventional_drag_response_design_gate_row_id"]
        assert row["formal_gate_status"] != "admitted_denominator_gate"
        assert row["disallowed_shortcut_evidence"]

    assert len(by_cell) == 12
    assert {len(cell_rows) for cell_rows in by_cell.values()} == {8}


def test_formal_design_gate_blocks_policy_path_and_promotion_for_every_cell() -> None:
    rows = _rows(GATE_ARTIFACT)

    policy_path_rows = [
        row
        for row in rows
        if row["design_gate"] == "policy_path_100bp_year_normalization"
    ]
    promotion_rows = [row for row in rows if row["design_gate"] == "promotion_rule"]

    assert len(policy_path_rows) == 12
    assert len(promotion_rows) == 12
    assert {row["formal_gate_status"] for row in policy_path_rows} == {
        "blocked_formal_gate_not_satisfied"
    }
    assert {row["formal_gate_status"] for row in promotion_rows} == {
        "blocked_formal_gate_not_satisfied"
    }
    assert all("scalar shocks" in row["disallowed_shortcut_evidence"] for row in policy_path_rows)
    assert all(
        "external recommendation" in row["disallowed_shortcut_evidence"]
        for row in promotion_rows
    )


def test_response_estimate_and_formal_gate_ledger_and_audit_invariants() -> None:
    ledger_rows = [
        row
        for row in _rows("ratewall_assumption_source_backing_ledger.csv")
        if row["artifact_or_surface"] in {REGISTRY_ARTIFACT, GATE_ARTIFACT}
    ]
    expected_counts = {
        REGISTRY_ARTIFACT: len(_rows(REGISTRY_ARTIFACT)),
        GATE_ARTIFACT: len(_rows(GATE_ARTIFACT)),
    }
    assert len(ledger_rows) == sum(expected_counts.values())
    for artifact, count in expected_counts.items():
        assert (
            len([row for row in ledger_rows if row["artifact_or_surface"] == artifact])
            == count
        )
    assert {row["source_backing_class"] for row in ledger_rows} == {
        "blocked_or_diagnostic_only"
    }
    assert {row["enters_canonical_ratio"] for row in ledger_rows} == {"false"}
    assert {row["prior_narrowing_allowed"] for row in ledger_rows} == {"false"}

    backend = {
        row["audit_item"]: row
        for row in _rows("ratewall_backend_invariant_guardrail_audit.csv")
    }
    assert backend["denominator_response_estimate_registry_fail_closed"][
        "audit_status"
    ] == "pass"
    assert backend["denominator_formal_design_gate_fail_closed"]["audit_status"] == (
        "pass"
    )

    source_backing = {
        row["audit_item"]: row
        for row in _rows("ratewall_assumption_source_backing_invariant_audit.csv")
    }
    assert source_backing["denominator_response_estimate_registry_fail_closed"][
        "audit_status"
    ] == "pass"
    assert source_backing["denominator_formal_design_gate_fail_closed"][
        "audit_status"
    ] == "pass"
