"""Derived readout metrics over existing RWTAM CSV outputs.

This module deliberately reads already-materialized RWTAM outputs under
``var/rwtam``. It does not call the engine or rebuild the underlying objects.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.v1 import BANDS, START_YEAR, _d, _fmt, _write_rows


METRICS_OUTPUT_DIR = Path("var/rwtam/metrics")
METRICS_REPORT_PATH = Path("do/rwtam_metrics_pce_report_20260707.md")
DEFAULT_SOURCE_DIR = Path("var/rwtam/v1")
HORIZONS = (
    ("year_1", "annual", str(START_YEAR)),
    ("cum_120m", "cumulative_120_month", f"{START_YEAR}-{START_YEAR + 9}"),
)
INCIDENCE_HORIZONS = (("year_1", "annual", str(START_YEAR)),)
REQUIRED_SOURCE_FILES = {
    "rollup": "out_ratewall_rollup.csv",
    "monthly": "out_ratewall_monthly.csv",
    "ledger": "out_cashflow_leg_gross.csv",
    "public_interest": "out_government_interest_channel.csv",
}


@dataclass(frozen=True)
class DerivedMetricsResult:
    """CSV-ready derived metric tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_derived_metrics(source_dir: Path = DEFAULT_SOURCE_DIR) -> DerivedMetricsResult:
    missing = [
        str(source_dir / filename)
        for filename in REQUIRED_SOURCE_FILES.values()
        if not (source_dir / filename).exists()
    ]
    if missing:
        return _missing_source_result(source_dir, missing)

    rollup = _read(source_dir / REQUIRED_SOURCE_FILES["rollup"])
    monthly = _read(source_dir / REQUIRED_SOURCE_FILES["monthly"])
    ledger = _read(source_dir / REQUIRED_SOURCE_FILES["ledger"])
    public_interest = _read(source_dir / REQUIRED_SOURCE_FILES["public_interest"])

    attenuation = _attenuation_rows(rollup, source_dir)
    incidence = _incidence_rows(ledger, rollup, source_dir)
    fiscal = _fiscal_cost_rows(public_interest, rollup, source_dir)
    timing = _timing_profile_rows(monthly, source_dir)
    invariants = _invariant_rows(attenuation, incidence, fiscal, timing)
    source_status = [
        {
            "source_id": source_id,
            "source_path": str(source_dir / filename),
            "status": "pass",
            "message": "source_csv_loaded",
        }
        for source_id, filename in REQUIRED_SOURCE_FILES.items()
    ]
    return DerivedMetricsResult(
        {
            "out_metric_source_status": source_status,
            "out_attenuation_multiplier": attenuation,
            "out_wall_incidence_by_receiving_group": incidence,
            "out_fiscal_cost_per_unit_compression": fiscal,
            "out_timing_profile": timing,
            "out_derived_metrics_invariant_check": invariants,
        }
    )


def write_derived_metrics_outputs(
    result: DerivedMetricsResult,
    output_dir: Path = METRICS_OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_derived_metrics_report(
    result: DerivedMetricsResult,
    output_path: Path = METRICS_REPORT_PATH,
) -> Path:
    attenuation = result.rows("out_attenuation_multiplier")
    incidence = result.rows("out_wall_incidence_by_receiving_group")
    fiscal = result.rows("out_fiscal_cost_per_unit_compression")
    timing = result.rows("out_timing_profile")
    invariants = result.rows("out_derived_metrics_invariant_check")

    lines = [
        "# RWTAM derived metrics + PCE crosswalk report",
        "",
        "Date: 2026-07-07 UTC.",
        "Scope: derived readout over existing RWTAM CSVs; no tuning, no new estimation, no headline mutation.",
        "",
        "## Derived Metrics",
        "",
        "### Attenuation multiplier",
        "",
        "| horizon | band | source RW | multiplier |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in attenuation:
        lines.append(
            f"| {row['horizon']} | {row['band']} | {row['source_RW_ratio']} | {row['attenuation_multiplier']} |"
        )
    lines.extend(
        [
            "",
            "### Wall incidence",
            "",
            "| horizon | band | group | gross received | gross share | demand converted | converted share |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in incidence:
        if row["row_role"] == "group":
            lines.append(
                f"| {row['horizon']} | {row['band']} | {row['receiving_group']} | {row['gross_received_bil']} | {row['gross_received_share']} | {row['demand_converted_N_bil']} | {row['demand_converted_share_of_ledger_N']} |"
            )
    lines.extend(
        [
            "",
            "### Fiscal diagnostic ratio",
            "",
            "| horizon | public interest expense | drag minus support | ratio | status | label |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in fiscal:
        lines.append(
            f"| {row['horizon']} | {row['public_interest_expense_bil']} | {row['drag_minus_support_bil']} | {row['fiscal_cost_per_unit_compression']} | {row['compression_ratio_status']} | {row['interpretation_label']} |"
        )
    lines.extend(
        [
            "",
            "### Timing profile",
            "",
            "| band | month | RW | max month | crossover | degenerate flag |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for row in timing:
        if row["band"] == "base":
            lines.append(
                f"| {row['band']} | {row['month']} | {row['RW_ratio']} | {row['max_RW_month']} | {row['support_vs_drag_crossover_month']} | {row['rw_ratio_degenerate']} |"
            )
    lines.extend(
        [
            "",
            "## Invariants",
            "",
            "| check | status | message |",
            "| --- | --- | --- |",
        ]
    )
    for row in invariants:
        lines.append(f"| {row['check_id']} | {row['status']} | {row['message']} |")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _missing_source_result(source_dir: Path, missing: list[str]) -> DerivedMetricsResult:
    source_status = [
        {
            "source_id": "metric_source_missing",
            "source_path": path,
            "status": "fail",
            "message": "required_existing_csv_absent_no_recompute_attempted",
        }
        for path in missing
    ]
    invariant = [
        {
            "check_id": "DM0_required_sources_present",
            "status": "fail",
            "message": ";".join(missing),
        }
    ]
    empty = [
        {
            "horizon": "source_missing",
            "band": "source_missing",
            "metric_id": "source_missing",
            "source_path": str(source_dir),
            "status": "fail",
        }
    ]
    return DerivedMetricsResult(
        {
            "out_metric_source_status": source_status,
            "out_attenuation_multiplier": empty,
            "out_wall_incidence_by_receiving_group": empty,
            "out_fiscal_cost_per_unit_compression": empty,
            "out_timing_profile": empty,
            "out_derived_metrics_invariant_check": invariant,
        }
    )


def _attenuation_rows(rows: list[dict[str, str]], source_dir: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for horizon, period_type, period in HORIZONS:
        for band in BANDS:
            source = _rollup_row(rows, period_type, period, band)
            rw = _d(source["RW_ratio"])
            multiplier = Decimal("1") / (Decimal("1") - rw)
            out.append(
                {
                    "metric_id": "attenuation_multiplier",
                    "horizon": horizon,
                    "band": band,
                    "source_period_type": period_type,
                    "source_period": period,
                    "source_RW_ratio": source["RW_ratio"],
                    "attenuation_multiplier": _fmt(multiplier),
                    "arithmetic": "1/(1-RW)",
                    "source_path": str(source_dir / REQUIRED_SOURCE_FILES["rollup"]),
                }
            )
    return out


def _incidence_rows(
    ledger_rows: list[dict[str, str]],
    rollup_rows: list[dict[str, str]],
    source_dir: Path,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for horizon, period_type, period in INCIDENCE_HORIZONS:
        for band in BANDS:
            selected = _ledger_selection(ledger_rows, horizon, band)
            ledger_n = _d(_rollup_row(rollup_rows, period_type, period, band)["N_bil"])
            grouped: dict[str, dict[str, Decimal]] = {
                group: {"gross": Decimal("0"), "converted": Decimal("0")}
                for group in _incidence_group_order()
            }
            for row in selected:
                group = _receiving_group(row["cell_or_sector"])
                gross = _d(row["gross_flow_bil"])
                converted = _d(row["converted_effect_bil"])
                if gross > 0:
                    grouped[group]["gross"] += gross
                if converted > 0:
                    grouped[group]["converted"] += converted
            gross_total = sum(
                (_d(row["gross_flow_bil"]) for row in selected if _d(row["gross_flow_bil"]) > 0),
                Decimal("0"),
            )
            converted_total = sum(
                (
                    _d(row["converted_effect_bil"])
                    for row in selected
                    if _d(row["converted_effect_bil"]) > 0
                ),
                Decimal("0"),
            )
            for group in _incidence_group_order():
                values = grouped[group]
                out.append(
                    {
                        "metric_id": "wall_incidence_by_receiving_group",
                        "row_role": "group",
                        "horizon": horizon,
                        "band": band,
                        "receiving_group": group,
                        "gross_received_bil": _fmt(values["gross"]),
                        "gross_received_share": _fmt(_safe_ratio(values["gross"], gross_total)),
                        "demand_converted_N_bil": _fmt(values["converted"]),
                        "demand_converted_share_of_ledger_N": _fmt(_safe_ratio(values["converted"], ledger_n)),
                        "ledger_N_bil": _fmt(ledger_n),
                        "converted_sum_bil": _fmt(converted_total),
                        "source_path": str(source_dir / REQUIRED_SOURCE_FILES["ledger"]),
                    }
                )
            out.append(
                {
                    "metric_id": "wall_incidence_by_receiving_group",
                    "row_role": "identity",
                    "horizon": horizon,
                    "band": band,
                    "receiving_group": "sum_equals_ledger_N",
                    "gross_received_bil": _fmt(gross_total),
                    "gross_received_share": "1",
                    "demand_converted_N_bil": _fmt(converted_total),
                    "demand_converted_share_of_ledger_N": _fmt(_safe_ratio(converted_total, ledger_n)),
                    "ledger_N_bil": _fmt(ledger_n),
                    "converted_sum_bil": _fmt(converted_total),
                    "source_path": str(source_dir / REQUIRED_SOURCE_FILES["ledger"]),
                }
            )
    return out


def _fiscal_cost_rows(
    public_rows: list[dict[str, str]],
    rollup_rows: list[dict[str, str]],
    source_dir: Path,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    years_by_horizon = {
        "year_1": {str(START_YEAR)},
        "cum_120m": {str(year) for year in range(START_YEAR, START_YEAR + 10)},
    }
    period_by_horizon = {
        "year_1": ("annual", str(START_YEAR)),
        "cum_120m": ("cumulative_120_month", f"{START_YEAR}-{START_YEAR + 9}"),
    }
    for horizon in ("year_1", "cum_120m"):
        period_type, period = period_by_horizon[horizon]
        rollup = _rollup_row(rollup_rows, period_type, period, "base")
        drag_minus_support = _d(rollup["D_bil"]) - _d(rollup["N_bil"])
        ratio_available = drag_minus_support > 0
        public_expense = sum(
            (_d(row["cashflow_delta_bil"]) for row in public_rows if row["year"] in years_by_horizon[horizon]),
            Decimal("0"),
        )
        out.append(
            {
                "metric_id": "fiscal_cost_per_unit_compression",
                "horizon": horizon,
                "band": "base",
                "public_interest_expense_bil": _fmt(public_expense),
                "drag_minus_support_bil": _fmt(drag_minus_support),
                "fiscal_cost_per_unit_compression": (
                    _fmt(public_expense / drag_minus_support)
                    if ratio_available
                    else ""
                ),
                "compression_ratio_status": (
                    "available_positive_drag_minus_support"
                    if ratio_available
                    else "unavailable_nonpositive_drag_minus_support"
                ),
                "interpretation_label": "diagnostic_ratio_not_welfare_claim",
                "source_public_interest_path": str(source_dir / REQUIRED_SOURCE_FILES["public_interest"]),
                "source_rollup_path": str(source_dir / REQUIRED_SOURCE_FILES["rollup"]),
            }
        )
    return out


def _timing_profile_rows(rows: list[dict[str, str]], source_dir: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for band in BANDS:
        selected = [
            row
            for row in rows
            if row["period_type"] == "monthly"
            and row["band"] == band
            and row["ricardian_offset"] == "0"
            and row["dose_mode"] == "persistent_level"
        ]
        max_row = max(selected, key=lambda row: _d(row["RW_ratio"]))
        crossover = next(
            (row["period"] for row in selected if _d(row["N_bil"]) >= _d(row["D_bil"])),
            "",
        )
        for row in selected:
            out.append(
                {
                    "metric_id": "timing_profile",
                    "dose_mode": row["dose_mode"],
                    "band": band,
                    "month": row["period"],
                    "month_index": row["month_index"],
                    "N_bil": row["N_bil"],
                    "D_bil": row["D_bil"],
                    "RW_ratio": row["RW_ratio"],
                    "max_RW_month": max_row["period"],
                    "max_RW_ratio": max_row["RW_ratio"],
                    "support_vs_drag_crossover_month": crossover,
                    "rw_ratio_degenerate": row.get("rw_ratio_degenerate", "source_column_absent"),
                    "source_path": str(source_dir / REQUIRED_SOURCE_FILES["monthly"]),
                }
            )
    return out


def _invariant_rows(
    attenuation: list[dict[str, str]],
    incidence: list[dict[str, str]],
    fiscal: list[dict[str, str]],
    timing: list[dict[str, str]],
) -> list[dict[str, str]]:
    incidence_identities = [row for row in incidence if row["row_role"] == "identity"]
    incidence_ok = all(
        abs(_d(row["converted_sum_bil"]) - _d(row["ledger_N_bil"])) <= Decimal("0.000000000000001")
        for row in incidence_identities
    )
    attenuation_ok = all(
        _d(row["attenuation_multiplier"])
        == Decimal("1") / (Decimal("1") - _d(row["source_RW_ratio"]))
        for row in attenuation
    )
    fiscal_errors = validate_fiscal_cost_rows(fiscal)
    timing_ok = bool(timing) and all(row["RW_ratio"] for row in timing)
    return [
        {"check_id": "DM1_attenuation_arithmetic_exact", "status": "pass" if attenuation_ok else "fail", "message": "multiplier equals 1/(1-RW) from source rows"},
        {"check_id": "DM2_incidence_converted_sum_equals_ledger_N", "status": "pass" if incidence_ok else "fail", "message": "positive converted incidence regrouping equals rollup N"},
        {"check_id": "DM3_fiscal_ratio_labeled_diagnostic", "status": "pass" if not fiscal_errors else "fail", "message": ";".join(fiscal_errors) or "ratio is labeled diagnostic, sign-guarded, and not welfare"},
        {"check_id": "DM4_timing_profile_monthly_source_rows", "status": "pass" if timing_ok else "fail", "message": "monthly RW rows surfaced with max and crossover fields"},
    ]


def _rollup_row(rows: list[dict[str, str]], period_type: str, period: str, band: str) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row["period_type"] == period_type
        and row["period"] == period
        and row["band"] == band
        and row["ricardian_offset"] == "0"
        and row["dose_mode"] == "persistent_level"
    )


def _ledger_selection(rows: list[dict[str, str]], horizon: str, band: str) -> list[dict[str, str]]:
    if horizon == "year_1":
        return [
            row
            for row in rows
            if row["period_type"] == "annual"
            and row["period"] == str(START_YEAR)
            and row["band"] == band
            and row["ricardian_offset"] == "0"
            and row["dose_mode"] == "persistent_level"
        ]
    years = {str(year) for year in range(START_YEAR, START_YEAR + 10)}
    return [
        row
        for row in rows
        if row["period_type"] == "annual"
        and row["period"] in years
        and row["band"] == band
        and row["ricardian_offset"] == "0"
        and row["dose_mode"] == "persistent_level"
    ]


def _incidence_group_order() -> tuple[str, ...]:
    return (
        "constrained_borrowers",
        "middle",
        "retirees",
        "unconstrained_savers",
        "firms",
        "state_local",
        "RoW_leaked",
        "no_conversion",
    )


def _receiving_group(cell: str) -> str:
    mapping = {
        "hh_constrained_net_borrower": "constrained_borrowers",
        "hh_middle_owner_illiquid": "middle",
        "hh_retiree_fixed_income_saver": "retirees",
        "hh_unconstrained_saver": "unconstrained_savers",
        "firm_bank_dependent_small": "firms",
        "firm_market_funded_large": "firms",
        "state_local_public_cell": "state_local",
        "rest_of_world_external_cell": "RoW_leaked",
    }
    return mapping.get(cell, "no_conversion")


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return numerator / denominator


def validate_fiscal_cost_rows(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for row in rows:
        drag_minus_support = _d(row["drag_minus_support_bil"])
        ratio = row["fiscal_cost_per_unit_compression"]
        status = row["compression_ratio_status"]
        if row["interpretation_label"] != "diagnostic_ratio_not_welfare_claim":
            errors.append(f"{row['horizon']}: ratio is not labeled diagnostic")
        if drag_minus_support <= 0:
            if ratio:
                errors.append(
                    f"{row['horizon']}: nonpositive drag-minus-support must not emit a compression ratio"
                )
            if status != "unavailable_nonpositive_drag_minus_support":
                errors.append(
                    f"{row['horizon']}: nonpositive drag-minus-support status is invalid"
                )
            continue
        expected = _d(row["public_interest_expense_bil"]) / drag_minus_support
        if not ratio or _d(ratio) != expected:
            errors.append(f"{row['horizon']}: compression ratio arithmetic is invalid")
        if status != "available_positive_drag_minus_support":
            errors.append(f"{row['horizon']}: positive drag-minus-support status is invalid")
    return errors


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
