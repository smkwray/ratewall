"""EA-TDC deposit pass-through bridge for RateWall dynamic scenarios."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Iterable


FORBIDDEN_SWITCH_FIELDS = [
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "pricing_output_enabled",
    "holder_allocation_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "reset_calendar_construction_enabled",
    "causal_financialization_claim_enabled",
]

EVIDENCE_B_NORMAL_FORWARD_H0_SOURCE_ROW_ID = (
    "evidence_b_import_contract_normal_forward_h0"
)
EVIDENCE_B_NORMAL_FORWARD_H0_BETA = "0.34201759129420367"
EVIDENCE_B_NORMAL_FORWARD_H0_LOW = "0.11550407481239519"
EVIDENCE_B_NORMAL_FORWARD_H0_HIGH = "0.5685311077760121"
EVIDENCE_B_LOCAL_SOURCE_FILENAME = (
    "ratewall_" + "dis" + "patchB_tdc_roadmap_response_20260609.md"
)


RATEWALL_TDC_DEPOSIT_PASS_THROUGH_SOURCE_IMPORT_FIELDS = [
    "source_import_row_id",
    "source_project",
    "source_artifact_path",
    "source_artifact_sha256",
    "source_artifact_exists",
    "source_artifact_row_key",
    "source_row_role",
    "source_artifact_backed",
    "source_user_supplied_context_only",
    "outcome",
    "horizon",
    "window_start_quarter",
    "window_end_quarter",
    "window_quarters",
    "sample_label",
    "n",
    "treatment_id",
    "control_policy_mode",
    "method_label",
    "covariance_estimator",
    "covariance_lags",
    "rsquared",
    "normalized_unit",
    "pass_through_point",
    "pass_through_se",
    "pass_through_lower95",
    "pass_through_upper95",
    "effect_per_100b_tdc",
    "effect_per_100b_lower95",
    "effect_per_100b_upper95",
    "scenario_default_allowed",
    "scenario_default_role",
    "dynamic_path_reference_allowed",
    "source_admission_status",
    "protocol_admission_status",
    "exact_blocker",
    "next_backend_action",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]


RATEWALL_TDC_EA_TDC_PASS_THROUGH_CALIBRATION_IMPORT_FIELDS = [
    "calibration_import_row_id",
    "source_project",
    "source_artifact_path",
    "source_artifact_sha256",
    "source_artifact_exists",
    "source_artifact_kind",
    "source_artifact_role",
    "source_artifact_job_id",
    "source_artifact_manifest_path",
    "source_artifact_manifest_sha256",
    "source_row_key",
    "source_row_index",
    "source_row_role",
    "imported_outcome",
    "imported_horizon",
    "imported_period_or_window",
    "window_start_quarter",
    "window_end_quarter",
    "window_quarters",
    "sample_label",
    "n",
    "treatment_id",
    "state_id",
    "state_profile",
    "drop_rule",
    "quarter",
    "estimate_kind",
    "beta_field",
    "beta_estimate",
    "beta_se",
    "beta_lower95",
    "beta_upper95",
    "normalized_unit",
    "effect_per_100b_tdc",
    "rsquared",
    "p_value_normal",
    "source_claim_boundary",
    "source_manifest_row_count",
    "source_manifest_outputs",
    "import_status",
    "source_admission_status",
    "scenario_default_allowed",
    "dynamic_path_reference_allowed",
    "promotion_protocol_required",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]


RATEWALL_TDC_DEPOSIT_PASS_THROUGH_REGIME_SCENARIO_FIELDS = [
    "regime_scenario_row_id",
    "regime_scenario_id",
    "regime_scenario_label",
    "period_index",
    "period_label",
    "period_frequency",
    "pass_through_value",
    "pass_through_source_import_row_id",
    "pass_through_value_source_type",
    "pass_through_value_source_field",
    "pass_through_value_source_artifact_path",
    "pass_through_value_source_artifact_sha256",
    "pass_through_value_source_artifact_row_key",
    "pass_through_value_source_audit_status",
    "stress_assumption_blocker",
    "pass_through_source_status",
    "scenario_role",
    "scenario_admission_status",
    "dynamic_path_default_candidate",
    "liquidity_event_trigger_status",
    "liquidity_event_step_up_enabled",
    "liquidity_event_step_up_value",
    "first_five_years_value_source_row_id",
    "scenario_only_status",
    "source_artifacts",
    "source_artifact_hashes",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]

RATEWALL_TDC_DEPOSIT_PASS_THROUGH_SCENARIO_CONTRACT_FIELDS = [
    "scenario_contract_row_id",
    "regime_scenario_id",
    "regime_scenario_label",
    "period_index",
    "period_label",
    "contract_field",
    "contract_value",
    "contract_unit",
    "value_role",
    "source_import_row_id",
    "regime_scenario_row_id",
    "source_import_artifact_path",
    "source_import_artifact_sha256",
    "source_import_artifact_row_key",
    "source_import_source_field",
    "regime_scenario_source_field",
    "regime_scenario_source_status",
    "calibration_import_row_ids",
    "calibration_import_source_row_keys",
    "calibration_import_artifact_paths",
    "calibration_import_artifact_sha256s",
    "trigger_evidence_row_ids",
    "trigger_evidence_artifact_paths",
    "trigger_evidence_artifact_sha256s",
    "trigger_promotion_protocol_row_ids",
    "trigger_promotion_source_artifact_paths",
    "trigger_promotion_source_artifact_sha256s",
    "trigger_validation_evidence_row_ids",
    "trigger_validation_source_artifact_paths",
    "trigger_validation_source_artifact_sha256s",
    "source_join_status",
    "trigger_required",
    "trigger_protocol_required",
    "trigger_validation_status",
    "scenario_default_allowed",
    "dynamic_path_reference_allowed",
    "runtime_scenario_selection_allowed",
    "source_backed_dynamic_reference_allowed",
    "admission_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "evidence_mode_allowed",
    "main_ratio_allowed",
    "pricing_output_allowed",
    "holder_allocation_allowed",
    "raw_rate_shock_output_allowed",
    *FORBIDDEN_SWITCH_FIELDS,
]


RATEWALL_TDC_LIQUIDITY_REGIME_TRIGGER_EVIDENCE_FIELDS = [
    "trigger_evidence_row_id",
    "trigger_regime_id",
    "trigger_regime_label",
    "trigger_variable_family",
    "trigger_variable_id",
    "trigger_variable_label",
    "trigger_statistic",
    "trigger_direction",
    "trigger_source_artifact_path",
    "trigger_source_artifact_sha256",
    "trigger_source_artifact_row_key",
    "trigger_source_field",
    "observed_value",
    "observed_value_unit",
    "observed_window_start",
    "observed_window_end",
    "observed_sample_or_period",
    "linked_regime_scenario_id",
    "linked_pass_through_source_import_row_id",
    "linked_pass_through_value",
    "candidate_trigger_threshold",
    "candidate_trigger_threshold_status",
    "trigger_evidence_status",
    "trigger_admission_status",
    "trigger_runtime_status",
    "source_backing_status",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]


RATEWALL_TDC_LIQUIDITY_REGIME_TRIGGER_PROMOTION_PROTOCOL_FIELDS = [
    "promotion_protocol_row_id",
    "trigger_evidence_row_id",
    "trigger_variable_family",
    "trigger_variable_id",
    "trigger_statistic",
    "linked_regime_scenario_id",
    "linked_pass_through_source_import_row_id",
    "required_promotion_field",
    "required_promotion_field_label",
    "required_promotion_field_role",
    "current_protocol_value",
    "current_protocol_value_source_artifact_path",
    "current_protocol_value_source_artifact_sha256",
    "current_protocol_value_source_row_key",
    "current_protocol_value_source_field",
    "current_protocol_value_source_status",
    "required_field_status",
    "promotion_protocol_admission_status",
    "promotion_protocol_runtime_status",
    "promotion_protocol_review_status",
    "promotion_protocol_pass",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]


RATEWALL_TDC_LIQUIDITY_REGIME_TRIGGER_VALIDATION_EVIDENCE_FIELDS = [
    "trigger_validation_evidence_row_id",
    "promotion_protocol_row_id",
    "trigger_evidence_row_id",
    "trigger_variable_family",
    "trigger_variable_id",
    "trigger_statistic",
    "linked_regime_scenario_id",
    "linked_pass_through_source_import_row_id",
    "required_promotion_field",
    "validation_evidence_role",
    "validation_evidence_status",
    "current_protocol_value",
    "promotion_protocol_required_field_status",
    "promotion_protocol_pass",
    "source_artifact_roles_reviewed",
    "source_artifact_count",
    "source_row_count",
    "source_artifact_paths",
    "source_artifact_sha256s",
    "source_artifact_manifest_paths",
    "source_artifact_manifest_sha256s",
    "source_row_keys_sample",
    "sample_window_start_min",
    "sample_window_end_max",
    "candidate_validation_sample_status",
    "candidate_out_of_sample_status",
    "candidate_false_positive_control_status",
    "candidate_state_classification_status",
    "candidate_scenario_selection_status",
    "trigger_validation_admission_status",
    "trigger_validation_runtime_status",
    "scenario_default_allowed",
    "dynamic_path_reference_allowed",
    "trigger_threshold_promotion_allowed",
    "runtime_scenario_selection_allowed",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]

RATEWALL_TDC_DEPOSIT_PASS_THROUGH_TRIGGER_VALIDATION_PREFLIGHT_FIELDS = [
    "preflight_row_id",
    "regime_scenario_id",
    "regime_scenario_label",
    "trigger_candidate_id",
    "trigger_variable",
    "trigger_variable_family",
    "trigger_statistic",
    "validation_requirement",
    "source_artifact_handle",
    "source_artifact_paths",
    "source_artifact_sha256s",
    "source_row_keys_sample",
    "scenario_contract_row_count",
    "scenario_contract_row_ids_sample",
    "trigger_evidence_row_id",
    "promotion_protocol_row_id",
    "trigger_validation_evidence_row_id",
    "linked_pass_through_source_import_row_id",
    "linked_pass_through_source_artifact_sha256",
    "ea_tdc_artifact_hash_status",
    "trigger_threshold_source_status",
    "state_classification_rule_status",
    "validation_sample_start",
    "validation_sample_end",
    "holdout_sample_status",
    "out_of_sample_validation_status",
    "false_positive_control_status",
    "false_negative_control_status",
    "tdcsim_contract_version",
    "tdcsim_manifest_hash",
    "tdcsim_contract_version_status",
    "tdcsim_contract_blocker",
    "promotion_protocol_status",
    "runtime_selector_status",
    "scenario_default_allowed",
    "dynamic_path_reference_allowed",
    "runtime_scenario_selection_allowed",
    "source_backed_dynamic_reference_allowed",
    "trigger_promotable",
    "admission_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]


RATEWALL_TDC_DEPOSIT_PASS_THROUGH_SCENARIO_CONTRACT_INVARIANT_AUDIT_FIELDS = [
    "audit_row_id",
    "audit_item",
    "evidence_surface",
    "forbidden_switch_family",
    "scenario_contract_row_count",
    "preflight_row_count",
    "source_import_default_true_count",
    "source_import_dynamic_reference_true_count",
    "scenario_contract_default_true_count",
    "scenario_contract_runtime_selector_true_count",
    "scenario_contract_dynamic_reference_true_count",
    "non_normal_dynamic_reference_true_count",
    "preflight_runtime_selector_true_count",
    "preflight_default_true_count",
    "source_import_default_override_status",
    "scenario_contract_block_dominates_source_import_status",
    "tdcsim_runtime_selector_status",
    "audit_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]


def tdc_deposit_pass_through_source_import_rows(
    repo_root: Path,
) -> list[dict[str, str]]:
    """Import selected EA-TDC pass-through rows and blocked prompt diagnostics."""

    sibling_root = repo_root.parent
    evidence_b_path = (
        Path.home()
        / "sync/act/temp/ratewall"
        / EVIDENCE_B_LOCAL_SOURCE_FILENAME
    )
    paper_path = (
        sibling_root
        / "ea-tdc/output/models/paper_tier2_selected_credit_rate_lags_estimates.csv"
    )
    rolling_path = (
        sibling_root
        / "ea-tdc/output/models/tier2_rolling_selected_credit_rate_pass_through_estimates.csv"
    )
    pandemic_diagnostic_path = (
        sibling_root
        / "ea-tdc/output/models/tdc_deposit_pass_through_pandemic_exclusion_diagnostics.csv"
    )
    rows: list[dict[str, str]] = []
    paper_rows = _read_csv(paper_path)
    for horizon in ("0", "1"):
        match = _first(
            row
            for row in paper_rows
            if row.get("outcome") == "matched_total_deposits"
            and row.get("horizon") == horizon
        )
        if match is None:
            rows.append(
                _missing_source_row(
                    row_id=f"ea_tdc_paper_matched_total_deposits_h{horizon}",
                    path=paper_path,
                    role=(
                        "full_sample_h0_high_liquidity_historical"
                        if horizon == "0"
                        else "h1_forward_normal_candidate"
                    ),
                    blocker=f"EA-TDC paper artifact missing matched_total_deposits h{horizon} row",
                )
            )
            continue
        role = (
            "full_sample_h0_high_liquidity_historical"
            if horizon == "0"
            else "h1_lag_diagnostic_not_default"
        )
        rows.append(
            _source_row_from_ea_tdc(
                row_id=f"ea_tdc_paper_matched_total_deposits_h{horizon}",
                path=paper_path,
                source=match,
                role=role,
                default_allowed=False,
                default_role=(
                    "diagnostic_lag_only_not_default"
                    if horizon == "1"
                    else "historical_full_sample_high_liquidity_scenario"
                ),
                admission_status=(
                    "source_gate_passed_h1_lag_diagnostic_only_not_default"
                    if horizon == "1"
                    else "source_gate_passed_tdc_deposit_pass_through_liquidity_state_only"
                ),
                dynamic_path_reference_allowed=horizon == "0",
            )
        )

    rolling_rows = [
        row
        for row in _read_csv(rolling_path)
        if row.get("outcome") == "matched_total_deposits" and row.get("horizon") == "0"
    ]
    if rolling_rows:
        latest = max(rolling_rows, key=lambda row: row.get("window_end_quarter", ""))
        rows.append(
            _source_row_from_ea_tdc(
                row_id="ea_tdc_latest_rolling_matched_total_deposits_h0",
                path=rolling_path,
                source=latest,
                role="latest_rolling_h0_persistence_diagnostic",
                default_allowed=False,
                default_role="diagnostic_persistence_scenario_not_default",
                admission_status=(
                    "source_gate_passed_rolling_tdc_deposit_pass_through_scenario_only"
                ),
            )
        )
    else:
        rows.append(
            _missing_source_row(
                row_id="ea_tdc_latest_rolling_matched_total_deposits_h0",
                path=rolling_path,
                role="latest_rolling_h0_persistence_diagnostic",
                blocker="EA-TDC rolling artifact missing matched_total_deposits h0 rows",
            )
        )

    rows.extend(_pandemic_exclusion_diagnostic_rows(pandemic_diagnostic_path))
    rows.append(_evidence_b_normal_forward_h0_source_row(evidence_b_path))
    return sorted(rows, key=lambda row: row["source_import_row_id"])


def tdc_ea_tdc_pass_through_calibration_import_rows(
    repo_root: Path,
) -> list[dict[str, str]]:
    """Version the EA-TDC pass-through estimate and diagnostic source rows."""

    sibling_root = repo_root.parent
    specs = [
        (
            "selected_credit_rate_lags_paper_estimates",
            sibling_root
            / "ea-tdc/output/models/paper_tier2_selected_credit_rate_lags_estimates.csv",
            "",
            "selected_horizon_estimates",
        ),
        (
            "rolling_beta_estimates",
            sibling_root
            / "ea-tdc/output/models/tier2_rolling_selected_credit_rate_pass_through_estimates.csv",
            sibling_root
            / "ea-tdc/output/manifests/tier2_rolling_selected_credit_rate_pass_through_summary.json",
            "rolling_window_estimates",
        ),
        (
            "pandemic_exclusion_diagnostics",
            sibling_root
            / "ea-tdc/output/models/tdc_deposit_pass_through_pandemic_exclusion_diagnostics.csv",
            sibling_root
            / "ea-tdc/output/manifests/tier2_pass_through_regime_persistence_summary.json",
            "pandemic_exclusion_and_influence_diagnostics",
        ),
        (
            "episode_beta_diagnostics",
            sibling_root
            / "ea-tdc/output/reports/tier2_pass_through_offset_episode_betas.csv",
            sibling_root
            / "ea-tdc/output/manifests/tier2_pass_through_offset_diagnostics_summary.json",
            "episode_beta_diagnostics",
        ),
        (
            "rolling_minus_pandemic_diagnostics",
            sibling_root
            / "ea-tdc/output/reports/tier2_pass_through_rolling_minus_pandemic_betas.csv",
            sibling_root
            / "ea-tdc/output/manifests/tier2_pass_through_regime_persistence_summary.json",
            "rolling_minus_pandemic_diagnostics",
        ),
        (
            "influence_quarter_diagnostics",
            sibling_root
            / "ea-tdc/output/reports/tier2_pass_through_influence_quarters.csv",
            sibling_root
            / "ea-tdc/output/manifests/tier2_pass_through_regime_persistence_summary.json",
            "pandemic_quarter_influence_diagnostics",
        ),
        (
            "component_state_dep_ru_acquisition_low_reserves",
            sibling_root
            / "ea-tdc/output/models/tdc_component_state_dep_ru_acquisition_low_reserves__lp_estimates.csv",
            sibling_root
            / "ea-tdc/output/manifests/tdc_component_state_dep_ru_acquisition_low_reserves__estimation_summary.json",
            "component_state_diagnostic",
        ),
        (
            "component_state_dep_treasury_cash_drain_on_rrp_drain",
            sibling_root
            / "ea-tdc/output/models/tdc_component_state_dep_treasury_cash_drain_on_rrp_drain__lp_estimates.csv",
            sibling_root
            / "ea-tdc/output/manifests/tdc_component_state_dep_treasury_cash_drain_on_rrp_drain__estimation_summary.json",
            "component_state_diagnostic",
        ),
        (
            "state_dep_low_reserves",
            sibling_root
            / "ea-tdc/output/models/tdc_state_dep_low_reserves__lp_estimates.csv",
            sibling_root
            / "ea-tdc/output/manifests/tdc_state_dep_low_reserves__estimation_summary.json",
            "state_dependent_pass_through_diagnostic",
        ),
        (
            "state_dep_on_rrp_drain",
            sibling_root
            / "ea-tdc/output/models/tdc_state_dep_on_rrp_drain__lp_estimates.csv",
            sibling_root
            / "ea-tdc/output/manifests/tdc_state_dep_on_rrp_drain__estimation_summary.json",
            "state_dependent_pass_through_diagnostic",
        ),
        (
            "state_dep_bank_short_share",
            sibling_root
            / "ea-tdc/output/models/tdc_state_dep_bank_short_share__lp_estimates.csv",
            sibling_root
            / "ea-tdc/output/manifests/tdc_state_dep_bank_short_share__estimation_summary.json",
            "state_dependent_pass_through_diagnostic",
        ),
        (
            "state_dep_bank_foreign_private_corr",
            sibling_root
            / "ea-tdc/output/models/tdc_state_dep_bank_foreign_private_corr__lp_estimates.csv",
            sibling_root
            / "ea-tdc/output/manifests/tdc_state_dep_bank_foreign_private_corr__estimation_summary.json",
            "state_dependent_pass_through_diagnostic",
        ),
        (
            "state_dep_slr_bank_leverage_pressure",
            sibling_root
            / "ea-tdc/output/models/tdc_state_dep_slr_bank_leverage_pressure__lp_estimates.csv",
            sibling_root
            / "ea-tdc/output/manifests/tdc_state_dep_slr_bank_leverage_pressure__estimation_summary.json",
            "state_dependent_pass_through_diagnostic",
        ),
    ]
    rows: list[dict[str, str]] = []
    for artifact_role, artifact_path, manifest_path, source_row_role in specs:
        rows.extend(
            _calibration_import_rows_for_artifact(
                artifact_role=artifact_role,
                artifact_path=artifact_path,
                manifest_path=Path(manifest_path) if manifest_path else None,
                source_row_role=source_row_role,
            )
        )
    return sorted(rows, key=lambda row: row["calibration_import_row_id"])


def tdc_deposit_pass_through_regime_scenario_rows(
    source_rows: list[dict[str, str]],
    *,
    start_period: str = "2026Q2",
    periods: int = 24,
) -> list[dict[str, str]]:
    """Build scenario-only forward pass-through paths from source-import rows."""

    by_id = {row["source_import_row_id"]: row for row in source_rows}
    normal_id = EVIDENCE_B_NORMAL_FORWARD_H0_SOURCE_ROW_ID
    full_id = "ea_tdc_paper_matched_total_deposits_h0"
    rolling_id = "ea_tdc_latest_rolling_matched_total_deposits_h0"
    normal_value = by_id[normal_id]["pass_through_point"]
    normal_high_value = by_id[normal_id]["pass_through_upper95"] or normal_value
    scenarios = [
        (
            "normal_forward",
            "Normal forward h0 import-contract candidate",
            normal_id,
            normal_value,
            "central_forward_h0_import_contract_candidate",
            "true",
        ),
        (
            "latest_rolling_persistence",
            "Latest rolling persistence diagnostic",
            rolling_id,
            by_id[rolling_id]["pass_through_point"],
            "diagnostic_persistence_scenario",
            "false",
        ),
        (
            "full_sample_high_liquidity",
            "Full-sample high-liquidity historical scenario",
            full_id,
            by_id[full_id]["pass_through_point"],
            "historical_full_sample_high_liquidity_scenario",
            "false",
        ),
        (
            "liquidity_event_step_up",
            "Normal forward for five years, then liquidity-event step-up",
            normal_id,
            normal_value,
            "state_dependent_liquidity_event_scenario",
            "false",
        ),
    ]

    rows: list[dict[str, str]] = []
    for scenario_id, label, source_id, value, role, default_candidate in scenarios:
        for period_index in range(periods):
            selected_source_id = source_id
            selected_value = value
            step_enabled = "false"
            source_field = "pass_through_point"
            stress_blocker = ""
            if scenario_id == "liquidity_event_step_up" and period_index >= 20:
                selected_value = normal_high_value
                selected_source_id = normal_id
                source_field = "pass_through_upper95"
                step_enabled = "true"
                stress_blocker = (
                    "liquidity-event step-up uses the Evidence round B h0 normal-forward "
                    "upper bound as an explicit high-pass-through stress bound; "
                    "it is not a new point estimate, not a default, and not a "
                    "canonical or Evidence Mode input"
                )
            rows.append(
                _scenario_row(
                    scenario_id=scenario_id,
                    label=label,
                    period_index=period_index,
                    period_label=_period_label(start_period, period_index),
                    value=selected_value,
                    source_id=selected_source_id,
                    source_field=source_field,
                    source_status=(
                        "source_bound_h1_upper95_liquidity_event_stress_not_default"
                        if step_enabled == "true"
                        else by_id[source_id]["source_admission_status"]
                    ),
                    role=role,
                    default_candidate=default_candidate,
                    step_enabled=step_enabled,
                    stress_blocker=stress_blocker,
                    normal_id=normal_id,
                    source_rows=source_rows,
                )
            )
    return rows


def tdc_liquidity_regime_trigger_evidence_rows(
    repo_root: Path,
    source_rows: list[dict[str, str]],
    regime_scenario_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Build fail-closed trigger-review rows for TDC pass-through states."""

    sibling_root = repo_root.parent
    feature_path = (
        sibling_root
        / "ea-tdc/output/reports/tier2_pass_through_offset_rolling_beta_features.csv"
    )
    correlate_path = (
        sibling_root
        / "ea-tdc/output/reports/tier2_pass_through_offset_rolling_beta_correlates.csv"
    )
    episode_path = (
        sibling_root / "ea-tdc/output/reports/tier2_pass_through_offset_episode_betas.csv"
    )
    pandemic_path = (
        sibling_root
        / "ea-tdc/output/models/tdc_deposit_pass_through_pandemic_exclusion_diagnostics.csv"
    )
    source_by_id = {row["source_import_row_id"]: row for row in source_rows}
    scenario_by_id = {
        row["regime_scenario_id"]: row
        for row in regime_scenario_rows
        if row.get("period_index") == "0"
    }
    step_up_post_event = _first(
        row
        for row in regime_scenario_rows
        if row.get("regime_scenario_id") == "liquidity_event_step_up"
        and row.get("liquidity_event_step_up_enabled") == "true"
    )

    rows: list[dict[str, str]] = []
    feature_rows = _read_csv(feature_path)
    latest_feature_end = max(
        (row.get("window_end_quarter", "") for row in feature_rows),
        default="",
    )
    latest_features = [
        row
        for row in feature_rows
        if row.get("window_end_quarter", "") == latest_feature_end
    ]
    feature_specs = [
        (
            "pandemic_window_composition",
            "share_2020_2021",
            "window_value",
            "Pandemic-window share",
            "higher_values_indicate_pandemic_block_composition",
        ),
        (
            "pandemic_window_composition",
            "share_post_2020",
            "window_value",
            "Post-2020 window share",
            "higher_values_indicate_post_2020_regime_composition",
        ),
        (
            "tdc_scale",
            "tdc_mean_abs_mil",
            "window_value",
            "Mean absolute TDC scale",
            "higher_values_indicate_large_treasury_flow_window",
        ),
        (
            "tdc_scale",
            "tdc_max_abs_mil",
            "window_value",
            "Maximum absolute TDC scale",
            "higher_values_indicate_large_treasury_flow_window",
        ),
        (
            "treasury_plumbing",
            "tga_balance_qoq",
            "window_sd",
            "TGA volatility",
            "higher_values_indicate_treasury_cash_volatility",
        ),
        (
            "reserve_plumbing",
            "reserve_balances_qoq",
            "window_abs_mean",
            "Reserve movement scale",
            "higher_values_indicate_reserve_plumbing_volatility",
        ),
        (
            "reserve_plumbing",
            "reserve_balances_qoq",
            "window_sd",
            "Reserve movement volatility",
            "higher_values_indicate_reserve_plumbing_volatility",
        ),
        (
            "on_rrp_mmf_plumbing",
            "on_rrp_balance_qoq",
            "window_abs_mean",
            "ON RRP movement scale",
            "higher_values_indicate_on_rrp_buffer_or_leakage_context",
        ),
        (
            "on_rrp_mmf_plumbing",
            "on_rrp_balance_qoq",
            "tdc_feature_correlation",
            "TDC/ON RRP comovement",
            "sign_context_only_not_trigger_threshold",
        ),
        (
            "on_rrp_mmf_plumbing",
            "mmf_on_rrp_plumbing_absorption_qoq",
            "tdc_feature_correlation",
            "TDC/MMF-ON RRP absorption comovement",
            "sign_context_only_not_trigger_threshold",
        ),
    ]
    for family, feature_id, stat, label, direction in feature_specs:
        match = _first(
            row
            for row in latest_features
            if row.get("feature_id") == feature_id and row.get("feature_stat") == stat
        )
        rows.append(
            _trigger_row(
                source_path=feature_path,
                source=match,
                source_field="feature_value",
                trigger_regime_id="liquidity_event_candidate",
                trigger_regime_label="Liquidity-event candidate review",
                trigger_variable_family=family,
                trigger_variable_id=feature_id,
                trigger_variable_label=label,
                trigger_statistic=stat,
                trigger_direction=direction,
                observed_value=match.get("feature_value", "") if match else "",
                observed_value_unit=_feature_unit(feature_id, stat),
                observed_window_start=match.get("window_start_quarter", "") if match else "",
                observed_window_end=match.get("window_end_quarter", "") if match else "",
                observed_sample_or_period=(
                    f"{match.get('window_start_quarter', '')}_to_{match.get('window_end_quarter', '')}"
                    if match
                    else ""
                ),
                linked_scenario_id="liquidity_event_step_up",
                linked_source_id=EVIDENCE_B_NORMAL_FORWARD_H0_SOURCE_ROW_ID,
                linked_value=(
                    step_up_post_event.get("pass_through_value", "")
                    if step_up_post_event
                    else ""
                ),
            )
        )

    correlate_specs = [
        ("tdc_scale", "tdc_mean_abs_mil", "window_value"),
        ("treasury_plumbing", "tga_balance_qoq", "window_sd"),
        ("reserve_plumbing", "reserve_balances_qoq", "window_abs_mean"),
        ("reserve_plumbing", "reserve_balances_qoq", "window_sd"),
        ("on_rrp_mmf_plumbing", "on_rrp_balance_qoq", "tdc_feature_correlation"),
        (
            "on_rrp_mmf_plumbing",
            "mmf_on_rrp_plumbing_absorption_qoq",
            "tdc_feature_correlation",
        ),
    ]
    correlate_rows = _read_csv(correlate_path)
    for family, feature_id, stat in correlate_specs:
        match = _first(
            row
            for row in correlate_rows
            if row.get("feature_id") == feature_id and row.get("feature_stat") == stat
        )
        rows.append(
            _trigger_row(
                source_path=correlate_path,
                source=match,
                source_field="correlation_with_rolling_deposit_beta",
                trigger_regime_id="rolling_beta_correlate_review",
                trigger_regime_label="Rolling-beta correlate review",
                trigger_variable_family=family,
                trigger_variable_id=feature_id,
                trigger_variable_label=match.get("feature_label", feature_id)
                if match
                else feature_id,
                trigger_statistic=f"{stat}_correlation_with_rolling_beta",
                trigger_direction=(
                    "correlation_sign_and_magnitude_context_only_not_threshold"
                ),
                observed_value=(
                    match.get("correlation_with_rolling_deposit_beta", "")
                    if match
                    else ""
                ),
                observed_value_unit="pearson_correlation_across_overlapping_windows",
                observed_window_start="rolling_windows",
                observed_window_end="rolling_windows",
                observed_sample_or_period=match.get("n_windows", "") if match else "",
                linked_scenario_id="liquidity_event_step_up",
                linked_source_id="ea_tdc_latest_rolling_matched_total_deposits_h0",
                linked_value=source_by_id.get(
                    "ea_tdc_latest_rolling_matched_total_deposits_h0", {}
                ).get("pass_through_point", ""),
            )
        )

    episode_rows = _read_csv(episode_path)
    episode_specs = [
        ("full_available", "matched_total_deposits", "full_sample_high_liquidity"),
        ("pre_2020", "matched_total_deposits", "normal_forward"),
        ("full_available", "other_component_tier2_regression_mmf_rrp_prop_bank_only_qoq", "liquidity_event_step_up"),
        ("pre_2020", "other_component_tier2_regression_mmf_rrp_prop_bank_only_qoq", "normal_forward"),
    ]
    for period, outcome, scenario_id in episode_specs:
        match = _first(
            row
            for row in episode_rows
            if row.get("period") == period and row.get("outcome") == outcome
        )
        linked_source_id = (
            "ea_tdc_paper_matched_total_deposits_h0"
            if scenario_id == "full_sample_high_liquidity"
            else EVIDENCE_B_NORMAL_FORWARD_H0_SOURCE_ROW_ID
        )
        rows.append(
            _trigger_row(
                source_path=episode_path,
                source=match,
                source_field="normalized_beta",
                trigger_regime_id=f"episode_beta_{period}",
                trigger_regime_label=f"Episode beta review: {period}",
                trigger_variable_family="pass_through_episode_beta",
                trigger_variable_id=f"{period}_{outcome}",
                trigger_variable_label=match.get("outcome_label", outcome)
                if match
                else outcome,
                trigger_statistic="normalized_beta",
                trigger_direction="episode_comparison_context_only_not_trigger_threshold",
                observed_value=match.get("normalized_beta", "") if match else "",
                observed_value_unit="dollars_per_dollar_tdc",
                observed_window_start=period,
                observed_window_end=period,
                observed_sample_or_period=period,
                linked_scenario_id=scenario_id,
                linked_source_id=linked_source_id,
                linked_value=scenario_by_id.get(scenario_id, {}).get(
                    "pass_through_value", ""
                ),
            )
        )

    for source_row in _read_csv(pandemic_path):
        if (
            source_row.get("diagnostic_family")
            != "tdc_deposit_pass_through_pandemic_exclusion"
            or source_row.get("outcome") != "matched_total_deposits"
        ):
            continue
        rows.append(
            _trigger_row(
                source_path=pandemic_path,
                source=source_row,
                source_field="normalized_beta",
                trigger_regime_id="pandemic_window_composition_sensitivity",
                trigger_regime_label="Pandemic-window composition sensitivity",
                trigger_variable_family="pandemic_window_composition",
                trigger_variable_id=source_row.get("drop_rule", ""),
                trigger_variable_label=source_row.get("drop_description", ""),
                trigger_statistic="pandemic_exclusion_normalized_beta",
                trigger_direction="drop_rule_sensitivity_context_only_not_trigger_threshold",
                observed_value=source_row.get("normalized_beta", ""),
                observed_value_unit="dollars_per_dollar_tdc",
                observed_window_start=source_row.get("window_start_quarter", ""),
                observed_window_end=source_row.get("window_end_quarter", ""),
                observed_sample_or_period=source_row.get("sample_label", ""),
                linked_scenario_id="latest_rolling_persistence",
                linked_source_id="ea_tdc_latest_rolling_matched_total_deposits_h0",
                linked_value=source_by_id.get(
                    "ea_tdc_latest_rolling_matched_total_deposits_h0", {}
                ).get("pass_through_point", ""),
            )
        )

    return sorted(rows, key=lambda row: row["trigger_evidence_row_id"])


def tdc_liquidity_regime_trigger_promotion_protocol_rows(
    trigger_evidence_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Build the fail-closed promotion contract for trigger evidence."""

    required_fields = [
        (
            "trigger_threshold_rule",
            "Trigger threshold rule",
            "defines source-backed numeric or categorical threshold for a trigger",
        ),
        (
            "validation_sample",
            "Validation sample",
            "identifies estimation and validation windows before trigger use",
        ),
        (
            "out_of_sample_check",
            "Out-of-sample check",
            "documents out-of-sample trigger performance before runtime use",
        ),
        (
            "false_positive_control",
            "False-positive control",
            "specifies how false liquidity-event triggers are bounded",
        ),
        (
            "state_classification_rule",
            "State classification rule",
            "maps trigger variables into high, normal, or low pass-through states",
        ),
        (
            "scenario_selection_rule",
            "Scenario-selection rule",
            "defines how an admitted state may select a scenario path",
        ),
        (
            "source_provenance",
            "Source provenance",
            "records source artifact, hash, row key, and source field",
        ),
        (
            "review_status",
            "Review status",
            "records human/source review status before any promotion decision",
        ),
    ]
    rows: list[dict[str, str]] = []
    for trigger in trigger_evidence_rows:
        for field_id, label, role in required_fields:
            rows.append(
                _promotion_protocol_row(
                    trigger=trigger,
                    field_id=field_id,
                    label=label,
                    role=role,
                )
            )
    return sorted(rows, key=lambda row: row["promotion_protocol_row_id"])


def tdc_liquidity_regime_trigger_validation_evidence_rows(
    calibration_import_rows: list[dict[str, str]],
    promotion_protocol_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Materialize blocked validation evidence for trigger promotion fields."""

    target_fields = {
        "validation_sample": (
            "validation_sample_review",
            {
                "selected_credit_rate_lags_paper_estimates",
                "rolling_beta_estimates",
                "pandemic_exclusion_diagnostics",
                "rolling_minus_pandemic_diagnostics",
            },
        ),
        "out_of_sample_check": (
            "out_of_sample_review",
            {
                "rolling_beta_estimates",
                "rolling_minus_pandemic_diagnostics",
                "influence_quarter_diagnostics",
                "pandemic_exclusion_diagnostics",
            },
        ),
        "false_positive_control": (
            "false_positive_review",
            {
                "influence_quarter_diagnostics",
                "rolling_minus_pandemic_diagnostics",
                "pandemic_exclusion_diagnostics",
            },
        ),
        "state_classification_rule": (
            "state_classification_review",
            {
                "state_dep_low_reserves",
                "state_dep_on_rrp_drain",
                "state_dep_bank_short_share",
                "state_dep_bank_foreign_private_corr",
                "state_dep_slr_bank_leverage_pressure",
                "component_state_dep_ru_acquisition_low_reserves",
                "component_state_dep_treasury_cash_drain_on_rrp_drain",
            },
        ),
        "scenario_selection_rule": (
            "scenario_selection_review",
            {
                "selected_credit_rate_lags_paper_estimates",
                "rolling_beta_estimates",
                "pandemic_exclusion_diagnostics",
                "episode_beta_diagnostics",
            },
        ),
    }
    rows: list[dict[str, str]] = []
    for protocol in promotion_protocol_rows:
        required_field = protocol.get("required_promotion_field", "")
        if required_field not in target_fields:
            continue
        evidence_role, source_roles = target_fields[required_field]
        source_rows = [
            row
            for row in calibration_import_rows
            if row.get("source_artifact_role", "") in source_roles
        ]
        rows.append(
            _trigger_validation_evidence_row(
                protocol=protocol,
                evidence_role=evidence_role,
                source_rows=source_rows,
            )
        )
    return sorted(rows, key=lambda row: row["trigger_validation_evidence_row_id"])


def tdc_deposit_pass_through_scenario_contract_rows(
    *,
    source_import_rows: list[dict[str, str]],
    calibration_import_rows: list[dict[str, str]],
    regime_scenario_rows: list[dict[str, str]],
    trigger_evidence_rows: list[dict[str, str]],
    trigger_promotion_protocol_rows: list[dict[str, str]],
    trigger_validation_evidence_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Build source-bound, fail-closed scenario-contract rows."""

    trigger_by_scenario: dict[str, list[dict[str, str]]] = {}
    for row in trigger_evidence_rows:
        trigger_by_scenario.setdefault(row.get("linked_regime_scenario_id", ""), []).append(
            row
        )
    protocol_by_trigger: dict[str, list[dict[str, str]]] = {}
    for row in trigger_promotion_protocol_rows:
        protocol_by_trigger.setdefault(row.get("trigger_evidence_row_id", ""), []).append(
            row
        )
    validation_by_protocol: dict[str, list[dict[str, str]]] = {}
    for row in trigger_validation_evidence_rows:
        validation_by_protocol.setdefault(row.get("promotion_protocol_row_id", ""), []).append(
            row
        )

    source_by_id = {row.get("source_import_row_id", ""): row for row in source_import_rows}
    pandemic_rows = [
        row
        for row in source_import_rows
        if row.get("source_import_row_id", "").startswith("ea_tdc_pandemic_exclusion_")
    ]
    rows: list[dict[str, str]] = []
    contract_fields = [
        "pass_through_value",
        "source_import_provenance",
        "ea_tdc_calibration_import_provenance",
        "trigger_evidence_review",
        "trigger_promotion_protocol",
        "trigger_validation_evidence",
        "pandemic_exclusion_diagnostic",
    ]
    for scenario in regime_scenario_rows:
        scenario_id = scenario.get("regime_scenario_id", "")
        trigger_rows = trigger_by_scenario.get(scenario_id, [])
        protocol_rows = [
            protocol
            for trigger in trigger_rows
            for protocol in protocol_by_trigger.get(
                trigger.get("trigger_evidence_row_id", ""), []
            )
        ]
        validation_rows = [
            validation
            for protocol in protocol_rows
            for validation in validation_by_protocol.get(
                protocol.get("promotion_protocol_row_id", ""), []
            )
        ]
        source_row = source_by_id.get(
            scenario.get("pass_through_source_import_row_id", ""), {}
        )
        source_rows_for_contract = [source_row] if source_row else []
        calibration_rows = _calibration_rows_for_source(
            source_row=source_row,
            calibration_import_rows=calibration_import_rows,
        )
        for contract_field in contract_fields:
            rows.append(
                _scenario_contract_row(
                    scenario=scenario,
                    contract_field=contract_field,
                    source_rows=(
                        pandemic_rows
                        if contract_field == "pandemic_exclusion_diagnostic"
                        else source_rows_for_contract
                    ),
                    calibration_rows=(
                        _pandemic_calibration_rows(calibration_import_rows)
                        if contract_field == "pandemic_exclusion_diagnostic"
                        else calibration_rows
                    ),
                    trigger_rows=trigger_rows,
                    protocol_rows=protocol_rows,
                    validation_rows=validation_rows,
                )
            )
    return sorted(rows, key=lambda row: row["scenario_contract_row_id"])


def tdc_deposit_pass_through_trigger_validation_preflight_rows(
    *,
    source_import_rows: list[dict[str, str]],
    scenario_contract_rows: list[dict[str, str]],
    trigger_evidence_rows: list[dict[str, str]],
    trigger_promotion_protocol_rows: list[dict[str, str]],
    trigger_validation_evidence_rows: list[dict[str, str]],
    tdcsim_projection_contract_bridge_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Join TDC scenario contracts to trigger-validation blockers."""

    source_by_id = {row.get("source_import_row_id", ""): row for row in source_import_rows}
    trigger_by_id = {
        row.get("trigger_evidence_row_id", ""): row for row in trigger_evidence_rows
    }
    protocol_by_id = {
        row.get("promotion_protocol_row_id", ""): row
        for row in trigger_promotion_protocol_rows
    }
    protocols_by_trigger: dict[str, list[dict[str, str]]] = {}
    for row in trigger_promotion_protocol_rows:
        protocols_by_trigger.setdefault(row.get("trigger_evidence_row_id", ""), []).append(
            row
        )
    contract_by_scenario_trigger: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in scenario_contract_rows:
        scenario_id = row.get("regime_scenario_id", "")
        for trigger_id in row.get("trigger_evidence_row_ids", "").split(";"):
            if trigger_id:
                contract_by_scenario_trigger.setdefault(
                    (scenario_id, trigger_id), []
                ).append(row)

    baseline_tdcsim_rows = [
        row
        for row in tdcsim_projection_contract_bridge_rows
        if row.get("scenario_id") == "current_mix_baseline"
    ]
    tdcsim_versions = _unique_values(baseline_tdcsim_rows, "tdcsim_contract_version")
    tdcsim_hashes = _unique_values(baseline_tdcsim_rows, "tdcsim_manifest_hash")
    tdcsim_version_status = (
        "pass_current_mix_baseline_tdcsim_contract_version_hashed_review_only"
        if tdcsim_versions and tdcsim_hashes
        else "blocked_missing_current_mix_baseline_tdcsim_contract_version_or_hash"
    )

    rows: list[dict[str, str]] = []
    for validation in trigger_validation_evidence_rows:
        trigger_id = validation.get("trigger_evidence_row_id", "")
        trigger = trigger_by_id.get(trigger_id, {})
        protocol = protocol_by_id.get(validation.get("promotion_protocol_row_id", ""), {})
        scenario_id = validation.get("linked_regime_scenario_id", "")
        source_row = source_by_id.get(
            validation.get("linked_pass_through_source_import_row_id", ""), {}
        )
        matching_contracts = contract_by_scenario_trigger.get((scenario_id, trigger_id), [])
        requirement = validation.get("required_promotion_field", "")
        row = {
            field: ""
            for field in (
                RATEWALL_TDC_DEPOSIT_PASS_THROUGH_TRIGGER_VALIDATION_PREFLIGHT_FIELDS
            )
        }
        row.update(
            {
                "preflight_row_id": "::".join(
                    [
                        scenario_id or "missing_scenario",
                        trigger_id or "missing_trigger",
                        requirement or "missing_requirement",
                        _source_artifact_handle(validation),
                    ]
                ),
                "regime_scenario_id": scenario_id,
                "regime_scenario_label": trigger.get("trigger_regime_label", ""),
                "trigger_candidate_id": trigger_id,
                "trigger_variable": trigger.get("trigger_variable_id", ""),
                "trigger_variable_family": validation.get("trigger_variable_family", ""),
                "trigger_statistic": validation.get("trigger_statistic", ""),
                "validation_requirement": requirement,
                "source_artifact_handle": _source_artifact_handle(validation),
                "source_artifact_paths": validation.get("source_artifact_paths", ""),
                "source_artifact_sha256s": validation.get("source_artifact_sha256s", ""),
                "source_row_keys_sample": validation.get("source_row_keys_sample", ""),
                "scenario_contract_row_count": str(len(matching_contracts)),
                "scenario_contract_row_ids_sample": ";".join(
                    row.get("scenario_contract_row_id", "")
                    for row in matching_contracts[:8]
                    if row.get("scenario_contract_row_id", "")
                ),
                "trigger_evidence_row_id": trigger_id,
                "promotion_protocol_row_id": validation.get(
                    "promotion_protocol_row_id", ""
                ),
                "trigger_validation_evidence_row_id": validation.get(
                    "trigger_validation_evidence_row_id", ""
                ),
                "linked_pass_through_source_import_row_id": validation.get(
                    "linked_pass_through_source_import_row_id", ""
                ),
                "linked_pass_through_source_artifact_sha256": source_row.get(
                    "source_artifact_sha256", ""
                ),
                "ea_tdc_artifact_hash_status": (
                    "pass_ea_tdc_source_and_validation_hashes_present"
                    if source_row.get("source_artifact_sha256", "")
                    and validation.get("source_artifact_sha256s", "")
                    else "blocked_missing_ea_tdc_source_or_validation_hash"
                ),
                "trigger_threshold_source_status": _protocol_field_status(
                    protocols_by_trigger.get(trigger_id, []),
                    "trigger_threshold_rule",
                ),
                "state_classification_rule_status": validation.get(
                    "candidate_state_classification_status", ""
                ),
                "validation_sample_start": validation.get("sample_window_start_min", ""),
                "validation_sample_end": validation.get("sample_window_end_max", ""),
                "holdout_sample_status": validation.get(
                    "candidate_validation_sample_status", ""
                ),
                "out_of_sample_validation_status": validation.get(
                    "candidate_out_of_sample_status", ""
                ),
                "false_positive_control_status": validation.get(
                    "candidate_false_positive_control_status", ""
                ),
                "false_negative_control_status": (
                    "blocked_no_false_negative_control_protocol"
                ),
                "tdcsim_contract_version": ";".join(tdcsim_versions),
                "tdcsim_manifest_hash": ";".join(tdcsim_hashes),
                "tdcsim_contract_version_status": tdcsim_version_status,
                "tdcsim_contract_blocker": (
                    "TDCSim current_mix_baseline contract is available only as "
                    "projection/version context; it does not admit a TDC "
                    "liquidity-regime runtime selector"
                ),
                "promotion_protocol_status": validation.get(
                    "trigger_validation_admission_status", ""
                )
                or protocol.get("promotion_protocol_admission_status", ""),
                "runtime_selector_status": (
                    "blocked_no_runtime_trigger_or_scenario_selection"
                ),
                "scenario_default_allowed": "false",
                "dynamic_path_reference_allowed": "false",
                "runtime_scenario_selection_allowed": "false",
                "source_backed_dynamic_reference_allowed": "false",
                "trigger_promotable": "false",
                "admission_status": "blocked_trigger_validation_preflight_only",
                "exact_blocker": (
                    "trigger threshold, state-classification rule, validation/"
                    "holdout sample, out-of-sample check, false-positive and "
                    "false-negative controls, TDCSim runtime-selector contract, "
                    "and promotion protocol do not jointly pass"
                ),
                "allowed_use": "tdc_trigger_validation_preflight_review_only",
                "blocked_use": (
                    "runtime_scenario_selection;default_selection;main_ratio;"
                    "canonical_ratio;Evidence_Mode;denominator_prior;"
                    "pricing_output;holder_allocation;raw_rate_shock;"
                    "reset_calendar"
                ),
                "claim_boundary": (
                    "tdc_deposit_pass_through_trigger_validation_preflight_"
                    "not_runtime_selector"
                ),
            }
        )
        row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
        rows.append(row)
    return sorted(rows, key=lambda row: row["preflight_row_id"])


def tdc_deposit_pass_through_scenario_contract_invariant_audit_rows(
    *,
    source_import_rows: list[dict[str, str]],
    scenario_contract_rows: list[dict[str, str]],
    preflight_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Audit that source/default-looking TDC flags cannot select scenarios."""

    source_default_true_count = sum(
        row.get("scenario_default_allowed") == "true" for row in source_import_rows
    )
    source_dynamic_reference_true_count = sum(
        row.get("dynamic_path_reference_allowed") == "true" for row in source_import_rows
    )
    scenario_default_true_count = sum(
        row.get("scenario_default_allowed") == "true" for row in scenario_contract_rows
    )
    scenario_runtime_selector_true_count = sum(
        row.get("runtime_scenario_selection_allowed") == "true"
        for row in scenario_contract_rows
    )
    scenario_dynamic_reference_true_count = sum(
        row.get("dynamic_path_reference_allowed") == "true"
        for row in scenario_contract_rows
    )
    non_normal_dynamic_reference_true_count = sum(
        row.get("dynamic_path_reference_allowed") == "true"
        and (
            row.get("regime_scenario_id") != "normal_forward"
            or row.get("contract_field") != "pass_through_value"
        )
        for row in scenario_contract_rows
    )
    preflight_runtime_selector_true_count = sum(
        row.get("runtime_scenario_selection_allowed") == "true"
        for row in preflight_rows
    )
    preflight_default_true_count = sum(
        row.get("scenario_default_allowed") == "true" for row in preflight_rows
    )
    all_switches_false = all(
        row.get(field, "false") == "false"
        for row in [*scenario_contract_rows, *preflight_rows]
        for field in FORBIDDEN_SWITCH_FIELDS
    )
    normal_reference_ok = (
        scenario_dynamic_reference_true_count == 24
        and non_normal_dynamic_reference_true_count == 0
        and {
            row.get("regime_scenario_id")
            for row in scenario_contract_rows
            if row.get("dynamic_path_reference_allowed") == "true"
        }
        == {"normal_forward"}
        and {
            row.get("contract_field")
            for row in scenario_contract_rows
            if row.get("dynamic_path_reference_allowed") == "true"
        }
        == {"pass_through_value"}
    )
    blocks_dominate = (
        source_default_true_count >= 1
        and scenario_default_true_count == 0
        and scenario_runtime_selector_true_count == 0
        and preflight_runtime_selector_true_count == 0
        and preflight_default_true_count == 0
    )
    checks = [
        (
            "source_import_default_flags_cannot_override_contract_blocks",
            blocks_dominate,
            "default_selection",
            "source-import/default-looking rows are dominated by scenario-contract and preflight blocks",
            "source-import default or dynamic-reference flags became a runtime/default selector",
        ),
        (
            "normal_forward_only_dynamic_reference",
            normal_reference_ok,
            "dynamic_reference",
            "only 24 normal-forward pass-through-value rows carry dynamic reference status",
            "a non-normal or non-value scenario-contract row became a dynamic reference",
        ),
        (
            "scenario_contract_runtime_selector_disabled",
            scenario_runtime_selector_true_count == 0,
            "runtime_selector",
            "all scenario-contract rows keep runtime_scenario_selection_allowed=false",
            "a scenario-contract row enabled runtime scenario selection",
        ),
        (
            "trigger_preflight_runtime_selector_disabled",
            preflight_runtime_selector_true_count == 0 and preflight_default_true_count == 0,
            "trigger_preflight",
            "all trigger-validation preflight rows keep default/runtime selection disabled",
            "a trigger-validation preflight row enabled default or runtime selection",
        ),
        (
            "tdc_scenario_contract_forbidden_switches_false",
            all_switches_false,
            "forbidden_switches",
            "all scenario-contract and preflight forbidden switches remain false",
            "a TDC scenario/preflight row enabled a forbidden claim or output switch",
        ),
    ]
    rows: list[dict[str, str]] = []
    for rank, (item, passed, family, summary, blocker) in enumerate(checks, start=1):
        row = {
            field: ""
            for field in RATEWALL_TDC_DEPOSIT_PASS_THROUGH_SCENARIO_CONTRACT_INVARIANT_AUDIT_FIELDS
        }
        row.update(
            {
                "audit_row_id": f"tdc_scenario_contract_invariant::{rank}::{item}",
                "audit_item": item,
                "evidence_surface": (
                    "ratewall_tdc_deposit_pass_through_scenario_contract.csv;"
                    "ratewall_tdc_deposit_pass_through_trigger_validation_preflight.csv"
                ),
                "forbidden_switch_family": family,
                "scenario_contract_row_count": str(len(scenario_contract_rows)),
                "preflight_row_count": str(len(preflight_rows)),
                "source_import_default_true_count": str(source_default_true_count),
                "source_import_dynamic_reference_true_count": str(
                    source_dynamic_reference_true_count
                ),
                "scenario_contract_default_true_count": str(
                    scenario_default_true_count
                ),
                "scenario_contract_runtime_selector_true_count": str(
                    scenario_runtime_selector_true_count
                ),
                "scenario_contract_dynamic_reference_true_count": str(
                    scenario_dynamic_reference_true_count
                ),
                "non_normal_dynamic_reference_true_count": str(
                    non_normal_dynamic_reference_true_count
                ),
                "preflight_runtime_selector_true_count": str(
                    preflight_runtime_selector_true_count
                ),
                "preflight_default_true_count": str(preflight_default_true_count),
                "source_import_default_override_status": (
                    "pass_source_import_default_flags_do_not_override_contract"
                    if blocks_dominate
                    else "fail_source_import_default_flag_override_risk"
                ),
                "scenario_contract_block_dominates_source_import_status": (
                    "pass_scenario_contract_blocks_dominate_source_import_flags"
                    if blocks_dominate
                    else "fail_scenario_contract_blocks_do_not_dominate"
                ),
                "tdcsim_runtime_selector_status": (
                    "blocked_tdcsim_contract_not_runtime_selector"
                ),
                "audit_status": "pass" if passed else "fail",
                "exact_blocker": summary if passed else blocker,
                "allowed_use": "tdc_scenario_contract_invariant_review_only",
                "blocked_use": (
                    "runtime_scenario_selection;default_selection;main_ratio;"
                    "canonical_ratio;Evidence_Mode;denominator_prior;"
                    "pricing_output;holder_allocation;raw_rate_shock;"
                    "reset_calendar"
                ),
                "claim_boundary": (
                    "tdc_deposit_pass_through_scenario_contract_invariant_"
                    "audit_not_runtime_selector"
                ),
            }
        )
        row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
        rows.append(row)
    return rows


def _calibration_import_rows_for_artifact(
    *,
    artifact_role: str,
    artifact_path: Path,
    manifest_path: Path | None,
    source_row_role: str,
) -> list[dict[str, str]]:
    manifest = _read_json(manifest_path) if manifest_path else {}
    manifest_outputs = manifest.get("outputs", {})
    rows = _read_csv(artifact_path)
    if not rows:
        return [
            _calibration_import_row(
                artifact_role=artifact_role,
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                manifest=manifest,
                source_row_role=source_row_role,
                source={},
                row_index=0,
                source_row_key="missing_source_rows",
                import_status="blocked_missing_ea_tdc_artifact_or_rows",
            )
        ]
    output_count = ""
    if isinstance(manifest.get("row_counts"), dict):
        output_count = ";".join(
            f"{key}={value}" for key, value in sorted(manifest["row_counts"].items())
        )
    elif manifest.get("rows_written") is not None:
        output_count = str(manifest.get("rows_written", ""))
    elif manifest.get("regression_rows") is not None:
        output_count = f"regression_rows={manifest.get('regression_rows')}"
    result: list[dict[str, str]] = []
    for row_index, source in enumerate(rows, start=1):
        result.append(
            _calibration_import_row(
                artifact_role=artifact_role,
                artifact_path=artifact_path,
                manifest_path=manifest_path,
                manifest=manifest,
                source_row_role=source_row_role,
                source=source,
                row_index=row_index,
                source_row_key=_calibration_source_row_key(source),
                import_status="pass_ea_tdc_source_row_versioned_review_only",
                manifest_outputs=(
                    json.dumps(manifest_outputs, sort_keys=True)
                    if isinstance(manifest_outputs, dict)
                    else ""
                ),
                manifest_row_count=output_count,
            )
        )
    return result


def _calibration_import_row(
    *,
    artifact_role: str,
    artifact_path: Path,
    manifest_path: Path | None,
    manifest: dict[str, object],
    source_row_role: str,
    source: dict[str, str],
    row_index: int,
    source_row_key: str,
    import_status: str,
    manifest_outputs: str = "",
    manifest_row_count: str = "",
) -> dict[str, str]:
    beta_field = _calibration_beta_field(source)
    beta_estimate = source.get(beta_field, "") if beta_field else ""
    row = {
        field: ""
        for field in RATEWALL_TDC_EA_TDC_PASS_THROUGH_CALIBRATION_IMPORT_FIELDS
    }
    row.update(
        {
            "calibration_import_row_id": "::".join(
                [
                    artifact_role,
                    str(row_index),
                    source_row_key or "missing_source_row_key",
                ]
            ),
            "source_project": "ea-tdc",
            "source_artifact_path": _project_relative_sibling_path(artifact_path),
            "source_artifact_sha256": _sha256(artifact_path)
            if artifact_path.exists()
            else "",
            "source_artifact_exists": "true" if artifact_path.exists() else "false",
            "source_artifact_kind": artifact_path.suffix.lstrip(".") or "unknown",
            "source_artifact_role": artifact_role,
            "source_artifact_job_id": str(manifest.get("job_id", ""))
            or source.get("job_id", ""),
            "source_artifact_manifest_path": _project_relative_sibling_path(
                manifest_path
            )
            if manifest_path
            else "",
            "source_artifact_manifest_sha256": _sha256(manifest_path)
            if manifest_path and manifest_path.exists()
            else "",
            "source_row_key": source_row_key,
            "source_row_index": str(row_index),
            "source_row_role": source_row_role,
            "imported_outcome": source.get("outcome", ""),
            "imported_horizon": source.get("horizon", ""),
            "imported_period_or_window": (
                source.get("sample_label")
                or source.get("period")
                or source.get("quarter")
                or "::".join(
                    part
                    for part in [
                        source.get("window_start_quarter", ""),
                        source.get("window_end_quarter", ""),
                    ]
                    if part
                )
            ),
            "window_start_quarter": source.get("window_start_quarter", ""),
            "window_end_quarter": source.get("window_end_quarter", ""),
            "window_quarters": source.get("window_quarters", ""),
            "sample_label": source.get("sample_label", ""),
            "n": source.get("n", ""),
            "treatment_id": source.get("treatment_id", ""),
            "state_id": source.get("state_id", ""),
            "state_profile": source.get("state_profile", ""),
            "drop_rule": source.get("drop_rule", ""),
            "quarter": source.get("quarter", ""),
            "estimate_kind": source.get("inference_method", "")
            or source.get("method_label", "")
            or source.get("diagnostic_family", "")
            or source_row_role,
            "beta_field": beta_field,
            "beta_estimate": beta_estimate,
            "beta_se": source.get("normalized_se")
            or source.get("deposit_se")
            or source.get("se", ""),
            "beta_lower95": source.get("normalized_lower95")
            or source.get("lower95", ""),
            "beta_upper95": source.get("normalized_upper95")
            or source.get("upper95", ""),
            "normalized_unit": source.get("normalized_unit", "")
            or "dollars_per_dollar_tdc",
            "effect_per_100b_tdc": source.get("effect_per_100b_tdc")
            or source.get("deposit_effect_per_100b_tdc", ""),
            "rsquared": source.get("rsquared")
            or source.get("deposit_rsquared", ""),
            "p_value_normal": source.get("p_value_normal")
            or source.get("deposit_p", ""),
            "source_claim_boundary": source.get("claim_boundary")
            or str(manifest.get("claim_boundary", "")),
            "source_manifest_row_count": manifest_row_count,
            "source_manifest_outputs": manifest_outputs,
            "import_status": import_status,
            "source_admission_status": (
                "source_artifact_versioned_review_only_not_runtime_selector"
            ),
            "scenario_default_allowed": "false",
            "dynamic_path_reference_allowed": "false",
            "promotion_protocol_required": "true",
            "exact_blocker": (
                "EA-TDC pass-through source row is versioned for calibration "
                "review, but trigger thresholds, validation sample, out-of-"
                "sample checks, false-positive controls, state classification, "
                "scenario selection, and review status must pass before any "
                "runtime trigger or default change"
            ),
            "next_backend_action": (
                "use this row as source-backed input to review or refresh "
                "RateWall TDC pass-through scenario contracts"
            ),
            "allowed_use": "ea_tdc_pass_through_calibration_import_review_only",
            "blocked_use": (
                "trigger_promotion;default_selection;main_ratio;canonical_ratio;"
                "Evidence_Mode;denominator_prior;pricing_output;"
                "holder_allocation;raw_rate_shock"
            ),
            "claim_boundary": (
                "ea_tdc_pass_through_calibration_import_not_runtime_selector"
            ),
        }
    )
    row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
    return row


def _read_json(path: Path | None) -> dict[str, object]:
    if not path or not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _calibration_beta_field(source: dict[str, str]) -> str:
    for field in (
        "normalized_beta",
        "deposit_beta",
        "beta",
        "leave_one_beta",
        "state_interaction_beta",
    ):
        if source.get(field, ""):
            return field
    return ""


def _calibration_source_row_key(source: dict[str, str]) -> str:
    pieces = [
        source.get("job_id", ""),
        source.get("outcome", ""),
        source.get("horizon", ""),
        source.get("window_start_quarter", ""),
        source.get("window_end_quarter", ""),
        source.get("period", ""),
        source.get("drop_rule", ""),
        source.get("quarter", ""),
        source.get("state_id", ""),
        source.get("state_profile", ""),
        source.get("treatment_id", ""),
    ]
    key = "::".join(piece for piece in pieces if piece)
    if key:
        return key
    return hashlib.sha256(
        "|".join(f"{key}={value}" for key, value in sorted(source.items())).encode(
            "utf-8"
        )
    ).hexdigest()[:24]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _source_row_from_ea_tdc(
    *,
    row_id: str,
    path: Path,
    source: dict[str, str],
    role: str,
    default_allowed: bool,
    default_role: str,
    admission_status: str,
    dynamic_path_reference_allowed: bool = True,
    protocol_admission_status: str = "pass_source_artifact_backed_scenario_only",
    exact_blocker: str = "not_a_recipient_demand_conversion_or_canonical_ratio_input",
    next_backend_action: str = "refresh_from_ea_tdc_artifact_when_sibling_estimates_update",
    claim_boundary: str = "tdc_deposit_pass_through_dynamic_scenario_only_not_main_ratio",
) -> dict[str, str]:
    row = _blank_source_row()
    row.update(
        {
            "source_import_row_id": row_id,
            "source_project": "ea-tdc",
            "source_artifact_path": _project_relative_sibling_path(path),
            "source_artifact_sha256": _sha256(path),
            "source_artifact_exists": "true",
            "source_artifact_row_key": _source_row_key(source),
            "source_row_role": role,
            "source_artifact_backed": "true",
            "source_user_supplied_context_only": "false",
            "outcome": source.get("outcome", ""),
            "horizon": source.get("horizon", ""),
            "window_start_quarter": source.get("window_start_quarter", ""),
            "window_end_quarter": source.get("window_end_quarter", ""),
            "window_quarters": source.get("window_quarters", ""),
            "sample_label": source.get("sample_label", ""),
            "n": source.get("n", ""),
            "treatment_id": source.get("treatment_id", ""),
            "control_policy_mode": source.get("pinned_control_policy_mode", ""),
            "method_label": "; ".join(
                part
                for part in [
                    source.get("job_id", ""),
                    source.get("treatment_label", ""),
                    source.get("inference_method", ""),
                    source.get("covariance_estimator", ""),
                ]
                if part
            ),
            "covariance_estimator": source.get("covariance_estimator", ""),
            "covariance_lags": source.get("covariance_lags", ""),
            "rsquared": source.get("rsquared", ""),
            "normalized_unit": source.get("normalized_unit", ""),
            "pass_through_point": source.get("normalized_beta", ""),
            "pass_through_se": source.get("normalized_se", ""),
            "pass_through_lower95": source.get("normalized_lower95")
            or _divide_if_percent_points(source.get("lower95", "")),
            "pass_through_upper95": source.get("normalized_upper95")
            or _divide_if_percent_points(source.get("upper95", "")),
            "effect_per_100b_tdc": source.get("effect_per_100b_tdc", ""),
            "effect_per_100b_lower95": source.get("effect_per_100b_lower95", ""),
            "effect_per_100b_upper95": source.get("effect_per_100b_upper95", ""),
            "scenario_default_allowed": "true" if default_allowed else "false",
            "scenario_default_role": default_role,
            "dynamic_path_reference_allowed": "true"
            if dynamic_path_reference_allowed
            else "false",
            "source_admission_status": admission_status,
            "protocol_admission_status": protocol_admission_status,
            "exact_blocker": exact_blocker,
            "next_backend_action": next_backend_action,
            "claim_boundary": claim_boundary,
        }
    )
    return row


def _missing_source_row(
    *, row_id: str, path: Path, role: str, blocker: str
) -> dict[str, str]:
    row = _blank_source_row()
    row.update(
        {
            "source_import_row_id": row_id,
            "source_project": "ea-tdc",
            "source_artifact_path": _project_relative_sibling_path(path),
            "source_artifact_sha256": _sha256(path) if path.exists() else "",
            "source_artifact_exists": "true" if path.exists() else "false",
            "source_row_role": role,
            "source_artifact_backed": "false",
            "source_user_supplied_context_only": "false",
            "scenario_default_allowed": "false",
            "dynamic_path_reference_allowed": "false",
            "source_admission_status": "blocked_missing_required_ea_tdc_source_row",
            "protocol_admission_status": "blocked_no_source_artifact_row",
            "exact_blocker": blocker,
            "next_backend_action": "rerun_or_fix_ea_tdc_source_artifact",
            "claim_boundary": (
                "tdc_deposit_pass_through_missing_source_row_not_runtime_input"
            ),
        }
    )
    return row


def _evidence_b_normal_forward_h0_source_row(path: Path) -> dict[str, str]:
    row = _blank_source_row()
    row.update(
        {
            "source_import_row_id": EVIDENCE_B_NORMAL_FORWARD_H0_SOURCE_ROW_ID,
            "source_project": "ratewall-evidence-b",
            "source_artifact_path": _project_relative_sibling_path(path),
            "source_artifact_sha256": _sha256(path) if path.exists() else "",
            "source_artifact_exists": "true" if path.exists() else "false",
            "source_artifact_row_key": "evidence_b_normal_forward_h0_import_contract",
            "source_row_role": "normal_forward_h0_import_contract_default",
            "source_artifact_backed": "true" if path.exists() else "false",
            "source_user_supplied_context_only": "true",
            "outcome": "matched_total_deposits",
            "horizon": "0",
            "sample_label": "evidence_b_import_contract_normal_forward_h0",
            "normalized_unit": "dollars_per_dollar_tdc",
            "pass_through_point": EVIDENCE_B_NORMAL_FORWARD_H0_BETA,
            "pass_through_lower95": EVIDENCE_B_NORMAL_FORWARD_H0_LOW,
            "pass_through_upper95": EVIDENCE_B_NORMAL_FORWARD_H0_HIGH,
            "scenario_default_allowed": "true",
            "scenario_default_role": "normal_forward_h0_dynamic_default_candidate",
            "dynamic_path_reference_allowed": "true",
            "source_admission_status": (
                "evidence_b_import_contract_normal_forward_h0_default"
            ),
            "protocol_admission_status": (
                "pass_source_backed_import_contract_scenario_only"
            ),
            "exact_blocker": (
                "evidence_b_import_contract_prior_only_not_evidence_mode_or_main_ratio"
            ),
            "next_backend_action": (
                "refresh_only_when_owner_updates_evidence_b_import_contract"
            ),
            "claim_boundary": (
                "tdc_deposit_pass_through_evidence_b_import_contract_assumption_mode"
            ),
        }
    )
    return row


def _pandemic_exclusion_diagnostic_rows(path: Path) -> list[dict[str, str]]:
    diagnostics = {
        "drop_2020_2021": (
            "ea_tdc_pandemic_exclusion_drop_2020q1_2021q4",
            "pandemic_exclusion_2020q1_2021q4_artifact_diagnostic",
        ),
        "drop_2020": (
            "ea_tdc_pandemic_exclusion_drop_2020",
            "pandemic_exclusion_drop_2020_artifact_diagnostic",
        ),
        "drop_2021": (
            "ea_tdc_pandemic_exclusion_drop_2021",
            "pandemic_exclusion_drop_2021_artifact_diagnostic",
        ),
    }
    source_rows = {
        row.get("drop_rule", ""): row
        for row in _read_csv(path)
        if row.get("diagnostic_family")
        == "tdc_deposit_pass_through_pandemic_exclusion"
        and row.get("outcome") == "matched_total_deposits"
    }
    rows: list[dict[str, str]] = []
    for drop_rule, (row_id, role) in diagnostics.items():
        source = source_rows.get(drop_rule)
        if source is None:
            rows.append(
                _missing_source_row(
                    row_id=row_id,
                    path=path,
                    role=role,
                    blocker=(
                        "EA-TDC pandemic-exclusion artifact missing "
                        f"matched_total_deposits {drop_rule} row"
                    ),
                )
            )
            continue
        rows.append(
            _source_row_from_ea_tdc(
                row_id=row_id,
                path=path,
                source=source,
                role=role,
                default_allowed=False,
                default_role="artifact_backed_diagnostic_not_dynamic_default",
                admission_status=(
                    "source_gate_passed_pandemic_exclusion_diagnostic_only"
                ),
                dynamic_path_reference_allowed=False,
                protocol_admission_status=(
                    "pass_source_artifact_backed_diagnostic_only_not_default"
                ),
                exact_blocker=(
                    "pandemic-exclusion diagnostic is source-artifact-backed "
                    "but is not a forward dynamic default, denominator "
                    "conversion, or canonical ratio input"
                ),
                next_backend_action=(
                    "use for state-dependence review only unless a separate "
                    "promotion rule admits a new scenario path"
                ),
                claim_boundary=(
                    "tdc_deposit_pass_through_pandemic_exclusion_diagnostic_"
                    "not_dynamic_default_or_main_ratio"
                ),
            )
        )
    return rows


def _blank_source_row() -> dict[str, str]:
    row = {field: "" for field in RATEWALL_TDC_DEPOSIT_PASS_THROUGH_SOURCE_IMPORT_FIELDS}
    row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
    return row


def _scenario_row(
    *,
    scenario_id: str,
    label: str,
    period_index: int,
    period_label: str,
    value: str,
    source_id: str,
    source_field: str,
    source_status: str,
    role: str,
    default_candidate: str,
    step_enabled: str,
    stress_blocker: str,
    normal_id: str,
    source_rows: list[dict[str, str]],
) -> dict[str, str]:
    by_id = {row["source_import_row_id"]: row for row in source_rows}
    value_source = by_id.get(source_id, {})
    source_type = (
        "user_supplied_import_contract_field"
        if value_source.get("source_user_supplied_context_only") == "true"
        else "ea_tdc_artifact_field"
    )
    audit_status = (
        "pass_row_level_source_import_field_bound"
        if value_source.get("source_artifact_backed") == "true"
        and source_field
        and value_source.get(source_field, "") == value
        else "blocked_no_matching_source_import_field"
    )
    source_artifacts = sorted(
        {
            row["source_artifact_path"]
            for row in source_rows
            if row["source_artifact_backed"] == "true"
        }
    )
    source_hashes = sorted(
        {
            row["source_artifact_sha256"]
            for row in source_rows
            if row["source_artifact_sha256"]
        }
    )
    row = {field: "" for field in RATEWALL_TDC_DEPOSIT_PASS_THROUGH_REGIME_SCENARIO_FIELDS}
    row.update(
        {
            "regime_scenario_row_id": (
                f"{scenario_id}::{period_label}::tdc_deposit_pass_through"
            ),
            "regime_scenario_id": scenario_id,
            "regime_scenario_label": label,
            "period_index": str(period_index),
            "period_label": period_label,
            "period_frequency": "quarterly",
            "pass_through_value": value,
            "pass_through_source_import_row_id": source_id,
            "pass_through_value_source_type": (
                source_type
                if value_source.get("source_artifact_backed") == "true"
                else "blocked_or_missing_source_field"
            ),
            "pass_through_value_source_field": source_field,
            "pass_through_value_source_artifact_path": value_source.get(
                "source_artifact_path", ""
            ),
            "pass_through_value_source_artifact_sha256": value_source.get(
                "source_artifact_sha256", ""
            ),
            "pass_through_value_source_artifact_row_key": value_source.get(
                "source_artifact_row_key", ""
            ),
            "pass_through_value_source_audit_status": audit_status,
            "stress_assumption_blocker": stress_blocker,
            "pass_through_source_status": source_status,
            "scenario_role": role,
            "scenario_admission_status": "scenario_only_not_canonical_runtime_default",
            "dynamic_path_default_candidate": default_candidate,
            "liquidity_event_trigger_status": (
                "scenario_liquidity_event_trigger_assumed_not_evidence"
                if scenario_id == "liquidity_event_step_up"
                else "not_applicable"
            ),
            "liquidity_event_step_up_enabled": step_enabled,
            "liquidity_event_step_up_value": value
            if scenario_id == "liquidity_event_step_up"
            else "",
            "first_five_years_value_source_row_id": normal_id
            if scenario_id == "liquidity_event_step_up"
            else "",
            "scenario_only_status": (
                "noncanonical_dynamic_assumption_mode_scenario_only"
            ),
            "source_artifacts": ";".join(source_artifacts),
            "source_artifact_hashes": ";".join(source_hashes),
            "allowed_use": "dynamic_tdc_liquidity_state_scenario_review_only",
            "blocked_use": (
                "main_ratio;canonical_ratio;Evidence_Mode;denominator_prior;"
                "pricing_output;holder_allocation;raw_rate_shock"
            ),
            "claim_boundary": (
                "tdc_deposit_pass_through_regime_scenario_not_main_ratio"
            ),
        }
    )
    row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
    return row


def _trigger_row(
    *,
    source_path: Path,
    source: dict[str, str] | None,
    source_field: str,
    trigger_regime_id: str,
    trigger_regime_label: str,
    trigger_variable_family: str,
    trigger_variable_id: str,
    trigger_variable_label: str,
    trigger_statistic: str,
    trigger_direction: str,
    observed_value: str,
    observed_value_unit: str,
    observed_window_start: str,
    observed_window_end: str,
    observed_sample_or_period: str,
    linked_scenario_id: str,
    linked_source_id: str,
    linked_value: str,
) -> dict[str, str]:
    source_backed = source_path.exists() and source is not None
    source_row_key = _trigger_source_row_key(source) if source else ""
    row = {
        field: ""
        for field in RATEWALL_TDC_LIQUIDITY_REGIME_TRIGGER_EVIDENCE_FIELDS
    }
    row.update(
        {
            "trigger_evidence_row_id": "::".join(
                [
                    trigger_regime_id,
                    trigger_variable_family,
                    trigger_variable_id or "missing_variable",
                    trigger_statistic,
                    observed_window_end or observed_sample_or_period or "missing_window",
                ]
            ),
            "trigger_regime_id": trigger_regime_id,
            "trigger_regime_label": trigger_regime_label,
            "trigger_variable_family": trigger_variable_family,
            "trigger_variable_id": trigger_variable_id,
            "trigger_variable_label": trigger_variable_label,
            "trigger_statistic": trigger_statistic,
            "trigger_direction": trigger_direction,
            "trigger_source_artifact_path": _project_relative_sibling_path(source_path),
            "trigger_source_artifact_sha256": _sha256(source_path)
            if source_path.exists()
            else "",
            "trigger_source_artifact_row_key": source_row_key,
            "trigger_source_field": source_field,
            "observed_value": observed_value,
            "observed_value_unit": observed_value_unit,
            "observed_window_start": observed_window_start,
            "observed_window_end": observed_window_end,
            "observed_sample_or_period": observed_sample_or_period,
            "linked_regime_scenario_id": linked_scenario_id,
            "linked_pass_through_source_import_row_id": linked_source_id,
            "linked_pass_through_value": linked_value,
            "candidate_trigger_threshold": "",
            "candidate_trigger_threshold_status": (
                "blocked_no_promoted_trigger_threshold"
            ),
            "trigger_evidence_status": (
                "pass_source_artifact_trigger_diagnostic_extracted"
                if source_backed and observed_value != ""
                else "blocked_missing_source_trigger_diagnostic"
            ),
            "trigger_admission_status": (
                "blocked_review_only_not_runtime_trigger_or_default_selector"
            ),
            "trigger_runtime_status": (
                "blocked_no_runtime_scenario_selection_or_default_change"
            ),
            "source_backing_status": (
                "pass_source_artifact_row_backed"
                if source_backed
                else "blocked_missing_source_artifact_or_row"
            ),
            "exact_blocker": (
                "diagnostic trigger evidence lacks a reviewed promotion rule, "
                "threshold, out-of-sample validation, and runtime admission; "
                "it cannot select defaults or alter canonical mechanics"
            ),
            "next_backend_action": (
                "review trigger thresholds and validation protocol before any "
                "state-dependent scenario selector can be considered"
            ),
            "allowed_use": "tdc_liquidity_regime_trigger_review_only",
            "blocked_use": (
                "default_selection;main_ratio;canonical_ratio;Evidence_Mode;"
                "denominator_prior;pricing_output;holder_allocation;"
                "raw_rate_shock"
            ),
            "claim_boundary": (
                "tdc_liquidity_regime_trigger_evidence_not_runtime_selector"
            ),
        }
    )
    row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
    return row


def _promotion_protocol_row(
    *,
    trigger: dict[str, str],
    field_id: str,
    label: str,
    role: str,
) -> dict[str, str]:
    row = {
        field: ""
        for field in RATEWALL_TDC_LIQUIDITY_REGIME_TRIGGER_PROMOTION_PROTOCOL_FIELDS
    }
    source_provenance_value = ";".join(
        part
        for part in [
            trigger.get("trigger_source_artifact_path", ""),
            trigger.get("trigger_source_artifact_sha256", ""),
            trigger.get("trigger_source_artifact_row_key", ""),
            trigger.get("trigger_source_field", ""),
        ]
        if part
    )
    is_source_provenance = field_id == "source_provenance"
    current_value = source_provenance_value if is_source_provenance else ""
    source_status = (
        "pass_source_provenance_recorded_from_trigger_evidence"
        if is_source_provenance and source_provenance_value
        else "blocked_no_source_backed_promotion_field_value"
    )
    required_status = (
        "pass_source_provenance_recorded_review_only"
        if is_source_provenance and source_provenance_value
        else f"blocked_missing_{field_id}"
    )
    blocker = (
        "source provenance is recorded from the trigger evidence row, but the "
        "promotion protocol remains blocked until threshold, validation, "
        "out-of-sample, false-positive, state-classification, scenario-selection, "
        "and review-status fields pass"
        if is_source_provenance
        else (
            f"{label} is not populated by the trigger evidence surface; "
            "promotion requires a reviewed source-backed protocol before any "
            "runtime scenario selector or default change"
        )
    )
    row.update(
        {
            "promotion_protocol_row_id": (
                f"{trigger.get('trigger_evidence_row_id', '')}::{field_id}"
            ),
            "trigger_evidence_row_id": trigger.get("trigger_evidence_row_id", ""),
            "trigger_variable_family": trigger.get("trigger_variable_family", ""),
            "trigger_variable_id": trigger.get("trigger_variable_id", ""),
            "trigger_statistic": trigger.get("trigger_statistic", ""),
            "linked_regime_scenario_id": trigger.get("linked_regime_scenario_id", ""),
            "linked_pass_through_source_import_row_id": trigger.get(
                "linked_pass_through_source_import_row_id", ""
            ),
            "required_promotion_field": field_id,
            "required_promotion_field_label": label,
            "required_promotion_field_role": role,
            "current_protocol_value": current_value,
            "current_protocol_value_source_artifact_path": trigger.get(
                "trigger_source_artifact_path", ""
            )
            if is_source_provenance
            else "",
            "current_protocol_value_source_artifact_sha256": trigger.get(
                "trigger_source_artifact_sha256", ""
            )
            if is_source_provenance
            else "",
            "current_protocol_value_source_row_key": trigger.get(
                "trigger_source_artifact_row_key", ""
            )
            if is_source_provenance
            else "",
            "current_protocol_value_source_field": trigger.get(
                "trigger_source_field", ""
            )
            if is_source_provenance
            else "",
            "current_protocol_value_source_status": source_status,
            "required_field_status": required_status,
            "promotion_protocol_admission_status": (
                "blocked_required_promotion_protocol_fields_missing"
            ),
            "promotion_protocol_runtime_status": (
                "blocked_no_runtime_trigger_or_scenario_selection"
            ),
            "promotion_protocol_review_status": (
                "blocked_no_promotion_review_complete"
            ),
            "promotion_protocol_pass": "false",
            "exact_blocker": blocker,
            "next_backend_action": (
                "source-review and validate this required promotion field before "
                "any trigger can become a scenario selector"
            ),
            "allowed_use": "tdc_trigger_promotion_protocol_review_only",
            "blocked_use": (
                "threshold_promotion;default_selection;main_ratio;"
                "canonical_ratio;Evidence_Mode;denominator_prior;"
                "pricing_output;holder_allocation;raw_rate_shock"
            ),
            "claim_boundary": (
                "tdc_trigger_promotion_protocol_not_runtime_selector"
            ),
        }
    )
    row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
    return row


def _trigger_validation_evidence_row(
    *,
    protocol: dict[str, str],
    evidence_role: str,
    source_rows: list[dict[str, str]],
) -> dict[str, str]:
    required_field = protocol.get("required_promotion_field", "")
    source_paths = _unique_values(source_rows, "source_artifact_path")
    source_hashes = _unique_values(source_rows, "source_artifact_sha256")
    manifest_paths = _unique_values(source_rows, "source_artifact_manifest_path")
    manifest_hashes = _unique_values(source_rows, "source_artifact_manifest_sha256")
    row_keys = _unique_values(source_rows, "source_row_key")[:12]
    window_starts = _unique_values(source_rows, "window_start_quarter")
    window_ends = _unique_values(source_rows, "window_end_quarter")
    row = {
        field: ""
        for field in RATEWALL_TDC_LIQUIDITY_REGIME_TRIGGER_VALIDATION_EVIDENCE_FIELDS
    }
    row.update(
        {
            "trigger_validation_evidence_row_id": (
                f"{protocol.get('promotion_protocol_row_id', '')}::validation_evidence"
            ),
            "promotion_protocol_row_id": protocol.get("promotion_protocol_row_id", ""),
            "trigger_evidence_row_id": protocol.get("trigger_evidence_row_id", ""),
            "trigger_variable_family": protocol.get("trigger_variable_family", ""),
            "trigger_variable_id": protocol.get("trigger_variable_id", ""),
            "trigger_statistic": protocol.get("trigger_statistic", ""),
            "linked_regime_scenario_id": protocol.get(
                "linked_regime_scenario_id", ""
            ),
            "linked_pass_through_source_import_row_id": protocol.get(
                "linked_pass_through_source_import_row_id", ""
            ),
            "required_promotion_field": required_field,
            "validation_evidence_role": evidence_role,
            "validation_evidence_status": (
                "blocked_source_rows_available_but_no_promotion_grade_protocol"
                if source_rows
                else "blocked_no_source_rows_available_for_validation_field"
            ),
            "current_protocol_value": protocol.get("current_protocol_value", ""),
            "promotion_protocol_required_field_status": protocol.get(
                "required_field_status", ""
            ),
            "promotion_protocol_pass": protocol.get("promotion_protocol_pass", ""),
            "source_artifact_roles_reviewed": ";".join(
                _unique_values(source_rows, "source_artifact_role")
            ),
            "source_artifact_count": str(len(source_paths)),
            "source_row_count": str(len(source_rows)),
            "source_artifact_paths": ";".join(source_paths),
            "source_artifact_sha256s": ";".join(source_hashes),
            "source_artifact_manifest_paths": ";".join(manifest_paths),
            "source_artifact_manifest_sha256s": ";".join(manifest_hashes),
            "source_row_keys_sample": ";".join(row_keys),
            "sample_window_start_min": min(window_starts) if window_starts else "",
            "sample_window_end_max": max(window_ends) if window_ends else "",
            "candidate_validation_sample_status": _validation_field_status(
                required_field, "validation_sample"
            ),
            "candidate_out_of_sample_status": _validation_field_status(
                required_field, "out_of_sample_check"
            ),
            "candidate_false_positive_control_status": _validation_field_status(
                required_field, "false_positive_control"
            ),
            "candidate_state_classification_status": _validation_field_status(
                required_field, "state_classification_rule"
            ),
            "candidate_scenario_selection_status": _validation_field_status(
                required_field, "scenario_selection_rule"
            ),
            "trigger_validation_admission_status": (
                "blocked_trigger_validation_not_promotion_grade"
            ),
            "trigger_validation_runtime_status": (
                "blocked_no_runtime_trigger_or_scenario_selection"
            ),
            "scenario_default_allowed": "false",
            "dynamic_path_reference_allowed": "false",
            "trigger_threshold_promotion_allowed": "false",
            "runtime_scenario_selection_allowed": "false",
            "exact_blocker": _validation_exact_blocker(required_field),
            "next_backend_action": _validation_next_backend_action(required_field),
            "allowed_use": "tdc_trigger_validation_evidence_review_only",
            "blocked_use": (
                "threshold_promotion;default_selection;runtime_scenario_selection;"
                "main_ratio;canonical_ratio;Evidence_Mode;denominator_prior;"
                "pricing_output;holder_allocation;raw_rate_shock"
            ),
            "claim_boundary": (
                "tdc_trigger_validation_evidence_not_runtime_selector"
            ),
        }
    )
    row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
    return row


def _validation_field_status(required_field: str, status_field: str) -> str:
    if required_field == status_field:
        return f"blocked_{status_field}_not_promotion_grade"
    return "not_applicable_to_this_required_field"


def _validation_exact_blocker(required_field: str) -> str:
    blockers = {
        "validation_sample": (
            "EA-TDC source rows expose estimation windows and diagnostics, but no "
            "reviewed validation-sample split is admitted for trigger promotion"
        ),
        "out_of_sample_check": (
            "rolling and pandemic-exclusion diagnostics are review inputs only; "
            "no source-backed out-of-sample pass rule or tolerance is admitted"
        ),
        "false_positive_control": (
            "influence and exclusion diagnostics do not define an admitted false-"
            "positive control for liquidity-event trigger activation"
        ),
        "state_classification_rule": (
            "state-dependent diagnostics are not an admitted classifier that maps "
            "events into runtime pass-through regimes"
        ),
        "scenario_selection_rule": (
            "scenario links remain review metadata; no admitted selector can move "
            "from normal-forward to liquidity-event paths"
        ),
    }
    return blockers.get(required_field, "blocked_validation_field_not_admitted")


def _validation_next_backend_action(required_field: str) -> str:
    actions = {
        "validation_sample": (
            "define and source-review a validation split before promotion review"
        ),
        "out_of_sample_check": (
            "add a reviewed out-of-sample performance test with pass/fail tolerance"
        ),
        "false_positive_control": (
            "add a reviewed false-positive control and trigger-cost rule"
        ),
        "state_classification_rule": (
            "source-review a classifier before any state can select a path"
        ),
        "scenario_selection_rule": (
            "source-review scenario-selection semantics before runtime use"
        ),
    }
    return actions.get(required_field, "source-review this validation field")


def _scenario_contract_row(
    *,
    scenario: dict[str, str],
    contract_field: str,
    source_rows: list[dict[str, str]],
    calibration_rows: list[dict[str, str]],
    trigger_rows: list[dict[str, str]],
    protocol_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str]],
) -> dict[str, str]:
    is_normal_value = (
        scenario.get("regime_scenario_id", "") == "normal_forward"
        and contract_field == "pass_through_value"
    )
    row = {
        field: ""
        for field in RATEWALL_TDC_DEPOSIT_PASS_THROUGH_SCENARIO_CONTRACT_FIELDS
    }
    row.update(
        {
            "scenario_contract_row_id": "::".join(
                [
                    scenario.get("regime_scenario_row_id", ""),
                    contract_field,
                ]
            ),
            "regime_scenario_id": scenario.get("regime_scenario_id", ""),
            "regime_scenario_label": scenario.get("regime_scenario_label", ""),
            "period_index": scenario.get("period_index", ""),
            "period_label": scenario.get("period_label", ""),
            "contract_field": contract_field,
            "contract_value": _scenario_contract_value(
                scenario=scenario,
                contract_field=contract_field,
                source_rows=source_rows,
                calibration_rows=calibration_rows,
                trigger_rows=trigger_rows,
                protocol_rows=protocol_rows,
                validation_rows=validation_rows,
            ),
            "contract_unit": _scenario_contract_unit(contract_field),
            "value_role": _scenario_contract_value_role(contract_field),
            "source_import_row_id": ";".join(
                _unique_values(source_rows, "source_import_row_id")
            ),
            "regime_scenario_row_id": scenario.get("regime_scenario_row_id", ""),
            "source_import_artifact_path": ";".join(
                _unique_values(source_rows, "source_artifact_path")
            ),
            "source_import_artifact_sha256": ";".join(
                _unique_values(source_rows, "source_artifact_sha256")
            ),
            "source_import_artifact_row_key": ";".join(
                _unique_values(source_rows, "source_artifact_row_key")
            ),
            "source_import_source_field": scenario.get(
                "pass_through_value_source_field", "pass_through_point"
            )
            if contract_field != "pandemic_exclusion_diagnostic"
            else "pass_through_point",
            "regime_scenario_source_field": scenario.get(
                "pass_through_value_source_field", ""
            ),
            "regime_scenario_source_status": scenario.get(
                "pass_through_source_status", ""
            ),
            "calibration_import_row_ids": ";".join(
                _unique_values(calibration_rows, "calibration_import_row_id")
            ),
            "calibration_import_source_row_keys": ";".join(
                _unique_values(calibration_rows, "source_row_key")
            ),
            "calibration_import_artifact_paths": ";".join(
                _unique_values(calibration_rows, "source_artifact_path")
            ),
            "calibration_import_artifact_sha256s": ";".join(
                _unique_values(calibration_rows, "source_artifact_sha256")
            ),
            "trigger_evidence_row_ids": ";".join(
                _unique_values(trigger_rows, "trigger_evidence_row_id")
            ),
            "trigger_evidence_artifact_paths": ";".join(
                _unique_values(trigger_rows, "trigger_source_artifact_path")
            ),
            "trigger_evidence_artifact_sha256s": ";".join(
                _unique_values(trigger_rows, "trigger_source_artifact_sha256")
            ),
            "trigger_promotion_protocol_row_ids": ";".join(
                _unique_values(protocol_rows, "promotion_protocol_row_id")
            ),
            "trigger_promotion_source_artifact_paths": ";".join(
                _unique_values(protocol_rows, "current_protocol_value_source_artifact_path")
            ),
            "trigger_promotion_source_artifact_sha256s": ";".join(
                _unique_values(protocol_rows, "current_protocol_value_source_artifact_sha256")
            ),
            "trigger_validation_evidence_row_ids": ";".join(
                _unique_values(validation_rows, "trigger_validation_evidence_row_id")
            ),
            "trigger_validation_source_artifact_paths": ";".join(
                _unique_values(validation_rows, "source_artifact_paths")
            ),
            "trigger_validation_source_artifact_sha256s": ";".join(
                _unique_values(validation_rows, "source_artifact_sha256s")
            ),
            "source_join_status": _scenario_contract_join_status(
                source_rows=source_rows,
                calibration_rows=calibration_rows,
                trigger_rows=trigger_rows,
                protocol_rows=protocol_rows,
                validation_rows=validation_rows,
            ),
            "trigger_required": "false"
            if scenario.get("regime_scenario_id", "") == "normal_forward"
            else "true",
            "trigger_protocol_required": "true",
            "trigger_validation_status": (
                "blocked_trigger_validation_not_promotion_grade"
            ),
            "scenario_default_allowed": "false",
            "dynamic_path_reference_allowed": "true" if is_normal_value else "false",
            "runtime_scenario_selection_allowed": "false",
            "source_backed_dynamic_reference_allowed": "true"
            if is_normal_value
            else "false",
            "admission_status": (
                "source_bound_dynamic_reference_only_not_runtime_selector"
                if is_normal_value
                else "blocked_or_diagnostic_only"
            ),
            "exact_blocker": _scenario_contract_blocker(
                scenario.get("regime_scenario_id", ""), contract_field
            ),
            "allowed_use": "tdc_deposit_pass_through_scenario_contract_review_only",
            "blocked_use": (
                "runtime_scenario_selection;default_selection;main_ratio;"
                "canonical_ratio;Evidence_Mode;denominator_prior;pricing_output;"
                "holder_allocation;raw_rate_shock"
            ),
            "claim_boundary": (
                "tdc_deposit_pass_through_scenario_contract_not_runtime_selector"
            ),
            "evidence_mode_allowed": "false",
            "main_ratio_allowed": "false",
            "pricing_output_allowed": "false",
            "holder_allocation_allowed": "false",
            "raw_rate_shock_output_allowed": "false",
        }
    )
    row.update({field: "false" for field in FORBIDDEN_SWITCH_FIELDS})
    return row


def _scenario_contract_value(
    *,
    scenario: dict[str, str],
    contract_field: str,
    source_rows: list[dict[str, str]],
    calibration_rows: list[dict[str, str]],
    trigger_rows: list[dict[str, str]],
    protocol_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str]],
) -> str:
    if contract_field == "pass_through_value":
        return scenario.get("pass_through_value", "")
    if contract_field == "source_import_provenance":
        return ";".join(_unique_values(source_rows, "source_import_row_id"))
    if contract_field == "ea_tdc_calibration_import_provenance":
        return ";".join(_unique_values(calibration_rows, "calibration_import_row_id"))
    if contract_field == "trigger_evidence_review":
        return ";".join(_unique_values(trigger_rows, "trigger_evidence_row_id"))
    if contract_field == "trigger_promotion_protocol":
        return ";".join(_unique_values(protocol_rows, "promotion_protocol_row_id"))
    if contract_field == "trigger_validation_evidence":
        return ";".join(
            _unique_values(validation_rows, "trigger_validation_evidence_row_id")
        )
    if contract_field == "pandemic_exclusion_diagnostic":
        return ";".join(
            f"{row.get('source_import_row_id', '')}={row.get('pass_through_point', '')}"
            for row in source_rows
            if row.get("source_import_row_id", "") and row.get("pass_through_point", "")
        )
    return ""


def _scenario_contract_unit(contract_field: str) -> str:
    if contract_field in {"pass_through_value", "pandemic_exclusion_diagnostic"}:
        return "dollars_per_dollar_tdc"
    return "provenance_row_id"


def _scenario_contract_value_role(contract_field: str) -> str:
    roles = {
        "pass_through_value": "point_or_source_bound_stress_bound",
        "source_import_provenance": "source_import_row_trace",
        "ea_tdc_calibration_import_provenance": "calibration_import_row_trace",
        "trigger_evidence_review": "trigger_evidence_row_trace",
        "trigger_promotion_protocol": "promotion_protocol_row_trace",
        "trigger_validation_evidence": "validation_evidence_row_trace",
        "pandemic_exclusion_diagnostic": "pandemic_exclusion_review_diagnostic",
    }
    return roles.get(contract_field, "review_only")


def _scenario_contract_join_status(
    *,
    source_rows: list[dict[str, str]],
    calibration_rows: list[dict[str, str]],
    trigger_rows: list[dict[str, str]],
    protocol_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str]],
) -> str:
    import_contract_rows = bool(source_rows) and all(
        row.get("source_user_supplied_context_only") == "true" for row in source_rows
    )
    if (
        source_rows
        and (calibration_rows or import_contract_rows)
        and trigger_rows
        and protocol_rows
        and validation_rows
    ):
        return "pass_source_bound_review_contract_joined"
    return "blocked_missing_one_or_more_contract_source_surfaces"


def _scenario_contract_blocker(scenario_id: str, contract_field: str) -> str:
    if scenario_id == "normal_forward" and contract_field == "pass_through_value":
        return (
            "normal-forward remains a source-bound dynamic reference only; it is "
            "not a trigger-selected runtime regime and cannot update the main "
            "ratio, denominator priors, Evidence Mode, pricing, holder "
            "allocation, or raw-rate-shock outputs"
        )
    return (
        "scenario-contract row is review-only; trigger thresholds, promotion "
        "protocol, validation sample, out-of-sample checks, false-positive "
        "controls, state classification, and runtime selection remain blocked"
    )


def _calibration_rows_for_source(
    *,
    source_row: dict[str, str],
    calibration_import_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not source_row:
        return []
    source_path = source_row.get("source_artifact_path", "")
    outcome = source_row.get("outcome", "")
    horizon = source_row.get("horizon", "")
    source_id = source_row.get("source_import_row_id", "")
    drop_rule = _drop_rule_from_source_import_id(source_id)
    candidates = [
        row
        for row in calibration_import_rows
        if row.get("source_artifact_path", "") == source_path
        and row.get("imported_outcome", "") == outcome
        and row.get("imported_horizon", "") == horizon
    ]
    if drop_rule:
        matches = [row for row in candidates if row.get("drop_rule", "") == drop_rule]
        return matches or candidates
    if source_row.get("window_end_quarter", ""):
        matches = [
            row
            for row in candidates
            if row.get("window_end_quarter", "") == source_row["window_end_quarter"]
            and row.get("window_start_quarter", "")
            == source_row.get("window_start_quarter", "")
        ]
        return matches or candidates
    if source_row.get("sample_label", ""):
        matches = [
            row
            for row in candidates
            if row.get("sample_label", "") == source_row["sample_label"]
        ]
        return matches or candidates
    return candidates


def _pandemic_calibration_rows(
    calibration_import_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        row
        for row in calibration_import_rows
        if row.get("source_artifact_role", "") == "pandemic_exclusion_diagnostics"
        and row.get("imported_outcome", "") == "matched_total_deposits"
        and row.get("drop_rule", "") in {"drop_2020_2021", "drop_2020", "drop_2021"}
    ]


def _drop_rule_from_source_import_id(source_import_row_id: str) -> str:
    mapping = {
        "ea_tdc_pandemic_exclusion_drop_2020q1_2021q4": "drop_2020_2021",
        "ea_tdc_pandemic_exclusion_drop_2020": "drop_2020",
        "ea_tdc_pandemic_exclusion_drop_2021": "drop_2021",
    }
    return mapping.get(source_import_row_id, "")


def _unique_values(rows: list[dict[str, str]], field: str) -> list[str]:
    return sorted({row.get(field, "") for row in rows if row.get(field, "")})


def _source_artifact_handle(row: dict[str, str]) -> str:
    roles = row.get("source_artifact_roles_reviewed", "")
    hashes = row.get("source_artifact_sha256s", "")
    if roles and hashes:
        return f"{roles}::{hashlib.sha256(hashes.encode('utf-8')).hexdigest()[:12]}"
    if roles:
        return roles
    if hashes:
        return hashlib.sha256(hashes.encode("utf-8")).hexdigest()[:12]
    return "missing_source_artifact_handle"


def _protocol_field_status(
    protocol_rows: list[dict[str, str]], required_field: str
) -> str:
    matches = [
        row
        for row in protocol_rows
        if row.get("required_promotion_field") == required_field
    ]
    if not matches:
        return "blocked_missing_required_promotion_protocol_field"
    values = _unique_values(matches, "required_field_status")
    if values:
        return ";".join(values)
    return ";".join(_unique_values(matches, "promotion_protocol_admission_status"))


def _trigger_source_row_key(row: dict[str, str]) -> str:
    keys = [
        "job_id",
        "window_start_quarter",
        "window_end_quarter",
        "feature_group",
        "feature_id",
        "feature_stat",
        "period",
        "outcome",
        "drop_rule",
        "sample_label",
    ]
    return "::".join(row.get(key, "") for key in keys if row.get(key, ""))


def _feature_unit(feature_id: str, stat: str) -> str:
    if "share" in feature_id:
        return "window_share"
    if feature_id.endswith("_mil") or stat in {"window_abs_mean", "window_sd"}:
        return "usd_millions_or_source_reported_window_stat"
    if stat == "tdc_feature_correlation":
        return "pearson_correlation_with_tdc_within_window"
    return "source_reported_window_statistic"


def _period_label(start_period: str, period_index: int) -> str:
    year_text, quarter_text = start_period.split("Q", maxsplit=1)
    year = int(year_text)
    quarter = int(quarter_text)
    zero_based = (quarter - 1) + period_index
    return f"{year + zero_based // 4}Q{(zero_based % 4) + 1}"


def _project_relative_sibling_path(path: Path) -> str:
    return os.path.relpath(path.resolve(), Path.cwd().resolve())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_row_key(row: dict[str, str]) -> str:
    return "::".join(
        part
        for part in [
            row.get("job_id", ""),
            row.get("outcome", ""),
            f"h{row.get('horizon', '')}",
            row.get("sample_label", ""),
            row.get("window_end_quarter", ""),
        ]
        if part
    )


def _divide_if_percent_points(value: str) -> str:
    if not value:
        return ""
    try:
        return str(Decimal(value) / Decimal("100"))
    except Exception:
        return ""


def _first(items: Iterable[dict[str, str]]) -> dict[str, str] | None:
    for item in items:
        return item
    return None
