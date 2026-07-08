from __future__ import annotations

import csv
from decimal import Decimal
from io import StringIO
from pathlib import Path

from ratewall.rwtam.fed_pnl import (
    OPENING_DEFERRED_ASSET_BASE_BIL,
    build_fed_pnl_dynamic_experiment,
    simulate_forward_paired_path,
    write_fed_pnl_outputs,
)
from ratewall.rwtam.v1 import _effective_pack, _load_pack, build_v1


PACK_DIR = Path("configs/rwtam/packs")
GOLDEN_WAVE8_DIR = Path("tests/fixtures/rwtam/golden_wave8")


def test_fed_pnl_dynamic_invariants_and_base_check_against(tmp_path: Path) -> None:
    result = build_fed_pnl_dynamic_experiment(PACK_DIR, output_root=tmp_path)

    assert {row["status"] for row in result.rows("out_fed_pnl_invariant_check")} == {"pass"}
    assert {row["status"] for row in result.rows("out_fed_pnl_funding_regime_invariant_check")} == {"pass"}
    rows = result.rows("out_fed_pnl_dynamic")
    base_year1 = _delta_row(rows, "base", "persistent_level", "year1_2026")
    base_cum = _delta_row(rows, "base", "persistent_level", "persistent_120m")

    assert Decimal(base_year1["delta_RW_ratio"]) == Decimal("0")
    assert Decimal(base_cum["delta_RW_ratio"]) == Decimal("0.00002056090412601559319312388")
    assert Decimal(base_cum["ricardian_0_delta_RW"]) == Decimal("0.00002056090412601559319312388")
    assert Decimal(base_cum["ricardian_0_2_delta_RW"]) < 0
    assert Decimal(base_cum["ricardian_0_5_delta_RW"]) < Decimal(base_cum["ricardian_0_2_delta_RW"])
    assert Decimal(base_cum["ricardian_0_2_delta_RW"]) == Decimal("-0.00029749158990862676771621045")
    assert Decimal(base_cum["ricardian_0_5_delta_RW"]) == Decimal("-0.00052477974981001114664558716")
    assert Decimal(base_cum["issuance_loop_input_bil"]) == -Decimal(base_cum["dynamic_public_effect_bil"])
    assert Decimal(base_cum["issuance_loop_delta_N_bil"]) == Decimal("0.0434066562926432679845965")
    assert Decimal(base_cum["issuance_loop_delta_D_bil"]) == Decimal("-0.015414179793587030563807")
    assert base_cum["public_budget_anticipation_sensitivity"] == "0"
    assert base_cum["government_revenue_doctrine"] == (
        "private_counterpart_plus_financing_closure; "
        "intra_government_transfers_zero_direct_demand_weight; "
        "deficit_effects_via_issuance_loop"
    )
    assert base_cum["doctrine_lineage"] == "public_revenue_closure_rule_20260705"
    assert base_cum["baseline_resumption_month"] == "2033-07"
    assert base_cum["shocked_resumption_month"] == "not_within_120m"
    assert Decimal(base_cum["dynamic_public_effect_bil"]) == Decimal(base_cum["resumption_timing_effect_bil"])
    assert base_cum["level_effect_bil"] == ""
    assert base_cum["residual_effect_bil"] == ""
    assert base_cum["decomposition_disposition"] == "timing_assertion_pass_independent_monthly_path"

    structural = [
        row
        for row in rows
        if row["row_type"] == "structural_non_identifiability"
        and row["band"] == "base"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == "persistent_120m"
    ][0]
    assert structural["level_identifiable_month_count"] == "0"
    assert structural["decomposition_disposition"] == (
        "structural_non_identifiability_shocked_never_resumes_in_horizon"
    )
    assert "FPNL5" in {row["check_id"] for row in result.rows("out_fed_pnl_invariant_check")}

    paths = write_fed_pnl_outputs(result, tmp_path / "written")
    assert paths["out_fed_pnl_dynamic"].exists()


def test_fed_pnl_treasury_funded_regime_and_overdraft_pins(tmp_path: Path) -> None:
    result = build_fed_pnl_dynamic_experiment(PACK_DIR, output_root=tmp_path)
    rows = result.rows("out_fed_pnl_funding_regime_delta")

    base_year1_zero = _funded_compare_row(rows, "year1_2026", "0")
    assert Decimal(base_year1_zero["self_cure_public_effect_bil"]) == Decimal("0")
    assert Decimal(base_year1_zero["treasury_funded_public_effect_bil"]) == Decimal(
        "-32.37602566666666666666666666"
    )
    assert Decimal(base_year1_zero["funded_minus_self_cure_delta_RW_ratio"]) == Decimal(
        "0.00004132043615499554969352803"
    )
    assert Decimal(base_year1_zero["loop_only_delta_N_bil"]) > 0
    assert Decimal(base_year1_zero["loop_only_delta_D_bil"]) < 0
    assert base_year1_zero["decomposition_disposition"] == (
        "structural_non_identifiability_self_cure_shocked_never_resumes_in_horizon"
    )

    base_cum_zero = _funded_compare_row(rows, "persistent_120m", "0")
    assert Decimal(base_cum_zero["self_cure_public_effect_bil"]) == Decimal("-76.385")
    assert Decimal(base_cum_zero["treasury_funded_public_effect_bil"]) == Decimal(
        "-280.8946966666666666666666667"
    )
    assert Decimal(base_cum_zero["level_effect_bil"]) == Decimal(
        "-204.5096966666666666666666667"
    )
    assert Decimal(base_cum_zero["funded_minus_self_cure_delta_RW_ratio"]) == Decimal(
        "0.00034969040650149261205525932"
    )
    assert Decimal(base_cum_zero["loop_only_delta_N_bil"]) == Decimal(
        "0.7794349734312059672514427"
    )
    assert Decimal(base_cum_zero["loop_only_delta_D_bil"]) == Decimal(
        "-0.3130385203792946863082311"
    )
    assert base_cum_zero["baseline_resumption_month"] == "2026-01"
    assert base_cum_zero["shocked_resumption_month"] == "2027-10"
    assert base_cum_zero["self_cure_baseline_resumption_month"] == "2033-07"
    assert base_cum_zero["self_cure_shocked_resumption_month"] == "not_within_120m"

    base_cum_half = _funded_compare_row(rows, "persistent_120m", "0.5")
    assert Decimal(base_cum_half["funded_minus_self_cure_delta_RW_ratio"]) == Decimal(
        "-0.00121758906146584383557279965"
    )
    assert Decimal(base_cum_half["converted_public_effect_bil"]) == Decimal(
        "-140.4473483333333333333333334"
    )

    overdraft = next(
        row
        for row in rows
        if row["row_type"] == "financing_variant"
        and row["band"] == "base"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == "persistent_120m"
        and row["financing_mode"] == "overdraft_indemnity"
    )
    assert Decimal(overdraft["off_RW_ratio"]) == Decimal(
        "0.05926472473321265409138702249"
    )
    assert Decimal(overdraft["treasury_funded_on_RW_ratio"]) == Decimal(
        "0.05926472473321265409138702249"
    )
    assert Decimal(overdraft["funded_minus_self_cure_delta_RW_ratio"]) == Decimal(
        "-0.00002056090412601559319312388"
    )
    assert Decimal(overdraft["issuance_loop_input_bil"]) == Decimal("0")
    assert "no marketable-issuance loop for the funded flow" in overdraft["memo"]
    assert "no Treasury overdraft authority" in overdraft["memo"]
    assert overdraft["government_revenue_doctrine"] == (
        "private_counterpart_plus_financing_closure; "
        "intra_government_transfers_zero_direct_demand_weight; "
        "deficit_effects_via_issuance_loop"
    )


def test_fed_pnl_overdraft_variant_is_engine_loop_off_funded_run(tmp_path: Path) -> None:
    result = build_fed_pnl_dynamic_experiment(PACK_DIR, output_root=tmp_path)
    rows = result.rows("out_fed_pnl_funding_regime_delta")

    year1 = _financing_variant_row(rows, "year1_2026")
    assert year1["treasury_funded_on_RW_ratio"] == year1["off_RW_ratio"]
    assert year1["loop_on_RW_ratio"] == year1["off_RW_ratio"]
    assert year1["on_RW_ratio"] == year1["off_RW_ratio"]
    assert Decimal(year1["funded_minus_self_cure_delta_RW_ratio"]) == Decimal("0")
    assert Decimal(year1["issuance_loop_input_bil"]) == Decimal("0")
    assert Decimal(year1["issuance_loop_delta_N_bil"]) == Decimal("0")
    assert Decimal(year1["issuance_loop_delta_D_bil"]) == Decimal("0")

    cumulative = _financing_variant_row(rows, "persistent_120m")
    assert cumulative["treasury_funded_on_RW_ratio"] == cumulative["off_RW_ratio"]
    assert cumulative["loop_on_RW_ratio"] == cumulative["off_RW_ratio"]
    assert cumulative["on_RW_ratio"] == cumulative["off_RW_ratio"]
    assert Decimal(cumulative["off_RW_ratio"]) == Decimal(
        "0.05926472473321265409138702249"
    )
    assert Decimal(cumulative["funded_minus_self_cure_delta_RW_ratio"]) == Decimal(
        "-0.00002056090412601559319312388"
    )
    assert Decimal(cumulative["issuance_loop_input_bil"]) == Decimal("0")
    assert Decimal(cumulative["issuance_loop_delta_N_bil"]) == Decimal("0")
    assert Decimal(cumulative["issuance_loop_delta_D_bil"]) == Decimal("0")


def test_fed_pnl_overdraft_delta_matches_negative_self_cure_loop_effect(
    tmp_path: Path,
) -> None:
    result = build_fed_pnl_dynamic_experiment(PACK_DIR, output_root=tmp_path)
    rows = result.rows("out_fed_pnl_funding_regime_delta")
    self_cure_by_key = {
        (row["band"], row["dose_mode"], row["horizon_id"]): row
        for row in rows
        if row["row_type"] == "funding_regime_delta"
        and row["funding_regime"] == "self_cure"
        and row["financing_mode"] == "marketable_issuance"
        and row["public_budget_anticipation_sensitivity"] == "0"
    }

    for overdraft in (
        row
        for row in rows
        if row["row_type"] == "financing_variant"
        and row["financing_mode"] == "overdraft_indemnity"
    ):
        self_cure = self_cure_by_key[
            (overdraft["band"], overdraft["dose_mode"], overdraft["horizon_id"])
        ]
        assert Decimal(overdraft["funded_minus_self_cure_delta_RW_ratio"]) == -Decimal(
            self_cure["delta_RW_ratio"]
        )
        assert Decimal(overdraft["funded_minus_self_cure_delta_RW_ratio"]) == (
            Decimal(overdraft["treasury_funded_on_RW_ratio"])
            - Decimal(overdraft["self_cure_on_RW_ratio"])
        )


def test_fed_pnl_opening_da_probe_and_income_identity() -> None:
    pack = _effective_pack(_load_pack(PACK_DIR), True, True)
    default = simulate_forward_paired_path(
        pack,
        band="base",
        dose_mode="persistent_level",
        opening_deferred_asset_bil=OPENING_DEFERRED_ASSET_BASE_BIL,
    )
    mutated = simulate_forward_paired_path(
        pack,
        band="base",
        dose_mode="persistent_level",
        opening_deferred_asset_bil=Decimal("25"),
    )

    assert _resumption_month(default, "baseline") != _resumption_month(mutated, "baseline")
    for row in default:
        for prefix in ("baseline", "shocked"):
            positive = max(Decimal("0"), Decimal(row[f"{prefix}_net_income_bil"]))
            paydown = Decimal(row[f"{prefix}_paydown_bil"])
            remittance = Decimal(row[f"{prefix}_remittance_bil"])
            assert paydown + remittance == positive
            assert Decimal(row[f"{prefix}_deferred_asset_end_bil"]) >= 0


def test_fed_pnl_scenario_keeps_default_wave8_rollup_byte_stable(tmp_path: Path) -> None:
    build_fed_pnl_dynamic_experiment(PACK_DIR, output_root=tmp_path)
    result = build_v1(PACK_DIR)
    expected_rows = list(
        csv.DictReader(
            StringIO((GOLDEN_WAVE8_DIR / "out_ratewall_rollup.csv").read_text(encoding="utf-8"))
        )
    )

    assert result.rows("out_ratewall_rollup") == expected_rows


def test_fed_pnl_backcast_scores_are_emitted_with_no_fit_policy(tmp_path: Path) -> None:
    result = build_fed_pnl_dynamic_experiment(PACK_DIR, output_root=tmp_path)
    scores = [row for row in result.rows("out_fed_pnl_dynamic") if row["row_type"] == "backcast_score"]
    monthly = result.rows("out_fed_pnl_backcast_monthly")

    assert scores
    assert {row["period"] for row in scores} >= {"2022", "2023", "2024"}
    assert all(row["no_fit_policy"] == "no_coefficients_or_mixes_adjusted_to_targets" for row in scores)
    assert monthly[0]["soma_treasury_open_bil"] == "5728.9"
    assert monthly[0]["soma_mbs_open_bil"] == "2683.8"
    assert monthly[0]["reserves_open_bil"] == "3853.1"
    assert monthly[0]["on_rrp_open_bil"] == "1600"
    assert monthly[0]["soma_avg_yield"] == "0.0215"
    assert monthly[-1]["soma_treasury_open_bil"] == "4336.7"
    assert monthly[-1]["on_rrp_open_bil"] == "200"
    assert any(
        row["backcast_metric"] == "public_cost"
        and Decimal(row["predicted_value_bil"]) != Decimal("0")
        for row in scores
    )


def _delta_row(rows: list[dict[str, str]], band: str, dose_mode: str, horizon_id: str) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row["row_type"] == "delta_rw"
        and row["band"] == band
        and row["dose_mode"] == dose_mode
        and row["horizon_id"] == horizon_id
    )


def _funded_compare_row(
    rows: list[dict[str, str]],
    horizon_id: str,
    sensitivity: str,
) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row["row_type"] == "funded_minus_self_cure_delta"
        and row["band"] == "base"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == horizon_id
        and row["public_budget_anticipation_sensitivity"] == sensitivity
    )


def _financing_variant_row(
    rows: list[dict[str, str]],
    horizon_id: str,
) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row["row_type"] == "financing_variant"
        and row["band"] == "base"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == horizon_id
        and row["financing_mode"] == "overdraft_indemnity"
    )


def _resumption_month(rows: list[dict[str, Decimal | str]], prefix: str) -> str:
    field = f"{prefix}_remittance_bil"
    for row in rows:
        if Decimal(row[field]) > 0:
            return str(row["month"])
    return "not_within_120m"
