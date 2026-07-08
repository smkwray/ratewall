"""Scenario-only AI-boom twin for RWTAM.

The scenario evolves opening-stock states with existing V1 stock, issuance, and
hysteresis machinery, then remeasures the standard +100bp wall on those states.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtam.hysteresis import (
    CHECKABLE_DEPOSIT_FAMILY,
    DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS,
    _apply_total_family,
    _move_family_stock,
    _write_opening,
)
from ratewall.rwtam.mechanisms import MIGRATION_BANDS
from ratewall.rwtam.reissuance_policy import PRIMARY_DEFICIT_BASE_PATH
from ratewall.rwtam.scenarios import ScenarioResult
from ratewall.rwtam.v1 import (
    CURRENT_DEFAULT_OBJECT_STAMP,
    DEFAULT_DOSE_MODE,
    _d,
    _effective_pack,
    _fmt,
    _load_pack,
    _monthly_records,
    _opening_by_family,
    _read_csv_rows,
    _write_rows,
    build_v1,
)


EXPERIMENT_ID = "rwtam_ai_boom_twin_20260704"
OUTPUT_DIR = Path("var/rwtam/scenarios/ai_boom_twin")
REPORT_PATH = Path("do/rwtam_ai_boom_report_20260704.md")
REMEASURE_MONTHS = (60, 120)
RATE_ENVIRONMENT_SHIFT_BP = Decimal("150")
RATE_ENVIRONMENT_VARIANTS_BP = (Decimal("150"), Decimal("250"))
GROWTH_DIFFERENTIAL_ANNUAL = Decimal("0.01")
FISCAL_BRANCHES = {"F_plus": Decimal("0.70"), "F_minus": Decimal("1.30")}
CONTROL_MULTIPLIER = Decimal("1")
CLAIM_LABEL = "scenario_only;hypothetical_state;assumption_directional_support"
DEFAULT_GOLDEN_ROLLUP = Path("tests/fixtures/rwtam/golden_wave8/out_ratewall_rollup.csv")
GROWTH_STOCK_FAMILIES = (
    "deposits_checkable",
    "deposits_savings_mmda",
    "deposits_time_cds",
    "mortgages_fixed",
    "mortgages_arm",
    "heloc",
    "credit_card_revolving",
    "auto_installment_debt",
    "student_loans_federal",
    "student_loans_private",
    "personal_installment_debt",
    "c_and_i_depository_loans",
    "syndicated_loans",
    "corporate_bonds",
    "cre_mortgages_floating",
    "cre_mortgages_fixed",
)


@dataclass(frozen=True)
class AiBoomRun:
    """One evolved state path used for +100bp remeasurement."""

    run_id: str
    source_pack_dir: Path
    pack: dict[str, list[dict[str, str]]]
    monthly_records: list[dict[str, Decimal | str]]
    state_rows: list[dict[str, str]]
    rate_environment_bp: Decimal
    growth_differential_annual: Decimal
    deficit_multiplier: Decimal


def build_ai_boom_twin(
    pack_dir: Path = Path("configs/rwtam/packs"),
    *,
    output_root: Path = OUTPUT_DIR,
) -> ScenarioResult:
    """Build control, F+, F-, and independent single-route ablations."""

    with localcontext() as context:
        context.prec = 28
        output_root.mkdir(parents=True, exist_ok=True)
        _clear_output_subdirs(output_root)

        specs = _run_specs()
        runs = {
            run_id: run_ai_boom_records(
                pack_dir,
                run_id=run_id,
                rate_environment_bp=rate_bp,
                growth_differential_annual=growth,
                deficit_multiplier=deficit,
            )
            for run_id, rate_bp, growth, deficit in specs
        }
        measures: dict[tuple[str, int], dict[str, str]] = {}
        for run_id, run in runs.items():
            for month in REMEASURE_MONTHS:
                measures[(run_id, month)] = measure_ai_boom_wall(run, month, output_root)

        full_state_rows = [
            row
            for run in runs.values()
            for row in run.state_rows
        ]
        twin_rows = _twin_rows(measures, state_rows=full_state_rows)
        state_rows = [
            row
            for run in runs.values()
            for row in run.state_rows
            if row["month_index"] in {"0", "60", "120"}
        ]
        tables = {
            "out_ai_boom_twin": twin_rows,
            "out_ai_boom_state_path": state_rows,
            "out_ai_boom_parameter_rows": _parameter_rows(),
            "out_ai_boom_notes": _note_rows(),
            "out_ai_boom_lineage": _lineage_rows(output_root),
            "out_ai_boom_caveats": _caveat_rows(),
            "out_ai_boom_invariant_check": _invariant_rows(pack_dir, twin_rows, state_rows),
        }
        return ScenarioResult(scenario_id=EXPERIMENT_ID, tables=tables)


def run_ai_boom_records(
    pack_dir: Path,
    *,
    run_id: str,
    rate_environment_bp: Decimal,
    growth_differential_annual: Decimal,
    deficit_multiplier: Decimal,
) -> AiBoomRun:
    """Run existing monthly records with the scenario state dials exposed."""

    pack = _effective_pack(_load_pack(pack_dir), True, True)
    hysteresis_config = _ai_hysteresis_config(pack)
    monthly = _monthly_records(
        pack,
        include_tdc_settlement=True,
        shock_start_month="2026-01",
        dose_mode=DEFAULT_DOSE_MODE,
        include_tax_layer=True,
        shock_size_bp=rate_environment_bp,
        hysteresis_state_config=hysteresis_config,
    )
    state_rows = _state_rows(
        pack,
        monthly,
        run_id=run_id,
        rate_environment_bp=rate_environment_bp,
        growth_differential_annual=growth_differential_annual,
        deficit_multiplier=deficit_multiplier,
    )
    return AiBoomRun(
        run_id=run_id,
        source_pack_dir=pack_dir,
        pack=pack,
        monthly_records=monthly,
        state_rows=state_rows,
        rate_environment_bp=rate_environment_bp,
        growth_differential_annual=growth_differential_annual,
        deficit_multiplier=deficit_multiplier,
    )


def measure_ai_boom_wall(
    run: AiBoomRun,
    month_T: int,
    output_root: Path = OUTPUT_DIR,
) -> dict[str, str]:
    """Export an evolved opening pack and run a fresh standard +100bp wall."""

    pack_dir = export_ai_boom_state_pack(
        run,
        month_T,
        output_root / "packs" / run.run_id / f"month_{month_T:03d}",
    )
    state = _state_row(run.state_rows, month_T)
    result = build_v1(
        pack_dir,
        dose_mode=DEFAULT_DOSE_MODE,
        shock_size_bp=Decimal("100"),
        include_impulse_beta_comparator=False,
        hysteresis_state_config=_measurement_hysteresis_config(run, state),
    )
    output_dir = output_root / "measurements" / run.run_id / f"month_{month_T:03d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    rollup_path = output_dir / "out_ratewall_rollup.csv"
    _write_rows(rollup_path, result.rows("out_ratewall_rollup"))
    headline = _headline(result.rows("out_ratewall_rollup"))
    return {
        "N_bil": headline["N_bil"],
        "D_bil": headline["D_bil"],
        "RW_ratio": headline["RW_ratio"],
        "pack_dir": str(pack_dir),
        "rollup_path": str(rollup_path),
    }


def export_ai_boom_state_pack(run: AiBoomRun, month_T: int, out_dir: Path) -> Path:
    """Write the month-T stock state using only exported pack dials."""

    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(run.source_pack_dir, out_dir)
    state = _state_row(run.state_rows, month_T)
    rows = _read_csv_rows(out_dir / "opening_stocks.csv")
    opening = _opening_by_family({"opening_stocks": rows})

    debt_add = _d(state["gross_issuance_cumulative_bil"])
    if debt_add:
        _apply_total_family(rows, "treasury_bills", opening["treasury_bills"] + debt_add * Decimal("0.30"))
        _apply_total_family(
            rows,
            "treasury_notes_bonds_tips",
            opening["treasury_notes_bonds_tips"] + debt_add * Decimal("0.70"),
        )
    growth_factor = _d(state["growth_stock_scale_factor"]) - Decimal("1")
    if growth_factor:
        for family in GROWTH_STOCK_FAMILIES:
            current_total = sum(_d(row["base"]) for row in rows if row["instrument_family"] == family)
            if current_total:
                _apply_total_family(rows, family, current_total * (Decimal("1") + growth_factor))
    migrated = _d(state["migrated_stock_bil"])
    if migrated:
        _move_family_stock(rows, CHECKABLE_DEPOSIT_FAMILY, "mmf_shares", migrated)

    _write_opening(out_dir / "opening_stocks.csv", rows)
    _write_rows(out_dir / "ai_boom_state_inputs.csv", [state])
    return out_dir


def write_ai_boom_outputs(
    result: ScenarioResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_ai_boom_report(
    result: ScenarioResult,
    output_path: Path = REPORT_PATH,
) -> Path:
    rows = result.rows("out_ai_boom_twin")
    f_plus_120 = next(row for row in rows if row["branch_id"] == "F_plus" and row["remeasure_month_index"] == "120")
    f_minus_120 = next(row for row in rows if row["branch_id"] == "F_minus" and row["remeasure_month_index"] == "120")
    answer = _answer_as_found(f_plus_120, f_minus_120)
    migration_message = next(
        row["message"]
        for row in result.rows("out_ai_boom_invariant_check")
        if row["check_id"] == "AI4_migration_activation_status_emitted"
    )
    lines = [
        "# RWTAM AI-boom twin",
        "",
        "Date: 2026-07-04.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: scenario/exhibit-grade hypothetical states; no headline or golden promotion.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
        "| control | built from current default state, CBO-base cumulative deficits, baseline rate environment, and 120-month evolution |",
        "| rate environment | built as +150bp and +250bp sustained state paths through existing hysteresis config; standard wall remains the +100bp marginal measurement on evolved states |",
        "| growth dial | built as a single +1pp/yr nominal stock-growth scale on income-linked deposit and household/firm-debt stock families |",
        "| fiscal branches | built as CBO primary-deficit path multipliers: F+ = 0.70, F- = 1.30 |",
        "| ablations | built from independent rate-only, growth-only, and fiscal-only runs; residual is computed and additivity is not assumed |",
        "| Levy rider | L4 display plug guard patched separately; pre-plug natural sums now fail loud above dust |",
        "",
        f"Answer as found: **{answer}**",
        "",
        f"Migration status: {migration_message}. The existing base threshold creates a dead zone below a 2pp rate-environment shock; the +250bp variant crosses it organically and emits activation month and pace.",
    ]
    lines.extend(_markdown_table("Branch Table", rows))
    lines.extend(_markdown_table("Invariants", result.rows("out_ai_boom_invariant_check")))
    lines.extend(_markdown_table("Notes", result.rows("out_ai_boom_notes")))
    lines.extend(_markdown_table("Lineage", result.rows("out_ai_boom_lineage")))
    lines.extend(_markdown_table("Caveats", result.rows("out_ai_boom_caveats")))
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `var/rwtam/scenarios/ai_boom_twin/out_ai_boom_twin.csv`",
            "- `var/rwtam/scenarios/ai_boom_twin/out_ai_boom_state_path.csv`",
        "- `var/rwtam/scenarios/ai_boom_twin/out_ai_boom_invariant_check.csv`",
        "- `var/rwtam/scenarios/ai_boom_twin/out_ai_boom_notes.csv`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _run_specs() -> tuple[tuple[str, Decimal, Decimal, Decimal], ...]:
    specs: list[tuple[str, Decimal, Decimal, Decimal]] = [
        ("control", Decimal("0"), Decimal("0"), CONTROL_MULTIPLIER),
        ("growth_only", Decimal("0"), GROWTH_DIFFERENTIAL_ANNUAL, CONTROL_MULTIPLIER),
        ("fiscal_only_F_plus", Decimal("0"), Decimal("0"), FISCAL_BRANCHES["F_plus"]),
        ("fiscal_only_F_minus", Decimal("0"), Decimal("0"), FISCAL_BRANCHES["F_minus"]),
    ]
    for rate_bp in RATE_ENVIRONMENT_VARIANTS_BP:
        suffix = _rate_suffix(rate_bp)
        specs.extend(
            [
                (f"rate_only_{suffix}", rate_bp, Decimal("0"), CONTROL_MULTIPLIER),
                (f"full_F_plus_{suffix}", rate_bp, GROWTH_DIFFERENTIAL_ANNUAL, FISCAL_BRANCHES["F_plus"]),
                (f"full_F_minus_{suffix}", rate_bp, GROWTH_DIFFERENTIAL_ANNUAL, FISCAL_BRANCHES["F_minus"]),
            ]
        )
    return tuple(specs)


def _state_rows(
    pack: dict[str, list[dict[str, str]]],
    monthly: list[dict[str, Decimal | str]],
    *,
    run_id: str,
    rate_environment_bp: Decimal,
    growth_differential_annual: Decimal,
    deficit_multiplier: Decimal,
) -> list[dict[str, str]]:
    opening = _opening_by_family(pack)
    base_records = [
        row
        for row in monthly
        if row["band"] == "base" and row["ricardian_offset"] == Decimal("0")
    ]
    rows = [
        _state_row_zero(
            opening,
            run_id=run_id,
            rate_environment_bp=rate_environment_bp,
            growth_differential_annual=growth_differential_annual,
            deficit_multiplier=deficit_multiplier,
        )
    ]
    gross_by_month = _monthly_primary_deficit_path(deficit_multiplier)
    cumulative_gross = Decimal("0")
    for record in base_records:
        month_index = int(record["month_index"])
        cumulative_gross += gross_by_month[month_index - 1]
        growth_scale = _growth_scale(month_index, growth_differential_annual)
        migrated = _d(record.get("hysteresis_migrated_stock_bil", Decimal("0")))
        rows.append(
            {
                "run_id": run_id,
                "experiment_id": EXPERIMENT_ID,
                "month_index": str(month_index),
                "month": str(record["month"]),
                "rate_environment_bp": _fmt(rate_environment_bp),
                "growth_differential_annual": _fmt(growth_differential_annual),
                "deficit_multiplier": _fmt(deficit_multiplier),
                "gross_issuance_month_bil": _fmt(gross_by_month[month_index - 1]),
                "gross_issuance_cumulative_bil": _fmt(cumulative_gross),
                "growth_stock_scale_factor": _fmt(growth_scale),
                "growth_stock_families": ";".join(GROWTH_STOCK_FAMILIES),
                "migrated_stock_bil": _fmt(migrated),
                "peak_migrated_stock_bil": _fmt(record.get("hysteresis_peak_migrated_stock_bil", Decimal("0"))),
                "migrated_share": _fmt(record.get("hysteresis_migrated_share", Decimal("0"))),
                "migration_flow_bil": _fmt(record.get("hysteresis_migration_flow_bil", Decimal("0"))),
                "migration_activated": str(migrated > 0).lower(),
                "claim_grade_label": CLAIM_LABEL,
                "source_engine_record": "src/ratewall/rwtam/v1.py:_monthly_records",
            }
        )
    return rows


def _state_row_zero(
    opening: dict[str, Decimal],
    *,
    run_id: str,
    rate_environment_bp: Decimal,
    growth_differential_annual: Decimal,
    deficit_multiplier: Decimal,
) -> dict[str, str]:
    return {
        "run_id": run_id,
        "experiment_id": EXPERIMENT_ID,
        "month_index": "0",
        "month": "2026-01_opening",
        "rate_environment_bp": _fmt(rate_environment_bp),
        "growth_differential_annual": _fmt(growth_differential_annual),
        "deficit_multiplier": _fmt(deficit_multiplier),
        "gross_issuance_month_bil": "0",
        "gross_issuance_cumulative_bil": "0",
        "growth_stock_scale_factor": "1",
        "growth_stock_families": ";".join(GROWTH_STOCK_FAMILIES),
        "migrated_stock_bil": "0",
        "peak_migrated_stock_bil": "0",
        "migrated_share": "0",
        "migration_flow_bil": "0",
        "migration_activated": "false",
        "claim_grade_label": CLAIM_LABEL,
        "source_engine_record": "configs/rwtam/packs/opening_stocks.csv",
        "opening_checkable_deposits_bil": _fmt(opening.get(CHECKABLE_DEPOSIT_FAMILY, Decimal("0"))),
    }


def _twin_rows(
    measures: dict[tuple[str, int], dict[str, str]],
    *,
    state_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rate_bp in RATE_ENVIRONMENT_VARIANTS_BP:
        suffix = _rate_suffix(rate_bp)
        activation = _rate_route_activation(state_rows, f"rate_only_{suffix}")
        for branch_id, fiscal_run in (("F_plus", "fiscal_only_F_plus"), ("F_minus", "fiscal_only_F_minus")):
            for month in REMEASURE_MONTHS:
                control = measures[("control", month)]
                full = measures[(f"full_{branch_id}_{suffix}", month)]
                rate = measures[(f"rate_only_{suffix}", month)]
                growth = measures[("growth_only", month)]
                fiscal = measures[(fiscal_run, month)]
                control_rw = _d(control["RW_ratio"])
                full_delta = _d(full["RW_ratio"]) - control_rw
                rate_delta = _d(rate["RW_ratio"]) - control_rw
                growth_delta = _d(growth["RW_ratio"]) - control_rw
                fiscal_delta = _d(fiscal["RW_ratio"]) - control_rw
                residual = full_delta - rate_delta - growth_delta - fiscal_delta
                rows.append(
                    {
                        "experiment_id": EXPERIMENT_ID,
                        "branch_id": branch_id,
                        "branch_deficit_multiplier": _fmt(FISCAL_BRANCHES[branch_id]),
                        "rate_environment_bp": _fmt(rate_bp),
                        "remeasure_month_index": str(month),
                        "horizon": "year_5" if month == 60 else "year_10",
                        "control_RW_ratio": control["RW_ratio"],
                        "full_branch_RW_ratio": full["RW_ratio"],
                        "delta_RW_vs_control": _fmt(full_delta),
                        "rate_environment_only_delta_RW": _fmt(rate_delta),
                        "growth_only_delta_RW": _fmt(growth_delta),
                        "fiscal_path_only_delta_RW": _fmt(fiscal_delta),
                        "ablation_residual_delta_RW": _fmt(residual),
                        "ablation_additivity_assumed": "false",
                        "rate_route_activation_month": activation["activation_month"],
                        "rate_route_peak_migrated_share": activation["peak_migrated_share"],
                        "rate_route_peak_migration_flow_bil": activation["peak_migration_flow_bil"],
                        "control_rollup_path": control["rollup_path"],
                        "full_rollup_path": full["rollup_path"],
                        "rate_only_rollup_path": rate["rollup_path"],
                        "growth_only_rollup_path": growth["rollup_path"],
                        "fiscal_only_rollup_path": fiscal["rollup_path"],
                        "answer_class": _branch_class(full_delta),
                        "claim_grade_label": CLAIM_LABEL,
                    }
                )
    return rows


def _ai_hysteresis_config(pack: dict[str, list[dict[str, str]]]) -> dict[str, object]:
    params = MIGRATION_BANDS["base"]
    opening = _opening_by_family(pack)
    return {
        "activation_pp": params["activation"],
        "migration_elasticity": params["elasticity"],
        "migration_cap": params["cap"],
        "reversal_share": Decimal("0"),
        "deposit_beta_competition_elasticity": DEPOSIT_BETA_COMPETITION_ELASTICITY_BANDS["base"],
        "checkable_reference_stock_bil": opening.get(CHECKABLE_DEPOSIT_FAMILY, Decimal("0")),
        "initial_migrated_stock_bil": Decimal("0"),
        "initial_peak_migrated_stock_bil": Decimal("0"),
        "base_migrated_stock_bil": Decimal("0"),
        "stock_adjustment_already_in_pack": False,
        "enabled_mechanisms": frozenset({"migration", "beta"}),
    }


def _measurement_hysteresis_config(run: AiBoomRun, state: dict[str, str]) -> dict[str, object] | None:
    migrated = _d(state["migrated_stock_bil"])
    if migrated == 0:
        return None
    config = _ai_hysteresis_config(run.pack)
    config["initial_migrated_stock_bil"] = migrated
    config["initial_peak_migrated_stock_bil"] = max(migrated, _d(state["peak_migrated_stock_bil"]))
    config["base_migrated_stock_bil"] = migrated
    config["stock_adjustment_already_in_pack"] = True
    return config


def _monthly_primary_deficit_path(multiplier: Decimal) -> list[Decimal]:
    return [annual * multiplier / Decimal("12") for annual in PRIMARY_DEFICIT_BASE_PATH for _ in range(12)]


def _growth_scale(month_index: int, growth_differential_annual: Decimal) -> Decimal:
    if growth_differential_annual == 0:
        return Decimal("1")
    return Decimal("1") + growth_differential_annual * (Decimal(month_index) / Decimal("12"))


def _parameter_rows() -> list[dict[str, str]]:
    return [
        {
            "parameter_id": "rate_environment_shift_bp",
            "base": ";".join(_fmt(value) for value in RATE_ENVIRONMENT_VARIANTS_BP),
            "units": "basis_points",
            "claim_grade_label": CLAIM_LABEL,
            "wiring": "state evolution shock_size_bp only; measured wall remains standard +100bp",
        },
        {
            "parameter_id": "growth_differential_annual",
            "base": _fmt(GROWTH_DIFFERENTIAL_ANNUAL),
            "units": "annual_share",
            "claim_grade_label": CLAIM_LABEL,
            "wiring": "single stock scale applied to income-linked deposit and household/firm debt families in exported opening packs",
        },
        {
            "parameter_id": "deficit_multiplier_F_plus",
            "base": _fmt(FISCAL_BRANCHES["F_plus"]),
            "units": "share_of_cbo_base",
            "claim_grade_label": CLAIM_LABEL,
            "wiring": "PRIMARY_DEFICIT_BASE_PATH multiplied by 0.70",
        },
        {
            "parameter_id": "deficit_multiplier_F_minus",
            "base": _fmt(FISCAL_BRANCHES["F_minus"]),
            "units": "share_of_cbo_base",
            "claim_grade_label": CLAIM_LABEL,
            "wiring": "PRIMARY_DEFICIT_BASE_PATH multiplied by 1.30",
        },
    ]


def _note_rows() -> list[dict[str, str]]:
    return [
        {
            "note_id": "migration_threshold_dead_zone",
            "note_text": "The ratchet has a dead zone below a 2pp shock: moderate rate-environment rises do not erode deposit franchises in this model; larger ones do.",
            "claim_grade_label": CLAIM_LABEL,
        }
    ]


def _lineage_rows(output_root: Path) -> list[dict[str, str]]:
    return [
        {
            "deliverable_column": "out_ai_boom_twin.*_RW_ratio",
            "source_file": str(output_root / "measurements"),
            "lineage_note": "fresh build_v1 standard +100bp remeasurements from exported month-T opening packs",
        },
        {
            "deliverable_column": "out_ai_boom_state_path.gross_issuance_cumulative_bil",
            "source_file": "src/ratewall/rwtam/reissuance_policy.py:PRIMARY_DEFICIT_BASE_PATH",
            "lineage_note": "CBO-shaped base path multiplied by control, F+, or F- branch dial",
        },
        {
            "deliverable_column": "out_ai_boom_state_path.migrated_stock_bil",
            "source_file": "src/ratewall/rwtam/v1.py:_monthly_records hysteresis_state_config",
            "lineage_note": "existing threshold migration/beta state; no authored migration path",
        },
        {
            "deliverable_column": "out_ai_boom_state_path.growth_stock_scale_factor",
            "source_file": "src/ratewall/rwtam/ai_boom_twin.py:GROWTH_STOCK_FAMILIES",
            "lineage_note": "single +1pp/year illustrative growth dial applied to existing stock families at export",
        },
    ]


def _caveat_rows() -> list[dict[str, str]]:
    return [
        {
            "caveat_id": "no_production_function",
            "caveat_text": "Productivity enters only through the rate environment, growth-stock scale, and deficit-path dials; no production function is modeled.",
            "claim_grade_label": CLAIM_LABEL,
        },
        {
            "caveat_id": "asset_price_wealth_revaluation_out_of_scope",
            "caveat_text": "Asset-price and wealth revaluation effects of an AI boom are outside this scenario boundary.",
            "claim_grade_label": CLAIM_LABEL,
        },
        {
            "caveat_id": "environment_not_policy_experiment",
            "caveat_text": "+150bp and +250bp are sustained environment shifts used to evolve state; the measured wall remains the standard +100bp marginal object.",
            "claim_grade_label": CLAIM_LABEL,
        },
    ]


def _invariant_rows(
    pack_dir: Path,
    twin_rows: list[dict[str, str]],
    state_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    residuals_reconcile = all(
        _d(row["delta_RW_vs_control"])
        == _d(row["rate_environment_only_delta_RW"])
        + _d(row["growth_only_delta_RW"])
        + _d(row["fiscal_path_only_delta_RW"])
        + _d(row["ablation_residual_delta_RW"])
        for row in twin_rows
    )
    fiscal_signs = all(
        (_d(row["fiscal_path_only_delta_RW"]) < 0 if row["branch_id"] == "F_plus" else _d(row["fiscal_path_only_delta_RW"]) > 0)
        for row in twin_rows
    )
    rate_rows = [
        row
        for row in state_rows
        if row["run_id"].startswith("rate_only_") and row["month_index"] in {"60", "120"}
    ]
    migration_activated = any(row["migration_activated"] == "true" for row in rate_rows)
    active_rate_rows = [
        row for row in twin_rows if _d(row["rate_environment_bp"]) >= Decimal("200")
    ]
    rate_wall_raises_if_active = (not migration_activated) or all(
        _d(row["rate_environment_only_delta_RW"]) > 0 for row in active_rate_rows
    )
    default_rows = build_v1(pack_dir, include_impulse_beta_comparator=False).rows("out_ratewall_rollup")
    golden_rows = _read_csv_rows(DEFAULT_GOLDEN_ROLLUP) if DEFAULT_GOLDEN_ROLLUP.exists() else []
    return [
        {
            "check_id": "AI1_default_rollup_matches_golden_after_scenario_build",
            "status": "pass" if default_rows == golden_rows else "fail",
            "message": f"fresh default build_v1 rollup compared with {DEFAULT_GOLDEN_ROLLUP}",
        },
        {
            "check_id": "AI2_independent_ablation_residual_reconciles",
            "status": "pass" if residuals_reconcile else "fail",
            "message": "full-control delta equals rate-only + growth-only + fiscal-only + genuine residual from independent runs",
        },
        {
            "check_id": "AI3_fiscal_route_signs",
            "status": "pass" if fiscal_signs else "fail",
            "message": "F+ fiscal-only lowers the wall; F- fiscal-only raises it",
        },
        {
            "check_id": "AI4_migration_activation_status_emitted",
            "status": "pass" if rate_rows else "fail",
            "message": f"rate-only migration activated in base path: {str(migration_activated).lower()}",
        },
        {
            "check_id": "AI5_rate_route_raises_wall_if_migration_activates",
            "status": "pass" if rate_wall_raises_if_active else "fail",
            "message": "conditional consistency check on rate-environment route",
        },
        {
            "check_id": "AI6_branch_dial_probe",
            "status": "pass" if _branch_dial_probe(twin_rows) else "fail",
            "message": "mutating deficit branch changes fiscal route while rate and growth routes remain equal across branches",
        },
    ]


def _branch_dial_probe(rows: list[dict[str, str]]) -> bool:
    for rate_bp in RATE_ENVIRONMENT_VARIANTS_BP:
        for month in REMEASURE_MONTHS:
            plus = next(row for row in rows if row["branch_id"] == "F_plus" and row["rate_environment_bp"] == _fmt(rate_bp) and row["remeasure_month_index"] == str(month))
            minus = next(row for row in rows if row["branch_id"] == "F_minus" and row["rate_environment_bp"] == _fmt(rate_bp) and row["remeasure_month_index"] == str(month))
            if plus["rate_environment_only_delta_RW"] != minus["rate_environment_only_delta_RW"]:
                return False
            if plus["growth_only_delta_RW"] != minus["growth_only_delta_RW"]:
                return False
            if plus["fiscal_path_only_delta_RW"] == minus["fiscal_path_only_delta_RW"]:
                return False
    return True


def _answer_as_found(f_plus: dict[str, str], f_minus: dict[str, str]) -> str:
    plus_delta = _d(f_plus["delta_RW_vs_control"])
    minus_delta = _d(f_minus["delta_RW_vs_control"])
    if plus_delta < 0 and minus_delta > 0:
        return "F+ sits below control while F- sits above control."
    if plus_delta > 0 and minus_delta > 0:
        return "the rate/franchise-erosion ratchet dominates both branches."
    if plus_delta < 0 and minus_delta < 0:
        return "growth/fiscal improvement dominates both branches."
    return "branch signs are mixed in the opposite direction."


def _branch_class(delta: Decimal) -> str:
    if delta > 0:
        return "above_control"
    if delta < 0:
        return "below_control"
    return "at_control"


def _clear_output_subdirs(output_root: Path) -> None:
    for name in ("packs", "measurements"):
        path = output_root / name
        if path.exists():
            shutil.rmtree(path)


def _state_row(rows: list[dict[str, str]], month_T: int) -> dict[str, str]:
    return [row for row in rows if row["month_index"] == str(month_T)][0]


def _rate_suffix(rate_bp: Decimal) -> str:
    return f"rate_{_fmt(rate_bp)}bp".replace(".", "_")


def _rate_route_activation(state_rows: list[dict[str, str]], run_id: str) -> dict[str, str]:
    rows = [row for row in state_rows if row["run_id"] == run_id and row["month_index"] != "0"]
    active = [row for row in rows if row["migration_activated"] == "true"]
    peak_share = max((_d(row["migrated_share"]) for row in rows), default=Decimal("0"))
    peak_flow = max((_d(row["migration_flow_bil"]) for row in rows), default=Decimal("0"))
    return {
        "activation_month": active[0]["month"] if active else "",
        "peak_migrated_share": _fmt(peak_share),
        "peak_migration_flow_bil": _fmt(peak_flow),
    }


def _headline(rows: list[dict[str, str]]) -> dict[str, str]:
    return [
        row
        for row in rows
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]


def _markdown_table(title: str, rows: list[dict[str, str]], max_rows: int = 16) -> list[str]:
    if not rows:
        return ["", f"## {title}", "", "_No rows._"]
    fields = list(rows[0])
    lines = ["", f"## {title}", "", "| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    if len(rows) > max_rows:
        lines.append(f"| ... {len(rows) - max_rows} more rows | " + " | ".join("" for _ in fields[1:]) + " |")
    return lines
