from __future__ import annotations

import csv
import gzip
from pathlib import Path

from ratewall.databook.direct_chi_evidence import (
    DIRECT_BETA_CHI_ESTIMATOR_CONTRACT_FIELDS,
    DIRECT_BETA_CHI_TARGET_IMPACT_FIELDS,
    DIRECT_CHI_ADJUDICATION_FIELDS,
    DIRECT_CHI_REQUIREMENT_FIELDS,
    DIRECT_CHI_SOURCE_FIELDS,
    DirectChiSourcePaths,
    direct_beta_chi_estimator_contract_rows,
    direct_beta_chi_target_impact_rows,
    direct_chi_adjudication_rows,
    direct_chi_evidence_memo_markdown,
    direct_chi_requirement_rows,
    direct_chi_source_inventory_rows,
    write_direct_chi_evidence_outputs,
)


def test_direct_chi_requirements_preserve_target_floors() -> None:
    rows = direct_chi_requirement_rows(_evidence_targets())

    assert {field for row in rows for field in row} == set(
        DIRECT_CHI_REQUIREMENT_FIELDS
    )
    first = rows[0]
    assert first["scenario_id"] == "tdcsim_combo_high_pressure_v1"
    assert first["required_chi_floor_at_existing_min_beta"] == "0.0303"
    assert first["required_beta_chi_floor"] == "0.0035"
    assert first["target_estimand"] == (
        "chi_or_beta_chi_response_to_materialized_tdc_ex_overlap_flow"
    )
    assert first["admission_status"] == "requirement_only_no_evidence_admitted"


def test_source_inventory_classifies_tdcest_and_current_demand_as_one_sided(
    tmp_path: Path,
) -> None:
    tdcest = tmp_path / "tdcest"
    tdcest.mkdir()
    _write_csv(
        tdcest / "tdc_downstream_estimator_contract.csv",
        [{"artifact_key": "tdc_tier2_interest_corrected_bank_only_ru_flow"}],
    )
    _write_csv(
        tdcest / "tdc_downstream_deposit_effect_series_panel.csv",
        [{"series_key": "tdc_tier2_interest_corrected_bank_only_ru_flow"}],
    )
    current_demand = tmp_path / "current_demand"
    current_demand.mkdir()
    (current_demand / "PCEC.csv").write_text("DATE,VALUE\n2026-01-01,1\n")

    rows = direct_chi_source_inventory_rows(
        paths=DirectChiSourcePaths(
            tdcsim_suite_dir=tmp_path / "missing_suite",
            tdcest_downstream_dir=tdcest,
            local_current_demand_dir=current_demand,
        )
    )

    assert {field for row in rows for field in row} == set(DIRECT_CHI_SOURCE_FIELDS)
    by_family = {row["source_family"]: row for row in rows}
    assert by_family["tdcest_downstream_contract"]["candidate_role"] == (
        "tdc_treatment_side_only"
    )
    assert by_family["tdcest_downstream_contract"]["has_materialized_tdc_treatment"] == (
        "true"
    )
    assert by_family["tdcest_downstream_contract"]["has_current_demand_outcome"] == (
        "false"
    )
    assert by_family["ratewall_current_demand_gdp_share"]["candidate_role"] == (
        "current_demand_outcome_side_only"
    )
    assert by_family["ratewall_current_demand_gdp_share"][
        "has_current_demand_outcome"
    ] == "true"
    assert by_family["ratewall_current_demand_gdp_share"][
        "admissibility_status"
    ] == "not_admitted_missing_tdc_ex_overlap_treatment"


def test_source_inventory_classifies_tdcsim_suite_as_treatment_side(
    tmp_path: Path,
) -> None:
    suite = tmp_path / "suite"
    suite.mkdir()
    _write_csv(
        suite / "ratewall_tdcsim_cbo_fiscal_year_ratio_input.csv",
        [
            {
                "scenario_id": "scenario_a",
                "fiscal_year": "2027",
                "tdc_change_ex_overlap_bil": "10",
            }
        ],
    )

    rows = direct_chi_source_inventory_rows(
        paths=DirectChiSourcePaths(
            tdcsim_suite_dir=suite,
            tdcest_downstream_dir=tmp_path / "missing_tdcest",
            local_current_demand_dir=tmp_path / "missing_current_demand",
        )
    )

    assert len(rows) == 1
    assert rows[0]["source_family"] == "tdcsim_cbo_ratewall_ratio_input"
    assert rows[0]["candidate_role"] == "tdc_ex_overlap_treatment_side_only"
    assert rows[0]["has_tdc_ex_overlap_treatment"] == "true"
    assert rows[0]["has_current_demand_outcome"] == "false"
    assert rows[0]["admissibility_status"] == (
        "not_admitted_missing_current_demand_outcome"
    )


def test_source_inventory_classifies_tdcsim_period_tdc_exports_as_treatment_side(
    tmp_path: Path,
) -> None:
    suite = tmp_path / "suite"
    outputs = suite / "outputs"
    outputs.mkdir(parents=True)
    _write_gzip_csv(
        outputs / "tdcsim_period_tdc_summary.csv.gz",
        [
            {
                "period_start": "2027-01-01",
                "period_end": "2027-01-02",
                "tdc_change_ex_overlap_bil": "10",
            }
        ],
    )
    _write_gzip_csv(
        outputs / "tdcsim_period_tdc_components.csv.gz",
        [
            {
                "period_start": "2027-01-01",
                "period_end": "2027-01-02",
                "amount_bil": "4",
                "is_additive_to_tdc_change": "True",
                "enters_tdc_deposit_support_default": "True",
            }
        ],
    )

    rows = direct_chi_source_inventory_rows(
        paths=DirectChiSourcePaths(
            tdcsim_suite_dir=suite,
            tdcest_downstream_dir=tmp_path / "missing_tdcest",
            local_current_demand_dir=tmp_path / "missing_current_demand",
        )
    )

    assert len(rows) == 2
    assert {row["source_family"] for row in rows} == {
        "tdcsim_cbo_period_tdc_accounting"
    }
    assert {row["has_tdc_ex_overlap_treatment"] for row in rows} == {"true"}
    assert {row["has_materialized_tdc_treatment"] for row in rows} == {"true"}
    assert {row["has_current_demand_outcome"] for row in rows} == {"false"}
    assert {row["has_identification_strategy"] for row in rows} == {"false"}
    assert {row["admissibility_status"] for row in rows} == {
        "not_admitted_missing_current_demand_outcome"
    }


def test_direct_chi_adjudication_fails_closed_without_direct_candidate() -> None:
    requirements = direct_chi_requirement_rows(_evidence_targets())
    sources = [
        {
            "direct_chi_source_row_id": "source::tdcest",
            "source_family": "tdcest",
            "source_artifact": "tdcest.csv",
            "candidate_role": "tdc_treatment_side_only",
            "row_count": "10",
            "has_tdc_ex_overlap_treatment": "false",
            "has_materialized_tdc_treatment": "true",
            "has_current_demand_outcome": "false",
            "has_identification_strategy": "false",
            "reports_chi_lower_bound": "false",
            "reported_chi_lower_bound": "",
            "reports_beta_chi_lower_bound": "false",
            "reported_beta_chi_lower_bound": "",
            "admissibility_status": "not_admitted_missing_tdc_ex_overlap_treatment",
            "admissibility_obstacle": "treatment_only",
            "allowed_use": "screen",
            "blocked_use": "floor",
            "claim_boundary": "screen",
        }
    ]

    rows = direct_chi_adjudication_rows(
        requirement_rows=requirements,
        source_rows=sources,
    )

    assert {field for row in rows for field in row} == set(
        DIRECT_CHI_ADJUDICATION_FIELDS
    )
    assert {row["admission_result"] for row in rows} == {
        "not_admitted_no_direct_chi_or_beta_chi_evidence"
    }
    assert {row["post_review_model_action"] for row in rows} == {
        "keep_point_calibrated_build_direct_estimator"
    }


def test_direct_beta_chi_estimator_contract_requires_joint_identified_panel() -> None:
    requirements = direct_chi_requirement_rows(_evidence_targets())
    sources = [
        _source(
            row_id="source::tdcsim",
            role="tdc_ex_overlap_treatment_side_only",
            has_treatment="true",
            has_materialized="true",
        ),
        _source(
            row_id="source::current_demand",
            role="current_demand_outcome_side_only",
            has_outcome="true",
        ),
    ]

    rows = direct_beta_chi_estimator_contract_rows(
        requirement_rows=requirements,
        source_rows=sources,
    )

    assert {field for row in rows for field in row} == set(
        DIRECT_BETA_CHI_ESTIMATOR_CONTRACT_FIELDS
    )
    assert {row["current_tdc_treatment_source_status"] for row in rows} == {
        "present"
    }
    assert {row["current_outcome_source_status"] for row in rows} == {"present"}
    assert {row["current_identification_source_status"] for row in rows} == {
        "missing"
    }
    assert {row["current_contract_status"] for row in rows} == {
        "blocked_missing_identification_strategy"
    }
    assert {row["admission_status"] for row in rows} == {
        "contract_only_no_floor_admitted"
    }


def test_direct_beta_chi_target_impact_identifies_future_reclassification() -> None:
    requirements = direct_chi_requirement_rows(_evidence_targets())
    adjudications = direct_chi_adjudication_rows(
        requirement_rows=requirements,
        source_rows=[_direct_candidate(beta_chi_lower_bound="0.006")],
    )

    rows = direct_beta_chi_target_impact_rows(
        requirement_rows=requirements,
        adjudication_rows=adjudications,
    )

    assert {field for row in rows for field in row} == set(
        DIRECT_BETA_CHI_TARGET_IMPACT_FIELDS
    )
    assert {row["current_claim_status"] for row in rows} == {
        "direct_floor_admitted"
    }
    assert {row["if_floor_admitted_model_action"] for row in rows} == {
        "reclassify_as_sign_robust_over_admitted_beta_chi_floor"
    }


def test_direct_chi_adjudication_can_admit_future_chi_lower_bound() -> None:
    requirements = direct_chi_requirement_rows(_evidence_targets())
    sources = [_direct_candidate(chi_lower_bound="0.04")]

    rows = direct_chi_adjudication_rows(
        requirement_rows=requirements,
        source_rows=sources,
    )

    by_scenario = {row["scenario_id"]: row for row in rows}
    assert by_scenario["tdcsim_combo_high_pressure_v1"]["admission_result"] == (
        "admit_floor_from_direct_evidence"
    )
    assert by_scenario["tdcsim_holder_bank_from_private_v1"]["admission_result"] == (
        "not_admitted_direct_candidate_below_required_floor"
    )


def test_direct_chi_adjudication_can_admit_future_beta_chi_product_floor() -> None:
    requirements = direct_chi_requirement_rows(_evidence_targets())
    sources = [_direct_candidate(beta_chi_lower_bound="0.006")]

    rows = direct_chi_adjudication_rows(
        requirement_rows=requirements,
        source_rows=sources,
    )

    assert {row["admission_result"] for row in rows} == {
        "admit_floor_from_direct_evidence"
    }


def test_direct_chi_outputs_write_csvs_and_memo(tmp_path: Path) -> None:
    requirements = direct_chi_requirement_rows(_evidence_targets())
    sources = direct_chi_source_inventory_rows(
        paths=DirectChiSourcePaths(
            tdcsim_suite_dir=tmp_path / "missing_suite",
            tdcest_downstream_dir=tmp_path / "missing_tdcest",
            local_current_demand_dir=tmp_path / "missing_current_demand",
        )
    )
    adjudications = direct_chi_adjudication_rows(
        requirement_rows=requirements,
        source_rows=sources,
    )
    estimator_contracts = direct_beta_chi_estimator_contract_rows(
        requirement_rows=requirements,
        source_rows=sources,
    )
    target_impacts = direct_beta_chi_target_impact_rows(
        requirement_rows=requirements,
        adjudication_rows=adjudications,
    )

    outputs = write_direct_chi_evidence_outputs(
        tmp_path,
        requirement_rows=requirements,
        source_rows=sources,
        adjudication_rows=adjudications,
        estimator_contract_rows=estimator_contracts,
        target_impact_rows=target_impacts,
    )

    assert outputs["requirements_csv"].read_text(encoding="utf-8").startswith(
        "direct_chi_requirement_row_id,"
    )
    assert outputs["source_inventory_csv"].read_text(encoding="utf-8").startswith(
        "direct_chi_source_row_id,"
    )
    assert outputs["adjudication_csv"].read_text(encoding="utf-8").startswith(
        "direct_chi_adjudication_row_id,"
    )
    assert outputs["estimator_contract_csv"].read_text(
        encoding="utf-8"
    ).startswith("direct_beta_chi_estimator_contract_row_id,")
    assert outputs["target_impact_csv"].read_text(encoding="utf-8").startswith(
        "direct_beta_chi_target_impact_row_id,"
    )
    memo = direct_chi_evidence_memo_markdown(
        requirement_rows=requirements,
        source_rows=sources,
        adjudication_rows=adjudications,
        estimator_contract_rows=estimator_contracts,
        target_impact_rows=target_impacts,
    )
    assert outputs["memo_md"].read_text(encoding="utf-8") == memo
    assert "No direct" in memo


def _evidence_targets() -> list[dict[str, str]]:
    return [
        {
            "fiscal_year": "2027",
            "scenario_id": "tdcsim_combo_high_pressure_v1",
            "scenario_axis": "combined_holder_rate",
            "evidence_distance_tier": "near_existing_floor",
            "required_chi_floor_at_existing_min_beta": "0.0303",
            "required_beta_chi_floor": "0.0035",
            "required_beta_floor_at_existing_min_chi": "0.1167",
            "current_beta_times_chi": "0.0239",
            "selected_moving_delta_ratewall_ratio_vs_baseline": "0.329",
        },
        {
            "fiscal_year": "2027",
            "scenario_id": "tdcsim_holder_bank_from_private_v1",
            "scenario_axis": "holder_only",
            "evidence_distance_tier": "large_lift",
            "required_chi_floor_at_existing_min_beta": "0.086",
            "required_beta_chi_floor": "0.004",
            "required_beta_floor_at_existing_min_chi": "0.133",
            "current_beta_times_chi": "0.0239",
            "selected_moving_delta_ratewall_ratio_vs_baseline": "0.101",
        },
    ]


def _direct_candidate(
    *,
    chi_lower_bound: str = "",
    beta_chi_lower_bound: str = "",
) -> dict[str, str]:
    return {
        "direct_chi_source_row_id": "direct_chi_source::future_estimator",
        "source_family": "future_estimator",
        "source_artifact": "future.csv",
        "candidate_role": "direct_chi_or_beta_chi_estimator",
        "row_count": "1",
        "has_tdc_ex_overlap_treatment": "true",
        "has_materialized_tdc_treatment": "true",
        "has_current_demand_outcome": "true",
        "has_identification_strategy": "true",
        "reports_chi_lower_bound": "true" if chi_lower_bound else "false",
        "reported_chi_lower_bound": chi_lower_bound,
        "reports_beta_chi_lower_bound": "true" if beta_chi_lower_bound else "false",
        "reported_beta_chi_lower_bound": beta_chi_lower_bound,
        "admissibility_status": "admissible",
        "admissibility_obstacle": "",
        "allowed_use": "direct_floor",
        "blocked_use": "canonical_without_owner_gate",
        "claim_boundary": "fixture",
    }


def _source(
    *,
    row_id: str,
    role: str,
    has_treatment: str = "false",
    has_materialized: str = "false",
    has_outcome: str = "false",
    has_identification: str = "false",
) -> dict[str, str]:
    return {
        "direct_chi_source_row_id": row_id,
        "source_family": row_id,
        "source_artifact": f"{row_id}.csv",
        "candidate_role": role,
        "row_count": "1",
        "has_tdc_ex_overlap_treatment": has_treatment,
        "has_materialized_tdc_treatment": has_materialized,
        "has_current_demand_outcome": has_outcome,
        "has_identification_strategy": has_identification,
        "reports_chi_lower_bound": "false",
        "reported_chi_lower_bound": "",
        "reports_beta_chi_lower_bound": "false",
        "reported_beta_chi_lower_bound": "",
        "admissibility_status": "not_admitted_fixture",
        "admissibility_obstacle": "fixture",
        "allowed_use": "screen",
        "blocked_use": "floor",
        "claim_boundary": "fixture",
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_gzip_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
