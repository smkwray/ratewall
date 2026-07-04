from __future__ import annotations

from decimal import Decimal

import pytest

import ratewall.databook.denominator_response_application as application
from ratewall.databook.denominator_response_application import (
    COEFFICIENT_UNIT,
    DENOMINATOR_RESPONSE_APPLICATION_FIELDS,
    DenominatorResponseApplicationError,
    denominator_response_application_rows,
    frbus_structural_denominator_response_application_rows_from_directory,
    owner_admitted_denominator_response_application_rows_from_directory,
)
from ratewall.databook.denominator_response_coefficient import (
    FRBUS_STRUCTURAL_COEFFICIENT,
    FRBUS_STRUCTURAL_PROFILE_ID,
)
from ratewall.databook.denominator_response_coefficient import (
    denominator_response_coefficient_profile_rows,
)


def test_missing_admitted_coefficient_blocks_nonzero_rate_path() -> None:
    rows = denominator_response_application_rows(
        _curve_rows(),
        coefficient_profile=denominator_response_coefficient_profile_rows(
            diagnostic_rows=[],
            path_object_rows=[],
        )[0],
    )

    assert {field for row in rows for field in row} == set(
        DENOMINATOR_RESPONSE_APPLICATION_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    baseline = by_scenario["baseline"]
    assert baseline["moving_denominator_bil"] == "1000"
    assert baseline["moving_ratewall_ratio"] == "0.1"
    assert baseline["denominator_response_requirement_status"] == (
        "zero_rate_path_frozen_D_consistent"
    )

    shorter = by_scenario["shorter_rate_down"]
    assert shorter["moving_denominator_bil"] == ""
    assert shorter["moving_ratewall_ratio"] == ""
    assert shorter["moving_delta_ratewall_ratio_vs_baseline"] == ""
    assert shorter["denominator_response_requirement_status"] == (
        "blocked_missing_admitted_denominator_response_coefficient"
    )
    assert "frozen_D_canonical_promotion_for_nonzero_rate_path" in (
        shorter["blocked_use"]
    )
    assert shorter["canonical_ratio_entry"] == "false"
    assert shorter["enters_main_ratio"] == "false"


def test_admitted_coefficient_moves_denominator_for_nonzero_paths() -> None:
    rows = denominator_response_application_rows(
        _curve_rows(),
        coefficient_profile={
            "denominator_response_profile_id": "test_profile",
            "denominator_response_coefficient": "0.2",
            "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
            "coefficient_admission_status": (
                "admitted_curve_denominator_response_coefficient"
            ),
        },
    )

    by_scenario = {row["scenario_id"]: row for row in rows}
    baseline = by_scenario["baseline"]
    assert baseline["delta_denominator_bil"] == "0"
    assert baseline["moving_denominator_bil"] == "1000"
    assert baseline["moving_ratewall_ratio"] == "0.1"
    assert baseline["moving_delta_ratewall_ratio_vs_baseline"] == "0"

    shorter = by_scenario["shorter_rate_down"]
    assert shorter["normalized_100bp_year_value"] == "-0.08"
    assert shorter["delta_denominator_bil"] == "-16"
    assert shorter["moving_denominator_bil"] == "984"
    assert Decimal(shorter["moving_ratewall_ratio"]) == (
        Decimal("110") / Decimal("984")
    )
    assert shorter["denominator_response_direction"] == (
        "negative_rate_path_decreases_D"
    )
    assert shorter["denominator_response_requirement_status"] == (
        "pass_moving_D_computed_from_admitted_profile"
    )
    assert Decimal(shorter["moving_delta_ratewall_ratio_vs_baseline"]) == (
        Decimal("110") / Decimal("984") - Decimal("0.1")
    )

    longer = by_scenario["longer_rate_up"]
    assert longer["delta_denominator_bil"] == "16"
    assert longer["moving_denominator_bil"] == "1016"
    assert longer["denominator_response_direction"] == (
        "positive_rate_path_increases_D"
    )
    assert longer["denominator_scope"] == "noncanonical_moving_D_scenario_sidecar"
    assert longer["canonical_ratio_entry"] == "false"
    assert longer["denominator_prior_update_allowed"] == "false"


def test_application_uses_path_bps_year_not_raw_effective_overlay() -> None:
    rows = denominator_response_application_rows(
        [
            {
                **_curve_rows()[0],
                "path_bps_year": "0",
                "normalized_100bp_year_value": "0",
            },
            {
                **_curve_rows()[1],
                "path_bps_year": "-4",
                "normalized_100bp_year_value": "-0.04",
            },
        ],
        coefficient_profile={
            "denominator_response_profile_id": "test_profile",
            "denominator_response_coefficient": "0.2",
            "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
            "coefficient_admission_status": (
                "admitted_curve_denominator_response_coefficient"
            ),
        },
    )

    shorter = {row["scenario_id"]: row for row in rows}["shorter_rate_down"]
    assert shorter["effective_curve_overlay_bp"] == "-8"
    assert shorter["path_bps_year"] == "-4"
    assert shorter["normalized_100bp_year_value"] == "-0.04"
    assert shorter["delta_denominator_bil"] == "-8"
    assert shorter["moving_denominator_bil"] == "992"


def test_application_rejects_inconsistent_path_normalization() -> None:
    bad_row = {
        **_curve_rows()[1],
        "path_bps_year": "-4",
        "normalized_100bp_year_value": "-0.08",
    }
    with pytest.raises(DenominatorResponseApplicationError, match="disagree"):
        denominator_response_application_rows(
            [_curve_rows()[0], bad_row],
            coefficient_profile={
                "denominator_response_profile_id": "test_profile",
                "denominator_response_coefficient": "0.2",
                "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
                "coefficient_admission_status": (
                    "admitted_curve_denominator_response_coefficient"
                ),
            },
        )


def test_application_rejects_duplicate_baseline_for_fiscal_year() -> None:
    duplicate = {
        **_curve_rows()[0],
        "tdcsim_cbo_curve_denominator_input_row_id": "curve_input::2027::baseline2",
    }
    with pytest.raises(DenominatorResponseApplicationError, match="exactly one"):
        denominator_response_application_rows(
            [*_curve_rows(), duplicate],
            coefficient_profile={
                "denominator_response_profile_id": "test_profile",
                "denominator_response_coefficient": "0.2",
                "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
                "coefficient_admission_status": (
                    "admitted_curve_denominator_response_coefficient"
                ),
            },
        )


def test_owner_admitted_theta0125_profile_emits_moving_d_rows() -> None:
    rows = denominator_response_application_rows(
        [
            {
                "tdcsim_cbo_curve_denominator_input_row_id": "curve::2027::baseline",
                "fiscal_year": "2027",
                "scenario_id": "baseline",
                "baseline_scenario_id": "baseline",
                "effective_curve_overlay_bp": "0",
                "path_bps_year": "0",
                "normalized_100bp_year_value": "0",
                "frozen_denominator_bil": "126.1995153634877105572719155",
                "total_current_demand_support_bil": "100",
                "frozen_ratewall_ratio": "0.792396068",
                "frozen_delta_ratewall_ratio_vs_baseline": "0",
            },
            {
                "tdcsim_cbo_curve_denominator_input_row_id": "curve::2027::rate_down",
                "fiscal_year": "2027",
                "scenario_id": "rate_down",
                "baseline_scenario_id": "baseline",
                "effective_curve_overlay_bp": "-7",
                "path_bps_year": "-7",
                "normalized_100bp_year_value": "-0.07",
                "frozen_denominator_bil": "126.1995153634877105572719155",
                "total_current_demand_support_bil": "100",
                "frozen_ratewall_ratio": "0.792396068",
                "frozen_delta_ratewall_ratio_vs_baseline": "0",
            },
        ],
        coefficient_profile={
            "denominator_response_profile_id": (
                "curve_denominator_response::owner_theta0125_h4_20260627"
            ),
            "denominator_response_coefficient": "0.125",
            "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
            "coefficient_admission_status": (
                "admitted_noncanonical_curve_denominator_response_coefficient"
            ),
        },
    )

    by_scenario = {row["scenario_id"]: row for row in rows}

    assert by_scenario["baseline"]["moving_denominator_bil"] == (
        "126.1995153634877105572719155"
    )
    assert by_scenario["rate_down"]["delta_denominator_bil"].startswith(
        "-1.104245759430517"
    )
    assert by_scenario["rate_down"]["moving_denominator_bil"].startswith(
        "125.095269604057193"
    )
    assert by_scenario["rate_down"]["denominator_response_direction"] == (
        "negative_rate_path_decreases_D"
    )
    assert by_scenario["rate_down"]["denominator_response_requirement_status"] == (
        "pass_moving_D_computed_from_admitted_profile"
    )
    assert by_scenario["rate_down"]["canonical_ratio_entry"] == "false"
    assert by_scenario["rate_down"]["denominator_prior_update_allowed"] == "false"


def test_frbus_structural_profile_emits_larger_moving_d_rows() -> None:
    rows = denominator_response_application_rows(
        [
            {
                "tdcsim_cbo_curve_denominator_input_row_id": "curve::2027::baseline",
                "fiscal_year": "2027",
                "scenario_id": "baseline",
                "baseline_scenario_id": "baseline",
                "effective_curve_overlay_bp": "0",
                "path_bps_year": "0",
                "normalized_100bp_year_value": "0",
                "frozen_denominator_bil": "126.1995153634877105572719155",
                "total_current_demand_support_bil": "100",
                "frozen_ratewall_ratio": "0.792396068",
                "frozen_delta_ratewall_ratio_vs_baseline": "0",
            },
            {
                "tdcsim_cbo_curve_denominator_input_row_id": "curve::2027::rate_down",
                "fiscal_year": "2027",
                "scenario_id": "rate_down",
                "baseline_scenario_id": "baseline",
                "effective_curve_overlay_bp": "-7",
                "path_bps_year": "-7",
                "normalized_100bp_year_value": "-0.07",
                "frozen_denominator_bil": "126.1995153634877105572719155",
                "total_current_demand_support_bil": "100",
                "frozen_ratewall_ratio": "0.792396068",
                "frozen_delta_ratewall_ratio_vs_baseline": "0",
            },
        ],
        coefficient_profile={
            "denominator_response_profile_id": FRBUS_STRUCTURAL_PROFILE_ID,
            "denominator_response_coefficient": FRBUS_STRUCTURAL_COEFFICIENT,
            "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
            "coefficient_admission_status": (
                "admitted_noncanonical_curve_denominator_response_coefficient"
            ),
        },
    )

    by_scenario = {row["scenario_id"]: row for row in rows}

    assert by_scenario["baseline"]["moving_denominator_bil"] == (
        "126.1995153634877105572719155"
    )
    assert by_scenario["rate_down"]["delta_denominator_bil"].startswith(
        "-9.892886525930589"
    )
    assert by_scenario["rate_down"]["moving_denominator_bil"].startswith(
        "116.30662883755712"
    )
    assert by_scenario["rate_down"]["denominator_response_profile_id"] == (
        FRBUS_STRUCTURAL_PROFILE_ID
    )
    assert by_scenario["rate_down"]["denominator_response_direction"] == (
        "negative_rate_path_decreases_D"
    )
    assert by_scenario["rate_down"]["denominator_response_requirement_status"] == (
        "pass_moving_D_computed_from_admitted_profile"
    )


def test_owner_admitted_rows_from_directory_move_nonzero_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_curve_rows(_suite_dir: object) -> list[dict[str, str]]:
        return [
            {
                **_curve_rows()[0],
                "frozen_denominator_bil": "126.1995153634877105572719155",
                "frozen_ratewall_ratio": "0.792396068",
            },
            {
                **_curve_rows()[1],
                "effective_curve_overlay_bp": "-7",
                "frozen_denominator_bil": "126.1995153634877105572719155",
                "frozen_ratewall_ratio": "0.792396068",
            },
        ]

    monkeypatch.setattr(
        application,
        "tdcsim_cbo_curve_denominator_input_rows_from_directory",
        fake_curve_rows,
    )

    rows = owner_admitted_denominator_response_application_rows_from_directory(
        suite_dir="unused"
    )
    by_scenario = {row["scenario_id"]: row for row in rows}

    assert by_scenario["shorter_rate_down"]["path_bps_year"] == "-7"
    assert by_scenario["shorter_rate_down"][
        "denominator_response_profile_id"
    ] == "curve_denominator_response::owner_theta0125_h4_20260627"
    assert by_scenario["shorter_rate_down"]["moving_denominator_bil"].startswith(
        "125.095269604057193"
    )


def test_frbus_structural_rows_from_directory_move_nonzero_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_curve_rows(_suite_dir: object) -> list[dict[str, str]]:
        return [
            {
                **_curve_rows()[0],
                "frozen_denominator_bil": "126.1995153634877105572719155",
                "frozen_ratewall_ratio": "0.792396068",
            },
            {
                **_curve_rows()[1],
                "effective_curve_overlay_bp": "-7",
                "frozen_denominator_bil": "126.1995153634877105572719155",
                "frozen_ratewall_ratio": "0.792396068",
            },
        ]

    monkeypatch.setattr(
        application,
        "tdcsim_cbo_curve_denominator_input_rows_from_directory",
        fake_curve_rows,
    )

    rows = frbus_structural_denominator_response_application_rows_from_directory(
        suite_dir="unused"
    )
    by_scenario = {row["scenario_id"]: row for row in rows}

    assert by_scenario["shorter_rate_down"]["path_bps_year"] == "-7"
    assert by_scenario["shorter_rate_down"][
        "denominator_response_profile_id"
    ] == FRBUS_STRUCTURAL_PROFILE_ID
    assert by_scenario["shorter_rate_down"]["moving_denominator_bil"].startswith(
        "116.30662883755712"
    )


def test_application_requires_supported_coefficient_unit() -> None:
    with pytest.raises(DenominatorResponseApplicationError, match="unsupported"):
        denominator_response_application_rows(
            _curve_rows(),
            coefficient_profile={
                "denominator_response_profile_id": "bad_profile",
                "denominator_response_coefficient": "0.2",
                "denominator_response_coefficient_unit": "basis_points",
                "coefficient_admission_status": (
                    "admitted_curve_denominator_response_coefficient"
                ),
            },
        )


def test_application_rejects_nonpositive_moving_denominator() -> None:
    with pytest.raises(DenominatorResponseApplicationError, match="positive"):
        denominator_response_application_rows(
            _curve_rows(),
            coefficient_profile={
                "denominator_response_profile_id": "too_large",
                "denominator_response_coefficient": "20",
                "denominator_response_coefficient_unit": COEFFICIENT_UNIT,
                "coefficient_admission_status": (
                    "admitted_curve_denominator_response_coefficient"
                ),
            },
        )


def _curve_rows() -> list[dict[str, str]]:
    base = {
        "source_model_scenario_summary_row_id": "summary::x",
        "source_scenario_effect_row_id": "effect::x",
        "fiscal_year": "2027",
        "baseline_scenario_id": "baseline",
        "total_current_demand_support_bil": "100",
        "frozen_denominator_bil": "1000",
        "frozen_ratewall_ratio": "0.1",
        "frozen_delta_ratewall_ratio_vs_baseline": "0",
    }
    return [
        {
            **base,
            "tdcsim_cbo_curve_denominator_input_row_id": (
                "curve_input::2027::baseline"
            ),
            "scenario_id": "baseline",
            "effective_curve_overlay_bp": "0",
        },
        {
            **base,
            "tdcsim_cbo_curve_denominator_input_row_id": (
                "curve_input::2027::shorter_rate_down"
            ),
            "scenario_id": "shorter_rate_down",
            "effective_curve_overlay_bp": "-8",
            "total_current_demand_support_bil": "110",
            "frozen_ratewall_ratio": "0.11",
            "frozen_delta_ratewall_ratio_vs_baseline": "0.01",
        },
        {
            **base,
            "tdcsim_cbo_curve_denominator_input_row_id": (
                "curve_input::2027::longer_rate_up"
            ),
            "scenario_id": "longer_rate_up",
            "effective_curve_overlay_bp": "8",
            "total_current_demand_support_bil": "90",
            "frozen_ratewall_ratio": "0.09",
            "frozen_delta_ratewall_ratio_vs_baseline": "-0.01",
        },
    ]
