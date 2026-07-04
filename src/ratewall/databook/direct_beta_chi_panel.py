"""Candidate panel for direct beta-chi evidence.

This module builds the panel shape RateWall needs before any direct beta-chi
lower bound can be admitted. It deliberately does not estimate or admit a floor:
TDCSim forecast treatment rows are not, by themselves, observed evidence.
"""

from __future__ import annotations

import csv
import gzip
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.direct_chi_evidence import (
    DEFAULT_LOCAL_CURRENT_DEMAND_DIR,
    DEFAULT_TDCSIM_PERIOD_TDC_DIR,
)

DIRECT_BETA_CHI_PANEL_FIELDS = [
    "direct_beta_chi_panel_row_id",
    "scenario_id",
    "quarter",
    "outcome_series_key",
    "horizon_quarters",
    "period_row_count",
    "tdc_change_ex_overlap_bil",
    "gdp_bil",
    "tdc_change_ex_overlap_share_of_gdp",
    "outcome_current_bil",
    "outcome_future_bil",
    "outcome_change_share_of_gdp",
    "matched_outcome_status",
    "identification_status",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DIRECT_BETA_CHI_PANEL_STATUS_FIELDS = [
    "direct_beta_chi_panel_status_row_id",
    "source_tdc_period_dir",
    "source_current_demand_dir",
    "treatment_quarter_count",
    "outcome_series_count",
    "candidate_panel_rows",
    "matched_panel_rows",
    "identified_panel_rows",
    "admitted_lower_bound_rows",
    "panel_status",
    "estimator_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class DirectBetaChiPanelError(ValueError):
    """Raised when candidate beta-chi panel rows cannot be built."""


@dataclass(frozen=True)
class DirectBetaChiPanelPaths:
    """Source paths for the candidate direct beta-chi panel."""

    tdcsim_period_tdc_dir: Path = DEFAULT_TDCSIM_PERIOD_TDC_DIR
    local_current_demand_dir: Path = DEFAULT_LOCAL_CURRENT_DEMAND_DIR


def direct_beta_chi_panel_rows(
    *,
    paths: DirectBetaChiPanelPaths = DirectBetaChiPanelPaths(),
    outcome_series_keys: Sequence[str] = ("PCEC", "LA0000031Q027SBEA"),
    horizons: Sequence[int] = (0, 1),
) -> list[dict[str, str]]:
    """Build candidate treatment/outcome panel rows for direct beta-chi evidence."""

    treatments = _quarterly_tdc_treatments(paths.tdcsim_period_tdc_dir)
    outcomes = _read_outcome_series(paths.local_current_demand_dir, outcome_series_keys)
    out: list[dict[str, str]] = []
    for treatment_key, treatment in sorted(treatments.items()):
        scenario_id, quarter = treatment_key
        for outcome_key in outcome_series_keys:
            outcome = outcomes.get(outcome_key, {})
            outcome_quarters = sorted(
                quarter_key for quarter_key in outcome if not quarter_key.startswith("GDP::")
            )
            outcome_index = {
                quarter_key: index for index, quarter_key in enumerate(outcome_quarters)
            }
            for horizon in horizons:
                row = _panel_row(
                    scenario_id=scenario_id,
                    quarter=quarter,
                    treatment=treatment,
                    outcome_key=outcome_key,
                    outcome=outcome,
                    outcome_index=outcome_index,
                    outcome_quarters=outcome_quarters,
                    horizon=horizon,
                )
                out.append(row)
    return sorted(
        out,
        key=lambda row: (
            row["scenario_id"],
            _quarter_sort_key(row["quarter"]),
            row["outcome_series_key"],
            int(row["horizon_quarters"]),
        ),
    )


def direct_beta_chi_panel_status_rows(
    rows: Iterable[Mapping[str, str]],
    *,
    paths: DirectBetaChiPanelPaths = DirectBetaChiPanelPaths(),
) -> list[dict[str, str]]:
    """Summarize whether the candidate panel can admit direct beta-chi evidence."""

    panel_rows = list(rows)
    treatment_quarters = {
        (row["scenario_id"], row["quarter"]) for row in panel_rows
    }
    outcome_series = {row["outcome_series_key"] for row in panel_rows}
    matched = [
        row
        for row in panel_rows
        if row["matched_outcome_status"] == "matched_observed_outcome"
    ]
    identified = [
        row
        for row in matched
        if row["identification_status"] == "identified_external_or_predetermined"
    ]
    admitted = [
        row for row in identified if row["admission_status"] == "admissible_lower_bound"
    ]
    if not panel_rows:
        status = "blocked_no_tdc_treatment_rows"
        blocker = "tdcsim_period_tdc_summary_missing_or_empty"
    elif not matched:
        status = "blocked_no_observed_outcome_match"
        blocker = "tdcsim_forecast_treatment_quarters_do_not_overlap_observed_outcomes"
    elif not identified:
        status = "blocked_missing_identification_strategy"
        blocker = "matched_panel_has_no_external_or_predetermined_variation"
    else:
        status = "ready_for_external_lower_bound_estimator"
        blocker = ""
    return [
        {
            "direct_beta_chi_panel_status_row_id": "direct_beta_chi_panel_status::current",
            "source_tdc_period_dir": str(paths.tdcsim_period_tdc_dir),
            "source_current_demand_dir": str(paths.local_current_demand_dir),
            "treatment_quarter_count": str(len(treatment_quarters)),
            "outcome_series_count": str(len(outcome_series)),
            "candidate_panel_rows": str(len(panel_rows)),
            "matched_panel_rows": str(len(matched)),
            "identified_panel_rows": str(len(identified)),
            "admitted_lower_bound_rows": str(len(admitted)),
            "panel_status": status,
            "estimator_blocker": blocker,
            "allowed_use": "direct_beta_chi_candidate_panel_status",
            "blocked_use": (
                "beta_chi_floor_admission_without_identified_lower_bound;"
                "canonical_headline_promotion;evidence_mode_claim;"
                "posterior_beta_or_chi_claim"
            ),
            "claim_boundary": (
                "panel_status_only;does_not_change_beta_chi_grid_or_scenario_math"
            ),
        }
    ]


def direct_beta_chi_panel_source_candidate_rows(
    status_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Represent the candidate panel in the direct-chi source inventory."""

    out: list[dict[str, str]] = []
    for row in status_rows:
        matched = _int(row["matched_panel_rows"])
        identified = _int(row["identified_panel_rows"])
        out.append(
            {
                "direct_chi_source_row_id": "direct_chi_source::direct_beta_chi_panel::current",
                "source_family": "ratewall_direct_beta_chi_candidate_panel",
                "source_artifact": (
                    "var/preliminary_scenario_results/direct_chi_evidence/"
                    "ratewall_direct_beta_chi_candidate_panel.csv"
                ),
                "candidate_role": "candidate_tdc_current_demand_panel",
                "row_count": row["candidate_panel_rows"],
                "has_tdc_ex_overlap_treatment": "true"
                if _int(row["treatment_quarter_count"]) > 0
                else "false",
                "has_materialized_tdc_treatment": "true"
                if _int(row["treatment_quarter_count"]) > 0
                else "false",
                "has_current_demand_outcome": "true" if matched > 0 else "false",
                "has_identification_strategy": "true" if identified > 0 else "false",
                "reports_chi_lower_bound": "false",
                "reported_chi_lower_bound": "",
                "reports_beta_chi_lower_bound": "false",
                "reported_beta_chi_lower_bound": "",
                "admissibility_status": _panel_source_admissibility(row),
                "admissibility_obstacle": row["estimator_blocker"],
                "allowed_use": "direct_beta_chi_panel_source_screen",
                "blocked_use": (
                    "chi_floor_admission;beta_chi_floor_admission;"
                    "canonical_headline_promotion;evidence_mode_claim"
                ),
                "claim_boundary": (
                    "candidate_panel_only;does_not_change_beta_chi_grid_or_"
                    "scenario_math"
                ),
            }
        )
    return out


def write_direct_beta_chi_panel_outputs(
    output_dir: str | Path,
    *,
    panel_rows: Sequence[Mapping[str, str]],
    status_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write candidate panel CSVs."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "direct_beta_chi_panel_csv": out
        / "ratewall_direct_beta_chi_candidate_panel.csv",
        "direct_beta_chi_panel_status_csv": out
        / "ratewall_direct_beta_chi_candidate_panel_status.csv",
    }
    _write_csv(paths["direct_beta_chi_panel_csv"], DIRECT_BETA_CHI_PANEL_FIELDS, panel_rows)
    _write_csv(
        paths["direct_beta_chi_panel_status_csv"],
        DIRECT_BETA_CHI_PANEL_STATUS_FIELDS,
        status_rows,
    )
    return paths


def _panel_row(
    *,
    scenario_id: str,
    quarter: str,
    treatment: Mapping[str, Decimal | int],
    outcome_key: str,
    outcome: Mapping[str, Decimal],
    outcome_index: Mapping[str, int],
    outcome_quarters: Sequence[str],
    horizon: int,
) -> dict[str, str]:
    tdc = _decimal(treatment["tdc_change_ex_overlap_bil"])
    period_count = int(treatment["period_row_count"])
    current = outcome.get(quarter)
    gdp = outcome.get(f"GDP::{quarter}")
    future = None
    index = outcome_index.get(quarter)
    if index is not None:
        future_index = index + horizon + 1
        if future_index < len(outcome_quarters):
            future = outcome.get(outcome_quarters[future_index])
    matched = current is not None and future is not None and gdp not in {None, Decimal("0")}
    outcome_change = (future - current) / gdp if matched else None
    return {
        "direct_beta_chi_panel_row_id": (
            f"direct_beta_chi_panel::{scenario_id}::{quarter}::"
            f"{outcome_key}::h{horizon}"
        ),
        "scenario_id": scenario_id,
        "quarter": quarter,
        "outcome_series_key": outcome_key,
        "horizon_quarters": str(horizon),
        "period_row_count": str(period_count),
        "tdc_change_ex_overlap_bil": _fmt(tdc),
        "gdp_bil": _fmt_optional(gdp),
        "tdc_change_ex_overlap_share_of_gdp": _fmt_optional(
            tdc / gdp if gdp not in {None, Decimal("0")} else None
        ),
        "outcome_current_bil": _fmt_optional(current),
        "outcome_future_bil": _fmt_optional(future),
        "outcome_change_share_of_gdp": _fmt_optional(outcome_change),
        "matched_outcome_status": (
            "matched_observed_outcome" if matched else "blocked_missing_observed_outcome"
        ),
        "identification_status": "missing_no_external_or_predetermined_variation",
        "admission_status": "not_admitted_candidate_panel_only",
        "allowed_use": "direct_beta_chi_candidate_panel",
        "blocked_use": (
            "beta_chi_floor_admission_without_identified_lower_bound;"
            "canonical_headline_promotion;evidence_mode_claim"
        ),
        "claim_boundary": (
            "candidate_panel_only;does_not_change_beta_chi_grid_or_scenario_math"
        ),
    }


def _quarterly_tdc_treatments(root: Path) -> dict[tuple[str, str], dict[str, Decimal | int]]:
    rows = _read_first_existing_csv(
        root,
        (
            "tdcsim_period_tdc_summary.csv",
            "tdcsim_period_tdc_summary.csv.gz",
            "outputs/tdcsim_period_tdc_summary.csv",
            "outputs/tdcsim_period_tdc_summary.csv.gz",
        ),
    )
    out: dict[tuple[str, str], dict[str, Decimal | int]] = {}
    for row in rows:
        scenario_id = row.get("scenario_id", "")
        quarter = _quarter_from_date(row.get("period_end", ""))
        value = row.get("tdc_change_ex_overlap_bil", "")
        if not scenario_id or not quarter or not value:
            continue
        key = (scenario_id, quarter)
        current = out.setdefault(
            key,
            {"tdc_change_ex_overlap_bil": Decimal("0"), "period_row_count": 0},
        )
        current["tdc_change_ex_overlap_bil"] = _decimal(
            current["tdc_change_ex_overlap_bil"]
        ) + _decimal(value)
        current["period_row_count"] = int(current["period_row_count"]) + 1
    return out


def _read_outcome_series(
    root: Path,
    outcome_series_keys: Sequence[str],
) -> dict[str, dict[str, Decimal]]:
    gdp = _read_fred_csv(root / "GDP.csv", "GDP")
    out: dict[str, dict[str, Decimal]] = {}
    for series_id in outcome_series_keys:
        values = _read_fred_csv(root / f"{series_id}.csv", series_id)
        if not values:
            continue
        enriched = dict(values)
        for quarter, value in gdp.items():
            enriched[f"GDP::{quarter}"] = value
        out[series_id] = enriched
    return out


def _read_first_existing_csv(root: Path, names: Sequence[str]) -> list[dict[str, str]]:
    for name in names:
        path = root / name
        if not path.exists():
            continue
        if path.suffix == ".gz":
            return _read_gzip_csv(path)
        return _read_csv(path)
    return []


def _read_fred_csv(path: Path, value_field: str) -> dict[str, Decimal]:
    if not path.exists():
        return {}
    out: dict[str, Decimal] = {}
    for row in _read_csv(path):
        quarter = _quarter_from_date(row.get("observation_date", ""))
        value = row.get(value_field, "")
        if quarter and value:
            out[quarter] = _decimal(value)
    return out


def _panel_source_admissibility(row: Mapping[str, str]) -> str:
    if _int(row["treatment_quarter_count"]) == 0:
        return "not_admitted_missing_tdc_ex_overlap_treatment"
    if _int(row["matched_panel_rows"]) == 0:
        return "not_admitted_missing_current_demand_outcome"
    if _int(row["identified_panel_rows"]) == 0:
        return "not_admitted_missing_identification_strategy"
    return "not_admitted_missing_lower_bound"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_gzip_csv(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _quarter_from_date(value: str) -> str:
    if len(value) < 7:
        return ""
    year = value[:4]
    month = int(value[5:7])
    quarter = ((month - 1) // 3) + 1
    return f"{year}Q{quarter}"


def _quarter_sort_key(value: str) -> tuple[int, int]:
    if len(value) < 6 or "Q" not in value:
        return (0, 0)
    year, quarter = value.split("Q", maxsplit=1)
    return (int(year), int(quarter))


def _decimal(value: str | Decimal | int) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DirectBetaChiPanelError(f"invalid decimal: {value!r}") from exc


def _int(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise DirectBetaChiPanelError(f"invalid integer: {value!r}") from exc


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _fmt_optional(value: Decimal | None) -> str:
    if value is None:
        return ""
    return _fmt(value)
