from __future__ import annotations

import csv
from decimal import Decimal
from functools import lru_cache
from io import StringIO
from pathlib import Path

import pytest

from ratewall.rwtam.three_gaps import (
    BANDS,
    build_three_gaps,
    write_three_gaps_outputs,
)
from ratewall.rwtam.v1 import build_v1


PACK_DIR = Path("configs/rwtam/packs")
GOLDEN_WAVE8_DIR = Path("tests/fixtures/rwtam/golden_wave8")
pytestmark = pytest.mark.audit_fast


@lru_cache(maxsize=1)
def _result():
    return build_three_gaps(PACK_DIR)


def test_g1_easing_asymmetry_applies_down_beta_only_to_cuts_and_blocks_distress() -> None:
    result = _result()
    rows = result.rows("out_easing_asymmetry")

    assert {row["shock_easing_bp"] for row in rows} == {"-100"}
    assert {row["shock_hike_bp"] for row in rows} == {"100"}
    assert {row["cut_distress_activation"] for row in rows} == {"false"}
    assert {row["deposit_down_beta_multiplier"] for row in rows if row["band"] == "low"} == {"1.2"}
    assert {row["deposit_down_beta_multiplier"] for row in rows if row["band"] == "base"} == {"1.5"}
    assert {row["deposit_down_beta_multiplier"] for row in rows if row["band"] == "high"} == {"2"}
    assert all(Decimal(row["down_beta_delta_D_bil"]) != 0 for row in rows)
    assert all(Decimal(row["distress_absence_delta_D_bil"]) <= 0 for row in rows)


def test_g1_emits_year1_both_modes_and_persistent_multiyear_comparison() -> None:
    result = _result()
    rows = result.rows("out_easing_asymmetry")

    horizons = {(row["dose_mode"], row["horizon_id"]) for row in rows}
    assert ("transient_12m", "year1_annual") in horizons
    assert ("persistent_level", "year1_annual") in horizons
    assert ("persistent_level", "multi_year_persistent") in horizons
    assert ("transient_12m", "multi_year_persistent") not in horizons

    base = [
        row
        for row in rows
        if row["band"] == "base" and row["horizon_id"] == "year1_annual"
    ]
    assert base
    assert all(row["comparison"] == "RW_easing_below_RW_hike" for row in base)
    assert all(Decimal(row["lockin_release_delta_D_bil"]) < 0 for row in base)


def test_g2_true_rstar_flat_and_apparent_rstar_monotone_is_emitted_not_assumed() -> None:
    result = _result()
    rows = result.rows("out_rstar_illusion_exhibit")

    assert len(rows) == 20
    assert {row["true_rstar_pp"] for row in rows} == {"0"}
    apparent = [Decimal(row["apparent_rstar_pp"]) for row in rows]
    assert all(b >= a for a, b in zip(apparent, apparent[1:]))
    assert Decimal(rows[-1]["apparent_rstar_pp"]) > Decimal(rows[0]["apparent_rstar_pp"])
    assert {row["label"] for row in rows} == {"hypothetical_illustration;shape_only"}


def test_g3_fx_off_reconciles_to_full_rwpi_minus_fx_exactly_and_straddles_year1_base() -> None:
    result = _result()
    rows = result.rows("out_rwpi_fx_off")

    assert {row["index_target"] for row in rows} == {"CPI_U"}
    assert {row["dose_mode"] for row in rows} == {"persistent_level", "transient_12m"}
    for row in rows:
        for band in BANDS:
            assert Decimal(row[f"full_minus_fx_identity_residual_{band}_pp"]) == Decimal("0")

    base = next(
        row
        for row in rows
        if row["dose_mode"] == "persistent_level"
        and row["slack_state"] == "balanced"
        and row["horizon_window"] == "0_12m"
    )
    assert Decimal(base["ND_pi_fx_off_base_pp"]).quantize(Decimal("0.0001")) == Decimal("-0.0094")
    assert base["decision_rule_verdict"] == "indeterminate_bands_straddle_zero"
    assert base["rent_companion_status"] == "unchanged_diagnostic_companion_not_summed"


def test_three_gap_invariants_and_outputs(tmp_path: Path) -> None:
    result = _result()
    checks = {row["check_id"]: row["status"] for row in result.rows("out_three_gaps_invariant_check")}

    assert set(checks.values()) == {"pass"}
    paths = write_three_gaps_outputs(result, tmp_path)
    assert paths["out_easing_asymmetry"].exists()
    assert paths["out_rstar_illusion_exhibit"].exists()
    assert paths["out_rwpi_fx_off"].exists()


def test_three_gap_build_preserves_wave8_golden_byte_stability() -> None:
    result = build_v1(PACK_DIR)
    for table_name in ["out_ratewall_rollup", "out_phase6_waterfall_scaffold", "out_invariant_check"]:
        expected_text = (GOLDEN_WAVE8_DIR / f"{table_name}.csv").read_text(encoding="utf-8")
        expected_rows = list(csv.DictReader(StringIO(expected_text)))
        actual_rows = result.rows(table_name)
        assert len(actual_rows) == len(expected_rows), table_name
        for actual, expected in zip(actual_rows, expected_rows, strict=True):
            assert list(actual) == list(expected), table_name
            assert actual == expected
