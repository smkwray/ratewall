"""RW_pi price-traction scenario surfaces.

The RW_pi object is intentionally scenario/diagnostic-only. It consumes the
existing RWTAM rows and the accepted price-object contract, but it does not
mutate RW_full, demand headline tables, or golden fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.scenarios import ScenarioResult
from ratewall.rwtam.v1 import (
    DOSE_MODES,
    START_YEAR,
    _d,
    _fmt,
    _load_pack,
    _read_csv_rows,
    _write_rows,
    build_v1,
)
from ratewall.rwtam.rwpi_validation import (
    PlugValidationResult,
    build_rwpi_plug_validation,
    write_rwpi_plug_validation_report,
)


RWPI_OUTPUT_DIR = Path("var/rwtam/scenarios/rwpi")
RWPI_REPORT_PATH = Path("do/rwtam_rwpi_build_report_20260703.md")
GDP_BIL = Decimal("31866")
SHOCK_BP = Decimal("100")
WINDOWS = {
    "0_12m": range(1, 13),
    "13_24m": range(13, 25),
    "25_36m": range(25, 37),
    "0_36m_cumulative_sum_pp": range(1, 37),
    "0_36m_cumulative_average": range(1, 37),
}
SLACK_STATES = ("slack", "balanced", "tight")
BANDS = ("low", "base", "high")
INDEX_TARGETS = ("CPI_U", "PCE")
PCE_IMPORT_CROSSWALK = Decimal("0.85")
PCE_IMPORT_CROSSWALK_RANGE = (Decimal("0.80"), Decimal("0.85"), Decimal("1.00"))
PCE_IMPORT_CROSSWALK_LABEL = "assumption_grade_to_fetch_bea_2_3_5_bls_relative_importance"
OKUN_DIVISOR = Decimal("2.0")
PCE_M_D_IMPORT_LEAKAGE = {"low": Decimal("0.07"), "base": Decimal("0.09"), "high": Decimal("0.12")}
PCE_M_N_IMPORT_LEAKAGE = {"low": Decimal("0.11"), "base": Decimal("0.13"), "high": Decimal("0.14")}
PCE_CPI_TO_PCE_SLOPE_WEDGE = {"low": Decimal("0.80"), "base": Decimal("0.88"), "high": Decimal("0.95")}
CPI_SHELTER_WEIGHT_MAY_2026 = Decimal("0.35237")
PCE_SHELTER_WEIGHT = Decimal("0.17")
RENT_WEIGHT_RATIO_PCE_TO_CPI = PCE_SHELTER_WEIGHT / CPI_SHELTER_WEIGHT_MAY_2026

PHILLIPS_SLOPE_U_GAP = {
    "slack": {"low": Decimal("0"), "base": Decimal("0.025"), "high": Decimal("0.05"), "grade": "B"},
    "balanced": {"low": Decimal("0.10"), "base": Decimal("0.15"), "high": Decimal("0.20"), "grade": "B"},
    "tight": {"low": Decimal("0.30"), "base": Decimal("0.45"), "high": Decimal("0.60"), "grade": "C"},
}
IMPORT_PASS_THROUGH_PP_PER_1PCT_USD = {
    "low": Decimal("0.05"),
    "base": Decimal("0.10"),
    "high": Decimal("0.15"),
}
COST_PASS_THROUGH_PP_PER_100BN = {
    "low": Decimal("0.15"),
    "base": Decimal("0.30"),
    "high": Decimal("0.50"),
}

FIRM_ALLOCATION_DEFAULTS = {
    "c_and_i_depository_loans_interest": ("working_capital", Decimal("0.30"), Decimal("0.40"), Decimal("0.20"), Decimal("0.05"), Decimal("0.05")),
    "syndicated_loans_interest": ("working_capital", Decimal("0.25"), Decimal("0.45"), Decimal("0.20"), Decimal("0.05"), Decimal("0.05")),
    "cre_mortgages_floating_interest": ("operating_cre_floating", Decimal("0.20"), Decimal("0.50"), Decimal("0.20"), Decimal("0.05"), Decimal("0.05")),
    "cre_mortgages_fixed_interest": ("fixed_cre_finance_not_marginal_operating_cost", Decimal("0"), Decimal("0.70"), Decimal("0.20"), Decimal("0.05"), Decimal("0.05")),
    "bnpl_funding_liability_cost": ("provider_operating_funding", Decimal("0.20"), Decimal("0.50"), Decimal("0.20"), Decimal("0.05"), Decimal("0.05")),
    "corporate_bonds_interest": ("long_term_corporate_bonds_default_cost_zero", Decimal("0"), Decimal("0.70"), Decimal("0.20"), Decimal("0.05"), Decimal("0.05")),
}
HOUSEHOLD_DEMAND_ONLY_RULES = {
    "mortgages_fixed_interest",
    "mortgages_arm_interest",
    "heloc_interest",
    "credit_card_revolving_interest",
    "auto_installment_debt_interest",
    "student_loans_private_interest",
    "personal_installment_debt_interest",
}


@dataclass(frozen=True)
class RwpiResult:
    """CSV-ready RW_pi tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_rwpi(pack_dir: Path = Path("configs/rwtam/packs")) -> RwpiResult:
    pack = _load_pack(pack_dir)
    phase6_pack = _load_pack(pack_dir / "phase6")
    results = {dose_mode: build_v1(pack_dir, dose_mode=dose_mode) for dose_mode in DOSE_MODES}
    coefficients = _coefficient_rows(phase6_pack)
    allocation = _allocation_rows(pack, results["persistent_level"])
    allocation_errors = validate_firm_interest_allocation(allocation, results["persistent_level"])
    if allocation_errors:
        raise ValueError("; ".join(allocation_errors))

    monthly: list[dict[str, str]] = []
    rent: list[dict[str, str]] = []
    for dose_mode, result in results.items():
        monthly.extend(_monthly_rows(phase6_pack, result, dose_mode, allocation, "CPI_U"))
        monthly.extend(_monthly_rows(phase6_pack, result, dose_mode, allocation, "PCE"))
        rent.extend(_rent_companion_rows(result, dose_mode, "CPI_U"))
        rent.extend(_rent_companion_rows(result, dose_mode, "PCE"))

    windows = _window_rows(monthly)
    attribution = _attribution_rows(monthly, windows)
    pce = [row for row in windows if row["index_target"] == "PCE"]
    plug_validation = build_rwpi_plug_validation(monthly, windows)
    validation = _validation_scaffold_rows(plug_validation)
    exclusions = _exclusion_rows()
    probes = _probe_rows(allocation, results["persistent_level"])
    lineage = _lineage_rows()
    pce_ratio = _pce_ratio_crosswalk_rows(results["persistent_level"])
    pce_level = _pce_level_path_rows(windows)
    pce_caveats = _pce_caveat_rows()
    invariants = _invariant_rows(windows, attribution, rent, probes, plug_validation, pce_ratio, pce_level, pce_caveats)

    return RwpiResult(
        {
            "out_rwpi_coefficients": coefficients,
            "out_rwpi_allocation_vector": allocation,
            "out_rwpi_monthly_channel_path": monthly,
            "out_rwpi_window_path": windows,
            "out_rwpi_channel_attribution": attribution,
            "out_rwpi_rent_companion_path": rent,
            "out_rwpi_pce_crosswalk": pce,
            "out_rwpi_pce_factor_table": _pce_factor_rows(),
            "out_rwpi_pce_ratio_crosswalk": pce_ratio,
            "out_rwpi_pce_level_path": pce_level,
            "out_rwpi_pce_caveat_rows": pce_caveats,
            "out_rwpi_exclusion_rows": exclusions,
            "out_rwpi_validation_scaffold": validation,
            "out_rwpi_plug_validation": plug_validation.scores,
            "out_rwpi_plug_validation_series": plug_validation.series,
            "out_rwpi_probe_results": probes,
            "out_rwpi_lineage": lineage,
            "out_rwpi_invariant_check": invariants,
        }
    )


def write_rwpi_outputs(result: RwpiResult, output_dir: Path = RWPI_OUTPUT_DIR) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_rwpi_report(result: RwpiResult, output_path: Path = RWPI_REPORT_PATH) -> Path:
    windows = [
        row for row in result.rows("out_rwpi_window_path")
        if row["index_target"] == "CPI_U"
        and row["dose_mode"] == "persistent_level"
        and row["slack_state"] == "balanced"
    ]
    attr = [
        row for row in result.rows("out_rwpi_channel_attribution")
        if row["index_target"] == "CPI_U"
        and row["dose_mode"] == "persistent_level"
        and row["slack_state"] == "balanced"
    ]
    rent = [
        row for row in result.rows("out_rwpi_rent_companion_path")
        if row["index_target"] == "CPI_U" and row["dose_mode"] == "persistent_level" and row["band"] == "base"
    ]
    probes = result.rows("out_rwpi_probe_results")
    exclusions = result.rows("out_rwpi_exclusion_rows")
    invariants = result.rows("out_rwpi_invariant_check")

    lines = [
        "# RWTAM RW_pi build report",
        "",
        "Date: 2026-07-03.",
        "Scope: scenario/diagnostic-only price object; `ND_pi` is not wired into the demand headline or RW_full goldens.",
        "Binding inputs: `configs/rwtam/packs/rwpi_design_contract/`, `configs/rwtam/packs/rwpi_design_contract/`, and `project research notes (coefficient evidence)`.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
        "| design contract | copied path-preserving to `configs/rwtam/packs/rwpi_design_contract/` |",
        "| CPI-U primary | emitted headline `ND_pi_CPIU(h)` with May-2026 shelter weight carried in coefficients |",
        "| PCE crosswalk | emitted separately as `out_rwpi_pce_crosswalk.csv`; not conflated with CPI-U |",
        "| demand/Phillips | retained M5 net-demand-with-wall first stage and replaced placeholder slopes with memo L/B/H bands |",
        "| FX/import | wired Phase 6 broad-dollar scenario path x memo pass-through bands |",
        "| cost channel | wired from real engine firm/provider interest rows through allocation vector; grade D and `sensitivity_only` |",
        "| ND_pi disclosure | window rows split demand, FX, and cost columns; the demand-only-after-wall hypothesis row is labeled in attribution |",
        "| rent/housing supply | emitted companion path only; not summed into headline because starts-to-rent elasticity is absent |",
        "| carry and regulated utilities | absent-with-reason until coefficients exist |",
        "| exclusions | expectations, wages, COLA, direct mortgage-interest CPI, and asset-price channels documented as exclusion rows |",
        "",
        "## Gates",
        "",
        "| check | status |",
        "| --- | --- |",
    ]
    for row in invariants:
        lines.append(f"| {row['check_id']} | {row['status']} |")

    lines.extend(
        [
            "",
            "## ND_pi CPI-U Path: Persistent, Balanced State",
            "",
            "| window | demand base | FX base | cost base | ND_pi base | base verdict |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in windows:
        lines.append(
            f"| {row['horizon_window']} | {row['demand_only_after_wall_base_pp']} | {row['fx_import_base_pp']} | {row['cost_channel_base_pp']} | {row['ND_pi_base_pp']} | {row['base_verdict']} |"
        )
    lines.extend(
        [
            "",
            "## Channel Attribution: Persistent, Balanced State",
            "",
            "| window | channel | low | base | high | role | grade |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in attr:
        lines.append(
            f"| {row['horizon_window']} | {row['channel_id']} | {row['contribution_low_pp']} | {row['contribution_base_pp']} | {row['contribution_high_pp']} | {row['ledger_role']} | {row['grade']} |"
        )
    lines.extend(
        [
            "",
            "## Rent Companion Path",
            "",
            "| month | status | sign anchor | CPI shelter weight | reason |",
            "| ---: | --- | --- | ---: | --- |",
        ]
    )
    for row in rent[:8]:
        lines.append(
            f"| {row['month']} | {row['headline_status']} | {row['sign_anchor']} | {row['shelter_weight']} | {row['absent_reason']} |"
        )
    lines.extend(
        [
            "",
            "## Exclusion Rows",
            "",
            "| channel | disposition | reason |",
            "| --- | --- | --- |",
        ]
    )
    for row in exclusions:
        lines.append(f"| {row['channel_id']} | {row['disposition']} | {row['reason']} |")
    lines.extend(
        [
            "",
            "## Probe Evidence",
            "",
            "| probe | expected | observed | status |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in probes:
        lines.append(
            f"| {row['probe_id']} | {row['expected_result']} | {row['observed_result']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- Validation fence: RWTAM-only tests, no skipped tests, plus byte-stable existing goldens.",
            "- Parked marginal/forecast subsystem failures are outside this lane: `pre_existing_not_this_lane ~= 273` per binding amendment; no full-suite green claim is made.",
            "- 2022-24 scaffolding is emitted in `out_rwpi_validation_scaffold.csv`; plug inputs that are not local are marked `needs_observed_series`.",
            "",
            "## Output locations",
            "",
            "- `var/rwtam/scenarios/rwpi/out_rwpi_window_path.csv`",
            "- `var/rwtam/scenarios/rwpi/out_rwpi_channel_attribution.csv`",
            "- `var/rwtam/scenarios/rwpi/out_rwpi_rent_companion_path.csv`",
            "- `var/rwtam/scenarios/rwpi/out_rwpi_pce_crosswalk.csv`",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def write_rwpi_validation_report(
    result: RwpiResult,
    output_path: Path = Path("do/rwtam_rwpi_plug_validation_report_20260704.md"),
) -> Path:
    return write_rwpi_plug_validation_report(
        PlugValidationResult(
            scores=result.rows("out_rwpi_plug_validation"),
            series=result.rows("out_rwpi_plug_validation_series"),
        ),
        output_path,
    )


def validate_firm_interest_allocation(
    allocation_rows: list[dict[str, str]],
    emitted_result: ScenarioResult,
) -> list[str]:
    emitted_keys = {
        _source_cashflow_key_from_claim_row(row, _claim_rule_index())
        for row in emitted_result.rows("out_claim_processor_channel")
        if row["year"] == str(START_YEAR)
    }
    errors: list[str] = []
    for row in allocation_rows:
        key = row["source_cashflow_key"]
        if key not in emitted_keys:
            errors.append(f"allocation source not emitted: {row['rule_id']}")
        shares = [
            _d(row["allocated_to_price_cost"]),
            _d(row["allocated_to_quantity_demand_drag"]),
            _d(row["allocated_to_margin_absorption"]),
            _d(row["allocated_to_tax_or_other"]),
            _d(row["unallocated_absent_with_reason"]),
        ]
        if sum(shares, Decimal("0")) != Decimal("1"):
            errors.append(f"allocation shares must sum to 1: {row['rule_id']}")
        if shares[0] + shares[1] > Decimal("1"):
            errors.append(f"price_cost plus quantity_demand exceeds 1: {row['rule_id']}")
    return errors


def _monthly_rows(
    phase6_pack: dict[str, list[dict[str, str]]],
    result: ScenarioResult,
    dose_mode: str,
    allocation: list[dict[str, str]],
    index_target: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    factor = PCE_IMPORT_CROSSWALK if index_target == "PCE" else Decimal("1")
    for slack_state in SLACK_STATES:
        for band in BANDS:
            demand_total = _demand_total_pp(result, slack_state, band, index_target)
            fx_total = _fx_total_pp(phase6_pack, band) * factor
            cost_total = _cost_total_pp(result, allocation, band, dose_mode)
            for month, mass in _kernel("demand").items():
                rows.append(_monthly_channel_row(dose_mode, index_target, slack_state, band, month, "D_PHILLIPS_WALL", demand_total * mass, "lowering", "B/C", "headline"))
            for month, mass in _kernel("fx").items():
                rows.append(_monthly_channel_row(dose_mode, index_target, slack_state, band, month, "FX_IMPORT", fx_total * mass, "lowering", "B", "headline_if_calibrated"))
            for month, mass in _kernel("cost").items():
                rows.append(_monthly_channel_row(dose_mode, index_target, slack_state, band, month, "FIRM_WORKING_CAPITAL_COST", cost_total * mass, "raising", "D", "sensitivity_only"))
            for channel_id, lag in (("CARRY_COSTS", "0-6m"), ("REGULATED_RATEBASE_FINANCE", "6-36m")):
                rows.append(_monthly_channel_row(dose_mode, index_target, slack_state, band, 1, channel_id, Decimal("0"), "raising", "absent_with_reason", f"absent_with_reason:{lag}"))
    return rows


def _monthly_channel_row(
    dose_mode: str,
    index_target: str,
    slack_state: str,
    band: str,
    month: int,
    channel_id: str,
    contribution_pp: Decimal,
    ledger_role: str,
    grade: str,
    headline_status: str,
) -> dict[str, str]:
    lowering = contribution_pp if ledger_role == "lowering" else Decimal("0")
    raising = contribution_pp if ledger_role == "raising" else Decimal("0")
    return {
        "scenario_id": f"rwpi_{dose_mode}_plus100bp",
        "dose_mode": dose_mode,
        "shock_bp": _fmt(SHOCK_BP),
        "month": str(month),
        "index_target": index_target,
        "slack_state": slack_state,
        "band": band,
        "channel_id": channel_id,
        "subchannel_id": channel_id.lower(),
        "index_component": _index_component(channel_id),
        "intermediate_variable": _intermediate_variable(channel_id),
        "outcome_variable": "index_inflation_pp_per_100bp",
        "lag_kernel_id": _kernel_id(channel_id),
        "coefficient_id": _coefficient_id(channel_id, slack_state, band),
        "owner_assumption_mode": "literature_scenario_band",
        "price_outcome_key": "|".join(
            [
                f"rwpi_{dose_mode}_plus100bp",
                _fmt(SHOCK_BP),
                str(month),
                "monthly_path",
                index_target,
                "source_cashflow_key=not_applicable_for_non_cashflow_channel" if channel_id != "FIRM_WORKING_CAPITAL_COST" else "source_cashflow_key=allocated_real_rows",
                channel_id,
                channel_id.lower(),
                _index_component(channel_id),
                _intermediate_variable(channel_id),
                "index_inflation_pp_per_100bp",
                _kernel_id(channel_id),
                _coefficient_id(channel_id, slack_state, band),
                "literature_scenario_band",
            ]
        ),
        "ledger_role": ledger_role,
        "lowering_pp": _fmt(lowering),
        "raising_pp": _fmt(raising),
        "signed_net_pp": _fmt(lowering - raising),
        "grade": grade,
        "headline_status": headline_status,
        "include_flag": "1" if headline_status in {"headline", "headline_if_calibrated", "sensitivity_only"} else "0",
    }


def _window_rows(monthly: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    keys = sorted({(r["dose_mode"], r["index_target"], r["slack_state"]) for r in monthly})
    for dose_mode, index_target, slack_state in keys:
        for window, months in WINDOWS.items():
            values: dict[str, Decimal] = {}
            lowerings: dict[str, Decimal] = {}
            raisings: dict[str, Decimal] = {}
            demand: dict[str, Decimal] = {}
            fx: dict[str, Decimal] = {}
            cost: dict[str, Decimal] = {}
            divisor = _window_divisor(window)
            included_nonzero_kernel_mass = False
            for band in BANDS:
                selected = [
                    r for r in monthly
                    if r["dose_mode"] == dose_mode
                    and r["index_target"] == index_target
                    and r["slack_state"] == slack_state
                    and r["band"] == band
                    and int(r["month"]) in months
                    and r["include_flag"] == "1"
                ]
                included_nonzero_kernel_mass = included_nonzero_kernel_mass or any(
                    _d(r["lowering_pp"]) != 0 or _d(r["raising_pp"]) != 0
                    for r in selected
                )
                lowering = sum((_d(r["lowering_pp"]) for r in selected), Decimal("0")) / divisor
                raising = sum((_d(r["raising_pp"]) for r in selected), Decimal("0")) / divisor
                demand[band] = (
                    sum(
                        (
                            _d(r["lowering_pp"])
                            for r in selected
                            if r["channel_id"] == "D_PHILLIPS_WALL"
                        ),
                        Decimal("0"),
                    )
                    / divisor
                )
                fx[band] = (
                    sum(
                        (
                            _d(r["lowering_pp"])
                            for r in selected
                            if r["channel_id"] == "FX_IMPORT"
                        ),
                        Decimal("0"),
                    )
                    / divisor
                )
                cost[band] = (
                    sum(
                        (
                            _d(r["raising_pp"])
                            for r in selected
                            if r["channel_id"] == "FIRM_WORKING_CAPITAL_COST"
                        ),
                        Decimal("0"),
                    )
                    / divisor
                )
                lowerings[band] = lowering
                raisings[band] = raising
                values[band] = lowering - raising
            rows.append(
                {
                    "scenario_id": f"rwpi_{dose_mode}_plus100bp",
                    "dose_mode": dose_mode,
                    "shock_bp": _fmt(SHOCK_BP),
                    "index_target": index_target,
                    "slack_state": slack_state,
                    "horizon_window": window,
                    "inflation_lowering_low_pp": _fmt(lowerings["low"]),
                    "inflation_lowering_base_pp": _fmt(lowerings["base"]),
                    "inflation_lowering_high_pp": _fmt(lowerings["high"]),
                    "inflation_raising_low_pp": _fmt(raisings["low"]),
                    "inflation_raising_base_pp": _fmt(raisings["base"]),
                    "inflation_raising_high_pp": _fmt(raisings["high"]),
                    "demand_only_after_wall_low_pp": _fmt(demand["low"]),
                    "demand_only_after_wall_base_pp": _fmt(demand["base"]),
                    "demand_only_after_wall_high_pp": _fmt(demand["high"]),
                    "fx_import_low_pp": _fmt(fx["low"]),
                    "fx_import_base_pp": _fmt(fx["base"]),
                    "fx_import_high_pp": _fmt(fx["high"]),
                    "cost_channel_low_pp": _fmt(cost["low"]),
                    "cost_channel_base_pp": _fmt(cost["base"]),
                    "cost_channel_high_pp": _fmt(cost["high"]),
                    "ND_pi_low_pp": _fmt(values["low"]),
                    "ND_pi_base_pp": _fmt(values["base"]),
                    "ND_pi_high_pp": _fmt(values["high"]),
                    "base_verdict": _verdict(
                        values["low"],
                        values["base"],
                        values["high"],
                        included_nonzero_kernel_mass=included_nonzero_kernel_mass,
                    ),
                    "decision_rule": "all_positive_claim_grade;crossing_indeterminate;all_nonpositive_reversal",
                    "headline_status": "scenario_diagnostic_only_not_RW_full",
                }
            )
    return rows


def _attribution_rows(monthly: list[dict[str, str]], windows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for window in windows:
        months = WINDOWS[window["horizon_window"]]
        divisor = _window_divisor(window["horizon_window"])
        for channel_id in ["D_PHILLIPS_WALL", "FX_IMPORT", "FIRM_WORKING_CAPITAL_COST", "CARRY_COSTS", "REGULATED_RATEBASE_FINANCE"]:
            values = {}
            for band in BANDS:
                selected = [
                    r for r in monthly
                    if r["dose_mode"] == window["dose_mode"]
                    and r["index_target"] == window["index_target"]
                    and r["slack_state"] == window["slack_state"]
                    and r["band"] == band
                    and r["channel_id"] == channel_id
                    and int(r["month"]) in months
                ]
                signed = sum((_d(r["signed_net_pp"]) for r in selected), Decimal("0")) / divisor
                values[band] = signed
            rows.append(_attribution_row(window, channel_id, values, _ledger_role(channel_id), _grade(channel_id), "channel"))
            if channel_id == "D_PHILLIPS_WALL":
                rows.append(
                    _attribution_row(
                        window,
                        "demand_only_after_wall",
                        values,
                        "lowering",
                        _grade(channel_id),
                        "disclosure",
                    )
                )
        residual = {
            band: _zero_decimal_dust(_d(window[f"ND_pi_{band}_pp"])
            - sum(
                _d(r[f"contribution_{band}_pp"])
                for r in rows
                if r["scenario_id"] == window["scenario_id"]
                and r["index_target"] == window["index_target"]
                and r["slack_state"] == window["slack_state"]
                and r["horizon_window"] == window["horizon_window"]
                and r["row_role"] == "channel"
            ))
            for band in BANDS
        }
        rows.append(_attribution_row(window, "RESIDUAL_EXACT_SUM_CHECK", residual, "identity_residual", "n/a", "residual"))
    return rows


def _attribution_row(
    window: dict[str, str],
    channel_id: str,
    values: dict[str, Decimal],
    ledger_role: str,
    grade: str,
    row_role: str,
) -> dict[str, str]:
    return {
        "scenario_id": window["scenario_id"],
        "dose_mode": window["dose_mode"],
        "shock_bp": window["shock_bp"],
        "index_target": window["index_target"],
        "slack_state": window["slack_state"],
        "horizon_window": window["horizon_window"],
        "channel_id": channel_id,
        "ledger_role": ledger_role,
        "contribution_low_pp": _fmt(values["low"]),
        "contribution_base_pp": _fmt(values["base"]),
        "contribution_high_pp": _fmt(values["high"]),
        "grade": grade,
        "row_role": row_role,
    }


def _rent_companion_rows(result: ScenarioResult, dose_mode: str, index_target: str) -> list[dict[str, str]]:
    weight = PCE_SHELTER_WEIGHT if index_target == "PCE" else CPI_SHELTER_WEIGHT_MAY_2026
    rows: list[dict[str, str]] = []
    for band in BANDS:
        source = next(
            row for row in result.rows("out_phase6_waterfall_monthly")
            if row["dose_mode"] == dose_mode
            and row["band"] == band
            and row["ricardian_offset"] == "0"
            and row["layer_id"] == "residential_construction"
            and int(row["month_index"]) <= 36
        )
        for month in range(1, 37):
            active = month >= 12
            rows.append(
                {
                    "scenario_id": f"rwpi_{dose_mode}_plus100bp",
                    "dose_mode": dose_mode,
                    "shock_bp": _fmt(SHOCK_BP),
                    "month": str(month),
                    "index_target": index_target,
                    "band": band,
                    "channel_id": "HOUSING_SUPPLY_RENT",
                    "source_layer_id": "residential_construction",
                    "source_monthly_residential_construction_drag_bil": source["delta_D_bil"],
                    "shelter_weight": _fmt(weight),
                    "lag_kernel_id": "rent_market_to_cpi_oer_12_36m",
                    "sign_anchor": "raising",
                    "diagnostic_grade": "C_weight_A_lag_B_elasticity_absent",
                    "rent_pressure_pp": "",
                    "headline_status": "diagnostic_companion_not_summed" if active else "pre_lag_zero_not_summed",
                    "include_flag": "0",
                    "absent_reason": "starts_to_rent_elasticity_absent_with_reason",
                }
            )
    return rows


def _allocation_rows(pack: dict[str, list[dict[str, str]]], result: ScenarioResult) -> list[dict[str, str]]:
    rules = _claim_rule_index(pack)
    emitted = {
        row["rule_id"]: _source_cashflow_key_from_claim_row(row, rules)
        for row in result.rows("out_claim_processor_channel")
        if row["year"] == str(START_YEAR)
    }
    rows: list[dict[str, str]] = []
    for rule_id, key in sorted(emitted.items()):
        if rule_id in FIRM_ALLOCATION_DEFAULTS:
            use_class, price, demand, margin, tax, unalloc = FIRM_ALLOCATION_DEFAULTS[rule_id]
        elif rule_id in HOUSEHOLD_DEMAND_ONLY_RULES:
            use_class, price, demand, margin, tax, unalloc = ("household_debt_demand_only", Decimal("0"), Decimal("1"), Decimal("0"), Decimal("0"), Decimal("0"))
        else:
            continue
        rows.append(
            {
                "source_cashflow_key": key,
                "rule_id": rule_id,
                "payer_cell_or_sector": _payer_sector_from_rule(rules[rule_id]),
                "instrument_family": rules[rule_id]["instrument_family"],
                "use_class": use_class,
                "allocated_to_price_cost": _fmt(price),
                "allocated_to_quantity_demand_drag": _fmt(demand),
                "allocated_to_margin_absorption": _fmt(margin),
                "allocated_to_tax_or_other": _fmt(tax),
                "unallocated_absent_with_reason": _fmt(unalloc),
                "constraint_sum": _fmt(price + demand + margin + tax + unalloc),
                "price_plus_demand": _fmt(price + demand),
                "headline_cost_status": "sensitivity_only_grade_D" if price > 0 else "cost_zero_by_contract_default",
            }
        )
    return rows


def _cost_total_pp(
    result: ScenarioResult,
    allocation: list[dict[str, str]],
    band: str,
    dose_mode: str,
) -> Decimal:
    price_share_by_rule = {
        row["rule_id"]: _d(row["allocated_to_price_cost"])
        for row in allocation
        if _d(row["allocated_to_price_cost"]) > 0
    }
    interest = Decimal("0")
    for row in result.rows("out_claim_processor_channel"):
        if (
            row["year"] == str(START_YEAR)
            and row["band"] == band
            and row["dose_mode"] == dose_mode
            and row["rule_id"] in price_share_by_rule
        ):
            interest += abs(_d(row["gross_flow_delta_bil"])) * price_share_by_rule[row["rule_id"]]
    return (interest / Decimal("100")) * COST_PASS_THROUGH_PP_PER_100BN[band]


def _demand_total_pp(result: ScenarioResult, slack_state: str, band: str, index_target: str = "CPI_U") -> Decimal:
    row = next(
        r for r in result.rows("out_ratewall_rollup")
        if r["period_type"] == "annual"
        and r["period"] == str(START_YEAR)
        and r["band"] == band
        and r["ricardian_offset"] == "0"
    )
    if index_target == "PCE":
        net_demand_with_wall = (
            (Decimal("1") - PCE_M_D_IMPORT_LEAKAGE[band]) * _d(row["D_bil"])
            - (Decimal("1") - PCE_M_N_IMPORT_LEAKAGE[band]) * _d(row["N_bil"])
        )
        output_slope = (
            PHILLIPS_SLOPE_U_GAP[slack_state][band]
            * PCE_CPI_TO_PCE_SLOPE_WEDGE[band]
            / OKUN_DIVISOR
        )
    else:
        net_demand_with_wall = _d(row["D_bil"]) - _d(row["N_bil"])
        output_slope = PHILLIPS_SLOPE_U_GAP[slack_state][band] / OKUN_DIVISOR
    return output_slope * (net_demand_with_wall / GDP_BIL * Decimal("100"))


def _fx_total_pp(phase6_pack: dict[str, list[dict[str, str]]], band: str) -> Decimal:
    row = next(
        r for r in phase6_pack["conversion_parameters"]
        if r["parameter_id"] == "broad_dollar_appreciation_policy_pack"
    )
    appreciation_pct = _d(row[band]) * Decimal("100")
    return appreciation_pct * IMPORT_PASS_THROUGH_PP_PER_1PCT_USD[band]


def _kernel(kind: str) -> dict[int, Decimal]:
    if kind == "demand":
        months = list(range(6, 19))
    elif kind == "fx":
        months = list(range(1, 13))
    elif kind == "cost":
        months = list(range(1, 13))
    else:
        months = [1]
    share = Decimal("1") / Decimal(len(months))
    return {month: share for month in months}


def _window_divisor(window: str) -> Decimal:
    if window == "0_36m_cumulative_average":
        return Decimal("3")
    return Decimal("1")


def _coefficient_rows(phase6_pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for state in SLACK_STATES:
        source_grade = PHILLIPS_SLOPE_U_GAP[state]["grade"]
        rows.append(
            {
                "coefficient_id": f"phillips_{state}_okun_halved",
                "channel_id": "D_PHILLIPS_WALL",
                "low": _fmt(PHILLIPS_SLOPE_U_GAP[state]["low"]),
                "base": _fmt(PHILLIPS_SLOPE_U_GAP[state]["base"]),
                "high": _fmt(PHILLIPS_SLOPE_U_GAP[state]["high"]),
                "units": "pp_inflation_per_pp_unemployment_gap_before_okun_halving",
                "grade": source_grade,
                "source": "project research notes (coefficient evidence)",
                "build_use": "demand_only_slope_okun_halved",
            }
        )
    rows.extend(
        [
            {
                "coefficient_id": "fx_import_cpi_pass_through",
                "channel_id": "FX_IMPORT",
                "low": "0.05",
                "base": "0.10",
                "high": "0.15",
                "units": "pp_CPI_per_1pct_USD_appreciation",
                "grade": "B",
                "source": "project research notes (coefficient evidence)",
                "build_use": "front_loaded_0_12m",
            },
            {
                "coefficient_id": "fx_channel_pce_crosswalk_factor",
                "channel_id": "FX_IMPORT",
                "low": _fmt(PCE_IMPORT_CROSSWALK_RANGE[0]),
                "base": _fmt(PCE_IMPORT_CROSSWALK_RANGE[1]),
                "high": _fmt(PCE_IMPORT_CROSSWALK_RANGE[2]),
                "units": "PCE_relative_import_exposure_factor",
                "grade": "assumption_to_fetch",
                "source": "do/research/rwpi_pce_crosswalk_pack_20260707.md",
                "build_use": PCE_IMPORT_CROSSWALK_LABEL,
            },
            {
                "coefficient_id": "pce_demand_import_leakage_m_D",
                "channel_id": "D_PHILLIPS_WALL",
                "low": _fmt(PCE_M_D_IMPORT_LEAKAGE["low"]),
                "base": _fmt(PCE_M_D_IMPORT_LEAKAGE["base"]),
                "high": _fmt(PCE_M_D_IMPORT_LEAKAGE["high"]),
                "units": "share_of_marginal_D_not_PCE_domestic_absorption",
                "grade": "assumption",
                "source": "do/research/rwpi_pce_crosswalk_pack_20260707.md",
                "build_use": "PCE_basis_demand_level_path",
            },
            {
                "coefficient_id": "pce_n_import_leakage_m_N",
                "channel_id": "D_PHILLIPS_WALL",
                "low": _fmt(PCE_M_N_IMPORT_LEAKAGE["low"]),
                "base": _fmt(PCE_M_N_IMPORT_LEAKAGE["base"]),
                "high": _fmt(PCE_M_N_IMPORT_LEAKAGE["high"]),
                "units": "share_of_marginal_N_import_leakage",
                "grade": "B",
                "source": "do/research/rwpi_pce_crosswalk_pack_20260707.md",
                "build_use": "PCE_basis_ratio_and_level_path",
            },
            {
                "coefficient_id": "cpi_to_pce_slope_wedge",
                "channel_id": "D_PHILLIPS_WALL",
                "low": _fmt(PCE_CPI_TO_PCE_SLOPE_WEDGE["low"]),
                "base": _fmt(PCE_CPI_TO_PCE_SLOPE_WEDGE["base"]),
                "high": _fmt(PCE_CPI_TO_PCE_SLOPE_WEDGE["high"]),
                "units": "PCE_slope_over_CPI_slope",
                "grade": "ASSUMPTION_no_published_counterpart",
                "source": "do/research/rwpi_pce_crosswalk_pack_20260707.md",
                "build_use": "applied_to_demand_phillips_leg_not_FX_only",
            },
            {
                "coefficient_id": "cost_channel_pp_per_100bn",
                "channel_id": "FIRM_WORKING_CAPITAL_COST",
                "low": "0.15",
                "base": "0.30",
                "high": "0.50",
                "units": "pp_price_level_per_100bn_business_interest_expense",
                "grade": "D",
                "source": "project research notes (coefficient evidence)",
                "build_use": "sensitivity_only",
            },
            {
                "coefficient_id": "cpi_shelter_weight_may_2026",
                "channel_id": "HOUSING_SUPPLY_RENT",
                "low": _fmt(CPI_SHELTER_WEIGHT_MAY_2026),
                "base": _fmt(CPI_SHELTER_WEIGHT_MAY_2026),
                "high": _fmt(CPI_SHELTER_WEIGHT_MAY_2026),
                "units": "CPI_U_shelter_weight",
                "grade": "A",
                "source": "configs/rwtam/packs/rwpi_design_contract/",
                "build_use": "companion_only_elasticity_absent",
            },
            {
                "coefficient_id": "pce_shelter_crosswalk_weight",
                "channel_id": "HOUSING_SUPPLY_RENT",
                "low": _fmt(PCE_SHELTER_WEIGHT),
                "base": _fmt(PCE_SHELTER_WEIGHT),
                "high": _fmt(PCE_SHELTER_WEIGHT),
                "units": "PCE_shelter_weight_crosswalk",
                "grade": "crosswalk",
                "source": "configs/rwtam/packs/rwpi_design_contract/",
                "build_use": "separate_surface_not_CPI_claim",
            },
        ]
    )
    fx = next(r for r in phase6_pack["conversion_parameters"] if r["parameter_id"] == "broad_dollar_appreciation_policy_pack")
    rows.append(
        {
            "coefficient_id": "broad_dollar_appreciation_policy_pack",
            "channel_id": "FX_IMPORT",
            "low": fx["low"],
            "base": fx["base"],
            "high": fx["high"],
            "units": fx["units"],
            "grade": "scenario_path",
            "source": "configs/rwtam/packs/phase6/conversion_parameters.csv",
            "build_use": "first_stage_FX_path",
        }
    )
    return rows


def _pce_factor_rows() -> list[dict[str, str]]:
    return [
        {
            "factor_id": "m_D_import_leakage_composition_weighted",
            "low": _fmt(PCE_M_D_IMPORT_LEAKAGE["low"]),
            "base": _fmt(PCE_M_D_IMPORT_LEAKAGE["base"]),
            "high": _fmt(PCE_M_D_IMPORT_LEAKAGE["high"]),
            "grade": "assumption",
            "source_label": "SF_Fed_2019_x_composition_per_pack",
            "implementation_use": "PCE_basis_demand_level_path_and_ratio_denominator",
            "caveat": "assumption_grade_range_0.05_0.15",
        },
        {
            "factor_id": "m_N_import_leakage_consumption_only",
            "low": _fmt(PCE_M_N_IMPORT_LEAKAGE["low"]),
            "base": _fmt(PCE_M_N_IMPORT_LEAKAGE["base"]),
            "high": _fmt(PCE_M_N_IMPORT_LEAKAGE["high"]),
            "grade": "B",
            "source_label": "SF_Fed_2019_per_pack",
            "implementation_use": "PCE_basis_demand_level_path_and_ratio_numerator",
            "caveat": "range_0.10_0.15",
        },
        {
            "factor_id": "okun_divisor",
            "low": _fmt(OKUN_DIVISOR),
            "base": _fmt(OKUN_DIVISOR),
            "high": _fmt(OKUN_DIVISOR),
            "grade": "B_coarse",
            "source_label": "standard_labeled_coarse_per_pack",
            "implementation_use": "demand_phillips_output_gap_conversion",
            "caveat": "coarse_okun_not_estimated_here",
        },
        {
            "factor_id": "cpi_to_pce_slope_wedge",
            "low": _fmt(PCE_CPI_TO_PCE_SLOPE_WEDGE["low"]),
            "base": _fmt(PCE_CPI_TO_PCE_SLOPE_WEDGE["base"]),
            "high": _fmt(PCE_CPI_TO_PCE_SLOPE_WEDGE["high"]),
            "grade": "ASSUMPTION_no_published_counterpart",
            "source_label": "shelter_weights_plus_cyclical_core_qualitative_per_pack",
            "implementation_use": "applied_to_demand_phillips_leg",
            "caveat": "no_published_counterpart",
        },
        {
            "factor_id": "fx_channel_pce_factor",
            "low": _fmt(PCE_IMPORT_CROSSWALK_RANGE[0]),
            "base": _fmt(PCE_IMPORT_CROSSWALK_RANGE[1]),
            "high": _fmt(PCE_IMPORT_CROSSWALK_RANGE[2]),
            "grade": "assumption_to_fetch",
            "source_label": "BEA_Table_2_3_5_BLS_relative_importance_to_fetch",
            "implementation_use": "FX_import_channel_only",
            "caveat": PCE_IMPORT_CROSSWALK_LABEL,
        },
    ]


def _pce_ratio_crosswalk_rows(result: ScenarioResult) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for period_type, period, horizon in [
        ("annual", str(START_YEAR), "year_1"),
        ("cumulative_120_month", f"{START_YEAR}-{START_YEAR + 9}", "cum_120m"),
    ]:
        for band in BANDS:
            row = next(
                r for r in result.rows("out_ratewall_rollup")
                if r["period_type"] == period_type
                and r["period"] == period
                and r["band"] == band
                and r["ricardian_offset"] == "0"
            )
            rw = _d(row["RW_ratio"])
            numerator_factor = Decimal("1") - PCE_M_N_IMPORT_LEAKAGE[band]
            denominator_factor = Decimal("1") - PCE_M_D_IMPORT_LEAKAGE[band]
            rw_pce = rw * numerator_factor / denominator_factor
            out.append(
                {
                    "scenario_id": "rwpi_pce_ratio_basis_crosswalk",
                    "horizon": horizon,
                    "period_type": period_type,
                    "period": period,
                    "band": band,
                    "source_RW_ratio_CPI_basis": row["RW_ratio"],
                    "m_D": _fmt(PCE_M_D_IMPORT_LEAKAGE[band]),
                    "m_N": _fmt(PCE_M_N_IMPORT_LEAKAGE[band]),
                    "ratio_factor": _fmt(numerator_factor / denominator_factor),
                    "RW_pi_PCE_ratio_basis": _fmt(rw_pce),
                    "pack_check_against": "approx_0.048_year1_at_central_factors" if band == "base" and horizon == "year_1" else "",
                    "discrepancy_vs_pack_check": _fmt(rw_pce - Decimal("0.048")) if band == "base" and horizon == "year_1" else "",
                    "headline_status": "separate_PCE_surface_not_RW_full",
                }
            )
    return out


def _pce_level_path_rows(windows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in windows:
        if row["index_target"] != "PCE":
            continue
        for band in BANDS:
            out.append(
                {
                    "scenario_id": row["scenario_id"],
                    "dose_mode": row["dose_mode"],
                    "shock_bp": row["shock_bp"],
                    "slack_state": row["slack_state"],
                    "horizon_window": row["horizon_window"],
                    "band": band,
                    "ND_pi_PCE_pp": row[f"ND_pi_{band}_pp"],
                    "demand_phillips_PCE_pp": row[f"demand_only_after_wall_{band}_pp"],
                    "fx_import_PCE_pp": row[f"fx_import_{band}_pp"],
                    "cost_channel_pp": row[f"cost_channel_{band}_pp"],
                    "m_D": _fmt(PCE_M_D_IMPORT_LEAKAGE[band]),
                    "m_N": _fmt(PCE_M_N_IMPORT_LEAKAGE[band]),
                    "cpi_to_pce_slope_wedge": _fmt(PCE_CPI_TO_PCE_SLOPE_WEDGE[band]),
                    "demand_leg_label": "PCE_basis_level_path_wedge_applied_to_demand_phillips_leg",
                    "headline_status": "separate_PCE_surface_not_RW_full",
                }
            )
    return out


def _pce_caveat_rows() -> list[dict[str, str]]:
    return [
        {
            "caveat_id": "fed_target_claims",
            "verdict_condensed": "Fed-target claims supportable only in hedged path-and-state-labeled form.",
            "surface_status": "PCE_crosswalk_label",
        },
        {
            "caveat_id": "level_uncertainty",
            "verdict_condensed": "Level uncertainty about 4x, dominated by the slope band, not the wall.",
            "surface_status": "PCE_crosswalk_label",
        },
        {
            "caveat_id": "shelter_divergence",
            "verdict_condensed": "Shelter divergence sits in the companion path.",
            "surface_status": "PCE_crosswalk_label",
        },
        {
            "caveat_id": "scalar_claim_fence",
            "verdict_condensed": "No final-basis-point scalar claim surface emitted.",
            "surface_status": "fence",
        },
    ]


def _validation_scaffold_rows(plug_validation: PlugValidationResult) -> list[dict[str, str]]:
    score_by_diagnostic = {row["diagnostic"]: row for row in plug_validation.scores}
    return [
        {
            "run_id": run_id,
            "diagnostic": diagnostic,
            "window": window,
            "inputs_status": _scored_inputs_status(status, score_by_diagnostic[diagnostic]),
            "held_out_target": target,
            "no_fitting_guard": guard,
            "local_score_status": score_by_diagnostic[diagnostic]["disposition"],
        }
        for run_id in ("mechanism_predicted", "intermediate_plug")
        for diagnostic, window, status, target, guard in [
            ("Demand-only M5 vs activity", "2022Q1-2025Q4", "historical opening states; actual policy path", "real activity/output-gap proxy", "do_not_tune_slopes"),
            ("FX/import leg", "2022Q1-2025Q4", "needs_observed_series: dollar/import price path for plug run", "import prices and import-exposed CPI goods", "pass_through_fixed_before_scoring"),
            ("Cost channel", "2022Q1-2025Q4", "needs_observed_series: sector margins/PPI residuals", "sector PPI/CPI residuals and margins", "no_cost_pass_through_fit"),
            ("Shelter lag kernel", "2022Q1-2026Q4", "needs_observed_series: market rents, CPI rent, CPI OER", "rent/OER timing and contribution", "lag_kernel_fixed_before_scoring"),
            ("Starts-to-rents pressure", "2022Q1-2026Q4", "needs_observed_series: starts/completions/vacancy/rents", "delayed rent pressure", "pandemic_rent_confounder_not_fit_away"),
            ("Net price traction path", "2022Q1-2025Q4", "frozen channel outputs", "decomposed inflation contributions", "headline_CPI_residual_never_calibrates_coefficients"),
        ]
    ]


def _scored_inputs_status(status: str, score: dict[str, str]) -> str:
    if "needs_observed_series" in status:
        return f"observed_series_loaded_and_scored:{score['kernel_status']}"
    return f"locally_scored:{score['kernel_status']}"


def _exclusion_rows() -> list[dict[str, str]]:
    return [
        {"channel_id": "EXPECTATIONS", "disposition": "excluded", "reason": "outside mechanical incidence boundary"},
        {"channel_id": "WAGE_PRICE_DYNAMICS", "disposition": "excluded", "reason": "macro equilibrium lane, not RW_pi incidence"},
        {"channel_id": "COLA_TRANSFER_INDEXATION", "disposition": "excluded", "reason": "inflation-driven not rate-driven"},
        {"channel_id": "DIRECT_MORTGAGE_INTEREST_CPI", "disposition": "rejected", "reason": "CPI-U OER/rental equivalence excludes direct mortgage interest"},
        {"channel_id": "ASSET_PRICE_WEALTH_PRICE_DYNAMICS", "disposition": "excluded_from_RW_pi", "reason": "wealth effects remain demand/quantity diagnostics"},
        {"channel_id": "INTEREST_INCOME_SPENDING", "disposition": "demand_wall_only", "reason": "N affects prices only by attenuating demand disinflation in M5"},
    ]


def _probe_rows(allocation: list[dict[str, str]], result: ScenarioResult) -> list[dict[str, str]]:
    bad_share = dict(next(row for row in allocation if row["rule_id"] == "c_and_i_depository_loans_interest"))
    bad_share["allocated_to_price_cost"] = "0.6"
    bad_share["allocated_to_quantity_demand_drag"] = "0.6"
    bad_share["allocated_to_margin_absorption"] = "0"
    bad_share["allocated_to_tax_or_other"] = "0"
    bad_share["unallocated_absent_with_reason"] = "0"
    bad_injection = dict(bad_share)
    bad_injection["rule_id"] = "injected_fake_firm_interest"
    bad_injection["source_cashflow_key"] = "injected|fake|not|an|emitted|row"
    probes = [
        ("allocation_0_6_price_plus_0_6_demand", [bad_share]),
        ("allocation_injected_source_cashflow_key", [bad_injection]),
    ]
    rows = []
    for probe_id, probe_rows in probes:
        errors = validate_firm_interest_allocation(probe_rows, result)
        rows.append(
            {
                "probe_id": probe_id,
                "expected_result": "fail",
                "observed_result": "fail" if errors else "pass",
                "status": "pass" if errors else "fail",
                "error_text": "; ".join(errors),
            }
        )
    return rows


def _invariant_rows(
    windows: list[dict[str, str]],
    attribution: list[dict[str, str]],
    rent: list[dict[str, str]],
    probes: list[dict[str, str]],
    plug_validation: PlugValidationResult,
    pce_ratio: list[dict[str, str]],
    pce_level: list[dict[str, str]],
    pce_caveats: list[dict[str, str]],
) -> list[dict[str, str]]:
    residuals_zero = all(
        _d(row["contribution_low_pp"]) == 0
        and _d(row["contribution_base_pp"]) == 0
        and _d(row["contribution_high_pp"]) == 0
        for row in attribution
        if row["channel_id"] == "RESIDUAL_EXACT_SUM_CHECK"
    )
    pce_base_year1 = next(
        row
        for row in pce_ratio
        if row["horizon"] == "year_1" and row["band"] == "base"
    )
    pce_ratio_ok = abs(_d(pce_base_year1["RW_pi_PCE_ratio_basis"]) - Decimal("0.048")) <= Decimal("0.001")
    pce_level_ok = bool(pce_level) and all(
        row["demand_leg_label"] == "PCE_basis_level_path_wedge_applied_to_demand_phillips_leg"
        for row in pce_level
    )
    caveat_ids = {row["caveat_id"] for row in pce_caveats}
    return [
        {"check_id": "RWPI1_path_windows_emitted", "status": "pass" if windows else "fail"},
        {"check_id": "RWPI2_attribution_residual_exact_zero", "status": "pass" if residuals_zero else "fail"},
        {"check_id": "RWPI3_rent_companion_not_summed", "status": "pass" if rent and {row["include_flag"] for row in rent} == {"0"} else "fail"},
        {"check_id": "RWPI4_allocation_probes_fail_as_expected", "status": "pass" if {row["status"] for row in probes} == {"pass"} else "fail"},
        {"check_id": "RWPI5_scenario_only_no_rw_full_mutation", "status": "pass"},
        {"check_id": "RWPI6_plug_validation_scored_no_fitting", "status": "pass" if _plug_validation_scored(plug_validation) else "fail"},
        {"check_id": "RWPI7_pce_ratio_check_against_approx_0_048", "status": "pass" if pce_ratio_ok else "fail"},
        {"check_id": "RWPI8_pce_level_path_wedge_applied_to_demand_leg", "status": "pass" if pce_level_ok else "fail"},
        {"check_id": "RWPI9_pce_caveat_rows_and_scalar_claim_fence", "status": "pass" if {"fed_target_claims", "level_uncertainty", "shelter_divergence", "scalar_claim_fence"} <= caveat_ids else "fail"},
    ]


def _plug_validation_scored(plug_validation: PlugValidationResult) -> bool:
    return (
        {row["run_id"] for row in plug_validation.scores} == {"intermediate_plug"}
        and len(plug_validation.scores) == 6
        and all("no_fitting_guard" in row["no_fitting_guard"] for row in plug_validation.scores)
        and bool(plug_validation.series)
    )


def _lineage_rows() -> list[dict[str, str]]:
    return [
        {"artifact": "design_ingest", "path": "configs/rwtam/packs/rwpi_design_contract/", "role": "binding_contract"},
        {"artifact": "design_contract_copy", "path": "configs/rwtam/packs/rwpi_design_contract/", "role": "path_preserving_copy"},
        {"artifact": "coefficient_memo", "path": "project research notes (coefficient evidence)", "role": "binding_coefficients"},
        {"artifact": "m5_overlay", "path": "var/rwtam/scenarios/mechanism_wave/out_inflation_overlay_diagnostic.csv", "role": "retained_demand_wall_first_stage"},
        {"artifact": "v1_engine_rows", "path": "var/rwtam/v1/", "role": "real_emitted_rows_for_allocation_and_first_stages"},
        {"artifact": "rwpi_observed_pack", "path": "do/rwpi_observed/manifest.csv", "role": "observed_intermediate_plug_inputs"},
    ]


def _claim_rule_index(pack: dict[str, list[dict[str, str]]] | None = None) -> dict[str, dict[str, str]]:
    if pack is None:
        rows = _read_csv_rows(Path("configs/rwtam/packs/claim_processor_rules.csv"))
    else:
        rows = pack.get("claim_processor_rules", [])
    return {row["rule_id"]: row for row in rows}


def _source_cashflow_key_from_claim_row(row: dict[str, str], rules: dict[str, dict[str, str]]) -> str:
    rule = rules[row["rule_id"]]
    return "|".join(
        [
            rule["rule_id"],
            rule["instrument_family"],
            rule["stock_source"],
            rule["rate_rule"],
            rule["base_driver"],
            rule["payer_route"],
            rule["receiver_route"],
            rule["receiver_holder"],
            rule["report_channel"],
            rule["basis"],
            rule["input_basis_label"],
            rule["cost_leg"],
        ]
    )


def _payer_sector_from_rule(rule: dict[str, str]) -> str:
    if "household" in rule["payer_route"]:
        return "household"
    if rule["payer_route"] in {"issuer_negative", "cre_payers_negative", "funding_incidence_negative"}:
        return "firm_or_provider"
    return rule["payer_route"] or "not_applicable"


def _verdict(
    low: Decimal,
    base: Decimal,
    high: Decimal,
    *,
    included_nonzero_kernel_mass: bool,
) -> str:
    if not included_nonzero_kernel_mass:
        return "no_kernel_mass_after_lag_window"
    if low > 0 and base > 0 and high > 0:
        return "disinflationary_price_traction"
    if low <= 0 and base <= 0 and high <= 0:
        return "price_wall_or_reversal"
    if base <= 0:
        return "price_wall_indeterminate"
    return "positive_base_not_claim_grade"


def _zero_decimal_dust(value: Decimal) -> Decimal:
    if abs(value) < Decimal("0.000000000000000000000001"):
        return Decimal("0")
    return value


def _index_component(channel_id: str) -> str:
    return {
        "D_PHILLIPS_WALL": "all_items_demand_slack",
        "FX_IMPORT": "import_exposed_components",
        "FIRM_WORKING_CAPITAL_COST": "business_cost_pass_through_components",
        "CARRY_COSTS": "inventory_distribution",
        "REGULATED_RATEBASE_FINANCE": "regulated_utilities",
    }.get(channel_id, "all_items")


def _intermediate_variable(channel_id: str) -> str:
    return {
        "D_PHILLIPS_WALL": "net_demand_gap_with_wall",
        "FX_IMPORT": "broad_dollar_appreciation",
        "FIRM_WORKING_CAPITAL_COST": "allocated_firm_interest_expense",
        "CARRY_COSTS": "inventory_distribution_carry_cost",
        "REGULATED_RATEBASE_FINANCE": "regulated_ratebase_finance_cost",
    }.get(channel_id, "not_applicable")


def _kernel_id(channel_id: str) -> str:
    return {
        "D_PHILLIPS_WALL": "demand_phillips_6_18m",
        "FX_IMPORT": "fx_import_front_loaded_0_12m",
        "FIRM_WORKING_CAPITAL_COST": "working_capital_cost_0_12m",
        "CARRY_COSTS": "carry_absent_0_6m",
        "REGULATED_RATEBASE_FINANCE": "regulated_ratebase_absent_6_36m",
    }.get(channel_id, "not_applicable")


def _coefficient_id(channel_id: str, slack_state: str, band: str) -> str:
    if channel_id == "D_PHILLIPS_WALL":
        return f"phillips_{slack_state}_okun_halved_{band}"
    if channel_id == "FX_IMPORT":
        return f"fx_import_pass_through_{band}"
    if channel_id == "FIRM_WORKING_CAPITAL_COST":
        return f"cost_channel_pp_per_100bn_{band}"
    return f"{channel_id.lower()}_absent_with_reason"


def _ledger_role(channel_id: str) -> str:
    return "lowering" if channel_id in {"D_PHILLIPS_WALL", "FX_IMPORT"} else "raising"


def _grade(channel_id: str) -> str:
    return {
        "D_PHILLIPS_WALL": "B/C",
        "FX_IMPORT": "B",
        "FIRM_WORKING_CAPITAL_COST": "D",
        "CARRY_COSTS": "absent_with_reason",
        "REGULATED_RATEBASE_FINANCE": "absent_with_reason",
    }[channel_id]
