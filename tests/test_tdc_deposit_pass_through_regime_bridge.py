from __future__ import annotations

import csv
import hashlib
from decimal import Decimal
from pathlib import Path

import pytest



pytestmark = pytest.mark.full_surface

OUTPUT_TABLES = Path("outputs/tables")
CALIBRATION_IMPORT = (
    OUTPUT_TABLES / "ratewall_tdc_ea_tdc_pass_through_calibration_import.csv"
)
SOURCE_IMPORT = OUTPUT_TABLES / "ratewall_tdc_deposit_pass_through_source_import.csv"
REGIME_SCENARIOS = (
    OUTPUT_TABLES / "ratewall_tdc_deposit_pass_through_regime_scenarios.csv"
)
SCENARIO_CONTRACT = (
    OUTPUT_TABLES / "ratewall_tdc_deposit_pass_through_scenario_contract.csv"
)
TRIGGER_VALIDATION_PREFLIGHT = (
    OUTPUT_TABLES
    / "ratewall_tdc_deposit_pass_through_trigger_validation_preflight.csv"
)
SCENARIO_CONTRACT_INVARIANT = (
    OUTPUT_TABLES
    / "ratewall_tdc_deposit_pass_through_scenario_contract_invariant_audit.csv"
)
TRIGGER_EVIDENCE = (
    OUTPUT_TABLES / "ratewall_tdc_liquidity_regime_trigger_evidence.csv"
)
PROMOTION_PROTOCOL = (
    OUTPUT_TABLES / "ratewall_tdc_liquidity_regime_trigger_promotion_protocol.csv"
)
VALIDATION_EVIDENCE = (
    OUTPUT_TABLES / "ratewall_tdc_liquidity_regime_trigger_validation_evidence.csv"
)
DYNAMIC_UNCERTAINTY_ENVELOPE = (
    OUTPUT_TABLES / "ratewall_dynamic_uncertainty_envelope.csv"
)
TDC_MATERIALIZATION_SEMANTIC_SUMMARY = (
    OUTPUT_TABLES / "ratewall_tdc_materialization_semantic_summary.csv"
)
PAPER_EA_TDC = Path(
    "../ea-tdc/output/models/paper_tier2_selected_credit_rate_lags_estimates.csv"
)
ROLLING_EA_TDC = Path(
    "../ea-tdc/output/models/tier2_rolling_selected_credit_rate_pass_through_estimates.csv"
)
PANDEMIC_EA_TDC = Path(
    "../ea-tdc/output/models/tdc_deposit_pass_through_pandemic_exclusion_diagnostics.csv"
)
ROLLING_MINUS_PANDEMIC_EA_TDC = Path(
    "../ea-tdc/output/reports/tier2_pass_through_rolling_minus_pandemic_betas.csv"
)
INFLUENCE_EA_TDC = Path(
    "../ea-tdc/output/reports/tier2_pass_through_influence_quarters.csv"
)
ROLLING_FEATURES_EA_TDC = Path(
    "../ea-tdc/output/reports/tier2_pass_through_offset_rolling_beta_features.csv"
)
ROLLING_CORRELATES_EA_TDC = Path(
    "../ea-tdc/output/reports/tier2_pass_through_offset_rolling_beta_correlates.csv"
)
EPISODE_BETAS_EA_TDC = Path(
    "../ea-tdc/output/reports/tier2_pass_through_offset_episode_betas.csv"
)
EVIDENCE_B_LOCAL_SOURCE_FILENAME = (
    "ratewall_" + "dis" + "patchB_tdc_roadmap_response_20260609.md"
)
EVIDENCE_B_TDC_ROADMAP = (
    Path.home()
    / "sync/act/temp/ratewall"
    / EVIDENCE_B_LOCAL_SOURCE_FILENAME
)

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


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        digest.update(handle.read())
    return digest.hexdigest()


def test_ea_tdc_pass_through_calibration_import_versions_source_rows() -> None:
    rows = _rows(CALIBRATION_IMPORT)
    assert len(rows) == 677
    roles = {row["source_artifact_role"] for row in rows}
    assert {
        "selected_credit_rate_lags_paper_estimates",
        "rolling_beta_estimates",
        "pandemic_exclusion_diagnostics",
        "episode_beta_diagnostics",
        "rolling_minus_pandemic_diagnostics",
        "influence_quarter_diagnostics",
        "state_dep_low_reserves",
        "state_dep_on_rrp_drain",
        "state_dep_bank_short_share",
        "state_dep_bank_foreign_private_corr",
        "state_dep_slr_bank_leverage_pressure",
        "component_state_dep_ru_acquisition_low_reserves",
        "component_state_dep_treasury_cash_drain_on_rrp_drain",
    } == roles
    by_role = {}
    for row in rows:
        by_role.setdefault(row["source_artifact_role"], []).append(row)
    assert len(by_role["rolling_beta_estimates"]) == 118
    assert len(by_role["rolling_minus_pandemic_diagnostics"]) == 156
    assert len(by_role["influence_quarter_diagnostics"]) == 192
    assert len(by_role["pandemic_exclusion_diagnostics"]) == 12
    assert {
        row["source_artifact_sha256"]
        for row in by_role["rolling_beta_estimates"]
    } == {_sha256(ROLLING_EA_TDC)}
    assert {
        row["source_artifact_sha256"]
        for row in by_role["pandemic_exclusion_diagnostics"]
    } == {_sha256(PANDEMIC_EA_TDC)}
    assert {
        row["source_artifact_sha256"]
        for row in by_role["rolling_minus_pandemic_diagnostics"]
    } == {_sha256(ROLLING_MINUS_PANDEMIC_EA_TDC)}
    assert {
        row["source_artifact_sha256"]
        for row in by_role["influence_quarter_diagnostics"]
    } == {_sha256(INFLUENCE_EA_TDC)}
    assert all(row["source_row_key"] for row in rows)
    assert {
        row["import_status"] for row in by_role["state_dep_bank_short_share"]
    } == {"blocked_missing_ea_tdc_artifact_or_rows"}
    assert {
        row["import_status"] for row in rows if row["source_artifact_role"] != "state_dep_bank_short_share"
    } == {"pass_ea_tdc_source_row_versioned_review_only"}
    assert all(row["scenario_default_allowed"] == "false" for row in rows)
    assert all(row["dynamic_path_reference_allowed"] == "false" for row in rows)
    assert all(row[field] == "false" for row in rows for field in FORBIDDEN_SWITCH_FIELDS)


def test_ea_tdc_calibration_import_is_ledgered_fail_closed_invariant() -> None:
    rows = _rows(CALIBRATION_IMPORT)
    ledger_rows = _rows(OUTPUT_TABLES / "ratewall_assumption_source_backing_ledger.csv")
    import_ledger = [
        row
        for row in ledger_rows
        if row["assumption_family"] == "tdc_ea_tdc_pass_through_calibration_import"
    ]
    assert len(import_ledger) == len(rows)
    assert {row["source_backing_class"] for row in import_ledger} == {
        "blocked_or_diagnostic_only"
    }
    assert all(row["enters_dynamic_path"] == "false" for row in import_ledger)
    assert all(row["enters_canonical_ratio"] == "false" for row in import_ledger)
    assert all(row["prior_narrowing_allowed"] == "false" for row in import_ledger)
    assert all(row["pricing_output_enabled"] == "false" for row in import_ledger)
    assert all(row["holder_allocation_enabled"] == "false" for row in import_ledger)
    assert all(row["raw_rate_shock_enabled"] == "false" for row in import_ledger)

    invariant_rows = _rows(
        OUTPUT_TABLES / "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    by_check = {row["audit_item"]: row for row in invariant_rows}
    assert by_check[
        "tdc_ea_tdc_pass_through_calibration_import_fail_closed"
    ]["audit_status"] == "pass"


def test_tdc_deposit_pass_through_source_import_hashes_ea_tdc_artifacts() -> None:
    rows = _rows(SOURCE_IMPORT)
    by_id = {row["source_import_row_id"]: row for row in rows}
    assert by_id["ea_tdc_paper_matched_total_deposits_h0"][
        "pass_through_point"
    ] == "0.6163494354563133"
    assert by_id["ea_tdc_paper_matched_total_deposits_h1"][
        "pass_through_point"
    ] == "0.3248830543813559"
    assert by_id["ea_tdc_paper_matched_total_deposits_h1"][
        "scenario_default_allowed"
    ] == "false"
    assert by_id["ea_tdc_paper_matched_total_deposits_h1"][
        "dynamic_path_reference_allowed"
    ] == "false"
    assert by_id["evidence_b_import_contract_normal_forward_h0"][
        "pass_through_point"
    ] == "0.34201759129420367"
    assert by_id["evidence_b_import_contract_normal_forward_h0"][
        "scenario_default_allowed"
    ] == "true"
    assert by_id["evidence_b_import_contract_normal_forward_h0"][
        "dynamic_path_reference_allowed"
    ] == "true"
    assert by_id["evidence_b_import_contract_normal_forward_h0"][
        "source_user_supplied_context_only"
    ] == "true"
    assert by_id["ea_tdc_latest_rolling_matched_total_deposits_h0"][
        "pass_through_point"
    ] == "0.5307509589554447"
    assert by_id["ea_tdc_paper_matched_total_deposits_h0"][
        "source_artifact_sha256"
    ] == _sha256(PAPER_EA_TDC)
    assert by_id["ea_tdc_latest_rolling_matched_total_deposits_h0"][
        "source_artifact_sha256"
    ] == _sha256(ROLLING_EA_TDC)
    assert by_id["ea_tdc_pandemic_exclusion_drop_2020q1_2021q4"][
        "source_artifact_sha256"
    ] == _sha256(PANDEMIC_EA_TDC)
    assert by_id["evidence_b_import_contract_normal_forward_h0"][
        "source_artifact_sha256"
    ] == _sha256(EVIDENCE_B_TDC_ROADMAP)


def test_pandemic_diagnostics_are_artifact_backed_but_not_defaults() -> None:
    rows = _rows(SOURCE_IMPORT)
    diagnostic_rows = [
        row
        for row in rows
        if row["source_import_row_id"].startswith("ea_tdc_pandemic_exclusion_")
    ]
    assert {row["source_import_row_id"]: row["pass_through_point"] for row in diagnostic_rows} == {
        "ea_tdc_pandemic_exclusion_drop_2020q1_2021q4": "0.4462798011574685",
        "ea_tdc_pandemic_exclusion_drop_2020": "0.2478871263682468",
        "ea_tdc_pandemic_exclusion_drop_2021": "0.7431033707535825",
    }
    assert all(row["source_project"] == "ea-tdc" for row in diagnostic_rows)
    assert all(row["source_artifact_backed"] == "true" for row in diagnostic_rows)
    assert all(row["source_user_supplied_context_only"] == "false" for row in diagnostic_rows)
    assert all(row["scenario_default_allowed"] == "false" for row in diagnostic_rows)
    assert all(
        row["dynamic_path_reference_allowed"] == "false" for row in diagnostic_rows
    )


def test_tdc_deposit_pass_through_regime_scenarios_are_noncanonical() -> None:
    rows = _rows(REGIME_SCENARIOS)
    assert len(rows) == 96
    assert {row["regime_scenario_id"] for row in rows} == {
        "normal_forward",
        "latest_rolling_persistence",
        "full_sample_high_liquidity",
        "liquidity_event_step_up",
    }
    normal_rows = [
        row for row in rows if row["regime_scenario_id"] == "normal_forward"
    ]
    assert {row["pass_through_value"] for row in normal_rows} == {
        "0.34201759129420367"
    }
    assert {row["pass_through_source_import_row_id"] for row in normal_rows} == {
        "evidence_b_import_contract_normal_forward_h0"
    }
    step_rows = [
        row for row in rows if row["regime_scenario_id"] == "liquidity_event_step_up"
    ]
    assert {row["pass_through_value"] for row in step_rows[:20]} == {
        "0.34201759129420367"
    }
    assert {row["pass_through_value"] for row in step_rows[20:]} == {
        "0.5685311077760121"
    }
    assert all(
        row["pass_through_source_import_row_id"]
        == "evidence_b_import_contract_normal_forward_h0"
        for row in step_rows[20:]
    )
    assert all(
        row["pass_through_value_source_type"] == "user_supplied_import_contract_field"
        and row["pass_through_value_source_field"] == "pass_through_upper95"
        and row["pass_through_value_source_artifact_path"]
        == f"../../../sync/act/temp/ratewall/{EVIDENCE_B_LOCAL_SOURCE_FILENAME}"
        and row["pass_through_value_source_artifact_sha256"]
        == _sha256(EVIDENCE_B_TDC_ROADMAP)
        and row["pass_through_value_source_artifact_row_key"]
        and row["pass_through_value_source_audit_status"]
        == "pass_row_level_source_import_field_bound"
        and "not a default" in row["stress_assumption_blocker"]
        for row in step_rows[20:]
    )
    assert all(
        row["pass_through_value_source_audit_status"]
        == "pass_row_level_source_import_field_bound"
        and row["pass_through_value_source_artifact_path"]
        and row["pass_through_value_source_artifact_sha256"]
        and row["pass_through_value_source_artifact_row_key"]
        for row in rows
    )
    for row in rows:
        assert all(row[field] == "false" for field in FORBIDDEN_SWITCH_FIELDS)


def test_tdc_pass_through_bridge_is_ledgered_noncanonical() -> None:
    ledger_rows = _rows(OUTPUT_TABLES / "ratewall_assumption_source_backing_ledger.csv")
    bridge_rows = [
        row
        for row in ledger_rows
        if row["assumption_family"] == "tdc_deposit_pass_through_regime_bridge"
    ]
    assert bridge_rows
    assert {
        row["source_backing_class"] for row in bridge_rows
    } <= {"sibling_contract_value", "scenario_assumption", "blocked_or_diagnostic_only"}
    step_ledger_rows = [
        row
        for row in bridge_rows
        if row["artifact_or_surface"]
        == "ratewall_tdc_deposit_pass_through_regime_scenarios.csv"
        and row["scenario_or_path_scope"] == "liquidity_event_step_up"
        and row["period_or_horizon"] >= "2031Q2"
    ]
    assert step_ledger_rows
    assert all(
        row["source_artifact"]
        == f"../../../sync/act/temp/ratewall/{EVIDENCE_B_LOCAL_SOURCE_FILENAME}"
        and row["source_hash_or_manifest_hash"] == _sha256(EVIDENCE_B_TDC_ROADMAP)
        and "pass_through_upper95" in row["source_field_or_series"]
        for row in step_ledger_rows
    )
    assert all(row["enters_canonical_ratio"] == "false" for row in bridge_rows)


def test_tdc_pass_through_scenario_contract_is_source_bound_fail_closed() -> None:
    rows = _rows(SCENARIO_CONTRACT)
    assert len(rows) == 672
    assert {row["contract_field"] for row in rows} == {
        "pass_through_value",
        "source_import_provenance",
        "ea_tdc_calibration_import_provenance",
        "trigger_evidence_review",
        "trigger_promotion_protocol",
        "trigger_validation_evidence",
        "pandemic_exclusion_diagnostic",
    }
    assert {row["regime_scenario_id"] for row in rows} == {
        "normal_forward",
        "latest_rolling_persistence",
        "full_sample_high_liquidity",
        "liquidity_event_step_up",
    }
    assert {row["source_join_status"] for row in rows} == {
        "pass_source_bound_review_contract_joined"
    }
    assert all(row["source_import_row_id"] for row in rows)
    assert all(row["regime_scenario_row_id"] for row in rows)
    assert all(row["source_import_artifact_sha256"] for row in rows)
    assert all(
        row["calibration_import_artifact_sha256s"]
        or row["source_import_row_id"] == "evidence_b_import_contract_normal_forward_h0"
        for row in rows
    )
    assert all(row["trigger_evidence_artifact_sha256s"] for row in rows)
    assert all(row["trigger_promotion_protocol_row_ids"] for row in rows)
    assert all(row["trigger_validation_evidence_row_ids"] for row in rows)

    normal_reference_rows = [
        row
        for row in rows
        if row["dynamic_path_reference_allowed"] == "true"
    ]
    assert len(normal_reference_rows) == 24
    assert {
        row["regime_scenario_id"] for row in normal_reference_rows
    } == {"normal_forward"}
    assert {row["contract_field"] for row in normal_reference_rows} == {
        "pass_through_value"
    }
    assert {row["source_backed_dynamic_reference_allowed"] for row in normal_reference_rows} == {
        "true"
    }
    assert all(row["scenario_default_allowed"] == "false" for row in rows)
    assert all(row["runtime_scenario_selection_allowed"] == "false" for row in rows)
    assert all(row["main_ratio_allowed"] == "false" for row in rows)
    assert all(row["evidence_mode_allowed"] == "false" for row in rows)
    assert all(row["pricing_output_allowed"] == "false" for row in rows)
    assert all(row["holder_allocation_allowed"] == "false" for row in rows)
    assert all(row["raw_rate_shock_output_allowed"] == "false" for row in rows)
    assert all(row[field] == "false" for row in rows for field in FORBIDDEN_SWITCH_FIELDS)

    step_value_rows = [
        row
        for row in rows
        if row["regime_scenario_id"] == "liquidity_event_step_up"
        and row["contract_field"] == "pass_through_value"
    ]
    assert {row["contract_value"] for row in step_value_rows[:20]} == {
        "0.34201759129420367"
    }
    assert {row["contract_value"] for row in step_value_rows[20:]} == {
        "0.5685311077760121"
    }
    assert all(
        row["source_import_source_field"] == "pass_through_upper95"
        for row in step_value_rows[20:]
    )

    pandemic_rows = [
        row for row in rows if row["contract_field"] == "pandemic_exclusion_diagnostic"
    ]
    assert len(pandemic_rows) == 96
    assert all(
        "ea_tdc_pandemic_exclusion_drop_2020q1_2021q4=0.4462798011574685"
        in row["contract_value"]
        and "ea_tdc_pandemic_exclusion_drop_2020=0.2478871263682468"
        in row["contract_value"]
        and "ea_tdc_pandemic_exclusion_drop_2021=0.7431033707535825"
        in row["contract_value"]
        for row in pandemic_rows
    )


def test_tdc_pass_through_scenario_contract_is_ledgered_fail_closed_invariant() -> None:
    rows = _rows(SCENARIO_CONTRACT)
    ledger_rows = _rows(OUTPUT_TABLES / "ratewall_assumption_source_backing_ledger.csv")
    contract_ledger = [
        row
        for row in ledger_rows
        if row["assumption_family"] == "tdc_deposit_pass_through_scenario_contract"
    ]
    assert len(contract_ledger) == len(rows)
    assert {row["source_backing_class"] for row in contract_ledger} == {
        "blocked_or_diagnostic_only"
    }
    assert all(row["enters_canonical_ratio"] == "false" for row in contract_ledger)
    assert all(row["prior_narrowing_allowed"] == "false" for row in contract_ledger)
    assert all(row["pricing_output_enabled"] == "false" for row in contract_ledger)
    assert all(row["holder_allocation_enabled"] == "false" for row in contract_ledger)
    assert all(row["raw_rate_shock_enabled"] == "false" for row in contract_ledger)

    invariant_rows = _rows(
        OUTPUT_TABLES / "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    by_check = {row["audit_item"]: row for row in invariant_rows}
    assert by_check[
        "tdc_deposit_pass_through_scenario_contract_fail_closed"
    ]["audit_status"] == "pass"

def test_tdc_liquidity_regime_trigger_evidence_is_review_only() -> None:
    rows = _rows(TRIGGER_EVIDENCE)
    assert len(rows) >= 20
    assert {
        "pandemic_window_composition",
        "tdc_scale",
        "treasury_plumbing",
        "reserve_plumbing",
        "on_rrp_mmf_plumbing",
        "pass_through_episode_beta",
    } <= {row["trigger_variable_family"] for row in rows}
    assert {
        "share_2020_2021",
        "tdc_mean_abs_mil",
        "tdc_max_abs_mil",
        "tga_balance_qoq",
        "reserve_balances_qoq",
        "on_rrp_balance_qoq",
        "mmf_on_rrp_plumbing_absorption_qoq",
    } <= {row["trigger_variable_id"] for row in rows}
    assert all(row["trigger_source_artifact_path"] for row in rows)
    assert all(row["trigger_source_artifact_sha256"] for row in rows)
    assert all(row["trigger_source_artifact_row_key"] for row in rows)
    assert all(row["observed_value"] for row in rows)
    assert all(
        row["candidate_trigger_threshold_status"]
        == "blocked_no_promoted_trigger_threshold"
        for row in rows
    )
    assert all(
        row["trigger_admission_status"]
        == "blocked_review_only_not_runtime_trigger_or_default_selector"
        for row in rows
    )
    assert all(
        row["trigger_runtime_status"]
        == "blocked_no_runtime_scenario_selection_or_default_change"
        for row in rows
    )
    assert all(
        row["allowed_use"] == "tdc_liquidity_regime_trigger_review_only"
        for row in rows
    )
    assert all(
        "default_selection" in row["blocked_use"]
        and "Evidence_Mode" in row["blocked_use"]
        for row in rows
    )
    assert all(row[field] == "false" for row in rows for field in FORBIDDEN_SWITCH_FIELDS)
    by_path = {row["trigger_source_artifact_path"]: row["trigger_source_artifact_sha256"] for row in rows}
    assert by_path[
        "../ea-tdc/output/reports/tier2_pass_through_offset_rolling_beta_features.csv"
    ] == _sha256(ROLLING_FEATURES_EA_TDC)
    assert by_path[
        "../ea-tdc/output/reports/tier2_pass_through_offset_rolling_beta_correlates.csv"
    ] == _sha256(ROLLING_CORRELATES_EA_TDC)
    assert by_path[
        "../ea-tdc/output/reports/tier2_pass_through_offset_episode_betas.csv"
    ] == _sha256(EPISODE_BETAS_EA_TDC)
    assert by_path[
        "../ea-tdc/output/models/tdc_deposit_pass_through_pandemic_exclusion_diagnostics.csv"
    ] == _sha256(PANDEMIC_EA_TDC)

    ledger_rows = _rows(OUTPUT_TABLES / "ratewall_assumption_source_backing_ledger.csv")
    trigger_ledger = [
        row
        for row in ledger_rows
        if row["assumption_family"] == "tdc_liquidity_regime_trigger_evidence"
    ]
    assert len(trigger_ledger) == len(rows)
    assert {row["source_backing_class"] for row in trigger_ledger} == {
        "blocked_or_diagnostic_only"
    }
    assert all(row["enters_dynamic_path"] == "false" for row in trigger_ledger)
    assert all(row["enters_canonical_ratio"] == "false" for row in trigger_ledger)
    assert all(row["prior_narrowing_allowed"] == "false" for row in trigger_ledger)
    assert all(row["pricing_output_enabled"] == "false" for row in trigger_ledger)
    assert all(row["holder_allocation_enabled"] == "false" for row in trigger_ledger)
    assert all(row["raw_rate_shock_enabled"] == "false" for row in trigger_ledger)


def test_tdc_trigger_evidence_fail_closed_invariant() -> None:
    invariant_rows = _rows(
        OUTPUT_TABLES / "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    by_check = {row["audit_item"]: row for row in invariant_rows}
    assert by_check["tdc_liquidity_regime_trigger_evidence_fail_closed"][
        "audit_status"
    ] == "pass"

def test_tdc_trigger_promotion_protocol_is_fail_closed() -> None:
    trigger_rows = _rows(TRIGGER_EVIDENCE)
    protocol_rows = _rows(PROMOTION_PROTOCOL)
    required_fields = {
        "trigger_threshold_rule",
        "validation_sample",
        "out_of_sample_check",
        "false_positive_control",
        "state_classification_rule",
        "scenario_selection_rule",
        "source_provenance",
        "review_status",
    }
    assert len(protocol_rows) == len(trigger_rows) * len(required_fields)
    assert {row["required_promotion_field"] for row in protocol_rows} == required_fields
    by_trigger = {}
    for row in protocol_rows:
        by_trigger.setdefault(row["trigger_evidence_row_id"], set()).add(
            row["required_promotion_field"]
        )
    assert set(by_trigger) == {row["trigger_evidence_row_id"] for row in trigger_rows}
    assert all(fields == required_fields for fields in by_trigger.values())
    assert all(
        row["promotion_protocol_admission_status"]
        == "blocked_required_promotion_protocol_fields_missing"
        for row in protocol_rows
    )
    assert all(
        row["promotion_protocol_runtime_status"]
        == "blocked_no_runtime_trigger_or_scenario_selection"
        for row in protocol_rows
    )
    assert all(
        row["promotion_protocol_review_status"]
        == "blocked_no_promotion_review_complete"
        for row in protocol_rows
    )
    assert {row["promotion_protocol_pass"] for row in protocol_rows} == {"false"}
    assert all(
        row["allowed_use"] == "tdc_trigger_promotion_protocol_review_only"
        for row in protocol_rows
    )
    assert all(
        "threshold_promotion" in row["blocked_use"]
        and "default_selection" in row["blocked_use"]
        and "Evidence_Mode" in row["blocked_use"]
        for row in protocol_rows
    )
    assert all(
        row[field] == "false"
        for row in protocol_rows
        for field in FORBIDDEN_SWITCH_FIELDS
    )
    source_rows = [
        row
        for row in protocol_rows
        if row["required_promotion_field"] == "source_provenance"
    ]
    assert len(source_rows) == len(trigger_rows)
    assert all(row["current_protocol_value"] for row in source_rows)
    assert all(row["current_protocol_value_source_artifact_path"] for row in source_rows)
    assert all(row["current_protocol_value_source_artifact_sha256"] for row in source_rows)
    assert all(row["current_protocol_value_source_row_key"] for row in source_rows)
    assert {
        row["current_protocol_value_source_status"] for row in source_rows
    } == {"pass_source_provenance_recorded_from_trigger_evidence"}
    blocked_rows = [
        row
        for row in protocol_rows
        if row["required_promotion_field"] != "source_provenance"
    ]
    assert all(row["current_protocol_value"] == "" for row in blocked_rows)
    assert all(
        row["current_protocol_value_source_status"]
        == "blocked_no_source_backed_promotion_field_value"
        for row in blocked_rows
    )

    ledger_rows = _rows(OUTPUT_TABLES / "ratewall_assumption_source_backing_ledger.csv")
    protocol_ledger = [
        row
        for row in ledger_rows
        if row["assumption_family"]
        == "tdc_liquidity_regime_trigger_promotion_protocol"
    ]
    assert len(protocol_ledger) == len(protocol_rows)
    assert {row["source_backing_class"] for row in protocol_ledger} == {
        "blocked_or_diagnostic_only"
    }
    assert all(row["enters_dynamic_path"] == "false" for row in protocol_ledger)
    assert all(row["enters_canonical_ratio"] == "false" for row in protocol_ledger)
    assert all(row["prior_narrowing_allowed"] == "false" for row in protocol_ledger)
    assert all(row["pricing_output_enabled"] == "false" for row in protocol_ledger)
    assert all(row["holder_allocation_enabled"] == "false" for row in protocol_ledger)
    assert all(row["raw_rate_shock_enabled"] == "false" for row in protocol_ledger)


def test_tdc_trigger_promotion_protocol_fail_closed_invariant() -> None:
    invariant_rows = _rows(
        OUTPUT_TABLES / "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    by_check = {row["audit_item"]: row for row in invariant_rows}
    assert by_check[
        "tdc_liquidity_regime_trigger_promotion_protocol_fail_closed"
    ]["audit_status"] == "pass"

def test_tdc_trigger_validation_evidence_materializes_fail_closed() -> None:
    protocol_rows = _rows(PROMOTION_PROTOCOL)
    validation_rows = _rows(VALIDATION_EVIDENCE)
    target_fields = {
        "validation_sample",
        "out_of_sample_check",
        "false_positive_control",
        "state_classification_rule",
        "scenario_selection_rule",
    }
    assert len(validation_rows) == 24 * len(target_fields)
    assert {row["required_promotion_field"] for row in validation_rows} == target_fields
    target_protocol_ids = {
        row["promotion_protocol_row_id"]
        for row in protocol_rows
        if row["required_promotion_field"] in target_fields
    }
    assert {row["promotion_protocol_row_id"] for row in validation_rows} == (
        target_protocol_ids
    )
    assert all(row["source_row_count"] for row in validation_rows)
    assert all(int(row["source_row_count"]) > 0 for row in validation_rows)
    assert all(row["source_artifact_paths"] for row in validation_rows)
    assert all(row["source_artifact_sha256s"] for row in validation_rows)
    assert all(
        row["validation_evidence_status"]
        == "blocked_source_rows_available_but_no_promotion_grade_protocol"
        for row in validation_rows
    )
    assert all(row["current_protocol_value"] == "" for row in validation_rows)
    assert {row["promotion_protocol_pass"] for row in validation_rows} == {"false"}
    assert all(
        row["trigger_validation_admission_status"]
        == "blocked_trigger_validation_not_promotion_grade"
        for row in validation_rows
    )
    assert all(
        row["trigger_validation_runtime_status"]
        == "blocked_no_runtime_trigger_or_scenario_selection"
        for row in validation_rows
    )
    assert all(row["scenario_default_allowed"] == "false" for row in validation_rows)
    assert all(
        row["dynamic_path_reference_allowed"] == "false" for row in validation_rows
    )
    assert all(
        row["trigger_threshold_promotion_allowed"] == "false"
        for row in validation_rows
    )
    assert all(
        row["runtime_scenario_selection_allowed"] == "false"
        for row in validation_rows
    )
    assert all(
        row["allowed_use"] == "tdc_trigger_validation_evidence_review_only"
        for row in validation_rows
    )
    assert all(
        "runtime_scenario_selection" in row["blocked_use"]
        and "default_selection" in row["blocked_use"]
        and "Evidence_Mode" in row["blocked_use"]
        for row in validation_rows
    )
    assert all(
        row[field] == "false"
        for row in validation_rows
        for field in FORBIDDEN_SWITCH_FIELDS
    )
    by_field = {
        row["required_promotion_field"]: row["source_artifact_roles_reviewed"]
        for row in validation_rows
    }
    assert "rolling_beta_estimates" in by_field["validation_sample"]
    assert "influence_quarter_diagnostics" in by_field["false_positive_control"]
    assert "state_dep_low_reserves" in by_field["state_classification_rule"]
    assert "selected_credit_rate_lags_paper_estimates" in by_field[
        "scenario_selection_rule"
    ]


def test_tdc_trigger_validation_evidence_is_ledgered_fail_closed_invariant() -> None:
    validation_rows = _rows(VALIDATION_EVIDENCE)
    ledger_rows = _rows(OUTPUT_TABLES / "ratewall_assumption_source_backing_ledger.csv")
    validation_ledger = [
        row
        for row in ledger_rows
        if row["assumption_family"]
        == "tdc_liquidity_regime_trigger_validation_evidence"
    ]
    assert len(validation_ledger) == len(validation_rows)
    assert {row["source_backing_class"] for row in validation_ledger} == {
        "blocked_or_diagnostic_only"
    }
    assert all(row["enters_dynamic_path"] == "false" for row in validation_ledger)
    assert all(row["enters_canonical_ratio"] == "false" for row in validation_ledger)
    assert all(row["prior_narrowing_allowed"] == "false" for row in validation_ledger)
    assert all(row["pricing_output_enabled"] == "false" for row in validation_ledger)
    assert all(row["holder_allocation_enabled"] == "false" for row in validation_ledger)
    assert all(row["raw_rate_shock_enabled"] == "false" for row in validation_ledger)

    invariant_rows = _rows(
        OUTPUT_TABLES / "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    by_check = {row["audit_item"]: row for row in invariant_rows}
    assert by_check[
        "tdc_liquidity_regime_trigger_validation_evidence_fail_closed"
    ]["audit_status"] == "pass"

def test_tdc_pass_through_source_envelope_is_review_only() -> None:
    source_rows = _rows(SOURCE_IMPORT)
    contract_rows = _rows(SCENARIO_CONTRACT)
    preflight_rows = _rows(TRIGGER_VALIDATION_PREFLIGHT)
    envelope_rows = _rows(DYNAMIC_UNCERTAINTY_ENVELOPE)

    source_by_id = {row["source_import_row_id"]: row for row in source_rows}
    tdc_envelope_rows = [
        row
        for row in envelope_rows
        if row["uncertainty_handle"]
        == "tdc_deposit_pass_through_share_source_envelope"
    ]
    assert len(tdc_envelope_rows) == 6
    assert {
        row["tdc_deposit_pass_through_variant_source_import_row_id"]
        for row in tdc_envelope_rows
    } == {
        "ea_tdc_paper_matched_total_deposits_h0",
        "ea_tdc_latest_rolling_matched_total_deposits_h0",
    }
    for row in tdc_envelope_rows:
        source = source_by_id[
            row["tdc_deposit_pass_through_variant_source_import_row_id"]
        ]
        assert source["source_artifact_backed"] == "true"
        assert source["dynamic_path_reference_allowed"] == "true"
        assert (
            source["protocol_admission_status"]
            == "pass_source_artifact_backed_scenario_only"
        )
        assert not source["source_import_row_id"].startswith(
            "ea_tdc_pandemic_exclusion_"
        )
        assert row["scenario_default_allowed"] == "false"
        assert row["runtime_scenario_selection_allowed"] == "false"
        assert row["trigger_threshold_promotion_allowed"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        assert row["denominator_prior_update_allowed"] == "false"

    assert {row["scenario_default_allowed"] for row in contract_rows} == {"false"}
    assert {row["runtime_scenario_selection_allowed"] for row in contract_rows} == {
        "false"
    }
    assert {row["runtime_scenario_selection_allowed"] for row in preflight_rows} == {
        "false"
    }


def test_tdc_materialization_summary_clarifies_not_deposit_pricing() -> None:
    summary_rows = _rows(TDC_MATERIALIZATION_SEMANTIC_SUMMARY)

    assert len(summary_rows) == 6
    assert {row["accounting_identity"] for row in summary_rows} == {
        "delta_total_deposits = delta_tdc + delta_non_tdc_deposits"
    }
    assert {row["coefficient_semantic_label"] for row in summary_rows} == {
        "tdc_to_total_deposits_net_materialization_coefficient"
    }
    assert {row["semantic_status"] for row in summary_rows} == {
        "review_only_tdc_materialization_not_fed_rate_deposit_pricing"
    }
    for row in summary_rows:
        variant_coefficient = Decimal(row["variant_tdc_materialization_coefficient"])
        tdc_input = Decimal(row["tdc_liquidity_state_input_share"])
        assert Decimal(
            row["variant_implied_non_tdc_deposit_offset_share_per_1_tdc"]
        ) == (Decimal("1") - variant_coefficient)
        assert Decimal(
            row["variant_net_materialized_deposit_liquidity_effect_share"]
        ) == (tdc_input * variant_coefficient)
        assert row["scenario_default_allowed"] == "false"
        assert row["runtime_scenario_selection_allowed"] == "false"
        assert row["trigger_threshold_promotion_allowed"] == "false"
        assert row["pricing_output_enabled"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        assert row["enters_main_ratio"] == "false"


def test_tdc_trigger_validation_preflight_materializes_fail_closed() -> None:
    scenario_rows = _rows(SCENARIO_CONTRACT)
    validation_rows = _rows(VALIDATION_EVIDENCE)
    preflight_rows = _rows(TRIGGER_VALIDATION_PREFLIGHT)

    assert len(preflight_rows) == len(validation_rows)
    assert len(preflight_rows) == 120
    assert {row["regime_scenario_id"] for row in preflight_rows} == {
        "normal_forward",
        "latest_rolling_persistence",
        "full_sample_high_liquidity",
        "liquidity_event_step_up",
    }
    assert {
        row["validation_requirement"] for row in preflight_rows
    } == {
        "validation_sample",
        "out_of_sample_check",
        "false_positive_control",
        "state_classification_rule",
        "scenario_selection_rule",
    }
    assert all(row["source_artifact_handle"] for row in preflight_rows)
    assert all(row["source_artifact_paths"] for row in preflight_rows)
    assert all(row["source_artifact_sha256s"] for row in preflight_rows)
    assert all(row["linked_pass_through_source_artifact_sha256"] for row in preflight_rows)
    assert all(
        row["ea_tdc_artifact_hash_status"]
        == "pass_ea_tdc_source_and_validation_hashes_present"
        for row in preflight_rows
    )
    assert all(int(row["scenario_contract_row_count"]) > 0 for row in preflight_rows)
    assert all(row["scenario_contract_row_ids_sample"] for row in preflight_rows)
    assert all(row["tdcsim_contract_version"] == "0.3.0" for row in preflight_rows)
    assert all(row["tdcsim_manifest_hash"] for row in preflight_rows)
    assert {
        row["tdcsim_contract_version_status"] for row in preflight_rows
    } == {"pass_current_mix_baseline_tdcsim_contract_version_hashed_review_only"}
    assert all(row["trigger_promotable"] == "false" for row in preflight_rows)
    assert all(
        row["admission_status"] == "blocked_trigger_validation_preflight_only"
        for row in preflight_rows
    )
    assert all(row["scenario_default_allowed"] == "false" for row in preflight_rows)
    assert all(row["dynamic_path_reference_allowed"] == "false" for row in preflight_rows)
    assert all(
        row["runtime_scenario_selection_allowed"] == "false"
        for row in preflight_rows
    )
    assert all(
        row[field] == "false"
        for row in preflight_rows
        for field in FORBIDDEN_SWITCH_FIELDS
    )
    assert all(
        "runtime_scenario_selection" in row["blocked_use"]
        and "Evidence_Mode" in row["blocked_use"]
        for row in preflight_rows
    )
    normal_dynamic_contracts = [
        row for row in scenario_rows if row["dynamic_path_reference_allowed"] == "true"
    ]
    assert len(normal_dynamic_contracts) == 24
    assert all(
        row["regime_scenario_id"] == "normal_forward"
        and row["contract_field"] == "pass_through_value"
        for row in normal_dynamic_contracts
    )


def test_tdc_scenario_contract_invariant_audit_blocks_source_import_defaults() -> None:
    invariant_rows = _rows(SCENARIO_CONTRACT_INVARIANT)
    assert len(invariant_rows) == 5
    assert {row["audit_status"] for row in invariant_rows} == {"pass"}
    by_item = {row["audit_item"]: row for row in invariant_rows}
    assert by_item[
        "source_import_default_flags_cannot_override_contract_blocks"
    ]["source_import_default_true_count"] == "1"
    assert all(row["scenario_contract_row_count"] == "672" for row in invariant_rows)
    assert all(row["preflight_row_count"] == "120" for row in invariant_rows)
    assert all(row["scenario_contract_default_true_count"] == "0" for row in invariant_rows)
    assert all(
        row["scenario_contract_runtime_selector_true_count"] == "0"
        for row in invariant_rows
    )
    assert all(
        row["preflight_runtime_selector_true_count"] == "0"
        for row in invariant_rows
    )
    assert all(row["preflight_default_true_count"] == "0" for row in invariant_rows)
    assert by_item["normal_forward_only_dynamic_reference"][
        "scenario_contract_dynamic_reference_true_count"
    ] == "24"
    assert by_item["normal_forward_only_dynamic_reference"][
        "non_normal_dynamic_reference_true_count"
    ] == "0"
    assert {
        row["scenario_contract_block_dominates_source_import_status"]
        for row in invariant_rows
    } == {"pass_scenario_contract_blocks_dominate_source_import_flags"}
    assert {
        row["tdcsim_runtime_selector_status"] for row in invariant_rows
    } == {"blocked_tdcsim_contract_not_runtime_selector"}
    assert all(
        row[field] == "false"
        for row in invariant_rows
        for field in FORBIDDEN_SWITCH_FIELDS
    )


def test_tdc_trigger_preflight_and_invariant_are_ledgered_fail_closed() -> None:
    preflight_rows = _rows(TRIGGER_VALIDATION_PREFLIGHT)
    invariant_rows = _rows(SCENARIO_CONTRACT_INVARIANT)
    ledger_rows = _rows(OUTPUT_TABLES / "ratewall_assumption_source_backing_ledger.csv")
    preflight_ledger = [
        row
        for row in ledger_rows
        if row["assumption_family"]
        == "tdc_deposit_pass_through_trigger_validation_preflight"
    ]
    invariant_ledger = [
        row
        for row in ledger_rows
        if row["assumption_family"]
        == "tdc_deposit_pass_through_scenario_contract_invariant_audit"
    ]
    assert len(preflight_ledger) == len(preflight_rows)
    assert len(invariant_ledger) == len(invariant_rows)
    assert {row["source_backing_class"] for row in preflight_ledger} == {
        "blocked_or_diagnostic_only"
    }
    assert {row["source_backing_class"] for row in invariant_ledger} == {
        "blocked_or_diagnostic_only"
    }
    assert all(row["enters_dynamic_path"] == "false" for row in preflight_ledger)
    assert all(row["enters_canonical_ratio"] == "false" for row in preflight_ledger)
    assert all(row["prior_narrowing_allowed"] == "false" for row in preflight_ledger)
    assert all(row["pricing_output_enabled"] == "false" for row in preflight_ledger)
    assert all(row["holder_allocation_enabled"] == "false" for row in preflight_ledger)
    assert all(row["raw_rate_shock_enabled"] == "false" for row in preflight_ledger)

    source_backing_invariants = _rows(
        OUTPUT_TABLES / "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    by_check = {row["audit_item"]: row for row in source_backing_invariants}
    assert by_check[
        "tdc_deposit_pass_through_trigger_validation_preflight_fail_closed"
    ]["audit_status"] == "pass"
    assert by_check[
        "tdc_deposit_pass_through_scenario_contract_invariant_audit_fail_closed"
    ]["audit_status"] == "pass"

    backend_invariants = _rows(
        OUTPUT_TABLES / "ratewall_backend_invariant_guardrail_audit.csv"
    )
    backend_by_item = {row["audit_item"]: row for row in backend_invariants}
    assert backend_by_item[
        "tdc_deposit_pass_through_scenario_contract_not_runtime_selector"
    ]["audit_status"] == "pass"
