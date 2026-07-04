"""Marginal D1 safe-yield delta surface."""

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
DEFAULT_D1_ADMISSION_PATH = Path(
    "var/preliminary_scenario_results/realized_safe_yield_income/"
    "ratewall_realized_safe_yield_payer_flow_admission.csv"
)
DEFAULT_FORECAST_ASSUMPTIONS_PATH = Path(
    "configs/assumption_mode/ratewall_deposit_safe_yield_forecast_assumptions.csv"
)

MARGINAL_SAFE_YIELD_DELTA_FIELDS = [
    "marginal_safe_yield_delta_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "shock_bps_year",
    "source_mode",
    "eligible_deposit_stock_bil",
    "current_candidate_gross_flow_bil",
    "marginal_deposit_beta",
    "recipient_share",
    "coverage_alignment_factor",
    "nonoverlap_factor",
    "tax_timing_leakage_share",
    "household_safe_yield_current_spend_share",
    "delta_gross_deposit_payer_flow_bil",
    "delta_safe_yield_bil",
    "selected_safe_yield_delta_allowed",
    "selection_gate_status",
    "source_panel_gate",
    "recipient_allocation_gate",
    "denominator_alignment_gate",
    "tax_timing_gate",
    "demand_conversion_gate",
    "overlap_gate",
    "owner_gate",
    "missing_gates",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_SAFE_YIELD_OVERLAP_AUDIT_FIELDS = [
    "marginal_safe_yield_overlap_audit_row_id",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "selected_safe_yield_delta_allowed",
    "overlap_gate",
    "nonoverlap_factor",
    "overlap_audit_status",
    "allowed_use",
    "blocked_use",
]


class MarginalSafeYieldError(ValueError):
    """Raised when marginal safe-yield rows violate selection rules."""


def marginal_safe_yield_delta_rows(
    *,
    denominator_path: str | Path = DEFAULT_DENOMINATOR_PATH,
    d1_admission_path: str | Path = DEFAULT_D1_ADMISSION_PATH,
    forecast_assumptions_path: str | Path = DEFAULT_FORECAST_ASSUMPTIONS_PATH,
) -> list[dict[str, str]]:
    denominator_rows = [
        row
        for row in _read_csv(Path(denominator_path))
        if row.get("selected_marginal_D") == "true"
    ]
    current_admission = _current_admission_row(Path(d1_admission_path))
    assumptions_by_key = _forecast_assumptions_by_key(Path(forecast_assumptions_path))
    rows: list[dict[str, str]] = []
    for d_row in denominator_rows:
        key = (d_row["period"], d_row["horizon"], d_row["state_id"], d_row["shock_path_id"])
        if d_row["period_object"] == "current":
            assumption = assumptions_by_key.get(key)
            if assumption and assumption.get("selected_safe_yield_delta_allowed") == "true":
                rows.append(
                    _assumption_row(
                        d_row,
                        assumption,
                        source_mode="current_assumption_mode_d1_household_npish_stock_beta_proxy",
                        blocked_reason_if_missing="current_safe_yield_assumption_row_missing",
                    )
                )
            else:
                rows.append(_current_row(d_row, current_admission))
        elif d_row["period_object"] == "forecast":
            rows.append(
                _assumption_row(
                    d_row,
                    assumptions_by_key.get(key),
                    source_mode="forecast_assumption_mode",
                    blocked_reason_if_missing="forecast_safe_yield_assumption_row_missing",
                )
            )
        else:
            rows.append(_not_routed_row(d_row, "historical_safe_yield_marginal_route_not_selected"))
    validate_marginal_safe_yield_delta_rows(rows)
    return rows


def marginal_safe_yield_overlap_audit_rows(
    delta_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    rows = []
    for row in delta_rows:
        selected = row["selected_safe_yield_delta_allowed"] == "true"
        rows.append(
            {
                "marginal_safe_yield_overlap_audit_row_id": (
                    f"marginal_safe_yield_overlap::{row['period']}::{row['state_id']}"
                ),
                "period": row["period"],
                "horizon": row["horizon"],
                "state_id": row["state_id"],
                "shock_path_id": row["shock_path_id"],
                "selected_safe_yield_delta_allowed": row["selected_safe_yield_delta_allowed"],
                "overlap_gate": row["overlap_gate"],
                "nonoverlap_factor": row["nonoverlap_factor"],
                "overlap_audit_status": (
                    "pass_selected_nonoverlap_applied"
                    if selected
                    else "fail_closed_no_selected_safe_yield_overlap_claim"
                ),
                "allowed_use": "marginal_safe_yield_overlap_audit",
                "blocked_use": "" if selected else "selected_safe_yield_delta_without_overlap_gate",
            }
        )
    return rows


def write_marginal_safe_yield_outputs(
    output_dir: str | Path,
    *,
    delta_rows: Sequence[Mapping[str, str]],
    overlap_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "safe_yield_delta_csv": out / "ratewall_marginal_safe_yield_delta.csv",
        "safe_yield_overlap_audit_csv": out / "ratewall_marginal_safe_yield_overlap_audit.csv",
    }
    write_rows(
        paths["safe_yield_delta_csv"],
        [dict(row) for row in delta_rows],
        MARGINAL_SAFE_YIELD_DELTA_FIELDS,
    )
    write_rows(
        paths["safe_yield_overlap_audit_csv"],
        [dict(row) for row in overlap_rows],
        MARGINAL_SAFE_YIELD_OVERLAP_AUDIT_FIELDS,
    )
    return paths


def validate_marginal_safe_yield_delta_rows(rows: Sequence[Mapping[str, str]]) -> None:
    if not rows:
        raise MarginalSafeYieldError("marginal safe-yield rows are empty")
    for row in rows:
        if set(row) != set(MARGINAL_SAFE_YIELD_DELTA_FIELDS):
            raise MarginalSafeYieldError("marginal safe-yield schema mismatch")
        selected = row["selected_safe_yield_delta_allowed"] == "true"
        if selected:
            if row["shock_path_id"] != "plus_100bp_year":
                raise MarginalSafeYieldError("selected safe-yield delta must use plus_100bp_year")
            if row["missing_gates"]:
                raise MarginalSafeYieldError("selected safe-yield delta has missing gates")
            if row["delta_safe_yield_bil"] == "":
                raise MarginalSafeYieldError("selected safe-yield delta is blank")
        else:
            if row["delta_safe_yield_bil"] == "":
                raise MarginalSafeYieldError("nonselected safe-yield delta must be explicit zero")
            if "fail_closed" not in row["selection_gate_status"]:
                raise MarginalSafeYieldError("nonselected safe-yield rows must fail closed")


def _current_row(d_row: Mapping[str, str], admission: Mapping[str, str] | None) -> dict[str, str]:
    if admission is None:
        return _not_routed_row(d_row, "current_d1_admission_row_missing")
    gate_map = {
        "source_panel_gate": admission.get("period_cashflow_gate", ""),
        "recipient_allocation_gate": admission.get("recipient_allocation_gate", ""),
        "denominator_alignment_gate": admission.get("denominator_alignment_gate", ""),
        "tax_timing_gate": admission.get("tax_timing_gate", ""),
        "demand_conversion_gate": admission.get("demand_conversion_gate", ""),
        "overlap_gate": admission.get("overlap_gate", ""),
        "owner_gate": admission.get("owner_gate", ""),
    }
    missing = _missing_gates(gate_map)
    selected = (
        admission.get("all_required_gates_pass") == "true"
        and admission.get("central_n_delta_bil_allowed") == "true"
        and not missing
    )
    delta = Decimal(admission.get("central_n_delta_bil") or "0") if selected else Decimal("0")
    return _base_row(
        d_row,
        source_mode="current_d1_admission",
        selected=selected,
        delta_safe_yield_bil=delta,
        gate_map=gate_map,
        missing_gates=missing,
        eligible_deposit_stock_bil="",
        current_candidate_gross_flow_bil=admission.get("candidate_gross_flow_bil", ""),
        marginal_deposit_beta="",
        recipient_share="",
        coverage_alignment_factor="",
        nonoverlap_factor="",
        tax_timing_leakage_share="",
        household_safe_yield_current_spend_share="",
        delta_gross_deposit_payer_flow_bil="",
        blocked_reason=admission.get("blocked_reason", ""),
    )


def _assumption_row(
    d_row: Mapping[str, str],
    assumption: Mapping[str, str] | None,
    *,
    source_mode: str,
    blocked_reason_if_missing: str,
) -> dict[str, str]:
    if assumption is None:
        return _not_routed_row(d_row, blocked_reason_if_missing)
    gate_map = {
        "source_panel_gate": assumption.get("source_panel_gate", ""),
        "recipient_allocation_gate": assumption.get("recipient_allocation_gate", ""),
        "denominator_alignment_gate": assumption.get("denominator_alignment_gate", ""),
        "tax_timing_gate": assumption.get("tax_timing_gate", ""),
        "demand_conversion_gate": assumption.get("demand_conversion_gate", ""),
        "overlap_gate": assumption.get("overlap_gate", ""),
        "owner_gate": assumption.get("owner_gate", ""),
    }
    missing = _missing_gates(gate_map)
    selected = assumption.get("selected_safe_yield_delta_allowed") == "true" and not missing
    shock = Decimal(d_row.get("shock_bps_year") or "0") / Decimal("10000")
    stock = Decimal(assumption.get("eligible_deposit_stock_bil") or "0")
    beta = Decimal(assumption.get("marginal_deposit_beta") or "0")
    recipient = Decimal(assumption.get("recipient_share") or "0")
    coverage = Decimal(assumption.get("coverage_alignment_factor") or "0")
    nonoverlap = Decimal(assumption.get("nonoverlap_factor") or "0")
    leakage = Decimal(assumption.get("tax_timing_leakage_share") or "0")
    spend = Decimal(assumption.get("household_safe_yield_current_spend_share") or "0")
    gross = stock * beta * shock
    delta = gross * recipient * coverage * nonoverlap * (Decimal("1") - leakage) * spend
    return _base_row(
        d_row,
        source_mode=source_mode,
        selected=selected,
        delta_safe_yield_bil=delta if selected else Decimal("0"),
        gate_map=gate_map,
        missing_gates=missing,
        eligible_deposit_stock_bil=assumption.get("eligible_deposit_stock_bil", ""),
        current_candidate_gross_flow_bil="",
        marginal_deposit_beta=assumption.get("marginal_deposit_beta", ""),
        recipient_share=assumption.get("recipient_share", ""),
        coverage_alignment_factor=assumption.get("coverage_alignment_factor", ""),
        nonoverlap_factor=assumption.get("nonoverlap_factor", ""),
        tax_timing_leakage_share=assumption.get("tax_timing_leakage_share", ""),
        household_safe_yield_current_spend_share=assumption.get(
            "household_safe_yield_current_spend_share", ""
        ),
        delta_gross_deposit_payer_flow_bil=_fmt(gross),
        blocked_reason=assumption.get("blocked_reason", ""),
    )


def _not_routed_row(d_row: Mapping[str, str], reason: str) -> dict[str, str]:
    gate_map = {
        "source_panel_gate": f"blocked_{reason}",
        "recipient_allocation_gate": "blocked_no_selected_route",
        "denominator_alignment_gate": "blocked_no_selected_route",
        "tax_timing_gate": "blocked_no_selected_route",
        "demand_conversion_gate": "blocked_no_selected_route",
        "overlap_gate": "blocked_no_selected_route",
        "owner_gate": "blocked_no_selected_route",
    }
    return _base_row(
        d_row,
        source_mode="not_selected",
        selected=False,
        delta_safe_yield_bil=Decimal("0"),
        gate_map=gate_map,
        missing_gates=_missing_gates(gate_map),
        eligible_deposit_stock_bil="",
        current_candidate_gross_flow_bil="",
        marginal_deposit_beta="",
        recipient_share="",
        coverage_alignment_factor="",
        nonoverlap_factor="",
        tax_timing_leakage_share="",
        household_safe_yield_current_spend_share="",
        delta_gross_deposit_payer_flow_bil="",
        blocked_reason=reason,
    )


def _base_row(
    d_row: Mapping[str, str],
    *,
    source_mode: str,
    selected: bool,
    delta_safe_yield_bil: Decimal,
    gate_map: Mapping[str, str],
    missing_gates: Sequence[str],
    eligible_deposit_stock_bil: str,
    current_candidate_gross_flow_bil: str,
    marginal_deposit_beta: str,
    recipient_share: str,
    coverage_alignment_factor: str,
    nonoverlap_factor: str,
    tax_timing_leakage_share: str,
    household_safe_yield_current_spend_share: str,
    delta_gross_deposit_payer_flow_bil: str,
    blocked_reason: str,
) -> dict[str, str]:
    status = "pass_selected_marginal_safe_yield_delta" if selected else "fail_closed_named_blocker_zero"
    return {
        "marginal_safe_yield_delta_row_id": f"marginal_safe_yield::{d_row['period']}::{d_row['state_id']}",
        "period_object": d_row["period_object"],
        "period": d_row["period"],
        "horizon": d_row["horizon"],
        "state_id": d_row["state_id"],
        "shock_path_id": d_row["shock_path_id"],
        "shock_bps_year": d_row.get("shock_bps_year", ""),
        "source_mode": source_mode,
        "eligible_deposit_stock_bil": eligible_deposit_stock_bil,
        "current_candidate_gross_flow_bil": current_candidate_gross_flow_bil,
        "marginal_deposit_beta": marginal_deposit_beta,
        "recipient_share": recipient_share,
        "coverage_alignment_factor": coverage_alignment_factor,
        "nonoverlap_factor": nonoverlap_factor,
        "tax_timing_leakage_share": tax_timing_leakage_share,
        "household_safe_yield_current_spend_share": household_safe_yield_current_spend_share,
        "delta_gross_deposit_payer_flow_bil": delta_gross_deposit_payer_flow_bil,
        "delta_safe_yield_bil": _fmt(delta_safe_yield_bil),
        "selected_safe_yield_delta_allowed": str(selected).lower(),
        "selection_gate_status": status,
        "source_panel_gate": gate_map["source_panel_gate"],
        "recipient_allocation_gate": gate_map["recipient_allocation_gate"],
        "denominator_alignment_gate": gate_map["denominator_alignment_gate"],
        "tax_timing_gate": gate_map["tax_timing_gate"],
        "demand_conversion_gate": gate_map["demand_conversion_gate"],
        "overlap_gate": gate_map["overlap_gate"],
        "owner_gate": gate_map["owner_gate"],
        "missing_gates": ";".join(missing_gates) if missing_gates else "",
        "allowed_use": "selected_marginal_safe_yield_delta" if selected else "safe_yield_gap_surface",
        "blocked_use": "" if selected else "selected_marginal_n_channel_addition",
        "claim_boundary": (
            "safe_yield_enters_selected_n_only_as_same_state_marginal_delta_after_all_gates"
            if selected
            else f"safe_yield_explicit_zero_until_gates_pass::{blocked_reason}"
        ),
    }


def _missing_gates(gate_map: Mapping[str, str]) -> list[str]:
    return [name for name, value in gate_map.items() if not value.startswith("pass")]


def _current_admission_row(path: Path) -> Mapping[str, str] | None:
    rows = [
        row
        for row in _read_csv(path)
        if row.get("candidate_family") == "deposit_interest_payer_flow"
    ]
    return rows[0] if rows else None


def _forecast_assumptions_by_key(path: Path) -> dict[tuple[str, str, str, str], Mapping[str, str]]:
    return {
        (row.get("period", ""), row.get("horizon", ""), row.get("state_id", ""), row.get("shock_path_id", "")): row
        for row in _read_csv(path)
        if row.get("period") and row.get("horizon") and row.get("state_id") and row.get("shock_path_id")
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")
