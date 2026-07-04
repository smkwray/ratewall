"""Marginal denominator surface for the final RW_M object."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal
from decimal import localcontext
from pathlib import Path
from typing import Any

import yaml

from ratewall.databook.marginal_object_ledger import DEFAULT_OBJECT_CONFIG_PATH
from ratewall.databook.table_io import write_rows

DEFAULT_GDP_PATH = Path("data/raw/current_demand_gdp_share/GDP.csv")
DEFAULT_CURRENT_BENCHMARK_PATH = Path(
    "var/preliminary_scenario_results/current_observed_overlay/"
    "ratewall_current_assumption_benchmark.csv"
)
DEFAULT_HISTORICAL_DENOMINATOR_PATH = Path(
    "var/preliminary_scenario_results/historical_provisional_estimate/"
    "ratewall_historical_denominator_convention_review.csv"
)
DEFAULT_DENOMINATOR_SEED_PATH = Path(
    "configs/assumption_mode/ratewall_marginal_denominator_seed.csv"
)

MARGINAL_DENOMINATOR_SURFACE_FIELDS = [
    "marginal_denominator_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "fiscal_year",
    "scenario_id",
    "shock_path_id",
    "shock_bps_year",
    "nominal_gdp_bil",
    "c_D_case",
    "c_D",
    "state_multiplier",
    "fixed_D_comparison_bil",
    "historical_path_D_bil",
    "marginal_denominator_bil",
    "denominator_basis",
    "selected_marginal_D",
    "fixed_D_audit_status",
    "old_denominator_variant_status",
    "source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_DENOMINATOR_AUDIT_FIELDS = [
    "marginal_denominator_audit_row_id",
    "check_id",
    "check_status",
    "row_count",
    "selected_row_count",
    "required_rule",
    "allowed_use",
    "blocked_use",
]

RATE_ENVIRONMENT_EXPOSURE_DIAGNOSTIC_FIELDS = [
    "rate_environment_exposure_diagnostic_row_id",
    "period_object",
    "scenario_id",
    "old_rate_path_denominator_rule",
    "marginal_denominator_rule",
    "rate_environment_moves_d",
    "selected_marginal_d_allowed",
    "blocked_use",
    "claim_boundary",
]

DENOMINATOR_STATE_MULTIPLIER_FIELDS = [
    "denominator_state_multiplier_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "state_multiplier_case",
    "state_multiplier",
    "selected_state_multiplier",
    "multiplier_basis",
    "admission_status",
    "source_status",
    "allowed_use",
    "blocked_drivers",
    "claim_boundary",
]

MARGINAL_DENOMINATOR_SEED_FIELDS = [
    "period_object",
    "period",
    "horizon",
    "state_id",
    "fiscal_year",
    "scenario_id",
    "shock_path_id",
    "shock_bps_year",
    "selected_marginal_D_bil",
    "nominal_gdp_bil",
    "fixed_D_comparison_bil",
    "historical_path_D_bil",
    "source_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class MarginalDenominatorError(ValueError):
    """Raised when marginal denominator rows violate the RW_M D contract."""


def marginal_denominator_surface_rows(
    *,
    object_config_path: str | Path = DEFAULT_OBJECT_CONFIG_PATH,
    gdp_path: str | Path = DEFAULT_GDP_PATH,
    current_benchmark_path: str | Path = DEFAULT_CURRENT_BENCHMARK_PATH,
    historical_denominator_path: str | Path = DEFAULT_HISTORICAL_DENOMINATOR_PATH,
    seed_path: str | Path | None = None,
    include_historical: bool = True,
    include_current_and_forecast: bool = True,
) -> list[dict[str, str]]:
    """Return marginal D rows using nominal GDP state scale and c_D bands."""

    config = _load_config(object_config_path)
    d_config = config.get("marginal_denominator", {})
    if not isinstance(d_config, dict):
        raise MarginalDenominatorError("marginal_denominator config must be a mapping")
    cases = _coefficient_cases(d_config)
    shock_path_id = _clean(config.get("shock_path_id"))
    horizon = _clean(config.get("horizon", "annual_h1_100bp_year"))
    shock_bps_year = Decimal(
        _clean(d_config.get("shock_bps_year", config.get("shock_bps_year")))
    )
    state_multiplier = Decimal(_clean(d_config.get("state_multiplier", "1")))
    if seed_path is not None:
        gdp_rows = _seed_denominator_rows(seed_path)
    else:
        gdp_rows: list[dict[str, str]] = []
        if include_historical:
            gdp_rows.extend(_historical_gdp_rows(gdp_path, historical_denominator_path))
        if include_current_and_forecast:
            gdp_rows.extend(_current_forecast_gdp_rows(current_benchmark_path))
    rows: list[dict[str, str]] = []
    for gdp_row in gdp_rows:
        nominal_gdp = Decimal(gdp_row["nominal_gdp_bil"])
        for case in cases:
            c_d = Decimal(case["c_D"])
            d_value = nominal_gdp * c_d * (shock_bps_year / Decimal("100")) * state_multiplier
            selected = case["selected"]
            rows.append(
                {
                    "marginal_denominator_row_id": (
                        "marginal_denominator::"
                        f"{gdp_row['period_object']}::{gdp_row['period']}::"
                        f"{gdp_row['state_id']}::{horizon}::{case['c_D_case']}"
                    ),
                    "period_object": gdp_row["period_object"],
                    "period": gdp_row["period"],
                    "horizon": horizon,
                    "state_id": gdp_row["state_id"],
                    "fiscal_year": gdp_row["fiscal_year"],
                    "scenario_id": gdp_row["scenario_id"],
                    "shock_path_id": shock_path_id,
                    "shock_bps_year": _fmt(shock_bps_year),
                    "nominal_gdp_bil": _fmt(nominal_gdp),
                    "c_D_case": case["c_D_case"],
                    "c_D": case["c_D"],
                    "state_multiplier": _fmt(state_multiplier),
                    "fixed_D_comparison_bil": gdp_row["fixed_D_comparison_bil"],
                    "historical_path_D_bil": gdp_row["historical_path_D_bil"],
                    "marginal_denominator_bil": _fmt(d_value),
                    "denominator_basis": (
                        "nominal_gdp_bil * c_D * (shock_bps_year / 100) * state_multiplier"
                    ),
                    "selected_marginal_D": str(selected).lower(),
                    "fixed_D_audit_status": gdp_row["fixed_D_audit_status"],
                    "old_denominator_variant_status": (
                        gdp_row["old_denominator_variant_status"]
                    ),
                    "source_status": gdp_row["source_status"],
                    "allowed_use": (
                        "selected_marginal_D_surface"
                        if selected
                        else "marginal_D_sensitivity_band"
                    ),
                    "blocked_use": (
                        "old_rate_path_D_scaled_by_observed_short_rate;"
                        "forecast_moving_D_as_final_rw_m;denominator_as_numerator"
                    ),
                    "claim_boundary": (
                        "marginal_D_is_standardized_plus_100bp_year_threshold_scale_not_current_rate_level"
                    ),
                }
            )
    validate_marginal_denominator_surface(rows)
    return rows


def marginal_denominator_audit_rows(
    surface_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Audit selected case, positivity, and standardized shock invariants."""

    if not surface_rows:
        raise MarginalDenominatorError("marginal denominator surface rows are empty")
    selected = [row for row in surface_rows if row["selected_marginal_D"] == "true"]
    periods = {
        (row["period"], row["horizon"], row["state_id"], row["shock_path_id"])
        for row in surface_rows
    }
    selected_periods = {
        (row["period"], row["horizon"], row["state_id"], row["shock_path_id"])
        for row in selected
    }
    checks = [
        (
            "one_selected_base_case_per_period",
            periods == selected_periods
            and all(row["c_D_case"] == "base" for row in selected),
            "each period,horizon,state_id,shock_path_id has one selected base c_D row",
            "promote_low_or_high_sensitivity_as_selected_D",
        ),
        (
            "positive_standardized_marginal_D",
            all(Decimal(row["marginal_denominator_bil"]) > 0 for row in surface_rows)
            and all(row["shock_bps_year"] == "100" for row in surface_rows),
            "all marginal D rows are positive and use the 100bp-year standard shock",
            "negative_or_zero_D;nonstandard_shock_selected",
        ),
        (
            "no_current_rate_level_scaled_D",
            all("observed_short_rate" in row["blocked_use"] for row in surface_rows),
            "old path-D/current-rate scaling is blocked for final RW_M denominator",
            "old_path_D_scaled_by_current_rate",
        ),
        (
            "historical_fixed_D_audit_recorded",
            all(
                row["fixed_D_audit_status"]
                in {
                    "pass_fixed_D_equals_nominal_gdp_times_c_D",
                    "not_applicable_nonhistorical",
                    "no_prior_fixed_D_artifact_gdp_only_backfill",
                }
                for row in surface_rows
            ),
            "historical fixed-D comparison status is explicit for every row",
            "silent_historical_path_D_promotion",
        ),
    ]
    return [
        {
            "marginal_denominator_audit_row_id": f"marginal_denominator_audit::{check_id}",
            "check_id": check_id,
            "check_status": "pass" if ok else "fail",
            "row_count": str(len(surface_rows)),
            "selected_row_count": str(len(selected)),
            "required_rule": required_rule,
            "allowed_use": "marginal_denominator_gate",
            "blocked_use": blocked_use,
        }
        for check_id, ok, required_rule, blocked_use in checks
    ]


def rate_environment_exposure_diagnostic_rows() -> list[dict[str, str]]:
    """Explain why final marginal D does not move mechanically with current rates."""

    rows = [
        {
            "rate_environment_exposure_diagnostic_row_id": (
                f"rate_environment_exposure::{period}"
            ),
            "period_object": period,
            "scenario_id": scenario,
            "old_rate_path_denominator_rule": (
                "path_D_or_moving_D_may_change_with_observed_or_scenario_rate_path"
            ),
            "marginal_denominator_rule": (
                "D_M_uses_state_nominal_gdp_times_standardized_100bp_year_c_D"
            ),
            "rate_environment_moves_d": "false",
            "selected_marginal_d_allowed": "true",
            "blocked_use": "mechanically_change_selected_D_M_because_current_short_rate_changed",
            "claim_boundary": (
                "current_rate_level_is_context_for_state_not_a_mechanical_multiplier_in_final_D_M"
            ),
        }
        for period, scenario in [
            ("historical", "actual_state"),
            ("current", "current_state"),
            ("forecast", "forecast_state"),
        ]
    ]
    return rows


def denominator_state_multiplier_rows(
    surface_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return the explicit state-multiplier rows used by selected marginal D."""

    selected = [row for row in surface_rows if row["selected_marginal_D"] == "true"]
    seen: set[tuple[str, str, str, str]] = set()
    rows: list[dict[str, str]] = []
    for row in selected:
        key = (
            row["period"],
            row["horizon"],
            row["state_id"],
            row["shock_path_id"],
        )
        if key in seen:
            raise MarginalDenominatorError("duplicate selected state multiplier key")
        seen.add(key)
        rows.append(
            {
                "denominator_state_multiplier_row_id": (
                    "denominator_state_multiplier::"
                    f"{row['period_object']}::{row['period']}::{row['state_id']}"
                ),
                "period_object": row["period_object"],
                "period": row["period"],
                "horizon": row["horizon"],
                "state_id": row["state_id"],
                "shock_path_id": row["shock_path_id"],
                "state_multiplier_case": "neutral",
                "state_multiplier": row["state_multiplier"],
                "selected_state_multiplier": "true",
                "multiplier_basis": (
                    "neutral_selected_default_until_admitted_state_transmission_model"
                ),
                "admission_status": "selected_neutral_default",
                "source_status": "owner_assumption_mode_state_multiplier_neutral",
                "allowed_use": "selected_marginal_D_multiplier",
                "blocked_drivers": (
                    "current_rate_level;old_path_D;numerator_size;tdc_stock;"
                    "deposit_stock;beta;chi;scenario_label"
                ),
                "claim_boundary": (
                    "selected_state_multiplier_is_not_a_mechanical_rate_or_stock_response"
                ),
            }
        )
    validate_denominator_state_multiplier(rows)
    return rows


def write_marginal_denominator_outputs(
    output_dir: str | Path,
    *,
    surface_rows: Sequence[Mapping[str, str]],
    audit_rows: Sequence[Mapping[str, str]],
    diagnostic_rows: Sequence[Mapping[str, str]],
    state_multiplier_rows: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Path]:
    """Write marginal denominator outputs."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "surface_csv": out / "ratewall_marginal_denominator_surface.csv",
        "audit_csv": out / "ratewall_marginal_denominator_audit.csv",
        "diagnostic_csv": out / "ratewall_rate_environment_exposure_diagnostic.csv",
        "state_multiplier_csv": out / "ratewall_denominator_state_multiplier.csv",
    }
    write_rows(paths["surface_csv"], [dict(row) for row in surface_rows], MARGINAL_DENOMINATOR_SURFACE_FIELDS)
    write_rows(paths["audit_csv"], [dict(row) for row in audit_rows], MARGINAL_DENOMINATOR_AUDIT_FIELDS)
    write_rows(
        paths["diagnostic_csv"],
        [dict(row) for row in diagnostic_rows],
        RATE_ENVIRONMENT_EXPOSURE_DIAGNOSTIC_FIELDS,
    )
    if state_multiplier_rows is None:
        state_multiplier_rows = denominator_state_multiplier_rows(surface_rows)
    write_rows(
        paths["state_multiplier_csv"],
        [dict(row) for row in state_multiplier_rows],
        DENOMINATOR_STATE_MULTIPLIER_FIELDS,
    )
    return paths


def validate_marginal_denominator_surface(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalDenominatorError("marginal denominator rows are empty")
    for row in rows:
        if set(row) != set(MARGINAL_DENOMINATOR_SURFACE_FIELDS):
            raise MarginalDenominatorError("marginal denominator schema mismatch")
        if not row["horizon"] or not row["state_id"]:
            raise MarginalDenominatorError("horizon and state_id are required")
        if row["shock_bps_year"] != "100":
            raise MarginalDenominatorError("marginal denominator must use 100bp-year shock")
        if Decimal(row["nominal_gdp_bil"]) <= 0:
            raise MarginalDenominatorError("nominal GDP must be positive")
        if Decimal(row["marginal_denominator_bil"]) <= 0:
            raise MarginalDenominatorError("marginal denominator must be positive")
        expected = (
            Decimal(row["nominal_gdp_bil"])
            * Decimal(row["c_D"])
            * (Decimal(row["shock_bps_year"]) / Decimal("100"))
            * Decimal(row["state_multiplier"])
        )
        if Decimal(row["marginal_denominator_bil"]) != expected:
            raise MarginalDenominatorError("marginal denominator formula mismatch")
        if row["selected_marginal_D"] == "true" and row["c_D_case"] != "base":
            raise MarginalDenominatorError("only base c_D can be selected marginal D")
        if (
            row["period_object"] == "historical"
            and row["historical_path_D_bil"]
            and row["historical_path_D_bil"] == row["marginal_denominator_bil"]
            and row["fixed_D_audit_status"]
            != "pass_fixed_D_equals_nominal_gdp_times_c_D"
        ):
            raise MarginalDenominatorError("historical path-D cannot be selected")
        if "old_rate_path_D_scaled_by_observed_short_rate" not in row["blocked_use"]:
            raise MarginalDenominatorError("old rate-path D blocker missing")
    selected_keys = [
        (row["period"], row["horizon"], row["state_id"], row["shock_path_id"])
        for row in rows
        if row["selected_marginal_D"] == "true"
    ]
    if len(selected_keys) != len(set(selected_keys)):
        raise MarginalDenominatorError("duplicate selected marginal D rows")


def validate_denominator_state_multiplier(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalDenominatorError("denominator state multiplier rows are empty")
    keys = []
    required_blockers = {
        "current_rate_level",
        "old_path_D",
        "numerator_size",
        "tdc_stock",
        "deposit_stock",
        "beta",
        "chi",
        "scenario_label",
    }
    for row in rows:
        if set(row) != set(DENOMINATOR_STATE_MULTIPLIER_FIELDS):
            raise MarginalDenominatorError("denominator state multiplier schema mismatch")
        key = (row["period"], row["horizon"], row["state_id"], row["shock_path_id"])
        keys.append(key)
        if row["state_multiplier_case"] != "neutral":
            raise MarginalDenominatorError("selected state multiplier must be neutral")
        if row["selected_state_multiplier"] != "true":
            raise MarginalDenominatorError("state multiplier rows must be selected")
        if Decimal(row["state_multiplier"]) != Decimal("1"):
            raise MarginalDenominatorError(
                "selected state multiplier must remain 1 until admitted model exists"
            )
        if row["multiplier_basis"] != (
            "neutral_selected_default_until_admitted_state_transmission_model"
        ):
            raise MarginalDenominatorError("state multiplier basis drift")
        blockers = set(row["blocked_drivers"].split(";"))
        missing = required_blockers - blockers
        if missing:
            raise MarginalDenominatorError(
                f"state multiplier missing blocked drivers: {sorted(missing)}"
            )
    if len(keys) != len(set(keys)):
        raise MarginalDenominatorError("duplicate denominator state multiplier rows")


def _historical_gdp_rows(
    gdp_path: str | Path,
    historical_denominator_path: str | Path,
) -> list[dict[str, str]]:
    rows = _historical_denominator_review_rows(historical_denominator_path)
    covered_periods = {row["period"] for row in rows}
    with Path(gdp_path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            date = _clean(row.get("observation_date"))
            value = _clean(row.get("GDP"))
            if not date or not value:
                continue
            year = int(date[:4])
            if year < 2000:
                continue
            quarter = _quarter_from_month(int(date[5:7]))
            period = f"{year}Q{quarter}"
            if period in covered_periods:
                continue
            rows.append(
                {
                    "period_object": "historical",
                    "period": period,
                    "state_id": f"historical_actual_state::{period}",
                    "fiscal_year": str(year),
                    "scenario_id": "actual_state",
                    "nominal_gdp_bil": _fmt(Decimal(value)),
                    "fixed_D_comparison_bil": "",
                    "historical_path_D_bil": "",
                    "fixed_D_audit_status": "no_prior_fixed_D_artifact_gdp_only_backfill",
                    "old_denominator_variant_status": "old_path_D_not_present_for_backfill_period",
                    "source_status": (
                        "source_backed_fred_nominal_gdp_quarterly_gdp_only_backfill"
                    ),
                }
            )
    return rows


def _historical_denominator_review_rows(path: str | Path) -> list[dict[str, str]]:
    if not Path(path).exists():
        return []
    rows = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            period = _clean(row.get("period"))
            nominal_gdp = Decimal(_clean(row.get("nominal_gdp_bil")))
            fixed_d = Decimal(_clean(row.get("fixed_D_comparison_bil")))
            expected = nominal_gdp * Decimal("0.00776")
            audit = (
                "pass_fixed_D_equals_nominal_gdp_times_c_D"
                if fixed_d == expected
                else "fail_fixed_D_not_nominal_gdp_times_c_D"
            )
            rows.append(
                {
                    "period_object": "historical",
                    "period": period,
                    "state_id": f"historical_actual_state::{period}",
                    "fiscal_year": period[:4],
                    "scenario_id": "actual_state",
                    "nominal_gdp_bil": _fmt(nominal_gdp),
                    "fixed_D_comparison_bil": _fmt(fixed_d),
                    "historical_path_D_bil": _fmt(
                        Decimal(_clean(row.get("selected_historical_path_D_bil")))
                    ),
                    "fixed_D_audit_status": audit,
                    "old_denominator_variant_status": (
                        "historical_path_D_reclassified_as_rate_environment_exposure"
                    ),
                    "source_status": (
                        "source_backed_historical_denominator_review_fixed_D_audited"
                    ),
                }
            )
    return rows


def _current_forecast_gdp_rows(path: str | Path) -> list[dict[str, str]]:
    rows = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            year = _clean(row.get("forecast_year"))
            gdp = _clean(row.get("nominal_gdp_bil"))
            if not year or not gdp:
                continue
            period_object = "current" if year == "2026" else "forecast"
            scenario_id = "current_state" if period_object == "current" else "cbo_baseline_state"
            rows.append(
                {
                    "period_object": period_object,
                    "period": year,
                    "state_id": f"{scenario_id}::{year}",
                    "fiscal_year": year,
                    "scenario_id": scenario_id,
                    "nominal_gdp_bil": _fmt(Decimal(gdp)),
                    "fixed_D_comparison_bil": "",
                    "historical_path_D_bil": "",
                    "fixed_D_audit_status": "not_applicable_nonhistorical",
                    "old_denominator_variant_status": (
                        "current_delta_D_conv_100bp_year_bil"
                        if period_object == "current"
                        else "forecast_ngdp_times_c_D_selected"
                    ),
                    "source_status": (
                        "current_assumption_benchmark_nominal_gdp"
                        if period_object == "current"
                        else "current_assumption_benchmark_forecast_nominal_gdp"
                    ),
                }
            )
    return rows


def _seed_denominator_rows(path: str | Path) -> list[dict[str, str]]:
    seed_path = Path(path)
    if not seed_path.exists():
        raise MarginalDenominatorError(
            f"marginal denominator seed path is missing: {seed_path}"
        )
    rows: list[dict[str, str]] = []
    with seed_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != set(MARGINAL_DENOMINATOR_SEED_FIELDS):
            raise MarginalDenominatorError("marginal denominator seed schema mismatch")
        for row in reader:
            selected_d = Decimal(_clean(row.get("selected_marginal_D_bil")))
            nominal_gdp = _clean(row.get("nominal_gdp_bil"))
            if not nominal_gdp:
                with localcontext() as ctx:
                    ctx.prec = 50
                    nominal_gdp = _fmt(selected_d / Decimal("0.00776"))
            rows.append(
                {
                    "period_object": _clean(row.get("period_object")),
                    "period": _clean(row.get("period")),
                    "state_id": _clean(row.get("state_id")),
                    "fiscal_year": _clean(row.get("fiscal_year")),
                    "scenario_id": _clean(row.get("scenario_id")),
                    "nominal_gdp_bil": nominal_gdp,
                    "fixed_D_comparison_bil": _clean(row.get("fixed_D_comparison_bil")),
                    "historical_path_D_bil": _clean(row.get("historical_path_D_bil")),
                    "fixed_D_audit_status": (
                        "pass_fixed_D_equals_nominal_gdp_times_c_D"
                        if _clean(row.get("period_object")) == "historical"
                        else "not_applicable_nonhistorical"
                    ),
                    "old_denominator_variant_status": (
                        "denominator_seed_reconstructs_existing_selected_D_without_value_change"
                    ),
                    "source_status": _clean(row.get("source_status")),
                }
            )
    if not rows:
        raise MarginalDenominatorError("marginal denominator seed rows are empty")
    return rows


def _coefficient_cases(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases = config.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise MarginalDenominatorError("marginal denominator cases are required")
    out = []
    for case in cases:
        if not isinstance(case, dict):
            raise MarginalDenominatorError("marginal denominator case must be a mapping")
        out.append(
            {
                "c_D_case": _clean(case.get("c_D_case")),
                "c_D": _fmt(Decimal(_clean(case.get("c_D")))),
                "selected": bool(case.get("selected")),
            }
        )
    if [case["c_D_case"] for case in out] != ["low", "base", "high"]:
        raise MarginalDenominatorError("marginal denominator cases must be low/base/high")
    if sum(1 for case in out if case["selected"]) != 1:
        raise MarginalDenominatorError("exactly one marginal denominator case must be selected")
    return out


def _load_config(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise MarginalDenominatorError("marginal denominator config must be a mapping")
    return payload


def _quarter_from_month(month: int) -> int:
    return ((month - 1) // 3) + 1


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
