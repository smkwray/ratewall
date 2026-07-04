"""Fail-closed QRA Watch / ATI to TDCSim scenario-contract surfaces."""

from __future__ import annotations

from collections.abc import Iterable

from ratewall.databook.tdcsim_contracts import DISABLED_SWITCHES


CLAIM_BOUNDARY = "qrawatch_tdcsim_bridge_assumption_mode_not_runtime_mechanics"

QRAWATCH_TDCSIM_SCENARIO_REGISTRY_FIELDS = [
    "scenario_contract_id",
    "scenario_family",
    "scenario_label",
    "qrawatch_derived",
    "qrawatch_input_role",
    "qrawatch_source_artifact",
    "source_backing_ledger_handle",
    "source_backing_class",
    "source_backing_admission_status",
    "source_record_count",
    "source_hash_or_manifest_hash",
    "tdcsim_required_input_contract",
    "tdcsim_contract_output_scenario_id",
    "tdcsim_contract_consumption_status",
    "current_mix_baseline_runtime_path",
    "central_default_runtime_path",
    "runtime_mechanics_enabled",
    "ratewall_runtime_source",
    "qrawatch_direct_runtime_read",
    "blocked_runtime_reason",
    "assumption_mode",
    "sensitivity_only",
    "diagnostic_only",
    "blocked_or_diagnostic",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

QRAWATCH_TDCSIM_PROVENANCE_AUDIT_FIELDS = [
    "audit_item",
    "audit_status",
    "scenario_contract_id",
    "qrawatch_source_artifact",
    "source_backing_ledger_handle",
    "source_backing_class",
    "source_backing_admission_status",
    "source_record_count",
    "source_hash_or_manifest_hash",
    "tdcsim_contract_consumption_status",
    "qrawatch_direct_runtime_read",
    "evidence_summary",
    "failure_mode_if_false",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

QRAWATCH_TDCSIM_BRIDGE_INVARIANT_AUDIT_FIELDS = [
    "audit_item",
    "audit_status",
    "evidence_table",
    "evidence_summary",
    "failure_mode_if_false",
    "current_mix_baseline_only_default",
    "ratewall_consumes_tdcsim_contracts_not_qra_directly",
    "qrawatch_pricing_output_enabled",
    "qrawatch_holder_allocation_enabled",
    "qrawatch_evidence_mode_enabled",
    "qrawatch_enters_main_ratio",
    "qrawatch_canonical_ratio_entry",
    "claim_boundary",
]


QRAWATCH_SCENARIO_SPECS = [
    {
        "scenario_contract_id": "qrawatch_ati_issuance_mix_measurement",
        "scenario_family": "qrawatch_ati_issuance_mix",
        "scenario_label": "QRA ATI issuance-mix measurement input",
        "qrawatch_input_role": "issuance_mix_ati",
        "qrawatch_source_artifact": "../qrawatch/output/publish/ati_quarter_table.csv",
        "source_backing_ledger_handle": "qrawatch_ati_quarter_table",
        "tdcsim_required_input_contract": "qrawatch_tdcsim_issuance_mix_path.csv",
        "blocked_runtime_reason": "requires_tdcsim_contract_output_before_ratewall_runtime_consumption",
        "diagnostic_only": "false",
    },
    {
        "scenario_contract_id": "qrawatch_ati_readiness_gate",
        "scenario_family": "qrawatch_ati_issuance_mix",
        "scenario_label": "QRA ATI seed versus official readiness gate",
        "qrawatch_input_role": "issuance_mix_readiness_gate",
        "qrawatch_source_artifact": "../qrawatch/output/publish/ati_seed_vs_official.csv",
        "source_backing_ledger_handle": "qrawatch_ati_seed_vs_official",
        "tdcsim_required_input_contract": "qrawatch_tdcsim_issuance_mix_path.csv",
        "blocked_runtime_reason": "readiness_gate_only_not_runtime_path",
        "diagnostic_only": "false",
    },
    {
        "scenario_contract_id": "qrawatch_forward_ati_path_blocked",
        "scenario_family": "qrawatch_ati_issuance_mix",
        "scenario_label": "QRA forward ATI path placeholder",
        "qrawatch_input_role": "issuance_mix_forward_path",
        "qrawatch_source_artifact": "../qrawatch/output/publish/ati_seed_forecast_table.csv",
        "source_backing_ledger_handle": "qrawatch_ati_seed_forecast_table",
        "tdcsim_required_input_contract": "qrawatch_tdcsim_issuance_mix_path.csv",
        "blocked_runtime_reason": "forward_ati_table_empty",
        "diagnostic_only": "true",
    },
    {
        "scenario_contract_id": "qrawatch_duration_supply_yield_shift",
        "scenario_family": "qrawatch_duration_supply",
        "scenario_label": "QRA duration-supply yield-shift sensitivity input",
        "qrawatch_input_role": "duration_supply_or_yield_shift",
        "qrawatch_source_artifact": "../qrawatch/output/publish/duration_supply_summary.csv",
        "source_backing_ledger_handle": "qrawatch_duration_supply_summary",
        "tdcsim_required_input_contract": "qrawatch_tdcsim_yield_shift_path.csv",
        "blocked_runtime_reason": "requires_tdcsim_yield_shift_contract_output_before_ratewall_runtime_consumption",
        "diagnostic_only": "false",
    },
    {
        "scenario_contract_id": "qrawatch_pricing_translation_context",
        "scenario_family": "qrawatch_duration_supply",
        "scenario_label": "QRA pricing translation context for yield-shift sensitivity",
        "qrawatch_input_role": "yield_shift_context_not_pricing_output",
        "qrawatch_source_artifact": "../qrawatch/output/publish/pricing_scenario_translation.csv",
        "source_backing_ledger_handle": "qrawatch_pricing_scenario_translation",
        "tdcsim_required_input_contract": "qrawatch_tdcsim_yield_shift_path.csv",
        "blocked_runtime_reason": "reduced_form_context_not_ratewall_pricing_output",
        "diagnostic_only": "true",
    },
    {
        "scenario_contract_id": "qrawatch_holder_preference_blocked",
        "scenario_family": "qrawatch_holder_preference",
        "scenario_label": "QRA holder-preference placeholder blocked by empty allotments",
        "qrawatch_input_role": "holder_preference_placeholder",
        "qrawatch_source_artifact": "../qrawatch/output/publish/investor_allotments_summary.csv",
        "source_backing_ledger_handle": "qrawatch_investor_allotments_summary",
        "tdcsim_required_input_contract": "qrawatch_tdcsim_holder_preference_path.csv",
        "blocked_runtime_reason": "investor_allotment_evidence_empty",
        "diagnostic_only": "true",
    },
    {
        "scenario_contract_id": "qrawatch_auction_absorption_diagnostic",
        "scenario_family": "qrawatch_diagnostic_context",
        "scenario_label": "QRA auction absorption diagnostic context",
        "qrawatch_input_role": "auction_absorption_diagnostic",
        "qrawatch_source_artifact": "../qrawatch/output/publish/auction_absorption_table.csv",
        "source_backing_ledger_handle": "qrawatch_auction_absorption_table",
        "tdcsim_required_input_contract": "qrawatch_tdcsim_diagnostic_context.csv",
        "blocked_runtime_reason": "diagnostic_context_not_holder_allocation",
        "diagnostic_only": "true",
    },
    {
        "scenario_contract_id": "qrawatch_plumbing_diagnostic",
        "scenario_family": "qrawatch_diagnostic_context",
        "scenario_label": "QRA plumbing diagnostic context",
        "qrawatch_input_role": "plumbing_diagnostic",
        "qrawatch_source_artifact": "../qrawatch/output/publish/plumbing_regression_summary.csv",
        "source_backing_ledger_handle": "qrawatch_plumbing_regression_summary",
        "tdcsim_required_input_contract": "qrawatch_tdcsim_diagnostic_context.csv",
        "blocked_runtime_reason": "diagnostic_regression_context_only",
        "diagnostic_only": "true",
    },
]


def qrawatch_tdcsim_scenario_registry_rows(
    *,
    source_backing_ledger_rows: list[dict[str, str]],
    tdcsim_projection_contract_bridge_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    scenario_ids = sorted(
        {
            row.get("scenario_id", "")
            for row in tdcsim_projection_contract_bridge_rows
            if row.get("scenario_id")
        }
    )
    for scenario_id in scenario_ids:
        rows.append(_tdcsim_runtime_row(scenario_id))

    ledger_by_handle = _ledger_by_handle(source_backing_ledger_rows)
    for spec in QRAWATCH_SCENARIO_SPECS:
        ledger_row = ledger_by_handle.get(spec["source_backing_ledger_handle"], {})
        rows.append(_qrawatch_registry_row(spec, ledger_row))
    return rows


def qrawatch_tdcsim_provenance_audit_rows(
    registry_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows = []
    for row in registry_rows:
        if row.get("qrawatch_derived") != "true":
            continue
        admitted = row["source_backing_admission_status"] not in {
            "fail_closed_missing_source_backing_ledger_row",
            "fail_closed_missing_source_artifact",
        }
        rows.append(
            {
                "audit_item": "qrawatch_source_backing_admission",
                "audit_status": "pass" if admitted else "fail",
                "scenario_contract_id": row["scenario_contract_id"],
                "qrawatch_source_artifact": row["qrawatch_source_artifact"],
                "source_backing_ledger_handle": row["source_backing_ledger_handle"],
                "source_backing_class": row["source_backing_class"],
                "source_backing_admission_status": row[
                    "source_backing_admission_status"
                ],
                "source_record_count": row["source_record_count"],
                "source_hash_or_manifest_hash": row["source_hash_or_manifest_hash"],
                "tdcsim_contract_consumption_status": row[
                    "tdcsim_contract_consumption_status"
                ],
                "qrawatch_direct_runtime_read": row["qrawatch_direct_runtime_read"],
                "evidence_summary": (
                    "source-backing ledger row gates this QRA input before any "
                    "TDCSim scenario-contract consumption"
                ),
                "failure_mode_if_false": (
                    "QRA scenario input lacked a source-backing ledger row or "
                    "was treated as direct RateWall runtime input"
                ),
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "pricing_output_enabled": "false",
                "holder_allocation_enabled": "false",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        )
    return rows


def qrawatch_tdcsim_bridge_invariant_audit_rows(
    *,
    registry_rows: list[dict[str, str]],
    provenance_rows: list[dict[str, str]],
    tdcsim_projection_contract_bridge_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    qra_rows = [row for row in registry_rows if row.get("qrawatch_derived") == "true"]
    default_rows = [
        row for row in registry_rows if row.get("central_default_runtime_path") == "true"
    ]
    checks = [
        (
            "current_mix_baseline_only_default",
            len(default_rows) == 1
            and default_rows[0].get("scenario_contract_id") == "current_mix_baseline",
            "ratewall_qrawatch_tdcsim_scenario_registry.csv",
            "only current_mix_baseline is marked as central/default runtime path",
            "a QRA or nonbaseline TDCSim sensitivity was marked central/default",
        ),
        (
            "ratewall_consumes_tdcsim_contracts_not_qra_directly",
            all(row.get("qrawatch_direct_runtime_read") == "false" for row in registry_rows)
            and bool(tdcsim_projection_contract_bridge_rows),
            "ratewall_tdcsim_projection_contract_bridge.csv",
            "registry records TDCSim contract outputs as RateWall runtime source",
            "RateWall consumed QRA source files directly as runtime projection output",
        ),
        (
            "qrawatch_rows_do_not_affect_runtime_mechanics",
            all(row.get("runtime_mechanics_enabled") == "false" for row in qra_rows),
            "ratewall_qrawatch_tdcsim_scenario_registry.csv",
            f"{len(qra_rows)} QRA-derived rows checked for runtime mechanics disablement",
            "a QRA-derived row was allowed to affect RateWall runtime mechanics",
        ),
        (
            "qrawatch_forbidden_switches_disabled",
            all(
                row.get(field) == "false"
                for row in [*qra_rows, *provenance_rows]
                for field in (
                    "enters_main_ratio",
                    "evidence_mode_enabled",
                    "pricing_output_enabled",
                    "holder_allocation_enabled",
                    "canonical_ratio_entry",
                )
            ),
            "ratewall_qrawatch_tdcsim_scenario_registry.csv;ratewall_qrawatch_tdcsim_provenance_audit.csv",
            "QRA registry and provenance rows keep requested forbidden switches disabled",
            "a QRA row enabled main-ratio, Evidence Mode, pricing, holder allocation, or canonical-ratio entry",
        ),
        (
            "qrawatch_holder_allocation_blocked_until_allotments",
            all(
                row.get("holder_allocation_enabled") == "false"
                and row.get("blocked_or_diagnostic") == "true"
                for row in qra_rows
                if row.get("qrawatch_input_role") == "holder_preference_placeholder"
            ),
            "ratewall_qrawatch_tdcsim_scenario_registry.csv",
            "holder-preference placeholder is blocked until investor-allotment evidence is populated and validated",
            "QRA holder-preference placeholder was treated as holder-allocation evidence",
        ),
        (
            "qrawatch_pricing_translation_not_ratewall_pricing",
            all(
                row.get("pricing_output_enabled") == "false"
                and "not_ratewall_pricing_output" in row.get("source_backing_admission_status", "")
                for row in qra_rows
                if row.get("qrawatch_input_role") == "yield_shift_context_not_pricing_output"
            ),
            "ratewall_qrawatch_tdcsim_scenario_registry.csv",
            "QRA pricing translation is recorded only as yield-shift context",
            "QRA pricing translation was read as RateWall pricing output",
        ),
        (
            "qrawatch_source_backing_provenance_passes",
            bool(provenance_rows)
            and {row.get("audit_status") for row in provenance_rows} == {"pass"},
            "ratewall_qrawatch_tdcsim_provenance_audit.csv",
            f"{len(provenance_rows)} QRA provenance rows passed source-backing checks",
            "QRA provenance lacked source-backing ledger admission evidence",
        ),
    ]
    return [
        _invariant_row(
            audit_item=item,
            passed=passed,
            evidence_table=evidence_table,
            evidence_summary=summary,
            failure_mode_if_false=failure,
        )
        for item, passed, evidence_table, summary, failure in checks
    ]


def _tdcsim_runtime_row(scenario_id: str) -> dict[str, str]:
    is_default = scenario_id == "current_mix_baseline"
    return {
        "scenario_contract_id": scenario_id,
        "scenario_family": "tdcsim_contract_output",
        "scenario_label": f"TDCSim contract output: {scenario_id}",
        "qrawatch_derived": "false",
        "qrawatch_input_role": "none",
        "qrawatch_source_artifact": "",
        "source_backing_ledger_handle": "tdcsim_forward_tdc_contract",
        "source_backing_class": "sibling_contract_value",
        "source_backing_admission_status": "tdcsim_contract_output_consumed_by_ratewall",
        "source_record_count": "",
        "source_hash_or_manifest_hash": "",
        "tdcsim_required_input_contract": "tdcsim_ratewall_quarterly_summary.csv",
        "tdcsim_contract_output_scenario_id": scenario_id,
        "tdcsim_contract_consumption_status": "consumed_as_ratewall_runtime_contract_output",
        "current_mix_baseline_runtime_path": str(is_default).lower(),
        "central_default_runtime_path": str(is_default).lower(),
        "runtime_mechanics_enabled": str(is_default).lower(),
        "ratewall_runtime_source": "ratewall_tdcsim_projection_contract_bridge.csv",
        "qrawatch_direct_runtime_read": "false",
        "blocked_runtime_reason": "" if is_default else "sensitivity_only_tdcsim_output",
        "assumption_mode": "true",
        "sensitivity_only": str(not is_default).lower(),
        "diagnostic_only": "false",
        "blocked_or_diagnostic": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "pricing_output_enabled": "false",
        "holder_allocation_enabled": "false",
        "canonical_ratio_entry": "false",
        "claim_boundary": CLAIM_BOUNDARY,
        **DISABLED_SWITCHES,
    }


def _qrawatch_registry_row(spec: dict[str, str], ledger_row: dict[str, str]) -> dict[str, str]:
    source_class = ledger_row.get("source_backing_class", "")
    source_record_count = ledger_row.get("source_record_count", "")
    admission_status = _qrawatch_admission_status(spec, ledger_row)
    blocked_or_diagnostic = str(
        spec.get("diagnostic_only") == "true"
        or admission_status.startswith("blocked")
        or admission_status.startswith("fail_closed")
    ).lower()
    return {
        "scenario_contract_id": spec["scenario_contract_id"],
        "scenario_family": spec["scenario_family"],
        "scenario_label": spec["scenario_label"],
        "qrawatch_derived": "true",
        "qrawatch_input_role": spec["qrawatch_input_role"],
        "qrawatch_source_artifact": spec["qrawatch_source_artifact"],
        "source_backing_ledger_handle": spec["source_backing_ledger_handle"],
        "source_backing_class": source_class,
        "source_backing_admission_status": admission_status,
        "source_record_count": source_record_count,
        "source_hash_or_manifest_hash": ledger_row.get("source_hash_or_manifest_hash", ""),
        "tdcsim_required_input_contract": spec["tdcsim_required_input_contract"],
        "tdcsim_contract_output_scenario_id": "",
        "tdcsim_contract_consumption_status": (
            "blocked_until_tdcsim_contract_exports_bundled_scenario"
        ),
        "current_mix_baseline_runtime_path": "false",
        "central_default_runtime_path": "false",
        "runtime_mechanics_enabled": "false",
        "ratewall_runtime_source": "tdcsim_contract_output_required",
        "qrawatch_direct_runtime_read": "false",
        "blocked_runtime_reason": spec["blocked_runtime_reason"],
        "assumption_mode": "true",
        "sensitivity_only": "true",
        "diagnostic_only": spec["diagnostic_only"],
        "blocked_or_diagnostic": blocked_or_diagnostic,
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "pricing_output_enabled": "false",
        "holder_allocation_enabled": "false",
        "canonical_ratio_entry": "false",
        "claim_boundary": CLAIM_BOUNDARY,
        **DISABLED_SWITCHES,
    }


def _qrawatch_admission_status(
    spec: dict[str, str], ledger_row: dict[str, str]
) -> str:
    if not ledger_row:
        return "fail_closed_missing_source_backing_ledger_row"
    if ledger_row.get("missing_expected_artifact") == "true":
        return "fail_closed_missing_source_artifact"
    if spec["scenario_contract_id"] == "qrawatch_pricing_translation_context":
        return "admitted_yield_shift_context_not_ratewall_pricing_output"
    if spec["scenario_contract_id"] == "qrawatch_holder_preference_blocked":
        return "blocked_until_investor_allotment_evidence_populated_and_validated"
    if ledger_row.get("source_record_count") == "0":
        return "blocked_until_source_rows_populated"
    source_class = ledger_row.get("source_backing_class", "")
    if source_class == "official_source_value":
        return "admitted_source_backed_sensitivity_only"
    if source_class == "scenario_assumption":
        return "admitted_sensitivity_only"
    if source_class == "blocked_or_diagnostic_only":
        return "blocked_or_diagnostic_only"
    return f"admitted_with_source_backing_class:{source_class}"


def _ledger_by_handle(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        handle = row.get("assumption_handle", "")
        if handle.startswith("qrawatch_") and handle not in out:
            out[handle] = row
    return out


def _invariant_row(
    *,
    audit_item: str,
    passed: bool,
    evidence_table: str,
    evidence_summary: str,
    failure_mode_if_false: str,
) -> dict[str, str]:
    return {
        "audit_item": audit_item,
        "audit_status": "pass" if passed else "fail",
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary,
        "failure_mode_if_false": failure_mode_if_false,
        "current_mix_baseline_only_default": "true"
        if audit_item == "current_mix_baseline_only_default" and passed
        else "false",
        "ratewall_consumes_tdcsim_contracts_not_qra_directly": "true"
        if audit_item == "ratewall_consumes_tdcsim_contracts_not_qra_directly" and passed
        else "false",
        "qrawatch_pricing_output_enabled": "false",
        "qrawatch_holder_allocation_enabled": "false",
        "qrawatch_evidence_mode_enabled": "false",
        "qrawatch_enters_main_ratio": "false",
        "qrawatch_canonical_ratio_entry": "false",
        "claim_boundary": CLAIM_BOUNDARY,
    }
