"""Admission registry for curve-to-denominator response coefficients."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation

from ratewall.databook.denominator_response_application import COEFFICIENT_UNIT


DENOMINATOR_RESPONSE_COEFFICIENT_PROFILE_FIELDS = [
    "denominator_response_profile_id",
    "profile_role",
    "target_outcome_id",
    "response_horizon",
    "denominator_response_coefficient",
    "denominator_response_coefficient_unit",
    "coefficient_admission_status",
    "coefficient_source_status",
    "coefficient_source_id",
    "shock_family",
    "path_construction",
    "tenor_weights",
    "horizon_integration",
    "source_estimate",
    "source_estimate_unit",
    "source_sample",
    "coefficient_uncertainty",
    "sign_convention",
    "fspdp_gdp_to_d_conversion",
    "path_object_candidate_count",
    "path_object_pass_count",
    "diagnostic_estimate_count",
    "primary_diagnostic_count",
    "primary_zero_crossing_count",
    "local_diagnostic_admission_status",
    "external_profile_review_status",
    "final_version_promotion_status",
    "exact_blocker",
    "next_model_requirement",
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

ADMITTED_PROFILE_STATUSES = {
    "admitted_curve_denominator_response_coefficient",
    "admitted_noncanonical_curve_denominator_response_coefficient",
}
PRIMARY_OUTCOME_ID = "share_weighted_real_fspdp_level_response_gdp_share_pp"
PRIMARY_HORIZON_Q = "4"
PRIMARY_RESPONSE_HORIZON = "annual_h4_one_year"

ADMITTED_SOURCE_STATUSES = {
    "reviewed_literature_calibrated_profile",
    "reviewed_econometric_estimate_profile",
    "owner_admitted_explicit_assumption_profile",
}

REQUIRED_ADMITTED_METADATA_FIELDS = [
    "coefficient_source_id",
    "shock_family",
    "path_construction",
    "tenor_weights",
    "horizon_integration",
    "source_estimate",
    "source_estimate_unit",
    "source_sample",
    "coefficient_uncertainty",
    "sign_convention",
    "fspdp_gdp_to_d_conversion",
]
OWNER_THETA0125_PROFILE_ID = (
    "curve_denominator_response::owner_theta0125_h4_20260627"
)
OWNER_THETA0125_COEFFICIENT = "0.125"
OWNER_THETA0125_IMPLIED_DRAG_PP_GDP = "0.097"
OWNER_THETA0125_D_SHARE_PP = "0.776"
FRBUS_STRUCTURAL_PROFILE_ID = (
    "curve_denominator_response::frbus_structural_term_premium_h4_20260627"
)
FRBUS_STRUCTURAL_COEFFICIENT = "1.1198692004749646"
FRBUS_STRUCTURAL_BETA_PP_GDP = "-0.8690184995685726"
FRBUS_STRUCTURAL_D_SHARE_PP = "0.776"
FRBUS_STRUCTURAL_PATH_BPS_YEAR = "100.00000000347879"
FRBUS_STRUCTURAL_SHOCK_SCALE = "0.4564213835876753"


class DenominatorResponseCoefficientError(ValueError):
    """Raised when a coefficient profile is internally inconsistent."""


def denominator_response_coefficient_profile_rows(
    *,
    diagnostic_rows: Iterable[Mapping[str, str]],
    path_object_rows: Iterable[Mapping[str, str]],
    candidate_profiles: Iterable[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Build admitted or blocked coefficient profiles from explicit evidence."""

    diagnostics = list(diagnostic_rows)
    paths = list(path_object_rows)
    candidates = list(candidate_profiles)
    context = _evidence_context(diagnostics, paths)
    rows = [_blocked_local_evidence_row(context)]
    rows.extend(_candidate_profile_row(row, context=context) for row in candidates)
    return rows


def selected_denominator_response_coefficient_profile(
    rows: Iterable[Mapping[str, str]],
) -> dict[str, str]:
    """Return the sole admitted coefficient profile, failing closed otherwise."""

    admitted = [
        dict(row)
        for row in rows
        if row.get("coefficient_admission_status") in ADMITTED_PROFILE_STATUSES
    ]
    if len(admitted) != 1:
        raise DenominatorResponseCoefficientError(
            f"expected exactly one admitted denominator response profile, found {len(admitted)}"
        )
    return admitted[0]


def owner_admitted_curve_denominator_response_candidate_profile() -> dict[str, str]:
    """Return the owner-admitted Assumption Mode coefficient candidate."""

    return {
        "denominator_response_profile_id": OWNER_THETA0125_PROFILE_ID,
        "profile_role": "base_final_assumption_mode_profile",
        "target_outcome_id": PRIMARY_OUTCOME_ID,
        "response_horizon": PRIMARY_RESPONSE_HORIZON,
        "denominator_response_coefficient": OWNER_THETA0125_COEFFICIENT,
        "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
        "coefficient_admission_status": (
            "admitted_noncanonical_curve_denominator_response_coefficient"
        ),
        "coefficient_source_status": "owner_admitted_explicit_assumption_profile",
        "coefficient_source_id": (
            "owner_assumption::curve_D_theta_base_0p125_bounds_0_0p25::"
            "2026-06-27"
        ),
        "shock_family": "tdcsim_cbo_effective_curve_5y10y30y_100bp_year",
        "path_construction": (
            "path_bps_year = 1yr * (0.25*curve_overlay_5y_bp + "
            "0.50*curve_overlay_10y_bp + 0.25*curve_overlay_30y_bp)"
        ),
        "tenor_weights": "5y=0.25;10y=0.50;30y=0.25",
        "horizon_integration": (
            "annual_h4_one_year_bps_year; current TDCSim/CBO overlays "
            "treated as one-year effective paths"
        ),
        "source_estimate": f"-{OWNER_THETA0125_IMPLIED_DRAG_PP_GDP}",
        "source_estimate_unit": (
            "owner_assumed_ppGDP_drag_equivalent_per_100bp_year_implied_by_"
            "cD_0p125_and_D_share_pp_0p776"
        ),
        "source_sample": (
            "none_owner_admitted_assumption; macro evidence supports sign only"
        ),
        "coefficient_uncertainty": (
            "owner_sensitivity_bounds_cD=[0,0.25]; "
            "selected_base_cD=0.125; "
            "lower_zero_is_sensitivity_not_zero_response_proof"
        ),
        "sign_convention": (
            "positive_effective_curve_overlay_is_contractionary_and_increases_D"
        ),
        "fspdp_gdp_to_d_conversion": (
            "c_D = owner_drag_ppGDP_per_100bp_year / D_share_pp = "
            f"{OWNER_THETA0125_IMPLIED_DRAG_PP_GDP} / "
            f"{OWNER_THETA0125_D_SHARE_PP} = {OWNER_THETA0125_COEFFICIENT}"
        ),
    }


def frbus_structural_curve_denominator_response_candidate_profile() -> dict[str, str]:
    """Return the FRB/US structural benchmark coefficient candidate."""

    return {
        "denominator_response_profile_id": FRBUS_STRUCTURAL_PROFILE_ID,
        "profile_role": "base_structural_benchmark_profile",
        "target_outcome_id": PRIMARY_OUTCOME_ID,
        "response_horizon": PRIMARY_RESPONSE_HORIZON,
        "denominator_response_coefficient": FRBUS_STRUCTURAL_COEFFICIENT,
        "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
        "coefficient_admission_status": (
            "admitted_noncanonical_curve_denominator_response_coefficient"
        ),
        "coefficient_source_status": "reviewed_literature_calibrated_profile",
        "coefficient_source_id": (
            "frbus_structural_benchmark::rg5p_rg10p_rg30p_scaled_"
            "100bp_year::2026-06-27"
        ),
        "shock_family": "frbus_structural_5y10y30y_term_premium_100bp_year",
        "path_construction": (
            "FRB/US pyfrbus 1.1.1 LONGBASE simulation; add "
            f"{FRBUS_STRUCTURAL_SHOCK_SCALE} pp to rg5p_aerr, rg10p_aerr, "
            "and rg30p_aerr in 2040Q1-2040Q4 so the effective path "
            f"equals {FRBUS_STRUCTURAL_PATH_BPS_YEAR} bp-year"
        ),
        "tenor_weights": "RG5=0.25;RG10=0.50;RG30=0.25",
        "horizon_integration": (
            "annual_h4_one_year_bps_year; effective path is "
            "0.25*RG5 + 0.50*RG10 + 0.25*RG30 over the first four quarters"
        ),
        "source_estimate": FRBUS_STRUCTURAL_BETA_PP_GDP,
        "source_estimate_unit": (
            "frbus_structural_ppGDP_FSPDP_like_response_per_100bp_year"
        ),
        "source_sample": (
            "official_frbus_pyfrbus_1.1.1_LONGBASE_2040Q1_structural_"
            "term_premium_simulation"
        ),
        "coefficient_uncertainty": (
            "structural_benchmark_no_sampling_ci; local econometric estimate "
            "not admitted; owner sensitivity cD=[0,0.25] retained separately"
        ),
        "sign_convention": (
            "positive_effective_curve_overlay_is_contractionary_and_increases_D"
        ),
        "fspdp_gdp_to_d_conversion": (
            "c_D = -beta_ppGDP_per_100bp_year / D_share_pp = "
            f"{FRBUS_STRUCTURAL_BETA_PP_GDP} / -{FRBUS_STRUCTURAL_D_SHARE_PP} "
            f"= {FRBUS_STRUCTURAL_COEFFICIENT}"
        ),
    }


def owner_admitted_curve_denominator_response_profile_rows(
    *,
    diagnostic_rows: Iterable[Mapping[str, str]],
    path_object_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Build T9 rows with the selected owner-admitted Assumption Mode profile."""

    return denominator_response_coefficient_profile_rows(
        diagnostic_rows=diagnostic_rows,
        path_object_rows=path_object_rows,
        candidate_profiles=[owner_admitted_curve_denominator_response_candidate_profile()],
    )


def frbus_structural_curve_denominator_response_profile_rows(
    *,
    diagnostic_rows: Iterable[Mapping[str, str]],
    path_object_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Build T9 rows with the selected FRB/US structural benchmark profile."""

    return denominator_response_coefficient_profile_rows(
        diagnostic_rows=diagnostic_rows,
        path_object_rows=path_object_rows,
        candidate_profiles=[frbus_structural_curve_denominator_response_candidate_profile()],
    )


def selected_owner_admitted_curve_denominator_response_profile(
    *,
    diagnostic_rows: Iterable[Mapping[str, str]],
    path_object_rows: Iterable[Mapping[str, str]],
) -> dict[str, str]:
    """Select the sole owner-admitted profile through the T9 gate."""

    return selected_denominator_response_coefficient_profile(
        owner_admitted_curve_denominator_response_profile_rows(
            diagnostic_rows=diagnostic_rows,
            path_object_rows=path_object_rows,
        )
    )


def selected_frbus_structural_curve_denominator_response_profile(
    *,
    diagnostic_rows: Iterable[Mapping[str, str]],
    path_object_rows: Iterable[Mapping[str, str]],
) -> dict[str, str]:
    """Select the sole FRB/US structural profile through the T9 gate."""

    return selected_denominator_response_coefficient_profile(
        frbus_structural_curve_denominator_response_profile_rows(
            diagnostic_rows=diagnostic_rows,
            path_object_rows=path_object_rows,
        )
    )


def _evidence_context(
    diagnostics: list[Mapping[str, str]],
    paths: list[Mapping[str, str]],
) -> dict[str, str]:
    primary = [
        row
        for row in diagnostics
        if row.get("horizon_q") == PRIMARY_HORIZON_Q
        and row.get("outcome_object_id") == PRIMARY_OUTCOME_ID
    ]
    path_pass_count = sum(
        row.get("normalization_status") == "pass_reviewed_100bp_year_path"
        and row.get("admission_status") == "admitted_path_object"
        for row in paths
    )
    zero_crossing_count = sum(_diagnostic_ci_crosses_zero(row) for row in primary)
    blockers: list[str] = []
    if path_pass_count == 0:
        blockers.append("no_reviewed_100bp_year_path_object")
    if not primary:
        blockers.append("no_primary_h4_share_weighted_fspdp_diagnostic")
    if zero_crossing_count:
        blockers.append("primary_h4_confidence_interval_crosses_zero")
    if not blockers:
        blockers.append("external_or_owner_profile_required_for_final_admission")
    return {
        "path_object_candidate_count": str(len(paths)),
        "path_object_pass_count": str(path_pass_count),
        "diagnostic_estimate_count": str(len(diagnostics)),
        "primary_diagnostic_count": str(len(primary)),
        "primary_zero_crossing_count": str(zero_crossing_count),
        "exact_blocker": ";".join(blockers),
    }


def _blocked_local_evidence_row(context: Mapping[str, str]) -> dict[str, str]:
    return {
        "denominator_response_profile_id": "curve_denominator_response::local_evidence_blocked",
        "profile_role": "local_evidence_status",
        "target_outcome_id": PRIMARY_OUTCOME_ID,
        "response_horizon": "annual_h4_one_year",
        "denominator_response_coefficient": "",
        "denominator_response_coefficient_unit": "",
        "coefficient_admission_status": "no_admitted_curve_denominator_response_coefficient",
        "coefficient_source_status": "local_diagnostics_not_sufficient_for_admission",
        "coefficient_source_id": "",
        "shock_family": "",
        "path_construction": "",
        "tenor_weights": "",
        "horizon_integration": "",
        "source_estimate": "",
        "source_estimate_unit": "",
        "source_sample": "",
        "coefficient_uncertainty": "",
        "sign_convention": (
            "positive_effective_curve_overlay_is_contractionary_and_increases_D"
        ),
        "fspdp_gdp_to_d_conversion": "",
        "path_object_candidate_count": context["path_object_candidate_count"],
        "path_object_pass_count": context["path_object_pass_count"],
        "diagnostic_estimate_count": context["diagnostic_estimate_count"],
        "primary_diagnostic_count": context["primary_diagnostic_count"],
        "primary_zero_crossing_count": context["primary_zero_crossing_count"],
        "local_diagnostic_admission_status": "blocked_local_diagnostic_only",
        "external_profile_review_status": "not_supplied",
        "final_version_promotion_status": "blocked_missing_admitted_coefficient_profile",
        "exact_blocker": context["exact_blocker"],
        "next_model_requirement": (
            "admit_literature_or_econometric_curve_to_denominator_profile"
        ),
        "allowed_use": "coefficient_gap_status_for_model_completion",
        "blocked_use": (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "path_ratio_denominator_replacement;release_headline_claim;"
            "moving_D_application_for_nonzero_rate_paths"
        ),
        "claim_boundary": (
            "local_diagnostics_do_not_admit_curve_sensitive_denominator"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
    }


def _candidate_profile_row(
    candidate: Mapping[str, str],
    *,
    context: Mapping[str, str],
) -> dict[str, str]:
    profile_id = _required(candidate, "denominator_response_profile_id")
    coefficient = _decimal(_required(candidate, "denominator_response_coefficient"))
    unit = _required(candidate, "denominator_response_coefficient_unit")
    status = _required(candidate, "coefficient_admission_status")
    source_status = _required(candidate, "coefficient_source_status")
    if coefficient < 0:
        raise DenominatorResponseCoefficientError(
            f"negative denominator response coefficient for {profile_id}"
        )
    if unit != COEFFICIENT_UNIT:
        raise DenominatorResponseCoefficientError(
            f"unsupported denominator response coefficient unit for {profile_id}: {unit}"
        )
    admitted = status in ADMITTED_PROFILE_STATUSES
    target_outcome = candidate.get("target_outcome_id", PRIMARY_OUTCOME_ID)
    response_horizon = candidate.get("response_horizon", PRIMARY_RESPONSE_HORIZON)
    if admitted:
        _validate_admitted_profile_metadata(
            candidate,
            profile_id=profile_id,
            source_status=source_status,
            target_outcome=target_outcome,
            response_horizon=response_horizon,
        )
    return {
        "denominator_response_profile_id": profile_id,
        "profile_role": candidate.get("profile_role", "candidate_profile"),
        "target_outcome_id": target_outcome,
        "response_horizon": response_horizon,
        "denominator_response_coefficient": _fmt(coefficient),
        "denominator_response_coefficient_unit": unit,
        "coefficient_admission_status": status,
        "coefficient_source_status": source_status,
        "coefficient_source_id": candidate.get("coefficient_source_id", ""),
        "shock_family": candidate.get("shock_family", ""),
        "path_construction": candidate.get("path_construction", ""),
        "tenor_weights": candidate.get("tenor_weights", ""),
        "horizon_integration": candidate.get("horizon_integration", ""),
        "source_estimate": candidate.get("source_estimate", ""),
        "source_estimate_unit": candidate.get("source_estimate_unit", ""),
        "source_sample": candidate.get("source_sample", ""),
        "coefficient_uncertainty": candidate.get("coefficient_uncertainty", ""),
        "sign_convention": candidate.get("sign_convention", ""),
        "fspdp_gdp_to_d_conversion": candidate.get(
            "fspdp_gdp_to_d_conversion", ""
        ),
        "path_object_candidate_count": context["path_object_candidate_count"],
        "path_object_pass_count": context["path_object_pass_count"],
        "diagnostic_estimate_count": context["diagnostic_estimate_count"],
        "primary_diagnostic_count": context["primary_diagnostic_count"],
        "primary_zero_crossing_count": context["primary_zero_crossing_count"],
        "local_diagnostic_admission_status": "local_diagnostics_context_only",
        "external_profile_review_status": (
            _external_profile_review_status(source_status)
            if admitted
            else "candidate_not_admitted"
        ),
        "final_version_promotion_status": (
            _final_version_promotion_status(source_status)
            if admitted
            else "blocked_candidate_profile_not_admitted"
        ),
        "exact_blocker": (
            "n/a" if admitted else "candidate_profile_not_admitted"
        ),
        "next_model_requirement": (
            "apply_profile_to_T8_moving_D_bridge"
            if admitted
            else "upgrade_candidate_to_reviewed_admitted_profile"
        ),
        "allowed_use": (
            _allowed_use(source_status)
            if admitted
            else "candidate_coefficient_review_only"
        ),
        "blocked_use": (
            _admitted_blocked_use(source_status)
            if admitted
            else (
                "canonical_headline_promotion;denominator_recalibration;"
                "path_ratio_denominator_replacement;release_headline_claim;"
                "moving_D_application_for_nonzero_rate_paths"
            )
        ),
        "claim_boundary": (
            _claim_boundary(source_status)
            if admitted
            else "candidate_profile_not_admitted_to_D"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
    }


def _external_profile_review_status(source_status: str) -> str:
    if source_status == "owner_admitted_explicit_assumption_profile":
        return "pass_owner_assumption_profile_supplied"
    return "pass_reviewed_profile_supplied"


def _final_version_promotion_status(source_status: str) -> str:
    if source_status == "owner_admitted_explicit_assumption_profile":
        return "ready_for_final_version_assumption_mode_moving_D_scenario_rows"
    if source_status == "reviewed_literature_calibrated_profile":
        return "ready_for_final_version_assumption_mode_structural_moving_D_route"
    return "ready_for_moving_D_model_scenario_gate_not_headline"


def _allowed_use(source_status: str) -> str:
    if source_status == "owner_admitted_explicit_assumption_profile":
        return "final_version_assumption_mode_moving_D_scenario_rows"
    if source_status == "reviewed_literature_calibrated_profile":
        return "final_version_assumption_mode_structural_moving_D_scenario_rows"
    return "moving_D_coefficient_profile_for_scenario_sidecar"


def _admitted_blocked_use(source_status: str) -> str:
    if source_status == "owner_admitted_explicit_assumption_profile":
        return (
            "empirical_estimate_claim;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "runtime_denominator_recalibration;formula_replacement;"
            "path_ratio_denominator_replacement;"
            "release_headline_claim_without_separate_owner_gate"
        )
    if source_status == "reviewed_literature_calibrated_profile":
        return (
            "empirical_same_axis_treasury_evidence_claim;"
            "local_econometric_estimate_claim;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "runtime_denominator_recalibration;formula_replacement;"
            "path_ratio_denominator_replacement;"
            "release_headline_claim_without_separate_owner_gate"
        )
    return (
        "canonical_headline_promotion_without_separate_owner_gate;"
        "release_headline_claim_without_separate_owner_gate"
    )


def _claim_boundary(source_status: str) -> str:
    if source_status == "owner_admitted_explicit_assumption_profile":
        return (
            "owner_admitted_final_version_assumption_mode_coefficient_moves_D_"
            "for_rate_changing_scenarios;not_empirical_estimate;"
            "not_denominator_prior_update;not_evidence_mode;"
            "not_causal_market_yield_estimate"
        )
    if source_status == "reviewed_literature_calibrated_profile":
        return (
            "final_version_assumption_mode_structural_coefficient_moves_D_for_"
            "rate_changing_scenarios;not_empirical_same_axis_treasury_evidence;"
            "not_local_econometric_estimate;not_denominator_prior_update;"
            "not_evidence_mode;not_causal_market_yield_estimate"
        )
    return "admitted_profile_moves_D_in_scenario_sidecar_not_runtime_replacement"


def _validate_admitted_profile_metadata(
    candidate: Mapping[str, str],
    *,
    profile_id: str,
    source_status: str,
    target_outcome: str,
    response_horizon: str,
) -> None:
    if source_status not in ADMITTED_SOURCE_STATUSES:
        raise DenominatorResponseCoefficientError(
            f"admitted profile lacks reviewed source status: {profile_id}"
        )
    if target_outcome != PRIMARY_OUTCOME_ID:
        raise DenominatorResponseCoefficientError(
            f"admitted profile uses unsupported target outcome: {profile_id}"
        )
    if response_horizon != PRIMARY_RESPONSE_HORIZON:
        raise DenominatorResponseCoefficientError(
            f"admitted profile uses unsupported response horizon: {profile_id}"
        )
    missing = [
        field
        for field in REQUIRED_ADMITTED_METADATA_FIELDS
        if not str(candidate.get(field, ""))
    ]
    if missing:
        raise DenominatorResponseCoefficientError(
            "admitted profile lacks required metadata for "
            f"{profile_id}: {';'.join(missing)}"
        )


def _diagnostic_ci_crosses_zero(row: Mapping[str, str]) -> bool:
    low = _decimal_or_none(row.get("ci95_low_hac"))
    high = _decimal_or_none(row.get("ci95_high_hac"))
    if low is None or high is None:
        return True
    return low <= 0 <= high


def _required(row: Mapping[str, str], field: str) -> str:
    value = str(row.get(field, ""))
    if not value:
        raise DenominatorResponseCoefficientError(f"missing required field: {field}")
    return value


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DenominatorResponseCoefficientError(
            f"invalid decimal value: {value}"
        ) from exc


def _decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _fmt(value: Decimal) -> str:
    if value == value.to_integral():
        return str(value.quantize(Decimal("1")))
    return format(value.normalize(), "f")
