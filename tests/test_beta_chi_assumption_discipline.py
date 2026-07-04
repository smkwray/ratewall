from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ratewall.databook.beta_chi_assumption_discipline import (
    BETA_CHI_CHI_BRIDGE_CANDIDATE_FIELDS,
    BETA_CHI_CHI_BRIDGE_TARGET_REVIEW_FIELDS,
    BETA_CHI_CHI_MAPPING_SENSITIVITY_FIELDS,
    BETA_CHI_CLAIM_GATE_FIELDS,
    BETA_CHI_EVIDENCE_TARGET_FIELDS,
    BETA_CHI_EXTERNAL_EVIDENCE_FIELDS,
    BETA_CHI_EXTERNAL_FLOOR_REVIEW_FIELDS,
    BETA_CHI_ROBUSTNESS_THRESHOLD_FIELDS,
    BETA_CHI_SOURCE_CONTEXT_FIELDS,
    BETA_CHI_SOURCE_REVIEW_FIELDS,
    beta_chi_chi_bridge_candidate_rows,
    beta_chi_chi_bridge_target_review_rows,
    beta_chi_chi_mapping_sensitivity_rows,
    beta_chi_claim_gate_memo_markdown,
    beta_chi_claim_gate_rows,
    beta_chi_evidence_target_rows,
    beta_chi_external_evidence_rows,
    beta_chi_external_floor_review_rows,
    beta_chi_robustness_threshold_rows,
    beta_chi_source_context_rows,
    beta_chi_source_review_rows,
    write_beta_chi_claim_gate_outputs,
)


def test_beta_chi_claim_gate_combines_grid_with_moving_denominator() -> None:
    rows = beta_chi_claim_gate_rows(
        unified_rows=_unified_rows(),
        beta_chi_robustness_rows=_robustness_rows(),
    )

    assert {field for row in rows for field in row} == set(
        BETA_CHI_CLAIM_GATE_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    holder = by_scenario["holder_more_banks"]
    assert holder["moving_d_beta_chi_sign_stability_status"] == "mixed_sign"
    assert holder["claim_strength_status"] == "point_calibrated_assumption_only"
    assert holder["narrower_range_admission_status"] == (
        "blocked_no_source_for_narrower_range_excluding_zero_crossing"
    )
    assert holder["zero_crossing_status_moving_d"] == "inside_existing_grid"
    assert holder["final_model_use"] == (
        "main_scenario_family_with_explicit_point_calibration_label"
    )

    primary = by_scenario["primary_up"]
    assert primary["moving_d_beta_chi_sign_stability_status"] == "stable_positive"
    assert primary["claim_strength_status"] == (
        "sign_robust_over_existing_beta_chi_grid"
    )
    assert primary["narrower_range_admission_status"] == (
        "not_needed_existing_grid_sign_stable"
    )

    rate = by_scenario["rate_down"]
    assert rate["scenario_axis"] == "rate_or_issuance_rate"
    assert rate["moving_d_beta_chi_sign_stability_status"] == "stable_positive"
    assert rate["grid_min_moving_delta_ratewall_ratio"] != (
        rate["grid_max_moving_delta_ratewall_ratio"]
    )


def test_beta_chi_thresholds_quantify_required_floor_for_mixed_rows() -> None:
    rows = beta_chi_claim_gate_rows(
        unified_rows=_unified_rows(),
        beta_chi_robustness_rows=_robustness_rows(),
    )

    threshold_rows = beta_chi_robustness_threshold_rows(rows)

    assert {field for row in threshold_rows for field in row} == set(
        BETA_CHI_ROBUSTNESS_THRESHOLD_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in threshold_rows}
    holder = by_scenario["holder_more_banks"]
    assert holder["admission_status"] == (
        "not_admitted_threshold_diagnostic_only_no_new_evidence"
    )
    assert Decimal(holder["required_chi_floor_at_existing_min_beta"]) > Decimal(
        holder["existing_grid_min_chi"]
    )
    assert Decimal(holder["required_beta_floor_at_existing_min_chi"]) > Decimal(
        holder["existing_grid_min_beta"]
    )
    assert holder["existing_floor_gap_status"] == (
        "both_existing_floors_below_threshold"
    )


def test_beta_chi_evidence_targets_rank_product_floor_lift() -> None:
    rows = beta_chi_claim_gate_rows(
        unified_rows=_unified_rows(),
        beta_chi_robustness_rows=_robustness_rows(),
    )
    threshold_rows = beta_chi_robustness_threshold_rows(rows)

    evidence_rows = beta_chi_evidence_target_rows(threshold_rows)

    assert {field for row in evidence_rows for field in row} == set(
        BETA_CHI_EVIDENCE_TARGET_FIELDS
    )
    holder = {row["scenario_id"]: row for row in evidence_rows}[
        "holder_more_banks"
    ]
    assert holder["required_beta_chi_floor"] == (
        threshold_rows[0]["zero_crossing_beta_times_chi_moving_d"]
    )
    assert Decimal(holder["required_product_lift_over_existing_min"]) > Decimal("0")
    assert holder["evidence_distance_tier"] == "outside_near_term_evidence_target"
    assert holder["current_model_action"] == "park_unless_new_direct_evidence"
    assert holder["admission_status"] == "not_admitted_no_new_source_evidence"


def test_beta_chi_source_review_fails_closed_without_floor_evidence(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.csv"
    source_path.write_text(
        "\n".join(
            [
                "quarter,source_status,current_demand_eligible,"
                "deposit_pass_through_scope",
                "2027Q1,source_backed_context,false,unknown_or_mixed",
                "2027Q2,source_available,false,false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rows = beta_chi_claim_gate_rows(
        unified_rows=_unified_rows(),
        beta_chi_robustness_rows=_robustness_rows(),
    )
    target_rows = beta_chi_evidence_target_rows(
        beta_chi_robustness_threshold_rows(rows)
    )

    context_rows = beta_chi_source_context_rows({"fixture": source_path})
    review_rows = beta_chi_source_review_rows(
        evidence_target_rows=target_rows,
        source_context_rows=context_rows,
    )

    assert {field for row in context_rows for field in row} == set(
        BETA_CHI_SOURCE_CONTEXT_FIELDS
    )
    assert context_rows[0]["source_row_count"] == "2"
    assert context_rows[0]["latest_quarter"] == "2027Q2"
    assert context_rows[0]["current_demand_eligible_rows"] == "0"
    assert context_rows[0]["source_review_status"] == (
        "context_available_no_admitted_beta_chi_floor"
    )
    assert {field for row in review_rows for field in row} == set(
        BETA_CHI_SOURCE_REVIEW_FIELDS
    )
    holder = {row["scenario_id"]: row for row in review_rows}[
        "holder_more_banks"
    ]
    assert holder["local_source_rows_scanned"] == "2"
    assert holder["local_admitted_beta_chi_floor_rows"] == "0"
    assert holder["admission_status"] == "not_admitted_no_source_floor"


def test_beta_chi_external_screen_does_not_admit_contextual_mpc() -> None:
    target_rows = [
        {
            "fiscal_year": "2027",
            "scenario_id": "near_floor",
            "scenario_axis": "combined_holder_rate",
            "evidence_distance_tier": "near_existing_floor",
            "required_chi_floor_at_existing_min_beta": "0.031",
            "required_beta_floor_at_existing_min_chi": "0.12",
        },
        {
            "fiscal_year": "2027",
            "scenario_id": "hard_floor",
            "scenario_axis": "holder_only",
            "evidence_distance_tier": "outside_near_term_evidence_target",
            "required_chi_floor_at_existing_min_beta": "0.30",
            "required_beta_floor_at_existing_min_chi": "0.70",
        },
    ]

    evidence_rows = beta_chi_external_evidence_rows()
    review_rows = beta_chi_external_floor_review_rows(
        evidence_target_rows=target_rows,
        external_evidence_rows=evidence_rows,
    )

    assert {field for row in evidence_rows for field in row} == set(
        BETA_CHI_EXTERNAL_EVIDENCE_FIELDS
    )
    assert {field for row in review_rows for field in row} == set(
        BETA_CHI_EXTERNAL_FLOOR_REVIEW_FIELDS
    )
    near = {row["scenario_id"]: row for row in review_rows}["near_floor"]
    assert Decimal(near["external_chi_candidates_clearing_floor"]) > Decimal("0")
    assert near["external_admitted_chi_floor_rows"] == "0"
    assert near["external_floor_review_result"] == (
        "external_screen_candidates_clear_floor_but_none_admitted"
    )
    assert near["admission_status"] == "not_admitted_external_screen_only"
    hard = {row["scenario_id"]: row for row in review_rows}["hard_floor"]
    assert hard["external_floor_review_result"] == (
        "no_external_candidate_clears_required_floor"
    )


def test_beta_chi_chi_bridge_quantifies_mapping_needed_without_admission() -> None:
    target_rows = [
        {
            "fiscal_year": "2027",
            "scenario_id": "near_floor",
            "scenario_axis": "combined_holder_rate",
            "evidence_distance_tier": "near_existing_floor",
            "required_chi_floor_at_existing_min_beta": "0.031",
        },
        {
            "fiscal_year": "2027",
            "scenario_id": "too_hard",
            "scenario_axis": "holder_only",
            "evidence_distance_tier": "outside_near_term_evidence_target",
            "required_chi_floor_at_existing_min_beta": "0.30",
        },
    ]

    candidate_rows = beta_chi_chi_bridge_candidate_rows(
        beta_chi_external_evidence_rows(),
    )
    review_rows = beta_chi_chi_bridge_target_review_rows(
        evidence_target_rows=target_rows,
        chi_bridge_candidate_rows=candidate_rows,
    )

    assert {field for row in candidate_rows for field in row} == set(
        BETA_CHI_CHI_BRIDGE_CANDIDATE_FIELDS
    )
    assert {field for row in review_rows for field in row} == set(
        BETA_CHI_CHI_BRIDGE_TARGET_REVIEW_FIELDS
    )
    assert candidate_rows[0]["bridge_candidate_id"] == (
        "aer_cash_like_transfer_mpc_2025"
    )
    near = {row["scenario_id"]: row for row in review_rows}["near_floor"]
    assert near["candidate_can_clear_floor_before_mapping_haircut"] == "true"
    assert near["mapping_share_feasibility_tier"] == "low_mapping_share_needed"
    assert near["admitted_chi_floor_after_bridge_rows"] == "0"
    assert near["admission_status"] == (
        "not_admitted_requires_ratewall_specific_bridge"
    )
    too_hard = {row["scenario_id"]: row for row in review_rows}["too_hard"]
    assert too_hard["candidate_can_clear_floor_before_mapping_haircut"] == "false"
    assert too_hard["mapping_share_feasibility_tier"] == (
        "candidate_too_small_even_before_mapping_haircut"
    )


def test_beta_chi_chi_mapping_sensitivity_keeps_claim_boundary() -> None:
    target_rows = [
        {
            "fiscal_year": "2027",
            "scenario_id": "near_floor",
            "scenario_axis": "combined_holder_rate",
            "evidence_distance_tier": "near_existing_floor",
            "required_chi_floor_at_existing_min_beta": "0.031",
            "existing_grid_min_chi": "0.03",
        },
        {
            "fiscal_year": "2027",
            "scenario_id": "moderate_floor",
            "scenario_axis": "holder_only",
            "evidence_distance_tier": "moderate_product_floor_lift",
            "required_chi_floor_at_existing_min_beta": "0.084",
            "existing_grid_min_chi": "0.03",
        },
    ]
    candidates = beta_chi_chi_bridge_candidate_rows(
        beta_chi_external_evidence_rows(),
    )

    rows = beta_chi_chi_mapping_sensitivity_rows(
        evidence_target_rows=target_rows,
        chi_bridge_candidate_rows=candidates,
        mapping_share_profiles=(
            ("low_bridge", Decimal("0.25")),
            ("medium_bridge", Decimal("0.50")),
        ),
    )

    assert {field for row in rows for field in row} == set(
        BETA_CHI_CHI_MAPPING_SENSITIVITY_FIELDS
    )
    by_key = {(row["scenario_id"], row["mapping_share_profile"]): row for row in rows}
    assert by_key[("near_floor", "low_bridge")]["implied_chi_floor"] == "0.0575"
    assert by_key[("near_floor", "low_bridge")]["clears_required_chi_floor"] == "true"
    assert (
        by_key[("moderate_floor", "low_bridge")]["clears_required_chi_floor"]
        == "false"
    )
    assert (
        by_key[("moderate_floor", "medium_bridge")]["clears_required_chi_floor"]
        == "true"
    )
    assert {
        row["admission_status"] for row in rows
    } == {"not_admitted_mapping_sensitivity_only_no_chi_floor_change"}


def test_beta_chi_claim_gate_outputs_csv_and_memo(tmp_path: Path) -> None:
    rows = beta_chi_claim_gate_rows(
        unified_rows=_unified_rows(),
        beta_chi_robustness_rows=_robustness_rows(),
    )
    threshold_rows = beta_chi_robustness_threshold_rows(rows)
    evidence_target_rows = beta_chi_evidence_target_rows(threshold_rows)
    source_context_rows = [
        {field: "0" for field in BETA_CHI_SOURCE_CONTEXT_FIELDS}
        | {
            "beta_chi_source_context_row_id": "context::fixture",
            "source_context_id": "fixture",
            "source_present": "true",
            "source_review_status": "context_available_no_admitted_beta_chi_floor",
        }
    ]
    source_review_rows = beta_chi_source_review_rows(
        evidence_target_rows=evidence_target_rows,
        source_context_rows=source_context_rows,
    )
    external_evidence_rows = beta_chi_external_evidence_rows()
    external_floor_review_rows = beta_chi_external_floor_review_rows(
        evidence_target_rows=evidence_target_rows,
        external_evidence_rows=external_evidence_rows,
    )
    chi_bridge_candidate_rows = beta_chi_chi_bridge_candidate_rows(
        external_evidence_rows,
    )
    chi_bridge_target_review_rows = beta_chi_chi_bridge_target_review_rows(
        evidence_target_rows=evidence_target_rows,
        chi_bridge_candidate_rows=chi_bridge_candidate_rows,
    )
    chi_mapping_sensitivity_rows = beta_chi_chi_mapping_sensitivity_rows(
        evidence_target_rows=evidence_target_rows,
        chi_bridge_candidate_rows=chi_bridge_candidate_rows,
    )

    outputs = write_beta_chi_claim_gate_outputs(
        tmp_path,
        rows=rows,
        threshold_rows=threshold_rows,
        evidence_target_rows=evidence_target_rows,
        source_context_rows=source_context_rows,
        source_review_rows=source_review_rows,
        external_evidence_rows=external_evidence_rows,
        external_floor_review_rows=external_floor_review_rows,
        chi_bridge_candidate_rows=chi_bridge_candidate_rows,
        chi_bridge_target_review_rows=chi_bridge_target_review_rows,
        chi_mapping_sensitivity_rows=chi_mapping_sensitivity_rows,
    )

    assert outputs["csv"].read_text(encoding="utf-8").startswith(
        "beta_chi_claim_gate_row_id,"
    )
    assert outputs["threshold_csv"].read_text(encoding="utf-8").startswith(
        "beta_chi_threshold_row_id,"
    )
    assert outputs["evidence_target_csv"].read_text(encoding="utf-8").startswith(
        "beta_chi_evidence_target_row_id,"
    )
    assert outputs["source_context_csv"].read_text(encoding="utf-8").startswith(
        "beta_chi_source_context_row_id,"
    )
    assert outputs["source_review_csv"].read_text(encoding="utf-8").startswith(
        "beta_chi_source_review_row_id,"
    )
    assert outputs["external_evidence_csv"].read_text(encoding="utf-8").startswith(
        "beta_chi_external_evidence_row_id,"
    )
    assert outputs["external_floor_review_csv"].read_text(
        encoding="utf-8"
    ).startswith("beta_chi_external_floor_review_row_id,")
    assert outputs["chi_bridge_candidate_csv"].read_text(
        encoding="utf-8"
    ).startswith("beta_chi_chi_bridge_candidate_row_id,")
    assert outputs["chi_bridge_target_review_csv"].read_text(
        encoding="utf-8"
    ).startswith("beta_chi_chi_bridge_target_review_row_id,")
    assert outputs["chi_mapping_sensitivity_csv"].read_text(
        encoding="utf-8"
    ).startswith("beta_chi_chi_mapping_sensitivity_row_id,")
    memo = beta_chi_claim_gate_memo_markdown(
        rows,
        threshold_rows=threshold_rows,
        evidence_target_rows=evidence_target_rows,
        source_review_rows=source_review_rows,
        external_floor_review_rows=external_floor_review_rows,
        chi_bridge_target_review_rows=chi_bridge_target_review_rows,
        chi_mapping_sensitivity_rows=chi_mapping_sensitivity_rows,
    )
    assert outputs["memo_md"].read_text(encoding="utf-8") == memo
    assert "does not justify narrowing the beta-chi range" in memo
    assert "What Would Make These Sign-Robust?" in memo
    assert "Evidence Targets" in memo
    assert "Source Review" in memo
    assert "External Evidence Screen" in memo
    assert "Chi Bridge Review" in memo
    assert "Chi Mapping Sensitivity" in memo
    assert "Rows admitted from external/direct floor evidence: `0`." in memo
    assert "Rows admitted after a RateWall-specific bridge: `0`." in memo
    assert "Mapping sensitivity rows admitted as new chi floors: `0`." in memo
    assert "No row is promoted into the canonical headline result" in memo


def _unified_rows() -> list[dict[str, str]]:
    return [
        _unified("baseline", "baseline", "100", "0"),
        _unified("holder_more_banks", "holder_only", "100", "0.20"),
        _unified("primary_up", "other_zero_rate", "100", "0.02"),
        _unified("rate_down", "rate_or_issuance_rate", "90", "0.05"),
    ]


def _unified(
    scenario_id: str,
    axis: str,
    moving_d: str,
    delta_rw: str,
) -> dict[str, str]:
    return {
        "fiscal_year": "2027",
        "scenario_id": scenario_id,
        "baseline_scenario_id": "baseline",
        "scenario_axis": axis,
        "selected_moving_denominator_bil": moving_d,
        "selected_moving_delta_ratewall_ratio_vs_baseline": delta_rw,
    }


def _robustness_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    profiles = [
        ("low", "conservative", "0.003"),
        ("base", "base", "0.024"),
        ("high", "demand_active", "0.068"),
    ]
    for beta, chi, beta_chi in profiles:
        rows.append(
            _robustness(
                "baseline",
                beta,
                chi,
                beta_chi,
                tdc_change="10",
                direct="5",
                bank="5",
                total="10.03" if beta == "low" else "10.24" if beta == "base" else "10.68",
            )
        )
        rows.append(
            _robustness(
                "holder_more_banks",
                beta,
                chi,
                beta_chi,
                tdc_change="100",
                direct="2",
                bank="2",
                total="4.3" if beta == "low" else "6.4" if beta == "base" else "10.8",
            )
        )
        rows.append(
            _robustness(
                "primary_up",
                beta,
                chi,
                beta_chi,
                tdc_change="20",
                direct="8",
                bank="6",
                total="14.06" if beta == "low" else "14.48" if beta == "base" else "15.36",
            )
        )
        rows.append(
            _robustness(
                "rate_down",
                beta,
                chi,
                beta_chi,
                tdc_change="10",
                direct="5",
                bank="5",
                total="10.03" if beta == "low" else "10.24" if beta == "base" else "10.68",
            )
        )
    return rows


def _robustness(
    scenario_id: str,
    beta: str,
    chi: str,
    beta_chi: str,
    *,
    tdc_change: str,
    direct: str,
    bank: str,
    total: str,
) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "baseline_scenario_id": "baseline",
        "fiscal_year": "2027",
        "tdc_materialization_beta_scenario": beta,
        "tdc_materialization_beta": {"low": "0.1", "base": "0.3", "high": "0.6"}[beta],
        "deposit_current_demand_share_profile": chi,
        "deposit_current_demand_share": {
            "conservative": "0.03",
            "base": "0.08",
            "demand_active": "0.11333333333333333",
        }[chi],
        "derived_beta_times_chi": beta_chi,
        "profile_is_current_point_calibration": str(
            beta == "base" and chi == "base"
        ).lower(),
        "tdc_change_ex_overlap_bil": tdc_change,
        "baseline_tdc_change_ex_overlap_bil": "10",
        "direct_treasury_current_demand_support_bil_fixed": direct,
        "baseline_direct_treasury_current_demand_support_bil_fixed": "5",
        "bank_treasury_current_demand_support_bil_fixed": bank,
        "baseline_bank_treasury_current_demand_support_bil_fixed": "5",
        "total_current_demand_support_bil_recomputed": total,
    }
