"""Final marginal RateWall model gate."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_SELECTED_NUMERATOR_PATH = Path(
    "var/preliminary_scenario_results/marginal_numerator/"
    "ratewall_marginal_selected_numerator_surface.csv"
)
DEFAULT_DENOMINATOR_PATH = Path(
    "var/preliminary_scenario_results/marginal_denominator/"
    "ratewall_marginal_denominator_surface.csv"
)
DEFAULT_SAFE_YIELD_PATH = Path(
    "var/preliminary_scenario_results/marginal_safe_yield/"
    "ratewall_marginal_safe_yield_delta.csv"
)
DEFAULT_ADMITTED_RESIDUAL_PATH = Path(
    "var/preliminary_scenario_results/marginal_residual/"
    "ratewall_marginal_admitted_disjoint_delta.csv"
)
DEFAULT_RESIDUAL_SIDECAR_PATH = Path(
    "var/preliminary_scenario_results/marginal_residual/"
    "ratewall_residual_safe_yield_sidecar.csv"
)
DEFAULT_CREDIT_SIDECAR_PATH = Path(
    "var/preliminary_scenario_results/marginal_residual/"
    "ratewall_credit_insulation_sidecar.csv"
)
DEFAULT_TDC_SUPPORT_PATH = Path(
    "var/preliminary_scenario_results/marginal_tdcsim/"
    "ratewall_marginal_tdc_support_panel.csv"
)
DEFAULT_TDCSIM_PAIR_ROOT = Path(
    "var/preliminary_scenario_results/marginal_tdcsim/source_pairs"
)
DEFAULT_PI_DEBT_AUDIT_PATH = Path(
    "var/preliminary_scenario_results/marginal_public_interest/"
    "ratewall_public_interest_debt_repricing_audit.csv"
)
DEFAULT_REMITTANCE_ASSUMPTIONS_PATH = Path(
    "configs/assumption_mode/ratewall_public_interest_remittance_absorber_assumptions.csv"
)
DEFAULT_HISTORICAL_WINDOW_PATH = Path(
    "configs/assumption_mode/ratewall_historical_selected_window.csv"
)

FINAL_MARGINAL_RW_RATIO_FIELDS = [
    "final_marginal_rw_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "demand_conversion_case",
    "selected_marginal_n_bil",
    "selected_marginal_D_bil",
    "final_rw_m",
    "final_rw_m_selected",
    "readiness_status",
    "blocked_reason",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

FINAL_MARGINAL_READINESS_FIELDS = [
    "final_marginal_readiness_row_id",
    "check_id",
    "check_status",
    "row_count",
    "selected_row_count",
    "required_rule",
    "evidence",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

SELECTED_RW_M_RWTAM_BLOCKED_USE = "comparison_or_summation_with_rwtam_headline_rw_full"
SELECTED_RW_M_CLAIM_BOUNDARY = (
    "RW_M uses the conventional-demand-drag threshold denominator "
    "(0.776pp GDP owner band) and gated-delta numerator with safe-yield + "
    "residual on owner assumption-mode bases; NOT comparable to RWTAM RW_full."
)
NONSELECTED_RW_M_BLOCKED_USE = "canonical_headline_promotion;selected_rw_m"
FINAL_RW_M_REQUIREMENTS_CLAIM_BOUNDARY = (
    "final_rw_m_requires_selected_marginal_n_and_selected_marginal_D"
)

EXPOSURE_DIAGNOSTICS_SNAPSHOT_FIELDS = [
    "exposure_diagnostic_snapshot_row_id",
    "diagnostic_surface_id",
    "diagnostic_role",
    "selected_final_rw_m_allowed",
    "required_rebuild",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class FinalMarginalModelError(ValueError):
    """Raised when final marginal RW_M rows violate selection rules."""


def final_marginal_rw_ratio_rows(
    *,
    selected_numerator_path: str | Path = DEFAULT_SELECTED_NUMERATOR_PATH,
    denominator_path: str | Path = DEFAULT_DENOMINATOR_PATH,
) -> list[dict[str, str]]:
    numerator_rows = _read_csv(Path(selected_numerator_path))
    denominator_by_key = {
        (row["period"], row["horizon"], row["state_id"], row["shock_path_id"]): row
        for row in _read_csv(Path(denominator_path))
        if row.get("selected_marginal_D") == "true"
    }
    rows = []
    for n_row in numerator_rows:
        key = (n_row["period"], n_row["horizon"], n_row["state_id"], n_row["shock_path_id"])
        d_row = denominator_by_key.get(key)
        n_ok = n_row["selected_marginal_n_allowed"] == "true"
        d_ok = d_row is not None
        if n_ok and d_ok:
            n = Decimal(n_row["selected_marginal_n_bil"])
            d = Decimal(d_row["marginal_denominator_bil"])
            ratio = n / d
            selected = True
            blocked = ""
            status = "pass_final_marginal_rw_selected"
        else:
            n = None
            d = Decimal(d_row["marginal_denominator_bil"]) if d_row else None
            ratio = None
            selected = False
            missing = []
            if not n_ok:
                missing.append("selected_marginal_n")
            if not d_ok:
                missing.append("selected_marginal_D")
            blocked = ";".join(missing)
            status = "fail_closed_final_marginal_rw_incomplete"
        rows.append(
            {
                "final_marginal_rw_row_id": f"final_marginal_rw::{n_row['period']}::{n_row['state_id']}",
                "period_object": n_row["period_object"],
                "period": n_row["period"],
                "horizon": n_row["horizon"],
                "state_id": n_row["state_id"],
                "shock_path_id": n_row["shock_path_id"],
                "demand_conversion_case": n_row.get("demand_conversion_case", ""),
                "selected_marginal_n_bil": _fmt(n) if n is not None else "",
                "selected_marginal_D_bil": _fmt(d) if d is not None else "",
                "final_rw_m": _fmt(ratio) if ratio is not None else "",
                "final_rw_m_selected": str(selected).lower(),
                "readiness_status": status,
                "blocked_reason": blocked,
                "allowed_use": "final_marginal_rw" if selected else "final_marginal_gap_surface",
                "blocked_use": (
                    SELECTED_RW_M_RWTAM_BLOCKED_USE
                    if selected
                    else NONSELECTED_RW_M_BLOCKED_USE
                ),
                "claim_boundary": (
                    SELECTED_RW_M_CLAIM_BOUNDARY
                    if selected
                    else FINAL_RW_M_REQUIREMENTS_CLAIM_BOUNDARY
                ),
            }
        )
    validate_final_marginal_rw_ratio_rows(rows)
    return rows


def final_marginal_readiness_rows(
    ratio_rows: Sequence[Mapping[str, str]],
    *,
    denominator_path: str | Path = DEFAULT_DENOMINATOR_PATH,
    safe_yield_path: str | Path = DEFAULT_SAFE_YIELD_PATH,
    admitted_residual_path: str | Path = DEFAULT_ADMITTED_RESIDUAL_PATH,
    residual_sidecar_path: str | Path = DEFAULT_RESIDUAL_SIDECAR_PATH,
    credit_sidecar_path: str | Path = DEFAULT_CREDIT_SIDECAR_PATH,
    tdc_support_path: str | Path = DEFAULT_TDC_SUPPORT_PATH,
    tdcsim_pair_root: str | Path = DEFAULT_TDCSIM_PAIR_ROOT,
    pi_debt_audit_path: str | Path = DEFAULT_PI_DEBT_AUDIT_PATH,
    remittance_assumptions_path: str | Path = DEFAULT_REMITTANCE_ASSUMPTIONS_PATH,
    historical_window_path: str | Path = DEFAULT_HISTORICAL_WINDOW_PATH,
    full_test_suite_passed: bool = False,
) -> list[dict[str, str]]:
    selected = [row for row in ratio_rows if row["final_rw_m_selected"] == "true"]
    denominator = _read_csv(Path(denominator_path))
    safe_yield = _read_csv(Path(safe_yield_path))
    admitted_residual = _read_csv(Path(admitted_residual_path))
    residual_sidecar = _read_csv(Path(residual_sidecar_path))
    credit_sidecar = _read_csv(Path(credit_sidecar_path))
    tdc_support = _read_csv(Path(tdc_support_path))
    debt_audit = _read_csv(Path(pi_debt_audit_path))
    remittance = _read_csv(Path(remittance_assumptions_path))
    historical_window = _read_csv(Path(historical_window_path))
    pair_dir_count = _tdcsim_pair_dir_count(Path(tdcsim_pair_root))

    selected_period_objects = {row["period_object"] for row in selected}
    selected_forecast_count = sum(1 for row in selected if row["period_object"] == "forecast")
    selected_current_forecast_count = sum(
        1 for row in selected if row["period_object"] in {"current", "forecast"}
    )
    historical_rows = [row for row in ratio_rows if row["period_object"] == "historical"]
    selected_historical_periods = {
        row["period"]
        for row in historical_window
        if row.get("selected_historical_rw_m_allowed_if_complete", "").lower()
        == "true"
    }
    selected_historical_rows = [
        row for row in selected if row["period_object"] == "historical"
    ]
    selected_safe_yield = [
        row for row in safe_yield if row.get("selected_safe_yield_delta_allowed") == "true"
    ]
    selected_residual = [
        row
        for row in admitted_residual
        if row.get("selected_admitted_disjoint_delta_allowed") == "true"
    ]
    selected_debt_replacements = [
        row for row in debt_audit if row.get("replacement_recommended") == "true"
    ]
    checks = [
        _check(
            "final_rw_m_selected_current_forecast_and_historical_true_v1_window",
            selected_current_forecast_count == 11
            and {"current", "forecast"}.issubset(selected_period_objects)
            and {row["period"] for row in selected_historical_rows}
            == selected_historical_periods,
            len(ratio_rows),
            len(selected),
            "selected final RW_M rows include current 2026, forecast 2027-2036, and the selected historical true-V1 window",
            f"selected_period_objects={sorted(selected_period_objects)}",
            "missing_current_forecast_or_historical_true_v1_selected_rows",
        ),
        _check(
            "historical_rows_outside_true_v1_window_fail_closed_not_omitted",
            bool(historical_rows)
            and all(
                row["final_rw_m_selected"] == "true"
                or row["period"] not in selected_historical_periods
                for row in historical_rows
            ),
            len(ratio_rows),
            len(selected_historical_rows),
            "historical rows outside the selected source-backed window remain present and fail closed",
            f"historical_rows={len(historical_rows)};selected_historical_rows={len(selected_historical_rows)}",
            "historical_selected_rw_m_outside_source_backed_true_v1_window",
        ),
        _check(
            "safe_yield_selected_assumption_mode_current_forecast",
            bool(safe_yield)
            and len(selected_safe_yield) == selected_current_forecast_count
            and all(
                Decimal(row.get("delta_safe_yield_bil") or "0") != 0
                for row in selected_safe_yield
            ),
            len(safe_yield),
            len(selected_safe_yield),
            "D1 safe-yield has selected current/forecast assumption rows and nonzero deltas",
            f"rows={len(safe_yield)};selected_safe_yield_rows={len(selected_safe_yield)}",
            "missing_or_zero_safe_yield_after_promotion_gate",
        ),
        _check(
            "admitted_residual_selected_private_safe_yield_assumption_mode",
            bool(admitted_residual)
            and len(selected_residual) == selected_current_forecast_count
            and all(
                Decimal(row.get("delta_other_admitted_disjoint_bil") or "0") != 0
                for row in selected_residual
            ),
            len(admitted_residual),
            len(selected_residual),
            "admitted-disjoint residual has selected current/forecast private safe-yield rows",
            f"rows={len(admitted_residual)};selected_residual_rows={len(selected_residual)}",
            "missing_or_zero_residual_after_promotion_gate",
        ),
        _check(
            "residual_and_credit_sidecars_formula_gated_nonselected",
            bool(residual_sidecar)
            and bool(credit_sidecar)
            and all(row.get("selected_n_addition_allowed") == "false" for row in residual_sidecar)
            and all(row.get("selected_n_addition_allowed") == "false" for row in credit_sidecar),
            len(residual_sidecar) + len(credit_sidecar),
            0,
            "residual/MMF/T-bill and credit sidecars are formula-visible but nonselected",
            f"residual_sidecar_rows={len(residual_sidecar)};credit_sidecar_rows={len(credit_sidecar)}",
            "direct_sidecar_selected_n_addition",
        ),
        _check(
            "pi_forecast_debt_repricing_replacement_selected",
            bool(debt_audit)
            and len(selected_debt_replacements) == selected_forecast_count,
            len(debt_audit),
            len(selected_debt_replacements),
            "forecast explicit debt-stock/maturity repricing replacement passes for selected forecast rows",
            f"rows={len(debt_audit)};forecast_replacement_rows={len(selected_debt_replacements)}",
            "missing_forecast_debt_stock_repricing_replacement_after_promotion_gate",
        ),
        _check(
            "remittance_absorber_zero_inside_pi",
            bool(remittance)
            and all(Decimal(row.get("current_remittance_demand_share") or "0") == 0 for row in remittance)
            and all(Decimal(row.get("future_remittance_drag_current_demand_share") or "0") == 0 for row in remittance),
            len(remittance),
            0,
            "remittance absorber rows are selected zero assumptions inside PI",
            f"rows={len(remittance)}",
            "standalone_or_nonzero_remittance_without_owner_gate",
        ),
        _check(
            "tdc_term_present_as_income_addendum_or_fail_closed_zero",
            len(tdc_support) == len(selected)
            and all(_tdc_term_available_for_selected_n(row) for row in tdc_support),
            len(tdc_support),
            sum(1 for row in tdc_support if _tdc_term_available_for_selected_n(row)),
            "TDC rows consumed by selected N must be admitted income addendum rows or retired fail-closed zero rows",
            f"rows={len(tdc_support)}",
            "tdc_term_missing_or_old_chi_support_selected",
        ),
        _check(
            "tdcsim_source_pair_packaging_status",
            pair_dir_count >= len(selected) and len(tdc_support) == len(selected),
            pair_dir_count,
            len(tdc_support),
            "source-pair directories are materialized for selected current/forecast/historical marginal TDC support",
            f"source_pair_dirs={pair_dir_count};support_rows={len(tdc_support)}",
            "tdcsim_source_pair_packaging_missing",
        ),
        _check(
            "denominator_surface_rebuildable",
            len(denominator) == 351
            and sum(1 for row in denominator if row.get("selected_marginal_D") == "true") == 117,
            len(denominator),
            sum(1 for row in denominator if row.get("selected_marginal_D") == "true"),
            "denominator surface has low/base/high rows and one selected base D per period",
            f"rows={len(denominator)}",
            "missing_or_nonrebuildable_marginal_D_surface",
        ),
        _check(
            "legacy_exposure_outputs_diagnostic_only",
            True,
            len(ratio_rows),
            len(selected),
            "old current/forecast/historical exposure ratios are diagnostics only",
            "final marginal model uses marginal numerator and denominator outputs",
            "old_current_forecast_or_historical_ratio_as_final_rw_m",
        ),
        _check(
            "full_test_suite_passed",
            full_test_suite_passed,
            len(ratio_rows),
            len(selected),
            "full pytest must pass before release-style V1 finality claim",
            "set by build_final_marginal_model.py --full-test-suite-passed after validation",
            "claiming_release_finality_without_full_pytest",
        ),
    ]
    return [
        {
            "final_marginal_readiness_row_id": f"final_marginal_readiness::{check_id}",
            "check_id": check_id,
            "check_status": "pass" if ok else "fail",
            "row_count": str(_rows),
            "selected_row_count": str(_selected_rows),
            "required_rule": rule,
            "evidence": evidence,
            "allowed_use": "final_marginal_readiness_ledger",
            "blocked_use": blocked,
            "claim_boundary": "readiness_check_for_v1_marginal_finality_closeout",
        }
        for check_id, ok, _rows, _selected_rows, rule, evidence, blocked in checks
    ]


def exposure_diagnostics_snapshot_rows() -> list[dict[str, str]]:
    rows = [
        (
            "current_object_bridge",
            "current_exposure_diagnostic",
            "current_same_state_delta_rebuild_required",
        ),
        (
            "forecast_central_scenario_surface",
            "forecast_exposure_diagnostic",
            "forecast_plus_100bp_year_delta_rebuild_required",
        ),
        (
            "historical_root_public_interest_rw_panel",
            "historical_context_diagnostic",
            "historical_same_quarter_delta_N_rebuild_required",
        ),
    ]
    return [
        {
            "exposure_diagnostic_snapshot_row_id": f"exposure_diagnostic_snapshot::{surface}",
            "diagnostic_surface_id": surface,
            "diagnostic_role": role,
            "selected_final_rw_m_allowed": "false",
            "required_rebuild": rebuild,
            "allowed_use": "final_marginal_exposure_diagnostic_snapshot",
            "blocked_use": "selected_rw_m;canonical_headline_promotion",
            "claim_boundary": "old_exposure_ratio_separated_from_final_marginal_model",
        }
        for surface, role, rebuild in rows
    ]


def write_final_marginal_model_outputs(
    output_dir: str | Path,
    *,
    ratio_rows: Sequence[Mapping[str, str]],
    readiness_rows: Sequence[Mapping[str, str]],
    diagnostic_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "ratio_snapshot_csv": out / "ratewall_final_marginal_rw_ratio_snapshot.csv",
        "readiness_csv": out / "ratewall_final_marginal_readiness_ledger.csv",
        "diagnostics_csv": out / "ratewall_exposure_diagnostics_snapshot.csv",
    }
    write_rows(
        paths["ratio_snapshot_csv"],
        [dict(row) for row in ratio_rows],
        FINAL_MARGINAL_RW_RATIO_FIELDS,
    )
    write_rows(
        paths["readiness_csv"],
        [dict(row) for row in readiness_rows],
        FINAL_MARGINAL_READINESS_FIELDS,
    )
    write_rows(
        paths["diagnostics_csv"],
        [dict(row) for row in diagnostic_rows],
        EXPOSURE_DIAGNOSTICS_SNAPSHOT_FIELDS,
    )
    return paths


def validate_final_marginal_rw_ratio_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise FinalMarginalModelError("final marginal RW rows are empty")
    for row in rows:
        if set(row) != set(FINAL_MARGINAL_RW_RATIO_FIELDS):
            raise FinalMarginalModelError("final marginal RW schema mismatch")
        if row["final_rw_m_selected"] == "true":
            if not row["selected_marginal_n_bil"] or not row["selected_marginal_D_bil"]:
                raise FinalMarginalModelError("selected RW_M requires N and D")
            if SELECTED_RW_M_RWTAM_BLOCKED_USE not in row["blocked_use"]:
                raise FinalMarginalModelError("selected RW_M RWTAM comparison blocker missing")
            if row["claim_boundary"] != SELECTED_RW_M_CLAIM_BOUNDARY:
                raise FinalMarginalModelError("selected RW_M claim boundary missing")
            expected = Decimal(row["selected_marginal_n_bil"]) / Decimal(
                row["selected_marginal_D_bil"]
            )
            if Decimal(row["final_rw_m"]) != expected:
                raise FinalMarginalModelError("final RW_M identity failed")
        else:
            if row["final_rw_m"]:
                raise FinalMarginalModelError("nonselected final RW_M must be blank")
            if "selected_rw_m" not in row["blocked_use"]:
                raise FinalMarginalModelError("selected RW_M blocker missing")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _tdc_term_available_for_selected_n(row: Mapping[str, str]) -> bool:
    if (
        row.get("selected_tdc_formula_pass") == "true"
        and row.get("enters_selected_rw_m") == "true"
    ):
        return True
    return (
        row.get("selected_tdc_formula_pass") == "false"
        and row.get("enters_selected_rw_m") == "false"
        and row.get("marginal_tdc_support_bil") == "0"
        and "retired_chi_support_zero" in row.get("support_formula", "")
        and "income_addendum" in row.get("blocked_use", "")
    )


def _tdcsim_pair_dir_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(
        1
        for child in path.iterdir()
        if child.is_dir()
        and (child / "tdcsim_ratewall_marginal_tdc_pair_manifest.json").exists()
        and (child / "tdcsim_ratewall_marginal_tdc_summary.csv").exists()
    )


def _check(
    check_id: str,
    ok: bool,
    row_count: int,
    selected_row_count: int,
    required_rule: str,
    evidence: str,
    blocked_use: str,
) -> tuple[str, bool, int, int, str, str, str]:
    return (
        check_id,
        ok,
        row_count,
        selected_row_count,
        required_rule,
        evidence,
        blocked_use,
    )


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")
