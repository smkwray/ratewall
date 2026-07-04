from __future__ import annotations

import csv
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.databook.marginal_tdcsim_contract import (
    CLAIM_BOUNDARY,
    MARGINAL_TDC_STATE_COMPOSITION_AUDIT_FIELDS,
    MARGINAL_TDC_SUPPORT_PANEL_FIELDS,
    MARGINAL_TDCSIM_CONTRACT_INGEST_FIELDS,
    MarginalTDCSimContractError,
    ingest_marginal_tdcsim_pair,
    ingest_marginal_tdcsim_pairs,
    validate_marginal_tdc_support_panel,
    write_marginal_tdcsim_outputs,
)


def test_missing_tdcsim_pair_fails_closed(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=tmp_path / "missing")

    assert len(tables["ingest_rows"]) == 1
    assert tables["support_rows"] == []
    assert len(tables["state_composition_audit_rows"]) == 1
    row = tables["ingest_rows"][0]
    audit = tables["state_composition_audit_rows"][0]
    assert row["contract_ingest_status"] == (
        "fail_closed_missing_or_invalid_tdcsim_v0p4_marginal_pair"
    )
    assert audit["selected_tdc_admission_status"] == "fail_closed_no_selected_tdc_support"
    assert "tdcsim_v0p3_output" in row["blocked_use"]


def test_valid_tdcsim_pair_ingests_support_panel(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path)

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert {field for row in tables["ingest_rows"] for field in row} == set(
        MARGINAL_TDCSIM_CONTRACT_INGEST_FIELDS
    )
    assert {field for row in tables["support_rows"] for field in row} == set(
        MARGINAL_TDC_SUPPORT_PANEL_FIELDS
    )
    assert {
        field
        for row in tables["state_composition_audit_rows"]
        for field in row
    } == set(MARGINAL_TDC_STATE_COMPOSITION_AUDIT_FIELDS)
    ingest = tables["ingest_rows"][0]
    support = tables["support_rows"][0]
    assert ingest["contract_ingest_status"] == "pass_tdcsim_v0p4_marginal_pair_ingested"
    assert ingest["object_id"] == "RW_M_PLUS_100BP_YEAR"
    assert ingest["shock_path_id"] == "plus_100bp_year"
    assert support["shock_path_id"] == "plus_100bp_year"
    assert support["horizon"] == "annual_h1_100bp_year"
    assert support["state_manifest_status"] == "pass"
    assert support["tdc_amount_basis"] == "pre_beta_ex_overlap_delta"
    assert support["delta_tdc_ex_overlap_bil"] == "2"
    assert support["beta_times_chi"] == "0.2"
    assert support["marginal_tdc_support_bil"] == "0.4"
    assert support["support_formula"] == "delta_tdc_ex_overlap_bil * beta * chi"
    assert support["enters_selected_rw_m"] == "true"
    assert tables["state_composition_audit_rows"][0]["full_key_status"] == (
        "pass_full_marginal_tdc_key_present"
    )


def test_pair_root_ingests_multiple_manifest_backed_pairs(tmp_path: Path) -> None:
    pair_root = tmp_path / "source_pairs"
    _write_pair(
        pair_root,
        pair_name="forecast_2035",
        pair_id="pair_2035",
        period="2035",
        state_id="forecast_state::2035",
    )
    _write_pair(
        pair_root,
        pair_name="forecast_2036",
        pair_id="pair_2036",
        period="2036",
        state_id="forecast_state::2036",
    )

    tables = ingest_marginal_tdcsim_pairs(pair_root=pair_root)

    assert len(tables["ingest_rows"]) == 2
    assert len(tables["support_rows"]) == 2
    assert len(tables["state_composition_audit_rows"]) == 2
    assert {row["period"] for row in tables["support_rows"]} == {"2035", "2036"}
    assert all(
        row["selected_tdc_formula_pass"] == "true" for row in tables["support_rows"]
    )


def test_forecast_assumption_fixture_is_not_selected_without_source_grade(tmp_path: Path) -> None:
    pair_root = tmp_path / "source_pairs"
    _write_pair(
        pair_root,
        pair_name="forecast_2036_fixture",
        pair_id="ratewall_forecast_cbo_baseline_2036_plus100bp_year_assumption_pair_v1",
        period="2036",
        state_id="cbo_baseline_state::2036",
    )

    tables = ingest_marginal_tdcsim_pairs(pair_root=pair_root)

    assert len(tables["ingest_rows"]) == 1
    assert tables["support_rows"] == []
    assert "source-grade" in tables["ingest_rows"][0]["failure_reason"]


def test_forecast_source_grade_support_requires_rollforward_hashes(tmp_path: Path) -> None:
    pair_dir = _write_pair(
        tmp_path,
        pair_name="forecast_2036_source_grade",
        pair_id="ratewall_forecast_cbo_baseline_2036_plus100bp_year_source_grade_pair_v1",
        period="2036",
        state_id="cbo_baseline_state::2036",
    )
    _rewrite_source_grade_fields(pair_dir, derived_sha="")

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert tables["support_rows"] == []
    assert "derived_state_package_sha256" in tables["ingest_rows"][0]["failure_reason"]


def test_forecast_source_grade_support_is_admitted(tmp_path: Path) -> None:
    pair_dir = _write_pair(
        tmp_path,
        pair_name="forecast_2036_source_grade",
        pair_id="ratewall_forecast_cbo_baseline_2036_plus100bp_year_source_grade_pair_v1",
        period="2036",
        state_id="cbo_baseline_state::2036",
    )
    _rewrite_source_grade_fields(pair_dir)

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert len(tables["support_rows"]) == 1
    assert tables["support_rows"][0]["source_grade_status"] == "pass_forecast_rollforward_source_grade"


def test_pair_root_prefers_source_grade_duplicate_key(tmp_path: Path) -> None:
    pair_root = tmp_path / "source_pairs"
    assumption = _write_pair(
        pair_root,
        pair_name="current_assumption",
        pair_id="current_assumption_pair",
        period="2026",
        state_id="current_state::2026",
    )
    source_grade = _write_pair(
        pair_root,
        pair_name="current_source_grade",
        pair_id="current_source_grade_pair",
        period="2026",
        state_id="current_state::2026",
    )
    _rewrite_summary_delta(assumption, pair_id="current_assumption_pair", delta_ex="0")
    _rewrite_summary_delta(source_grade, pair_id="current_source_grade_pair", delta_ex="4")

    tables = ingest_marginal_tdcsim_pairs(pair_root=pair_root)

    assert len(tables["ingest_rows"]) == 2
    assert len(tables["support_rows"]) == 1
    support = tables["support_rows"][0]
    assert support["pair_id"] == "current_source_grade_pair"
    assert support["delta_tdc_ex_overlap_bil"] == "4"
    assert support["marginal_tdc_support_bil"] == "0.8"


def test_tdcsim_outputs_are_written(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=_write_pair(tmp_path))
    outputs = write_marginal_tdcsim_outputs(
        tmp_path / "out",
        ingest_rows=tables["ingest_rows"],
        support_rows=tables["support_rows"],
        state_composition_audit_rows=tables["state_composition_audit_rows"],
    )

    assert outputs["contract_ingest_csv"].read_text(encoding="utf-8").startswith(
        "marginal_tdcsim_contract_ingest_row_id,"
    )
    assert outputs["support_panel_csv"].read_text(encoding="utf-8").startswith(
        "marginal_tdc_support_row_id,"
    )
    assert outputs["state_composition_audit_csv"].read_text(
        encoding="utf-8"
    ).startswith("marginal_tdc_state_composition_audit_row_id,")


def test_legacy_or_gross_tdc_summary_is_rejected(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path)
    summary_path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(summary_path)
    rows[0].pop("object_id")
    _write_csv(summary_path, rows)

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert tables["support_rows"] == []
    assert tables["ingest_rows"][0]["contract_ingest_status"].startswith("fail_closed")
    assert "missing summary fields" in tables["ingest_rows"][0]["failure_reason"]


def test_bad_support_panel_rejects_formula_drift(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=_write_pair(tmp_path))
    bad = deepcopy(tables["support_rows"])
    bad[0]["marginal_tdc_support_bil"] = "0.6"

    with pytest.raises(MarginalTDCSimContractError, match="identity"):
        validate_marginal_tdc_support_panel(bad, allow_empty=False)


def test_selected_tdc_support_requires_selected_entry_flag_true(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=_write_pair(tmp_path))
    bad = deepcopy(tables["support_rows"])
    bad[0]["enters_selected_rw_m"] = "false"

    with pytest.raises(MarginalTDCSimContractError, match="enters_selected_rw_m"):
        validate_marginal_tdc_support_panel(bad, allow_empty=False)


def test_ingest_requires_beta_schedule_row_when_schedule_is_supplied(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path, period="2036", state_id="forecast_state::2036")
    schedule = _write_beta_schedule(tmp_path, period="2035", state_id="forecast_state::2035")

    tables = ingest_marginal_tdcsim_pair(
        pair_dir=pair_dir,
        beta_schedule_path=schedule,
    )

    assert tables["support_rows"] == []
    assert "missing beta schedule row" in tables["ingest_rows"][0]["failure_reason"]


def test_ingest_rejects_beta_mismatch_against_schedule(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path, period="2036", state_id="forecast_state::2036")
    schedule = _write_beta_schedule(
        tmp_path,
        period="2036",
        state_id="forecast_state::2036",
        beta="0.6163494354563133",
        chi="0.07",
    )

    tables = ingest_marginal_tdcsim_pair(
        pair_dir=pair_dir,
        beta_schedule_path=schedule,
    )

    assert tables["support_rows"] == []
    assert "does not match RateWall beta schedule" in tables["ingest_rows"][0]["failure_reason"]


def test_ingest_accepts_beta_schedule_match_and_recomputes_support(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path, period="2036", state_id="forecast_state::2036")
    _rewrite_summary_beta(pair_dir, beta="0.6163494354563133", chi="0.07")
    schedule = _write_beta_schedule(
        tmp_path,
        period="2036",
        state_id="forecast_state::2036",
        beta="0.6163494354563133",
        chi="0.07",
    )

    tables = ingest_marginal_tdcsim_pair(
        pair_dir=pair_dir,
        beta_schedule_path=schedule,
    )

    support = tables["support_rows"][0]
    assert support["beta"] == "0.6163494354563133"
    assert support["chi"] == "0.07"
    assert support["beta_times_chi"] == "0.043144460481941931"
    assert support["marginal_tdc_support_bil"] == "0.086288920963883862"


def test_bad_support_panel_rejects_duplicate_full_key(tmp_path: Path) -> None:
    tables = ingest_marginal_tdcsim_pair(pair_dir=_write_pair(tmp_path))
    bad = deepcopy(tables["support_rows"])
    bad.append(deepcopy(bad[0]))

    with pytest.raises(MarginalTDCSimContractError, match="duplicate"):
        validate_marginal_tdc_support_panel(bad, allow_empty=False)


def test_tdcsim_summary_requires_state_manifest_fields(tmp_path: Path) -> None:
    pair_dir = _write_pair(tmp_path)
    summary_path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(summary_path)
    rows[0].pop("state_fingerprint_sha256")
    _write_csv(summary_path, rows)

    tables = ingest_marginal_tdcsim_pair(pair_dir=pair_dir)

    assert tables["support_rows"] == []
    assert "state_fingerprint_sha256" in tables["ingest_rows"][0]["failure_reason"]


def _write_pair(
    tmp_path: Path,
    *,
    pair_name: str = "pair",
    pair_id: str = "pair_001",
    period: str = "2036",
    state_id: str = "forecast_state::2036",
) -> Path:
    pair_dir = tmp_path / pair_name
    pair_dir.mkdir(parents=True)
    manifest = {
        "schema_version": "tdcsim_cbo_marginal_tdc_manifest_v1",
        "pair_id": pair_id,
        "generated_at_utc": "2026-06-30T00:00:00Z",
        "pair_spec": {
            "schema_version": "tdcsim_cbo_marginal_tdc_pair_v1",
            "object_id": "RW_M_PLUS_100BP_YEAR",
            "shock_path_id": "plus_100bp_year",
            "shock_bps_year": 100,
            "denominator_equivalence_key": "ratewall_D_conv_plus_100bp_year_v1",
            "require_same_baseline_hashes": True,
            "require_same_opening_state": True,
            "require_same_actuals_available_as_of": True,
            "require_same_simulation_dates": True,
            "require_same_period_index": True,
            "require_same_non_rate_compiled_inputs": True,
            "one_named_rate_shock_only": True,
        },
        "baseline_run": {},
        "shock_run": {},
        "validation": {"status": "pass"},
        "files": {},
        "claim_boundary": CLAIM_BOUNDARY,
        "pair_manifest_config_sha256": "0" * 64,
    }
    (pair_dir / "tdcsim_ratewall_marginal_tdc_pair_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    _write_csv(
        pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv",
        [
            {
                "schema_version": "tdcsim_cbo_marginal_tdc_pair_v1",
                "contract_version": "0.4.0",
                "pair_id": pair_id,
                "object_id": "RW_M_PLUS_100BP_YEAR",
                "shock_path_id": "plus_100bp_year",
                "shock_bps_year": "100",
                "state_id": state_id,
                "state_kind": "forecast_state",
                "state_period": period,
                "scenario_id": "forecast_scenario::baseline",
                "scenario_state_set_id": "forecast_state_set::baseline",
                "state_fingerprint_sha256": "a" * 64,
                "state_component_inventory_sha256": "b" * 64,
                "period": period,
                "period_start": f"{period}-01-01",
                "period_end": f"{period}-12-31",
                "horizon": "annual_h1_100bp_year",
                "demand_conversion_case": "central",
                "baseline_run_id": "baseline",
                "shock_run_id": "shock",
                "tdc_change_baseline_bil": "10",
                "tdc_change_shock_bil": "13",
                "delta_tdc_change_bil": "3",
                "overlap_baseline_bil": "1",
                "overlap_shock_bil": "2",
                "delta_overlap_bil": "1",
                "tdc_change_ex_overlap_baseline_bil": "9",
                "tdc_change_ex_overlap_shock_bil": "11",
                "delta_tdc_ex_overlap_bil": "2",
                "beta_assumption_id": "beta_fixture",
                "beta": "0.5",
                "beta_source_status": "fixture",
                "chi_assumption_id": "chi_fixture",
                "chi": "0.4",
                "chi_source_status": "fixture",
                "beta_times_chi": "0.2",
                "tdc_amount_basis": "pre_beta_ex_overlap_delta",
                "support_formula": "delta_tdc_ex_overlap_bil * beta * chi",
                "overlap_scope": "tdcsim_and_external_support",
                "marginal_tdc_support_bil": "0.4",
                "same_state_status": "pass",
                "rate_shock_only_status": "pass",
                "shock_path_validation_status": "pass",
                "period_alignment_status": "pass",
                "overlap_identity_status": "pass",
                "component_identity_status": "pass",
                "route_identity_status": "pass",
                "support_identity_status": "pass",
                "state_manifest_status": "pass",
                "contract_ingest_status": "ready_for_ratewall_assumption_mode_ingest",
                "failure_reason": "",
                "assumption_mode": "true",
                "evidence_mode_enabled": "false",
                "raw_rate_shock_enabled": "false",
                "named_marginal_shock_path_enabled": "true",
                "tdcsim_channel_classifier_enabled": "false",
                "enters_main_ratio_candidate": "true",
                "canonical_ratio_entry": "false",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        ],
    )
    return pair_dir


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _rewrite_summary_delta(pair_dir: Path, *, pair_id: str, delta_ex: str) -> None:
    path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(path)
    row = rows[0]
    row["pair_id"] = pair_id
    row["tdc_change_baseline_bil"] = "0"
    row["tdc_change_shock_bil"] = delta_ex
    row["delta_tdc_change_bil"] = delta_ex
    row["overlap_baseline_bil"] = "0"
    row["overlap_shock_bil"] = "0"
    row["delta_overlap_bil"] = "0"
    row["tdc_change_ex_overlap_baseline_bil"] = "0"
    row["tdc_change_ex_overlap_shock_bil"] = delta_ex
    row["delta_tdc_ex_overlap_bil"] = delta_ex
    row["marginal_tdc_support_bil"] = str(float(delta_ex) * 0.2).rstrip("0").rstrip(".")
    _write_csv(path, rows)


def _rewrite_source_grade_fields(pair_dir: Path, *, derived_sha: str | None = None) -> None:
    path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(path)
    row = rows[0]
    row["source_vintage"] = "2026-02-11"
    row["source_grade_status"] = "pass_forecast_rollforward_source_grade"
    row["state_construction_method"] = "baseline_rollforward_export_v1"
    row["forecast_state_export_manifest_sha256"] = "c" * 64
    row["derived_state_package_sha256"] = "d" * 64 if derived_sha is None else derived_sha
    row["parent_baseline_package_sha256"] = "e" * 64
    row["rollforward_run_manifest_sha256"] = "f" * 64
    row["compiled_non_rate_inputs_digest"] = "1" * 64
    _write_csv(path, rows)


def _rewrite_summary_beta(pair_dir: Path, *, beta: str, chi: str) -> None:
    path = pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv"
    rows = _read_csv(path)
    row = rows[0]
    row["beta_assumption_id"] = "beta_ea_tdc_h0_matched_total_deposits_anchor_v1"
    row["beta"] = beta
    row["beta_source_status"] = "source_grade_ea_tdc_anchor"
    row["chi_assumption_id"] = "chi_ratewall_default_20260630"
    row["chi"] = chi
    row["chi_source_status"] = "assumption_mode"
    row["beta_times_chi"] = "0.043144460481941931"
    row["marginal_tdc_support_bil"] = "0.086288920963883862"
    _write_csv(path, rows)


def _write_beta_schedule(
    tmp_path: Path,
    *,
    period: str,
    state_id: str,
    beta: str = "0.5",
    chi: str = "0.4",
) -> Path:
    path = tmp_path / "ratewall_marginal_tdc_beta_schedule.csv"
    row = {
        "beta_schedule_row_id": f"marginal_tdc_beta::forecast::{period}::{state_id}::central",
        "object_id": "RW_M_PLUS_100BP_YEAR",
        "period_object": "forecast",
        "period": period,
        "state_id": state_id,
        "state_kind": "forecast_state",
        "horizon": "annual_h1_100bp_year",
        "shock_path_id": "plus_100bp_year",
        "shock_bps_year": "100",
        "demand_conversion_case": "central",
        "beta_assumption_id": "beta_ea_tdc_h0_matched_total_deposits_anchor_v1",
        "beta_selected": beta,
        "beta_low": "0.34201759129420367",
        "beta_high": "0.729969",
        "beta_legacy_scaffold": "0.34201759129420367",
        "beta_source_artifact": "ea-tdc/output/models/paper_tier2_selected_credit_rate_lags_estimates.csv",
        "beta_source_field": "normalized_beta",
        "beta_source_sample_start": "2002Q1",
        "beta_source_sample_end": "2025Q4",
        "beta_method": "ea_tdc_h0_matched_total_deposits_source_anchor",
        "beta_projection_method": "flat_carry_forward_from_2025Q4",
        "beta_source_status": "source_grade_ea_tdc_anchor",
        "beta_selection_status": "selected_source_grade_ea_tdc_anchor_flat_forecast",
        "time_varying_proxy_available": "false",
        "time_varying_proxy_central": "",
        "time_varying_proxy_low": "",
        "time_varying_proxy_high": "",
        "time_varying_proxy_source_artifact": "",
        "chi_assumption_id": "chi_ratewall_default_20260630",
        "chi_selected": chi,
        "chi_low": "0.03",
        "chi_high": "0.12",
        "chi_source_status": "assumption_mode",
        "beta_times_chi_selected": str(Decimal(beta) * Decimal(chi)),
        "claim_boundary": "selected_tdc_beta_is_ea_tdc_anchor_not_time_varying_proxy_or_legacy_scaffold",
    }
    _write_csv(path, [row])
    return path
