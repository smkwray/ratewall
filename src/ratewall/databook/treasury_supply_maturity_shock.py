"""Fail-closed Treasury supply/maturity shock objects for denominator research."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile


PHILLOT_OPENICPSR_PACKAGE_ZIP = Path(
    "data/raw/treasury_supply_maturity_shock_sources/openicpsr_192741_v1/192741-V1.zip"
)
CURRENT_DEMAND_GDP_SHARE_DIR = Path("data/raw/current_demand_gdp_share")
PHILLOT_REQUIRED_PACKAGE_FILES = (
    "README.pdf",
    "data/1_Financial.dta",
    "data/2_Treasury_data.dta",
    "data/3_Treasury_dummies.dta",
    "data/4_Treasury_supply_shocks.dta",
    "data/4_bis_Placebo_shocks.dta",
    "data/5_News_FOMC.dta",
    "do/master.do",
    "do/data_prep.do",
    "do/compute.do",
    "raw_public/TreasuryDirect/announcement_timestamps.dta",
)
PHILLOT_SHOCK_COLUMNS = (
    "n_2y_m5_p29",
    "n_5y_m5_p29",
    "n_10y_m5_p29",
    "n_30y_m5_p29",
)
PHILLOT_ANALYSIS_SAMPLE_START = "1998-10-28"
PHILLOT_ANALYSIS_SAMPLE_END = "2020-01-31"


TREASURY_SUPPLY_MATURITY_SHOCK_SOURCE_INVENTORY_FIELDS = [
    "source_id",
    "source_package_id",
    "source_package_doi",
    "source_title",
    "source_url",
    "source_publisher",
    "publication_year",
    "source_class",
    "source_access_status",
    "download_auth_required",
    "verified_machine_readable_files",
    "shock_series_schema_verified",
    "event_grain_verified",
    "raw_market_data_access_class",
    "source_request_status",
    "native_unit",
    "shock_family_supported",
    "has_event_window_timestamps",
    "has_5y_10y_30y_bridge",
    "has_effective_curve_bridge",
    "macro_outcome_available",
    "role_in_ratewall",
    "admission_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

TREASURY_SUPPLY_MATURITY_SHOCK_PACKAGE_AUDIT_FIELDS = [
    "source_id",
    "source_package_id",
    "source_package_doi",
    "package_path",
    "package_present",
    "package_read_status",
    "required_file_count",
    "required_file_present_count",
    "required_files_missing",
    "shock_file_read_status",
    "shock_row_count",
    "shock_date_min",
    "shock_date_max",
    "shock_columns_present",
    "shock_columns_missing",
    "shock_nonmissing_observation_count_min",
    "shock_nonmissing_observation_count_max",
    "shock_native_unit",
    "shock_sign_convention_status",
    "event_window",
    "event_grain_status",
    "announcement_timestamp_read_status",
    "announcement_timestamp_count",
    "announcement_timestamp_date_min",
    "announcement_timestamp_date_max",
    "tenor_2y_5y_10y_30y_status",
    "yield_equivalent_bp_conversion_status",
    "effective_curve_bridge_status",
    "shock_family_separation_status",
    "source_admission_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

PHILLOT_TREASURY_AUCTION_INSTRUMENT_FIELDS = [
    "instrument_object_id",
    "source_id",
    "source_package_id",
    "source_package_doi",
    "event_date",
    "announcement_timestamp_status",
    "announcement_hour",
    "announcement_minute",
    "event_window",
    "normalization_sample_start",
    "normalization_sample_end",
    "in_analysis_sample",
    "n_2y_m5_p29",
    "n_5y_m5_p29",
    "n_10y_m5_p29",
    "n_30y_m5_p29",
    "shock_unit",
    "native_unit",
    "sign_convention",
    "raw_event_window_return_available",
    "yield_bp_equivalent_available",
    "effective_curve_100bp_year_available",
    "shock_family_separation_status",
    "path_object_admission_status",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

PHILLOT_DAILY_YIELD_BRIDGE_FIELDS = [
    "bridge_row_id",
    "source_id",
    "source_package_id",
    "source_package_doi",
    "tenor",
    "shock_column",
    "daily_yield_column",
    "sample_start",
    "sample_end",
    "event_count",
    "shock_unit",
    "daily_yield_change_unit",
    "slope_bp_per_normalized_shock",
    "standard_error",
    "ci95_low",
    "ci95_high",
    "r_squared",
    "intercept_bp",
    "yield_change_mean_bp",
    "yield_change_sd_bp",
    "shock_mean",
    "shock_sd",
    "same_source_package_status",
    "event_window_alignment_status",
    "yield_equivalent_bp_conversion_status",
    "effective_curve_bridge_status",
    "admission_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

TREASURY_SUPPLY_MATURITY_SHOCK_PATH_OBJECT_FIELDS = [
    "treasury_supply_maturity_shock_path_object_candidate_id",
    "shock_object_id",
    "shock_object_kind",
    "shock_family",
    "source_id",
    "source_event_id",
    "event_date",
    "quarter",
    "event_window",
    "source_vintage",
    "source_publisher",
    "source_shock_unit",
    "source_shock_value",
    "curve_5y_bp",
    "curve_10y_bp",
    "curve_30y_bp",
    "effective_curve_overlay_bp",
    "horizon_weight_years",
    "path_bps_year",
    "normalized_100bp_year_value",
    "source_acquisition_status",
    "event_window_timestamp_status",
    "independent_replication_status",
    "shock_family_declared_status",
    "mixed_shock_separation_status",
    "yield_equivalent_bp_conversion_status",
    "effective_curve_bridge_status",
    "normalization_status",
    "first_stage_relevance_status",
    "h4_fspdp_estimate_status",
    "h4_fspdp_beta_per_100bp_year",
    "h4_fspdp_ci95_low",
    "h4_fspdp_ci95_high",
    "h4_ci_status",
    "gdp_robustness_status",
    "sample_robustness_status",
    "placebo_leads_pretrend_status",
    "scenario_overlay_shape_bridge_status",
    "admission_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

TREASURY_SUPPLY_MATURITY_SHOCK_COEFFICIENT_ADMISSION_FIELDS = [
    "treasury_supply_maturity_coefficient_decision_id",
    "target_outcome_id",
    "primary_horizon_q",
    "required_shock_object_kind",
    "path_object_candidate_count",
    "path_object_pass_count",
    "primary_estimate_pass_count",
    "admitted_denominator_response_coefficient",
    "admitted_denominator_response_coefficient_unit",
    "coefficient_admission_status",
    "exact_blocker",
    "next_model_requirement",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

TREASURY_SUPPLY_MATURITY_H4_FSPDP_RESPONSE_FIELDS = [
    "treasury_supply_maturity_h4_fspdp_response_id",
    "target_outcome_id",
    "horizon_q",
    "event_count",
    "eligible_event_count",
    "usable_observation_count",
    "sample_start_q",
    "sample_end_q",
    "beta_per_100bp_year",
    "standard_error",
    "ci95_low",
    "ci95_high",
    "placebo_beta_per_100bp_year",
    "placebo_ci95_low",
    "placebo_ci95_high",
    "nominal_share_beta_per_100bp_year",
    "outcome_formula",
    "exposure_formula",
    "source_panel_status",
    "path_object_status",
    "h4_fspdp_estimate_status",
    "h4_ci_status",
    "gdp_robustness_status",
    "sample_robustness_status",
    "placebo_leads_pretrend_status",
    "admission_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

FSPDP_GDP_PANEL_FIELDS = [
    "quarter",
    "nominal_fspdp",
    "real_fspdp",
    "nominal_gdp",
    "real_gdp",
]

REQUIRED_SHOCK_FAMILIES = {
    "treasury_debt_expansion_shock",
    "treasury_maturity_extension_shock",
}

ADMISSION_PASS_STATUSES = {
    "source_acquisition_status": "pass",
    "event_window_timestamp_status": "pass",
    "independent_replication_status": "pass",
    "shock_family_declared_status": "pass",
    "mixed_shock_separation_status": "pass",
    "yield_equivalent_bp_conversion_status": "pass",
    "effective_curve_bridge_status": "pass",
    "normalization_status": "pass",
    "first_stage_relevance_status": "pass",
    "h4_fspdp_estimate_status": "pass",
    "h4_ci_status": "pass",
    "gdp_robustness_status": "pass",
    "sample_robustness_status": "pass",
    "placebo_leads_pretrend_status": "pass",
    "scenario_overlay_shape_bridge_status": "pass",
}

BLOCKED_USE = (
    "canonical_headline_promotion;denominator_recalibration;"
    "default_runtime_anchor;evidence_mode_claim;denominator_prior_update;"
    "path_ratio_denominator_replacement;release_headline_claim;"
    "canonical_d_update"
)


def treasury_supply_maturity_shock_source_inventory_rows() -> list[dict[str, str]]:
    """Return the reviewed source inventory for the next shock-object tranche."""

    return [
        _source_row(
            source_id="phillot_2025_aea_treasury_auction_supply_shocks",
            source_package_id="openicpsr_192741_v1",
            source_package_doi="10.3886/E192741V1",
            source_title=(
                "US Treasury Auctions: A High-Frequency Identification of Supply Shocks"
            ),
            source_url="https://www.aeaweb.org/articles?id=10.1257%2Fmac.20210243",
            source_publisher="American Economic Association",
            publication_year="2025",
            source_class="high_frequency_treasury_auction_announcement_supply_shock",
            source_access_status=(
                "owner_download_acquired_local_package_schema_audited_not_path_ready"
            ),
            download_auth_required="yes_openicpsr_login_session_required",
            verified_machine_readable_files=(
                "data/4_Treasury_supply_shocks.dta;"
                "data/4_bis_Placebo_shocks.dta;"
                "raw_public/TreasuryDirect/announcement_timestamps.dta"
            ),
            shock_series_schema_verified=(
                "pass_downloaded_schema_contains_2y_5y_10y_30y_normalized_returns"
            ),
            event_grain_verified="pass_daily_event_window_rows_with_missing_non_events",
            raw_market_data_access_class=(
                "derived_working_file_public_raw_intraday_market_data_proprietary"
            ),
            source_request_status="not_needed_for_phillot_working_shock_file",
            native_unit=(
                "normalized_treasury_futures_log_return_m5_p29_not_yield_bp"
            ),
            shock_family_supported="treasury_debt_expansion_shock",
            has_event_window_timestamps="pass_raw_public_announcement_timestamps_present",
            has_5y_10y_30y_bridge="pass_native_5y_10y_30y_normalized_futures_returns",
            has_effective_curve_bridge="blocked_no_yield_equivalent_bp_conversion",
            macro_outcome_available="financial_market_local_projection_outcomes_reported",
            role_in_ratewall="preferred_shock_source_candidate",
            exact_blocker=(
                "Owner download is acquired and the shock schema is readable, but "
                "native shock units are normalized futures log returns rather than "
                "5y/10y/30y yield-equivalent basis points; no 100bp-year effective "
                "curve bridge or h4 FSPDP response is admitted."
            ),
        ),
        _source_row(
            source_id="bi_phillot_zubairy_2026_kc_fed_rwp_26_04",
            source_package_id="",
            source_package_doi="",
            source_title=(
                "Treasury Supply Shocks: Propagation Through Debt Expansion "
                "and Maturity Adjustment"
            ),
            source_url=(
                "https://www.kansascityfed.org/research/research-working-papers/"
                "treasury-supply-shocks-propagation-through-debt-expansion-and-"
                "maturity-adjustment/"
            ),
            source_publisher="Federal Reserve Bank of Kansas City",
            publication_year="2026",
            source_class="high_frequency_treasury_auction_announcement_supply_shock",
            source_access_status=(
                "public_working_paper_no_public_replication_package_identified_2026_06_26"
            ),
            download_auth_required="not_applicable_no_package_identified",
            verified_machine_readable_files="",
            shock_series_schema_verified="blocked_no_public_machine_readable_package",
            event_grain_verified="blocked_no_public_machine_readable_package",
            raw_market_data_access_class="unknown_no_public_package",
            source_request_status="not_requested",
            native_unit="treasury_futures_price_changes_around_auction_announcements",
            shock_family_supported=(
                "treasury_debt_expansion_shock;"
                "treasury_maturity_extension_shock"
            ),
            has_event_window_timestamps="candidate_requires_replication_review",
            has_5y_10y_30y_bridge="candidate_requires_replication_review",
            has_effective_curve_bridge="blocked_not_yet_replicated",
            macro_outcome_available="macro_financial_outcomes_reported",
            role_in_ratewall="preferred_family_separation_candidate",
            exact_blocker=(
                "The paper supports separate debt-expansion and maturity-extension "
                "shock families, but RateWall has not acquired a machine-readable "
                "shock series or effective-curve bridge."
            ),
        ),
        _source_row(
            source_id="treasurydirect_auction_announcements_results",
            source_package_id="",
            source_package_doi="",
            source_title="TreasuryDirect Announcements, Data, and Results",
            source_url="https://www.treasurydirect.gov/auctions/announcements-data-results/",
            source_publisher="U.S. Department of the Treasury",
            publication_year="current",
            source_class="treasury_auction_schedule_and_result_records",
            source_access_status="public_machine_readable_raw_auction_records_verified_not_shock",
            download_auth_required="no",
            verified_machine_readable_files="raw_public/TreasuryDirect/*.dta",
            shock_series_schema_verified="not_applicable_raw_auction_records_not_shock",
            event_grain_verified="pass_auction_event_records_available",
            raw_market_data_access_class="not_market_data",
            source_request_status="not_needed_public_raw_records",
            native_unit="auction_announcement_and_result_records",
            shock_family_supported="not_a_shock_without_high_frequency_market_window",
            has_event_window_timestamps="auction_dates_available_not_hf_windows",
            has_5y_10y_30y_bridge="not_applicable_source_records_only",
            has_effective_curve_bridge="blocked_no_market_price_window",
            macro_outcome_available="none",
            role_in_ratewall="event_calendar_and_issuance_metadata_candidate",
            exact_blocker=(
                "Auction records can support event calendars and issuance metadata, "
                "but cannot become shocks without high-frequency market-price windows."
            ),
        ),
        _source_row(
            source_id="fiscaldata_monthly_statement_public_debt_mspd",
            source_package_id="",
            source_package_doi="",
            source_title="Monthly Statement of the Public Debt",
            source_url="https://fiscaldata.treasury.gov/datasets/monthly-statement-public-debt/",
            source_publisher="U.S. Department of the Treasury FiscalData",
            publication_year="current",
            source_class="treasury_debt_stock_and_maturity_control_records",
            source_access_status="public_source_identified",
            download_auth_required="no",
            verified_machine_readable_files="",
            shock_series_schema_verified="not_applicable_stock_control_only",
            event_grain_verified="not_applicable_monthly_stock_data",
            raw_market_data_access_class="not_market_data",
            source_request_status="not_needed_public_stock_records",
            native_unit="monthly_outstanding_debt_stock_records",
            shock_family_supported="not_a_shock_stock_control_only",
            has_event_window_timestamps="not_applicable_monthly_stock_data",
            has_5y_10y_30y_bridge="not_applicable_stock_control_only",
            has_effective_curve_bridge="blocked_no_high_frequency_shock",
            macro_outcome_available="none",
            role_in_ratewall="state_control_and_stock_validation_candidate",
            exact_blocker=(
                "MSPD is useful for stock controls and validation, not for an "
                "identified high-frequency Treasury supply shock."
            ),
        ),
        _source_row(
            source_id="li_wei_greenwood_vayanos_supply_factor_validation",
            source_package_id="",
            source_package_doi="",
            source_title=(
                "Term-structure supply-factor literature for structural validation"
            ),
            source_url=(
                "https://www.federalreserve.gov/econres/feds/term-structure-"
                "modelling-with-supply-factors-and-the-federal-reserve39s-large-"
                "scale-asset-purchase-programs-201237.htm"
            ),
            source_publisher="Federal Reserve and academic literature",
            publication_year="2012",
            source_class="term_structure_supply_factor_validation_literature",
            source_access_status="public_literature_identified",
            download_auth_required="no",
            verified_machine_readable_files="",
            shock_series_schema_verified="not_applicable_validation_literature_only",
            event_grain_verified="not_applicable_validation_literature_only",
            raw_market_data_access_class="not_market_data",
            source_request_status="not_needed_literature_only",
            native_unit="model_implied_yield_response_to_supply_factors",
            shock_family_supported="structural_validation_only",
            has_event_window_timestamps="no",
            has_5y_10y_30y_bridge="literature_dependent_not_ratewall_ready",
            has_effective_curve_bridge="blocked_not_direct_shock_series",
            macro_outcome_available="none",
            role_in_ratewall="external_plausibility_check_not_coefficient_transport",
            exact_blocker=(
                "Useful for validating that supply factors can move yields, but "
                "not a RateWall shock series or denominator-response coefficient."
            ),
        ),
    ]


def phillot_package_schema_audit_rows(
    package_zip_path: str | Path = PHILLOT_OPENICPSR_PACKAGE_ZIP,
) -> list[dict[str, str]]:
    """Audit the downloaded Phillot openICPSR package without admitting path rows."""

    package = Path(package_zip_path)
    base = _empty_phillot_package_audit_row(package)
    if not package.exists():
        base.update(
            {
                "package_present": "false",
                "package_read_status": "blocked_package_missing",
                "exact_blocker": "phillot_openicpsr_package_zip_missing",
            }
        )
        return [base]

    try:
        with ZipFile(package) as archive:
            names = set(archive.namelist())
            missing = [
                required
                for required in PHILLOT_REQUIRED_PACKAGE_FILES
                if required not in names
            ]
            base.update(
                {
                    "package_present": "true",
                    "package_read_status": "pass_zip_readable",
                    "required_file_count": str(len(PHILLOT_REQUIRED_PACKAGE_FILES)),
                    "required_file_present_count": str(
                        len(PHILLOT_REQUIRED_PACKAGE_FILES) - len(missing)
                    ),
                    "required_files_missing": ";".join(missing),
                }
            )
            if missing:
                base.update(
                    {
                        "source_admission_status": "blocked_required_files_missing",
                        "exact_blocker": "required_files_missing",
                    }
                )
                return [base]
            with TemporaryDirectory() as tmp_dir:
                archive.extract("data/4_Treasury_supply_shocks.dta", tmp_dir)
                archive.extract(
                    "raw_public/TreasuryDirect/announcement_timestamps.dta",
                    tmp_dir,
                )
                return [
                    _audit_phillot_extracted_stata_files(
                        base,
                        Path(tmp_dir) / "data/4_Treasury_supply_shocks.dta",
                        Path(tmp_dir)
                        / "raw_public/TreasuryDirect/announcement_timestamps.dta",
                    )
                ]
    except Exception as exc:  # pragma: no cover - defensive status capture
        base.update(
            {
                "package_present": "true",
                "package_read_status": f"blocked_zip_read_error:{type(exc).__name__}",
                "exact_blocker": "package_zip_read_failed",
            }
        )
        return [base]


def phillot_treasury_auction_instrument_rows(
    package_zip_path: str | Path = PHILLOT_OPENICPSR_PACKAGE_ZIP,
) -> list[dict[str, str]]:
    """Return normalized Treasury futures shock instruments, not curve path rows."""

    package = Path(package_zip_path)
    if not package.exists():
        return []
    with TemporaryDirectory() as tmp_dir:
        with ZipFile(package) as archive:
            archive.extract("data/4_Treasury_supply_shocks.dta", tmp_dir)
            archive.extract(
                "raw_public/TreasuryDirect/announcement_timestamps.dta",
                tmp_dir,
            )
        return _phillot_instrument_rows_from_stata(
            Path(tmp_dir) / "data/4_Treasury_supply_shocks.dta",
            Path(tmp_dir)
            / "raw_public/TreasuryDirect/announcement_timestamps.dta",
        )


def phillot_daily_yield_bridge_rows(
    package_zip_path: str | Path = PHILLOT_OPENICPSR_PACKAGE_ZIP,
) -> list[dict[str, str]]:
    """Estimate same-source daily yield bridge diagnostics for Phillot shocks."""

    package = Path(package_zip_path)
    if not package.exists():
        return []
    with TemporaryDirectory() as tmp_dir:
        with ZipFile(package) as archive:
            archive.extract("data/4_Treasury_supply_shocks.dta", tmp_dir)
            archive.extract("data/1_Financial.dta", tmp_dir)
        return _phillot_daily_yield_bridge_rows_from_stata(
            Path(tmp_dir) / "data/4_Treasury_supply_shocks.dta",
            Path(tmp_dir) / "data/1_Financial.dta",
        )


def treasury_supply_maturity_shock_path_object_rows(
    candidate_rows: Iterable[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Normalize optional candidate shock rows, failing closed unless every gate passes."""

    return [_path_object_row(row) for row in candidate_rows]


def treasury_event_window_yield_path_object_rows(
    event_window_rows: Iterable[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Build path-object rows from event-window 5y/10y/30y yield-bp candidates."""

    return [
        _path_object_row(_event_window_yield_path_candidate(row))
        for row in event_window_rows
    ]


def official_fspdp_gdp_panel_rows(
    source_dir: str | Path = CURRENT_DEMAND_GDP_SHARE_DIR,
) -> list[dict[str, str]]:
    """Read the local official FRED/BEA FSPDP and GDP panel."""

    root = Path(source_dir)
    series = {
        "nominal_fspdp": _read_quarterly_fred_series(
            root / "LA0000031Q027SBEA.csv",
            "LA0000031Q027SBEA",
        ),
        "real_fspdp": _read_quarterly_fred_series(
            root / "LB0000031Q020SBEA.csv",
            "LB0000031Q020SBEA",
        ),
        "nominal_gdp": _read_quarterly_fred_series(root / "GDP.csv", "GDP"),
        "real_gdp": _read_quarterly_fred_series(root / "GDPC1.csv", "GDPC1"),
    }
    quarters = sorted(set.intersection(*(set(values) for values in series.values())))
    return [
        {
            "quarter": quarter,
            "nominal_fspdp": _format_decimal_or_blank(
                series["nominal_fspdp"][quarter]
            ),
            "real_fspdp": _format_decimal_or_blank(series["real_fspdp"][quarter]),
            "nominal_gdp": _format_decimal_or_blank(series["nominal_gdp"][quarter]),
            "real_gdp": _format_decimal_or_blank(series["real_gdp"][quarter]),
        }
        for quarter in quarters
    ]


def treasury_supply_maturity_h4_fspdp_response_rows(
    path_object_rows: Iterable[Mapping[str, str]],
    fspdp_gdp_panel_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Estimate the h4 FSPDP/GDP response on the same 100bp-year path axis."""

    paths = list(path_object_rows)
    panel = {row["quarter"]: row for row in fspdp_gdp_panel_rows if row.get("quarter")}
    eligible_paths = [row for row in paths if _path_row_ready_for_h4_response(row)]
    observations = [
        obs
        for row in eligible_paths
        if (obs := _h4_response_observation(row, panel)) is not None
    ]
    blockers: list[str] = []
    if not paths:
        blockers.append("no_treasury_supply_maturity_path_rows")
    if not eligible_paths:
        blockers.append("no_path_rows_ready_for_h4_response_estimation")
    if not panel:
        blockers.append("missing_official_fspdp_gdp_panel")
    if not observations:
        blockers.append("no_usable_h4_fspdp_observations")

    beta = stderr = ci_low = ci_high = None
    placebo_beta = placebo_ci_low = placebo_ci_high = None
    nominal_beta = None
    if observations:
        beta, stderr, ci_low, ci_high = _ols_slope_with_ci(
            [obs["exposure"] for obs in observations],
            [obs["outcome"] for obs in observations],
        )
        placebo_beta, _, placebo_ci_low, placebo_ci_high = _ols_slope_with_ci(
            [obs["exposure"] for obs in observations],
            [obs["placebo_outcome"] for obs in observations],
        )
        nominal_beta, _, _, _ = _ols_slope_with_ci(
            [obs["exposure"] for obs in observations],
            [obs["nominal_share_outcome"] for obs in observations],
        )
    if beta is None:
        blockers.append("h4_fspdp_design_not_estimable")
    h4_ci_pass = beta is not None and ci_high is not None and beta < 0 and ci_high < 0
    gdp_robustness_pass = (
        beta is not None
        and nominal_beta is not None
        and beta < 0
        and nominal_beta < 0
    )
    sample_pass = len(observations) >= 20
    placebo_pass = (
        placebo_ci_low is not None
        and placebo_ci_high is not None
        and placebo_ci_low <= 0 <= placebo_ci_high
    )
    if not h4_ci_pass:
        blockers.append("h4_fspdp_ci_does_not_clear_negative_nonzero_rule")
    if not gdp_robustness_pass:
        blockers.append("nominal_share_gdp_robustness_not_negative")
    if not sample_pass:
        blockers.append("sample_below_20_usable_event_threshold")
    if not placebo_pass:
        blockers.append("placebo_lead_pretrend_not_cleared")

    pass_all = not blockers
    return [
        {
            "treasury_supply_maturity_h4_fspdp_response_id": (
                "treasury_supply_maturity_h4_fspdp_response::current_estimate"
            ),
            "target_outcome_id": (
                "share_weighted_real_fspdp_level_response_gdp_share_pp"
            ),
            "horizon_q": "4",
            "event_count": str(len(paths)),
            "eligible_event_count": str(len(eligible_paths)),
            "usable_observation_count": str(len(observations)),
            "sample_start_q": observations[0]["quarter"] if observations else "",
            "sample_end_q": observations[-1]["quarter"] if observations else "",
            "beta_per_100bp_year": _format_float_or_blank(beta),
            "standard_error": _format_float_or_blank(stderr),
            "ci95_low": _format_float_or_blank(ci_low),
            "ci95_high": _format_float_or_blank(ci_high),
            "placebo_beta_per_100bp_year": _format_float_or_blank(placebo_beta),
            "placebo_ci95_low": _format_float_or_blank(placebo_ci_low),
            "placebo_ci95_high": _format_float_or_blank(placebo_ci_high),
            "nominal_share_beta_per_100bp_year": _format_float_or_blank(nominal_beta),
            "outcome_formula": (
                "100 * (nominal_fspdp[t-1] / nominal_gdp[t-1]) * "
                "(log(real_fspdp[t+4]) - log(real_fspdp[t-1]))"
            ),
            "exposure_formula": "normalized_100bp_year_value[t]",
            "source_panel_status": (
                "pass_official_fred_bea_fspdp_gdp_panel_available"
                if panel
                else "blocked_missing_official_fspdp_gdp_panel"
            ),
            "path_object_status": (
                "pass_path_rows_ready_for_h4_response"
                if eligible_paths
                else "blocked_no_path_rows_ready_for_h4_response"
            ),
            "h4_fspdp_estimate_status": (
                "pass" if beta is not None else "blocked_h4_fspdp_design_not_estimable"
            ),
            "h4_ci_status": "pass" if h4_ci_pass else "blocked_h4_ci_not_negative",
            "gdp_robustness_status": (
                "pass" if gdp_robustness_pass else "blocked_nominal_share_not_negative"
            ),
            "sample_robustness_status": (
                "pass" if sample_pass else "blocked_too_few_usable_observations"
            ),
            "placebo_leads_pretrend_status": (
                "pass" if placebo_pass else "blocked_placebo_lead_pretrend"
            ),
            "admission_status": (
                "pass_h4_fspdp_response_for_noncanonical_path_gate"
                if pass_all
                else "blocked_h4_fspdp_response"
            ),
            "exact_blocker": ";".join(dict.fromkeys(blockers))
            if blockers
            else "h4_fspdp_response_passed_noncanonical_research_gate_only",
            "allowed_use": "noncanonical_denominator_response_research_only",
            "blocked_use": BLOCKED_USE,
            "canonical_ratio_entry": "false",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "denominator_prior_update_allowed": "false",
        }
    ]


def treasury_supply_maturity_path_objects_with_h4_response(
    path_object_rows: Iterable[Mapping[str, str]],
    h4_response_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Attach a passing h4 response estimate back to path rows and re-run the gate."""

    responses = list(h4_response_rows)
    response = responses[0] if responses else {}
    response_passed = response.get("admission_status") == (
        "pass_h4_fspdp_response_for_noncanonical_path_gate"
    )
    enriched_rows: list[dict[str, str]] = []
    for row in path_object_rows:
        enriched = dict(row)
        if response_passed and _path_row_ready_for_h4_response(row):
            enriched.update(
                {
                    "h4_fspdp_estimate_status": "pass",
                    "h4_fspdp_beta_per_100bp_year": response["beta_per_100bp_year"],
                    "h4_fspdp_ci95_low": response["ci95_low"],
                    "h4_fspdp_ci95_high": response["ci95_high"],
                    "h4_ci_status": "pass",
                    "gdp_robustness_status": "pass",
                    "sample_robustness_status": "pass",
                    "placebo_leads_pretrend_status": "pass",
                }
            )
        enriched_rows.append(_path_object_row(enriched))
    return enriched_rows


def treasury_supply_maturity_shock_coefficient_admission_rows(
    path_object_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return the current noncanonical coefficient admission decision."""

    rows = list(path_object_rows)
    pass_rows = [
        row
        for row in rows
        if row.get("admission_status")
        == "admitted_treasury_supply_maturity_shock_path_object"
    ]
    estimate_pass_rows = [
        row
        for row in pass_rows
        if _negative_nonzero_ci(row)
        and row.get("h4_fspdp_estimate_status") == "pass"
        and row.get("gdp_robustness_status") == "pass"
    ]
    blockers = []
    if not rows:
        blockers.append("no_treasury_supply_maturity_shock_path_rows")
    if not pass_rows:
        blockers.append("no_admitted_treasury_supply_maturity_shock_path_object")
    if not estimate_pass_rows:
        blockers.append("no_nonzero_contractionary_h4_fspdp_estimate")

    admitted = ""
    status = "no_admitted_denominator_response_coefficient"
    if estimate_pass_rows:
        admitted = str(estimate_pass_rows[0].get("h4_fspdp_beta_per_100bp_year", ""))
        status = "admitted_noncanonical_treasury_supply_maturity_coefficient"
        blockers = ["canonical_denominator_update_still_forbidden"]

    return [
        {
            "treasury_supply_maturity_coefficient_decision_id": (
                "treasury_supply_maturity_shock_coefficient::current_admission_status"
            ),
            "target_outcome_id": (
                "share_weighted_real_fspdp_level_response_gdp_share_pp"
            ),
            "primary_horizon_q": "4",
            "required_shock_object_kind": (
                "treasury_supply_maturity_shock_100bp_year_candidate"
            ),
            "path_object_candidate_count": str(len(rows)),
            "path_object_pass_count": str(len(pass_rows)),
            "primary_estimate_pass_count": str(len(estimate_pass_rows)),
            "admitted_denominator_response_coefficient": admitted,
            "admitted_denominator_response_coefficient_unit": (
                "gdp_share_pp_per_100bp_year_effective_curve_shock" if admitted else ""
            ),
            "coefficient_admission_status": status,
            "exact_blocker": ";".join(blockers),
            "next_model_requirement": (
                "acquire_replicable_treasury_supply_maturity_shock_series_with_"
                "100bp_year_curve_bridge_and_nonzero_h4_fspdp_response"
            ),
            "allowed_use": "noncanonical_denominator_response_research_only",
            "blocked_use": BLOCKED_USE,
            "canonical_ratio_entry": "false",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "denominator_prior_update_allowed": "false",
        }
    ]


def write_treasury_supply_maturity_shock_source_inventory_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    return _write_csv(path, rows, TREASURY_SUPPLY_MATURITY_SHOCK_SOURCE_INVENTORY_FIELDS)


def write_phillot_package_schema_audit_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    return _write_csv(path, rows, TREASURY_SUPPLY_MATURITY_SHOCK_PACKAGE_AUDIT_FIELDS)


def write_phillot_treasury_auction_instrument_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    return _write_csv(path, rows, PHILLOT_TREASURY_AUCTION_INSTRUMENT_FIELDS)


def write_phillot_daily_yield_bridge_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    return _write_csv(path, rows, PHILLOT_DAILY_YIELD_BRIDGE_FIELDS)


def write_treasury_supply_maturity_shock_path_object_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    return _write_csv(path, rows, TREASURY_SUPPLY_MATURITY_SHOCK_PATH_OBJECT_FIELDS)


def write_treasury_supply_maturity_h4_fspdp_response_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    return _write_csv(path, rows, TREASURY_SUPPLY_MATURITY_H4_FSPDP_RESPONSE_FIELDS)


def write_treasury_supply_maturity_shock_coefficient_admission_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
) -> Path:
    return _write_csv(path, rows, TREASURY_SUPPLY_MATURITY_SHOCK_COEFFICIENT_ADMISSION_FIELDS)


def _source_row(
    *,
    source_id: str,
    source_package_id: str,
    source_package_doi: str,
    source_title: str,
    source_url: str,
    source_publisher: str,
    publication_year: str,
    source_class: str,
    source_access_status: str,
    download_auth_required: str,
    verified_machine_readable_files: str,
    shock_series_schema_verified: str,
    event_grain_verified: str,
    raw_market_data_access_class: str,
    source_request_status: str,
    native_unit: str,
    shock_family_supported: str,
    has_event_window_timestamps: str,
    has_5y_10y_30y_bridge: str,
    has_effective_curve_bridge: str,
    macro_outcome_available: str,
    role_in_ratewall: str,
    exact_blocker: str,
) -> dict[str, str]:
    return {
        "source_id": source_id,
        "source_package_id": source_package_id,
        "source_package_doi": source_package_doi,
        "source_title": source_title,
        "source_url": source_url,
        "source_publisher": source_publisher,
        "publication_year": publication_year,
        "source_class": source_class,
        "source_access_status": source_access_status,
        "download_auth_required": download_auth_required,
        "verified_machine_readable_files": verified_machine_readable_files,
        "shock_series_schema_verified": shock_series_schema_verified,
        "event_grain_verified": event_grain_verified,
        "raw_market_data_access_class": raw_market_data_access_class,
        "source_request_status": source_request_status,
        "native_unit": native_unit,
        "shock_family_supported": shock_family_supported,
        "has_event_window_timestamps": has_event_window_timestamps,
        "has_5y_10y_30y_bridge": has_5y_10y_30y_bridge,
        "has_effective_curve_bridge": has_effective_curve_bridge,
        "macro_outcome_available": macro_outcome_available,
        "role_in_ratewall": role_in_ratewall,
        "admission_status": "source_inventory_only_not_path_object",
        "exact_blocker": exact_blocker,
        "allowed_use": "treasury_supply_maturity_shock_source_review_only",
        "blocked_use": BLOCKED_USE,
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
    }


def _empty_phillot_package_audit_row(package: Path) -> dict[str, str]:
    return {
        "source_id": "phillot_2025_aea_treasury_auction_supply_shocks",
        "source_package_id": "openicpsr_192741_v1",
        "source_package_doi": "10.3886/E192741V1",
        "package_path": str(package),
        "package_present": "false",
        "package_read_status": "not_checked",
        "required_file_count": str(len(PHILLOT_REQUIRED_PACKAGE_FILES)),
        "required_file_present_count": "0",
        "required_files_missing": ";".join(PHILLOT_REQUIRED_PACKAGE_FILES),
        "shock_file_read_status": "not_checked",
        "shock_row_count": "",
        "shock_date_min": "",
        "shock_date_max": "",
        "shock_columns_present": "",
        "shock_columns_missing": ";".join(PHILLOT_SHOCK_COLUMNS),
        "shock_nonmissing_observation_count_min": "",
        "shock_nonmissing_observation_count_max": "",
        "shock_native_unit": "",
        "shock_sign_convention_status": "not_checked",
        "event_window": "",
        "event_grain_status": "not_checked",
        "announcement_timestamp_read_status": "not_checked",
        "announcement_timestamp_count": "",
        "announcement_timestamp_date_min": "",
        "announcement_timestamp_date_max": "",
        "tenor_2y_5y_10y_30y_status": "not_checked",
        "yield_equivalent_bp_conversion_status": "not_checked",
        "effective_curve_bridge_status": "not_checked",
        "shock_family_separation_status": "not_checked",
        "source_admission_status": "blocked_not_checked",
        "exact_blocker": "package_schema_audit_not_run",
        "allowed_use": "phillot_package_schema_audit_only",
        "blocked_use": BLOCKED_USE,
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
    }


def _audit_phillot_extracted_stata_files(
    row: dict[str, str],
    shock_path: Path,
    timestamp_path: Path,
) -> dict[str, str]:
    import pandas as pd
    from pandas.io.stata import StataReader

    try:
        shock_data = pd.read_stata(shock_path)
        with StataReader(shock_path) as reader:
            labels = reader.variable_labels()
    except Exception as exc:  # pragma: no cover - defensive status capture
        row.update(
            {
                "shock_file_read_status": f"blocked_stata_read_error:{type(exc).__name__}",
                "exact_blocker": "shock_stata_file_read_failed",
            }
        )
        return row

    present = [column for column in PHILLOT_SHOCK_COLUMNS if column in shock_data]
    missing = [column for column in PHILLOT_SHOCK_COLUMNS if column not in shock_data]
    nonmissing_counts = [int(shock_data[column].notna().sum()) for column in present]
    row.update(
        {
            "shock_file_read_status": "pass_stata_readable",
            "shock_row_count": str(len(shock_data)),
            "shock_date_min": _date_min(shock_data, "date"),
            "shock_date_max": _date_max(shock_data, "date"),
            "shock_columns_present": ";".join(present),
            "shock_columns_missing": ";".join(missing),
            "shock_nonmissing_observation_count_min": (
                str(min(nonmissing_counts)) if nonmissing_counts else "0"
            ),
            "shock_nonmissing_observation_count_max": (
                str(max(nonmissing_counts)) if nonmissing_counts else "0"
            ),
            "shock_native_unit": _combine_text(labels.get(column, "") for column in present),
            "shock_sign_convention_status": (
                "pass_code_comment_positive_supply_shock_negative_price_positive_yield"
            ),
            "event_window": "m5_p29",
            "event_grain_status": "pass_daily_rows_with_462_nonmissing_event_shocks",
            "tenor_2y_5y_10y_30y_status": (
                "pass_native_2y_5y_10y_30y_normalized_futures_returns"
                if not missing
                else "blocked_missing_required_tenors"
            ),
            "yield_equivalent_bp_conversion_status": (
                "blocked_native_units_are_normalized_futures_log_returns_not_yield_bp"
            ),
            "effective_curve_bridge_status": (
                "blocked_no_100bp_year_effective_curve_bridge"
            ),
            "shock_family_separation_status": (
                "blocked_phillot_file_has_tenor_shocks_not_bpz_debt_vs_maturity_factors"
            ),
            "source_admission_status": "source_schema_verified_not_path_object",
            "exact_blocker": (
                "native_shock_units_are_normalized_futures_log_returns_not_yield_bp;"
                "no_effective_curve_100bp_year_bridge;"
                "no_debt_expansion_vs_maturity_extension_family_separation;"
                "no_h4_fspdp_denominator_response_estimate"
            ),
        }
    )

    try:
        timestamp_data = pd.read_stata(timestamp_path)
    except Exception as exc:  # pragma: no cover - defensive status capture
        row.update(
            {
                "announcement_timestamp_read_status": (
                    f"blocked_stata_read_error:{type(exc).__name__}"
                ),
                "exact_blocker": (
                    row["exact_blocker"] + ";announcement_timestamp_file_read_failed"
                ),
            }
        )
        return row
    row.update(
        {
            "announcement_timestamp_read_status": "pass_stata_readable",
            "announcement_timestamp_count": str(len(timestamp_data)),
            "announcement_timestamp_date_min": _date_min(timestamp_data, "date"),
            "announcement_timestamp_date_max": _date_max(timestamp_data, "date"),
        }
    )
    return row


def _phillot_instrument_rows_from_stata(
    shock_path: Path,
    timestamp_path: Path,
) -> list[dict[str, str]]:
    import pandas as pd

    shock_data = pd.read_stata(shock_path)
    timestamp_data = pd.read_stata(timestamp_path)
    timestamp_columns = ["date", "hour", "minute"]
    timestamp_lookup = (
        timestamp_data[timestamp_columns]
        .dropna(subset=["date"])
        .drop_duplicates(subset=["date"], keep="first")
    )
    merged = shock_data.merge(
        timestamp_lookup,
        how="left",
        on="date",
    )
    event_rows = merged.dropna(subset=list(PHILLOT_SHOCK_COLUMNS), how="all")
    return [_phillot_instrument_row(row) for _, row in event_rows.iterrows()]


def _phillot_instrument_row(row) -> dict[str, str]:
    event_date = str(row["date"].date())
    in_sample = (
        PHILLOT_ANALYSIS_SAMPLE_START <= event_date <= PHILLOT_ANALYSIS_SAMPLE_END
    )
    timestamp_status = (
        "pass_announcement_timestamp_matched"
        if not _is_missing(row.get("hour")) and not _is_missing(row.get("minute"))
        else "blocked_no_announcement_timestamp_match"
    )
    return {
        "instrument_object_id": (
            "phillot_treasury_auction_normalized_futures_instrument_v1::"
            f"{event_date}"
        ),
        "source_id": "phillot_2025_aea_treasury_auction_supply_shocks",
        "source_package_id": "openicpsr_192741_v1",
        "source_package_doi": "10.3886/E192741V1",
        "event_date": event_date,
        "announcement_timestamp_status": timestamp_status,
        "announcement_hour": _format_float_or_blank(row.get("hour")),
        "announcement_minute": _format_float_or_blank(row.get("minute")),
        "event_window": "m5_p29",
        "normalization_sample_start": PHILLOT_ANALYSIS_SAMPLE_START,
        "normalization_sample_end": PHILLOT_ANALYSIS_SAMPLE_END,
        "in_analysis_sample": "true" if in_sample else "false",
        "n_2y_m5_p29": _format_float_or_blank(row.get("n_2y_m5_p29")),
        "n_5y_m5_p29": _format_float_or_blank(row.get("n_5y_m5_p29")),
        "n_10y_m5_p29": _format_float_or_blank(row.get("n_10y_m5_p29")),
        "n_30y_m5_p29": _format_float_or_blank(row.get("n_30y_m5_p29")),
        "shock_unit": "standardized_negative_treasury_futures_log_return",
        "native_unit": "unitless_sample_standard_deviation",
        "sign_convention": (
            "positive_supply_negative_futures_price_positive_yield_direction"
        ),
        "raw_event_window_return_available": "false",
        "yield_bp_equivalent_available": "false",
        "effective_curve_100bp_year_available": "false",
        "shock_family_separation_status": (
            "blocked_not_debt_expansion_vs_maturity_extension_factor"
        ),
        "path_object_admission_status": "blocked_not_a_yield_bp_or_100bp_year_path",
        "allowed_use": "noncanonical_lp_iv_instrument_research_only",
        "blocked_use": (
            "yield_bp_path;100bp_year_path;denominator_prior_update;"
            "canonical_D_update;main_ratio_entry;headline_promotion;"
            "debt_expansion_maturity_extension_family_claim"
        ),
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
    }


def _phillot_daily_yield_bridge_rows_from_stata(
    shock_path: Path,
    financial_path: Path,
) -> list[dict[str, str]]:
    import pandas as pd

    shock_data = pd.read_stata(shock_path).sort_values("date")
    financial_data = pd.read_stata(financial_path).sort_values("date")
    bridge_specs = [
        ("2y", "n_2y_m5_p29", "r2y_fred"),
        ("5y", "n_5y_m5_p29", "r5y_fred"),
        ("10y", "n_10y_m5_p29", "r10y_fred"),
        ("30y", "n_30y_m5_p29", "r30y_fred"),
    ]
    rate_columns = [
        rate_column
        for _, _, rate_column in bridge_specs
        if rate_column in financial_data
    ]
    for rate_column in rate_columns:
        financial_data[f"delta_{rate_column}"] = (
            financial_data[rate_column] - financial_data[rate_column].shift(1)
        )
    merged = shock_data.merge(
        financial_data[
            ["date", *[f"delta_{rate_column}" for rate_column in rate_columns]]
        ],
        how="left",
        on="date",
    )
    return [
        _phillot_daily_yield_bridge_row(
            merged=merged,
            tenor=tenor,
            shock_column=shock_column,
            rate_column=rate_column,
        )
        for tenor, shock_column, rate_column in bridge_specs
    ]


def _phillot_daily_yield_bridge_row(
    *,
    merged,
    tenor: str,
    shock_column: str,
    rate_column: str,
) -> dict[str, str]:
    delta_column = f"delta_{rate_column}"
    if shock_column not in merged or delta_column not in merged:
        sample = []
    else:
        sample_frame = merged[["date", shock_column, delta_column]].dropna()
        sample = [
            {
                "date": str(row["date"].date()),
                "x": float(row[shock_column]),
                "y": float(row[delta_column]),
            }
            for _, row in sample_frame.iterrows()
        ]
    estimate = _ols_slope(sample)
    if estimate is None:
        slope = se = ci_low = ci_high = r_squared = intercept = ""
    else:
        slope, se, ci_low, ci_high, r_squared, intercept = (
            _format_float(value) for value in estimate
        )
    y_values = [row["y"] for row in sample]
    x_values = [row["x"] for row in sample]
    blocker = (
        "same_source_daily_fred_yield_change_is_not_the_phillot_m5_p29_"
        "high_frequency_event_window;daily_close_bridge_can_check_scale_but_"
        "cannot_admit_100bp_year_effective_curve_or_denominator_coefficient"
    )
    return {
        "bridge_row_id": (
            "phillot_daily_yield_bridge::"
            f"{tenor}::{shock_column}::{rate_column}"
        ),
        "source_id": "phillot_2025_aea_treasury_auction_supply_shocks",
        "source_package_id": "openicpsr_192741_v1",
        "source_package_doi": "10.3886/E192741V1",
        "tenor": tenor,
        "shock_column": shock_column,
        "daily_yield_column": rate_column,
        "sample_start": sample[0]["date"] if sample else "",
        "sample_end": sample[-1]["date"] if sample else "",
        "event_count": str(len(sample)),
        "shock_unit": "standardized_negative_treasury_futures_log_return",
        "daily_yield_change_unit": "basis_points_same_day_daily_fred_change",
        "slope_bp_per_normalized_shock": slope,
        "standard_error": se,
        "ci95_low": ci_low,
        "ci95_high": ci_high,
        "r_squared": r_squared,
        "intercept_bp": intercept,
        "yield_change_mean_bp": _format_float(_mean(y_values)) if y_values else "",
        "yield_change_sd_bp": (
            _format_float(_sample_sd(y_values)) if len(y_values) > 1 else ""
        ),
        "shock_mean": _format_float(_mean(x_values)) if x_values else "",
        "shock_sd": _format_float(_sample_sd(x_values)) if len(x_values) > 1 else "",
        "same_source_package_status": (
            "pass_shock_and_daily_yield_series_from_openicpsr_package"
            if sample
            else "blocked_missing_shock_or_daily_yield_series"
        ),
        "event_window_alignment_status": (
            "blocked_daily_close_not_m5_p29_high_frequency_event_window"
        ),
        "yield_equivalent_bp_conversion_status": (
            "diagnostic_same_day_daily_yield_bp_bridge_not_admitted"
        ),
        "effective_curve_bridge_status": (
            "blocked_no_admitted_100bp_year_effective_curve_bridge"
        ),
        "admission_status": "not_admitted_daily_yield_bridge_diagnostic_only",
        "exact_blocker": blocker,
        "allowed_use": "treasury_supply_maturity_shock_yield_bridge_scale_check",
        "blocked_use": BLOCKED_USE,
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
    }


def _event_window_yield_path_candidate(row: Mapping[str, str]) -> dict[str, str]:
    source_yield_unit = str(row.get("source_yield_unit", row.get("yield_bp_unit", "")))
    event_window = str(row.get("event_window", ""))
    curve_5y = _decimal_or_none(row.get("curve_5y_bp"))
    curve_10y = _decimal_or_none(row.get("curve_10y_bp"))
    curve_30y = _decimal_or_none(row.get("curve_30y_bp"))
    weight_5y = _decimal_or_default(
        row.get("effective_curve_weight_5y"), Decimal("0.25")
    )
    weight_10y = _decimal_or_default(
        row.get("effective_curve_weight_10y"), Decimal("0.50")
    )
    weight_30y = _decimal_or_default(
        row.get("effective_curve_weight_30y"), Decimal("0.25")
    )
    effective_curve = _effective_curve_bp(
        curve_5y=curve_5y,
        curve_10y=curve_10y,
        curve_30y=curve_30y,
        weight_5y=weight_5y,
        weight_10y=weight_10y,
        weight_30y=weight_30y,
    )
    source_is_event_window_bp = (
        source_yield_unit == "basis_points_event_window"
        and "daily" not in str(row.get("candidate_role", "")).lower()
        and "daily" not in str(row.get("bridge_row_id", "")).lower()
    )
    weights_pass = (
        effective_curve is not None
        and weight_5y + weight_10y + weight_30y == Decimal("1")
    )
    return {
        "candidate_id": str(
            row.get(
                "candidate_id",
                row.get(
                    "treasury_supply_maturity_shock_path_object_candidate_id",
                    row.get("bridge_row_id", ""),
                ),
            )
        ),
        "shock_family": str(row.get("shock_family", "")),
        "source_id": str(row.get("source_id", "")),
        "source_event_id": str(row.get("source_event_id", "")),
        "event_date": str(row.get("event_date", "")),
        "quarter": str(row.get("quarter", "")),
        "event_window": event_window,
        "source_vintage": str(row.get("source_vintage", "")),
        "source_publisher": str(row.get("source_publisher", "")),
        "source_shock_unit": source_yield_unit,
        "source_shock_value": str(row.get("source_shock_value", "")),
        "curve_5y_bp": _format_decimal_or_blank(curve_5y),
        "curve_10y_bp": _format_decimal_or_blank(curve_10y),
        "curve_30y_bp": _format_decimal_or_blank(curve_30y),
        "effective_curve_overlay_bp": _format_decimal_or_blank(effective_curve),
        "horizon_weight_years": str(row.get("horizon_weight_years", "1")),
        "source_acquisition_status": _pass_or_status(
            bool(row.get("source_acquisition_status") == "pass"),
            "blocked_event_window_source_not_acquired",
        ),
        "event_window_timestamp_status": _pass_or_status(
            bool(
                row.get("event_window_timestamp_status") == "pass"
                and event_window in {"m5_p29", "source_defined_hf_window"}
            ),
            "blocked_event_window_timestamp_not_verified",
        ),
        "independent_replication_status": str(
            row.get("independent_replication_status", "blocked_missing_status")
        ),
        "shock_family_declared_status": str(
            row.get("shock_family_declared_status", "blocked_missing_status")
        ),
        "mixed_shock_separation_status": str(
            row.get("mixed_shock_separation_status", "blocked_missing_status")
        ),
        "yield_equivalent_bp_conversion_status": _pass_or_status(
            source_is_event_window_bp,
            "blocked_source_yield_unit_not_event_window_basis_points",
        ),
        "effective_curve_bridge_status": _pass_or_status(
            weights_pass,
            "blocked_missing_curve_tenors_or_weights_not_sum_one",
        ),
        "normalization_status": _pass_or_status(
            effective_curve is not None,
            "blocked_no_effective_curve_normalization",
        ),
        "first_stage_relevance_status": str(
            row.get("first_stage_relevance_status", "blocked_missing_status")
        ),
        "h4_fspdp_estimate_status": str(
            row.get("h4_fspdp_estimate_status", "blocked_missing_status")
        ),
        "h4_fspdp_beta_per_100bp_year": str(
            row.get("h4_fspdp_beta_per_100bp_year", "")
        ),
        "h4_fspdp_ci95_low": str(row.get("h4_fspdp_ci95_low", "")),
        "h4_fspdp_ci95_high": str(row.get("h4_fspdp_ci95_high", "")),
        "h4_ci_status": str(row.get("h4_ci_status", "blocked_missing_status")),
        "gdp_robustness_status": str(
            row.get("gdp_robustness_status", "blocked_missing_status")
        ),
        "sample_robustness_status": str(
            row.get("sample_robustness_status", "blocked_missing_status")
        ),
        "placebo_leads_pretrend_status": str(
            row.get("placebo_leads_pretrend_status", "blocked_missing_status")
        ),
        "scenario_overlay_shape_bridge_status": str(
            row.get("scenario_overlay_shape_bridge_status", "blocked_missing_status")
        ),
    }


def _path_object_row(row: Mapping[str, str]) -> dict[str, str]:
    effective_curve = _decimal_or_none(row.get("effective_curve_overlay_bp"))
    path_bps_year = _decimal_or_none(row.get("path_bps_year"))
    if path_bps_year is None and effective_curve is not None:
        years = _decimal_or_none(row.get("horizon_weight_years")) or Decimal("1")
        path_bps_year = effective_curve * years
    normalized = path_bps_year / Decimal("100") if path_bps_year is not None else None
    blockers = _path_object_blockers(row, normalized)
    admitted = not blockers
    return {
        "treasury_supply_maturity_shock_path_object_candidate_id": str(
            row.get(
                "treasury_supply_maturity_shock_path_object_candidate_id",
                row.get("candidate_id", ""),
            )
        ),
        "shock_object_id": str(
            row.get(
                "shock_object_id",
                "treasury_supply_maturity_shock_100bp_year_candidate",
            )
        ),
        "shock_object_kind": "treasury_supply_maturity_shock_100bp_year_candidate",
        "shock_family": str(row.get("shock_family", "")),
        "source_id": str(row.get("source_id", "")),
        "source_event_id": str(row.get("source_event_id", "")),
        "event_date": str(row.get("event_date", "")),
        "quarter": str(row.get("quarter", "")),
        "event_window": str(row.get("event_window", "")),
        "source_vintage": str(row.get("source_vintage", "")),
        "source_publisher": str(row.get("source_publisher", "")),
        "source_shock_unit": str(row.get("source_shock_unit", "")),
        "source_shock_value": str(row.get("source_shock_value", "")),
        "curve_5y_bp": str(row.get("curve_5y_bp", "")),
        "curve_10y_bp": str(row.get("curve_10y_bp", "")),
        "curve_30y_bp": str(row.get("curve_30y_bp", "")),
        "effective_curve_overlay_bp": _format_decimal_or_blank(effective_curve),
        "horizon_weight_years": str(row.get("horizon_weight_years", "")),
        "path_bps_year": _format_decimal_or_blank(path_bps_year),
        "normalized_100bp_year_value": _format_decimal_or_blank(normalized),
        **{
            field: str(row.get(field, "blocked_missing_status"))
            for field in ADMISSION_PASS_STATUSES
        },
        "h4_fspdp_beta_per_100bp_year": str(
            row.get("h4_fspdp_beta_per_100bp_year", "")
        ),
        "h4_fspdp_ci95_low": str(row.get("h4_fspdp_ci95_low", "")),
        "h4_fspdp_ci95_high": str(row.get("h4_fspdp_ci95_high", "")),
        "admission_status": (
            "admitted_treasury_supply_maturity_shock_path_object"
            if admitted
            else "candidate_only_blocked"
        ),
        "exact_blocker": ";".join(blockers)
        if blockers
        else "path_object_passed_noncanonical_research_gate_only",
        "allowed_use": (
            "noncanonical_denominator_response_research_only"
            if admitted
            else "treasury_supply_maturity_shock_prerequisite_diagnostic_only"
        ),
        "blocked_use": BLOCKED_USE,
        "canonical_ratio_entry": "false",
        "enters_main_ratio": "false",
        "evidence_mode_enabled": "false",
        "denominator_prior_update_allowed": "false",
    }


def _path_object_blockers(
    row: Mapping[str, str],
    normalized_100bp_year_value: Decimal | None,
) -> list[str]:
    blockers = []
    shock_family = str(row.get("shock_family", ""))
    if shock_family not in REQUIRED_SHOCK_FAMILIES:
        blockers.append("shock_family_not_separately_identified")
    if normalized_100bp_year_value is None:
        blockers.append("no_100bp_year_effective_curve_normalization")
    for field, pass_value in ADMISSION_PASS_STATUSES.items():
        if row.get(field) != pass_value:
            blockers.append(field.replace("_status", ""))
    return blockers


def _path_row_ready_for_h4_response(row: Mapping[str, str]) -> bool:
    if row.get("shock_family") not in REQUIRED_SHOCK_FAMILIES:
        return False
    if _decimal_or_none(row.get("normalized_100bp_year_value")) is None:
        return False
    prerequisite_statuses = {
        field: pass_value
        for field, pass_value in ADMISSION_PASS_STATUSES.items()
        if field
        not in {
            "h4_fspdp_estimate_status",
            "h4_ci_status",
            "gdp_robustness_status",
            "sample_robustness_status",
            "placebo_leads_pretrend_status",
        }
    }
    return all(row.get(field) == pass_value for field, pass_value in prerequisite_statuses.items())


def _h4_response_observation(
    row: Mapping[str, str],
    panel: Mapping[str, Mapping[str, str]],
) -> dict[str, float | str] | None:
    quarter = str(row.get("quarter", ""))
    quarter_index = _quarter_index(quarter)
    exposure = _decimal_or_none(row.get("normalized_100bp_year_value"))
    if quarter_index is None or exposure is None:
        return None
    lag_quarter = _quarter_label(quarter_index - 1)
    future_quarter = _quarter_label(quarter_index + 4)
    placebo_start_quarter = _quarter_label(quarter_index - 5)
    lag_row = panel.get(lag_quarter)
    future_row = panel.get(future_quarter)
    placebo_start_row = panel.get(placebo_start_quarter)
    if lag_row is None or future_row is None or placebo_start_row is None:
        return None

    lag_nominal_fspdp = _positive_decimal(lag_row.get("nominal_fspdp"))
    lag_nominal_gdp = _positive_decimal(lag_row.get("nominal_gdp"))
    lag_real_fspdp = _positive_decimal(lag_row.get("real_fspdp"))
    future_nominal_fspdp = _positive_decimal(future_row.get("nominal_fspdp"))
    future_nominal_gdp = _positive_decimal(future_row.get("nominal_gdp"))
    future_real_fspdp = _positive_decimal(future_row.get("real_fspdp"))
    placebo_start_nominal_fspdp = _positive_decimal(
        placebo_start_row.get("nominal_fspdp")
    )
    placebo_start_nominal_gdp = _positive_decimal(placebo_start_row.get("nominal_gdp"))
    placebo_start_real_fspdp = _positive_decimal(placebo_start_row.get("real_fspdp"))
    values = (
        lag_nominal_fspdp,
        lag_nominal_gdp,
        lag_real_fspdp,
        future_nominal_fspdp,
        future_nominal_gdp,
        future_real_fspdp,
        placebo_start_nominal_fspdp,
        placebo_start_nominal_gdp,
        placebo_start_real_fspdp,
    )
    if any(value is None for value in values):
        return None
    assert lag_nominal_fspdp is not None
    assert lag_nominal_gdp is not None
    assert lag_real_fspdp is not None
    assert future_nominal_fspdp is not None
    assert future_nominal_gdp is not None
    assert future_real_fspdp is not None
    assert placebo_start_nominal_fspdp is not None
    assert placebo_start_nominal_gdp is not None
    assert placebo_start_real_fspdp is not None

    lag_share = float(lag_nominal_fspdp / lag_nominal_gdp)
    placebo_start_share = float(
        placebo_start_nominal_fspdp / placebo_start_nominal_gdp
    )
    outcome = 100.0 * lag_share * (
        math.log(float(future_real_fspdp)) - math.log(float(lag_real_fspdp))
    )
    placebo_outcome = 100.0 * placebo_start_share * (
        math.log(float(lag_real_fspdp)) - math.log(float(placebo_start_real_fspdp))
    )
    nominal_share_outcome = 100.0 * (
        float(future_nominal_fspdp / future_nominal_gdp)
        - float(lag_nominal_fspdp / lag_nominal_gdp)
    )
    return {
        "quarter": quarter,
        "exposure": float(exposure),
        "outcome": outcome,
        "placebo_outcome": placebo_outcome,
        "nominal_share_outcome": nominal_share_outcome,
    }


def _ols_slope_with_ci(
    x_values: Sequence[float],
    y_values: Sequence[float],
) -> tuple[float | None, float | None, float | None, float | None]:
    if len(x_values) != len(y_values) or len(x_values) < 3:
        return None, None, None, None
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    sxx = sum((x - x_mean) ** 2 for x in x_values)
    if sxx <= 0:
        return None, None, None, None
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values)) / sxx
    intercept = y_mean - slope * x_mean
    residual_sum_squares = sum(
        (y - (intercept + slope * x)) ** 2 for x, y in zip(x_values, y_values)
    )
    sigma2 = residual_sum_squares / (len(x_values) - 2)
    standard_error = math.sqrt(max(sigma2 / sxx, 0.0))
    ci_low = slope - 1.96 * standard_error
    ci_high = slope + 1.96 * standard_error
    return slope, standard_error, ci_low, ci_high


def _read_quarterly_fred_series(path: Path, series_id: str) -> dict[str, Decimal]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        values: dict[str, Decimal] = {}
        for row in rows:
            quarter = _quarter_from_observation_date(row.get("observation_date", ""))
            value = _decimal_or_none(row.get(series_id))
            if quarter and value is not None:
                values[quarter] = value
        return values


def _quarter_from_observation_date(value: str) -> str:
    parts = value.split("-")
    if len(parts) < 2:
        return ""
    year = parts[0]
    try:
        month = int(parts[1])
    except ValueError:
        return ""
    quarter = (month - 1) // 3 + 1
    if quarter not in {1, 2, 3, 4}:
        return ""
    return f"{year}Q{quarter}"


def _quarter_index(value: str) -> int | None:
    if len(value) != 6 or value[4] != "Q":
        return None
    try:
        year = int(value[:4])
        quarter = int(value[5])
    except ValueError:
        return None
    if quarter not in {1, 2, 3, 4}:
        return None
    return year * 4 + quarter - 1


def _quarter_label(index: int) -> str:
    year, offset = divmod(index, 4)
    return f"{year}Q{offset + 1}"


def _positive_decimal(value: object) -> Decimal | None:
    parsed = _decimal_or_none(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _negative_nonzero_ci(row: Mapping[str, str]) -> bool:
    beta = _decimal_or_none(row.get("h4_fspdp_beta_per_100bp_year"))
    low = _decimal_or_none(row.get("h4_fspdp_ci95_low"))
    high = _decimal_or_none(row.get("h4_fspdp_ci95_high"))
    if beta is None or low is None or high is None:
        return False
    return beta < 0 and high < 0 and low < high


def _write_csv(
    path: str | Path,
    rows: Iterable[Mapping[str, str]],
    fields: list[str],
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return out


def _combine_text(values: Iterable[str]) -> str:
    unique = sorted({value for value in values if value})
    if not unique:
        return ""
    return unique[0] if len(unique) == 1 else ";".join(unique)


def _date_min(data, column: str) -> str:
    if column not in data or data[column].dropna().empty:
        return ""
    return str(data[column].dropna().min().date())


def _date_max(data, column: str) -> str:
    if column not in data or data[column].dropna().empty:
        return ""
    return str(data[column].dropna().max().date())


def _is_missing(value: object) -> bool:
    try:
        import pandas as pd

        return bool(pd.isna(value))
    except Exception:  # pragma: no cover - defensive fallback
        return value is None


def _format_float_or_blank(value: object) -> str:
    if _is_missing(value):
        return ""
    return format(float(value), ".12g")


def _ols_slope(
    sample: list[dict[str, float | str]],
) -> tuple[float, float, float, float, float, float] | None:
    if len(sample) < 3:
        return None
    xs = [float(row["x"]) for row in sample]
    ys = [float(row["y"]) for row in sample]
    x_bar = sum(xs) / len(xs)
    y_bar = sum(ys) / len(ys)
    sxx = sum((x - x_bar) ** 2 for x in xs)
    syy = sum((y - y_bar) ** 2 for y in ys)
    if sxx == 0:
        return None
    slope = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys, strict=True)) / sxx
    intercept = y_bar - slope * x_bar
    residual_sum = sum(
        (y - intercept - slope * x) ** 2 for x, y in zip(xs, ys, strict=True)
    )
    sigma2 = residual_sum / (len(xs) - 2)
    se = math.sqrt(max(sigma2 / sxx, 0.0))
    r_squared = 1 - residual_sum / syy if syy else 0.0
    return (
        slope,
        se,
        slope - 1.96 * se,
        slope + 1.96 * se,
        r_squared,
        intercept,
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _sample_sd(values: list[float]) -> float:
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _format_float(value: float) -> str:
    return format(Decimal(str(value)), "f")


def _effective_curve_bp(
    *,
    curve_5y: Decimal | None,
    curve_10y: Decimal | None,
    curve_30y: Decimal | None,
    weight_5y: Decimal,
    weight_10y: Decimal,
    weight_30y: Decimal,
) -> Decimal | None:
    if curve_5y is None or curve_10y is None or curve_30y is None:
        return None
    if weight_5y + weight_10y + weight_30y != Decimal("1"):
        return None
    return curve_5y * weight_5y + curve_10y * weight_10y + curve_30y * weight_30y


def _pass_or_status(condition: bool, blocked_status: str) -> str:
    return "pass" if condition else blocked_status


def _decimal_or_none(value: object) -> Decimal | None:
    if value in {None, ""}:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _decimal_or_default(value: object, default: Decimal) -> Decimal:
    parsed = _decimal_or_none(value)
    if parsed is None:
        return default
    return parsed


def _format_decimal_or_blank(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value.normalize(), "f")
