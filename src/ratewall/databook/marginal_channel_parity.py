"""Channel parity/readiness matrix for the selected marginal RateWall object."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ratewall.databook.marginal_object_ledger import COMPLETE_CHANNEL_REQUIREMENTS
from ratewall.databook.table_io import write_rows

CHANNEL_PERIOD_PARITY_FIELDS = [
    "channel_id",
    "channel_family",
    "historical_status",
    "current_status",
    "forecast_status",
    "historical_route",
    "current_route",
    "forecast_route",
    "selected_value_status",
    "selected_allowed_now",
    "exact_selection_condition",
    "fail_closed_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


def channel_period_parity_rows(
    selected_numerator_rows: Sequence[Mapping[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Return one parity row for every complete marginal channel inventory row."""

    selected_period_objects = {
        row.get("period_object", "")
        for row in selected_numerator_rows or []
        if row.get("selected_marginal_n_allowed") == "true"
    }
    rows = [
        _parity_row(dict(requirement), selected_period_objects)
        for requirement in COMPLETE_CHANNEL_REQUIREMENTS
    ]
    validate_channel_period_parity_rows(rows)
    return rows


def write_channel_period_parity_output(
    output_dir: str | Path,
    *,
    parity_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    validate_channel_period_parity_rows(parity_rows)
    path = out / "ratewall_channel_period_parity_matrix.csv"
    write_rows(path, [dict(row) for row in parity_rows], CHANNEL_PERIOD_PARITY_FIELDS)
    return {"channel_period_parity_csv": path}


def validate_channel_period_parity_rows(rows: Sequence[Mapping[str, str]]) -> None:
    if not rows:
        raise ValueError("channel parity rows are empty")
    required_ids = {row["prior_channel_id"] for row in COMPLETE_CHANNEL_REQUIREMENTS}
    observed_ids = {row.get("channel_id", "") for row in rows}
    if observed_ids != required_ids:
        raise ValueError("channel parity matrix does not cover complete inventory")
    for row in rows:
        if set(row) != set(CHANNEL_PERIOD_PARITY_FIELDS):
            raise ValueError("channel parity schema mismatch")
        if not row["exact_selection_condition"]:
            raise ValueError("channel parity row missing selection condition")
        if row["channel_id"] in {"tdc_ex_overlap_beta_chi", "conventional_demand_drag"}:
            for token in ["tdc_stock", "full_tdc_level"]:
                if token in row["blocked_use"]:
                    break
            else:
                if row["channel_id"] == "tdc_ex_overlap_beta_chi":
                    raise ValueError("TDC parity row missing full TDC blocker")


def _parity_row(
    requirement: Mapping[str, str],
    selected_period_objects: set[str],
) -> dict[str, str]:
    channel_id = requirement["prior_channel_id"]
    status = requirement["marginal_status"]
    if channel_id == "public_interest_net_block":
        current_status = _selected_or_fail("current", selected_period_objects)
        forecast_status = _selected_or_fail("forecast", selected_period_objects)
        historical_status = "fail_closed_missing_same_quarter_public_interest_delta"
        selected_allowed = "current_forecast_selected"
    elif channel_id == "tdc_ex_overlap_beta_chi":
        current_status = _selected_or_fail("current", selected_period_objects)
        forecast_status = _selected_or_fail("forecast", selected_period_objects)
        historical_status = "fail_closed_no_selected_historical_tdcsim_pair_route"
        selected_allowed = "current_forecast_selected_after_tdc_pair_gate"
    elif channel_id == "conventional_demand_drag":
        current_status = "selected_marginal_D"
        forecast_status = "selected_marginal_D"
        historical_status = "selected_marginal_D_context_not_selected_RW_M"
        selected_allowed = "selected_as_denominator_not_numerator"
    elif channel_id == "deposit_safe_yield_payer_flow":
        current_status = "selected_assumption_mode_household_npish_stock_beta_proxy"
        forecast_status = "selected_assumption_mode_household_npish_stock_beta_proxy_projected_gdp_ratio"
        historical_status = "context_fail_closed_until_same_quarter_marginal_route_exists"
        selected_allowed = "current_forecast_selected_after_d1_assumption_gate"
    elif channel_id == "mmf_tbill_realized_yield":
        current_status = "selected_admitted_disjoint_residual_private_retail_prime_mmf"
        forecast_status = "selected_admitted_disjoint_residual_private_retail_prime_mmf_projected_gdp_ratio"
        historical_status = "context_fail_closed_until_same_quarter_marginal_route_exists"
        selected_allowed = "current_forecast_selected_after_admitted_disjoint_gate"
    elif status == "included_inside_public_interest_net_block":
        current_status = "inside_selected_public_interest_block"
        forecast_status = "inside_selected_public_interest_block"
        historical_status = "context_only_until_historical_public_interest_delta_exists"
        selected_allowed = "inside_pi_only"
    elif status in {"sidecar_only", "sensitivity_only", "replacement_only"}:
        current_status = f"{status}_nonselected"
        forecast_status = f"{status}_nonselected"
        historical_status = "context_or_not_selected"
        selected_allowed = "false"
    elif status in {"diagnostic_only", "blocked_non_marginal_form"}:
        current_status = "diagnostic_only"
        forecast_status = "diagnostic_only"
        historical_status = "diagnostic_only"
        selected_allowed = "false"
    else:
        current_status = status
        forecast_status = status
        historical_status = status
        selected_allowed = "false"

    route = requirement["source_or_assumption_route"]
    return {
        "channel_id": channel_id,
        "channel_family": requirement["selected_role"],
        "historical_status": historical_status,
        "current_status": current_status,
        "forecast_status": forecast_status,
        "historical_route": _historical_route(channel_id, route),
        "current_route": route,
        "forecast_route": route,
        "selected_value_status": requirement["marginal_status"],
        "selected_allowed_now": selected_allowed,
        "exact_selection_condition": requirement["promotion_rule"],
        "fail_closed_blocker": requirement["gate_id"],
        "allowed_use": "marginal_channel_period_parity_matrix",
        "blocked_use": requirement["blocked_use"],
        "claim_boundary": requirement["claim_boundary"],
    }


def _selected_or_fail(period_object: str, selected_period_objects: set[str]) -> str:
    if period_object in selected_period_objects:
        return "selected_same_state_plus_100bp_year_delta"
    return "fail_closed_missing_selected_marginal_n"


def _historical_route(channel_id: str, route: str) -> str:
    if channel_id == "conventional_demand_drag":
        return "marginal_denominator_surface_context_for_historical_rows"
    return f"historical_context_until_same_quarter_marginal_route::{route}"
