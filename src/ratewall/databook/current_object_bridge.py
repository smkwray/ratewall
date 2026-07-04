"""Current-object bridge and freeze surface for RateWall D2/D10."""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_CURRENT_OVERLAY_DIR = Path(
    "var/preliminary_scenario_results/current_observed_overlay"
)
DEFAULT_SAFE_YIELD_DIR = Path(
    "var/preliminary_scenario_results/realized_safe_yield_income"
)
DEFAULT_RUNTIME_TABLE_DIR = Path("outputs/tables")

SELECTED_CURRENT_ID = "current_assumption_benchmark::2026"
SELECTED_CURRENT_N = "83.542224868775"
SELECTED_CURRENT_D = "247.55956656"
SELECTED_CURRENT_RW = "0.337463124652"
PUBLIC_INTEREST_COMPONENT = "56.03251655775289810515522913"
LEGACY_RUNTIME_TDC_COMPONENT = "27.50970831102218887944538608"
R38_TDC_CANDIDATE = "19.25679581771553221561177026"
R38_COMPOSITE_N = "75.28931237546843032076699939"
R38_COMPOSITE_RW = "0.3041260470021903496128297608"
LEGACY_STATIC_RW = "0.04157132893140423351153088093"

CURRENT_OBJECT_BRIDGE_FIELDS = [
    "current_object_bridge_row_id",
    "current_object_id",
    "row_kind",
    "period_object",
    "source_surface",
    "selected_current_row",
    "selected_current_component",
    "current_object_role",
    "n_bil",
    "d_bil",
    "rw",
    "public_interest_component_bil",
    "legacy_runtime_tdc_component_bil",
    "r38_public_interest_candidate_bil",
    "r38_beta_chi_tdc_candidate_bil",
    "safe_yield_scenario",
    "safe_yield_support_bil",
    "central_n_delta_bil_allowed",
    "central_n_delta_bil",
    "tdc_formula_basis",
    "replacement_gate_status",
    "runtime_replay_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

CURRENT_OBJECT_FREEZE_DECISION_FIELDS = [
    "freeze_decision_row_id",
    "selected_current_object_id",
    "selected_n_bil",
    "selected_d_bil",
    "selected_rw",
    "selection_status",
    "legacy_static_status",
    "r38_status",
    "d1_status",
    "replacement_gate_status",
    "no_hybrid_rule",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

CURRENT_OBJECT_INPUT_MANIFEST_FIELDS = [
    "input_manifest_row_id",
    "input_path",
    "required_for",
    "exists",
    "row_count",
    "sha256",
    "runtime_replay_status",
    "provenance_note",
]


class CurrentObjectBridgeError(ValueError):
    """Raised when current-object bridge rows violate the freeze contract."""


def current_object_bridge_rows(
    *,
    current_overlay_dir: str | Path = DEFAULT_CURRENT_OVERLAY_DIR,
    safe_yield_dir: str | Path = DEFAULT_SAFE_YIELD_DIR,
    runtime_table_dir: str | Path = DEFAULT_RUNTIME_TABLE_DIR,
) -> list[dict[str, str]]:
    """Return current bridge rows separating selected, candidate, and sensitivity rows."""

    overlay_dir = Path(current_overlay_dir)
    benchmark = _selected_benchmark(
        _read_required(overlay_dir / "ratewall_current_assumption_benchmark.csv")
    )
    admission = _single_row(
        _read_required(overlay_dir / "ratewall_current_observed_overlay_admission.csv"),
        "current observed-overlay admission",
    )
    safe_yield_rows = _read_required(
        Path(safe_yield_dir) / "ratewall_realized_safe_yield_bounded_sensitivity.csv"
    )
    replay_status = _combined_runtime_status(
        current_object_input_manifest_rows(runtime_table_dir=runtime_table_dir)
    )
    rows = [
        _bridge_row(
            "legacy_static_lane",
            "rw_legacy_static_assumption_mode",
            "full_current_object",
            "legacy_static_reference",
            "false",
            "false",
            "sensitivity_only",
            "",
            "",
            LEGACY_STATIC_RW,
            "",
            "",
            "",
            "",
            "",
            "",
            "false",
            "0",
            "not_applicable",
            "blocked_reference_only",
            replay_status,
            "legacy_static_reference_sensitivity",
            "selected_current_row;runtime_benchmark_replacement",
            "legacy_static_not_selected_current",
        ),
        _bridge_row(
            "selected_runtime_benchmark",
            SELECTED_CURRENT_ID,
            "full_current_object",
            "current_assumption_runtime",
            "true",
            "false",
            "selected_benchmark_recast",
            benchmark["benchmark_numerator_bil"],
            benchmark["fixed_D_bil"],
            benchmark["benchmark_ratewall_ratio"],
            PUBLIC_INTEREST_COMPONENT,
            LEGACY_RUNTIME_TDC_COMPONENT,
            "",
            "",
            "",
            "",
            "false",
            "0",
            "legacy_runtime_recast_not_source_led_tdc_promotion",
            "selected_current_object_frozen",
            replay_status,
            "selected_current_benchmark_recast",
            "r38_or_d1_hybrid_replacement;legacy_static_selection",
            "current_selected_values_frozen",
        ),
        _bridge_row(
            "selected_public_interest_component",
            "current_runtime_public_interest_component",
            "selected_component",
            "current_assumption_runtime",
            "false",
            "true",
            "selected_block_input",
            PUBLIC_INTEREST_COMPONENT,
            "",
            "",
            PUBLIC_INTEREST_COMPONENT,
            "",
            "",
            "",
            "",
            "",
            "false",
            "0",
            "inside_frozen_current_benchmark",
            "component_not_selected_current_row",
            replay_status,
            "selected_current_component_recast",
            "standalone_selected_current_row",
            "public_interest_component_nonstandalone",
        ),
        _bridge_row(
            "selected_legacy_runtime_tdc_component",
            "current_runtime_legacy_tdc_component",
            "selected_component",
            "current_assumption_runtime",
            "false",
            "true",
            "selected_block_input",
            LEGACY_RUNTIME_TDC_COMPONENT,
            "",
            "",
            "",
            LEGACY_RUNTIME_TDC_COMPONENT,
            "",
            "",
            "",
            "",
            "false",
            "0",
            "legacy_runtime_tdc_inside_frozen_benchmark",
            "component_not_selected_current_row",
            replay_status,
            "selected_current_component_recast",
            "observed_source_led_tdc_promotion;standalone_selected_current_row",
            "legacy_runtime_tdc_component_nonstandalone",
        ),
        _bridge_row(
            "r38_public_interest_candidate",
            "r38_public_interest_candidate",
            "candidate_component",
            "current_observed_overlay",
            "false",
            "false",
            "candidate_replacement",
            admission["public_interest_support_bil"],
            "",
            "",
            "",
            "",
            admission["public_interest_support_bil"],
            "",
            "",
            "",
            "false",
            "0",
            "source_led_public_interest_candidate",
            "blocked_replacement_surface_not_admitted",
            replay_status,
            "current_candidate_replacement_review",
            "selected_current_row;silent_benchmark_replacement",
            "r38_public_interest_nonselected",
        ),
        _bridge_row(
            "r38_beta_chi_tdc_candidate",
            "r38_beta_chi_tdc_candidate",
            "candidate_component",
            "current_observed_overlay",
            "false",
            "false",
            "candidate_replacement",
            admission["selected_beta_chi_tdc_support_bil"],
            "",
            "",
            "",
            "",
            "",
            admission["selected_beta_chi_tdc_support_bil"],
            "",
            "",
            "false",
            "0",
            "tdc_change_ex_overlap_bil * beta * chi",
            admission["replacement_gate_status"],
            replay_status,
            "current_candidate_replacement_review",
            "selected_current_row;tdc_full_bil;silent_benchmark_replacement",
            "r38_tdc_ex_overlap_beta_chi_nonselected",
        ),
        _bridge_row(
            "r38_composite_candidate",
            "r38_composite_candidate",
            "full_current_object",
            "current_observed_overlay",
            "false",
            "false",
            "candidate_replacement",
            admission["selected_overlay_candidate_n_bil"],
            admission["benchmark_D_bil"],
            admission["selected_overlay_candidate_ratewall_ratio"],
            "",
            "",
            admission["public_interest_support_bil"],
            admission["selected_beta_chi_tdc_support_bil"],
            "",
            "",
            "false",
            "0",
            "public_interest_candidate + tdc_change_ex_overlap_bil * beta * chi",
            admission["replacement_gate_status"],
            replay_status,
            "current_candidate_replacement_review",
            "selected_current_row;benchmark_r38_d1_hybrid",
            "r38_composite_nonselected",
        ),
    ]
    for row in safe_yield_rows:
        scenario = row["scenario"]
        rows.append(
            _bridge_row(
                f"d1_safe_yield_bounded_{scenario}",
                f"d1_safe_yield_bounded_{scenario}",
                "bounded_sensitivity",
                "realized_safe_yield_income",
                "false",
                "false",
                "sensitivity_only",
                row["safe_yield_support_bil"],
                row["current_D_bil"],
                row["support_to_current_D_ratio"],
                "",
                "",
                "",
                "",
                scenario,
                row["safe_yield_support_bil"],
                row["central_n_delta_bil_allowed"],
                row["central_n_delta_bil"],
                "safe_yield_bounded_sensitivity_only",
                "blocked_all_gates_not_passed",
                replay_status,
                "D1_bounded_sensitivity_review",
                "selected_current_row;central_current_addition",
                "D1_safe_yield_noncentral_until_all_gates_pass",
            )
        )
    validate_current_object_bridge(rows)
    return rows


def current_object_freeze_decision_rows(
    bridge_rows: Sequence[Mapping[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Return the freeze decision row for the selected current benchmark."""

    rows = list(bridge_rows) if bridge_rows is not None else current_object_bridge_rows()
    validate_current_object_bridge(rows)
    selected = _single_selected_bridge(rows)
    decisions = [
        {
            "freeze_decision_row_id": "current_object_freeze::2026",
            "selected_current_object_id": selected["current_object_id"],
            "selected_n_bil": selected["n_bil"],
            "selected_d_bil": selected["d_bil"],
            "selected_rw": selected["rw"],
            "selection_status": "freeze_selected_runtime_benchmark",
            "legacy_static_status": "sensitivity_only_not_selected",
            "r38_status": "candidate_replacement_blocked_until_named_surface_passes",
            "d1_status": "sensitivity_only_noncentral_central_delta_zero",
            "replacement_gate_status": "closed_no_named_replacement_surface",
            "no_hybrid_rule": "no_benchmark_r38_d1_hybrid_row_allowed",
            "allowed_use": "current_object_freeze_decision",
            "blocked_use": "silent_current_value_change;evidence_mode_claim",
            "claim_boundary": "current_object_bridge_preserves_selected_values",
        }
    ]
    validate_current_object_freeze_decision(decisions, bridge_rows=rows)
    return decisions


def current_object_input_manifest_rows(
    *,
    runtime_table_dir: str | Path = DEFAULT_RUNTIME_TABLE_DIR,
) -> list[dict[str, str]]:
    """Return manifest rows for runtime inputs required by the selected benchmark."""

    root = Path(runtime_table_dir)
    specs = [
        (
            "runtime_benchmark_overlay",
            root / "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv",
            "selected_current_benchmark_overlay",
        ),
        (
            "runtime_frontier_summary",
            root / "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv",
            "selected_current_frontier_source_row",
        ),
        (
            "runtime_support_offset_scenarios",
            root / "ratewall_runtime_annual_flow_support_offset_scenarios.csv",
            "selected_current_runtime_scenario_source_row",
        ),
    ]
    rows = []
    for row_id, path, required_for in specs:
        exists = path.exists()
        rows.append(
            {
                "input_manifest_row_id": f"current_object_input::{row_id}",
                "input_path": str(path),
                "required_for": required_for,
                "exists": str(exists).lower(),
                "row_count": str(_row_count(path)) if exists else "0",
                "sha256": _sha256(path) if exists else "",
                "runtime_replay_status": (
                    "runtime_replay_input_present"
                    if exists
                    else "generated_output_backed_not_runtime_replay_backed"
                ),
                "provenance_note": (
                    "local runtime input present for current benchmark replay"
                    if exists
                    else "missing runtime input; do not claim full replay"
                ),
            }
        )
    return rows


def current_object_bridge_readout_markdown(
    *,
    bridge_rows: Sequence[Mapping[str, str]],
    freeze_decision_rows: Sequence[Mapping[str, str]],
    input_manifest_rows: Sequence[Mapping[str, str]],
) -> str:
    """Return a compact current-object bridge readout."""

    validate_current_object_bridge(bridge_rows)
    validate_current_object_freeze_decision(
        freeze_decision_rows, bridge_rows=bridge_rows
    )
    selected = _single_selected_bridge(bridge_rows)
    manifest_status = _combined_runtime_status(input_manifest_rows)
    return "\n".join(
        [
            "# Current Object Bridge",
            "",
            "This bridge freezes the selected current object and separates it from legacy, R38, and D1 rows.",
            "",
            "## Selected Current Object",
            "",
            f"- object: `{selected['current_object_id']}`",
            f"- N: `{selected['n_bil']}`",
            f"- D: `{selected['d_bil']}`",
            f"- RW: `{selected['rw']}`",
            f"- runtime replay status: `{manifest_status}`",
            "",
            "## Nonselected Rows",
            "",
            "- legacy static lane remains reference/sensitivity only.",
            "- R38 public-interest and beta-chi TDC rows are candidate replacements, not the selected benchmark.",
            "- D1 safe-yield low/base/high rows are bounded sensitivities with central delta zero.",
            "- no benchmark/R38/D1 hybrid row is admitted.",
            "",
            "This bridge does not change selected N, D, RW, beta, chi, or c_D.",
            "",
        ]
    )


def write_current_object_bridge_outputs(
    output_dir: str | Path,
    *,
    bridge_rows: Sequence[Mapping[str, str]],
    freeze_decision_rows: Sequence[Mapping[str, str]],
    input_manifest_rows: Sequence[Mapping[str, str]],
    readout_markdown: str,
) -> dict[str, Path]:
    """Write current-object bridge outputs."""

    validate_current_object_bridge(bridge_rows)
    validate_current_object_freeze_decision(
        freeze_decision_rows, bridge_rows=bridge_rows
    )
    root = Path(output_dir)
    outputs = {
        "bridge_csv": root / "ratewall_current_object_bridge.csv",
        "freeze_decision_csv": root / "ratewall_current_object_freeze_decision.csv",
        "input_manifest_csv": root / "ratewall_current_object_input_manifest.csv",
        "readout_md": root / "current_object_bridge_readout.md",
    }
    write_rows(outputs["bridge_csv"], list(bridge_rows), CURRENT_OBJECT_BRIDGE_FIELDS)
    write_rows(
        outputs["freeze_decision_csv"],
        list(freeze_decision_rows),
        CURRENT_OBJECT_FREEZE_DECISION_FIELDS,
    )
    write_rows(
        outputs["input_manifest_csv"],
        list(input_manifest_rows),
        CURRENT_OBJECT_INPUT_MANIFEST_FIELDS,
    )
    outputs["readout_md"].parent.mkdir(parents=True, exist_ok=True)
    outputs["readout_md"].write_text(readout_markdown, encoding="utf-8")
    return outputs


def validate_current_object_bridge(rows: Sequence[Mapping[str, str]]) -> None:
    """Validate current-object bridge invariants."""

    if not rows:
        raise CurrentObjectBridgeError("current-object bridge is empty")
    by_id = {row["current_object_bridge_row_id"]: row for row in rows}
    required = {
        "current_object_bridge::legacy_static_lane",
        "current_object_bridge::selected_runtime_benchmark",
        "current_object_bridge::selected_public_interest_component",
        "current_object_bridge::selected_legacy_runtime_tdc_component",
        "current_object_bridge::r38_public_interest_candidate",
        "current_object_bridge::r38_beta_chi_tdc_candidate",
        "current_object_bridge::r38_composite_candidate",
        "current_object_bridge::d1_safe_yield_bounded_low",
        "current_object_bridge::d1_safe_yield_bounded_base",
        "current_object_bridge::d1_safe_yield_bounded_high",
    }
    missing = required - set(by_id)
    if missing:
        raise CurrentObjectBridgeError(f"missing current bridge rows: {sorted(missing)}")
    selected = [row for row in rows if row["selected_current_row"] == "true"]
    if len(selected) != 1:
        raise CurrentObjectBridgeError(
            f"expected one selected current row, found {len(selected)}"
        )
    selected_row = selected[0]
    if selected_row["current_object_id"] != SELECTED_CURRENT_ID:
        raise CurrentObjectBridgeError("wrong selected current object")
    if (
        selected_row["n_bil"] != SELECTED_CURRENT_N
        or selected_row["d_bil"] != SELECTED_CURRENT_D
        or selected_row["rw"] != SELECTED_CURRENT_RW
    ):
        raise CurrentObjectBridgeError("selected current values drifted")
    component_sum = Decimal(PUBLIC_INTEREST_COMPONENT) + Decimal(
        LEGACY_RUNTIME_TDC_COMPONENT
    )
    if abs(component_sum - Decimal(SELECTED_CURRENT_N)) > Decimal("1e-12"):
        raise CurrentObjectBridgeError("selected current components do not sum to N")
    for row in rows:
        if row["selected_current_component"] == "true" and row[
            "selected_current_row"
        ] != "false":
            raise CurrentObjectBridgeError("component row selected as full object")
        if row["current_object_id"].startswith("r38") and row[
            "selected_current_row"
        ] != "false":
            raise CurrentObjectBridgeError("R38 row selected current")
        if row["current_object_id"].startswith("d1_safe_yield") and (
            row["selected_current_row"] != "false"
            or row["central_n_delta_bil_allowed"] != "false"
            or row["central_n_delta_bil"] != "0"
        ):
            raise CurrentObjectBridgeError("D1 safe-yield row is central or selected")
        if "hybrid" in row["current_object_id"]:
            raise CurrentObjectBridgeError("hybrid current object is forbidden")
    legacy = by_id["current_object_bridge::legacy_static_lane"]
    if legacy["rw"] != LEGACY_STATIC_RW or legacy["selected_current_row"] != "false":
        raise CurrentObjectBridgeError("legacy static lane must remain reference only")
    r38_tdc = by_id["current_object_bridge::r38_beta_chi_tdc_candidate"]
    if (
        r38_tdc["r38_beta_chi_tdc_candidate_bil"] != R38_TDC_CANDIDATE
        or r38_tdc["tdc_formula_basis"] != "tdc_change_ex_overlap_bil * beta * chi"
    ):
        raise CurrentObjectBridgeError("R38 TDC candidate must use ex-overlap beta chi")
    r38_composite = by_id["current_object_bridge::r38_composite_candidate"]
    if (
        r38_composite["n_bil"] != R38_COMPOSITE_N
        or r38_composite["rw"] != R38_COMPOSITE_RW
        or r38_composite["selected_current_row"] != "false"
    ):
        raise CurrentObjectBridgeError("R38 composite candidate is wrong or selected")


def validate_current_object_freeze_decision(
    rows: Sequence[Mapping[str, str]],
    *,
    bridge_rows: Sequence[Mapping[str, str]],
) -> None:
    """Validate the freeze decision against bridge rows."""

    if len(rows) != 1:
        raise CurrentObjectBridgeError("expected one freeze decision row")
    selected = _single_selected_bridge(bridge_rows)
    decision = rows[0]
    if (
        decision["selected_current_object_id"] != selected["current_object_id"]
        or decision["selected_n_bil"] != selected["n_bil"]
        or decision["selected_d_bil"] != selected["d_bil"]
        or decision["selected_rw"] != selected["rw"]
    ):
        raise CurrentObjectBridgeError("freeze decision does not preserve selected row")
    if "hybrid" not in decision["no_hybrid_rule"]:
        raise CurrentObjectBridgeError("freeze decision missing no-hybrid rule")


def _bridge_row(
    row_id: str,
    current_object_id: str,
    row_kind: str,
    source_surface: str,
    selected_current_row: str,
    selected_current_component: str,
    current_object_role: str,
    n_bil: str,
    d_bil: str,
    rw: str,
    public_interest_component_bil: str,
    legacy_runtime_tdc_component_bil: str,
    r38_public_interest_candidate_bil: str,
    r38_beta_chi_tdc_candidate_bil: str,
    safe_yield_scenario: str,
    safe_yield_support_bil: str,
    central_n_delta_bil_allowed: str,
    central_n_delta_bil: str,
    tdc_formula_basis: str,
    replacement_gate_status: str,
    runtime_replay_status: str,
    allowed_use: str,
    blocked_use: str,
    claim_boundary: str,
) -> dict[str, str]:
    return {
        "current_object_bridge_row_id": f"current_object_bridge::{row_id}",
        "current_object_id": current_object_id,
        "row_kind": row_kind,
        "period_object": "current",
        "source_surface": source_surface,
        "selected_current_row": selected_current_row,
        "selected_current_component": selected_current_component,
        "current_object_role": current_object_role,
        "n_bil": n_bil,
        "d_bil": d_bil,
        "rw": rw,
        "public_interest_component_bil": public_interest_component_bil,
        "legacy_runtime_tdc_component_bil": legacy_runtime_tdc_component_bil,
        "r38_public_interest_candidate_bil": r38_public_interest_candidate_bil,
        "r38_beta_chi_tdc_candidate_bil": r38_beta_chi_tdc_candidate_bil,
        "safe_yield_scenario": safe_yield_scenario,
        "safe_yield_support_bil": safe_yield_support_bil,
        "central_n_delta_bil_allowed": central_n_delta_bil_allowed,
        "central_n_delta_bil": central_n_delta_bil,
        "tdc_formula_basis": tdc_formula_basis,
        "replacement_gate_status": replacement_gate_status,
        "runtime_replay_status": runtime_replay_status,
        "allowed_use": allowed_use,
        "blocked_use": blocked_use,
        "claim_boundary": claim_boundary,
    }


def _read_required(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise CurrentObjectBridgeError(f"missing required input: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _selected_benchmark(rows: Sequence[Mapping[str, str]]) -> Mapping[str, str]:
    selected = [row for row in rows if row["current_benchmark_row_id"] == SELECTED_CURRENT_ID]
    if len(selected) != 1:
        raise CurrentObjectBridgeError(
            f"expected selected benchmark {SELECTED_CURRENT_ID}, found {len(selected)}"
        )
    return selected[0]


def _single_row(rows: Sequence[Mapping[str, str]], label: str) -> Mapping[str, str]:
    if len(rows) != 1:
        raise CurrentObjectBridgeError(f"expected one {label} row, found {len(rows)}")
    return rows[0]


def _single_selected_bridge(rows: Sequence[Mapping[str, str]]) -> Mapping[str, str]:
    selected = [row for row in rows if row["selected_current_row"] == "true"]
    if len(selected) != 1:
        raise CurrentObjectBridgeError(
            f"expected one selected bridge row, found {len(selected)}"
        )
    return selected[0]


def _row_count(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return max(sum(1 for _ in csv.DictReader(handle)), 0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _combined_runtime_status(rows: Sequence[Mapping[str, str]]) -> str:
    if all(row["exists"] == "true" for row in rows):
        return "runtime_replay_inputs_present"
    return "generated_output_backed_not_runtime_replay_backed"
