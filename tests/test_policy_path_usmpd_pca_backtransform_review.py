import pytest
import csv
from collections import Counter
from pathlib import Path




pytestmark = pytest.mark.full_surface

LOADING_ARTIFACT = (
    "outputs/tables/"
    "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv"
)
SCALAR_ARTIFACT = (
    "outputs/tables/"
    "ratewall_policy_path_usmpd_scalar_score_replication_review.csv"
)
GATE_ARTIFACT = (
    "outputs/tables/ratewall_policy_path_usmpd_pca_backtransform_gate_review.csv"
)

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


def test_usmpd_pca_loading_backtransform_row_counts_and_replication() -> None:
    rows = _rows(LOADING_ARTIFACT)

    assert len(rows) == 19
    assert len({row["pca_loading_review_row_id"] for row in rows}) == 19
    assert Counter(row["event_surface"] for row in rows) == {
        "statements": 5,
        "press_conferences": 5,
        "monetary_events": 5,
        "minutes": 4,
    }
    assert Counter(row["instrument_code"] for row in rows) == {
        "MP1": 3,
        "MP2": 4,
        "ED2": 4,
        "ED3": 4,
        "ED4": 4,
    }
    assert all(float(row["source_mps_max_abs_diff"]) < 1e-10 for row in rows)
    assert {row["pca_replication_status"] for row in rows} == {
        "pass_prcomp_scale_true_replication_review_only"
    }
    assert {row["loading_back_transform_status"] for row in rows} == {
        "pass_pca_loading_and_scalar_backtransform_review_only_not_path"
    }
    assert {row["policy_path_100bp_year_normalization_status"] for row in rows} == {
        "blocked_no_admitted_bps_year_policy_path"
    }


def test_usmpd_scalar_score_replication_row_counts_and_match() -> None:
    rows = _rows(SCALAR_ARTIFACT)

    assert len(rows) == 815
    assert len({row["scalar_score_review_row_id"] for row in rows}) == 815
    assert Counter(row["event_surface"] for row in rows) == {
        "statements": 276,
        "press_conferences": 92,
        "monetary_events": 276,
        "minutes": 171,
    }
    assert all(float(row["replication_abs_diff"]) < 1e-10 for row in rows)
    assert {row["replication_match_status"] for row in rows} == {
        "pass_reproduces_source_mps_within_tolerance"
    }
    assert {row["scalar_score_construction_status"] for row in rows} == {
        "pass_event_level_scalar_mps_replication_review_only"
    }
    assert {row["policy_path_100bp_year_normalization_status"] for row in rows} == {
        "blocked_no_admitted_bps_year_policy_path"
    }


def test_usmpd_pca_gate_review_fail_closed_matrix() -> None:
    rows = _rows(GATE_ARTIFACT)
    pass_review_gates = {
        "source_unit_and_scaling",
        "pca_loading_and_standardization",
        "scalar_score_replication",
    }
    blocked_gates = {
        "event_specific_horizon_weights",
        "bps_year_integral_formula",
        "independent_bps_year_replication_target",
        "promotion_rule",
    }

    assert len(rows) == 28
    assert len({row["pca_backtransform_gate_review_row_id"] for row in rows}) == 28
    assert Counter(row["event_surface"] for row in rows) == {
        "statements": 7,
        "press_conferences": 7,
        "monetary_events": 7,
        "minutes": 7,
    }
    assert {row["required_gate"] for row in rows} == pass_review_gates | blocked_gates
    assert {
        row["gate_review_status"]
        for row in rows
        if row["required_gate"] in pass_review_gates
    } == {f"pass_{gate}_review_only_not_bps_year_path" for gate in pass_review_gates}
    assert {
        row["gate_review_status"]
        for row in rows
        if row["required_gate"] in blocked_gates
    } == {f"blocked_missing_{gate}" for gate in blocked_gates}
    assert {row["protocol_admission_status"] for row in rows} == {
        "blocked_usmpd_pca_backtransform_review_not_complete_bps_year_protocol"
    }


def test_usmpd_pca_backtransform_review_fail_closed_fields() -> None:
    for rows in [_rows(LOADING_ARTIFACT), _rows(SCALAR_ARTIFACT), _rows(GATE_ARTIFACT)]:
        for row in rows:
            assert all(row[field] == "" for field in CANDIDATE_FIELDS)
            assert all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)
            assert row["claim_boundary"] == (
                "policy_path_usmpd_pca_backtransform_review_"
                "not_bps_year_or_runtime_input"
            )


def test_usmpd_pca_backtransform_review_ledger_and_audit_invariant() -> None:
    artifact_to_family = {
        LOADING_ARTIFACT: "policy_path_usmpd_pca_loading_backtransform_review",
        SCALAR_ARTIFACT: "policy_path_usmpd_scalar_score_replication_review",
        GATE_ARTIFACT: "policy_path_usmpd_pca_backtransform_gate_review",
    }
    ledger_rows = _rows("outputs/tables/ratewall_assumption_source_backing_ledger.csv")
    backend_audit_rows = _rows(
        "outputs/tables/ratewall_backend_invariant_guardrail_audit.csv"
    )
    source_audit_rows = _rows(
        "outputs/tables/ratewall_assumption_source_backing_invariant_audit.csv"
    )

    for artifact, family in artifact_to_family.items():
        rows = _rows(artifact)
        family_rows = [
            row for row in ledger_rows if row["assumption_family"] == family
        ]
        assert len(family_rows) == len(rows)
        assert {row["source_backing_class"] for row in family_rows} == {
            "blocked_or_diagnostic_only"
        }
        assert all(
            row["prior_narrowing_allowed"] == "false"
            and row["formula_replacement_allowed"] == "false"
            and row["split_denominator_promotion_allowed"] == "false"
            and row["enters_canonical_ratio"] == "false"
            for row in family_rows
        )

    expected_audits = {
        "policy_path_usmpd_pca_loading_backtransform_review_fail_closed",
        "policy_path_usmpd_scalar_score_replication_review_fail_closed",
        "policy_path_usmpd_pca_backtransform_gate_review_fail_closed",
    }
    assert {
        row["audit_item"]
        for row in backend_audit_rows
        if row["audit_item"] in expected_audits and row["audit_status"] == "pass"
    } == expected_audits
    assert {
        row["audit_item"]
        for row in source_audit_rows
        if row["audit_item"] in expected_audits and row["audit_status"] == "pass"
    } == expected_audits
