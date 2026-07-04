from __future__ import annotations

import pytest
import csv
from collections import Counter
from pathlib import Path

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS




pytestmark = pytest.mark.full_surface

OUTPUTS = Path("outputs/tables")
ARTIFACT = "ratewall_final_recipient_current_demand_bridge_attempt.csv"
QUEUE_ARTIFACT = "ratewall_bank_behavior_bridge_source_contract_queue.csv"
RANK1_PATH_ARTIFACT = "ratewall_bank_behavior_rank1_source_contract_path.csv"
TREASURY_PATH_ARTIFACT = "ratewall_treasury_recipient_source_contract_path.csv"
TREASURY_PROXY_SCAFFOLD_ARTIFACT = (
    "ratewall_treasury_recipient_current_demand_proxy_scaffold.csv"
)
BLOCKED_STATUS = (
    "blocked_no_admissible_source_backed_final_recipient_current_demand_bridge"
)


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def test_final_recipient_current_demand_bridge_attempt_materializes_fail_closed_scan() -> None:
    rows = _rows(ARTIFACT)

    _assert_fail_closed(rows)
    assert len(rows) == 11
    assert Counter(row["attempt_family"] for row in rows) == {
        "treasury_final_recipient_current_demand": 7,
        "bank_retained_margin_current_demand": 4,
    }
    assert {row["bridge_materialization_status"] for row in rows} == {BLOCKED_STATUS}
    assert {row["source_status"] for row in rows} == {
        "source_scan_completed_context_available_bridge_not_admitted"
    }
    assert all(row["missing_source_backed_fields"] for row in rows)
    assert all(row["exact_next_required_field_set"] for row in rows)
    assert all(
        "runtime_default;canonical_rw_y" in row["blocked_use"] for row in rows
    )


def test_final_recipient_current_demand_bridge_attempt_records_source_scan_counts() -> None:
    by_family = {
        row["source_or_gate_family"]: row for row in _rows(ARTIFACT)
    }

    z1 = by_family["domestic_private_holder_context"]
    assert z1["candidate_source_row_count"] == "4228"
    assert "z1_rows=4228" in z1["source_scan_result"]
    assert "current_demand_eligible_rows=0" in z1["source_scan_result"]
    assert "unknown_or_mixed_m2_rows=906" in z1["source_scan_result"]

    mmf = by_family["mmf_portfolio_and_repo_context"]
    assert mmf["candidate_source_row_count"] == "2355"
    assert "mmf_rows=136" in mmf["source_scan_result"]
    assert "mmf_current_demand_eligible_rows=0" in mmf["source_scan_result"]
    assert "mmf_m2_true_rows=14" in mmf["source_scan_result"]
    assert "monetary_route_rows=2219" in mmf["source_scan_result"]

    tdcsim = by_family["tdcsim_funding_route_contract_gap"]
    assert tdcsim["candidate_source_row_count"] == "8"
    assert "tdcsim_classification_rows=8" in tdcsim["source_scan_result"]
    assert "route_contract_present_rows=3" in tdcsim["source_scan_result"]
    assert "binding_blocker_rows=7" in tdcsim["source_scan_result"]
    assert "tdcest_route_context_latest_quarter=2025Q4" in tdcsim[
        "source_scan_result"
    ]
    assert "tdcest_route_context_rows=6583" in tdcsim["source_scan_result"]
    assert "source_backed_private_bucket_split_rows=0" in tdcsim[
        "source_scan_result"
    ]
    assert "route_context_target_rows=3" in tdcsim["source_scan_result"]

    bank_cashflow = by_family["gross_iorb_cashflow_basis"]
    assert bank_cashflow["candidate_source_row_count"] == "99"
    assert "deposit_pricing_source_backed_rows=21" in bank_cashflow[
        "source_scan_result"
    ]
    assert "rolling_pass_through_rows=59" in bank_cashflow["source_scan_result"]

    bank_intermediation = by_family["bank_intermediation_context"]
    assert bank_intermediation["candidate_source_row_count"] == "163"
    assert "bank_nim_context_rows=1" in bank_intermediation["source_scan_result"]
    assert "bank_loan_repricing_context_rows=1" in bank_intermediation[
        "source_scan_result"
    ]
    assert "tdcpass_borrower_channel_rows=143" in bank_intermediation[
        "source_scan_result"
    ]
    assert "tdcpass_latest_quarter=2025Q4" in bank_intermediation[
        "source_scan_result"
    ]
    assert "fdic_aggregate_retention_route_rows=18" in bank_intermediation[
        "source_scan_result"
    ]
    assert "fdic_latest_quarter=2026Q1" in bank_intermediation[
        "source_scan_result"
    ]

    bank_gate = by_family["bank_behavior_current_demand_gate"]
    assert bank_gate["candidate_source_row_count"] == "262"
    assert "tdcpass_borrower_channel_rows=143" in bank_gate[
        "source_scan_result"
    ]
    assert "fdic_aggregate_retention_route_rows=18" in bank_gate["source_scan_result"]
    assert "source_backed_iorb_specific_retention_distribution_timing_rows=0" in (
        bank_gate["source_scan_result"]
    )


def test_final_recipient_current_demand_bridge_attempt_is_active_output_indexed() -> None:
    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    assert ARTIFACT in active
    assert active[ARTIFACT]["active_status"] == "blocked_source_backed_context"
    assert active[ARTIFACT]["canonical_ratio_entry"] == "false"
    assert "canonical_rw_y" in active[ARTIFACT]["blocked_use"]


def test_bank_behavior_bridge_source_contract_queue_ranks_missing_source_contracts() -> None:
    rows = _rows(QUEUE_ARTIFACT)

    _assert_fail_closed(rows)
    assert len(rows) == 4
    assert [row["queue_rank"] for row in rows] == ["1", "2", "3", "4"]
    by_family = {row["source_or_gate_family"]: row for row in rows}
    assert set(by_family) == {
        "bank_behavior_current_demand_gate",
        "bank_intermediation_context",
        "reserve_income_and_deposit_pricing_context",
        "gross_iorb_cashflow_basis",
    }

    gate = by_family["bank_behavior_current_demand_gate"]
    assert gate["source_contract_focus"] == (
        "iorb_specific_retention_distribution_timing_and_nonadditivity_panel"
    )
    assert gate["candidate_source_row_count"] == "262"
    assert "source_backed_iorb_specific_retention_distribution_timing_rows=0" in (
        gate["source_scan_result"]
    )
    assert "retention_deposit_pass_through" in gate["required_new_source_contract"]
    assert gate["blocking_status"] == (
        "blocked_bank_behavior_source_contract_missing_required_fields"
    )
    assert gate["promotion_decision_status"] == (
        "blocked_no_bank_current_demand_or_denominator_promotion"
    )
    assert gate["allowed_use"] == "bank_behavior_source_contract_queue_only"
    assert gate["claim_boundary"] == (
        "bank_behavior_bridge_source_contract_queue_not_admission"
    )
    assert gate["canonical_ratio_entry"] == "false"
    assert "canonical_rw_y" in gate["blocked_use"]

    intermediation = by_family["bank_intermediation_context"]
    assert intermediation["candidate_source_row_count"] == "163"
    assert "tdcpass_borrower_channel_rows=143" in intermediation[
        "source_scan_result"
    ]
    assert "fdic_aggregate_retention_route_rows=18" in intermediation[
        "source_scan_result"
    ]
    assert "fdic_latest_quarter=2026Q1" in intermediation["source_scan_result"]


def test_bank_behavior_bridge_source_contract_queue_is_active_output_indexed() -> None:
    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    assert QUEUE_ARTIFACT in active
    assert active[QUEUE_ARTIFACT]["active_status"] == "blocked_source_contract_queue"
    assert active[QUEUE_ARTIFACT]["denominator_family"] == (
        "not_applicable_source_contract_queue"
    )
    assert active[QUEUE_ARTIFACT]["denominator_status"] == (
        "bank_behavior_bridge_source_contract_queue_fail_closed"
    )
    assert active[QUEUE_ARTIFACT]["source_status"] == (
        "blocked_source_contract_queue_indexed"
    )
    assert active[QUEUE_ARTIFACT]["canonical_ratio_entry"] == "false"
    assert "canonical_rw_y" in active[QUEUE_ARTIFACT]["blocked_use"]


def test_bank_behavior_rank1_source_contract_path_separates_context_from_reopen_trigger() -> None:
    rows = _rows(RANK1_PATH_ARTIFACT)

    _assert_fail_closed(rows)
    assert len(rows) == 4
    assert [row["path_rank"] for row in rows] == ["1", "2", "3", "4"]
    by_path = {row["path_id"]: row for row in rows}

    local = by_path["local_public_context_exhaustion_check"]
    assert local["linked_queue_row_id"] == (
        "bank_behavior_bridge_source_contract_queue::01"
    )
    assert local["local_context_row_count"] == "262"
    assert "source_backed_iorb_specific_retention_distribution_timing_rows=0" in (
        local["local_available_context"]
    )
    assert local["admission_status"] == (
        "blocked_current_local_context_not_rank1_contract"
    )
    assert local["source_status"] == "local_context_exhausted_rank1_contract_missing"
    assert local["canonical_ratio_entry"] == "false"

    fdic = by_path["public_fdic_bank_financials_extension"]
    assert fdic["local_context_row_count"] == "18"
    assert "not_iorb_specific" in fdic["current_source_gap"]
    assert fdic["admission_status"] == (
        "blocked_public_aggregate_context_not_rank1_contract"
    )

    tdcpass = by_path["tdcpass_borrower_channel_extension"]
    assert tdcpass["local_context_row_count"] == "143"
    assert "aggregate borrower-channel context" in tdcpass["why_not_admitted_now"]
    assert tdcpass["admission_status"] == "blocked_borrower_context_not_rank1_contract"

    trigger = by_path["source_owned_iorb_depositor_timing_panel"]
    assert trigger["local_context_row_count"] == "0"
    assert trigger["path_role"] == "true_reopen_trigger"
    assert trigger["admission_status"] == "candidate_reopen_trigger_only_no_data_present"
    assert trigger["reopen_trigger"] == (
        "source_owned_rank1_panel_present_with_all_required_fields_and_"
        "nonadditivity_audit_passed"
    )
    assert "retention_deposit_pass_through" in trigger[
        "required_new_source_contract"
    ]


def test_bank_behavior_rank1_source_contract_path_is_active_output_indexed() -> None:
    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    assert RANK1_PATH_ARTIFACT in active
    assert active[RANK1_PATH_ARTIFACT]["active_status"] == (
        "blocked_source_contract_path"
    )
    assert active[RANK1_PATH_ARTIFACT]["source_status"] == (
        "blocked_source_contract_path_indexed"
    )
    assert active[RANK1_PATH_ARTIFACT]["canonical_ratio_entry"] == "false"
    assert "canonical_rw_y" in active[RANK1_PATH_ARTIFACT]["blocked_use"]


def test_treasury_recipient_source_contract_path_separates_context_from_reopen_trigger() -> None:
    rows = _rows(TREASURY_PATH_ARTIFACT)

    _assert_fail_closed(rows)
    assert len(rows) == 6
    assert [row["path_rank"] for row in rows] == ["1", "2", "3", "4", "5", "6"]
    by_path = {row["path_id"]: row for row in rows}

    local = by_path["local_public_context_exhaustion_check"]
    assert local["linked_bridge_attempt_row_id"] == (
        "final_recipient_current_demand_bridge_attempt::treasury::01"
    )
    assert local["local_context_row_count"] == "6"
    assert "final_owner_mapping_ready_rows=0" in local["local_available_context"]
    assert local["admission_status"] == (
        "blocked_current_local_context_not_recipient_contract"
    )
    assert local["source_status"] == (
        "local_context_exhausted_treasury_recipient_contract_missing"
    )

    z1 = by_path["z1_domestic_holder_context_extension"]
    assert z1["local_context_row_count"] == "4228"
    assert "current_demand_eligible_rows=0" in z1["local_available_context"]
    assert "unknown_or_mixed_m2_rows=906" in z1["local_available_context"]
    assert z1["admission_status"] == (
        "blocked_public_holder_context_not_recipient_contract"
    )

    mmf = by_path["mmf_route_context_extension"]
    assert mmf["local_context_row_count"] == "2355"
    assert "mmf_m2_true_rows=14" in mmf["local_available_context"]
    assert "monetary_route_current_demand_eligible_rows=0" in (
        mmf["local_available_context"]
    )
    assert mmf["admission_status"] == (
        "blocked_intermediation_context_not_recipient_contract"
    )

    foreign = by_path["tic_foreign_leakage_context_extension"]
    assert foreign["local_context_row_count"] == "12"
    assert "foreign_recycling_rows_blocked_pending_beneficial_owner_timing=1" in (
        foreign["local_available_context"]
    )

    tdcsim = by_path["tdcsim_route_contract_extension"]
    assert tdcsim["local_context_row_count"] == "8"
    assert "source_backed_private_bucket_split_rows=0" in (
        tdcsim["local_available_context"]
    )
    assert "forecast_component_mapping" in tdcsim["required_schema_fields"]

    trigger = by_path["source_owned_treasury_recipient_current_demand_panel"]
    assert trigger["path_role"] == "true_reopen_trigger"
    assert trigger["local_context_row_count"] == "0"
    assert trigger["admission_status"] == (
        "candidate_reopen_trigger_only_no_data_present"
    )
    assert "current_demand_share" in trigger["required_schema_fields"]
    assert "nonadditivity_check" in trigger["required_schema_fields"]
    assert trigger["canonical_ratio_entry"] == "false"


def test_treasury_recipient_source_contract_path_is_active_output_indexed() -> None:
    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    assert TREASURY_PATH_ARTIFACT in active
    assert active[TREASURY_PATH_ARTIFACT]["active_status"] == (
        "blocked_source_contract_path"
    )
    assert active[TREASURY_PATH_ARTIFACT]["denominator_family"] == (
        "not_applicable_source_contract_path"
    )
    assert active[TREASURY_PATH_ARTIFACT]["denominator_status"] == (
        "treasury_recipient_source_contract_path_fail_closed"
    )
    assert active[TREASURY_PATH_ARTIFACT]["source_status"] == (
        "blocked_source_contract_path_indexed"
    )
    assert active[TREASURY_PATH_ARTIFACT]["canonical_ratio_entry"] == "false"
    assert "canonical_rw_y" in active[TREASURY_PATH_ARTIFACT]["blocked_use"]


def test_treasury_recipient_proxy_scaffold_records_external_review_route_design() -> None:
    rows = _rows(TREASURY_PROXY_SCAFFOLD_ARTIFACT)

    _assert_fail_closed(rows)
    assert len(rows) == 10
    assert [row["proxy_route_rank"] for row in rows] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
    ]
    assert {row["scaffold_status"] for row in rows} == {
        "proxy_scaffold_created_not_panel_materialized"
    }
    assert {row["admission_status"] for row in rows} == {
        "proxy_scaffold_created_not_admitted_current_demand_fields_pending"
    }
    assert all(
        row["linked_source_contract_path_row_id"]
        == "treasury_recipient_source_contract_path::06"
        for row in rows
    )

    by_route = {row["recipient_route"]: row for row in rows}
    assert set(by_route) == {
        "foreign_official_private_leakage",
        "federal_reserve_or_intragovernmental_internal",
        "direct_household_treasurydirect_or_brokerage",
        "household_via_mmf_or_deposit_like_fund",
        "household_via_mutual_fund_etf",
        "pension_insurance_retained_or_imputed",
        "depository_and_financial_business_retained",
        "nonfinancial_business",
        "state_local_government",
        "unclassified_residual",
    }

    direct = by_route["direct_household_treasurydirect_or_brokerage"]
    assert "scf" in direct["candidate_public_sources"]
    assert "consumer_expenditure" in direct["candidate_public_sources"]
    assert "published_mpc_estimates" in direct["candidate_public_sources"]
    assert "current_window_mpc" in direct["proxy_formula_or_rule"]
    assert "observed_treasury_interest_deposit_to_spending_link" in (
        direct["required_row6_fields_missing"]
    )

    mmf = by_route["household_via_mmf_or_deposit_like_fund"]
    assert "sec_n_mfp" in mmf["candidate_public_sources"]
    assert "fund_intermediary_rows_replace_not_stack" in (
        mmf["nonadditivity_check_design"]
    )

    foreign = by_route["foreign_official_private_leakage"]
    assert "tic_foreign_holder_data" in foreign["candidate_public_sources"]
    assert foreign["current_demand_share_status"] == (
        "domestic_current_demand_share_zero_unless_recycling_source_backed"
    )

    residual = by_route["unclassified_residual"]
    assert residual["proxy_formula_or_rule"] == (
        "current_demand_share=0_until_residual_is_classified_by_source"
    )
    assert "period;period_type;recipient_route" in residual["expected_output_schema"]
    assert "validation_check" in residual["expected_output_schema"]
    assert "nonadditivity_check" in residual["expected_output_schema"]


def test_treasury_recipient_proxy_scaffold_is_active_output_indexed() -> None:
    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    assert TREASURY_PROXY_SCAFFOLD_ARTIFACT in active
    assert active[TREASURY_PROXY_SCAFFOLD_ARTIFACT]["active_status"] == (
        "proxy_scaffold_not_admitted"
    )
    assert active[TREASURY_PROXY_SCAFFOLD_ARTIFACT]["denominator_family"] == (
        "not_applicable_proxy_scaffold"
    )
    assert active[TREASURY_PROXY_SCAFFOLD_ARTIFACT]["denominator_status"] == (
        "treasury_recipient_current_demand_proxy_scaffold_fail_closed"
    )
    assert active[TREASURY_PROXY_SCAFFOLD_ARTIFACT]["source_status"] == (
        "proxy_scaffold_created_not_admitted_indexed"
    )
    assert active[TREASURY_PROXY_SCAFFOLD_ARTIFACT]["canonical_ratio_entry"] == (
        "false"
    )
    assert "canonical_rw_y" in active[TREASURY_PROXY_SCAFFOLD_ARTIFACT][
        "blocked_use"
    ]
