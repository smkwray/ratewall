from __future__ import annotations

import csv
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.databook.marginal_public_interest import (
    MARGINAL_PUBLIC_INTEREST_DEBT_REPRICING_AUDIT_FIELDS,
    MARGINAL_PUBLIC_INTEREST_COMPONENT_FIELDS,
    MARGINAL_PUBLIC_INTEREST_DELTA_FIELDS,
    REQUIRED_COMPONENT_KEYS,
    MarginalPublicInterestError,
    marginal_public_interest_component_rows,
    marginal_public_interest_debt_repricing_audit_rows,
    marginal_public_interest_delta_rows,
    validate_marginal_public_interest_component_rows,
    validate_marginal_public_interest_debt_repricing_audit_rows,
    validate_marginal_public_interest_delta_rows,
    write_marginal_public_interest_outputs,
)


def test_public_interest_delta_staging_blocks_non_plus_100bp_forecast(tmp_path: Path) -> None:
    path = _write_forecast_fixture(tmp_path)

    rows = marginal_public_interest_delta_rows(forecast_public_interest_path=path)

    assert {field for row in rows for field in row} == set(
        MARGINAL_PUBLIC_INTEREST_DELTA_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    shock = by_scenario["rate_up_existing"]
    assert shock["delta_public_interest_net_block_bil"] == "2.5"
    assert shock["shock_path_id"] == (
        "diagnostic_existing_forecast_scenario_not_plus_100bp_year"
    )
    assert shock["selected_pi_delta_allowed"] == "false"
    assert "selected_marginal_n" in shock["blocked_use"]
    assert by_scenario["missing_plus_100bp_year_pair"]["selected_pi_delta_allowed"] == "false"


def test_current_plus100_public_interest_no_zero_placeholder(
    tmp_path: Path,
) -> None:
    component_input = _write_current_component_input_fixture(tmp_path)
    components = marginal_public_interest_component_rows(
        forecast_public_interest_path=_write_forecast_fixture(tmp_path),
        current_component_input_path=component_input,
        historical_component_input_path=None,
    )

    rows = marginal_public_interest_delta_rows(
        forecast_public_interest_path=_write_forecast_fixture(tmp_path),
        plus100_pair_input_path=None,
        current_component_input_path=component_input,
        historical_component_input_path=None,
        component_rows=components,
    )

    selected = [row for row in rows if row["selected_pi_delta_allowed"] == "true"]
    assert len(selected) == 1
    row = selected[0]
    assert row["period_object"] == "current"
    assert row["period"] == "2026"
    assert row["state_id"] == "current_state::2026"
    assert row["shock_path_id"] == "plus_100bp_year"
    assert row["source_mode"] == "assumption_mode"
    assert row["assumption_mode"] == "true"
    assert row["evidence_mode_enabled"] == "false"
    assert row["scenario_id"].endswith("_v2")
    assert row["delta_public_interest_net_block_bil"] != "0"
    assert row["public_interest_baseline_bil"] != row["public_interest_shock_bil"]
    assert {row["component_key"] for row in components} == set(REQUIRED_COMPONENT_KEYS)


def test_forecast_public_interest_operating_rate_delta_formula_reconciles(
    tmp_path: Path,
) -> None:
    rows = marginal_public_interest_delta_rows(
        forecast_public_interest_path=_write_full_forecast_fixture(tmp_path),
        plus100_pair_input_path=None,
        current_component_input_path=None,
        historical_component_input_path=None,
        debt_repricing_input_path=None,
    )

    selected = [row for row in rows if row["selected_pi_delta_allowed"] == "true"]
    assert len(selected) == 1
    row = selected[0]
    assert row["period_object"] == "forecast"
    assert row["state_id"] == "cbo_baseline_state::2036"
    assert row["scenario_id"] == (
        "cbo_baseline_plus_100bp_year_public_interest_assumption_v2"
    )
    assert row["same_state_delta_status"] == "pass_same_state_plus_100bp_year_delta"
    assert row["shock_path_id"] == "plus_100bp_year"
    assert row["source_mode"] == "assumption_mode"
    assert Decimal(row["delta_direct_treasury_current_demand_support_bil"]) == Decimal("4")
    assert Decimal(row["delta_bank_treasury_current_demand_support_bil"]) == Decimal("0.6")
    assert Decimal(row["public_interest_shock_bil"]) - Decimal(
        row["public_interest_baseline_bil"]
    ) == Decimal(row["delta_public_interest_net_block_bil"])


def test_zero_remittance_absorber_assumptions_preserve_selected_pi(
    tmp_path: Path,
) -> None:
    absorber = _write_remittance_absorber_fixture(tmp_path)
    base_components = marginal_public_interest_component_rows(
        forecast_public_interest_path=_write_full_forecast_fixture(tmp_path),
        current_component_input_path=_write_current_component_input_fixture(tmp_path),
        remittance_absorber_assumptions_path=None,
    )
    explicit_components = marginal_public_interest_component_rows(
        forecast_public_interest_path=_write_full_forecast_fixture(tmp_path),
        current_component_input_path=_write_current_component_input_fixture(tmp_path),
        remittance_absorber_assumptions_path=absorber,
    )

    def selected_sum(rows: list[dict[str, str]]) -> Decimal:
        summaries = marginal_public_interest_delta_rows(
            forecast_public_interest_path=_write_full_forecast_fixture(tmp_path),
            plus100_pair_input_path=None,
            current_component_input_path=_write_current_component_input_fixture(tmp_path),
            remittance_absorber_assumptions_path=absorber,
            component_rows=rows,
        )
        return sum(
            Decimal(row["delta_public_interest_net_block_bil"])
            for row in summaries
            if row["selected_pi_delta_allowed"] == "true"
        )

    assert selected_sum(explicit_components) == selected_sum(base_components)


def test_debt_repricing_audit_stays_audit_only_without_replacement_input(
    tmp_path: Path,
) -> None:
    components = marginal_public_interest_component_rows(
        forecast_public_interest_path=_write_full_forecast_fixture(tmp_path),
        current_component_input_path=_write_current_component_input_fixture(tmp_path),
    )

    rows = marginal_public_interest_debt_repricing_audit_rows(
        component_rows=components,
        debt_repricing_input_path=tmp_path / "missing.csv",
    )

    assert {field for row in rows for field in row} == set(
        MARGINAL_PUBLIC_INTEREST_DEBT_REPRICING_AUDIT_FIELDS
    )
    assert {row["replacement_recommended"] for row in rows} == {"false"}
    assert all("selected_public_interest_replacement" in row["blocked_use"] for row in rows)


def test_debt_repricing_audit_can_show_replacement_candidate(
    tmp_path: Path,
) -> None:
    components = marginal_public_interest_component_rows(
        forecast_public_interest_path=_write_full_forecast_fixture(tmp_path),
        current_component_input_path=None,
    )
    input_path = _write_debt_repricing_input_fixture(tmp_path)

    rows = marginal_public_interest_debt_repricing_audit_rows(
        component_rows=components,
        debt_repricing_input_path=input_path,
    )
    validate_marginal_public_interest_debt_repricing_audit_rows(rows)

    row = next(row for row in rows if row["period"] == "2036")
    assert row["replacement_recommended"] == "true"
    assert row["explicit_direct_treasury_delta_bil"] == "1.000000000000000000"
    assert row["explicit_bank_treasury_delta_bil"] == "0.100000000000000000"


def test_forecast_diagnostic_scenario_deltas_remain_nonselected(tmp_path: Path) -> None:
    rows = marginal_public_interest_delta_rows(
        forecast_public_interest_path=_write_full_forecast_fixture(tmp_path),
        plus100_pair_input_path=None,
        current_component_input_path=None,
    )

    diagnostic = [
        row
        for row in rows
        if row["shock_path_id"] == "diagnostic_existing_forecast_scenario_not_plus_100bp_year"
    ]
    assert diagnostic
    assert all(row["selected_pi_delta_allowed"] == "false" for row in diagnostic)


def test_selected_public_interest_requires_same_state_delta_status(tmp_path: Path) -> None:
    rows = marginal_public_interest_delta_rows(
        forecast_public_interest_path=_write_forecast_fixture(tmp_path),
        plus100_pair_input_path=None,
        current_component_input_path=_write_current_component_input_fixture(tmp_path),
    )
    bad = deepcopy(rows)
    selected = next(row for row in bad if row["selected_pi_delta_allowed"] == "true")
    selected["same_state_delta_status"] = "fail_closed_cross_state_delta"

    with pytest.raises(MarginalPublicInterestError, match="same-state"):
        validate_marginal_public_interest_delta_rows(bad)


def test_selected_public_interest_key_uniqueness(tmp_path: Path) -> None:
    rows = marginal_public_interest_delta_rows(
        forecast_public_interest_path=_write_forecast_fixture(tmp_path),
        plus100_pair_input_path=None,
        current_component_input_path=_write_current_component_input_fixture(tmp_path),
    )
    bad = deepcopy(rows)
    selected = next(row for row in bad if row["selected_pi_delta_allowed"] == "true")
    bad.append(deepcopy(selected))

    with pytest.raises(MarginalPublicInterestError, match="duplicate"):
        validate_marginal_public_interest_delta_rows(bad)


def test_selected_public_interest_rejects_old_current_benchmark_n(tmp_path: Path) -> None:
    rows = marginal_public_interest_delta_rows(
        forecast_public_interest_path=_write_forecast_fixture(tmp_path),
        plus100_pair_input_path=None,
        current_component_input_path=_write_current_component_input_fixture(tmp_path),
    )
    selected = next(row for row in rows if row["selected_pi_delta_allowed"] == "true")

    assert selected["public_interest_baseline_bil"] != "83.542224868775"
    assert "old_current_benchmark_n" in selected["blocked_use"]


def test_public_interest_outputs_are_written(tmp_path: Path) -> None:
    components = marginal_public_interest_component_rows(
        forecast_public_interest_path=_write_forecast_fixture(tmp_path),
        current_component_input_path=_write_current_component_input_fixture(tmp_path),
    )
    rows = marginal_public_interest_delta_rows(
        forecast_public_interest_path=_write_forecast_fixture(tmp_path),
        current_component_input_path=_write_current_component_input_fixture(tmp_path),
        component_rows=components,
    )
    outputs = write_marginal_public_interest_outputs(
        tmp_path / "out",
        delta_rows=rows,
        component_rows=components,
        debt_repricing_audit_rows=marginal_public_interest_debt_repricing_audit_rows(
            component_rows=components,
            debt_repricing_input_path=tmp_path / "missing.csv",
        ),
    )

    assert outputs["delta_csv"].read_text(encoding="utf-8").startswith(
        "marginal_public_interest_delta_row_id,"
    )
    assert outputs["component_csv"].read_text(encoding="utf-8").startswith(
        "marginal_public_interest_component_row_id,"
    )
    assert outputs["debt_repricing_audit_csv"].read_text(encoding="utf-8").startswith(
        "public_interest_debt_repricing_audit_row_id,"
    )


def test_bad_public_interest_row_rejects_selected_noncanonical_shock(tmp_path: Path) -> None:
    rows = marginal_public_interest_delta_rows(
        forecast_public_interest_path=_write_forecast_fixture(tmp_path),
        plus100_pair_input_path=None,
        current_component_input_path=None,
    )
    bad = deepcopy(rows)
    bad[0]["selected_pi_delta_allowed"] = "true"

    with pytest.raises(MarginalPublicInterestError, match="plus_100bp_year"):
        validate_marginal_public_interest_delta_rows(bad)


def test_public_interest_component_schema_complete(tmp_path: Path) -> None:
    components = marginal_public_interest_component_rows(
        forecast_public_interest_path=_write_full_forecast_fixture(tmp_path),
        current_component_input_path=_write_current_component_input_fixture(tmp_path),
    )

    assert {field for row in components for field in row} == set(
        MARGINAL_PUBLIC_INTEREST_COMPONENT_FIELDS
    )
    selected_keys = {
        (row["period_object"], row["period"], row["component_key"])
        for row in components
    }
    assert {
        ("current", "2026", key) for key in REQUIRED_COMPONENT_KEYS
    } <= selected_keys
    assert {
        ("forecast", "2036", key) for key in REQUIRED_COMPONENT_KEYS
    } <= selected_keys
    assert all(
        row["tdc_overlap_policy"] == "excluded_from_tdc_default"
        for row in components
        if row["component_key"]
        in {"direct_treasury_domestic_nonbank", "bank_treasury", "iorb_reserves", "on_rrp"}
    )


def test_bad_component_rejects_legacy_interest_addition(tmp_path: Path) -> None:
    components = marginal_public_interest_component_rows(
        forecast_public_interest_path=_write_full_forecast_fixture(tmp_path),
        current_component_input_path=None,
    )
    bad = deepcopy(components)
    legacy = next(
        row for row in bad if row["component_key"] == "legacy_interest_replacement_memo"
    )
    legacy["enters_selected_net_public_interest"] = "true"

    with pytest.raises(MarginalPublicInterestError, match="legacy"):
        validate_marginal_public_interest_component_rows(bad)


def _write_forecast_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "public_interest.csv"
    _write_csv(
        path,
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "baseline",
                "baseline_scenario_id": "baseline",
                "net_interest_after_fiscal_tga_offsets_bil": "10",
            },
            {
                "fiscal_year": "2036",
                "scenario_id": "rate_up_existing",
                "baseline_scenario_id": "baseline",
                "net_interest_after_fiscal_tga_offsets_bil": "12.5",
            },
        ],
    )
    return path


def _write_full_forecast_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "public_interest_full.csv"
    _write_csv(
        path,
        [
            {
                "fiscal_year": "2036",
                "scenario_id": "cbo_baseline_noop_v1",
                "baseline_scenario_id": "cbo_baseline_noop_v1",
                "net_interest_after_fiscal_tga_offsets_bil": "100",
                "direct_treasury_current_demand_support_bil": "11",
                "bank_treasury_current_demand_support_bil": "1.1",
                "legacy_interest_support_bil": "12.1",
                "projected_iorb_interest_basis_bil": "1000",
                "projected_iorb_current_demand_support_bil": "30",
                "projected_on_rrp_interest_basis_bil": "100",
                "projected_on_rrp_current_demand_support_bil": "2",
                "cbo_nominal_gdp_bil": "20000",
                "cbo_short_rate_pct": "4",
                "reserve_balance_stock_gdp_share": "1",
                "on_rrp_stock_gdp_share": "0.1",
                "iorb_rate_spread_vs_cbo_short_rate_pct": "1",
                "on_rrp_rate_spread_vs_cbo_short_rate_pct": "1",
                "gross_public_interest_current_demand_support_bil": "200",
                "interest_income_tax_timing_drag_bil": "20",
                "net_interest_before_fiscal_tga_offsets_bil": "180",
                "fiscal_offset_bil": "18",
                "tga_liquidity_offset_bil": "9",
            },
            {
                "fiscal_year": "2036",
                "scenario_id": "diagnostic_rate_up",
                "baseline_scenario_id": "cbo_baseline_noop_v1",
                "net_interest_after_fiscal_tga_offsets_bil": "101",
                "direct_treasury_current_demand_support_bil": "11.2",
                "bank_treasury_current_demand_support_bil": "1.2",
                "legacy_interest_support_bil": "12.4",
                "projected_iorb_interest_basis_bil": "1000",
                "projected_iorb_current_demand_support_bil": "30",
                "projected_on_rrp_interest_basis_bil": "100",
                "projected_on_rrp_current_demand_support_bil": "2",
                "cbo_nominal_gdp_bil": "20000",
                "cbo_short_rate_pct": "4",
                "reserve_balance_stock_gdp_share": "1",
                "on_rrp_stock_gdp_share": "0.1",
                "iorb_rate_spread_vs_cbo_short_rate_pct": "1",
                "on_rrp_rate_spread_vs_cbo_short_rate_pct": "1",
                "gross_public_interest_current_demand_support_bil": "200",
                "interest_income_tax_timing_drag_bil": "20",
                "net_interest_before_fiscal_tga_offsets_bil": "180",
                "fiscal_offset_bil": "18",
                "tga_liquidity_offset_bil": "9",
            },
            {
                "fiscal_year": "2036",
                "scenario_id": "tdcsim_rate_up_25bp_v1",
                "baseline_scenario_id": "cbo_baseline_noop_v1",
                "net_interest_after_fiscal_tga_offsets_bil": "101",
                "direct_treasury_current_demand_support_bil": "12",
                "bank_treasury_current_demand_support_bil": "1.3",
                "legacy_interest_support_bil": "13.3",
                "projected_iorb_interest_basis_bil": "1000",
                "projected_iorb_current_demand_support_bil": "30",
                "projected_on_rrp_interest_basis_bil": "100",
                "projected_on_rrp_current_demand_support_bil": "2",
                "cbo_nominal_gdp_bil": "20000",
                "cbo_short_rate_pct": "4",
                "reserve_balance_stock_gdp_share": "1",
                "on_rrp_stock_gdp_share": "0.1",
                "iorb_rate_spread_vs_cbo_short_rate_pct": "1",
                "on_rrp_rate_spread_vs_cbo_short_rate_pct": "1",
                "gross_public_interest_current_demand_support_bil": "200",
                "interest_income_tax_timing_drag_bil": "20",
                "net_interest_before_fiscal_tga_offsets_bil": "180",
                "fiscal_offset_bil": "18",
                "tga_liquidity_offset_bil": "9",
            },
            {
                "fiscal_year": "2036",
                "scenario_id": "tdcsim_rate_down_25bp_v1",
                "baseline_scenario_id": "cbo_baseline_noop_v1",
                "net_interest_after_fiscal_tga_offsets_bil": "99",
                "direct_treasury_current_demand_support_bil": "10",
                "bank_treasury_current_demand_support_bil": "1.0",
                "legacy_interest_support_bil": "11",
                "projected_iorb_interest_basis_bil": "1000",
                "projected_iorb_current_demand_support_bil": "30",
                "projected_on_rrp_interest_basis_bil": "100",
                "projected_on_rrp_current_demand_support_bil": "2",
                "cbo_nominal_gdp_bil": "20000",
                "cbo_short_rate_pct": "4",
                "reserve_balance_stock_gdp_share": "1",
                "on_rrp_stock_gdp_share": "0.1",
                "iorb_rate_spread_vs_cbo_short_rate_pct": "1",
                "on_rrp_rate_spread_vs_cbo_short_rate_pct": "1",
                "gross_public_interest_current_demand_support_bil": "200",
                "interest_income_tax_timing_drag_bil": "20",
                "net_interest_before_fiscal_tga_offsets_bil": "180",
                "fiscal_offset_bil": "18",
                "tga_liquidity_offset_bil": "9",
            },
        ],
    )
    return path


def _write_current_component_input_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "current_component_input.csv"
    _write_csv(
        path,
        [
            {
                "period_object": "current",
                "period": "2026",
                "horizon": "annual_h1_100bp_year",
                "state_id": "current_state::2026",
                "scenario_id": "current_plus_100bp_year_public_interest_assumption_v2",
                "baseline_scenario_id": "current_state_no_incremental_shock",
                "shock_scenario_id": "current_plus_100bp_year_public_interest_assumption_v2",
                "shock_path_id": "plus_100bp_year",
                "shock_bps_year": "100",
                "nominal_gdp_bil": "1000",
                "baseline_public_interest_support_bil": "56",
                "treasury_repricing_base_bil": "1000",
                "treasury_repricing_pass_through": "1",
                "domestic_nonbank_treasury_holder_share": "0.6",
                "bank_treasury_holder_share": "0.1",
                "foreign_treasury_holder_share": "0.3",
                "direct_treasury_current_demand_share": "0.1",
                "bank_treasury_current_demand_share": "0.1",
                "reserve_balance_stock_bil": "100",
                "iorb_pass_through_scale": "1",
                "iorb_recipient_current_demand_share": "0.03",
                "on_rrp_stock_bil": "10",
                "on_rrp_pass_through_scale": "1",
                "on_rrp_recipient_current_demand_share": "0.06",
                "remittance_capacity_bil": "0",
                "remittance_offset_share": "1",
                "current_remittance_demand_share": "0",
                "future_remittance_drag_current_demand_share": "0",
                "tax_timing_rate": "0.18",
                "fiscal_offset_rate": "0.08",
                "tga_liquidity_offset_rate": "0.05",
                "tdc_overlap_shield_bil": "0",
                "holder_split_basis": "test_current_holder_split",
                "source_mode": "assumption_mode",
                "assumption_mode": "true",
                "evidence_mode_enabled": "false",
                "selected_input_allowed": "true",
                "allowed_use": "test_current_component_input",
                "blocked_use": "canonical_headline_promotion_without_final_gate",
                "claim_boundary": "test_current_component_input",
            }
        ],
    )
    return path


def _write_remittance_absorber_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "remittance_absorber.csv"
    _write_csv(
        path,
        [
            {
                "period_object": "current",
                "period": "2026",
                "state_id": "current_state::2026",
                "current_remittance_demand_share": "0",
                "future_remittance_drag_current_demand_share": "0",
                "selected_remittance_absorber_assumption_allowed": "true",
                "selection_gate_status": "pass_zero_remittance_absorber_assumption",
            },
            {
                "period_object": "forecast",
                "period": "2036",
                "state_id": "cbo_baseline_state::2036",
                "current_remittance_demand_share": "0",
                "future_remittance_drag_current_demand_share": "0",
                "selected_remittance_absorber_assumption_allowed": "true",
                "selection_gate_status": "pass_zero_remittance_absorber_assumption",
            },
        ],
    )
    return path


def _write_debt_repricing_input_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "debt_repricing.csv"
    _write_csv(
        path,
        [
            {
                "period_object": "forecast",
                "period": "2036",
                "state_id": "cbo_baseline_state::2036",
                "shock_path_id": "plus_100bp_year",
                "marketable_debt_stock_bil": "1000",
                "repricing_share": "0.5",
                "floating_rate_share": "0",
                "domestic_nonbank_holder_share": "0.2",
                "bank_holder_share": "0.1",
                "foreign_holder_share": "0.7",
                "pass_through": "1",
                "direct_treasury_current_demand_share": "1",
                "bank_treasury_current_demand_share": "0.2",
                "selected_debt_repricing_replacement_allowed": "true",
                "selection_status": "pass_explicit_debt_repricing_replacement_candidate",
            }
        ],
    )
    return path


def _write_current_pair_input_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "current_pair_input.csv"
    _write_csv(
        path,
        [
            {
                "marginal_public_interest_delta_row_id": (
                    "public_interest_pair::current::2026::current_state::2026"
                ),
                "period_object": "current",
                "period": "2026",
                "horizon": "annual_h1_100bp_year",
                "state_id": "current_state::2026",
                "scenario_id": "current_plus_100bp_year_public_interest_assumption_v1",
                "baseline_scenario_id": "current_state_no_incremental_shock",
                "shock_scenario_id": (
                    "current_plus_100bp_year_public_interest_assumption_v1"
                ),
                "shock_path_id": "plus_100bp_year",
                "public_interest_pair_source_id": (
                    "current_observed_overlay_admission.public_interest_support_bil"
                ),
                "source_mode": "assumption_mode",
                "assumption_mode": "true",
                "evidence_mode_enabled": "false",
                "public_interest_baseline_bil": "56",
                "public_interest_shock_bil": "56",
                "delta_public_interest_net_block_bil": "0",
                "same_state_delta_status": "pass_same_state_plus_100bp_year_delta",
                "selected_pi_delta_allowed": "true",
                "selection_gate_status": (
                    "pass_selected_assumption_mode_plus_100bp_year_public_interest_delta"
                ),
                "allowed_use": "selected_marginal_public_interest_delta_assumption_mode",
                "blocked_use": (
                    "standalone_public_interest_level;old_current_benchmark_n;"
                    "selected_rw_m_without_full_n_and_d"
                ),
                "claim_boundary": (
                    "assumption_mode_current_public_interest_delta_zero_no_source_grade_"
                    "current_rate_basis"
                ),
            }
        ],
    )
    return path


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
