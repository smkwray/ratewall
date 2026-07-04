import pytest
import csv
from collections import Counter
from pathlib import Path




pytestmark = pytest.mark.full_surface

ARTIFACT = (
    "outputs/tables/"
    "ratewall_conventional_drag_research_extended_source_code_interpretation.csv"
)

FORBIDDEN_SWITCH_FIELDS = [
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]


def _rows(path: str) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_extended_source_code_interpretation_row_grain_and_gap_set() -> None:
    rows = _rows(ARTIFACT)

    assert len(rows) == 24
    assert len({row["extended_source_code_interpretation_row_id"] for row in rows}) == 24
    assert {row["target_outcome_id"] for row in rows} == {"fspdp_gdp_share"}
    assert {row["target_horizon_quarters"] for row in rows} == {"4", "8", "12"}
    assert Counter(row["source_outcome_label"] for row in rows) == {
        "PCES": 3,
        "PRFI": 3,
        "BEA_NIPA_PRIVATE_NONRESIDENTIAL_STRUCTURES": 3,
        "BEA_NIPA_PRIVATE_EQUIPMENT": 3,
        "BEA_NIPA_PRIVATE_IPP": 3,
        "BUSINVx": 3,
        "RPI": 3,
        "LIP": 3,
    }


def test_extended_source_code_interpretation_classifies_fspdp_gaps() -> None:
    rows = _rows(ARTIFACT)
    by_outcome = {row["source_outcome_label"]: row for row in rows}

    assert by_outcome["PCES"]["fspdp_coverage_gap_status"] == (
        "blocked_missing_pce_services_irf_coverage"
    )
    assert by_outcome["PRFI"]["target_contract_blocker_status"] == (
        "blocked_missing_direct_residential_fixed_investment_expenditure_irf"
    )
    for outcome in {
        "BEA_NIPA_PRIVATE_NONRESIDENTIAL_STRUCTURES",
        "BEA_NIPA_PRIVATE_EQUIPMENT",
        "BEA_NIPA_PRIVATE_IPP",
    }:
        assert by_outcome[outcome]["source_outcome_role"] == (
            "required_missing_private_fixed_investment_component"
        )
        assert by_outcome[outcome]["target_contract_blocker_status"] == (
            "blocked_missing_private_fixed_investment_subcomponent_irf"
        )


def test_extended_source_code_interpretation_keeps_context_rows_out_of_fspdp() -> None:
    rows = _rows(ARTIFACT)
    by_outcome = {row["source_outcome_label"]: row for row in rows}

    assert by_outcome["BUSINVx"]["source_outcome_role"] == (
        "inventory_context_not_final_sales_target"
    )
    assert by_outcome["BUSINVx"]["fspdp_coverage_gap_status"] == (
        "blocked_inventory_excluded_from_final_sales"
    )
    assert by_outcome["RPI"]["source_outcome_role"] == (
        "real_personal_income_macro_crosscheck"
    )
    assert by_outcome["LIP"]["source_candidate_handle"] == "gertler_karadi_aej"
    assert by_outcome["LIP"]["source_outcome_role"] == (
        "industrial_production_macro_crosscheck"
    )
    assert by_outcome["LIP"]["source_mat_or_data_sha256s"]


def test_extended_source_code_interpretation_hashes_contracts_and_fail_closed() -> None:
    rows = _rows(ARTIFACT)

    assert all(row["payload_archive_sha256"] for row in rows)
    assert all(row["source_script_sha256s"] for row in rows)
    assert all(len(row["blocked_contract_row_ids"].split(";")) == 8 for row in rows)
    assert all(
        len(row["blocked_required_field_names"].split(";")) == 8 for row in rows
    )
    assert all(row["candidate_bps_year_exposure"] == "" for row in rows)
    assert all(row["candidate_gdp_share_drag_per_100bp_year"] == "" for row in rows)
    assert all(row["candidate_ci_lower"] == "" for row in rows)
    assert all(row["candidate_ci_upper"] == "" for row in rows)
    assert {
        row["research_parameterization_admission_status"] for row in rows
    } == {"blocked_extended_source_code_interpretation_not_denominator_calibration"}
    assert all(
        all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
        for row in rows
    )


def test_extended_source_code_interpretation_ledger_and_audit_invariant() -> None:
    rows = _rows(ARTIFACT)
    ledger_rows = _rows("outputs/tables/ratewall_assumption_source_backing_ledger.csv")
    backend_audit_rows = _rows(
        "outputs/tables/ratewall_backend_invariant_guardrail_audit.csv"
    )
    source_audit_rows = _rows(
        "outputs/tables/ratewall_assumption_source_backing_invariant_audit.csv"
    )

    family_rows = [
        row
        for row in ledger_rows
        if row["assumption_family"]
        == "conventional_drag_research_extended_source_code_interpretation"
    ]
    assert len(family_rows) == len(rows)
    assert {row["source_backing_class"] for row in family_rows} == {
        "blocked_or_diagnostic_only"
    }
    assert {row["claim_boundary"] for row in family_rows} == {
        "research_extended_source_code_interpretation_not_denominator_calibration"
    }

    audit_item = (
        "conventional_drag_research_extended_source_code_interpretation_fail_closed"
    )
    assert {
        row["audit_status"]
        for row in backend_audit_rows
        if row["audit_item"] == audit_item
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in source_audit_rows
        if row["audit_item"] == audit_item
    } == {"pass"}
