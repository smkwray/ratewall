"""Promoted credit-deposit coupling for RWTAM.

This module keeps the 6D demand leg diagnostic-only and uses its existing
quantity elasticity only to move the bank-deposit balance-sheet counterpart.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtam.v1 import (
    BANDS,
    CURRENT_DEFAULT_OBJECT_STAMP,
    DEFAULT_DOSE_MODE,
    DOSE_MODES,
    _d,
    _fmt,
    _load_pack,
    _read_csv_rows,
    _write_rows,
    build_v1,
)


EXPERIMENT_ID = "rwtam_credit_deposit_coupling_20260704"
OUTPUT_DIR = Path("var/rwtam/scenarios/credit_deposit_coupling")
REPORT_PATH = Path("do/rwtam_credit_deposit_report_20260704.md")
FIX_REPORT_PATH = Path("do/rwtam_credit_deposit_fix_report_20260704.md")
LABEL = (
    "default_baseline;combined_sinks;credit_deposit_coupling;"
    "assumption_directional_support;credit_stock_deposit_mirror"
)
LEAKAGE_SHARE_BANDS = {
    "low": Decimal("0.10"),
    "base": Decimal("0.25"),
    "high": Decimal("0.45"),
}
BANK_CREDIT_FAMILIES = (
    "c_and_i_depository_loans",
    "cre_mortgages_floating",
    "cre_mortgages_fixed",
)
DEPOSIT_FAMILIES = (
    "deposits_checkable",
    "deposits_savings_mmda",
    "deposits_time_cds",
)
MIGRATION_BASE_FAMILIES = ("deposits_checkable",)
COMPETITION_BETA_STOCK_FAMILIES = ("deposits_savings_mmda", "deposits_time_cds")


@dataclass(frozen=True)
class CreditDepositResult:
    """CSV-ready credit-deposit coupling tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_credit_deposit_coupling_experiment(
    pack_dir: Path = Path("configs/rwtam/packs"),
    *,
    output_root: Path = OUTPUT_DIR,
    shock_size_bp: Decimal = Decimal("100"),
) -> CreditDepositResult:
    """Build ON/OFF and independent ablation rows for the coupling scenario."""

    with localcontext() as context:
        context.prec = 28
        output_root.mkdir(parents=True, exist_ok=True)
        _clear_output_subdirs(output_root)
        base_pack = _load_pack(pack_dir)
        phase6_pack = _load_pack(pack_dir / "phase6")
        deltas = {
            band: _credit_deposit_delta(base_pack, phase6_pack, band, shock_size_bp)
            for band in BANDS
        }
        bank_credit_stocks = {
            band: _bank_credit_stock(base_pack, band)
            for band in BANDS
        }
        off_pack = export_credit_deposit_off_pack(
            pack_dir,
            output_root / "packs" / "coupling_off",
        )
        full_pack = export_credit_deposit_pack(
            pack_dir,
            output_root / "packs" / "coupling_on_full",
            deltas,
            DEPOSIT_FAMILIES,
        )
        migration_pack = export_credit_deposit_pack(
            pack_dir,
            output_root / "packs" / "coupling_on_migration_base",
            deltas,
            MIGRATION_BASE_FAMILIES,
        )
        beta_pack = export_credit_deposit_pack(
            pack_dir,
            output_root / "packs" / "coupling_on_competition_beta_stock",
            deltas,
            COMPETITION_BETA_STOCK_FAMILIES,
        )
        builds: dict[tuple[str, str], object] = {}
        for dose_mode in DOSE_MODES:
            builds[("off", dose_mode)] = build_v1(
                off_pack,
                dose_mode=dose_mode,
                shock_size_bp=shock_size_bp,
                include_impulse_beta_comparator=False,
            )
            builds[("full", dose_mode)] = build_v1(
                full_pack,
                dose_mode=dose_mode,
                shock_size_bp=shock_size_bp,
                include_impulse_beta_comparator=False,
            )
            builds[("migration_base", dose_mode)] = build_v1(
                migration_pack,
                dose_mode=dose_mode,
                shock_size_bp=shock_size_bp,
                include_impulse_beta_comparator=False,
            )
            builds[("competition_beta_stock", dose_mode)] = build_v1(
                beta_pack,
                dose_mode=dose_mode,
                shock_size_bp=shock_size_bp,
                include_impulse_beta_comparator=False,
            )

        cross_builds: dict[tuple[str, str, str], object] = {}
        cross_deltas: dict[tuple[str, str], Decimal] = {}
        for leakage_band in BANDS:
            for elasticity_band in BANDS:
                combo_deltas = {
                    band: _credit_deposit_delta_cross(
                        base_pack,
                        phase6_pack,
                        output_band=band,
                        elasticity_band=elasticity_band,
                        leakage_band=leakage_band,
                        shock_size_bp=shock_size_bp,
                    )
                    for band in BANDS
                }
                cross_deltas[(leakage_band, elasticity_band)] = combo_deltas["base"]
                combo_pack = export_credit_deposit_pack(
                    pack_dir,
                    output_root / "packs" / f"coupling_on_cross_leakage_{leakage_band}_elasticity_{elasticity_band}",
                    combo_deltas,
                    DEPOSIT_FAMILIES,
                )
                for dose_mode in DOSE_MODES:
                    cross_builds[(leakage_band, elasticity_band, dose_mode)] = build_v1(
                        combo_pack,
                        dose_mode=dose_mode,
                        shock_size_bp=shock_size_bp,
                        include_impulse_beta_comparator=False,
                    )

        _write_measurement_rollups(output_root, builds)
        _write_cross_measurement_rollups(output_root, cross_builds)
        table_rows = _coupling_rows(builds, deltas, bank_credit_stocks, output_root)
        band_cross_rows = _band_cross_rows(
            builds,
            cross_builds,
            cross_deltas,
            bank_credit_stocks,
            output_root,
        )
        tables = {
            "out_credit_deposit_coupling": table_rows,
            "out_credit_deposit_band_cross": band_cross_rows,
            "out_credit_deposit_state_path": _state_rows(base_pack, phase6_pack, deltas),
            "out_credit_deposit_invariant_check": _invariant_rows(pack_dir, output_root, builds),
            "out_credit_deposit_lineage": _lineage_rows(output_root),
            "out_credit_deposit_caveats": _caveat_rows(),
        }
        return CreditDepositResult(tables=tables)


def export_credit_deposit_pack(
    pack_dir: Path,
    out_dir: Path,
    deposit_delta_by_band: dict[str, Decimal],
    families: tuple[str, ...] = DEPOSIT_FAMILIES,
) -> Path:
    """Write a scenario pack with bank-issued deposit stocks moved by band."""

    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(pack_dir, out_dir)
    opening_path = out_dir / "opening_stocks.csv"
    rows = _read_csv_rows(opening_path)
    for band, delta in deposit_delta_by_band.items():
        _apply_bank_deposit_delta(rows, band, delta, families)
    _write_rows(opening_path, rows)
    return out_dir


def export_credit_deposit_off_pack(pack_dir: Path, out_dir: Path) -> Path:
    """Write the explicit OFF scenario pack without mutating any input rows."""

    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(pack_dir, out_dir)
    return out_dir


def write_credit_deposit_outputs(
    result: CreditDepositResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_credit_deposit_report(
    result: CreditDepositResult,
    output_path: Path = REPORT_PATH,
) -> Path:
    rows = result.rows("out_credit_deposit_coupling")
    base_persistent = next(
        row
        for row in rows
        if row["band"] == "base"
        and row["dose_mode"] == DEFAULT_DOSE_MODE
        and row["horizon_id"] == "year1_2026"
    )
    finding = (
        "the wall is measured slightly lower once bank credit's deposit counterpart is in the ledger - the credit channel fights the wall on both sides"
        if _d(base_persistent["coupling_delta_RW"]) < 0
        else "the credit-deposit coupling run does not support the hypothesis-form sentence at the base year-1 persistent setting"
    )
    lines = [
        "# RWTAM credit-deposit coupling",
        "",
        "Date: 2026-07-04.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        f"Frame: `{LABEL}`; mechanism default OFF; 6D demand leg remains OFF/diagnostic.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
        "| credit_deposit_coupling | built as scenario-only exported-pack mechanism; default `build_v1` byte path untouched |",
        "| 6D elasticity | promoted only for this balance-sheet mirror; evidence grade and demand-side 6D gate unchanged |",
        "| leakage share | owner-flagged L/B/H `0.10/0.25/0.45`; H.8/Call Report aggregate non-deposit liability mix carried as directional support note |",
        "| deposit route | loan delta moves bank-issued deposit stocks one-for-one less leakage through existing deposit-family machinery |",
        "| ablations | independent pack runs: all deposit families, checkable family only, and savings/CD families only; residual is full minus the two family-subset runs |",
        "| attribution boundary | attribution is by deposit-family subset, not outcome route; the family-subset axis cannot identify a deposit-interest-only outcome route |",
        "| band structure | joint L/B/H rows retained as `joint_band`; separate leakage-by-6D-elasticity cross table emitted around the base output band |",
        "| loan delta | kept as `simplification_static_t0_loan_shift`: a static opening-stock shift from SLOOS x response x shock size, not a per-period paired-run loan path |",
        "| double-count guard | 6D demand leg is OFF in these runs; if enabled later, the same loan delta can legitimately drive spending and interest-income routes as distinct outcomes |",
        "| headline/goldens | OFF/default byte equality asserted in invariant table; no headline fixture refreeze |",
        "",
        f"Finding statement: **{finding}.**",
    ]
    lines.extend(_markdown_table("Delta RW Table", rows))
    lines.extend(_markdown_table("Leakage x 6D Elasticity Cross", result.rows("out_credit_deposit_band_cross")))
    lines.extend(_markdown_table("State Path", result.rows("out_credit_deposit_state_path")))
    lines.extend(_markdown_table("Invariants", result.rows("out_credit_deposit_invariant_check")))
    lines.extend(_markdown_table("Lineage", result.rows("out_credit_deposit_lineage")))
    lines.extend(_markdown_table("Caveats", result.rows("out_credit_deposit_caveats")))
    lines.extend(
        [
            "",
            "## Output Locations",
            "",
            "- `var/rwtam/scenarios/credit_deposit_coupling/out_credit_deposit_coupling.csv`",
            "- `var/rwtam/scenarios/credit_deposit_coupling/out_credit_deposit_band_cross.csv`",
            "- `var/rwtam/scenarios/credit_deposit_coupling/out_credit_deposit_state_path.csv`",
            "- `var/rwtam/scenarios/credit_deposit_coupling/out_credit_deposit_invariant_check.csv`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def write_credit_deposit_fix_report(
    result: CreditDepositResult,
    output_path: Path = FIX_REPORT_PATH,
) -> Path:
    rows = result.rows("out_credit_deposit_coupling")
    base_persistent = next(
        row
        for row in rows
        if row["band"] == "base"
        and row["dose_mode"] == DEFAULT_DOSE_MODE
        and row["horizon_id"] == "year1_2026"
    )
    attribution_rows = [
        {
            "horizon_id": row["horizon_id"],
            "dose_mode": row["dose_mode"],
            "band": row["band"],
            "full_delta_RW": row["coupling_delta_RW"],
            "checkable_families_only_delta_RW": row["checkable_families_only_delta_RW"],
            "savings_cd_families_only_delta_RW": row["savings_cd_families_only_delta_RW"],
            "family_subset_residual_delta_RW": row["family_subset_residual_delta_RW"],
        }
        for row in rows
    ]
    cross_rows = [
        row
        for row in result.rows("out_credit_deposit_band_cross")
        if row["horizon_id"] == "year1_2026" and row["dose_mode"] == DEFAULT_DOSE_MODE
    ]
    lines = [
        "# RWTAM credit-deposit coupling fix report",
        "",
        "Date: 2026-07-04.",
        "",
        "## Dispositions",
        "",
        "| finding | disposition |",
        "| --- | --- |",
        "| attribution honesty | fixed: removed the fabricated deposit-interest leg; family-subset ablations now report checkable-only and savings/CD-only independent runs |",
        "| residual | fixed: residual is `full_delta_RW - checkable_families_only_delta_RW - savings_cd_families_only_delta_RW`; base year-1 persistent residual is `" + base_persistent["family_subset_residual_delta_RW"] + "` |",
        "| identifiability | disclosed: this axis attributes by deposit family, not by outcome route; outcome-route decomposition is not identifiable here |",
        "| band structure | fixed: retained joint rows and emitted the leakage x 6D-elasticity cross table |",
        "| loan delta | kept static with explicit caveat `simplification_static_t0_loan_shift`; no per-period paired-run loan path is claimed |",
        "| tests | focused tests assert the exported OFF path, engine leakage mutation, and the numeric three-run residual |",
    ]
    lines.extend(_markdown_table("Corrected Attribution Table", attribution_rows))
    lines.extend(_markdown_table("Base Persistent Band Cross", cross_rows))
    lines.extend(_markdown_table("Caveats", result.rows("out_credit_deposit_caveats")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _credit_deposit_delta(
    pack: dict[str, list[dict[str, str]]],
    phase6_pack: dict[str, list[dict[str, str]]],
    band: str,
    shock_size_bp: Decimal,
) -> Decimal:
    loan_stock = _bank_credit_stock(pack, band)
    tightening_pp = _phase6_param(
        phase6_pack,
        "credit_supply_sloos_net_tightening_grid",
        band,
    )
    response_per_10pp = _phase6_param(
        phase6_pack,
        "credit_supply_owner_diagnostic_new_lending_quantity_response_per_10pp_sloos",
        band,
    )
    loan_delta = (
        -_sign(shock_size_bp)
        * loan_stock
        * (tightening_pp / Decimal("10"))
        * response_per_10pp
        * (abs(shock_size_bp) / Decimal("100"))
    )
    return loan_delta * (Decimal("1") - LEAKAGE_SHARE_BANDS[band])


def _credit_deposit_delta_cross(
    pack: dict[str, list[dict[str, str]]],
    phase6_pack: dict[str, list[dict[str, str]]],
    *,
    output_band: str,
    elasticity_band: str,
    leakage_band: str,
    shock_size_bp: Decimal,
) -> Decimal:
    loan_stock = _bank_credit_stock(pack, output_band)
    tightening_pp = _phase6_param(
        phase6_pack,
        "credit_supply_sloos_net_tightening_grid",
        elasticity_band,
    )
    response_per_10pp = _phase6_param(
        phase6_pack,
        "credit_supply_owner_diagnostic_new_lending_quantity_response_per_10pp_sloos",
        elasticity_band,
    )
    loan_delta = (
        -_sign(shock_size_bp)
        * loan_stock
        * (tightening_pp / Decimal("10"))
        * response_per_10pp
        * (abs(shock_size_bp) / Decimal("100"))
    )
    return loan_delta * (Decimal("1") - LEAKAGE_SHARE_BANDS[leakage_band])


def _bank_credit_stock(pack: dict[str, list[dict[str, str]]], band: str) -> Decimal:
    total = Decimal("0")
    for row in pack["opening_stocks"]:
        if row["instrument_family"] not in BANK_CREDIT_FAMILIES:
            continue
        if _holder(row) != "banks":
            continue
        total += _d(row[band])
    return total


def _apply_bank_deposit_delta(
    rows: list[dict[str, str]],
    band: str,
    delta: Decimal,
    families: tuple[str, ...],
) -> None:
    targets = [
        row
        for row in rows
        if row["instrument_family"] in families and _issuer(row) == "banks"
    ]
    base = sum(_d(row[band]) for row in targets)
    if base == 0 or delta == 0:
        return
    if delta < 0 and -delta > base:
        delta = -base
    for row in targets:
        old_value = _d(row[band])
        share = Decimal("0") if base == 0 else old_value / base
        row[band] = _fmt(old_value + delta * share)


def _coupling_rows(
    builds: dict[tuple[str, str], object],
    deltas: dict[str, Decimal],
    bank_credit_stocks: dict[str, Decimal],
    output_root: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    horizons = [
        ("year1_2026", "annual", "2026", "transient_12m"),
        ("year1_2026", "annual", "2026", "persistent_level"),
        ("persistent_120m", "cumulative_120_month", "2026-2035", "persistent_level"),
    ]
    for horizon_id, period_type, period, dose_mode in horizons:
        for band in BANDS:
            off = _headline(builds[("off", dose_mode)], period_type, period, band)
            full = _headline(builds[("full", dose_mode)], period_type, period, band)
            checkable = _headline(builds[("migration_base", dose_mode)], period_type, period, band)
            savings_cd = _headline(builds[("competition_beta_stock", dose_mode)], period_type, period, band)
            off_rw = _d(off["cumulative_RW"])
            full_delta = _d(full["cumulative_RW"]) - off_rw
            checkable_delta = _d(checkable["cumulative_RW"]) - off_rw
            savings_cd_delta = _d(savings_cd["cumulative_RW"]) - off_rw
            residual = full_delta - checkable_delta - savings_cd_delta
            rows.append(
                {
                    "experiment_id": EXPERIMENT_ID,
                    "horizon_id": horizon_id,
                    "period_type": period_type,
                    "period": period,
                    "dose_mode": dose_mode,
                    "shock_size_bp": "100",
                    "band_structure": "joint_band",
                    "band": band,
                    "leakage_band": band,
                    "elasticity_band": band,
                    "credit_deposit_coupling": "on",
                    "label": LABEL,
                    "credit_supply_demand_leg": "off_diagnostic_only",
                    "bank_credit_stock_bil": _fmt(bank_credit_stocks[band]),
                    "loan_stock_delta_bil": _fmt(_d(deltas[band]) / (Decimal("1") - LEAKAGE_SHARE_BANDS[band])),
                    "nonbank_funding_leakage_share": _fmt(LEAKAGE_SHARE_BANDS[band]),
                    "deposit_stock_delta_bil": _fmt(deltas[band]),
                    "off_RW": off["cumulative_RW"],
                    "on_RW": full["cumulative_RW"],
                    "coupling_delta_RW": _fmt(full_delta),
                    "coupling_delta_RW_pct_of_off": _fmt(Decimal("0") if off_rw == 0 else full_delta / off_rw),
                    "off_N_bil": off["cumulative_N_bil"],
                    "on_N_bil": full["cumulative_N_bil"],
                    "delta_N_bil": _fmt(_d(full["cumulative_N_bil"]) - _d(off["cumulative_N_bil"])),
                    "off_D_bil": off["cumulative_D_bil"],
                    "on_D_bil": full["cumulative_D_bil"],
                    "delta_D_bil": _fmt(_d(full["cumulative_D_bil"]) - _d(off["cumulative_D_bil"])),
                    "checkable_families_only_delta_RW": _fmt(checkable_delta),
                    "savings_cd_families_only_delta_RW": _fmt(savings_cd_delta),
                    "family_subset_residual_delta_RW": _fmt(residual),
                    "ablation_additivity_assumed": "false",
                    "off_rollup_path": str(output_root / "measurements" / dose_mode / "off" / "out_phase6_waterfall_scaffold.csv"),
                    "on_rollup_path": str(output_root / "measurements" / dose_mode / "full" / "out_phase6_waterfall_scaffold.csv"),
                    "notes": "Attribution is by deposit-family subset, not by outcome route; the same family shift moves deposit interest, migration-base, and beta-base mechanics together.",
                }
            )
    return rows


def _band_cross_rows(
    builds: dict[tuple[str, str], object],
    cross_builds: dict[tuple[str, str, str], object],
    cross_deltas: dict[tuple[str, str], Decimal],
    bank_credit_stocks: dict[str, Decimal],
    output_root: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    horizons = [
        ("year1_2026", "annual", "2026", "transient_12m"),
        ("year1_2026", "annual", "2026", "persistent_level"),
        ("persistent_120m", "cumulative_120_month", "2026-2035", "persistent_level"),
    ]
    output_band = "base"
    for horizon_id, period_type, period, dose_mode in horizons:
        off = _headline(builds[("off", dose_mode)], period_type, period, output_band)
        off_rw = _d(off["cumulative_RW"])
        for leakage_band in BANDS:
            for elasticity_band in BANDS:
                on = _headline(
                    cross_builds[(leakage_band, elasticity_band, dose_mode)],
                    period_type,
                    period,
                    output_band,
                )
                full_delta = _d(on["cumulative_RW"]) - off_rw
                deposit_delta = cross_deltas[(leakage_band, elasticity_band)]
                rows.append(
                    {
                        "experiment_id": EXPERIMENT_ID,
                        "horizon_id": horizon_id,
                        "period_type": period_type,
                        "period": period,
                        "dose_mode": dose_mode,
                        "shock_size_bp": "100",
                        "band_structure": "leakage_elasticity_cross",
                        "output_band": output_band,
                        "leakage_band": leakage_band,
                        "elasticity_band": elasticity_band,
                        "credit_deposit_coupling": "on",
                        "bank_credit_stock_bil": _fmt(bank_credit_stocks[output_band]),
                        "loan_stock_delta_bil": _fmt(
                            deposit_delta / (Decimal("1") - LEAKAGE_SHARE_BANDS[leakage_band])
                        ),
                        "nonbank_funding_leakage_share": _fmt(LEAKAGE_SHARE_BANDS[leakage_band]),
                        "deposit_stock_delta_bil": _fmt(deposit_delta),
                        "off_RW": off["cumulative_RW"],
                        "on_RW": on["cumulative_RW"],
                        "coupling_delta_RW": _fmt(full_delta),
                        "coupling_delta_RW_pct_of_off": _fmt(Decimal("0") if off_rw == 0 else full_delta / off_rw),
                        "off_rollup_path": str(output_root / "measurements" / dose_mode / "off" / "out_phase6_waterfall_scaffold.csv"),
                        "on_rollup_path": str(
                            output_root
                            / "measurements"
                            / dose_mode
                            / f"cross_leakage_{leakage_band}_elasticity_{elasticity_band}"
                            / "out_phase6_waterfall_scaffold.csv"
                        ),
                    }
                )
    return rows


def _state_rows(
    pack: dict[str, list[dict[str, str]]],
    phase6_pack: dict[str, list[dict[str, str]]],
    deltas: dict[str, Decimal],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for band in BANDS:
        tightening = _phase6_param(phase6_pack, "credit_supply_sloos_net_tightening_grid", band)
        response = _phase6_param(
            phase6_pack,
            "credit_supply_owner_diagnostic_new_lending_quantity_response_per_10pp_sloos",
            band,
        )
        loan_delta = deltas[band] / (Decimal("1") - LEAKAGE_SHARE_BANDS[band])
        rows.append(
            {
                "experiment_id": EXPERIMENT_ID,
                "band": band,
                "credit_supply_demand_leg": "off_diagnostic_only",
                "promoted_elasticity_scope": "credit_deposit_coupling_only",
                "bank_credit_stock_bil": _fmt(_bank_credit_stock(pack, band)),
                "sloos_net_tightening_pp": _fmt(tightening),
                "loan_quantity_response_per_10pp_sloos": _fmt(response),
                "loan_stock_delta_bil": _fmt(loan_delta),
                "nonbank_funding_leakage_share": _fmt(LEAKAGE_SHARE_BANDS[band]),
                "deposit_stock_delta_bil": _fmt(deltas[band]),
                "deposit_allocation_rule": "pro_rata_existing_bank_issued_deposit_family_holder_rows",
                "loan_delta_method": "simplification_static_t0_loan_shift",
                "deposit_families": ";".join(DEPOSIT_FAMILIES),
                "bank_credit_families": ";".join(BANK_CREDIT_FAMILIES),
                "claim_grade_label": LABEL,
                "lineage": "configs/rwtam/packs/phase6/conversion_parameters.csv rows 59/61; configs/rwtam/packs/opening_stocks.csv bank-credit rows",
            }
        )
    return rows


def _invariant_rows(
    pack_dir: Path,
    output_root: Path,
    builds: dict[tuple[str, str], object],
) -> list[dict[str, str]]:
    expected = build_v1(
        pack_dir,
        dose_mode=DEFAULT_DOSE_MODE,
        include_impulse_beta_comparator=False,
    ).rows("out_phase6_waterfall_scaffold")
    actual = builds[("off", DEFAULT_DOSE_MODE)].rows("out_phase6_waterfall_scaffold")  # type: ignore[attr-defined]
    byte_exact = expected == actual
    off = _headline(builds[("off", DEFAULT_DOSE_MODE)], "annual", "2026", "base")
    full = _headline(builds[("full", DEFAULT_DOSE_MODE)], "annual", "2026", "base")
    coupling_delta = _d(full["cumulative_RW"]) - _d(off["cumulative_RW"])
    return [
        {
            "check_id": "default_off_byte_exact",
            "status": "pass" if byte_exact else "fail",
            "expected": str(len(expected)),
            "actual": str(len(actual)),
            "note": "OFF run equals standard build_v1 phase6 waterfall rows",
        },
        {
            "check_id": "direction_check_base_year1_persistent",
            "status": "pass" if coupling_delta <= 0 else "review",
            "expected": "coupling_delta_RW<=0",
            "actual": _fmt(coupling_delta),
            "note": "negative means lower measured wall after loan-created deposit counterpart is wired",
        },
    ]


def _lineage_rows(output_root: Path) -> list[dict[str, str]]:
    return [
        {
            "artifact": "out_credit_deposit_coupling.csv",
            "path": str(output_root / "out_credit_deposit_coupling.csv"),
            "lineage_note": "ON/OFF and ablation values are fresh build_v1 phase6 waterfall outputs from exported scenario packs",
        },
        {
            "artifact": "coupling_on_full pack",
            "path": str(output_root / "packs" / "coupling_on_full"),
            "lineage_note": "opening_stocks.csv bank-issued deposit rows shifted by 6D loan-stock delta net of leakage",
        },
        {
            "artifact": "coupling_off pack",
            "path": str(output_root / "packs" / "coupling_off"),
            "lineage_note": "explicit default-OFF export path copied without stock mutation and byte-compared to default build_v1",
        },
        {
            "artifact": "phase6 6D rows",
            "path": "configs/rwtam/packs/phase6/conversion_parameters.csv",
            "lineage_note": "credit_supply_sloos_net_tightening_grid and diagnostic new-lending quantity response used only for this balance-sheet mirror",
        },
    ]


def _caveat_rows() -> list[dict[str, str]]:
    return [
        {
            "caveat_id": "assumption_grade_promoted",
            "caveat_text": "Mechanism is promoted into the default baseline as an owner-flagged assumption-grade combined-sink credit-stock mirror.",
        },
        {
            "caveat_id": "evidence_grade",
            "caveat_text": "6D quantity response keeps its owner-assumption diagnostic grade; this run does not claim a demand-side 6D dollar drag.",
        },
        {
            "caveat_id": "leakage_anchor",
            "caveat_text": "Leakage share represents non-deposit bank funding such as wholesale funding, FHLB advances, and bond issuance; H.8/Call Report liability mix is the directional support anchor.",
        },
        {
            "caveat_id": "symmetry",
            "caveat_text": "Cuts expand bank credit and deposits symmetrically in this mechanism because no asymmetric 6D evidence row is present.",
        },
        {
            "caveat_id": "double_count_guard",
            "caveat_text": "If 6D demand is enabled later, the same loan delta can drive two legitimate channels: spending quantities and bank liability-side interest-income stocks.",
        },
        {
            "caveat_id": "simplification_static_t0_loan_shift",
            "caveat_text": "The loan delta is a static t=0 closed-form opening-stock shift from SLOOS, response, and shock size; it is not a per-period paired-run loan path and is intentionally identical across dose modes.",
        },
    ]


def _write_measurement_rollups(output_root: Path, builds: dict[tuple[str, str], object]) -> None:
    for (variant, dose_mode), result in builds.items():
        out_dir = output_root / "measurements" / dose_mode / variant
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_rows(
            out_dir / "out_phase6_waterfall_scaffold.csv",
            result.rows("out_phase6_waterfall_scaffold"),  # type: ignore[attr-defined]
        )


def _write_cross_measurement_rollups(
    output_root: Path,
    builds: dict[tuple[str, str, str], object],
) -> None:
    for (leakage_band, elasticity_band, dose_mode), result in builds.items():
        out_dir = (
            output_root
            / "measurements"
            / dose_mode
            / f"cross_leakage_{leakage_band}_elasticity_{elasticity_band}"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_rows(
            out_dir / "out_phase6_waterfall_scaffold.csv",
            result.rows("out_phase6_waterfall_scaffold"),  # type: ignore[attr-defined]
        )


def _headline(
    result: object,
    period_type: str,
    period: str,
    band: str,
) -> dict[str, str]:
    rows = result.rows("out_phase6_waterfall_scaffold")  # type: ignore[attr-defined]
    return next(
        row
        for row in rows
        if row["period_type"] == period_type
        and row["period"] == period
        and row["band"] == band
        and row["ricardian_offset"] == "0"
        and row["headline_status"] == "final_rw_full"
    )


def _phase6_param(
    phase6_pack: dict[str, list[dict[str, str]]],
    parameter_id: str,
    band: str,
) -> Decimal:
    for row in phase6_pack["conversion_parameters"]:
        if row["parameter_id"] == parameter_id:
            return _d(row[band])
    raise KeyError(parameter_id)


def _holder(row: dict[str, str]) -> str:
    return _part(row["cell_or_sector"], "holder")


def _issuer(row: dict[str, str]) -> str:
    return _part(row["cell_or_sector"], "issuer")


def _part(cell: str, name: str) -> str:
    prefix = f"{name}="
    for part in cell.split("|"):
        if part.startswith(prefix):
            return part.removeprefix(prefix)
    return ""


def _sign(value: Decimal) -> Decimal:
    if value > 0:
        return Decimal("1")
    if value < 0:
        return Decimal("-1")
    return Decimal("0")


def _clear_output_subdirs(output_root: Path) -> None:
    for name in ("packs", "measurements"):
        path = output_root / name
        if path.exists():
            shutil.rmtree(path)


def _markdown_table(title: str, rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return ["", f"## {title}", "", "_No rows._"]
    headers = list(rows[0])
    lines = ["", f"## {title}", "", "| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return lines
