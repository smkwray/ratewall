"""RateWall ingestion helpers for vendored tdcsim contracts."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

from ratewall.accounting.tdc_deposit_channel import (
    TdcCurrentDemandSupportInputs,
    compute_tdc_current_demand_support,
)


DISABLED_SWITCHES = {
    "empirical_claim_enabled": "false",
    "policy_failure_claim_enabled": "false",
    "pricing_output_enabled": "false",
    "incidence_claim_enabled": "false",
    "welfare_claim_enabled": "false",
    "tax_output_enabled": "false",
    "mpc_output_enabled": "false",
    "holder_allocation_enabled": "false",
    "reset_calendar_construction_enabled": "false",
    "raw_rate_shock_enabled": "false",
    "causal_financialization_claim_enabled": "false",
}

CLAIM_BOUNDARY = "ratewall_tdcsim_contract_ingest_assumption_mode_not_evidence"
CONTRACT_DIR = Path("data/raw/ratewall_sibling_calibration/tdcsim")
ASSUMPTION_MODE_CONTRACT_DIR = Path(
    "data/raw/ratewall_sibling_calibration/tdcsim_assumption_mode"
)
TDCEST_ESTIMATES_PATH = Path("../tdcest/data/processed/tdc_estimates.csv")
EXPECTED_TDCSIM_CONTRACT_VERSION = "0.3.0"

TDCSIM_SUMMARY_LABEL_FIELDS = [
    "principal_to_du_domestic_nonbank_bil",
    "principal_to_du_mmf_cash_fund_route_bil",
    "bill_discount_interest_to_du_domestic_nonbank_bil",
    "bill_discount_interest_to_du_mmf_cash_fund_route_bil",
    "coupon_interest_to_du_domestic_nonbank_bil",
    "coupon_interest_to_du_mmf_cash_fund_route_bil",
    "frn_interest_to_du_domestic_nonbank_bil",
    "frn_interest_to_du_mmf_cash_fund_route_bil",
    "tips_coupon_interest_to_du_domestic_nonbank_bil",
    "tips_coupon_interest_to_du_mmf_cash_fund_route_bil",
    "tips_inflation_compensation_to_du_domestic_nonbank_bil",
    "tips_inflation_compensation_to_du_mmf_cash_fund_route_bil",
    "auction_absorption_domestic_nonbank_bil",
    "auction_absorption_mmf_cash_fund_route_bil",
    "secondary_trades_domestic_nonbank_bil",
    "secondary_trades_mmf_cash_fund_route_bil",
    "mmf_ru_plumbing_bil",
    "mmf_deposit_pass_through",
    "mmf_deposit_pass_through_status",
    "principal_redeemed_total_bil",
    "bill_discount_interest_to_du_bil",
    "coupon_interest_to_du_bil",
    "frn_interest_to_du_bil",
    "tips_coupon_interest_to_du_bil",
    "tips_inflation_compensation_to_du_bil",
    "secondary_du_to_ru_bil",
    "secondary_ru_to_du_bil",
    "cb_remittance_to_tga_bil",
    "cb_deferred_asset_end_bil",
]

TDCSIM_REQUIRED_SUMMARY_FIELDS = {
    "scenario_id",
    "quarter",
    "tdc_change_bil",
    "tdc_fiscal_flow_bil",
    "tdc_debt_service_principal_to_du_bil",
    "tdc_debt_service_interest_to_du_bil",
    "tdc_auction_absorption_du_bil",
    "tdc_secondary_trades_bil",
    "tdc_other_bil",
    "overlap_cashflow_bil",
    "tdc_change_ex_overlap_bil",
    "gross_issuance_cash_proceeds_bil",
    "gross_issuance_proceeds_absorbed_by_du_bil",
    "component_sum_bil",
    "component_sum_error_bil",
    *TDCSIM_SUMMARY_LABEL_FIELDS,
}

TDCSIM_REQUIRED_COMPONENT_FIELDS = {
    "scenario_id",
    "quarter",
    "component_key",
    "holder_bucket",
    "ratewall_perimeter",
    "security_type",
    "cash_component_key",
    "amount_bil",
    "enters_direct_interest_support",
    "enters_tdc_deposit_support_default",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _decimal(value: str | int | float | Decimal | None) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _fmt(value: Decimal) -> str:
    return str(value.normalize()) if value else "0"


def _csv_fieldnames(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as handle:
        return set(csv.DictReader(handle).fieldnames or [])


def _quarter_key(quarter: str) -> tuple[int, int]:
    if "Q" not in quarter:
        return (-1, -1)
    year, qtr = quarter.split("Q", 1)
    try:
        return (int(year), int(qtr))
    except ValueError:
        return (-1, -1)


def _latest_quarter(rows: list[dict[str, str]]) -> str:
    quarters = [row.get("quarter", "") for row in rows if row.get("quarter")]
    return max(quarters, key=_quarter_key) if quarters else ""


def _latest_by_id(
    rows: list[dict[str, str]],
    *,
    id_field: str,
    ref_quarter: str,
) -> dict[str, dict[str, str]]:
    return {
        row.get(id_field, ""): row
        for row in rows
        if row.get("quarter") == ref_quarter and row.get(id_field)
    }


def _row_amount(
    by_id: dict[str, dict[str, str]],
    route_id: str,
    *amount_fields: str,
) -> str:
    row = by_id.get(route_id, {})
    for field in amount_fields:
        if row.get(field) not in (None, ""):
            return _fmt(_decimal(row.get(field)))
    return "0"


def _tdcest_route_context_fields(
    monetary_rows: list[dict[str, str]],
    mmf_rows: list[dict[str, str]],
    z1_rows: list[dict[str, str]],
) -> dict[str, str]:
    latest_quarter = max(
        (
            quarter
            for quarter in (
                _latest_quarter(monetary_rows),
                _latest_quarter(mmf_rows),
                _latest_quarter(z1_rows),
            )
            if quarter
        ),
        key=_quarter_key,
        default="",
    )
    monetary_latest = _latest_by_id(
        monetary_rows,
        id_field="route_id",
        ref_quarter=latest_quarter,
    )
    mmf_latest = _latest_by_id(mmf_rows, id_field="route_id", ref_quarter=latest_quarter)
    z1_latest = _latest_by_id(
        z1_rows,
        id_field="sector_route_id",
        ref_quarter=latest_quarter,
    )
    latest_values = ";".join(
        [
            "monetary_retail_mmf_m2_non_deposit_qoq_bil="
            + _row_amount(monetary_latest, "retail_mmf_m2_non_deposit_scope", "amount_bil"),
            "monetary_mmf_onrrp_non_m2_qoq_bil="
            + _row_amount(monetary_latest, "mmf_onrrp_runoff_non_m2_plumbing", "amount_bil"),
            "monetary_z1_domestic_nonbank_mixed_qoq_bil="
            + _row_amount(
                monetary_latest,
                "z1_domestic_nonbank_mixed_unknown_m2_scope",
                "amount_bil",
            ),
            "monetary_z1_other_financial_non_m2_qoq_bil="
            + _row_amount(monetary_latest, "z1_other_financial_non_m2_scope", "amount_bil"),
            "z1_mmf_sector_context_bil="
            + _row_amount(z1_latest, "z1_mmf_sector_context", "z1_component_amount_bil"),
            "z1_insurance_pensions_context_bil="
            + _row_amount(
                z1_latest,
                "z1_insurance_pensions_sector_context",
                "z1_component_amount_bil",
            ),
            "sec_nmfp_institutional_treasury_bil="
            + _row_amount(
                mmf_latest,
                "institutional_or_nonretail_mmf_treasury_holdings_context",
                "treasury_total_bil",
            ),
            "sec_nmfp_retail_treasury_bil="
            + _row_amount(
                mmf_latest,
                "retail_mmf_treasury_holdings_context",
                "treasury_total_bil",
            ),
            "sec_nmfp_institutional_onrrp_bil="
            + _row_amount(
                mmf_latest,
                "institutional_or_nonretail_mmf_onrrp_plumbing_context",
                "fed_onrrp_bil",
            ),
            "sec_nmfp_retail_onrrp_bil="
            + _row_amount(
                mmf_latest,
                "retail_mmf_onrrp_plumbing_context",
                "fed_onrrp_bil",
            ),
        ]
    )
    return {
        "linked_tdcest_route_context_artifacts": (
            "ratewall_tdcest_monetary_route_bridge.csv;"
            "ratewall_tdcest_mmf_route_split_context.csv;"
            "ratewall_tdcest_z1_domestic_nonbank_sector_context.csv"
        ),
        "linked_tdcest_latest_quarter": latest_quarter,
        "linked_tdcest_route_context_row_count": str(
            len(monetary_rows) + len(mmf_rows) + len(z1_rows)
        ),
        "linked_tdcest_latest_route_values": latest_values if latest_quarter else "",
    }


def _manifest(contract_dir: Path = CONTRACT_DIR) -> dict:
    path = contract_dir / "tdcsim_ratewall_manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _contract_status(contract_dir: Path = CONTRACT_DIR) -> dict[str, str]:
    manifest = _manifest(contract_dir)
    required = [
        "tdcsim_ratewall_manifest.json",
        "tdcsim_ratewall_quarterly_summary.csv",
        "tdcsim_ratewall_quarterly_components.csv",
        "tdcsim_ratewall_source_registry.csv",
    ]
    missing = [name for name in required if not (contract_dir / name).exists()]
    validation = manifest.get("validation", {}) if isinstance(manifest, dict) else {}
    if missing:
        return {
            "status": "fail_closed_missing_contract",
            "contract_version": str(manifest.get("contract_version", "")) if manifest else "",
            "manifest_hash": str(manifest.get("config_hash", "")) if manifest else "",
            "failure_reason": "missing:" + ",".join(missing),
        }
    if not manifest:
        return {
            "status": "fail_closed_malformed_manifest",
            "contract_version": "",
            "manifest_hash": "",
            "failure_reason": "manifest_unreadable",
        }
    if validation.get("validation_status") != "pass":
        return {
            "status": "fail_closed_contract_validation_failed",
            "contract_version": str(manifest.get("contract_version", "")),
            "manifest_hash": str(manifest.get("config_hash", "")),
            "failure_reason": str(validation.get("failure_reasons", "")),
        }
    contract_version = str(manifest.get("contract_version", ""))
    if contract_version != EXPECTED_TDCSIM_CONTRACT_VERSION:
        return {
            "status": "fail_closed_stale_contract_version",
            "contract_version": contract_version,
            "manifest_hash": str(manifest.get("config_hash", "")),
            "failure_reason": (
                f"expected_contract_version:{EXPECTED_TDCSIM_CONTRACT_VERSION};"
                f"actual:{contract_version}"
            ),
        }
    summary_path = contract_dir / "tdcsim_ratewall_quarterly_summary.csv"
    component_path = contract_dir / "tdcsim_ratewall_quarterly_components.csv"
    missing_summary_fields = sorted(
        TDCSIM_REQUIRED_SUMMARY_FIELDS - _csv_fieldnames(summary_path)
    )
    missing_component_fields = sorted(
        TDCSIM_REQUIRED_COMPONENT_FIELDS - _csv_fieldnames(component_path)
    )
    if missing_summary_fields or missing_component_fields:
        return {
            "status": "fail_closed_missing_contract_fields",
            "contract_version": contract_version,
            "manifest_hash": str(manifest.get("config_hash", "")),
            "failure_reason": ";".join(
                [
                    "missing_summary_fields:" + ",".join(missing_summary_fields),
                    "missing_component_fields:" + ",".join(missing_component_fields),
                ]
            ),
        }
    for row in _read_csv(summary_path):
        tdc_change = _decimal(row.get("tdc_change_bil"))
        overlap = _decimal(row.get("overlap_cashflow_bil"))
        ex_overlap = _decimal(row.get("tdc_change_ex_overlap_bil"))
        if abs((tdc_change - overlap) - ex_overlap) > Decimal("1e-7"):
            return {
                "status": "fail_closed_contract_identity_failed",
                "contract_version": contract_version,
                "manifest_hash": str(manifest.get("config_hash", "")),
                "failure_reason": (
                    "tdc_change_ex_overlap_identity_failed:"
                    f"{row.get('scenario_id', '')}:{row.get('quarter', '')}"
                ),
            }
    for row in _read_csv(component_path):
        if (
            row.get("enters_direct_interest_support") == "true"
            and row.get("enters_tdc_deposit_support_default") == "true"
        ):
            return {
                "status": "fail_closed_contract_identity_failed",
                "contract_version": contract_version,
                "manifest_hash": str(manifest.get("config_hash", "")),
                "failure_reason": (
                    "component_dual_direct_interest_and_tdc_support:"
                    f"{row.get('component_key', '')}"
                ),
            }
    return {
        "status": "pass",
        "contract_version": contract_version,
        "manifest_hash": str(manifest.get("config_hash", "")),
        "failure_reason": "",
    }


TDC_HISTORICAL_SOURCE_CONTRACT_FIELDS = [
    "source_family",
    "artifact_key",
    "series_key",
    "estimator_role",
    "default_classification",
    "binding_blocker",
    "source_status",
    "historical_default_eligible",
    "historical_sensitivity_eligible",
    "historical_diagnostic_only",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDC_HISTORICAL_SELECTED_SERIES_FIELDS = [
    "selection_id",
    "selected_series_key",
    "selection_status",
    "selection_rule",
    "selected_quarter_count",
    "source_status",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDC_FORWARD_PROJECTION_SURFACE_FIELDS = [
    "scenario_id",
    "quarter",
    "demand_conversion_case",
    "canonical_tdc_accounting_path_id",
    "tdcsim_contract_version",
    "tdcsim_manifest_hash",
    "tdc_change_bil",
    "direct_interest_overlap_cashflow_bil",
    "tdc_deposit_support_base_ex_direct_interest_bil",
    "tdc_materialization_beta_scenario",
    "tdc_materialization_beta_assumption",
    "tdc_materialization_beta_low",
    "tdc_materialization_beta_high",
    "tdc_materialization_beta_source_status",
    "deposit_current_demand_share_profile",
    "deposit_current_demand_share_assumption",
    "derived_beta_times_chi_assumption",
    "tdc_deposit_conversion_share_assumption",
    "tdc_net_materialized_deposits_bil",
    "tdc_deposit_current_demand_support_bil",
    "direct_interest_support_bil",
    "combined_noncanonical_support_bil",
    "contract_ingest_status",
    "assumption_mode",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDCSIM_PROJECTION_CONTRACT_BRIDGE_FIELDS = [
    "scenario_id",
    "quarter",
    "tdcsim_contract_version",
    "tdcsim_manifest_hash",
    "tdc_change_bil",
    "tdc_fiscal_flow_bil",
    "tdc_debt_service_principal_to_du_bil",
    "tdc_debt_service_interest_to_du_bil",
    "tdc_auction_absorption_du_bil",
    "tdc_secondary_trades_bil",
    "tdc_other_bil",
    "overlap_cashflow_bil",
    "tdc_change_ex_overlap_bil",
    "gross_issuance_cash_proceeds_bil",
    "gross_issuance_proceeds_absorbed_by_du_bil",
    *TDCSIM_SUMMARY_LABEL_FIELDS,
    "component_sum_bil",
    "component_sum_error_bil",
    "primary_flow_status",
    "secondary_trade_status",
    "other_status",
    "contract_ingest_status",
    "assumption_mode",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDCSIM_DOMESTIC_NONBANK_FUNDING_CLASSIFICATION_FIELDS = [
    "classification_row_id",
    "classification_scope",
    "tdcsim_holder_bucket",
    "current_ratewall_role",
    "current_contract_status",
    "proposed_ratewall_category",
    "funding_route",
    "deposit_funded_status",
    "non_deposit_funded_domestic_nonbank_status",
    "mmf_on_rrp_status",
    "current_ratewall_treatment",
    "next_tdcsim_patch_requirement",
    "allowed_use",
    "blocked_use",
    "exact_blocker",
    "tdcsim_route_contract_status",
    "tdcsim_route_contract_role",
    "tdcsim_route_contract_central_default_eligible",
    "tdcsim_route_contract_sensitivity_only",
    "tdcsim_route_contract_binding_blocker",
    "linked_tdcest_route_context_artifacts",
    "linked_tdcest_latest_quarter",
    "linked_tdcest_route_context_row_count",
    "linked_tdcest_latest_route_values",
    "source_backed_private_bucket_split_status",
    "source_backed_private_bucket_split_blocker",
    "source_artifact",
    "source_status",
    "assumption_mode",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDCSIM_PRIVATE_ROUTE_SENSITIVITY_INGEST_FIELDS = [
    "ingest_row_id",
    "source_contract_version",
    "tdcsim_contract_key",
    "ref_quarter",
    "object_family",
    "route_class",
    "route_subclass",
    "raw_amount_bil",
    "denominator_bil",
    "share_lambda_0",
    "share_lambda_0_5",
    "share_lambda_1",
    "evidence_tier",
    "measurement_stage",
    "mapping_burden",
    "assumption_status",
    "sensitivity_parameter",
    "sensitivity_label",
    "mmf_split_status",
    "onrrp_treatment",
    "source_backed_private_bucket_split_status",
    "bounded_noncanonical_private_route_proxy",
    "source_backed_private_bucket_split_row",
    "central_default_eligible",
    "sensitivity_only",
    "current_demand_eligible",
    "canonical_tdc_math_change",
    "allowed_use",
    "blocked_use",
    "exact_blocker",
    "binding_blocker",
    "contract_ingest_status",
    "source_artifact",
    "source_status",
    "assumption_mode",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "split_denominator_promotion_allowed",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDCSIM_ASSUMPTION_MODE_SUPPORT_INGEST_FIELDS = [
    "ingest_row_id",
    "registry_version",
    "source_support_row_id",
    "producer_project",
    "producer_artifact",
    "route_component_id",
    "normalized_route_component_id",
    "object_family",
    "measurement_stage",
    "evidence_tier",
    "mapping_burden",
    "assumption_status",
    "admissible_use",
    "blocked_use",
    "source_backed_private_bucket_split_status",
    "source_backed_private_bucket_split_row",
    "bounded_or_context_support_row",
    "canonical_tdc_math_change",
    "current_demand_eligible",
    "contract_ingest_status",
    "source_artifact",
    "source_status",
    "assumption_mode",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "split_denominator_promotion_allowed",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDCSIM_ASSUMPTION_MODE_CLAIM_GATE_FIELDS = [
    "gate_id",
    "gate_status",
    "evidence_table",
    "source_scan_result",
    "binding_blocker",
    "assumption_mode",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "current_demand_eligible",
    "source_backed_private_bucket_split_rows",
    "bounded_or_context_support_rows",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDCSIM_ASSUMPTION_MODE_FORECAST_PRIVATE_ROUTE_ENVELOPE_FIELDS = [
    "envelope_row_id",
    "forecast_year",
    "maturity_scenario",
    "holder_scenario",
    "tdcsim_contract_scenario_id",
    "reference_quarter",
    "source_sensitivity_row_id",
    "scenario_basis_artifact",
    "scenario_basis_field",
    "scenario_basis_bil",
    "mpc_invariance_status",
    "object_family",
    "route_class",
    "route_subclass",
    "evidence_tier",
    "measurement_stage",
    "mapping_burden",
    "assumption_status",
    "share_lambda_0",
    "share_lambda_0_5",
    "share_lambda_1",
    "route_amount_lambda_0_bil",
    "route_amount_lambda_0_5_bil",
    "route_amount_lambda_1_bil",
    "route_amount_bandwidth_bil",
    "source_backed_private_bucket_split_status",
    "source_backed_private_bucket_split_row",
    "current_demand_eligible",
    "canonical_tdc_math_change",
    "allowed_use",
    "blocked_use",
    "exact_blocker",
    "binding_blocker",
    "source_artifact",
    "source_status",
    "assumption_mode",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "split_denominator_promotion_allowed",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDCSIM_ASSUMPTION_MODE_FORECAST_PRIVATE_ROUTE_CLAIM_GATE_FIELDS = [
    "gate_id",
    "gate_status",
    "envelope_table",
    "underlying_sensitivity_table",
    "funding_classification_table",
    "scenario_rows",
    "route_class_rows",
    "envelope_rows",
    "expected_envelope_rows",
    "reference_quarter",
    "object_family",
    "mpc_invariance_failures",
    "central_share_sum_failure_rows",
    "scenario_variation_status",
    "source_backed_private_bucket_split_rows",
    "current_demand_eligible_rows",
    "holder_allocation_enabled_rows",
    "canonical_ratio_entry_rows",
    "scenario_math_changed_rows",
    "forbidden_enabled_rows",
    "binding_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "source_status",
    "assumption_mode",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "current_demand_eligible",
    "denominator_prior_update_allowed",
    "prior_narrowing_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "split_denominator_promotion_allowed",
    *DISABLED_SWITCHES,
]

TDC_FORWARD_COMPONENT_AUDIT_FIELDS = [
    "scenario_id",
    "quarter",
    "component_key",
    "holder_bucket",
    "ratewall_perimeter",
    "security_type",
    "cash_component_key",
    "amount_bil",
    "enters_direct_interest_support",
    "enters_tdc_deposit_support_default",
    "component_dual_entry_status",
    "source_family",
    "observability_tier",
    "assumption_status",
    "contract_ingest_status",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDC_FORWARD_OVERLAP_GUARDRAIL_FIELDS = [
    "scenario_id",
    "quarter",
    "tdc_change_bil",
    "direct_interest_overlap_cashflow_bil",
    "tdc_change_ex_overlap_bil",
    "recomputed_tdc_change_ex_overlap_bil",
    "overlap_identity_error_bil",
    "overlap_subtracted_before_demand_conversion",
    "principal_overlap_subtracted",
    "guardrail_status",
    "contract_ingest_status",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDC_FORWARD_INVARIANT_AUDIT_FIELDS = [
    "audit_item",
    "audit_status",
    "evidence_table",
    "failure_mode_if_false",
    "contract_ingest_status",
    "prior_narrowing_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "dynamic_equation_changed_this_tranche",
    "split_denominator_promotion_allowed",
    "forbidden_switches_remain_disabled",
    "claim_boundary",
]

TDC_FORWARD_ASSUMPTION_REGISTRY_FIELDS = [
    "assumption_id",
    "assumption_family",
    "assumption_value",
    "assumption_low",
    "assumption_high",
    "derived_from_assumption_ids",
    "source_status",
    "allowed_use",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

TDC_FORWARD_SCENARIO_DECOMPOSITION_FIELDS = [
    "scenario_id",
    "quarter",
    "decomposition_component",
    "component_amount_bil",
    "included_in_tdc_ex_direct_interest_base",
    "direct_interest_overlap_component",
    "canonical_tdc_accounting_path_id",
    "source_table",
    "contract_ingest_status",
    "assumption_mode",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

CANONICAL_TDC_ACCOUNTING_PATH_FIELDS = [
    "tdc_path_id",
    "quarter",
    "path_type",
    "source_project",
    "source_artifact",
    "source_contract_version",
    "tdc_change_bil",
    "primary_fiscal_flow_to_du_bil",
    "interest_to_du_bil",
    "principal_to_du_bil",
    "auction_absorption_by_du_bil",
    "secondary_du_to_ru_bil",
    "secondary_ru_to_du_bil",
    "secondary_trades_net_bil",
    "other_bil",
    "component_sum_bil",
    "component_sum_error_bil",
    "direct_interest_overlap_cashflow_bil",
    "tdc_change_ex_direct_interest_overlap_bil",
    "secondary_trade_status",
    "other_status",
    "source_status",
    "component_identity_status",
    "overlap_guardrail_status",
    "principal_overlap_subtracted",
    "canonical_tdc_accounting_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

CANONICAL_TDC_STITCHED_ACCOUNTING_PATH_FIELDS = [
    "tdc_path_id",
    "quarter",
    "path_segment",
    "handoff_quarter",
    "source_project",
    "source_artifact",
    "source_series_key",
    "source_contract_version",
    "tdc_change_bil",
    "component_detail_status",
    "path_type",
    "primary_fiscal_flow_to_du_bil",
    "interest_to_du_bil",
    "principal_to_du_bil",
    "auction_absorption_by_du_bil",
    "secondary_du_to_ru_bil",
    "secondary_ru_to_du_bil",
    "secondary_trades_net_bil",
    "other_bil",
    "component_sum_bil",
    "component_sum_error_bil",
    "direct_interest_overlap_cashflow_bil",
    "tdc_change_ex_direct_interest_overlap_bil",
    "secondary_trade_status",
    "other_status",
    "source_status",
    "component_identity_status",
    "overlap_guardrail_status",
    "principal_overlap_subtracted",
    "canonical_tdc_accounting_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]

CANONICAL_TDC_ACCOUNTING_SOURCE_HIERARCHY_AUDIT_FIELDS = [
    "audit_item",
    "audit_status",
    "source_family",
    "source_artifact",
    "evidence_summary",
    "failure_mode_if_false",
    "canonical_accounting_status",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "claim_boundary",
    *DISABLED_SWITCHES,
]


def _quarter_from_date(value: str) -> str:
    if not value:
        return ""
    try:
        year, month, _ = value.split("-")
        quarter = (int(month) - 1) // 3 + 1
        return f"{int(year)}Q{quarter}"
    except (ValueError, TypeError):
        return ""


def _selected_series_key(selected_rows: list[dict[str, str]] | None = None) -> str:
    if selected_rows:
        return selected_rows[0].get("selected_series_key", "")
    selected = tdc_historical_selected_series_rows(tdc_historical_source_contract_rows())
    return selected[0].get("selected_series_key", "") if selected else ""


def _historical_tdc_flow_rows(
    selected_rows: list[dict[str, str]] | None = None,
    *,
    estimates_path: Path = TDCEST_ESTIMATES_PATH,
) -> list[dict[str, str]]:
    key = _selected_series_key(selected_rows)
    if not key or not estimates_path.exists():
        return []
    rows = _read_csv(estimates_path)
    out: list[dict[str, str]] = []
    for row in rows:
        value = row.get(key, "")
        if value in {"", "nan", "NaN", "None", None}:
            continue
        quarter = _quarter_from_date(row.get("date", ""))
        if not quarter:
            continue
        out.append(
            {
                "quarter": quarter,
                "tdc_change_bil": _fmt(_decimal(value)),
                "source_series_key": key,
            }
        )
    return out


def tdc_historical_source_contract_rows() -> list[dict[str, str]]:
    sibling_path = Path("../tdcest/data/processed/tdc_downstream_estimator_contract.csv")
    rows = _read_csv(sibling_path)
    if not rows:
        return [
            {
                "source_family": "tdcest",
                "artifact_key": str(sibling_path),
                "series_key": "",
                "estimator_role": "",
                "default_classification": "fail_closed",
                "binding_blocker": "tdcest_downstream_estimator_contract_missing",
                "source_status": "sibling_contract_missing_fail_closed",
                "historical_default_eligible": "false",
                "historical_sensitivity_eligible": "false",
                "historical_diagnostic_only": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "claim_boundary": "tdcest_historical_contract_missing_not_ratewall_default",
                **DISABLED_SWITCHES,
            }
        ]
    out = []
    for row in rows:
        key = (
            row.get("estimator_key")
            or row.get("series_key")
            or row.get("tdc_estimator_key")
            or row.get("artifact_key")
            or ""
        )
        role = row.get("current_role") or row.get("estimator_role") or row.get("best_downstream_use", "")
        classification = row.get("default_classification") or row.get("contract_classification", "")
        blocker = row.get("binding_blocker") or row.get("exact_final_blocker", "")
        lowered = " ".join([key, role, classification]).lower()
        diagnostic_only = (
            "true"
            if "tier3" in lowered
            or "diagnostic" in lowered
            or "partial_shell" in lowered
            or "nondefault" in lowered
            or blocker not in {"", "none"}
            else "false"
        )
        default_eligible = (
            "true"
            if role in {"working_corrected_headline"}
            or classification in {"headline_default"}
            else "false"
        )
        out.append(
            {
                "source_family": "tdcest",
                "artifact_key": str(sibling_path),
                "series_key": key,
                "estimator_role": role,
                "default_classification": classification,
                "binding_blocker": blocker,
                "source_status": "sibling_contract_ingested",
                "historical_default_eligible": default_eligible if diagnostic_only == "false" else "false",
                "historical_sensitivity_eligible": "true",
                "historical_diagnostic_only": diagnostic_only,
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "claim_boundary": "tdcest_historical_contract_bridge_not_ratewall_evidence_promotion",
                **DISABLED_SWITCHES,
            }
        )
    return out


def tdc_historical_selected_series_rows(
    source_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    eligible = [
        row
        for row in source_rows
        if row.get("historical_default_eligible") == "true"
        and row.get("historical_diagnostic_only") == "false"
    ]
    selected = eligible[0] if eligible else None
    return [
        {
            "selection_id": "tdcest_contract_selected_series",
            "selected_series_key": selected.get("series_key", "") if selected else "",
            "selection_status": "selected_from_tdcest_contract"
            if selected
            else "fail_closed_no_contract_default_alias",
            "selection_rule": (
                "use_tdcest_contract_default_alias_or_approved_tier2_role;"
                "tier3_rows_diagnostic_until_receipt_completion"
            ),
            "selected_quarter_count": "0",
            "source_status": selected.get("source_status", "") if selected else "no_default_selected",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "claim_boundary": "tdcest_selected_series_contract_not_ratewall_canonical_default",
            **DISABLED_SWITCHES,
        }
    ]


def _tdc_materialization_beta_registry_rows() -> list[dict[str, str]]:
    contract = _read_csv(
        Path("../ea-tdc/outputs/tables/ea_tdc_pass_through_ratewall_import_contract.csv")
    )
    by_regime = {row.get("regime_id", ""): row for row in contract}
    normal = by_regime.get("normal_forward", {})
    latest = by_regime.get("latest_rolling_persistence", {})
    high = by_regime.get("pandemic_exclusion_drop_2021", {})
    low = by_regime.get("pandemic_exclusion_drop_2020", {})

    def beta_row(
        *,
        assumption_id: str,
        assumption_value: str,
        low_value: str,
        high_value: str,
        source_status: str,
        allowed_use: str,
        canonical: str = "false",
    ) -> dict[str, str]:
        return {
            "assumption_id": assumption_id,
            "assumption_family": "tdc_materialization_beta",
            "assumption_value": assumption_value,
            "assumption_low": low_value,
            "assumption_high": high_value,
            "derived_from_assumption_ids": "",
            "source_status": source_status,
            "allowed_use": allowed_use,
            "enters_main_ratio": canonical,
            "evidence_mode_enabled": "false",
            "canonical_ratio_entry": canonical,
            "claim_boundary": (
                "tdc_materialization_beta_labeled_assumption_mode_not_runtime_selector"
            ),
            **DISABLED_SWITCHES,
        }

    return [
        beta_row(
            assumption_id="tdc_materialization_beta_normal_forward",
            assumption_value=normal.get("pass_through_point", "0.3420"),
            low_value=normal.get("pass_through_lower95", "0.1155"),
            high_value=normal.get("pass_through_upper95", "0.5685"),
            source_status=(
                normal.get("recommended_ratewall_use")
                or "assumption_mode_scenario_allowed"
            ),
            allowed_use="canonical_tdcsim_forward_surface_default_beta",
            canonical="true",
        ),
        beta_row(
            assumption_id="tdc_materialization_beta_low_conservative",
            assumption_value=low.get("pass_through_point", "0.2478871263682468"),
            low_value=low.get("pass_through_lower95", ""),
            high_value=low.get("pass_through_upper95", ""),
            source_status=low.get("recommended_ratewall_use") or "assumption_mode_scenario_allowed",
            allowed_use="canonical_tdcsim_forward_surface_sensitivity_beta",
        ),
        beta_row(
            assumption_id="tdc_materialization_beta_latest_rolling_persistence",
            assumption_value=latest.get("pass_through_point", "0.5307509589554447"),
            low_value=latest.get("pass_through_lower95", ""),
            high_value=latest.get("pass_through_upper95", ""),
            source_status=(
                latest.get("recommended_ratewall_use")
                or "assumption_mode_scenario_allowed"
            ),
            allowed_use="canonical_tdcsim_forward_surface_user_selected_beta",
        ),
        beta_row(
            assumption_id="tdc_materialization_beta_high_materialization_postcovid",
            assumption_value=high.get("pass_through_point", "0.7431033707535825"),
            low_value=high.get("pass_through_lower95", ""),
            high_value=high.get("pass_through_upper95", ""),
            source_status=high.get("recommended_ratewall_use") or "assumption_mode_scenario_allowed",
            allowed_use="canonical_tdcsim_forward_surface_user_selected_beta_not_default",
        ),
    ]


def tdc_forward_assumption_registry_rows() -> list[dict[str, str]]:
    chi_rows = [
        {
            "assumption_id": "tdc_deposit_conversion_low",
            "assumption_family": "tdc_deposit_current_demand_conversion",
            "assumption_value": "0.03",
            "assumption_low": "0.03",
            "assumption_high": "0.12",
            "derived_from_assumption_ids": "",
            "source_status": "evidence_c_chi_assumption_mode_not_beta_or_mpc_output",
            "allowed_use": "canonical_tdcsim_forward_surface_chi",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "canonical_ratio_entry": "false",
            "claim_boundary": CLAIM_BOUNDARY,
            **DISABLED_SWITCHES,
        },
        {
            "assumption_id": "tdc_deposit_conversion_base",
            "assumption_family": "tdc_deposit_current_demand_conversion",
            "assumption_value": "0.07",
            "assumption_low": "0.03",
            "assumption_high": "0.12",
            "derived_from_assumption_ids": "",
            "source_status": "evidence_c_chi_assumption_mode_not_beta_or_mpc_output",
            "allowed_use": "canonical_tdcsim_forward_surface_default_chi",
            "enters_main_ratio": "true",
            "evidence_mode_enabled": "false",
            "canonical_ratio_entry": "true",
            "claim_boundary": CLAIM_BOUNDARY,
            **DISABLED_SWITCHES,
        },
        {
            "assumption_id": "tdc_deposit_conversion_high",
            "assumption_family": "tdc_deposit_current_demand_conversion",
            "assumption_value": "0.12",
            "assumption_low": "0.03",
            "assumption_high": "0.12",
            "derived_from_assumption_ids": "",
            "source_status": "evidence_c_chi_assumption_mode_not_beta_or_mpc_output",
            "allowed_use": "canonical_tdcsim_forward_surface_chi",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "canonical_ratio_entry": "false",
            "claim_boundary": CLAIM_BOUNDARY,
            **DISABLED_SWITCHES,
        },
    ]
    derived_rows = []
    normal = next(
        row
        for row in _tdc_materialization_beta_registry_rows()
        if row["assumption_id"] == "tdc_materialization_beta_normal_forward"
    )
    for chi in chi_rows:
        composite = _decimal(normal["assumption_value"]) * _decimal(chi["assumption_value"])
        derived_rows.append(
            {
                "assumption_id": (
                    "tdc_deposit_conversion_share_assumption_derived_"
                    f"{chi['assumption_id'].removeprefix('tdc_deposit_conversion_')}"
                ),
                "assumption_family": "tdc_deposit_conversion_share_assumption_derived_alias",
                "assumption_value": _fmt(composite),
                "assumption_low": "",
                "assumption_high": "",
                "derived_from_assumption_ids": (
                    f"{normal['assumption_id']};{chi['assumption_id']}"
                ),
                "source_status": "derived_alias_beta_times_chi_not_standalone_kappa",
                "allowed_use": "derived_compatibility_alias_not_direct_coefficient",
                "enters_main_ratio": chi["enters_main_ratio"],
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": chi["canonical_ratio_entry"],
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        )
    return _tdc_materialization_beta_registry_rows() + chi_rows + derived_rows


def tdc_forward_projection_surface_rows(
    contract_dir: Path = CONTRACT_DIR,
) -> list[dict[str, str]]:
    status = _contract_status(contract_dir)
    summary = _read_csv(contract_dir / "tdcsim_ratewall_quarterly_summary.csv")
    assumptions = [
        row
        for row in tdc_forward_assumption_registry_rows()
        if row["assumption_family"] == "tdc_deposit_current_demand_conversion"
    ]
    beta = next(
        row
        for row in tdc_forward_assumption_registry_rows()
        if row["assumption_id"] == "tdc_materialization_beta_normal_forward"
    )
    if status["status"] != "pass" or not summary:
        return [
            {
                "scenario_id": "",
                "quarter": "",
                "demand_conversion_case": "",
                "canonical_tdc_accounting_path_id": "",
                "tdcsim_contract_version": status["contract_version"],
                "tdcsim_manifest_hash": status["manifest_hash"],
                "tdc_change_bil": "0",
                "direct_interest_overlap_cashflow_bil": "0",
                "tdc_deposit_support_base_ex_direct_interest_bil": "0",
                "tdc_materialization_beta_scenario": "",
                "tdc_materialization_beta_assumption": "0",
                "tdc_materialization_beta_low": "",
                "tdc_materialization_beta_high": "",
                "tdc_materialization_beta_source_status": "",
                "deposit_current_demand_share_profile": "",
                "deposit_current_demand_share_assumption": "0",
                "derived_beta_times_chi_assumption": "0",
                "tdc_deposit_conversion_share_assumption": "0",
                "tdc_net_materialized_deposits_bil": "0",
                "tdc_deposit_current_demand_support_bil": "0",
                "direct_interest_support_bil": "0",
                "combined_noncanonical_support_bil": "0",
                "contract_ingest_status": status["status"],
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        ]
    out = []
    for row in summary:
        tdc_change = _decimal(row.get("tdc_change_bil"))
        overlap = _decimal(row.get("overlap_cashflow_bil"))
        base = _decimal(row.get("tdc_change_ex_overlap_bil"))
        for assumption in assumptions:
            support = compute_tdc_current_demand_support(
                TdcCurrentDemandSupportInputs(
                    tdc_change_ex_overlap_bil=base,
                    tdc_materialization_beta=beta["assumption_value"],
                    deposit_current_demand_share=assumption["assumption_value"],
                )
            )
            share = _decimal(assumption["assumption_value"])
            tdc_support = support["tdc_current_demand_support_bil"]
            direct_support = overlap * share
            out.append(
                {
                    "scenario_id": row.get("scenario_id", ""),
                    "quarter": row.get("quarter", ""),
                    "demand_conversion_case": assumption["assumption_id"],
                    "canonical_tdc_accounting_path_id": (
                        f"forward_tdcsim_{row.get('scenario_id', '')}"
                    ),
                    "tdcsim_contract_version": status["contract_version"],
                    "tdcsim_manifest_hash": status["manifest_hash"],
                    "tdc_change_bil": _fmt(tdc_change),
                    "direct_interest_overlap_cashflow_bil": _fmt(overlap),
                    "tdc_deposit_support_base_ex_direct_interest_bil": _fmt(base),
                    "tdc_materialization_beta_scenario": beta["assumption_id"],
                    "tdc_materialization_beta_assumption": beta["assumption_value"],
                    "tdc_materialization_beta_low": beta["assumption_low"],
                    "tdc_materialization_beta_high": beta["assumption_high"],
                    "tdc_materialization_beta_source_status": beta["source_status"],
                    "deposit_current_demand_share_profile": assumption["assumption_id"],
                    "deposit_current_demand_share_assumption": assumption[
                        "assumption_value"
                    ],
                    "derived_beta_times_chi_assumption": _fmt(
                        support["derived_beta_times_chi"]
                    ),
                    "tdc_deposit_conversion_share_assumption": _fmt(
                        support["derived_beta_times_chi"]
                    ),
                    "tdc_net_materialized_deposits_bil": _fmt(
                        support["tdc_net_materialized_deposits_bil"]
                    ),
                    "tdc_deposit_current_demand_support_bil": _fmt(tdc_support),
                    "direct_interest_support_bil": _fmt(direct_support),
                    "combined_noncanonical_support_bil": _fmt(tdc_support + direct_support),
                    "contract_ingest_status": status["status"],
                    "assumption_mode": "true",
                    "enters_main_ratio": "false",
                    "evidence_mode_enabled": "false",
                    "canonical_ratio_entry": "false",
                    "claim_boundary": CLAIM_BOUNDARY,
                    **DISABLED_SWITCHES,
                }
            )
    return out


def tdcsim_projection_contract_bridge_rows(
    contract_dir: Path = CONTRACT_DIR,
) -> list[dict[str, str]]:
    status = _contract_status(contract_dir)
    summary = _read_csv(contract_dir / "tdcsim_ratewall_quarterly_summary.csv")
    if status["status"] != "pass" or not summary:
        return [
            {
                "scenario_id": "",
                "quarter": "",
                "tdcsim_contract_version": status["contract_version"],
                "tdcsim_manifest_hash": status["manifest_hash"],
                "tdc_change_bil": "0",
                "tdc_fiscal_flow_bil": "0",
                "tdc_debt_service_principal_to_du_bil": "0",
                "tdc_debt_service_interest_to_du_bil": "0",
                "tdc_auction_absorption_du_bil": "0",
                "tdc_secondary_trades_bil": "0",
                "tdc_other_bil": "0",
                "overlap_cashflow_bil": "0",
                "tdc_change_ex_overlap_bil": "0",
                "gross_issuance_cash_proceeds_bil": "0",
                "gross_issuance_proceeds_absorbed_by_du_bil": "0",
                **{field: "0" for field in TDCSIM_SUMMARY_LABEL_FIELDS},
                "component_sum_bil": "0",
                "component_sum_error_bil": "0",
                "primary_flow_status": "",
                "secondary_trade_status": "",
                "other_status": "",
                "contract_ingest_status": status["status"],
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        ]
    out = []
    for row in summary:
        out.append(
            {
                "scenario_id": row.get("scenario_id", ""),
                "quarter": row.get("quarter", ""),
                "tdcsim_contract_version": status["contract_version"],
                "tdcsim_manifest_hash": status["manifest_hash"],
                "tdc_change_bil": row.get("tdc_change_bil", "0"),
                "tdc_fiscal_flow_bil": row.get("tdc_fiscal_flow_bil", "0"),
                "tdc_debt_service_principal_to_du_bil": row.get(
                    "tdc_debt_service_principal_to_du_bil", "0"
                ),
                "tdc_debt_service_interest_to_du_bil": row.get(
                    "tdc_debt_service_interest_to_du_bil", "0"
                ),
                "tdc_auction_absorption_du_bil": row.get(
                    "tdc_auction_absorption_du_bil", "0"
                ),
                "tdc_secondary_trades_bil": row.get("tdc_secondary_trades_bil", "0"),
                "tdc_other_bil": row.get("tdc_other_bil", "0"),
                "overlap_cashflow_bil": row.get("overlap_cashflow_bil", "0"),
                "tdc_change_ex_overlap_bil": row.get("tdc_change_ex_overlap_bil", "0"),
                "gross_issuance_cash_proceeds_bil": row.get(
                    "gross_issuance_cash_proceeds_bil", "0"
                ),
                "gross_issuance_proceeds_absorbed_by_du_bil": row.get(
                    "gross_issuance_proceeds_absorbed_by_du_bil", "0"
                ),
                **{
                    field: row.get(field, "0")
                    for field in TDCSIM_SUMMARY_LABEL_FIELDS
                },
                "component_sum_bil": row.get("component_sum_bil", "0"),
                "component_sum_error_bil": row.get("component_sum_error_bil", "0"),
                "primary_flow_status": row.get("primary_flow_status", ""),
                "secondary_trade_status": row.get("secondary_trade_status", ""),
                "other_status": row.get("other_status", ""),
                "contract_ingest_status": status["status"],
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        )
    return out


def tdcsim_domestic_nonbank_funding_classification_rows(
    contract_dir: Path = CONTRACT_DIR,
    *,
    tdcest_monetary_route_bridge_rows: list[dict[str, str]] | None = None,
    tdcest_mmf_route_split_context_rows: list[dict[str, str]] | None = None,
    tdcest_z1_domestic_nonbank_sector_context_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    status = _contract_status(contract_dir)
    source_artifact = contract_dir / "tdcsim_ratewall_source_registry.csv"
    source_registry = _read_csv(source_artifact)
    holder_rows = [
        row for row in source_registry if row.get("source_family") == "holder_mapping"
    ]
    route_rows = {
        row.get("source_key", ""): row
        for row in source_registry
        if row.get("source_family") == "holder_route_contract"
    }
    route_context = _tdcest_route_context_fields(
        tdcest_monetary_route_bridge_rows or [],
        tdcest_mmf_route_split_context_rows or [],
        tdcest_z1_domestic_nonbank_sector_context_rows or [],
    )

    def empty_route_context_fields() -> dict[str, str]:
        return {
            "linked_tdcest_route_context_artifacts": "",
            "linked_tdcest_latest_quarter": "",
            "linked_tdcest_route_context_row_count": "0",
            "linked_tdcest_latest_route_values": "",
            "source_backed_private_bucket_split_status": (
                "not_applicable_to_this_tdcsim_holder_bucket"
            ),
            "source_backed_private_bucket_split_blocker": "",
        }

    def private_bucket_route_context_fields(
        *,
        status_value: str,
        blocker: str,
    ) -> dict[str, str]:
        return {
            **route_context,
            "source_backed_private_bucket_split_status": status_value,
            "source_backed_private_bucket_split_blocker": blocker,
        }

    def route_contract_fields(route_id: str) -> dict[str, str]:
        route = route_rows.get(route_id, {})
        return {
            "tdcsim_route_contract_status": route.get(
                "source_status", "route_contract_absent_from_tdcsim_source_registry"
            ),
            "tdcsim_route_contract_role": route.get("ratewall_role", ""),
            "tdcsim_route_contract_central_default_eligible": route.get(
                "central_default_eligible", "false"
            ),
            "tdcsim_route_contract_sensitivity_only": route.get(
                "sensitivity_only", "true"
            ),
            "tdcsim_route_contract_binding_blocker": route.get(
                "binding_blocker", "missing_holder_route_contract_row"
            ),
        }

    if status["status"] != "pass" or not holder_rows:
        return [
            {
                "classification_row_id": "tdcsim_holder_funding_classification::fail_closed",
                "classification_scope": "tdcsim_holder_funding_route_contract",
                "tdcsim_holder_bucket": "",
                "current_ratewall_role": "",
                "current_contract_status": status["status"],
                "proposed_ratewall_category": "",
                "funding_route": "",
                "deposit_funded_status": "",
                "non_deposit_funded_domestic_nonbank_status": "fail_closed_missing_holder_mapping",
                "mmf_on_rrp_status": "fail_closed_missing_holder_mapping",
                "current_ratewall_treatment": "no_current_contract_classification",
                "next_tdcsim_patch_requirement": (
                    "restore holder_mapping rows before domestic-nonbank funding "
                    "route classification"
                ),
                "allowed_use": "fail_closed_tdcsim_contract_diagnostic",
                "blocked_use": "forecast_math;holder_allocation;incidence;pricing;canonical_rw_y",
                "exact_blocker": status["failure_reason"],
                **route_contract_fields(""),
                **empty_route_context_fields(),
                "source_artifact": str(source_artifact),
                "source_status": "missing_or_invalid_tdcsim_holder_mapping",
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        ]

    rows: list[dict[str, str]] = []
    for row in holder_rows:
        holder_bucket = row.get("source_key", "")
        current_role = row.get("ratewall_role", "")
        route_contract = route_contract_fields(holder_bucket)
        if holder_bucket == "Private":
            proposed_category = (
                route_contract["tdcsim_route_contract_role"]
                or "domestic_nonbank_undifferentiated_current_contract"
            )
            funding_route = "funding_route_not_observed_in_current_private_bucket"
            deposit_status = "not_separately_identified_current_private_bucket"
            non_deposit_status = (
                "blocked_missing_explicit_non_deposit_funded_domestic_nonbank_bucket"
            )
            mmf_status = "blocked_mmf_on_rrp_not_split_from_private_bucket"
            current_treatment = "treated_as_DU_in_current_tdcsim_contract"
            next_requirement = (
                "split Private holder bucket into deposit-funded domestic "
                "nonbanks and non-deposit-funded domestic nonbanks before using "
                "funding-route-specific current-demand assumptions"
            )
            blocker = "current_private_bucket_mixes_deposit_and_non_deposit_funding_routes"
            route_context_fields = private_bucket_route_context_fields(
                status_value="source_context_available_private_bucket_still_unsplit",
                blocker=(
                    "tdcest_z1_mmf_and_monetary_route_context_does_not_allocate_"
                    "current_tdcsim_private_bucket_across_deposit_non_deposit_and_"
                    "mmf_onrrp_routes"
                ),
            )
        elif current_role == "RU":
            proposed_category = "reserve_user_current_contract_bucket"
            funding_route = "reserve_user_or_external_holder_route"
            deposit_status = "not_domestic_nonbank_deposit_funded_route"
            non_deposit_status = "not_domestic_nonbank_target_bucket"
            mmf_status = "not_mmf_on_rrp_target_bucket"
            current_treatment = "treated_as_RU_in_current_tdcsim_contract"
            next_requirement = "none_for_this_existing_holder_bucket"
            blocker = ""
            route_context_fields = empty_route_context_fields()
        elif current_role == "intragov":
            proposed_category = "intragovernmental_current_contract_bucket"
            funding_route = "intragovernmental_not_private_funding_route"
            deposit_status = "not_domestic_nonbank_deposit_funded_route"
            non_deposit_status = "not_domestic_nonbank_target_bucket"
            mmf_status = "not_mmf_on_rrp_target_bucket"
            current_treatment = "excluded_from_private_recipient_funding_route_split"
            next_requirement = "none_for_this_existing_holder_bucket"
            blocker = ""
            route_context_fields = empty_route_context_fields()
        else:
            proposed_category = "unclassified_current_contract_bucket"
            funding_route = "unknown_current_contract_route"
            deposit_status = "unknown"
            non_deposit_status = "unknown"
            mmf_status = "unknown"
            current_treatment = "fail_closed_unclassified_holder_bucket"
            next_requirement = "classify holder bucket before using in RateWall"
            blocker = "unclassified_tdcsim_holder_bucket"
            route_context_fields = empty_route_context_fields()
        rows.append(
            {
                "classification_row_id": (
                    "tdcsim_holder_funding_classification::current::"
                    f"{holder_bucket}"
                ),
                "classification_scope": "current_tdcsim_holder_mapping",
                "tdcsim_holder_bucket": holder_bucket,
                "current_ratewall_role": current_role,
                "current_contract_status": row.get("source_status", ""),
                "proposed_ratewall_category": proposed_category,
                "funding_route": funding_route,
                "deposit_funded_status": deposit_status,
                "non_deposit_funded_domestic_nonbank_status": non_deposit_status,
                "mmf_on_rrp_status": mmf_status,
                "current_ratewall_treatment": current_treatment,
                "next_tdcsim_patch_requirement": next_requirement,
                "allowed_use": "tdcsim_holder_funding_route_gap_diagnostic",
                "blocked_use": "forecast_math;holder_allocation;incidence;pricing;canonical_rw_y",
                "exact_blocker": blocker,
                **route_contract,
                **route_context_fields,
                "source_artifact": str(source_artifact),
                "source_status": row.get("source_status", ""),
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        )

    target_specs = [
        {
            "target_id": "domestic_nonbank_non_deposit_funded",
            "proposed_ratewall_category": "domestic_nonbank_non_deposit_funded",
            "funding_route": "non_deposit_funded_domestic_nonbank_cash_or_security_absorption",
            "deposit_funded_status": "explicitly_not_deposit_funded_target",
            "non_deposit_status": "route_contract_present_but_not_current_holder_bucket",
            "mmf_status": "may_include_mmf_when_not_on_rrp_route_specific",
            "current_treatment": "not_represented_separately_in_current_tdcsim_contract",
            "next_requirement": (
                "source-back the split from the current Private bucket before "
                "using this route in RateWall forecast math"
            ),
            "blocker": "missing_non_deposit_funded_domestic_nonbank_contract_bucket",
            "split_status": (
                "source_context_available_target_route_not_current_tdcsim_holder_bucket"
            ),
            "split_blocker": (
                "z1_and_monetary_route_context_do_not_source_back_private_bucket_"
                "split_or_forecast_component_mapping"
            ),
        },
        {
            "target_id": "mmf_cash_fund_route",
            "proposed_ratewall_category": "mmf_on_rrp_reserve_user_like_domestic_nonbank",
            "funding_route": "mmf_on_rrp_or_fed_repo_drawdown_route",
            "deposit_funded_status": "explicitly_not_deposit_funded_target",
            "non_deposit_status": "route_contract_present_but_not_current_holder_bucket",
            "mmf_status": "route_contract_present_but_not_current_holder_bucket",
            "current_treatment": (
                "future_tdcsim_route_should_be_reserve_user_like_for_RateWall_"
                "accounting_until_better_recipient_split_exists"
            ),
            "next_requirement": (
                "source-back an MMF/ON-RRP route split before using the route "
                "as reserve-user-like in RateWall forecast math"
            ),
            "blocker": "missing_mmf_on_rrp_route_specific_contract_bucket",
            "split_status": (
                "source_context_available_mmf_onrrp_amounts_not_tdcsim_bucket_split"
            ),
            "split_blocker": (
                "sec_nmfp_and_tdcest_onrrp_context_do_not_identify_final_investor_"
                "or_create_current_tdcsim_holder_bucket"
            ),
        },
    ]
    for spec in target_specs:
        route_contract = route_contract_fields(spec["target_id"])
        route_present = (
            route_contract["tdcsim_route_contract_status"] == "route_contract_present"
        )
        rows.append(
            {
                "classification_row_id": (
                    "tdcsim_holder_funding_classification::target::"
                    f"{spec['target_id']}"
                ),
                "classification_scope": "future_tdcsim_contract_requirement",
                "tdcsim_holder_bucket": "",
                "current_ratewall_role": "",
                "current_contract_status": (
                    "route_contract_present_target_not_current_holder_type"
                    if route_present
                    else "fail_closed_missing_explicit_contract_bucket"
                ),
                "proposed_ratewall_category": spec["proposed_ratewall_category"],
                "funding_route": spec["funding_route"],
                "deposit_funded_status": spec["deposit_funded_status"],
                "non_deposit_funded_domestic_nonbank_status": spec[
                    "non_deposit_status"
                ],
                "mmf_on_rrp_status": spec["mmf_status"],
                "current_ratewall_treatment": spec["current_treatment"],
                "next_tdcsim_patch_requirement": spec["next_requirement"],
                "allowed_use": "tdcsim_sibling_route_contract_diagnostic",
                "blocked_use": "forecast_math;holder_allocation;incidence;pricing;canonical_rw_y",
                "exact_blocker": (
                    route_contract["tdcsim_route_contract_binding_blocker"]
                    if route_present
                    else spec["blocker"]
                ),
                **route_contract,
                **private_bucket_route_context_fields(
                    status_value=spec["split_status"],
                    blocker=spec["split_blocker"],
                ),
                "source_artifact": str(source_artifact),
                "source_status": route_contract["tdcsim_route_contract_status"],
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        )
    return rows


def tdcsim_private_route_sensitivity_ingest_rows(
    contract_dir: Path = CONTRACT_DIR,
) -> list[dict[str, str]]:
    status = _contract_status(contract_dir)
    source_artifact = contract_dir / "tdcsim_private_route_sensitivity_contract.csv"
    source_rows = _read_csv(source_artifact)
    if not source_rows:
        return [
            {
                "ingest_row_id": "tdcsim_private_route_sensitivity::fail_closed",
                "source_contract_version": "",
                "tdcsim_contract_key": "",
                "ref_quarter": "",
                "object_family": "",
                "route_class": "",
                "route_subclass": "",
                "raw_amount_bil": "0",
                "denominator_bil": "0",
                "share_lambda_0": "0",
                "share_lambda_0_5": "0",
                "share_lambda_1": "0",
                "evidence_tier": "unresolved_residual",
                "measurement_stage": "",
                "mapping_burden": "sidecar_missing",
                "assumption_status": "unresolved",
                "sensitivity_parameter": "",
                "sensitivity_label": "",
                "mmf_split_status": "",
                "onrrp_treatment": "",
                "source_backed_private_bucket_split_status": (
                    "not_source_backed_private_bucket_split"
                ),
                "bounded_noncanonical_private_route_proxy": "false",
                "source_backed_private_bucket_split_row": "false",
                "central_default_eligible": "false",
                "sensitivity_only": "true",
                "current_demand_eligible": "false",
                "canonical_tdc_math_change": "false",
                "allowed_use": "fail_closed_missing_tdcsim_private_route_sidecar",
                "blocked_use": (
                    "runtime_default;canonical_rw_y;evidence_mode;holder_allocation;"
                    "pricing;incidence;welfare;tax;mpc;prior_narrowing"
                ),
                "exact_blocker": "tdcsim_private_route_sensitivity_contract_missing",
                "binding_blocker": (
                    "requires_source_backed_split_from_current_private_holder_bucket"
                ),
                "contract_ingest_status": status["status"],
                "source_artifact": str(source_artifact),
                "source_status": "missing_tdcsim_private_route_sidecar",
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "denominator_prior_update_allowed": "false",
                "prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_offset_ratio_changed_this_tranche": "false",
                "split_denominator_promotion_allowed": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        ]

    out: list[dict[str, str]] = []
    for row in source_rows:
        split_status = row.get(
            "source_backed_private_bucket_split_status",
            "not_source_backed_private_bucket_split",
        )
        proxy_row = split_status == "not_source_backed_private_bucket_split"
        out.append(
            {
                "ingest_row_id": row.get(
                    "allocation_row_id",
                    "tdcsim_private_route_sensitivity::row",
                ),
                "source_contract_version": row.get("contract_version", ""),
                "tdcsim_contract_key": row.get("tdcsim_contract_key", ""),
                "ref_quarter": row.get("ref_quarter", ""),
                "object_family": row.get("object_family", ""),
                "route_class": row.get("route_class", ""),
                "route_subclass": row.get("route_subclass", ""),
                "raw_amount_bil": row.get("raw_amount_bil", "0"),
                "denominator_bil": row.get("denominator_bil", "0"),
                "share_lambda_0": row.get("share_lambda_0", "0"),
                "share_lambda_0_5": row.get("share_lambda_0_5", "0"),
                "share_lambda_1": row.get("share_lambda_1", "0"),
                "evidence_tier": row.get("evidence_tier", "bounded_proxy"),
                "measurement_stage": row.get("measurement_stage", ""),
                "mapping_burden": row.get(
                    "mapping_burden", "requires_unobserved_actor_split"
                ),
                "assumption_status": row.get(
                    "assumption_status", "bounded_assumption"
                ),
                "sensitivity_parameter": row.get("sensitivity_parameter", ""),
                "sensitivity_label": row.get("sensitivity_label", ""),
                "mmf_split_status": row.get("mmf_split_status", ""),
                "onrrp_treatment": row.get("onrrp_treatment", ""),
                "source_backed_private_bucket_split_status": split_status,
                "bounded_noncanonical_private_route_proxy": (
                    "true" if proxy_row else "false"
                ),
                "source_backed_private_bucket_split_row": "false",
                "central_default_eligible": "false",
                "sensitivity_only": "true",
                "current_demand_eligible": "false",
                "canonical_tdc_math_change": "false",
                "allowed_use": "noncanonical_private_route_sensitivity_context",
                "blocked_use": (
                    "runtime_default;canonical_rw_y;evidence_mode;holder_allocation;"
                    "pricing;incidence;welfare;tax;mpc;prior_narrowing"
                ),
                "exact_blocker": row.get(
                    "exact_blocker",
                    "requires_source_backed_split_from_current_private_holder_bucket",
                ),
                "binding_blocker": row.get(
                    "binding_blocker",
                    "requires_source_backed_split_from_current_private_holder_bucket",
                ),
                "contract_ingest_status": status["status"],
                "source_artifact": str(source_artifact),
                "source_status": (
                    "bounded_noncanonical_proxy_ingested_not_source_backed_split"
                ),
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "denominator_prior_update_allowed": "false",
                "prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_offset_ratio_changed_this_tranche": "false",
                "split_denominator_promotion_allowed": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        )
    return out


def _assumption_mode_status(contract_dir: Path) -> dict[str, str]:
    registry_path = contract_dir / "tdcsim_route_component_support_registry.csv"
    verdict_path = contract_dir / "tdcsim_route_component_verdict.csv"
    manifest_path = contract_dir / "tdcsim_assumption_mode_manifest.json"
    missing = [
        path.name
        for path in (registry_path, verdict_path, manifest_path)
        if not path.exists()
    ]
    if missing:
        return {
            "status": "fail_closed_missing_assumption_mode_contract",
            "failure_reason": "missing:" + ",".join(missing),
        }
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "fail_closed_malformed_assumption_mode_manifest",
            "failure_reason": "manifest_unreadable",
        }
    validation = payload.get("validation", {})
    if validation.get("validation_status") != "pass":
        return {
            "status": "fail_closed_assumption_mode_validation_failed",
            "failure_reason": str(validation.get("failure_reasons", "")),
        }
    return {"status": "pass", "failure_reason": ""}


def tdcsim_assumption_mode_support_ingest_rows(
    contract_dir: Path = ASSUMPTION_MODE_CONTRACT_DIR,
) -> list[dict[str, str]]:
    status = _assumption_mode_status(contract_dir)
    source_artifact = contract_dir / "tdcsim_route_component_support_registry.csv"
    source_rows = _read_csv(source_artifact)
    if not source_rows:
        return [
            {
                "ingest_row_id": "tdcsim_assumption_mode_support::fail_closed",
                "registry_version": "",
                "source_support_row_id": "",
                "producer_project": "",
                "producer_artifact": "",
                "route_component_id": "",
                "normalized_route_component_id": "",
                "object_family": "",
                "measurement_stage": "",
                "evidence_tier": "unresolved_residual",
                "mapping_burden": "assumption_mode_contract_missing",
                "assumption_status": "unresolved",
                "admissible_use": "diagnostic_only",
                "blocked_use": (
                    "source_backed_private_bucket_split;canonical_tdc_math;"
                    "evidence_mode;final_current_demand;holder_allocation"
                ),
                "source_backed_private_bucket_split_status": (
                    "not_source_backed_private_bucket_split"
                ),
                "source_backed_private_bucket_split_row": "false",
                "bounded_or_context_support_row": "false",
                "canonical_tdc_math_change": "false",
                "current_demand_eligible": "false",
                "holder_allocation_enabled": "false",
                "contract_ingest_status": status["status"],
                "source_artifact": str(source_artifact),
                "source_status": "missing_tdcsim_assumption_mode_support_registry",
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "denominator_prior_update_allowed": "false",
                "prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_offset_ratio_changed_this_tranche": "false",
                "split_denominator_promotion_allowed": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        ]

    out: list[dict[str, str]] = []
    for row in source_rows:
        tier = row.get("evidence_tier", "")
        bounded = tier in {
            "bounded_proxy",
            "context_only",
            "assumption_only",
            "unresolved_residual",
        }
        private_status = row.get(
            "source_backed_private_bucket_split_status",
            "not_source_backed_private_bucket_split",
        )
        out.append(
            {
                "ingest_row_id": row.get("registry_row_id", ""),
                "registry_version": row.get("registry_version", ""),
                "source_support_row_id": row.get("source_support_row_id", ""),
                "producer_project": row.get("producer_project", ""),
                "producer_artifact": row.get("producer_artifact", ""),
                "route_component_id": row.get("route_component_id", ""),
                "normalized_route_component_id": row.get(
                    "normalized_route_component_id", ""
                ),
                "object_family": row.get("object_family", ""),
                "measurement_stage": row.get("measurement_stage", ""),
                "evidence_tier": tier,
                "mapping_burden": row.get("mapping_burden", ""),
                "assumption_status": row.get("assumption_status", ""),
                "admissible_use": row.get("admissible_use", ""),
                "blocked_use": row.get("blocked_use", ""),
                "source_backed_private_bucket_split_status": private_status,
                "source_backed_private_bucket_split_row": "false",
                "bounded_or_context_support_row": "true" if bounded else "false",
                "canonical_tdc_math_change": "false",
                "current_demand_eligible": "false",
                "holder_allocation_enabled": "false",
                "contract_ingest_status": status["status"],
                "source_artifact": str(source_artifact),
                "source_status": "tdcsim_assumption_mode_support_ingested",
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "denominator_prior_update_allowed": "false",
                "prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_offset_ratio_changed_this_tranche": "false",
                "split_denominator_promotion_allowed": "false",
                "claim_boundary": row.get("claim_boundary", CLAIM_BOUNDARY),
                **DISABLED_SWITCHES,
            }
        )
    return out


def tdcsim_assumption_mode_claim_gate_rows(
    support_rows: list[dict[str, str]] | None = None,
    contract_dir: Path = ASSUMPTION_MODE_CONTRACT_DIR,
) -> list[dict[str, str]]:
    rows = support_rows or tdcsim_assumption_mode_support_ingest_rows(contract_dir)
    source_backed_private = sum(
        1
        for row in rows
        if row.get("source_backed_private_bucket_split_row") == "true"
    )
    bounded_or_context = sum(
        1 for row in rows if row.get("bounded_or_context_support_row") == "true"
    )
    forbidden_enabled = [
        row
        for row in rows
        if row.get("evidence_mode_enabled") == "true"
        or row.get("canonical_ratio_entry") == "true"
        or row.get("current_demand_eligible") == "true"
        or row.get("holder_allocation_enabled") == "true"
    ]
    passed = source_backed_private == 0 and not forbidden_enabled
    return [
        {
            "gate_id": "tdcsim_assumption_mode_support_no_promotion_gate",
            "gate_status": "pass" if passed else "fail",
            "evidence_table": "ratewall_tdcsim_assumption_mode_support_ingest.csv",
            "source_scan_result": (
                f"support_rows={len(rows)};"
                f"bounded_or_context_support_rows={bounded_or_context};"
                f"source_backed_private_bucket_split_rows={source_backed_private};"
                f"forbidden_enabled_rows={len(forbidden_enabled)}"
            ),
            "binding_blocker": (
                "assumption_mode_support_registry_does_not_identify_final_"
                "current_demand_or_private_bucket_funding_routes"
            ),
            "assumption_mode": "true",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "canonical_ratio_entry": "false",
            "current_demand_eligible": "false",
            "holder_allocation_enabled": "false",
            "source_backed_private_bucket_split_rows": str(source_backed_private),
            "bounded_or_context_support_rows": str(bounded_or_context),
            "claim_boundary": CLAIM_BOUNDARY,
            **DISABLED_SWITCHES,
        }
    ]


PRIVATE_ROUTE_ENVELOPE_BOUNDARY = (
    "ratewall_tdcsim_assumption_mode_forecast_private_route_envelope_no_promotion"
)
PRIVATE_ROUTE_ENVELOPE_BLOCKED_USE = (
    "source_backed_private_bucket_split;current_demand_admission;holder_allocation;"
    "canonical_rw_y;Evidence_Mode;denominator_prior_update;prior_narrowing;"
    "formula_replacement;pricing;incidence;welfare;tax;mpc_claims"
)


def _latest_ref_quarter(rows: list[dict[str, str]]) -> str:
    quarters = [row.get("ref_quarter", "") for row in rows if row.get("ref_quarter")]
    return max(quarters, key=_quarter_key) if quarters else ""


def _forecast_private_route_scenario_basis_rows(
    forecast_holder_tdc_consistency_bridge_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in forecast_holder_tdc_consistency_bridge_rows:
        key = (
            row.get("forecast_year", ""),
            row.get("maturity_scenario", ""),
            row.get("holder_scenario", ""),
            row.get("tdcsim_contract_scenario_id", ""),
        )
        grouped.setdefault(key, []).append(row)

    out: list[dict[str, str]] = []
    for key in sorted(grouped):
        rows = grouped[key]
        bases = {
            row.get("tdc_deposit_liquidity_base_ex_interest_bil", "0")
            for row in rows
        }
        representative = rows[0]
        out.append(
            {
                "forecast_year": key[0],
                "maturity_scenario": key[1],
                "holder_scenario": key[2],
                "tdcsim_contract_scenario_id": key[3],
                "scenario_basis_bil": representative.get(
                    "tdc_deposit_liquidity_base_ex_interest_bil", "0"
                ),
                "mpc_invariance_status": (
                    "pass_mpc_invariant_basis"
                    if len(bases) == 1
                    else "fail_mpc_variant_basis"
                ),
            }
        )
    return out


def tdcsim_assumption_mode_forecast_private_route_envelope_rows(
    *,
    forecast_holder_tdc_consistency_bridge_rows: list[dict[str, str]],
    private_route_sensitivity_ingest_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    latest_quarter = _latest_ref_quarter(private_route_sensitivity_ingest_rows)
    route_rows = [
        row
        for row in private_route_sensitivity_ingest_rows
        if row.get("ref_quarter") == latest_quarter
        and row.get("object_family") == "flow_absorption_trailing_4q"
    ]
    basis_rows = _forecast_private_route_scenario_basis_rows(
        forecast_holder_tdc_consistency_bridge_rows
    )
    if not basis_rows or not route_rows:
        return [
            {
                "envelope_row_id": "tdcsim_assumption_mode_forecast_private_route_envelope::fail_closed",
                "forecast_year": "",
                "maturity_scenario": "",
                "holder_scenario": "",
                "tdcsim_contract_scenario_id": "",
                "reference_quarter": latest_quarter,
                "source_sensitivity_row_id": "",
                "scenario_basis_artifact": (
                    "ratewall_forecast_holder_tdc_consistency_bridge.csv"
                ),
                "scenario_basis_field": "tdc_deposit_liquidity_base_ex_interest_bil",
                "scenario_basis_bil": "0",
                "mpc_invariance_status": "fail_missing_forecast_or_route_rows",
                "object_family": "flow_absorption_trailing_4q",
                "route_class": "",
                "route_subclass": "",
                "evidence_tier": "unresolved_residual",
                "measurement_stage": "",
                "mapping_burden": "missing_required_input",
                "assumption_status": "unresolved",
                "share_lambda_0": "0",
                "share_lambda_0_5": "0",
                "share_lambda_1": "0",
                "route_amount_lambda_0_bil": "0",
                "route_amount_lambda_0_5_bil": "0",
                "route_amount_lambda_1_bil": "0",
                "route_amount_bandwidth_bil": "0",
                "source_backed_private_bucket_split_status": (
                    "not_source_backed_private_bucket_split"
                ),
                "source_backed_private_bucket_split_row": "false",
                "current_demand_eligible": "false",
                "holder_allocation_enabled": "false",
                "canonical_tdc_math_change": "false",
                "allowed_use": "fail_closed_missing_forecast_private_route_envelope_input",
                "blocked_use": PRIVATE_ROUTE_ENVELOPE_BLOCKED_USE,
                "exact_blocker": "missing_forecast_basis_or_latest_flow_route_sensitivity_rows",
                "binding_blocker": (
                    "requires_source_backed_split_from_current_private_holder_bucket"
                ),
                "source_artifact": (
                    "ratewall_forecast_holder_tdc_consistency_bridge.csv;"
                    "ratewall_tdcsim_private_route_sensitivity_ingest.csv"
                ),
                "source_status": "missing_required_forecast_private_route_envelope_input",
                "assumption_mode": "true",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "denominator_prior_update_allowed": "false",
                "prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_offset_ratio_changed_this_tranche": "false",
                "split_denominator_promotion_allowed": "false",
                "claim_boundary": PRIVATE_ROUTE_ENVELOPE_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        ]

    out: list[dict[str, str]] = []
    for basis in basis_rows:
        basis_amount = _decimal(basis["scenario_basis_bil"])
        for route in route_rows:
            share_0 = _decimal(route.get("share_lambda_0", "0"))
            share_mid = _decimal(route.get("share_lambda_0_5", "0"))
            share_1 = _decimal(route.get("share_lambda_1", "0"))
            amount_0 = basis_amount * share_0
            amount_mid = basis_amount * share_mid
            amount_1 = basis_amount * share_1
            row_id = (
                "tdcsim_assumption_mode_forecast_private_route_envelope::"
                f"{basis['forecast_year']}::{basis['maturity_scenario']}::"
                f"{basis['holder_scenario']}::{basis['tdcsim_contract_scenario_id']}::"
                f"{route.get('route_class', '')}"
            )
            out.append(
                {
                    "envelope_row_id": row_id,
                    "forecast_year": basis["forecast_year"],
                    "maturity_scenario": basis["maturity_scenario"],
                    "holder_scenario": basis["holder_scenario"],
                    "tdcsim_contract_scenario_id": basis["tdcsim_contract_scenario_id"],
                    "reference_quarter": latest_quarter,
                    "source_sensitivity_row_id": route.get("ingest_row_id", ""),
                    "scenario_basis_artifact": (
                        "ratewall_forecast_holder_tdc_consistency_bridge.csv"
                    ),
                    "scenario_basis_field": (
                        "tdc_deposit_liquidity_base_ex_interest_bil"
                    ),
                    "scenario_basis_bil": _fmt(basis_amount),
                    "mpc_invariance_status": basis["mpc_invariance_status"],
                    "object_family": route.get("object_family", ""),
                    "route_class": route.get("route_class", ""),
                    "route_subclass": route.get("route_subclass", ""),
                    "evidence_tier": route.get("evidence_tier", "bounded_proxy"),
                    "measurement_stage": route.get("measurement_stage", ""),
                    "mapping_burden": route.get(
                        "mapping_burden", "requires_unobserved_actor_split"
                    ),
                    "assumption_status": route.get(
                        "assumption_status", "bounded_assumption"
                    ),
                    "share_lambda_0": route.get("share_lambda_0", "0"),
                    "share_lambda_0_5": route.get("share_lambda_0_5", "0"),
                    "share_lambda_1": route.get("share_lambda_1", "0"),
                    "route_amount_lambda_0_bil": _fmt(amount_0),
                    "route_amount_lambda_0_5_bil": _fmt(amount_mid),
                    "route_amount_lambda_1_bil": _fmt(amount_1),
                    "route_amount_bandwidth_bil": _fmt(amount_1 - amount_0),
                    "source_backed_private_bucket_split_status": route.get(
                        "source_backed_private_bucket_split_status",
                        "not_source_backed_private_bucket_split",
                    ),
                    "source_backed_private_bucket_split_row": "false",
                    "current_demand_eligible": "false",
                    "holder_allocation_enabled": "false",
                    "canonical_tdc_math_change": "false",
                    "allowed_use": "assumption_mode_forecast_private_route_flow_envelope",
                    "blocked_use": PRIVATE_ROUTE_ENVELOPE_BLOCKED_USE,
                    "exact_blocker": route.get(
                        "exact_blocker",
                        "requires_source_backed_split_from_current_private_holder_bucket",
                    ),
                    "binding_blocker": route.get(
                        "binding_blocker",
                        "requires_source_backed_split_from_current_private_holder_bucket",
                    ),
                    "source_artifact": (
                        "ratewall_forecast_holder_tdc_consistency_bridge.csv;"
                        "ratewall_tdcsim_private_route_sensitivity_ingest.csv;"
                        "ratewall_tdcsim_domestic_nonbank_funding_classification.csv"
                    ),
                    "source_status": (
                        "bounded_forecast_private_route_flow_envelope_"
                        "not_source_backed_split"
                    ),
                    "assumption_mode": "true",
                    "enters_main_ratio": "false",
                    "evidence_mode_enabled": "false",
                    "canonical_ratio_entry": "false",
                    "denominator_prior_update_allowed": "false",
                    "prior_narrowing_allowed": "false",
                    "formula_replacement_allowed": "false",
                    "main_offset_ratio_changed_this_tranche": "false",
                    "split_denominator_promotion_allowed": "false",
                    "claim_boundary": PRIVATE_ROUTE_ENVELOPE_BOUNDARY,
                    **DISABLED_SWITCHES,
                }
            )
    return out


def tdcsim_assumption_mode_forecast_private_route_claim_gate_rows(
    *,
    envelope_rows: list[dict[str, str]],
    private_route_sensitivity_ingest_rows: list[dict[str, str]],
    domestic_nonbank_funding_classification_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    latest_quarter = _latest_ref_quarter(private_route_sensitivity_ingest_rows)
    route_rows = [
        row
        for row in private_route_sensitivity_ingest_rows
        if row.get("ref_quarter") == latest_quarter
        and row.get("object_family") == "flow_absorption_trailing_4q"
    ]
    scenario_keys = {
        (
            row.get("forecast_year", ""),
            row.get("maturity_scenario", ""),
            row.get("holder_scenario", ""),
            row.get("tdcsim_contract_scenario_id", ""),
        )
        for row in envelope_rows
        if row.get("forecast_year")
    }
    expected_rows = len(scenario_keys) * len(route_rows)
    source_backed_private = sum(
        row.get("source_backed_private_bucket_split_row") == "true"
        for row in envelope_rows
    )
    current_demand = sum(
        row.get("current_demand_eligible") == "true" for row in envelope_rows
    )
    holder_allocation = sum(
        row.get("holder_allocation_enabled") == "true" for row in envelope_rows
    )
    canonical = sum(row.get("canonical_ratio_entry") == "true" for row in envelope_rows)
    scenario_math_changed = sum(
        row.get("canonical_tdc_math_change") == "true"
        or row.get("main_offset_ratio_changed_this_tranche") == "true"
        for row in envelope_rows
    )
    forbidden_enabled = sum(
        row.get("evidence_mode_enabled") == "true"
        or row.get("canonical_ratio_entry") == "true"
        or row.get("current_demand_eligible") == "true"
        or row.get("holder_allocation_enabled") == "true"
        or row.get("denominator_prior_update_allowed") == "true"
        or row.get("prior_narrowing_allowed") == "true"
        or row.get("formula_replacement_allowed") == "true"
        or row.get("split_denominator_promotion_allowed") == "true"
        or any(row.get(field) == "true" for field in DISABLED_SWITCHES)
        for row in envelope_rows
    )
    mpc_failures = sum(
        row.get("mpc_invariance_status") != "pass_mpc_invariant_basis"
        for row in envelope_rows
    )
    central_sum_failures = 0
    tolerance = Decimal("0.01")
    for key in scenario_keys:
        scenario_rows = [
            row
            for row in envelope_rows
            if (
                row.get("forecast_year", ""),
                row.get("maturity_scenario", ""),
                row.get("holder_scenario", ""),
                row.get("tdcsim_contract_scenario_id", ""),
            )
            == key
        ]
        basis = _decimal(scenario_rows[0].get("scenario_basis_bil", "0"))
        central_sum = sum(
            _decimal(row.get("route_amount_lambda_0_5_bil", "0"))
            for row in scenario_rows
        )
        if abs(central_sum - basis) > tolerance:
            central_sum_failures += 1
    central_amounts_by_year_route: dict[tuple[str, str], set[str]] = {}
    for row in envelope_rows:
        central_amounts_by_year_route.setdefault(
            (row.get("forecast_year", ""), row.get("route_class", "")), set()
        ).add(row.get("route_amount_lambda_0_5_bil", "0"))
    scenario_variation_pass = any(
        len(amounts) > 1 for amounts in central_amounts_by_year_route.values()
    )
    passed = (
        bool(envelope_rows)
        and len(envelope_rows) == expected_rows
        and source_backed_private == 0
        and current_demand == 0
        and holder_allocation == 0
        and canonical == 0
        and scenario_math_changed == 0
        and forbidden_enabled == 0
        and mpc_failures == 0
        and central_sum_failures == 0
        and scenario_variation_pass
    )
    return [
        {
            "gate_id": "tdcsim_assumption_mode_forecast_private_route_envelope_no_promotion_gate",
            "gate_status": "pass" if passed else "fail",
            "envelope_table": (
                "ratewall_tdcsim_assumption_mode_forecast_private_route_envelope.csv"
            ),
            "underlying_sensitivity_table": (
                "ratewall_tdcsim_private_route_sensitivity_ingest.csv"
            ),
            "funding_classification_table": (
                "ratewall_tdcsim_domestic_nonbank_funding_classification.csv"
            ),
            "scenario_rows": str(len(scenario_keys)),
            "route_class_rows": str(len(route_rows)),
            "envelope_rows": str(len(envelope_rows)),
            "expected_envelope_rows": str(expected_rows),
            "reference_quarter": latest_quarter,
            "object_family": "flow_absorption_trailing_4q",
            "mpc_invariance_failures": str(mpc_failures),
            "central_share_sum_failure_rows": str(central_sum_failures),
            "scenario_variation_status": (
                "pass_distinct_within_year_route_amounts"
                if scenario_variation_pass
                else "fail_no_distinct_within_year_route_amounts"
            ),
            "source_backed_private_bucket_split_rows": str(source_backed_private),
            "current_demand_eligible_rows": str(current_demand),
            "holder_allocation_enabled_rows": str(holder_allocation),
            "canonical_ratio_entry_rows": str(canonical),
            "scenario_math_changed_rows": str(scenario_math_changed),
            "forbidden_enabled_rows": str(forbidden_enabled),
            "binding_blocker": (
                "requires_source_backed_split_from_current_private_holder_bucket;"
                f"funding_classification_rows={len(domestic_nonbank_funding_classification_rows)}"
            ),
            "allowed_use": "assumption_mode_forecast_private_route_flow_envelope_gate",
            "blocked_use": PRIVATE_ROUTE_ENVELOPE_BLOCKED_USE,
            "claim_boundary": PRIVATE_ROUTE_ENVELOPE_BOUNDARY,
            "source_status": (
                "bounded_forecast_private_route_flow_envelope_checked_no_promotion"
            ),
            "assumption_mode": "true",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "canonical_ratio_entry": "false",
            "current_demand_eligible": "false",
            "denominator_prior_update_allowed": "false",
            "prior_narrowing_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_offset_ratio_changed_this_tranche": "false",
            "split_denominator_promotion_allowed": "false",
            **DISABLED_SWITCHES,
        }
    ]


def tdc_forward_scenario_decomposition_rows(
    bridge_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    rows = bridge_rows if bridge_rows is not None else tdcsim_projection_contract_bridge_rows()
    specs = [
        (
            "primary_fiscal_flow_to_du",
            "tdc_fiscal_flow_bil",
            "true",
            "false",
        ),
        (
            "principal_to_du",
            "tdc_debt_service_principal_to_du_bil",
            "true",
            "false",
        ),
        (
            "interest_to_du_direct_overlap",
            "tdc_debt_service_interest_to_du_bil",
            "false",
            "true",
        ),
        (
            "auction_absorption_by_du",
            "tdc_auction_absorption_du_bil",
            "true",
            "false",
        ),
        (
            "secondary_trades_net",
            "tdc_secondary_trades_bil",
            "true",
            "false",
        ),
        (
            "other_explicit_or_zero",
            "tdc_other_bil",
            "true",
            "false",
        ),
    ]
    out: list[dict[str, str]] = []
    for row in rows:
        if row.get("contract_ingest_status") != "pass":
            continue
        for component, field, included, overlap in specs:
            out.append(
                {
                    "scenario_id": row.get("scenario_id", ""),
                    "quarter": row.get("quarter", ""),
                    "decomposition_component": component,
                    "component_amount_bil": _fmt(_decimal(row.get(field, "0"))),
                    "included_in_tdc_ex_direct_interest_base": included,
                    "direct_interest_overlap_component": overlap,
                    "canonical_tdc_accounting_path_id": (
                        f"forward_tdcsim_{row.get('scenario_id', '')}"
                    ),
                    "source_table": "ratewall_tdcsim_projection_contract_bridge.csv",
                    "contract_ingest_status": row.get("contract_ingest_status", ""),
                    "assumption_mode": "true",
                    "enters_main_ratio": "false",
                    "evidence_mode_enabled": "false",
                    "canonical_ratio_entry": "false",
                    "claim_boundary": (
                        "tdc_forward_decomposition_chart_support_not_main_ratio"
                    ),
                    **DISABLED_SWITCHES,
                }
            )
    return out


def _forward_canonical_accounting_row(row: dict[str, str]) -> dict[str, str]:
    tdc_change = _decimal(row.get("tdc_change_bil"))
    primary = _decimal(row.get("tdc_fiscal_flow_bil"))
    interest = _decimal(row.get("tdc_debt_service_interest_to_du_bil"))
    principal = _decimal(row.get("tdc_debt_service_principal_to_du_bil"))
    auction = _decimal(row.get("tdc_auction_absorption_du_bil"))
    secondary_net = _decimal(row.get("tdc_secondary_trades_bil"))
    other = _decimal(row.get("tdc_other_bil"))
    component_sum = primary + interest + principal + auction + secondary_net + other
    component_error = component_sum - tdc_change
    overlap = _decimal(row.get("overlap_cashflow_bil"))
    ex_overlap = tdc_change - overlap
    contract_ex_overlap = _decimal(row.get("tdc_change_ex_overlap_bil"))
    source_status = (
        "canonical_tdc_accounting_forward_projection_from_validated_tdcsim_contract;"
        f"primary_flow_status={row.get('primary_flow_status', '')}"
    )
    return {
        "tdc_path_id": f"forward_tdcsim_{row.get('scenario_id', '')}",
        "quarter": row.get("quarter", ""),
        "path_type": "forward_projection",
        "source_project": "tdcsim",
        "source_artifact": "ratewall_tdcsim_projection_contract_bridge.csv",
        "source_contract_version": row.get("tdcsim_contract_version", ""),
        "tdc_change_bil": _fmt(tdc_change),
        "primary_fiscal_flow_to_du_bil": _fmt(primary),
        "interest_to_du_bil": _fmt(interest),
        "principal_to_du_bil": _fmt(principal),
        "auction_absorption_by_du_bil": _fmt(auction),
        "secondary_du_to_ru_bil": "0",
        "secondary_ru_to_du_bil": "0",
        "secondary_trades_net_bil": _fmt(secondary_net),
        "other_bil": _fmt(other),
        "component_sum_bil": _fmt(component_sum),
        "component_sum_error_bil": _fmt(component_error),
        "direct_interest_overlap_cashflow_bil": _fmt(overlap),
        "tdc_change_ex_direct_interest_overlap_bil": _fmt(ex_overlap),
        "secondary_trade_status": row.get("secondary_trade_status", ""),
        "other_status": row.get("other_status", ""),
        "source_status": source_status,
        "component_identity_status": "pass"
        if abs(component_error) <= Decimal("1e-7")
        else "fail",
        "overlap_guardrail_status": "pass"
        if abs(ex_overlap - contract_ex_overlap) <= Decimal("1e-7")
        else "fail",
        "principal_overlap_subtracted": "false",
        "canonical_tdc_accounting_entry": "true",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "canonical_ratio_entry": "false",
        "claim_boundary": (
            "canonical_tdc_accounting_path_not_demand_conversion_or_wall_ratio"
        ),
        **DISABLED_SWITCHES,
    }


def _historical_canonical_accounting_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "tdc_path_id": f"historical_tdcest_{row.get('source_series_key', '')}",
        "quarter": row.get("quarter", ""),
        "path_type": "historical",
        "source_project": "tdcest",
        "source_artifact": str(TDCEST_ESTIMATES_PATH),
        "source_contract_version": "",
        "tdc_change_bil": row.get("tdc_change_bil", ""),
        "primary_fiscal_flow_to_du_bil": "",
        "interest_to_du_bil": "",
        "principal_to_du_bil": "",
        "auction_absorption_by_du_bil": "",
        "secondary_du_to_ru_bil": "",
        "secondary_ru_to_du_bil": "",
        "secondary_trades_net_bil": "",
        "other_bil": "",
        "component_sum_bil": "",
        "component_sum_error_bil": "",
        "direct_interest_overlap_cashflow_bil": "",
        "tdc_change_ex_direct_interest_overlap_bil": "",
        "secondary_trade_status": "not_applicable_historical_flow_only",
        "other_status": "not_applicable_historical_flow_only",
        "source_status": (
            "canonical_tdc_accounting_historical_flow_from_tdcest_selected_series;"
            "component_detail_unavailable_not_imputed"
        ),
        "component_identity_status": "not_applicable_historical_flow_only",
        "overlap_guardrail_status": "not_applicable_historical_flow_only",
        "principal_overlap_subtracted": "false",
        "canonical_tdc_accounting_entry": "true",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "canonical_ratio_entry": "false",
        "claim_boundary": (
            "canonical_tdc_accounting_path_not_demand_conversion_or_wall_ratio"
        ),
        **DISABLED_SWITCHES,
    }


def canonical_tdc_accounting_path_rows(
    *,
    selected_rows: list[dict[str, str]] | None = None,
    contract_dir: Path = CONTRACT_DIR,
) -> list[dict[str, str]]:
    historical = [
        _historical_canonical_accounting_row(row)
        for row in _historical_tdc_flow_rows(selected_rows)
    ]
    forward = [
        _forward_canonical_accounting_row(row)
        for row in tdcsim_projection_contract_bridge_rows(contract_dir)
        if row.get("contract_ingest_status") == "pass"
    ]
    return historical + forward


def canonical_tdc_stitched_accounting_path_rows(
    *,
    selected_rows: list[dict[str, str]] | None = None,
    contract_dir: Path = CONTRACT_DIR,
    forward_scenario_id: str = "current_mix_baseline",
) -> list[dict[str, str]]:
    historical = [
        _historical_canonical_accounting_row(row)
        for row in _historical_tdc_flow_rows(selected_rows)
    ]
    handoff_quarter = max((row["quarter"] for row in historical), default="")
    rows: list[dict[str, str]] = []
    for row in historical:
        stitched = {
            "tdc_path_id": "canonical_tdc_stitched_accounting_path",
            "path_segment": "historical_tdcest",
            "handoff_quarter": handoff_quarter,
            "source_series_key": _selected_series_key(selected_rows),
            "component_detail_status": (
                "historical_selected_series_component_detail_unavailable"
            ),
            **row,
        }
        stitched["tdc_path_id"] = "canonical_tdc_stitched_accounting_path"
        rows.append(stitched)
    for row in tdcsim_projection_contract_bridge_rows(contract_dir):
        if row.get("scenario_id") != forward_scenario_id:
            continue
        canonical = _forward_canonical_accounting_row(row)
        if handoff_quarter and canonical["quarter"] <= handoff_quarter:
            continue
        stitched = {
            "tdc_path_id": "canonical_tdc_stitched_accounting_path",
            "path_segment": "forward_tdcsim",
            "handoff_quarter": handoff_quarter,
            "source_series_key": forward_scenario_id,
            "component_detail_status": "forward_tdcsim_full_component_detail",
            **canonical,
        }
        stitched["tdc_path_id"] = "canonical_tdc_stitched_accounting_path"
        rows.append(stitched)
    return rows


def canonical_tdc_accounting_source_hierarchy_audit_rows(
    *,
    accounting_rows: list[dict[str, str]],
    stitched_rows: list[dict[str, str]],
    contract_dir: Path = CONTRACT_DIR,
) -> list[dict[str, str]]:
    registry = _read_csv(contract_dir / "tdcsim_ratewall_source_registry.csv")
    source_families = {row.get("source_family", "") for row in registry}
    input_sources = _manifest(contract_dir).get("source_hierarchy", {})
    checks = [
        (
            "tdcest_historical_authority",
            any(row.get("path_type") == "historical" for row in accounting_rows),
            "tdcest",
            str(TDCEST_ESTIMATES_PATH),
            "historical rows come from the selected tdcest series",
            "historical TDC accounting path is missing or not sourced to tdcest",
        ),
        (
            "tdcsim_forward_mechanics_authority",
            any(row.get("path_type") == "forward_projection" for row in accounting_rows),
            "tdcsim",
            "data/raw/ratewall_sibling_calibration/tdcsim",
            "forward rows come from the validated vendored tdcsim contract",
            "forward TDC accounting path is missing or not sourced to tdcsim",
        ),
        (
            "tdcmix_prior_not_holder_allocation_evidence",
            "tdcmix" in source_families,
            "tdcmix",
            "tdcsim_ratewall_source_registry.csv",
            "tdcmix appears only as holder scenario prior/regularization",
            "tdcmix priors were absent or could be mistaken for holder evidence",
        ),
        (
            "weak_wamest_rows_sensitivity_only",
            any(
                row.get("source_family") == "wamest"
                and row.get("central_default_eligible") == "false"
                and row.get("sensitivity_only") == "true"
                for row in registry
            ),
            "wamest",
            "tdcsim_ratewall_source_registry.csv",
            "weak WAMEST rows are blocked from central defaults",
            "weak WAMEST maturity/WAM rows may have fed central defaults",
        ),
        (
            "source_backed_inputs_recorded",
            {"bond_history", "primary_flow", "yield_curve"} <= set(input_sources),
            "FiscalData/Treasury/CBO/tdcsim",
            "tdcsim_ratewall_manifest.json",
            "FiscalData MSPD, Treasury/CBO curve inputs, and CBO primary-flow proxy are recorded",
            "source-backed TDCSim inputs are missing from the manifest",
        ),
        (
            "historical_component_detail_explicitly_unavailable",
            any(
                row.get("component_detail_status")
                == "historical_selected_series_component_detail_unavailable"
                for row in stitched_rows
            ),
            "tdcest",
            "ratewall_canonical_tdc_stitched_accounting_path.csv",
            "historical selected-series rows are not imputed into fake component detail",
            "historical missing component detail was not explicitly labeled unavailable",
        ),
        (
            "no_total_deposit_growth_shortcut_or_arbitrary_beta",
            all("deposit_growth" not in row.get("source_status", "") for row in accounting_rows)
            and all("holder_beta" not in row.get("source_status", "") for row in accounting_rows),
            "ratewall",
            "ratewall_canonical_tdc_accounting_path.csv",
            "canonical accounting path uses TDC contract rows, not total deposits or arbitrary holder betas",
            "canonical TDC accounting path used a shortcut deposit-growth or holder-beta proxy",
        ),
        (
            "no_residual_gap_stacked_as_live_drag",
            {row.get("enters_main_ratio") for row in accounting_rows} <= {"false"},
            "ratewall",
            "ratewall_canonical_tdc_accounting_path.csv",
            "canonical accounting entries do not enter the main ratio or stack residual drag",
            "TDC accounting rows entered the main ratio or stacked residual drag",
        ),
        (
            "direct_interest_overlap_not_double_counted",
            all(
                row.get("overlap_guardrail_status")
                in {"pass", "not_applicable_historical_flow_only"}
                and row.get("principal_overlap_subtracted") == "false"
                for row in accounting_rows
            ),
            "ratewall",
            "ratewall_canonical_tdc_accounting_path.csv",
            "direct domestic-nonbank Treasury interest is separated from TDC ex-overlap support",
            "direct interest overlap failed or principal was subtracted as interest overlap",
        ),
    ]
    return [
        {
            "audit_item": item,
            "audit_status": "pass" if passed else "fail",
            "source_family": source_family,
            "source_artifact": source_artifact,
            "evidence_summary": evidence,
            "failure_mode_if_false": failure,
            "canonical_accounting_status": "canonical_tdc_accounting_entry_only",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "canonical_ratio_entry": "false",
            "claim_boundary": (
                "canonical_tdc_accounting_source_hierarchy_not_demand_or_holder_claim"
            ),
            **DISABLED_SWITCHES,
        }
        for item, passed, source_family, source_artifact, evidence, failure in checks
    ]


def tdc_forward_component_audit_rows(
    contract_dir: Path = CONTRACT_DIR,
) -> list[dict[str, str]]:
    status = _contract_status(contract_dir)
    components = _read_csv(contract_dir / "tdcsim_ratewall_quarterly_components.csv")
    if not components:
        return []
    out = []
    for row in components:
        dual = (
            row.get("enters_direct_interest_support") == "true"
            and row.get("enters_tdc_deposit_support_default") == "true"
        )
        out.append(
            {
                "scenario_id": row.get("scenario_id", ""),
                "quarter": row.get("quarter", ""),
                "component_key": row.get("component_key", ""),
                "holder_bucket": row.get("holder_bucket", ""),
                "ratewall_perimeter": row.get("ratewall_perimeter", ""),
                "security_type": row.get("security_type", ""),
                "cash_component_key": row.get("cash_component_key", ""),
                "amount_bil": row.get("amount_bil", "0"),
                "enters_direct_interest_support": row.get("enters_direct_interest_support", "false"),
                "enters_tdc_deposit_support_default": row.get("enters_tdc_deposit_support_default", "false"),
                "component_dual_entry_status": "fail_dual_entry" if dual else "pass_mutually_exclusive",
                "source_family": row.get("source_family", ""),
                "observability_tier": row.get("observability_tier", ""),
                "assumption_status": row.get("assumption_status", ""),
                "contract_ingest_status": status["status"],
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        )
    return out


def tdc_forward_overlap_guardrail_rows(
    contract_dir: Path = CONTRACT_DIR,
) -> list[dict[str, str]]:
    status = _contract_status(contract_dir)
    summary = _read_csv(contract_dir / "tdcsim_ratewall_quarterly_summary.csv")
    out = []
    for row in summary:
        tdc_change = _decimal(row.get("tdc_change_bil"))
        overlap = _decimal(row.get("overlap_cashflow_bil"))
        ex_overlap = _decimal(row.get("tdc_change_ex_overlap_bil"))
        recomputed = tdc_change - overlap
        error = recomputed - ex_overlap
        out.append(
            {
                "scenario_id": row.get("scenario_id", ""),
                "quarter": row.get("quarter", ""),
                "tdc_change_bil": _fmt(tdc_change),
                "direct_interest_overlap_cashflow_bil": _fmt(overlap),
                "tdc_change_ex_overlap_bil": _fmt(ex_overlap),
                "recomputed_tdc_change_ex_overlap_bil": _fmt(recomputed),
                "overlap_identity_error_bil": _fmt(error),
                "overlap_subtracted_before_demand_conversion": "true",
                "principal_overlap_subtracted": "false",
                "guardrail_status": "pass" if abs(error) <= Decimal("1e-7") else "fail",
                "contract_ingest_status": status["status"],
                "claim_boundary": CLAIM_BOUNDARY,
                **DISABLED_SWITCHES,
            }
        )
    return out


def tdc_forward_invariant_audit_rows(
    *,
    projection_rows: list[dict[str, str]],
    component_rows: list[dict[str, str]],
    overlap_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    projection_pass = bool(projection_rows) and all(
        row.get("enters_main_ratio") == "false"
        and row.get("evidence_mode_enabled") == "false"
        and row.get("canonical_ratio_entry") == "false"
        for row in projection_rows
    )
    component_pass = bool(component_rows) and all(
        row.get("component_dual_entry_status") == "pass_mutually_exclusive"
        and row.get("enters_main_ratio") == "false"
        and row.get("evidence_mode_enabled") == "false"
        for row in component_rows
    )
    overlap_pass = bool(overlap_rows) and all(
        row.get("guardrail_status") == "pass"
        and row.get("principal_overlap_subtracted") == "false"
        for row in overlap_rows
    )
    remittance_rows = [
        row
        for row in component_rows
        if row.get("component_key") == "central_bank_remittance_to_tga"
    ]
    remittance_xor_pass = bool(remittance_rows) and all(
        row.get("cash_component_key") == "central_bank_remittance_to_tga"
        and row.get("holder_bucket") == "CB"
        and row.get("enters_direct_interest_support") == "false"
        and row.get("enters_tdc_deposit_support_default") == "false"
        and row.get("component_dual_entry_status") == "pass_mutually_exclusive"
        for row in remittance_rows
    )
    checks = [
        (
            "tdcsim_forward_projection_surface_noncanonical",
            projection_pass,
            "ratewall_tdc_forward_projection_surface.csv",
            "tdcsim projection rows entered main ratio, Evidence Mode, or canonical status",
        ),
        (
            "tdcsim_forward_components_mutually_exclusive",
            component_pass,
            "ratewall_tdc_forward_component_audit.csv",
            "a component entered both direct interest support and TDC deposit support",
        ),
        (
            "tdcsim_forward_interest_overlap_subtracted_once",
            overlap_pass,
            "ratewall_tdc_forward_overlap_guardrail.csv",
            "direct-interest overlap was not subtracted exactly once before conversion",
        ),
        (
            "tdcsim_forward_remittance_static_xor_proven",
            remittance_xor_pass,
            "ratewall_tdc_forward_component_audit.csv",
            "central-bank remittance was missing or entered a TDC/direct-interest support channel",
        ),
    ]
    return [
        {
            "audit_item": item,
            "audit_status": "pass" if passed else "fail",
            "evidence_table": evidence,
            "failure_mode_if_false": failure,
            "contract_ingest_status": projection_rows[0].get("contract_ingest_status", "")
            if projection_rows
            else "missing_projection_rows",
            "prior_narrowing_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_offset_ratio_changed_this_tranche": "false",
            "dynamic_equation_changed_this_tranche": "false",
            "split_denominator_promotion_allowed": "false",
            "forbidden_switches_remain_disabled": "true",
            "claim_boundary": "tdc_forward_invariant_audit_not_evidence_promotion",
        }
        for item, passed, evidence, failure in checks
    ]
