"""TDSP current-demand blocker rows without databook-wide build wiring."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from ratewall.databook.policy_path_normalization import (
    POLICY_PATH_BPS_EXPOSURE_FORMULA,
    blocked_policy_path_normalization_fields,
)
from ratewall.sources.base import SourceSnapshot


_CONVENTIONAL_DRAG_EVIDENCE = {
    "handles": (
        "admissible_shock_denominator_design;borrowing_cost_credit_supply_"
        "asset_price_expectations_external_channels"
    ),
    "status": "source_specific_shock_context_available_denominator_priors_review",
}
TDSP_PAYMENT_DOLLARS_AVAILABLE_STATUS = (
    "mechanical_tdsp_payment_dollars_candidate_available_not_current_demand_bridge"
)
TDSP_CURRENT_DEMAND_GDP_SHARE_AVAILABLE_STATUS = (
    "mechanical_tdsp_current_demand_gdp_share_candidate_available_not_promoted"
)
TDSP_CORE_RESPONSE_ADMISSION_CLASS = "core"
TDSP_CORE_RESPONSE_SOURCE_FAMILY = "tdsp_household_cashflow_current_demand_response"
TDSP_RESPONSE_UNITS = (
    "dollars_current_demand_reduction_per_dollar_payment_increase"
)
TDSP_RESPONSE_SIGN_CONVENTION = "positive_payment_change_reduces_current_demand"


@dataclass(frozen=True)
class TdspPaymentDollarsCandidate:
    status: str
    date: str
    tdsp_percent_of_dpi: Decimal | None
    dspi_bil_saar: Decimal | None
    payment_bil_saar: Decimal | None
    exact_blocker: str


@dataclass(frozen=True)
class TdspCurrentDemandGdpShareCandidate:
    status: str
    date: str
    payment_bil_saar: Decimal | None
    payment_change_bil_saar: Decimal | None
    response_id: str
    response_admission_class: str
    marginal_current_demand_response: Decimal | None
    current_demand_bil_saar: Decimal | None
    nominal_gdp_bil_saar: Decimal | None
    current_demand_gdp_share: Decimal | None
    exact_blocker: str


@dataclass(frozen=True)
class TdspMarginalCurrentDemandResponse:
    response_id: str
    admission_class: str
    source_title: str
    source_url_or_citation: str
    source_family: str
    payment_object: str
    demand_object: str
    timing_convention: str
    units: str
    sign_convention: str
    central: Decimal | None
    lower: Decimal | None
    upper: Decimal | None
    uncertainty_basis: str
    admitted_for_core: bool


def tdsp_payment_dollars_candidate(
    *, snapshots: list[SourceSnapshot]
) -> TdspPaymentDollarsCandidate:
    snapshot_map = _source_snapshot_map(snapshots)
    tdsp = snapshot_map.get("TDSP")
    dspi = snapshot_map.get("DSPI")
    if tdsp is None or dspi is None:
        return _blocked_payment_candidate(
            "blocked_missing_tdsp_or_dspi_snapshot",
            "TDSP and DSPI snapshots are required for the mechanical payment-dollar "
            "candidate.",
        )
    tdsp_records = _numeric_records_by_date(tdsp)
    dspi_records = _numeric_records_by_date(dspi)
    common_dates = sorted(set(tdsp_records) & set(dspi_records))
    if not common_dates:
        return _blocked_payment_candidate(
            "blocked_no_common_tdsp_dspi_date",
            "TDSP and DSPI snapshots do not share an exact observation date.",
        )
    date_key = common_dates[-1]
    tdsp_percent = tdsp_records[date_key]
    dspi_bil_saar = dspi_records[date_key]
    payment_bil_saar = dspi_bil_saar * tdsp_percent / Decimal("100")
    return TdspPaymentDollarsCandidate(
        status=TDSP_PAYMENT_DOLLARS_AVAILABLE_STATUS,
        date=date_key,
        tdsp_percent_of_dpi=tdsp_percent,
        dspi_bil_saar=dspi_bil_saar,
        payment_bil_saar=payment_bil_saar,
        exact_blocker=(
            "TDSP-to-payment-dollars is a source-backed mechanical candidate, "
            "but no marginal current-demand response, GDP-share drag conversion, "
            "policy-path normalization, uncertainty, or promotion gate is admitted."
        ),
    )


def tdsp_current_demand_gdp_share_candidate(
    *,
    snapshots: list[SourceSnapshot],
    payment_change_bil_saar: object | None = None,
    marginal_current_demand_response: object | None = None,
    response_admitted: bool = False,
) -> TdspCurrentDemandGdpShareCandidate:
    payment = tdsp_payment_dollars_candidate(snapshots=snapshots)
    if payment.payment_bil_saar is None:
        return _blocked_gdp_share_candidate(
            payment.status,
            payment.exact_blocker,
        )
    if marginal_current_demand_response is None or not response_admitted:
        return _blocked_gdp_share_candidate(
            "blocked_no_admitted_marginal_current_demand_response",
            "A source-backed marginal current-demand response must be admitted "
            "before payment dollars can become current-demand GDP share.",
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
        )
    if not isinstance(
        marginal_current_demand_response, TdspMarginalCurrentDemandResponse
    ):
        return _blocked_gdp_share_candidate(
            "blocked_unstructured_marginal_current_demand_response_not_admitted",
            "A bare scalar cannot admit the TDSP current-demand bridge; response "
            "metadata must identify source, admission class, units, sign, timing, "
            "and uncertainty.",
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
        )
    response_object = marginal_current_demand_response
    if (
        response_object.admission_class != TDSP_CORE_RESPONSE_ADMISSION_CLASS
        or not response_object.admitted_for_core
    ):
        return _blocked_gdp_share_candidate(
            "blocked_marginal_current_demand_response_not_core_admitted",
            "Only a core-admitted source-backed marginal current-demand response "
            "can enter the TDSP GDP-share candidate; sensitivity and context "
            "objects remain blocked from runtime and denominator admission.",
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
            response_id=response_object.response_id,
            response_admission_class=response_object.admission_class,
        )
    if response_object.source_family != TDSP_CORE_RESPONSE_SOURCE_FAMILY:
        return _blocked_gdp_share_candidate(
            "blocked_marginal_current_demand_response_source_family_mismatch",
            "A core TDSP current-demand bridge must come from the approved "
            "household-cash-flow current-demand response source family; generic "
            "MPCs, single-product proxies, and sensitivity objects remain "
            "blocked even if their unit labels match.",
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
            response_id=response_object.response_id,
            response_admission_class=response_object.admission_class,
        )
    if (
        response_object.units != TDSP_RESPONSE_UNITS
        or response_object.sign_convention != TDSP_RESPONSE_SIGN_CONVENTION
    ):
        return _blocked_gdp_share_candidate(
            "blocked_marginal_current_demand_response_unit_contract_mismatch",
            "The TDSP bridge requires a positive response magnitude in dollars "
            "of current-demand reduction per dollar payment increase.",
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
            response_id=response_object.response_id,
            response_admission_class=response_object.admission_class,
        )
    if response_object.central is None:
        return _blocked_gdp_share_candidate(
            "blocked_missing_core_marginal_current_demand_response_central",
            "A core TDSP marginal current-demand response must include a "
            "source-backed central response magnitude.",
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
            response_id=response_object.response_id,
            response_admission_class=response_object.admission_class,
        )
    try:
        response_magnitude = _nonnegative_decimal(response_object.central)
    except ValueError as exc:
        return _blocked_gdp_share_candidate(
            "blocked_invalid_core_marginal_current_demand_response",
            str(exc),
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
            response_id=response_object.response_id,
            response_admission_class=response_object.admission_class,
        )
    if payment_change_bil_saar is None:
        return _blocked_gdp_share_candidate(
            "blocked_no_tdsp_payment_change_input",
            "The TDSP current-demand bridge is defined on changes in required "
            "payments, not the total level of TDSP payment dollars.",
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
            response_id=response_object.response_id,
            response_admission_class=response_object.admission_class,
        )
    try:
        payment_change = _decimal(payment_change_bil_saar)
    except ValueError as exc:
        return _blocked_gdp_share_candidate(
            "blocked_invalid_tdsp_payment_change_input",
            str(exc),
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
            response_id=response_object.response_id,
            response_admission_class=response_object.admission_class,
        )
    snapshot_map = _source_snapshot_map(snapshots)
    gdp = snapshot_map.get("GDP")
    if gdp is None:
        return _blocked_gdp_share_candidate(
            "blocked_missing_nominal_gdp_snapshot",
            "A nominal GDP snapshot is required for current-demand GDP-share "
            "conversion.",
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
            payment_change_bil_saar=payment_change,
            response_id=response_object.response_id,
            response_admission_class=response_object.admission_class,
        )
    gdp_records = _numeric_records_by_date(gdp)
    nominal_gdp = gdp_records.get(payment.date)
    if nominal_gdp is None or nominal_gdp <= Decimal("0"):
        return _blocked_gdp_share_candidate(
            "blocked_missing_or_nonpositive_nominal_gdp_for_payment_date",
            "Nominal GDP must be positive on the TDSP/DSPI payment date.",
            date=payment.date,
            payment_bil_saar=payment.payment_bil_saar,
            payment_change_bil_saar=payment_change,
            response_id=response_object.response_id,
            response_admission_class=response_object.admission_class,
        )
    response = -response_magnitude
    current_demand = payment_change * response
    return TdspCurrentDemandGdpShareCandidate(
        status=TDSP_CURRENT_DEMAND_GDP_SHARE_AVAILABLE_STATUS,
        date=payment.date,
        payment_bil_saar=payment.payment_bil_saar,
        payment_change_bil_saar=payment_change,
        response_id=response_object.response_id,
        response_admission_class=response_object.admission_class,
        marginal_current_demand_response=response,
        current_demand_bil_saar=current_demand,
        nominal_gdp_bil_saar=nominal_gdp,
        current_demand_gdp_share=current_demand / nominal_gdp,
        exact_blocker=(
            "Current-demand GDP-share arithmetic is a candidate only; promotion "
            "still requires reviewed policy-path normalization, uncertainty, "
            "replication, robustness, and admission gates."
        ),
    )


def tdsp_current_demand_unit_conversion_rows(
    *, snapshots: list[SourceSnapshot]
) -> list[dict[str, str]]:
    snapshot_map = _source_snapshot_map(snapshots)
    payment_candidate = tdsp_payment_dollars_candidate(snapshots=snapshots)
    specs = [
        (
            "tdsp_ratio_to_payment_dollars",
            "TDSP",
            "DSPI",
            "percent_of_disposable_income",
            "payment_dollars",
            "blocked_missing_disposable_income_snapshot_and_tdsp_payment_base",
            "TDSP_payment_dollars = TDSP_percent_of_DPI * DPI",
            "TDSP is published as a percent of disposable income, but no DPI/"
            "DSPI snapshot and no reviewed numerator convention are admitted.",
        ),
        (
            "payment_dollars_to_current_demand",
            "TDSP",
            "PCEC;PCECC96",
            "payment_dollars",
            "current_demand_dollars",
            "blocked_missing_marginal_consumption_response_bridge",
            "current_demand_drag = payment_change * marginal_current_demand_response",
            "No source-backed marginal current-demand response, MPC, or PCE "
            "quantity bridge is admitted.",
        ),
        (
            "current_demand_dollars_to_gdp_share",
            "GDP",
            "GDP",
            "current_demand_dollars",
            "gdp_share_per_100bp_year",
            "blocked_missing_current_demand_dollars_and_policy_path_normalization",
            "gdp_share_drag = current_demand_dollars / nominal_GDP / bps_year",
            "GDP is available, but the numerator current-demand dollars and "
            "bps-year exposure denominator are not admitted.",
        ),
        (
            "tdsp_diagnostic_points_to_gdp_growth",
            "TDSP",
            "GDP",
            "tdsp_level_change_points",
            "annualized_gdp_percent_change",
            "diagnostic_mapping_estimable_but_not_unit_conversion",
            "OLS maps TDSP changes to GDP changes for review only",
            "A diagnostic regression can be estimated from current snapshots, "
            "but it is not a source-backed unit conversion or causal demand "
            "drag object.",
        ),
        (
            "scalar_shock_to_100bp_year_policy_path",
            "fed_brw_monetary_policy_shocks;sf_fed_monetary_policy_surprises",
            "policy_path_exposure_vector",
            "event_scalar_bps_or_pctpt",
            "bps_year",
            "blocked_no_reviewed_policy_path_exposure_vector",
            POLICY_PATH_BPS_EXPOSURE_FORMULA,
            "The shock sources contain event scalars, not a reviewed path vector.",
        ),
    ]
    rows: list[dict[str, str]] = []
    for conversion_id, source_id, aux_ids, input_units, target_units, status, formula, blocker in specs:
        output_value = ""
        source_backing_status = "blocked_missing_required_source_or_design_gate"
        exact_blocker = blocker
        if (
            conversion_id == "tdsp_ratio_to_payment_dollars"
            and payment_candidate.payment_bil_saar is not None
        ):
            status = payment_candidate.status
            source_backing_status = "source_backed_tdsp_dspi_inputs_available"
            output_value = _format_decimal(payment_candidate.payment_bil_saar)
            exact_blocker = payment_candidate.exact_blocker
        source_ids = [part for part in f"{source_id};{aux_ids}".split(";") if part]
        rows.append(
            {
                "unit_conversion_id": f"tdsp_current_demand_unit_conversion::{conversion_id}",
                "conversion_input_role": conversion_id,
                "input_source_id": source_id,
                "required_auxiliary_source_ids": aux_ids,
                "input_units": input_units,
                "target_units": target_units,
                "mechanical_conversion_status": status,
                "source_backing_requirement_status": source_backing_status,
                "conversion_formula_candidate": formula,
                "conversion_output_value": output_value,
                "conversion_uncertainty_status": (
                    "blocked_no_conversion_level_uncertainty_protocol"
                ),
                "exact_blocker": exact_blocker,
                "evidence_needed_before_mapping": (
                    "All conversion inputs require source snapshots, a reviewed "
                    "mapping formula, uncertainty propagation, replication, and "
                    "promotion-gate pass before any demand-drag use."
                ),
                "source_status": "tdsp_current_demand_unit_conversion_blocked",
                **tdsp_mapping_false_fields(
                    source_ids=source_ids,
                    artifacts="ratewall_tdsp_current_demand_unit_conversion.csv",
                    snapshot_map=snapshot_map,
                    evidence_status="tdsp_current_demand_unit_conversion_fail_closed",
                    claim_boundary=(
                        "tdsp_current_demand_unit_conversion_not_prior_narrowing"
                    ),
                ),
            }
        )
    return rows


def tdsp_policy_path_normalization_blocker_rows(
    *,
    evidence_tranche_rows: list[dict[str, str]],
    snapshots: list[SourceSnapshot],
) -> list[dict[str, str]]:
    snapshot_map = _source_snapshot_map(snapshots)
    rows: list[dict[str, str]] = []
    for tranche in evidence_tranche_rows:
        if tranche.get("outcome_series_id") != "TDSP":
            continue
        shock_id = tranche.get("shock_source_id", "")
        rows.append(
            {
                "policy_path_blocker_id": (
                    "tdsp_policy_path_normalization_blocker::"
                    + tranche.get("evidence_tranche_id", "")
                ),
                "source_evidence_tranche_id": tranche.get("evidence_tranche_id", ""),
                "shock_source_id": shock_id,
                "shock_units": tranche.get("shock_units", ""),
                "tdsp_mechanical_outcome_change_per_100bp": tranche.get(
                    "mechanical_outcome_change_per_100bp", ""
                ),
                "tdsp_mechanical_unit_status": tranche.get(
                    "mechanical_100bp_unit_status", ""
                ),
                **blocked_policy_path_normalization_fields(),
                "source_status": "tdsp_policy_path_normalization_blocked",
                **tdsp_mapping_false_fields(
                    source_ids=[shock_id, "TDSP"],
                    artifacts=(
                        "ratewall_tdsp_policy_path_normalization_blocker.csv;"
                        "ratewall_conventional_drag_evidence_tranche.csv"
                    ),
                    snapshot_map=snapshot_map,
                    evidence_status=(
                        "tdsp_policy_path_100bp_year_normalization_blocked"
                    ),
                    claim_boundary=(
                        "tdsp_policy_path_normalization_not_prior_narrowing"
                    ),
                ),
            }
        )
    return rows


def tdsp_current_demand_admission_audit_rows(
    *,
    source_review_rows: list[dict[str, str]],
    unit_conversion_rows: list[dict[str, str]],
    diagnostic_mapping_rows: list[dict[str, str]],
    policy_path_blocker_rows: list[dict[str, str]],
    source_backing_ledger_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    def ledger_matches(artifact: str, key: str) -> list[dict[str, str]]:
        return [
            row
            for row in source_backing_ledger_rows
            if row.get("artifact_or_surface") == artifact
            and row.get("upstream_row_key") == key
        ]

    def unique_join(values: Iterable[str]) -> str:
        return ";".join(sorted({str(value) for value in values if str(value)}))

    specs: list[tuple[str, str, str, dict[str, str]]] = []
    specs.extend(
        (
            "ratewall_tdsp_current_demand_source_review.csv",
            row["source_review_id"],
            row.get("source_admission_status", ""),
            row,
        )
        for row in source_review_rows
    )
    specs.extend(
        (
            "ratewall_tdsp_current_demand_unit_conversion.csv",
            row["unit_conversion_id"],
            row.get("mechanical_conversion_status", ""),
            row,
        )
        for row in unit_conversion_rows
    )
    specs.extend(
        (
            "ratewall_tdsp_current_demand_diagnostic_mapping.csv",
            row["diagnostic_mapping_id"],
            row.get("estimate_status", ""),
            row,
        )
        for row in diagnostic_mapping_rows
    )
    specs.extend(
        (
            "ratewall_tdsp_policy_path_normalization_blocker.csv",
            row["policy_path_blocker_id"],
            row.get("policy_path_100bp_year_normalization_status", ""),
            row,
        )
        for row in policy_path_blocker_rows
    )

    rows: list[dict[str, str]] = []
    for artifact, key, status, row in specs:
        matches = ledger_matches(artifact, key)
        rows.append(
            {
                "admission_audit_id": (
                    "tdsp_current_demand_admission_audit::"
                    + artifact.removesuffix(".csv")
                    + "::"
                    + key
                ),
                "audited_surface": artifact,
                "audited_row_key": key,
                "source_backing_ledger_gate_status": (
                    "blocked_source_backing_ledger_present_but_diagnostic_only"
                    if matches
                    else "blocked_missing_source_backing_ledger_row"
                ),
                "source_backing_ledger_row_count": str(len(matches)),
                "source_backing_ledger_classes": unique_join(
                    item.get("source_backing_class", "") for item in matches
                ),
                "source_backing_ledger_allowed_use": unique_join(
                    item.get("allowed_use", "") for item in matches
                ),
                "mapping_estimate_status": status,
                "unit_conversion_status": row.get(
                    "mechanical_conversion_status",
                    row.get("outcome_transform", ""),
                ),
                "policy_path_100bp_year_normalization_status": row.get(
                    "policy_path_100bp_year_normalization_status",
                    "blocked_no_reviewed_policy_path_vector_or_duration_scalar",
                ),
                "conversion_admission_status": (
                    "blocked_no_runtime_or_denominator_admission"
                ),
                "source_status": (
                    "tdsp_current_demand_admission_audit_blocked_fail_closed"
                ),
                "exact_blocker": (
                    "The audited TDSP/current-demand row is source-ledgered as "
                    "diagnostic or blocked only and lacks at least one required "
                    "conversion, policy-path, uncertainty, replication, or "
                    "robustness gate; it cannot affect runtime mechanics."
                ),
                "evidence_needed_before_prior_narrowing": (
                    "Every audited row must have source-backed mapping inputs, "
                    "GDP-share conversion, 100bp-year normalization, uncertainty, "
                    "replication, robustness, and a promotion-gate pass."
                ),
                "evidence_needed_before_promotion": (
                    "No TDSP/current-demand row may enter the main ratio, "
                    "Evidence Mode, canonical ratio, pricing, TDC/QRA runtime, "
                    "or forbidden claim surfaces unless all gates pass."
                ),
                "next_backend_action": (
                    "resolve_missing_pce_dpi_policy_path_and_promotion_grade_"
                    "mapping_evidence_before_rebuilding_admission"
                ),
                **tdsp_mapping_false_fields(
                    source_ids=[
                        part
                        for part in row.get(
                            "source_specific_series_or_table_ids", ""
                        ).split(";")
                        if part
                    ],
                    artifacts=(
                        "ratewall_tdsp_current_demand_admission_audit.csv;"
                        "ratewall_assumption_source_backing_ledger.csv"
                    ),
                    snapshot_map={},
                    evidence_status=(
                        "tdsp_current_demand_admission_audit_fail_closed"
                    ),
                    claim_boundary=(
                        "tdsp_current_demand_admission_audit_not_prior_"
                        "narrowing_or_promotion"
                    ),
                ),
            }
        )
    return rows


def tdsp_mapping_false_fields(
    *,
    source_ids: Iterable[str],
    artifacts: str,
    snapshot_map: dict[str, SourceSnapshot],
    evidence_status: str,
    claim_boundary: str,
) -> dict[str, str]:
    source_id_list = list(source_ids)
    return {
        "candidate_gdp_share_drag_per_100bp_year": "",
        "demand_drag_conversion_candidate_available": "false",
        "denominator_prior_update_allowed": "false",
        "empirical_threshold_claim_enabled": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "canonical_ratio_entry": "false",
        "prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_offset_ratio_changed_this_tranche": "false",
        **_source_specific_evidence_fields(
            channel_component="tdsp_current_demand_mapping",
            source_ids=source_id_list,
            artifacts=artifacts,
            snapshot_map=snapshot_map,
            evidence_status=evidence_status,
        ),
        "source_snapshot_kind_summary": _source_kind_summary(
            snapshot_map, source_id_list
        ),
        "claim_boundary": claim_boundary,
        **_disabled_claim_switches(),
    }


def _source_snapshot_map(snapshots: list[SourceSnapshot]) -> dict[str, SourceSnapshot]:
    return {snapshot.metadata.series_id: snapshot for snapshot in snapshots}


def _blocked_payment_candidate(
    status: str,
    exact_blocker: str,
) -> TdspPaymentDollarsCandidate:
    return TdspPaymentDollarsCandidate(
        status=status,
        date="",
        tdsp_percent_of_dpi=None,
        dspi_bil_saar=None,
        payment_bil_saar=None,
        exact_blocker=exact_blocker,
    )


def _blocked_gdp_share_candidate(
    status: str,
    exact_blocker: str,
    *,
    date: str = "",
    payment_bil_saar: Decimal | None = None,
    payment_change_bil_saar: Decimal | None = None,
    response_id: str = "",
    response_admission_class: str = "",
) -> TdspCurrentDemandGdpShareCandidate:
    return TdspCurrentDemandGdpShareCandidate(
        status=status,
        date=date,
        payment_bil_saar=payment_bil_saar,
        payment_change_bil_saar=payment_change_bil_saar,
        response_id=response_id,
        response_admission_class=response_admission_class,
        marginal_current_demand_response=None,
        current_demand_bil_saar=None,
        nominal_gdp_bil_saar=None,
        current_demand_gdp_share=None,
        exact_blocker=exact_blocker,
    )


def _numeric_records_by_date(snapshot: SourceSnapshot) -> dict[str, Decimal]:
    records: dict[str, Decimal] = {}
    for record in snapshot.records:
        date_key = str(record.get("date", ""))
        if not date_key:
            continue
        value = record.get("value")
        try:
            records[date_key] = _decimal(value)
        except ValueError:
            continue
    return records


def _decimal(value: object) -> Decimal:
    if value in {None, "", "."}:
        raise ValueError(f"Invalid numeric TDSP current-demand value: {value!r}")
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(
            f"Invalid numeric TDSP current-demand value: {value!r}"
        ) from exc
    if not decimal_value.is_finite():
        raise ValueError(f"Invalid finite TDSP current-demand value: {value!r}")
    return decimal_value


def _nonnegative_decimal(value: object) -> Decimal:
    decimal_value = _decimal(value)
    if decimal_value < Decimal("0"):
        raise ValueError(
            "TDSP marginal current-demand response magnitude must be nonnegative."
        )
    return decimal_value


def _format_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _source_specific_evidence_fields(
    *,
    channel_component: str,
    source_ids: Iterable[str],
    artifacts: str,
    snapshot_map: dict[str, SourceSnapshot],
    evidence_status: str,
) -> dict[str, str]:
    ids = ";".join(source_ids)
    status = evidence_status
    if channel_component:
        status = f"{status};component={channel_component}" if status else channel_component
    return {
        "source_specific_artifacts": artifacts,
        "source_specific_series_or_table_ids": ids,
        "source_specific_urls_or_docs": _source_urls_for_ids(
            snapshot_map, ids.split(";")
        )
        if ids
        else "",
        "source_specific_citation_or_design_handles": _CONVENTIONAL_DRAG_EVIDENCE[
            "handles"
        ],
        "source_specific_evidence_status": status
        or _CONVENTIONAL_DRAG_EVIDENCE["status"],
    }


def _source_urls_for_ids(
    snapshot_map: dict[str, SourceSnapshot] | None,
    source_ids: Iterable[str],
) -> str:
    if snapshot_map is None:
        return ""
    urls = []
    for source_id in source_ids:
        snapshot = snapshot_map.get(source_id)
        if snapshot and snapshot.metadata.source_url:
            urls.append(f"{source_id}:{snapshot.metadata.source_url}")
        elif source_id:
            urls.append(f"{source_id}:not_in_current_snapshot")
    return ";".join(urls)


def _source_kind_summary(
    snapshot_map: dict[str, SourceSnapshot],
    source_ids: list[str],
) -> str:
    parts = []
    for series_id in source_ids:
        snapshot = snapshot_map.get(series_id)
        if snapshot is None:
            parts.append(f"{series_id}:missing")
        else:
            parts.append(f"{series_id}:{snapshot.metadata.snapshot_kind}")
    return ";".join(parts)


def _disabled_claim_switches() -> dict[str, str]:
    return {
        "empirical_claim_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "welfare_claim_enabled": "false",
        "tax_output_enabled": "false",
        "mpc_output_enabled": "false",
        "holder_allocation_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "raw_rate_shock_enabled": "false",
        "causal_financialization_claim_enabled": "false",
    }
