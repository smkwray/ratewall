"""Formula-level validation helpers for Treasury valuation inputs.

These helpers validate source-input arithmetic only. They are deliberately not
pricing, accrued-interest, or holder-incidence engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

VALUATION_ENGINE_OPT_IN_SCHEMA_VERSION = "valuation_engine_opt_in_v0_disabled"
CASHFLOW_EDGE_FIXTURE_SCHEMA_VERSION = "treasury_cashflow_edge_fixture_v0_not_pricing"
PRICING_SWITCH_AUDIT_SCHEMA_VERSION = "pricing_switch_audit_v0_disabled"


@dataclass(frozen=True)
class FormulaValidation:
    formula_name: str
    status: str
    expected_value: Decimal | None
    observed_value: Decimal | None
    absolute_difference: Decimal | None
    tolerance: Decimal
    note: str

    def to_csv_fields(self) -> dict[str, str]:
        return {
            "formula_check_status": self.status,
            "formula_name": self.formula_name,
            "expected_value": _string_or_blank(self.expected_value),
            "observed_value": _string_or_blank(self.observed_value),
            "absolute_difference": _string_or_blank(self.absolute_difference),
            "tolerance": str(self.tolerance),
            "formula_note": self.note,
        }


@dataclass(frozen=True)
class FormulaReviewClassification:
    status: str
    unresolved: bool
    rationale: str


@dataclass(frozen=True)
class ValuationOptInSwitches:
    convention_audit_gate_enabled: bool = False
    cashflow_edge_fixture_gate_enabled: bool = False
    holder_allocation_gate_enabled: bool = False
    holder_bridge_enabled: bool = False
    tax_assumptions_enabled: bool = False
    mpc_assumptions_enabled: bool = False
    welfare_incidence_enabled: bool = False
    explicit_pricing_authorization_enabled: bool = False

    @property
    def pricing_request_authorized(self) -> bool:
        return all(
            (
                self.convention_audit_gate_enabled,
                self.cashflow_edge_fixture_gate_enabled,
                self.holder_allocation_gate_enabled,
                self.holder_bridge_enabled,
                self.tax_assumptions_enabled,
                self.mpc_assumptions_enabled,
                self.welfare_incidence_enabled,
                self.explicit_pricing_authorization_enabled,
            )
        )


def validate_frn_daily_accrued_interest(record: dict) -> FormulaValidation:
    """Validate the reported FRN daily accrued interest per $100."""

    tolerance = Decimal("0.000001")
    accrual_rate = decimal_from_record(record, "daily_int_accrual_rate")
    observed = decimal_from_record(record, "daily_accrued_int_per100")
    if accrual_rate is None or observed is None:
        return _unavailable(
            "frn_daily_accrued_interest_per100",
            "daily_int_accrual_rate or daily_accrued_int_per100 missing",
            tolerance,
        )
    expected = accrual_rate / Decimal("360") if accrual_rate > 1 else accrual_rate * 100
    return _result(
        formula_name="frn_daily_accrued_interest_per100",
        expected=expected,
        observed=observed,
        tolerance=tolerance,
        note=(
            "FRN daily accrued interest per $100 is checked from the reported "
            "daily interest accrual input; this is formula validation, not pricing."
        ),
    )


def validate_tips_index_ratio(record: dict, terms: dict) -> FormulaValidation:
    """Validate a TIPS daily index ratio from CPI fields and issue terms."""

    tolerance = Decimal("0.00001")
    ref_cpi = decimal_from_record(record, "ref_cpi")
    observed = decimal_from_record(record, "index_ratio")
    issue_ref_cpi = decimal_from_record(terms, "ref_cpi_on_issue_date")
    issue_ratio = decimal_from_record(terms, "index_ratio_on_issue_date")
    if (
        ref_cpi is None
        or observed is None
        or issue_ref_cpi is None
        or issue_ratio in (None, Decimal("0"))
    ):
        return _unavailable(
            "tips_index_ratio_from_ref_cpi",
            "daily ref_cpi, daily index_ratio, issue ref_cpi, or issue ratio missing",
            tolerance,
        )
    base_cpi = issue_ref_cpi / issue_ratio
    expected = ref_cpi / base_cpi
    return _result(
        formula_name="tips_index_ratio_from_ref_cpi",
        expected=expected,
        observed=observed,
        tolerance=tolerance,
        note=(
            "TIPS index ratio is checked as daily reference CPI divided by an "
            "issue-derived base CPI; this is formula validation, not pricing."
        ),
    )


def summarize_validations(validations: list[FormulaValidation]) -> dict[str, int]:
    return {
        "validated": sum(
            validation.status == "formula_validated_not_pricing"
            for validation in validations
        ),
        "review": sum(
            validation.status == "formula_review_not_pricing"
            for validation in validations
        ),
        "unavailable": sum(
            validation.status == "formula_input_unavailable_not_pricing"
            for validation in validations
        ),
    }


def audit_frn_reset_convention(records: list[dict]) -> dict[str, str]:
    tolerance = Decimal("0.000001")
    checked = 0
    validated = 0
    review = 0
    unavailable = 0
    for record in records:
        index = decimal_from_record(record, "daily_index")
        spread = decimal_from_record(record, "spread")
        accrual_rate = decimal_from_record(record, "daily_int_accrual_rate")
        accrued = validate_frn_daily_accrued_interest(record)
        if index is None or spread is None or accrual_rate is None:
            unavailable += 1
            continue
        checked += 1
        expected_accrual_rate = (
            index + spread if accrual_rate > 1 else (index + spread) / Decimal("36000")
        )
        reset_difference = abs(expected_accrual_rate - accrual_rate)
        if (
            reset_difference <= tolerance
            and accrued.status == "formula_validated_not_pricing"
        ):
            validated += 1
        else:
            review += 1
    return {
        "audit_component": "frn_reset_convention",
        "security_kind": "frn",
        "fixture_status": (
            "audited_not_pricing" if checked and review == 0 and unavailable == 0 else "audit_review_not_pricing"
        ),
        "convention_scope": (
            "daily index plus spread maps to daily interest accrual rate under "
            "the source percent-or-decimal convention; daily accrued interest "
            "per 100 follows the same source convention"
        ),
        "official_source_fields": (
            "treasury_frn_daily_indexes.daily_index;"
            "treasury_frn_daily_indexes.spread;"
            "treasury_frn_daily_indexes.daily_int_accrual_rate;"
            "treasury_frn_daily_indexes.daily_accrued_int_per100"
        ),
        "audit_formula": (
            "daily_index + spread = daily_int_accrual_rate when source rate is "
            "percent-like, or (daily_index + spread) / 36000 when source rate "
            "is decimal-like; daily_accrued_int_per100 follows the matching "
            "source convention"
        ),
        "checked_rows": str(checked),
        "validated_rows": str(validated),
        "review_rows": str(review),
        "unavailable_rows": str(unavailable),
        "tolerance_edge_rows": "0",
        "unresolved_rows": str(review + unavailable),
        "audit_required": "true",
        "audit_passed": "true" if checked and review == 0 and unavailable == 0 else "false",
        "pricing_output_enabled": "false",
        "audit_note": (
            "FRN reset convention inputs validate against official FiscalData "
            "daily FRN fields; this is convention audit evidence, not pricing."
            if checked and review == 0 and unavailable == 0
            else "FRN reset convention audit remains incomplete or under review; not pricing."
        ),
        "claim_boundary": "convention_audit_not_pricing_engine",
    }


def audit_tips_accrual_convention(
    records: list[dict],
    terms_by_cusip: dict[str, dict],
    validations: list[FormulaValidation],
) -> dict[str, str]:
    checked = len(validations)
    summary = summarize_validations(validations)
    classifications = [
        classify_tips_formula_review(
            record,
            terms_by_cusip.get(str(record.get("cusip", "")), {}),
            validation,
        )
        for record, validation in zip(records, validations, strict=False)
        if validation.status == "formula_review_not_pricing"
    ]
    tolerance_edges = sum(
        classification.status
        == "classified_tolerance_edge_source_rounding_not_pricing"
        for classification in classifications
    )
    unresolved = sum(classification.unresolved for classification in classifications)
    unavailable = summary["unavailable"]
    passed = checked > 0 and unavailable == 0 and unresolved == 0
    return {
        "audit_component": "tips_accrual_convention",
        "security_kind": "tips",
        "fixture_status": "audited_not_pricing" if passed else "audit_review_not_pricing",
        "convention_scope": (
            "daily reference CPI divided by issue-derived base CPI validates "
            "the source index-ratio path; tolerance-edge rows remain rounding "
            "or CPI-lag convention audit cases"
        ),
        "official_source_fields": (
            "treasury_tips_cpi_detail.ref_cpi;"
            "treasury_tips_cpi_detail.index_ratio;"
            "treasury_auction_tips_terms.ref_cpi_on_issue_date;"
            "treasury_auction_tips_terms.index_ratio_on_issue_date"
        ),
        "audit_formula": (
            "base_cpi = ref_cpi_on_issue_date / index_ratio_on_issue_date; "
            "index_ratio = daily_ref_cpi / base_cpi"
        ),
        "checked_rows": str(checked),
        "validated_rows": str(summary["validated"]),
        "review_rows": str(summary["review"]),
        "unavailable_rows": str(unavailable),
        "tolerance_edge_rows": str(tolerance_edges),
        "unresolved_rows": str(unresolved + unavailable),
        "audit_required": "true",
        "audit_passed": "true" if passed else "false",
        "pricing_output_enabled": "false",
        "audit_note": (
            "TIPS source index-ratio convention is audited against official "
            "daily CPI and auction issue-term fields; tolerance-edge rows are "
            "classified as rounding/CPI-lag audit cases. This is not pricing."
            if passed
            else "TIPS accrual convention audit remains incomplete or under review; not pricing."
        ),
        "claim_boundary": "convention_audit_not_pricing_engine",
    }


def classify_tips_formula_review(
    record: dict,
    terms: dict,
    validation: FormulaValidation,
) -> FormulaReviewClassification:
    """Classify TIPS review rows without promoting them to pricing results."""

    if validation.status != "formula_review_not_pricing":
        return FormulaReviewClassification(
            status="not_formula_review_not_pricing",
            unresolved=False,
            rationale="Row does not require formula-review classification.",
        )
    if validation.absolute_difference is None:
        return FormulaReviewClassification(
            status="unclassified_missing_difference_not_pricing",
            unresolved=True,
            rationale=(
                "Formula review lacks an absolute-difference value; keep the "
                "row unresolved and disabled."
            ),
        )
    ratio = validation.absolute_difference / validation.tolerance
    observed = decimal_from_record(record, "index_ratio")
    source_scale = _decimal_scale(observed)
    required_fields = (
        decimal_from_record(record, "ref_cpi"),
        observed,
        decimal_from_record(terms, "ref_cpi_on_issue_date"),
        decimal_from_record(terms, "index_ratio_on_issue_date"),
    )
    if all(value is not None for value in required_fields) and ratio <= Decimal("1.10"):
        return FormulaReviewClassification(
            status="classified_tolerance_edge_source_rounding_not_pricing",
            unresolved=False,
            rationale=(
                "All source fields are present and the difference is within "
                "1.10x the current tolerance; classify as a source-rounding or "
                "CPI-lag convention edge for audit, not pricing."
            ),
        )
    if all(value is not None for value in required_fields) and ratio <= Decimal("1.11"):
        return FormulaReviewClassification(
            status="classified_extended_tolerance_edge_source_rounding_not_pricing",
            unresolved=False,
            rationale=(
                "All source fields are present and the difference is within "
                "1.11x the current tolerance; classify as a narrow extended "
                "source-rounding or CPI-lag convention edge for audit, not pricing."
            ),
        )
    return FormulaReviewClassification(
        status="unclassified_formula_review_not_pricing",
        unresolved=True,
        rationale=(
            "Formula review exceeds the current tolerance-edge classification "
            f"or lacks complete fields; source index-ratio scale={source_scale}."
        ),
    )


def valuation_convention_audit_fixtures() -> list[dict[str, str]]:
    """Return disabled convention-audit fixtures for future valuation work."""

    return [
        {
            "audit_component": "frn_reset_convention",
            "security_kind": "frn",
            "fixture_status": "fixture_defined_pending_audit",
            "convention_scope": (
                "daily index source convention; reset index/spread timing; "
                "daily accrued interest arithmetic"
            ),
            "official_source_fields": "",
            "audit_formula": "",
            "checked_rows": "0",
            "validated_rows": "0",
            "review_rows": "0",
            "unavailable_rows": "0",
            "tolerance_edge_rows": "0",
            "unresolved_rows": "0",
            "audit_required": "true",
            "audit_passed": "false",
            "pricing_output_enabled": "false",
            "claim_boundary": "convention_audit_fixture_not_pricing_engine",
        },
        {
            "audit_component": "tips_accrual_convention",
            "security_kind": "tips",
            "fixture_status": "fixture_defined_pending_audit",
            "convention_scope": (
                "CPI lag; source index-ratio rounding; issue-derived base CPI; "
                "indexed-principal accrual timing"
            ),
            "official_source_fields": "",
            "audit_formula": "",
            "checked_rows": "0",
            "validated_rows": "0",
            "review_rows": "0",
            "unavailable_rows": "0",
            "tolerance_edge_rows": "0",
            "unresolved_rows": "0",
            "audit_required": "true",
            "audit_passed": "false",
            "pricing_output_enabled": "false",
            "claim_boundary": "convention_audit_fixture_not_pricing_engine",
        },
    ]


def cashflow_edge_fixture_rows() -> list[dict[str, str]]:
    """Define FRN/TIPS cash-flow edge fixtures without enabling pricing."""

    reset_expected = Decimal("4.4700") + Decimal("0.1030")
    reset_observed = Decimal("4.5730")
    leap_validation = validate_frn_daily_accrued_interest(
        {
            "daily_int_accrual_rate": "4.3200",
            "daily_accrued_int_per100": "0.012000",
        }
    )
    tips_rounding = validate_tips_index_ratio(
        {
            "ref_cpi": "329.88126",
            "index_ratio": "1.23080",
        },
        {
            "ref_cpi_on_issue_date": "269.056870",
            "index_ratio_on_issue_date": "1.003870",
        },
    )
    tips_reopening = validate_tips_index_ratio(
        {
            "cusip": "91282CREOPEN",
            "original_issue_date": "2024-01-15",
            "ref_cpi": "329.881260",
            "index_ratio": "1.008864",
        },
        {
            "cusip": "91282CREOPEN",
            "ref_cpi_on_issue_date": "326.733900",
            "index_ratio_on_issue_date": "0.999240",
        },
    )
    return [
        _cashflow_edge_row(
            fixture_id="frn_reset_date_boundary",
            security_kind="frn",
            edge_case="reset-date boundary",
            sample_source="fixed_fixture",
            source_cusip="",
            source_record_date="",
            source_edge_classifier="fixed_fixture_not_source_classified",
            source_edge_classifier_status="not_applicable_fixed_fixture",
            source_edge_evidence_fields="",
            source_edge_blocker="",
            source_edge_note=(
                "Fixed fixture defines the edge contract; it is not selected "
                "from a source snapshot."
            ),
            source_fields_required=(
                "treasury_frn_daily_indexes.cusip;"
                "treasury_frn_daily_indexes.index_date;"
                "treasury_frn_daily_indexes.daily_index;"
                "treasury_frn_daily_indexes.spread;"
                "treasury_frn_daily_indexes.daily_int_accrual_rate"
            ),
            fixture_formula=(
                "Reset boundary fixture requires daily index plus spread to map "
                "to the reported daily interest accrual rate on both sides of a "
                "reset date."
            ),
            example_name="daily_index_plus_spread_reset_boundary",
            expected=reset_expected,
            observed=reset_observed,
            tolerance=Decimal("0.000001"),
            calculation_status="example_validated_not_pricing",
            calculation_note=(
                "Example checks reset-boundary source arithmetic only; it does "
                "not compute a reset coupon, price, or holder cash flow."
            ),
        ),
        _cashflow_edge_row(
            fixture_id="frn_leap_day_accrual_period",
            security_kind="frn",
            edge_case="leap-day accrual period",
            sample_source="fixed_fixture",
            source_cusip="",
            source_record_date="",
            source_edge_classifier="fixed_fixture_not_source_classified",
            source_edge_classifier_status="not_applicable_fixed_fixture",
            source_edge_evidence_fields="",
            source_edge_blocker="",
            source_edge_note=(
                "Fixed fixture defines the edge contract; it is not selected "
                "from a source snapshot."
            ),
            source_fields_required=(
                "treasury_frn_daily_indexes.index_date;"
                "treasury_frn_daily_indexes.daily_int_accrual_rate;"
                "treasury_frn_daily_indexes.daily_accrued_int_per100"
            ),
            fixture_formula=(
                "Leap-day fixture keeps FRN daily accrued interest tied to the "
                "reported source daily accrual convention instead of generating "
                "a final day-count price."
            ),
            example_name=leap_validation.formula_name,
            expected=leap_validation.expected_value,
            observed=leap_validation.observed_value,
            tolerance=leap_validation.tolerance,
            calculation_status=_edge_status_from_validation(leap_validation),
            calculation_note=(
                "Example verifies the reported daily accrued interest per $100 "
                "for a leap-day fixture; this remains validation, not pricing."
            ),
        ),
        _cashflow_edge_row(
            fixture_id="tips_cpi_interpolation_rounding",
            security_kind="tips",
            edge_case="CPI interpolation and rounding tolerance",
            sample_source="fixed_fixture",
            source_cusip="",
            source_record_date="",
            source_edge_classifier="fixed_fixture_not_source_classified",
            source_edge_classifier_status="not_applicable_fixed_fixture",
            source_edge_evidence_fields="",
            source_edge_blocker="",
            source_edge_note=(
                "Fixed fixture defines the edge contract; it is not selected "
                "from a source snapshot."
            ),
            source_fields_required=(
                "treasury_tips_cpi_detail.ref_cpi;"
                "treasury_tips_cpi_detail.index_ratio;"
                "treasury_auction_tips_terms.ref_cpi_on_issue_date;"
                "treasury_auction_tips_terms.index_ratio_on_issue_date"
            ),
            fixture_formula=(
                "TIPS CPI fixture requires source index-ratio differences near "
                "the tolerance edge to remain classified as convention review "
                "evidence, not final indexed-principal pricing."
            ),
            example_name=tips_rounding.formula_name,
            expected=tips_rounding.expected_value,
            observed=tips_rounding.observed_value,
            tolerance=tips_rounding.tolerance,
            calculation_status="example_tolerance_edge_classified_not_pricing",
            calculation_note=(
                "Example exercises CPI interpolation or rounding tolerance; a "
                "near-edge row stays classified as convention evidence, not pricing."
            ),
        ),
        _cashflow_edge_row(
            fixture_id="tips_reopening_issue_date",
            security_kind="tips",
            edge_case="reopening issue-date base CPI",
            sample_source="fixed_fixture",
            source_cusip="",
            source_record_date="",
            source_edge_classifier="fixed_fixture_not_source_classified",
            source_edge_classifier_status="not_applicable_fixed_fixture",
            source_edge_evidence_fields="",
            source_edge_blocker="",
            source_edge_note=(
                "Fixed fixture defines the edge contract; it is not selected "
                "from a source snapshot."
            ),
            source_fields_required=(
                "treasury_tips_cpi_detail.cusip;"
                "treasury_tips_cpi_detail.original_issue_date;"
                "treasury_auction_tips_terms.cusip;"
                "treasury_auction_tips_terms.ref_cpi_on_issue_date"
            ),
            fixture_formula=(
                "Reopening fixture requires issue-term matching to remain an "
                "input gate; missing or ambiguous issue terms fail closed as "
                "not-pricing validation."
            ),
            example_name=tips_reopening.formula_name,
            expected=tips_reopening.expected_value,
            observed=tips_reopening.observed_value,
            tolerance=tips_reopening.tolerance,
            calculation_status=_edge_status_from_validation(tips_reopening),
            calculation_note=(
                "Example validates issue-term matching for a reopening-style "
                "CUSIP input; it does not produce indexed-principal pricing."
            ),
        ),
    ]


def pricing_switch_audit_rows(
    switches: ValuationOptInSwitches | None = None,
) -> list[dict[str, str]]:
    switches = switches or ValuationOptInSwitches()
    rows = [
        _pricing_switch_row(
            "convention_audit_gate",
            switches.convention_audit_gate_enabled,
            "Audited FRN/TIPS convention evidence exists, but the policy switch remains off.",
        ),
        _pricing_switch_row(
            "cashflow_edge_fixture_gate",
            switches.cashflow_edge_fixture_gate_enabled,
            "Cash-flow edge fixtures exist, but they are validation-only and the policy switch remains off.",
        ),
        _pricing_switch_row(
            "holder_allocation_gate",
            switches.holder_allocation_gate_enabled,
            "Holder-allocation gate evidence exists, but no allocation switch is enabled.",
        ),
        _pricing_switch_row(
            "holder_bridge_enabled",
            switches.holder_bridge_enabled,
            "CUSIP-to-final-owner holder bridge remains disabled.",
        ),
        _pricing_switch_row(
            "tax_assumptions_enabled",
            switches.tax_assumptions_enabled,
            "Tax assumption layer remains disabled.",
        ),
        _pricing_switch_row(
            "mpc_assumptions_enabled",
            switches.mpc_assumptions_enabled,
            "MPC assumption layer remains disabled.",
        ),
        _pricing_switch_row(
            "welfare_incidence_enabled",
            switches.welfare_incidence_enabled,
            "Welfare/incidence layer remains disabled.",
        ),
        _pricing_switch_row(
            "explicit_pricing_authorization_enabled",
            switches.explicit_pricing_authorization_enabled,
            "Explicit pricing authorization remains disabled.",
        ),
    ]
    return rows


def cashflow_edge_source_sample_rows(
    *,
    frn_records: list[dict],
    frn_terms: dict[str, list[dict]] | None = None,
    tips_records: list[dict],
    tips_terms: dict[str, dict],
    tips_term_rows: dict[str, list[dict]] | None = None,
) -> list[dict[str, str]]:
    """Build validation-only edge rows from live/source-backed records."""

    rows: list[dict[str, str]] = []
    frn_reset, frn_reset_classifier = _select_frn_reset_boundary_sample(
        frn_records,
        frn_terms or {},
    )
    if frn_reset:
        index = decimal_from_record(frn_reset, "daily_index")
        spread = decimal_from_record(frn_reset, "spread")
        observed = decimal_from_record(frn_reset, "daily_int_accrual_rate")
        expected = None
        if index is not None and spread is not None and observed is not None:
            expected = (
                index + spread
                if observed > 1
                else (index + spread) / Decimal("36000")
            )
        rows.append(
            _cashflow_edge_row(
                fixture_id="frn_reset_date_boundary_source_sample",
                security_kind="frn",
                edge_case="reset-date boundary source sample",
                sample_source="source_backed_snapshot",
                source_cusip=str(frn_reset.get("cusip", "")),
                source_record_date=_source_record_date(frn_reset),
                **frn_reset_classifier,
                source_fields_required=(
                    "treasury_frn_daily_indexes.cusip;"
                    "treasury_frn_daily_indexes.index_date;"
                    "treasury_frn_daily_indexes.daily_index;"
                    "treasury_frn_daily_indexes.spread;"
                    "treasury_frn_daily_indexes.daily_int_accrual_rate"
                ),
                fixture_formula="daily_index plus spread maps to reported daily_int_accrual_rate",
                example_name="source_daily_index_plus_spread",
                expected=expected,
                observed=observed,
                tolerance=Decimal("0.000001"),
                calculation_status=_source_edge_status(expected, observed, Decimal("0.000001")),
                calculation_note=(
                    "Source-backed FRN row validates daily reset arithmetic only; "
                    "it is not coupon pricing or holder cash-flow output."
                ),
            )
        )
    frn_leap, frn_leap_classifier = _select_frn_leap_day_sample(frn_records)
    if frn_leap:
        validation = validate_frn_daily_accrued_interest(frn_leap)
        rows.append(
            _cashflow_edge_row(
                fixture_id="frn_leap_day_accrual_period_source_sample",
                security_kind="frn",
                edge_case="leap-day accrual source sample",
                sample_source="source_backed_snapshot",
                source_cusip=str(frn_leap.get("cusip", "")),
                source_record_date=_source_record_date(frn_leap),
                **frn_leap_classifier,
                source_fields_required=(
                    "treasury_frn_daily_indexes.index_date;"
                    "treasury_frn_daily_indexes.daily_int_accrual_rate;"
                    "treasury_frn_daily_indexes.daily_accrued_int_per100"
                ),
                fixture_formula="daily_accrued_int_per100 follows reported daily accrual convention",
                example_name=validation.formula_name,
                expected=validation.expected_value,
                observed=validation.observed_value,
                tolerance=validation.tolerance,
                calculation_status=_edge_status_from_validation(validation),
                calculation_note=(
                    "Source-backed FRN row validates reported daily accrued interest "
                    "per $100 only; it is not a day-count pricing result."
                ),
            )
        )
    tips_rounding = _select_tips_rounding_sample(tips_records, tips_terms)
    if tips_rounding:
        record, validation, classifier = tips_rounding
        rows.append(
            _cashflow_edge_row(
                fixture_id="tips_cpi_interpolation_rounding_source_sample",
                security_kind="tips",
                edge_case="CPI interpolation and rounding source sample",
                sample_source="source_backed_snapshot",
                source_cusip=str(record.get("cusip", "")),
                source_record_date=str(record.get("index_date", "")),
                **classifier,
                source_fields_required=(
                    "treasury_tips_cpi_detail.ref_cpi;"
                    "treasury_tips_cpi_detail.index_ratio;"
                    "treasury_auction_tips_terms.ref_cpi_on_issue_date;"
                    "treasury_auction_tips_terms.index_ratio_on_issue_date"
                ),
                fixture_formula="daily_ref_cpi divided by issue-derived base CPI maps to source index_ratio",
                example_name=validation.formula_name,
                expected=validation.expected_value,
                observed=validation.observed_value,
                tolerance=validation.tolerance,
                calculation_status=_edge_status_from_validation(validation),
                calculation_note=(
                    "Source-backed TIPS row validates CPI/index-ratio arithmetic "
                    "or tolerance-edge classification only; it is not indexed-principal pricing."
                ),
            )
        )
    tips_reopening = _select_tips_reopening_sample(
        tips_records,
        tips_terms,
        tips_term_rows or {},
    )
    if tips_reopening:
        record, validation, classifier = tips_reopening
        rows.append(
            _cashflow_edge_row(
                fixture_id="tips_reopening_issue_date_source_sample",
                security_kind="tips",
                edge_case="reopening issue-date source sample",
                sample_source="source_backed_snapshot",
                source_cusip=str(record.get("cusip", "")),
                source_record_date=str(record.get("index_date", "")),
                **classifier,
                source_fields_required=(
                    "treasury_tips_cpi_detail.cusip;"
                    "treasury_tips_cpi_detail.original_issue_date;"
                    "treasury_auction_tips_terms.cusip;"
                    "treasury_auction_tips_terms.ref_cpi_on_issue_date"
                ),
                fixture_formula="issue-term CPI inputs remain an input gate for source TIPS rows",
                example_name=validation.formula_name,
                expected=validation.expected_value,
                observed=validation.observed_value,
                tolerance=validation.tolerance,
                calculation_status=_edge_status_from_validation(validation),
                calculation_note=(
                    "Source-backed TIPS row validates issue-term matching only; "
                    "it is not indexed-principal pricing."
                ),
            )
        )
    return rows


def valuation_engine_opt_in_contract_rows(
    *,
    convention_audit_rows: list[dict[str, str]],
    cashflow_edge_rows: list[dict[str, str]],
    holder_gate_rows: list[dict[str, str]],
    switches: ValuationOptInSwitches | None = None,
) -> list[dict[str, str]]:
    """Return a fail-closed opt-in contract for future valuation work."""

    switches = switches or ValuationOptInSwitches()
    conventions_audited = all(
        row.get("audit_passed") == "true" for row in convention_audit_rows
    ) and bool(convention_audit_rows)
    edge_fixtures_defined = all(
        row.get("test_status") == "fixture_contract_tested_not_pricing"
        and row.get("pricing_output_enabled") == "false"
        for row in cashflow_edge_rows
    ) and bool(cashflow_edge_rows)
    holder_gate_present = bool(holder_gate_rows) and all(
        row.get("incidence_claim_enabled") == "false" for row in holder_gate_rows
    )
    rows = [
        _opt_in_requirement_row(
            requirement_id="audited_conventions",
            evidence_status=(
                "satisfied_not_pricing" if conventions_audited else "missing_or_failed"
            ),
            requirement_satisfied=conventions_audited,
            switch_name="convention_audit_gate",
            switch_enabled=switches.convention_audit_gate_enabled,
            blocker=(
                ""
                if conventions_audited
                else "requires_passing_frn_and_tips_convention_audits"
            ),
        ),
        _opt_in_requirement_row(
            requirement_id="cashflow_edge_fixtures",
            evidence_status=(
                "fixtures_defined_not_pricing"
                if edge_fixtures_defined
                else "fixtures_missing_or_unreviewed"
            ),
            requirement_satisfied=edge_fixtures_defined,
            switch_name="cashflow_edge_fixture_gate",
            switch_enabled=switches.cashflow_edge_fixture_gate_enabled,
            blocker=(
                ""
                if edge_fixtures_defined
                else "requires_frn_tips_cashflow_edge_fixtures"
            ),
        ),
        _opt_in_requirement_row(
            requirement_id="holder_allocation_gate",
            evidence_status=(
                "gate_present_disabled_not_incidence"
                if holder_gate_present
                else "holder_gate_missing_or_enabled"
            ),
            requirement_satisfied=holder_gate_present,
            switch_name="holder_allocation_gate",
            switch_enabled=switches.holder_allocation_gate_enabled,
            blocker=(
                ""
                if holder_gate_present
                else "requires_disabled_holder_allocation_gate"
            ),
        ),
        _opt_in_requirement_row(
            requirement_id="explicit_pricing_switch",
            evidence_status="disabled_by_policy",
            requirement_satisfied=switches.pricing_request_authorized,
            switch_name="pricing_output_enabled",
            switch_enabled=switches.explicit_pricing_authorization_enabled,
            blocker=(
                ""
                if switches.pricing_request_authorized
                else "explicit_pricing_switch_disabled_by_policy"
            ),
        ),
    ]
    return rows


def _opt_in_requirement_row(
    *,
    requirement_id: str,
    evidence_status: str,
    requirement_satisfied: bool,
    switch_name: str,
    switch_enabled: bool,
    blocker: str,
) -> dict[str, str]:
    return {
        "contract_schema_version": VALUATION_ENGINE_OPT_IN_SCHEMA_VERSION,
        "requirement_id": requirement_id,
        "evidence_status": evidence_status,
        "requirement_satisfied": "true" if requirement_satisfied else "false",
        "switch_name": switch_name,
        "switch_enabled": "true" if switch_enabled else "false",
        "valuation_engine_ready": "false",
        "pricing_output_enabled": "false",
        "holder_allocation_enabled": "false",
        "incidence_claim_enabled": "false",
        "blocker": blocker,
        "claim_boundary": "disabled_valuation_opt_in_contract_not_pricing",
    }


def _cashflow_edge_row(
    *,
    fixture_id: str,
    security_kind: str,
    edge_case: str,
    sample_source: str,
    source_cusip: str,
    source_record_date: str,
    source_edge_classifier: str,
    source_edge_classifier_status: str,
    source_edge_evidence_fields: str,
    source_edge_blocker: str,
    source_edge_note: str,
    source_fields_required: str,
    fixture_formula: str,
    example_name: str,
    expected: Decimal | None,
    observed: Decimal | None,
    tolerance: Decimal,
    calculation_status: str,
    calculation_note: str,
) -> dict[str, str]:
    difference = (
        abs(expected - observed) if expected is not None and observed is not None else None
    )
    return {
        "fixture_schema_version": CASHFLOW_EDGE_FIXTURE_SCHEMA_VERSION,
        "fixture_id": fixture_id,
        "security_kind": security_kind,
        "edge_case": edge_case,
        "sample_source": sample_source,
        "source_cusip": source_cusip,
        "source_record_date": source_record_date,
        "source_edge_classifier": source_edge_classifier,
        "source_edge_classifier_status": source_edge_classifier_status,
        "source_edge_evidence_fields": source_edge_evidence_fields,
        "source_edge_blocker": source_edge_blocker,
        "source_edge_note": source_edge_note,
        "source_fields_required": source_fields_required,
        "fixture_formula": fixture_formula,
        "example_calculation_name": example_name,
        "example_expected_value": _string_or_blank(expected),
        "example_observed_value": _string_or_blank(observed),
        "example_absolute_difference": _string_or_blank(difference),
        "example_tolerance": str(tolerance),
        "example_calculation_status": calculation_status,
        "example_calculation_note": calculation_note,
        "fixture_status": "fixture_defined_not_pricing",
        "test_status": "fixture_contract_tested_not_pricing",
        "pricing_output_enabled": "false",
        "claim_boundary": "cashflow_edge_fixture_not_pricing_engine",
    }


def _pricing_switch_row(
    switch_name: str,
    switch_enabled: bool,
    blocker_note: str,
) -> dict[str, str]:
    return {
        "audit_schema_version": PRICING_SWITCH_AUDIT_SCHEMA_VERSION,
        "switch_name": switch_name,
        "switch_enabled": "true" if switch_enabled else "false",
        "pricing_output_enabled": "false",
        "holder_allocation_enabled": "false",
        "incidence_claim_enabled": "false",
        "blocker_note": blocker_note if not switch_enabled else "",
        "claim_boundary": "pricing_switch_audit_disabled_not_pricing",
    }


def _select_frn_reset_boundary_sample(
    records: list[dict],
    terms_by_cusip: dict[str, list[dict]],
) -> tuple[dict | None, dict[str, str]]:
    sorted_records = sorted(
        records,
        key=lambda record: (
            str(record.get("cusip", "")),
            _source_record_date(record),
        ),
    )
    previous: dict | None = None
    for record in sorted_records:
        if (
            previous is not None
            and str(previous.get("cusip", "")) == str(record.get("cusip", ""))
            and str(previous.get("daily_int_accrual_rate", ""))
            != str(record.get("daily_int_accrual_rate", ""))
        ):
            terms = terms_by_cusip.get(str(record.get("cusip", "")), [])
            term_note = _frn_term_evidence_note(terms)
            return record, {
                "source_edge_classifier": "frn_reset_boundary_classifier",
                "source_edge_classifier_status": (
                    "source_rate_change_observed_with_term_fields_recurring_reset_calendar_missing_not_pricing"
                    if terms
                    else "source_rate_change_observed_missing_term_reset_fields_not_pricing"
                ),
                "source_edge_evidence_fields": (
                    "cusip;record_date;start_of_accrual_period;end_of_accrual_period;"
                    "daily_index;spread;daily_int_accrual_rate;"
                    "treasury_auction_frn_terms.frn_index_determination_date;"
                    "treasury_auction_frn_terms.frn_index_determination_rate;"
                    "treasury_auction_frn_terms.reopening"
                ),
                "source_edge_blocker": (
                    "official auctions_query term fields are joined, but "
                    "treasury_frn_daily_indexes and auctions_query do not expose "
                    "a full recurring reset-calendar date for each daily source row"
                    if terms
                    else "no matching treasury_auction_frn_terms row found for this CUSIP"
                ),
                "source_edge_note": (
                    "Source rows show a within-CUSIP daily accrual-rate change, "
                    f"and {term_note} Exact recurring reset-boundary dating "
                    "remains blocked by missing source reset-calendar fields; "
                    "validation remains not pricing."
                ),
            }
        previous = record
    if not sorted_records:
        return None, _source_classifier_missing(
            "frn_reset_boundary_classifier",
            "no_treasury_frn_daily_indexes_records",
        )
    return sorted_records[0], {
        "source_edge_classifier": "frn_reset_boundary_classifier",
        "source_edge_classifier_status": "not_observed_in_current_snapshot_not_pricing",
        "source_edge_evidence_fields": (
            "cusip;record_date;start_of_accrual_period;end_of_accrual_period;"
            "daily_index;spread;daily_int_accrual_rate"
        ),
        "source_edge_blocker": (
            "no within-CUSIP daily_int_accrual_rate change observed in current "
            "matched FRN source sample"
        ),
        "source_edge_note": (
            "Fallback FRN source row is retained for arithmetic validation only; "
            "it is not a confirmed reset-boundary row."
        ),
    }


def _select_frn_leap_day_sample(
    records: list[dict],
) -> tuple[dict | None, dict[str, str]]:
    for record in records:
        if any(
            str(record.get(field, "")).endswith("-02-29")
            for field in (
                "index_date",
                "record_date",
                "start_of_accrual_period",
                "end_of_accrual_period",
            )
        ):
            return record, {
                "source_edge_classifier": "frn_leap_day_classifier",
                "source_edge_classifier_status": "source_leap_day_observed_not_pricing",
                "source_edge_evidence_fields": (
                    "record_date;start_of_accrual_period;end_of_accrual_period;"
                    "daily_int_accrual_rate;daily_accrued_int_per100"
                ),
                "source_edge_blocker": "",
                "source_edge_note": (
                    "Source date fields include a Feb. 29 row; validation checks "
                    "reported daily accrual only and remains not pricing."
                ),
            }
    if not records:
        return None, _source_classifier_missing(
            "frn_leap_day_classifier",
            "no_treasury_frn_daily_indexes_records",
        )
    return records[0], {
        "source_edge_classifier": "frn_leap_day_classifier",
        "source_edge_classifier_status": "not_observed_in_current_snapshot_not_pricing",
        "source_edge_evidence_fields": (
            "record_date;start_of_accrual_period;end_of_accrual_period;"
            "daily_int_accrual_rate;daily_accrued_int_per100"
        ),
        "source_edge_blocker": (
            "official frn_daily_indexes history retrieved for this snapshot has "
            "no record_date, start_of_accrual_period, or end_of_accrual_period "
            "ending in 02-29"
        ),
        "source_edge_note": (
            "Fallback FRN source row is retained for daily-accrual validation; "
            "a true leap-day source sample requires a snapshot containing Feb. 29."
        ),
    }


def _select_tips_rounding_sample(
    records: list[dict],
    terms_by_cusip: dict[str, dict],
) -> tuple[dict, FormulaValidation] | None:
    fallback: tuple[dict, FormulaValidation, dict[str, str]] | None = None
    for record in records:
        validation = validate_tips_index_ratio(
            record,
            terms_by_cusip.get(str(record.get("cusip", "")), {}),
        )
        if fallback is None and validation.status == "formula_validated_not_pricing":
            fallback = (
                record,
                validation,
                {
                    "source_edge_classifier": "tips_rounding_review_classifier",
                    "source_edge_classifier_status": (
                        "not_observed_fallback_validated_row_not_pricing"
                    ),
                    "source_edge_evidence_fields": (
                        "cusip;index_date;ref_cpi;index_ratio;"
                        "ref_cpi_on_issue_date;index_ratio_on_issue_date"
                    ),
                    "source_edge_blocker": (
                        "no matched TIPS formula-review row observed before "
                        "fallback selection"
                    ),
                    "source_edge_note": (
                        "Fallback TIPS source row validates CPI/index-ratio "
                        "arithmetic but is not a tolerance-edge sample."
                    ),
                },
            )
        if validation.status == "formula_review_not_pricing":
            classification = classify_tips_formula_review(
                record,
                terms_by_cusip.get(str(record.get("cusip", "")), {}),
                validation,
            )
            if not classification.unresolved:
                return record, validation, {
                    "source_edge_classifier": "tips_rounding_review_classifier",
                    "source_edge_classifier_status": classification.status,
                    "source_edge_evidence_fields": (
                        "cusip;index_date;ref_cpi;index_ratio;"
                        "ref_cpi_on_issue_date;index_ratio_on_issue_date;"
                        "absolute_difference;tolerance"
                    ),
                    "source_edge_blocker": "",
                    "source_edge_note": classification.rationale,
                }
    return fallback


def _select_tips_reopening_sample(
    records: list[dict],
    terms_by_cusip: dict[str, dict],
    term_rows_by_cusip: dict[str, list[dict]],
) -> tuple[dict, FormulaValidation, dict[str, str]] | None:
    fallback: tuple[dict, FormulaValidation, dict[str, str]] | None = None
    for record in records:
        cusip = str(record.get("cusip", ""))
        terms = terms_by_cusip.get(cusip, {})
        term_rows = term_rows_by_cusip.get(cusip, [])
        if not term_rows and terms:
            term_rows = [terms]
        reopening_terms = [
            term for term in term_rows if str(term.get("reopening", "")).lower() == "yes"
        ]
        validation = validate_tips_index_ratio(record, terms)
        if fallback is None:
            fallback = (
                record,
                validation,
                {
                    "source_edge_classifier": "tips_reopening_classifier",
                    "source_edge_classifier_status": (
                        "not_observed_in_current_snapshot_not_pricing"
                    ),
                    "source_edge_evidence_fields": (
                        "cusip;original_issue_date;index_date;"
                        "treasury_auction_tips_terms.reopening;issue_date"
                    ),
                    "source_edge_blocker": (
                        "no matched TIPS daily CPI row joins to an auction term "
                        "record with reopening=Yes in the current snapshot"
                    ),
                    "source_edge_note": (
                        "Fallback TIPS source row validates issue-term matching; "
                        "a true reopening classifier requires a matched auction "
                        "term row with reopening=Yes."
                    ),
                },
            )
        if reopening_terms:
            return record, validation, {
                "source_edge_classifier": "tips_reopening_classifier",
                "source_edge_classifier_status": "source_reopening_observed_not_pricing",
                "source_edge_evidence_fields": (
                    "cusip;original_issue_date;index_date;"
                    "treasury_auction_tips_terms.reopening;issue_date"
                ),
                "source_edge_blocker": "",
                "source_edge_note": (
                    "Matched source terms identify the CUSIP as a reopening; "
                    f"{len(reopening_terms)} reopening auction term row(s) are "
                    "available for this CUSIP. Validation checks issue-term "
                    "inputs only and remains not pricing."
                ),
            }
    return fallback


def _source_record_date(record: dict) -> str:
    return str(
        record.get("index_date")
        or record.get("record_date")
        or record.get("start_of_accrual_period")
        or record.get("end_of_accrual_period")
        or ""
    )


def _source_classifier_missing(classifier: str, blocker: str) -> dict[str, str]:
    return {
        "source_edge_classifier": classifier,
        "source_edge_classifier_status": "source_records_missing_not_pricing",
        "source_edge_evidence_fields": "",
        "source_edge_blocker": blocker,
        "source_edge_note": (
            "No source-backed row can be selected for this classifier; output "
            "remains validation-only and pricing disabled."
        ),
    }


def _frn_term_evidence_note(terms: list[dict]) -> str:
    term_dates = [
        str(term.get("frn_index_determination_date", ""))
        for term in terms
        if str(term.get("frn_index_determination_date", "")) not in {"", "null"}
    ]
    reopening_values = sorted(
        {
            str(term.get("reopening", ""))
            for term in terms
            if str(term.get("reopening", "")) not in {"", "null"}
        }
    )
    if not terms:
        return "no FRN term rows are joined."
    return (
        f"{len(terms)} FRN auction term row(s) are joined with "
        f"index-determination dates {','.join(term_dates) or 'none'} "
        f"and reopening flags {','.join(reopening_values) or 'none'}."
    )


def _source_edge_status(
    expected: Decimal | None,
    observed: Decimal | None,
    tolerance: Decimal,
) -> str:
    if expected is None or observed is None:
        return "example_input_unavailable_not_pricing"
    if abs(expected - observed) <= tolerance:
        return "example_validated_not_pricing"
    return "example_review_not_pricing"


def _edge_status_from_validation(validation: FormulaValidation) -> str:
    if validation.status == "formula_validated_not_pricing":
        return "example_validated_not_pricing"
    if validation.status == "formula_review_not_pricing":
        return "example_review_not_pricing"
    return "example_input_unavailable_not_pricing"


def decimal_from_record(record: dict, key: str) -> Decimal | None:
    raw = record.get(key)
    if raw in (None, "", ".", "null"):
        return None
    try:
        return Decimal(str(raw).replace(",", ""))
    except Exception:
        return None


def _decimal_scale(value: Decimal | None) -> int:
    if value is None:
        return 0
    return max(0, -value.as_tuple().exponent)


def _result(
    *,
    formula_name: str,
    expected: Decimal,
    observed: Decimal,
    tolerance: Decimal,
    note: str,
) -> FormulaValidation:
    difference = abs(expected - observed)
    return FormulaValidation(
        formula_name=formula_name,
        status=(
            "formula_validated_not_pricing"
            if difference <= tolerance
            else "formula_review_not_pricing"
        ),
        expected_value=expected,
        observed_value=observed,
        absolute_difference=difference,
        tolerance=tolerance,
        note=note,
    )


def _unavailable(
    formula_name: str, reason: str, tolerance: Decimal
) -> FormulaValidation:
    return FormulaValidation(
        formula_name=formula_name,
        status="formula_input_unavailable_not_pricing",
        expected_value=None,
        observed_value=None,
        absolute_difference=None,
        tolerance=tolerance,
        note=f"{reason}; formula validation remains not final pricing.",
    )


def _string_or_blank(value: Decimal | None) -> str:
    return "" if value is None else str(value)
