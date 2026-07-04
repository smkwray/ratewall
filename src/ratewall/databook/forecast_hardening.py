"""Forecast hardening sidecars for RateWall model readouts."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.denominator_response_coefficient import (
    FRBUS_STRUCTURAL_COEFFICIENT,
    FRBUS_STRUCTURAL_PROFILE_ID,
)
from ratewall.databook.table_io import write_rows

DEFAULT_FORECAST_READOUT_DIR = Path("var/preliminary_scenario_results/forecast_10y")
DEFAULT_DENOMINATOR_PARITY_DIR = Path(
    "var/preliminary_scenario_results/denominator_parity"
)
DEFAULT_CORE_SUPPORT_DIR = Path("var/preliminary_scenario_results/core_support_parity")
DEFAULT_CBO_REVENUE_PATH = Path("data/raw/cbo/51138-2026-02-Revenue-annual_fy.csv")

FORECAST_SELECTED_D_FIELDS = [
    "forecast_selected_d_row_id",
    "surface_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "fixed_runtime_D_bil",
    "path_D_bil",
    "moving_D_bil",
    "selected_D_bil",
    "selected_denominator_variant_role",
    "rate_changing_scenario_flag",
    "scenario_rate_overlay_bp",
    "selected_D_matches_denominator_parity",
    "central_n_bil",
    "central_ratewall_ratio",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

FORECAST_ASSUMPTION_LEDGER_FIELDS = [
    "forecast_assumption_ledger_row_id",
    "assumption_id",
    "assumption_value",
    "assumption_units",
    "source_method_block_id",
    "model_role",
    "source_status",
    "formula_or_rule",
    "selected_value_change_allowed",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

FORECAST_DENOMINATOR_CD_ROBUSTNESS_FIELDS = [
    "forecast_denominator_cd_robustness_row_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "c_D_case_id",
    "c_D",
    "path_D_bil",
    "scenario_rate_overlay_bp",
    "robust_D_bil",
    "selected_D_bil",
    "delta_robust_D_vs_selected_D_bil",
    "central_n_bil",
    "robust_ratewall_ratio",
    "selected_ratewall_ratio",
    "selected_structural_benchmark_case",
    "allowed_use",
    "blocked_use",
]

FORECAST_PUBLIC_INTEREST_SENSITIVITY_FIELDS = [
    "forecast_public_interest_sensitivity_row_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "sensitivity_case_id",
    "public_interest_support_bil",
    "delta_vs_selected_net_block_bil",
    "central_n_delta_bil_allowed",
    "signed_flow_or_clipping_status",
    "composition_rule",
    "allowed_use",
    "blocked_use",
]

FORECAST_REMITTANCE_BASELINE_FIELDS = [
    "forecast_remittance_baseline_row_id",
    "fiscal_year",
    "remittance_baseline_bil",
    "source_artifact",
    "source_status",
    "period_basis",
    "scenario_delta_admitted",
    "central_n_delta_bil",
    "h41_negative_remittance_treatment",
    "tga_treatment",
    "allowed_use",
    "blocked_use",
]

FORECAST_RESIDUAL_SAFE_YIELD_LEVEL_BOUND_FIELDS = [
    "forecast_residual_safe_yield_level_bound_row_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "assumption_set",
    "household_safe_yield_capture_bil",
    "paired_deposit_mmf_net_sensitivity_bil",
    "firm_cash_attenuation_bil",
    "total_residual_sensitivity_bil",
    "level_bound_bil",
    "central_n_delta_bil_allowed",
    "admission_status",
    "overlap_guard",
    "allowed_use",
    "blocked_use",
]

FORECAST_HARDENING_AUDIT_FIELDS = [
    "forecast_hardening_audit_row_id",
    "check_id",
    "check_status",
    "row_count",
    "required_rule",
    "allowed_use",
    "blocked_use",
]


class ForecastHardeningError(ValueError):
    """Raised when forecast hardening inputs are inconsistent."""


def forecast_selected_d_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
    denominator_parity_dir: str | Path = DEFAULT_DENOMINATOR_PARITY_DIR,
) -> list[dict[str, str]]:
    """Expose the selected forecast denominator directly."""

    bridge_rows = _read_required(
        Path(denominator_parity_dir) / "ratewall_denominator_parity_bridge.csv"
    )
    central_rows = _read_required(
        Path(forecast_readout_dir) / "ratewall_forecast_central_scenario_surface.csv"
    )
    central_by_key = {_key(row): row for row in central_rows}
    out: list[dict[str, str]] = []
    for row in bridge_rows:
        central = _required(central_by_key, _key(row), "central forecast row")
        matches = Decimal(row["selected_D_bil"]) == Decimal(
            central["central_moving_denominator_bil"]
        )
        out.append(
            {
                "forecast_selected_d_row_id": (
                    f"forecast_selected_d::{row['fiscal_year']}::{row['scenario_id']}"
                ),
                "surface_id": row["surface_id"],
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "baseline_scenario_id": row["baseline_scenario_id"],
                "fixed_runtime_D_bil": row["fixed_runtime_D_bil"],
                "path_D_bil": row["path_D_bil"],
                "moving_D_bil": row["moving_D_bil"],
                "selected_D_bil": row["selected_D_bil"],
                "selected_denominator_variant_role": row[
                    "selected_denominator_variant_role"
                ],
                "rate_changing_scenario_flag": row["rate_changing_scenario_flag"],
                "scenario_rate_overlay_bp": row["scenario_rate_overlay_bp"],
                "selected_D_matches_denominator_parity": str(matches).lower(),
                "central_n_bil": central["central_n_bil"],
                "central_ratewall_ratio": central["central_ratewall_ratio"],
                "allowed_use": "forecast_selected_d_explicit_model_sidecar",
                "blocked_use": "canonical_headline_promotion;evidence_mode_claim;model_D_change",
                "claim_boundary": "forecast_hardening_sidecar_no_selected_value_change",
            }
        )
    return out


def forecast_assumption_ledger_rows() -> list[dict[str, str]]:
    """Return core forecast assumptions as explicit non-mutating ledger rows."""

    specs = [
        (
            "forecast_selected_n_rule",
            "public_interest_net_block + forecast_tdc_support",
            "billions_of_dollars",
            "forecast_public_interest_net_block;forecast_tdc_support",
            "selected_n_formula",
            "source_backed_forecast_objects",
            "central_N equals TDC ex-overlap support plus public-interest net block",
        ),
        (
            "forecast_tdc_beta",
            "0.34201759129420367",
            "share",
            "beta_chi_calibration",
            "tdc_materialization_assumption",
            "assumption_mode_no_direct_floor_admitted",
            "exact EA-TDC beta retained",
        ),
        (
            "forecast_chi",
            "0.07",
            "share",
            "beta_chi_calibration",
            "current_demand_conversion_assumption",
            "assumption_mode_no_direct_floor_admitted",
            "deposit current-demand share retained",
        ),
        (
            "tdcsim_mmf_routing",
            "0.97",
            "route_coefficient",
            "forecast_tdc_support",
            "holder_route_metadata_not_beta_chi",
            "tdcsim_route_metadata",
            "MMF routing is not beta or chi",
        ),
        (
            "forecast_selected_D_rule",
            "moving_D_for_rate_scenarios_else_path_D",
            "rule",
            "forecast_denominator",
            "selected_d_formula",
            "denominator_parity_audited",
            "fixed D is comparison-only",
        ),
        (
            "forecast_c_D_selected",
            FRBUS_STRUCTURAL_COEFFICIENT,
            "coefficient",
            "forecast_denominator",
            "structural_assumption_mode_rate_response",
            "frbus_structural_assumption_mode",
            FRBUS_STRUCTURAL_PROFILE_ID,
        ),
        (
            "remittance_scenario_delta",
            "0",
            "billions_of_dollars",
            "forecast_remittance_baseline_path",
            "baseline_context_not_scenario_delta",
            "source_to_acquire_or_context_only",
            "CBO baseline is not private demand support",
        ),
    ]
    return [
        {
            "forecast_assumption_ledger_row_id": f"forecast_assumption::{assumption_id}",
            "assumption_id": assumption_id,
            "assumption_value": value,
            "assumption_units": units,
            "source_method_block_id": block,
            "model_role": role,
            "source_status": source_status,
            "formula_or_rule": rule,
            "selected_value_change_allowed": "false",
            "allowed_use": "forecast_assumption_ledger",
            "blocked_use": "beta_prior_update;chi_prior_update;denominator_prior_update;canonical_headline_promotion",
            "claim_boundary": "forecast_hardening_sidecar_no_selected_value_change",
        }
        for assumption_id, value, units, block, role, source_status, rule in specs
    ]


def forecast_denominator_cd_robustness_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
    denominator_parity_dir: str | Path = DEFAULT_DENOMINATOR_PARITY_DIR,
) -> list[dict[str, str]]:
    """Return c_D robustness rows for fixed/path/structural denominator response."""

    bridge_rows = _read_required(
        Path(denominator_parity_dir) / "ratewall_denominator_parity_bridge.csv"
    )
    central_rows = _read_required(
        Path(forecast_readout_dir) / "ratewall_forecast_central_scenario_surface.csv"
    )
    central_by_key = {_key(row): row for row in central_rows}
    cases = [
        ("zero_no_rate_response", Decimal("0")),
        ("low_legacy_0_125", Decimal("0.125")),
        ("selected_frbus_structural", Decimal(FRBUS_STRUCTURAL_COEFFICIENT)),
    ]
    out: list[dict[str, str]] = []
    for row in bridge_rows:
        central = _required(central_by_key, _key(row), "central forecast row")
        path_d = Decimal(row["path_D_bil"])
        overlay_bp = Decimal(row["scenario_rate_overlay_bp"])
        central_n = Decimal(central["central_n_bil"])
        selected_d = Decimal(row["selected_D_bil"])
        for case_id, c_d in cases:
            robust_d = path_d * (Decimal("1") + c_d * overlay_bp / Decimal("100"))
            robust_ratio = central_n / robust_d if robust_d else Decimal("0")
            out.append(
                {
                    "forecast_denominator_cd_robustness_row_id": (
                        "forecast_denominator_cd_robustness::"
                        f"{case_id}::{row['fiscal_year']}::{row['scenario_id']}"
                    ),
                    "fiscal_year": row["fiscal_year"],
                    "scenario_id": row["scenario_id"],
                    "baseline_scenario_id": row["baseline_scenario_id"],
                    "c_D_case_id": case_id,
                    "c_D": _fmt(c_d),
                    "path_D_bil": row["path_D_bil"],
                    "scenario_rate_overlay_bp": row["scenario_rate_overlay_bp"],
                    "robust_D_bil": _fmt(robust_d),
                    "selected_D_bil": row["selected_D_bil"],
                    "delta_robust_D_vs_selected_D_bil": _fmt(robust_d - selected_d),
                    "central_n_bil": central["central_n_bil"],
                    "robust_ratewall_ratio": _fmt(robust_ratio),
                    "selected_ratewall_ratio": central["central_ratewall_ratio"],
                    "selected_structural_benchmark_case": str(
                        case_id == "selected_frbus_structural"
                    ).lower(),
                    "allowed_use": "forecast_denominator_cd_robustness_sidecar",
                    "blocked_use": "overwrite_selected_structural_benchmark;canonical_headline_promotion;evidence_mode_claim",
                }
            )
    return out


def forecast_public_interest_sensitivity_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Return public-interest net-block sensitivity rows."""

    source_rows = _read_required(
        Path(forecast_readout_dir) / "ratewall_forecast_public_interest_net_block.csv"
    )
    cases = [
        (
            "selected_net_after_tax_fiscal_tga",
            "net_interest_after_fiscal_tga_offsets_bil",
            "selected signed-flow net block",
        ),
        (
            "before_fiscal_tga_absorbers",
            "net_interest_before_fiscal_tga_offsets_bil",
            "tax timing applied; fiscal and TGA absorbers removed",
        ),
        (
            "gross_before_tax_fiscal_tga",
            "gross_public_interest_current_demand_support_bil",
            "gross signed-flow support before absorbers",
        ),
        (
            "legacy_direct_bank_only",
            "legacy_interest_support_bil",
            "legacy direct plus bank interest comparison",
        ),
    ]
    out: list[dict[str, str]] = []
    for row in source_rows:
        selected = Decimal(row["net_interest_after_fiscal_tga_offsets_bil"])
        for case_id, field, status in cases:
            value = Decimal(row[field])
            out.append(
                {
                    "forecast_public_interest_sensitivity_row_id": (
                        "forecast_public_interest_sensitivity::"
                        f"{case_id}::{row['fiscal_year']}::{row['scenario_id']}"
                    ),
                    "fiscal_year": row["fiscal_year"],
                    "scenario_id": row["scenario_id"],
                    "baseline_scenario_id": row["baseline_scenario_id"],
                    "sensitivity_case_id": case_id,
                    "public_interest_support_bil": _fmt(value),
                    "delta_vs_selected_net_block_bil": _fmt(value - selected),
                    "central_n_delta_bil_allowed": str(
                        case_id == "selected_net_after_tax_fiscal_tga"
                    ).lower(),
                    "signed_flow_or_clipping_status": (
                        status
                        + ";remittance_baseline_zero_until_clean_annual_path"
                    ),
                    "composition_rule": (
                        "sensitivity_only_selected_case_matches_central_net_block"
                    ),
                    "allowed_use": "forecast_public_interest_sensitivity_sidecar",
                    "blocked_use": "overwrite_selected_public_interest_net_block;standalone_direct_bank_addition;canonical_headline_promotion",
                }
            )
    return out


def forecast_remittance_baseline_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
    cbo_revenue_path: str | Path = DEFAULT_CBO_REVENUE_PATH,
) -> list[dict[str, str]]:
    """Return CBO remittance baseline rows, failing closed if the source is absent."""

    public_rows = _read_required(
        Path(forecast_readout_dir) / "ratewall_forecast_public_interest_net_block.csv"
    )
    years = sorted({row["fiscal_year"] for row in public_rows}, key=int)
    path = Path(cbo_revenue_path)
    remittance_by_year, source_status = _cbo_remittance_baseline_by_year(path)
    return [
        {
            "forecast_remittance_baseline_row_id": (
                f"forecast_remittance_baseline::{year}"
            ),
            "fiscal_year": year,
            "remittance_baseline_bil": remittance_by_year.get(year, ""),
            "source_artifact": str(path),
            "source_status": source_status,
            "period_basis": "fiscal_year",
            "scenario_delta_admitted": "false",
            "central_n_delta_bil": "0",
            "h41_negative_remittance_treatment": (
                "deferred_asset_state_not_positive_private_demand_support"
            ),
            "tga_treatment": "separate_state_context_lane",
            "allowed_use": "forecast_remittance_baseline_context",
            "blocked_use": "scenario_delta_without_fed_earnings_model;private_demand_support_conversion;canonical_headline_promotion",
        }
        for year in years
    ]


def forecast_residual_safe_yield_level_bound_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Return noncentral residual safe-yield/MMF level-bound rows."""

    residual_rows = _read_required(
        Path(forecast_readout_dir) / "ratewall_forecast_residual_numerator_sensitivity.csv"
    )
    out: list[dict[str, str]] = []
    for row in residual_rows:
        safe = Decimal(row["household_safe_yield_capture_bil"])
        paired = Decimal(row["paired_deposit_mmf_net_sensitivity_bil"])
        firm_cash = Decimal(row["firm_cash_attenuation_bil"])
        level_bound = safe + paired + firm_cash
        out.append(
            {
                "forecast_residual_safe_yield_level_bound_row_id": (
                    "forecast_residual_safe_yield_level_bound::"
                    f"{row['assumption_set']}::{row['fiscal_year']}::{row['scenario_id']}"
                ),
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "baseline_scenario_id": row["baseline_scenario_id"],
                "assumption_set": row["assumption_set"],
                "household_safe_yield_capture_bil": row[
                    "household_safe_yield_capture_bil"
                ],
                "paired_deposit_mmf_net_sensitivity_bil": row[
                    "paired_deposit_mmf_net_sensitivity_bil"
                ],
                "firm_cash_attenuation_bil": row["firm_cash_attenuation_bil"],
                "total_residual_sensitivity_bil": row[
                    "total_residual_sensitivity_bil"
                ],
                "level_bound_bil": _fmt(level_bound),
                "central_n_delta_bil_allowed": "false",
                "admission_status": "noncentral_level_bound_context_only",
                "overlap_guard": (
                    "not_added_to_forecast_central_N;avoid_public_interest_tdc_moving_D_overlap"
                ),
                "allowed_use": "forecast_residual_safe_yield_level_bound_sidecar",
                "blocked_use": "add_to_forecast_central_N;raw_stock_times_mpc;canonical_headline_promotion",
            }
        )
    return out


def forecast_hardening_audit_rows(
    *,
    selected_d_rows: Sequence[Mapping[str, str]],
    cd_rows: Sequence[Mapping[str, str]],
    remittance_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return minimal hardening audits."""

    selected_ok = all(
        row["selected_D_matches_denominator_parity"] == "true"
        for row in selected_d_rows
    )
    cd_case_ids = {row["c_D_case_id"] for row in cd_rows}
    remittance_ok = all(
        row["scenario_delta_admitted"] == "false"
        and row["central_n_delta_bil"] == "0"
        for row in remittance_rows
    )
    return [
        _audit(
            "selected_D_matches_denominator_parity",
            selected_ok,
            len(selected_d_rows),
            "all selected-D rows match denominator parity selected_D",
        ),
        _audit(
            "cd_robustness_cases_present",
            cd_case_ids
            == {
                "zero_no_rate_response",
                "low_legacy_0_125",
                "selected_frbus_structural",
            },
            len(cd_rows),
            "c_D robustness includes 0, 0.125, and selected FRB structural",
        ),
        _audit(
            "remittance_baseline_context_only",
            remittance_ok,
            len(remittance_rows),
            "remittance baseline rows have no scenario delta and no central N effect",
        ),
    ]


def write_forecast_hardening_outputs(
    output_dir: str | Path,
    *,
    selected_d_rows: Sequence[Mapping[str, str]],
    assumption_rows: Sequence[Mapping[str, str]],
    cd_rows: Sequence[Mapping[str, str]],
    public_interest_rows: Sequence[Mapping[str, str]],
    remittance_rows: Sequence[Mapping[str, str]],
    residual_rows: Sequence[Mapping[str, str]],
    audit_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write forecast hardening sidecar outputs."""

    root = Path(output_dir)
    outputs = {
        "selected_d_csv": root / "ratewall_forecast_selected_d_surface.csv",
        "assumption_ledger_csv": root / "ratewall_forecast_central_assumption_ledger.csv",
        "cd_robustness_csv": root / "ratewall_forecast_denominator_cd_robustness.csv",
        "public_interest_sensitivity_csv": root
        / "ratewall_forecast_public_interest_sensitivity.csv",
        "remittance_baseline_csv": root / "ratewall_forecast_remittance_baseline_path.csv",
        "residual_safe_yield_bound_csv": root
        / "ratewall_forecast_residual_safe_yield_level_bound.csv",
        "audit_csv": root / "ratewall_forecast_hardening_audit.csv",
    }
    write_rows(outputs["selected_d_csv"], list(selected_d_rows), FORECAST_SELECTED_D_FIELDS)
    write_rows(
        outputs["assumption_ledger_csv"],
        list(assumption_rows),
        FORECAST_ASSUMPTION_LEDGER_FIELDS,
    )
    write_rows(
        outputs["cd_robustness_csv"],
        list(cd_rows),
        FORECAST_DENOMINATOR_CD_ROBUSTNESS_FIELDS,
    )
    write_rows(
        outputs["public_interest_sensitivity_csv"],
        list(public_interest_rows),
        FORECAST_PUBLIC_INTEREST_SENSITIVITY_FIELDS,
    )
    write_rows(
        outputs["remittance_baseline_csv"],
        list(remittance_rows),
        FORECAST_REMITTANCE_BASELINE_FIELDS,
    )
    write_rows(
        outputs["residual_safe_yield_bound_csv"],
        list(residual_rows),
        FORECAST_RESIDUAL_SAFE_YIELD_LEVEL_BOUND_FIELDS,
    )
    write_rows(outputs["audit_csv"], list(audit_rows), FORECAST_HARDENING_AUDIT_FIELDS)
    return outputs


def _audit(
    check_id: str,
    passed: bool,
    row_count: int,
    required_rule: str,
) -> dict[str, str]:
    return {
        "forecast_hardening_audit_row_id": f"forecast_hardening_audit::{check_id}",
        "check_id": check_id,
        "check_status": "pass" if passed else "fail",
        "row_count": str(row_count),
        "required_rule": required_rule,
        "allowed_use": "forecast_hardening_audit",
        "blocked_use": "canonical_headline_promotion;evidence_mode_claim",
    }


def _key(row: Mapping[str, str]) -> tuple[str, str]:
    return row["fiscal_year"], row["scenario_id"]


def _required(
    mapping: Mapping[tuple[str, str], Mapping[str, str]],
    key: tuple[str, str],
    label: str,
) -> Mapping[str, str]:
    try:
        return mapping[key]
    except KeyError as exc:
        raise ForecastHardeningError(f"missing {label}: {key}") from exc


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ForecastHardeningError(f"missing required input: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _cbo_remittance_baseline_by_year(path: Path) -> tuple[dict[str, str], str]:
    if not path.exists():
        return {}, "source_to_acquire_cbo_revenue_open_data_csv_missing"
    if path.suffix.lower() != ".csv":
        return {}, "source_present_but_extraction_not_implemented"
    rows = _read_required(path)
    remittances: dict[str, str] = {}
    for row in rows:
        if row.get("variable") != "rev_fed_reserve":
            continue
        fiscal_year = row.get("date", "")
        if fiscal_year.startswith("FY") and row.get("value", "") != "":
            remittances[fiscal_year.removeprefix("FY")] = row["value"]
    if not remittances:
        return {}, "source_present_cbo_open_data_csv_missing_rev_fed_reserve"
    return remittances, "source_present_cbo_open_data_csv_rev_fed_reserve_extracted"
