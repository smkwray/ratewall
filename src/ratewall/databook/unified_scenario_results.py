"""Unified Assumption Mode scenario-result surface and PNG diagnostics."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ratewall.databook.denominator_response_application import (
    denominator_response_application_rows,
)
from ratewall.databook.denominator_response_coefficient import (
    selected_frbus_structural_curve_denominator_response_profile,
)
from ratewall.databook.model_artifact_store import (
    ArtifactManifestView,
    artifact_manifest_exists,
)
from ratewall.databook.preliminary_scenario_results import (
    FRBUS_STRUCTURAL_CLAIM_BOUNDARY,
    FRBUS_STRUCTURAL_TERM_PREMIUM_BENCHMARK_LABEL,
)

DEFAULT_UNIFIED_SUITE_DIR = Path(
    "var/tdcsim_cbo_suite_20260626_tdcsim72dc6c7_t1_t2"
)

COMBINED_SCENARIO_GATE_IDS = {
    "tdcsim_combo_high_pressure_v1",
    "tdcsim_combo_lower_pressure_v1",
    "tdcsim_combo_fiscal_stress_market_offset_v1",
    "tdcsim_combo_fiscal_relief_holder_stress_v1",
}

UNIFIED_SCENARIO_RESULT_FIELDS = [
    "unified_scenario_result_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_label",
    "scenario_axis",
    "scenario_family",
    "summary_role",
    "comparison_group",
    "baseline_scenario_id",
    "paired_issuance_only_scenario_id",
    "term_premium_tier",
    "ten_year_nominal_rate_shock_bp",
    "rate_path_changes",
    "holder_preferences_change",
    "combined_holder_rate_gate_status",
    "same_run_source_status",
    "total_current_demand_support_bil",
    "delta_total_current_demand_support_bil",
    "tdc_current_demand_support_bil",
    "delta_tdc_current_demand_support_bil",
    "direct_treasury_current_demand_support_bil",
    "delta_direct_treasury_current_demand_support_bil",
    "bank_treasury_current_demand_support_bil",
    "delta_bank_treasury_current_demand_support_bil",
    "support_mechanism_profile",
    "dominant_delta_support_component",
    "dominant_delta_support_component_bil",
    "mmf_deposit_pass_through",
    "path_bps_year",
    "curve_overlay_5y_bp",
    "curve_overlay_10y_bp",
    "curve_overlay_30y_bp",
    "selected_denominator_response_profile_id",
    "selected_denominator_response_label",
    "selected_denominator_response_coefficient",
    "selected_denominator_response_coefficient_unit",
    "selected_denominator_response_status",
    "frozen_denominator_bil",
    "selected_delta_denominator_bil",
    "selected_moving_denominator_bil",
    "frozen_ratewall_ratio",
    "frozen_delta_ratewall_ratio_vs_baseline",
    "selected_moving_ratewall_ratio",
    "selected_moving_delta_ratewall_ratio_vs_baseline",
    "moving_minus_frozen_ratewall_ratio",
    "selected_wall_hit_status",
    "beta_chi_sign_stability_status",
    "source_beta_chi_sign_stability_status",
    "moving_d_beta_chi_sign_stability_status",
    "moving_d_beta_chi_claim_strength_status",
    "moving_d_beta_chi_claim_gate_status",
    "beta_chi_min_delta_ratewall_ratio",
    "beta_chi_max_delta_ratewall_ratio",
    "model_relevance_class",
    "recommended_use",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "denominator_prior_update_allowed",
]

UNIFIED_SCENARIO_MODEL_DECISION_FIELDS = [
    "unified_scenario_model_decision_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "selected_moving_delta_ratewall_ratio_vs_baseline",
    "delta_total_current_demand_support_bil",
    "selected_delta_denominator_bil",
    "source_beta_chi_sign_stability_status",
    "moving_d_beta_chi_sign_stability_status",
    "moving_d_beta_chi_claim_strength_status",
    "carry_forward_status",
    "economic_read",
    "primary_mechanism",
    "model_gap",
    "canonical_promotion_status",
]


class UnifiedScenarioResultError(ValueError):
    """Raised when unified scenario rows cannot be assembled consistently."""


@dataclass(frozen=True)
class _SuiteFiles:
    root: Path
    artifact: ArtifactManifestView | None


def unified_scenario_result_rows_from_directory(
    suite_dir: str | Path = DEFAULT_UNIFIED_SUITE_DIR,
) -> list[dict[str, str]]:
    """Build one current-suite scenario surface with recomputed moving D."""

    files = _suite_files(suite_dir)
    return unified_scenario_result_rows(
        summary_rows=_read_csv(files, "ratewall_tdcsim_cbo_model_scenario_summary.csv"),
        effect_rows=_read_csv(files, "ratewall_tdcsim_cbo_scenario_effect.csv"),
        ratio_rows=_read_csv(files, "ratewall_tdcsim_cbo_fiscal_year_ratio_input.csv"),
        curve_rows=_read_csv(files, "ratewall_tdcsim_cbo_curve_denominator_input.csv"),
        beta_chi_rows=_read_csv(
            files,
            "ratewall_tdcsim_cbo_model_scenario_beta_chi_sign_stability.csv",
        ),
        materiality_rows=_read_csv(
            files,
            "ratewall_tdcsim_cbo_model_scenario_materiality_classification.csv",
        ),
        scenario_payloads=_scenario_payloads(files),
    )


def unified_scenario_result_rows(
    *,
    summary_rows: Iterable[Mapping[str, str]],
    effect_rows: Iterable[Mapping[str, str]],
    ratio_rows: Iterable[Mapping[str, str]],
    curve_rows: Iterable[Mapping[str, str]],
    beta_chi_rows: Iterable[Mapping[str, str]],
    materiality_rows: Iterable[Mapping[str, str]],
    scenario_payloads: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Combine saved TDCSim surfaces while recomputing the selected moving D."""

    summaries = _by_key(summary_rows, "summary")
    effects = _by_key(effect_rows, "effect")
    ratios = _by_key(ratio_rows, "ratio")
    curves = _by_key(curve_rows, "curve")
    beta_chi = _by_key(beta_chi_rows, "beta_chi")
    materiality = _by_key(materiality_rows, "materiality")
    profile = selected_frbus_structural_curve_denominator_response_profile(
        diagnostic_rows=[],
        path_object_rows=[],
    )
    moving_d = _by_key(
        denominator_response_application_rows(
            curves.values(),
            coefficient_profile=profile,
        ),
        "moving_d",
    )

    out: list[dict[str, str]] = []
    for key, summary in summaries.items():
        effect = _required(effects, key, "effect")
        ratio = _required(ratios, key, "ratio")
        curve = _required(curves, key, "curve")
        app = _required(moving_d, key, "moving-D application")
        beta = _required(beta_chi, key, "beta-chi")
        mat = _required(materiality, key, "materiality")
        payload = scenario_payloads.get(summary["scenario_id"], {})
        path_bps_year = _decimal(app["path_bps_year"])
        holder_changes = _has_holder_preferences(payload)
        rate_changes = path_bps_year != 0
        gate_status = _combined_holder_rate_gate_status(
            summary,
            effect=effect,
            curve=curve,
            app=app,
            payload=payload,
            holder_changes=holder_changes,
            rate_changes=rate_changes,
        )
        moving_ratio = _decimal(app["moving_ratewall_ratio"])
        out.append(
            {
                "unified_scenario_result_row_id": (
                    f"unified_scenario_result::{summary['fiscal_year']}::"
                    f"{summary['scenario_id']}"
                ),
                "fiscal_year": summary["fiscal_year"],
                "scenario_id": summary["scenario_id"],
                "scenario_label": summary["model_interpretation"],
                "scenario_axis": _scenario_axis(summary, holder_changes, rate_changes),
                "scenario_family": mat["scenario_family"],
                "summary_role": summary["summary_role"],
                "comparison_group": summary["comparison_group"],
                "baseline_scenario_id": summary["baseline_scenario_id"],
                "paired_issuance_only_scenario_id": summary[
                    "paired_issuance_only_scenario_id"
                ],
                "term_premium_tier": summary["term_premium_tier"],
                "ten_year_nominal_rate_shock_bp": summary[
                    "ten_year_nominal_rate_shock_bp"
                ],
                "rate_path_changes": _bool(rate_changes),
                "holder_preferences_change": _bool(holder_changes),
                "combined_holder_rate_gate_status": gate_status,
                "same_run_source_status": "pass_current_suite_single_manifest_surface",
                "total_current_demand_support_bil": effect[
                    "total_current_demand_support_bil"
                ],
                "delta_total_current_demand_support_bil": summary[
                    "delta_total_current_demand_support_bil"
                ],
                "tdc_current_demand_support_bil": effect[
                    "tdc_current_demand_support_bil"
                ],
                "delta_tdc_current_demand_support_bil": summary[
                    "delta_tdc_current_demand_support_bil"
                ],
                "direct_treasury_current_demand_support_bil": effect[
                    "direct_treasury_current_demand_support_bil"
                ],
                "delta_direct_treasury_current_demand_support_bil": summary[
                    "delta_direct_treasury_current_demand_support_bil"
                ],
                "bank_treasury_current_demand_support_bil": effect[
                    "bank_treasury_current_demand_support_bil"
                ],
                "delta_bank_treasury_current_demand_support_bil": summary[
                    "delta_bank_treasury_current_demand_support_bil"
                ],
                "support_mechanism_profile": summary["support_mechanism_profile"],
                "dominant_delta_support_component": summary[
                    "dominant_delta_support_component"
                ],
                "dominant_delta_support_component_bil": summary[
                    "dominant_delta_support_component_bil"
                ],
                "mmf_deposit_pass_through": ratio["mmf_deposit_pass_through"],
                "path_bps_year": app["path_bps_year"],
                "curve_overlay_5y_bp": curve["curve_overlay_5y_bp"],
                "curve_overlay_10y_bp": curve["curve_overlay_10y_bp"],
                "curve_overlay_30y_bp": curve["curve_overlay_30y_bp"],
                "selected_denominator_response_profile_id": app[
                    "denominator_response_profile_id"
                ],
                "selected_denominator_response_label": (
                    FRBUS_STRUCTURAL_TERM_PREMIUM_BENCHMARK_LABEL
                ),
                "selected_denominator_response_coefficient": app[
                    "denominator_response_coefficient"
                ],
                "selected_denominator_response_coefficient_unit": app[
                    "denominator_response_coefficient_unit"
                ],
                "selected_denominator_response_status": app[
                    "denominator_response_requirement_status"
                ],
                "frozen_denominator_bil": app["frozen_denominator_bil"],
                "selected_delta_denominator_bil": app["delta_denominator_bil"],
                "selected_moving_denominator_bil": app["moving_denominator_bil"],
                "frozen_ratewall_ratio": summary["level_ratewall_ratio"],
                "frozen_delta_ratewall_ratio_vs_baseline": summary[
                    "delta_ratewall_ratio_vs_baseline"
                ],
                "selected_moving_ratewall_ratio": app["moving_ratewall_ratio"],
                "selected_moving_delta_ratewall_ratio_vs_baseline": app[
                    "moving_delta_ratewall_ratio_vs_baseline"
                ],
                "moving_minus_frozen_ratewall_ratio": app[
                    "moving_minus_frozen_ratewall_ratio"
                ],
                "selected_wall_hit_status": (
                    "wall_hit" if moving_ratio >= Decimal("1") else "no_hit"
                ),
                "beta_chi_sign_stability_status": beta[
                    "sign_stability_status"
                ],
                "source_beta_chi_sign_stability_status": beta[
                    "sign_stability_status"
                ],
                "moving_d_beta_chi_sign_stability_status": (
                    "not_evaluated_run_beta_chi_claim_gate"
                ),
                "moving_d_beta_chi_claim_strength_status": (
                    "not_evaluated_run_beta_chi_claim_gate"
                ),
                "moving_d_beta_chi_claim_gate_status": (
                    "not_applied_to_unified_surface"
                ),
                "beta_chi_min_delta_ratewall_ratio": beta[
                    "min_delta_ratewall_ratio_over_beta_chi_grid"
                ],
                "beta_chi_max_delta_ratewall_ratio": beta[
                    "max_delta_ratewall_ratio_over_beta_chi_grid"
                ],
                "model_relevance_class": mat["model_relevance_class"],
                "recommended_use": mat["recommended_use"],
                "allowed_use": "unified_assumption_mode_scenario_readout",
                "blocked_use": (
                    "canonical_headline_promotion_without_owner_gate;"
                    "release_headline_claim_without_owner_gate;"
                    "denominator_prior_update;evidence_mode_claim;"
                    "path_ratio_denominator_replacement"
                ),
                "claim_boundary": FRBUS_STRUCTURAL_CLAIM_BOUNDARY,
                "canonical_ratio_entry": "false",
                "enters_main_ratio": "false",
                "evidence_mode_enabled": "false",
                "denominator_prior_update_allowed": "false",
            }
        )
    return sorted(out, key=lambda row: (int(row["fiscal_year"]), row["scenario_id"]))


def apply_moving_d_beta_chi_claim_gate(
    rows: Sequence[Mapping[str, str]],
    claim_gate_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Attach moving-D-aware beta-chi claim-gate statuses to unified rows."""

    claims = _by_key(claim_gate_rows, "beta-chi claim gate")
    out: list[dict[str, str]] = []
    for row in rows:
        key = (row["scenario_id"], row["fiscal_year"])
        claim = _required(claims, key, "beta-chi claim gate")
        enriched = dict(row)
        enriched["source_beta_chi_sign_stability_status"] = row[
            "source_beta_chi_sign_stability_status"
        ]
        enriched["moving_d_beta_chi_sign_stability_status"] = claim[
            "moving_d_beta_chi_sign_stability_status"
        ]
        enriched["moving_d_beta_chi_claim_strength_status"] = claim[
            "claim_strength_status"
        ]
        enriched["moving_d_beta_chi_claim_gate_status"] = (
            "pass_moving_d_beta_chi_claim_gate_joined"
        )
        out.append(enriched)
    return sorted(out, key=lambda row: (int(row["fiscal_year"]), row["scenario_id"]))


def write_unified_scenario_outputs(
    output_dir: str | Path,
    *,
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write unified CSV, PNG diagnostics, and a plain readout."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": out / "ratewall_unified_scenario_results.csv",
        "decision_csv": out / "ratewall_unified_scenario_model_decisions.csv",
        "readout_md": out / "unified_scenario_readout.md",
        "model_memo_md": out / "unified_scenario_model_memo.md",
        "png_delta_rw": out / "unified_01_delta_ratewall.png",
        "png_frozen_moving": out / "unified_02_frozen_vs_moving_ratewall.png",
        "png_components": out / "unified_03_mechanism_components.png",
        "png_combined": out / "unified_04_combined_scenarios.png",
    }
    _write_csv(paths["csv"], rows)
    _write_decision_csv(
        paths["decision_csv"],
        unified_scenario_model_decision_rows(rows),
    )
    paths["readout_md"].write_text(
        unified_scenario_readout_markdown(rows),
        encoding="utf-8",
    )
    paths["model_memo_md"].write_text(
        unified_scenario_model_memo_markdown(rows),
        encoding="utf-8",
    )
    _write_pngs(paths, rows)
    return paths


def unified_scenario_model_decision_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Classify rows for the forward model narrative without promoting them."""

    out = [
        {
            "unified_scenario_model_decision_row_id": (
                f"unified_scenario_model_decision::{row['fiscal_year']}::"
                f"{row['scenario_id']}"
            ),
            "fiscal_year": row["fiscal_year"],
            "scenario_id": row["scenario_id"],
            "scenario_axis": row["scenario_axis"],
            "selected_moving_delta_ratewall_ratio_vs_baseline": row[
                "selected_moving_delta_ratewall_ratio_vs_baseline"
            ],
            "delta_total_current_demand_support_bil": row[
                "delta_total_current_demand_support_bil"
            ],
            "selected_delta_denominator_bil": row["selected_delta_denominator_bil"],
            "source_beta_chi_sign_stability_status": row[
                "source_beta_chi_sign_stability_status"
            ],
            "moving_d_beta_chi_sign_stability_status": row[
                "moving_d_beta_chi_sign_stability_status"
            ],
            "moving_d_beta_chi_claim_strength_status": row[
                "moving_d_beta_chi_claim_strength_status"
            ],
            "carry_forward_status": _carry_forward_status(row),
            "economic_read": _economic_read(row),
            "primary_mechanism": _primary_mechanism(row),
            "model_gap": _model_gap(row),
            "canonical_promotion_status": (
                "blocked_scenario_mode_only_without_owner_gate"
            ),
        }
        for row in rows
    ]
    return sorted(out, key=lambda row: (int(row["fiscal_year"]), row["scenario_id"]))


def unified_scenario_readout_markdown(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Return a short economist-facing readout of the unified surface."""

    baseline = _baseline(rows)
    largest = sorted(
        [row for row in rows if row["scenario_id"] != baseline["scenario_id"]],
        key=lambda row: abs(
            _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
        ),
        reverse=True,
    )[:8]
    combined = [row for row in rows if row["scenario_axis"] == "combined_holder_rate"]
    lines = [
        "# Unified RateWall Scenario Readout",
        "",
        "RateWall is `RW = N / D`. `N` is current-demand support. `D` is the conventional-demand shortfall. A scenario hits the wall when `RW >= 1`.",
        "",
        "## What This Surface Does",
        "",
        "- Uses one current TDCSim/CBO suite as the source.",
        "- Recomputes moving `D` for every scenario with a nonzero rate path.",
        "- Keeps `D` fixed for holder-only and other zero-rate scenarios.",
        "- Includes combined holder-plus-rate rows only when the same suite has holder settings, rate settings, effect rows, and moving-D rows.",
        "",
        "## Baseline",
        "",
        f"- Scenario: `{baseline['scenario_id']}`.",
        f"- RW: `{baseline['selected_moving_ratewall_ratio']}`.",
        f"- `N`: `{baseline['total_current_demand_support_bil']}` billion.",
        f"- `D`: `{baseline['selected_moving_denominator_bil']}` billion.",
        "",
        "## Moving-D Assumption",
        "",
        f"- Profile: `{baseline['selected_denominator_response_profile_id']}`.",
        f"- Coefficient: `{baseline['selected_denominator_response_coefficient']}`.",
        f"- Unit: `{baseline['selected_denominator_response_coefficient_unit']}`.",
        "- Positive rate paths raise `D`; negative rate paths lower `D`.",
        "",
        "## Largest Scenario Movements",
        "",
    ]
    for row in largest:
        lines.append(
            "- "
            f"`{row['scenario_id']}`: selected delta RW "
            f"`{row['selected_moving_delta_ratewall_ratio_vs_baseline']}`, "
            f"axis `{row['scenario_axis']}`, path `{row['path_bps_year']}` bp-year, "
            f"delta `N` `{row['delta_total_current_demand_support_bil']}` bn, "
            f"delta `D` `{row['selected_delta_denominator_bil']}` bn."
        )
    lines.extend(["", "## Combined Rows", ""])
    if combined:
        for row in combined:
            lines.append(
                "- "
                f"`{row['scenario_id']}`: gate "
                f"`{row['combined_holder_rate_gate_status']}`, "
                f"selected delta RW "
                f"`{row['selected_moving_delta_ratewall_ratio_vs_baseline']}`."
            )
    else:
        lines.append("- No combined rows passed the current-suite gate.")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- These are Assumption Mode scenario rows, not headline canonical entries.",
            "- They do not update denominator priors and do not replace the canonical path-ratio denominator.",
        ]
    )
    return "\n".join(lines) + "\n"


def unified_scenario_model_memo_markdown(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Return a concise model memo separating mechanisms and remaining gaps."""

    baseline = _baseline(rows)
    decisions = unified_scenario_model_decision_rows(rows)
    decisions_by_id = {row["scenario_id"]: row for row in decisions}
    holder = _top_by_axis(rows, "holder_only")
    rate_up_down = _rate_direction_summary(rows)
    combined = _top_by_axis(rows, "combined_holder_rate")
    carry_forward = [
        row
        for row in decisions
        if row["carry_forward_status"].startswith("carry_forward")
    ]
    checks = [
        row
        for row in decisions
        if row["carry_forward_status"].startswith("keep_as")
    ]
    beta_chi_mixed = [
        row
        for row in decisions
        if row["model_gap"]
        == "beta_chi_range_mixed_sign_requires_assumption_label_or_narrower_gate"
    ]
    lines = [
        "# Unified Scenario Model Memo",
        "",
        "## Bottom Line",
        "",
        (
            "The current model result is that holder-allocation/TDC scenarios are "
            "large, rate-only scenarios are smaller but directionally important "
            "because they move `D`, and combined holder-plus-rate scenarios are "
            "the largest current stress cases."
        ),
        "",
        "No row is promoted into the canonical headline result. These are scenario-mode rows.",
        "",
        "## Baseline",
        "",
        f"- Baseline scenario: `{baseline['scenario_id']}`.",
        f"- Baseline RW: `{baseline['selected_moving_ratewall_ratio']}`.",
        f"- Baseline `N`: `{baseline['total_current_demand_support_bil']}` billion.",
        f"- Baseline `D`: `{baseline['selected_moving_denominator_bil']}` billion.",
        f"- MMF deposit pass-through: `{baseline['mmf_deposit_pass_through']}`.",
        "",
        "## Holder/TDC Mechanism",
        "",
        (
            "Holder scenarios change who absorbs Treasury issuance. When more "
            "issuance is absorbed by reserve-user sectors, TDCSim reports larger "
            "TDC current-demand support. Because these rows do not change rates, "
            "`D` stays fixed and RW moves through `N`."
        ),
        "",
        (
            f"- Largest holder row: `{holder['scenario_id']}` changes RW by "
            f"`{holder['selected_moving_delta_ratewall_ratio_vs_baseline']}`."
        ),
        f"- Its delta `N` is `{holder['delta_total_current_demand_support_bil']}` billion.",
        f"- Its delta `D` is `{holder['selected_delta_denominator_bil']}` billion.",
        f"- Carry-forward status: `{decisions_by_id[holder['scenario_id']]['carry_forward_status']}`.",
        "",
        "## Rate/Denominator Mechanism",
        "",
        (
            "Rate scenarios change RW partly through `D`. Under the selected "
            "FRB/US structural Assumption Mode denominator route, rate-down "
            "paths lower `D` and raise RW; "
            "rate-up paths raise `D` and lower RW."
        ),
        "",
        (
            f"- Largest rate-down row: `{rate_up_down['down']['scenario_id']}` "
            f"changes RW by "
            f"`{rate_up_down['down']['selected_moving_delta_ratewall_ratio_vs_baseline']}` "
            f"with delta `D` `{rate_up_down['down']['selected_delta_denominator_bil']}` billion."
        ),
        (
            f"- Largest rate-up row: `{rate_up_down['up']['scenario_id']}` "
            f"changes RW by "
            f"`{rate_up_down['up']['selected_moving_delta_ratewall_ratio_vs_baseline']}` "
            f"with delta `D` `{rate_up_down['up']['selected_delta_denominator_bil']}` billion."
        ),
        f"- Denominator coefficient: `{baseline['selected_denominator_response_coefficient']}`.",
        "",
        "## Combined Mechanism",
        "",
        (
            "Combined rows put the holder/TDC channel and rate/D channel in the "
            "same scenario. The largest combined rows pair higher reserve-user "
            "absorption with a rate-down path, so `N` rises while `D` falls."
        ),
        "",
        (
            f"- Largest combined row: `{combined['scenario_id']}` changes RW by "
            f"`{combined['selected_moving_delta_ratewall_ratio_vs_baseline']}`."
        ),
        f"- Its delta `N` is `{combined['delta_total_current_demand_support_bil']}` billion.",
        f"- Its delta `D` is `{combined['selected_delta_denominator_bil']}` billion.",
        f"- Gate status: `{combined['combined_holder_rate_gate_status']}`.",
        "",
        "## Carry Forward",
        "",
        (
            f"- Carry forward as main scenario families: `{len(carry_forward)}` rows."
        ),
        f"- Keep as checks or sensitivities: `{len(checks)}` rows.",
        "- Main scenario families to keep: holder/TDC, rate/D, and combined holder-plus-rate.",
        "- Checks to keep: primary-deficit benchmark, MMF pass-through, and issuance-only controls.",
        "",
        "## Remaining Model Gaps",
        "",
    ]
    if beta_chi_mixed:
        lines.append(
            "- "
            f"{len(beta_chi_mixed)} rows remain point-calibrated only after the "
            "moving-D-aware beta-chi gate; final claims need either a narrower "
            "admitted beta-chi range or explicit assumption labels."
        )
    else:
        lines.append(
            "- The moving-D-aware beta-chi gate does not leave a mixed-sign blocker "
            "on the current carry-forward rows, but no new beta or chi floor is "
            "admitted."
        )
    lines.extend(
        [
        (
            "- The moving-D coefficient is the final FRB/US structural "
            "Assumption Mode denominator route, not empirical same-axis "
            "Treasury evidence, not a local econometric estimate, and not a "
            "denominator-prior update."
        ),
        (
            "- Canonical promotion still needs an owner gate. Until then, the "
            "correct use is scenario comparison, not headline replacement."
        ),
        ]
    )
    return "\n".join(lines) + "\n"


def _suite_files(suite_dir: str | Path) -> _SuiteFiles:
    root = Path(suite_dir)
    artifact = ArtifactManifestView.from_root(root) if artifact_manifest_exists(root) else None
    return _SuiteFiles(root=root, artifact=artifact)


def _read_csv(files: _SuiteFiles, logical_path: str) -> list[dict[str, str]]:
    if files.artifact is not None:
        if not files.artifact.has_file(logical_path):
            raise UnifiedScenarioResultError(
                f"missing required suite CSV: {logical_path}"
            )
        with files.artifact.open_text(logical_path) as handle:
            return list(csv.DictReader(handle))
    path = files.root / logical_path
    if not path.exists():
        raise UnifiedScenarioResultError(f"missing required suite CSV: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _scenario_payloads(files: _SuiteFiles) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    if files.artifact is not None:
        paths = files.artifact.list_files(prefix="scenarios/", suffix=".json")
        for logical_path in paths:
            payload = json.loads(files.artifact.read_text(logical_path))
            scenario_id = str(payload.get("scenario_id", ""))
            if scenario_id:
                out[scenario_id] = payload
        return out
    scenario_dir = files.root / "scenarios"
    if not scenario_dir.exists():
        return out
    for path in sorted(scenario_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        scenario_id = str(payload.get("scenario_id", ""))
        if scenario_id:
            out[scenario_id] = payload
    return out


def _combined_holder_rate_gate_status(
    summary: Mapping[str, str],
    *,
    effect: Mapping[str, str],
    curve: Mapping[str, str],
    app: Mapping[str, str],
    payload: Mapping[str, Any],
    holder_changes: bool,
    rate_changes: bool,
) -> str:
    if summary["scenario_id"] not in COMBINED_SCENARIO_GATE_IDS:
        return "not_combined_holder_rate_scenario"
    if summary["summary_role"] != "combined_narrative_scenario":
        return "blocked_combined_row_wrong_summary_role"
    if not payload:
        return "blocked_combined_row_missing_scenario_config"
    if not holder_changes:
        return "blocked_combined_row_missing_holder_preferences"
    if not _has_nonzero_nominal_curve(payload):
        return "blocked_combined_row_missing_nonzero_curve_overlay"
    if not rate_changes:
        return "blocked_combined_row_zero_effective_rate_path"
    if not effect.get("tdcsim_cbo_scenario_effect_row_id"):
        return "blocked_combined_row_missing_effect"
    if _decimal(curve["effective_curve_overlay_bp"]) != _decimal(app["path_bps_year"]):
        return "blocked_combined_row_curve_path_mismatch"
    if app["denominator_response_requirement_status"] != (
        "pass_moving_D_computed_from_admitted_profile"
    ):
        return "blocked_combined_row_missing_moving_D"
    return "pass_combined_holder_rate_same_run_gate"


def _scenario_axis(
    summary: Mapping[str, str],
    holder_changes: bool,
    rate_changes: bool,
) -> str:
    if summary["summary_role"] == "baseline_anchor":
        return "baseline"
    if holder_changes and rate_changes:
        return "combined_holder_rate"
    if holder_changes:
        return "holder_only"
    if rate_changes:
        return "rate_or_issuance_rate"
    if "mmf_pass_through" in summary["scenario_id"]:
        return "mmf_passthrough"
    if summary["summary_role"] == "issuance_only_control":
        return "issuance_only"
    return "other_zero_rate"


def _has_holder_preferences(payload: Mapping[str, Any]) -> bool:
    rows = (
        payload.get("overrides", {})
        .get("holder_preferences", {})
        .get("rows", [])
    )
    return bool(rows)


def _has_nonzero_nominal_curve(payload: Mapping[str, Any]) -> bool:
    curve = payload.get("overrides", {}).get("nominal_yield_curve", {})
    shocks = curve.get("shocks", []) if isinstance(curve, Mapping) else []
    for shock in shocks:
        if _decimal(shock.get("shock_bp", "0")) != 0:
            return True
    return False


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=UNIFIED_SCENARIO_RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_decision_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=UNIFIED_SCENARIO_MODEL_DECISION_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_pngs(paths: Mapping[str, Path], rows: Sequence[Mapping[str, str]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nonbaseline = [row for row in rows if row["scenario_axis"] != "baseline"]
    ranked = sorted(
        nonbaseline,
        key=lambda row: abs(
            _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
        ),
    )
    fig, ax = plt.subplots(figsize=(11, 7.5))
    labels = [_short_label(row) for row in ranked]
    values = [
        _float(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
        for row in ranked
    ]
    colors = [_axis_color(row["scenario_axis"]) for row in ranked]
    ax.barh(labels, values, color=colors)
    ax.axvline(0, color="#111827", linewidth=0.8)
    ax.set_title("Unified Scenarios: Selected Moving-D Delta RateWall")
    ax.set_xlabel("RateWall ratio change vs baseline")
    fig.tight_layout()
    fig.savefig(paths["png_delta_rw"], dpi=180)
    plt.close(fig)

    rate_rows = [row for row in rows if row["rate_path_changes"] == "true"]
    rate_rows = sorted(rate_rows, key=lambda row: row["scenario_id"])
    fig, ax = plt.subplots(figsize=(11, 6.2))
    x = range(len(rate_rows))
    width = 0.38
    ax.bar(
        [index - width / 2 for index in x],
        [_float(row["frozen_delta_ratewall_ratio_vs_baseline"]) for row in rate_rows],
        width,
        label="Frozen D",
        color="#94a3b8",
    )
    ax.bar(
        [index + width / 2 for index in x],
        [
            _float(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
            for row in rate_rows
        ],
        width,
        label="Moving D",
        color="#2563eb",
    )
    ax.axhline(0, color="#111827", linewidth=0.8)
    ax.set_xticks(list(x), [_short_label(row) for row in rate_rows], rotation=25, ha="right")
    ax.set_title("Rate-Changing Scenarios: Frozen vs Moving D")
    ax.set_ylabel("Delta RateWall")
    ax.legend()
    fig.tight_layout()
    fig.savefig(paths["png_frozen_moving"], dpi=180)
    plt.close(fig)

    top = sorted(
        nonbaseline,
        key=lambda row: abs(
            _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
        ),
        reverse=True,
    )[:8]
    fig, ax = plt.subplots(figsize=(11, 6.6))
    x = range(len(top))
    width = 0.22
    components = [
        ("delta_tdc_current_demand_support_bil", "TDC", "#2563eb"),
        ("delta_direct_treasury_current_demand_support_bil", "Direct", "#7c3aed"),
        ("delta_bank_treasury_current_demand_support_bil", "Bank", "#0891b2"),
        ("selected_delta_denominator_bil", "D move", "#ea580c"),
    ]
    offsets = (-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width)
    for offset, (field, label, color) in zip(offsets, components, strict=True):
        ax.bar(
            [index + offset for index in x],
            [_float(row[field]) for row in top],
            width,
            label=label,
            color=color,
        )
    ax.axhline(0, color="#111827", linewidth=0.8)
    ax.set_xticks(list(x), [_short_label(row) for row in top], rotation=25, ha="right")
    ax.set_title("Largest Scenarios: Numerator Components and D Move")
    ax.set_ylabel("Billion dollars")
    ax.legend()
    fig.tight_layout()
    fig.savefig(paths["png_components"], dpi=180)
    plt.close(fig)

    combined = [row for row in rows if row["scenario_axis"] == "combined_holder_rate"]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.barh(
        [_short_label(row) for row in combined],
        [
            _float(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
            for row in combined
        ],
        color="#0f766e",
    )
    ax.axvline(0, color="#111827", linewidth=0.8)
    ax.set_title("Combined Holder + Rate Scenarios Passing Gate")
    ax.set_xlabel("Selected moving-D delta RateWall")
    fig.tight_layout()
    fig.savefig(paths["png_combined"], dpi=180)
    plt.close(fig)


def _by_key(
    rows: Iterable[Mapping[str, str]],
    label: str,
) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["scenario_id"], row["fiscal_year"])
        if key in out:
            raise UnifiedScenarioResultError(f"duplicate {label} row for {key}")
        out[key] = dict(row)
    return out


def _required(
    rows: Mapping[tuple[str, str], dict[str, str]],
    key: tuple[str, str],
    label: str,
) -> dict[str, str]:
    try:
        return rows[key]
    except KeyError as exc:
        raise UnifiedScenarioResultError(f"missing {label} row for {key}") from exc


def _baseline(rows: Sequence[Mapping[str, str]]) -> Mapping[str, str]:
    for row in rows:
        if row["scenario_id"] == row["baseline_scenario_id"]:
            return row
    raise UnifiedScenarioResultError("missing baseline row")


def _top_by_axis(
    rows: Sequence[Mapping[str, str]],
    axis: str,
) -> Mapping[str, str]:
    selected = [row for row in rows if row["scenario_axis"] == axis]
    if not selected:
        raise UnifiedScenarioResultError(f"missing scenario axis: {axis}")
    return max(
        selected,
        key=lambda row: abs(
            _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
        ),
    )


def _rate_direction_summary(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Mapping[str, str]]:
    rate_rows = [row for row in rows if row["scenario_axis"] == "rate_or_issuance_rate"]
    down = [row for row in rate_rows if _decimal(row["path_bps_year"]) < 0]
    up = [row for row in rate_rows if _decimal(row["path_bps_year"]) > 0]
    if not down or not up:
        raise UnifiedScenarioResultError("rate memo requires rate-up and rate-down rows")
    return {
        "down": max(
            down,
            key=lambda row: abs(
                _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
            ),
        ),
        "up": max(
            up,
            key=lambda row: abs(
                _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
            ),
        ),
    }


def _carry_forward_status(row: Mapping[str, str]) -> str:
    axis = row["scenario_axis"]
    if axis == "baseline":
        return "baseline_reference"
    if axis == "combined_holder_rate":
        if row["combined_holder_rate_gate_status"] == (
            "pass_combined_holder_rate_same_run_gate"
        ):
            return "carry_forward_main_combined_scenario_family"
        return "park_failed_combined_gate"
    if axis == "holder_only":
        return "carry_forward_main_holder_tdc_scenario_family"
    if axis == "rate_or_issuance_rate":
        return "carry_forward_main_rate_denominator_scenario_family"
    if axis == "mmf_passthrough":
        return "keep_as_passthrough_sensitivity_check"
    if axis == "issuance_only":
        return "keep_as_issuance_control_check"
    return "keep_as_model_benchmark_check"


def _economic_read(row: Mapping[str, str]) -> str:
    axis = row["scenario_axis"]
    if axis == "baseline":
        return "CBO-grounded forward baseline reference."
    if axis == "combined_holder_rate":
        return "Joint holder-allocation and rate-path scenario."
    if axis == "holder_only":
        return "Holder allocation changes RateWall through TDC support in N."
    if axis == "rate_or_issuance_rate":
        return "Rate path changes RateWall through selected moving D."
    if axis == "mmf_passthrough":
        return "MMF pass-through sensitivity around the TDC deposit channel."
    if axis == "issuance_only":
        return "Issuance-mix accounting control before rate-path movement."
    return "Benchmark check row for scale and sign."


def _primary_mechanism(row: Mapping[str, str]) -> str:
    axis = row["scenario_axis"]
    if axis == "baseline":
        return "baseline_reference"
    if axis == "combined_holder_rate":
        return "tdc_numerator_plus_moving_denominator"
    if axis == "holder_only":
        return "tdc_numerator"
    if axis == "rate_or_issuance_rate":
        return "moving_denominator"
    if axis == "mmf_passthrough":
        return "tdc_passthrough_sensitivity"
    if axis == "issuance_only":
        return "issuance_accounting_control"
    return "benchmark_scale_check"


def _model_gap(row: Mapping[str, str]) -> str:
    axis = row["scenario_axis"]
    if axis == "baseline":
        return "none_baseline_reference"
    if axis == "rate_or_issuance_rate":
        return "moving_D_profile_is_final_structural_assumption_mode_not_empirical_same_axis"
    if _beta_chi_decision_status(row) == "mixed_sign":
        return "beta_chi_range_mixed_sign_requires_assumption_label_or_narrower_gate"
    if axis == "combined_holder_rate":
        return "combined_assumption_scenario_requires_owner_gate_for_headline_use"
    return "scenario_mode_only_no_canonical_promotion"


def _beta_chi_decision_status(row: Mapping[str, str]) -> str:
    status = row.get("moving_d_beta_chi_sign_stability_status", "")
    if status and not status.startswith("not_evaluated"):
        return status
    return row.get("beta_chi_sign_stability_status", "")


def _axis_color(axis: str) -> str:
    return {
        "baseline": "#64748b",
        "combined_holder_rate": "#0f766e",
        "holder_only": "#2563eb",
        "rate_or_issuance_rate": "#dc2626",
        "mmf_passthrough": "#7c3aed",
        "issuance_only": "#f97316",
        "other_zero_rate": "#64748b",
    }.get(axis, "#64748b")


def _short_label(row: Mapping[str, str]) -> str:
    label = row.get("scenario_label") or row["scenario_id"]
    label = label.replace("tdcsim_", "").replace("_v1", "")
    return label[:42]


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise UnifiedScenarioResultError(f"invalid decimal value: {value}") from exc


def _float(value: object) -> float:
    return float(_decimal(value))


def _bool(value: bool) -> str:
    return "true" if value else "false"
