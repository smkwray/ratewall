from __future__ import annotations

import pytest

from ratewall.databook.denominator_response_application import COEFFICIENT_UNIT
from ratewall.databook.denominator_response_application import (
    denominator_response_application_rows,
)
from ratewall.databook.denominator_response_coefficient import (
    DENOMINATOR_RESPONSE_COEFFICIENT_PROFILE_FIELDS,
    FRBUS_STRUCTURAL_COEFFICIENT,
    FRBUS_STRUCTURAL_PROFILE_ID,
    DenominatorResponseCoefficientError,
    denominator_response_coefficient_profile_rows,
    frbus_structural_curve_denominator_response_candidate_profile,
    frbus_structural_curve_denominator_response_profile_rows,
    owner_admitted_curve_denominator_response_candidate_profile,
    owner_admitted_curve_denominator_response_profile_rows,
    selected_denominator_response_coefficient_profile,
    selected_frbus_structural_curve_denominator_response_profile,
    selected_owner_admitted_curve_denominator_response_profile,
)


def test_local_evidence_profile_is_blocked_without_admitted_profile() -> None:
    rows = denominator_response_coefficient_profile_rows(
        diagnostic_rows=[_diagnostic(ci_low="-0.1", ci_high="0.2")],
        path_object_rows=[_path_object(admitted=False)],
    )

    assert len(rows) == 1
    row = rows[0]
    assert list(row) == DENOMINATOR_RESPONSE_COEFFICIENT_PROFILE_FIELDS
    assert row["coefficient_admission_status"] == (
        "no_admitted_curve_denominator_response_coefficient"
    )
    assert row["path_object_candidate_count"] == "1"
    assert row["path_object_pass_count"] == "0"
    assert row["primary_diagnostic_count"] == "1"
    assert row["primary_zero_crossing_count"] == "1"
    assert row["final_version_promotion_status"] == (
        "blocked_missing_admitted_coefficient_profile"
    )
    assert "no_reviewed_100bp_year_path_object" in row["exact_blocker"]
    assert "primary_h4_confidence_interval_crosses_zero" in row["exact_blocker"]
    assert row["canonical_ratio_entry"] == "false"
    assert row["enters_main_ratio"] == "false"

    with pytest.raises(DenominatorResponseCoefficientError, match="found 0"):
        selected_denominator_response_coefficient_profile(rows)


def test_reviewed_profile_can_be_selected_for_moving_d_bridge() -> None:
    rows = denominator_response_coefficient_profile_rows(
        diagnostic_rows=[_diagnostic(ci_low="-0.4", ci_high="-0.1")],
        path_object_rows=[_path_object(admitted=True)],
        candidate_profiles=[
            _candidate_profile(
                profile_role="base_profile",
                coefficient_admission_status=(
                    "admitted_curve_denominator_response_coefficient"
                ),
                coefficient_source_status="reviewed_literature_calibrated_profile",
            )
        ],
    )

    assert len(rows) == 2
    selected = selected_denominator_response_coefficient_profile(rows)
    assert selected["denominator_response_profile_id"] == (
        "curve_response_profile::reviewed"
    )
    assert selected["denominator_response_coefficient"] == "0.2"
    assert selected["denominator_response_coefficient_unit"] == COEFFICIENT_UNIT
    assert selected["path_object_pass_count"] == "1"
    assert selected["primary_zero_crossing_count"] == "0"
    assert selected["external_profile_review_status"] == (
        "pass_reviewed_profile_supplied"
    )
    assert selected["final_version_promotion_status"] == (
        "ready_for_final_version_assumption_mode_structural_moving_D_route"
    )
    assert selected["allowed_use"] == (
        "final_version_assumption_mode_structural_moving_D_scenario_rows"
    )
    assert selected["canonical_ratio_entry"] == "false"
    assert selected["denominator_prior_update_allowed"] == "false"


def test_selected_profile_feeds_moving_d_application_bridge() -> None:
    profile_rows = denominator_response_coefficient_profile_rows(
        diagnostic_rows=[_diagnostic(ci_low="-0.4", ci_high="-0.1")],
        path_object_rows=[_path_object(admitted=True)],
        candidate_profiles=[
            _candidate_profile(
                coefficient_admission_status=(
                    "admitted_curve_denominator_response_coefficient"
                ),
                coefficient_source_status="reviewed_econometric_estimate_profile",
            )
        ],
    )
    moving_rows = denominator_response_application_rows(
        [
            {
                "tdcsim_cbo_curve_denominator_input_row_id": "curve::baseline",
                "fiscal_year": "2027",
                "scenario_id": "baseline",
                "baseline_scenario_id": "baseline",
                "effective_curve_overlay_bp": "0",
                "frozen_denominator_bil": "1000",
                "total_current_demand_support_bil": "100",
                "frozen_ratewall_ratio": "0.1",
                "frozen_delta_ratewall_ratio_vs_baseline": "0",
            },
            {
                "tdcsim_cbo_curve_denominator_input_row_id": "curve::shorter",
                "fiscal_year": "2027",
                "scenario_id": "shorter",
                "baseline_scenario_id": "baseline",
                "effective_curve_overlay_bp": "-8",
                "frozen_denominator_bil": "1000",
                "total_current_demand_support_bil": "110",
                "frozen_ratewall_ratio": "0.11",
                "frozen_delta_ratewall_ratio_vs_baseline": "0.01",
            },
        ],
        coefficient_profile=selected_denominator_response_coefficient_profile(
            profile_rows
        ),
    )

    by_scenario = {row["scenario_id"]: row for row in moving_rows}
    assert by_scenario["shorter"]["moving_denominator_bil"] == "984"
    assert by_scenario["shorter"]["denominator_response_requirement_status"] == (
        "pass_moving_D_computed_from_admitted_profile"
    )


def test_owner_admitted_theta0125_profile_is_selected_through_t9() -> None:
    rows = owner_admitted_curve_denominator_response_profile_rows(
        diagnostic_rows=[],
        path_object_rows=[_path_object(admitted=False)],
    )

    assert len(rows) == 2
    profile = selected_owner_admitted_curve_denominator_response_profile(
        diagnostic_rows=[],
        path_object_rows=[_path_object(admitted=False)],
    )
    assert profile["denominator_response_profile_id"] == (
        "curve_denominator_response::owner_theta0125_h4_20260627"
    )
    assert profile["denominator_response_coefficient"] == "0.125"
    assert profile["coefficient_admission_status"] == (
        "admitted_noncanonical_curve_denominator_response_coefficient"
    )
    assert profile["coefficient_source_status"] == (
        "owner_admitted_explicit_assumption_profile"
    )
    assert profile["external_profile_review_status"] == (
        "pass_owner_assumption_profile_supplied"
    )
    assert profile["final_version_promotion_status"] == (
        "ready_for_final_version_assumption_mode_moving_D_scenario_rows"
    )
    assert profile["allowed_use"] == (
        "final_version_assumption_mode_moving_D_scenario_rows"
    )
    assert "not_empirical_estimate" in profile["claim_boundary"]
    assert "evidence_mode_claim" in profile["blocked_use"]
    assert profile["evidence_mode_enabled"] == "false"
    assert profile["denominator_prior_update_allowed"] == "false"


def test_frbus_structural_profile_is_selected_through_t9() -> None:
    rows = frbus_structural_curve_denominator_response_profile_rows(
        diagnostic_rows=[],
        path_object_rows=[_path_object(admitted=True)],
    )

    assert len(rows) == 2
    profile = selected_frbus_structural_curve_denominator_response_profile(
        diagnostic_rows=[],
        path_object_rows=[_path_object(admitted=True)],
    )

    assert profile["denominator_response_profile_id"] == FRBUS_STRUCTURAL_PROFILE_ID
    assert profile["denominator_response_coefficient"] == FRBUS_STRUCTURAL_COEFFICIENT
    assert profile["coefficient_admission_status"] == (
        "admitted_noncanonical_curve_denominator_response_coefficient"
    )
    assert profile["coefficient_source_status"] == (
        "reviewed_literature_calibrated_profile"
    )
    assert profile["external_profile_review_status"] == (
        "pass_reviewed_profile_supplied"
    )
    assert profile["final_version_promotion_status"] == (
        "ready_for_final_version_assumption_mode_structural_moving_D_route"
    )
    assert profile["allowed_use"] == (
        "final_version_assumption_mode_structural_moving_D_scenario_rows"
    )
    assert profile["canonical_ratio_entry"] == "false"
    assert profile["denominator_prior_update_allowed"] == "false"


def test_owner_profile_metadata_matches_greenlight_conversion() -> None:
    candidate = owner_admitted_curve_denominator_response_candidate_profile()

    assert candidate["denominator_response_coefficient"] == "0.125"
    assert candidate["source_estimate"] == "-0.097"
    assert candidate["source_estimate_unit"] == (
        "owner_assumed_ppGDP_drag_equivalent_per_100bp_year_implied_by_"
        "cD_0p125_and_D_share_pp_0p776"
    )
    assert candidate["coefficient_uncertainty"] == (
        "owner_sensitivity_bounds_cD=[0,0.25]; selected_base_cD=0.125; "
        "lower_zero_is_sensitivity_not_zero_response_proof"
    )
    assert candidate["fspdp_gdp_to_d_conversion"] == (
        "c_D = owner_drag_ppGDP_per_100bp_year / D_share_pp = 0.097 / "
        "0.776 = 0.125"
    )
    assert candidate["sign_convention"] == (
        "positive_effective_curve_overlay_is_contractionary_and_increases_D"
    )


def test_frbus_structural_profile_metadata_matches_structural_benchmark() -> None:
    candidate = frbus_structural_curve_denominator_response_candidate_profile()

    assert candidate["denominator_response_coefficient"] == "1.1198692004749646"
    assert candidate["source_estimate"] == "-0.8690184995685726"
    assert candidate["source_estimate_unit"] == (
        "frbus_structural_ppGDP_FSPDP_like_response_per_100bp_year"
    )
    assert "pyfrbus 1.1.1 LONGBASE" in candidate["path_construction"]
    assert "100.00000000347879 bp-year" in candidate["path_construction"]
    assert candidate["coefficient_uncertainty"] == (
        "structural_benchmark_no_sampling_ci; local econometric estimate not "
        "admitted; owner sensitivity cD=[0,0.25] retained separately"
    )
    assert candidate["fspdp_gdp_to_d_conversion"] == (
        "c_D = -beta_ppGDP_per_100bp_year / D_share_pp = "
        "-0.8690184995685726 / -0.776 = 1.1198692004749646"
    )


def test_frbus_structural_profile_is_final_assumption_mode_not_empirical() -> None:
    profile = selected_frbus_structural_curve_denominator_response_profile(
        diagnostic_rows=[],
        path_object_rows=[],
    )

    assert profile["final_version_promotion_status"] == (
        "ready_for_final_version_assumption_mode_structural_moving_D_route"
    )
    assert profile["allowed_use"] == (
        "final_version_assumption_mode_structural_moving_D_scenario_rows"
    )
    assert "empirical_same_axis_treasury_evidence_claim" in profile["blocked_use"]
    assert "not_empirical_same_axis_treasury_evidence" in profile["claim_boundary"]
    assert profile["evidence_mode_enabled"] == "false"
    assert profile["denominator_prior_update_allowed"] == "false"


def test_admitted_profile_requires_reviewed_source_status() -> None:
    with pytest.raises(DenominatorResponseCoefficientError, match="reviewed"):
        denominator_response_coefficient_profile_rows(
            diagnostic_rows=[],
            path_object_rows=[],
            candidate_profiles=[
                _candidate_profile(
                    "bad",
                    coefficient_admission_status=(
                        "admitted_curve_denominator_response_coefficient"
                    ),
                    coefficient_source_status="unreviewed_guess",
                )
            ],
        )


def test_admitted_profile_requires_axis_metadata() -> None:
    candidate = _candidate_profile(
        "metadata_gap",
        coefficient_admission_status=(
            "admitted_curve_denominator_response_coefficient"
        ),
        coefficient_source_status="reviewed_econometric_estimate_profile",
    )
    candidate.pop("path_construction")

    with pytest.raises(DenominatorResponseCoefficientError, match="metadata"):
        denominator_response_coefficient_profile_rows(
            diagnostic_rows=[],
            path_object_rows=[],
            candidate_profiles=[candidate],
        )


def test_admitted_profile_requires_primary_outcome_axis() -> None:
    with pytest.raises(DenominatorResponseCoefficientError, match="target outcome"):
        denominator_response_coefficient_profile_rows(
            diagnostic_rows=[],
            path_object_rows=[],
            candidate_profiles=[
                _candidate_profile(
                    "wrong_outcome",
                    target_outcome_id="real_gdp_level_response",
                    coefficient_admission_status=(
                        "admitted_curve_denominator_response_coefficient"
                    ),
                    coefficient_source_status="reviewed_econometric_estimate_profile",
                )
            ],
        )


def test_selected_profile_rejects_multiple_admitted_profiles() -> None:
    rows = denominator_response_coefficient_profile_rows(
        diagnostic_rows=[],
        path_object_rows=[],
        candidate_profiles=[
            _candidate_profile(
                "a",
                denominator_response_coefficient="0.1",
                coefficient_admission_status=(
                    "admitted_curve_denominator_response_coefficient"
                ),
                coefficient_source_status="reviewed_econometric_estimate_profile",
            ),
            _candidate_profile(
                "b",
                coefficient_admission_status=(
                    "admitted_curve_denominator_response_coefficient"
                ),
                coefficient_source_status="reviewed_econometric_estimate_profile",
            ),
        ],
    )

    with pytest.raises(DenominatorResponseCoefficientError, match="found 2"):
        selected_denominator_response_coefficient_profile(rows)


def test_profile_rejects_unsupported_unit() -> None:
    with pytest.raises(DenominatorResponseCoefficientError, match="unsupported"):
        denominator_response_coefficient_profile_rows(
            diagnostic_rows=[],
            path_object_rows=[],
            candidate_profiles=[
                {
                    "denominator_response_profile_id": "bad_unit",
                    "denominator_response_coefficient": "0.2",
                    "denominator_response_coefficient_unit": "pp_gdp_per_100bp",
                    "coefficient_admission_status": (
                        "admitted_curve_denominator_response_coefficient"
                    ),
                    "coefficient_source_status": "reviewed_econometric_estimate_profile",
                }
            ],
        )


def _diagnostic(*, ci_low: str, ci_high: str) -> dict[str, str]:
    return {
        "horizon_q": "4",
        "outcome_object_id": "share_weighted_real_fspdp_level_response_gdp_share_pp",
        "ci95_low_hac": ci_low,
        "ci95_high_hac": ci_high,
    }


def _path_object(*, admitted: bool) -> dict[str, str]:
    if admitted:
        return {
            "normalization_status": "pass_reviewed_100bp_year_path",
            "admission_status": "admitted_path_object",
        }
    return {
        "normalization_status": "pass_assumption_mode_100bp_year_curve_path_not_empirical",
        "admission_status": "assumption_path_only_not_empirical",
    }


def _candidate_profile(
    profile_id: str = "curve_response_profile::reviewed",
    **overrides: str,
) -> dict[str, str]:
    row = {
        "denominator_response_profile_id": profile_id,
        "denominator_response_coefficient": "0.2",
        "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
        "coefficient_admission_status": "candidate_not_admitted",
        "coefficient_source_status": "candidate_profile_review_only",
        "coefficient_source_id": "source::reviewed-benchmark",
        "shock_family": "effective_curve_5y10y30y_100bp_year",
        "path_construction": "0.25*UST5Y+0.50*UST10Y+0.25*UST30Y",
        "tenor_weights": "5y=0.25;10y=0.50;30y=0.25",
        "horizon_integration": "annual_h4_one_year_bps_year",
        "source_estimate": "-0.2",
        "source_estimate_unit": "pp_gdp_per_100bp_year",
        "source_sample": "documented_test_sample",
        "coefficient_uncertainty": "ci95=[-0.3,-0.1]",
        "sign_convention": (
            "positive_effective_curve_overlay_is_contractionary_and_increases_D"
        ),
        "fspdp_gdp_to_d_conversion": "c_D=-beta_ppGDP_per_100bp_year/D_share_pp",
    }
    row.update(overrides)
    return row
