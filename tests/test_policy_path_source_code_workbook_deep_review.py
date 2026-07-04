import pytest
import csv
from collections import Counter, defaultdict
from pathlib import Path




pytestmark = pytest.mark.full_surface

OBJECT_ARTIFACT = (
    "outputs/tables/ratewall_policy_path_source_code_workbook_object_inventory.csv"
)
DEEP_REVIEW_ARTIFACT = (
    "outputs/tables/ratewall_policy_path_source_code_workbook_protocol_deep_review.csv"
)

EXPECTED_PROTOCOL_FIELDS = {
    "source_cell_or_series_unit_contract",
    "source_backed_policy_path_vector",
    "event_horizon_grid",
    "loading_back_transform",
    "bps_year_integral_formula",
    "independent_bps_year_replication_target",
}

CANDIDATE_FIELDS = [
    "candidate_rate_change_bps",
    "candidate_bps_year_component",
    "candidate_bps_year_exposure",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
]

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
    "holder_allocation_enabled",
    "raw_rate_shock_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "causal_financialization_claim_enabled",
]


def _rows(path: str) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_source_code_workbook_object_inventory_shape_and_coverage() -> None:
    rows = _rows(OBJECT_ARTIFACT)

    assert len(rows) == 19
    assert len({row["source_object_inventory_row_id"] for row in rows}) == 19
    assert Counter(row["source_bundle_handle"] for row in rows) == {
        "sf_fed_usmpd_source_zip": 5,
        "fed_sofr_continuity_accessible_materials_zip": 2,
        "sf_fed_usmpd_workbook": 5,
        "sf_fed_monetary_policy_surprises_workbook": 5,
        "acosta_abj_2024_monetary_policy_surprises_workbook": 2,
    }
    assert Counter(row["object_type"] for row in rows) == {
        "xlsx_workbook_sheet": 12,
        "csv_data_or_output": 3,
        "html_accessible_materials": 2,
        "documentation_text": 1,
        "source_code_script": 1,
    }
    assert {row["object_role"] for row in rows} >= {
        "usmpd_scalar_mps_construction_code",
        "usmpd_source_futures_input_matrix",
        "event_level_candidate_workbook_sheet",
        "monthly_candidate_workbook_sheet",
        "acosta_updated_policy_news_shock_series",
        "fed_sofr_continuity_accessible_context",
    }
    assert all(row["source_artifact_sha256"] for row in rows)
    assert all(row["object_sha256"] for row in rows)


def test_source_code_workbook_inventory_detects_review_clues_without_admission() -> None:
    rows = _rows(OBJECT_ARTIFACT)
    mps_code = next(row for row in rows if row["object_path"] == "mps.R")
    fomc_update = next(
        row
        for row in rows
        if row["object_path"].startswith("FOMC (update 2023)::")
    )

    assert "principal component" in mps_code["detected_pca_or_factor_tokens"]
    assert "loading" in mps_code["detected_loading_or_weight_tokens"]
    assert "ed[1-4]" in mps_code["detected_horizon_tokens"]
    assert mps_code["pca_loading_clue_status"] == (
        "pass_pca_or_loading_clue_review_only_not_back_transform"
    )
    assert fomc_update["horizon_construction_clue_status"] == (
        "pass_horizon_clue_review_only_not_event_grid"
    )
    assert {row["object_protocol_review_status"] for row in rows} == {
        "blocked_object_inventory_not_complete_bps_year_protocol"
    }
    for row in rows:
        assert all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)


def test_source_code_workbook_protocol_deep_review_fail_closed_gate_matrix() -> None:
    rows = _rows(DEEP_REVIEW_ARTIFACT)
    fields_by_object: dict[str, set[str]] = defaultdict(set)

    assert len(rows) == 114
    assert len({row["source_protocol_deep_review_row_id"] for row in rows}) == 114
    assert {row["required_protocol_field"] for row in rows} == EXPECTED_PROTOCOL_FIELDS
    for row in rows:
        fields_by_object[row["source_object_inventory_row_id"]].add(
            row["required_protocol_field"]
        )
        assert all(row[field] == "" for field in CANDIDATE_FIELDS)
        assert all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
        assert row["full_protocol_gate_status"] == (
            "blocked_missing_complete_source_code_workbook_bps_year_protocol"
        )
        assert row["protocol_admission_status"] == (
            "blocked_source_code_workbook_deep_review_not_complete_bps_year_protocol"
        )
        assert row["policy_path_100bp_year_normalization_status"] == (
            "blocked_no_admitted_bps_year_policy_path"
        )

    assert len(fields_by_object) == 19
    assert all(fields == EXPECTED_PROTOCOL_FIELDS for fields in fields_by_object.values())
    assert {
        row["deep_review_evidence_status"]
        for row in rows
        if row["required_protocol_field"] == "source_backed_policy_path_vector"
    } == {"blocked_object_does_not_supply_policy_rate_path_vector"}
    assert {
        row["deep_review_evidence_status"]
        for row in rows
        if row["required_protocol_field"] == "bps_year_integral_formula"
    } >= {
        "blocked_no_bps_year_integral_formula_in_object",
    }


def test_source_code_workbook_deep_review_ledger_and_audit_invariant() -> None:
    object_rows = _rows(OBJECT_ARTIFACT)
    review_rows = _rows(DEEP_REVIEW_ARTIFACT)
    ledger_rows = _rows("outputs/tables/ratewall_assumption_source_backing_ledger.csv")
    backend_audit_rows = _rows(
        "outputs/tables/ratewall_backend_invariant_guardrail_audit.csv"
    )
    source_audit_rows = _rows(
        "outputs/tables/ratewall_assumption_source_backing_invariant_audit.csv"
    )
    object_ledger = [
        row
        for row in ledger_rows
        if row["assumption_family"]
        == "policy_path_source_code_workbook_object_inventory"
    ]
    review_ledger = [
        row
        for row in ledger_rows
        if row["assumption_family"]
        == "policy_path_source_code_workbook_protocol_deep_review"
    ]
    assert len(object_ledger) == len(object_rows)
    assert len(review_ledger) == len(review_rows)
    assert {row["source_backing_class"] for row in object_ledger + review_ledger} == {
        "blocked_or_diagnostic_only"
    }
    assert {
        row["audit_status"]
        for row in backend_audit_rows
        if row["audit_item"]
        in {
            "policy_path_source_code_workbook_object_inventory_fail_closed",
            "policy_path_source_code_workbook_protocol_deep_review_fail_closed",
        }
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in source_audit_rows
        if row["audit_item"]
        in {
            "policy_path_source_code_workbook_object_inventory_fail_closed",
            "policy_path_source_code_workbook_protocol_deep_review_fail_closed",
        }
    } == {"pass"}
