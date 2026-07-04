from __future__ import annotations

import pytest
import csv
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUTS = Path("outputs/tables")


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def test_selected_series_bridge_remediation_matrix_maps_available_candidates() -> None:
    rows = _rows("ratewall_historical_tdc_selected_series_bridge_remediation_matrix.csv")

    _assert_fail_closed(rows)

    assert len(rows) == 167
    assert {row["selected_series_exact_match"] for row in rows} == {"false"}
    assert {row["bridge_remediation_status"] for row in rows} == {
        "blocked_selected_series_contract_key_missing_exact_bridge_row"
    }

    rows_2022q1 = [row for row in rows if row["quarter"] == "2022Q1"]
    assert len(rows_2022q1) == 10
    assert rows_2022q1[0]["bridge_candidate_estimator_key"] == (
        "tdc_tier2_component_anchored_bank_only_ru_flow"
    )
    assert rows_2022q1[0]["bridge_candidate_rank_for_quarter"] == "1"
    assert rows_2022q1[0]["bridge_candidate_comparability_class"] == (
        "bank_only_ru_surrogate_candidate"
    )

    rows_2026q1 = [row for row in rows if row["quarter"] == "2026Q1"]
    assert len(rows_2026q1) == 1
    assert rows_2026q1[0]["bridge_candidate_estimator_key"] == ""
    assert rows_2026q1[0]["bridge_candidate_available_for_quarter"] == "false"
    assert rows_2026q1[0]["bridge_remediation_counterfactual_status"] == (
        "counterfactual_no_bridge_candidate_available_for_quarter"
    )


def test_du_ru_sensitive_panel_blocker_registry_isolates_exact_fields() -> None:
    rows = _rows("ratewall_historical_tdc_du_ru_sensitive_panel_blocker_registry.csv")

    _assert_fail_closed(rows)

    assert len(rows) == 40
    assert {row["bridge_only_counterfactual_status"] for row in rows} == {
        "counterfactual_still_blocked_after_bridge_due_to_du_ru_sensitive_panel_field"
    }
    assert {
        row["du_ru_sensitive_blocker_class"] for row in rows
    } == {
        "exact_du_ru_recipient_split_missing",
        "exact_du_security_absorption_missing",
        "foreign_ru_absorption_proxy_missing",
    }

    count_by_quarter: dict[str, int] = {}
    for row in rows:
        count_by_quarter[row["quarter"]] = count_by_quarter.get(row["quarter"], 0) + 1
    assert count_by_quarter["2021Q4"] == 2
    assert count_by_quarter["2026Q1"] == 3


def test_admission_candidate_matrix_stays_fail_closed_under_bridge_counterfactuals() -> None:
    rows = _rows("ratewall_historical_tdc_admission_candidate_matrix.csv")

    _assert_fail_closed(rows)

    assert len(rows) == 19
    assert {row["current_source_backed_companion_status"] for row in rows} == {
        "blocked_nonheadline_source_backed_historical_tdc_candidate"
    }
    assert {row["full_gate_closure_candidate_status"] for row in rows} == {
        "counterfactual_nonheadline_candidate_evaluable_if_bridge_panel_overlap_close"
    }

    by_quarter = {row["quarter"]: row for row in rows}
    assert by_quarter["2021Q4"]["bridge_only_candidate_status"] == (
        "counterfactual_still_blocked_after_bridge_due_to_panel"
    )
    assert by_quarter["2021Q4"]["remaining_blockers_after_bridge_only"] == (
        "exact_du_ru_panel_gap"
    )
    assert by_quarter["2021Q4"]["bridge_plus_du_ru_panel_candidate_status"] == (
        "counterfactual_eligible_if_bridge_and_du_ru_panel_improve"
    )

    assert by_quarter["2026Q1"]["ru_context_blocker_count"] == "1"
    assert by_quarter["2026Q1"]["other_panel_blocker_count"] == "0"
    assert by_quarter["2026Q1"]["bridge_plus_du_ru_panel_candidate_status"] == (
        "counterfactual_still_blocked_after_bridge_and_du_ru_panel_due_to_overlap"
    )
