from __future__ import annotations

import copy
import csv
from functools import lru_cache
from decimal import Decimal, localcontext
from io import StringIO
from pathlib import Path
import shutil

import pytest

from ratewall.rwtam.backcast import build_backcast, write_backcast_outputs
from ratewall.rwtam.scenarios import (
    build_crossing_shock_sweep,
    build_distress_scenario,
    write_distress_scenario_outputs,
)
from ratewall.rwtam.v1 import validate_bond_mtm_overlap_rows
from ratewall.rwtam.v1 import build_v1, write_v1_outputs
from ratewall.rwtam.v1 import (
    _driver,
    _effective_pack,
    _household_tax_family,
    _load_pack,
    _monthly_records,
    _opening_by_family,
    _t59,
    _month_index_from_label,
    _treasury_yield_delta_bp,
    _treasury_coupon_interest_components,
)
import ratewall.rwtam.v1 as v1_module


PACK_DIR = Path("configs/rwtam/packs")
GOLDEN_WAVE1_DIR = Path("tests/fixtures/rwtam/golden_wave1")
GOLDEN_WAVE2_DIR = Path("tests/fixtures/rwtam/golden_wave2")
GOLDEN_WAVE3_DIR = Path("tests/fixtures/rwtam/golden_wave3")
GOLDEN_WAVE4_DIR = Path("tests/fixtures/rwtam/golden_wave4")
GOLDEN_WAVE5_DIR = Path("tests/fixtures/rwtam/golden_wave5")
GOLDEN_WAVE6_DIR = Path("tests/fixtures/rwtam/golden_wave6")
GOLDEN_WAVE6_TAX_OFF_DIR = Path("tests/fixtures/rwtam/golden_wave6_tax_off")
GOLDEN_WAVE7_DIR = Path("tests/fixtures/rwtam/golden_wave7")
GOLDEN_WAVE7_TAX_OFF_DIR = Path("tests/fixtures/rwtam/golden_wave7_tax_off")
GOLDEN_WAVE8_DIR = Path("tests/fixtures/rwtam/golden_wave8")
GOLDEN_WAVE8_TAX_OFF_DIR = Path("tests/fixtures/rwtam/golden_wave8_tax_off")


@lru_cache(maxsize=1)
def _session_default_v1_result():
    return build_v1(PACK_DIR)


@pytest.fixture(scope="session")
def default_v1_result():
    return _session_default_v1_result()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _crossing_order_signature(rows: list[dict[str, str]]) -> list[str]:
    expected = [
        "cre_refi_wall",
        "cre_floating",
        "mortgage_arm_heloc",
        "business_ci_small",
        "corporate_high_yield",
        "consumer_unsecured",
        "mortgage_fixed_reset_refi",
    ]
    seen: set[str] = set()
    for row in rows:
        family = row.get("crossing_order_family") or row.get("crossing_family")
        if family:
            seen.add(family)
    return [family for family in expected if family in seen]


def test_rwtam_headline_byte_exact(default_v1_result) -> None:
    rows = default_v1_result.rows("out_ratewall_rollup")
    annual = [
        row
        for row in rows
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]
    cumulative = [
        row
        for row in rows
        if row["period_type"] == "cumulative_120_month"
        and row["period"] == "2026-2035"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]

    assert annual["RW_ratio"] == "0.04998743127077140250725423303"
    assert cumulative["RW_ratio"] == "0.05821291586424109293357621483"


def test_headline_sign_and_gdp_share_contract_rejects_mutations(
    default_v1_result,
) -> None:
    tables = {
        name: copy.deepcopy(default_v1_result.rows(name))
        for name in (
            "out_ratewall_rollup",
            "out_ratewall_monthly",
            "out_cashflow_core_rollup",
        )
    }

    assert v1_module._t63(tables)

    sign_mutation = copy.deepcopy(tables)
    sign_row = sign_mutation["out_ratewall_rollup"][0]
    sign_row["net_bil"] = str(-Decimal(sign_row["net_bil"]))
    assert not v1_module._t63(sign_mutation)

    scale_mutation = copy.deepcopy(tables)
    scale_row = scale_mutation["out_ratewall_rollup"][0]
    scale_row["net_gdp_share"] = str(
        Decimal(scale_row["net_gdp_share"]) * Decimal("100")
    )
    assert not v1_module._t63(scale_mutation)


def test_round7_switches_false_reproduce_wave7_headline() -> None:
    result = build_v1(
        PACK_DIR,
        include_combined_sinks=False,
        include_tdc_split_addendum=False,
        include_impulse_beta_comparator=False,
    )
    annual = [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]
    cumulative = [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["period_type"] == "cumulative_120_month"
        and row["period"] == "2026-2035"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]

    assert annual["RW_ratio"] == "0.05007759304057134174016063453"
    assert cumulative["RW_ratio"] == "0.05831903370124703618722353693"


def test_t25_to_t34_v1_invariants_all_pass(default_v1_result) -> None:
    result = default_v1_result
    checks = result.rows("out_invariant_check")

    assert {row["status"] for row in checks} == {"pass"}
    for check_id in [f"T{i}" for i in range(25, 45)] + [f"T{i}" for i in range(47, 54)]:
        assert any(row["check_id"].startswith(check_id) for row in checks), check_id


def test_t45_wave8_refreeze_preserves_tax_on_surface(default_v1_result) -> None:
    """golden_wave8 preserves the suspended-split, structural-beta surface."""
    result = default_v1_result
    frozen_tables = [
        "out_ratewall_rollup",
        "out_phase6_waterfall_scaffold",
        "out_cashflow_core_rollup",
        "out_cre_cashflow_channel",
        "out_deposit_holder_routing",
        "out_mortgage_holder_routing",
        "out_bank_receipt_pay_ledger",
        "out_tax_layer_household_wedge",
        "out_tax_layer_corporate_shield",
        "out_treasury_tax_receipts",
        "out_tax_layer_clawback_memo",
        "out_tax_layer_attribution",
        "out_scenario_axes_config",
        "out_tdc_beta_authority",
        "out_invariant_check",
    ]

    assert (GOLDEN_WAVE1_DIR / "out_ratewall_rollup.csv").exists()
    assert (GOLDEN_WAVE2_DIR / "out_ratewall_rollup.csv").exists()
    assert (GOLDEN_WAVE3_DIR / "out_ratewall_rollup.csv").exists()
    assert (GOLDEN_WAVE4_DIR / "out_ratewall_rollup.csv").exists()
    assert (GOLDEN_WAVE5_DIR / "out_ratewall_rollup.csv").exists()
    assert (GOLDEN_WAVE6_DIR / "out_ratewall_rollup.csv").exists()
    for table_name in frozen_tables:
        actual_rows = result.rows(table_name)
        expected_text = (GOLDEN_WAVE8_DIR / f"{table_name}.csv").read_text(encoding="utf-8")
        expected_rows = list(csv.DictReader(StringIO(expected_text)))
        assert len(actual_rows) == len(expected_rows), table_name
        for actual, expected in zip(actual_rows, expected_rows, strict=True):
            assert list(actual) == list(expected), table_name
            for field, expected_value in expected.items():
                actual_value = actual[field]
                if _is_decimal(actual_value) and _is_decimal(expected_value):
                    assert abs(Decimal(actual_value) - Decimal(expected_value)) <= Decimal("1e-18"), (
                        table_name,
                        field,
                        actual_value,
                        expected_value,
                    )
                else:
                    assert actual_value == expected_value, (table_name, field)


def test_shock_start_month_changes_monthly_core_path() -> None:
    jan = build_v1(PACK_DIR, shock_start_month="2026-01")
    jul = build_v1(PACK_DIR, shock_start_month="2026-07")
    jan_row = [
        row
        for row in jan.rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]
    jul_row = [
        row
        for row in jul.rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]

    assert Decimal(jan_row["N_bil"]) != Decimal(jul_row["N_bil"])
    assert Decimal(jan_row["D_bil"]) != Decimal(jul_row["D_bil"])


def test_dose_mode_default_is_persistent_and_f3_mechanics_change_cumulative_path() -> None:
    persistent = _session_default_v1_result()
    transient = build_v1(PACK_DIR, dose_mode="transient_12m")

    assert {row["dose_mode"] for rows in persistent.tables.values() for row in rows} == {
        "persistent_level"
    }
    assert {row["dose_mode"] for rows in transient.tables.values() for row in rows} == {
        "transient_12m"
    }

    def row(result, period: str) -> dict[str, str]:
        return [
            item
            for item in result.rows("out_ratewall_rollup")
            if item["period_type"] == "annual"
            and item["period"] == period
            and item["band"] == "base"
            and item["ricardian_offset"] == "0"
        ][0]

    assert Decimal(row(persistent, "2026")["N_bil"]) != Decimal(row(transient, "2026")["N_bil"])
    assert Decimal(row(persistent, "2026")["D_bil"]) != Decimal(row(transient, "2026")["D_bil"])
    assert Decimal(row(persistent, "2030")["N_bil"]) > Decimal(row(transient, "2030")["N_bil"])


def test_curve_construction_arithmetic_and_shape_assertions() -> None:
    pack = _effective_pack(_load_pack(PACK_DIR), True, True)
    start = _month_index_from_label("2026-01")

    assert _treasury_yield_delta_bp(
        pack, "10y", "base", 1, start, "persistent_level"
    ) == Decimal("115")
    assert _treasury_yield_delta_bp(
        pack, "10y", "base", 1, start, "transient_12m"
    ) == Decimal("16")
    assert _treasury_yield_delta_bp(
        pack, "10y", "base", 1, start, "transient_12m"
    ) > _treasury_yield_delta_bp(
        pack, "10y", "base", 7, start, "transient_12m"
    ) > _treasury_yield_delta_bp(
        pack, "10y", "base", 12, start, "transient_12m"
    )


def test_qt_supply_stress_flag_adds_long_end_term_premium_pack_addon() -> None:
    pack = _effective_pack(_load_pack(PACK_DIR), True, True)
    start = _month_index_from_label("2026-01")
    default_30y = _treasury_yield_delta_bp(
        pack, "30y", "base", 1, start, "persistent_level"
    )
    default_10y = _treasury_yield_delta_bp(
        pack, "10y", "base", 1, start, "persistent_level"
    )
    qt_30y = _treasury_yield_delta_bp(
        pack,
        "30y",
        "base",
        1,
        start,
        "persistent_level",
        qt_supply_stress=True,
    )
    qt_10y = _treasury_yield_delta_bp(
        pack,
        "10y",
        "base",
        1,
        start,
        "persistent_level",
        qt_supply_stress=True,
    )
    relief_10y = _treasury_yield_delta_bp(
        pack,
        "10y",
        "base",
        1,
        start,
        "persistent_level",
        qt_supply_stress=Decimal("-1"),
    )
    addon = v1_module._term_premium_parameter(
        pack, "delta_tp_qt_supply_addon_30y", "base"
    )
    addon_10y = v1_module._term_premium_parameter(
        pack, "delta_tp_qt_supply_addon_10y", "base"
    )
    scenario_axes = build_v1(PACK_DIR, qt_supply_stress=True).rows(
        "out_scenario_axes_config"
    )

    assert qt_30y - default_30y == addon
    assert qt_10y - default_10y == Decimal("5")
    assert default_10y - relief_10y == addon_10y
    assert any(row["scenario_id"] == "qt_supply_stress" for row in scenario_axes)


def test_qt_supply_stress_flag_adds_scenario_only_deposit_stock_leg() -> None:
    default = build_v1(PACK_DIR, include_impulse_beta_comparator=False)
    qt = build_v1(PACK_DIR, qt_supply_stress=True, include_impulse_beta_comparator=False)

    assert "out_qt_deposit_leg" not in default.tables
    qt_leg = qt.rows("out_qt_deposit_leg")
    base_qt = [row for row in qt_leg if row["band"] == "base"][0]

    assert Decimal(base_qt["qt_runoff_bil"]) > 0
    assert Decimal(base_qt["nonbank_absorption_share"]) > 0
    assert Decimal(base_qt["deposit_stock_delta_bil"]) < 0
    assert base_qt["label"] == "scenario_only"


def test_term_premium_parameter_missing_parameter_id_fails_loud() -> None:
    pack = _effective_pack(_load_pack(PACK_DIR), True, True)
    pack["term_premium_parameters"] = [
        row
        for row in pack["term_premium_parameters"]
        if row["parameter_id"] != "delta_tp_persistent_level_30y"
    ]
    start = _month_index_from_label("2026-01")

    with pytest.raises(ValueError, match="delta_tp_persistent_level_30y"):
        _treasury_yield_delta_bp(pack, "30y", "base", 1, start, "persistent_level")


def test_tax_off_new_construction_is_rebaselined_and_tax_layer_is_pure_extension(
    tmp_path: Path,
) -> None:
    tax_off = build_v1(PACK_DIR, include_tax_layer=False, dose_mode="transient_12m")
    tax_on = build_v1(PACK_DIR, include_tax_layer=True, dose_mode="transient_12m")
    tax_off_paths = write_v1_outputs(tax_off, tmp_path / "tax_off_wave8")

    assert tax_off.rows("out_ratewall_rollup")[0]["object_version_stamp"].startswith(
        "current_default_wave8_combined_sinks_tdc_split_suspended"
    )
    frozen = sorted(GOLDEN_WAVE8_TAX_OFF_DIR.glob("*.csv"))
    assert frozen
    assert sorted(path.name for path in frozen) == sorted(
        path.name for path in tax_off_paths.values() if path.exists()
    )
    for expected_path in frozen:
        if expected_path.name == "out_moneyness_liquid_buffers.csv":
            continue
        actual_path = tax_off_paths[expected_path.stem]
        assert actual_path.read_bytes() == expected_path.read_bytes(), expected_path.name
    assert tax_off.rows("out_tax_layer_attribution") == []
    assert tax_on.rows("out_tax_layer_attribution")
    assert {row["status"] for row in tax_on.rows("out_invariant_check")} == {"pass"}


def test_impulse_beta_context_is_comparison_only() -> None:
    result = _session_default_v1_result()
    comparison = result.rows("out_parallel_curve_comparison")

    assert any(row["scenario_id"] == "expectations_consistent_term_premium" for row in comparison)
    old = [row for row in comparison if row["scenario_id"] == "superseded_impulse_beta_comparator"][0]
    assert old["basis"] == "old_fixed_curve_beta_context_only"
    assert any(row["scenario_id"] == "impulse_beta_context" for row in comparison)


def test_retired_annual_monthly_bridge_is_not_current_curve_gate() -> None:
    bridge_script = Path("scripts/build_rwtam_annual_monthly_bridge.py").read_text(
        encoding="utf-8"
    )

    assert "legacy_annual_records_for_comparison" in bridge_script
    assert "_driver(\"treasury_notes_bonds_tips\"" in bridge_script
    assert "expectations_consistent_term_premium" not in bridge_script


def test_t59_receipt_identity_fails_when_stored_receipt_flow_is_mutated() -> None:
    result = _session_default_v1_result()
    pack = _effective_pack(_load_pack(PACK_DIR), True, True)
    phase6_pack = _load_pack(PACK_DIR / "phase6")
    monthly_records = _monthly_records(
        pack,
        phase6_pack=phase6_pack,
        include_tdc_settlement=True,
        include_tdc_split_addendum=False,
        tdc_split_addendum=v1_module._tdc_split_suspended(),
        include_combined_sinks=True,
        shock_start_month="2026-01",
        dose_mode="persistent_level",
        include_tax_layer=True,
    )
    tables = {name: [dict(row) for row in rows] for name, rows in result.tables.items()}
    tables["out_treasury_tax_receipts"][0]["net_treasury_receipt_flow_bil"] = "999999"

    assert not _t59(pack, monthly_records, tables)


def test_wrapper_double_count_probe(monkeypatch) -> None:
    def misclassified_tax_family(family: str) -> str | None:
        if family == "mmf_short_funding_assets":
            return "dc_assets"
        return _household_tax_family(family)

    monkeypatch.setattr(v1_module, "_household_tax_family", misclassified_tax_family)
    result = build_v1(PACK_DIR)
    t58 = [row for row in result.rows("out_invariant_check") if row["check_id"] == "T58"][0]

    assert t58["status"] == "fail"
    assert any(
        row["tax_pack_family"] == "dc_assets"
        for row in result.rows("out_tax_layer_household_wedge")
    )


def test_zero_household_tax_rates_remove_d_netting_exposure(monkeypatch) -> None:
    baseline = _session_default_v1_result()
    original_tax_parameter = v1_module._tax_parameter

    def zero_household_tax_parameter(
        pack: dict[str, list[dict[str, str]]],
        parameter_id: str,
        cell: str,
        family: str,
        band: str,
    ) -> Decimal:
        if parameter_id in {
            "interest_income_mtr_federal_only",
            "interest_income_mtr_federal_plus_state_avg",
            "taxable_or_current_taxed_account_share",
        }:
            return Decimal("0")
        return original_tax_parameter(pack, parameter_id, cell, family, band)

    monkeypatch.setattr(v1_module, "_tax_parameter", zero_household_tax_parameter)
    no_household_tax = build_v1(PACK_DIR)

    def household_netting_d_delta(result) -> Decimal:
        return sum(
            Decimal(row["d_delta_bil"])
            for row in result.rows("out_tax_layer_attribution")
            if row["period_type"] == "cumulative_120_month"
            and row["band"] == "base"
            and row["attribution_component"] == "household_tax_cell_netting_sign_effect"
        )

    baseline_component = household_netting_d_delta(baseline)
    probe_component = household_netting_d_delta(no_household_tax)
    assert baseline_component > Decimal("0")
    assert probe_component == Decimal("0")


def test_mortgage_turnover_share_band_probe_moves_fixed_mortgage_gross() -> None:
    result = _session_default_v1_result()
    rows = [
        row
        for row in result.rows("out_cashflow_family_contributions_monthly")
        if row["period_type"] == "cumulative_120_month"
        and row["instrument_family"] == "mortgages_fixed"
        and row["ricardian_offset"] == "0"
    ]
    by_band = {row["band"]: Decimal(row["raw_cashflow_bil"]) for row in rows}
    assert by_band["low"] < by_band["base"] < by_band["high"]


def test_direct_163j_stress_probe_lowers_leveraged_family_shield() -> None:
    low_stress = v1_module._dynamic_163j_shield(
        Decimal("0.168"),
        Decimal("0.85"),
        Decimal("0.50"),
        Decimal("100"),
    )
    high_stress = v1_module._dynamic_163j_shield(
        Decimal("0.168"),
        Decimal("0.85"),
        Decimal("0.50"),
        Decimal("300"),
    )
    assert high_stress < low_stress


def test_installment_amortizing_survival_reduces_old_no_decay_surface() -> None:
    result = _session_default_v1_result()
    pack = _effective_pack(_load_pack(PACK_DIR), True, True)
    assumptions = v1_module._assumptions(pack)
    opening = v1_module._opening_by_family(pack)

    base_rows = [
        row
        for row in result.rows("out_cashflow_family_contributions_monthly")
        if row["period_type"] == "cumulative_120_month"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
        and row["instrument_family"]
        in {"auto_installment_debt", "personal_installment_debt", "student_loans_private"}
    ]
    actual_raw = {
        row["instrument_family"]: Decimal(row["raw_cashflow_bil"])
        for row in base_rows
    }
    old_auto_raw = (
        opening["auto_installment_debt"]
        * _driver("auto_installment_debt", "base", 1)
        * assumptions["consumer_installment_new_flow_share"]["base"]
        * sum(Decimal(month) / Decimal("12") / Decimal("12") for month in range(1, 121))
    )
    assert actual_raw["auto_installment_debt"] < old_auto_raw


def test_invalid_dose_mode_rejected() -> None:
    try:
        build_v1(PACK_DIR, dose_mode="implicit_plus_100bp")
    except ValueError as exc:
        assert "dose_mode" in str(exc)
    else:
        raise AssertionError("invalid dose_mode should fail")


def test_persistent_coupon_cohort_repricing_keeps_post_year1_shock_path() -> None:
    persistent = build_v1(PACK_DIR, dose_mode="persistent_level")
    transient = build_v1(PACK_DIR, dose_mode="transient_12m")

    def cohort_row(result, source: str, month: str) -> dict[str, str]:
        return [
            row
            for row in result.rows("out_coupon_cohort_repricing")
            if row["band"] == "base"
            and row["cohort_source"] == source
            and row["roll_month"] == month
        ][0]

    persistent_expected_bp = Decimal("115")
    assert Decimal(
        cohort_row(persistent, "current_stock_roll", "2029-04")["shock_minus_baseline_bp"]
    ) == persistent_expected_bp
    assert Decimal(
        cohort_row(persistent, "new_deficit_issuance", "2029-04")["shock_minus_baseline_bp"]
    ) == persistent_expected_bp
    assert Decimal(
        cohort_row(transient, "current_stock_roll", "2029-04")["shock_minus_baseline_bp"]
    ) == Decimal("0")
    assert Decimal(
        cohort_row(transient, "new_deficit_issuance", "2029-04")["shock_minus_baseline_bp"]
    ) == Decimal("0")


def test_t46_config_only_synthetic_family_routes_without_engine_name(tmp_path: Path) -> None:
    pack_copy = tmp_path / "packs"
    shutil.copytree(PACK_DIR, pack_copy)
    synthetic_family = "subvened_auto_promo"
    with (pack_copy / "scenario_adjustments.csv").open("a", encoding="utf-8", newline="") as handle:
        handle.write(
            "toy_delta,toy_claim,"
            f"{synthetic_family},households,nonbank_finance,10,10,10,"
            "synthetic_claim,1,0,0,0,owner_assumption_mode,"
            "Synthetic never-seen family for generic processor test.\n"
        )
    with (pack_copy / "claim_processor_rules.csv").open("a", encoding="utf-8", newline="") as handle:
        handle.write(
            "toy_reward_rule,"
            f"{synthetic_family},1,opening_stocks,base,driver_curve,credit_card_revolving,"
            "household_debtors_negative,literal_holder,nonbank_finance,"
            "toy_channel,Synthetic reward-like claim route,owner_assumption_mode,"
            "0,0,false\n"
        )

    result = build_v1(pack_copy)
    rows = result.rows("out_claim_processor_channel")
    assert any(row["instrument_family"] == synthetic_family for row in rows)
    assert synthetic_family not in Path("src/ratewall/rwtam/v1.py").read_text(encoding="utf-8")


def _is_decimal(value: str) -> bool:
    if value == "":
        return False
    try:
        Decimal(value)
    except Exception:
        return False
    return True


def test_t27_treasury_bills_and_coupons_are_separate_and_sum_to_marketable() -> None:
    result = _session_default_v1_result()
    government = result.rows("out_government_interest_channel")
    y1_bills = [
        row
        for row in government
        if row["year"] == "2026" and row["instrument_family"] == "treasury_bills"
    ]
    y1_coupons = [
        row
        for row in government
        if row["year"] == "2026"
        and row["instrument_family"] == "treasury_notes_bonds_tips"
    ]

    assert y1_bills
    assert y1_coupons
    bill_mmf_share = [
        Decimal(row["holder_share"]) for row in y1_bills if row["holder"] == "mmfs"
    ][0]
    coupon_mmf_share = [
        Decimal(row["holder_share"]) for row in y1_coupons if row["holder"] == "mmfs"
    ][0]
    assert bill_mmf_share != coupon_mmf_share
    bill_cashflow = sum(Decimal(row["cashflow_delta_bil"]) for row in y1_bills)
    coupon_cashflow = sum(Decimal(row["cashflow_delta_bil"]) for row in y1_coupons)
    assert bill_cashflow > coupon_cashflow


def test_t28_intermediary_routes_convert_once_and_unallocated_zero() -> None:
    result = _session_default_v1_result()
    government = result.rows("out_government_interest_channel")

    unallocated = [row for row in government if row["unallocated_flag"] == "true"]
    assert unallocated
    assert {Decimal(row["converted_net_bil"]) for row in unallocated} == {Decimal("0")}

    mmf_rows = [row for row in government if row["holder"] == "mmfs"]
    assert mmf_rows
    assert all(
        abs(Decimal(row["routed_bil"]) - Decimal(row["cashflow_delta_bil"]))
        <= Decimal("0.000001")
        for row in mmf_rows
    )


def test_t29_remittance_deferred_asset_placeholder_is_reported() -> None:
    result = _session_default_v1_result()
    iorb = result.rows("out_iorb_channel")

    assert iorb
    assert {row["placeholder_flag"] for row in iorb} == {
        "OWNER_PLACEHOLDER_fed_deferred_asset_open_bil"
    }
    assert {row["fed_deferred_asset_open_bil"] for row in iorb} == {"190"}
    assert all(Decimal(row["fed_deferred_asset_open_bil"]) >= 0 for row in iorb)


def test_t30_horizon_rollup_and_monthly_government_interest_timing() -> None:
    result = _session_default_v1_result()
    rollup = result.rows("out_ratewall_rollup")
    cumulative = [
        row
        for row in rollup
        if row["period_type"] == "cumulative_120_month"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]
    annual = [
        row
        for row in rollup
        if row["period_type"] == "annual"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ]

    recomputed_rw = sum(Decimal(r["N_bil"]) for r in annual) / sum(
        Decimal(r["D_bil"]) for r in annual
    )
    assert abs(Decimal(cumulative["RW_ratio"]) - recomputed_rw) <= Decimal("1e-27")
    government = result.rows("out_government_interest_channel")
    y1 = sum(
        Decimal(row["cashflow_delta_bil"])
        for row in government
        if row["year"] == "2026"
    )
    y5 = sum(
        Decimal(row["cashflow_delta_bil"])
        for row in government
        if row["year"] == "2030"
    )
    assert y5 > y1
    assert y5 > 0


def test_t31_headline_has_bands_and_ricardian_columns() -> None:
    result = _session_default_v1_result()
    rollup = result.rows("out_ratewall_rollup")

    assert {"low", "base", "high"}.issubset({row["band"] for row in rollup})
    assert {"0", "0.2", "0.5"}.issubset({row["ricardian_offset"] for row in rollup})
    for column in [
        "ricardian_0_N_bil",
        "ricardian_0_2_N_bil",
        "ricardian_0_5_N_bil",
        "ricardian_0_RW",
        "ricardian_0_2_RW",
        "ricardian_0_5_RW",
    ]:
        assert column in rollup[0]


def test_t32_legacy_comparator_is_labeled_comparator_only() -> None:
    result = _session_default_v1_result()
    comparator = result.rows("out_legacy_d_comparator")

    assert comparator
    assert {row["role"] for row in comparator} == {"comparator_only"}
    assert all(Decimal(row["legacy_D_bil"]) > 0 for row in comparator)


def test_t33_retiree_collapse_diagnostic_is_reported() -> None:
    result = _session_default_v1_result()
    diagnostic = result.rows("out_retiree_collapse_diagnostic")[0]

    assert Decimal(diagnostic["retiree_interest_sensitive_asset_share"]) > Decimal("0.10")
    assert diagnostic["status"] == "retain_cell"


def test_t34_scaled_fungibility_is_preserved_in_headline_contract() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")

    assert [row for row in checks if row["check_id"] == "T34"][0]["status"] == "pass"
    rollup = result.rows("out_ratewall_rollup")[0]
    assert rollup["classification_rule"] == "net_within_cell_plus_phase6_headline_drag"


def test_t35_deposit_audit_split_uses_distinct_checkable_savings_and_cd_families() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")

    assert [row for row in checks if row["check_id"] == "T35"][0]["status"] == "pass"


def test_t36_mortgage_holder_decomposition_is_not_double_counted() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")
    routing = result.rows("out_mortgage_holder_routing")

    assert [row for row in checks if row["check_id"] == "T36"][0]["status"] == "pass"
    base_2026 = [
        row for row in routing if row["year"] == "2026" and row["band"] == "base"
    ]
    paid = {Decimal(row["mortgage_interest_paid_bil"]) for row in base_2026}
    received = sum(Decimal(row["holder_receipt_bil"]) for row in base_2026)
    assert len(paid) == 1
    assert abs(next(iter(paid)) - received) <= Decimal("0.000001")


def test_t37_mmf_short_funding_proxy_closes_asset_side() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")

    assert [row for row in checks if row["check_id"] == "T37"][0]["status"] == "pass"


def test_t38_phase6_waterfall_scaffold_is_additive_and_labeled() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")
    rows = result.rows("out_phase6_waterfall_scaffold")

    assert [row for row in checks if row["check_id"] == "T38"][0]["status"] == "pass"
    base_2026 = [
        row
        for row in rows
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ]
    assert [row["layer_id"] for row in base_2026][0] == "cashflow_core"
    assert base_2026[-1]["headline_status"] == "final_rw_full"
    assert Decimal(base_2026[-1]["cumulative_D_bil"]) > Decimal("200")
    assert {row["layer_label"] for row in base_2026} >= {"quantity", "valuation", "credit"}


def test_t39_phase6_overlap_registry_assigns_transaction_units_once() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")
    registry = result.rows("out_phase6_overlap_registry")

    assert [row for row in checks if row["check_id"] == "T39"][0]["status"] == "pass"
    exposure_keys = {row["exposure_exclusion_key"] for row in registry}
    assert "source_channel_id|exposure_id|month|cell_or_sector" in exposure_keys
    assert (
        "firm_id_or_sector|instrument_family|margin=cashflow_debt_service_vs_investment_hurdle"
        in exposure_keys
    )
    assert "housing_transaction_id|hpi_wealth_stock_id|lost_sale_attribution" in exposure_keys


def test_t40_rw_full_is_within_legacy_scalar_gate() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")
    comparator = result.rows("out_legacy_d_comparator")

    assert [row for row in checks if row["check_id"] == "T40"][0]["status"] == "pass"
    base = [
        row
        for row in comparator
        if row["band"] == "base" and row["ricardian_offset"] == "0"
    ][0]
    assert Decimal("0.4") <= Decimal(base["ratio"]) <= Decimal("1.6")


def test_t41_deposit_holder_rows_route_once_and_match_bank_payment() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")
    routing = result.rows("out_deposit_holder_routing")

    assert [row for row in checks if row["check_id"] == "T41"][0]["status"] == "pass"
    base_2026 = [
        row for row in routing if row["year"] == "2026" and row["band"] == "base"
    ]
    assert base_2026
    for family in {"deposits_checkable", "deposits_savings_mmda", "deposits_time_cds"}:
        rows = [row for row in base_2026 if row["instrument_family"] == family]
        holder_receipts = [
            row for row in rows if row["holder"] != "banks_payment_total"
        ]
        payment = [row for row in rows if row["holder"] == "banks_payment_total"][0]
        assert {row["route_count"] for row in holder_receipts} == {"1"}
        assert sum(Decimal(row["receipt_bil"]) for row in holder_receipts) == Decimal(
            payment["bank_family_payment_bil"]
        )


def test_t42_additive_waterfall_inputs_have_no_exposure_duplicates() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")
    rows = result.rows("out_additive_waterfall_inputs")

    assert [row for row in checks if row["check_id"] == "T42"][0]["status"] == "pass"
    keys = [
        (
            row["source_channel_id"],
            row["exposure_id"],
            row["month"],
            row["cell_or_sector"],
            row["band"],
            row["ricardian_offset"],
        )
        for row in rows
    ]
    assert len(keys) == len(set(keys))


def test_bank_ledgers_are_boundary_labeled_and_complete() -> None:
    result = _session_default_v1_result()
    ledger = result.rows("out_bank_receipt_pay_ledger")
    base_2026 = [row for row in ledger if row["year"] == "2026"]

    assert {row["ledger_boundary"] for row in base_2026} == {
        "depository_bank_only",
        "bank_plus_nonbank_credit_intermediation",
    }
    assert {
        row["line_item"]
        for row in base_2026
        if row["ledger_boundary"] == "bank_plus_nonbank_credit_intermediation"
    } >= {
        "syndicated_loan_receipts",
        "a2_mbs_investor_receipts",
        "deposit_interest_paid",
        "a6_short_funding_repo_paid",
    }
    complete_net = [
        row
        for row in base_2026
        if row["ledger_boundary"] == "bank_plus_nonbank_credit_intermediation"
        and row["ledger_side"] == "net"
    ][0]
    assert abs(Decimal(complete_net["amount_bil"])) <= Decimal("15")


def test_cre_cashflow_channel_routes_payers_and_creditors() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")
    cre = result.rows("out_cre_cashflow_channel")

    assert [row for row in checks if row["check_id"] == "T44"][0]["status"] == "pass"
    base_2026 = [
        row for row in cre if row["year"] == "2026" and row["band"] == "base"
    ]
    assert {row["instrument_family"] for row in base_2026} == {
        "cre_mortgages_floating",
        "cre_mortgages_fixed",
    }
    assert {row["holder"] for row in base_2026} == {"banks", "nonbank_finance"}
    assert {row["payer_small_share"] for row in base_2026} == {"0.6"}
    for family in {"cre_mortgages_floating", "cre_mortgages_fixed"}:
        rows = [row for row in base_2026 if row["instrument_family"] == family]
        paid = {Decimal(row["interest_paid_bil"]) for row in rows}
        assert len(paid) == 1
        assert sum(Decimal(row["holder_receipt_bil"]) for row in rows) == next(iter(paid))


def test_bnpl_channel_is_configured_and_rewards_zero_delta() -> None:
    result = _session_default_v1_result()
    bnpl = result.rows("out_bnpl_channel")
    base_2026 = [
        row for row in bnpl if row["year"] == "2026" and row["band"] == "base"
    ]

    assert {row["rule_id"] for row in base_2026} >= {
        "bnpl_installment_penalty",
        "bnpl_funding_liability_cost",
        "bnpl_float_deposit_yield",
        "bnpl_float_mmf_yield",
        "bnpl_card_float_removed",
        "bnpl_rewards_zero_delta",
    }
    reward = [row for row in base_2026 if row["rule_id"] == "bnpl_rewards_zero_delta"][0]
    assert Decimal(reward["gross_flow_delta_bil"]) == 0
    assert Decimal(reward["converted_net_bil"]) == 0


def test_bnpl_share_sensitivity_scales_linearly() -> None:
    result = _session_default_v1_result()
    rows = result.rows("out_bnpl_share_sensitivity")

    with localcontext() as context:
        context.prec = 200
        assert [row["bnpl_share_of_purchases"] for row in rows] == ["0.01", "0.1"]
        one_pct, ten_pct = rows
        assert Decimal(ten_pct["N_bil"]) == Decimal(one_pct["N_bil"]) * Decimal("10")
        assert Decimal(ten_pct["D_bil"]) == Decimal(one_pct["D_bil"]) * Decimal("10")
        assert Decimal(ten_pct["net_bil"]) == Decimal(one_pct["net_bil"]) * Decimal("10")
        assert Decimal(one_pct["net_bil"]) == Decimal("0.2085204479166666666666666667")
    default_pack = _effective_pack(_load_pack(PACK_DIR), True, True)
    default_opening = {
        family
        for family in _opening_by_family(default_pack)
        if family.startswith("bnpl") or family == "bnpl_installment"
    }
    assert default_opening == set()


def test_t47_constant_spread_level_terms_do_not_enter_pair_deltas() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")
    t47 = [row for row in checks if row["check_id"] == "T47"][0]

    assert t47["status"] == "pass"


def test_t48_cost_legs_do_not_route_household_income() -> None:
    result = _session_default_v1_result()
    checks = result.rows("out_invariant_check")
    t48 = [row for row in checks if row["check_id"] == "T48"][0]

    assert t48["status"] == "pass"
    with (PACK_DIR / "claim_processor_rules.csv").open(encoding="utf-8", newline="") as handle:
        rules = list(csv.DictReader(handle))
    cost_rules = [row for row in rules if row.get("cost_leg") == "true"]
    assert {row["rule_id"] for row in cost_rules} >= {"bnpl_funding_liability_cost"}
    assert all(row["receiver_route"] != "opening_holders" for row in cost_rules)


def test_t49_scenario_delta_balance_identity_closes_by_sector() -> None:
    result = _session_default_v1_result()
    rows = result.rows("out_scenario_delta_balance")

    assert rows
    assert {row["status"] for row in rows} == {"pass"}
    households = [
        row
        for row in rows
        if row["delta_set_id"] == "bnpl_delta_set"
        and row["band"] == "base"
        and row["sector"] == "households"
    ][0]
    assert abs(Decimal(households["identity_gap_bil"])) <= Decimal("0.000001")
    assert any(
        row["declared_real_side_counterpart_bil"] != "0"
        for row in rows
        if row["delta_set_id"] == "bnpl_delta_set" and row["band"] == "base"
    )


def test_t49_misdeclared_delta_set_fails_closure_probe(tmp_path: Path) -> None:
    pack_copy = tmp_path / "packs"
    shutil.copytree(PACK_DIR, pack_copy)
    path = pack_copy / "scenario_adjustments.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row["row_id"] == "bnpl_real_counterpart_banks":
            row["stock_base"] = "0"
            break
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    result = build_v1(pack_copy)
    probe = [
        row
        for row in result.rows("out_scenario_delta_balance")
        if row["delta_set_id"] == "bnpl_delta_set"
        and row["band"] == "base"
        and row["sector"] == "banks"
    ][0]
    assert probe["status"] == "fail"
    assert Decimal(probe["identity_gap_bil"]) != 0


def test_moneyness_weight_diagnostic_emits_cell_buffers() -> None:
    result = _session_default_v1_result()
    rows = result.rows("out_moneyness_liquid_buffers")

    assert rows
    assert "hh_constrained_net_borrower" in {row["cell_or_sector"] for row in rows}
    assert all(Decimal(row["average_moneyness_weight"]) >= 0 for row in rows)
    by_cell = {row["cell_or_sector"]: row for row in rows}
    assert by_cell["federal_reserve_accounting_cell"]["moneyness_weighted_buffer_bil"] == "5167.164"
    assert by_cell["unallocated_no_conversion"]["moneyness_weighted_buffer_bil"] == "1731.834"
    assert by_cell["hh_constrained_net_borrower"]["moneyness_weighted_buffer_bil"] == (
        "680.239303637335316672784"
    )
    weight_rows = _read_csv(PACK_DIR / "moneyness_weights.csv")
    weight_by_family = {row["instrument_family"]: row for row in weight_rows}
    assert weight_by_family["treasury_notes_bonds_tips"]["moneyness_weight"] == "0.90"
    assert weight_by_family["treasury_notes_bonds_tips"]["moneyness_weight_low"] == "0.82"
    assert weight_by_family["treasury_notes_bonds_tips"]["moneyness_weight_high"] == "0.95"
    assert weight_by_family["treasury_notes_bonds_tips"]["evidence_label"] == "market-calibrated"
    assert weight_by_family["credit_card_revolving"]["moneyness_weight"] == "0.06"
    assert weight_by_family["credit_card_revolving"]["evidence_label"] == "still-assumption"


def test_s4_moneyness_calibration_preserves_distress_crossings_and_ordering() -> None:
    expected_stress_crossed = {
        ("business_ci_small", "firm_bank_dependent_small", "performing_to_distressed", "3"),
        ("consumer_auto_loan", "hh_constrained_net_borrower", "performing_to_distressed", "3"),
        ("consumer_auto_loan", "hh_middle_owner_illiquid", "performing_to_distressed", "3"),
        ("consumer_credit_card_revolving", "hh_constrained_net_borrower", "performing_to_distressed", "3"),
        ("consumer_credit_card_revolving", "hh_middle_owner_illiquid", "performing_to_distressed", "3"),
        ("consumer_personal_other", "hh_constrained_net_borrower", "performing_to_distressed", "3"),
        ("corporate_high_yield", "firm_market_funded_large", "performing_to_distressed", "3"),
        ("cre_floating", "firm_real_estate_cre_floating", "performing_to_distressed", "3"),
        ("cre_refi_wall", "firm_real_estate_cre_maturity_wall", "performing_to_distressed", "3"),
        ("cre_refi_wall", "firm_real_estate_cre_maturity_wall", "performing_to_default", "5"),
        ("mortgage_arm_heloc", "hh_constrained_net_borrower", "performing_to_distressed", "3"),
        ("mortgage_arm_heloc", "hh_middle_owner_illiquid", "performing_to_distressed", "3"),
        ("student_private_variable", "hh_constrained_net_borrower", "performing_to_distressed", "3"),
        ("student_private_variable", "hh_middle_owner_illiquid", "performing_to_distressed", "3"),
    }

    stress = build_distress_scenario(PACK_DIR, scenario_id="stress_300bp")
    policy = build_distress_scenario(PACK_DIR, scenario_id="policy_100bp_distress_on")
    stress_crossed = {
        (
            row["family"],
            row["cell_or_sector"],
            row["threshold"],
            row["crossed_month_index"],
        )
        for row in stress.rows("out_distress_threshold_crossings")
        if row["crossed_month_index"]
    }

    assert stress_crossed == expected_stress_crossed
    assert {
        row["crossed_month_index"]
        for row in policy.rows("out_distress_threshold_crossings")
    } == {""}
    assert _crossing_order_signature(stress.rows("out_distress_threshold_crossings")) == [
        "cre_refi_wall",
        "cre_floating",
        "mortgage_arm_heloc",
        "business_ci_small",
        "corporate_high_yield",
        "consumer_unsecured",
        "mortgage_fixed_reset_refi",
    ]
    assert _crossing_order_signature(build_crossing_shock_sweep(PACK_DIR)) == [
        "cre_refi_wall",
        "cre_floating",
        "mortgage_arm_heloc",
        "business_ci_small",
        "corporate_high_yield",
        "consumer_unsecured",
        "mortgage_fixed_reset_refi",
    ]


def test_t50_tdc_stocks_are_zero_when_shock_equals_baseline() -> None:
    result = _session_default_v1_result()
    t50 = [row for row in result.rows("out_invariant_check") if row["check_id"] == "T50"][0]

    assert t50["status"] == "pass"


def test_t51_tdc_created_deposit_income_uses_full_rate_level() -> None:
    """Fixture: monthly core applies the 3.5% full rate to monthly earning stock."""
    result = _session_default_v1_result()
    row = [
        row
        for row in result.rows("out_tdc_channel")
        if row["mode_id"] == "TOTAL" and row["year"] == "2026" and row["band"] == "base"
    ][0]

    assert Decimal(row["full_level_deposit_rate"]) == Decimal("0.035")
    assert Decimal("0") < Decimal(row["created_deposit_income_bil"]) < (
        Decimal(row["created_deposit_stock_bil"]) * Decimal("0.035")
    )


def test_tdc_mode_mix_sensitivity_includes_all_a_all_b_and_base() -> None:
    result = _session_default_v1_result()
    rows = result.rows("out_tdc_mode_sensitivity")

    scenario_rows = [row for row in rows if row["scenario_id"]]
    sensitivity_rows = [row for row in rows if not row["scenario_id"]]
    assert {row["scenario_id"] for row in scenario_rows} == {
        "all_A_domestic_nonbank_swap",
        "all_B_bank_expansion",
        "base_mix",
    }
    assert {row["sensitivity_id"] for row in sensitivity_rows} == {
        "tdc_beta_sensitivity_minus_0p005",
        "tdc_beta_sensitivity_legacy_0p342",
        "tdc_beta_sensitivity_0p516",
        "tdc_beta_sensitivity_1p038",
    }
    for row in sensitivity_rows:
        assert row["authority_status"] == "equal_status_sensitivity"
        assert row["canonical_status"] == "noncanonical_sensitivity_only"
    legacy = [
        row
        for row in sensitivity_rows
        if row["sensitivity_id"] == "tdc_beta_sensitivity_legacy_0p342"
    ][0]
    assert legacy["legacy_status"] == "visibly_legacy"
    all_a = [row for row in scenario_rows if row["scenario_id"] == "all_A_domestic_nonbank_swap"][0]
    all_b = [row for row in scenario_rows if row["scenario_id"] == "all_B_bank_expansion"][0]
    base = [row for row in scenario_rows if row["scenario_id"] == "base_mix"][0]
    assert Decimal(all_a["year1_tdc_N_bil"]) == 0
    assert Decimal(all_b["year1_tdc_N_bil"]) > Decimal(base["year1_tdc_N_bil"]) > 0


def test_t52_parameter_derived_delta_set_stocks_match_loaded_values() -> None:
    result = _session_default_v1_result()
    rows = result.rows("out_scenario_delta_derivation")

    assert rows
    assert {row["status"] for row in rows} == {"pass"}


def test_t53_tdcsim_coupon_roll_schedule_is_promoted_and_binds_monthly_path() -> None:
    result = _session_default_v1_result()
    schedule = result.rows("out_treasury_coupon_roll_schedule")
    measured = [row for row in schedule if row["mode_id"] == "measured_monthly_schedule"]
    fallback = [row for row in schedule if row["mode_id"] == "blended_rate_fallback_sensitivity"]
    checks = result.rows("out_invariant_check")

    assert len(measured) == 120
    assert measured[0]["input_basis_label"] == "measured"
    assert Decimal(measured[11]["cumulative_share_of_current_stock"]) == Decimal("0.1329564616")
    assert fallback
    assert [row for row in checks if row["check_id"] == "T53"][0]["status"] == "pass"

    government = result.rows("out_government_interest_channel")
    y1 = sum(
        Decimal(row["cashflow_delta_bil"])
        for row in government
        if row["year"] == "2026"
    )
    y5 = sum(
        Decimal(row["cashflow_delta_bil"])
        for row in government
        if row["year"] == "2030"
    )
    assert y5 > y1
    assert y5 > 0


def test_treasury_coupon_runoff_splits_current_stock_from_new_issuance() -> None:
    result = _session_default_v1_result()
    government = result.rows("out_government_interest_channel")
    y1_coupon = [
        row
        for row in government
        if row["year"] == "2026"
        and row["instrument_family"] == "treasury_notes_bonds_tips"
    ][0]
    y2_coupon = [
        row
        for row in government
        if row["year"] == "2027"
        and row["instrument_family"] == "treasury_notes_bonds_tips"
    ][0]

    assert Decimal(y1_coupon["new_issuance_coupon_interest_bil"]) > 0
    assert Decimal(y2_coupon["new_issuance_coupon_interest_bil"]) > 0
    assert (
        Decimal(y2_coupon["current_stock_reprice_share"])
        != Decimal(y2_coupon["new_issuance_reprice_share"])
    )

    no_new = _treasury_coupon_interest_components(
        _load_pack(PACK_DIR),
        "base",
        1,
        Decimal("23822"),
        Decimal("0"),
    )
    assert no_new["new_issuance_coupon_interest"] == 0
    assert no_new["current_stock_reprice_share"] == Decimal("0.1329564616")


def test_tdcsim_issuance_mix_is_carried_as_sensitivity_not_core_promotion() -> None:
    result = _session_default_v1_result()
    rows = result.rows("out_treasury_issuance_tenor_mix")
    summary = [row for row in rows if row["tenor_bucket"] == "SUMMARY_bill_share"][0]

    assert Decimal(summary["share_of_gross_issuance"]) == Decimal("0.198")
    assert summary["promotion_status"] == "not_promoted_current_core_assumption_base_remains_0_30"


def test_t54_t55_backcast_outputs_are_diagnostic_and_closed(tmp_path: Path) -> None:
    if not Path("do/backcast").exists():
        pytest.skip("backcast diagnostic inputs are not part of the published repository")
    result = build_backcast(PACK_DIR, Path("do/backcast"))
    checks = result.rows("out_backcast_invariant_check")
    tracking = result.rows("out_backcast_tracking")
    mmf_decomposition = result.rows("out_mmf_income_gross_to_net_decomposition")
    predicted = result.rows("out_backcast_predicted_flows")
    rw = result.rows("out_RW_cash_backcast_series")
    state_packs = result.rows("out_backcast_state_packs")

    assert {row["status"] for row in checks} == {"pass"}
    assert {row["check_id"] for row in checks} == {"T54", "T55", "T56", "T57"}
    assert {"2022Q1", "2023Q1", "2024Q1", "2025Q1"} == {
        row["anchor_quarter"] for row in state_packs
    }
    assert all(row["diagnostic_label"] == "backcast_diagnostic" for row in predicted)
    assert all(row["headline_entry_flag"] == "false" for row in predicted)
    assert any("gap_no_defensible" in row["coverage"] for row in tracking)
    assert any(
        row["channel"] == "public_interest_net_block_v2_anchor_support_vs_2021"
        and row["predicted_channel"] == "government_interest_public_net_block"
        and row["perimeter"] == "identity_context_not_model_validation"
        and row["classification"] == "identity_context_not_model_validation"
        for row in tracking
    )
    assert any(
        row["channel"] == "direct_treasury_interest_support"
        and row["perimeter"] == "repricing_on_fixed_stock_approx"
        and row["classification"] == "public_interest_clean_test_state_proxy_or_rate_path_error"
        for row in tracking
    )
    assert all(
        row["perimeter"]
        for row in tracking
        if row["channel"].startswith("treasury_")
        or row["channel"].startswith("direct_treasury")
    )
    assert not any(
        row["perimeter"] != "repricing_on_fixed_stock_approx"
        and row["classification"] == "public_interest_clean_test_state_proxy_or_rate_path_error"
        for row in tracking
        if row["channel"].startswith("treasury_")
        or row["channel"].startswith("direct_treasury")
    )
    assert all(
        row["perimeter"] == "repricing_on_fixed_stock_approx"
        for row in tracking
        if row["classification"] == "public_interest_clean_test_state_proxy_or_rate_path_error"
        and (
            row["channel"].startswith("treasury_")
            or row["channel"].startswith("direct_treasury")
        )
    )
    assert all(
        row["classification"] != "public_interest_clean_test_state_proxy_or_rate_path_error"
        for row in tracking
        if row["channel"] == "treasury_marketable_fixed_coupon_bill_interest_residual_level"
    )
    assert all(
        row["classification"] == "needs_reconstruction"
        for row in tracking
        if row["channel"] == "stock_growth_interest_bridge"
    )
    scored = [
        row
        for row in tracking
        if row["channel"] == "direct_treasury_interest_support"
    ]
    expected_ratios = {
        "2022": Decimal("1.1697"),
        "2023": Decimal("1.0629"),
        "2024": Decimal("1.0496"),
    }
    for row in scored:
        ratio = Decimal(row["predicted_value_bil"]) / Decimal(row["aligned_realized_value_bil"])
        assert ratio.quantize(Decimal("0.0001")) == expected_ratios[row["calendar_year"]]
    assert any(
        row["channel"] == "fed_cash_remittances_transferred_to_treasury_level"
        and row["definition_alignment"].startswith("target_level_minus_2021")
        for row in tracking
    )
    assert any(
        row["channel"] == "fed_iorb_and_other_deposits_interest_expense_level"
        and row["predicted_channel"] == "iorb_and_other_deposits_recipient_support"
        for row in tracking
    )
    assert any(
        row["channel"] == "deposit_safe_yield_income_d1_candidate"
        and row["circularity_flag"] == "true"
        for row in tracking
    )
    card = [
        row
        for row in tracking
        if row["channel"] == "credit_card_interest_g19_proxy_level"
        and row["calendar_year"] == "2022"
    ][0]
    assert Decimal(card["aligned_realized_value_bil"]) == Decimal("43.584")
    assert card["definition_alignment"].startswith("target_level_minus_2021")
    assert all(
        row["classification"] == "observed_level_context"
        for row in tracking
        if row["channel"] == "credit_card_interest_cfpb_observed"
    )
    assert [row["calendar_year"] for row in rw] == ["2022", "2023", "2024"]
    assert {row["rw_object"] for row in rw} == {"RW_cash_backcast"}
    assert all("headline_RW_full" in row["forbidden_comparisons"] for row in rw)
    episode = result.rows("out_episode_waterfall_housing_cash_only")
    assert [row["calendar_year"] for row in episode] == ["2022", "2023", "2024"]
    assert {row["rw_object"] for row in episode} == {"episode_waterfall_housing_cash_only"}
    assert all(
        Decimal("20") <= Decimal(row["housing_quantity_D_bil"]) <= Decimal("600")
        for row in episode
        if Decimal(row["avg_policy_shock_bp_vs_2022Q1"]) <= Decimal("500")
    )
    on_rrp_check = result.rows("out_backcast_on_rrp_opening_check")
    assert {row["status"] for row in on_rrp_check} == {"pass"}
    assert all(Decimal("50") <= Decimal(row["opening_base_bil"]) <= Decimal("3000") for row in on_rrp_check)
    paths = write_backcast_outputs(result, tmp_path)
    assert paths["out_backcast_tracking"].exists()
    assert paths["out_RW_cash_backcast_series"].exists()
    mmf_2022 = [
        row for row in mmf_decomposition if row["calendar_year"] == "2022"
    ][0]
    assert Decimal(mmf_2022["net_model_income_bil"]) < Decimal(
        mmf_2022["gross_model_income_bil"]
    )
    assert mmf_2022["target_quality_status"] == "scored_accrual_net_yield_construction"
    assert mmf_2022["distribution_context_status"] == "target_side_perimeter_gap_unexplained"
    assert Decimal(mmf_2022["mmf_expense_ratio_base"]) == Decimal("0.0013")
    assert Decimal(mmf_2022["ratio_net_to_sec_accrual"]).quantize(Decimal("0.01")) == Decimal("1.02")
    assert Decimal(mmf_2022["ratio_net_to_dividends_paid"]) > Decimal("1")
    assert any(
        row["channel"] == "mmf_income_ici_table39_distribution_series_context"
        and row["classification"] == "distribution_series_context_not_scored"
        for row in tracking
    )


def test_treasury_perimeter_decomposition_targets_are_complete() -> None:
    if not Path("do/backcast").exists():
        pytest.skip("backcast diagnostic inputs are not part of the published repository")
    with Path("do/backcast/realized_flow_targets.csv").open(encoding="utf-8", newline="") as handle:
        targets = list(csv.DictReader(handle))

    treasury_rows = [
        row
        for row in targets
        if row["channel"].startswith("treasury_")
        or row["channel"].startswith("direct_treasury")
        or row["channel"] == "stock_growth_interest_bridge"
    ]
    assert treasury_rows
    assert all(row["perimeter"] for row in treasury_rows)

    by_channel_year = {(row["channel"], row["year"]): row for row in targets}
    for channel, perimeter, coverage in [
        (
            "treasury_tips_inflation_compensation",
            "tips_inflation_compensation",
            "accrual_counted_in_expense;fy_annual_proxy_in_cy_row",
        ),
        ("treasury_frn_interest", "frn_interest", "sfd_stock_rate_proxy"),
        ("treasury_savings_nonmarketable", "savings_nonmarketable", "sfd_stock_rate_proxy"),
        (
            "treasury_marketable_fixed_coupon_bill_interest_residual_level",
            "perimeter_not_fixed_stock_comparable",
            "residual_construction",
        ),
    ]:
        rows = [row for row in targets if row["channel"] == channel]
        assert {row["year"] for row in rows} == {"2021", "2022", "2023", "2024"}
        assert {row["perimeter"] for row in rows} == {perimeter}
        assert {row["coverage"] for row in rows} == {coverage}

    bridge_values = {
        "2022": Decimal("0.573536"),
        "2023": Decimal("182.426216"),
        "2024": Decimal("332.246992"),
    }
    for year, bridge_value in bridge_values.items():
        v1 = Decimal(by_channel_year[("direct_treasury_interest_support", year)]["realized_value_bil"])
        residual = (
            Decimal(
                by_channel_year[
                    ("treasury_marketable_fixed_coupon_bill_interest_residual_level", year)
                ]["realized_value_bil"]
            )
            - Decimal(
                by_channel_year[
                    ("treasury_marketable_fixed_coupon_bill_interest_residual_level", "2021")
                ]["realized_value_bil"]
            )
        )
        bridge = Decimal(by_channel_year[("stock_growth_interest_bridge", year)]["realized_value_bil"])
        assert bridge == bridge_value
        assert v1 + bridge == residual


def test_bond_mtm_diagnostic_is_include_zero_and_matches_pack_check_against() -> None:
    result = _session_default_v1_result()
    rows = result.rows("out_bond_mtm_diagnostic")
    checks = result.rows("out_invariant_check")

    assert rows
    assert [row for row in checks if row["check_id"] == "T55"][0]["status"] == "pass"
    assert {row["include_flag"] for row in rows} == {"0"}
    assert {row["headline_entry_flag"] for row in rows} == {"false"}
    total_base = sum(Decimal(row["diagnostic_D_base_bil"]) for row in rows)
    assert abs(total_base - Decimal("4.66912416328307787532812500")) <= Decimal("0.0001")
    additive = result.rows("out_additive_waterfall_inputs")
    assert "bond_mtm_wealth" not in {row["source_channel_id"] for row in additive}


def test_bond_mtm_same_security_overlap_probe_rejects_double_count() -> None:
    probe = [
        {
            "source_channel_id": "bond_mtm_wealth",
            "security_id": "T_NOTE_1",
            "issuer_sector": "treasury_federal",
            "holder_route": "hh_retiree_fixed_income_saver",
            "duration_bucket": "5-10y",
            "coupon_type": "fixed",
            "cell_or_sector": "hh_retiree_fixed_income_saver",
            "duration_price_leg": "1",
            "coupon_cashflow_leg": "0",
            "include_flag": "1",
        },
        {
            "source_channel_id": "cashflow_interest_income_or_expense",
            "security_id": "T_NOTE_1",
            "issuer_sector": "treasury_federal",
            "holder_route": "hh_retiree_fixed_income_saver",
            "duration_bucket": "5-10y",
            "coupon_type": "fixed",
            "cell_or_sector": "hh_retiree_fixed_income_saver",
            "duration_price_leg": "0",
            "coupon_cashflow_leg": "1",
            "include_flag": "1",
        },
    ]

    errors = validate_bond_mtm_overlap_rows(probe)
    assert errors
    assert "same-security coupon-vs-MTM overlap rejected" in errors[0]


def test_distress_scenario_outputs_are_isolated_and_invariants_pass(tmp_path: Path) -> None:
    result = build_distress_scenario(PACK_DIR, scenario_id="stress_300bp")
    checks = result.rows("out_distress_invariant_check")
    ledger = result.rows("out_distress_ledger_monthly")
    damping = result.rows("out_distress_buffer_damping_incidence")

    assert {row["status"] for row in checks} == {"pass"}
    assert {row["headline_entry_flag"] for row in ledger} == {"false"}
    assert {row["baseline_multiplier"] for row in damping} == {"1"}
    assert any(Decimal(row["slope_multiplier"]) > 1 for row in damping)
    fixed = [row for row in ledger if row["family"] == "mortgage_fixed_reset_refi"]
    assert fixed
    assert {Decimal(row["incremental_default_principal_bil"]) for row in fixed} == {Decimal("0")}
    cumulative_incremental: dict[tuple[str, str], Decimal] = {}
    for row in sorted(ledger, key=lambda item: (item["family"], item["cell_or_sector"], int(item["month_index"]))):
        key = (row["family"], row["cell_or_sector"])
        cumulative_incremental[key] = cumulative_incremental.get(key, Decimal("0")) + Decimal(
            row["incremental_default_principal_bil"]
        )
        assert Decimal(row["deadweight_realized_bil"]) <= cumulative_incremental[key]
    paths = write_distress_scenario_outputs(result, tmp_path)
    assert paths["out_distress_ledger_monthly"].exists()


def test_policy_100bp_distress_falsification_is_emitted() -> None:
    result = build_distress_scenario(PACK_DIR, scenario_id="policy_100bp_distress_on")
    rows = result.rows("out_distress_falsification_check")

    assert {row["criterion"] for row in rows} == {
        "household_monthly_increment_bp_lte_10",
        "cre_matured_balloon_no_threshold_cross_at_100bp",
    }
    assert {row["status"] for row in result.rows("out_distress_invariant_check")} == {"pass"}


def test_static_hold_crossing_shock_sweep_reports_order_and_dsr_dispersion() -> None:
    rows = build_crossing_shock_sweep(PACK_DIR)

    assert rows
    assert {row["shock_sweep_bp"] for row in rows} == {"0;10;20;50;100;150;250"}
    assert {"P_to_X", "P_to_N"} == {row["transition"] for row in rows}
    assert {row["cell_dsr_baseline_dispersion"] for row in rows} == {"percentile_bucket_grid"}
    assert {row["distribution_bucket"] for row in rows} == {"percentile_bucket_grid"}
    assert all("baseline_share_above_threshold" in row for row in rows)
    assert any(Decimal(row["incremental_share"]) > Decimal("0") for row in rows)
    assert any(row["minimum_static_hold_shock_bp"] for row in rows)


def test_build_rwtam_v1_writes_required_outputs(tmp_path: Path) -> None:
    result = _session_default_v1_result()
    paths = write_v1_outputs(result, tmp_path)

    for name in [
        "out_ratewall_rollup",
        "out_iorb_channel",
        "out_government_interest_channel",
        "out_curve_to_holders_channel",
        "out_legacy_d_comparator",
        "out_phase6_waterfall_scaffold",
        "out_phase6_overlap_registry",
        "out_phase6_channel_table",
        "out_phase6_excluded_diagnostics",
        "out_bank_receipt_pay_ledger",
        "out_deposit_holder_routing",
        "out_mortgage_holder_routing",
        "out_cre_cashflow_channel",
        "out_claim_processor_channel",
        "out_bnpl_channel",
        "out_bnpl_share_sensitivity",
        "out_scenario_delta_derivation",
        "out_scenario_delta_balance",
        "out_moneyness_liquid_buffers",
        "out_absorption_modes",
        "out_tdc_beta_authority",
        "out_tdc_channel",
        "out_tdc_beta_implied",
        "out_tdc_mode_sensitivity",
        "out_tdc_chi_diagnostic",
        "out_treasury_coupon_roll_schedule",
        "out_treasury_issuance_tenor_mix",
        "out_bond_mtm_diagnostic",
        "out_cashflow_leg_gross",
        "out_tax_layer_household_wedge",
        "out_tax_layer_corporate_shield",
        "out_treasury_tax_receipts",
        "out_tax_layer_clawback_memo",
        "out_tax_layer_attribution",
        "out_additive_waterfall_inputs",
        "out_fed_rrp_channel",
        "out_scenario_axes_config",
        "out_flagged_assumptions",
        "out_invariant_check",
    ]:
        assert paths[name].exists()
        assert paths[name].read_text(encoding="utf-8").splitlines()[0]


def test_tdc_beta_authority_is_equal_status_and_has_no_selectors() -> None:
    pack = v1_module._effective_pack(v1_module._load_pack(PACK_DIR), True, True)
    authority = pack["tdc_beta_authority"]

    assert {row["beta"] for row in authority} == {"-0.005", "0.342", "0.516", "1.038"}
    assert all(row["authority_status"] == "equal_status_sensitivity" for row in authority)
    assert next(
        row for row in authority if row["beta"] == "0.342"
    )["legacy_status"] == "visibly_legacy"
    assert "tdc_flow_size_beta_override" not in pack
    assert "beta_state_indicator" not in pack
    assert v1_module._tdc_implied_beta(pack, "base") == Decimal("0.2")
    assert all(row["status"] == "pass" for row in v1_module._validate_tdc_beta_authority(pack))


def test_suspended_tdcsim_split_cannot_enter_v1() -> None:
    with pytest.raises(ValueError, match="suspended TDCSim split input"):
        build_v1(PACK_DIR, include_tdc_split_addendum=True)
    with pytest.raises(ValueError, match="suspended TDCSim split input"):
        _monthly_records(
            v1_module._effective_pack(v1_module._load_pack(PACK_DIR), True, True),
            include_tdc_settlement=True,
            include_tdc_split_addendum=True,
            shock_start_month="2026-01",
            dose_mode="persistent_level",
            include_tax_layer=True,
        )


def test_tdc_validator_rejects_defaults_and_all_selector_surfaces() -> None:
    pack = v1_module._effective_pack(v1_module._load_pack(PACK_DIR), True, True)
    checks = {
        row["check_id"]: row["status"]
        for row in v1_module._validate_tdc_beta_authority(pack)
    }
    assert checks == {
        "T25_tdc_beta_equal_status_sensitivity_set": "pass",
        "T25_tdc_beta_no_selector": "pass",
        "T25_tdc_beta_noncanonical": "pass",
    }

    mutations: list[dict[str, list[dict[str, str]]]] = []
    singleton_default = copy.deepcopy(pack)
    singleton_default["tdc_beta_authority"][1]["is_default"] = "1"
    mutations.append(singleton_default)
    state_mapping = copy.deepcopy(pack)
    state_mapping["tdc_beta_authority"][1]["state_family"] = "plumbing_active"
    state_mapping["tdc_beta_authority"][1]["transition_direction"] = "toward_offset"
    mutations.append(state_mapping)
    flow_size = copy.deepcopy(pack)
    flow_size["tdc_flow_size_beta_override"] = [{"enabled": "1"}]
    mutations.append(flow_size)
    quiet_or_large_shock = copy.deepcopy(pack)
    quiet_or_large_shock["beta_state_indicator"] = [
        {"selection_scope": "quiet_or_large_shock"}
    ]
    mutations.append(quiet_or_large_shock)
    forward = copy.deepcopy(pack)
    forward["tdc_empirical_beta_path"].append(
        {
            "period": "2026",
            "beta": "0.342",
            "regime_label": "forward",
            "input_basis_label": "forbidden_forward_mapping",
            "rationale": "test mutation",
        }
    )
    mutations.append(forward)
    for mutated in mutations:
        selector_check = next(
            row
            for row in v1_module._validate_tdc_beta_authority(mutated)
            if row["check_id"] == "T25_tdc_beta_no_selector"
        )
        assert selector_check["status"] == "fail"

    missing_empirical = copy.deepcopy(pack)
    del missing_empirical["tdc_empirical_beta_path"]
    required_check = next(
        row for row in v1_module.validate_pack(missing_empirical) if row["check_id"] == "T25_files"
    )
    assert required_check["status"] == "fail"


def test_tdc_beta_is_structural_and_invariant_to_flow_size() -> None:
    pack = v1_module._effective_pack(v1_module._load_pack(PACK_DIR), True, True)
    expected = Decimal("0.20")

    assert v1_module._tdc_implied_beta(pack, "base") == expected
    for flow in (Decimal("1"), Decimal("52.3"), Decimal("1000"), Decimal("-1000")):
        metrics = v1_module._tdc_metrics_for_period(
            pack,
            "base",
            1,
            flow,
            Decimal("0"),
            True,
        )
        assert metrics["implied_beta"] == expected
        assert metrics["full_level_deposit_rate"] == Decimal("0.035")
        assert metrics["new_created_deposits_bil"] == flow * expected
        assert metrics["created_deposit_stock_bil"] == flow * expected
        assert metrics["created_deposit_income_bil"] == (
            metrics["created_deposit_stock_bil"]
            * metrics["full_level_deposit_rate"]
        )
