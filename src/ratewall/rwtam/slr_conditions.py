"""Scenario-only SLR-exemption conditions experiment for RWTAM."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtam.hysteresis import (
    CHECKABLE_DEPOSIT_FAMILY,
    _apply_total_family,
    _deadweight,
    _distress_result_for_shock,
    _write_opening,
)
from ratewall.rwtam.reissuance_policy import PRIMARY_DEFICIT_BASE_PATH
from ratewall.rwtam.scenarios import (
    FINANCIALIZATION_SCENARIO_IDS,
    _append_csv_rows,
    _financialization_config_rows,
)
from ratewall.rwtam.v1 import (
    BANDS,
    CURRENT_DEFAULT_OBJECT_STAMP,
    DEFAULT_DOSE_MODE,
    START_YEAR,
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
    _term_premium_parameter,
    _write_rows,
)


EXPERIMENT_ID = "rwtam_slr_conditions_20260703"
OUTPUT_DIR = Path("var/rwtam/scenarios/slr_conditions")
REPORT_PATH = Path("do/rwtam_slr_conditions_report_20260703.md")
ABSORPTION_REGIMES = {
    "normal_0342": Decimal("0.342"),
    "rrp_active_045_060": Decimal("0.50"),
}
SLR_TDC_BETA_SELECTOR_SUSPENSION = (
    "slr_conditions is suspended: unrepaired state-conditioned TDC beta selector "
    "ABSORPTION_REGIMES/_set_absorption_beta cannot enter the application"
)
DEFICIT_PATHS = {"cbo_base": Decimal("1"), "cbo_plus_50pct": Decimal("1.5")}
FINANCIALIZATION_STATES = ("base", "F-asset-25")
SLR_DELTAS = {"slr_shift_10pp": Decimal("0.10"), "slr_shift_25pp": Decimal("0.25")}
PERMANENCE_VARIANTS = {"temporary_2y": 2, "permanent": 10}
TP_SCENARIOS = {
    "tp_mild": {"10y": Decimal("-5"), "30y": Decimal("-8")},
    "tp_base": {"10y": Decimal("-15"), "30y": Decimal("-20")},
    "tp_high": {"10y": Decimal("-30"), "30y": Decimal("-40")},
}
HORIZONS = (1, 5, 10)
QUARANTINE_LABEL = (
    "hypothetical_ratio_one_illustration;"
    "shape_only_all_levels_meaningless;"
    "distress_calibration_invalid_at_this_leverage"
)
TEXTBOOK_LABEL = (
    "textbook_limit_fiat_state;"
    "shape_only_all_levels_meaningless;"
    "distress_calibration_invalid_at_this_leverage"
)
SLR_CAPTION_NOTE = (
    "Conditional SLR scenario: permanence matters, temporary relief can flip sign, "
    "and Mode-B uptake is an upper-bound assumption because bank portfolio demand is "
    "not endogenously capacity-bound here. Ratio-1/textbook endpoint rows are "
    "shape-only illustrations, not calibrated levels."
)


@dataclass(frozen=True)
class SlrConditionsResult:
    """CSV-ready SLR condition experiment output tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_slr_conditions_experiment(
    pack_dir: Path = Path("configs/rwtam/packs"),
    *,
    full_grid: bool = True,
    output_root: Path = OUTPUT_DIR,
) -> SlrConditionsResult:
    """Build the SLR conditions grid and quarantined fiat exhibits."""

    raise RuntimeError(SLR_TDC_BETA_SELECTOR_SUSPENSION)

    with localcontext() as context:
        context.prec = 28
        _verify_dependencies(pack_dir)
        _prepare_output_root(output_root)
        grid_rows, stimulus_rows, lineage_rows = _build_grid(pack_dir, full_grid, output_root)
        ranking_rows = _ranking_rows(grid_rows)
        fiat_rows, spectrum_rows, fiat_lineage = _fiat_exhibits(pack_dir, output_root)
        lineage_rows.extend(fiat_lineage)
        tables = {
            "out_slr_conditions_grid": grid_rows,
            "out_slr_conditions_ranking": ranking_rows,
            "out_slr_stimulus_leg": stimulus_rows,
            "out_slr_fiat_response_curve": fiat_rows,
            "out_slr_spectrum": spectrum_rows,
            "out_slr_lineage": lineage_rows,
            "out_slr_disposition": _disposition_rows(),
            "out_slr_scenario_config": _scenario_config_rows(),
        }
        return SlrConditionsResult(tables=_captioned_tables(tables, SLR_CAPTION_NOTE))


def _prepare_output_root(output_root: Path) -> None:
    for name in ("packs", "measurements", "stimulus_leg", "fiat_packs"):
        path = output_root / name
        if path.exists():
            shutil.rmtree(path)


def write_slr_conditions_outputs(
    result: SlrConditionsResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_slr_conditions_report(
    result: SlrConditionsResult,
    output_path: Path = REPORT_PATH,
) -> Path:
    grid = result.rows("out_slr_conditions_grid")
    ranking = result.rows("out_slr_conditions_ranking")
    stimulus = result.rows("out_slr_stimulus_leg")
    coeffs = [_d(row["coefficient_delta_RW_per_bil_current_stimulus"]) for row in grid]
    lines = [
        "# RWTAM SLR-exemption conditions experiment",
        "",
        "Date: 2026-07-03.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: scenario-only, owner-flagged SLR exemption experiment. No headline or golden change.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
    ]
    for row in result.rows("out_slr_disposition"):
        lines.append(f"| {row['item']} | {row['disposition']} |")
    lines.extend(
        [
            "",
            "## Coefficient Distribution",
            "",
            "| metric | value |",
            "| --- | ---: |",
            f"| row_count | {len(grid)} |",
            f"| min | {_fmt(min(coeffs)) if coeffs else '0'} |",
            f"| median | {_fmt(sorted(coeffs)[len(coeffs) // 2]) if coeffs else '0'} |",
            f"| max | {_fmt(max(coeffs)) if coeffs else '0'} |",
            "",
            "## Hardest-Binding Conditions",
            "",
            "| rank | condition key | max coefficient | max delta RW 10y | stimulus |",
            "| ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in ranking[:12]:
        lines.append(
            "| {rank} | {condition_key} | {max_coefficient_delta_RW_per_bil_current_stimulus} | {max_delta_RW_10y} | {current_stimulus_bil_at_max} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Stimulus Legs",
            "",
            "| tp scenario | permanence | financialization | delta D now | current stimulus | source |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in stimulus:
        lines.append(
            "| {tp_scenario} | {permanence_variant} | {financialization_state} | {delta_D_bil} | {current_stimulus_bil} | `{slr_rollup_path}` |".format(
                **row
            )
        )
    lines.extend(_markdown_table("Conditions Grid", grid))
    lines.extend(_markdown_table("Fiat Response Curve", result.rows("out_slr_fiat_response_curve")))
    lines.extend(_markdown_table("Spectrum Exhibit", result.rows("out_slr_spectrum")))
    lines.extend(_markdown_table("Lineage", result.rows("out_slr_lineage")))
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- Mode-B capacity remains unconstrained. Because the exemption relaxes a constraint this model never binds, bank uptake is an upper-bound scenario, not an endogenous bank portfolio choice.",
            "- The term-premium leg is assumption-directional-support: it is the sign-reversed QT/supply add-on, with owner-flagged 10y and 30y values.",
            "- Temporary permanence affects the issuance-regime stock path after year 2. The current-stimulus row is a year-1 active-policy measurement.",
            "- The ratio-1 and textbook-limit points are by-fiat illustrations; all rows carry quarantine labels and must not be placed next to claim-grade surfaces without those labels.",
            "",
            "## Output Locations",
            "",
            f"- `{OUTPUT_DIR / 'out_slr_conditions_grid.csv'}`",
            f"- `{OUTPUT_DIR / 'out_slr_conditions_ranking.csv'}`",
            f"- `{OUTPUT_DIR / 'out_slr_fiat_response_curve.csv'}`",
            f"- `{OUTPUT_DIR / 'out_slr_spectrum.csv'}`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def cleanup_stale_hysteresis_redo_artifacts(
    output_dir: Path = Path("var/rwtam/scenarios/hysteresis_redo"),
) -> list[Path]:
    """Delete orphaned top-level hysteresis-redo CSVs with superseded labels."""

    stale_names = {
        "out_hysteresis_experiment.csv",
        "out_hysteresis_conditions.csv",
        "out_hysteresis_lineage.csv",
        "out_hysteresis_parameter_rows.csv",
        "out_hysteresis_r1_gate.csv",
        "out_illustrative_decomposition_superseded.csv",
        "out_response_crash_threshold.csv",
        "out_response_curve.csv",
        "out_hysteresis_caveats.csv",
    }
    removed: list[Path] = []
    if not output_dir.exists():
        return removed
    for path in sorted(output_dir.glob("*.csv")):
        if path.name in stale_names:
            path.unlink()
            removed.append(path)
    return removed


def _verify_dependencies(pack_dir: Path) -> None:
    from ratewall.rwtam.hysteresis import export_state_as_opening_pack

    if export_state_as_opening_pack is None:
        raise RuntimeError("missing dependency: export_state_as_opening_pack")
    pack = _effective_pack(_load_pack(pack_dir), True, True)
    _term_premium_parameter(pack, "delta_tp_qt_supply_addon_10y", "base")
    _term_premium_parameter(pack, "delta_tp_qt_supply_addon_30y", "base")
    default_10y = _slr_yield_delta_check(pack, "10y", False)
    relief_10y = _slr_yield_delta_check(pack, "10y", Decimal("-1"))
    if relief_10y >= default_10y:
        raise RuntimeError("qt_supply_stress signed relief dependency is not wired")


def _slr_yield_delta_check(
    pack: dict[str, list[dict[str, str]]],
    tenor: str,
    qt_supply_stress: bool | Decimal,
) -> Decimal:
    from ratewall.rwtam.v1 import _month_index_from_label, _treasury_yield_delta_bp

    return _treasury_yield_delta_bp(
        pack,
        tenor,
        "base",
        1,
        _month_index_from_label("2026-01"),
        DEFAULT_DOSE_MODE,
        qt_supply_stress=qt_supply_stress,
    )


def _build_grid(
    pack_dir: Path,
    full_grid: bool,
    output_root: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    absorption_items = tuple(ABSORPTION_REGIMES.items()) if full_grid else (("normal_0342", ABSORPTION_REGIMES["normal_0342"]),)
    deficit_items = tuple(DEFICIT_PATHS.items()) if full_grid else (("cbo_base", DEFICIT_PATHS["cbo_base"]),)
    financialization_items = FINANCIALIZATION_STATES if full_grid else ("base",)
    delta_items = tuple(SLR_DELTAS.items()) if full_grid else (("slr_shift_10pp", SLR_DELTAS["slr_shift_10pp"]),)
    permanence_items = tuple(PERMANENCE_VARIANTS.items()) if full_grid else (("permanent", PERMANENCE_VARIANTS["permanent"]),)
    tp_items = tuple(TP_SCENARIOS.items()) if full_grid else (("tp_base", TP_SCENARIOS["tp_base"]),)
    horizons = HORIZONS if full_grid else (1, 5)

    grid_rows: list[dict[str, str]] = []
    stimulus_rows: list[dict[str, str]] = []
    lineage_rows: list[dict[str, str]] = _base_lineage_rows(output_root)
    stimulus_cache: dict[tuple[str, str, str], dict[str, str]] = {}
    wall_cache: dict[tuple[str, str, str, str, str, int], dict[str, str]] = {}
    control_cache: dict[tuple[str, str, str, int], dict[str, str]] = {}
    with tempfile.TemporaryDirectory(prefix="rwtam_slr_conditions_") as tmp:
        tmp_root = Path(tmp)
        for fin_state in financialization_items:
            fin_pack = _financialization_pack(pack_dir, fin_state, tmp_root / f"fin_{fin_state}")
            for tp_scenario, tp_values in tp_items:
                for permanence_id, _active_years in permanence_items:
                    key = (fin_state, tp_scenario, permanence_id)
                    stimulus_cache[key] = _stimulus_leg(
                        fin_pack,
                        fin_state,
                        tp_scenario,
                        tp_values,
                        permanence_id,
                        output_root,
                    )
                    stimulus_rows.append(stimulus_cache[key])
            for absorption_id, baseline_beta in absorption_items:
                for deficit_id, deficit_mult in deficit_items:
                    for horizon in horizons:
                        control_key = (fin_state, absorption_id, deficit_id, horizon)
                        control_cache[control_key] = _wall_measurement(
                            fin_pack,
                            output_root,
                            scenario_id=f"control__{fin_state}__{absorption_id}__{deficit_id}__h{horizon}",
                            absorption_beta=baseline_beta,
                            deficit_multiplier=deficit_mult,
                            horizon_years=horizon,
                            active_years=horizon,
                            mutate_debt=True,
                        )
                    for delta_id, delta in delta_items:
                        treated_beta = min(Decimal("1"), baseline_beta + delta)
                        displaced_gap = delta
                        for permanence_id, active_years in permanence_items:
                            for horizon in horizons:
                                wall_key = (
                                    fin_state,
                                    absorption_id,
                                    deficit_id,
                                    delta_id,
                                    permanence_id,
                                    horizon,
                                )
                                wall_cache[wall_key] = _wall_measurement(
                                    fin_pack,
                                    output_root,
                                    scenario_id=f"treated__{fin_state}__{absorption_id}__{deficit_id}__{delta_id}__{permanence_id}__h{horizon}",
                                    absorption_beta=treated_beta,
                                    deficit_multiplier=deficit_mult,
                                    horizon_years=horizon,
                                    active_years=min(active_years, horizon),
                                    mutate_debt=True,
                                )
                                control = control_cache[(fin_state, absorption_id, deficit_id, horizon)]
                                treated = wall_cache[wall_key]
                                delta_rw = _d(treated["RW_ratio"]) - _d(control["RW_ratio"])
                                for tp_scenario, _tp_values in tp_items:
                                    stimulus = stimulus_cache[(fin_state, tp_scenario, permanence_id)]
                                    stimulus_bil = _d(stimulus["current_stimulus_bil"])
                                    coefficient = Decimal("0") if stimulus_bil == 0 else delta_rw / stimulus_bil
                                    grid_rows.append(
                                        {
                                            "experiment_id": EXPERIMENT_ID,
                                            "absorption_regime": absorption_id,
                                            "baseline_mode_B_share": _fmt(baseline_beta),
                                            "slr_shift_id": delta_id,
                                            "slr_shift_pp": _fmt(delta * Decimal("100")),
                                            "treated_mode_B_share": _fmt(treated_beta),
                                            "displaced_absorber_beta_gap": _fmt(displaced_gap),
                                            "deficit_path": deficit_id,
                                            "deficit_multiplier": _fmt(deficit_mult),
                                            "financialization_state": fin_state,
                                            "tp_scenario": tp_scenario,
                                            "permanence_variant": permanence_id,
                                            "horizon_years": str(horizon),
                                            "control_RW_ratio": control["RW_ratio"],
                                            "treated_RW_ratio": treated["RW_ratio"],
                                            "delta_RW_ratio": _fmt(delta_rw),
                                            "current_stimulus_bil": stimulus["current_stimulus_bil"],
                                            "coefficient_delta_RW_per_bil_current_stimulus": _fmt(coefficient),
                                            "control_pack_dir": control["pack_dir"],
                                            "treated_pack_dir": treated["pack_dir"],
                                            "control_rollup_path": control["rollup_path"],
                                            "treated_rollup_path": treated["rollup_path"],
                                            "claim_grade_label": "scenario_only_owner_flagged",
                                        }
                                    )
    return grid_rows, stimulus_rows, lineage_rows


def _financialization_pack(pack_dir: Path, scenario_id: str, out_dir: Path) -> Path:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(pack_dir, out_dir)
    if scenario_id == "base":
        return out_dir
    if scenario_id not in FINANCIALIZATION_SCENARIO_IDS:
        raise ValueError(f"unknown financialization state {scenario_id}")
    scenario_rows, split_rows, claim_rules = _financialization_config_rows(pack_dir, scenario_id)
    _append_csv_rows(out_dir / "scenario_adjustments.csv", scenario_rows)
    _append_csv_rows(out_dir / "household_stock_splits.csv", split_rows)
    _append_csv_rows(out_dir / "claim_processor_rules.csv", claim_rules)
    return out_dir


def _stimulus_leg(
    pack_dir: Path,
    financialization_state: str,
    tp_scenario: str,
    tp_values: dict[str, Decimal],
    permanence_id: str,
    output_root: Path,
) -> dict[str, str]:
    scenario_dir = output_root / "stimulus_leg" / financialization_state / tp_scenario / permanence_id
    scenario_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rwtam_slr_tp_") as tmp:
        slr_pack = Path(tmp) / "pack"
        shutil.copytree(pack_dir, slr_pack)
        _set_slr_tp_addons(slr_pack / "term_premium_response" / "rwtam_term_premium_response_bands_2026-07-02" / "parameters_term_premium.csv", tp_values)
        base_rollup = _rollup_only(pack_dir, qt_supply_stress=False)
        slr_rollup = _rollup_only(slr_pack, qt_supply_stress=True)
    base_path = scenario_dir / "control_out_ratewall_rollup.csv"
    slr_path = scenario_dir / "slr_out_ratewall_rollup.csv"
    _write_rows(base_path, base_rollup)
    _write_rows(slr_path, slr_rollup)
    base = _headline(base_rollup, "annual")
    slr = _headline(slr_rollup, "annual")
    delta_d = _d(slr["D_bil"]) - _d(base["D_bil"])
    delta_n = _d(slr["N_bil"]) - _d(base["N_bil"])
    stimulus = -((_d(slr["N_bil"]) - _d(slr["D_bil"])) - (_d(base["N_bil"]) - _d(base["D_bil"])))
    return {
        "experiment_id": EXPERIMENT_ID,
        "financialization_state": financialization_state,
        "tp_scenario": tp_scenario,
        "permanence_variant": permanence_id,
        "tp_10y_bp": _fmt(tp_values["10y"]),
        "tp_30y_bp": _fmt(tp_values["30y"]),
        "control_N_bil": base["N_bil"],
        "control_D_bil": base["D_bil"],
        "slr_N_bil": slr["N_bil"],
        "slr_D_bil": slr["D_bil"],
        "delta_N_bil": _fmt(delta_n),
        "delta_D_bil": _fmt(delta_d),
        "current_stimulus_bil": _fmt(stimulus),
        "control_rollup_path": str(base_path),
        "slr_rollup_path": str(slr_path),
        "claim_grade_label": "scenario_only_owner_flagged",
    }


def _set_slr_tp_addons(path: Path, tp_values: dict[str, Decimal]) -> None:
    rows = _read_csv_rows(path)
    for row in rows:
        pid = row["parameter_id"]
        if pid == "delta_tp_qt_supply_addon_10y":
            for band, value in zip(BANDS, (tp_values["10y"], tp_values["10y"], tp_values["10y"]), strict=True):
                row[band] = _fmt(value)
            row["input_basis_label"] = "owner_flagged_slr_supply_relief_directional_support"
        if pid == "delta_tp_qt_supply_addon_30y":
            for band, value in zip(BANDS, (tp_values["30y"], tp_values["30y"], tp_values["30y"]), strict=True):
                row[band] = _fmt(value)
            row["input_basis_label"] = "owner_flagged_slr_supply_relief_directional_support"
    _write_rows(path, rows)


def _wall_measurement(
    pack_dir: Path,
    output_root: Path,
    *,
    scenario_id: str,
    absorption_beta: Decimal,
    deficit_multiplier: Decimal,
    horizon_years: int,
    active_years: int,
    mutate_debt: bool,
) -> dict[str, str]:
    pack_out = output_root / "packs" / scenario_id
    if pack_out.exists():
        shutil.rmtree(pack_out)
    shutil.copytree(pack_dir, pack_out)
    _set_absorption_beta(pack_out / "absorption_modes.csv", absorption_beta)
    _apply_slr_issuance_state(
        pack_out / "opening_stocks.csv",
        absorption_beta=absorption_beta,
        deficit_multiplier=deficit_multiplier,
        horizon_years=horizon_years,
        active_years=active_years,
        mutate_debt=mutate_debt,
    )
    rollup = _rollup_only(pack_out, qt_supply_stress=False)
    measurement_dir = output_root / "measurements" / scenario_id
    measurement_dir.mkdir(parents=True, exist_ok=True)
    rollup_path = measurement_dir / "out_ratewall_rollup.csv"
    _write_rows(rollup_path, rollup)
    row = _headline(rollup, "annual")
    _write_rows(
        pack_out / "slr_state_inputs.csv",
        [
            {
                "scenario_id": scenario_id,
                "absorption_beta": _fmt(absorption_beta),
                "deficit_multiplier": _fmt(deficit_multiplier),
                "horizon_years": str(horizon_years),
                "active_years": str(active_years),
                "mutate_debt": str(mutate_debt).lower(),
            }
        ],
    )
    return {
        "N_bil": row["N_bil"],
        "D_bil": row["D_bil"],
        "RW_ratio": row["RW_ratio"],
        "pack_dir": str(pack_out),
        "rollup_path": str(rollup_path),
    }


def _set_absorption_beta(path: Path, beta: Decimal) -> None:
    rows = _read_csv_rows(path)
    current_b = next(_d(row["base"]) for row in rows if row["mode_id"] == "B")
    non_b_total = sum(_d(row["base"]) for row in rows if row["mode_id"] != "B")
    scale = Decimal("0") if non_b_total == 0 else (Decimal("1") - beta) / non_b_total
    for row in rows:
        if row["mode_id"] == "B":
            row["base"] = _fmt(beta)
        else:
            row["base"] = _fmt(_d(row["base"]) * scale)
        row["input_basis_label"] = f"{row['input_basis_label']};slr_conditions_absorption_regime_from_{_fmt(current_b)}"
    _write_rows(path, rows)


def _apply_slr_issuance_state(
    opening_path: Path,
    *,
    absorption_beta: Decimal,
    deficit_multiplier: Decimal,
    horizon_years: int,
    active_years: int,
    mutate_debt: bool,
) -> None:
    rows = _read_csv_rows(opening_path)
    opening = _opening_by_family({"opening_stocks": rows})
    gross_by_year = [
        PRIMARY_DEFICIT_BASE_PATH[index] * deficit_multiplier
        for index in range(horizon_years)
    ]
    debt_add = sum(gross_by_year, Decimal("0")) if mutate_debt else Decimal("0")
    deposit_add = sum(gross_by_year[:active_years], Decimal("0")) * absorption_beta
    if debt_add:
        _apply_total_family(rows, "treasury_bills", opening["treasury_bills"] + debt_add * Decimal("0.30"))
        _apply_total_family(
            rows,
            "treasury_notes_bonds_tips",
            opening["treasury_notes_bonds_tips"] + debt_add * Decimal("0.70"),
        )
    if deposit_add:
        _add_tdc_deposits_by_recipient_cells(rows, deposit_add)
    _write_opening(opening_path, rows)


def _add_tdc_deposits_by_recipient_cells(rows: list[dict[str, str]], amount: Decimal) -> None:
    splits = _read_csv_rows(Path("configs/rwtam/packs/tdc_recipient_splits.csv"))
    for row in splits:
        share = _d(row["base"])
        if share == 0:
            continue
        stock = amount * share
        rows.append(
            {
                "parameter_id": "slr_conditions_mode_B_created_deposit_stock",
                "cell_or_sector": f"holder={row['cell_or_sector']}|issuer=banks",
                "instrument_family": CHECKABLE_DEPOSIT_FAMILY,
                "low": _fmt(stock),
                "base": _fmt(stock),
                "high": _fmt(stock),
                "units": "$bn_current",
                "source_id": "slr_conditions_mode_B_created_deposits",
                "input_basis_label": "owner_flagged_slr_conditions_created_deposits",
                "rationale": "SLR conditions scenario-created deposits from Mode-B gross issuance absorption.",
            }
        )


def _rollup_only(
    pack_dir: Path,
    *,
    qt_supply_stress: bool | Decimal | str,
    shock_size_bp: Decimal = Decimal("100"),
    dose_mode: str = DEFAULT_DOSE_MODE,
    include_cumulative: bool = True,
) -> list[dict[str, str]]:
    pack = _effective_pack(_load_pack(pack_dir), True, True)
    phase6_pack = _load_pack(pack_dir / "phase6")
    monthly_records = _monthly_records(
        pack,
        include_tdc_settlement=True,
        shock_start_month="2026-01",
        dose_mode=dose_mode,
        include_tax_layer=True,
        qt_supply_stress=qt_supply_stress,
        shock_size_bp=shock_size_bp,
    )
    records = _annual_records_from_monthly(monthly_records)
    cashflow_annual = [_headline_row(record, "annual") for record in records]
    waterfall = _phase6_waterfall(cashflow_annual, phase6_pack)
    if include_cumulative:
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
        waterfall += _phase6_cumulative_waterfall(waterfall)
    return _rw_full_headline_from_waterfall(waterfall)


def _headline(rows: list[dict[str, str]], period_type: str) -> dict[str, str]:
    return [
        row
        for row in rows
        if row["period_type"] == period_type
        and (period_type != "annual" or row["period"] == str(START_YEAR))
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]


def _ranking_rows(grid_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in grid_rows:
        if row["horizon_years"] != "10":
            continue
        key = "|".join(
            [
                row["absorption_regime"],
                row["deficit_path"],
                row["financialization_state"],
                row["slr_shift_id"],
                row["permanence_variant"],
            ]
        )
        grouped.setdefault(key, []).append(row)
    ranked: list[tuple[Decimal, str, dict[str, str]]] = []
    for key, rows in grouped.items():
        max_row = max(rows, key=lambda item: _d(item["coefficient_delta_RW_per_bil_current_stimulus"]))
        ranked.append((_d(max_row["coefficient_delta_RW_per_bil_current_stimulus"]), key, max_row))
    out: list[dict[str, str]] = []
    for rank, (_coeff, key, row) in enumerate(sorted(ranked, reverse=True, key=lambda item: item[0]), start=1):
        out.append(
            {
                "rank": str(rank),
                "condition_key": key,
                "max_coefficient_delta_RW_per_bil_current_stimulus": row["coefficient_delta_RW_per_bil_current_stimulus"],
                "max_delta_RW_10y": row["delta_RW_ratio"],
                "current_stimulus_bil_at_max": row["current_stimulus_bil"],
                "tp_scenario_at_max": row["tp_scenario"],
                "claim_grade_label": "scenario_only_owner_flagged",
            }
        )
    return out


def _fiat_exhibits(
    pack_dir: Path,
    output_root: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    ratio_pack, ratio_inputs = _ratio_one_pack(pack_dir, output_root / "fiat_packs" / "ratio_one")
    textbook_pack, textbook_inputs = _textbook_pack(pack_dir, output_root / "fiat_packs" / "textbook_limit")
    base_headline = _headline(_rollup_only(pack_dir, qt_supply_stress=False), "annual")
    ratio_headline = _headline(
        _rollup_only(ratio_pack, qt_supply_stress=False, include_cumulative=False),
        "annual",
    )
    textbook_headline = _headline(
        _rollup_only(textbook_pack, qt_supply_stress=False, include_cumulative=False),
        "annual",
    )
    fiat_rows = _response_curve_for_pack(
        ratio_pack,
        "hypothetical_ratio_one_illustration",
        QUARANTINE_LABEL,
        output_root,
    )
    spectrum = [
        _spectrum_row("textbook_limit_fiat_state", textbook_headline, TEXTBOOK_LABEL, textbook_inputs, str(textbook_pack)),
        _spectrum_row("calibrated_US_2026_default", base_headline, "claim_grade_default_surface", "none", str(pack_dir)),
        _spectrum_row("hypothetical_ratio_one_illustration", ratio_headline, QUARANTINE_LABEL, ratio_inputs, str(ratio_pack)),
    ]
    lineage = [
        {
            "deliverable_column": "out_slr_fiat_response_curve",
            "source_file": str(output_root / "fiat_response_curve" / "hypothetical_ratio_one_illustration"),
            "lineage_note": "build_v1 shock pairs plus distress deadweight; fiat opening state documented in fiat_illustration_inputs",
        },
        {
            "deliverable_column": "out_slr_spectrum",
            "source_file": f"{textbook_pack};{pack_dir};{ratio_pack}",
            "lineage_note": "three fresh rollup-only measurements from opening packs",
        },
    ]
    return fiat_rows, spectrum, lineage


def _ratio_one_pack(pack_dir: Path, out_dir: Path) -> tuple[Path, str]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(pack_dir, out_dir)
    debt_multiplier = Decimal("3")
    deposit_multiplier = Decimal("37")
    debt_families = [
        "treasury_bills",
        "treasury_notes_bonds_tips",
        "credit_card_revolving",
        "auto_installment_debt",
        "personal_installment_debt",
        "student_loans_private",
        "c_and_i_depository_loans",
        "cre_mortgages_floating",
        "cre_mortgages_fixed",
        "corporate_bonds",
        "syndicated_loans",
        "mortgages_arm",
        "heloc",
        "mortgages_fixed",
    ]
    _scale_families(out_dir / "opening_stocks.csv", debt_families, debt_multiplier)
    _scale_families(out_dir / "opening_stocks.csv", ["deposits_checkable", "deposits_savings_mmda", "deposits_time_cds"], deposit_multiplier)
    inputs = f"fiat_illustration_inputs:debt_multiplier={_fmt(debt_multiplier)};deposit_multiplier={_fmt(deposit_multiplier)};target_RW_approx=1.05"
    _write_rows(out_dir / "fiat_illustration_inputs.csv", [{"scenario_id": "hypothetical_ratio_one_illustration", "inputs": inputs}])
    return out_dir, inputs


def _textbook_pack(pack_dir: Path, out_dir: Path) -> tuple[Path, str]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(pack_dir, out_dir)
    families = [
        "treasury_bills",
        "treasury_notes_bonds_tips",
        "deposits_checkable",
        "deposits_savings_mmda",
        "deposits_time_cds",
        "mmf_shares",
        "mmf_short_funding_assets",
    ]
    _scale_families(out_dir / "opening_stocks.csv", families, Decimal("0.05"))
    inputs = "fiat_illustration_inputs:public_debt_and_interest_bearing_liquid_claims_multiplier=0.05"
    _write_rows(out_dir / "fiat_illustration_inputs.csv", [{"scenario_id": "textbook_limit_fiat_state", "inputs": inputs}])
    return out_dir, inputs


def _scale_families(opening_path: Path, families: list[str], multiplier: Decimal) -> None:
    rows = _read_csv_rows(opening_path)
    for row in rows:
        if row["instrument_family"] in families:
            for band in BANDS:
                row[band] = _fmt(_d(row[band]) * multiplier)
            row["input_basis_label"] = f"{row['input_basis_label']};fiat_illustration"
    _write_opening(opening_path, rows)


def _response_curve_for_pack(
    pack_dir: Path,
    state_id: str,
    label: str,
    output_root: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    nd_by_shock: list[tuple[Decimal, Decimal]] = []
    starting = _headline(
        _rollup_only(pack_dir, qt_supply_stress=False, include_cumulative=False),
        "annual",
    )
    for shock_bp in (
        Decimal("25"),
        Decimal("50"),
        Decimal("100"),
        Decimal("150"),
        Decimal("200"),
        Decimal("300"),
        Decimal("400"),
        Decimal("500"),
        Decimal("800"),
        Decimal("1000"),
        Decimal("1500"),
    ):
        rollup = _rollup_only(
            pack_dir,
            qt_supply_stress=False,
            shock_size_bp=shock_bp,
            include_cumulative=False,
        )
        output_dir = output_root / "fiat_response_curve" / state_id / f"shock_{_fmt(shock_bp)}bp"
        output_dir.mkdir(parents=True, exist_ok=True)
        rollup_path = output_dir / "out_ratewall_rollup.csv"
        _write_rows(rollup_path, rollup)
        distress = _distress_result_for_shock(pack_dir, shock_bp)
        annual = _headline(rollup, "annual")
        deadweight = _deadweight(distress, "2026")
        nd = _d(annual["N_bil"]) - _d(annual["D_bil"]) - deadweight
        nd_by_shock.append((shock_bp, nd))
        rows.append(
            {
                "experiment_id": EXPERIMENT_ID,
                "state_id": state_id,
                "shock_bp": _fmt(shock_bp),
                "starting_RW_ratio": starting["RW_ratio"],
                "converted_N_bil": annual["N_bil"],
                "converted_D_bil": annual["D_bil"],
                "deadweight_bil": _fmt(deadweight),
                "net_demand_effect_bil": _fmt(nd),
                "distress_on": "true",
                "distress_calibration_status": "distress_calibration_invalid_at_this_leverage",
                "build_v1_rollup_path": str(rollup_path),
                "claim_grade_label": label,
            }
        )
    crossing = next((shock for shock, nd in nd_by_shock if nd < 0), None)
    rows.append(
        {
            "experiment_id": EXPERIMENT_ID,
            "state_id": state_id,
            "shock_bp": "s_star",
            "starting_RW_ratio": starting["RW_ratio"],
            "converted_N_bil": "",
            "converted_D_bil": "",
            "deadweight_bil": "",
            "net_demand_effect_bil": "",
            "distress_on": "true",
            "distress_calibration_status": "distress_calibration_invalid_at_this_leverage",
            "build_v1_rollup_path": "",
            "claim_grade_label": f"{label};s_star_bp={_fmt(crossing) if crossing is not None else 'not_crossed_in_grid'}",
        }
    )
    return rows


def _spectrum_row(
    state_id: str,
    headline: dict[str, str],
    label: str,
    inputs: str,
    pack_dir: str,
) -> dict[str, str]:
    return {
        "state_id": state_id,
        "RW_ratio": headline["RW_ratio"],
        "N_bil": headline["N_bil"],
        "D_bil": headline["D_bil"],
        "fiat_illustration_inputs": inputs,
        "pack_dir": pack_dir,
        "claim_grade_label": label,
    }


def _scenario_config_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for scenario_id, beta in ABSORPTION_REGIMES.items():
        rows.append({"config_type": "absorption_regime", "scenario_id": scenario_id, "value": _fmt(beta), "basis": "owner_flagged_conditions_grid"})
    for scenario_id, value in SLR_DELTAS.items():
        rows.append({"config_type": "slr_shift", "scenario_id": scenario_id, "value": _fmt(value), "basis": "owner_flagged_conditions_grid"})
    for scenario_id, values in TP_SCENARIOS.items():
        rows.append({"config_type": "term_premium_relief", "scenario_id": scenario_id, "value": f"10y={_fmt(values['10y'])};30y={_fmt(values['30y'])}", "basis": "Du-Forbes-Luzzetti_QT_mirror_directional_support_owner_flagged"})
    for scenario_id, value in DEFICIT_PATHS.items():
        rows.append({"config_type": "deficit_path", "scenario_id": scenario_id, "value": _fmt(value), "basis": "PRIMARY_DEFICIT_BASE_PATH_multiplier"})
    return rows


def _disposition_rows() -> list[dict[str, str]]:
    return [
        {"item": "dependency_export_state_as_opening_pack", "disposition": "verified_present_and_used_as_package_pattern_for_fresh_opening_pack_remeasurement"},
        {"item": "dependency_qt_supply_stress_signed", "disposition": "verified_signed_values lower long-end term-premium add-ons; boolean True preserved"},
        {"item": "S1_slr_primitive", "disposition": "implemented as Mode-B share shift, signed 10y/30y term-premium relief, and temporary/permanent active-year variants"},
        {"item": "S2_two_sided_measurement", "disposition": "current stimulus from fresh term-premium rollups; wall leg from evolved opening packs and fresh rollups"},
        {"item": "S3_conditions_grid", "disposition": "emits coefficient rows plus 10-year condition ranking; absorption axis uses tdcest beta vocabulary normal_0342 and rrp_active_045_060"},
        {"item": "S4_quarantined_exhibits", "disposition": "ratio-1 and textbook-limit fiat states emitted with mandatory quarantine labels"},
        {"item": "headline_goldens", "disposition": "untouched; scenario outputs only"},
    ]


def _base_lineage_rows(output_root: Path) -> list[dict[str, str]]:
    return [
        {
            "deliverable_column": "out_slr_conditions_grid.current_stimulus_bil",
            "source_file": str(output_root / "stimulus_leg"),
            "lineage_note": "control and SLR term-premium-relief out_ratewall_rollup.csv pairs",
        },
        {
            "deliverable_column": "out_slr_conditions_grid.delta_RW_ratio",
            "source_file": str(output_root / "measurements"),
            "lineage_note": "fresh rollup measurements from evolved opening packs; treated minus no-SLR control",
        },
        {
            "deliverable_column": "out_slr_conditions_grid.gross_issuance",
            "source_file": "src/ratewall/rwtam/reissuance_policy.py:PRIMARY_DEFICIT_BASE_PATH",
            "lineage_note": "gross issuance volume for SLR deposit creation and debt-stock path",
        },
    ]


def _markdown_table(title: str, rows: list[dict[str, str]], *, max_rows: int = 40) -> list[str]:
    if not rows:
        return ["", f"## {title}", "", "_No rows._"]
    fields = list(rows[0])
    lines = ["", f"## {title}", "", "| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join(row.get(field, "") for field in fields) + " |")
    if len(rows) > max_rows:
        lines.append(f"| ... | {len(rows) - max_rows} more rows omitted from markdown; CSV is authoritative |" + " |" * (len(fields) - 2))
    return lines


def _captioned_tables(
    tables: dict[str, list[dict[str, str]]],
    caption_note: str,
) -> dict[str, list[dict[str, str]]]:
    return {
        name: [
            row if row.get("caption_note") else row | {"caption_note": caption_note}
            for row in rows
        ]
        for name, rows in tables.items()
    }
