from decimal import Decimal

import pytest

from ratewall.databook.policy_path_normalization import (
    POLICY_PATH_BLOCKED_NORMALIZATION_STATUS,
    POLICY_PATH_BPS_EXPOSURE_FORMULA,
    POLICY_PATH_EFFECT_NORMALIZATION_FORMULA,
    blocked_policy_path_normalization_fields,
    normalize_effect_per_100bp_year,
    policy_path_exposure_bps_year,
)


@pytest.mark.parametrize(
    ("path", "interval_years", "expected_bps_year", "expected_100bp_year"),
    (
        ([Decimal("100")], Decimal("1"), Decimal("100"), Decimal("1")),
        ([Decimal("50")], Decimal("2"), Decimal("100"), Decimal("1")),
        ([Decimal("100")], Decimal("0.5"), Decimal("50"), Decimal("0.5")),
        (
            [Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100")],
            Decimal("0.25"),
            Decimal("100.00"),
            Decimal("1.00"),
        ),
    ),
)
def test_policy_path_exposure_uses_bps_year_convention(
    path: list[Decimal],
    interval_years: Decimal,
    expected_bps_year: Decimal,
    expected_100bp_year: Decimal,
) -> None:
    exposure = policy_path_exposure_bps_year(
        path,
        interval_years=interval_years,
    )

    assert exposure.exposure_bps_year == expected_bps_year
    assert exposure.exposure_100bp_year == expected_100bp_year


def test_policy_path_exposure_accepts_horizon_specific_intervals() -> None:
    exposure = policy_path_exposure_bps_year(
        [Decimal("150"), Decimal("50")],
        interval_years=[Decimal("0.25"), Decimal("1.25")],
    )

    assert exposure.exposure_bps_year == Decimal("100.00")
    assert exposure.exposure_100bp_year == Decimal("1.00")


def test_policy_path_exposure_rejects_misaligned_intervals() -> None:
    with pytest.raises(ValueError, match="must align"):
        policy_path_exposure_bps_year(
            [Decimal("100"), Decimal("100")],
            interval_years=[Decimal("0.25")],
        )


def test_normalization_requires_explicit_policy_path_admission() -> None:
    result = normalize_effect_per_100bp_year(
        Decimal("0.30"),
        exposure_bps_year=Decimal("100"),
        policy_path_admitted=False,
    )

    assert result.normalization_status == POLICY_PATH_BLOCKED_NORMALIZATION_STATUS
    assert result.exposure_bps_year is None
    assert result.normalized_effect_per_100bp_year is None
    assert "no source-backed policy-path exposure vector" in result.exact_blocker


@pytest.mark.parametrize("exposure_bps_year", (Decimal("0"), Decimal("-100")))
def test_normalization_blocks_nonpositive_exposure(
    exposure_bps_year: Decimal,
) -> None:
    result = normalize_effect_per_100bp_year(
        Decimal("0.30"),
        exposure_bps_year=exposure_bps_year,
        policy_path_admitted=True,
    )

    assert result.normalization_status == POLICY_PATH_BLOCKED_NORMALIZATION_STATUS
    assert result.normalized_effect_per_100bp_year is None
    assert result.exact_blocker == "Policy-path exposure must be positive."


def test_admitted_policy_path_normalizes_by_bps_year_exposure() -> None:
    result = normalize_effect_per_100bp_year(
        Decimal("0.30"),
        exposure_bps_year=Decimal("50"),
        policy_path_admitted=True,
    )

    assert result.normalization_status == (
        "pass_reviewed_policy_path_100bp_year_candidate"
    )
    assert result.exposure_bps_year == Decimal("50")
    assert result.exposure_100bp_year == Decimal("0.5")
    assert result.normalized_effect_per_100bp_year == Decimal("0.60")


def test_blocked_policy_path_fields_do_not_emit_value_bearing_outputs() -> None:
    fields = blocked_policy_path_normalization_fields()

    assert fields["policy_path_100bp_year_normalization_status"] == (
        POLICY_PATH_BLOCKED_NORMALIZATION_STATUS
    )
    assert fields["bps_year_exposure_output"] == ""
    assert fields["normalization_output_value"] == ""
    assert fields["normalization_formula_candidate"] == (
        POLICY_PATH_EFFECT_NORMALIZATION_FORMULA
    )
    assert POLICY_PATH_BPS_EXPOSURE_FORMULA.endswith(
        "exposure_100bp_year = bps_year_exposure / 100"
    )
