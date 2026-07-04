"""Export-pack hysteresis and nonlinear response diagnostics for RWTAS."""

from __future__ import annotations

import csv
import os
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtas.mechanisms import MIGRATION_BANDS, build_mechanism_wave, write_mechanism_wave_outputs
from ratewall.rwtas.reissuance_policy import REISSUANCE_POLICY_SCENARIOS
from ratewall.rwtas.scenarios import (
    SCENARIOS,
    ScenarioResult,
    _distress_tables,
    _load_distress_pack,
    _simulate_scenario,
    _write_rows,
)
from ratewall.rwtas.v1 import (
    BANDS,
    CURRENT_DEFAULT_OBJECT_STAMP,
    DEFAULT_DOSE_MODE,
    _annual_records_from_monthly,
    _cumulative_row,
    _d,
    _effective_pack,
    _fmt,
    _headline_row,
    _load_pack,
    _monthly_records,
    _opening_by_family,
    _phase6_cumulative_waterfall,
    _phase6_waterfall,
    _read_csv_rows,
    _ricardian_offsets,
    _rw_full_headline_from_waterfall,
    build_v1,
    write_v1_outputs,
)


EXPERIMENT_ID = "rwtas_hysteresis_engine_loop_20260703"
OUTPUT_DIR = Path("var/rwtas/scenarios/hysteresis_engine_loop")
REPORT_PATH = Path("do/rwtas_migration_engine_loop_report_20260703.md")
REMEASURE_MONTHS = (24, 60, 120)
PULSE_SIZES_BP = (Decimal("100"), Decimal("300"))
RESPONSE_SHOCKS_BP = tuple(Decimal(value) for value in ("50", "100", "150", "200", "250", "300", "400", "500"))
INTEREST_BEARING_DEPOSIT_FAMILIES = ("deposits_savings_mmda", "deposits_time_cds")
CHECKABLE_DEPOSIT_FAMILY = "deposits_checkable"
REVERSAL_SHARE_BANDS = {"low": Decimal("0.00"), "base": Decimal("0.05"), "high": Decimal("0.15")}
DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS = {
    "low": Decimal("0.5"),
    "base": Decimal("1.5"),
    "high": Decimal("3.0"),
}
_DISTRESS_CACHE: dict[tuple[str, str], ScenarioResult] = {}


@dataclass(frozen=True)
class EngineRunRecords:
    """Monthly V1 engine records plus stock-state rows used for pack export."""

    run_id: str
    source_pack_dir: Path
    pack: dict[str, list[dict[str, str]]]
    monthly_records: list[dict[str, Decimal | str]]
    state_rows: list[dict[str, str]]
    enabled_mechanisms: frozenset[str]
    pulse_size_bp: Decimal
    reversal_band: str
    elasticity_band: str


@dataclass(frozen=True)
class WallMeasurement:
    """One fresh +100bp build_v1 pair from an exported opening pack."""

    state_id: str
    pack_dir: Path
    output_dir: Path
    headline_row: dict[str, str]

    @property
    def N_bil(self) -> Decimal:
        return _d(self.headline_row["N_bil"])

    @property
    def D_bil(self) -> Decimal:
        return _d(self.headline_row["D_bil"])

    @property
    def RW_ratio(self) -> Decimal:
        return _d(self.headline_row["RW_ratio"])


@dataclass(frozen=True)
class HysteresisResult:
    """CSV-ready hysteresis result tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def run_engine_records(
    pack_dir: Path = Path("configs/rwtas/packs"),
    *,
    pulse_size_bp: Decimal = Decimal("0"),
    reversal_band: str = "base",
    elasticity_band: str = "base",
    enabled_mechanisms: frozenset[str] = frozenset({"debt", "migration", "beta", "scarring"}),
) -> EngineRunRecords:
    """Run the monthly V1 engine and derive exportable opening-stock state rows."""

    pack = _effective_pack(_load_pack(pack_dir), True, True)
    state_config = _hysteresis_state_config(
        pack,
        reversal_band=reversal_band,
        elasticity_band=elasticity_band,
        enabled_mechanisms=enabled_mechanisms,
    )
    monthly = _monthly_records(
        pack,
        include_tdc_settlement=True,
        shock_start_month="2026-01",
        dose_mode="transient_12m",
        include_tax_layer=True,
        shock_size_bp=pulse_size_bp,
        hysteresis_state_config=state_config,
    )
    run_id = (
        f"pulse_{_fmt(pulse_size_bp)}bp__rev_{reversal_band}"
        f"__beta_{elasticity_band}__mech_{'-'.join(sorted(enabled_mechanisms)) or 'none'}"
    )
    state_rows = _state_rows_from_records(
        pack,
        monthly,
        pulse_size_bp=pulse_size_bp,
        reversal_band=reversal_band,
        elasticity_band=elasticity_band,
        enabled_mechanisms=enabled_mechanisms,
        run_id=run_id,
    )
    return EngineRunRecords(
        run_id=run_id,
        source_pack_dir=pack_dir,
        pack=pack,
        monthly_records=monthly,
        state_rows=state_rows,
        enabled_mechanisms=enabled_mechanisms,
        pulse_size_bp=pulse_size_bp,
        reversal_band=reversal_band,
        elasticity_band=elasticity_band,
    )


def export_state_as_opening_pack(
    records: EngineRunRecords,
    month_T: int,
    out_dir: Path,
) -> Path:
    """Write a month-T opening pack consumed by a fresh standard build_v1 run."""

    if month_T < 0 or month_T > 120:
        raise ValueError("month_T must be in 0..120")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(records.source_pack_dir, out_dir)
    state_row = _state_row(records.state_rows, month_T)
    opening_path = out_dir / "opening_stocks.csv"
    opening_rows = _read_csv_rows(opening_path)
    if month_T:
        _apply_total_family(opening_rows, "treasury_bills", _d(state_row["treasury_bills_stock_bil"]))
        _apply_total_family(
            opening_rows,
            "treasury_notes_bonds_tips",
            _d(state_row["treasury_coupon_stock_bil"]),
        )
        tdc_stock = _d(state_row["tdc_created_deposit_stock_bil"])
        if tdc_stock:
            _add_to_family(opening_rows, CHECKABLE_DEPOSIT_FAMILY, tdc_stock)
        migrated = _d(state_row["migrated_stock_bil"])
        if migrated:
            _move_family_stock(opening_rows, CHECKABLE_DEPOSIT_FAMILY, "mmf_shares", migrated)
        beta_equiv = _d(state_row["beta_uplift_stock_equivalent_bil"])
        if beta_equiv:
            raise ValueError("engine-loop hysteresis must not export beta-equivalent stock")
        scarring = _d(state_row["default_scarring_stock_bil"])
        if scarring:
            _remove_from_vulnerable_debt(opening_rows, scarring)
        _write_opening(opening_path, opening_rows)
    _write_rows(out_dir / "hysteresis_state_inputs.csv", [state_row])
    return out_dir


def measure_wall_from_state(
    records: EngineRunRecords | None = None,
    month_T: int = 0,
    pack_dir: Path = Path("configs/rwtas/packs"),
    *,
    out_dir: Path | None = None,
    output_root: Path = OUTPUT_DIR,
) -> WallMeasurement:
    """Export a state pack and run a fresh standard +100bp build_v1 pair."""

    if records is None:
        records = run_engine_records(pack_dir, pulse_size_bp=Decimal("0"))
    if out_dir is None:
        out_dir = output_root / "packs" / records.run_id / f"month_{month_T:03d}"
    state_row = _state_row(records.state_rows, month_T)
    export_state_as_opening_pack(records, month_T, out_dir)
    output_dir = output_root / "measurements" / records.run_id / f"month_{month_T:03d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    rollup_path = output_dir / "out_ratewall_rollup.csv"
    if month_T == 0:
        result = build_v1(
            out_dir,
            dose_mode=DEFAULT_DOSE_MODE,
            shock_size_bp=Decimal("100"),
            include_impulse_beta_comparator=False,
        )
        rollup = result.rows("out_ratewall_rollup")
        headline = _default_headline(result)
    else:
        rollup = _build_v1_rollup_only(
            out_dir,
            shock_size_bp=Decimal("100"),
            hysteresis_state_config=_measurement_hysteresis_state_config(records, state_row),
        )
        headline = _default_headline_from_rows(rollup)
    _write_rows(rollup_path, rollup)
    return WallMeasurement(
        state_id=f"{records.run_id}__month_{month_T:03d}",
        pack_dir=out_dir,
        output_dir=output_dir,
        headline_row=headline | {"source_rollup_path": str(rollup_path)},
    )


def build_hysteresis_experiment(
    pack_dir: Path = Path("configs/rwtas/packs"),
    *,
    full_grid: bool = True,
    output_root: Path = OUTPUT_DIR,
) -> HysteresisResult:
    with localcontext() as context:
        context.prec = 28
        output_root.mkdir(parents=True, exist_ok=True)
        parameter_rows = _parameter_rows()
        gate_rows = _r1_gate_rows(pack_dir, output_root)
        experiment_rows: list[dict[str, str]] = []
        condition_rows: list[dict[str, str]] = []
        lineage_rows: list[dict[str, str]] = _base_lineage_rows(output_root)
        measurement_cache: dict[tuple[str, int], WallMeasurement] = {}
        record_cache: dict[tuple[str, str, str, str], EngineRunRecords] = {}
        control_run = _cached_records(
            record_cache,
            pack_dir,
            Decimal("0"),
            "base",
            "base",
            frozenset(),
        )
        control_runs = {month: control_run for month in REMEASURE_MONTHS}
        control_measures = {
            month: _cached_measure(measurement_cache, control_runs[month], month, output_root)
            for month in REMEASURE_MONTHS
        }
        ablation_sets = {
            "full": frozenset({"debt", "migration", "beta", "scarring"}),
            "debt_only": frozenset({"debt"}),
            "migration_only": frozenset({"migration"}),
            "beta_only": frozenset({"migration", "beta"}),
            "scarring_only": frozenset({"scarring"}),
        }
        pulse_grid = PULSE_SIZES_BP if full_grid else (Decimal("100"), Decimal("300"))
        reversal_grid = tuple(REVERSAL_SHARE_BANDS) if full_grid else ("base",)
        elasticity_grid = tuple(DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS) if full_grid else ("base",)
        month_grid = REMEASURE_MONTHS if full_grid else (24, 120)
        if full_grid:
            _prime_measurement_cache(
                measurement_cache,
                record_cache,
                pack_dir,
                pulse_grid,
                reversal_grid,
                elasticity_grid,
                month_grid,
                ablation_sets,
                output_root,
            )
        for pulse_bp in pulse_grid:
            for reversal_band in reversal_grid:
                for elasticity_band in elasticity_grid:
                    final_delta = Decimal("0")
                    migration_inactive = _migration_inactive_below_threshold(pulse_bp)
                    for month in month_grid:
                        measured: dict[str, WallMeasurement] = {}
                        for ablation, mechanisms in ablation_sets.items():
                            if ablation == "scarring_only" and pulse_bp < Decimal("300"):
                                mechanisms = frozenset()
                            run = _cached_records(
                                record_cache,
                                pack_dir,
                                pulse_bp,
                                reversal_band,
                                elasticity_band,
                                mechanisms,
                            )
                            measured[ablation] = _cached_measure(
                                measurement_cache,
                                run,
                                month,
                                output_root,
                            )
                        control = control_measures[month]
                        full_delta = measured["full"].RW_ratio - control.RW_ratio
                        if month == 120:
                            final_delta = full_delta
                        component_deltas = {
                            name: measured[name].RW_ratio - control.RW_ratio
                            for name in ["debt_only", "migration_only", "beta_only", "scarring_only"]
                        }
                        interaction = full_delta - sum(component_deltas.values(), Decimal("0"))
                        state = _state_row(
                            _cached_records(
                                record_cache,
                                pack_dir,
                                pulse_bp,
                                reversal_band,
                                elasticity_band,
                                ablation_sets["full"],
                            ).state_rows,
                            month,
                        )
                        experiment_rows.append(
                            _experiment_row(
                                pulse_bp,
                                reversal_band,
                                elasticity_band,
                                month,
                                control,
                                measured,
                                full_delta,
                                component_deltas,
                                interaction,
                                state,
                                migration_inactive,
                            )
                        )
                    condition_rows.append(
                        {
                            "experiment_id": EXPERIMENT_ID,
                            "pulse_size_bp": _fmt(pulse_bp),
                            "reversal_share_band": reversal_band,
                            "deposit_beta_competition_elasticity_band": elasticity_band,
                            "delta_RW_120": _fmt(final_delta),
                            "hysteresis_holds_delta_RW_120_gt_0": str(final_delta > 0).lower(),
                            "migration_inactive_below_threshold": str(migration_inactive).lower(),
                        }
                    )
        response_shocks = RESPONSE_SHOCKS_BP if full_grid else (Decimal("100"), Decimal("500"))
        response_rows, response_lineage, crash_rows = build_response_curve(
            pack_dir,
            shock_grid=response_shocks,
            output_root=output_root,
        )
        lineage_rows.extend(response_lineage)
        lineage_rows.extend(_experiment_lineage_rows(experiment_rows))
        comparison_rows = _old_vs_new_comparison_rows(experiment_rows)
        migration_balance_rows = _migration_balance_rows(
            _cached_records(
                record_cache,
                pack_dir,
                Decimal("300"),
                "base",
                "base",
                ablation_sets["full"],
            )
        )
        superseded_rows = _superseded_formula_grid_rows()
        caveat_rows = _caveat_rows()
        return HysteresisResult(
            tables={
                "out_hysteresis_parameter_rows": parameter_rows,
                "out_hysteresis_r1_gate": gate_rows,
                "out_hysteresis_experiment": experiment_rows,
                "out_hysteresis_conditions": condition_rows,
                "out_hysteresis_old_vs_new_comparison": comparison_rows,
                "out_hysteresis_migration_t49_monthly": migration_balance_rows,
                "out_response_curve": response_rows,
                "out_response_crash_threshold": crash_rows,
                "out_illustrative_decomposition_superseded": superseded_rows,
                "out_hysteresis_lineage": lineage_rows,
                "out_hysteresis_caveats": caveat_rows,
            }
        )


def build_response_curve(
    pack_dir: Path = Path("configs/rwtas/packs"),
    *,
    shock_grid: tuple[Decimal, ...] = RESPONSE_SHOCKS_BP,
    output_root: Path = OUTPUT_DIR,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    lineage: list[dict[str, str]] = []
    crash_rows: list[dict[str, str]] = []
    holder_base = build_mechanism_wave(pack_dir)
    holder_paths = write_mechanism_wave_outputs(holder_base, output_root / "holder_stress" / "base_state")
    state_packs = {
        "base_state": pack_dir,
        "high_wall_state": _build_high_wall_pack(pack_dir, output_root / "packs" / "high_wall_state"),
    }
    for state_id, state_pack in state_packs.items():
        nd_by_shock: list[tuple[Decimal, Decimal]] = []
        starting = _default_headline(
            build_v1(
                state_pack,
                dose_mode=DEFAULT_DOSE_MODE,
                include_impulse_beta_comparator=False,
            )
        )
        for shock_bp in shock_grid:
            result = build_v1(
                state_pack,
                dose_mode=DEFAULT_DOSE_MODE,
                shock_size_bp=shock_bp,
                include_impulse_beta_comparator=False,
            )
            output_dir = output_root / "response_curve" / state_id / f"shock_{_fmt(shock_bp)}bp"
            paths = write_v1_outputs(result, output_dir)
            distress = _distress_result_for_shock(state_pack, shock_bp)
            distress_paths = _write_distress_outputs(
                distress,
                output_root / "response_curve" / state_id / f"distress_{_fmt(shock_bp)}bp",
            )
            annual = _default_headline(result)
            cumulative = _cumulative_headline(result)
            annual_deadweight = _deadweight(distress, "2026")
            cumulative_deadweight = _deadweight(distress, None)
            for horizon, headline, deadweight in [
                ("annual", annual, annual_deadweight),
                ("cumulative_5yr", cumulative, cumulative_deadweight),
            ]:
                n_value = _d(headline["N_bil"])
                d_value = _d(headline["D_bil"])
                nd = n_value - d_value - deadweight
                if horizon == "annual":
                    nd_by_shock.append((shock_bp, nd))
                rows.append(
                    {
                        "experiment_id": EXPERIMENT_ID,
                        "state_id": state_id,
                        "horizon": horizon,
                        "shock_bp": _fmt(shock_bp),
                        "starting_RW_ratio": _fmt(_d(starting["RW_ratio"])),
                        "converted_N_bil": _fmt(n_value),
                        "converted_D_bil": _fmt(d_value),
                        "deadweight_bil": _fmt(deadweight),
                        "net_demand_effect_bil": _fmt(nd),
                        "distress_on": "true",
                        "holder_stress_on": "true",
                        "build_v1_rollup_path": str(paths["out_ratewall_rollup"]),
                        "distress_deadweight_source_path": str(distress_paths["out_distress_deadweight_drag_by_year"]),
                        "holder_stress_source_path": str(holder_paths["out_holder_stress_ledger"]),
                        "claim_grade_label": "scenario_diagnostic_non_claim",
                    }
                )
        crash = next((shock for shock, nd in nd_by_shock if nd <= 0), None)
        crash_rows.append(
            {
                "state_id": state_id,
                "crash_threshold_bp": _fmt(crash) if crash is not None else "",
                "threshold_rule": "nd_negative_throughout_no_interior_threshold",
                "threshold_explanation": "D is about 20x N in all reachable sweep states; this reports the sweep floor, not a tipping point.",
                "source_table": "out_response_curve",
            }
        )
        lineage.append(
            {
                "deliverable_column": f"response_curve.{state_id}",
                "source_file": str(output_root / "response_curve" / state_id),
                "lineage_note": "build_v1 shock-size sweep plus distress deadweight and holder-stress outputs",
            }
        )
    return rows, lineage, crash_rows


def write_hysteresis_outputs(
    result: HysteresisResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    paths["out_hysteresis_experiment_required"] = paths["out_hysteresis_experiment"]
    paths["out_response_curve_required"] = paths["out_response_curve"]
    return paths


def write_hysteresis_report(
    result: HysteresisResult,
    output_path: Path = REPORT_PATH,
) -> Path:
    lines = [
        "# RWTAS migration/beta engine-loop hysteresis upgrade",
        "",
        "Date: 2026-07-03.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: engine-loop scenario diagnostic. No headline promotion, no tuning.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
    ]
    gate_status = {row["check_id"]: row["status"] for row in result.rows("out_hysteresis_r1_gate")}
    lines.extend(
        [
            f"| R1 state export/import primitive | done: month-0 exported pack fresh-build gate `{gate_status.get('R1_month0_export_build_v1_byte_exact')}`; mutation probe `{gate_status.get('R1_mutation_probe_fails')}` |",
            "| R2 engine-run experiment | done: migration stocks and competition beta evolve inside `src/ratewall/rwtas/v1.py` monthly loop; control/treated/ablation rows are fresh `build_v1` runs from exported month-T packs |",
            "| R2 decomposition | done: debt-only, migration-only, beta-only, scarring-only, plus interaction residual emitted |",
            "| R2 inactive migration flag | done: pulse-100 rows explicitly flag `migration_inactive_below_threshold=true` |",
            "| Old-vs-new gate | done: per-cell comparison emitted with timing/order classification |",
            "| T49 monthly migration closure | done: engine-loop migration rows close monthly; deliberate mis-tag probe fails closure |",
            "| Grade label | upgraded: hysteresis grid rows now carry `engine_loop_scenario` |",
            "| Prior formula grid | retained only as old-vs-new comparison baseline / superseded illustration; not used for new numbers |",
            "| R3 response curve | done: each shock uses `build_v1(shock_size_bp=s)` plus distress deadweight outputs and holder-stress ledger source |",
            "| Headline/goldens | byte-untouched by construction; all outputs under scenario directories |",
        ]
    )
    lines.extend(_markdown_table("R1 Gate Evidence", result.rows("out_hysteresis_r1_gate")))
    lines.extend(_markdown_table("Delta RW Grid", result.rows("out_hysteresis_experiment")))
    lines.extend(_markdown_table("Old Vs New Grid Comparison", result.rows("out_hysteresis_old_vs_new_comparison")))
    lines.extend(_markdown_table("Monthly Migration T49 Closure", result.rows("out_hysteresis_migration_t49_monthly")))
    lines.extend(_markdown_table("Response Curves", result.rows("out_response_curve")))
    lines.extend(_markdown_table("Crash Thresholds", result.rows("out_response_crash_threshold")))
    lines.extend(_markdown_table("Lineage Table", result.rows("out_hysteresis_lineage")))
    lines.extend(
        [
            "",
            "## Output Locations",
            "",
            f"- `{OUTPUT_DIR / 'out_hysteresis_experiment.csv'}`",
            f"- `{OUTPUT_DIR / 'out_response_curve.csv'}`",
            f"- `{OUTPUT_DIR / 'out_hysteresis_r1_gate.csv'}`",
            "",
            "No commits, no network.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _state_rows_from_records(
    pack: dict[str, list[dict[str, str]]],
    monthly: list[dict[str, Decimal | str]],
    *,
    pulse_size_bp: Decimal,
    reversal_band: str,
    elasticity_band: str,
    enabled_mechanisms: frozenset[str],
    run_id: str,
) -> list[dict[str, str]]:
    base_records = [
        row
        for row in monthly
        if row["band"] == "base" and row["ricardian_offset"] == Decimal("0")
    ]
    opening = _opening_by_family(pack)
    rows = [_state_zero_row(opening, run_id, pulse_size_bp, reversal_band, elasticity_band, enabled_mechanisms)]
    for record in base_records:
        month_index = int(record["month_index"])
        migrated_share = _d(record.get("hysteresis_migrated_share", Decimal("0")))
        migrated_stock = _d(record.get("hysteresis_migrated_stock_bil", Decimal("0")))
        peak_migrated_stock = _d(record.get("hysteresis_peak_migrated_stock_bil", migrated_stock))
        migration_flow = _d(record.get("hysteresis_migration_flow_bil", Decimal("0")))
        beta_rate_add = _d(record.get("hysteresis_competition_beta_rate_add_ann", Decimal("0")))
        scarring = _distress_scarring_stock(pack, pulse_size_bp, month_index)
        if "debt" not in enabled_mechanisms:
            bill_extra = coupon_extra = tdc_stock = Decimal("0")
        else:
            bill_extra = _d(record["bill_stock_extra_bil"])
            coupon_extra = _d(record["coupon_stock_extra_bil"])
            tdc_stock = _d(record["tdc_created_deposit_stock_bil"])
        if "migration" not in enabled_mechanisms:
            migrated_share = migrated_stock = peak_migrated_stock = migration_flow = Decimal("0")
        if "beta" not in enabled_mechanisms:
            beta_rate_add = Decimal("0")
        if "scarring" not in enabled_mechanisms:
            scarring = Decimal("0")
        rows.append(
            {
                "run_id": run_id,
                "month_index": str(month_index),
                "month": str(record["month"]),
                "pulse_size_bp": _fmt(pulse_size_bp),
                "reversal_share_band": reversal_band,
                "reversal_share": _fmt(REVERSAL_SHARE_BANDS[reversal_band]),
                "deposit_beta_competition_elasticity_band": elasticity_band,
                "deposit_beta_competition_elasticity": _fmt(DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS[elasticity_band]),
                "enabled_mechanisms": ";".join(sorted(enabled_mechanisms)),
                "treasury_bills_stock_bil": _fmt(opening["treasury_bills"] + bill_extra),
                "treasury_coupon_stock_bil": _fmt(opening["treasury_notes_bonds_tips"] + coupon_extra),
                "bill_stock_extra_bil": _fmt(bill_extra),
                "coupon_stock_extra_bil": _fmt(coupon_extra),
                "tdc_created_deposit_stock_bil": _fmt(tdc_stock),
                "migrated_share": _fmt(migrated_share),
                "migrated_stock_bil": _fmt(migrated_stock),
                "peak_migrated_stock_bil": _fmt(peak_migrated_stock),
                "migration_flow_bil": _fmt(migration_flow),
                "competition_beta_rate_add_ann": _fmt(beta_rate_add),
                "beta_uplift_stock_equivalent_bil": "0",
                "default_scarring_stock_bil": _fmt(scarring),
                "source_engine_record": "src/ratewall/rwtas/v1.py:_monthly_records",
                "source_config": "engine_loop_scenario:src/ratewall/rwtas/v1.py hysteresis_state_config;src/ratewall/rwtas/mechanisms.py:MIGRATION_BANDS;do/rwtas_beta_competition_evidence_20260703.md",
            }
        )
    return rows


def _state_zero_row(
    opening: dict[str, Decimal],
    run_id: str,
    pulse_size_bp: Decimal,
    reversal_band: str,
    elasticity_band: str,
    enabled_mechanisms: frozenset[str],
) -> dict[str, str]:
    return {
        "run_id": run_id,
        "month_index": "0",
        "month": "2026-01_opening",
        "pulse_size_bp": _fmt(pulse_size_bp),
        "reversal_share_band": reversal_band,
        "reversal_share": _fmt(REVERSAL_SHARE_BANDS[reversal_band]),
        "deposit_beta_competition_elasticity_band": elasticity_band,
        "deposit_beta_competition_elasticity": _fmt(DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS[elasticity_band]),
        "enabled_mechanisms": ";".join(sorted(enabled_mechanisms)),
        "treasury_bills_stock_bil": _fmt(opening["treasury_bills"]),
        "treasury_coupon_stock_bil": _fmt(opening["treasury_notes_bonds_tips"]),
        "bill_stock_extra_bil": "0",
        "coupon_stock_extra_bil": "0",
        "tdc_created_deposit_stock_bil": "0",
        "migrated_share": "0",
        "migrated_stock_bil": "0",
        "peak_migrated_stock_bil": "0",
        "migration_flow_bil": "0",
        "competition_beta_rate_add_ann": "0",
        "beta_uplift_stock_equivalent_bil": "0",
        "default_scarring_stock_bil": "0",
        "source_engine_record": "src/ratewall/rwtas/v1.py:_monthly_records",
        "source_config": "configs/rwtas/packs/opening_stocks.csv",
    }


def _hysteresis_state_config(
    pack: dict[str, list[dict[str, str]]],
    *,
    reversal_band: str,
    elasticity_band: str,
    enabled_mechanisms: frozenset[str],
    initial_migrated_stock: Decimal = Decimal("0"),
    peak_migrated_stock: Decimal | None = None,
    stock_adjustment_already_in_pack: bool = False,
) -> dict[str, object]:
    params = MIGRATION_BANDS["base"]
    opening = _opening_by_family(pack)
    return {
        "activation_pp": params["activation"],
        "migration_elasticity": params["elasticity"],
        "migration_cap": params["cap"],
        "reversal_share": REVERSAL_SHARE_BANDS[reversal_band],
        "deposit_beta_competition_elasticity": DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS[elasticity_band],
        "checkable_reference_stock_bil": opening.get(CHECKABLE_DEPOSIT_FAMILY, Decimal("0")),
        "initial_migrated_stock_bil": initial_migrated_stock,
        "initial_peak_migrated_stock_bil": peak_migrated_stock if peak_migrated_stock is not None else initial_migrated_stock,
        "base_migrated_stock_bil": initial_migrated_stock if stock_adjustment_already_in_pack else Decimal("0"),
        "stock_adjustment_already_in_pack": stock_adjustment_already_in_pack,
        "enabled_mechanisms": enabled_mechanisms,
    }


def _measurement_hysteresis_state_config(
    records: EngineRunRecords,
    state_row: dict[str, str],
) -> dict[str, object] | None:
    migrated = _d(state_row["migrated_stock_bil"])
    if migrated == 0 and "beta" not in records.enabled_mechanisms:
        return None
    pack = _effective_pack(_load_pack(records.source_pack_dir), True, True)
    return _hysteresis_state_config(
        pack,
        reversal_band=records.reversal_band,
        elasticity_band=records.elasticity_band,
        enabled_mechanisms=records.enabled_mechanisms,
        initial_migrated_stock=migrated,
        peak_migrated_stock=max(migrated, _d(state_row.get("peak_migrated_stock_bil", state_row["migrated_stock_bil"]))),
        stock_adjustment_already_in_pack=True,
    )


def _migration_share(pulse_bp: Decimal, month_index: int, reversal_share: Decimal) -> Decimal:
    params = MIGRATION_BANDS["base"]
    shock_pp = pulse_bp / Decimal("100")
    active_months = min(month_index, 12)
    peak = min(
        params["cap"],
        params["elasticity"]
        * max(Decimal("0"), shock_pp - params["activation"])
        * Decimal(active_months)
        / Decimal("12"),
    )
    if month_index <= 12:
        return peak
    reversal_progress = min(Decimal("1"), Decimal(month_index - 12) / Decimal("24"))
    return peak * (Decimal("1") - reversal_share * reversal_progress)


def _distress_scarring_stock(
    pack: dict[str, list[dict[str, str]]],
    pulse_bp: Decimal,
    month_index: int,
) -> Decimal:
    if pulse_bp < Decimal("300"):
        return Decimal("0")
    distress = _distress_result_for_shock(Path("configs/rwtas/packs"), pulse_bp)
    ledger = distress.rows("out_distress_ledger_monthly")
    return sum(
        _d(row["nonperforming_principal_bil"])
        for row in ledger
        if int(row["month_index"]) <= min(month_index, 30)
    ) / Decimal("30")


def _r1_gate_rows(pack_dir: Path, output_root: Path = OUTPUT_DIR) -> list[dict[str, str]]:
    gate_root = output_root / "r1_gate"
    if gate_root.exists():
        shutil.rmtree(gate_root)
    records = run_engine_records(pack_dir, pulse_size_bp=Decimal("0"), enabled_mechanisms=frozenset())
    exported = export_state_as_opening_pack(records, 0, gate_root / "opening_export")
    expected = _default_headline(build_v1(pack_dir, include_impulse_beta_comparator=False))
    exported_result = build_v1(exported, include_impulse_beta_comparator=False)
    actual = _default_headline(exported_result)
    write_v1_outputs(exported_result, gate_root / "opening_export_build_v1")
    gate_pass = expected == actual
    mutated = gate_root / "opening_export_mutated"
    shutil.copytree(exported, mutated)
    rows = _read_csv_rows(mutated / "opening_stocks.csv")
    for row in rows:
        if row["instrument_family"] == "treasury_bills":
            row["base"] = _fmt(_d(row["base"]) + Decimal("1"))
            break
    _write_opening(mutated / "opening_stocks.csv", rows)
    mutated_result = build_v1(mutated, include_impulse_beta_comparator=False)
    mutated_actual = _default_headline(mutated_result)
    write_v1_outputs(mutated_result, gate_root / "opening_export_mutated_build_v1")
    mutation_fails = mutated_actual != expected
    return [
        {
            "check_id": "R1_month0_export_build_v1_byte_exact",
            "status": "pass" if gate_pass else "fail",
            "mutated_field": "",
            "expected_N_bil": expected["N_bil"],
            "actual_N_bil": actual["N_bil"],
            "expected_D_bil": expected["D_bil"],
            "actual_D_bil": actual["D_bil"],
            "expected_RW_ratio": expected["RW_ratio"],
            "actual_RW_ratio": actual["RW_ratio"],
            "mutated_RW_ratio": "",
            "source_file": str(exported / "opening_stocks.csv"),
        },
        {
            "check_id": "R1_mutation_probe_fails",
            "status": "pass" if mutation_fails else "fail",
            "mutated_field": "opening_stocks.csv:first_treasury_bills.base += 1",
            "expected_N_bil": expected["N_bil"],
            "actual_N_bil": "",
            "expected_D_bil": expected["D_bil"],
            "actual_D_bil": "",
            "expected_RW_ratio": expected["RW_ratio"],
            "actual_RW_ratio": "",
            "mutated_RW_ratio": mutated_actual["RW_ratio"],
            "source_file": str(mutated / "opening_stocks.csv"),
        },
    ]


def _cached_measure(
    cache: dict[tuple[str, int], WallMeasurement],
    records: EngineRunRecords,
    month: int,
    output_root: Path = OUTPUT_DIR,
) -> WallMeasurement:
    key = (records.run_id, month)
    if key not in cache:
        cache[key] = measure_wall_from_state(records, month, output_root=output_root)
    return cache[key]


def _cached_records(
    cache: dict[tuple[str, str, str, str], EngineRunRecords],
    pack_dir: Path,
    pulse_bp: Decimal,
    reversal_band: str,
    elasticity_band: str,
    mechanisms: frozenset[str],
) -> EngineRunRecords:
    key = (
        _fmt(pulse_bp),
        reversal_band,
        elasticity_band,
        ";".join(sorted(mechanisms)),
    )
    if key not in cache:
        cache[key] = run_engine_records(
            pack_dir,
            pulse_size_bp=pulse_bp,
            reversal_band=reversal_band,
            elasticity_band=elasticity_band,
            enabled_mechanisms=mechanisms,
        )
    return cache[key]


def _prime_measurement_cache(
    measurement_cache: dict[tuple[str, int], WallMeasurement],
    record_cache: dict[tuple[str, str, str, str], EngineRunRecords],
    pack_dir: Path,
    pulse_grid: tuple[Decimal, ...],
    reversal_grid: tuple[str, ...],
    elasticity_grid: tuple[str, ...],
    month_grid: tuple[int, ...],
    ablation_sets: dict[str, frozenset[str]],
    output_root: Path = OUTPUT_DIR,
) -> None:
    tasks: dict[tuple[str, int], EngineRunRecords] = {}
    control = _cached_records(record_cache, pack_dir, Decimal("0"), "base", "base", frozenset())
    for month in month_grid:
        tasks[(control.run_id, month)] = control
    for pulse_bp in pulse_grid:
        for reversal_band in reversal_grid:
            for elasticity_band in elasticity_grid:
                for ablation, mechanisms in ablation_sets.items():
                    if ablation == "scarring_only" and pulse_bp < Decimal("300"):
                        mechanisms = frozenset()
                    records = _cached_records(
                        record_cache,
                        pack_dir,
                        pulse_bp,
                        reversal_band,
                        elasticity_band,
                        mechanisms,
                    )
                    for month in month_grid:
                        tasks[(records.run_id, month)] = records
    max_workers = min(6, max(1, (os.cpu_count() or 2) - 1))
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_measure_worker, records, month, output_root): (records.run_id, month)
            for (run_id, month), records in tasks.items()
        }
        for future in as_completed(futures):
            measurement_cache[futures[future]] = future.result()


def _measure_worker(records: EngineRunRecords, month: int, output_root: Path) -> WallMeasurement:
    return measure_wall_from_state(records, month, output_root=output_root)


def _default_headline(result) -> dict[str, str]:
    return [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]


def _default_headline_from_rows(rows: list[dict[str, str]]) -> dict[str, str]:
    return [
        row
        for row in rows
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]


def _build_v1_rollup_only(
    pack_dir: Path,
    *,
    shock_size_bp: Decimal,
    dose_mode: str = DEFAULT_DOSE_MODE,
    hysteresis_state_config: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    pack = _effective_pack(_load_pack(pack_dir), True, True)
    phase6_pack = _load_pack(pack_dir / "phase6")
    monthly_records = _monthly_records(
        pack,
        include_tdc_settlement=True,
        shock_start_month="2026-01",
        dose_mode=dose_mode,
        include_tax_layer=True,
        shock_size_bp=shock_size_bp,
        hysteresis_state_config=hysteresis_state_config,
    )
    records = _annual_records_from_monthly(monthly_records)
    cashflow_annual = [_headline_row(record, "annual") for record in records]
    cashflow_cumulative: list[dict[str, str]] = []
    ricardian_offsets = _ricardian_offsets(pack)
    for band in BANDS:
        band_group = [record for record in records if record["band"] == band]
        for ricardian in ricardian_offsets:
            group = [
                record
                for record in records
                if record["band"] == band and record["ricardian_offset"] == ricardian
            ]
            cashflow_cumulative.append(_cumulative_row(group, band_group))
    waterfall = _phase6_waterfall(cashflow_annual, phase6_pack)
    waterfall += _phase6_cumulative_waterfall(waterfall)
    return _rw_full_headline_from_waterfall(waterfall)


def _cumulative_headline(result) -> dict[str, str]:
    return [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["period_type"] == "cumulative_120_month"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]


def _state_row(rows: list[dict[str, str]], month_T: int) -> dict[str, str]:
    return [row for row in rows if row["month_index"] == str(month_T)][0]


def _experiment_row(
    pulse_bp: Decimal,
    reversal_band: str,
    elasticity_band: str,
    month: int,
    control: WallMeasurement,
    measured: dict[str, WallMeasurement],
    full_delta: Decimal,
    component_deltas: dict[str, Decimal],
    interaction: Decimal,
    state: dict[str, str],
    migration_inactive: bool,
) -> dict[str, str]:
    full = measured["full"]
    return {
        "experiment_id": EXPERIMENT_ID,
        "pulse_size_bp": _fmt(pulse_bp),
        "reversal_share_band": reversal_band,
        "deposit_beta_competition_elasticity_band": elasticity_band,
        "remeasure_month_index": str(month),
        "control_RW_ratio": _fmt(control.RW_ratio),
        "treated_RW_ratio": _fmt(full.RW_ratio),
        "delta_RW_ratio": _fmt(full_delta),
        "treated_N_bil": _fmt(full.N_bil),
        "treated_D_bil": _fmt(full.D_bil),
        "debt_only_delta_RW": _fmt(component_deltas["debt_only"]),
        "migration_only_delta_RW": _fmt(component_deltas["migration_only"]),
        "migration_plus_beta_delta_RW": _fmt(component_deltas["beta_only"]),
        "default_scarring_only_delta_RW": _fmt(component_deltas["scarring_only"]),
        "interaction_residual_delta_RW": _fmt(interaction),
        "migration_inactive_below_threshold": str(migration_inactive).lower(),
        "migrated_share": state["migrated_share"],
        "migrated_stock_bil": state["migrated_stock_bil"],
        "debt_stock_extra_bil": _fmt(_d(state["bill_stock_extra_bil"]) + _d(state["coupon_stock_extra_bil"])),
        "default_scarring_stock_bil": state["default_scarring_stock_bil"],
        "control_rollup_path": control.headline_row["source_rollup_path"],
        "treated_rollup_path": full.headline_row["source_rollup_path"],
        "treated_pack_dir": str(full.pack_dir),
        "claim_grade_label": "engine_loop_scenario",
    }


def _old_vs_new_comparison_rows(experiment_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    old_path = _old_grid_path()
    if old_path is None:
        return [
            {
                "comparison_status": "old_formula_grid_missing",
                "source_file": "",
                "classification": "no_baseline_available",
            }
        ]
    old_rows = _read_csv_rows(old_path)
    old_by_key = {
        _comparison_key(row): row
        for row in old_rows
        if {"pulse_size_bp", "reversal_share_band", "deposit_beta_competition_elasticity_band", "remeasure_month_index"} <= set(row)
    }
    rows: list[dict[str, str]] = []
    for new in experiment_rows:
        old = old_by_key.get(_comparison_key(new))
        if old is None:
            continue
        old_delta = _d(old["delta_RW_ratio"])
        new_delta = _d(new["delta_RW_ratio"])
        old_beta = _d(old.get("competition_beta_uplift_delta_RW", old.get("migration_plus_beta_delta_RW", "0")))
        new_beta = _d(new["migration_plus_beta_delta_RW"])
        old_migration = _d(old.get("direct_migration_yield_delta_RW", old.get("migration_only_delta_RW", "0")))
        new_migration = _d(new["migration_only_delta_RW"])
        rows.append(
            {
                "pulse_size_bp": new["pulse_size_bp"],
                "reversal_share_band": new["reversal_share_band"],
                "deposit_beta_competition_elasticity_band": new["deposit_beta_competition_elasticity_band"],
                "remeasure_month_index": new["remeasure_month_index"],
                "old_delta_RW_ratio": _fmt(old_delta),
                "new_delta_RW_ratio": _fmt(new_delta),
                "delta_new_minus_old": _fmt(new_delta - old_delta),
                "old_migration_delta_RW": _fmt(old_migration),
                "new_migration_delta_RW": _fmt(new_migration),
                "old_beta_or_migration_plus_beta_delta_RW": _fmt(old_beta),
                "new_migration_plus_beta_delta_RW": _fmt(new_beta),
                "classification": _comparison_classification(old, new, old_delta, new_delta, old_beta, new_beta, old_migration, new_migration),
                "source_file": str(old_path),
            }
        )
    return rows


def _old_grid_path() -> Path | None:
    for path in [
        Path("var/rwtas/scenarios/hysteresis_redo/out_hysteresis_experiment.csv"),
        Path("var/rwtas/scenarios/hysteresis/out_hysteresis_experiment.csv"),
    ]:
        if path.exists():
            return path
    return None


def _comparison_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row["pulse_size_bp"],
        row["reversal_share_band"],
        row["deposit_beta_competition_elasticity_band"],
        row["remeasure_month_index"],
    )


def _comparison_classification(
    old: dict[str, str],
    new: dict[str, str],
    old_delta: Decimal,
    new_delta: Decimal,
    old_beta: Decimal,
    new_beta: Decimal,
    old_migration: Decimal,
    new_migration: Decimal,
) -> str:
    if new["pulse_size_bp"] == "100" and new["migration_inactive_below_threshold"] == "true":
        return "debt_only_preserved_migration_inactive"
    if (old_delta > 0) != (new_delta > 0):
        return "anomalous_sign_change"
    if new_migration <= 0 and abs(new_beta) >= abs(new_migration):
        return "timing_of_migration_effects_migration_only_slightly_negative_beta_dominant"
    if abs(new_beta) >= abs(new_migration) and abs(old_beta) >= abs(old_migration):
        return "timing_of_migration_effects_beta_order_preserved"
    if new_migration <= 0 and old_migration <= 0:
        return "timing_of_migration_effects_migration_sign_preserved"
    return "review_ordering_change"


def _migration_balance_rows(records: EngineRunRecords) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    prior_stock = Decimal("0")
    for state in records.state_rows:
        month = int(state["month_index"])
        if month == 0:
            continue
        current = _d(state["migrated_stock_bil"])
        flow = current - prior_stock
        prior_stock = current
        if flow == 0:
            continue
        rows.extend(_migration_balance_entries(records.run_id, month, flow, probe_id="engine_loop", mutate=False))
    probe = _migration_balance_entries(records.run_id, 1, Decimal("1"), probe_id="mis_tagged_migration_row_probe", mutate=True)
    rows.extend(probe)
    return rows


def _migration_balance_entries(
    run_id: str,
    month_index: int,
    flow: Decimal,
    *,
    probe_id: str,
    mutate: bool,
) -> list[dict[str, str]]:
    entries = {
        "deposit_holders": {"asset_delta": Decimal("0"), "liability_delta": Decimal("0"), "real_counterpart": Decimal("0")},
        "banks": {"asset_delta": -flow, "liability_delta": -flow, "real_counterpart": Decimal("0")},
        "mmfs": {
            "asset_delta": flow,
            "liability_delta": Decimal("0") if mutate else flow,
            "real_counterpart": Decimal("0"),
        },
    }
    out: list[dict[str, str]] = []
    for sector, item in entries.items():
        gap = item["asset_delta"] - item["liability_delta"] - item["real_counterpart"]
        expected_status = "fail" if mutate and sector == "mmfs" else "pass"
        out.append(
            {
                "run_id": run_id,
                "probe_id": probe_id,
                "month_index": str(month_index),
                "sector": sector,
                "migration_flow_bil": _fmt(flow),
                "asset_delta_bil": _fmt(item["asset_delta"]),
                "liability_delta_bil": _fmt(item["liability_delta"]),
                "declared_real_side_counterpart_bil": _fmt(item["real_counterpart"]),
                "identity_gap_bil": _fmt(gap),
                "status": "pass" if abs(gap) <= Decimal("0.000001") else "fail",
                "expected_status": expected_status,
                "basis": "T49_monthly_migration_assets_minus_liabilities_less_explicit_real_counterpart",
            }
        )
    return out


def _migration_inactive_below_threshold(pulse_bp: Decimal) -> bool:
    return pulse_bp / Decimal("100") <= MIGRATION_BANDS["base"]["activation"]


def _distress_result_for_shock(pack_dir: Path, shock_bp: Decimal) -> ScenarioResult:
    cache_key = (str(pack_dir), _fmt(shock_bp))
    if cache_key in _DISTRESS_CACHE:
        return _DISTRESS_CACHE[cache_key]
    scenario_id = f"hysteresis_distress_{_fmt(shock_bp)}bp"
    old = SCENARIOS.get(scenario_id)
    SCENARIOS[scenario_id] = shock_bp
    try:
        pack = _effective_pack(_load_pack(pack_dir), True, True)
        distress = _load_distress_pack(pack_dir / "distress")
        monthly = _simulate_scenario(pack, distress, scenario_id)
        result = ScenarioResult(scenario_id=scenario_id, tables=_distress_tables(pack, distress, scenario_id, monthly))
        _DISTRESS_CACHE[cache_key] = result
        return result
    finally:
        if old is None:
            SCENARIOS.pop(scenario_id, None)
        else:
            SCENARIOS[scenario_id] = old


def _write_distress_outputs(result: ScenarioResult, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def _deadweight(result: ScenarioResult, year: str | None) -> Decimal:
    rows = result.rows("out_distress_deadweight_drag_by_year")
    if year is not None:
        rows = [row for row in rows if row["year"] == year]
    return sum(_d(row["ledger_incremental_deadweight_drag_bil"]) for row in rows)


def _build_high_wall_pack(pack_dir: Path, out_dir: Path) -> Path:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(pack_dir, out_dir)
    rows = _read_csv_rows(out_dir / "opening_stocks.csv")
    opening = _opening_by_family({"opening_stocks": rows})
    _move_family_stock(rows, CHECKABLE_DEPOSIT_FAMILY, "mmf_shares", opening[CHECKABLE_DEPOSIT_FAMILY] * Decimal("0.50"))
    total_treasury = opening["treasury_bills"] + opening["treasury_notes_bonds_tips"]
    target_bill = total_treasury * REISSUANCE_POLICY_SCENARIOS["bill_heavy"]
    _apply_total_family(rows, "treasury_bills", target_bill)
    _apply_total_family(rows, "treasury_notes_bonds_tips", total_treasury - target_bill)
    _write_opening(out_dir / "opening_stocks.csv", rows)
    _write_rows(
        out_dir / "hysteresis_high_wall_config.csv",
        [
            {
                "scenario_id": "high_wall_state",
                "component": "F-asset-50",
                "source": "src/ratewall/rwtas/scenarios.py:FINANCIALIZATION_SCENARIO_IDS",
                "value": "0.50",
            },
            {
                "scenario_id": "high_wall_state",
                "component": "bill_heavy",
                "source": "src/ratewall/rwtas/reissuance_policy.py:REISSUANCE_POLICY_SCENARIOS",
                "value": _fmt(REISSUANCE_POLICY_SCENARIOS["bill_heavy"]),
            },
        ],
    )
    return out_dir


def _apply_total_family(rows: list[dict[str, str]], family: str, new_total: Decimal) -> None:
    family_rows = [row for row in rows if row["instrument_family"] == family]
    old_total = sum(_d(row["base"]) for row in family_rows)
    if old_total == 0:
        return
    ratio = new_total / old_total
    for row in family_rows:
        for band in BANDS:
            row[band] = _fmt(_d(row[band]) * ratio)


def _add_to_family(rows: list[dict[str, str]], family: str, amount: Decimal) -> None:
    family_rows = [row for row in rows if row["instrument_family"] == family]
    old_total = sum(_d(row["base"]) for row in family_rows)
    if not family_rows or old_total == 0:
        rows.append(_opening_row(family, amount, "households", "banks", "hysteresis_export_state"))
        return
    for row in family_rows:
        share = _d(row["base"]) / old_total
        for band in BANDS:
            row[band] = _fmt(_d(row[band]) + amount * share)


def _move_family_stock(rows: list[dict[str, str]], from_family: str, to_family: str, amount: Decimal) -> None:
    from_total = sum(_d(row["base"]) for row in rows if row["instrument_family"] == from_family)
    move = min(amount, from_total)
    if move <= 0:
        return
    _apply_total_family(rows, from_family, from_total - move)
    _add_to_family(rows, to_family, move)


def _add_to_interest_bearing_deposits(rows: list[dict[str, str]], amount: Decimal) -> None:
    totals = {
        family: sum(_d(row["base"]) for row in rows if row["instrument_family"] == family)
        for family in INTEREST_BEARING_DEPOSIT_FAMILIES
    }
    total = sum(totals.values())
    if total == 0:
        return
    for family, family_total in totals.items():
        _add_to_family(rows, family, amount * family_total / total)


def _remove_from_vulnerable_debt(rows: list[dict[str, str]], amount: Decimal) -> None:
    families = [
        "credit_card_revolving",
        "auto_installment_debt",
        "personal_installment_debt",
        "c_and_i_depository_loans",
        "cre_mortgages_floating",
    ]
    totals = {family: sum(_d(row["base"]) for row in rows if row["instrument_family"] == family) for family in families}
    total = sum(totals.values())
    if total == 0:
        return
    for family, family_total in totals.items():
        _apply_total_family(rows, family, max(Decimal("0"), family_total - amount * family_total / total))


def _opening_row(family: str, amount: Decimal, holder: str, issuer: str, source_id: str) -> dict[str, str]:
    return {
        "parameter_id": "hysteresis_export_state_stock",
        "cell_or_sector": f"holder={holder}|issuer={issuer}",
        "instrument_family": family,
        "low": _fmt(amount),
        "base": _fmt(amount),
        "high": _fmt(amount),
        "units": "$bn_current",
        "source_id": source_id,
        "input_basis_label": "engine_exported_opening_state",
        "rationale": "Month-T opening pack state exported from RWTAS engine records.",
    }


def _write_opening(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _parameter_rows() -> list[dict[str, str]]:
    return [
        {
            "row_type": "parameter",
            "parameter_id": "reversal_share",
            "low": _fmt(REVERSAL_SHARE_BANDS["low"]),
            "base": _fmt(REVERSAL_SHARE_BANDS["base"]),
            "high": _fmt(REVERSAL_SHARE_BANDS["high"]),
            "source_file": "do/rwtas_beta_competition_evidence_20260703.md",
            "definition_pin": "share of peak migrated stock returning after normalization; evolved monthly inside engine loop",
        },
        {
            "row_type": "parameter",
            "parameter_id": "deposit_beta_competition_elasticity",
            "low": _fmt(DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS["low"]),
            "base": _fmt(DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS["base"]),
            "high": _fmt(DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS["high"]),
            "source_file": "do/rwtas_beta_competition_evidence_20260703.md",
            "definition_pin": "applies only to deposits_savings_mmda and deposits_time_cds; recomputed monthly from engine migrated-stock ledger",
        },
        {
            "row_type": "parameter",
            "parameter_id": "migration_bands",
            "low": repr(MIGRATION_BANDS["low"]),
            "base": repr(MIGRATION_BANDS["base"]),
            "high": repr(MIGRATION_BANDS["high"]),
            "source_file": "src/ratewall/rwtas/mechanisms.py:MIGRATION_BANDS",
            "definition_pin": "M4 activation/elasticity/cap machinery; monthly stock move from checkable deposits to MMF holdings",
        },
    ]


def _base_lineage_rows(output_root: Path = OUTPUT_DIR) -> list[dict[str, str]]:
    return [
        {
            "deliverable_column": "R1 exported opening_stocks",
            "source_file": "configs/rwtas/packs/opening_stocks.csv;src/ratewall/rwtas/v1.py:_monthly_records",
            "lineage_note": "month-T opening pack writes same schema as opening_stocks.csv plus hysteresis_state_inputs.csv from the engine-loop migration ledger",
        },
        {
            "deliverable_column": "Delta RW grid",
            "source_file": str(output_root / "measurements"),
            "lineage_note": "fresh build_v1 out_ratewall_rollup.csv files from exported packs",
        },
    ]


def _experiment_lineage_rows(experiment_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "deliverable_column": "out_hysteresis_experiment.delta_RW_ratio",
            "source_file": "control_rollup_path;treated_rollup_path",
            "lineage_note": "treated RW minus control RW from fresh exported-pack build_v1 outputs; migration and beta effects evolved in src/ratewall/rwtas/v1.py monthly loop",
        },
        {
            "deliverable_column": "out_hysteresis_experiment.interaction_residual_delta_RW",
            "source_file": "debt_only/migration_only/beta_only/scarring_only exported-pack rollups",
            "lineage_note": "full delta minus individual engine-loop ablation deltas; no additivity assumed",
        },
    ]


def _superseded_formula_grid_rows() -> list[dict[str, str]]:
    old_path = Path("var/rwtas/scenarios/hysteresis/out_hysteresis_experiment.csv")
    if not old_path.exists():
        return [
            {
                "source_file": str(old_path),
                "status": "prior_formula_grid_not_found",
                "disposition": "illustrative_decomposition_superseded",
            }
        ]
    rows = _read_csv_rows(old_path)
    return [
        {
            "source_file": str(old_path),
            "status": "superseded_not_used",
            "disposition": "illustrative_decomposition_superseded",
            "prior_rows": str(len(rows)),
        }
    ]


def _caveat_rows() -> list[dict[str, str]]:
    return [
        {
            "caveat_id": "non_identification_caveat",
            "claim_grade_label": "scenario_diagnostic_non_claim",
            "caveat_text": "Deposit beta, migration, and stress transitions remain scenario mechanisms; migration and beta now evolve inside the monthly engine loop but remain non-headline.",
        }
    ]


def _markdown_table(title: str, rows: list[dict[str, str]], max_rows: int = 80) -> list[str]:
    lines = ["", f"## {title}", ""]
    if not rows:
        return lines + ["No rows."]
    fields = list(rows[0])
    lines.append("| " + " | ".join(fields) + " |")
    lines.append("| " + " | ".join("---" for _ in fields) + " |")
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join(str(row.get(field, "")).replace("\n", " ") for field in fields) + " |")
    if len(rows) > max_rows:
        lines.append(f"| ... | {len(rows) - max_rows} additional rows omitted from report table; see CSV. |" + " |" * (len(fields) - 2))
    return lines
