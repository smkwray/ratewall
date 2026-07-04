"""Source/method authority matrix for RateWall model surfaces."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_CBO_REVENUE_PATH = Path("data/raw/cbo/51138-2026-02-Revenue-annual_fy.csv")

SOURCE_METHOD_MATRIX_FIELDS = [
    "source_method_matrix_row_id",
    "block_id",
    "surface_id",
    "object_role",
    "presentation_layer",
    "claim_status_plain_english",
    "centrality",
    "source_object",
    "source_artifact_or_candidate",
    "method_formula",
    "translation_family",
    "denominator_object",
    "evidence_status",
    "known_gap",
    "admission_or_parking_rule",
    "proof_artifact",
    "central_n_delta_bil_allowed",
    "local_source_status",
    "source_coverage_flag",
    "overlap_guard_id",
    "compatibility_alias",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

SOURCE_METHOD_SUMMARY_FIELDS = [
    "source_method_summary_row_id",
    "summary_scope",
    "metric_id",
    "metric_value",
    "interpretation",
    "allowed_use",
    "blocked_use",
]

ALLOWED_OBJECT_ROLES = {
    "selected_n",
    "selected_block_input",
    "selected_benchmark_recast",
    "candidate_replacement",
    "diagnostic_context",
    "sensitivity_only",
    "blocked_source_or_method",
    "denominator_only",
    "not_applicable",
}


class SourceMethodMatrixError(ValueError):
    """Raised when source/method rows are inconsistent."""


def source_method_matrix_rows(
    *,
    cbo_revenue_path: str | Path = DEFAULT_CBO_REVENUE_PATH,
) -> list[dict[str, str]]:
    """Return the builder-readable source/method authority rows."""

    cbo_revenue_status = (
        "present_local" if Path(cbo_revenue_path).exists() else "source_to_acquire"
    )
    rows = [
        _row(
            "forecast_tdc_support",
            "forecast_central_tdcsim_cbo",
            "headline_model",
            "Forecast Treasury deposit creation support is central.",
            "central",
            "tdcsim_cbo_forecast_suite",
            "var/tdcsim_cbo_suite_20260627_tdcsim72dc6c7_full10y_core/ratewall_model_artifact_manifest.json;var/preliminary_scenario_results/core_support_parity/ratewall_tdc_ex_overlap_support_shared.csv",
            "tdc_current_demand_support_bil = tdc_change_ex_overlap_bil * beta * chi",
            "spendable_liquidity_inflow",
            "forecast_selected_D",
            "source_backed_forecast_method_assumption_mode_beta_chi",
            "direct_beta_chi_floor_not_admitted",
            "central_in_forecast_only_ex_overlap_basis_required",
            "ratewall_tdc_ex_overlap_support_shared.csv",
            "true",
            "present_local",
            "fy2027_fy2036_forecast_suite",
            "tdc_ex_overlap_only",
            "forecast_tdc_support",
        ),
        _row(
            "current_tdc_decomposition",
            "current_assumption_runtime",
            "audit_ledger",
            "Current TDC is decomposition/context, not the current selected numerator.",
            "context",
            "sibling_tdc_calibration",
            "data/raw/ratewall_sibling_calibration/tdcest_tdc_estimates.csv;data/raw/ratewall_sibling_calibration/tdcpass_quarterly_panel.csv",
            "decomposition_only_no_selected_current_N_formula",
            "not_a_current_demand_support_formula",
            "current_fixed_D_if_context_ratio",
            "source_backed_decomposition_not_central",
            "exact_current_ex_overlap_support_gate_not_admitted",
            "support_sensitivity_only_after_beta_chi_ex_overlap_demand_overlap_gates",
            "source_method_matrix_row",
            "false",
            "present_local",
            "historical_current_quarterly_context",
            "tdc_not_deposit_income_substitute",
            "current_tdc_decomposition",
        ),
        _row(
            "historical_tdc_decomposition",
            "historical_path_context",
            "audit_ledger",
            "Historical TDC is decomposition/backtest unless full support gates pass.",
            "context",
            "historical_tdc_context_adapter",
            "var/preliminary_scenario_results/historical_comparable_adapter/ratewall_historical_comparable_surface.csv",
            "historical_noncanonical_tdc_context_bil = legacy_tdc_current_demand_support_bil",
            "not_a_final_classifier_formula",
            "historical_provisional_D_if_available",
            "source_backed_context_nonclassifier",
            "historical_ex_overlap_beta_chi_demand_translation_not_admitted",
            "decomposition_backtest;support_sensitivity_only_after_all_gates",
            "ratewall_historical_channel_adapter_status.csv",
            "false",
            "present_local",
            "partial_historical_component_context",
            "historical_ratio_not_classifier",
            "historical_noncanonical_tdc_context_bil",
        ),
        _row(
            "beta_chi_calibration",
            "forecast_central_tdcsim_cbo",
            "audit_ledger",
            "Beta and chi are transparent Assumption-Mode forecast conversion values.",
            "cross_cutting_assumption",
            "ea_tdc_beta_chi_context",
            "var/preliminary_scenario_results/beta_chi_calibration_readout/",
            "beta_times_chi = 0.34201759129420367 * 0.07",
            "spendable_liquidity_inflow",
            "inherits_surface_D",
            "assumption_mode_no_direct_floor_admitted",
            "exact_matched_current_demand_panel_absent",
            "do_not_change_without_separately_admitted_evidence",
            "ratewall_beta_chi_calibration_summary.csv",
            "false",
            "present_local",
            "forecast_conversion_assumption",
            "beta_chi_not_mmf_route",
            "forecast_beta_chi_assumption",
        ),
        _row(
            "forecast_public_interest_net_block",
            "forecast_central_tdcsim_cbo",
            "headline_model",
            "Forecast public-interest cashflows are a central net block.",
            "central",
            "tdcsim_cbo_public_interest_block",
            "var/preliminary_scenario_results/forecast_10y/ratewall_forecast_public_interest_net_block.csv;var/preliminary_scenario_results/core_support_parity/ratewall_public_interest_net_block_shared.csv",
            "net_interest_after_fiscal_tga_offsets_bil = gross_public_interest_support - tax_timing - fiscal_offset - tga_offset",
            "direct_private_cash_income;intermediated_financial_income",
            "forecast_selected_D",
            "source_backed_forecast_block_with_assumption_absorbers",
            "cbo_remittance_baseline_workbook_missing_until_acquired",
            "central_forecast_block;direct_bank_inputs_not_additive",
            "ratewall_public_interest_net_block_shared.csv",
            "true",
            "present_local",
            "fy2027_fy2036_forecast",
            "public_interest_block_xor",
            "public_interest_net_block",
        ),
        _row(
            "forecast_fed_liability_sources",
            "forecast_central_tdcsim_cbo",
            "audit_ledger",
            "Fed liability inputs support IORB/ON RRP state and rate assumptions.",
            "block_input",
            "fred_fed_liability_cache",
            "var/preliminary_scenario_results/forecast_10y/ratewall_forecast_fed_liability_sources.csv",
            "latest_stock_gdp_share_and_rate_spread_held_constant",
            "intermediated_financial_income;market_safe_yield_income",
            "forecast_selected_D",
            "source_backed_latest_state_inputs",
            "annual_remittance_projection_not_present",
            "input_to_public_interest_block_not_standalone",
            "ratewall_forecast_fed_liability_sources.csv",
            "false",
            "present_local",
            "latest_state_inputs_held_constant",
            "fed_liability_input_not_standalone_N",
            "forecast_fed_liability_inputs",
        ),
        _row(
            "forecast_remittance_baseline_path",
            "forecast_central_tdcsim_cbo",
            "audit_ledger",
            "CBO remittance baseline is context; scenario delta remains zero.",
            "baseline_context",
            "cbo_revenue_projection_federal_reserve_remittances",
            "data/raw/cbo/51138-2026-02-Revenue-annual_fy.csv;data/raw/cbo/51138-2026-02-Revenue-schema.json",
            "extract_rev_fed_reserve_by_fiscal_year_for_budget_context;central_n_delta_bil=0",
            "not_private_demand_support_without_scenario_model",
            "forecast_selected_D_if_future_scenario_delta_admitted",
            "source_present_context_only_if_local_csv_available",
            "scenario_remittance_delta_model_not_admitted",
            "do_not_convert_baseline_remittances_to_private_demand_support",
            "ratewall_forecast_remittance_baseline_path.csv",
            "false",
            cbo_revenue_status,
            "fy2027_fy2036_baseline_context",
            "remittance_state_not_private_income",
            "forecast_remittance_baseline_context",
        ),
        _row(
            "current_public_interest_runtime",
            "current_assumption_runtime",
            "headline_model",
            "Current/static benchmark is the existing assumption runtime recast unchanged.",
            "benchmark_central",
            "ratewall_assumption_engine",
            "configs/ratewall_assumption_sets.yml;configs/ratewall_parameter_packs.yml;src/ratewall/accounting/assumption_engine.py",
            "existing_runtime_public_cashflow_support_minus_absorbers",
            "assumption_mode_current_runtime",
            "current_fixed_D",
            "assumption_runtime_existing_method",
            "observed_source_replacement_not_built_yet",
            "reproduce_unchanged_before_overlay_replacement",
            "current benchmark snapshot",
            "true",
            "present_local",
            "current_runtime",
            "current_benchmark_no_silent_replacement",
            "current_assumption_benchmark",
        ),
        _row(
            "historical_public_interest_net_block",
            "historical_path_context",
            "headline_model",
            "Historical public-interest block is a provisional nonfinal estimate.",
            "provisional_required",
            "historical_public_finance_sources",
            "var/preliminary_scenario_results/historical_provisional_estimate/ratewall_historical_public_interest_net_block.csv;var/preliminary_scenario_results/historical_provisional_estimate/ratewall_historical_provisional_classifier_gate.csv",
            "observed_period_public_interest_cashflows_net_of_leakages_absorbers",
            "direct_private_cash_income;intermediated_financial_income",
            "historical_provisional_D",
            "source_backed_historical_public_interest_net_block_with_h41_remittance_guard",
            "none_R37_context_nonclassifier_decision",
            "use_R37_historical_context_nonclassifier;do_not_promote",
            "ratewall_historical_public_interest_net_block.csv",
            "false",
            "present_local_context",
            "historical_public_interest_h41_guard_context_closed",
            "historical_public_interest_subchannel_guard",
            "historical_public_interest_net_block",
        ),
        _row(
            "realized_safe_yield_income",
            "current_and_historical_overlay",
            "research_appendix",
            "Full realized safe-yield composite is not headline; deposit payer-flow is a candidate.",
            "diagnostic_candidate",
            "realized_deposit_mmf_tbill_income_sources",
            "ffiec_fdic_call_report_deposit_interest_expense;ncua_share_deposit_interest;ofr_mmf;sec_nmfp;ici_mmf;bea_personal_interest_income",
            "period_cashflow_to_eligible_recipient_basis_then_demand_conversion",
            "realized_household_safe_yield_income",
            "current_fixed_D_or_historical_provisional_D",
            "diagnostic_source_ledger_required",
            "recipient_allocation_and_overlap_proof_missing",
            "full_composite_not_headline_deposit_candidate_build_now",
            "future realized safe-yield decision/source inventory",
            "false",
            "source_to_acquire",
            "candidate_source_inventory_required",
            "bank_first_vs_recipient_flow_xor",
            "realized_safe_yield_income",
        ),
        _row(
            "safe_asset_allocation_offset_drag",
            "forecast_sensitivity_tdcsim_cbo",
            "research_appendix",
            "Safe-asset allocation drag is sidecar/diagnostic unless a disjoint basis exists.",
            "sidecar",
            "residual_safe_asset_gate",
            "var/preliminary_scenario_results/residual_channel_closure/ratewall_residual_safe_asset_drag_admission_gate.csv",
            "central_n_delta_bil=0_until_disjoint_residual_cashflow_basis",
            "market_safe_yield_income",
            "surface_specific_D_context",
            "rejected_without_disjoint_basis",
            "overlaps_public_interest_tdc_realized_safe_yield_or_moving_D",
            "keep_noncentral_until_admission_gate_passes",
            "ratewall_residual_safe_asset_drag_admission_gate.csv",
            "false",
            "present_local",
            "forecast_residual_gate",
            "safe_asset_drag_nonoverlap_required",
            "safe_asset_allocation_drag_sidecar",
        ),
        _row(
            "firm_cash_attenuation",
            "forecast_sensitivity_tdcsim_cbo",
            "audit_ledger",
            "Firm cash is current recast/forecast sensitivity, not forecast central.",
            "sensitivity",
            "firm_liquid_asset_stock_context",
            "var/preliminary_scenario_results/residual_channel_closure/ratewall_residual_channel_admission_matrix.csv",
            "firm_cash_rate_path_yield_basis_bil * firm_cash_attenuation_share",
            "firm_liquidity_cushion",
            "surface_specific_D_context",
            "source_backed_stock_context_assumption_conversion",
            "conversion_not_final_central_forecast",
            "keep_sensitivity;do_not_stack_with_firm_cushion",
            "ratewall_residual_channel_admission_matrix.csv",
            "false",
            "present_local",
            "forecast_sensitivity",
            "firm_liquid_asset_basis_xor",
            "firm_cash_attenuation",
        ),
        _row(
            "firm_liquid_asset_cushion",
            "forecast_sensitivity_tdcsim_cbo",
            "research_appendix",
            "Firm liquid-asset cushion is replacement-only.",
            "replacement_candidate",
            "firm_liquid_asset_stock_context",
            "var/preliminary_scenario_results/residual_channel_closure/ratewall_firm_liquidity_replacement_decision.csv",
            "replacement_candidate_only_not_additive",
            "firm_liquidity_cushion",
            "surface_specific_D_context",
            "replacement_candidate_not_active",
            "cannot_stack_with_firm_cash",
            "may_replace_firm_cash_only_after_demotion_rule",
            "ratewall_firm_liquidity_replacement_decision.csv",
            "false",
            "present_local",
            "replacement_candidate",
            "firm_liquid_asset_basis_xor",
            "firm_liquid_asset_cushion",
        ),
        _row(
            "firm_rollover_pressure_drag",
            "research_appendix",
            "research_appendix",
            "Firm rollover belongs in denominator/credit sidecar, not numerator central.",
            "parked",
            "firm_credit_sidecar_candidate",
            "configs/ratewall_parameter_packs.yml",
            "no_current_numerator_formula_admitted",
            "wealth_revaluation",
            "denominator_or_credit_context",
            "parked_sidecar",
            "maturing_debt_stock_reset_wedge_activity_response_missing",
            "do_not_convert_denominator_drag_to_numerator_drag",
            "ratewall_evidence_lane_fallback_registry.csv",
            "false",
            "present_local",
            "sidecar_only",
            "denominator_credit_sidecar_only",
            "firm_rollover_pressure_drag",
        ),
        _row(
            "zero_low_apr_credit",
            "research_appendix",
            "research_appendix",
            "Zero/low-APR credit remains product-screen sidecar unless source-backed stock path exists.",
            "sidecar",
            "zero_low_apr_product_screen",
            "var/preliminary_scenario_results/forecast_10y/ratewall_forecast_zero_low_apr_credit_materiality.csv",
            "outstanding_stock * rate_wedge * duration * pass_through * demand_conversion",
            "intermediated_financial_income",
            "context_or_sensitivity_D",
            "product_screen_not_central",
            "current_outstanding_stock_duration_path_missing_for_material_products",
            "reject_originations_only;central_allowed_only_after_product_gates",
            "ratewall_forecast_zero_low_apr_credit_materiality.csv",
            "false",
            "present_local",
            "product_screen",
            "consumer_credit_denominator_overlap_guard",
            "zero_low_apr_credit",
        ),
        _row(
            "current_denominator",
            "current_assumption_runtime",
            "headline_model",
            "Current denominator is the fixed annual-flow assumption-runtime anchor.",
            "benchmark_central",
            "ratewall_assumption_engine_denominator",
            "configs/ratewall_parameter_packs.yml;configs/ratewall_assumption_source_backing_overrides.yml",
            "D = GDP * contractionary_drag_gdp_share * rate_path_bps_year / 100",
            "not_a_numerator_translation",
            "current_fixed_D",
            "assumption_mode_literature_prior",
            "not_empirical_source_backed_denominator_estimate",
            "current_fixed_D_only;do_not_reuse_as_forecast_or_historical_selected_D",
            "ratewall_methodology_parity_denominators.csv",
            "false",
            "present_local",
            "current_runtime_denominator",
            "fixed_D_surface_specific",
            "current_fixed_D",
        ),
        _row(
            "forecast_denominator",
            "forecast_central_tdcsim_cbo",
            "headline_model",
            "Forecast selected denominator uses path D or moving D by scenario.",
            "central",
            "forecast_denominator_parity",
            "var/preliminary_scenario_results/denominator_parity/ratewall_denominator_parity_bridge.csv",
            "selected_D = moving_D for rate scenarios else path_D",
            "not_a_numerator_translation",
            "forecast_selected_D",
            "settled_structural_assumption_mode",
            "coefficient_is_not_evidence_mode",
            "preserve_selected_D_and_add_robustness_sidecar",
            "ratewall_denominator_scenario_delta_audit.csv",
            "false",
            "present_local",
            "fy2027_fy2036_forecast_denominator",
            "selected_D_surface_specific",
            "forecast_selected_D",
        ),
        _row(
            "historical_denominator",
            "historical_path_context",
            "headline_model",
            "Historical denominator dollars are required for provisional RW estimates.",
            "provisional_required",
            "historical_denominator_source_panel",
            "var/preliminary_scenario_results/historical_provisional_estimate/ratewall_historical_provisional_denominator_panel.csv;data/raw/cbo/55022-2026-02-Historical-Economic-Data.zip",
            "D = CBO_quarterly_nominal_GDP * drag_share_pp_gdp * CBO_fed_funds_rate_pct / 100",
            "not_a_numerator_translation",
            "historical_provisional_D",
            "source_backed_provisional_denominator_dollars",
            "final_rate_path_convention_and_classifier_gates_not_clear",
            "use_R30_provisional_D;final_classifier_gate_later",
            "ratewall_historical_provisional_denominator_panel.csv",
            "false",
            "present_local",
            "historical_provisional_denominator_built",
            "historical_D_not_forecast_moving_D",
            "historical_provisional_D",
        ),
    ]
    _validate_rows(rows)
    return rows


def source_method_summary_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return compact summary counts for the source/method matrix."""

    _validate_rows(rows)
    layers = Counter(row["presentation_layer"] for row in rows)
    central_allowed = sum(row["central_n_delta_bil_allowed"] == "true" for row in rows)
    source_statuses = Counter(row["local_source_status"] for row in rows)
    roles = Counter(row["object_role"] for row in rows)
    return [
        _summary("row_count", str(len(rows)), "source/method matrix rows"),
        _summary(
            "headline_model_rows",
            str(layers["headline_model"]),
            "rows allowed in the clean economist-facing model layer",
        ),
        _summary(
            "audit_ledger_rows",
            str(layers["audit_ledger"]),
            "rows for proof, source, coverage, and overlap tracking",
        ),
        _summary(
            "research_appendix_rows",
            str(layers["research_appendix"]),
            "candidate, parked, or diagnostic rows outside headline equations",
        ),
        _summary(
            "central_n_delta_allowed_rows",
            str(central_allowed),
            "rows whose central N effect is currently allowed by the matrix",
        ),
        *[
            _summary(
                f"object_role::{role}",
                str(roles[role]),
                f"rows with D9 disposition role {role}",
            )
            for role in sorted(ALLOWED_OBJECT_ROLES)
            if roles[role]
        ],
        _summary(
            "source_to_acquire_rows",
            str(source_statuses["source_to_acquire"]),
            "rows with named source work still required",
        ),
    ]


def write_source_method_matrix_outputs(
    output_dir: str | Path,
    *,
    rows: Sequence[Mapping[str, str]],
    summary_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write source/method matrix outputs."""

    root = Path(output_dir)
    outputs = {
        "matrix_csv": root / "ratewall_source_method_matrix.csv",
        "summary_csv": root / "ratewall_source_method_matrix_summary.csv",
    }
    write_rows(outputs["matrix_csv"], list(rows), SOURCE_METHOD_MATRIX_FIELDS)
    write_rows(
        outputs["summary_csv"], list(summary_rows), SOURCE_METHOD_SUMMARY_FIELDS
    )
    return outputs


def _row(
    block_id: str,
    surface_id: str,
    presentation_layer: str,
    claim: str,
    centrality: str,
    source_object: str,
    artifact: str,
    formula: str,
    translation: str,
    denominator: str,
    evidence: str,
    gap: str,
    admission: str,
    proof: str,
    central_allowed: str,
    local_source_status: str,
    source_coverage_flag: str,
    overlap_guard_id: str,
    compatibility_alias: str,
) -> dict[str, str]:
    return {
        "source_method_matrix_row_id": f"source_method_matrix::{block_id}",
        "block_id": block_id,
        "surface_id": surface_id,
        "object_role": _object_role(block_id, centrality, surface_id, proof),
        "presentation_layer": presentation_layer,
        "claim_status_plain_english": claim,
        "centrality": centrality,
        "source_object": source_object,
        "source_artifact_or_candidate": artifact,
        "method_formula": formula,
        "translation_family": translation,
        "denominator_object": denominator,
        "evidence_status": evidence,
        "known_gap": gap,
        "admission_or_parking_rule": admission,
        "proof_artifact": proof,
        "central_n_delta_bil_allowed": central_allowed,
        "local_source_status": local_source_status,
        "source_coverage_flag": source_coverage_flag,
        "overlap_guard_id": overlap_guard_id,
        "compatibility_alias": compatibility_alias,
        "allowed_use": "source_method_authority_for_model_buildout",
        "blocked_use": (
            "canonical_headline_promotion;evidence_mode_claim;"
            "implicit_source_status;silent_central_N_change"
        ),
        "claim_boundary": "source_method_matrix_no_model_value_change",
    }


def _summary(metric_id: str, value: str, interpretation: str) -> dict[str, str]:
    return {
        "source_method_summary_row_id": f"source_method_summary::{metric_id}",
        "summary_scope": "source_method_matrix",
        "metric_id": metric_id,
        "metric_value": value,
        "interpretation": interpretation,
        "allowed_use": "source_method_matrix_status_summary",
        "blocked_use": "canonical_headline_promotion;evidence_mode_claim",
    }


def _validate_rows(rows: Sequence[Mapping[str, str]]) -> None:
    if not rows:
        raise SourceMethodMatrixError("source/method matrix is empty")
    valid_layers = {"headline_model", "audit_ledger", "research_appendix"}
    seen: set[str] = set()
    for row in rows:
        block_id = row["block_id"]
        if block_id in seen:
            raise SourceMethodMatrixError(f"duplicate block_id: {block_id}")
        seen.add(block_id)
        if row["presentation_layer"] not in valid_layers:
            raise SourceMethodMatrixError(
                f"invalid presentation layer for {block_id}: {row['presentation_layer']}"
            )
        if row["central_n_delta_bil_allowed"] not in {"true", "false"}:
            raise SourceMethodMatrixError(
                f"invalid central_n_delta_bil_allowed for {block_id}"
            )
        if row["presentation_layer"] == "research_appendix" and row[
            "central_n_delta_bil_allowed"
        ] != "false":
            raise SourceMethodMatrixError(
                f"research appendix row can affect central N: {block_id}"
            )
        if row["object_role"] not in ALLOWED_OBJECT_ROLES:
            raise SourceMethodMatrixError(
                f"invalid object role for {block_id}: {row['object_role']}"
            )


def _object_role(
    block_id: str,
    centrality: str,
    surface_id: str,
    proof_artifact: str,
) -> str:
    if block_id in {"forecast_tdc_support", "forecast_public_interest_net_block"}:
        return "selected_n"
    if block_id in {
        "forecast_fed_liability_sources",
        "forecast_remittance_baseline_path",
        "forecast_direct_treasury_interest_block_input",
    }:
        return "selected_block_input"
    if block_id == "current_public_interest_runtime":
        return "selected_benchmark_recast"
    if block_id in {"current_denominator", "forecast_denominator", "historical_denominator"}:
        return "denominator_only"
    if block_id in {
        "firm_liquid_asset_cushion",
        "current_tdc_decomposition",
    }:
        return "candidate_replacement" if "current" not in block_id else "diagnostic_context"
    if block_id in {"firm_cash_attenuation", "safe_asset_allocation_offset_drag"}:
        return "sensitivity_only"
    if block_id in {
        "realized_safe_yield_income",
        "zero_low_apr_credit",
    }:
        return "blocked_source_or_method"
    if block_id == "firm_rollover_pressure_drag":
        return "denominator_only"
    if surface_id == "historical_path_context" or "historical" in block_id:
        return "diagnostic_context"
    if centrality in {"central", "benchmark_central"}:
        return "selected_n" if surface_id.startswith("forecast") else "selected_benchmark_recast"
    if centrality in {"block_input", "baseline_context"}:
        return "selected_block_input"
    if centrality in {"replacement_candidate"}:
        return "candidate_replacement"
    if centrality in {"sensitivity", "sidecar"}:
        return "sensitivity_only"
    if "not_applicable" in proof_artifact:
        return "not_applicable"
    return "diagnostic_context"
