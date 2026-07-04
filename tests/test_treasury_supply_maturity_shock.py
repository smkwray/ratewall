from __future__ import annotations

import math
from zipfile import ZipFile

import pandas as pd

from ratewall.databook.treasury_supply_maturity_shock import (
    PHILLOT_DAILY_YIELD_BRIDGE_FIELDS,
    TREASURY_SUPPLY_MATURITY_SHOCK_COEFFICIENT_ADMISSION_FIELDS,
    PHILLOT_TREASURY_AUCTION_INSTRUMENT_FIELDS,
    TREASURY_SUPPLY_MATURITY_SHOCK_PACKAGE_AUDIT_FIELDS,
    TREASURY_SUPPLY_MATURITY_SHOCK_PATH_OBJECT_FIELDS,
    TREASURY_SUPPLY_MATURITY_SHOCK_SOURCE_INVENTORY_FIELDS,
    official_fspdp_gdp_panel_rows,
    phillot_daily_yield_bridge_rows,
    phillot_package_schema_audit_rows,
    phillot_treasury_auction_instrument_rows,
    treasury_event_window_yield_path_object_rows,
    treasury_supply_maturity_h4_fspdp_response_rows,
    treasury_supply_maturity_path_objects_with_h4_response,
    treasury_supply_maturity_shock_coefficient_admission_rows,
    treasury_supply_maturity_shock_path_object_rows,
    treasury_supply_maturity_shock_source_inventory_rows,
    write_phillot_daily_yield_bridge_csv,
)


def test_source_inventory_is_review_only_and_fail_closed() -> None:
    rows = treasury_supply_maturity_shock_source_inventory_rows()

    assert len(rows) == 5
    assert {field for row in rows for field in row} == set(
        TREASURY_SUPPLY_MATURITY_SHOCK_SOURCE_INVENTORY_FIELDS
    )
    assert {
        "phillot_2025_aea_treasury_auction_supply_shocks",
        "bi_phillot_zubairy_2026_kc_fed_rwp_26_04",
        "treasurydirect_auction_announcements_results",
        "fiscaldata_monthly_statement_public_debt_mspd",
        "li_wei_greenwood_vayanos_supply_factor_validation",
    } == {row["source_id"] for row in rows}
    assert {row["admission_status"] for row in rows} == {
        "source_inventory_only_not_path_object"
    }
    phillot = {
        row["source_id"]: row for row in rows
    }["phillot_2025_aea_treasury_auction_supply_shocks"]
    assert phillot["source_package_id"] == "openicpsr_192741_v1"
    assert phillot["source_package_doi"] == "10.3886/E192741V1"
    assert phillot["source_access_status"] == (
        "owner_download_acquired_local_package_schema_audited_not_path_ready"
    )
    assert phillot["shock_series_schema_verified"] == (
        "pass_downloaded_schema_contains_2y_5y_10y_30y_normalized_returns"
    )
    assert phillot["has_effective_curve_bridge"] == (
        "blocked_no_yield_equivalent_bp_conversion"
    )
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["denominator_prior_update_allowed"] for row in rows} == {"false"}


def test_phillot_package_audit_fails_closed_when_zip_missing(tmp_path) -> None:
    rows = phillot_package_schema_audit_rows(tmp_path / "missing.zip")

    assert len(rows) == 1
    assert set(rows[0]) == set(TREASURY_SUPPLY_MATURITY_SHOCK_PACKAGE_AUDIT_FIELDS)
    assert rows[0]["package_present"] == "false"
    assert rows[0]["package_read_status"] == "blocked_package_missing"
    assert rows[0]["source_admission_status"] == "blocked_not_checked"
    assert rows[0]["canonical_ratio_entry"] == "false"
    assert rows[0]["enters_main_ratio"] == "false"


def test_phillot_package_audit_reads_shock_schema_but_blocks_path_rows(tmp_path) -> None:
    package = _phillot_fixture_zip(tmp_path)

    rows = phillot_package_schema_audit_rows(package)

    assert len(rows) == 1
    row = rows[0]
    assert set(row) == set(TREASURY_SUPPLY_MATURITY_SHOCK_PACKAGE_AUDIT_FIELDS)
    assert row["package_present"] == "true"
    assert row["package_read_status"] == "pass_zip_readable"
    assert row["required_files_missing"] == ""
    assert row["shock_file_read_status"] == "pass_stata_readable"
    assert row["shock_row_count"] == "3"
    assert row["shock_date_min"] == "1998-10-21"
    assert row["shock_date_max"] == "1998-10-28"
    assert row["shock_columns_present"] == (
        "n_2y_m5_p29;n_5y_m5_p29;n_10y_m5_p29;n_30y_m5_p29"
    )
    assert row["shock_nonmissing_observation_count_min"] == "2"
    assert row["event_window"] == "m5_p29"
    assert row["announcement_timestamp_read_status"] == "pass_stata_readable"
    assert row["announcement_timestamp_count"] == "2"
    assert row["tenor_2y_5y_10y_30y_status"] == (
        "pass_native_2y_5y_10y_30y_normalized_futures_returns"
    )
    assert row["yield_equivalent_bp_conversion_status"] == (
        "blocked_native_units_are_normalized_futures_log_returns_not_yield_bp"
    )
    assert row["effective_curve_bridge_status"] == (
        "blocked_no_100bp_year_effective_curve_bridge"
    )
    assert row["source_admission_status"] == "source_schema_verified_not_path_object"
    assert row["canonical_ratio_entry"] == "false"
    assert row["enters_main_ratio"] == "false"


def test_phillot_instrument_rows_are_noncanonical_and_not_path_rows(tmp_path) -> None:
    package = _phillot_fixture_zip(tmp_path)

    rows = phillot_treasury_auction_instrument_rows(package)

    assert len(rows) == 2
    assert {field for row in rows for field in row} == set(
        PHILLOT_TREASURY_AUCTION_INSTRUMENT_FIELDS
    )
    pre_sample, in_sample = rows
    assert pre_sample["event_date"] == "1998-10-21"
    assert pre_sample["in_analysis_sample"] == "false"
    assert in_sample["event_date"] == "1998-10-28"
    assert in_sample["in_analysis_sample"] == "true"
    assert in_sample["announcement_timestamp_status"] == (
        "pass_announcement_timestamp_matched"
    )
    assert in_sample["announcement_hour"] == "9"
    assert in_sample["announcement_minute"] == "30"
    assert in_sample["event_window"] == "m5_p29"
    assert in_sample["shock_unit"] == (
        "standardized_negative_treasury_futures_log_return"
    )
    assert in_sample["native_unit"] == "unitless_sample_standard_deviation"
    assert in_sample["n_2y_m5_p29"] == "1"
    assert in_sample["raw_event_window_return_available"] == "false"
    assert in_sample["yield_bp_equivalent_available"] == "false"
    assert in_sample["effective_curve_100bp_year_available"] == "false"
    assert in_sample["path_object_admission_status"] == (
        "blocked_not_a_yield_bp_or_100bp_year_path"
    )
    assert in_sample["allowed_use"] == "noncanonical_lp_iv_instrument_research_only"
    assert in_sample["canonical_ratio_entry"] == "false"
    assert in_sample["enters_main_ratio"] == "false"
    assert in_sample["denominator_prior_update_allowed"] == "false"
    assert "yield_bp_path" in in_sample["blocked_use"]
    assert "100bp_year_path" in in_sample["blocked_use"]


def test_phillot_daily_yield_bridge_is_scale_check_not_admission(tmp_path) -> None:
    package = _phillot_yield_bridge_fixture_zip(tmp_path)

    rows = phillot_daily_yield_bridge_rows(package)

    assert len(rows) == 4
    assert {field for row in rows for field in row} == set(
        PHILLOT_DAILY_YIELD_BRIDGE_FIELDS
    )
    by_tenor = {row["tenor"]: row for row in rows}
    assert by_tenor["5y"]["event_count"] == "3"
    assert by_tenor["5y"]["slope_bp_per_normalized_shock"] == "2.0"
    assert by_tenor["10y"]["slope_bp_per_normalized_shock"] == "3.0"
    assert by_tenor["30y"]["slope_bp_per_normalized_shock"] == "4.0"
    assert {row["same_source_package_status"] for row in rows} == {
        "pass_shock_and_daily_yield_series_from_openicpsr_package"
    }
    assert {row["event_window_alignment_status"] for row in rows} == {
        "blocked_daily_close_not_m5_p29_high_frequency_event_window"
    }
    assert {row["admission_status"] for row in rows} == {
        "not_admitted_daily_yield_bridge_diagnostic_only"
    }
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["denominator_prior_update_allowed"] for row in rows} == {"false"}


def test_phillot_daily_yield_bridge_writer_uses_stable_schema(tmp_path) -> None:
    rows = phillot_daily_yield_bridge_rows(_phillot_yield_bridge_fixture_zip(tmp_path))

    output = write_phillot_daily_yield_bridge_csv(tmp_path / "bridge.csv", rows)

    assert output.read_text(encoding="utf-8").startswith("bridge_row_id,")
    with output.open(encoding="utf-8", newline="") as handle:
        written = list(pd.read_csv(handle).to_dict("records"))
    assert len(written) == 4


def test_path_object_schema_is_empty_until_candidate_rows_exist() -> None:
    rows = treasury_supply_maturity_shock_path_object_rows()
    admission = treasury_supply_maturity_shock_coefficient_admission_rows(rows)

    assert rows == []
    assert set(admission[0]) == set(
        TREASURY_SUPPLY_MATURITY_SHOCK_COEFFICIENT_ADMISSION_FIELDS
    )
    assert admission[0]["path_object_candidate_count"] == "0"
    assert admission[0]["path_object_pass_count"] == "0"
    assert admission[0]["admitted_denominator_response_coefficient"] == ""
    assert admission[0]["coefficient_admission_status"] == (
        "no_admitted_denominator_response_coefficient"
    )
    assert "no_treasury_supply_maturity_shock_path_rows" in admission[0][
        "exact_blocker"
    ]
    assert admission[0]["canonical_ratio_entry"] == "false"
    assert admission[0]["enters_main_ratio"] == "false"


def test_event_window_yield_path_candidate_can_pass_existing_gate() -> None:
    rows = treasury_event_window_yield_path_object_rows(
        [_event_window_candidate_fixture()]
    )
    admission = treasury_supply_maturity_shock_coefficient_admission_rows(rows)

    row = rows[0]
    assert row["admission_status"] == (
        "admitted_treasury_supply_maturity_shock_path_object"
    )
    assert row["curve_5y_bp"] == "80"
    assert row["curve_10y_bp"] == "100"
    assert row["curve_30y_bp"] == "120"
    assert row["effective_curve_overlay_bp"] == "100"
    assert row["path_bps_year"] == "100"
    assert row["normalized_100bp_year_value"] == "1"
    assert row["yield_equivalent_bp_conversion_status"] == "pass"
    assert admission[0]["coefficient_admission_status"] == (
        "admitted_noncanonical_treasury_supply_maturity_coefficient"
    )
    assert admission[0]["admitted_denominator_response_coefficient"] == "-0.2"


def test_daily_yield_bridge_rows_cannot_be_promoted_to_event_window_path(
    tmp_path,
) -> None:
    daily_rows = phillot_daily_yield_bridge_rows(
        _phillot_yield_bridge_fixture_zip(tmp_path)
    )

    rows = treasury_event_window_yield_path_object_rows(daily_rows)

    assert len(rows) == 4
    assert {row["admission_status"] for row in rows} == {"candidate_only_blocked"}
    assert {row["yield_equivalent_bp_conversion_status"] for row in rows} == {
        "blocked_source_yield_unit_not_event_window_basis_points"
    }
    assert {row["effective_curve_overlay_bp"] for row in rows} == {""}
    assert all("yield_equivalent_bp_conversion" in row["exact_blocker"] for row in rows)
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["denominator_prior_update_allowed"] for row in rows} == {"false"}


def test_event_window_candidate_blocks_bad_effective_curve_weights() -> None:
    candidate = _event_window_candidate_fixture()
    candidate["effective_curve_weight_5y"] = "0.50"
    candidate["effective_curve_weight_10y"] = "0.50"
    candidate["effective_curve_weight_30y"] = "0.50"

    row = treasury_event_window_yield_path_object_rows([candidate])[0]

    assert row["admission_status"] == "candidate_only_blocked"
    assert row["effective_curve_overlay_bp"] == ""
    assert row["effective_curve_bridge_status"] == (
        "blocked_missing_curve_tenors_or_weights_not_sum_one"
    )
    assert row["normalized_100bp_year_value"] == ""
    assert "effective_curve_bridge" in row["exact_blocker"]


def test_event_window_candidate_accepts_explicit_zero_curve_weights() -> None:
    candidate = _event_window_candidate_fixture()
    candidate["effective_curve_weight_5y"] = "0"
    candidate["effective_curve_weight_10y"] = "1"
    candidate["effective_curve_weight_30y"] = "0"

    row = treasury_event_window_yield_path_object_rows([candidate])[0]

    assert row["admission_status"] == (
        "admitted_treasury_supply_maturity_shock_path_object"
    )
    assert row["effective_curve_overlay_bp"] == "100"
    assert row["path_bps_year"] == "100"


def test_official_fspdp_gdp_panel_reads_local_sources() -> None:
    rows = official_fspdp_gdp_panel_rows()

    assert len(rows) > 250
    assert {"nominal_fspdp", "real_fspdp", "nominal_gdp", "real_gdp"} <= set(rows[0])
    assert rows[0]["quarter"].endswith("Q1")
    assert rows[-1]["nominal_fspdp"]
    assert rows[-1]["real_gdp"]


def test_h4_fspdp_response_enriches_path_objects_and_admits_coefficient() -> None:
    candidates = [
        _event_window_candidate_without_h4(_quarter_label(1990 * 4 + 10 + index * 8), index)
        for index in range(20)
    ]
    initial_paths = treasury_event_window_yield_path_object_rows(candidates)
    response = treasury_supply_maturity_h4_fspdp_response_rows(
        initial_paths,
        _linear_h4_fspdp_panel_rows(),
    )
    enriched_paths = treasury_supply_maturity_path_objects_with_h4_response(
        initial_paths,
        response,
    )
    admission = treasury_supply_maturity_shock_coefficient_admission_rows(
        enriched_paths
    )

    assert {row["admission_status"] for row in initial_paths} == {
        "candidate_only_blocked"
    }
    assert response[0]["admission_status"] == (
        "pass_h4_fspdp_response_for_noncanonical_path_gate"
    )
    assert math.isclose(float(response[0]["beta_per_100bp_year"]), -0.3)
    assert response[0]["h4_ci_status"] == "pass"
    assert response[0]["gdp_robustness_status"] == "pass"
    assert response[0]["sample_robustness_status"] == "pass"
    assert response[0]["placebo_leads_pretrend_status"] == "pass"
    assert {row["admission_status"] for row in enriched_paths} == {
        "admitted_treasury_supply_maturity_shock_path_object"
    }
    assert admission[0]["coefficient_admission_status"] == (
        "admitted_noncanonical_treasury_supply_maturity_coefficient"
    )
    assert math.isclose(
        float(admission[0]["admitted_denominator_response_coefficient"]),
        -0.3,
    )


def test_h4_fspdp_response_blocks_without_usable_event_window_paths() -> None:
    response = treasury_supply_maturity_h4_fspdp_response_rows(
        [],
        _linear_h4_fspdp_panel_rows(),
    )

    assert response[0]["admission_status"] == "blocked_h4_fspdp_response"
    assert response[0]["usable_observation_count"] == "0"
    assert "no_treasury_supply_maturity_path_rows" in response[0]["exact_blocker"]
    assert response[0]["canonical_ratio_entry"] == "false"
    assert response[0]["denominator_prior_update_allowed"] == "false"


def _phillot_fixture_zip(tmp_path):
    package_root = tmp_path / "package"
    package_root.mkdir()
    for relative in (
        "data",
        "do",
        "raw_public/TreasuryDirect",
    ):
        (package_root / relative).mkdir(parents=True, exist_ok=True)
    for relative in (
        "README.pdf",
        "data/1_Financial.dta",
        "data/2_Treasury_data.dta",
        "data/3_Treasury_dummies.dta",
        "data/4_bis_Placebo_shocks.dta",
        "data/5_News_FOMC.dta",
        "do/master.do",
        "do/data_prep.do",
        "do/compute.do",
    ):
        target = package_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix == ".dta":
            pd.DataFrame({"date": pd.to_datetime(["2020-01-01"])}).to_stata(
                target,
                write_index=False,
            )
        else:
            target.write_text("fixture", encoding="utf-8")
    pd.DataFrame(
        {
            "date": pd.to_datetime(["1998-10-21", "1998-10-22", "1998-10-28"]),
            "n_2y_m5_p29": [0.5, None, 1.0],
            "n_5y_m5_p29": [0.5, None, 1.0],
            "n_10y_m5_p29": [0.5, None, 1.0],
            "n_30y_m5_p29": [0.5, None, 1.0],
        }
    ).to_stata(
        package_root / "data/4_Treasury_supply_shocks.dta",
        write_index=False,
        variable_labels={
            "n_2y_m5_p29": "Normalized 2y-futures log-return, m5_p29",
            "n_5y_m5_p29": "Normalized 5y-futures log-return, m5_p29",
            "n_10y_m5_p29": "Normalized 10y-futures log-return, m5_p29",
            "n_30y_m5_p29": "Normalized 30y-futures log-return, m5_p29",
        },
    )
    pd.DataFrame(
        {
            "date": pd.to_datetime(["1998-10-21", "1998-10-28"]),
            "hour": [14.0, 9.0],
            "minute": [0.0, 30.0],
        }
    ).to_stata(
        package_root / "raw_public/TreasuryDirect/announcement_timestamps.dta",
        write_index=False,
    )
    package = tmp_path / "192741-V1.zip"
    with ZipFile(package, "w") as archive:
        for path in package_root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(package_root))
    return package


def _phillot_yield_bridge_fixture_zip(tmp_path):
    package_root = tmp_path / "bridge_package"
    package_root.mkdir()
    for relative in (
        "data",
        "do",
        "raw_public/TreasuryDirect",
    ):
        (package_root / relative).mkdir(parents=True, exist_ok=True)
    for relative in (
        "README.pdf",
        "data/2_Treasury_data.dta",
        "data/3_Treasury_dummies.dta",
        "data/4_bis_Placebo_shocks.dta",
        "data/5_News_FOMC.dta",
        "do/master.do",
        "do/data_prep.do",
        "do/compute.do",
        "raw_public/TreasuryDirect/announcement_timestamps.dta",
    ):
        target = package_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix == ".dta":
            pd.DataFrame({"date": pd.to_datetime(["2020-01-01"])}).to_stata(
                target,
                write_index=False,
            )
        else:
            target.write_text("fixture", encoding="utf-8")
    dates = pd.to_datetime(
        ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-06"]
    )
    pd.DataFrame(
        {
            "date": dates,
            "n_2y_m5_p29": [None, 1.0, 2.0, 3.0],
            "n_5y_m5_p29": [None, 1.0, 2.0, 3.0],
            "n_10y_m5_p29": [None, 1.0, 2.0, 3.0],
            "n_30y_m5_p29": [None, 1.0, 2.0, 3.0],
        }
    ).to_stata(
        package_root / "data/4_Treasury_supply_shocks.dta",
        write_index=False,
    )
    pd.DataFrame(
        {
            "date": dates,
            "r2y_fred": [100.0, 101.0, 103.0, 106.0],
            "r5y_fred": [100.0, 102.0, 106.0, 112.0],
            "r10y_fred": [100.0, 103.0, 109.0, 118.0],
            "r30y_fred": [100.0, 104.0, 112.0, 124.0],
        }
    ).to_stata(
        package_root / "data/1_Financial.dta",
        write_index=False,
    )
    package = tmp_path / "yield-bridge.zip"
    with ZipFile(package, "w") as archive:
        for path in package_root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(package_root))
    return package


def test_incomplete_candidate_cannot_self_admit() -> None:
    rows = treasury_supply_maturity_shock_path_object_rows(
        [
            {
                "candidate_id": "candidate::bad",
                "shock_family": "mixed_treasury_supply_shock",
                "admission_status": "admitted_treasury_supply_maturity_shock_path_object",
                "effective_curve_overlay_bp": "25",
                "horizon_weight_years": "1",
            }
        ]
    )
    row = rows[0]

    assert set(row) == set(TREASURY_SUPPLY_MATURITY_SHOCK_PATH_OBJECT_FIELDS)
    assert row["admission_status"] == "candidate_only_blocked"
    assert row["path_bps_year"] == "25"
    assert row["normalized_100bp_year_value"] == "0.25"
    assert "shock_family_not_separately_identified" in row["exact_blocker"]
    assert "source_acquisition" in row["exact_blocker"]
    assert row["canonical_ratio_entry"] == "false"
    assert row["enters_main_ratio"] == "false"


def test_full_gate_candidate_is_noncanonical_only() -> None:
    candidate = {
        "candidate_id": "candidate::full_gate",
        "shock_family": "treasury_maturity_extension_shock",
        "source_id": "bi_phillot_zubairy_2026_kc_fed_rwp_26_04",
        "source_event_id": "event::1",
        "event_date": "2020-01-01",
        "quarter": "2020Q1",
        "event_window": "source_defined_hf_window",
        "effective_curve_overlay_bp": "100",
        "horizon_weight_years": "1",
        "h4_fspdp_beta_per_100bp_year": "-0.2",
        "h4_fspdp_ci95_low": "-0.4",
        "h4_fspdp_ci95_high": "-0.1",
    }
    for field in (
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
        "h4_ci_status",
        "gdp_robustness_status",
        "sample_robustness_status",
        "placebo_leads_pretrend_status",
        "scenario_overlay_shape_bridge_status",
    ):
        candidate[field] = "pass"

    rows = treasury_supply_maturity_shock_path_object_rows([candidate])
    admission = treasury_supply_maturity_shock_coefficient_admission_rows(rows)

    assert rows[0]["admission_status"] == (
        "admitted_treasury_supply_maturity_shock_path_object"
    )
    assert rows[0]["normalized_100bp_year_value"] == "1"
    assert rows[0]["canonical_ratio_entry"] == "false"
    assert rows[0]["enters_main_ratio"] == "false"
    assert admission[0]["coefficient_admission_status"] == (
        "admitted_noncanonical_treasury_supply_maturity_coefficient"
    )
    assert admission[0]["admitted_denominator_response_coefficient"] == "-0.2"
    assert admission[0]["canonical_ratio_entry"] == "false"
    assert admission[0]["enters_main_ratio"] == "false"


def _event_window_candidate_fixture() -> dict[str, str]:
    candidate = {
        "candidate_id": "event_window_candidate::good",
        "shock_family": "treasury_debt_expansion_shock",
        "source_id": "phillot_author_or_market_data_event_window_bridge",
        "source_event_id": "event::2020-01-01",
        "event_date": "2020-01-01",
        "quarter": "2020Q1",
        "event_window": "m5_p29",
        "source_vintage": "fixture",
        "source_publisher": "fixture",
        "source_yield_unit": "basis_points_event_window",
        "source_shock_value": "1",
        "curve_5y_bp": "80",
        "curve_10y_bp": "100",
        "curve_30y_bp": "120",
        "effective_curve_weight_5y": "0.25",
        "effective_curve_weight_10y": "0.50",
        "effective_curve_weight_30y": "0.25",
        "horizon_weight_years": "1",
        "h4_fspdp_beta_per_100bp_year": "-0.2",
        "h4_fspdp_ci95_low": "-0.4",
        "h4_fspdp_ci95_high": "-0.1",
    }
    for field in (
        "source_acquisition_status",
        "event_window_timestamp_status",
        "independent_replication_status",
        "shock_family_declared_status",
        "mixed_shock_separation_status",
        "first_stage_relevance_status",
        "h4_fspdp_estimate_status",
        "h4_ci_status",
        "gdp_robustness_status",
        "sample_robustness_status",
        "placebo_leads_pretrend_status",
        "scenario_overlay_shape_bridge_status",
    ):
        candidate[field] = "pass"
    return candidate


def _event_window_candidate_without_h4(quarter: str, index: int) -> dict[str, str]:
    exposure_bp = "50" if index % 2 == 0 else "150"
    candidate = _event_window_candidate_fixture()
    candidate["candidate_id"] = f"event_window_candidate::{quarter}"
    candidate["source_event_id"] = f"event::{quarter}"
    candidate["event_date"] = _quarter_start_date(quarter)
    candidate["quarter"] = quarter
    candidate["curve_5y_bp"] = exposure_bp
    candidate["curve_10y_bp"] = exposure_bp
    candidate["curve_30y_bp"] = exposure_bp
    for field in (
        "h4_fspdp_beta_per_100bp_year",
        "h4_fspdp_ci95_low",
        "h4_fspdp_ci95_high",
        "h4_fspdp_estimate_status",
        "h4_ci_status",
        "gdp_robustness_status",
        "sample_robustness_status",
        "placebo_leads_pretrend_status",
    ):
        candidate.pop(field, None)
    return candidate


def _linear_h4_fspdp_panel_rows() -> list[dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for index in range(1990 * 4, 1990 * 4 + 190):
        rows[_quarter_label(index)] = {
            "quarter": _quarter_label(index),
            "nominal_fspdp": "50",
            "real_fspdp": "100",
            "nominal_gdp": "1000",
            "real_gdp": "2000",
        }
    for event_index in range(20):
        quarter_index = 1990 * 4 + 10 + event_index * 8
        exposure = 0.5 if event_index % 2 == 0 else 1.5
        noise = 0.005 if event_index % 4 in {0, 1} else -0.005
        outcome = -0.3 * exposure + noise
        future_index = quarter_index + 4
        future_real_fspdp = 100 * math.exp(outcome / 5)
        future_nominal_fspdp = 50 + outcome * 10
        rows[_quarter_label(future_index)]["real_fspdp"] = str(future_real_fspdp)
        rows[_quarter_label(future_index)]["nominal_fspdp"] = str(
            future_nominal_fspdp
        )
    return [rows[quarter] for quarter in sorted(rows)]


def _quarter_label(index: int) -> str:
    year, offset = divmod(index, 4)
    return f"{year}Q{offset + 1}"


def _quarter_start_date(quarter: str) -> str:
    year = quarter[:4]
    month = {"1": "01", "2": "04", "3": "07", "4": "10"}[quarter[-1]]
    return f"{year}-{month}-01"
