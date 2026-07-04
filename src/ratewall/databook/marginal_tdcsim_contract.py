"""RateWall ingest validator for TDCSim marginal TDC pair outputs."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from ratewall.databook.marginal_tdc_beta import (
    lookup_beta_schedule_row,
)
from ratewall.databook.table_io import write_rows

DEFAULT_PAIR_DIR = Path("var/preliminary_scenario_results/marginal_tdcsim/source_pair")
DEFAULT_PAIR_ROOT = Path("var/preliminary_scenario_results/marginal_tdcsim/source_pairs")

SUMMARY_FILE = "tdcsim_ratewall_marginal_tdc_summary.csv"
MANIFEST_FILE = "tdcsim_ratewall_marginal_tdc_pair_manifest.json"
PAIR_SCHEMA_VERSION = "tdcsim_cbo_marginal_tdc_pair_v1"
MANIFEST_SCHEMA_VERSION = "tdcsim_cbo_marginal_tdc_manifest_v1"
OBJECT_ID = "RW_M_PLUS_100BP_YEAR"
SHOCK_PATH_ID = "plus_100bp_year"
CONTRACT_FAMILY = "ratewall_marginal_pair"
CONTRACT_VERSION = "0.4.0"
CLAIM_BOUNDARY = "tdcsim_marginal_pair_assumption_mode_not_evidence_not_channel_classifier"
SUMMARY_DECIMAL_TOLERANCE = Decimal("0.000000001")

REQUIRED_SUMMARY_FIELDS = {
    "schema_version",
    "contract_version",
    "pair_id",
    "object_id",
    "shock_path_id",
    "shock_bps_year",
    "state_id",
    "state_kind",
    "state_period",
    "scenario_id",
    "scenario_state_set_id",
    "state_fingerprint_sha256",
    "state_component_inventory_sha256",
    "period",
    "period_start",
    "period_end",
    "horizon",
    "demand_conversion_case",
    "baseline_run_id",
    "shock_run_id",
    "tdc_change_baseline_bil",
    "tdc_change_shock_bil",
    "delta_tdc_change_bil",
    "overlap_baseline_bil",
    "overlap_shock_bil",
    "delta_overlap_bil",
    "tdc_change_ex_overlap_baseline_bil",
    "tdc_change_ex_overlap_shock_bil",
    "delta_tdc_ex_overlap_bil",
    "beta",
    "beta_assumption_id",
    "beta_source_status",
    "chi",
    "chi_assumption_id",
    "chi_source_status",
    "beta_times_chi",
    "tdc_amount_basis",
    "support_formula",
    "marginal_tdc_support_bil",
    "same_state_status",
    "rate_shock_only_status",
    "shock_path_validation_status",
    "period_alignment_status",
    "overlap_identity_status",
    "component_identity_status",
    "route_identity_status",
    "support_identity_status",
    "state_manifest_status",
    "contract_ingest_status",
    "failure_reason",
    "assumption_mode",
    "evidence_mode_enabled",
    "raw_rate_shock_enabled",
    "named_marginal_shock_path_enabled",
    "tdcsim_channel_classifier_enabled",
    "enters_main_ratio_candidate",
    "canonical_ratio_entry",
    "claim_boundary",
}

MARGINAL_TDCSIM_CONTRACT_INGEST_FIELDS = [
    "marginal_tdcsim_contract_ingest_row_id",
    "pair_dir",
    "manifest_path",
    "summary_path",
    "manifest_schema_version",
    "pair_schema_version",
    "contract_family",
    "contract_version",
    "object_id",
    "shock_path_id",
    "summary_row_count",
    "contract_ingest_status",
    "failure_reason",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_TDC_SUPPORT_PANEL_FIELDS = [
    "marginal_tdc_support_row_id",
    "pair_id",
    "object_id",
    "shock_path_id",
    "shock_bps_year",
    "state_id",
    "state_kind",
    "state_period",
    "scenario_id",
    "source_vintage",
    "source_grade_status",
    "state_construction_method",
    "forecast_state_export_manifest_sha256",
    "derived_state_package_sha256",
    "parent_baseline_package_sha256",
    "rollforward_run_manifest_sha256",
    "compiled_non_rate_inputs_digest",
    "scenario_state_set_id",
    "state_fingerprint_sha256",
    "state_manifest_status",
    "period",
    "period_start",
    "period_end",
    "horizon",
    "demand_conversion_case",
    "baseline_run_id",
    "shock_run_id",
    "delta_tdc_change_bil",
    "delta_overlap_bil",
    "delta_tdc_ex_overlap_bil",
    "beta_assumption_id",
    "beta",
    "chi_assumption_id",
    "chi",
    "beta_times_chi",
    "tdc_amount_basis",
    "overlap_scope",
    "marginal_tdc_support_bil",
    "support_formula",
    "component_identity_status",
    "route_identity_status",
    "state_composition_status",
    "selected_tdc_formula_pass",
    "enters_selected_rw_m",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_TDC_STATE_COMPOSITION_AUDIT_FIELDS = [
    "marginal_tdc_state_composition_audit_row_id",
    "pair_id",
    "scenario_state_set_id",
    "state_id",
    "state_fingerprint_sha256",
    "shock_path_id",
    "horizon",
    "demand_conversion_case",
    "state_manifest_status",
    "full_key_status",
    "selected_tdc_admission_status",
    "failure_reason",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class MarginalTDCSimContractError(ValueError):
    """Raised when TDCSim marginal TDC output is not admissible."""


def ingest_marginal_tdcsim_pair(
    *,
    pair_dir: str | Path = DEFAULT_PAIR_DIR,
    beta_schedule_path: str | Path | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Validate a TDCSim marginal pair directory and return RateWall ingest rows."""

    root = Path(pair_dir)
    if not root.exists():
        ingest = [_fail_closed_ingest_row(root, "missing marginal TDCSim pair directory")]
        audit = marginal_tdc_state_composition_audit_rows([])
        return {
            "ingest_rows": ingest,
            "support_rows": [],
            "state_composition_audit_rows": audit,
        }
    manifest_path = root / MANIFEST_FILE
    summary_path = root / SUMMARY_FILE
    try:
        manifest = _read_manifest(manifest_path)
        summary = _read_summary(summary_path)
        _validate_manifest(manifest)
        _validate_summary(summary)
        support_rows = marginal_tdc_support_rows(
            summary,
            beta_schedule_path=beta_schedule_path,
        )
        audit_rows = marginal_tdc_state_composition_audit_rows(support_rows)
        ingest_rows = [
            {
                "marginal_tdcsim_contract_ingest_row_id": (
                    f"marginal_tdcsim_contract_ingest::{manifest['pair_id']}"
                ),
                "pair_dir": str(root),
                "manifest_path": str(manifest_path),
                "summary_path": str(summary_path),
                "manifest_schema_version": str(manifest["schema_version"]),
                "pair_schema_version": str(
                    manifest.get("pair_spec", {}).get("schema_version", "")
                ),
                "contract_family": CONTRACT_FAMILY,
                "contract_version": CONTRACT_VERSION,
                "object_id": OBJECT_ID,
                "shock_path_id": SHOCK_PATH_ID,
                "summary_row_count": str(len(summary)),
                "contract_ingest_status": "pass_tdcsim_v0p4_marginal_pair_ingested",
                "failure_reason": "",
                "allowed_use": "marginal_tdc_support_panel_candidate",
                "blocked_use": "tdcsim_v0p3_output;full_tdc_level;observed_tdc_level",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        ]
    except (OSError, KeyError, ValueError, MarginalTDCSimContractError) as exc:
        ingest_rows = [_fail_closed_ingest_row(root, str(exc))]
        support_rows = []
        audit_rows = marginal_tdc_state_composition_audit_rows(support_rows)
    validate_marginal_tdcsim_contract_ingest(ingest_rows)
    validate_marginal_tdc_support_panel(support_rows, allow_empty=True)
    validate_marginal_tdc_state_composition_audit_rows(audit_rows)
    return {
        "ingest_rows": ingest_rows,
        "support_rows": support_rows,
        "state_composition_audit_rows": audit_rows,
    }


def ingest_marginal_tdcsim_pairs(
    *,
    pair_dirs: Sequence[str | Path] | None = None,
    pair_root: str | Path | None = None,
    beta_schedule_path: str | Path | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Validate one or more TDCSim marginal pair directories."""

    roots = [Path(path) for path in pair_dirs or []]
    if pair_root is not None:
        root = Path(pair_root)
        if root.exists():
            roots.extend(
                sorted(
                    path
                    for path in root.iterdir()
                    if path.is_dir() and (path / MANIFEST_FILE).exists()
                )
            )
        elif not roots:
            roots.append(root)
    if not roots:
        roots.append(DEFAULT_PAIR_DIR)

    ingest_rows: list[dict[str, str]] = []
    support_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    for root in roots:
        tables = ingest_marginal_tdcsim_pair(
            pair_dir=root,
            beta_schedule_path=beta_schedule_path,
        )
        ingest_rows.extend(tables["ingest_rows"])
        support_rows.extend(tables["support_rows"])
        audit_rows.extend(tables["state_composition_audit_rows"])

    support_rows = _prefer_source_grade_support_rows(support_rows)
    audit_rows = marginal_tdc_state_composition_audit_rows(support_rows)
    validate_marginal_tdcsim_contract_ingest(ingest_rows)
    validate_marginal_tdc_support_panel(support_rows, allow_empty=True)
    validate_marginal_tdc_state_composition_audit_rows(audit_rows)
    return {
        "ingest_rows": ingest_rows,
        "support_rows": support_rows,
        "state_composition_audit_rows": audit_rows,
    }


def _prefer_source_grade_support_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    by_key: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (
            row["period"],
            row["horizon"],
            row["state_id"],
            row["shock_path_id"],
            row["demand_conversion_case"],
        )
        candidate = dict(row)
        existing = by_key.get(key)
        candidate_rank = _source_grade_rank(candidate)
        existing_rank = _source_grade_rank(existing) if existing is not None else -1
        if existing is not None and candidate_rank > 0 and candidate_rank == existing_rank:
            raise MarginalTDCSimContractError("duplicate source-grade marginal TDC full key")
        if existing is None or candidate_rank > existing_rank:
            by_key[key] = candidate
    return list(by_key.values())


def _source_grade_rank(row: Mapping[str, str]) -> int:
    status = row.get("source_grade_status", "")
    if status == "pass_forecast_rollforward_source_grade":
        return 30
    if status == "pass_current_source_grade" or "source_grade" in row.get("pair_id", "").lower():
        return 20
    if "assumption_pair" in row.get("pair_id", "") or row.get("source_vintage") == "ratewall_assumption_mode_fixture_20260630":
        return 0
    return 0


def marginal_tdc_support_rows(
    summary_rows: Sequence[Mapping[str, str]],
    *,
    beta_schedule_path: str | Path | None = None,
) -> list[dict[str, str]]:
    beta_schedule_rows = (
        _read_summary(Path(beta_schedule_path)) if beta_schedule_path is not None else None
    )
    rows: list[dict[str, str]] = []
    for row in summary_rows:
        schedule_row = _matching_beta_schedule_row(row, beta_schedule_rows)
        beta = Decimal(str(schedule_row["beta_selected"] if schedule_row else row["beta"]))
        chi = Decimal(str(schedule_row["chi_selected"] if schedule_row else row["chi"]))
        delta_ex = Decimal(str(row["delta_tdc_ex_overlap_bil"]))
        support = delta_ex * beta * chi
        if schedule_row is not None:
            _validate_summary_beta_matches_schedule(row, schedule_row)
        rows.append(
            {
                "marginal_tdc_support_row_id": (
                    f"marginal_tdc_support::{row['pair_id']}::{row['period']}::"
                    f"{row['demand_conversion_case']}"
                ),
                "pair_id": str(row["pair_id"]),
                "object_id": str(row["object_id"]),
                "shock_path_id": str(row["shock_path_id"]),
                "shock_bps_year": str(row["shock_bps_year"]),
                "state_id": str(row["state_id"]),
                "state_kind": str(row["state_kind"]),
                "state_period": str(row["state_period"]),
                "scenario_id": str(row["scenario_id"]),
                "source_vintage": str(row.get("source_vintage", "")),
                "source_grade_status": str(row.get("source_grade_status", "")),
                "state_construction_method": str(row.get("state_construction_method", "")),
                "forecast_state_export_manifest_sha256": str(row.get("forecast_state_export_manifest_sha256", "")),
                "derived_state_package_sha256": str(row.get("derived_state_package_sha256", "")),
                "parent_baseline_package_sha256": str(row.get("parent_baseline_package_sha256", "")),
                "rollforward_run_manifest_sha256": str(row.get("rollforward_run_manifest_sha256", "")),
                "compiled_non_rate_inputs_digest": str(row.get("compiled_non_rate_inputs_digest", "")),
                "scenario_state_set_id": str(row["scenario_state_set_id"]),
                "state_fingerprint_sha256": str(row["state_fingerprint_sha256"]),
                "state_manifest_status": str(row["state_manifest_status"]),
                "period": str(row["period"]),
                "period_start": str(row["period_start"]),
                "period_end": str(row["period_end"]),
                "horizon": str(row["horizon"]),
                "demand_conversion_case": str(row["demand_conversion_case"]),
                "baseline_run_id": str(row["baseline_run_id"]),
                "shock_run_id": str(row["shock_run_id"]),
                "delta_tdc_change_bil": _fmt(Decimal(str(row["delta_tdc_change_bil"]))),
                "delta_overlap_bil": _fmt(Decimal(str(row["delta_overlap_bil"]))),
                "delta_tdc_ex_overlap_bil": _fmt(delta_ex),
                "beta_assumption_id": str(
                    schedule_row["beta_assumption_id"] if schedule_row else row["beta_assumption_id"]
                ),
                "beta": _fmt(beta),
                "chi_assumption_id": str(
                    schedule_row["chi_assumption_id"] if schedule_row else row["chi_assumption_id"]
                ),
                "chi": _fmt(chi),
                "beta_times_chi": _fmt(beta * chi),
                "tdc_amount_basis": str(row["tdc_amount_basis"]),
                "overlap_scope": str(row.get("overlap_scope", "tdcsim_and_external_support")),
                "marginal_tdc_support_bil": _fmt(support),
                "support_formula": "delta_tdc_ex_overlap_bil * beta * chi",
                "component_identity_status": str(row["component_identity_status"]),
                "route_identity_status": str(row["route_identity_status"]),
                "state_composition_status": "pass_manifest_backed_state_composition",
                "selected_tdc_formula_pass": "true",
                "enters_selected_rw_m": "true",
                "allowed_use": "selected_marginal_tdc_support_after_contract_gate",
                "blocked_use": "full_tdc_level;tdcsim_v0p3_output",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    validate_marginal_tdc_support_panel(rows, allow_empty=False)
    return rows


def marginal_tdc_state_composition_audit_rows(
    support_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Audit whether TDCSim support rows are manifest-backed scenario-state deltas."""

    if not support_rows:
        return [
            {
                "marginal_tdc_state_composition_audit_row_id": (
                    "marginal_tdc_state_composition_audit::fail_closed"
                ),
                "pair_id": "",
                "scenario_state_set_id": "",
                "state_id": "",
                "state_fingerprint_sha256": "",
                "shock_path_id": SHOCK_PATH_ID,
                "horizon": "",
                "demand_conversion_case": "",
                "state_manifest_status": "fail_closed_missing_manifest_backed_support",
                "full_key_status": "fail_closed_missing_full_keyed_support",
                "selected_tdc_admission_status": "fail_closed_no_selected_tdc_support",
                "failure_reason": "missing manifest-backed marginal TDCSim support row",
                "allowed_use": "marginal_tdc_state_composition_gap_audit",
                "blocked_use": "selected_tdc_support;selected_rw_m",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        ]
    return [
        {
            "marginal_tdc_state_composition_audit_row_id": (
                "marginal_tdc_state_composition_audit::"
                f"{row['pair_id']}::{row['period']}::{row['demand_conversion_case']}"
            ),
            "pair_id": row["pair_id"],
            "scenario_state_set_id": row["scenario_state_set_id"],
            "state_id": row["state_id"],
            "state_fingerprint_sha256": row["state_fingerprint_sha256"],
            "shock_path_id": row["shock_path_id"],
            "horizon": row["horizon"],
            "demand_conversion_case": row["demand_conversion_case"],
            "state_manifest_status": row["state_manifest_status"],
            "full_key_status": "pass_full_marginal_tdc_key_present",
            "selected_tdc_admission_status": "pass_manifest_backed_marginal_support_candidate",
            "failure_reason": "",
            "allowed_use": "marginal_tdc_state_composition_audit",
            "blocked_use": "full_tdc_level;cross_state_subtraction",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for row in support_rows
    ]


def write_marginal_tdcsim_outputs(
    output_dir: str | Path,
    *,
    ingest_rows: Sequence[Mapping[str, str]],
    support_rows: Sequence[Mapping[str, str]],
    state_composition_audit_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "contract_ingest_csv": out / "ratewall_marginal_tdcsim_contract_ingest.csv",
        "support_panel_csv": out / "ratewall_marginal_tdc_support_panel.csv",
        "state_composition_audit_csv": (
            out / "ratewall_marginal_tdc_state_composition_audit.csv"
        ),
    }
    write_rows(
        paths["contract_ingest_csv"],
        [dict(row) for row in ingest_rows],
        MARGINAL_TDCSIM_CONTRACT_INGEST_FIELDS,
    )
    write_rows(
        paths["support_panel_csv"],
        [dict(row) for row in support_rows],
        MARGINAL_TDC_SUPPORT_PANEL_FIELDS,
    )
    write_rows(
        paths["state_composition_audit_csv"],
        [dict(row) for row in state_composition_audit_rows],
        MARGINAL_TDC_STATE_COMPOSITION_AUDIT_FIELDS,
    )
    return paths


def validate_marginal_tdcsim_contract_ingest(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalTDCSimContractError("TDCSim ingest rows are empty")
    ids: set[str] = set()
    for row in rows:
        if set(row) != set(MARGINAL_TDCSIM_CONTRACT_INGEST_FIELDS):
            raise MarginalTDCSimContractError("TDCSim ingest schema mismatch")
        row_id = row["marginal_tdcsim_contract_ingest_row_id"]
        if row_id in ids and not row_id.endswith("::fail_closed"):
            raise MarginalTDCSimContractError("duplicate TDCSim ingest row id")
        ids.add(row_id)
        if row["object_id"] and row["object_id"] != OBJECT_ID:
            raise MarginalTDCSimContractError("unsupported object_id")
        if row["shock_path_id"] and row["shock_path_id"] != SHOCK_PATH_ID:
            raise MarginalTDCSimContractError("unsupported shock_path_id")
        if row["contract_ingest_status"].startswith("pass"):
            if row["manifest_schema_version"] != MANIFEST_SCHEMA_VERSION:
                raise MarginalTDCSimContractError("unsupported manifest schema version")
            if row["pair_schema_version"] != PAIR_SCHEMA_VERSION:
                raise MarginalTDCSimContractError("unsupported pair schema version")
        if "tdcsim_v0p3_output" not in row["blocked_use"]:
            raise MarginalTDCSimContractError("old TDCSim output blocker missing")


def validate_marginal_tdc_support_panel(
    rows: Sequence[Mapping[str, str]],
    *,
    allow_empty: bool,
) -> None:
    if not rows and allow_empty:
        return
    if not rows:
        raise MarginalTDCSimContractError("marginal TDC support panel is empty")
    keys: set[tuple[str, str, str, str, str]] = set()
    for row in rows:
        if set(row) != set(MARGINAL_TDC_SUPPORT_PANEL_FIELDS):
            raise MarginalTDCSimContractError("marginal TDC support schema mismatch")
        key = (
            row["period"],
            row["horizon"],
            row["state_id"],
            row["shock_path_id"],
            row["demand_conversion_case"],
        )
        if key in keys:
            raise MarginalTDCSimContractError("duplicate marginal TDC full key")
        keys.add(key)
        if row["object_id"] != OBJECT_ID or row["shock_path_id"] != SHOCK_PATH_ID:
            raise MarginalTDCSimContractError("unsupported marginal TDC object or shock")
        if row["shock_bps_year"] != "100":
            raise MarginalTDCSimContractError("marginal TDC shock_bps_year must be 100")
        for status_field in [
            "state_manifest_status",
            "component_identity_status",
            "route_identity_status",
        ]:
            if str(row[status_field]).lower() != "pass":
                raise MarginalTDCSimContractError(f"{status_field} failed")
        if not row["state_fingerprint_sha256"]:
            raise MarginalTDCSimContractError("state fingerprint is required")
        if row["tdc_amount_basis"] != "pre_beta_ex_overlap_delta":
            raise MarginalTDCSimContractError("unsupported TDC amount basis")
        if row["support_formula"] != "delta_tdc_ex_overlap_bil * beta * chi":
            raise MarginalTDCSimContractError("unsupported TDC support formula")
        expected = (
            Decimal(row["delta_tdc_ex_overlap_bil"])
            * Decimal(row["beta"])
            * Decimal(row["chi"])
        )
        if Decimal(row["marginal_tdc_support_bil"]) != expected:
            raise MarginalTDCSimContractError("marginal TDC support identity failed")
        if row["selected_tdc_formula_pass"] == "true" and row["enters_selected_rw_m"] != "true":
            raise MarginalTDCSimContractError(
                "selected TDC support must have enters_selected_rw_m=true"
            )
        if "full_tdc_level" not in row["blocked_use"]:
            raise MarginalTDCSimContractError("full TDC blocker missing")
        _validate_forecast_source_grade_support(row)


def _matching_beta_schedule_row(
    summary_row: Mapping[str, str],
    beta_schedule_rows: Sequence[Mapping[str, str]] | None,
) -> dict[str, str] | None:
    if beta_schedule_rows is None:
        return None
    period_object = _period_object_from_summary(summary_row)
    state_kind = _state_kind_from_period_object(period_object)
    try:
        return lookup_beta_schedule_row(
            schedule_rows=beta_schedule_rows,
            period_object=period_object,
            period=summary_row["period"],
            state_id=summary_row["state_id"],
            state_kind=state_kind,
            horizon=summary_row["horizon"],
            shock_path_id=summary_row["shock_path_id"],
            demand_conversion_case=summary_row["demand_conversion_case"],
        )
    except ValueError as exc:
        raise MarginalTDCSimContractError(
            f"missing beta schedule row for marginal TDC pair: {exc}"
        ) from exc


def _validate_summary_beta_matches_schedule(
    summary_row: Mapping[str, str],
    schedule_row: Mapping[str, str],
) -> None:
    exact_checks = [
        ("beta", "beta_selected"),
        ("chi", "chi_selected"),
    ]
    for summary_key, schedule_key in exact_checks:
        if Decimal(str(summary_row[summary_key])) != Decimal(str(schedule_row[schedule_key])):
            raise MarginalTDCSimContractError(
                f"TDCSim {summary_key} does not match RateWall beta schedule"
            )
    if not _decimal_close(
        Decimal(str(summary_row["beta_times_chi"])),
        Decimal(str(schedule_row["beta_times_chi_selected"])),
    ):
        raise MarginalTDCSimContractError(
            "TDCSim beta_times_chi does not match RateWall beta schedule"
        )
    expected_support = (
        Decimal(str(summary_row["delta_tdc_ex_overlap_bil"]))
        * Decimal(str(schedule_row["beta_selected"]))
        * Decimal(str(schedule_row["chi_selected"]))
    )
    if not _decimal_close(
        expected_support,
        Decimal(str(summary_row["marginal_tdc_support_bil"])),
    ):
        raise MarginalTDCSimContractError(
            "TDCSim marginal support does not match RateWall beta schedule"
        )


def _period_object_from_summary(row: Mapping[str, str]) -> str:
    state_kind = row.get("state_kind", "")
    state_id = row.get("state_id", "")
    if state_kind == "current_state" or state_id.startswith("current_state::"):
        return "current"
    if state_kind == "historical_state" or state_id.startswith("historical_actual_state::"):
        return "historical"
    if state_kind == "forecast_state" or state_id.startswith("cbo_baseline_state::"):
        return "forecast"
    raise MarginalTDCSimContractError("cannot infer TDC period_object for beta schedule")


def _state_kind_from_period_object(period_object: str) -> str:
    if period_object == "current":
        return "current_state"
    if period_object == "historical":
        return "historical_state"
    if period_object == "forecast":
        return "forecast_state"
    raise MarginalTDCSimContractError("unsupported beta schedule period_object")


def validate_marginal_tdc_state_composition_audit_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalTDCSimContractError("state composition audit rows are empty")
    for row in rows:
        if set(row) != set(MARGINAL_TDC_STATE_COMPOSITION_AUDIT_FIELDS):
            raise MarginalTDCSimContractError("state composition audit schema mismatch")
        if row["claim_boundary"] != CLAIM_BOUNDARY:
            raise MarginalTDCSimContractError("state composition audit boundary failed")
        if row["selected_tdc_admission_status"].startswith("pass"):
            if row["state_manifest_status"] != "pass":
                raise MarginalTDCSimContractError("passing audit needs state manifest")
            if row["full_key_status"] != "pass_full_marginal_tdc_key_present":
                raise MarginalTDCSimContractError("passing audit needs full key")
            if not row["state_fingerprint_sha256"]:
                raise MarginalTDCSimContractError("passing audit needs state fingerprint")
        else:
            if "selected_tdc_support" not in row["blocked_use"]:
                raise MarginalTDCSimContractError("audit selected TDC blocker missing")


def _validate_forecast_source_grade_support(row: Mapping[str, str]) -> None:
    state_id = row.get("state_id", "")
    if not state_id.startswith("cbo_baseline_state::"):
        return
    try:
        year = int(state_id.split("::", 1)[1])
    except (IndexError, ValueError):
        return
    if year < 2027 or year > 2036:
        return
    if row.get("source_grade_status") != "pass_forecast_rollforward_source_grade":
        raise MarginalTDCSimContractError("forecast TDC support requires source-grade rollforward status")
    if row.get("state_construction_method") != "baseline_rollforward_export_v1":
        raise MarginalTDCSimContractError("forecast TDC support requires rollforward state construction")
    if row.get("source_vintage") == "ratewall_assumption_mode_fixture_20260630":
        raise MarginalTDCSimContractError("forecast TDC support cannot use assumption fixture vintage")
    for field in (
        "derived_state_package_sha256",
        "rollforward_run_manifest_sha256",
        "compiled_non_rate_inputs_digest",
    ):
        value = row.get(field, "")
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
            raise MarginalTDCSimContractError(f"forecast TDC support requires {field}")
    if not row.get("pair_id", "").endswith("_source_grade_pair_v1"):
        raise MarginalTDCSimContractError("forecast source-grade pair id suffix failed")


def _validate_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise MarginalTDCSimContractError("unsupported manifest schema version")
    if manifest.get("claim_boundary") != CLAIM_BOUNDARY:
        raise MarginalTDCSimContractError("manifest claim boundary failed")
    if manifest.get("validation", {}).get("status") != "pass":
        raise MarginalTDCSimContractError("manifest validation status is not pass")
    spec = manifest.get("pair_spec", {})
    if not isinstance(spec, Mapping):
        raise MarginalTDCSimContractError("manifest pair_spec missing")
    required = {
        "schema_version": PAIR_SCHEMA_VERSION,
        "object_id": OBJECT_ID,
        "shock_path_id": SHOCK_PATH_ID,
        "denominator_equivalence_key": "ratewall_D_conv_plus_100bp_year_v1",
    }
    for key, expected in required.items():
        if spec.get(key) != expected:
            raise MarginalTDCSimContractError(f"pair spec {key} failed")
    for key in [
        "require_same_baseline_hashes",
        "require_same_opening_state",
        "require_same_actuals_available_as_of",
        "require_same_simulation_dates",
        "require_same_period_index",
        "require_same_non_rate_compiled_inputs",
        "one_named_rate_shock_only",
    ]:
        if spec.get(key) is not True:
            raise MarginalTDCSimContractError(f"pair spec {key} must be true")
    if Decimal(str(spec.get("shock_bps_year"))) != Decimal("100"):
        raise MarginalTDCSimContractError("pair spec shock_bps_year failed")


def _validate_summary(rows: Sequence[Mapping[str, str]]) -> None:
    if not rows:
        raise MarginalTDCSimContractError("marginal TDC summary is empty")
    missing = sorted(REQUIRED_SUMMARY_FIELDS - set(rows[0]))
    if missing:
        raise MarginalTDCSimContractError(f"missing summary fields: {missing}")
    for row in rows:
        if row["object_id"] != OBJECT_ID:
            raise MarginalTDCSimContractError("summary object_id failed")
        if row["shock_path_id"] != SHOCK_PATH_ID:
            raise MarginalTDCSimContractError("summary shock_path_id failed")
        if row["claim_boundary"] != CLAIM_BOUNDARY:
            raise MarginalTDCSimContractError("summary claim boundary failed")
        for status_field in [
            "same_state_status",
            "rate_shock_only_status",
            "shock_path_validation_status",
            "period_alignment_status",
            "overlap_identity_status",
            "component_identity_status",
            "route_identity_status",
            "support_identity_status",
            "state_manifest_status",
        ]:
            if str(row[status_field]).lower() != "pass":
                raise MarginalTDCSimContractError(f"{status_field} failed")
        if row["schema_version"] != PAIR_SCHEMA_VERSION:
            raise MarginalTDCSimContractError("summary schema_version failed")
        if row["contract_version"] != CONTRACT_VERSION:
            raise MarginalTDCSimContractError("summary contract_version failed")
        if row["shock_bps_year"] != "100":
            raise MarginalTDCSimContractError("summary shock_bps_year failed")
        if not row["horizon"]:
            raise MarginalTDCSimContractError("summary horizon is required")
        if not row["state_fingerprint_sha256"]:
            raise MarginalTDCSimContractError("summary state fingerprint is required")
        if row["tdc_amount_basis"] != "pre_beta_ex_overlap_delta":
            raise MarginalTDCSimContractError("summary TDC amount basis failed")
        if row["support_formula"] != "delta_tdc_ex_overlap_bil * beta * chi":
            raise MarginalTDCSimContractError("summary support formula failed")
        if not str(row["contract_ingest_status"]).startswith("ready_for_ratewall"):
            raise MarginalTDCSimContractError("summary contract ingest status failed")
        delta_tdc = Decimal(row["delta_tdc_change_bil"])
        delta_overlap = Decimal(row["delta_overlap_bil"])
        delta_ex = Decimal(row["delta_tdc_ex_overlap_bil"])
        if not _decimal_close(delta_tdc - delta_overlap, delta_ex):
            raise MarginalTDCSimContractError("delta TDC ex-overlap identity failed")
        beta = Decimal(row["beta"])
        chi = Decimal(row["chi"])
        if not _decimal_close(beta * chi, Decimal(row["beta_times_chi"])):
            raise MarginalTDCSimContractError("beta chi identity failed")
        if not _decimal_close(
            delta_ex * beta * chi, Decimal(row["marginal_tdc_support_bil"])
        ):
            raise MarginalTDCSimContractError("support identity failed")


def _fail_closed_ingest_row(pair_dir: Path, reason: str) -> dict[str, str]:
    return {
        "marginal_tdcsim_contract_ingest_row_id": "marginal_tdcsim_contract_ingest::fail_closed",
        "pair_dir": str(pair_dir),
        "manifest_path": str(pair_dir / MANIFEST_FILE),
        "summary_path": str(pair_dir / SUMMARY_FILE),
        "manifest_schema_version": "",
        "pair_schema_version": "",
        "contract_family": CONTRACT_FAMILY,
        "contract_version": CONTRACT_VERSION,
        "object_id": OBJECT_ID,
        "shock_path_id": SHOCK_PATH_ID,
        "summary_row_count": "0",
        "contract_ingest_status": "fail_closed_missing_or_invalid_tdcsim_v0p4_marginal_pair",
        "failure_reason": reason,
        "allowed_use": "fail_closed_tdcsim_ingest_diagnostic",
        "blocked_use": "selected_tdc_support;tdcsim_v0p3_output;full_tdc_level;observed_tdc_level",
        "claim_boundary": "no_selected_tdc_until_tdcsim_v0p4_marginal_pair_passes",
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise MarginalTDCSimContractError("manifest must be a JSON object")
    return payload


def _read_summary(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _decimal_close(left: Decimal, right: Decimal) -> bool:
    return abs(left - right) <= SUMMARY_DECIMAL_TOLERANCE
