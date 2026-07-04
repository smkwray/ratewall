from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.databook.marginal_tdc_beta import (
    BETA_SCHEDULE_FIELDS,
    LEGACY_BETA,
    MarginalTdcBetaError,
    build_beta_schedule,
    build_beta_sensitivity_panel,
    load_beta_anchor,
    validate_beta_schedule,
)


def test_beta_schedule_builds_for_current_forecast_and_historical_window(
    tmp_path: Path,
) -> None:
    _write_anchor_inputs(tmp_path, source_grade=True)
    rows = build_beta_schedule(
        denominator_rows=_denominator_rows(),
        historical_window_rows=_historical_window_rows(),
        project_root=tmp_path,
        tdcest_proxy_path="tdcest_proxy.csv",
    )

    assert {field for row in rows for field in row} == set(BETA_SCHEDULE_FIELDS)
    by_key = {(row["period_object"], row["period"]): row for row in rows}
    assert by_key[("historical", "2022Q4")]["beta_selection_status"] == (
        "selected_source_grade_ea_tdc_rolling_beta"
    )
    assert by_key[("current", "2026")]["beta_projection_method"] == (
        "flat_carry_forward_from_latest_rolling_window_2026Q2"
    )
    assert by_key[("forecast", "2036")]["beta_projection_method"] == (
        "flat_carry_forward_from_latest_rolling_window_2026Q2"
    )
    assert by_key[("historical", "2022Q4")]["beta_selected"] == "0.735875"
    assert by_key[("current", "2026")]["beta_selected"] == "0.530751"


def test_selected_beta_is_not_legacy_scaffold_value(tmp_path: Path) -> None:
    _write_anchor_inputs(tmp_path, source_grade=True)
    rows = build_beta_schedule(
        denominator_rows=_denominator_rows(),
        historical_window_rows=_historical_window_rows(),
        project_root=tmp_path,
        tdcest_proxy_path="tdcest_proxy.csv",
    )

    assert {row["beta_selected"] for row in rows} == {
        "0.530751",
        "0.735875",
    }
    assert all(Decimal(row["beta_selected"]) != LEGACY_BETA for row in rows)


def test_ea_tdc_raw_artifact_controls_source_grade_status(tmp_path: Path) -> None:
    _write_anchor_inputs(tmp_path, source_grade=False)
    fallback = load_beta_anchor(tmp_path)
    assert fallback.source_status == "documented_source_anchor_raw_artifact_not_packaged"
    assert fallback.selected_source_grade_allowed is False

    _write_anchor_inputs(tmp_path, source_grade=True)
    source_grade = load_beta_anchor(tmp_path)
    assert source_grade.source_status == "source_grade_ea_tdc_anchor"
    assert source_grade.selected_source_grade_allowed is True


def test_beta_bounds_and_identity_are_enforced(tmp_path: Path) -> None:
    _write_anchor_inputs(tmp_path, source_grade=True)
    rows = build_beta_schedule(
        denominator_rows=_denominator_rows(),
        historical_window_rows=_historical_window_rows(),
        project_root=tmp_path,
        tdcest_proxy_path="tdcest_proxy.csv",
    )
    bad = [dict(row) for row in rows]
    bad[0]["beta_times_chi_selected"] = "0"

    with pytest.raises(MarginalTdcBetaError, match="identity"):
        validate_beta_schedule(bad)


def test_pre_2002_beta_fails_closed(tmp_path: Path) -> None:
    _write_anchor_inputs(tmp_path, source_grade=True)
    rows = build_beta_schedule(
        denominator_rows=[
            *_denominator_rows(),
            _denominator_row("historical", "2001Q4", "historical_actual_state::2001Q4"),
        ],
        historical_window_rows=_historical_window_rows(),
        project_root=tmp_path,
        tdcest_proxy_path="tdcest_proxy.csv",
    )

    pre = next(row for row in rows if row["period"] == "2001Q4")
    assert pre["beta_selection_status"] == "fail_closed_no_ea_tdc_sample_coverage"


def test_tdcest_time_varying_proxy_is_not_selected(tmp_path: Path) -> None:
    _write_anchor_inputs(tmp_path, source_grade=True)
    _write_csv(
        tmp_path / "tdcest_proxy.csv",
        [
            {
                "ref_quarter": "2022Q4",
                "object_family": "flow_absorption_trailing_4q",
                "route_class": "deposit_funded_domestic_nonbank_possible",
                "share_low": "0",
                "share_central": "0.359682",
                "share_high": "0.719364",
            }
        ],
    )

    rows = build_beta_schedule(
        denominator_rows=_denominator_rows(),
        historical_window_rows=_historical_window_rows(),
        project_root=tmp_path,
        tdcest_proxy_path="tdcest_proxy.csv",
    )
    proxied = next(row for row in rows if row["period"] == "2022Q4")
    assert proxied["time_varying_proxy_available"] == "true"
    assert proxied["time_varying_proxy_high"] == "0.719364"
    assert proxied["beta_selected"] == "0.735875"


def test_beta_sensitivity_panel_marks_only_selected_central(tmp_path: Path) -> None:
    _write_anchor_inputs(tmp_path, source_grade=True)
    rows = build_beta_schedule(
        denominator_rows=_denominator_rows(),
        historical_window_rows=_historical_window_rows(),
        project_root=tmp_path,
        tdcest_proxy_path="tdcest_proxy.csv",
    )
    sensitivity = build_beta_sensitivity_panel(rows)

    assert {row["case_id"] for row in sensitivity} == {
        "legacy_low",
        "selected_central",
        "rolling_high",
    }
    assert {
        row["selected_central"] for row in sensitivity if row["case_id"] == "selected_central"
    } == {"true"}


def _write_anchor_inputs(root: Path, *, source_grade: bool) -> None:
    _write_csv(
        root / "configs/assumption_mode/ratewall_tdc_beta_anchor_override.csv",
        [
            {
                "beta_anchor_id": "ea_tdc_h0_matched_total_deposits_anchor_v1",
                "beta_selected": "0.6163494354563133",
                "beta_low": "0.34201759129420367",
                "beta_high": "0.729969",
                "beta_legacy_scaffold": "0.34201759129420367",
                "chi_selected": "0.07",
                "chi_low": "0.03",
                "chi_high": "0.12",
                "source_artifact": "ea-tdc/output/models/paper_tier2_selected_credit_rate_lags_estimates.csv",
                "source_field": "normalized_beta",
                "source_status": "documented_source_anchor_raw_artifact_not_packaged",
                "selected_source_grade_allowed": "false",
                "claim_boundary": "beta_selected_source_grade_requires_vendored_ea_tdc_artifact",
            }
        ],
    )
    if source_grade:
        _write_csv(
            root
            / "data/raw/ratewall_sibling_calibration/"
            "ea_tdc_paper_tier2_selected_credit_rate_lags_estimates.csv",
            [
                {
                    "outcome": "matched_total_deposits",
                    "horizon": "0",
                    "normalized_beta": "0.6163494354563133",
                }
            ],
        )
        _write_csv(
            root
            / "data/raw/ratewall_sibling_calibration/"
            "ea_tdc_tier2_rolling_selected_credit_rate_pass_through_estimates.csv",
            [
                {
                    "job_id": "tier2_rolling_selected_credit_rate_pass_through",
                    "window_start_quarter": "2011Q1",
                    "window_end_quarter": "2022Q4",
                    "window_quarters": "48",
                    "outcome": "matched_total_deposits",
                    "horizon": "0",
                    "normalized_beta": "0.735875",
                    "normalized_lower95": "0.185293",
                    "normalized_upper95": "1.286457",
                    "inference_method": "rolling_selected_credit_rate_lags_rank_aware",
                },
                {
                    "job_id": "tier2_rolling_selected_credit_rate_pass_through",
                    "window_start_quarter": "2014Q3",
                    "window_end_quarter": "2026Q2",
                    "window_quarters": "48",
                    "outcome": "matched_total_deposits",
                    "horizon": "0",
                    "normalized_beta": "0.530751",
                    "normalized_lower95": "0.146373",
                    "normalized_upper95": "0.915129",
                    "inference_method": "rolling_selected_credit_rate_lags_rank_aware",
                },
            ],
        )


def _denominator_rows() -> list[dict[str, str]]:
    return [
        _denominator_row("historical", "2022Q4", "historical_actual_state::2022Q4"),
        _denominator_row("current", "2026", "current_state::2026"),
        _denominator_row("forecast", "2036", "cbo_baseline_state::2036"),
    ]


def _denominator_row(period_object: str, period: str, state_id: str) -> dict[str, str]:
    return {
        "period_object": period_object,
        "period": period,
        "state_id": state_id,
        "horizon": "annual_h1_100bp_year",
        "shock_path_id": "plus_100bp_year",
        "shock_bps_year": "100",
        "selected_marginal_D": "true",
    }


def _historical_window_rows() -> list[dict[str, str]]:
    return [
        {
            "period": "2022Q4",
            "selected_historical_rw_m_allowed_if_complete": "true",
            "selection_gate_status": "pending_source_grade_pair",
        }
    ]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
