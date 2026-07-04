from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest

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


def test_selected_series_bridge_alignment_stays_blocked_and_quarter_aware() -> None:
    rows = _rows("ratewall_historical_tdc_selected_series_bridge_alignment.csv")

    _assert_fail_closed(rows)

    assert len(rows) == 19
    assert {row["selected_series_bridge_status"] for row in rows} == {
        "blocked_selected_series_key_absent_from_estimator_bridge"
    }
    assert {
        row["bridge_alignment_status"] for row in rows
    } == {
        "blocked_selected_series_bridge_alignment_missing_but_fallback_available",
        "blocked_no_bridge_alignment_or_fallback_for_quarter",
    }
    assert all(
        row["next_bridge_alignment_action"]
        == "bridge_selected_series_contract_key_to_estimator_bridge"
        for row in rows
    )


def test_historical_tdc_admission_feasibility_summary_distinguishes_bridge_failure() -> None:
    rows = _rows("ratewall_historical_tdc_admission_feasibility_summary.csv")

    _assert_fail_closed(rows)

    assert len(rows) == 19
    assert {row["primary_blocker_family"] for row in rows} == {
        "selected_series_bridge_failure"
    }
    assert {row["admission_feasibility_status"] for row in rows} == {
        "blocked_selected_series_bridge_then_panel_overlap"
    }
    assert Counter(row["secondary_blocker_families"] for row in rows) == {
        "panel_gap": 17,
        "panel_gap;overlap_gap": 2,
    }


def test_source_backed_companion_candidate_registry_stays_fail_closed() -> None:
    rows = _rows("ratewall_historical_tdc_source_backed_companion_candidate.csv")

    _assert_fail_closed(rows)

    assert len(rows) == 19
    assert {row["companion_candidate_status"] for row in rows} == {
        "blocked_nonheadline_source_backed_historical_tdc_candidate"
    }
    assert all(row["companion_candidate_numerator_bil"] == "" for row in rows)
    assert all(row["companion_candidate_ratio_reference"] == "" for row in rows)
