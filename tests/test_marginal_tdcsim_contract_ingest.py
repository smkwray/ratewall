from __future__ import annotations

import csv
import json
from copy import deepcopy
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from ratewall.databook.marginal_tdcsim_contract import (
    CLAIM_BOUNDARY,
    MARGINAL_TDC_STATE_COMPOSITION_AUDIT_FIELDS,
    MARGINAL_TDC_SUPPORT_PANEL_FIELDS,
    MARGINAL_TDCSIM_CONTRACT_INGEST_FIELDS,
    MarginalTDCSimContractError,
    ingest_marginal_tdcsim_pair,
    ingest_marginal_tdcsim_pairs,
    validate_marginal_tdc_support_panel,
    write_marginal_tdcsim_outputs,
)


def test_missing_tdcsim_pair_fails_closed(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=tmp_path / "missing")

    assert len(tables["ingest_rows"]) == 1
    assert tables["support_rows"] == []
    assert len(tables["state_composition_audit_rows"]) == 1
    row = tables["ingest_rows"][0]
    audit = tables["state_composition_audit_rows"][0]
    assert row["contract_ingest_status"] == (
        "fail_closed_missing_or_invalid_tdcsim_v0p4_marginal_pair"
    )
    assert audit["selected_tdc_admission_status"] == "fail_closed_no_selected_tdc_support"
    assert "tdcsim_v0p3_output" in row["blocked_use"]


def test_valid_tdcsim_pair_ingests_support_panel(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path)

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert {field for row in tables["ingest_rows"] for field in row} == set(
        MARGINAL_TDCSIM_CONTRACT_INGEST_FIELDS
    )
    assert {field for row in tables["support_rows"] for field in row} == set(
        MARGINAL_TDC_SUPPORT_PANEL_FIELDS
    )
    assert {
        field
        for row in tables["state_composition_audit_rows"]
        for field in row
    } == set(MARGINAL_TDC_STATE_COMPOSITION_AUDIT_FIELDS)
    ingest = tables["ingest_rows"][0]
    support = tables["support_rows"][0]
    assert ingest["contract_ingest_status"] == "pass_tdcsim_v0p4_marginal_pair_ingested"
    assert ingest["object_id"] == "RW_M_PLUS_100BP_YEAR"
    assert ingest["shock_path_id"] == "plus_100bp_year"
    assert support["shock_path_id"] == "plus_100bp_year"
    assert support["horizon"] == "annual_h1_100bp_year"
    assert support["state_manifest_status"] == "pass"
    assert support["tdc_amount_basis"] == "pre_beta_ex_overlap_delta"
    assert support["delta_tdc_ex_overlap_bil"] == "2"
    assert support["beta_times_chi"] == "0.2"
    assert support["marginal_tdc_support_bil"] == "0.0070143241875"
    assert "tdc_income_addendum_split_admissible" in support["support_formula"]
    assert support["enters_selected_rw_m"] == "true"
    audit = tables["state_composition_audit_rows"][0]
    assert audit["full_key_status"] == (
        "pass_full_marginal_tdc_key_present"
    )
    assert audit["selected_tdc_admission_status"] == "pass_split_income_addendum_admitted"


def test_tdcsim_mmf_debt_service_collision_parks_income_addendum() -> None:
    pair_components = Path(
        "var/preliminary_scenario_results/marginal_tdcsim/source_pairs/"
        "current_state_2026_plus_100bp_year_source_grade/"
        "tdcsim_ratewall_marginal_tdc_components.csv"
    )
    rwtam_interest = Path("var/rwtam/v1/out_government_interest_channel.csv")

    components = _read_csv(pair_components)
    mmf_debt_service = [
        row
        for row in components
        if row["component_family"] == "debt_service_interest"
        and row["holder_subsector"] == "mmf_cash_fund_route"
        and row["included_in_delta_tdc_ex_overlap"] == "True"
    ]
    by_component = {row["component_key"]: row for row in mmf_debt_service}

    assert {
        "bill_discount_interest_to_du_mmf",
        "fixed_coupon_interest_to_du_mmf",
        "frn_interest_to_du_mmf",
        "tips_coupon_interest_to_du_mmf",
    } == set(by_component)
    assert by_component["bill_discount_interest_to_du_mmf"]["payment_type"] == "bill_discount"
    assert by_component["bill_discount_interest_to_du_mmf"]["delta_amount_bil"] == (
        "1.7155374486231132"
    )
    assert by_component["fixed_coupon_interest_to_du_mmf"]["payment_type"] == "fixed_coupon"
    assert by_component["fixed_coupon_interest_to_du_mmf"]["delta_amount_bil"] == (
        "1.4264137925026574"
    )
    assert by_component["frn_interest_to_du_mmf"]["payment_type"] == "frn_interest"
    assert by_component["frn_interest_to_du_mmf"]["delta_amount_bil"] == "0.0"
    assert by_component["tips_coupon_interest_to_du_mmf"]["payment_type"] == "tips_coupon"
    assert by_component["tips_coupon_interest_to_du_mmf"]["delta_amount_bil"] == "0.0"

    direct_interest = _read_csv(rwtam_interest)
    rwtam_mmf = {
        row["instrument_family"]: row
        for row in direct_interest
        if row["year"] == "2026" and row["holder"] == "mmfs"
    }

    assert {"treasury_bills", "treasury_notes_bonds_tips"} <= set(rwtam_mmf)
    assert Decimal(rwtam_mmf["treasury_bills"]["cashflow_delta_bil"]) > 0
    assert Decimal(rwtam_mmf["treasury_notes_bonds_tips"]["cashflow_delta_bil"]) > 0
    assert Decimal(rwtam_mmf["treasury_bills"]["converted_net_bil"]) == Decimal(
        "3.269165154515898167414403335"
    )
    assert Decimal(rwtam_mmf["treasury_notes_bonds_tips"]["converted_net_bil"]) == Decimal(
        "0.03508584955161260792589390621"
    )


def test_pair_root_ingests_multiple_manifest_backed_pairs(tmp_path: Path) -> None:
    pair_root = tmp_path / "source_pairs"
    _write_pair(
        pair_root,
        pair_name="forecast_2035",
        pair_id="pair_2035",
        period="2035",
        state_id="forecast_state::2035",
    )
    _write_pair(
        pair_root,
        pair_name="forecast_2036",
        pair_id="pair_2036",
        period="2036",
        state_id="forecast_state::2036",
    )

    tables = ingest_marginal_tdcsim_pairs(pair_root=pair_root)

    assert len(tables["ingest_rows"]) == 2
    assert len(tables["support_rows"]) == 2
    assert len(tables["state_composition_audit_rows"]) == 2
    assert {row["period"] for row in tables["support_rows"]} == {"2035", "2036"}
    assert all(
        row["selected_tdc_formula_pass"] == "true"
        and row["enters_selected_rw_m"] == "true"
        for row in tables["support_rows"]
    )


def test_forecast_assumption_fixture_is_not_selected_without_source_grade(tmp_path: Path) -> None:
    pair_root = tmp_path / "source_pairs"
    _write_pair(
        pair_root,
        pair_name="forecast_2036_fixture",
        pair_id="ratewall_forecast_cbo_baseline_2036_plus100bp_year_assumption_pair_v1",
        period="2036",
        state_id="cbo_baseline_state::2036",
    )

    tables = ingest_marginal_tdcsim_pairs(pair_root=pair_root)

    assert len(tables["ingest_rows"]) == 1
    assert tables["support_rows"] == []
    assert "source-grade" in tables["ingest_rows"][0]["failure_reason"]


def test_forecast_source_grade_support_requires_rollforward_hashes(tmp_path: Path) -> None:
    pair_dir = _write_pair(
        tmp_path,
        pair_name="forecast_2036_source_grade",
        pair_id="ratewall_forecast_cbo_baseline_2036_plus100bp_year_source_grade_pair_v1",
        period="2036",
        state_id="cbo_baseline_state::2036",
    )
    _rewrite_source_grade_fields(pair_dir, derived_sha="")

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert tables["support_rows"] == []
    assert "derived_state_package_sha256" in tables["ingest_rows"][0]["failure_reason"]


def test_forecast_source_grade_support_is_admitted(tmp_path: Path) -> None:
    pair_dir = _write_pair(
        tmp_path,
        pair_name="forecast_2036_source_grade",
        pair_id="ratewall_forecast_cbo_baseline_2036_plus100bp_year_source_grade_pair_v1",
        period="2036",
        state_id="cbo_baseline_state::2036",
    )
    _rewrite_source_grade_fields(pair_dir)

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert len(tables["support_rows"]) == 1
    assert tables["support_rows"][0]["source_grade_status"] == "pass_forecast_rollforward_source_grade"


def test_pair_root_prefers_source_grade_duplicate_key(tmp_path: Path) -> None:
    pair_root = tmp_path / "source_pairs"
    assumption = _write_pair(
        pair_root,
        pair_name="current_assumption",
        pair_id="current_assumption_pair",
        period="2026",
        state_id="current_state::2026",
    )
    source_grade = _write_pair(
        pair_root,
        pair_name="current_source_grade",
        pair_id="current_source_grade_pair",
        period="2026",
        state_id="current_state::2026",
    )
    _rewrite_summary_delta(assumption, pair_id="current_assumption_pair", delta_ex="0")
    _rewrite_summary_delta(source_grade, pair_id="current_source_grade_pair", delta_ex="4")

    tables = ingest_marginal_tdcsim_pairs(pair_root=pair_root)

    assert len(tables["ingest_rows"]) == 2
    assert len(tables["support_rows"]) == 1
    support = tables["support_rows"][0]
    assert support["pair_id"] == "current_source_grade_pair"
    assert support["delta_tdc_ex_overlap_bil"] == "4"
    assert support["marginal_tdc_support_bil"] == "0.014028648375"


def test_tdcsim_outputs_are_written(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=_write_pair(tmp_path))
    outputs = write_marginal_tdcsim_outputs(
        tmp_path / "out",
        ingest_rows=tables["ingest_rows"],
        support_rows=tables["support_rows"],
        state_composition_audit_rows=tables["state_composition_audit_rows"],
    )

    assert outputs["contract_ingest_csv"].read_text(encoding="utf-8").startswith(
        "marginal_tdcsim_contract_ingest_row_id,"
    )
    assert outputs["support_panel_csv"].read_text(encoding="utf-8").startswith(
        "marginal_tdc_support_row_id,"
    )
    assert outputs["state_composition_audit_csv"].read_text(
        encoding="utf-8"
    ).startswith("marginal_tdc_state_composition_audit_row_id,")


def test_legacy_or_gross_tdc_summary_is_rejected(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path)
    summary_path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(summary_path)
    rows[0].pop("object_id")
    _write_csv(summary_path, rows)

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert tables["support_rows"] == []
    assert tables["ingest_rows"][0]["contract_ingest_status"].startswith("fail_closed")
    assert "missing summary fields" in tables["ingest_rows"][0]["failure_reason"]


def test_bad_support_panel_rejects_formula_drift(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=_write_pair(tmp_path))
    bad = deepcopy(tables["support_rows"])
    bad[0]["marginal_tdc_support_bil"] = "0.6"

    with pytest.raises(MarginalTDCSimContractError, match="split TDC N coefficient"):
        validate_marginal_tdc_support_panel(bad, allow_empty=False)


def test_split_tdc_support_rejects_selected_entry_flag_false(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=_write_pair(tmp_path))
    bad = deepcopy(tables["support_rows"])
    bad[0]["selected_tdc_formula_pass"] = "false"
    bad[0]["enters_selected_rw_m"] = "false"

    with pytest.raises(MarginalTDCSimContractError, match="split TDC addendum"):
        validate_marginal_tdc_support_panel(bad, allow_empty=False)


def test_ingest_requires_beta_schedule_row_when_schedule_is_supplied(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path, period="2036", state_id="forecast_state::2036")
    schedule = _write_beta_schedule(tmp_path, period="2035", state_id="forecast_state::2035")

    with localcontext() as context:
        context.prec = 28
        tables = ingest_marginal_tdcsim_pair(
            pair_dir=pair_dir,
            beta_schedule_path=schedule,
        )

    assert tables["support_rows"] == []
    assert "missing beta schedule row" in tables["ingest_rows"][0]["failure_reason"]


def test_ingest_rejects_beta_mismatch_against_schedule(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path, period="2036", state_id="forecast_state::2036")
    schedule = _write_beta_schedule(
        tmp_path,
        period="2036",
        state_id="forecast_state::2036",
        beta="0.6163494354563133",
        chi="0.07",
    )

    tables = ingest_marginal_tdcsim_pair(
        pair_dir=pair_dir,
        beta_schedule_path=schedule,
    )

    assert tables["support_rows"] == []
    assert "does not match RateWall beta schedule" in tables["ingest_rows"][0]["failure_reason"]


def test_ingest_accepts_beta_schedule_match_and_recomputes_support(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path, period="2036", state_id="forecast_state::2036")
    _rewrite_summary_beta(pair_dir, beta="0.6163494354563133", chi="0.07")
    schedule = _write_beta_schedule(
        tmp_path,
        period="2036",
        state_id="forecast_state::2036",
        beta="0.6163494354563133",
        chi="0.07",
    )

    tables = ingest_marginal_tdcsim_pair(
        pair_dir=pair_dir,
        beta_schedule_path=schedule,
    )

    support = tables["support_rows"][0]
    assert support["beta"] == "0.6163494354563133"
    assert support["chi"] == "0.07"
    assert support["beta_times_chi"] == "0.043144460481941931"
    assert support["marginal_tdc_support_bil"] == "0.0086465495061463769595358875"
    assert "tdc_income_addendum_split_admissible" in support["support_formula"]


def test_pre_beta_flooded_pair_recomputes_schedule_cases(tmp_path: Path) -> None:
    pair_dir = _write_pair(
        tmp_path,
        pair_id="flooded_state_2028_plus100bp_year_pair",
        period="2028",
        state_id="flooded_state::2028",
        state_kind="scenario_state",
        demand_conversion_case="pre_beta_pair",
        beta="1.0",
        chi="1.0",
        beta_source_status="not_applied_in_tdcsim_pair_artifact",
        chi_source_status="not_applied_in_tdcsim_pair_artifact",
        source_grade_status="pass_flooded_scenario_state_export",
        state_construction_method="scenario_rollforward_export_v1",
    )
    schedule = _write_beta_schedule(
        tmp_path,
        period="2028",
        state_id="flooded_state::2028",
        period_object="scenario_state",
        state_kind="scenario_state",
        demand_conversion_case="flooded_persistence_0q",
        beta="0.7",
        chi="0.07",
    )

    tables = ingest_marginal_tdcsim_pair(
        pair_dir=pair_dir,
        beta_schedule_path=schedule,
    )

    support = tables["support_rows"][0]
    assert support["demand_conversion_case"] == "flooded_persistence_0q"
    assert support["beta"] == "0.7"
    assert support["chi"] == "0.07"
    assert support["marginal_tdc_support_bil"] == "0.0098200538625"
    assert support["enters_selected_rw_m"] == "true"
    assert "legacy_chi_support" in support["blocked_use"]


def test_fiscal_injection_pair_is_ingested_but_blocked_from_selected_rw_m(tmp_path: Path) -> None:
    pair_dir = _write_pair(
        tmp_path,
        pair_id="fiscal_injection_2028_v1_pair",
        object_id="TDC_FISCAL_INJECTION_2028",
        shock_path_id="fiscal_injection_2028_v1",
        shock_bps_year="0",
        denominator_equivalence_key="tdc_fiscal_injection_2028_no_rate_shock_v1",
        require_same_non_rate_compiled_inputs=False,
        one_named_rate_shock_only=False,
        period="2028",
        state_id="flooded_state::2028",
        state_kind="scenario_state",
        demand_conversion_case="pre_beta_pair",
        beta="1.0",
        chi="1.0",
        beta_source_status="not_applied_in_tdcsim_pair_artifact",
        chi_source_status="not_applied_in_tdcsim_pair_artifact",
        rate_shock_only_status="pass_fiscal_injection_no_rate_shock",
        source_grade_status="pass_flooded_scenario_state_export",
        state_construction_method="scenario_rollforward_export_v1",
    )
    schedule = _write_beta_schedule(
        tmp_path,
        period="2028",
        state_id="flooded_state::2028",
        object_id="TDC_FISCAL_INJECTION_2028",
        shock_path_id="fiscal_injection_2028_v1",
        shock_bps_year="0",
        period_object="scenario_state",
        state_kind="scenario_state",
        demand_conversion_case="flooded_persistence_0q",
        beta="0.7",
        chi="0.07",
    )

    tables = ingest_marginal_tdcsim_pair(
        pair_dir=pair_dir,
        beta_schedule_path=schedule,
    )

    ingest = tables["ingest_rows"][0]
    support = tables["support_rows"][0]
    assert ingest["object_id"] == "TDC_FISCAL_INJECTION_2028"
    assert ingest["shock_path_id"] == "fiscal_injection_2028_v1"
    assert "selected_rw_m" in ingest["blocked_use"]
    assert support["object_id"] == "TDC_FISCAL_INJECTION_2028"
    assert support["marginal_tdc_support_bil"] == "0"
    assert support["enters_selected_rw_m"] == "false"


def test_fiscal_injection_held_beta_support_uses_full_precision_anchor(
    tmp_path: Path,
) -> None:
    with localcontext() as context:
        context.prec = 200
        pair_dir = _write_pair(
            tmp_path,
            pair_id="fiscal_injection_2028_v1_pair",
            object_id="TDC_FISCAL_INJECTION_2028",
            shock_path_id="fiscal_injection_2028_v1",
            shock_bps_year="0",
            denominator_equivalence_key="tdc_fiscal_injection_2028_no_rate_shock_v1",
            require_same_non_rate_compiled_inputs=False,
            one_named_rate_shock_only=False,
            period="2028",
            state_id="flooded_state::2028",
            state_kind="scenario_state",
            demand_conversion_case="pre_beta_pair",
            beta="1.0",
            chi="1.0",
            beta_source_status="not_applied_in_tdcsim_pair_artifact",
            chi_source_status="not_applied_in_tdcsim_pair_artifact",
            rate_shock_only_status="pass_fiscal_injection_no_rate_shock",
            source_grade_status="pass_flooded_scenario_state_export",
            state_construction_method="scenario_rollforward_export_v1",
        )
        _rewrite_summary_delta_with_identity(
            pair_dir,
            pair_id="fiscal_injection_2028_v1_pair",
            delta_ex="1499.8215831399216",
        )
        schedule = _write_beta_schedule(
            tmp_path,
            period="2028",
            state_id="flooded_state::2028",
            object_id="TDC_FISCAL_INJECTION_2028",
            shock_path_id="fiscal_injection_2028_v1",
            shock_bps_year="0",
            period_object="scenario_state",
            state_kind="scenario_state",
            demand_conversion_case="held_standard_anchor",
            beta="0.5307509589554447",
            chi="0.07",
        )

        tables = ingest_marginal_tdcsim_pair(
            pair_dir=pair_dir,
            beta_schedule_path=schedule,
        )

    support = tables["support_rows"][0]
    assert support["demand_conversion_case"] == "held_standard_anchor"
    assert support["delta_tdc_ex_overlap_bil"] == "1499.8215831399216"
    assert support["beta"] == "0.5307509589554447"
    assert support["chi"] == "0.07"
    assert support["marginal_tdc_support_bil"] == "0"
    assert (
        "diagnostic_chi_support_bil=55.7222220459510633861078175794864"
        in support["allowed_use"]
    )
    assert support["enters_selected_rw_m"] == "false"


def test_bad_support_panel_rejects_duplicate_full_key(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=_write_pair(tmp_path))
    bad = deepcopy(tables["support_rows"])
    bad.append(deepcopy(bad[0]))

    with pytest.raises(MarginalTDCSimContractError, match="duplicate"):
        validate_marginal_tdc_support_panel(bad, allow_empty=False)


def test_tdcsim_summary_requires_state_manifest_fields(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path)
    summary_path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(summary_path)
    rows[0].pop("state_fingerprint_sha256")
    _write_csv(summary_path, rows)

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert tables["support_rows"] == []
    assert "state_fingerprint_sha256" in tables["ingest_rows"][0]["failure_reason"]


def _write_pair(
    tmp_path: Path,
    *,
    pair_name: str = "pair",
    pair_id: str = "pair_001",
    object_id: str = "RW_M_PLUS_100BP_YEAR",
    shock_path_id: str = "plus_100bp_year",
    shock_bps_year: str = "100",
    denominator_equivalence_key: str = "ratewall_D_conv_plus_100bp_year_v1",
    require_same_non_rate_compiled_inputs: bool = True,
    one_named_rate_shock_only: bool = True,
    period: str = "2036",
    state_id: str = "forecast_state::2036",
    state_kind: str = "forecast_state",
    demand_conversion_case: str = "central",
    beta: str = "0.5",
    chi: str = "0.4",
    beta_source_status: str = "fixture",
    chi_source_status: str = "fixture",
    rate_shock_only_status: str = "pass",
    source_grade_status: str = "",
    state_construction_method: str = "",
) -> Path:
    pair_dir = tmp_path / pair_name
    pair_dir.mkdir(parents=True)
    manifest = {
        "schema_version": "tdcsim_cbo_marginal_tdc_manifest_v1",
        "pair_id": pair_id,
        "generated_at_utc": "2026-06-30T00:00:00Z",
        "pair_spec": {
            "schema_version": "tdcsim_cbo_marginal_tdc_pair_v1",
            "object_id": object_id,
            "shock_path_id": shock_path_id,
            "shock_bps_year": int(shock_bps_year),
            "denominator_equivalence_key": denominator_equivalence_key,
            "require_same_baseline_hashes": True,
            "require_same_opening_state": True,
            "require_same_actuals_available_as_of": True,
            "require_same_simulation_dates": True,
            "require_same_period_index": True,
            "require_same_non_rate_compiled_inputs": require_same_non_rate_compiled_inputs,
            "one_named_rate_shock_only": one_named_rate_shock_only,
        },
        "baseline_run": {},
        "shock_run": {},
        "validation": {"status": "pass"},
        "files": {},
        "claim_boundary": CLAIM_BOUNDARY,
        "pair_manifest_config_sha256": "0" * 64,
    }
    (pair_dir / "tdcsim_ratewall_marginal_tdc_pair_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    _write_csv(
        pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv",
        [
            {
                "schema_version": "tdcsim_cbo_marginal_tdc_pair_v1",
                "contract_version": "0.4.0",
                "pair_id": pair_id,
                "object_id": object_id,
                "shock_path_id": shock_path_id,
                "shock_bps_year": shock_bps_year,
                "state_id": state_id,
                "state_kind": state_kind,
                "state_period": period,
                "scenario_id": "forecast_scenario::baseline",
                "scenario_state_set_id": "forecast_state_set::baseline",
                "state_fingerprint_sha256": "a" * 64,
                "state_component_inventory_sha256": "b" * 64,
                "period": period,
                "period_start": f"{period}-01-01",
                "period_end": f"{period}-12-31",
                "horizon": "annual_h1_100bp_year",
                "demand_conversion_case": demand_conversion_case,
                "baseline_run_id": "baseline",
                "shock_run_id": "shock",
                "tdc_change_baseline_bil": "10",
                "tdc_change_shock_bil": "13",
                "delta_tdc_change_bil": "3",
                "overlap_baseline_bil": "1",
                "overlap_shock_bil": "2",
                "delta_overlap_bil": "1",
                "tdc_change_ex_overlap_baseline_bil": "9",
                "tdc_change_ex_overlap_shock_bil": "11",
                "delta_tdc_ex_overlap_bil": "2",
                "tdc_deposit_creation_split_schema_version": "tdc_deposit_creation_split_v1",
                "delta_tdc_ex_overlap_interest_driven_excluded_bil": "0.5",
                "delta_tdc_ex_overlap_non_interest_admissible_bil": "1.5",
                "delta_tdc_ex_overlap_split_remainder_bil": "0",
                "delta_tdc_ex_overlap_reconciled_bil": "2.0",
                "tdc_materialized_deposit_stock_admissible_bil": str(
                    Decimal("1.5") * Decimal(beta)
                ),
                "tdc_materialized_deposit_stock_interest_excluded_bil": str(
                    Decimal("0.5") * Decimal(beta)
                ),
                "tdc_income_addendum_full_level_rate": "0.035",
                "tdc_income_addendum_gross_interest_bil": str(
                    Decimal("1.5") * Decimal(beta) * Decimal("0.035")
                ),
                "tdc_income_addendum_route_family": "tdc_income_from_tdcsim_marginal_deposit_stock",
                "tdc_income_addendum_admission_status": "admitted_split_non_interest_bucket",
                "tdc_income_addendum_collision_status": "pass_split_collision_excluded",
                "selected_support_formula": "admissible × β × rate × sfc_route_coefficients",
                "beta_assumption_id": "beta_fixture",
                "beta": beta,
                "beta_source_status": beta_source_status,
                "chi_assumption_id": "chi_fixture",
                "chi": chi,
                "chi_source_status": chi_source_status,
                "beta_times_chi": str(Decimal(beta) * Decimal(chi)),
                "tdc_amount_basis": "pre_beta_ex_overlap_delta",
                "support_formula": "delta_tdc_ex_overlap_bil * beta * chi",
                "overlap_scope": "tdcsim_and_external_support",
                "marginal_tdc_support_bil": str(Decimal("2") * Decimal(beta) * Decimal(chi)),
                "same_state_status": "pass",
                "rate_shock_only_status": rate_shock_only_status,
                "shock_path_validation_status": "pass",
                "period_alignment_status": "pass",
                "overlap_identity_status": "pass",
                "component_identity_status": "pass",
                "route_identity_status": "pass",
                "support_identity_status": "pass",
                "state_manifest_status": "pass",
                "contract_ingest_status": "ready_for_ratewall_assumption_mode_ingest",
                "failure_reason": "",
                "assumption_mode": "true",
                "evidence_mode_enabled": "false",
                "raw_rate_shock_enabled": "false",
                "named_marginal_shock_path_enabled": "true",
                "tdcsim_channel_classifier_enabled": "false",
                "enters_main_ratio_candidate": "true",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
                "source_vintage": "2026-02-11" if source_grade_status else "",
                "source_grade_status": source_grade_status,
                "state_construction_method": state_construction_method,
                "forecast_state_export_manifest_sha256": "c" * 64 if source_grade_status else "",
                "derived_state_package_sha256": "d" * 64 if source_grade_status else "",
                "parent_baseline_package_sha256": "e" * 64 if source_grade_status else "",
                "rollforward_run_manifest_sha256": "f" * 64 if source_grade_status else "",
                "compiled_non_rate_inputs_digest": "1" * 64 if source_grade_status else "",
            }
        ],
    )
    return pair_dir


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _rewrite_summary_delta(pair_dir: Path, *, pair_id: str, delta_ex: str) -> None:
    path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(path)
    row = rows[0]
    row["pair_id"] = pair_id
    row["tdc_change_baseline_bil"] = "0"
    row["tdc_change_shock_bil"] = delta_ex
    row["delta_tdc_change_bil"] = delta_ex
    row["overlap_baseline_bil"] = "0"
    row["overlap_shock_bil"] = "0"
    row["delta_overlap_bil"] = "0"
    row["tdc_change_ex_overlap_baseline_bil"] = "0"
    row["tdc_change_ex_overlap_shock_bil"] = delta_ex
    row["delta_tdc_ex_overlap_bil"] = delta_ex
    row["marginal_tdc_support_bil"] = str(float(delta_ex) * 0.2).rstrip("0").rstrip(".")
    _sync_split_fields(row)
    _write_csv(path, rows)


def _rewrite_summary_delta_with_identity(
    pair_dir: Path,
    *,
    pair_id: str,
    delta_ex: str,
) -> None:
    path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(path)
    row = rows[0]
    row["pair_id"] = pair_id
    row["tdc_change_baseline_bil"] = "0"
    row["tdc_change_shock_bil"] = delta_ex
    row["delta_tdc_change_bil"] = delta_ex
    row["overlap_baseline_bil"] = "0"
    row["overlap_shock_bil"] = "0"
    row["delta_overlap_bil"] = "0"
    row["tdc_change_ex_overlap_baseline_bil"] = "0"
    row["tdc_change_ex_overlap_shock_bil"] = delta_ex
    row["delta_tdc_ex_overlap_bil"] = delta_ex
    row["marginal_tdc_support_bil"] = str(
        Decimal(delta_ex) * Decimal(row["beta"]) * Decimal(row["chi"])
    )
    _sync_split_fields(row)
    _write_csv(path, rows)


def _rewrite_source_grade_fields(pair_dir: Path, *, derived_sha: str | None = None) -> None:
    path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(path)
    row = rows[0]
    row["source_vintage"] = "2026-02-11"
    row["source_grade_status"] = "pass_forecast_rollforward_source_grade"
    row["state_construction_method"] = "baseline_rollforward_export_v1"
    row["forecast_state_export_manifest_sha256"] = "c" * 64
    row["derived_state_package_sha256"] = "d" * 64 if derived_sha is None else derived_sha
    row["parent_baseline_package_sha256"] = "e" * 64
    row["rollforward_run_manifest_sha256"] = "f" * 64
    row["compiled_non_rate_inputs_digest"] = "1" * 64
    _write_csv(path, rows)


def _rewrite_summary_beta(pair_dir: Path, *, beta: str, chi: str) -> None:
    path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(path)
    row = rows[0]
    row["beta_assumption_id"] = "beta_ea_tdc_h0_matched_total_deposits_anchor_v1"
    row["beta"] = beta
    row["beta_source_status"] = "source_grade_ea_tdc_anchor"
    row["chi_assumption_id"] = "chi_ratewall_default_20260630"
    row["chi"] = chi
    row["chi_source_status"] = "assumption_mode"
    row["beta_times_chi"] = "0.043144460481941931"
    row["marginal_tdc_support_bil"] = "0.086288920963883862"
    _sync_split_fields(row)
    _write_csv(path, rows)


def _sync_split_fields(row: dict[str, str]) -> None:
    delta_ex = Decimal(row["delta_tdc_ex_overlap_bil"])
    beta = Decimal(row["beta"])
    admitted = delta_ex * Decimal("0.75")
    excluded = delta_ex - admitted
    rate = Decimal(row.get("tdc_income_addendum_full_level_rate") or "0.035")
    row["tdc_deposit_creation_split_schema_version"] = "tdc_deposit_creation_split_v1"
    row["delta_tdc_ex_overlap_interest_driven_excluded_bil"] = str(excluded)
    row["delta_tdc_ex_overlap_non_interest_admissible_bil"] = str(admitted)
    row["delta_tdc_ex_overlap_split_remainder_bil"] = "0"
    row["delta_tdc_ex_overlap_reconciled_bil"] = str(delta_ex)
    row["tdc_materialized_deposit_stock_admissible_bil"] = str(admitted * beta)
    row["tdc_materialized_deposit_stock_interest_excluded_bil"] = str(excluded * beta)
    row["tdc_income_addendum_full_level_rate"] = str(rate)
    row["tdc_income_addendum_gross_interest_bil"] = str(admitted * beta * rate)
    row["tdc_income_addendum_route_family"] = "tdc_income_from_tdcsim_marginal_deposit_stock"
    row["tdc_income_addendum_admission_status"] = "admitted_split_non_interest_bucket"
    row["tdc_income_addendum_collision_status"] = "pass_split_collision_excluded"
    row["selected_support_formula"] = "admissible × β × rate × sfc_route_coefficients"


def _write_beta_schedule(
    tmp_path: Path,
    *,
    period: str,
    state_id: str,
    object_id: str = "RW_M_PLUS_100BP_YEAR",
    shock_path_id: str = "plus_100bp_year",
    shock_bps_year: str = "100",
    period_object: str = "forecast",
    state_kind: str = "forecast_state",
    demand_conversion_case: str = "central",
    beta: str = "0.5",
    chi: str = "0.4",
) -> Path:
    path = tmp_path / "ratewall_marginal_tdc_beta_schedule.csv"
    row = {
        "beta_schedule_row_id": f"marginal_tdc_beta::{period_object}::{period}::{state_id}::{demand_conversion_case}",
        "object_id": object_id,
        "period_object": period_object,
        "period": period,
        "state_id": state_id,
        "state_kind": state_kind,
        "horizon": "annual_h1_100bp_year",
        "shock_path_id": shock_path_id,
        "shock_bps_year": shock_bps_year,
        "demand_conversion_case": demand_conversion_case,
        "beta_assumption_id": "beta_ea_tdc_h0_matched_total_deposits_anchor_v1",
        "beta_selected": beta,
        "beta_low": "0.34201759129420367",
        "beta_high": "0.729969",
        "beta_legacy_scaffold": "0.34201759129420367",
        "beta_source_artifact": "ea-tdc/output/models/paper_tier2_selected_credit_rate_lags_estimates.csv",
        "beta_source_field": "normalized_beta",
        "beta_source_sample_start": "2002Q1",
        "beta_source_sample_end": "2025Q4",
        "beta_method": "ea_tdc_h0_matched_total_deposits_source_anchor",
        "beta_projection_method": "flat_carry_forward_from_2025Q4",
        "beta_source_status": "source_grade_ea_tdc_anchor",
        "beta_selection_status": "selected_source_grade_ea_tdc_anchor_flat_forecast",
        "time_varying_proxy_available": "false",
        "time_varying_proxy_central": "",
        "time_varying_proxy_low": "",
        "time_varying_proxy_high": "",
        "time_varying_proxy_source_artifact": "",
        "chi_assumption_id": "chi_ratewall_default_20260630",
        "chi_selected": chi,
        "chi_low": "0.03",
        "chi_high": "0.12",
        "chi_source_status": "assumption_mode",
        "beta_times_chi_selected": str(Decimal(beta) * Decimal(chi)),
        "claim_boundary": "selected_tdc_beta_is_ea_tdc_anchor_not_time_varying_proxy_or_legacy_scaffold",
        "assumption_caveat": "",
    }
    _write_csv(path, [row])
    return path
