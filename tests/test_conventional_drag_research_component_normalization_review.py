import pytest
import csv
from collections import Counter, defaultdict
from pathlib import Path




pytestmark = pytest.mark.full_surface

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


AGGREGATION_ARTIFACT = (
    "outputs/tables/"
    "ratewall_conventional_drag_research_mir_component_aggregation_"
    "normalization_review.csv"
)
VARIANT_ARTIFACT = (
    "outputs/tables/"
    "ratewall_conventional_drag_research_mir_component_source_variant_review.csv"
)


def _rows(path: str) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_mir_component_aggregation_review_row_grain_and_counts() -> None:
    rows = _rows(AGGREGATION_ARTIFACT)
    interpretation_rows = _rows(
        "outputs/tables/"
        "ratewall_conventional_drag_research_source_code_interpretation.csv"
    )

    assert len(rows) == 24
    assert len({row["component_aggregation_review_row_id"] for row in rows}) == 24
    assert {
        row["source_code_interpretation_row_id"] for row in rows
    } == {row["source_code_interpretation_row_id"] for row in interpretation_rows}
    assert Counter(row["component_evidence_class"] for row in rows) == {
        "direct_pce_subcomponent_quantity_evidence": 12,
        "residential_investment_activity_proxy": 12,
    }
    assert Counter(row["supporting_source_variant_count"] for row in rows) == {
        "1": 12,
        "2": 12,
    }


def test_mir_component_aggregation_review_parent_share_and_contract_joins() -> None:
    rows = _rows(AGGREGATION_ARTIFACT)

    assert {row["parent_share_bridge_row_count"] for row in rows} == {"3"}
    assert {
        row["parent_share_bridge_status"] for row in rows
    } == {"pass_parent_share_bridge_available_review_only"}
    assert all(
        len(row["parent_share_bridge_row_ids"].split(";")) == 3 for row in rows
    )
    assert all(len(row["blocked_contract_row_ids"].split(";")) == 8 for row in rows)
    assert all(
        len(row["blocked_required_field_names"].split(";")) == 8 for row in rows
    )
    assert {
        row["policy_path_normalization_gate_status"] for row in rows
    } == {"blocked_no_admitted_100bp_year_policy_path"}


def test_mir_component_aggregation_review_component_status_matrix() -> None:
    rows = _rows(AGGREGATION_ARTIFACT)
    by_outcome = defaultdict(list)
    for row in rows:
        by_outcome[row["source_outcome_label"]].append(row)

    for outcome in ("DDURRA3M086SBEA", "DNDGRA3M086SBEA"):
        assert {
            row["component_evidence_class_status"] for row in by_outcome[outcome]
        } == {"pass_direct_pce_subcomponent_evidence_review_only"}
        assert {
            row["component_weight_status"] for row in by_outcome[outcome]
        } == {"blocked_missing_pce_major_type_component_weights"}
        assert {
            row["proxy_bridge_status"] for row in by_outcome[outcome]
        } == {"not_applicable_direct_component_series"}

    for outcome in ("HOUST", "PERMIT"):
        assert {
            row["component_evidence_class_status"] for row in by_outcome[outcome]
        } == {"pass_residential_investment_activity_proxy_review_only"}
        assert {
            row["component_weight_status"] for row in by_outcome[outcome]
        } == {"blocked_missing_private_fixed_investment_subcomponent_weights"}
        assert {
            row["proxy_bridge_status"] for row in by_outcome[outcome]
        } == {
            "blocked_missing_reviewed_proxy_bridge_to_residential_fixed_investment"
        }
        assert not any(
            "direct_bea_fixed_investment" in row["component_evidence_class"]
            for row in by_outcome[outcome]
        )


def test_mir_component_source_variant_review_exposes_multi_mat_conflict() -> None:
    rows = _rows(VARIANT_ARTIFACT)
    by_interpretation = defaultdict(list)
    for row in rows:
        by_interpretation[row["source_code_interpretation_row_id"]].append(row)

    assert len(rows) == 36
    assert len({row["component_source_variant_review_row_id"] for row in rows}) == 36
    assert Counter(len(items) for items in by_interpretation.values()) == {
        1: 12,
        2: 12,
    }
    assert {
        row["support_variant_conflict_status"]
        for row in rows
        if row["source_outcome_label"] in {"HOUST", "PERMIT"}
    } == {"blocked_supporting_variant_values_not_identical_across_mat_paths"}
    assert {
        row["support_variant_conflict_status"]
        for row in rows
        if row["source_outcome_label"] in {"DDURRA3M086SBEA", "DNDGRA3M086SBEA"}
    } == {"pass_single_variant_family_member"}


def test_mir_component_reviews_fail_closed_candidate_and_switch_fields() -> None:
    for rows in (_rows(AGGREGATION_ARTIFACT), _rows(VARIANT_ARTIFACT)):
        assert all(row["candidate_bps_year_exposure"] == "" for row in rows)
        assert all(row["candidate_gdp_share_drag_per_100bp_year"] == "" for row in rows)
        assert all(row["candidate_ci_lower"] == "" for row in rows)
        assert all(row["candidate_ci_upper"] == "" for row in rows)
        assert all(
            row["research_parameterization_admission_status"].startswith("blocked")
            for row in rows
        )
        assert all(
            all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
            for row in rows
        )


def test_mir_component_review_ledger_and_audit_invariant() -> None:
    ledger_rows = _rows("outputs/tables/ratewall_assumption_source_backing_ledger.csv")
    backend_audit_rows = _rows(
        "outputs/tables/ratewall_backend_invariant_guardrail_audit.csv"
    )
    source_audit_rows = _rows(
        "outputs/tables/ratewall_assumption_source_backing_invariant_audit.csv"
    )

    expected = {
        (
            "conventional_drag_research_mir_component_aggregation_review",
            AGGREGATION_ARTIFACT.replace("outputs/tables/", ""),
            len(_rows(AGGREGATION_ARTIFACT)),
            "research_mir_component_aggregation_review_not_denominator_calibration",
        ),
        (
            "conventional_drag_research_mir_component_source_variant_review",
            VARIANT_ARTIFACT.replace("outputs/tables/", ""),
            len(_rows(VARIANT_ARTIFACT)),
            "research_component_source_variant_review_not_denominator_calibration",
        ),
    }
    for family, artifact_name, expected_count, claim_boundary in expected:
        family_rows = [
            row for row in ledger_rows if row["assumption_family"] == family
        ]
        assert len(family_rows) == expected_count
        assert {row["artifact_or_surface"] for row in family_rows} == {artifact_name}
        assert {row["source_backing_class"] for row in family_rows} == {
            "blocked_or_diagnostic_only"
        }
        assert {row["claim_boundary"] for row in family_rows} == {claim_boundary}
        assert all(row["enters_canonical_ratio"] == "false" for row in family_rows)

    for audit_item in {
        "conventional_drag_research_mir_component_aggregation_review_fail_closed",
        "conventional_drag_research_mir_component_source_variant_review_fail_closed",
    }:
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
