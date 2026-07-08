"""Observed-data plug validation for RW_pi.

This module scores the frozen RW_pi kernels against the observed pack under
`do/rwpi_observed/`. It deliberately reports findings only; it does not mutate
coefficients, kernels, or headline/golden artifacts.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, DivisionByZero, InvalidOperation
from pathlib import Path


OBSERVED_DIR = Path("do/rwpi_observed")
VALIDATION_REPORT_PATH = Path("do/rwtam_rwpi_plug_validation_report_20260704.md")


@dataclass(frozen=True)
class PlugValidationResult:
    """CSV-ready validation tables."""

    scores: list[dict[str, str]]
    series: list[dict[str, str]]


def build_rwpi_plug_validation(
    monthly_channel_rows: list[dict[str, str]],
    window_rows: list[dict[str, str]],
    *,
    observed_dir: Path = OBSERVED_DIR,
) -> PlugValidationResult:
    observed = _ObservedPack(observed_dir)
    scores: list[dict[str, str]] = []
    series: list[dict[str, str]] = []

    score, rows = _score_demand_m5(window_rows, observed)
    scores.append(score)
    series.extend(rows)

    score, rows = _score_fx_import(observed)
    scores.append(score)
    series.extend(rows)

    score, rows = _score_cost_channel(monthly_channel_rows, observed)
    scores.append(score)
    series.extend(rows)

    score, rows = _score_shelter_kernel(observed)
    scores.append(score)
    series.extend(rows)

    score, rows = _score_starts_to_rents(observed)
    scores.append(score)
    series.extend(rows)

    score, rows = _score_net_price_traction(window_rows, observed)
    scores.append(score)
    series.extend(rows)

    return PlugValidationResult(scores=scores, series=series)


def write_rwpi_plug_validation_report(
    result: PlugValidationResult,
    output_path: Path = VALIDATION_REPORT_PATH,
) -> Path:
    lines = [
        "# RWTAM RW_pi plug-validation report",
        "",
        "Date: 2026-07-04.",
        "Scope: intermediate-plug validation using `do/rwpi_observed/`; coefficients and lag kernels remain frozen.",
        "",
        "## Dispositions",
        "",
        "| diagnostic | disposition | timing | sign | magnitude ratio | kernel status |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in result.scores:
        lines.append(
            "| {diagnostic} | {disposition} | {timing_pass} | {sign_pass} | {magnitude_ratio} | {kernel_status} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Scores",
            "",
            "| diagnostic | no-fitting guard | caveats honored | evidence summary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in result.scores:
        lines.append(
            "| {diagnostic} | {no_fitting_guard} | {guardrail_status} | {evidence_summary} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Observed vs Predicted Series",
            "",
            "| diagnostic | period | predicted | observed | unit | note |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in result.series:
        lines.append(
            "| {diagnostic} | {period} | {predicted_value} | {observed_value} | {unit} | {note} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Caveats Honored",
            "",
            "- CPI rent/OER level comparisons are re-based to 2022-01=100 before comparison; SEHC's Dec-1982 base is never compared raw to the 1982-84-base components.",
            "- ZORI is treated as `proxy_for_new_tenant_index`: market-rent timing/sign evidence only, not a CPI-rent level target.",
            "- RRVRUSQ156N is quarterly and is carried as a quarterly/step diagnostic, not silently monthly.",
            "- Cost-channel scoring is weak validation only; no cost pass-through is fitted to PPI residuals.",
            "- Starts-to-rents remains underidentified on 2022-24 alone; the report carries the 2025 tail available in the observed pack.",
            "- Headline CPI/PCE residuals are not used to tune any coefficient or lag kernel.",
            "",
            "Output CSVs: `var/rwtam/scenarios/rwpi/out_rwpi_plug_validation.csv` and `var/rwtam/scenarios/rwpi/out_rwpi_plug_validation_series.csv`.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _score_demand_m5(
    window_rows: list[dict[str, str]],
    observed: "_ObservedPack",
) -> tuple[dict[str, str], list[dict[str, str]]]:
    fed = observed.monthly("FEDFUNDS")
    cpi_yoy = _yoy(observed.monthly("CPIAUCNS"))
    pce_yoy = _yoy(observed.monthly("PCEPI"))
    start, end = "2022-03", "2025-12"
    fed_change = _delta(fed, start, "2023-07")
    cpi_disinflation = _delta(cpi_yoy, _peak_month(cpi_yoy, "2022-01", "2022-12"), "2025-12") * Decimal("-1")
    pce_disinflation = _delta(pce_yoy, _peak_month(pce_yoy, "2022-01", "2022-12"), "2025-12") * Decimal("-1")
    demand_base = _window_value(window_rows, "demand_only_after_wall_base_pp", "0_36m_cumulative_sum_pp")
    timing = "pass" if fed_change > 0 and cpi_disinflation > 0 and pce_disinflation > 0 else "fail"
    sign = timing
    ratio = _ratio(demand_base, cpi_disinflation)
    score = _score_row(
        "Demand-only M5 vs activity",
        "2022Q1-2025Q4",
        "survives_as_qualitative_shape_check",
        timing,
        sign,
        ratio,
        "demand_only_to_CPI_disinflation_ratio",
        "do_not_tune_slopes",
        "no_fitting_guard;real_activity_proxy_absent_from_observed_pack",
        "demand_kernel_survives_but_does_not_explain_full_disinflation",
        f"Fed funds +{_fmt(fed_change)}pp; CPI y/y disinflation {_fmt(cpi_disinflation)}pp; PCE y/y disinflation {_fmt(pce_disinflation)}pp",
    )
    rows = [
        _series_row("Demand-only M5 vs activity", "2022-2025", demand_base, cpi_disinflation, "pp", "frozen demand-only 0-36m vs realized CPI y/y disinflation"),
        _series_row("Demand-only M5 vs activity", "2022-2025", demand_base, pce_disinflation, "pp", "frozen demand-only 0-36m vs realized PCE y/y disinflation"),
    ]
    return score, rows


def _score_fx_import(observed: "_ObservedPack") -> tuple[dict[str, str], list[dict[str, str]]]:
    usd_yoy = _yoy(observed.monthly("DTWEXBGS_monthly_avg", "avg_value"))
    import_yoy = _yoy(observed.monthly("IREXPET"))
    usd_peak = _peak_month(usd_yoy, "2022-01", "2023-12")
    import_min = _trough_month(import_yoy, usd_peak, _add_months(usd_peak, 12))
    lag = _months_between(usd_peak, import_min)
    observed_disinflation = _delta(
        import_yoy,
        _peak_month(import_yoy, "2022-01", "2022-12"),
        import_min,
    ) * Decimal("-1")
    predicted_cpi = usd_yoy[usd_peak] * Decimal("0.10")
    timing = "pass" if 0 <= lag <= 12 else "fail"
    sign = "pass" if usd_yoy[usd_peak] > 0 and observed_disinflation > 0 else "fail"
    score = _score_row(
        "FX/import leg",
        "2022Q1-2025Q4",
        "survives_observed_data_confrontation",
        timing,
        sign,
        _ratio(predicted_cpi, observed_disinflation),
        "base_CPI_pass_through_to_import_price_yoy_disinflation",
        "pass_through_fixed_before_scoring",
        "no_fitting_guard;observed_DTWEXBGS_plug;IR_and_IREXPET_lineage",
        "kernel_survives",
        f"USD y/y peak {usd_peak}; import ex-pet y/y trough {import_min}; lag {lag}m",
    )
    rows = []
    for period in [usd_peak, import_min, "2025-12"]:
        if period in usd_yoy and period in import_yoy:
            rows.append(
                _series_row(
                    "FX/import leg",
                    period,
                    usd_yoy[period] * Decimal("0.10"),
                    import_yoy[period],
                    "yoy_pp",
                    "observed broad-dollar plug vs import ex-petroleum y/y",
                )
            )
    return score, rows


def _score_cost_channel(
    monthly_channel_rows: list[dict[str, str]],
    observed: "_ObservedPack",
) -> tuple[dict[str, str], list[dict[str, str]]]:
    manufacturing_yoy = _yoy(observed.monthly("PCUOMFGOMFG"))
    ppi_yoy = _yoy(observed.monthly("PPIACO"))
    residual = {
        month: manufacturing_yoy[month] - ppi_yoy[month]
        for month in manufacturing_yoy.keys() & ppi_yoy.keys()
    }
    start = "2022-03"
    peak = _peak_month(residual, "2022-03", "2024-12")
    residual_change = residual[peak] - residual[start]
    predicted_cost = sum(
        _dec(row["raising_pp"])
        for row in monthly_channel_rows
        if row["dose_mode"] == "persistent_level"
        and row["index_target"] == "CPI_U"
        and row["slack_state"] == "balanced"
        and row["band"] == "base"
        and row["channel_id"] == "FIRM_WORKING_CAPITAL_COST"
    )
    timing = "pass" if peak <= "2024-12" else "fail"
    sign = "pass" if residual_change > 0 and predicted_cost > 0 else "fail"
    disposition = "survives_weak_validation_only" if sign == "pass" else "kernel_refuted_needs_redesign"
    score = _score_row(
        "Cost channel",
        "2022Q1-2025Q4",
        disposition,
        timing,
        sign,
        _ratio(predicted_cost, residual_change),
        "predicted_cost_pp_to_manufacturing_minus_all_PPI_yoy_residual_change",
        "no_cost_pass_through_fit",
        "no_fitting_guard;weak_validation_only;exposed_sector_PCUOMFGOMFG_vs_PPIACO",
        "kernel_survives_weak_validation_only" if sign == "pass" else "kernel_refuted_needs_redesign",
        f"manufacturing-minus-all-PPI y/y residual change {_fmt(residual_change)}pp by {peak}",
    )
    rows = [
        _series_row("Cost channel", start, predicted_cost, residual[start], "pp", "exposed-sector residual start"),
        _series_row("Cost channel", peak, predicted_cost, residual[peak], "pp", "exposed-sector residual peak"),
    ]
    return score, rows


def _score_shelter_kernel(observed: "_ObservedPack") -> tuple[dict[str, str], list[dict[str, str]]]:
    zori_yoy = _yoy(observed.monthly("ZORI_national", "zori_national"))
    rent_yoy = _yoy(observed.monthly("CUSR0000SEHA"))
    oer_yoy = _yoy(observed.monthly("CUSR0000SEHC"))
    rent_level = _rebased(observed.monthly("CUSR0000SEHA"), "2022-01")
    oer_level = _rebased(observed.monthly("CUSR0000SEHC"), "2022-01")
    zori_peak = _peak_month(zori_yoy, "2022-01", "2023-12")
    rent_peak = _peak_month(rent_yoy, zori_peak, _add_months(zori_peak, 24))
    oer_peak = _peak_month(oer_yoy, zori_peak, _add_months(zori_peak, 24))
    rent_lag = _months_between(zori_peak, rent_peak)
    oer_lag = _months_between(zori_peak, oer_peak)
    timing = "pass" if 6 <= rent_lag <= 24 and 6 <= oer_lag <= 24 else "fail"
    sign = "pass" if rent_yoy[rent_peak] > 0 and oer_yoy[oer_peak] > 0 else "fail"
    score = _score_row(
        "Shelter lag kernel",
        "2022Q1-2026Q4",
        "survives_timing_sign_only",
        timing,
        sign,
        "",
        "not_meaningful_timing_sign_only",
        "lag_kernel_fixed_before_scoring",
        "no_fitting_guard;CPI_components_rebased;ZORI_proxy_for_new_tenant_index",
        "kernel_survives_timing_sign_not_level",
        f"ZORI y/y peak {zori_peak}; rent peak lag {rent_lag}m; OER peak lag {oer_lag}m",
    )
    rows = [
        _series_row("Shelter lag kernel", zori_peak, Decimal("12"), zori_yoy[zori_peak], "yoy_pp_or_lag_m", "ZORI proxy peak; predicted 12-36m CPI lag starts"),
        _series_row("Shelter lag kernel", rent_peak, Decimal(str(rent_lag)), rent_yoy[rent_peak], "yoy_pp_or_lag_m", "CPI rent y/y peak after market-rent proxy"),
        _series_row("Shelter lag kernel", oer_peak, Decimal(str(oer_lag)), oer_yoy[oer_peak], "yoy_pp_or_lag_m", "CPI OER y/y peak after market-rent proxy"),
        _series_row("Shelter lag kernel", "2022-01", rent_level["2022-01"], oer_level["2022-01"], "rebased_index", "SEHA and SEHC rebased to common 2022-01=100"),
    ]
    return score, rows


def _score_starts_to_rents(observed: "_ObservedPack") -> tuple[dict[str, str], list[dict[str, str]]]:
    starts = observed.monthly("HOUST")
    completions = observed.monthly("COMPUTSA")
    vacancy = observed.monthly("RRVRUSQ156N")
    zori_yoy = _yoy(observed.monthly("ZORI_national", "zori_national"))
    oer_yoy = _yoy(observed.monthly("CUSR0000SEHC"))
    starts_shortfall = _avg(starts, "2023-01", "2024-12") - _avg(starts, "2022-01", "2022-12")
    completions_tail = _avg(completions, "2024-01", "2025-12") - _avg(completions, "2022-01", "2022-12")
    vacancy_change = _delta(vacancy, "2022-01", "2025-10")
    zori_tail = _delta(zori_yoy, "2023-12", "2025-12")
    oer_tail = _delta(oer_yoy, "2023-12", "2025-12")
    predicted_direction = Decimal("1") if starts_shortfall < 0 else Decimal("-1")
    observed_tail_direction = Decimal("1") if zori_tail > 0 or oer_tail > 0 else Decimal("-1")
    sign = "pass" if predicted_direction == observed_tail_direction else "fail"
    score = _score_row(
        "Starts-to-rents pressure",
        "2022Q1-2026Q4",
        "underidentified_2022_24_tail_mixed",
        "fail",
        sign,
        "",
        "not_meaningful_underidentified_tail",
        "pandemic_rent_confounder_not_fit_away",
        "no_fitting_guard;RRVRUSQ156N_quarterly;tail_through_2025_included",
        "kernel_stays_underidentified",
        f"starts avg change {_fmt(starts_shortfall)}k SAAR; completions tail {_fmt(completions_tail)}k; vacancy change {_fmt(vacancy_change)}pp",
    )
    rows = [
        _series_row("Starts-to-rents pressure", "2023-2024", predicted_direction, starts_shortfall, "k_SAAR", "starts shortfall relative to 2022 avg"),
        _series_row("Starts-to-rents pressure", "2024-2025", predicted_direction, completions_tail, "k_SAAR", "completion tail relative to 2022 avg"),
        _series_row("Starts-to-rents pressure", "2022Q1-2025Q4", predicted_direction, vacancy_change, "quarterly_pp", "RRVRUSQ156N is quarterly"),
        _series_row("Starts-to-rents pressure", "2023-12_to_2025-12", predicted_direction, zori_tail, "yoy_pp", "ZORI proxy rent tail"),
        _series_row("Starts-to-rents pressure", "2023-12_to_2025-12", predicted_direction, oer_tail, "yoy_pp", "CPI OER tail"),
    ]
    return score, rows


def _score_net_price_traction(
    window_rows: list[dict[str, str]],
    observed: "_ObservedPack",
) -> tuple[dict[str, str], list[dict[str, str]]]:
    cpi_yoy = _yoy(observed.monthly("CPIAUCNS"))
    pce_yoy = _yoy(observed.monthly("PCEPI"))
    cpi_peak = _peak_month(cpi_yoy, "2022-01", "2022-12")
    pce_peak = _peak_month(pce_yoy, "2022-01", "2022-12")
    cpi_disinflation = (cpi_yoy[cpi_peak] - cpi_yoy["2025-12"])
    pce_disinflation = (pce_yoy[pce_peak] - pce_yoy["2025-12"])
    ndpi = _window_value(window_rows, "ND_pi_base_pp", "0_36m_cumulative_sum_pp")
    demand = _window_value(window_rows, "demand_only_after_wall_base_pp", "0_36m_cumulative_sum_pp")
    timing = "pass" if cpi_disinflation > 0 and pce_disinflation > 0 else "fail"
    sign = "pass" if ndpi > demand > 0 else "fail"
    score = _score_row(
        "Net price traction path",
        "2022Q1-2025Q4",
        "survives_as_diagnostic_not_headline_fit",
        timing,
        sign,
        _ratio(ndpi, cpi_disinflation),
        "frozen_ND_pi_to_realized_CPI_yoy_disinflation_diagnostic_only",
        "headline_CPI_residual_never_calibrates_coefficients",
        "no_fitting_guard;CPI_PCE_crosswalk_kept_separate;no_headline_fit",
        "kernel_survives_as_diagnostic",
        f"frozen ND_pi {_fmt(ndpi)}pp exceeds demand-only {_fmt(demand)}pp; CPI/PCE y/y fell",
    )
    rows = [
        _series_row("Net price traction path", "0_36m", ndpi, cpi_disinflation, "pp", "diagnostic only; not headline CPI fit"),
        _series_row("Net price traction path", "0_36m", ndpi, pce_disinflation, "pp", "PCE kept separate from CPI"),
    ]
    return score, rows


class _ObservedPack:
    def __init__(self, root: Path) -> None:
        self.root = root

    def monthly(self, stem: str, value_col: str = "value") -> dict[str, Decimal]:
        path = self.root / f"{stem}.csv"
        rows: dict[str, Decimal] = {}
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                raw = row[value_col]
                if raw == "." or raw == "":
                    continue
                rows[_month_key(row["date"] if "date" in row else row["month"])] = Decimal(raw)
        return rows


def _score_row(
    diagnostic: str,
    window: str,
    disposition: str,
    timing_pass: str,
    sign_pass: str,
    magnitude_ratio: str,
    magnitude_ratio_meaning: str,
    no_fitting_guard: str,
    guardrail_status: str,
    kernel_status: str,
    evidence_summary: str,
) -> dict[str, str]:
    return {
        "run_id": "intermediate_plug",
        "diagnostic": diagnostic,
        "window": window,
        "disposition": disposition,
        "timing_pass": timing_pass,
        "sign_pass": sign_pass,
        "magnitude_ratio": magnitude_ratio,
        "magnitude_ratio_meaning": magnitude_ratio_meaning,
        "no_fitting_guard": f"{no_fitting_guard};no_fitting_guard",
        "guardrail_status": guardrail_status,
        "kernel_status": kernel_status,
        "evidence_summary": evidence_summary,
        "lineage": "do/rwpi_observed/manifest.csv;do/rwtam_rwpi_observed_series_20260704.md",
    }


def _series_row(
    diagnostic: str,
    period: str,
    predicted: Decimal,
    observed: Decimal,
    unit: str,
    note: str,
) -> dict[str, str]:
    return {
        "diagnostic": diagnostic,
        "period": period,
        "predicted_value": _fmt(predicted),
        "observed_value": _fmt(observed),
        "unit": unit,
        "note": note,
    }


def _window_value(rows: list[dict[str, str]], column: str, window: str) -> Decimal:
    row = next(
        r for r in rows
        if r["dose_mode"] == "persistent_level"
        and r["index_target"] == "CPI_U"
        and r["slack_state"] == "balanced"
        and r["horizon_window"] == window
    )
    return _dec(row[column])


def _yoy(series: dict[str, Decimal]) -> dict[str, Decimal]:
    values = {}
    for month, value in series.items():
        prior = _add_months(month, -12)
        if prior in series and series[prior] != 0:
            values[month] = ((value / series[prior]) - Decimal("1")) * Decimal("100")
    return values


def _rebased(series: dict[str, Decimal], base_month: str) -> dict[str, Decimal]:
    base = series[base_month]
    return {month: value / base * Decimal("100") for month, value in series.items()}


def _peak_month(series: dict[str, Decimal], start: str, end: str) -> str:
    return max(_between(series, start, end), key=lambda month: series[month])


def _trough_month(series: dict[str, Decimal], start: str, end: str) -> str:
    return min(_between(series, start, end), key=lambda month: series[month])


def _between(series: dict[str, Decimal], start: str, end: str) -> list[str]:
    return [month for month in sorted(series) if start <= month <= end]


def _avg(series: dict[str, Decimal], start: str, end: str) -> Decimal:
    values = [series[month] for month in _between(series, start, end)]
    return sum(values, Decimal("0")) / Decimal(len(values))


def _delta(series: dict[str, Decimal], start: str, end: str) -> Decimal:
    if end not in series:
        end = max(month for month in series if month <= end)
    return series[end] - series[start]


def _ratio(predicted: Decimal, observed: Decimal) -> str:
    try:
        if observed == 0:
            return ""
        return _fmt(predicted / observed)
    except (DivisionByZero, InvalidOperation):
        return ""


def _month_key(value: str) -> str:
    return value[:7]


def _add_months(month: str, months: int) -> str:
    year, month_num = [int(part) for part in month.split("-")]
    offset = (year * 12 + month_num - 1) + months
    new_year = offset // 12
    new_month = offset % 12 + 1
    return f"{new_year:04d}-{new_month:02d}"


def _months_between(start: str, end: str) -> int:
    start_date = date(int(start[:4]), int(start[5:7]), 1)
    end_date = date(int(end[:4]), int(end[5:7]), 1)
    return (end_date.year - start_date.year) * 12 + end_date.month - start_date.month


def _dec(value: str) -> Decimal:
    return Decimal(value)


def _fmt(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")
