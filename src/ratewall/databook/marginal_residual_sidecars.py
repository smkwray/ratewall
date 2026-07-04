"""Residual marginal sidecars and admitted disjoint delta gate."""

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
DEFAULT_ADMITTED_RESIDUAL_ASSUMPTIONS_PATH = Path(
    "configs/assumption_mode/ratewall_marginal_admitted_disjoint_assumptions.csv"
)
DEFAULT_RESIDUAL_SAFE_YIELD_COMPONENT_ASSUMPTIONS_PATH = Path(
    "configs/assumption_mode/ratewall_selected_residual_private_channels.csv"
)

MARGINAL_ADMITTED_DISJOINT_DELTA_FIELDS = [
    "marginal_admitted_disjoint_delta_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "delta_other_admitted_disjoint_bil",
    "selected_admitted_disjoint_delta_allowed",
    "selection_gate_status",
    "source_route_status",
    "overlap_gate",
    "demand_conversion_gate",
    "missing_gates",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

RESIDUAL_SAFE_YIELD_SIDECAR_FIELDS = [
    "residual_safe_yield_sidecar_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "channel_id",
    "stock_source_id",
    "eligible_asset_stock_bil",
    "private_asset_share",
    "marginal_yield_pass_through",
    "shock_bps_year",
    "delta_gross_residual_flow_bil",
    "final_domestic_private_recipient_share",
    "nonoverlap_factor",
    "tax_timing_leakage_share",
    "current_spend_share",
    "private_payer_drag_netting_factor",
    "delta_residual_safe_yield_support_bil",
    "source_route_status",
    "overlap_gate",
    "demand_conversion_gate",
    "selected_n_addition_allowed",
    "sidecar_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

CREDIT_INSULATION_SIDECAR_FIELDS = [
    "credit_insulation_sidecar_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "channel_id",
    "eligible_fixed_or_zero_apr_balance_bil",
    "remaining_duration_share",
    "pass_through_gap",
    "payment_sensitivity_share",
    "demand_conversion_share",
    "insulated_payment_flow_bil",
    "current_demand_support_sidecar_bil",
    "materiality_gate",
    "duration_gate",
    "wedge_gate",
    "source_route_status",
    "overlap_gate",
    "demand_conversion_gate",
    "selected_n_addition_allowed",
    "sidecar_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class MarginalResidualSidecarError(ValueError):
    """Raised when residual sidecar rows violate selection rules."""


def marginal_admitted_disjoint_delta_rows(
    *,
    denominator_path: str | Path = DEFAULT_DENOMINATOR_PATH,
    assumptions_path: str | Path = DEFAULT_ADMITTED_RESIDUAL_ASSUMPTIONS_PATH,
) -> list[dict[str, str]]:
    denominator_rows = [
        row
        for row in _read_csv(Path(denominator_path))
        if row.get("selected_marginal_D") == "true"
    ]
    assumptions = _assumptions_by_key(Path(assumptions_path))
    rows = []
    for d_row in denominator_rows:
        key = (d_row["period"], d_row["horizon"], d_row["state_id"], d_row["shock_path_id"])
        assumption = assumptions.get(key)
        if assumption is None:
            rows.append(_blocked_row(d_row, "no_admitted_disjoint_residual_assumption_row"))
        else:
            rows.append(_assumption_row(d_row, assumption))
    validate_marginal_admitted_disjoint_delta_rows(rows)
    return rows


def residual_safe_yield_sidecar_rows(
    admitted_rows: Sequence[Mapping[str, str]],
    *,
    component_assumptions_path: str | Path | None = None,
) -> list[dict[str, str]]:
    components = _residual_components_by_key(
        None if component_assumptions_path is None else Path(component_assumptions_path)
    )
    return [
        _residual_safe_yield_sidecar_row(
            row,
            components.get((row["period"], row["horizon"], row["state_id"], row["shock_path_id"])),
        )
        for row in admitted_rows
    ]


def credit_insulation_sidecar_rows(
    admitted_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    return [
        _credit_insulation_sidecar_row(row)
        for row in admitted_rows
    ]


def write_marginal_residual_sidecar_outputs(
    output_dir: str | Path,
    *,
    admitted_rows: Sequence[Mapping[str, str]],
    safe_yield_sidecar_rows: Sequence[Mapping[str, str]],
    credit_sidecar_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    validate_marginal_admitted_disjoint_delta_rows(admitted_rows)
    validate_residual_safe_yield_sidecar_rows(safe_yield_sidecar_rows)
    validate_credit_insulation_sidecar_rows(credit_sidecar_rows)
    paths = {
        "admitted_disjoint_delta_csv": out / "ratewall_marginal_admitted_disjoint_delta.csv",
        "residual_safe_yield_sidecar_csv": out / "ratewall_residual_safe_yield_sidecar.csv",
        "credit_insulation_sidecar_csv": out / "ratewall_credit_insulation_sidecar.csv",
    }
    write_rows(
        paths["admitted_disjoint_delta_csv"],
        [dict(row) for row in admitted_rows],
        MARGINAL_ADMITTED_DISJOINT_DELTA_FIELDS,
    )
    write_rows(
        paths["residual_safe_yield_sidecar_csv"],
        [dict(row) for row in safe_yield_sidecar_rows],
        RESIDUAL_SAFE_YIELD_SIDECAR_FIELDS,
    )
    write_rows(
        paths["credit_insulation_sidecar_csv"],
        [dict(row) for row in credit_sidecar_rows],
        CREDIT_INSULATION_SIDECAR_FIELDS,
    )
    return paths


def validate_marginal_admitted_disjoint_delta_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalResidualSidecarError("admitted disjoint delta rows are empty")
    for row in rows:
        if set(row) != set(MARGINAL_ADMITTED_DISJOINT_DELTA_FIELDS):
            raise MarginalResidualSidecarError("admitted disjoint delta schema mismatch")
        selected = row["selected_admitted_disjoint_delta_allowed"] == "true"
        if selected:
            if row["missing_gates"]:
                raise MarginalResidualSidecarError("selected admitted disjoint delta has missing gates")
            if row["delta_other_admitted_disjoint_bil"] == "":
                raise MarginalResidualSidecarError("selected admitted disjoint delta is blank")
        else:
            if row["delta_other_admitted_disjoint_bil"] == "":
                raise MarginalResidualSidecarError("nonselected admitted disjoint delta must be explicit zero")
            if "fail_closed" not in row["selection_gate_status"]:
                raise MarginalResidualSidecarError("nonselected admitted disjoint rows must fail closed")


def validate_residual_safe_yield_sidecar_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalResidualSidecarError("residual safe-yield sidecar rows are empty")
    for row in rows:
        if set(row) != set(RESIDUAL_SAFE_YIELD_SIDECAR_FIELDS):
            raise MarginalResidualSidecarError("residual safe-yield sidecar schema mismatch")
        gross = (
            Decimal(row["eligible_asset_stock_bil"])
            * Decimal(row["private_asset_share"])
            * Decimal(row["marginal_yield_pass_through"])
            * Decimal(row["shock_bps_year"])
            / Decimal("10000")
        )
        support = (
            gross
            * Decimal(row["final_domestic_private_recipient_share"])
            * Decimal(row["nonoverlap_factor"])
            * (Decimal("1") - Decimal(row["tax_timing_leakage_share"]))
            * Decimal(row["current_spend_share"])
            * Decimal(row["private_payer_drag_netting_factor"])
        )
        if Decimal(row["delta_gross_residual_flow_bil"]) != gross:
            raise MarginalResidualSidecarError("residual sidecar gross formula mismatch")
        if Decimal(row["delta_residual_safe_yield_support_bil"]) != support:
            raise MarginalResidualSidecarError("residual sidecar support formula mismatch")
        if row["selected_n_addition_allowed"] != "false":
            raise MarginalResidualSidecarError("residual sidecar cannot directly select N")


def validate_credit_insulation_sidecar_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalResidualSidecarError("credit sidecar rows are empty")
    for row in rows:
        if set(row) != set(CREDIT_INSULATION_SIDECAR_FIELDS):
            raise MarginalResidualSidecarError("credit sidecar schema mismatch")
        insulated = (
            Decimal(row["eligible_fixed_or_zero_apr_balance_bil"])
            * Decimal(row["remaining_duration_share"])
            * Decimal(row["pass_through_gap"])
            * Decimal(row["payment_sensitivity_share"])
        )
        support = insulated * Decimal(row["demand_conversion_share"])
        if Decimal(row["insulated_payment_flow_bil"]) != insulated:
            raise MarginalResidualSidecarError("credit sidecar payment formula mismatch")
        if Decimal(row["current_demand_support_sidecar_bil"]) != support:
            raise MarginalResidualSidecarError("credit sidecar demand formula mismatch")
        if row["selected_n_addition_allowed"] != "false":
            raise MarginalResidualSidecarError("credit sidecar cannot directly select N")


def _residual_safe_yield_sidecar_row(
    row: Mapping[str, str],
    component: Mapping[str, str] | None,
) -> dict[str, str]:
    selected_component = (
        row["selected_admitted_disjoint_delta_allowed"] == "true"
        and component is not None
        and component.get("selected_residual_channel_allowed") == "true"
    )
    stock = Decimal(component.get("eligible_asset_stock_bil", "0")) if selected_component else Decimal("0")
    private_asset_share = Decimal(component.get("private_asset_share", "0")) if selected_component else Decimal("0")
    pass_through = Decimal(component.get("marginal_yield_pass_through", "0")) if selected_component else Decimal("0")
    shock = Decimal("100")
    gross = stock * private_asset_share * pass_through * shock / Decimal("10000")
    recipient = Decimal(component.get("final_domestic_private_recipient_share", "0")) if selected_component else Decimal("0")
    nonoverlap = Decimal(component.get("nonoverlap_factor", "0")) if selected_component else Decimal("0")
    tax_leakage = Decimal(component.get("tax_timing_leakage_share", "0")) if selected_component else Decimal("0")
    spend = Decimal(component.get("current_spend_share", "0")) if selected_component else Decimal("0")
    payer_drag = Decimal(component.get("private_payer_drag_netting_factor", "1")) if selected_component else Decimal("1")
    support = gross * recipient * nonoverlap * (Decimal("1") - tax_leakage) * spend * payer_drag
    return {
        "residual_safe_yield_sidecar_row_id": (
            f"residual_safe_yield_sidecar::{row['period']}::{row['state_id']}"
        ),
        "period_object": row["period_object"],
        "period": row["period"],
        "horizon": row["horizon"],
        "state_id": row["state_id"],
        "shock_path_id": row["shock_path_id"],
        "channel_id": (
            component.get("channel_id", "residual_mmf_tbill_safe_yield")
            if selected_component
            else "residual_mmf_tbill_safe_yield"
        ),
        "stock_source_id": component.get("stock_source_id", "") if selected_component else "",
        "eligible_asset_stock_bil": _fmt(stock),
        "private_asset_share": _fmt(private_asset_share),
        "marginal_yield_pass_through": _fmt(pass_through),
        "shock_bps_year": _fmt(shock),
        "delta_gross_residual_flow_bil": _fmt(gross),
        "final_domestic_private_recipient_share": _fmt(recipient),
        "nonoverlap_factor": _fmt(nonoverlap),
        "tax_timing_leakage_share": _fmt(tax_leakage),
        "current_spend_share": _fmt(spend),
        "private_payer_drag_netting_factor": _fmt(payer_drag),
        "delta_residual_safe_yield_support_bil": _fmt(support),
        "source_route_status": row["source_route_status"],
        "overlap_gate": row["overlap_gate"],
        "demand_conversion_gate": row["demand_conversion_gate"],
        "selected_n_addition_allowed": "false",
        "sidecar_status": (
            "pass_selected_residual_private_safe_yield_component_trace"
            if selected_component
            else "sidecar_only_until_disjoint_source_overlap_and_demand_gates_pass"
        ),
        "allowed_use": "residual_safe_yield_formula_sidecar",
        "blocked_use": "selected_marginal_n_channel_addition",
        "claim_boundary": (
            component.get(
                "claim_boundary",
                "residual_safe_yield_not_selected_without_admitted_disjoint_delta_gate",
            )
            if selected_component
            else "residual_safe_yield_not_selected_without_admitted_disjoint_delta_gate"
        ),
    }


def _credit_insulation_sidecar_row(row: Mapping[str, str]) -> dict[str, str]:
    balance = Decimal("0")
    duration = Decimal("0")
    gap = Decimal("0")
    sensitivity = Decimal("0")
    demand = Decimal("0")
    insulated = balance * duration * gap * sensitivity
    support = insulated * demand
    return {
        "credit_insulation_sidecar_row_id": (
            f"credit_insulation_sidecar::{row['period']}::{row['state_id']}"
        ),
        "period_object": row["period_object"],
        "period": row["period"],
        "horizon": row["horizon"],
        "state_id": row["state_id"],
        "shock_path_id": row["shock_path_id"],
        "channel_id": "credit_insulation",
        "eligible_fixed_or_zero_apr_balance_bil": _fmt(balance),
        "remaining_duration_share": _fmt(duration),
        "pass_through_gap": _fmt(gap),
        "payment_sensitivity_share": _fmt(sensitivity),
        "demand_conversion_share": _fmt(demand),
        "insulated_payment_flow_bil": _fmt(insulated),
        "current_demand_support_sidecar_bil": _fmt(support),
        "materiality_gate": "blocked_materiality_gate",
        "duration_gate": "blocked_duration_gate",
        "wedge_gate": "blocked_wedge_gate",
        "source_route_status": row["source_route_status"],
        "overlap_gate": row["overlap_gate"],
        "demand_conversion_gate": row["demand_conversion_gate"],
        "selected_n_addition_allowed": "false",
        "sidecar_status": (
            "sidecar_only_until_stock_duration_wedge_pass_through_and_demand_gates_pass"
        ),
        "allowed_use": "credit_insulation_formula_sidecar",
        "blocked_use": "selected_marginal_n_channel_addition",
        "claim_boundary": "credit_insulation_not_selected_without_admitted_marginal_support_gate",
    }


def _assumption_row(d_row: Mapping[str, str], assumption: Mapping[str, str]) -> dict[str, str]:
    gate_map = {
        "source_route_status": assumption.get("source_route_status", ""),
        "overlap_gate": assumption.get("overlap_gate", ""),
        "demand_conversion_gate": assumption.get("demand_conversion_gate", ""),
    }
    missing = [name for name, value in gate_map.items() if not value.startswith("pass")]
    selected = assumption.get("selected_admitted_disjoint_delta_allowed") == "true" and not missing
    raw_delta = Decimal(assumption.get("delta_other_admitted_disjoint_bil") or "0")
    blocked_reason = assumption.get("blocked_reason", "")
    if selected:
        delta = raw_delta
    elif raw_delta != 0:
        delta = Decimal("0")
        missing = [*missing, "nonselected_nonzero_delta"]
        blocked_reason = "nonselected_admitted_disjoint_nonzero_assumption_rejected"
    else:
        delta = Decimal("0")
    return _base_row(
        d_row,
        selected=selected,
        delta=delta,
        source_route_status=gate_map["source_route_status"],
        overlap_gate=gate_map["overlap_gate"],
        demand_conversion_gate=gate_map["demand_conversion_gate"],
        missing_gates=missing,
        blocked_reason=blocked_reason,
    )


def _blocked_row(d_row: Mapping[str, str], reason: str) -> dict[str, str]:
    return _base_row(
        d_row,
        selected=False,
        delta=Decimal("0"),
        source_route_status=f"blocked_{reason}",
        overlap_gate="blocked_no_selected_route",
        demand_conversion_gate="blocked_no_selected_route",
        missing_gates=["source_route_status", "overlap_gate", "demand_conversion_gate"],
        blocked_reason=reason,
    )


def _base_row(
    d_row: Mapping[str, str],
    *,
    selected: bool,
    delta: Decimal,
    source_route_status: str,
    overlap_gate: str,
    demand_conversion_gate: str,
    missing_gates: Sequence[str],
    blocked_reason: str,
) -> dict[str, str]:
    return {
        "marginal_admitted_disjoint_delta_row_id": (
            f"marginal_admitted_disjoint::{d_row['period']}::{d_row['state_id']}"
        ),
        "period_object": d_row["period_object"],
        "period": d_row["period"],
        "horizon": d_row["horizon"],
        "state_id": d_row["state_id"],
        "shock_path_id": d_row["shock_path_id"],
        "delta_other_admitted_disjoint_bil": _fmt(delta),
        "selected_admitted_disjoint_delta_allowed": str(selected).lower(),
        "selection_gate_status": (
            "pass_selected_admitted_disjoint_delta"
            if selected
            else "fail_closed_named_blocker_zero"
        ),
        "source_route_status": source_route_status,
        "overlap_gate": overlap_gate,
        "demand_conversion_gate": demand_conversion_gate,
        "missing_gates": ";".join(missing_gates),
        "allowed_use": "selected_marginal_admitted_disjoint_delta" if selected else "residual_gap_surface",
        "blocked_use": "" if selected else "selected_marginal_n_channel_addition",
        "claim_boundary": (
            "admitted_disjoint_residual_enters_selected_n_only_after_source_overlap_and_demand_gates"
            if selected
            else f"admitted_disjoint_residual_explicit_zero::{blocked_reason}"
        ),
    }


def _assumptions_by_key(path: Path) -> dict[tuple[str, str, str, str], Mapping[str, str]]:
    return {
        (row.get("period", ""), row.get("horizon", ""), row.get("state_id", ""), row.get("shock_path_id", "")): row
        for row in _read_csv(path)
        if row.get("period") and row.get("horizon") and row.get("state_id") and row.get("shock_path_id")
    }


def _residual_components_by_key(
    path: Path | None,
) -> dict[tuple[str, str, str, str], Mapping[str, str]]:
    if path is None:
        return {}
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
