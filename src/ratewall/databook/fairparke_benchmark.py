"""Read-only Fair/Parke benchmark inventory and mapping surfaces."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


RUN_INVENTORY_FIELDS = [
    "benchmark_run_row_id",
    "source_repo_path",
    "source_export_root",
    "manifest_path",
    "dictionary_path",
    "run_payload_path",
    "run_id",
    "family_id",
    "group",
    "scenario_name",
    "horizon_id",
    "horizon_label",
    "forecast_start",
    "forecast_end",
    "summary",
    "run_family_kind",
    "available_series_count",
    "has_short_rate_series",
    "has_output_series",
    "has_unemployment_series",
    "has_pce_component_bundle",
    "has_residential_investment_series",
    "has_nonresidential_investment_series",
    "scenario_compatibility_status",
    "benchmark_priority",
    "benchmark_role",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
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

MAPPING_CONTRACT_FIELDS = [
    "mapping_row_id",
    "ratewall_target_slot_id",
    "ratewall_target_label",
    "fairparke_variable_expression",
    "fairparke_dictionary_labels",
    "mapping_class",
    "mapping_status",
    "existing_export_scenario_status",
    "requires_custom_rate_scenario",
    "benchmark_priority",
    "benchmark_role",
    "exact_blocker",
    "next_backend_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
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

FAIRPARKE_REPO = Path("../fp-wraptr")
FAIRPARKE_EXPORT_ROOT = FAIRPARKE_REPO / "public" / "model-runs"
FAIRPARKE_MANIFEST_PATH = FAIRPARKE_EXPORT_ROOT / "manifest.json"
FAIRPARKE_DICTIONARY_PATH = FAIRPARKE_EXPORT_ROOT / "dictionary.json"

BENCHMARK_PRIORITY = "secondary_to_frbus_unless_fairparke_adds_missing_benchmark_shape"
BENCHMARK_ROLE = "secondary_model_benchmark_only"
SCENARIO_BLOCKER = (
    "Current Fair/Parke public runs are stock-baseline or public-service-employment "
    "scenario families, not monetary-tightening comparison runs."
)
SCENARIO_NEXT_ACTION = (
    "prefer_frbus_benchmark_unless_fairparke_adds_missing_component_or_scenario"
)
CUSTOM_SCENARIO_ACTION = (
    "if_rate_tightening_benchmark_needed_request_fp_wraptr_agent_for_existing_compatible_"
    "run_or_custom_scenario_without_touching_current_public_outputs"
)

_PCE_COMPONENTS = ("CD", "CN", "CS")
_RESIDENTIAL_COMPONENTS = ("IHF", "IHH")
_NONRES_COMPONENTS = ("IKB",)


@dataclass(frozen=True)
class FairParkeBenchmarkArtifacts:
    run_inventory_rows: list[dict[str, str]]
    mapping_contract_rows: list[dict[str, str]]


def build_fairparke_benchmark_artifacts() -> FairParkeBenchmarkArtifacts:
    manifest = _read_json_object(FAIRPARKE_MANIFEST_PATH)
    dictionary = _read_json_object(FAIRPARKE_DICTIONARY_PATH)
    if manifest is None or dictionary is None:
        return FairParkeBenchmarkArtifacts(
            run_inventory_rows=[_missing_inventory_row()],
            mapping_contract_rows=_missing_mapping_rows(),
        )

    runs = manifest.get("runs")
    if not isinstance(runs, list):
        return FairParkeBenchmarkArtifacts(
            run_inventory_rows=[_missing_inventory_row()],
            mapping_contract_rows=_missing_mapping_rows(),
        )

    inventory_rows = [
        _inventory_row(run_meta=run_meta)
        for run_meta in runs
        if isinstance(run_meta, dict)
    ]
    mapping_rows = _mapping_contract_rows(dictionary=dictionary)
    return FairParkeBenchmarkArtifacts(
        run_inventory_rows=inventory_rows,
        mapping_contract_rows=mapping_rows,
    )


def _inventory_row(*, run_meta: dict[str, object]) -> dict[str, str]:
    data_path = str(run_meta.get("data_path", ""))
    payload = _read_json_object(FAIRPARKE_EXPORT_ROOT / data_path)
    series = payload.get("series", {}) if payload is not None else {}
    series_keys = set(series) if isinstance(series, dict) else set()
    row = {field: "" for field in RUN_INVENTORY_FIELDS}
    row.update(
        {
            "benchmark_run_row_id": (
                f"fairparke_benchmark_run_inventory::{run_meta.get('run_id', '')}"
            ),
            "source_repo_path": str(FAIRPARKE_REPO),
            "source_export_root": str(FAIRPARKE_EXPORT_ROOT),
            "manifest_path": str(FAIRPARKE_MANIFEST_PATH),
            "dictionary_path": str(FAIRPARKE_DICTIONARY_PATH),
            "run_payload_path": data_path,
            "run_id": str(run_meta.get("run_id", "")),
            "family_id": str(run_meta.get("family_id", "")),
            "group": str(run_meta.get("group", "")),
            "scenario_name": str(run_meta.get("scenario_name", "")),
            "horizon_id": str(run_meta.get("horizon_id", "")),
            "horizon_label": str(run_meta.get("horizon_label", "")),
            "forecast_start": str(run_meta.get("forecast_start", "")),
            "forecast_end": str(run_meta.get("forecast_end", "")),
            "summary": str(run_meta.get("summary", "")),
            "run_family_kind": _run_family_kind(run_meta),
            "available_series_count": str(len(series_keys)),
            "has_short_rate_series": _bool_text("RS" in series_keys),
            "has_output_series": _bool_text("Y" in series_keys),
            "has_unemployment_series": _bool_text("UR" in series_keys),
            "has_pce_component_bundle": _bool_text(
                all(component in series_keys for component in _PCE_COMPONENTS)
            ),
            "has_residential_investment_series": _bool_text(
                all(component in series_keys for component in _RESIDENTIAL_COMPONENTS)
            ),
            "has_nonresidential_investment_series": _bool_text(
                all(component in series_keys for component in _NONRES_COMPONENTS)
            ),
            "scenario_compatibility_status": _scenario_compatibility_status(run_meta),
            "benchmark_priority": BENCHMARK_PRIORITY,
            "benchmark_role": BENCHMARK_ROLE,
            "exact_blocker": _inventory_exact_blocker(run_meta),
            "next_backend_action": _inventory_next_action(run_meta),
            "allowed_use": "fairparke_benchmark_inventory_review_only",
            "blocked_use": (
                "admitted_denominator;main_ratio;Evidence_Mode;prior_narrowing;"
                "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
                "tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "fairparke_read_only_export_not_denominator_calibration",
            **_disabled_switches(),
        }
    )
    return row


def _mapping_contract_rows(*, dictionary: dict[str, object]) -> list[dict[str, str]]:
    variable_block = dictionary.get("variables", {})
    labels: dict[str, str] = {}
    if isinstance(variable_block, dict):
        for key, value in variable_block.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            short_name = value.get("short_name")
            description = value.get("description")
            if isinstance(short_name, str) and short_name:
                labels[key] = short_name
            elif isinstance(description, str) and description:
                labels[key] = description
    specs = [
        (
            "policy_rate_short_rate_context",
            "Fair/Parke short rate context",
            "RS",
            "direct_series",
        ),
        (
            "real_output_benchmark",
            "Fair/Parke real output benchmark",
            "Y",
            "direct_series",
        ),
        (
            "unemployment_context",
            "Fair/Parke unemployment context",
            "UR",
            "direct_series",
        ),
        (
            "pce_durables_component",
            "Fair/Parke durable-goods component",
            "CD",
            "direct_series",
        ),
        (
            "pce_nondurables_component",
            "Fair/Parke nondurable-goods component",
            "CN",
            "direct_series",
        ),
        (
            "pce_services_component",
            "Fair/Parke services component",
            "CS",
            "direct_series",
        ),
        (
            "residential_investment_component",
            "Fair/Parke residential investment bridge",
            "IHF + IHH",
            "aggregated_expression",
        ),
        (
            "nonresidential_fixed_investment_component",
            "Fair/Parke nonresidential investment bridge",
            "IKB",
            "direct_series",
        ),
        (
            "fspdp_component_sum_proxy",
            "Fair/Parke FSPDP component-sum proxy",
            "CD + CN + CS + IHF + IHH + IKB",
            "aggregated_expression",
        ),
    ]
    rows: list[dict[str, str]] = []
    for target_slot_id, target_label, expression, mapping_class in specs:
        variables = [token.strip() for token in expression.split("+")]
        labels_text = "; ".join(
            f"{variable}={labels.get(variable, 'MISSING')}" for variable in variables
        )
        mapping_status = (
            "pass_variable_mapping_available_read_only"
            if all(variable in labels for variable in variables)
            else "blocked_dictionary_variable_missing"
        )
        blocker = (
            SCENARIO_BLOCKER
            if mapping_status.startswith("pass_")
            else "Fair/Parke dictionary is missing one or more required variables."
        )
        next_action = (
            CUSTOM_SCENARIO_ACTION
            if mapping_status.startswith("pass_")
            else "repair_dictionary_or_keep_fairparke_route_as_incomplete_context_only"
        )
        row = {field: "" for field in MAPPING_CONTRACT_FIELDS}
        row.update(
            {
                "mapping_row_id": f"fairparke_benchmark_mapping_contract::{target_slot_id}",
                "ratewall_target_slot_id": target_slot_id,
                "ratewall_target_label": target_label,
                "fairparke_variable_expression": expression,
                "fairparke_dictionary_labels": labels_text,
                "mapping_class": mapping_class,
                "mapping_status": mapping_status,
                "existing_export_scenario_status": (
                    "blocked_existing_export_lacks_rate_tightening_counterfactual"
                    if mapping_status.startswith("pass_")
                    else "blocked_dictionary_variable_missing"
                ),
                "requires_custom_rate_scenario": _bool_text(mapping_status.startswith("pass_")),
                "benchmark_priority": BENCHMARK_PRIORITY,
                "benchmark_role": BENCHMARK_ROLE,
                "exact_blocker": blocker,
                "next_backend_action": next_action,
                "allowed_use": "fairparke_mapping_contract_review_only",
                "blocked_use": (
                    "admitted_denominator;main_ratio;Evidence_Mode;prior_narrowing;"
                    "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
                    "tax_incidence_welfare_mpc"
                ),
                "claim_boundary": "fairparke_mapping_contract_not_denominator_calibration",
                **_disabled_switches(),
            }
        )
        rows.append(row)
    return rows


def _missing_inventory_row() -> dict[str, str]:
    row = {field: "" for field in RUN_INVENTORY_FIELDS}
    row.update(
        {
            "benchmark_run_row_id": "fairparke_benchmark_run_inventory::missing",
            "source_repo_path": str(FAIRPARKE_REPO),
            "source_export_root": str(FAIRPARKE_EXPORT_ROOT),
            "manifest_path": str(FAIRPARKE_MANIFEST_PATH),
            "dictionary_path": str(FAIRPARKE_DICTIONARY_PATH),
            "scenario_compatibility_status": "blocked_missing_sibling_export_surface",
            "benchmark_priority": BENCHMARK_PRIORITY,
            "benchmark_role": BENCHMARK_ROLE,
            "exact_blocker": (
                "Fair/Parke sibling export surface is missing or unreadable at "
                "../fp-wraptr/public/model-runs."
            ),
            "next_backend_action": (
                "confirm_fp_wraptr_public_model_runs_export_exists_before_any_benchmark_import"
            ),
            "allowed_use": "fairparke_benchmark_inventory_review_only",
            "blocked_use": (
                "admitted_denominator;main_ratio;Evidence_Mode;prior_narrowing;"
                "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
                "tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "fairparke_read_only_export_not_denominator_calibration",
            **_disabled_switches(),
        }
    )
    return row


def _missing_mapping_rows() -> list[dict[str, str]]:
    row = {field: "" for field in MAPPING_CONTRACT_FIELDS}
    row.update(
        {
            "mapping_row_id": "fairparke_benchmark_mapping_contract::missing",
            "ratewall_target_slot_id": "missing_export_surface",
            "ratewall_target_label": "Fair/Parke export surface missing",
            "mapping_status": "blocked_missing_sibling_export_surface",
            "existing_export_scenario_status": "blocked_missing_sibling_export_surface",
            "requires_custom_rate_scenario": "false",
            "benchmark_priority": BENCHMARK_PRIORITY,
            "benchmark_role": BENCHMARK_ROLE,
            "exact_blocker": (
                "Fair/Parke sibling export surface is missing or unreadable at "
                "../fp-wraptr/public/model-runs."
            ),
            "next_backend_action": (
                "confirm_fp_wraptr_public_model_runs_export_exists_before_any_benchmark_import"
            ),
            "allowed_use": "fairparke_mapping_contract_review_only",
            "blocked_use": (
                "admitted_denominator;main_ratio;Evidence_Mode;prior_narrowing;"
                "pricing;holder_allocation;raw_rate_shock;reset_calendar;"
                "tax_incidence_welfare_mpc"
            ),
            "claim_boundary": "fairparke_mapping_contract_not_denominator_calibration",
            **_disabled_switches(),
        }
    )
    return [row]


def _run_family_kind(run_meta: dict[str, object]) -> str:
    run_id = str(run_meta.get("run_id", "")).lower()
    group = str(run_meta.get("group", ""))
    if run_id == "stock_fm_baseline":
        return "stock_reference_baseline"
    if "pse" in run_id or "PSE" in group:
        return "public_service_employment_counterfactual"
    return "other_existing_export_run"


def _scenario_compatibility_status(run_meta: dict[str, object]) -> str:
    run_kind = _run_family_kind(run_meta)
    if run_kind == "stock_reference_baseline":
        return "baseline_reference_only_not_rate_tightening_counterfactual"
    return "blocked_existing_export_lacks_rate_tightening_counterfactual"


def _inventory_exact_blocker(run_meta: dict[str, object]) -> str:
    if _run_family_kind(run_meta) == "stock_reference_baseline":
        return (
            "Stock Fair/Parke baseline is useful for variable coverage and level checks, "
            "but it is not a tightening-vs-counterfactual benchmark."
        )
    return SCENARIO_BLOCKER


def _inventory_next_action(run_meta: dict[str, object]) -> str:
    if _run_family_kind(run_meta) == "stock_reference_baseline":
        return SCENARIO_NEXT_ACTION
    return CUSTOM_SCENARIO_ACTION


def _read_json_object(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _disabled_switches() -> dict[str, str]:
    return {
        "denominator_prior_update_allowed": "false",
        "empirical_threshold_claim_enabled": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "canonical_ratio_entry": "false",
        "prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_offset_ratio_changed_this_tranche": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
        "tax_output_enabled": "false",
        "mpc_output_enabled": "false",
        "mpc_channel_enabled": "false",
        "holder_allocation_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "reset_calendar_enabled": "false",
        "raw_rate_shock_enabled": "false",
        "empirical_claim_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "causal_financialization_claim_enabled": "false",
    }
