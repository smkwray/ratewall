from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter
from pathlib import Path

import yaml

from ratewall.databook.ratewall_layer_registries import ARCHITECTURE_GUARDRAIL_FIELDS


OUTPUTS = Path("outputs/tables")
TABLE_PLATE = Path("outputs/reports/ratewall_table_plate.md")
RELEASE_INDEX = Path("outputs/reports/ratewall_release_artifact_index.md")
SOURCE_ARCHIVE = Path("outputs/release/ratewall_release_23_0_source_archive.zip")
ARTIFACT = "ratewall_paper_core_results_index.csv"
REPO_ROOT = Path(__file__).resolve().parents[1]
KEEP_MANIFEST = REPO_ROOT / "configs/ratewall_keep_tables_20260607.yml"
COMPETING_DRIVER_FRONTIERS = {
    "ratewall_paper_sensitivity_summary.csv",
    "ratewall_frontier_driver_ranking.csv",
    "ratewall_assumption_mode_driver_dominance_matrix.csv",
}


def _rows(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _assert_fail_closed(rows: list[dict[str, str]]) -> None:
    assert rows
    for row in rows:
        assert row["canonical_ratio_entry"] == "false"
        for field in ARCHITECTURE_GUARDRAIL_FIELDS:
            assert row[field] == "false"


def test_paper_core_results_index_is_compact_and_fail_closed() -> None:
    rows = _rows(ARTIFACT)
    _assert_fail_closed(rows)

    assert len(rows) == 15
    assert Counter(row["category"] for row in rows) == {
        "component_bridge": 1,
        "sensitivity": 6,
        "backend": 1,
        "guardrail": 4,
        "diagnostic": 2,
        "legacy": 1,
    }
    assert {row["allowed_for_claims"] for row in rows} <= {"true", "false"}
    assert {
        row["output_name"]
        for row in rows
        if row["allowed_for_claims"] == "true"
    } == {
        "ratewall_forecast_path_ratio_pass_through_scenario_registry.csv",
        "ratewall_joint_wall_probability_summary.csv",
        "ratewall_critical_beta_frontier.csv",
        "ratewall_2d_wall_phase_diagram.csv",
        "ratewall_historical_closest_approach_clean.csv",
        "ratewall_minimum_conditions_to_hit_wall.csv",
        "ratewall_reference_scenario_object_crosswalk.csv",
    }
    assert [
        row["output_name"]
        for row in rows
        if row["paper_role"] == "designated_sensitivity_driver_frontier"
    ] == ["ratewall_critical_beta_frontier.csv"]
    assert not ({row["output_name"] for row in rows} & COMPETING_DRIVER_FRONTIERS)

    missing = [row["path"] for row in rows if not Path(row["path"]).exists()]
    assert not missing


def test_paper_core_results_index_names_claim_uses_and_replacements() -> None:
    rows = _rows(ARTIFACT)
    by_output = {row["output_name"]: row for row in rows}
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    readme_words = " ".join(readme_text.split())
    assert "Two-headline crosswalk" in readme_text
    assert "static `rw_legacy_static_assumption_mode` currently" in readme_text
    assert "0.04157132893140423351153088093" in readme_text
    assert "0.7999562733566150813589606680" in readme_text
    assert "0.6269427811677864744139409715" in readme_text
    assert "is not the provisional selector" in readme_words
    assert "tdcsim 0.3.0 re-pin/crosswalk closure" in readme_words
    assert "scenario handle, and claim boundary" in readme_words
    assert "Base-N load-bearing decomposition" in readme_text
    assert "static RW `0.04157132893140423351153088093`" in readme_text
    assert "N=`10.2766218409779053969792000`" in readme_text
    assert "future-remittance drag" in readme_text
    assert "Default `pytest` is green only after the default keeper databook build" in (
        readme_text
    )
    assert "a buildless fresh checkout is not a supported green-suite claim" in (
        readme_words
    )

    explicit_beta = by_output[
        "ratewall_forecast_path_ratio_pass_through_scenario_registry.csv"
    ]
    assert explicit_beta["category"] == "sensitivity"
    assert explicit_beta["allowed_for_claims"] == "true"
    assert explicit_beta["claim_use_status"] == "conditional_sensitivity_claims_only"
    assert "not the headline kappa_D forecast leg" in explicit_beta["reason"]
    assert "headline_forecast_tdc_leg" in explicit_beta["blocked_use"]
    assert "posterior_beta_claim" in explicit_beta["blocked_use"]

    holder_bridge = by_output["ratewall_forecast_holder_tdc_consistency_bridge.csv"]
    assert holder_bridge["category"] == "component_bridge"
    assert holder_bridge["allowed_for_claims"] == "false"
    assert "ex-direct-interest-overlap" in holder_bridge["reason"]
    assert "explicit beta pass-through" in (
        holder_bridge["safe_sentence"]
    )
    assert "headline_wall_ratio_claim" in holder_bridge["blocked_use"]

    joint_summary = by_output["ratewall_joint_wall_probability_summary.csv"]
    assert joint_summary["category"] == "sensitivity"
    assert "empirical_probability_claim" in joint_summary["blocked_use"]
    assert "conditional named-grid shares" in joint_summary["safe_sentence"]

    legacy_static = by_output["ratewall_paper_canonical_scenario_results.csv"]
    assert legacy_static["category"] == "legacy"
    assert legacy_static["allowed_for_claims"] == "false"
    assert legacy_static["replacement_if_legacy"] == (
        "ratewall_forecast_path_ratio_pass_through_scenario_registry.csv"
    )

    critical_beta = by_output["ratewall_critical_beta_frontier.csv"]
    assert critical_beta["category"] == "sensitivity"
    assert critical_beta["paper_role"] == "designated_sensitivity_driver_frontier"
    assert critical_beta["allowed_for_claims"] == "true"
    assert "full-TDC deposit-balance beta contract" in critical_beta["reason"]
    assert "posterior_beta_claim" in critical_beta["blocked_use"]

    minimum_conditions = by_output["ratewall_minimum_conditions_to_hit_wall.csv"]
    assert minimum_conditions["category"] == "sensitivity"
    assert minimum_conditions["allowed_for_claims"] == "true"
    assert minimum_conditions["claim_boundary"]
    assert "conditional parameter values" in minimum_conditions["safe_sentence"]
    assert "0.0918-class value to a state-neutral" in minimum_conditions["safe_sentence"]
    assert "0.078-class value" in minimum_conditions["safe_sentence"]
    assert "0.04157132893140423351153088093" in minimum_conditions["safe_sentence"]
    assert "Two-headline crosswalk" in minimum_conditions["safe_sentence"]
    assert "0.7999562733566150813589606680" in (
        minimum_conditions["safe_sentence"]
    )
    assert "tdcsim 0.3.0 re-pin/crosswalk closure" in (
        minimum_conditions["safe_sentence"]
    )
    assert "empirical wall claim" in minimum_conditions["safe_sentence"]

    phase_diagram = by_output["ratewall_2d_wall_phase_diagram.csv"]
    assert phase_diagram["category"] == "sensitivity"
    assert phase_diagram["paper_role"] == "two_dimensional_wall_phase_figure_source"
    assert phase_diagram["allowed_for_claims"] == "true"
    assert "existing calibrated handles" in phase_diagram["safe_sentence"]
    assert "new_channel_activation" in phase_diagram["blocked_use"]

    for output_name in COMPETING_DRIVER_FRONTIERS:
        path = OUTPUTS / output_name
        if not path.exists():
            continue
        row = next(csv.DictReader(path.open(encoding="utf-8")))
        assert row["claim_boundary"].endswith("_not_empirical_estimate")


def test_static_base_marks_only_genuinely_inert_interest_terms() -> None:
    rows = _rows("ratewall_wall_hit_scenarios.csv")
    base = next(
        row for row in rows if row["assumption_set"] == "base_current_100bps"
    )

    assert base["on_rrp_recipient_map_status"] == (
        "conditionally_active_on_rrp_reinflation"
    )
    assert base["current_remittance_capacity_status"] == (
        "conditionally_active_remittances_resume"
    )
    assert base["future_remittance_timing_status"] == (
        "load_bearing_future_drag_current_demand_offset"
    )
    assert base["future_remittance_drag_demand_offset_bil"] == "-1.516294566500"
    assert base["scalar_countervailing_total_bil"] == (
        "10.2766218409779053969792000"
    )
    assert base["ratewall_offset_ratio"] == (
        "0.04157132893140423351153088093"
    )


def test_keep_manifest_tier1_matches_paper_core_designation() -> None:
    rows = _rows(ARTIFACT)
    indexed_outputs = {row["output_name"] for row in rows}
    manifest = yaml.safe_load(KEEP_MANIFEST.read_text(encoding="utf-8"))
    tier1 = manifest["tiers"]["tier1_paper_core"]
    by_output = {row["output_name"]: row for row in tier1}

    assert indexed_outputs <= set(by_output)
    assert by_output["ratewall_minimum_conditions_to_hit_wall.csv"]["source"] == (
        "paper_core"
    )
    assert by_output["ratewall_minimum_conditions_to_hit_wall.csv"]["reason"] == (
        "paper_core_results_index"
    )
    assert not (set(by_output) & COMPETING_DRIVER_FRONTIERS)

    paper_core_by_output = {row["output_name"]: row for row in rows}
    historical_closest = paper_core_by_output[
        "ratewall_historical_closest_approach_clean.csv"
    ]
    assert historical_closest["category"] == "sensitivity"
    assert historical_closest["allowed_for_claims"] == "true"
    assert "near-zero" in historical_closest["reason"]
    assert "exact_wall_crossing_date" in historical_closest["blocked_use"]


def test_keep_manifest_retains_tdc_assumption_mode_channel() -> None:
    manifest = yaml.safe_load(KEEP_MANIFEST.read_text(encoding="utf-8"))
    keep_names = {
        row["output_name"]
        for rows in manifest["tiers"].values()
        for row in rows
    }
    assert "ratewall_tdc_assumption_mode_channel.csv" in keep_names

    active = {
        Path(row["artifact_path"]).name: row
        for row in _rows("ratewall_active_output_index.csv")
    }
    tdc = active["ratewall_tdc_assumption_mode_channel.csv"]
    assert tdc["ratio_object_id"] == "rw_tdc_forward_headline_assumption_mode"
    assert tdc["active_status"] == "active_main"
    assert tdc["canonical_ratio_entry"] == "false"


def test_paper_core_results_index_is_active_released_and_archived() -> None:
    active = {Path(row["artifact_path"]).name for row in _rows("ratewall_active_output_index.csv")}
    assert {
        ARTIFACT,
        "ratewall_forecast_path_ratio_pass_through_scenario_registry.csv",
        "ratewall_2d_wall_phase_diagram.csv",
        "ratewall_critical_beta_frontier.csv",
        "ratewall_historical_closest_approach_clean.csv",
        "ratewall_minimum_conditions_to_hit_wall.csv",
    } <= active

    manifest = json.loads(
        (OUTPUTS / "ratewall_release_manifest.json").read_text(encoding="utf-8")
    )
    listed = set().union(
        *(set(layer) for layer in manifest["artifact_layers"].values())
    )
    assert f"outputs/tables/{ARTIFACT}" in listed

    for path in (TABLE_PLATE, RELEASE_INDEX):
        text = path.read_text(encoding="utf-8")
        assert ARTIFACT in text

    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        names = set(archive.namelist())
    assert f"outputs/tables/{ARTIFACT}" in names
