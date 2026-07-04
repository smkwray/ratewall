"""Denominator comparability bridge for RateWall forecast surfaces."""

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

DENOMINATOR_PARITY_BRIDGE_FIELDS = [
    "denominator_parity_bridge_row_id",
    "surface_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "fixed_runtime_D_bil",
    "path_D_bil",
    "moving_D_bil",
    "selected_D_bil",
    "delta_path_D_vs_fixed_bil",
    "delta_moving_D_vs_path_bil",
    "delta_selected_D_vs_baseline_bil",
    "scenario_rate_overlay_bp",
    "rate_changing_scenario_flag",
    "c_D_object_id",
    "c_D",
    "denominator_rule",
    "selected_denominator_variant_role",
    "path_denominator_status",
    "moving_denominator_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DENOMINATOR_VARIANT_SURFACE_FIELDS = [
    "denominator_variant_surface_row_id",
    "surface_id",
    "fiscal_year",
    "scenario_id",
    "denominator_variant",
    "denominator_value_bil",
    "delta_denominator_vs_path_bil",
    "selected_variant",
    "variant_role",
    "allowed_use",
    "blocked_use",
]

DENOMINATOR_SCENARIO_DELTA_AUDIT_FIELDS = [
    "denominator_scenario_delta_audit_row_id",
    "check_id",
    "check_status",
    "row_count",
    "rate_changing_row_count",
    "nonrate_row_count",
    "required_rule",
    "allowed_use",
    "blocked_use",
]


class DenominatorParityError(ValueError):
    """Raised when denominator parity rows cannot be built safely."""


def denominator_parity_bridge_rows(
    *,
    forecast_readout_dir: str | Path = DEFAULT_FORECAST_READOUT_DIR,
) -> list[dict[str, str]]:
    """Build fixed/path/moving/selected D rows for the central forecast surface."""

    root = Path(forecast_readout_dir)
    central_rows = _read_required(root / "ratewall_forecast_central_scenario_surface.csv")
    path_d_by_year = _baseline_path_d_by_year(central_rows)
    fixed_d = path_d_by_year[min(path_d_by_year, key=int)]
    out: list[dict[str, str]] = []
    c_d = Decimal(FRBUS_STRUCTURAL_COEFFICIENT)
    for row in central_rows:
        fiscal_year = row["fiscal_year"]
        path_d = path_d_by_year[fiscal_year]
        moving_d = Decimal(row["central_moving_denominator_bil"])
        delta_moving = moving_d - path_d
        rate_changing = delta_moving != 0
        selected_d = moving_d if rate_changing else path_d
        rate_overlay = (
            delta_moving / (path_d * c_d) * Decimal("100")
            if path_d != 0 and c_d != 0
            else Decimal("0")
        )
        out.append(
            {
                "denominator_parity_bridge_row_id": (
                    "denominator_parity_bridge::forecast_central_tdcsim_cbo::"
                    f"{fiscal_year}::{row['scenario_id']}"
                ),
                "surface_id": "forecast_central_tdcsim_cbo",
                "fiscal_year": fiscal_year,
                "scenario_id": row["scenario_id"],
                "baseline_scenario_id": row["baseline_scenario_id"],
                "fixed_runtime_D_bil": _fmt(fixed_d),
                "path_D_bil": _fmt(path_d),
                "moving_D_bil": _fmt(moving_d),
                "selected_D_bil": _fmt(selected_d),
                "delta_path_D_vs_fixed_bil": _fmt(path_d - fixed_d),
                "delta_moving_D_vs_path_bil": _fmt(delta_moving),
                "delta_selected_D_vs_baseline_bil": _fmt(selected_d - path_d),
                "scenario_rate_overlay_bp": _fmt(rate_overlay),
                "rate_changing_scenario_flag": str(rate_changing).lower(),
                "c_D_object_id": FRBUS_STRUCTURAL_PROFILE_ID,
                "c_D": FRBUS_STRUCTURAL_COEFFICIENT,
                "denominator_rule": (
                    "fixed_D_is_reference;path_D_is_cbo_gdp_scaled_anchor;"
                    "moving_D_applies_frbus_structural_c_D_to_rate_scenarios"
                ),
                "selected_denominator_variant_role": (
                    "selected_moving_D_for_rate_changing_forecast_scenario"
                    if rate_changing
                    else "selected_path_D_for_nonrate_forecast_scenario"
                ),
                "path_denominator_status": "cbo_gdp_scaled_path_from_fy2027_anchor",
                "moving_denominator_status": (
                    "frbus_structural_moving_D_applied"
                    if rate_changing
                    else "no_rate_overlay_path_D_equals_moving_D"
                ),
                "allowed_use": "denominator_comparability_bridge",
                "blocked_use": (
                    "fixed_D_selected_for_rate_changing_forecast_scenario;"
                    "canonical_headline_promotion;evidence_mode_claim"
                ),
                "claim_boundary": "model_parity_surface_not_final_promotion",
            }
        )
    return sorted(out, key=lambda r: (int(r["fiscal_year"]), r["scenario_id"]))


def denominator_variant_surface_rows(
    bridge_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Explode bridge rows into fixed/path/moving denominator variants."""

    out: list[dict[str, str]] = []
    for row in bridge_rows:
        selected = row["selected_denominator_variant_role"]
        for variant, field, role in [
            ("fixed_D", "fixed_runtime_D_bil", "comparison_only_fixed_reference"),
            ("path_D", "path_D_bil", "cbo_gdp_scaled_path_reference"),
            ("moving_D", "moving_D_bil", "rate_response_variant"),
        ]:
            is_selected = (
                (variant == "moving_D" and selected.startswith("selected_moving"))
                or (variant == "path_D" and selected.startswith("selected_path"))
            )
            out.append(
                {
                    "denominator_variant_surface_row_id": (
                        f"denominator_variant::{variant}::"
                        f"{row['fiscal_year']}::{row['scenario_id']}"
                    ),
                    "surface_id": row["surface_id"],
                    "fiscal_year": row["fiscal_year"],
                    "scenario_id": row["scenario_id"],
                    "denominator_variant": variant,
                    "denominator_value_bil": row[field],
                    "delta_denominator_vs_path_bil": _fmt(
                        Decimal(row[field]) - Decimal(row["path_D_bil"])
                    ),
                    "selected_variant": str(is_selected).lower(),
                    "variant_role": role,
                    "allowed_use": "denominator_variant_comparison",
                    "blocked_use": (
                        "select_fixed_D_for_rate_changing_forecast_scenario"
                        if variant == "fixed_D"
                        else "canonical_headline_promotion"
                    ),
                }
            )
    return out


def denominator_scenario_delta_audit_rows(
    bridge_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Audit that rate-changing and non-rate denominator moves are classified safely."""

    if not bridge_rows:
        raise DenominatorParityError("denominator bridge rows are empty")
    rate_rows = [row for row in bridge_rows if row["rate_changing_scenario_flag"] == "true"]
    nonrate_rows = [
        row for row in bridge_rows if row["rate_changing_scenario_flag"] == "false"
    ]
    sign_ok = all(
        _rate_sign_ok(row["scenario_id"], Decimal(row["delta_moving_D_vs_path_bil"]))
        for row in rate_rows
    )
    nonrate_ok = all(Decimal(row["delta_moving_D_vs_path_bil"]) == 0 for row in nonrate_rows)
    selected_ok = all(
        row["selected_denominator_variant_role"].startswith("selected_moving")
        for row in rate_rows
    ) and all(
        row["selected_denominator_variant_role"].startswith("selected_path")
        for row in nonrate_rows
    )
    return [
        {
            "denominator_scenario_delta_audit_row_id": (
                "denominator_scenario_delta_audit::moving_D_selection"
            ),
            "check_id": "moving_D_selected_for_rate_scenarios",
            "check_status": "pass" if selected_ok else "fail",
            "row_count": str(len(bridge_rows)),
            "rate_changing_row_count": str(len(rate_rows)),
            "nonrate_row_count": str(len(nonrate_rows)),
            "required_rule": (
                "rate_changing_rows_select_moving_D;nonrate_rows_select_path_D"
            ),
            "allowed_use": "denominator_bridge_audit",
            "blocked_use": "promote_fixed_D_as_selected_rate_scenario_D",
        },
        {
            "denominator_scenario_delta_audit_row_id": (
                "denominator_scenario_delta_audit::signs"
            ),
            "check_id": "rate_direction_signs",
            "check_status": "pass" if sign_ok and nonrate_ok else "fail",
            "row_count": str(len(bridge_rows)),
            "rate_changing_row_count": str(len(rate_rows)),
            "nonrate_row_count": str(len(nonrate_rows)),
            "required_rule": (
                "rate_down_lowers_D;rate_up_raises_D;nonrate_rows_have_zero_rate_D_move"
            ),
            "allowed_use": "denominator_bridge_audit",
            "blocked_use": "interpret_scenario_before_D_signs_pass",
        },
    ]


def write_denominator_parity_outputs(
    output_dir: str | Path,
    *,
    bridge_rows: Sequence[Mapping[str, str]],
    variant_rows: Sequence[Mapping[str, str]],
    audit_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write denominator parity bridge outputs."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "bridge_csv": out / "ratewall_denominator_parity_bridge.csv",
        "variant_csv": out / "ratewall_denominator_variant_surface.csv",
        "audit_csv": out / "ratewall_denominator_scenario_delta_audit.csv",
    }
    write_rows(
        paths["bridge_csv"],
        [dict(row) for row in bridge_rows],
        DENOMINATOR_PARITY_BRIDGE_FIELDS,
    )
    write_rows(
        paths["variant_csv"],
        [dict(row) for row in variant_rows],
        DENOMINATOR_VARIANT_SURFACE_FIELDS,
    )
    write_rows(
        paths["audit_csv"],
        [dict(row) for row in audit_rows],
        DENOMINATOR_SCENARIO_DELTA_AUDIT_FIELDS,
    )
    return paths


def _baseline_path_d_by_year(rows: Sequence[Mapping[str, str]]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for row in rows:
        if row["scenario_id"] == row["baseline_scenario_id"]:
            fiscal_year = row["fiscal_year"]
            if fiscal_year in out:
                raise DenominatorParityError(
                    f"multiple baseline denominator rows for FY{fiscal_year}"
                )
            out[fiscal_year] = Decimal(row["central_moving_denominator_bil"])
    fiscal_years = {row["fiscal_year"] for row in rows}
    missing = fiscal_years - set(out)
    if missing:
        raise DenominatorParityError(
            "missing baseline denominator rows for " + ", ".join(sorted(missing))
        )
    return out


def _rate_sign_ok(scenario_id: str, delta_d: Decimal) -> bool:
    if "rate_down" in scenario_id:
        return delta_d < 0
    if "rate_up" in scenario_id:
        return delta_d > 0
    return delta_d != 0


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise DenominatorParityError(f"missing required input: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _fmt(value: Decimal) -> str:
    return format(value, "f")
