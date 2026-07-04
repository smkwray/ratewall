"""Selected marginal numerator gate for RW_M."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_DENOMINATOR_PATH = Path(
    "var/preliminary_scenario_results/marginal_denominator/"
    "ratewall_marginal_denominator_surface.csv"
)
DEFAULT_PUBLIC_INTEREST_PATH = Path(
    "var/preliminary_scenario_results/marginal_public_interest/"
    "ratewall_marginal_public_interest_delta.csv"
)
DEFAULT_TDC_SUPPORT_PATH = Path(
    "var/preliminary_scenario_results/marginal_tdcsim/"
    "ratewall_marginal_tdc_support_panel.csv"
)
DEFAULT_SAFE_YIELD_PATH = Path(
    "var/preliminary_scenario_results/marginal_safe_yield/"
    "ratewall_marginal_safe_yield_delta.csv"
)
DEFAULT_ADMITTED_RESIDUAL_PATH = Path(
    "var/preliminary_scenario_results/marginal_residual/"
    "ratewall_marginal_admitted_disjoint_delta.csv"
)
DEFAULT_HISTORICAL_WINDOW_PATH = Path(
    "configs/assumption_mode/ratewall_historical_selected_window.csv"
)

MARGINAL_SELECTED_NUMERATOR_SURFACE_FIELDS = [
    "marginal_selected_numerator_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "demand_conversion_case",
    "delta_public_interest_net_block_bil",
    "marginal_tdc_support_bil",
    "delta_safe_yield_bil",
    "delta_other_admitted_disjoint_bil",
    "selected_marginal_n_bil",
    "selected_marginal_n_allowed",
    "selected_n_formula",
    "safe_yield_component_status",
    "admitted_disjoint_residual_status",
    "selection_gate_status",
    "missing_components",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_OVERLAP_AUDIT_FIELDS = [
    "marginal_overlap_audit_row_id",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "demand_conversion_case",
    "public_interest_overlap_status",
    "tdc_overlap_status",
    "safe_yield_overlap_status",
    "overall_overlap_status",
    "allowed_use",
    "blocked_use",
]


class MarginalSelectedNumeratorError(ValueError):
    """Raised when selected marginal numerator gates are unsafe."""


def marginal_selected_numerator_rows(
    *,
    denominator_path: str | Path = DEFAULT_DENOMINATOR_PATH,
    public_interest_path: str | Path = DEFAULT_PUBLIC_INTEREST_PATH,
    tdc_support_path: str | Path = DEFAULT_TDC_SUPPORT_PATH,
    safe_yield_path: str | Path = DEFAULT_SAFE_YIELD_PATH,
    admitted_residual_path: str | Path = DEFAULT_ADMITTED_RESIDUAL_PATH,
    historical_window_path: str | Path = DEFAULT_HISTORICAL_WINDOW_PATH,
) -> list[dict[str, str]]:
    denominator_rows = [
        row
        for row in _read_csv(Path(denominator_path))
        if row.get("selected_marginal_D") == "true"
    ]
    pi_by_key = _selected_public_interest_by_key(Path(public_interest_path))
    tdc_by_key = _tdc_support_by_key(Path(tdc_support_path))
    safe_yield_by_key = _safe_yield_by_key(Path(safe_yield_path))
    admitted_residual_by_key = _admitted_residual_by_key(Path(admitted_residual_path))
    historical_selected_periods = _historical_selected_periods(Path(historical_window_path))
    rows = []
    for d_row in denominator_rows:
        key = (d_row["period"], d_row["horizon"], d_row["state_id"], d_row["shock_path_id"])
        pi = pi_by_key.get(key)
        demand_case = "central"
        tdc = tdc_by_key.get((*key, demand_case))
        safe_yield = safe_yield_by_key.get(key)
        admitted_residual = admitted_residual_by_key.get(key)
        missing = []
        if pi is None:
            missing.append("public_interest_delta")
        tdc_required = d_row["period_object"] in {"current", "forecast"} or (
            d_row["period_object"] == "historical"
            and d_row["period"] in historical_selected_periods
        )
        if tdc is None and tdc_required:
            missing.append("tdc_marginal_pair")
        safe_yield_value, safe_yield_status, safe_yield_missing = _component_value(
            safe_yield,
            value_field="delta_safe_yield_bil",
            allowed_field="selected_safe_yield_delta_allowed",
            component_name="safe_yield_delta",
        )
        residual_value, residual_status, residual_missing = _component_value(
            admitted_residual,
            value_field="delta_other_admitted_disjoint_bil",
            allowed_field="selected_admitted_disjoint_delta_allowed",
            component_name="admitted_disjoint_residual_delta",
        )
        missing.extend(safe_yield_missing)
        missing.extend(residual_missing)
        allowed = not missing
        pi_value = Decimal(pi["delta_public_interest_net_block_bil"]) if pi else Decimal("0")
        tdc_value = Decimal(tdc["marginal_tdc_support_bil"]) if tdc else Decimal("0")
        n_value = pi_value + tdc_value + safe_yield_value + residual_value
        rows.append(
            {
                "marginal_selected_numerator_row_id": (
                    f"marginal_selected_numerator::{d_row['period']}::{d_row['state_id']}"
                ),
                "period_object": d_row["period_object"],
                "period": d_row["period"],
                "horizon": d_row["horizon"],
                "state_id": d_row["state_id"],
                "shock_path_id": d_row["shock_path_id"],
                "demand_conversion_case": demand_case,
                "delta_public_interest_net_block_bil": _fmt(pi_value) if pi else "",
                "marginal_tdc_support_bil": _fmt(tdc_value) if tdc else "",
                "delta_safe_yield_bil": _fmt(safe_yield_value) if safe_yield else "",
                "delta_other_admitted_disjoint_bil": _fmt(residual_value) if admitted_residual else "",
                "selected_marginal_n_bil": _fmt(n_value) if allowed else "",
                "selected_marginal_n_allowed": str(allowed).lower(),
                "selected_n_formula": (
                    "delta_public_interest_net_block_bil + marginal_tdc_support_bil + "
                    "delta_safe_yield_bil + delta_other_admitted_disjoint_bil"
                ),
                "safe_yield_component_status": safe_yield_status,
                "admitted_disjoint_residual_status": residual_status,
                "selection_gate_status": (
                    "pass_selected_marginal_n_complete"
                    if allowed
                    else "fail_closed_selected_n_incomplete"
                ),
                "missing_components": ";".join(missing),
                "allowed_use": (
                    "selected_marginal_n_surface" if allowed else "selected_n_gap_surface"
                ),
                "blocked_use": (
                    "selected_rw_m;canonical_headline_promotion"
                    if not allowed
                    else "canonical_headline_promotion_without_final_gate"
                ),
                "claim_boundary": "selected_marginal_n_requires_all_same_state_delta_components",
            }
        )
    validate_marginal_selected_numerator_rows(rows)
    return rows


def marginal_overlap_audit_rows(
    selected_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    rows = []
    for row in selected_rows:
        missing = set(filter(None, row["missing_components"].split(";")))
        rows.append(
            {
                "marginal_overlap_audit_row_id": f"marginal_overlap_audit::{row['period']}::{row['state_id']}",
                "period": row["period"],
                "horizon": row["horizon"],
                "state_id": row["state_id"],
                "shock_path_id": row["shock_path_id"],
                "demand_conversion_case": row["demand_conversion_case"],
                "public_interest_overlap_status": (
                    "pass_public_interest_delta_present"
                    if "public_interest_delta" not in missing
                    else "fail_closed_missing_public_interest_delta"
                ),
                "tdc_overlap_status": (
                    "pass_tdc_ex_overlap_pair_present"
                    if "tdc_marginal_pair" not in missing
                    else "fail_closed_missing_tdcsim_pair"
                ),
                "safe_yield_overlap_status": (
                    row["safe_yield_component_status"]
                    if "safe_yield_delta" not in missing
                    else "fail_closed_missing_safe_yield_overlap_gate"
                ),
                "overall_overlap_status": (
                    "pass" if row["selected_marginal_n_allowed"] == "true" else "fail_closed"
                ),
                "allowed_use": "marginal_overlap_audit",
                "blocked_use": (
                    "selected_rw_m" if row["selected_marginal_n_allowed"] == "false" else ""
                ),
            }
        )
    return rows


def write_marginal_selected_numerator_outputs(
    output_dir: str | Path,
    *,
    selected_rows: Sequence[Mapping[str, str]],
    overlap_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "selected_numerator_csv": out / "ratewall_marginal_selected_numerator_surface.csv",
        "overlap_audit_csv": out / "ratewall_marginal_overlap_audit.csv",
    }
    write_rows(
        paths["selected_numerator_csv"],
        [dict(row) for row in selected_rows],
        MARGINAL_SELECTED_NUMERATOR_SURFACE_FIELDS,
    )
    write_rows(
        paths["overlap_audit_csv"],
        [dict(row) for row in overlap_rows],
        MARGINAL_OVERLAP_AUDIT_FIELDS,
    )
    return paths


def validate_marginal_selected_numerator_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalSelectedNumeratorError("selected marginal numerator rows are empty")
    for row in rows:
        if set(row) != set(MARGINAL_SELECTED_NUMERATOR_SURFACE_FIELDS):
            raise MarginalSelectedNumeratorError("selected marginal numerator schema mismatch")
        if row["selected_marginal_n_allowed"] == "true":
            if row["shock_path_id"] != "plus_100bp_year":
                raise MarginalSelectedNumeratorError("selected N must use plus_100bp_year")
            if row["missing_components"]:
                raise MarginalSelectedNumeratorError("selected N cannot have missing components")
            if row["delta_safe_yield_bil"] == "":
                raise MarginalSelectedNumeratorError("selected N cannot have blank safe-yield delta")
            if row["delta_other_admitted_disjoint_bil"] == "":
                raise MarginalSelectedNumeratorError("selected N cannot have blank admitted residual delta")
        else:
            if "fail_closed" not in row["selection_gate_status"]:
                raise MarginalSelectedNumeratorError("nonselected N must fail closed")
            if "selected_rw_m" not in row["blocked_use"]:
                raise MarginalSelectedNumeratorError("selected RW_M blocker missing")


def _selected_public_interest_by_key(path: Path) -> dict[tuple[str, str, str, str], Mapping[str, str]]:
    if not path.exists():
        return {}
    rows = _read_csv(path)
    return {
        (row["period"], row["horizon"], row["state_id"], row["shock_path_id"]): row
        for row in rows
        if row.get("selected_pi_delta_allowed") == "true"
    }


def _tdc_support_by_key(path: Path) -> dict[tuple[str, str, str, str, str], Mapping[str, str]]:
    if not path.exists():
        return {}
    rows = [
        row
        for row in _read_csv(path)
        if row.get("selected_tdc_formula_pass") == "true"
        and row.get("enters_selected_rw_m") == "true"
    ]
    keyed: dict[tuple[str, str, str, str, str], Mapping[str, str]] = {}
    for row in rows:
        if row.get("state_id", "").startswith("cbo_baseline_state::") and row.get("source_grade_status") != "pass_forecast_rollforward_source_grade":
            continue
        key = (
            row.get("period", ""),
            row.get("horizon", ""),
            row.get("state_id", ""),
            row.get("shock_path_id", ""),
            row.get("demand_conversion_case", ""),
        )
        if "" in key:
            continue
        if key in keyed:
            raise MarginalSelectedNumeratorError("duplicate marginal TDC full key")
        keyed[key] = row
    return keyed


def _historical_selected_periods(path: Path) -> set[str]:
    return {
        row["period"]
        for row in _read_csv(path)
        if row.get("period")
        and row.get("selected_historical_rw_m_allowed_if_complete", "").lower() == "true"
    }


def _safe_yield_by_key(path: Path) -> dict[tuple[str, str, str, str], Mapping[str, str]]:
    rows = _read_csv(path)
    keyed: dict[tuple[str, str, str, str], Mapping[str, str]] = {}
    for row in rows:
        key = (
            row.get("period", ""),
            row.get("horizon", ""),
            row.get("state_id", ""),
            row.get("shock_path_id", ""),
        )
        if "" in key:
            continue
        if key in keyed:
            raise MarginalSelectedNumeratorError("duplicate marginal safe-yield key")
        keyed[key] = row
    return keyed


def _admitted_residual_by_key(path: Path) -> dict[tuple[str, str, str, str], Mapping[str, str]]:
    rows = _read_csv(path)
    keyed: dict[tuple[str, str, str, str], Mapping[str, str]] = {}
    for row in rows:
        key = (
            row.get("period", ""),
            row.get("horizon", ""),
            row.get("state_id", ""),
            row.get("shock_path_id", ""),
        )
        if "" in key:
            continue
        if key in keyed:
            raise MarginalSelectedNumeratorError("duplicate admitted residual key")
        keyed[key] = row
    return keyed


def _component_value(
    row: Mapping[str, str] | None,
    *,
    value_field: str,
    allowed_field: str,
    component_name: str,
) -> tuple[Decimal, str, list[str]]:
    if row is None:
        return Decimal("0"), "missing_component_row", [component_name]
    value = row.get(value_field, "")
    if value == "":
        return Decimal("0"), "missing_component_value", [component_name]
    if row.get(allowed_field) == "true":
        return Decimal(value), "pass_selected_component_delta", []
    status = row.get("selection_gate_status", "")
    if "fail_closed" in status:
        decimal_value = Decimal(value)
        if decimal_value == 0:
            return decimal_value, status, []
        return Decimal("0"), "fail_closed_nonzero_component_rejected", [component_name]
    return Decimal("0"), status or "missing_component_gate_status", [component_name]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")
