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


def test_historical_tdc_admission_exposes_finer_source_gates() -> None:
    rows = _rows("ratewall_historical_tdc_path_admission.csv")

    _assert_fail_closed(rows)

    assert {row["selected_series_gate_status"] for row in rows} == {
        "blocked_selected_series_contract_zero_quarters"
    }
    assert {row["historical_panel_gate_status"] for row in rows} == {
        "context_only_panel_coverage_limited_missing_exact_du_ru_split",
        "context_only_partial_source_backed_proxy",
    }
    assert {
        row["historical_tdc_reduced_form_source_gate_status"] for row in rows
    } == {
        "comparison_only_reduced_form_source_gate_passed",
        "blocked_missing_historical_tdc_sidecar_for_quarter",
    }
    assert {row["historical_tdc_overlap_gate_status"] for row in rows} == {
        "pass_overlap_identity_proved_for_historical_tdc",
        "blocked_missing_historical_tdc_sidecar_for_quarter",
    }
    assert {
        row["historical_tdc_source_hardening_status"] for row in rows
    } == {
        "comparison_only_selected_series_empty_panel_context_limited",
        "blocked_missing_reduced_form_sidecar_for_quarter",
    }


def test_historical_tdc_source_hardening_audit_summarizes_blockers() -> None:
    rows = _rows("ratewall_historical_tdc_source_hardening_audit.csv")

    _assert_fail_closed(rows)

    by_family = {row["evidence_family"]: row for row in rows}
    assert set(by_family) == {
        "selected_series_contract",
        "historical_source_contract",
        "historical_reconciliation",
        "historical_panel_context",
        "tdc_source_coverage",
        "quarter_level_admission_summary",
    }

    assert by_family["selected_series_contract"]["selected_series_status"] == (
        "selected_from_tdcest_contract"
    )
    assert by_family["selected_series_contract"]["selected_series_quarter_count"] == "0"
    assert by_family["historical_source_contract"]["default_eligible_row_count"] == "1"
    assert by_family["historical_reconciliation"]["pass_row_count"] == "7"
    assert by_family["historical_reconciliation"]["blocked_row_count"] == "1"
    assert by_family["tdc_source_coverage"]["pass_row_count"] == "12"
    assert by_family["tdc_source_coverage"]["context_only_row_count"] == "1"
    assert by_family["tdc_source_coverage"]["blocked_row_count"] == "1"
    assert by_family["quarter_level_admission_summary"][
        "comparison_only_quarter_count"
    ] == "0"
    assert by_family["quarter_level_admission_summary"][
        "missing_sidecar_quarter_count"
    ] == "2"
    assert by_family["quarter_level_admission_summary"][
        "headline_blocked_quarter_count"
    ] == "19"
