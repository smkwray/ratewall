from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pytest

from ratewall.rwtam.rwpi import (
    build_rwpi,
    validate_firm_interest_allocation,
    write_rwpi_outputs,
)
from ratewall.rwtam.rwpi_validation import build_rwpi_plug_validation
from ratewall.rwtam.v1 import build_v1


PACK_DIR = Path("configs/rwtam/packs")
pytestmark = pytest.mark.audit_fast


@lru_cache(maxsize=1)
def _rwpi_result():
    return build_rwpi(PACK_DIR)


def test_rwpi_emits_path_windows_and_preserves_scenario_fence(tmp_path: Path) -> None:
    result = _rwpi_result()
    checks = {row["check_id"]: row["status"] for row in result.rows("out_rwpi_invariant_check")}

    assert set(checks.values()) == {"pass"}
    assert checks["RWPI5_scenario_only_no_rw_full_mutation"] == "pass"

    windows = result.rows("out_rwpi_window_path")
    assert {row["horizon_window"] for row in windows} == {
        "0_12m",
        "13_24m",
        "25_36m",
        "0_36m_cumulative_sum_pp",
        "0_36m_cumulative_average",
    }
    assert {row["dose_mode"] for row in windows} == {"persistent_level", "transient_12m"}
    assert {row["index_target"] for row in windows} == {"CPI_U", "PCE"}
    assert all(row["headline_status"] == "scenario_diagnostic_only_not_RW_full" for row in windows)
    assert all("demand_only_after_wall_base_pp" in row for row in windows)
    assert all("fx_import_base_pp" in row for row in windows)
    assert all("cost_channel_base_pp" in row for row in windows)

    base = {
        row["horizon_window"]: row
        for row in windows
        if row["dose_mode"] == "persistent_level"
        and row["index_target"] == "CPI_U"
        and row["slack_state"] == "balanced"
    }
    assert base["25_36m"]["base_verdict"] == "no_kernel_mass_after_lag_window"
    assert abs(
        Decimal(base["0_36m_cumulative_sum_pp"]["ND_pi_base_pp"]) / Decimal("3")
        - Decimal(base["0_36m_cumulative_average"]["ND_pi_base_pp"])
    ) <= Decimal("1e-24")
    assert Decimal(base["0_12m"]["demand_only_after_wall_base_pp"]).quantize(
        Decimal("0.0001")
    ) == Decimal("0.0254")

    paths = write_rwpi_outputs(result, tmp_path)
    assert paths["out_rwpi_window_path"].exists()
    assert paths["out_rwpi_pce_crosswalk"].exists()


def test_rwpi_attribution_sums_exactly_with_residual_row() -> None:
    result = _rwpi_result()
    residuals = [
        row
        for row in result.rows("out_rwpi_channel_attribution")
        if row["channel_id"] == "RESIDUAL_EXACT_SUM_CHECK"
    ]

    assert residuals
    for row in residuals:
        assert Decimal(row["contribution_low_pp"]) == Decimal("0")
        assert Decimal(row["contribution_base_pp"]) == Decimal("0")
        assert Decimal(row["contribution_high_pp"]) == Decimal("0")
    disclosures = [
        row
        for row in result.rows("out_rwpi_channel_attribution")
        if row["channel_id"] == "demand_only_after_wall"
    ]
    assert disclosures
    assert {row["row_role"] for row in disclosures} == {"disclosure"}


def test_rwpi_allocation_vector_uses_real_rows_and_rejects_bad_probe() -> None:
    result = _rwpi_result()
    allocation = result.rows("out_rwpi_allocation_vector")
    v1 = build_v1(PACK_DIR)

    assert not validate_firm_interest_allocation(allocation, v1)
    assert any(row["rule_id"] == "corporate_bonds_interest" and row["allocated_to_price_cost"] == "0" for row in allocation)
    assert any(row["rule_id"] == "mortgages_arm_interest" and row["allocated_to_price_cost"] == "0" for row in allocation)

    bad = dict(next(row for row in allocation if row["rule_id"] == "c_and_i_depository_loans_interest"))
    bad["allocated_to_price_cost"] = "0.6"
    bad["allocated_to_quantity_demand_drag"] = "0.6"
    bad["allocated_to_margin_absorption"] = "0"
    bad["allocated_to_tax_or_other"] = "0"
    bad["unallocated_absent_with_reason"] = "0"

    errors = validate_firm_interest_allocation([bad], v1)
    assert any("exceeds 1" in error for error in errors)


def test_rwpi_rent_companion_and_exclusions_are_not_headline_summed() -> None:
    result = _rwpi_result()
    rent = result.rows("out_rwpi_rent_companion_path")
    exclusions = {row["channel_id"]: row for row in result.rows("out_rwpi_exclusion_rows")}

    assert rent
    assert {row["include_flag"] for row in rent} == {"0"}
    assert {row["absent_reason"] for row in rent} == {"starts_to_rent_elasticity_absent_with_reason"}
    assert exclusions["DIRECT_MORTGAGE_INTEREST_CPI"]["disposition"] == "rejected"
    assert exclusions["INTEREST_INCOME_SPENDING"]["disposition"] == "demand_wall_only"


def test_rwpi_validation_scaffold_is_scored_from_observed_series() -> None:
    result = _rwpi_result()
    scaffold = result.rows("out_rwpi_validation_scaffold")

    assert {row["run_id"] for row in scaffold} == {"mechanism_predicted", "intermediate_plug"}
    assert not any("needs_observed_series" in row["inputs_status"] for row in scaffold)
    assert any("observed_series_loaded_and_scored" in row["inputs_status"] for row in scaffold)


@pytest.mark.parametrize(
    "diagnostic",
    [
        "Demand-only M5 vs activity",
        "FX/import leg",
        "Cost channel",
        "Shelter lag kernel",
        "Starts-to-rents pressure",
        "Net price traction path",
    ],
)
def test_rwpi_plug_validation_recomputes_each_diagnostic(diagnostic: str) -> None:
    result = _rwpi_result()
    recomputed = build_rwpi_plug_validation(
        result.rows("out_rwpi_monthly_channel_path"),
        result.rows("out_rwpi_window_path"),
    )
    emitted = {
        row["diagnostic"]: row
        for row in result.rows("out_rwpi_plug_validation")
    }
    expected = {row["diagnostic"]: row for row in recomputed.scores}

    assert emitted[diagnostic] == expected[diagnostic]
    assert emitted[diagnostic]["run_id"] == "intermediate_plug"
    assert "no_fitting_guard" in emitted[diagnostic]["no_fitting_guard"]


def test_rwpi_plug_validation_honors_caveats_and_dispositions() -> None:
    result = _rwpi_result()
    scores = {
        row["diagnostic"]: row
        for row in result.rows("out_rwpi_plug_validation")
    }
    series = result.rows("out_rwpi_plug_validation_series")

    assert scores["Shelter lag kernel"]["kernel_status"] == "kernel_survives_timing_sign_not_level"
    assert "CPI_components_rebased" in scores["Shelter lag kernel"]["guardrail_status"]
    assert "ZORI_proxy_for_new_tenant_index" in scores["Shelter lag kernel"]["guardrail_status"]
    assert scores["Starts-to-rents pressure"]["kernel_status"] == "kernel_stays_underidentified"
    assert "RRVRUSQ156N_quarterly" in scores["Starts-to-rents pressure"]["guardrail_status"]
    assert scores["Cost channel"]["kernel_status"] in {
        "kernel_survives_weak_validation_only",
        "kernel_refuted_needs_redesign",
    }
    assert any(row["unit"] == "rebased_index" for row in series)
    assert any(row["unit"] == "quarterly_pp" for row in series)


def test_rwpi_pce_crosswalk_uses_labeled_factor_chain_and_reproduces_pack_check() -> None:
    result = _rwpi_result()
    factors = {row["factor_id"]: row for row in result.rows("out_rwpi_pce_factor_table")}
    ratios = {
        (row["horizon"], row["band"]): row
        for row in result.rows("out_rwpi_pce_ratio_crosswalk")
    }
    caves = {row["caveat_id"]: row["verdict_condensed"] for row in result.rows("out_rwpi_pce_caveat_rows")}

    assert factors["m_D_import_leakage_composition_weighted"]["base"] == "0.09"
    assert factors["m_D_import_leakage_composition_weighted"]["grade"] == "assumption"
    assert factors["m_N_import_leakage_consumption_only"]["base"] == "0.13"
    assert factors["m_N_import_leakage_consumption_only"]["grade"] == "B"
    assert factors["cpi_to_pce_slope_wedge"]["base"] == "0.88"
    assert factors["cpi_to_pce_slope_wedge"]["grade"] == "ASSUMPTION_no_published_counterpart"
    assert factors["fx_channel_pce_factor"]["base"] == "0.85"
    assert factors["fx_channel_pce_factor"]["grade"] == "assumption_to_fetch"
    assert "to_fetch" in factors["fx_channel_pce_factor"]["caveat"]

    base_year = ratios[("year_1", "base")]
    expected = (
        Decimal(base_year["source_RW_ratio_CPI_basis"])
        * (Decimal("1") - Decimal(base_year["m_N"]))
        / (Decimal("1") - Decimal(base_year["m_D"]))
    )
    assert Decimal(base_year["RW_pi_PCE_ratio_basis"]) == expected
    assert Decimal(base_year["RW_pi_PCE_ratio_basis"]).quantize(Decimal("0.001")) == Decimal("0.048")
    assert base_year["pack_check_against"] == "approx_0.048_year1_at_central_factors"

    assert caves["fed_target_claims"] == "Fed-target claims supportable only in hedged path-and-state-labeled form."
    assert caves["level_uncertainty"] == "Level uncertainty about 4x, dominated by the slope band, not the wall."
    assert caves["shelter_divergence"] == "Shelter divergence sits in the companion path."
    assert caves["scalar_claim_fence"] == "No final-basis-point scalar claim surface emitted."


def test_rwpi_pce_level_path_applies_wedge_to_demand_leg_not_only_fx() -> None:
    result = _rwpi_result()
    level = result.rows("out_rwpi_pce_level_path")
    windows = result.rows("out_rwpi_window_path")
    pce = next(
        row
        for row in level
        if row["dose_mode"] == "persistent_level"
        and row["slack_state"] == "balanced"
        and row["horizon_window"] == "0_36m_cumulative_sum_pp"
        and row["band"] == "base"
    )
    cpi_window = next(
        row
        for row in windows
        if row["dose_mode"] == "persistent_level"
        and row["index_target"] == "CPI_U"
        and row["slack_state"] == "balanced"
        and row["horizon_window"] == "0_36m_cumulative_sum_pp"
    )
    pce_window = next(
        row
        for row in windows
        if row["dose_mode"] == "persistent_level"
        and row["index_target"] == "PCE"
        and row["slack_state"] == "balanced"
        and row["horizon_window"] == "0_36m_cumulative_sum_pp"
    )

    assert pce["demand_leg_label"] == "PCE_basis_level_path_wedge_applied_to_demand_phillips_leg"
    assert pce["cpi_to_pce_slope_wedge"] == "0.88"
    assert pce["m_D"] == "0.09"
    assert pce["m_N"] == "0.13"
    assert Decimal(pce["demand_phillips_PCE_pp"]) == Decimal(pce_window["demand_only_after_wall_base_pp"])
    assert Decimal(pce["demand_phillips_PCE_pp"]) != Decimal(cpi_window["demand_only_after_wall_base_pp"])
    assert Decimal(pce_window["fx_import_base_pp"]) == Decimal(cpi_window["fx_import_base_pp"]) * Decimal("0.85")


def test_rwpi_cpi_basis_window_values_stay_exact_after_pce_crosswalk() -> None:
    result = _rwpi_result()
    row = next(
        item
        for item in result.rows("out_rwpi_window_path")
        if item["dose_mode"] == "persistent_level"
        and item["index_target"] == "CPI_U"
        and item["slack_state"] == "balanced"
        and item["horizon_window"] == "0_36m_cumulative_sum_pp"
    )

    assert row["demand_only_after_wall_base_pp"] == "0.04726101904188957067498136778"
    assert row["fx_import_base_pp"] == "0.3500000000000000000000000003"
    assert row["cost_channel_base_pp"] == "0.03483003"
    assert row["ND_pi_base_pp"] == "0.3624309890418895706749813681"


def test_rwpi_plug_validation_uses_independent_literal_oracles() -> None:
    result = _rwpi_result()
    scores = {
        row["diagnostic"]: row
        for row in result.rows("out_rwpi_plug_validation")
    }
    series = {
        (row["diagnostic"], row["period"], row["note"]): row
        for row in result.rows("out_rwpi_plug_validation_series")
    }

    fx_peak = series[
        (
            "FX/import leg",
            "2022-10",
            "observed broad-dollar plug vs import ex-petroleum y/y",
        )
    ]
    rent_peak = series[
        (
            "Shelter lag kernel",
            "2023-03",
            "CPI rent y/y peak after market-rent proxy",
        )
    ]
    oer_peak = series[
        (
            "Shelter lag kernel",
            "2023-04",
            "CPI OER y/y peak after market-rent proxy",
        )
    ]

    assert Decimal(fx_peak["predicted_value"]).quantize(Decimal("0.00001")) == Decimal("1.17628")
    assert "USD y/y peak 2022-10" in scores["FX/import leg"]["evidence_summary"]
    assert "lag 7m" in scores["FX/import leg"]["evidence_summary"]
    assert Decimal(rent_peak["predicted_value"]) == Decimal("13")
    assert Decimal(oer_peak["predicted_value"]) == Decimal("14")
    assert "ZORI y/y peak 2022-02" in scores["Shelter lag kernel"]["evidence_summary"]
    assert Decimal(
        scores["Cost channel"]["evidence_summary"]
        .split("residual change ", maxsplit=1)[1]
        .removesuffix("pp by 2023-08")
    ).quantize(Decimal("0.00001")) == Decimal("7.14007")
