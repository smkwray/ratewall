from __future__ import annotations

from pathlib import Path

from ratewall.databook.marginal_channel_parity import (
    CHANNEL_PERIOD_PARITY_FIELDS,
    channel_period_parity_rows,
    write_channel_period_parity_output,
)
from ratewall.databook.marginal_object_ledger import COMPLETE_CHANNEL_REQUIREMENTS


def test_channel_parity_matrix_covers_complete_channel_inventory() -> None:
    rows = channel_period_parity_rows(
        [
            {
                "period_object": "current",
                "selected_marginal_n_allowed": "true",
            },
            {
                "period_object": "forecast",
                "selected_marginal_n_allowed": "true",
            },
        ]
    )

    assert {field for row in rows for field in row} == set(CHANNEL_PERIOD_PARITY_FIELDS)
    assert len(rows) == len(COMPLETE_CHANNEL_REQUIREMENTS)
    by_id = {row["channel_id"]: row for row in rows}
    assert by_id["public_interest_net_block"]["current_status"] == (
        "selected_same_state_plus_100bp_year_delta"
    )
    assert by_id["tdc_ex_overlap_beta_chi"]["selected_allowed_now"] == (
        "current_forecast_selected_as_income_addendum_or_fail_closed_zero"
    )
    assert "full_tdc_level" in by_id["tdc_ex_overlap_beta_chi"]["blocked_use"]
    assert by_id["deposit_safe_yield_payer_flow"]["selected_allowed_now"] == (
        "current_forecast_selected_after_d1_assumption_gate"
    )
    assert by_id["mmf_tbill_realized_yield"]["selected_allowed_now"] == (
        "current_forecast_selected_after_admitted_disjoint_gate"
    )
    assert by_id["zero_low_apr_credit"]["selected_allowed_now"] == "false"


def test_channel_parity_output_is_written(tmp_path: Path) -> None:
    rows = channel_period_parity_rows([])
    outputs = write_channel_period_parity_output(tmp_path, parity_rows=rows)

    assert outputs["channel_period_parity_csv"].read_text(encoding="utf-8").startswith(
        "channel_id,"
    )
