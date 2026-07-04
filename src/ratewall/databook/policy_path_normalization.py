"""Policy-path exposure normalization helpers for model gates."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


BPS_PER_100BP_YEAR = Decimal("100")
DEFAULT_QUARTER_YEAR = Decimal("0.25")

POLICY_PATH_REQUIRED_OBJECT = (
    "horizon_by_horizon_policy_rate_bps_exposure_vector_or_reviewed_duration_scalar"
)
POLICY_PATH_BLOCKED_NORMALIZATION_STATUS = (
    "blocked_no_reviewed_policy_path_vector_or_duration_scalar"
)
POLICY_PATH_BLOCKED_SOURCE_STATUS = (
    "shock_source_contains_scalar_event_or_monthly_shock_only"
)
POLICY_PATH_BPS_EXPOSURE_FORMULA = (
    "bps_year_exposure = sum(policy_rate_bps_path[t] * interval_years[t]); "
    "exposure_100bp_year = bps_year_exposure / 100"
)
POLICY_PATH_EFFECT_NORMALIZATION_FORMULA = (
    "diagnostic_tdsp_change_per_100bp * 100 / "
    "reviewed_policy_path_bps_year_exposure"
)
POLICY_PATH_EXACT_BLOCKER = (
    "The TDSP tranche reports a diagnostic mechanical outcome change per 100bp "
    "scalar shock, but no source-backed policy-path exposure vector or duration "
    "scalar is admitted for converting it into a 100bp-year demand-drag object."
)
POLICY_PATH_EVIDENCE_NEEDED = (
    "Admit a policy-path exposure vector, document bps-year normalization, and "
    "propagate uncertainty through the TDSP-to-current-demand mapping before "
    "promotion."
)


@dataclass(frozen=True)
class PolicyPathExposure:
    exposure_bps_year: Decimal
    exposure_100bp_year: Decimal


@dataclass(frozen=True)
class PolicyPathNormalizationResult:
    normalization_status: str
    exposure_bps_year: Decimal | None
    exposure_100bp_year: Decimal | None
    normalized_effect_per_100bp_year: Decimal | None
    exact_blocker: str


def policy_path_exposure_bps_year(
    policy_rate_bps_path: Iterable[object],
    *,
    interval_years: object | Iterable[object] = DEFAULT_QUARTER_YEAR,
) -> PolicyPathExposure:
    """Integrate a policy-rate path into basis-point-years.

    Repo convention treats 100 basis-point-years as one 100bp-year exposure.
    """

    bps_values = [_decimal(value) for value in policy_rate_bps_path]
    if isinstance(interval_years, str) or not isinstance(interval_years, Iterable):
        year_values = [_decimal(interval_years)] * len(bps_values)
    else:
        year_values = [_decimal(value) for value in interval_years]
    if len(bps_values) != len(year_values):
        raise ValueError("policy_rate_bps_path and interval_years must align")
    exposure = sum(
        (bps * years for bps, years in zip(bps_values, year_values, strict=True)),
        Decimal("0"),
    )
    return PolicyPathExposure(
        exposure_bps_year=exposure,
        exposure_100bp_year=exposure / BPS_PER_100BP_YEAR,
    )


def normalize_effect_per_100bp_year(
    diagnostic_effect_per_scalar_100bp: object,
    *,
    exposure_bps_year: object,
    policy_path_admitted: bool,
) -> PolicyPathNormalizationResult:
    """Normalize a diagnostic scalar-shock effect to one 100bp-year exposure."""

    if not policy_path_admitted:
        return _blocked_result(POLICY_PATH_EXACT_BLOCKER)
    try:
        exposure = _decimal(exposure_bps_year)
        effect = _decimal(diagnostic_effect_per_scalar_100bp)
    except ValueError as exc:
        return _blocked_result(str(exc))
    if exposure <= Decimal("0"):
        return _blocked_result("Policy-path exposure must be positive.")
    normalized = effect * BPS_PER_100BP_YEAR / exposure
    return PolicyPathNormalizationResult(
        normalization_status="pass_reviewed_policy_path_100bp_year_candidate",
        exposure_bps_year=exposure,
        exposure_100bp_year=exposure / BPS_PER_100BP_YEAR,
        normalized_effect_per_100bp_year=normalized,
        exact_blocker="",
    )


def blocked_policy_path_normalization_fields() -> dict[str, str]:
    return {
        "required_policy_path_object": POLICY_PATH_REQUIRED_OBJECT,
        "policy_path_100bp_year_normalization_status": (
            POLICY_PATH_BLOCKED_NORMALIZATION_STATUS
        ),
        "policy_path_source_status": POLICY_PATH_BLOCKED_SOURCE_STATUS,
        "bps_year_exposure_output": "",
        "normalization_formula_candidate": POLICY_PATH_EFFECT_NORMALIZATION_FORMULA,
        "normalization_output_value": "",
        "exact_blocker": POLICY_PATH_EXACT_BLOCKER,
        "evidence_needed_before_mapping": POLICY_PATH_EVIDENCE_NEEDED,
    }


def _blocked_result(exact_blocker: str) -> PolicyPathNormalizationResult:
    return PolicyPathNormalizationResult(
        normalization_status=POLICY_PATH_BLOCKED_NORMALIZATION_STATUS,
        exposure_bps_year=None,
        exposure_100bp_year=None,
        normalized_effect_per_100bp_year=None,
        exact_blocker=exact_blocker,
    )


def _decimal(value: object) -> Decimal:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid numeric policy-path value: {value!r}") from exc
    if not decimal_value.is_finite():
        raise ValueError(f"Invalid finite policy-path value: {value!r}")
    return decimal_value
