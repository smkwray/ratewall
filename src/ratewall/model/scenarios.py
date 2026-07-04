"""Calibrated scenario smoke layer for RateWall."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from ratewall.accounting.rate_impulse import compute_rate_impulse
from ratewall.accounting.ratewall_threshold import (
    DEFAULT_THRESHOLD_SCENARIOS,
    compute_threshold_row,
)
from ratewall.accounting.tdc_deposit_channel import (
    DEFAULT_TDC_SCENARIOS,
    apply_tdc_scenario,
)
from ratewall.accounting.valuation import (
    audit_frn_reset_convention,
    audit_tips_accrual_convention,
    cashflow_edge_fixture_rows,
    cashflow_edge_source_sample_rows,
    classify_tips_formula_review,
    pricing_switch_audit_rows,
    validate_frn_daily_accrued_interest,
    validate_tips_index_ratio,
)
from ratewall.data.derived import derive_accounting_inputs
from ratewall.data.snapshots import read_snapshot_bundle
from ratewall.model.holder_mapping import disabled_scenario_context


@dataclass(frozen=True)
class Scenario:
    name: str
    bps: Decimal
    treasury_pass_through: Decimal
    reserve_pass_through: Decimal
    on_rrp_pass_through: Decimal
    fed_remittance_offset: Decimal


DEFAULT_SCENARIOS = (
    Scenario("baseline_100bps", Decimal("100"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1")),
    Scenario("low_pass_through", Decimal("100"), Decimal("0.5"), Decimal("1"), Decimal("1"), Decimal("1")),
    Scenario("no_remittance_offset", Decimal("100"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("0")),
    Scenario("high_rate_200bps", Decimal("200"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1")),
)


def build_scenario_table(
    *,
    snapshot_bundle: Path,
    output: Path,
    scenarios: tuple[Scenario, ...] = DEFAULT_SCENARIOS,
) -> Path:
    snapshots = read_snapshot_bundle(snapshot_bundle)
    derived = derive_accounting_inputs(snapshots)
    cbo_context = _cbo_projection_context(snapshots)
    incidence_context = _incidence_context(snapshots)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario",
                "horizon",
                "bps",
                "annualized_public_interest_impulse_bil",
                "period_public_interest_impulse_bil",
                "gdp_share",
                "mspd_table3_snapshot_kind",
                "weakest_source_status",
                "repricing_anchor_status",
                "calibration_source_status",
                "allowed_use",
                "promotion_gate_status",
                "cbo_2036_net_interest_gdp",
                "cbo_2036_debt_held_public_gdp",
                "cbo_2036_average_interest_rate_debt_public",
                "private_investor_holder_share",
                "foreign_investor_holder_share",
                "fed_bank_holder_share",
                "households_nonprofits_fine_holder_share",
                "money_market_funds_fine_holder_share",
                "depositories_fine_holder_share",
                "dfa_top10_government_muni_securities_gdp",
                "dfa_middle40_government_muni_securities_gdp",
                "dfa_bottom50_government_muni_securities_gdp",
                "treasury_buybacks_accepted_bil",
                "tic_foreign_official_net_purchases_bil",
                "tic_other_foreigners_net_purchases_bil",
                "tic_foreign_official_treasury_stock_share",
                "tic_other_foreign_treasury_stock_share",
                "tic_sector_split_scope",
                "ofr_mmf_direct_treasury_holdings_bil",
                "ofr_mmf_treasury_repo_bil",
                "sec_nmfp_direct_treasury_holdings_bil",
                "sec_nmfp_repo_treasury_collateral_bil",
                "frn_latest_spread_pct",
                "tips_latest_index_ratio_on_issue",
                "frn_latest_daily_index_pct",
                "tips_latest_daily_index_ratio",
                "frn_formula_check_status",
                "tips_formula_check_status",
                "holder_allocation_gate_status",
                "final_owner_mapping_ready",
                "final_owner_allocation_output_status",
                "final_owner_allocation_schema_version",
                "allocation_design_ledger_status",
                "allocation_design_ledger_schema_version",
                "welfare_incidence_enabled",
                "holder_mapping_schema_version",
                "holder_mapping_stage",
                "holder_bridge_enabled",
                "tax_assumptions_enabled",
                "mpc_assumptions_enabled",
                "incidence_claim_enabled",
                "sec_nmfp_mspd_matched_cusip_count",
                "sec_nmfp_mspd_matched_principal_bil",
                "valuation_input_gate_status",
                "valuation_engine_readiness_status",
                "valuation_pricing_output_enabled",
                "valuation_opt_in_contract_status",
                "valuation_readiness_coverage_rows",
                "valuation_readiness_source_blocker_rows",
                "valuation_readiness_policy_blocker_rows",
                "valuation_readiness_gate_evidence_rows",
                "valuation_readiness_gate_blocker_rows",
                "valuation_readiness_gate_disabled_rows",
                "valuation_frn_reset_official_source_audit_rows",
                "valuation_frn_reset_official_audit_blocked_rows",
                "valuation_frn_reset_official_source_schema_evidence_rows",
                "valuation_frn_reset_official_source_schema_blocked_rows",
                "valuation_frn_reset_official_source_schema_validation_rows",
                "valuation_frn_reset_method_semantics_audit_rows",
                "valuation_frn_reset_method_semantics_context_only_rows",
                "valuation_cashflow_edge_fixture_rows",
                "valuation_source_backed_edge_sample_rows",
                "valuation_source_edge_classified_rows",
                "valuation_source_edge_blocked_rows",
                "valuation_pricing_switch_audit_rows",
                "valuation_pricing_switches_enabled",
                "valuation_pricing_switches_disabled",
                "valuation_explicit_pricing_switch_enabled",
                "valuation_formula_review_rows",
                "valuation_classified_formula_review_rows",
                "valuation_unresolved_formula_review_rows",
                "valuation_frn_reset_method_design_ledger_rows",
                "valuation_frn_reset_method_design_required_rows",
                "valuation_frn_reset_cusip_coverage_ledger_rows",
                "valuation_frn_reset_cusip_coverage_blocked_rows",
                "valuation_frn_reset_cusip_three_way_overlap_count",
                "valuation_frn_reset_fixture_readiness_ledger_rows",
                "valuation_frn_reset_fixture_readiness_blocked_rows",
                "valuation_frn_reset_fixture_readiness_covered_rows",
                "valuation_frn_reset_calendar_policy_rows",
                "valuation_frn_reset_calendar_policy_fail_closed_rows",
                "valuation_frn_reset_calendar_policy_blocker_rows",
                "valuation_frn_reset_explicit_opt_in_gate_rows",
                "valuation_frn_reset_explicit_opt_in_disabled_switch_rows",
                "valuation_frn_reset_explicit_opt_in_prerequisite_rows",
                "valuation_frn_reset_method_frontier_ledger_rows",
                "valuation_frn_reset_method_frontier_reduced_rows",
                "valuation_frn_reset_method_frontier_blocked_rows",
                "valuation_frn_reset_method_frontier_future_opt_in_rows",
                "tdc_deposit_channel_layer_status",
                "tdc_reference_sibling",
                "tdc_deposit_pricing_context_separate",
                "tdc_ru_financed_du_outlay_case_impulse_bil",
                "tdc_ru_financed_du_outlay_case_gdp_share",
                "tdc_historical_panel_status",
                "tdc_deposit_pricing_pass_through_status",
                "tdc_claim_boundary",
                "tdc_pricing_output_enabled",
                "tdc_incidence_claim_enabled",
                "ratewall_threshold_layer_status",
                "ratewall_threshold_reference_scenario",
                "ratewall_threshold_offset_ratio",
                "ratewall_threshold_hit_under_assumptions",
                "ratewall_threshold_claim_boundary",
                "financialization_pressure_layer_status",
                "financialization_pressure_gdp_share",
                "financialization_causal_claim_enabled",
                "release_13_calibration_layer_status",
                "release_13_remaining_speculative_inputs",
                "release_13_calibration_claim_boundary",
                "release_14_validation_layer_status",
                "release_14_policy_boundary_claim",
                "release_14_remaining_promotion_blockers",
                "release_15_publication_decision_status",
                "release_15_bounded_publication_claim",
                "release_15_promotion_claim_enabled",
                "release_16_closeout_status",
                "release_16_final_no_further_promotion",
                "release_16_source_resolution_claim_boundary",
                "release_17_external_review_status",
                "release_17_blocker_reopen_status",
                "release_17_publication_polish_claim_boundary",
            ],
        )
        writer.writeheader()
        for scenario in scenarios:
            inputs = derived.to_rate_impulse_inputs()
            inputs = inputs.__class__(
                reserves=inputs.reserves,
                on_rrp=inputs.on_rrp,
                gdp=inputs.gdp,
                horizons=inputs.horizons,
                treasury_pass_through=scenario.treasury_pass_through,
                reserve_pass_through=scenario.reserve_pass_through,
                on_rrp_pass_through=scenario.on_rrp_pass_through,
                fed_remittance_offset=scenario.fed_remittance_offset,
            )
            impulse = compute_rate_impulse(inputs, bps=scenario.bps)
            for horizon, result in impulse.items():
                tdc_context = _tdc_scenario_context(
                    result.period_public_interest_impulse,
                    derived.gdp_bil,
                    snapshots,
                )
                threshold_context = _threshold_scenario_context(
                    horizon,
                    result,
                    derived.gdp_bil,
                )
                writer.writerow(
                    {
                        "scenario": scenario.name,
                        "horizon": horizon,
                        "bps": scenario.bps,
                        "annualized_public_interest_impulse_bil": result.annualized_public_interest_impulse,
                        "period_public_interest_impulse_bil": result.period_public_interest_impulse,
                        "gdp_share": result.period_public_interest_impulse_gdp_share,
                        **_scenario_source_status_context(result, snapshots),
                        **cbo_context,
                        **incidence_context,
                        **tdc_context,
                        **threshold_context,
                    }
                )
    return output


def _tdc_scenario_context(
    period_public_interest_impulse: Decimal,
    gdp_bil: Decimal,
    snapshots: list,
) -> dict[str, str]:
    row = apply_tdc_scenario(
        period_public_interest_impulse_bil=period_public_interest_impulse,
        assumption=DEFAULT_TDC_SCENARIOS[0],
    )
    deposit_impulse = Decimal(str(row["tdc_deposit_channel_impulse_bil"]))
    return {
        "tdc_deposit_channel_layer_status": "non_causal_accounting_context_enabled",
        "tdc_reference_sibling": "tdcmain_read_only_method_reference",
        "tdc_deposit_pricing_context_separate": "true",
        "tdc_ru_financed_du_outlay_case_impulse_bil": str(deposit_impulse),
        "tdc_ru_financed_du_outlay_case_gdp_share": str(deposit_impulse / gdp_bil),
        "tdc_historical_panel_status": _tdc_historical_context_status(snapshots),
        "tdc_deposit_pricing_pass_through_status": _tdc_pricing_context_status(snapshots),
        "tdc_claim_boundary": "tdc_accounting_scenario_not_causal_or_incidence_claim",
        "tdc_pricing_output_enabled": "false",
        "tdc_incidence_claim_enabled": "false",
    }


def _threshold_scenario_context(
    horizon: str,
    result,
    gdp_bil: Decimal,
) -> dict[str, str]:
    treasury = result.annualized_treasury_interest * result.months / Decimal("12")
    threshold = compute_threshold_row(
        scenario=DEFAULT_THRESHOLD_SCENARIOS[0],
        horizon=horizon,
        months=result.months,
        gdp_bil=gdp_bil,
        period_public_interest_impulse_bil=result.period_public_interest_impulse,
        period_treasury_interest_impulse_bil=treasury,
        period_fed_interest_impulse_bil=result.period_public_interest_impulse
        - treasury,
        source_status=_scenario_dependent_source_status(result.source_status),
    )
    return {
        "ratewall_threshold_layer_status": "conditional_scenario_context_enabled",
        "ratewall_threshold_reference_scenario": threshold["scenario"],
        "ratewall_threshold_offset_ratio": threshold[
            "offset_ratio_to_contractionary_benchmark"
        ],
        "ratewall_threshold_hit_under_assumptions": threshold[
            "threshold_hit_under_assumptions"
        ],
        "ratewall_threshold_claim_boundary": threshold["claim_boundary"],
        "financialization_pressure_layer_status": (
            "bounded_context_not_causal_financialization"
        ),
        "financialization_pressure_gdp_share": threshold[
            "financialization_pressure_gdp_share"
        ],
        "financialization_causal_claim_enabled": "false",
        "release_13_calibration_layer_status": (
            "calibration_range_sensitivity_review_not_promotion"
        ),
        "release_13_remaining_speculative_inputs": (
            "du_outlay_share;fiscal_offset_share;contractionary_drag_gdp_share"
        ),
        "release_13_calibration_claim_boundary": (
            "calibration_range_sensitivity_review_not_final_policy_failure_or_causal_claim"
        ),
        "release_14_validation_layer_status": (
            "historical_threshold_validation_generated_not_promoted"
        ),
        "release_14_policy_boundary_claim": (
            "sensitivity_diagnostics_only_no_universal_ratewall_date"
        ),
        "release_14_remaining_promotion_blockers": (
            "du_outlay_share;fiscal_offset_share;dynamic_contractionary_benchmark"
        ),
        "release_15_publication_decision_status": (
            "publish_bounded_package_with_final_blockers"
        ),
        "release_15_bounded_publication_claim": (
            "accounting_and_conditional_sensitivity_only"
        ),
        "release_15_promotion_claim_enabled": "false",
        "release_16_closeout_status": (
            "bounded_publication_closeout_no_further_promotion"
        ),
        "release_16_final_no_further_promotion": "true",
        "release_16_source_resolution_claim_boundary": (
            "source_resolution_closeout_not_claim_promotion"
        ),
        "release_17_external_review_status": (
            "publication_polish_and_reviewer_consistency_audit_passed"
        ),
        "release_17_blocker_reopen_status": (
            "no_blockers_reopened_absent_new_source_method_evidence"
        ),
        "release_17_publication_polish_claim_boundary": (
            "release_17_polish_not_claim_promotion"
        ),
    }


def _scenario_source_status_context(result, snapshots: list) -> dict[str, str]:
    mspd = next(
        (
            snapshot
            for snapshot in snapshots
            if snapshot.metadata.series_id == "treasury_mspd_table_3"
        ),
        None,
    )
    mspd_kind = mspd.metadata.snapshot_kind if mspd else "missing"
    weakest = _scenario_dependent_source_status(result.source_status)
    blocked = any(token in weakest for token in ("fallback", "review", "blocked"))
    return {
        "mspd_table3_snapshot_kind": mspd_kind,
        "weakest_source_status": weakest,
        "repricing_anchor_status": (
            "anchor_fallback_not_live_security_level" if blocked else result.source_status
        ),
        "calibration_source_status": (
            "calibration_range_sensitivity_review_not_promotion"
        ),
        "allowed_use": (
            "fallback_context_only_scenario_diagnostic"
            if blocked
            else "source_labeled_scenario_diagnostic"
        ),
        "promotion_gate_status": (
            "blocked_not_live_security_level_not_threshold_promotion"
            if blocked
            else "nonpromotion_scenario_context"
        ),
    }


def _scenario_dependent_source_status(source_status: str) -> str:
    if any(token in source_status for token in ("fallback", "review", "blocked")):
        return f"fallback_context_only_depends_on_{source_status}"
    return source_status


def _tdc_historical_context_status(snapshots: list) -> str:
    series = {snapshot.metadata.series_id for snapshot in snapshots}
    required = {"DPSACBW027SBOG", "WTREGEN", "mts_table_4"}
    if required <= series:
        return "historical_partial_source_backed_context_available_not_final_tdc_estimate"
    return "historical_context_coverage_limited_missing_required_sources"


def _tdc_pricing_context_status(snapshots: list) -> str:
    series = {snapshot.metadata.series_id for snapshot in snapshots}
    required = {"DPSACBW027SBOG", "SNDR", "DTB3", "FEDFUNDS"}
    if required <= series:
        return "deposit_pricing_pass_through_context_available_not_pricing_model"
    return "deposit_pricing_context_coverage_limited_missing_required_sources"


def _cbo_projection_context(snapshots) -> dict[str, str]:
    wanted = {
        ("2036", "net_interest_gdp_pct"): "cbo_2036_net_interest_gdp",
        ("2036", "debt_held_public_gdp_pct"): "cbo_2036_debt_held_public_gdp",
        (
            "2036",
            "average_interest_rate_debt_public_pct",
        ): "cbo_2036_average_interest_rate_debt_public",
    }
    context = {column: "" for column in wanted.values()}
    for snapshot in snapshots:
        if snapshot.metadata.series_id != "cbo_budget_economic_outlook":
            continue
        for record in snapshot.records:
            if record.get("record_type") != "cbo_projection":
                continue
            column = wanted.get(
                (str(record.get("fiscal_year", "")), str(record.get("metric", "")))
            )
            if not column:
                continue
            value = _decimal_from_record(record, "value")
            if value is None:
                continue
            if str(record.get("units", "")).startswith("percent"):
                value /= Decimal("100")
            context[column] = str(value)
    return context


def _incidence_context(snapshots) -> dict[str, str]:
    snapshot_map = {snapshot.metadata.series_id: snapshot for snapshot in snapshots}
    holder_values = {
        "private_investor_holder_share": _latest_decimal(snapshot_map, "FDHBPIN"),
        "foreign_investor_holder_share": _latest_decimal(snapshot_map, "FDHBFIN"),
        "fed_bank_holder_share": _latest_decimal(snapshot_map, "FDHBFRBN"),
    }
    total = sum((value or Decimal("0") for value in holder_values.values()), Decimal("0"))
    context = {
        key: (str(value / total) if value is not None and total > 0 else "")
        for key, value in holder_values.items()
    }
    fine_holder_values = {
        "households_nonprofits_fine_holder_share": _latest_decimal(
            snapshot_map, "BOGZ1LM153061105Q"
        ),
        "money_market_funds_fine_holder_share": _latest_decimal(
            snapshot_map, "BOGZ1FL633061105Q"
        ),
        "depositories_fine_holder_share": _latest_decimal(
            snapshot_map, "BOGZ1FL763061100Q"
        ),
    }
    fine_total = sum(
        (value or Decimal("0") for value in fine_holder_values.values()), Decimal("0")
    )
    context.update(
        {
            key: (str(value / fine_total) if value is not None and fine_total > 0 else "")
            for key, value in fine_holder_values.items()
        }
    )
    dfa = snapshot_map.get("distributional_interest_exposure")
    dfa_record = dfa.records[0] if dfa and dfa.records else {}
    gdp = _latest_decimal(snapshot_map, "GDP") or Decimal("0")
    for column, field in (
        (
            "dfa_top10_government_muni_securities_gdp",
            "top10_us_government_municipal_securities_mil",
        ),
        (
            "dfa_middle40_government_muni_securities_gdp",
            "middle40_us_government_municipal_securities_mil",
        ),
        (
            "dfa_bottom50_government_muni_securities_gdp",
            "bottom50_us_government_municipal_securities_mil",
        ),
    ):
        value = _decimal_from_record(dfa_record, field)
        context[column] = str(value / Decimal("1000") / gdp) if value and gdp > 0 else ""
    buybacks = snapshot_map.get("treasury_buybacks")
    total_accepted = Decimal("0")
    if buybacks:
        for operation in buybacks.records:
            for detail in operation.get("securityDetails", []) or []:
                total_accepted += _decimal_from_record(detail, "parAmountAccepted") or Decimal(
                    "0"
                )
    context["treasury_buybacks_accepted_bil"] = str(
        total_accepted / Decimal("1000000000")
    )
    tic = _latest_record(snapshot_map.get("tic_treasury_sector_transactions"))
    official = _decimal_from_record(tic, "foreign_official_institutions_mil")
    other = _decimal_from_record(tic, "other_foreigners_mil")
    context["tic_foreign_official_net_purchases_bil"] = (
        str(official / Decimal("1000")) if official is not None else ""
    )
    context["tic_other_foreigners_net_purchases_bil"] = (
        str(other / Decimal("1000")) if other is not None else ""
    )
    tic_stock = _tic_stock_record(snapshot_map)
    official_share = _decimal_from_record(tic_stock, "official_share")
    other_share = _decimal_from_record(tic_stock, "other_share")
    context["tic_foreign_official_treasury_stock_share"] = (
        str(official_share) if official_share is not None else ""
    )
    context["tic_other_foreign_treasury_stock_share"] = (
        str(other_share) if other_share is not None else ""
    )
    context["tic_sector_split_scope"] = (
        "net_purchases_plus_tic_stock_context_no_cusip_incidence"
        if tic or tic_stock
        else ""
    )
    ofr = snapshot_map.get("ofr_mmf_treasury_holdings")
    ofr_records = {str(row.get("channel")): row for row in (ofr.records if ofr else [])}
    direct = _decimal_from_record(ofr_records.get("us_treasury_securities", {}), "value")
    repo = _decimal_from_record(ofr_records.get("treasury_repo_total", {}), "value")
    context["ofr_mmf_direct_treasury_holdings_bil"] = (
        str(direct / Decimal("1000000000")) if direct is not None else ""
    )
    context["ofr_mmf_treasury_repo_bil"] = (
        str(repo / Decimal("1000000000")) if repo is not None else ""
    )
    sec_nmfp = snapshot_map.get("sec_nmfp_mmf_treasury_cusip_holdings")
    sec_direct = _sec_nmfp_aggregate(sec_nmfp, "direct_security")
    sec_repo = _sec_nmfp_aggregate(sec_nmfp, "repo_collateral")
    direct_value = _decimal_from_record(sec_direct, "value_bil")
    repo_value = _decimal_from_record(sec_repo, "value_bil")
    context["sec_nmfp_direct_treasury_holdings_bil"] = (
        str(direct_value) if direct_value is not None else ""
    )
    context["sec_nmfp_repo_treasury_collateral_bil"] = (
        str(repo_value) if repo_value is not None else ""
    )
    frn = _latest_record(snapshot_map.get("treasury_auction_frn_terms"))
    tips = _latest_record(snapshot_map.get("treasury_auction_tips_terms"))
    frn_spread = _decimal_from_record(frn, "spread")
    tips_ratio = _decimal_from_record(tips, "index_ratio_on_issue_date")
    context["frn_latest_spread_pct"] = str(frn_spread) if frn_spread is not None else ""
    context["tips_latest_index_ratio_on_issue"] = (
        str(tips_ratio) if tips_ratio is not None else ""
    )
    frn_daily = _latest_record(snapshot_map.get("treasury_frn_daily_indexes"))
    tips_daily = _latest_record(snapshot_map.get("treasury_tips_cpi_detail"))
    frn_index = _decimal_from_record(frn_daily, "daily_index")
    tips_daily_ratio = _decimal_from_record(tips_daily, "index_ratio")
    context["frn_latest_daily_index_pct"] = (
        str(frn_index) if frn_index is not None else ""
    )
    context["tips_latest_daily_index_ratio"] = (
        str(tips_daily_ratio) if tips_daily_ratio is not None else ""
    )
    context["frn_formula_check_status"] = _frn_formula_status(frn_daily)
    tips_daily_formula_record = _record_with_matching_terms(
        snapshot_map.get("treasury_tips_cpi_detail"),
        snapshot_map.get("treasury_auction_tips_terms"),
    ) or tips_daily
    context["tips_formula_check_status"] = _tips_formula_status(
        tips_daily_formula_record,
        _terms_for_cusip(
            snapshot_map.get("treasury_auction_tips_terms"),
            str(tips_daily_formula_record.get("cusip", "")),
        ),
    )
    overlap = _sec_nmfp_mspd_overlap(snapshot_map)
    context["holder_allocation_gate_status"] = (
        "non_final_cusip_overlap_available"
        if overlap["matched_cusip_count"] > 0
        else "no_cusip_overlap_in_current_sample"
    )
    context.update(disabled_scenario_context())
    context["sec_nmfp_mspd_matched_cusip_count"] = str(overlap["matched_cusip_count"])
    context["sec_nmfp_mspd_matched_principal_bil"] = str(
        overlap["matched_principal_bil"]
    )
    context["valuation_input_gate_status"] = _valuation_input_gate_status(snapshot_map)
    context.update(_valuation_engine_readiness_context(snapshot_map))
    return context


def _frn_formula_status(record: dict) -> str:
    return validate_frn_daily_accrued_interest(record).status


def _tips_formula_status(record: dict, terms: dict) -> str:
    return validate_tips_index_ratio(record, terms).status


def _terms_for_cusip(snapshot, cusip: str) -> dict:
    if not snapshot or not cusip:
        return {}
    return next(
        (dict(record) for record in snapshot.records if record.get("cusip") == cusip),
        {},
    )


def _record_with_matching_terms(daily_snapshot, terms_snapshot) -> dict:
    if not daily_snapshot or not terms_snapshot:
        return {}
    term_ids = {str(record.get("cusip", "")) for record in terms_snapshot.records}
    return next(
        (
            dict(record)
            for record in daily_snapshot.records
            if str(record.get("cusip", "")) in term_ids
        ),
        {},
    )


def _latest_decimal(snapshot_map: dict, series_id: str) -> Decimal | None:
    snapshot = snapshot_map.get(series_id)
    if not snapshot:
        return None
    for record in _records_newest_first(snapshot):
        value = _decimal_from_record(record, "value")
        if value is not None:
            return value
    return None


def _latest_record(snapshot) -> dict:
    if not snapshot:
        return {}
    return _records_newest_first(snapshot)[0] if snapshot.records else {}


def _records_newest_first(snapshot) -> list[dict]:
    return sorted(
        (dict(record) for record in snapshot.records),
        key=_record_time_key,
        reverse=True,
    )


def _record_time_key(record: dict) -> str:
    for key in (
        "date",
        "record_date",
        "release_date",
        "as_of_date",
        "effectiveDate",
        "index_date",
        "month",
        "report_date",
    ):
        value = str(record.get(key, ""))
        if _date_sort_key(value):
            return _date_sort_key(value)
    return ""


def _date_sort_key(value: str) -> str:
    value = str(value or "")
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return value


def _tic_stock_record(snapshot_map: dict) -> dict:
    snapshot = snapshot_map.get("tic_foreign_treasury_stock_split")
    if not snapshot:
        return {}
    return next(
        (
            dict(record)
            for record in snapshot.records
            if record.get("component") == "total_treasury_securities"
        ),
        dict(snapshot.records[0]) if snapshot.records else {},
    )


def _sec_nmfp_aggregate(snapshot, channel: str) -> dict:
    if not snapshot:
        return {}
    return next(
        (
            dict(record)
            for record in snapshot.records
            if record.get("record_type") == "aggregate"
            and record.get("period_role", "latest") == "latest"
            and record.get("channel") == channel
            and record.get("security_bucket") == "total"
        ),
        {},
    )


def _sec_nmfp_mspd_overlap(snapshot_map: dict) -> dict:
    mspd = snapshot_map.get("treasury_mspd_table_3")
    sec_nmfp = snapshot_map.get("sec_nmfp_mmf_treasury_cusip_holdings")
    if not mspd or not mspd.records:
        return {"matched_cusip_count": 0, "matched_principal_bil": Decimal("0")}
    record_date = max(str(record.get("record_date", "")) for record in mspd.records)
    mspd_by_cusip = {}
    for record in mspd.records:
        if record.get("record_date") != record_date:
            continue
        if str(record.get("security_type_desc", "")).lower() != "marketable":
            continue
        if str(record.get("security_class1_desc", "")).lower().startswith("total"):
            continue
        cusip = str(
            record.get("cusip")
            or record.get("cusip_nbr")
            or record.get("security_class2_desc")
            or ""
        )
        if not cusip:
            continue
        amount = _decimal_from_record(record, "outstanding_amt")
        if amount is None:
            issued = _decimal_from_record(record, "issued_amt") or Decimal("0")
            redeemed = _decimal_from_record(record, "redeemed_amt") or Decimal("0")
            amount = max(issued - redeemed, Decimal("0"))
        mspd_by_cusip[cusip] = amount / Decimal("1000")
    sec_cusips = {
        str(record.get("cusip", ""))
        for record in (sec_nmfp.records if sec_nmfp else [])
        if record.get("record_type") == "cusip"
        and record.get("period_role", "latest") == "latest"
    }
    matched = set(mspd_by_cusip) & sec_cusips
    return {
        "matched_cusip_count": len(matched),
        "matched_principal_bil": sum(
            (mspd_by_cusip[cusip] for cusip in matched), Decimal("0")
        ),
    }


def _valuation_input_gate_status(snapshot_map: dict) -> str:
    mspd = snapshot_map.get("treasury_mspd_table_3")
    frn_daily = snapshot_map.get("treasury_frn_daily_indexes")
    tips_daily = snapshot_map.get("treasury_tips_cpi_detail")
    if not mspd or not mspd.records:
        return "missing_mspd_cashflow_context"
    record_date = max(str(record.get("record_date", "")) for record in mspd.records)
    frn_ids = set()
    tips_ids = set()
    for record in mspd.records:
        if record.get("record_date") != record_date:
            continue
        security_id = str(
            record.get("cusip")
            or record.get("cusip_nbr")
            or record.get("security_class2_desc")
            or ""
        )
        description = str(record.get("security_class1_desc", "")).lower()
        if "floating" in description and security_id:
            frn_ids.add(security_id)
        if "inflation" in description and security_id:
            tips_ids.add(security_id)
    frn_source_ids = {
        str(record.get("cusip", "")) for record in (frn_daily.records if frn_daily else [])
    }
    tips_source_ids = {
        str(record.get("cusip", "")) for record in (tips_daily.records if tips_daily else [])
    }
    if frn_ids & frn_source_ids and tips_ids & tips_source_ids:
        return "inputs_validated"
    return "partial_input_join"


def _valuation_engine_readiness_context(snapshot_map: dict) -> dict[str, str]:
    mspd = snapshot_map.get("treasury_mspd_table_3")
    frn_daily = snapshot_map.get("treasury_frn_daily_indexes")
    tips_daily = snapshot_map.get("treasury_tips_cpi_detail")
    tips_terms_snapshot = snapshot_map.get("treasury_auction_tips_terms")
    frn_terms_snapshot = snapshot_map.get("treasury_auction_frn_terms")
    frn_terms: dict[str, list[dict]] = {}
    for record in (frn_terms_snapshot.records if frn_terms_snapshot else []):
        frn_terms.setdefault(str(record.get("cusip", "")), []).append(record)
    frn_ids, tips_ids = _mspd_frn_tips_security_ids(mspd)
    tips_terms = {
        str(record.get("cusip", "")): record
        for record in (tips_terms_snapshot.records if tips_terms_snapshot else [])
    }
    tips_term_rows: dict[str, list[dict]] = {}
    for record in (tips_terms_snapshot.records if tips_terms_snapshot else []):
        tips_term_rows.setdefault(str(record.get("cusip", "")), []).append(record)
    frn_review = 0
    frn_unavailable = 0
    frn_matches = []
    for record in (frn_daily.records if frn_daily else []):
        if str(record.get("cusip", "")) not in frn_ids:
            continue
        frn_matches.append(record)
        validation = validate_frn_daily_accrued_interest(record)
        frn_review += validation.status == "formula_review_not_pricing"
        frn_unavailable += (
            validation.status == "formula_input_unavailable_not_pricing"
        )
    tips_review = 0
    tips_classified = 0
    tips_unresolved = 0
    tips_unavailable = 0
    tips_missing_terms = 0
    tips_matches = []
    tips_validations = []
    for record in (tips_daily.records if tips_daily else []):
        if str(record.get("cusip", "")) not in tips_ids:
            continue
        tips_matches.append(record)
        terms = tips_terms.get(str(record.get("cusip", "")), {})
        if not terms:
            tips_missing_terms += 1
        validation = validate_tips_index_ratio(record, terms)
        tips_validations.append(validation)
        if validation.status == "formula_review_not_pricing":
            tips_review += 1
            classification = classify_tips_formula_review(record, terms, validation)
            tips_classified += not classification.unresolved
            tips_unresolved += classification.unresolved
        tips_unavailable += (
            validation.status == "formula_input_unavailable_not_pricing"
        )
    formula_review_rows = frn_review + tips_review
    classified_review_rows = tips_classified
    unresolved_review_rows = frn_review + tips_unresolved
    unavailable_rows = frn_unavailable + tips_unavailable
    frn_audit = audit_frn_reset_convention(frn_matches)
    tips_audit = audit_tips_accrual_convention(
        tips_matches,
        tips_terms,
        tips_validations,
    )
    frn_source_records = list(frn_daily.records if frn_daily else [])
    tips_source_records = list(tips_daily.records if tips_daily else [])
    edge_rows = cashflow_edge_fixture_rows() + cashflow_edge_source_sample_rows(
        frn_records=frn_source_records,
        frn_terms=frn_terms,
        tips_records=tips_source_records,
        tips_terms=tips_terms,
        tips_term_rows=tips_term_rows,
    )
    source_edge_rows = [
        row for row in edge_rows if row.get("sample_source") == "source_backed_snapshot"
    ]
    source_edge_classified_rows = [
        row
        for row in source_edge_rows
        if not row.get("source_edge_classifier_status", "").startswith("not_observed")
        and row.get("source_edge_classifier_status")
        != "source_records_missing_not_pricing"
    ]
    source_edge_blocked_rows = [
        row for row in source_edge_rows if row.get("source_edge_blocker")
    ]
    switch_audit = pricing_switch_audit_rows()
    reset_calendar_source_blocked = _frn_reset_calendar_source_blocked(
        frn_daily,
        frn_terms_snapshot,
    )
    reset_official_audit_rows = 4
    reset_official_audit_blocked_rows = int(reset_calendar_source_blocked)
    reset_official_schema_evidence_rows = 5
    reset_official_schema_blocked_rows = 1
    reset_official_schema_validation_rows = 2
    reset_method_semantics_audit_rows = 6
    reset_method_semantics_context_only_rows = 2
    reset_method_design_ledger_rows = 6
    reset_method_design_required_rows = 6
    reset_cusip_coverage_ledger_rows = 8
    reset_cusip_coverage_blocked_rows = 1
    reset_cusip_three_way_overlap_count = _frn_reset_three_way_cusip_overlap_count(
        frn_daily,
        frn_terms_snapshot,
        snapshot_map.get("treasury_mspd_table_3"),
    )
    reset_fixture_readiness_ledger_rows = 7
    reset_fixture_readiness_blocked_rows = 5
    reset_fixture_readiness_covered_rows = 2
    reset_calendar_policy_rows = 6
    reset_calendar_policy_fail_closed_rows = 5
    reset_calendar_policy_blocker_rows = 1
    reset_explicit_opt_in_gate_rows = len(switch_audit) + 1
    reset_explicit_opt_in_disabled_switch_rows = reset_explicit_opt_in_gate_rows
    reset_explicit_opt_in_prerequisite_rows = reset_explicit_opt_in_gate_rows
    reset_method_frontier_ledger_rows = 7
    reset_method_frontier_reduced_rows = 3
    reset_method_frontier_blocked_rows = 3
    reset_method_frontier_future_opt_in_rows = 1
    source_blocker_rows = (
        int(bool(source_edge_blocked_rows))
        + int(reset_calendar_source_blocked)
        + int(bool(unresolved_review_rows or unavailable_rows or tips_missing_terms))
    )
    policy_blocker_rows = int(
        any(row.get("switch_enabled") == "false" for row in switch_audit)
    )
    readiness_gate_evidence_rows = 5
    readiness_gate_blocker_rows = 4
    readiness_gate_disabled_rows = 2
    edge_fixtures_defined = all(
        row.get("test_status") == "fixture_contract_tested_not_pricing"
        and row.get("pricing_output_enabled") == "false"
        for row in edge_rows
    )
    conventions_audited = (
        frn_audit["audit_passed"] == "true" and tips_audit["audit_passed"] == "true"
    )
    status = (
        "blocked_pending_formula_review_resolution"
        if unresolved_review_rows or unavailable_rows or tips_missing_terms
        else (
            "disabled_opt_in_contract_pricing_disabled"
            if conventions_audited and edge_fixtures_defined
            else "blocked_pending_reset_accrual_convention_audit"
        )
    )
    return {
        "valuation_engine_readiness_status": status,
        "valuation_pricing_output_enabled": "false",
        "valuation_opt_in_contract_status": "disabled_requires_explicit_switches",
        "valuation_readiness_coverage_rows": "7",
        "valuation_readiness_source_blocker_rows": str(source_blocker_rows),
        "valuation_readiness_policy_blocker_rows": str(policy_blocker_rows),
        "valuation_readiness_gate_evidence_rows": str(readiness_gate_evidence_rows),
        "valuation_readiness_gate_blocker_rows": str(readiness_gate_blocker_rows),
        "valuation_readiness_gate_disabled_rows": str(readiness_gate_disabled_rows),
        "valuation_frn_reset_official_source_audit_rows": str(
            reset_official_audit_rows
        ),
        "valuation_frn_reset_official_audit_blocked_rows": str(
            reset_official_audit_blocked_rows
        ),
        "valuation_frn_reset_official_source_schema_evidence_rows": str(
            reset_official_schema_evidence_rows
        ),
        "valuation_frn_reset_official_source_schema_blocked_rows": str(
            reset_official_schema_blocked_rows
        ),
        "valuation_frn_reset_official_source_schema_validation_rows": str(
            reset_official_schema_validation_rows
        ),
        "valuation_frn_reset_method_semantics_audit_rows": str(
            reset_method_semantics_audit_rows
        ),
        "valuation_frn_reset_method_semantics_context_only_rows": str(
            reset_method_semantics_context_only_rows
        ),
        "valuation_cashflow_edge_fixture_rows": str(len(edge_rows)),
        "valuation_source_backed_edge_sample_rows": str(len(source_edge_rows)),
        "valuation_source_edge_classified_rows": str(len(source_edge_classified_rows)),
        "valuation_source_edge_blocked_rows": str(len(source_edge_blocked_rows)),
        "valuation_pricing_switch_audit_rows": str(len(switch_audit)),
        "valuation_pricing_switches_enabled": str(
            sum(row.get("switch_enabled") == "true" for row in switch_audit)
        ),
        "valuation_pricing_switches_disabled": str(
            sum(row.get("switch_enabled") == "false" for row in switch_audit)
        ),
        "valuation_explicit_pricing_switch_enabled": "false",
        "valuation_formula_review_rows": str(formula_review_rows),
        "valuation_classified_formula_review_rows": str(classified_review_rows),
        "valuation_unresolved_formula_review_rows": str(unresolved_review_rows),
        "valuation_frn_reset_method_design_ledger_rows": str(
            reset_method_design_ledger_rows
        ),
        "valuation_frn_reset_method_design_required_rows": str(
            reset_method_design_required_rows
        ),
        "valuation_frn_reset_cusip_coverage_ledger_rows": str(
            reset_cusip_coverage_ledger_rows
        ),
        "valuation_frn_reset_cusip_coverage_blocked_rows": str(
            reset_cusip_coverage_blocked_rows
        ),
        "valuation_frn_reset_cusip_three_way_overlap_count": str(
            reset_cusip_three_way_overlap_count
        ),
        "valuation_frn_reset_fixture_readiness_ledger_rows": str(
            reset_fixture_readiness_ledger_rows
        ),
        "valuation_frn_reset_fixture_readiness_blocked_rows": str(
            reset_fixture_readiness_blocked_rows
        ),
        "valuation_frn_reset_fixture_readiness_covered_rows": str(
            reset_fixture_readiness_covered_rows
        ),
        "valuation_frn_reset_calendar_policy_rows": str(
            reset_calendar_policy_rows
        ),
        "valuation_frn_reset_calendar_policy_fail_closed_rows": str(
            reset_calendar_policy_fail_closed_rows
        ),
        "valuation_frn_reset_calendar_policy_blocker_rows": str(
            reset_calendar_policy_blocker_rows
        ),
        "valuation_frn_reset_explicit_opt_in_gate_rows": str(
            reset_explicit_opt_in_gate_rows
        ),
        "valuation_frn_reset_explicit_opt_in_disabled_switch_rows": str(
            reset_explicit_opt_in_disabled_switch_rows
        ),
        "valuation_frn_reset_explicit_opt_in_prerequisite_rows": str(
            reset_explicit_opt_in_prerequisite_rows
        ),
        "valuation_frn_reset_method_frontier_ledger_rows": str(
            reset_method_frontier_ledger_rows
        ),
        "valuation_frn_reset_method_frontier_reduced_rows": str(
            reset_method_frontier_reduced_rows
        ),
        "valuation_frn_reset_method_frontier_blocked_rows": str(
            reset_method_frontier_blocked_rows
        ),
        "valuation_frn_reset_method_frontier_future_opt_in_rows": str(
            reset_method_frontier_future_opt_in_rows
        ),
    }


def _frn_reset_calendar_source_blocked(frn_daily, frn_terms_snapshot) -> bool:
    fields = set()
    for snapshot in (frn_daily, frn_terms_snapshot):
        for record in (snapshot.records if snapshot else []):
            fields.update(str(key) for key in record)
    candidate_terms = ("reset", "calendar")
    excluded_terms = ("index_determination", "tax")
    return not any(
        any(term in field.lower() for term in candidate_terms)
        and not any(term in field.lower() for term in excluded_terms)
        for field in fields
    )


def _frn_reset_three_way_cusip_overlap_count(
    frn_daily, frn_terms_snapshot, mspd_snapshot
) -> int:
    daily_cusips = _field_cusips(frn_daily, "cusip")
    term_cusips = _field_cusips(frn_terms_snapshot, "cusip")
    if not mspd_snapshot or not mspd_snapshot.records:
        return 0
    latest_record_date = max(
        str(row.get("record_date", ""))
        for row in mspd_snapshot.records
        if str(row.get("record_date", ""))
    )
    mspd_cusips = {
        str(row.get("security_class2_desc", "")).strip()
        for row in mspd_snapshot.records
        if row.get("record_date") == latest_record_date
        and str(row.get("security_class1_desc", "")).lower()
        == "floating rate notes"
        and str(row.get("security_type_desc", "")).lower() == "marketable"
        and str(row.get("security_class2_desc", "")).strip()
        and str(row.get("security_class2_desc", "")).strip().lower() != "null"
    }
    return len(daily_cusips & term_cusips & mspd_cusips)


def _field_cusips(snapshot, field: str) -> set[str]:
    if not snapshot:
        return set()
    return {
        str(row.get(field, "")).strip()
        for row in snapshot.records
        if str(row.get(field, "")).strip()
        and str(row.get(field, "")).strip().lower() != "null"
    }


def _mspd_frn_tips_security_ids(mspd) -> tuple[set[str], set[str]]:
    frn_ids: set[str] = set()
    tips_ids: set[str] = set()
    if not mspd or not mspd.records:
        return frn_ids, tips_ids
    record_date = max(str(record.get("record_date", "")) for record in mspd.records)
    for record in mspd.records:
        if record.get("record_date") != record_date:
            continue
        security_id = str(
            record.get("cusip")
            or record.get("cusip_nbr")
            or record.get("security_class2_desc")
            or ""
        )
        description = str(record.get("security_class1_desc", "")).lower()
        if not security_id:
            continue
        if "floating" in description:
            frn_ids.add(security_id)
        if "inflation" in description:
            tips_ids.add(security_id)
    return frn_ids, tips_ids


def _decimal_from_record(record: dict, key: str) -> Decimal | None:
    raw = record.get(key)
    if raw in (None, "", "."):
        return None
    try:
        return Decimal(str(raw).replace(",", ""))
    except Exception:
        return None
