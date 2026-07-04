from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.beta_chi_calibration_readout import (
    BETA_CHI_CALIBRATION_DECISION_FIELDS,
    BETA_CHI_CALIBRATION_SUMMARY_FIELDS,
    beta_chi_calibration_decision_rows,
    beta_chi_calibration_readout_markdown,
    beta_chi_calibration_summary_rows,
    write_beta_chi_calibration_readout_outputs,
)


def test_beta_chi_calibration_summary_keeps_assumption_mode_when_no_floor(
    tmp_path: Path,
) -> None:
    claim_gate_dir, direct_dir = _write_fixture_inputs(tmp_path)

    rows = beta_chi_calibration_summary_rows(
        claim_gate_dir=claim_gate_dir,
        direct_chi_dir=direct_dir,
    )

    assert {field for row in rows for field in row} == set(
        BETA_CHI_CALIBRATION_SUMMARY_FIELDS
    )
    row = rows[0]
    assert row["current_beta"] == "0.34201759129420367"
    assert row["current_chi"] == "0.07"
    assert row["current_beta_times_chi"] == "0.0239412313905942569"
    assert row["existing_grid_min_beta_times_chi"] == "0.0034651222443718557"
    assert row["claim_gate_rows"] == "3"
    assert row["sign_robust_rows"] == "1"
    assert row["point_calibrated_rows"] == "1"
    assert row["mixed_sign_rows"] == "1"
    assert row["direct_admitted_floor_rows"] == "0"
    assert row["estimator_ready_rows"] == "0"
    assert row["panel_candidate_rows"] == "24"
    assert row["panel_matched_rows"] == "0"
    assert row["local_source_rows_scanned"] == "12"
    assert row["calibration_decision"] == (
        "assumption_mode_keep_exact_ea_tdc_beta_and_existing_chi"
    )
    assert row["direct_evidence_status"] == (
        "blocked_tdcsim_forecast_treatment_quarters_do_not_overlap_observed_outcomes"
    )
    assert "does_not_change_beta_chi_grid" in row["claim_boundary"]


def test_beta_chi_calibration_decisions_separate_beta_chi_and_direct_floor(
    tmp_path: Path,
) -> None:
    claim_gate_dir, direct_dir = _write_fixture_inputs(tmp_path)
    summary_rows = beta_chi_calibration_summary_rows(
        claim_gate_dir=claim_gate_dir,
        direct_chi_dir=direct_dir,
    )

    rows = beta_chi_calibration_decision_rows(summary_rows)

    assert {field for row in rows for field in row} == set(
        BETA_CHI_CALIBRATION_DECISION_FIELDS
    )
    by_area = {row["decision_area"]: row for row in rows}
    assert by_area["default_beta"]["current_status"] == (
        "admitted_assumption_from_ea_tdc_normal_forward_profile"
    )
    assert by_area["chi"]["current_status"] == (
        "assumption_mode_current_demand_share"
    )
    assert by_area["direct_beta_chi_floor"]["model_action"] == (
        "no_floor_admitted_keep_mixed_rows_point_calibrated"
    )
    assert by_area["external_mpc_bridge"]["model_action"] == (
        "do_not_convert_cash_like_mpc_screens_into_chi_floors"
    )


def test_beta_chi_calibration_outputs_csvs_and_readout(tmp_path: Path) -> None:
    claim_gate_dir, direct_dir = _write_fixture_inputs(tmp_path)
    summary_rows = beta_chi_calibration_summary_rows(
        claim_gate_dir=claim_gate_dir,
        direct_chi_dir=direct_dir,
    )
    decision_rows = beta_chi_calibration_decision_rows(summary_rows)

    outputs = write_beta_chi_calibration_readout_outputs(
        tmp_path / "out",
        summary_rows=summary_rows,
        decision_rows=decision_rows,
    )

    assert outputs["summary_csv"].read_text(encoding="utf-8").startswith(
        "beta_chi_calibration_summary_row_id,"
    )
    assert outputs["decision_csv"].read_text(encoding="utf-8").startswith(
        "beta_chi_calibration_decision_row_id,"
    )
    readout = beta_chi_calibration_readout_markdown(
        summary_rows=summary_rows,
        decision_rows=decision_rows,
    )
    assert outputs["readout_md"].read_text(encoding="utf-8") == readout
    assert "The forecast should keep the exact EA-TDC beta" in readout
    assert "Direct admitted floor rows: `0`." in readout
    assert "This readout changes no forecast numerator or denominator value" in readout


def _write_fixture_inputs(tmp_path: Path) -> tuple[Path, Path]:
    claim_gate_dir = tmp_path / "claim_gate"
    direct_dir = tmp_path / "direct"
    claim_gate_dir.mkdir()
    direct_dir.mkdir()
    _write_csv(
        claim_gate_dir / "ratewall_beta_chi_claim_gate.csv",
        [
            {
                "current_beta": "0.34201759129420367",
                "current_chi": "0.07",
                "existing_grid_min_beta": "0.11550407481239519",
                "existing_grid_min_chi": "0.03",
                "claim_strength_status": "baseline_reference",
                "moving_d_beta_chi_sign_stability_status": "zero_baseline",
            },
            {
                "current_beta": "0.34201759129420367",
                "current_chi": "0.07",
                "existing_grid_min_beta": "0.11550407481239519",
                "existing_grid_min_chi": "0.03",
                "claim_strength_status": "point_calibrated_assumption_only",
                "moving_d_beta_chi_sign_stability_status": "mixed_sign",
            },
            {
                "current_beta": "0.34201759129420367",
                "current_chi": "0.07",
                "existing_grid_min_beta": "0.11550407481239519",
                "existing_grid_min_chi": "0.03",
                "claim_strength_status": "sign_robust_over_existing_beta_chi_grid",
                "moving_d_beta_chi_sign_stability_status": "stable_positive",
            },
        ],
    )
    _write_csv(
        claim_gate_dir / "ratewall_beta_chi_robustness_thresholds.csv",
        [{"scenario_id": "holder_more_banks"}],
    )
    _write_csv(
        claim_gate_dir / "ratewall_beta_chi_source_context.csv",
        [
            {
                "source_row_count": "5",
                "admitted_beta_floor_rows": "0",
                "admitted_chi_floor_rows": "0",
                "admitted_beta_chi_floor_rows": "0",
            },
            {
                "source_row_count": "7",
                "admitted_beta_floor_rows": "0",
                "admitted_chi_floor_rows": "0",
                "admitted_beta_chi_floor_rows": "0",
            },
        ],
    )
    _write_csv(
        claim_gate_dir / "ratewall_beta_chi_external_floor_review.csv",
        [
            {
                "external_admitted_beta_floor_rows": "0",
                "external_admitted_chi_floor_rows": "0",
            }
        ],
    )
    _write_csv(
        claim_gate_dir / "ratewall_beta_chi_chi_mapping_sensitivity.csv",
        [{"admission_status": "not_admitted_mapping_sensitivity_only"}],
    )
    _write_csv(
        direct_dir / "ratewall_direct_chi_requirements.csv",
        [{"scenario_id": "holder_more_banks"}],
    )
    _write_csv(
        direct_dir / "ratewall_direct_chi_adjudication.csv",
        [{"admission_result": "not_admitted_no_direct_chi_or_beta_chi_evidence"}],
    )
    _write_csv(
        direct_dir / "ratewall_direct_beta_chi_estimator_contract.csv",
        [{"current_contract_status": "blocked_missing_identification_strategy"}],
    )
    _write_csv(
        direct_dir / "ratewall_direct_beta_chi_candidate_panel_status.csv",
        [
            {
                "candidate_panel_rows": "24",
                "matched_panel_rows": "0",
                "identified_panel_rows": "0",
                "admitted_lower_bound_rows": "0",
                "estimator_blocker": (
                    "tdcsim_forecast_treatment_quarters_do_not_overlap_"
                    "observed_outcomes"
                ),
            }
        ],
    )
    return claim_gate_dir, direct_dir


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
