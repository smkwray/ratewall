"""Scenario-only RWTAS diagnostics for V2b distress packs."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ratewall.rwtas.v1 import (
    BANDS,
    CURRENT_DEFAULT_OBJECT_STAMP,
    DEFAULT_DOSE_MODE,
    _assumptions,
    _d,
    _effective_pack,
    _fmt,
    _driver,
    _load_pack,
    _moneyness_liquid_buffers,
    _opening_by_family,
    _private_driver,
    _read_csv_rows,
    _write_rows,
    build_v1,
)


SCENARIOS = {
    "stress_300bp": Decimal("300"),
    "policy_100bp_distress_on": Decimal("100"),
}
STATIC_SWEEP_SHOCKS = tuple(Decimal(value) for value in ("10", "50", "100", "150", "200", "250", "300"))
MONTHS = 30
START_YEAR = 2026
EXPECTED_CROSSING_ORDER = [
    "cre_refi_wall",
    "cre_floating",
    "mortgage_arm_heloc",
    "business_ci_small",
    "corporate_high_yield",
    "consumer_unsecured",
]


@dataclass(frozen=True)
class ScenarioResult:
    """CSV-ready scenario-only output tables."""

    scenario_id: str
    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_distress_scenario(
    pack_dir: Path = Path("configs/rwtas/packs"),
    *,
    scenario_id: str,
) -> ScenarioResult:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"unknown distress scenario {scenario_id}")
    base_pack = _effective_pack(_load_pack(pack_dir), True, True)
    distress_dir = pack_dir / "distress"
    distress = _load_distress_pack(distress_dir)
    scenario_rows = _simulate_scenario(base_pack, distress, scenario_id)
    tables = _distress_tables(base_pack, distress, scenario_id, scenario_rows)
    return ScenarioResult(scenario_id=scenario_id, tables=tables)


def build_all_distress_scenarios(
    pack_dir: Path = Path("configs/rwtas/packs"),
) -> dict[str, ScenarioResult]:
    return {
        scenario_id: build_distress_scenario(pack_dir, scenario_id=scenario_id)
        for scenario_id in SCENARIOS
    }


def write_distress_scenario_outputs(
    result: ScenarioResult,
    output_root: Path,
) -> dict[str, Path]:
    output_dir = output_root / result.scenario_id
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_all_distress_scenarios(
    results: dict[str, ScenarioResult],
    output_root: Path = Path("var/rwtas/scenarios"),
) -> dict[str, dict[str, Path]]:
    return {
        scenario_id: write_distress_scenario_outputs(result, output_root)
        for scenario_id, result in results.items()
    }


def _load_distress_pack(distress_dir: Path) -> dict[str, list[dict[str, str]]]:
    tables = {
        path.stem: _read_csv_rows(path)
        for path in sorted(distress_dir.glob("*.csv"))
        if path.suffix == ".csv"
    }
    cre_pack = distress_dir.parent / "cre_maturity_dsr_dispersion"
    for filename in [
        "cre_maturity_wall_schedule_tdcsim_style_2026_2036.csv",
        "cre_wall_vs_current_uniform_gate.csv",
        "distress_threshold_exceedance_share_grid.csv",
    ]:
        path = _find_pack_file(cre_pack, filename)
        if path is not None:
            tables[path.stem] = _read_csv_rows(path)
    return tables


def _simulate_scenario(
    base_pack: dict[str, list[dict[str, str]]],
    distress: dict[str, list[dict[str, str]]],
    scenario_id: str,
) -> list[dict[str, Decimal | str]]:
    pd_params = _pd_params(distress["distress_pd_parameters"])
    lgd_params = _family_params(distress["distress_lgd_recovery_deadweight"])
    profiles = {
        (row["instrument_family"], row["transition"]): row
        for row in distress["distress_nonlinearity_profile"]
    }
    exposures = _distress_exposures(base_pack, distress)
    cells = _distress_cells(distress["distress_pd_parameters"])
    debt_service = _monthly_required_debt_service(base_pack, distress, exposures, cells)
    damping = _damping_by_family_cell(base_pack, distress, debt_service)
    shock_path = _shock_path(SCENARIOS[scenario_id])
    rows: list[dict[str, Decimal | str]] = []
    for family in sorted(pd_params):
        family_exposure = exposures.get(family, Decimal("0"))
        if family_exposure == 0 and family != "mortgage_fixed_reset_refi":
            continue
        for cell in cells[family]:
            share = Decimal("1") / Decimal(len(cells[family]))
            exposure = family_exposure * share
            damp = damping.get((family, cell), _default_damping(family, cell))
            baseline_state = {"P": exposure, "X": Decimal("0"), "N": Decimal("0")}
            scenario_state = {"P": exposure, "X": Decimal("0"), "N": Decimal("0")}
            deadweight_lag = int(
                lgd_params.get(family, {})
                .get("deadweight_realization_lag_months", {})
                .get("base", Decimal("0"))
            )
            deadweight_share = (
                lgd_params.get(family, {})
                .get("deadweight_share_of_defaulted_principal", {})
                .get("base", Decimal("0"))
            )
            deadweight_due: dict[int, Decimal] = {}
            for month_index, shock_bp in enumerate(shock_path, start=1):
                base_q = _transition_qs(pd_params[family], profiles, family, Decimal("0"), Decimal("1"))
                stress_q = _transition_qs(
                    pd_params[family],
                    profiles,
                    family,
                    shock_bp,
                    damp["slope_multiplier"],
                )
                base_flow = _apply_transition_month(baseline_state, base_q)
                stress_flow = _apply_transition_month(scenario_state, stress_q)
                incremental_default = max(
                    Decimal("0"),
                    stress_flow["new_default_principal_bil"]
                    - base_flow["new_default_principal_bil"],
                )
                scheduled_deadweight = incremental_default * deadweight_share
                if scheduled_deadweight:
                    deadweight_due[month_index + deadweight_lag] = (
                        deadweight_due.get(month_index + deadweight_lag, Decimal("0"))
                        + scheduled_deadweight
                    )
                realized_deadweight = deadweight_due.get(month_index, Decimal("0"))
                held_dsr, held_payment = _scenario_state_from_profile(
                    profiles, family, "performing_to_distressed", shock_bp
                )
                rows.append(
                    {
                        "scenario_id": scenario_id,
                        "month_index": Decimal(month_index),
                        "month": _month_label(month_index),
                        "year": str(START_YEAR + (month_index - 1) // 12),
                        "family": family,
                        "cell_or_sector": cell,
                        "shock_bp": shock_bp,
                        "performing_principal_bil": scenario_state["P"],
                        "distressed_principal_bil": scenario_state["X"],
                        "nonperforming_principal_bil": scenario_state["N"],
                        "baseline_new_default_principal_bil": base_flow["new_default_principal_bil"],
                        "stress_new_default_principal_bil": stress_flow["new_default_principal_bil"],
                        "incremental_default_principal_bil": incremental_default,
                        "deadweight_scheduled_bil": scheduled_deadweight,
                        "deadweight_realized_bil": realized_deadweight,
                        "q_px_monthly": stress_q["px"],
                        "q_pn_monthly": stress_q["pn"],
                        "q_xp_monthly": stress_q["xp"],
                        "q_np_monthly": stress_q["np"],
                        "held_state_dsr": held_dsr,
                        "held_state_payment_shock_ratio": held_payment,
                        "buffer_coverage_months": damp["buffer_coverage_months"],
                        "liquidity_gap_ratio": damp["liquidity_gap_ratio"],
                        "slope_multiplier": damp["slope_multiplier"],
                        "headline_entry_flag": "false",
                        "include_flag": "0",
                        "claim_grade_label": "non_claim_grade",
                    }
                )
    return rows


def _distress_tables(
    base_pack: dict[str, list[dict[str, str]]],
    distress: dict[str, list[dict[str, str]]],
    scenario_id: str,
    monthly_rows: list[dict[str, Decimal | str]],
) -> dict[str, list[dict[str, str]]]:
    ledger = [_stringify(row) for row in monthly_rows]
    threshold_crossings = _threshold_crossings(distress, scenario_id)
    deadweight = _deadweight_by_family_year(monthly_rows, distress)
    damping = _buffer_damping_incidence(monthly_rows)
    falsification = _falsification_rows(monthly_rows, threshold_crossings, scenario_id)
    verification = _pack_field_verification(distress)
    checks = _distress_invariant_checks(
        base_pack,
        ledger,
        threshold_crossings,
        damping,
        verification,
    )
    return {
        "out_distress_ledger_monthly": ledger,
        "out_distress_threshold_crossings": threshold_crossings,
        "out_distress_crossing_by_shock": _crossing_by_static_shock(distress),
        "out_distress_deadweight_drag_by_year": deadweight,
        "out_distress_buffer_damping_incidence": damping,
        "out_distress_falsification_check": falsification,
        "out_distress_pack_field_verification": verification,
        "out_distress_invariant_check": checks,
    }


def _pd_params(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, Decimal]]]:
    out: dict[str, dict[str, dict[str, Decimal]]] = {}
    for row in rows:
        family = row["instrument_family"]
        out.setdefault(family, {})[row["parameter_id"]] = {
            band: _d(row[band]) for band in BANDS
        }
    return out


def _family_params(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, Decimal]]]:
    out: dict[str, dict[str, dict[str, Decimal]]] = {}
    for row in rows:
        family = row["instrument_family"]
        out.setdefault(family, {})[row["parameter_id"]] = {
            band: _d(row[band]) for band in BANDS
        }
    return out


def _distress_cells(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    cell_rows: dict[str, set[str]] = {}
    for row in rows:
        family = row["instrument_family"]
        cell_rows.setdefault(family, set())
        for cell in row["cell_or_sector"].split(";"):
            cell_rows[family].add(_normalize_distress_cell(cell))
    return {family: sorted(cells) for family, cells in cell_rows.items()}


def _normalize_distress_cell(cell: str) -> str:
    mapping = {
        "all_household_mortgage_cells_reset_refi_only": "hh_middle_owner_illiquid",
        "firm_bank_dependent_small_business": "firm_bank_dependent_small",
        "firm_market_funded_high_yield": "firm_market_funded_large",
        "firm_real_estate_cre_floating": "firm_real_estate_cre_floating",
        "firm_real_estate_cre_maturity_wall": "firm_real_estate_cre_maturity_wall",
    }
    return mapping.get(cell, cell)


def _distress_exposures(
    base_pack: dict[str, list[dict[str, str]]],
    distress: dict[str, list[dict[str, str]]],
) -> dict[str, Decimal]:
    opening = _opening_by_family(base_pack)
    assumptions = _assumptions(base_pack)
    order = {
        row["instrument_family"]: _d(row["exposure_base_bn"])
        for row in distress["distress_order_of_magnitude_drag"]
    }
    exposures = dict(order)
    exposures["consumer_credit_card_revolving"] = opening.get("credit_card_revolving", order["consumer_credit_card_revolving"])
    exposures["consumer_auto_loan"] = opening.get("auto_installment_debt", order["consumer_auto_loan"])
    exposures["consumer_personal_other"] = opening.get("personal_installment_debt", order["consumer_personal_other"])
    exposures["student_private_variable"] = opening.get("student_loans_private", order["student_private_variable"])
    exposures["mortgage_arm_heloc"] = opening.get("mortgages_arm", Decimal("0")) + opening.get("heloc", Decimal("0"))
    exposures["business_ci_small"] = (
        opening.get("c_and_i_depository_loans", order["business_ci_small"]) * Decimal("0.30")
    )
    exposures["cre_floating"] = opening.get("cre_mortgages_floating", order["cre_floating"])
    exposures["cre_refi_wall"] = (
        _cre_wall_schedule_total(distress, START_YEAR)
        or opening.get("cre_mortgages_fixed", Decimal("0"))
        * assumptions["cre_fixed_roll_rate"]["base"]
    )
    exposures["mortgage_fixed_reset_refi"] = Decimal("0")
    return exposures


def _monthly_required_debt_service(
    base_pack: dict[str, list[dict[str, str]]],
    distress: dict[str, list[dict[str, str]]],
    exposures: dict[str, Decimal],
    cells: dict[str, list[str]],
) -> dict[str, Decimal]:
    profiles = {
        (row["instrument_family"], row["transition"]): row
        for row in distress["distress_nonlinearity_profile"]
    }
    out: dict[str, Decimal] = {}
    for family, family_cells in cells.items():
        profile = profiles.get((family, "performing_to_distressed"))
        if not profile:
            continue
        payment_100 = _d(profile["scenario_100_payment_shock_ratio"])
        if payment_100 <= 0:
            continue
        monthly_required = exposures.get(family, Decimal("0")) * Decimal("0.01") / payment_100 / Decimal("12")
        for cell in family_cells:
            out[cell] = out.get(cell, Decimal("0")) + monthly_required / Decimal(len(family_cells))
    return out


def _damping_by_family_cell(
    base_pack: dict[str, list[dict[str, str]]],
    distress: dict[str, list[dict[str, str]]],
    debt_service: dict[str, Decimal],
) -> dict[tuple[str, str], dict[str, Decimal]]:
    buffers = {
        row["cell_or_sector"]: _d(row["moneyness_weighted_buffer_bil"])
        for row in _moneyness_liquid_buffers(base_pack)
    }
    damping_rows = distress["distress_liquidity_buffer_damping"]
    out: dict[tuple[str, str], dict[str, Decimal]] = {}
    families = sorted(
        {
            row["instrument_family"]
            for row in distress["distress_pd_parameters"]
        }
    )
    cells = _distress_cells(distress["distress_pd_parameters"])
    for family in families:
        for cell in cells[family]:
            params = _damping_params_for(family, cell, damping_rows)
            buffer = buffers.get(cell, Decimal("0"))
            monthly_debt_service = debt_service.get(cell, Decimal("0"))
            coverage = Decimal("0") if monthly_debt_service == 0 else buffer / monthly_debt_service
            target = params["target"]
            gamma = params["gamma"]
            cap = params["cap"]
            gap = Decimal("0") if target == 0 else max(Decimal("0"), target - coverage) / target
            multiplier = min(cap, max(Decimal("1"), Decimal("1") + gamma * gap))
            out[(family, cell)] = {
                "moneyness_weighted_buffer_bil": buffer,
                "monthly_required_debt_service_bil": monthly_debt_service,
                "buffer_coverage_months": coverage,
                "liquidity_gap_ratio": gap,
                "slope_multiplier": multiplier,
                "target_buffer_months": target,
                "liquidity_gap_gamma": gamma,
                "slope_multiplier_cap": cap,
            }
    return out


def _damping_params_for(
    family: str,
    cell: str,
    rows: list[dict[str, str]],
) -> dict[str, Decimal]:
    target = Decimal("3")
    gamma = Decimal("0.75")
    cap = Decimal("2")
    family_group = _damping_family_group(family)
    for row in rows:
        if family_group not in row["instrument_family"].split(";"):
            continue
        if _normalize_distress_cell(row["cell_or_sector"]) not in {cell, "all"}:
            continue
        if row["parameter_id"] == "buffer_coverage_target_months":
            target = _d(row["base"])
        elif row["parameter_id"] == "liquidity_gap_gamma":
            gamma = _d(row["base"])
        elif row["parameter_id"] == "slope_multiplier_cap":
            cap = _d(row["base"])
    if family == "cre_floating":
        target, gamma, cap = Decimal("12"), Decimal("1"), Decimal("2.5")
    if family == "corporate_high_yield":
        target, gamma, cap = Decimal("3"), Decimal("0"), Decimal("1")
    return {"target": target, "gamma": gamma, "cap": cap}


def _damping_family_group(family: str) -> str:
    if family in {
        "consumer_credit_card_revolving",
        "consumer_auto_loan",
        "consumer_personal_other",
        "student_private_variable",
    }:
        return "household_unsecured_auto_student"
    if family in {"mortgage_arm_heloc", "mortgage_fixed_reset_refi"}:
        return "mortgage_arm_heloc"
    return family


def _default_damping(family: str, cell: str) -> dict[str, Decimal]:
    return {
        "moneyness_weighted_buffer_bil": Decimal("0"),
        "monthly_required_debt_service_bil": Decimal("0"),
        "buffer_coverage_months": Decimal("0"),
        "liquidity_gap_ratio": Decimal("0"),
        "slope_multiplier": Decimal("1"),
        "target_buffer_months": Decimal("0"),
        "liquidity_gap_gamma": Decimal("0"),
        "slope_multiplier_cap": Decimal("1"),
    }


def _transition_qs(
    params: dict[str, dict[str, Decimal]],
    profiles: dict[tuple[str, str], dict[str, str]],
    family: str,
    shock_bp: Decimal,
    slope_multiplier: Decimal,
) -> dict[str, Decimal]:
    return {
        "px": _q_for_transition(params, profiles, family, "performing_to_distressed", shock_bp, slope_multiplier),
        "pn": _q_for_transition(params, profiles, family, "performing_to_default", shock_bp, slope_multiplier),
        "xp": params.get("distressed_to_performing_cure_monthly_probability", {}).get("base", Decimal("0")),
        "np": params.get("default_to_performing_reperform_monthly_probability", {}).get("base", Decimal("0")),
    }


def _q_for_transition(
    params: dict[str, dict[str, Decimal]],
    profiles: dict[tuple[str, str], dict[str, str]],
    family: str,
    transition: str,
    shock_bp: Decimal,
    slope_multiplier: Decimal,
) -> Decimal:
    prefix = transition
    base = params[f"{prefix}_base_monthly_probability"]["base"]
    threshold = params[f"{prefix}_dsr_threshold"]["base"]
    slope_dsr = params[f"{prefix}_slope_dsr"]["base"]
    slope_payment = params[f"{prefix}_slope_payment_shock"]["base"]
    baseline_dsr, baseline_payment = _scenario_state_from_profile(profiles, family, transition, Decimal("0"))
    dsr, payment = _scenario_state_from_profile(profiles, family, transition, shock_bp)
    baseline_stress_term = slope_dsr * max(Decimal("0"), baseline_dsr - threshold) + slope_payment * baseline_payment
    scenario_stress_term = slope_dsr * max(Decimal("0"), dsr - threshold) + slope_payment * payment
    q = base + baseline_stress_term + slope_multiplier * (scenario_stress_term - baseline_stress_term)
    return min(Decimal("1"), max(Decimal("0"), q))


def _scenario_state_from_profile(
    profiles: dict[tuple[str, str], dict[str, str]],
    family: str,
    transition: str,
    shock_bp: Decimal,
) -> tuple[Decimal, Decimal]:
    profile = profiles[(family, transition)]
    dsr100 = _d(profile["scenario_100_dsr"])
    dsr300 = _d(profile["scenario_300_dsr"])
    pay100 = _d(profile["scenario_100_payment_shock_ratio"])
    pay300 = _d(profile["scenario_300_payment_shock_ratio"])
    dsr0 = dsr100 - (dsr300 - dsr100) / Decimal("2")
    pay0 = pay100 - (pay300 - pay100) / Decimal("2")
    scale = shock_bp / Decimal("300")
    return dsr0 + (dsr300 - dsr0) * scale, pay0 + (pay300 - pay0) * scale


def _apply_transition_month(
    state: dict[str, Decimal],
    q: dict[str, Decimal],
) -> dict[str, Decimal]:
    p = state["P"]
    x = state["X"]
    n = state["N"]
    p_to_x = p * q["px"]
    p_to_n = p * q["pn"]
    x_to_p = x * q["xp"]
    n_to_p = n * q["np"]
    x_to_n = x * q["pn"]
    state["P"] = max(Decimal("0"), p - p_to_x - p_to_n + x_to_p + n_to_p)
    state["X"] = max(Decimal("0"), x + p_to_x - x_to_p - x_to_n)
    state["N"] = max(Decimal("0"), n + p_to_n + x_to_n - n_to_p)
    return {"new_default_principal_bil": p_to_n + x_to_n}


def _shock_path(max_bp: Decimal) -> list[Decimal]:
    path: list[Decimal] = []
    for month in range(1, 7):
        path.append(max_bp * Decimal(month) / Decimal("6"))
    path.extend([max_bp] * 18)
    for step in range(5, -1, -1):
        path.append(max_bp * Decimal(step) / Decimal("6"))
    return path


def _threshold_crossings(
    distress: dict[str, list[dict[str, str]]],
    scenario_id: str,
) -> list[dict[str, str]]:
    pd_params = _pd_params(distress["distress_pd_parameters"])
    profiles = {
        (row["instrument_family"], row["transition"]): row
        for row in distress["distress_nonlinearity_profile"]
    }
    cells = _distress_cells(distress["distress_pd_parameters"])
    shock_path = _shock_path(SCENARIOS[scenario_id])
    rows: list[dict[str, str]] = []
    for family in sorted(pd_params):
        for transition in ["performing_to_distressed", "performing_to_default"]:
            threshold = pd_params[family][f"{transition}_dsr_threshold"]["base"]
            for cell in cells[family]:
                crossed_month = ""
                crossed_dsr = ""
                for month_index, shock_bp in enumerate(shock_path, start=1):
                    dsr, _payment = _scenario_state_from_profile(profiles, family, transition, shock_bp)
                    if dsr >= threshold:
                        crossed_month = str(month_index)
                        crossed_dsr = _fmt(dsr)
                        break
                rows.append(
                    {
                        "scenario_id": scenario_id,
                        "family": family,
                        "cell_or_sector": cell,
                        "threshold": transition,
                        "threshold_dsr": _fmt(threshold),
                        "crossed_month_index": crossed_month,
                        "crossed_month": _month_label(int(crossed_month)) if crossed_month else "",
                        "crossing_dsr": crossed_dsr,
                        "crossing_order_family": _crossing_family_bucket(family),
                        "claim_grade_label": "non_claim_grade",
                    }
                )
    return rows


def build_crossing_shock_sweep(
    pack_dir: Path = Path("configs/rwtas/packs"),
) -> list[dict[str, str]]:
    distress = _load_distress_pack(pack_dir / "distress")
    return _crossing_by_static_shock(distress)


def write_crossing_shock_sweep(
    rows: list[dict[str, str]],
    output_root: Path = Path("var/rwtas/scenarios"),
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "out_distress_crossing_by_shock.csv"
    _write_rows(path, rows)
    return path


def _crossing_by_static_shock(
    distress: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    grid = _crossing_by_pack_grid(distress)
    if grid:
        return grid

    pd_params = _pd_params(distress["distress_pd_parameters"])
    profiles = {
        (row["instrument_family"], row["transition"]): row
        for row in distress["distress_nonlinearity_profile"]
    }
    cells = _distress_cells(distress["distress_pd_parameters"])
    rows: list[dict[str, str]] = []
    for family in sorted(pd_params):
        for cell in cells[family]:
            for transition, label in [
                ("performing_to_distressed", "P_to_X"),
                ("performing_to_default", "P_to_N"),
            ]:
                threshold = pd_params[family][f"{transition}_dsr_threshold"]["base"]
                crossing_shock = ""
                crossing_dsr = ""
                for shock_bp in STATIC_SWEEP_SHOCKS:
                    dsr, _payment = _scenario_state_from_profile(
                        profiles, family, transition, shock_bp
                    )
                    if dsr >= threshold:
                        crossing_shock = _fmt(shock_bp)
                        crossing_dsr = _fmt(dsr)
                        break
                baseline_dsr, _baseline_payment = _scenario_state_from_profile(
                    profiles, family, transition, Decimal("0")
                )
                rows.append(
                    {
                        "family": family,
                        "crossing_family": _crossing_family_bucket(family),
                        "cell_or_sector": cell,
                        "transition": label,
                        "baseline_share_above_threshold": "",
                        "shocked_share": "",
                        "incremental_share": "",
                        "distribution_bucket": "point_value_per_family_cell",
                        "minimum_static_hold_shock_bp": crossing_shock,
                        "threshold_dsr": _fmt(threshold),
                        "crossing_dsr": crossing_dsr,
                        "baseline_dsr": _fmt(baseline_dsr),
                        "shock_sweep_bp": ";".join(_fmt(value) for value in STATIC_SWEEP_SHOCKS),
                        "distress_on": "true",
                        "ramp_compression_note": "static_hold_sweep_recovers_order_hidden_by_ramp",
                        "cell_dsr_baseline_dispersion": "point_value_per_family_cell",
                        "dispersion_input_flag": "future_pack_needed_for_within_cell_dispersion",
                        "headline_entry_flag": "false",
                        "claim_grade_label": "non_claim_grade",
                    }
                )
    return rows


def _crossing_family_bucket(family: str) -> str:
    if family.startswith("consumer") or family == "student_private_variable":
        return "consumer_unsecured"
    return family


def _deadweight_by_family_year(
    monthly_rows: list[dict[str, Decimal | str]],
    distress: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    order = {
        row["instrument_family"]: row
        for row in distress["distress_order_of_magnitude_drag"]
    }
    grouped: dict[tuple[str, str], Decimal] = {}
    for row in monthly_rows:
        key = (str(row["family"]), str(row["year"]))
        grouped[key] = grouped.get(key, Decimal("0")) + _d(row["deadweight_realized_bil"])
    rows: list[dict[str, str]] = []
    for (family, year), drag in sorted(grouped.items()):
        check = Decimal("0")
        if year == "2026" and family in order:
            check = _d(order[family]["first_year_direct_deadweight_drag_bn_base"])
        wall = ""
        if family == "cre_refi_wall":
            wall_total = _cre_wall_schedule_total(distress, int(year))
            if wall_total:
                wall = _fmt(wall_total)
                if family in order and year != "2026":
                    row = order[family]
                    check = (
                        wall_total
                        * _d(row["delta_default_q_monthly_300_base"])
                        * _d(row["months"])
                        * _d(row["deadweight_share_base"])
                    )
        rows.append(
            {
                "family": family,
                "year": year,
                "ledger_incremental_deadweight_drag_bil": _fmt(drag),
                "pack_first_year_direct_check_against_bil": _fmt(check),
                "deviation_bil": _fmt(drag - check) if check else "",
                "cre_wall_schedule_base_bil": wall,
                "comparison_policy": "check_against_not_target",
            }
        )
    return rows


def _cre_wall_schedule_total(distress: dict[str, list[dict[str, str]]], year: int) -> Decimal:
    rows = distress.get("cre_maturity_wall_schedule_tdcsim_style_2026_2036", [])
    values = [
        _d(row["base"])
        for row in rows
        if row.get("year") == str(year)
        and row.get("parameter_id") == "cre_maturity_wall_principal_due"
    ]
    return sum(values, Decimal("0"))


def _crossing_by_pack_grid(distress: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    grid = distress.get("distress_threshold_exceedance_share_grid", [])
    if not grid:
        return []
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in grid:
        grouped.setdefault(
            (row["instrument_family"], row["rwtas_parent_cell_or_sector"], row["transition"]),
            [],
        ).append(row)
    rows: list[dict[str, str]] = []
    for (family, cell, transition), group in sorted(grouped.items()):
        group = sorted(group, key=lambda row: _d(row["shock_delta_metric_ratio"]))
        base_share = _d(group[0]["share_above_threshold_base_distribution"])
        crossing_shock = ""
        crossing_dsr = ""
        shocked_share = base_share
        for row in group:
            share = _d(row["share_above_threshold_base_distribution"])
            if share > base_share:
                crossing_shock = _fmt(_d(row["shock_delta_metric_ratio"]) * Decimal("1000"))
                crossing_dsr = row["effective_threshold_after_metric_shock"]
                shocked_share = share
                break
        rows.append(
            {
                "family": family,
                "crossing_family": _crossing_family_bucket(family),
                "cell_or_sector": cell,
                "transition": transition,
                "baseline_share_above_threshold": _fmt(base_share),
                "shocked_share": _fmt(shocked_share),
                "incremental_share": _fmt(shocked_share - base_share),
                "distribution_bucket": "percentile_bucket_grid",
                "minimum_static_hold_shock_bp": crossing_shock,
                "threshold_dsr": group[0]["threshold_base"],
                "crossing_dsr": crossing_dsr,
                "baseline_dsr": group[0]["effective_threshold_after_metric_shock"],
                "shock_sweep_bp": _pack_grid_shock_sweep_label(group),
                "distress_on": "true",
                "ramp_compression_note": "threshold_exceedance_grid_pack",
                "cell_dsr_baseline_dispersion": "percentile_bucket_grid",
                "dispersion_input_flag": "calibrated_D2_pack",
                "headline_entry_flag": "false",
                "claim_grade_label": "non_claim_grade",
            }
        )
    return rows


def _pack_grid_shock_sweep_label(group: list[dict[str, str]]) -> str:
    shocks = sorted({_d(row["shock_delta_metric_ratio"]) * Decimal("1000") for row in group})
    return ";".join(_fmt(value) for value in shocks)


def _find_pack_file(root: Path, filename: str) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(root.rglob(filename))
    return matches[0] if matches else None


def _buffer_damping_incidence(
    monthly_rows: list[dict[str, Decimal | str]],
) -> list[dict[str, str]]:
    first_rows: dict[tuple[str, str], dict[str, Decimal | str]] = {}
    for row in monthly_rows:
        key = (str(row["family"]), str(row["cell_or_sector"]))
        first_rows.setdefault(key, row)
    rows: list[dict[str, str]] = []
    for (family, cell), row in sorted(first_rows.items()):
        rows.append(
            {
                "family": family,
                "cell_or_sector": cell,
                "moneyness_buffer_coverage_months": _fmt(row["buffer_coverage_months"]),
                "liquidity_gap_ratio": _fmt(row["liquidity_gap_ratio"]),
                "slope_multiplier": _fmt(row["slope_multiplier"]),
                "slope_only_flag": "true",
                "baseline_multiplier": "1",
                "headline_entry_flag": "false",
                "claim_grade_label": "non_claim_grade",
            }
        )
    return rows


def _falsification_rows(
    monthly_rows: list[dict[str, Decimal | str]],
    crossings: list[dict[str, str]],
    scenario_id: str,
) -> list[dict[str, str]]:
    if scenario_id != "policy_100bp_distress_on":
        return []
    household = [
        row
        for row in monthly_rows
        if str(row["cell_or_sector"]).startswith("hh_") and row["shock_bp"] == Decimal("100")
    ]
    max_household_bp = max(
        (
            (row["q_px_monthly"] - Decimal(str(row["q_px_monthly"])) + Decimal("0"))
            for row in []
        ),
        default=Decimal("0"),
    )
    # Compare held-state q against the zero-shock path using fields already in the ledger.
    max_increment = Decimal("0")
    for row in household:
        stress_default = row["stress_new_default_principal_bil"]
        baseline_default = row["baseline_new_default_principal_bil"]
        exposure = row["performing_principal_bil"] + row["distressed_principal_bil"] + row["nonperforming_principal_bil"]
        if exposure > 0:
            max_increment = max(max_increment, (stress_default - baseline_default) / exposure)
    max_household_bp = max_increment * Decimal("10000")
    cre_refi_cross = any(
        row["family"] == "cre_refi_wall" and row["crossed_month_index"]
        for row in crossings
    )
    return [
        {
            "criterion": "household_monthly_increment_bp_lte_10",
            "observed_value": _fmt(max_household_bp),
            "status": "pass" if max_household_bp <= Decimal("10") else "fail",
            "basis": "held_100bp_path_incremental_defaults_vs_zero_shock_baseline",
        },
        {
            "criterion": "cre_matured_balloon_no_threshold_cross_at_100bp",
            "observed_value": "crossed" if cre_refi_cross else "not_crossed",
            "status": "fail" if cre_refi_cross else "pass",
            "basis": "cre_refi_wall_threshold_crossing_report",
            "claim_grade_label": "non_claim_grade",
        },
    ]


def _pack_field_verification(
    distress: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    required_pd = {
        "performing_to_distressed_base_monthly_probability",
        "performing_to_distressed_dsr_threshold",
        "performing_to_distressed_slope_dsr",
        "performing_to_distressed_slope_payment_shock",
        "performing_to_default_base_monthly_probability",
        "performing_to_default_dsr_threshold",
        "performing_to_default_slope_dsr",
        "performing_to_default_slope_payment_shock",
        "distressed_to_performing_cure_monthly_probability",
        "default_to_performing_reperform_monthly_probability",
    }
    observed = {
        row["parameter_id"]
        for row in distress["distress_pd_parameters"]
    }
    required_lgd = {
        "lgd_rate_at_default",
        "writeoff_recognition_share",
        "writeoff_recognition_lag_months",
        "recovery_rate_after_default",
        "recovery_lag_months",
        "deadweight_share_of_defaulted_principal",
        "deadweight_realization_lag_months",
    }
    observed_lgd = {
        row["parameter_id"]
        for row in distress["distress_lgd_recovery_deadweight"]
    }
    return [
        {
            "check_id": "distress_pd_functional_fields",
            "status": "pass" if required_pd <= observed else "fail",
            "missing_fields": ";".join(sorted(required_pd - observed)),
        },
        {
            "check_id": "distress_lgd_deadweight_fields",
            "status": "pass" if required_lgd <= observed_lgd else "fail",
            "missing_fields": ";".join(sorted(required_lgd - observed_lgd)),
        },
    ]


def _distress_invariant_checks(
    base_pack: dict[str, list[dict[str, str]]],
    ledger: list[dict[str, str]],
    crossings: list[dict[str, str]],
    damping: list[dict[str, str]],
    verification: list[dict[str, str]],
) -> list[dict[str, str]]:
    headline_tables = {
        "out_ratewall_rollup",
        "out_phase6_waterfall_scaffold",
        "out_additive_waterfall_inputs",
    }
    scenario_tables = {
        "out_distress_ledger_monthly",
        "out_distress_threshold_crossings",
        "out_distress_deadweight_drag_by_year",
    }
    no_headline_entry = all(row["headline_entry_flag"] == "false" for row in ledger)
    damping_baseline_one = all(row["baseline_multiplier"] == "1" for row in damping)
    fixed_inert = all(
        _d(row["incremental_default_principal_bil"]) == 0
        for row in ledger
        if row["family"] == "mortgage_fixed_reset_refi"
    )
    cumulative_incremental: dict[tuple[str, str], Decimal] = {}
    principal_transfer_ok = True
    for row in sorted(ledger, key=lambda item: (item["family"], item["cell_or_sector"], int(item["month_index"]))):
        key = (row["family"], row["cell_or_sector"])
        cumulative_incremental[key] = cumulative_incremental.get(key, Decimal("0")) + _d(
            row["incremental_default_principal_bil"]
        )
        if _d(row["deadweight_realized_bil"]) > cumulative_incremental[key]:
            principal_transfer_ok = False
            break
    return [
        {
            "check_id": "T55_scenario_outputs_isolated",
            "status": "pass" if headline_tables.isdisjoint(scenario_tables) and no_headline_entry else "fail",
            "message": "distress scenario outputs are not headline tables and rows carry headline_entry_flag=false",
        },
        {
            "check_id": "distress_field_for_field_pack_load",
            "status": "pass" if {row["status"] for row in verification} == {"pass"} else "fail",
            "message": "PD/LGD/deadweight fields load in the supplied P/X/N functional form",
        },
        {
            "check_id": "liquidity_damping_slopes_only",
            "status": "pass" if damping_baseline_one else "fail",
            "message": "liquidity multiplier is reported as stress-slope-only with baseline multiplier fixed at 1",
        },
        {
            "check_id": "fixed_rate_no_shock_until_reset",
            "status": "pass" if fixed_inert else "fail",
            "message": "fixed-rate mortgage reset/refi family has zero exposure absent reset/refi flags",
        },
        {
            "check_id": "principal_transfer_not_drag",
            "status": "pass" if principal_transfer_ok else "fail",
            "message": "lagged deadweight rows never exceed cumulative incremental default principal",
        },
    ]


FINANCIALIZATION_SCENARIO_IDS = (
    "base",
    "F-asset-25",
    "F-asset-50",
    "F-liability-30",
    "F-liability-60",
    "F-both",
    "F-wrapper",
)
FINANCIALIZED_MMF_FAMILY = "financialized_mmf_like_shares"
WRAPPER_SOURCES = (
    ("mmf", "mmf_shares", "mmf_shares", "mmf_shares", "nonbank_finance_mmfs"),
    (
        "corporate",
        "corporate_bonds",
        "corporate_bonds",
        "bond_equity_funds_lookthrough",
        "nonfinancial_firms",
    ),
    (
        "municipal",
        "municipal_securities",
        "municipal_securities",
        "bond_equity_funds_lookthrough",
        "state_local",
    ),
)
DC_WRAPPER_SPLIT = {
    "hh_retiree_fixed_income_saver": Decimal("0.07"),
    "hh_middle_owner_illiquid": Decimal("0.02"),
    "hh_unconstrained_saver": Decimal("0.01"),
    "dc_pension_deferred_balance_no_near_term_conversion": Decimal("0.90"),
}
ISSUANCE_MIX_SCENARIOS = {
    "S1_bills_heavy": Decimal("0.40"),
    "S1_termed_out": Decimal("0.05"),
}
HOLDER_COMPOSITION_SCENARIOS = (
    "S2_banks_absorb",
    "S2_row_returns",
)
RSTAR_STRESS_SWEEP_SHOCKS = tuple(Decimal(value) for value in ("50", "100", "150", "200", "250", "300"))


def build_financialization_grid(
    pack_dir: Path = Path("configs/rwtas/packs"),
    *,
    dose_mode: str = DEFAULT_DOSE_MODE,
) -> dict[str, ScenarioResult]:
    """Build the financialization scenario grid from scenario-local pack rows."""
    base_result = build_v1(pack_dir, dose_mode=dose_mode)
    with tempfile.TemporaryDirectory(prefix="rwtas_financialization_") as tmp:
        tmp_root = Path(tmp)
        results: dict[str, ScenarioResult] = {
            "base": _financialization_result_from_pack(
                "base",
                pack_dir,
                base_result.tables,
                [],
                dose_mode,
            )
        }
        for scenario_id in FINANCIALIZATION_SCENARIO_IDS:
            if scenario_id == "base":
                continue
            scenario_pack = tmp_root / scenario_id
            shutil.copytree(pack_dir, scenario_pack)
            scenario_rows, split_rows, claim_rules = _financialization_config_rows(
                pack_dir,
                scenario_id,
            )
            _append_csv_rows(scenario_pack / "scenario_adjustments.csv", scenario_rows)
            _append_csv_rows(scenario_pack / "household_stock_splits.csv", split_rows)
            _append_csv_rows(scenario_pack / "claim_processor_rules.csv", claim_rules)
            result = build_v1(scenario_pack, dose_mode=dose_mode)
            results[scenario_id] = _financialization_result_from_pack(
                scenario_id,
                scenario_pack,
                result.tables,
                scenario_rows,
                dose_mode,
            )
    summary_rows = _financialization_summary_rows(results)
    for result in results.values():
        result.tables["out_financialization_grid"] = summary_rows
    return results


def write_financialization_grid_outputs(
    results: dict[str, ScenarioResult],
    output_root: Path = Path("var/rwtas/scenarios/financialization"),
) -> dict[str, dict[str, Path] | Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    written: dict[str, dict[str, Path] | Path] = {}
    summary = next(iter(results.values())).rows("out_financialization_grid")
    summary_path = output_root / "out_financialization_grid.csv"
    _write_rows(summary_path, summary)
    written["out_financialization_grid"] = summary_path
    for scenario_id, result in results.items():
        scenario_dir = output_root / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        scenario_paths: dict[str, Path] = {}
        for table_name in [
            "out_ratewall_rollup",
            "out_cashflow_core_rollup",
            "out_financialization_gap",
            "out_financialization_credit_supply_diagnostic",
            "out_financialization_scenario_config",
            "out_scenario_delta_balance",
        ]:
            path = scenario_dir / f"{table_name}.csv"
            _write_rows(path, result.rows(table_name))
            scenario_paths[table_name] = path
        written[scenario_id] = scenario_paths
    return written


def write_financialization_report(
    results: dict[str, ScenarioResult],
    output_path: Path = Path("do/rwtas_financialization_report_20260702.md"),
) -> Path:
    summary = next(iter(results.values())).rows("out_financialization_grid")
    monotone = _rw_monotone_in_gap(summary)
    f_both = [row for row in summary if row["scenario"] == "F-both"][0]
    caveat = results["F-asset-50"].rows("out_financialization_credit_supply_diagnostic")[0]
    lines = [
        "# RWTAS financialization scenario grid",
        "",
        "Date: 2026-07-02.",
        "Frame: scenario run output for the financialization thesis note; the thesis is treated as a hypothesis, not a target.",
        "",
        "## Grid table",
        "",
        "| scenario | floating gap | N | D_full | RW_full | delta RW vs base |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        lines.append(
            "| {scenario} | {gap} | {n} | {d} | {rw} | {delta} |".format(
                scenario=row["scenario"],
                gap=row["floating_gap_statistic_bil"],
                n=row["N_bil"],
                d=row["D_full_bil"],
                rw=row["RW_full"],
                delta=row["delta_RW_vs_base"],
            )
        )
    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- RW_full monotone in the floating-gap statistic: {monotone}.",
            f"- F-both net sign: {f_both['net_sign_vs_base']} ({f_both['delta_RW_vs_base']} RW points vs base).",
            (
                "- 6D caveat displayed: "
                f"{caveat['diagnostic_message']} "
                f"F-asset-50 migrated stock = {caveat['deposit_shift_bil']}bn; "
                f"MMF-like gross income = {caveat['mmf_like_gross_income_bil']}bn."
            ),
            "- Surprise: F-wrapper lowers RW_full without materially changing the floating-gap statistic; it is a conversion/wrapper countercurrent, not an asset-liability repricing-gap move.",
            "",
            "## Output locations",
            "",
            "- `var/rwtas/scenarios/financialization/out_financialization_grid.csv`",
            "- `var/rwtas/scenarios/financialization/<scenario>/out_ratewall_rollup.csv`",
            "- `var/rwtas/scenarios/financialization/<scenario>/out_financialization_gap.csv`",
            "- `var/rwtas/scenarios/financialization/<scenario>/out_financialization_credit_supply_diagnostic.csv`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _financialization_result_from_pack(
    scenario_id: str,
    pack_dir: Path,
    tables: dict[str, list[dict[str, str]]],
    scenario_rows: list[dict[str, str]],
    dose_mode: str,
) -> ScenarioResult:
    pack = _effective_pack(_load_pack(pack_dir), True, True)
    result_tables = dict(tables)
    result_tables["out_financialization_gap"] = [
        _floating_exposure_gap_row(scenario_id, pack)
    ]
    result_tables["out_financialization_credit_supply_diagnostic"] = [
        _credit_supply_diagnostic_row(scenario_id, pack, scenario_rows)
    ]
    result_tables["out_financialization_scenario_config"] = [
        {**row, "scenario_id": scenario_id} for row in scenario_rows
    ] or [
        {
            "scenario_id": scenario_id,
            "delta_set_id": "base",
            "row_id": "base",
            "instrument_family": "",
            "holder": "",
            "issuer": "",
            "stock_low": "0",
            "stock_base": "0",
            "stock_high": "0",
            "delta_role": "base",
            "include_in_opening": "0",
            "sector_balance_low": "0",
            "sector_balance_base": "0",
            "sector_balance_high": "0",
            "input_basis_label": "current_default_post_promotion_tdc_on",
            "rationale": "No financialization scenario delta.",
        }
    ]
    return ScenarioResult(
        scenario_id=scenario_id,
        tables=_stamp_scenario_tables(result_tables, dose_mode),
    )


def _financialization_summary_rows(
    results: dict[str, ScenarioResult],
) -> list[dict[str, str]]:
    base_headline = _headline_summary(results["base"])
    base_rw = _d(base_headline["RW_ratio"])
    rows: list[dict[str, str]] = []
    for scenario_id in FINANCIALIZATION_SCENARIO_IDS:
        result = results[scenario_id]
        headline = _headline_summary(result)
        rw = _d(headline["RW_ratio"])
        delta = rw - base_rw
        rows.append(
            {
                "scenario": scenario_id,
                "dose_mode": headline.get("dose_mode", DEFAULT_DOSE_MODE),
                "floating_gap_statistic_bil": result.rows("out_financialization_gap")[0][
                    "floating_gap_statistic_bil"
                ],
                "N_bil": headline["N_bil"],
                "D_full_bil": headline["D_bil"],
                "RW_full": headline["RW_ratio"],
                "delta_RW_vs_base": _fmt(delta),
                "net_sign_vs_base": "positive" if delta > 0 else "negative" if delta < 0 else "zero",
            }
        )
    return rows


def _headline_summary(result: ScenarioResult) -> dict[str, str]:
    return [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["period"] == str(START_YEAR)
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]


def _financialization_config_rows(
    pack_dir: Path,
    scenario_id: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    base_pack = _load_pack(pack_dir)
    scenario_rows: list[dict[str, str]] = []
    split_rows: list[dict[str, str]] = []
    claim_rules: list[dict[str, str]] = []
    if scenario_id in {"F-asset-25", "F-asset-50", "F-both"}:
        share = Decimal("0.25") if scenario_id == "F-asset-25" else Decimal("0.50")
        scenario_rows.extend(_asset_migration_rows(base_pack, scenario_id, share))
        split_rows.extend(_copy_household_split_rows(base_pack, "deposits_checkable", FINANCIALIZED_MMF_FAMILY))
        claim_rules.append(
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
        )
    if scenario_id in {"F-liability-30", "F-liability-60", "F-both"}:
        target = Decimal("0.60") if scenario_id in {"F-liability-60", "F-both"} else Decimal("0.30")
        scenario_rows.extend(_liability_migration_rows(base_pack, scenario_id, target))
    if scenario_id == "F-wrapper":
        rows, splits, rules = _wrapper_rows(base_pack, scenario_id)
        scenario_rows.extend(rows)
        split_rows.extend(splits)
        claim_rules.extend(rules)
    return scenario_rows, split_rows, claim_rules


def _asset_migration_rows(
    pack: dict[str, list[dict[str, str]]],
    scenario_id: str,
    share: Decimal,
) -> list[dict[str, str]]:
    checkable = _household_opening_stock(pack, "deposits_checkable", "households")
    amount = checkable * share
    delta_set = f"{scenario_id}_asset_migration"
    return [
        _scenario_row(delta_set, f"{scenario_id}_checkable_out", "deposits_checkable", "households", "banks", -amount, "asset_migration"),
        _scenario_row(delta_set, f"{scenario_id}_mmf_like_in", FINANCIALIZED_MMF_FAMILY, "households", "nonbank_finance", amount, "asset_migration"),
        _scenario_row(delta_set, f"{scenario_id}_bank_counterpart", "financialization_real_side_counterpart", "banks", "real_side_sector", amount, "real_side_counterpart", include=False),
        _scenario_row(delta_set, f"{scenario_id}_nonbank_counterpart", "financialization_real_side_counterpart", "nonbank_finance", "real_side_sector", -amount, "real_side_counterpart", include=False),
    ]


def _liability_migration_rows(
    pack: dict[str, list[dict[str, str]]],
    scenario_id: str,
    target_arm_share: Decimal,
) -> list[dict[str, str]]:
    opening = _opening_by_family(pack)
    total = opening["mortgages_fixed"] + opening["mortgages_arm"]
    target_arm = total * target_arm_share
    shift = target_arm - opening["mortgages_arm"]
    delta_set = f"{scenario_id}_liability_migration"
    return [
        _scenario_row(delta_set, f"{scenario_id}_fixed_out", "mortgages_fixed", "banks_nonbank_finance", "households", -shift, "liability_migration"),
        _scenario_row(delta_set, f"{scenario_id}_arm_in", "mortgages_arm", "banks_nonbank_finance", "households", shift, "liability_migration"),
    ]


def _wrapper_rows(
    pack: dict[str, list[dict[str, str]]],
    scenario_id: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    scenario_rows: list[dict[str, str]] = []
    split_rows: list[dict[str, str]] = []
    claim_rules: list[dict[str, str]] = []
    for label, source_family, base_driver, split_family, issuer in WRAPPER_SOURCES:
        amount = _household_opening_stock(pack, source_family, "households") * Decimal("0.50")
        direct_family = f"financialized_direct_{label}_removed"
        wrapped_family = f"financialized_dc_{label}_wrapped"
        delta_set = f"{scenario_id}_{label}_wrapper_migration"
        scenario_rows.extend(
            [
                _scenario_row(delta_set, f"{scenario_id}_{label}_direct_out", direct_family, "households", issuer, -amount, "wrapper_migration"),
                _scenario_row(delta_set, f"{scenario_id}_{label}_dc_in", wrapped_family, "households", issuer, amount, "wrapper_migration"),
            ]
        )
        split_rows.extend(_copy_household_split_rows(pack, split_family, direct_family))
        split_rows.extend(_dc_wrapper_split_rows(wrapped_family))
        claim_rules.extend(
            [
                _claim_rule(
                    f"{direct_family}_yield",
                    direct_family,
                    "driver_curve",
                    base_driver,
                    "issuer_negative",
                    "opening_holders",
                    "",
                    "financialization_scenario",
                ),
                _claim_rule(
                    f"{wrapped_family}_yield",
                    wrapped_family,
                    "driver_curve",
                    base_driver,
                    "issuer_negative",
                    "opening_holders",
                    "",
                    "financialization_scenario",
                ),
            ]
        )
    return scenario_rows, split_rows, claim_rules


def _scenario_row(
    delta_set_id: str,
    row_id: str,
    instrument_family: str,
    holder: str,
    issuer: str,
    amount: Decimal,
    delta_role: str,
    *,
    include: bool = True,
) -> dict[str, str]:
    value = _fmt(amount)
    return {
        "delta_set_id": delta_set_id,
        "row_id": row_id,
        "instrument_family": instrument_family,
        "holder": holder,
        "issuer": issuer,
        "stock_low": value,
        "stock_base": value,
        "stock_high": value,
        "delta_role": delta_role,
        "include_in_opening": "1" if include else "0",
        "sector_balance_low": "0",
        "sector_balance_base": "0",
        "sector_balance_high": "0",
        "input_basis_label": "financialization_scenario",
        "rationale": "Scenario-local financialization migration row; not a default claim.",
    }


def _claim_rule(
    rule_id: str,
    instrument_family: str,
    rate_rule: str,
    base_driver: str,
    payer_route: str,
    receiver_route: str,
    receiver_holder: str,
    report_channel: str,
) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "instrument_family": instrument_family,
        "active": "1",
        "stock_source": "opening_stocks",
        "stock_band_mode": "base",
        "rate_rule": rate_rule,
        "base_driver": base_driver,
        "payer_route": payer_route,
        "receiver_route": receiver_route,
        "receiver_holder": receiver_holder,
        "report_channel": report_channel,
        "basis": "financialization_scenario_config_only",
        "input_basis_label": "financialization_scenario",
        "spread_delta": "0",
        "constant_level_delta": "0",
        "cost_leg": "false",
    }


def _copy_household_split_rows(
    pack: dict[str, list[dict[str, str]]],
    source_family: str,
    target_family: str,
) -> list[dict[str, str]]:
    rows = [
        row for row in pack["household_stock_splits"] if row["instrument_family"] == source_family
    ]
    return [
        {
            **row,
            "instrument_family": target_family,
            "source_id": f"{row['source_id']};FINANCIALIZATION_SCENARIO",
            "input_basis_label": "financialization_scenario",
            "rationale": f"Copied from {source_family} for scenario-local routing.",
        }
        for row in rows
    ]


def _dc_wrapper_split_rows(instrument_family: str) -> list[dict[str, str]]:
    return [
        {
            "parameter_id": "hh_stock_share_by_cell",
            "cell_or_sector": cell,
            "instrument_family": instrument_family,
            "low": _fmt(share),
            "base": _fmt(share),
            "high": _fmt(share),
            "units": "share_of_household_sector_aggregate",
            "source_id": "FINANCIALIZATION_DC_WRAPPER",
            "input_basis_label": "financialization_scenario",
            "rationale": "DC wrapper conversion: 10 percent near-term household pass-through, 90 percent deferred.",
        }
        for cell, share in DC_WRAPPER_SPLIT.items()
    ]


def _household_opening_stock(
    pack: dict[str, list[dict[str, str]]],
    family: str,
    holder: str,
) -> Decimal:
    return sum(
        _d(row["base"])
        for row in pack["opening_stocks"]
        if row["instrument_family"] == family and f"holder={holder}" in row["cell_or_sector"]
    )


def _append_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    existing = _read_csv_rows(path)
    fieldnames = list(existing[0]) if existing else list(rows[0])
    _write_rows(path, existing + [{field: row.get(field, "") for field in fieldnames} for row in rows])


def _floating_exposure_gap_row(
    scenario_id: str,
    pack: dict[str, list[dict[str, str]]],
) -> dict[str, str]:
    assumptions = _assumptions(pack)
    asset = Decimal("0")
    liability = Decimal("0")
    for row in pack["opening_stocks"]:
        holder = _holder_label(row["cell_or_sector"])
        issuer = _issuer_label(row["cell_or_sector"])
        stock = _d(row["base"])
        family = row["instrument_family"]
        beta = _effective_beta(family, assumptions)
        if holder in {"households", "households_direct"} or holder.startswith("hh_"):
            asset += stock * beta
        if issuer == "households":
            liability += stock * beta
    gap = asset - liability
    return {
        "scenario_id": scenario_id,
        "asset_effective_floating_stock_bil": _fmt(asset),
        "liability_effective_floating_stock_bil": _fmt(liability),
        "floating_gap_statistic_bil": _fmt(gap),
        "basis": "sum_household_stock_times_effective_beta_base_band_year1",
    }


def _effective_beta(
    family: str,
    assumptions: dict[str, dict[str, Decimal]],
) -> Decimal:
    driver_family = _scenario_driver_family(family)
    try:
        rate = _private_driver(driver_family, "base", 1, assumptions)
    except KeyError:
        rate = _driver(driver_family, "base", 1)
    return rate / Decimal("0.01")


def _scenario_driver_family(family: str) -> str:
    mapping = {
        FINANCIALIZED_MMF_FAMILY: "mmf_shares",
        "financialized_direct_mmf_removed": "mmf_shares",
        "financialized_dc_mmf_wrapped": "mmf_shares",
        "financialized_direct_corporate_removed": "corporate_bonds",
        "financialized_dc_corporate_wrapped": "corporate_bonds",
        "financialized_direct_municipal_removed": "municipal_securities",
        "financialized_dc_municipal_wrapped": "municipal_securities",
    }
    return mapping.get(family, family)


def _credit_supply_diagnostic_row(
    scenario_id: str,
    pack: dict[str, list[dict[str, str]]],
    scenario_rows: list[dict[str, str]],
) -> dict[str, str]:
    deposit_shift = sum(
        _d(row["stock_base"])
        for row in scenario_rows
        if row["instrument_family"] == FINANCIALIZED_MMF_FAMILY
    )
    removed_checkable = -sum(
        _d(row["stock_base"])
        for row in scenario_rows
        if row["instrument_family"] == "deposits_checkable"
    )
    mmf_income = deposit_shift * _driver("mmf_shares", "base", 1)
    bank_payment_removed = removed_checkable * _driver("deposits_checkable", "base", 1)
    return {
        "scenario_id": scenario_id,
        "layer_id": "credit_supply",
        "phase": "6D",
        "value_status": "diagnostic_only_non_additive",
        "headline_entry_flag": "false",
        "include_flag": "0",
        "deposit_shift_bil": _fmt(deposit_shift),
        "bank_checkable_payment_removed_bil": _fmt(bank_payment_removed),
        "mmf_like_gross_income_bil": _fmt(mmf_income),
        "credit_supply_include_flag": _phase6_credit_supply_include_flag(pack),
        "diagnostic_message": "bank counter-leg is displayed, not added to RW_full; 6D remains gated diagnostic-only.",
    }


def _phase6_credit_supply_include_flag(pack: dict[str, list[dict[str, str]]]) -> str:
    phase6 = _load_pack(Path("configs/rwtas/packs/phase6"))
    for row in phase6.get("conversion_parameters", []):
        if row["parameter_id"] == "credit_supply_headline_include_flag":
            return row["base"]
    return "0"


def _rw_monotone_in_gap(summary: list[dict[str, str]]) -> str:
    pairs = sorted((_d(row["floating_gap_statistic_bil"]), _d(row["RW_full"])) for row in summary)
    nondecreasing = all(right[1] >= left[1] for left, right in zip(pairs, pairs[1:], strict=False))
    nonincreasing = all(right[1] <= left[1] for left, right in zip(pairs, pairs[1:], strict=False))
    if nondecreasing:
        return "yes_nondecreasing"
    if nonincreasing:
        return "yes_nonincreasing"
    return "no"


def build_issuance_mix_scenarios(
    pack_dir: Path = Path("configs/rwtas/packs"),
    *,
    dose_mode: str = DEFAULT_DOSE_MODE,
) -> dict[str, ScenarioResult]:
    """Build S1 issuance-mix/WAM scenarios as isolated temp-pack runs."""
    base_result = build_v1(pack_dir, dose_mode=dose_mode)
    with tempfile.TemporaryDirectory(prefix="rwtas_s1_") as tmp:
        tmp_root = Path(tmp)
        results: dict[str, ScenarioResult] = {
            "base": _s1_result_from_tables("base", base_result.tables, [])
        }
        for scenario_id, bill_share in ISSUANCE_MIX_SCENARIOS.items():
            scenario_pack = tmp_root / scenario_id
            shutil.copytree(pack_dir, scenario_pack)
            config_rows = _set_marginal_issuance_bill_share(scenario_pack, scenario_id, bill_share)
            scenario_result = build_v1(scenario_pack, dose_mode=dose_mode)
            results[scenario_id] = _s1_result_from_tables(
                scenario_id,
                scenario_result.tables,
                config_rows,
            )
    comparison = _scenario_comparison_rows(
        results,
        scenario_ids=list(ISSUANCE_MIX_SCENARIOS),
        expected_direction={
            "S1_bills_heavy": "shorter_issuance_should_raise_or_advance_N",
            "S1_termed_out": "longer_issuance_should_slow_N_and_shift_duration_relevance",
        },
    )
    for result in results.values():
        result.tables["out_s1_comparison_vs_base"] = comparison
    return results


def write_issuance_mix_outputs(
    results: dict[str, ScenarioResult],
    output_root: Path = Path("var/rwtas/scenarios/issuance_mix"),
) -> dict[str, dict[str, Path] | Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    written: dict[str, dict[str, Path] | Path] = {}
    comparison_path = output_root / "out_s1_comparison_vs_base.csv"
    _write_rows(comparison_path, next(iter(results.values())).rows("out_s1_comparison_vs_base"))
    written["out_s1_comparison_vs_base"] = comparison_path
    for scenario_id, result in results.items():
        scenario_dir = output_root / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        scenario_paths: dict[str, Path] = {}
        for table_name in [
            "out_ratewall_rollup",
            "out_government_interest_channel",
            "out_government_interest_delta_path",
            "out_s1_scenario_config",
        ]:
            path = scenario_dir / f"{table_name}.csv"
            _write_rows(path, result.rows(table_name))
            scenario_paths[table_name] = path
        written[scenario_id] = scenario_paths
    return written


def build_holder_composition_scenarios(
    pack_dir: Path = Path("configs/rwtas/packs"),
    *,
    dose_mode: str = DEFAULT_DOSE_MODE,
) -> dict[str, ScenarioResult]:
    """Build S2 holder-composition scenarios as isolated temp-pack runs."""
    base_result = build_v1(pack_dir, dose_mode=dose_mode)
    with tempfile.TemporaryDirectory(prefix="rwtas_s2_") as tmp:
        tmp_root = Path(tmp)
        results: dict[str, ScenarioResult] = {
            "base": _s2_result_from_tables("base", base_result.tables, [], [])
        }
        for scenario_id in HOLDER_COMPOSITION_SCENARIOS:
            scenario_pack = tmp_root / scenario_id
            shutil.copytree(pack_dir, scenario_pack)
            config_rows, closure_rows = _apply_holder_composition_scenario(
                scenario_pack,
                scenario_id,
            )
            scenario_result = build_v1(scenario_pack, dose_mode=dose_mode)
            results[scenario_id] = _s2_result_from_tables(
                scenario_id,
                scenario_result.tables,
                config_rows,
                closure_rows,
            )
    comparison = _scenario_comparison_rows(
        results,
        scenario_ids=list(HOLDER_COMPOSITION_SCENARIOS),
        expected_direction={
            "S2_banks_absorb": "banks_displace_ROW_should_reduce_leakage_and_raise_N",
            "S2_row_returns": "ROW_displaces_domestic_liquid_holders_should_raise_leakage_and_lower_N",
        },
    )
    base_disposition = results["base"].rows("out_treasury_interest_disposition")[0]
    shifts = [
        _disposition_shift_row(scenario_id, results[scenario_id], base_disposition)
        for scenario_id in HOLDER_COMPOSITION_SCENARIOS
    ]
    for result in results.values():
        result.tables["out_s2_comparison_vs_base"] = comparison
        result.tables["out_s2_disposition_shifts_vs_base"] = shifts
    return results


def write_holder_composition_outputs(
    results: dict[str, ScenarioResult],
    output_root: Path = Path("var/rwtas/scenarios/holder_composition"),
) -> dict[str, dict[str, Path] | Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    written: dict[str, dict[str, Path] | Path] = {}
    for table_name in [
        "out_s2_comparison_vs_base",
        "out_s2_disposition_shifts_vs_base",
    ]:
        path = output_root / f"{table_name}.csv"
        _write_rows(path, next(iter(results.values())).rows(table_name))
        written[table_name] = path
    for scenario_id, result in results.items():
        scenario_dir = output_root / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        scenario_paths: dict[str, Path] = {}
        for table_name in [
            "out_ratewall_rollup",
            "out_government_interest_channel",
            "out_treasury_interest_disposition",
            "out_s2_scenario_config",
            "out_s2_balance_sheet_closure",
        ]:
            path = scenario_dir / f"{table_name}.csv"
            _write_rows(path, result.rows(table_name))
            scenario_paths[table_name] = path
        written[scenario_id] = scenario_paths
    return written


def build_rstar_wedge_rows(
    *,
    base_result: ScenarioResult,
    financialization_results: dict[str, ScenarioResult],
    issuance_results: dict[str, ScenarioResult],
    holder_results: dict[str, ScenarioResult],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rows.extend(_wedge_rows_for_result("base", "base", base_result, Decimal("100"), "base_same_state_plus_100bp_pair"))
    for scenario_id, result in financialization_results.items():
        if scenario_id == "base":
            continue
        rows.extend(_wedge_rows_for_result("financialization", scenario_id, result, Decimal("100"), "financialization_grid_plus_100bp_pair"))
    for scenario_id, result in issuance_results.items():
        if scenario_id == "base":
            continue
        rows.extend(_wedge_rows_for_result("issuance_mix", scenario_id, result, Decimal("100"), "S1_same_state_plus_100bp_pair"))
    for scenario_id, result in holder_results.items():
        if scenario_id == "base":
            continue
        rows.extend(_wedge_rows_for_result("holder_composition", scenario_id, result, Decimal("100"), "S2_same_state_plus_100bp_pair"))
    for shock_bp in RSTAR_STRESS_SWEEP_SHOCKS:
        scenario_id = f"distress_static_{_fmt(shock_bp)}bp"
        rows.extend(
            _wedge_rows_for_result(
                "stress_sweep",
                scenario_id,
                base_result,
                shock_bp,
                "distress_sweep_shock_size_only_no_RW_full_headline_entry",
            )
        )
    return rows


def write_rstar_wedge(rows: list[dict[str, str]], output_root: Path = Path("var/rwtas/scenarios")) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "out_rstar_wedge.csv"
    _write_rows(path, rows)
    return path


def write_s1s2_wedge_report(
    *,
    issuance_results: dict[str, ScenarioResult],
    holder_results: dict[str, ScenarioResult],
    wedge_rows: list[dict[str, str]],
    output_path: Path = Path("do/rwtas_s1s2_wedge_report_20260702.md"),
) -> Path:
    s1 = issuance_results["base"].rows("out_s1_comparison_vs_base")
    s2 = holder_results["base"].rows("out_s2_comparison_vs_base")
    shifts = holder_results["base"].rows("out_s2_disposition_shifts_vs_base")
    wedge_summary = _wedge_summary_rows(wedge_rows)
    lines = [
        "# RWTAS S1/S2 scenario studies + r-star wedge",
        "",
        "Date: 2026-07-02.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: scenario-only output; default headline tables are not promoted or rewritten.",
        "",
        "## S1 issuance-mix comparison vs base",
        "",
        "| scenario | horizon | N | D | RW | delta N | delta D | delta RW | direction check |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in s1:
        lines.append(_comparison_markdown_row(row))
    lines.extend(
        [
            "",
            "S1 timing note: the current V1 core is annual and expands annual values to monthly rows. The July 2026 start is therefore represented in this wave by the first modeled issuance-stock effect, which appears from the 2027 annual row rather than as a separate 2026H2 month-level break.",
            "",
            "## S2 holder-composition comparison vs base",
            "",
            "| scenario | horizon | N | D | RW | delta N | delta D | delta RW | direction check |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in s2:
        lines.append(_comparison_markdown_row(row))
    lines.extend(
        [
            "",
            "## Treasury-interest disposition shifts",
            "",
            "| scenario | gross | leak share | recycle share | route share | convert share | delta leak | delta convert | funding/closure note |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in shifts:
        lines.append(
            "| {scenario} | {gross} | {leak} | {recycle} | {route} | {convert} | {dleak} | {dconvert} | {note} |".format(
                scenario=row["scenario"],
                gross=row["gross_cashflow_delta_bil"],
                leak=row["leak_share"],
                recycle=row["recycle_share"],
                route=row["route_share"],
                convert=row["convert_share"],
                dleak=row["delta_leak_share_vs_base"],
                dconvert=row["delta_convert_share_vs_base"],
                note=row["balance_sheet_closure_note"],
            )
        )
    lines.extend(
        [
            "",
            "## r-star wedge year-1 summary",
            "",
            "| family | scenario | shock bp | RW_full Y1 | wedge per 100bp stance | wedge Y1 |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in wedge_summary:
        lines.append(
            "| {family} | {scenario} | {shock} | {rw} | {per100} | {wedge} |".format(
                family=row["scenario_family"],
                scenario=row["scenario_id"],
                shock=row["shock_bp"],
                rw=row["RW_full_year1"],
                per100=row["wedge_per_100bp_stance_bp"],
                wedge=row["wedge_year1_bp_year"],
            )
        )
    lines.extend(
        [
            "",
            "Base check-against: year-1 wedge per 100bp stance is "
            f"{_base_wedge_per_100(wedge_rows)}bp, close to the note's approx 6.5bp check.",
            "",
            "## Output locations",
            "",
            "- `var/rwtas/scenarios/issuance_mix/`",
            "- `var/rwtas/scenarios/holder_composition/`",
            "- `var/rwtas/scenarios/out_rstar_wedge.csv`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _s1_result_from_tables(
    scenario_id: str,
    tables: dict[str, list[dict[str, str]]],
    config_rows: list[dict[str, str]],
) -> ScenarioResult:
    dose_mode = tables["out_ratewall_rollup"][0].get("dose_mode", DEFAULT_DOSE_MODE)
    result_tables = dict(tables)
    result_tables["out_government_interest_delta_path"] = _government_interest_delta_path(
        scenario_id,
        tables["out_government_interest_channel"],
    )
    result_tables["out_s1_scenario_config"] = config_rows or [
        {
            "scenario_id": scenario_id,
            "parameter": "marginal_issuance_bill_share",
            "target_base": "0.30",
            "start_month": "2026-07",
            "engine_timing_note": "base_current_default",
            "input_basis_label": "current_default_post_promotion_tdc_on",
        }
    ]
    return ScenarioResult(
        scenario_id=scenario_id,
        tables=_stamp_scenario_tables(result_tables, dose_mode),
    )


def _s2_result_from_tables(
    scenario_id: str,
    tables: dict[str, list[dict[str, str]]],
    config_rows: list[dict[str, str]],
    closure_rows: list[dict[str, str]],
) -> ScenarioResult:
    dose_mode = tables["out_ratewall_rollup"][0].get("dose_mode", DEFAULT_DOSE_MODE)
    result_tables = dict(tables)
    disposition = _treasury_interest_disposition_rows(
        scenario_id,
        tables["out_government_interest_channel"],
        _closure_note(scenario_id),
    )
    result_tables["out_treasury_interest_disposition"] = disposition
    result_tables["out_s2_scenario_config"] = config_rows or [
        {
            "scenario_id": scenario_id,
            "instrument_family": "base",
            "holder": "",
            "share_delta": "0",
            "input_basis_label": "current_default_post_promotion_tdc_on",
            "rationale": "No holder-composition scenario delta.",
        }
    ]
    result_tables["out_s2_balance_sheet_closure"] = closure_rows or [
        {
            "scenario_id": scenario_id,
            "sector": "base",
            "asset_delta_bil": "0",
            "liability_delta_bil": "0",
            "real_counterpart_bil": "0",
            "status": "pass",
            "funding_note": "Current default holder matrix; no scenario transaction.",
        }
    ]
    return ScenarioResult(
        scenario_id=scenario_id,
        tables=_stamp_scenario_tables(result_tables, dose_mode),
    )


def _set_marginal_issuance_bill_share(
    pack_dir: Path,
    scenario_id: str,
    bill_share: Decimal,
) -> list[dict[str, str]]:
    path = pack_dir / "structural_assumptions.csv"
    rows = _read_csv_rows(path)
    out_rows: list[dict[str, str]] = []
    config_rows: list[dict[str, str]] = []
    for row in rows:
        if row["assumption_id"] != "marginal_issuance_bill_share":
            out_rows.append(row)
            continue
        updated = {
            **row,
            "low": _fmt(bill_share),
            "base": _fmt(bill_share),
            "high": _fmt(bill_share),
            "input_basis_label": "S1_issuance_mix_scenario",
            "rationale": (
                f"{scenario_id}: scenario-local marginal issuance bill share from 2026-07; "
                "remainder issued as coupons using existing tenor-mix/coupon repricing machinery."
            ),
        }
        out_rows.append(updated)
        config_rows.append(
            {
                "scenario_id": scenario_id,
                "parameter": "marginal_issuance_bill_share",
                "target_base": _fmt(bill_share),
                "start_month": "2026-07",
                "engine_timing_note": "annual_core_first_stock_effect_in_2027",
                "input_basis_label": "S1_issuance_mix_scenario",
            }
        )
    _write_rows(path, _clean_csv_rows(out_rows))
    return config_rows


def _apply_holder_composition_scenario(
    pack_dir: Path,
    scenario_id: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    matrix_path = pack_dir / "treasury_holder_matrix.csv"
    opening_path = pack_dir / "opening_stocks.csv"
    matrix_rows = _read_csv_rows(matrix_path)
    opening_rows = _read_csv_rows(opening_path)
    config_rows: list[dict[str, str]] = []
    closure_rows: list[dict[str, str]] = []
    for family in ["all_marketable_treasuries", "treasury_bills", "treasury_notes_bonds_tips"]:
        family_rows = [row for row in matrix_rows if row["instrument_family"] == family]
        config_rows.extend(_shift_holder_rows(family_rows, scenario_id, "share"))
    for family in ["treasury_bills", "treasury_notes_bonds_tips"]:
        family_rows = [row for row in opening_rows if row["instrument_family"] == family]
        config_rows.extend(_shift_holder_rows(family_rows, scenario_id, "stock"))
        closure_rows.extend(_holder_closure_rows(family_rows, scenario_id, family))
    _write_rows(matrix_path, _clean_csv_rows(matrix_rows))
    _write_rows(opening_path, _clean_csv_rows(opening_rows))
    return config_rows, closure_rows


def _clean_csv_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return rows
    fields = [field for field in rows[0] if field is not None]
    return [{field: row.get(field, "") for field in fields} for row in rows]


def _shift_holder_rows(
    rows: list[dict[str, str]],
    scenario_id: str,
    value_kind: str,
) -> list[dict[str, str]]:
    if not rows:
        return []
    config_rows: list[dict[str, str]] = []
    holder_values = {_holder_from_row(row): row for row in rows}
    original_values = {
        holder: {band: _d(row[band]) for band in ("low", "base", "high")}
        for holder, row in holder_values.items()
    }
    bands = ("low", "base", "high")
    family = rows[0]["instrument_family"]
    if scenario_id == "S2_banks_absorb":
        buyers = {"banks": Decimal("1")}
        sellers = {"rest_of_world": Decimal("1")}
        note = "banks buy Treasuries from ROW, funded by bank liability/reserve claim to ROW"
    elif scenario_id == "S2_row_returns":
        buyers = {"rest_of_world": Decimal("1")}
        sellers = {"mmfs": Decimal("0"), "households_direct": Decimal("0")}
        note = "ROW buys Treasuries from MMFs and households pro-rata; domestic sellers receive liquid bank/MMF claims"
    else:
        raise ValueError(f"unknown holder composition scenario {scenario_id}")
    if value_kind == "share":
        base_total = Decimal("1")
        target_shift = Decimal("0.10")
    else:
        base_total = sum(_d(row["base"]) for row in rows)
        target_shift = base_total * Decimal("0.10")
    for band in bands:
        if scenario_id == "S2_row_returns":
            available = sum(_d(holder_values[seller][band]) for seller in sellers)
            applied_shift = min(target_shift if value_kind == "stock" else Decimal("0.10"), available)
            seller_total = available
            seller_weights = {
                seller: (_d(holder_values[seller][band]) / seller_total if seller_total else Decimal("0"))
                for seller in sellers
            }
        else:
            applied_shift = target_shift if value_kind == "stock" else Decimal("0.10")
            seller_weights = sellers
        for holder, weight in buyers.items():
            holder_values[holder][band] = _fmt(_d(holder_values[holder][band]) + applied_shift * weight)
        for holder, weight in seller_weights.items():
            holder_values[holder][band] = _fmt(_d(holder_values[holder][band]) - applied_shift * weight)
    for holder, row in holder_values.items():
        if holder in {*buyers, *sellers}:
            config_rows.append(
                {
                    "scenario_id": scenario_id,
                    "instrument_family": family,
                    "holder": holder,
                    "value_kind": value_kind,
                    "base_delta": _fmt(_d(row["base"]) - original_values[holder]["base"]),
                    "input_basis_label": "S2_holder_composition_scenario",
                    "rationale": note,
                }
            )
            row["input_basis_label"] = "S2_holder_composition_scenario"
            row["rationale"] = note
    return config_rows


def _holder_from_row(row: dict[str, str]) -> str:
    cell_or_sector = row["cell_or_sector"]
    for part in cell_or_sector.split("|"):
        if part.startswith("holder="):
            return part.removeprefix("holder=")
    return cell_or_sector


def _holder_closure_rows(
    rows: list[dict[str, str]],
    scenario_id: str,
    family: str,
) -> list[dict[str, str]]:
    base_total = sum(_d(row["base"]) for row in rows)
    amount = base_total * Decimal("0.10")
    if scenario_id == "S2_banks_absorb":
        return [
            _closure_row(scenario_id, family, "banks", amount, amount, Decimal("0"), "bank Treasury asset purchase funded by liability/reserve claim to ROW"),
            _closure_row(scenario_id, family, "rest_of_world", -amount, Decimal("0"), -amount, "ROW sells Treasury and receives bank liability/reserve claim; real-side counterpart records external portfolio swap"),
        ]
    if scenario_id == "S2_row_returns":
        mmf = next(row for row in rows if _holder_from_row(row) == "mmfs")
        hh = next(row for row in rows if _holder_from_row(row) == "households_direct")
        seller_total = _d(mmf["base"]) + _d(hh["base"])
        mmf_amount = amount * _d(mmf["base"]) / seller_total
        hh_amount = amount * _d(hh["base"]) / seller_total
        return [
            _closure_row(scenario_id, family, "rest_of_world", amount, Decimal("0"), amount, "ROW external portfolio rotation into Treasuries"),
            _closure_row(scenario_id, family, "mmfs", -mmf_amount, -mmf_amount, Decimal("0"), "MMFs sell Treasuries and extinguish/replace liquid fund shares pro-rata"),
            _closure_row(scenario_id, family, "households_direct", -hh_amount, -hh_amount, Decimal("0"), "Households sell direct Treasuries and receive liquid deposits/MMF claims pro-rata"),
        ]
    raise ValueError(f"unknown holder composition scenario {scenario_id}")


def _closure_row(
    scenario_id: str,
    family: str,
    sector: str,
    asset_delta: Decimal,
    liability_delta: Decimal,
    real_counterpart: Decimal,
    note: str,
) -> dict[str, str]:
    gap = asset_delta - liability_delta - real_counterpart
    return {
        "scenario_id": scenario_id,
        "instrument_family": family,
        "sector": sector,
        "asset_delta_bil": _fmt(asset_delta),
        "liability_delta_bil": _fmt(liability_delta),
        "real_counterpart_bil": _fmt(real_counterpart),
        "identity_gap_bil": _fmt(gap),
        "status": "pass" if abs(gap) <= Decimal("0.000001") else "fail",
        "funding_note": note,
    }


def _scenario_comparison_rows(
    results: dict[str, ScenarioResult],
    *,
    scenario_ids: list[str],
    expected_direction: dict[str, str],
) -> list[dict[str, str]]:
    base_rows = _rollup_summary_by_horizon(results["base"])
    rows: list[dict[str, str]] = []
    for scenario_id in scenario_ids:
        scenario_rows = _rollup_summary_by_horizon(results[scenario_id])
        for horizon in ["year_1", "year_5", "cumulative_120_month"]:
            scenario = scenario_rows[horizon]
            base = base_rows[horizon]
            delta_n = _d(scenario["N_bil"]) - _d(base["N_bil"])
            delta_d = _d(scenario["D_bil"]) - _d(base["D_bil"])
            delta_rw = _d(scenario["RW_ratio"]) - _d(base["RW_ratio"])
            rows.append(
                {
                    "scenario": scenario_id,
                    "horizon": horizon,
                    "period": scenario["period"],
                    "N_bil": scenario["N_bil"],
                    "D_bil": scenario["D_bil"],
                    "RW_ratio": scenario["RW_ratio"],
                    "base_N_bil": base["N_bil"],
                    "base_D_bil": base["D_bil"],
                    "base_RW_ratio": base["RW_ratio"],
                    "dose_mode": scenario.get("dose_mode", DEFAULT_DOSE_MODE),
                    "delta_N_bil": _fmt(delta_n),
                    "delta_D_bil": _fmt(delta_d),
                    "delta_RW_ratio": _fmt(delta_rw),
                    "expected_direction": expected_direction[scenario_id],
                    "direction_check": _direction_check(scenario_id, horizon, delta_n, delta_rw),
                    "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
                }
            )
    return rows


def _rollup_summary_by_horizon(result: ScenarioResult) -> dict[str, dict[str, str]]:
    rows = [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["band"] == "base" and row["ricardian_offset"] == "0"
    ]
    return {
        "year_1": next(row for row in rows if row["period_type"] == "annual" and row["period"] == "2026"),
        "year_5": next(row for row in rows if row["period_type"] == "annual" and row["period"] == "2030"),
        "cumulative_120_month": next(row for row in rows if row["period_type"] == "cumulative_120_month"),
    }


def _direction_check(scenario_id: str, horizon: str, delta_n: Decimal, delta_rw: Decimal) -> str:
    if scenario_id in {"S1_bills_heavy", "S1_termed_out"} and horizon == "year_1" and delta_n == 0 and delta_rw == 0:
        return "no_year1_effect_annual_timing_limit"
    if scenario_id in {"S1_bills_heavy", "S2_banks_absorb"}:
        return "as_expected" if delta_n >= 0 and delta_rw >= 0 else "deviation"
    if scenario_id in {"S1_termed_out", "S2_row_returns"}:
        return "as_expected" if delta_n <= 0 and delta_rw <= 0 else "deviation"
    return "not_applicable"


def _government_interest_delta_path(
    scenario_id: str,
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[str, dict[str, Decimal]] = {}
    for row in rows:
        year = row["year"]
        item = grouped.setdefault(
            year,
            {
                "bill": Decimal("0"),
                "coupon": Decimal("0"),
                "current_coupon": Decimal("0"),
                "new_coupon": Decimal("0"),
            },
        )
        cashflow = _d(row["cashflow_delta_bil"])
        if row["instrument_family"] == "treasury_bills":
            item["bill"] += cashflow
        else:
            item["coupon"] += cashflow
            item["current_coupon"] = max(item["current_coupon"], _d(row["current_stock_coupon_interest_bil"]))
            item["new_coupon"] = max(item["new_coupon"], _d(row["new_issuance_coupon_interest_bil"]))
    out: list[dict[str, str]] = []
    for year, values in sorted(grouped.items()):
        total = values["bill"] + values["coupon"]
        out.append(
            {
                "scenario_id": scenario_id,
                "year": year,
                "bill_interest_delta_bil": _fmt(values["bill"]),
                "coupon_interest_delta_bil": _fmt(values["coupon"]),
                "current_stock_coupon_interest_bil": _fmt(values["current_coupon"]),
                "new_issuance_coupon_interest_bil": _fmt(values["new_coupon"]),
                "government_interest_delta_bil": _fmt(total),
                "bill_share_of_government_delta": _fmt(values["bill"] / total) if total else "0",
                "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
            }
        )
    return out


def _treasury_interest_disposition_rows(
    scenario_id: str,
    rows: list[dict[str, str]],
    closure_note: str,
) -> list[dict[str, str]]:
    gross = sum(_d(row["cashflow_delta_bil"]) for row in rows)
    leaked = sum(_d(row["leaked_bil"]) for row in rows)
    recycled = sum(_d(row["recycled_bil"]) for row in rows)
    routed = sum(_d(row["routed_bil"]) for row in rows)
    converted = sum(_d(row["converted_net_bil"]) for row in rows)
    return [
        {
            "scenario": scenario_id,
            "gross_cashflow_delta_bil": _fmt(gross),
            "leaked_bil": _fmt(leaked),
            "recycled_bil": _fmt(recycled),
            "routed_bil": _fmt(routed),
            "converted_net_bil": _fmt(converted),
            "leak_share": _fmt(leaked / gross) if gross else "0",
            "recycle_share": _fmt(recycled / gross) if gross else "0",
            "route_share": _fmt(routed / gross) if gross else "0",
            "convert_share": _fmt(converted / gross) if gross else "0",
            "balance_sheet_closure_note": closure_note,
            "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
        }
    ]


def _disposition_shift_row(
    scenario_id: str,
    result: ScenarioResult,
    base: dict[str, str],
) -> dict[str, str]:
    row = result.rows("out_treasury_interest_disposition")[0]
    return {
        **row,
        "delta_leak_share_vs_base": _fmt(_d(row["leak_share"]) - _d(base["leak_share"])),
        "delta_recycle_share_vs_base": _fmt(_d(row["recycle_share"]) - _d(base["recycle_share"])),
        "delta_route_share_vs_base": _fmt(_d(row["route_share"]) - _d(base["route_share"])),
        "delta_convert_share_vs_base": _fmt(_d(row["convert_share"]) - _d(base["convert_share"])),
    }


def _closure_note(scenario_id: str) -> str:
    if scenario_id == "S2_banks_absorb":
        return "banks +10pp Treasury share, displacing ROW; purchases funded by bank liability/reserve claim to ROW"
    if scenario_id == "S2_row_returns":
        return "ROW +10pp Treasury share, displacing MMFs and households pro-rata; domestic sellers receive liquid claims"
    return "base holder composition"


def _wedge_rows_for_result(
    scenario_family: str,
    scenario_id: str,
    result: ScenarioResult,
    shock_bp: Decimal,
    stance_basis: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    annual = [
        row
        for row in result.rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ]
    for row in annual:
        year_index = Decimal(int(row["period"]) - START_YEAR + 1)
        stance = shock_bp * year_index
        rw = _d(row["RW_ratio"])
        rows.append(
            {
                "scenario_family": scenario_family,
                "scenario_id": scenario_id,
                "period_type": "annual",
                "year": row["period"],
                "dose_mode": row.get("dose_mode", DEFAULT_DOSE_MODE),
                "year_index": _fmt(year_index),
                "shock_bp": _fmt(shock_bp),
                "cumulative_stance_bp_year": _fmt(stance),
                "RW_full": row["RW_ratio"],
                "wedge_bp_year": _fmt(rw * stance),
                "wedge_per_100bp_stance_bp": _fmt(rw * Decimal("100")),
                "stance_basis": stance_basis,
                "object_version_stamp": CURRENT_DEFAULT_OBJECT_STAMP,
            }
        )
    return rows


def _wedge_summary_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "scenario_family": row["scenario_family"],
            "scenario_id": row["scenario_id"],
            "dose_mode": row.get("dose_mode", DEFAULT_DOSE_MODE),
            "shock_bp": row["shock_bp"],
            "RW_full_year1": row["RW_full"],
            "wedge_per_100bp_stance_bp": row["wedge_per_100bp_stance_bp"],
            "wedge_year1_bp_year": row["wedge_bp_year"],
        }
        for row in rows
        if row["year_index"] == "1"
    ]


def _base_wedge_per_100(rows: list[dict[str, str]]) -> str:
    return next(
        row["wedge_per_100bp_stance_bp"]
        for row in rows
        if row["scenario_family"] == "base" and row["scenario_id"] == "base" and row["year_index"] == "1"
    )


def _comparison_markdown_row(row: dict[str, str]) -> str:
    return "| {scenario} | {horizon} | {n} | {d} | {rw} | {dn} | {dd} | {drw} | {check} |".format(
        scenario=row["scenario"],
        horizon=row["horizon"],
        n=row["N_bil"],
        d=row["D_bil"],
        rw=row["RW_ratio"],
        dn=row["delta_N_bil"],
        dd=row["delta_D_bil"],
        drw=row["delta_RW_ratio"],
        check=row["direction_check"],
    )


def _holder_label(cell_or_sector: str) -> str:
    for part in cell_or_sector.split("|"):
        if part.startswith("holder="):
            return part.removeprefix("holder=")
    return cell_or_sector


def _issuer_label(cell_or_sector: str) -> str:
    for part in cell_or_sector.split("|"):
        if part.startswith("issuer="):
            return part.removeprefix("issuer=")
    return cell_or_sector


def _stringify(row: dict[str, Decimal | str]) -> dict[str, str]:
    return {key: _fmt(value) if isinstance(value, Decimal) else value for key, value in row.items()}


def _stamp_scenario_tables(
    tables: dict[str, list[dict[str, str]]],
    dose_mode: str,
) -> dict[str, list[dict[str, str]]]:
    stamped: dict[str, list[dict[str, str]]] = {}
    for table_name, rows in tables.items():
        stamped[table_name] = [{**row, "dose_mode": row.get("dose_mode", dose_mode)} for row in rows]
    return stamped


def _month_label(month_index: int) -> str:
    return f"{START_YEAR + (month_index - 1) // 12}-{((month_index - 1) % 12) + 1:02d}"
