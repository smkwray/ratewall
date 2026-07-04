"""Deposit payer-flow source panel gates for D1 safe-yield admission."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_OUTPUT_DIR = Path("var/preliminary_scenario_results/realized_safe_yield_income")
FFIEC_PANEL_RELATIVE_PATH = Path("ffiec_fdic/deposit_interest_expense_panel.csv")
NCUA_PANEL_RELATIVE_PATH = Path("ncua/share_deposit_interest_panel.csv")
ACQUISITION_FAIL_CLOSED_RELATIVE_PATH = Path(
    "safe_yield/deposit_payer_flow_source_acquisition_fail_closed.csv"
)

FFIEC_INCLUDED_FIELDS = ["RIAD4508", "RIAD0093", "RIADHK03", "RIADHK04"]
FFIEC_EXCLUDED_FIELDS = ["RIAD4172"]
NCUA_INCLUDED_FIELDS = ["380", "381"]
NCUA_CROSS_CHECK_FIELDS = ["340", "350"]

ACCEPTED_CURRENT_ROW_THRESHOLD = Decimal("0.990")
BLOCKED_CURRENT_YTD_SHARE_THRESHOLD = Decimal("0.010")
EXIT_EXPOSURE_SHARE_THRESHOLD = Decimal("0.020")

DEPOSIT_PAYER_FLOW_SOURCE_PANEL_FIELDS = [
    "source_row_id",
    "source_family",
    "object_role",
    "report_date",
    "period_id",
    "institution_id",
    "institution_name",
    "source_unit",
    "ytd_interest_expense_bil",
    "prior_same_year_ytd_interest_expense_bil",
    "quarterly_interest_expense_bil",
    "accepted_current_row",
    "blocked_reason",
    "formula_fields_included",
    "excluded_fields_retained",
    "cross_check_fields_retained",
    "source_shape_status",
    "periodization_rule",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DEPOSIT_PAYER_FLOW_SOURCE_DEFINITION_FIELDS = [
    "field_id",
    "source_family",
    "source_label",
    "included_in_formula",
    "formula_role",
    "definition_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

SAFE_YIELD_SUBLANE_STATUS_FIELDS = [
    "sublane_id",
    "object_role",
    "requested_period_ids",
    "ffiec_fdic_panel_status",
    "ncua_panel_status",
    "source_gate_status",
    "eligible_current_rows",
    "accepted_current_rows",
    "accepted_current_row_share",
    "blocked_current_ytd_share",
    "exit_exposure_share",
    "positive_flow_all_periods",
    "gross_realized_income_bil",
    "centrality",
    "central_n_delta_bil_allowed",
    "central_n_delta_bil",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DEPOSIT_PAYER_FLOW_ACQUISITION_FAIL_CLOSED_FIELDS = [
    "source_family",
    "expected_artifact",
    "fail_closed_artifact",
    "source_status",
    "required_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


@dataclass(frozen=True)
class _ParsedSource:
    family: str
    status: str
    rows: list[dict[str, str]]
    exit_exposure_bil: Decimal


def deposit_payer_flow_source_definition_rows() -> list[dict[str, str]]:
    """Return the field-level D1 source definitions."""

    specs = [
        *[
            (
                field,
                "ffiec_fdic_call_report_deposit_interest_expense",
                "bank domestic deposit-interest expense formula field",
                "true",
                "included_bank_deposit_interest_expense_ytd",
                "accepted_formula_input",
            )
            for field in FFIEC_INCLUDED_FIELDS
        ],
        (
            "RIAD4172",
            "ffiec_fdic_call_report_deposit_interest_expense",
            "bank total interest expense cross-check field",
            "false",
            "retained_excluded_from_safe_yield_formula",
            "excluded_not_domestic_deposit_formula_input",
        ),
        *[
            (
                field,
                "ncua_credit_union_share_deposit_interest_expense",
                "credit-union share/deposit interest expense formula field",
                "true",
                "included_credit_union_share_deposit_interest_expense_ytd",
                "accepted_formula_input",
            )
            for field in NCUA_INCLUDED_FIELDS
        ],
        *[
            (
                field,
                "ncua_credit_union_share_deposit_interest_expense",
                "credit-union cross-check account retained but not substituted",
                "false",
                "cross_check_only_cannot_substitute_for_380_381",
                "retained_cross_check_only",
            )
            for field in NCUA_CROSS_CHECK_FIELDS
        ],
    ]
    return [
        {
            "field_id": field_id,
            "source_family": family,
            "source_label": label,
            "included_in_formula": included,
            "formula_role": role,
            "definition_status": status,
            "allowed_use": "deposit_payer_flow_source_definition",
            "blocked_use": "central_safe_yield_admission_without_panel_gate",
            "claim_boundary": "D1_field_definition_no_selected_value_change",
        }
        for field_id, family, label, included, role, status in specs
    ]


def deposit_payer_flow_source_panel_rows(
    *,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
) -> list[dict[str, str]]:
    """Build source panel rows from raw FFIEC/FDIC and NCUA files."""

    raw = Path(raw_dir)
    ffiec = _parse_source_panel(
        raw / FFIEC_PANEL_RELATIVE_PATH,
        family="ffiec_fdic_call_report_deposit_interest_expense",
        institution_candidates=["rssd_id", "institution_id", "cert", "certificate"],
        name_candidates=["institution_name", "name"],
        included_fields=FFIEC_INCLUDED_FIELDS,
        excluded_fields=FFIEC_EXCLUDED_FIELDS,
        cross_check_fields=[],
    )
    ncua = _parse_source_panel(
        raw / NCUA_PANEL_RELATIVE_PATH,
        family="ncua_credit_union_share_deposit_interest_expense",
        institution_candidates=[
            "charter_number",
            "institution_id",
            "cu_number",
            "credit_union_id",
        ],
        name_candidates=["institution_name", "credit_union_name", "name"],
        included_fields=NCUA_INCLUDED_FIELDS,
        excluded_fields=[],
        cross_check_fields=NCUA_CROSS_CHECK_FIELDS,
    )
    return [*ffiec.rows, *ncua.rows]


def safe_yield_sublane_status_rows(
    panel_rows: Sequence[Mapping[str, str]],
    *,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    requested_period_ids: Sequence[str] | None = None,
) -> list[dict[str, str]]:
    """Return the combined D1 source gate row."""

    raw = Path(raw_dir)
    requested = list(requested_period_ids or _common_period_ids(panel_rows))
    ffiec = _parse_source_panel(
        raw / FFIEC_PANEL_RELATIVE_PATH,
        family="ffiec_fdic_call_report_deposit_interest_expense",
        institution_candidates=["rssd_id", "institution_id", "cert", "certificate"],
        name_candidates=["institution_name", "name"],
        included_fields=FFIEC_INCLUDED_FIELDS,
        excluded_fields=FFIEC_EXCLUDED_FIELDS,
        cross_check_fields=[],
    )
    ncua = _parse_source_panel(
        raw / NCUA_PANEL_RELATIVE_PATH,
        family="ncua_credit_union_share_deposit_interest_expense",
        institution_candidates=[
            "charter_number",
            "institution_id",
            "cu_number",
            "credit_union_id",
        ],
        name_candidates=["institution_name", "credit_union_name", "name"],
        included_fields=NCUA_INCLUDED_FIELDS,
        excluded_fields=[],
        cross_check_fields=NCUA_CROSS_CHECK_FIELDS,
    )
    all_rows = [*ffiec.rows, *ncua.rows] if not panel_rows else list(panel_rows)
    eligible = [
        row
        for row in all_rows
        if row["report_date"] and (not requested or row["period_id"] in requested)
    ]
    accepted = [row for row in eligible if row["accepted_current_row"] == "true"]
    accepted_share = (
        Decimal(len(accepted)) / Decimal(len(eligible)) if eligible else Decimal("0")
    )
    total_current_ytd = sum(
        _decimal_or_zero(row["ytd_interest_expense_bil"]) for row in eligible
    )
    blocked_current_ytd = sum(
        abs(_decimal_or_zero(row["ytd_interest_expense_bil"]))
        for row in eligible
        if row["accepted_current_row"] != "true"
    )
    exit_exposure = ffiec.exit_exposure_bil + ncua.exit_exposure_bil
    exposure_denominator = total_current_ytd + exit_exposure
    blocked_share = (
        blocked_current_ytd / total_current_ytd
        if total_current_ytd > 0
        else Decimal("1")
    )
    exit_share = (
        exit_exposure / exposure_denominator
        if exposure_denominator > 0
        else Decimal("1")
    )
    accepted_by_period: dict[str, Decimal] = {
        period_id: Decimal("0") for period_id in requested
    }
    for row in accepted:
        accepted_by_period.setdefault(row["period_id"], Decimal("0"))
        accepted_by_period[row["period_id"]] += _decimal_or_zero(
            row["quarterly_interest_expense_bil"]
        )
    positive_all_periods = bool(requested) and all(
        value > 0 for value in accepted_by_period.values()
    )
    coverage_complete = _requested_periods_complete(accepted, requested)
    source_gate_pass = (
        ffiec.status == "source_panel_present_shape_passed"
        and ncua.status == "source_panel_present_shape_passed"
        and coverage_complete
        and accepted_share >= ACCEPTED_CURRENT_ROW_THRESHOLD
        and blocked_share <= BLOCKED_CURRENT_YTD_SHARE_THRESHOLD
        and exit_share <= EXIT_EXPOSURE_SHARE_THRESHOLD
        and positive_all_periods
    )
    blocked_reasons = []
    if ffiec.status != "source_panel_present_shape_passed":
        blocked_reasons.append("ffiec_fdic_panel_not_success")
    if ncua.status != "source_panel_present_shape_passed":
        blocked_reasons.append("ncua_panel_not_success")
    if not coverage_complete:
        blocked_reasons.append("requested_common_quarter_coverage_incomplete")
    if accepted_share < ACCEPTED_CURRENT_ROW_THRESHOLD:
        blocked_reasons.append("accepted_current_rows_below_0_990")
    if blocked_share > BLOCKED_CURRENT_YTD_SHARE_THRESHOLD:
        blocked_reasons.append("blocked_current_ytd_share_above_0_010")
    if exit_share > EXIT_EXPOSURE_SHARE_THRESHOLD:
        blocked_reasons.append("exit_exposure_share_above_0_020")
    if not positive_all_periods:
        blocked_reasons.append("nonpositive_accepted_aggregate_flow")
    return [
        {
            "sublane_id": "D1_deposit_payer_flow_source_gate",
            "object_role": "blocked_source_or_method",
            "requested_period_ids": "|".join(requested),
            "ffiec_fdic_panel_status": ffiec.status,
            "ncua_panel_status": ncua.status,
            "source_gate_status": (
                "pass_source_panels_shape_coverage_and_flow"
                if source_gate_pass
                else "blocked_" + ";".join(blocked_reasons)
            ),
            "eligible_current_rows": str(len(eligible)),
            "accepted_current_rows": str(len(accepted)),
            "accepted_current_row_share": _fmt(accepted_share),
            "blocked_current_ytd_share": _fmt(blocked_share),
            "exit_exposure_share": _fmt(exit_share),
            "positive_flow_all_periods": str(positive_all_periods).lower(),
            "gross_realized_income_bil": _fmt(
                sum(accepted_by_period.values(), Decimal("0"))
            ),
            "centrality": "source_gate_only_not_selected_addition",
            "central_n_delta_bil_allowed": "false",
            "central_n_delta_bil": "0",
            "allowed_use": "safe_yield_payer_flow_source_gate_input",
            "blocked_use": "central_N_delta_without_recipient_overlap_owner_gates",
            "claim_boundary": "D1_source_gate_no_selected_value_change",
        }
    ]


def write_fail_closed_acquisition_artifacts(
    *,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
) -> dict[str, Path]:
    """Write raw fail-closed placeholders when required source panels are missing."""

    raw = Path(raw_dir)
    outputs = {
        "ffiec_fail_closed_csv": raw
        / "ffiec_fdic/deposit_interest_expense_panel.FAIL_CLOSED.csv",
        "ncua_fail_closed_csv": raw / "ncua/share_deposit_interest_panel.FAIL_CLOSED.csv",
        "acquisition_fail_closed_csv": raw / ACQUISITION_FAIL_CLOSED_RELATIVE_PATH,
    }
    rows = []
    for family, expected, fail_closed, action in [
        (
            "ffiec_fdic_call_report_deposit_interest_expense",
            raw / FFIEC_PANEL_RELATIVE_PATH,
            outputs["ffiec_fail_closed_csv"],
            "acquire_or_build_domestic_deposit_interest_expense_panel",
        ),
        (
            "ncua_credit_union_share_deposit_interest_expense",
            raw / NCUA_PANEL_RELATIVE_PATH,
            outputs["ncua_fail_closed_csv"],
            "acquire_or_build_credit_union_share_interest_panel",
        ),
    ]:
        if expected.exists():
            fail_closed.unlink(missing_ok=True)
        else:
            write_rows(
                fail_closed,
                [
                    {
                        "source_family": family,
                        "expected_artifact": str(expected),
                        "fail_closed_artifact": str(fail_closed),
                        "source_status": "missing_required_source_panel",
                        "required_action": action,
                        "allowed_use": "source_acquisition_status_only",
                        "blocked_use": "deposit_payer_flow_substitution",
                        "claim_boundary": "D1_missing_source_fail_closed",
                    }
                ],
                DEPOSIT_PAYER_FLOW_ACQUISITION_FAIL_CLOSED_FIELDS,
            )
        rows.append(
            {
                "source_family": family,
                "expected_artifact": str(expected),
                "fail_closed_artifact": str(fail_closed),
                "source_status": (
                    "source_panel_present"
                    if expected.exists()
                    else "missing_required_source_panel"
                ),
                "required_action": action,
                "allowed_use": "source_acquisition_status_only",
                "blocked_use": "deposit_payer_flow_substitution",
                "claim_boundary": "D1_missing_source_fail_closed",
            }
        )
    write_rows(
        outputs["acquisition_fail_closed_csv"],
        rows,
        DEPOSIT_PAYER_FLOW_ACQUISITION_FAIL_CLOSED_FIELDS,
    )
    return outputs


def write_deposit_payer_flow_source_outputs(
    output_dir: str | Path,
    *,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    requested_period_ids: Sequence[str] | None = None,
) -> dict[str, Path]:
    """Write D1 payer-flow source panel artifacts."""

    write_fail_closed_acquisition_artifacts(raw_dir=raw_dir)
    panel_rows = deposit_payer_flow_source_panel_rows(raw_dir=raw_dir)
    definition_rows = deposit_payer_flow_source_definition_rows()
    status_rows = safe_yield_sublane_status_rows(
        panel_rows,
        raw_dir=raw_dir,
        requested_period_ids=requested_period_ids,
    )
    out = Path(output_dir)
    outputs = {
        "source_panel_csv": out / "ratewall_deposit_payer_flow_source_panel.csv",
        "source_definitions_csv": out
        / "ratewall_deposit_payer_flow_source_definitions.csv",
        "sublane_status_csv": out / "ratewall_safe_yield_sublane_status.csv",
    }
    write_rows(
        outputs["source_panel_csv"],
        panel_rows,
        DEPOSIT_PAYER_FLOW_SOURCE_PANEL_FIELDS,
    )
    write_rows(
        outputs["source_definitions_csv"],
        definition_rows,
        DEPOSIT_PAYER_FLOW_SOURCE_DEFINITION_FIELDS,
    )
    write_rows(
        outputs["sublane_status_csv"],
        status_rows,
        SAFE_YIELD_SUBLANE_STATUS_FIELDS,
    )
    return outputs


def _parse_source_panel(
    path: Path,
    *,
    family: str,
    institution_candidates: Sequence[str],
    name_candidates: Sequence[str],
    included_fields: Sequence[str],
    excluded_fields: Sequence[str],
    cross_check_fields: Sequence[str],
) -> _ParsedSource:
    if not path.exists():
        return _ParsedSource(
            family=family,
            status="missing_required_source_panel",
            rows=[_fail_closed_panel_row(family, "missing_required_source_panel")],
            exit_exposure_bil=Decimal("0"),
        )
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        date_col = _first_present(fieldnames, ["report_date", "date", "quarter_end_date"])
        inst_col = _first_present(fieldnames, institution_candidates)
        name_col = _first_present(fieldnames, name_candidates)
        included_cols = {
            field: _source_field_name(fieldnames, field) for field in included_fields
        }
        missing = [
            field
            for field, column_name in included_cols.items()
            if column_name is None
        ]
        if date_col is None:
            missing.append("report_date")
        if inst_col is None:
            missing.append("institution_id")
        raw_rows = list(reader)
    if missing:
        return _ParsedSource(
            family=family,
            status="source_panel_shape_failed_missing_" + "|".join(sorted(missing)),
            rows=[
                _fail_closed_panel_row(
                    family,
                    "source_panel_shape_failed_missing_" + "|".join(sorted(missing)),
                )
            ],
            exit_exposure_bil=Decimal("0"),
        )
    parsed: list[dict[str, str]] = []
    ytd_by_key: dict[tuple[str, int, int], Decimal] = {}
    current_by_period: dict[tuple[int, int], set[str]] = {}
    ytd_by_period_inst: dict[tuple[int, int, str], Decimal] = {}
    for raw_row in raw_rows:
        report_date = _parse_date(raw_row.get(date_col or ""))
        inst = (raw_row.get(inst_col or "") or "").strip()
        if report_date is None or not inst:
            continue
        ytd = _sum_fields(raw_row, included_cols.values())
        if ytd is None:
            continue
        ytd_bil = ytd / Decimal("1000000")
        key = (inst, report_date.year, _quarter(report_date))
        ytd_by_key[key] = ytd_bil
        current_by_period.setdefault((report_date.year, _quarter(report_date)), set()).add(
            inst
        )
        ytd_by_period_inst[(report_date.year, _quarter(report_date), inst)] = ytd_bil
    for raw_row in raw_rows:
        report_date = _parse_date(raw_row.get(date_col or ""))
        inst = (raw_row.get(inst_col or "") or "").strip()
        name = (raw_row.get(name_col or "") or "").strip() if name_col else ""
        period_id = _period_id(report_date) if report_date else ""
        ytd = _sum_fields(raw_row, included_cols.values())
        if report_date is None or not inst or ytd is None:
            parsed.append(_fail_closed_panel_row(family, "invalid_report_date_or_ytd"))
            continue
        quarter = _quarter(report_date)
        ytd_bil = ytd / Decimal("1000000")
        prior = Decimal("0") if quarter == 1 else ytd_by_key.get(
            (inst, report_date.year, quarter - 1)
        )
        if prior is None:
            qflow = Decimal("0")
            accepted = False
            reason = "missing_prior_same_institution_same_year_ytd"
        else:
            qflow = ytd_bil - prior
            accepted = qflow >= 0
            reason = "accepted" if accepted else "negative_same_year_ytd_difference"
        parsed.append(
            {
            "source_row_id": f"{family}::{period_id}::{inst}",
            "source_family": family,
            "object_role": "blocked_source_or_method",
            "report_date": report_date.isoformat(),
                "period_id": period_id,
                "institution_id": inst,
                "institution_name": name,
                "source_unit": "thousands_usd_converted_to_billions_usd",
                "ytd_interest_expense_bil": _fmt(ytd_bil),
                "prior_same_year_ytd_interest_expense_bil": _fmt(prior),
                "quarterly_interest_expense_bil": _fmt(qflow if accepted else Decimal("0")),
                "accepted_current_row": str(accepted).lower(),
                "blocked_reason": reason,
                "formula_fields_included": "|".join(included_fields),
                "excluded_fields_retained": "|".join(excluded_fields),
                "cross_check_fields_retained": "|".join(cross_check_fields),
                "source_shape_status": "source_panel_present_shape_passed",
                "periodization_rule": (
                    "Q1_current_YTD_Q2_Q3_Q4_current_minus_prior_same_institution_same_year_YTD"
                ),
                "allowed_use": "deposit_payer_flow_source_gate_input",
                "blocked_use": "central_N_delta_without_combined_gate",
                "claim_boundary": "D1_source_panel_periodized_no_selected_value_change",
            }
        )
    exit_exposure = _exit_exposure_bil(current_by_period, ytd_by_period_inst)
    return _ParsedSource(
        family=family,
        status="source_panel_present_shape_passed",
        rows=parsed,
        exit_exposure_bil=exit_exposure,
    )


def _fail_closed_panel_row(family: str, reason: str) -> dict[str, str]:
    return {
        "source_row_id": f"{family}::fail_closed",
        "source_family": family,
        "object_role": "blocked_source_or_method",
        "report_date": "",
        "period_id": "",
        "institution_id": "",
        "institution_name": "",
        "source_unit": "",
        "ytd_interest_expense_bil": "0",
        "prior_same_year_ytd_interest_expense_bil": "0",
        "quarterly_interest_expense_bil": "0",
        "accepted_current_row": "false",
        "blocked_reason": reason,
        "formula_fields_included": "",
        "excluded_fields_retained": "",
        "cross_check_fields_retained": "",
        "source_shape_status": reason,
        "periodization_rule": (
            "Q1_current_YTD_Q2_Q3_Q4_current_minus_prior_same_institution_same_year_YTD"
        ),
        "allowed_use": "source_acquisition_status_only",
        "blocked_use": "central_safe_yield_admission",
        "claim_boundary": "D1_source_panel_fail_closed_no_selected_value_change",
    }


def _requested_periods_complete(
    rows: Sequence[Mapping[str, str]], requested_period_ids: Sequence[str]
) -> bool:
    if not requested_period_ids:
        return False
    by_family: dict[str, set[str]] = {}
    for row in rows:
        by_family.setdefault(row["source_family"], set()).add(row["period_id"])
    required = set(requested_period_ids)
    return all(required <= periods for periods in by_family.values()) and len(by_family) >= 2


def _common_period_ids(rows: Sequence[Mapping[str, str]]) -> list[str]:
    periods_by_family: dict[str, set[str]] = {}
    for row in rows:
        if row["period_id"] and row["accepted_current_row"] == "true":
            periods_by_family.setdefault(row["source_family"], set()).add(row["period_id"])
    if len(periods_by_family) < 2:
        return []
    common = set.intersection(*periods_by_family.values())
    return sorted(common)


def _exit_exposure_bil(
    current_by_period: Mapping[tuple[int, int], set[str]],
    ytd_by_period_inst: Mapping[tuple[int, int, str], Decimal],
) -> Decimal:
    exposure = Decimal("0")
    for year, quarter in sorted(current_by_period):
        if quarter == 1:
            continue
        prior = current_by_period.get((year, quarter - 1), set())
        current = current_by_period[(year, quarter)]
        for inst in prior - current:
            exposure += ytd_by_period_inst.get((year, quarter - 1, inst), Decimal("0"))
    return exposure


def _sum_fields(
    row: Mapping[str, str],
    columns: Sequence[str | None],
) -> Decimal | None:
    total = Decimal("0")
    for column_name in columns:
        if column_name is None:
            return None
        value = _parse_decimal(row.get(column_name))
        if value is None:
            return None
        total += value
    return total


def _source_field_name(fieldnames: Sequence[str], field_id: str) -> str | None:
    candidates = [
        field_id,
        f"RIAD{field_id}" if field_id.isdigit() else field_id,
        f"account_{field_id}",
        f"ACCT_{field_id}",
        f"ncua_{field_id}",
        f"NCUA_{field_id}",
    ]
    return _first_present(fieldnames, candidates)


def _first_present(options: Sequence[str], candidates: Sequence[str]) -> str | None:
    option_set = {option.lower(): option for option in options}
    for candidate in candidates:
        found = option_set.get(candidate.lower())
        if found is not None:
            return found
    return None


def _parse_date(raw: str | None) -> date | None:
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return None


def _parse_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    text = raw.strip().replace(",", "")
    if text in {"", "."}:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _quarter(value: date) -> int:
    return ((value.month - 1) // 3) + 1


def _period_id(value: date | None) -> str:
    if value is None:
        return ""
    return f"{value.year}Q{_quarter(value)}"


def _decimal_or_zero(raw: str) -> Decimal:
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal("0")


def _fmt(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")
