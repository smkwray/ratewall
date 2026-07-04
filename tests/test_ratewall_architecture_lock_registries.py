from __future__ import annotations

import pytest
import csv
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import FORBIDDEN_SWITCH_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")

ARCHITECTURE_TABLES = {
    "ratewall_ratio_layer_registry.csv",
    "ratewall_estimation_target_registry.csv",
    "ratewall_channel_taxonomy_registry.csv",
    "ratewall_historical_interpretation_audit.csv",
    "ratewall_tdc_equation_variant_registry.csv",
    "ratewall_policy_path_source_extraction_task_packet.csv",
}

ARCHITECTURE_FAMILIES = {
    "ratio_layer_registry",
    "estimation_target_registry",
    "channel_taxonomy_registry",
    "historical_interpretation_audit",
    "tdc_equation_variant_registry",
    "policy_path_source_extraction_task_packet",
}


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUT_TABLES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        assert row["denominator_prior_update_allowed"] == "false"
        assert row["prior_narrowing_allowed"] == "false"
        assert row["formula_replacement_allowed"] == "false"
        assert row["split_denominator_promotion_allowed"] == "false"
        for field in FORBIDDEN_SWITCH_FIELDS:
            assert row[field] == "false"


def test_ratio_layer_registry_separates_rw_y_from_design_only_rw_pi() -> None:
    rows = _rows("ratewall_ratio_layer_registry.csv")
    _assert_fail_closed(rows)

    by_ratio = {row["ratio_id"]: row for row in rows}
    assert {"RW_Y", "RW_pi", "RW_Y_actual_rate_sidecar"} <= set(by_ratio)

    assert by_ratio["RW_Y"]["canonical_status"] == "canonical_assumption_mode_annual_flow"
    assert by_ratio["RW_Y"]["denominator_basis"] == "canonical_100bp_year"
    assert by_ratio["RW_Y"]["exact_blocker"] == ""
    assert by_ratio["RW_pi"]["canonical_status"] == "design_only_blocked"
    assert by_ratio["RW_pi"]["design_only"] == "true"
    assert by_ratio["RW_pi"]["enters_main_ratio"] == "false"
    assert by_ratio["RW_Y_actual_rate_sidecar"]["canonical_status"] == (
        "sidecar_diagnostic"
    )
    assert by_ratio["RW_Y_actual_rate_sidecar"]["denominator_basis"] == (
        "actual_rate_level_sidecar"
    )


def test_channel_taxonomy_keeps_price_channels_out_of_rw_y_numerator() -> None:
    rows = _rows("ratewall_channel_taxonomy_registry.csv")
    _assert_fail_closed(rows)

    price_tokens = {
        "working capital",
        "working-capital",
        "working_capital",
        "carry",
        "wacc",
        "shelter",
        "dealer inventory",
        "dealer_inventory",
        "inventory carry",
    }
    price_rows = [
        row
        for row in rows
        if any(
            token
            in " ".join(
                [
                    row["channel_id"],
                    row["source_channel_label"],
                    row["channel_role"],
                ]
            ).lower()
            for token in price_tokens
        )
    ]
    assert price_rows
    assert {row["enters_rw_y_numerator"] for row in price_rows} == {"false"}
    assert {row["enters_main_ratio"] for row in price_rows} == {"false"}
    assert {
        row["ratio_layer"]
        for row in price_rows
        if row["channel_id"] != "consumer_credit_fast_repricing_drag"
    } == {"inflation_wall"}


def test_historical_interpretation_audit_blocks_actual_rate_and_covid_claims() -> None:
    rows = _rows("ratewall_historical_interpretation_audit.csv")
    _assert_fail_closed(rows)

    actual_rate_rows = [
        row for row in rows if row["denominator_basis"] == "actual_rate_level_sidecar"
    ]
    assert actual_rate_rows
    assert not [
        row
        for row in actual_rate_rows
        if row["canonical_status"] == "canonical"
        or row["value_admission_status"] == "admitted_empirical"
        or row["enters_main_paper_claim"] == "true"
    ]

    covid_or_near_zero_rows = [
        row
        for row in rows
        if row["covid_liquidity_regime_flag"] == "true"
        or row["near_zero_denominator_flag"] == "true"
    ]
    assert covid_or_near_zero_rows
    assert not [
        row for row in covid_or_near_zero_rows if row["canonical_status"] == "canonical"
    ]


def test_tdc_equation_variant_registry_is_replace_not_stack_and_blocked() -> None:
    rows = _rows("ratewall_tdc_equation_variant_registry.csv")
    _assert_fail_closed(rows)

    assert len(rows) == 5
    assert {row["replace_vs_stack_semantics"] for row in rows} == {"replace_not_stack"}
    assert {row["allowed_for_rw_y"] for row in rows} == {"false"}
    assert {row["allowed_for_rw_pi"] for row in rows} == {"false"}
    assert {row["admission_status"] for row in rows} <= {
        "blocked_missing_current_demand_conversion",
        "blocked_missing_overlap_rule",
        "blocked_tdc_equation_variant_not_rw_y_input",
        "forbidden_double_count_without_replace_not_stack_rule",
        "diagnostic_only",
        "pass_central_tdc_object_family_assumption_mode_not_rw_y",
    }
    core_rows = [
        row for row in rows if row["tdc_variant_id"] == "ru_flow_tier2_tdc_core_object"
    ]
    assert len(core_rows) == 1
    core_row = core_rows[0]
    assert core_row["admission_status"] == (
        "pass_central_tdc_object_family_assumption_mode_not_rw_y"
    )
    assert core_row["exact_blocker"] == ""
    assert core_row["current_demand_conversion_status"] == (
        "not_an_inclusion_gate_sensitivity_or_interpretation_only"
    )
    assert core_row["iorb_rrp_mmf_treatment"] == (
        "route_proxy_sidecar_sensitivity_not_core_tdc_gate"
    )
    assert "ratewall_tdc_deposit_pass_through_source_import.csv" in core_row[
        "source_artifacts"
    ]
    assert "without_broad_du_flow_build" in core_row["next_backend_action"]


def test_policy_path_source_extraction_task_packet_preserves_queue_classes() -> None:
    queue_rows = _rows("ratewall_policy_path_field_evidence_resolution_queue.csv")
    packet_rows = _rows("ratewall_policy_path_source_extraction_task_packet.csv")
    _assert_fail_closed(packet_rows)

    assert len(queue_rows) == 39
    assert len(packet_rows) == len(queue_rows)

    by_class: dict[str, list[dict[str, str]]] = {}
    for row in packet_rows:
        by_class.setdefault(row["field_resolution_class"], []).append(row)
        assert row["candidate_rate_change_bps"] == ""
        assert row["candidate_bps_year_exposure"] == ""
        assert row["candidate_gdp_share_drag_per_100bp_year"] == ""

    assert len(by_class["deeper_source_extraction_required"]) == 23
    assert {
        row["task_class"] for row in by_class["deeper_source_extraction_required"]
    } == {"source_extraction_task"}
    assert len(by_class["independent_replication_target_design_required"]) == 5
    assert {
        row["task_class"]
        for row in by_class["independent_replication_target_design_required"]
    } == {"blocked_non_extraction_design_task"}
    assert len(by_class["explicit_authored_invariant_required"]) == 11
    assert {
        row["task_class"] for row in by_class["explicit_authored_invariant_required"]
    } == {"blocked_authored_invariant_task"}


def test_architecture_lock_ledger_and_audit_invariants() -> None:
    ledger_rows = [
        row
        for row in _rows("ratewall_assumption_source_backing_ledger.csv")
        if row["assumption_family"] in ARCHITECTURE_FAMILIES
    ]
    assert ledger_rows
    assert {row["source_backing_class"] for row in ledger_rows} == {
        "blocked_or_diagnostic_only"
    }
    assert {row["enters_canonical_ratio"] for row in ledger_rows} == {"false"}
    assert {row["prior_narrowing_allowed"] for row in ledger_rows} == {"false"}
    assert {row["formula_replacement_allowed"] for row in ledger_rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in ledger_rows} == {
        "false"
    }

    source_backing = {
        row["audit_item"]: row
        for row in _rows("ratewall_assumption_source_backing_invariant_audit.csv")
    }
    for family in ARCHITECTURE_FAMILIES:
        assert source_backing[f"{family}_fail_closed"]["audit_status"] == "pass"

    backend = {
        row["audit_item"]: row
        for row in _rows("ratewall_backend_invariant_guardrail_audit.csv")
    }
    for audit_item in {
        "backend_expansion_context_surfaces_nonpromotional",
        "context_surface_no_main_ratio_audit_complete",
    }:
        assert backend[audit_item]["audit_status"] == "pass"
