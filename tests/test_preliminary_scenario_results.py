from __future__ import annotations

from decimal import Decimal

from ratewall.databook.preliminary_scenario_results import (
    FRBUS_STRUCTURAL_TERM_PREMIUM_BENCHMARK_LABEL,
    PRELIMINARY_SCENARIO_RESULT_FIELDS,
    central_rate_components_svg,
    economist_readout_markdown,
    frozen_vs_moving_ratewall_svg,
    path_to_delta_d_svg,
    preliminary_scenario_result_rows,
    selected_delta_ratewall_svg,
    write_preliminary_scenario_outputs,
)


def test_preliminary_rows_carry_selected_frbus_moving_d() -> None:
    rows = preliminary_scenario_result_rows(
        summary_rows=_summary_rows(),
        synthesis_rows=_synthesis_rows(),
        materiality_rows=_materiality_rows(),
    )

    assert {field for row in rows for field in row} == set(
        PRELIMINARY_SCENARIO_RESULT_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    baseline = by_scenario["cbo_baseline_noop_v1"]
    assert baseline["selected_denominator_response_label"] == (
        FRBUS_STRUCTURAL_TERM_PREMIUM_BENCHMARK_LABEL
    )
    assert baseline["selected_denominator_response_coefficient"] == (
        "1.1198692004749646"
    )
    assert baseline["selected_wall_hit_status"] == "no_hit"
    assert baseline["canonical_ratio_entry"] == "false"
    assert baseline["evidence_mode_enabled"] == "false"
    assert baseline["denominator_prior_update_allowed"] == "false"

    shorter = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]
    assert shorter["path_bps_year"] == "-7"
    assert shorter["selected_delta_denominator_bil"].startswith(
        "-9.892886525930589"
    )
    assert shorter["selected_moving_denominator_bil"].startswith(
        "116.30662883755712"
    )
    assert shorter["moving_minus_frozen_ratewall_ratio"] != "0"
    assert shorter["model_relevance_class"] == (
        "less_than_quarter_primary_deficit_up_1pct;point_calibration_only"
    )
    assert Decimal(shorter["total_current_demand_support_bil"]) == (
        Decimal(shorter["selected_moving_ratewall_ratio"])
        * Decimal(shorter["selected_moving_denominator_bil"])
    )


def test_preliminary_visuals_and_readout_are_generated(tmp_path) -> None:
    rows = preliminary_scenario_result_rows(
        summary_rows=_summary_rows(),
        synthesis_rows=_synthesis_rows(),
        materiality_rows=_materiality_rows(),
    )

    assert "Selected FRB/US moving-D" in selected_delta_ratewall_svg(rows)
    assert "Frozen vs selected moving RateWall" in frozen_vs_moving_ratewall_svg(rows)
    assert "Curve path to selected delta D" in path_to_delta_d_svg(rows)
    assert "Central rate scenario components" in central_rate_components_svg(rows)

    readout = economist_readout_markdown(rows)
    assert "RateWall is `RW = N / D`" in readout
    assert "c_D=1.1198692004749646" in readout
    assert "not local econometric evidence" in readout

    outputs = write_preliminary_scenario_outputs(tmp_path, rows=rows)
    assert outputs["csv"].read_text(encoding="utf-8").startswith(
        "preliminary_scenario_result_row_id,"
    )
    assert outputs["readout_md"].read_text(encoding="utf-8") == readout
    assert outputs["ranking_svg"].exists()
    assert outputs["bridge_svg"].exists()
    assert outputs["scatter_svg"].exists()
    assert outputs["components_svg"].exists()


def _summary_rows() -> list[dict[str, str]]:
    base = {
        "fiscal_year": "2027",
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "term_premium_tier": "",
        "ten_year_nominal_rate_shock_bp": "0",
        "delta_tdc_current_demand_support_bil": "0",
        "delta_direct_treasury_current_demand_support_bil": "0",
        "delta_bank_treasury_current_demand_support_bil": "0",
        "component_delta_sum_check_bil": "0",
        "component_delta_sum_status": "pass_components_sum_to_total_support_delta",
        "tdc_delta_abs_contribution_share": "0",
        "direct_treasury_delta_abs_contribution_share": "0",
        "bank_treasury_delta_abs_contribution_share": "0",
        "support_mechanism_profile": "baseline",
        "rate_overlay_delta_ratewall_ratio": "0",
        "offset_fraction_of_abs_issuance_effect": "",
        "primary_deficit_up_1pct_delta_ratewall_ratio": "0.1",
        "abs_delta_vs_primary_deficit_up_1pct": "0",
        "dominant_delta_support_component": "none",
        "dominant_delta_support_component_bil": "0",
        "allowed_use": "test",
        "blocked_use": "canonical_headline_promotion",
        "canonical_ratio_entry": "false",
    }
    return [
        {
            **base,
            "tdcsim_cbo_model_scenario_summary_row_id": "summary::baseline",
            "summary_role": "baseline_anchor",
            "comparison_group": "baseline",
            "scenario_id": "cbo_baseline_noop_v1",
            "paired_issuance_only_scenario_id": "",
            "level_ratewall_ratio": "0.2247127655840447839105904186",
            "delta_ratewall_ratio_vs_baseline": "0",
            "delta_total_current_demand_support_bil": "0",
            "model_interpretation": "baseline_anchor_no_delta",
        },
        {
            **base,
            "tdcsim_cbo_model_scenario_summary_row_id": "summary::shorter",
            "summary_role": "issuance_rate_overlay",
            "comparison_group": "issuance_duration",
            "scenario_id": (
                "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
            ),
            "paired_issuance_only_scenario_id": (
                "tdcsim_issuance_empirical_shorter_uncoupled_v1"
            ),
            "term_premium_tier": "central",
            "level_ratewall_ratio": "0.2278047973963986765422176778",
            "delta_ratewall_ratio_vs_baseline": "0.0030920318123538926316272592",
            "delta_total_current_demand_support_bil": "1",
            "delta_tdc_current_demand_support_bil": "1.2",
            "delta_direct_treasury_current_demand_support_bil": "-0.2",
            "support_mechanism_profile": "mixed_support",
            "dominant_delta_support_component": "tdc",
            "dominant_delta_support_component_bil": "1.2",
            "model_interpretation": "shorter_issuance_plus_rate_down",
        },
    ]


def _synthesis_rows() -> list[dict[str, str]]:
    base = {
        "source_model_scenario_summary_row_id": "summary::x",
        "source_beta_chi_sign_stability_row_id": "beta::x",
        "fiscal_year": "2027",
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "paired_issuance_only_scenario_id": "",
        "term_premium_tier": "",
        "point_calibration_sign": "positive",
        "point_calibration_level_ratewall_ratio": "0.2247127655840447839105904186",
        "beta_chi_sign_stability_status": "mixed_sign",
        "beta_chi_signs_observed": "negative;positive",
        "beta_chi_min_delta_ratewall_ratio": "-0.01",
        "beta_chi_max_delta_ratewall_ratio": "0.02",
        "beta_chi_wall_hit_any_grid_cell": "false",
        "denominator_bound_theta_values": "0;0.125;0.25",
        "denominator_bound_min_delta_denominator_bil": "-1",
        "denominator_bound_max_delta_denominator_bil": "0",
        "denominator_bound_min_moving_delta_ratewall_ratio_vs_baseline": "-0.01",
        "denominator_bound_max_moving_delta_ratewall_ratio_vs_baseline": "0.01",
        "denominator_bound_signs_observed": "negative;positive",
        "denominator_bound_sign_stability_status": "denominator_bounds_mixed_sign",
        "primary_deficit_up_1pct_delta_ratewall_ratio": "0.1",
        "abs_delta_vs_primary_deficit_up_1pct": "0.1",
        "primary_deficit_scale_bucket": "less_than_quarter_primary_deficit_up_1pct",
        "dominant_delta_support_component": "tdc",
        "dominant_delta_support_component_bil": "1.2",
        "component_delta_sum_check_bil": "0",
        "component_delta_sum_status": "pass_components_sum_to_total_support_delta",
        "tdc_delta_abs_contribution_share": "0.6",
        "direct_treasury_delta_abs_contribution_share": "0.4",
        "bank_treasury_delta_abs_contribution_share": "0",
        "support_mechanism_profile": "mixed_support",
        "model_interpretation": "test",
        "final_interpretation": "point_calibration_not_beta_chi_sign_robust",
        "allowed_use": "test",
        "blocked_use": "canonical_headline_promotion",
        "claim_boundary": "test",
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
        "selected_denominator_response_profile_id": (
            "curve_denominator_response::frbus_structural_term_premium_h4_20260627"
        ),
        "selected_denominator_response_coefficient": "1.1198692004749646",
        "selected_denominator_response_coefficient_unit": (
            "fraction_of_frozen_denominator_per_100bp_year"
        ),
    }
    return [
        {
            **base,
            "tdcsim_cbo_model_scenario_interpretation_synthesis_row_id": (
                "synthesis::baseline"
            ),
            "summary_role": "baseline_anchor",
            "comparison_group": "baseline",
            "scenario_id": "cbo_baseline_noop_v1",
            "curve_effective_overlay_bp": "0",
            "point_calibration_delta_ratewall_ratio": "0",
            "selected_delta_denominator_bil": "0",
            "selected_moving_denominator_bil": "126.1995153634877105572719155",
            "selected_moving_ratewall_ratio": "0.2247127655840447839105904186",
            "selected_moving_delta_ratewall_ratio_vs_baseline": "0",
            "selected_denominator_response_status": "zero_rate_path_frozen_D_consistent",
        },
        {
            **base,
            "tdcsim_cbo_model_scenario_interpretation_synthesis_row_id": (
                "synthesis::shorter"
            ),
            "summary_role": "issuance_rate_overlay",
            "comparison_group": "issuance_duration",
            "scenario_id": (
                "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
            ),
            "paired_issuance_only_scenario_id": (
                "tdcsim_issuance_empirical_shorter_uncoupled_v1"
            ),
            "term_premium_tier": "central",
            "curve_effective_overlay_bp": "-7",
            "point_calibration_delta_ratewall_ratio": "0.0030920318123538926316272592",
            "selected_delta_denominator_bil": "-9.892886525930589577649151444",
            "selected_moving_denominator_bil": "116.3066288375571209796227641",
            "selected_moving_ratewall_ratio": "0.2475764520491533491554773336",
            "selected_moving_delta_ratewall_ratio_vs_baseline": (
                "0.0197716548728518143420056191"
            ),
            "selected_denominator_response_status": (
                "pass_moving_D_computed_from_admitted_profile"
            ),
        },
    ]


def _materiality_rows() -> list[dict[str, str]]:
    return [
        {
            "scenario_id": "cbo_baseline_noop_v1",
            "fiscal_year": "2027",
            "scenario_family": "baseline",
            "model_relevance_class": "baseline_anchor",
            "recommended_use": "baseline_reference_only",
        },
        {
            "scenario_id": (
                "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
            ),
            "fiscal_year": "2027",
            "scenario_family": "issuance_duration",
            "model_relevance_class": (
                "less_than_quarter_primary_deficit_up_1pct;point_calibration_only"
            ),
            "recommended_use": "scenario_mode_interpretation_only_not_canonical",
        },
    ]
