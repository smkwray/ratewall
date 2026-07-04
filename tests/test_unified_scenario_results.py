from __future__ import annotations

import csv
import json
from pathlib import Path

from ratewall.databook.unified_scenario_results import (
    COMBINED_SCENARIO_GATE_IDS,
    UNIFIED_SCENARIO_MODEL_DECISION_FIELDS,
    UNIFIED_SCENARIO_RESULT_FIELDS,
    apply_moving_d_beta_chi_claim_gate,
    unified_scenario_model_decision_rows,
    unified_scenario_model_memo_markdown,
    unified_scenario_readout_markdown,
    unified_scenario_result_rows,
    unified_scenario_result_rows_from_directory,
    write_unified_scenario_outputs,
)


def test_unified_rows_recompute_moving_d_and_gate_combined_rows() -> None:
    rows = unified_scenario_result_rows(
        summary_rows=_summary_rows(),
        effect_rows=_effect_rows(),
        ratio_rows=_ratio_rows(),
        curve_rows=_curve_rows(),
        beta_chi_rows=_beta_chi_rows(),
        materiality_rows=_materiality_rows(),
        scenario_payloads=_scenario_payloads(),
    )

    assert {field for row in rows for field in row} == set(
        UNIFIED_SCENARIO_RESULT_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}

    baseline = by_scenario["cbo_baseline_noop_v1"]
    assert baseline["scenario_axis"] == "baseline"
    assert baseline["selected_delta_denominator_bil"] == "0"
    assert baseline["selected_moving_delta_ratewall_ratio_vs_baseline"] == "0"

    holder = by_scenario["tdcsim_holder_source_reserve_user_absorption_v1"]
    assert holder["scenario_axis"] == "holder_only"
    assert holder["holder_preferences_change"] == "true"
    assert holder["rate_path_changes"] == "false"
    assert holder["selected_delta_denominator_bil"] == "0"
    assert float(holder["selected_moving_ratewall_ratio"]) == float(
        holder["frozen_ratewall_ratio"]
    )

    rate = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]
    assert rate["scenario_axis"] == "rate_or_issuance_rate"
    assert rate["path_bps_year"] == "-7"
    assert rate["selected_delta_denominator_bil"] == "-7.8390844033247522"
    assert rate["selected_denominator_response_status"] == (
        "pass_moving_D_computed_from_admitted_profile"
    )
    assert rate["source_beta_chi_sign_stability_status"] == "mixed_sign"
    assert rate["moving_d_beta_chi_sign_stability_status"] == (
        "not_evaluated_run_beta_chi_claim_gate"
    )

    combined = by_scenario["tdcsim_combo_high_pressure_v1"]
    assert combined["scenario_axis"] == "combined_holder_rate"
    assert combined["holder_preferences_change"] == "true"
    assert combined["rate_path_changes"] == "true"
    assert combined["combined_holder_rate_gate_status"] == (
        "pass_combined_holder_rate_same_run_gate"
    )
    assert combined["selected_moving_delta_ratewall_ratio_vs_baseline"] != (
        combined["frozen_delta_ratewall_ratio_vs_baseline"]
    )


def test_unified_model_decisions_separate_carry_forward_and_checks() -> None:
    rows = unified_scenario_result_rows(
        summary_rows=_summary_rows(),
        effect_rows=_effect_rows(),
        ratio_rows=_ratio_rows(),
        curve_rows=_curve_rows(),
        beta_chi_rows=_beta_chi_rows(),
        materiality_rows=_materiality_rows(),
        scenario_payloads=_scenario_payloads(),
    )

    decisions = unified_scenario_model_decision_rows(rows)

    assert {field for row in decisions for field in row} == set(
        UNIFIED_SCENARIO_MODEL_DECISION_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in decisions}
    assert by_scenario["cbo_baseline_noop_v1"]["carry_forward_status"] == (
        "baseline_reference"
    )
    assert by_scenario["tdcsim_holder_source_reserve_user_absorption_v1"][
        "carry_forward_status"
    ] == "carry_forward_main_holder_tdc_scenario_family"
    assert by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]["carry_forward_status"] == (
        "carry_forward_main_rate_denominator_scenario_family"
    )
    assert by_scenario["tdcsim_combo_high_pressure_v1"][
        "carry_forward_status"
    ] == "carry_forward_main_combined_scenario_family"
    assert all(
        row["canonical_promotion_status"]
        == "blocked_scenario_mode_only_without_owner_gate"
        for row in decisions
    )
    assert by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]["model_gap"] == (
        "moving_D_profile_is_final_structural_assumption_mode_not_empirical_same_axis"
    )
    assert by_scenario["tdcsim_holder_source_reserve_user_absorption_v1"][
        "model_gap"
    ] == "beta_chi_range_mixed_sign_requires_assumption_label_or_narrower_gate"


def test_unified_decisions_use_moving_d_beta_chi_claim_gate_status() -> None:
    rows = unified_scenario_result_rows(
        summary_rows=_summary_rows(),
        effect_rows=_effect_rows(),
        ratio_rows=_ratio_rows(),
        curve_rows=_curve_rows(),
        beta_chi_rows=_beta_chi_rows(),
        materiality_rows=_materiality_rows(),
        scenario_payloads=_scenario_payloads(),
    )

    enriched = apply_moving_d_beta_chi_claim_gate(rows, _claim_gate_rows())
    decisions = unified_scenario_model_decision_rows(enriched)

    by_scenario = {row["scenario_id"]: row for row in decisions}
    rate = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]
    assert rate["source_beta_chi_sign_stability_status"] == "mixed_sign"
    assert rate["moving_d_beta_chi_sign_stability_status"] == "stable_positive"
    assert rate["moving_d_beta_chi_claim_strength_status"] == (
        "sign_robust_over_existing_beta_chi_grid"
    )
    assert rate["model_gap"] == (
        "moving_D_profile_is_final_structural_assumption_mode_not_empirical_same_axis"
    )
    combo = by_scenario["tdcsim_combo_high_pressure_v1"]
    assert combo["source_beta_chi_sign_stability_status"] == "mixed_sign"
    assert combo["moving_d_beta_chi_sign_stability_status"] == "stable_positive"
    assert combo["model_gap"] == (
        "combined_assumption_scenario_requires_owner_gate_for_headline_use"
    )
    holder = by_scenario["tdcsim_holder_source_reserve_user_absorption_v1"]
    assert holder["moving_d_beta_chi_sign_stability_status"] == "mixed_sign"
    assert holder["model_gap"] == (
        "beta_chi_range_mixed_sign_requires_assumption_label_or_narrower_gate"
    )


def test_unified_rows_read_manifest_root_tables(tmp_path: Path) -> None:
    _write_suite(tmp_path)

    rows = unified_scenario_result_rows_from_directory(tmp_path)

    assert len(rows) == 5
    by_scenario = {row["scenario_id"]: row for row in rows}
    assert by_scenario["tdcsim_combo_high_pressure_v1"][
        "combined_holder_rate_gate_status"
    ] == "pass_combined_holder_rate_same_run_gate"


def test_unified_outputs_write_png_csv_and_readout(tmp_path: Path) -> None:
    rows = unified_scenario_result_rows(
        summary_rows=_summary_rows(),
        effect_rows=_effect_rows(),
        ratio_rows=_ratio_rows(),
        curve_rows=_curve_rows(),
        beta_chi_rows=_beta_chi_rows(),
        materiality_rows=_materiality_rows(),
        scenario_payloads=_scenario_payloads(),
    )

    outputs = write_unified_scenario_outputs(tmp_path / "out", rows=rows)

    assert outputs["csv"].read_text(encoding="utf-8").startswith(
        "unified_scenario_result_row_id,"
    )
    readout = unified_scenario_readout_markdown(rows)
    assert outputs["readout_md"].read_text(encoding="utf-8") == readout
    assert "Recomputes moving `D`" in readout
    assert "tdcsim_combo_high_pressure_v1" in readout
    memo = unified_scenario_model_memo_markdown(rows)
    assert outputs["model_memo_md"].read_text(encoding="utf-8") == memo
    assert "holder-allocation/TDC scenarios are large" in memo
    assert "No row is promoted into the canonical headline result" in memo
    assert outputs["decision_csv"].read_text(encoding="utf-8").startswith(
        "unified_scenario_model_decision_row_id,"
    )
    for key in (
        "png_delta_rw",
        "png_frozen_moving",
        "png_components",
        "png_combined",
    ):
        assert outputs[key].read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def _summary_rows() -> list[dict[str, str]]:
    return [
        _summary_row("cbo_baseline_noop_v1", "baseline_anchor", "baseline", "0.20", "0"),
        _summary_row(
            "tdcsim_holder_source_reserve_user_absorption_v1",
            "holder_preference_comparator",
            "holder_preference",
            "0.50",
            "0.30",
        ),
        _summary_row(
            "tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            "coupled_central_empirical_scenario",
            "shorter_issuance",
            "0.21",
            "0.01",
            term_premium_tier="central",
            paired="tdcsim_issuance_empirical_shorter_uncoupled_v1",
            ten_year_shock="-8",
        ),
        _summary_row(
            "tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            "coupled_central_empirical_scenario",
            "longer_issuance",
            "0.19",
            "-0.01",
            term_premium_tier="central",
            paired="tdcsim_issuance_empirical_longer_uncoupled_v1",
            ten_year_shock="8",
        ),
        _summary_row(
            "tdcsim_combo_high_pressure_v1",
            "combined_narrative_scenario",
            "combined_narrative",
            "0.55",
            "0.35",
            paired="tdcsim_issuance_empirical_shorter_uncoupled_v1",
            ten_year_shock="-8",
        ),
    ]


def _summary_row(
    scenario_id: str,
    role: str,
    group: str,
    rw: str,
    delta_rw: str,
    *,
    term_premium_tier: str = "none",
    paired: str = "",
    ten_year_shock: str = "0",
) -> dict[str, str]:
    return {
        "tdcsim_cbo_model_scenario_summary_row_id": f"summary::{scenario_id}",
        "fiscal_year": "2027",
        "summary_role": role,
        "comparison_group": group,
        "scenario_id": scenario_id,
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "paired_issuance_only_scenario_id": paired,
        "term_premium_tier": term_premium_tier,
        "ten_year_nominal_rate_shock_bp": ten_year_shock,
        "level_ratewall_ratio": rw,
        "delta_ratewall_ratio_vs_baseline": delta_rw,
        "delta_total_current_demand_support_bil": "10" if delta_rw != "0" else "0",
        "delta_tdc_current_demand_support_bil": "8" if delta_rw != "0" else "0",
        "delta_direct_treasury_current_demand_support_bil": "1",
        "delta_bank_treasury_current_demand_support_bil": "1",
        "component_delta_sum_check_bil": "0",
        "component_delta_sum_status": "pass_components_sum_to_total_support_delta",
        "tdc_delta_abs_contribution_share": "0.8",
        "direct_treasury_delta_abs_contribution_share": "0.1",
        "bank_treasury_delta_abs_contribution_share": "0.1",
        "support_mechanism_profile": "tdc_dominant",
        "rate_overlay_delta_ratewall_ratio": "0",
        "offset_fraction_of_abs_issuance_effect": "",
        "primary_deficit_up_1pct_delta_ratewall_ratio": "0.1",
        "abs_delta_vs_primary_deficit_up_1pct": "1",
        "dominant_delta_support_component": "tdc",
        "dominant_delta_support_component_bil": "8",
        "model_interpretation": scenario_id.replace("_v1", ""),
        "allowed_use": "test",
        "blocked_use": "canonical_headline_promotion",
        "canonical_ratio_entry": "false",
    }


def _effect_rows() -> list[dict[str, str]]:
    return [
        _effect_row("cbo_baseline_noop_v1", "20", "0.20", "0"),
        _effect_row("tdcsim_holder_source_reserve_user_absorption_v1", "50", "0.50", "30"),
        _effect_row(
            "tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            "21",
            "0.21",
            "1",
        ),
        _effect_row(
            "tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            "19",
            "0.19",
            "-1",
        ),
        _effect_row("tdcsim_combo_high_pressure_v1", "55", "0.55", "35"),
    ]


def _effect_row(
    scenario_id: str,
    support: str,
    rw: str,
    delta_support: str,
) -> dict[str, str]:
    return {
        "tdcsim_cbo_scenario_effect_row_id": f"effect::{scenario_id}",
        "scenario_id": scenario_id,
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "fiscal_year": "2027",
        "level_ratewall_ratio": rw,
        "delta_ratewall_ratio_vs_baseline": "0" if scenario_id == "cbo_baseline_noop_v1" else "0.1",
        "total_current_demand_support_bil": support,
        "delta_total_current_demand_support_bil": delta_support,
        "tdc_current_demand_support_bil": support,
        "delta_tdc_current_demand_support_bil": delta_support,
        "direct_treasury_current_demand_support_bil": "1",
        "delta_direct_treasury_current_demand_support_bil": "1",
        "bank_treasury_current_demand_support_bil": "1",
        "delta_bank_treasury_current_demand_support_bil": "1",
        "frozen_denominator_bil": "100",
    }


def _ratio_rows() -> list[dict[str, str]]:
    return [
        {
            "scenario_id": row["scenario_id"],
            "fiscal_year": "2027",
            "mmf_deposit_pass_through": "0.97",
        }
        for row in _summary_rows()
    ]


def _curve_rows() -> list[dict[str, str]]:
    return [
        _curve_row("cbo_baseline_noop_v1", "0"),
        _curve_row("tdcsim_holder_source_reserve_user_absorption_v1", "0"),
        _curve_row(
            "tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            "-7",
        ),
        _curve_row(
            "tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            "7",
        ),
        _curve_row("tdcsim_combo_high_pressure_v1", "-7"),
    ]


def _curve_row(scenario_id: str, path: str) -> dict[str, str]:
    return {
        "tdcsim_cbo_curve_denominator_input_row_id": f"curve::{scenario_id}",
        "scenario_id": scenario_id,
        "baseline_scenario_id": "cbo_baseline_noop_v1",
        "fiscal_year": "2027",
        "effective_curve_overlay_bp": path,
        "curve_overlay_5y_bp": path,
        "curve_overlay_10y_bp": path,
        "curve_overlay_30y_bp": path,
        "frozen_denominator_bil": "100",
        "total_current_demand_support_bil": {
            "cbo_baseline_noop_v1": "20",
            "tdcsim_holder_source_reserve_user_absorption_v1": "50",
            "tdcsim_issuance_empirical_shorter_termprem_down_central_v1": "21",
            "tdcsim_issuance_empirical_longer_termprem_up_central_v1": "19",
            "tdcsim_combo_high_pressure_v1": "55",
        }[scenario_id],
        "frozen_ratewall_ratio": {
            "cbo_baseline_noop_v1": "0.20",
            "tdcsim_holder_source_reserve_user_absorption_v1": "0.50",
            "tdcsim_issuance_empirical_shorter_termprem_down_central_v1": "0.21",
            "tdcsim_issuance_empirical_longer_termprem_up_central_v1": "0.19",
            "tdcsim_combo_high_pressure_v1": "0.55",
        }[scenario_id],
        "frozen_delta_ratewall_ratio_vs_baseline": {
            "cbo_baseline_noop_v1": "0",
            "tdcsim_holder_source_reserve_user_absorption_v1": "0.30",
            "tdcsim_issuance_empirical_shorter_termprem_down_central_v1": "0.01",
            "tdcsim_issuance_empirical_longer_termprem_up_central_v1": "-0.01",
            "tdcsim_combo_high_pressure_v1": "0.35",
        }[scenario_id],
    }


def _beta_chi_rows() -> list[dict[str, str]]:
    return [
        {
            "scenario_id": row["scenario_id"],
            "fiscal_year": "2027",
            "sign_stability_status": "mixed_sign",
            "min_delta_ratewall_ratio_over_beta_chi_grid": "-0.01",
            "max_delta_ratewall_ratio_over_beta_chi_grid": "0.40",
        }
        for row in _summary_rows()
    ]


def _claim_gate_rows() -> list[dict[str, str]]:
    stable_rate_rows = {
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
        "tdcsim_issuance_empirical_longer_termprem_up_central_v1",
        "tdcsim_combo_high_pressure_v1",
    }
    return [
        {
            "scenario_id": row["scenario_id"],
            "fiscal_year": "2027",
            "moving_d_beta_chi_sign_stability_status": "stable_positive"
            if row["scenario_id"] in stable_rate_rows
            else "mixed_sign",
            "claim_strength_status": "sign_robust_over_existing_beta_chi_grid"
            if row["scenario_id"] in stable_rate_rows
            else "point_calibrated_only_mixed_sign_over_existing_grid",
        }
        for row in _summary_rows()
    ]


def _materiality_rows() -> list[dict[str, str]]:
    return [
        {
            "scenario_id": row["scenario_id"],
            "fiscal_year": "2027",
            "scenario_family": "baseline"
            if row["scenario_id"] == "cbo_baseline_noop_v1"
            else "composite_assumption"
            if row["scenario_id"] in COMBINED_SCENARIO_GATE_IDS
            else "single_channel_assumption",
            "model_relevance_class": "test_relevance",
            "recommended_use": "test_readout",
        }
        for row in _summary_rows()
    ]


def _scenario_payloads() -> dict[str, dict[str, object]]:
    return {
        "cbo_baseline_noop_v1": _scenario_payload("cbo_baseline_noop_v1"),
        "tdcsim_holder_source_reserve_user_absorption_v1": _scenario_payload(
            "tdcsim_holder_source_reserve_user_absorption_v1",
            holder=True,
        ),
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1": _scenario_payload(
            "tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            curve=True,
        ),
        "tdcsim_issuance_empirical_longer_termprem_up_central_v1": _scenario_payload(
            "tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            curve=True,
        ),
        "tdcsim_combo_high_pressure_v1": _scenario_payload(
            "tdcsim_combo_high_pressure_v1",
            holder=True,
            curve=True,
        ),
    }


def _scenario_payload(
    scenario_id: str,
    *,
    holder: bool = False,
    curve: bool = False,
) -> dict[str, object]:
    overrides: dict[str, object] = {}
    if holder:
        overrides["holder_preferences"] = {
            "rows": [{"security_type": "notes", "shares": {"Banks": 0.2}}]
        }
    if curve:
        overrides["nominal_yield_curve"] = {
            "mode": "key_rate_bp",
            "shocks": [
                {"tenor_years": 5, "shock_bp": -4},
                {"tenor_years": 10, "shock_bp": -8},
                {"tenor_years": 30, "shock_bp": -8},
            ],
        }
    return {
        "scenario_id": scenario_id,
        "title": scenario_id,
        "overrides": overrides,
    }


def _write_suite(root: Path) -> None:
    _write_csv(root / "ratewall_tdcsim_cbo_model_scenario_summary.csv", _summary_rows())
    _write_csv(root / "ratewall_tdcsim_cbo_scenario_effect.csv", _effect_rows())
    _write_csv(root / "ratewall_tdcsim_cbo_fiscal_year_ratio_input.csv", _ratio_rows())
    _write_csv(root / "ratewall_tdcsim_cbo_curve_denominator_input.csv", _curve_rows())
    _write_csv(
        root / "ratewall_tdcsim_cbo_model_scenario_beta_chi_sign_stability.csv",
        _beta_chi_rows(),
    )
    _write_csv(
        root / "ratewall_tdcsim_cbo_model_scenario_materiality_classification.csv",
        _materiality_rows(),
    )
    scenario_dir = root / "scenarios"
    scenario_dir.mkdir()
    for scenario_id, payload in _scenario_payloads().items():
        (scenario_dir / f"{scenario_id}.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
