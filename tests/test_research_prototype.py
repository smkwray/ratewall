import csv
import hashlib
import json
import time
import zipfile
from collections import Counter
from dataclasses import fields as dataclass_fields
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

import ratewall.databook.build as databook_build
from ratewall.databook import build_legacy as databook_legacy
from ratewall.databook.build import (

    _denominator_calibration_source_context,
    _frn_reset_source_blocker_map_rows,
    _latest_record,
    _paper_forbidden_switches_false,
    _quarterly_mts_interest_outlays,
    build_databook,
)
from ratewall.accounting.assumption_engine import (
    load_ratewall_assumption_sets,
    parameter_pack_rows,
)
from ratewall.data.build import build_snapshot_bundle
from ratewall.data.demo import fallback_snapshot
from ratewall.data.derived import derive_accounting_inputs
from ratewall.data.snapshots import read_snapshot_bundle
from ratewall.accounting.valuation import (
    ValuationOptInSwitches,
    cashflow_edge_fixture_rows,
    cashflow_edge_source_sample_rows,
    classify_tips_formula_review,
    pricing_switch_audit_rows,
    valuation_engine_opt_in_contract_rows,
    valuation_convention_audit_fixtures,
    validate_frn_daily_accrued_interest,
    validate_tips_index_ratio,
)
from ratewall.empirical.local_projection import (
    LocalProjectionSpec,
    write_empirical_results,
    write_empirical_smoke_panel,
    write_shock_dataset_catalog,
    write_empirical_specs,
)
from ratewall.generated_text_claim_scan import generated_text_claim_boundary_scan_rows
from ratewall.databook.tdcsim_contracts import (
    tdc_forward_projection_surface_rows,
    tdcsim_domestic_nonbank_funding_classification_rows,
    tdcsim_projection_contract_bridge_rows,
)
from ratewall.model.holder_mapping import (
    HolderMappingSwitches,
    disabled_allocation_design_ledger_rows,
    disabled_final_owner_allocation_rows,
    disabled_mapping_design,
)
from ratewall.model.scenarios import build_scenario_table
from ratewall.release import (
    build_release_package,
    _release_23_archive_verification_rows,
)
from ratewall.sources.registry import SourceRegistry
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot



pytestmark = pytest.mark.full_surface

def test_demo_snapshot_bundle_has_provenance_and_four_impulse_horizons(
    tmp_path: Path,
) -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    output = build_snapshot_bundle(
        registry=registry,
        output=tmp_path / "snapshot.json",
        mode="demo",
    )

    snapshots = read_snapshot_bundle(output)
    assert {snapshot.metadata.series_id for snapshot in snapshots} >= {
        "WRESBAL",
        "RRPONTSYD",
        "GDP",
        "FEDFUNDS",
        "IORB",
        "debt_to_penny",
        "treasury_repricing_anchor",
        "tic_foreign_treasury_stock_split",
        "sec_nmfp_mmf_treasury_cusip_holdings",
        "treasury_frn_daily_indexes",
        "treasury_tips_cpi_detail",
    }
    assert all(snapshot.metadata.retrieved_at.endswith("Z") for snapshot in snapshots)
    assert all(
        snapshot.metadata.source_url.startswith("https://") for snapshot in snapshots
    )
    assert all(snapshot.metadata.snapshot_kind == "demo_stub" for snapshot in snapshots)

    derived = derive_accounting_inputs(snapshots)
    assert [horizon.label for horizon in derived.horizons] == ["1q", "1y", "3y", "10y"]
    assert derived.reserves_bil == Decimal("3032.588")
    assert derived.debt_held_public_bil == Decimal("31260")


def test_romer_romer_converted_snapshot_is_fail_closed_source_input() -> None:
    snapshots = read_snapshot_bundle(Path("data/raw/ratewall_snapshot.json"))
    snapshot = next(
        snapshot
        for snapshot in snapshots
        if snapshot.metadata.series_id == "romer_romer_2004"
    )

    assert snapshot.metadata.source_id == "berkeley_romer_romer"
    assert snapshot.metadata.snapshot_kind == "converted_source_snapshot"
    assert snapshot.metadata.units == "basis_points"
    assert snapshot.metadata.frequency == "monthly"
    assert snapshot.metadata.source_release_at == "2004-07-27"
    assert (
        "converted_csv_sha256=33baaf209d61d3e838806c3dae68d3d6cdaecc20b8aa3a556e61f7f30310963f"
        in (snapshot.metadata.note or "")
    )
    assert (
        "source_xls_sha256=4f90c85125443e67177e410245539fc9cec3b9cf22db978ed72463ed63eab24e"
        in (snapshot.metadata.note or "")
    )

    assert len(snapshot.records) == 372
    assert snapshot.records[0]["date"] == "1966-01-01"
    assert snapshot.records[-1]["date"] == "1996-12-01"
    assert (
        sum(
            1
            for record in snapshot.records
            if str(record.get("sample_1969_1996")) == "true"
        )
        == 336
    )
    assert {
        "date",
        "resid_pct_point",
        "shock_bps",
        "sample_1969_1996",
    } <= set(snapshot.records[0])

    source_context = _denominator_calibration_source_context(
        "romer_romer_2004",
        shock_snapshot=snapshot,
    )
    assert source_context["candidate_source_file_url"] == (
        "data/raw/romer_romer/romer_romer_monthly_shocks.csv"
    )
    assert source_context["parser_source_admission_status"] == (
        "admitted_reviewed_converted_csv_snapshot_not_runtime_xls_parser"
    )
    assert source_context["parser_runtime_status"] == (
        "admitted_backend_uses_materialized_csv_snapshot_no_runtime_"
        "legacy_xls_parser_required"
    )
    assert source_context["candidate_schema_review_status"] == (
        "admitted_date_resid_monthly_schema_and_mtgdate_resid_meeting_schema_documented"
    )
    assert source_context["candidate_unit_review_status"] == (
        "admitted_resid_pct_point_to_shock_bps_materialized"
    )
    assert source_context["candidate_sample_harmonization_status"] == (
        "admitted_monthly_rows_flag_1969_1996_replication_window"
    )
    assert source_context["snapshot_admission_status"] == (
        "admitted_converted_csv_source_snapshot_fail_closed"
    )
    assert source_context["cross_source_replication_input_status"] == (
        "admitted_converted_csv_snapshot_fail_closed_for_response_estimate_review"
    )
    assert (
        "fail-closed response-estimate review"
        in (source_context["cross_source_replication_blocker"])
    )

    response_rows = list(
        csv.DictReader(
            Path(
                "outputs/tables/ratewall_denominator_response_estimate_diagnostic.csv"
            ).open(encoding="utf-8")
        )
    )
    rr_response = next(
        row
        for row in response_rows
        if row["response_estimate_diagnostic_id"]
        == (
            "denominator_response_estimate_diagnostic::"
            "scalar_conventional_drag_amplitude::8q::romer_romer_2004::GDP"
        )
    )
    assert rr_response["response_estimate_available"] == "true"
    assert rr_response["response_estimate_used_for_prior"] == "false"
    assert rr_response["shock_source_id"] == "romer_romer_2004"
    assert rr_response["outcome_series_id"] == "GDP"
    assert rr_response["horizon_bucket"] == "8q"
    assert rr_response["horizon_months"] == "24"
    assert rr_response["shock_value_field"] == "shock_bps"
    assert rr_response["shock_units"] == "basis_points"
    assert rr_response["sample_window"] == (
        "1969-01-01_to_1996-12-01_rr_sample_flag_true"
    )
    assert rr_response["outcome_transform"] == "annualized_percent_change"
    assert rr_response["date_alignment_rule"] == (
        "baseline=latest_quarterly_gdp_on_or_before_rr_month;"
        "future=first_quarterly_gdp_on_or_after_rr_month_plus_24_months"
    )
    assert rr_response["event_observation_count"] == "336"
    assert rr_response["usable_observation_count"] == "336"
    assert rr_response["missing_baseline_count"] == "0"
    assert rr_response["missing_future_window_count"] == "0"
    assert rr_response["response_outcome_units_per_shock_unit"] == (
        "annualized_gdp_percent_change_per_basis_points"
    )
    assert rr_response["unit_conversion_to_gdp_share_status"] == (
        "blocked_rr_gdp_8q_not_reviewed_gdp_share_per_100bp_year"
    )
    assert rr_response["robust_uncertainty_status"] == (
        "blocked_rr_classical_ols_uncertainty_not_promotion_grade"
    )
    assert rr_response["confidence_interval_status"] == (
        "blocked_rr_no_promotion_grade_confidence_interval"
    )
    assert rr_response["p_value_status"] == ("blocked_rr_no_promotion_grade_p_value")
    assert (
        "endpoint annualized GDP percent-change"
        in (rr_response["formal_response_estimate_blocker"])
    )
    assert rr_response["denominator_prior_calibration_grade"] == (
        "not_calibration_grade_diagnostic_only"
    )
    assert rr_response["prior_narrowing_allowed"] == "false"
    assert rr_response["split_denominator_promotion_allowed"] == "false"
    assert rr_response["formula_replacement_allowed"] == "false"
    assert rr_response["main_offset_ratio_changed_this_tranche"] == "false"

    denominator_gate_rows = list(
        csv.DictReader(
            Path(
                "outputs/tables/ratewall_denominator_calibration_design_gate.csv"
            ).open(encoding="utf-8")
        )
    )
    romer_gate = next(
        row
        for row in denominator_gate_rows
        if row["gate_id"] == "denominator_calibration::romer_romer::real_gdp::8q"
    )
    assert romer_gate["source_input_status"] == (
        "source_backed_shock_and_outcome_snapshots_available"
    )
    assert romer_gate["response_estimate_layer_status"] == (
        "diagnostic_response_estimate_available_not_promotion_grade"
    )
    assert romer_gate["promotion_decision"] == (
        "blocked_diagnostic_estimate_available_not_promotion_grade"
    )
    assert romer_gate["matched_response_estimate_available_count"] == "1"
    assert (
        romer_gate["matched_response_estimate_diagnostic_id"]
        == (rr_response["response_estimate_diagnostic_id"])
    )
    assert romer_gate["unit_conversion_review_status"] == (
        "blocked_rr_gdp_8q_not_reviewed_gdp_share_per_100bp_year"
    )
    assert (
        "policy-path duration normalization"
        in (romer_gate["unit_conversion_review_blocker"])
    )
    assert romer_gate["uncertainty_review_status"] == (
        "fail_closed_hac_diagnostic_available_not_promotion_grade"
    )
    assert (
        "not a promotion-grade denominator calibration"
        in (romer_gate["uncertainty_review_blocker"])
    )
    assert romer_gate["confidence_interval_review_status"] == (
        "diagnostic_hac_confidence_interval_available_not_promotion_grade"
    )
    assert romer_gate["p_value_review_status"] == (
        "diagnostic_hac_normal_approx_p_value_available_not_promotion_grade"
    )
    assert romer_gate["prior_narrowing_allowed"] == "false"
    assert romer_gate["formula_replacement_allowed"] == "false"


def test_irs_soi_taxable_interest_snapshot_is_fail_closed_tax_context() -> None:
    snapshots = {
        snapshot.metadata.series_id: snapshot
        for snapshot in read_snapshot_bundle(Path("data/raw/ratewall_snapshot.json"))
    }
    federal_persons_business_interest_snapshot = snapshots["NA000309Q"]
    snapshot = snapshots["irs_soi_taxable_interest"]
    ira_snapshot = snapshots["irs_soi_ira_type_agi"]
    average_tax_rate_snapshot = snapshots["irs_soi_average_tax_rate_percentile"]
    dfa_account_snapshot = snapshots["fed_dfa_household_account_type_context"]
    scf_account_snapshot = snapshots["fed_scf_2022_safe_asset_account_tax_context"]
    payment_timing_snapshot = snapshots["irs_estimated_tax_payment_timing"]
    state_agi_snapshot = snapshots["irs_soi_state_interest_agi"]
    treasury_tax_snapshot = snapshots["treasury_security_interest_tax_treatment"]
    irs_interest_tax_snapshot = snapshots["irs_interest_received_tax_topic_403"]
    irs_pub550_snapshot = snapshots["irs_publication_550_interest_income_taxonomy"]
    irs_1099_snapshot = snapshots["irs_1099_int_div_reporting_taxonomy"]
    fta_state_rate_snapshot = snapshots["fta_state_individual_income_tax_rates"]
    tic_custody_snapshot = snapshots["tic_foreign_holder_custody_limitation_context"]
    fed_cross_border_snapshot = snapshots[
        "fed_cross_border_treasury_basis_trade_context"
    ]

    assert federal_persons_business_interest_snapshot.metadata.source_id == "fred"
    assert federal_persons_business_interest_snapshot.metadata.snapshot_kind == "live"
    assert (
        federal_persons_business_interest_snapshot.metadata.units
        == "millions_of_dollars"
    )
    assert federal_persons_business_interest_snapshot.metadata.frequency == "quarterly"
    assert "recipient_leakage_federal_interest_to_persons_business_context_only" in (
        federal_persons_business_interest_snapshot.metadata.note or ""
    )
    assert len(federal_persons_business_interest_snapshot.records) >= 250

    assert snapshot.metadata.source_id == "irs_soi"
    assert snapshot.metadata.snapshot_kind == "converted_source_snapshot"
    assert snapshot.metadata.units == "return_counts_and_thousands_of_dollars"
    assert snapshot.metadata.frequency == "annual"
    assert snapshot.metadata.source_release_at == "2026-03"
    assert (
        "source_xls_sha256=b6c1f87fbb5533417e195f6938538e5de09b6a0825a6a54346bf9363a18d96af"
        in (snapshot.metadata.note or "")
    )
    assert (
        "converted_csv_sha256=903a551db9081f66755d751f7102f7602bffeee4c6d31de56dc6aae15416e2e4"
        in (snapshot.metadata.note or "")
    )
    assert "tax_clawback_gate_passed=false" in (snapshot.metadata.note or "")
    assert "main_ratio_admission_allowed=false" in (snapshot.metadata.note or "")

    assert ira_snapshot.metadata.source_id == "irs_soi"
    assert ira_snapshot.metadata.snapshot_kind == "converted_source_snapshot"
    assert ira_snapshot.metadata.units == "return_counts_and_thousands_of_dollars"
    assert ira_snapshot.metadata.frequency == "annual"
    assert ira_snapshot.metadata.source_release_at == "2025-02"
    assert "source_record_count=64" in (ira_snapshot.metadata.note or "")
    assert "account_type_context_available=true" in (ira_snapshot.metadata.note or "")
    assert "state_tax_context_available=false" in (ira_snapshot.metadata.note or "")
    assert "payment_timing_available=false" in (ira_snapshot.metadata.note or "")
    assert "tax_clawback_gate_passed=false" in (ira_snapshot.metadata.note or "")
    assert "main_ratio_admission_allowed=false" in (ira_snapshot.metadata.note or "")

    assert average_tax_rate_snapshot.metadata.source_id == "irs_soi"
    assert (
        average_tax_rate_snapshot.metadata.snapshot_kind == "converted_source_snapshot"
    )
    assert (
        average_tax_rate_snapshot.metadata.units
        == "return_counts_millions_of_dollars_and_percentages"
    )
    assert average_tax_rate_snapshot.metadata.frequency == "annual"
    assert average_tax_rate_snapshot.metadata.source_release_at == "2026-03"
    assert "source_record_count=2760" in (average_tax_rate_snapshot.metadata.note or "")
    assert "tax_rate_distribution_context_available=true" in (
        average_tax_rate_snapshot.metadata.note or ""
    )
    assert "full_tax_incidence_available=false" in (
        average_tax_rate_snapshot.metadata.note or ""
    )
    assert "current_demand_conversion_available=false" in (
        average_tax_rate_snapshot.metadata.note or ""
    )
    assert "tax_clawback_gate_passed=false" in (
        average_tax_rate_snapshot.metadata.note or ""
    )
    assert "main_ratio_admission_allowed=false" in (
        average_tax_rate_snapshot.metadata.note or ""
    )

    assert dfa_account_snapshot.metadata.source_id == "fed_dfa"
    assert dfa_account_snapshot.metadata.snapshot_kind == "live"
    assert dfa_account_snapshot.metadata.units == "millions_of_dollars"
    assert dfa_account_snapshot.metadata.frequency == "quarterly"
    assert dfa_account_snapshot.metadata.source_release_at == "2025:Q4"
    assert "source_record_count=6" in (dfa_account_snapshot.metadata.note or "")
    assert "tax_clawback_gate_passed=false" in (
        dfa_account_snapshot.metadata.note or ""
    )
    assert "main_ratio_admission_allowed=false" in (
        dfa_account_snapshot.metadata.note or ""
    )

    assert len(dfa_account_snapshot.records) == 6
    assert {
        "date",
        "as_of_date",
        "wealth_group",
        "deposits_mil",
        "money_market_fund_shares_mil",
        "debt_securities_mil",
        "us_government_municipal_securities_mil",
        "annuities_mil",
        "dc_pension_entitlements_mil",
        "db_pension_entitlements_mil",
        "retirement_entitlements_mil",
        "tax_deferred_or_retirement_account_context_available",
    } <= set(dfa_account_snapshot.records[0])
    assert dfa_account_snapshot.records[0]["as_of_date"] == "2025:Q4"
    assert (
        dfa_account_snapshot.records[0][
            "tax_deferred_or_retirement_account_context_available"
        ]
        == "true"
    )
    assert dfa_account_snapshot.records[0]["tax_clawback_gate_passed"] == "false"

    assert scf_account_snapshot.metadata.source_id == "fed_scf"
    assert (
        scf_account_snapshot.metadata.snapshot_kind
        == "live_zip_csv_weighted_summary_context"
    )
    assert (
        scf_account_snapshot.metadata.units == "2022_dollars_weighted_account_context"
    )
    assert scf_account_snapshot.metadata.frequency == "triennial_cross_section"
    assert scf_account_snapshot.metadata.source_release_at == "2024-04-03"
    assert "source_record_count=12" in (scf_account_snapshot.metadata.note or "")
    assert "deposit_mmf_bond_retirement_account_context_available=true" in (
        scf_account_snapshot.metadata.note or ""
    )
    assert "source_specific_interest_payer_mapping_available=false" in (
        scf_account_snapshot.metadata.note or ""
    )
    assert "current_demand_conversion_available=false" in (
        scf_account_snapshot.metadata.note or ""
    )
    assert "tax_clawback_gate_passed=false" in (
        scf_account_snapshot.metadata.note or ""
    )
    assert len(scf_account_snapshot.records) == 12
    assert scf_account_snapshot.records[0]["source_field"] == "CHECKING"
    assert scf_account_snapshot.records[3]["source_field"] == "MMMF"
    assert scf_account_snapshot.records[9]["source_field"] == "RETQLIQ"
    assert (
        scf_account_snapshot.records[9]["tax_relevance_context"]
        == "tax_deferred_or_tax_preferred_account_context"
    )
    assert (
        scf_account_snapshot.records[0][
            "source_specific_interest_payer_mapping_available"
        ]
        == "false"
    )
    assert scf_account_snapshot.records[0]["main_ratio_admission_allowed"] == "false"

    assert payment_timing_snapshot.metadata.source_id == "irs_tax_guidance"
    assert payment_timing_snapshot.metadata.snapshot_kind == "live_text_context"
    assert payment_timing_snapshot.metadata.units == "recurring_due_date_context"
    assert (
        payment_timing_snapshot.metadata.frequency
        == "annual_recurring_quarterly_schedule"
    )
    assert payment_timing_snapshot.metadata.source_release_at == "2017-10-22"
    assert "source_record_count=4" in (payment_timing_snapshot.metadata.note or "")
    assert "payment_timing_available=true" in (
        payment_timing_snapshot.metadata.note or ""
    )
    assert "state_tax_context_available=false" in (
        payment_timing_snapshot.metadata.note or ""
    )
    assert "current_demand_conversion_available=false" in (
        payment_timing_snapshot.metadata.note or ""
    )
    assert "tax_clawback_gate_passed=false" in (
        payment_timing_snapshot.metadata.note or ""
    )
    assert len(payment_timing_snapshot.records) == 4
    assert payment_timing_snapshot.records[0]["estimated_tax_due_month_day"] == "04-15"
    assert payment_timing_snapshot.records[-1]["estimated_tax_due_year_relation"] == (
        "following_year"
    )
    assert (
        payment_timing_snapshot.records[0][
            "source_marker_quarterly_estimated_payments_verified"
        ]
        == "true"
    )

    assert state_agi_snapshot.metadata.source_id == "irs_soi"
    assert state_agi_snapshot.metadata.snapshot_kind == "converted_source_snapshot"
    assert state_agi_snapshot.metadata.units == "return_counts_and_thousands_of_dollars"
    assert state_agi_snapshot.metadata.frequency == "annual"
    assert state_agi_snapshot.metadata.source_release_at == "2025-12"
    assert "source_record_count=594" in (state_agi_snapshot.metadata.note or "")
    assert "state_or_area_count=54" in (state_agi_snapshot.metadata.note or "")
    assert "agi_stub_count=11" in (state_agi_snapshot.metadata.note or "")
    assert "state_agi_recipient_context_available=true" in (
        state_agi_snapshot.metadata.note or ""
    )
    assert "state_tax_treatment_available=false" in (
        state_agi_snapshot.metadata.note or ""
    )
    assert "current_demand_conversion_available=false" in (
        state_agi_snapshot.metadata.note or ""
    )
    assert "tax_clawback_gate_passed=false" in (state_agi_snapshot.metadata.note or "")
    assert len(state_agi_snapshot.records) == 594
    assert state_agi_snapshot.records[0]["state_code"] == "US"
    assert state_agi_snapshot.records[0]["agi_stub"] == "0"
    assert (
        state_agi_snapshot.records[0]["taxable_interest_amount_thousand_usd"]
        == "133121649"
    )
    assert state_agi_snapshot.records[-1]["state_code"] == "PR"

    assert treasury_tax_snapshot.metadata.source_id == "treasury_direct"
    assert treasury_tax_snapshot.metadata.snapshot_kind == "live_text_context"
    assert treasury_tax_snapshot.metadata.units == "tax_treatment_context"
    assert treasury_tax_snapshot.metadata.frequency == "guidance_page_specific"
    assert "source_record_count=1" in (treasury_tax_snapshot.metadata.note or "")
    assert "treasury_interest_federal_tax_marker_verified=true" in (
        treasury_tax_snapshot.metadata.note or ""
    )
    assert "treasury_interest_state_local_exemption_marker_verified=true" in (
        treasury_tax_snapshot.metadata.note or ""
    )
    assert "source_specific_tax_treatment_available=true" in (
        treasury_tax_snapshot.metadata.note or ""
    )
    assert "tax_clawback_gate_passed=false" in (
        treasury_tax_snapshot.metadata.note or ""
    )
    assert len(treasury_tax_snapshot.records) == 1
    assert (
        treasury_tax_snapshot.records[0]["federal_income_tax_treatment"]
        == "subject_to_federal_income_tax"
    )
    assert (
        treasury_tax_snapshot.records[0]["state_local_income_tax_treatment"]
        == "exempt_from_state_and_local_income_taxes"
    )
    assert (
        treasury_tax_snapshot.records[0]["source_specific_recipient_mapping_available"]
        == "false"
    )
    assert treasury_tax_snapshot.records[0]["main_ratio_admission_allowed"] == "false"

    assert irs_interest_tax_snapshot.metadata.source_id == "irs_tax_guidance"
    assert irs_interest_tax_snapshot.metadata.snapshot_kind == "live_text_context"
    assert (
        irs_interest_tax_snapshot.metadata.units
        == "source_specific_interest_tax_treatment_context"
    )
    assert irs_interest_tax_snapshot.metadata.frequency == "guidance_page_specific"
    assert "source_record_count=4" in (irs_interest_tax_snapshot.metadata.note or "")
    assert "deposit_mmf_cd_corporate_interest_tax_marker_verified=true" in (
        irs_interest_tax_snapshot.metadata.note or ""
    )
    assert "treasury_interest_tax_marker_verified=true" in (
        irs_interest_tax_snapshot.metadata.note or ""
    )
    assert "source_specific_tax_treatment_available=true" in (
        irs_interest_tax_snapshot.metadata.note or ""
    )
    assert "source_specific_recipient_mapping_available=false" in (
        irs_interest_tax_snapshot.metadata.note or ""
    )
    assert len(irs_interest_tax_snapshot.records) == 4
    assert (
        irs_interest_tax_snapshot.records[0]["cashflow_component"]
        == "deposit_mmf_and_private_interest"
    )
    assert (
        irs_interest_tax_snapshot.records[0]["federal_income_tax_treatment"]
        == "generally_taxable_interest_income"
    )
    assert (
        irs_interest_tax_snapshot.records[0]["main_ratio_admission_allowed"] == "false"
    )

    assert irs_pub550_snapshot.metadata.source_id == "irs_tax_guidance"
    assert irs_pub550_snapshot.metadata.snapshot_kind == "live_text_context"
    assert (
        irs_pub550_snapshot.metadata.units
        == "source_specific_interest_income_taxonomy_context"
    )
    assert irs_pub550_snapshot.metadata.frequency == "annual_guidance_publication"
    assert irs_pub550_snapshot.metadata.source_release_at == "2025"
    assert "source_record_count=7" in (irs_pub550_snapshot.metadata.note or "")
    assert "bank_cd_treasury_mmf_state_local_interest_markers_verified=true" in (
        irs_pub550_snapshot.metadata.note or ""
    )
    assert "source_specific_recipient_mapping_available=false" in (
        irs_pub550_snapshot.metadata.note or ""
    )
    assert "state_tax_rate_mapping_available=false" in (
        irs_pub550_snapshot.metadata.note or ""
    )
    assert "current_demand_conversion_available=false" in (
        irs_pub550_snapshot.metadata.note or ""
    )
    assert "tax_clawback_gate_passed=false" in (irs_pub550_snapshot.metadata.note or "")
    assert len(irs_pub550_snapshot.records) == 7
    assert (
        irs_pub550_snapshot.records[0]["cashflow_component"]
        == "deposit_and_private_interest"
    )
    assert irs_pub550_snapshot.records[3]["cashflow_component"] == "treasury_interest"
    assert (
        irs_pub550_snapshot.records[3]["state_local_income_tax_treatment"]
        == "exempt_from_all_state_and_local_income_taxes"
    )
    assert irs_pub550_snapshot.records[0]["main_ratio_admission_allowed"] == "false"

    assert irs_1099_snapshot.metadata.source_id == "irs_tax_guidance"
    assert irs_1099_snapshot.metadata.snapshot_kind == "live_text_context"
    assert (
        irs_1099_snapshot.metadata.units == "information_return_box_reporting_context"
    )
    assert irs_1099_snapshot.metadata.frequency == "annual_guidance_publication"
    assert "source_record_count=7" in (irs_1099_snapshot.metadata.note or "")
    assert (
        "deposit_private_interest_treasury_tax_exempt_mmf_dividend_"
        "reporting_and_reportability_constraint_markers_verified=true"
    ) in (irs_1099_snapshot.metadata.note or "")
    assert (
        "tax_deferred_exempt_and_foreign_payee_reportability_constraints_available=true"
    ) in (irs_1099_snapshot.metadata.note or "")
    assert "source_specific_reporting_available=true" in (
        irs_1099_snapshot.metadata.note or ""
    )
    assert "source_specific_recipient_mapping_available=false" in (
        irs_1099_snapshot.metadata.note or ""
    )
    assert "current_demand_conversion_available=false" in (
        irs_1099_snapshot.metadata.note or ""
    )
    assert "tax_clawback_gate_passed=false" in (irs_1099_snapshot.metadata.note or "")
    assert len(irs_1099_snapshot.records) == 7
    assert (
        irs_1099_snapshot.records[0]["cashflow_component"]
        == "deposit_and_private_interest"
    )
    assert irs_1099_snapshot.records[1]["cashflow_component"] == "treasury_interest"
    assert (
        irs_1099_snapshot.records[3]["cashflow_component"]
        == "money_market_fund_distribution_tax_context"
    )
    assert irs_1099_snapshot.records[0]["main_ratio_admission_allowed"] == "false"
    assert (
        irs_1099_snapshot.records[5]["cashflow_component"]
        == "tax_deferred_or_exempt_recipient_constraint"
    )
    assert (
        irs_1099_snapshot.records[6]["cashflow_component"]
        == "foreign_payee_reporting_exclusion_constraint"
    )
    assert (
        irs_1099_snapshot.records[5]["source_specific_tax_account_mapping_available"]
        == "true"
    )

    assert fta_state_rate_snapshot.metadata.source_id == (
        "federation_of_tax_administrators"
    )
    assert fta_state_rate_snapshot.metadata.snapshot_kind == "live_html_table_context"
    assert (
        fta_state_rate_snapshot.metadata.units
        == "state_individual_income_tax_rate_context"
    )
    assert fta_state_rate_snapshot.metadata.frequency == "annual"
    assert fta_state_rate_snapshot.metadata.source_release_at == "2025-01-01"
    assert "source_record_count=51" in (fta_state_rate_snapshot.metadata.note or "")
    assert "state_tax_rate_mapping_available=true" in (
        fta_state_rate_snapshot.metadata.note or ""
    )
    assert "source_specific_recipient_mapping_available=false" in (
        fta_state_rate_snapshot.metadata.note or ""
    )
    assert "current_demand_conversion_available=false" in (
        fta_state_rate_snapshot.metadata.note or ""
    )
    assert "tax_clawback_gate_passed=false" in (
        fta_state_rate_snapshot.metadata.note or ""
    )
    assert len(fta_state_rate_snapshot.records) == 51
    assert fta_state_rate_snapshot.records[0]["state_postal_code"] == "AL"
    assert fta_state_rate_snapshot.records[0]["tax_rate_high_percent"] == "5.0"
    assert (
        fta_state_rate_snapshot.records[1]["no_state_individual_income_tax"] == "true"
    )
    assert fta_state_rate_snapshot.records[-1]["state_postal_code"] == "DC"
    assert fta_state_rate_snapshot.records[-1]["tax_rate_high_percent"] == "10.75"
    assert fta_state_rate_snapshot.records[0]["main_ratio_admission_allowed"] == "false"

    assert tic_custody_snapshot.metadata.source_id == "treasury_tic"
    assert tic_custody_snapshot.metadata.snapshot_kind == "live_text_context"
    assert (
        tic_custody_snapshot.metadata.units
        == "custody_beneficial_owner_limitation_context"
    )
    assert tic_custody_snapshot.metadata.frequency == "guidance_page_specific"
    assert "source_record_count=1" in (tic_custody_snapshot.metadata.note or "")
    assert "custodial_data_basis_verified=true" in (
        tic_custody_snapshot.metadata.note or ""
    )
    assert "beneficial_owner_complete_accuracy_available=false" in (
        tic_custody_snapshot.metadata.note or ""
    )
    assert "holder_allocation_promotion_allowed=false" in (
        tic_custody_snapshot.metadata.note or ""
    )
    assert len(tic_custody_snapshot.records) == 1
    assert (
        tic_custody_snapshot.records[0]["third_country_custody_limitation_verified"]
        == "true"
    )
    assert tic_custody_snapshot.records[0]["main_ratio_admission_allowed"] == "false"

    assert fed_cross_border_snapshot.metadata.source_id == "fed_feds_notes"
    assert (
        fed_cross_border_snapshot.metadata.snapshot_kind
        == "live_html_and_accessible_context"
    )
    assert (
        fed_cross_border_snapshot.metadata.units
        == "foreign_treasury_method_bridge_context"
    )
    assert fed_cross_border_snapshot.metadata.frequency == "research_note_specific"
    assert "source_record_count=5" in (fed_cross_border_snapshot.metadata.note or "")
    assert "public_z1_efa_proxy_available=true" in (
        fed_cross_border_snapshot.metadata.note or ""
    )
    assert "domestic_demand_timing_bridge=false" in (
        fed_cross_border_snapshot.metadata.note or ""
    )
    assert "holder_allocation_enabled=false" in (
        fed_cross_border_snapshot.metadata.note or ""
    )
    assert len(fed_cross_border_snapshot.records) == 5
    assert fed_cross_border_snapshot.records[0]["metric"] == (
        "tic_undercount_estimate_end_2024"
    )
    assert fed_cross_border_snapshot.records[0]["promotion_gate_passed"] == "false"

    assert len(ira_snapshot.records) == 64
    assert {
        "date",
        "tax_year",
        "agi_class",
        "ira_plan_type",
        "contribution_taxpayers",
        "contribution_amount_thousand_usd",
        "fair_market_value_taxpayers",
        "fair_market_value_amount_thousand_usd",
        "account_type_context",
    } <= set(ira_snapshot.records[0])
    assert ira_snapshot.records[0]["agi_class"] == "All taxpayers"
    assert ira_snapshot.records[0]["ira_plan_type"] == "traditional_ira"
    assert (
        ira_snapshot.records[0]["account_type_context"]
        == "tax_deferred_or_tax_preferred_retirement_account_context"
    )
    assert len(average_tax_rate_snapshot.records) == 2760
    assert {
        "date",
        "tax_year",
        "source_table_id",
        "measure",
        "percentile_group",
        "value",
        "unit",
        "tax_rate_distribution_context",
        "full_tax_incidence_available",
        "current_demand_conversion_available",
    } <= set(average_tax_rate_snapshot.records[0])
    assert average_tax_rate_snapshot.records[0]["measure"] == "number_of_returns"
    assert average_tax_rate_snapshot.records[0]["percentile_group"] == "total"
    assert average_tax_rate_snapshot.records[0]["value"] == "119370886"
    assert average_tax_rate_snapshot.records[-1]["measure"] == "total_income_tax_share"
    assert average_tax_rate_snapshot.records[-1]["percentile_group"] == "top_50_percent"

    assert len(snapshot.records) == 37
    assert {
        "date",
        "tax_year",
        "filing_year",
        "return_population",
        "agi_class",
        "taxable_interest_number_of_returns",
        "taxable_interest_amount_thousand_usd",
        "tax_exempt_interest_number_of_returns",
        "tax_exempt_interest_amount_thousand_usd",
        "income_tax_before_credits_amount_thousand_usd",
    } <= set(snapshot.records[0])
    assert snapshot.records[0]["return_population"] == "all_returns_total"
    assert snapshot.records[0]["taxable_interest_amount_thousand_usd"] == "313812674"
    assert snapshot.records[-1]["return_population"] == "nontaxable_returns_total"

    recipient_rows = list(
        csv.DictReader(
            Path("outputs/tables/ratewall_recipient_leakage_design_gate.csv").open(
                encoding="utf-8"
            )
        )
    )
    tax_row = next(
        row
        for row in recipient_rows
        if row["cashflow_component"] == "interest_income_tax_clawback"
    )
    assert tax_row["source_context_series_ids"] == (
        "PII;W055RC1;NA000309Q;irs_soi_taxable_interest;"
        "irs_soi_ira_type_agi;irs_soi_average_tax_rate_percentile;"
        "fed_dfa_household_account_type_context;"
        "fed_scf_2022_safe_asset_account_tax_context;"
        "irs_estimated_tax_payment_timing;"
        "irs_soi_state_interest_agi;treasury_security_interest_tax_treatment;"
        "FDHBPIN;FDHBFIN;FDHBFRBN;BOGZ1LM153061105Q;"
        "BOGZ1FL763061100Q;BOGZ1FL633061105Q;"
        "BOGZ1FL653061105Q;BOGZ1FL573061105Q;"
        "tic_foreign_treasury_stock_split;tic_treasury_sector_transactions;"
        "ofr_mmf_treasury_holdings;sec_nmfp_mmf_treasury_cusip_holdings;"
        "irs_interest_received_tax_topic_403;"
        "irs_publication_550_interest_income_taxonomy;"
        "irs_1099_int_div_reporting_taxonomy;"
        "fta_state_individual_income_tax_rates;"
        "cbo_capital_tax_rates"
    )
    assert "NA000309Q:" in tax_row["source_record_count_summary"]
    assert "irs_soi_taxable_interest:37" in tax_row["source_record_count_summary"]
    assert "irs_soi_ira_type_agi:64" in tax_row["source_record_count_summary"]
    assert (
        "irs_soi_average_tax_rate_percentile:2760"
        in (tax_row["source_record_count_summary"])
    )
    assert (
        "fed_dfa_household_account_type_context:6"
        in (tax_row["source_record_count_summary"])
    )
    assert (
        "fed_scf_2022_safe_asset_account_tax_context:12"
        in (tax_row["source_record_count_summary"])
    )
    assert (
        "irs_estimated_tax_payment_timing:4" in (tax_row["source_record_count_summary"])
    )
    assert "irs_soi_state_interest_agi:594" in (tax_row["source_record_count_summary"])
    assert (
        "treasury_security_interest_tax_treatment:1"
        in (tax_row["source_record_count_summary"])
    )
    for source_count in [
        "FDHBPIN:224",
        "FDHBFIN:223",
        "FDHBFRBN:224",
        "BOGZ1LM153061105Q:321",
        "BOGZ1FL763061100Q:321",
        "BOGZ1FL633061105Q:321",
        "BOGZ1FL653061105Q:321",
        "BOGZ1FL573061105Q:321",
        "tic_foreign_treasury_stock_split:3",
        "tic_treasury_sector_transactions:541",
        "ofr_mmf_treasury_holdings:6",
        "sec_nmfp_mmf_treasury_cusip_holdings:668",
    ]:
        assert source_count in tax_row["source_record_count_summary"]
    assert (
        "irs_interest_received_tax_topic_403:4"
        in (tax_row["source_record_count_summary"])
    )
    assert (
        "irs_publication_550_interest_income_taxonomy:7"
        in (tax_row["source_record_count_summary"])
    )
    assert (
        "irs_1099_int_div_reporting_taxonomy:7"
        in (tax_row["source_record_count_summary"])
    )
    assert (
        "fta_state_individual_income_tax_rates:51"
        in (tax_row["source_record_count_summary"])
    )
    assert "cbo_capital_tax_rates:0" in (tax_row["source_record_count_summary"])
    assert (
        "irs_soi_taxable_interest:2023-01-01..2023-01-01"
        in (tax_row["source_record_date_bounds_summary"])
    )
    assert "NA000309Q:" in tax_row["source_record_date_bounds_summary"]
    assert (
        "irs_soi_ira_type_agi:2022-01-01..2022-01-01"
        in (tax_row["source_record_date_bounds_summary"])
    )
    assert (
        "irs_soi_average_tax_rate_percentile:2001-01-01..2023-01-01"
        in tax_row["source_record_date_bounds_summary"]
    )
    assert (
        "fed_dfa_household_account_type_context:2025-10-01..2025-10-01"
        in (tax_row["source_record_date_bounds_summary"])
    )
    assert (
        "fed_scf_2022_safe_asset_account_tax_context:2022-01-01..2022-01-01"
        in tax_row["source_record_date_bounds_summary"]
    )
    assert (
        "irs_estimated_tax_payment_timing:annual_recurring_q1..annual_recurring_q4"
        in tax_row["source_record_date_bounds_summary"]
    )
    assert (
        "irs_soi_state_interest_agi:2022-01-01..2022-01-01"
        in (tax_row["source_record_date_bounds_summary"])
    )
    assert (
        "treasury_security_interest_tax_treatment:"
        "guidance_page_current..guidance_page_current"
        in tax_row["source_record_date_bounds_summary"]
    )
    for source_dates in [
        "FDHBPIN:1970-01-01..2025-10-01",
        "FDHBFIN:1970-01-01..2025-07-01",
        "FDHBFRBN:1970-01-01..2025-10-01",
        "BOGZ1LM153061105Q:1945-10-01..2025-10-01",
        "BOGZ1FL763061100Q:1945-10-01..2025-10-01",
        "BOGZ1FL633061105Q:1945-10-01..2025-10-01",
        "BOGZ1FL653061105Q:1945-10-01..2025-10-01",
        "BOGZ1FL573061105Q:1945-10-01..2025-10-01",
        "tic_foreign_treasury_stock_split:December 2025..December 2025",
        "tic_treasury_sector_transactions:1978-01..2023-01",
        "ofr_mmf_treasury_holdings:2026-03-31..2026-03-31",
        "sec_nmfp_mmf_treasury_cusip_holdings:2025-11-30..2026-04-30",
    ]:
        assert source_dates in tax_row["source_record_date_bounds_summary"]
    assert (
        "irs_interest_received_tax_topic_403:"
        "guidance_page_current..guidance_page_current"
        in tax_row["source_record_date_bounds_summary"]
    )
    assert (
        "irs_publication_550_interest_income_taxonomy:"
        "guidance_page_current..guidance_page_current"
        in tax_row["source_record_date_bounds_summary"]
    )
    assert (
        "irs_1099_int_div_reporting_taxonomy:"
        "guidance_page_current..guidance_page_current"
        in tax_row["source_record_date_bounds_summary"]
    )
    assert (
        "fta_state_individual_income_tax_rates:2024-01-01..2024-01-01"
        in tax_row["source_record_date_bounds_summary"]
    )
    assert (
        "cbo_capital_tax_rates:missing" in tax_row["source_record_date_bounds_summary"]
    )
    assert tax_row["mechanical_cashflow_context_status"] == (
        "source_backed_personal_interest_tax_irs_soi_taxable_interest_"
        "federal_interest_persons_business_ira_average_tax_rate_"
        "dfa_scf_account_type_"
        "payment_timing_state_agi_treasury_and_irs_tax_treatment_"
        "treasury_holder_context_publication_550_1099_reporting_"
        "reportability_constraint_and_fta_state_rate_context_available_"
        "cbo_capital_tax_rate_"
        "registered_fetch_blocked_not_full_tax_incidence_or_"
        "current_demand"
    )
    assert tax_row["can_narrow_demand_conversion_prior"] == "false"
    assert tax_row["tax_output_enabled"] == "false"
    assert tax_row["welfare_claim_enabled"] == "false"
    assert tax_row["mpc_output_enabled"] == "false"

    registry_rows = list(
        csv.DictReader(
            Path("outputs/tables/ratewall_higher_rate_channel_registry.csv").open(
                encoding="utf-8"
            )
        )
    )
    registry_row = next(
        row
        for row in registry_rows
        if row["channel_name"] == "interest_income_tax_clawback_leakage"
    )
    assert (
        "admitted_source_ids=PII;W055RC1;NA000309Q;"
        "irs_soi_taxable_interest;irs_soi_ira_type_agi;"
        "irs_soi_average_tax_rate_percentile;"
        "fed_dfa_household_account_type_context;"
        "fed_scf_2022_safe_asset_account_tax_context;"
        "irs_estimated_tax_payment_timing;irs_soi_state_interest_agi;"
        "treasury_security_interest_tax_treatment;"
        "FDHBPIN;FDHBFIN;FDHBFRBN;BOGZ1LM153061105Q;"
        "BOGZ1FL763061100Q;BOGZ1FL633061105Q;"
        "BOGZ1FL653061105Q;BOGZ1FL573061105Q;"
        "tic_foreign_treasury_stock_split;tic_treasury_sector_transactions;"
        "ofr_mmf_treasury_holdings;sec_nmfp_mmf_treasury_cusip_holdings;"
        "irs_interest_received_tax_topic_403;"
        "irs_publication_550_interest_income_taxonomy;"
        "irs_1099_int_div_reporting_taxonomy;"
        "fta_state_individual_income_tax_rates"
    ) in (registry_row["source_status"])
    assert (
        "NA000309Q:https://fred.stlouisfed.org/graph/fredgraph.csv?id=NA000309Q"
        in registry_row["source_specific_urls_or_docs"]
    )
    assert (
        "irs_soi_taxable_interest:https://www.irs.gov/pub/irs-soi/23in14ar.xls"
        in (registry_row["source_specific_urls_or_docs"])
    )
    assert (
        "irs_soi_ira_type_agi:https://www.irs.gov/pub/irs-soi/22in03ira.xlsx"
        in (registry_row["source_specific_urls_or_docs"])
    )
    assert (
        "irs_soi_average_tax_rate_percentile:"
        "https://www.irs.gov/pub/irs-soi/23in41ts.xlsx"
        in registry_row["source_specific_urls_or_docs"]
    )
    assert (
        "fed_dfa_household_account_type_context:"
        "https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip"
    ) in registry_row["source_specific_urls_or_docs"]
    assert (
        "fed_scf_2022_safe_asset_account_tax_context:"
        "https://www.federalreserve.gov/econres/files/scfp2022excel.zip"
    ) in registry_row["source_specific_urls_or_docs"]
    assert (
        "irs_estimated_tax_payment_timing:"
        "https://www.irs.gov/payments/pay-as-you-go-so-you-wont-owe-a-guide-to-"
        "withholding-estimated-taxes-and-ways-to-avoid-the-estimated-tax-penalty"
    ) in registry_row["source_specific_urls_or_docs"]
    assert (
        "irs_soi_state_interest_agi:https://www.irs.gov/pub/irs-soi/22in55cmcsv.csv"
        in registry_row["source_specific_urls_or_docs"]
    )
    assert (
        "treasury_security_interest_tax_treatment:"
        "https://www.treasurydirect.gov/marketable-securities/"
        "tax-forms-and-withholding/" in registry_row["source_specific_urls_or_docs"]
    )
    assert (
        "irs_interest_received_tax_topic_403:https://www.irs.gov/taxtopics/tc403"
        in registry_row["source_specific_urls_or_docs"]
    )
    assert (
        "irs_publication_550_interest_income_taxonomy:"
        "https://www.irs.gov/publications/p550"
        in registry_row["source_specific_urls_or_docs"]
    )
    assert (
        "irs_1099_int_div_reporting_taxonomy:"
        "https://www.irs.gov/instructions/i1099int/"
        in registry_row["source_specific_urls_or_docs"]
    )
    assert (
        "fta_state_individual_income_tax_rates:"
        "https://taxadmin.org/2024-state-income-tax-rates/"
        in registry_row["source_specific_urls_or_docs"]
    )
    assert (
        "cbo_capital_tax_rates:not_in_current_snapshot"
        in registry_row["source_specific_urls_or_docs"]
    )
    assert registry_row["enters_main_offset_ratio"] == "false"
    assert registry_row["tax_output_enabled"] == "false"


def test_higher_rate_channel_source_context_snapshots_are_fail_closed() -> None:
    snapshots = {
        snapshot.metadata.series_id: snapshot
        for snapshot in read_snapshot_bundle(Path("data/raw/ratewall_snapshot.json"))
    }
    expected = {
        "TOTALSL": ("billions_of_dollars", "fast_repricing_consumer_credit", 100),
        "REVOLSL": ("billions_of_dollars", "fast_repricing_consumer_credit", 100),
        "NONREVSL": ("billions_of_dollars", "fast_repricing_consumer_credit", 100),
        "TERMCBCCALLNS": ("percent", "fast_repricing_consumer_credit", 100),
        "CDSP": ("percent", "fast_repricing_consumer_credit_payment_burden", 80),
        "DRCCLACBS": ("percent", "fast_repricing_consumer_credit_delinquency", 100),
        "DRCLACBS": ("percent", "fast_repricing_consumer_credit_delinquency", 100),
        "CREACBM027NBOG": (
            "billions_of_dollars",
            "cre_refinancing_bank_exposure",
            100,
        ),
        "DRCRELEXFACBS": (
            "percent",
            "cre_refinancing_delinquency",
            100,
        ),
        "CORCREXFACBS": (
            "percent",
            "cre_refinancing_chargeoff",
            100,
        ),
        "TLNRESCONS": (
            "millions_of_dollars_saar",
            "cre_nonresidential_construction_real_activity",
            100,
        ),
        "PNRESCONS": (
            "millions_of_dollars_saar",
            "cre_private_nonresidential_construction",
            100,
        ),
        "PBNRESCONS": (
            "millions_of_dollars_saar",
            "cre_public_nonresidential_construction",
            100,
        ),
        "PLODGCONS": (
            "millions_of_dollars_saar",
            "cre_private_lodging_construction",
            100,
        ),
        "PROFCONS": (
            "millions_of_dollars_saar",
            "cre_private_office_construction",
            100,
        ),
        "PRCOMCONS": (
            "millions_of_dollars_saar",
            "cre_private_commercial_construction",
            100,
        ),
        "PRHLTHCONS": (
            "millions_of_dollars_saar",
            "cre_private_health_care_construction",
            100,
        ),
        "PREDUCONS": (
            "millions_of_dollars_saar",
            "cre_private_educational_construction",
            100,
        ),
        "PRAMUSCONS": (
            "millions_of_dollars_saar",
            "cre_private_amusement_recreation_construction",
            100,
        ),
        "PRMFGCONS": (
            "millions_of_dollars_saar",
            "cre_private_manufacturing_construction",
            100,
        ),
        "MORTGAGE30US": ("percent", "mortgage_lockin_rate", 100),
        "B112RC1Q027SBEA": (
            "billions_of_dollars_saar",
            "state_local_cash_interest_receipts",
            100,
        ),
    }
    for series_id, (units, context_marker, minimum_records) in expected.items():
        snapshot = snapshots[series_id]
        assert snapshot.metadata.source_id == "fred"
        assert snapshot.metadata.snapshot_kind == "live"
        assert snapshot.metadata.units == units
        assert len(snapshot.records) >= minimum_records
        note = snapshot.metadata.note or ""
        assert f"{context_marker}_context_only" in note
        assert "higher_rate_channel_gate_passed=false" in note
        assert "prior_narrowing_allowed=false" in note
        assert "main_ratio_admission_allowed=false" in note

    cfpb_card_context = snapshots["cfpb_credit_card_market_figure_data_2025"]
    assert cfpb_card_context.metadata.source_id == "cfpb"
    assert cfpb_card_context.metadata.snapshot_kind == "live_workbook_context"
    assert (
        cfpb_card_context.metadata.units
        == "payment_balance_repricing_utilization_context"
    )
    assert len(cfpb_card_context.records) == 274
    cfpb_note = cfpb_card_context.metadata.note or ""
    assert (
        "cfpb_credit_card_market_payment_balance_repricing_utilization_context_only"
    ) in cfpb_note
    assert "source_workbook_sha256=" in cfpb_note
    assert "source_record_count=274" in cfpb_note
    assert "minimum_payment_behavior_context_available=true" in cfpb_note
    assert "balance_by_credit_score_context_available=true" in cfpb_note
    assert "repricing_context_available=true" in cfpb_note
    assert "utilization_context_available=true" in cfpb_note
    assert "borrower_level_microdata_available=false" in cfpb_note
    assert "current_demand_conversion_available=false" in cfpb_note
    assert "split_denominator_promotion_allowed=false" in cfpb_note
    assert (
        cfpb_card_context.records[0]["denominator_prior_narrowing_allowed"] == "false"
    )
    assert cfpb_card_context.records[0]["main_ratio_admission_allowed"] == "false"

    cfpb_cct_context = snapshots["cfpb_consumer_credit_trends_all_data"]
    assert cfpb_cct_context.metadata.source_id == "cfpb"
    assert cfpb_cct_context.metadata.snapshot_kind == "live_csv_context"
    assert (
        cfpb_cct_context.metadata.units == "consumer_credit_trends_source_table_units"
    )
    assert len(cfpb_cct_context.records) == 51426
    cfpb_cct_note = cfpb_cct_context.metadata.note or ""
    assert "cfpb_consumer_credit_trends_product_score_income_age_context_only" in (
        cfpb_cct_note
    )
    assert "source_csv_sha256=" in cfpb_cct_note
    assert "source_codebook_sha256=" in cfpb_cct_note
    assert "source_record_count=51426" in cfpb_cct_note
    assert "credit_score_distribution_context_available=true" in cfpb_cct_note
    assert "income_distribution_context_available=true" in cfpb_cct_note
    assert "borrower_level_microdata_available=false" in cfpb_cct_note
    assert "payment_behavior_context_available=false" in cfpb_cct_note
    assert "current_demand_conversion_available=false" in cfpb_cct_note
    assert "split_denominator_promotion_allowed=false" in cfpb_cct_note
    assert cfpb_cct_context.records[0]["denominator_prior_narrowing_allowed"] == "false"
    assert cfpb_cct_context.records[0]["main_ratio_admission_allowed"] == "false"

    cfpb_mem_context = snapshots["cfpb_making_ends_meet_sample1_public_use"]
    assert cfpb_mem_context.metadata.source_id == "cfpb"
    assert cfpb_mem_context.metadata.snapshot_kind == "live_zip_csv_public_use_context"
    assert cfpb_mem_context.metadata.units == "public_use_survey_credit_panel_context"
    assert len(cfpb_mem_context.records) == 1
    cfpb_mem_note = cfpb_mem_context.metadata.note or ""
    assert "cfpb_mem_public_use_borrower_liquidity_payment_context_only" in (
        cfpb_mem_note
    )
    assert "source_zip_sha256=" in cfpb_mem_note
    assert "source_record_count=2986" in cfpb_mem_note
    assert "source_column_count=612" in cfpb_mem_note
    assert "borrower_level_public_survey_microdata_available=true" in (cfpb_mem_note)
    assert "credit_card_payment_behavior_context_available=true" in cfpb_mem_note
    assert "liquidity_context_available=true" in cfpb_mem_note
    assert "bill_payment_stress_context_available=true" in cfpb_mem_note
    assert "borrower_level_credit_bureau_microdata_available=false" in (cfpb_mem_note)
    assert "rate_sensitive_payment_drag_transmission_available=false" in (cfpb_mem_note)
    assert "current_demand_conversion_available=false" in cfpb_mem_note
    cfpb_mem_record = cfpb_mem_context.records[0]
    assert cfpb_mem_record["source_csv_row_count"] == "2986"
    assert cfpb_mem_record["source_csv_column_count"] == "612"
    assert cfpb_mem_record["borrower_level_public_survey_microdata_available"] == "true"
    assert cfpb_mem_record["main_ratio_admission_allowed"] == "false"
    assert cfpb_mem_record["incidence_output_enabled"] == "false"

    cfpb_mem_multisample = snapshots["cfpb_making_ends_meet_samples_3_6_public_use"]
    assert cfpb_mem_multisample.metadata.source_id == "cfpb"
    assert (
        cfpb_mem_multisample.metadata.snapshot_kind
        == "live_zip_csv_multisample_public_use_context"
    )
    assert (
        cfpb_mem_multisample.metadata.units == "public_use_multisample_schema_context"
    )
    assert len(cfpb_mem_multisample.records) == 4
    cfpb_mem_multisample_note = cfpb_mem_multisample.metadata.note or ""
    assert (
        "cfpb_mem_samples_3_6_public_use_multisample_harmonized_context_only"
        in cfpb_mem_multisample_note
    )
    assert "source_record_count=4" in cfpb_mem_multisample_note
    assert "underlying_public_use_row_count=10004" in cfpb_mem_multisample_note
    assert "sample_3:2125" in cfpb_mem_multisample_note
    assert "sample_4:2136" in cfpb_mem_multisample_note
    assert "sample_5:3113" in cfpb_mem_multisample_note
    assert "sample_6:2630" in cfpb_mem_multisample_note
    assert "survey_wave_start=2022-01-01" in cfpb_mem_multisample_note
    assert "survey_wave_latest=2025-01-01" in cfpb_mem_multisample_note
    assert "borrower_level_public_survey_microdata_available=true" in (
        cfpb_mem_multisample_note
    )
    assert "rate_sensitive_payment_drag_transmission_available=false" in (
        cfpb_mem_multisample_note
    )
    assert "current_demand_conversion_available=false" in cfpb_mem_multisample_note
    cfpb_mem_multisample_rows = {
        row["sample_id"]: row for row in cfpb_mem_multisample.records
    }
    assert cfpb_mem_multisample_rows["sample_3"]["source_csv_row_count"] == "2125"
    assert cfpb_mem_multisample_rows["sample_6"]["source_csv_column_count"] == "346"
    assert (
        cfpb_mem_multisample_rows["sample_3"][
            "credit_score_self_report_context_available"
        ]
        == "false"
    )
    assert {
        row["split_denominator_promotion_allowed"]
        for row in cfpb_mem_multisample.records
    } == {"false"}
    assert {
        row["main_ratio_admission_allowed"] for row in cfpb_mem_multisample.records
    } == {"false"}

    philly_y14_context = snapshots[
        "philadelphia_fed_y14_large_bank_credit_card_context"
    ]
    assert philly_y14_context.metadata.source_id == "philadelphia_fed"
    assert philly_y14_context.metadata.snapshot_kind == "live_csv_context"
    assert (
        philly_y14_context.metadata.units == "aggregate_large_bank_credit_card_context"
    )
    assert len(philly_y14_context.records) == 108
    philly_y14_note = philly_y14_context.metadata.note or ""
    assert "philadelphia_fed_y14_large_bank_credit_card_aggregate_context_only" in (
        philly_y14_note
    )
    assert "source_record_count=108" in philly_y14_note
    assert "balances_row_count=54" in philly_y14_note
    assert "originations_row_count=54" in philly_y14_note
    assert "first_observation_date=2012-09-30" in philly_y14_note
    assert "latest_observation_date=2025-12-31" in philly_y14_note
    assert "payment_behavior_context_available=true" in philly_y14_note
    assert "purchase_volume_context_available=true" in philly_y14_note
    assert "purchase_apr_context_available=true" in philly_y14_note
    assert "origination_context_available=true" in philly_y14_note
    assert "current_demand_response_available=false" in philly_y14_note
    assert "rate_sensitive_payment_drag_transmission_available=false" in (
        philly_y14_note
    )
    assert philly_y14_context.records[0]["main_ratio_admission_allowed"] == "false"
    assert (
        philly_y14_context.records[0]["denominator_prior_narrowing_allowed"] == "false"
    )

    dfa_liability_context = snapshots["fed_dfa_household_liability_context"]
    assert dfa_liability_context.metadata.source_id == "fed_dfa"
    assert dfa_liability_context.metadata.snapshot_kind == "live"
    assert dfa_liability_context.metadata.units == "millions_of_dollars"
    assert dfa_liability_context.metadata.frequency == "quarterly"
    assert dfa_liability_context.metadata.source_release_at == "2025:Q4"
    assert len(dfa_liability_context.records) == 6
    dfa_liability_note = dfa_liability_context.metadata.note or ""
    assert (
        "fast_repricing_consumer_credit_dfa_liability_liquidity_context_only"
        in dfa_liability_note
    )
    assert "source_record_count=6" in dfa_liability_note
    assert "product_balance_context_available=true" in dfa_liability_note
    assert "liquid_asset_proxy_context_available=true" in dfa_liability_note
    assert "borrower_level_microdata_available=false" in dfa_liability_note
    assert "current_demand_conversion_available=false" in dfa_liability_note
    assert "split_denominator_promotion_allowed=false" in dfa_liability_note
    assert {
        "date",
        "as_of_date",
        "wealth_group",
        "liabilities_mil",
        "consumer_credit_mil",
        "liquid_assets_proxy_mil",
        "split_denominator_promotion_allowed",
    } <= set(dfa_liability_context.records[0])
    assert (
        dfa_liability_context.records[0]["split_denominator_promotion_allowed"]
        == "false"
    )
    assert dfa_liability_context.records[0]["incidence_output_enabled"] == "false"

    scf_context = snapshots["fed_scf_2022_summary_extract_context"]
    assert scf_context.metadata.source_id == "fed_scf"
    assert scf_context.metadata.snapshot_kind == "live_zip_csv_context"
    assert scf_context.metadata.units == "2022_dollars_and_survey_flags"
    assert scf_context.metadata.frequency == "triennial_cross_section"
    assert scf_context.metadata.source_release_at == "2024-04-03"
    assert len(scf_context.records) == 22975
    scf_note = scf_context.metadata.note or ""
    assert "fed_scf_public_summary_extract_debt_liquidity_payment_context_only" in (
        scf_note
    )
    assert "source_zip_sha256=" in scf_note
    assert "source_record_count=22975" in scf_note
    assert "public_family_level_record_context_available=true" in scf_note
    assert "liquidity_context_available=true" in scf_note
    assert "payment_behavior_context_available=true" in scf_note
    assert "borrower_level_credit_bureau_microdata_available=false" in scf_note
    assert "current_demand_conversion_available=false" in scf_note
    assert "split_denominator_promotion_allowed=false" in scf_note
    assert {
        "date",
        "survey_year",
        "income",
        "liq",
        "ccbal",
        "debt",
        "conspay",
        "revpay",
        "pirrev",
        "split_denominator_promotion_allowed",
    } <= set(scf_context.records[0])
    assert scf_context.records[0]["source_csv_schema_reviewed"] == "true"
    assert scf_context.records[0]["main_ratio_admission_allowed"] == "false"
    assert scf_context.records[0]["incidence_output_enabled"] == "false"

    scf_weighted = snapshots["fed_scf_2022_weighted_consumer_credit_summary_context"]
    assert scf_weighted.metadata.source_id == "fed_scf"
    assert (
        scf_weighted.metadata.snapshot_kind == "live_zip_csv_weighted_summary_context"
    )
    assert scf_weighted.metadata.units == "2022_dollars_weighted_summary_context"
    assert scf_weighted.metadata.frequency == "triennial_cross_section"
    assert scf_weighted.metadata.source_release_at == "2024-04-03"
    assert len(scf_weighted.records) == 23
    scf_weighted_note = scf_weighted.metadata.note or ""
    assert (
        "fed_scf_public_summary_extract_weighted_consumer_credit_review_context_only"
        in scf_weighted_note
    )
    assert "source_record_count=23" in scf_weighted_note
    assert "source_extract_record_count=22975" in scf_weighted_note
    assert "survey_design_weighted_summary_available=true" in scf_weighted_note
    assert "replicate_weight_uncertainty_available=false" in scf_weighted_note
    assert "current_demand_conversion_available=false" in scf_weighted_note
    assert "split_denominator_promotion_allowed=false" in scf_weighted_note
    all_summary = scf_weighted.records[0]
    assert all_summary["group_dimension"] == "all"
    assert all_summary["source_public_extract_record_count"] == "22975"
    assert all_summary["source_public_family_count"] == "4595"
    assert all_summary["summary_method"] == "weighted_descriptive_summary_context_only"
    assert all_summary["imputation_handling"] == "all_implicates_weight_divided_by_5"
    assert all_summary["survey_design_weighted_summary_available"] == "true"
    assert all_summary["replicate_weight_uncertainty_available"] == "false"
    assert all_summary["main_ratio_admission_allowed"] == "false"
    assert all_summary["incidence_output_enabled"] == "false"
    assert {
        "weighted_mean_debt",
        "weighted_median_debt",
        "weighted_mean_credit_card_balance",
        "weighted_mean_liquid_assets",
        "weighted_mean_consumer_payment",
        "weighted_mean_revolving_payment_income_ratio",
    } <= set(all_summary)

    scf_replicate = snapshots["fed_scf_2022_replicate_weight_methodology_context"]
    assert scf_replicate.metadata.source_id == "fed_scf"
    assert scf_replicate.metadata.snapshot_kind == "live_zip_dta_methodology_context"
    assert (
        scf_replicate.metadata.units
        == "replicate_weight_schema_and_methodology_context"
    )
    assert scf_replicate.metadata.frequency == "triennial_cross_section"
    assert scf_replicate.metadata.source_release_at == "2024-04-03"
    assert len(scf_replicate.records) == 1
    scf_replicate_note = scf_replicate.metadata.note or ""
    assert (
        "fed_scf_replicate_weight_schema_and_standard_error_methodology_context_only"
        in scf_replicate_note
    )
    assert "source_dta_observation_count=4595" in scf_replicate_note
    assert "source_dta_variable_count=2000" in scf_replicate_note
    assert "replicate_weight_variable_count=999" in scf_replicate_note
    assert "replicate_weight_uncertainty_source_available=true" in (scf_replicate_note)
    assert "replicate_weight_uncertainty_executed=false" in scf_replicate_note
    assert "current_demand_conversion_available=false" in scf_replicate_note
    replicate_record = scf_replicate.records[0]
    assert replicate_record["source_file"] == "p22_rw1.dta"
    assert replicate_record["source_dta_observation_count"] == "4595"
    assert replicate_record["source_dta_variable_count"] == "2000"
    assert replicate_record["replicate_weight_variable_count"] == "999"
    assert replicate_record["replicate_weight_first_variable"] == "wt1b1"
    assert replicate_record["replicate_weight_last_variable"] == "wt1b999"
    assert replicate_record["family_join_keys_available"] == "y1;yy1"
    assert replicate_record["replicate_weight_uncertainty_executed"] == "false"
    assert replicate_record["main_ratio_admission_allowed"] == "false"
    assert replicate_record["incidence_output_enabled"] == "false"

    scf_uncertainty = snapshots["fed_scf_2022_consumer_credit_uncertainty_context"]
    assert scf_uncertainty.metadata.source_id == "fed_scf"
    assert (
        scf_uncertainty.metadata.snapshot_kind == "live_zip_csv_dta_uncertainty_context"
    )
    assert scf_uncertainty.metadata.units == "2022_dollars_weighted_uncertainty_context"
    assert scf_uncertainty.metadata.frequency == "triennial_cross_section"
    assert scf_uncertainty.metadata.source_release_at == "2024-04-03"
    assert len(scf_uncertainty.records) >= 1
    scf_uncertainty_note = scf_uncertainty.metadata.note or ""
    assert "fed_scf_joined_replicate_weight_uncertainty_review_context_only" in (
        scf_uncertainty_note
    )
    assert "source_record_count=" in scf_uncertainty_note
    assert "summary_extract_join_executed=true" in scf_uncertainty_note
    assert "replicate_weight_uncertainty_executed=true" in scf_uncertainty_note
    assert "current_demand_conversion_available=false" in scf_uncertainty_note
    uncertainty_record = scf_uncertainty.records[0]
    assert uncertainty_record["summary_method"] == (
        "scf_meanit_replicate_weight_uncertainty_review_context_only"
    )
    assert uncertainty_record["combined_standard_error_formula"] == (
        "sqrt((6/5)*imputation_variance+sampling_variance)"
    )
    assert uncertainty_record["replicate_estimate_count"] == "999"
    assert uncertainty_record["schema_support_check_passed"] == "true"
    assert uncertainty_record["main_ratio_admission_allowed"] == "false"
    assert uncertainty_record["incidence_output_enabled"] == "false"

    nyfed_ccp_context = snapshots["nyfed_consumer_credit_panel_faq"]
    assert nyfed_ccp_context.metadata.source_id == "ny_fed"
    assert nyfed_ccp_context.metadata.snapshot_kind == "live_text_context"
    assert (
        nyfed_ccp_context.metadata.units == "consumer_credit_panel_access_scope_context"
    )
    assert len(nyfed_ccp_context.records) == 1
    nyfed_note = nyfed_ccp_context.metadata.note or ""
    assert "nyfed_consumer_credit_panel_access_scope_context_only" in nyfed_note
    assert "ccp_microdata_access_limited=true" in nyfed_note
    assert "aggregate_data_bank_available=true" in nyfed_note
    assert "custom_cuts_available=false" in nyfed_note
    assert "transactor_revolver_split_available=false" in nyfed_note
    assert "current_demand_conversion_available=false" in nyfed_note
    assert nyfed_ccp_context.records[0]["borrower_level_microdata_admitted"] == "false"
    assert (
        nyfed_ccp_context.records[0]["split_denominator_promotion_allowed"] == "false"
    )

    nyfed_hhdc_context = snapshots["nyfed_household_debt_credit_report_2026q1"]
    assert nyfed_hhdc_context.metadata.source_id == "ny_fed"
    assert nyfed_hhdc_context.metadata.snapshot_kind == "live_workbook_context"
    assert nyfed_hhdc_context.metadata.units == "household_debt_credit_report_context"
    assert len(nyfed_hhdc_context.records) == 21259
    nyfed_hhdc_note = nyfed_hhdc_context.metadata.note or ""
    assert (
        "nyfed_household_debt_credit_product_age_state_delinquency_context_only"
        in nyfed_hhdc_note
    )
    assert "source_workbook_sha256=" in nyfed_hhdc_note
    assert "source_record_count=21259" in nyfed_hhdc_note
    assert "source_data_sheet_count=36" in nyfed_hhdc_note
    assert "age_distribution_context_available=true" in nyfed_hhdc_note
    assert "state_distribution_context_available=true" in nyfed_hhdc_note
    assert "delinquency_transition_context_available=true" in nyfed_hhdc_note
    assert "borrower_level_microdata_available=false" in nyfed_hhdc_note
    assert "income_distribution_available=false" in nyfed_hhdc_note
    assert "current_demand_conversion_available=false" in nyfed_hhdc_note
    assert "split_denominator_promotion_allowed=false" in nyfed_hhdc_note
    assert nyfed_hhdc_context.records[0]["source_workbook_schema_reviewed"] == "true"
    assert nyfed_hhdc_context.records[0]["main_ratio_admission_allowed"] == "false"

    for series_id in (
        "sloos_consumer_lending",
        "sloos_cre",
        "sloos_ndfi_special_questions",
    ):
        snapshot = snapshots[series_id]
        assert snapshot.metadata.source_id == "fed_sloos"
        assert snapshot.metadata.snapshot_kind == "live_text_context"
        assert snapshot.metadata.units == "qualitative_survey_context"
        assert len(snapshot.records) == 1
        note = snapshot.metadata.note or ""
        assert "sloos_official_release_context_only" in note
        assert "source_markers_verified=true" in note
        assert "denominator_prior_narrowing_allowed=false" in note
        assert "split_denominator_promotion_allowed=false" in note
        assert snapshot.records[0]["promotion_gate_passed"] == "false"
        if series_id == "sloos_cre":
            assert "cre_dscr_term_context_available=true" in note
            assert snapshot.records[0]["cre_dscr_term_context_available"] == "true"
            assert (
                "lowered debt service coverage ratios"
                in (snapshot.records[0]["source_marker_3"])
            )

    cre_maturity = snapshots["mba_cre_maturity_ladder_context"]
    assert cre_maturity.metadata.source_id == "mba_newslink"
    assert cre_maturity.metadata.snapshot_kind == "live_text_context"
    assert cre_maturity.metadata.units == "billions_of_dollars_and_share"
    assert len(cre_maturity.records) == 1
    assert cre_maturity.records[0]["maturity_year"] == "2026"
    assert cre_maturity.records[0]["maturing_balance_bil"] == "875"
    assert cre_maturity.records[0]["split_denominator_promotion_allowed"] == "false"
    assert "mba_cre_maturity_context_only" in (cre_maturity.metadata.note or "")

    ndfi_context = snapshots["fed_private_credit_notes"]
    assert ndfi_context.metadata.source_id == "fed_feds_notes"
    assert ndfi_context.metadata.snapshot_kind == "live_text_context"
    assert ndfi_context.metadata.units == "qualitative_research_note_context"
    assert len(ndfi_context.records) == 1
    assert ndfi_context.records[0]["floating_rate_marker_verified"] == "true"
    assert ndfi_context.records[0]["exposure_size_available"] == "false"
    assert ndfi_context.records[0]["borrower_pass_through_available"] == "false"
    assert ndfi_context.records[0]["split_denominator_promotion_allowed"] == "false"
    assert "fed_private_credit_transmission_context_only" in (
        ndfi_context.metadata.note or ""
    )

    ndfi_accessible_context = snapshots[
        "fed_private_credit_characteristics_accessible_data"
    ]
    assert ndfi_accessible_context.metadata.source_id == "fed_feds_notes"
    assert ndfi_accessible_context.metadata.snapshot_kind == "live_html_table_context"
    assert ndfi_accessible_context.metadata.units == "mixed_table_units"
    assert len(ndfi_accessible_context.records) == 426
    ndfi_accessible_note = ndfi_accessible_context.metadata.note or ""
    assert "fed_private_credit_characteristics_accessible_data_context_only" in (
        ndfi_accessible_note
    )
    assert "source_html_sha256=" in ndfi_accessible_note
    assert "source_record_count=426" in ndfi_accessible_note
    assert "source_tables=Figure 1-Figure 16 accessible data tables" in (
        ndfi_accessible_note
    )
    assert "private_credit_maturity_context_available=true" in ndfi_accessible_note
    assert "private_credit_exposure_size_context_available=true" in (
        ndfi_accessible_note
    )
    assert "private_credit_liquidity_context_available=true" in ndfi_accessible_note
    assert "borrower_rate_context_available=true" in ndfi_accessible_note
    assert "borrower_resilience_context_available=true" in ndfi_accessible_note
    assert "collateral_structure_context_available=true" in ndfi_accessible_note
    assert "borrower_pass_through_context_available=false" in ndfi_accessible_note
    assert "nonbank_to_real_activity_context_available=false" in ndfi_accessible_note
    assert "split_denominator_promotion_allowed=false" in ndfi_accessible_note
    assert ndfi_accessible_context.records[0]["metric"] == (
        "private_credit_allocation_scale_assets_under_management"
    )
    assert (
        ndfi_accessible_context.records[0][
            "private_credit_exposure_size_context_available"
        ]
        == "true"
    )
    assert (
        ndfi_accessible_context.records[0]["split_denominator_promotion_allowed"]
        == "false"
    )
    assert ndfi_accessible_context.records[0]["main_ratio_admission_allowed"] == "false"

    ndfi_bank_lending_context = snapshots[
        "fed_bank_lending_private_credit_financial_stability_context"
    ]
    assert ndfi_bank_lending_context.metadata.source_id == "fed_feds_notes"
    assert ndfi_bank_lending_context.metadata.snapshot_kind == (
        "live_html_table_context"
    )
    assert ndfi_bank_lending_context.metadata.units == (
        "bank_private_credit_exposure_stress_context"
    )
    assert len(ndfi_bank_lending_context.records) == 64
    ndfi_bank_lending_note = ndfi_bank_lending_context.metadata.note or ""
    assert "fed_bank_lending_private_credit_financial_stability_context_only" in (
        ndfi_bank_lending_note
    )
    assert "source_html_sha256=" in ndfi_bank_lending_note
    assert "source_record_count=64" in ndfi_bank_lending_note
    assert "credit_line_utilization_context_available=true" in (ndfi_bank_lending_note)
    assert "capital_liquidity_stress_context_available=true" in (ndfi_bank_lending_note)
    assert "public_reusable_loan_level_artifact_available=false" in (
        ndfi_bank_lending_note
    )
    assert "underlying_y14q_supervisory_data_publicly_reusable=false" in (
        ndfi_bank_lending_note
    )
    assert any(
        record["source_row_label"] == "BDCs"
        and record["metric"] == "loan_commitment_bil"
        and record["metric_value"] == "56"
        for record in ndfi_bank_lending_context.records
    )
    assert any(
        record["source_row_label"] == "Private Debt Funds"
        and record["metric"] == "average_interest_rate_pct"
        and record["metric_value"] == "6.6"
        for record in ndfi_bank_lending_context.records
    )
    assert {
        record["split_denominator_promotion_allowed"]
        for record in ndfi_bank_lending_context.records
    } == {"false"}

    ndfi_indirect_context = snapshots["fed_indirect_credit_supply_private_credit"]
    assert ndfi_indirect_context.metadata.source_id == "fed_feds"
    assert ndfi_indirect_context.metadata.snapshot_kind == "live_text_context"
    assert ndfi_indirect_context.metadata.units == "qualitative_research_paper_context"
    assert len(ndfi_indirect_context.records) == 1
    assert (
        ndfi_indirect_context.records[0][
            "bank_bdc_intermediation_chain_marker_verified"
        ]
        == "true"
    )
    assert (
        ndfi_indirect_context.records[0]["borrower_pass_through_available"]
        == "context_only_not_promotable"
    )
    assert (
        ndfi_indirect_context.records[0][
            "public_reusable_loan_level_artifact_available"
        ]
        == "false"
    )
    assert (
        ndfi_indirect_context.records[0]["split_denominator_promotion_allowed"]
        == "false"
    )

    ndfi_indirect_accessible_context = snapshots[
        "fed_indirect_credit_supply_accessible_materials"
    ]
    assert ndfi_indirect_accessible_context.metadata.source_id == "fed_feds"
    assert (
        ndfi_indirect_accessible_context.metadata.snapshot_kind
        == "live_accessible_zip_context"
    )
    assert (
        ndfi_indirect_accessible_context.metadata.units
        == "regression_and_accessible_figure_context"
    )
    ndfi_indirect_accessible_note = ndfi_indirect_accessible_context.metadata.note or ""
    assert "fed_indirect_credit_supply_accessible_materials_context_only" in (
        ndfi_indirect_accessible_note
    )
    assert "source_zip_sha256=" in ndfi_indirect_accessible_note
    assert "borrower_pass_through_context_available=true" in (
        ndfi_indirect_accessible_note
    )
    assert "nonbank_to_real_activity_context_available=true" in (
        ndfi_indirect_accessible_note
    )
    assert "public_reusable_loan_level_artifact_available=false" in (
        ndfi_indirect_accessible_note
    )
    assert "split_denominator_promotion_allowed=false" in (
        ndfi_indirect_accessible_note
    )
    assert len(ndfi_indirect_accessible_context.records) > 50
    assert any(
        record["source_table_title"]
        == "Table 8:  BDCs' Reliance on Bank Financing and Monetary Pass Through"
        and record["source_row_label"] == "BankLoanExpenseShare times Tightening"
        and record["source_column_label"] == "Interest Rate (3)"
        and record["coefficient"] == "0.313"
        for record in ndfi_indirect_accessible_context.records
    )
    assert any(
        record["source_table_title"]
        == "Table 9:  Real Effects of BDC Financing during Tightening"
        and record["source_row_label"] == "High BDC Reliance times Tightening"
        and record["source_column_label"] == "Interest Coverage (5)"
        and record["coefficient"] == "-1.84"
        for record in ndfi_indirect_accessible_context.records
    )
    assert {
        record["split_denominator_promotion_allowed"]
        for record in ndfi_indirect_accessible_context.records
    } == {"false"}

    ofr_ndfi_context = snapshots["ofr_private_credit_counterparty_exposure_context"]
    assert ofr_ndfi_context.metadata.source_id == "ofr_research"
    assert ofr_ndfi_context.metadata.snapshot_kind == "live_text_context"
    assert ofr_ndfi_context.metadata.units == "qualitative_research_brief_context"
    assert len(ofr_ndfi_context.records) == 1
    assert (
        ofr_ndfi_context.records[0]["counterparty_exposure_marker_verified"] == "true"
    )
    assert (
        ofr_ndfi_context.records[0]["exposure_size_available"]
        == "context_only_not_promotable"
    )
    assert (
        ofr_ndfi_context.records[0]["public_reusable_fund_level_artifact_available"]
        == "false"
    )
    assert ofr_ndfi_context.records[0]["split_denominator_promotion_allowed"] == "false"

    sec_form_pf_context = snapshots["sec_private_fund_statistics_aggregate_assets"]
    assert sec_form_pf_context.metadata.source_id == "sec_statistics"
    assert sec_form_pf_context.metadata.snapshot_kind == "live_json_context"
    assert sec_form_pf_context.metadata.units == "usd_aggregate_form_pf_statistics"
    assert len(sec_form_pf_context.records) > 1000
    sec_form_pf_note = sec_form_pf_context.metadata.note or ""
    assert "sec_form_pf_private_fund_aggregate_assets_context_only" in (
        sec_form_pf_note
    )
    assert "source_json_sha256=" in sec_form_pf_note
    assert "source_record_count=" in sec_form_pf_note
    assert "first_observation_date=2013-03-31" in sec_form_pf_note
    assert "latest_observation_date=2025-09-30" in sec_form_pf_note
    assert "form_pf_aggregate_statistics_available=true" in sec_form_pf_note
    assert "private_fund_exposure_size_context_available=true" in sec_form_pf_note
    assert "public_reusable_fund_level_artifact_available=false" in (sec_form_pf_note)
    assert "borrower_pass_through_context_available=false" in sec_form_pf_note
    assert "nonbank_to_real_activity_context_available=false" in sec_form_pf_note
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_form_pf_context.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"] for record in sec_form_pf_context.records
    } == {"false"}

    cfpb_payment_furnishing = snapshots["cfpb_payment_amount_furnishing_report"]
    assert cfpb_payment_furnishing.metadata.source_id == "cfpb"
    assert cfpb_payment_furnishing.metadata.snapshot_kind == "live_pdf_context"
    assert (
        cfpb_payment_furnishing.metadata.units
        == "actual_payment_furnishing_share_context"
    )
    assert len(cfpb_payment_furnishing.records) == 7
    payment_furnishing_note = cfpb_payment_furnishing.metadata.note or ""
    assert "cfpb_payment_amount_furnishing_credit_bureau_context_only" in (
        payment_furnishing_note
    )
    assert "source_pdf_sha256=" in payment_furnishing_note
    assert "source_record_count=7" in payment_furnishing_note
    assert "observation_date=2020-03-31" in payment_furnishing_note
    assert "actual_payment_furnishing_context_available=true" in (
        payment_furnishing_note
    )
    assert "rate_sensitive_payment_drag_transmission_available=false" in (
        payment_furnishing_note
    )
    assert any(
        record["loan_type"] == "credit_card"
        and record["actual_payment_amount_furnished_pct"] == "40"
        and record["revolving_credit_payment_gap_context_available"] == "true"
        for record in cfpb_payment_furnishing.records
    )
    assert {
        record["split_denominator_promotion_allowed"]
        for record in cfpb_payment_furnishing.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"]
        for record in cfpb_payment_furnishing.records
    } == {"false"}

    cfpb_revolvers = snapshots["cfpb_credit_card_revolvers_data_point"]
    assert cfpb_revolvers.metadata.source_id == "cfpb"
    assert cfpb_revolvers.metadata.snapshot_kind == "live_pdf_context"
    assert (
        cfpb_revolvers.metadata.units
        == "credit_card_revolver_duration_repayment_context"
    )
    assert len(cfpb_revolvers.records) == 12
    revolvers_note = cfpb_revolvers.metadata.note or ""
    assert "cfpb_credit_card_revolver_duration_repayment_context_only" in (
        revolvers_note
    )
    assert "source_pdf_sha256=" in revolvers_note
    assert "source_record_count=12" in revolvers_note
    assert "sample_start=2008-04-01" in revolvers_note
    assert "sample_end=2016-04-30" in revolvers_note
    assert "rate_sensitive_payment_drag_transmission_available=false" in (
        revolvers_note
    )
    assert any(
        record["metric"] == "outstanding_balance_revolved_share"
        and record["metric_value"] == "82"
        and record["payment_behavior_context_available"] == "true"
        for record in cfpb_revolvers.records
    )
    assert {
        record["split_denominator_promotion_allowed"]
        for record in cfpb_revolvers.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"] for record in cfpb_revolvers.records
    } == {"false"}

    cfpb_market_report = snapshots["cfpb_credit_card_market_report_2025"]
    assert cfpb_market_report.metadata.source_id == "cfpb"
    assert cfpb_market_report.metadata.snapshot_kind == "live_pdf_context"
    assert cfpb_market_report.metadata.units == "credit_card_apr_payment_report_context"
    assert len(cfpb_market_report.records) == 8
    market_report_note = cfpb_market_report.metadata.note or ""
    assert (
        "cfpb_credit_card_market_report_apr_payment_transmission_"
        "limitations_context_only"
    ) in market_report_note
    assert "source_pdf_sha256=" in market_report_note
    assert "source_record_count=8" in market_report_note
    assert "minimum_payment_behavior_context_available=true" in market_report_note
    assert "variable_index_rate_context_available=true" in market_report_note
    assert "issuer_margin_attribution_available=false" in market_report_note
    assert "rate_sensitive_payment_drag_transmission_available=false" in (
        market_report_note
    )
    assert any(
        record["metric"] == "prime_rate_increase_2022_2023"
        and record["metric_value"] == "5.1"
        and record["metric_unit"] == "percentage_points"
        for record in cfpb_market_report.records
    )
    assert {
        record["split_denominator_promotion_allowed"]
        for record in cfpb_market_report.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"] for record in cfpb_market_report.records
    } == {"false"}

    cfpb_interest_mechanics = snapshots[
        "cfpb_credit_card_interest_payment_mechanics_context"
    ]
    assert cfpb_interest_mechanics.metadata.source_id == "cfpb"
    assert (
        cfpb_interest_mechanics.metadata.snapshot_kind
        == "live_html_and_regulation_context"
    )
    assert (
        cfpb_interest_mechanics.metadata.units
        == "credit_card_interest_payment_mechanics_context"
    )
    assert cfpb_interest_mechanics.metadata.frequency == (
        "consumer_guidance_and_regulation"
    )
    assert cfpb_interest_mechanics.metadata.source_release_at == "2024-01-22"
    assert len(cfpb_interest_mechanics.records) == 6
    interest_mechanics_note = cfpb_interest_mechanics.metadata.note or ""
    assert "cfpb_credit_card_interest_payment_mechanics_context_only" in (
        interest_mechanics_note
    )
    assert "source_html_sha256=" in interest_mechanics_note
    assert "source_regulation_html_sha256=" in interest_mechanics_note
    assert "source_record_count=6" in interest_mechanics_note
    assert "rate_sensitive_payment_mechanics_context_available=true" in (
        interest_mechanics_note
    )
    assert "payment_allocation_mechanics_available=true" in interest_mechanics_note
    assert "monetary_rate_shock_payment_drag_transmission_available=false" in (
        interest_mechanics_note
    )
    assert "current_demand_response_available=false" in interest_mechanics_note
    assert "split_denominator_promotion_allowed=false" in interest_mechanics_note
    assert any(
        record["metric"] == "daily_interest_accrual_context"
        for record in cfpb_interest_mechanics.records
    )
    assert any(
        record["metric"] == "excess_payment_high_apr_allocation_context"
        for record in cfpb_interest_mechanics.records
    )
    assert {
        record["main_ratio_admission_allowed"]
        for record in cfpb_interest_mechanics.records
    } == {"false"}

    boston_card_spending = snapshots[
        "boston_fed_credit_card_interest_spending_response_context"
    ]
    assert boston_card_spending.metadata.source_id == "boston_fed"
    assert boston_card_spending.metadata.snapshot_kind == "live_html_article_context"
    assert boston_card_spending.metadata.units == (
        "credit_card_interest_rate_spending_response_context"
    )
    assert boston_card_spending.metadata.source_release_at == "2026-03-25"
    assert len(boston_card_spending.records) == 10
    boston_note = boston_card_spending.metadata.note or ""
    assert (
        "boston_fed_credit_card_interest_rate_spending_response_context_only"
        in boston_note
    )
    assert "source_html_sha256=" in boston_note
    assert "source_record_count=10" in boston_note
    assert "sample_start=2016-01-01" in boston_note
    assert "sample_end=2025-12-31" in boston_note
    assert "credit_card_spending_response_context_available=true" in boston_note
    assert "rate_sensitive_payment_drag_transmission_available=true" in boston_note
    assert (
        "monetary_rate_shock_payment_drag_transmission_available=false" in boston_note
    )
    assert "current_demand_conversion_available=false" in boston_note
    assert any(
        record["metric"] == "credit_card_spending_response_per_1pp_apr_increase"
        and record["metric_value"] == "-8.7"
        and record["metric_unit"] == "percent_next_month"
        for record in boston_card_spending.records
    )
    assert {
        record["split_denominator_promotion_allowed"]
        for record in boston_card_spending.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"]
        for record in boston_card_spending.records
    } == {"false"}

    boston_wp = snapshots["boston_fed_credit_card_spending_channel_wp_context"]
    assert boston_wp.metadata.source_id == "boston_fed"
    assert boston_wp.metadata.snapshot_kind == "live_pdf_research_context"
    assert boston_wp.metadata.units == (
        "credit_card_spending_channel_working_paper_context"
    )
    assert boston_wp.metadata.source_release_at == "2025-09-01"
    assert len(boston_wp.records) == 15
    boston_wp_note = boston_wp.metadata.note or ""
    assert (
        "boston_fed_credit_card_spending_channel_working_paper_context_only"
        in boston_wp_note
    )
    assert "source_pdf_sha256=" in boston_wp_note
    assert "source_record_count=15" in boston_wp_note
    assert "rkd_estimate_context_available=true" in boston_wp_note
    assert "local_projection_iv_context_available=true" in boston_wp_note
    assert (
        "promotion_grade_monetary_rate_shock_bridge_available=false" in boston_wp_note
    )
    assert "current_demand_conversion_available=false" in boston_wp_note
    assert any(
        record["metric"] == "aggregate_lp_iv_total_spending_growth_h2"
        and record["metric_value"] == "-0.0949"
        and record["metric_lower_ci"] == "-0.188"
        and record["metric_upper_ci"] == "0.044"
        for record in boston_wp.records
    )
    assert {
        record["split_denominator_promotion_allowed"] for record in boston_wp.records
    } == {"false"}
    assert {record["main_ratio_admission_allowed"] for record in boston_wp.records} == {
        "false"
    }

    fed_dsr = snapshots["fed_credit_bureau_household_dsr_accessible_data"]
    assert fed_dsr.metadata.source_id == "fed_feds_notes"
    assert fed_dsr.metadata.snapshot_kind == "live_accessible_html_table_context"
    assert fed_dsr.metadata.units == "percent_of_disposable_personal_income"
    assert fed_dsr.metadata.frequency == "quarterly"
    assert fed_dsr.metadata.source_release_at == "2024-09-04"
    assert len(fed_dsr.records) == 231
    fed_dsr_note = fed_dsr.metadata.note or ""
    assert "fed_credit_bureau_household_dsr_scheduled_payment_context_only" in (
        fed_dsr_note
    )
    assert "source_html_sha256=" in fed_dsr_note
    assert "source_record_count=231" in fed_dsr_note
    assert "first_observation_date=2005-03-31" in fed_dsr_note
    assert "latest_observation_date=2024-03-31" in fed_dsr_note
    assert "direct_required_payment_context_available=true" in fed_dsr_note
    assert "credit_card_minimum_payment_method_context_available=true" in (fed_dsr_note)
    assert "rate_sensitive_payment_drag_transmission_available=false" in (fed_dsr_note)
    assert any(
        record["component"] == "consumer_debt_dsr"
        and record["quarter"] == "2024Q1"
        and record["credit_bureau_methodology_dsr_pct_dpi"] == "5.55"
        for record in fed_dsr.records
    )
    assert {
        record["split_denominator_promotion_allowed"] for record in fed_dsr.records
    } == {"false"}
    assert {record["main_ratio_admission_allowed"] for record in fed_dsr.records} == {
        "false"
    }

    student_restart = snapshots["fed_student_loan_payment_restart_spending_context"]
    assert student_restart.metadata.source_id == "fed_feds_notes"
    assert student_restart.metadata.snapshot_kind == "live_html_and_accessible_context"
    assert (
        student_restart.metadata.units
        == "student_loan_payment_spending_response_context"
    )
    assert student_restart.metadata.frequency == "research_note"
    assert student_restart.metadata.source_release_at == "2025-09-05"
    assert len(student_restart.records) == 6
    student_restart_note = student_restart.metadata.note or ""
    assert "fed_student_loan_payment_restart_spending_context_only" in (
        student_restart_note
    )
    assert "source_html_sha256=" in student_restart_note
    assert "source_accessible_html_sha256=" in student_restart_note
    assert "source_record_count=6" in student_restart_note
    assert "current_demand_response_context_available=true" in student_restart_note
    assert "monetary_rate_shock_payment_drag_transmission_available=false" in (
        student_restart_note
    )
    assert "fast_repricing_credit_card_auto_context_available=false" in (
        student_restart_note
    )
    assert "split_denominator_promotion_allowed=false" in student_restart_note
    assert any(
        record["metric"] == "payment_resumption_spending_response_per_10000_debt"
        and record["metric_value"] == "-12.20"
        and record["confidence_interval_95"] == "-17_to_-7"
        for record in student_restart.records
    )
    assert {
        record["monetary_rate_shock_payment_drag_transmission_available"]
        for record in student_restart.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in student_restart.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"] for record in student_restart.records
    } == {"false"}

    credit_limit_debt = snapshots["fed_credit_card_limit_increase_debt_context"]
    assert credit_limit_debt.metadata.source_id == "fed_feds_notes"
    assert (
        credit_limit_debt.metadata.snapshot_kind == "live_html_and_accessible_context"
    )
    assert (
        credit_limit_debt.metadata.units
        == "credit_card_limit_increase_debt_response_context"
    )
    assert credit_limit_debt.metadata.frequency == "research_note"
    assert credit_limit_debt.metadata.source_release_at == "2026-01-16"
    assert len(credit_limit_debt.records) == 8
    credit_limit_debt_note = credit_limit_debt.metadata.note or ""
    assert "fed_credit_card_limit_increase_debt_context_only" in (
        credit_limit_debt_note
    )
    assert "source_html_sha256=" in credit_limit_debt_note
    assert "source_accessible_html_sha256=" in credit_limit_debt_note
    assert "source_record_count=8" in credit_limit_debt_note
    assert "fr_y14m_regulatory_data_context_available=true" in (credit_limit_debt_note)
    assert "credit_card_debt_response_context_available=true" in (
        credit_limit_debt_note
    )
    assert "underlying_account_microdata_publicly_reusable=false" in (
        credit_limit_debt_note
    )
    assert "monetary_rate_shock_payment_drag_transmission_available=false" in (
        credit_limit_debt_note
    )
    assert "rate_sensitive_payment_drag_transmission_available=false" in (
        credit_limit_debt_note
    )
    assert "current_demand_response_available=false" in credit_limit_debt_note
    assert "split_denominator_promotion_allowed=false" in credit_limit_debt_note
    assert any(
        record["metric"] == "six_month_debt_response_after_limit_increase_context"
        and record["metric_value"] == "30"
        for record in credit_limit_debt.records
    )
    assert {
        record["monetary_rate_shock_payment_drag_transmission_available"]
        for record in credit_limit_debt.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in credit_limit_debt.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"] for record in credit_limit_debt.records
    } == {"false"}

    profitability = snapshots["fed_credit_card_profitability_revolver_context"]
    assert profitability.metadata.source_id == "fed_feds_notes"
    assert profitability.metadata.snapshot_kind == "live_html_table_context"
    assert profitability.metadata.units == "credit_card_revolver_payment_burden_context"
    assert profitability.metadata.frequency == "research_note"
    assert profitability.metadata.source_release_at == "2022-09-09"
    assert len(profitability.records) == 68
    profitability_note = profitability.metadata.note or ""
    assert "fed_credit_card_profitability_revolver_context_only" in (profitability_note)
    assert "source_html_sha256=" in profitability_note
    assert "source_record_count=68" in profitability_note
    assert "revolver_transactor_payment_burden_context_available=true" in (
        profitability_note
    )
    assert "credit_card_payment_drag_magnitude_context_available=true" in (
        profitability_note
    )
    assert "underlying_account_microdata_publicly_reusable=false" in (
        profitability_note
    )
    assert "monetary_rate_shock_payment_drag_transmission_available=false" in (
        profitability_note
    )
    assert "rate_sensitive_payment_drag_transmission_available=false" in (
        profitability_note
    )
    assert "current_demand_response_available=false" in profitability_note
    assert "split_denominator_promotion_allowed=false" in profitability_note
    assert any(
        record["metric"]
        == "credit_card_profitability_interest_charge_heavy_revolver_mean"
        and record["metric_value"] == "60.5"
        for record in profitability.records
    )
    assert {
        record["monetary_rate_shock_payment_drag_transmission_available"]
        for record in profitability.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in profitability.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"] for record in profitability.records
    } == {"false"}

    delinquency_prediction = snapshots["fed_credit_card_delinquency_prediction_context"]
    assert delinquency_prediction.metadata.source_id == "fed_feds_notes"
    assert (
        delinquency_prediction.metadata.snapshot_kind
        == "live_html_and_accessible_table_context"
    )
    assert (
        delinquency_prediction.metadata.units
        == "credit_card_delinquency_prediction_model_context"
    )
    assert delinquency_prediction.metadata.frequency == "research_note"
    assert delinquency_prediction.metadata.source_release_at == "2025-02-28"
    assert len(delinquency_prediction.records) == 340
    delinquency_prediction_note = delinquency_prediction.metadata.note or ""
    assert "fed_credit_card_delinquency_prediction_context_only" in (
        delinquency_prediction_note
    )
    assert "source_html_sha256=" in delinquency_prediction_note
    assert "source_accessible_html_sha256=" in delinquency_prediction_note
    assert "source_record_count=340" in delinquency_prediction_note
    assert "rate_sensitive_model_context_available=true" in (
        delinquency_prediction_note
    )
    assert "prime_rate_context_available=true" in delinquency_prediction_note
    assert "sloos_tightening_context_available=true" in delinquency_prediction_note
    assert (
        "monetary_rate_shock_payment_drag_transmission_available=false"
        in delinquency_prediction_note
    )
    assert "current_demand_response_available=false" in (delinquency_prediction_note)
    assert "split_denominator_promotion_allowed=false" in (delinquency_prediction_note)
    assert any(
        record["metric"] == "preferred_model_adjusted_r_squared_context"
        and record["metric_value"] == "0.97"
        for record in delinquency_prediction.records
    )
    assert {
        record["monetary_rate_shock_payment_drag_transmission_available"]
        for record in delinquency_prediction.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in delinquency_prediction.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"]
        for record in delinquency_prediction.records
    } == {"false"}

    delinquency_dynamics = snapshots["fed_consumer_delinquency_dynamics_context"]
    assert delinquency_dynamics.metadata.source_id == "fed_feds_notes"
    assert (
        delinquency_dynamics.metadata.snapshot_kind
        == "live_html_and_accessible_table_context"
    )
    assert (
        delinquency_dynamics.metadata.units
        == "credit_card_auto_delinquency_distribution_context"
    )
    assert delinquency_dynamics.metadata.frequency == "research_note"
    assert delinquency_dynamics.metadata.source_release_at == "2025-11-24"
    assert len(delinquency_dynamics.records) == 921
    delinquency_dynamics_note = delinquency_dynamics.metadata.note or ""
    assert "fed_consumer_delinquency_dynamics_context_only" in (
        delinquency_dynamics_note
    )
    assert "source_html_sha256=" in delinquency_dynamics_note
    assert "source_accessible_html_sha256=" in delinquency_dynamics_note
    assert "source_record_count=921" in delinquency_dynamics_note
    assert "ccp_equifax_context_available=true" in delinquency_dynamics_note
    assert "credit_score_distribution_context_available=true" in (
        delinquency_dynamics_note
    )
    assert "income_tract_context_available=true" in delinquency_dynamics_note
    assert "mortgage_status_context_available=true" in delinquency_dynamics_note
    assert (
        "monetary_rate_shock_payment_drag_transmission_available=false"
        in delinquency_dynamics_note
    )
    assert "current_demand_response_available=false" in delinquency_dynamics_note
    assert "split_denominator_promotion_allowed=false" in delinquency_dynamics_note
    assert any(
        record["source_table_title"] == "credit_card_delinquency_by_credit_score"
        and record["source_row_label"] == "3/31/2000"
        for record in delinquency_dynamics.records
    )
    assert {
        record["monetary_rate_shock_payment_drag_transmission_available"]
        for record in delinquency_dynamics.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in delinquency_dynamics.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"]
        for record in delinquency_dynamics.records
    } == {"false"}

    credit_rewards = snapshots["fed_credit_card_rewards_limit_spending_context"]
    assert credit_rewards.metadata.source_id == "fed_feds"
    assert credit_rewards.metadata.snapshot_kind == "live_accessible_zip_context"
    assert (
        credit_rewards.metadata.units
        == "credit_card_limit_increase_spending_payment_balance_context"
    )
    assert credit_rewards.metadata.frequency == "research_paper"
    assert credit_rewards.metadata.source_release_at == "2023-01-20"
    assert len(credit_rewards.records) == 21
    credit_rewards_note = credit_rewards.metadata.note or ""
    assert "fed_credit_card_rewards_limit_spending_context_only" in (
        credit_rewards_note
    )
    assert "source_zip_sha256=" in credit_rewards_note
    assert "index_html_sha256=" in credit_rewards_note
    assert "accessible_figures_html_sha256=" in credit_rewards_note
    assert "source_record_count=21" in credit_rewards_note
    assert "credit_card_spending_response_context_available=true" in (
        credit_rewards_note
    )
    assert "current_demand_response_context_available=true" in credit_rewards_note
    assert "monetary_rate_shock_payment_drag_transmission_available=false" in (
        credit_rewards_note
    )
    assert "rate_sensitive_payment_drag_transmission_available=false" in (
        credit_rewards_note
    )
    assert "current_demand_conversion_available=false" in credit_rewards_note
    assert "underlying_y14m_account_microdata_publicly_reusable=false" in (
        credit_rewards_note
    )
    assert any(
        record["source_row_label"] == "Reward Card"
        and record["source_column_label"] == "Delta Spending(1)"
        and record["metric_value"] == "75.77"
        for record in credit_rewards.records
    )
    assert {
        record["monetary_rate_shock_payment_drag_transmission_available"]
        for record in credit_rewards.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in credit_rewards.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"] for record in credit_rewards.records
    } == {"false"}

    auto_payment_delinquency = snapshots["fed_auto_loan_payment_delinquency_context"]
    assert auto_payment_delinquency.metadata.source_id == "fed_feds_notes"
    assert (
        auto_payment_delinquency.metadata.snapshot_kind
        == "live_html_and_accessible_context"
    )
    assert (
        auto_payment_delinquency.metadata.units
        == "auto_loan_payment_delinquency_context"
    )
    assert auto_payment_delinquency.metadata.frequency == "research_note"
    assert auto_payment_delinquency.metadata.source_release_at == "2024-09-26"
    assert len(auto_payment_delinquency.records) == 10
    auto_payment_delinquency_note = auto_payment_delinquency.metadata.note or ""
    assert "fed_auto_loan_payment_delinquency_context_only" in (
        auto_payment_delinquency_note
    )
    assert "source_html_sha256=" in auto_payment_delinquency_note
    assert "source_accessible_html_sha256=" in auto_payment_delinquency_note
    assert "source_record_count=10" in auto_payment_delinquency_note
    assert "auto_loan_payment_context_available=true" in (auto_payment_delinquency_note)
    assert "auto_loan_delinquency_context_available=true" in (
        auto_payment_delinquency_note
    )
    assert "monetary_rate_shock_payment_drag_transmission_available=false" in (
        auto_payment_delinquency_note
    )
    assert "current_demand_response_available=false" in (auto_payment_delinquency_note)
    assert any(
        record["metric"] == "average_required_monthly_payment_increase_context"
        and record["metric_value"] == "470_to_600"
        for record in auto_payment_delinquency.records
    )
    assert {
        record["rate_sensitive_payment_drag_transmission_available"]
        for record in auto_payment_delinquency.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in auto_payment_delinquency.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"]
        for record in auto_payment_delinquency.records
    } == {"false"}

    auto_prepayment_maturity = snapshots["fed_auto_loan_prepayment_maturity_context"]
    assert auto_prepayment_maturity.metadata.source_id == "fed_feds"
    assert (
        auto_prepayment_maturity.metadata.snapshot_kind == "live_accessible_zip_context"
    )
    assert (
        auto_prepayment_maturity.metadata.units
        == "auto_loan_maturity_prepayment_payment_behavior_context"
    )
    assert auto_prepayment_maturity.metadata.frequency == "research_paper"
    assert auto_prepayment_maturity.metadata.source_release_at == "2025-01-31"
    assert len(auto_prepayment_maturity.records) == 145
    auto_prepayment_maturity_note = auto_prepayment_maturity.metadata.note or ""
    assert "fed_auto_loan_prepayment_maturity_context_only" in (
        auto_prepayment_maturity_note
    )
    assert "source_zip_sha256=" in auto_prepayment_maturity_note
    assert "index_html_sha256=" in auto_prepayment_maturity_note
    assert "accessible_figures_html_sha256=" in auto_prepayment_maturity_note
    assert "source_record_count=145" in auto_prepayment_maturity_note
    assert "auto_loan_maturity_context_available=true" in (
        auto_prepayment_maturity_note
    )
    assert "auto_loan_prepayment_context_available=true" in (
        auto_prepayment_maturity_note
    )
    assert "auto_loan_payment_behavior_context_available=true" in (
        auto_prepayment_maturity_note
    )
    assert "monetary_rate_shock_payment_drag_transmission_available=false" in (
        auto_prepayment_maturity_note
    )
    assert "current_demand_response_available=false" in (auto_prepayment_maturity_note)
    assert any(
        record["metric"] == "auto_loan_actual_paid_over_scheduled_payment"
        for record in auto_prepayment_maturity.records
    )
    assert {
        record["rate_sensitive_payment_drag_transmission_available"]
        for record in auto_prepayment_maturity.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in auto_prepayment_maturity.records
    } == {"false"}
    assert {
        record["main_ratio_admission_allowed"]
        for record in auto_prepayment_maturity.records
    } == {"false"}

    registry_rows = {
        row["channel_name"]: row
        for row in csv.DictReader(
            Path("outputs/tables/ratewall_higher_rate_channel_registry.csv").open(
                encoding="utf-8"
            )
        )
    }
    assert (
        "admitted_source_ids=TOTALSL;REVOLSL;NONREVSL;TERMCBCCALLNS;CDSP;"
        "DRCCLACBS;DRCLACBS;nyfed_consumer_credit_panel_faq;"
        "nyfed_household_debt_credit_report_2026q1;"
        "sloos_consumer_lending;"
        "cfpb_credit_card_market_figure_data_2025;"
        "cfpb_credit_card_market_report_2025;"
        "cfpb_credit_card_interest_payment_mechanics_context;"
        "cfpb_consumer_credit_trends_all_data;"
        "cfpb_consumer_credit_trends_codebook;"
        "cfpb_terms_credit_card_plans_2025h1;"
        "cfpb_payment_amount_furnishing_report;"
        "cfpb_credit_card_revolvers_data_point;"
        "fed_credit_bureau_household_dsr_accessible_data;"
        "fed_student_loan_payment_restart_spending_context;"
        "fed_credit_card_limit_increase_debt_context;"
        "fed_credit_card_profitability_revolver_context;"
        "fed_credit_card_delinquency_prediction_context;"
        "fed_consumer_delinquency_dynamics_context;"
        "fed_credit_card_rewards_limit_spending_context;"
        "fed_auto_loan_payment_delinquency_context;"
        "fed_auto_loan_prepayment_maturity_context;"
        "boston_fed_credit_card_interest_spending_response_context;"
        "boston_fed_credit_card_spending_channel_wp_context;"
        "cfpb_making_ends_meet_sample1_public_use;"
        "cfpb_making_ends_meet_samples_3_6_public_use;"
        "philadelphia_fed_y14_large_bank_credit_card_context;"
        "fed_dfa_household_liability_context;"
        "fed_scf_2022_summary_extract_context;"
        "fed_scf_2022_weighted_consumer_credit_summary_context;"
        "fed_scf_2022_replicate_weight_methodology_context;"
        "fed_scf_2022_consumer_credit_uncertainty_context;"
        "fed_shed_2025_financial_fragility_credit_payment_context"
    ) in (registry_rows["fast_repricing_consumer_credit_drag"]["source_status"])
    assert (
        "nyfed_consumer_credit_panel_faq"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "nyfed_household_debt_credit_report_2026q1"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_dfa_household_liability_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_scf_2022_summary_extract_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_scf_2022_weighted_consumer_credit_summary_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_scf_2022_replicate_weight_methodology_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_scf_2022_consumer_credit_uncertainty_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_shed_2025_financial_fragility_credit_payment_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "cfpb_terms_credit_card_plans_2025h1"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "cfpb_payment_amount_furnishing_report"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "cfpb_credit_card_revolvers_data_point"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "cfpb_credit_card_interest_payment_mechanics_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_credit_card_limit_increase_debt_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_credit_card_rewards_limit_spending_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_auto_loan_payment_delinquency_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_auto_loan_prepayment_maturity_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "boston_fed_credit_card_interest_spending_response_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "boston_fed_credit_card_spending_channel_wp_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "cfpb_making_ends_meet_sample1_public_use"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "cfpb_making_ends_meet_samples_3_6_public_use"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "philadelphia_fed_y14_large_bank_credit_card_context"
        in (
            registry_rows["fast_repricing_consumer_credit_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "admitted_source_ids=CREACBM027NBOG;DRCRELEXFACBS;CORCREXFACBS;"
        "sloos_cre;mba_cre_maturity_ladder_context"
    ) in (registry_rows["cre_refinancing_bank_exposure_drag"]["source_status"])
    assert (
        "DRCRELEXFACBS"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "mba_cre_maturity_ladder_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_cre_high_growth_deposit_accessible_data"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "atlanta_fed_cremi_longweights_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_cre_evergreening_extension_terms_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_abs_ee_cmbs_asset_level_performance_panel"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_abs_ee_cmbs_asset_time_dimension_panel"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_abs_ee_recent_filing_index_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_abs_ee_candidate_cmbs_xml_verification_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_abs_ee_cmbs_representativeness_design_review_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "BOGZ1FL673065505Q"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_z1_cmbs_abs_commercial_mortgage_population_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "ASCMA"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fed_z1_total_commercial_mortgage_population_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_abs_ee_cmbs_reviewed_balance_coverage_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "TLNRESCONS"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "fred_nonres_construction_real_activity_bridge_context"
        in (
            registry_rows["cre_refinancing_bank_exposure_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "public_refinancing_outcome_real_activity_gate_blocked"
        in (registry_rows["cre_refinancing_bank_exposure_drag"]["source_status"])
    )
    cre_high_growth_context = snapshots["fed_cre_high_growth_deposit_accessible_data"]
    assert cre_high_growth_context.metadata.source_id == "fed_feds_notes"
    assert (
        cre_high_growth_context.metadata.snapshot_kind == "live_accessible_text_context"
    )
    assert cre_high_growth_context.metadata.units == "mixed_accessible_text_units"
    assert len(cre_high_growth_context.records) == 9
    cre_high_growth_note = cre_high_growth_context.metadata.note or ""
    assert "fed_cre_high_growth_deposit_accessible_context_only" in (
        cre_high_growth_note
    )
    assert "source_record_count=9" in cre_high_growth_note
    assert "local_deposit_funding_context_available=true" in cre_high_growth_note
    assert "cre_refinancing_outcome_available=false" in cre_high_growth_note
    assert "split_denominator_promotion_allowed=false" in cre_high_growth_note
    assert (
        cre_high_growth_context.records[0]["cre_public_records_context_available"]
        == "true"
    )
    assert (
        cre_high_growth_context.records[0]["split_denominator_promotion_allowed"]
        == "false"
    )
    cremi_context = snapshots["atlanta_fed_cremi_longweights_context"]
    assert cremi_context.metadata.source_id == "atlanta_fed"
    assert cremi_context.metadata.snapshot_kind == "live_csv_and_html_context"
    assert cremi_context.metadata.units == "cremi_variable_weight_percent_context"
    assert len(cremi_context.records) > 1000
    cremi_note = cremi_context.metadata.note or ""
    assert "atlanta_fed_cremi_longweights_context_only" in cremi_note
    assert "noi_cap_rate_asset_value_input_roles_available=true" in cremi_note
    assert "raw_noi_cap_rate_asset_value_source_publicly_shareable=false" in (
        cremi_note
    )
    assert "split_denominator_promotion_allowed=false" in cremi_note
    assert {
        "NOI.Index",
        "Market.Cap.Rate",
        "Asset.Value",
    }.issubset({record["cremi_input_variable"] for record in cremi_context.records})
    assert {
        record["split_denominator_promotion_allowed"]
        for record in cremi_context.records
    } == {"false"}
    cre_evergreening_context = snapshots["fed_cre_evergreening_extension_terms_context"]
    assert cre_evergreening_context.metadata.source_id == "fed_feds"
    assert (
        cre_evergreening_context.metadata.snapshot_kind
        == "live_html_pdf_research_context"
    )
    assert (
        cre_evergreening_context.metadata.units
        == "cre_extension_terms_research_context"
    )
    assert len(cre_evergreening_context.records) == 6
    cre_evergreening_note = cre_evergreening_context.metadata.note or ""
    assert "fed_cre_evergreening_extension_terms_context_only" in (
        cre_evergreening_note
    )
    assert "source_record_count=6" in cre_evergreening_note
    assert "cre_extension_terms_context_available=true" in cre_evergreening_note
    assert "cre_noi_debt_yield_context_available=true" in cre_evergreening_note
    assert "underlying_supervisory_data_publicly_reusable=false" in (
        cre_evergreening_note
    )
    assert "cre_dscr_context_available=false" in cre_evergreening_note
    assert "split_denominator_promotion_allowed=false" in cre_evergreening_note
    assert any(
        record["cre_noi_debt_yield_context_available"] == "true"
        for record in cre_evergreening_context.records
    )
    assert {
        record["split_denominator_promotion_allowed"]
        for record in cre_evergreening_context.records
    } == {"false"}
    abs_ee_context = snapshots["sec_abs_ee_cmbs_asset_level_performance_panel"]
    assert abs_ee_context.metadata.source_id == "sec_edgar"
    assert (
        abs_ee_context.metadata.snapshot_kind
        == "live_sec_abs_ee_cmbs_asset_level_performance_panel"
    )
    assert abs_ee_context.metadata.units == "source_abs_ee_asset_data_units"
    assert len(abs_ee_context.records) >= 300
    abs_ee_note = abs_ee_context.metadata.note or ""
    assert "sec_abs_ee_cmbs_asset_level_performance_panel" in abs_ee_note
    assert "reviewed_filing_count=6" in abs_ee_note
    assert "public_reusable_asset_level_cre_panel_available=true" in abs_ee_note
    assert "cre_dscr_context_available=true" in abs_ee_note
    assert "cre_refinancing_outcome_available=false" in abs_ee_note
    assert "cre_real_activity_mapping_available=false" in abs_ee_note
    assert {
        record["split_denominator_promotion_allowed"]
        for record in abs_ee_context.records
    } == {"false"}
    assert {
        record["cre_refinancing_outcome_available"] for record in abs_ee_context.records
    } == {"false"}
    abs_ee_time_context = snapshots["sec_abs_ee_cmbs_asset_time_dimension_panel"]
    assert abs_ee_time_context.metadata.source_id == "sec_edgar"
    assert (
        abs_ee_time_context.metadata.snapshot_kind
        == "live_sec_abs_ee_cmbs_asset_time_dimension_panel"
    )
    assert abs_ee_time_context.metadata.units == "source_abs_ee_asset_data_units"
    assert len(abs_ee_time_context.records) >= len(abs_ee_context.records)
    abs_ee_time_note = abs_ee_time_context.metadata.note or ""
    assert "sec_abs_ee_cmbs_asset_time_dimension_panel" in abs_ee_time_note
    assert "reviewed_trust_count=6" in abs_ee_time_note
    assert "public_asset_time_dimension_context_available=true" in abs_ee_time_note
    assert "public_representativeness_design_available=false" in abs_ee_time_note
    assert "cre_refinancing_outcome_available=false" in abs_ee_time_note
    assert "cre_real_activity_mapping_available=false" in abs_ee_time_note
    assert {
        record["public_asset_time_dimension_context_available"]
        for record in abs_ee_time_context.records
    } == {"true"}
    assert {
        record["public_representativeness_design_available"]
        for record in abs_ee_time_context.records
    } == {"false"}
    assert {
        record["cre_refinancing_outcome_available"]
        for record in abs_ee_time_context.records
    } == {"false"}
    assert {
        record["cre_real_activity_mapping_available"]
        for record in abs_ee_time_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in abs_ee_time_context.records
    } == {"false"}
    abs_ee_index_context = snapshots["sec_abs_ee_recent_filing_index_context"]
    assert abs_ee_index_context.metadata.source_id == "sec_edgar"
    assert (
        abs_ee_index_context.metadata.snapshot_kind
        == "live_sec_abs_ee_recent_filing_index_context"
    )
    assert abs_ee_index_context.metadata.units == "sec_master_index_filing_rows"
    assert len(abs_ee_index_context.records) > len(abs_ee_time_context.records)
    abs_ee_index_note = abs_ee_index_context.metadata.note or ""
    assert "sec_abs_ee_recent_filing_index_context" in abs_ee_index_note
    assert "public_abs_ee_filing_index_frame_available=true" in abs_ee_index_note
    assert "candidate_cmbs_name_match_available=true" in abs_ee_index_note
    assert "cre_market_representativeness_design_available=false" in (abs_ee_index_note)
    assert "cre_refinancing_outcome_available=false" in abs_ee_index_note
    assert "cre_real_activity_mapping_available=false" in abs_ee_index_note
    assert {
        record["public_abs_ee_filing_index_frame_available"]
        for record in abs_ee_index_context.records
    } == {"true"}
    assert {
        record["cre_market_representativeness_design_available"]
        for record in abs_ee_index_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in abs_ee_index_context.records
    } == {"false"}
    abs_ee_xml_context = snapshots["sec_abs_ee_candidate_cmbs_xml_verification_context"]
    assert abs_ee_xml_context.metadata.source_id == "sec_edgar"
    assert (
        abs_ee_xml_context.metadata.snapshot_kind
        == "live_sec_abs_ee_candidate_cmbs_xml_verification_context"
    )
    assert abs_ee_xml_context.metadata.units == "sec_abs_ee_xml_verification_rows"
    assert len(abs_ee_xml_context.records) >= 2
    abs_ee_xml_note = abs_ee_xml_context.metadata.note or ""
    assert "sec_abs_ee_candidate_cmbs_xml_verification_context" in abs_ee_xml_note
    assert "public_xml_verification_context_available=true" in abs_ee_xml_note
    assert "public_bounded_xml_verification_sample_available=true" in abs_ee_xml_note
    assert "cre_market_representativeness_design_available=false" in abs_ee_xml_note
    assert "cre_refinancing_outcome_available=false" in abs_ee_xml_note
    assert "cre_real_activity_mapping_available=false" in abs_ee_xml_note
    assert {
        record["public_abs_ee_filing_index_frame_available"]
        for record in abs_ee_xml_context.records
    } == {"true"}
    assert {
        record["public_bounded_xml_verification_sample_available"]
        for record in abs_ee_xml_context.records
    } == {"true"}
    assert "true" in {
        record["public_xml_verification_context_available"]
        for record in abs_ee_xml_context.records
    }
    assert {
        record["cre_market_representativeness_design_available"]
        for record in abs_ee_xml_context.records
    } == {"false"}
    assert {
        record["cre_refinancing_outcome_available"]
        for record in abs_ee_xml_context.records
    } == {"false"}
    assert {
        record["cre_real_activity_mapping_available"]
        for record in abs_ee_xml_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in abs_ee_xml_context.records
    } == {"false"}
    abs_ee_repr_context = snapshots[
        "sec_abs_ee_cmbs_representativeness_design_review_context"
    ]
    assert abs_ee_repr_context.metadata.source_id == "sec_edgar"
    assert (
        abs_ee_repr_context.metadata.snapshot_kind
        == "derived_sec_abs_ee_cmbs_representativeness_design_review_context"
    )
    assert (
        abs_ee_repr_context.metadata.units
        == "sec_abs_ee_representativeness_design_review_rows"
    )
    assert len(abs_ee_repr_context.records) == 2
    abs_ee_repr_note = abs_ee_repr_context.metadata.note or ""
    assert "sec_abs_ee_cmbs_representativeness_design_review_context" in (
        abs_ee_repr_note
    )
    assert "public_abs_ee_filing_frame_available=true" in abs_ee_repr_note
    assert "asset_class_xml_verification_sample_available=true" in (abs_ee_repr_note)
    assert "public_cre_market_population_denominator_available=false" in (
        abs_ee_repr_note
    )
    assert "representative_sampling_weights_available=false" in abs_ee_repr_note
    assert {
        record["public_representativeness_frame_for_abs_ee_index_available"]
        for record in abs_ee_repr_context.records
    } == {"true"}
    assert {
        record["public_cre_market_population_denominator_available"]
        for record in abs_ee_repr_context.records
    } == {"false"}
    assert {
        record["representative_sampling_weights_available"]
        for record in abs_ee_repr_context.records
    } == {"false"}
    assert {
        record["cre_market_representativeness_design_available"]
        for record in abs_ee_repr_context.records
    } == {"false"}
    assert {
        record["cre_refinancing_outcome_available"]
        for record in abs_ee_repr_context.records
    } == {"false"}
    assert {
        record["cre_real_activity_mapping_available"]
        for record in abs_ee_repr_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in abs_ee_repr_context.records
    } == {"false"}
    z1_cmbs_abs_context = snapshots[
        "fed_z1_cmbs_abs_commercial_mortgage_population_context"
    ]
    assert z1_cmbs_abs_context.metadata.source_id == "fred"
    assert (
        z1_cmbs_abs_context.metadata.snapshot_kind
        == "derived_fred_z1_cmbs_abs_population_denominator_context"
    )
    assert z1_cmbs_abs_context.metadata.units == "denominator_review_rows"
    assert len(z1_cmbs_abs_context.records) == 2
    z1_cmbs_abs_note = z1_cmbs_abs_context.metadata.note or ""
    assert "fed_z1_cmbs_abs_commercial_mortgage_population_context" in (
        z1_cmbs_abs_note
    )
    assert "source_records_sha256=" in z1_cmbs_abs_note
    assert "public_cmbs_abs_segment_population_denominator_available=true" in (
        z1_cmbs_abs_note
    )
    assert "population_denominator_is_full_cre_market=false" in (z1_cmbs_abs_note)
    assert "representative_sampling_weights_available=false" in z1_cmbs_abs_note
    assert {
        record["public_cmbs_abs_segment_population_denominator_available"]
        for record in z1_cmbs_abs_context.records
    } == {"true"}
    assert {
        record["population_denominator_is_full_cre_market"]
        for record in z1_cmbs_abs_context.records
    } == {"false"}
    assert {
        record["filing_count_to_balance_weight_available"]
        for record in z1_cmbs_abs_context.records
    } == {"false"}
    assert {
        record["cre_refinancing_outcome_available"]
        for record in z1_cmbs_abs_context.records
    } == {"false"}
    assert {
        record["cre_real_activity_mapping_available"]
        for record in z1_cmbs_abs_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in z1_cmbs_abs_context.records
    } == {"false"}
    z1_total_cre_context = snapshots[
        "fed_z1_total_commercial_mortgage_population_context"
    ]
    assert z1_total_cre_context.metadata.source_id == "fred"
    assert (
        z1_total_cre_context.metadata.snapshot_kind
        == "derived_fred_z1_total_cre_population_denominator_context"
    )
    assert z1_total_cre_context.metadata.units == "denominator_review_rows"
    assert len(z1_total_cre_context.records) == 2
    z1_total_cre_note = z1_total_cre_context.metadata.note or ""
    assert "fed_z1_total_commercial_mortgage_population_context" in (z1_total_cre_note)
    assert "source_records_sha256=" in z1_total_cre_note
    assert "public_total_commercial_mortgage_population_denominator_available=true" in (
        z1_total_cre_note
    )
    assert "population_denominator_is_full_cre_market=true" in z1_total_cre_note
    assert "representative_sampling_weights_available=false" in z1_total_cre_note
    assert {
        record["public_total_commercial_mortgage_population_denominator_available"]
        for record in z1_total_cre_context.records
    } == {"true"}
    assert {
        record["public_cre_market_population_denominator_available"]
        for record in z1_total_cre_context.records
    } == {"true"}
    assert {
        record["population_denominator_is_full_cre_market"]
        for record in z1_total_cre_context.records
    } == {"true"}
    assert {
        record["filing_count_to_balance_weight_available"]
        for record in z1_total_cre_context.records
    } == {"false"}
    assert {
        record["representative_sampling_weights_available"]
        for record in z1_total_cre_context.records
    } == {"false"}
    assert {
        record["cre_refinancing_outcome_available"]
        for record in z1_total_cre_context.records
    } == {"false"}
    assert {
        record["cre_real_activity_mapping_available"]
        for record in z1_total_cre_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in z1_total_cre_context.records
    } == {"false"}
    abs_ee_balance_context = snapshots[
        "sec_abs_ee_cmbs_reviewed_balance_coverage_context"
    ]
    assert abs_ee_balance_context.metadata.source_id == "sec_edgar"
    assert (
        abs_ee_balance_context.metadata.snapshot_kind
        == "derived_sec_abs_ee_cmbs_reviewed_balance_coverage_context"
    )
    assert (
        abs_ee_balance_context.metadata.units == "reviewed_balance_coverage_review_rows"
    )
    assert len(abs_ee_balance_context.records) == 2
    abs_ee_balance_note = abs_ee_balance_context.metadata.note or ""
    assert "sec_abs_ee_cmbs_reviewed_balance_coverage_context" in (abs_ee_balance_note)
    assert "source_records_sha256=" in abs_ee_balance_note
    assert "public_reviewed_cmbs_balance_coverage_available=true" in (
        abs_ee_balance_note
    )
    assert "filing_count_to_balance_weight_context_available=true" in (
        abs_ee_balance_note
    )
    assert "filing_count_to_balance_weight_available=false" in (abs_ee_balance_note)
    assert {
        record["public_reviewed_cmbs_balance_coverage_available"]
        for record in abs_ee_balance_context.records
    } == {"true"}
    assert {
        record["filing_count_to_balance_weight_context_available"]
        for record in abs_ee_balance_context.records
    } == {"true"}
    assert {
        record["filing_count_to_balance_weight_available"]
        for record in abs_ee_balance_context.records
    } == {"false"}
    assert {
        record["representative_sampling_weights_available"]
        for record in abs_ee_balance_context.records
    } == {"false"}
    assert {
        record["cre_refinancing_outcome_available"]
        for record in abs_ee_balance_context.records
    } == {"false"}
    assert {
        record["cre_real_activity_mapping_available"]
        for record in abs_ee_balance_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in abs_ee_balance_context.records
    } == {"false"}
    abs_ee_maturity_status_context = snapshots[
        "sec_abs_ee_cmbs_maturity_status_outcome_review_context"
    ]
    assert abs_ee_maturity_status_context.metadata.source_id == "sec_edgar"
    assert (
        abs_ee_maturity_status_context.metadata.snapshot_kind
        == "derived_sec_abs_ee_cmbs_maturity_status_outcome_review_context"
    )
    assert (
        abs_ee_maturity_status_context.metadata.units
        == "maturity_status_outcome_review_rows"
    )
    assert len(abs_ee_maturity_status_context.records) == 10
    abs_ee_maturity_status_note = abs_ee_maturity_status_context.metadata.note or ""
    assert "sec_abs_ee_cmbs_maturity_status_outcome_review_context" in (
        abs_ee_maturity_status_note
    )
    assert "source_records_sha256=" in abs_ee_maturity_status_note
    assert "public_maturity_window_status_context_available=true" in (
        abs_ee_maturity_status_note
    )
    assert "explicit_refinancing_outcome_field_available=false" in (
        abs_ee_maturity_status_note
    )
    assert "cre_refinancing_outcome_available=false" in (abs_ee_maturity_status_note)
    assert {
        record["public_maturity_window_status_context_available"]
        for record in abs_ee_maturity_status_context.records
    } == {"true"}
    assert {
        record["public_paid_through_payment_status_context_available"]
        for record in abs_ee_maturity_status_context.records
    } == {"true"}
    assert {
        record["explicit_refinancing_outcome_field_available"]
        for record in abs_ee_maturity_status_context.records
    } == {"false"}
    assert {
        record["representative_sampling_weights_available"]
        for record in abs_ee_maturity_status_context.records
    } == {"false"}
    assert {
        record["cre_refinancing_outcome_available"]
        for record in abs_ee_maturity_status_context.records
    } == {"false"}
    assert {
        record["cre_real_activity_mapping_available"]
        for record in abs_ee_maturity_status_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in abs_ee_maturity_status_context.records
    } == {"false"}
    nonres_bridge_context = snapshots[
        "fred_nonres_construction_real_activity_bridge_context"
    ]
    assert nonres_bridge_context.metadata.source_id == "fred"
    assert (
        nonres_bridge_context.metadata.snapshot_kind
        == "derived_fred_nonres_construction_real_activity_bridge_context"
    )
    assert nonres_bridge_context.metadata.units == "real_activity_bridge_review_rows"
    assert len(nonres_bridge_context.records) == 2
    nonres_bridge_note = nonres_bridge_context.metadata.note or ""
    assert "fred_nonres_construction_real_activity_bridge_context" in (
        nonres_bridge_note
    )
    assert "source_records_sha256=" in nonres_bridge_note
    assert (
        "public_nonresidential_construction_real_activity_series_available=true"
        in nonres_bridge_note
    )
    assert "flow_stock_ratio_is_not_elasticity=true" in nonres_bridge_note
    assert "cre_real_activity_mapping_available=false" in nonres_bridge_note
    assert {
        record["public_nonresidential_construction_real_activity_series_available"]
        for record in nonres_bridge_context.records
    } == {"true"}
    assert {
        record["public_real_activity_bridge_review_available"]
        for record in nonres_bridge_context.records
    } == {"true"}
    assert {
        record["flow_stock_ratio_is_not_elasticity"]
        for record in nonres_bridge_context.records
    } == {"true"}
    assert {
        record["cre_refinancing_outcome_available"]
        for record in nonres_bridge_context.records
    } == {"false"}
    assert {
        record["cre_real_activity_mapping_available"]
        for record in nonres_bridge_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in nonres_bridge_context.records
    } == {"false"}
    property_bridge_context = snapshots[
        "fred_cre_property_type_construction_bridge_context"
    ]
    assert property_bridge_context.metadata.source_id == "fred"
    assert (
        property_bridge_context.metadata.snapshot_kind
        == "derived_fred_cre_property_type_construction_bridge_context"
    )
    assert (
        property_bridge_context.metadata.units
        == "property_type_real_activity_bridge_review_rows"
    )
    assert len(property_bridge_context.records) == 18
    property_bridge_note = property_bridge_context.metadata.note or ""
    assert "fred_cre_property_type_construction_bridge_context" in (
        property_bridge_note
    )
    assert "source_records_sha256=" in property_bridge_note
    assert "public_property_type_construction_series_available=true" in (
        property_bridge_note
    )
    assert "property_type_mapping_is_construction_spending_not_debt_exposure=true" in (
        property_bridge_note
    )
    assert "cre_debt_repricing_to_real_activity_mapping_available=false" in (
        property_bridge_note
    )
    assert {
        record["public_property_type_construction_series_available"]
        for record in property_bridge_context.records
    } == {"true"}
    assert {
        record["property_type_mapping_is_construction_spending_not_debt_exposure"]
        for record in property_bridge_context.records
    } == {"true"}
    assert {
        record["filing_count_to_balance_weight_available"]
        for record in property_bridge_context.records
    } == {"false"}
    assert {
        record["representative_sampling_weights_available"]
        for record in property_bridge_context.records
    } == {"false"}
    assert {
        record["cre_debt_repricing_to_real_activity_mapping_available"]
        for record in property_bridge_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in property_bridge_context.records
    } == {"false"}
    assert (
        "admitted_source_ids=sloos_ndfi_special_questions;fed_private_credit_notes;"
        "fed_private_credit_characteristics_accessible_data;"
        "fed_bank_lending_private_credit_financial_stability_context;"
        "fed_indirect_credit_supply_private_credit;"
        "fed_indirect_credit_supply_accessible_materials;"
        "ofr_private_credit_counterparty_exposure_context;"
        "sec_private_fund_statistics_aggregate_assets;"
        "sec_bdc_public_filing_availability_context;"
        "sec_bdc_portfolio_investment_terms_panel;"
        "sec_bdc_portfolio_performance_status_panel;"
        "sec_bdc_portfolio_terms_status_join_panel;"
        "sec_bdc_portfolio_terms_status_time_panel;"
        "sec_bdc_floating_rate_pass_through_design_context;"
        "sec_bdc_borrower_name_continuity_context;"
        "sec_bdc_investment_signature_continuity_context;"
        "sec_bdc_recurring_investment_value_status_context"
    ) in (registry_rows["private_credit_ndfi_funding_drag"]["source_status"])
    assert (
        "promotion_grade_pass_through_real_activity_bridge_blocked"
        in (registry_rows["private_credit_ndfi_funding_drag"]["source_status"])
    )
    assert (
        "sec_private_fund_statistics_aggregate_assets"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_bdc_public_filing_availability_context"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_bdc_portfolio_investment_terms_panel"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_bdc_portfolio_performance_status_panel"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_bdc_portfolio_terms_status_join_panel"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_bdc_portfolio_terms_status_time_panel"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_bdc_floating_rate_pass_through_design_context"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_bdc_borrower_name_continuity_context"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_bdc_investment_signature_continuity_context"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    assert (
        "sec_bdc_recurring_investment_value_status_context"
        in (
            registry_rows["private_credit_ndfi_funding_drag"][
                "source_specific_series_or_table_ids"
            ]
        )
    )
    sec_bdc_context = snapshots["sec_bdc_public_filing_availability_context"]
    assert sec_bdc_context.metadata.source_id == "sec_edgar"
    assert sec_bdc_context.metadata.snapshot_kind == "live_sec_edgar_filing_context"
    assert sec_bdc_context.metadata.units == "bdc_public_filing_availability_context"
    assert len(sec_bdc_context.records) == 4
    sec_bdc_note = sec_bdc_context.metadata.note or ""
    assert "sec_edgar_bdc_public_filing_availability_context_only" in (sec_bdc_note)
    assert "source_record_count=4" in sec_bdc_note
    assert "public_reusable_company_filing_artifact_available=true" in (sec_bdc_note)
    assert "public_reusable_normalized_loan_level_panel_available=false" in (
        sec_bdc_note
    )
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_bdc_context.records
    } == {"false"}
    sec_bdc_terms_context = snapshots["sec_bdc_portfolio_investment_terms_panel"]
    assert sec_bdc_terms_context.metadata.source_id == "sec_edgar"
    assert (
        sec_bdc_terms_context.metadata.snapshot_kind
        == "live_sec_edgar_normalized_filing_table_panel"
    )
    assert sec_bdc_terms_context.metadata.units == "source_filing_table_units"
    assert len(sec_bdc_terms_context.records) >= 1000
    sec_bdc_terms_note = sec_bdc_terms_context.metadata.note or ""
    assert "sec_edgar_bdc_portfolio_investment_terms_panel" in sec_bdc_terms_note
    assert "public_reusable_normalized_investment_terms_panel_available=true" in (
        sec_bdc_terms_note
    )
    assert "borrower_pass_through_context_available=false" in sec_bdc_terms_note
    assert "nonbank_to_real_activity_context_available=false" in sec_bdc_terms_note
    assert {
        record["public_reusable_normalized_investment_terms_panel_available"]
        for record in sec_bdc_terms_context.records
    } == {"true"}
    assert {
        record["borrower_pass_through_context_available"]
        for record in sec_bdc_terms_context.records
    } == {"false"}
    assert {
        record["nonbank_to_real_activity_context_available"]
        for record in sec_bdc_terms_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_bdc_terms_context.records
    } == {"false"}
    sec_bdc_status_context = snapshots["sec_bdc_portfolio_performance_status_panel"]
    assert sec_bdc_status_context.metadata.source_id == "sec_edgar"
    assert (
        sec_bdc_status_context.metadata.snapshot_kind
        == "live_sec_edgar_bdc_performance_status_panel"
    )
    assert sec_bdc_status_context.metadata.units == "source_filing_table_units"
    assert len(sec_bdc_status_context.records) >= 1000
    sec_bdc_status_note = sec_bdc_status_context.metadata.note or ""
    assert "sec_edgar_bdc_portfolio_performance_status_panel" in (sec_bdc_status_note)
    assert "non_accrual_marker_rows=" in sec_bdc_status_note
    assert "valuation_gap_context_rows=" in sec_bdc_status_note
    assert "public_reusable_borrower_level_performance_marker_available=true" in (
        sec_bdc_status_note
    )
    assert "borrower_pass_through_context_available=false" in sec_bdc_status_note
    assert {
        record["borrower_pass_through_context_available"]
        for record in sec_bdc_status_context.records
    } == {"false"}
    assert {
        record["nonbank_to_real_activity_context_available"]
        for record in sec_bdc_status_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_bdc_status_context.records
    } == {"false"}
    sec_bdc_join_context = snapshots["sec_bdc_portfolio_terms_status_join_panel"]
    assert sec_bdc_join_context.metadata.source_id == "sec_edgar"
    assert (
        sec_bdc_join_context.metadata.snapshot_kind
        == "live_sec_edgar_bdc_terms_status_join_panel"
    )
    assert sec_bdc_join_context.metadata.units == "source_filing_table_units"
    assert len(sec_bdc_join_context.records) >= 1000
    sec_bdc_join_note = sec_bdc_join_context.metadata.note or ""
    assert "sec_edgar_bdc_portfolio_terms_status_join_panel" in sec_bdc_join_note
    assert "source_record_count=4287" in sec_bdc_join_note
    assert "full_terms_and_performance_status_rows=" in sec_bdc_join_note
    assert (
        "public_reusable_borrower_investment_terms_status_panel_available=true"
        in sec_bdc_join_note
    )
    assert "monetary_pass_through_design_available=false" in sec_bdc_join_note
    assert "nonbank_to_real_activity_context_available=false" in sec_bdc_join_note
    assert {
        record["public_reusable_borrower_investment_terms_status_panel_available"]
        for record in sec_bdc_join_context.records
    } == {"true"}
    assert {
        record["monetary_pass_through_design_available"]
        for record in sec_bdc_join_context.records
    } == {"false"}
    assert {
        record["nonbank_to_real_activity_context_available"]
        for record in sec_bdc_join_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_bdc_join_context.records
    } == {"false"}
    sec_bdc_time_context = snapshots["sec_bdc_portfolio_terms_status_time_panel"]
    assert sec_bdc_time_context.metadata.source_id == "sec_edgar"
    assert (
        sec_bdc_time_context.metadata.snapshot_kind
        == "live_sec_edgar_bdc_terms_status_time_panel"
    )
    assert sec_bdc_time_context.metadata.units == "source_filing_table_units"
    assert len(sec_bdc_time_context.records) > len(sec_bdc_join_context.records)
    sec_bdc_time_note = sec_bdc_time_context.metadata.note or ""
    assert "sec_edgar_bdc_portfolio_terms_status_time_panel" in sec_bdc_time_note
    assert "periodic_filing_count=16" in sec_bdc_time_note
    assert "report_date_count=4" in sec_bdc_time_note
    assert (
        "public_reusable_borrower_investment_time_dimension_available=true"
        in sec_bdc_time_note
    )
    assert "public_reusable_repayment_schedule_panel_available=false" in (
        sec_bdc_time_note
    )
    assert "monetary_pass_through_design_available=false" in sec_bdc_time_note
    assert "nonbank_to_real_activity_context_available=false" in sec_bdc_time_note
    assert {
        record["public_reusable_borrower_investment_time_dimension_available"]
        for record in sec_bdc_time_context.records
    } == {"true"}
    assert {
        record["stable_public_borrower_identifier_available"]
        for record in sec_bdc_time_context.records
    } == {"false"}
    assert {
        record["public_reusable_repayment_schedule_panel_available"]
        for record in sec_bdc_time_context.records
    } == {"false"}
    assert {
        record["monetary_pass_through_design_available"]
        for record in sec_bdc_time_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_bdc_time_context.records
    } == {"false"}
    sec_bdc_pass_context = snapshots[
        "sec_bdc_floating_rate_pass_through_design_context"
    ]
    assert sec_bdc_pass_context.metadata.source_id == "sec_edgar"
    assert (
        sec_bdc_pass_context.metadata.snapshot_kind
        == "derived_sec_edgar_bdc_floating_rate_pass_through_context"
    )
    assert sec_bdc_pass_context.metadata.units == "source_filing_table_units"
    sec_bdc_pass_note = sec_bdc_pass_context.metadata.note or ""
    assert "sec_edgar_bdc_floating_rate_pass_through_design_context" in (
        sec_bdc_pass_note
    )
    assert "contractual_floating_rate_pass_through_context_available=true" in (
        sec_bdc_pass_note
    )
    assert "promotion_grade_monetary_pass_through_design_available=false" in (
        sec_bdc_pass_note
    )
    assert {
        record["contractual_floating_rate_pass_through_context_available"]
        for record in sec_bdc_pass_context.records
    } == {"true"}
    assert {
        record["promotion_grade_monetary_pass_through_design_available"]
        for record in sec_bdc_pass_context.records
    } == {"false"}
    assert {
        record["stable_public_borrower_identifier_available"]
        for record in sec_bdc_pass_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_bdc_pass_context.records
    } == {"false"}
    sec_bdc_name_context = snapshots["sec_bdc_borrower_name_continuity_context"]
    assert sec_bdc_name_context.metadata.source_id == "sec_edgar"
    assert (
        sec_bdc_name_context.metadata.snapshot_kind
        == "derived_sec_edgar_bdc_borrower_name_continuity_context"
    )
    assert sec_bdc_name_context.metadata.units == "source_filing_table_units"
    sec_bdc_name_note = sec_bdc_name_context.metadata.note or ""
    assert "sec_edgar_bdc_borrower_name_continuity_context" in (sec_bdc_name_note)
    assert "exact_public_borrower_name_continuity_context_available=true" in (
        sec_bdc_name_note
    )
    assert "stable_public_borrower_identifier_available=false" in (sec_bdc_name_note)
    assert {
        record["exact_public_borrower_name_continuity_context_available"]
        for record in sec_bdc_name_context.records
    } == {"true"}
    assert {
        record["stable_public_borrower_identifier_available"]
        for record in sec_bdc_name_context.records
    } == {"false"}
    assert {
        record["public_reusable_loan_identifier_available"]
        for record in sec_bdc_name_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_bdc_name_context.records
    } == {"false"}
    sec_bdc_signature_context = snapshots[
        "sec_bdc_investment_signature_continuity_context"
    ]
    assert sec_bdc_signature_context.metadata.source_id == "sec_edgar"
    assert (
        sec_bdc_signature_context.metadata.snapshot_kind
        == "derived_sec_edgar_bdc_investment_signature_continuity_context"
    )
    assert sec_bdc_signature_context.metadata.units == "source_filing_table_units"
    sec_bdc_signature_note = sec_bdc_signature_context.metadata.note or ""
    assert "sec_edgar_bdc_investment_signature_continuity_context" in (
        sec_bdc_signature_note
    )
    assert (
        "public_investment_signature_continuity_context_available=true"
        in sec_bdc_signature_note
    )
    assert "stable_public_borrower_identifier_available=false" in (
        sec_bdc_signature_note
    )
    assert {
        record["public_investment_signature_continuity_context_available"]
        for record in sec_bdc_signature_context.records
    } == {"true"}
    assert {
        record["stable_public_borrower_identifier_available"]
        for record in sec_bdc_signature_context.records
    } == {"false"}
    assert {
        record["public_reusable_loan_identifier_available"]
        for record in sec_bdc_signature_context.records
    } == {"false"}
    assert {
        record["public_reusable_repayment_schedule_panel_available"]
        for record in sec_bdc_signature_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_bdc_signature_context.records
    } == {"false"}
    sec_bdc_value_status_context = snapshots[
        "sec_bdc_recurring_investment_value_status_context"
    ]
    assert sec_bdc_value_status_context.metadata.source_id == "sec_edgar"
    assert (
        sec_bdc_value_status_context.metadata.snapshot_kind
        == "derived_sec_edgar_bdc_recurring_investment_value_status_context"
    )
    assert sec_bdc_value_status_context.metadata.units == "source_filing_table_units"
    sec_bdc_value_status_note = sec_bdc_value_status_context.metadata.note or ""
    assert "sec_edgar_bdc_recurring_investment_value_status_context" in (
        sec_bdc_value_status_note
    )
    assert (
        "public_recurring_investment_value_status_context_available=true"
        in sec_bdc_value_status_note
    )
    assert "value_or_status_variation_context_rows=" in sec_bdc_value_status_note
    assert "stable_public_borrower_identifier_available=false" in (
        sec_bdc_value_status_note
    )
    assert {
        record["public_recurring_investment_value_status_context_available"]
        for record in sec_bdc_value_status_context.records
    } == {"true"}
    assert {
        record["stable_public_borrower_identifier_available"]
        for record in sec_bdc_value_status_context.records
    } == {"false"}
    assert {
        record["public_reusable_repayment_schedule_panel_available"]
        for record in sec_bdc_value_status_context.records
    } == {"false"}
    assert {
        record["monetary_pass_through_design_available"]
        for record in sec_bdc_value_status_context.records
    } == {"false"}
    assert {
        record["split_denominator_promotion_allowed"]
        for record in sec_bdc_value_status_context.records
    } == {"false"}
    assert (
        "admitted_source_ids=MORTGAGE30US"
        in (
            registry_rows["mortgage_lockin_payment_shield_shelter_sidecar"][
                "source_status"
            ]
        )
    )
    assert (
        "admitted_source_ids=B112RC1Q027SBEA;GDP"
        in (registry_rows["state_local_cash_interest_spendback"]["source_status"])
    )
    assert {row["enters_main_offset_ratio"] for row in registry_rows.values()} == {
        "false"
    }


def test_corporate_net_interest_fred_snapshots_are_materialized_fail_closed() -> None:
    snapshots = {
        snapshot.metadata.series_id: snapshot
        for snapshot in read_snapshot_bundle(Path("data/raw/ratewall_snapshot.json"))
    }

    for series_id in (
        "BOGZ1FU106130001Q",
        "BOGZ1FU106130101Q",
        "NCBCDCA",
        "TSDABSNNCB",
        "TSABSNNCB",
        "BOGZ1FL103034000Q",
        "SRPSABSNNCB",
        "CBLBSNNCB",
        "NCBDBIQ027S",
        "NCBLL",
        "CPLBSNNCB",
    ):
        snapshot = snapshots[series_id]
        assert snapshot.metadata.source_id == "fred"
        assert snapshot.metadata.snapshot_kind == "live"
        assert snapshot.metadata.units == "millions_of_dollars"
        assert snapshot.metadata.frequency == "quarterly"
        assert len(snapshot.records) > 250
        assert "source_records_sha256=" in (snapshot.metadata.note or "")
        assert "prior_narrowing_allowed=false" in (snapshot.metadata.note or "")
        assert "formula_replacement_allowed=false" in (snapshot.metadata.note or "")
        assert "main_ratio_admission_allowed=false" in (snapshot.metadata.note or "")

    qfr_snapshot = snapshots["census_qfr_interest_expense"]
    qfr_note = qfr_snapshot.metadata.note or ""
    assert qfr_snapshot.metadata.source_id == "census_qfr"
    assert qfr_snapshot.metadata.snapshot_kind == "live"
    assert qfr_snapshot.metadata.source_url.endswith("qfr25q4f.xlsx")
    assert qfr_snapshot.metadata.units == "million_dollars_or_percent_as_published"
    assert qfr_snapshot.metadata.source_release_at == "2026-03-23"
    assert len(qfr_snapshot.records) > 1000
    assert "source_workbook_sha256=" in qfr_note
    assert "source_records_sha256=" in qfr_note
    assert "aggregate_qfr_cash_debt_maturity_context_only" in qfr_note
    assert "fixed_floating_direct_evidence=false" in qfr_note
    assert "firm_level_overlap_evidence=false" in qfr_note
    assert "main_ratio_admission_allowed=false" in qfr_note
    assert {
        "interest_expense",
        "short_term_debt_original_maturity",
        "current_long_term_debt_due_within_one_year",
        "long_term_debt_due_more_than_one_year",
        "total_cash_us_government_other_securities",
    } <= {str(record["field_role"]) for record in qfr_snapshot.records}


def test_treasury_dts_tga_snapshot_is_materialized_fail_closed() -> None:
    snapshots = {
        snapshot.metadata.series_id: snapshot
        for snapshot in read_snapshot_bundle(Path("data/raw/ratewall_snapshot.json"))
    }

    snapshot = snapshots["treasury_dts"]
    note = snapshot.metadata.note or ""
    assert snapshot.metadata.source_id == "treasury_fiscaldata"
    assert snapshot.metadata.snapshot_kind == "live"
    assert snapshot.metadata.source_url.startswith(
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
        "v1/accounting/dts/operating_cash_balance"
    )
    assert snapshot.metadata.units == "millions_of_dollars"
    assert snapshot.metadata.frequency == "daily"
    assert snapshot.metadata.transform == "treasury_operating_cash_balance_tga_context"
    assert len(snapshot.records) > 50
    assert "source_records_sha256=" in note
    assert "Treasury General Account (TGA) Closing Balance" in note
    assert "timing_nonadditivity_bridge_passed=false" in note
    assert "absorber_prior_narrowing_allowed=false" in note
    assert "formula_replacement_allowed=false" in note
    assert "main_ratio_admission_allowed=false" in note
    assert {
        "record_date",
        "account_type",
        "open_today_bal",
        "table_nm",
        "src_line_nbr",
    } <= set(snapshot.records[0])

    bridge_rows = list(
        csv.DictReader(
            Path("outputs/tables/ratewall_public_finance_timing_bridge.csv").open(
                encoding="utf-8"
            )
        )
    )
    fiscal_row = next(
        row for row in bridge_rows if row["timing_object"] == "fiscal_offset"
    )
    tga_row = next(
        row for row in bridge_rows if row["timing_object"] == "tga_liquidity_offset"
    )
    assert fiscal_row["netting_nonadditivity_context_status"] == (
        "blocked_mts_dts_h41_wtregen_current_flow_netting_reviewed_no_shared_flow_key"
    )
    assert tga_row["netting_nonadditivity_context_status"] == (
        "blocked_dts_wtregen_h41_context_reviewed_no_tga_financing_source_counterparty_split"
    )
    assert "shared_cashflow_key" in fiscal_row["exact_blocker"]
    assert (
        "financing-source counterparty split"
        in tga_row["evidence_needed_before_prior_narrowing"]
    )
    assert fiscal_row["can_narrow_absorber_prior"] == "false"
    assert tga_row["can_narrow_absorber_prior"] == "false"


def test_databook_builds_tables_figures_and_provenance(tmp_path: Path) -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    snapshot = build_snapshot_bundle(
        registry=registry,
        output=tmp_path / "snapshot.json",
        mode="demo",
    )

    artifacts = build_databook(
        snapshot_bundle=snapshot, output_dir=tmp_path / "outputs"
    )

    rows = list(csv.DictReader(artifacts.impulse_table.open(encoding="utf-8")))
    assert [row["horizon"] for row in rows] == ["1q", "1y", "3y", "10y"]
    assert artifacts.summary_table.exists()
    metrics = list(csv.DictReader(artifacts.metrics_table.open(encoding="utf-8")))
    assert len(metrics) >= 15
    metric_names = {row["metric"] for row in metrics}
    assert {
        "household_debt_service_ratio",
        "bank_loans_leases_gdp",
        "national_financial_conditions_index",
        "top10_bottom50_interest_asset_gap",
        "top10_liability_share",
        "cbo_2036_net_interest_gdp",
        "private_investor_holder_share",
        "treasury_buybacks_accepted_gdp",
        "ratewall_threshold_simulation_rows",
        "financialization_pressure_context_rows",
    } <= metric_names
    assert len(artifacts.metric_figures) >= 15
    assert all(path.exists() for path in artifacts.metric_figures)
    dashboard_rows = list(
        csv.DictReader(artifacts.ratewall_dashboard_table.open(encoding="utf-8"))
    )
    assert {row["dashboard_component"] for row in dashboard_rows} == {
        "mechanical_ratewall_score",
        "empirical_readiness_score",
        "welfare_boundary_score",
        "ratewall_release_completion_score",
    }
    assert all(row["pricing_output_enabled"] == "false" for row in dashboard_rows)
    assert all(
        row["reset_calendar_construction_enabled"] == "false" for row in dashboard_rows
    )
    assert all(row["welfare_incidence_enabled"] == "false" for row in dashboard_rows)
    mechanical_dashboard = next(
        row
        for row in dashboard_rows
        if row["dashboard_component"] == "mechanical_ratewall_score"
    )
    assert mechanical_dashboard["status"] == "fallback_context_only_mechanical_index"
    assert any(
        row["claim_boundary"] == "release_completion_not_pricing_or_incidence_result"
        for row in dashboard_rows
    )
    paper_support = artifacts.paper_support_report.read_text(encoding="utf-8")
    assert "RateWall Paper Support Packet" in paper_support
    assert "does not claim that higher rates always raise inflation" in paper_support
    assert "remain disabled" in paper_support
    tdc_historical = list(
        csv.DictReader(artifacts.tdc_historical_panel_table.open(encoding="utf-8"))
    )
    assert tdc_historical
    assert {row["pricing_output_enabled"] for row in tdc_historical} == {"false"}
    assert {row["incidence_claim_enabled"] for row in tdc_historical} == {"false"}
    assert any(
        row["source_coverage_status"]
        in {"partial_source_backed_proxy", "coverage_limited_missing_exact_du_ru_split"}
        for row in tdc_historical
    )
    deposit_pricing = list(
        csv.DictReader(
            artifacts.deposit_pricing_pass_through_table.open(encoding="utf-8")
        )
    )
    assert deposit_pricing
    assert {row["pricing_output_enabled"] for row in deposit_pricing} == {"false"}
    assert all(
        row["claim_boundary"]
        == "deposit_pricing_context_not_pricing_model_or_tdc_identity"
        for row in deposit_pricing
    )
    tdc_reconciliation = list(
        csv.DictReader(
            artifacts.tdc_historical_reconciliation_table.open(encoding="utf-8")
        )
    )
    tdc_source_coverage = list(
        csv.DictReader(artifacts.tdc_source_coverage_table.open(encoding="utf-8"))
    )
    public_impulse_coverage = next(
        row
        for row in tdc_source_coverage
        if row["tdc_component"] == "public_interest_impulse"
    )
    assert public_impulse_coverage["coverage_status"] in {
        "fallback_context_only",
        "source_backed",
    }
    assert len(public_impulse_coverage["latest_as_of"]) == 10
    assert public_impulse_coverage["latest_period"] == ""
    tdc_impulse_rows = list(
        csv.DictReader(
            artifacts.tdc_ru_financing_deposit_impulse_table.open(encoding="utf-8")
        )
    )
    assert tdc_impulse_rows
    assert {row["mspd_table3_snapshot_kind"] for row in tdc_impulse_rows} <= {
        "fallback_stub",
        "demo_stub",
    }
    assert {row["recipient_base_status"] for row in tdc_impulse_rows} == {
        "recipient_base_incomplete_sensitivity_review"
    }
    assert all("scenario_diagnostic" in row["allowed_use"] for row in tdc_impulse_rows)
    assert {row["coverage_status"] for row in tdc_reconciliation} >= {
        "source_backed",
        "missing",
    }
    assert all(
        not row["latest_as_of"] or len(row["latest_as_of"]) == 10
        for row in tdc_reconciliation
    )
    threshold_rows = list(
        csv.DictReader(
            artifacts.ratewall_threshold_simulation_table.open(encoding="utf-8")
        )
    )
    assert {row["horizon"] for row in threshold_rows} == {
        "1q",
        "1y",
        "3y",
        "5y",
        "10y",
    }
    assert {row["assumption_status"] for row in threshold_rows} == {
        "speculative_scenario_assumptions"
    }
    assert {row["threshold_hit_under_assumptions"] for row in threshold_rows} <= {
        "true",
        "false",
    }
    assert {row["deposit_pricing_income_context_bil"] for row in threshold_rows} == {
        "0"
    }
    assert {row["financialization_causal_claim_enabled"] for row in threshold_rows} == {
        "false"
    }
    assert {row["pricing_output_enabled"] for row in threshold_rows} == {"false"}
    assert {row["incidence_claim_enabled"] for row in threshold_rows} == {"false"}
    assert {row["welfare_claim_enabled"] for row in threshold_rows} == {"false"}
    financialization_rows = list(
        csv.DictReader(artifacts.financialization_pressure_table.open(encoding="utf-8"))
    )
    assert financialization_rows
    assert {row["claim_boundary"] for row in financialization_rows} == {
        "financialization_pressure_context_not_causal_financialization"
    }
    assert {
        row["financialization_causal_claim_enabled"] for row in financialization_rows
    } == {"false"}
    calibration_rows = list(
        csv.DictReader(
            artifacts.ratewall_threshold_calibration_ranges_table.open(encoding="utf-8")
        )
    )
    assert {
        "ru_absorption_share",
        "deposit_beta",
        "financial_retention_share",
    } <= {row["calibration_parameter"] for row in calibration_rows}
    assert any(
        row["source_status"] in {"source_backed", "sibling_derived_source_backed"}
        for row in calibration_rows
    )
    assert {row["claim_boundary"] for row in calibration_rows} == {
        "calibration_range_not_final_incidence_or_causal_claim"
    }
    calibrated_threshold_rows = list(
        csv.DictReader(
            artifacts.ratewall_threshold_calibrated_simulation_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["horizon"] for row in calibrated_threshold_rows} == {
        "1q",
        "1y",
        "3y",
        "5y",
        "10y",
    }
    assert {row["assumption_status"] for row in calibrated_threshold_rows} == {
        "calibration_range_sensitivity_review"
    }
    assert {
        row["threshold_hit_under_assumptions"] for row in calibrated_threshold_rows
    } <= {"true", "false"}
    assert all(
        "du_outlay_share" in row["remaining_speculative_inputs"]
        for row in calibrated_threshold_rows
    )
    assert "source_backed_range_label" not in calibrated_threshold_rows[0]
    assert {row["recipient_base_status"] for row in calibrated_threshold_rows} == {
        "recipient_base_incomplete_sensitivity_review"
    }
    assert all(
        "Calibration-range sensitivity scenario" in row["scenario_description"]
        for row in calibrated_threshold_rows
    )
    assert {row["pricing_output_enabled"] for row in calibrated_threshold_rows} == {
        "false"
    }
    assumption_rows = list(
        csv.DictReader(artifacts.ratewall_assumption_sets_table.open(encoding="utf-8"))
    )
    assert assumption_rows
    assert {row["mode"] for row in assumption_rows} == {"assumption_mode"}
    assert "zero_interest_credit_extension" in {
        row["assumption_set"] for row in assumption_rows
    }
    assert {
        "borrowing_cost_drag_share",
        "credit_supply_drag_share",
        "asset_price_drag_share",
        "expectations_drag_share",
        "exchange_rate_external_drag_share",
        "denominator_share_sum",
        "denominator_share_sum_status",
        "split_denominator_total_drag_multiplier",
    } <= set(assumption_rows[0])
    wall_hit_rows = list(
        csv.DictReader(
            artifacts.ratewall_wall_hit_scenarios_table.open(encoding="utf-8")
        )
    )
    assert wall_hit_rows
    assert {row["wall_hit_under_assumptions"] for row in wall_hit_rows} == {
        "false",
        "true",
    }
    assert {row["claim_boundary"] for row in wall_hit_rows} == {
        "speculative_assumption_mode_not_empirical_threshold_date"
    }
    assert {row["empirical_claim_enabled"] for row in wall_hit_rows} == {"false"}
    assert {row["policy_failure_claim_enabled"] for row in wall_hit_rows} == {"false"}
    assert {row["pricing_output_enabled"] for row in wall_hit_rows} == {"false"}
    assert {row["incidence_claim_enabled"] for row in wall_hit_rows} == {"false"}
    assert {row["welfare_claim_enabled"] for row in wall_hit_rows} == {"false"}
    assert {row["component_recipient_map_status"] for row in wall_hit_rows} == {
        "component_recipient_maps_assumption_mode_incomplete_not_incidence"
    }
    assert {
        "split_denominator_conventional_drag_bil",
        "split_denominator_offset_ratio",
        "split_denominator_wall_hit_under_assumptions",
        "split_denominator_wall_classification",
        "denominator_model_comparison",
        "private_recipient_cashflow_impulse_bil",
        "component_display_public_impulse_total_bil",
        "future_public_finance_drag_bil",
        "safe_asset_allocation_drag_bil",
        "classification_change_driver",
        "scalar_countervailing_total_bil",
        "composition_only_countervailing_total_bil",
        "total_scaled_countervailing_total_bil",
        "targeted_attenuation_drag_basis",
        "scalar_baseline_uses_split_targeted_attenuation",
        "dominant_gross_interest_subchannel",
        "dominant_net_countervailing_channel",
        "net_interest_after_fiscal_tga_offsets_bil",
    } <= set(wall_hit_rows[0])
    for row in wall_hit_rows:
        assert Decimal(row["gross_public_interest_impulse_bil"]) == Decimal(
            row["private_recipient_cashflow_impulse_bil"]
        )
        assert Decimal(row["component_display_public_impulse_total_bil"]) >= Decimal(
            row["gross_public_interest_impulse_bil"]
        )
        assert row["scalar_baseline_uses_split_targeted_attenuation"] == "false"
        scalar_ratio = Decimal(row["scalar_countervailing_total_bil"]) / Decimal(
            row["conventional_contractionary_effect_bil"]
        )
        split_ratio = Decimal(row["total_scaled_countervailing_total_bil"]) / Decimal(
            row["split_denominator_conventional_drag_bil"]
        )
        assert scalar_ratio == Decimal(row["ratewall_offset_ratio"])
        assert split_ratio == Decimal(row["split_denominator_offset_ratio"])
        assert Decimal(row["net_interest_after_fiscal_tga_offsets_bil"]) == Decimal(
            row["net_interest_demand_offset_bil"]
        )
        assert (
            row["dominant_countervailing_channel"]
            == row["dominant_net_countervailing_channel"]
        )
        if Decimal(row["net_interest_after_fiscal_tga_offsets_bil"]) == 0:
            assert row["dominant_net_countervailing_channel"] != (
                "treasury_interest_demand_offset"
            )
    assert all(row["why_hit_or_nonhit"] for row in wall_hit_rows)
    frontier_rows = list(
        csv.DictReader(
            artifacts.ratewall_condition_frontier_table.open(encoding="utf-8")
        )
    )
    assert {
        "at_or_beyond_wall_under_assumptions",
        "below_wall_under_assumptions",
    } <= {row["frontier_status"] for row in frontier_rows}
    solver_rows = list(
        csv.DictReader(artifacts.ratewall_threshold_solver_table.open(encoding="utf-8"))
    )
    assert {row["answer_status"] for row in solver_rows} == {
        "wall_hit_under_assumptions",
        "wall_not_hit_under_assumptions",
    }
    decomposition_rows = list(
        csv.DictReader(
            artifacts.ratewall_offset_decomposition_table.open(encoding="utf-8")
        )
    )
    assert decomposition_rows
    assert "share_of_countervailing_total" in decomposition_rows[0]
    assert "decisive_channel_label" in decomposition_rows[0]
    assert "additivity_scope" in decomposition_rows[0]
    assert {
        "gross_subchannel_nonadditive",
        "net_additive_countervailing",
    } <= {row["additivity_scope"] for row in decomposition_rows}
    public_impulse_rows = list(
        csv.DictReader(
            artifacts.ratewall_public_impulse_factorization_table.open(encoding="utf-8")
        )
    )
    assert len(public_impulse_rows) == len(assumption_rows)
    assert {row["public_impulse_multiplier_status"] for row in public_impulse_rows} == {
        "deprecated_compatibility_field_derived_from_factored_public_impulse_handles"
    }
    assert all(row["rate_path_bps_year"] for row in public_impulse_rows)
    repricing_ladder_rows = list(
        csv.DictReader(
            artifacts.ratewall_public_liability_repricing_ladder_table.open(
                encoding="utf-8"
            )
        )
    )
    repricing_evidence_bridge_rows = list(
        csv.DictReader(
            artifacts.ratewall_public_liability_repricing_evidence_bridge_table.open(
                encoding="utf-8"
            )
        )
    )
    repricing_reconciliation_gap_rows = list(
        csv.DictReader(
            artifacts.ratewall_public_liability_repricing_reconciliation_gap_table.open(
                encoding="utf-8"
            )
        )
    )
    recipient_bridge_rows = list(
        csv.DictReader(
            artifacts.ratewall_interest_recipient_leakage_bridge_table.open(
                encoding="utf-8"
            )
        )
    )
    recipient_evidence_gap_rows = list(
        csv.DictReader(
            artifacts.ratewall_interest_recipient_leakage_evidence_gap_table.open(
                encoding="utf-8"
            )
        )
    )
    treasury_recipient_source_gate_rows = list(
        csv.DictReader(
            artifacts.ratewall_treasury_recipient_leakage_source_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    finance_timing_rows = list(
        csv.DictReader(
            artifacts.ratewall_public_finance_timing_path_table.open(encoding="utf-8")
        )
    )
    finance_timing_evidence_gap_rows = list(
        csv.DictReader(
            artifacts.ratewall_public_finance_timing_evidence_gap_table.open(
                encoding="utf-8"
            )
        )
    )
    finance_timing_design_test_rows = list(
        csv.DictReader(
            artifacts.ratewall_public_finance_timing_design_test_scaffold_table.open(
                encoding="utf-8"
            )
        )
    )
    module_registry_rows = list(
        csv.DictReader(
            artifacts.ratewall_interest_channel_module_registry_table.open(
                encoding="utf-8"
            )
        )
    )
    channel_completion_matrix_rows = list(
        csv.DictReader(
            artifacts.ratewall_interest_channel_completion_matrix_table.open(
                encoding="utf-8"
            )
        )
    )
    dynamic_scenario_path_rows = list(
        csv.DictReader(
            artifacts.ratewall_dynamic_scenario_paths_table.open(encoding="utf-8")
        )
    )
    dynamic_scenario_path_consistency_rows = list(
        csv.DictReader(
            artifacts.ratewall_dynamic_scenario_path_consistency_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    dynamic_offset_ratio_path_rows = list(
        csv.DictReader(
            artifacts.ratewall_dynamic_offset_ratio_path_table.open(encoding="utf-8")
        )
    )
    scenario_crossing_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_scenario_crossing_diagnostic_table.open(encoding="utf-8")
        )
    )
    dynamic_sensitivity_frontier_rows = list(
        csv.DictReader(
            artifacts.ratewall_dynamic_sensitivity_frontier_table.open(encoding="utf-8")
        )
    )
    dynamic_scenario_family_registry_rows = list(
        csv.DictReader(
            artifacts.ratewall_dynamic_scenario_family_registry_table.open(
                encoding="utf-8"
            )
        )
    )
    dynamic_uncertainty_envelope_rows = list(
        csv.DictReader(
            artifacts.ratewall_dynamic_uncertainty_envelope_table.open(encoding="utf-8")
        )
    )
    tdc_materialization_semantic_summary_rows = list(
        csv.DictReader(
            artifacts.ratewall_tdc_materialization_semantic_summary_table.open(
                encoding="utf-8"
            )
        )
    )
    dynamic_crossing_robustness_rows = list(
        csv.DictReader(
            artifacts.ratewall_dynamic_crossing_robustness_table.open(encoding="utf-8")
        )
    )
    safe_yield_pairing_gap_rows = list(
        csv.DictReader(
            artifacts.ratewall_safe_yield_offset_drag_pairing_gap_table.open(
                encoding="utf-8"
            )
        )
    )
    bnpl_float_gap_rows = list(
        csv.DictReader(
            artifacts.ratewall_bnpl_zero_interest_float_evidence_gap_table.open(
                encoding="utf-8"
            )
        )
    )
    financialized_gap_rows = list(
        csv.DictReader(
            artifacts.ratewall_financialized_balance_sheet_evidence_gap_table.open(
                encoding="utf-8"
            )
        )
    )
    firm_gap_rows = list(
        csv.DictReader(
            artifacts.ratewall_firm_cash_debt_maturity_evidence_gap_table.open(
                encoding="utf-8"
            )
        )
    )
    conventional_drag_gap_rows = list(
        csv.DictReader(
            artifacts.ratewall_conventional_drag_channel_evidence_gap_table.open(
                encoding="utf-8"
            )
        )
    )
    conventional_drag_source_design_gate_rows = list(
        csv.DictReader(
            artifacts.ratewall_conventional_drag_source_design_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_response_design_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_response_design_scaffold_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_response_design_test_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_response_design_test_scaffold_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_response_gate_attempt_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_response_gate_attempt_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_aligned_response_panel_scaffold_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_aligned_response_panel_scaffold_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_event_outcome_cell_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_event_outcome_cell_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_event_outcome_panel_value_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_event_outcome_panel_value_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_event_level_response_panel_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_event_level_response_panel_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_uncertainty_pass_fail_review_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_uncertainty_pass_fail_review_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_panel_design_test_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_panel_design_test_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_pretrend_placebo_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_pretrend_placebo_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_shock_relevance_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_shock_relevance_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_sign_consistency_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_sign_consistency_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_horizon_sensitivity_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_horizon_sensitivity_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_outlier_window_robustness_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_outlier_window_robustness_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_design_readiness_decision_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_design_readiness_decision_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_formal_design_test_result_scaffold_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_formal_design_test_result_scaffold_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_formal_design_test_result_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_formal_design_test_result_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_response_estimate_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_response_estimate_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_cross_source_design_validation_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_cross_source_design_validation_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_evidence_upgrade_source_design_requirement_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_evidence_upgrade_source_design_requirement_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_evidence_upgrade_priority_queue_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_evidence_upgrade_priority_queue_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_evidence_upgrade_tier1_workplan_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_evidence_upgrade_tier1_workplan_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_evidence_upgrade_blocker_resolution_matrix_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_evidence_upgrade_blocker_resolution_matrix_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_evidence_upgrade_blocker_status_rollup_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_evidence_upgrade_blocker_status_rollup_table.open(
                encoding="utf-8"
            )
        )
    )
    conventional_drag_evidence_tranche_rows = list(
        csv.DictReader(
            artifacts.ratewall_conventional_drag_evidence_tranche_table.open(
                encoding="utf-8"
            )
        )
    )
    conventional_drag_demand_conversion_admission_rows = list(
        csv.DictReader(
            artifacts.ratewall_conventional_drag_demand_conversion_admission_table.open(
                encoding="utf-8"
            )
        )
    )
    horizon_timing_rows = list(
        csv.DictReader(
            artifacts.ratewall_interest_channel_horizon_timing_matrix_table.open(
                encoding="utf-8"
            )
        )
    )
    promotion_gate_rows = list(
        csv.DictReader(
            artifacts.ratewall_interest_channel_promotion_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    evidence_upgrade_queue_rows = list(
        csv.DictReader(
            artifacts.ratewall_interest_channel_evidence_upgrade_queue_table.open(
                encoding="utf-8"
            )
        )
    )
    high_priority_source_bridge_rows = list(
        csv.DictReader(
            artifacts.ratewall_high_priority_interest_channel_source_bridge_table.open(
                encoding="utf-8"
            )
        )
    )
    source_gate_decision_rows = list(
        csv.DictReader(
            artifacts.ratewall_source_gate_prior_narrowing_decision_table.open(
                encoding="utf-8"
            )
        )
    )
    source_gate_exhaustion_closure_rows = list(
        csv.DictReader(
            artifacts.ratewall_source_gate_exhaustion_closure_table.open(
                encoding="utf-8"
            )
        )
    )
    restricted_data_gate_spec_rows = list(
        csv.DictReader(
            artifacts.ratewall_restricted_data_gate_spec_table.open(
                encoding="utf-8"
            )
        )
    )
    assumption_mode_post_closure_boundary_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_post_closure_boundary_map_table.open(
                encoding="utf-8"
            )
        )
    )
    sibling_evidence_bridge_rows = list(
        csv.DictReader(
            artifacts.ratewall_sibling_evidence_bridge_table.open(encoding="utf-8")
        )
    )
    sibling_evidence_upgrade_queue_rows = list(
        csv.DictReader(
            artifacts.ratewall_sibling_evidence_upgrade_queue_table.open(
                encoding="utf-8"
            )
        )
    )
    higher_rate_channel_registry_rows = list(
        csv.DictReader(
            artifacts.ratewall_higher_rate_channel_registry_table.open(encoding="utf-8")
        )
    )
    corporate_net_interest_cashflow_bridge_rows = list(
        csv.DictReader(
            artifacts.ratewall_corporate_net_interest_cashflow_bridge_table.open(
                encoding="utf-8"
            )
        )
    )
    working_capital_cost_channel_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_working_capital_cost_channel_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    term_structure_pricing_carry_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_term_structure_pricing_carry_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    mspd_table3_bucket_gate_rows = list(
        csv.DictReader(
            artifacts.ratewall_mspd_table3_bucket_repricing_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    calibration_parameter_recommendation_rows = list(
        csv.DictReader(
            artifacts.ratewall_calibration_parameter_recommendations_table.open(
                encoding="utf-8"
            )
        )
    )
    calibration_source_plan_rows = list(
        csv.DictReader(
            artifacts.ratewall_calibration_source_acquisition_plan_table.open(
                encoding="utf-8"
            )
        )
    )
    denominator_calibration_design_gate_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_calibration_design_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    recipient_leakage_design_gate_rows = list(
        csv.DictReader(
            artifacts.ratewall_recipient_leakage_design_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    public_finance_timing_bridge_rows = list(
        csv.DictReader(
            artifacts.ratewall_public_finance_timing_bridge_table.open(encoding="utf-8")
        )
    )
    assert len(repricing_ladder_rows) == len(assumption_rows) * 5
    assert len(repricing_evidence_bridge_rows) == 8
    assert len(repricing_reconciliation_gap_rows) == 8
    assert len(recipient_bridge_rows) == len(assumption_rows) * 5
    assert len(recipient_evidence_gap_rows) == 5
    assert len(treasury_recipient_source_gate_rows) == 5
    assert len(finance_timing_rows) == len(assumption_rows) * 6
    assert len(finance_timing_evidence_gap_rows) == 5
    assert len(finance_timing_design_test_rows) == 25
    assert len(safe_yield_pairing_gap_rows) == 3
    assert len(bnpl_float_gap_rows) == 3
    assert len(financialized_gap_rows) == 3
    assert len(firm_gap_rows) == 4
    assert len(conventional_drag_gap_rows) == 5
    assert len(conventional_drag_source_design_gate_rows) == 6
    assert len(denominator_response_design_rows) == 6
    assert len(denominator_response_design_test_rows) == 30
    assert len(denominator_response_gate_attempt_rows) == 30
    denominator_cell_count = len(denominator_aligned_response_panel_scaffold_rows)
    assert denominator_cell_count == 260
    assert len(denominator_event_outcome_cell_diagnostic_rows) == denominator_cell_count
    assert (
        len(denominator_event_outcome_panel_value_diagnostic_rows)
        == denominator_cell_count
    )
    assert len(denominator_event_level_response_panel_rows) >= 0
    assert len(denominator_panel_design_test_diagnostic_rows) == (
        denominator_cell_count * 5
    )
    assert len(denominator_pretrend_placebo_diagnostic_rows) == denominator_cell_count
    assert len(denominator_shock_relevance_diagnostic_rows) == denominator_cell_count
    assert len(denominator_sign_consistency_diagnostic_rows) == denominator_cell_count
    assert (
        len(denominator_horizon_sensitivity_diagnostic_rows) == denominator_cell_count
    )
    assert (
        len(denominator_outlier_window_robustness_diagnostic_rows)
        == denominator_cell_count
    )
    assert len(denominator_design_readiness_decision_rows) == denominator_cell_count
    assert (
        len(denominator_formal_design_test_result_scaffold_rows)
        == denominator_cell_count
    )
    assert len(denominator_formal_design_test_result_rows) == denominator_cell_count
    assert len(denominator_response_estimate_diagnostic_rows) in {
        len(denominator_formal_design_test_result_rows),
        len(denominator_formal_design_test_result_rows) + 1,
    }
    assert len(denominator_cross_source_design_validation_rows) == len(
        denominator_response_estimate_diagnostic_rows
    )
    blocked_denominator_validation_groups = {
        (
            row["denominator_component"],
            row["horizon_bucket"],
            row["outcome_series_id"],
        )
        for row in denominator_cross_source_design_validation_rows
        if row["cell_validation_status"] == "blocked"
    }
    assert len(denominator_evidence_upgrade_source_design_requirement_rows) == len(
        blocked_denominator_validation_groups
    )
    assert len(denominator_evidence_upgrade_priority_queue_rows) == len(
        denominator_evidence_upgrade_source_design_requirement_rows
    )
    assert len(conventional_drag_evidence_tranche_rows) == (
        len(denominator_evidence_upgrade_tier1_workplan_rows) * 3
    )
    assert {
        row["shock_source_id"] for row in conventional_drag_evidence_tranche_rows
    } == {
        "fed_brw_monetary_policy_shocks",
        "sf_fed_monetary_policy_surprises",
        "romer_romer_2004",
    }
    assert len(conventional_drag_demand_conversion_admission_rows) == len(
        conventional_drag_evidence_tranche_rows
    )
    assert len(horizon_timing_rows) == 12 * 5
    assert len(promotion_gate_rows) == 13
    assert len(evidence_upgrade_queue_rows) == 10
    assert len(high_priority_source_bridge_rows) >= 30
    assert len(source_gate_decision_rows) == 23
    assert len(source_gate_exhaustion_closure_rows) == 5
    assert len(sibling_evidence_bridge_rows) == 14
    assert len(sibling_evidence_upgrade_queue_rows) == 14
    assert len(higher_rate_channel_registry_rows) == 13
    assert len(corporate_net_interest_cashflow_bridge_rows) == 3
    assert len(working_capital_cost_channel_diagnostic_rows) == 3
    assert len(term_structure_pricing_carry_diagnostic_rows) == 4
    assert len(mspd_table3_bucket_gate_rows) == 7
    assert len(calibration_parameter_recommendation_rows) == 14
    assert len(calibration_source_plan_rows) == 12
    assert len(denominator_calibration_design_gate_rows) == 6
    assert len(recipient_leakage_design_gate_rows) == 7
    assert len(public_finance_timing_bridge_rows) == 5
    assert len(channel_completion_matrix_rows) == 13
    assert {
        row["claim_boundary"] for row in calibration_parameter_recommendation_rows
    } == {"calibration_guidance_not_empirical_promotion"}
    assert {row["claim_boundary"] for row in calibration_source_plan_rows} == {
        "calibration_source_plan_not_claim_promotion"
    }
    assert {
        row["claim_boundary"] for row in denominator_calibration_design_gate_rows
    } == {"denominator_calibration_design_gate_not_prior_narrowing"}
    assert {row["claim_boundary"] for row in recipient_leakage_design_gate_rows} == {
        "recipient_leakage_design_gate_not_incidence_mpc_or_holder_allocation"
    }
    assert {row["claim_boundary"] for row in public_finance_timing_bridge_rows} == {
        "public_finance_timing_bridge_not_fiscal_reaction_or_threshold_claim"
    }
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in calibration_parameter_recommendation_rows
    } == {"false"}
    assert {
        row["prior_narrowing_allowed"]
        for row in denominator_calibration_design_gate_rows
    } == {"false"}
    assert {
        row["split_denominator_promotion_allowed"]
        for row in denominator_calibration_design_gate_rows
    } == {"false"}
    assert {
        row["can_narrow_demand_conversion_prior"]
        for row in recipient_leakage_design_gate_rows
    } == {"false"}
    assert {
        row["source_context_gate_movement_this_tranche"]
        for row in recipient_leakage_design_gate_rows
    } == {
        "context_gate_moved_source_specific_context_only",
        (
            "context_gate_moved_tax_account_type_average_tax_rate_"
            "payment_timing_state_agi_"
            "treasury_irs_tax_treatment_publication_550_1099_reporting_"
            "reportability_constraint_and_treasury_holder_context_"
            "fta_state_rate_scf_account_and_federal_interest_persons_business_"
            "context_only"
        ),
        "context_gate_moved_cayman_method_bridge_and_source_specific_payment_context_only",
    }
    assert any(
        row["cashflow_component"] == "on_rrp_mmf"
        and row["demand_conversion_evidence_status"]
        == "blocked_no_mmf_investor_pass_through_to_current_demand_bridge"
        for row in recipient_leakage_design_gate_rows
    )
    assert any(
        row["cashflow_component"] == "interest_income_tax_clawback"
        and row["source_context_series_ids"]
        == (
            "PII;W055RC1;NA000309Q;irs_soi_taxable_interest;"
            "irs_soi_ira_type_agi;irs_soi_average_tax_rate_percentile;"
            "fed_dfa_household_account_type_context;"
            "fed_scf_2022_safe_asset_account_tax_context;"
            "irs_estimated_tax_payment_timing;"
            "irs_soi_state_interest_agi;treasury_security_interest_tax_treatment;"
            "FDHBPIN;FDHBFIN;FDHBFRBN;BOGZ1LM153061105Q;"
            "BOGZ1FL763061100Q;BOGZ1FL633061105Q;"
            "BOGZ1FL653061105Q;BOGZ1FL573061105Q;"
            "tic_foreign_treasury_stock_split;tic_treasury_sector_transactions;"
            "ofr_mmf_treasury_holdings;sec_nmfp_mmf_treasury_cusip_holdings;"
            "irs_interest_received_tax_topic_403;"
            "irs_publication_550_interest_income_taxonomy;"
            "irs_1099_int_div_reporting_taxonomy;"
            "fta_state_individual_income_tax_rates;"
            "cbo_capital_tax_rates"
        )
        and "PII:" in row["source_record_hash_summary"]
        and "NA000309Q:" in row["source_record_hash_summary"]
        and "irs_soi_taxable_interest:" in row["source_record_hash_summary"]
        and "irs_soi_ira_type_agi:" in row["source_record_hash_summary"]
        and "irs_soi_average_tax_rate_percentile:" in row["source_record_hash_summary"]
        and "fed_dfa_household_account_type_context:"
        in row["source_record_hash_summary"]
        and "fed_scf_2022_safe_asset_account_tax_context:"
        in row["source_record_hash_summary"]
        and "irs_estimated_tax_payment_timing:" in row["source_record_hash_summary"]
        and "irs_soi_state_interest_agi:" in row["source_record_hash_summary"]
        and "treasury_security_interest_tax_treatment:"
        in row["source_record_hash_summary"]
        and "FDHBPIN:" in row["source_record_hash_summary"]
        and "FDHBFIN:" in row["source_record_hash_summary"]
        and "FDHBFRBN:" in row["source_record_hash_summary"]
        and "BOGZ1LM153061105Q:" in row["source_record_hash_summary"]
        and "BOGZ1FL763061100Q:" in row["source_record_hash_summary"]
        and "BOGZ1FL633061105Q:" in row["source_record_hash_summary"]
        and "BOGZ1FL653061105Q:" in row["source_record_hash_summary"]
        and "BOGZ1FL573061105Q:" in row["source_record_hash_summary"]
        and "tic_foreign_treasury_stock_split:" in row["source_record_hash_summary"]
        and "tic_treasury_sector_transactions:" in row["source_record_hash_summary"]
        and "ofr_mmf_treasury_holdings:" in row["source_record_hash_summary"]
        and "sec_nmfp_mmf_treasury_cusip_holdings:" in row["source_record_hash_summary"]
        and "irs_interest_received_tax_topic_403:" in row["source_record_hash_summary"]
        and "irs_publication_550_interest_income_taxonomy:"
        in row["source_record_hash_summary"]
        and "irs_1099_int_div_reporting_taxonomy:" in row["source_record_hash_summary"]
        and "fta_state_individual_income_tax_rates:"
        in row["source_record_hash_summary"]
        and "cbo_capital_tax_rates:" in row["source_record_hash_summary"]
        and row["demand_conversion_evidence_status"]
        == "blocked_no_interest_income_tax_clawback_mapping_to_current_demand"
        and row["can_narrow_demand_conversion_prior"] == "false"
        for row in recipient_leakage_design_gate_rows
    )
    assert any(
        row["cashflow_component"] == "foreign_treasury_holder_leakage"
        and "FDHBFIN" in row["source_context_series_ids"]
        and row["demand_conversion_evidence_status"]
        == "blocked_no_foreign_holder_leakage_recycling_to_current_demand_bridge"
        and row["can_narrow_demand_conversion_prior"] == "false"
        for row in recipient_leakage_design_gate_rows
    )
    assert any(
        row["cashflow_component"] == "iorb"
        and "bank behavior" in row["exact_blocker"].lower()
        for row in recipient_leakage_design_gate_rows
    )
    assert {
        row["can_narrow_absorber_prior"] for row in public_finance_timing_bridge_rows
    } == {"false"}
    timing_movements = {
        row["source_context_gate_movement_this_tranche"]
        for row in public_finance_timing_bridge_rows
    }
    assert timing_movements >= {
        "admitted_mts_cbo_context_as_fiscal_timing_context_only",
        "admitted_wtregen_h41_mts_context_as_tga_timing_context_only",
    } or timing_movements >= {
        "admitted_mts_cbo_dts_tga_context_as_fiscal_timing_context_only",
        "admitted_wtregen_h41_mts_dts_tga_context_as_tga_timing_context_only",
    }
    assert any(
        row["timing_object"] == "tga_liquidity_offset"
        and (
            (
                row["missing_source_artifacts_for_gate"] == "treasury_dts"
                and row["netting_nonadditivity_context_status"]
                == "blocked_no_tga_financing_source_reserves_rrp_deposit_netting_test"
            )
            or (
                row["missing_source_artifacts_for_gate"] == "none"
                and row["netting_nonadditivity_context_status"]
                in {
                    "blocked_dts_tga_context_available_no_financing_source_reserves_rrp_deposit_netting_test",
                    "blocked_dts_wtregen_h41_context_reviewed_no_tga_financing_source_counterparty_split",
                }
            )
        )
        for row in public_finance_timing_bridge_rows
    )
    assert any(
        row["timing_object"] == "future_remittance_drag_demand_share_offset"
        and row["absorber_prior_evidence_status"]
        == "blocked_context_not_future_remittance_drag_current_share_evidence"
        for row in public_finance_timing_bridge_rows
    )
    assert {
        row["enters_main_offset_ratio"] for row in higher_rate_channel_registry_rows
    } == {"false"}
    assert {
        row["recipient_leakage_wrapper_channel"]
        for row in higher_rate_channel_registry_rows
        if row["channel_role"] == "recipient_leakage_wrapper"
    } == {"true"}
    assert {
        row["denominator_drag_channel"]
        for row in higher_rate_channel_registry_rows
        if row["channel_role"] == "denominator_drag"
    } == {"true"}
    assert {
        row["price_channel"]
        for row in higher_rate_channel_registry_rows
        if row["channel_role"] == "price_channel_sidecar"
    } == {"true"}
    assert any(
        row["channel_name"] == "interest_income_tax_clawback_leakage"
        and row["rough_calibration_range"] == "0.08/0.18/0.32"
        and row["tax_output_enabled"] == "false"
        for row in higher_rate_channel_registry_rows
    )
    assert any(
        row["channel_name"] == "foreign_treasury_holder_leakage"
        and row["rough_calibration_range"] == "0.15/0.25/0.35"
        and row["holder_allocation_enabled"] == "false"
        for row in higher_rate_channel_registry_rows
    )
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in higher_rate_channel_registry_rows
        + corporate_net_interest_cashflow_bridge_rows
        + working_capital_cost_channel_diagnostic_rows
        + term_structure_pricing_carry_diagnostic_rows
    } == {"false"}
    assert {
        row["cashflow_support_channel"]
        for row in working_capital_cost_channel_diagnostic_rows
        + term_structure_pricing_carry_diagnostic_rows
    } == {"false"}
    assert {
        row["pricing_output_enabled"]
        for row in higher_rate_channel_registry_rows
        + corporate_net_interest_cashflow_bridge_rows
        + working_capital_cost_channel_diagnostic_rows
        + term_structure_pricing_carry_diagnostic_rows
    } == {"false"}
    assert {
        row["corporate_cashflow_gate_passed"]
        for row in corporate_net_interest_cashflow_bridge_rows
    } == {"false"}
    assert {
        row["can_narrow_prior"] for row in corporate_net_interest_cashflow_bridge_rows
    } == {"false"}
    assert {
        row["source_admission_result"]
        for row in corporate_net_interest_cashflow_bridge_rows
    } <= {
        "blocked_after_qfr_compustat_official_artifact_review_no_admitted_"
        "fixed_floating_maturity_refinancing_overlap_snapshot",
        "qfr_aggregate_snapshot_admitted_gate_blocked_no_fixed_floating_"
        "or_firm_level_overlap",
    }
    treasury_repricing_recommendation = next(
        row
        for row in calibration_parameter_recommendation_rows
        if row["parameter"] == "treasury_repricing_speed_share"
    )
    assert treasury_repricing_recommendation["calibration_status"] == (
        "evidence_c_part2_literature_calibrated_assumption_mode"
    )
    assert treasury_repricing_recommendation["source_gate_table"] == (
        "ratewall_treasury_bucket_repricing_prior_bridge.csv"
    )
    assert treasury_repricing_recommendation["can_enter_main_ratio"] == "true"
    denominator_recommendation = next(
        row
        for row in calibration_parameter_recommendation_rows
        if row["parameter"] == "contractionary_drag_gdp_share"
    )
    assert denominator_recommendation["allowed_model_use"] == "sensitivity_only"
    assert denominator_recommendation["can_narrow_prior"] == "false"
    sf_fed_gdp_calibration_gate = next(
        row
        for row in denominator_calibration_design_gate_rows
        if row["gate_id"] == "denominator_calibration::sf_fed::real_gdp::4q"
    )
    assert sf_fed_gdp_calibration_gate["source_input_status"] == (
        "source_backed_shock_and_outcome_snapshots_available"
    )
    assert sf_fed_gdp_calibration_gate["cross_source_replication_input_status"] == (
        "baseline_source_available_not_cross_source_replication"
    )
    assert sf_fed_gdp_calibration_gate["shock_snapshot_source_id"] == "sf_fed"
    assert sf_fed_gdp_calibration_gate["outcome_source_id"] == "GDP"
    assert sf_fed_gdp_calibration_gate["outcome_snapshot_source_id"] == "fred"
    assert int(sf_fed_gdp_calibration_gate["matched_response_estimate_count"]) >= 0
    if sf_fed_gdp_calibration_gate["matched_response_estimate_available_count"] != "0":
        assert sf_fed_gdp_calibration_gate[
            "matched_response_estimate_diagnostic_id"
        ].startswith(
            "denominator_response_estimate_diagnostic::"
            "scalar_conventional_drag_amplitude"
        )
        assert sf_fed_gdp_calibration_gate["diagnostic_response_coefficient"]
        assert sf_fed_gdp_calibration_gate["diagnostic_response_standard_error"]
        assert sf_fed_gdp_calibration_gate["diagnostic_response_units"] == (
            "transformed_outcome_change_per_basis_points"
        )
        assert sf_fed_gdp_calibration_gate["unit_conversion_review_status"] == (
            "blocked_diagnostic_units_not_reviewed_gdp_share_per_100bp_year"
        )
        assert sf_fed_gdp_calibration_gate["unit_conversion_gate_decision"] == (
            "blocked_mechanical_mapping_only_not_admitted_denominator_conversion"
        )
        assert sf_fed_gdp_calibration_gate["formal_design_protocol_status"] == (
            "registered_fail_closed_lp_proxy_svar_path_integral_protocol_not_executed"
        )
        assert sf_fed_gdp_calibration_gate["formal_design_protocol_gate_decision"] == (
            "registered_fail_closed_protocol_blocked_missing_policy_path_and_"
            "gdp_response_path"
        )
        assert (
            "policy-path exposure vector"
            in sf_fed_gdp_calibration_gate["formal_design_protocol_gate_blocker"]
        )
        assert sf_fed_gdp_calibration_gate["retained_gdp_response_path_status"] == (
            "source_admitted_retained_gdp_response_paths_from_fred_snapshot_fail_closed"
        )
        assert (
            int(sf_fed_gdp_calibration_gate["retained_gdp_response_path_event_count"])
            > 0
        )
        assert sf_fed_gdp_calibration_gate["policy_path_exposure_vector_status"] == (
            "blocked_source_records_retain_event_shock_scalar_not_policy_path_"
            "exposure_vector"
        )
        assert (
            sf_fed_gdp_calibration_gate["policy_path_exposure_vector_source_status"]
            == "blocked_no_source_record_policy_path_exposure_vector"
        )
        assert (
            sf_fed_gdp_calibration_gate[
                "policy_path_exposure_vector_construction_method_status"
            ]
            == "blocked_no_registered_policy_path_vector_construction_method"
        )
        assert (
            "model assumption"
            in sf_fed_gdp_calibration_gate["policy_path_exposure_vector_method_blocker"]
        )
        assert sf_fed_gdp_calibration_gate["path_exposure_admission_decision"] == (
            "partial_source_admission_gdp_response_path_admitted_policy_path_"
            "exposure_vector_blocked"
        )
        assert (
            sf_fed_gdp_calibration_gate["policy_path_duration_normalization_status"]
            == "blocked_policy_path_duration_normalization_not_admitted"
        )
        assert (
            sf_fed_gdp_calibration_gate["gdp_loss_convention_review_status"]
            == "blocked_cumulative_or_average_gdp_loss_convention_not_admitted"
        )
        assert (
            "mechanical_candidate_only=max(0,-coefficient)"
            in (sf_fed_gdp_calibration_gate["mechanical_gdp_share_drag_formula"])
        )
        assert sf_fed_gdp_calibration_gate["uncertainty_review_status"] == (
            "blocked_diagnostic_ols_uncertainty_not_promotion_grade"
        )
        assert sf_fed_gdp_calibration_gate["unit_conversion_protocol_status"] == (
            "review_protocol_defined_execution_blocked_no_promotion_grade_conversion"
        )
        assert (
            "SF Fed basis-point surprise coefficient"
            in (sf_fed_gdp_calibration_gate["unit_conversion_protocol_required_inputs"])
        )
        assert sf_fed_gdp_calibration_gate["uncertainty_protocol_status"] == (
            "review_protocol_defined_execution_blocked_no_promotion_grade_uncertainty"
        )
        assert (
            "event-window clustered"
            in (sf_fed_gdp_calibration_gate["uncertainty_protocol_required_inputs"])
        )
        assert sf_fed_gdp_calibration_gate["executable_uncertainty_runner_status"] == (
            "fail_closed_hac_uncertainty_review_executed_not_promotion_grade"
        )
        assert sf_fed_gdp_calibration_gate["event_level_panel_retention_status"] == (
            "event_level_response_panel_materialized_nonpromotional"
        )
        assert (
            "HAC review executed"
            in sf_fed_gdp_calibration_gate["executable_runner_blocker"]
        )
        assert sf_fed_gdp_calibration_gate["executable_runner_next_action"] == (
            "review_unit_conversion_and_formal_local_projection_design_"
            "before_any_denominator_prior_narrowing"
        )
    assert sf_fed_gdp_calibration_gate["response_estimate_layer_status"] in {
        "diagnostic_response_estimate_available_not_promotion_grade",
        "blocked_matched_cell_without_available_estimate",
        "blocked_no_matched_response_estimate_cell",
    }
    assert sf_fed_gdp_calibration_gate["promotion_decision"] in {
        "blocked_diagnostic_estimate_available_not_promotion_grade",
        "blocked_matched_cell_without_available_response_estimate",
        "blocked_missing_source_or_matched_response_estimate",
    }
    assert sf_fed_gdp_calibration_gate["prior_narrowing_allowed"] == "false"
    assert sf_fed_gdp_calibration_gate["split_denominator_promotion_allowed"] == "false"
    assert sf_fed_gdp_calibration_gate["formula_replacement_allowed"] == "false"
    assert (
        sf_fed_gdp_calibration_gate["main_offset_ratio_changed_this_tranche"] == "false"
    )
    assert (
        "no reviewed conversion to GDP-share drag per 100bp-year"
        in sf_fed_gdp_calibration_gate["promotion_blocker"]
        or "no usable diagnostic response estimate is available"
        in sf_fed_gdp_calibration_gate["promotion_blocker"]
    )
    fed_brw_gdp_calibration_gate = next(
        row
        for row in denominator_calibration_design_gate_rows
        if row["gate_id"] == "denominator_calibration::fed_brw::real_gdp::4q"
    )
    assert fed_brw_gdp_calibration_gate["source_input_status"] == (
        "source_backed_shock_and_outcome_snapshots_available"
    )
    assert fed_brw_gdp_calibration_gate["candidate_source_file_status"] == (
        "admitted_federal_reserve_feds_brw_csv_snapshot_with_source_hash"
    )
    assert fed_brw_gdp_calibration_gate["cross_source_replication_input_status"] == (
        "admitted_fed_feds_brw_snapshot_fail_closed_for_response_estimate_review"
    )
    assert fed_brw_gdp_calibration_gate["parser_source_admission_status"] == (
        "admitted_existing_fed_feds_csv_adapter"
    )
    assert fed_brw_gdp_calibration_gate["candidate_unit_review_status"] == (
        "admitted_percentage_point_shock_units_for_fail_closed_diagnostic_alignment"
    )
    assert fed_brw_gdp_calibration_gate["shock_snapshot_source_id"] == ("fed_feds")
    assert int(fed_brw_gdp_calibration_gate["shock_observation_count"]) > 0
    if fed_brw_gdp_calibration_gate["matched_response_estimate_available_count"] != "0":
        assert fed_brw_gdp_calibration_gate[
            "matched_response_estimate_diagnostic_id"
        ] == (
            "denominator_response_estimate_diagnostic::"
            "scalar_conventional_drag_amplitude::1y::"
            "fed_brw_monetary_policy_shocks::GDP"
        )
        assert fed_brw_gdp_calibration_gate["diagnostic_response_units"] == (
            "transformed_outcome_change_per_percentage_points"
        )
        assert fed_brw_gdp_calibration_gate["unit_conversion_review_status"] == (
            "blocked_diagnostic_units_not_reviewed_gdp_share_per_100bp_year"
        )
        assert fed_brw_gdp_calibration_gate["unit_conversion_gate_decision"] == (
            "blocked_mechanical_mapping_only_not_admitted_denominator_conversion"
        )
        assert fed_brw_gdp_calibration_gate["formal_design_protocol_gate_decision"] == (
            "registered_fail_closed_protocol_blocked_missing_policy_path_and_"
            "gdp_response_path"
        )
        assert fed_brw_gdp_calibration_gate["retained_gdp_response_path_status"] == (
            "source_admitted_retained_gdp_response_paths_from_fred_snapshot_fail_closed"
        )
        assert fed_brw_gdp_calibration_gate["policy_path_exposure_vector_status"] == (
            "blocked_source_records_retain_event_shock_scalar_not_policy_path_"
            "exposure_vector"
        )
        assert (
            fed_brw_gdp_calibration_gate["policy_path_exposure_vector_source_status"]
            == "blocked_no_source_record_policy_path_exposure_vector"
        )
        assert (
            fed_brw_gdp_calibration_gate[
                "policy_path_exposure_vector_construction_method_status"
            ]
            == "blocked_no_registered_policy_path_vector_construction_method"
        )
        assert (
            "max(0,-coefficient/100)"
            in (fed_brw_gdp_calibration_gate["mechanical_gdp_share_drag_formula"])
        )
        assert (
            fed_brw_gdp_calibration_gate["shock_unit_conversion_review_status"]
            == "reviewed_mechanical_percentage_point_to_basis_point_shock_unit"
        )
        assert fed_brw_gdp_calibration_gate["uncertainty_review_status"] == (
            "blocked_diagnostic_ols_uncertainty_not_promotion_grade"
        )
        assert fed_brw_gdp_calibration_gate["unit_conversion_protocol_status"] == (
            "review_protocol_defined_execution_blocked_no_promotion_grade_conversion"
        )
        assert (
            "convert FEDS/BRW percentage-point shock units"
            in (
                fed_brw_gdp_calibration_gate["unit_conversion_protocol_required_inputs"]
            )
        )
        assert (
            "monthly/FOMC alignment"
            in (fed_brw_gdp_calibration_gate["uncertainty_protocol_required_inputs"])
        )
        assert fed_brw_gdp_calibration_gate["executable_uncertainty_runner_status"] == (
            "fail_closed_hac_uncertainty_review_executed_not_promotion_grade"
        )
        assert fed_brw_gdp_calibration_gate["executable_pass_fail_runner_status"] == (
            "fail_closed_pass_fail_review_executed_promotion_blocked"
        )
    assert fed_brw_gdp_calibration_gate["promotion_decision"] in {
        "blocked_diagnostic_estimate_available_not_promotion_grade",
        "blocked_matched_cell_without_available_response_estimate",
        "blocked_missing_source_or_matched_response_estimate",
    }
    assert fed_brw_gdp_calibration_gate["prior_narrowing_allowed"] == "false"
    assert (
        fed_brw_gdp_calibration_gate["split_denominator_promotion_allowed"] == "false"
    )
    assert fed_brw_gdp_calibration_gate["formula_replacement_allowed"] == "false"
    assert (
        fed_brw_gdp_calibration_gate["main_offset_ratio_changed_this_tranche"]
        == "false"
    )
    fed_brw_ip_calibration_gate = next(
        row
        for row in denominator_calibration_design_gate_rows
        if row["gate_id"]
        == "denominator_calibration::fed_brw::industrial_production::4q"
    )
    assert fed_brw_ip_calibration_gate["source_input_status"] == (
        "source_backed_shock_and_outcome_snapshots_available"
    )
    assert fed_brw_ip_calibration_gate["outcome_source_id"] == "INDPRO"
    assert int(fed_brw_ip_calibration_gate["matched_response_estimate_count"]) >= 0
    romer_calibration_gate = next(
        row
        for row in denominator_calibration_design_gate_rows
        if row["gate_id"] == "denominator_calibration::romer_romer::real_gdp::8q"
    )
    if (
        romer_calibration_gate["source_input_status"]
        == "blocked_missing_shock_snapshot"
    ):
        assert romer_calibration_gate["candidate_source_file_status"] == (
            "candidate_berkeley_xls_identified_but_not_registered_as_"
            "current_snapshot_source_or_parsed"
        )
        assert romer_calibration_gate["cross_source_replication_input_status"] == (
            "blocked_candidate_source_file_not_harmonized_into_snapshot"
        )
        assert (
            romer_calibration_gate["matched_response_estimate_available_count"] == "0"
        )
        assert romer_calibration_gate["promotion_decision"] == (
            "blocked_missing_source_or_matched_response_estimate"
        )
    else:
        assert romer_calibration_gate["source_input_status"] == (
            "source_backed_shock_and_outcome_snapshots_available"
        )
        assert romer_calibration_gate["candidate_source_file_status"] == (
            "admitted_converted_csv_snapshot_from_berkeley_xls_with_source_hash"
        )
        assert romer_calibration_gate["cross_source_replication_input_status"] == (
            "admitted_converted_csv_snapshot_fail_closed_for_response_estimate_review"
        )
        assert romer_calibration_gate["parser_source_admission_status"] == (
            "admitted_reviewed_converted_csv_snapshot_not_runtime_xls_parser"
        )
        assert romer_calibration_gate["parser_runtime_status"] == (
            "admitted_backend_uses_materialized_csv_snapshot_no_runtime_"
            "legacy_xls_parser_required"
        )
        assert romer_calibration_gate["candidate_schema_review_status"] == (
            "admitted_date_resid_monthly_schema_and_mtgdate_resid_"
            "meeting_schema_documented"
        )
        assert romer_calibration_gate["snapshot_admission_status"] == (
            "admitted_converted_csv_source_snapshot_fail_closed"
        )
        assert (
            "fail-closed response-estimate review"
            in romer_calibration_gate["cross_source_replication_blocker"]
        )
        if romer_calibration_gate["matched_response_estimate_available_count"] == "0":
            assert romer_calibration_gate["promotion_decision"] in {
                "blocked_missing_source_or_matched_response_estimate",
                "blocked_matched_cell_without_available_response_estimate",
            }
        else:
            assert (
                romer_calibration_gate["matched_response_estimate_available_count"] == "1"
            )
            assert romer_calibration_gate["matched_response_estimate_diagnostic_id"] == (
                "denominator_response_estimate_diagnostic::"
                "scalar_conventional_drag_amplitude::8q::romer_romer_2004::GDP"
            )
            assert romer_calibration_gate["diagnostic_response_units"] == (
                "annualized_gdp_percent_change_per_basis_points"
            )
            assert romer_calibration_gate["unit_conversion_review_status"] == (
                "blocked_rr_gdp_8q_not_reviewed_gdp_share_per_100bp_year"
            )
            assert romer_calibration_gate["unit_conversion_gate_decision"] == (
                "blocked_rr_endpoint_gdp_mapping_not_admitted_100bp_year_conversion"
            )
            assert romer_calibration_gate["formal_design_protocol_gate_decision"] == (
                "registered_fail_closed_protocol_blocked_endpoint_8q_not_path_integral"
            )
            assert romer_calibration_gate["retained_gdp_response_path_status"] == (
                "source_admitted_retained_gdp_response_paths_from_fred_snapshot_fail_closed"
            )
            assert romer_calibration_gate["path_exposure_admission_decision"] == (
                "partial_source_admission_gdp_response_path_admitted_policy_path_"
                "exposure_vector_blocked"
            )
            assert (
                romer_calibration_gate["policy_path_exposure_vector_source_status"]
                == "blocked_no_source_record_policy_path_exposure_vector"
            )
            assert (
                romer_calibration_gate[
                    "policy_path_exposure_vector_construction_method_status"
                ]
                == "blocked_no_registered_policy_path_vector_construction_method"
            )
            assert (
                "endpoint 8q annualized response"
                in romer_calibration_gate["formal_design_protocol_gate_blocker"]
            )
            assert (
                "cumulative-or-average GDP-loss convention"
                in (romer_calibration_gate["unit_conversion_gate_blocker"])
            )
            assert romer_calibration_gate["uncertainty_review_status"] == (
                "blocked_rr_classical_ols_uncertainty_not_promotion_grade"
            )
            assert romer_calibration_gate["confidence_interval_review_status"] == (
                "blocked_rr_no_promotion_grade_confidence_interval"
            )
            assert romer_calibration_gate["p_value_review_status"] == (
                "blocked_rr_no_promotion_grade_p_value"
            )
            assert romer_calibration_gate["unit_conversion_protocol_status"] == (
                "review_protocol_defined_execution_blocked_no_promotion_grade_conversion"
            )
            assert (
                "cumulative or average GDP-loss"
                in romer_calibration_gate["unit_conversion_protocol_required_inputs"]
            )
            assert (
                "overlapping monthly RR events"
                in romer_calibration_gate["uncertainty_protocol_required_inputs"]
            )
            assert romer_calibration_gate["pass_fail_review_protocol_status"] == (
                "review_protocol_defined_execution_blocked_missing_formal_pass_"
                "fail_diagnostics"
            )
            assert romer_calibration_gate["residual_design_retention_status"] == (
                "event_level_design_and_residual_summary_retained_fail_closed_"
                "not_full_lp_design"
            )
            assert romer_calibration_gate["executable_uncertainty_runner_status"] == (
                "fail_closed_hac_uncertainty_review_executed_not_promotion_grade"
            )
            assert (
                "HAC review executed"
                in romer_calibration_gate["executable_runner_blocker"]
            )
            assert romer_calibration_gate["promotion_decision"] == (
                "blocked_diagnostic_estimate_available_not_promotion_grade"
            )
    assert romer_calibration_gate["prior_narrowing_allowed"] == "false"
    assert romer_calibration_gate["split_denominator_promotion_allowed"] == "false"
    assert romer_calibration_gate["formula_replacement_allowed"] == "false"
    assert romer_calibration_gate["main_offset_ratio_changed_this_tranche"] == "false"
    gss_calibration_gate = next(
        row
        for row in denominator_calibration_design_gate_rows
        if row["gate_id"]
        == "denominator_calibration::gss_target_path::real_final_sales::4q"
    )
    assert gss_calibration_gate["candidate_source_file_status"] == (
        "reviewed_sf_fed_bauer_swanson_workbook_available_not_gss_"
        "target_path_factor_snapshot"
    )
    assert gss_calibration_gate["cross_source_replication_input_status"] == (
        "blocked_no_reviewed_gss_target_path_factor_snapshot_or_construction_pipeline"
    )
    assert gss_calibration_gate["parser_source_admission_status"] == (
        "blocked_source_is_bauer_swanson_mps_not_gss_target_path"
    )
    assert gss_calibration_gate["snapshot_admission_status"] == (
        "blocked_no_admitted_gss_target_path_factor_snapshot_or_construction_pipeline"
    )
    assert (
        "Bauer-Swanson monetary-policy-surprises workbook"
        in (gss_calibration_gate["cross_source_replication_blocker"])
    )
    assert "MPS_ORTH" in gss_calibration_gate["cross_source_replication_blocker"]
    assert gss_calibration_gate["unit_conversion_protocol_status"] == (
        "blocked_no_matched_response_estimate_cell_for_protocol_review"
    )
    assert gss_calibration_gate["uncertainty_protocol_status"] == (
        "blocked_no_matched_response_estimate_cell_for_uncertainty_protocol"
    )
    assert gss_calibration_gate["executable_uncertainty_runner_status"] == (
        "blocked_no_matched_response_cell_for_hac_bootstrap_or_lp"
    )
    assert gss_calibration_gate["executable_runner_next_action"] == (
        "admit_or_construct_matched_event_level_denominator_panel_"
        "before_executable_uncertainty_review"
    )
    for disabled_field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {
            row[disabled_field] for row in calibration_parameter_recommendation_rows
        } == {"false"}
        assert {
            row[disabled_field] for row in denominator_calibration_design_gate_rows
        } == {"false"}
        assert {row[disabled_field] for row in recipient_leakage_design_gate_rows} == {
            "false"
        }
        assert {row[disabled_field] for row in public_finance_timing_bridge_rows} == {
            "false"
        }
    assert len(dynamic_scenario_path_rows) == 176
    assert len(dynamic_scenario_path_consistency_rows) == 176
    assert len(dynamic_offset_ratio_path_rows) == 176
    assert len(scenario_crossing_diagnostic_rows) == 11
    assert len(dynamic_sensitivity_frontier_rows) == 33
    assert len(dynamic_scenario_family_registry_rows) == 11
    assert len(dynamic_uncertainty_envelope_rows) == 160
    assert len(dynamic_crossing_robustness_rows) == 11
    assert {
        "baseline_debt_liquidity_glide",
        "high_debt_liquidity_drift_to_wall",
        "tdc_liquidity_boost_boundary_case",
        "high_debt_near_wall_no_crossing",
        "high_denominator_drag_non_crossing",
        "fiscal_tga_remittance_absorption_stress",
        "safe_yield_drag_dominant_case",
        "research_calibrated_conservative_no_hit",
        "research_calibrated_high_debt_near_wall",
        "research_calibrated_attenuated_hit_candidate",
        "research_calibrated_upper_bound_stress",
    } == {row["scenario_id"] for row in scenario_crossing_diagnostic_rows}
    crossing_rows = [
        row
        for row in scenario_crossing_diagnostic_rows
        if row["crossing_status"] == "scenario_implied_crossing_under_assumptions"
    ]
    assert all(
        row["crossing_is_empirical_threshold_date"] == "false"
        and "not an empirical threshold date" in row["scenario_implied_crossing_label"]
        and row["evaluation_horizon"]
        and row["crossing_semantics"]
        == "period_indexed_state_crossing_on_static_evaluation_horizon_"
        "not_realized_quarter_flow_threshold"
        for row in crossing_rows
    )
    assert all(
        row["crossing_status"]
        in {
            "scenario_implied_crossing_under_assumptions",
            "no_crossing_in_configured_horizon",
        }
        for row in scenario_crossing_diagnostic_rows
    )
    assert {
        row["static_main_offset_ratio_changed"] for row in dynamic_scenario_path_rows
    } == {"false"}
    assert {
        row["prior_narrowing_allowed"] for row in dynamic_scenario_path_consistency_rows
    } == {"false"}
    assert {
        row["formula_replacement_allowed"]
        for row in dynamic_scenario_path_consistency_rows
    } == {"false"}
    assert {
        row["static_main_offset_ratio_changed"]
        for row in dynamic_scenario_path_consistency_rows
    } == {"false"}
    assert {
        row["growth_path_consistency_status"]
        for row in dynamic_scenario_path_consistency_rows
    } <= {
        "growth_implied_path_matches_configured_debt_and_liquidity",
        "scenario_override_path_not_mechanically_growth_implied",
    }
    assert {
        row["static_main_offset_ratio_changed"]
        for row in dynamic_offset_ratio_path_rows
    } == {"false"}
    assert {row["claim_boundary"] for row in dynamic_scenario_path_rows} == {
        "dynamic_assumption_mode_scenario_implied_not_empirical_threshold_date"
    }
    assert {row["tdc_effect_role"] for row in dynamic_scenario_path_rows} == {
        "liquidity_deposit_state_scenario_input_not_incidence_or_mpc"
    }
    assert "tdc_deposit_pass_through_share" not in assumption_rows[0]
    assert {
        row["tdc_deposit_pass_through_source_project"]
        for row in dynamic_scenario_path_rows
    } == {"ratewall-evidence-b"}
    assert {
        row["tdc_deposit_pass_through_gate_status"]
        for row in dynamic_scenario_path_rows
    } == {"evidence_b_import_contract_normal_forward_h0_default"}
    assert {
        row["tdc_deposit_pass_through_admission_scope"]
        for row in dynamic_scenario_path_rows
    } == {"pass_source_backed_import_contract_scenario_only"}
    assert {
        row["tdc_deposit_pass_through_source_import_row_id"]
        for row in dynamic_scenario_path_rows
    } == {"evidence_b_import_contract_normal_forward_h0"}
    assert {
        row["tdc_deposit_pass_through_regime_scenario_id"]
        for row in dynamic_scenario_path_rows
    } == {"normal_forward"}
    assert all(
        0.3 <= float(row["tdc_deposit_pass_through_share"]) <= 0.35
        for row in dynamic_scenario_path_rows
    )
    assert all(
        row["tdc_deposit_pass_through_source_project"] == "ratewall-evidence-b"
        and row["tdc_deposit_pass_through_gate_status"]
        == "evidence_b_import_contract_normal_forward_h0_default"
        and row["state_period_frequency"] == "quarterly"
        and row["evaluation_horizon"]
        and row["crossing_semantics"]
        == "period_indexed_state_crossing_on_static_evaluation_horizon_"
        "not_realized_quarter_flow_threshold"
        for row in dynamic_offset_ratio_path_rows
    )
    assert all(
        float(row["tdc_adjusted_safe_asset_allocation_offset_share"])
        >= float(row["base_safe_asset_allocation_offset_share"])
        and float(row["tdc_liquidity_effect_offset_bil"]) >= 0
        for row in dynamic_offset_ratio_path_rows
    )
    tdc_scenario_ids = {
        row["scenario_id"]
        for row in dynamic_scenario_path_rows
        if row["tdc_effect_enabled"] == "true"
    }
    assert {
        "tdc_liquidity_boost_boundary_case",
        "research_calibrated_attenuated_hit_candidate",
        "research_calibrated_upper_bound_stress",
    } <= tdc_scenario_ids
    tdc_path_rows = [
        row
        for row in dynamic_scenario_path_rows
        if row["scenario_id"] in tdc_scenario_ids
    ]
    non_tdc_path_rows = [
        row
        for row in dynamic_scenario_path_rows
        if row["scenario_id"] not in tdc_scenario_ids
    ]
    assert any(float(row["tdc_liquidity_effect_share"]) > 0 for row in tdc_path_rows)
    assert all(
        float(row["tdc_liquidity_effect_share"]) == 0
        and float(row["tdc_liquidity_state_input_share"]) == 0
        for row in non_tdc_path_rows
    )
    assert all(
        abs(
            float(row["tdc_liquidity_effect_share"])
            - (
                float(row["tdc_liquidity_state_input_share"])
                * float(row["tdc_deposit_pass_through_share"])
            )
        )
        < 1e-12
        for row in tdc_path_rows
    )
    assert {
        row["main_classifier_status"] for row in dynamic_scenario_family_registry_rows
    } == {"static_assumption_mode_v1_ratio_remains_main_classifier"}
    assert {
        row["prior_narrowing_allowed"] for row in dynamic_uncertainty_envelope_rows
    } == {"false"}
    assert {
        row["formula_replacement_allowed"] for row in dynamic_uncertainty_envelope_rows
    } == {"false"}
    assert {
        row["crossing_is_empirical_threshold_date"]
        for row in dynamic_crossing_robustness_rows
    } == {"false"}
    assert {row["uncertainty_handle"] for row in dynamic_uncertainty_envelope_rows} == {
        "public_debt_stock_scale",
        "rate_path_bps_year",
        "treasury_recipient_conversion",
        "fiscal_tga_absorbers",
        "contractionary_drag",
        "safe_yield_offset_drag_pair",
        "tdc_liquidity_state_input",
        "tdc_deposit_pass_through_share_source_envelope",
    }
    tdc_source_envelope_rows = [
        row
        for row in dynamic_uncertainty_envelope_rows
        if row["uncertainty_handle"]
        == "tdc_deposit_pass_through_share_source_envelope"
    ]
    assert len(tdc_source_envelope_rows) == 6
    assert {row["scenario_id"] for row in tdc_source_envelope_rows} == {
        "tdc_liquidity_boost_boundary_case",
        "research_calibrated_attenuated_hit_candidate",
        "research_calibrated_upper_bound_stress",
    }
    assert {
        row["tdc_deposit_pass_through_variant_source_import_row_id"]
        for row in tdc_source_envelope_rows
    } == {
        "ea_tdc_paper_matched_total_deposits_h0",
        "ea_tdc_latest_rolling_matched_total_deposits_h0",
    }
    assert all(
        not row["tdc_deposit_pass_through_variant_source_import_row_id"].startswith(
            "ea_tdc_pandemic_exclusion_"
        )
        for row in tdc_source_envelope_rows
    )
    assert all(
        row["changed_path_parameters"]
        == "tdc_deposit_pass_through_share;tdc_liquidity_effect_share"
        and row["allowed_use"]
        == "tdc_deposit_pass_through_dynamic_uncertainty_envelope_review_only"
        and "runtime_selector" in row["blocked_use"]
        and row["scenario_default_allowed"] == "false"
        and row["runtime_scenario_selection_allowed"] == "false"
        and row["trigger_threshold_promotion_allowed"] == "false"
        for row in tdc_source_envelope_rows
    )
    for row in tdc_source_envelope_rows:
        state_input = (
            Decimal(row["tdc_base_liquidity_effect_share"])
            / Decimal(row["tdc_base_deposit_pass_through_share"])
        )
        assert Decimal(row["tdc_variant_liquidity_effect_share"]) == (
            state_input * Decimal(row["tdc_variant_deposit_pass_through_share"])
        )
        assert Decimal(row["tdc_liquidity_effect_delta_share"]) == (
            Decimal(row["tdc_variant_liquidity_effect_share"])
            - Decimal(row["tdc_base_liquidity_effect_share"])
        )
    assert len(tdc_materialization_semantic_summary_rows) == 6
    assert {
        row["coefficient_semantic_label"]
        for row in tdc_materialization_semantic_summary_rows
    } == {"tdc_to_total_deposits_net_materialization_coefficient"}
    assert {
        row["semantic_status"] for row in tdc_materialization_semantic_summary_rows
    } == {"review_only_tdc_materialization_not_fed_rate_deposit_pricing"}
    for row in tdc_materialization_semantic_summary_rows:
        variant_coefficient = Decimal(row["variant_tdc_materialization_coefficient"])
        tdc_input = Decimal(row["tdc_liquidity_state_input_share"])
        assert Decimal(
            row["variant_implied_non_tdc_deposit_offset_share_per_1_tdc"]
        ) == (Decimal("1") - variant_coefficient)
        assert Decimal(
            row["variant_net_materialized_deposit_liquidity_effect_share"]
        ) == (tdc_input * variant_coefficient)
        assert row["pricing_output_enabled"] == "false"
        assert row["allowed_use"] == "tdc_materialization_semantic_review_only"
    assert {row["frontier_parameter"] for row in dynamic_sensitivity_frontier_rows} == {
        "countervailing_total_multiplier",
        "conventional_drag_multiplier",
        "tdc_liquidity_effect_share",
    }
    dynamic_report = artifacts.ratewall_dynamic_assumption_mode_equations.read_text(
        encoding="utf-8"
    )
    assert "RateWall Dynamic Assumption Mode Equations" in dynamic_report
    assert "not an empirical threshold-date estimate" in dynamic_report
    assert "Dynamic uncertainty envelope" in dynamic_report
    assert "TdcDepositPassThroughShare" in dynamic_report
    assert "does not enter the static main offset ratio" in dynamic_report
    assert "compares source-backed EA-TDC pass-through variants for review only" in (
        dynamic_report
    )
    assert "net materialization coefficient" in dynamic_report
    assert "not a Fed-rate-to-deposit-pricing pass-through estimate" in dynamic_report
    assert "do not select liquidity regimes" in dynamic_report
    assert {
        "public_liability_repricing_ladder",
        "treasury_fed_recipient_leakage_bridge",
        "fiscal_tga_remittance_timing_path",
        "conventional_drag_denominator_evidence_matrix",
        "firm_cash_debt_maturity_heterogeneity",
        "corporate_net_interest_cashflow_bridge",
        "working_capital_cost_pass_through",
        "term_structure_pricing_carry",
        "household_yield_optimization_financialized_balance_sheet",
        "safe_yield_offset_drag_pairing",
        "bnpl_zero_interest_float",
        "equity_transmission_attenuation",
        "horizon_timing_layer",
    } == {row["module_name"] for row in module_registry_rows}
    for rows in (
        repricing_ladder_rows,
        repricing_evidence_bridge_rows,
        repricing_reconciliation_gap_rows,
        recipient_bridge_rows,
        recipient_evidence_gap_rows,
        treasury_recipient_source_gate_rows,
        finance_timing_rows,
        finance_timing_evidence_gap_rows,
        finance_timing_design_test_rows,
        safe_yield_pairing_gap_rows,
        bnpl_float_gap_rows,
        financialized_gap_rows,
        firm_gap_rows,
        conventional_drag_gap_rows,
        conventional_drag_source_design_gate_rows,
        denominator_response_design_rows,
        denominator_response_design_test_rows,
        denominator_response_gate_attempt_rows,
        denominator_aligned_response_panel_scaffold_rows,
        denominator_event_outcome_cell_diagnostic_rows,
        horizon_timing_rows,
        promotion_gate_rows,
        high_priority_source_bridge_rows,
        source_gate_decision_rows,
        mspd_table3_bucket_gate_rows,
        dynamic_scenario_path_rows,
        dynamic_offset_ratio_path_rows,
        scenario_crossing_diagnostic_rows,
        dynamic_sensitivity_frontier_rows,
        dynamic_scenario_family_registry_rows,
        dynamic_uncertainty_envelope_rows,
        dynamic_crossing_robustness_rows,
        module_registry_rows,
    ):
        assert rows
        assert all(row["source_status"] for row in rows)
        assert all(row["evidence_needed"] for row in rows)
        assert all(row["promotion_gate"] for row in rows)
        for disabled_field in (
            "empirical_claim_enabled",
            "policy_failure_claim_enabled",
            "pricing_output_enabled",
            "incidence_claim_enabled",
            "welfare_claim_enabled",
            "tax_output_enabled",
            "mpc_output_enabled",
            "holder_allocation_enabled",
            "reset_calendar_construction_enabled",
            "raw_rate_shock_enabled",
            "causal_financialization_claim_enabled",
        ):
            assert {row[disabled_field] for row in rows} == {"false"}
    assert {row["channel_module"] for row in channel_completion_matrix_rows} == {
        row["module_name"] for row in module_registry_rows
    }
    assert {row["claim_boundary"] for row in channel_completion_matrix_rows} == {
        "interest_channel_completion_matrix_not_empirical_promotion"
    }
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in channel_completion_matrix_rows
    } == {"false"}
    assert {
        row["empirical_promotion_status"] for row in channel_completion_matrix_rows
    } == {"blocked_source_gated_no_empirical_promotion"}
    assert any(
        row["channel_module"] == "conventional_drag_denominator_evidence_matrix"
        and row["v1_completion_status"]
        == "assumption_mode_v1_complete_denominator_evidence_blocked"
        and "support-count cells" in row["current_blocker"]
        for row in channel_completion_matrix_rows
    )
    for disabled_field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[disabled_field] for row in channel_completion_matrix_rows} == {
            "false"
        }
    assert {
        "public_liability_repricing_ladder",
        "treasury_fed_recipient_leakage_bridge",
        "conventional_drag_denominator_evidence_matrix",
        "fiscal_tga_remittance_timing_path",
    } <= {row["channel_module"] for row in high_priority_source_bridge_rows}
    assert {
        "treasury_mspd_table_3",
        "fed_brw_monetary_policy_shocks",
        "mts_table_4",
    } <= {row["source_id"] for row in high_priority_source_bridge_rows}
    assert any(
        row["source_status"]
        in {"fallback_stub_review_not_promotion", "demo_stub_review_not_promotion"}
        for row in high_priority_source_bridge_rows
    )
    assert all(
        row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["empirical_claim_enabled"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["incidence_claim_enabled"] == "false"
        and row["holder_allocation_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in high_priority_source_bridge_rows
    )
    assert all(
        row["source_id"]
        and row["source_artifact"]
        and row["exact_source_table_or_series"]
        and row["exact_design_handle"]
        and row["missing_evidence"]
        and row["promotion_gate"]
        and row["promotion_readiness"].startswith("blocked_")
        for row in high_priority_source_bridge_rows
    )
    assert {
        "ea-tdc",
        "tdcest",
        "tdcpass",
        "tdc-hf",
        "tdcsfc",
        "tgarefill",
        "tdcladder",
        "buycurve",
        "tsyparty",
        "rowflow",
        "liqsub",
        "bankcap",
        "regcap",
    } <= {row["sibling_project"] for row in sibling_evidence_bridge_rows}
    assert {
        "tdc_deposit_pass_through_liquidity_state",
        "tdc_liquidity_state_dynamic_input",
        "treasury_fed_recipient_leakage_bridge",
        "conventional_drag_denominator_evidence_matrix",
        "fiscal_tga_remittance_timing_path",
    } <= {row["ratewall_channel"] for row in sibling_evidence_bridge_rows}
    assert all(
        (
            row["can_narrow_prior"] == "false"
            or (
                row["sibling_project"] == "ea-tdc"
                and row["ratewall_channel"]
                == "tdc_deposit_pass_through_liquidity_state"
                and row["candidate_prior_handle"] == "tdc_deposit_pass_through_share"
                and row["coefficient_admission_scope"]
                == "source_backed_tdc_deposit_pass_through_liquidity_state_only"
            )
        )
        and row["can_replace_formula_handle"] == "false"
        and row["can_enter_main_ratio"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["source_gate_attempted_this_tranche"] in {"true", "false"}
        and row["runtime_prior_narrowing_allowed"] == "false"
        and row["canonical_denominator_prior_update_allowed"] == "false"
        and row["empirical_claim_enabled"] == "false"
        and row["incidence_claim_enabled"] == "false"
        and row["mpc_output_enabled"] == "false"
        and row["holder_allocation_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in sibling_evidence_bridge_rows + sibling_evidence_upgrade_queue_rows
    )
    if any(row["artifact_exists"] == "true" for row in sibling_evidence_bridge_rows):
        ea_tdc_rows = [
            row
            for row in sibling_evidence_bridge_rows
            if row["sibling_project"] == "ea-tdc"
            and row["ratewall_channel"] == "tdc_deposit_pass_through_liquidity_state"
        ]
        assert len(ea_tdc_rows) == 1
        ea_tdc_row = ea_tdc_rows[0]
        assert (
            ea_tdc_row["source_gate_attempt_result"]
            == "source_gate_passed_tdc_deposit_pass_through_liquidity_state_only"
        )
        assert ea_tdc_row["candidate_prior_handle"] == "tdc_deposit_pass_through_share"
        assert ea_tdc_row["can_narrow_prior"] == "true"
        assert ea_tdc_row["can_source_bind_dynamic_pass_through_handle"] == "true"
        assert ea_tdc_row["runtime_prior_narrowing_allowed"] == "false"
        assert ea_tdc_row["canonical_denominator_prior_update_allowed"] == "false"
        assert ea_tdc_row["can_replace_formula_handle"] == "false"
        assert ea_tdc_row["can_enter_main_ratio"] == "false"
        assert ea_tdc_row["main_offset_ratio_changed_this_tranche"] == "false"
        assert ea_tdc_row["coefficient_units"] == "dollars_per_dollar_tdc"
        assert 0.5 <= float(ea_tdc_row["admitted_coefficient_base"]) <= 0.7
        assert "2002Q1 to 2025Q4" in ea_tdc_row["source_vintage_or_sample"]
        assert (
            "not identify Treasury interest recipient demand conversion"
            in (ea_tdc_row["exact_blocker_if_blocked"])
        )
        assert any(
            row["sibling_project"] == "tdcpass"
            and row["ratewall_channel"] == "tdc_deposit_pass_through_legacy_comparison"
            and row["current_admission_status"]
            == "legacy_context_only_demoted_by_ea_tdc"
            and row["can_narrow_prior"] == "false"
            and row["source_gate_attempt_result"]
            == "demoted_legacy_context_only_canonical_source_is_ea_tdc"
            for row in sibling_evidence_bridge_rows
        )
        assert any(
            row["sibling_project"] == "tdcest"
            and row["ratewall_channel"] == "public_liability_repricing_ladder"
            and row["source_status_upgrade_allowed"] == "true"
            and row["source_gate_attempt_result"]
            == "source_status_upgraded_to_component_pool_context_only"
            and "component pools" in row["exact_source_method_blocker_after_attempt"]
            and row["can_narrow_prior"] == "false"
            and row["can_replace_formula_handle"] == "false"
            for row in sibling_evidence_bridge_rows
        )
        assert any(
            row["sibling_project"] == "bankcap"
            and row["ratewall_channel"]
            == "conventional_drag_denominator_evidence_matrix"
            and row["source_status_upgrade_allowed"] == "false"
            and row["source_gate_attempt_result"]
            == "blocked_bank_regime_context_not_shock_identified_credit_response"
            for row in sibling_evidence_bridge_rows
        )
        assert any(
            row["sibling_project"] == "tsyparty"
            and row["ratewall_channel"] == "treasury_fed_recipient_leakage_bridge"
            and "cannot narrow treasury_interest_demand_share"
            in row["exact_promotion_gate"]
            and row["source_gate_attempt_result"]
            == "blocked_holder_context_not_demand_conversion_or_allocation_gate"
            for row in sibling_evidence_bridge_rows
        )
    else:
        assert {
            row["source_gate_attempt_result"] for row in sibling_evidence_bridge_rows
        } == {"blocked_sibling_artifact_missing"}
    assert any(
        row["sibling_project"] == "tdcest"
        and row["ratewall_channel"] == "tdc_liquidity_state_dynamic_input"
        and "not identify recipient spending" in row["exact_blocker_if_blocked"]
        for row in sibling_evidence_bridge_rows
    )
    assert {
        "public_liability_repricing_ladder",
        "treasury_fed_recipient_leakage_bridge",
        "conventional_drag_denominator_evidence_matrix",
        "fiscal_tga_remittance_timing_path",
    } <= {row["channel_module"] for row in source_gate_decision_rows}
    assert all(
        row["bridge_eligible_now"] == "false"
        for row in source_gate_decision_rows
        if row["channel_module"] != "public_liability_repricing_ladder"
    )
    assert all(
        row["promotion_gate_passed"] == "false"
        for row in source_gate_decision_rows
        if row["channel_module"] != "public_liability_repricing_ladder"
    )
    assert all(
        row["prior_narrowing_allowed"] == "false"
        for row in source_gate_decision_rows
        if row["channel_module"] != "public_liability_repricing_ladder"
    )
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in source_gate_decision_rows
    } == {"false"}
    assert {row["claim_boundary"] for row in source_gate_decision_rows} == {
        "source_gate_prior_narrowing_decision_not_promotion"
    }
    assert {row["gate_id"] for row in source_gate_exhaustion_closure_rows} == {
        "cre_refinancing_denominator_promotion_gate",
        "ndfi_private_credit_promotion_gate",
        "consumer_credit_denominator_promotion_gate",
        "interest_income_tax_clawback_wrapper_promotion_gate",
        "foreign_treasury_holder_leakage_promotion_gate",
    }
    assert {
        row["source_gate_mining_phase_status"]
        for row in source_gate_exhaustion_closure_rows
    } == {"stage_exhausted_no_concrete_promotion_grade_next_step"}
    assert all(
        row["promotion_gate_passed"] == "false"
        and row["no_further_source_mining_goal_recommended"] == "true"
        for row in source_gate_exhaustion_closure_rows
    )
    closure_by_gate = {
        row["gate_id"]: row for row in source_gate_exhaustion_closure_rows
    }
    assert (
        "fed_cross_border_treasury_basis_trade_context"
        in closure_by_gate["foreign_treasury_holder_leakage_promotion_gate"][
            "admitted_context_series_ids"
        ]
    )
    assert (
        closure_by_gate["foreign_treasury_holder_leakage_promotion_gate"][
            "gate_moved_beyond_context_this_tranche"
        ]
        == "true"
    )
    assert len(restricted_data_gate_spec_rows) == 5
    assert {
        row["gate_id"] for row in restricted_data_gate_spec_rows
    } == set(closure_by_gate)
    assert {
        row["promotion_gate_passed"] for row in restricted_data_gate_spec_rows
    } == {"false"}
    assert {
        row["forbidden_switches_remain_disabled"]
        for row in restricted_data_gate_spec_rows
    } == {"true"}
    assert {
        row["boundary_layer"] for row in assumption_mode_post_closure_boundary_rows
    } == {
        "evidence_mode_admitted_context",
        "stage_exhausted_public_source_blockers",
        "restricted_or_licensed_data_requirements",
        "explicit_assumption_mode_scenario_parameters",
        "disabled_claims_and_forbidden_outputs",
    }
    assert {
        row["public_source_mining_status"]
        for row in assumption_mode_post_closure_boundary_rows
        if row["boundary_layer"] == "stage_exhausted_public_source_blockers"
    } == {"stage_exhausted_no_general_mining_goal"}
    assert {
        row["forbidden_switches_remain_disabled"]
        for row in assumption_mode_post_closure_boundary_rows
    } == {"true"}
    assert {
        row["prior_narrowing_allowed"]
        for row in assumption_mode_post_closure_boundary_rows
    } == {"false"}
    assert any(
        row["channel_module"] == "public_liability_repricing_ladder"
        and row["candidate_prior_or_formula_handle"]
        == "treasury_repricing_speed_share_bucket_candidate"
        and (
            "MSPD Table 3 bucket gate passed" in row["exact_blocker"]
            or "fallback" in row["exact_blocker"]
        )
        for row in source_gate_decision_rows
    )
    live_bucket_rows = [
        row
        for row in source_gate_decision_rows
        if row["channel_module"] == "public_liability_repricing_ladder"
        and row["bridge_eligible_now"] == "true"
    ]
    assert all(
        row["bridge_action"]
        == (
            "use_existing_source_specific_formula_context_bridge_"
            "fail_closed_until_explicit_solver_opt_in"
        )
        and row["source_bridge_created_this_tranche"] == "false"
        and "no_new_table_or_solver_opt_in" in row["why_no_bridge_created"]
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["aggregate_assumption_behavior_preserved"] == "true"
        for row in live_bucket_rows
    )
    assert any(
        row["channel_module"] == "treasury_fed_recipient_leakage_bridge"
        and row["candidate_prior_or_formula_handle"] == "treasury_interest_demand_share"
        and "Holder-stock" in row["exact_blocker"]
        and row["gate_attempted_this_tranche"] == "true"
        and row["source_bridge_created_this_tranche"] == "false"
        and "demand_conversion" in row["why_no_bridge_created"]
        for row in source_gate_decision_rows
    )
    assert any(
        row["channel_module"] == "conventional_drag_denominator_evidence_matrix"
        and row["candidate_prior_or_formula_handle"] == "contractionary_drag_gdp_share"
        and "admissible" in row["evidence_needed_to_move_gate"]
        and row["gate_attempted_this_tranche"] == "true"
        and row["source_bridge_created_this_tranche"] == "false"
        and "channel_response" in row["why_no_bridge_created"]
        for row in source_gate_decision_rows
    )
    assert any(
        row["channel_module"] == "fiscal_tga_remittance_timing_path"
        and row["candidate_prior_or_formula_handle"] == "tga_liquidity_offset_share"
        and "non-additivity" in row["exact_blocker"]
        and row["gate_attempted_this_tranche"] == "true"
        and row["source_bridge_created_this_tranche"] == "false"
        and "denominator_response_design_scaffold" in row["next_gate_after_blocker"]
        for row in source_gate_decision_rows
    )
    assert {row["channel_component"] for row in safe_yield_pairing_gap_rows} == {
        "safe_yield_income_support_offset",
        "safe_yield_allocation_drag",
        "paired_net_safe_yield_effect",
    }
    assert {
        row["new_scaffold_enters_main_offset_ratio"]
        for row in safe_yield_pairing_gap_rows
        + bnpl_float_gap_rows
        + financialized_gap_rows
        + firm_gap_rows
        + conventional_drag_gap_rows
    } == {"false"}
    assert any(
        row["channel_component"] == "safe_yield_allocation_drag"
        and "paired" in row["promotion_gate"]
        for row in safe_yield_pairing_gap_rows
    )
    assert {row["channel_component"] for row in bnpl_float_gap_rows} == {
        "zero_interest_float_duration",
        "consumer_liquidity_sorting",
        "merchant_fee_pass_through",
    }
    assert {row["channel_component"] for row in financialized_gap_rows} == {
        "household_yield_optimization",
        "retail_mmf_tbill_access",
        "firm_liquid_asset_buffer",
    }
    assert {row["channel_component"] for row in firm_gap_rows} == {
        "firm_cash_assets",
        "debt_maturity_rollover",
        "floating_rate_refinancing_exposure",
        "external_finance_sector_sort",
    }
    assert {row["channel_component"] for row in conventional_drag_gap_rows} == {
        "conventional_drag_borrowing_cost",
        "conventional_drag_credit_supply",
        "conventional_drag_asset_price",
        "conventional_drag_expectations",
        "conventional_drag_exchange_rate_external",
    }
    assert {
        row["denominator_component"]
        for row in conventional_drag_source_design_gate_rows
    } == {
        "scalar_conventional_drag_amplitude",
        "conventional_drag_borrowing_cost",
        "conventional_drag_credit_supply",
        "conventional_drag_asset_price",
        "conventional_drag_expectations",
        "conventional_drag_exchange_rate_external",
    }
    assert {
        "safe_yield_offset_drag_pairing",
        "bnpl_zero_interest_float",
        "household_yield_optimization_financialized_balance_sheet",
        "firm_cash_debt_maturity_heterogeneity",
        "conventional_drag_denominator_evidence_matrix",
        "horizon_timing_layer",
    } <= {row["channel_module"] for row in promotion_gate_rows}
    assert {row["priority_rank"] for row in evidence_upgrade_queue_rows} == {
        str(rank) for rank in range(1, 11)
    }
    assert {row["channel_module"] for row in evidence_upgrade_queue_rows} <= {
        row["module_name"] for row in module_registry_rows
    }
    assert {
        "corporate_net_interest_cashflow_bridge",
        "working_capital_cost_pass_through",
        "term_structure_pricing_carry",
    }.isdisjoint({row["channel_module"] for row in evidence_upgrade_queue_rows})
    assert (
        evidence_upgrade_queue_rows[0]["channel_module"]
        == "public_liability_repricing_ladder"
    )
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in evidence_upgrade_queue_rows
    } == {"false"}
    assert {row["claim_boundary"] for row in evidence_upgrade_queue_rows} == {
        "interest_channel_evidence_queue_not_promotion"
    }
    for disabled_field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[disabled_field] for row in evidence_upgrade_queue_rows} == {"false"}
    assert {row["readiness_status"] for row in promotion_gate_rows} == {
        "model_audit_ready_source_gated_not_empirical_promotion"
    }
    assert {row["claim_boundary"] for row in promotion_gate_rows} == {
        "interest_channel_promotion_gate_not_claim_promotion"
    }
    recipient_promotion_gate = next(
        row
        for row in promotion_gate_rows
        if row["channel_module"] == "treasury_fed_recipient_leakage_bridge"
    )
    assert (
        "Do not narrow demand-conversion priors until the Treasury "
        "current-demand contract passes"
    ) in recipient_promotion_gate["promotion_gate"]
    assert "bank IORB timing blocker clears" in recipient_promotion_gate[
        "promotion_gate"
    ]
    assert "pricing" in recipient_promotion_gate["promotion_gate"]
    assert recipient_promotion_gate["incidence_claim_enabled"] == "false"
    assert recipient_promotion_gate["welfare_claim_enabled"] == "false"
    assert recipient_promotion_gate["holder_allocation_enabled"] == "false"
    assert {row["claim_boundary"] for row in horizon_timing_rows} == {
        "interest_channel_horizon_timing_matrix_not_dynamic_forecast"
    }
    for rows in (
        repricing_ladder_rows,
        repricing_evidence_bridge_rows,
        repricing_reconciliation_gap_rows,
        recipient_bridge_rows,
        recipient_evidence_gap_rows,
        treasury_recipient_source_gate_rows,
        finance_timing_rows,
        finance_timing_evidence_gap_rows,
        safe_yield_pairing_gap_rows,
        bnpl_float_gap_rows,
        financialized_gap_rows,
        firm_gap_rows,
        conventional_drag_gap_rows,
        conventional_drag_source_design_gate_rows,
        denominator_response_design_rows,
        denominator_event_outcome_cell_diagnostic_rows,
        denominator_design_readiness_decision_rows,
        denominator_formal_design_test_result_scaffold_rows,
        horizon_timing_rows,
        promotion_gate_rows,
        evidence_upgrade_queue_rows,
        source_gate_decision_rows,
        mspd_table3_bucket_gate_rows,
    ):
        assert all(row["source_specific_artifacts"] for row in rows)
        assert all(row["source_specific_series_or_table_ids"] for row in rows)
        assert all(row["source_specific_urls_or_docs"] for row in rows)
        assert all(row["source_specific_citation_or_design_handles"] for row in rows)
        assert all(row["source_specific_evidence_status"] for row in rows)
    assert {
        "0_1q",
        "1y",
        "3y",
        "5y",
        "10y",
    } == {row["horizon_bucket"] for row in horizon_timing_rows}
    assert {row["claim_boundary"] for row in repricing_ladder_rows} == {
        "public_liability_repricing_ladder_assumption_mode_not_security_level_repricing"
    }
    assert {row["claim_boundary"] for row in repricing_evidence_bridge_rows} == {
        (
            "public_liability_repricing_evidence_bridge_not_security_level_or_"
            "policy_claim"
        )
    }
    assert {
        "treasury_marketable_debt",
        "fed_reserve_liabilities",
        "fed_on_rrp_liabilities",
        "fed_treasury_remittance_timing",
    } <= {row["liability_block"] for row in repricing_evidence_bridge_rows}
    assert {
        row["current_assumption_behavior_preserved"]
        for row in repricing_evidence_bridge_rows
    } == {"true"}
    assert {
        row["enters_main_offset_ratio"] for row in repricing_evidence_bridge_rows
    } == {"false"}
    assert {row["claim_boundary"] for row in repricing_reconciliation_gap_rows} == {
        "public_liability_repricing_reconciliation_gap_not_formula_promotion"
    }
    assert {
        "source_backed_stock_context_review",
        "source_backed_timing_context_review",
    } <= {row["source_status_class"] for row in repricing_reconciliation_gap_rows}
    assert {
        row["source_status_class"]
        for row in repricing_reconciliation_gap_rows
        if row["liability_block"] == "treasury_marketable_debt"
    } <= {"fallback_review", "source_backed_context_review"}
    assert {
        row["aggregate_assumption_behavior_preserved"]
        for row in repricing_reconciliation_gap_rows
    } == {"true"}
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in repricing_reconciliation_gap_rows
    } == {"false"}
    assert {
        row["enters_main_offset_ratio"] for row in repricing_reconciliation_gap_rows
    } == {"false"}
    assert any(
        row["liability_block"] == "treasury_marketable_debt"
        and row["promotion_readiness"] == "blocked_fallback_or_reconciliation_review"
        and "MSPD Table 3" in row["exact_evidence_needed_before_formula_promotion"]
        for row in repricing_reconciliation_gap_rows
    )
    assert {row["claim_boundary"] for row in mspd_table3_bucket_gate_rows} == {
        "mspd_table3_bucket_repricing_gate_not_formula_or_prior_promotion"
    }
    assert {
        "mspd_table3_gate_summary",
        "maturity_bucket_coverage",
        "stock_scale_reconciliation",
        "field_coverage_and_model_scope",
    } <= {row["gate_block"] for row in mspd_table3_bucket_gate_rows}
    assert {
        row["horizon"]
        for row in mspd_table3_bucket_gate_rows
        if row["gate_block"] == "maturity_bucket_coverage"
    } == {"1q", "1y", "3y", "10y"}
    assert {
        row["formula_replacement_allowed"] for row in mspd_table3_bucket_gate_rows
    } <= {"false", "true"}
    assert {row["prior_narrowing_allowed"] for row in mspd_table3_bucket_gate_rows} <= {
        "false",
        "true",
    }
    assert all(
        (
            row["formula_replacement_allowed"] == "false"
            and row["prior_narrowing_allowed"] == "false"
        )
        or (
            row["source_snapshot_kind"] == "live"
            and row["mspd_reconciliation_status"] == "ok"
            and row["formula_replacement_allowed"] == "true"
            and row["prior_narrowing_allowed"] == "true"
        )
        for row in mspd_table3_bucket_gate_rows
    )
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in mspd_table3_bucket_gate_rows
    } == {"false"}
    assert {
        row["enters_main_offset_ratio"] for row in mspd_table3_bucket_gate_rows
    } == {"false"}
    assert any(
        row["gate_block"] == "mspd_table3_gate_summary"
        and row["source_snapshot_kind"] in {"fallback_stub", "demo_stub", "live"}
        and "treasury_recipient_leakage" in row["next_bridge_item_if_blocked"]
        for row in mspd_table3_bucket_gate_rows
    )
    assert any(
        row["gate_block"] == "stock_scale_reconciliation"
        and row["mspd_reconciliation_status"] in {"review", "ok", "missing_input"}
        for row in mspd_table3_bucket_gate_rows
    )
    assert any(
        row["evidence_block"] == "treasury_market_debt_repricing"
        and row["source_snapshot_kind"] in {"fallback_stub", "live", "demo_stub"}
        for row in repricing_evidence_bridge_rows
    )
    assert {row["claim_boundary"] for row in recipient_bridge_rows} == {
        "interest_recipient_leakage_bridge_assumption_mode_not_incidence_or_mpc"
    }
    assert {row["claim_boundary"] for row in recipient_evidence_gap_rows} == {
        (
            "interest_recipient_leakage_evidence_gap_not_incidence_mpc_or_"
            "holder_allocation"
        )
    }
    assert {row["cashflow_component"] for row in recipient_evidence_gap_rows} == {
        "treasury_interest",
        "iorb_interest",
        "on_rrp_interest",
        "current_remittance_reduction",
        "future_remittance_drag",
    }
    assert {
        row["aggregate_assumption_behavior_preserved"]
        for row in recipient_evidence_gap_rows
    } == {"true"}
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in recipient_evidence_gap_rows
    } == {"false"}
    assert any(
        row["cashflow_component"] == "treasury_interest"
        and row["gate_attempted_this_tranche"] == "true"
        and row["gate_attempt_result"]
        == "blocked_no_non_holder_demand_conversion_evidence"
        and row["prior_narrowing_decision"] == "do_not_narrow_demand_conversion_prior"
        and "leakage" in row["beyond_holder_or_context_evidence_status"]
        for row in recipient_evidence_gap_rows
    )
    assert {row["enters_main_offset_ratio"] for row in recipient_evidence_gap_rows} == {
        "false"
    }
    assert any(
        row["cashflow_component"] == "treasury_interest"
        and "holder-allocation" in row["exact_gate_before_demand_conversion_narrowing"]
        and row["source_evidence_exists"] == "true"
        for row in recipient_evidence_gap_rows
    )
    assert any(
        row["cashflow_component"] == "iorb_interest"
        and "Bank IORB pass-through"
        in row["missing_leakage_pass_through_timing_evidence"]
        for row in recipient_evidence_gap_rows
    )
    assert {row["claim_boundary"] for row in treasury_recipient_source_gate_rows} == {
        (
            "treasury_recipient_leakage_source_gate_not_incidence_mpc_tax_"
            "welfare_or_holder_allocation"
        )
    }
    assert {
        "treasury_recipient_gate_summary",
        "domestic_private_holder_context",
        "foreign_holder_leakage_context",
        "federal_reserve_remittance_routing_context",
        "mmf_portfolio_context",
    } == {row["gate_block"] for row in treasury_recipient_source_gate_rows}
    assert {
        row["holder_context_can_narrow_treasury_interest_demand_share"]
        for row in treasury_recipient_source_gate_rows
    } == {"false"}
    assert {
        row["prior_narrowing_allowed"] for row in treasury_recipient_source_gate_rows
    } == {"false"}
    assert {
        row["gate_attempted_this_tranche"]
        for row in treasury_recipient_source_gate_rows
    } == {"true"}
    assert {
        row["treasury_recipient_prior_narrowing_decision"]
        for row in treasury_recipient_source_gate_rows
    } == {"keep_treasury_interest_demand_share_prior_unchanged"}
    assert {
        row["admitted_context_without_prior_narrowing"]
        for row in treasury_recipient_source_gate_rows
    } == {"true"}
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in treasury_recipient_source_gate_rows
    } == {"false"}
    assert {
        row["enters_main_offset_ratio"] for row in treasury_recipient_source_gate_rows
    } == {"false"}
    assert {
        row["source_admission_review_status"]
        for row in treasury_recipient_source_gate_rows
    } == {"source_records_admitted_for_context_fail_closed_not_demand_conversion"}
    assert {
        row["source_gate_delta_this_tranche"]
        for row in treasury_recipient_source_gate_rows
    } == {"recipient_leakage_source_provenance_metadata_wired_fail_closed"}
    assert all(
        row["source_record_count_summary"]
        and row["source_record_hash_summary"]
        and row["source_record_date_bounds_summary"]
        for row in treasury_recipient_source_gate_rows
    )
    assert any(
        row["gate_block"] == "treasury_recipient_gate_summary"
        and row["demand_conversion_parameter"] == "treasury_interest_demand_share"
        and "Holder-stock" in row["why_holder_context_alone_cannot_narrow"]
        and "holder-allocation"
        in row["exact_gate_before_treasury_demand_conversion_narrowing"]
        for row in treasury_recipient_source_gate_rows
    )
    assert any(
        row["gate_block"] == "mmf_portfolio_context"
        and row["source_context_gate_movement_this_tranche"]
        == "admitted_ofr_sec_mmf_context_as_portfolio_context_only"
        and row["pass_through_context_status"]
        == "blocked_mmf_portfolio_context_not_final_investor_pass_through"
        and row["demand_conversion_evidence_status"]
        == "blocked_no_final_investor_demand_conversion_or_fee_retention_bridge"
        for row in treasury_recipient_source_gate_rows
    )
    assert any(
        row["gate_block"] == "federal_reserve_remittance_routing_context"
        and row["timing_context_status"]
        == "h41_mts_tga_context_available_but_nonadditive_remittance_timing_gate_still_blocks"
        and "h41_current:" in row["source_record_hash_summary"]
        for row in treasury_recipient_source_gate_rows
    )
    assert all(
        row["source_admission_review_status"]
        == "source_records_admitted_for_context_fail_closed_not_demand_conversion"
        and row["source_record_count_summary"]
        and row["source_record_hash_summary"]
        and row["source_record_date_bounds_summary"]
        and row["can_narrow_demand_conversion_prior"] == "false"
        for row in recipient_leakage_design_gate_rows
    )
    assert {
        row["claim_boundary"] for row in conventional_drag_source_design_gate_rows
    } == {
        "conventional_drag_source_design_gate_not_empirical_denominator_or_raw_rate_shock"
    }
    assert {
        row["denominator_prior_can_narrow"]
        for row in conventional_drag_source_design_gate_rows
    } == {"false"}
    assert {
        row["split_denominator_can_promote_to_main_classifier"]
        for row in conventional_drag_source_design_gate_rows
    } == {"false"}
    assert {
        row["prior_narrowing_allowed"]
        for row in conventional_drag_source_design_gate_rows
    } == {"false"}
    assert {
        row["gate_attempted_after_recipient_block"]
        for row in conventional_drag_source_design_gate_rows
    } == {"true"}
    assert {
        row["gate_attempt_result"] for row in conventional_drag_source_design_gate_rows
    } == {"blocked_no_admissible_channel_response_design_estimate"}
    assert {
        row["prior_narrowing_decision"]
        for row in conventional_drag_source_design_gate_rows
    } == {"keep_scalar_and_split_denominator_priors_unchanged"}
    assert {
        row["bridge_table_created"] for row in conventional_drag_source_design_gate_rows
    } == {"false"}
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in conventional_drag_source_design_gate_rows
    } == {"false"}
    assert any(
        row["gate_block"] == "denominator_design_gate_summary"
        and row["current_assumption_handle"] == "contractionary_drag_gdp_share"
        and "admissible" in row["exact_gate_before_denominator_prior_narrowing"]
        and row["raw_rate_shock_enabled"] == "false"
        for row in conventional_drag_source_design_gate_rows
    )
    assert {row["claim_boundary"] for row in denominator_response_design_rows} == {
        (
            "denominator_response_design_scaffold_not_empirical_drag_estimate_"
            "or_raw_rate_shock"
        )
    }
    assert {
        row["denominator_component"] for row in denominator_response_design_rows
    } == {
        "scalar_conventional_drag_amplitude",
        "conventional_drag_borrowing_cost",
        "conventional_drag_credit_supply",
        "conventional_drag_asset_price",
        "conventional_drag_expectations",
        "conventional_drag_exchange_rate_external",
    }
    assert {
        row["prior_narrowing_allowed"] for row in denominator_response_design_rows
    } == {"false"}
    assert {
        row["split_denominator_promotion_allowed"]
        for row in denominator_response_design_rows
    } == {"false"}
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in denominator_response_design_rows
    } == {"false"}
    assert any(
        row["denominator_component"] == "scalar_conventional_drag_amplitude"
        and "BRW" in row["admissible_shock_context"]
        and "horizon_specific_total_drag" in row["required_estimation_output"]
        and row["raw_rate_shock_enabled"] == "false"
        for row in denominator_response_design_rows
    )
    assert {row["horizon_bucket"] for row in denominator_response_design_test_rows} == {
        "0_1q",
        "1y",
        "3y",
        "5y",
        "10y",
    }
    assert {
        row["denominator_component"] for row in denominator_response_design_test_rows
    } == {
        "scalar_conventional_drag_amplitude",
        "conventional_drag_borrowing_cost",
        "conventional_drag_credit_supply",
        "conventional_drag_asset_price",
        "conventional_drag_expectations",
        "conventional_drag_exchange_rate_external",
    }
    assert {
        row["execution_status"] for row in denominator_response_design_test_rows
    } == {"blocked_design_metadata_only_no_denominator_estimate"}
    assert {row["claim_boundary"] for row in denominator_response_design_test_rows} == {
        "denominator_response_design_test_scaffold_not_empirical_drag_estimate"
    }
    assert all(
        row["support_diagnostic_required"] == "true"
        and row["pretrend_placebo_required"] == "true"
        and row["shock_relevance_required"] == "true"
        and row["sign_check_required"] == "true"
        and row["horizon_sensitivity_required"] == "true"
        and row["outlier_window_robustness_required"] == "true"
        and row["nonpromotion_check_required"] == "true"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in denominator_response_design_test_rows
    )
    assert {
        row["gate_attempt_result"] for row in denominator_response_gate_attempt_rows
    } == {"blocked_no_aligned_response_estimation_panel"}
    assert {
        row["claim_boundary"] for row in denominator_response_gate_attempt_rows
    } == {"denominator_response_gate_attempt_not_estimate_or_promotion"}
    assert all(
        row["source_context_available"] == "true"
        and row["all_design_metadata_present"] == "true"
        and row["aligned_response_estimation_panel_available"] == "false"
        and row["support_diagnostics_available"] == "false"
        and row["pretrend_placebo_available"] == "false"
        and row["shock_relevance_available"] == "false"
        and row["sign_check_available"] == "false"
        and row["horizon_sensitivity_available"] == "false"
        and row["outlier_window_robustness_available"] == "false"
        and row["nonpromotion_checks_available"] == "true"
        and row["bridge_eligible_now"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_response_gate_attempt_rows
    )
    assert {
        row["horizon_bucket"]
        for row in denominator_aligned_response_panel_scaffold_rows
    } == {"0_1q", "1y", "3y", "5y", "10y"}
    assert {
        row["denominator_component"]
        for row in denominator_aligned_response_panel_scaffold_rows
    } == {
        "scalar_conventional_drag_amplitude",
        "conventional_drag_borrowing_cost",
        "conventional_drag_credit_supply",
        "conventional_drag_asset_price",
        "conventional_drag_expectations",
        "conventional_drag_exchange_rate_external",
    }
    assert {
        row["shock_source_id"]
        for row in denominator_aligned_response_panel_scaffold_rows
    } == {
        "fed_brw_monetary_policy_shocks",
        "sf_fed_monetary_policy_surprises",
        "romer_romer_2004",
    }
    assert {
        row["source_frequency_alignment_status"]
        for row in denominator_aligned_response_panel_scaffold_rows
    } == {
        "registered_sources_alignable_with_high_frequency_aggregation_required",
        "registered_sources_alignable_with_monthly_outcome_window_required",
        "registered_sources_alignable_with_quarterly_release_lag_conversion_required",
    }
    assert {
        row["gate_attempt_result"]
        for row in denominator_aligned_response_panel_scaffold_rows
    } == {"blocked_panel_alignment_scaffold_no_estimation"}
    assert {
        row["claim_boundary"]
        for row in denominator_aligned_response_panel_scaffold_rows
    } == {"denominator_aligned_response_panel_scaffold_not_estimate_or_promotion"}
    assert all(
        row["panel_scaffold_created"] == "true"
        and row["registered_source_context_available"] == "true"
        and row["panel_cell_constructible_from_registered_sources"] == "true"
        and row["aligned_response_estimation_panel_available"] == "false"
        and row["support_diagnostics_available"] == "false"
        and row["pretrend_placebo_available"] == "false"
        and row["shock_relevance_available"] == "false"
        and row["sign_check_available"] == "false"
        and row["horizon_sensitivity_available"] == "false"
        and row["outlier_window_robustness_available"] == "false"
        and row["nonpromotion_checks_available"] == "true"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["aggregate_assumption_behavior_preserved"] == "true"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_aligned_response_panel_scaffold_rows
    )
    assert {
        row["horizon_bucket"] for row in denominator_event_outcome_cell_diagnostic_rows
    } == {"0_1q", "1y", "3y", "5y", "10y"}
    assert {
        row["denominator_component"]
        for row in denominator_event_outcome_cell_diagnostic_rows
    } == {
        "scalar_conventional_drag_amplitude",
        "conventional_drag_borrowing_cost",
        "conventional_drag_credit_supply",
        "conventional_drag_asset_price",
        "conventional_drag_expectations",
        "conventional_drag_exchange_rate_external",
    }
    assert {
        row["shock_source_id"] for row in denominator_event_outcome_cell_diagnostic_rows
    } == {
        "fed_brw_monetary_policy_shocks",
        "sf_fed_monetary_policy_surprises",
        "romer_romer_2004",
    }
    assert {
        row["support_count_status"]
        for row in denominator_event_outcome_cell_diagnostic_rows
    } <= {
        "minimum_support_count_met_not_estimation_ready",
        "some_cells_constructible_support_below_threshold",
        "no_constructible_event_outcome_cells",
    }
    assert all(
        int(row["constructible_event_outcome_cell_count"]) >= 0
        and int(row["missing_baseline_count"]) >= 0
        and int(row["missing_future_window_count"]) >= 0
        for row in denominator_event_outcome_cell_diagnostic_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_event_outcome_cell_diagnostic_rows
    } == {"denominator_event_outcome_cell_diagnostic_not_estimate_or_promotion"}
    assert all(
        row["cell_construction_status"]
        == "diagnostic_counts_only_no_event_outcome_panel_written"
        and row["response_estimate_available"] == "false"
        and row["support_diagnostics_available"] == "true"
        and row["pretrend_placebo_available"] == "false"
        and row["shock_relevance_available"] == "false"
        and row["sign_check_available"] == "false"
        and row["horizon_sensitivity_available"] == "false"
        and row["outlier_window_robustness_available"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["aggregate_assumption_behavior_preserved"] == "true"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_event_outcome_cell_diagnostic_rows
    )
    assert {
        row["claim_boundary"]
        for row in denominator_event_outcome_panel_value_diagnostic_rows
    } == {"denominator_event_outcome_panel_values_not_estimate_or_promotion"}
    assert {
        row["event_outcome_values_available"]
        for row in denominator_event_outcome_panel_value_diagnostic_rows
    } <= {"true", "false"}
    assert {
        row["value_diagnostic_status"]
        for row in denominator_event_outcome_panel_value_diagnostic_rows
    } <= {
        "sample_panel_values_constructed_not_response_estimate",
        "no_constructible_panel_values_from_registered_sources",
    }
    assert all(
        int(row["panel_value_rows_constructed_count"]) >= 0
        and row["transform_check_status"]
        in {
            "transform_values_computed_for_diagnostic_not_estimate",
            "transform_check_blocked_missing_panel_values",
        }
        for row in denominator_event_outcome_panel_value_diagnostic_rows
    )
    assert all(
        row["response_estimate_available"] == "false"
        and row["support_diagnostics_available"] == "true"
        and row["pretrend_placebo_available"] == "false"
        and row["shock_relevance_available"] == "false"
        and row["sign_check_available"] == "false"
        and row["horizon_sensitivity_available"] == "false"
        and row["outlier_window_robustness_available"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_event_outcome_panel_value_diagnostic_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_event_level_response_panel_rows
    } <= {"denominator_event_level_response_panel_not_estimate_or_promotion"}
    if denominator_event_level_response_panel_rows:
        assert {
            row["denominator_component"]
            for row in denominator_event_level_response_panel_rows
        } == {"scalar_conventional_drag_amplitude"}
        assert {
            row["shock_source_id"]
            for row in denominator_event_level_response_panel_rows
        } <= {
            "sf_fed_monetary_policy_surprises",
            "fed_brw_monetary_policy_shocks",
            "romer_romer_2004",
        }
        assert {
            row["outcome_series_id"]
            for row in denominator_event_level_response_panel_rows
        } <= {"GDP", "INDPRO"}
        assert {
            row["event_level_panel_available"]
            for row in denominator_event_level_response_panel_rows
        } <= {"true", "false"}
        assert {
            row["uncertainty_runner_executed"]
            for row in denominator_event_level_response_panel_rows
        } == {"false"}
        assert all(
            row["response_estimate_available"] == "false"
            and row["promotion_gate_passed"] == "false"
            and row["prior_narrowing_allowed"] == "false"
            and row["split_denominator_promotion_allowed"] == "false"
            and row["formula_replacement_allowed"] == "false"
            and row["main_offset_ratio_changed_this_tranche"] == "false"
            and row["raw_rate_shock_enabled"] == "false"
            and row["causal_financialization_claim_enabled"] == "false"
            for row in denominator_event_level_response_panel_rows
        )
        admitted_gdp_path_rows = [
            row
            for row in denominator_event_level_response_panel_rows
            if row["outcome_series_id"] == "GDP"
            and row["event_level_panel_available"] == "true"
        ]
        if admitted_gdp_path_rows:
            assert {
                row["retained_gdp_response_path_status"]
                for row in admitted_gdp_path_rows
            } == {
                "source_admitted_retained_gdp_response_path_from_fred_snapshot_"
                "fail_closed"
            }
        assert all(
            int(row["retained_gdp_response_path_observation_count"]) >= 2
            and row["retained_gdp_response_path_dates"]
            and row["retained_gdp_response_path_values"]
            and row["policy_path_exposure_vector_status"]
            == (
                "blocked_source_records_retain_event_shock_scalar_not_policy_"
                "path_exposure_vector"
            )
            and row["policy_path_exposure_vector_values"] == ""
            and row["policy_path_exposure_vector_source_status"]
            == "blocked_no_source_record_policy_path_exposure_vector"
            and row["policy_path_exposure_vector_construction_method_status"]
            == "blocked_no_registered_policy_path_vector_construction_method"
            and "model assumption" in row["policy_path_exposure_vector_method_blocker"]
            and "event/month shock scalar"
            in row["path_exposure_source_admission_blocker"]
            for row in admitted_gdp_path_rows
        )
        assert {
            row["claim_boundary"]
            for row in denominator_uncertainty_pass_fail_review_rows
        } <= {"denominator_uncertainty_review_not_calibration_or_promotion"}
    if denominator_uncertainty_pass_fail_review_rows:
        assert len(denominator_uncertainty_pass_fail_review_rows) >= 4
        assert {
            row["shock_source_id"]
            for row in denominator_uncertainty_pass_fail_review_rows
        } <= {
            "sf_fed_monetary_policy_surprises",
            "fed_brw_monetary_policy_shocks",
            "romer_romer_2004",
        }
        assert {
            row["outcome_series_id"]
            for row in denominator_uncertainty_pass_fail_review_rows
        } <= {"GDP", "INDPRO"}
        assert all(
            row["unit_conversion_to_gdp_share_per_100bp_year_status"]
            == "blocked_not_reviewed_for_denominator_prior_calibration"
            and row["uncertainty_pass"] == "false"
            and row["promotion_gate_passed"] == "false"
            and row["prior_narrowing_allowed"] == "false"
            and row["split_denominator_promotion_allowed"] == "false"
            and row["formula_replacement_allowed"] == "false"
            and row["main_offset_ratio_changed_this_tranche"] == "false"
            and row["raw_rate_shock_enabled"] == "false"
            and row["causal_financialization_claim_enabled"] == "false"
            and row["policy_path_duration_normalization_status"]
            == "blocked_policy_path_duration_normalization_not_admitted"
            and row["gdp_loss_convention_review_status"]
            == "blocked_cumulative_or_average_gdp_loss_convention_not_admitted"
            and row["unit_conversion_gate_decision"]
            in {
                "blocked_mechanical_mapping_only_not_admitted_denominator_conversion",
                "blocked_rr_endpoint_gdp_mapping_not_admitted_100bp_year_conversion",
                "blocked_ip_outcome_not_gdp_share_without_aggregation_bridge",
            }
            and row["formal_design_protocol_status"]
            == (
                "registered_fail_closed_lp_proxy_svar_path_integral_protocol_"
                "not_executed"
            )
            and row["formal_design_protocol_gate_decision"]
            in {
                "blocked_no_available_response_estimate_for_design_protocol_execution",
                "registered_fail_closed_protocol_blocked_missing_policy_path_and_"
                "gdp_response_path",
                "registered_fail_closed_protocol_blocked_endpoint_8q_not_path_integral",
                "registered_fail_closed_protocol_blocked_non_gdp_requires_"
                "aggregation_bridge",
            }
            and "bps-year" in row["policy_path_duration_protocol"]
            and "path-integral GDP-loss" in row["gdp_loss_convention_protocol"]
            and "denominator_drag_share_per_100bp_year"
            in row["path_integral_conversion_protocol"]
            and row["policy_path_exposure_vector_status"]
            in {
                "blocked_no_available_response_estimate_for_exposure_vector_review",
                "blocked_source_records_retain_event_shock_scalar_not_policy_path_"
                "exposure_vector",
                "blocked_non_gdp_outcome_not_scalar_denominator_exposure_design",
            }
            and row["policy_path_exposure_vector_event_count"] == "0"
            and row["policy_path_exposure_vector_construction_method_status"]
            in {
                "blocked_no_response_estimate_for_construction_method_review",
                "blocked_no_registered_policy_path_vector_construction_method",
                "blocked_non_gdp_outcome_requires_aggregation_before_method_review",
            }
            for row in denominator_uncertainty_pass_fail_review_rows
        )
        executed_gdp_uncertainty_rows = [
            row
            for row in denominator_uncertainty_pass_fail_review_rows
            if row["outcome_series_id"] == "GDP"
            and row["uncertainty_runner_executed"] == "true"
        ]
        if executed_gdp_uncertainty_rows:
            assert {
                row["retained_gdp_response_path_status"]
                for row in executed_gdp_uncertainty_rows
            } == {
                "source_admitted_retained_gdp_response_paths_from_fred_snapshot_"
                "fail_closed"
            }
            assert {
                row["path_exposure_admission_decision"]
                for row in executed_gdp_uncertainty_rows
            } == {
                "partial_source_admission_gdp_response_path_admitted_policy_path_"
                "exposure_vector_blocked"
            }
            assert {
                row["policy_path_exposure_vector_construction_method_status"]
                for row in executed_gdp_uncertainty_rows
            } == {"blocked_no_registered_policy_path_vector_construction_method"}
        assert {
            row["outcome_unit_handling_review_status"]
            for row in denominator_uncertainty_pass_fail_review_rows
            if row["outcome_series_id"] == "INDPRO"
        } == {"blocked_industrial_production_not_gdp_share_without_aggregation"}
        assert {
            row["outcome_unit_handling_review_status"]
            for row in denominator_uncertainty_pass_fail_review_rows
            if row["outcome_series_id"] == "GDP"
        } == {"reviewed_gdp_annualized_percent_change_endpoint_not_path_integral"}
        assert all(
            "mechanical_candidate_only" in row["mechanical_gdp_share_drag_formula"]
            for row in denominator_uncertainty_pass_fail_review_rows
            if row["outcome_series_id"] == "GDP"
        )
        executed_review_rows = [
            row
            for row in denominator_uncertainty_pass_fail_review_rows
            if row["uncertainty_runner_executed"] == "true"
        ]
        assert all(
            int(row["usable_observation_count"]) >= 30
            and row["hac_standard_error"]
            and row["diagnostic_ci_95_lower"]
            and row["diagnostic_ci_95_upper"]
            and row["diagnostic_p_value_normal_approx"]
            and row["uncertainty_method"]
            == (
                "diagnostic_event_level_ols_with_newey_west_hac_not_lp_or_"
                "promotion_grade"
            )
            and row["residual_design_retention_status"]
            == (
                "event_level_design_and_residual_summary_retained_"
                "fail_closed_not_full_lp_design"
            )
            and row["ci_p_value_availability_status"]
            == ("diagnostic_hac_ci_and_normal_p_value_available_not_promotion_grade")
            and row["pass_fail_decision"]
            == "blocked_review_executed_not_promotion_grade"
            for row in executed_review_rows
        )
    assert {
        row["claim_boundary"] for row in denominator_panel_design_test_diagnostic_rows
    } == {"denominator_panel_design_tests_not_estimate_or_promotion"}
    assert {
        row["design_test_family"]
        for row in denominator_panel_design_test_diagnostic_rows
    } == {
        "pretrend_placebo",
        "shock_relevance",
        "sign_consistency",
        "horizon_sensitivity",
        "outlier_window_robustness",
    }
    assert {
        row["diagnostic_status"]
        for row in denominator_panel_design_test_diagnostic_rows
    } == {"design_test_required_not_estimated_or_promotional"}
    assert {
        row["test_execution_status"]
        for row in denominator_panel_design_test_diagnostic_rows
    } <= {
        "design_inputs_constructible_test_not_run",
        "blocked_missing_event_outcome_values",
        "blocked_insufficient_horizon_peers_for_design_test",
    }
    assert all(
        row["test_statistic_available"] == "false"
        and row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["response_estimate_available"] == "false"
        and row["pretrend_placebo_available"] == "false"
        and row["shock_relevance_available"] == "false"
        and row["sign_check_available"] == "false"
        and row["horizon_sensitivity_available"] == "false"
        and row["outlier_window_robustness_available"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        and row["required_test_object"]
        and row["required_test_statistic"]
        and row["minimum_pass_condition_before_prior_narrowing"]
        for row in denominator_panel_design_test_diagnostic_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_pretrend_placebo_diagnostic_rows
    } == {"denominator_pretrend_placebo_statistics_not_estimate_or_promotion"}
    assert {
        row["diagnostic_status"] for row in denominator_pretrend_placebo_diagnostic_rows
    } <= {
        "pretrend_placebo_statistics_available_diagnostic_only",
        "blocked_insufficient_pretrend_or_placebo_support",
    }
    assert {
        row["diagnostic_statistic_available"]
        for row in denominator_pretrend_placebo_diagnostic_rows
    } <= {"true", "false"}
    assert all(
        row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["response_estimate_available"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_pretrend_placebo_diagnostic_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_shock_relevance_diagnostic_rows
    } == {"denominator_shock_relevance_statistics_not_estimate_or_promotion"}
    assert {
        row["diagnostic_status"] for row in denominator_shock_relevance_diagnostic_rows
    } <= {
        "shock_relevance_statistics_available_diagnostic_only",
        "shock_relevance_statistics_blocked",
    }
    assert {
        row["diagnostic_statistic_available"]
        for row in denominator_shock_relevance_diagnostic_rows
    } <= {"true", "false"}
    assert all(
        row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["response_estimate_available"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_shock_relevance_diagnostic_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_sign_consistency_diagnostic_rows
    } == {"denominator_sign_consistency_statistics_not_estimate_or_promotion"}
    assert {
        row["diagnostic_status"] for row in denominator_sign_consistency_diagnostic_rows
    } <= {
        "sign_consistency_statistics_available_diagnostic_only",
        "sign_consistency_statistics_blocked",
    }
    assert {
        row["diagnostic_statistic_available"]
        for row in denominator_sign_consistency_diagnostic_rows
    } <= {"true", "false"}
    assert all(
        row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["response_estimate_available"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_sign_consistency_diagnostic_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_horizon_sensitivity_diagnostic_rows
    } == {"denominator_horizon_sensitivity_statistics_not_estimate_or_promotion"}
    assert {
        row["diagnostic_status"]
        for row in denominator_horizon_sensitivity_diagnostic_rows
    } <= {
        "horizon_sensitivity_statistics_available_diagnostic_only",
        "horizon_sensitivity_statistics_blocked",
    }
    assert {
        row["diagnostic_statistic_available"]
        for row in denominator_horizon_sensitivity_diagnostic_rows
    } <= {"true", "false"}
    assert all(
        row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["response_estimate_available"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_horizon_sensitivity_diagnostic_rows
    )
    assert {
        row["claim_boundary"]
        for row in denominator_outlier_window_robustness_diagnostic_rows
    } == {"denominator_outlier_window_robustness_statistics_not_estimate_or_promotion"}
    assert {
        row["diagnostic_status"]
        for row in denominator_outlier_window_robustness_diagnostic_rows
    } <= {
        "outlier_window_statistics_available_diagnostic_only",
        "outlier_window_statistics_blocked",
    }
    assert {
        row["diagnostic_statistic_available"]
        for row in denominator_outlier_window_robustness_diagnostic_rows
    } <= {"true", "false"}
    assert all(
        row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["response_estimate_available"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_outlier_window_robustness_diagnostic_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_design_readiness_decision_rows
    } == {"denominator_design_readiness_decision_not_estimate_or_promotion"}
    assert {
        row["design_readiness_status"]
        for row in denominator_design_readiness_decision_rows
    } <= {
        "diagnostic_suite_complete_nonpromotional_not_prior_narrowing_ready",
        "blocked_missing_required_design_diagnostics",
    }
    assert {
        row["all_required_diagnostics_available"]
        for row in denominator_design_readiness_decision_rows
    } <= {"true", "false"}
    assert {
        row["missing_diagnostic_family_count"]
        for row in denominator_design_readiness_decision_rows
    }
    assert all(
        row["response_estimate_available"] == "false"
        and row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["promotion_gate_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_design_readiness_decision_rows
    )
    assert {
        row["claim_boundary"]
        for row in denominator_formal_design_test_result_scaffold_rows
    } == {"denominator_formal_design_test_result_scaffold_not_estimate_or_promotion"}
    assert {
        row["formal_result_status"]
        for row in denominator_formal_design_test_result_scaffold_rows
    } <= {
        "formal_result_scaffold_ready_nonpromotional_no_estimate_or_test_result",
        "blocked_before_formal_result_scaffold",
    }
    assert {
        row["formal_result_scaffold_created"]
        for row in denominator_formal_design_test_result_scaffold_rows
    } <= {"true", "false"}
    assert all(
        row["response_estimate_available"] == "false"
        and row["response_estimate_used_for_prior"] == "false"
        and row["formal_test_result_available"] == "false"
        and row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_formal_design_test_result_scaffold_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_formal_design_test_result_rows
    } == {"denominator_formal_design_test_result_not_estimate_or_promotion"}
    assert {
        row["formal_runner_status"]
        for row in denominator_formal_design_test_result_rows
    } <= {
        "formal_diagnostic_runner_executed_nonpromotional_no_response_estimate",
        "blocked_missing_required_diagnostic_families",
    }
    assert all(
        row["response_estimate_available"] == "false"
        and row["response_estimate_used_for_prior"] == "false"
        and row["formal_test_result_available"] == "false"
        and row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_formal_design_test_result_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_response_estimate_diagnostic_rows
    } == {"denominator_response_estimate_diagnostic_not_prior_narrowing_or_promotion"}
    assert {
        row["response_estimate_available"]
        for row in denominator_response_estimate_diagnostic_rows
    } <= {"true", "false"}
    assert all(
        row["response_estimate_used_for_prior"] == "false"
        and row["formal_test_result_available"] == "false"
        and row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_response_estimate_diagnostic_rows
    )
    assert {
        row["shock_admissibility_status"]
        for row in denominator_response_estimate_diagnostic_rows
    } <= {
        "diagnostic_shock_context_only_not_raw_rate_shock_claim",
        "romer_romer_narrative_shock_source_input_not_raw_rate_shock_claim",
    }
    assert {
        row["unit_conversion_to_gdp_share_status"]
        for row in denominator_response_estimate_diagnostic_rows
    } <= {
        "blocked_no_reviewed_mapping_to_gdp_share_per_100bp_year",
        "blocked_rr_gdp_8q_not_reviewed_gdp_share_per_100bp_year",
    }
    assert {
        row["denominator_prior_calibration_grade"]
        for row in denominator_response_estimate_diagnostic_rows
    } == {"not_calibration_grade_diagnostic_only"}
    assert {
        row["claim_boundary"]
        for row in denominator_cross_source_design_validation_rows
    } == {
        "denominator_cross_source_design_validation_not_prior_narrowing_or_promotion"
    }
    assert {
        row["cell_validation_status"]
        for row in denominator_cross_source_design_validation_rows
    } <= {"internally_consistent", "failed", "blocked"}
    assert {
        row["promotion_switch_lock_status"]
        for row in denominator_cross_source_design_validation_rows
    } == {"pass"}
    assert all(
        row["response_estimate_used_for_prior"] == "false"
        and row["formal_test_result_available"] == "false"
        and row["test_result_available"] == "false"
        and row["test_passed"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_cross_source_design_validation_rows
    )
    romer_borrowing_peer_rows = [
        row
        for row in denominator_cross_source_design_validation_rows
        if row["denominator_component"] == "conventional_drag_borrowing_cost"
        and row["shock_source_id"] == "romer_romer_2004"
        and row["outcome_series_id"] in {"GDP", "INDPRO"}
    ]
    assert len(romer_borrowing_peer_rows) == 10
    assert {
        row["cross_source_replication_validation_status"]
        for row in romer_borrowing_peer_rows
    } <= {
        "cross_source_peer_available_diagnostic_only_not_promotion",
        "blocked_cell_not_internally_consistent",
    }
    assert {
        row["formal_response_alignment_status"] for row in romer_borrowing_peer_rows
    } <= {"pass", "blocked_formal_diagnostic_result_unavailable"}
    assert {row["response_estimate_available"] for row in romer_borrowing_peer_rows} <= {
        "true",
        "false",
    }
    assert all(
        (
            row["cross_source_replication_validation_status"]
            == "cross_source_peer_available_diagnostic_only_not_promotion"
            and row["formal_response_alignment_status"] == "pass"
        )
        if row["response_estimate_available"] == "true"
        else (
            row["cross_source_replication_validation_status"]
            == "blocked_cell_not_internally_consistent"
            and row["formal_response_alignment_status"]
            == "blocked_formal_diagnostic_result_unavailable"
        )
        for row in romer_borrowing_peer_rows
    )
    assert all(
        row["response_estimate_used_for_prior"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in romer_borrowing_peer_rows
    )
    romer_borrowing_blocked_rows = [
        row
        for row in denominator_cross_source_design_validation_rows
        if row["denominator_component"] == "conventional_drag_borrowing_cost"
        and row["shock_source_id"] == "romer_romer_2004"
        and row["outcome_series_id"] in {"TDSP", "BAMLH0A0HYM2"}
    ]
    assert len(romer_borrowing_blocked_rows) == 10
    assert {
        row["cross_source_replication_validation_status"]
        for row in romer_borrowing_blocked_rows
    } == {"blocked_cell_not_internally_consistent"}
    assert {
        row["response_estimate_available"] for row in romer_borrowing_blocked_rows
    } == {"false"}
    assert {
        row["claim_boundary"]
        for row in denominator_evidence_upgrade_source_design_requirement_rows
    } == {
        (
            "denominator_evidence_upgrade_source_design_requirement_not_"
            "prior_narrowing_or_promotion"
        )
    }
    assert {
        row["requirement_status"]
        for row in denominator_evidence_upgrade_source_design_requirement_rows
    } == {"blocked_diagnostic_only_evidence_upgrade_required"}
    assert all(
        int(row["blocked_validation_cell_count"]) >= 1
        and row["missing_source_or_design_evidence"]
        and row["required_promotion_grade_evidence"]
        and row["required_source_design_upgrade"]
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_evidence_upgrade_source_design_requirement_rows
    )
    assert {
        row["claim_boundary"] for row in denominator_evidence_upgrade_priority_queue_rows
    } == {
        "denominator_evidence_upgrade_priority_queue_not_prior_narrowing_or_promotion"
    }
    assert {
        row["priority_surface_status"]
        for row in denominator_evidence_upgrade_priority_queue_rows
    } == {"blocked_diagnostic_only_priority_queue"}
    assert [int(row["priority_rank"]) for row in denominator_evidence_upgrade_priority_queue_rows] == list(
        range(1, len(denominator_evidence_upgrade_priority_queue_rows) + 1)
    )
    assert all(
        int(row["priority_score"]) >= int(row["likely_model_relevance_score"])
        and row["primary_blocker_type"]
        and row["priority_bucket"]
        and row["recommended_review_sequence"]
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_evidence_upgrade_priority_queue_rows
    )
    tier1_priority_rows = [
        row
        for row in denominator_evidence_upgrade_priority_queue_rows
        if row["priority_bucket"] == "tier_1_highest_review_priority"
    ]
    assert len(denominator_evidence_upgrade_tier1_workplan_rows) == len(
        tier1_priority_rows
    )
    assert {
        row["claim_boundary"]
        for row in denominator_evidence_upgrade_tier1_workplan_rows
    } == {
        "denominator_evidence_upgrade_tier1_workplan_not_source_claim_or_promotion"
    }
    assert {
        row["workplan_surface_status"]
        for row in denominator_evidence_upgrade_tier1_workplan_rows
    } == {"blocked_diagnostic_only_tier1_workplan"}
    assert [
        int(row["source_priority_rank"])
        for row in denominator_evidence_upgrade_tier1_workplan_rows
    ] == [int(row["priority_rank"]) for row in tier1_priority_rows]
    assert all(
        row["source_priority_bucket"] == "tier_1_highest_review_priority"
        and row["current_source_artifacts"]
        and row["linked_cross_source_design_validation_ids"]
        and row["linked_chain_key_alignment_status_summary"]
        and row["linked_formal_response_alignment_status_summary"]
        and row["linked_cross_source_replication_validation_status_summary"]
        and row["source_design_execution_status"].startswith(
            "current_source_design_inputs_"
        )
        and row["source_design_execution_blocker"]
        and row["missing_evidence_contract"]
        and row["candidate_peer_source_design_requirement"]
        and row["provenance_review_contract"]
        and row["fail_closed_admission_gate"]
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_evidence_upgrade_tier1_workplan_rows
    )
    assert {
        row["source_tier1_workplan_id"]
        for row in denominator_evidence_upgrade_blocker_resolution_matrix_rows
    } == {
        row["tier1_workplan_id"]
        for row in denominator_evidence_upgrade_tier1_workplan_rows
    }
    assert {
        row["claim_boundary"]
        for row in denominator_evidence_upgrade_blocker_resolution_matrix_rows
    } == {
        "denominator_evidence_upgrade_blocker_resolution_matrix_not_source_claim_or_promotion"
    }
    assert {
        row["resolution_surface_status"]
        for row in denominator_evidence_upgrade_blocker_resolution_matrix_rows
    } == {"blocked_diagnostic_only_blocker_resolution_matrix"}
    assert {
        "missing_evidence_contract_item",
        "diagnostic_family_repair_item",
        "candidate_peer_source_design_prerequisite",
        "provenance_prerequisite",
        "fail_closed_admission_status",
    }.issubset(
        {
            row["resolution_category"]
            for row in denominator_evidence_upgrade_blocker_resolution_matrix_rows
        }
    )
    assert all(
        row["blocker_item"]
        and row["required_resolution_action"]
        and row["admission_gate_status"] == "blocked_no_source_admission"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_evidence_upgrade_blocker_resolution_matrix_rows
    )
    matrix_pairs = {
        (row["source_tier1_workplan_id"], row["resolution_category"])
        for row in denominator_evidence_upgrade_blocker_resolution_matrix_rows
    }
    assert len(denominator_evidence_upgrade_blocker_status_rollup_rows) == len(
        matrix_pairs
    )
    assert {
        (row["source_tier1_workplan_id"], row["resolution_category"])
        for row in denominator_evidence_upgrade_blocker_status_rollup_rows
    } == matrix_pairs
    assert {
        row["claim_boundary"]
        for row in denominator_evidence_upgrade_blocker_status_rollup_rows
    } == {
        "denominator_evidence_upgrade_blocker_status_rollup_not_source_claim_or_promotion"
    }
    assert {
        row["rollup_surface_status"]
        for row in denominator_evidence_upgrade_blocker_status_rollup_rows
    } == {"blocked_diagnostic_only_blocker_status_rollup"}
    assert all(
        int(row["blocker_item_count"]) > 0
        and int(row["unresolved_item_count"]) == int(row["blocker_item_count"])
        and row["unresolved_status"] == "all_items_unresolved_blocked"
        and row["required_next_evidence_action"]
        and row["required_action_coverage_status"]
        == "all_required_actions_populated"
        and row["provenance_coverage_status"]
        and row["admission_gate_status"] == "blocked_no_source_admission"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in denominator_evidence_upgrade_blocker_status_rollup_rows
    )
    assert {
        row["claim_boundary"] for row in conventional_drag_evidence_tranche_rows
    } == {"conventional_drag_evidence_tranche_not_prior_narrowing_or_promotion"}
    assert {
        row["priority_selection_status"]
        for row in conventional_drag_evidence_tranche_rows
    } <= {
        "no_tier1_priority_row_estimable_from_current_artifacts",
        "higher_priority_row_blocked_by_current_artifacts",
        "selected_first_estimable_priority_row",
        "not_selected_lower_priority_or_nonestimable_row",
    }
    selected_tranche_rows = [
        row
        for row in conventional_drag_evidence_tranche_rows
        if row["priority_selection_status"] == "selected_first_estimable_priority_row"
    ]
    if selected_tranche_rows:
        assert {
            (
                row["source_priority_rank"],
                row["denominator_component"],
                row["outcome_series_id"],
            )
            for row in selected_tranche_rows
        } == {("2", "conventional_drag_borrowing_cost", "TDSP")}
        assert all(
            row["estimate_available"] == "true"
            and row["diagnostic_coefficient"]
            and row["hac_standard_error"]
            and row["mechanical_outcome_change_per_100bp"]
            for row in selected_tranche_rows
        )
    else:
        assert {
            row["priority_selection_status"]
            for row in conventional_drag_evidence_tranche_rows
        } == {"no_tier1_priority_row_estimable_from_current_artifacts"}
    assert all(
        row["literature_calibration_status"]
        == "context_only_no_source_backed_literature_calibration_row"
        and row["promotion_gate_status"] == "blocked_no_denominator_promotion"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        and row["causal_financialization_claim_enabled"] == "false"
        for row in conventional_drag_evidence_tranche_rows
    )
    assert all(
        row["estimate_available"] == "false"
        and row["estimate_status"].startswith("blocked_")
        for row in conventional_drag_evidence_tranche_rows
        if row["priority_selection_status"]
        == "higher_priority_row_blocked_by_current_artifacts"
    )
    assert {row["claim_boundary"] for row in finance_timing_rows} == {
        "public_finance_timing_path_assumption_mode_not_fiscal_reaction_estimate"
    }
    assert {row["claim_boundary"] for row in finance_timing_evidence_gap_rows} == {
        (
            "public_finance_timing_evidence_gap_not_fiscal_reaction_or_"
            "threshold_promotion"
        )
    }
    assert {row["timing_component"] for row in finance_timing_evidence_gap_rows} == {
        "fiscal_offset",
        "tga_liquidity_offset",
        "current_remittance_reduction",
        "future_remittance_drag_demand_offset",
        "future_public_finance_drag_residual_memo",
    }
    assert {
        row["aggregate_assumption_behavior_preserved"]
        for row in finance_timing_evidence_gap_rows
    } == {"true"}
    assert {
        row["main_offset_ratio_changed_this_tranche"]
        for row in finance_timing_evidence_gap_rows
    } == {"false"}
    assert {
        row["enters_main_offset_ratio"] for row in finance_timing_evidence_gap_rows
    } == {"false"}
    assert {
        row["gate_attempted_this_tranche"] for row in finance_timing_evidence_gap_rows
    } == {"true"}
    assert {
        row["admitted_context_without_prior_narrowing"]
        for row in finance_timing_evidence_gap_rows
    } == {"true"}
    assert any(
        row["timing_component"] == "fiscal_offset"
        and (
            (
                row["missing_source_artifacts_for_gate"] == "treasury_dts"
                and row["timing_source_context_status"]
                == "source_backed_mts_cbo_context_available_dts_snapshot_missing"
            )
            or (
                row["missing_source_artifacts_for_gate"] == "none"
                and row["timing_source_context_status"]
                == "source_backed_mts_dts_cbo_context_available_nonadditivity_bridge_still_blocked"
            )
        )
        and row["absorber_prior_evidence_status"]
        == "blocked_context_not_fiscal_offset_prior_evidence"
        for row in finance_timing_evidence_gap_rows
    )
    assert any(
        row["timing_component"] == "current_remittance_reduction"
        and row["timing_source_context_status"]
        == "source_backed_h41_mts_tga_context_available_current_remittance_state_guard_still_required"
        and row["netting_nonadditivity_context_status"]
        == "blocked_no_remittance_treasury_cash_fiscal_tga_netting_test"
        for row in finance_timing_evidence_gap_rows
    )
    assert {row["test_family"] for row in finance_timing_design_test_rows} == {
        "source_timing_alignment",
        "netting_nonadditivity",
        "current_numerator_inclusion",
        "memo_only_residual_guard",
        "absorber_prior_narrowing_gate",
    }
    assert {row["timing_component"] for row in finance_timing_design_test_rows} == {
        "fiscal_offset",
        "tga_liquidity_offset",
        "current_remittance_reduction",
        "future_remittance_drag_demand_offset",
        "future_public_finance_drag_residual_memo",
    }
    assert {row["execution_status"] for row in finance_timing_design_test_rows} == {
        "blocked_design_metadata_only_no_timing_bridge"
    }
    assert {row["claim_boundary"] for row in finance_timing_design_test_rows} == {
        (
            "public_finance_timing_design_test_scaffold_not_fiscal_reaction_or_"
            "threshold_promotion"
        )
    }
    assert all(
        row["current_numerator_inclusion_decision"]
        and row["netting_nonadditivity_requirement"]
        and row["test_blocker"]
        == "missing_source_backed_timing_netting_nonadditivity_bridge"
        and row["prior_narrowing_allowed"] == "false"
        and row["timing_bridge_created"] == "false"
        and row["main_offset_ratio_changed_this_tranche"] == "false"
        and row["policy_failure_claim_enabled"] == "false"
        and row["tax_output_enabled"] == "false"
        and row["mpc_output_enabled"] == "false"
        for row in finance_timing_design_test_rows
    )
    assert {
        row["timing_prior_narrowing_decision"]
        for row in finance_timing_evidence_gap_rows
    } == {"keep_public_finance_timing_and_absorber_priors_unchanged"}
    assert {
        row["timing_bridge_created"] for row in finance_timing_evidence_gap_rows
    } == {"false"}
    assert any(
        row["timing_component"] == "tga_liquidity_offset"
        and "financing-source" in row["exact_gate_before_timing_absorber_narrowing"]
        and row["source_evidence_exists"] == "true"
        for row in finance_timing_evidence_gap_rows
    )
    assert any(
        row["timing_component"] == "future_public_finance_drag_residual_memo"
        and row["memo_only_public_finance_timing_values"] == "true"
        and "memo" in row["allowed_current_use"]
        for row in finance_timing_evidence_gap_rows
    )
    assert any(
        row["timing_component"] == "future_public_finance_drag_residual_memo"
        and row["memo_only_public_finance_timing"] == "true"
        and row["enters_main_offset_ratio"] == "false"
        for row in finance_timing_rows
    )
    assert any(
        row["cashflow_component"] == "future_remittance_drag"
        and row["main_offset_ratio_role"]
        == "current_negative_demand_offset_for_demand_share_only"
        for row in recipient_bridge_rows
    )
    flow_stage_rows = list(
        csv.DictReader(
            artifacts.ratewall_flow_stage_decomposition_table.open(encoding="utf-8")
        )
    )
    assert flow_stage_rows
    assert {
        "mechanical_public_cashflows",
        "recipient_demand_conversion",
        "absorber_block",
        "private_attenuation_block",
    } <= {row["stage"] for row in flow_stage_rows}
    absorber_rows = [
        row
        for row in flow_stage_rows
        if row["component"] in {"fiscal_offset", "tga_liquidity_offset"}
    ]
    assert absorber_rows
    assert {row["stage_basis"] for row in absorber_rows} == {
        "tax_adjusted_recipient_demand_converted_interest_offset"
    }
    assert {row["numerator_inclusion_scope"] for row in absorber_rows} == {
        "included_via_net_interest_block"
    }
    assert all(row["scalar_component_value_bil"] for row in flow_stage_rows)
    assert all(row["split_component_value_bil"] for row in flow_stage_rows)
    for field in (
        "reported_component_value_bil_default_scalar",
        "scalar_countervailing_total_bil",
        "split_countervailing_total_bil",
        "share_of_scalar_countervailing_total",
        "share_of_split_countervailing_total",
        "directly_added_to_final_numerator",
        "indirectly_enters_via_net_interest_block",
    ):
        assert field in flow_stage_rows[0]
    assert {
        row["indirectly_enters_via_net_interest_block"] for row in absorber_rows
    } == {"true"}
    assert any(
        row["component"] == "firm_cash_attenuation"
        and row["stage_basis"] == "firm_liquid_asset_stock_share_gdp_rate_path_base"
        and row["scalar_component_value_bil"] == row["split_component_value_bil"]
        for row in flow_stage_rows
    )
    assert all(
        row["claim_boundary"]
        == "flow_stage_decomposition_assumption_mode_not_incidence_or_fiscal_reaction_estimate"
        for row in flow_stage_rows
    )
    gross_rows = list(
        csv.DictReader(
            artifacts.ratewall_gross_interest_subchannels_table.open(encoding="utf-8")
        )
    )
    finance_rows = list(
        csv.DictReader(
            artifacts.ratewall_public_finance_adjustment_table.open(encoding="utf-8")
        )
    )
    net_rows = list(
        csv.DictReader(
            artifacts.ratewall_net_countervailing_channels_table.open(encoding="utf-8")
        )
    )
    assert gross_rows and finance_rows and net_rows
    assert {row["additivity_scope"] for row in gross_rows} == {
        "gross_subchannel_nonadditive"
    }
    assert all(row["numerator_inclusion_scope"] for row in gross_rows)
    assert any(
        row["adjustment_component"] == "future_public_finance_drag_residual_memo"
        and row["memo_only_public_finance_timing"] == "true"
        for row in finance_rows
    )
    assert all("directly_added_to_final_numerator" in row for row in finance_rows)
    assert any(
        row["adjustment_component"] == "future_remittance_drag_demand_offset"
        and row["indirectly_enters_via_net_interest_block"] == "true"
        for row in finance_rows
    )
    assert "net_interest_after_fiscal_tga_offsets" in {
        row["net_channel"] for row in net_rows
    }
    assert all(row["scalar_channel_value_bil"] for row in net_rows)
    assert all(row["split_channel_value_bil"] for row in net_rows)
    assert all(row["share_of_scalar_countervailing_total"] for row in net_rows)
    assert all(row["share_of_split_countervailing_total"] for row in net_rows)
    parameter_rows = list(
        csv.DictReader(
            artifacts.ratewall_parameter_frontier_table.open(encoding="utf-8")
        )
    )
    assert parameter_rows
    assert {
        "public_debt_stock_scale",
        "treasury_repricing_speed_share",
        "rate_path_bps_year",
        "fed_liability_stock_scale",
        "treasury_interest_demand_share",
        "firm_cash_attenuation_share",
        "safe_asset_allocation_offset_share",
        "safe_asset_allocation_drag_share",
        "fiscal_offset_share",
        "tga_liquidity_offset_share",
        "contractionary_drag_gdp_share",
    } <= {row["parameter"] for row in parameter_rows}
    assert {row["claim_boundary"] for row in parameter_rows} == {
        "parameter_frontier_assumption_mode_not_empirical_estimate"
    }
    for field in (
        "parameter_pack_low",
        "parameter_pack_base",
        "parameter_pack_high",
        "threshold_within_parameter_pack",
        "threshold_pack_status",
    ):
        assert field in parameter_rows[0]
    assert "mathematically_reachable_outside_prior_pack" in {
        row["threshold_pack_status"] for row in parameter_rows
    }
    hit_fragility_rows = list(
        csv.DictReader(
            artifacts.ratewall_hit_fragility_frontier_table.open(encoding="utf-8")
        )
    )
    assert hit_fragility_rows
    assert {row["claim_boundary"] for row in hit_fragility_rows} == {
        "hit_fragility_frontier_assumption_mode_not_empirical_threshold"
    }
    assert {row["assumption_set"] for row in hit_fragility_rows} == {
        row["assumption_set"]
        for row in wall_hit_rows
        if row["wall_hit_under_assumptions"] == "true"
    }
    assert {
        "fragility_threshold_found",
        "still_hits_at_solver_bound",
    } & {row["frontier_status"] for row in hit_fragility_rows}
    assert all(row["fragility_threshold_value"] for row in hit_fragility_rows)
    drag_decomposition_rows = list(
        csv.DictReader(
            artifacts.ratewall_conventional_drag_decomposition_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(drag_decomposition_rows) == len(assumption_rows) * 5
    assert {row["claim_boundary"] for row in drag_decomposition_rows} == {
        "split_denominator_robustness_lane_non_load_bearing_for_headline_hit_verdict_assumption_mode_not_empirical_estimate"
    }
    assert {row["enters_main_ratio"] for row in drag_decomposition_rows} == {"false"}
    assert {
        row["split_denominator_promotion_allowed"] for row in drag_decomposition_rows
    } == {"false"}
    assert {row["allowed_use"] for row in drag_decomposition_rows} == {
        "robustness_decomposition_only"
    }
    assert {row["blocked_use"] for row in drag_decomposition_rows} == {
        "headline_hit_verdict;canonical_rw_y;evidence_mode"
    }
    for assumption_set in {row["assumption_set"] for row in drag_decomposition_rows}:
        group = [
            row
            for row in drag_decomposition_rows
            if row["assumption_set"] == assumption_set
        ]
        split_sum = sum(Decimal(row["component_value_bil"]) for row in group)
        expected = Decimal(group[0]["split_conventional_drag_bil"])
        assert split_sum == expected
        assert group[0]["denominator_share_sum_status"] == "shares_sum_to_one"
    split_rows = list(
        csv.DictReader(
            artifacts.ratewall_split_denominator_comparison_table.open(encoding="utf-8")
        )
    )
    assert len(split_rows) == len(assumption_rows)
    assert {row["claim_boundary"] for row in split_rows} == {
        "split_denominator_robustness_lane_non_load_bearing_for_headline_hit_verdict_assumption_mode_not_empirical_estimate"
    }
    assert {row["enters_main_ratio"] for row in split_rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in split_rows} == {
        "false"
    }
    assert {row["allowed_use"] for row in split_rows} == {
        "robustness_decomposition_only"
    }
    assert {row["blocked_use"] for row in split_rows} == {
        "headline_hit_verdict;canonical_rw_y;evidence_mode"
    }
    assert {row["empirical_claim_enabled"] for row in split_rows} == {"false"}
    assert {row["policy_failure_claim_enabled"] for row in split_rows} == {"false"}
    assert {row["pricing_output_enabled"] for row in split_rows} == {"false"}
    assert {row["incidence_claim_enabled"] for row in split_rows} == {"false"}
    assert {row["welfare_claim_enabled"] for row in split_rows} == {"false"}
    assert {row["causal_financialization_claim_enabled"] for row in split_rows} == {
        "false"
    }
    assert "classification_changes_under_split_denominator" in {
        row["classification_change_flag"] for row in split_rows
    } or all(
        row["denominator_share_sum_status"] == "shares_sum_to_one" for row in split_rows
    )
    assert {row["denominator_share_sum_status"] for row in split_rows} == {
        "shares_sum_to_one"
    }
    assert {
        row["scalar_baseline_uses_split_targeted_attenuation"] for row in split_rows
    } == {"false"}
    denominator_sensitivity_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_sensitivity_table.open(encoding="utf-8")
        )
    )
    assert len(denominator_sensitivity_rows) == len(assumption_rows) * 5
    assert {row["claim_boundary"] for row in denominator_sensitivity_rows} == {
        "denominator_sensitivity_assumption_mode_not_empirical_estimate"
    }
    for field in (
        "classification_change_driver",
        "classification_change_driver_type",
        "decisive_denominator_channel",
        "component_share_interpretation",
    ):
        assert all(row[field] for row in denominator_sensitivity_rows)
    assert all(
        row["decisive_denominator_channel"] == "split_denominator_total_drag_multiplier"
        and "decomposition_only" in row["component_share_interpretation"]
        for row in denominator_sensitivity_rows
        if row["classification_change_driver_type"] == "total_drag_amplitude"
    )
    denominator_uncertainty_rows = list(
        csv.DictReader(
            artifacts.ratewall_split_denominator_uncertainty_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(denominator_uncertainty_rows) == len(assumption_rows) * 5 * 3
    assert {row["stress_family"] for row in denominator_uncertainty_rows} == {
        "composition_reallocation_stress"
    }
    assert all(
        abs(Decimal(row["denominator_share_sum"]) - Decimal("1")) < Decimal("0.000001")
        for row in denominator_uncertainty_rows
    )
    assert {row["claim_boundary"] for row in denominator_uncertainty_rows} == {
        "split_denominator_uncertainty_assumption_mode_not_empirical_estimate"
    }
    for disabled_field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[disabled_field] for row in denominator_uncertainty_rows} == {
            "false"
        }
    regime_stability_rows = list(
        csv.DictReader(
            artifacts.ratewall_split_denominator_regime_stability_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(regime_stability_rows) == len(assumption_rows)
    assert {row["claim_boundary"] for row in regime_stability_rows} == {
        "split_denominator_regime_stability_assumption_mode_not_empirical_threshold"
    }
    assert {row["stability_group"] for row in regime_stability_rows} <= {
        "stable_hit",
        "stable_near_wall_or_attenuated",
        "stable_robust_non_hit",
        "classification_sensitive",
    }
    for disabled_field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[disabled_field] for row in regime_stability_rows} == {"false"}
    parameter_pack_rows_ = list(
        csv.DictReader(artifacts.ratewall_parameter_packs_table.open(encoding="utf-8"))
    )
    assert parameter_pack_rows_
    assert {
        "public_impulse_multiplier",
        "treasury_interest_demand_share",
        "borrowing_cost_drag_share",
        "credit_supply_drag_share",
        "asset_price_drag_share",
        "expectations_drag_share",
        "exchange_rate_external_drag_share",
        "zero_interest_credit_attenuation_share",
        "safe_asset_allocation_drag_share",
        "split_denominator_total_drag_multiplier",
        "household_yield_optimization_share",
        "household_interest_bearing_liquid_share",
        "deposit_beta_to_households",
        "mmf_tbill_access_share",
        "firm_liquid_asset_scale",
    } <= {row["parameter"] for row in parameter_pack_rows_}
    assert {row["claim_boundary"] for row in parameter_pack_rows_} == {
        "parameter_pack_context_not_empirical_threshold"
    }
    assert all(row["source_status"] for row in parameter_pack_rows_)
    assert all(row["plausibility_status"] for row in parameter_pack_rows_)
    assert all(row["source_note"] for row in parameter_pack_rows_)
    assert all(row["literature_context"] for row in parameter_pack_rows_)
    assert all(row["evidence_needed"] for row in parameter_pack_rows_)
    assert all(row["model_use"] for row in parameter_pack_rows_)
    assert all(row["review_question"] for row in parameter_pack_rows_)
    assert all(row["calibration_status"] for row in parameter_pack_rows_)
    assert all(row["allowed_model_use"] for row in parameter_pack_rows_)
    assert {row["scenario_implied_only"] for row in parameter_pack_rows_} == {"true"}
    financialized_pack_rows = [
        row
        for row in parameter_pack_rows_
        if row["parameter"]
        in {
            "household_yield_optimization_share",
            "household_interest_bearing_liquid_share",
            "deposit_beta_to_households",
            "mmf_tbill_access_share",
            "firm_liquid_asset_scale",
        }
    ]
    assert len(financialized_pack_rows) == 5
    assert all(
        row["plausibility_status"]
        in {
            "optional_amplifier_not_causal_financialization",
            "optional_amplifier_not_incidence",
            "optional_amplifier_not_deposit_pricing_output",
            "optional_amplifier_not_holder_allocation",
        }
        for row in financialized_pack_rows
    )
    financialized_rows = list(
        csv.DictReader(
            artifacts.ratewall_financialized_balance_sheet_channel_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(financialized_rows) == len(assumption_rows) * 3
    assert {row["variant"] for row in financialized_rows} == {"low", "base", "high"}
    assert {row["model_use"] for row in financialized_rows} == {
        "optional_financialized_balance_sheet_amplifier_pro_forma_not_main_ratio"
    }
    assert {row["claim_boundary"] for row in financialized_rows} == {
        "financialized_balance_sheet_channel_assumption_mode_not_causal_financialization"
    }
    assert all(
        Decimal(row["pro_forma_offset_ratio"])
        >= Decimal(row["base_ratewall_offset_ratio"])
        for row in financialized_rows
    )
    for disabled_field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[disabled_field] for row in financialized_rows} == {"false"}
    disabled_financialization_fields = (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    )
    financialization_registry_rows = list(
        csv.DictReader(
            artifacts.ratewall_financialization_proxy_registry_table.open(
                encoding="utf-8"
            )
        )
    )
    registry = SourceRegistry.from_path("configs/sources.yml")
    valid_source_tokens = set(registry.sources) | set(registry.series)
    registry_proxy_ids = {row["proxy_id"] for row in financialization_registry_rows}
    assert len(financialization_registry_rows) >= 14
    assert {
        "closer_to_wall",
        "farther_from_wall",
        "ambiguous_two_sided",
    } <= {row["mechanism_direction"] for row in financialization_registry_rows}
    assert {
        row["enters_main_ratio"] for row in financialization_registry_rows
    } == {"false"}
    assert {
        row["causal_financialization_claim_enabled"]
        for row in financialization_registry_rows
    } == {"false"}
    assert {
        "household_safe_asset_stock_exposure",
        "deposit_mmf_substitution_surface",
        "firm_rollover_pressure",
        "private_credit_bdc_context",
    } <= {row["proxy_id"] for row in financialization_registry_rows}
    for row in financialization_registry_rows:
        assert row["source_backed_scope"]
        assert row["assumption_mode_scope"]
        assert row["blocked_scope"]
        assert row["expected_backend_artifact"]
        assert row["context_artifacts"]
        for source_token in row["source_id"].split(";"):
            assert source_token in valid_source_tokens

    financialization_source_gate_rows = list(
        csv.DictReader(
            artifacts.ratewall_financialization_proxy_source_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(financialization_source_gate_rows) == len(
        financialization_registry_rows
    )
    assert {
        row["promotion_gate_passed"] for row in financialization_source_gate_rows
    } == {"false"}
    assert {
        row["final_status"] for row in financialization_source_gate_rows
    } == {"fail_closed_context_only"}
    for field in disabled_financialization_fields:
        assert {row[field] for row in financialization_source_gate_rows} == {"false"}
    assert {row["proxy_id"] for row in financialization_source_gate_rows} == (
        registry_proxy_ids
    )
    assert "pass" not in {
        row["opposite_sign_pairing_gate"] for row in financialization_source_gate_rows
    }
    assert {
        row["opposite_sign_pairing_gate"] for row in financialization_source_gate_rows
    } <= {
        "not_applicable",
        "requires_pairing_on_use",
        "paired_surface_available_context_only",
    }
    financialization_source_gate_alias_rows = list(
        csv.DictReader(
            artifacts.ratewall_financialization_source_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    assert financialization_source_gate_alias_rows == financialization_source_gate_rows

    household_safe_asset_rows = list(
        csv.DictReader(
            artifacts.ratewall_household_safe_asset_exposure_panel_table.open(
                encoding="utf-8"
            )
        )
    )
    deposit_mmf_rows = list(
        csv.DictReader(
            artifacts.ratewall_deposit_mmf_substitution_surface_table.open(
                encoding="utf-8"
            )
        )
    )
    private_credit_context_rows = list(
        csv.DictReader(
            artifacts.ratewall_private_credit_bdc_context_table.open(encoding="utf-8")
        )
    )
    assert {row["mechanism_direction"] for row in household_safe_asset_rows} == {
        "closer_to_wall"
    }
    assert {row["mechanism_direction"] for row in deposit_mmf_rows} == {
        "ambiguous_two_sided"
    }
    assert {row["mechanism_direction"] for row in private_credit_context_rows} == {
        "farther_from_wall"
    }
    for rows in (
        household_safe_asset_rows,
        deposit_mmf_rows,
        private_credit_context_rows,
    ):
        assert rows
        assert {row["enters_main_ratio"] for row in rows} == {"false"}
        assert {row["promotion_gate_passed"] for row in rows} == {"false"}
        for field in disabled_financialization_fields:
            assert {row[field] for row in rows} == {"false"}

    financialization_protocol_rows = list(
        csv.DictReader(
            artifacts.ratewall_financialization_restricted_protocols_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(financialization_protocol_rows) >= 5
    assert all(
        row["identification_design"]
        and row["promotion_pass_rule"]
        and row["abandonment_rule"]
        for row in financialization_protocol_rows
    )
    assert {row["claim_boundary"] for row in financialization_protocol_rows} == {
        "restricted_protocol_design_only_not_current_evidence"
    }

    financialization_overlap_rows = list(
        csv.DictReader(
            artifacts.ratewall_financialization_overlap_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert financialization_overlap_rows
    assert {row["audit_status"] for row in financialization_overlap_rows} == {"pass"}
    assert {row["formula_change_allowed"] for row in financialization_overlap_rows} == {
        "false"
    }
    assert {row["enters_main_ratio"] for row in financialization_overlap_rows} == {
        "false"
    }
    assert {row["proxy_id"] for row in financialization_overlap_rows} == (
        registry_proxy_ids
    )
    financialization_double_count_rows = list(
        csv.DictReader(
            artifacts.ratewall_financialization_double_count_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["proxy_id"] for row in financialization_double_count_rows} == (
        registry_proxy_ids
    )
    financialization_traceability_rows = list(
        csv.DictReader(
            artifacts.ratewall_financialization_artifact_traceability_matrix_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["proxy_id"] for row in financialization_traceability_rows} == (
        registry_proxy_ids
    )
    assert {row["double_count_coverage_status"] for row in financialization_traceability_rows} == {
        "covered"
    }
    assert {row["release_layer"] for row in financialization_traceability_rows} == {
        "financialization_proxy_context_design"
    }
    for row in financialization_traceability_rows:
        assert row["source_backed_scope"]
        assert row["assumption_mode_scope"]
        assert row["blocked_scope"]
        assert row["expected_backend_artifact"]
        assert row["context_artifacts"]
        assert row["enters_main_ratio"] == "false"
        assert row["promotion_gate_passed"] == "false"
        for field in disabled_financialization_fields:
            assert row[field] == "false"
    backend_expansion_rows = list(
        csv.DictReader(
            artifacts.ratewall_backend_expansion_context_registry_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {
        "household_within_distribution_safe_asset_capture",
        "deposit_pass_through_dispersion_conditioner",
        "brokerage_tbill_mmf_access",
        "firm_interest_income_expense_balance",
        "firm_debt_maturity_wall",
        "bdc_private_credit_stress_marker",
        "cre_maturity_refi_pressure",
        "bnpl_zero_interest_float",
        "safe_asset_substitution_pairing",
        "composite_financialization_index",
        "public_aggregate_causal_financialization_regression",
        "bank_nim_credit_supply",
        "tax_timing_interest_income",
        "foreign_holder_interest_leakage",
        "public_finance_remittance_timing_stress_grid",
        "insurance_pension_asset_liability",
        "housing_lockin_cashflow",
        "dealer_inventory_carry",
    } == {row["context_id"] for row in backend_expansion_rows}
    assert {
        "financialization_expansion",
        "financialization_avoidance",
        "additional_rate_channel",
    } == {row["candidate_group"] for row in backend_expansion_rows}
    assert {row["enters_main_ratio"] for row in backend_expansion_rows} == {
        "false"
    }
    assert {row["promotion_gate_passed"] for row in backend_expansion_rows} == {
        "false"
    }
    for row in backend_expansion_rows:
        assert row["source_backed_scope"]
        assert row["assumption_mode_scope"]
        assert row["blocked_scope"]
        assert row["expected_model_hook"]
        for source_token in row["source_ids"].split(";"):
            if source_token == "not_applicable":
                continue
            assert source_token in valid_source_tokens
        for field in disabled_financialization_fields:
            assert row[field] == "false"
    backend_expansion_artifact_paths = [
        artifacts.ratewall_household_within_distribution_safe_asset_capture_context_table,
        artifacts.ratewall_deposit_pass_through_dispersion_conditioner_table,
        artifacts.ratewall_brokerage_tbill_mmf_access_context_table,
        artifacts.ratewall_firm_interest_income_expense_balance_context_table,
        artifacts.ratewall_firm_debt_maturity_wall_context_table,
        artifacts.ratewall_bdc_private_credit_stress_marker_context_table,
        artifacts.ratewall_cre_maturity_refi_pressure_context_table,
        artifacts.ratewall_bnpl_zero_interest_float_context_table,
        artifacts.ratewall_safe_asset_substitution_pairing_audit_table,
        artifacts.ratewall_financialization_expansion_avoidance_audit_table,
        artifacts.ratewall_bank_nim_credit_supply_context_table,
        artifacts.ratewall_tax_timing_interest_income_context_table,
        artifacts.ratewall_foreign_holder_interest_leakage_context_table,
        artifacts.ratewall_public_finance_remittance_timing_stress_grid_table,
        artifacts.ratewall_insurance_pension_asset_liability_context_table,
        artifacts.ratewall_housing_lockin_cashflow_context_table,
        artifacts.ratewall_dealer_inventory_carry_context_table,
    ]
    for path in backend_expansion_artifact_paths:
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        assert rows
        assert {row["artifact_name"] for row in rows} == {path.name}
        assert {row["enters_main_ratio"] for row in rows} == {"false"}
        assert {row["promotion_gate_passed"] for row in rows} == {"false"}
        for field in disabled_financialization_fields:
            assert {row[field] for row in rows} == {"false"}
    assumption_promotion_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_channel_promotion_decision_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(assumption_promotion_rows) == len(backend_expansion_rows)
    assert {
        "assumption_mode_promoted_now",
        "assumption_mode_promoted_now_as_conditioner",
        "assumption_mode_promoted_now_as_offset_component",
        "assumption_mode_promoted_now_as_paired_drag",
        "phase4_owner_gated_not_current_headline",
        "avoid_do_not_model",
    } <= {row["promotion_decision"] for row in assumption_promotion_rows}
    firm_promotion_rows = {
        row["context_id"]: row
        for row in assumption_promotion_rows
        if row["context_id"]
        in {"firm_interest_income_expense_balance", "firm_debt_maturity_wall"}
    }
    assert {
        row["promotion_decision"] for row in firm_promotion_rows.values()
    } == {"phase4_owner_gated_not_current_headline"}
    assert {
        row["main_ratio_entry_status"] for row in firm_promotion_rows.values()
    } == {"not_entered_current_main_ratio_until_owner_approval"}
    assert all(row["main_ratio_entry_status"] for row in assumption_promotion_rows)
    for field in disabled_financialization_fields:
        assert {row[field] for row in assumption_promotion_rows} == {"false"}
    promoted_contribution_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_promoted_channel_contributions_table.open(
                encoding="utf-8"
            )
        )
    )
    assert promoted_contribution_rows
    assert {
        "household_safe_yield_capture",
        "deposit_mmf_substitution_offset",
        "deposit_mmf_substitution_drag",
        "firm_liquid_asset_cushion",
        "firm_rollover_pressure_drag",
    } == {row["module_id"] for row in promoted_contribution_rows}
    assert any(
        row["assumption_mode_promotion_status"] == "active_assumption_mode_terms"
        and Decimal(row["signed_numerator_effect_bil"]) != Decimal("0")
        for row in promoted_contribution_rows
    )
    firm_contribution_rows = [
        row
        for row in promoted_contribution_rows
        if row["module_id"]
        in {"firm_liquid_asset_cushion", "firm_rollover_pressure_drag"}
    ]
    assert firm_contribution_rows
    assert {
        row["assumption_mode_promotion_status"] for row in firm_contribution_rows
    } == {"phase4_owner_gated_not_current_headline"}
    assert {
        Decimal(row["signed_numerator_effect_bil"])
        for row in firm_contribution_rows
    } == {Decimal("0")}
    assert {row["source_mode_label"] for row in promoted_contribution_rows} == {
        "Assumption Mode",
        "Assumption Mode candidate",
    }
    for field in disabled_financialization_fields:
        assert {row[field] for row in promoted_contribution_rows} == {"false"}
    overlap_guardrail_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_overlap_guardrail_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert overlap_guardrail_rows
    assert "blocked_legacy_explicit_overlap" not in {
        row["stacking_status"] for row in overlap_guardrail_rows
    }
    for field in disabled_financialization_fields:
        assert {row[field] for row in overlap_guardrail_rows} == {"false"}
    sidecar_decision_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_sidecar_channel_decision_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {
        "foreign_holder_interest_leakage",
        "tax_timing_interest_income",
        "fast_repricing_consumer_credit_drag",
        "cre_maturity_refi_pressure",
        "private_credit_ndfi_drag",
        "denominator_sidecar_overlap_discount",
        "housing_lockin_payment_shield",
        "public_finance_remittance_timing_stress_grid",
        "insurance_pension_asset_liability",
    } == {row["channel_id"] for row in sidecar_decision_rows}
    assert {row["canonical_ratio_entry"] for row in sidecar_decision_rows} == {"false"}
    for field in disabled_financialization_fields:
        assert {row[field] for row in sidecar_decision_rows} == {"false"}
    sidecar_contribution_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_sidecar_contributions_table.open(
                encoding="utf-8"
            )
        )
    )
    assert sidecar_contribution_rows
    assert {row["canonical_ratio_entry"] for row in sidecar_contribution_rows} == {
        "false"
    }
    assert any(
        row["assumption_set"] == "assumption_mode_combined_recipient_leakage_wrappers"
        and row["channel_id"] == "tax_timing_interest_income"
        and Decimal(row["channel_value_bil"]) > Decimal("0")
        for row in sidecar_contribution_rows
    )
    assert any(
        row["assumption_set"]
        == "assumption_mode_combined_denominator_sidecar_overlap_discounted"
        and row["channel_id"] == "denominator_sidecar_overlap_discount"
        and Decimal(row["channel_value_bil"]) > Decimal("0")
        for row in sidecar_contribution_rows
    )
    combined_denominator_sidecar = next(
        row
        for row in wall_hit_rows
        if row["assumption_set"]
        == "assumption_mode_combined_denominator_sidecar_overlap_discounted"
    )
    assert (
        combined_denominator_sidecar["denominator_sidecar_overlap_discount_status"]
        == "active_multi_channel_discount"
    )
    assert (
        Decimal(
            combined_denominator_sidecar[
                "denominator_sidecar_overlap_discount_bil"
            ]
        )
        > Decimal("0")
    )
    positive_drag_total = Decimal(
        combined_denominator_sidecar[
            "denominator_sidecar_positive_drag_total_bil"
        ]
    )
    assert positive_drag_total == (
        Decimal(combined_denominator_sidecar["consumer_credit_drag_sidecar_bil"])
        + Decimal(combined_denominator_sidecar["cre_refi_drag_sidecar_bil"])
        + Decimal(combined_denominator_sidecar["private_credit_ndfi_drag_sidecar_bil"])
    )
    assert (
        Decimal(combined_denominator_sidecar["denominator_sidecar_overlap_discount_bil"])
        <= positive_drag_total
    )
    sidecar_reasonableness_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_sidecar_reasonableness_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert sidecar_reasonableness_rows
    assert {row["canonical_ratio_changed"] for row in sidecar_reasonableness_rows} == {
        "false"
    }
    assert {
        "recipient_leakage_drag_share_of_countervailing",
        "positive_denominator_sidecar_drag_share_of_conventional_drag",
        "net_denominator_sidecar_adjustment_share_of_conventional_drag",
        "overlap_discount_share_of_positive_sidecar_drag",
        "recipient_leakage_ratio_gap_vs_canonical",
        "denominator_sidecar_ratio_gap_vs_canonical",
        "max_static_sidecar_ratio_gap_vs_canonical",
        "active_sidecar_contribution_count",
    } <= {row["audit_metric"] for row in sidecar_reasonableness_rows}
    combined_leakage_gap = next(
        row
        for row in sidecar_reasonableness_rows
        if row["assumption_set"]
        == "assumption_mode_combined_recipient_leakage_wrappers"
        and row["audit_metric"] == "recipient_leakage_ratio_gap_vs_canonical"
    )
    assert Decimal(combined_leakage_gap["metric_value"]) == Decimal("0")
    recipient_conversion_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_recipient_conversion_overlap_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert recipient_conversion_rows
    assert "fail_unguarded_recipient_conversion_stack" not in {
        row["recipient_conversion_overlap_status"] for row in recipient_conversion_rows
    }
    assert any(
        Decimal(row["canonical_private_recipient_demand_offset_bil"]) > 0
        and Decimal(row["explicit_safe_yield_mmf_offset_bil"]) > 0
        and row["recipient_conversion_overlap_status"]
        == "pass_explicit_incremental_assumption_labeled"
        for row in recipient_conversion_rows
    )
    recipient_leakage_basis_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_recipient_leakage_absorber_basis_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert recipient_leakage_basis_rows
    assert {row["canonical_ratio_entry"] for row in recipient_leakage_basis_rows} == {
        "false"
    }
    assert {
        row["recipient_leakage_absorber_basis"]
        for row in recipient_leakage_basis_rows
    } == {"canonical_tax_adjusted_pre_fiscal_tga_recipient_offset"}
    assert all(
        Decimal(row["pre_absorber_recipient_leakage_drag_bil"]) > Decimal("0")
        for row in recipient_leakage_basis_rows
    )
    sidecar_frontier_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_sidecar_frontier_table.open(
                encoding="utf-8"
            )
        )
    )
    assert sidecar_frontier_rows
    assert {row["canonical_ratio_entry"] for row in sidecar_frontier_rows} == {
        "false"
    }
    assert {
        row["canonical_wall_hit_label_preserved"] for row in sidecar_frontier_rows
    } == {"true"}
    assert {row["secondary_ratio_not_classifier"] for row in sidecar_frontier_rows} == {
        "true"
    }
    assert {
        "recipient_leakage_secondary_ratio",
        "denominator_sidecar_secondary_ratio",
    } <= {row["sidecar_metric_id"] for row in sidecar_frontier_rows}
    frontier_ranks = [
        int(row["frontier_rank"]) for row in sidecar_frontier_rows
    ]
    assert frontier_ranks == list(range(1, len(sidecar_frontier_rows) + 1))
    assert any(
        row["assumption_set"]
        == "assumption_mode_combined_denominator_sidecar_overlap_discounted"
        and row["sidecar_metric_id"] == "denominator_sidecar_secondary_ratio"
        and row["overlap_discount_status"] == "active_multi_channel_discount"
        and Decimal(row["overlap_discount_bil"]) > Decimal("0")
        for row in sidecar_frontier_rows
    )
    assert all(
        row["secondary_label_differs_from_canonical"]
        == str(
            row["sidecar_wall_hit_under_secondary_ratio"]
            != row["canonical_wall_hit_under_assumptions"]
        ).lower()
        for row in sidecar_frontier_rows
    )
    sidecar_driver_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_sidecar_driver_decomposition_table.open(
                encoding="utf-8"
            )
        )
    )
    assert sidecar_driver_rows
    assert {row["canonical_ratio_entry"] for row in sidecar_driver_rows} == {
        "false"
    }
    assert {
        "recipient_leakage_secondary_ratio",
        "denominator_sidecar_secondary_ratio",
    } <= {row["sidecar_metric_id"] for row in sidecar_driver_rows}
    assert "dynamic_sidecar_value" not in {
        row["sidecar_metric_id"] for row in sidecar_driver_rows
    }
    assert {row["sidecar_additivity_scope"] for row in sidecar_driver_rows} == {
        "additive_static_sidecar_driver"
    }
    assert any(
        row["channel_id"] == "denominator_sidecar_overlap_discount"
        and row["overlap_discount_status"] == "active_multi_channel_discount"
        for row in sidecar_driver_rows
    )
    dynamic_sidecar_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_dynamic_sidecar_paths_table.open(
                encoding="utf-8"
            )
        )
    )
    assert dynamic_sidecar_rows
    assert {row["canonical_dynamic_path_changed"] for row in dynamic_sidecar_rows} == {
        "false"
    }
    assert {
        "dynamic_public_finance_current_support",
        "dynamic_public_finance_future_drag",
        "dynamic_pension_contribution_relief_low",
        "dynamic_pension_contribution_relief_high",
        "dynamic_retirement_yield_spend_low",
        "dynamic_retirement_yield_spend_high",
    } <= {row["dynamic_sidecar_id"] for row in dynamic_sidecar_rows}
    assert "public_finance_remittance_timing_grid" not in {
        row["dynamic_sidecar_id"] for row in dynamic_sidecar_rows
    }
    assert all(
        row["dynamic_sidecar_family"]
        and row["variant_label"]
        and row["additivity_scope"] == "alternative_dynamic_variant_not_additive"
        and row["denominator_basis"]
        and row["lag_applied_status"]
        for row in dynamic_sidecar_rows
    )
    assert any(
        row["dynamic_sidecar_id"] == "dynamic_public_finance_current_support"
        and row["mechanism_direction"] == "closer_to_wall"
        for row in dynamic_sidecar_rows
    )
    assert any(
        row["dynamic_sidecar_id"] == "dynamic_public_finance_future_drag"
        and Decimal(row["sidecar_value_bil"]) > Decimal("0")
        and row["mechanism_direction"] == "farther_from_wall"
        for row in dynamic_sidecar_rows
    )
    dynamic_driver_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_dynamic_sidecar_driver_decomposition_table.open(
                encoding="utf-8"
            )
        )
    )
    assert dynamic_driver_rows
    assert {row["canonical_dynamic_path_changed"] for row in dynamic_driver_rows} == {
        "false"
    }
    assert {row["absolute_effect_share"] for row in dynamic_driver_rows} == {
        "not_applicable"
    }
    assert {row["additivity_scope"] for row in dynamic_driver_rows} == {
        "alternative_dynamic_variant_not_additive"
    }
    dynamic_rank_groups: dict[tuple[str, str], list[int]] = {}
    for row in dynamic_driver_rows:
        dynamic_rank_groups.setdefault((row["scenario"], row["period"]), []).append(
            int(row["driver_rank"])
        )
    for ranks in dynamic_rank_groups.values():
        assert ranks == list(range(1, len(ranks) + 1))
    for field in disabled_financialization_fields:
        assert {row[field] for row in sidecar_contribution_rows} == {"false"}
        assert {row[field] for row in sidecar_reasonableness_rows} == {"false"}
        assert {row[field] for row in recipient_conversion_rows} == {"false"}
        assert {row[field] for row in recipient_leakage_basis_rows} == {"false"}
        assert {row[field] for row in sidecar_frontier_rows} == {"false"}
        assert {row[field] for row in sidecar_driver_rows} == {"false"}
        assert {row[field] for row in dynamic_sidecar_rows} == {"false"}
        assert {row[field] for row in dynamic_driver_rows} == {"false"}
    paper_financialization_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_financialization_interpretation_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {
        "safe_asset_income_capture",
        "borrower_fragility_refinancing_pressure",
        "paired_two_sided_financialization",
        "financialization_freeze_guardrail",
    } == {row["interpretation_row"] for row in paper_financialization_rows}
    assert {
        "closer_to_wall",
        "farther_from_wall",
        "ambiguous_two_sided",
    } <= {row["mechanism_direction"] for row in paper_financialization_rows}
    assert {row["main_ratio_inclusion"] for row in paper_financialization_rows} == {
        "false"
    }
    assert {row["composite_index_allowed"] for row in paper_financialization_rows} == {
        "false"
    }
    assert {row["promotion_gate_passed"] for row in paper_financialization_rows} == {
        "false"
    }
    assert all(row["paper_safe_sentence"] for row in paper_financialization_rows)
    assert all(row["paper_forbidden_sentence"] for row in paper_financialization_rows)
    for field in disabled_financialization_fields:
        assert {row[field] for row in paper_financialization_rows} == {"false"}
    financialization_interpretation_memo = (
        artifacts.ratewall_financialization_interpretation_memo.read_text(
            encoding="utf-8"
        )
    )
    assert "cannot be collapsed into a single financialization scalar" in (
        financialization_interpretation_memo
    )
    equity_channel_rows = list(
        csv.DictReader(
            artifacts.ratewall_equity_transmission_channel_map_table.open(
                encoding="utf-8"
            )
        )
    )
    equity_exposure_rows = list(
        csv.DictReader(
            artifacts.ratewall_equity_exposure_matrix_table.open(encoding="utf-8")
        )
    )
    equity_diagnostic_rows = list(
        csv.DictReader(
            artifacts.ratewall_equity_sensitivity_diagnostic_table.open(
                encoding="utf-8"
            )
        )
    )
    equity_claim_rows = list(
        csv.DictReader(
            artifacts.ratewall_equity_claim_status_table.open(encoding="utf-8")
        )
    )
    equity_workplan_rows = list(
        csv.DictReader(
            artifacts.ratewall_equity_evidence_workplan_table.open(encoding="utf-8")
        )
    )
    assert {
        "discount_rate_duration",
        "cash_interest_income",
        "debt_repricing_rollover",
        "sector_rotation_and_financial_sector_split",
    } <= {row["channel"] for row in equity_channel_rows}
    assert {
        "cash_rich_mega_cap",
        "leveraged_small_or_external_finance_dependent_firm",
        "large_bank_or_deposit_franchise",
    } <= {row["firm_or_sector_type"] for row in equity_exposure_rows}
    assert {
        "low_debt_low_liquidity",
        "high_debt_high_liquidity",
    } <= {row["ratewall_state"] for row in equity_diagnostic_rows}
    assert {
        "higher_rates_always_lower_stocks",
        "broad_indexes_become_rate_resistant_near_ratewall",
        "ratewall_proves_monetary_policy_stops_working",
    } <= {row["claim"] for row in equity_claim_rows}
    assert {
        "firm_cash_assets",
        "debt_maturity_rollover",
        "sector_returns",
        "financial_sector_split",
        "identified_monetary_shock_designs",
    } == {row["evidence_area"] for row in equity_workplan_rows}
    assert all(row["source_specific_artifacts"] for row in equity_workplan_rows)
    assert all(
        row["source_specific_series_or_table_ids"] for row in equity_workplan_rows
    )
    assert all(row["source_specific_urls_or_docs"] for row in equity_workplan_rows)
    assert all(
        row["source_specific_citation_or_design_handles"]
        for row in equity_workplan_rows
    )
    assert all(row["source_specific_evidence_status"] for row in equity_workplan_rows)
    assert {
        row["status"]
        for row in equity_claim_rows
        if row["claim"] == "ratewall_proves_monetary_policy_stops_working"
    } == {"blocked"}
    for rows in (
        equity_channel_rows,
        equity_exposure_rows,
        equity_diagnostic_rows,
        equity_claim_rows,
        equity_workplan_rows,
    ):
        assert rows
        for disabled_field in (
            "empirical_claim_enabled",
            "policy_failure_claim_enabled",
            "pricing_output_enabled",
            "incidence_claim_enabled",
            "welfare_claim_enabled",
            "holder_allocation_enabled",
            "raw_rate_shock_enabled",
            "causal_financialization_claim_enabled",
        ):
            assert {row[disabled_field] for row in rows} == {"false"}
    assert artifacts.ratewall_equity_transmission_attenuation_memo.exists()
    equity_memo = artifacts.ratewall_equity_transmission_attenuation_memo.read_text(
        encoding="utf-8"
    )
    assert "not a pricing model" in equity_memo
    assert "secondary equity-market diagnostic" in equity_memo
    assert artifacts.ratewall_equity_evidence_workplan.exists()
    equity_workplan_text = artifacts.ratewall_equity_evidence_workplan.read_text(
        encoding="utf-8"
    )
    assert "identified monetary-shock designs" in equity_workplan_text
    assert "does not enter the main offset ratio" in equity_workplan_text
    denominator_pack_rows = [
        row
        for row in parameter_pack_rows_
        if row["parameter"]
        in {
            "borrowing_cost_drag_share",
            "credit_supply_drag_share",
            "asset_price_drag_share",
            "expectations_drag_share",
            "exchange_rate_external_drag_share",
        }
    ]
    assert len(denominator_pack_rows) == 5
    assert all(row["candidate_source_literature"] for row in denominator_pack_rows)
    assert all(row["uncertainty_status"] for row in denominator_pack_rows)
    for field in (
        "citation_handle",
        "source_family",
        "identification_design",
        "horizon_relevance",
        "evidence_strength",
        "prior_basis",
        "external_review_status",
        "evidence_upgrade_blocker",
        "upgrade_gate",
        "model_use",
        "review_question",
        "evidence_needed",
        "claim_boundary",
    ):
        assert all(row[field] for row in denominator_pack_rows)
    literature_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_literature_matrix_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(literature_rows) == 5
    assert {
        "borrowing_cost_drag_share",
        "credit_supply_drag_share",
        "asset_price_drag_share",
        "expectations_drag_share",
        "exchange_rate_external_drag_share",
    } == {row["denominator_parameter"] for row in literature_rows}
    assert {row["claim_boundary"] for row in literature_rows} == {
        "denominator_literature_matrix_not_empirical_proof"
    }
    assert all(row["admissible_shock_requirement"] for row in literature_rows)
    for field in (
        "citation_handle",
        "source_family",
        "identification_design",
        "horizon_relevance",
        "evidence_strength",
        "prior_basis",
        "external_review_status",
        "evidence_upgrade_blocker",
        "upgrade_gate",
    ):
        assert all(row[field] for row in literature_rows)
    joint_uncertainty_rows = list(
        csv.DictReader(
            artifacts.ratewall_split_denominator_joint_uncertainty_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(joint_uncertainty_rows) == len(assumption_rows) * 5
    assert {row["stress_family"] for row in joint_uncertainty_rows} == {
        "joint_composition_and_total_drag_amplitude_stress"
    }
    assert {row["denominator_share_sum"] for row in joint_uncertainty_rows} == {"1.00"}
    assert {row["claim_boundary"] for row in joint_uncertainty_rows} == {
        "joint_denominator_uncertainty_assumption_mode_not_empirical_estimate"
    }
    for disabled_field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[disabled_field] for row in joint_uncertainty_rows} == {"false"}
    joint_stability_rows = list(
        csv.DictReader(
            artifacts.ratewall_split_denominator_joint_regime_stability_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(joint_stability_rows) == len(assumption_rows)
    assert {row["claim_boundary"] for row in joint_stability_rows} == {
        "joint_denominator_regime_stability_assumption_mode_not_empirical_threshold"
    }
    assert "classification_sensitive" in {
        row["overall_denominator_stability_group"] for row in joint_stability_rows
    }
    for disabled_field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[disabled_field] for row in joint_stability_rows} == {"false"}
    classifier_rows = list(
        csv.DictReader(
            artifacts.ratewall_denominator_classifier_comparison_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(classifier_rows) == len(assumption_rows)
    assert {row["claim_boundary"] for row in classifier_rows} == {
        "denominator_classifier_comparison_assumption_mode_not_empirical_threshold"
    }
    assert all(row["current_classifier_decision"] for row in classifier_rows)
    assert all(row["dominant_split_denominator_component"] for row in classifier_rows)
    assert all(row["classification_change_driver_type"] for row in classifier_rows)
    assert all(
        row["promotion_status"] == "prototype_robustness_only"
        for row in classifier_rows
    )
    assert all(
        row["decisive_denominator_channel"] == "split_denominator_total_drag_multiplier"
        for row in classifier_rows
        if row["classification_change_driver_type"] == "total_drag_amplitude"
    )
    assert all(
        row["most_classification_sensitive_denominator_component"]
        for row in classifier_rows
    )
    assert all(row["weakest_prior_status"] for row in classifier_rows)
    assert all(
        "Assumption Mode classifier result" in row["writing_safe_interpretation"]
        for row in classifier_rows
    )
    assert {row["main_classifier_eligible"] for row in classifier_rows} == {"false"}
    assert all(row["reason_not_promoted"] for row in classifier_rows)
    assert all(row["channel_evidence_status"] for row in classifier_rows)
    assert all(row["joint_stability_required"] for row in classifier_rows)
    for field in (
        "scalar_regime_group",
        "split_regime_group",
        "joint_regime_group_range",
        "hit_cutoff",
        "near_wall_cutoff",
        "attenuated_cutoff",
    ):
        assert all(row[field] for row in classifier_rows)
    assert {row["hit_cutoff"] for row in classifier_rows} == {"1.0"}
    assert {row["near_wall_cutoff"] for row in classifier_rows} == {"0.75"}
    assert {row["attenuated_cutoff"] for row in classifier_rows} == {"0.5"}
    for disabled_field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[disabled_field] for row in classifier_rows} == {"false"}
    readiness_rows = list(
        csv.DictReader(
            artifacts.ratewall_backend_model_readiness_gate_table.open(encoding="utf-8")
        )
    )
    assert readiness_rows
    assert {
        "backend_model_packet",
        "denominator_priors",
        "hard_boundary_switches",
        "interest_channel_completion_gates",
        "denominator_evidence_upgrade_boundary",
        "tdsp_diagnostic_family_completion_boundary",
        "joint_wall_probability_boundary",
        "assumption_mode_v1_completion",
        "dynamic_assumption_mode_scenario_engine",
        "assumption_mode_v1_stage_completion",
    } <= {row["gate_component"] for row in readiness_rows}
    assert {row["writing_pdf_ready"] for row in readiness_rows} == {"false"}
    assert {row["empirical_promotion_enabled"] for row in readiness_rows} == {"false"}
    assert "ready_for_substantive_model_audit" in next(
        row["gate_status"]
        for row in readiness_rows
        if row["gate_component"] == "backend_model_packet"
    )
    source_specific_recipient_blockers = (
        "ratewall_final_recipient_current_demand_bridge_attempt.csv",
        "blocked_no_admissible_source_backed_final_recipient_current_demand_bridge",
        "exact next source fields live in that bridge-attempt artifact",
        "blocked_no_recipient_current_demand_bridge",
        "no_source_backed_mapping_from_tdcest_gross_interest_cashflow_to_"
        "final_recipient_current_demand",
        "blocked_bank_iorb_timing_matrix_requires_behavior_bridge",
    )
    interest_channel_readiness = next(
        row
        for row in readiness_rows
        if row["gate_component"] == "interest_channel_completion_gates"
    )
    for blocker in source_specific_recipient_blockers:
        assert blocker in interest_channel_readiness["evidence"]
    joint_probability_boundary_terms = (
        "ratewall_joint_wall_probability_summary.csv",
        "conditional_named_grid_share_not_empirical_or_posterior_probability",
        "object-family wall-hit shares stay separate",
        "empirical probability",
        "posterior probability",
        "canonical RW_Y",
        "Evidence Mode",
        "prior updates remain blocked",
    )
    joint_probability_readiness = next(
        row
        for row in readiness_rows
        if row["gate_component"] == "joint_wall_probability_boundary"
    )
    assert (
        joint_probability_readiness["gate_status"]
        == "conditional_grid_surface_ready_not_empirical_probability"
    )
    for term in joint_probability_boundary_terms:
        assert term in joint_probability_readiness["evidence"]
    denominator_evidence_upgrade_terms = (
        "ratewall_denominator_evidence_upgrade_priority_queue.csv",
        "ratewall_denominator_evidence_upgrade_tier1_workplan.csv",
        "ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv",
        "denominator_evidence_upgrade_queue_nonpromotional_source_acquisition_only",
        "blocked denominator source-design work",
        "unresolved evidence actions",
        "denominator prior narrowing",
        "split-denominator promotion",
        "Evidence Mode",
        "canonical ratio entry",
    )
    tdsp_completion_gate_terms = (
        "ratewall_tdsp_diagnostic_family_completion_gate.csv",
        "fail-closed TDSP completion-family",
        "audited rows",
        "ledger-covered audit rows",
        "original and",
        "refreshed diagnostic estimates",
        "source/runtime admission gaps",
        "policy-path blockers",
        "no admitted TDSP-to-current-demand/GDP-share conversion",
        "promotion_switch_violation_count=0",
    )
    denominator_upgrade_readiness = next(
        row
        for row in readiness_rows
        if row["gate_component"] == "denominator_evidence_upgrade_boundary"
    )
    assert (
        denominator_upgrade_readiness["gate_status"]
        == "diagnostic_source_acquisition_queue_ready_not_prior_narrowing"
    )
    for term in denominator_evidence_upgrade_terms:
        assert term in denominator_upgrade_readiness["evidence"]
    tdsp_completion_readiness = next(
        row
        for row in readiness_rows
        if row["gate_component"] == "tdsp_diagnostic_family_completion_boundary"
    )
    assert (
        tdsp_completion_readiness["gate_status"]
        == "tdsp_diagnostic_family_complete_fail_closed_not_promotion"
    )
    assert (
        tdsp_completion_readiness["failure_action"]
        == "only_reopen_tdsp_with_reviewed_policy_path_vector_current_demand_"
        "conversion_uncertainty_and_independent_replication"
    )
    for term in tdsp_completion_gate_terms:
        assert term in tdsp_completion_readiness["evidence"]
    central_tdc_guardrail_terms = (
        "ru_flow_tier2_tdc_core_object",
        "central TDC-family scenario object",
        "route/final-recipient gaps",
        "not TDC exclusion or quarantine gates",
        "DU-flow is not a prerequisite",
    )
    assumption_mode_completion = next(
        row
        for row in readiness_rows
        if row["gate_component"] == "assumption_mode_v1_completion"
    )
    for term in central_tdc_guardrail_terms:
        assert term in assumption_mode_completion["evidence"]
    chapter_self_audit_rows = list(
        csv.DictReader(
            artifacts.ratewall_chapter_readiness_self_audit_table.open(encoding="utf-8")
        )
    )
    assert {
        "chapter_regime_label_coverage",
        "prior_stack_semantics",
        "numerator_entry_semantics",
        "denominator_driver_semantics",
        "scenario_ladder_semantics",
        "interest_channel_expansion_scaffolds",
        "source_gated_channel_blockers",
        "source_specific_evidence_upgrade_queue",
        "high_priority_source_bridge",
        "mspd_table3_bucket_repricing_gate",
        "treasury_recipient_leakage_source_gate",
        "conventional_drag_source_design_gate",
        "denominator_response_gate_attempt",
        "denominator_aligned_response_panel_scaffold",
        "denominator_event_outcome_cell_diagnostic",
        "denominator_event_outcome_panel_value_diagnostic",
        "denominator_panel_design_test_diagnostic",
        "denominator_pretrend_placebo_diagnostic",
        "denominator_shock_relevance_diagnostic",
        "denominator_sign_consistency_diagnostic",
        "denominator_horizon_sensitivity_diagnostic",
        "denominator_outlier_window_robustness_diagnostic",
        "denominator_design_readiness_decision",
        "denominator_formal_design_test_result_scaffold",
        "denominator_formal_design_test_result",
        "source_gate_prior_narrowing_decision",
        "sibling_evidence_bridge",
        "interest_channel_completion_matrix",
        "dynamic_assumption_mode_scenario_engine",
        "hard_boundary_and_external_audit_decision",
        "assumption_mode_v1_stage_completion",
    } == {row["audit_component"] for row in chapter_self_audit_rows}
    assert {row["audit_status"] for row in chapter_self_audit_rows} <= {
        "pass",
        "fail",
    }
    assert all(
        (
            row["external_audit_needed"] == "false"
            and (
                row["chapter_drafting_ready"] == "true"
                or row["audit_component"]
                in {
                    "source_gated_channel_blockers",
                    "source_specific_evidence_upgrade_queue",
                    "high_priority_source_bridge",
                    "mspd_table3_bucket_repricing_gate",
                    "treasury_recipient_leakage_source_gate",
                    "conventional_drag_source_design_gate",
                    "denominator_response_gate_attempt",
                    "denominator_aligned_response_panel_scaffold",
                    "denominator_event_outcome_cell_diagnostic",
                    "denominator_event_outcome_panel_value_diagnostic",
                    "denominator_panel_design_test_diagnostic",
                    "denominator_pretrend_placebo_diagnostic",
                    "denominator_shock_relevance_diagnostic",
                    "denominator_sign_consistency_diagnostic",
                    "denominator_horizon_sensitivity_diagnostic",
                    "denominator_outlier_window_robustness_diagnostic",
                    "denominator_design_readiness_decision",
                    "denominator_formal_design_test_result_scaffold",
                    "denominator_formal_design_test_result",
                    "source_gate_prior_narrowing_decision",
                    "sibling_evidence_bridge",
                    "dynamic_assumption_mode_scenario_engine",
                    "assumption_mode_v1_stage_completion",
                }
            )
        )
        if row["audit_status"] == "pass"
        else (
            row["external_audit_needed"] == "true"
            and row["chapter_drafting_ready"] == "false"
        )
        for row in chapter_self_audit_rows
    )
    assert all(
        row["claim_boundary"] == "chapter_readiness_self_audit_not_empirical_promotion"
        for row in chapter_self_audit_rows
    )
    frontier_summary_rows = list(
        csv.DictReader(artifacts.ratewall_frontier_summary_table.open(encoding="utf-8"))
    )
    assert frontier_summary_rows
    assert all(row["why_hit_or_nonhit"] for row in frontier_summary_rows)
    regime_rows = list(
        csv.DictReader(artifacts.ratewall_regime_map_table.open(encoding="utf-8"))
    )
    assert {"wall_hit", "robust_non_hit"} <= {
        row["regime_group"] for row in regime_rows
    }
    interpretation_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_interpretation_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(interpretation_rows) == len(assumption_rows)
    assert {row["prose_regime_group"] for row in interpretation_rows} <= {
        "wall_hit",
        "near_wall",
        "materially_attenuated",
        "robust_non_hit",
    }
    assert all(row["chapter_regime_use_label"] for row in interpretation_rows)
    assert {row["chapter_regime_use_label"] for row in interpretation_rows} <= {
        "stable_robust_nonhit",
        "scalar_robust_denominator_sensitive",
        "materially_attenuated_nonhit",
        "near_wall_nonhit",
        "marginal_hit_single_move",
        "stacked_upper_bound_hit",
    }
    assert {"stable_robust_nonhit", "stacked_upper_bound_hit"} <= {
        row["chapter_regime_use_label"] for row in interpretation_rows
    }
    assert all(row["prior_stacking_preview"] for row in interpretation_rows)
    assert {row["empirical_claim_enabled"] for row in interpretation_rows} == {"false"}
    assert {row["policy_failure_claim_enabled"] for row in interpretation_rows} == {
        "false"
    }
    assert {row["pricing_output_enabled"] for row in interpretation_rows} == {"false"}
    assert {row["incidence_claim_enabled"] for row in interpretation_rows} == {"false"}
    assert {row["welfare_claim_enabled"] for row in interpretation_rows} == {"false"}
    assert {
        row["causal_financialization_claim_enabled"] for row in interpretation_rows
    } == {"false"}
    assert all(
        "Assumption Mode scenario diagnostic" in row["writing_safe_interpretation"]
        for row in interpretation_rows
    )
    assert all(
        "not an empirical threshold date" in row["writing_safe_interpretation"]
        for row in interpretation_rows
    )
    for field in (
        "parameter_pack_low",
        "parameter_pack_base",
        "parameter_pack_high",
        "threshold_within_parameter_pack",
        "threshold_pack_status",
    ):
        assert field in interpretation_rows[0]
    prior_stack_rows = list(
        csv.DictReader(
            artifacts.ratewall_prior_stack_diagnostic_table.open(encoding="utf-8")
        )
    )
    assert len(prior_stack_rows) == len(assumption_rows)
    assert {
        "stacked_upper_bound_wall_hit",
        "moderately_stacked_pro_wall",
    } & {row["stacking_classification"] for row in prior_stack_rows}
    assert all(row["prose_regime_group"] for row in prior_stack_rows)
    assert all(row["public_impulse_factorization_status"] for row in prior_stack_rows)
    for field in (
        "within_pack_frontier_count",
        "load_bearing_weighted_stack_score",
        "effective_stack_score",
        "ablation_to_pack_base_ratio",
        "counterfactual_to_pack_base_ratio",
        "full_pack_base_counterfactual_ratio",
        "counterfactual_scope",
        "dominant_single_ablation_delta",
        "dominant_stack_contribution_parameter",
        "dominant_stack_contribution_ratio_delta",
        "near_zero_channel_flag",
        "moderate_pro_wall_distance_score",
        "composite_dependency_flag",
        "prior_count_stack_degree",
        "load_bearing_stack_sensitivity",
        "hit_marginality_class",
    ):
        assert all(row[field] for row in prior_stack_rows)
    assert {row["hit_marginality_class"] for row in prior_stack_rows} <= {
        "stacked_upper_bound_hit",
        "marginal_hit",
        "near_wall_nonhit",
        "materially_attenuated_nonhit",
        "non_hit",
    }
    assert {"stacked_upper_bound_hit", "non_hit"} <= {
        row["hit_marginality_class"] for row in prior_stack_rows
    }
    assert any(
        row["ablation_to_pack_base_ratio"] != row["counterfactual_to_pack_base_ratio"]
        for row in prior_stack_rows
    )
    assert not any(
        "treasury_repricing_pass_through" in row["stacked_parameter_names"]
        for row in prior_stack_rows
    )
    scenario_ladder_rows = list(
        csv.DictReader(artifacts.ratewall_scenario_ladder_table.open(encoding="utf-8"))
    )
    assert [row["ladder_step"] for row in scenario_ladder_rows] == [
        "base",
        "repricing_only",
        "recipient_conversion",
        "low_absorption",
        "clean_near_wall",
        "marginal_hit",
        "upper_bound_stress",
    ]
    scenario_ladder_groups = {row["prose_regime_group"] for row in scenario_ladder_rows}
    assert {"robust_non_hit", "wall_hit"} <= scenario_ladder_groups
    assert scenario_ladder_groups <= {
        "robust_non_hit",
        "materially_attenuated",
        "near_wall",
        "wall_hit",
    }
    for field in (
        "main_formula_effective_changed_parameter_names",
        "main_formula_effective_changed_parameter_count",
        "denominator_robustness_changed_parameter_names",
        "denominator_robustness_changed_parameter_count",
        "main_formula_one_at_a_time_delta_ratio_by_parameter",
        "denominator_robustness_one_at_a_time_delta_ratio_by_parameter",
        "chapter_regime_use_label",
    ):
        assert field in scenario_ladder_rows[0]
    marginal_step = next(
        row for row in scenario_ladder_rows if row["ladder_step"] == "marginal_hit"
    )
    assert marginal_step["is_single_move_step"] == "true"
    assert (
        marginal_step["main_formula_effective_changed_parameter_names"]
        == "treasury_interest_demand_share"
    )
    assert all(
        row["claim_boundary"]
        == "scenario_ladder_assumption_mode_not_empirical_threshold"
        for row in scenario_ladder_rows
    )
    assert {row["empirical_claim_enabled"] for row in prior_stack_rows} == {"false"}
    assert {row["policy_failure_claim_enabled"] for row in prior_stack_rows} == {
        "false"
    }
    assert {row["pricing_output_enabled"] for row in prior_stack_rows} == {"false"}
    assert {row["incidence_claim_enabled"] for row in prior_stack_rows} == {"false"}
    assert {row["welfare_claim_enabled"] for row in prior_stack_rows} == {"false"}
    assert {row["raw_rate_shock_enabled"] for row in prior_stack_rows} == {"false"}
    assert {
        row["causal_financialization_claim_enabled"] for row in prior_stack_rows
    } == {"false"}
    adequacy_rows = list(
        csv.DictReader(
            artifacts.ratewall_model_adequacy_matrix_table.open(encoding="utf-8")
        )
    )
    assert adequacy_rows
    assert {
        "offset_ratio_denominator",
        "wall_hit_examples",
        "conventional_tightening_benchmark",
    } <= {row["model_component"] for row in adequacy_rows}
    assert {row["claim_boundary"] for row in adequacy_rows} == {
        "model_adequacy_review_not_empirical_threshold"
    }
    assert all(row["review_question"] for row in adequacy_rows)
    assert all(row["evidence_to_improve"] for row in adequacy_rows)
    assert all(path.exists() for path in artifacts.assumption_mode_figures)
    assert any(
        path.name == "ratewall_assumption_offset_ratio.svg"
        for path in artifacts.assumption_mode_figures
    )
    minimum_condition_rows = list(
        csv.DictReader(
            artifacts.ratewall_minimum_conditions_to_hit_wall_table.open(
                encoding="utf-8"
            )
        )
    )
    assert minimum_condition_rows
    ranking_rows = list(
        csv.DictReader(
            artifacts.ratewall_frontier_driver_ranking_table.open(encoding="utf-8")
        )
    )
    assert ranking_rows
    assert {row["rank"] for row in ranking_rows if row["assumption_set"]} >= {"1"}
    driver_dominance_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_driver_dominance_matrix_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(driver_dominance_rows) == len(scenario_ladder_rows)
    assert {row["claim_boundary"] for row in driver_dominance_rows} == {
        "driver_dominance_matrix_assumption_mode_not_empirical_estimate"
    }
    assert all(row["dominant_offset_component"] for row in driver_dominance_rows)
    assert all(
        row["top_frontier_driver_parameter"]
        for row in driver_dominance_rows
        if row["wall_status"] == "wall_not_hit_under_assumptions"
    )
    assert all(
        row["top_hit_fragility_parameter"]
        for row in driver_dominance_rows
        if row["wall_status"] == "wall_hit_under_assumptions"
    )
    assert {
        row["top_hit_fragility_status"]
        for row in driver_dominance_rows
        if row["wall_status"] == "wall_hit_under_assumptions"
    } <= {"fragility_threshold_found", "still_hits_at_solver_bound"}
    disabled_driver_fields = (
        "prior_narrowing_allowed",
        "formula_replacement_allowed",
        "main_offset_ratio_changed_this_tranche",
        "dynamic_equation_changed_this_tranche",
        "split_denominator_promotion_allowed",
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    )
    for field in disabled_driver_fields:
        assert {row[field] for row in driver_dominance_rows} == {"false"}
    pairwise_sensitivity_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_pairwise_sensitivity_matrix_table.open(
                encoding="utf-8"
            )
        )
    )
    assert pairwise_sensitivity_rows
    assert {row["claim_boundary"] for row in pairwise_sensitivity_rows} == {
        "pairwise_sensitivity_matrix_assumption_mode_not_empirical_estimate"
    }
    assert any(row["parameter_a"] and row["parameter_b"] for row in pairwise_sensitivity_rows)
    assert {
        row["pair_interaction_class"] for row in pairwise_sensitivity_rows
    } & {
        "additive_or_near_additive",
        "reinforcing_pair",
        "offsetting_pair",
    }
    for field in disabled_driver_fields:
        assert {row[field] for row in pairwise_sensitivity_rows} == {"false"}
    assumption_audit_rows = list(
        csv.DictReader(
            artifacts.ratewall_assumption_mode_claim_boundary_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert assumption_audit_rows
    assert {row["audit_status"] for row in assumption_audit_rows} == {"pass"}
    invariant_audit_rows = list(
        csv.DictReader(
            artifacts.ratewall_backend_invariant_guardrail_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["audit_status"] for row in invariant_audit_rows} <= {"pass", "fail"}
    demo_allowed_invariant_failures = {
        "historical_tdc_selected_series_bridge_execution_noncanonical",
        "historical_tdc_du_ru_methodology_panel_noncanonical",
        "historical_tdc_post_bridge_admission_status_noncanonical",
        "historical_tdc_exact_du_ru_closure_contract_noncanonical",
        "historical_tdc_overlap_identity_closure_contract_noncanonical",
        "conventional_drag_fspdp_value_bearing_exposure_lp_execution_fail_closed",
        "conventional_drag_fspdp_denominator_conversion_uncertainty_boundary_fail_closed",
        "conventional_drag_fspdp_gdp_share_conversion_design_gate_fail_closed",
        "release_archive_reproducibility_audit_manifest_membership",
        "context_surface_materialization_counts_current",
    }
    assert {
        row["audit_item"]
        for row in invariant_audit_rows
        if row["audit_status"] == "fail"
    } <= demo_allowed_invariant_failures
    assert {row["claim_boundary"] for row in invariant_audit_rows} == {
        "backend_invariant_guardrail_audit_not_empirical_promotion"
    }
    assert {
        row["audit_item"] for row in invariant_audit_rows
    } >= {
        "source_gate_closure_remains_fail_closed",
        "restricted_data_spec_not_current_evidence",
        "driver_dominance_matrix_nonpromotional",
        "pairwise_sensitivity_matrix_nonpromotional",
        "financialization_proxy_layer_sign_split_nonpromotional",
        "backend_expansion_context_surfaces_nonpromotional",
        "assumption_mode_channel_promotions_guarded",
        "assumption_mode_overlap_guardrails_destacked",
        "assumption_mode_sidecars_noncanonical",
        "assumption_parameter_activation_ledger_matches_engine_universe",
        "dynamic_sidecar_family_summary_nonadditive_and_noncanonical",
        "dynamic_secondary_overlay_noncanonical_and_constructibility_guarded",
        "channel_status_crosswalk_complete_and_nonpromotional",
        "restricted_protocol_falsification_matrix_design_only_and_fail_closed",
        "assumption_mode_formula_identity_audit_static_and_sidecar_passes",
        "restricted_protocol_field_contract_expands_all_required_fields_fail_closed",
        "context_surface_no_main_ratio_audit_complete",
        "context_surface_materialization_counts_current",
        "sidecar_bundle_frontier_static_secondary_not_classifier",
        "generated_text_claim_boundary_scan_no_unqualified_forbidden_claims",
        "paper_support_tables_nonpromotional_and_complete",
    }
    for field in (
        "prior_narrowing_allowed",
        "formula_replacement_allowed",
        "main_offset_ratio_changed_this_tranche",
        "dynamic_equation_changed_this_tranche",
        "split_denominator_promotion_allowed",
    ):
        assert {row[field] for row in invariant_audit_rows} == {"false"}
    assert {row["forbidden_switches_remain_disabled"] for row in invariant_audit_rows} == {
        "true"
    }
    completion_verdict_rows = list(
        csv.DictReader(
            artifacts.ratewall_backend_completion_verdict_table.open(encoding="utf-8")
        )
    )
    assert len(completion_verdict_rows) == 1
    completion_verdict = completion_verdict_rows[0]
    assert completion_verdict["completion_status"] in {
        "complete_for_current_assumption_mode_backend_pending_manual_journal_review",
        "blocked_by_backend_invariant_failure",
    }
    if completion_verdict["completion_status"] == "blocked_by_backend_invariant_failure":
        assert (
            completion_verdict["remaining_backend_blocker"]
            == "repair_backend_invariant_guardrail_failures_before_review"
        )
    else:
        assert (
            completion_verdict["remaining_backend_blocker"]
            == "none_for_current_assumption_mode_backend_manual_journal_review_still_required"
        )
    assert completion_verdict["forbidden_switches_remain_disabled"] == "true"
    assert (
        completion_verdict["claim_boundary"]
        == "backend_completion_verdict_not_empirical_promotion"
    )
    assert (
        "ru_flow_tier2_tdc_core_object_central_not_quarantined"
        in completion_verdict["assumption_mode_surface_status"]
    )
    assert (
        "joint_wall_probability_conditional_grid_surface_not_empirical_probability"
        in completion_verdict["assumption_mode_surface_status"]
    )
    assert (
        "denominator_evidence_upgrade_queue_nonpromotional_source_acquisition_only"
        in completion_verdict["assumption_mode_surface_status"]
    )
    assert (
        "tdsp_diagnostic_family_completion_gate_fail_closed_not_promotion"
        in completion_verdict["assumption_mode_surface_status"]
    )
    assert (
        "use_joint_wall_probability_summary_only_for_conditional_object_family_sensitivity"
        in completion_verdict["next_recommended_work"]
    )
    assert (
        "use_denominator_evidence_upgrade_tier1_workplan_for_source_design_acquisition_without_prior_narrowing"
        in completion_verdict["next_recommended_work"]
    )
    assert (
        "treat_tdsp_diagnostic_family_completion_gate_as_fail_closed_until_"
        "policy_path_conversion_uncertainty_and_replication_exist"
        in completion_verdict["next_recommended_work"]
    )
    for term in denominator_evidence_upgrade_terms:
        assert term in completion_verdict["remaining_evidence_promotion_blocker"]
    for term in tdsp_completion_gate_terms:
        assert term in completion_verdict["remaining_evidence_promotion_blocker"]
    for blocker in (
        "ratewall_final_recipient_current_demand_bridge_attempt.csv",
        "blocked_no_admissible_source_backed_final_recipient_current_demand_bridge",
        "exact next source fields live in that bridge-attempt artifact",
        "blocked_no_recipient_current_demand_bridge",
        "no_source_backed_mapping_from_tdcest_gross_interest_cashflow_to_"
        "final_recipient_current_demand",
        "blocked_bank_iorb_timing_matrix_requires_behavior_bridge",
    ):
        assert blocker in completion_verdict["remaining_evidence_promotion_blocker"]
    for field in (
        "prior_narrowing_allowed",
        "formula_replacement_allowed",
        "main_offset_ratio_changed_this_tranche",
        "dynamic_equation_changed_this_tranche",
        "split_denominator_promotion_allowed",
    ):
        assert completion_verdict[field] == "false"

    paper_channel_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_channel_map_table.open(encoding="utf-8")
        )
    )
    assert len(paper_channel_rows) == 15
    assert {row["source_mode_label"] for row in paper_channel_rows} == {
        "context-only",
        "fail_closed_context_only",
        "source-backed",
    }
    assert {
        "TDC deposit channel",
        "consumer credit payment drag",
        "CRE refinancing drag",
        "interest-income tax clawback",
        "public liability interest cashflow",
    } <= {row["paper_channel"] for row in paper_channel_rows}
    for field in disabled_driver_fields:
        assert {row[field] for row in paper_channel_rows} == {"false"}
    assert {row["claim_boundary"] for row in paper_channel_rows} == {
        "paper_channel_map_not_empirical_promotion"
    }
    paper_channel_critical_fields = (
        "backend_source_table",
        "evidence_status",
        "evidence_base",
        "main_ratio_role",
        "promotion_status",
        "source_gate_status",
        "source_backed_scope",
        "assumption_mode_scope",
        "blocked_scope",
        "promotion_gate_id",
        "paper_safe_sentence",
        "paper_forbidden_sentence",
    )
    assert all(
        row[field]
        for row in paper_channel_rows
        for field in paper_channel_critical_fields
    )
    stage_exhausted_rows = [
        row for row in paper_channel_rows if row["evidence_status"] == "stage_exhausted"
    ]
    assert {row["source_mode_label"] for row in stage_exhausted_rows} == {
        "fail_closed_context_only"
    }
    assert {row["source_gate_status"] for row in stage_exhausted_rows} == {
        "stage_exhausted_fail_closed"
    }
    assert {row["assumption_mode_scope"] for row in stage_exhausted_rows} == {
        "none_for_gate_promotion"
    }
    source_backed_rows = [
        row for row in paper_channel_rows if row["source_mode_label"] == "source-backed"
    ]
    assert source_backed_rows
    assert all(
        row["source_backed_scope"] not in {"", "descriptive_context_or_none"}
        for row in source_backed_rows
    )
    assert all(row["blocked_scope"] for row in source_backed_rows)
    by_paper_channel = {row["paper_channel"]: row for row in paper_channel_rows}
    assert by_paper_channel["household yield optimization"][
        "backend_source_table"
    ] == (
        "outputs/tables/ratewall_financialized_balance_sheet_channel.csv;"
        "outputs/tables/ratewall_financialized_balance_sheet_evidence_gap.csv"
    )
    assert by_paper_channel["BNPL and zero-interest float"][
        "backend_source_table"
    ] == "outputs/tables/ratewall_bnpl_zero_interest_float_evidence_gap.csv"

    paper_scenario_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_canonical_scenario_results_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(paper_scenario_rows) == len(scenario_ladder_rows)
    assert {row["source_mode_label"] for row in paper_scenario_rows} == {
        "Assumption Mode"
    }
    assert {
        row["claim_boundary"] for row in paper_scenario_rows
    } == {
        "paper_canonical_scenario_results_assumption_mode_not_empirical_threshold"
    }
    for field in disabled_driver_fields:
        assert {row[field] for row in paper_scenario_rows} == {"false"}

    paper_tdc_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_tdc_dynamic_contribution_table.open(
                encoding="utf-8"
            )
        )
    )
    assert paper_tdc_rows
    assert "true" in {row["tdc_effect_enabled"] for row in paper_tdc_rows}
    assert {row["source_mode_label"] for row in paper_tdc_rows} == {"Assumption Mode"}
    tdc_enabled_row = next(
        row
        for row in paper_tdc_rows
        if row["tdc_effect_enabled"] == "true"
        and Decimal(row["tdc_increment_to_ratio"]) != Decimal("0")
    )
    assert Decimal(tdc_enabled_row["tdc_increment_to_ratio"]) != Decimal("0")
    assert (
        Decimal(tdc_enabled_row["tdc_off_offset_ratio"])
        + Decimal(tdc_enabled_row["tdc_increment_to_ratio"])
        == Decimal(tdc_enabled_row["tdc_on_offset_ratio"])
    )
    for field in disabled_driver_fields:
        assert {row[field] for row in paper_tdc_rows} == {"false"}

    paper_parameter_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_parameter_justification_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(paper_parameter_rows) >= 32
    assert {row["source_mode_label"] for row in paper_parameter_rows} == {
        "Assumption Mode"
    }
    assert {
        "public_debt_stock_scale",
        "treasury_interest_demand_share",
        "contractionary_drag_gdp_share",
        "household_safe_asset_stock_share",
        "firm_rollover_pressure_share",
    } <= {row["parameter"] for row in paper_parameter_rows}
    for field in disabled_driver_fields:
        assert {row[field] for row in paper_parameter_rows} == {"false"}

    paper_sensitivity_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_sensitivity_summary_table.open(encoding="utf-8")
        )
    )
    assert paper_sensitivity_rows
    assert {row["source_mode_label"] for row in paper_sensitivity_rows} == {
        "Assumption Mode"
    }
    assert {
        "one_parameter_frontier",
        "hit_fragility_frontier",
        "pairwise_interaction_residual",
    } <= {row["summary_type"] for row in paper_sensitivity_rows}
    for field in disabled_driver_fields:
        assert {row[field] for row in paper_sensitivity_rows} == {"false"}

    paper_disabled_claim_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_disabled_claims_appendix_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(paper_disabled_claim_rows) == 14
    assert {row["status"] for row in paper_disabled_claim_rows} == {"disabled"}
    assert {
        "empirical_threshold_date",
        "policy_failure_claim",
        "pricing_output",
        "holder_allocation",
        "prior_narrowing",
        "formula_replacement",
    } <= {row["claim_or_output"] for row in paper_disabled_claim_rows}
    for field in disabled_driver_fields:
        assert {row[field] for row in paper_disabled_claim_rows} == {"false"}

    paper_support_audit_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_support_invariant_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(paper_support_audit_rows) == 9
    assert {row["audit_status"] for row in paper_support_audit_rows} == {"pass"}
    assert {
        "paper_channel_map_no_blank_critical_fields",
        "stage_exhausted_rows_are_fail_closed_context",
        "source_backed_rows_have_scoped_subclaims",
        "financialization_interpretation_nonpromotional",
    } <= {row["audit_item"] for row in paper_support_audit_rows}
    for field in (
        "prior_narrowing_allowed",
        "formula_replacement_allowed",
        "main_offset_ratio_changed_this_tranche",
        "dynamic_equation_changed_this_tranche",
        "split_denominator_promotion_allowed",
    ):
        assert {row[field] for row in paper_support_audit_rows} == {"false"}
    assert {row["forbidden_switches_remain_disabled"] for row in paper_support_audit_rows} == {
        "true"
    }

    accounting_identity_rows = list(
        csv.DictReader(
            artifacts.ratewall_backend_accounting_identity_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert accounting_identity_rows
    assert {row["identity_status"] for row in accounting_identity_rows} == {"pass"}
    assert {
        "canonical_scenario_ratio",
        "tdc_on_off_increment",
        "dynamic_crossing_not_empirical_threshold",
    } <= {row["identity_scope"] for row in accounting_identity_rows}
    assert all(Decimal(row["residual"]) == Decimal("0") for row in accounting_identity_rows)

    scenario_bridge_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_scenario_accounting_bridge_table.open(
                encoding="utf-8"
            )
        )
    )
    assert scenario_bridge_rows
    assert {
        row["assumption_set"] for row in scenario_bridge_rows
    } == {row["assumption_set"] for row in paper_scenario_rows}
    assert {
        "countervailing_numerator",
        "conventional_drag_denominator",
        "final_ratio_check",
    } <= {row["bridge_stage"] for row in scenario_bridge_rows}
    assert {row["source_mode_label"] for row in scenario_bridge_rows} == {
        "Assumption Mode"
    }
    assert {row["denominator_basis"] for row in scenario_bridge_rows} == {
        "scalar_conventional_drag_bil"
    }
    assert {
        row["reconciliation_status"] for row in scenario_bridge_rows
    } <= {
        "pass",
        "declared_residual_scalar_denominator_basis",
        "explicit_residual_row",
    }
    denominator_rows_by_set: dict[str, list[dict[str, str]]] = {}
    for row in scenario_bridge_rows:
        if row["bridge_stage"].startswith("conventional_drag_denominator"):
            denominator_rows_by_set.setdefault(row["assumption_set"], []).append(row)
    for rows in denominator_rows_by_set.values():
        target = Decimal(rows[0]["component_sum_target_bil"])
        summed = sum(Decimal(row["component_value_bil"]) for row in rows)
        declared_residual = {
            row["reconciliation_status"]
            for row in rows
            if row["bridge_stage"] == "conventional_drag_denominator"
        }
        assert summed == target or declared_residual == {
            "declared_residual_scalar_denominator_basis"
        }
    for field in disabled_driver_fields:
        assert {row[field] for row in scenario_bridge_rows} == {"false"}

    dynamic_summary_rows = list(
        csv.DictReader(
            artifacts.ratewall_paper_dynamic_scenario_summary_table.open(
                encoding="utf-8"
            )
        )
    )
    assert dynamic_summary_rows
    assert {row["source_mode_label"] for row in dynamic_summary_rows} == {
        "Assumption Mode"
    }
    assert {row["not_empirical_threshold_date"] for row in dynamic_summary_rows} == {
        "true"
    }
    assert {
        row["scenario_id"] for row in dynamic_summary_rows
    } >= {"baseline_debt_liquidity_glide", "high_debt_liquidity_drift_to_wall"}
    for field in disabled_driver_fields:
        assert {row[field] for row in dynamic_summary_rows} == {"false"}

    paper_support_text = artifacts.ratewall_paper_support_backend_appendix.read_text(
        encoding="utf-8"
    )
    assert "does not change priors, formulas, source gates" in paper_support_text
    assert "ratewall_paper_tdc_dynamic_contribution.csv" in paper_support_text
    assert "ratewall_backend_accounting_identity_audit.csv" in paper_support_text
    assert "ratewall_paper_dynamic_scenario_summary.csv" in paper_support_text
    assert "Assumption Mode" in artifacts.ratewall_assumption_engine_memo.read_text(
        encoding="utf-8"
    )
    theory_chapter_text = artifacts.ratewall_assumption_mode_theory_chapter.read_text(
        encoding="utf-8"
    )
    assert "Evidence Mode" in theory_chapter_text
    assert "Assumption Mode" in theory_chapter_text
    assert "Wall-Hit Regimes" in theory_chapter_text
    assert "Near-Wall Regimes" in theory_chapter_text
    assert "Robust Non-Hit Regimes" in theory_chapter_text
    assert "BNPL And Zero-Interest Credit" in theory_chapter_text
    assert "fast_repricing_high_recipient_spend" in theory_chapter_text
    assert "combined_wall_hit_regime" in theory_chapter_text
    assert "strong_contractionary_drag_nonhit" in theory_chapter_text
    assert "deprecated compatibility field" in theory_chapter_text
    assert "Model Adequacy And Critique Target" in theory_chapter_text
    assert "denominator" in theory_chapter_text
    assert "split-denominator" in theory_chapter_text
    assert "classification changes" in theory_chapter_text
    assert "Denominator uncertainty/stability findings" in theory_chapter_text
    assert "Joint denominator uncertainty findings" in theory_chapter_text
    assert (
        "Conditions That Keep Robust Non-Hit Regimes Away From The Wall"
        in theory_chapter_text
    )
    assert "not an empirical threshold date" in theory_chapter_text
    assert "configs/ratewall_assumption_sets.yml" in theory_chapter_text
    audit_packet_text = artifacts.ratewall_assumption_mode_model_audit_packet.read_text(
        encoding="utf-8"
    )
    assert "Model Structure" in audit_packet_text
    assert "Questions For External Review" in audit_packet_text
    assert "Model Adequacy Matrix" in audit_packet_text
    assert "Split-Denominator Comparison" in audit_packet_text
    assert "Denominator Uncertainty And Regime Stability" in audit_packet_text
    assert "Joint Denominator Uncertainty" in audit_packet_text
    assert "Does the offset-ratio structure" in audit_packet_text
    assert (
        "not a request for another narrow release-surface lint pass"
        in audit_packet_text
    )
    critique_response_text = (
        artifacts.ratewall_assumption_mode_critique_response.read_text(encoding="utf-8")
    )
    assert "RateWall Assumption Mode Critique Response" in critique_response_text
    assert "Current Answer To When The Wall Hits" in critique_response_text
    assert "Split-Denominator Answer" in critique_response_text
    assert "Denominator Stability Answer" in critique_response_text
    assert "Joint Denominator Stability Answer" in critique_response_text
    assert "does not promote empirical claims" in critique_response_text
    professor_prompt_text = artifacts.ratewall_professor_model_review_prompt.read_text(
        encoding="utf-8"
    )
    assert "Professor / External Review Model Review Prompt" in professor_prompt_text
    assert "model structure" in professor_prompt_text.lower()
    assert "parameter plausibility" in professor_prompt_text.lower()
    assert "ratewall_model_adequacy_matrix.csv" in professor_prompt_text
    assert "ratewall_split_denominator_comparison.csv" in professor_prompt_text
    assert "ratewall_split_denominator_uncertainty.csv" in professor_prompt_text
    assert "ratewall_split_denominator_joint_uncertainty.csv" in professor_prompt_text
    assert "High-Priority Model Adequacy Questions" in professor_prompt_text
    assert "low-level archive or wording lint" in professor_prompt_text
    assert "empirical threshold date" in professor_prompt_text
    evidence_workplan_text = (
        artifacts.ratewall_split_denominator_evidence_workplan.read_text(
            encoding="utf-8"
        )
    )
    assert "RateWall Split-Denominator Evidence Workplan" in evidence_workplan_text
    assert "Admissible-Shock Requirements" in evidence_workplan_text
    assert "Review Questions" in evidence_workplan_text
    assert "not empirical proof" in evidence_workplan_text
    denominator_evidence_review = (
        artifacts.ratewall_denominator_evidence_review.read_text(encoding="utf-8")
    )
    assert "RateWall Denominator Evidence Review" in denominator_evidence_review
    assert (
        "not promote any denominator share as source-backed"
        in denominator_evidence_review
    )
    bridge_rows = list(
        csv.DictReader(
            artifacts.ratewall_du_ru_tga_calibration_bridge_table.open(encoding="utf-8")
        )
    )
    assert bridge_rows
    assert {row["claim_boundary"] for row in bridge_rows} == {
        "bridge_context_not_final_du_ru_tga_estimate"
    }
    financialization_evidence_rows = list(
        csv.DictReader(
            artifacts.financialization_pressure_evidence_appendix_table.open(
                encoding="utf-8"
            )
        )
    )
    assert financialization_evidence_rows
    assert {
        row["financialization_causal_claim_enabled"]
        for row in financialization_evidence_rows
    } == {"false"}
    assert {row["claim_boundary"] for row in financialization_evidence_rows} == {
        "financialization_pressure_evidence_not_causal_financialization"
    }
    safe_asset_rows = list(
        csv.DictReader(
            artifacts.safe_asset_retention_context_table.open(encoding="utf-8")
        )
    )
    assert safe_asset_rows
    assert {row["claim_boundary"] for row in safe_asset_rows} == {
        "safe_asset_retention_context_not_causal_financialization"
    }
    assert {
        row["financialization_causal_claim_enabled"] for row in safe_asset_rows
    } == {"false"}
    safe_asset_evidence_rows = list(
        csv.DictReader(
            artifacts.safe_asset_retention_evidence_appendix_table.open(
                encoding="utf-8"
            )
        )
    )
    assert safe_asset_evidence_rows
    assert {row["claim_boundary"] for row in safe_asset_evidence_rows} == {
        "safe_asset_retention_evidence_not_causal_financialization"
    }
    metric_names = {row["metric"] for row in metrics}
    assert {
        "ratewall_threshold_calibration_range_rows",
        "ratewall_calibrated_threshold_simulation_rows",
        "du_ru_tga_calibration_bridge_rows",
        "financialization_pressure_evidence_rows",
        "safe_asset_retention_context_rows",
        "buyer_case_sign_matrix_rows",
        "recipient_mpc_scenario_rows",
    } <= metric_names
    benchmark_rows = list(
        csv.DictReader(
            artifacts.ratewall_contractionary_benchmark_calibration_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {
        "contractionary_drag_gdp_share",
        "du_outlay_share",
        "fiscal_offset_share",
    } <= {row["benchmark_component"] for row in benchmark_rows}
    assert "blocked_missing_exact_source_field" in {
        row["calibration_status"] for row in benchmark_rows
    }
    assert {row["claim_boundary"] for row in benchmark_rows} == {
        "benchmark_calibration_not_policy_failure_or_causal_claim"
    }
    contractionary = next(
        row
        for row in benchmark_rows
        if row["benchmark_component"] == "contractionary_drag_gdp_share"
    )
    assert contractionary["calibration_status"] == "blocked_missing_exact_source_field"
    assert contractionary["source_field"] == "mixed_event_study_outcomes_not_gdp_share"
    uncertainty_rows = list(
        csv.DictReader(
            artifacts.ratewall_threshold_uncertainty_bands_table.open(encoding="utf-8")
        )
    )
    assert {row["horizon"] for row in uncertainty_rows} == {
        "1q",
        "1y",
        "3y",
        "5y",
        "10y",
    }
    assert {row["policy_failure_claim_enabled"] for row in uncertainty_rows} == {
        "false"
    }
    validation_rows = list(
        csv.DictReader(
            artifacts.ratewall_historical_threshold_validation_table.open(
                encoding="utf-8"
            )
        )
    )
    assert validation_rows
    assert {
        row["raw_rate_change_identification_rejected"] for row in validation_rows
    } == {"true"}
    assert {row["causal_claim_enabled"] for row in validation_rows} == {"false"}
    assert {row["policy_failure_claim_enabled"] for row in validation_rows} == {"false"}
    boundary_rows = list(
        csv.DictReader(
            artifacts.ratewall_policy_boundary_synthesis_table.open(encoding="utf-8")
        )
    )
    assert boundary_rows
    assert {row["pricing_output_enabled"] for row in boundary_rows} == {"false"}
    assert {row["incidence_claim_enabled"] for row in boundary_rows} == {"false"}
    assert {row["welfare_claim_enabled"] for row in boundary_rows} == {"false"}
    assert {row["financialization_causal_claim_enabled"] for row in boundary_rows} == {
        "false"
    }
    assert {row["policy_failure_claim_enabled"] for row in boundary_rows} == {"false"}
    metric_names = {row["metric"] for row in metrics}
    assert {
        "ratewall_contractionary_benchmark_calibration_rows",
        "ratewall_threshold_uncertainty_band_rows",
        "ratewall_historical_threshold_validation_rows",
        "ratewall_policy_boundary_synthesis_rows",
    } <= metric_names
    threshold_audit_rows = list(
        csv.DictReader(
            artifacts.ratewall_threshold_claim_boundary_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["audit_status"] for row in threshold_audit_rows} == {"pass"}
    buyer_rows = list(
        csv.DictReader(artifacts.buyer_case_sign_matrix_table.open(encoding="utf-8"))
    )
    assert {
        "bank_absorption",
        "mmf_absorption_from_bank_deposits",
        "mmf_absorption_from_on_rrp",
        "row_absorption",
        "domestic_nonbank_absorption",
        "fed_secondary_market_purchase",
    } == {row["buyer_case"] for row in buyer_rows}
    assert {row["incidence_claim_enabled"] for row in buyer_rows} == {"false"}
    mpc_rows = list(
        csv.DictReader(
            artifacts.recipient_mpc_scenario_scaffold_table.open(encoding="utf-8")
        )
    )
    assert {row["mpc_assumptions_enabled"] for row in mpc_rows} == {"false"}
    invariant_rows = list(
        csv.DictReader(
            artifacts.release_19_accounting_invariant_audit_table.open(encoding="utf-8")
        )
    )
    assert {row["audit_status"] for row in invariant_rows} == {"pass"}
    post_audit_rows = list(
        csv.DictReader(
            artifacts.release_19_post_audit_methodology_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["action_status"] for row in post_audit_rows} == {"accepted"}
    release_20_activity_rows = list(
        csv.DictReader(
            artifacts.release_20_activity_demand_benchmark_table.open(encoding="utf-8")
        )
    )
    assert {"coherent_gdp_share_contractionary_drag"} <= {
        row["benchmark_object"] for row in release_20_activity_rows
    }
    assert any(
        row["benchmark_status"] == "blocked_no_defensible_mapping_to_gdp_share"
        for row in release_20_activity_rows
    )
    assert {
        row["policy_failure_claim_enabled"] for row in release_20_activity_rows
    } == {"false"}
    release_20_lp_rows = list(
        csv.DictReader(
            artifacts.release_20_state_dependent_lp_diagnostics_table.open(
                encoding="utf-8"
            )
        )
    )
    assert release_20_lp_rows
    assert {
        row["raw_rate_change_identification_rejected"] for row in release_20_lp_rows
    } == {"true"}
    assert {row["dynamic_lp_claim_enabled"] for row in release_20_lp_rows} == {"false"}
    release_20_decision_rows = list(
        csv.DictReader(
            artifacts.release_20_benchmark_submission_decision_table.open(
                encoding="utf-8"
            )
        )
    )
    assert any(
        row["decision_status"] == "blocked_final_gdp_share_mapping_missing"
        for row in release_20_decision_rows
    )
    assert {
        row["threshold_recalibration_enabled"] for row in release_20_decision_rows
    } == {"false"}
    release_21_live_rows = list(
        csv.DictReader(
            artifacts.release_21_live_refresh_endpoint_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["audit_status"] for row in release_21_live_rows} == {"pass"}
    assert {
        "endpoint_progress_logging",
        "bounded_fred_transport_timeouts",
        "per_series_deadline_and_fallback_provenance",
    } == {row["audit_component"] for row in release_21_live_rows}
    release_21_benchmark_rows = list(
        csv.DictReader(
            artifacts.release_21_final_benchmark_gate_table.open(encoding="utf-8")
        )
    )
    assert any(
        row["gate_component"] == "coherent_gdp_share_denominator"
        and row["gate_status"] == "blocked_final_no_gdp_share_promotion"
        for row in release_21_benchmark_rows
    )
    assert {
        row["threshold_recalibration_enabled"] for row in release_21_benchmark_rows
    } == {"false"}
    assert {
        row["policy_failure_claim_enabled"] for row in release_21_benchmark_rows
    } == {"false"}
    release_21_invariant_rows = list(
        csv.DictReader(
            artifacts.release_21_backend_invariant_audit_table.open(encoding="utf-8")
        )
    )
    assert {row["audit_status"] for row in release_21_invariant_rows} == {"pass"}
    blocker_resolution_rows = list(
        csv.DictReader(
            artifacts.ratewall_blocker_resolution_ledger_table.open(encoding="utf-8")
        )
    )
    assert {
        "exact_du_outlay_recipient_split",
        "final_ru_absorption_bridge",
        "fiscal_offset_behavior",
        "dynamic_contractionary_benchmark",
        "policy_claim_promotion",
    } <= {row["blocker_id"] for row in blocker_resolution_rows}
    assert {row["promotion_enabled"] for row in blocker_resolution_rows} == {"false"}
    assert {row["claim_boundary"] for row in blocker_resolution_rows} == {
        "blocker_resolution_not_claim_promotion"
    }
    assert any(
        row["release_15_resolution_status"].startswith("blocked")
        for row in blocker_resolution_rows
    )
    assert any(
        row["release_15_resolution_status"] == "resolved_for_bounded_context"
        for row in blocker_resolution_rows
    )
    publication_claim_rows = list(
        csv.DictReader(
            artifacts.ratewall_publication_claim_decision_table.open(encoding="utf-8")
        )
    )
    assert publication_claim_rows
    assert {row["promotion_claim_enabled"] for row in publication_claim_rows} == {
        "false"
    }
    assert any(
        row["claim_id"] == "conditional_threshold_sensitivity"
        and row["publication_claim_enabled"] == "true"
        for row in publication_claim_rows
    )
    assert any(
        row["claim_id"] == "joint_wall_probability_conditional_grid"
        and row["publication_claim_enabled"] == "true"
        and row["promotion_claim_enabled"] == "false"
        and row["evidence_artifact"] == "ratewall_joint_wall_probability_summary.csv"
        and all(
            term in row["decision_basis"] for term in joint_probability_boundary_terms
        )
        for row in publication_claim_rows
    )
    assert any(
        row["claim_id"] == "denominator_evidence_upgrade_source_acquisition_queue"
        and row["publication_claim_enabled"] == "true"
        and row["promotion_claim_enabled"] == "false"
        and row["evidence_artifact"]
        == "ratewall_denominator_evidence_upgrade_priority_queue.csv"
        and all(term in row["decision_basis"] for term in denominator_evidence_upgrade_terms)
        for row in publication_claim_rows
    )
    assert any(
        row["claim_id"] == "tdsp_diagnostic_family_completion_boundary"
        and row["publication_claim_enabled"] == "true"
        and row["promotion_claim_enabled"] == "false"
        and row["evidence_artifact"]
        == "ratewall_tdsp_diagnostic_family_completion_gate.csv"
        and all(term in row["decision_basis"] for term in tdsp_completion_gate_terms)
        for row in publication_claim_rows
    )
    assert any(
        row["claim_id"] == "bounded_accounting_and_source_package"
        and all(
            term in row["decision_basis"] for term in central_tdc_guardrail_terms
        )
        for row in publication_claim_rows
    )
    assert any(
        row["claim_id"] == "final_threshold_or_policy_failure"
        and row["publication_claim_enabled"] == "false"
        and row["publication_decision"] == "block_promotion"
        and "ratewall_final_recipient_current_demand_bridge_attempt.csv"
        in row["decision_basis"]
        and "blocked_no_admissible_source_backed_final_recipient_current_demand_bridge"
        in row["decision_basis"]
        and "exact next source fields live in that bridge-attempt artifact"
        in row["decision_basis"]
        and "blocked_no_recipient_current_demand_bridge" in row["decision_basis"]
        and "no_source_backed_mapping_from_tdcest_gross_interest_cashflow_to_"
        "final_recipient_current_demand"
        in row["decision_basis"]
        and "blocked_bank_iorb_timing_matrix_requires_behavior_bridge"
        in row["decision_basis"]
        for row in publication_claim_rows
    )
    assert any(
        row["claim_id"] == "release_15_publication_boundary"
        and row["publication_decision"] == "publish_with_blockers"
        and all(
            blocker in row["decision_basis"]
            for blocker in source_specific_recipient_blockers
        )
        and all(
            term in row["decision_basis"] for term in central_tdc_guardrail_terms
        )
        and all(term in row["decision_basis"] for term in tdsp_completion_gate_terms)
        for row in publication_claim_rows
    )
    final_blocker_rows = list(
        csv.DictReader(
            artifacts.ratewall_final_blocker_ledger_table.open(encoding="utf-8")
        )
    )
    assert final_blocker_rows
    assert {row["promotion_enabled"] for row in final_blocker_rows} == {"false"}
    assert {row["pricing_output_enabled"] for row in final_blocker_rows} == {"false"}
    assert {row["incidence_claim_enabled"] for row in final_blocker_rows} == {"false"}
    assert {row["welfare_claim_enabled"] for row in final_blocker_rows} == {"false"}
    assert {row["policy_failure_claim_enabled"] for row in final_blocker_rows} == {
        "false"
    }
    assert "publication_claim_package" in {
        row["blocker_id"] for row in final_blocker_rows
    }
    release_16_source_rows = list(
        csv.DictReader(
            artifacts.ratewall_release_16_source_resolution_closeout_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(release_16_source_rows) == 5
    assert {row["release_16_resolution_status"] for row in release_16_source_rows} == {
        "final_no_further_promotion"
    }
    assert {row["promotion_enabled"] for row in release_16_source_rows} == {"false"}
    assert {
        "source_backed_context",
        "source_backed_bounded_empirical",
        "sibling_derived",
        "missing",
        "blocked",
    } <= {row["source_label"] for row in release_16_source_rows}
    assert all(row["source_backed_field"] for row in release_16_source_rows)
    assert all(row["sibling_derived_field"] for row in release_16_source_rows)
    assert all(row["inferred_field"] for row in release_16_source_rows)
    assert all(row["speculative_field"] for row in release_16_source_rows)
    assert all(row["missing_field"] for row in release_16_source_rows)
    assert all(row["blocked_field"] for row in release_16_source_rows)
    release_16_no_promotion_rows = list(
        csv.DictReader(
            artifacts.ratewall_release_16_no_further_promotion_ledger_table.open(
                encoding="utf-8"
            )
        )
    )
    assert release_16_no_promotion_rows
    assert {
        row["final_no_further_promotion"] for row in release_16_no_promotion_rows
    } == {"true"}
    assert {row["promotion_enabled"] for row in release_16_no_promotion_rows} == {
        "false"
    }
    assert {row["pricing_output_enabled"] for row in release_16_no_promotion_rows} == {
        "false"
    }
    assert {row["incidence_claim_enabled"] for row in release_16_no_promotion_rows} == {
        "false"
    }
    assert {row["welfare_claim_enabled"] for row in release_16_no_promotion_rows} == {
        "false"
    }
    assert {
        "bounded_publication_closeout",
        "final_threshold_date_or_policy_failure",
    } <= {row["claim_id"] for row in release_16_no_promotion_rows}
    release_17_review_rows = list(
        csv.DictReader(
            artifacts.ratewall_release_17_external_review_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(release_17_review_rows) == 6
    assert {row["review_status"] for row in release_17_review_rows} == {"pass"}
    assert {row["promotion_enabled"] for row in release_17_review_rows} == {"false"}
    assert {
        "source_provenance_appendix",
        "threshold_sensitivity_appendix",
        "tdc_deposit_channel_appendix",
    } <= {row["review_component"] for row in release_17_review_rows}
    release_17_polish_rows = list(
        csv.DictReader(
            artifacts.ratewall_release_17_publication_polish_qa_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(release_17_polish_rows) == 7
    assert {row["qa_status"] for row in release_17_polish_rows} == {"pass"}
    assert {row["manual_macro_values_allowed"] for row in release_17_polish_rows} == {
        "false"
    }
    release_17_reopen_rows = list(
        csv.DictReader(
            artifacts.ratewall_release_17_blocker_reopen_decision_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(release_17_reopen_rows) == 6
    assert {row["blocker_reopened"] for row in release_17_reopen_rows} == {"false"}
    assert {row["new_evidence_found"] for row in release_17_reopen_rows} == {"false"}
    assert {
        "exact_du_outlay_recipient_split",
        "final_ru_absorption_bridge",
        "fiscal_offset_behavior",
        "dynamic_contractionary_benchmark",
        "causal_financialization",
    } <= {row["blocker_id"] for row in release_17_reopen_rows}
    release_18_refresh_rows = list(
        csv.DictReader(
            artifacts.ratewall_release_18_live_refresh_robustness_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(release_18_refresh_rows) == 6
    assert {row["stored_secrets_allowed"] for row in release_18_refresh_rows} == {
        "false"
    }
    assert {row["pricing_output_enabled"] for row in release_18_refresh_rows} == {
        "false"
    }
    assert {row["policy_failure_claim_enabled"] for row in release_18_refresh_rows} == {
        "false"
    }
    assert {
        "socket_timeout_guard",
        "per_series_deadline_guard",
        "fallback_provenance_guard",
        "publication_freeze_boundary",
    } <= {row["refresh_component"] for row in release_18_refresh_rows}
    metric_names = {row["metric"] for row in metrics}
    assert {
        "ratewall_blocker_resolution_ledger_rows",
        "ratewall_blocker_resolved_for_context_rows",
        "ratewall_publication_claim_decision_rows",
        "ratewall_publication_claim_enabled_rows",
        "ratewall_final_blocker_ledger_rows",
        "ratewall_final_blocker_blocked_rows",
        "ratewall_release_16_source_resolution_closeout_rows",
        "ratewall_release_16_final_no_further_promotion_rows",
        "ratewall_release_16_no_further_promotion_ledger_rows",
        "ratewall_release_16_promotion_disabled_rows",
        "ratewall_release_17_external_review_audit_rows",
        "ratewall_release_17_external_review_pass_rows",
        "ratewall_release_17_publication_polish_qa_rows",
        "ratewall_release_17_publication_polish_pass_rows",
        "ratewall_release_17_blocker_reopen_decision_rows",
        "ratewall_release_17_blockers_reopened_rows",
        "ratewall_release_18_live_refresh_robustness_rows",
        "ratewall_release_18_live_refresh_pass_rows",
    } <= metric_names
    assert artifacts.maturity_ladder_table.exists()
    assert artifacts.mspd_field_coverage_table.exists()
    coverage = list(
        csv.DictReader(artifacts.mspd_field_coverage_table.open(encoding="utf-8"))
    )
    assert {row["component"] for row in coverage} >= {
        "coupon_payment_dates",
        "frn_reset_identification",
        "tips_accrual",
        "buyback_adjustments",
        "holder_split",
    }
    reconciliation = list(
        csv.DictReader(artifacts.mspd_reconciliation_table.open(encoding="utf-8"))
    )
    assert reconciliation[0]["record_date"] == "2026-04-30"
    assert reconciliation[0]["status"] == "ok"
    cbo_rows = list(
        csv.DictReader(artifacts.cbo_projection_table.open(encoding="utf-8"))
    )
    assert {row["metric"] for row in cbo_rows} >= {
        "net_interest_gdp_pct",
        "debt_held_public_gdp_pct",
        "deficit_gdp_pct",
        "average_interest_rate_debt_public_pct",
    }
    cashflows = list(
        csv.DictReader(artifacts.treasury_coupon_cashflow_table.open(encoding="utf-8"))
    )
    assert cashflows
    assert all(row["cashflow_date"] for row in cashflows)
    assert {"coupon", "principal"} <= {row["cashflow_type"] for row in cashflows}
    assert any(
        "actual/actual" in row["day_count_basis"]
        for row in cashflows
        if row["cashflow_type"] == "coupon"
    )
    assert all(row["day_count_source_status"] for row in cashflows)
    assert any(
        row["valuation_input_status"] == "frn_daily_index_joined" for row in cashflows
    )
    assert any(
        row["valuation_input_status"] == "tips_daily_index_joined" for row in cashflows
    )
    assumptions = list(
        csv.DictReader(
            artifacts.treasury_frn_tips_assumptions_table.open(encoding="utf-8")
        )
    )
    assert {row["component"] for row in assumptions} == {"frn_reset", "tips_accrual"}
    assert all(row["missing_fields"] for row in assumptions)
    buyback_rows = list(
        csv.DictReader(artifacts.treasury_buybacks_table.open(encoding="utf-8"))
    )
    assert buyback_rows[0]["cusip"] == "demo_note"
    buyback_join = list(
        csv.DictReader(
            artifacts.treasury_buyback_mspd_join_table.open(encoding="utf-8")
        )
    )
    assert any(row["join_status"] == "matched_buyback" for row in buyback_join)
    holder_rows = list(
        csv.DictReader(artifacts.holder_context_table.open(encoding="utf-8"))
    )
    assert {row["sector"] for row in holder_rows} >= {
        "private_investors",
        "foreign_and_international",
        "federal_reserve_banks",
    }
    fine_holder_rows = list(
        csv.DictReader(artifacts.fine_holder_context_table.open(encoding="utf-8"))
    )
    assert {row["sector"] for row in fine_holder_rows} >= {
        "households_nonprofits_treasury_securities",
        "us_chartered_depositories_treasury_securities",
        "money_market_funds_treasury_securities",
        "foreign_official_private_transaction_split",
        "foreign_official_private_stock_split",
        "sec_nmfp_money_fund_cusip_detail",
    }
    tic_rows = list(
        csv.DictReader(
            artifacts.tic_foreign_holder_reconciliation_table.open(encoding="utf-8")
        )
    )
    assert any(row["component"] == "foreign_official_institutions" for row in tic_rows)
    tic_stock_rows = list(
        csv.DictReader(
            artifacts.tic_foreign_treasury_stock_split_table.open(encoding="utf-8")
        )
    )
    assert any(
        row["component"] == "total_treasury_securities" for row in tic_stock_rows
    )
    ofr_rows = list(
        csv.DictReader(artifacts.ofr_mmf_treasury_context_table.open(encoding="utf-8"))
    )
    assert any(row["channel"] == "us_treasury_securities" for row in ofr_rows)
    assert any(row["sec_nmfp_value_bil"] for row in ofr_rows)
    sec_nmfp_rows = list(
        csv.DictReader(
            artifacts.sec_nmfp_mmf_treasury_cusip_context_table.open(encoding="utf-8")
        )
    )
    assert {"direct_security", "repo_collateral"} <= {
        row["channel"] for row in sec_nmfp_rows
    }
    assert {"latest", "historical"} <= {row["period_role"] for row in sec_nmfp_rows}
    valuation_rows = list(
        csv.DictReader(artifacts.treasury_valuation_inputs_table.open(encoding="utf-8"))
    )
    assert {"frn", "tips"} <= {row["security_kind"] for row in valuation_rows}
    daily_valuation_rows = list(
        csv.DictReader(
            artifacts.treasury_daily_valuation_paths_table.open(encoding="utf-8")
        )
    )
    assert {"frn_daily_index", "tips_daily_index_ratio"} <= {
        row["security_kind"] for row in daily_valuation_rows
    }
    valuation_validation = list(
        csv.DictReader(
            artifacts.treasury_valuation_validation_table.open(encoding="utf-8")
        )
    )
    assert {row["component"] for row in valuation_validation} >= {
        "frn_reset_daily_index_join",
        "tips_cpi_lag_index_ratio_join",
        "frn_reset_formula_coverage_summary",
        "tips_index_ratio_formula_coverage_summary",
    }
    representative_rows = [
        row
        for row in valuation_validation
        if row["coverage_scope"] == "representative_row"
    ]
    coverage_rows = [
        row
        for row in valuation_validation
        if row["coverage_scope"] == "matched_mspd_cashflow_cusips"
    ]
    assert all(row["status"] == "input_join_validated" for row in representative_rows)
    assert all(
        row["claim_boundary"] == "formula_validation_not_pricing_engine"
        for row in representative_rows
    )
    assert all(
        row["formula_check_status"] == "formula_validated_not_pricing"
        for row in representative_rows
    )
    assert all(row["formula_name"] for row in representative_rows)
    assert all(row["absolute_difference"] for row in representative_rows)
    assert coverage_rows
    assert all(row["formula_candidate_rows"] for row in coverage_rows)
    assert all(row["coverage_ratio"] for row in coverage_rows)
    assert all(
        row["claim_boundary"] == "formula_coverage_validation_not_pricing_engine"
        for row in coverage_rows
    )
    tips_validation = next(
        row
        for row in valuation_validation
        if row["component"] == "tips_cpi_lag_index_ratio_join"
    )
    assert tips_validation["term_match_status"] == "issue_term_matched"
    assert int(tips_validation["matched_term_rows"]) >= 1
    valuation_diagnostics = list(
        csv.DictReader(
            artifacts.treasury_valuation_coverage_diagnostics_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["diagnostic_component"] for row in valuation_diagnostics} >= {
        "frn_source_convention_diagnostics",
        "frn_formula_review_diagnostics",
        "tips_issue_term_coverage_diagnostics",
        "tips_formula_review_diagnostics",
    }
    assert all(
        row["claim_boundary"].endswith("_not_pricing_engine")
        for row in valuation_diagnostics
    )
    frn_diagnostic = next(
        row
        for row in valuation_diagnostics
        if row["diagnostic_component"] == "frn_source_convention_diagnostics"
    )
    assert (
        int(frn_diagnostic["source_convention_decimal_like_rows"])
        + int(frn_diagnostic["source_convention_percent_like_rows"])
    ) >= 1
    frn_review = next(
        row
        for row in valuation_diagnostics
        if row["diagnostic_component"] == "frn_formula_review_diagnostics"
    )
    assert frn_review["review_sample_count"]
    assert "not pricing" in frn_review["review_sample_note"]
    tips_diagnostic = next(
        row
        for row in valuation_diagnostics
        if row["diagnostic_component"] == "tips_issue_term_coverage_diagnostics"
    )
    assert int(tips_diagnostic["missing_issue_term_rows"]) >= 0
    assert tips_diagnostic["missing_issue_cusip_count"]
    assert tips_diagnostic["gap_explanation"]
    tips_review_explanation = list(
        csv.DictReader(
            artifacts.treasury_tips_formula_review_explanation_table.open(
                encoding="utf-8"
            )
        )
    )
    assert tips_review_explanation
    assert all(
        row["claim_boundary"] == "formula_review_explanation_not_pricing_engine"
        for row in tips_review_explanation
    )
    assert {row["formula_check_status"] for row in tips_review_explanation} <= {
        "formula_review_not_pricing",
        "no_formula_review_rows_not_pricing",
    }
    assert all(
        row["explanation_status"]
        in {
            "formula_tolerance_classified_not_pricing",
            "inactive_no_review_rows",
        }
        for row in tips_review_explanation
    )
    assert all(
        row["unresolved_after_classification"] in {"false", ""}
        for row in tips_review_explanation
    )
    assert all(row["classification_rationale"] for row in tips_review_explanation)
    convention_audit = list(
        csv.DictReader(
            artifacts.treasury_valuation_convention_audit_table.open(encoding="utf-8")
        )
    )
    assert {row["audit_component"] for row in convention_audit} == {
        "frn_reset_convention",
        "tips_accrual_convention",
    }
    assert all(row["audit_required"] == "true" for row in convention_audit)
    assert all(row["audit_passed"] == "true" for row in convention_audit)
    assert all(row["pricing_output_enabled"] == "false" for row in convention_audit)
    assert all(int(row["checked_rows"]) >= 1 for row in convention_audit)
    assert all(int(row["unresolved_rows"]) == 0 for row in convention_audit)
    assert all(row["audit_note"] for row in convention_audit)
    assert all(
        row["claim_boundary"] == "convention_audit_not_pricing_engine"
        for row in convention_audit
    )
    edge_fixtures = list(
        csv.DictReader(
            artifacts.treasury_cashflow_edge_fixtures_table.open(encoding="utf-8")
        )
    )
    assert {row["fixture_id"] for row in edge_fixtures} >= {
        "frn_reset_date_boundary",
        "frn_leap_day_accrual_period",
        "tips_cpi_interpolation_rounding",
        "tips_reopening_issue_date",
    }
    assert any(
        row["sample_source"] == "source_backed_snapshot" for row in edge_fixtures
    )
    assert {
        row["security_kind"]
        for row in edge_fixtures
        if row["sample_source"] == "source_backed_snapshot"
    } >= {"frn", "tips"}
    source_edge_fixtures = [
        row for row in edge_fixtures if row["sample_source"] == "source_backed_snapshot"
    ]
    assert {row["source_edge_classifier"] for row in source_edge_fixtures} == {
        "frn_reset_boundary_classifier",
        "frn_leap_day_classifier",
        "tips_rounding_review_classifier",
        "tips_reopening_classifier",
    }
    assert all(row["source_edge_classifier_status"] for row in source_edge_fixtures)
    assert any(row["source_edge_blocker"] for row in source_edge_fixtures)
    assert all(row["source_edge_note"] for row in source_edge_fixtures)
    frn_leap_gap = list(
        csv.DictReader(
            artifacts.treasury_frn_leap_day_source_gap_table.open(encoding="utf-8")
        )
    )
    assert {row["date_field"] for row in frn_leap_gap} >= {
        "record_date",
        "start_of_accrual_period",
        "end_of_accrual_period",
    }
    assert all(row["pricing_output_enabled"] == "false" for row in frn_leap_gap)
    assert all(row["holder_allocation_enabled"] == "false" for row in frn_leap_gap)
    assert all(row["incidence_claim_enabled"] == "false" for row in frn_leap_gap)
    assert any(
        row["target_leap_day_status"] == "outside_current_official_source_history"
        for row in frn_leap_gap
    )
    assert any(
        row["gap_status"] == "source_gap_documented_not_pricing" for row in frn_leap_gap
    )
    frn_reset_blocker_map = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_source_blocker_map_table.open(encoding="utf-8")
        )
    )
    assert {row["source_field_group"] for row in frn_reset_blocker_map} == {
        "daily_frn_index_accrual_fields",
        "auction_term_reset_reference_fields",
        "recurring_reset_calendar_fields",
    }
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_blocker_map
    )
    assert all(row["current_official_fields"] for row in frn_reset_blocker_map)
    assert all(
        row["schema_drift_status"] == "no_candidate_reset_calendar_fields_present"
        for row in frn_reset_blocker_map
    )
    assert any(
        row["field_status"] == "not_exposed_in_current_official_fields"
        for row in frn_reset_blocker_map
    )
    frn_reset_method_note = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_method_note_table.open(encoding="utf-8")
        )
    )
    assert {row["method_component"] for row in frn_reset_method_note} == {
        "official_frn_interest_method",
        "reset_calendar_source_gap",
        "treasurydirect_frn_context",
    }
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_method_note
    )
    assert all(
        row["holder_allocation_enabled"] == "false" for row in frn_reset_method_note
    )
    assert all(
        row["incidence_claim_enabled"] == "false" for row in frn_reset_method_note
    )
    assert any(
        row["reconstruction_policy"] == "reject_ad_hoc_reconstruction"
        for row in frn_reset_method_note
    )
    frn_reset_official_audit = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_official_source_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["audit_component"] for row in frn_reset_official_audit} == {
        "frn_daily_index_endpoint_field_audit",
        "frn_auction_term_endpoint_field_audit",
        "treasury_frn_term_sheet_method_audit",
        "recurring_reset_calendar_conclusion",
    }
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_official_audit
    )
    assert all(
        row["holder_allocation_enabled"] == "false" for row in frn_reset_official_audit
    )
    assert all(
        row["incidence_claim_enabled"] == "false" for row in frn_reset_official_audit
    )
    assert any(
        row["audit_status"] == "blocked_official_evidence_not_pricing"
        for row in frn_reset_official_audit
    )
    assert any(
        "recurring_reset_date_per_daily_row"
        in row["unavailable_recurring_reset_fields"]
        for row in frn_reset_official_audit
    )
    frn_reset_schema_evidence = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_official_source_schema_evidence_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["schema_evidence_component"] for row in frn_reset_schema_evidence} == {
        "frn_daily_index_schema",
        "auction_term_schema",
        "combined_machine_readable_schema_gap",
        "term_sheet_method_context",
        "schema_drift_watch",
    }
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_schema_evidence
    )
    assert all(
        row["reset_calendar_construction_enabled"] == "false"
        for row in frn_reset_schema_evidence
    )
    assert any(
        row["evidence_status"] == "blocked_reset_calendar_schema_absent"
        and "recurring_reset_date_per_daily_row"
        in row["unavailable_reset_calendar_fields"]
        for row in frn_reset_schema_evidence
    )
    assert any(
        row["schema_evidence_component"] == "schema_drift_watch"
        and row["evidence_status"] == "no_candidate_reset_calendar_fields_present"
        for row in frn_reset_schema_evidence
    )
    assert any(
        "derive_reset_dates_from_record_dates" in row["prohibited_current_use"]
        for row in frn_reset_schema_evidence
    )
    frn_reset_method_semantics = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_method_semantics_audit_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["semantic_component"] for row in frn_reset_method_semantics} == {
        "daily_reset_frequency",
        "actual_360_day_count",
        "index_plus_spread",
        "two_business_day_lockout",
        "business_day_holiday_adjustment",
        "row_level_reset_calendar",
    }
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_method_semantics
    )
    assert all(
        row["holder_allocation_enabled"] == "false"
        for row in frn_reset_method_semantics
    )
    assert all(
        row["incidence_claim_enabled"] == "false" for row in frn_reset_method_semantics
    )
    assert any(
        row["source_field_mapping_status"] == "source_fields_available_not_pricing"
        for row in frn_reset_method_semantics
    )
    assert any(
        row["source_field_mapping_status"]
        == "method_context_only_requires_future_audit"
        for row in frn_reset_method_semantics
    )
    assert any(
        row["semantic_component"] == "row_level_reset_calendar"
        and row["source_field_mapping_status"] == "machine_readable_calendar_absent"
        for row in frn_reset_method_semantics
    )
    frn_reset_method_design = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_method_design_ledger_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["design_requirement_id"] for row in frn_reset_method_design} == {
        "official_reset_calendar_source",
        "official_method_semantics",
        "cusip_coverage_reconciliation",
        "calendar_generation_policy",
        "validation_fixture_suite",
        "explicit_pricing_opt_in_gate",
    }
    assert all(
        row["requirement_status"] == "required_before_any_construction"
        for row in frn_reset_method_design
    )
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_method_design
    )
    assert all(
        row["holder_allocation_enabled"] == "false" for row in frn_reset_method_design
    )
    assert all(
        row["incidence_claim_enabled"] == "false" for row in frn_reset_method_design
    )
    assert any(
        "generate_reset_dates" in row["prohibited_current_use"]
        for row in frn_reset_method_design
    )
    assert any(
        "treasury_frn_reset_official_source_audit.csv" in row["input_artifacts"]
        for row in frn_reset_method_design
    )
    official_source_row = [
        row
        for row in frn_reset_method_design
        if row["design_requirement_id"] == "official_reset_calendar_source"
    ][0]
    assert (
        "treasury_frn_reset_official_source_schema_evidence.csv"
        in (official_source_row["input_artifacts"])
    )
    assert "schema_evidence_rows=5" in official_source_row["current_evidence"]
    assert "schema_blocked_rows=1" in official_source_row["current_evidence"]
    method_semantics_row = [
        row
        for row in frn_reset_method_design
        if row["design_requirement_id"] == "official_method_semantics"
    ][0]
    assert (
        method_semantics_row["source_evidence_status"]
        == "semantics_audited_not_calendar_mapped"
    )
    assert (
        "treasury_frn_reset_method_semantics_audit.csv"
        in method_semantics_row["input_artifacts"]
    )
    assert "context_only_components" in method_semantics_row["current_evidence"]
    cusip_coverage_row = [
        row
        for row in frn_reset_method_design
        if row["design_requirement_id"] == "cusip_coverage_reconciliation"
    ][0]
    assert (
        cusip_coverage_row["source_evidence_status"]
        == "cusip_coverage_audited_not_calendar_ready"
    )
    assert (
        "treasury_frn_reset_cusip_coverage_ledger.csv"
        in cusip_coverage_row["input_artifacts"]
    )
    assert "coverage_ledger_rows=8" in cusip_coverage_row["current_evidence"]
    fixture_suite_row = [
        row
        for row in frn_reset_method_design
        if row["design_requirement_id"] == "validation_fixture_suite"
    ][0]
    assert (
        fixture_suite_row["source_evidence_status"]
        == "fixture_requirements_mapped_not_construction_ready"
    )
    assert (
        "treasury_frn_reset_fixture_readiness_ledger.csv"
        in fixture_suite_row["input_artifacts"]
    )
    assert "fixture_readiness_rows=7" in fixture_suite_row["current_evidence"]
    calendar_policy_row = [
        row
        for row in frn_reset_method_design
        if row["design_requirement_id"] == "calendar_generation_policy"
    ][0]
    assert (
        calendar_policy_row["source_evidence_status"]
        == "fail_closed_policy_mapped_not_construction_ready"
    )
    assert (
        "treasury_frn_reset_calendar_generation_policy.csv"
        in calendar_policy_row["input_artifacts"]
    )
    assert "calendar_policy_rows=6" in calendar_policy_row["current_evidence"]
    explicit_opt_in_row = [
        row
        for row in frn_reset_method_design
        if row["design_requirement_id"] == "explicit_pricing_opt_in_gate"
    ][0]
    assert (
        explicit_opt_in_row["source_evidence_status"]
        == "explicit_opt_in_switches_documented_disabled"
    )
    assert (
        "treasury_frn_reset_explicit_opt_in_gate.csv"
        in explicit_opt_in_row["input_artifacts"]
    )
    assert "reset-calendar construction" in explicit_opt_in_row["current_evidence"]
    frn_reset_cusip_coverage = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_cusip_coverage_ledger_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["coverage_component"] for row in frn_reset_cusip_coverage} == {
        "frn_daily_index_cusip_coverage",
        "auction_term_cusip_coverage",
        "mspd_cashflow_frn_cusip_coverage",
        "daily_to_auction_cusip_overlap",
        "daily_to_cashflow_cusip_overlap",
        "auction_to_cashflow_cusip_overlap",
        "three_way_cusip_overlap",
        "date_key_gap",
    }
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_cusip_coverage
    )
    assert all(
        row["holder_allocation_enabled"] == "false" for row in frn_reset_cusip_coverage
    )
    assert all(
        row["incidence_claim_enabled"] == "false" for row in frn_reset_cusip_coverage
    )
    assert any(
        row["date_key_status"] == "no_common_recurring_reset_date_key"
        and row["coverage_status"] == "source_or_method_blocker_documented"
        for row in frn_reset_cusip_coverage
    )
    assert any(
        row["coverage_component"] == "three_way_cusip_overlap"
        and int(row["overlap_cusips"]) >= 0
        for row in frn_reset_cusip_coverage
    )
    frn_reset_fixture_readiness = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_fixture_readiness_ledger_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["fixture_requirement_id"] for row in frn_reset_fixture_readiness} == {
        "reset_date_boundaries",
        "lockout_periods",
        "leap_days",
        "business_day_holiday_shifts",
        "reopenings",
        "percent_vs_decimal_conventions",
        "missing_field_failures",
    }
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_fixture_readiness
    )
    assert all(
        row["holder_allocation_enabled"] == "false"
        for row in frn_reset_fixture_readiness
    )
    assert all(
        row["incidence_claim_enabled"] == "false" for row in frn_reset_fixture_readiness
    )
    assert any(
        row["fixture_requirement_id"] == "lockout_periods"
        and row["readiness_status"] == "source_or_method_blocker_documented"
        for row in frn_reset_fixture_readiness
    )
    assert any(
        row["fixture_requirement_id"] == "percent_vs_decimal_conventions"
        and row["readiness_status"] == "covered_validation_only"
        for row in frn_reset_fixture_readiness
    )
    assert any(
        "construct_reset_calendar" in row["prohibited_current_use"]
        or "emit_reset_dates" in row["prohibited_current_use"]
        for row in frn_reset_fixture_readiness
    )
    frn_reset_calendar_policy = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_calendar_policy_table.open(encoding="utf-8")
        )
    )
    assert {row["policy_id"] for row in frn_reset_calendar_policy} == {
        "reject_ad_hoc_reconstruction",
        "official_source_field_gate",
        "official_method_implementation_gate",
        "cusip_date_coverage_gate",
        "fixture_audit_gate",
        "explicit_future_opt_in_gate",
    }
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_calendar_policy
    )
    assert all(
        row["holder_allocation_enabled"] == "false" for row in frn_reset_calendar_policy
    )
    assert all(
        row["incidence_claim_enabled"] == "false" for row in frn_reset_calendar_policy
    )
    assert any(
        row["policy_id"] == "reject_ad_hoc_reconstruction"
        and row["policy_status"] == "blocked_current_policy"
        for row in frn_reset_calendar_policy
    )
    assert any(
        row["policy_status"] == "fail_closed_required"
        and "fail closed" in row["fail_closed_rule"]
        for row in frn_reset_calendar_policy
    )
    assert any(
        "infer_calendar_from_term_sheet_prose" in row["prohibited_current_use"]
        for row in frn_reset_calendar_policy
    )
    frn_reset_explicit_opt_in = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_explicit_opt_in_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["switch_name"] for row in frn_reset_explicit_opt_in} >= {
        "explicit_pricing_authorization_enabled",
        "holder_bridge_enabled",
        "tax_assumptions_enabled",
        "mpc_assumptions_enabled",
        "welfare_incidence_enabled",
        "reset_calendar_construction_enabled",
    }
    assert all(
        row["gate_status"] == "disabled_fail_closed_not_pricing"
        for row in frn_reset_explicit_opt_in
    )
    assert all(row["switch_enabled"] == "false" for row in frn_reset_explicit_opt_in)
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_explicit_opt_in
    )
    assert all(
        row["holder_allocation_enabled"] == "false" for row in frn_reset_explicit_opt_in
    )
    assert all(
        row["incidence_claim_enabled"] == "false" for row in frn_reset_explicit_opt_in
    )
    assert all(row["future_opt_in_prerequisite"] for row in frn_reset_explicit_opt_in)
    assert any(
        row["switch_name"] == "reset_calendar_construction_enabled"
        and "construct_reset_calendar" in row["prohibited_current_use"]
        for row in frn_reset_explicit_opt_in
    )
    frn_reset_method_frontier = list(
        csv.DictReader(
            artifacts.treasury_frn_reset_method_frontier_ledger_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["frontier_component"] for row in frn_reset_method_frontier} == {
        "official_source_frontier",
        "method_semantics_frontier",
        "cusip_date_frontier",
        "fixture_frontier",
        "calendar_policy_frontier",
        "explicit_opt_in_frontier",
        "valuation_readiness_frontier",
    }
    assert {
        "reduced",
        "blocked",
        "future_opt_in_only",
    } <= {row["frontier_status"] for row in frn_reset_method_frontier}
    assert all(
        row["pricing_output_enabled"] == "false" for row in frn_reset_method_frontier
    )
    assert all(
        row["holder_allocation_enabled"] == "false" for row in frn_reset_method_frontier
    )
    assert all(
        row["reset_calendar_construction_enabled"] == "false"
        for row in frn_reset_method_frontier
    )
    assert all(
        row["incidence_claim_enabled"] == "false" for row in frn_reset_method_frontier
    )
    assert any(
        row["frontier_component"] == "explicit_opt_in_frontier"
        and row["frontier_status"] == "future_opt_in_only"
        for row in frn_reset_method_frontier
    )
    assert any(
        "construct_reset_calendar" in row["prohibited_current_use"]
        for row in frn_reset_method_frontier
    )
    frontier_official_source_row = [
        row
        for row in frn_reset_method_frontier
        if row["frontier_component"] == "official_source_frontier"
    ][0]
    assert (
        "treasury_frn_reset_official_source_schema_evidence.csv"
        in (frontier_official_source_row["source_artifacts"])
    )
    assert "schema_evidence_rows=5" in frontier_official_source_row["reduced_evidence"]
    assert (
        "official_schema_gap=blocked_reset_calendar_schema_absent"
        in frontier_official_source_row["blocked_evidence"]
    )
    frontier_readiness_row = [
        row
        for row in frn_reset_method_frontier
        if row["frontier_component"] == "valuation_readiness_frontier"
    ][0]
    assert (
        "treasury_valuation_readiness_gate_evidence.csv"
        in (frontier_readiness_row["source_artifacts"])
    )
    assert (
        "readiness_gate_evidence_rows=5" in frontier_readiness_row["reduced_evidence"]
    )
    assert "readiness_gate_blocker_rows=4" in frontier_readiness_row["blocked_evidence"]
    readiness_coverage = list(
        csv.DictReader(
            artifacts.treasury_valuation_readiness_coverage_table.open(encoding="utf-8")
        )
    )
    assert {row["coverage_component"] for row in readiness_coverage} >= {
        "frn_formula_validation_coverage",
        "tips_formula_review_classification",
        "cashflow_edge_source_sampling",
        "frn_recurring_reset_calendar_source",
        "frn_reset_method_reconstruction_policy",
        "reset_accrual_convention_audit",
        "explicit_pricing_policy_switches",
    }
    assert all(row["pricing_output_enabled"] == "false" for row in readiness_coverage)
    assert all(
        row["holder_allocation_enabled"] == "false" for row in readiness_coverage
    )
    assert all(row["incidence_claim_enabled"] == "false" for row in readiness_coverage)
    assert any(
        row["coverage_status"] == "source_or_method_blocker_documented"
        for row in readiness_coverage
    )
    assert any(
        row["coverage_status"] == "policy_switch_disabled" for row in readiness_coverage
    )
    readiness_gate_evidence = list(
        csv.DictReader(
            artifacts.treasury_valuation_readiness_gate_evidence_table.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["gate_evidence_component"] for row in readiness_gate_evidence} == {
        "formula_convention_validation_coverage",
        "cashflow_edge_source_sampling_gate",
        "frn_reset_source_method_blockers",
        "disabled_policy_switch_gate",
        "fail_closed_readiness_conclusion",
    }
    assert all(
        row["pricing_output_enabled"] == "false" for row in readiness_gate_evidence
    )
    assert all(
        row["reset_calendar_construction_enabled"] == "false"
        for row in readiness_gate_evidence
    )
    assert any(
        row["evidence_status"] == "policy_switch_disabled"
        and "pricing_switches_enabled=0" in row["current_evidence"]
        for row in readiness_gate_evidence
    )
    assert any(
        row["evidence_status"] == "disabled_gate_not_pricing"
        and "valuation_engine_ready=false" in row["current_evidence"]
        for row in readiness_gate_evidence
    )
    assert any(
        "construct_reset_calendar_from_blocker_ledgers" in row["prohibited_current_use"]
        for row in readiness_gate_evidence
    )
    assert all(
        row["test_status"] == "fixture_contract_tested_not_pricing"
        for row in edge_fixtures
    )
    assert all(row["example_calculation_name"] for row in edge_fixtures)
    assert all(row["example_expected_value"] for row in edge_fixtures)
    assert all(row["example_observed_value"] for row in edge_fixtures)
    assert all(
        row["example_calculation_status"]
        in {
            "example_validated_not_pricing",
            "example_tolerance_edge_classified_not_pricing",
        }
        for row in edge_fixtures
    )
    assert all(row["pricing_output_enabled"] == "false" for row in edge_fixtures)
    opt_in_contract = list(
        csv.DictReader(
            artifacts.treasury_valuation_opt_in_contract_table.open(encoding="utf-8")
        )
    )
    assert {row["requirement_id"] for row in opt_in_contract} == {
        "audited_conventions",
        "cashflow_edge_fixtures",
        "holder_allocation_gate",
        "explicit_pricing_switch",
    }
    assert all(row["pricing_output_enabled"] == "false" for row in opt_in_contract)
    assert all(row["holder_allocation_enabled"] == "false" for row in opt_in_contract)
    assert all(row["incidence_claim_enabled"] == "false" for row in opt_in_contract)
    explicit_switch = [
        row
        for row in opt_in_contract
        if row["requirement_id"] == "explicit_pricing_switch"
    ][0]
    assert explicit_switch["requirement_satisfied"] == "false"
    assert explicit_switch["switch_enabled"] == "false"
    pricing_switch_audit = list(
        csv.DictReader(
            artifacts.treasury_pricing_switch_audit_table.open(encoding="utf-8")
        )
    )
    assert {row["switch_name"] for row in pricing_switch_audit} >= {
        "explicit_pricing_authorization_enabled",
        "holder_bridge_enabled",
        "tax_assumptions_enabled",
        "mpc_assumptions_enabled",
        "welfare_incidence_enabled",
    }
    assert all(row["switch_enabled"] == "false" for row in pricing_switch_audit)
    assert all(row["pricing_output_enabled"] == "false" for row in pricing_switch_audit)
    assert all(row["blocker_note"] for row in pricing_switch_audit)
    metrics = list(csv.DictReader(artifacts.metrics_table.open(encoding="utf-8")))
    metric_map = {row["metric"]: row for row in metrics}
    assert int(metric_map["treasury_source_backed_edge_sample_rows"]["value"]) >= 1
    assert int(metric_map["treasury_source_edge_classified_rows"]["value"]) >= 0
    assert int(metric_map["treasury_source_edge_blocked_rows"]["value"]) >= 1
    assert int(metric_map["treasury_frn_reset_source_blocker_map_rows"]["value"]) == 3
    assert (
        int(metric_map["treasury_frn_reset_unavailable_calendar_field_rows"]["value"])
        == 1
    )
    assert (
        int(metric_map["treasury_frn_reset_schema_drift_candidate_rows"]["value"]) == 0
    )
    assert int(metric_map["treasury_frn_reset_method_note_rows"]["value"]) == 3
    assert (
        int(metric_map["treasury_frn_reset_official_source_audit_rows"]["value"]) == 4
    )
    assert (
        int(metric_map["treasury_frn_reset_official_audit_blocked_rows"]["value"]) >= 1
    )
    assert (
        int(
            metric_map["treasury_frn_reset_official_source_schema_evidence_rows"][
                "value"
            ]
        )
        == 5
    )
    assert (
        int(
            metric_map["treasury_frn_reset_official_source_schema_blocked_rows"][
                "value"
            ]
        )
        == 1
    )
    assert (
        int(
            metric_map["treasury_frn_reset_official_source_schema_validation_rows"][
                "value"
            ]
        )
        == 2
    )
    assert (
        int(metric_map["treasury_frn_reset_method_semantics_audit_rows"]["value"]) == 6
    )
    assert (
        int(
            metric_map["treasury_frn_reset_method_semantics_context_only_rows"]["value"]
        )
        == 2
    )
    assert int(metric_map["treasury_frn_reset_method_design_ledger_rows"]["value"]) == 6
    assert (
        int(metric_map["treasury_frn_reset_method_design_required_rows"]["value"]) == 6
    )
    assert (
        int(metric_map["treasury_frn_reset_cusip_coverage_ledger_rows"]["value"]) == 8
    )
    assert (
        int(metric_map["treasury_frn_reset_cusip_coverage_blocked_rows"]["value"]) >= 1
    )
    assert (
        int(metric_map["treasury_frn_reset_cusip_three_way_overlap_count"]["value"])
        >= 0
    )
    assert (
        int(metric_map["treasury_frn_reset_fixture_readiness_ledger_rows"]["value"])
        == 7
    )
    assert (
        int(metric_map["treasury_frn_reset_fixture_readiness_blocked_rows"]["value"])
        >= 1
    )
    assert (
        int(metric_map["treasury_frn_reset_fixture_readiness_covered_rows"]["value"])
        >= 1
    )
    assert int(metric_map["treasury_frn_reset_calendar_policy_rows"]["value"]) == 6
    assert (
        int(metric_map["treasury_frn_reset_calendar_policy_fail_closed_rows"]["value"])
        >= 1
    )
    assert (
        int(metric_map["treasury_frn_reset_calendar_policy_blocker_rows"]["value"]) >= 1
    )
    assert int(metric_map["treasury_frn_reset_explicit_opt_in_gate_rows"]["value"]) == 9
    assert (
        int(
            metric_map["treasury_frn_reset_explicit_opt_in_disabled_switch_rows"][
                "value"
            ]
        )
        == 9
    )
    assert (
        int(metric_map["treasury_frn_reset_explicit_opt_in_prerequisite_rows"]["value"])
        == 9
    )
    assert (
        int(metric_map["treasury_frn_reset_method_frontier_ledger_rows"]["value"]) == 7
    )
    assert (
        int(metric_map["treasury_frn_reset_method_frontier_reduced_rows"]["value"]) == 3
    )
    assert (
        int(metric_map["treasury_frn_reset_method_frontier_blocked_rows"]["value"]) == 3
    )
    assert (
        int(
            metric_map["treasury_frn_reset_method_frontier_future_opt_in_rows"]["value"]
        )
        == 1
    )
    assert int(metric_map["treasury_frn_leap_day_source_gap_rows"]["value"]) >= 1
    assert int(metric_map["treasury_frn_leap_day_observed_rows"]["value"]) == 0
    assert int(metric_map["treasury_valuation_readiness_coverage_rows"]["value"]) == 7
    assert (
        int(metric_map["treasury_valuation_readiness_source_blocker_rows"]["value"])
        >= 1
    )
    assert (
        int(metric_map["treasury_valuation_readiness_policy_blocker_rows"]["value"])
        == 1
    )
    assert (
        int(metric_map["treasury_valuation_readiness_gate_evidence_rows"]["value"]) == 5
    )
    assert (
        int(metric_map["treasury_valuation_readiness_gate_blocker_rows"]["value"]) == 4
    )
    assert (
        int(metric_map["treasury_valuation_readiness_gate_disabled_rows"]["value"]) == 2
    )
    assert int(metric_map["treasury_pricing_switches_enabled"]["value"]) == 0
    readiness_gate = list(
        csv.DictReader(
            artifacts.treasury_valuation_engine_readiness_gate_table.open(
                encoding="utf-8"
            )
        )
    )
    assert len(readiness_gate) == 1
    assert readiness_gate[0]["valuation_engine_ready"] == "false"
    assert readiness_gate[0]["pricing_output_enabled"] == "false"
    assert readiness_gate[0]["holder_allocation_enabled"] == "false"
    assert readiness_gate[0]["classified_formula_review_rows"]
    assert readiness_gate[0]["unresolved_formula_review_rows"]
    assert readiness_gate[0]["convention_audit_fixture_rows"] == "2"
    assert readiness_gate[0]["frn_reset_conventions_audited"] == "true"
    assert readiness_gate[0]["tips_accrual_conventions_audited"] == "true"
    assert int(readiness_gate[0]["cashflow_edge_fixture_rows"]) >= 4
    assert int(readiness_gate[0]["source_backed_edge_sample_rows"]) >= 1
    assert int(readiness_gate[0]["source_edge_classified_rows"]) >= 0
    assert int(readiness_gate[0]["source_edge_blocked_rows"]) >= 1
    assert readiness_gate[0]["pricing_switches_enabled"] == "0"
    assert int(readiness_gate[0]["pricing_switches_disabled"]) >= 1
    assert readiness_gate[0]["cashflow_edge_fixtures_defined"] == "true"
    assert (
        readiness_gate[0]["valuation_opt_in_contract_status"]
        == "disabled_requires_explicit_switches"
    )
    assert readiness_gate[0]["explicit_pricing_switch_enabled"] == "false"
    assert readiness_gate[0]["readiness_blocker"]
    assert (
        "valuation_opt_in_contract_disabled_by_policy"
        in readiness_gate[0]["readiness_blocker"]
    )
    assert "pricing_output_disabled_by_policy" in readiness_gate[0]["readiness_blocker"]
    assert readiness_gate[0]["claim_boundary"] == "readiness_gate_not_pricing_engine"
    holder_gate = list(
        csv.DictReader(artifacts.holder_allocation_gate_table.open(encoding="utf-8"))
    )
    assert {row["gate_component"] for row in holder_gate} >= {
        "foreign_stock_context",
        "money_fund_direct_treasury_context",
        "sec_nmfp_mspd_cusip_overlap",
        "valuation_input_gate",
        "final_owner_mapping_readiness",
    }
    assert all(
        "not_final" in row["claim_boundary"] or "not_" in row["claim_boundary"]
        for row in holder_gate
    )
    assert all(row["final_owner_mapping_ready"] == "false" for row in holder_gate)
    assert all(row["welfare_incidence_enabled"] == "false" for row in holder_gate)
    assert all(row["incidence_claim_enabled"] == "false" for row in holder_gate)
    assert {"holder_mapping_design_v0_non_final"} == {
        row["mapping_schema_version"] for row in holder_gate
    }
    assert "cusip" in {row["security_match_key"] for row in holder_gate}
    assert all(row["holder_bridge_enabled"] == "false" for row in holder_gate)
    assert all(row["tax_assumptions_enabled"] == "false" for row in holder_gate)
    assert all(row["mpc_assumptions_enabled"] == "false" for row in holder_gate)
    assert all(row["readiness_blocker"] for row in holder_gate)
    disabled_allocation = list(
        csv.DictReader(
            artifacts.disabled_final_owner_allocation_table.open(encoding="utf-8")
        )
    )
    assert disabled_allocation
    assert {"holder_final_owner_allocation_v0_disabled"} == {
        row["allocation_schema_version"] for row in disabled_allocation
    }
    assert all(
        row["candidate_final_owner_group"] == "not_allocated"
        for row in disabled_allocation
    )
    assert all(row["allocation_weight"] == "" for row in disabled_allocation)
    assert all(row["allocated_cashflow_bil"] == "" for row in disabled_allocation)
    assert all(row["tax_assumption"] == "" for row in disabled_allocation)
    assert all(row["mpc_assumption"] == "" for row in disabled_allocation)
    assert all(row["welfare_incidence_metric"] == "" for row in disabled_allocation)
    assert all(
        row["output_status"] == "disabled_no_weights_no_incidence"
        for row in disabled_allocation
    )
    assert all(row["incidence_claim_enabled"] == "false" for row in disabled_allocation)
    design_ledger = list(
        csv.DictReader(
            artifacts.disabled_allocation_design_ledger_table.open(encoding="utf-8")
        )
    )
    assert design_ledger
    assert {
        "legal_holder",
        "intermediary",
        "beneficial_owner",
        "taxable_owner",
        "mpc",
        "welfare",
    } <= {row["design_layer"] for row in design_ledger}
    assert all(row["switch_enabled"] == "false" for row in design_ledger)
    assert all(row["weight_output_enabled"] == "false" for row in design_ledger)
    assert all(row["cashflow_output_enabled"] == "false" for row in design_ledger)
    assert all(row["tax_output_enabled"] == "false" for row in design_ledger)
    assert all(row["mpc_output_enabled"] == "false" for row in design_ledger)
    assert all(row["welfare_output_enabled"] == "false" for row in design_ledger)
    assert all(row["incidence_claim_enabled"] == "false" for row in design_ledger)
    assert all(
        row["claim_boundary"] == "disabled_design_ledger_not_incidence"
        for row in design_ledger
    )
    distributional_levels = list(
        csv.DictReader(
            artifacts.distributional_exposure_levels_table.open(encoding="utf-8")
        )
    )
    assert {row["net_worth_group"] for row in distributional_levels} >= {
        "top_10_net_worth",
        "middle_40_net_worth",
        "bottom_50_net_worth",
    }
    assert any(row["level_bil"] for row in distributional_levels)
    limitations = list(
        csv.DictReader(artifacts.evidence_limitations_table.open(encoding="utf-8"))
    )
    assert {row["artifact"] for row in limitations} >= {
        "cbo_budget_economic_outlook",
        "treasury_maturity_ladder",
        "treasury_mspd_reconciliation",
        "treasury_mspd_field_coverage",
        "treasury_coupon_cashflow_schedule",
        "treasury_buybacks",
        "public_liability_holder_context",
        "public_liability_fine_holder_context",
        "tic_foreign_holder_reconciliation",
        "tic_foreign_treasury_stock_split",
        "ofr_mmf_treasury_context",
        "sec_nmfp_mmf_treasury_cusip_context",
        "treasury_valuation_inputs",
        "treasury_daily_valuation_paths",
        "treasury_valuation_validation",
        "treasury_valuation_coverage_diagnostics",
        "treasury_tips_formula_review_explanation",
        "treasury_valuation_convention_audit",
        "treasury_cashflow_edge_fixtures",
        "treasury_frn_leap_day_source_gap",
        "treasury_frn_reset_source_blocker_map",
        "treasury_frn_reset_method_note",
        "treasury_frn_reset_official_source_audit",
        "treasury_frn_reset_official_source_schema_evidence",
        "treasury_frn_reset_method_semantics_audit",
        "treasury_frn_reset_method_design_ledger",
        "treasury_frn_reset_cusip_coverage_ledger",
        "treasury_frn_reset_fixture_readiness_ledger",
        "treasury_frn_reset_calendar_generation_policy",
        "treasury_frn_reset_explicit_opt_in_gate",
        "treasury_frn_reset_method_frontier_ledger",
        "treasury_valuation_readiness_coverage",
        "treasury_valuation_readiness_gate_evidence",
        "treasury_pricing_switch_audit_disabled",
        "treasury_valuation_engine_readiness_gate",
        "holder_allocation_gate",
        "holder_final_owner_allocation_disabled",
        "holder_allocation_design_ledger_disabled",
        "distributional_interest_exposure",
        "distributional_exposure_levels",
    }
    treasury_row = next(
        row for row in limitations if row["artifact"] == "treasury_maturity_ladder"
    )
    assert "FRN reset calendars" in treasury_row["needed_fields"]
    assert "mechanical accounting only" in artifacts.impulse_figure.read_text(
        encoding="utf-8"
    )
    provenance = json.loads(artifacts.provenance.read_text(encoding="utf-8"))
    assert provenance["sources"][0]["source_url"].startswith("https://")


def test_assumption_mode_configs_are_editable_and_fail_closed(tmp_path: Path) -> None:
    assumptions = load_ratewall_assumption_sets(
        Path("configs/ratewall_assumption_sets.yml")
    )
    assert len(assumptions) >= 10
    assert {assumption.name for assumption in assumptions} >= {
        "fast_repricing_high_recipient_spend",
        "combined_wall_hit_regime",
    }
    assert all(assumption.editable_label for assumption in assumptions)
    packs = parameter_pack_rows(Path("configs/ratewall_parameter_packs.yml"))
    assert {row["parameter"] for row in packs} >= {
        "public_impulse_multiplier",
        "public_debt_stock_scale",
        "treasury_repricing_speed_share",
        "rate_path_bps_year",
        "fed_liability_stock_scale",
        "future_remittance_drag_timing_share",
        "contractionary_drag_gdp_share",
        "zero_interest_credit_attenuation_share",
        "household_yield_optimization_share",
        "firm_liquid_asset_scale",
    }
    assert all(row["source_note"] for row in packs)
    assert all(row["literature_context"] for row in packs)
    assert all(row["evidence_needed"] for row in packs)
    assert all(row["model_use"] for row in packs)
    assert all(row["review_question"] for row in packs)
    assert all(row["calibration_status"] for row in packs)
    assert all(row["allowed_model_use"] for row in packs)
    assert {row["scenario_implied_only"] for row in packs} == {"true"}
    assert {row["claim_boundary"] for row in packs} == {
        "parameter_pack_context_not_empirical_threshold"
    }
    invalid_assumptions = tmp_path / "bad_assumptions.yml"
    invalid_assumptions.write_text(
        """
schema: ratewall.assumption_sets.v1
assumption_sets:
  - name: bad
    description: Bad share
    horizon: 1y
    policy_rate_bps: 100
    public_impulse_multiplier: 1
    public_debt_stock_scale: 1
    treasury_repricing_speed_share: 1
    rate_path_bps_year: 100
    treasury_repricing_pass_through: 1
    fed_liability_stock_scale: 1
    iorb_pass_through_scale: 1
    on_rrp_pass_through_scale: 1
    current_remittance_timing_share: 1
    future_remittance_drag_timing_share: 1
    future_remittance_drag_treatment: future_public_finance_memo
    treasury_interest_demand_share: 1.5
    fed_interest_demand_share: 0
    iorb_recipient_demand_share: 0
    on_rrp_recipient_demand_share: 0
    current_remittance_demand_share: 0
    future_remittance_drag_demand_share: 0
    fiscal_offset_share: 0
    tga_liquidity_offset_share: 0
    firm_cash_attenuation_share: 0
    safe_asset_allocation_offset_share: 0
    safe_asset_allocation_drag_share: 0
    zero_interest_credit_attenuation_share: 0
    contractionary_drag_gdp_share: 0.001
    borrowing_cost_drag_share: 0.35
    credit_supply_drag_share: 0.20
    asset_price_drag_share: 0.20
    expectations_drag_share: 0.15
    exchange_rate_external_drag_share: 0.10
    split_denominator_total_drag_multiplier: 1
    benchmark_uncertainty_share: 0
    assumption_status: assumption_mode_speculative
    source_status: test
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="treasury_interest_demand_share"):
        load_ratewall_assumption_sets(invalid_assumptions)
    invalid_pack = tmp_path / "bad_packs.yml"
    invalid_pack.write_text(
        """
schema: ratewall.parameter_packs.v1
parameter_packs:
  - parameter: bad_share
    channel: test
    unit: share
    low: 0.2
    base: 0.1
    high: 0.3
    source_status: assumption_only
    rationale: invalid ordering
    source_note: test note
    literature_context: test context
    evidence_needed: test evidence
    review_priority: low
    model_use: test model use
    review_question: test review question
    plausibility_status: review
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="low <= base <= high"):
        parameter_pack_rows(invalid_pack)


def test_scenario_table_and_empirical_specs_are_reproducible(tmp_path: Path) -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    snapshot = build_snapshot_bundle(
        registry=registry,
        output=tmp_path / "snapshot.json",
        mode="demo",
    )

    scenario_path = build_scenario_table(
        snapshot_bundle=snapshot,
        output=tmp_path / "outputs" / "tables" / "scenarios.csv",
    )
    scenario_rows = list(csv.DictReader(scenario_path.open(encoding="utf-8")))
    assert {row["scenario"] for row in scenario_rows} >= {
        "baseline_100bps",
        "low_pass_through",
        "no_remittance_offset",
        "high_rate_200bps",
    }
    assert scenario_rows[0]["cbo_2036_net_interest_gdp"]
    assert scenario_rows[0]["mspd_table3_snapshot_kind"] in {
        "demo_stub",
        "fallback_stub",
    }
    if scenario_rows[0]["mspd_table3_snapshot_kind"] == "fallback_stub":
        assert scenario_rows[0]["weakest_source_status"].startswith(
            "fallback_context_only"
        )
        assert (
            scenario_rows[0]["repricing_anchor_status"]
            == "anchor_fallback_not_live_security_level"
        )
        assert (
            scenario_rows[0]["allowed_use"]
            == "fallback_context_only_scenario_diagnostic"
        )
        assert scenario_rows[0]["promotion_gate_status"].startswith("blocked_not_live")
    else:
        assert scenario_rows[0]["weakest_source_status"]
        assert scenario_rows[0]["repricing_anchor_status"]
        assert scenario_rows[0]["allowed_use"] == "source_labeled_scenario_diagnostic"
        assert (
            scenario_rows[0]["promotion_gate_status"] == "nonpromotion_scenario_context"
        )
    assert scenario_rows[0]["private_investor_holder_share"]
    assert scenario_rows[0]["households_nonprofits_fine_holder_share"]
    assert scenario_rows[0]["dfa_top10_government_muni_securities_gdp"]
    assert scenario_rows[0]["treasury_buybacks_accepted_bil"]
    assert scenario_rows[0]["tic_foreign_official_net_purchases_bil"]
    assert scenario_rows[0]["tic_foreign_official_treasury_stock_share"]
    assert scenario_rows[0]["ofr_mmf_direct_treasury_holdings_bil"]
    assert scenario_rows[0]["sec_nmfp_direct_treasury_holdings_bil"]
    assert scenario_rows[0]["frn_latest_spread_pct"]
    assert scenario_rows[0]["tips_latest_index_ratio_on_issue"]
    assert scenario_rows[0]["frn_latest_daily_index_pct"]
    assert scenario_rows[0]["tips_latest_daily_index_ratio"]
    assert (
        scenario_rows[0]["frn_formula_check_status"] == "formula_validated_not_pricing"
    )
    assert (
        scenario_rows[0]["tips_formula_check_status"] == "formula_validated_not_pricing"
    )
    assert scenario_rows[0]["holder_allocation_gate_status"]
    assert scenario_rows[0]["final_owner_mapping_ready"] == "false"
    assert (
        scenario_rows[0]["final_owner_allocation_output_status"]
        == "disabled_no_weights_no_incidence"
    )
    assert (
        scenario_rows[0]["final_owner_allocation_schema_version"]
        == "holder_final_owner_allocation_v0_disabled"
    )
    assert (
        scenario_rows[0]["allocation_design_ledger_status"]
        == "disabled_design_layers_no_weights"
    )
    assert (
        scenario_rows[0]["allocation_design_ledger_schema_version"]
        == "holder_allocation_design_ledger_v0_disabled"
    )
    assert scenario_rows[0]["welfare_incidence_enabled"] == "false"
    assert (
        scenario_rows[0]["holder_mapping_schema_version"]
        == "holder_mapping_design_v0_non_final"
    )
    assert scenario_rows[0]["holder_bridge_enabled"] == "false"
    assert scenario_rows[0]["tax_assumptions_enabled"] == "false"
    assert scenario_rows[0]["mpc_assumptions_enabled"] == "false"
    assert scenario_rows[0]["incidence_claim_enabled"] == "false"
    assert scenario_rows[0]["sec_nmfp_mspd_matched_cusip_count"]
    assert scenario_rows[0]["valuation_input_gate_status"] == "inputs_validated"
    assert scenario_rows[0]["valuation_engine_readiness_status"] in {
        "blocked_pending_formula_review_resolution",
        "blocked_pending_reset_accrual_convention_audit",
        "audited_conventions_pricing_disabled",
        "disabled_opt_in_contract_pricing_disabled",
    }
    assert scenario_rows[0]["valuation_pricing_output_enabled"] == "false"
    assert (
        scenario_rows[0]["valuation_opt_in_contract_status"]
        == "disabled_requires_explicit_switches"
    )
    assert scenario_rows[0]["valuation_readiness_coverage_rows"] == "7"
    assert int(scenario_rows[0]["valuation_readiness_source_blocker_rows"]) >= 1
    assert scenario_rows[0]["valuation_readiness_policy_blocker_rows"] == "1"
    assert scenario_rows[0]["valuation_readiness_gate_evidence_rows"] == "5"
    assert scenario_rows[0]["valuation_readiness_gate_blocker_rows"] == "4"
    assert scenario_rows[0]["valuation_readiness_gate_disabled_rows"] == "2"
    assert scenario_rows[0]["valuation_frn_reset_official_source_audit_rows"] == "4"
    assert int(scenario_rows[0]["valuation_frn_reset_official_audit_blocked_rows"]) >= 1
    assert (
        scenario_rows[0]["valuation_frn_reset_official_source_schema_evidence_rows"]
        == "5"
    )
    assert (
        scenario_rows[0]["valuation_frn_reset_official_source_schema_blocked_rows"]
        == "1"
    )
    assert (
        scenario_rows[0]["valuation_frn_reset_official_source_schema_validation_rows"]
        == "2"
    )
    assert scenario_rows[0]["valuation_frn_reset_method_semantics_audit_rows"] == "6"
    assert (
        scenario_rows[0]["valuation_frn_reset_method_semantics_context_only_rows"]
        == "2"
    )
    assert scenario_rows[0]["valuation_frn_reset_method_design_ledger_rows"] == "6"
    assert scenario_rows[0]["valuation_frn_reset_method_design_required_rows"] == "6"
    assert scenario_rows[0]["valuation_frn_reset_cusip_coverage_ledger_rows"] == "8"
    assert int(scenario_rows[0]["valuation_frn_reset_cusip_coverage_blocked_rows"]) >= 1
    assert (
        int(scenario_rows[0]["valuation_frn_reset_cusip_three_way_overlap_count"]) >= 0
    )
    assert scenario_rows[0]["valuation_frn_reset_fixture_readiness_ledger_rows"] == "7"
    assert (
        int(scenario_rows[0]["valuation_frn_reset_fixture_readiness_blocked_rows"]) >= 1
    )
    assert (
        int(scenario_rows[0]["valuation_frn_reset_fixture_readiness_covered_rows"]) >= 1
    )
    assert scenario_rows[0]["valuation_frn_reset_calendar_policy_rows"] == "6"
    assert (
        int(scenario_rows[0]["valuation_frn_reset_calendar_policy_fail_closed_rows"])
        >= 1
    )
    assert (
        int(scenario_rows[0]["valuation_frn_reset_calendar_policy_blocker_rows"]) >= 1
    )
    assert scenario_rows[0]["valuation_frn_reset_explicit_opt_in_gate_rows"] == "9"
    assert (
        scenario_rows[0]["valuation_frn_reset_explicit_opt_in_disabled_switch_rows"]
        == "9"
    )
    assert (
        scenario_rows[0]["valuation_frn_reset_explicit_opt_in_prerequisite_rows"] == "9"
    )
    assert scenario_rows[0]["valuation_frn_reset_method_frontier_ledger_rows"] == "7"
    assert scenario_rows[0]["valuation_frn_reset_method_frontier_reduced_rows"] == "3"
    assert scenario_rows[0]["valuation_frn_reset_method_frontier_blocked_rows"] == "3"
    assert (
        scenario_rows[0]["valuation_frn_reset_method_frontier_future_opt_in_rows"]
        == "1"
    )
    assert int(scenario_rows[0]["valuation_cashflow_edge_fixture_rows"]) >= 4
    assert int(scenario_rows[0]["valuation_source_backed_edge_sample_rows"]) >= 1
    assert int(scenario_rows[0]["valuation_source_edge_classified_rows"]) >= 0
    assert int(scenario_rows[0]["valuation_source_edge_blocked_rows"]) >= 1
    assert int(scenario_rows[0]["valuation_pricing_switch_audit_rows"]) >= 1
    assert scenario_rows[0]["valuation_pricing_switches_enabled"] == "0"
    assert int(scenario_rows[0]["valuation_pricing_switches_disabled"]) >= 1
    assert scenario_rows[0]["valuation_explicit_pricing_switch_enabled"] == "false"
    assert scenario_rows[0]["valuation_formula_review_rows"]
    assert scenario_rows[0]["valuation_classified_formula_review_rows"]
    assert scenario_rows[0]["valuation_unresolved_formula_review_rows"]
    assert (
        scenario_rows[0]["ratewall_threshold_layer_status"]
        == "conditional_scenario_context_enabled"
    )
    assert (
        scenario_rows[0]["ratewall_threshold_claim_boundary"]
        == "conditional_threshold_simulation_not_policy_failure_or_causal_claim"
    )
    assert (
        scenario_rows[0]["release_13_calibration_layer_status"]
        == "calibration_range_sensitivity_review_not_promotion"
    )
    assert (
        "du_outlay_share" in scenario_rows[0]["release_13_remaining_speculative_inputs"]
    )
    assert (
        scenario_rows[0]["release_13_calibration_claim_boundary"]
        == "calibration_range_sensitivity_review_not_final_policy_failure_or_causal_claim"
    )
    assert (
        scenario_rows[0]["release_14_validation_layer_status"]
        == "historical_threshold_validation_generated_not_promoted"
    )
    assert (
        scenario_rows[0]["release_14_policy_boundary_claim"]
        == "sensitivity_diagnostics_only_no_universal_ratewall_date"
    )
    assert (
        "dynamic_contractionary_benchmark"
        in (scenario_rows[0]["release_14_remaining_promotion_blockers"])
    )
    assert (
        scenario_rows[0]["release_15_publication_decision_status"]
        == "publish_bounded_package_with_final_blockers"
    )
    assert (
        scenario_rows[0]["release_15_bounded_publication_claim"]
        == "accounting_and_conditional_sensitivity_only"
    )
    assert scenario_rows[0]["release_15_promotion_claim_enabled"] == "false"
    assert (
        scenario_rows[0]["release_16_closeout_status"]
        == "bounded_publication_closeout_no_further_promotion"
    )
    assert scenario_rows[0]["release_16_final_no_further_promotion"] == "true"
    assert (
        scenario_rows[0]["release_16_source_resolution_claim_boundary"]
        == "source_resolution_closeout_not_claim_promotion"
    )
    assert (
        scenario_rows[0]["release_17_external_review_status"]
        == "publication_polish_and_reviewer_consistency_audit_passed"
    )
    assert (
        scenario_rows[0]["release_17_blocker_reopen_status"]
        == "no_blockers_reopened_absent_new_source_method_evidence"
    )
    assert (
        scenario_rows[0]["release_17_publication_polish_claim_boundary"]
        == "release_17_polish_not_claim_promotion"
    )
    assert scenario_rows[0]["financialization_causal_claim_enabled"] == "false"

    specs_path = write_empirical_specs(
        tmp_path / "outputs" / "empirical" / "specs.json"
    )
    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    assert specs[0]["shock"] == "high_frequency_monetary_surprise"

    shocks_path = write_shock_dataset_catalog(
        tmp_path / "outputs" / "empirical" / "monetary_shock_datasets.json"
    )
    shocks = json.loads(shocks_path.read_text(encoding="utf-8"))
    assert shocks[0]["dataset_id"] == "sf_fed_monetary_policy_surprises"
    assert shocks[0]["shock_column"] == "orthogonalized_surprise_bps"

    smoke_path = write_empirical_smoke_panel(
        snapshot_bundle=snapshot,
        output=tmp_path / "outputs" / "empirical" / "shock_state_smoke.csv",
    )
    smoke_rows = list(csv.DictReader(smoke_path.open(encoding="utf-8")))
    assert smoke_rows[0]["shock_column"] == "orthogonalized_surprise_bps"
    assert smoke_rows[0]["state_alignment_scope"] in {
        "historical_fred_reserves_rrp_gdp",
        "historical_fred_reserves_gdp_missing_rrp",
        "insufficient_historical_fred_state",
    }
    assert smoke_rows[0]["treasury_repricing_scope"] in {
        "latest_mspd_table_3_proxy",
        "historical_debt_latest_mspd_table_3_proxy",
    }
    assert smoke_rows[0]["guardrail"] == "not_raw_policy_rate_change"

    empirical_results_path = write_empirical_results(
        snapshot_bundle=snapshot,
        output=tmp_path / "outputs" / "tables" / "ratewall_empirical_results.csv",
        outcome_panel=tmp_path
        / "outputs"
        / "tables"
        / "ratewall_empirical_outcome_panel.csv",
        figure=tmp_path
        / "outputs"
        / "figures"
        / "ratewall_empirical_state_association.svg",
        report=tmp_path
        / "outputs"
        / "reports"
        / "ratewall_empirical_results_summary.md",
        final_paper_support=tmp_path
        / "outputs"
        / "reports"
        / "ratewall_final_paper_support.md",
    )
    empirical_rows = list(csv.DictReader(empirical_results_path.open(encoding="utf-8")))
    outcome_rows = list(
        csv.DictReader(
            (
                tmp_path / "outputs" / "tables" / "ratewall_empirical_outcome_panel.csv"
            ).open(encoding="utf-8")
        )
    )
    assert outcome_rows[0]["outcome_source"] in {"PCEPILFE", "INDPRO", "UNRATE"}
    assert outcome_rows[0]["raw_rate_change_identification_rejected"] == "true"
    assert any(
        row["result_status"] == "final_documented_blocker_for_full_causal_lp_proxy_svar"
        for row in empirical_rows
    )
    assert {
        "admissible_shock_state_association_not_causal_lp",
        "admissible_event_study_estimate_with_limitations",
        "final_documented_blocker_for_full_causal_lp_proxy_svar",
    } & {row["result_status"] for row in empirical_rows}
    assert {
        row["raw_rate_change_identification_rejected"] for row in empirical_rows
    } == {"true"}
    assert {row["pricing_output_enabled"] for row in empirical_rows} == {"false"}
    assert {row["incidence_claim_enabled"] for row in empirical_rows} == {"false"}
    assert "descriptive, not causal estimates" in (
        tmp_path / "outputs" / "figures" / "ratewall_empirical_state_association.svg"
    ).read_text(encoding="utf-8")
    assert "Deck-Ready Empirical Slide" in (
        tmp_path / "outputs" / "reports" / "ratewall_final_paper_support.md"
    ).read_text(encoding="utf-8")
    causal_audit = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_causal_identification_audit.csv"
            ).open(encoding="utf-8")
        )
    )
    causal_blocker = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_causal_defensibility_blocker.csv"
            ).open(encoding="utf-8")
        )
    )
    robustness_manifest = json.loads(
        (
            tmp_path
            / "outputs"
            / "tables"
            / "ratewall_empirical_robustness_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert any(
        row["audit_component"] == "dynamic_lp_proxy_svar_identification"
        and row["audit_status"] == "blocked"
        for row in causal_audit
    )
    assert causal_blocker[0]["blocker_status"] == "final_blocker_documented"
    assert causal_blocker[0]["raw_rate_change_identification_rejected"] == "true"
    assert robustness_manifest["causal_claim_enabled"] is False
    assert robustness_manifest["raw_rate_change_identification_rejected"] is True
    assert "Release 1.1 Causal-Identification Appendix" in (
        tmp_path / "outputs" / "reports" / "ratewall_causal_identification_appendix.md"
    ).read_text(encoding="utf-8")
    assert "Reviewer Limitations Memo" in (
        tmp_path / "outputs" / "reports" / "ratewall_reviewer_limitations_memo.md"
    ).read_text(encoding="utf-8")
    support_rows = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_event_study_support_diagnostics.csv"
            ).open(encoding="utf-8")
        )
    )
    robustness_rows = list(
        csv.DictReader(
            (
                tmp_path / "outputs" / "tables" / "ratewall_event_study_robustness.csv"
            ).open(encoding="utf-8")
        )
    )
    submission_decisions = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_submission_identification_decision.csv"
            ).open(encoding="utf-8")
        )
    )
    assert support_rows
    assert all(
        row["raw_rate_change_identification_rejected"] == "true" for row in support_rows
    )
    if robustness_rows:
        assert {
            "baseline_external_shock_event_study",
            "winsorized_shock_5_95",
            "drop_largest_absolute_surprise",
            "predetermined_outcome_balance",
        } <= {row["diagnostic_type"] for row in robustness_rows}
    assert any(
        row["decision_id"] == "release_2_0_submission_decision"
        and row["decision_status"]
        in {
            "submission_ready_bounded_event_study_full_lp_proxy_svar_blocked",
            "submission_blocked_pending_support",
        }
        for row in submission_decisions
    )
    assert any(
        row["decision_id"] == "full_lp_proxy_svar_identification"
        and row["decision_status"] == "blocked"
        for row in submission_decisions
    )
    assert all(
        row["full_lp_proxy_svar_claim_enabled"] == "false"
        for row in submission_decisions
    )
    assert "Release 2.0 Submission Causal Appendix" in (
        tmp_path / "outputs" / "reports" / "ratewall_submission_causal_appendix.md"
    ).read_text(encoding="utf-8")
    assert "External Review Response Packet" in (
        tmp_path / "outputs" / "reports" / "ratewall_external_review_response_packet.md"
    ).read_text(encoding="utf-8")
    assert (
        tmp_path / "outputs" / "figures" / "ratewall_event_study_robustness.svg"
    ).exists()
    dynamic_lp_rows = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_dynamic_lp_feasibility_diagnostics.csv"
            ).open(encoding="utf-8")
        )
    )
    proxy_svar_rows = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_proxy_svar_feasibility_diagnostics.csv"
            ).open(encoding="utf-8")
        )
    )
    dynamic_blocker = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_dynamic_causal_final_blocker.csv"
            ).open(encoding="utf-8")
        )
    )
    journal_manifest = json.loads(
        (
            tmp_path
            / "outputs"
            / "tables"
            / "ratewall_journal_submission_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert {row["gate_id"] for row in dynamic_lp_rows} >= {
        "pre_specified_lag_control_matrix",
        "hac_or_clustered_uncertainty",
        "pretrend_placebo_dynamic_diagnostics",
    }
    assert any(row["gate_status"] == "blocked" for row in dynamic_lp_rows)
    assert any(row["gate_status"] == "blocked" for row in proxy_svar_rows)
    assert all(row["dynamic_lp_claim_enabled"] == "false" for row in dynamic_lp_rows)
    assert all(row["proxy_svar_claim_enabled"] == "false" for row in proxy_svar_rows)
    assert (
        dynamic_blocker[0]["blocker_status"] == "journal_grade_final_blocker_documented"
    )
    assert dynamic_blocker[0]["dynamic_lp_claim_enabled"] == "false"
    assert dynamic_blocker[0]["proxy_svar_claim_enabled"] == "false"
    assert (
        journal_manifest["release_3_0_decision"]
        == "journal_submission_bounded_event_study_dynamic_lp_proxy_svar_blocked"
    )
    assert journal_manifest["dynamic_lp_claim_enabled"] is False
    assert journal_manifest["proxy_svar_claim_enabled"] is False
    assert "Release 3.0 Journal-Submission Appendix" in (
        tmp_path / "outputs" / "reports" / "ratewall_journal_submission_appendix.md"
    ).read_text(encoding="utf-8")
    assert "Dynamic-Causal Blocker Memo" in (
        tmp_path / "outputs" / "reports" / "ratewall_dynamic_causal_blocker_memo.md"
    ).read_text(encoding="utf-8")
    assert "Referee Response Compendium" in (
        tmp_path / "outputs" / "reports" / "ratewall_referee_response_compendium.md"
    ).read_text(encoding="utf-8")
    assert (
        tmp_path / "outputs" / "figures" / "ratewall_dynamic_causal_gate.svg"
    ).exists()
    hac_rows = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_event_study_hac_diagnostics.csv"
            ).open(encoding="utf-8")
        )
    )
    placebo_rows = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_pretrend_placebo_diagnostics.csv"
            ).open(encoding="utf-8")
        )
    )
    promotion_contract = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_dynamic_identification_promotion_contract_disabled.csv"
            ).open(encoding="utf-8")
        )
    )
    release_4_blocker = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_4_0_dynamic_causal_final_blocker.csv"
            ).open(encoding="utf-8")
        )
    )
    release_4_manifest = json.loads(
        (
            tmp_path
            / "outputs"
            / "tables"
            / "ratewall_release_4_0_submission_manifest.json"
        ).read_text(encoding="utf-8")
    )
    controlled_lp_results = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_controlled_dynamic_lp_results.csv"
            ).open(encoding="utf-8")
        )
    )
    controlled_lp_support = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_controlled_dynamic_lp_support_diagnostics.csv"
            ).open(encoding="utf-8")
        )
    )
    release_5_decision = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_5_0_identification_decision.csv"
            ).open(encoding="utf-8")
        )
    )
    release_5_proxy_blocker = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_5_0_proxy_svar_final_blocker.csv"
            ).open(encoding="utf-8")
        )
    )
    release_5_manifest = json.loads(
        (
            tmp_path
            / "outputs"
            / "tables"
            / "ratewall_release_5_0_dynamic_causal_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert hac_rows
    assert placebo_rows
    assert promotion_contract
    assert release_4_blocker
    assert {row["dynamic_lp_claim_enabled"] for row in hac_rows + placebo_rows} == {
        "false"
    }
    assert {row["proxy_svar_claim_enabled"] for row in hac_rows} == {"false"}
    assert all(
        row["full_lp_proxy_svar_claim_enabled"] == "false" for row in promotion_contract
    )
    assert any(
        row["requirement_id"] == "explicit_claim_promotion_switch"
        and row["requirement_status"] == "blocked"
        for row in promotion_contract
    )
    assert (
        release_4_blocker[0]["blocker_status"]
        == "journal_grade_final_blocker_strengthened"
    )
    assert release_4_blocker[0]["dynamic_lp_claim_enabled"] == "false"
    assert release_4_blocker[0]["proxy_svar_claim_enabled"] == "false"
    assert (
        release_4_manifest["release_4_0_decision"]
        == "final_bounded_journal_submission_dynamic_design_blocked"
    )
    assert release_4_manifest["dynamic_lp_claim_enabled"] is False
    assert release_4_manifest["proxy_svar_claim_enabled"] is False
    assert "Release 4.0 Final Submission Memo" in (
        tmp_path
        / "outputs"
        / "reports"
        / "ratewall_release_4_0_final_submission_memo.md"
    ).read_text(encoding="utf-8")
    assert "RateWall Release 4.0 Referee Packet" in (
        tmp_path / "outputs" / "reports" / "ratewall_release_4_0_referee_packet.md"
    ).read_text(encoding="utf-8")
    assert (
        tmp_path
        / "outputs"
        / "figures"
        / "ratewall_release_4_0_identification_frontier.svg"
    ).exists()
    assert controlled_lp_results
    assert controlled_lp_support
    assert release_5_decision
    assert release_5_proxy_blocker
    assert {
        row["raw_rate_change_identification_rejected"] for row in release_5_decision
    } == {"true"}
    assert {row["proxy_svar_claim_enabled"] for row in release_5_decision} == {"false"}
    assert {row["pricing_output_enabled"] for row in release_5_decision} == {"false"}
    assert {row["incidence_claim_enabled"] for row in release_5_decision} == {"false"}
    assert release_5_proxy_blocker[0]["proxy_svar_claim_enabled"] == "false"
    assert release_5_proxy_blocker[0]["full_lp_proxy_svar_claim_enabled"] == "false"
    assert release_5_manifest["release"] == "5.0"
    assert release_5_manifest["raw_rate_change_identification_rejected"] is True
    assert release_5_manifest["proxy_svar_claim_enabled"] is False
    assert release_5_manifest["pricing_output_enabled"] is False
    assert "Release 5.0 Dynamic LP Appendix" in (
        tmp_path / "outputs" / "reports" / "ratewall_release_5_0_dynamic_lp_appendix.md"
    ).read_text(encoding="utf-8")
    assert "RateWall Release 5.0 Referee Response" in (
        tmp_path / "outputs" / "reports" / "ratewall_release_5_0_referee_response.md"
    ).read_text(encoding="utf-8")
    assert (
        tmp_path
        / "outputs"
        / "figures"
        / "ratewall_release_5_0_dynamic_lp_estimates.svg"
    ).exists()
    proxy_svar_system_panel = list(
        csv.DictReader(
            (
                tmp_path / "outputs" / "tables" / "ratewall_proxy_svar_system_panel.csv"
            ).open(encoding="utf-8")
        )
    )
    proxy_svar_relevance = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_proxy_svar_proxy_relevance_diagnostics.csv"
            ).open(encoding="utf-8")
        )
    )
    proxy_svar_residual = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_proxy_svar_residual_diagnostics.csv"
            ).open(encoding="utf-8")
        )
    )
    proxy_svar_timing = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_proxy_svar_timing_support_diagnostics.csv"
            ).open(encoding="utf-8")
        )
    )
    release_6_decision = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_6_0_identification_decision.csv"
            ).open(encoding="utf-8")
        )
    )
    release_6_proxy_blocker = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_6_0_proxy_svar_final_blocker.csv"
            ).open(encoding="utf-8")
        )
    )
    release_6_valuation_frontier = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_6_0_valuation_incidence_frontier_disabled.csv"
            ).open(encoding="utf-8")
        )
    )
    release_6_manifest = json.loads(
        (
            tmp_path
            / "outputs"
            / "tables"
            / "ratewall_release_6_0_system_identification_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert proxy_svar_system_panel
    assert proxy_svar_relevance
    assert proxy_svar_residual
    assert proxy_svar_timing
    assert release_6_decision
    assert release_6_proxy_blocker
    assert release_6_valuation_frontier
    assert {row["proxy_svar_claim_enabled"] for row in proxy_svar_system_panel} == {
        "false"
    }
    assert {
        row["raw_rate_change_identification_rejected"] for row in release_6_decision
    } == {"true"}
    assert {
        row["system_identification_claim_enabled"] for row in release_6_decision
    } == {"false"}
    assert {row["pricing_output_enabled"] for row in release_6_decision} == {"false"}
    assert {
        row["reset_calendar_construction_enabled"] for row in release_6_decision
    } == {"false"}
    assert all(
        row["pricing_output_enabled"] == "false"
        and row["incidence_claim_enabled"] == "false"
        for row in release_6_valuation_frontier
    )
    assert (
        release_6_manifest["release_6_0_decision"]
        == "proxy_svar_system_blocked_bounded_dynamic_lp_retained"
    )
    assert release_6_manifest["proxy_svar_claim_enabled"] is False
    assert release_6_manifest["system_identification_claim_enabled"] is False
    assert release_6_manifest["pricing_output_enabled"] is False
    assert "Release 6.0 Proxy-SVAR/System Identification Appendix" in (
        tmp_path
        / "outputs"
        / "reports"
        / "ratewall_release_6_0_proxy_svar_system_appendix.md"
    ).read_text(encoding="utf-8")
    assert "RateWall Release 6.0 Reviewer Response" in (
        tmp_path / "outputs" / "reports" / "ratewall_release_6_0_reviewer_response.md"
    ).read_text(encoding="utf-8")
    assert (
        tmp_path
        / "outputs"
        / "figures"
        / "ratewall_release_6_0_system_identification_gate.svg"
    ).exists()
    release_7_lag_selection = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_7_0_var_lag_selection.csv"
            ).open(encoding="utf-8")
        )
    )
    release_7_estimates = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_7_0_reduced_form_system_estimates.csv"
            ).open(encoding="utf-8")
        )
    )
    release_7_covariance = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_7_0_residual_covariance.csv"
            ).open(encoding="utf-8")
        )
    )
    release_7_proxy_support = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_7_0_proxy_relevance_support.csv"
            ).open(encoding="utf-8")
        )
    )
    release_7_timing_audit = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv"
            ).open(encoding="utf-8")
        )
    )
    release_7_contract = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_7_0_claim_promotion_contract_disabled.csv"
            ).open(encoding="utf-8")
        )
    )
    release_7_decision = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_7_0_identification_decision.csv"
            ).open(encoding="utf-8")
        )
    )
    release_7_blocker = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_7_0_proxy_svar_final_blocker.csv"
            ).open(encoding="utf-8")
        )
    )
    release_7_manifest = json.loads(
        (
            tmp_path
            / "outputs"
            / "tables"
            / "ratewall_release_7_0_system_identification_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert release_7_lag_selection
    assert release_7_estimates
    assert release_7_covariance
    assert release_7_proxy_support
    assert release_7_timing_audit
    assert release_7_contract
    assert release_7_decision
    assert release_7_blocker
    assert {row["proxy_svar_claim_enabled"] for row in release_7_decision} == {"false"}
    assert {
        row["system_identification_claim_enabled"] for row in release_7_decision
    } == {"false"}
    assert {row["pricing_output_enabled"] for row in release_7_decision} == {"false"}
    assert {
        row["reset_calendar_construction_enabled"] for row in release_7_decision
    } == {"false"}
    assert {
        row["dynamic_identification_promotion_enabled"] for row in release_7_contract
    } == {"false"}
    assert (
        release_7_manifest["release_7_0_decision"]
        == "proxy_svar_system_blocked_reduced_form_diagnostics_published"
    )
    assert release_7_manifest["proxy_svar_claim_enabled"] is False
    assert release_7_manifest["system_identification_claim_enabled"] is False
    assert release_7_manifest["pricing_output_enabled"] is False
    assert "RateWall Release 7.0 System-Identification Appendix" in (
        tmp_path
        / "outputs"
        / "reports"
        / "ratewall_release_7_0_system_identification_appendix.md"
    ).read_text(encoding="utf-8")
    assert "RateWall Release 7.0 External Review Packet" in (
        tmp_path
        / "outputs"
        / "reports"
        / "ratewall_release_7_0_external_review_packet.md"
    ).read_text(encoding="utf-8")
    assert (
        tmp_path
        / "outputs"
        / "figures"
        / "ratewall_release_7_0_system_identification_frontier.svg"
    ).exists()
    release_8_proxy_specs = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_8_0_proxy_specification_audit.csv"
            ).open(encoding="utf-8")
        )
    )
    release_8_gaps = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_8_0_structural_gap_ledger.csv"
            ).open(encoding="utf-8")
        )
    )
    release_8_proof = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_8_0_nonpromotion_proof.csv"
            ).open(encoding="utf-8")
        )
    )
    release_8_decision = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_8_0_identification_decision.csv"
            ).open(encoding="utf-8")
        )
    )
    release_8_manifest = json.loads(
        (
            tmp_path
            / "outputs"
            / "tables"
            / "ratewall_release_8_0_system_identification_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert release_8_proxy_specs
    assert release_8_gaps
    assert release_8_proof
    assert release_8_decision
    assert {row["proxy_svar_claim_enabled"] for row in release_8_decision} == {"false"}
    assert {
        row["system_identification_claim_enabled"] for row in release_8_decision
    } == {"false"}
    assert {row["pricing_output_enabled"] for row in release_8_decision} == {"false"}
    assert {
        row["reset_calendar_construction_enabled"] for row in release_8_decision
    } == {"false"}
    assert {
        row["dynamic_identification_promotion_enabled"] for row in release_8_gaps
    } == {"false"}
    assert (
        release_8_manifest["release_8_0_decision"]
        == "structural_system_identification_not_promoted_final_bounded_package"
    )
    assert release_8_manifest["proxy_svar_claim_enabled"] is False
    assert release_8_manifest["system_identification_claim_enabled"] is False
    assert release_8_manifest["pricing_output_enabled"] is False
    assert "RateWall Release 8.0 System-Identification Non-Promotion Appendix" in (
        tmp_path
        / "outputs"
        / "reports"
        / "ratewall_release_8_0_system_nonpromotion_appendix.md"
    ).read_text(encoding="utf-8")
    assert "RateWall Release 8.0 Reviewer Response" in (
        tmp_path / "outputs" / "reports" / "ratewall_release_8_0_reviewer_response.md"
    ).read_text(encoding="utf-8")
    assert (
        tmp_path / "outputs" / "figures" / "ratewall_release_8_0_nonpromotion_gate.svg"
    ).exists()
    release_9_registry = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_9_0_external_proxy_source_registry.csv"
            ).open(encoding="utf-8")
        )
    )
    release_9_support = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_9_0_external_proxy_support_audit.csv"
            ).open(encoding="utf-8")
        )
    )
    release_9_decision = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_9_0_structural_identification_decision.csv"
            ).open(encoding="utf-8")
        )
    )
    release_9_proof = list(
        csv.DictReader(
            (
                tmp_path
                / "outputs"
                / "tables"
                / "ratewall_release_9_0_final_nonpromotion_proof.csv"
            ).open(encoding="utf-8")
        )
    )
    release_9_manifest = json.loads(
        (
            tmp_path
            / "outputs"
            / "tables"
            / "ratewall_release_9_0_structural_identification_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert release_9_registry
    assert release_9_support
    assert release_9_decision
    assert release_9_proof
    assert {
        row["raw_rate_change_identification_rejected"] for row in release_9_support
    } == {"true"}
    assert {row["proxy_svar_claim_enabled"] for row in release_9_decision} == {"false"}
    assert {
        row["system_identification_claim_enabled"] for row in release_9_decision
    } == {"false"}
    assert {row["pricing_output_enabled"] for row in release_9_decision} == {"false"}
    assert {
        row["reset_calendar_construction_enabled"] for row in release_9_decision
    } == {"false"}
    assert (
        release_9_manifest["release_9_0_decision"]
        == "structural_system_identification_not_promoted_final_publication_boundary"
    )
    assert release_9_manifest["proxy_svar_claim_enabled"] is False
    assert release_9_manifest["system_identification_claim_enabled"] is False
    assert release_9_manifest["pricing_output_enabled"] is False
    assert "RateWall Release 9.0 Structural Boundary Appendix" in (
        tmp_path
        / "outputs"
        / "reports"
        / "ratewall_release_9_0_structural_boundary_appendix.md"
    ).read_text(encoding="utf-8")
    assert "RateWall Release 9.0 External Proxy Review Packet" in (
        tmp_path
        / "outputs"
        / "reports"
        / "ratewall_release_9_0_external_proxy_review_packet.md"
    ).read_text(encoding="utf-8")
    assert (
        tmp_path
        / "outputs"
        / "figures"
        / "ratewall_release_9_0_structural_boundary.svg"
    ).exists()

    build_databook(snapshot_bundle=snapshot, output_dir=tmp_path / "outputs")
    release_artifacts = build_release_package(
        snapshot_bundle=snapshot,
        output_dir=tmp_path / "outputs",
    )
    assert release_artifacts.final_paper_quarto.exists()
    assert release_artifacts.slide_deck_quarto.exists()
    assert release_artifacts.public_readme.exists()
    assert release_artifacts.release_index.exists()
    assert release_artifacts.reproduction_commands.exists()
    assert release_artifacts.public_release_checklist.exists()
    assert release_artifacts.figure_plate.exists()
    assert release_artifacts.table_plate.exists()
    assert release_artifacts.archival_manifest.exists()
    assert release_artifacts.source_archive.exists()
    assert (
        release_artifacts.source_archive.name
        == "ratewall_release_23_0_source_archive.zip"
    )
    assert release_artifacts.citation_metadata.exists()
    assert release_artifacts.package_smoke.exists()
    assert release_artifacts.publication_claim_decision_memo.exists()
    assert release_artifacts.release_16_bounded_publication_closeout_memo.exists()
    assert release_artifacts.release_16_reviewer_blocker_text.exists()
    assert release_artifacts.release_17_external_review_packet.exists()
    assert release_artifacts.release_17_publication_polish_memo.exists()
    assert release_artifacts.release_18_publication_freeze_memo.exists()
    assert release_artifacts.release_19_post_audit_methodology_memo.exists()
    assert release_artifacts.release_20_submission_readiness_memo.exists()
    assert release_artifacts.release_21_backend_closeout_memo.exists()
    assert release_artifacts.release_22_backend_fix_memo.exists()
    assert release_artifacts.release_23_backend_fix_memo.exists()
    assert release_artifacts.release_23_reproducibility_manifest.exists()
    assert release_artifacts.release_23_archive_verification_audit.exists()
    archive_audit = list(
        csv.DictReader(
            release_artifacts.release_23_archive_verification_audit.open(
                encoding="utf-8"
            )
        )
    )
    assert {row["audit_status"] for row in archive_audit} == {"pass"}
    release_23_manifest = json.loads(
        release_artifacts.release_23_reproducibility_manifest.read_text(
            encoding="utf-8"
        )
    )
    assert release_23_manifest["file_count"] > 0
    assert all(
        not str(record["source_path"]).startswith("/")
        for record in release_23_manifest["files"]
    )
    with zipfile.ZipFile(release_artifacts.source_archive) as archive:
        archive_names = set(archive.namelist())
        assert not {
            archive_name
            for archive_name in archive_names
            if archive_name.startswith("outputs/figures/")
            and archive_name.endswith(".svg")
        }
        archive_text = {
            archive_name: archive.read(archive_name).decode("utf-8")
            for archive_name in (
                "outputs/tables/ratewall_threshold_calibrated_simulation.csv",
                "outputs/reports/ratewall_final_paper.md",
                "outputs/reports/ratewall_table_plate.md",
                "outputs/reports/ratewall_figure_plate.md",
                "outputs/reports/ratewall_public_deck.qmd",
                "outputs/reports/ratewall_theory_of_change.md",
                "outputs/reports/ratewall_dynamic_assumption_mode_equations.md",
                "outputs/reports/ratewall_paper_support_backend_appendix.md",
                "outputs/reports/ratewall_financialization_interpretation_memo.md",
            )
        }
    assert {
        "data/raw/ratewall_snapshot.json",
        "data/raw/romer_romer/romer_romer_monthly_shocks.csv",
        "data/raw/romer_romer/PROVENANCE.json",
        "outputs/tables/treasury_maturity_ladder.csv",
        "outputs/tables/treasury_mspd_reconciliation.csv",
        "outputs/tables/ratewall_denominator_aligned_response_panel_scaffold.csv",
        "outputs/tables/ratewall_denominator_event_outcome_cell_diagnostic.csv",
        "outputs/tables/ratewall_denominator_event_outcome_panel_value_diagnostic.csv",
        "outputs/tables/ratewall_denominator_event_level_response_panel.csv",
        "outputs/tables/ratewall_denominator_uncertainty_pass_fail_review.csv",
        "outputs/tables/ratewall_denominator_panel_design_test_diagnostic.csv",
        "outputs/tables/ratewall_denominator_pretrend_placebo_diagnostic.csv",
        "outputs/tables/ratewall_denominator_shock_relevance_diagnostic.csv",
        "outputs/tables/ratewall_denominator_sign_consistency_diagnostic.csv",
        "outputs/tables/ratewall_denominator_horizon_sensitivity_diagnostic.csv",
        "outputs/tables/ratewall_denominator_outlier_window_robustness_diagnostic.csv",
        "outputs/tables/ratewall_denominator_design_readiness_decision.csv",
        "outputs/tables/ratewall_denominator_formal_design_test_result_scaffold.csv",
        "outputs/tables/ratewall_denominator_formal_design_test_result.csv",
        "outputs/tables/ratewall_denominator_response_estimate_diagnostic.csv",
        "outputs/tables/ratewall_denominator_cross_source_design_validation.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_source_design_requirement.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_priority_queue.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_tier1_workplan.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv",
        "outputs/tables/ratewall_conventional_drag_evidence_tranche.csv",
        "outputs/tables/ratewall_conventional_drag_demand_conversion_admission.csv",
        "outputs/tables/ratewall_tdsp_current_demand_source_review.csv",
        "outputs/tables/ratewall_tdsp_current_demand_unit_conversion.csv",
        "outputs/tables/ratewall_tdsp_current_demand_diagnostic_mapping.csv",
        "outputs/tables/ratewall_tdsp_policy_path_normalization_blocker.csv",
        "outputs/tables/ratewall_tdsp_current_demand_admission_audit.csv",
        "outputs/tables/ratewall_sibling_evidence_bridge.csv",
        "outputs/tables/ratewall_sibling_evidence_upgrade_queue.csv",
        "outputs/tables/ratewall_higher_rate_channel_registry.csv",
        "outputs/tables/ratewall_corporate_net_interest_cashflow_bridge.csv",
        "outputs/tables/ratewall_working_capital_cost_channel_diagnostic.csv",
        "outputs/tables/ratewall_term_structure_pricing_carry_diagnostic.csv",
        "outputs/tables/ratewall_interest_channel_completion_matrix.csv",
        "outputs/tables/ratewall_dynamic_scenario_paths.csv",
        "outputs/tables/ratewall_dynamic_scenario_path_consistency_diagnostic.csv",
        "outputs/tables/ratewall_dynamic_offset_ratio_path.csv",
        "outputs/tables/ratewall_scenario_crossing_diagnostic.csv",
        "outputs/tables/ratewall_dynamic_sensitivity_frontier.csv",
        "outputs/tables/ratewall_dynamic_scenario_family_registry.csv",
        "outputs/tables/ratewall_dynamic_uncertainty_envelope.csv",
        "outputs/tables/ratewall_dynamic_crossing_robustness.csv",
        "outputs/reports/ratewall_dynamic_assumption_mode_equations.md",
        "configs/ratewall_dynamic_scenario_paths.yml",
        "outputs/tables/ratewall_release_22_core_output_source_gate.csv",
        "outputs/tables/ratewall_release_23_source_status_propagation_audit.csv",
        "outputs/tables/ratewall_release_23_reproducibility_hash_manifest.json",
        "outputs/reports/ratewall_theory_of_change.md",
        "outputs/reports/ratewall_backend_completion_readiness_report.md",
        "outputs/reports/ratewall_assumption_mode_v1_stage_completion_report.md",
        "outputs/reports/ratewall_assumption_mode_post_closure_boundary_memo.md",
        "outputs/reports/ratewall_paper_support_backend_appendix.md",
        "outputs/reports/ratewall_financialization_interpretation_memo.md",
        "outputs/tables/ratewall_paper_channel_map.csv",
        "outputs/tables/ratewall_paper_canonical_scenario_results.csv",
        "outputs/tables/ratewall_paper_tdc_dynamic_contribution.csv",
        "outputs/tables/ratewall_paper_parameter_justification.csv",
        "outputs/tables/ratewall_paper_sensitivity_summary.csv",
        "outputs/tables/ratewall_paper_disabled_claims_appendix.csv",
        "outputs/tables/ratewall_paper_financialization_interpretation.csv",
        "outputs/tables/ratewall_paper_support_invariant_audit.csv",
        "outputs/tables/ratewall_backend_accounting_identity_audit.csv",
        "outputs/tables/ratewall_paper_scenario_accounting_bridge.csv",
        "outputs/tables/ratewall_paper_dynamic_scenario_summary.csv",
        "scripts/materialize_release_inputs.py",
    } <= archive_names
    archived_dynamic_report = archive_text[
        "outputs/reports/ratewall_dynamic_assumption_mode_equations.md"
    ]
    current_dynamic_report = (
        tmp_path
        / "outputs"
        / "reports"
        / "ratewall_dynamic_assumption_mode_equations.md"
    ).read_text(encoding="utf-8")
    assert archived_dynamic_report == current_dynamic_report
    archived_paper_support = archive_text[
        "outputs/reports/ratewall_paper_support_backend_appendix.md"
    ]
    assert "ratewall_paper_channel_map.csv" in archived_paper_support
    assert "ratewall_paper_financialization_interpretation.csv" in archived_paper_support
    archived_financialization_memo = archive_text[
        "outputs/reports/ratewall_financialization_interpretation_memo.md"
    ]
    assert "cannot be collapsed into a single financialization scalar" in (
        archived_financialization_memo
    )
    assert "outputs/tables/ratewall_release_archive_manifest.json" not in archive_names
    assert (
        "outputs/tables/ratewall_release_23_archive_hash_verification_audit.csv"
        not in archive_names
    )
    assert "outputs/reports/ratewall_final_paper.pdf" not in archive_names
    assert "outputs/reports/ratewall_public_deck.pptx" not in archive_names
    assert "outputs/tables/ratewall_release_archive_manifest.json" not in (
        release_artifacts.public_readme.read_text(encoding="utf-8")
    )
    assert "outputs/tables/ratewall_release_archive_manifest.json" not in json.dumps(
        json.loads(release_artifacts.release_manifest.read_text(encoding="utf-8"))
    )
    for text in archive_text.values():
        assert "source_backed_range_label" not in text
        assert "Source-backed calibration-range" not in text
        assert "source-backed paper-support package" not in text
        assert "source-backed tables" not in text
        assert "source-backed release package" not in text
    claim_rows = list(
        csv.DictReader(release_artifacts.claim_audit.open(encoding="utf-8"))
    )
    assert {row["audit_status"] for row in claim_rows} == {"pass"}
    assert any(
        row["boundary"] == "release_13_0_calibrated_threshold_gate"
        for row in claim_rows
    )
    assert any(
        row["boundary"] == "release_14_0_historical_threshold_validation_gate"
        for row in claim_rows
    )
    assert any(
        row["boundary"] == "release_15_0_publication_claim_decision_gate"
        for row in claim_rows
    )
    assert any(
        row["boundary"] == "release_16_0_bounded_publication_closeout_gate"
        for row in claim_rows
    )
    assert any(
        row["boundary"] == "release_17_0_external_review_publication_polish_gate"
        for row in claim_rows
    )
    assert any(
        row["boundary"] == "release_18_0_live_refresh_publication_freeze_gate"
        for row in claim_rows
    )
    assert any(
        row["boundary"] == "release_19_0_post_audit_methodology_gate"
        for row in claim_rows
    )
    assert any(
        row["boundary"] == "release_20_0_submission_benchmark_gate"
        for row in claim_rows
    )
    assert any(
        row["boundary"] == "release_21_0_backend_closeout_gate" for row in claim_rows
    )
    assert "does not claim that higher rates always raise inflation" in (
        release_artifacts.final_paper.read_text(encoding="utf-8")
    )
    assert "bounded event-study estimates" in (
        release_artifacts.slide_deck.read_text(encoding="utf-8")
    )
    paper_qmd = release_artifacts.final_paper_quarto.read_text(encoding="utf-8")
    assert "format:" in paper_qmd
    assert "pdf:" in paper_qmd
    deck_qmd = release_artifacts.slide_deck_quarto.read_text(encoding="utf-8")
    assert "pptx:" in deck_qmd
    assert "Raw policy-rate changes remain rejected" in deck_qmd
    assert "Release 2.0 Causal Gate" in paper_qmd
    assert "Release 3.0 Dynamic Causal Gate" in paper_qmd
    assert "Release 4.0 Final Submission Gate" in paper_qmd
    assert "Release 5.0 Controlled Dynamic LP Frontier" in paper_qmd
    assert "Release 6.0 Proxy-SVAR/System Identification Frontier" in paper_qmd
    assert "Release 7.0 System-Identification Frontier" in paper_qmd
    assert "Release 8.0 System-Identification Non-Promotion Proof" in paper_qmd
    assert "Release 9.0 External-Proxy Publication Boundary" in paper_qmd
    assert "Release 10.0 TDC Deposit-Channel Layer" in paper_qmd
    assert "Release 11.0 Historical TDC and Deposit-Pricing Layer" in paper_qmd
    assert "Release 12.0 Threshold And Financialization-Pressure Extension" in paper_qmd
    assert "Release 13.0 Calibrated Threshold Layer" in paper_qmd
    assert "Release 14.0 Historical Threshold Validation" in paper_qmd
    assert "Release 15.0 Publication-Claim Decision" in paper_qmd
    assert "Release 16.0 Bounded-Publication Closeout" in paper_qmd
    assert "Release 17.0 External Review And Publication Polish" in paper_qmd
    assert "Release 18.0 Live Refresh And Publication Freeze" in paper_qmd
    assert "Release 2.0 support diagnostic rows" in deck_qmd
    assert "Release 3.0: dynamic causal frontier" in deck_qmd
    assert "Release 4.0: final submission frontier" in deck_qmd
    assert "Release 5.0: controlled dynamic LP frontier" in deck_qmd
    assert "Release 6.0: proxy-SVAR/system frontier" in deck_qmd
    assert "Release 7.0: system-identification frontier" in deck_qmd
    assert "Release 8.0: final system non-promotion proof" in deck_qmd
    assert "Release 9.0: expanded external-proxy boundary" in deck_qmd
    assert "Release 10.0: TDC deposit-channel accounting" in deck_qmd
    assert "Release 11.0: historical TDC and deposit-pricing context" in deck_qmd
    assert (
        "Release 12.0: conditional threshold and legacy retention context" in deck_qmd
    )
    assert "Release 13.0: calibrated threshold context" in deck_qmd
    assert "Release 14.0: historical threshold validation" in deck_qmd
    assert "Release 15.0: publication-claim decision" in deck_qmd
    assert "Release 16.0: bounded publication closeout" in deck_qmd
    assert "Release 17.0: external review and polish" in deck_qmd
    assert "Release 18.0: live refresh and publication freeze" in deck_qmd
    readme_text = release_artifacts.public_readme.read_text(encoding="utf-8")
    assert "Raw policy-rate changes are rejected" in readme_text
    assert "ratewall_dynamic_causal_final_blocker.csv" in readme_text
    assert "ratewall_release_4_0_dynamic_causal_final_blocker.csv" in readme_text
    assert "ratewall_release_5_0_identification_decision.csv" in readme_text
    assert "ratewall_release_6_0_identification_decision.csv" in readme_text
    assert "ratewall_release_7_0_identification_decision.csv" in readme_text
    assert "ratewall_release_8_0_identification_decision.csv" in readme_text
    assert "ratewall_release_9_0_structural_identification_decision.csv" in readme_text
    assert "ratewall_tdc_deposit_channel_ledger.csv" in readme_text
    assert "ratewall_tdc_historical_panel.csv" in readme_text
    assert "ratewall_deposit_pricing_pass_through_context.csv" in readme_text
    assert "ratewall_tdc_historical_reconciliation.csv" in readme_text
    assert "ratewall_threshold_simulation.csv" in readme_text
    assert "ratewall_financialization_pressure.csv" in readme_text
    assert "ratewall_safe_asset_retention_context.csv" in readme_text
    assert "ratewall_threshold_calibration_ranges.csv" in readme_text
    assert "ratewall_threshold_calibrated_simulation.csv" in readme_text
    assert "ratewall_du_ru_tga_calibration_bridge.csv" in readme_text
    assert "ratewall_financialization_pressure_evidence_appendix.csv" in readme_text
    assert "ratewall_contractionary_benchmark_calibration.csv" in readme_text
    assert "ratewall_threshold_uncertainty_bands.csv" in readme_text
    assert "ratewall_historical_threshold_validation.csv" in readme_text
    assert "ratewall_policy_boundary_synthesis.csv" in readme_text
    assert "ratewall_blocker_resolution_ledger.csv" in readme_text
    assert "ratewall_publication_claim_decision.csv" in readme_text
    assert "ratewall_final_blocker_ledger.csv" in readme_text
    assert "ratewall_release_16_source_resolution_closeout.csv" in readme_text
    assert "ratewall_release_16_no_further_promotion_ledger.csv" in readme_text
    assert "ratewall_release_17_external_review_audit.csv" in readme_text
    assert "ratewall_release_17_publication_polish_qa.csv" in readme_text
    assert "ratewall_release_17_blocker_reopen_decision.csv" in readme_text
    assert "ratewall_release_18_live_refresh_robustness_audit.csv" in readme_text
    assert "ratewall_publication_claim_decision_memo.md" in readme_text
    assert "ratewall_release_16_bounded_publication_closeout_memo.md" in readme_text
    assert "ratewall_release_16_reviewer_blocker_text.md" in readme_text
    assert "ratewall_release_17_external_review_packet.md" in readme_text
    assert "ratewall_release_17_publication_polish_memo.md" in readme_text
    assert "ratewall_release_18_publication_freeze_memo.md" in readme_text
    assert "ratewall_release_19_post_audit_methodology_memo.md" in readme_text
    assert "ratewall_release_20_activity_demand_benchmark.csv" in readme_text
    assert "ratewall_release_20_state_dependent_lp_diagnostics.csv" in readme_text
    assert "ratewall_release_20_benchmark_submission_decision.csv" in readme_text
    assert "ratewall_release_20_submission_readiness_memo.md" in readme_text
    assert "ratewall_release_21_live_refresh_endpoint_audit.csv" in readme_text
    assert "ratewall_release_21_final_benchmark_gate.csv" in readme_text
    assert "ratewall_release_21_backend_invariant_audit.csv" in readme_text
    assert "ratewall_release_21_backend_closeout_memo.md" in readme_text
    assert "ratewall_reproduction_commands.md" in readme_text
    assert "ratewall_theory_of_change.md" in readme_text
    assert "ratewall_assumption_sets.csv" in readme_text
    assert "ratewall_condition_frontier.csv" in readme_text
    assert "ratewall_public_impulse_factorization.csv" in readme_text
    assert "ratewall_public_liability_repricing_ladder.csv" in readme_text
    assert "ratewall_public_liability_repricing_evidence_bridge.csv" in readme_text
    assert "ratewall_public_liability_repricing_reconciliation_gap.csv" in readme_text
    assert "ratewall_mspd_table3_bucket_repricing_gate.csv" in readme_text
    assert "ratewall_interest_recipient_leakage_bridge.csv" in readme_text
    assert "ratewall_interest_recipient_leakage_evidence_gap.csv" in readme_text
    assert "ratewall_treasury_recipient_leakage_source_gate.csv" in readme_text
    assert "ratewall_public_finance_timing_path.csv" in readme_text
    assert "ratewall_public_finance_timing_evidence_gap.csv" in readme_text
    assert "ratewall_public_finance_timing_design_test_scaffold.csv" in readme_text
    assert "ratewall_safe_yield_offset_drag_pairing_gap.csv" in readme_text
    assert "ratewall_bnpl_zero_interest_float_evidence_gap.csv" in readme_text
    assert "ratewall_financialized_balance_sheet_evidence_gap.csv" in readme_text
    assert "ratewall_firm_cash_debt_maturity_evidence_gap.csv" in readme_text
    assert "ratewall_conventional_drag_channel_evidence_gap.csv" in readme_text
    assert "ratewall_conventional_drag_source_design_gate.csv" in readme_text
    assert "ratewall_denominator_response_design_scaffold.csv" in readme_text
    assert "ratewall_denominator_response_design_test_scaffold.csv" in readme_text
    assert "ratewall_denominator_response_gate_attempt.csv" in readme_text
    assert "ratewall_denominator_aligned_response_panel_scaffold.csv" in readme_text
    assert "ratewall_denominator_event_outcome_cell_diagnostic.csv" in readme_text
    assert (
        "ratewall_denominator_event_outcome_panel_value_diagnostic.csv" in readme_text
    )
    assert "ratewall_denominator_event_level_response_panel.csv" in readme_text
    assert "ratewall_denominator_uncertainty_pass_fail_review.csv" in readme_text
    assert "ratewall_denominator_panel_design_test_diagnostic.csv" in readme_text
    assert "ratewall_denominator_pretrend_placebo_diagnostic.csv" in readme_text
    assert "ratewall_denominator_shock_relevance_diagnostic.csv" in readme_text
    assert "ratewall_denominator_sign_consistency_diagnostic.csv" in readme_text
    assert "ratewall_denominator_horizon_sensitivity_diagnostic.csv" in readme_text
    assert (
        "ratewall_denominator_outlier_window_robustness_diagnostic.csv" in readme_text
    )
    assert "ratewall_denominator_design_readiness_decision.csv" in readme_text
    assert "ratewall_denominator_formal_design_test_result_scaffold.csv" in readme_text
    assert "ratewall_denominator_formal_design_test_result.csv" in readme_text
    assert "ratewall_denominator_response_estimate_diagnostic.csv" in readme_text
    assert "ratewall_denominator_cross_source_design_validation.csv" in readme_text
    assert (
        "ratewall_denominator_evidence_upgrade_source_design_requirement.csv"
        in readme_text
    )
    assert "ratewall_denominator_evidence_upgrade_priority_queue.csv" in readme_text
    assert "ratewall_denominator_evidence_upgrade_tier1_workplan.csv" in readme_text
    assert (
        "ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv"
        in readme_text
    )
    assert (
        "ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv"
        in readme_text
    )
    assert "ratewall_conventional_drag_evidence_tranche.csv" in readme_text
    assert "ratewall_conventional_drag_demand_conversion_admission.csv" in readme_text
    assert "ratewall_tdsp_current_demand_source_review.csv" in readme_text
    assert "ratewall_tdsp_current_demand_unit_conversion.csv" in readme_text
    assert "ratewall_tdsp_current_demand_diagnostic_mapping.csv" in readme_text
    assert "ratewall_tdsp_policy_path_normalization_blocker.csv" in readme_text
    assert "ratewall_tdsp_current_demand_admission_audit.csv" in readme_text
    assert "ratewall_interest_channel_horizon_timing_matrix.csv" in readme_text
    assert "ratewall_interest_channel_promotion_gate.csv" in readme_text
    assert "ratewall_interest_channel_evidence_upgrade_queue.csv" in readme_text
    assert "ratewall_high_priority_interest_channel_source_bridge.csv" in readme_text
    assert "ratewall_source_gate_prior_narrowing_decision.csv" in readme_text
    assert "ratewall_source_gate_exhaustion_closure.csv" in readme_text
    assert "ratewall_restricted_data_gate_spec.csv" in readme_text
    assert "ratewall_assumption_mode_post_closure_boundary_map.csv" in readme_text
    assert "ratewall_sibling_evidence_bridge.csv" in readme_text
    assert "ratewall_sibling_evidence_upgrade_queue.csv" in readme_text
    assert "ratewall_higher_rate_channel_registry.csv" in readme_text
    assert "ratewall_corporate_net_interest_cashflow_bridge.csv" in readme_text
    assert "ratewall_working_capital_cost_channel_diagnostic.csv" in readme_text
    assert "ratewall_term_structure_pricing_carry_diagnostic.csv" in readme_text
    assert "ratewall_interest_channel_module_registry.csv" in readme_text
    assert "ratewall_interest_channel_completion_matrix.csv" in readme_text
    assert "ratewall_flow_stage_decomposition.csv" in readme_text
    assert "ratewall_gross_interest_subchannels.csv" in readme_text
    assert "ratewall_public_finance_adjustment.csv" in readme_text
    assert "ratewall_net_countervailing_channels.csv" in readme_text
    assert "ratewall_wall_hit_scenarios.csv" in readme_text
    assert "ratewall_threshold_solver.csv" in readme_text
    assert "ratewall_parameter_frontier.csv" in readme_text
    assert "ratewall_minimum_conditions_to_hit_wall.csv" in readme_text
    assert "ratewall_hit_fragility_frontier.csv" in readme_text
    assert "ratewall_frontier_driver_ranking.csv" in readme_text
    assert "ratewall_assumption_mode_driver_dominance_matrix.csv" in readme_text
    assert "ratewall_assumption_mode_pairwise_sensitivity_matrix.csv" in readme_text
    assert "ratewall_backend_invariant_guardrail_audit.csv" in readme_text
    assert "ratewall_backend_completion_verdict.csv" in readme_text
    assert "ratewall_paper_channel_map.csv" in readme_text
    assert "ratewall_paper_canonical_scenario_results.csv" in readme_text
    assert "ratewall_paper_tdc_dynamic_contribution.csv" in readme_text
    assert "ratewall_paper_parameter_justification.csv" in readme_text
    assert "ratewall_paper_sensitivity_summary.csv" in readme_text
    assert "ratewall_paper_disabled_claims_appendix.csv" in readme_text
    assert "ratewall_paper_financialization_interpretation.csv" in readme_text
    assert "ratewall_paper_support_invariant_audit.csv" in readme_text
    assert "ratewall_backend_accounting_identity_audit.csv" in readme_text
    assert "ratewall_paper_scenario_accounting_bridge.csv" in readme_text
    assert "ratewall_paper_dynamic_scenario_summary.csv" in readme_text
    assert "ratewall_conventional_drag_decomposition.csv" in readme_text
    assert "ratewall_split_denominator_comparison.csv" in readme_text
    assert "ratewall_denominator_sensitivity.csv" in readme_text
    assert "ratewall_split_denominator_uncertainty.csv" in readme_text
    assert "ratewall_split_denominator_regime_stability.csv" in readme_text
    assert "ratewall_chapter_readiness_self_audit.csv" in readme_text
    assert "ratewall_financialized_balance_sheet_channel.csv" in readme_text
    financialization_release_artifacts = [
        "ratewall_financialization_proxy_registry.csv",
        "ratewall_household_safe_asset_capture_proxy.csv",
        "ratewall_household_safe_asset_exposure_panel.csv",
        "ratewall_household_safe_asset_access_context.csv",
        "ratewall_retail_safe_yield_access_substitution_context.csv",
        "ratewall_retail_deposit_beta_gap_context.csv",
        "ratewall_retail_pass_through_dispersion_panel.csv",
        "ratewall_deposit_competition_conditioner.csv",
        "ratewall_deposit_mmf_substitution_surface.csv",
        "ratewall_personal_net_interest_position_context.csv",
        "ratewall_firm_liquid_asset_public_context.csv",
        "ratewall_firm_liquid_asset_cushion_panel.csv",
        "ratewall_firm_net_interest_cushion_context.csv",
        "ratewall_firm_rollover_pressure_panel.csv",
        "ratewall_firm_short_rate_exposure_proxy.csv",
        "ratewall_household_borrower_fragility_context.csv",
        "ratewall_bank_loan_repricing_context.csv",
        "ratewall_cre_refinancing_public_context.csv",
        "ratewall_private_credit_bdc_context.csv",
        "ratewall_safe_yield_paired_proxy_surface.csv",
        "ratewall_financialization_proxy_source_gate.csv",
        "ratewall_financialization_source_gate.csv",
        "ratewall_financialization_restricted_protocols.csv",
        "ratewall_financialization_double_count_audit.csv",
        "ratewall_financialization_overlap_audit.csv",
        "ratewall_financialization_artifact_traceability_matrix.csv",
    ]
    for artifact_name in financialization_release_artifacts:
        assert artifact_name in readme_text
    backend_expansion_release_artifacts = [
        "ratewall_backend_expansion_context_registry.csv",
        "ratewall_assumption_mode_channel_promotion_decision.csv",
        "ratewall_assumption_mode_promoted_channel_contributions.csv",
        "ratewall_household_within_distribution_safe_asset_capture_context.csv",
        "ratewall_deposit_pass_through_dispersion_conditioner.csv",
        "ratewall_brokerage_tbill_mmf_access_context.csv",
        "ratewall_firm_interest_income_expense_balance_context.csv",
        "ratewall_firm_debt_maturity_wall_context.csv",
        "ratewall_bdc_private_credit_stress_marker_context.csv",
        "ratewall_cre_maturity_refi_pressure_context.csv",
        "ratewall_bnpl_zero_interest_float_context.csv",
        "ratewall_safe_asset_substitution_pairing_audit.csv",
        "ratewall_financialization_expansion_avoidance_audit.csv",
        "ratewall_bank_nim_credit_supply_context.csv",
        "ratewall_tax_timing_interest_income_context.csv",
        "ratewall_foreign_holder_interest_leakage_context.csv",
        "ratewall_public_finance_remittance_timing_stress_grid.csv",
        "ratewall_insurance_pension_asset_liability_context.csv",
        "ratewall_housing_lockin_cashflow_context.csv",
        "ratewall_dealer_inventory_carry_context.csv",
    ]
    for artifact_name in backend_expansion_release_artifacts:
        assert artifact_name in readme_text
    assert "ratewall_equity_transmission_channel_map.csv" in readme_text
    assert "ratewall_equity_exposure_matrix.csv" in readme_text
    assert "ratewall_equity_sensitivity_diagnostic.csv" in readme_text
    assert "ratewall_equity_claim_status.csv" in readme_text
    assert "ratewall_equity_evidence_workplan.csv" in readme_text
    assert "ratewall_parameter_packs.csv" in readme_text
    assert "ratewall_frontier_summary.csv" in readme_text
    assert "ratewall_regime_map.csv" in readme_text
    assert "ratewall_assumption_mode_interpretation.csv" in readme_text
    assert "ratewall_prior_stack_diagnostic.csv" in readme_text
    assert "ratewall_scenario_ladder.csv" in readme_text
    assert "ratewall_model_adequacy_matrix.csv" in readme_text
    assert "ratewall_assumption_offset_ratio.svg" not in readme_text
    assert "configs/ratewall_assumption_sets.yml" in readme_text
    assert "ratewall_assumption_engine_memo.md" in readme_text
    assert "ratewall_assumption_mode_theory_chapter.md" in readme_text
    assert "ratewall_assumption_mode_model_audit_packet.md" in readme_text
    assert "ratewall_assumption_mode_critique_response.md" in readme_text
    assert "ratewall_professor_model_review_prompt.md" in readme_text
    assert "ratewall_interest_channel_expansion_plan.md" in readme_text
    assert "ratewall_backend_completion_readiness_report.md" in readme_text
    assert "ratewall_assumption_mode_v1_stage_completion_report.md" in readme_text
    assert "ratewall_assumption_mode_post_closure_boundary_memo.md" in readme_text
    assert "ratewall_paper_support_backend_appendix.md" in readme_text
    assert "ratewall_financialization_proxy_backend_audit.md" in readme_text
    assert "ratewall_financialization_interpretation_memo.md" in readme_text
    assert "ratewall_equity_transmission_attenuation_memo.md" in readme_text
    assert "ratewall_equity_evidence_workplan.md" in readme_text
    assert "ratewall_split_denominator_evidence_workplan.md" in readme_text
    reproduction_text = release_artifacts.reproduction_commands.read_text(
        encoding="utf-8"
    )
    assert "PYTHONPYCACHEPREFIX=/tmp/ratewall-pycache" in reproduction_text
    assert "quarto render ratewall_final_paper.qmd" not in reproduction_text
    assert "quarto render ratewall_public_deck.qmd" not in reproduction_text
    assert "uv build --out-dir /tmp/ratewall-dist" in reproduction_text
    assert "import ratewall; import ratewall.cli" in reproduction_text
    assert "RateWall Figure Plate" in release_artifacts.figure_plate.read_text(
        encoding="utf-8"
    )
    assert "RateWall Table Plate" in release_artifacts.table_plate.read_text(
        encoding="utf-8"
    )
    assert "ratewall_causal_identification_audit.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_dynamic_causal_final_blocker.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_tdc_ru_financing_deposit_impulse.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_deposit_pricing_pass_through_context.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_threshold_simulation.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_threshold_calibration_ranges.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_threshold_calibrated_simulation.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_du_ru_tga_calibration_bridge.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_financialization_pressure_evidence_appendix.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_paper_financialization_interpretation.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    table_plate_text = release_artifacts.table_plate.read_text(encoding="utf-8")
    for artifact_name in (
        "ratewall_financialization_proxy_registry.csv",
        "ratewall_financialization_proxy_source_gate.csv",
        "ratewall_financialization_source_gate.csv",
        "ratewall_financialization_restricted_protocols.csv",
        "ratewall_financialization_double_count_audit.csv",
        "ratewall_financialization_overlap_audit.csv",
        "ratewall_financialization_artifact_traceability_matrix.csv",
    ):
        assert artifact_name in table_plate_text
    for artifact_name in backend_expansion_release_artifacts:
        assert artifact_name in table_plate_text
    assert "ratewall_safe_asset_retention_context.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_safe_yield_offset_drag_pairing_gap.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_interest_channel_promotion_gate.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_interest_channel_evidence_upgrade_queue.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_event_outcome_panel_value_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_event_level_response_panel.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_uncertainty_pass_fail_review.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_panel_design_test_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_pretrend_placebo_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_shock_relevance_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_sign_consistency_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_horizon_sensitivity_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_outlier_window_robustness_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_design_readiness_decision.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_formal_design_test_result_scaffold.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_formal_design_test_result.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_response_estimate_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_cross_source_design_validation.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_evidence_upgrade_source_design_requirement.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_evidence_upgrade_priority_queue.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_evidence_upgrade_tier1_workplan.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_conventional_drag_evidence_tranche.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_conventional_drag_demand_conversion_admission.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_tdsp_current_demand_source_review.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_tdsp_current_demand_unit_conversion.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_tdsp_current_demand_diagnostic_mapping.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_tdsp_policy_path_normalization_blocker.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_tdsp_current_demand_admission_audit.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_high_priority_interest_channel_source_bridge.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_source_gate_prior_narrowing_decision.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_source_gate_exhaustion_closure.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_restricted_data_gate_spec.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_assumption_mode_post_closure_boundary_map.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_sibling_evidence_bridge.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_sibling_evidence_upgrade_queue.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_mspd_table3_bucket_repricing_gate.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_treasury_recipient_leakage_source_gate.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_conventional_drag_source_design_gate.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_response_design_scaffold.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_response_design_test_scaffold.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_response_gate_attempt.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_aligned_response_panel_scaffold.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_denominator_event_outcome_cell_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_interest_channel_completion_matrix.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_higher_rate_channel_registry.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_corporate_net_interest_cashflow_bridge.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_working_capital_cost_channel_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_term_structure_pricing_carry_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_dynamic_scenario_paths.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_scenario_crossing_diagnostic.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_dynamic_sensitivity_frontier.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_dynamic_uncertainty_envelope.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_dynamic_crossing_robustness.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_public_finance_timing_design_test_scaffold.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_buyer_case_sign_matrix.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_contractionary_benchmark_calibration.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_threshold_uncertainty_bands.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_historical_threshold_validation.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_policy_boundary_synthesis.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_blocker_resolution_ledger.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_publication_claim_decision.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_final_blocker_ledger.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_release_16_source_resolution_closeout.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_release_16_no_further_promotion_ledger.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_release_17_external_review_audit.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_release_17_publication_polish_qa.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_release_17_blocker_reopen_decision.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    assert "ratewall_release_18_live_refresh_robustness_audit.csv" in (
        release_artifacts.table_plate.read_text(encoding="utf-8")
    )
    archive_manifest = json.loads(
        release_artifacts.archival_manifest.read_text(encoding="utf-8")
    )
    assert archive_manifest["schema"] == "ratewall.release_archive_manifest.v1"
    assert archive_manifest["file_count"] >= 10
    assert archive_manifest["source_archive"]["sha256"]
    with zipfile.ZipFile(release_artifacts.source_archive) as archive:
        assert "data/raw/ratewall_snapshot.json" in archive.namelist()
    assert (
        archive_manifest["claim_boundary"][
            "archive_is_release_packaging_not_new_evidence"
        ]
        is True
    )
    assert archive_manifest["claim_boundary"]["dynamic_lp_claim_enabled"] is False
    assert archive_manifest["claim_boundary"]["proxy_svar_claim_enabled"] is False
    assert (
        archive_manifest["claim_boundary"]["system_identification_claim_enabled"]
        is False
    )
    assert (
        archive_manifest["claim_boundary"]["valuation_incidence_claim_enabled"] is False
    )
    assert (
        archive_manifest["claim_boundary"]["financialization_causal_claim_enabled"]
        is False
    )
    assert (
        archive_manifest["claim_boundary"]["threshold_policy_failure_claim_enabled"]
        is False
    )
    assert (
        archive_manifest["claim_boundary"]["dynamic_identification_promotion_enabled"]
        is False
    )
    assert (
        archive_manifest["claim_boundary"]["expanded_external_proxy_frontier_enabled"]
        is True
    )
    assert (
        archive_manifest["claim_boundary"]["defensible_structural_appendix_enabled"]
        is False
    )
    assert "cff-version: 1.2.0" in release_artifacts.citation_metadata.read_text(
        encoding="utf-8"
    )
    assert "version: 23.0.0" in release_artifacts.citation_metadata.read_text(
        encoding="utf-8"
    )
    assert "RateWall Package Smoke Checks" in release_artifacts.package_smoke.read_text(
        encoding="utf-8"
    )
    assert "Bounded-Publication Closeout Memo" in (
        release_artifacts.release_16_bounded_publication_closeout_memo.read_text(
            encoding="utf-8"
        )
    )
    assert "Reviewer Blocker Text" in (
        release_artifacts.release_16_reviewer_blocker_text.read_text(encoding="utf-8")
    )
    assert "External Review Packet" in (
        release_artifacts.release_17_external_review_packet.read_text(encoding="utf-8")
    )
    assert "Publication Polish Memo" in (
        release_artifacts.release_17_publication_polish_memo.read_text(encoding="utf-8")
    )
    assert "Publication Freeze Memo" in (
        release_artifacts.release_18_publication_freeze_memo.read_text(encoding="utf-8")
    )
    assert "Post-Audit Methodology Memo" in (
        release_artifacts.release_19_post_audit_methodology_memo.read_text(
            encoding="utf-8"
        )
    )
    assert "Submission-Readiness Memo" in (
        release_artifacts.release_20_submission_readiness_memo.read_text(
            encoding="utf-8"
        )
    )
    assert "Backend Closeout Memo" in (
        release_artifacts.release_21_backend_closeout_memo.read_text(encoding="utf-8")
    )
    manifest = json.loads(
        release_artifacts.release_manifest.read_text(encoding="utf-8")
    )
    assert manifest["hard_boundaries"]["raw_rate_change_shocks"] is False
    assert manifest["hard_boundaries"]["pricing_output_enabled"] is False
    assert manifest["hard_boundaries"]["welfare_incidence_enabled"] is False
    assert manifest["hard_boundaries"]["causal_lp_proxy_svar_claim_enabled"] is False
    assert manifest["hard_boundaries"]["dynamic_lp_claim_enabled"] is False
    assert "controlled_dynamic_lp_appendix_enabled" in manifest["hard_boundaries"]
    assert manifest["hard_boundaries"]["proxy_svar_claim_enabled"] is False
    assert manifest["hard_boundaries"]["system_identification_claim_enabled"] is False
    assert manifest["hard_boundaries"]["valuation_incidence_claim_enabled"] is False
    assert manifest["hard_boundaries"]["reset_calendar_construction_enabled"] is False
    assert manifest["hard_boundaries"]["financialization_causal_claim_enabled"] is False
    assert manifest["hard_boundaries"]["disabled_claim_switches"] == {
        "empirical_claim_enabled": False,
        "policy_failure_claim_enabled": False,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "welfare_claim_enabled": False,
        "tax_output_enabled": False,
        "mpc_output_enabled": False,
        "holder_allocation_enabled": False,
        "reset_calendar_construction_enabled": False,
        "raw_rate_shock_enabled": False,
        "causal_financialization_claim_enabled": False,
    }
    assert (
        manifest["hard_boundaries"]["threshold_policy_failure_claim_enabled"] is False
    )
    assert (
        manifest["hard_boundaries"]["dynamic_identification_promotion_enabled"] is False
    )
    assert (
        manifest["hard_boundaries"]["expanded_external_proxy_frontier_enabled"] is True
    )
    assert (
        manifest["hard_boundaries"]["defensible_structural_appendix_enabled"] is False
    )
    assert manifest["hard_boundaries"]["bounded_event_study_appendix_enabled"] is True
    assert (
        "outputs/tables/ratewall_release_17_external_review_audit.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_dynamic_scenario_paths.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_scenario_crossing_diagnostic.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_dynamic_uncertainty_envelope.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_design_readiness_decision.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_formal_design_test_result_scaffold.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_formal_design_test_result.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_response_estimate_diagnostic.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_cross_source_design_validation.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_evidence_upgrade_source_design_requirement.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_evidence_upgrade_priority_queue.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_evidence_upgrade_tier1_workplan.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_conventional_drag_evidence_tranche.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_conventional_drag_demand_conversion_admission.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_tdsp_current_demand_source_review.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_tdsp_current_demand_unit_conversion.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_tdsp_current_demand_diagnostic_mapping.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_tdsp_policy_path_normalization_blocker.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_tdsp_current_demand_admission_audit.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_dynamic_crossing_robustness.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_event_outcome_panel_value_diagnostic.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_event_level_response_panel.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_panel_design_test_diagnostic.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_pretrend_placebo_diagnostic.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_shock_relevance_diagnostic.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_sign_consistency_diagnostic.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_horizon_sensitivity_diagnostic.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/tables/ratewall_denominator_outlier_window_robustness_diagnostic.csv"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert (
        "outputs/reports/ratewall_dynamic_assumption_mode_equations.md"
        in manifest["artifact_layers"]["assumption_mode"]
    )
    assert any(
        path.endswith("outputs/reports/ratewall_release_17_external_review_packet.md")
        for path in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        manifest["empirical_result_status_counts"][
            "final_documented_blocker_for_full_causal_lp_proxy_svar"
        ]
        == 1
    )
    assert (
        str(release_artifacts.final_paper_quarto)
        in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        "outputs/reports/ratewall_theory_of_change.md"
        in manifest["artifact_layers"]["release_reports"]
    )
    assert {
        "outputs/tables/ratewall_assumption_sets.csv",
        "outputs/tables/ratewall_condition_frontier.csv",
        "outputs/tables/ratewall_offset_decomposition.csv",
        "outputs/tables/ratewall_public_impulse_factorization.csv",
        "outputs/tables/ratewall_public_liability_repricing_ladder.csv",
        "outputs/tables/ratewall_public_liability_repricing_evidence_bridge.csv",
        "outputs/tables/ratewall_public_liability_repricing_reconciliation_gap.csv",
        "outputs/tables/ratewall_mspd_table3_bucket_repricing_gate.csv",
        "outputs/tables/ratewall_interest_recipient_leakage_bridge.csv",
        "outputs/tables/ratewall_interest_recipient_leakage_evidence_gap.csv",
        "outputs/tables/ratewall_treasury_recipient_leakage_source_gate.csv",
        "outputs/tables/ratewall_public_finance_timing_path.csv",
        "outputs/tables/ratewall_public_finance_timing_evidence_gap.csv",
        "outputs/tables/ratewall_public_finance_timing_design_test_scaffold.csv",
        "outputs/tables/ratewall_safe_yield_offset_drag_pairing_gap.csv",
        "outputs/tables/ratewall_bnpl_zero_interest_float_evidence_gap.csv",
        "outputs/tables/ratewall_financialized_balance_sheet_evidence_gap.csv",
        "outputs/tables/ratewall_firm_cash_debt_maturity_evidence_gap.csv",
        "outputs/tables/ratewall_conventional_drag_channel_evidence_gap.csv",
        "outputs/tables/ratewall_conventional_drag_source_design_gate.csv",
        "outputs/tables/ratewall_denominator_response_design_scaffold.csv",
        "outputs/tables/ratewall_denominator_response_design_test_scaffold.csv",
        "outputs/tables/ratewall_denominator_response_gate_attempt.csv",
        "outputs/tables/ratewall_denominator_aligned_response_panel_scaffold.csv",
        "outputs/tables/ratewall_denominator_event_outcome_cell_diagnostic.csv",
        "outputs/tables/ratewall_denominator_event_outcome_panel_value_diagnostic.csv",
        "outputs/tables/ratewall_denominator_event_level_response_panel.csv",
        "outputs/tables/ratewall_denominator_panel_design_test_diagnostic.csv",
        "outputs/tables/ratewall_denominator_pretrend_placebo_diagnostic.csv",
        "outputs/tables/ratewall_denominator_shock_relevance_diagnostic.csv",
        "outputs/tables/ratewall_denominator_sign_consistency_diagnostic.csv",
        "outputs/tables/ratewall_denominator_horizon_sensitivity_diagnostic.csv",
        "outputs/tables/ratewall_denominator_outlier_window_robustness_diagnostic.csv",
        "outputs/tables/ratewall_denominator_design_readiness_decision.csv",
        "outputs/tables/ratewall_denominator_formal_design_test_result_scaffold.csv",
        "outputs/tables/ratewall_denominator_formal_design_test_result.csv",
        "outputs/tables/ratewall_denominator_response_estimate_diagnostic.csv",
        "outputs/tables/ratewall_denominator_cross_source_design_validation.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_source_design_requirement.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_priority_queue.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_tier1_workplan.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv",
        "outputs/tables/ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv",
        "outputs/tables/ratewall_conventional_drag_evidence_tranche.csv",
        "outputs/tables/ratewall_conventional_drag_demand_conversion_admission.csv",
        "outputs/tables/ratewall_tdsp_current_demand_source_review.csv",
        "outputs/tables/ratewall_tdsp_current_demand_unit_conversion.csv",
        "outputs/tables/ratewall_tdsp_current_demand_diagnostic_mapping.csv",
        "outputs/tables/ratewall_tdsp_policy_path_normalization_blocker.csv",
        "outputs/tables/ratewall_tdsp_current_demand_admission_audit.csv",
        "outputs/tables/ratewall_interest_channel_horizon_timing_matrix.csv",
        "outputs/tables/ratewall_interest_channel_promotion_gate.csv",
        "outputs/tables/ratewall_interest_channel_evidence_upgrade_queue.csv",
        "outputs/tables/ratewall_high_priority_interest_channel_source_bridge.csv",
        "outputs/tables/ratewall_source_gate_prior_narrowing_decision.csv",
        "outputs/tables/ratewall_source_gate_exhaustion_closure.csv",
        "outputs/tables/ratewall_restricted_data_gate_spec.csv",
        "outputs/tables/ratewall_assumption_mode_post_closure_boundary_map.csv",
        "outputs/tables/ratewall_sibling_evidence_bridge.csv",
        "outputs/tables/ratewall_sibling_evidence_upgrade_queue.csv",
        "outputs/tables/ratewall_higher_rate_channel_registry.csv",
        "outputs/tables/ratewall_corporate_net_interest_cashflow_bridge.csv",
        "outputs/tables/ratewall_working_capital_cost_channel_diagnostic.csv",
        "outputs/tables/ratewall_term_structure_pricing_carry_diagnostic.csv",
        "outputs/tables/ratewall_interest_channel_module_registry.csv",
        "outputs/tables/ratewall_interest_channel_completion_matrix.csv",
        "outputs/tables/ratewall_flow_stage_decomposition.csv",
        "outputs/tables/ratewall_gross_interest_subchannels.csv",
        "outputs/tables/ratewall_public_finance_adjustment.csv",
        "outputs/tables/ratewall_net_countervailing_channels.csv",
        "outputs/tables/ratewall_wall_hit_scenarios.csv",
        "outputs/tables/ratewall_threshold_solver.csv",
        "outputs/tables/ratewall_assumption_sensitivity.csv",
        "outputs/tables/ratewall_parameter_frontier.csv",
        "outputs/tables/ratewall_minimum_conditions_to_hit_wall.csv",
        "outputs/tables/ratewall_hit_fragility_frontier.csv",
        "outputs/tables/ratewall_frontier_driver_ranking.csv",
        "outputs/tables/ratewall_assumption_mode_driver_dominance_matrix.csv",
        "outputs/tables/ratewall_assumption_mode_pairwise_sensitivity_matrix.csv",
        "outputs/tables/ratewall_backend_invariant_guardrail_audit.csv",
        "outputs/tables/ratewall_backend_completion_verdict.csv",
        "outputs/tables/ratewall_paper_channel_map.csv",
        "outputs/tables/ratewall_paper_canonical_scenario_results.csv",
        "outputs/tables/ratewall_paper_tdc_dynamic_contribution.csv",
        "outputs/tables/ratewall_paper_parameter_justification.csv",
        "outputs/tables/ratewall_paper_sensitivity_summary.csv",
        "outputs/tables/ratewall_paper_disabled_claims_appendix.csv",
        "outputs/tables/ratewall_paper_support_invariant_audit.csv",
        "outputs/tables/ratewall_backend_accounting_identity_audit.csv",
        "outputs/tables/ratewall_paper_scenario_accounting_bridge.csv",
        "outputs/tables/ratewall_paper_dynamic_scenario_summary.csv",
        "outputs/tables/ratewall_conventional_drag_decomposition.csv",
        "outputs/tables/ratewall_split_denominator_comparison.csv",
        "outputs/tables/ratewall_denominator_sensitivity.csv",
        "outputs/tables/ratewall_split_denominator_uncertainty.csv",
        "outputs/tables/ratewall_split_denominator_regime_stability.csv",
        "outputs/tables/ratewall_denominator_literature_matrix.csv",
        "outputs/tables/ratewall_split_denominator_joint_uncertainty.csv",
        "outputs/tables/ratewall_split_denominator_joint_regime_stability.csv",
        "outputs/tables/ratewall_denominator_classifier_comparison.csv",
        "outputs/tables/ratewall_backend_model_readiness_gate.csv",
        "outputs/tables/ratewall_chapter_readiness_self_audit.csv",
        "outputs/tables/ratewall_financialized_balance_sheet_channel.csv",
        "outputs/tables/ratewall_equity_transmission_channel_map.csv",
        "outputs/tables/ratewall_equity_exposure_matrix.csv",
        "outputs/tables/ratewall_equity_sensitivity_diagnostic.csv",
        "outputs/tables/ratewall_equity_claim_status.csv",
        "outputs/tables/ratewall_equity_evidence_workplan.csv",
        "outputs/tables/ratewall_parameter_packs.csv",
        "outputs/tables/ratewall_frontier_summary.csv",
        "outputs/tables/ratewall_regime_map.csv",
        "outputs/tables/ratewall_assumption_mode_interpretation.csv",
        "outputs/tables/ratewall_prior_stack_diagnostic.csv",
        "outputs/tables/ratewall_scenario_ladder.csv",
        "outputs/tables/ratewall_model_adequacy_matrix.csv",
        "outputs/tables/ratewall_assumption_mode_claim_boundary_audit.csv",
        "outputs/reports/ratewall_assumption_engine_memo.md",
        "outputs/reports/ratewall_assumption_mode_theory_chapter.md",
        "outputs/reports/ratewall_assumption_mode_model_audit_packet.md",
        "outputs/reports/ratewall_assumption_mode_critique_response.md",
        "outputs/reports/ratewall_professor_model_review_prompt.md",
        "outputs/reports/ratewall_interest_channel_expansion_plan.md",
        "outputs/reports/ratewall_backend_completion_readiness_report.md",
        "outputs/reports/ratewall_assumption_mode_v1_stage_completion_report.md",
        "outputs/reports/ratewall_assumption_mode_post_closure_boundary_memo.md",
        "outputs/reports/ratewall_equity_transmission_attenuation_memo.md",
        "outputs/reports/ratewall_equity_evidence_workplan.md",
        "outputs/reports/ratewall_split_denominator_evidence_workplan.md",
        "configs/ratewall_assumption_sets.yml",
        "configs/ratewall_parameter_packs.yml",
    } <= set(manifest["artifact_layers"]["assumption_mode"])
    assert not {
        artifact
        for layer_artifacts in manifest["artifact_layers"].values()
        for artifact in layer_artifacts
        if artifact.startswith("outputs/figures/") and artifact.endswith(".svg")
    }
    assert (
        "outputs/reports/ratewall_final_paper.pdf"
        not in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        "outputs/reports/ratewall_public_deck.pptx"
        not in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        str(release_artifacts.public_readme)
        in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        "outputs/tables/ratewall_causal_defensibility_blocker.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_event_study_robustness.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_dynamic_causal_final_blocker.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_event_study_hac_diagnostics.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_release_4_0_dynamic_causal_final_blocker.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_controlled_dynamic_lp_results.csv"
        in manifest["artifact_layers"]["empirical_estimates"]
    )
    assert (
        "outputs/tables/ratewall_release_5_0_proxy_svar_final_blocker.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_release_6_0_proxy_svar_final_blocker.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_proxy_svar_system_panel.csv"
        in manifest["artifact_layers"]["empirical_estimates"]
    )
    assert (
        "outputs/tables/ratewall_release_7_0_proxy_svar_final_blocker.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_release_8_0_nonpromotion_proof.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_release_9_0_final_nonpromotion_proof.csv"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/tables/ratewall_threshold_simulation.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_financialization_pressure.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_safe_asset_retention_context.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_threshold_calibration_ranges.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_threshold_calibrated_simulation.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_du_ru_tga_calibration_bridge.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_financialization_pressure_evidence_appendix.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_release_19_post_audit_methodology_audit.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_release_20_activity_demand_benchmark.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_release_20_state_dependent_lp_diagnostics.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_release_20_benchmark_submission_decision.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_release_21_live_refresh_endpoint_audit.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_release_21_final_benchmark_gate.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_release_21_backend_invariant_audit.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    financialization_layer_paths = {
        "outputs/tables/ratewall_financialization_proxy_registry.csv",
        "outputs/tables/ratewall_household_safe_asset_capture_proxy.csv",
        "outputs/tables/ratewall_household_safe_asset_exposure_panel.csv",
        "outputs/tables/ratewall_household_safe_asset_access_context.csv",
        "outputs/tables/ratewall_retail_safe_yield_access_substitution_context.csv",
        "outputs/tables/ratewall_retail_deposit_beta_gap_context.csv",
        "outputs/tables/ratewall_retail_pass_through_dispersion_panel.csv",
        "outputs/tables/ratewall_deposit_competition_conditioner.csv",
        "outputs/tables/ratewall_deposit_mmf_substitution_surface.csv",
        "outputs/tables/ratewall_personal_net_interest_position_context.csv",
        "outputs/tables/ratewall_firm_liquid_asset_public_context.csv",
        "outputs/tables/ratewall_firm_liquid_asset_cushion_panel.csv",
        "outputs/tables/ratewall_firm_net_interest_cushion_context.csv",
        "outputs/tables/ratewall_firm_rollover_pressure_panel.csv",
        "outputs/tables/ratewall_firm_short_rate_exposure_proxy.csv",
        "outputs/tables/ratewall_household_borrower_fragility_context.csv",
        "outputs/tables/ratewall_bank_loan_repricing_context.csv",
        "outputs/tables/ratewall_cre_refinancing_public_context.csv",
        "outputs/tables/ratewall_private_credit_bdc_context.csv",
        "outputs/tables/ratewall_safe_yield_paired_proxy_surface.csv",
        "outputs/tables/ratewall_financialization_proxy_source_gate.csv",
        "outputs/tables/ratewall_financialization_source_gate.csv",
        "outputs/tables/ratewall_financialization_restricted_protocols.csv",
        "outputs/tables/ratewall_financialization_double_count_audit.csv",
        "outputs/tables/ratewall_financialization_overlap_audit.csv",
        "outputs/tables/ratewall_financialization_artifact_traceability_matrix.csv",
        "outputs/tables/ratewall_paper_financialization_interpretation.csv",
        "outputs/reports/ratewall_financialization_proxy_backend_audit.md",
        "outputs/reports/ratewall_financialization_interpretation_memo.md",
    }
    assert financialization_layer_paths <= set(
        manifest["artifact_layers"]["financialization_proxy_context_design"]
    )
    backend_expansion_layer_paths = {
        f"outputs/tables/{artifact_name}"
        for artifact_name in backend_expansion_release_artifacts
    }
    assert backend_expansion_layer_paths <= set(
        manifest["artifact_layers"]["backend_expansion_context_design"]
    )
    assert (
        "outputs/tables/ratewall_contractionary_benchmark_calibration.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_threshold_uncertainty_bands.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_historical_threshold_validation.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_policy_boundary_synthesis.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_blocker_resolution_ledger.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_publication_claim_decision.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_final_blocker_ledger.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_release_16_source_resolution_closeout.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        "outputs/tables/ratewall_release_16_no_further_promotion_ledger.csv"
        in manifest["artifact_layers"]["threshold_financialization_context"]
    )
    assert (
        str(release_artifacts.release_16_bounded_publication_closeout_memo)
        in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        str(release_artifacts.release_16_reviewer_blocker_text)
        in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        str(release_artifacts.release_20_submission_readiness_memo)
        in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        str(release_artifacts.release_21_backend_closeout_memo)
        in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        "outputs/reports/ratewall_journal_submission_appendix.md"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/reports/ratewall_release_4_0_referee_packet.md"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/reports/ratewall_release_5_0_dynamic_lp_appendix.md"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/reports/ratewall_release_6_0_proxy_svar_system_appendix.md"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/reports/ratewall_release_7_0_system_identification_appendix.md"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/reports/ratewall_release_8_0_system_nonpromotion_appendix.md"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/reports/ratewall_release_9_0_structural_boundary_appendix.md"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        "outputs/reports/ratewall_submission_causal_appendix.md"
        in manifest["artifact_layers"]["empirical_diagnostics_and_blockers"]
    )
    assert (
        str(release_artifacts.archival_manifest)
        not in manifest["artifact_layers"]["release_reports"]
    )
    assert (
        str(release_artifacts.publication_claim_decision_memo)
        in manifest["artifact_layers"]["release_reports"]
    )
    assert "Publication-Claim Decision Memo" in (
        release_artifacts.publication_claim_decision_memo.read_text(encoding="utf-8")
    )
    assert "Source And Provenance Appendix" in (
        release_artifacts.source_appendix.read_text(encoding="utf-8")
    )
    assert "Empirical Method Appendix" in (
        release_artifacts.empirical_appendix.read_text(encoding="utf-8")
    )
    assert "Limitations Appendix" in (
        release_artifacts.limitations_appendix.read_text(encoding="utf-8")
    )
    assert "RateWall Validation Package" in (
        release_artifacts.validation_package.read_text(encoding="utf-8")
    )


def test_release_23_archive_verifier_fails_closed_on_archive_mutations(
    tmp_path: Path,
) -> None:
    required_files = {
        "README.md": b"safe backend archive\n",
        "outputs/tables/treasury_maturity_ladder.csv": b"a,b\n1,2\n",
        "outputs/tables/treasury_mspd_reconciliation.csv": b"status\nreview\n",
        "outputs/tables/ratewall_release_22_core_output_source_gate.csv": (
            b"artifact,gate\nx,blocked\n"
        ),
    }

    def write_case(
        name: str,
        files: dict[str, bytes],
        *,
        records: list[dict[str, str]] | None = None,
    ) -> tuple[Path, Path]:
        archive_path = tmp_path / f"{name}.zip"
        manifest_path = tmp_path / f"{name}.json"
        with zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for archive_name, payload in files.items():
                archive.writestr(archive_name, payload)
        if records is None:
            records = [
                {
                    "archive_path": archive_name,
                    "source_path": archive_name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
                for archive_name, payload in files.items()
            ]
        manifest_path.write_text(
            json.dumps({"files": records}, sort_keys=True), encoding="utf-8"
        )
        return archive_path, manifest_path

    good_archive, good_manifest = write_case("good", required_files)
    assert (
        _release_23_archive_verification_rows(
            archive_path=good_archive, manifest_path=good_manifest
        )[0]["audit_status"]
        == "pass"
    )

    good_records = json.loads(good_manifest.read_text(encoding="utf-8"))["files"]
    mutations = {}
    mutations["missing_listed_file"] = (
        required_files,
        [
            *good_records,
            {
                "archive_path": "missing.csv",
                "source_path": "missing.csv",
                "sha256": hashlib.sha256(b"missing").hexdigest(),
            },
        ],
    )
    bad_hash_records = [dict(record) for record in good_records]
    bad_hash_records[0]["sha256"] = "0" * 64
    mutations["hash_mismatch"] = (required_files, bad_hash_records)
    mutations["duplicate_manifest_path"] = (
        required_files,
        [*good_records, dict(good_records[0])],
    )
    unsafe_records = [dict(record) for record in good_records]
    unsafe_records[0]["source_path"] = "../README.md"
    mutations["unsafe_source_path"] = (required_files, unsafe_records)
    mutations["unlisted_extra_file"] = (
        {**required_files, "outputs/tables/unlisted.csv": b"x\n"},
        good_records,
    )
    mutations["unsafe_language"] = (
        {
            **required_files,
            "README.md": b"Figures regenerate from source-backed tables.\n",
        },
        None,
    )
    mutations["compiled_render_artifact"] = (
        {**required_files, "outputs/reports/ratewall_final_paper.pdf": b"%PDF stale"},
        None,
    )

    duplicate_zip_archive = tmp_path / "duplicate_zip.zip"
    duplicate_zip_manifest = tmp_path / "duplicate_zip.json"
    with zipfile.ZipFile(
        duplicate_zip_archive, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for archive_name, payload in required_files.items():
            archive.writestr(archive_name, payload)
        with pytest.warns(UserWarning, match="Duplicate name: 'README.md'"):
            archive.writestr("README.md", b"duplicate\n")
    duplicate_zip_manifest.write_text(
        json.dumps({"files": good_records}, sort_keys=True), encoding="utf-8"
    )
    assert (
        _release_23_archive_verification_rows(
            archive_path=duplicate_zip_archive, manifest_path=duplicate_zip_manifest
        )[0]["audit_status"]
        == "fail"
    )

    for case_name, (files, records) in mutations.items():
        archive_path, manifest_path = write_case(case_name, files, records=records)
        row = _release_23_archive_verification_rows(
            archive_path=archive_path, manifest_path=manifest_path
        )[0]
        assert row["audit_status"] == "fail", case_name


def test_empirical_specs_reject_raw_policy_rate_changes() -> None:
    spec = LocalProjectionSpec(
        outcome="inflation",
        shock="policy_rate_change",
        state_variable="debt_gdp",
        horizons=(0, 1),
        controls=(),
    )

    assert spec.validate() == ["raw policy-rate changes are not valid monetary shocks"]


def test_frn_and_tips_formula_fixtures_are_validation_not_pricing() -> None:
    frn = validate_frn_daily_accrued_interest(
        {
            "daily_int_accrual_rate": "0.00012139",
            "daily_accrued_int_per100": "0.012139",
        }
    )
    assert frn.status == "formula_validated_not_pricing"
    assert frn.formula_name == "frn_daily_accrued_interest_per100"

    tips = validate_tips_index_ratio(
        {
            "ref_cpi": "326.90000",
            "index_ratio": "1.002860",
        },
        {
            "ref_cpi_on_issue_date": "326.733900",
            "index_ratio_on_issue_date": "1.002350",
        },
    )
    assert tips.status == "formula_validated_not_pricing"
    assert tips.formula_name == "tips_index_ratio_from_ref_cpi"
    assert "not pricing" in tips.note


def test_valuation_edge_fixtures_are_not_pricing_claims() -> None:
    missing_frn = validate_frn_daily_accrued_interest(
        {"daily_int_accrual_rate": "", "daily_accrued_int_per100": ""}
    )
    assert missing_frn.status == "formula_input_unavailable_not_pricing"
    assert "not final pricing" in missing_frn.note

    review_frn = validate_frn_daily_accrued_interest(
        {
            "daily_int_accrual_rate": "0.00012139",
            "daily_accrued_int_per100": "0.010000",
        }
    )
    assert review_frn.status == "formula_review_not_pricing"

    decimal_frn = validate_frn_daily_accrued_interest(
        {
            "daily_int_accrual_rate": "0.00012139",
            "daily_accrued_int_per100": "0.012139",
        }
    )
    percent_frn = validate_frn_daily_accrued_interest(
        {
            "daily_int_accrual_rate": "4.3704",
            "daily_accrued_int_per100": "0.012140",
        }
    )
    assert decimal_frn.status == "formula_validated_not_pricing"
    assert percent_frn.status == "formula_validated_not_pricing"

    older_tips_without_terms = validate_tips_index_ratio(
        {
            "cusip": "912810OLDER",
            "ref_cpi": "326.90000",
            "index_ratio": "1.002860",
        },
        {},
    )
    assert older_tips_without_terms.status == "formula_input_unavailable_not_pricing"
    assert "not final pricing" in older_tips_without_terms.note

    review_tips = validate_tips_index_ratio(
        {"ref_cpi": "326.90000", "index_ratio": "1.100000"},
        {
            "ref_cpi_on_issue_date": "326.733900",
            "index_ratio_on_issue_date": "1.002350",
        },
    )
    assert review_tips.status == "formula_review_not_pricing"


def test_tips_review_classification_and_convention_fixtures_stay_disabled() -> None:
    tolerance_edge = validate_tips_index_ratio(
        {
            "ref_cpi": "329.88126",
            "index_ratio": "1.23080",
        },
        {
            "ref_cpi_on_issue_date": "269.056870",
            "index_ratio_on_issue_date": "1.003870",
        },
    )
    assert tolerance_edge.status == "formula_review_not_pricing"
    classification = classify_tips_formula_review(
        {
            "ref_cpi": "329.88126",
            "index_ratio": "1.23080",
        },
        {
            "ref_cpi_on_issue_date": "269.056870",
            "index_ratio_on_issue_date": "1.003870",
        },
        tolerance_edge,
    )
    assert (
        classification.status == "classified_tolerance_edge_source_rounding_not_pricing"
    )
    assert classification.unresolved is False
    assert "not pricing" in classification.rationale

    extended_edge = validate_tips_index_ratio(
        {
            "ref_cpi": "326.63170",
            "index_ratio": "1.29804",
        },
        {
            "ref_cpi_on_issue_date": "251.261750",
            "index_ratio_on_issue_date": "0.998510",
        },
    )
    extended_classification = classify_tips_formula_review(
        {
            "ref_cpi": "326.63170",
            "index_ratio": "1.29804",
        },
        {
            "ref_cpi_on_issue_date": "251.261750",
            "index_ratio_on_issue_date": "0.998510",
        },
        extended_edge,
    )
    assert (
        extended_classification.status
        == "classified_extended_tolerance_edge_source_rounding_not_pricing"
    )
    assert extended_classification.unresolved is False

    fixtures = valuation_convention_audit_fixtures()
    assert {fixture["audit_component"] for fixture in fixtures} == {
        "frn_reset_convention",
        "tips_accrual_convention",
    }
    assert all(fixture["audit_required"] == "true" for fixture in fixtures)
    assert all(fixture["audit_passed"] == "false" for fixture in fixtures)
    assert all(fixture["pricing_output_enabled"] == "false" for fixture in fixtures)

    edge_fixtures = cashflow_edge_fixture_rows()
    assert {fixture["fixture_id"] for fixture in edge_fixtures} == {
        "frn_reset_date_boundary",
        "frn_leap_day_accrual_period",
        "tips_cpi_interpolation_rounding",
        "tips_reopening_issue_date",
    }
    assert all(
        fixture["test_status"] == "fixture_contract_tested_not_pricing"
        for fixture in edge_fixtures
    )
    assert all(fixture["example_calculation_name"] for fixture in edge_fixtures)
    assert all(
        fixture["example_calculation_status"]
        in {
            "example_validated_not_pricing",
            "example_tolerance_edge_classified_not_pricing",
        }
        for fixture in edge_fixtures
    )
    assert all(
        fixture["pricing_output_enabled"] == "false" for fixture in edge_fixtures
    )

    switch_audit = pricing_switch_audit_rows()
    assert {row["switch_name"] for row in switch_audit} >= {
        "convention_audit_gate",
        "cashflow_edge_fixture_gate",
        "holder_allocation_gate",
        "explicit_pricing_authorization_enabled",
    }
    assert all(row["switch_enabled"] == "false" for row in switch_audit)
    assert all(row["pricing_output_enabled"] == "false" for row in switch_audit)
    assert all(
        row["claim_boundary"] == "pricing_switch_audit_disabled_not_pricing"
        for row in switch_audit
    )

    opt_in = valuation_engine_opt_in_contract_rows(
        convention_audit_rows=[
            {"audit_component": "frn_reset_convention", "audit_passed": "true"},
            {"audit_component": "tips_accrual_convention", "audit_passed": "true"},
        ],
        cashflow_edge_rows=edge_fixtures,
        holder_gate_rows=[
            {
                "gate_component": "holder_allocation_gate",
                "incidence_claim_enabled": "false",
            }
        ],
    )
    assert {row["requirement_id"] for row in opt_in} == {
        "audited_conventions",
        "cashflow_edge_fixtures",
        "holder_allocation_gate",
        "explicit_pricing_switch",
    }
    assert all(row["pricing_output_enabled"] == "false" for row in opt_in)
    assert all(row["holder_allocation_enabled"] == "false" for row in opt_in)
    assert all(row["incidence_claim_enabled"] == "false" for row in opt_in)
    assert [
        row for row in opt_in if row["requirement_id"] == "explicit_pricing_switch"
    ][0]["requirement_satisfied"] == "false"

    partial_switches = ValuationOptInSwitches(
        convention_audit_gate_enabled=True,
        cashflow_edge_fixture_gate_enabled=True,
        holder_allocation_gate_enabled=True,
        explicit_pricing_authorization_enabled=True,
    )
    partial_opt_in = valuation_engine_opt_in_contract_rows(
        convention_audit_rows=[
            {"audit_component": "frn_reset_convention", "audit_passed": "true"},
            {"audit_component": "tips_accrual_convention", "audit_passed": "true"},
        ],
        cashflow_edge_rows=edge_fixtures,
        holder_gate_rows=[
            {
                "gate_component": "holder_allocation_gate",
                "incidence_claim_enabled": "false",
            }
        ],
        switches=partial_switches,
    )
    assert [
        row
        for row in partial_opt_in
        if row["requirement_id"] == "explicit_pricing_switch"
    ][0]["requirement_satisfied"] == "false"
    assert all(row["pricing_output_enabled"] == "false" for row in partial_opt_in)

    all_future_switches = ValuationOptInSwitches(
        convention_audit_gate_enabled=True,
        cashflow_edge_fixture_gate_enabled=True,
        holder_allocation_gate_enabled=True,
        holder_bridge_enabled=True,
        tax_assumptions_enabled=True,
        mpc_assumptions_enabled=True,
        welfare_incidence_enabled=True,
        explicit_pricing_authorization_enabled=True,
    )
    all_switch_opt_in = valuation_engine_opt_in_contract_rows(
        convention_audit_rows=[
            {"audit_component": "frn_reset_convention", "audit_passed": "true"},
            {"audit_component": "tips_accrual_convention", "audit_passed": "true"},
        ],
        cashflow_edge_rows=edge_fixtures,
        holder_gate_rows=[
            {
                "gate_component": "holder_allocation_gate",
                "incidence_claim_enabled": "false",
            }
        ],
        switches=all_future_switches,
    )
    assert [
        row
        for row in all_switch_opt_in
        if row["requirement_id"] == "explicit_pricing_switch"
    ][0]["requirement_satisfied"] == "true"
    assert all(row["pricing_output_enabled"] == "false" for row in all_switch_opt_in)
    assert all(
        row["claim_boundary"] == "disabled_valuation_opt_in_contract_not_pricing"
        for row in all_switch_opt_in
    )


def test_source_backed_edge_classifiers_fail_closed_without_pricing() -> None:
    frn_records = [
        {
            "cusip": "FRN1",
            "record_date": "2024-02-28",
            "start_of_accrual_period": "2024-02-28",
            "end_of_accrual_period": "2024-02-29",
            "daily_index": "4.4700",
            "spread": "0.1030",
            "daily_int_accrual_rate": "4.5730",
            "daily_accrued_int_per100": "0.012703",
        },
        {
            "cusip": "FRN1",
            "record_date": "2024-02-29",
            "start_of_accrual_period": "2024-02-29",
            "end_of_accrual_period": "2024-03-01",
            "daily_index": "4.4800",
            "spread": "0.1030",
            "daily_int_accrual_rate": "4.5830",
            "daily_accrued_int_per100": "0.012731",
        },
    ]
    tips_terms = {
        "TIPS1": {
            "cusip": "TIPS1",
            "ref_cpi_on_issue_date": "269.056870",
            "index_ratio_on_issue_date": "1.003870",
            "reopening": "No",
            "issue_date": "2020-01-31",
        },
        "TIPS2": {
            "cusip": "TIPS2",
            "ref_cpi_on_issue_date": "326.733900",
            "index_ratio_on_issue_date": "1.002350",
            "reopening": "No",
            "issue_date": "2026-04-30",
        },
    }
    tips_records = [
        {
            "cusip": "TIPS1",
            "index_date": "2026-05-29",
            "original_issue_date": "2020-01-15",
            "ref_cpi": "329.88126",
            "index_ratio": "1.23080",
        },
        {
            "cusip": "TIPS2",
            "index_date": "2026-05-30",
            "original_issue_date": "2026-04-15",
            "ref_cpi": "326.90000",
            "index_ratio": "1.002860",
        },
    ]

    rows = cashflow_edge_source_sample_rows(
        frn_records=frn_records,
        frn_terms={
            "FRN1": [
                {
                    "cusip": "FRN1",
                    "frn_index_determination_date": "2024-02-26",
                    "frn_index_determination_rate": "4.4700",
                    "reopening": "No",
                }
            ]
        },
        tips_records=tips_records,
        tips_terms=tips_terms,
        tips_term_rows={
            "TIPS2": [
                {
                    "cusip": "TIPS2",
                    "ref_cpi_on_issue_date": "326.733900",
                    "index_ratio_on_issue_date": "1.002350",
                    "reopening": "No",
                    "issue_date": "2026-04-30",
                },
                {
                    "cusip": "TIPS2",
                    "ref_cpi_on_issue_date": "326.733900",
                    "index_ratio_on_issue_date": "1.002350",
                    "reopening": "Yes",
                    "issue_date": "2026-05-15",
                },
            ]
        },
    )
    by_id = {row["fixture_id"]: row for row in rows}
    assert (
        by_id["frn_reset_date_boundary_source_sample"]["source_edge_classifier_status"]
        == "source_rate_change_observed_with_term_fields_recurring_reset_calendar_missing_not_pricing"
    )
    assert (
        "FRN auction term row"
        in by_id["frn_reset_date_boundary_source_sample"]["source_edge_note"]
    )
    assert (
        by_id["frn_leap_day_accrual_period_source_sample"][
            "source_edge_classifier_status"
        ]
        == "source_leap_day_observed_not_pricing"
    )
    assert (
        by_id["tips_cpi_interpolation_rounding_source_sample"][
            "source_edge_classifier_status"
        ]
        == "classified_tolerance_edge_source_rounding_not_pricing"
    )
    assert (
        by_id["tips_reopening_issue_date_source_sample"][
            "source_edge_classifier_status"
        ]
        == "source_reopening_observed_not_pricing"
    )
    assert all(row["pricing_output_enabled"] == "false" for row in rows)
    assert all(
        row["claim_boundary"] == "cashflow_edge_fixture_not_pricing_engine"
        for row in rows
    )


def test_frn_reset_blocker_map_detects_schema_drift_without_pricing() -> None:
    frn_metadata = RetrievalMetadata(
        source_id="treasury_fiscaldata",
        series_id="treasury_frn_daily_indexes",
        source_url="https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/frn_daily_indexes",
        units="mixed",
        frequency="daily",
        transform="frn_daily_index_path",
        retrieved_at="2026-05-10T00:00:00Z",
    )
    term_metadata = RetrievalMetadata(
        source_id="treasury_fiscaldata",
        series_id="treasury_auction_frn_terms",
        source_url="https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query",
        units="mixed",
        frequency="auction",
        transform="frn_term_sheet_fields",
        retrieved_at="2026-05-10T00:00:00Z",
    )
    rows = _frn_reset_source_blocker_map_rows(
        {
            "treasury_frn_daily_indexes": SourceSnapshot(
                metadata=frn_metadata,
                records=[
                    {
                        "cusip": "FRN1",
                        "record_date": "2026-05-10",
                        "daily_index": "4.1",
                        "daily_int_accrual_rate": "4.2",
                        "next_reset_date": "2026-05-13",
                    }
                ],
            ),
            "treasury_auction_frn_terms": SourceSnapshot(
                metadata=term_metadata,
                records=[
                    {
                        "cusip": "FRN1",
                        "frn_index_determination_date": "2026-05-06",
                        "frn_index_determination_rate": "4.1",
                    }
                ],
            ),
        }
    )
    recurring = [
        row
        for row in rows
        if row["source_field_group"] == "recurring_reset_calendar_fields"
    ][0]
    assert recurring["field_status"] == "candidate_fields_observed_requires_audit"
    assert recurring["schema_drift_status"] == (
        "candidate_reset_calendar_fields_present_requires_audit"
    )
    assert (
        recurring["blocker_status"] == "candidate_reset_calendar_fields_require_audit"
    )
    assert recurring["reset_calendar_candidate_fields"] == "next_reset_date"
    assert recurring["pricing_output_enabled"] == "false"


def test_disabled_holder_mapping_switches_do_not_enable_incidence() -> None:
    design = disabled_mapping_design(
        gate_component="sec_nmfp_mspd_cusip_overlap",
        source_inputs="SEC N-MFP CUSIPs;MSPD Table 3 cash-flow scaffold",
    )
    assert design["mapping_schema_version"] == "holder_mapping_design_v0_non_final"
    assert design["security_match_key"] == "cusip"
    assert design["holder_bridge_enabled"] == "false"
    assert design["incidence_claim_enabled"] == "false"

    switches = HolderMappingSwitches(
        holder_bridge_enabled=True,
        tax_assumptions_enabled=True,
        mpc_assumptions_enabled=True,
        welfare_incidence_enabled=False,
    )
    assert switches.incidence_claim_enabled is False

    rows = disabled_final_owner_allocation_rows(
        gate_rows=[
            {
                "gate_component": "sec_nmfp_mspd_cusip_overlap",
                "status": "non_final_cusip_overlap_available",
                "source_inputs": "SEC N-MFP CUSIPs;MSPD Table 3 cash-flow scaffold",
            }
        ],
        switches=switches,
    )
    assert (
        rows[0]["allocation_schema_version"]
        == "holder_final_owner_allocation_v0_disabled"
    )
    assert rows[0]["allocation_weight"] == ""
    assert rows[0]["allocated_cashflow_bil"] == ""
    assert rows[0]["tax_assumption"] == ""
    assert rows[0]["mpc_assumption"] == ""
    assert rows[0]["welfare_incidence_metric"] == ""
    assert rows[0]["incidence_claim_enabled"] == "false"
    assert rows[0]["claim_boundary"] == "disabled_schema_not_final_owner_incidence"

    ledger = disabled_allocation_design_ledger_rows(
        gate_rows=[
            {
                "gate_component": "sec_nmfp_mspd_cusip_overlap",
                "status": "non_final_cusip_overlap_available",
                "source_inputs": "SEC N-MFP CUSIPs;MSPD Table 3 cash-flow scaffold",
            }
        ],
        switches=switches,
    )
    assert {
        "legal_holder",
        "intermediary",
        "beneficial_owner",
        "taxable_owner",
        "mpc",
        "welfare",
    } == {row["design_layer"] for row in ledger}
    assert all(row["switch_enabled"] == "false" for row in ledger)
    assert all(row["weight_output_enabled"] == "false" for row in ledger)
    assert all(row["cashflow_output_enabled"] == "false" for row in ledger)
    assert all(row["incidence_claim_enabled"] == "false" for row in ledger)


def test_demo_snapshot_uses_injected_clock(tmp_path: Path) -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    fixed = datetime(2026, 5, 9, 19, 0, tzinfo=timezone.utc)
    from ratewall.data.demo import build_demo_snapshots

    snapshots = build_demo_snapshots(registry, clock=lambda: fixed)

    assert snapshots[0].metadata.retrieved_at == "2026-05-09T19:00:00Z"
    assert snapshots[0].metadata.source_release_at is not None


def test_live_fallback_snapshot_is_explicitly_labeled() -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")

    snapshot = fallback_snapshot(registry, "h41_current", reason="parser failed")

    assert snapshot.metadata.snapshot_kind == "fallback_stub"
    assert snapshot.metadata.note == "Live parser fallback: parser failed"
    assert snapshot.metadata.source_url.startswith("https://")


def test_live_snapshot_mode_falls_back_with_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")

    def fail_pull(self: object, series_id: str = "h41_current") -> object:
        raise ValueError("parse miss")

    monkeypatch.setattr("ratewall.data.build.FedH41Adapter.pull_release", fail_pull)
    output = build_snapshot_bundle(
        registry=registry,
        output=tmp_path / "live.json",
        mode="live",
        series_ids=("h41_current",),
        progress=True,
    )

    progress = capsys.readouterr().err
    assert "[ratewall-live] pulling h41_current from fed_h41" in progress
    assert "endpoint=https://www.federalreserve.gov/releases/h41/current/" in progress
    assert "[ratewall-live] fallback h41_current" in progress
    [snapshot] = read_snapshot_bundle(output)
    assert snapshot.metadata.snapshot_kind == "fallback_stub"
    assert "parse miss" in (snapshot.metadata.note or "")
    assert "source=fed_h41" in (snapshot.metadata.note or "")
    assert "endpoint=https://www.federalreserve.gov/releases/h41/current/" in (
        snapshot.metadata.note or ""
    )


def test_live_snapshot_mode_falls_back_on_series_deadline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")

    def slow_pull(self: object, series_id: str = "h41_current") -> object:
        time.sleep(2)
        return self

    monkeypatch.setenv("RATEWALL_LIVE_SERIES_TIMEOUT_SECONDS", "1")
    monkeypatch.setattr("ratewall.data.build.FedH41Adapter.pull_release", slow_pull)

    output = build_snapshot_bundle(
        registry=registry,
        output=tmp_path / "live-timeout.json",
        mode="live",
        series_ids=("h41_current",),
    )

    [snapshot] = read_snapshot_bundle(output)
    assert snapshot.metadata.snapshot_kind == "fallback_stub"
    assert "live retrieval exceeded 1s for h41_current" in (
        snapshot.metadata.note or ""
    )


def test_data_snapshot_cli_accepts_repeated_series_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ratewall import cli as ratewall_cli

    captured: dict[str, object] = {}

    def fake_build_snapshot_bundle(**kwargs: object) -> Path:
        captured.update(kwargs)
        return kwargs["output"]  # type: ignore[return-value]

    monkeypatch.setattr(
        "ratewall.cli.build_snapshot_bundle",
        fake_build_snapshot_bundle,
    )

    parser = ratewall_cli.build_parser()
    output = tmp_path / "pce-dpi.json"
    args = parser.parse_args(
        [
            "data",
            "snapshot",
            "--mode",
            "live",
            "--output",
            str(output),
            "--series",
            "PCEC",
            "--series",
            "DSPI",
        ]
    )

    assert args.func(args) == 0
    assert captured["output"] == output
    assert captured["mode"] == "live"
    assert captured["series_ids"] == ("PCEC", "DSPI")
    assert captured["progress"] is True


def test_live_mspd_table3_pull_uses_latest_month_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    calls: list[tuple[dict[str, str], bool]] = []

    def fake_pull_table(
        _self: object,
        series_id: str,
        *,
        params: dict[str, str] | None = None,
        paginate: bool = False,
    ) -> SourceSnapshot:
        params = dict(params or {})
        calls.append((params, paginate))
        records = (
            [{"record_date": "2026-04-30"}]
            if params.get("fields") == "record_date"
            else [
                {
                    "record_date": "2026-04-30",
                    "security_type_desc": "Marketable",
                    "security_class1_desc": "Bills",
                    "maturity_date": "2026-06-30",
                    "current_month_outstanding_amt": "1000000000",
                    "src_line_nbr": "1",
                }
            ]
        )
        return SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id="treasury_fiscaldata",
                series_id=series_id,
                source_url=registry.series_definition(series_id).endpoint,
                units="millions_of_dollars",
                frequency="monthly",
                transform="security_level_maturity_proxy",
                retrieved_at="2026-05-14T00:00:00Z",
                source_release_at="2026-04-30",
            ),
            records=records,
        )

    monkeypatch.setattr(
        "ratewall.data.build.FiscalDataAdapter.pull_table",
        fake_pull_table,
    )

    output = build_snapshot_bundle(
        registry=registry,
        output=tmp_path / "mspd-live-latest.json",
        mode="live",
        series_ids=("treasury_mspd_table_3",),
    )

    [snapshot] = read_snapshot_bundle(output)
    assert snapshot.metadata.snapshot_kind == "live"
    assert len(calls) == 2
    assert calls[0] == (
        {"fields": "record_date", "page[size]": "1", "sort": "-record_date"},
        False,
    )
    assert calls[1][0]["filter"] == "record_date:eq:2026-04-30"
    assert calls[1][0]["sort"] == "src_line_nbr"
    assert calls[1][1] is False
    assert snapshot.records[0]["maturity_date"] == "2026-06-30"


def test_mspd_maturity_ladder_uses_security_level_records(tmp_path: Path) -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    snapshot = build_snapshot_bundle(
        registry=registry,
        output=tmp_path / "snapshot.json",
        mode="demo",
    )

    derived = derive_accounting_inputs(read_snapshot_bundle(snapshot))

    assert "MSPD table 3" in str(derived.maturity_ladder[0]["source_note"])
    assert derived.horizons[0].debt_repricing < derived.horizons[-1].debt_repricing
    assert all(
        horizon.debt_repricing <= derived.debt_held_public_bil
        for horizon in derived.horizons
    )


def test_fallback_mspd_cannot_masquerade_as_live_maturity_ladder(
    tmp_path: Path,
) -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    snapshots = build_snapshot_bundle(
        registry=registry,
        output=tmp_path / "snapshot.json",
        mode="demo",
    )
    records = [
        fallback_snapshot(
            registry,
            snapshot.metadata.series_id,
            reason="unit test fallback",
        )
        if snapshot.metadata.series_id == "treasury_mspd_table_3"
        else snapshot
        for snapshot in read_snapshot_bundle(snapshots)
    ]

    derived = derive_accounting_inputs(records)

    assert {row["source_status"] for row in derived.maturity_ladder} == {
        "anchor_fallback_not_live_security_level"
    }
    assert all(
        "fallback_stub" in str(row["source_note"]) for row in derived.maturity_ladder
    )


def test_latest_record_uses_date_key_not_file_order() -> None:
    snapshot = SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id="fred",
            series_id="DPSACBW027SBOG",
            source_url="https://example.test",
            units="millions_of_dollars",
            frequency="weekly",
            transform="level",
            retrieved_at="2026-05-12T00:00:00Z",
        ),
        records=[
            {"date": "1973-01-03", "value": "100"},
            {"date": "2026-05-06", "value": "200"},
        ],
    )

    assert _latest_record(snapshot)["date"] == "2026-05-06"


def test_quarterly_mts_interest_outlays_sum_monthly_flows() -> None:
    snapshot = SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id="treasury_fiscaldata",
            series_id="mts_table_4",
            source_url="https://example.test",
            units="dollars",
            frequency="monthly",
            transform="level",
            retrieved_at="2026-05-12T00:00:00Z",
        ),
        records=[
            {
                "record_date": "2026-01-31",
                "classification_desc": "Total--Interest on the Public Debt",
                "current_month_net_outly_amt": "1000000000",
            },
            {
                "record_date": "2026-02-28",
                "classification_desc": "Total--Interest on the Public Debt",
                "current_month_net_outly_amt": "2000000000",
            },
            {
                "record_date": "2026-03-31",
                "classification_desc": "Total--Interest on the Public Debt",
                "current_month_net_outly_amt": "3000000000",
            },
        ],
    )

    assert _quarterly_mts_interest_outlays(snapshot)["2026Q1"] == Decimal("6")


def _read_output_table(name: str) -> list[dict[str, str]]:
    return list(
        csv.DictReader(
            Path("outputs/tables", name).open(encoding="utf-8", newline="")
        )
    )


SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS = (
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
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
)


def test_conventional_drag_evidence_tranche_selects_first_estimable_row() -> None:
    rows = _read_output_table("ratewall_conventional_drag_evidence_tranche.csv")
    workplan_rows = _read_output_table(
        "ratewall_denominator_evidence_upgrade_tier1_workplan.csv"
    )

    assert len(rows) == len(workplan_rows) * 3
    assert {
        row["claim_boundary"] for row in rows
    } == {"conventional_drag_evidence_tranche_not_prior_narrowing_or_promotion"}
    selected = [
        row
        for row in rows
        if row["priority_selection_status"] == "selected_first_estimable_priority_row"
    ]
    assert {
        (row["source_priority_rank"], row["denominator_component"], row["outcome_series_id"])
        for row in selected
    } == {("2", "conventional_drag_borrowing_cost", "TDSP")}
    assert {row["estimate_available"] for row in selected} == {"true"}
    assert all(row["diagnostic_coefficient"] for row in selected)
    assert all(row["hac_standard_error"] for row in selected)
    assert all(row["mechanical_outcome_change_per_100bp"] for row in selected)
    assert all(
        row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in rows
    )


def test_denominator_tier1_workplan_names_nonconstructible_event_window() -> None:
    panel_rows = _read_output_table(
        "ratewall_denominator_event_outcome_panel_value_diagnostic.csv"
    )
    workplan_rows = _read_output_table(
        "ratewall_denominator_evidence_upgrade_tier1_workplan.csv"
    )
    matrix_rows = _read_output_table(
        "ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv"
    )

    target_panel_rows = [
        row
        for row in panel_rows
        if row["denominator_component"] == "conventional_drag_borrowing_cost"
        and row["horizon_bucket"] == "10y"
        and row["outcome_series_id"] == "BAMLH0A0HYM2"
    ]
    assert len(target_panel_rows) == 3
    assert {row["event_outcome_values_available"] for row in target_panel_rows} == {
        "false"
    }
    assert {
        row["source_specific_evidence_status"].split(";", 1)[0]
        for row in target_panel_rows
    } == {
        "event_outcome_panel_values_not_constructible_from_registered_sources"
    }

    [workplan] = [
        row
        for row in workplan_rows
        if row["tier1_workplan_id"]
        == (
            "denominator_evidence_upgrade_tier1_workplan::"
            "conventional_drag_borrowing_cost::10y::BAMLH0A0HYM2"
        )
    ]
    assert workplan["source_priority_rank"] == "1"
    assert (
        workplan["source_design_execution_status"]
        == "current_source_design_inputs_linked_but_event_outcome_window_support_not_constructible"
    )
    assert (
        "event_outcome_window_support_not_constructible_from_registered_sources"
        in workplan["missing_evidence_contract"]
    )
    assert (
        "complete_or_repair_missing_diagnostic_families=event_outcome_window_support;"
        in workplan["candidate_diagnostic_family_requirement"]
    )
    assert workplan["prior_narrowing_allowed"] == "false"
    assert workplan["split_denominator_promotion_allowed"] == "false"
    assert workplan["formula_replacement_allowed"] == "false"
    assert workplan["raw_rate_shock_enabled"] == "false"

    target_matrix_rows = [
        row
        for row in matrix_rows
        if row["source_tier1_workplan_id"] == workplan["tier1_workplan_id"]
    ]
    assert {
        (
            row["resolution_category"],
            row["blocker_item"],
        )
        for row in target_matrix_rows
    } >= {
        (
            "missing_evidence_contract_item",
            "event_outcome_window_support_not_constructible_from_registered_sources",
        ),
        ("diagnostic_family_repair_item", "event_outcome_window_support"),
    }


def test_denominator_tier1_workplan_carries_tdsp_shorter_horizon_context() -> None:
    workplan_rows = _read_output_table(
        "ratewall_denominator_evidence_upgrade_tier1_workplan.csv"
    )

    [workplan] = [
        row
        for row in workplan_rows
        if row["tier1_workplan_id"]
        == (
            "denominator_evidence_upgrade_tier1_workplan::"
            "conventional_drag_borrowing_cost::10y::TDSP"
        )
    ]
    assert workplan["source_priority_rank"] == "2"
    assert workplan["same_outcome_response_estimate_available_count"] == "8"
    assert (
        workplan["same_outcome_shorter_horizon_available_response_count"] == "8"
    )
    assert (
        workplan["same_outcome_current_horizon_response_status"]
        == "current_horizon_response_estimate_blocked_but_shorter_horizon_diagnostic_responses_available"
    )
    shorter_summary = workplan["same_outcome_shorter_horizon_response_summary"]
    assert (
        "5y/fed_brw_monetary_policy_shocks=coef:3.724829999,n:190"
        in shorter_summary
    )
    assert (
        "5y/sf_fed_monetary_policy_surprises=coef:0.01103886546,n:76"
        in shorter_summary
    )
    assert workplan["prior_narrowing_allowed"] == "false"
    assert workplan["split_denominator_promotion_allowed"] == "false"
    assert workplan["formula_replacement_allowed"] == "false"
    assert workplan["raw_rate_shock_enabled"] == "false"


def test_baml_source_history_repair_contract_fails_closed() -> None:
    rows = _read_output_table("ratewall_baml_source_history_repair_contract.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 4
    by_id = {row["contract_id"]: row for row in rows}
    ten_year = by_id[
        "baml_source_history_repair_contract::"
        "conventional_drag_borrowing_cost::10y::BAMLH0A0HYM2"
    ]
    assert ten_year["decision_rank"] == "1"
    assert (
        ten_year["integrated_external_review_decision"]
        == "repair_direct_baml_history_first_then_use_shorter_horizon_baml_only_as_fail_closed_diagnostic_fallback_keep_tdsp_diagnostic_only"
    )
    assert ten_year["outcome_object_role"] == "credit_spread_oas_diagnostic"
    assert (
        ten_year["object_semantics_status"]
        == "oas_spread_object_not_all_in_borrowing_cost_yield"
    )
    assert (
        ten_year["source_history_status"]
        == "current_baml_history_not_constructible_for_registered_windows"
    )
    assert ten_year["max_constructible_event_outcome_cell_count"] == "0"
    assert (
        ten_year["admission_status"]
        == "blocked_no_constructible_baml_event_outcome_windows"
    )
    assert (
        ten_year["ten_year_transport_status"]
        == "blocked_no_short_horizon_to_10y_transport_contract"
    )
    assert (
        ten_year["tdsp_decision"]
        == "do_not_advance_tdsp_current_demand_mapping_in_this_tranche"
    )

    one_year = by_id[
        "baml_source_history_repair_contract::"
        "conventional_drag_borrowing_cost::1y::BAMLH0A0HYM2"
    ]
    assert (
        one_year["source_history_status"]
        == "current_baml_history_has_short_overlap_but_below_support_floor"
    )
    assert one_year["max_constructible_event_outcome_cell_count"] == "5"
    assert one_year["admission_status"] == "blocked_baml_support_below_minimum_threshold"
    assert "sf_fed_monetary_policy_surprises=5" in one_year[
        "constructible_count_by_shock_source"
    ]

    effective_yield = by_id[
        "baml_source_history_repair_contract::candidate_effective_yield::BAMLH0A0HYM2EY"
    ]
    assert (
        effective_yield["source_history_status"]
        == "blocked_effective_yield_object_not_registered_or_provenanced"
    )
    assert effective_yield["current_source_snapshot_kind"] == "missing"
    assert effective_yield["current_observation_count"] == "0"

    assert {
        row["claim_boundary"] for row in rows
    } == {"baml_source_history_repair_contract_not_prior_narrowing_or_promotion"}
    for field in [
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_baml_source_history_repair_contract.csv"
    ]
    assert (
        active["source_status"]
        == "blocked_baml_source_history_repair_contract_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_borrowing_cost_source_object_adjudication_keeps_baml_blocked() -> None:
    rows = _read_output_table(
        "ratewall_borrowing_cost_source_object_adjudication.csv"
    )
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 9
    by_id = {row["candidate_id"]: row for row in rows}

    public_oas = by_id[
        "borrowing_cost_source_object_adjudication::baml_oas_public_fred"
    ]
    assert public_oas["decision_rank"] == "1"
    assert public_oas["series_or_object_id"] == "BAMLH0A0HYM2"
    assert public_oas["candidate_family"] == "oas_credit_spread"
    assert (
        public_oas["object_semantics"]
        == "oas_spread_object_not_all_in_borrowing_cost_yield"
    )
    assert (
        public_oas["source_history_gate_status"]
        == "blocked_current_public_history_too_short"
    )
    assert public_oas["support_gate_status"] == "blocked_10y_3y_zero_1y_below_floor"
    assert (
        "sf_fed_monetary_policy_surprises=5"
        in public_oas["event_window_support_1y_by_shock"]
    )
    assert public_oas["redistribution_allowed"] == "false"
    assert public_oas["raw_generated_output_allowed"] == "false"

    public_effective_yield = by_id[
        "borrowing_cost_source_object_adjudication::"
        "baml_effective_yield_public_fred"
    ]
    assert public_effective_yield["series_or_object_id"] == "BAMLH0A0HYM2EY"
    assert (
        public_effective_yield["object_semantics"]
        == "all_in_market_yield_candidate_better_semantics_than_oas"
    )
    assert (
        public_effective_yield["support_gate_status"]
        == "not_computed_candidate_not_registered"
    )
    assert public_effective_yield["record_count"] == "0"

    licensed_effective_yield = by_id[
        "borrowing_cost_source_object_adjudication::"
        "licensed_ice_baml_effective_yield"
    ]
    assert licensed_effective_yield["credentialed_fetch_required"] == "true"
    assert (
        licensed_effective_yield["license_status"]
        == "ice_license_required_unconfirmed"
    )
    assert (
        licensed_effective_yield["admissible_use"]
        == "licensed_metadata_only_until_rights_and_support_pass"
    )

    hqm = by_id[
        "borrowing_cost_source_object_adjudication::"
        "treasury_hqm_public_corporate_yield"
    ]
    assert hqm["candidate_family"] == "public_corporate_yield_proxy"
    assert (
        hqm["object_semantics"]
        == "high_quality_corporate_all_in_yield_not_high_yield"
    )
    assert hqm["primary_next_action"] == (
        "register_hqm_proxy_lane_if_public_source_review_passes"
    )
    assert hqm["claim_boundary"] == "hqm_public_proxy_not_baml_or_high_yield"

    baa = by_id[
        "borrowing_cost_source_object_adjudication::"
        "moodys_baa_yield_rights_review"
    ]
    assert baa["series_or_object_id"] == "BAA"
    assert baa["record_count"].isdigit()
    assert int(baa["record_count"]) > 0
    assert baa["frequency"] == "monthly"
    assert baa["source_history_gate_status"] == (
        "source_history_materialized_rights_and_mapping_review_required"
    )
    assert baa["support_gate_status"] == "not_computed_source_history_available"
    assert baa["admissible_use"] == "source_backed_baa_comparator_context_only"
    assert baa["raw_generated_output_allowed"] == (
        "diagnostic_metadata_and_aggregate_rows_only"
    )
    assert baa["primary_next_action"] == (
        "compute_baa_event_window_support_and_mapping_diagnostic"
    )

    ebp = by_id[
        "borrowing_cost_source_object_adjudication::"
        "gz_ebp_credit_supply_diagnostic"
    ]
    assert ebp["candidate_family"] == "credit_supply_premium"
    assert ebp["admissible_use"] == (
        "credit_supply_or_financial_conditions_diagnostic_only"
    )

    tdsp = by_id[
        "borrowing_cost_source_object_adjudication::"
        "tdsp_current_demand_not_replacement"
    ]
    assert tdsp["candidate_family"] == (
        "current_demand_bridge_not_corporate_borrowing_cost"
    )
    assert (
        tdsp["claim_boundary"]
        == "tdsp_not_corporate_borrowing_cost_replacement"
    )

    for field in [
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_borrowing_cost_source_object_adjudication.csv"
    ]
    assert (
        active["source_status"]
        == "blocked_borrowing_cost_source_object_adjudication_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_baml_effective_yield_source_access_gate_fails_closed() -> None:
    rows = _read_output_table("ratewall_baml_effective_yield_source_access_gate.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 6
    by_route = {row["source_route"]: row for row in rows}
    assert set(by_route) == {
        "public_fred_effective_yield_metadata",
        "alfred_vintage_metadata",
        "public_raw_fetch_and_storage_rights",
        "licensed_ice_full_history",
        "source_snapshot_registration_contract",
        "event_window_support_recompute_gate",
    }

    fred = by_route["public_fred_effective_yield_metadata"]
    assert fred["series_or_object_id"] == "BAMLH0A0HYM2EY"
    assert fred["public_window_start"] == "2023-06-05"
    assert fred["public_window_end"] == "2026-06-02"
    assert fred["redistribution_allowed"] == "false"
    assert fred["raw_generated_output_allowed"] == "false"
    assert fred["metadata_only_allowed"] == "true"
    assert fred["admission_status"] == (
        "blocked_public_history_too_short_and_rights_unresolved"
    )

    licensed = by_route["licensed_ice_full_history"]
    assert licensed["credentialed_fetch_required"] == "true"
    assert licensed["public_window_status"] == "not_public_requires_licensed_source"
    assert licensed["admission_status"] == (
        "blocked_pending_license_and_full_history_snapshot"
    )

    registration = by_route["source_snapshot_registration_contract"]
    assert registration["source_snapshot_present_in_ratewall"] == "false"
    assert registration["source_snapshot_observation_count"] == "0"
    assert registration["source_snapshot_hash_required"] == "true"

    recompute = by_route["event_window_support_recompute_gate"]
    assert recompute["support_recompute_required"] == "true"
    assert recompute["admission_status"] == (
        "blocked_until_registered_event_window_support_passes"
    )

    assert {row["claim_boundary"] for row in rows} == {
        "baml_effective_yield_source_access_gate_not_registration_or_"
        "denominator_promotion"
    }
    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_baml_effective_yield_source_access_gate.csv"
    ]
    assert active["active_status"] == "blocked_source_access_gate"
    assert active["source_status"] == (
        "blocked_baml_effective_yield_source_access_gate_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_hqm_source_proxy_lane_review_is_public_proxy_only() -> None:
    rows = _read_output_table("ratewall_hqm_source_proxy_lane_review.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 2
    by_id = {row["source_candidate_id"]: row for row in rows}

    par = by_id["TREASURY_HQM_EOM_10Y_PAR"]
    assert par["source_owner"] == "US_Treasury"
    assert (
        par["official_source_status"]
        == "official_public_treasury_source_page_reviewed"
    )
    assert par["public_access_status"] == "public_official_no_credentials_required"
    assert par["credentialed_fetch_required"] == "false"
    assert (
        par["object_semantics"]
        == "high_quality_corporate_all_in_10y_eom_par_yield_proxy_not_high_yield"
    )
    assert (
        par["source_materialization_status"]
        == "materialized_official_treasury_hqm_eom_10y_par_snapshot_available;"
        "record_count=508"
    )
    assert par["source_range_start"] == "1984-01-31"
    assert par["source_range_end"] == "2026-04-30"
    assert (
        par["event_window_feasibility_artifact"]
        == "ratewall_hqm_event_window_feasibility.csv"
    )

    spot = by_id["treasury_hqm_spot_rate_curve_1984_2028"]
    assert spot["source_range_end"] == "2028_file_block_on_official_source_page"
    assert (
        spot["object_semantics"]
        == "high_quality_corporate_spot_rate_curve_proxy_not_high_yield"
    )

    for field in [
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_hqm_source_proxy_lane_review.csv"
    ]
    assert active["source_status"] == "blocked_hqm_source_proxy_lane_review_indexed"
    assert active["canonical_ratio_entry"] == "false"


def test_hqm_event_window_feasibility_is_support_only() -> None:
    rows = _read_output_table("ratewall_hqm_event_window_feasibility.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 9
    assert {row["source_candidate_id"] for row in rows} == {
        "TREASURY_HQM_EOM_10Y_PAR"
    }
    assert {row["candidate_source_start_date"] for row in rows} == {"1984-01-31"}
    assert {row["candidate_source_end_date"] for row in rows} == {"2026-04-30"}
    assert {row["horizon_bucket"] for row in rows} == {"10y", "3y", "1y"}
    assert {row["support_count_status"] for row in rows} == {
        "minimum_support_count_met_not_estimation_ready"
    }
    ten_year_counts = {
        row["shock_source_id"]: row["constructible_event_outcome_cell_count"]
        for row in rows
        if row["horizon_bucket"] == "10y"
    }
    assert ten_year_counts == {
        "fed_brw_monetary_policy_shocks": "268",
        "romer_romer_2004": "155",
        "sf_fed_monetary_policy_surprises": "35",
    }
    assert all(
        int(row["constructible_event_outcome_cell_count"])
        >= int(row["minimum_support_threshold"])
        for row in rows
    )
    assert {row["source_range_feasibility_status"] for row in rows} == {
        "observed_hqm_monthly_values_support_only_no_response_estimate"
    }
    assert {row["cell_construction_status"] for row in rows} == {
        "not_constructed_observed_support_count_only"
    }
    assert {row["response_estimate_available"] for row in rows} == {"false"}
    assert {row["support_diagnostics_available"] for row in rows} == {"true"}
    assert {row["pretrend_placebo_required"] for row in rows} == {"true"}

    for field in [
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_hqm_event_window_feasibility.csv"
    ]
    assert active["source_status"] == "blocked_hqm_event_window_feasibility_indexed"
    assert active["canonical_ratio_entry"] == "false"


def test_hqm_event_outcome_panel_values_are_observed_only() -> None:
    rows = _read_output_table("ratewall_hqm_event_outcome_panel_values.csv")
    feasibility_rows = _read_output_table("ratewall_hqm_event_window_feasibility.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    expected_count = sum(
        int(row["constructible_event_outcome_cell_count"])
        for row in feasibility_rows
    )
    assert len(rows) == expected_count == 1614
    group_counts = Counter(
        (row["shock_source_id"], row["horizon_bucket"]) for row in rows
    )
    assert group_counts[("fed_brw_monetary_policy_shocks", "10y")] == 268
    assert group_counts[("romer_romer_2004", "10y")] == 155
    assert group_counts[("sf_fed_monetary_policy_surprises", "10y")] == 35
    assert {row["source_candidate_id"] for row in rows} == {
        "TREASURY_HQM_EOM_10Y_PAR"
    }
    assert {row["outcome_change_unit"] for row in rows} == {
        "level_change_points_or_index_units"
    }
    assert {row["baseline_support_status"] for row in rows} == {
        "observed_baseline_value_available"
    }
    assert {row["future_window_support_status"] for row in rows} == {
        "observed_future_window_value_available"
    }
    assert {row["event_outcome_panel_value_status"] for row in rows} == {
        "observed_hqm_event_outcome_values_constructed_not_response_estimate"
    }
    first = rows[0]
    assert first["event_date"] == "1994-01-01"
    assert first["baseline_outcome_date"] == "1993-12-31"
    assert first["baseline_outcome_value"] == "6.42"
    assert first["future_outcome_date"] == "2004-01-31"
    assert first["future_outcome_value"] == "4.95"
    assert first["raw_outcome_change"] == "-1.47"

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_hqm_event_outcome_panel_values.csv"
    ]
    assert (
        active["source_status"]
        == "blocked_hqm_event_outcome_panel_values_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_hqm_formal_diagnostic_gate_blocks_prior_movement() -> None:
    rows = _read_output_table("ratewall_hqm_formal_diagnostic_gate.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 9
    assert {row["source_candidate_id"] for row in rows} == {
        "TREASURY_HQM_EOM_10Y_PAR"
    }
    ten_year_counts = {
        row["shock_source_id"]: row["panel_value_row_count"]
        for row in rows
        if row["horizon_bucket"] == "10y"
    }
    assert ten_year_counts == {
        "fed_brw_monetary_policy_shocks": "268",
        "romer_romer_2004": "155",
        "sf_fed_monetary_policy_surprises": "35",
    }
    assert {row["response_ols_available"] for row in rows} == {"true"}
    assert {row["outlier_trimmed_ols_available"] for row in rows} == {"true"}
    assert {row["formal_diagnostic_gate_status"] for row in rows} == {
        "blocked_diagnostics_available_not_promotion_grade"
    }
    assert all(row["same_shock_horizon_coefficients"] for row in rows)
    assert {
        row["shock_relevance_status"] for row in rows
    } == {"diagnostic_nonzero_shock_variance_available_not_identification_grade"}
    assert all(
        row["sign_check_status"].endswith("_not_promotion_grade")
        for row in rows
    )

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_hqm_formal_diagnostic_gate.csv"
    ]
    assert active["source_status"] == "blocked_hqm_formal_diagnostic_gate_indexed"
    assert active["canonical_ratio_entry"] == "false"


def test_hqm_public_fallback_response_result_reports_existing_coefficients() -> None:
    rows = _read_output_table("ratewall_hqm_public_fallback_response_result.csv")
    formal_rows = _read_output_table("ratewall_hqm_formal_diagnostic_gate.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 9
    assert {row["source_candidate_id"] for row in rows} == {
        "TREASURY_HQM_EOM_10Y_PAR"
    }
    assert {row["fallback_object_label"] for row in rows} == {
        "Treasury HQM 10-year high-quality corporate par yield"
    }
    assert {row["ice_baml_acquisition_status"] for row in rows} == {
        "external_ice_acquisition_sprint_submitted_pending_response"
    }
    assert {row["fallback_result_status"] for row in rows} == {
        "computed_public_hqm_fallback_response_result_not_baml_high_yield_not_denominator_admission"
    }
    assert {row["admissible_use"] for row in rows} == {
        "public_hqm_fallback_model_interpretation_and_substitute_comparison_only"
    }
    assert {row["claim_boundary"] for row in rows} == {
        "hqm_public_fallback_result_supports_high_grade_corporate_yield_conditions_not_high_yield_effective_borrowing_cost"
    }

    by_key = {
        (row["shock_source_id"], row["horizon_bucket"]): row
        for row in formal_rows
    }
    for row in rows:
        formal = by_key[(row["shock_source_id"], row["horizon_bucket"])]
        for field in [
            "horizon_months",
            "panel_value_row_count",
            "response_coefficient",
            "response_hac_standard_error",
            "response_p_value_normal_approx",
            "response_ci_95_lower",
            "response_ci_95_upper",
            "response_r_squared",
            "same_shock_horizon_coefficients",
            "pretrend_placebo_status",
            "outlier_window_robustness_status",
        ]:
            assert row[field] == formal[field]

    by_shock_horizon = {
        (row["shock_source_id"], row["horizon_bucket"]): row for row in rows
    }
    assert (
        by_shock_horizon[
            ("fed_brw_monetary_policy_shocks", "3y")
        ]["response_coefficient"]
        == "3.665970326"
    )
    assert (
        by_shock_horizon[
            ("fed_brw_monetary_policy_shocks", "3y")
        ]["response_sign"]
        == "positive_yield_response_to_tightening_shock"
    )
    assert (
        by_shock_horizon[
            ("sf_fed_monetary_policy_surprises", "10y")
        ]["response_sign"]
        == "negative_yield_response_to_tightening_shock"
    )

    for field in [
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
        "reset_calendar_construction_enabled",
        "causal_financialization_claim_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_hqm_public_fallback_response_result.csv"
    ]
    assert (
        active["source_status"]
        == "active_hqm_public_fallback_response_result_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"
    assert active["paper_use"] == "fallback_context_only"


def test_hqm_promotion_protocol_gate_encodes_external_review_decision() -> None:
    rows = _read_output_table("ratewall_hqm_promotion_protocol_gate.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 5
    by_stage = {row["promotion_stage"]: row for row in rows}
    assert by_stage["source_proxy"]["stage_status"] == (
        "passed_nonpromotional_source_proxy"
    )
    assert by_stage["observed_panel"]["stage_status"] == (
        "passed_nonpromotional_observed_panel"
    )
    assert by_stage["diagnostic_response"]["stage_status"] == (
        "blocked_partial_diagnostic_response_not_pass_fail"
    )
    assert by_stage["denominator_evidence"]["stage_status"] == (
        "blocked_no_denominator_object_mapping"
    )
    assert by_stage["current_demand_denominator"]["stage_status"] == (
        "blocked_no_current_demand_bridge"
    )
    assert by_stage["observed_panel"]["current_result"].startswith(
        "passed_panel_rows=1614"
    )
    assert {row["promotion_allowed"] for row in rows} == {"false"}

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_hqm_promotion_protocol_gate.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert active["source_status"] == "blocked_hqm_promotion_protocol_gate_indexed"
    assert active["canonical_ratio_entry"] == "false"


def test_hqm_policy_path_exposure_admission_blocks_scalar_shocks() -> None:
    rows = _read_output_table("ratewall_hqm_policy_path_exposure_admission.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 3
    assert {row["shock_source_id"] for row in rows} == {
        "fed_brw_monetary_policy_shocks",
        "romer_romer_2004",
        "sf_fed_monetary_policy_surprises",
    }
    assert {row["path_vector_available"] for row in rows} == {"false"}
    assert {row["admission_status"] for row in rows} == {
        "blocked_scalar_shock_not_policy_path_exposure_vector"
    }
    assert {row["exposure_bps_year_0_10y"] for row in rows} == {""}

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_hqm_policy_path_exposure_admission.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert (
        active["source_status"]
        == "blocked_hqm_policy_path_exposure_admission_indexed"
    )


def test_hqm_policy_path_protocol_dependency_gate_links_global_blockers() -> None:
    rows = _read_output_table("ratewall_hqm_policy_path_protocol_dependency_gate.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 3
    assert {row["source_candidate_id"] for row in rows} == {
        "TREASURY_HQM_EOM_10Y_PAR"
    }
    assert {row["shock_source_id"] for row in rows} == {
        "fed_brw_monetary_policy_shocks",
        "romer_romer_2004",
        "sf_fed_monetary_policy_surprises",
    }
    assert {row["global_full_protocol_id"] for row in rows} == {
        "policy_path_bps_year_full_protocol"
    }
    assert {row["global_full_protocol_admission_status"] for row in rows} == {
        "blocked_full_policy_path_protocol_not_admitted"
    }
    assert {row["blocked_component_count"] for row in rows} == {"0"}
    assert {row["blocked_component_ids"] for row in rows} == {""}
    assert {row["hqm_path_dependency_status"] for row in rows} == {
        "blocked_hqm_path_dependency_requires_explicit_rebuild_review"
    }
    assert {row["admission_status"] for row in rows} == {
        "blocked_hqm_policy_path_dependency_not_admitted"
    }
    assert {row["matched_source_family"] for row in rows} == {
        "usmpd_event_study_database"
    }
    assert {row["candidate_bps_year_exposure"] for row in rows} == {""}

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_hqm_policy_path_protocol_dependency_gate.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert active["source_status"] == (
        "blocked_hqm_policy_path_protocol_dependency_gate_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_hqm_mapping_and_current_demand_gates_block_overclaim() -> None:
    mapping_rows = _read_output_table("ratewall_hqm_denominator_mapping_gate.csv")
    bridge_rows = _read_output_table("ratewall_hqm_current_demand_bridge_gate.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(mapping_rows) == 3
    assert {row["maturity_years"] for row in mapping_rows} == {"10"}
    assert {row["response_horizon_months"] for row in mapping_rows} == {
        "12",
        "36",
        "120",
    }
    assert {row["all_in_yield_object"] for row in mapping_rows} == {"true"}
    assert {row["high_yield_object"] for row in mapping_rows} == {"false"}
    assert {row["credit_spread_object"] for row in mapping_rows} == {"false"}
    assert {row["mapping_status"] for row in mapping_rows} == {
        "passed_high_quality_proxy_blocked_denominator_promotion"
    }
    assert all("high_yield_equivalence" in row["impossible_claims"] for row in mapping_rows)

    assert len(bridge_rows) == 7
    bridge_by_id = {row["bridge_id"]: row for row in bridge_rows}
    assert set(bridge_by_id) == {
        "hqm_current_demand_bridge_gate::internal_hqm_diagnostics",
        "hqm_current_demand_bridge_gate::policy_path_100bp_year_dependency",
        "hqm_current_demand_bridge_gate::frbus_or_external_macro_model",
        "hqm_current_demand_bridge_gate::tdsp_household_proxy",
        "hqm_current_demand_bridge_gate::baa_yield_proxy_context",
        "hqm_current_demand_bridge_gate::macro_activity_controls",
        "hqm_current_demand_bridge_gate::final_recipient_context",
    }
    assert bridge_by_id[
        "hqm_current_demand_bridge_gate::internal_hqm_diagnostics"
    ]["bridge_status"] == (
        "blocked_internal_hqm_diagnostics_not_current_demand_bridge"
    )
    assert bridge_by_id[
        "hqm_current_demand_bridge_gate::frbus_or_external_macro_model"
    ]["bridge_status"] == "blocked_no_independent_current_demand_bridge_source"
    assert bridge_by_id["hqm_current_demand_bridge_gate::tdsp_household_proxy"][
        "candidate_source_row_count"
    ] == "84"
    assert bridge_by_id[
        "hqm_current_demand_bridge_gate::policy_path_100bp_year_dependency"
    ]["candidate_source_row_count"] == "3"
    assert bridge_by_id[
        "hqm_current_demand_bridge_gate::frbus_or_external_macro_model"
    ]["local_context_available"] == "false"
    assert bridge_by_id[
        "hqm_current_demand_bridge_gate::final_recipient_context"
    ]["local_context_available"] == "false"
    assert {row["independence_from_ratewall"] for row in bridge_rows} == {"false"}
    assert {row["model_run_replicated"] for row in bridge_rows} == {"false"}
    assert {row["uncertainty_interval_available"] for row in bridge_rows} == {"false"}
    assert {
        row["source_backed_current_demand_conversion_available"]
        for row in bridge_rows
    } == {"false"}
    assert {row["timing_mapping_available"] for row in bridge_rows} == {"false"}
    assert {row["nonadditivity_check_available"] for row in bridge_rows} == {"false"}

    for rows in [mapping_rows, bridge_rows]:
        for field in [
            "response_estimate_available",
            "promotion_gate_passed",
            "enters_main_ratio",
            "evidence_mode_enabled",
            "canonical_ratio_entry",
            "prior_narrowing_allowed",
            "split_denominator_promotion_allowed",
            "formula_replacement_allowed",
            "pricing_output_enabled",
            "incidence_claim_enabled",
            "welfare_claim_enabled",
            "tax_output_enabled",
            "mpc_output_enabled",
            "holder_allocation_enabled",
            "raw_rate_shock_enabled",
        ]:
            assert {row[field] for row in rows} == {"false"}

    active_by_path = {row["artifact_path"]: row for row in active_rows}
    for path, status in {
        "outputs/tables/ratewall_hqm_denominator_mapping_gate.csv": (
            "blocked_hqm_denominator_mapping_gate_indexed"
        ),
        "outputs/tables/ratewall_hqm_current_demand_bridge_gate.csv": (
            "blocked_hqm_current_demand_bridge_gate_indexed"
        ),
    }.items():
        active = active_by_path[path]
        assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
        assert active["source_status"] == status
        assert active["canonical_ratio_entry"] == "false"


def test_hqm_borrowing_cost_object_comparator_quantifies_mapping_blocker() -> None:
    rows = _read_output_table("ratewall_hqm_borrowing_cost_object_comparator.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 3
    by_series = {row["comparator_series_id"]: row for row in rows}

    baml_oas = by_series["BAMLH0A0HYM2"]
    assert baml_oas["source_candidate_snapshot_kind"] == "live_official_workbook"
    assert baml_oas["comparator_snapshot_kind"] == "live"
    assert baml_oas["alignment_rule"] == (
        "same_calendar_month_last_numeric_observation_for_each_series"
    )
    assert int(baml_oas["overlap_observation_count"]) > 0
    assert baml_oas["overlap_first_month"] == "2023-05"
    assert baml_oas["comparator_availability_status"] == (
        "comparator_source_snapshot_available_with_overlap"
    )
    assert baml_oas["object_mapping_status"] == (
        "blocked_oas_credit_spread_not_all_in_effective_yield_and_hqm_"
        "high_quality_not_high_yield"
    )
    assert baml_oas["pearson_correlation"]
    assert baml_oas["admission_status"] == (
        "blocked_quantified_comparator_not_denominator_promotion"
    )

    effective_yield = by_series["BAMLH0A0HYM2EY"]
    assert effective_yield["comparator_snapshot_kind"] == "missing"
    assert effective_yield["overlap_observation_count"] == "0"
    assert effective_yield["comparator_availability_status"] == (
        "blocked_comparator_source_snapshot_missing"
    )
    assert effective_yield["object_mapping_status"] == (
        "blocked_effective_yield_object_not_registered_in_current_snapshot"
    )

    baa = by_series["BAA"]
    assert baa["comparator_snapshot_kind"] == "live"
    assert baa["comparator_source_owner"] == "Moodys_via_FRED"
    assert baa["comparator_frequency"] == "monthly"
    assert int(baa["comparator_observation_count"]) > 0
    assert int(baa["overlap_observation_count"]) > 0
    assert baa["comparator_availability_status"] == (
        "comparator_source_snapshot_available_with_overlap"
    )
    assert baa["object_mapping_status"] == (
        "source_backed_baa_comparator_available_mapping_still_blocked_"
        "pending_proxy_uncertainty"
    )
    assert baa["admission_status"] == (
        "blocked_quantified_comparator_not_denominator_promotion"
    )

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_hqm_borrowing_cost_object_comparator.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert active["source_status"] == (
        "blocked_hqm_borrowing_cost_object_comparator_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_baa_event_window_support_diagnostic_counts_support_without_promotion() -> None:
    rows = _read_output_table("ratewall_baa_event_window_support_diagnostic.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 9
    assert {row["comparator_series_id"] for row in rows} == {"BAA"}
    assert {row["comparator_snapshot_kind"] for row in rows} == {"live"}
    assert {row["comparator_frequency"] for row in rows} == {"monthly"}
    assert {row["minimum_support_threshold"] for row in rows} == {"30"}
    assert all(int(row["comparator_observation_count"]) == 1289 for row in rows)
    by_shock = {}
    for row in rows:
        by_shock.setdefault(row["shock_source_id"], []).append(row)
    assert all(
        int(row["constructible_event_window_count"]) >= 30
        for row in by_shock["fed_brw_monetary_policy_shocks"]
    )
    assert all(
        int(row["constructible_event_window_count"]) >= 30
        for row in by_shock["sf_fed_monetary_policy_surprises"]
    )
    assert {row["constructible_event_window_count"] for row in by_shock["romer_romer_2004"]} == {
        "0"
    }
    assert {row["support_count_status"] for row in by_shock["romer_romer_2004"]} == {
        "blocked_support_below_minimum"
    }
    assert {row["admission_status"] for row in rows} == {
        "blocked_support_diagnostic_not_denominator_promotion"
    }
    assert {row["claim_boundary"] for row in rows} == {
        "baa_event_window_support_diagnostic_not_denominator_promotion"
    }

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_baa_event_window_support_diagnostic.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert active["source_status"] == (
        "blocked_baa_event_window_support_diagnostic_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_baa_hqm_mapping_diagnostic_quantifies_stability_without_promotion() -> None:
    rows = _read_output_table("ratewall_baa_hqm_mapping_diagnostic.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 5
    by_window = {row["window_label"]: row for row in rows}
    assert set(by_window) == {
        "full_overlap",
        "pre_2000",
        "2000_2009",
        "2010_2019",
        "2020_present",
    }
    full = by_window["full_overlap"]
    assert full["source_candidate_id"] == "TREASURY_HQM_EOM_10Y_PAR"
    assert full["comparator_series_id"] == "BAA"
    assert full["overlap_observation_count"] == "508"
    assert full["window_start_month"] == "1984-01"
    assert full["window_end_month"] == "2026-04"
    assert full["pearson_correlation"]
    assert full["ols_hqm_on_baa_available"] == "true"
    assert full["mapping_stability_status"] == (
        "diagnostic_mapping_statistics_available_not_promotion_grade"
    )
    assert {row["admission_status"] for row in rows} == {
        "blocked_mapping_diagnostic_not_denominator_promotion"
    }
    assert {row["claim_boundary"] for row in rows} == {
        "baa_hqm_mapping_diagnostic_not_denominator_promotion"
    }

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_baa_hqm_mapping_diagnostic.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert active["source_status"] == "blocked_baa_hqm_mapping_diagnostic_indexed"
    assert active["canonical_ratio_entry"] == "false"


def test_baa_response_diagnostic_runs_only_as_nonpromotional_sidecar() -> None:
    rows = _read_output_table("ratewall_baa_response_diagnostic.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 9
    by_shock = {}
    for row in rows:
        by_shock.setdefault(row["shock_source_id"], []).append(row)
    assert set(by_shock) == {
        "fed_brw_monetary_policy_shocks",
        "romer_romer_2004",
        "sf_fed_monetary_policy_surprises",
    }
    assert {
        row["response_ols_available"]
        for row in by_shock["fed_brw_monetary_policy_shocks"]
    } == {"true"}
    assert {
        row["response_ols_available"]
        for row in by_shock["sf_fed_monetary_policy_surprises"]
    } == {"true"}
    assert {
        row["response_ols_available"]
        for row in by_shock["romer_romer_2004"]
    } == {"false"}
    assert {
        row["support_count_status"] for row in by_shock["romer_romer_2004"]
    } == {"blocked_support_below_minimum_response_not_run"}
    assert {
        row["response_diagnostic_status"]
        for row in by_shock["romer_romer_2004"]
    } == {"blocked_no_response_diagnostic_support_below_minimum"}
    assert {row["admission_status"] for row in rows} == {
        "blocked_response_diagnostic_not_denominator_promotion"
    }
    assert {row["claim_boundary"] for row in rows} == {
        "baa_response_diagnostic_not_denominator_estimate_or_promotion"
    }
    assert {row["current_demand_bridge_status"] for row in rows} == {
        "blocked_no_baa_to_current_demand_bridge"
    }

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"] == "outputs/tables/ratewall_baa_response_diagnostic.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert active["source_status"] == "blocked_baa_response_diagnostic_indexed"
    assert active["canonical_ratio_entry"] == "false"


def test_baa_policy_path_normalization_gate_blocks_mechanical_scaling() -> None:
    rows = _read_output_table("ratewall_baa_policy_path_normalization_gate.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 9
    by_key = {
        (row["shock_source_id"], row["horizon_bucket"]): row for row in rows
    }
    brw_10y = by_key[("fed_brw_monetary_policy_shocks", "10y")]
    assert brw_10y["shock_unit_basis"] == "percentage_points"
    assert brw_10y["mechanical_baa_yield_change_per_100bp_shock"] == "2.545162"
    assert brw_10y["mechanical_100bp_shock_scaling_status"] == (
        "mechanical_percentage_point_shock_equals_100bp_shock"
    )
    sf_10y = by_key[("sf_fed_monetary_policy_surprises", "10y")]
    assert sf_10y["shock_unit_basis"] == "basis_points"
    assert sf_10y["mechanical_baa_yield_change_per_100bp_shock"] == "-0.126369"
    assert sf_10y["mechanical_100bp_shock_scaling_status"] == (
        "mechanical_basis_point_shock_scaled_by_100"
    )
    rr_10y = by_key[("romer_romer_2004", "10y")]
    assert rr_10y["response_ols_available"] == "false"
    assert rr_10y["mechanical_baa_yield_change_per_100bp_shock"] == ""
    assert rr_10y["normalization_gate_status"] == (
        "blocked_no_response_diagnostic_to_normalize"
    )
    assert {row["policy_path_100bp_year_normalization_status"] for row in rows} == {
        "blocked_event_shock_not_reviewed_as_100bp_year_policy_path",
        "blocked_response_unavailable",
    }
    assert {row["current_demand_bridge_status"] for row in rows} == {
        "blocked_no_baa_yield_response_to_current_demand_bridge"
    }
    assert {row["admission_status"] for row in rows} == {
        "blocked_policy_path_normalization_not_denominator_promotion"
    }
    assert {row["claim_boundary"] for row in rows} == {
        "baa_policy_path_normalization_gate_not_denominator_or_current_demand_promotion"
    }

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_baa_policy_path_normalization_gate.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert active["source_status"] == (
        "blocked_baa_policy_path_normalization_gate_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_baa_rights_proxy_uncertainty_review_blocks_promotion() -> None:
    rows = _read_output_table("ratewall_baa_rights_proxy_uncertainty_review.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 5
    by_dimension = {row["review_dimension"]: row for row in rows}
    assert set(by_dimension) == {
        "source_history_available_rights_unresolved",
        "proxy_semantics_baa_not_ratewall_denominator_object",
        "hqm_mapping_level_gap_uncertainty",
        "response_and_policy_path_uncertainty",
        "current_demand_conversion_missing",
    }

    source_row = by_dimension["source_history_available_rights_unresolved"]
    assert source_row["comparator_series_id"] == "BAA"
    assert source_row["source_owner"] == "Moodys_via_FRED"
    assert source_row["source_snapshot_kind"] == "live"
    assert source_row["source_frequency"] == "monthly"
    assert source_row["source_observation_count"] == "1289"
    assert source_row["source_first_observation_date"] == "1919-01-01"
    assert source_row["source_last_observation_date"] == "2026-05-01"
    assert source_row["hqm_overlap_observation_count"] == "508"
    assert source_row["hqm_baa_pearson_correlation"] == "0.989105"
    assert source_row["hqm_minus_baa_mean"] == "-1.103976"
    assert source_row["response_diagnostic_available_rows"] == "6"
    assert source_row["mechanical_scaling_available_rows"] == "6"
    assert source_row["rights_review_status"] == (
        "blocked_moodys_fred_rights_and_redistribution_terms_not_"
        "promotion_reviewed"
    )

    assert by_dimension["proxy_semantics_baa_not_ratewall_denominator_object"][
        "proxy_semantics_status"
    ] == (
        "blocked_seasoned_baa_long_maturity_corporate_yield_not_direct_"
        "ratewall_borrowing_cost_denominator"
    )
    assert by_dimension["hqm_mapping_level_gap_uncertainty"][
        "mapping_uncertainty_status"
    ] == "blocked_high_correlation_with_systematic_level_gap_not_denominator_map"
    assert by_dimension["response_and_policy_path_uncertainty"][
        "policy_path_status"
    ] == "blocked_mechanical_100bp_shock_scaling_not_100bp_year_policy_path"
    assert by_dimension["current_demand_conversion_missing"][
        "current_demand_bridge_status"
    ] == (
        "blocked_no_independent_baa_yield_to_current_demand_or_gdp_"
        "share_drag_bridge"
    )
    assert {row["admission_status"] for row in rows} == {
        "blocked_baa_rights_proxy_uncertainty_not_denominator_promotion"
    }
    assert {row["claim_boundary"] for row in rows} == {
        "baa_rights_proxy_uncertainty_review_not_denominator_or_"
        "current_demand_promotion"
    }

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_baa_rights_proxy_uncertainty_review.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert active["source_status"] == (
        "blocked_baa_rights_proxy_uncertainty_review_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_baa_current_demand_bridge_source_audit_blocks_conversion() -> None:
    rows = _read_output_table("ratewall_baa_current_demand_bridge_source_audit.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 5
    by_route = {row["candidate_bridge_route"]: row for row in rows}
    assert set(by_route) == {
        "internal_baa_response_diagnostic",
        "frbus_or_published_macro_model_bridge",
        "tdsp_household_current_demand_proxy",
        "macro_activity_correlation_proxy",
        "final_recipient_current_demand_bridge_context",
    }
    internal = by_route["internal_baa_response_diagnostic"]
    assert internal["baa_response_diagnostic_available_rows"] == "6"
    assert internal["baa_mechanical_scaling_available_rows"] == "6"
    assert internal["baa_rights_proxy_blocked_rows"] == "5"
    assert internal["bridge_evidence_status"] == (
        "blocked_internal_response_and_mechanical_scaling_not_current_"
        "demand_conversion"
    )
    assert by_route["frbus_or_published_macro_model_bridge"][
        "candidate_source_row_count"
    ] == "0"
    assert by_route["tdsp_household_current_demand_proxy"][
        "bridge_evidence_status"
    ] == (
        "blocked_tdsp_household_debt_service_not_baa_corporate_yield_"
        "to_current_demand_bridge"
    )
    assert by_route["macro_activity_correlation_proxy"][
        "bridge_evidence_status"
    ] == (
        "blocked_macro_activity_series_are_outcomes_or_controls_not_"
        "baa_yield_to_current_demand_conversion"
    )
    assert by_route["final_recipient_current_demand_bridge_context"][
        "bridge_evidence_status"
    ] == (
        "blocked_final_recipient_context_does_not_map_baa_corporate_"
        "yield_response_to_current_demand"
    )
    assert {row["independent_bridge_source_available"] for row in rows} == {"false"}
    assert {row["source_backed_current_demand_conversion_available"] for row in rows} == {
        "false"
    }
    assert {row["bridge_admission_status"] for row in rows} == {
        "blocked_no_baa_current_demand_bridge_source_admitted"
    }
    assert {row["claim_boundary"] for row in rows} == {
        "baa_current_demand_bridge_source_audit_not_current_demand_"
        "or_denominator_promotion"
    }

    for field in [
        "response_estimate_available",
        "promotion_gate_passed",
        "enters_main_ratio",
        "evidence_mode_enabled",
        "canonical_ratio_entry",
        "prior_narrowing_allowed",
        "split_denominator_promotion_allowed",
        "formula_replacement_allowed",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "raw_rate_shock_enabled",
    ]:
        assert {row[field] for row in rows} == {"false"}

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_baa_current_demand_bridge_source_audit.csv"
    ]
    assert active["active_status"] == "active_diagnostic_sidecar_fail_closed"
    assert active["source_status"] == (
        "blocked_baa_current_demand_bridge_source_audit_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"


def test_baml_hqm_denominator_repair_bundle_is_released_fail_closed() -> None:
    expected_paths = {
        "outputs/tables/ratewall_baml_source_history_repair_contract.csv",
        "outputs/tables/ratewall_borrowing_cost_source_object_adjudication.csv",
        "outputs/tables/ratewall_baml_effective_yield_source_access_gate.csv",
        "outputs/tables/ratewall_hqm_source_proxy_lane_review.csv",
        "outputs/tables/ratewall_hqm_event_window_feasibility.csv",
        "outputs/tables/ratewall_hqm_event_outcome_panel_values.csv",
        "outputs/tables/ratewall_hqm_formal_diagnostic_gate.csv",
        "outputs/tables/ratewall_hqm_promotion_protocol_gate.csv",
        "outputs/tables/ratewall_hqm_policy_path_exposure_admission.csv",
        "outputs/tables/ratewall_hqm_policy_path_protocol_dependency_gate.csv",
        "outputs/tables/ratewall_hqm_denominator_mapping_gate.csv",
        "outputs/tables/ratewall_hqm_borrowing_cost_object_comparator.csv",
        "outputs/tables/ratewall_baa_event_window_support_diagnostic.csv",
        "outputs/tables/ratewall_baa_hqm_mapping_diagnostic.csv",
        "outputs/tables/ratewall_baa_response_diagnostic.csv",
        "outputs/tables/ratewall_baa_policy_path_normalization_gate.csv",
        "outputs/tables/ratewall_baa_rights_proxy_uncertainty_review.csv",
        "outputs/tables/ratewall_baa_current_demand_bridge_source_audit.csv",
        "outputs/tables/ratewall_hqm_current_demand_bridge_gate.csv",
    }
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    table_plate = Path("outputs/reports/ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )

    assert expected_paths <= set(release_manifest["artifact_layers"]["assumption_mode"])
    assert all(Path(path).name in table_plate for path in expected_paths)

    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_paths <= set(archive.namelist())

    context_rows = _read_output_table("ratewall_context_surface_no_main_ratio_audit.csv")
    context_by_artifact = {row["artifact_name"]: row for row in context_rows}
    for path in expected_paths:
        row = context_by_artifact[Path(path).name]
        assert row["release_manifest_verified"] == "true"
        assert row["readme_verified"] == "true"
        assert row["table_plate_verified"] == "true"
        assert row["source_archive_verified"] == "true"
        assert row["outside_canonical_denominator"] == "true"
        assert row["evidence_mode_promotion_surface"] == "false"
        assert row["forbidden_switches_disabled"] == "true"
        assert row["materialization_contract_status"] == "pass"
        assert row["audit_status"] == "pass"


def test_conventional_drag_demand_conversion_admission_fails_closed() -> None:
    tranche_rows = _read_output_table("ratewall_conventional_drag_evidence_tranche.csv")
    workplan_rows = _read_output_table(
        "ratewall_denominator_evidence_upgrade_tier1_workplan.csv"
    )
    rows = _read_output_table(
        "ratewall_conventional_drag_demand_conversion_admission.csv"
    )

    assert len(rows) == len(tranche_rows) == len(workplan_rows) * 3
    assert {
        row["claim_boundary"] for row in rows
    } == {"conventional_drag_demand_conversion_admission_not_prior_narrowing_or_promotion"}
    assert all(int(row["source_backing_ledger_row_count"]) > 0 for row in rows)
    assert {
        (
            row["source_priority_rank"],
            row["outcome_series_id"],
            row["conversion_admission_status"],
        )
        for row in rows
        if row["estimate_available"] == "true"
    } == {
        ("2", "TDSP", "blocked_diagnostic_tdsp_estimate_not_demand_drag"),
    }
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["demand_drag_conversion_candidate_available"] == "false"
        and row["denominator_prior_update_allowed"] == "false"
        and row["empirical_threshold_claim_enabled"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in rows
    )


def test_conventional_drag_calibration_route_fails_closed() -> None:
    tranche_rows = _read_output_table("ratewall_conventional_drag_evidence_tranche.csv")
    conversion_rows = _read_output_table(
        "ratewall_conventional_drag_demand_conversion_admission.csv"
    )
    refresh_rows = _read_output_table(
        "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv"
    )
    route_rows = _read_output_table("ratewall_conventional_drag_calibration_route.csv")
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(route_rows) == len(tranche_rows) + 3 == len(conversion_rows) + 3
    assert {
        row["claim_boundary"] for row in route_rows
    } == {"conventional_drag_calibration_route_not_prior_narrowing_or_promotion"}
    assert {row["selected_calibration_route_decision"] for row in route_rows} == {
        "blocked_no_admissible_calibration_route"
    }
    assert {row["admissible_calibration_route_available"] for row in route_rows} == {
        "false"
    }
    assert {row["calibration_route_admission_status"] for row in route_rows} == {
        "blocked_fail_closed_no_route_admitted"
    }
    assert {
        row["research_parameterization_admissibility_decision"]
        for row in route_rows
        if row["primary_calibration_object"] == "true"
    } == {"blocked_research_parameter_contract_missing_required_source_fields"}
    assert {
        row["research_parameterization_admissibility_decision"]
        for row in route_rows
        if row["primary_calibration_object"] != "true"
    } <= {
        "blocked_literature_context_not_source_backed_parameterization",
        "blocked_research_parameter_contract_missing_required_source_fields",
    }
    primary_rows = [
        row for row in route_rows if row["primary_calibration_object"] == "true"
    ]
    assert len(primary_rows) == 3
    assert {row["target_outcome_id"] for row in primary_rows} == {
        "fspdp_gdp_share"
    }
    assert {row["horizon_bucket"] for row in primary_rows} == {"4q", "8q", "12q"}
    assert {row["calibration_object_role"] for row in primary_rows} == {
        "primary_denominator_target"
    }
    assert all(row["outcome_series_id"] == "FSPDP" for row in primary_rows)
    selected = [
        row
        for row in route_rows
        if row["priority_selection_status"] == "selected_first_estimable_priority_row"
    ]
    assert {
        (row["source_priority_rank"], row["outcome_series_id"])
        for row in selected
    } == {("2", "TDSP")}
    assert {row["primary_calibration_object"] for row in selected} == {"false"}
    assert {row["calibration_object_role"] for row in selected} == {
        "channel_crosscheck"
    }
    assert {row["target_outcome_id"] for row in selected} == {"tdsp_diagnostic"}
    assert {row["regression_based_route_candidate_status"] for row in selected} == {
        "candidate_diagnostic_regression_route_available_not_admissible"
    }
    assert {
        row["regression_based_route_admissibility_decision"] for row in selected
    } == {
        "blocked_tdsp_regression_route_missing_current_demand_conversion_policy_path_uncertainty_replication_robustness"
    }
    assert {row["tdsp_refresh_diagnostic_row_count"] for row in selected} == {
        str(len(refresh_rows))
    }
    assert {row["tdsp_refresh_estimate_available_count"] for row in selected} == {
        str(sum(row["estimate_available"] == "true" for row in refresh_rows))
    }
    assert {row["policy_path_100bp_year_normalization_status"] for row in route_rows} == {
        "blocked_no_reviewed_policy_path_vector_or_duration_scalar"
    }
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "conventional_drag_calibration_route_fail_closed"
    } == {"pass"}
    assert (
        "outputs/tables/ratewall_conventional_drag_calibration_route.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert (
            "outputs/tables/ratewall_conventional_drag_calibration_route.csv"
            in set(archive.namelist())
        )
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["demand_drag_conversion_candidate_available"] == "false"
        and row["denominator_prior_update_allowed"] == "false"
        and row["empirical_threshold_claim_enabled"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in route_rows
    )


def test_conventional_drag_research_parameterization_contract_fails_closed() -> None:
    contract_rows = _read_output_table(
        "ratewall_conventional_drag_research_parameterization_source_contract.csv"
    )
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(contract_rows) == 24
    assert {row["priority_selection_status"] for row in contract_rows} == {
        "primary_current_demand_core_contract_selected"
    }
    assert {row["source_priority_rank"] for row in contract_rows} == {"1"}
    assert {row["outcome_series_id"] for row in contract_rows} == {"FSPDP"}
    assert {row["target_outcome_id"] for row in contract_rows} == {"fspdp_gdp_share"}
    assert {row["primary_calibration_object"] for row in contract_rows} == {"true"}
    assert {row["target_horizon_quarters"] for row in contract_rows} == {
        "4",
        "8",
        "12",
    }
    assert {row["horizon_bucket"] for row in contract_rows} == {"4q", "8q", "12q"}
    assert {row["required_field_name"] for row in contract_rows} == {
        "research_estimate_point_gdp_share_per_100bp_year",
        "research_estimate_uncertainty_interval",
        "policy_path_bps_year_exposure_protocol",
        "current_demand_mapping_protocol",
        "gdp_share_conversion_protocol",
        "independent_replication_aggregation",
        "robustness_and_transport_review",
        "provenance_manifest",
    }
    assert {row["source_backing_admission_status"] for row in contract_rows} == {
        "blocked_no_source_backed_contract_value"
    }
    assert {row["promotion_status"] for row in contract_rows} == {"blocked"}
    assert {
        row["claim_boundary"] for row in contract_rows
    } == {
        "conventional_drag_research_parameterization_source_contract_not_prior_narrowing_or_promotion"
    }
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"]
        == "conventional_drag_research_parameterization_contract_fail_closed"
    } == {"pass"}
    assert (
        "outputs/tables/ratewall_conventional_drag_research_parameterization_source_contract.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert (
            "outputs/tables/ratewall_conventional_drag_research_parameterization_source_contract.csv"
            in set(archive.namelist())
        )
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["demand_drag_conversion_candidate_available"] == "false"
        and row["denominator_prior_update_allowed"] == "false"
        and row["empirical_threshold_claim_enabled"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in contract_rows
    )


def test_conventional_drag_research_payload_manifest_fail_closed() -> None:
    rows = _read_output_table("ratewall_conventional_drag_research_payload_manifest.csv")
    invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert {
        row["source_candidate_handle"] for row in rows
    } == {"miranda_agrippino_ricco_aej", "gertler_karadi_aej"}
    assert {
        row["payload_presence_status"] for row in rows
    } <= {
        "blocked_payload_archive_missing",
        "blocked_payload_archive_unreadable",
        "pass_payload_inner_file_hashed_review_only",
    }
    present_rows = [
        row
        for row in rows
        if row["payload_presence_status"] == "pass_payload_inner_file_hashed_review_only"
    ]
    assert present_rows
    assert all(row["payload_archive_sha256"] for row in present_rows)
    assert all(row["inner_file_sha256"] for row in present_rows)
    assert all(row["payload_archive_path"] for row in rows)
    assert all(row["candidate_gdp_share_drag_per_100bp_year"] == "" for row in rows)
    assert all(
        row["source_admission_status"] == "blocked_or_diagnostic_only" for row in rows
    )
    assert all(
        row["denominator_prior_update_allowed"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "conventional_drag_research_payload_manifest_fail_closed"
    } == {"pass"}
    artifact = "outputs/tables/ratewall_conventional_drag_research_payload_manifest.csv"
    assert artifact in set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert artifact in set(archive.namelist())


def test_conventional_drag_research_parser_status_fail_closed() -> None:
    rows = _read_output_table(
        "ratewall_conventional_drag_research_parameterization_parser_status.csv"
    )
    payload_rows = _read_output_table("ratewall_conventional_drag_research_payload_manifest.csv")
    backend_invariant_rows = _read_output_table(
        "ratewall_backend_invariant_guardrail_audit.csv"
    )
    source_invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(rows) == len(payload_rows)
    assert len(rows) >= len(databook_build.CONVENTIONAL_DRAG_RESEARCH_EXPECTED_PARSE_ROLES) * 2
    assert {row["source_candidate_handle"] for row in rows} == {
        "miranda_agrippino_ricco_aej",
        "gertler_karadi_aej",
    }
    assert {row["payload_manifest_row_id"] for row in rows} == {
        row["payload_manifest_row_id"] for row in payload_rows
    }
    actual_roles = {row["expected_payload_role"] for row in rows}
    assert actual_roles <= set(databook_build.CONVENTIONAL_DRAG_RESEARCH_EXPECTED_PARSE_ROLES)
    assert {
        "readme_or_documentation",
        "replication_code",
        "source_data",
        "matlab_mat_or_output",
        "table_or_figure_output",
    } <= actual_roles
    assert {
        row["parser_object_role"] for row in rows
    } <= {
        "blocked_missing_payload_expected_object",
        "candidate_documentation",
        "candidate_irf_object",
        "candidate_mat_output_container",
        "candidate_payload_file_review_only",
        "candidate_replication_code",
        "candidate_source_data",
        "candidate_svar_or_proxy_svar_object",
        "candidate_table_or_figure_output",
    }
    assert {row["parser_eligible"] for row in rows} <= {"true", "false"}
    assert {
        row["research_parameterization_admission_status"] for row in rows
    } == {"blocked_parser_status_not_denominator_calibration"}
    assert {
        row["policy_path_100bp_year_compatibility_status"] for row in rows
    } == {"blocked_no_admitted_100bp_year_policy_path_bridge"}
    assert all(row["candidate_gdp_share_drag_per_100bp_year"] == "" for row in rows)
    assert all(row["candidate_ci_lower"] == "" and row["candidate_ci_upper"] == "" for row in rows)
    assert all(
        row["denominator_prior_update_allowed"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in rows
    )
    assert {
        row["audit_status"]
        for row in backend_invariant_rows
        if row["audit_item"]
        == "conventional_drag_research_parameterization_parser_status_fail_closed"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in source_invariant_rows
        if row["audit_item"]
        == "conventional_drag_research_parameterization_parser_status_fail_closed"
    } == {"pass"}
    artifact = (
        "outputs/tables/"
        "ratewall_conventional_drag_research_parameterization_parser_status.csv"
    )
    assert artifact in set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert artifact in set(archive.namelist())


def test_conventional_drag_research_extraction_harness_fail_closed() -> None:
    inner_rows = _read_output_table(
        "ratewall_conventional_drag_research_payload_inner_inventory.csv"
    )
    candidate_rows = _read_output_table(
        "ratewall_conventional_drag_research_extraction_candidate.csv"
    )
    gate_rows = _read_output_table(
        "ratewall_conventional_drag_research_extraction_gate_audit.csv"
    )
    gate_detail_rows = _read_output_table(
        "ratewall_conventional_drag_research_extraction_gate_detail.csv"
    )
    source_method_bridge_rows = _read_output_table(
        "ratewall_conventional_drag_research_source_method_bridge.csv"
    )
    source_code_interpretation_rows = _read_output_table(
        "ratewall_conventional_drag_research_source_code_interpretation.csv"
    )
    conversion_bridge_rows = _read_output_table(
        "ratewall_conventional_drag_research_extraction_conversion_bridge.csv"
    )
    contract_rows = _read_output_table(
        "ratewall_conventional_drag_research_parameterization_source_contract.csv"
    )
    backend_invariant_rows = _read_output_table(
        "ratewall_backend_invariant_guardrail_audit.csv"
    )
    source_invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(inner_rows) >= len(databook_build.CONVENTIONAL_DRAG_RESEARCH_EXPECTED_PARSE_ROLES) * 2
    assert len(candidate_rows) >= len(inner_rows)
    assert {row["inner_inventory_row_id"] for row in inner_rows} <= {
        row["inner_inventory_row_id"] for row in candidate_rows
    }
    assert {row["source_candidate_handle"] for row in inner_rows} == {
        "miranda_agrippino_ricco_aej",
        "gertler_karadi_aej",
    }
    actual_roles = {row["expected_payload_role"] for row in inner_rows}
    assert actual_roles <= set(databook_build.CONVENTIONAL_DRAG_RESEARCH_EXPECTED_PARSE_ROLES)
    assert {
        "readme_or_documentation",
        "replication_code",
        "source_data",
        "matlab_mat_or_output",
        "table_or_figure_output",
    } <= actual_roles
    assert {row["source_admission_status"] for row in inner_rows} == {
        "blocked_or_diagnostic_only"
    }
    assert {
        row["research_parameterization_admission_status"] for row in candidate_rows
    } == {"blocked_extraction_candidate_not_denominator_calibration"}
    assert {
        row["policy_path_100bp_year_compatibility_status"] for row in candidate_rows
    } == {"blocked_no_admitted_100bp_year_policy_path_bridge"}
    primary_contract_rows = [
        row for row in contract_rows if row["primary_calibration_object"] == "true"
    ]
    assert len(gate_rows) == len(primary_contract_rows) * 2 * 9
    assert {
        row["research_parameterization_admission_status"] for row in gate_rows
    } == {"blocked_extraction_gates_not_all_passed"}
    assert gate_detail_rows
    assert {
        row["required_gate"] for row in gate_detail_rows
    } == {
        "point_estimate",
        "uncertainty_interpretation",
        "policy_path_100bp_year_normalization",
        "current_demand_mapping",
        "gdp_share_conversion",
        "replication",
        "robustness",
        "provenance",
        "promotion_rule",
    }
    detail_groups: dict[tuple[str, ...], set[str]] = {}
    for row in gate_detail_rows:
        group_key = (
            row["source_candidate_handle"],
            row["source_method_object_family"],
            row["source_object_type"],
            row["source_outcome_label"],
            row["source_horizon_index"],
            row["source_statistic_role"],
            row["exact_blocker_group"],
        )
        detail_groups.setdefault(group_key, set()).add(row["required_gate"])
    assert all(
        gates
        == {
            "point_estimate",
            "uncertainty_interpretation",
            "policy_path_100bp_year_normalization",
            "current_demand_mapping",
            "gdp_share_conversion",
            "replication",
            "robustness",
            "provenance",
            "promotion_rule",
        }
        for gates in detail_groups.values()
    )
    raw_detail_rows = [
        row
        for row in gate_detail_rows
        if int(row["raw_value_available_count"]) > 0
    ]
    ambiguous_detail_rows = [
        row
        for row in gate_detail_rows
        if "ambiguous" in row["source_raw_value_parse_statuses"]
    ]
    assert raw_detail_rows
    assert ambiguous_detail_rows
    assert any(
        row["required_gate"] == "point_estimate"
        and row["gate_status"]
        == "blocked_source_raw_point_present_not_promotion_grade"
        for row in raw_detail_rows
    )
    assert any(
        row["required_gate"] == "point_estimate"
        and row["gate_status"] == "blocked_no_unambiguous_source_point_estimate"
        for row in ambiguous_detail_rows
    )
    assert {row["source_candidate_handle"] for row in gate_detail_rows} <= {
        "miranda_agrippino_ricco_aej",
        "gertler_karadi_aej",
    }
    assert "tdsp" not in {row["source_outcome_label"] for row in gate_detail_rows}
    assert {
        row["research_parameterization_admission_status"] for row in gate_detail_rows
    } == {"blocked_extraction_family_gates_not_all_passed"}
    assert source_method_bridge_rows
    bridge_keys = {
        (
            row["source_candidate_handle"],
            row["source_method_object_family"],
            row["source_object_type"],
            row["source_outcome_label"],
            row["source_horizon_index"],
            row["source_statistic_role"],
        )
        for row in source_method_bridge_rows
    }
    assert len(bridge_keys) == len(source_method_bridge_rows)
    assert {
        "nearest_usable_current_demand_irf_review_only",
        "ambiguous_irf_manual_source_code_interpretation_required",
        "source_data_or_metadata_not_reported_irf",
    } <= {row["parser_family_classification"] for row in source_method_bridge_rows}
    nearest_rows = [
        row
        for row in source_method_bridge_rows
        if row["parser_family_classification"]
        == "nearest_usable_current_demand_irf_review_only"
    ]
    assert nearest_rows
    assert {row["nearest_current_demand_irf_status"] for row in nearest_rows} == {
        "nearest_current_demand_irf_candidate_review_only"
    }
    assert {row["parser_readiness_status"] for row in nearest_rows} == {
        "review_ready_source_raw_component_irf_not_admitted"
    }
    assert {row["manual_interpretation_required"] for row in nearest_rows} == {"true"}
    assert {
        row["source_horizon_index"] for row in nearest_rows
    } <= {"4", "8", "12"}
    assert all(row["target_contract_scope_id"] for row in nearest_rows)
    assert {
        row["target_contract_match_status"] for row in nearest_rows
    } == {"blocked_component_proxy_not_fspdp_aggregate_contract"}
    assert "tdsp" not in {
        row["source_outcome_label"].lower() for row in source_method_bridge_rows
    }
    assert {
        row["research_parameterization_admission_status"]
        for row in source_method_bridge_rows
    } == {"blocked_source_method_bridge_not_denominator_calibration"}
    assert all(int(row["missing_gate_count"]) == 9 for row in source_method_bridge_rows)
    assert len(source_code_interpretation_rows) == len(nearest_rows)
    assert {row["source_candidate_handle"] for row in source_code_interpretation_rows} == {
        "miranda_agrippino_ricco_aej"
    }
    assert {
        row["source_outcome_label"] for row in source_code_interpretation_rows
    } == {"DDURRA3M086SBEA", "DNDGRA3M086SBEA", "HOUST", "PERMIT"}
    assert {
        row["source_horizon_index"] for row in source_code_interpretation_rows
    } == {"4", "8", "12"}
    assert {
        row["estimation_method"] for row in source_code_interpretation_rows
    } == {"bayesian_local_projection", "local_projection"}
    assert {
        row["variable_definition_status"] for row in source_code_interpretation_rows
    } == {"pass_source_script_lists_component_variable_review_only"}
    assert {
        row["uncertainty_band_semantics_status"]
        for row in source_code_interpretation_rows
    } == {
        "pass_irfs_l_u_quantile_band_semantics_review_only",
        "pass_irfs_l_u_robust_error_band_semantics_review_only",
    }
    assert {
        row["shock_scaling_status"] for row in source_code_interpretation_rows
    } == {"pass_source_script_gs1_one_percentage_point_review_only"}
    assert {
        row["horizon_interpretation_status"]
        for row in source_code_interpretation_rows
    } == {"pass_source_horizon_index_with_24_horizon_grid_review_only"}
    assert {
        row["fspdp_target_mapping_status"]
        for row in source_code_interpretation_rows
    } == {"blocked_component_proxy_not_fspdp_aggregate_or_gdp_share"}
    assert all(row["source_script_sha256s"] for row in source_code_interpretation_rows)
    assert {
        row["research_parameterization_admission_status"]
        for row in source_code_interpretation_rows
    } == {"blocked_source_code_interpretation_not_denominator_calibration"}
    assert len(conversion_bridge_rows) == 6
    assert {row["conversion_bridge_status"] for row in conversion_bridge_rows} == {
        "pass_source_backed_fspdp_share_bridge_available_not_drag"
    }
    assert {
        row["policy_path_normalization_gate_status"] for row in conversion_bridge_rows
    } == {"blocked_policy_path_100bp_year_compatibility_not_promotion_grade"}
    assert {
        row["research_parameterization_admission_status"]
        for row in conversion_bridge_rows
    } == {
        "blocked_conversion_bridge_missing_research_payload_normalization_uncertainty_replication_or_promotion"
    }
    for rows in (
        inner_rows,
        candidate_rows,
        gate_rows,
        gate_detail_rows,
        source_method_bridge_rows,
        source_code_interpretation_rows,
        conversion_bridge_rows,
    ):
        assert all(row["candidate_gdp_share_drag_per_100bp_year"] == "" for row in rows)
        assert all(row["candidate_ci_lower"] == "" for row in rows)
        assert all(row["candidate_ci_upper"] == "" for row in rows)
        assert all(
            all(row[field] == "false" for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS)
            for row in rows
        )
    for audit_item in {
        "conventional_drag_research_payload_inner_inventory_fail_closed",
            "conventional_drag_research_extraction_candidate_fail_closed",
            "conventional_drag_research_extraction_gate_audit_fail_closed",
            "conventional_drag_research_extraction_gate_detail_fail_closed",
            "conventional_drag_research_source_method_bridge_fail_closed",
            "conventional_drag_research_source_code_interpretation_fail_closed",
            "conventional_drag_research_extraction_conversion_bridge_fail_closed",
        }:
        assert {
            row["audit_status"]
            for row in backend_invariant_rows
            if row["audit_item"] == audit_item
        } == {"pass"}
        assert {
            row["audit_status"]
            for row in source_invariant_rows
            if row["audit_item"] == audit_item
        } == {"pass"}
    expected_artifacts = {
        "outputs/tables/ratewall_conventional_drag_research_payload_inner_inventory.csv",
        "outputs/tables/ratewall_conventional_drag_research_extraction_candidate.csv",
        "outputs/tables/ratewall_conventional_drag_research_extraction_gate_audit.csv",
        "outputs/tables/ratewall_conventional_drag_research_extraction_gate_detail.csv",
        "outputs/tables/ratewall_conventional_drag_research_source_method_bridge.csv",
        "outputs/tables/ratewall_conventional_drag_research_source_code_interpretation.csv",
        "outputs/tables/ratewall_conventional_drag_research_extraction_conversion_bridge.csv",
    }
    assert expected_artifacts <= set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_artifacts <= set(archive.namelist())


def test_conventional_drag_research_parser_status_hashes_present_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload_path = tmp_path / "openicpsr_e116841_payload.zip"
    with zipfile.ZipFile(payload_path, "w") as archive:
        archive.writestr(
            "REPLICATION-FILES---PUBLIC/README.txt",
            (
                "readme monetary policy shock basis points output horizon "
                "bootstrap confidence interval 1979 2014 replication"
            ),
        )
        archive.writestr(
            "REPLICATION-FILES---PUBLIC/code/proxy_svar_irf.m",
            "% proxy SVAR IRF bootstrap confidence interval\nH=20; output = 1;",
        )
        archive.writestr(
            "REPLICATION-FILES---PUBLIC/DATA/source_data.csv",
            "date,output,shock\n1979,1,2\n",
        )
        archive.writestr("REPLICATION-FILES---PUBLIC/MATfiles/IRFs.mat", "mat")
        archive.writestr("REPLICATION-FILES---PUBLIC/TABLES/Table1.xlsx", "table")

    monkeypatch.setattr(
        databook_legacy,
        "CONVENTIONAL_DRAG_RESEARCH_PAYLOAD_SLOTS",
        (
            {
                "source_candidate_handle": "miranda_agrippino_ricco_aej",
                "project_id": "116841",
                "payload_archive_path": str(payload_path),
            },
        ),
    )
    payload_rows = databook_build._ratewall_conventional_drag_research_payload_manifest_rows()
    parser_rows = (
        databook_build._ratewall_conventional_drag_research_parameterization_parser_status_rows(
            payload_rows
        )
    )
    inner_rows = databook_build._ratewall_conventional_drag_research_payload_inner_inventory_rows(
        payload_rows
    )
    candidate_rows = (
        databook_build._ratewall_conventional_drag_research_extraction_candidate_rows(
            inner_rows
        )
    )

    assert len(payload_rows) == 5
    assert len(parser_rows) == 5
    assert len(inner_rows) == 5
    assert len(candidate_rows) == 5
    assert all(row["payload_archive_sha256"] for row in parser_rows)
    assert all(row["inner_file_sha256"] for row in parser_rows)
    assert all(row["inner_file_sha256"] for row in inner_rows)
    readme_row = next(row for row in parser_rows if row["inner_file_path"].endswith("README.txt"))
    assert readme_row["content_parse_status"] == (
        "pass_payload_content_metadata_parsed_review_only"
    )
    assert "basis_points" in readme_row["parsed_shock_tokens"]
    assert "output" in readme_row["parsed_outcome_tokens"]
    assert "bootstrap" in readme_row["parsed_uncertainty_tokens"]
    assert readme_row["shock_normalization_status"] == (
        "blocked_source_shock_metadata_present_not_100bp_year"
    )
    assert {
        row["parser_object_role"]
        for row in parser_rows
        if "proxy_svar_irf" in row["inner_file_path"]
    } == {"candidate_svar_or_proxy_svar_object"}
    assert {
        row["replication_status"]
        for row in parser_rows
        if "proxy_svar_irf" in row["inner_file_path"]
    } == {"blocked_replication_script_metadata_present_no_run"}
    assert {
        row["expected_payload_role"]
        for row in parser_rows
        if row["inner_file_path"].endswith("IRFs.mat")
    } == {"matlab_mat_or_output"}
    assert {
        row["expected_payload_role"]
        for row in parser_rows
        if row["inner_file_path"].endswith("source_data.csv")
    } == {"source_data"}
    assert {
        row["expected_payload_role"]
        for row in parser_rows
        if row["inner_file_path"].endswith("Table1.xlsx")
    } == {"table_or_figure_output"}
    assert all(row["candidate_gdp_share_drag_per_100bp_year"] == "" for row in parser_rows)
    assert all(
        row["research_parameterization_admission_status"]
        == "blocked_parser_status_not_denominator_calibration"
        for row in parser_rows
    )
    assert {
        row["parser_object_role"]
        for row in candidate_rows
        if "proxy_svar_irf" in row["inner_file_path"]
    } == {"candidate_svar_or_proxy_svar_object"}
    assert {
        row["shock_unit_original"]
        for row in candidate_rows
        if row["inner_file_path"].endswith("README.txt")
    } == {"source_metadata_mentions_basis_points_not_100bp_year"}
    assert all(
        row["research_parameterization_admission_status"]
        == "blocked_extraction_candidate_not_denominator_calibration"
        for row in candidate_rows
    )
    assert all(row["candidate_gdp_share_drag_per_100bp_year"] == "" for row in candidate_rows)


def test_conventional_drag_research_payload_content_metadata_is_source_bound() -> None:
    parser_rows = _read_output_table(
        "ratewall_conventional_drag_research_parameterization_parser_status.csv"
    )
    candidate_rows = _read_output_table(
        "ratewall_conventional_drag_research_extraction_candidate.csv"
    )

    assert {row["content_parse_status"] for row in parser_rows} == {
        "pass_payload_content_metadata_parsed_review_only"
    }
    assert sum(1 for row in parser_rows if row["parsed_shock_tokens"]) > 0
    assert sum(1 for row in parser_rows if row["parsed_outcome_tokens"]) > 0
    assert sum(1 for row in parser_rows if row["parsed_mat_variable_names"]) > 0
    assert sum(1 for row in parser_rows if row["parsed_xlsx_sheet_names"]) > 0
    assert any(
        "shockSize" in row["parsed_mat_variable_names"]
        for row in parser_rows
        if row["inner_file_path"].endswith("IRFs7914_Figure7.mat")
    )
    assert any(
        "FF4_IV_variants" in row["parsed_xlsx_sheet_names"]
        for row in parser_rows
        if row["inner_file_path"].endswith("Miranda-Agrippino&Ricco_ALLDATA.xlsx")
    )
    assert any(
        row["replication_status"]
        == "blocked_replication_script_metadata_present_no_run"
        for row in parser_rows
        if row["inner_file_path"].endswith("VAR_main.m")
    )
    assert all(
        row["policy_path_100bp_year_compatibility_status"]
        == "blocked_no_admitted_100bp_year_policy_path_bridge"
        for row in candidate_rows
    )
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["candidate_ci_lower"] == ""
        and row["candidate_ci_upper"] == ""
        for row in candidate_rows
    )
    assert {
        "matlab_mat_variable",
        "matlab_irf_response_cell",
        "xlsx_sheet",
        "replication_code_script",
        "documentation_text",
    } <= {row["source_object_type"] for row in candidate_rows}
    assert any(
        row["source_object_type"] == "matlab_irf_response_cell"
        and row["source_object_name"].startswith("IRF_::")
        and row["source_raw_value_parse_status"]
        == "blocked_irfs_and_irfs_m_both_present_point_field_ambiguous"
        and row["point_estimate_raw"] == ""
        and row["lower_raw"] == ""
        and row["upper_raw"] == ""
        for row in candidate_rows
        if row["inner_file_path"].endswith("IRFs7914_Figure7.mat")
    )
    unambiguous_irf_rows = [
        row
        for row in candidate_rows
        if row["source_object_type"] == "matlab_irf_response_cell"
        and "Input_D2_1.mat" in row["inner_file_path"]
        and row["source_object_name"].startswith("IRF_LP::")
        and row["source_horizon_index"] == "0"
    ]
    assert unambiguous_irf_rows
    assert any(
        row["source_raw_value_parse_status"] == "pass_irfs_point_field_unambiguous"
        and row["point_estimate_raw"] != ""
        and row["lower_raw"] != ""
        and row["upper_raw"] != ""
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["candidate_ci_lower"] == ""
        and row["candidate_ci_upper"] == ""
        for row in unambiguous_irf_rows
    )
    assert any(
        row["source_object_type"] == "xlsx_sheet"
        and row["source_object_name"] == "MM_IVinstruments"
        and row["source_raw_value_parse_status"]
        == "blocked_xlsx_sheet_inventory_not_reported_response_estimate"
        and row["point_estimate_raw"] == ""
        and row["lower_raw"] == ""
        and row["upper_raw"] == ""
        for row in candidate_rows
    )


def test_current_demand_gdp_share_panel_is_conversion_only() -> None:
    source_rows = _read_output_table(
        "ratewall_current_demand_gdp_share_source_manifest.csv"
    )
    panel_rows = _read_output_table("ratewall_current_demand_gdp_share_panel.csv")
    bridge_rows = _read_output_table(
        "ratewall_conventional_drag_current_demand_mapping_bridge.csv"
    )
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    expected_series = {
        "LA0000031Q027SBEA",
        "LB0000031Q020SBEA",
        "GDP",
        "GDPC1",
        "PCEC",
        "PCECC96",
        "FPI",
        "FPIC1",
    }
    expected_components = {"fspdp", "gdp", "pce", "private_fixed_investment"}
    assert {row["source_series_id"] for row in source_rows} == expected_series
    assert {row["component_id"] for row in source_rows} == expected_components
    assert {row["component_id"] for row in panel_rows} == expected_components
    assert all(row["source_hash"] for row in source_rows)
    assert all(row["source_snapshot_sha256"] for row in source_rows)
    assert all(row["source_hash"] for row in panel_rows)
    assert all(row["source_snapshot_sha256"] for row in panel_rows)

    gdp_rows = [row for row in panel_rows if row["component_id"] == "gdp"]
    assert gdp_rows
    assert {row["nominal_share_of_gdp"] for row in gdp_rows} == {"1"}
    assert {row["transformation_status"] for row in gdp_rows} == {
        "pass_gdp_share_identity"
    }
    assert {
        row["transformation_status"]
        for row in panel_rows
        if row["component_id"] != "gdp"
    } <= {
        "pass_nominal_share_and_real_quantity_source_joined",
        "pass_nominal_share_real_series_missing_or_unavailable",
    }
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        for row in [*source_rows, *panel_rows, *bridge_rows]
    )
    assert all(
        row[field] == "false"
        for row in [*source_rows, *panel_rows, *bridge_rows]
        for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
    )
    assert len(bridge_rows) == 27
    assert {row["component_id"] for row in bridge_rows} == {
        "fspdp",
        "pce",
        "private_fixed_investment",
    }
    assert {row["target_horizon_quarters"] for row in bridge_rows} == {
        "4",
        "8",
        "12",
    }
    assert {row["share_window_id"] for row in bridge_rows} == {
        "baseline_1994q1_2019q4",
        "full_available_panel",
        "latest_12q_available",
    }
    assert {row["conversion_formula_status"] for row in bridge_rows} == {
        "pass_share_formula_review_only_no_irf_or_bps_year"
    }
    assert {
        row["policy_path_100bp_year_normalization_status"] for row in bridge_rows
    } == {"blocked_no_admitted_bps_year_policy_path"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "current_demand_gdp_share_conversion_panel_no_drag"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "conventional_drag_current_demand_mapping_bridge_no_drag"
    } == {"pass"}

    expected_release_paths = {
        "outputs/tables/ratewall_current_demand_gdp_share_source_manifest.csv",
        "outputs/tables/ratewall_current_demand_gdp_share_panel.csv",
        "outputs/tables/ratewall_conventional_drag_current_demand_mapping_bridge.csv",
    }
    assert expected_release_paths <= set(
        release_manifest["artifact_layers"]["assumption_mode"]
    )
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        archive_names = set(archive.namelist())
    assert expected_release_paths <= archive_names
    assert (
        "data/raw/current_demand_gdp_share/current_demand_gdp_share_snapshot.json"
        in archive_names
    )


def test_conventional_drag_local_lp_scaffold_fails_closed() -> None:
    macro_rows = _read_output_table("ratewall_conventional_drag_local_macro_panel.csv")
    shock_rows = _read_output_table(
        "ratewall_conventional_drag_local_shock_quarterly.csv"
    )
    design_rows = _read_output_table("ratewall_conventional_drag_local_lp_design.csv")
    diagnostic_rows = _read_output_table(
        "ratewall_conventional_drag_local_lp_diagnostic.csv"
    )
    estimate_rows = _read_output_table(
        "ratewall_conventional_drag_local_lp_estimate_diagnostic.csv"
    )
    robustness_rows = _read_output_table(
        "ratewall_conventional_drag_local_lp_robustness_diagnostic.csv"
    )
    sample_rows = _read_output_table(
        "ratewall_conventional_drag_local_lp_sample_window_audit.csv"
    )
    admission_rows = _read_output_table(
        "ratewall_conventional_drag_local_lp_admission_audit.csv"
    )
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(macro_rows) == 317
    assert len(shock_rows) == 1280
    assert len(design_rows) == 40
    assert len(diagnostic_rows) == 240
    assert len(estimate_rows) == 240
    assert len(robustness_rows) == 960
    assert len(sample_rows) == 40
    assert len(admission_rows) == 11
    assert {row["outcome_id"] for row in design_rows} == {
        "fspdp",
        "gdp",
        "pce",
        "private_fixed_investment",
    }
    assert {
        row["policy_path_100bp_year_normalization_status"]
        for row in shock_rows + diagnostic_rows + estimate_rows + robustness_rows + sample_rows
    } == {"blocked_no_admitted_bps_year_policy_path"}
    assert {
        row["source_admission_status"] for row in diagnostic_rows
    } == {"blocked_diagnostic_estimate_only"}
    assert {
        row["promotion_status"] for row in design_rows
    } == {"blocked_local_lp_diagnostic_only"}
    assert {
        row["gate_status"]
        for row in admission_rows
        if row["required_gate"] == "policy_path_100bp_year_normalization"
    } == {"blocked_policy_path_100bp_year_normalization_not_admitted"}
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        for row in macro_rows
        + shock_rows
        + design_rows
        + diagnostic_rows
        + estimate_rows
        + robustness_rows
        + sample_rows
        + admission_rows
    )
    assert all(
        row["beta_point"] == ""
        and row["beta_se_nw"] == ""
        and row["cum_response_point"] == ""
        for row in diagnostic_rows
    )
    available_estimates = [
        row
        for row in estimate_rows
        if row["diagnostic_estimate_status"]
        == "diagnostic_lp_source_unit_estimate_available_not_calibration"
    ]
    assert len(available_estimates) == 72
    assert {row["outcome_id"] for row in estimate_rows}.isdisjoint({"tdsp"})
    assert all(row["beta_source_unit"] != "" for row in available_estimates)
    assert all(row["se_hac_source_unit"] != "" for row in available_estimates)
    assert all(row["cum_response_source_unit"] != "" for row in available_estimates)
    assert all(row["sample_start_q"] for row in available_estimates)
    assert all(row["sample_end_q"] for row in available_estimates)
    assert all(row["n_obs"] for row in available_estimates)
    assert {row["exclude_elb"] for row in estimate_rows} <= {"true", ""}
    assert {row["exclude_pandemic"] for row in estimate_rows} <= {"true", ""}
    assert {row["exclude_emergency_meetings"] for row in estimate_rows} <= {
        "true",
        "",
    }
    assert {
        row["sample_window_status"] for row in available_estimates
    } == {"pass_source_unit_diagnostic_sample_available_not_calibration"}
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        for row in available_estimates
    )
    assert {
        row["robustness_case"] for row in robustness_rows
    } == {
        "baseline_source_unit",
        "drop_max_abs_shock_source_unit",
        "pretrend_lead1_source_unit",
        "leave_one_out_max_shift_source_unit",
    }
    assert any(
        row["leave_one_out_status"]
        == "diagnostic_leave_one_out_source_unit_estimated_not_promotion"
        for row in robustness_rows
    )
    assert any(
        row["sample_window_status"]
        == "pass_source_unit_diagnostic_sample_available_not_calibration"
        for row in sample_rows
    )
    assert all(
        row[field] == "false"
        for row in macro_rows
        + shock_rows
        + design_rows
        + diagnostic_rows
        + estimate_rows
        + robustness_rows
        + sample_rows
        + admission_rows
        for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "conventional_drag_local_lp_diagnostic_fail_closed"
    } == {"pass"}

    expected_release_paths = {
        "outputs/tables/ratewall_conventional_drag_local_macro_panel.csv",
        "outputs/tables/ratewall_conventional_drag_local_shock_quarterly.csv",
        "outputs/tables/ratewall_conventional_drag_local_lp_design.csv",
        "outputs/tables/ratewall_conventional_drag_local_lp_diagnostic.csv",
        "outputs/tables/ratewall_conventional_drag_local_lp_estimate_diagnostic.csv",
        "outputs/tables/ratewall_conventional_drag_local_lp_robustness_diagnostic.csv",
        "outputs/tables/ratewall_conventional_drag_local_lp_sample_window_audit.csv",
        "outputs/tables/ratewall_conventional_drag_local_lp_admission_audit.csv",
    }
    assert expected_release_paths <= set(
        release_manifest["artifact_layers"]["assumption_mode"]
    )
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_release_paths <= set(archive.namelist())


def test_conventional_drag_source_frontier_acquires_hashes_and_fails_closed() -> None:
    frontier_rows = _read_output_table(
        "ratewall_conventional_drag_research_parameterization_source_frontier.csv"
    )
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    raw_manifest = json.loads(
        Path(
            "data/raw/conventional_drag_parameterization_sources/"
            "source_acquisition_manifest.json"
        ).read_text(encoding="utf-8")
    )

    assert len(frontier_rows) == 72
    assert raw_manifest["output_row_count"] == len(frontier_rows)
    assert {
        row["required_contract_field"] for row in frontier_rows
    } == {
        "point_estimate_gdp_share_per_100bp_year",
        "uncertainty_interval",
        "policy_path_normalization",
        "current_demand_mapping",
        "gdp_share_conversion",
        "replication_or_aggregation",
        "robustness_transport",
        "provenance_and_promotion_rule",
    }
    acquired = [row for row in frontier_rows if row["artifact_sha256"]]
    assert len(acquired) >= 40
    assert {
        row["research_parameterization_admission_status"] for row in frontier_rows
    } == {"blocked_missing_full_research_parameterization_contract"}
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["candidate_ci_lower"] == ""
        and row["candidate_ci_upper"] == ""
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in frontier_rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"]
        == "conventional_drag_research_parameterization_source_frontier_fail_closed"
    } == {"pass"}
    assert (
        "outputs/tables/ratewall_conventional_drag_research_parameterization_source_frontier.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        names = set(archive.namelist())
        assert (
            "outputs/tables/ratewall_conventional_drag_research_parameterization_source_frontier.csv"
            in names
        )
        assert (
            "data/raw/conventional_drag_parameterization_sources/"
            "source_acquisition_manifest.json"
            in names
        )


def test_openicpsr_replication_package_manifest_fails_closed() -> None:
    rows = _read_output_table("ratewall_openicpsr_replication_package_source_manifest.csv")
    invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    raw_manifest = json.loads(
        Path(
            "data/raw/conventional_drag_parameterization_sources/"
            "openicpsr_replication_package_acquisition_manifest.json"
        ).read_text(encoding="utf-8")
    )

    assert len(rows) == 14
    assert raw_manifest["output_row_count"] == len(rows)
    assert {row["source_candidate_handle"] for row in rows} == {
        "miranda_agrippino_ricco_aej",
        "gertler_karadi_aej",
    }
    assert {row["project_id"] for row in rows} == {"116841", "114082"}
    assert {
        "readme",
        "code_inventory",
        "data_workbook_inventory",
        "data_build_code_inventory",
        "irf_figure_code_inventory",
        "proxy_svar_code_inventory",
    } <= {row["candidate_review_role"] for row in rows}
    assert any(
        row["source_candidate_handle"] == "miranda_agrippino_ricco_aej"
        and int(row["parsed_file_manifest_entry_count"] or "0") >= 20
        and "Replicate_Figure10.m" in row["parsed_candidate_file_names"]
        for row in rows
    )
    assert any(
        row["source_candidate_handle"] == "gertler_karadi_aej"
        and int(row["parsed_file_manifest_entry_count"] or "0") >= 20
        and "VAR_main_RunMe.m" in row["candidate_variable_or_irf_names"]
        for row in rows
    )
    assert any(
        row["candidate_readme_status"] == "pass_readme_metadata_present_review_only"
        and row["metadata_artifact_sha256"]
        for row in rows
    )
    assert any(
        row["candidate_code_status"] == "pass_code_metadata_present_review_only"
        and row["metadata_artifact_sha256"]
        for row in rows
    )
    assert any(
        row["candidate_data_status"] == "pass_data_metadata_present_review_only"
        for row in rows
    )
    assert {
        row["source_file_payload_status"] for row in rows
    } == {"blocked_openicpsr_payload_not_downloaded_terms_or_cloudflare"}
    payload_rows = [
        row
        for row in rows
        if row["object_kind"] in {"file_page_html", "folder_page_html"}
    ]
    assert payload_rows
    assert all("download/terms" in row["source_file_payload_download_url"] for row in payload_rows)
    assert {
        "blocked_http_error_from_download_terms_route",
        "blocked_login_required_from_download_terms_route",
    } & {row["source_file_payload_blocker_class"] for row in payload_rows}
    assert all(
        row["source_file_payload_path"] == ""
        and row["source_file_payload_sha256"] == ""
        and (
            row["source_file_payload_blocker_class"]
            in {
                "not_applicable_metadata_only_object",
                "blocked_http_error_from_download_terms_route",
                "blocked_login_required_from_download_terms_route",
                "blocked_terms_or_html_interstitial_from_download_terms_route",
                "blocked_network_error_from_download_terms_route",
                "blocked_no_download_terms_link_discovered",
            }
        )
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["candidate_ci_lower"] == ""
        and row["candidate_ci_upper"] == ""
        and row["bps_year_exposure_output"] == ""
        and row["research_parameterization_admission_status"].startswith("blocked_")
        and row["candidate_uncertainty_availability_status"]
        == "blocked_no_parsed_uncertainty_array_or_confidence_interval"
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"]
        == "openicpsr_replication_package_source_manifest_fail_closed"
    } == {"pass"}


def test_frbus_model_benchmark_readiness_fails_closed() -> None:
    rows = _read_output_table("ratewall_frbus_model_benchmark_simulation_readiness.csv")
    invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(rows) == 16
    assert {row["artifact_handle"] for row in rows} == {
        "frbus_python_package_zip",
        "frbus_data_only_package_zip",
    }
    assert all(row["artifact_sha256"] for row in rows)
    assert any(
        "pyfrbus/demos/example1.py" in row["candidate_file_or_variable"]
        for row in rows
    )
    assert any("XGDP" in row["candidate_file_or_variable"] for row in rows)
    assert {
        row["model_benchmark_admission_status"] for row in rows
    } == {"blocked_model_benchmark_readiness_only_not_denominator_value"}
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["bps_year_exposure_output"] == ""
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"]
        == "frbus_model_benchmark_simulation_readiness_fail_closed"
    } == {"pass"}
    expected_path = (
        "outputs/tables/ratewall_frbus_model_benchmark_simulation_readiness.csv"
    )
    assert expected_path in set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_path in set(archive.namelist())


def test_frbus_conventional_drag_benchmark_protocol_fails_closed() -> None:
    rows = _read_output_table("ratewall_frbus_conventional_drag_benchmark_protocol.csv")
    readiness_rows = _read_output_table(
        "ratewall_frbus_model_benchmark_simulation_readiness.csv"
    )
    invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(rows) == len({row["artifact_handle"] for row in readiness_rows}) * 4 * 3
    assert {row["model_artifact_handle"] for row in rows} == {
        "frbus_python_package_zip",
        "frbus_data_only_package_zip",
    }
    assert {
        row["model_benchmark_admission_status"] for row in rows
    } == {"blocked_frbus_benchmark_protocol_not_calibration"}
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["candidate_ci_lower"] == ""
        and row["candidate_ci_upper"] == ""
        and row["bps_year_exposure_output"] == ""
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "frbus_conventional_drag_benchmark_protocol_fail_closed"
    } == {"pass"}
    expected_path = "outputs/tables/ratewall_frbus_conventional_drag_benchmark_protocol.csv"
    assert expected_path in set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_path in set(archive.namelist())


def test_frbus_official_model_package_inventory_and_simulation_protocol_fail_closed() -> None:
    inventory_rows = _read_output_table(
        "ratewall_frbus_official_model_package_inventory.csv"
    )
    protocol_rows = _read_output_table(
        "ratewall_frbus_official_model_benchmark_simulation_protocol.csv"
    )
    invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(inventory_rows) == 15
    assert {row["artifact_handle"] for row in inventory_rows} == {
        "frbus_python_landing_page_html",
        "frbus_python_package_zip",
        "frbus_data_only_package_zip",
    }
    assert {
        "model_equation_file",
        "official_100bp_policy_shock_demo",
        "frbus_baseline_dataset",
        "frbus_historical_dataset",
    } <= {row["inner_file_role"] for row in inventory_rows}
    assert all(row["artifact_sha256"] for row in inventory_rows)
    assert all(
        row["inner_file_sha256"] or row["inner_file_role"] == "landing_page_metadata"
        for row in inventory_rows
    )
    assert {
        row["model_benchmark_admission_status"] for row in inventory_rows
    } == {"blocked_package_inventory_only_not_denominator_value"}

    assert len(protocol_rows) == 4 * 3 * 9
    assert {row["protocol_gate"] for row in protocol_rows} == {
        "source_artifact_hashes",
        "model_code_inventory",
        "baseline_dataset_inventory",
        "official_100bp_demo_identified",
        "run_environment",
        "simulation_execution",
        "policy_path_100bp_year_normalization",
        "current_demand_gdp_share_mapping",
        "uncertainty_replication_promotion",
    }
    assert {
        "pass_official_artifact_hashes_present",
        "pass_model_code_inventory_present",
        "pass_data_package_inventory_present",
        "pass_official_demo_add_factor_identified_review_only",
        "blocked_no_reviewed_reproducible_frbus_runtime_environment",
        "blocked_no_replicated_ratewall_frbus_simulation_output",
        "blocked_no_admitted_100bp_year_mapping_for_frbus_demo",
        "blocked_no_frbus_current_demand_to_gdp_share_response_mapping",
        "blocked_no_empirical_uncertainty_replication_or_promotion_rule",
    } == {row["gate_status"] for row in protocol_rows}
    assert {
        row["model_benchmark_admission_status"] for row in protocol_rows
    } == {"blocked_frbus_simulation_protocol_not_calibration"}
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["candidate_ci_lower"] == ""
        and row["candidate_ci_upper"] == ""
        and row["bps_year_exposure_output"] == ""
        and row["policy_path_100bp_year_compatibility_status"]
        == "blocked_one_period_demo_not_admitted_100bp_year"
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in protocol_rows
    )
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["candidate_ci_lower"] == ""
        and row["candidate_ci_upper"] == ""
        and row["bps_year_exposure_output"] == ""
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in inventory_rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"]
        in {
            "frbus_official_model_package_inventory_fail_closed",
            "frbus_official_model_benchmark_simulation_protocol_fail_closed",
        }
    } == {"pass"}
    expected_paths = {
        "outputs/tables/ratewall_frbus_official_model_package_inventory.csv",
        (
            "outputs/tables/"
            "ratewall_frbus_official_model_benchmark_simulation_protocol.csv"
        ),
    }
    assert expected_paths <= set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_paths <= set(archive.namelist())


def test_frbus_runtime_runner_preflight_and_output_slots_fail_closed() -> None:
    preflight_rows = _read_output_table("ratewall_frbus_runtime_runner_preflight.csv")
    output_rows = _read_output_table("ratewall_frbus_runtime_runner_output_slots.csv")
    invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    backend_invariant_rows = _read_output_table(
        "ratewall_backend_invariant_guardrail_audit.csv"
    )
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(preflight_rows) == 5
    assert {row["step_id"] for row in preflight_rows} == {
        "installed_package_metadata_check",
        "dependency_import_check",
        "pyfrbus_import_check",
        "frbus_model_load_check",
        "official_100bp_demo_execution_check",
    }
    assert {row["runtime_step_status"] for row in preflight_rows} == {
        "pass_runtime_step_completed_review_only"
    }
    assert all(row["pyfrbus_package_sha256"] for row in preflight_rows)
    assert all(row["data_package_sha256"] for row in preflight_rows)
    assert all(row["dependency_install_command"] for row in preflight_rows)
    assert {
        row["model_benchmark_admission_status"] for row in preflight_rows
    } == {"blocked_frbus_runtime_preflight_not_calibration"}

    assert len(output_rows) == 3
    assert {row["output_slot_name"] for row in output_rows} == {
        "xgdp_h4",
        "ec_h4",
        "ebfi_h4",
    }
    assert all(row["model_output_value_review_only"] for row in output_rows)
    assert {
        row["model_benchmark_admission_status"] for row in output_rows
    } == {"blocked_frbus_runtime_output_slot_not_calibration"}
    assert {
        row["policy_path_100bp_year_compatibility_status"] for row in output_rows
    } == {"blocked_frbus_demo_not_admitted_100bp_year_policy_path"}

    for rows in (preflight_rows, output_rows):
        assert all(
            row["candidate_gdp_share_drag_per_100bp_year"] == ""
            and row["candidate_ci_lower"] == ""
            and row["candidate_ci_upper"] == ""
            and row["bps_year_exposure_output"] == ""
            and all(
                row[field] == "false"
                for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
            )
            for row in rows
        )

    expected_audits = {
        "frbus_runtime_runner_preflight_fail_closed",
        "frbus_runtime_runner_output_slots_fail_closed",
    }
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] in expected_audits
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in backend_invariant_rows
        if row["audit_item"] in expected_audits
    } == {"pass"}
    expected_paths = {
        "outputs/tables/ratewall_frbus_runtime_runner_preflight.csv",
        "outputs/tables/ratewall_frbus_runtime_runner_output_slots.csv",
    }
    assert expected_paths <= set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        names = set(archive.namelist())
        assert expected_paths <= names
        assert (
            "data/raw/conventional_drag_parameterization_sources/"
            "frbus_runtime_runner_preflight.json"
        ) in names


def test_frbus_benchmark_comparison_mapping_contract_fails_closed() -> None:
    rows = _read_output_table("ratewall_frbus_benchmark_comparison_mapping_contract.csv")
    output_rows = _read_output_table("ratewall_frbus_runtime_runner_output_slots.csv")
    invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    backend_invariant_rows = _read_output_table(
        "ratewall_backend_invariant_guardrail_audit.csv"
    )
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(rows) == len(output_rows) * 8
    assert {row["output_slot_name"] for row in rows} == {
        "xgdp_h4",
        "ec_h4",
        "ebfi_h4",
    }
    assert {row["required_gate"] for row in rows} == {
        "runtime_reproduction",
        "pinned_output_comparison",
        "policy_path_100bp_year_normalization",
        "current_demand_mapping",
        "gdp_share_conversion",
        "empirical_uncertainty",
        "independent_replication",
        "promotion_rule",
    }
    assert all(row["pinned_model_output_value"] for row in rows)
    assert all(row["source_preflight_json_sha256"] for row in rows)
    assert all(row["pyfrbus_package_sha256"] for row in rows)
    assert all(row["data_package_sha256"] for row in rows)
    assert all(row["solver_package_versions"] for row in rows)
    assert {
        row["model_benchmark_admission_status"] for row in rows
    } == {"blocked_frbus_benchmark_comparison_mapping_not_calibration"}
    assert {
        row["policy_path_100bp_year_compatibility_status"] for row in rows
    } == {"blocked_frbus_demo_not_admitted_100bp_year_policy_path"}
    component_mapping_rows = [
        row for row in rows if row["outcome_id"] in {"real_pce", "real_private_fixed_investment"}
    ]
    assert component_mapping_rows
    assert all(row["current_demand_mapping_bridge_row_id"] for row in component_mapping_rows)
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["candidate_ci_lower"] == ""
        and row["candidate_ci_upper"] == ""
        and row["bps_year_exposure_output"] == ""
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"]
        == "frbus_benchmark_comparison_mapping_contract_fail_closed"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in backend_invariant_rows
        if row["audit_item"]
        == "frbus_benchmark_comparison_mapping_contract_fail_closed"
    } == {"pass"}
    expected_path = (
        "outputs/tables/ratewall_frbus_benchmark_comparison_mapping_contract.csv"
    )
    assert expected_path in set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_path in set(archive.namelist())


def test_tdsp_current_demand_mapping_tranche_fails_closed() -> None:
    source_rows = _read_output_table("ratewall_tdsp_current_demand_source_review.csv")
    conversion_rows = _read_output_table(
        "ratewall_tdsp_current_demand_unit_conversion.csv"
    )
    mapping_rows = _read_output_table(
        "ratewall_tdsp_current_demand_diagnostic_mapping.csv"
    )
    path_rows = _read_output_table(
        "ratewall_tdsp_policy_path_normalization_blocker.csv"
    )
    audit_rows = _read_output_table("ratewall_tdsp_current_demand_admission_audit.csv")
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    public_readme = Path("outputs/reports/ratewall_public_readme.md").read_text(
        encoding="utf-8"
    )
    table_plate = Path("outputs/reports/ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )

    assert len(source_rows) == 8
    assert len(conversion_rows) == 5
    assert len(mapping_rows) == 15
    assert len(path_rows) == 3
    assert len(audit_rows) == (
        len(source_rows) + len(conversion_rows) + len(mapping_rows) + len(path_rows)
    )
    assert {
        row["source_id"]
        for row in source_rows
        if row["source_admission_status"] == "blocked_missing_source_snapshot"
    } == set()
    refresh_backed_source_rows = [
        row for row in source_rows if row["source_id"] in {"PCEC", "PCECC96", "DSPI"}
    ]
    assert {row["source_snapshot_status"] for row in refresh_backed_source_rows} == {
        "missing_from_current_snapshot"
    }
    assert {
        row["source_admission_status"] for row in refresh_backed_source_rows
    } == {
        "blocked_current_runtime_snapshot_missing_refresh_bundle_materialized_review_only"
    }
    assert all(
        "materialized in the reproducible PCE/DPI refresh bundle"
        in row["exact_blocker"]
        for row in refresh_backed_source_rows
    )
    assert {row["source_status"] for row in refresh_backed_source_rows} == {
        "tdsp_current_demand_source_review_blocked_fail_closed"
    }
    assert {row["source_snapshot_kind_summary"] for row in refresh_backed_source_rows} == {
        "PCEC:refresh_bundle_not_current_runtime_snapshot",
        "PCECC96:refresh_bundle_not_current_runtime_snapshot",
        "DSPI:refresh_bundle_not_current_runtime_snapshot",
    }
    gdp_mapping_rows = [
        row
        for row in mapping_rows
        if row["current_demand_candidate_source_id"] == "GDP"
    ]
    assert {row["estimate_available"] for row in gdp_mapping_rows} == {"true"}
    assert all(row["diagnostic_coefficient"] for row in gdp_mapping_rows)
    assert all(row["hac_standard_error"] for row in gdp_mapping_rows)
    refresh_backed_mapping_rows = [
        row
        for row in mapping_rows
        if row["current_demand_candidate_source_id"] in {"PCEC", "PCECC96", "DSPI"}
    ]
    assert {row["estimate_available"] for row in refresh_backed_mapping_rows} == {
        "true"
    }
    assert {
        row["estimate_status"] for row in refresh_backed_mapping_rows
    } == {"diagnostic_refresh_bundle_mapping_available_fail_closed"}
    assert all(row["diagnostic_coefficient"] for row in refresh_backed_mapping_rows)
    assert all(row["hac_standard_error"] for row in refresh_backed_mapping_rows)
    assert {
        row["policy_path_100bp_year_normalization_status"]
        for row in refresh_backed_mapping_rows
    } == {"blocked_no_reviewed_policy_path_vector_or_duration_scalar"}
    assert all(
        row["source_snapshot_kind_summary"].endswith(
            ":refresh_bundle_not_current_runtime_snapshot"
        )
        for row in refresh_backed_mapping_rows
    )
    assert {
        row["policy_path_100bp_year_normalization_status"] for row in path_rows
    } == {"blocked_no_reviewed_policy_path_vector_or_duration_scalar"}
    assert all(int(row["source_backing_ledger_row_count"]) > 0 for row in audit_rows)
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "tdsp_current_demand_mapping_admission_fail_closed"
    } == {"pass"}
    expected_release_paths = {
        "outputs/tables/ratewall_tdsp_current_demand_source_review.csv",
        "outputs/tables/ratewall_tdsp_current_demand_unit_conversion.csv",
        "outputs/tables/ratewall_tdsp_current_demand_diagnostic_mapping.csv",
        "outputs/tables/ratewall_tdsp_policy_path_normalization_blocker.csv",
        "outputs/tables/ratewall_tdsp_current_demand_admission_audit.csv",
    }
    assert expected_release_paths <= set(
        release_manifest["artifact_layers"]["assumption_mode"]
    )
    assert all(Path(path).name in public_readme for path in expected_release_paths)
    assert all(Path(path).name in table_plate for path in expected_release_paths)
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_release_paths <= set(archive.namelist())

    guarded_rows = source_rows + conversion_rows + mapping_rows + path_rows + audit_rows
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["demand_drag_conversion_candidate_available"] == "false"
        and row["denominator_prior_update_allowed"] == "false"
        and row["empirical_threshold_claim_enabled"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in guarded_rows
    )


def test_pce_dpi_policy_path_source_acquisition_gate_fails_closed() -> None:
    contract_rows = _read_output_table("ratewall_pce_dpi_source_refresh_contract.csv")
    refresh_rows = _read_output_table(
        "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv"
    )
    policy_rows = _read_output_table(
        "ratewall_policy_path_exposure_vector_design_gate.csv"
    )
    audit_rows = _read_output_table(
        "ratewall_tdsp_pce_dpi_policy_path_admission_audit.csv"
    )
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    ledger_rows = _read_output_table("ratewall_assumption_source_backing_ledger.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    public_readme = Path("outputs/reports/ratewall_public_readme.md").read_text(
        encoding="utf-8"
    )
    table_plate = Path("outputs/reports/ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )

    assert {row["series_id"] for row in contract_rows} == {
        "PCEC",
        "PCECC96",
        "DSPI",
    }
    assert {row["source_registry_status"] for row in contract_rows} == {
        "registry_entry_present"
    }
    assert {row["default_live_series_status"] for row in contract_rows} == {
        "included_in_DEFAULT_SERIES"
    }
    assert {row["current_snapshot_status"] for row in contract_rows} == {
        "missing_from_current_snapshot"
    }
    assert {row["source_refresh_contract_status"] for row in contract_rows} == {
        "source_refresh_contract_materialized_review_only"
    }
    assert {row["source_admission_status"] for row in contract_rows} == {
        "source_refresh_materialized_diagnostic_only_not_current_runtime_snapshot"
    }
    assert {row["refresh_snapshot_status"] for row in contract_rows} == {
        "present_in_refresh_bundle"
    }
    assert {row["refresh_snapshot_validation_status"] for row in contract_rows} == {
        "pass_materialized_source_bundle"
    }
    assert {
        row["series_id"]: int(row["refresh_snapshot_record_count"])
        for row in contract_rows
    } == {"PCEC": 317, "PCECC96": 317, "DSPI": 807}
    assert all(row["refresh_snapshot_first_observation_date"] for row in contract_rows)
    assert all(row["refresh_snapshot_latest_observation_date"] for row in contract_rows)
    assert all(
        len(row["refresh_snapshot_file_sha256"]) == 64 for row in contract_rows
    )
    assert all(
        len(row["refresh_snapshot_records_sha256"]) == 64 for row in contract_rows
    )

    assert len(refresh_rows) == 9
    assert {
        (row["current_demand_candidate_source_id"], row["horizon_bucket"])
        for row in refresh_rows
    } == {
        (series_id, horizon)
        for series_id in {"PCEC", "PCECC96", "DSPI"}
        for horizon in {"3y", "5y", "10y"}
    }
    assert {row["refresh_snapshot_validation_status"] for row in refresh_rows} == {
        "pass_materialized_source_bundle"
    }
    assert {row["estimate_available"] for row in refresh_rows} == {"true"}
    assert {row["estimate_status"] for row in refresh_rows} == {
        "diagnostic_refresh_bundle_mapping_available_fail_closed"
    }
    assert {row["diagnostic_admission_status"] for row in refresh_rows} == {
        "blocked_refresh_diagnostic_mapping_not_conversion_or_promotion"
    }
    assert {
        row["policy_path_100bp_year_normalization_status"] for row in refresh_rows
    } == {"blocked_no_reviewed_policy_path_vector_or_duration_scalar"}

    assert {row["shock_source_id"] for row in policy_rows} == {
        "fed_brw_monetary_policy_shocks",
        "sf_fed_monetary_policy_surprises",
        "romer_romer_2004",
    }
    assert {row["design_gate_status"] for row in policy_rows} == {
        "blocked_scalar_shock_not_policy_path"
    }
    assert {row["policy_path_100bp_year_normalization_status"] for row in policy_rows} == {
        "blocked_no_source_record_policy_path_exposure_vector"
    }
    assert {row["bps_year_exposure_output"] for row in policy_rows} == {""}
    assert all(
        row["source_snapshot_kind_summary"].endswith(":live")
        or row["source_snapshot_kind_summary"].endswith(":converted_source_snapshot")
        for row in policy_rows
    )

    assert len(audit_rows) == len(contract_rows) + len(refresh_rows) + len(policy_rows)
    assert all(int(row["source_backing_ledger_row_count"]) > 0 for row in audit_rows)
    assert {
        row["audited_surface"] for row in audit_rows
    } == {
        "ratewall_pce_dpi_source_refresh_contract.csv",
        "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv",
        "ratewall_policy_path_exposure_vector_design_gate.csv",
    }
    assert {row["source_backing_ledger_classes"] for row in audit_rows} == {
        "blocked_or_diagnostic_only"
    }
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "tdsp_pce_dpi_policy_path_admission_fail_closed"
    } == {"pass"}
    assert {
        row["source_backing_class"]
        for row in ledger_rows
        if row["assumption_family"] == "tdsp_pce_dpi_policy_path_gate"
    } == {"blocked_or_diagnostic_only"}

    expected_release_paths = {
        "outputs/tables/ratewall_pce_dpi_source_refresh_contract.csv",
        "outputs/tables/ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv",
        "outputs/tables/ratewall_policy_path_exposure_vector_design_gate.csv",
        "outputs/tables/ratewall_tdsp_pce_dpi_policy_path_admission_audit.csv",
    }
    assert expected_release_paths <= set(
        release_manifest["artifact_layers"]["assumption_mode"]
    )
    assert all(Path(path).name in public_readme for path in expected_release_paths)
    assert all(Path(path).name in table_plate for path in expected_release_paths)
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_release_paths <= set(archive.namelist())
        assert (
            "data/raw/ratewall_pce_dpi_source_refresh_snapshot.json"
            in set(archive.namelist())
        )

    guarded_rows = contract_rows + refresh_rows + policy_rows + audit_rows
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["demand_drag_conversion_candidate_available"] == "false"
        and row["denominator_prior_update_allowed"] == "false"
        and row["empirical_threshold_claim_enabled"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in guarded_rows
    )


def test_tdsp_diagnostic_family_completion_gate_fails_closed() -> None:
    rows = _read_output_table("ratewall_tdsp_diagnostic_family_completion_gate.csv")
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    public_readme = Path("outputs/reports/ratewall_public_readme.md").read_text(
        encoding="utf-8"
    )
    table_plate = Path("outputs/reports/ratewall_table_plate.md").read_text(
        encoding="utf-8"
    )

    assert len(rows) == 4
    assert {row["diagnostic_family"] for row in rows} == {
        "source_provenance",
        "diagnostic_estimate_family",
        "policy_path_and_conversion",
        "replication_and_promotion",
    }
    assert {row["admission_status"] for row in rows} == {
        "blocked_tdsp_diagnostic_family_completion_gate_not_promotion_grade"
    }
    assert {row["source_review_row_count"] for row in rows} == {"8"}
    assert {row["unit_conversion_row_count"] for row in rows} == {"5"}
    assert {row["original_diagnostic_mapping_row_count"] for row in rows} == {
        "15"
    }
    assert {row["refresh_diagnostic_mapping_row_count"] for row in rows} == {
        "9"
    }
    assert {row["policy_path_blocker_row_count"] for row in rows} == {"3"}
    assert {row["source_backing_audit_row_count"] for row in rows} == {"46"}
    assert {row["estimate_available_count"] for row in rows} == {"15"}
    assert {row["refresh_estimate_available_count"] for row in rows} == {"9"}
    assert {row["source_backing_ledger_covered_count"] for row in rows} == {"46"}
    assert {row["source_snapshot_blocker_count"] for row in rows} == {"3"}
    assert {row["policy_path_blocker_count"] for row in rows} == {"18"}
    assert {row["promotion_switch_violation_count"] for row in rows} == {"0"}
    assert {
        row["policy_path_status"] for row in rows
    } == {"blocked_no_reviewed_policy_path_vector_or_duration_scalar"}
    assert {
        row["current_demand_conversion_status"] for row in rows
    } == {"blocked_no_admitted_tdsp_to_current_demand_gdp_share_conversion"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "tdsp_diagnostic_family_completion_gate_fail_closed"
    } == {"pass"}

    expected_path = (
        "outputs/tables/ratewall_tdsp_diagnostic_family_completion_gate.csv"
    )
    assert expected_path in set(release_manifest["artifact_layers"]["assumption_mode"])
    assert Path(expected_path).name in public_readme
    assert Path(expected_path).name in table_plate
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_path in set(archive.namelist())

    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["demand_drag_conversion_candidate_available"] == "false"
        and row["denominator_prior_update_allowed"] == "false"
        and row["empirical_threshold_claim_enabled"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in rows
    )


def test_tdsp_supported_horizon_response_profile_summarizes_shorter_horizons() -> None:
    rows = _read_output_table("ratewall_tdsp_supported_horizon_response_profile.csv")
    active_rows = _read_output_table("ratewall_active_output_index.csv")

    assert len(rows) == 5
    by_horizon = {row["horizon_bucket"]: row for row in rows}
    assert set(by_horizon) == {"0_1q", "1y", "3y", "5y", "10y"}

    for horizon in ("0_1q", "1y", "3y", "5y"):
        row = by_horizon[horizon]
        assert row["available_response_source_count"] == "2"
        assert row["blocked_response_source_count"] == "1"
        assert row["response_sign_pattern"] == "all_available_sources_positive"
        assert row["supported_horizon_profile_decision"] == (
            "usable_as_supported_horizon_diagnostic_evidence_not_10y_prior"
        )
        assert row["ten_year_admissibility_status"] == (
            "not_10y_horizon_does_not_resolve_registered_10y_window_blocker"
        )

    ten_year = by_horizon["10y"]
    assert ten_year["available_response_source_count"] == "0"
    assert ten_year["blocked_response_source_count"] == "3"
    assert ten_year["supported_horizon_profile_status"] == (
        "blocked_registered_10y_response_profile_unavailable"
    )
    assert ten_year["ten_year_admissibility_status"] == (
        "blocked_10y_pretrend_placebo_and_long_window_robustness_support"
    )

    for row in rows:
        assert row["model_use_status"] == (
            "diagnostic_model_review_only_not_denominator_prior_or_"
            "current_demand_conversion"
        )
        assert row["prior_narrowing_allowed"] == "false"
        assert row["split_denominator_promotion_allowed"] == "false"
        assert row["formula_replacement_allowed"] == "false"
        assert row["main_offset_ratio_changed_this_tranche"] == "false"
        assert row["raw_rate_shock_enabled"] == "false"

    [active] = [
        row
        for row in active_rows
        if row["artifact_path"]
        == "outputs/tables/ratewall_tdsp_supported_horizon_response_profile.csv"
    ]
    assert (
        active["source_status"]
        == "blocked_tdsp_supported_horizon_response_profile_indexed"
    )
    assert active["canonical_ratio_entry"] == "false"
    assert active["paper_use"] == "backend_reference"


def test_policy_path_bps_year_source_protocol_fails_closed() -> None:
    context_rows = _read_output_table(
        "ratewall_policy_path_reviewed_protocol_source_context.csv"
    )
    protocol_rows = _read_output_table(
        "ratewall_policy_path_bps_year_source_protocol.csv"
    )
    candidate_vector_rows = _read_output_table(
        "ratewall_policy_path_event_level_candidate_vector.csv"
    )
    candidate_vector_audit_rows = _read_output_table(
        "ratewall_policy_path_event_level_candidate_vector_audit.csv"
    )
    source_acquisition_rows = _read_output_table(
        "ratewall_policy_path_protocol_source_acquisition_registry.csv"
    )
    source_acquisition_audit_rows = _read_output_table(
        "ratewall_policy_path_protocol_source_acquisition_audit.csv"
    )
    protocol_review_rows = _read_output_table(
        "ratewall_policy_path_protocol_review_inventory.csv"
    )
    protocol_review_audit_rows = _read_output_table(
        "ratewall_policy_path_protocol_review_audit.csv"
    )
    mps_scalar_replication_rows = _read_output_table(
        "ratewall_policy_path_mps_scalar_replication_diagnostic.csv"
    )
    mps_scalar_replication_audit_rows = _read_output_table(
        "ratewall_policy_path_mps_scalar_replication_audit.csv"
    )
    bps_year_blocker_decision_rows = _read_output_table(
        "ratewall_policy_path_bps_year_blocker_decision.csv"
    )
    bps_year_blocker_decision_audit_rows = _read_output_table(
        "ratewall_policy_path_bps_year_blocker_decision_audit.csv"
    )
    policy_rows = _read_output_table(
        "ratewall_policy_path_exposure_vector_design_gate.csv"
    )
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(context_rows) == 1
    context_row = context_rows[0]
    assert context_row["applicable_shock_source_id"] == (
        "sf_fed_monetary_policy_surprises"
    )
    assert context_row["protocol_context_admission_status"] == (
        "blocked_candidate_event_vector_missing_horizon_integral_replication"
    )
    assert context_row["policy_path_100bp_year_normalization_status"] == (
        "blocked_no_source_record_policy_path_exposure_vector"
    )
    assert context_row["bps_year_exposure_output"] == ""
    assert context_row["chart_csv_record_count"] == "102"
    assert context_row["horizon_context"] == (
        "futures contracts covering the next four quarters"
    )
    assert context_row["factor_context"] == (
        "weighted average first principal component of futures-rate changes"
    )
    assert len(context_row["landing_page_sha256"]) == 64
    assert len(context_row["chart_csv_sha256"]) == 64
    assert len(context_row["data_xlsx_sha256"]) == 64

    assert len(source_acquisition_rows) == 11
    assert {row["source_handle"] for row in source_acquisition_rows} == {
        "sf_fed_usmpd",
        "fed_sofr_continuity",
        "acosta_sofr_gss_updates",
    }
    assert {
        row["artifact_handle"] for row in source_acquisition_rows
    } == {
        "sf_fed_usmpd_landing_page",
        "sf_fed_usmpd_xlsx",
        "sf_fed_usmpd_monetary_policy_surprises_zip",
        "sf_fed_usmpd_chart1_csv",
        "sf_fed_usmpd_chart2_csv",
        "fed_sofr_continuity_landing_page",
        "fed_sofr_continuity_pdf",
        "fed_sofr_continuity_accessible_zip",
        "acosta_research_page",
        "acosta_dataverse_metadata_json",
        "acosta_abj_2024_monetary_policy_surprises_xlsx",
    }
    assert all(len(row["sha256"]) == 64 for row in source_acquisition_rows)
    assert all(int(row["file_size_bytes"]) > 0 for row in source_acquisition_rows)
    assert {row["parse_status"] for row in source_acquisition_rows} == {
        "blocked_not_parsed_for_bps_year_protocol"
    }
    assert {row["source_admission_status"] for row in source_acquisition_rows} == {
        "blocked_raw_protocol_source_artifact_review_only"
    }
    assert len(source_acquisition_audit_rows) == 3
    assert {row["audit_status"] for row in source_acquisition_audit_rows} == {
        "pass_acquired_raw_protocol_sources_fail_closed"
    }
    for row in source_acquisition_rows:
        assert row["bps_year_exposure_output"] == ""
        assert row["candidate_gdp_share_drag_per_100bp_year"] == ""
        assert row["denominator_prior_update_allowed"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        assert row["canonical_ratio_entry"] == "false"
        assert row["pricing_output_enabled"] == "false"
        assert row["holder_allocation_enabled"] == "false"
        assert row["raw_rate_shock_enabled"] == "false"

    assert len(protocol_review_rows) == 13
    assert {row["source_handle"] for row in protocol_review_rows} == {
        "sf_fed_usmpd",
        "fed_sofr_continuity",
        "acosta_sofr_gss_updates",
    }
    assert {
        row["review_field_name"] for row in protocol_review_rows
    } >= {
        "mps_percentage_point_units_and_y1_normalization",
        "mps_r_selected_variables",
        "sofr_switch_date_recommendation",
        "sofr_eurodollar_contract_substitution",
        "updated_gss_ns_factor_series",
    }
    assert {
        row["protocol_admission_status"] for row in protocol_review_rows
    } == {"blocked_reviewed_context_missing_bps_year_admission_fields"}
    assert any(
        row["unit_conversion_review_status"].startswith("reviewed_")
        for row in protocol_review_rows
    )
    assert all(
        row["current_protocol_value"] == ""
        and row["bps_year_exposure_output"] == ""
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["denominator_prior_update_allowed"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["holder_allocation_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in protocol_review_rows
    )
    assert len(protocol_review_audit_rows) == 3
    assert {row["audit_status"] for row in protocol_review_audit_rows} == {
        "pass_protocol_review_inventory_fail_closed"
    }

    assert len(mps_scalar_replication_rows) == 4
    assert {row["replication_target"] for row in mps_scalar_replication_rows} == {
        "STMT",
        "PC",
        "ME",
        "MIN",
    }
    assert {
        row["replication_status"] for row in mps_scalar_replication_rows
    } == {"pass_scalar_mps_replication_within_tolerance"}
    assert {
        row["loadings_back_transform_status"]
        for row in mps_scalar_replication_rows
    } == {"blocked_no_reviewed_loadings_back_transform"}
    assert {
        row["event_date_horizon_weight_status"]
        for row in mps_scalar_replication_rows
    } == {"blocked_no_reviewed_event_date_horizon_weights"}
    assert {
        row["protocol_admission_status"] for row in mps_scalar_replication_rows
    } == {"blocked_scalar_replication_not_bps_year_protocol"}
    assert all(
        row["current_protocol_value"] == ""
        and row["bps_year_exposure_output"] == ""
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["denominator_prior_update_allowed"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["holder_allocation_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in mps_scalar_replication_rows
    )
    assert len(mps_scalar_replication_audit_rows) == 1
    assert {
        row["audit_status"] for row in mps_scalar_replication_audit_rows
    } == {"pass_mps_scalar_replication_diagnostic_fail_closed"}

    assert len(bps_year_blocker_decision_rows) == 5
    assert {
        row["required_bridge_field"] for row in bps_year_blocker_decision_rows
    } == {
        "loadings_back_transform",
        "event_date_horizon_weights",
        "factor_loadings_and_horizon_back_transform",
        "sofr_eurodollar_horizon_weight_mapping",
        "admitted_bps_year_policy_path_protocol",
    }
    assert {
        row["bps_year_route_decision"] for row in bps_year_blocker_decision_rows
    } == {"terminal_blocked_scalar_replication_not_bps_year_path"}
    assert {
        row["reviewed_bridge_evidence_status"]
        for row in bps_year_blocker_decision_rows
    } == {
        "blocked_scalar_code_outputs_mps_only_no_loadings_back_transform",
        "blocked_workbook_schema_has_instruments_without_horizon_weights",
        "blocked_factor_series_scaled_outputs_no_loadings_or_weights",
        "blocked_sofr_substitution_context_not_bps_year_weights",
        "terminal_blocked_no_reviewed_bps_year_bridge_in_local_sources",
    }
    assert {
        row["next_backend_action"] for row in bps_year_blocker_decision_rows
    } == {"pivot_to_reviewed_research_parameterization_contract_source"}
    assert all(
        row["current_protocol_value"] == ""
        and row["bps_year_exposure_output"] == ""
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["denominator_prior_update_allowed"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["holder_allocation_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in bps_year_blocker_decision_rows
    )
    assert len(bps_year_blocker_decision_audit_rows) == 1
    assert {
        row["audit_status"] for row in bps_year_blocker_decision_audit_rows
    } == {"pass_bps_year_blocker_decision_fail_closed"}

    assert len(candidate_vector_rows) == 4104
    assert {row["instrument_column"] for row in candidate_vector_rows} == {
        "FF1",
        "FF2",
        "ED1",
        "ED2",
        "ED3",
        "ED4",
    }
    candidate_by_vintage = {}
    for row in candidate_vector_audit_rows:
        candidate_by_vintage[row["source_sheet_vintage"]] = row
    assert {
        vintage: row["event_row_count"]
        for vintage, row in candidate_by_vintage.items()
    } == {
        "update_2023": "361",
        "original": "323",
    }
    assert {
        vintage: row["last_event_date"]
        for vintage, row in candidate_by_vintage.items()
    } == {
        "update_2023": "2023-12-13",
        "original": "2019-12-11",
    }
    assert all(
        row["policy_rate_bps_exposure"] == ""
        and row["bps_year_component"] == ""
        and row["bps_year_exposure_output"] == ""
        and row["horizon_weight_years"] == ""
        and row["replication_status"] == "blocked_no_independent_replication"
        and row["candidate_vector_extraction_status"]
        in {
            "pass_source_workbook_cell_extracted",
            "blocked_source_value_missing_or_na",
        }
        for row in candidate_vector_rows
    )
    assert any(
        row["instrument_column"] in {"FF1", "FF2"}
        and row["source_reported_value_raw"] == "NA"
        and row["candidate_value_available"] == "false"
        and row["candidate_policy_rate_change_value"] == ""
        for row in candidate_vector_rows
    )

    assert len(protocol_rows) == 24
    assert {row["shock_source_id"] for row in protocol_rows} == {
        row["shock_source_id"] for row in policy_rows
    }
    assert {row["required_protocol_field_name"] for row in protocol_rows} == {
        "event_identifier_and_date",
        "horizon_month_grid",
        "policy_rate_bps_exposure_vector",
        "bps_year_integral",
        "scalar_to_path_construction_method",
        "target_path_factor_source",
        "replication_validation",
        "provenance_manifest",
    }
    assert {
        row["source_backing_admission_status"] for row in protocol_rows
    } == {
        "blocked_no_source_backed_protocol_value",
        "blocked_partial_reviewed_source_context_missing_bps_year_vector",
        "blocked_candidate_vector_not_reviewed_bps_year_protocol",
    }
    sf_fed_context_fields = {
        row["required_protocol_field_name"]: row
        for row in protocol_rows
        if row["shock_source_id"] == "sf_fed_monetary_policy_surprises"
        and row["current_source_artifact"]
    }
    assert set(sf_fed_context_fields) == {
        "event_identifier_and_date",
        "horizon_month_grid",
        "policy_rate_bps_exposure_vector",
        "scalar_to_path_construction_method",
        "target_path_factor_source",
        "provenance_manifest",
    }
    assert {
        row["source_admission_status"] for row in sf_fed_context_fields.values()
    } == {
        "blocked_candidate_event_vector_not_reviewed_bps_year_protocol",
        "blocked_policy_path_context_not_event_level_bps_year_protocol",
    }
    assert {row["protocol_admission_status"] for row in protocol_rows} == {
        "blocked_required_protocol_field_missing",
        "blocked_candidate_vector_missing_unit_horizon_integral_replication",
    }
    assert {row["bps_year_exposure_output"] for row in protocol_rows} == {""}
    assert {
        row["policy_path_100bp_year_normalization_status"]
        for row in protocol_rows
    } == {"blocked_no_source_record_policy_path_exposure_vector"}
    assert {
        row["claim_boundary"] for row in protocol_rows
    } == {"policy_path_bps_year_source_protocol_not_prior_narrowing_or_raw_rate_shock"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "policy_path_reviewed_protocol_source_context_fail_closed"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "policy_path_protocol_source_acquisition_fail_closed"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "policy_path_protocol_review_inventory_fail_closed"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"]
        == "policy_path_mps_scalar_replication_diagnostic_fail_closed"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "policy_path_bps_year_blocker_decision_fail_closed"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "policy_path_event_level_candidate_vector_fail_closed"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "policy_path_bps_year_source_protocol_fail_closed"
    } == {"pass"}
    assert (
        "outputs/tables/ratewall_policy_path_reviewed_protocol_source_context.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_protocol_source_acquisition_registry.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_protocol_source_acquisition_audit.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_protocol_review_inventory.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_protocol_review_audit.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_mps_scalar_replication_diagnostic.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_mps_scalar_replication_audit.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_bps_year_blocker_decision.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_bps_year_blocker_decision_audit.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_event_level_candidate_vector.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_event_level_candidate_vector_audit.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_bps_year_source_protocol.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert (
            "outputs/tables/ratewall_policy_path_bps_year_source_protocol.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_reviewed_protocol_source_context.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_protocol_source_acquisition_registry.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_protocol_source_acquisition_audit.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_protocol_review_inventory.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_protocol_review_audit.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_mps_scalar_replication_diagnostic.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_mps_scalar_replication_audit.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_bps_year_blocker_decision.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_bps_year_blocker_decision_audit.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_event_level_candidate_vector.csv"
            in set(archive.namelist())
        )
        assert (
            "outputs/tables/ratewall_policy_path_event_level_candidate_vector_audit.csv"
            in set(archive.namelist())
        )
        assert (
            "data/raw/policy_path_protocol_sources/"
            "sf_fed_monetary_policy_surprises_candidate_event_vector.csv"
            in set(archive.namelist())
        )
        assert (
            "data/raw/policy_path_protocol_sources/"
            "sf_fed_monetary_policy_surprises_protocol_context_manifest.json"
            in set(archive.namelist())
        )
        assert (
            "data/raw/policy_path_protocol_sources/"
            "sf_fed_monetary_policy_surprises_workbook_schema_manifest.json"
            in set(archive.namelist())
        )
        assert (
            "data/raw/policy_path_protocol_sources/"
            "policy_path_protocol_source_acquisition_manifest.json"
            in set(archive.namelist())
        )
        assert (
            "data/raw/policy_path_protocol_sources/"
            "policy_path_protocol_review_inventory.csv"
            in set(archive.namelist())
        )
        assert (
            "data/raw/policy_path_protocol_sources/"
            "usmpd_mps_scalar_replication_diagnostic.csv"
            in set(archive.namelist())
        )
        assert (
            "data/raw/policy_path_protocol_sources/"
            "policy_path_bps_year_blocker_decision.csv"
            in set(archive.namelist())
        )
        assert (
            "data/raw/policy_path_protocol_sources/sf_fed_usmpd.xlsx"
            in set(archive.namelist())
        )
        assert (
            "data/raw/policy_path_protocol_sources/"
            "acosta_abj_2024_monetary_policy_surprises.xlsx"
            in set(archive.namelist())
        )
    assert all(
        row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["demand_drag_conversion_candidate_available"] == "false"
        and row["denominator_prior_update_allowed"] == "false"
        and row["empirical_threshold_claim_enabled"] == "false"
        and row["enters_main_ratio"] == "false"
        and row["evidence_mode_enabled"] == "false"
        and row["canonical_ratio_entry"] == "false"
        and row["prior_narrowing_allowed"] == "false"
        and row["split_denominator_promotion_allowed"] == "false"
        and row["formula_replacement_allowed"] == "false"
        and row["pricing_output_enabled"] == "false"
        and row["raw_rate_shock_enabled"] == "false"
        for row in context_rows + protocol_rows + candidate_vector_rows
    )


def test_policy_path_normalization_review_fails_closed() -> None:
    candidate_rows = _read_output_table(
        "ratewall_policy_path_event_level_candidate_vector.csv"
    )
    scalar_rows = _read_output_table(
        "ratewall_policy_path_mps_scalar_replication_diagnostic.csv"
    )
    manifest_rows = _read_output_table(
        "ratewall_policy_path_normalization_source_manifest.csv"
    )
    review_rows = _read_output_table(
        "ratewall_policy_path_bps_year_normalization_review.csv"
    )
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    formula_steps = {
        "source_cell_or_scalar_extraction",
        "source_unit_review",
        "event_date_contract_interval",
        "horizon_weight_year_fraction",
        "bps_year_integration_formula",
        "independent_replication",
    }

    assert len(manifest_rows) == 7
    assert len(review_rows) == (len(candidate_rows) + len(scalar_rows)) * len(
        formula_steps
    )
    assert {row["formula_step"] for row in review_rows} == formula_steps
    assert {row["source_family"] for row in review_rows} == {
        "sf_fed_fomc_futures_candidate_vector",
        "sf_fed_usmpd_scalar_mps",
    }
    assert {
        row["admission_status"]
        for row in review_rows
        if row["source_family"] == "sf_fed_usmpd_scalar_mps"
    } == {"blocked_scalar_factor_not_bps_year_policy_path"}
    review_by_source_step = {
        (row["source_row_id"], row["formula_step"]): row
        for row in review_rows
        if row["source_family"] == "sf_fed_fomc_futures_candidate_vector"
    }
    ed1_1988 = next(
        row
        for row in candidate_rows
        if row["event_date"] == "1988-02-04" and row["instrument_code"] == "ED1"
    )
    ed1_1988_interval = review_by_source_step[
        (ed1_1988["candidate_vector_row_id"], "event_date_contract_interval")
    ]
    assert ed1_1988_interval["contract_horizon_start_date"] == "1988-03-16"
    assert ed1_1988_interval["contract_horizon_end_date"] == "1988-06-14"
    assert ed1_1988_interval["horizon_days"] == "91"
    ed1_2023 = next(
        row
        for row in candidate_rows
        if row["event_date"] == "2023-12-13" and row["instrument_code"] == "ED1"
    )
    ed1_2023_interval = review_by_source_step[
        (ed1_2023["candidate_vector_row_id"], "event_date_contract_interval")
    ]
    assert ed1_2023_interval["contract_horizon_start_date"] == "2023-09-20"
    assert ed1_2023_interval["contract_horizon_end_date"] == "2023-12-19"
    assert ed1_2023_interval["horizon_days"] == "7"
    assert all(
        row["candidate_bps_year_component"] == ""
        and row["candidate_bps_year_exposure"] == ""
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["protocol_admission_status"].startswith("blocked_")
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in manifest_rows
    )
    assert all(
        row["rate_change_bps"] == ""
        and row["candidate_bps_year_component"] == ""
        and row["candidate_bps_year_exposure"] == ""
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["admission_status"].startswith("blocked_")
        and row["protocol_admission_status"].startswith("blocked_")
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in review_rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "policy_path_normalization_source_manifest_fail_closed"
    } == {"pass"}
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "policy_path_bps_year_normalization_review_fail_closed"
    } == {"pass"}
    assert (
        "outputs/tables/ratewall_policy_path_normalization_source_manifest.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    assert (
        "outputs/tables/ratewall_policy_path_bps_year_normalization_review.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        names = set(archive.namelist())
        assert (
            "outputs/tables/ratewall_policy_path_normalization_source_manifest.csv"
            in names
        )
        assert (
            "outputs/tables/ratewall_policy_path_bps_year_normalization_review.csv"
            in names
        )


def test_policy_path_bps_year_protocol_closure_prevents_shortcuts() -> None:
    unit_rows = _read_output_table(
        "ratewall_policy_path_source_cell_unit_contract_review.csv"
    )
    closure_rows = _read_output_table(
        "ratewall_policy_path_bps_year_protocol_closure.csv"
    )
    leak_rows = _read_output_table("ratewall_policy_path_normalization_leak_audit.csv")
    contract_rows = _read_output_table(
        "ratewall_policy_path_contract_interval_source_review.csv"
    )
    scalar_rows = _read_output_table(
        "ratewall_policy_path_mps_scalar_replication_diagnostic.csv"
    )
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(unit_rows) == 64
    assert {row["required_unit_claim"] for row in unit_rows} == {
        "source_workbook_cell_unit",
        "source_workbook_cell_sign",
        "official_quote_rule_context",
        "contract_interval_context",
    }
    assert {row["source_instrument_code"] for row in unit_rows} == {
        "FF1",
        "FF2",
        "ED1",
        "ED2",
        "ED3",
        "ED4",
    }
    assert all(row["source_artifact_path"] for row in unit_rows)
    assert all(len(row["source_artifact_sha256"]) == 64 for row in unit_rows)
    assert all(
        row["quote_rule_review_status"]
        == "pass_official_quote_rule_metadata_hashed"
        and row["source_cell_unit_admission_status"]
        == "blocked_no_reviewed_source_cell_unit_conversion"
        and row["rate_to_price_sign_admission_status"]
        == "blocked_quote_rule_metadata_not_runtime_sign_rule"
        and row["candidate_rate_change_bps"] == ""
        and row["candidate_bps_year_component"] == ""
        and row["candidate_bps_year_exposure"] == ""
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in unit_rows
    )

    assert {row["admission_gate"] for row in closure_rows} == {
        "source_cell_unit_contract",
        "rate_to_price_sign_contract",
        "event_date_horizon_weight_protocol",
        "factor_loading_or_back_transform_protocol",
        "bps_year_integral_formula",
        "independent_bps_year_replication_target",
        "promotion_rule",
        "denominator_isolation",
    }
    assert {row["formula_step"] for row in closure_rows} == {
        "source_cell_or_scalar_extraction",
        "source_unit_review",
        "event_date_contract_interval",
        "horizon_weight_year_fraction",
        "bps_year_integration_formula",
        "independent_replication",
    }
    assert all(
        row["admit_bps_year_path"] == "false"
        and row["protocol_closure_status"]
        == "blocked_missing_complete_bps_year_protocol"
        and row["candidate_rate_change_bps"] == ""
        and row["candidate_bps_year_component"] == ""
        and row["candidate_bps_year_exposure"] == ""
        and row["bps_year_exposure_output"] == ""
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in closure_rows
    )

    assert leak_rows
    assert all(row["audit_status"] == "pass" for row in leak_rows)
    assert all(row["observed_violation_count"] == "0" for row in leak_rows)
    assert {
        row["leak_rule"]
        for row in leak_rows
        if row["field_name"] == "source_cell_unit_admission_status"
    } == {"cme_quote_rules_cannot_admit_sf_fed_source_cell_units"}
    assert {
        row["leak_rule"]
        for row in leak_rows
        if row["field_name"] == "policy_path_100bp_year_normalization_status"
    } == {"scalar_mps_replication_cannot_admit_bps_year_path"}
    assert all(
        not (
            row["instrument_family"]
            in {"eurodollar_futures", "sofr_futures_source_labeled_ed_columns"}
            and row["reference_period_start"].endswith(
                ("-01-01", "-04-01", "-07-01", "-10-01")
            )
        )
        for row in contract_rows
    )
    assert all(
        not row["protocol_admission_status"].startswith("pass_")
        and not row["policy_path_100bp_year_normalization_status"].startswith(
            "pass_"
        )
        for row in scalar_rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"]
        in {
            "policy_path_source_cell_unit_contract_review_fail_closed",
            "policy_path_bps_year_protocol_closure_fail_closed",
            "policy_path_normalization_leak_audit_fail_closed",
        }
    } == {"pass"}
    for artifact in [
        "outputs/tables/ratewall_policy_path_source_cell_unit_contract_review.csv",
        "outputs/tables/ratewall_policy_path_bps_year_protocol_closure.csv",
        "outputs/tables/ratewall_policy_path_normalization_leak_audit.csv",
    ]:
        assert artifact in set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        names = set(archive.namelist())
        for artifact in [
            "outputs/tables/ratewall_policy_path_source_cell_unit_contract_review.csv",
            "outputs/tables/ratewall_policy_path_bps_year_protocol_closure.csv",
            "outputs/tables/ratewall_policy_path_normalization_leak_audit.csv",
        ]:
            assert artifact in names


def test_policy_path_contract_interval_review_preserves_na_and_fails_closed() -> None:
    candidate_rows = _read_output_table(
        "ratewall_policy_path_event_level_candidate_vector.csv"
    )
    contract_rows = _read_output_table(
        "ratewall_policy_path_contract_interval_source_review.csv"
    )
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    raw_manifest = json.loads(
        Path(
            "data/raw/policy_path_contract_interval_sources/"
            "contract_interval_source_acquisition_manifest.json"
        ).read_text(encoding="utf-8")
    )

    assert len(contract_rows) == len(candidate_rows) == 4104
    assert raw_manifest["output_row_count"] == len(contract_rows)
    assert {row["candidate_instrument_code"] for row in contract_rows} == {
        "FF1",
        "FF2",
        "ED1",
        "ED2",
        "ED3",
        "ED4",
    }
    literal_na_rows = [
        row for row in contract_rows if row["literal_na_status"] == "source_literal_na"
    ]
    assert literal_na_rows
    assert all(row["source_cell_value_numeric"] == "" for row in literal_na_rows)
    assert all(row["official_spec_artifact_path"] for row in contract_rows)
    assert all(len(row["official_spec_artifact_sha256"]) == 64 for row in contract_rows)
    assert {
        row["official_spec_acquisition_status"] for row in contract_rows
    } == {"pass_official_spec_artifact_hashed"}
    contract_by_event_instrument = {
        (row["event_date"], row["candidate_instrument_code"]): row
        for row in contract_rows
    }
    assert contract_by_event_instrument[("1988-02-04", "FF1")][
        "candidate_delivery_month"
    ] == "1988-02"
    assert contract_by_event_instrument[("1988-02-04", "FF2")][
        "candidate_delivery_month"
    ] == "1988-03"
    ed1_1988 = contract_by_event_instrument[("1988-02-04", "ED1")]
    assert ed1_1988["candidate_delivery_month"] == "1988-03"
    assert ed1_1988["reference_period_start"] == "1988-03-16"
    assert ed1_1988["reference_period_end"] == "1988-06-14"
    assert (
        ed1_1988["delivery_month_selection_rule_status"]
        == "eurodollar_imm_third_wednesday_delivery_context_reviewed_not_admitted_mapping"
    )
    assert (
        ed1_1988["candidate_interval_weight_status"]
        == "eurodollar_imm_term_context_metadata_only_not_bps_year_weight"
    )
    assert ed1_1988["reference_period_start"] != "1988-01-01"
    ed1_2023 = contract_by_event_instrument[("2023-12-13", "ED1")]
    assert ed1_2023["candidate_delivery_month"] == "2023-12"
    assert ed1_2023["reference_period_start"] == "2023-09-20"
    assert ed1_2023["reference_period_end"] == "2023-12-19"
    assert (
        ed1_2023["delivery_month_selection_rule_status"]
        == "sofr_chapter_460_reference_quarter_third_wednesday_rule_reviewed_not_admitted_mapping"
    )
    assert (
        ed1_2023["candidate_interval_weight_status"]
        == "sofr_reference_quarter_metadata_only_not_bps_year_weight"
    )
    assert all(
        row["policy_rate_bps_exposure"] == ""
        and row["bps_year_component"] == ""
        and row["bps_year_exposure_output"] == ""
        and row["candidate_gdp_share_drag_per_100bp_year"] == ""
        and row["protocol_admission_status"]
        == "blocked_contract_interval_review_not_bps_year_protocol"
        and all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in contract_rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"] == "policy_path_contract_interval_source_review_fail_closed"
    } == {"pass"}
    assert (
        "outputs/tables/ratewall_policy_path_contract_interval_source_review.csv"
        in set(release_manifest["artifact_layers"]["assumption_mode"])
    )
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        names = set(archive.namelist())
        assert (
            "outputs/tables/ratewall_policy_path_contract_interval_source_review.csv"
            in names
        )
        assert (
            "data/raw/policy_path_contract_interval_sources/"
            "contract_interval_source_acquisition_manifest.json"
            in names
        )


def test_policy_path_contract_spec_acquisition_blocker_fails_closed() -> None:
    rows = _read_output_table("ratewall_policy_path_contract_spec_acquisition_blocker.csv")
    invariant_rows = _read_output_table(
        "ratewall_assumption_source_backing_invariant_audit.csv"
    )
    release_manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert {row["artifact_handle"] for row in rows} == {
        "cme_cbot_chapter_22_fed_funds_pdf",
        "cme_chapter_460_sofr_pdf",
        "cme_eurodollar_futures_foundational_concepts_pdf",
    }
    assert all(row["local_artifact_path"] for row in rows)
    assert all(len(row["local_artifact_sha256"]) == 64 for row in rows)
    assert all(
        row["fallback_path_status"]
        == "pass_reproducible_official_spec_artifact_hash_present"
        for row in rows
    )
    assert sum(int(row["covered_candidate_row_count"]) for row in rows) == 4104
    assert all(
        all(
            row[field] == "false"
            for field in SOURCE_ACQUISITION_FORBIDDEN_SWITCH_FIELDS
        )
        for row in rows
    )
    assert {
        row["audit_status"]
        for row in invariant_rows
        if row["audit_item"]
        == "policy_path_contract_spec_acquisition_blocker_fail_closed"
    } == {"pass"}
    expected_path = (
        "outputs/tables/ratewall_policy_path_contract_spec_acquisition_blocker.csv"
    )
    assert expected_path in set(release_manifest["artifact_layers"]["assumption_mode"])
    with zipfile.ZipFile(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    ) as archive:
        assert expected_path in set(archive.namelist())


def test_interest_income_mpc_calibration_registries_are_assumption_only() -> None:
    registry_rows = _read_output_table(
        "ratewall_interest_income_mpc_calibration_registry.csv"
    )
    proxy_rows = _read_output_table("ratewall_interest_income_public_proxy_catalog.csv")
    range_rows = _read_output_table("ratewall_interest_income_proxy_range_registry.csv")
    boundary_rows = _read_output_table(
        "ratewall_interest_income_claim_boundary_audit.csv"
    )

    assert len(registry_rows) == 7
    assert len(proxy_rows) == 6
    assert len(range_rows) == 7
    assert len(boundary_rows) == 72
    assert {
        "rba_la_cava_household_cash_flow_channel_lender_interest",
        "boe_nmg_savings_interest_spending_response",
        "baker_nagel_wurgler_dividend_consumption",
        "di_maggio_kermani_majlesi_stock_returns_consumption",
    } <= {row["source_id"] for row in registry_rows}
    assert {
        row["claim_boundary"] for row in registry_rows + proxy_rows + range_rows
    } == {"interest_income_mpc_calibration_assumption_only_not_empirical_output"}
    for row in registry_rows:
        assert row["assumption_mode_allowed"] == "true"
        assert row["evidence_mode_enabled"] == "false"
        assert row["mpc_output_enabled"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["can_change_parameter_pack"] == "false"
        assert row["citation_short"]
        assert row["source_url"].startswith("https://")
        assert row["boundary_note"]
    for row in proxy_rows:
        assert row["causal_estimation_allowed"] == "false"
        assert row["assumption_mode_only"] == "true"
        assert row["evidence_gate_status"] == (
            "fail_closed_public_proxy_not_evidence_mode"
        )
        assert row["source_url"].startswith("https://")
    for row in range_rows:
        assert row["allowed_for_assumption_mode"] == "true"
        assert row["disallowed_for_evidence_mode"] == "true"
        assert row["mpc_output_enabled"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["can_change_parameter_pack"] == "false"
    assert {row["status"] for row in boundary_rows} == {"pass"}


def test_post_covid_interest_income_wall_distance_is_secondary_diagnostic() -> None:
    rows = _read_output_table("ratewall_post_covid_interest_income_wall_distance.csv")
    solved_by_assumption = {
        row["assumption_set"]: row
        for row in _read_output_table("ratewall_wall_hit_scenarios.csv")
    }

    assert len(rows) == 24
    assert {row["calibration_band"] for row in rows} == {
        "low",
        "base",
        "high",
        "stress_upper_bound_not_realistic",
    }
    assert {row["canonical_wall_hit_label_preserved"] for row in rows} == {"true"}
    assert {row["secondary_ratio_not_classifier"] for row in rows} == {"true"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["mpc_output_enabled"] for row in rows} == {"false"}
    assert {row["claim_boundary"] for row in rows} == {
        "post_covid_interest_income_wall_distance_assumption_mode_proxy_not_empirical_mpc"
    }
    stress_rows = [
        row for row in rows if row["calibration_band"] == "stress_upper_bound_not_realistic"
    ]
    assert len(stress_rows) == 6
    assert {
        row["calibration_confidence_label"] for row in stress_rows
    } == {"low_for_interest"}
    for row in rows:
        solved = solved_by_assumption[row["assumption_set"]]
        assert row["canonical_ratewall_offset_ratio"] == solved["ratewall_offset_ratio"]
        assert (
            row["canonical_wall_hit_under_assumptions"]
            == solved["wall_hit_under_assumptions"]
        )
        private_cashflow = Decimal(
            row["interest_income_available_for_current_spending_bil"]
        )
        spend_share = Decimal(row["interest_income_current_spend_share_assumption"])
        existing_offset = Decimal(row["existing_interest_demand_offset_bil"])
        canonical_countervailing = Decimal(row["scalar_countervailing_total_bil"])
        denominator = Decimal(row["conventional_contractionary_effect_bil"])
        expected_offset = private_cashflow * spend_share
        expected_countervailing = max(
            Decimal("0"),
            canonical_countervailing - existing_offset + expected_offset,
        )
        expected_ratio = (
            Decimal("0")
            if denominator == 0
            else expected_countervailing / denominator
        )
        assert Decimal(row["calibrated_interest_current_spend_offset_bil"]) == (
            expected_offset
        )
        assert abs(
            Decimal(row["calibrated_secondary_ratewall_offset_ratio"])
            - expected_ratio
        ) < Decimal("1e-24")
        assert row["secondary_wall_hit_under_calibrated_interest_share"] == str(
            expected_ratio >= Decimal("1")
        ).lower()


def test_historical_iorb_demand_proxy_path_is_assumption_only_time_series() -> None:
    rows = _read_output_table("ratewall_historical_iorb_demand_proxy_path.csv")

    assert rows
    assert {row["demand_conversion_case"] for row in rows} == {
        "low_bank_behavior_proxy",
        "base_bank_behavior_proxy",
        "high_bank_behavior_proxy",
    }
    assert {row["iorb_recipient_demand_share_assumption"] for row in rows} == {
        "0.02",
        "0.06",
        "0.20",
    }
    assert min(row["quarter"] for row in rows) == "2021Q3"
    assert max(row["quarter"] for row in rows) >= "2026Q2"
    assert {row["iorb_rate_proxy_source"] for row in rows} == {"IORB"}
    assert {row["exact_iorb_rate_available"] for row in rows} == {"true"}
    assert {row["mechanical_iorb_cashflow_status"] for row in rows} == {
        "source_backed_mechanical_cashflow_input"
    }
    assert {row["demand_channel_status"] for row in rows} == {
        "assumption_mode_bank_behavior_proxy_not_incidence"
    }
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["mpc_output_enabled"] for row in rows} == {"false"}
    assert {row["claim_boundary"] for row in rows} == {
        "historical_iorb_demand_proxy_not_evidence_mode_not_mpc_output"
    }
    for row in rows:
        reserves = Decimal(row["reserve_balance_avg_bil"])
        rate = Decimal(row["iorb_rate_proxy_pct"])
        gdp = Decimal(row["nominal_gdp_bil"])
        share = Decimal(row["iorb_recipient_demand_share_assumption"])
        cashflow = reserves * rate / Decimal("100")
        offset = cashflow * share
        assert Decimal(row["annualized_iorb_cashflow_bil"]) == cashflow
        assert Decimal(row["iorb_demand_offset_bil"]) == offset
        assert Decimal(row["iorb_cashflow_gdp_share"]) == cashflow / gdp
        assert Decimal(row["iorb_demand_offset_gdp_share"]) == offset / gdp


def test_historical_wall_ratio_path_uses_source_backed_iorb_and_assumptions() -> None:
    rows = _read_output_table("ratewall_historical_wall_ratio_path.csv")

    assert rows
    assert {row["calibration_band"] for row in rows} == {"low", "base", "high"}
    assert {row["baseline_quarter"] for row in rows} == {"2021Q4"}
    assert min(row["quarter"] for row in rows) == "2021Q4"
    assert max(row["quarter"] for row in rows) >= "2026Q2"
    assert {row["mechanical_iorb_cashflow_canonical_input"] for row in rows} == {
        "true"
    }
    assert {row["canonical_formula_identity_applied"] for row in rows} == {"true"}
    assert {row["canonical_solved_output_replaced"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["mpc_output_enabled"] for row in rows} == {"false"}
    assert {row["claim_boundary"] for row in rows} == {
        "historical_wall_ratio_path_assumption_mode_not_evidence_mode"
    }
    for row in rows:
        reserves = Decimal(row["reserve_balance_avg_bil"])
        rate = Decimal(row["iorb_rate_pct"])
        baseline_rate = Decimal(row["baseline_iorb_rate_pct"])
        baseline_cashflow = Decimal(row["baseline_annualized_iorb_cashflow_bil"])
        personal_interest = Decimal(row["personal_interest_income_saar_bil"])
        baseline_personal_interest = Decimal(
            row["baseline_personal_interest_income_saar_bil"]
        )
        interest_share = Decimal(
            row["interest_income_current_spend_share_assumption"]
        )
        iorb_share = Decimal(row["iorb_bank_behavior_share_assumption"])
        gdp = Decimal(row["nominal_gdp_bil"])
        drag_share = Decimal(row["contractionary_drag_gdp_share_assumption"])
        cashflow = reserves * rate / Decimal("100")
        incremental_iorb = max(cashflow - baseline_cashflow, Decimal("0"))
        incremental_personal_interest = max(
            personal_interest - baseline_personal_interest,
            Decimal("0"),
        )
        personal_offset = incremental_personal_interest * interest_share
        iorb_offset = incremental_iorb * iorb_share
        countervailing = personal_offset + iorb_offset
        conventional_drag = gdp * drag_share * max(
            rate - baseline_rate, Decimal("0")
        )
        expected_ratio = (
            Decimal("0")
            if conventional_drag == 0
            else countervailing / conventional_drag
        )
        assert Decimal(row["annualized_iorb_cashflow_bil"]) == cashflow
        assert Decimal(row["incremental_iorb_cashflow_bil"]) == incremental_iorb
        assert Decimal(row["incremental_personal_interest_income_saar_bil"]) == (
            incremental_personal_interest
        )
        assert Decimal(row["personal_interest_current_spend_offset_bil"]) == (
            personal_offset
        )
        assert Decimal(row["iorb_bank_behavior_demand_offset_bil"]) == iorb_offset
        assert Decimal(row["historical_countervailing_total_proxy_bil"]) == (
            countervailing
        )
        assert Decimal(row["conventional_drag_proxy_bil"]) == conventional_drag
        assert abs(Decimal(row["historical_wall_ratio"]) - expected_ratio) < Decimal(
            "1e-24"
        )


def test_historical_assumption_mode_wall_ratio_path_spans_available_history() -> None:
    rows = _read_output_table("ratewall_historical_assumption_mode_wall_ratio_path.csv")

    assert rows
    assert min(row["quarter"] for row in rows) == "1960Q1"
    assert "base_current_100bps" in {row["assumption_set"] for row in rows}
    assert "marginal_wall_hit_treasury_conversion" in {
        row["assumption_set"] for row in rows
    }
    assert {row["historical_ratio_not_classifier"] for row in rows} == {"true"}
    assert {row["canonical_solved_output_replaced"] for row in rows} == {"false"}
    assert {row["canonical_wall_hit_label_replaced"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["claim_boundary"] for row in rows} == {
        "historical_assumption_mode_wall_ratio_path_not_evidence_mode"
    }
    assert any(row["reserve_remuneration_rate_source"] == "IOER" for row in rows)
    assert any(row["reserve_remuneration_rate_source"] == "IORB" for row in rows)

    for row in rows:
        countervailing = Decimal(row["scalar_countervailing_total_bil"])
        drag_100bp = Decimal(row["conventional_drag_100bp_equivalent_bil"])
        drag_rate_level = Decimal(row["conventional_drag_rate_level_bil"])
        expected_100bp = (
            Decimal("0") if drag_100bp == 0 else countervailing / drag_100bp
        )
        expected_historical = (
            Decimal("0") if drag_rate_level == 0 else countervailing / drag_rate_level
        )
        assert abs(
            Decimal(row["ratewall_offset_ratio_100bp_equivalent"]) - expected_100bp
        ) < Decimal("1e-18")
        assert abs(
            Decimal(row["historical_assumption_mode_wall_ratio"])
            - expected_historical
        ) < Decimal("1e-18")
        assert Decimal(row["remaining_gap_to_wall_bil"]) == max(
            drag_rate_level - countervailing,
            Decimal("0"),
        )


def test_forecast_holder_tdc_consistency_bridge_offsets_holder_interest_shift() -> None:
    rows = _read_output_table("ratewall_forecast_holder_tdc_consistency_bridge.csv")

    assert rows
    assert {row["holder_scenario"] for row in rows} == {
        "current_holder_distribution",
        "shift_to_domestic_nonbanks",
        "shift_to_banks_foreigners",
    }
    assert {row["maturity_scenario"] for row in rows} == {
        "higher_wam_slower_repricing",
        "current_wam_cbo_rate_path",
        "lower_wam_faster_repricing",
    }
    assert {row["mpc_scenario"] for row in rows} == {
        "low_mpc_5pct",
        "base_mpc_10pct",
        "high_mpc_20pct",
    }
    assert {row["holder_share_sum_status"] for row in rows} == {
        "pass_normalized_to_one"
    }
    assert Counter(row["tdcsim_contract_mapping_status"] for row in rows) == {
        "pass_tdcsim_contract_annualized": 297,
    }
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["holder_allocation_enabled"] for row in rows} == {"false"}
    assert {row["mpc_output_enabled"] for row in rows} == {"false"}
    assert {row["claim_boundary"] for row in rows} == {
        "forecast_holder_tdc_consistency_bridge_assumption_mode_not_holder_allocation"
    }

    current_key_rows = {
        row["holder_scenario"]: row
        for row in rows
        if row["forecast_year"] == "2026"
        and row["mpc_scenario"] == "base_mpc_10pct"
        and row["maturity_scenario"] == "current_wam_cbo_rate_path"
    }
    current = current_key_rows["current_holder_distribution"]
    domestic = current_key_rows["shift_to_domestic_nonbanks"]
    reserve = current_key_rows["shift_to_banks_foreigners"]

    assert Decimal(domestic["domestic_nonbank_interest_support_bil"]) > Decimal(
        current["domestic_nonbank_interest_support_bil"]
    )
    assert Decimal(domestic["tdc_auction_absorption_bil"]) < Decimal(
        current["tdc_auction_absorption_bil"]
    )
    assert Decimal(reserve["domestic_nonbank_interest_support_bil"]) < Decimal(
        current["domestic_nonbank_interest_support_bil"]
    )
    assert Decimal(reserve["tdc_auction_absorption_bil"]) > Decimal(
        current["tdc_auction_absorption_bil"]
    )

    for row in rows:
        interest_cashflow = Decimal(row["projected_total_interest_cashflow_bil"])
        domestic_share = Decimal(row["domestic_nonbank_holder_share"])
        bank_share = Decimal(row["bank_holder_share"])
        spend_share = Decimal(
            row["domestic_nonbank_current_spend_share_assumption"]
        )
        primary_deficit = Decimal(row["simulated_primary_deficit_bil"])
        total_deficit = Decimal(row["simulated_total_deficit_financing_need_bil"])
        principal_rollover = Decimal(row["simulated_principal_rollover_bil"])
        gross_issuance = Decimal(row["simulated_gross_issuance_need_bil"])
        drag = Decimal(row["conventional_drag_bil"])
        interest_support = (
            interest_cashflow * domestic_share * spend_share
            + interest_cashflow * bank_share * Decimal("0.02")
        )
        tdc_principal_to_domestic = principal_rollover * domestic_share
        tdc_interest_to_domestic = interest_cashflow * domestic_share
        tdc_debt_service_to_domestic = (
            tdc_principal_to_domestic + tdc_interest_to_domestic
        )
        tdc_auction_absorption = -(gross_issuance * domestic_share)
        tdc_change = (
            primary_deficit
            + tdc_debt_service_to_domestic
            + tdc_auction_absorption
        )
        tdc_full = Decimal(row["tdc_full_bil"])
        tdc_interest_overlap = Decimal(
            row["tdc_interest_debt_service_overlap_with_interest_income_bil"]
        )
        tdc_liquidity_base_ex_interest = tdc_full - tdc_interest_overlap
        tdc_support = (
            tdc_liquidity_base_ex_interest
            * Decimal("0.34201759129420367")
            * spend_share
        )
        assert abs(Decimal(row["holder_share_sum"]) - Decimal("1")) < Decimal(
            "1e-24"
        )
        assert total_deficit + principal_rollover == gross_issuance
        assert Decimal(row["interest_income_current_demand_support_bil"]) == (
            interest_support
        )
        assert Decimal(row["tdc_fiscal_flow_bil"]) == primary_deficit
        assert Decimal(row["tdc_debt_service_principal_to_domestic_nonbanks_bil"]) == (
            tdc_principal_to_domestic
        )
        assert Decimal(row["tdc_debt_service_interest_to_domestic_nonbanks_bil"]) == (
            tdc_interest_to_domestic
        )
        assert Decimal(row["tdc_debt_service_total_to_domestic_nonbanks_bil"]) == (
            tdc_debt_service_to_domestic
        )
        assert Decimal(row["tdc_auction_absorption_bil"]) == (
            tdc_auction_absorption
        )
        assert Decimal(row["tdc_secondary_trades_bil"]) == Decimal("0")
        assert Decimal(row["tdc_other_bil"]) == Decimal("0")
        assert Decimal(row["legacy_inline_projected_tdc_change_bil"]) == tdc_change
        assert Decimal(row["tdcsim_projected_tdc_change_bil"]) == tdc_full
        assert abs(
            Decimal(row["tdc_ex_direct_interest_overlap_bil"])
            - tdc_liquidity_base_ex_interest
        ) <= Decimal("1e-9")
        if row["tdcsim_contract_mapping_status"].startswith("blocked_"):
            assert tdc_interest_overlap == tdc_interest_to_domestic
            assert tdc_full == tdc_change
        assert abs(
            Decimal(row["tdc_deposit_liquidity_base_ex_interest_bil"])
            - tdc_liquidity_base_ex_interest
        ) <= Decimal("1e-9")
        assert abs(
            Decimal(row["tdc_deposit_current_demand_support_bil"]) - tdc_support
        ) <= Decimal("1e-9")
        assert tdc_interest_overlap not in {Decimal("0"), tdc_full}
        assert "tdc_deposit_support_uses_tdcsim_projected_tdc_change_ex_interest_overlap_times_ea_tdc_beta_times_chi" in (
            row["double_count_prevention_rule"]
        )
        assert abs(
            Decimal(row["combined_current_demand_support_bil"])
            - (interest_support + tdc_support)
        ) <= Decimal("1e-9")
        assert abs(
            Decimal(row["interest_only_wall_ratio"]) - interest_support / drag
        ) < Decimal("1e-24")
        assert abs(
            Decimal(row["holder_tdc_consistent_wall_ratio"])
            - (interest_support + tdc_support) / drag
        ) <= Decimal("1e-12")


def test_tdcest_historical_estimator_bridge_uses_source_units() -> None:
    rows = _read_output_table("ratewall_tdcest_historical_estimator_bridge.csv")

    assert rows
    estimator_keys = {row["estimator_key"] for row in rows}
    assert {
        "tdc_level_bank_only_sensitivity",
        "tdc_bank_only_extended_1990",
        "tdc_base_bank_only_ru_flow",
        "tdc_tier2_component_anchored_bank_only_ru_flow",
        "tdc_tier2_canonical_depository_institution_mmf_rrp_prop_ru_flow",
        "tdc_tier3_fiscal_corrected_bank_only_ru_flow",
    } <= estimator_keys
    assert min(
        row["quarter"]
        for row in rows
        if row["estimator_key"] == "tdc_level_bank_only_sensitivity"
    ) == "1952Q1"
    assert min(
        row["quarter"]
        for row in rows
        if row["estimator_key"] == "tdc_tier3_fiscal_corrected_bank_only_ru_flow"
    ) >= "2022Q1"
    assert {row["canonical_tdc_mechanism_input"] for row in rows} == {"true"}
    assert {row["canonical_solved_output_replaced"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}

    for row in rows:
        assert Decimal(row["estimator_value_bil"]) == (
            Decimal(row["estimator_value_mil"]) / Decimal("1000")
        )


def test_tdcest_monetary_route_bridge_keeps_non_m2_routes_out_of_math() -> None:
    rows = _read_output_table("ratewall_tdcest_monetary_route_bridge.csv")

    assert rows
    latest = [row for row in rows if row["quarter"] == "2025Q4"]
    by_route = {row["route_id"]: row for row in latest}
    retail = by_route["retail_mmf_m2_non_deposit_scope"]
    assert retail["m2_scope"] == "true"
    assert retail["deposit_pass_through_scope"] == "false"
    assert retail["current_demand_eligible"] == "false"

    onrrp = by_route["mmf_onrrp_runoff_non_m2_plumbing"]
    assert onrrp["m2_scope"] == "false"
    assert onrrp["deposit_pass_through_scope"] == "false"
    assert onrrp["ratewall_treatment"] == (
        "source_backed_plumbing_context_excluded_from_deposit_pass_through"
    )

    domestic = by_route["z1_domestic_nonbank_mixed_unknown_m2_scope"]
    assert domestic["deposit_pass_through_scope"] == "unknown_or_mixed"
    assert domestic["ratewall_treatment"] == (
        "blocked_until_m2_or_deposit_funding_split_exists"
    )

    other = by_route["z1_other_financial_non_m2_scope"]
    assert other["m2_scope"] == "false"
    assert other["enters_main_ratio"] == "false"
    assert {row["canonical_tdc_math_change"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}


def test_tdcest_mmf_route_split_context_keeps_sec_split_out_of_math() -> None:
    rows = _read_output_table("ratewall_tdcest_mmf_route_split_context.csv")

    assert rows
    latest_quarter = max(row["quarter"] for row in rows)
    latest = [row for row in rows if row["quarter"] == latest_quarter]
    by_route = {row["route_id"]: row for row in latest}

    retail = by_route["retail_mmf_treasury_holdings_context"]
    assert retail["m2_scope"] == "true"
    assert retail["deposit_pass_through_scope"] == "false"
    assert retail["current_demand_eligible"] == "false"
    assert float(retail["treasury_total_bil"]) > 0

    institutional = by_route[
        "institutional_or_nonretail_mmf_treasury_holdings_context"
    ]
    assert institutional["m2_scope"] == "false"
    assert institutional["deposit_pass_through_scope"] == "false"
    assert float(institutional["treasury_total_bil"]) > 0

    onrrp = by_route["institutional_or_nonretail_mmf_onrrp_plumbing_context"]
    assert onrrp["ratewall_treatment"] == "fed_onrrp_plumbing_context_only"
    assert float(onrrp["fed_onrrp_bil"]) >= 0

    assert {row["canonical_tdc_math_change"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}


def test_tdcest_z1_domestic_nonbank_sector_context_keeps_sector_context_out_of_math() -> None:
    rows = _read_output_table("ratewall_tdcest_z1_domestic_nonbank_sector_context.csv")

    assert rows
    latest_quarter = max(row["quarter"] for row in rows)
    latest = [row for row in rows if row["quarter"] == latest_quarter]
    by_route = {row["sector_route_id"]: row for row in latest}

    mmf = by_route["z1_mmf_sector_context"]
    assert mmf["m2_scope"] == "mixed_retail_mmf_and_non_m2_mmf"
    assert mmf["deposit_pass_through_scope"] == "false"
    assert mmf["ratewall_current_demand_gate"] == "fail_mixed_unknown"

    dealer = by_route["z1_security_brokers_dealers_sector_context"]
    assert dealer["debited_claim_type"] == "repo_claim"
    assert dealer["ratewall_current_demand_gate"] == "fail_noncurrent_claim"

    household_residual = by_route[
        "z1_households_nonprofits_residual_sector_context"
    ]
    assert household_residual["deposit_pass_through_scope"] == "unknown_or_mixed"
    assert household_residual["current_demand_eligible"] == "false"

    assert {row["source_status"] for row in rows} == {
        "source_backed_z1_sector_context"
    }
    assert {row["tdc_admissibility"] for row in rows} == {"context_only"}
    assert {row["current_demand_eligible"] for row in rows} == {"false"}
    assert {row["canonical_tdc_math_change"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}


def test_tdcest_route_admissibility_registry_guardrails_existing_routes() -> None:
    registry_path = (
        Path("data/raw/ratewall_sibling_calibration")
        / "tdcest_route_admissibility_registry.csv"
    )
    with registry_path.open(newline="") as handle:
        registry = list(csv.DictReader(handle))

    monetary_rows = _read_output_table("ratewall_tdcest_monetary_route_bridge.csv")
    mmf_rows = _read_output_table("ratewall_tdcest_mmf_route_split_context.csv")
    expected_route_ids = {row["route_id"] for row in monetary_rows} | {
        row["route_id"] for row in mmf_rows
    }

    assert registry
    assert len(registry) == 11
    assert "quarter" not in registry[0]
    assert {row["route_id"] for row in registry} == expected_route_ids
    assert {row["current_demand_eligible"] for row in registry} == {"false"}
    assert {row["canonical_tdc_math_change"] for row in registry} == {"false"}
    assert not any(
        row["ratewall_current_demand_gate"].startswith("pass_") for row in registry
    )

    by_route = {row["route_id"]: row for row in registry}
    retail = by_route["retail_mmf_m2_non_deposit_scope"]
    assert retail["m2_scope"] == "true"
    assert retail["deposit_pass_through_scope"] == "false"
    assert retail["tdc_admissibility"] == "context_only"

    onrrp = by_route["mmf_onrrp_runoff_non_m2_plumbing"]
    assert onrrp["debited_claim_type"] == "fed_rrp_liability"
    assert onrrp["tdc_admissibility"] == "named_plumbing_adjustment"
    assert onrrp["ratewall_current_demand_gate"] == "fail_noncurrent_claim"
    assert onrrp["onrrp_boundary_status"] == (
        "nyfed_fed_liability_counterparty_type_context"
    )
    assert onrrp["onrrp_counterparty_scope"] == "mmf_counterparty_aggregate"

    mixed_domestic = by_route["z1_domestic_nonbank_mixed_unknown_m2_scope"]
    assert mixed_domestic["preferred_guardrail_label"] == (
        "mixed_domestic_nonbank_absorption_context"
    )
    assert mixed_domestic["ratewall_current_demand_gate"] == "fail_mixed_unknown"

    for route_id, row in by_route.items():
        if any(
            marker in route_id
            for marker in (
                "retail_mmf",
                "institutional",
                "z1_domestic_nonbank",
                "dealer",
                "repo",
                "onrrp",
            )
        ):
            assert row["current_demand_eligible"] == "false"
            assert not row["ratewall_current_demand_gate"].startswith("pass_")

    retail_onrrp = by_route["retail_mmf_onrrp_plumbing_context"]
    institutional_onrrp = by_route[
        "institutional_or_nonretail_mmf_onrrp_plumbing_context"
    ]
    assert retail_onrrp["onrrp_boundary_status"] == (
        "sec_nmfp_fed_onrrp_portfolio_context"
    )
    assert retail_onrrp["onrrp_counterparty_scope"] == "retail_mmf_fund_scope"
    assert institutional_onrrp["onrrp_counterparty_scope"] == (
        "institutional_or_nonretail_mmf_fund_scope"
    )
    assert {row["current_demand_eligible"] for row in (retail_onrrp, institutional_onrrp)} == {
        "false"
    }


def test_tdcest_z1_domestic_nonbank_sector_context_stays_context_only() -> None:
    context_path = (
        Path("data/raw/ratewall_sibling_calibration")
        / "tdcest_z1_domestic_nonbank_sector_context.csv"
    )
    with context_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    latest_quarter = max(row["quarter"] for row in rows)
    latest = [row for row in rows if row["quarter"] == latest_quarter]
    by_sector = {row["sector_route_id"]: row for row in latest}

    assert len(latest) == 14
    assert {
        "z1_mmf_sector_context",
        "z1_security_brokers_dealers_sector_context",
        "z1_gse_sector_context",
        "z1_mutual_funds_sector_context",
        "z1_households_nonprofits_residual_sector_context",
    } <= set(by_sector)
    assert {row["current_demand_eligible"] for row in rows} == {"false"}
    assert {row["canonical_tdc_math_change"] for row in rows} == {"false"}
    assert not any(
        row["ratewall_current_demand_gate"].startswith("pass_") for row in rows
    )

    mmf = by_sector["z1_mmf_sector_context"]
    assert mmf["m2_scope"] == "mixed_retail_mmf_and_non_m2_mmf"
    assert mmf["ratewall_current_demand_gate"] == "fail_mixed_unknown"

    dealer = by_sector["z1_security_brokers_dealers_sector_context"]
    assert dealer["debited_claim_type"] == "repo_claim"
    assert dealer["ratewall_current_demand_gate"] == "fail_noncurrent_claim"

    household = by_sector["z1_households_nonprofits_residual_sector_context"]
    assert household["deposit_pass_through_scope"] == "unknown_or_mixed"
    assert household["ratewall_current_demand_gate"] == "fail_mixed_unknown"


def test_historical_tdc_wall_ratio_path_uses_tdcest_bridge() -> None:
    rows = _read_output_table("ratewall_historical_tdc_wall_ratio_path.csv")

    assert rows
    assert {row["calibration_band"] for row in rows} == {"rolling_tdc_pass_through"}
    assert min(row["quarter"] for row in rows) >= "2011Q4"
    assert {
        "tdc_tier2_component_anchored_bank_only_ru_flow",
        "tdc_tier2_canonical_depository_institution_mmf_rrp_prop_ru_flow",
    } <= {row["estimator_key"] for row in rows}
    assert "tdc_tier3_fiscal_corrected_bank_only_ru_flow" in {
        row["estimator_key"]
        for row in _read_output_table("ratewall_tdcest_historical_estimator_bridge.csv")
    }
    assert {row["canonical_tdc_mechanism_input"] for row in rows} == {"true"}
    assert {row["canonical_solved_output_replaced"] for row in rows} == {"false"}
    assert {row["historical_ratio_not_classifier"] for row in rows} == {"true"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["claim_boundary"] for row in rows} == {
        "historical_tdc_wall_ratio_path_source_backed_tdc_mechanism_"
        "not_mpc_or_incidence_output"
    }

    for row in rows:
        tdc = Decimal(row["tdc_estimate_bil"])
        pass_through = Decimal(row["tdc_deposit_pass_through_share"])
        other_component_share = Decimal(row["tdc_other_component_regression_share"])
        effect = tdc * pass_through
        other_effect = tdc * other_component_share
        drag = Decimal(row["conventional_drag_rate_level_bil"])
        expected_ratio = Decimal("0") if drag == 0 else effect / drag
        assert Decimal(row["tdc_liquidity_demand_effect_bil"]) == effect
        assert Decimal(row["tdc_other_component_effect_bil"]) == other_effect
        assert (
            Decimal(row["tdc_deposit_plus_other_component_regression_effect_bil"])
            == effect + other_effect
        )
        assert row["tdc_component_identity_status"] == (
            "rolling_regression_components_reported_not_forced_accounting_identity"
        )
        assert abs(Decimal(row["tdc_only_wall_ratio"]) - expected_ratio) < Decimal(
            "1e-18"
        )
        assert Decimal(row["tdc_gap_to_wall_bil"]) == max(
            drag - effect,
            Decimal("0"),
        )


def test_tdc_rolling_pass_through_context_is_active_historical_parameter() -> None:
    rows = _read_output_table("ratewall_tdc_rolling_pass_through_context.csv")

    assert rows
    assert min(int(row["window_quarters"]) for row in rows) >= 48
    assert {row["ratewall_use_status"] for row in rows} == {
        "active_historical_assumption_mode_tdc_parameter_not_main_classifier"
    }
    assert {row["claim_boundary"] for row in rows} == {
        "tdc_rolling_pass_through_context_not_mpc_or_incidence_output"
    }
    assert all(
        "tier2_rolling_selected_credit_rate_pass_through_estimates.csv"
        in row["source_artifact"]
        for row in rows
    )
    assert all(
        row["calculation_method"]
        == "rolling_48_quarter_selected_credit_rate_lags_rank_aware_newey_west_reestimate"
        for row in rows
    )
    for row in rows:
        deposit_share = Decimal(row["rolling_deposit_pass_through_share"])
        other_share = Decimal(row["rolling_other_component_regression_share"])
        assert (
            Decimal(row["rolling_deposit_plus_other_component_regression_share"])
            == deposit_share + other_share
        )
        assert row["component_identity_status"] == (
            "regression_components_reported_not_forced_accounting_identity"
        )
    assert max(Decimal(row["rolling_deposit_pass_through_share"]) for row in rows) > Decimal(
        "0.5"
    )


def test_historical_assumption_mode_tdc_wall_ratio_path_combines_tdc() -> None:
    rows = _read_output_table(
        "ratewall_historical_assumption_mode_tdc_wall_ratio_path.csv"
    )

    assert rows
    assert {row["tdc_calibration_band"] for row in rows} == {
        "rolling_tdc_pass_through"
    }
    assert "base_current_100bps" in {row["assumption_set"] for row in rows}
    assert {row["canonical_tdc_mechanism_input"] for row in rows} == {"true"}
    assert {row["canonical_solved_output_replaced"] for row in rows} == {"false"}
    assert {row["canonical_wall_hit_label_replaced"] for row in rows} == {"false"}
    assert {row["historical_ratio_not_classifier"] for row in rows} == {"true"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["claim_boundary"] for row in rows} == {
        "historical_assumption_mode_tdc_wall_ratio_path_not_evidence_mode"
    }
    post_2022_estimators = {
        row["tdc_estimator_key"] for row in rows if row["quarter"] >= "2022Q1"
    }
    assert post_2022_estimators == {"tdc_tier2_component_anchored_bank_only_ru_flow"}
    assert {
        "tier3_diagnostic_only" in row["tdc_stitch_rule"] for row in rows
    } == {True}

    for row in rows:
        countervailing_before = Decimal(
            row["scalar_countervailing_total_bil_before_tdc"]
        )
        tdc_effect = Decimal(row["tdc_liquidity_demand_effect_bil"])
        other_effect = Decimal(row["tdc_other_component_effect_bil"])
        countervailing_with_tdc = countervailing_before + tdc_effect
        drag = Decimal(row["conventional_drag_rate_level_bil"])
        expected_ratio = (
            Decimal("0") if drag == 0 else countervailing_with_tdc / drag
        )
        assert (
            Decimal(row["tdc_deposit_plus_other_component_regression_effect_bil"])
            == tdc_effect + other_effect
        )
        assert row["tdc_component_identity_status"] == (
            "rolling_regression_components_reported_not_forced_accounting_identity"
        )
        assert Decimal(row["scalar_countervailing_total_bil_with_tdc"]) == (
            countervailing_with_tdc
        )
        assert abs(
            Decimal(row["historical_assumption_mode_wall_ratio_with_tdc"])
            - expected_ratio
        ) < Decimal("1e-18")
        assert Decimal(row["remaining_gap_to_wall_bil_with_tdc"]) == max(
            drag - countervailing_with_tdc,
            Decimal("0"),
        )


def test_tdc_other_component_bridge_closes_gap_to_unity_identity() -> None:
    rows = _read_output_table("ratewall_tdc_other_component_bridge.csv")

    assert rows
    assert {row["source_status"] for row in rows} == {"identity_bridge_passed"}
    assert {row["legacy_interpretation_status"] for row in rows} == {
        "deprecated_do_not_use_for_live_ratio"
    }
    assert {row["live_ratio_default_treatment"] for row in rows} == {
        "reduced_form_deposit_effect_only_no_residual_stack"
    }
    for row in rows:
        unity = Decimal(row["tdc_unity_benchmark_effect_bil"])
        gap = Decimal(row["tdc_gap_to_unity_adjustment_bil"])
        reduced = Decimal(row["tdc_reduced_form_deposit_effect_bil"])
        assert abs(unity + gap - reduced) < Decimal("1e-12")
        assert abs(Decimal(row["tdc_bridge_identity_error_bil"])) < Decimal("1e-12")


def test_tdc_deposit_credit_decomposition_default_not_live() -> None:
    rows = _read_output_table("ratewall_tdc_deposit_credit_decomposition.csv")

    assert rows
    assert {row["residual_pack_id"] for row in rows} == {"unclassified_default"}
    assert {row["enters_live_ratio"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    share_sum_by_key: dict[tuple[str, str, str, str], Decimal] = {}
    for row in rows:
        key = (
            row["quarter"],
            row["assumption_set"],
            row["horizon"],
            row["tdc_estimator_key"],
        )
        share_sum_by_key[key] = share_sum_by_key.get(key, Decimal("0")) + Decimal(
            row["bucket_share"]
        )
    assert set(share_sum_by_key.values()) == {Decimal("1")}


def test_tdc_double_count_guardrail_blocks_incremental_drag_by_default() -> None:
    rows = _read_output_table("ratewall_tdc_double_count_guardrail.csv")

    assert rows
    assert {row["candidate_overlap_channel"] for row in rows} == {
        "credit_supply_drag",
        "foreign_flow_context",
        "mmf_rrp_context",
        "safe_asset_substitution",
        "treasury_timing_context",
        "unclassified_residual",
    }
    assert {row["candidate_overlap_channel_family"] for row in rows} == {
        "context_or_memo_only",
        "existing_denominator_drag",
    }
    assert {row["guardrail_pass"] for row in rows} == {"true"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["admitted_incremental_countervailing_bil"] for row in rows} == {"0"}
    assert {row["admitted_incremental_drag_bil"] for row in rows} == {"0"}
    assert {row["tdc_beta_denominator_freeze"] for row in rows} == {"true"}
    assert {row["tdc_credit_supply_overlap_memo_share"] for row in rows} == {
        "0.00/0.25/0.50"
    }
    assert {row["tdc_credit_supply_overlap_discount_share_live"] for row in rows} == {
        "1.00"
    }
    assert {row["allowed_use"] for row in rows} == {
        "tdc_credit_supply_beta_overlap_safeguard"
    }
    assert {
        "credit_supply_drag_delta" in row["blocked_use"]
        and "retail_safe_yield_pass_through_beta_delta" in row["blocked_use"]
        and "consumer_credit_sidecar_delta" in row["blocked_use"]
        for row in rows
    } == {True}
    assert {row["claim_boundary"] for row in rows} == {
        "tdc_credit_supply_beta_overlap_safeguard_assumption_mode_no_double_count_not_source_gate_promotion"
    }
    assert {row["safe_sentence"] for row in rows} == {
        "EA-TDC beta is numerator-only in N_TDC; it cannot move credit_supply_drag, "
        "retail safe-yield pass-through, consumer-credit repricing, or any "
        "denominator term."
    }
    assert {
        row["violation_reason"] for row in rows if row["default_action"] == "replace_not_stack"
    } == {"blocked_default_replace_not_stack"}
    assert {
        row["violation_reason"] for row in rows if row["default_action"] == "memo_only"
    } == {"memo_only_no_live_ratio_admission"}


def test_tdc_net_ratewall_effect_variants_are_equivalent_under_identity_bridge() -> None:
    rows = _read_output_table("ratewall_tdc_net_ratewall_effect.csv")

    assert rows
    assert {row["ratio_variant"] for row in rows} == {
        "reduced_form_support_default",
        "unity_benchmark_reference",
    }
    rows_by_key = {
        (
            row["quarter"],
            row["assumption_set"],
            row["horizon"],
            row["tdc_estimator_key"],
            row["ratio_variant"],
        ): row
        for row in rows
    }
    reduced_rows = [
        row for row in rows if row["ratio_variant"] == "reduced_form_support_default"
    ]
    assert {row["canonical_variant"] for row in reduced_rows} == {"true"}
    assert {
        row["canonical_variant"]
        for row in rows
        if row["ratio_variant"] == "unity_benchmark_reference"
    } == {"false"}
    for reduced in reduced_rows:
        unity = rows_by_key[
            (
                reduced["quarter"],
                reduced["assumption_set"],
                reduced["horizon"],
                reduced["tdc_estimator_key"],
                "unity_benchmark_reference",
            )
        ]
        assert abs(
            Decimal(reduced["wall_ratio_after_tdc"])
            - Decimal(unity["wall_ratio_after_tdc"])
        ) < Decimal("1e-18")
        assert Decimal(reduced["tdc_incremental_drag_bil_admitted"]) == Decimal("0")
        assert Decimal(unity["tdc_incremental_drag_bil_admitted"]) == Decimal("0")


def test_tdc_new_tables_keep_forbidden_switches_false() -> None:
    table_names = (
        "ratewall_tdc_other_component_bridge.csv",
        "ratewall_tdc_deposit_credit_decomposition.csv",
        "ratewall_tdc_double_count_guardrail.csv",
        "ratewall_tdc_net_ratewall_effect.csv",
        "ratewall_tdc_historical_source_contract.csv",
        "ratewall_tdc_historical_selected_series.csv",
        "ratewall_tdcsim_projection_contract_bridge.csv",
        "ratewall_tdcsim_domestic_nonbank_funding_classification.csv",
        "ratewall_canonical_tdc_accounting_path.csv",
        "ratewall_canonical_tdc_stitched_accounting_path.csv",
        "ratewall_canonical_tdc_accounting_source_hierarchy_audit.csv",
        "ratewall_tdc_forward_projection_surface.csv",
        "ratewall_tdc_forward_component_audit.csv",
        "ratewall_tdc_forward_overlap_guardrail.csv",
        "ratewall_tdc_forward_assumption_registry.csv",
        "ratewall_tdc_forward_scenario_decomposition.csv",
        "ratewall_forecast_holder_tdc_consistency_bridge.csv",
        "ratewall_qrawatch_tdcsim_scenario_registry.csv",
        "ratewall_qrawatch_tdcsim_provenance_audit.csv",
    )
    disabled_fields = (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    )

    for table_name in table_names:
        rows = _read_output_table(table_name)
        assert rows
        for field in disabled_fields:
            assert {row[field] for row in rows} == {"false"}
        if "enters_main_ratio" in rows[0]:
            enters_values = {row["enters_main_ratio"] for row in rows}
            if table_name == "ratewall_tdc_forward_assumption_registry.csv":
                assert enters_values == {"false", "true"}
                assert {
                    row["assumption_family"]
                    for row in rows
                    if row["enters_main_ratio"] == "true"
                } == {
                    "tdc_materialization_beta",
                    "tdc_deposit_current_demand_conversion",
                    "tdc_deposit_conversion_share_assumption_derived_alias",
                }
            else:
                assert enters_values == {"false"}


def test_tdcsim_forward_contract_version_required() -> None:
    rows = _read_output_table("ratewall_tdc_forward_projection_surface.csv")

    assert rows
    assert {row["contract_ingest_status"] for row in rows} == {"pass"}
    assert all(row["tdcsim_contract_version"] for row in rows)
    assert all(row["tdcsim_manifest_hash"] for row in rows)


def test_missing_tdcsim_contract_fails_closed(tmp_path: Path) -> None:
    rows = tdc_forward_projection_surface_rows(tmp_path / "missing_tdcsim_contract")
    bridge_rows = tdcsim_projection_contract_bridge_rows(
        tmp_path / "missing_tdcsim_contract"
    )
    classification_rows = tdcsim_domestic_nonbank_funding_classification_rows(
        tmp_path / "missing_tdcsim_contract"
    )

    assert len(rows) == 1
    assert rows[0]["contract_ingest_status"] == "fail_closed_missing_contract"
    assert rows[0]["enters_main_ratio"] == "false"
    assert rows[0]["evidence_mode_enabled"] == "false"
    assert rows[0]["canonical_ratio_entry"] == "false"
    assert len(bridge_rows) == 1
    assert bridge_rows[0]["contract_ingest_status"] == "fail_closed_missing_contract"
    assert bridge_rows[0]["enters_main_ratio"] == "false"
    assert bridge_rows[0]["evidence_mode_enabled"] == "false"
    assert bridge_rows[0]["canonical_ratio_entry"] == "false"
    assert len(classification_rows) == 1
    assert (
        classification_rows[0]["current_contract_status"]
        == "fail_closed_missing_contract"
    )
    assert classification_rows[0]["enters_main_ratio"] == "false"
    assert classification_rows[0]["evidence_mode_enabled"] == "false"
    assert classification_rows[0]["canonical_ratio_entry"] == "false"


def test_tdcsim_projection_contract_bridge_is_source_backed_and_noncanonical() -> None:
    rows = _read_output_table("ratewall_tdcsim_projection_contract_bridge.csv")

    assert rows
    assert {row["contract_ingest_status"] for row in rows} == {"pass"}
    assert {
        row["primary_flow_status"]
        for row in rows
    } == {"aggregate_cash_proxy_from_cbo_total_deficit_less_net_interest"}
    assert {row["secondary_trade_status"] for row in rows} == {"absent_not_imputed"}
    assert {row["other_status"] for row in rows} == {"explicit_zero"}
    assert {row["assumption_mode"] for row in rows} == {"true"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {
        row["scenario_id"]
        for row in rows
    } == {
        "current_mix_baseline",
        "current_mix_bear_steepener",
        "current_mix_bull_flattener",
        "current_mix_higher_for_longer",
        "current_mix_rapid_easing",
        "domestic_nonbank_absorption_shift",
        "domestic_nonbank_absorption_shift_higher_for_longer",
        "domestic_nonbank_absorption_shift_rapid_easing",
        "reserve_user_absorption_shift",
        "reserve_user_absorption_shift_higher_for_longer",
        "reserve_user_absorption_shift_rapid_easing",
    }


def test_tdcsim_domestic_nonbank_funding_classification_marks_mmf_gap() -> None:
    rows = _read_output_table(
        "ratewall_tdcsim_domestic_nonbank_funding_classification.csv"
    )

    assert rows
    by_id = {row["classification_row_id"]: row for row in rows}
    private = by_id["tdcsim_holder_funding_classification::current::Private"]
    assert private["current_ratewall_role"] == "DU"
    assert (
        private["proposed_ratewall_category"]
        == "domestic_nonbank_undifferentiated_current_contract"
    )
    assert private["tdcsim_route_contract_status"] == "route_contract_present"
    assert (
        private["tdcsim_route_contract_role"]
        == "domestic_nonbank_undifferentiated_current_contract"
    )
    assert private["non_deposit_funded_domestic_nonbank_status"] == (
        "blocked_missing_explicit_non_deposit_funded_domestic_nonbank_bucket"
    )
    assert private["mmf_on_rrp_status"] == (
        "blocked_mmf_on_rrp_not_split_from_private_bucket"
    )
    assert private["linked_tdcest_latest_quarter"] == "2025Q4"
    assert private["linked_tdcest_route_context_row_count"] == "6583"
    assert "monetary_mmf_onrrp_non_m2_qoq_bil=7.414234" in private[
        "linked_tdcest_latest_route_values"
    ]
    assert "sec_nmfp_institutional_onrrp_bil=69.692966" in private[
        "linked_tdcest_latest_route_values"
    ]
    assert private["source_backed_private_bucket_split_status"] == (
        "source_context_available_private_bucket_still_unsplit"
    )
    target = by_id[
        "tdcsim_holder_funding_classification::target::"
        "domestic_nonbank_non_deposit_funded"
    ]
    assert (
        target["current_contract_status"]
        == "route_contract_present_target_not_current_holder_type"
    )
    assert (
        target["proposed_ratewall_category"]
        == "domestic_nonbank_non_deposit_funded"
    )
    assert target["tdcsim_route_contract_status"] == "route_contract_present"
    assert (
        target["tdcsim_route_contract_binding_blocker"]
        == "requires_source_backed_split_from_current_private_holder_bucket"
    )
    assert target["source_backed_private_bucket_split_status"] == (
        "source_context_available_target_route_not_current_tdcsim_holder_bucket"
    )
    assert "do_not_source_back_private_bucket_split" in target[
        "source_backed_private_bucket_split_blocker"
    ]
    mmf_target = by_id[
        "tdcsim_holder_funding_classification::target::"
        "mmf_cash_fund_route"
    ]
    assert mmf_target["funding_route"] == "mmf_on_rrp_or_fed_repo_drawdown_route"
    assert mmf_target["tdcsim_route_contract_status"] == "route_contract_present"
    assert (
        mmf_target["tdcsim_route_contract_binding_blocker"]
        == "requires_source_backed_mmf_on_rrp_route_split_before_ru_like_use"
    )
    assert mmf_target["source_backed_private_bucket_split_status"] == (
        "source_context_available_mmf_onrrp_amounts_not_tdcsim_bucket_split"
    )
    assert "do_not_identify_final_investor" in mmf_target[
        "source_backed_private_bucket_split_blocker"
    ]
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}


def test_qrawatch_tdcsim_bridge_is_fail_closed_and_tdcsim_gated() -> None:
    registry_rows = _read_output_table(
        "ratewall_qrawatch_tdcsim_scenario_registry.csv"
    )
    provenance_rows = _read_output_table(
        "ratewall_qrawatch_tdcsim_provenance_audit.csv"
    )
    invariant_rows = _read_output_table(
        "ratewall_qrawatch_tdcsim_bridge_invariant_audit.csv"
    )
    tdcsim_rows = _read_output_table("ratewall_tdcsim_projection_contract_bridge.csv")

    assert registry_rows
    assert provenance_rows
    assert invariant_rows
    assert {row["audit_status"] for row in invariant_rows} == {"pass"}
    assert {row["audit_status"] for row in provenance_rows} == {"pass"}

    default_rows = [
        row
        for row in registry_rows
        if row["central_default_runtime_path"] == "true"
    ]
    assert [row["scenario_contract_id"] for row in default_rows] == [
        "current_mix_baseline"
    ]
    assert default_rows[0]["runtime_mechanics_enabled"] == "true"
    assert default_rows[0]["ratewall_runtime_source"] == (
        "ratewall_tdcsim_projection_contract_bridge.csv"
    )
    assert {row["scenario_id"] for row in tdcsim_rows} >= {"current_mix_baseline"}

    qrawatch_rows = [
        row for row in registry_rows if row["qrawatch_derived"] == "true"
    ]
    assert {
        row["scenario_contract_id"] for row in qrawatch_rows
    } == {
        "qrawatch_ati_issuance_mix_measurement",
        "qrawatch_ati_readiness_gate",
        "qrawatch_forward_ati_path_blocked",
        "qrawatch_duration_supply_yield_shift",
        "qrawatch_pricing_translation_context",
        "qrawatch_holder_preference_blocked",
        "qrawatch_auction_absorption_diagnostic",
        "qrawatch_plumbing_diagnostic",
    }
    for row in qrawatch_rows:
        assert row["runtime_mechanics_enabled"] == "false"
        assert row["qrawatch_direct_runtime_read"] == "false"
        assert row["central_default_runtime_path"] == "false"
        assert row["current_mix_baseline_runtime_path"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["evidence_mode_enabled"] == "false"
        assert row["pricing_output_enabled"] == "false"
        assert row["holder_allocation_enabled"] == "false"
        assert row["canonical_ratio_entry"] == "false"
        assert row["tdcsim_required_input_contract"].startswith("qrawatch_tdcsim_")
        assert row["tdcsim_contract_consumption_status"] != (
            "consumed_as_ratewall_runtime_contract_output"
        )

    holder = next(
        row
        for row in qrawatch_rows
        if row["scenario_contract_id"] == "qrawatch_holder_preference_blocked"
    )
    assert holder["source_record_count"] == "0"
    assert holder["holder_allocation_enabled"] == "false"
    assert "investor_allotment_evidence" in holder["source_backing_admission_status"]

    pricing = next(
        row
        for row in qrawatch_rows
        if row["scenario_contract_id"] == "qrawatch_pricing_translation_context"
    )
    assert pricing["pricing_output_enabled"] == "false"
    assert "not_ratewall_pricing_output" in pricing["source_backing_admission_status"]


def test_tdc_forward_component_sum_equals_tdc_change() -> None:
    rows = _read_output_table("ratewall_tdc_forward_overlap_guardrail.csv")

    assert rows
    assert {row["guardrail_status"] for row in rows} == {"pass"}
    for row in rows:
        assert abs(Decimal(row["overlap_identity_error_bil"])) <= Decimal("1e-7")


def test_tdc_forward_component_audit_reconciles_and_excludes_dual_entry() -> None:
    rows = _read_output_table("ratewall_tdc_forward_component_audit.csv")

    assert rows
    assert {row["component_dual_entry_status"] for row in rows} == {
        "pass_mutually_exclusive"
    }
    assert not [
        row
        for row in rows
        if row["enters_direct_interest_support"] == "true"
        and row["enters_tdc_deposit_support_default"] == "true"
    ]
    assert {
        row["ratewall_perimeter"]
        for row in rows
        if row["holder_bucket"] in {"DU", "DU_RU"}
    } <= {"DU", "bridge"}


def test_tdc_forward_direct_interest_overlap_subtracted_exactly_once() -> None:
    projection_rows = _read_output_table("ratewall_tdc_forward_projection_surface.csv")
    overlap_rows = _read_output_table("ratewall_tdc_forward_overlap_guardrail.csv")

    assert projection_rows
    assert overlap_rows
    assert all(row["canonical_tdc_accounting_path_id"] for row in projection_rows)
    assert {
        row["canonical_tdc_accounting_path_id"]
        for row in projection_rows
    } == {
        f"forward_tdcsim_{row['scenario_id']}" for row in projection_rows
    }
    assert {row["principal_overlap_subtracted"] for row in overlap_rows} == {"false"}
    overlap_by_key = {
        (row["scenario_id"], row["quarter"]): row for row in overlap_rows
    }
    for row in projection_rows:
        guardrail = overlap_by_key[(row["scenario_id"], row["quarter"])]
        tdc_change = Decimal(row["tdc_change_bil"])
        overlap = Decimal(row["direct_interest_overlap_cashflow_bil"])
        base_ex_interest = Decimal(
            row["tdc_deposit_support_base_ex_direct_interest_bil"]
        )
        beta = Decimal(row["tdc_materialization_beta_assumption"])
        chi = Decimal(row["deposit_current_demand_share_assumption"])
        composite = Decimal(row["tdc_deposit_conversion_share_assumption"])
        assert base_ex_interest == tdc_change - overlap
        assert composite == beta * chi
        assert Decimal(row["tdc_net_materialized_deposits_bil"]) == (
            base_ex_interest * beta
        )
        assert Decimal(row["tdc_deposit_current_demand_support_bil"]) == (
            base_ex_interest * beta * chi
        )
        assert Decimal(guardrail["direct_interest_overlap_cashflow_bil"]) == overlap


def test_tdc_forward_source_hierarchy_blocks_weak_wamest_and_tdcmix_claims() -> None:
    with (
        Path("data/raw/ratewall_sibling_calibration/tdcsim")
        / "tdcsim_ratewall_source_registry.csv"
    ).open(encoding="utf-8", newline="") as handle:
        registry = list(csv.DictReader(handle))

    weak_wamest = next(row for row in registry if row["source_family"] == "wamest")
    tdcmix = next(row for row in registry if row["source_family"] == "tdcmix")
    assert weak_wamest["central_default_eligible"] == "false"
    assert weak_wamest["sensitivity_only"] == "true"
    assert "weak_sector_revaluation" in weak_wamest["binding_blocker"]
    assert tdcmix["ratewall_role"] == "holder_scenario_prior_not_allocation_claim"


def test_legacy_forecast_holder_tdc_bridge_not_final_or_canonical() -> None:
    rows = _read_output_table("ratewall_forecast_holder_tdc_consistency_bridge.csv")

    assert rows
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["legacy_scaffold_reference_status"] for row in rows} == {
        "legacy_inline_scaffold_demoted_not_ratewall_tdc_object"
    }
    assert all("legacy_scaffold_demoted" in row["source_status"] for row in rows)
    assert all(
        row["tdc_proxy_vs_theoretical_gap_flag"]
        == "future_work_not_current_blocker;ea_tdc_proxy_carried_as_assumption_mode_beta_range"
        for row in rows
    )


def test_tdc_forward_invariant_audit_passes() -> None:
    rows = _read_output_table("ratewall_tdc_forward_invariant_audit.csv")

    assert rows
    assert {row["audit_status"] for row in rows} == {"pass"}
    assert {row["main_offset_ratio_changed_this_tranche"] for row in rows} == {
        "false"
    }
    assert {row["dynamic_equation_changed_this_tranche"] for row in rows} == {
        "false"
    }
    assert {row["forbidden_switches_remain_disabled"] for row in rows} == {"true"}


def test_tdc_forward_scenario_decomposition_supports_charts() -> None:
    rows = _read_output_table("ratewall_tdc_forward_scenario_decomposition.csv")

    assert rows
    assert {row["assumption_mode"] for row in rows} == {"true"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["decomposition_component"] for row in rows} >= {
        "primary_fiscal_flow_to_du",
        "principal_to_du",
        "interest_to_du_direct_overlap",
        "auction_absorption_by_du",
    }
    current_2026 = [
        row
        for row in rows
        if row["scenario_id"] == "current_mix_baseline"
        and row["quarter"].startswith("2026")
    ]
    assert current_2026
    assert {
        row["direct_interest_overlap_component"]
        for row in current_2026
        if row["decomposition_component"] == "interest_to_du_direct_overlap"
    } == {"true"}


def test_canonical_tdc_accounting_path_is_accounting_only() -> None:
    rows = _read_output_table("ratewall_canonical_tdc_accounting_path.csv")

    assert rows
    assert {row["canonical_tdc_accounting_entry"] for row in rows} == {"true"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["path_type"] for row in rows} == {
        "historical",
        "forward_projection",
    }
    assert {row["source_project"] for row in rows if row["path_type"] == "historical"} == {
        "tdcest"
    }
    assert {
        row["source_project"] for row in rows if row["path_type"] == "forward_projection"
    } == {"tdcsim"}


def test_canonical_tdc_forward_component_identity_and_overlap() -> None:
    rows = [
        row
        for row in _read_output_table("ratewall_canonical_tdc_accounting_path.csv")
        if row["path_type"] == "forward_projection"
    ]

    assert rows
    for row in rows:
        tdc_change = Decimal(row["tdc_change_bil"])
        component_sum = sum(
            Decimal(row[field])
            for field in (
                "primary_fiscal_flow_to_du_bil",
                "interest_to_du_bil",
                "principal_to_du_bil",
                "auction_absorption_by_du_bil",
                "secondary_trades_net_bil",
                "other_bil",
            )
        )
        overlap = Decimal(row["direct_interest_overlap_cashflow_bil"])
        ex_overlap = Decimal(row["tdc_change_ex_direct_interest_overlap_bil"])

        assert abs(component_sum - tdc_change) <= Decimal("1e-7")
        assert row["component_identity_status"] == "pass"
        assert abs(ex_overlap - (tdc_change - overlap)) <= Decimal("1e-7")
        assert row["overlap_guardrail_status"] == "pass"
        assert row["principal_overlap_subtracted"] == "false"
        assert row["secondary_trade_status"] == "absent_not_imputed"
        assert row["other_status"] == "explicit_zero"


def test_canonical_tdc_stitched_path_keeps_historical_flow_only() -> None:
    rows = _read_output_table("ratewall_canonical_tdc_stitched_accounting_path.csv")
    historical_rows = [row for row in rows if row["path_segment"] == "historical_tdcest"]
    forward_rows = [row for row in rows if row["path_segment"] == "forward_tdcsim"]

    assert rows
    assert historical_rows
    assert forward_rows
    assert all(row["handoff_quarter"] for row in rows)
    assert {row["source_project"] for row in historical_rows} == {"tdcest"}
    assert {row["source_project"] for row in forward_rows} == {"tdcsim"}
    assert {row["component_detail_status"] for row in historical_rows} == {
        "historical_selected_series_component_detail_unavailable"
    }
    assert {row["component_identity_status"] for row in historical_rows} == {
        "not_applicable_historical_flow_only"
    }
    assert {row["primary_fiscal_flow_to_du_bil"] for row in historical_rows} == {""}
    assert {row["component_detail_status"] for row in forward_rows} == {
        "forward_tdcsim_full_component_detail"
    }
    assert {row["component_identity_status"] for row in forward_rows} == {"pass"}


def test_canonical_tdc_source_hierarchy_audit_passes() -> None:
    rows = _read_output_table(
        "ratewall_canonical_tdc_accounting_source_hierarchy_audit.csv"
    )

    assert rows
    assert {row["audit_status"] for row in rows} == {"pass"}
    assert {row["audit_item"] for row in rows} >= {
        "tdcest_historical_authority",
        "tdcsim_forward_mechanics_authority",
        "tdcmix_prior_not_holder_allocation_evidence",
        "weak_wamest_rows_sensitivity_only",
        "source_backed_inputs_recorded",
        "historical_component_detail_explicitly_unavailable",
        "no_total_deposit_growth_shortcut_or_arbitrary_beta",
        "no_residual_gap_stacked_as_live_drag",
        "direct_interest_overlap_not_double_counted",
    }


def test_backend_invariant_records_canonical_tdc_accounting_boundary() -> None:
    rows = _read_output_table("ratewall_tdc_equation_variant_registry.csv")

    assert rows
    core = next(
        row for row in rows if row["tdc_variant_id"] == "ru_flow_tier2_tdc_core_object"
    )
    assert core["replace_vs_stack_semantics"] == "replace_not_stack"
    assert core["admission_status"] == (
        "pass_central_tdc_object_family_assumption_mode_not_rw_y"
    )
    assert set(core["double_count_exclusion_pairs"].split(";")) == {
        "bank_balance_sheet",
        "direct_interest",
        "du_flow_shadow",
        "route_proxy",
    }
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["formula_replacement_allowed"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {
        "false"
    }


def test_interest_income_calibration_keeps_canonical_outputs_unmodified() -> None:
    solved_rows = _read_output_table("ratewall_wall_hit_scenarios.csv")
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")

    assert not any(
        row["assumption_set"].startswith("post_covid_interest_income")
        for row in solved_rows
    )
    interest_invariant = next(
        row
        for row in invariant_rows
        if row["audit_item"]
        == "interest_income_mpc_calibration_registry_assumption_only"
    )
    assert interest_invariant["audit_status"] == "pass"
    assert interest_invariant["main_offset_ratio_changed_this_tranche"] == "false"
    assert interest_invariant["dynamic_equation_changed_this_tranche"] == "false"
    assert interest_invariant["split_denominator_promotion_allowed"] == "false"
    assert interest_invariant["forbidden_switches_remain_disabled"] == "true"


def test_interest_income_calibration_forbidden_switches_false() -> None:
    disabled_fields = (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    )
    artifact_names = (
        "ratewall_interest_income_mpc_calibration_registry.csv",
        "ratewall_interest_income_public_proxy_catalog.csv",
        "ratewall_interest_income_proxy_range_registry.csv",
        "ratewall_interest_income_claim_boundary_audit.csv",
        "ratewall_post_covid_interest_income_wall_distance.csv",
        "ratewall_historical_iorb_demand_proxy_path.csv",
        "ratewall_historical_wall_ratio_path.csv",
        "ratewall_historical_assumption_mode_wall_ratio_path.csv",
        "ratewall_tdcest_historical_estimator_bridge.csv",
        "ratewall_tdcest_monetary_route_bridge.csv",
        "ratewall_tdcest_mmf_route_split_context.csv",
        "ratewall_tdcest_z1_domestic_nonbank_sector_context.csv",
        "ratewall_tdc_rolling_pass_through_context.csv",
        "ratewall_historical_tdc_wall_ratio_path.csv",
        "ratewall_historical_assumption_mode_tdc_wall_ratio_path.csv",
        "ratewall_tdc_other_component_bridge.csv",
        "ratewall_tdc_deposit_credit_decomposition.csv",
        "ratewall_tdc_double_count_guardrail.csv",
        "ratewall_tdc_net_ratewall_effect.csv",
        "ratewall_forecast_holder_tdc_consistency_bridge.csv",
    )

    for artifact_name in artifact_names:
        rows = _read_output_table(artifact_name)
        assert rows
        for field in disabled_fields:
            assert {row[field] for row in rows} == {"false"}


def test_generated_text_claim_scan_covers_interest_income_calibration_artifacts() -> None:
    rows = _read_output_table("ratewall_generated_text_claim_boundary_scan.csv")
    scanned_paths = {row["artifact_path"] for row in rows}

    assert {
        "outputs/tables/ratewall_interest_income_mpc_calibration_registry.csv",
        "outputs/tables/ratewall_interest_income_public_proxy_catalog.csv",
        "outputs/tables/ratewall_interest_income_proxy_range_registry.csv",
        "outputs/tables/ratewall_interest_income_claim_boundary_audit.csv",
        "outputs/tables/ratewall_post_covid_interest_income_wall_distance.csv",
        "outputs/tables/ratewall_historical_iorb_demand_proxy_path.csv",
        "outputs/tables/ratewall_historical_wall_ratio_path.csv",
        "outputs/tables/ratewall_historical_assumption_mode_wall_ratio_path.csv",
        "outputs/tables/ratewall_forecast_holder_tdc_consistency_bridge.csv",
    } <= scanned_paths
    assert {
        row["audit_status"]
        for row in rows
        if "interest_income" in row["artifact_path"]
    } == {"pass"}


def test_parameter_activation_ledger_covers_current_engine_parameter_universe() -> None:
    assumptions = load_ratewall_assumption_sets()
    metadata_fields = {
        "name",
        "description",
        "horizon",
        "assumption_status",
        "source_status",
        "editable_label",
        "unit_scope",
        "claim_boundary",
    }
    parameter_names = [
        field.name
        for field in dataclass_fields(type(assumptions[0]))
        if field.name not in metadata_fields
    ]
    rows = _read_output_table("ratewall_assumption_mode_parameter_activation_ledger.csv")

    assert len(rows) == len(assumptions) * len(parameter_names)
    assert {
        (row["assumption_set"], row["parameter_name"]) for row in rows
    } == {
        (assumption.name, parameter_name)
        for assumption in assumptions
        for parameter_name in parameter_names
    }
    assert {
        "engine_and_pack",
        "engine_only_missing_pack",
        "deprecated_compatibility_only",
    } <= {row["parameter_pack_coverage_status"] for row in rows}


def test_parameter_activation_ledger_places_promoted_sidecar_and_dynamic_parameters_correctly() -> None:
    rows = _read_output_table("ratewall_assumption_mode_parameter_activation_ledger.csv")
    by_parameter = {}
    for row in rows:
        by_parameter.setdefault(row["parameter_name"], []).append(row)

    assert {row["placement_layer"] for row in by_parameter["public_impulse_multiplier"]} == {
        "compatibility_metadata"
    }
    assert {
        row["deprecated_compatibility_status"]
        for row in by_parameter["public_impulse_multiplier"]
    } == {"deprecated_compatibility_only_neutral_required"}
    assert {
        row["placement_layer"]
        for row in by_parameter["foreign_treasury_holder_leakage_share"]
    } == {"static_sidecar"}
    assert all(
        row["static_sidecar_terms"] == "foreign_treasury_holder_leakage_drag_bil"
        for row in by_parameter["foreign_treasury_holder_leakage_share"]
    )
    assert {
        row["placement_layer"]
        for row in by_parameter["pension_insurance_pass_through_lag_years"]
    } == {"dynamic_sidecar"}
    assert {
        row["placement_layer"]
        for row in by_parameter["household_safe_asset_stock_share"]
    } == {"assumption_mode_static_entry"}
    for field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[field] for row in rows} == {"false"}


def test_dynamic_sidecar_family_summary_matches_underlying_paths() -> None:
    path_rows = _read_output_table("ratewall_assumption_mode_dynamic_sidecar_paths.csv")
    summary_rows = _read_output_table(
        "ratewall_assumption_mode_dynamic_sidecar_family_summary.csv"
    )
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in path_rows:
        key = (
            row["scenario"],
            row["dynamic_sidecar_family"],
            row["variant_label"],
            row["dynamic_sidecar_id"],
        )
        groups.setdefault(key, []).append(row)
    summary_by_key = {
        (
            row["scenario"],
            row["dynamic_sidecar_family"],
            row["variant_label"],
            row["dynamic_sidecar_id"],
        ): row
        for row in summary_rows
    }

    assert summary_by_key.keys() == groups.keys()
    assert len(summary_rows) == 88
    for key, rows in groups.items():
        summary = summary_by_key[key]
        values = [Decimal(row["sidecar_value_bil"]) for row in rows]
        peak_index = max(range(len(rows)), key=lambda idx: abs(values[idx]))
        assert int(summary["period_count"]) == len(rows)
        assert int(summary["nonzero_period_count"]) == sum(1 for value in values if value)
        assert Decimal(summary["cumulative_value_bil"]) == sum(values, Decimal("0"))
        assert summary["peak_period"] == rows[peak_index]["period"]
        assert Decimal(summary["peak_value_bil"]) == values[peak_index]
        assert summary["canonical_path_unchanged_flag"] == "true"
        assert summary["additivity_scope"] == "alternative_dynamic_variant_not_additive"
    assert {row["path_shape_label"] for row in summary_rows} <= {
        "all_zero",
        "single_period_impulse",
        "flat_nonzero_plateau",
        "monotone_ramp_up",
        "monotone_ramp_down",
        "hump_shaped",
        "u_shaped_or_reversal",
        "mixed_nonmonotone",
    }


def test_dynamic_secondary_paths_cover_and_guard_dynamic_sidecars() -> None:
    sidecar_rows = _read_output_table("ratewall_assumption_mode_dynamic_sidecar_paths.csv")
    secondary_rows = _read_output_table(
        "ratewall_assumption_mode_dynamic_sidecar_secondary_paths.csv"
    )

    def key(row: dict[str, str]) -> tuple[str, str, str]:
        return (row["scenario"], row["period"], row["dynamic_sidecar_id"])

    assert {key(row) for row in secondary_rows} == {key(row) for row in sidecar_rows}
    assert len(secondary_rows) == len(sidecar_rows) == 1408
    assert {row["canonical_dynamic_path_changed"] for row in secondary_rows} == {
        "false"
    }
    assert {row["secondary_ratio_not_classifier"] for row in secondary_rows} == {
        "true"
    }
    assert {row["canonical_ratio_entry"] for row in secondary_rows} == {"false"}
    public_rows = [
        row
        for row in secondary_rows
        if row["dynamic_sidecar_family"] == "public_finance_remittance_timing"
    ]
    assert public_rows
    assert {row["secondary_ratio_constructible"] for row in public_rows} == {
        "false"
    }
    assert {row["constructibility_blocker"] for row in public_rows} == {
        "already_in_canonical_dynamic_path_do_not_reapply"
    }


def test_dynamic_secondary_paths_apply_family_specific_adjustments() -> None:
    rows = _read_output_table("ratewall_assumption_mode_dynamic_sidecar_secondary_paths.csv")
    sample_by_family = {}
    for row in rows:
        if row["secondary_ratio_constructible"] == "true" and Decimal(
            row["sidecar_value_bil"]
        ):
            sample_by_family.setdefault(row["dynamic_sidecar_family"], row)

    assert {
        "cre_refi_pressure",
        "pension_contribution_relief",
        "retirement_insurance_yield_spend",
    } <= set(sample_by_family)
    cre = sample_by_family["cre_refi_pressure"]
    assert cre["secondary_adjustment_basis"] == "denominator_addition"
    assert Decimal(cre["secondary_numerator_adjustment_bil"]) == Decimal("0")
    assert Decimal(cre["secondary_denominator_adjustment_bil"]) == Decimal(
        cre["sidecar_value_bil"]
    )
    expected_cre_ratio = Decimal(cre["canonical_countervailing_bil"]) / (
        Decimal(cre["canonical_denominator_bil"]) + Decimal(cre["sidecar_value_bil"])
    )
    assert Decimal(cre["secondary_ratio"]) == expected_cre_ratio

    for family in ("pension_contribution_relief", "retirement_insurance_yield_spend"):
        row = sample_by_family[family]
        assert row["secondary_adjustment_basis"] == "numerator_addition"
        assert Decimal(row["secondary_numerator_adjustment_bil"]) == Decimal(
            row["sidecar_value_bil"]
        )
        assert Decimal(row["secondary_denominator_adjustment_bil"]) == Decimal("0")
        expected_ratio = (
            Decimal(row["canonical_countervailing_bil"])
            + Decimal(row["sidecar_value_bil"])
        ) / Decimal(row["canonical_denominator_bil"])
        assert Decimal(row["secondary_ratio"]) == expected_ratio


def test_dynamic_secondary_frontier_matches_path_peaks_and_crossings() -> None:
    path_rows = _read_output_table(
        "ratewall_assumption_mode_dynamic_sidecar_secondary_paths.csv"
    )
    frontier_rows = _read_output_table(
        "ratewall_assumption_mode_dynamic_sidecar_secondary_frontier.csv"
    )
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in path_rows:
        groups.setdefault((row["scenario"], row["dynamic_sidecar_id"]), []).append(row)
    frontier_by_key = {
        (row["scenario"], row["dynamic_sidecar_id"]): row for row in frontier_rows
    }

    assert frontier_by_key.keys() == groups.keys()
    assert len(frontier_rows) == 88
    for key, rows in groups.items():
        frontier = frontier_by_key[key]
        if frontier["secondary_ratio_constructible"] == "false":
            assert frontier["frontier_rank_within_scenario"] == "not_applicable"
            assert frontier["constructibility_blocker"]
            continue
        peak = max(
            rows,
            key=lambda row: Decimal(row["absolute_ratio_gap"]).quantize(
                Decimal("0.000000000001")
            ),
        )
        crossing_rows = [
            row for row in rows if row["secondary_wall_hit_under_secondary_ratio"] == "true"
        ]
        assert frontier["peak_gap_period"] == peak["period"]
        assert frontier["absolute_peak_ratio_gap"] == peak["absolute_ratio_gap"]
        assert frontier["secondary_ratio_at_peak_gap"] == peak["secondary_ratio"]
        assert frontier["any_secondary_crossing"] == str(bool(crossing_rows)).lower()
        assert frontier["first_secondary_crossing_period"] == (
            crossing_rows[0]["period"] if crossing_rows else ""
        )
        assert frontier["last_secondary_crossing_period"] == (
            crossing_rows[-1]["period"] if crossing_rows else ""
        )
        assert frontier["cross_family_combination_status"] == (
            "alternative_dynamic_variant_not_additive"
        )
        assert frontier["dynamic_sidecar_only"] == "true"
        assert frontier["secondary_ratio_not_classifier"] == "true"
        assert frontier["canonical_ratio_entry"] == "false"


def test_channel_status_crosswalk_covers_all_proxy_rows() -> None:
    proxy_rows = _read_output_table("ratewall_financialization_proxy_registry.csv")
    crosswalk_rows = _read_output_table(
        "ratewall_assumption_mode_channel_status_crosswalk.csv"
    )
    linked_proxy_ids = {
        proxy_id
        for row in crosswalk_rows
        for proxy_id in row["linked_proxy_ids"].split(";")
        if proxy_id
    }

    assert {row["proxy_id"] for row in proxy_rows} <= linked_proxy_ids
    assert len(crosswalk_rows) == 21
    assert {row["claim_boundary"] for row in crosswalk_rows} == {
        "channel_status_crosswalk_not_evidence_mode_promotion"
    }


def test_channel_status_crosswalk_special_cases_are_mapped_explicitly() -> None:
    rows = {
        row["channel_key"]: row
        for row in _read_output_table("ratewall_assumption_mode_channel_status_crosswalk.csv")
    }

    assert (
        rows["cre_refi_pressure"]["static_sidecar_status"]
        == "sidecar_sensitivity_only"
    )
    assert "dynamic_cre_refi_pressure_low" in rows["cre_refi_pressure"][
        "dynamic_sidecar_id_list"
    ]
    assert rows["public_finance_remittance_timing"]["dynamic_sidecar_id_list"] == (
        "dynamic_public_finance_current_support;dynamic_public_finance_future_drag"
    )
    for channel_key in (
        "public_finance_remittance_timing",
        "pension_contribution_relief",
        "retirement_insurance_yield_spend",
    ):
        assert rows[channel_key]["next_gate_or_blocker"] == (
            "dynamic_sidecar_only_no_canonical_path_change"
        )
        assert rows[channel_key]["dynamic_variant_status"] == "dynamic_only_primary"
        assert rows[channel_key]["canonical_dynamic_path_unchanged"] == "true"
        assert rows[channel_key]["static_sidecar_status"] == (
            "dynamic_sidecar_only_not_static_sidecar"
        )
    assert (
        rows["pension_contribution_relief"]["context_id"]
        == rows["retirement_insurance_yield_spend"]["context_id"]
        == "insurance_pension_asset_liability"
    )
    assert rows["denominator_sidecar_overlap_discount"]["context_id"] == ""
    assert rows["denominator_sidecar_overlap_discount"]["linked_proxy_ids"] == ""
    assert {
        rows["composite_financialization_index"]["final_interpretation"],
        rows["public_aggregate_causal_financialization_regression"][
            "final_interpretation"
        ],
    } == {"avoid_nonmodel_candidate"}
    assert {
        rows["composite_financialization_index"]["canonical_static_status"],
        rows["public_aggregate_causal_financialization_regression"][
            "canonical_static_status"
        ],
    } == {"not_canonical"}


def test_restricted_protocol_falsification_matrix_covers_all_exhausted_gates() -> None:
    matrix_rows = _read_output_table("ratewall_restricted_protocol_falsification_matrix.csv")
    closure_rows = _read_output_table("ratewall_source_gate_exhaustion_closure.csv")

    assert {row["gate_id"] for row in matrix_rows} == {
        row["gate_id"] for row in closure_rows
    }
    assert len(matrix_rows) == 5
    assert {row["promotion_gate_passed"] for row in matrix_rows} == {"false"}
    assert all(row["falsification_rule"] for row in matrix_rows)
    assert all(row["representativeness_rule"] for row in matrix_rows)
    assert all(row["abandonment_rule"] for row in matrix_rows)


def test_assumption_mode_formula_identity_audit_static_and_sidecar_rows_pass() -> None:
    rows = _read_output_table("ratewall_assumption_mode_formula_identity_audit.csv")

    assert len(rows) == len({row["assumption_set"] for row in rows}) * len(
        {row["identity_id"] for row in rows}
    )
    assert {row["identity_status"] for row in rows} == {"pass"}
    assert {
        "household_safe_yield_capture_offset_identity",
        "deposit_mmf_substitution_drag_identity",
        "firm_liquid_asset_cushion_offset_identity",
        "foreign_treasury_holder_leakage_drag_identity",
        "recipient_leakage_sidecar_offset_ratio_identity",
        "denominator_sidecar_overlap_discount_identity",
        "denominator_sidecar_offset_ratio_identity",
        "promoted_contribution_signed_sum_bridge_identity",
        "recipient_leakage_sidecar_signed_sum_bridge_identity",
        "denominator_sidecar_signed_sum_bridge_identity",
    } <= {row["identity_id"] for row in rows}
    assert {row["canonical_ratio_entry_changed"] for row in rows} == {"false"}
    assert {row["formula_replacement_allowed"] for row in rows} == {"false"}


def test_assumption_mode_formula_identity_audit_denominator_overlap_case() -> None:
    rows = _read_output_table("ratewall_assumption_mode_formula_identity_audit.csv")
    overlap_rows = [
        row
        for row in rows
        if row["assumption_set"]
        == "assumption_mode_combined_denominator_sidecar_overlap_discounted"
    ]
    by_identity = {row["identity_id"]: row for row in overlap_rows}

    assert Decimal(
        by_identity["denominator_sidecar_overlap_discount_identity"][
            "recomputed_value"
        ]
    ) > Decimal("0")
    assert (
        by_identity["denominator_sidecar_signed_sum_bridge_identity"][
            "reported_value"
        ]
        == by_identity["denominator_sidecar_signed_sum_bridge_identity"][
            "recomputed_value"
        ]
    )
    assert (
        by_identity["denominator_sidecar_offset_ratio_identity"]["reported_value"]
        == by_identity["denominator_sidecar_offset_ratio_identity"][
            "recomputed_value"
        ]
    )


def test_assumption_mode_formula_identity_audit_forbidden_switches_false() -> None:
    rows = _read_output_table("ratewall_assumption_mode_formula_identity_audit.csv")
    for field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[field] for row in rows} == {"false"}


def test_restricted_protocol_field_contract_expands_all_gate_spec_fields() -> None:
    contract_rows = _read_output_table("ratewall_restricted_protocol_field_contract.csv")
    spec_rows = _read_output_table("ratewall_restricted_data_gate_spec.csv")
    expected_pairs = {
        (row["gate_id"], field.strip())
        for row in spec_rows
        for field in row["must_have_schema_fields"].split(";")
        if field.strip()
    }

    assert {(row["gate_id"], row["required_field"]) for row in contract_rows} == (
        expected_pairs
    )
    assert len(contract_rows) == len(expected_pairs) == 45
    assert {row["current_status"] for row in contract_rows} == {
        "design_only_no_data_admitted"
    }
    assert {row["promotion_gate_passed"] for row in contract_rows} == {"false"}
    assert {row["evidence_admission_status"] for row in contract_rows} == {
        "not_current_evidence"
    }


def test_restricted_protocol_field_contract_roles_and_rules_present() -> None:
    rows = _read_output_table("ratewall_restricted_protocol_field_contract.csv")
    row_by_gate_field = {
        (row["gate_id"], row["required_field"]): row for row in rows
    }

    assert row_by_gate_field[
        ("consumer_credit_denominator_promotion_gate", "apr_or_index_rate")
    ]["field_role"] == "rate_or_policy_exposure"
    assert row_by_gate_field[
        ("cre_refinancing_denominator_promotion_gate", "loan_balance")
    ]["field_role"] == "exposure_or_cashflow_measurement"
    assert row_by_gate_field[
        ("interest_income_tax_clawback_wrapper_promotion_gate", "taxable_account_flag")
    ]["field_role"] == "tax_or_account_classification"
    assert row_by_gate_field[
        ("foreign_treasury_holder_leakage_promotion_gate", "timing_lag")
    ]["field_role"] == "timing"
    assert all(row["falsification_rule"] for row in rows)
    assert all(row["representativeness_rule"] for row in rows)
    assert all(row["abandonment_rule"] for row in rows)
    for field in (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    ):
        assert {row[field] for row in rows} == {"false"}


def test_context_surface_no_main_ratio_audit_covers_all_noncanonical_inventory_items() -> None:
    rows = _read_output_table("ratewall_context_surface_no_main_ratio_audit.csv")
    expected_inventory_tables = {
        artifact
        for artifact, *_ in databook_legacy.NONCANONICAL_SURFACE_INVENTORY
    }
    audited_artifacts = {row["artifact_name"] for row in rows}

    assert {row["audit_status"] for row in rows} == {"pass"}
    assert {row["materialization_contract_status"] for row in rows} == {"pass"}
    assert expected_inventory_tables <= audited_artifacts
    assert {
        "ratewall_assumption_mode_parameter_activation_ledger.csv",
        "ratewall_assumption_mode_dynamic_sidecar_family_summary.csv",
        "ratewall_assumption_mode_dynamic_sidecar_secondary_paths.csv",
        "ratewall_assumption_mode_dynamic_sidecar_secondary_frontier.csv",
        "ratewall_assumption_mode_channel_status_crosswalk.csv",
        "ratewall_assumption_mode_formula_identity_audit.csv",
        "ratewall_restricted_protocol_falsification_matrix.csv",
        "ratewall_restricted_protocol_field_contract.csv",
        "ratewall_context_surface_no_main_ratio_audit.csv",
        "ratewall_assumption_mode_sidecar_bundle_frontier.csv",
        "ratewall_generated_text_claim_boundary_scan.csv",
        "ratewall_tdc_other_component_bridge.csv",
        "ratewall_tdc_deposit_credit_decomposition.csv",
        "ratewall_tdc_double_count_guardrail.csv",
        "ratewall_tdc_net_ratewall_effect.csv",
        "ratewall_forecast_holder_tdc_consistency_bridge.csv",
    } <= audited_artifacts
    for field in (
        "outside_canonical_numerator",
        "outside_canonical_denominator",
        "outside_canonical_classifier",
        "outside_canonical_dynamic_paths",
        "outside_split_denominator_promotion",
    ):
        assert {row[field] for row in rows} == {"true"}


def test_context_surface_audit_uses_actual_row_counts_and_verified_listings() -> None:
    rows = _read_output_table("ratewall_context_surface_no_main_ratio_audit.csv")
    rows_by_artifact = {row["artifact_name"]: row for row in rows}
    invariant_rows = _read_output_table("ratewall_backend_invariant_guardrail_audit.csv")

    assert rows_by_artifact["ratewall_backend_invariant_guardrail_audit.csv"][
        "actual_row_count"
    ] == str(len(invariant_rows))
    assert rows_by_artifact["ratewall_context_surface_no_main_ratio_audit.csv"][
        "actual_row_count"
    ] == str(len(rows))
    assert {row["row_count_match_status"] for row in rows} == {"pass"}
    assert all(
        row["expected_row_count"] == ""
        or row["expected_row_count"] == row["disk_row_count"]
        for row in rows
    )
    for field in (
        "release_manifest_verified",
        "artifact_index_verified",
        "table_plate_verified",
        "release_hash_manifest_verified",
        "source_archive_verified",
    ):
        assert {row[field] for row in rows} <= {
            "not_available_pre_release_build",
            "true",
        }
    assert all(
        row["readme_verified"] == "true"
        or (
            row["mode_layer"] == "backend_expansion_context_design"
            and "readme_required=false" in row["proof_basis"]
        )
        for row in rows
    )
    for artifact in (
        "ratewall_assumption_mode_formula_identity_audit.csv",
        "ratewall_restricted_protocol_field_contract.csv",
        "ratewall_backend_invariant_guardrail_audit.csv",
        "ratewall_context_surface_no_main_ratio_audit.csv",
        "ratewall_tdc_other_component_bridge.csv",
        "ratewall_tdc_deposit_credit_decomposition.csv",
        "ratewall_tdc_double_count_guardrail.csv",
        "ratewall_tdc_net_ratewall_effect.csv",
        "ratewall_forecast_holder_tdc_consistency_bridge.csv",
    ):
        row = rows_by_artifact[artifact]
        assert row["actual_row_count_status"] == "current_nonzero"
        assert row["release_manifest_verified"] in {
            "not_available_pre_release_build",
            "true",
        }
        assert row["readme_verified"] in {"not_available_pre_release_build", "true"}
        assert row["artifact_index_verified"] in {
            "not_available_pre_release_build",
            "true",
        }
        assert row["table_plate_verified"] in {
            "not_available_pre_release_build",
            "true",
        }
        assert row["release_hash_manifest_verified"] in {
            "not_available_pre_release_build",
            "true",
        }
        assert row["source_archive_verified"] in {
            "not_available_pre_release_build",
            "true",
        }


def test_sidecar_reasonableness_excludes_dynamic_only_rows_from_static_activation_count() -> None:
    contribution_rows = _read_output_table(
        "ratewall_assumption_mode_sidecar_contributions.csv"
    )
    reasonableness_rows = _read_output_table(
        "ratewall_assumption_mode_sidecar_reasonableness_audit.csv"
    )
    static_counts: dict[tuple[str, str], int] = {}
    for row in contribution_rows:
        if (
            row["sidecar_metric_scope"] != "dynamic_compatibility_only"
            and Decimal(row["channel_value_bil"]) != Decimal("0")
        ):
            static_counts[(row["assumption_set"], row["horizon"])] = (
                static_counts.get((row["assumption_set"], row["horizon"]), 0) + 1
            )

    for row in reasonableness_rows:
        if row["audit_metric"] == "active_sidecar_contribution_count":
            key = (row["assumption_set"], row["horizon"])
            assert int(Decimal(row["metric_value"])) == static_counts.get(key, 0)


def test_sidecar_bundle_frontier_excludes_dynamic_sidecars() -> None:
    rows = _read_output_table("ratewall_assumption_mode_sidecar_bundle_frontier.csv")

    assert rows
    assert {row["static_sidecar_only"] for row in rows} == {"true"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["secondary_ratio_not_classifier"] for row in rows} == {"true"}
    dynamic_tokens = ("dynamic_", "pension_contribution", "retirement_insurance")
    assert not any(
        token in row["bundle_id"]
        or token in row["bundle_family"]
        or token in row["bundle_channels"]
        for row in rows
        for token in dynamic_tokens
    )


def test_sidecar_bundle_frontier_no_composite_financialization_index() -> None:
    rows = _read_output_table("ratewall_assumption_mode_sidecar_bundle_frontier.csv")

    forbidden_tokens = {
        "all_financialization",
        "all_sidecars_canonical_ratio",
        "financialization_composite_score",
        "composite_financialization_index",
        "dynamic_plus_static_sidecar_total",
    }
    assert not any(
        token in row["bundle_id"]
        or token in row["bundle_family"]
        or token in row["bundle_channels"]
        for row in rows
        for token in forbidden_tokens
    )
    for row in rows:
        if row["bundle_id"] == "recipient_plus_denominator_cross_family_diagnostic":
            assert row["cross_family_combination_status"] == (
                "synthetic_secondary_diagnostic_not_additive_not_classifier"
            )
        else:
            assert row["cross_family_combination_status"] == (
                "within_family_static_sidecar_bundle"
            )


def test_sidecar_bundle_frontier_overlap_discount_math_matches_solved_rows() -> None:
    rows = _read_output_table("ratewall_assumption_mode_sidecar_bundle_frontier.csv")
    solved_by_assumption = {
        row["assumption_set"]: row
        for row in _read_output_table("ratewall_wall_hit_scenarios.csv")
    }
    discounted_rows = [
        row for row in rows if row["bundle_id"] == "denominator_drag_bundle_discounted"
    ]
    undiscounted_rows = [
        row
        for row in rows
        if row["bundle_id"] == "denominator_drag_bundle_undiscounted_review"
    ]

    assert discounted_rows
    assert undiscounted_rows
    for row in discounted_rows:
        solved = solved_by_assumption[row["assumption_set"]]
        conventional_drag = Decimal(solved["conventional_contractionary_effect_bil"])
        adjusted_drag = Decimal(
            solved["denominator_sidecar_adjusted_conventional_drag_bil"]
        )
        expected_ratio = (
            Decimal(solved["scalar_countervailing_total_bil"]) / adjusted_drag
        )
        assert Decimal(row["overlap_discount_bil"]) == Decimal(
            solved["denominator_sidecar_overlap_discount_bil"]
        )
        assert Decimal(row["overlap_discount_share"]) == Decimal(
            solved["denominator_sidecar_overlap_discount_share"]
        )
        assert Decimal(row["bundle_denominator_adjustment_bil"]) == (
            adjusted_drag - conventional_drag
        )
        assert abs(Decimal(row["bundle_secondary_ratio"]) - expected_ratio) < Decimal(
            "1e-24"
        )

    combined = next(
        row
        for row in discounted_rows
        if row["assumption_set"]
        == "assumption_mode_combined_denominator_sidecar_overlap_discounted"
    )
    assert combined["overlap_discount_status"] == "active_multi_channel_discount"
    assert Decimal(combined["overlap_discount_bil"]) > Decimal("0")

    for row in undiscounted_rows:
        solved = solved_by_assumption[row["assumption_set"]]
        conventional_drag = Decimal(solved["conventional_contractionary_effect_bil"])
        positive_drag = Decimal(solved["denominator_sidecar_positive_drag_total_bil"])
        housing_shield = Decimal(solved["housing_lockin_payment_shield_sidecar_bil"])
        expected_denominator = conventional_drag + positive_drag - housing_shield
        expected_ratio = (
            Decimal(solved["scalar_countervailing_total_bil"])
            / expected_denominator
        )
        assert Decimal(row["bundle_denominator_adjustment_bil"]) == (
            expected_denominator - conventional_drag
        )
        assert abs(Decimal(row["bundle_secondary_ratio"]) - expected_ratio) < Decimal(
            "1e-24"
        )


def test_sidecar_bundle_frontier_secondary_label_never_rewrites_canonical() -> None:
    rows = _read_output_table("ratewall_assumption_mode_sidecar_bundle_frontier.csv")
    solved_by_assumption = {
        row["assumption_set"]: row
        for row in _read_output_table("ratewall_wall_hit_scenarios.csv")
    }

    assert {row["canonical_wall_hit_label_preserved"] for row in rows} == {"true"}
    assert {
        row["bundle_id"] for row in rows
    } >= {"housing_lockin_denominator_shield_bundle"}
    for row in rows:
        solved = solved_by_assumption[row["assumption_set"]]
        assert row["canonical_offset_ratio"] == solved["ratewall_offset_ratio"]
        assert (
            row["canonical_wall_hit_under_assumptions"]
            == solved["wall_hit_under_assumptions"]
        )
        assert row["secondary_label_differs_from_canonical"] == str(
            row["bundle_wall_hit_under_secondary_ratio"]
            != row["canonical_wall_hit_under_assumptions"]
        ).lower()


def test_sidecar_bundle_frontier_forbidden_switches_false() -> None:
    rows = _read_output_table("ratewall_assumption_mode_sidecar_bundle_frontier.csv")
    disabled_fields = (
        "empirical_claim_enabled",
        "policy_failure_claim_enabled",
        "pricing_output_enabled",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
        "tax_output_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "reset_calendar_construction_enabled",
        "raw_rate_shock_enabled",
        "causal_financialization_claim_enabled",
    )

    assert rows
    for field in disabled_fields:
        assert {row[field] for row in rows} == {"false"}


def test_generated_text_claim_boundary_scan_runs_on_reports_tables_and_manifests() -> None:
    rows = _read_output_table("ratewall_generated_text_claim_boundary_scan.csv")

    assert rows
    assert {
        "markdown_report",
        "csv_table",
        "json_manifest",
    } <= {row["artifact_kind"] for row in rows}
    assert {
        "empirical_threshold_claim",
        "policy_failure_claim",
        "higher_rates_always_raise_inflation_claim",
        "pricing_output_claim",
        "incidence_claim",
        "welfare_claim",
        "tax_output_claim",
        "mpc_claim",
        "holder_allocation_claim",
        "reset_calendar_construction_claim",
        "raw_rate_shock_claim",
        "causal_financialization_claim",
        "split_denominator_promotion_claim",
        "evidence_mode_promotion_claim",
        "canonical_sidecar_promotion_claim",
        "composite_financialization_index_claim",
    } == {row["claim_rule_id"] for row in rows}
    assert {
        "outputs/reports/ratewall_public_readme.md",
        "outputs/reports/ratewall_table_plate.md",
        "outputs/reports/ratewall_release_artifact_index.md",
        "outputs/tables/ratewall_release_manifest.json",
    } <= {row["artifact_path"] for row in rows}
    assert "outputs/tables/ratewall_generated_text_claim_boundary_scan.csv" not in {
        row["artifact_path"] for row in rows
    }


def test_generated_text_claim_boundary_scan_all_rows_pass() -> None:
    rows = _read_output_table("ratewall_generated_text_claim_boundary_scan.csv")

    assert rows
    assert {row["audit_status"] for row in rows} == {"pass"}
    assert {row["claim_boundary"] for row in rows} == {
        "generated_text_claim_boundary_scan_not_claim_adjudication_not_evidence_promotion"
    }


def test_generated_text_claim_boundary_scan_allows_disabled_boundary_statements() -> None:
    rows = _read_output_table("ratewall_generated_text_claim_boundary_scan.csv")
    rows_with_matches = [
        row for row in rows if int(row["total_match_count"]) > 0
    ]

    assert rows_with_matches
    assert any(
        row["claim_rule_id"] == "higher_rates_always_raise_inflation_claim"
        and int(row["allowed_boundary_match_count"]) > 0
        for row in rows_with_matches
    )
    assert all(
        int(row["allowed_boundary_match_count"])
        == int(row["total_match_count"])
        for row in rows_with_matches
    )
    assert any(row["allowed_boundary_pattern_hit"] for row in rows_with_matches)


def test_generated_text_claim_boundary_scan_rejects_bare_forbidden_phrases(
    tmp_path: Path,
) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (tmp_path / "tables").mkdir()
    (reports / "bare_forbidden.md").write_text(
        "\n".join(
            [
                "This release provides pricing output.",
                "The backend includes a welfare claim.",
                "The table contains incidence output results.",
                "MPC output is reported.",
                "Holder allocation output is reported.",
            ]
        ),
        encoding="utf-8",
    )

    rows = generated_text_claim_boundary_scan_rows(tmp_path)
    failing_rules = {
        row["claim_rule_id"]
        for row in rows
        if row["artifact_path"].endswith("bare_forbidden.md")
        and row["audit_status"] == "fail"
    }

    assert {
        "pricing_output_claim",
        "welfare_claim",
        "incidence_claim",
        "mpc_claim",
        "holder_allocation_claim",
    } <= failing_rules


def test_generated_text_claim_boundary_scan_allows_explicit_disabled_language(
    tmp_path: Path,
) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (tmp_path / "tables").mkdir()
    (reports / "bounded.md").write_text(
        "\n".join(
            [
                "Pricing output remains disabled.",
                "Holder allocation output is not enabled.",
                "Welfare claim language is not a claim.",
            ]
        ),
        encoding="utf-8",
    )

    rows = generated_text_claim_boundary_scan_rows(tmp_path)
    matched_rows = [
        row
        for row in rows
        if row["artifact_path"].endswith("bounded.md")
        and int(row["total_match_count"])
    ]

    assert matched_rows
    assert {row["audit_status"] for row in matched_rows} == {"pass"}
    assert all(row["allowed_boundary_pattern_hit"] for row in matched_rows)


def test_generated_text_claim_boundary_scan_does_not_self_qualify_matches(
    tmp_path: Path,
) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (tmp_path / "tables").mkdir()
    (reports / "self_qualifying.md").write_text(
        "The appendix lists pricing output and welfare claim results.",
        encoding="utf-8",
    )

    rows = generated_text_claim_boundary_scan_rows(tmp_path)
    matched_rows = [
        row
        for row in rows
        if row["artifact_path"].endswith("self_qualifying.md")
        and int(row["total_match_count"])
    ]

    assert matched_rows
    assert {row["audit_status"] for row in matched_rows} == {"fail"}


def test_generated_text_claim_boundary_scan_csv_false_does_not_qualify_row(
    tmp_path: Path,
) -> None:
    tables = tmp_path / "tables"
    tables.mkdir()
    (tmp_path / "reports").mkdir()
    (tables / "claims.csv").write_text(
        "description,generic_flag\n"
        '"This release provides pricing output",false\n',
        encoding="utf-8",
    )

    rows = generated_text_claim_boundary_scan_rows(tmp_path)
    pricing_row = next(
        row
        for row in rows
        if row["artifact_path"].endswith("claims.csv")
        and row["claim_rule_id"] == "pricing_output_claim"
    )

    assert pricing_row["total_match_count"] == "1"
    assert pricing_row["audit_status"] == "fail"
    assert pricing_row["allowed_boundary_pattern_hit"] == ""


def test_paper_forbidden_switches_false_requires_every_switch_field() -> None:
    complete_row = {
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

    assert _paper_forbidden_switches_false([complete_row])
    missing_row = dict(complete_row)
    missing_row.pop("tax_output_enabled")
    assert not _paper_forbidden_switches_false([missing_row])
    enabled_row = dict(complete_row)
    enabled_row["tax_output_enabled"] = "true"
    assert not _paper_forbidden_switches_false([enabled_row])


def test_generated_text_claim_boundary_scan_flags_no_unqualified_forbidden_claims() -> None:
    rows = _read_output_table("ratewall_generated_text_claim_boundary_scan.csv")

    assert sum(
        int(row["forbidden_unqualified_match_count"]) for row in rows
    ) == 0
    assert {row["sample_unqualified_match"] for row in rows} == {""}


def test_release_manifest_references_existing_artifacts() -> None:
    manifest = json.loads(
        Path("outputs/tables/ratewall_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    referenced_paths = {
        Path(path)
        for paths in manifest["artifact_layers"].values()
        for path in paths
    }

    assert {
        Path("outputs/tables/ratewall_assumption_mode_parameter_activation_ledger.csv"),
        Path("outputs/tables/ratewall_assumption_mode_dynamic_sidecar_family_summary.csv"),
        Path("outputs/tables/ratewall_assumption_mode_dynamic_sidecar_secondary_paths.csv"),
        Path("outputs/tables/ratewall_assumption_mode_dynamic_sidecar_secondary_frontier.csv"),
        Path("outputs/tables/ratewall_assumption_mode_channel_status_crosswalk.csv"),
        Path("outputs/tables/ratewall_restricted_protocol_falsification_matrix.csv"),
        Path("outputs/tables/ratewall_context_surface_no_main_ratio_audit.csv"),
        Path("outputs/tables/ratewall_assumption_mode_sidecar_bundle_frontier.csv"),
        Path("outputs/tables/ratewall_generated_text_claim_boundary_scan.csv"),
        Path("outputs/tables/ratewall_tdc_other_component_bridge.csv"),
        Path("outputs/tables/ratewall_tdc_deposit_credit_decomposition.csv"),
        Path("outputs/tables/ratewall_tdc_double_count_guardrail.csv"),
        Path("outputs/tables/ratewall_tdc_net_ratewall_effect.csv"),
        Path("outputs/tables/ratewall_pce_dpi_source_refresh_contract.csv"),
        Path("outputs/tables/ratewall_conventional_drag_calibration_route.csv"),
        Path("outputs/tables/ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv"),
        Path("outputs/tables/ratewall_policy_path_exposure_vector_design_gate.csv"),
        Path("outputs/tables/ratewall_tdsp_pce_dpi_policy_path_admission_audit.csv"),
    } <= referenced_paths
    recursive_archive_self_reference = Path(
        "outputs/release/ratewall_release_23_0_source_archive.zip"
    )
    required_current_paths = {
        Path("outputs/tables/ratewall_assumption_mode_parameter_activation_ledger.csv"),
        Path("outputs/tables/ratewall_generated_text_claim_boundary_scan.csv"),
        Path("outputs/tables/ratewall_tdc_double_count_guardrail.csv"),
        Path("outputs/tables/ratewall_tdc_net_ratewall_effect.csv"),
        Path("outputs/tables/ratewall_policy_path_exposure_vector_design_gate.csv"),
    }
    assert required_current_paths <= referenced_paths
    assert all(path.exists() for path in required_current_paths)
    assert recursive_archive_self_reference in referenced_paths
