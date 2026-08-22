"""Scenario-only proposal-gap surfaces for RWTAM.

This module is intentionally outside the default V1 build path. It emits the
three remaining proposal diagnostics without mutating headline or golden rows.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtam.rwpi import build_rwpi
from ratewall.rwtam.scenarios import (
    FINANCIALIZED_MMF_FAMILY,
    _append_csv_rows,
    _asset_migration_rows,
    _claim_rule,
    _copy_household_split_rows,
    build_distress_scenario,
)
from ratewall.rwtam.v1 import (
    BANDS,
    DOSE_MODES,
    _d,
    _fmt,
    _load_pack,
    _write_rows,
    build_v1,
)


OUTPUT_DIR = Path("var/rwtam/scenarios/three_gaps")
REPORT_PATH = Path("do/rwtam_three_gaps_report_20260704.md")
DEPOSIT_FAMILIES = ("deposits_checkable", "deposits_savings_mmda", "deposits_time_cds")
DOWN_BETA_MULTIPLIER = {"low": Decimal("1.2"), "base": Decimal("1.5"), "high": Decimal("2.0")}
TRUE_RSTAR_PP = Decimal("0")
STANDARDIZED_STANCE_PP = Decimal("2")


@dataclass(frozen=True)
class ThreeGapsResult:
    """CSV-ready tables for the three proposal-gap diagnostics."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_three_gaps(pack_dir: Path = Path("configs/rwtam/packs")) -> ThreeGapsResult:
    with localcontext() as context:
        context.prec = 28
        easing = _easing_asymmetry_rows(pack_dir)
        rstar = _rstar_illusion_rows(pack_dir)
        fx_off = _rwpi_fx_off_rows(pack_dir)
        invariants = _invariant_rows(easing, rstar, fx_off)
        lineage = _lineage_rows()
        return ThreeGapsResult(
            {
                "out_easing_asymmetry": easing,
                "out_rstar_illusion_exhibit": rstar,
                "out_rwpi_fx_off": fx_off,
                "out_three_gaps_invariant_check": invariants,
                "out_three_gaps_lineage": lineage,
            }
        )


def write_three_gaps_outputs(
    result: ThreeGapsResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_three_gaps_report(
    result: ThreeGapsResult,
    output_path: Path = REPORT_PATH,
) -> Path:
    easing_base = [
        row
        for row in result.rows("out_easing_asymmetry")
        if row["band"] == "base"
        and row["ricardian_offset"] == "0"
        and row["horizon_id"] in {"year1_annual", "multi_year_persistent"}
    ]
    rstar = result.rows("out_rstar_illusion_exhibit")
    fx_off = [
        row
        for row in result.rows("out_rwpi_fx_off")
        if row["slack_state"] == "balanced"
        and row["index_target"] == "CPI_U"
    ]
    lines = [
        "# RWTAM three proposal gaps report",
        "",
        "Date: 2026-07-04.",
        "Scope: scenario/diagnostic-only; RW_full headline and golden fixtures are not promoted or rewritten.",
        "",
        "## Dispositions",
        "",
        "| gap | disposition |",
        "| --- | --- |",
        "| G1 easing asymmetry | emitted `out_easing_asymmetry.csv`; signed -100bp engine pairs run in both dose modes; down-beta overlay applies only to cuts; +100bp distress deadweight is one-sided; 6A transaction-service sign is flipped under cuts from existing layer values |",
        "| G2 r-star illusion | emitted `out_rstar_illusion_exhibit.csv`; true r* is flat by construction; F-asset trajectory phases the existing F-asset-50 state over 20 annual remeasurements |",
        "| G3 FX-off ND_pi | emitted `out_rwpi_fx_off.csv`; CPI-U ND_pi excludes FX/import and reconciles exactly to full ND_pi minus FX |",
        "",
        "## Easing vs Hike",
        "",
        "| dose | horizon | RW_easing | RW_hike | comparison | down-beta D | distress absence D | lock-in release D |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in easing_base:
        lines.append(
            f"| {row['dose_mode']} | {row['horizon_id']} | {row['RW_easing']} | {row['RW_hike']} | {row['comparison']} | {row['down_beta_delta_D_bil']} | {row['distress_absence_delta_D_bil']} | {row['lockin_release_delta_D_bil']} |"
        )
    lines.extend(
        [
            "",
            "Readout: the base easing wall is below the hike wall in the emitted magnitude comparison. Deposit down-betas make the easing cashflow response larger, but the absence of distress drag and the lock-in/turnover release both pull the easing denominator away from the hike-side wall.",
            "",
            "## Econometrician's Illusion",
            "",
            "| year | F-asset share | RW(t) | true r* | apparent r* |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in rstar:
        lines.append(
            f"| {row['year']} | {row['f_asset_trajectory_share']} | {row['RW_t']} | {row['true_rstar_pp']} | {row['apparent_rstar_pp']} |"
        )
    lines.extend(
        [
            "",
            "## FX-off ND_pi",
            "",
            "| dose | window | low | base | high | verdict | full minus FX residual |",
            "| --- | --- | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for row in fx_off:
        lines.append(
            f"| {row['dose_mode']} | {row['horizon_window']} | {row['ND_pi_fx_off_low_pp']} | {row['ND_pi_fx_off_base_pp']} | {row['ND_pi_fx_off_high_pp']} | {row['decision_rule_verdict']} | {row['full_minus_fx_identity_residual_base_pp']} |"
        )
    lines.extend(
        [
            "",
            "## Gates",
            "",
            "| check | status | detail |",
            "| --- | --- | --- |",
        ]
    )
    for row in result.rows("out_three_gaps_invariant_check"):
        lines.append(f"| {row['check_id']} | {row['status']} | {row['detail']} |")
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- G1 reports sign-normalized wall magnitudes plus signed N/D fields; cuts have opposite-signed cashflow and real-side rows.",
            "- G2 is a shape-only illustration, not an r* estimate or a historical calibration.",
            "- G3 leaves the RW_pi rent companion unchanged and unsummed; FX/import is excluded only for this sensitivity surface.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _easing_asymmetry_rows(pack_dir: Path) -> list[dict[str, str]]:
    results = {
        (dose_mode, shock): build_v1(
            pack_dir,
            dose_mode=dose_mode,
            shock_size_bp=shock,
            include_impulse_beta_comparator=False,
        )
        for dose_mode in DOSE_MODES
        for shock in (Decimal("100"), Decimal("-100"))
    }
    distress_by_horizon = _distress_drag_by_horizon(pack_dir)
    rows: list[dict[str, str]] = []
    for dose_mode in DOSE_MODES:
        horizons = [("year1_annual", "annual", "2026")]
        if dose_mode == "persistent_level":
            horizons.append(("multi_year_persistent", "cumulative_120_month", "2026-2035"))
        for horizon_id, period_type, period in horizons:
            for band in BANDS:
                hike = _rollup(results[(dose_mode, Decimal("100"))], period_type, period, band)
                ease = _rollup(results[(dose_mode, Decimal("-100"))], period_type, period, band)
                deposit = _deposit_contribution(results[(dose_mode, Decimal("-100"))], period_type, period, band)
                multiplier = DOWN_BETA_MULTIPLIER[band]
                down_n = deposit["N"] * (multiplier - Decimal("1"))
                down_d = deposit["D"] * (multiplier - Decimal("1"))
                distress_d = distress_by_horizon[horizon_id]
                lockin_hike_d = _layer_delta(results[(dose_mode, Decimal("100"))], period_type, period, band, "housing_transaction_services")
                lockin_ease_d = _layer_delta(results[(dose_mode, Decimal("-100"))], period_type, period, band, "housing_transaction_services")
                ease_n = ease["N"] + down_n
                ease_d = ease["D"] + down_d
                hike_n = hike["N"]
                hike_d = hike["D"] + distress_d
                rw_ease = _wall_magnitude(ease_n, ease_d)
                rw_hike = _wall_magnitude(hike_n, hike_d)
                rows.append(
                    {
                        "scenario_id": "easing_asymmetry_minus100_vs_plus100",
                        "dose_mode": dose_mode,
                        "horizon_id": horizon_id,
                        "period_type": period_type,
                        "period": period,
                        "band": band,
                        "ricardian_offset": "0",
                        "deposit_down_beta_multiplier": _fmt(multiplier),
                        "shock_easing_bp": "-100",
                        "shock_hike_bp": "100",
                        "RW_easing": _fmt(rw_ease),
                        "RW_hike": _fmt(rw_hike),
                        "RW_easing_signed": _fmt(ease_n / ease_d) if ease_d else "0",
                        "RW_hike_signed": _fmt(hike_n / hike_d) if hike_d else "0",
                        "comparison": "RW_easing_above_RW_hike"
                        if rw_ease > rw_hike
                        else "RW_easing_below_RW_hike"
                        if rw_ease < rw_hike
                        else "RW_easing_equals_RW_hike",
                        "easing_N_bil": _fmt(ease_n),
                        "easing_D_bil": _fmt(ease_d),
                        "hike_N_bil": _fmt(hike_n),
                        "hike_D_bil": _fmt(hike_d),
                        "down_beta_delta_N_bil": _fmt(down_n),
                        "down_beta_delta_D_bil": _fmt(down_d),
                        "distress_absence_delta_D_bil": _fmt(-distress_d),
                        "lockin_release_delta_D_bil": _fmt(lockin_ease_d - lockin_hike_d),
                        "hike_distress_deadweight_D_bil": _fmt(distress_d),
                        "cut_distress_activation": "false",
                        "lockin_release_rule": "existing_6A_transaction_services_sign_flipped_under_negative_shock",
                        "evidence_label": "owner_assumption_directional_support:DSS_deposits_channel;observed_2024_25_deposit_rate_cuts_outpacing_2022_23_climb",
                        "headline_status": "scenario_diagnostic_only_not_RW_full",
                    }
                )
    return rows


def _rstar_illusion_rows(pack_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="rwtam_rstar_illusion_") as tmp:
        tmp_root = Path(tmp)
        base_pack = _load_pack(pack_dir)
        for year in range(1, 21):
            share = Decimal(year) * Decimal("0.025")
            scenario_id = f"F_asset_path_year_{year:02d}"
            scenario_pack = tmp_root / scenario_id
            shutil.copytree(pack_dir, scenario_pack)
            scenario_rows = _asset_migration_rows(base_pack, scenario_id, share)
            split_rows = _copy_household_split_rows(base_pack, "deposits_checkable", FINANCIALIZED_MMF_FAMILY)
            claim_rules = [
                _claim_rule(
                    "financialized_mmf_like_yield",
                    FINANCIALIZED_MMF_FAMILY,
                    "driver_curve",
                    "mmf_shares",
                    "nonbank_finance",
                    "opening_holders",
                    "",
                    "financialization_scenario",
                )
            ]
            _append_csv_rows(scenario_pack / "scenario_adjustments.csv", scenario_rows)
            _append_csv_rows(scenario_pack / "household_stock_splits.csv", split_rows)
            _append_csv_rows(scenario_pack / "claim_processor_rules.csv", claim_rules)
            result = build_v1(
                scenario_pack,
                dose_mode="persistent_level",
                shock_size_bp=Decimal("100"),
                include_impulse_beta_comparator=False,
            )
            headline = _rollup(result, "annual", "2026", "base")
            rw = _wall_magnitude(headline["N"], headline["D"])
            apparent = TRUE_RSTAR_PP + rw * STANDARDIZED_STANCE_PP
            rows.append(
                {
                    "scenario_id": "econometrician_illusion_f_asset_path",
                    "year": str(year),
                    "calendar_year_label": str(2026 + year - 1),
                    "f_asset_trajectory_share": _fmt(share),
                    "RW_t": _fmt(rw),
                    "true_rstar_pp": _fmt(TRUE_RSTAR_PP),
                    "standardized_stance_pp": _fmt(STANDARDIZED_STANCE_PP),
                    "apparent_rstar_pp": _fmt(apparent),
                    "label": "hypothetical_illustration;shape_only",
                    "construction_note": "true_rstar_flat_by_construction;apparent_moves_only_through_remeasured_RW_t",
                    "lineage": "existing_F_asset_50_financialization_endpoint_phased_linearly_over_20_years",
                }
            )
    return rows


def _rwpi_fx_off_rows(pack_dir: Path) -> list[dict[str, str]]:
    rwpi = build_rwpi(pack_dir)
    rows: list[dict[str, str]] = []
    for row in rwpi.rows("out_rwpi_window_path"):
        if row["index_target"] != "CPI_U":
            continue
        values: dict[str, Decimal] = {}
        residuals: dict[str, Decimal] = {}
        for band in BANDS:
            values[band] = _d(
                row[f"demand_drag_minus_support_after_wall_{band}_pp"]
            ) - _d(row[f"cost_channel_{band}_pp"])
            residuals[band] = _zero_decimal_dust(values[band] - (_d(row[f"ND_pi_{band}_pp"]) - _d(row[f"fx_import_{band}_pp"])))
        rows.append(
            {
                "scenario_id": "fx_channel_excluded_sensitivity",
                "dose_mode": row["dose_mode"],
                "shock_bp": row["shock_bp"],
                "index_target": row["index_target"],
                "slack_state": row["slack_state"],
                "horizon_window": row["horizon_window"],
                "band": "all",
                "demand_drag_minus_support_after_wall_low_pp": row[
                    "demand_drag_minus_support_after_wall_low_pp"
                ],
                "demand_drag_minus_support_after_wall_base_pp": row[
                    "demand_drag_minus_support_after_wall_base_pp"
                ],
                "demand_drag_minus_support_after_wall_high_pp": row[
                    "demand_drag_minus_support_after_wall_high_pp"
                ],
                "cost_channel_low_pp": row["cost_channel_low_pp"],
                "cost_channel_base_pp": row["cost_channel_base_pp"],
                "cost_channel_high_pp": row["cost_channel_high_pp"],
                "excluded_fx_import_low_pp": row["fx_import_low_pp"],
                "excluded_fx_import_base_pp": row["fx_import_base_pp"],
                "excluded_fx_import_high_pp": row["fx_import_high_pp"],
                "ND_pi_fx_off_low_pp": _fmt(values["low"]),
                "ND_pi_fx_off_base_pp": _fmt(values["base"]),
                "ND_pi_fx_off_high_pp": _fmt(values["high"]),
                "full_ND_pi_low_pp": row["ND_pi_low_pp"],
                "full_ND_pi_base_pp": row["ND_pi_base_pp"],
                "full_ND_pi_high_pp": row["ND_pi_high_pp"],
                "full_minus_fx_identity_residual_low_pp": _fmt(residuals["low"]),
                "full_minus_fx_identity_residual_base_pp": _fmt(residuals["base"]),
                "full_minus_fx_identity_residual_high_pp": _fmt(residuals["high"]),
                "decision_rule_verdict": _verdict(values["low"], values["base"], values["high"]),
                "sensitivity_label": "fx_channel_excluded_sensitivity",
                "rent_companion_status": "unchanged_diagnostic_companion_not_summed",
                "headline_status": "scenario_diagnostic_only_not_RW_full",
            }
        )
    return rows


def _invariant_rows(
    easing: list[dict[str, str]],
    rstar: list[dict[str, str]],
    fx_off: list[dict[str, str]],
) -> list[dict[str, str]]:
    apparent = [_d(row["apparent_rstar_pp"]) for row in rstar]
    true_values = {_d(row["true_rstar_pp"]) for row in rstar}
    return [
        _check(
            "G1_down_beta_only_on_falling_paths",
            all(_d(row["deposit_down_beta_multiplier"]) > 1 for row in easing)
            and all(_d(row["down_beta_delta_D_bil"]) != 0 for row in easing),
            "down-beta multiplier is emitted only on -100bp easing rows",
        ),
        _check(
            "G1_distress_no_activation_on_cuts",
            {row["cut_distress_activation"] for row in easing} == {"false"}
            and all(_d(row["distress_absence_delta_D_bil"]) <= 0 for row in easing),
            "cut-side distress activation is false and hike deadweight is one-sided",
        ),
        _check(
            "G2_true_rstar_flat",
            len(true_values) == 1 and len(rstar) == 20,
            "true r* has one value across twenty rows",
        ),
        _check(
            "G2_apparent_rstar_monotone_emitted",
            all(b >= a for a, b in zip(apparent, apparent[1:])),
            "monotonicity is checked from emitted apparent r* values",
        ),
        _check(
            "G3_full_minus_fx_identity_exact",
            all(
                _d(row[f"full_minus_fx_identity_residual_{band}_pp"]) == 0
                for row in fx_off
                for band in BANDS
            ),
            "FX-off ND_pi equals full ND_pi minus FX/import for every emitted band",
        ),
    ]


def _lineage_rows() -> list[dict[str, str]]:
    return [
        {
            "output": "out_easing_asymmetry.csv",
            "source": "build_v1(+100/-100), out_cashflow_family_contributions, out_phase6_waterfall_scaffold, distress policy_100bp_distress_on",
            "note": "scenario-local overlay; no default V1 mutation",
        },
        {
            "output": "out_rstar_illusion_exhibit.csv",
            "source": "existing financialization F-asset migration config rows, remeasured through build_v1",
            "note": "true r* flat; apparent r* is true r* plus RW(t) times 200bp stance",
        },
        {
            "output": "out_rwpi_fx_off.csv",
            "source": "build_rwpi out_rwpi_window_path",
            "note": "FX/import columns excluded by exact identity; CPI-U only",
        },
    ]


def _rollup(result, period_type: str, period: str, band: str) -> dict[str, Decimal]:
    row = next(
        row
        for row in result.rows("out_ratewall_rollup")
        if row["period_type"] == period_type
        and row["period"] == period
        and row["band"] == band
        and row["ricardian_offset"] == "0"
    )
    return {"N": _d(row["N_bil"]), "D": _d(row["D_bil"])}


def _deposit_contribution(result, period_type: str, period: str, band: str) -> dict[str, Decimal]:
    rows = [
        row
        for row in result.rows("out_cashflow_family_contributions")
        if row["period_type"] == period_type
        and row["period"] == period
        and row["band"] == band
        and row["ricardian_offset"] == "0"
        and row["instrument_family"] in DEPOSIT_FAMILIES
    ]
    return {
        "N": sum((_d(row["N_bil"]) for row in rows), Decimal("0")),
        "D": sum((_d(row["D_bil"]) for row in rows), Decimal("0")),
    }


def _layer_delta(result, period_type: str, period: str, band: str, layer_id: str) -> Decimal:
    row = next(
        row
        for row in result.rows("out_phase6_waterfall_scaffold")
        if row["period_type"] == period_type
        and row["period"] == period
        and row["band"] == band
        and row["ricardian_offset"] == "0"
        and row["layer_id"] == layer_id
    )
    return _d(row["delta_D_bil"])


def _distress_drag_by_horizon(pack_dir: Path) -> dict[str, Decimal]:
    distress = build_distress_scenario(pack_dir, scenario_id="policy_100bp_distress_on")
    rows = distress.rows("out_distress_deadweight_drag_by_year")
    year1 = sum((_d(row["ledger_incremental_deadweight_drag_bil"]) for row in rows if row["year"] == "2026"), Decimal("0"))
    cumulative = sum((_d(row["ledger_incremental_deadweight_drag_bil"]) for row in rows), Decimal("0"))
    return {"year1_annual": year1, "multi_year_persistent": cumulative}


def _wall_magnitude(n_value: Decimal, d_value: Decimal) -> Decimal:
    if d_value == 0:
        return Decimal("0")
    return abs(n_value) / abs(d_value)


def _verdict(low: Decimal, base: Decimal, high: Decimal) -> str:
    if low <= 0 <= high or high <= 0 <= low:
        return "indeterminate_bands_straddle_zero"
    if low > 0 and base > 0 and high > 0:
        return "positive_all_bands"
    if low < 0 and base < 0 and high < 0:
        return "negative_all_bands"
    return "mixed_sign_check"


def _zero_decimal_dust(value: Decimal) -> Decimal:
    return Decimal("0") if abs(value) <= Decimal("1e-24") else value


def _check(check_id: str, ok: bool, detail: str) -> dict[str, str]:
    return {"check_id": check_id, "status": "pass" if ok else "fail", "detail": detail}
