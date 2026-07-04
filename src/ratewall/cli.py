"""Command-line entry points for the RateWall kernel."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from ratewall.accounting.rate_impulse import HorizonRepricing, RateImpulseInputs
from ratewall.accounting.rate_impulse import compute_rate_impulse
from ratewall.databook.build import (
    apply_default_table_output_policy,
    build_databook,
    refresh_build_census_written_tables,
)
from ratewall.data.build import build_snapshot_bundle
from ratewall.data.derived import derive_accounting_inputs
from ratewall.data.snapshots import read_snapshot_bundle
from ratewall.empirical.local_projection import (
    write_empirical_results,
    write_empirical_smoke_panel,
    write_empirical_specs,
    write_shock_dataset_catalog,
)
from ratewall.model.scenarios import build_scenario_table
from ratewall.release import build_release_package
from ratewall.sources.fred import FredAdapter
from ratewall.sources.registry import SourceRegistry

DEFAULT_CONFIG = Path("configs/sources.yml")
RELEASE_VALIDATION_TABLE_NAMES = {
    "ratewall_backend_artifact_claim_boundary_manifest.csv",
    "ratewall_backend_surface_schema_contract.csv",
    "ratewall_release_archive_reproducibility_audit.csv",
}
RELEASE_DATABOOK_REBUILD_MODES = ("none", "default", "full")


def _decimal_arg(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except Exception as exc:  # pragma: no cover - argparse displays the message
        raise argparse.ArgumentTypeError(f"not a decimal number: {value}") from exc
    return parsed


def _filter_existing_artifact_payload(payload: dict[str, object]) -> dict[str, object]:
    filtered: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            if Path(value).exists():
                filtered[key] = value
        elif isinstance(value, list):
            filtered[key] = [
                item
                for item in value
                if not isinstance(item, str) or Path(item).exists()
            ]
        else:
            filtered[key] = value
    return filtered


def _load_registry(path: Path) -> SourceRegistry:
    return SourceRegistry.from_path(path)


def _cmd_sources_list(args: argparse.Namespace) -> int:
    registry = _load_registry(args.config)
    for source in registry.sources.values():
        series_count = len(registry.series_for_source(source.source_id))
        print(f"{source.source_id}\t{source.name}\t{series_count} series")
    return 0


def _cmd_sources_show(args: argparse.Namespace) -> int:
    registry = _load_registry(args.config)
    source = registry.source(args.source)
    print(json.dumps(source.to_dict(), indent=2, sort_keys=True))
    return 0


def _cmd_data_pull(args: argparse.Namespace) -> int:
    registry = _load_registry(args.config)
    if args.source != "fred":
        raise SystemExit("first tranche implements live pulls for source 'fred' only")
    snapshot = FredAdapter(registry).pull_series(args.series)
    print(json.dumps(snapshot.to_dict(), indent=2, sort_keys=True))
    return 0


def _cmd_data_snapshot(args: argparse.Namespace) -> int:
    registry = _load_registry(args.config)
    series_ids = tuple(args.series) if args.series else None
    output = build_snapshot_bundle(
        registry=registry,
        output=args.output,
        mode=args.mode,
        **({"series_ids": series_ids} if series_ids is not None else {}),
        progress=args.mode == "live",
    )
    print(str(output))
    return 0


def _cmd_impulse(args: argparse.Namespace) -> int:
    if args.snapshot:
        derived = derive_accounting_inputs(read_snapshot_bundle(args.snapshot))
        inputs = derived.to_rate_impulse_inputs()
    else:
        horizons = [
            HorizonRepricing(
                label=args.horizon,
                months=args.months,
                debt_repricing=args.debt_repricing,
            )
        ]
        inputs = RateImpulseInputs(
            reserves=args.reserves,
            on_rrp=args.on_rrp,
            gdp=args.gdp,
            horizons=horizons,
            fed_remittance_offset=args.fed_remittance_offset,
        )
    impulse = compute_rate_impulse(inputs, bps=args.bps)
    payload = {label: result.to_dict() for label, result in impulse.items()}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_databook_build(args: argparse.Namespace) -> int:
    full = args.full or args.legacy_full
    if full and (args.include_frozen or args.forbid_extra_default_tables):
        raise SystemExit(
            "--include-frozen and --forbid-extra-default-tables only apply to "
            "default spine-only output mode"
        )
    artifacts = build_databook(
        snapshot_bundle=args.snapshot,
        output_dir=args.output_dir,
        full=full,
    )
    if not full:
        apply_default_table_output_policy(
            args.output_dir,
            include_frozen=args.include_frozen,
            forbid_extra_default_tables=args.forbid_extra_default_tables,
        )
        refresh_build_census_written_tables(args.output_dir)
    dynamic_path_consistency_table = (
        artifacts.ratewall_dynamic_scenario_path_consistency_diagnostic_table
    )
    payload = {
                "impulse_table": str(artifacts.impulse_table),
                "summary_table": str(artifacts.summary_table),
                "metrics_table": str(artifacts.metrics_table),
                "maturity_ladder_table": str(artifacts.maturity_ladder_table),
                "mspd_reconciliation_table": str(artifacts.mspd_reconciliation_table),
                "mspd_field_coverage_table": str(artifacts.mspd_field_coverage_table),
                "cbo_projection_table": str(artifacts.cbo_projection_table),
                "treasury_coupon_cashflow_table": str(
                    artifacts.treasury_coupon_cashflow_table
                ),
                "treasury_frn_tips_assumptions_table": str(
                    artifacts.treasury_frn_tips_assumptions_table
                ),
                "treasury_buybacks_table": str(artifacts.treasury_buybacks_table),
                "treasury_buyback_mspd_join_table": str(
                    artifacts.treasury_buyback_mspd_join_table
                ),
                "holder_context_table": str(artifacts.holder_context_table),
                "fine_holder_context_table": str(artifacts.fine_holder_context_table),
                "tic_foreign_holder_reconciliation_table": str(
                    artifacts.tic_foreign_holder_reconciliation_table
                ),
                "tic_foreign_treasury_stock_split_table": str(
                    artifacts.tic_foreign_treasury_stock_split_table
                ),
                "ofr_mmf_treasury_context_table": str(
                    artifacts.ofr_mmf_treasury_context_table
                ),
                "sec_nmfp_mmf_treasury_cusip_context_table": str(
                    artifacts.sec_nmfp_mmf_treasury_cusip_context_table
                ),
                "treasury_valuation_inputs_table": str(
                    artifacts.treasury_valuation_inputs_table
                ),
                "treasury_daily_valuation_paths_table": str(
                    artifacts.treasury_daily_valuation_paths_table
                ),
                "treasury_valuation_validation_table": str(
                    artifacts.treasury_valuation_validation_table
                ),
                "treasury_valuation_coverage_diagnostics_table": str(
                    artifacts.treasury_valuation_coverage_diagnostics_table
                ),
                "treasury_tips_formula_review_explanation_table": str(
                    artifacts.treasury_tips_formula_review_explanation_table
                ),
                "treasury_valuation_convention_audit_table": str(
                    artifacts.treasury_valuation_convention_audit_table
                ),
                "treasury_cashflow_edge_fixtures_table": str(
                    artifacts.treasury_cashflow_edge_fixtures_table
                ),
                "treasury_frn_leap_day_source_gap_table": str(
                    artifacts.treasury_frn_leap_day_source_gap_table
                ),
                "treasury_frn_reset_source_blocker_map_table": str(
                    artifacts.treasury_frn_reset_source_blocker_map_table
                ),
                "treasury_frn_reset_method_note_table": str(
                    artifacts.treasury_frn_reset_method_note_table
                ),
                "treasury_frn_reset_official_source_audit_table": str(
                    artifacts.treasury_frn_reset_official_source_audit_table
                ),
                "treasury_frn_reset_official_source_schema_evidence_table": str(
                    artifacts.treasury_frn_reset_official_source_schema_evidence_table
                ),
                "treasury_frn_reset_method_semantics_audit_table": str(
                    artifacts.treasury_frn_reset_method_semantics_audit_table
                ),
                "treasury_frn_reset_method_design_ledger_table": str(
                    artifacts.treasury_frn_reset_method_design_ledger_table
                ),
                "treasury_frn_reset_cusip_coverage_ledger_table": str(
                    artifacts.treasury_frn_reset_cusip_coverage_ledger_table
                ),
                "treasury_frn_reset_fixture_readiness_ledger_table": str(
                    artifacts.treasury_frn_reset_fixture_readiness_ledger_table
                ),
                "treasury_frn_reset_calendar_policy_table": str(
                    artifacts.treasury_frn_reset_calendar_policy_table
                ),
                "treasury_frn_reset_explicit_opt_in_gate_table": str(
                    artifacts.treasury_frn_reset_explicit_opt_in_gate_table
                ),
                "treasury_frn_reset_method_frontier_ledger_table": str(
                    artifacts.treasury_frn_reset_method_frontier_ledger_table
                ),
                "treasury_valuation_readiness_coverage_table": str(
                    artifacts.treasury_valuation_readiness_coverage_table
                ),
                "treasury_valuation_readiness_gate_evidence_table": str(
                    artifacts.treasury_valuation_readiness_gate_evidence_table
                ),
                "treasury_valuation_opt_in_contract_table": str(
                    artifacts.treasury_valuation_opt_in_contract_table
                ),
                "treasury_pricing_switch_audit_table": str(
                    artifacts.treasury_pricing_switch_audit_table
                ),
                "treasury_valuation_engine_readiness_gate_table": str(
                    artifacts.treasury_valuation_engine_readiness_gate_table
                ),
                "holder_allocation_gate_table": str(
                    artifacts.holder_allocation_gate_table
                ),
                "disabled_final_owner_allocation_table": str(
                    artifacts.disabled_final_owner_allocation_table
                ),
                "disabled_allocation_design_ledger_table": str(
                    artifacts.disabled_allocation_design_ledger_table
                ),
                "distributional_exposure_levels_table": str(
                    artifacts.distributional_exposure_levels_table
                ),
                "tdc_deposit_channel_ledger_table": str(
                    artifacts.tdc_deposit_channel_ledger_table
                ),
                "treasury_attributed_deposit_component_table": str(
                    artifacts.treasury_attributed_deposit_component_table
                ),
                "tdc_ru_financing_deposit_impulse_table": str(
                    artifacts.tdc_ru_financing_deposit_impulse_table
                ),
                "tdc_historical_panel_table": str(artifacts.tdc_historical_panel_table),
                "deposit_pricing_pass_through_table": str(
                    artifacts.deposit_pricing_pass_through_table
                ),
                "tdc_historical_reconciliation_table": str(
                    artifacts.tdc_historical_reconciliation_table
                ),
                "ratewall_threshold_simulation_table": str(
                    artifacts.ratewall_threshold_simulation_table
                ),
                "ratewall_threshold_calibration_ranges_table": str(
                    artifacts.ratewall_threshold_calibration_ranges_table
                ),
                "ratewall_threshold_calibrated_simulation_table": str(
                    artifacts.ratewall_threshold_calibrated_simulation_table
                ),
                "ratewall_du_ru_tga_calibration_bridge_table": str(
                    artifacts.ratewall_du_ru_tga_calibration_bridge_table
                ),
                "ratewall_tdcest_historical_estimator_bridge_table": str(
                    artifacts.ratewall_tdcest_historical_estimator_bridge_table
                ),
                "ratewall_tdcest_monetary_route_bridge_table": str(
                    artifacts.ratewall_tdcest_monetary_route_bridge_table
                ),
                "ratewall_tdcest_mmf_route_split_context_table": str(
                    artifacts.ratewall_tdcest_mmf_route_split_context_table
                ),
                "ratewall_tdcest_z1_domestic_nonbank_sector_context_table": str(
                    artifacts.ratewall_tdcest_z1_domestic_nonbank_sector_context_table
                ),
                "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy_table": str(
                    artifacts.ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy_table
                ),
                "ratewall_tdc_rolling_pass_through_context_table": str(
                    artifacts.ratewall_tdc_rolling_pass_through_context_table
                ),
                "ratewall_tdc_deposit_pass_through_trigger_validation_preflight_table": str(
                    artifacts.ratewall_tdc_deposit_pass_through_trigger_validation_preflight_table
                ),
                "ratewall_tdc_deposit_pass_through_scenario_contract_invariant_audit_table": str(
                    artifacts.ratewall_tdc_deposit_pass_through_scenario_contract_invariant_audit_table
                ),
                "ratewall_historical_tdc_wall_ratio_path_table": str(
                    artifacts.ratewall_historical_tdc_wall_ratio_path_table
                ),
                "ratewall_historical_assumption_mode_tdc_wall_ratio_path_table": str(
                    artifacts.ratewall_historical_assumption_mode_tdc_wall_ratio_path_table
                ),
                "ratewall_tdc_other_component_bridge_table": str(
                    artifacts.ratewall_tdc_other_component_bridge_table
                ),
                "ratewall_tdc_deposit_credit_decomposition_table": str(
                    artifacts.ratewall_tdc_deposit_credit_decomposition_table
                ),
                "ratewall_tdc_double_count_guardrail_table": str(
                    artifacts.ratewall_tdc_double_count_guardrail_table
                ),
                "ratewall_tdc_net_ratewall_effect_table": str(
                    artifacts.ratewall_tdc_net_ratewall_effect_table
                ),
                "ratewall_forecast_holder_tdc_consistency_bridge_table": str(
                    artifacts.ratewall_forecast_holder_tdc_consistency_bridge_table
                ),
                "ratewall_conventional_drag_decomposition_table": str(
                    artifacts.ratewall_conventional_drag_decomposition_table
                ),
                "ratewall_public_impulse_factorization_table": str(
                    artifacts.ratewall_public_impulse_factorization_table
                ),
                "ratewall_public_liability_repricing_ladder_table": str(
                    artifacts.ratewall_public_liability_repricing_ladder_table
                ),
                "ratewall_public_liability_repricing_evidence_bridge_table": str(
                    artifacts.ratewall_public_liability_repricing_evidence_bridge_table
                ),
                "ratewall_public_liability_repricing_reconciliation_gap_table": str(
                    artifacts.ratewall_public_liability_repricing_reconciliation_gap_table
                ),
                "ratewall_mspd_table3_bucket_repricing_gate_table": str(
                    artifacts.ratewall_mspd_table3_bucket_repricing_gate_table
                ),
                "ratewall_treasury_bucket_repricing_prior_bridge_table": str(
                    artifacts.ratewall_treasury_bucket_repricing_prior_bridge_table
                ),
                "ratewall_interest_recipient_leakage_bridge_table": str(
                    artifacts.ratewall_interest_recipient_leakage_bridge_table
                ),
                "ratewall_interest_recipient_leakage_evidence_gap_table": str(
                    artifacts.ratewall_interest_recipient_leakage_evidence_gap_table
                ),
                "ratewall_treasury_recipient_leakage_source_gate_table": str(
                    artifacts.ratewall_treasury_recipient_leakage_source_gate_table
                ),
                "ratewall_public_finance_timing_path_table": str(
                    artifacts.ratewall_public_finance_timing_path_table
                ),
                "ratewall_public_finance_timing_evidence_gap_table": str(
                    artifacts.ratewall_public_finance_timing_evidence_gap_table
                ),
                "ratewall_public_finance_timing_design_test_scaffold_table": str(
                    artifacts.ratewall_public_finance_timing_design_test_scaffold_table
                ),
                "ratewall_safe_yield_offset_drag_pairing_gap_table": str(
                    artifacts.ratewall_safe_yield_offset_drag_pairing_gap_table
                ),
                "ratewall_bnpl_zero_interest_float_evidence_gap_table": str(
                    artifacts.ratewall_bnpl_zero_interest_float_evidence_gap_table
                ),
                "ratewall_financialized_balance_sheet_evidence_gap_table": str(
                    artifacts.ratewall_financialized_balance_sheet_evidence_gap_table
                ),
                "ratewall_financialization_proxy_registry_table": str(
                    artifacts.ratewall_financialization_proxy_registry_table
                ),
                "ratewall_household_safe_asset_capture_proxy_table": str(
                    artifacts.ratewall_household_safe_asset_capture_proxy_table
                ),
                "ratewall_household_safe_asset_exposure_panel_table": str(
                    artifacts.ratewall_household_safe_asset_exposure_panel_table
                ),
                "ratewall_household_safe_asset_access_context_table": str(
                    artifacts.ratewall_household_safe_asset_access_context_table
                ),
                "ratewall_retail_safe_yield_access_substitution_context_table": str(
                    artifacts.ratewall_retail_safe_yield_access_substitution_context_table
                ),
                "ratewall_retail_deposit_beta_gap_context_table": str(
                    artifacts.ratewall_retail_deposit_beta_gap_context_table
                ),
                "ratewall_retail_pass_through_dispersion_panel_table": str(
                    artifacts.ratewall_retail_pass_through_dispersion_panel_table
                ),
                "ratewall_deposit_competition_conditioner_table": str(
                    artifacts.ratewall_deposit_competition_conditioner_table
                ),
                "ratewall_deposit_mmf_substitution_surface_table": str(
                    artifacts.ratewall_deposit_mmf_substitution_surface_table
                ),
                "ratewall_personal_net_interest_position_context_table": str(
                    artifacts.ratewall_personal_net_interest_position_context_table
                ),
                "ratewall_firm_liquid_asset_public_context_table": str(
                    artifacts.ratewall_firm_liquid_asset_public_context_table
                ),
                "ratewall_firm_liquid_asset_cushion_panel_table": str(
                    artifacts.ratewall_firm_liquid_asset_cushion_panel_table
                ),
                "ratewall_firm_net_interest_cushion_context_table": str(
                    artifacts.ratewall_firm_net_interest_cushion_context_table
                ),
                "ratewall_firm_rollover_pressure_panel_table": str(
                    artifacts.ratewall_firm_rollover_pressure_panel_table
                ),
                "ratewall_firm_short_rate_exposure_proxy_table": str(
                    artifacts.ratewall_firm_short_rate_exposure_proxy_table
                ),
                "ratewall_household_borrower_fragility_context_table": str(
                    artifacts.ratewall_household_borrower_fragility_context_table
                ),
                "ratewall_bank_loan_repricing_context_table": str(
                    artifacts.ratewall_bank_loan_repricing_context_table
                ),
                "ratewall_cre_refinancing_public_context_table": str(
                    artifacts.ratewall_cre_refinancing_public_context_table
                ),
                "ratewall_private_credit_bdc_context_table": str(
                    artifacts.ratewall_private_credit_bdc_context_table
                ),
                "ratewall_safe_yield_paired_proxy_surface_table": str(
                    artifacts.ratewall_safe_yield_paired_proxy_surface_table
                ),
                "ratewall_financialization_proxy_source_gate_table": str(
                    artifacts.ratewall_financialization_proxy_source_gate_table
                ),
                "ratewall_financialization_source_gate_table": str(
                    artifacts.ratewall_financialization_source_gate_table
                ),
                "ratewall_financialization_restricted_protocols_table": str(
                    artifacts.ratewall_financialization_restricted_protocols_table
                ),
                "ratewall_financialization_double_count_audit_table": str(
                    artifacts.ratewall_financialization_double_count_audit_table
                ),
                "ratewall_financialization_overlap_audit_table": str(
                    artifacts.ratewall_financialization_overlap_audit_table
                ),
                "ratewall_financialization_artifact_traceability_matrix_table": str(
                    artifacts.ratewall_financialization_artifact_traceability_matrix_table
                ),
                "ratewall_backend_expansion_context_registry_table": str(
                    artifacts.ratewall_backend_expansion_context_registry_table
                ),
                "ratewall_assumption_mode_channel_promotion_decision_table": str(
                    artifacts.ratewall_assumption_mode_channel_promotion_decision_table
                ),
                "ratewall_assumption_mode_promoted_channel_contributions_table": str(
                    artifacts.ratewall_assumption_mode_promoted_channel_contributions_table
                ),
                "ratewall_assumption_mode_overlap_guardrail_audit_table": str(
                    artifacts.ratewall_assumption_mode_overlap_guardrail_audit_table
                ),
                "ratewall_assumption_mode_recipient_conversion_overlap_audit_table": str(
                    artifacts.ratewall_assumption_mode_recipient_conversion_overlap_audit_table
                ),
                "ratewall_assumption_mode_sidecar_channel_decision_table": str(
                    artifacts.ratewall_assumption_mode_sidecar_channel_decision_table
                ),
                "ratewall_assumption_mode_sidecar_contributions_table": str(
                    artifacts.ratewall_assumption_mode_sidecar_contributions_table
                ),
                "ratewall_assumption_mode_sidecar_reasonableness_audit_table": str(
                    artifacts.ratewall_assumption_mode_sidecar_reasonableness_audit_table
                ),
                "ratewall_assumption_mode_dynamic_sidecar_paths_table": str(
                    artifacts.ratewall_assumption_mode_dynamic_sidecar_paths_table
                ),
                "ratewall_assumption_mode_sidecar_frontier_table": str(
                    artifacts.ratewall_assumption_mode_sidecar_frontier_table
                ),
                "ratewall_assumption_mode_sidecar_bundle_frontier_table": str(
                    artifacts.ratewall_assumption_mode_sidecar_bundle_frontier_table
                ),
                "ratewall_assumption_mode_sidecar_driver_decomposition_table": str(
                    artifacts.ratewall_assumption_mode_sidecar_driver_decomposition_table
                ),
                "ratewall_assumption_mode_dynamic_sidecar_driver_decomposition_table": str(
                    artifacts.ratewall_assumption_mode_dynamic_sidecar_driver_decomposition_table
                ),
                "ratewall_assumption_mode_dynamic_sidecar_family_summary_table": str(
                    artifacts.ratewall_assumption_mode_dynamic_sidecar_family_summary_table
                ),
                "ratewall_assumption_mode_dynamic_sidecar_secondary_paths_table": str(
                    artifacts.ratewall_assumption_mode_dynamic_sidecar_secondary_paths_table
                ),
                "ratewall_assumption_mode_dynamic_sidecar_secondary_frontier_table": str(
                    artifacts.ratewall_assumption_mode_dynamic_sidecar_secondary_frontier_table
                ),
                "ratewall_assumption_mode_parameter_activation_ledger_table": str(
                    artifacts.ratewall_assumption_mode_parameter_activation_ledger_table
                ),
                "ratewall_assumption_mode_channel_status_crosswalk_table": str(
                    artifacts.ratewall_assumption_mode_channel_status_crosswalk_table
                ),
                "ratewall_assumption_mode_formula_identity_audit_table": str(
                    artifacts.ratewall_assumption_mode_formula_identity_audit_table
                ),
                "ratewall_restricted_protocol_falsification_matrix_table": str(
                    artifacts.ratewall_restricted_protocol_falsification_matrix_table
                ),
                "ratewall_restricted_protocol_field_contract_table": str(
                    artifacts.ratewall_restricted_protocol_field_contract_table
                ),
                "ratewall_context_surface_no_main_ratio_audit_table": str(
                    artifacts.ratewall_context_surface_no_main_ratio_audit_table
                ),
                "ratewall_backend_surface_schema_contract_table": str(
                    artifacts.ratewall_backend_surface_schema_contract_table
                ),
                "ratewall_backend_artifact_claim_boundary_manifest_table": str(
                    artifacts.ratewall_backend_artifact_claim_boundary_manifest_table
                ),
                "ratewall_release_archive_reproducibility_audit_table": str(
                    artifacts.ratewall_release_archive_reproducibility_audit_table
                ),
                "ratewall_generated_text_claim_boundary_scan_table": str(
                    artifacts.ratewall_generated_text_claim_boundary_scan_table
                ),
                "ratewall_assumption_mode_recipient_leakage_absorber_basis_audit_table": str(
                    artifacts.ratewall_assumption_mode_recipient_leakage_absorber_basis_audit_table
                ),
                "ratewall_household_within_distribution_safe_asset_capture_context_table": str(
                    artifacts.ratewall_household_within_distribution_safe_asset_capture_context_table
                ),
                "ratewall_deposit_pass_through_dispersion_conditioner_table": str(
                    artifacts.ratewall_deposit_pass_through_dispersion_conditioner_table
                ),
                "ratewall_brokerage_tbill_mmf_access_context_table": str(
                    artifacts.ratewall_brokerage_tbill_mmf_access_context_table
                ),
                "ratewall_firm_interest_income_expense_balance_context_table": str(
                    artifacts.ratewall_firm_interest_income_expense_balance_context_table
                ),
                "ratewall_firm_debt_maturity_wall_context_table": str(
                    artifacts.ratewall_firm_debt_maturity_wall_context_table
                ),
                "ratewall_bdc_private_credit_stress_marker_context_table": str(
                    artifacts.ratewall_bdc_private_credit_stress_marker_context_table
                ),
                "ratewall_cre_maturity_refi_pressure_context_table": str(
                    artifacts.ratewall_cre_maturity_refi_pressure_context_table
                ),
                "ratewall_bnpl_zero_interest_float_context_table": str(
                    artifacts.ratewall_bnpl_zero_interest_float_context_table
                ),
                "ratewall_safe_asset_substitution_pairing_audit_table": str(
                    artifacts.ratewall_safe_asset_substitution_pairing_audit_table
                ),
                "ratewall_financialization_expansion_avoidance_audit_table": str(
                    artifacts.ratewall_financialization_expansion_avoidance_audit_table
                ),
                "ratewall_bank_nim_credit_supply_context_table": str(
                    artifacts.ratewall_bank_nim_credit_supply_context_table
                ),
                "ratewall_tax_timing_interest_income_context_table": str(
                    artifacts.ratewall_tax_timing_interest_income_context_table
                ),
                "ratewall_foreign_holder_interest_leakage_context_table": str(
                    artifacts.ratewall_foreign_holder_interest_leakage_context_table
                ),
                "ratewall_public_finance_remittance_timing_stress_grid_table": str(
                    artifacts.ratewall_public_finance_remittance_timing_stress_grid_table
                ),
                "ratewall_insurance_pension_asset_liability_context_table": str(
                    artifacts.ratewall_insurance_pension_asset_liability_context_table
                ),
                "ratewall_housing_lockin_cashflow_context_table": str(
                    artifacts.ratewall_housing_lockin_cashflow_context_table
                ),
                "ratewall_dealer_inventory_carry_context_table": str(
                    artifacts.ratewall_dealer_inventory_carry_context_table
                ),
                "ratewall_financialization_proxy_backend_audit": str(
                    artifacts.ratewall_financialization_proxy_backend_audit
                ),
                "ratewall_paper_financialization_interpretation_table": str(
                    artifacts.ratewall_paper_financialization_interpretation_table
                ),
                "ratewall_financialization_interpretation_memo": str(
                    artifacts.ratewall_financialization_interpretation_memo
                ),
                "ratewall_firm_cash_debt_maturity_evidence_gap_table": str(
                    artifacts.ratewall_firm_cash_debt_maturity_evidence_gap_table
                ),
                "ratewall_conventional_drag_channel_evidence_gap_table": str(
                    artifacts.ratewall_conventional_drag_channel_evidence_gap_table
                ),
                "ratewall_conventional_drag_source_design_gate_table": str(
                    artifacts.ratewall_conventional_drag_source_design_gate_table
                ),
                "ratewall_calibration_parameter_recommendations_table": str(
                    artifacts.ratewall_calibration_parameter_recommendations_table
                ),
                "ratewall_calibration_source_acquisition_plan_table": str(
                    artifacts.ratewall_calibration_source_acquisition_plan_table
                ),
                "ratewall_denominator_calibration_design_gate_table": str(
                    artifacts.ratewall_denominator_calibration_design_gate_table
                ),
                "ratewall_recipient_leakage_design_gate_table": str(
                    artifacts.ratewall_recipient_leakage_design_gate_table
                ),
                "ratewall_public_finance_timing_bridge_table": str(
                    artifacts.ratewall_public_finance_timing_bridge_table
                ),
                "ratewall_denominator_response_design_scaffold_table": str(
                    artifacts.ratewall_denominator_response_design_scaffold_table
                ),
                "ratewall_denominator_response_design_test_scaffold_table": str(
                    artifacts.ratewall_denominator_response_design_test_scaffold_table
                ),
                "ratewall_denominator_response_gate_attempt_table": str(
                    artifacts.ratewall_denominator_response_gate_attempt_table
                ),
                "ratewall_denominator_aligned_response_panel_scaffold_table": str(
                    artifacts.ratewall_denominator_aligned_response_panel_scaffold_table
                ),
                "ratewall_denominator_event_outcome_cell_diagnostic_table": str(
                    artifacts.ratewall_denominator_event_outcome_cell_diagnostic_table
                ),
                "ratewall_denominator_event_outcome_panel_value_diagnostic_table": str(
                    artifacts.ratewall_denominator_event_outcome_panel_value_diagnostic_table
                ),
                "ratewall_denominator_event_level_response_panel_table": str(
                    artifacts.ratewall_denominator_event_level_response_panel_table
                ),
                "ratewall_denominator_uncertainty_pass_fail_review_table": str(
                    artifacts.ratewall_denominator_uncertainty_pass_fail_review_table
                ),
                "ratewall_denominator_panel_design_test_diagnostic_table": str(
                    artifacts.ratewall_denominator_panel_design_test_diagnostic_table
                ),
                "ratewall_denominator_pretrend_placebo_diagnostic_table": str(
                    artifacts.ratewall_denominator_pretrend_placebo_diagnostic_table
                ),
                "ratewall_denominator_shock_relevance_diagnostic_table": str(
                    artifacts.ratewall_denominator_shock_relevance_diagnostic_table
                ),
                "ratewall_denominator_sign_consistency_diagnostic_table": str(
                    artifacts.ratewall_denominator_sign_consistency_diagnostic_table
                ),
                "ratewall_denominator_horizon_sensitivity_diagnostic_table": str(
                    artifacts.ratewall_denominator_horizon_sensitivity_diagnostic_table
                ),
                "ratewall_denominator_outlier_window_robustness_diagnostic_table": str(
                    artifacts.ratewall_denominator_outlier_window_robustness_diagnostic_table
                ),
                "ratewall_denominator_design_readiness_decision_table": str(
                    artifacts.ratewall_denominator_design_readiness_decision_table
                ),
                "ratewall_denominator_formal_design_test_result_scaffold_table": str(
                    artifacts.ratewall_denominator_formal_design_test_result_scaffold_table
                ),
                "ratewall_denominator_formal_design_test_result_table": str(
                    artifacts.ratewall_denominator_formal_design_test_result_table
                ),
                "ratewall_denominator_response_estimate_diagnostic_table": str(
                    artifacts.ratewall_denominator_response_estimate_diagnostic_table
                ),
                "ratewall_denominator_cross_source_design_validation_table": str(
                    artifacts.ratewall_denominator_cross_source_design_validation_table
                ),
                "ratewall_denominator_evidence_upgrade_source_design_requirement_table": str(
                    artifacts.ratewall_denominator_evidence_upgrade_source_design_requirement_table
                ),
                "ratewall_denominator_evidence_upgrade_priority_queue_table": str(
                    artifacts.ratewall_denominator_evidence_upgrade_priority_queue_table
                ),
                "ratewall_denominator_evidence_upgrade_tier1_workplan_table": str(
                    artifacts.ratewall_denominator_evidence_upgrade_tier1_workplan_table
                ),
                "ratewall_denominator_evidence_upgrade_blocker_resolution_matrix_table": str(
                    artifacts.ratewall_denominator_evidence_upgrade_blocker_resolution_matrix_table
                ),
                "ratewall_denominator_evidence_upgrade_blocker_status_rollup_table": str(
                    artifacts.ratewall_denominator_evidence_upgrade_blocker_status_rollup_table
                ),
                "ratewall_conventional_drag_evidence_tranche_table": str(
                    artifacts.ratewall_conventional_drag_evidence_tranche_table
                ),
                "ratewall_conventional_drag_demand_conversion_admission_table": str(
                    artifacts.ratewall_conventional_drag_demand_conversion_admission_table
                ),
                "ratewall_conventional_drag_calibration_route_table": str(
                    artifacts.ratewall_conventional_drag_calibration_route_table
                ),
                "ratewall_conventional_drag_research_parameterization_source_contract_table": str(
                    artifacts.ratewall_conventional_drag_research_parameterization_source_contract_table
                ),
                "ratewall_conventional_drag_research_parameterization_source_frontier_table": str(
                    artifacts.ratewall_conventional_drag_research_parameterization_source_frontier_table
                ),
                "ratewall_conventional_drag_research_payload_manifest_table": str(
                    artifacts.ratewall_conventional_drag_research_payload_manifest_table
                ),
                "ratewall_conventional_drag_research_parameterization_parser_status_table": str(
                    artifacts.ratewall_conventional_drag_research_parameterization_parser_status_table
                ),
                "ratewall_conventional_drag_research_payload_inner_inventory_table": str(
                    artifacts.ratewall_conventional_drag_research_payload_inner_inventory_table
                ),
                "ratewall_conventional_drag_research_extraction_candidate_table": str(
                    artifacts.ratewall_conventional_drag_research_extraction_candidate_table
                ),
                "ratewall_conventional_drag_research_extraction_gate_audit_table": str(
                    artifacts.ratewall_conventional_drag_research_extraction_gate_audit_table
                ),
                "ratewall_frbus_conventional_drag_benchmark_protocol_table": str(
                    artifacts.ratewall_frbus_conventional_drag_benchmark_protocol_table
                ),
                "ratewall_frbus_official_model_package_inventory_table": str(
                    artifacts.ratewall_frbus_official_model_package_inventory_table
                ),
                "ratewall_frbus_official_model_benchmark_simulation_protocol_table": str(
                    artifacts.ratewall_frbus_official_model_benchmark_simulation_protocol_table
                ),
                "ratewall_frbus_runtime_runner_preflight_table": str(
                    artifacts.ratewall_frbus_runtime_runner_preflight_table
                ),
                "ratewall_frbus_runtime_runner_output_slots_table": str(
                    artifacts.ratewall_frbus_runtime_runner_output_slots_table
                ),
                "ratewall_frbus_benchmark_comparison_mapping_contract_table": str(
                    artifacts.ratewall_frbus_benchmark_comparison_mapping_contract_table
                ),
                "ratewall_frbus_benchmark_output_slot_extension_review_table": str(
                    artifacts.ratewall_frbus_benchmark_output_slot_extension_review_table
                ),
                "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge_table": str(
                    artifacts.ratewall_conventional_drag_source_unit_aggregation_blocker_bridge_table
                ),
                "ratewall_conventional_drag_mirgk_targeted_gap_source_followup_table": str(
                    artifacts.ratewall_conventional_drag_mirgk_targeted_gap_source_followup_table
                ),
                "ratewall_conventional_drag_promotion_contract_checklist_table": str(
                    artifacts.ratewall_conventional_drag_promotion_contract_checklist_table
                ),
                "ratewall_current_demand_gdp_share_source_manifest_table": str(
                    artifacts.ratewall_current_demand_gdp_share_source_manifest_table
                ),
                "ratewall_current_demand_gdp_share_panel_table": str(
                    artifacts.ratewall_current_demand_gdp_share_panel_table
                ),
                "ratewall_conventional_drag_current_demand_mapping_bridge_table": str(
                    artifacts.ratewall_conventional_drag_current_demand_mapping_bridge_table
                ),
                "ratewall_conventional_drag_research_extraction_conversion_bridge_table": str(
                    artifacts.ratewall_conventional_drag_research_extraction_conversion_bridge_table
                ),
                "ratewall_conventional_drag_local_macro_panel_table": str(
                    artifacts.ratewall_conventional_drag_local_macro_panel_table
                ),
                "ratewall_conventional_drag_local_shock_quarterly_table": str(
                    artifacts.ratewall_conventional_drag_local_shock_quarterly_table
                ),
                "ratewall_conventional_drag_local_lp_design_table": str(
                    artifacts.ratewall_conventional_drag_local_lp_design_table
                ),
                "ratewall_conventional_drag_local_lp_diagnostic_table": str(
                    artifacts.ratewall_conventional_drag_local_lp_diagnostic_table
                ),
                "ratewall_conventional_drag_local_lp_estimate_diagnostic_table": str(
                    artifacts.ratewall_conventional_drag_local_lp_estimate_diagnostic_table
                ),
                "ratewall_conventional_drag_local_lp_robustness_diagnostic_table": str(
                    artifacts.ratewall_conventional_drag_local_lp_robustness_diagnostic_table
                ),
                "ratewall_conventional_drag_local_lp_sample_window_audit_table": str(
                    artifacts.ratewall_conventional_drag_local_lp_sample_window_audit_table
                ),
                "ratewall_conventional_drag_local_lp_admission_audit_table": str(
                    artifacts.ratewall_conventional_drag_local_lp_admission_audit_table
                ),
                "ratewall_tdsp_current_demand_source_review_table": str(
                    artifacts.ratewall_tdsp_current_demand_source_review_table
                ),
                "ratewall_tdsp_current_demand_unit_conversion_table": str(
                    artifacts.ratewall_tdsp_current_demand_unit_conversion_table
                ),
                "ratewall_tdsp_current_demand_diagnostic_mapping_table": str(
                    artifacts.ratewall_tdsp_current_demand_diagnostic_mapping_table
                ),
                "ratewall_tdsp_policy_path_normalization_blocker_table": str(
                    artifacts.ratewall_tdsp_policy_path_normalization_blocker_table
                ),
                "ratewall_tdsp_current_demand_admission_audit_table": str(
                    artifacts.ratewall_tdsp_current_demand_admission_audit_table
                ),
                "ratewall_pce_dpi_source_refresh_contract_table": str(
                    artifacts.ratewall_pce_dpi_source_refresh_contract_table
                ),
                "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping_table": str(
                    artifacts.ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping_table
                ),
                "ratewall_policy_path_exposure_vector_design_gate_table": str(
                    artifacts.ratewall_policy_path_exposure_vector_design_gate_table
                ),
                "ratewall_policy_path_reviewed_protocol_source_context_table": str(
                    artifacts.ratewall_policy_path_reviewed_protocol_source_context_table
                ),
                "ratewall_policy_path_protocol_source_acquisition_registry_table": str(
                    artifacts.ratewall_policy_path_protocol_source_acquisition_registry_table
                ),
                "ratewall_policy_path_protocol_source_acquisition_audit_table": str(
                    artifacts.ratewall_policy_path_protocol_source_acquisition_audit_table
                ),
                "ratewall_policy_path_protocol_review_inventory_table": str(
                    artifacts.ratewall_policy_path_protocol_review_inventory_table
                ),
                "ratewall_policy_path_protocol_review_audit_table": str(
                    artifacts.ratewall_policy_path_protocol_review_audit_table
                ),
                "ratewall_policy_path_mps_scalar_replication_diagnostic_table": str(
                    artifacts.ratewall_policy_path_mps_scalar_replication_diagnostic_table
                ),
                "ratewall_policy_path_mps_scalar_replication_audit_table": str(
                    artifacts.ratewall_policy_path_mps_scalar_replication_audit_table
                ),
                "ratewall_policy_path_bps_year_blocker_decision_table": str(
                    artifacts.ratewall_policy_path_bps_year_blocker_decision_table
                ),
                "ratewall_policy_path_bps_year_blocker_decision_audit_table": str(
                    artifacts.ratewall_policy_path_bps_year_blocker_decision_audit_table
                ),
                "ratewall_policy_path_event_level_candidate_vector_table": str(
                    artifacts.ratewall_policy_path_event_level_candidate_vector_table
                ),
                "ratewall_policy_path_event_level_candidate_vector_audit_table": str(
                    artifacts.ratewall_policy_path_event_level_candidate_vector_audit_table
                ),
                "ratewall_policy_path_contract_interval_source_review_table": str(
                    artifacts.ratewall_policy_path_contract_interval_source_review_table
                ),
                "ratewall_policy_path_contract_spec_acquisition_blocker_table": str(
                    artifacts.ratewall_policy_path_contract_spec_acquisition_blocker_table
                ),
                "ratewall_policy_path_bps_year_source_protocol_table": str(
                    artifacts.ratewall_policy_path_bps_year_source_protocol_table
                ),
                "ratewall_policy_path_normalization_source_manifest_table": str(
                    artifacts.ratewall_policy_path_normalization_source_manifest_table
                ),
                "ratewall_policy_path_bps_year_normalization_review_table": str(
                    artifacts.ratewall_policy_path_bps_year_normalization_review_table
                ),
                "ratewall_policy_path_source_cell_unit_contract_review_table": str(
                    artifacts.ratewall_policy_path_source_cell_unit_contract_review_table
                ),
                "ratewall_policy_path_bps_year_protocol_closure_table": str(
                    artifacts.ratewall_policy_path_bps_year_protocol_closure_table
                ),
                "ratewall_policy_path_normalization_leak_audit_table": str(
                    artifacts.ratewall_policy_path_normalization_leak_audit_table
                ),
                "ratewall_policy_path_reviewed_bps_year_protocol_gap_matrix_table": str(
                    artifacts.ratewall_policy_path_reviewed_bps_year_protocol_gap_matrix_table
                ),
                "ratewall_policy_path_protocol_source_acquisition_work_queue_table": str(
                    artifacts.ratewall_policy_path_protocol_source_acquisition_work_queue_table
                ),
                "ratewall_policy_path_protocol_source_parse_execution_review_table": str(
                    artifacts.ratewall_policy_path_protocol_source_parse_execution_review_table
                ),
                "ratewall_policy_path_source_parse_synthesis_queue_table": str(
                    artifacts.ratewall_policy_path_source_parse_synthesis_queue_table
                ),
                "ratewall_policy_path_source_parse_action_execution_table": str(
                    artifacts.ratewall_policy_path_source_parse_action_execution_table
                ),
                "ratewall_policy_path_deeper_parse_execution_review_table": str(
                    artifacts.ratewall_policy_path_deeper_parse_execution_review_table
                ),
                "ratewall_policy_path_protocol_candidate_draft_review_table": str(
                    artifacts.ratewall_policy_path_protocol_candidate_draft_review_table
                ),
                "ratewall_policy_path_protocol_missing_evidence_acquisition_queue_table": str(
                    artifacts.ratewall_policy_path_protocol_missing_evidence_acquisition_queue_table
                ),
                "ratewall_policy_path_protocol_missing_evidence_parse_execution_review_table": str(
                    artifacts.ratewall_policy_path_protocol_missing_evidence_parse_execution_review_table
                ),
                "ratewall_policy_path_protocol_authoring_readiness_matrix_table": str(
                    artifacts.ratewall_policy_path_protocol_authoring_readiness_matrix_table
                ),
                "ratewall_policy_path_protocol_field_authoring_contract_table": str(
                    artifacts.ratewall_policy_path_protocol_field_authoring_contract_table
                ),
                "ratewall_policy_path_field_evidence_resolution_queue_table": str(
                    artifacts.ratewall_policy_path_field_evidence_resolution_queue_table
                ),
                "ratewall_tdsp_pce_dpi_policy_path_admission_audit_table": str(
                    artifacts.ratewall_tdsp_pce_dpi_policy_path_admission_audit_table
                ),
                "ratewall_interest_channel_horizon_timing_matrix_table": str(
                    artifacts.ratewall_interest_channel_horizon_timing_matrix_table
                ),
                "ratewall_interest_channel_promotion_gate_table": str(
                    artifacts.ratewall_interest_channel_promotion_gate_table
                ),
                "ratewall_interest_channel_evidence_upgrade_queue_table": str(
                    artifacts.ratewall_interest_channel_evidence_upgrade_queue_table
                ),
                "ratewall_high_priority_interest_channel_source_bridge_table": str(
                    artifacts.ratewall_high_priority_interest_channel_source_bridge_table
                ),
                "ratewall_source_gate_prior_narrowing_decision_table": str(
                    artifacts.ratewall_source_gate_prior_narrowing_decision_table
                ),
                "ratewall_source_gate_exhaustion_closure_table": str(
                    artifacts.ratewall_source_gate_exhaustion_closure_table
                ),
                "ratewall_restricted_data_gate_spec_table": str(
                    artifacts.ratewall_restricted_data_gate_spec_table
                ),
                "ratewall_assumption_mode_post_closure_boundary_map_table": str(
                    artifacts.ratewall_assumption_mode_post_closure_boundary_map_table
                ),
                "ratewall_sibling_evidence_bridge_table": str(
                    artifacts.ratewall_sibling_evidence_bridge_table
                ),
                "ratewall_sibling_evidence_upgrade_queue_table": str(
                    artifacts.ratewall_sibling_evidence_upgrade_queue_table
                ),
                "ratewall_interest_channel_module_registry_table": str(
                    artifacts.ratewall_interest_channel_module_registry_table
                ),
                "ratewall_higher_rate_channel_registry_table": str(
                    artifacts.ratewall_higher_rate_channel_registry_table
                ),
                "ratewall_corporate_net_interest_cashflow_bridge_table": str(
                    artifacts.ratewall_corporate_net_interest_cashflow_bridge_table
                ),
                "ratewall_working_capital_cost_channel_diagnostic_table": str(
                    artifacts.ratewall_working_capital_cost_channel_diagnostic_table
                ),
                "ratewall_term_structure_pricing_carry_diagnostic_table": str(
                    artifacts.ratewall_term_structure_pricing_carry_diagnostic_table
                ),
                "ratewall_interest_channel_completion_matrix_table": str(
                    artifacts.ratewall_interest_channel_completion_matrix_table
                ),
                "ratewall_dynamic_scenario_paths_table": str(
                    artifacts.ratewall_dynamic_scenario_paths_table
                ),
                "ratewall_dynamic_scenario_path_consistency_diagnostic_table": str(
                    dynamic_path_consistency_table
                ),
                "ratewall_dynamic_offset_ratio_path_table": str(
                    artifacts.ratewall_dynamic_offset_ratio_path_table
                ),
                "ratewall_scenario_crossing_diagnostic_table": str(
                    artifacts.ratewall_scenario_crossing_diagnostic_table
                ),
                "ratewall_dynamic_sensitivity_frontier_table": str(
                    artifacts.ratewall_dynamic_sensitivity_frontier_table
                ),
                "ratewall_dynamic_scenario_family_registry_table": str(
                    artifacts.ratewall_dynamic_scenario_family_registry_table
                ),
                "ratewall_dynamic_uncertainty_envelope_table": str(
                    artifacts.ratewall_dynamic_uncertainty_envelope_table
                ),
                "ratewall_dynamic_crossing_robustness_table": str(
                    artifacts.ratewall_dynamic_crossing_robustness_table
                ),
                "ratewall_flow_stage_decomposition_table": str(
                    artifacts.ratewall_flow_stage_decomposition_table
                ),
                "ratewall_gross_interest_subchannels_table": str(
                    artifacts.ratewall_gross_interest_subchannels_table
                ),
                "ratewall_public_finance_adjustment_table": str(
                    artifacts.ratewall_public_finance_adjustment_table
                ),
                "ratewall_net_countervailing_channels_table": str(
                    artifacts.ratewall_net_countervailing_channels_table
                ),
                "ratewall_scenario_ladder_table": str(
                    artifacts.ratewall_scenario_ladder_table
                ),
                "ratewall_assumption_mode_driver_dominance_matrix_table": str(
                    artifacts.ratewall_assumption_mode_driver_dominance_matrix_table
                ),
                "ratewall_assumption_mode_pairwise_sensitivity_matrix_table": str(
                    artifacts.ratewall_assumption_mode_pairwise_sensitivity_matrix_table
                ),
                "ratewall_backend_invariant_guardrail_audit_table": str(
                    artifacts.ratewall_backend_invariant_guardrail_audit_table
                ),
                "ratewall_backend_completion_verdict_table": str(
                    artifacts.ratewall_backend_completion_verdict_table
                ),
                "ratewall_paper_channel_map_table": str(
                    artifacts.ratewall_paper_channel_map_table
                ),
                "ratewall_paper_canonical_scenario_results_table": str(
                    artifacts.ratewall_paper_canonical_scenario_results_table
                ),
                "ratewall_paper_tdc_dynamic_contribution_table": str(
                    artifacts.ratewall_paper_tdc_dynamic_contribution_table
                ),
                "ratewall_paper_parameter_justification_table": str(
                    artifacts.ratewall_paper_parameter_justification_table
                ),
                "ratewall_paper_sensitivity_summary_table": str(
                    artifacts.ratewall_paper_sensitivity_summary_table
                ),
                "ratewall_paper_disabled_claims_appendix_table": str(
                    artifacts.ratewall_paper_disabled_claims_appendix_table
                ),
                "ratewall_paper_support_invariant_audit_table": str(
                    artifacts.ratewall_paper_support_invariant_audit_table
                ),
                "ratewall_backend_accounting_identity_audit_table": str(
                    artifacts.ratewall_backend_accounting_identity_audit_table
                ),
                "ratewall_paper_scenario_accounting_bridge_table": str(
                    artifacts.ratewall_paper_scenario_accounting_bridge_table
                ),
                "ratewall_paper_dynamic_scenario_summary_table": str(
                    artifacts.ratewall_paper_dynamic_scenario_summary_table
                ),
                "ratewall_split_denominator_comparison_table": str(
                    artifacts.ratewall_split_denominator_comparison_table
                ),
                "ratewall_denominator_sensitivity_table": str(
                    artifacts.ratewall_denominator_sensitivity_table
                ),
                "ratewall_split_denominator_uncertainty_table": str(
                    artifacts.ratewall_split_denominator_uncertainty_table
                ),
                "ratewall_split_denominator_regime_stability_table": str(
                    artifacts.ratewall_split_denominator_regime_stability_table
                ),
                "ratewall_denominator_literature_matrix_table": str(
                    artifacts.ratewall_denominator_literature_matrix_table
                ),
                "ratewall_split_denominator_joint_uncertainty_table": str(
                    artifacts.ratewall_split_denominator_joint_uncertainty_table
                ),
                "ratewall_split_denominator_joint_regime_stability_table": str(
                    artifacts.ratewall_split_denominator_joint_regime_stability_table
                ),
                "ratewall_denominator_classifier_comparison_table": str(
                    artifacts.ratewall_denominator_classifier_comparison_table
                ),
                "ratewall_backend_model_readiness_gate_table": str(
                    artifacts.ratewall_backend_model_readiness_gate_table
                ),
                "ratewall_chapter_readiness_self_audit_table": str(
                    artifacts.ratewall_chapter_readiness_self_audit_table
                ),
                "ratewall_contractionary_benchmark_calibration_table": str(
                    artifacts.ratewall_contractionary_benchmark_calibration_table
                ),
                "ratewall_threshold_uncertainty_bands_table": str(
                    artifacts.ratewall_threshold_uncertainty_bands_table
                ),
                "ratewall_historical_threshold_validation_table": str(
                    artifacts.ratewall_historical_threshold_validation_table
                ),
                "ratewall_policy_boundary_synthesis_table": str(
                    artifacts.ratewall_policy_boundary_synthesis_table
                ),
                "ratewall_blocker_resolution_ledger_table": str(
                    artifacts.ratewall_blocker_resolution_ledger_table
                ),
                "ratewall_publication_claim_decision_table": str(
                    artifacts.ratewall_publication_claim_decision_table
                ),
                "ratewall_final_blocker_ledger_table": str(
                    artifacts.ratewall_final_blocker_ledger_table
                ),
                "ratewall_release_16_source_resolution_closeout_table": str(
                    artifacts.ratewall_release_16_source_resolution_closeout_table
                ),
                "ratewall_release_16_no_further_promotion_ledger_table": str(
                    artifacts.ratewall_release_16_no_further_promotion_ledger_table
                ),
                "ratewall_release_17_external_review_audit_table": str(
                    artifacts.ratewall_release_17_external_review_audit_table
                ),
                "ratewall_release_17_publication_polish_qa_table": str(
                    artifacts.ratewall_release_17_publication_polish_qa_table
                ),
                "ratewall_release_17_blocker_reopen_decision_table": str(
                    artifacts.ratewall_release_17_blocker_reopen_decision_table
                ),
                "ratewall_release_18_live_refresh_robustness_audit_table": str(
                    artifacts.ratewall_release_18_live_refresh_robustness_audit_table
                ),
                "financialization_pressure_table": str(
                    artifacts.financialization_pressure_table
                ),
                "financialization_pressure_evidence_appendix_table": str(
                    artifacts.financialization_pressure_evidence_appendix_table
                ),
                "safe_asset_retention_context_table": str(
                    artifacts.safe_asset_retention_context_table
                ),
                "safe_asset_retention_evidence_appendix_table": str(
                    artifacts.safe_asset_retention_evidence_appendix_table
                ),
                "buyer_case_sign_matrix_table": str(
                    artifacts.buyer_case_sign_matrix_table
                ),
                "recipient_mpc_scenario_scaffold_table": str(
                    artifacts.recipient_mpc_scenario_scaffold_table
                ),
                "release_19_accounting_invariant_audit_table": str(
                    artifacts.release_19_accounting_invariant_audit_table
                ),
                "release_19_post_audit_methodology_audit_table": str(
                    artifacts.release_19_post_audit_methodology_audit_table
                ),
                "release_20_activity_demand_benchmark_table": str(
                    artifacts.release_20_activity_demand_benchmark_table
                ),
                "release_20_state_dependent_lp_diagnostics_table": str(
                    artifacts.release_20_state_dependent_lp_diagnostics_table
                ),
                "release_20_benchmark_submission_decision_table": str(
                    artifacts.release_20_benchmark_submission_decision_table
                ),
                "release_21_live_refresh_endpoint_audit_table": str(
                    artifacts.release_21_live_refresh_endpoint_audit_table
                ),
                "release_21_final_benchmark_gate_table": str(
                    artifacts.release_21_final_benchmark_gate_table
                ),
                "release_21_backend_invariant_audit_table": str(
                    artifacts.release_21_backend_invariant_audit_table
                ),
                "ratewall_threshold_claim_boundary_audit_table": str(
                    artifacts.ratewall_threshold_claim_boundary_audit_table
                ),
                "tdc_source_coverage_table": str(artifacts.tdc_source_coverage_table),
                "tdc_claim_boundary_audit_table": str(
                    artifacts.tdc_claim_boundary_audit_table
                ),
                "tdc_deposit_channel_appendix": str(
                    artifacts.tdc_deposit_channel_appendix
                ),
                "evidence_limitations_table": str(artifacts.evidence_limitations_table),
                "ratewall_dashboard_table": str(artifacts.ratewall_dashboard_table),
                "paper_support_report": str(artifacts.paper_support_report),
                "provenance": str(artifacts.provenance),
                "impulse_figure": str(artifacts.impulse_figure),
                "metric_figures": [str(path) for path in artifacts.metric_figures],
            }
    if not full:
        payload = _filter_existing_artifact_payload(payload)
        payload["output_policy"] = {
            "forbid_extra_default_tables": args.forbid_extra_default_tables,
            "include_frozen": args.include_frozen,
            "mode": "keeper",
        }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_scenarios_build(args: argparse.Namespace) -> int:
    output = build_scenario_table(
        snapshot_bundle=args.snapshot,
        output=args.output,
    )
    print(str(output))
    return 0


def _cmd_empirical_specs(args: argparse.Namespace) -> int:
    output = write_empirical_specs(args.output)
    print(str(output))
    return 0


def _cmd_empirical_shocks(args: argparse.Namespace) -> int:
    output = write_shock_dataset_catalog(args.output)
    print(str(output))
    return 0


def _cmd_empirical_smoke(args: argparse.Namespace) -> int:
    output = write_empirical_smoke_panel(
        snapshot_bundle=args.snapshot,
        output=args.output,
    )
    print(str(output))
    return 0


def _cmd_empirical_results(args: argparse.Namespace) -> int:
    output = write_empirical_results(
        snapshot_bundle=args.snapshot,
        output=args.output,
        outcome_panel=args.outcome_panel,
        figure=args.figure,
        report=args.report,
        final_paper_support=args.final_paper_support,
        paper_support=args.paper_support,
    )
    print(str(output))
    return 0


def _cmd_release_build(args: argparse.Namespace) -> int:
    if args.rebuild_databook != "none":
        build_databook(
            snapshot_bundle=args.snapshot,
            output_dir=args.output_dir,
            full=args.rebuild_databook == "full",
        )
        if args.rebuild_databook == "default":
            apply_default_table_output_policy(args.output_dir)
            refresh_build_census_written_tables(args.output_dir)
    artifacts = build_release_package(
        snapshot_bundle=args.snapshot,
        output_dir=args.output_dir,
    )
    apply_default_table_output_policy(
        args.output_dir,
        extra_allowed_names=RELEASE_VALIDATION_TABLE_NAMES,
    )
    print(
        json.dumps(
            {
                "final_paper": str(artifacts.final_paper),
                "final_paper_quarto": str(artifacts.final_paper_quarto),
                "slide_deck": str(artifacts.slide_deck),
                "slide_deck_quarto": str(artifacts.slide_deck_quarto),
                "release_manifest": str(artifacts.release_manifest),
                "claim_audit": str(artifacts.claim_audit),
                "source_appendix": str(artifacts.source_appendix),
                "empirical_appendix": str(artifacts.empirical_appendix),
                "limitations_appendix": str(artifacts.limitations_appendix),
                "validation_package": str(artifacts.validation_package),
                "public_readme": str(artifacts.public_readme),
                "release_index": str(artifacts.release_index),
                "reproduction_commands": str(artifacts.reproduction_commands),
                "public_release_checklist": str(artifacts.public_release_checklist),
                "publication_claim_decision_memo": str(
                    artifacts.publication_claim_decision_memo
                ),
                "release_16_bounded_publication_closeout_memo": str(
                    artifacts.release_16_bounded_publication_closeout_memo
                ),
                "release_16_reviewer_blocker_text": str(
                    artifacts.release_16_reviewer_blocker_text
                ),
                "release_17_external_review_packet": str(
                    artifacts.release_17_external_review_packet
                ),
                "release_17_publication_polish_memo": str(
                    artifacts.release_17_publication_polish_memo
                ),
                "release_18_publication_freeze_memo": str(
                    artifacts.release_18_publication_freeze_memo
                ),
                "release_19_post_audit_methodology_memo": str(
                    artifacts.release_19_post_audit_methodology_memo
                ),
                "release_20_submission_readiness_memo": str(
                    artifacts.release_20_submission_readiness_memo
                ),
                "release_21_backend_closeout_memo": str(
                    artifacts.release_21_backend_closeout_memo
                ),
                "release_22_backend_fix_memo": str(
                    artifacts.release_22_backend_fix_memo
                ),
                "release_23_backend_fix_memo": str(
                    artifacts.release_23_backend_fix_memo
                ),
                "release_23_reproducibility_manifest": str(
                    artifacts.release_23_reproducibility_manifest
                ),
                "release_23_archive_verification_audit": str(
                    artifacts.release_23_archive_verification_audit
                ),
                "figure_plate": str(artifacts.figure_plate),
                "table_plate": str(artifacts.table_plate),
                "archival_manifest": str(artifacts.archival_manifest),
                "source_archive": str(artifacts.source_archive),
                "citation_metadata": str(artifacts.citation_metadata),
                "package_smoke": str(artifacts.package_smoke),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ratewall")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="path to the source registry YAML",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sources = subparsers.add_parser("sources")
    sources_sub = sources.add_subparsers(dest="sources_command", required=True)
    list_parser = sources_sub.add_parser("list")
    list_parser.set_defaults(func=_cmd_sources_list)
    show_parser = sources_sub.add_parser("show")
    show_parser.add_argument("source")
    show_parser.set_defaults(func=_cmd_sources_show)

    data = subparsers.add_parser("data")
    data_sub = data.add_subparsers(dest="data_command", required=True)
    pull_parser = data_sub.add_parser("pull")
    pull_parser.add_argument("--source", required=True)
    pull_parser.add_argument("--series", required=True)
    pull_parser.set_defaults(func=_cmd_data_pull)
    snapshot_parser = data_sub.add_parser("snapshot")
    snapshot_parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    snapshot_parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/ratewall_snapshot.json"),
    )
    snapshot_parser.add_argument(
        "--series",
        action="append",
        help="limit the snapshot bundle to one series id; repeat for multiple series",
    )
    snapshot_parser.set_defaults(func=_cmd_data_snapshot)

    impulse = subparsers.add_parser("impulse")
    impulse.add_argument("--bps", type=_decimal_arg, default=Decimal("100"))
    impulse.add_argument("--snapshot", type=Path)
    impulse.add_argument("--horizon", default="1y")
    impulse.add_argument("--months", type=_decimal_arg, default=Decimal("12"))
    impulse.add_argument("--debt-repricing", type=_decimal_arg)
    impulse.add_argument("--reserves", type=_decimal_arg)
    impulse.add_argument("--on-rrp", type=_decimal_arg)
    impulse.add_argument("--gdp", type=_decimal_arg)
    impulse.add_argument(
        "--fed-remittance-offset",
        type=_decimal_arg,
        default=Decimal("1"),
        help="share of extra Fed interest payments that lowers remittances",
    )
    impulse.set_defaults(func=_cmd_impulse)

    databook = subparsers.add_parser("databook")
    databook_sub = databook.add_subparsers(dest="databook_command", required=True)
    databook_build = databook_sub.add_parser("build")
    databook_build.add_argument(
        "--snapshot",
        type=Path,
        default=Path("data/raw/ratewall_snapshot.json"),
    )
    databook_build.add_argument("--output-dir", type=Path, default=Path("outputs"))
    databook_build.add_argument(
        "--full",
        action="store_true",
        help="build the complete databook table surface",
    )
    databook_build.add_argument(
        "--legacy-full",
        action="store_true",
        help="deprecated alias for --full",
    )
    databook_build.add_argument(
        "--include-frozen",
        action="store_true",
        help="retain freeze-manifest tables in default spine-only output mode",
    )
    databook_build.add_argument(
        "--forbid-extra-default-tables",
        action="store_true",
        help="fail if default mode leaves non-keeper tables or misses keepers",
    )
    databook_build.set_defaults(func=_cmd_databook_build)

    scenarios = subparsers.add_parser("scenarios")
    scenarios_sub = scenarios.add_subparsers(dest="scenarios_command", required=True)
    scenarios_build = scenarios_sub.add_parser("build")
    scenarios_build.add_argument(
        "--snapshot",
        type=Path,
        default=Path("data/raw/ratewall_snapshot.json"),
    )
    scenarios_build.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/tables/ratewall_scenarios.csv"),
    )
    scenarios_build.set_defaults(func=_cmd_scenarios_build)

    empirical = subparsers.add_parser("empirical")
    empirical_sub = empirical.add_subparsers(dest="empirical_command", required=True)
    empirical_specs = empirical_sub.add_parser("specs")
    empirical_specs.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/empirical/local_projection_specs.json"),
    )
    empirical_specs.set_defaults(func=_cmd_empirical_specs)
    empirical_shocks = empirical_sub.add_parser("shocks")
    empirical_shocks.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/empirical/monetary_shock_datasets.json"),
    )
    empirical_shocks.set_defaults(func=_cmd_empirical_shocks)
    empirical_smoke = empirical_sub.add_parser("smoke")
    empirical_smoke.add_argument(
        "--snapshot",
        type=Path,
        default=Path("data/raw/ratewall_snapshot.json"),
    )
    empirical_smoke.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/tables/empirical_smoke_panel.csv"),
    )
    empirical_smoke.set_defaults(func=_cmd_empirical_smoke)
    empirical_results = empirical_sub.add_parser("results")
    empirical_results.add_argument(
        "--snapshot",
        type=Path,
        default=Path("data/raw/ratewall_snapshot.json"),
    )
    empirical_results.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/tables/ratewall_empirical_results.csv"),
    )
    empirical_results.add_argument(
        "--outcome-panel",
        type=Path,
        default=Path("outputs/tables/ratewall_empirical_outcome_panel.csv"),
    )
    empirical_results.add_argument(
        "--figure",
        type=Path,
        default=Path("outputs/figures/ratewall_empirical_state_association.svg"),
    )
    empirical_results.add_argument(
        "--report",
        type=Path,
        default=Path("outputs/reports/ratewall_empirical_results_summary.md"),
    )
    empirical_results.add_argument(
        "--final-paper-support",
        type=Path,
        default=Path("outputs/reports/ratewall_final_paper_support.md"),
    )
    empirical_results.add_argument(
        "--paper-support",
        type=Path,
        default=Path("outputs/reports/ratewall_paper_support_packet.md"),
    )
    empirical_results.set_defaults(func=_cmd_empirical_results)

    release = subparsers.add_parser("release")
    release_sub = release.add_subparsers(dest="release_command", required=True)
    release_build = release_sub.add_parser("build")
    release_build.add_argument(
        "--snapshot",
        type=Path,
        default=Path("data/raw/ratewall_snapshot.json"),
    )
    release_build.add_argument("--output-dir", type=Path, default=Path("outputs"))
    release_build.add_argument(
        "--rebuild-databook",
        choices=RELEASE_DATABOOK_REBUILD_MODES,
        default="none",
        help=(
            "optionally rebuild databook outputs before packaging; "
            "`full` is expensive and intentionally opt-in"
        ),
    )
    release_build.set_defaults(func=_cmd_release_build)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
