from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from ratewall.databook.marginal_numerator_ledger import (
    MARGINAL_EXPOSURE_DIAGNOSTIC_MAP_FIELDS,
    MARGINAL_NUMERATOR_CHANNEL_LEDGER_FIELDS,
    MarginalNumeratorLedgerError,
    build_all,
    marginal_exposure_diagnostic_rows,
    marginal_numerator_channel_rows,
    validate_marginal_numerator_channel_rows,
    write_marginal_numerator_outputs,
)


def test_marginal_numerator_channels_fail_closed_until_deltas_exist() -> None:
    rows = marginal_numerator_channel_rows()

    assert {field for row in rows for field in row} == set(
        MARGINAL_NUMERATOR_CHANNEL_LEDGER_FIELDS
    )
    by_id = {row["channel_id"]: row for row in rows}
    assert {
        "public_interest_net_block",
        "tdc_ex_overlap_beta_chi",
        "deposit_safe_yield_payer_flow",
        "other_admitted_disjoint",
    } <= set(by_id)
    assert {row["selected_marginal_n_allowed"] for row in rows} == {"false"}
    assert by_id["tdc_ex_overlap_beta_chi"]["delta_formula"] == (
        "delta_tdc_income_addendum_bil_or_fail_closed_zero"
    )
    assert "tdcsim_v0p3_output" in by_id["tdc_ex_overlap_beta_chi"]["blocked_use"]
    assert "chi_support" in by_id["tdc_ex_overlap_beta_chi"]["blocked_use"]
    assert "stock_rate_fallback" in by_id["deposit_safe_yield_payer_flow"]["blocked_use"]


def test_exposure_diagnostic_map_blocks_old_surfaces() -> None:
    rows = marginal_exposure_diagnostic_rows()

    assert {field for row in rows for field in row} == set(
        MARGINAL_EXPOSURE_DIAGNOSTIC_MAP_FIELDS
    )
    by_surface = {row["old_surface_id"]: row for row in rows}
    assert {
        "current_object_bridge",
        "forecast_central_scenario_surface",
        "historical_root_public_interest_rw_panel",
        "historical_denominator_convention_review",
    } <= set(by_surface)
    assert {row["selected_marginal_n_allowed"] for row in rows} == {"false"}
    assert all("selected_rw_m" in row["blocked_use"] for row in rows)


def test_marginal_numerator_outputs_are_written(tmp_path: Path) -> None:
    tables = build_all()
    outputs = write_marginal_numerator_outputs(
        tmp_path / "out",
        channel_rows=tables["channel_rows"],
        diagnostic_rows=tables["diagnostic_rows"],
    )

    assert outputs["channel_ledger_csv"].read_text(encoding="utf-8").startswith(
        "marginal_numerator_channel_row_id,"
    )
    assert outputs["exposure_map_csv"].read_text(encoding="utf-8").startswith(
        "marginal_exposure_diagnostic_row_id,"
    )


def test_bad_numerator_row_rejects_old_full_tdc_formula() -> None:
    rows = marginal_numerator_channel_rows()
    bad = deepcopy(rows)
    by_id = {row["channel_id"]: row for row in bad}
    by_id["tdc_ex_overlap_beta_chi"]["delta_formula"] = "tdc_full_bil * beta * chi"

    with pytest.raises(MarginalNumeratorLedgerError, match="TDC must use"):
        validate_marginal_numerator_channel_rows(bad)
