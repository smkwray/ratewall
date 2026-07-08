"""Fail-closed marginal numerator ledger for RW_M."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ratewall.databook.table_io import write_rows

MARGINAL_NUMERATOR_CHANNEL_LEDGER_FIELDS = [
    "marginal_numerator_channel_row_id",
    "channel_id",
    "period_scope",
    "marginal_role",
    "selected_marginal_n_allowed",
    "delta_formula",
    "required_input_artifact",
    "same_state_delta_status",
    "flow_basis_status",
    "overlap_status",
    "same_period_d_status",
    "selection_gate_status",
    "fail_closed_label",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_EXPOSURE_DIAGNOSTIC_MAP_FIELDS = [
    "marginal_exposure_diagnostic_row_id",
    "old_surface_id",
    "old_value_fields",
    "diagnostic_role",
    "selected_marginal_n_allowed",
    "required_rebuild",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class MarginalNumeratorLedgerError(ValueError):
    """Raised when the marginal numerator ledger is not fail-closed."""


def marginal_numerator_channel_rows() -> list[dict[str, str]]:
    """Return channel rows that block selected N until real marginal deltas exist."""

    rows = [
        _channel(
            "public_interest_net_block",
            "historical,current,forecast",
            "candidate_marginal_replacement",
            "PI_net_block_shock_bil - PI_net_block_baseline_bil",
            "var/preliminary_scenario_results/marginal_public_interest/ratewall_marginal_public_interest_delta.csv",
            "fail_closed_missing_same_state_public_interest_delta",
            "pass_flow_basis_required_by_builder",
            "pass_public_interest_block_xor_required_by_builder",
            "pass_selected_marginal_D_required_by_builder",
            "fail_closed_selected_n_incomplete",
            "fail_closed_selected_n_incomplete",
            "marginal_public_interest_candidate",
            "legacy_level_public_interest;standalone_direct_treasury_or_iorb_or_on_rrp;selected_marginal_n",
            "public_interest_selected_only_after_same_state_delta_and_overlap_gate",
        ),
        _channel(
            "tdc_ex_overlap_beta_chi",
            "current,forecast",
            "candidate_marginal_replacement",
            "delta_tdc_income_addendum_bil_or_fail_closed_zero",
            "var/preliminary_scenario_results/marginal_tdcsim/ratewall_marginal_tdc_support_panel.csv",
            "fail_closed_missing_tdcsim_v0p4_marginal_pair",
            "pass_tdcsim_pair_flow_basis_required_by_builder_but_chi_retired",
            "fail_closed_income_addendum_parked_direct_treasury_mmf_interest_collision",
            "pass_selected_marginal_D_required_by_builder",
            "fail_closed_selected_n_incomplete",
            "fail_closed_tdc_income_addendum_parked",
            "marginal_tdc_pair_diagnostic_income_addendum_parked",
            "full_tdc_level;observed_tdc_level;tdcsim_v0p3_output;legacy_runtime_tdc_component;selected_marginal_n;chi_support",
            "tdc_selected_only_as_income_addendum_or_fail_closed_zero_after_disjointness_gate",
        ),
        _channel(
            "deposit_safe_yield_payer_flow",
            "historical,current,forecast",
            "candidate_marginal_replacement",
            "delta_payer_flow_to_recipients_after_tax_timing_overlap_controls",
            "var/preliminary_scenario_results/marginal_safe_yield/ratewall_marginal_safe_yield_delta.csv",
            "fail_closed_missing_marginal_payer_flow_delta",
            "fail_closed_missing_recipient_tax_timing_and_current_spend_gate",
            "fail_closed_missing_safe_yield_overlap_gate",
            "pass_selected_marginal_D_required_by_builder",
            "fail_closed_selected_n_incomplete",
            "fail_closed_safe_yield_marginal_gate_missing",
            "noncentral_candidate_until_full_marginal_gate",
            "stock_rate_fallback;level_safe_yield_income;deposit_rate_level_times_stock;selected_marginal_n",
            "safe_yield_selected_only_after_extra_payer_flow_from_shock_is_identified",
        ),
        _channel(
            "other_admitted_disjoint",
            "historical,current,forecast",
            "blocked_source_or_method",
            "delta_other_admitted_disjoint_bil",
            "",
            "fail_closed_no_other_marginal_delta_admitted",
            "fail_closed_no_flow_basis",
            "fail_closed_no_overlap_proof",
            "pass_selected_marginal_D_required_by_builder",
            "fail_closed_selected_n_incomplete",
            "fail_closed_selected_n_incomplete",
            "parking_lane_only",
            "generic_mpc_scalar;stock_only_support;denominator_drag_as_numerator",
            "no_other_channel_enters_until_specific_same_state_delta_is_admitted",
        ),
    ]
    validate_marginal_numerator_channel_rows(rows)
    return rows


def marginal_exposure_diagnostic_rows() -> list[dict[str, str]]:
    """Map old exposure surfaces to diagnostic-only status."""

    rows = [
        _diagnostic(
            "current_object_bridge",
            "n_bil;d_bil;rw;legacy_runtime_tdc_component_bil",
            "diagnostic_exposure_only",
            "current_state_same_state_delta_N_required",
            "selected_current_benchmark;selected_marginal_n;selected_rw_m",
        ),
        _diagnostic(
            "forecast_central_scenario_surface",
            "central_n_bil;central_moving_denominator_bil;central_ratewall_ratio",
            "diagnostic_exposure_only",
            "forecast_same_state_delta_N_and_D_required",
            "selected_forecast_ratio;selected_marginal_n;selected_rw_m",
        ),
        _diagnostic(
            "historical_root_public_interest_rw_panel",
            "root_public_interest_n_bil;root_public_interest_ratewall_ratio",
            "historical_context_only",
            "historical_same_quarter_delta_N_required",
            "historical_classifier_as_final_ratio;selected_marginal_n;selected_rw_m",
        ),
        _diagnostic(
            "historical_denominator_convention_review",
            "selected_historical_path_D_bil;fixed_D_comparison_bil",
            "rate_environment_exposure_diagnostic",
            "fixed_D_comparison_may_feed_selected_D_only_after_audit",
            "historical_path_D_as_selected_marginal_D;denominator_drag_as_numerator;selected_rw_m",
        ),
    ]
    validate_marginal_exposure_diagnostic_rows(rows)
    return rows


def build_all() -> dict[str, list[dict[str, str]]]:
    return {
        "channel_rows": marginal_numerator_channel_rows(),
        "diagnostic_rows": marginal_exposure_diagnostic_rows(),
    }


def write_marginal_numerator_outputs(
    output_dir: str | Path,
    *,
    channel_rows: Sequence[Mapping[str, str]],
    diagnostic_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "channel_ledger_csv": out / "ratewall_marginal_numerator_channel_ledger.csv",
        "exposure_map_csv": out / "ratewall_marginal_exposure_diagnostic_map.csv",
    }
    write_rows(
        paths["channel_ledger_csv"],
        [dict(row) for row in channel_rows],
        MARGINAL_NUMERATOR_CHANNEL_LEDGER_FIELDS,
    )
    write_rows(
        paths["exposure_map_csv"],
        [dict(row) for row in diagnostic_rows],
        MARGINAL_EXPOSURE_DIAGNOSTIC_MAP_FIELDS,
    )
    return paths


def validate_marginal_numerator_channel_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalNumeratorLedgerError("marginal numerator rows are empty")
    for row in rows:
        if set(row) != set(MARGINAL_NUMERATOR_CHANNEL_LEDGER_FIELDS):
            raise MarginalNumeratorLedgerError("marginal numerator schema mismatch")
        if row["selected_marginal_n_allowed"] != "false":
            raise MarginalNumeratorLedgerError("selected marginal N must fail closed")
        if (
            row["channel_id"] == "tdc_ex_overlap_beta_chi"
            and row["delta_formula"] != "delta_tdc_income_addendum_bil_or_fail_closed_zero"
        ):
            raise MarginalNumeratorLedgerError(
                "TDC must use income addendum or fail-closed zero delta"
            )
        if not row["delta_formula"].startswith(("PI_net", "delta_", "Delta_")):
            raise MarginalNumeratorLedgerError("marginal numerator formula must be a delta")
        if "fail_closed" not in row["selection_gate_status"]:
            raise MarginalNumeratorLedgerError("selection gate must fail closed")
        if "selected_marginal_n" not in row["blocked_use"] and row["channel_id"] != "other_admitted_disjoint":
            raise MarginalNumeratorLedgerError("selected marginal N blocker missing")
    tdc = _by_id(rows, "tdc_ex_overlap_beta_chi")
    if "tdcsim_v0p3_output" not in tdc["blocked_use"]:
        raise MarginalNumeratorLedgerError("old TDCSim output blocker missing")


def validate_marginal_exposure_diagnostic_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalNumeratorLedgerError("exposure diagnostic map is empty")
    for row in rows:
        if set(row) != set(MARGINAL_EXPOSURE_DIAGNOSTIC_MAP_FIELDS):
            raise MarginalNumeratorLedgerError("exposure diagnostic schema mismatch")
        if row["selected_marginal_n_allowed"] != "false":
            raise MarginalNumeratorLedgerError("old exposure row cannot select marginal N")
        if "selected_rw_m" not in row["blocked_use"]:
            raise MarginalNumeratorLedgerError("selected RW_M blocker missing")


def _channel(
    channel_id: str,
    period_scope: str,
    marginal_role: str,
    delta_formula: str,
    required_input_artifact: str,
    same_state_delta_status: str,
    flow_basis_status: str,
    overlap_status: str,
    same_period_d_status: str,
    selection_gate_status: str,
    fail_closed_label: str,
    allowed_use: str,
    blocked_use: str,
    claim_boundary: str,
) -> dict[str, str]:
    return {
        "marginal_numerator_channel_row_id": f"marginal_numerator_channel::{channel_id}",
        "channel_id": channel_id,
        "period_scope": period_scope,
        "marginal_role": marginal_role,
        "selected_marginal_n_allowed": "false",
        "delta_formula": delta_formula,
        "required_input_artifact": required_input_artifact,
        "same_state_delta_status": same_state_delta_status,
        "flow_basis_status": flow_basis_status,
        "overlap_status": overlap_status,
        "same_period_d_status": same_period_d_status,
        "selection_gate_status": selection_gate_status,
        "fail_closed_label": fail_closed_label,
        "allowed_use": allowed_use,
        "blocked_use": blocked_use,
        "claim_boundary": claim_boundary,
    }


def _diagnostic(
    old_surface_id: str,
    old_value_fields: str,
    diagnostic_role: str,
    required_rebuild: str,
    blocked_use: str,
) -> dict[str, str]:
    return {
        "marginal_exposure_diagnostic_row_id": f"marginal_exposure::{old_surface_id}",
        "old_surface_id": old_surface_id,
        "old_value_fields": old_value_fields,
        "diagnostic_role": diagnostic_role,
        "selected_marginal_n_allowed": "false",
        "required_rebuild": required_rebuild,
        "allowed_use": "marginal_exposure_diagnostic_map",
        "blocked_use": blocked_use,
        "claim_boundary": "old_exposure_surface_reclassified_not_selected_marginal_n",
    }


def _by_id(rows: Sequence[Mapping[str, str]], row_id: str) -> Mapping[str, str]:
    for row in rows:
        if row["channel_id"] == row_id:
            return row
    raise MarginalNumeratorLedgerError(f"missing channel row: {row_id}")
