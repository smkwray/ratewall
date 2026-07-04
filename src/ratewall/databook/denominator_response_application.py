"""Apply admitted denominator-response profiles to scenario rate paths."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.tdcsim_cbo_contracts import (
    TDCSIM_CBO_SCENARIO_RUNS_DIR,
    tdcsim_cbo_curve_denominator_input_rows_from_directory,
)


DENOMINATOR_RESPONSE_APPLICATION_FIELDS = [
    "denominator_response_application_row_id",
    "source_curve_denominator_input_row_id",
    "fiscal_year",
    "scenario_id",
    "baseline_scenario_id",
    "effective_curve_overlay_bp",
    "path_bps_year",
    "normalized_100bp_year_value",
    "frozen_denominator_bil",
    "denominator_response_profile_id",
    "denominator_response_coefficient",
    "denominator_response_coefficient_unit",
    "coefficient_admission_status",
    "delta_denominator_bil",
    "moving_denominator_bil",
    "total_current_demand_support_bil",
    "frozen_ratewall_ratio",
    "moving_ratewall_ratio",
    "frozen_delta_ratewall_ratio_vs_baseline",
    "moving_delta_ratewall_ratio_vs_baseline",
    "moving_minus_frozen_ratewall_ratio",
    "denominator_response_direction",
    "denominator_response_requirement_status",
    "denominator_scope",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
    "formula_replacement_allowed",
    "causal_market_yield_estimate_enabled",
]

ADMITTED_COEFFICIENT_STATUSES = {
    "admitted_curve_denominator_response_coefficient",
    "admitted_noncanonical_curve_denominator_response_coefficient",
}
COEFFICIENT_UNIT = "fraction_of_frozen_denominator_per_100bp_year"


class DenominatorResponseApplicationError(ValueError):
    """Raised when a moving-D application row cannot be computed safely."""


def denominator_response_application_rows_from_directory(
    coefficient_profile: Mapping[str, str],
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
) -> list[dict[str, str]]:
    """Apply a denominator-response profile to current TDCSim/CBO curve rows."""

    return denominator_response_application_rows(
        _curve_rows_with_current_path_fields(
            tdcsim_cbo_curve_denominator_input_rows_from_directory(suite_dir)
        ),
        coefficient_profile=coefficient_profile,
    )


def owner_admitted_denominator_response_application_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
) -> list[dict[str, str]]:
    """Emit moving-D rows using the owner-admitted Assumption Mode profile."""

    from ratewall.databook.denominator_response_coefficient import (
        selected_owner_admitted_curve_denominator_response_profile,
    )

    return denominator_response_application_rows_from_directory(
        selected_owner_admitted_curve_denominator_response_profile(
            diagnostic_rows=[],
            path_object_rows=[],
        ),
        suite_dir=suite_dir,
    )


def frbus_structural_denominator_response_application_rows_from_directory(
    suite_dir: str | Path = TDCSIM_CBO_SCENARIO_RUNS_DIR,
) -> list[dict[str, str]]:
    """Emit moving-D rows using the FRB/US structural benchmark profile."""

    from ratewall.databook.denominator_response_coefficient import (
        selected_frbus_structural_curve_denominator_response_profile,
    )

    return denominator_response_application_rows_from_directory(
        selected_frbus_structural_curve_denominator_response_profile(
            diagnostic_rows=[],
            path_object_rows=[],
        ),
        suite_dir=suite_dir,
    )


def denominator_response_application_rows(
    curve_denominator_input_rows: Iterable[Mapping[str, str]],
    *,
    coefficient_profile: Mapping[str, str],
) -> list[dict[str, str]]:
    """Move D for scenario rate paths only when an admitted profile is supplied."""

    input_rows = list(curve_denominator_input_rows)
    profile = _coefficient_profile(coefficient_profile)
    prelim = [_application_row(row, profile=profile) for row in input_rows]
    baseline_rows_by_year: dict[str, list[dict[str, str]]] = {}
    for row in prelim:
        if row["scenario_id"] == row["baseline_scenario_id"]:
            baseline_rows_by_year.setdefault(row["fiscal_year"], []).append(row)
    baseline_by_year: dict[str, dict[str, str]] = {}
    for fiscal_year, baseline_rows in baseline_rows_by_year.items():
        if len(baseline_rows) != 1:
            raise DenominatorResponseApplicationError(
                "moving-D application requires exactly one baseline row per "
                f"fiscal year; found {len(baseline_rows)} for {fiscal_year}"
            )
        baseline_by_year[fiscal_year] = baseline_rows[0]
    out: list[dict[str, str]] = []
    for row in prelim:
        baseline = baseline_by_year.get(row["fiscal_year"])
        if baseline is None:
            raise DenominatorResponseApplicationError(
                "moving-D application requires one baseline row per fiscal year"
            )
        row = dict(row)
        if row["moving_ratewall_ratio"] and baseline["moving_ratewall_ratio"]:
            row["moving_delta_ratewall_ratio_vs_baseline"] = _fmt(
                _decimal(row["moving_ratewall_ratio"])
                - _decimal(baseline["moving_ratewall_ratio"])
            )
        out.append(row)
    return sorted(out, key=lambda row: (int(row["fiscal_year"]), row["scenario_id"]))


def _curve_rows_with_current_path_fields(
    rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        row_out = dict(row)
        path_value = row_out.get("path_bps_year", "")
        normalized_value = row_out.get("normalized_100bp_year_value", "")
        if path_value and normalized_value:
            out.append(row_out)
            continue
        effective_bp = _decimal(row_out["effective_curve_overlay_bp"])
        if not path_value:
            row_out["path_bps_year"] = _fmt(effective_bp)
        if not normalized_value:
            row_out["normalized_100bp_year_value"] = _fmt(
                effective_bp / Decimal("100")
            )
        out.append(row_out)
    return out


def _application_row(
    row: Mapping[str, str],
    *,
    profile: Mapping[str, str],
) -> dict[str, str]:
    path_bps_year = _path_bps_year(row)
    normalized = path_bps_year / Decimal("100")
    frozen_denominator = _decimal(row["frozen_denominator_bil"])
    total_support = _decimal(row["total_current_demand_support_bil"])
    frozen_ratio = _decimal(row["frozen_ratewall_ratio"])
    coefficient_status = profile["coefficient_admission_status"]
    coefficient = profile["denominator_response_coefficient"]
    admitted = coefficient_status in ADMITTED_COEFFICIENT_STATUSES

    delta_denominator = Decimal("0")
    moving_denominator = frozen_denominator
    moving_ratio = frozen_ratio
    requirement_status = "zero_rate_path_frozen_D_consistent"
    scope = "zero_rate_path_frozen_D_consistent"
    allowed_use = "denominator_response_application_zero_rate_reference"
    blocked_use = (
        "canonical_headline_promotion;release_headline_claim;"
        "path_ratio_denominator_replacement"
    )
    claim_boundary = "zero_rate_path_no_denominator_response_required"
    direction = "zero_curve_overlay_keeps_denominator_frozen"

    if path_bps_year != 0 and not admitted:
        requirement_status = "blocked_missing_admitted_denominator_response_coefficient"
        scope = "blocked_nonzero_rate_path_no_moving_D"
        allowed_use = "blocked_denominator_response_application_status"
        blocked_use = (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "path_ratio_denominator_replacement;release_headline_claim;"
            "frozen_D_canonical_promotion_for_nonzero_rate_path"
        )
        claim_boundary = (
            "nonzero_rate_path_requires_admitted_coefficient_or_zero_response_proof"
        )
        return _row_payload(
            row,
            profile=profile,
            normalized=normalized,
            delta_denominator="",
            moving_denominator="",
            moving_ratio="",
            moving_minus_frozen="",
            direction="blocked_no_admitted_coefficient",
            requirement_status=requirement_status,
            scope=scope,
            allowed_use=allowed_use,
            blocked_use=blocked_use,
            claim_boundary=claim_boundary,
        )

    if path_bps_year != 0:
        delta_denominator = frozen_denominator * coefficient * normalized
        moving_denominator = frozen_denominator + delta_denominator
        if moving_denominator <= 0:
            raise DenominatorResponseApplicationError(
                "moving denominator must stay positive for "
                f"{row['scenario_id']}"
            )
        moving_ratio = total_support / moving_denominator
        requirement_status = "pass_moving_D_computed_from_admitted_profile"
        scope = "noncanonical_moving_D_scenario_sidecar"
        allowed_use = "moving_D_scenario_sidecar_after_coefficient_admission"
        blocked_use = (
            "canonical_headline_promotion_without_separate_owner_gate;"
            "release_headline_claim_without_separate_owner_gate"
        )
        claim_boundary = (
            "moving_D_computed_from_explicit_coefficient_profile;"
            "not_runtime_canonical_replacement"
        )
        direction = _direction(delta_denominator)

    return _row_payload(
        row,
        profile=profile,
        normalized=normalized,
        delta_denominator=_fmt(delta_denominator),
        moving_denominator=_fmt(moving_denominator),
        moving_ratio=_fmt(moving_ratio),
        moving_minus_frozen=_fmt(moving_ratio - frozen_ratio),
        direction=direction,
        requirement_status=requirement_status,
        scope=scope,
        allowed_use=allowed_use,
        blocked_use=blocked_use,
        claim_boundary=claim_boundary,
    )


def _row_payload(
    row: Mapping[str, str],
    *,
    profile: Mapping[str, str],
    normalized: Decimal,
    delta_denominator: str,
    moving_denominator: str,
    moving_ratio: str,
    moving_minus_frozen: str,
    direction: str,
    requirement_status: str,
    scope: str,
    allowed_use: str,
    blocked_use: str,
    claim_boundary: str,
) -> dict[str, str]:
    return {
        "denominator_response_application_row_id": (
            "denominator_response_application::"
            f"{row['fiscal_year']}::{row['scenario_id']}::"
            f"{profile['denominator_response_profile_id']}"
        ),
        "source_curve_denominator_input_row_id": row[
            "tdcsim_cbo_curve_denominator_input_row_id"
        ],
        "fiscal_year": row["fiscal_year"],
        "scenario_id": row["scenario_id"],
        "baseline_scenario_id": row["baseline_scenario_id"],
        "effective_curve_overlay_bp": row["effective_curve_overlay_bp"],
        "path_bps_year": _fmt(normalized * Decimal("100")),
        "normalized_100bp_year_value": _fmt(normalized),
        "frozen_denominator_bil": row["frozen_denominator_bil"],
        "denominator_response_profile_id": profile[
            "denominator_response_profile_id"
        ],
        "denominator_response_coefficient": _profile_coefficient_text(profile),
        "denominator_response_coefficient_unit": profile[
            "denominator_response_coefficient_unit"
        ],
        "coefficient_admission_status": profile["coefficient_admission_status"],
        "delta_denominator_bil": delta_denominator,
        "moving_denominator_bil": moving_denominator,
        "total_current_demand_support_bil": row["total_current_demand_support_bil"],
        "frozen_ratewall_ratio": row["frozen_ratewall_ratio"],
        "moving_ratewall_ratio": moving_ratio,
        "frozen_delta_ratewall_ratio_vs_baseline": row[
            "frozen_delta_ratewall_ratio_vs_baseline"
        ],
        "moving_delta_ratewall_ratio_vs_baseline": "",
        "moving_minus_frozen_ratewall_ratio": moving_minus_frozen,
        "denominator_response_direction": direction,
        "denominator_response_requirement_status": requirement_status,
        "denominator_scope": scope,
        "allowed_use": allowed_use,
        "blocked_use": blocked_use,
        "claim_boundary": claim_boundary,
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
    }


def _path_bps_year(row: Mapping[str, str]) -> Decimal:
    path_value = row.get("path_bps_year", "")
    normalized_value = row.get("normalized_100bp_year_value", "")
    path = _decimal(path_value) if path_value not in ("", None) else None
    normalized = (
        _decimal(normalized_value)
        if normalized_value not in ("", None)
        else None
    )
    if path is not None and normalized is not None:
        implied_path = normalized * Decimal("100")
        if path != implied_path:
            raise DenominatorResponseApplicationError(
                "path_bps_year and normalized_100bp_year_value disagree"
            )
        return path
    if path is not None:
        return path
    if normalized is not None:
        return normalized * Decimal("100")
    return _decimal(row["effective_curve_overlay_bp"])


def _coefficient_profile(profile: Mapping[str, str]) -> dict[str, str | Decimal]:
    profile_id = str(profile.get("denominator_response_profile_id", ""))
    status = str(profile.get("coefficient_admission_status", ""))
    unit = str(profile.get("denominator_response_coefficient_unit", ""))
    if not profile_id:
        raise DenominatorResponseApplicationError(
            "denominator_response_profile_id is required"
        )
    admitted = status in ADMITTED_COEFFICIENT_STATUSES
    if not admitted:
        return {
            "denominator_response_profile_id": profile_id,
            "denominator_response_coefficient": str(
                profile.get("denominator_response_coefficient", "")
            ),
            "denominator_response_coefficient_unit": unit,
            "coefficient_admission_status": status,
        }
    coefficient = _decimal(profile.get("denominator_response_coefficient", ""))
    if unit != COEFFICIENT_UNIT:
        raise DenominatorResponseApplicationError(
            f"unsupported denominator response coefficient unit: {unit}"
        )
    if coefficient < 0:
        raise DenominatorResponseApplicationError(
            "denominator response coefficient must be nonnegative"
        )
    return {
        "denominator_response_profile_id": profile_id,
        "denominator_response_coefficient": coefficient,
        "denominator_response_coefficient_unit": unit,
        "coefficient_admission_status": status,
    }


def _profile_coefficient_text(profile: Mapping[str, str | Decimal]) -> str:
    value = profile["denominator_response_coefficient"]
    if isinstance(value, Decimal):
        return _fmt(value)
    return str(value)


def _direction(delta_denominator: Decimal) -> str:
    if delta_denominator > 0:
        return "positive_rate_path_increases_D"
    if delta_denominator < 0:
        return "negative_rate_path_decreases_D"
    return "zero_rate_path_keeps_D_frozen"


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DenominatorResponseApplicationError(
            f"invalid decimal value: {value}"
        ) from exc


def _fmt(value: Decimal) -> str:
    if value == value.to_integral():
        return str(value.quantize(Decimal("1")))
    return format(value.normalize(), "f")
