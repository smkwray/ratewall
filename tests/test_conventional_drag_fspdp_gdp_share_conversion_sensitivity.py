from __future__ import annotations

import pytest
import csv
from decimal import Decimal
from pathlib import Path

from ratewall.databook.conventional_drag_fspdp_controlled_lp import _format_float
from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
METHOD_ARTIFACT = (
    "ratewall_conventional_drag_fspdp_gdp_share_conversion_method_admission.csv"
)
SENSITIVITY_ARTIFACT = (
    "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv"
)
LP_SAMPLE_JOIN_ARTIFACT = (
    "ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv"
)


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sensitivity_rows() -> list[dict[str, str]]:
    return _rows(SENSITIVITY_ARTIFACT)


def test_conversion_method_admission_is_sensitivity_only() -> None:
    rows = _rows(METHOD_ARTIFACT)
    assert {
        row["conversion_method_admission_row_id"] for row in rows
    } == {"conventional_drag_fspdp_gdp_share_conversion_method_admission::0001"}
    row = rows[0]

    assert row["conversion_convention_id"] == (
        "log_exact_nominal_share_scaled_real_fspdp_quantity_drag_v1"
    )
    assert row["conversion_convention_status"] == (
        "pass_admitted_for_noncanonical_sensitivity_only"
    )
    assert row["primary_share_window_id"] == "lp_sample_base_quarter_mean"
    assert row["lp_sample_base_share_status"] == (
        "pass_lp_sample_base_quarter_share_join_materialized"
    )
    assert row["uncertainty_propagation_status"] == (
        "pass_pointwise_lp_ci_conditional_on_fixed_share_convention"
    )
    assert row["promotion_rule_status"] == (
        "blocked_no_denominator_promotion_rule_pass"
    )
    assert row["admission_status"] == "admitted_noncanonical_sensitivity_not_d_y"
    assert row["linked_lp_sample_base_share_join_artifact"] == LP_SAMPLE_JOIN_ARTIFACT
    assert row["enters_main_ratio"] == "false"
    assert row["evidence_mode_enabled"] == "false"
    assert row["canonical_ratio_entry"] == "false"
    for field in FORBIDDEN_SWITCH_FIELDS:
        assert row[field] == "false"


def test_conversion_sensitivity_row_grain_links_and_roles() -> None:
    rows = _sensitivity_rows()
    horizons = {"4", "8"}
    share_windows = {
        "lp_sample_base_quarter_mean",
        "baseline_1994q1_2019q4",
        "full_available_panel",
        "latest_12q_available",
    }
    assert {(row["horizon_q"], row["share_window_id"]) for row in rows} == {
        (horizon, share_window)
        for horizon in horizons
        for share_window in share_windows
    }
    assert len({row["fspdp_gdp_share_conversion_sensitivity_row_id"] for row in rows}) == len(
        rows
    )
    assert {row["conversion_convention_id"] for row in rows} == {
        "log_exact_nominal_share_scaled_real_fspdp_quantity_drag_v1"
    }
    assert all(
        row["fspdp_gdp_share_conversion_design_gate_row_id"]
        for row in rows
        if row["share_window_id"] != "lp_sample_base_quarter_mean"
    )
    assert all(
        row["linked_lp_sample_base_share_join_artifact"] == LP_SAMPLE_JOIN_ARTIFACT
        for row in rows
        if row["share_window_id"] == "lp_sample_base_quarter_mean"
    )
    assert all(
        row["linked_lp_sample_base_share_join_row_ids"]
        for row in rows
        if row["share_window_id"] == "lp_sample_base_quarter_mean"
    )
    assert all(row["denominator_conversion_uncertainty_boundary_row_id"] for row in rows)
    assert {
        row["linked_gdp_share_conversion_design_gate_artifact"]
        for row in rows
        if row["share_window_id"] != "lp_sample_base_quarter_mean"
    } == {
        "ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv"
    }
    assert {
        row["linked_denominator_conversion_uncertainty_boundary_artifact"]
        for row in rows
    } == {
        "ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv"
    }
    assert {
        row["share_window_role"]
        for row in rows
        if row["share_window_id"] == "lp_sample_base_quarter_mean"
    } == {"primary_lp_sample_base_quarter_mean_sensitivity_center"}
    assert {
        row["share_window_role"]
        for row in rows
        if row["share_window_id"] == "baseline_1994q1_2019q4"
    } == {"baseline_fallback_modern_prepandemic_sensitivity"}


def test_conversion_sensitivity_uses_log_exact_formula() -> None:
    rows = {
        (row["horizon_q"], row["share_window_id"]): row
        for row in _sensitivity_rows()
    }
    h4 = rows[("4", "lp_sample_base_quarter_mean")]
    h8 = rows[("8", "lp_sample_base_quarter_mean")]

    assert Decimal(h4["share_scalar"]) == Decimal("0.84098657287")
    assert Decimal(h8["share_scalar"]) == Decimal("0.84098657287")

    assert Decimal(h4["positive_drag_gdp_share_per_100bp_year"]) == Decimal(
        "-0.030484423878"
    )
    assert Decimal(h4["positive_drag_pp_gdp_per_100bp_year"]) == Decimal(
        "-3.048442387788"
    )
    assert Decimal(h4["candidate_ci_lower"]) == Decimal("-0.101647268194")
    assert Decimal(h4["candidate_ci_upper"]) == Decimal("0.035306079484")

    assert Decimal(h8["positive_drag_gdp_share_per_100bp_year"]) == Decimal(
        "0.048191248237"
    )
    assert Decimal(h8["positive_drag_pp_gdp_per_100bp_year"]) == Decimal(
        "4.819124823732"
    )
    assert Decimal(h8["candidate_ci_lower"]) == Decimal("0.000689334128")
    assert Decimal(h8["candidate_ci_upper"]) == Decimal("0.093007884134")


def test_conversion_sensitivity_float_formatter_is_stable_for_edge_values() -> None:
    assert _format_float(None) == ""
    assert _format_float(1e-7) == "0.0000001"
    assert _format_float(1e-9) == "0"
    assert _format_float(0.30000000000000004) == "0.3"
    assert _format_float(-3.048442387788) == "-3.04844239"


def test_conversion_sensitivity_p_values_are_horizon_not_window_specific() -> None:
    rows = _sensitivity_rows()
    p_values_by_horizon: dict[str, set[str]] = {}
    for row in rows:
        p_values_by_horizon.setdefault(row["horizon_q"], set()).add(
            row["candidate_p_value_pointwise"]
        )
        assert row["uncertainty_interpretation"] == (
            "pointwise_lp_ci_conditional_on_fixed_share_convention"
        )
    assert p_values_by_horizon == {
        "4": {"0.373954085499"},
        "8": {"0.046853744352"},
    }


def test_conversion_sensitivity_preserves_no_promotion_switches() -> None:
    for row in _sensitivity_rows():
        assert row["sensitivity_status"] == "admitted_noncanonical_sensitivity_not_d_y"
        assert row["promotion_rule_status"] == "blocked_no_denominator_promotion_rule_pass"
        assert row["admitted_d_y"] == ""
        assert row["admitted_bps_year_exposure_output"] == ""
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        assert row["canonical_ratio_entry"] == "false"
        assert row["denominator_prior_update_allowed"] == "false"
        assert "D_Y" in row["blocked_use"]
        assert "not_nominal_gdp_estimate" in row["claim_boundary"]
        for field in FORBIDDEN_SWITCH_FIELDS:
            assert row[field] == "false"


def test_conversion_sensitivity_ledger_active_output_and_invariant() -> None:
    ledger_rows = [
        row
        for row in _rows("ratewall_assumption_source_backing_ledger.csv")
        if row["artifact_or_surface"] == SENSITIVITY_ARTIFACT
    ]
    assert len(ledger_rows) == len(_sensitivity_rows())
    assert {row["assumption_family"] for row in ledger_rows} == {
        "conventional_drag_fspdp_gdp_share_conversion_sensitivity"
    }
    assert {row["source_backing_class"] for row in ledger_rows} == {
        "blocked_or_diagnostic_only"
    }
    assert {row["source_backing_subclass"] for row in ledger_rows} == {
        "local_lp_diagnostic_not_calibration"
    }
    assert {row["enters_canonical_ratio"] for row in ledger_rows} == {"false"}

    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    assert active[SENSITIVITY_ARTIFACT]["source_status"] == (
        "admitted_noncanonical_fspdp_gdp_share_conversion_sensitivity_indexed"
    )
    assert active[SENSITIVITY_ARTIFACT]["canonical_ratio_entry"] == "false"

    backend = {
        row["audit_item"]: row
        for row in _rows("ratewall_backend_invariant_guardrail_audit.csv")
    }
    assert backend[
        "conventional_drag_fspdp_gdp_share_conversion_sensitivity_no_promotion"
    ]["audit_status"] == "pass"
