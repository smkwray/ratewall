"""Core support numerator parity surface for RateWall forecast rows."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_FORECAST_READOUT_DIR = Path("var/preliminary_scenario_results/forecast_10y")

CORE_SUPPORT_NUMERATOR_FIELDS = [
    "core_support_numerator_row_id",
    "surface_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "tdc_change_ex_overlap_bil",
    "beta_profile_id",
    "beta",
    "chi",
    "beta_times_chi",
    "tdc_current_demand_support_bil",
    "public_interest_block_id",
    "legacy_interest_support_bil",
    "public_interest_net_block_bil",
    "replacement_delta_vs_legacy_interest_support_bil",
    "core_support_n_bil",
    "central_surface_n_bil",
    "identity_error_bil",
    "selected_denominator_bil",
    "selected_ratewall_ratio",
    "direct_treasury_entry_role",
    "bank_treasury_entry_role",
    "public_interest_entry_role",
    "tdc_entry_role",
    "overlap_guard_status",
    "composition_rule",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

PUBLIC_INTEREST_NET_BLOCK_SHARED_FIELDS = [
    "public_interest_net_block_row_id",
    "surface_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "public_interest_block_id",
    "direct_treasury_current_demand_support_bil",
    "direct_treasury_entry_role",
    "bank_treasury_current_demand_support_bil",
    "bank_treasury_entry_role",
    "legacy_interest_support_bil",
    "projected_iorb_current_demand_support_bil",
    "projected_on_rrp_current_demand_support_bil",
    "projected_current_remittance_demand_offset_bil",
    "projected_future_remittance_drag_demand_offset_bil",
    "gross_public_interest_current_demand_support_bil",
    "interest_income_tax_timing_drag_bil",
    "fiscal_offset_bil",
    "tga_liquidity_offset_bil",
    "net_interest_after_fiscal_tga_offsets_bil",
    "replacement_delta_vs_legacy_interest_support_bil",
    "composition_rule",
    "overlap_guard_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

TDC_EX_OVERLAP_SUPPORT_SHARED_FIELDS = [
    "tdc_ex_overlap_support_row_id",
    "surface_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "tdc_change_ex_overlap_bil",
    "tdc_amount_basis",
    "overlap_policy",
    "beta_profile_id",
    "beta",
    "chi",
    "beta_times_chi",
    "tdc_current_demand_support_bil",
    "beta_chi_admission_status",
    "tdcsim_mmf_routing_or_offset_coefficient",
    "tdcsim_mmf_routing_role",
    "support_formula",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

CORE_SUPPORT_OVERLAP_AUDIT_FIELDS = [
    "core_support_overlap_audit_row_id",
    "check_id",
    "check_status",
    "max_abs_identity_error_bil",
    "row_count",
    "required_rule",
    "allowed_use",
    "blocked_use",
]


class CoreSupportParityError(ValueError):
    """Raised when core support parity inputs are missing or inconsistent."""


def core_support_numerator_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Join selected TDC support and public-interest net block into one surface."""

    root = Path(forecast_readout_dir)
    timed = _read_required(root / "ratewall_forecast_timed_beta_paths.csv")
    public_interest = _read_required(root / "ratewall_forecast_public_interest_net_block.csv")
    central = _read_required(root / "ratewall_forecast_central_scenario_surface.csv")
    channels = _read_required(root / "ratewall_forecast_channel_classification.csv")

    timed_by_key = {
        _key(row): row for row in timed if row["beta_path_id"] == "normal_forward_constant"
    }
    public_by_key = {_key(row): row for row in public_interest}
    role_by_channel = {row["channel_id"]: row for row in channels}
    rows: list[dict[str, str]] = []
    for central_row in central:
        key = _key(central_row)
        timed_row = _required(timed_by_key, key, "normal-forward TDC row")
        interest_row = _required(public_by_key, key, "public-interest net block row")
        tdc_support = Decimal(timed_row["tdc_current_demand_support_bil_recomputed"])
        interest_support = Decimal(interest_row["net_interest_after_fiscal_tga_offsets_bil"])
        core_n = tdc_support + interest_support
        central_n = Decimal(central_row["central_n_bil"])
        identity_error = central_n - core_n
        rows.append(
            {
                "core_support_numerator_row_id": (
                    f"core_support_numerator::forecast_central_tdcsim_cbo::"
                    f"{central_row['fiscal_year']}::{central_row['scenario_id']}"
                ),
                "surface_id": "forecast_central_tdcsim_cbo",
                "fiscal_year": central_row["fiscal_year"],
                "scenario_id": central_row["scenario_id"],
                "baseline_scenario_id": central_row["baseline_scenario_id"],
                "tdc_change_ex_overlap_bil": timed_row["tdc_change_ex_overlap_bil"],
                "beta_profile_id": timed_row["tdc_materialization_beta_scenario"],
                "beta": timed_row["tdc_materialization_beta"],
                "chi": timed_row["deposit_current_demand_share"],
                "beta_times_chi": timed_row["derived_beta_times_chi"],
                "tdc_current_demand_support_bil": _fmt(tdc_support),
                "public_interest_block_id": "public_interest_net_block::shared_v1",
                "legacy_interest_support_bil": interest_row["legacy_interest_support_bil"],
                "public_interest_net_block_bil": _fmt(interest_support),
                "replacement_delta_vs_legacy_interest_support_bil": interest_row[
                    "replacement_delta_vs_legacy_interest_support_bil"
                ],
                "core_support_n_bil": _fmt(core_n),
                "central_surface_n_bil": central_row["central_n_bil"],
                "identity_error_bil": _fmt(identity_error),
                "selected_denominator_bil": central_row["central_moving_denominator_bil"],
                "selected_ratewall_ratio": central_row["central_ratewall_ratio"],
                "direct_treasury_entry_role": _role(
                    role_by_channel,
                    "direct_treasury_interest_support",
                ),
                "bank_treasury_entry_role": _role(
                    role_by_channel,
                    "bank_treasury_interest_support",
                ),
                "public_interest_entry_role": _role(
                    role_by_channel,
                    "net_interest_after_fiscal_tga_offsets",
                ),
                "tdc_entry_role": _role(
                    role_by_channel,
                    "tdc_ex_overlap_current_demand_support",
                ),
                "overlap_guard_status": (
                    "direct_and_bank_interest_are_replacement_block_inputs_not_"
                    "standalone_selected_terms;tdc_uses_ex_overlap_basis"
                ),
                "composition_rule": (
                    "selected_central_N_equals_tdc_ex_overlap_support_plus_"
                    "public_interest_net_block"
                ),
                "allowed_use": "core_support_numerator_parity_model_surface",
                "blocked_use": (
                    "add_direct_or_bank_interest_on_top_of_public_interest_block;"
                    "tdc_full_support_basis;canonical_headline_promotion"
                ),
                "claim_boundary": "model_parity_surface_not_final_promotion",
            }
        )
    return rows


def public_interest_net_block_shared_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Expose the forecast public-interest block as a shared model object."""

    root = Path(forecast_readout_dir)
    public_interest = _read_required(root / "ratewall_forecast_public_interest_net_block.csv")
    channels = _read_required(root / "ratewall_forecast_channel_classification.csv")
    role_by_channel = {row["channel_id"]: row for row in channels}
    rows: list[dict[str, str]] = []
    for row in public_interest:
        rows.append(
            {
                "public_interest_net_block_row_id": (
                    "public_interest_net_block::shared_v1::forecast_central_tdcsim_cbo::"
                    f"{row['fiscal_year']}::{row['scenario_id']}"
                ),
                "surface_id": "forecast_central_tdcsim_cbo",
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "baseline_scenario_id": row["baseline_scenario_id"],
                "public_interest_block_id": "public_interest_net_block::shared_v1",
                "direct_treasury_current_demand_support_bil": row[
                    "direct_treasury_current_demand_support_bil"
                ],
                "direct_treasury_entry_role": _role(
                    role_by_channel,
                    "direct_treasury_interest_support",
                ),
                "bank_treasury_current_demand_support_bil": row[
                    "bank_treasury_current_demand_support_bil"
                ],
                "bank_treasury_entry_role": _role(
                    role_by_channel,
                    "bank_treasury_interest_support",
                ),
                "legacy_interest_support_bil": row["legacy_interest_support_bil"],
                "projected_iorb_current_demand_support_bil": row[
                    "projected_iorb_current_demand_support_bil"
                ],
                "projected_on_rrp_current_demand_support_bil": row[
                    "projected_on_rrp_current_demand_support_bil"
                ],
                "projected_current_remittance_demand_offset_bil": row[
                    "projected_current_remittance_demand_offset_bil"
                ],
                "projected_future_remittance_drag_demand_offset_bil": row[
                    "projected_future_remittance_drag_demand_offset_bil"
                ],
                "gross_public_interest_current_demand_support_bil": row[
                    "gross_public_interest_current_demand_support_bil"
                ],
                "interest_income_tax_timing_drag_bil": row[
                    "interest_income_tax_timing_drag_bil"
                ],
                "fiscal_offset_bil": row["fiscal_offset_bil"],
                "tga_liquidity_offset_bil": row["tga_liquidity_offset_bil"],
                "net_interest_after_fiscal_tga_offsets_bil": row[
                    "net_interest_after_fiscal_tga_offsets_bil"
                ],
                "replacement_delta_vs_legacy_interest_support_bil": row[
                    "replacement_delta_vs_legacy_interest_support_bil"
                ],
                "composition_rule": row["composition_rule"],
                "overlap_guard_status": (
                    "legacy_direct_and_bank_interest_are_inputs_not_additive_selected_terms"
                ),
                "allowed_use": "shared_public_interest_net_block_forecast_adapter",
                "blocked_use": (
                    "standalone_direct_bank_addition;tax_output;fiscal_reaction_estimate;"
                    "canonical_headline_promotion"
                ),
                "claim_boundary": "forecast_adapter_for_shared_model_object",
            }
        )
    return rows


def tdc_ex_overlap_support_shared_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Expose normal-forward TDC ex-overlap support as a shared model object."""

    root = Path(forecast_readout_dir)
    timed = _read_required(root / "ratewall_forecast_timed_beta_paths.csv")
    rows: list[dict[str, str]] = []
    for row in timed:
        if row["beta_path_id"] != "normal_forward_constant":
            continue
        rows.append(
            {
                "tdc_ex_overlap_support_row_id": (
                    "tdc_ex_overlap_support::shared_v1::forecast_central_tdcsim_cbo::"
                    f"{row['fiscal_year']}::{row['scenario_id']}"
                ),
                "surface_id": "forecast_central_tdcsim_cbo",
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "baseline_scenario_id": row["baseline_scenario_id"],
                "tdc_change_ex_overlap_bil": row["tdc_change_ex_overlap_bil"],
                "tdc_amount_basis": "tdcsim_tdc_change_ex_overlap_bil",
                "overlap_policy": "direct_interest_overlap_removed_before_beta_chi",
                "beta_profile_id": row["tdc_materialization_beta_scenario"],
                "beta": row["tdc_materialization_beta"],
                "chi": row["deposit_current_demand_share"],
                "beta_times_chi": row["derived_beta_times_chi"],
                "tdc_current_demand_support_bil": row[
                    "tdc_current_demand_support_bil_recomputed"
                ],
                "beta_chi_admission_status": (
                    "assumption_mode_beta_chi_no_direct_floor_admitted"
                ),
                "tdcsim_mmf_routing_or_offset_coefficient": "0.97",
                "tdcsim_mmf_routing_role": (
                    "holder_route_correction_not_beta_not_chi"
                ),
                "support_formula": (
                    "tdc_current_demand_support_bil="
                    "tdc_change_ex_overlap_bil*beta*chi"
                ),
                "allowed_use": "shared_tdc_ex_overlap_support_forecast_adapter",
                "blocked_use": (
                    "tdc_full_support_basis;mmf_0_97_as_beta_or_chi;"
                    "canonical_headline_promotion"
                ),
                "claim_boundary": "forecast_adapter_for_shared_model_object",
            }
        )
    return rows


def core_support_overlap_audit_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return identity and role-audit rows for the core support surface."""

    if not rows:
        raise CoreSupportParityError("core support rows are empty")
    max_abs_error = max(abs(Decimal(row["identity_error_bil"])) for row in rows)
    role_ok = all(
        row["direct_treasury_entry_role"] == "replacement_block_input_not_standalone"
        and row["bank_treasury_entry_role"] == "replacement_block_input_not_standalone"
        and row["public_interest_entry_role"] == "standalone_final_n_term"
        and row["tdc_entry_role"] == "standalone_final_n_term"
        for row in rows
    )
    return [
        {
            "core_support_overlap_audit_row_id": "core_support_overlap_audit::identity",
            "check_id": "selected_n_identity",
            "check_status": "pass" if max_abs_error == 0 else "fail",
            "max_abs_identity_error_bil": _fmt(max_abs_error),
            "row_count": str(len(rows)),
            "required_rule": (
                "central_N_equals_TDC_ex_overlap_support_plus_public_interest_net_block"
            ),
            "allowed_use": "core_support_overlap_guard",
            "blocked_use": "ignore_identity_error",
        },
        {
            "core_support_overlap_audit_row_id": "core_support_overlap_audit::roles",
            "check_id": "replacement_block_roles",
            "check_status": "pass" if role_ok else "fail",
            "max_abs_identity_error_bil": _fmt(max_abs_error),
            "row_count": str(len(rows)),
            "required_rule": (
                "direct_and_bank_interest_are_inputs;public_interest_and_tdc_are_"
                "standalone_selected_terms"
            ),
            "allowed_use": "core_support_overlap_guard",
            "blocked_use": "treat_replacement_inputs_as_selected_additive_terms",
        },
    ]


def write_core_support_parity_outputs(
    output_dir: str | Path,
    *,
    public_interest_rows: Sequence[Mapping[str, str]],
    tdc_rows: Sequence[Mapping[str, str]],
    rows: Sequence[Mapping[str, str]],
    audit_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write core support numerator parity outputs."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "public_interest_csv": out / "ratewall_public_interest_net_block_shared.csv",
        "tdc_csv": out / "ratewall_tdc_ex_overlap_support_shared.csv",
        "core_support_csv": out / "ratewall_core_support_numerator_surface.csv",
        "overlap_audit_csv": out / "ratewall_core_support_overlap_audit.csv",
    }
    write_rows(
        paths["public_interest_csv"],
        [dict(row) for row in public_interest_rows],
        PUBLIC_INTEREST_NET_BLOCK_SHARED_FIELDS,
    )
    write_rows(
        paths["tdc_csv"],
        [dict(row) for row in tdc_rows],
        TDC_EX_OVERLAP_SUPPORT_SHARED_FIELDS,
    )
    write_rows(paths["core_support_csv"], [dict(row) for row in rows], CORE_SUPPORT_NUMERATOR_FIELDS)
    write_rows(paths["overlap_audit_csv"], [dict(row) for row in audit_rows], CORE_SUPPORT_OVERLAP_AUDIT_FIELDS)
    return paths


def _key(row: Mapping[str, str]) -> tuple[str, str]:
    return (row["fiscal_year"], row["scenario_id"])


def _required(
    rows: Mapping[tuple[str, str], Mapping[str, str]],
    key: tuple[str, str],
    label: str,
) -> Mapping[str, str]:
    try:
        return rows[key]
    except KeyError as exc:
        raise CoreSupportParityError(f"missing {label} for {key}") from exc


def _role(rows: Mapping[str, Mapping[str, str]], channel_id: str) -> str:
    try:
        return rows[channel_id]["selected_central_entry_role"]
    except KeyError as exc:
        raise CoreSupportParityError(f"missing channel role for {channel_id}") from exc


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise CoreSupportParityError(f"missing required input: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _fmt(value: Decimal) -> str:
    return format(value, "f")
