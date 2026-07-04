from decimal import Decimal

from ratewall.databook.policy_path_normalization import (
    POLICY_PATH_BPS_EXPOSURE_FORMULA,
    POLICY_PATH_EFFECT_NORMALIZATION_FORMULA,
)
from ratewall.databook.tdsp_current_demand import (
    TDSP_CORE_RESPONSE_ADMISSION_CLASS,
    TDSP_CORE_RESPONSE_SOURCE_FAMILY,
    TDSP_CURRENT_DEMAND_GDP_SHARE_AVAILABLE_STATUS,
    TDSP_PAYMENT_DOLLARS_AVAILABLE_STATUS,
    TDSP_RESPONSE_SIGN_CONVENTION,
    TDSP_RESPONSE_UNITS,
    TdspMarginalCurrentDemandResponse,
    tdsp_current_demand_gdp_share_candidate,
    tdsp_current_demand_admission_audit_rows,
    tdsp_current_demand_unit_conversion_rows,
    tdsp_payment_dollars_candidate,
    tdsp_policy_path_normalization_blocker_rows,
)
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot


def _snapshot(
    series_id: str,
    *,
    kind: str = "fixture",
    records: list[dict[str, str]] | None = None,
) -> SourceSnapshot:
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id="fixture",
            series_id=series_id,
            source_url=f"fixture://{series_id}",
            units="level",
            frequency="quarterly",
            transform="level",
            retrieved_at="2026-06-17T00:00:00Z",
            source_release_at="2026-06-17",
            snapshot_kind=kind,
        ),
        records=records
        or [
            {"date": "2020-01-01", "value": "1"},
            {"date": "2021-01-01", "value": "2"},
        ],
    )


def _tdsp_response(
    *,
    response_id: str = "test_core_response",
    admission_class: str = TDSP_CORE_RESPONSE_ADMISSION_CLASS,
    source_family: str = TDSP_CORE_RESPONSE_SOURCE_FAMILY,
    central: str | None = "0.25",
    units: str = TDSP_RESPONSE_UNITS,
    sign_convention: str = TDSP_RESPONSE_SIGN_CONVENTION,
    admitted_for_core: bool = True,
) -> TdspMarginalCurrentDemandResponse:
    return TdspMarginalCurrentDemandResponse(
        response_id=response_id,
        admission_class=admission_class,
        source_title="Fixture source",
        source_url_or_citation="fixture://tdsp-response",
        source_family=source_family,
        payment_object="tdsp_required_payment_change",
        demand_object="current_demand_dollars",
        timing_convention="same_quarter_saar",
        units=units,
        sign_convention=sign_convention,
        central=Decimal(central) if central is not None else None,
        lower=None,
        upper=None,
        uncertainty_basis="fixture",
        admitted_for_core=admitted_for_core,
    )


def test_tdsp_current_demand_unit_conversion_rows_fail_closed_without_outputs() -> None:
    rows = tdsp_current_demand_unit_conversion_rows(
        snapshots=[
            _snapshot("TDSP"),
            _snapshot("GDP"),
            _snapshot("fed_brw_monetary_policy_shocks"),
        ]
    )

    by_role = {row["conversion_input_role"]: row for row in rows}
    assert set(by_role) == {
        "tdsp_ratio_to_payment_dollars",
        "payment_dollars_to_current_demand",
        "current_demand_dollars_to_gdp_share",
        "tdsp_diagnostic_points_to_gdp_growth",
        "scalar_shock_to_100bp_year_policy_path",
    }
    assert by_role["payment_dollars_to_current_demand"][
        "mechanical_conversion_status"
    ] == "blocked_missing_marginal_consumption_response_bridge"
    assert by_role["current_demand_dollars_to_gdp_share"][
        "mechanical_conversion_status"
    ] == "blocked_missing_current_demand_dollars_and_policy_path_normalization"
    assert by_role["scalar_shock_to_100bp_year_policy_path"][
        "mechanical_conversion_status"
    ] == "blocked_no_reviewed_policy_path_exposure_vector"
    assert by_role["scalar_shock_to_100bp_year_policy_path"][
        "conversion_formula_candidate"
    ] == POLICY_PATH_BPS_EXPOSURE_FORMULA
    assert by_role["payment_dollars_to_current_demand"][
        "source_snapshot_kind_summary"
    ] == "TDSP:fixture;PCEC:missing;PCECC96:missing"

    for row in rows:
        assert row["demand_drag_conversion_candidate_available"] == "false"
        assert row["denominator_prior_update_allowed"] == "false"
        assert row["enters_main_ratio"] == "false"
        assert row["canonical_ratio_entry"] == "false"
        assert row["raw_rate_shock_enabled"] == "false"


def test_tdsp_payment_dollars_candidate_uses_exact_tdsp_dspi_date() -> None:
    candidate = tdsp_payment_dollars_candidate(
        snapshots=[
            _snapshot(
                "TDSP",
                records=[
                    {"date": "2023-10-01", "value": "9"},
                    {"date": "2024-01-01", "value": "10"},
                ],
            ),
            _snapshot(
                "DSPI",
                records=[
                    {"date": "2023-12-01", "value": "19000"},
                    {"date": "2024-01-01", "value": "20000"},
                ],
            ),
        ]
    )

    assert candidate.status == TDSP_PAYMENT_DOLLARS_AVAILABLE_STATUS
    assert candidate.date == "2024-01-01"
    assert candidate.tdsp_percent_of_dpi == Decimal("10")
    assert candidate.dspi_bil_saar == Decimal("20000")
    assert candidate.payment_bil_saar == Decimal("2000")


def test_tdsp_payment_dollars_candidate_blocks_without_exact_shared_date() -> None:
    candidate = tdsp_payment_dollars_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-02-01", "value": "20000"}]),
        ]
    )

    assert candidate.status == "blocked_no_common_tdsp_dspi_date"
    assert candidate.payment_bil_saar is None


def test_tdsp_current_demand_gdp_share_candidate_requires_admitted_response() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        marginal_current_demand_response=Decimal("0.25"),
        response_admitted=False,
    )

    assert candidate.status == "blocked_no_admitted_marginal_current_demand_response"
    assert candidate.payment_bil_saar == Decimal("2000")
    assert candidate.current_demand_gdp_share is None


def test_tdsp_current_demand_gdp_share_candidate_rejects_bare_scalar() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        marginal_current_demand_response=Decimal("0.25"),
        response_admitted=True,
    )

    assert candidate.status == (
        "blocked_unstructured_marginal_current_demand_response_not_admitted"
    )
    assert candidate.payment_bil_saar == Decimal("2000")
    assert candidate.current_demand_bil_saar is None
    assert candidate.current_demand_gdp_share is None


def test_tdsp_current_demand_gdp_share_candidate_calculates_delta_signed_response() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        payment_change_bil_saar=Decimal("100"),
        marginal_current_demand_response=_tdsp_response(central="0.25"),
        response_admitted=True,
    )

    assert candidate.status == TDSP_CURRENT_DEMAND_GDP_SHARE_AVAILABLE_STATUS
    assert candidate.payment_bil_saar == Decimal("2000")
    assert candidate.payment_change_bil_saar == Decimal("100")
    assert candidate.response_id == "test_core_response"
    assert candidate.response_admission_class == TDSP_CORE_RESPONSE_ADMISSION_CLASS
    assert candidate.marginal_current_demand_response == Decimal("-0.25")
    assert candidate.current_demand_bil_saar == Decimal("-25.00")
    assert candidate.nominal_gdp_bil_saar == Decimal("30000")
    assert candidate.current_demand_gdp_share == Decimal("-25.00") / Decimal("30000")


def test_tdsp_current_demand_gdp_share_candidate_requires_payment_change() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        marginal_current_demand_response=_tdsp_response(central="0.25"),
        response_admitted=True,
    )

    assert candidate.status == "blocked_no_tdsp_payment_change_input"
    assert candidate.payment_bil_saar == Decimal("2000")
    assert candidate.response_id == "test_core_response"
    assert candidate.current_demand_bil_saar is None


def test_tdsp_sensitivity_response_cannot_enter_core_candidate() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        payment_change_bil_saar=Decimal("100"),
        marginal_current_demand_response=_tdsp_response(
            response_id="sensitivity_fixture",
            admission_class="sensitivity_only",
            admitted_for_core=True,
        ),
        response_admitted=True,
    )

    assert candidate.status == "blocked_marginal_current_demand_response_not_core_admitted"
    assert candidate.response_id == "sensitivity_fixture"
    assert candidate.response_admission_class == "sensitivity_only"
    assert candidate.current_demand_bil_saar is None


def test_tdsp_response_admitted_for_core_flag_is_required() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        payment_change_bil_saar=Decimal("100"),
        marginal_current_demand_response=_tdsp_response(admitted_for_core=False),
        response_admitted=True,
    )

    assert candidate.status == "blocked_marginal_current_demand_response_not_core_admitted"
    assert candidate.response_admission_class == TDSP_CORE_RESPONSE_ADMISSION_CLASS
    assert candidate.current_demand_bil_saar is None


def test_tdsp_response_source_family_mismatch_blocks() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        payment_change_bil_saar=Decimal("100"),
        marginal_current_demand_response=_tdsp_response(
            source_family="generic_mpc_proxy"
        ),
        response_admitted=True,
    )

    assert candidate.status == (
        "blocked_marginal_current_demand_response_source_family_mismatch"
    )
    assert candidate.response_admission_class == TDSP_CORE_RESPONSE_ADMISSION_CLASS
    assert candidate.current_demand_bil_saar is None


def test_tdsp_response_unit_contract_mismatch_blocks() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        payment_change_bil_saar=Decimal("100"),
        marginal_current_demand_response=_tdsp_response(units="generic_mpc"),
        response_admitted=True,
    )

    assert candidate.status == (
        "blocked_marginal_current_demand_response_unit_contract_mismatch"
    )
    assert candidate.current_demand_bil_saar is None


def test_tdsp_response_sign_contract_mismatch_blocks() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        payment_change_bil_saar=Decimal("100"),
        marginal_current_demand_response=_tdsp_response(
            sign_convention="positive_payment_change_positive_demand"
        ),
        response_admitted=True,
    )

    assert candidate.status == (
        "blocked_marginal_current_demand_response_unit_contract_mismatch"
    )
    assert candidate.current_demand_bil_saar is None


def test_tdsp_response_missing_or_negative_central_blocks() -> None:
    missing = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        payment_change_bil_saar=Decimal("100"),
        marginal_current_demand_response=_tdsp_response(central=None),
        response_admitted=True,
    )
    negative = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        payment_change_bil_saar=Decimal("100"),
        marginal_current_demand_response=_tdsp_response(central="-0.25"),
        response_admitted=True,
    )

    assert missing.status == "blocked_missing_core_marginal_current_demand_response_central"
    assert negative.status == "blocked_invalid_core_marginal_current_demand_response"
    assert missing.current_demand_bil_saar is None
    assert negative.current_demand_bil_saar is None


def test_tdsp_invalid_payment_change_blocks() -> None:
    candidate = tdsp_current_demand_gdp_share_candidate(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
            _snapshot("GDP", records=[{"date": "2024-01-01", "value": "30000"}]),
        ],
        payment_change_bil_saar="not-a-number",
        marginal_current_demand_response=_tdsp_response(),
        response_admitted=True,
    )

    assert candidate.status == "blocked_invalid_tdsp_payment_change_input"
    assert candidate.current_demand_bil_saar is None


def test_tdsp_unit_conversion_row_populates_payment_candidate_but_not_promotion() -> None:
    rows = tdsp_current_demand_unit_conversion_rows(
        snapshots=[
            _snapshot("TDSP", records=[{"date": "2024-01-01", "value": "10"}]),
            _snapshot("DSPI", records=[{"date": "2024-01-01", "value": "20000"}]),
        ]
    )
    by_role = {row["conversion_input_role"]: row for row in rows}
    payment_row = by_role["tdsp_ratio_to_payment_dollars"]

    assert payment_row["mechanical_conversion_status"] == (
        TDSP_PAYMENT_DOLLARS_AVAILABLE_STATUS
    )
    assert payment_row["source_backing_requirement_status"] == (
        "source_backed_tdsp_dspi_inputs_available"
    )
    assert payment_row["conversion_output_value"] == "2000"
    assert payment_row["candidate_gdp_share_drag_per_100bp_year"] == ""
    assert payment_row["demand_drag_conversion_candidate_available"] == "false"
    assert payment_row["denominator_prior_update_allowed"] == "false"
    assert payment_row["enters_main_ratio"] == "false"
    assert payment_row["canonical_ratio_entry"] == "false"


def test_tdsp_policy_path_blocker_filters_to_tdsp_and_keeps_switches_off() -> None:
    rows = tdsp_policy_path_normalization_blocker_rows(
        evidence_tranche_rows=[
            {
                "evidence_tranche_id": "tranche::tdsp",
                "outcome_series_id": "TDSP",
                "shock_source_id": "fed_brw_monetary_policy_shocks",
                "shock_units": "basis_points",
                "mechanical_outcome_change_per_100bp": "0.2",
                "mechanical_100bp_unit_status": "diagnostic_only",
            },
            {
                "evidence_tranche_id": "tranche::gdp",
                "outcome_series_id": "GDP",
                "shock_source_id": "fed_brw_monetary_policy_shocks",
            },
        ],
        snapshots=[
            _snapshot("TDSP"),
            _snapshot("fed_brw_monetary_policy_shocks"),
        ],
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["source_evidence_tranche_id"] == "tranche::tdsp"
    assert row["policy_path_100bp_year_normalization_status"] == (
        "blocked_no_reviewed_policy_path_vector_or_duration_scalar"
    )
    assert row["policy_path_source_status"] == (
        "shock_source_contains_scalar_event_or_monthly_shock_only"
    )
    assert row["normalization_output_value"] == ""
    assert row["normalization_formula_candidate"] == (
        POLICY_PATH_EFFECT_NORMALIZATION_FORMULA
    )
    assert row["candidate_gdp_share_drag_per_100bp_year"] == ""
    assert row["enters_main_ratio"] == "false"
    assert row["source_snapshot_kind_summary"] == (
        "fed_brw_monetary_policy_shocks:fixture;TDSP:fixture"
    )


def test_tdsp_admission_audit_blocks_runtime_use_without_building_tables() -> None:
    snapshots = [
        _snapshot("TDSP"),
        _snapshot("GDP"),
        _snapshot("fed_brw_monetary_policy_shocks"),
    ]
    unit_rows = tdsp_current_demand_unit_conversion_rows(snapshots=snapshots)
    policy_rows = tdsp_policy_path_normalization_blocker_rows(
        evidence_tranche_rows=[
            {
                "evidence_tranche_id": "tranche::tdsp",
                "outcome_series_id": "TDSP",
                "shock_source_id": "fed_brw_monetary_policy_shocks",
                "shock_units": "basis_points",
            }
        ],
        snapshots=snapshots,
    )
    diagnostic_rows = [
        {
            "diagnostic_mapping_id": (
                "tdsp_current_demand_diagnostic_mapping::TDSP::GDP::3y"
            ),
            "estimate_status": (
                "diagnostic_tdsp_to_current_demand_mapping_estimate_available_fail_closed"
            ),
            "outcome_transform": "annualized_percent_change",
            "policy_path_100bp_year_normalization_status": (
                "blocked_no_reviewed_policy_path_vector_or_duration_scalar"
            ),
            "source_specific_series_or_table_ids": "TDSP;GDP",
        }
    ]
    source_review_rows = [
        {
            "source_review_id": (
                "tdsp_current_demand_source_review::tdsp_financial_outcome_input"
            ),
            "source_admission_status": "source_admitted_diagnostic_input_only",
            "source_specific_series_or_table_ids": "TDSP",
        }
    ]
    source_backing_rows = [
        {
            "artifact_or_surface": "ratewall_tdsp_current_demand_unit_conversion.csv",
            "upstream_row_key": unit_rows[0]["unit_conversion_id"],
            "source_backing_class": "diagnostic_only",
            "allowed_use": "blocked_current_demand_mapping",
        }
    ]

    rows = tdsp_current_demand_admission_audit_rows(
        source_review_rows=source_review_rows,
        unit_conversion_rows=unit_rows,
        diagnostic_mapping_rows=diagnostic_rows,
        policy_path_blocker_rows=policy_rows,
        source_backing_ledger_rows=source_backing_rows,
    )

    assert len(rows) == 8
    assert {
        row["audited_surface"] for row in rows
    } == {
        "ratewall_tdsp_current_demand_source_review.csv",
        "ratewall_tdsp_current_demand_unit_conversion.csv",
        "ratewall_tdsp_current_demand_diagnostic_mapping.csv",
        "ratewall_tdsp_policy_path_normalization_blocker.csv",
    }
    assert all(
        row["conversion_admission_status"] == "blocked_no_runtime_or_denominator_admission"
        for row in rows
    )
    assert all(row["source_status"] == "tdsp_current_demand_admission_audit_blocked_fail_closed" for row in rows)
    assert all(row["denominator_prior_update_allowed"] == "false" for row in rows)
    assert all(row["enters_main_ratio"] == "false" for row in rows)
    assert all(row["evidence_mode_enabled"] == "false" for row in rows)

    ledgered_unit = next(
        row for row in rows if row["audited_row_key"] == unit_rows[0]["unit_conversion_id"]
    )
    assert ledgered_unit["source_backing_ledger_gate_status"] == (
        "blocked_source_backing_ledger_present_but_diagnostic_only"
    )
    assert ledgered_unit["source_backing_ledger_row_count"] == "1"
