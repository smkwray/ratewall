from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ratewall.rwtas.mechanisms import (
    build_mechanism_wave,
    _scale_holder_stress_shock_row,
    validate_holder_stress_overlap_rows,
    write_mechanism_wave_outputs,
)
from ratewall.rwtas.scenarios import build_crossing_shock_sweep
from ratewall.rwtas.reissuance_policy import build_reissuance_policy_scenarios
from ratewall.rwtas.v1 import build_v1


PACK_DIR = Path("configs/rwtas/packs")


def test_m0_reissuance_base_self_rolls_bills_and_scenarios_diverge() -> None:
    results = build_reissuance_policy_scenarios(PACK_DIR)
    base = results["base"].rows("out_reissuance_composition_path")
    bill_heavy = results["bill_heavy"].rows("out_reissuance_composition_path")
    coupon_heavy = results["coupon_heavy"].rows("out_reissuance_composition_path")

    base_start = Decimal(base[0]["bill_share_start"])
    base_end = Decimal(base[-1]["bill_share_end"])
    assert abs(base_end - base_start) < Decimal("0.02")
    assert Decimal(bill_heavy[-1]["policy_bill_share"]) == Decimal("0.45")
    assert Decimal(bill_heavy[-1]["bill_share_end"]) > base_end
    assert Decimal(coupon_heavy[-1]["bill_share_end"]) < base_start

    checks = {row["check_id"]: row["status"] for row in results["base"].rows("out_reissuance_invariant_check")}
    assert checks["RP3_base_headline_byte_regression"] == "pass"
    assert checks["RP5_base_bill_share_drift_lt_2pp"] == "pass"

    divergence = results["base"].rows("out_reissuance_divergence_vs_base")
    spread = next(
        row
        for row in divergence
        if row["scenario"] == "bill_heavy_minus_coupon_heavy" and row["horizon"] == "year_10"
    )
    assert Decimal(spread["delta_government_interest_bil_vs_base"]) > Decimal("42")
    assert Decimal(spread["delta_RW_ratio_vs_base"]) > Decimal("0.024")


def test_mechanism_wave_isolated_placeholders_and_overlap_probe(tmp_path: Path) -> None:
    result = build_mechanism_wave(PACK_DIR)

    checks = {row["check_id"]: row["status"] for row in result.rows("out_mechanism_invariant_check")}
    assert set(checks.values()) == {"pass"}
    assert checks["T55_mechanism_outputs_isolated"] == "pass"
    assert checks["T45_base_headline_byte_unchanged"] == "pass"
    assert checks["M1_holder_mtm_overlap_probe_fails"] == "pass"

    placeholders = result.rows("out_mechanism_placeholder_rows")
    assert placeholders
    assert "false" in {row["owner_assumption_mode"] for row in placeholders}
    assert any(
        row["placeholder_flag"].startswith("CALIBRATED_")
        for row in placeholders
    )
    assert {row["include_flag"] for row in placeholders} == {"0"}

    paths = write_mechanism_wave_outputs(result, tmp_path)
    assert paths["out_holder_stress_ledger"].exists()
    assert paths["out_inflation_overlay_diagnostic"].exists()


def test_holder_stress_duplicate_bond_mtm_key_is_rejected() -> None:
    result = build_mechanism_wave(PACK_DIR)
    bond = build_v1(PACK_DIR).rows("out_bond_mtm_diagnostic")
    probe = [dict(result.rows("out_holder_stress_ledger")[0], mtm_overlap_key=bond[0]["exposure_id"])]

    errors = validate_holder_stress_overlap_rows(probe, bond)
    assert errors


def test_bank_tier1_current_ratio_scaling_is_config_backed() -> None:
    parameters = [
        {
            "parameter_id": "holder_stress_ratio",
            "cell_or_sector": "holder=banks|regulatory=FDIC_insured",
            "instrument_family": "current_unrealized_loss_to_tier1",
            "low": "0.2",
            "base": "0.2",
            "high": "0.2",
        }
    ]
    scaled = _scale_holder_stress_shock_row(
        {
            "holder_class": "banks",
            "metric": "current+incremental MTM loss / Tier1 RBC",
            "low": "0.4",
            "base": "0.5",
            "high": "0.6",
        },
        Decimal("0"),
        parameters,
    )

    assert scaled["low"] == scaled["base"] == scaled["high"] == "0.2"


def test_dsr_dispersion_desynchronizes_crossings_and_inflation_overlay_emits_policy_metric() -> None:
    result = build_mechanism_wave(PACK_DIR)
    crossings = result.rows("out_dsr_dispersion_crossing_profile")
    assert {row["crossing_profile"] for row in crossings} == {
        "threshold_exceedance_share_grid_pack"
    }
    for column in [
        "baseline_share_above_threshold",
        "shocked_share",
        "incremental_share",
        "distribution_bucket",
    ]:
        assert all(column in row for row in crossings)
    assert all(row["distribution_bucket"] == "percentile_bucket_grid" for row in crossings)
    assert any(Decimal(row["incremental_share"]) > Decimal("0") for row in crossings)
    assert any(row["minimum_static_hold_shock_bp_share_ge_50"] for row in crossings)

    response = result.rows("out_episode_response_form_comparison")
    assert any(Decimal(row["selected_response_bil"]) < Decimal(row["linear_response_bil"]) for row in response)

    migration = result.rows("out_endogenous_financialization_migration_path")
    assert Decimal(migration[-1]["migration_share_base"]) > Decimal("0")
    assert any(Decimal(row["N_effect_base_bil"]) > Decimal("0") for row in migration)

    inflation = result.rows("out_inflation_overlay_diagnostic")
    assert {row["shock_bp"] for row in inflation} == {"100", "300"}
    assert all(Decimal(row["wall_attenuation_pp_per_100bp"]) > Decimal("0") for row in inflation)


def test_distress_crossing_sweep_exposes_incremental_shares_and_10bp_label() -> None:
    rows = build_crossing_shock_sweep(PACK_DIR)

    assert rows
    for column in [
        "baseline_share_above_threshold",
        "shocked_share",
        "incremental_share",
        "distribution_bucket",
    ]:
        assert all(column in row for row in rows)
    assert all(row["distribution_bucket"] == "percentile_bucket_grid" for row in rows)
    assert any(Decimal(row["incremental_share"]) > Decimal("0") for row in rows)
    assert all("10" in row["shock_sweep_bp"].split(";") for row in rows)
