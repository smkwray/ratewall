from __future__ import annotations

import pytest
import csv
from collections import Counter
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
FIELD_ARTIFACT = "ratewall_policy_path_source_bundle_field_exhaustion_decision.csv"
COMPONENT_ARTIFACT = (
    "ratewall_policy_path_source_bundle_component_exhaustion_decision.csv"
)
NO_HIT_FIELDS = {
    "source_cell_unit_sign__price_to_rate_sign_transform",
    "bps_year_formula__aggregation_formula",
    "bps_year_formula__bps_year_component_formula",
    "event_date_horizon_grid__no_static_quarter_fallback",
    "event_date_horizon_grid__year_fractions",
}


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed_tail(row: dict[str, str]) -> None:
    assert row["candidate_rate_change_bps"] == ""
    assert row["candidate_bps_year_component"] == ""
    assert row["candidate_bps_year_exposure"] == ""
    assert row["bps_year_exposure_output"] == ""
    assert row["candidate_gdp_share_drag_per_100bp_year"] == ""
    assert row["candidate_ci_lower"] == ""
    assert row["candidate_ci_upper"] == ""
    assert row["protocol_admission_status"].startswith("blocked")
    assert row["policy_path_100bp_year_normalization_status"].startswith("blocked")
    assert row["enters_main_ratio"] == "false"
    assert row["evidence_mode_enabled"] == "false"
    assert row["denominator_prior_update_allowed"] == "false"
    assert row["prior_narrowing_allowed"] == "false"
    for field in FORBIDDEN_SWITCH_FIELDS:
        assert row[field] == "false"


def test_source_bundle_field_exhaustion_row_grain_and_classes() -> None:
    rows = _rows(FIELD_ARTIFACT)

    assert len(rows) == 39
    assert (
        len({row["policy_path_source_bundle_field_exhaustion_decision_row_id"] for row in rows})
        == 39
    )
    assert Counter(row["field_decision_class"] for row in rows) == {
        "context_locator_review_only_not_promotable": 18,
        "terminal_no_hit_exhausted_current_source_bundle": 5,
        "independent_replication_design_only_not_implemented": 5,
        "authored_fail_closed_invariant_only_not_admission": 11,
    }
    assert {
        row["authored_field_name"]
        for row in rows
        if row["field_decision_class"]
        == "terminal_no_hit_exhausted_current_source_bundle"
    } == NO_HIT_FIELDS
    assert {row["current_source_bundle_exhausted"] for row in rows} == {
        "false",
        "true",
    }


def test_source_bundle_field_exhaustion_links_upstream_decisions() -> None:
    rows = _rows(FIELD_ARTIFACT)
    by_class: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_class.setdefault(row["field_decision_class"], []).append(row)

    for row in by_class["context_locator_review_only_not_promotable"]:
        assert row["linked_terminal_no_hit_closure_row_id"].startswith(
            "policy_path_terminal_no_hit_closure::"
        )
        assert row["linked_pass_rule_adjudication_row_ids"]
        assert row["context_only_locator_count"] == "4"
        assert row["terminal_no_hit_count"] == "0"
        assert row["current_source_bundle_exhausted"] == "false"

    for row in by_class["terminal_no_hit_exhausted_current_source_bundle"]:
        assert row["linked_terminal_no_hit_closure_row_id"].startswith(
            "policy_path_terminal_no_hit_closure::"
        )
        assert row["linked_pass_rule_adjudication_row_ids"]
        assert row["context_only_locator_count"] == "0"
        assert row["terminal_no_hit_count"] == "4"
        assert row["current_source_bundle_exhausted"] == "true"

    for row in by_class["independent_replication_design_only_not_implemented"]:
        assert row["linked_independent_replication_design_row_id"].startswith(
            "policy_path_independent_replication_target_design::"
        )
        assert row["linked_terminal_no_hit_closure_row_id"] == ""
        assert row["linked_authored_invariant_design_row_id"] == ""

    for row in by_class["authored_fail_closed_invariant_only_not_admission"]:
        assert row["linked_authored_invariant_design_row_id"].startswith(
            "policy_path_authored_fail_closed_invariant_design::"
        )
        assert row["linked_terminal_no_hit_closure_row_id"] == ""
        assert row["linked_independent_replication_design_row_id"] == ""


def test_source_bundle_component_exhaustion_row_grain_and_classes() -> None:
    rows = _rows(COMPONENT_ARTIFACT)

    assert len(rows) == 7
    assert (
        len(
            {
                row[
                    "policy_path_source_bundle_component_exhaustion_decision_row_id"
                ]
                for row in rows
            }
        )
        == 7
    )
    assert {row["protocol_component"] for row in rows} == {
        "source_cell_unit_sign",
        "event_date_horizon_grid",
        "loading_back_transform",
        "bps_year_formula",
        "independent_replication_target_tolerance",
        "denominator_isolation",
        "promotion_rule",
    }
    assert Counter(row["component_decision_class"] for row in rows) == {
        "source_component_current_bundle_context_or_no_hit_not_promotable": 4,
        "independent_replication_component_design_only_not_admitted": 1,
        "authored_invariant_component_design_only_not_admitted": 2,
    }
    assert {row["full_protocol_gate_status"] for row in rows} == {
        "blocked_full_policy_path_protocol_gate_conjunction_incomplete"
    }


def test_source_bundle_component_exhaustion_counts() -> None:
    rows = {row["protocol_component"]: row for row in _rows(COMPONENT_ARTIFACT)}

    assert rows["source_cell_unit_sign"]["context_only_field_count"] == "5"
    assert rows["source_cell_unit_sign"]["terminal_no_hit_field_count"] == "1"
    assert rows["event_date_horizon_grid"]["context_only_field_count"] == "5"
    assert rows["event_date_horizon_grid"]["terminal_no_hit_field_count"] == "2"
    assert rows["loading_back_transform"]["context_only_field_count"] == "5"
    assert rows["loading_back_transform"]["terminal_no_hit_field_count"] == "0"
    assert rows["bps_year_formula"]["context_only_field_count"] == "3"
    assert rows["bps_year_formula"]["terminal_no_hit_field_count"] == "2"
    assert (
        rows["independent_replication_target_tolerance"][
            "independent_replication_design_field_count"
        ]
        == "5"
    )
    assert rows["denominator_isolation"]["authored_invariant_design_field_count"] == "6"
    assert rows["promotion_rule"]["authored_invariant_design_field_count"] == "5"
    for row in rows.values():
        assert row["promotion_grade_evidence_count"] == "0"
        assert row["field_pass_count"] == "0"
        assert row["linked_field_exhaustion_decision_row_ids"]


def test_source_bundle_exhaustion_fail_closed_outputs_and_switches() -> None:
    for row in _rows(FIELD_ARTIFACT):
        _assert_fail_closed_tail(row)
        assert row["field_decision_status"].startswith("blocked")
        assert row["allowed_use"] == (
            "policy_path_source_bundle_field_exhaustion_decision_only"
        )
    for row in _rows(COMPONENT_ARTIFACT):
        _assert_fail_closed_tail(row)
        assert row["component_decision_status"].startswith("blocked")
        assert row["allowed_use"] == (
            "policy_path_source_bundle_component_exhaustion_decision_only"
        )


def test_source_bundle_exhaustion_ledger_and_audit_invariant() -> None:
    ledger_rows = _rows("ratewall_assumption_source_backing_ledger.csv")
    expected = {
        FIELD_ARTIFACT: len(_rows(FIELD_ARTIFACT)),
        COMPONENT_ARTIFACT: len(_rows(COMPONENT_ARTIFACT)),
    }
    for artifact, count in expected.items():
        artifact_ledger_rows = [
            row for row in ledger_rows if row["artifact_or_surface"] == artifact
        ]
        assert len(artifact_ledger_rows) == count
        assert {row["source_backing_class"] for row in artifact_ledger_rows} == {
            "blocked_or_diagnostic_only"
        }
        assert {row["enters_canonical_ratio"] for row in artifact_ledger_rows} == {
            "false"
        }

    backend = {
        row["audit_item"]: row
        for row in _rows("ratewall_backend_invariant_guardrail_audit.csv")
    }
    for audit_item in {
        "policy_path_source_bundle_field_exhaustion_decision_fail_closed",
        "policy_path_source_bundle_component_exhaustion_decision_fail_closed",
    }:
        assert backend[audit_item]["audit_status"] == "pass"

    source_backing = {
        row["audit_item"]: row
        for row in _rows("ratewall_assumption_source_backing_invariant_audit.csv")
    }
    for audit_item in {
        "policy_path_source_bundle_field_exhaustion_decision_fail_closed",
        "policy_path_source_bundle_component_exhaustion_decision_fail_closed",
    }:
        assert source_backing[audit_item]["audit_status"] == "pass"
