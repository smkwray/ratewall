from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.databook.denominator_response_coefficient import (
    FRBUS_STRUCTURAL_COEFFICIENT,
    FRBUS_STRUCTURAL_PROFILE_ID,
)
from ratewall.databook.tdcsim_cbo_contracts import (
    CBO_CANONICAL_ENTRY_DECISION_FIELDS,
    CBO_CORE_SCENARIO_INTERPRETATION_FIELDS,
    CBO_CURVE_DENOMINATOR_EMPIRICAL_STATUS_FIELDS,
    CBO_CURVE_DENOMINATOR_INPUT_FIELDS,
    CBO_CURVE_SENSITIVE_DENOMINATOR_ASSUMPTION_BOUND_FIELDS,
    CBO_EMPIRICAL_SCENARIO_INTERPRETATION_FIELDS,
    CBO_EMPIRICAL_TERM_PREMIUM_COMPARISON_FIELDS,
    CBO_FISCAL_YEAR_RATIO_INPUT_FIELDS,
    CBO_MATCHED_PERIOD_RESPONSE_FIELDS,
    CBO_MATCHED_RESPONSE_COEFFICIENT_FIELDS,
    CBO_MODEL_SCENARIO_BETA_CHI_ROBUSTNESS_FIELDS,
    CBO_MODEL_SCENARIO_BETA_CHI_SIGN_STABILITY_FIELDS,
    CBO_MODEL_SCENARIO_MATERIALITY_CLASSIFICATION_FIELDS,
    CBO_MODEL_SCENARIO_INTERPRETATION_SYNTHESIS_FIELDS,
    CBO_MODEL_SCENARIO_SUMMARY_FIELDS,
    CBO_ROUTE_STOCK_CLOSURE_FIELDS,
    CBO_SCENARIO_EFFECT_FIELDS,
    CBO_SCENARIO_LEVER_DIAGNOSTIC_FIELDS,
    CBO_SETTLEMENT_ACCRUAL_BRIDGE_FIELDS,
    TDCSIM_CBO_CBO_GDP_SCALED_DENOMINATOR_SCOPE,
    COMMON_METADATA_FIELDS,
    EXPECTED_TDC_AMOUNT_BASIS,
    EXPECTED_TDC_OVERLAP_POLICY,
    TABLE_REQUIRED_FIELDS,
    BETA_CHI_ROBUSTNESS_BETA_PROFILES,
    BETA_CHI_ROBUSTNESS_CHI_PROFILES,
    TDCSIM_CBO_TABLES,
    TdcsimCboContractError,
    _denominator_map_from_cbo_gdp_anchor,
    assemble_cbo_fiscal_year_numerator,
    attach_frozen_denominators,
    load_tdcsim_cbo_run,
    tdcsim_cbo_canonical_entry_decision_rows,
    tdcsim_cbo_canonical_entry_decision_rows_from_directory,
    tdcsim_cbo_core_scenario_interpretation_rows,
    tdcsim_cbo_curve_denominator_empirical_status_rows,
    tdcsim_cbo_curve_denominator_input_rows,
    tdcsim_cbo_curve_sensitive_denominator_assumption_bound_rows,
    tdcsim_cbo_empirical_scenario_interpretation_rows,
    tdcsim_cbo_empirical_term_premium_comparison_rows,
    tdcsim_cbo_fiscal_year_ratio_input_rows,
    tdcsim_cbo_fiscal_year_ratio_input_rows_from_directory,
    tdcsim_cbo_matched_period_response_rows,
    tdcsim_cbo_matched_response_coefficient_rows,
    tdcsim_cbo_model_scenario_beta_chi_robustness_rows,
    tdcsim_cbo_model_scenario_beta_chi_sign_stability_rows,
    tdcsim_cbo_model_scenario_interpretation_synthesis_rows,
    tdcsim_cbo_model_scenario_materiality_classification_rows,
    tdcsim_cbo_model_scenario_summary_rows,
    tdcsim_cbo_route_stock_closure_rows,
    tdcsim_cbo_scenario_effect_rows,
    tdcsim_cbo_scenario_lever_diagnostic_rows,
    tdcsim_cbo_settlement_accrual_bridge_rows,
)


def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _scenario_effect_fixture_row(
    *,
    scenario_id: str,
    delta_rw: str,
    delta_support: str,
    delta_tdc_support: str | None = None,
    delta_direct_support: str = "0",
    delta_bank_support: str = "0",
    delta_tdc_fiscal_flow: str = "0",
    delta_principal_to_du: str = "0",
    delta_interest_to_du: str = "0",
    delta_auction_absorption_du: str = "0",
) -> dict[str, str]:
    row = {field: "0" for field in CBO_SCENARIO_EFFECT_FIELDS}
    row.update(
        {
            "tdcsim_cbo_scenario_effect_row_id": (
                f"tdcsim_cbo_scenario_effect::2027::{scenario_id}"
            ),
            "scenario_id": scenario_id,
            "baseline_scenario_id": "cbo_baseline_noop_v1",
            "fiscal_year": "2027",
            "level_ratewall_ratio": str(Decimal("0.2") + Decimal(delta_rw)),
            "delta_ratewall_ratio_vs_baseline": delta_rw,
            "total_current_demand_support_bil": str(
                Decimal("100") + Decimal(delta_support)
            ),
            "delta_total_current_demand_support_bil": delta_support,
            "tdc_current_demand_support_bil": str(
                Decimal("90") + Decimal(delta_tdc_support or delta_support)
            ),
            "delta_tdc_current_demand_support_bil": (
                delta_tdc_support or delta_support
            ),
            "direct_treasury_current_demand_support_bil": "10",
            "delta_direct_treasury_current_demand_support_bil": (
                delta_direct_support
            ),
            "bank_treasury_current_demand_support_bil": "0",
            "delta_bank_treasury_current_demand_support_bil": delta_bank_support,
            "tdc_fiscal_flow_bil": "0",
            "delta_tdc_fiscal_flow_bil": delta_tdc_fiscal_flow,
            "tdc_debt_service_principal_to_du_bil": "0",
            "delta_tdc_debt_service_principal_to_du_bil": delta_principal_to_du,
            "tdc_debt_service_interest_to_du_bil": "0",
            "delta_tdc_debt_service_interest_to_du_bil": delta_interest_to_du,
            "tdc_auction_absorption_du_bil": "0",
            "delta_tdc_auction_absorption_du_bil": delta_auction_absorption_du,
            "frozen_denominator_bil": "1000",
            "denominator_scope": "frozen",
            "allowed_use": "test",
            "blocked_use": "denominator_change",
            "canonical_ratio_entry": "false",
        }
    )
    return row


def _robustness_effect_row(
    *,
    scenario_id: str,
    tdc_change: str,
    direct: str,
    bank: str,
    baseline_tdc_change: str = "100",
    baseline_direct: str = "10",
    baseline_bank: str = "1",
) -> dict[str, str]:
    beta_chi = Decimal("0.34201759129420367") * Decimal("0.07")
    denominator = Decimal("1000")
    total = (
        Decimal(tdc_change) * beta_chi
        + Decimal(direct)
        + Decimal(bank)
    )
    baseline_total = (
        Decimal(baseline_tdc_change) * beta_chi
        + Decimal(baseline_direct)
        + Decimal(baseline_bank)
    )
    row = {field: "0" for field in CBO_SCENARIO_EFFECT_FIELDS}
    row.update(
        {
            "tdcsim_cbo_scenario_effect_row_id": (
                f"tdcsim_cbo_scenario_effect::2027::{scenario_id}"
            ),
            "scenario_id": scenario_id,
            "baseline_scenario_id": "cbo_baseline_noop_v1",
            "fiscal_year": "2027",
            "scenario_role": "test",
            "scenario_label": scenario_id,
            "scenario_interpretation_status": "test",
            "core_scenario_entry": "false",
            "level_ratewall_ratio": str(total / denominator),
            "delta_ratewall_ratio_vs_baseline": str(
                (total - baseline_total) / denominator
            ),
            "total_current_demand_support_bil": str(total),
            "delta_total_current_demand_support_bil": str(
                total - baseline_total
            ),
            "tdc_current_demand_support_bil": str(
                Decimal(tdc_change) * beta_chi
            ),
            "delta_tdc_current_demand_support_bil": str(
                (Decimal(tdc_change) - Decimal(baseline_tdc_change)) * beta_chi
            ),
            "direct_treasury_current_demand_support_bil": direct,
            "delta_direct_treasury_current_demand_support_bil": str(
                Decimal(direct) - Decimal(baseline_direct)
            ),
            "bank_treasury_current_demand_support_bil": bank,
            "delta_bank_treasury_current_demand_support_bil": str(
                Decimal(bank) - Decimal(baseline_bank)
            ),
            "tdc_change_ex_overlap_bil": tdc_change,
            "delta_tdc_change_ex_overlap_bil": str(
                Decimal(tdc_change) - Decimal(baseline_tdc_change)
            ),
            "frozen_denominator_bil": str(denominator),
            "denominator_scope": "external_frozen_by_fiscal_year",
            "allowed_use": "test",
            "blocked_use": "denominator_change",
            "canonical_ratio_entry": "false",
        }
    )
    return row


def _beta_chi_effect_rows() -> list[dict[str, str]]:
    return [
        _robustness_effect_row(
            scenario_id="cbo_baseline_noop_v1",
            tdc_change="100",
            direct="10",
            bank="1",
        ),
        _robustness_effect_row(
            scenario_id="tdcsim_issuance_empirical_shorter_uncoupled_v1",
            tdc_change="200",
            direct="8",
            bank="1",
        ),
        _robustness_effect_row(
            scenario_id="tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            tdc_change="200",
            direct="7.5",
            bank="1",
        ),
        _robustness_effect_row(
            scenario_id="tdcsim_issuance_empirical_longer_uncoupled_v1",
            tdc_change="50",
            direct="12",
            bank="1",
        ),
        _robustness_effect_row(
            scenario_id="tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            tdc_change="50",
            direct="12.5",
            bank="1",
        ),
        _robustness_effect_row(
            scenario_id="tdcsim_primary_deficit_down_1pct_v1",
            tdc_change="80",
            direct="10",
            bank="1",
        ),
        _robustness_effect_row(
            scenario_id="tdcsim_primary_deficit_up_1pct_v1",
            tdc_change="120",
            direct="10",
            bank="1",
        ),
        _robustness_effect_row(
            scenario_id="tdcsim_holder_source_reserve_user_absorption_v1",
            tdc_change="1000",
            direct="6",
            bank="1",
        ),
        _robustness_effect_row(
            scenario_id="tdcsim_holder_source_domestic_nonbank_absorption_v1",
            tdc_change="-800",
            direct="14",
            bank="1",
        ),
    ]


def _metadata(scenario_id: str = "cbo_baseline") -> dict[str, str]:
    return {
        "schema_version": "tdcsim_cbo_handoff_1",
        "scenario_id": scenario_id,
        "run_id": f"run_{scenario_id}",
        "package_id": "package_20260625",
        "source_vintage": "cbo_2026_06",
        "actuals_available_as_of": "2026-09-20",
        "scenario_config_sha256": f"sha_{scenario_id}",
        "compiled_inputs_digest": "compiled_digest",
        "mmf_deposit_pass_through": "0.97",
        "mmf_deposit_pass_through_status": "fixed_fraction",
        "fiscal_incidence_policy_id": "default_signed_net_primary_proxy",
        "fiscal_incidence_basis": "signed_net_primary_proxy",
        "fiscal_incidence_du_share": "1",
        "fiscal_incidence_ru_share": "0",
        "fiscal_incidence_foreign_share": "0",
        "fiscal_incidence_other_share": "0",
    }


def _mmf_metadata_override(value: str) -> dict[str, dict[str, str]]:
    return {
        table: {"mmf_deposit_pass_through": value}
        for table in TDCSIM_CBO_TABLES
    }


def _package(
    tmp_path: Path,
    *,
    scenario_id: str = "cbo_baseline",
    incomplete: bool = False,
    tdc_ex_overlap_per_period: str = "90",
    direct_interest_per_period: str = "10",
    bank_interest_per_period: str = "5",
    weighted_original_term_years: str = "2",
    du_absorbed_issuance_proceeds_per_period: str = "0",
    scenario_overrides: Mapping[str, object] | None = None,
    tdc_component_override: Mapping[str, str] | None = None,
    metadata_override: Mapping[str, Mapping[str, str]] | None = None,
) -> Path:
    root = tmp_path / scenario_id
    outputs = root / "outputs"
    outputs.mkdir(parents=True)
    metadata = _metadata(scenario_id)
    (root / "tdcsim_cbo_run_manifest.json").write_text(
        json.dumps({"run_id": metadata["run_id"], "scenario": {"scenario_id": scenario_id}}),
        encoding="utf-8",
    )
    (root / "scenario.json").write_text(
        json.dumps(
            {
                "scenario_id": scenario_id,
                "overrides": scenario_overrides or {},
            }
        ),
        encoding="utf-8",
    )
    periods = [
        ("2026-10-01", "2026-12-31"),
        ("2027-01-01", "2027-03-31"),
        ("2027-04-01", "2027-06-30"),
        ("2027-07-01", "2027-09-30"),
    ]
    if incomplete:
        periods = periods[1:]
    tdc_ex_overlap = Decimal(tdc_ex_overlap_per_period)
    direct_interest = Decimal(direct_interest_per_period)
    bank_interest = Decimal(bank_interest_per_period)
    tdc_change = tdc_ex_overlap + direct_interest
    rows_by_table = {
        "tdcsim_period_issuance_flows": [
            {
                "period_start": start,
                "period_end": end,
                "flow_id": f"iss_{index}",
                "security_id": f"sec_{index}",
                "holder_sector": "Private",
                "holder_subsector": "domestic_nonbank_deposit_funded",
                "instrument_type": "Fixed",
                "maturity_bucket": "2y",
                "weighted_original_term_years": weighted_original_term_years,
                "face_issued_bil": "120",
                "cash_proceeds_bil": "118",
            }
            for index, (start, end) in enumerate(periods, start=1)
        ],
        "tdcsim_period_principal_flows": [
            {
                "period_start": start,
                "period_end": end,
                "flow_id": f"red_{index}",
                "security_id": f"sec_{index}",
                "holder_sector": "Private",
                "holder_subsector": "domestic_nonbank_deposit_funded",
                "instrument_type": "Fixed",
                "maturity_bucket": "2y",
                "face_redeemed_bil": "20",
                "principal_redeemed_bil": "20",
                "cash_paid_bil": "20",
            }
            for index, (start, end) in enumerate(periods, start=1)
        ],
        "tdcsim_period_payment_flows": [
            {
                "period_start": start,
                "period_end": end,
                "flow_id": f"pay_private_{index}",
                "security_id": f"sec_{index}",
                "holder_sector": "Private",
                "holder_subsector": "domestic_nonbank_deposit_funded",
                "instrument_type": "Fixed",
                "maturity_bucket": "2y",
                "payment_type": "fixed_coupon",
                "accounting_basis": "cash",
                "amount_bil": str(direct_interest),
                "is_additive_to_cash_total": "true",
            }
            for index, (start, end) in enumerate(periods, start=1)
        ]
        + [
            {
                "period_start": start,
                "period_end": end,
                "flow_id": f"pay_bank_{index}",
                "security_id": f"sec_bank_{index}",
                "holder_sector": "Banks",
                "holder_subsector": "bank_treasury_book",
                "instrument_type": "Fixed",
                "maturity_bucket": "2y",
                "payment_type": "fixed_coupon",
                "accounting_basis": "cash",
                "amount_bil": str(bank_interest),
                "is_additive_to_cash_total": "true",
            }
            for index, (start, end) in enumerate(periods, start=1)
        ],
        "tdcsim_holder_stocks": [
            {
                "date": end,
                "holder_sector": "Private",
                "holder_subsector": "domestic_nonbank_deposit_funded",
                "instrument_type": "Fixed",
                "maturity_bucket": "2y",
                "debt_held_bil": "1000",
                "valuation_basis": "face",
                "debt_scope": "controlled_public_marketable",
            }
            for _, end in periods
        ],
        "tdcsim_tdc_principal_route_stocks": [
            {
                "date": end,
                "route_holder_sector": "Private",
                "route_holder_subsector": "domestic_nonbank_deposit_funded",
                "instrument_type": "Fixed",
                "maturity_bucket": "2y",
                "route_debt_held_bil": str(1000 + 100 * index),
                "valuation_basis": "face",
                "debt_scope": "controlled_public_marketable",
                "route_stock_basis": "tdc_principal_settlement_route",
            }
            for index, (_, end) in enumerate(periods)
        ],
        "tdcsim_tdc_principal_route_stock_closure": [
            {
                "period_start": start,
                "period_end": end,
                "route_holder_sector": "Private",
                "route_holder_subsector": "domestic_nonbank_deposit_funded",
                "instrument_type": "Fixed",
                "maturity_bucket": "2y",
                "debt_scope": "controlled_public_marketable",
                "opening_route_stock_bil": str(900 + 100 * index),
                "route_face_issued_bil": "120",
                "route_face_redeemed_bil": "20",
                "route_stock_residual_or_indexation_bil": "0",
                "closing_route_stock_bil": str(1000 + 100 * index),
                "closure_identity_error_bil": "0",
                "route_stock_basis": "tdc_principal_settlement_route",
                "residual_basis": "fixture_no_residual",
            }
            for index, (start, end) in enumerate(periods)
        ],
        "tdcsim_debt_target_bridge": [
            {
                "date": end,
                "cbo_public_debt_target_bil": "31000",
                "controlled_public_marketable_target_bil": "30000",
                "controlled_debt_pre_issuance_bil": "29900",
                "face_issued_bil": "120",
                "face_retired_bil": "20",
                "controlled_debt_post_issuance_bil": "30000",
                "target_error_bil": "0",
                "funding_mode": "cbo_debt_stock_control",
            }
            for _, end in periods
        ],
        "tdcsim_scenario_metrics": [
            {
                "date": end,
                "new_issuance_wam_years": "6",
                "outstanding_controlled_wam_years": "5.5",
                "new_issuance_bill_share": "0.20",
                "outstanding_controlled_bill_share": "0.18",
                "new_issuance_short_maturity_share": "0.40",
                "outstanding_controlled_short_maturity_share": "0.37",
            }
            for _, end in periods
        ],
        "tdcsim_period_tdc_summary": [
            {
                "period_start": start,
                "period_end": end,
                "tdc_change_bil": str(tdc_change),
                "tdc_fiscal_flow_bil": str(tdc_ex_overlap),
                "tdc_debt_service_bil": str(direct_interest),
                "tdc_debt_service_principal_to_du_bil": "30",
                "tdc_debt_service_interest_to_du_bil": str(direct_interest),
                "gross_principal_cash_paid_to_du_bil": "33",
                "principal_redeemed_to_du_domestic_nonbank_bil": "30",
                "principal_redeemed_to_du_mmf_bil": "0",
                "gross_principal_cash_paid_to_du_domestic_nonbank_bil": "33",
                "gross_principal_cash_paid_to_du_mmf_bil": "0",
                "gross_principal_cash_paid_to_du_mmf_plumbing_bil": "0",
                "tdc_auction_absorption_du_bil": "0",
                "tdc_secondary_trades_bil": "0",
                "tdc_other_bil": "0",
                "overlap_cashflow_bil": str(direct_interest),
                "tdc_change_ex_overlap_bil": str(tdc_ex_overlap),
                "component_sum_bil": str(tdc_change),
                "component_sum_error_bil": "0",
                "gross_issuance_cash_proceeds_bil": "118",
                "gross_issuance_proceeds_absorbed_by_du_bil": (
                    du_absorbed_issuance_proceeds_per_period
                ),
                "net_du_principal_issuance_cashflow_bil": "33",
                "tdc_amount_basis": EXPECTED_TDC_AMOUNT_BASIS,
                "holder_allocation_scope": "fixture",
                "overlap_policy": EXPECTED_TDC_OVERLAP_POLICY,
            }
            for start, end in periods
        ],
        "tdcsim_period_tdc_components": [
            component
            for index, (start, end) in enumerate(periods, start=1)
            for component in (
                {
                    "period_start": start,
                    "period_end": end,
                    "component_id": f"tdc_{index}",
                    "component_key": "fiscal_flow",
                    "component_family": "fiscal",
                    "holder_sector": "Private",
                    "holder_subsector": "domestic_ultimate_net_primary_proxy",
                    "instrument_type": "",
                    "payment_type": "primary_deficit_or_surplus",
                    "accounting_basis": "signed_net_primary_proxy",
                    "amount_bil": str(tdc_ex_overlap),
                    "is_additive_to_tdc_change": "true",
                    "enters_direct_interest_support": "false",
                    "enters_tdc_deposit_support_default": "true",
                    "tdc_amount_basis": EXPECTED_TDC_AMOUNT_BASIS,
                    "overlap_policy": EXPECTED_TDC_OVERLAP_POLICY,
                },
                {
                    "period_start": start,
                    "period_end": end,
                    "component_id": f"direct_{index}",
                    "component_key": "fixed_coupon_interest_to_du_domestic_nonbank",
                    "component_family": "debt_service_interest",
                    "holder_sector": "Private",
                    "holder_subsector": "domestic_nonbank_deposit_funded",
                    "instrument_type": "Fixed",
                    "payment_type": "fixed_coupon",
                    "accounting_basis": "cash",
                    "amount_bil": str(direct_interest),
                    "is_additive_to_tdc_change": "true",
                    "enters_direct_interest_support": "true",
                    "enters_tdc_deposit_support_default": "false",
                    "tdc_amount_basis": EXPECTED_TDC_AMOUNT_BASIS,
                    "overlap_policy": EXPECTED_TDC_OVERLAP_POLICY,
                },
                {
                    "period_start": start,
                    "period_end": end,
                    "component_id": f"tips_{index}",
                    "component_key": "tips_indexation",
                    "component_family": "tips_indexation",
                    "holder_sector": "Private",
                    "holder_subsector": "domestic_nonbank_deposit_funded",
                    "instrument_type": "TIPS",
                    "payment_type": "tips_indexation",
                    "accounting_basis": "face_stock",
                    "amount_bil": "3",
                    "is_additive_to_tdc_change": "false",
                    "enters_direct_interest_support": "false",
                    "enters_tdc_deposit_support_default": "false",
                    "tdc_amount_basis": EXPECTED_TDC_AMOUNT_BASIS,
                    "overlap_policy": EXPECTED_TDC_OVERLAP_POLICY,
                },
            )
        ],
    }
    if tdc_component_override:
        rows_by_table["tdcsim_period_tdc_components"][1].update(tdc_component_override)
    for table in TDCSIM_CBO_TABLES:
        rows = []
        for row in rows_by_table[table]:
            row_metadata = dict(metadata)
            row_metadata.update((metadata_override or {}).get(table, {}))
            rows.append({**row_metadata, **row})
        fieldnames = sorted(COMMON_METADATA_FIELDS | TABLE_REQUIRED_FIELDS[table] | set(rows[0]))
        _write_csv(outputs / f"{table}.csv", fieldnames, rows)
    return root


def test_loads_cbo_package_and_assembles_fy2027_numerator(tmp_path: Path) -> None:
    package = _package(tmp_path)

    run = load_tdcsim_cbo_run(package, expected_mmf_deposit_pass_through=Decimal("0.97"))
    row = assemble_cbo_fiscal_year_numerator(run, 2027)

    assert row.scenario_id == "cbo_baseline"
    assert row.period_count == 4
    assert row.tdc_change_ex_overlap_bil == Decimal("360")
    assert row.direct_treasury_interest_basis_bil == Decimal("40")
    assert row.bank_treasury_interest_basis_bil == Decimal("20")
    assert row.tdc_current_demand_support_bil == Decimal("8.6188433006139324840")
    assert row.direct_treasury_current_demand_support_bil == Decimal("4.00")
    assert row.bank_treasury_current_demand_support_bil == Decimal("0.20")
    assert row.total_current_demand_support_bil == Decimal("12.8188433006139324840")


def test_missing_tdc_component_table_fails_closed(tmp_path: Path) -> None:
    package = _package(tmp_path)
    (package / "outputs" / "tdcsim_period_tdc_components.csv").unlink()

    with pytest.raises(TdcsimCboContractError, match="missing required.*components"):
        load_tdcsim_cbo_run(package)


def test_mismatched_metadata_fails_closed(tmp_path: Path) -> None:
    package = _package(
        tmp_path,
        metadata_override={
            "tdcsim_scenario_metrics": {"scenario_id": "different_scenario"},
        },
    )

    with pytest.raises(TdcsimCboContractError, match="metadata differs"):
        load_tdcsim_cbo_run(package)


def test_direct_interest_component_cannot_also_enter_tdc_default(
    tmp_path: Path,
) -> None:
    package = _package(
        tmp_path,
        tdc_component_override={"enters_tdc_deposit_support_default": "true"},
    )

    with pytest.raises(TdcsimCboContractError, match="cannot enter direct support"):
        load_tdcsim_cbo_run(package)


def test_incomplete_fiscal_year_is_rejected(tmp_path: Path) -> None:
    package = _package(tmp_path, incomplete=True)
    run = load_tdcsim_cbo_run(package)

    with pytest.raises(TdcsimCboContractError, match="coverage is incomplete"):
        assemble_cbo_fiscal_year_numerator(run, 2027)


def test_denominator_attachment_is_frozen_by_fiscal_year(tmp_path: Path) -> None:
    baseline = load_tdcsim_cbo_run(_package(tmp_path, scenario_id="baseline"))
    longer = load_tdcsim_cbo_run(_package(tmp_path, scenario_id="longer_issuance"))
    numerators = (
        assemble_cbo_fiscal_year_numerator(baseline, 2027),
        assemble_cbo_fiscal_year_numerator(longer, 2027),
    )

    rows = attach_frozen_denominators(numerators, {2027: Decimal("1000")})

    assert {row.frozen_denominator for row in rows} == {Decimal("1000")}
    assert {row.denominator_scope for row in rows} == {"external_frozen_by_fiscal_year"}
    assert rows[0].ratio == rows[1].ratio


def test_denominator_attachment_accepts_explicit_bridge_scope(tmp_path: Path) -> None:
    baseline = load_tdcsim_cbo_run(_package(tmp_path, scenario_id="baseline"))
    numerator = assemble_cbo_fiscal_year_numerator(baseline, 2027)

    rows = attach_frozen_denominators(
        [numerator],
        {2027: Decimal("1000")},
        denominator_scope=TDCSIM_CBO_CBO_GDP_SCALED_DENOMINATOR_SCOPE,
    )

    assert rows[0].denominator_scope == TDCSIM_CBO_CBO_GDP_SCALED_DENOMINATOR_SCOPE


def test_cbo_gdp_denominator_bridge_preserves_anchor_and_scales_later_years() -> None:
    rows = _denominator_map_from_cbo_gdp_anchor(
        {2027: Decimal("126.1995153634877105572719155")},
        {
            2027: Decimal("33315.187"),
            2028: Decimal("34665.785"),
            2029: Decimal("36010.049"),
        },
        fiscal_years=[2027, 2028, 2029],
    )

    share = Decimal("126.1995153634877105572719155") / Decimal("33315.187")
    assert rows[2027] == Decimal("126.1995153634877105572719155")
    assert rows[2028] == Decimal("34665.785") * share
    assert rows[2029] == Decimal("36010.049") * share


def test_cbo_gdp_denominator_bridge_rejects_missing_anchor_gdp() -> None:
    with pytest.raises(TdcsimCboContractError, match="missing anchor GDP"):
        _denominator_map_from_cbo_gdp_anchor(
            {2027: Decimal("126.1995153634877105572719155")},
            {2028: Decimal("34665.785")},
            fiscal_years=[2027, 2028],
        )


def test_cbo_ratio_input_rows_move_numerator_not_denominator(tmp_path: Path) -> None:
    baseline = _package(
        tmp_path,
        scenario_id="baseline",
        tdc_ex_overlap_per_period="90",
        direct_interest_per_period="10",
        bank_interest_per_period="5",
    )
    longer = _package(
        tmp_path,
        scenario_id="longer_issuance",
        tdc_ex_overlap_per_period="140",
        direct_interest_per_period="16",
        bank_interest_per_period="8",
    )

    rows = tdcsim_cbo_fiscal_year_ratio_input_rows(
        [baseline, longer],
        fiscal_years=[2027],
        denominator_by_fiscal_year={2027: Decimal("1000")},
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    assert {field for row in rows for field in row} == set(
        CBO_FISCAL_YEAR_RATIO_INPUT_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    assert by_scenario["baseline"]["frozen_denominator_bil"] == "1000"
    assert by_scenario["longer_issuance"]["frozen_denominator_bil"] == "1000"
    assert Decimal(
        by_scenario["longer_issuance"]["total_current_demand_support_bil"]
    ) > Decimal(by_scenario["baseline"]["total_current_demand_support_bil"])
    assert Decimal(by_scenario["longer_issuance"]["ratewall_ratio"]) > Decimal(
        by_scenario["baseline"]["ratewall_ratio"]
    )
    assert {
        row["denominator_invariance_status"] for row in rows
    } == {"pass_external_fiscal_year_denominator_reused_across_scenarios"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert all("maturity_curve_holder_specific_D" in row["blocked_use"] for row in rows)


def test_cbo_ratio_input_rows_load_from_suite_directory(tmp_path: Path) -> None:
    suite = tmp_path / "suite"
    runs = suite / "runs"
    runs.mkdir(parents=True)
    _write_csv(
        suite / "frozen_denominator_by_fiscal_year.csv",
        ["fiscal_year", "frozen_denominator_bil"],
        [{"fiscal_year": "2027", "frozen_denominator_bil": "1000"}],
    )
    _package(runs, scenario_id="baseline")
    _package(
        runs,
        scenario_id="holder_shift",
        tdc_ex_overlap_per_period="120",
        direct_interest_per_period="14",
        bank_interest_per_period="7",
    )

    rows = tdcsim_cbo_fiscal_year_ratio_input_rows_from_directory(
        suite,
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    assert [row["scenario_id"] for row in rows] == ["baseline", "holder_shift"]
    assert {row["frozen_denominator_bil"] for row in rows} == {"1000"}
    assert Decimal(rows[1]["ratewall_ratio"]) > Decimal(rows[0]["ratewall_ratio"])


def test_tdcsim_cbo_canonical_entry_decision_admits_only_forward_baseline(
    tmp_path: Path,
) -> None:
    baseline = _package(
        tmp_path,
        scenario_id="cbo_baseline_noop_v1",
        tdc_ex_overlap_per_period="90",
    )
    shorter = _package(
        tmp_path,
        scenario_id="tdcsim_issuance_empirical_shorter_uncoupled_v1",
        tdc_ex_overlap_per_period="120",
    )

    ratio_rows = tdcsim_cbo_fiscal_year_ratio_input_rows(
        [baseline, shorter],
        fiscal_years=[2027],
        denominator_by_fiscal_year={2027: Decimal("1000")},
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )
    rows = tdcsim_cbo_canonical_entry_decision_rows(ratio_rows)

    assert len(rows) == 1
    row = rows[0]
    assert list(row) == CBO_CANONICAL_ENTRY_DECISION_FIELDS
    assert row["fiscal_year"] == "2027"
    assert row["canonical_entry_scope"] == "current_forward_model_baseline_case"
    assert row["baseline_scenario_id"] == "cbo_baseline_noop_v1"
    assert row["baseline_ratewall_ratio"] == "0.012818843300613932484"
    assert row["canonical_forward_baseline_entry"] == "true"
    assert row["runtime_canonical_ratio_object_id"] == "rw_runtime_support_offset_af_fixed"
    assert row["runtime_canonical_replacement_allowed"] == "false"
    assert row["scenario_rows_reviewed_count"] == "1"
    assert row["nonbaseline_rows_entering_forward_baseline_count"] == "0"
    assert row["denominator_scope"] == "external_frozen_by_fiscal_year"
    assert row["denominator_decision"] == (
        "use_existing_frozen_fy_denominator_no_curve_sensitive_D"
    )
    assert row["canonical_ratio_entry"] == "false"
    assert row["enters_main_ratio"] == "false"
    assert "nonbaseline_scenario_canonical_entry" in row["blocked_use"]


def test_tdcsim_cbo_canonical_entry_decision_reads_manifest_backed_default_suite() -> None:
    rows = tdcsim_cbo_canonical_entry_decision_rows_from_directory()

    assert len(rows) == 1
    row = rows[0]
    assert list(row) == CBO_CANONICAL_ENTRY_DECISION_FIELDS
    assert row["fiscal_year"] == "2027"
    assert row["baseline_scenario_id"] == "cbo_baseline_noop_v1"
    assert row["baseline_ratewall_ratio"] == "0.2278047971763015348134717145"
    assert row["canonical_forward_baseline_entry"] == "true"
    assert row["scenario_rows_reviewed_count"] == "22"
    assert row["runtime_canonical_replacement_allowed"] == "false"
    assert row["denominator_prior_update_allowed"] == "false"


def test_tdcsim_cbo_canonical_entry_decision_rejects_nonbaseline_entry(
    tmp_path: Path,
) -> None:
    baseline = _package(tmp_path, scenario_id="cbo_baseline_noop_v1")
    stress = _package(tmp_path, scenario_id="tdcsim_primary_deficit_up_1pct_v1")
    ratio_rows = tdcsim_cbo_fiscal_year_ratio_input_rows(
        [baseline, stress],
        fiscal_years=[2027],
        denominator_by_fiscal_year={2027: Decimal("1000")},
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )
    ratio_rows[1]["canonical_ratio_entry"] = "true"

    with pytest.raises(TdcsimCboContractError, match="nonbaseline"):
        tdcsim_cbo_canonical_entry_decision_rows(ratio_rows)


def test_cbo_scenario_effect_rows_separate_level_and_delta(
    tmp_path: Path,
) -> None:
    baseline = _package(
        tmp_path,
        scenario_id="cbo_baseline_noop_v1",
        tdc_ex_overlap_per_period="90",
        direct_interest_per_period="10",
        bank_interest_per_period="5",
    )
    shorter = _package(
        tmp_path,
        scenario_id="ratewall_shorter_issuance_v1",
        tdc_ex_overlap_per_period="120",
        direct_interest_per_period="12",
        bank_interest_per_period="6",
    )

    rows = tdcsim_cbo_scenario_effect_rows(
        [baseline, shorter],
        fiscal_years=[2027],
        denominator_by_fiscal_year={2027: Decimal("1000")},
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    assert {field for row in rows for field in row} == set(CBO_SCENARIO_EFFECT_FIELDS)
    by_scenario = {row["scenario_id"]: row for row in rows}
    assert by_scenario["cbo_baseline_noop_v1"]["scenario_role"] == "baseline"
    assert by_scenario["cbo_baseline_noop_v1"]["delta_ratewall_ratio_vs_baseline"] == "0"
    assert by_scenario["ratewall_shorter_issuance_v1"]["core_scenario_entry"] == "true"
    assert by_scenario["ratewall_shorter_issuance_v1"]["frozen_denominator_bil"] == "1000"
    assert Decimal(
        by_scenario["ratewall_shorter_issuance_v1"][
            "delta_total_current_demand_support_bil"
        ]
    ) > Decimal("0")
    assert by_scenario["ratewall_shorter_issuance_v1"][
        "delta_gross_principal_cash_paid_to_du_bil"
    ] == "0"
    assert by_scenario["ratewall_shorter_issuance_v1"]["canonical_ratio_entry"] == "false"


def test_cbo_scenario_effect_rows_label_empirical_term_premium_scenarios(
    tmp_path: Path,
) -> None:
    baseline = _package(
        tmp_path,
        scenario_id="cbo_baseline_noop_v1",
        tdc_ex_overlap_per_period="90",
    )
    coupled = _package(
        tmp_path,
        scenario_id="tdcsim_issuance_empirical_longer_termprem_up_central_v1",
        tdc_ex_overlap_per_period="95",
    )

    rows = tdcsim_cbo_scenario_effect_rows(
        [baseline, coupled],
        fiscal_years=[2027],
        denominator_by_fiscal_year={2027: Decimal("1000")},
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    by_scenario = {row["scenario_id"]: row for row in rows}
    row = by_scenario["tdcsim_issuance_empirical_longer_termprem_up_central_v1"]
    assert row["scenario_role"] == "empirical_longer_issuance_term_premium_central"
    assert row["scenario_interpretation_status"] == "core_empirical_coupled_scenario"
    assert row["core_scenario_entry"] == "true"
    assert row["canonical_ratio_entry"] == "false"
    assert "denominator_change" in row["blocked_use"]


def test_empirical_term_premium_comparison_rows_measure_overlay_offset() -> None:
    effect_rows = [
        _scenario_effect_fixture_row(
            scenario_id="cbo_baseline_noop_v1",
            delta_rw="0",
            delta_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_shorter_uncoupled_v1",
            delta_rw="0.0016",
            delta_support="0.20",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            delta_rw="0.0004",
            delta_support="0.05",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_longer_uncoupled_v1",
            delta_rw="-0.0030",
            delta_support="-0.39",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            delta_rw="-0.0015",
            delta_support="-0.18",
        ),
    ]

    rows = tdcsim_cbo_empirical_term_premium_comparison_rows(effect_rows)

    assert {field for row in rows for field in row} == set(
        CBO_EMPIRICAL_TERM_PREMIUM_COMPARISON_FIELDS
    )
    by_key = {
        (row["issuance_direction"], row["term_premium_tier"]): row
        for row in rows
    }
    shorter = by_key[("shorter", "central")]
    assert shorter["ten_year_nominal_rate_shock_bp"] == "-8"
    assert shorter["rate_overlay_delta_ratewall_ratio"] == "-0.0012"
    assert shorter["offset_fraction_of_abs_issuance_effect"] == "0.75"
    assert shorter["net_effect_fraction_remaining"] == "0.25"

    longer = by_key[("longer", "central")]
    assert longer["ten_year_nominal_rate_shock_bp"] == "8"
    assert longer["rate_overlay_delta_ratewall_ratio"] == "0.0015"
    assert longer["offset_fraction_of_abs_issuance_effect"] == "0.5"
    assert longer["net_effect_fraction_remaining"] == "0.5"
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert all("denominator_change" in row["blocked_use"] for row in rows)


def test_empirical_scenario_interpretation_rows_select_and_decompose() -> None:
    effect_rows = [
        _scenario_effect_fixture_row(
            scenario_id="cbo_baseline_noop_v1",
            delta_rw="0",
            delta_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_shorter_uncoupled_v1",
            delta_rw="0.0016",
            delta_support="0.20",
            delta_tdc_support="0.19",
            delta_direct_support="0.01",
            delta_tdc_fiscal_flow="2",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            delta_rw="0.0004",
            delta_support="0.05",
            delta_tdc_support="0.04",
            delta_direct_support="0.01",
            delta_tdc_fiscal_flow="1",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_longer_uncoupled_v1",
            delta_rw="-0.0030",
            delta_support="-0.39",
            delta_tdc_support="-0.38",
            delta_direct_support="-0.01",
            delta_auction_absorption_du="-3",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            delta_rw="-0.0015",
            delta_support="-0.18",
            delta_tdc_support="-0.17",
            delta_direct_support="-0.01",
            delta_auction_absorption_du="-2",
        ),
    ]

    rows = tdcsim_cbo_empirical_scenario_interpretation_rows(effect_rows)

    assert {field for row in rows for field in row} == set(
        CBO_EMPIRICAL_SCENARIO_INTERPRETATION_FIELDS
    )
    assert [row["scenario_set_role"] for row in rows] == [
        "baseline_anchor",
        "issuance_only_control",
        "coupled_central_empirical_scenario",
        "issuance_only_control",
        "coupled_central_empirical_scenario",
    ]
    by_scenario = {row["scenario_id"]: row for row in rows}
    shorter = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]
    assert shorter["paired_issuance_only_scenario_id"] == (
        "tdcsim_issuance_empirical_shorter_uncoupled_v1"
    )
    assert shorter["rate_overlay_delta_ratewall_ratio"] == "-0.0012"
    assert shorter["offset_fraction_of_abs_issuance_effect"] == "0.75"
    assert shorter["delta_tdc_fiscal_flow_bil"] == "1"
    assert shorter["dominant_delta_support_component"] == (
        "tdc_current_demand_support"
    )

    longer = by_scenario[
        "tdcsim_issuance_empirical_longer_termprem_up_central_v1"
    ]
    assert longer["rate_overlay_delta_ratewall_ratio"] == "0.0015"
    assert longer["net_effect_fraction_remaining"] == "0.5"
    assert longer["delta_tdc_auction_absorption_du_bil"] == "-2"
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}


def test_model_scenario_summary_rows_add_primary_deficit_comparator() -> None:
    effect_rows = [
        _scenario_effect_fixture_row(
            scenario_id="cbo_baseline_noop_v1",
            delta_rw="0",
            delta_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_shorter_uncoupled_v1",
            delta_rw="0.0016",
            delta_support="0.20",
            delta_tdc_support="0.19",
            delta_direct_support="0.01",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            delta_rw="0.0004",
            delta_support="0.05",
            delta_tdc_support="0.04",
            delta_direct_support="0.01",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_longer_uncoupled_v1",
            delta_rw="-0.0030",
            delta_support="-0.39",
            delta_tdc_support="-0.38",
            delta_direct_support="-0.01",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            delta_rw="-0.0015",
            delta_support="-0.18",
            delta_tdc_support="-0.17",
            delta_direct_support="-0.01",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_primary_deficit_down_1pct_v1",
            delta_rw="-0.0015",
            delta_support="-0.19",
            delta_tdc_support="-0.19",
            delta_tdc_fiscal_flow="-10",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_primary_deficit_up_1pct_v1",
            delta_rw="0.0015",
            delta_support="0.19",
            delta_tdc_support="0.19",
            delta_tdc_fiscal_flow="10",
        ),
    ]

    rows = tdcsim_cbo_model_scenario_summary_rows(effect_rows)

    assert {field for row in rows for field in row} == set(
        CBO_MODEL_SCENARIO_SUMMARY_FIELDS
    )
    assert [row["comparison_group"] for row in rows] == [
        "baseline",
        "shorter_issuance",
        "shorter_issuance",
        "longer_issuance",
        "longer_issuance",
        "primary_deficit",
        "primary_deficit",
    ]
    by_scenario = {row["scenario_id"]: row for row in rows}
    shorter = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]
    assert shorter["primary_deficit_up_1pct_delta_ratewall_ratio"] == "0.0015"
    assert shorter["abs_delta_vs_primary_deficit_up_1pct"] == (
        "0.2666666666666666666666666667"
    )
    assert shorter["rate_overlay_delta_ratewall_ratio"] == "-0.0012"
    assert shorter["allowed_use"] == "assumption_mode_model_scenario_summary"
    assert shorter["component_delta_sum_check_bil"] == "0"
    assert shorter["component_delta_sum_status"] == (
        "pass_components_sum_to_total_support_delta"
    )
    assert shorter["tdc_delta_abs_contribution_share"] == "0.8"
    assert shorter["direct_treasury_delta_abs_contribution_share"] == "0.2"
    assert shorter["bank_treasury_delta_abs_contribution_share"] == "0"
    assert shorter["support_mechanism_profile"] == "tdc_support_dominant"

    primary = by_scenario["tdcsim_primary_deficit_up_1pct_v1"]
    assert primary["summary_role"] == "fiscal_scale_comparator"
    assert primary["abs_delta_vs_primary_deficit_up_1pct"] == "1"
    assert primary["tdc_delta_abs_contribution_share"] == "1"
    assert primary["support_mechanism_profile"] == "tdc_support_dominant"
    assert primary["model_interpretation"] == (
        "primary_deficit_up_1pct_scale_comparator"
    )
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert all("denominator_change" in row["blocked_use"] for row in rows)


def test_model_scenario_summary_rows_add_holder_preference_comparators() -> None:
    effect_rows = [
        _scenario_effect_fixture_row(
            scenario_id="cbo_baseline_noop_v1",
            delta_rw="0",
            delta_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_primary_deficit_up_1pct_v1",
            delta_rw="0.0015",
            delta_support="0.19",
            delta_tdc_support="0.19",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_holder_source_reserve_user_absorption_v1",
            delta_rw="0.20",
            delta_support="20",
            delta_tdc_support="25",
            delta_direct_support="-5",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_holder_source_current_mix_v1",
            delta_rw="0.02",
            delta_support="2",
            delta_tdc_support="2",
            delta_direct_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_holder_source_domestic_nonbank_absorption_v1",
            delta_rw="-0.16",
            delta_support="-16",
            delta_tdc_support="-20",
            delta_direct_support="4",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_private_holder_high_v1",
            delta_rw="0.04",
            delta_support="4",
            delta_tdc_support="5",
            delta_direct_support="-1",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_private_holder_low_v1",
            delta_rw="-0.06",
            delta_support="-6",
            delta_tdc_support="-7",
            delta_direct_support="1",
        ),
    ]

    rows = tdcsim_cbo_model_scenario_summary_rows(effect_rows)

    by_scenario = {row["scenario_id"]: row for row in rows}
    low = by_scenario["tdcsim_holder_source_reserve_user_absorption_v1"]
    central = by_scenario["tdcsim_holder_source_current_mix_v1"]
    high = by_scenario["tdcsim_holder_source_domestic_nonbank_absorption_v1"]
    old_high = by_scenario["tdcsim_private_holder_high_v1"]
    old_low = by_scenario["tdcsim_private_holder_low_v1"]
    assert low["summary_role"] == "holder_preference_comparator"
    assert central["summary_role"] == "holder_preference_comparator"
    assert high["summary_role"] == "holder_preference_comparator"
    assert old_high["summary_role"] == "holder_preference_comparator"
    assert old_low["summary_role"] == "holder_preference_comparator"
    assert low["comparison_group"] == "holder_preference"
    assert central["comparison_group"] == "holder_preference"
    assert high["comparison_group"] == "holder_preference"
    assert low["model_interpretation"] == (
        "holder_source_reserve_user_absorption_low_private_comparator"
    )
    assert central["model_interpretation"] == (
        "holder_source_current_mix_central_comparator"
    )
    assert high["model_interpretation"] == (
        "holder_source_domestic_nonbank_absorption_high_private_comparator"
    )
    assert old_high["model_interpretation"] == (
        "private_holder_high_reserve_user_private_route_comparator"
    )
    assert old_low["model_interpretation"] == (
        "private_holder_low_reserve_user_private_route_comparator"
    )
    assert low["support_mechanism_profile"] == "offsetting_mixed_support"
    assert high["support_mechanism_profile"] == "offsetting_mixed_support"
    assert Decimal(low["abs_delta_vs_primary_deficit_up_1pct"]) > Decimal("100")
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}


def test_model_scenario_summary_rows_add_rate_curve_comparators() -> None:
    effect_rows = [
        _scenario_effect_fixture_row(
            scenario_id="cbo_baseline_noop_v1",
            delta_rw="0",
            delta_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_rate_down_25bp_v1",
            delta_rw="0.04",
            delta_support="4",
            delta_tdc_support="0",
            delta_direct_support="4",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_rate_up_25bp_v1",
            delta_rw="-0.03",
            delta_support="-3",
            delta_tdc_support="0",
            delta_direct_support="-3",
        ),
    ]

    rows = tdcsim_cbo_model_scenario_summary_rows(effect_rows)

    by_scenario = {row["scenario_id"]: row for row in rows}
    down = by_scenario["tdcsim_rate_down_25bp_v1"]
    up = by_scenario["tdcsim_rate_up_25bp_v1"]
    assert down["summary_role"] == "rate_curve_comparator"
    assert up["summary_role"] == "rate_curve_comparator"
    assert down["comparison_group"] == "rate_curve"
    assert up["comparison_group"] == "rate_curve"
    assert down["model_interpretation"] == (
        "parallel_nominal_rate_down_25bp_comparator"
    )
    assert up["model_interpretation"] == "parallel_nominal_rate_up_25bp_comparator"
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}


def test_model_scenario_summary_rows_add_mmf_pass_through_comparators() -> None:
    effect_rows = [
        _scenario_effect_fixture_row(
            scenario_id="cbo_baseline_noop_v1",
            delta_rw="0",
            delta_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_primary_deficit_up_1pct_v1",
            delta_rw="0.0015",
            delta_support="0.19",
            delta_tdc_support="0.19",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_mmf_pass_through_90_v1",
            delta_rw="-0.00045",
            delta_support="-0.045",
            delta_tdc_support="-0.045",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_mmf_pass_through_99_v1",
            delta_rw="0.00012",
            delta_support="0.012",
            delta_tdc_support="0.012",
        ),
    ]

    rows = tdcsim_cbo_model_scenario_summary_rows(effect_rows)

    by_scenario = {row["scenario_id"]: row for row in rows}
    low = by_scenario["tdcsim_mmf_pass_through_90_v1"]
    high = by_scenario["tdcsim_mmf_pass_through_99_v1"]
    assert low["summary_role"] == "mmf_pass_through_comparator"
    assert high["summary_role"] == "mmf_pass_through_comparator"
    assert low["comparison_group"] == "mmf_pass_through"
    assert high["comparison_group"] == "mmf_pass_through"
    assert low["model_interpretation"] == "mmf_pass_through_low_90_comparator"
    assert high["model_interpretation"] == "mmf_pass_through_high_99_comparator"
    assert all(row["canonical_ratio_entry"] == "false" for row in rows)
    assert all("denominator_change" in row["blocked_use"] for row in rows)


def test_model_scenario_summary_rows_add_combined_narrative_scenarios() -> None:
    effect_rows = [
        _scenario_effect_fixture_row(
            scenario_id="cbo_baseline_noop_v1",
            delta_rw="0",
            delta_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_primary_deficit_up_1pct_v1",
            delta_rw="0.0015",
            delta_support="0.19",
            delta_tdc_support="0.19",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_combo_high_pressure_v1",
            delta_rw="0.30",
            delta_support="30",
            delta_tdc_support="40",
            delta_direct_support="-10",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_combo_lower_pressure_v1",
            delta_rw="0.08",
            delta_support="8",
            delta_tdc_support="10",
            delta_direct_support="-2",
        ),
    ]

    rows = tdcsim_cbo_model_scenario_summary_rows(effect_rows)

    by_scenario = {row["scenario_id"]: row for row in rows}
    high_pressure = by_scenario["tdcsim_combo_high_pressure_v1"]
    lower_pressure = by_scenario["tdcsim_combo_lower_pressure_v1"]
    assert high_pressure["summary_role"] == "combined_narrative_scenario"
    assert lower_pressure["summary_role"] == "combined_narrative_scenario"
    assert high_pressure["comparison_group"] == "combined_narrative"
    assert lower_pressure["comparison_group"] == "combined_narrative"
    assert high_pressure["model_interpretation"] == (
        "combined_high_pressure_deficit_reserve_shorter_rate_down"
    )
    assert lower_pressure["model_interpretation"] == (
        "combined_lower_pressure_deficit_down_domestic_longer_rate_up"
    )
    assert high_pressure["support_mechanism_profile"] == "offsetting_mixed_support"
    assert "canonical_headline_promotion" in high_pressure["blocked_use"]
    assert all(row["canonical_ratio_entry"] == "false" for row in rows)


def test_model_scenario_summary_rows_fail_closed_when_components_do_not_sum() -> None:
    effect_rows = [
        _scenario_effect_fixture_row(
            scenario_id="cbo_baseline_noop_v1",
            delta_rw="0",
            delta_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_primary_deficit_up_1pct_v1",
            delta_rw="0.0015",
            delta_support="0.19",
            delta_tdc_support="0.18",
            delta_direct_support="0",
            delta_bank_support="0",
        ),
    ]

    with pytest.raises(TdcsimCboContractError, match="components do not reconcile"):
        tdcsim_cbo_model_scenario_summary_rows(effect_rows)


def test_curve_denominator_input_rows_record_verified_curve_vector(
    tmp_path: Path,
) -> None:
    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    (scenario_dir / "18_shorter.json").write_text(
        json.dumps(
            {
                "scenario_id": (
                    "tdcsim_issuance_empirical_shorter_"
                    "termprem_down_central_v1"
                ),
                "overrides": {
                    "nominal_yield_curve": {
                        "mode": "key_rate_bp",
                        "shocks": [
                            {"tenor_years": 0.25, "shock_bp": 0},
                            {"tenor_years": 2, "shock_bp": 0},
                            {"tenor_years": 5, "shock_bp": -4},
                            {"tenor_years": 10, "shock_bp": -8},
                            {"tenor_years": 30, "shock_bp": -8},
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (scenario_dir / "21_longer.json").write_text(
        json.dumps(
            {
                "scenario_id": (
                    "tdcsim_issuance_empirical_longer_termprem_up_central_v1"
                ),
                "overrides": {
                    "nominal_yield_curve": {
                        "mode": "key_rate_bp",
                        "shocks": [
                            {"tenor_years": 0.25, "shock_bp": 0},
                            {"tenor_years": 2, "shock_bp": 0},
                            {"tenor_years": 5, "shock_bp": 4},
                            {"tenor_years": 10, "shock_bp": 8},
                            {"tenor_years": 30, "shock_bp": 8},
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    rows = tdcsim_cbo_curve_denominator_input_rows(
        _beta_chi_effect_rows(),
        scenario_config_dir=scenario_dir,
    )

    assert {field for row in rows for field in row} == set(
        CBO_CURVE_DENOMINATOR_INPUT_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    baseline = by_scenario["cbo_baseline_noop_v1"]
    assert baseline["curve_overlay_10y_bp"] == "0"
    assert baseline["curve_overlay_key_rate_source_status"] == (
        "not_applicable_zero_overlay"
    )
    assert baseline["moving_denominator_bil"] == ""

    shorter = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]
    assert shorter["curve_overlay_key_rate_source_status"] == (
        "pass_explicit_key_rates"
    )
    assert shorter["curve_overlay_5y_bp"] == "-4"
    assert shorter["curve_overlay_10y_bp"] == "-8"
    assert shorter["curve_overlay_30y_bp"] == "-8"
    assert shorter["curve_weight_sum_status"] == "pass_sum_to_one"
    assert shorter["effective_curve_overlay_bp"] == "-7"
    assert shorter["denominator_response_coefficient_status"] == "not_admitted"
    assert shorter["delta_denominator_bil_from_curve"] == ""
    assert shorter["moving_ratewall_ratio"] == ""
    assert shorter["frozen_denominator_bil"] == "1000"
    assert shorter["frozen_ratewall_ratio"] != ""
    assert shorter["canonical_ratio_entry"] == "false"
    assert shorter["enters_main_ratio"] == "false"
    assert shorter["evidence_mode_enabled"] == "false"
    assert "numeric_moving_denominator_claim_without_response_profile" in (
        shorter["blocked_use"]
    )
    assert "does_not_change_frozen_ratewall_ratio" in shorter["claim_boundary"]

    longer = by_scenario[
        "tdcsim_issuance_empirical_longer_termprem_up_central_v1"
    ]
    assert longer["curve_overlay_5y_bp"] == "4"
    assert longer["curve_overlay_10y_bp"] == "8"
    assert longer["curve_overlay_30y_bp"] == "8"
    assert longer["effective_curve_overlay_bp"] == "7"


def test_curve_denominator_input_rows_accept_parallel_curve_vector(
    tmp_path: Path,
) -> None:
    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    (scenario_dir / "rate_up.json").write_text(
        json.dumps(
            {
                "scenario_id": "tdcsim_rate_up_25bp_v1",
                "overrides": {
                    "nominal_yield_curve": {
                        "mode": "parallel_bp",
                        "shock_bp": 25,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    effect_rows = [
        _scenario_effect_fixture_row(
            scenario_id="cbo_baseline_noop_v1",
            delta_rw="0",
            delta_support="0",
        ),
        _scenario_effect_fixture_row(
            scenario_id="tdcsim_rate_up_25bp_v1",
            delta_rw="-0.03",
            delta_support="-3",
            delta_tdc_support="0",
            delta_direct_support="-3",
        ),
    ]

    rows = tdcsim_cbo_curve_denominator_input_rows(
        effect_rows,
        scenario_config_dir=scenario_dir,
    )

    by_scenario = {row["scenario_id"]: row for row in rows}
    rate_up = by_scenario["tdcsim_rate_up_25bp_v1"]
    assert rate_up["curve_overlay_5y_bp"] == "25"
    assert rate_up["curve_overlay_10y_bp"] == "25"
    assert rate_up["curve_overlay_30y_bp"] == "25"
    assert rate_up["effective_curve_overlay_bp"] == "25"
    assert rate_up["curve_overlay_key_rate_source_status"] == (
        "pass_explicit_key_rates"
    )


def test_curve_denominator_input_rows_label_unverified_design_ladder() -> None:
    rows = tdcsim_cbo_curve_denominator_input_rows(_beta_chi_effect_rows())
    by_scenario = {row["scenario_id"]: row for row in rows}

    shorter = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]

    assert shorter["curve_overlay_key_rate_source_id"] == "project_design_ladder"
    assert shorter["curve_overlay_key_rate_source_status"] == (
        "project_design_ladder_not_scenario_json_verified"
    )
    assert shorter["curve_overlay_5y_bp"] == "-4"
    assert shorter["curve_overlay_10y_bp"] == "-8"
    assert shorter["curve_overlay_30y_bp"] == "-8"
    assert shorter["moving_denominator_bil"] == ""
    assert shorter["denominator_scope"] == (
        "noncanonical_curve_vector_input_sidecar_only"
    )


def test_curve_denominator_input_rows_fail_closed_on_missing_key_rates(
    tmp_path: Path,
) -> None:
    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    (scenario_dir / "missing_30y.json").write_text(
        json.dumps(
            {
                "scenario_id": (
                    "tdcsim_issuance_empirical_shorter_"
                    "termprem_down_central_v1"
                ),
                "overrides": {
                    "nominal_yield_curve": {
                        "mode": "key_rate_bp",
                        "shocks": [
                            {"tenor_years": 5, "shock_bp": -4},
                            {"tenor_years": 10, "shock_bp": -8},
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TdcsimCboContractError, match="missing required curve"):
        tdcsim_cbo_curve_denominator_input_rows(
            _beta_chi_effect_rows(),
            scenario_config_dir=scenario_dir,
        )


def test_curve_sensitive_denominator_assumption_bounds_rows() -> None:
    rows = tdcsim_cbo_curve_sensitive_denominator_assumption_bound_rows(
        _beta_chi_effect_rows()
    )

    assert {field for row in rows for field in row} == set(
        CBO_CURVE_SENSITIVE_DENOMINATOR_ASSUMPTION_BOUND_FIELDS
    )
    assert len(rows) == 9 * 3
    assert {row["denominator_response_profile_tier"] for row in rows} == {
        "low",
        "base",
        "high",
    }
    assert {row["theta_curve_relative_to_policy_anchor"] for row in rows} == {
        "0",
        "0.125",
        "0.25",
    }
    assert {row["coefficient_empirical_claim_allowed"] for row in rows} == {
        "false"
    }
    assert {row["coefficient_source_status"] for row in rows} == {
        "not_literature_calibrated_not_econometrically_estimated"
    }
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["denominator_prior_update_allowed"] for row in rows} == {"false"}
    assert {row["formula_replacement_allowed"] for row in rows} == {"false"}
    assert {row["causal_market_yield_estimate_enabled"] for row in rows} == {
        "false"
    }
    for row in rows:
        assert "empirical_denominator_response_claim" in row["blocked_use"]
        assert "not_econometrically_estimated" in row["claim_boundary"]
        assert Decimal(row["moving_denominator_bil"]) > 0

    by_key = {
        (row["scenario_id"], row["denominator_response_profile_tier"]): row
        for row in rows
    }
    baseline_base = by_key[("cbo_baseline_noop_v1", "base")]
    assert baseline_base["delta_denominator_bil_from_curve"] == "0"
    assert baseline_base["moving_denominator_bil"] == (
        baseline_base["frozen_denominator_bil"]
    )
    assert baseline_base["moving_ratewall_ratio"] == (
        baseline_base["frozen_ratewall_ratio"]
    )

    shorter_base = by_key[
        (
            "tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            "base",
        )
    ]
    frozen_d = Decimal(shorter_base["frozen_denominator_bil"])
    effective = Decimal(shorter_base["effective_curve_overlay_bp"])
    theta = Decimal(shorter_base["theta_curve_relative_to_policy_anchor"])
    expected_delta_d = frozen_d * theta * effective / Decimal("100")
    expected_moving_d = frozen_d + expected_delta_d
    expected_ratio = (
        Decimal(shorter_base["total_current_demand_support_bil"])
        / expected_moving_d
    )
    assert Decimal(shorter_base["delta_denominator_bil_from_curve"]) == (
        expected_delta_d
    )
    assert Decimal(shorter_base["moving_denominator_bil"]) == expected_moving_d
    assert Decimal(shorter_base["moving_ratewall_ratio"]) == expected_ratio
    assert shorter_base["denominator_response_direction"] == (
        "negative_curve_overlay_decreases_denominator"
    )

    longer_high = by_key[
        (
            "tdcsim_issuance_empirical_longer_termprem_up_central_v1",
            "high",
        )
    ]
    assert Decimal(longer_high["delta_denominator_bil_from_curve"]) > 0
    assert longer_high["denominator_response_direction"] == (
        "positive_curve_overlay_increases_denominator"
    )
    assert longer_high["transport_rule"] == (
        "gamma_curve_equals_theta_curve_times_frozen_policy_drag_anchor"
    )


def test_model_scenario_interpretation_synthesis_rows() -> None:
    rows = tdcsim_cbo_model_scenario_interpretation_synthesis_rows(
        _beta_chi_effect_rows()
    )

    assert {field for row in rows for field in row} == set(
        CBO_MODEL_SCENARIO_INTERPRETATION_SYNTHESIS_FIELDS
    )
    assert len(rows) == 9
    by_scenario = {row["scenario_id"]: row for row in rows}

    baseline = by_scenario["cbo_baseline_noop_v1"]
    assert baseline["final_interpretation"] == "baseline_anchor_no_delta"
    assert baseline["denominator_bound_sign_stability_status"] == (
        "zero_or_baseline_only"
    )
    assert baseline["denominator_bound_theta_values"] == "0;0.125;0.25"
    assert baseline["denominator_bound_min_delta_denominator_bil"] == "0"
    assert baseline["denominator_bound_max_delta_denominator_bil"] == "0"
    assert baseline["selected_denominator_response_profile_id"] == (
        FRBUS_STRUCTURAL_PROFILE_ID
    )
    assert baseline["selected_denominator_response_coefficient"] == (
        FRBUS_STRUCTURAL_COEFFICIENT
    )
    assert baseline["selected_delta_denominator_bil"] == "0"
    assert baseline["selected_moving_denominator_bil"] == "1000"
    assert baseline["selected_denominator_response_status"] == (
        "zero_rate_path_frozen_D_consistent"
    )

    shorter = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]
    assert shorter["beta_chi_sign_stability_status"] == "mixed_sign"
    assert shorter["final_interpretation"] == (
        "point_calibration_not_beta_chi_sign_robust"
    )
    assert shorter["curve_effective_overlay_bp"] == "-7"
    assert shorter["denominator_bound_sign_stability_status"] == (
        "denominator_bounds_mixed_sign"
    )
    assert Decimal(shorter["denominator_bound_min_delta_denominator_bil"]) < 0
    assert shorter["denominator_bound_max_delta_denominator_bil"] == "0"
    assert shorter["selected_denominator_response_profile_id"] == (
        FRBUS_STRUCTURAL_PROFILE_ID
    )
    assert Decimal(shorter["selected_delta_denominator_bil"]) < (
        Decimal(shorter["denominator_bound_min_delta_denominator_bil"])
    )
    assert shorter["selected_moving_denominator_bil"].startswith(
        "921.609155966752"
    )
    assert shorter["selected_denominator_response_status"] == (
        "pass_moving_D_computed_from_admitted_profile"
    )
    assert shorter["primary_deficit_scale_bucket"] == (
        "less_than_quarter_primary_deficit_up_1pct"
    )
    assert shorter["component_delta_sum_status"] == (
        "pass_components_sum_to_total_support_delta"
    )
    assert Decimal(shorter["tdc_delta_abs_contribution_share"]) > 0
    assert Decimal(shorter["direct_treasury_delta_abs_contribution_share"]) > 0
    assert shorter["support_mechanism_profile"] in {
        "tdc_support_dominant",
        "mixed_support",
        "offsetting_mixed_support",
    }

    primary_up = by_scenario["tdcsim_primary_deficit_up_1pct_v1"]
    assert primary_up["beta_chi_sign_stability_status"] == "stable_positive"
    assert primary_up["denominator_bound_sign_stability_status"] == (
        "denominator_bounds_preserve_point_sign"
    )
    assert primary_up["final_interpretation"] == (
        "sign_stable_over_beta_chi_and_denominator_bounds"
    )
    assert primary_up["primary_deficit_scale_bucket"] == (
        "near_primary_deficit_up_1pct"
    )
    assert primary_up["canonical_ratio_entry"] == "false"
    assert "empirical_denominator_response_claim" in primary_up["blocked_use"]

    holder_low = by_scenario["tdcsim_holder_source_reserve_user_absorption_v1"]
    assert holder_low["comparison_group"] == "holder_preference"
    assert holder_low["support_mechanism_profile"] == "offsetting_mixed_support"
    assert holder_low["primary_deficit_scale_bucket"] == (
        "larger_than_primary_deficit_up_1pct"
    )


def test_model_scenario_materiality_classification_rows_rank_and_flag_robustness(
    tmp_path: Path,
) -> None:
    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    (scenario_dir / "combo.json").write_text(
        json.dumps(
            {
                "scenario_id": "tdcsim_combo_high_pressure_v1",
                "overrides": {
                    "nominal_yield_curve": {
                        "mode": "key_rate_bp",
                        "shocks": [
                            {"tenor_years": 0.25, "shock_bp": 0},
                            {"tenor_years": 2, "shock_bp": 0},
                            {"tenor_years": 5, "shock_bp": -4},
                            {"tenor_years": 10, "shock_bp": -8},
                            {"tenor_years": 30, "shock_bp": -8},
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    effect_rows = [
        *_beta_chi_effect_rows(),
        _robustness_effect_row(
            scenario_id="tdcsim_combo_high_pressure_v1",
            tdc_change="3000",
            direct="-15",
            bank="1",
        ),
    ]

    rows = tdcsim_cbo_model_scenario_materiality_classification_rows(
        effect_rows,
        scenario_config_dir=scenario_dir,
    )

    assert {field for row in rows for field in row} == set(
        CBO_MODEL_SCENARIO_MATERIALITY_CLASSIFICATION_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    baseline = by_scenario["cbo_baseline_noop_v1"]
    assert baseline["materiality_rank_abs_delta"] == "0"
    assert baseline["scenario_family"] == "baseline"
    assert baseline["recommended_use"] == "baseline_reference_only"

    combo = by_scenario["tdcsim_combo_high_pressure_v1"]
    assert combo["materiality_rank_abs_delta"] == "1"
    assert combo["scenario_family"] == "composite_assumption"
    assert combo["materiality_tier_vs_primary_deficit_up_1pct"] == (
        "large_above_primary_deficit_up_1pct"
    )
    assert combo["beta_chi_robustness_class"] == (
        "point_calibration_only_beta_chi_mixed_sign"
    )
    assert combo["denominator_recompute_readiness"] == (
        "curve_metadata_present_frbus_coefficient_admitted"
    )
    assert combo["model_relevance_class"].endswith("point_calibration_only")
    assert combo["recommended_use"] == (
        "scenario_mode_interpretation_only_not_canonical"
    )
    assert combo["canonical_ratio_entry"] == "false"
    assert combo["denominator_prior_update_allowed"] == "false"

    primary_up = by_scenario["tdcsim_primary_deficit_up_1pct_v1"]
    assert primary_up["beta_chi_robustness_class"] == (
        "sign_stable_over_beta_chi_grid"
    )
    assert primary_up["recommended_use"] == (
        "scenario_mode_sign_stable_comparator_not_canonical"
    )


def test_curve_denominator_empirical_status_rows_record_frbus_structural_profile() -> None:
    rows = tdcsim_cbo_curve_denominator_empirical_status_rows(
        _beta_chi_effect_rows()
    )

    assert {field for row in rows for field in row} == set(
        CBO_CURVE_DENOMINATOR_EMPIRICAL_STATUS_FIELDS
    )
    assert len(rows) == 9
    assert {row["empirical_denominator_coefficient_status"] for row in rows} == {
        "admitted_structural_curve_denominator_response_coefficient"
    }
    assert {row["literature_calibrated_coefficient_status"] for row in rows} == {
        "admitted_frbus_structural_curve_to_denominator_coefficient"
    }
    assert {row["econometric_estimate_status"] for row in rows} == {
        "no_econometrically_admitted_curve_to_denominator_coefficient"
    }
    assert {row["admitted_curve_response_coefficient"] for row in rows} == {
        FRBUS_STRUCTURAL_COEFFICIENT
    }
    assert {row["current_denominator_profile_status"] for row in rows} == {
        "frbus_structural_profile_selected_with_assumption_bounds_retained"
    }
    assert {row["current_denominator_profile_used_for_scenarios"] for row in rows} == {
        FRBUS_STRUCTURAL_PROFILE_ID
    }
    assert {row["candidate_econometric_surface_status"] for row in rows} == {
        "not_available_in_current_tdcsim_cbo_suite"
    }
    assert {row["denominator_model_decision"] for row in rows} == {
        "use_frbus_structural_moving_D_for_rate_changing_model_scenarios"
    }
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["denominator_prior_update_allowed"] for row in rows} == {"false"}

    by_scenario = {row["scenario_id"]: row for row in rows}
    shorter = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]
    assert shorter["curve_effective_overlay_bp"] == "-7"
    assert shorter["denominator_bound_theta_values"] == "0;0.125;0.25"
    assert shorter["selected_denominator_response_profile_id"] == (
        FRBUS_STRUCTURAL_PROFILE_ID
    )
    assert shorter["selected_moving_denominator_bil"].startswith(
        "921.609155966752"
    )
    assert shorter["selected_denominator_response_status"] == (
        "pass_moving_D_computed_from_admitted_profile"
    )
    assert len(shorter["linked_assumption_bound_row_ids"].split(";")) == 3
    assert "empirical_denominator_response_claim" in shorter["blocked_use"]
    assert "not_local_econometric_estimate" in shorter["claim_boundary"]


def test_model_scenario_beta_chi_robustness_rows_recompute_grid() -> None:
    effect_rows = _beta_chi_effect_rows()
    summary_rows = tdcsim_cbo_model_scenario_summary_rows(effect_rows)

    rows = tdcsim_cbo_model_scenario_beta_chi_robustness_rows(effect_rows)

    assert {field for row in rows for field in row} == set(
        CBO_MODEL_SCENARIO_BETA_CHI_ROBUSTNESS_FIELDS
    )
    assert len(rows) == (
        len(summary_rows)
        * len(BETA_CHI_ROBUSTNESS_BETA_PROFILES)
        * len(BETA_CHI_ROBUSTNESS_CHI_PROFILES)
    )
    beta_values = {
        row["tdc_materialization_beta_scenario"]: row["tdc_materialization_beta"]
        for row in rows
    }
    assert beta_values["normal_forward"] == "0.34201759129420367"
    assert beta_values["latest_rolling_persistence"] == "0.5307509589554447"
    assert beta_values["pooled_full_sample"] == "0.6163494354563133"
    assert beta_values["pandemic_exclusion_drop_2020"] == "0.2478871263682468"
    assert "0.97" not in set(beta_values.values())
    base_rows = [
        row for row in rows if row["profile_is_current_point_calibration"] == "true"
    ]
    assert len(base_rows) == len(summary_rows)
    summary_by_scenario = {row["scenario_id"]: row for row in summary_rows}
    for row in base_rows:
        summary = summary_by_scenario[row["scenario_id"]]
        assert row["level_ratewall_ratio_recomputed"] == summary[
            "level_ratewall_ratio"
        ]
        assert Decimal(row["delta_ratewall_ratio_vs_baseline_recomputed"]) == (
            Decimal(summary["delta_ratewall_ratio_vs_baseline"])
        )

    shorter_rows = [
        row
        for row in rows
        if row["scenario_id"] == "tdcsim_issuance_empirical_shorter_uncoupled_v1"
    ]
    assert {row["direct_treasury_current_demand_support_bil_fixed"] for row in shorter_rows} == {
        "8"
    }
    assert {row["bank_treasury_current_demand_support_bil_fixed"] for row in shorter_rows} == {
        "1"
    }
    high = next(
        row
        for row in shorter_rows
        if row["tdc_materialization_beta_scenario"] == "normal_forward_upper95"
        and row["deposit_current_demand_share_profile"] == "demand_active"
    )
    assert Decimal(high["tdc_current_demand_support_bil_recomputed"]) == (
        Decimal("200") * Decimal("0.5685311077760121") * Decimal("0.12")
    )
    assert high["primary_deficit_up_1pct_delta_ratewall_ratio_recomputed"] != (
        high["abs_delta_vs_current_point_primary_deficit_up_1pct"]
    )
    assert high["canonical_ratio_entry"] == "false"
    assert "denominator_change" in high["blocked_use"]
    assert "posterior_beta_claim" in high["blocked_use"]


def test_model_scenario_beta_chi_robustness_recomputes_paired_overlay() -> None:
    rows = tdcsim_cbo_model_scenario_beta_chi_robustness_rows(
        _beta_chi_effect_rows()
    )
    by_key = {
        (
            row["scenario_id"],
            row["tdc_materialization_beta_scenario"],
            row["deposit_current_demand_share_profile"],
        ): row
        for row in rows
    }
    coupled = by_key[
        (
            "tdcsim_issuance_empirical_shorter_termprem_down_central_v1",
            "normal_forward",
            "base",
        )
    ]
    paired = by_key[
        (
            "tdcsim_issuance_empirical_shorter_uncoupled_v1",
            "normal_forward",
            "base",
        )
    ]
    assert Decimal(coupled["rate_overlay_delta_ratewall_ratio_recomputed"]) == (
        Decimal(coupled["delta_ratewall_ratio_vs_baseline_recomputed"])
        - Decimal(paired["delta_ratewall_ratio_vs_baseline_recomputed"])
    )
    assert coupled["paired_issuance_only_scenario_id"] == (
        "tdcsim_issuance_empirical_shorter_uncoupled_v1"
    )


def test_model_scenario_beta_chi_sign_stability_rows_classify_crossings() -> None:
    rows = tdcsim_cbo_model_scenario_beta_chi_sign_stability_rows(
        _beta_chi_effect_rows()
    )

    assert {field for row in rows for field in row} == set(
        CBO_MODEL_SCENARIO_BETA_CHI_SIGN_STABILITY_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    shorter = by_scenario["tdcsim_issuance_empirical_shorter_uncoupled_v1"]
    assert shorter["sign_stability_status"] == "mixed_sign"
    assert shorter["zero_crossing_status"] == "inside_grid"
    assert shorter["wall_hit_any_grid_cell"] == "false"
    assert shorter["canonical_ratio_entry"] == "false"
    assert "statistical_significance_claim" in shorter["blocked_use"]

    primary_up = by_scenario["tdcsim_primary_deficit_up_1pct_v1"]
    assert primary_up["sign_stability_status"] == "stable_positive"
    assert primary_up["same_sign_cell_count"] == str(
        len(BETA_CHI_ROBUSTNESS_BETA_PROFILES)
        * len(BETA_CHI_ROBUSTNESS_CHI_PROFILES)
    )
    primary_down = by_scenario["tdcsim_primary_deficit_down_1pct_v1"]
    assert primary_down["sign_stability_status"] == "stable_negative"


def test_model_scenario_beta_chi_robustness_requires_effect_operands() -> None:
    effect_rows = _beta_chi_effect_rows()
    for row in effect_rows:
        row.pop("tdc_change_ex_overlap_bil", None)

    with pytest.raises(TdcsimCboContractError, match="missing field"):
        tdcsim_cbo_model_scenario_beta_chi_robustness_rows(effect_rows)


def test_cbo_settlement_accrual_bridge_decomposes_gross_maturity_cash(
    tmp_path: Path,
) -> None:
    package = _package(tmp_path, scenario_id="cbo_baseline_noop_v1")

    rows = tdcsim_cbo_settlement_accrual_bridge_rows(
        [package],
        fiscal_years=[2027],
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    assert {field for row in rows for field in row} == set(
        CBO_SETTLEMENT_ACCRUAL_BRIDGE_FIELDS
    )
    maturity_rows = [
        row for row in rows if row["bridge_family"] == "du_maturity_cash_decomposition"
    ]
    assert len(maturity_rows) == 1
    maturity = maturity_rows[0]
    assert maturity["settlement_cash_bil"] == "132"
    assert maturity["principal_component_bil"] == "120"
    assert maturity["interest_or_accrual_component_bil"] == "12"
    assert "do not use gross cash as principal" in maturity["treatment_note"]

    bank_rows = [
        row
        for row in rows
        if row["bridge_family"] == "payment_flow_accounting_basis"
        and row["holder_sector"] == "Banks"
        and row["payment_type"] == "fixed_coupon"
    ]
    assert len(bank_rows) == 1
    assert bank_rows[0]["ratewall_current_demand_basis_bil"] == "20"
    assert bank_rows[0]["settlement_cash_bil"] == "20"


def test_cbo_core_scenario_interpretation_keeps_core_point_rank(
    tmp_path: Path,
) -> None:
    baseline = _package(
        tmp_path,
        scenario_id="cbo_baseline_noop_v1",
        tdc_ex_overlap_per_period="90",
        direct_interest_per_period="10",
        bank_interest_per_period="5",
    )
    high_private = _package(
        tmp_path,
        scenario_id="tdcsim_holder_source_domestic_nonbank_absorption_v1",
        tdc_ex_overlap_per_period="50",
        direct_interest_per_period="10",
        bank_interest_per_period="5",
    )
    shorter = _package(
        tmp_path,
        scenario_id="tdcsim_issuance_shorter_v1",
        tdc_ex_overlap_per_period="120",
        direct_interest_per_period="10",
        bank_interest_per_period="5",
    )
    diagnostic = _package(
        tmp_path,
        scenario_id="cbo_fiscal_fed_cash_v1",
        tdc_ex_overlap_per_period="150",
        direct_interest_per_period="10",
        bank_interest_per_period="5",
    )
    effect_rows = tdcsim_cbo_scenario_effect_rows(
        [baseline, high_private, shorter, diagnostic],
        fiscal_years=[2027],
        denominator_by_fiscal_year={2027: Decimal("1000")},
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    rows = tdcsim_cbo_core_scenario_interpretation_rows(effect_rows)

    assert {field for row in rows for field in row} == set(
        CBO_CORE_SCENARIO_INTERPRETATION_FIELDS
    )
    assert [row["scenario_id"] for row in rows] == [
        "tdcsim_issuance_shorter_v1",
        "cbo_baseline_noop_v1",
        "tdcsim_holder_source_domestic_nonbank_absorption_v1",
    ]
    assert [row["point_calibration_rank"] for row in rows] == ["1", "2", "3"]
    assert {row["wall_hit_status"] for row in rows} == {"no_hit"}
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert all(
        row["ranking_stability"] == "point_calibration_only_not_coefficient_robust"
        for row in rows
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    assert by_scenario["tdcsim_issuance_shorter_v1"][
        "delta_direction_vs_baseline"
    ] == "above_baseline"
    assert by_scenario["tdcsim_holder_source_domestic_nonbank_absorption_v1"][
        "delta_direction_vs_baseline"
    ] == "below_baseline"
    assert by_scenario["cbo_baseline_noop_v1"][
        "delta_direction_vs_baseline"
    ] == "baseline"


def test_cbo_matched_response_coefficients_use_actual_axis_values(
    tmp_path: Path,
) -> None:
    baseline = _package(
        tmp_path,
        scenario_id="cbo_baseline_noop_v1",
        tdc_ex_overlap_per_period="90",
        weighted_original_term_years="6",
        du_absorbed_issuance_proceeds_per_period="40",
    )
    rate_down = _package(
        tmp_path,
        scenario_id="tdcsim_rate_down_25bp_v1",
        tdc_ex_overlap_per_period="80",
        weighted_original_term_years="6",
        du_absorbed_issuance_proceeds_per_period="40",
    )
    rate_up = _package(
        tmp_path,
        scenario_id="tdcsim_rate_up_25bp_v1",
        tdc_ex_overlap_per_period="100",
        weighted_original_term_years="6",
        du_absorbed_issuance_proceeds_per_period="40",
    )
    issuance_shorter = _package(
        tmp_path,
        scenario_id="tdcsim_issuance_shorter_v1",
        tdc_ex_overlap_per_period="110",
        weighted_original_term_years="2",
        du_absorbed_issuance_proceeds_per_period="40",
    )
    issuance_longer = _package(
        tmp_path,
        scenario_id="tdcsim_issuance_longer_v1",
        tdc_ex_overlap_per_period="70",
        weighted_original_term_years="10",
        du_absorbed_issuance_proceeds_per_period="40",
    )
    private_low = _package(
        tmp_path,
        scenario_id="tdcsim_holder_source_reserve_user_absorption_v1",
        tdc_ex_overlap_per_period="85",
        weighted_original_term_years="6",
        du_absorbed_issuance_proceeds_per_period="20",
    )
    private_high = _package(
        tmp_path,
        scenario_id="tdcsim_holder_source_domestic_nonbank_absorption_v1",
        tdc_ex_overlap_per_period="95",
        weighted_original_term_years="6",
        du_absorbed_issuance_proceeds_per_period="80",
    )
    mmf_low = _package(
        tmp_path,
        scenario_id="tdcsim_mmf_pass_through_90_v1",
        tdc_ex_overlap_per_period="84",
        weighted_original_term_years="6",
        du_absorbed_issuance_proceeds_per_period="40",
        metadata_override=_mmf_metadata_override("0.90"),
    )
    mmf_high = _package(
        tmp_path,
        scenario_id="tdcsim_mmf_pass_through_99_v1",
        tdc_ex_overlap_per_period="96",
        weighted_original_term_years="6",
        du_absorbed_issuance_proceeds_per_period="40",
        metadata_override=_mmf_metadata_override("0.99"),
    )
    primary_down = _package(
        tmp_path,
        scenario_id="tdcsim_primary_deficit_down_1pct_v1",
        tdc_ex_overlap_per_period="85",
        weighted_original_term_years="6",
        du_absorbed_issuance_proceeds_per_period="40",
    )
    primary_up = _package(
        tmp_path,
        scenario_id="tdcsim_primary_deficit_up_1pct_v1",
        tdc_ex_overlap_per_period="95",
        weighted_original_term_years="6",
        du_absorbed_issuance_proceeds_per_period="40",
    )

    rows = tdcsim_cbo_matched_response_coefficient_rows(
        [
            baseline,
            rate_down,
            rate_up,
            issuance_shorter,
            issuance_longer,
            private_low,
            private_high,
            mmf_low,
            mmf_high,
            primary_down,
            primary_up,
        ],
        fiscal_years=[2027],
        denominator_by_fiscal_year={2027: Decimal("1000")},
    )

    assert {field for row in rows for field in row} == set(
        CBO_MATCHED_RESPONSE_COEFFICIENT_FIELDS
    )
    by_key = {
        (row["response_axis"], row["outcome_name"]): row
        for row in rows
    }
    rate_total = by_key[
        ("nominal_rate_parallel", "total_current_demand_support_bil")
    ]
    assert rate_total["baseline_x"] == "0"
    assert rate_total["low_x"] == "-25"
    assert rate_total["high_x"] == "25"
    assert Decimal(rate_total["signed_slope_per_x"]) > Decimal("0")
    assert rate_total["symmetry_status"] == "locally_symmetric_around_baseline"

    issuance_total = by_key[
        ("issuance_maturity_mix", "total_current_demand_support_bil")
    ]
    assert issuance_total["low_x"] == "2"
    assert issuance_total["high_x"] == "10"
    assert Decimal(issuance_total["signed_slope_per_x"]) < Decimal("0")

    private_total = by_key[
        (
            "source_grounded_private_du_issuance_share",
            "total_current_demand_support_bil",
        )
    ]
    assert private_total["low_scenario_id"] == (
        "tdcsim_holder_source_reserve_user_absorption_v1"
    )
    assert private_total["high_scenario_id"] == (
        "tdcsim_holder_source_domestic_nonbank_absorption_v1"
    )
    assert Decimal(private_total["low_x"]) < Decimal(private_total["high_x"])
    mmf_total = by_key[
        ("mmf_deposit_pass_through", "total_current_demand_support_bil")
    ]
    assert mmf_total["baseline_x"] == "0.97"
    assert mmf_total["low_x"] == "0.9"
    assert mmf_total["high_x"] == "0.99"
    assert mmf_total["low_scenario_id"] == "tdcsim_mmf_pass_through_90_v1"
    assert mmf_total["high_scenario_id"] == "tdcsim_mmf_pass_through_99_v1"
    primary_total = by_key[
        ("primary_deficit_scale", "total_current_demand_support_bil")
    ]
    assert primary_total["low_x"] == "0.99"
    assert primary_total["high_x"] == "1.01"
    assert Decimal(primary_total["signed_slope_per_x"]) > Decimal("0")
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert all("denominator_change" in row["blocked_use"] for row in rows)


def test_cbo_matched_period_response_keeps_timing_separate(
    tmp_path: Path,
) -> None:
    packages = [
        _package(
            tmp_path,
            scenario_id="cbo_baseline_noop_v1",
            tdc_ex_overlap_per_period="90",
            weighted_original_term_years="6",
            du_absorbed_issuance_proceeds_per_period="40",
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_rate_down_25bp_v1",
            tdc_ex_overlap_per_period="80",
            weighted_original_term_years="6",
            du_absorbed_issuance_proceeds_per_period="40",
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_rate_up_25bp_v1",
            tdc_ex_overlap_per_period="100",
            weighted_original_term_years="6",
            du_absorbed_issuance_proceeds_per_period="40",
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_issuance_shorter_v1",
            tdc_ex_overlap_per_period="110",
            weighted_original_term_years="2",
            du_absorbed_issuance_proceeds_per_period="40",
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_issuance_longer_v1",
            tdc_ex_overlap_per_period="70",
            weighted_original_term_years="10",
            du_absorbed_issuance_proceeds_per_period="40",
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_holder_source_reserve_user_absorption_v1",
            tdc_ex_overlap_per_period="85",
            weighted_original_term_years="6",
            du_absorbed_issuance_proceeds_per_period="20",
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_holder_source_domestic_nonbank_absorption_v1",
            tdc_ex_overlap_per_period="95",
            weighted_original_term_years="6",
            du_absorbed_issuance_proceeds_per_period="80",
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_mmf_pass_through_90_v1",
            tdc_ex_overlap_per_period="84",
            weighted_original_term_years="6",
            du_absorbed_issuance_proceeds_per_period="40",
            metadata_override=_mmf_metadata_override("0.90"),
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_mmf_pass_through_99_v1",
            tdc_ex_overlap_per_period="96",
            weighted_original_term_years="6",
            du_absorbed_issuance_proceeds_per_period="40",
            metadata_override=_mmf_metadata_override("0.99"),
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_primary_deficit_down_1pct_v1",
            tdc_ex_overlap_per_period="85",
            weighted_original_term_years="6",
            du_absorbed_issuance_proceeds_per_period="40",
        ),
        _package(
            tmp_path,
            scenario_id="tdcsim_primary_deficit_up_1pct_v1",
            tdc_ex_overlap_per_period="95",
            weighted_original_term_years="6",
            du_absorbed_issuance_proceeds_per_period="40",
        ),
    ]

    rows = tdcsim_cbo_matched_period_response_rows(
        packages,
        fiscal_years=[2027],
    )

    assert {field for row in rows for field in row} == set(
        CBO_MATCHED_PERIOD_RESPONSE_FIELDS
    )
    row = next(
        item
        for item in rows
        if item["response_axis"] == "nominal_rate_parallel"
        and item["outcome_name"] == "total_current_demand_support_bil"
        and item["period_end"] == "2026-12-31"
    )
    assert row["lag_days_from_fiscal_year_start"] == "91"
    assert Decimal(row["low_delta_vs_baseline"]) < Decimal("0")
    assert Decimal(row["high_delta_vs_baseline"]) > Decimal("0")
    assert Decimal(row["central_difference_delta"]) > Decimal("0")
    assert row["canonical_ratio_entry"] == "false"
    assert "annual_ratio_replacement" in row["blocked_use"]


def test_cbo_scenario_lever_diagnostic_classifies_near_noop_rows(
    tmp_path: Path,
) -> None:
    baseline = _package(
        tmp_path,
        scenario_id="cbo_baseline_noop_v1",
        tdc_ex_overlap_per_period="90",
    )
    primary = _package(
        tmp_path,
        scenario_id="tdcsim_primary_deficit_up_1pct_v1",
        tdc_ex_overlap_per_period="100",
        scenario_overrides={"primary_deficit": {"mode": "scale_path", "scale": 1.01}},
    )
    operating_cash = _package(
        tmp_path,
        scenario_id="tdcsim_operating_cash_inflation_beta_50_v1",
        tdc_ex_overlap_per_period="90",
        scenario_overrides={"operating_cash": {"mode": "inflation_beta", "beta": 0.5}},
    )
    fed = _package(
        tmp_path,
        scenario_id="tdcsim_fed_holdings_scale_1_v1",
        tdc_ex_overlap_per_period="90",
        scenario_overrides={"fed_holdings": {"mode": "scale_path", "scale": 1.0}},
    )

    rows = tdcsim_cbo_scenario_lever_diagnostic_rows(
        [baseline, primary, operating_cash, fed],
        fiscal_years=[2027],
        denominator_by_fiscal_year={2027: Decimal("1000")},
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    assert {field for row in rows for field in row} == set(
        CBO_SCENARIO_LEVER_DIAGNOSTIC_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    assert by_scenario["tdcsim_primary_deficit_up_1pct_v1"][
        "response_status"
    ] == "active_tdc_fiscal_flow_only_debt_path_fixed"
    assert Decimal(
        by_scenario["tdcsim_primary_deficit_up_1pct_v1"][
            "delta_tdc_fiscal_flow_bil"
        ]
    ) > Decimal("0")
    assert by_scenario["tdcsim_primary_deficit_up_1pct_v1"][
        "delta_route_face_issued_bil"
    ] == "0"
    assert by_scenario["tdcsim_operating_cash_inflation_beta_50_v1"][
        "response_status"
    ] == "no_exported_ratewall_numerator_effect"
    assert by_scenario["tdcsim_fed_holdings_scale_1_v1"][
        "response_status"
    ] == "baseline_equivalent_scale_value"
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert all("denominator_change" in row["blocked_use"] for row in rows)


def test_cbo_route_stock_closure_rows_are_diagnostic_only(tmp_path: Path) -> None:
    package = _package(tmp_path, scenario_id="tdcsim_issuance_shorter_v1")

    rows = tdcsim_cbo_route_stock_closure_rows(
        [package],
        fiscal_years=[2027],
        expected_mmf_deposit_pass_through=Decimal("0.97"),
    )

    assert rows
    assert {field for row in rows for field in row} == set(
        CBO_ROUTE_STOCK_CLOSURE_FIELDS
    )
    assert {row["scenario_id"] for row in rows} == {"tdcsim_issuance_shorter_v1"}
    assert {row["route_stock_basis"] for row in rows} == {
        "tdc_principal_settlement_route"
    }
    assert {row["allowed_use"] for row in rows} == {
        "tdcsim_principal_route_stock_closure_diagnostic"
    }
    assert {row["blocked_use"] for row in rows} == {
        "denominator_replacement_or_canonical_ratio_math"
    }
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    for row in rows:
        lhs = (
            Decimal(row["opening_route_stock_bil"])
            + Decimal(row["route_face_issued_bil"])
            - Decimal(row["route_face_redeemed_bil"])
            + Decimal(row["route_stock_residual_or_indexation_bil"])
        )
        assert lhs == Decimal(row["closing_route_stock_bil"])
        assert Decimal(row["closure_identity_error_bil"]) == Decimal("0")


def test_cbo_ratio_input_writer_uses_exact_fields(tmp_path: Path) -> None:
    from ratewall.databook.build_legacy import (
        _write_tdcsim_cbo_core_scenario_interpretation_table,
        _write_tdcsim_cbo_fiscal_year_ratio_input_table,
        _write_tdcsim_cbo_matched_period_response_table,
        _write_tdcsim_cbo_matched_response_coefficient_table,
        _write_tdcsim_cbo_route_stock_closure_table,
        _write_tdcsim_cbo_scenario_effect_table,
        _write_tdcsim_cbo_scenario_lever_diagnostic_table,
        _write_tdcsim_cbo_settlement_accrual_bridge_table,
    )

    row = {field: "" for field in CBO_FISCAL_YEAR_RATIO_INPUT_FIELDS}
    row.update(
        {
            "tdcsim_cbo_ratio_input_row_id": "tdcsim_cbo_ratio_input::2027::baseline",
            "scenario_id": "baseline",
            "fiscal_year": "2027",
            "frozen_denominator_bil": "1000",
            "ratewall_ratio": "0.01",
            "denominator_scope": "external_frozen_by_fiscal_year",
        }
    )
    path = tmp_path / "ratewall_tdcsim_cbo_fiscal_year_ratio_input.csv"

    _write_tdcsim_cbo_fiscal_year_ratio_input_table(path, [row])

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == CBO_FISCAL_YEAR_RATIO_INPUT_FIELDS
        assert list(reader) == [row]

    effect_row = {field: "" for field in CBO_SCENARIO_EFFECT_FIELDS}
    effect_row.update(
        {
            "tdcsim_cbo_scenario_effect_row_id": (
                "tdcsim_cbo_scenario_effect::2027::baseline"
            ),
            "scenario_id": "baseline",
            "fiscal_year": "2027",
            "level_ratewall_ratio": "0.01",
            "delta_ratewall_ratio_vs_baseline": "0",
        }
    )
    effect_path = tmp_path / "ratewall_tdcsim_cbo_scenario_effect.csv"

    _write_tdcsim_cbo_scenario_effect_table(effect_path, [effect_row])

    with effect_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == CBO_SCENARIO_EFFECT_FIELDS
        assert list(reader) == [effect_row]

    interpretation_row = {
        field: "" for field in CBO_CORE_SCENARIO_INTERPRETATION_FIELDS
    }
    interpretation_row.update(
        {
            "tdcsim_cbo_core_scenario_interpretation_row_id": (
                "tdcsim_cbo_core_scenario_interpretation::2027::baseline"
            ),
            "scenario_id": "baseline",
            "fiscal_year": "2027",
            "level_ratewall_ratio": "0.01",
            "delta_ratewall_ratio_vs_baseline": "0",
        }
    )
    interpretation_path = (
        tmp_path / "ratewall_tdcsim_cbo_core_scenario_interpretation.csv"
    )

    _write_tdcsim_cbo_core_scenario_interpretation_table(
        interpretation_path, [interpretation_row]
    )

    with interpretation_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == CBO_CORE_SCENARIO_INTERPRETATION_FIELDS
        assert list(reader) == [interpretation_row]

    bridge_row = {field: "" for field in CBO_SETTLEMENT_ACCRUAL_BRIDGE_FIELDS}
    bridge_row.update(
        {
            "tdcsim_cbo_settlement_accrual_bridge_row_id": (
                "tdcsim_cbo_settlement_accrual_bridge::2027::baseline"
            ),
            "scenario_id": "baseline",
            "fiscal_year": "2027",
            "bridge_family": "du_maturity_cash_decomposition",
        }
    )
    bridge_path = tmp_path / "ratewall_tdcsim_cbo_settlement_accrual_bridge.csv"

    _write_tdcsim_cbo_settlement_accrual_bridge_table(bridge_path, [bridge_row])

    with bridge_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == CBO_SETTLEMENT_ACCRUAL_BRIDGE_FIELDS
        assert list(reader) == [bridge_row]

    closure_row = {field: "" for field in CBO_ROUTE_STOCK_CLOSURE_FIELDS}
    closure_row.update(
        {
            "tdcsim_cbo_route_stock_closure_row_id": (
                "tdcsim_cbo_route_stock_closure::2027::baseline"
            ),
            "scenario_id": "baseline",
            "fiscal_year": "2027",
            "period_start": "2026-10-01",
            "period_end": "2026-12-31",
        }
    )
    closure_path = tmp_path / "ratewall_tdcsim_cbo_route_stock_closure.csv"

    _write_tdcsim_cbo_route_stock_closure_table(closure_path, [closure_row])

    with closure_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == CBO_ROUTE_STOCK_CLOSURE_FIELDS
        assert list(reader) == [closure_row]

    coefficient_row = {
        field: "" for field in CBO_MATCHED_RESPONSE_COEFFICIENT_FIELDS
    }
    coefficient_row.update(
        {
            "tdcsim_cbo_matched_response_coefficient_row_id": (
                "tdcsim_cbo_matched_response_coefficient::2027::axis::outcome"
            ),
            "fiscal_year": "2027",
            "response_axis": "axis",
            "outcome_name": "outcome",
        }
    )
    coefficient_path = (
        tmp_path / "ratewall_tdcsim_cbo_matched_response_coefficient.csv"
    )

    _write_tdcsim_cbo_matched_response_coefficient_table(
        coefficient_path, [coefficient_row]
    )

    with coefficient_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == CBO_MATCHED_RESPONSE_COEFFICIENT_FIELDS
        assert list(reader) == [coefficient_row]

    period_response_row = {field: "" for field in CBO_MATCHED_PERIOD_RESPONSE_FIELDS}
    period_response_row.update(
        {
            "tdcsim_cbo_matched_period_response_row_id": (
                "tdcsim_cbo_matched_period_response::axis::outcome::2026-12-31"
            ),
            "response_axis": "axis",
            "outcome_name": "outcome",
            "period_end": "2026-12-31",
            "fiscal_year": "2027",
        }
    )
    period_response_path = tmp_path / "ratewall_tdcsim_cbo_matched_period_response.csv"

    _write_tdcsim_cbo_matched_period_response_table(
        period_response_path, [period_response_row]
    )

    with period_response_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == CBO_MATCHED_PERIOD_RESPONSE_FIELDS
        assert list(reader) == [period_response_row]

    lever_row = {field: "" for field in CBO_SCENARIO_LEVER_DIAGNOSTIC_FIELDS}
    lever_row.update(
        {
            "tdcsim_cbo_scenario_lever_diagnostic_row_id": (
                "tdcsim_cbo_scenario_lever_diagnostic::2027::scenario"
            ),
            "scenario_id": "scenario",
            "fiscal_year": "2027",
            "lever_name": "primary_deficit",
        }
    )
    lever_path = tmp_path / "ratewall_tdcsim_cbo_scenario_lever_diagnostic.csv"

    _write_tdcsim_cbo_scenario_lever_diagnostic_table(lever_path, [lever_row])

    with lever_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == CBO_SCENARIO_LEVER_DIAGNOSTIC_FIELDS
        assert list(reader) == [lever_row]
