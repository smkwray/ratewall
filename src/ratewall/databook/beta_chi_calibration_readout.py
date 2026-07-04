"""Consolidated beta-chi calibration readout for forecast scenarios."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.table_io import write_rows
from ratewall.databook.tdcsim_cbo_contracts import (
    DEFAULT_TDC_BETA,
    DEFAULT_TDC_DEPOSIT_CURRENT_DEMAND_SHARE,
)

DEFAULT_BETA_CHI_CLAIM_GATE_DIR = Path(
    "var/preliminary_scenario_results/beta_chi_claim_gate"
)
DEFAULT_DIRECT_CHI_EVIDENCE_DIR = Path(
    "var/preliminary_scenario_results/direct_chi_evidence"
)

BETA_CHI_CALIBRATION_SUMMARY_FIELDS = [
    "beta_chi_calibration_summary_row_id",
    "current_beta",
    "current_chi",
    "current_beta_times_chi",
    "existing_grid_min_beta",
    "existing_grid_min_chi",
    "existing_grid_min_beta_times_chi",
    "claim_gate_rows",
    "sign_robust_rows",
    "point_calibrated_rows",
    "mixed_sign_rows",
    "threshold_rows",
    "direct_requirement_rows",
    "direct_adjudication_rows",
    "direct_admitted_floor_rows",
    "estimator_contract_rows",
    "estimator_ready_rows",
    "panel_candidate_rows",
    "panel_matched_rows",
    "panel_identified_rows",
    "panel_admitted_lower_bound_rows",
    "local_source_context_rows",
    "local_source_rows_scanned",
    "local_admitted_floor_rows",
    "external_admitted_floor_rows",
    "chi_mapping_admitted_floor_rows",
    "selected_model_use",
    "direct_evidence_status",
    "calibration_decision",
    "next_model_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_CALIBRATION_DECISION_FIELDS = [
    "beta_chi_calibration_decision_row_id",
    "decision_area",
    "current_status",
    "evidence_basis",
    "model_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class BetaChiCalibrationReadoutError(ValueError):
    """Raised when calibration readout inputs are missing or inconsistent."""


def beta_chi_calibration_summary_rows(
    *,
    claim_gate_dir: str | Path = DEFAULT_BETA_CHI_CLAIM_GATE_DIR,
    direct_chi_dir: str | Path = DEFAULT_DIRECT_CHI_EVIDENCE_DIR,
) -> list[dict[str, str]]:
    """Summarize the current beta-chi calibration evidence state."""

    inputs = _read_inputs(Path(claim_gate_dir), Path(direct_chi_dir))
    claim_rows = inputs["claim_gate"]
    if not claim_rows:
        raise BetaChiCalibrationReadoutError("missing beta-chi claim-gate rows")
    first = claim_rows[0]
    current_beta = _field_or_default(first, "current_beta", DEFAULT_TDC_BETA)
    current_chi = _field_or_default(
        first,
        "current_chi",
        DEFAULT_TDC_DEPOSIT_CURRENT_DEMAND_SHARE,
    )
    grid_min_beta = _field_or_default(first, "existing_grid_min_beta", Decimal("0"))
    grid_min_chi = _field_or_default(first, "existing_grid_min_chi", Decimal("0"))
    direct_admitted = _count(
        inputs["direct_adjudication"],
        "admission_result",
        "admit_floor_from_direct_evidence",
    )
    estimator_ready = _count(
        inputs["estimator_contract"],
        "current_contract_status",
        "ready_for_direct_estimator_input",
    )
    local_admitted = sum(
        _int(row.get("admitted_beta_floor_rows", "0"))
        + _int(row.get("admitted_chi_floor_rows", "0"))
        + _int(row.get("admitted_beta_chi_floor_rows", "0"))
        for row in inputs["source_context"]
    )
    external_admitted = sum(
        _int(row.get("external_admitted_beta_floor_rows", "0"))
        + _int(row.get("external_admitted_chi_floor_rows", "0"))
        for row in inputs["external_floor_review"]
    )
    chi_mapping_admitted = _count_admitted_status(
        inputs["chi_mapping_sensitivity"],
        "admission_status",
    )
    panel_status = inputs["panel_status"][0] if inputs["panel_status"] else {}
    direct_status = _direct_status(
        direct_admitted=direct_admitted,
        estimator_ready=estimator_ready,
        panel_status=panel_status,
    )
    calibration_decision = (
        "assumption_mode_keep_exact_ea_tdc_beta_and_existing_chi"
        if direct_admitted == 0
        and estimator_ready == 0
        and local_admitted == 0
        and external_admitted == 0
        and chi_mapping_admitted == 0
        else "new_floor_or_ready_estimator_requires_owner_review"
    )
    return [
        {
            "beta_chi_calibration_summary_row_id": "beta_chi_calibration::current",
            "current_beta": _fmt(current_beta),
            "current_chi": _fmt(current_chi),
            "current_beta_times_chi": _fmt(current_beta * current_chi),
            "existing_grid_min_beta": _fmt(grid_min_beta),
            "existing_grid_min_chi": _fmt(grid_min_chi),
            "existing_grid_min_beta_times_chi": _fmt(grid_min_beta * grid_min_chi),
            "claim_gate_rows": str(len(claim_rows)),
            "sign_robust_rows": str(
                _count(
                    claim_rows,
                    "claim_strength_status",
                    "sign_robust_over_existing_beta_chi_grid",
                )
            ),
            "point_calibrated_rows": str(
                _count(
                    claim_rows,
                    "claim_strength_status",
                    "point_calibrated_assumption_only",
                )
            ),
            "mixed_sign_rows": str(
                _count(
                    claim_rows,
                    "moving_d_beta_chi_sign_stability_status",
                    "mixed_sign",
                )
            ),
            "threshold_rows": str(len(inputs["thresholds"])),
            "direct_requirement_rows": str(len(inputs["requirements"])),
            "direct_adjudication_rows": str(len(inputs["direct_adjudication"])),
            "direct_admitted_floor_rows": str(direct_admitted),
            "estimator_contract_rows": str(len(inputs["estimator_contract"])),
            "estimator_ready_rows": str(estimator_ready),
            "panel_candidate_rows": panel_status.get("candidate_panel_rows", "0"),
            "panel_matched_rows": panel_status.get("matched_panel_rows", "0"),
            "panel_identified_rows": panel_status.get("identified_panel_rows", "0"),
            "panel_admitted_lower_bound_rows": panel_status.get(
                "admitted_lower_bound_rows",
                "0",
            ),
            "local_source_context_rows": str(len(inputs["source_context"])),
            "local_source_rows_scanned": str(
                sum(_int(row.get("source_row_count", "0")) for row in inputs["source_context"])
            ),
            "local_admitted_floor_rows": str(local_admitted),
            "external_admitted_floor_rows": str(external_admitted),
            "chi_mapping_admitted_floor_rows": str(chi_mapping_admitted),
            "selected_model_use": (
                "central_forecast_uses_current_beta_times_chi;"
                "sensitivity_surfaces_keep_existing_grid"
            ),
            "direct_evidence_status": direct_status,
            "calibration_decision": calibration_decision,
            "next_model_action": (
                "do_not_reopen_local_ols;carry_assumption_mode_transparently;"
                "only_reopen_with_identified_materialized_tdc_current_demand_panel"
            ),
            "allowed_use": "forecast_calibration_status_and_model_readout",
            "blocked_use": (
                "canonical_headline_promotion;evidence_mode_claim;"
                "posterior_beta_or_chi_claim;new_beta_chi_floor_admission"
            ),
            "claim_boundary": (
                "readout_only;does_not_change_beta_chi_grid_numerator_or_denominator"
            ),
        }
    ]


def beta_chi_calibration_decision_rows(
    summary_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Build explicit model decisions implied by the calibration summary."""

    if len(summary_rows) != 1:
        raise BetaChiCalibrationReadoutError("expected one calibration summary row")
    summary = summary_rows[0]
    return [
        _decision(
            "default_beta",
            "admitted_assumption_from_ea_tdc_normal_forward_profile",
            f"exact_beta={summary['current_beta']}",
            "use_as_central_forecast_beta_until_owner_changes_beta_profile",
        ),
        _decision(
            "chi",
            "assumption_mode_current_demand_share",
            f"chi={summary['current_chi']}",
            "use_as_current_forecast_chi_assumption_not_empirical_posterior",
        ),
        _decision(
            "direct_beta_chi_floor",
            summary["direct_evidence_status"],
            (
                f"direct_admitted={summary['direct_admitted_floor_rows']};"
                f"estimator_ready={summary['estimator_ready_rows']};"
                f"matched_panel={summary['panel_matched_rows']};"
                f"identified_panel={summary['panel_identified_rows']}"
            ),
            "no_floor_admitted_keep_mixed_rows_point_calibrated",
        ),
        _decision(
            "external_mpc_bridge",
            "screen_only_no_ratewall_specific_bridge",
            (
                f"external_admitted_floor_rows="
                f"{summary['external_admitted_floor_rows']};"
                f"chi_mapping_admitted_floor_rows="
                f"{summary['chi_mapping_admitted_floor_rows']}"
            ),
            "do_not_convert_cash_like_mpc_screens_into_chi_floors",
        ),
        _decision(
            "source_context",
            "context_available_no_floor_admitted",
            (
                f"source_context_rows={summary['local_source_context_rows']};"
                f"rows_scanned={summary['local_source_rows_scanned']};"
                f"local_admitted_floor_rows="
                f"{summary['local_admitted_floor_rows']}"
            ),
            "use_for_audit_context_not_for_prior_narrowing",
        ),
    ]


def beta_chi_calibration_readout_markdown(
    *,
    summary_rows: Sequence[Mapping[str, str]],
    decision_rows: Sequence[Mapping[str, str]],
) -> str:
    """Return a plain-language calibration readout."""

    if len(summary_rows) != 1:
        raise BetaChiCalibrationReadoutError("expected one calibration summary row")
    summary = summary_rows[0]
    lines = [
        "# Beta-Chi Calibration Readout",
        "",
        "## Bottom Line",
        "",
        (
            "The forecast should keep the exact EA-TDC beta and the existing chi "
            "assumption. The current evidence does not admit a new direct beta-chi "
            "floor, does not narrow the beta/chi grid, and does not promote an "
            "evidence-mode claim."
        ),
        "",
        "## Current Scale",
        "",
        f"- Beta: `{summary['current_beta']}`.",
        f"- Chi: `{summary['current_chi']}`.",
        f"- Beta times chi: `{summary['current_beta_times_chi']}`.",
        f"- Existing low-grid beta times chi: `{summary['existing_grid_min_beta_times_chi']}`.",
        "",
        "## Evidence Status",
        "",
        f"- Claim-gate rows: `{summary['claim_gate_rows']}`.",
        f"- Sign-robust rows: `{summary['sign_robust_rows']}`.",
        f"- Point-calibrated rows: `{summary['point_calibrated_rows']}`.",
        f"- Mixed-sign rows: `{summary['mixed_sign_rows']}`.",
        f"- Direct admitted floor rows: `{summary['direct_admitted_floor_rows']}`.",
        f"- Estimator-ready rows: `{summary['estimator_ready_rows']}`.",
        f"- Candidate panel rows: `{summary['panel_candidate_rows']}`.",
        f"- Matched panel rows: `{summary['panel_matched_rows']}`.",
        f"- Identified panel rows: `{summary['panel_identified_rows']}`.",
        f"- Local source rows scanned: `{summary['local_source_rows_scanned']}`.",
        "",
        "## Decision",
        "",
        f"- Calibration decision: `{summary['calibration_decision']}`.",
        f"- Direct-evidence status: `{summary['direct_evidence_status']}`.",
        f"- Next model action: `{summary['next_model_action']}`.",
        "",
        "## Decision Rows",
        "",
    ]
    for row in decision_rows:
        lines.append(
            "- "
            f"`{row['decision_area']}`: `{row['current_status']}`; "
            f"{row['model_action']}."
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This readout changes no forecast numerator or denominator value.",
            "- It is a calibration-status artifact for the model roadmap.",
            "- It keeps direct beta-chi evidence closed unless a matched and identified panel appears.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_beta_chi_calibration_readout_outputs(
    output_dir: str | Path,
    *,
    summary_rows: Sequence[Mapping[str, str]],
    decision_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write calibration summary, decisions, and readout markdown."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary_csv": out / "ratewall_beta_chi_calibration_summary.csv",
        "decision_csv": out / "ratewall_beta_chi_calibration_decisions.csv",
        "readout_md": out / "beta_chi_calibration_readout.md",
    }
    write_rows(
        paths["summary_csv"],
        [dict(row) for row in summary_rows],
        BETA_CHI_CALIBRATION_SUMMARY_FIELDS,
    )
    write_rows(
        paths["decision_csv"],
        [dict(row) for row in decision_rows],
        BETA_CHI_CALIBRATION_DECISION_FIELDS,
    )
    paths["readout_md"].write_text(
        beta_chi_calibration_readout_markdown(
            summary_rows=summary_rows,
            decision_rows=decision_rows,
        ),
        encoding="utf-8",
    )
    return paths


def _read_inputs(claim_gate_dir: Path, direct_chi_dir: Path) -> dict[str, list[dict[str, str]]]:
    return {
        "claim_gate": _read_required(
            claim_gate_dir / "ratewall_beta_chi_claim_gate.csv",
        ),
        "thresholds": _read_required(
            claim_gate_dir / "ratewall_beta_chi_robustness_thresholds.csv",
        ),
        "source_context": _read_required(
            claim_gate_dir / "ratewall_beta_chi_source_context.csv",
        ),
        "external_floor_review": _read_required(
            claim_gate_dir / "ratewall_beta_chi_external_floor_review.csv",
        ),
        "chi_mapping_sensitivity": _read_required(
            claim_gate_dir / "ratewall_beta_chi_chi_mapping_sensitivity.csv",
        ),
        "requirements": _read_required(
            direct_chi_dir / "ratewall_direct_chi_requirements.csv",
        ),
        "direct_adjudication": _read_required(
            direct_chi_dir / "ratewall_direct_chi_adjudication.csv",
        ),
        "estimator_contract": _read_required(
            direct_chi_dir / "ratewall_direct_beta_chi_estimator_contract.csv",
        ),
        "panel_status": _read_required(
            direct_chi_dir / "ratewall_direct_beta_chi_candidate_panel_status.csv",
        ),
    }


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise BetaChiCalibrationReadoutError(f"missing required input: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _decision(
    area: str,
    status: str,
    basis: str,
    action: str,
) -> dict[str, str]:
    return {
        "beta_chi_calibration_decision_row_id": f"beta_chi_calibration::{area}",
        "decision_area": area,
        "current_status": status,
        "evidence_basis": basis,
        "model_action": action,
        "allowed_use": "model_calibration_decision_readout",
        "blocked_use": (
            "canonical_headline_promotion;evidence_mode_claim;"
            "posterior_beta_or_chi_claim;new_beta_chi_floor_admission"
        ),
        "claim_boundary": "decision_readout_only_not_math_change",
    }


def _field_or_default(row: Mapping[str, str], field: str, default: Decimal) -> Decimal:
    value = row.get(field, "")
    if not value:
        return default
    return _decimal(value)


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise BetaChiCalibrationReadoutError(f"invalid decimal: {value!r}") from exc


def _int(value: str) -> int:
    if value == "":
        return 0
    return int(value)


def _count(rows: Sequence[Mapping[str, str]], field: str, value: str) -> int:
    return sum(row.get(field) == value for row in rows)


def _count_admitted_status(rows: Sequence[Mapping[str, str]], field: str) -> int:
    return sum(row.get(field, "").startswith("admitted") for row in rows)


def _direct_status(
    *,
    direct_admitted: int,
    estimator_ready: int,
    panel_status: Mapping[str, str],
) -> str:
    if direct_admitted:
        return "direct_floor_admitted_requires_owner_review"
    if estimator_ready:
        return "estimator_ready_no_floor_admitted"
    if panel_status:
        blocker = panel_status.get("estimator_blocker", "")
        if blocker:
            return f"blocked_{blocker}"
    return "blocked_no_direct_floor_or_ready_estimator"


def _fmt(value: Decimal) -> str:
    return format(value, "f")
