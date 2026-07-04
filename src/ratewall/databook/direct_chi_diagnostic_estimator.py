"""Diagnostic direct-chi estimator candidate for RateWall.

This module deliberately does not admit a chi floor. It measures whether current
local series can even produce a reproducible treatment/outcome diagnostic, then
records why the result is not a valid RateWall chi estimate.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.direct_chi_evidence import (
    DEFAULT_LOCAL_CURRENT_DEMAND_DIR,
)

DEFAULT_TDCEST_ESTIMATES_PATH = Path(
    "data/raw/ratewall_sibling_calibration/tdcest_tdc_estimates.csv"
)

DIRECT_CHI_DIAGNOSTIC_ESTIMATOR_FIELDS = [
    "direct_chi_diagnostic_estimator_row_id",
    "estimator_id",
    "treatment_series_key",
    "outcome_series_key",
    "sample_start",
    "sample_end",
    "observation_count",
    "horizon_quarters",
    "treatment_unit",
    "outcome_unit",
    "coefficient",
    "standard_error",
    "ci95_low",
    "ci95_high",
    "reported_chi_lower_bound",
    "reports_chi_lower_bound",
    "reports_beta_chi_lower_bound",
    "admissibility_status",
    "admissibility_obstacle",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class DirectChiDiagnosticEstimatorError(ValueError):
    """Raised when the diagnostic estimator cannot be computed."""


@dataclass(frozen=True)
class DirectChiDiagnosticEstimatorPaths:
    """Source paths for the diagnostic estimator."""

    tdcest_estimates_path: Path = DEFAULT_TDCEST_ESTIMATES_PATH
    local_current_demand_dir: Path = DEFAULT_LOCAL_CURRENT_DEMAND_DIR


def direct_chi_diagnostic_estimator_rows(
    *,
    paths: DirectChiDiagnosticEstimatorPaths = DirectChiDiagnosticEstimatorPaths(),
    treatment_series_keys: Sequence[str] = (
        "tdc_tier2_interest_corrected_bank_only_ru_flow",
        "tdc_tier2_canonical_depository_institution_mmf_rrp_prop_ru_flow",
        "tdc_tier3_fiscal_corrected_bank_only_ru_flow",
    ),
    outcome_series_keys: Sequence[str] = ("PCEC", "LA0000031Q027SBEA"),
    horizons: Sequence[int] = (0, 1),
) -> list[dict[str, str]]:
    """Estimate diagnostic current-demand responses to TDC proxy series."""

    tdc = _read_tdc_series(paths.tdcest_estimates_path)
    outcomes = _read_outcome_series(paths.local_current_demand_dir)
    rows: list[dict[str, str]] = []
    for treatment_key in treatment_series_keys:
        treatment = tdc.get(treatment_key, {})
        for outcome_key in outcome_series_keys:
            outcome = outcomes.get(outcome_key, {})
            for horizon in horizons:
                sample = _estimation_sample(
                    treatment=treatment,
                    outcome=outcome,
                    horizon=horizon,
                )
                row_id = (
                    "direct_chi_diagnostic_estimator::"
                    f"{treatment_key}::{outcome_key}::h{horizon}"
                )
                if len(sample) < 12:
                    rows.append(
                        _blocked_row(
                            row_id=row_id,
                            treatment_key=treatment_key,
                            outcome_key=outcome_key,
                            horizon=horizon,
                            sample=sample,
                            obstacle="insufficient_overlap_sample_for_diagnostic_ols",
                        )
                    )
                    continue
                estimate = _ols_slope_hc1(sample)
                if estimate is None:
                    rows.append(
                        _blocked_row(
                            row_id=row_id,
                            treatment_key=treatment_key,
                            outcome_key=outcome_key,
                            horizon=horizon,
                            sample=sample,
                            obstacle="singular_design_or_zero_treatment_variance",
                        )
                    )
                    continue
                coef, se, low, high = estimate
                rows.append(
                    {
                        "direct_chi_diagnostic_estimator_row_id": row_id,
                        "estimator_id": (
                            "diagnostic_ols_current_demand_change_on_tdc_share"
                        ),
                        "treatment_series_key": treatment_key,
                        "outcome_series_key": outcome_key,
                        "sample_start": sample[0]["quarter"],
                        "sample_end": sample[-1]["quarter"],
                        "observation_count": str(len(sample)),
                        "horizon_quarters": str(horizon),
                        "treatment_unit": "tdc_proxy_flow_share_of_nominal_gdp",
                        "outcome_unit": (
                            "nominal_current_demand_saar_quarterly_change_"
                            "share_of_nominal_gdp"
                        ),
                        "coefficient": _fmt(coef),
                        "standard_error": _fmt(se),
                        "ci95_low": _fmt(low),
                        "ci95_high": _fmt(high),
                        "reported_chi_lower_bound": "",
                        "reports_chi_lower_bound": "false",
                        "reports_beta_chi_lower_bound": "false",
                        "admissibility_status": (
                            "not_admitted_diagnostic_only_no_identification"
                        ),
                        "admissibility_obstacle": (
                            "short_recent_sample;tdc_proxy_not_exact_ex_overlap;"
                            "no_external_instrument_or_shock;outcome_is_aggregate_"
                            "current_demand_not_recipient_spending"
                        ),
                        "allowed_use": (
                            "diagnostic_estimator_pipeline_and_scale_check_only"
                        ),
                        "blocked_use": (
                            "chi_floor_admission;beta_chi_floor_admission;"
                            "canonical_headline_promotion;evidence_mode_claim;"
                            "posterior_chi_claim"
                        ),
                        "claim_boundary": (
                            "diagnostic_only;does_not_change_beta_chi_grid_or_"
                            "scenario_math"
                        ),
                    }
                )
    return sorted(
        rows,
        key=lambda row: (
            row["treatment_series_key"],
            row["outcome_series_key"],
            int(row["horizon_quarters"]),
        ),
    )


def write_direct_chi_diagnostic_estimator_outputs(
    output_dir: str | Path,
    *,
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write diagnostic estimator CSV and memo."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "diagnostic_estimator_csv": out
        / "ratewall_direct_chi_diagnostic_estimator.csv",
        "diagnostic_estimator_memo_md": out
        / "direct_chi_diagnostic_estimator_memo.md",
    }
    _write_csv(
        paths["diagnostic_estimator_csv"],
        DIRECT_CHI_DIAGNOSTIC_ESTIMATOR_FIELDS,
        rows,
    )
    paths["diagnostic_estimator_memo_md"].write_text(
        direct_chi_diagnostic_estimator_memo_markdown(rows),
        encoding="utf-8",
    )
    return paths


def direct_chi_diagnostic_estimator_memo_markdown(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Return a concise diagnostic-estimator memo."""

    computed = [
        row
        for row in rows
        if row["admissibility_status"]
        == "not_admitted_diagnostic_only_no_identification"
    ]
    admitted = [row for row in rows if row["reports_chi_lower_bound"] == "true"]
    lines = [
        "# Direct Chi Diagnostic Estimator Memo",
        "",
        "## Bottom Line",
        "",
        (
            "The diagnostic estimator runs, but it does not admit a χ or β×χ "
            "floor. The current local historical sample is short, uses TDC proxy "
            "series rather than exact ex-overlap treatment, and lacks an external "
            "instrument or shock design."
        ),
        "",
        "## Counts",
        "",
        f"- Estimator rows: `{len(rows)}`.",
        f"- Computed diagnostic rows: `{len(computed)}`.",
        f"- Admitted lower-bound rows: `{len(admitted)}`.",
        "",
        "## Model Consequence",
        "",
        (
            "This validates the estimator plumbing and scale checks only. It does "
            "not reclassify holder or combined scenarios."
        ),
    ]
    return "\n".join(lines) + "\n"


def direct_chi_diagnostic_source_candidate_rows(
    rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Convert diagnostic estimator rows into direct-chi source inventory rows."""

    out: list[dict[str, str]] = []
    for row in rows:
        out.append(
            {
                "direct_chi_source_row_id": (
                    "direct_chi_source::diagnostic_estimator::"
                    f"{row['treatment_series_key']}::{row['outcome_series_key']}::"
                    f"h{row['horizon_quarters']}"
                ),
                "source_family": "ratewall_direct_chi_diagnostic_estimator",
                "source_artifact": (
                    "var/preliminary_scenario_results/direct_chi_evidence/"
                    "ratewall_direct_chi_diagnostic_estimator.csv"
                ),
                "candidate_role": "diagnostic_tdc_current_demand_estimator",
                "row_count": row["observation_count"],
                "has_tdc_ex_overlap_treatment": "false",
                "has_materialized_tdc_treatment": "true",
                "has_current_demand_outcome": "true",
                "has_identification_strategy": "false",
                "reports_chi_lower_bound": "false",
                "reported_chi_lower_bound": "",
                "reports_beta_chi_lower_bound": "false",
                "reported_beta_chi_lower_bound": "",
                "admissibility_status": row["admissibility_status"],
                "admissibility_obstacle": row["admissibility_obstacle"],
                "allowed_use": "diagnostic_estimator_source_screen",
                "blocked_use": (
                    "chi_floor_admission;beta_chi_floor_admission;"
                    "canonical_headline_promotion;evidence_mode_claim"
                ),
                "claim_boundary": (
                    "diagnostic_estimator_only;does_not_change_beta_chi_grid_or_"
                    "scenario_math"
                ),
            }
        )
    return out


def _estimation_sample(
    *,
    treatment: Mapping[str, Decimal],
    outcome: Mapping[str, Decimal],
    horizon: int,
) -> list[dict[str, Decimal | str]]:
    quarters = sorted(set(treatment) & set(outcome))
    outcome_quarters = sorted(
        quarter for quarter in outcome if not quarter.startswith("GDP::")
    )
    outcome_index = {quarter: index for index, quarter in enumerate(outcome_quarters)}
    sample: list[dict[str, Decimal | str]] = []
    for quarter in quarters:
        index = outcome_index.get(quarter)
        if index is None:
            continue
        future_index = index + horizon + 1
        if future_index >= len(outcome_quarters):
            continue
        future_quarter = outcome_quarters[future_index]
        current = outcome.get(quarter)
        future = outcome.get(future_quarter)
        tdc_value = treatment.get(quarter)
        gdp_value = outcome.get(f"GDP::{quarter}")
        if None in {current, future, tdc_value, gdp_value} or gdp_value == 0:
            continue
        sample.append(
            {
                "quarter": quarter,
                "x": tdc_value / gdp_value,
                "y": (future - current) / gdp_value,
            }
        )
    return sample


def _ols_slope_hc1(
    sample: Sequence[Mapping[str, Decimal | str]],
) -> tuple[Decimal, Decimal, Decimal, Decimal] | None:
    xs = [float(row["x"]) for row in sample]
    ys = [float(row["y"]) for row in sample]
    n = len(xs)
    x_bar = sum(xs) / n
    y_bar = sum(ys) / n
    sxx = sum((x - x_bar) ** 2 for x in xs)
    if sxx == 0:
        return None
    beta = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys, strict=True)) / sxx
    alpha = y_bar - beta * x_bar
    leverage_den = sxx
    meat = 0.0
    for x, y in zip(xs, ys, strict=True):
        residual = y - alpha - beta * x
        leverage_x = x - x_bar
        meat += leverage_x * leverage_x * residual * residual
    variance = (n / (n - 2)) * meat / (leverage_den * leverage_den)
    se = math.sqrt(max(variance, 0.0))
    low = beta - 1.96 * se
    high = beta + 1.96 * se
    return (Decimal(str(beta)), Decimal(str(se)), Decimal(str(low)), Decimal(str(high)))


def _read_tdc_series(path: Path) -> dict[str, dict[str, Decimal]]:
    rows = _read_csv(path)
    out: dict[str, dict[str, Decimal]] = {}
    if not rows:
        return out
    fields = [field for field in rows[0] if field != "date"]
    for field in fields:
        series: dict[str, Decimal] = {}
        for row in rows:
            value = row.get(field, "")
            quarter = _quarter_from_date(row.get("date", ""))
            if value and quarter:
                # TDC-est exports millions; convert to billions for GDP-scale work.
                series[quarter] = _decimal(value) / Decimal("1000")
        if series:
            out[field] = series
    return out


def _read_outcome_series(root: Path) -> dict[str, dict[str, Decimal]]:
    gdp = _read_fred_csv(root / "GDP.csv", "GDP")
    out: dict[str, dict[str, Decimal]] = {}
    for series_id in ("PCEC", "LA0000031Q027SBEA"):
        values = _read_fred_csv(root / f"{series_id}.csv", series_id)
        if not values:
            continue
        enriched = dict(values)
        for quarter, value in gdp.items():
            enriched[f"GDP::{quarter}"] = value
        out[series_id] = enriched
    return out


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


def _blocked_row(
    *,
    row_id: str,
    treatment_key: str,
    outcome_key: str,
    horizon: int,
    sample: Sequence[Mapping[str, Decimal | str]],
    obstacle: str,
) -> dict[str, str]:
    return {
        "direct_chi_diagnostic_estimator_row_id": row_id,
        "estimator_id": "diagnostic_ols_current_demand_change_on_tdc_share",
        "treatment_series_key": treatment_key,
        "outcome_series_key": outcome_key,
        "sample_start": str(sample[0]["quarter"]) if sample else "",
        "sample_end": str(sample[-1]["quarter"]) if sample else "",
        "observation_count": str(len(sample)),
        "horizon_quarters": str(horizon),
        "treatment_unit": "tdc_proxy_flow_share_of_nominal_gdp",
        "outcome_unit": (
            "nominal_current_demand_saar_quarterly_change_share_of_nominal_gdp"
        ),
        "coefficient": "",
        "standard_error": "",
        "ci95_low": "",
        "ci95_high": "",
        "reported_chi_lower_bound": "",
        "reports_chi_lower_bound": "false",
        "reports_beta_chi_lower_bound": "false",
        "admissibility_status": "not_admitted_blocked_diagnostic_estimator",
        "admissibility_obstacle": obstacle,
        "allowed_use": "diagnostic_estimator_pipeline_check",
        "blocked_use": (
            "chi_floor_admission;beta_chi_floor_admission;"
            "canonical_headline_promotion;evidence_mode_claim"
        ),
        "claim_boundary": (
            "diagnostic_only;does_not_change_beta_chi_grid_or_scenario_math"
        ),
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
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


def _decimal(value: str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DirectChiDiagnosticEstimatorError(f"invalid decimal: {value!r}") from exc


def _fmt(value: Decimal) -> str:
    return format(value, "f")
