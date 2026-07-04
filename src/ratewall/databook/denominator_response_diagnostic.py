"""Diagnostic denominator-response estimates from local source snapshots."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.sources.base import SourceSnapshot


CURRENT_DEMAND_GDP_SHARE_SNAPSHOT = Path(
    "data/raw/current_demand_gdp_share/current_demand_gdp_share_snapshot.json"
)
RATEWALL_SNAPSHOT = Path("data/raw/ratewall_snapshot.json")
SF_FED_EVENT_VECTOR = Path(
    "data/raw/policy_path_protocol_sources/"
    "sf_fed_monetary_policy_surprises_candidate_event_vector.csv"
)

DENOMINATOR_RESPONSE_DIAGNOSTIC_FIELDS = [
    "denominator_response_diagnostic_row_id",
    "estimator_id",
    "horizon_q",
    "target_outcome_id",
    "outcome_object_id",
    "outcome_unit",
    "primary_admission_horizon",
    "shock_source_id",
    "shock_measure",
    "shock_unit",
    "sample_start_q",
    "sample_end_q",
    "n_obs",
    "outcome_transform",
    "control_spec",
    "beta_response_gdp_share_pp_per_source_unit",
    "se_hac",
    "ci95_low_hac",
    "ci95_high_hac",
    "d_y_candidate",
    "candidate_ci_low_d_y",
    "candidate_ci_high_d_y",
    "admitted_curve_response_coefficient",
    "admitted_curve_response_coefficient_unit",
    "policy_path_100bp_year_normalization_status",
    "coefficient_admission_status",
    "source_snapshot_status",
    "source_paths",
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


@dataclass(frozen=True)
class DiagnosticEstimate:
    horizon_q: int
    sample_start_q: str
    sample_end_q: str
    n_obs: int
    beta: float
    se: float
    ci_low: float
    ci_high: float


def denominator_response_diagnostic_rows_from_local_sources(
    *,
    current_demand_snapshot_path: str | Path = CURRENT_DEMAND_GDP_SHARE_SNAPSHOT,
    ratewall_snapshot_path: str | Path = RATEWALL_SNAPSHOT,
    event_vector_path: str | Path = SF_FED_EVENT_VECTOR,
) -> list[dict[str, str]]:
    """Estimate diagnostic FSPDP/GDP responses from local source files."""

    macro_rows = _macro_rows_from_current_demand_snapshot(
        Path(current_demand_snapshot_path)
    )
    control_snapshots = _snapshots_by_series(Path(ratewall_snapshot_path))
    shock_rows = _quarterly_ed_strip_shock_rows(Path(event_vector_path))
    return denominator_response_diagnostic_rows(
        macro_rows=macro_rows,
        control_snapshots=control_snapshots,
        shock_rows=shock_rows,
        source_paths=[
            Path(current_demand_snapshot_path),
            Path(ratewall_snapshot_path),
            Path(event_vector_path),
        ],
    )


def denominator_response_diagnostic_rows(
    *,
    macro_rows: Iterable[Mapping[str, str]],
    control_snapshots: Mapping[str, SourceSnapshot],
    shock_rows: Iterable[Mapping[str, str]],
    source_paths: Iterable[Path] = (),
) -> list[dict[str, str]]:
    """Build h4/h8 diagnostic estimates without admitting a denominator coefficient."""

    macro_by_quarter = {
        row["quarter"]: row for row in macro_rows if row.get("quarter")
    }
    controls = _quarterly_average_controls(control_snapshots)
    shocks = {
        row["quarter"]: _float_or_none(row.get("monetary_event_sum"))
        for row in shock_rows
        if row.get("quarter")
    }
    source_status = _source_status(macro_by_quarter, controls, shocks)
    estimates = [
        _estimate_horizon(
            horizon_q=horizon,
            macro_by_quarter=macro_by_quarter,
            controls=controls,
            shocks=shocks,
        )
        for horizon in (4, 8)
    ]
    return [
        _diagnostic_row(
            estimate=estimate,
            source_status=source_status,
            source_paths=source_paths,
        )
        for estimate in estimates
        if estimate is not None
    ]


def _diagnostic_row(
    *,
    estimate: DiagnosticEstimate,
    source_status: str,
    source_paths: Iterable[Path],
) -> dict[str, str]:
    blocker = (
        "The SF Fed update-2023 ED1-ED4 event strip is source-backed and locally "
        "estimable, but it is not an admitted 100bp-year policy path. Scenario "
        "denominator movement still needs a reviewed bps-year path object or a "
        "literature/econometric transport rule before any coefficient can enter D."
    )
    return {
        "denominator_response_diagnostic_row_id": (
            "denominator_response_diagnostic::"
            f"fspdp_gdp_share_sf_fed_ed_strip_h{estimate.horizon_q}"
        ),
        "estimator_id": "local_projection_fspdp_gdp_share_sf_fed_ed_strip_scalar",
        "horizon_q": str(estimate.horizon_q),
        "target_outcome_id": "fspdp_gdp_share",
        "outcome_object_id": (
            "share_weighted_real_fspdp_level_response_gdp_share_pp"
        ),
        "outcome_unit": "percentage_points_of_gdp",
        "primary_admission_horizon": "h4_only",
        "shock_source_id": "sf_fed_monetary_policy_surprises_candidate_event_vector",
        "shock_measure": "quarterly_sum_update_2023_ed1_ed4_event_strip",
        "shock_unit": "source_scalar_surprise_not_100bp_year",
        "sample_start_q": estimate.sample_start_q,
        "sample_end_q": estimate.sample_end_q,
        "n_obs": str(estimate.n_obs),
        "outcome_transform": (
            "100 * lag_nominal_fspdp_share_of_gdp * "
            "(log(real_fspdp[t+h]) - log(real_fspdp[t-1]))"
        ),
        "control_spec": (
            "constant;shock[t];4 lags of outcome growth, PCE inflation, "
            "UNRATE, FEDFUNDS, and shock"
        ),
        "beta_response_gdp_share_pp_per_source_unit": _format_float(estimate.beta),
        "se_hac": _format_float(estimate.se),
        "ci95_low_hac": _format_float(estimate.ci_low),
        "ci95_high_hac": _format_float(estimate.ci_high),
        "d_y_candidate": _format_float(-estimate.beta),
        "candidate_ci_low_d_y": _format_float(-estimate.ci_high),
        "candidate_ci_high_d_y": _format_float(-estimate.ci_low),
        "admitted_curve_response_coefficient": "",
        "admitted_curve_response_coefficient_unit": "",
        "policy_path_100bp_year_normalization_status": (
            "blocked_scalar_surprise_not_admitted_100bp_year_policy_path"
        ),
        "coefficient_admission_status": "diagnostic_only_not_admitted_to_D",
        "source_snapshot_status": source_status,
        "source_paths": ";".join(str(path) for path in source_paths),
        "exact_blocker": blocker,
        "next_model_requirement": (
            "admit_reviewed_100bp_year_policy_path_or_external_transport_rule"
        ),
        "allowed_use": "denominator_response_econometric_diagnostic_only",
        "blocked_use": (
            "canonical_headline_promotion;denominator_recalibration;"
            "default_runtime_anchor;evidence_mode_claim;"
            "causal_market_yield_estimate;denominator_prior_update;"
            "path_ratio_denominator_replacement;release_headline_claim;"
            "empirical_denominator_response_claim"
        ),
        "claim_boundary": (
            "source_backed_local_projection_diagnostic_not_curve_sensitive_D"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
        "formula_replacement_allowed": "false",
        "causal_market_yield_estimate_enabled": "false",
    }


def write_denominator_response_diagnostic_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=DENOMINATOR_RESPONSE_DIAGNOSTIC_FIELDS
        )
        writer.writeheader()
        writer.writerows(rows)
    return out


def _estimate_horizon(
    *,
    horizon_q: int,
    macro_by_quarter: Mapping[str, Mapping[str, str]],
    controls: Mapping[str, Mapping[str, float]],
    shocks: Mapping[str, float | None],
) -> DiagnosticEstimate | None:
    quarters = sorted(set(macro_by_quarter) & set(shocks))
    y_values: list[float] = []
    x_rows: list[list[float]] = []
    used_quarters: list[str] = []
    for quarter in quarters:
        q_index = _quarter_index(quarter)
        if q_index is None:
            continue
        shock = shocks.get(quarter)
        base = macro_by_quarter.get(_quarter_label(q_index - 1), {})
        future = macro_by_quarter.get(_quarter_label(q_index + horizon_q), {})
        base_real = _decimal_or_none(base.get("real_fspdp"))
        future_real = _decimal_or_none(future.get("real_fspdp"))
        share = _decimal_or_none(base.get("fspdp_share_of_gdp"))
        if (
            shock is None
            or share is None
            or base_real is None
            or future_real is None
            or base_real <= 0
            or future_real <= 0
        ):
            continue
        lag_controls: list[float] = []
        valid = True
        for lag in range(1, 5):
            lag_q = _quarter_label(q_index - lag)
            lag_row = macro_by_quarter.get(lag_q, {})
            prev_row = macro_by_quarter.get(_quarter_label(q_index - lag - 1), {})
            growth = _log_change_pct(
                _decimal_or_none(lag_row.get("real_fspdp")),
                _decimal_or_none(prev_row.get("real_fspdp")),
            )
            inflation = _log_change_pct(
                _pce_price(lag_row),
                _pce_price(prev_row),
            )
            unrate = controls.get("UNRATE", {}).get(lag_q)
            fedfunds = controls.get("FEDFUNDS", {}).get(lag_q)
            lag_shock = shocks.get(lag_q)
            if None in {growth, inflation, unrate, fedfunds, lag_shock}:
                valid = False
                break
            lag_controls.extend([growth, inflation, unrate, fedfunds, lag_shock])
        if not valid:
            continue
        outcome = 100.0 * float(share) * (
            math.log(float(future_real)) - math.log(float(base_real))
        )
        y_values.append(outcome)
        x_rows.append([1.0, shock, *lag_controls])
        used_quarters.append(quarter)
    if not y_values:
        return None
    estimate = _ols_hac(y_values, x_rows, bandwidth=max(4, horizon_q + 1))
    if estimate is None:
        return None
    return DiagnosticEstimate(
        horizon_q=horizon_q,
        sample_start_q=used_quarters[0],
        sample_end_q=used_quarters[-1],
        n_obs=len(y_values),
        beta=estimate[0],
        se=estimate[1],
        ci_low=estimate[2],
        ci_high=estimate[3],
    )


def _macro_rows_from_current_demand_snapshot(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = {
        str(item.get("metadata", {}).get("series_id", "")): {
            str(record.get("date", "")): record.get("value")
            for record in item.get("records", [])
            if record.get("date")
        }
        for item in payload.get("snapshots", [])
    }
    rows: list[dict[str, str]] = []
    for date_key in sorted(set(series.get("GDP", {}))):
        quarter = _quarter_from_date(date_key)
        nominal_gdp = series.get("GDP", {}).get(date_key)
        nominal_fspdp = series.get("LA0000031Q027SBEA", {}).get(date_key)
        real_fspdp = series.get("LB0000031Q020SBEA", {}).get(date_key)
        nominal_pce = series.get("PCEC", {}).get(date_key)
        real_pce = series.get("PCECC96", {}).get(date_key)
        fspdp_value = _decimal_or_none(nominal_fspdp)
        gdp_value = _decimal_or_none(nominal_gdp)
        if not quarter or fspdp_value is None or gdp_value in {None, Decimal("0")}:
            continue
        rows.append(
            {
                "quarter": quarter,
                "nominal_gdp": str(nominal_gdp or ""),
                "nominal_fspdp": str(nominal_fspdp or ""),
                "real_fspdp": str(real_fspdp or ""),
                "nominal_pce": str(nominal_pce or ""),
                "real_pce": str(real_pce or ""),
                "fspdp_share_of_gdp": str(fspdp_value / gdp_value),
            }
        )
    return rows


def _snapshots_by_series(path: Path) -> dict[str, SourceSnapshot]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, SourceSnapshot] = {}
    for snapshot in payload.get("snapshots", []):
        parsed = SourceSnapshot.from_dict(snapshot)
        out[parsed.metadata.series_id] = parsed
    return out


def _quarterly_ed_strip_shock_rows(path: Path) -> list[dict[str, str]]:
    by_event: dict[str, dict[str, Decimal]] = defaultdict(dict)
    event_dates: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("source_sheet_vintage") != "update_2023":
                continue
            instrument = row.get("instrument_code", "")
            if instrument not in {"ED1", "ED2", "ED3", "ED4"}:
                continue
            value = _decimal_or_none(row.get("source_reported_value_numeric"))
            event_id = row.get("event_id", "")
            if value is None or not event_id:
                continue
            by_event[event_id][instrument] = value
            event_dates[event_id] = row.get("event_date", "")
    grouped: dict[str, list[Decimal]] = defaultdict(list)
    for event_id, values in by_event.items():
        if set(values) != {"ED1", "ED2", "ED3", "ED4"}:
            continue
        quarter = _quarter_from_date(event_dates.get(event_id, ""))
        if quarter:
            grouped[quarter].append(sum(values.values(), Decimal("0")))
    return [
        {
            "quarter": quarter,
            "monetary_event_sum": str(sum(values, Decimal("0"))),
            "event_count": str(len(values)),
        }
        for quarter, values in sorted(grouped.items())
    ]


def _quarterly_average_controls(
    snapshots: Mapping[str, SourceSnapshot],
) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for series_id in ("UNRATE", "FEDFUNDS"):
        grouped: dict[str, list[float]] = defaultdict(list)
        snapshot = snapshots.get(series_id)
        if snapshot is None:
            out[series_id] = {}
            continue
        for record in snapshot.records:
            quarter = _quarter_from_date(str(record.get("date", "")))
            value = _float_or_none(record.get("value"))
            if quarter and value is not None:
                grouped[quarter].append(value)
        out[series_id] = {
            quarter: sum(values) / len(values)
            for quarter, values in grouped.items()
            if values
        }
    return out


def _ols_hac(
    y_values: list[float],
    x_rows: list[list[float]],
    *,
    bandwidth: int,
) -> tuple[float, float, float, float] | None:
    import numpy as np

    y = np.array(y_values, dtype=float)
    x = np.array(x_rows, dtype=float)
    if x.shape[0] <= x.shape[1] or np.linalg.matrix_rank(x) < x.shape[1]:
        return None
    beta = np.linalg.solve(x.T @ x, x.T @ y)
    residuals = y - x @ beta
    xtx_inv = np.linalg.inv(x.T @ x)
    meat = x.T @ np.diag(residuals**2) @ x
    n = len(y)
    for lag in range(1, min(bandwidth, n - 1) + 1):
        weight = 1.0 - lag / (bandwidth + 1.0)
        gamma = x[lag:].T @ np.diag(residuals[lag:] * residuals[:-lag]) @ x[:-lag]
        meat += weight * (gamma + gamma.T)
    cov = xtx_inv @ meat @ xtx_inv
    se = float(math.sqrt(max(cov[1, 1], 0.0)))
    beta_1 = float(beta[1])
    return beta_1, se, beta_1 - 1.96 * se, beta_1 + 1.96 * se


def _source_status(
    macro_by_quarter: Mapping[str, Mapping[str, str]],
    controls: Mapping[str, Mapping[str, float]],
    shocks: Mapping[str, float | None],
) -> str:
    if not macro_by_quarter:
        return "blocked_missing_current_demand_macro_rows"
    if not controls.get("UNRATE") or not controls.get("FEDFUNDS"):
        return "blocked_missing_unrate_or_fedfunds_controls"
    if not shocks:
        return "blocked_missing_sf_fed_ed_strip_shocks"
    return "pass_local_sources_available_for_diagnostic_estimate"


def _pce_price(row: Mapping[str, str]) -> Decimal | None:
    nominal = _decimal_or_none(row.get("nominal_pce"))
    real = _decimal_or_none(row.get("real_pce"))
    if nominal is None or real in {None, Decimal("0")}:
        return None
    return nominal / real


def _log_change_pct(current: Decimal | None, previous: Decimal | None) -> float | None:
    if current is None or previous is None or current <= 0 or previous <= 0:
        return None
    return 100.0 * (math.log(float(current)) - math.log(float(previous)))


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


def _quarter_index(label: str) -> int | None:
    if len(label) != 6 or label[4] != "Q":
        return None
    try:
        year = int(label[:4])
        quarter = int(label[5])
    except ValueError:
        return None
    if quarter not in {1, 2, 3, 4}:
        return None
    return year * 4 + quarter - 1


def _quarter_label(index: int) -> str:
    year, offset = divmod(index, 4)
    return f"{year}Q{offset + 1}"


def _decimal_or_none(value: object) -> Decimal | None:
    if value in {None, ""}:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _float_or_none(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _format_float(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return ""
    text = f"{value:.12g}"
    return "0" if text == "-0" else text
