"""Candidate shock/path objects for denominator-response admission."""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.model_artifact_store import (
    ArtifactManifestView,
    artifact_manifest_exists,
)
from ratewall.databook.tdcsim_cbo_contracts import (
    TDCSIM_CBO_SCENARIO_RUNS_DIR,
    tdcsim_cbo_curve_denominator_input_rows_from_directory,
)


SF_FED_EVENT_VECTOR = Path(
    "data/raw/policy_path_protocol_sources/"
    "sf_fed_monetary_policy_surprises_candidate_event_vector.csv"
)
CURRENT_TDCSIM_CBO_SUITE = TDCSIM_CBO_SCENARIO_RUNS_DIR
CURVE_DENOMINATOR_INPUT_CSV = (
    CURRENT_TDCSIM_CBO_SUITE / "ratewall_tdcsim_cbo_curve_denominator_input.csv"
)

DENOMINATOR_RESPONSE_PATH_OBJECT_FIELDS = [
    "denominator_response_path_object_candidate_id",
    "shock_object_id",
    "shock_object_kind",
    "source_event_id",
    "event_date",
    "quarter",
    "source_vintage",
    "source_publisher",
    "instrument_set",
    "instruments_present",
    "source_horizon_label_summary",
    "source_unit",
    "source_scalar_value",
    "converted_bp",
    "horizon_weight_years",
    "path_bps_year",
    "normalized_100bp_year_value",
    "source_unit_conversion_status",
    "horizon_mapping_status",
    "bps_year_integral_status",
    "replication_status",
    "information_shock_filter_status",
    "normalization_status",
    "admission_status",
    "denominator_response_requirement",
    "future_denominator_update_status",
    "canonical_promotion_gate",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

DENOMINATOR_RESPONSE_COEFFICIENT_ADMISSION_FIELDS = [
    "denominator_response_coefficient_decision_id",
    "target_outcome_id",
    "primary_horizon_q",
    "required_shock_object_kind",
    "path_object_candidate_count",
    "path_object_pass_count",
    "diagnostic_estimate_count",
    "primary_diagnostic_count",
    "primary_zero_crossing_count",
    "admitted_denominator_response_coefficient",
    "admitted_denominator_response_coefficient_unit",
    "coefficient_admission_status",
    "exact_blocker",
    "next_model_requirement",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

REQUIRED_POLICY_PATH_INSTRUMENTS = ("ED1", "ED2", "ED3", "ED4")
REVIEWED_SOURCE_UNIT_STATUS = "pass_reviewed_percentage_point_rate_change_source_text"
REVIEWED_SLOT_LABELS_BLOCKED_GRID_STATUS = (
    "blocked_slot_labels_reviewed_but_no_event_date_specific_horizon_grid"
)


@dataclass(frozen=True)
class PathObjectCandidate:
    source_event_id: str
    event_date: str
    quarter: str
    source_vintage: str
    source_publisher: str
    values: Mapping[str, Decimal]
    horizon_labels: Mapping[str, str]
    source_unit_conversion_status: str
    horizon_mapping_status: str
    bps_year_integral_status: str
    replication_status: str
    normalization_status: str


def denominator_response_path_object_rows_from_local_sources(
    event_vector_path: str | Path = SF_FED_EVENT_VECTOR,
) -> list[dict[str, str]]:
    """Build candidate policy-path rows from the local SF Fed event-vector CSV."""

    with Path(event_vector_path).open(encoding="utf-8-sig", newline="") as handle:
        return denominator_response_path_object_rows(csv.DictReader(handle))


def denominator_response_curve_path_object_rows_from_local_suite(
    curve_denominator_input_path: str | Path | None = None,
    *,
    suite_dir: str | Path = CURRENT_TDCSIM_CBO_SUITE,
) -> list[dict[str, str]]:
    """Build assumption-only curve-path rows from current TDCSim key-rate overlays."""

    if curve_denominator_input_path is None:
        return denominator_response_curve_path_object_rows(
            _default_curve_path_input_rows_for_path_object(
                tdcsim_cbo_curve_denominator_input_rows_from_directory(suite_dir)
            )
        )
    path = Path(curve_denominator_input_path)
    artifact = _artifact_view_for_path(path)
    if artifact is not None:
        logical_path = _artifact_logical_path(artifact, path)
        with artifact.open_text(logical_path) as handle:
            return denominator_response_curve_path_object_rows(csv.DictReader(handle))
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return denominator_response_curve_path_object_rows(csv.DictReader(handle))


def denominator_response_path_object_registry_rows_from_local_sources(
    *,
    event_vector_path: str | Path = SF_FED_EVENT_VECTOR,
    curve_denominator_input_path: str | Path | None = None,
    suite_dir: str | Path = CURRENT_TDCSIM_CBO_SUITE,
) -> list[dict[str, str]]:
    """Build the current combined policy-path and curve-path registry."""

    return [
        *denominator_response_path_object_rows_from_local_sources(event_vector_path),
        *denominator_response_curve_path_object_rows_from_local_suite(
            curve_denominator_input_path,
            suite_dir=suite_dir,
        ),
    ]


def denominator_response_path_object_rows(
    event_vector_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Aggregate ED1-ED4 source rows into blocked candidate path objects."""

    candidates = _policy_path_candidates(event_vector_rows)
    return [_path_object_row(candidate) for candidate in candidates]


def _artifact_view_for_path(path: Path) -> ArtifactManifestView | None:
    for candidate in (path, *path.parents):
        if artifact_manifest_exists(candidate):
            return ArtifactManifestView.from_root(candidate)
    return None


def _artifact_logical_path(artifact: ArtifactManifestView, path: Path) -> str:
    return path.relative_to(artifact.root).as_posix()


def denominator_response_curve_path_object_rows(
    curve_denominator_input_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Convert TDCSim 5y/10y/30y curve overlays into assumption-only path rows."""

    return [
        _curve_path_object_row(row)
        for row in curve_denominator_input_rows
        if row.get("scenario_id")
    ]


def _default_curve_path_input_rows_for_path_object(
    rows: Iterable[Mapping[str, str]],
) -> list[Mapping[str, str]]:
    return [
        row
        for row in rows
        if row.get("comparison_group")
        in {"baseline", "shorter_issuance", "longer_issuance", "primary_deficit"}
    ]


def denominator_response_coefficient_admission_rows(
    *,
    diagnostic_rows: Iterable[Mapping[str, str]],
    path_object_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return the current denominator-response coefficient admission decision."""

    diagnostics = list(diagnostic_rows)
    paths = list(path_object_rows)
    primary_diagnostics = [
        row
        for row in diagnostics
        if row.get("horizon_q") == "4"
        and row.get("outcome_object_id")
        == "share_weighted_real_fspdp_level_response_gdp_share_pp"
    ]
    path_pass_count = sum(
        row.get("normalization_status") == "pass_reviewed_100bp_year_path"
        and row.get("admission_status") == "admitted_path_object"
        for row in paths
    )
    zero_crossing_count = sum(_diagnostic_ci_crosses_zero(row) for row in primary_diagnostics)
    blockers = []
    if path_pass_count == 0:
        blockers.append("no_reviewed_100bp_year_path_object")
    if not primary_diagnostics:
        blockers.append("no_primary_h4_share_weighted_fspdp_diagnostic")
    if zero_crossing_count:
        blockers.append("primary_h4_confidence_interval_crosses_zero")
    if not blockers:
        blockers.append("coefficient_requires_manual_owner_admission")
    return [
        {
            "denominator_response_coefficient_decision_id": (
                "denominator_response_coefficient::current_admission_status"
            ),
            "target_outcome_id": (
                "share_weighted_real_fspdp_level_response_gdp_share_pp"
            ),
            "primary_horizon_q": "4",
            "required_shock_object_kind": (
                "reviewed_policy_path_or_curve_path_100bp_year"
            ),
            "path_object_candidate_count": str(len(paths)),
            "path_object_pass_count": str(path_pass_count),
            "diagnostic_estimate_count": str(len(diagnostics)),
            "primary_diagnostic_count": str(len(primary_diagnostics)),
            "primary_zero_crossing_count": str(zero_crossing_count),
            "admitted_denominator_response_coefficient": "",
            "admitted_denominator_response_coefficient_unit": "",
            "coefficient_admission_status": (
                "no_admitted_denominator_response_coefficient"
            ),
            "exact_blocker": ";".join(blockers),
            "next_model_requirement": (
                "reviewed_100bp_year_path_object_and_nonzero_h4_response"
            ),
            "allowed_use": "denominator_response_admission_status_only",
            "blocked_use": (
                "canonical_headline_promotion;denominator_recalibration;"
                "default_runtime_anchor;evidence_mode_claim;"
                "causal_market_yield_estimate;denominator_prior_update;"
                "path_ratio_denominator_replacement;release_headline_claim;"
                "empirical_denominator_response_claim"
            ),
            "canonical_ratio_entry": "false",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "denominator_prior_update_allowed": "false",
        }
    ]


def write_denominator_response_path_object_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    return _write_csv(path, rows, DENOMINATOR_RESPONSE_PATH_OBJECT_FIELDS)


def write_denominator_response_coefficient_admission_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    return _write_csv(path, rows, DENOMINATOR_RESPONSE_COEFFICIENT_ADMISSION_FIELDS)


def _policy_path_candidates(
    event_vector_rows: Iterable[Mapping[str, str]],
) -> list[PathObjectCandidate]:
    events: dict[str, dict[str, Mapping[str, str]]] = defaultdict(dict)
    for row in event_vector_rows:
        if row.get("source_sheet_vintage") != "update_2023":
            continue
        instrument = row.get("instrument_code", "")
        if instrument not in REQUIRED_POLICY_PATH_INSTRUMENTS:
            continue
        event_id = row.get("event_id", "")
        if not event_id or _decimal_or_none(row.get("source_reported_value_numeric")) is None:
            continue
        events[event_id][instrument] = row

    candidates: list[PathObjectCandidate] = []
    for event_id, rows_by_instrument in sorted(events.items()):
        if tuple(sorted(rows_by_instrument)) != REQUIRED_POLICY_PATH_INSTRUMENTS:
            continue
        rows = [rows_by_instrument[instrument] for instrument in REQUIRED_POLICY_PATH_INSTRUMENTS]
        event_date = str(rows[0].get("event_date", ""))
        candidates.append(
            PathObjectCandidate(
                source_event_id=event_id,
                event_date=event_date,
                quarter=_quarter_from_date(event_date),
                source_vintage=str(rows[0].get("source_sheet_vintage", "")),
                source_publisher=str(rows[0].get("source_publisher", "")),
                values={
                    instrument: _decimal_or_none(
                        rows_by_instrument[instrument].get(
                            "source_reported_value_numeric"
                        )
                    )
                    or Decimal("0")
                    for instrument in REQUIRED_POLICY_PATH_INSTRUMENTS
                },
                horizon_labels={
                    instrument: str(
                        rows_by_instrument[instrument].get("source_horizon_label", "")
                    )
                    for instrument in REQUIRED_POLICY_PATH_INSTRUMENTS
                },
                source_unit_conversion_status=REVIEWED_SOURCE_UNIT_STATUS,
                horizon_mapping_status=REVIEWED_SLOT_LABELS_BLOCKED_GRID_STATUS,
                bps_year_integral_status=_combine_status(
                    row.get("bps_year_integral_status", "") for row in rows
                ),
                replication_status=_combine_status(
                    row.get("replication_status", "") for row in rows
                ),
                normalization_status=_combine_status(
                    row.get("policy_path_100bp_year_normalization_status", "")
                    for row in rows
                ),
            )
        )
    return candidates


def _path_object_row(candidate: PathObjectCandidate) -> dict[str, str]:
    source_scalar_value = sum(candidate.values.values(), Decimal("0"))
    converted_bp = source_scalar_value * Decimal("100")
    blocker = (
        "ED1-ED4 event-strip rows are source-backed candidate policy-path inputs, "
        "but the scalar is a derived unweighted ED slot sum, not the official SF Fed "
        "monetary-policy-surprise object. Source-unit review supports percentage-point "
        "rate changes convertible to basis points. Event-date horizon mapping, "
        "bps-year integration, independent replication, and information-shock "
        "filtering have not passed. This row cannot admit a denominator coefficient."
    )
    return {
        "denominator_response_path_object_candidate_id": (
            "denominator_response_path_object::policy_path::"
            f"{candidate.source_event_id}"
        ),
        "shock_object_id": "sf_fed_update_2023_ed1_ed4_policy_path_candidate",
        "shock_object_kind": "policy_path_100bp_year_candidate",
        "source_event_id": candidate.source_event_id,
        "event_date": candidate.event_date,
        "quarter": candidate.quarter,
        "source_vintage": candidate.source_vintage,
        "source_publisher": candidate.source_publisher,
        "instrument_set": ";".join(REQUIRED_POLICY_PATH_INSTRUMENTS),
        "instruments_present": ";".join(candidate.values),
        "source_horizon_label_summary": ";".join(
            f"{instrument}={candidate.horizon_labels.get(instrument, '')}"
            for instrument in REQUIRED_POLICY_PATH_INSTRUMENTS
        ),
        "source_unit": (
            "derived_unweighted_ed_slot_sum_percentage_point_rate_change_30_min_window_"
            "not_sf_fed_mps"
        ),
        "source_scalar_value": _format_decimal(source_scalar_value),
        "converted_bp": _format_decimal(converted_bp),
        "horizon_weight_years": "",
        "path_bps_year": "",
        "normalized_100bp_year_value": "",
        "source_unit_conversion_status": candidate.source_unit_conversion_status,
        "horizon_mapping_status": candidate.horizon_mapping_status,
        "bps_year_integral_status": candidate.bps_year_integral_status,
        "replication_status": candidate.replication_status,
        "information_shock_filter_status": "blocked_no_information_shock_filter",
        "normalization_status": candidate.normalization_status,
        "admission_status": "candidate_only_blocked",
        "denominator_response_requirement": (
            "blocked_until_reviewed_path_and_admitted_coefficient"
        ),
        "future_denominator_update_status": (
            "policy_path_candidate_not_ready_for_denominator_update"
        ),
        "canonical_promotion_gate": (
            "requires_reviewed_100bp_year_path_and_admitted_denominator_"
            "response_coefficient"
        ),
        "exact_blocker": blocker,
        "allowed_use": "policy_path_object_prerequisite_diagnostic_only",
        "blocked_use": (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "path_ratio_denominator_replacement;release_headline_claim;"
            "empirical_denominator_response_claim"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
    }


def _curve_path_object_row(row: Mapping[str, str]) -> dict[str, str]:
    scenario_id = str(row.get("scenario_id", ""))
    fiscal_year = str(row.get("fiscal_year", ""))
    effective_overlay = _decimal_or_none(row.get("effective_curve_overlay_bp"))
    overlay_5y = _decimal_or_none(row.get("curve_overlay_5y_bp"))
    overlay_10y = _decimal_or_none(row.get("curve_overlay_10y_bp"))
    overlay_30y = _decimal_or_none(row.get("curve_overlay_30y_bp"))
    weight_5y = _decimal_or_none(row.get("curve_weight_5y"))
    weight_10y = _decimal_or_none(row.get("curve_weight_10y"))
    weight_30y = _decimal_or_none(row.get("curve_weight_30y"))
    path_bps_year = effective_overlay if effective_overlay is not None else None
    normalized = (
        path_bps_year / Decimal("100")
        if path_bps_year is not None
        else None
    )
    denominator_requirement = _curve_denominator_response_requirement(
        path_bps_year
    )
    future_update_status = _curve_future_denominator_update_status(path_bps_year)
    blocker = (
        "TDCSim scenario rows provide explicit 5y/10y/30y nominal key-rate "
        "overlays and fixed effective-curve weights. This is a scenario curve "
        "path for nonempirical assumption bounds only. A nonzero scenario rate "
        "path must not be promoted canonically with frozen D unless a later "
        "coefficient admission or explicit zero-response proof says otherwise."
    )
    return {
        "denominator_response_path_object_candidate_id": (
            "denominator_response_path_object::curve_path::"
            f"{fiscal_year}::{scenario_id}"
        ),
        "shock_object_id": "tdcsim_cbo_key_rate_curve_overlay_candidate",
        "shock_object_kind": "curve_path_100bp_year_assumption_candidate",
        "source_event_id": scenario_id,
        "event_date": "",
        "quarter": "",
        "source_vintage": "current_tdcsim_cbo_suite_manifest_backed",
        "source_publisher": "TDCSim scenario package consumed by RateWall",
        "instrument_set": "5y;10y;30y",
        "instruments_present": _present_curve_instruments(overlay_5y, overlay_10y, overlay_30y),
        "source_horizon_label_summary": (
            f"5y_weight={_format_decimal_or_blank(weight_5y)};"
            f"10y_weight={_format_decimal_or_blank(weight_10y)};"
            f"30y_weight={_format_decimal_or_blank(weight_30y)}"
        ),
        "source_unit": "basis_point_nominal_treasury_key_rate_overlay",
        "source_scalar_value": _format_decimal_or_blank(effective_overlay),
        "converted_bp": _format_decimal_or_blank(effective_overlay),
        "horizon_weight_years": "1",
        "path_bps_year": _format_decimal_or_blank(path_bps_year),
        "normalized_100bp_year_value": _format_decimal_or_blank(normalized),
        "source_unit_conversion_status": "pass_source_unit_basis_points",
        "horizon_mapping_status": (
            "pass_assumption_mode_h4_one_year_curve_overlay_horizon"
        ),
        "bps_year_integral_status": (
            "pass_assumption_mode_effective_bp_times_one_year"
        ),
        "replication_status": str(
            row.get("curve_overlay_key_rate_source_status", "")
        ),
        "information_shock_filter_status": (
            "not_applicable_tdcsim_scenario_curve_overlay"
        ),
        "normalization_status": (
            "pass_assumption_mode_100bp_year_curve_path_not_empirical"
        ),
        "admission_status": "assumption_path_only_not_empirical",
        "denominator_response_requirement": denominator_requirement,
        "future_denominator_update_status": future_update_status,
        "canonical_promotion_gate": (
            "requires_admitted_curve_denominator_response_coefficient_or_"
            "explicit_zero_response_proof"
        ),
        "exact_blocker": blocker,
        "allowed_use": "curve_path_assumption_bounds_only",
        "blocked_use": (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "path_ratio_denominator_replacement;release_headline_claim;"
            "empirical_denominator_response_claim"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
    }


def _present_curve_instruments(
    overlay_5y: Decimal | None,
    overlay_10y: Decimal | None,
    overlay_30y: Decimal | None,
) -> str:
    values = {
        "5y": overlay_5y,
        "10y": overlay_10y,
        "30y": overlay_30y,
    }
    return ";".join(name for name, value in values.items() if value is not None)


def _curve_denominator_response_requirement(path_bps_year: Decimal | None) -> str:
    if path_bps_year is None:
        return "blocked_missing_curve_path"
    if path_bps_year == 0:
        return "not_required_zero_curve_overlay"
    return "required_before_canonical_promotion"


def _curve_future_denominator_update_status(path_bps_year: Decimal | None) -> str:
    if path_bps_year is None:
        return "missing_curve_path_no_denominator_update_possible"
    if path_bps_year == 0:
        return "zero_rate_path_frozen_D_consistent"
    return "rate_shock_captured_coefficient_not_admitted"


def _diagnostic_ci_crosses_zero(row: Mapping[str, str]) -> bool:
    low = _decimal_or_none(row.get("ci95_low_hac"))
    high = _decimal_or_none(row.get("ci95_high_hac"))
    if low is None or high is None:
        return True
    return low <= 0 <= high


def _combine_status(values: Iterable[str]) -> str:
    unique = sorted({value for value in values if value})
    if not unique:
        return "blocked_missing_status"
    return unique[0] if len(unique) == 1 else ";".join(unique)


def _write_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
    fields: list[str],
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return out


def _quarter_from_date(value: str) -> str:
    if len(value) < 7:
        return ""
    try:
        year = int(value[:4])
        month = int(value[5:7])
    except ValueError:
        return ""
    if not 1 <= month <= 12:
        return ""
    return f"{year}Q{((month - 1) // 3) + 1}"


def _decimal_or_none(value: object) -> Decimal | None:
    if value in {None, ""}:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _format_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _format_decimal_or_blank(value: Decimal | None) -> str:
    return "" if value is None else _format_decimal(value)
