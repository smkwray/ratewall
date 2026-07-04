from __future__ import annotations

from ratewall.databook.denominator_response_path_object import (
    DENOMINATOR_RESPONSE_COEFFICIENT_ADMISSION_FIELDS,
    DENOMINATOR_RESPONSE_PATH_OBJECT_FIELDS,
    denominator_response_coefficient_admission_rows,
    denominator_response_curve_path_object_rows,
    denominator_response_curve_path_object_rows_from_local_suite,
    denominator_response_path_object_registry_rows_from_local_sources,
    denominator_response_path_object_rows,
)


def test_path_object_rows_are_candidate_only() -> None:
    rows = denominator_response_path_object_rows(_event_rows())

    assert len(rows) == 2
    assert {field for row in rows for field in row} == set(
        DENOMINATOR_RESPONSE_PATH_OBJECT_FIELDS
    )
    assert {row["shock_object_kind"] for row in rows} == {
        "policy_path_100bp_year_candidate"
    }
    assert {row["instrument_set"] for row in rows} == {"ED1;ED2;ED3;ED4"}
    assert {row["admission_status"] for row in rows} == {"candidate_only_blocked"}
    assert {row["source_horizon_label_summary"] for row in rows} == {
        "ED1=current_quarter_money_market_futures;"
        "ED2=next_quarter_money_market_futures;"
        "ED3=two_quarter_ahead_money_market_futures;"
        "ED4=three_quarter_ahead_money_market_futures"
    }
    assert {row["horizon_mapping_status"] for row in rows} == {
        "blocked_slot_labels_reviewed_but_no_event_date_specific_horizon_grid"
    }
    assert {row["horizon_weight_years"] for row in rows} == {""}
    assert {row["path_bps_year"] for row in rows} == {""}
    assert {row["source_unit"] for row in rows} == {
        "derived_unweighted_ed_slot_sum_percentage_point_rate_change_30_min_window_"
        "not_sf_fed_mps"
    }
    assert {row["source_unit_conversion_status"] for row in rows} == {
        "pass_reviewed_percentage_point_rate_change_source_text"
    }
    assert [row["converted_bp"] for row in rows] == ["2", "-4"]
    assert {row["normalized_100bp_year_value"] for row in rows} == {""}
    assert {row["normalization_status"] for row in rows} == {
        "blocked_no_admitted_bps_year_policy_path"
    }
    assert {row["denominator_response_requirement"] for row in rows} == {
        "blocked_until_reviewed_path_and_admitted_coefficient"
    }
    assert {row["future_denominator_update_status"] for row in rows} == {
        "policy_path_candidate_not_ready_for_denominator_update"
    }
    assert {row["canonical_promotion_gate"] for row in rows} == {
        "requires_reviewed_100bp_year_path_and_admitted_denominator_"
        "response_coefficient"
    }
    assert {row["information_shock_filter_status"] for row in rows} == {
        "blocked_no_information_shock_filter"
    }
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["denominator_prior_update_allowed"] for row in rows} == {"false"}
    assert rows[0]["source_scalar_value"] == "0.02"
    assert rows[1]["source_scalar_value"] == "-0.04"


def test_path_object_rows_exclude_incomplete_event_strips() -> None:
    incomplete = [
        row
        for row in _event_rows()
        if not (
            row["event_id"] == "update_2023::0002::2000-02-01"
            and row["instrument_code"] == "ED4"
        )
    ]

    rows = denominator_response_path_object_rows(incomplete)

    assert len(rows) == 1
    assert rows[0]["source_event_id"] == "update_2023::0001::2000-01-01"


def test_curve_path_object_rows_are_assumption_only() -> None:
    rows = denominator_response_curve_path_object_rows(_curve_input_rows())

    assert len(rows) == 2
    assert {field for row in rows for field in row} == set(
        DENOMINATOR_RESPONSE_PATH_OBJECT_FIELDS
    )
    baseline, shorter = rows
    assert baseline["shock_object_kind"] == "curve_path_100bp_year_assumption_candidate"
    assert baseline["path_bps_year"] == "0"
    assert baseline["normalized_100bp_year_value"] == "0"
    assert baseline["denominator_response_requirement"] == (
        "not_required_zero_curve_overlay"
    )
    assert baseline["future_denominator_update_status"] == (
        "zero_rate_path_frozen_D_consistent"
    )
    assert shorter["source_event_id"] == "shorter_central"
    assert shorter["instrument_set"] == "5y;10y;30y"
    assert shorter["instruments_present"] == "5y;10y;30y"
    assert shorter["source_horizon_label_summary"] == (
        "5y_weight=0.25;10y_weight=0.5;30y_weight=0.25"
    )
    assert shorter["source_unit"] == "basis_point_nominal_treasury_key_rate_overlay"
    assert shorter["source_scalar_value"] == "-7"
    assert shorter["converted_bp"] == "-7"
    assert shorter["horizon_weight_years"] == "1"
    assert shorter["path_bps_year"] == "-7"
    assert shorter["normalized_100bp_year_value"] == "-0.07"
    assert shorter["normalization_status"] == (
        "pass_assumption_mode_100bp_year_curve_path_not_empirical"
    )
    assert shorter["admission_status"] == "assumption_path_only_not_empirical"
    assert shorter["denominator_response_requirement"] == (
        "required_before_canonical_promotion"
    )
    assert shorter["future_denominator_update_status"] == (
        "rate_shock_captured_coefficient_not_admitted"
    )
    assert shorter["canonical_promotion_gate"] == (
        "requires_admitted_curve_denominator_response_coefficient_or_"
        "explicit_zero_response_proof"
    )
    assert shorter["allowed_use"] == "curve_path_assumption_bounds_only"
    assert shorter["canonical_ratio_entry"] == "false"
    assert shorter["enters_main_ratio"] == "false"
    assert shorter["denominator_prior_update_allowed"] == "false"


def test_current_manifest_suite_curve_paths_mark_nonzero_rate_scenarios() -> None:
    rows = denominator_response_curve_path_object_rows_from_local_suite()

    assert len(rows) == 11
    by_scenario = {row["source_event_id"]: row for row in rows}
    baseline = by_scenario["cbo_baseline_noop_v1"]
    assert baseline["path_bps_year"] == "0"
    assert baseline["denominator_response_requirement"] == (
        "not_required_zero_curve_overlay"
    )

    shorter = by_scenario[
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1"
    ]
    assert shorter["converted_bp"] == "-7"
    assert shorter["denominator_response_requirement"] == (
        "required_before_canonical_promotion"
    )
    assert shorter["future_denominator_update_status"] == (
        "rate_shock_captured_coefficient_not_admitted"
    )
    assert "denominator_recalibration" in shorter["blocked_use"]
    assert {
        row["denominator_response_requirement"]
        for row in rows
        if row["path_bps_year"] != "0"
    } == {"required_before_canonical_promotion"}
    assert len([row for row in rows if row["path_bps_year"] != "0"]) == 6


def test_local_registry_builder_combines_policy_and_curve_paths(tmp_path) -> None:
    event_path = tmp_path / "events.csv"
    curve_path = tmp_path / "curve.csv"
    _write_rows(event_path, _event_rows())
    _write_rows(curve_path, _curve_input_rows())

    rows = denominator_response_path_object_registry_rows_from_local_sources(
        event_vector_path=event_path,
        curve_denominator_input_path=curve_path,
    )

    assert len(rows) == 4
    assert {row["shock_object_kind"] for row in rows} == {
        "policy_path_100bp_year_candidate",
        "curve_path_100bp_year_assumption_candidate",
    }
    assert {row["admission_status"] for row in rows} == {
        "candidate_only_blocked",
        "assumption_path_only_not_empirical",
    }


def test_coefficient_admission_fails_without_reviewed_path_object() -> None:
    path_rows = [
        *denominator_response_path_object_rows(_event_rows()),
        *denominator_response_curve_path_object_rows(_curve_input_rows()),
    ]
    admission_rows = denominator_response_coefficient_admission_rows(
        diagnostic_rows=[
            {
                "horizon_q": "4",
                "outcome_object_id": (
                    "share_weighted_real_fspdp_level_response_gdp_share_pp"
                ),
                "ci95_low_hac": "-1.0",
                "ci95_high_hac": "0.5",
            },
            {
                "horizon_q": "8",
                "outcome_object_id": (
                    "share_weighted_real_fspdp_level_response_gdp_share_pp"
                ),
                "ci95_low_hac": "-2.0",
                "ci95_high_hac": "0.1",
            },
        ],
        path_object_rows=path_rows,
    )

    assert len(admission_rows) == 1
    row = admission_rows[0]
    assert set(row) == set(DENOMINATOR_RESPONSE_COEFFICIENT_ADMISSION_FIELDS)
    assert row["path_object_candidate_count"] == "4"
    assert row["path_object_pass_count"] == "0"
    assert row["primary_diagnostic_count"] == "1"
    assert row["primary_zero_crossing_count"] == "1"
    assert row["admitted_denominator_response_coefficient"] == ""
    assert row["coefficient_admission_status"] == (
        "no_admitted_denominator_response_coefficient"
    )
    assert "no_reviewed_100bp_year_path_object" in row["exact_blocker"]
    assert "primary_h4_confidence_interval_crosses_zero" in row["exact_blocker"]
    assert row["canonical_ratio_entry"] == "false"
    assert row["enters_main_ratio"] == "false"


def test_coefficient_admission_requires_primary_h4_diagnostic() -> None:
    rows = denominator_response_coefficient_admission_rows(
        diagnostic_rows=[],
        path_object_rows=[],
    )

    assert rows[0]["coefficient_admission_status"] == (
        "no_admitted_denominator_response_coefficient"
    )
    assert "no_primary_h4_share_weighted_fspdp_diagnostic" in rows[0][
        "exact_blocker"
    ]


def _event_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    event_specs = [
        ("update_2023::0001::2000-01-01", "2000-01-01", ["0.01", "0.02", "0", "-0.01"]),
        ("update_2023::0002::2000-02-01", "2000-02-01", ["-0.02", "-0.01", "0", "-0.01"]),
    ]
    for event_id, event_date, values in event_specs:
        for instrument, value in zip(("ED1", "ED2", "ED3", "ED4"), values):
            horizon_labels = {
                "ED1": "current_quarter_money_market_futures",
                "ED2": "next_quarter_money_market_futures",
                "ED3": "two_quarter_ahead_money_market_futures",
                "ED4": "three_quarter_ahead_money_market_futures",
            }
            rows.append(
                {
                    "source_sheet_vintage": "update_2023",
                    "instrument_code": instrument,
                    "event_id": event_id,
                    "event_date": event_date,
                    "source_publisher": "Federal Reserve Bank of San Francisco",
                    "source_horizon_label": horizon_labels[instrument],
                    "source_reported_value_numeric": value,
                    "unit_conversion_status": (
                        "blocked_no_reviewed_source_unit_conversion"
                    ),
                    "horizon_mapping_status": (
                        "blocked_no_reviewed_event_date_specific_horizon_grid"
                    ),
                    "bps_year_integral_status": (
                        "blocked_no_reviewed_bps_year_integral_formula"
                    ),
                    "replication_status": "blocked_no_independent_replication",
                    "policy_path_100bp_year_normalization_status": (
                        "blocked_no_admitted_bps_year_policy_path"
                    ),
                }
            )
    rows.append(
        {
            "source_sheet_vintage": "update_2023",
            "instrument_code": "FF1",
            "event_id": "update_2023::0003::2000-03-01",
            "event_date": "2000-03-01",
            "source_reported_value_numeric": "0.5",
        }
    )
    rows.append(
        {
            "source_sheet_vintage": "legacy",
            "instrument_code": "ED1",
            "event_id": "legacy::0001::1999-01-01",
            "event_date": "1999-01-01",
            "source_reported_value_numeric": "0.5",
        }
    )
    return rows


def _curve_input_rows() -> list[dict[str, str]]:
    base = {
        "fiscal_year": "2027",
        "curve_weight_5y": "0.25",
        "curve_weight_10y": "0.5",
        "curve_weight_30y": "0.25",
    }
    return [
        {
            **base,
            "scenario_id": "baseline",
            "curve_overlay_5y_bp": "0",
            "curve_overlay_10y_bp": "0",
            "curve_overlay_30y_bp": "0",
            "effective_curve_overlay_bp": "0",
            "curve_overlay_key_rate_source_status": (
                "pass_zero_overlay_from_scenario_json"
            ),
        },
        {
            **base,
            "scenario_id": "shorter_central",
            "curve_overlay_5y_bp": "-4",
            "curve_overlay_10y_bp": "-8",
            "curve_overlay_30y_bp": "-8",
            "effective_curve_overlay_bp": "-7",
            "curve_overlay_key_rate_source_status": "pass_explicit_key_rates",
        },
    ]


def _write_rows(path, rows: list[dict[str, str]]) -> None:
    import csv

    fieldnames = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
