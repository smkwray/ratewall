"""TDC beta/chi schedule for selected marginal RateWall TDC support."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_EA_TDC_BETA_PATH = Path(
    "data/raw/ratewall_sibling_calibration/"
    "ea_tdc_paper_tier2_selected_credit_rate_lags_estimates.csv"
)
DEFAULT_EA_TDC_ROLLING_BETA_PATH = Path(
    "data/raw/ratewall_sibling_calibration/"
    "ea_tdc_tier2_rolling_selected_credit_rate_pass_through_estimates.csv"
)
DEFAULT_OVERRIDE_PATH = Path(
    "configs/assumption_mode/ratewall_tdc_beta_anchor_override.csv"
)
DEFAULT_DENOMINATOR_PATH = Path(
    "var/preliminary_scenario_results/marginal_denominator/"
    "ratewall_marginal_denominator_surface.csv"
)
DEFAULT_HISTORICAL_WINDOW_PATH = Path(
    "configs/assumption_mode/ratewall_historical_selected_window.csv"
)
DEFAULT_TDCEST_PROXY_PATH = Path(
    "../tdcest/data/processed/tdc_tdcsim_private_route_allocation_sensitivity.csv"
)
DEFAULT_OUTPUT_PATH = Path(
    "var/preliminary_scenario_results/marginal_tdcsim/"
    "ratewall_marginal_tdc_beta_schedule.csv"
)
DEFAULT_SENSITIVITY_OUTPUT_PATH = Path(
    "var/preliminary_scenario_results/marginal_tdcsim/"
    "ratewall_marginal_tdc_beta_sensitivity_panel.csv"
)

OBJECT_ID = "RW_M_PLUS_100BP_YEAR"
BETA_ANCHOR_ID = "beta_ea_tdc_rolling_h0_matched_total_deposits_v1"
CHI_ASSUMPTION_ID = "chi_ratewall_default_20260630"
SELECTED_OUTCOME = "matched_total_deposits"
SELECTED_HORIZON = "0"
DEFAULT_SAMPLE_START = "2002Q1"
DEFAULT_SAMPLE_END = "2025Q4"
DEFAULT_ROLLING_WINDOW_END = "2026Q2"
LEGACY_BETA = Decimal("0.34201759129420367")
DEFAULT_BETA_HIGH = Decimal("0.729969")

BETA_SCHEDULE_FIELDS = [
    "beta_schedule_row_id",
    "object_id",
    "period_object",
    "period",
    "state_id",
    "state_kind",
    "horizon",
    "shock_path_id",
    "shock_bps_year",
    "demand_conversion_case",
    "beta_assumption_id",
    "beta_selected",
    "beta_low",
    "beta_high",
    "beta_legacy_scaffold",
    "beta_source_artifact",
    "beta_source_field",
    "beta_source_sample_start",
    "beta_source_sample_end",
    "beta_raw_estimate",
    "beta_raw_lower95",
    "beta_raw_upper95",
    "beta_window_start_quarter",
    "beta_window_end_quarter",
    "beta_window_quarters",
    "beta_method",
    "beta_projection_method",
    "beta_source_status",
    "beta_selection_status",
    "time_varying_proxy_available",
    "time_varying_proxy_central",
    "time_varying_proxy_low",
    "time_varying_proxy_high",
    "time_varying_proxy_source_artifact",
    "chi_assumption_id",
    "chi_selected",
    "chi_low",
    "chi_high",
    "chi_source_status",
    "beta_times_chi_selected",
    "claim_boundary",
]

BETA_SENSITIVITY_FIELDS = [
    "beta_sensitivity_row_id",
    "period_object",
    "period",
    "state_id",
    "case_id",
    "beta",
    "chi",
    "beta_times_chi",
    "selected_central",
    "allowed_use",
    "claim_boundary",
]


@dataclass(frozen=True)
class BetaAnchor:
    beta_selected: Decimal
    beta_low: Decimal
    beta_high: Decimal
    beta_legacy_scaffold: Decimal
    chi_selected: Decimal
    chi_low: Decimal
    chi_high: Decimal
    source_artifact: str
    source_field: str
    source_status: str
    selected_source_grade_allowed: bool
    sample_start: str
    sample_end: str


@dataclass(frozen=True)
class BetaEstimate:
    beta_selected: Decimal
    beta_low: Decimal
    beta_high: Decimal
    raw_beta: Decimal
    raw_low: Decimal
    raw_high: Decimal
    window_start: str
    window_end: str
    window_quarters: str
    source_artifact: str
    source_field: str
    source_status: str
    method: str
    projection_method: str
    sample_start: str
    sample_end: str
    selected_source_grade_allowed: bool


class MarginalTdcBetaError(ValueError):
    """Raised when the marginal TDC beta schedule is malformed."""


def load_beta_anchor(
    project_root: Path,
    *,
    ea_tdc_beta_path: str | Path = DEFAULT_EA_TDC_BETA_PATH,
    override_path: str | Path = DEFAULT_OVERRIDE_PATH,
) -> BetaAnchor:
    """Load the selected EA/TDC beta anchor or explicit fallback override."""

    source_path = project_root / Path(ea_tdc_beta_path)
    override = _load_override(project_root / Path(override_path))
    if source_path.exists():
        rows = _read_csv(source_path)
        matches = [
            row
            for row in rows
            if str(row.get("horizon", "")) == SELECTED_HORIZON
            and row.get("outcome") == SELECTED_OUTCOME
        ]
        if len(matches) != 1:
            raise MarginalTdcBetaError("EA/TDC beta source must have one selected row")
        row = matches[0]
        beta = Decimal(str(row["normalized_beta"]))
        return BetaAnchor(
            beta_selected=beta,
            beta_low=override.beta_low,
            beta_high=override.beta_high,
            beta_legacy_scaffold=override.beta_legacy_scaffold,
            chi_selected=override.chi_selected,
            chi_low=override.chi_low,
            chi_high=override.chi_high,
            source_artifact=str(Path(ea_tdc_beta_path)),
            source_field="normalized_beta",
            source_status="source_grade_ea_tdc_anchor",
            selected_source_grade_allowed=True,
            sample_start=DEFAULT_SAMPLE_START,
            sample_end=DEFAULT_SAMPLE_END,
        )
    return override


def build_beta_schedule(
    *,
    denominator_rows: Sequence[Mapping[str, str]],
    historical_window_rows: Sequence[Mapping[str, str]],
    project_root: Path,
    ea_tdc_beta_path: str | Path = DEFAULT_EA_TDC_BETA_PATH,
    rolling_beta_path: str | Path = DEFAULT_EA_TDC_ROLLING_BETA_PATH,
    override_path: str | Path = DEFAULT_OVERRIDE_PATH,
    tdcest_proxy_path: str | Path = DEFAULT_TDCEST_PROXY_PATH,
) -> list[dict[str, str]]:
    """Build one beta row for each selected marginal denominator state."""

    anchor = load_beta_anchor(
        project_root,
        ea_tdc_beta_path=ea_tdc_beta_path,
        override_path=override_path,
    )
    rolling = _load_rolling_beta_rows(project_root / Path(rolling_beta_path))
    windows = {row["period"]: row for row in historical_window_rows}
    proxies = _proxy_rows_by_period(project_root / Path(tdcest_proxy_path))
    rows: list[dict[str, str]] = []
    selected_denominator = [
        row for row in denominator_rows if _bool(row.get("selected_marginal_D"))
    ]
    for d_row in selected_denominator:
        period_object = d_row["period_object"]
        period = d_row["period"]
        state_id = d_row["state_id"]
        status = _selection_status(
            period_object=period_object,
            period=period,
            historical_window=windows.get(period),
            selected_source_grade_allowed=bool(rolling) or anchor.selected_source_grade_allowed,
        )
        proxy = proxies.get(period, {})
        beta_estimate = _beta_estimate_for_period(
            period_object=period_object,
            period=period,
            rolling_rows=rolling,
            fallback_anchor=anchor,
            rolling_beta_path=rolling_beta_path,
        )
        row = {
            "beta_schedule_row_id": (
                f"marginal_tdc_beta::{period_object}::{period}::{state_id}::central"
            ),
            "object_id": OBJECT_ID,
            "period_object": period_object,
            "period": period,
            "state_id": state_id,
            "state_kind": _state_kind(period_object),
            "horizon": d_row["horizon"],
            "shock_path_id": d_row["shock_path_id"],
            "shock_bps_year": d_row["shock_bps_year"],
            "demand_conversion_case": "central",
            "beta_assumption_id": BETA_ANCHOR_ID,
            "beta_selected": _fmt(beta_estimate.beta_selected),
            "beta_low": _fmt(beta_estimate.beta_low),
            "beta_high": _fmt(beta_estimate.beta_high),
            "beta_legacy_scaffold": _fmt(anchor.beta_legacy_scaffold),
            "beta_source_artifact": beta_estimate.source_artifact,
            "beta_source_field": beta_estimate.source_field,
            "beta_source_sample_start": beta_estimate.sample_start,
            "beta_source_sample_end": beta_estimate.sample_end,
            "beta_raw_estimate": _fmt(beta_estimate.raw_beta),
            "beta_raw_lower95": _fmt(beta_estimate.raw_low),
            "beta_raw_upper95": _fmt(beta_estimate.raw_high),
            "beta_window_start_quarter": beta_estimate.window_start,
            "beta_window_end_quarter": beta_estimate.window_end,
            "beta_window_quarters": beta_estimate.window_quarters,
            "beta_method": beta_estimate.method,
            "beta_projection_method": beta_estimate.projection_method,
            "beta_source_status": beta_estimate.source_status,
            "beta_selection_status": status,
            "time_varying_proxy_available": str(bool(proxy)).lower(),
            "time_varying_proxy_central": _fmt_or_blank(proxy.get("share_central")),
            "time_varying_proxy_low": _fmt_or_blank(proxy.get("share_low")),
            "time_varying_proxy_high": _fmt_or_blank(proxy.get("share_high")),
            "time_varying_proxy_source_artifact": (
                str(Path(tdcest_proxy_path)) if proxy else ""
            ),
            "chi_assumption_id": CHI_ASSUMPTION_ID,
            "chi_selected": _fmt(anchor.chi_selected),
            "chi_low": _fmt(anchor.chi_low),
            "chi_high": _fmt(anchor.chi_high),
            "chi_source_status": "assumption_mode",
            "beta_times_chi_selected": _fmt(
                beta_estimate.beta_selected * anchor.chi_selected
            ),
            "claim_boundary": (
                "selected_tdc_beta_is_rolling_ea_tdc_estimate_bounded_0_1"
            ),
        }
        rows.append(row)
    validate_beta_schedule(rows)
    return rows


def build_beta_sensitivity_panel(
    schedule_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Emit visible beta sensitivity cases without changing selected central beta."""

    rows: list[dict[str, str]] = []
    for schedule in schedule_rows:
        cases = [
            ("legacy_low", schedule["beta_low"], "false"),
            ("selected_central", schedule["beta_selected"], "true"),
            ("rolling_high", schedule["beta_high"], "false"),
        ]
        for case_id, beta_text, selected in cases:
            beta = Decimal(str(beta_text))
            chi = Decimal(str(schedule["chi_selected"]))
            rows.append(
                {
                    "beta_sensitivity_row_id": (
                        f"marginal_tdc_beta_sensitivity::{schedule['period_object']}::"
                        f"{schedule['period']}::{schedule['state_id']}::{case_id}"
                    ),
                    "period_object": schedule["period_object"],
                    "period": schedule["period"],
                    "state_id": schedule["state_id"],
                    "case_id": case_id,
                    "beta": _fmt(beta),
                    "chi": _fmt(chi),
                    "beta_times_chi": _fmt(beta * chi),
                    "selected_central": selected,
                    "allowed_use": (
                        "selected_beta_case"
                        if selected == "true"
                        else "nonselected_beta_sensitivity"
                    ),
                    "claim_boundary": "beta_sensitivity_does_not_replace_selected_schedule",
                }
            )
    return rows


def lookup_beta_schedule_row(
    *,
    schedule_rows: Sequence[Mapping[str, str]],
    period_object: str,
    period: str,
    state_id: str,
    state_kind: str,
    horizon: str,
    shock_path_id: str,
    demand_conversion_case: str,
) -> dict[str, str]:
    matches = [
        dict(row)
        for row in schedule_rows
        if row["period_object"] == period_object
        and row["period"] == period
        and row["state_id"] == state_id
        and row["state_kind"] == state_kind
        and row["horizon"] == horizon
        and row["shock_path_id"] == shock_path_id
        and row["demand_conversion_case"] == demand_conversion_case
    ]
    if len(matches) != 1:
        raise MarginalTdcBetaError("expected exactly one matching beta schedule row")
    return matches[0]


def validate_beta_schedule(rows: Sequence[Mapping[str, str]]) -> None:
    if not rows:
        raise MarginalTdcBetaError("beta schedule is empty")
    keys: set[tuple[str, str, str, str, str, str]] = set()
    has_selected = False
    for row in rows:
        if set(row) != set(BETA_SCHEDULE_FIELDS):
            raise MarginalTdcBetaError("beta schedule schema mismatch")
        key = (
            row["period_object"],
            row["period"],
            row["state_id"],
            row["horizon"],
            row["shock_path_id"],
            row["demand_conversion_case"],
        )
        if key in keys:
            raise MarginalTdcBetaError("duplicate beta schedule key")
        keys.add(key)
        beta = Decimal(row["beta_selected"])
        beta_low = Decimal(row["beta_low"])
        beta_high = Decimal(row["beta_high"])
        legacy = Decimal(row["beta_legacy_scaffold"])
        chi = Decimal(row["chi_selected"])
        chi_low = Decimal(row["chi_low"])
        chi_high = Decimal(row["chi_high"])
        if not (Decimal("0") <= beta_low <= beta <= beta_high <= Decimal("1")):
            raise MarginalTdcBetaError("beta bounds must satisfy 0 <= low <= selected <= high <= 1")
        if not (Decimal("0") <= chi_low <= chi <= chi_high <= Decimal("1")):
            raise MarginalTdcBetaError("chi bounds must satisfy 0 <= low <= selected <= high <= 1")
        if beta == legacy:
            raise MarginalTdcBetaError("selected beta cannot equal legacy scaffold beta")
        if Decimal(row["beta_times_chi_selected"]) != beta * chi:
            raise MarginalTdcBetaError("beta times chi identity failed")
        raw_beta = Decimal(row["beta_raw_estimate"])
        if row["beta_source_status"].startswith("source_grade_ea_tdc_rolling"):
            if beta != _bound_beta(raw_beta):
                raise MarginalTdcBetaError("selected rolling beta must be bounded raw beta")
        if row["object_id"] != OBJECT_ID:
            raise MarginalTdcBetaError("unexpected beta schedule object")
        if row["shock_path_id"] != "plus_100bp_year":
            raise MarginalTdcBetaError("unexpected beta schedule shock path")
        if row["beta_selection_status"].startswith("selected"):
            has_selected = True
    if not has_selected:
        raise MarginalTdcBetaError("beta schedule has no selected rows")


def write_beta_schedule(
    project_root: Path,
    *,
    denominator_path: str | Path = DEFAULT_DENOMINATOR_PATH,
    historical_window_path: str | Path = DEFAULT_HISTORICAL_WINDOW_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    sensitivity_output_path: str | Path = DEFAULT_SENSITIVITY_OUTPUT_PATH,
) -> dict[str, Path]:
    denominator_rows = _read_csv(project_root / Path(denominator_path))
    historical_rows = _read_csv(project_root / Path(historical_window_path))
    rows = build_beta_schedule(
        denominator_rows=denominator_rows,
        historical_window_rows=historical_rows,
        project_root=project_root,
    )
    sensitivity = build_beta_sensitivity_panel(rows)
    out = project_root / Path(output_path)
    sensitivity_out = project_root / Path(sensitivity_output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_rows(out, rows, BETA_SCHEDULE_FIELDS)
    write_rows(sensitivity_out, sensitivity, BETA_SENSITIVITY_FIELDS)
    return {"beta_schedule_csv": out, "beta_sensitivity_csv": sensitivity_out}


def _selection_status(
    *,
    period_object: str,
    period: str,
    historical_window: Mapping[str, str] | None,
    selected_source_grade_allowed: bool,
) -> str:
    if period_object == "historical":
        if _period_before(period, DEFAULT_SAMPLE_START):
            return "fail_closed_no_ea_tdc_sample_coverage"
        if historical_window is None:
            return "diagnostic_historical_outside_true_v1_selected_window"
        if not _bool(historical_window.get("selected_historical_rw_m_allowed_if_complete")):
            return str(historical_window.get("selection_gate_status", "fail_closed_historical_window"))
        return (
            "selected_source_grade_ea_tdc_rolling_beta"
            if selected_source_grade_allowed
            else "selected_assumption_mode_documented_anchor"
        )
    if period_object == "current":
        return (
            "selected_source_grade_ea_tdc_rolling_beta_carry_forward"
            if selected_source_grade_allowed
            else "selected_assumption_mode_documented_anchor_carry_forward"
        )
    if period_object == "forecast":
        return (
            "selected_source_grade_ea_tdc_rolling_beta_flat_forecast"
            if selected_source_grade_allowed
            else "selected_assumption_mode_documented_anchor_flat_forecast"
        )
    return "fail_closed_unknown_period_object"


def _projection_method(period_object: str, period: str) -> str:
    if period_object == "historical":
        return "in_sample_anchor" if not _period_after(period, DEFAULT_SAMPLE_END) else "fail_closed_outside_sample"
    if period_object == "current":
        return "carry_forward_from_2025Q4"
    if period_object == "forecast":
        return "flat_carry_forward_from_2025Q4"
    return "unknown"


def _load_rolling_beta_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = [
        row
        for row in _read_csv(path)
        if row.get("outcome") == SELECTED_OUTCOME
        and str(row.get("horizon", "")) == SELECTED_HORIZON
    ]
    rows.sort(key=lambda row: _period_key(row["window_end_quarter"]))
    seen: set[str] = set()
    for row in rows:
        end = row["window_end_quarter"]
        if end in seen:
            raise MarginalTdcBetaError("duplicate rolling beta window end")
        seen.add(end)
    return rows


def _beta_estimate_for_period(
    *,
    period_object: str,
    period: str,
    rolling_rows: Sequence[Mapping[str, str]],
    fallback_anchor: BetaAnchor,
    rolling_beta_path: str | Path,
) -> BetaEstimate:
    if not rolling_rows:
        return BetaEstimate(
            beta_selected=fallback_anchor.beta_selected,
            beta_low=fallback_anchor.beta_low,
            beta_high=fallback_anchor.beta_high,
            raw_beta=fallback_anchor.beta_selected,
            raw_low=fallback_anchor.beta_low,
            raw_high=fallback_anchor.beta_high,
            window_start=fallback_anchor.sample_start,
            window_end=fallback_anchor.sample_end,
            window_quarters="",
            source_artifact=fallback_anchor.source_artifact,
            source_field=fallback_anchor.source_field,
            source_status=fallback_anchor.source_status,
            method="ea_tdc_h0_matched_total_deposits_source_anchor",
            projection_method=_projection_method(period_object, period),
            sample_start=fallback_anchor.sample_start,
            sample_end=fallback_anchor.sample_end,
            selected_source_grade_allowed=fallback_anchor.selected_source_grade_allowed,
        )
    period_key = _period_key(period)
    candidates = [
        row for row in rolling_rows if _period_key(row["window_end_quarter"]) <= period_key
    ]
    selected = candidates[-1] if candidates else rolling_rows[0]
    raw_beta = Decimal(str(selected["normalized_beta"]))
    raw_low = Decimal(str(selected["normalized_lower95"]))
    raw_high = Decimal(str(selected["normalized_upper95"]))
    latest_end = str(rolling_rows[-1]["window_end_quarter"])
    window_end = str(selected["window_end_quarter"])
    projection = "rolling_window_same_period"
    if not candidates:
        projection = f"fail_closed_before_first_rolling_window_{window_end}"
    elif _period_key(period) > _period_key(latest_end):
        projection = f"flat_carry_forward_from_latest_rolling_window_{latest_end}"
    elif period_object in {"current", "forecast"} and "Q" not in period:
        projection = f"latest_available_rolling_window_{window_end}"
    return BetaEstimate(
        beta_selected=_bound_beta(raw_beta),
        beta_low=_bound_beta(raw_low),
        beta_high=_bound_beta(raw_high),
        raw_beta=raw_beta,
        raw_low=raw_low,
        raw_high=raw_high,
        window_start=str(selected["window_start_quarter"]),
        window_end=window_end,
        window_quarters=str(selected["window_quarters"]),
        source_artifact=str(Path(rolling_beta_path)),
        source_field="normalized_beta_bounded_0_1",
        source_status="source_grade_ea_tdc_rolling_beta",
        method="ea_tdc_rolling_selected_credit_rate_lags_rank_aware",
        projection_method=projection,
        sample_start=str(rolling_rows[0]["window_start_quarter"]),
        sample_end=latest_end,
        selected_source_grade_allowed=True,
    )


def _load_override(path: Path) -> BetaAnchor:
    rows = _read_csv(path)
    if len(rows) != 1:
        raise MarginalTdcBetaError("beta override must have one row")
    row = rows[0]
    return BetaAnchor(
        beta_selected=Decimal(row["beta_selected"]),
        beta_low=Decimal(row["beta_low"]),
        beta_high=Decimal(row["beta_high"]),
        beta_legacy_scaffold=Decimal(row["beta_legacy_scaffold"]),
        chi_selected=Decimal(row["chi_selected"]),
        chi_low=Decimal(row["chi_low"]),
        chi_high=Decimal(row["chi_high"]),
        source_artifact=row["source_artifact"],
        source_field=row["source_field"],
        source_status=row["source_status"],
        selected_source_grade_allowed=_bool(row["selected_source_grade_allowed"]),
        sample_start=DEFAULT_SAMPLE_START,
        sample_end=DEFAULT_SAMPLE_END,
    )


def _proxy_rows_by_period(path: Path) -> dict[str, Mapping[str, str]]:
    if not path.exists():
        return {}
    rows = _read_csv(path)
    return {
        row["ref_quarter"]: row
        for row in rows
        if row.get("object_family") == "flow_absorption_trailing_4q"
        and row.get("route_class") == "deposit_funded_domestic_nonbank_possible"
    }


def _state_kind(period_object: str) -> str:
    if period_object == "historical":
        return "historical_state"
    if period_object == "current":
        return "current_state"
    if period_object == "forecast":
        return "forecast_state"
    return period_object


def _period_before(period: str, cutoff: str) -> bool:
    return _period_key(period) < _period_key(cutoff)


def _period_after(period: str, cutoff: str) -> bool:
    return _period_key(period) > _period_key(cutoff)


def _period_key(period: str) -> tuple[int, int]:
    if "Q" in period:
        year, quarter = period.split("Q", 1)
        return int(year), int(quarter)
    return int(period), 4


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _fmt_or_blank(value: object) -> str:
    if value in (None, ""):
        return ""
    return _fmt(Decimal(str(value)))


def _bound_beta(value: Decimal) -> Decimal:
    return min(Decimal("1"), max(Decimal("0"), value))
