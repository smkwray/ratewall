"""Beta-chi assumption discipline for unified RateWall scenario claims."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.model_artifact_store import (
    ArtifactManifestView,
    artifact_manifest_exists,
)
from ratewall.databook.unified_scenario_results import (
    DEFAULT_UNIFIED_SUITE_DIR,
    unified_scenario_result_rows_from_directory,
)

DEFAULT_BETA_CHI_SOURCE_CONTEXT_PATHS = {
    "tdcsim_holder_absorption_path": Path(
        "data/raw/ratewall_sibling_calibration/tdcsim/inputs/"
        "tdcsim_holder_absorption_path.csv"
    ),
    "tdcest_z1_domestic_nonbank_sector_context": Path(
        "data/raw/ratewall_sibling_calibration/"
        "tdcest_z1_domestic_nonbank_sector_context.csv"
    ),
    "tdcest_mmf_route_split_context": Path(
        "data/raw/ratewall_sibling_calibration/tdcest_mmf_route_split_context.csv"
    ),
    "tdcest_domestic_nonbank_monetary_route_bridge": Path(
        "data/raw/ratewall_sibling_calibration/"
        "tdcest_domestic_nonbank_monetary_route_bridge.csv"
    ),
}

BETA_CHI_CLAIM_GATE_FIELDS = [
    "beta_chi_claim_gate_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "current_beta",
    "current_chi",
    "current_beta_times_chi",
    "existing_grid_min_beta",
    "existing_grid_min_chi",
    "selected_moving_delta_ratewall_ratio_vs_baseline",
    "grid_min_moving_delta_ratewall_ratio",
    "grid_max_moving_delta_ratewall_ratio",
    "grid_signs_observed",
    "grid_same_sign_cell_count",
    "grid_cell_count",
    "moving_d_beta_chi_sign_stability_status",
    "zero_crossing_beta_times_chi_moving_d",
    "zero_crossing_status_moving_d",
    "narrower_range_admission_status",
    "claim_strength_status",
    "final_model_use",
    "canonical_promotion_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_ROBUSTNESS_THRESHOLD_FIELDS = [
    "beta_chi_threshold_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "selected_moving_delta_ratewall_ratio_vs_baseline",
    "point_sign",
    "current_beta",
    "current_chi",
    "current_beta_times_chi",
    "existing_grid_min_beta",
    "existing_grid_min_chi",
    "zero_crossing_beta_times_chi_moving_d",
    "zero_crossing_status_moving_d",
    "required_chi_floor_at_existing_min_beta",
    "required_beta_floor_at_existing_min_chi",
    "current_beta_chi_margin_over_crossing",
    "existing_floor_gap_status",
    "model_improvement_target",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_EVIDENCE_TARGET_FIELDS = [
    "beta_chi_evidence_target_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "selected_moving_delta_ratewall_ratio_vs_baseline",
    "point_sign",
    "current_beta_times_chi",
    "existing_grid_min_beta_times_chi",
    "required_beta_chi_floor",
    "required_product_lift_over_existing_min",
    "required_chi_floor_at_existing_min_beta",
    "required_beta_floor_at_existing_min_chi",
    "evidence_distance_tier",
    "source_evidence_question",
    "current_model_action",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_SOURCE_CONTEXT_FIELDS = [
    "beta_chi_source_context_row_id",
    "source_context_id",
    "source_path",
    "source_present",
    "source_row_count",
    "latest_quarter",
    "source_backed_context_rows",
    "current_demand_eligible_rows",
    "deposit_pass_through_true_rows",
    "deposit_pass_through_unknown_rows",
    "admitted_beta_floor_rows",
    "admitted_chi_floor_rows",
    "admitted_beta_chi_floor_rows",
    "source_review_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_SOURCE_REVIEW_FIELDS = [
    "beta_chi_source_review_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "selected_moving_delta_ratewall_ratio_vs_baseline",
    "evidence_distance_tier",
    "required_beta_chi_floor",
    "required_product_lift_over_existing_min",
    "local_source_context_count",
    "local_source_rows_scanned",
    "local_current_demand_eligible_rows",
    "local_admitted_beta_floor_rows",
    "local_admitted_chi_floor_rows",
    "local_admitted_beta_chi_floor_rows",
    "source_review_result",
    "post_review_model_action",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_EXTERNAL_EVIDENCE_FIELDS = [
    "beta_chi_external_evidence_row_id",
    "evidence_id",
    "evidence_family",
    "candidate_floor_object",
    "candidate_floor_value",
    "source_title",
    "source_locator",
    "source_value_label",
    "source_directness",
    "numeric_screen_status",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_EXTERNAL_FLOOR_REVIEW_FIELDS = [
    "beta_chi_external_floor_review_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "evidence_distance_tier",
    "required_chi_floor_at_existing_min_beta",
    "required_beta_floor_at_existing_min_chi",
    "external_beta_candidates_clearing_floor",
    "external_chi_candidates_clearing_floor",
    "external_admitted_beta_floor_rows",
    "external_admitted_chi_floor_rows",
    "best_numeric_chi_candidate",
    "best_numeric_beta_candidate",
    "external_floor_review_result",
    "post_review_model_action",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_CHI_BRIDGE_CANDIDATE_FIELDS = [
    "beta_chi_chi_bridge_candidate_row_id",
    "bridge_candidate_id",
    "evidence_family",
    "candidate_chi_value",
    "source_title",
    "source_locator",
    "source_value_label",
    "economic_object",
    "mapping_to_ratewall_chi",
    "directness_tier",
    "empirical_status",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_CHI_BRIDGE_TARGET_REVIEW_FIELDS = [
    "beta_chi_chi_bridge_target_review_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "evidence_distance_tier",
    "required_chi_floor_at_existing_min_beta",
    "best_bridge_candidate_id",
    "best_bridge_candidate_chi_value",
    "required_mapping_share_of_best_candidate",
    "mapping_share_feasibility_tier",
    "candidate_can_clear_floor_before_mapping_haircut",
    "admitted_chi_floor_after_bridge_rows",
    "bridge_review_result",
    "post_review_model_action",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

BETA_CHI_CHI_MAPPING_SENSITIVITY_FIELDS = [
    "beta_chi_chi_mapping_sensitivity_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "evidence_distance_tier",
    "bridge_candidate_id",
    "candidate_chi_value",
    "mapping_share_profile",
    "mapping_share",
    "implied_chi_floor",
    "existing_grid_min_chi",
    "required_chi_floor_at_existing_min_beta",
    "clears_required_chi_floor",
    "mapping_result",
    "post_mapping_model_use",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DEFAULT_CHI_BRIDGE_MAPPING_SHARE_PROFILES = (
    ("minimal_bridge", Decimal("0.15")),
    ("low_bridge", Decimal("0.25")),
    ("medium_bridge", Decimal("0.50")),
    ("large_bridge", Decimal("0.70")),
    ("full_candidate", Decimal("1")),
)


class BetaChiAssumptionDisciplineError(ValueError):
    """Raised when beta-chi claim-gate rows cannot be computed safely."""


@dataclass(frozen=True)
class _SuiteFiles:
    root: Path
    artifact: ArtifactManifestView | None


def beta_chi_claim_gate_rows_from_directory(
    suite_dir: str | Path = DEFAULT_UNIFIED_SUITE_DIR,
) -> list[dict[str, str]]:
    """Build moving-D-aware beta-chi claim-gate rows for the current suite."""

    files = _suite_files(suite_dir)
    return beta_chi_claim_gate_rows(
        unified_rows=unified_scenario_result_rows_from_directory(suite_dir),
        beta_chi_robustness_rows=_read_csv(
            files,
            "ratewall_tdcsim_cbo_model_scenario_beta_chi_robustness.csv",
        ),
    )


def beta_chi_claim_gate_rows(
    *,
    unified_rows: Iterable[Mapping[str, str]],
    beta_chi_robustness_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Classify scenario claims after recomputing beta-chi over moving D."""

    unified_by_key = _by_key(unified_rows, "unified")
    robustness = list(beta_chi_robustness_rows)
    robustness_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in robustness:
        robustness_by_key.setdefault(
            (row["scenario_id"], row["fiscal_year"]),
            [],
        ).append(dict(row))
    baseline_by_year = _baseline_grid_by_year(robustness)
    out = []
    for key, unified in sorted(unified_by_key.items(), key=lambda item: item[0]):
        rows = robustness_by_key.get(key)
        if not rows:
            raise BetaChiAssumptionDisciplineError(
                f"missing beta-chi robustness rows for {key}"
            )
        grid = [
            _moving_delta_row(
                row,
                unified=unified,
                baseline_grid=baseline_by_year[row["fiscal_year"]],
                baseline_unified=unified_by_key[
                    (row["baseline_scenario_id"], row["fiscal_year"])
                ],
            )
            for row in rows
        ]
        out.append(_claim_gate_row(unified, grid))
    return sorted(out, key=lambda row: (int(row["fiscal_year"]), row["scenario_id"]))


def write_beta_chi_claim_gate_outputs(
    output_dir: str | Path,
    *,
    rows: Sequence[Mapping[str, str]],
    threshold_rows: Sequence[Mapping[str, str]] = (),
    evidence_target_rows: Sequence[Mapping[str, str]] = (),
    source_context_rows: Sequence[Mapping[str, str]] = (),
    source_review_rows: Sequence[Mapping[str, str]] = (),
    external_evidence_rows: Sequence[Mapping[str, str]] = (),
    external_floor_review_rows: Sequence[Mapping[str, str]] = (),
    chi_bridge_candidate_rows: Sequence[Mapping[str, str]] = (),
    chi_bridge_target_review_rows: Sequence[Mapping[str, str]] = (),
    chi_mapping_sensitivity_rows: Sequence[Mapping[str, str]] = (),
) -> dict[str, Path]:
    """Write beta-chi claim-gate CSV and a short model memo."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": out / "ratewall_beta_chi_claim_gate.csv",
        "threshold_csv": out / "ratewall_beta_chi_robustness_thresholds.csv",
        "evidence_target_csv": out / "ratewall_beta_chi_evidence_targets.csv",
        "source_context_csv": out / "ratewall_beta_chi_source_context.csv",
        "source_review_csv": out / "ratewall_beta_chi_source_review.csv",
        "external_evidence_csv": out / "ratewall_beta_chi_external_evidence.csv",
        "external_floor_review_csv": (
            out / "ratewall_beta_chi_external_floor_review.csv"
        ),
        "chi_bridge_candidate_csv": (
            out / "ratewall_beta_chi_chi_bridge_candidates.csv"
        ),
        "chi_bridge_target_review_csv": (
            out / "ratewall_beta_chi_chi_bridge_target_review.csv"
        ),
        "chi_mapping_sensitivity_csv": (
            out / "ratewall_beta_chi_chi_mapping_sensitivity.csv"
        ),
        "memo_md": out / "beta_chi_claim_gate_memo.md",
    }
    _write_csv(paths["csv"], rows)
    if threshold_rows:
        _write_threshold_csv(paths["threshold_csv"], threshold_rows)
    if evidence_target_rows:
        _write_evidence_target_csv(
            paths["evidence_target_csv"],
            evidence_target_rows,
        )
    if source_context_rows:
        _write_source_context_csv(paths["source_context_csv"], source_context_rows)
    if source_review_rows:
        _write_source_review_csv(paths["source_review_csv"], source_review_rows)
    if external_evidence_rows:
        _write_external_evidence_csv(
            paths["external_evidence_csv"],
            external_evidence_rows,
        )
    if external_floor_review_rows:
        _write_external_floor_review_csv(
            paths["external_floor_review_csv"],
            external_floor_review_rows,
        )
    if chi_bridge_candidate_rows:
        _write_chi_bridge_candidate_csv(
            paths["chi_bridge_candidate_csv"],
            chi_bridge_candidate_rows,
        )
    if chi_bridge_target_review_rows:
        _write_chi_bridge_target_review_csv(
            paths["chi_bridge_target_review_csv"],
            chi_bridge_target_review_rows,
        )
    if chi_mapping_sensitivity_rows:
        _write_chi_mapping_sensitivity_csv(
            paths["chi_mapping_sensitivity_csv"],
            chi_mapping_sensitivity_rows,
        )
    paths["memo_md"].write_text(
        beta_chi_claim_gate_memo_markdown(
            rows,
            threshold_rows=threshold_rows,
            evidence_target_rows=evidence_target_rows,
            source_review_rows=source_review_rows,
            external_floor_review_rows=external_floor_review_rows,
            chi_bridge_target_review_rows=chi_bridge_target_review_rows,
            chi_mapping_sensitivity_rows=chi_mapping_sensitivity_rows,
        ),
        encoding="utf-8",
    )
    return paths


def beta_chi_claim_gate_memo_markdown(
    rows: Sequence[Mapping[str, str]],
    *,
    threshold_rows: Sequence[Mapping[str, str]] = (),
    evidence_target_rows: Sequence[Mapping[str, str]] = (),
    source_review_rows: Sequence[Mapping[str, str]] = (),
    external_floor_review_rows: Sequence[Mapping[str, str]] = (),
    chi_bridge_target_review_rows: Sequence[Mapping[str, str]] = (),
    chi_mapping_sensitivity_rows: Sequence[Mapping[str, str]] = (),
) -> str:
    """Return a concise memo for the beta-chi claim gate."""

    stable = [
        row
        for row in rows
        if row["claim_strength_status"] == "sign_robust_over_existing_beta_chi_grid"
    ]
    point_only = [
        row
        for row in rows
        if row["claim_strength_status"] == "point_calibrated_assumption_only"
    ]
    blocked_narrowing = [
        row
        for row in rows
        if row["narrower_range_admission_status"].startswith("blocked")
    ]
    largest_point_only = sorted(
        point_only,
        key=lambda row: abs(
            _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
        ),
        reverse=True,
    )[:6]
    lines = [
        "# Beta-Chi Claim Gate Memo",
        "",
        "## Bottom Line",
        "",
        (
            "The current evidence does not justify narrowing the beta-chi range. "
            "Large holder/TDC and combined scenario claims should therefore be "
            "carried as explicit point-calibrated assumptions, not as robust sign claims."
        ),
        "",
        f"- Sign-robust rows over the existing grid: `{len(stable)}`.",
        f"- Point-calibrated-only rows: `{len(point_only)}`.",
        f"- Rows where range narrowing is blocked: `{len(blocked_narrowing)}`.",
        "",
        "## Largest Point-Calibrated Rows",
        "",
    ]
    for row in largest_point_only:
        lines.append(
            "- "
            f"`{row['scenario_id']}`: delta RW "
            f"`{row['selected_moving_delta_ratewall_ratio_vs_baseline']}`, "
            f"signs `{row['grid_signs_observed']}`, zero crossing "
            f"`{row['zero_crossing_beta_times_chi_moving_d']}`."
        )
    if threshold_rows:
        largest_thresholds = sorted(
            threshold_rows,
            key=lambda row: abs(
                _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
            ),
            reverse=True,
        )[:6]
        lines.extend(["", "## What Would Make These Sign-Robust?", ""])
        for row in largest_thresholds:
            lines.append(
                "- "
                f"`{row['scenario_id']}` needs chi floor "
                f"`{row['required_chi_floor_at_existing_min_beta']}` at the "
                f"existing low beta, or beta floor "
                f"`{row['required_beta_floor_at_existing_min_chi']}` at the "
                "existing low chi."
            )
    if evidence_target_rows:
        by_tier: dict[str, int] = {}
        for row in evidence_target_rows:
            by_tier[row["evidence_distance_tier"]] = (
                by_tier.get(row["evidence_distance_tier"], 0) + 1
            )
        tier_counts = ", ".join(
            f"{tier} `{count}`" for tier, count in sorted(by_tier.items())
        )
        priority_rows = [
            row
            for row in evidence_target_rows
            if row["current_model_action"] == "prioritize_for_source_evidence_review"
        ]
        lines.extend(["", "## Evidence Targets", ""])
        lines.append(f"- Evidence-distance tiers: {tier_counts}.")
        lines.append(
            "- Priority source-evidence review rows: "
            f"`{len(priority_rows)}`."
        )
    if source_review_rows:
        admitted = [
            row
            for row in source_review_rows
            if row["admission_status"] != "not_admitted_no_source_floor"
        ]
        near_blocked = [
            row
            for row in source_review_rows
            if row["evidence_distance_tier"] == "near_existing_floor"
            and row["admission_status"] == "not_admitted_no_source_floor"
        ]
        lines.extend(["", "## Source Review", ""])
        lines.append(
            "- Local source review admitted beta/chi floor rows: "
            f"`{len(admitted)}`."
        )
        lines.append(
            "- Near-floor rows still blocked by missing source floor: "
            f"`{len(near_blocked)}`."
        )
    if external_floor_review_rows:
        screen_rows = [
            row
            for row in external_floor_review_rows
            if row["external_floor_review_result"]
            == "external_screen_candidates_clear_floor_but_none_admitted"
        ]
        admitted_rows = [
            row
            for row in external_floor_review_rows
            if row["external_floor_review_result"]
            == "external_admitted_floor_candidate_present"
        ]
        lines.extend(["", "## External Evidence Screen", ""])
        lines.append(
            "- Rows with numeric external screen candidates clearing the floor: "
            f"`{len(screen_rows)}`."
        )
        lines.append(
            "- Rows admitted from external/direct floor evidence: "
            f"`{len(admitted_rows)}`."
        )
    if chi_bridge_target_review_rows:
        feasible = [
            row
            for row in chi_bridge_target_review_rows
            if row["candidate_can_clear_floor_before_mapping_haircut"] == "true"
        ]
        admitted_bridge = [
            row
            for row in chi_bridge_target_review_rows
            if row["bridge_review_result"] == "admitted_chi_floor_after_bridge"
        ]
        minimum_mapping_share = min(
            (
                _decimal(row["required_mapping_share_of_best_candidate"])
                for row in feasible
            ),
            default=Decimal("0"),
        )
        lines.extend(["", "## Chi Bridge Review", ""])
        lines.append(
            "- Rows where an empirical chi candidate can clear the needed floor "
            f"before mapping haircut: `{len(feasible)}`."
        )
        lines.append(
            "- Smallest required mapping share among feasible rows: "
            f"`{_fmt(minimum_mapping_share)}`."
        )
        lines.append(
            "- Rows admitted after a RateWall-specific bridge: "
            f"`{len(admitted_bridge)}`."
        )
    if chi_mapping_sensitivity_rows:
        by_profile: dict[str, int] = {}
        for row in chi_mapping_sensitivity_rows:
            if row["clears_required_chi_floor"] != "true":
                continue
            profile = row["mapping_share_profile"]
            by_profile[profile] = by_profile.get(profile, 0) + 1
        clear_counts = ", ".join(
            f"{profile} `{count}`" for profile, count in sorted(by_profile.items())
        )
        lines.extend(["", "## Chi Mapping Sensitivity", ""])
        lines.append(
            "- Target rows cleared by mapping-share profile: "
            f"{clear_counts or '`0`'}."
        )
        lines.append(
            "- Mapping sensitivity rows admitted as new chi floors: `0`."
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Stable rows can support sign-robust scenario statements within the existing beta-chi grid.",
            "- Mixed-sign rows can be shown as point-calibrated scenario results only.",
            "- A narrower beta-chi range is not admitted here because this pass adds no new evidence for narrowing.",
            "- No row is promoted into the canonical headline result.",
        ]
    )
    return "\n".join(lines) + "\n"


def beta_chi_robustness_threshold_rows(
    claim_gate_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Quantify what beta or chi floor would make mixed-sign rows robust."""

    out = []
    for row in claim_gate_rows:
        if row["claim_strength_status"] != "point_calibrated_assumption_only":
            continue
        if row["zero_crossing_status_moving_d"] != "inside_existing_grid":
            continue
        point_sign = _sign(
            _decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])
        )
        if point_sign != "positive":
            continue
        crossing = _decimal(row["zero_crossing_beta_times_chi_moving_d"])
        min_beta = _existing_min_beta(row)
        min_chi = _existing_min_chi(row)
        required_chi = crossing / min_beta if min_beta else Decimal("Infinity")
        required_beta = crossing / min_chi if min_chi else Decimal("Infinity")
        current_margin = (
            (_decimal(row["current_beta_times_chi"]) - crossing) / crossing
            if crossing
            else Decimal("Infinity")
        )
        out.append(
            {
                "beta_chi_threshold_row_id": (
                    f"beta_chi_threshold::{row['fiscal_year']}::"
                    f"{row['scenario_id']}"
                ),
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "scenario_axis": row["scenario_axis"],
                "selected_moving_delta_ratewall_ratio_vs_baseline": row[
                    "selected_moving_delta_ratewall_ratio_vs_baseline"
                ],
                "point_sign": point_sign,
                "current_beta": row["current_beta"],
                "current_chi": row["current_chi"],
                "current_beta_times_chi": row["current_beta_times_chi"],
                "existing_grid_min_beta": _fmt(min_beta),
                "existing_grid_min_chi": _fmt(min_chi),
                "zero_crossing_beta_times_chi_moving_d": _fmt(crossing),
                "zero_crossing_status_moving_d": row[
                    "zero_crossing_status_moving_d"
                ],
                "required_chi_floor_at_existing_min_beta": _fmt(required_chi),
                "required_beta_floor_at_existing_min_chi": _fmt(required_beta),
                "current_beta_chi_margin_over_crossing": _fmt(current_margin),
                "existing_floor_gap_status": _floor_gap_status(
                    min_beta=min_beta,
                    min_chi=min_chi,
                    required_beta=required_beta,
                    required_chi=required_chi,
                ),
                "model_improvement_target": (
                    "source_evidence_for_chi_floor_or_beta_floor_above_zero_crossing"
                ),
                "admission_status": (
                    "not_admitted_threshold_diagnostic_only_no_new_evidence"
                ),
                "allowed_use": "model_improvement_target_for_beta_chi_evidence",
                "blocked_use": (
                    "prior_narrowing_without_new_evidence;"
                    "canonical_headline_promotion;evidence_mode_claim;"
                    "posterior_beta_claim;posterior_chi_claim"
                ),
                "claim_boundary": (
                    "threshold_math_only_identifies_required_floor;"
                    "does_not_admit_narrower_beta_chi_range"
                ),
            }
        )
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            -abs(_decimal(row["selected_moving_delta_ratewall_ratio_vs_baseline"])),
            row["scenario_id"],
        ),
    )


def beta_chi_evidence_target_rows(
    threshold_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Rank threshold rows by the product-floor evidence lift they need."""

    out = []
    for row in threshold_rows:
        min_beta = _decimal(row["existing_grid_min_beta"])
        min_chi = _decimal(row["existing_grid_min_chi"])
        existing_min_product = min_beta * min_chi
        required_product = _decimal(row["zero_crossing_beta_times_chi_moving_d"])
        product_lift = (
            (required_product - existing_min_product) / existing_min_product
            if existing_min_product
            else Decimal("Infinity")
        )
        tier = _evidence_distance_tier(product_lift)
        out.append(
            {
                "beta_chi_evidence_target_row_id": (
                    f"beta_chi_evidence_target::{row['fiscal_year']}::"
                    f"{row['scenario_id']}"
                ),
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "scenario_axis": row["scenario_axis"],
                "selected_moving_delta_ratewall_ratio_vs_baseline": row[
                    "selected_moving_delta_ratewall_ratio_vs_baseline"
                ],
                "point_sign": row["point_sign"],
                "current_beta_times_chi": row["current_beta_times_chi"],
                "existing_grid_min_beta_times_chi": _fmt(existing_min_product),
                "required_beta_chi_floor": _fmt(required_product),
                "required_product_lift_over_existing_min": _fmt(product_lift),
                "required_chi_floor_at_existing_min_beta": row[
                    "required_chi_floor_at_existing_min_beta"
                ],
                "required_beta_floor_at_existing_min_chi": row[
                    "required_beta_floor_at_existing_min_chi"
                ],
                "evidence_distance_tier": tier,
                "source_evidence_question": _source_evidence_question(row),
                "current_model_action": _evidence_target_action(tier),
                "admission_status": "not_admitted_no_new_source_evidence",
                "allowed_use": "prioritize_beta_chi_source_evidence_work",
                "blocked_use": (
                    "narrower_beta_chi_range_without_source_evidence;"
                    "canonical_headline_promotion;evidence_mode_claim;"
                    "posterior_beta_claim;posterior_chi_claim"
                ),
                "claim_boundary": (
                    "triage_only_for_model_evidence_work;"
                    "does_not_change_beta_chi_grid_or_scenario_math"
                ),
            }
        )
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            _decimal(row["required_product_lift_over_existing_min"]),
            row["scenario_id"],
        ),
    )


def beta_chi_source_context_rows(
    source_paths: Mapping[str, str | Path] | None = None,
) -> list[dict[str, str]]:
    """Summarize local source context relevant to beta/chi floor evidence."""

    paths = source_paths or DEFAULT_BETA_CHI_SOURCE_CONTEXT_PATHS
    out = []
    for source_context_id, source_path in sorted(paths.items()):
        path = Path(source_path)
        if not path.exists():
            out.append(_missing_source_context_row(source_context_id, path))
            continue
        rows = _read_plain_csv(path)
        source_backed_context = _count_source_backed_context_rows(rows)
        current_demand_eligible = _count_value(rows, "current_demand_eligible", "true")
        deposit_true = _count_value(rows, "deposit_pass_through_scope", "true")
        deposit_unknown = _count_value(
            rows,
            "deposit_pass_through_scope",
            "unknown_or_mixed",
        )
        admitted_beta = _count_value(rows, "admitted_beta_floor", "true")
        admitted_chi = _count_value(rows, "admitted_chi_floor", "true")
        admitted_product = _count_value(rows, "admitted_beta_chi_floor", "true")
        out.append(
            {
                "beta_chi_source_context_row_id": (
                    f"beta_chi_source_context::{source_context_id}"
                ),
                "source_context_id": source_context_id,
                "source_path": path.as_posix(),
                "source_present": "true",
                "source_row_count": str(len(rows)),
                "latest_quarter": _latest_quarter(rows),
                "source_backed_context_rows": str(source_backed_context),
                "current_demand_eligible_rows": str(current_demand_eligible),
                "deposit_pass_through_true_rows": str(deposit_true),
                "deposit_pass_through_unknown_rows": str(deposit_unknown),
                "admitted_beta_floor_rows": str(admitted_beta),
                "admitted_chi_floor_rows": str(admitted_chi),
                "admitted_beta_chi_floor_rows": str(admitted_product),
                "source_review_status": _source_context_status(
                    row_count=len(rows),
                    admitted_beta=admitted_beta,
                    admitted_chi=admitted_chi,
                    admitted_product=admitted_product,
                ),
                "allowed_use": "local_source_context_for_beta_chi_floor_review",
                "blocked_use": (
                    "automatic_beta_chi_prior_narrowing;"
                    "canonical_headline_promotion;evidence_mode_claim"
                ),
                "claim_boundary": (
                    "source_context_count_only_not_floor_admission;"
                    "does_not_change_beta_chi_grid"
                ),
            }
        )
    return out


def beta_chi_source_review_rows(
    *,
    evidence_target_rows: Iterable[Mapping[str, str]],
    source_context_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Join evidence targets to local source context and fail closed."""

    context = list(source_context_rows)
    local_source_rows = sum(_int(row["source_row_count"]) for row in context)
    current_demand_rows = sum(
        _int(row["current_demand_eligible_rows"]) for row in context
    )
    admitted_beta = sum(_int(row["admitted_beta_floor_rows"]) for row in context)
    admitted_chi = sum(_int(row["admitted_chi_floor_rows"]) for row in context)
    admitted_product = sum(
        _int(row["admitted_beta_chi_floor_rows"]) for row in context
    )
    out = []
    for row in evidence_target_rows:
        result, action, admission = _source_review_decision(
            row,
            admitted_beta=admitted_beta,
            admitted_chi=admitted_chi,
            admitted_product=admitted_product,
        )
        out.append(
            {
                "beta_chi_source_review_row_id": (
                    f"beta_chi_source_review::{row['fiscal_year']}::"
                    f"{row['scenario_id']}"
                ),
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "scenario_axis": row["scenario_axis"],
                "selected_moving_delta_ratewall_ratio_vs_baseline": row[
                    "selected_moving_delta_ratewall_ratio_vs_baseline"
                ],
                "evidence_distance_tier": row["evidence_distance_tier"],
                "required_beta_chi_floor": row["required_beta_chi_floor"],
                "required_product_lift_over_existing_min": row[
                    "required_product_lift_over_existing_min"
                ],
                "local_source_context_count": str(len(context)),
                "local_source_rows_scanned": str(local_source_rows),
                "local_current_demand_eligible_rows": str(current_demand_rows),
                "local_admitted_beta_floor_rows": str(admitted_beta),
                "local_admitted_chi_floor_rows": str(admitted_chi),
                "local_admitted_beta_chi_floor_rows": str(admitted_product),
                "source_review_result": result,
                "post_review_model_action": action,
                "admission_status": admission,
                "allowed_use": "local_source_review_for_beta_chi_evidence_targets",
                "blocked_use": (
                    "narrower_beta_chi_range_without_source_floor;"
                    "canonical_headline_promotion;evidence_mode_claim;"
                    "posterior_beta_claim;posterior_chi_claim"
                ),
                "claim_boundary": (
                    "review_of_existing_local_sources_only;"
                    "does_not_change_beta_chi_grid_or_scenario_math"
                ),
            }
        )
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            _evidence_tier_sort_key(row["evidence_distance_tier"]),
            _decimal(row["required_product_lift_over_existing_min"]),
            row["scenario_id"],
        ),
    )


def beta_chi_external_evidence_rows() -> list[dict[str, str]]:
    """Return reviewed external/direct beta or chi floor candidates."""

    raw_rows = [
        {
            "evidence_id": "ea_tdc_normal_forward_beta_lower95",
            "evidence_family": "tdc_materialization_beta",
            "candidate_floor_object": "beta",
            "candidate_floor_value": "0.11550407481239519",
            "source_title": "EA-TDC normal-forward pass-through lower 95% bound",
            "source_locator": "../ea-tdc/outputs/tables/ea_tdc_pass_through_ratewall_import_contract.csv",
            "source_value_label": "pass_through_lower95",
            "source_directness": "direct_beta_estimate_already_in_ratewall_grid",
            "numeric_screen_status": "direct_beta_floor_below_near_floor_requirement",
            "admission_status": "already_in_grid_not_new_external_floor",
        },
        {
            "evidence_id": "aer_cash_like_transfer_mpc_2025",
            "evidence_family": "consumption_response",
            "candidate_floor_object": "chi",
            "candidate_floor_value": "0.23",
            "source_title": (
                "Five Facts about MPCs: Evidence from a Randomized Experiment"
            ),
            "source_locator": (
                "https://www.aeaweb.org/articles?id=10.1257/aer.20240138"
            ),
            "source_value_label": "cash_like_transfer_mpc",
            "source_directness": (
                "cash_like_transfer_mpc_closer_than_wealth_mpc_but_not_treasury_tdc_chi"
            ),
            "numeric_screen_status": "numeric_chi_screen_candidate",
            "admission_status": "screen_only_not_direct_chi_floor",
        },
        {
            "evidence_id": "feds_wealth_heterogeneity_mpc_2025",
            "evidence_family": "consumption_response",
            "candidate_floor_object": "chi",
            "candidate_floor_value": "0.035",
            "source_title": "FEDS Notes: Wealth Heterogeneity and Consumer Spending",
            "source_locator": "https://www.federalreserve.gov/econres/notes/feds-notes/wealth-heterogeneity-and-consumer-spending-20250805.html",
            "source_value_label": "aggregate_wealth_mpc",
            "source_directness": "contextual_wealth_mpc_not_treasury_tdc_chi",
            "numeric_screen_status": "numeric_chi_screen_candidate",
            "admission_status": "screen_only_not_direct_chi_floor",
        },
        {
            "evidence_id": "boston_fed_psid_mpc_2019",
            "evidence_family": "consumption_response",
            "candidate_floor_object": "chi",
            "candidate_floor_value": "0.10",
            "source_title": "Boston Fed working paper on PSID wealth and consumption MPC",
            "source_locator": "https://www.bostonfed.org/publications/research-department-working-paper/2019/housing-wealth-and-consumption-the-role-of-heterogeneous-credit-constraints.aspx",
            "source_value_label": "overall_mpc",
            "source_directness": "contextual_wealth_mpc_not_treasury_tdc_chi",
            "numeric_screen_status": "numeric_chi_screen_candidate",
            "admission_status": "screen_only_not_direct_chi_floor",
        },
        {
            "evidence_id": "hank_one_asset_mpc",
            "evidence_family": "consumption_response",
            "candidate_floor_object": "chi",
            "candidate_floor_value": "0.027",
            "source_title": "Heterogeneous Agent New Keynesian model MPC comparison",
            "source_locator": "https://www.nber.org/papers/w21897",
            "source_value_label": "one_asset_aggregate_mpc",
            "source_directness": "model_mpc_not_treasury_tdc_chi",
            "numeric_screen_status": "numeric_chi_screen_below_near_floor",
            "admission_status": "screen_only_not_direct_chi_floor",
        },
        {
            "evidence_id": "hank_two_asset_mpc",
            "evidence_family": "consumption_response",
            "candidate_floor_object": "chi",
            "candidate_floor_value": "0.131",
            "source_title": "Heterogeneous Agent New Keynesian model MPC comparison",
            "source_locator": "https://www.nber.org/papers/w21897",
            "source_value_label": "two_asset_aggregate_mpc",
            "source_directness": "model_mpc_not_treasury_tdc_chi",
            "numeric_screen_status": "numeric_chi_screen_candidate",
            "admission_status": "screen_only_not_direct_chi_floor",
        },
    ]
    return [
        {
            "beta_chi_external_evidence_row_id": (
                f"beta_chi_external_evidence::{row['evidence_id']}"
            ),
            **row,
            "allowed_use": "external_numeric_screen_for_beta_chi_floor_review",
            "blocked_use": (
                "automatic_beta_chi_prior_narrowing;"
                "canonical_headline_promotion;evidence_mode_claim;"
                "direct_chi_floor_admission_without_mapping"
            ),
            "claim_boundary": (
                "external_screen_only_until_source_directness_and_mapping_pass;"
                "does_not_change_beta_chi_grid"
            ),
        }
        for row in raw_rows
    ]


def beta_chi_external_floor_review_rows(
    *,
    evidence_target_rows: Iterable[Mapping[str, str]],
    external_evidence_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Compare external candidate values with each target's required floor."""

    evidence = list(external_evidence_rows)
    out = []
    for target in evidence_target_rows:
        required_beta = _decimal(target["required_beta_floor_at_existing_min_chi"])
        required_chi = _decimal(target["required_chi_floor_at_existing_min_beta"])
        beta_candidates = [
            row
            for row in evidence
            if row["candidate_floor_object"] == "beta"
            and _decimal(row["candidate_floor_value"]) >= required_beta
        ]
        chi_candidates = [
            row
            for row in evidence
            if row["candidate_floor_object"] == "chi"
            and _decimal(row["candidate_floor_value"]) >= required_chi
        ]
        admitted_beta = [
            row
            for row in beta_candidates
            if row["admission_status"].startswith("admitted")
        ]
        admitted_chi = [
            row
            for row in chi_candidates
            if row["admission_status"].startswith("admitted")
        ]
        result, action, admission = _external_floor_review_decision(
            beta_candidates=beta_candidates,
            chi_candidates=chi_candidates,
            admitted_beta=admitted_beta,
            admitted_chi=admitted_chi,
        )
        out.append(
            {
                "beta_chi_external_floor_review_row_id": (
                    f"beta_chi_external_floor_review::{target['fiscal_year']}::"
                    f"{target['scenario_id']}"
                ),
                "fiscal_year": target["fiscal_year"],
                "scenario_id": target["scenario_id"],
                "scenario_axis": target["scenario_axis"],
                "evidence_distance_tier": target["evidence_distance_tier"],
                "required_chi_floor_at_existing_min_beta": target[
                    "required_chi_floor_at_existing_min_beta"
                ],
                "required_beta_floor_at_existing_min_chi": target[
                    "required_beta_floor_at_existing_min_chi"
                ],
                "external_beta_candidates_clearing_floor": str(len(beta_candidates)),
                "external_chi_candidates_clearing_floor": str(len(chi_candidates)),
                "external_admitted_beta_floor_rows": str(len(admitted_beta)),
                "external_admitted_chi_floor_rows": str(len(admitted_chi)),
                "best_numeric_chi_candidate": _best_candidate_id(chi_candidates),
                "best_numeric_beta_candidate": _best_candidate_id(beta_candidates),
                "external_floor_review_result": result,
                "post_review_model_action": action,
                "admission_status": admission,
                "allowed_use": "external_floor_screen_for_beta_chi_targets",
                "blocked_use": (
                    "narrower_beta_chi_range_without_direct_mapping;"
                    "canonical_headline_promotion;evidence_mode_claim;"
                    "posterior_beta_claim;posterior_chi_claim"
                ),
                "claim_boundary": (
                    "external_screen_only_not_floor_admission;"
                    "does_not_change_beta_chi_grid_or_scenario_math"
                ),
            }
        )
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            _evidence_tier_sort_key(row["evidence_distance_tier"]),
            _decimal(row["required_chi_floor_at_existing_min_beta"]),
            row["scenario_id"],
        ),
    )


def beta_chi_chi_bridge_candidate_rows(
    external_evidence_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return chi bridge candidates, without admitting them as chi floors."""

    out = []
    for row in external_evidence_rows:
        if row["candidate_floor_object"] != "chi":
            continue
        out.append(
            {
                "beta_chi_chi_bridge_candidate_row_id": (
                    f"beta_chi_chi_bridge_candidate::{row['evidence_id']}"
                ),
                "bridge_candidate_id": row["evidence_id"],
                "evidence_family": row["evidence_family"],
                "candidate_chi_value": row["candidate_floor_value"],
                "source_title": row["source_title"],
                "source_locator": row["source_locator"],
                "source_value_label": row["source_value_label"],
                "economic_object": _chi_bridge_economic_object(row),
                "mapping_to_ratewall_chi": _chi_bridge_mapping_statement(row),
                "directness_tier": _chi_bridge_directness_tier(row),
                "empirical_status": "external_empirical_or_model_context",
                "admission_status": "not_admitted_requires_ratewall_specific_bridge",
                "allowed_use": "chi_bridge_feasibility_screen_for_beta_chi_targets",
                "blocked_use": (
                    "automatic_chi_floor_admission;beta_chi_prior_narrowing;"
                    "canonical_headline_promotion;evidence_mode_claim;"
                    "posterior_chi_claim"
                ),
                "claim_boundary": (
                    "bridge_candidate_only;does_not_change_chi_grid_or_scenario_math"
                ),
            }
        )
    return sorted(
        out,
        key=lambda row: (
            -_decimal(row["candidate_chi_value"]),
            row["bridge_candidate_id"],
        ),
    )


def beta_chi_chi_bridge_target_review_rows(
    *,
    evidence_target_rows: Iterable[Mapping[str, str]],
    chi_bridge_candidate_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Quantify how much bridge mapping would be needed for each chi target."""

    candidates = sorted(
        list(chi_bridge_candidate_rows),
        key=lambda row: _decimal(row["candidate_chi_value"]),
        reverse=True,
    )
    best = candidates[0] if candidates else None
    out = []
    for target in evidence_target_rows:
        required_chi = _decimal(target["required_chi_floor_at_existing_min_beta"])
        candidate_value = (
            _decimal(best["candidate_chi_value"]) if best is not None else Decimal("0")
        )
        required_mapping_share = (
            required_chi / candidate_value if candidate_value else Decimal("Infinity")
        )
        candidate_clears = best is not None and required_mapping_share <= 1
        result, action, admission = _chi_bridge_review_decision(
            candidate_clears=candidate_clears,
        )
        out.append(
            {
                "beta_chi_chi_bridge_target_review_row_id": (
                    f"beta_chi_chi_bridge_target_review::{target['fiscal_year']}::"
                    f"{target['scenario_id']}"
                ),
                "fiscal_year": target["fiscal_year"],
                "scenario_id": target["scenario_id"],
                "scenario_axis": target["scenario_axis"],
                "evidence_distance_tier": target["evidence_distance_tier"],
                "required_chi_floor_at_existing_min_beta": target[
                    "required_chi_floor_at_existing_min_beta"
                ],
                "best_bridge_candidate_id": (
                    best["bridge_candidate_id"] if best is not None else ""
                ),
                "best_bridge_candidate_chi_value": _fmt(candidate_value),
                "required_mapping_share_of_best_candidate": _fmt(
                    required_mapping_share
                ),
                "mapping_share_feasibility_tier": _mapping_share_feasibility_tier(
                    required_mapping_share,
                ),
                "candidate_can_clear_floor_before_mapping_haircut": str(
                    candidate_clears
                ).lower(),
                "admitted_chi_floor_after_bridge_rows": "0",
                "bridge_review_result": result,
                "post_review_model_action": action,
                "admission_status": admission,
                "allowed_use": "chi_bridge_feasibility_review_for_beta_chi_targets",
                "blocked_use": (
                    "narrower_beta_chi_range_without_ratewall_specific_bridge;"
                    "canonical_headline_promotion;evidence_mode_claim;"
                    "posterior_chi_claim"
                ),
                "claim_boundary": (
                    "bridge_feasibility_only_not_chi_floor_admission;"
                    "does_not_change_beta_chi_grid_or_scenario_math"
                ),
            }
        )
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            _decimal(row["required_mapping_share_of_best_candidate"]),
            row["scenario_id"],
        ),
    )


def beta_chi_chi_mapping_sensitivity_rows(
    *,
    evidence_target_rows: Iterable[Mapping[str, str]],
    chi_bridge_candidate_rows: Iterable[Mapping[str, str]],
    mapping_share_profiles: Sequence[tuple[str, Decimal]]
    = DEFAULT_CHI_BRIDGE_MAPPING_SHARE_PROFILES,
) -> list[dict[str, str]]:
    """Apply explicit mapping-share assumptions to the best chi candidate."""

    candidates = sorted(
        list(chi_bridge_candidate_rows),
        key=lambda row: _decimal(row["candidate_chi_value"]),
        reverse=True,
    )
    if not candidates:
        return []
    best = candidates[0]
    candidate_chi = _decimal(best["candidate_chi_value"])
    out = []
    for target in evidence_target_rows:
        required_chi = _decimal(target["required_chi_floor_at_existing_min_beta"])
        existing_min_chi = _decimal(target.get("existing_grid_min_chi", "0.03"))
        for profile_name, mapping_share in mapping_share_profiles:
            implied_chi = candidate_chi * mapping_share
            clears_floor = implied_chi >= required_chi
            out.append(
                {
                    "beta_chi_chi_mapping_sensitivity_row_id": (
                        "beta_chi_chi_mapping_sensitivity::"
                        f"{target['fiscal_year']}::{target['scenario_id']}::"
                        f"{profile_name}"
                    ),
                    "fiscal_year": target["fiscal_year"],
                    "scenario_id": target["scenario_id"],
                    "scenario_axis": target["scenario_axis"],
                    "evidence_distance_tier": target["evidence_distance_tier"],
                    "bridge_candidate_id": best["bridge_candidate_id"],
                    "candidate_chi_value": _fmt(candidate_chi),
                    "mapping_share_profile": profile_name,
                    "mapping_share": _fmt(mapping_share),
                    "implied_chi_floor": _fmt(implied_chi),
                    "existing_grid_min_chi": _fmt(existing_min_chi),
                    "required_chi_floor_at_existing_min_beta": _fmt(required_chi),
                    "clears_required_chi_floor": str(clears_floor).lower(),
                    "mapping_result": (
                        "would_clear_required_chi_floor"
                        if clears_floor
                        else "does_not_clear_required_chi_floor"
                    ),
                    "post_mapping_model_use": (
                        "sign_robust_if_mapping_share_admitted"
                        if clears_floor
                        else "point_calibrated_under_mapping_share"
                    ),
                    "admission_status": (
                        "not_admitted_mapping_sensitivity_only_no_chi_floor_change"
                    ),
                    "allowed_use": (
                        "scenario_interpretation_under_explicit_chi_mapping_share"
                    ),
                    "blocked_use": (
                        "automatic_chi_floor_admission;beta_chi_prior_narrowing;"
                        "canonical_headline_promotion;evidence_mode_claim;"
                        "posterior_chi_claim"
                    ),
                    "claim_boundary": (
                        "mapping_share_sensitivity_only;"
                        "does_not_change_beta_chi_grid_or_scenario_math"
                    ),
                }
            )
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            row["scenario_id"],
            _decimal(row["mapping_share"]),
        ),
    )


def _suite_files(suite_dir: str | Path) -> _SuiteFiles:
    root = Path(suite_dir)
    artifact = ArtifactManifestView.from_root(root) if artifact_manifest_exists(root) else None
    return _SuiteFiles(root=root, artifact=artifact)


def _read_csv(files: _SuiteFiles, logical_path: str) -> list[dict[str, str]]:
    if files.artifact is not None:
        if not files.artifact.has_file(logical_path):
            raise BetaChiAssumptionDisciplineError(
                f"missing required suite CSV: {logical_path}"
            )
        with files.artifact.open_text(logical_path) as handle:
            return list(csv.DictReader(handle))
    path = files.root / logical_path
    if not path.exists():
        raise BetaChiAssumptionDisciplineError(
            f"missing required suite CSV: {path}"
        )
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_plain_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _moving_delta_row(
    row: Mapping[str, str],
    *,
    unified: Mapping[str, str],
    baseline_grid: Mapping[tuple[str, str], Mapping[str, str]],
    baseline_unified: Mapping[str, str],
) -> dict[str, Decimal | str]:
    profile = (
        row["tdc_materialization_beta_scenario"],
        row["deposit_current_demand_share_profile"],
    )
    baseline = baseline_grid.get(profile)
    if baseline is None:
        raise BetaChiAssumptionDisciplineError(
            f"missing baseline beta-chi profile {profile}"
        )
    scenario_denominator = _decimal(unified["selected_moving_denominator_bil"])
    baseline_denominator = _decimal(
        baseline_unified["selected_moving_denominator_bil"]
    )
    scenario_support = _decimal(row["total_current_demand_support_bil_recomputed"])
    baseline_support = _decimal(
        baseline["total_current_demand_support_bil_recomputed"]
    )
    delta = scenario_support / scenario_denominator - baseline_support / baseline_denominator
    return {
        "scenario_id": row["scenario_id"],
        "fiscal_year": row["fiscal_year"],
        "beta_label": row["tdc_materialization_beta_scenario"],
        "chi_label": row["deposit_current_demand_share_profile"],
        "beta": _decimal(row["tdc_materialization_beta"]),
        "chi": _decimal(row["deposit_current_demand_share"]),
        "beta_chi": _decimal(row["derived_beta_times_chi"]),
        "is_current": row["profile_is_current_point_calibration"],
        "delta": delta,
        "sign": _sign(delta),
        "tdc_change": _decimal(row["tdc_change_ex_overlap_bil"]),
        "baseline_tdc_change": _decimal(
            baseline["tdc_change_ex_overlap_bil"]
        ),
        "direct": _decimal(
            row["direct_treasury_current_demand_support_bil_fixed"]
        ),
        "baseline_direct": _decimal(
            baseline["direct_treasury_current_demand_support_bil_fixed"]
        ),
        "bank": _decimal(row["bank_treasury_current_demand_support_bil_fixed"]),
        "baseline_bank": _decimal(
            baseline["bank_treasury_current_demand_support_bil_fixed"]
        ),
        "scenario_denominator": scenario_denominator,
        "baseline_denominator": baseline_denominator,
    }


def _claim_gate_row(
    unified: Mapping[str, str],
    grid: Sequence[Mapping[str, Decimal | str]],
) -> dict[str, str]:
    current_rows = [row for row in grid if row["is_current"] == "true"]
    if len(current_rows) != 1:
        raise BetaChiAssumptionDisciplineError(
            f"expected one current beta-chi row for {unified['scenario_id']}"
        )
    current = current_rows[0]
    deltas = [_as_decimal(row["delta"]) for row in grid]
    signs = sorted({_as_str(row["sign"]) for row in grid})
    point_sign = _sign(
        _decimal(unified["selected_moving_delta_ratewall_ratio_vs_baseline"])
    )
    same_sign_count = sum(1 for row in grid if row["sign"] == point_sign)
    min_beta = min(_as_decimal(row["beta"]) for row in grid)
    min_chi = min(_as_decimal(row["chi"]) for row in grid)
    crossing, crossing_status = _moving_zero_crossing(grid)
    stability = _sign_stability(signs)
    return {
        "beta_chi_claim_gate_row_id": (
            f"beta_chi_claim_gate::{unified['fiscal_year']}::"
            f"{unified['scenario_id']}"
        ),
        "fiscal_year": unified["fiscal_year"],
        "scenario_id": unified["scenario_id"],
        "scenario_axis": unified["scenario_axis"],
        "current_beta": _fmt(_as_decimal(current["beta"])),
        "current_chi": _fmt(_as_decimal(current["chi"])),
        "current_beta_times_chi": _fmt(_as_decimal(current["beta_chi"])),
        "existing_grid_min_beta": _fmt(min_beta),
        "existing_grid_min_chi": _fmt(min_chi),
        "selected_moving_delta_ratewall_ratio_vs_baseline": unified[
            "selected_moving_delta_ratewall_ratio_vs_baseline"
        ],
        "grid_min_moving_delta_ratewall_ratio": _fmt(min(deltas)),
        "grid_max_moving_delta_ratewall_ratio": _fmt(max(deltas)),
        "grid_signs_observed": ";".join(signs),
        "grid_same_sign_cell_count": str(same_sign_count),
        "grid_cell_count": str(len(grid)),
        "moving_d_beta_chi_sign_stability_status": stability,
        "zero_crossing_beta_times_chi_moving_d": _fmt(crossing),
        "zero_crossing_status_moving_d": crossing_status,
        "narrower_range_admission_status": _narrower_range_status(
            stability,
            crossing_status,
        ),
        "claim_strength_status": _claim_strength(unified, stability),
        "final_model_use": _final_model_use(unified, stability),
        "canonical_promotion_status": (
            "blocked_scenario_mode_only_without_owner_gate"
        ),
        "allowed_use": "beta_chi_assumption_discipline_for_scenario_claims",
        "blocked_use": (
            "canonical_headline_promotion;posterior_beta_claim;"
            "prior_narrowing_without_new_evidence;evidence_mode_claim;"
            "tdc_beta_without_chi_numerator;denominator_recalibration"
        ),
        "claim_boundary": (
            "moving_D_aware_beta_chi_claim_gate;"
            "does_not_change_numerator_math_or_admit_new_beta_chi_prior"
        ),
    }


def _moving_zero_crossing(
    grid: Sequence[Mapping[str, Decimal | str]],
) -> tuple[Decimal, str]:
    first = grid[0]
    scenario_denominator = _as_decimal(first["scenario_denominator"])
    baseline_denominator = _as_decimal(first["baseline_denominator"])
    slope = (
        _as_decimal(first["tdc_change"]) / scenario_denominator
        - _as_decimal(first["baseline_tdc_change"]) / baseline_denominator
    )
    intercept = (
        (_as_decimal(first["direct"]) + _as_decimal(first["bank"]))
        / scenario_denominator
        - (
            _as_decimal(first["baseline_direct"])
            + _as_decimal(first["baseline_bank"])
        )
        / baseline_denominator
    )
    if slope == 0:
        if intercept == 0:
            return Decimal("0"), "identically_zero"
        return Decimal("0"), "no_beta_chi_slope"
    crossing = -intercept / slope
    values = [_as_decimal(row["beta_chi"]) for row in grid]
    if min(values) <= crossing <= max(values):
        return crossing, "inside_existing_grid"
    return crossing, "outside_existing_grid"


def _baseline_grid_by_year(
    robustness_rows: Sequence[Mapping[str, str]],
) -> dict[str, dict[tuple[str, str], Mapping[str, str]]]:
    out: dict[str, dict[tuple[str, str], Mapping[str, str]]] = {}
    for row in robustness_rows:
        if row["scenario_id"] != row["baseline_scenario_id"]:
            continue
        profile = (
            row["tdc_materialization_beta_scenario"],
            row["deposit_current_demand_share_profile"],
        )
        out.setdefault(row["fiscal_year"], {})[profile] = row
    if not out:
        raise BetaChiAssumptionDisciplineError("missing baseline beta-chi grid")
    return out


def _by_key(
    rows: Iterable[Mapping[str, str]],
    label: str,
) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["scenario_id"], row["fiscal_year"])
        if key in out:
            raise BetaChiAssumptionDisciplineError(
                f"duplicate {label} row for {key}"
            )
        out[key] = dict(row)
    return out


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BETA_CHI_CLAIM_GATE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_threshold_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BETA_CHI_ROBUSTNESS_THRESHOLD_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_evidence_target_csv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BETA_CHI_EVIDENCE_TARGET_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_source_context_csv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BETA_CHI_SOURCE_CONTEXT_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_source_review_csv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BETA_CHI_SOURCE_REVIEW_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_external_evidence_csv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BETA_CHI_EXTERNAL_EVIDENCE_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_external_floor_review_csv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BETA_CHI_EXTERNAL_FLOOR_REVIEW_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_chi_bridge_candidate_csv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BETA_CHI_CHI_BRIDGE_CANDIDATE_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_chi_bridge_target_review_csv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BETA_CHI_CHI_BRIDGE_TARGET_REVIEW_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_chi_mapping_sensitivity_csv(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=BETA_CHI_CHI_MAPPING_SENSITIVITY_FIELDS,
        )
        writer.writeheader()
        writer.writerows(rows)


def _existing_min_beta(row: Mapping[str, str]) -> Decimal:
    return _decimal(row["existing_grid_min_beta"])


def _existing_min_chi(row: Mapping[str, str]) -> Decimal:
    return _decimal(row["existing_grid_min_chi"])


def _floor_gap_status(
    *,
    min_beta: Decimal,
    min_chi: Decimal,
    required_beta: Decimal,
    required_chi: Decimal,
) -> str:
    beta_pass = min_beta > required_beta
    chi_pass = min_chi > required_chi
    if beta_pass and chi_pass:
        return "existing_floors_already_above_threshold"
    if beta_pass:
        return "chi_floor_binds"
    if chi_pass:
        return "beta_floor_binds"
    return "both_existing_floors_below_threshold"


def _evidence_distance_tier(product_lift: Decimal) -> str:
    if product_lift <= Decimal("0.05"):
        return "near_existing_floor"
    if product_lift <= Decimal("0.75"):
        return "moderate_product_floor_lift"
    if product_lift <= Decimal("2"):
        return "large_product_floor_lift"
    return "outside_near_term_evidence_target"


def _source_evidence_question(row: Mapping[str, str]) -> str:
    if row["scenario_axis"] == "holder_only":
        return (
            "can_holder_tdc_channel_source_evidence_support_required_"
            "beta_chi_product_floor"
        )
    if row["scenario_axis"] == "combined_holder_rate":
        return (
            "can_combined_holder_rate_case_support_required_beta_chi_"
            "product_floor_after_moving_D"
        )
    return (
        "can_tdc_channel_source_evidence_support_required_beta_chi_product_floor"
    )


def _evidence_target_action(tier: str) -> str:
    if tier == "near_existing_floor":
        return "prioritize_for_source_evidence_review"
    if tier == "moderate_product_floor_lift":
        return "review_after_near_floor_rows"
    return "park_unless_new_direct_evidence"


def _missing_source_context_row(source_context_id: str, path: Path) -> dict[str, str]:
    return {
        "beta_chi_source_context_row_id": (
            f"beta_chi_source_context::{source_context_id}"
        ),
        "source_context_id": source_context_id,
        "source_path": path.as_posix(),
        "source_present": "false",
        "source_row_count": "0",
        "latest_quarter": "",
        "source_backed_context_rows": "0",
        "current_demand_eligible_rows": "0",
        "deposit_pass_through_true_rows": "0",
        "deposit_pass_through_unknown_rows": "0",
        "admitted_beta_floor_rows": "0",
        "admitted_chi_floor_rows": "0",
        "admitted_beta_chi_floor_rows": "0",
        "source_review_status": "missing_source_context",
        "allowed_use": "missing_local_source_context_flag",
        "blocked_use": (
            "automatic_beta_chi_prior_narrowing;"
            "canonical_headline_promotion;evidence_mode_claim"
        ),
        "claim_boundary": (
            "missing_source_context_count_only_not_floor_admission;"
            "does_not_change_beta_chi_grid"
        ),
    }


def _count_source_backed_context_rows(rows: Sequence[Mapping[str, str]]) -> int:
    return sum(
        1
        for row in rows
        if "source_backed" in row.get("source_status", "")
        or "source_available" in row.get("source_status", "")
    )


def _count_value(
    rows: Sequence[Mapping[str, str]],
    field: str,
    value: str,
) -> int:
    return sum(1 for row in rows if row.get(field, "").lower() == value)


def _latest_quarter(rows: Sequence[Mapping[str, str]]) -> str:
    quarters = [row.get("quarter", "") for row in rows if row.get("quarter")]
    if quarters:
        return sorted(quarters)[-1]
    dates = [row.get("date", "") for row in rows if row.get("date")]
    return sorted(dates)[-1] if dates else ""


def _source_context_status(
    *,
    row_count: int,
    admitted_beta: int,
    admitted_chi: int,
    admitted_product: int,
) -> str:
    if row_count == 0:
        return "missing_source_context"
    if admitted_product:
        return "admitted_beta_chi_floor_present"
    if admitted_beta or admitted_chi:
        return "partial_floor_evidence_present"
    return "context_available_no_admitted_beta_chi_floor"


def _source_review_decision(
    row: Mapping[str, str],
    *,
    admitted_beta: int,
    admitted_chi: int,
    admitted_product: int,
) -> tuple[str, str, str]:
    if admitted_product or (admitted_beta and admitted_chi):
        return (
            "local_source_floor_present_needs_formal_admission_review",
            "review_possible_floor_admission_before_reclassifying",
            "pending_formal_floor_admission_review",
        )
    if row["evidence_distance_tier"] == "near_existing_floor":
        return (
            "near_floor_but_no_local_source_floor",
            "keep_point_calibrated_seek_direct_floor_evidence",
            "not_admitted_no_source_floor",
        )
    return (
        "no_local_source_floor_for_required_beta_chi_product",
        "keep_point_calibrated_or_park_until_direct_evidence",
        "not_admitted_no_source_floor",
    )


def _external_floor_review_decision(
    *,
    beta_candidates: Sequence[Mapping[str, str]],
    chi_candidates: Sequence[Mapping[str, str]],
    admitted_beta: Sequence[Mapping[str, str]],
    admitted_chi: Sequence[Mapping[str, str]],
) -> tuple[str, str, str]:
    if admitted_beta or admitted_chi:
        return (
            "external_admitted_floor_candidate_present",
            "review_possible_floor_admission_before_reclassifying",
            "pending_formal_floor_admission_review",
        )
    if beta_candidates or chi_candidates:
        return (
            "external_screen_candidates_clear_floor_but_none_admitted",
            "needs_direct_mapping_or_econometric_bridge_before_reclassifying",
            "not_admitted_external_screen_only",
        )
    return (
        "no_external_candidate_clears_required_floor",
        "keep_point_calibrated_or_seek_new_direct_evidence",
        "not_admitted_no_external_floor_candidate",
    )


def _chi_bridge_economic_object(row: Mapping[str, str]) -> str:
    directness = row["source_directness"]
    if "cash_like_transfer" in directness:
        return "mpc_out_of_cash_like_transfer"
    if "wealth_mpc" in directness:
        return "mpc_out_of_wealth_change"
    if "model_mpc" in directness:
        return "model_implied_aggregate_mpc"
    return "consumption_response_context"


def _chi_bridge_mapping_statement(row: Mapping[str, str]) -> str:
    directness = row["source_directness"]
    if "cash_like_transfer" in directness:
        return (
            "requires_mapping_cash_like_transfer_mpc_to_spending_response_from_"
            "tdc_materialized_deposit_flow"
        )
    if "wealth_mpc" in directness:
        return (
            "requires_mapping_wealth_mpc_to_spending_response_from_tdc_"
            "materialized_deposit_flow"
        )
    if "model_mpc" in directness:
        return (
            "requires_mapping_model_mpc_to_empirical_tdc_deposit_flow_response"
        )
    return "requires_ratewall_specific_chi_mapping"


def _chi_bridge_directness_tier(row: Mapping[str, str]) -> str:
    directness = row["source_directness"]
    if "cash_like_transfer" in directness:
        return "closest_context_cash_like_transfer_not_direct_tdc"
    if "wealth_mpc" in directness:
        return "contextual_wealth_mpc_not_direct_tdc"
    if "model_mpc" in directness:
        return "model_context_not_empirical_tdc"
    return "context_only_not_direct_tdc"


def _mapping_share_feasibility_tier(required_mapping_share: Decimal) -> str:
    if required_mapping_share.is_infinite():
        return "no_numeric_candidate"
    if required_mapping_share <= Decimal("0.25"):
        return "low_mapping_share_needed"
    if required_mapping_share <= Decimal("0.50"):
        return "moderate_mapping_share_needed"
    if required_mapping_share <= Decimal("1"):
        return "large_mapping_share_needed"
    return "candidate_too_small_even_before_mapping_haircut"


def _chi_bridge_review_decision(
    *,
    candidate_clears: bool,
) -> tuple[str, str, str]:
    if candidate_clears:
        return (
            "candidate_clears_floor_before_mapping_but_not_admitted",
            "build_ratewall_specific_mapping_or_keep_point_calibrated",
            "not_admitted_requires_ratewall_specific_bridge",
        )
    return (
        "no_candidate_clears_floor_even_before_mapping",
        "keep_point_calibrated_or_seek_stronger_direct_chi_evidence",
        "not_admitted_no_bridge_candidate",
    )


def _best_candidate_id(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    return max(
        rows,
        key=lambda row: _decimal(row["candidate_floor_value"]),
    )["evidence_id"]


def _evidence_tier_sort_key(tier: str) -> int:
    order = {
        "near_existing_floor": 0,
        "moderate_product_floor_lift": 1,
        "large_product_floor_lift": 2,
        "outside_near_term_evidence_target": 3,
    }
    return order.get(tier, 99)


def _sign_stability(signs: Sequence[str]) -> str:
    nonzero = [sign for sign in signs if sign != "zero"]
    if not nonzero:
        return "zero_baseline"
    if len(set(nonzero)) == 1:
        return f"stable_{nonzero[0]}"
    return "mixed_sign"


def _narrower_range_status(stability: str, crossing_status: str) -> str:
    if stability != "mixed_sign":
        return "not_needed_existing_grid_sign_stable"
    if crossing_status == "inside_existing_grid":
        return "blocked_no_source_for_narrower_range_excluding_zero_crossing"
    return "blocked_mixed_sign_grid_without_new_beta_chi_evidence"


def _claim_strength(row: Mapping[str, str], stability: str) -> str:
    if row["scenario_axis"] == "baseline":
        return "baseline_reference"
    if stability.startswith("stable_"):
        return "sign_robust_over_existing_beta_chi_grid"
    return "point_calibrated_assumption_only"


def _final_model_use(row: Mapping[str, str], stability: str) -> str:
    if row["scenario_axis"] == "baseline":
        return "baseline_reference"
    if stability.startswith("stable_"):
        return "scenario_claim_sign_robust_within_existing_beta_chi_grid"
    if row["scenario_axis"] in {
        "holder_only",
        "combined_holder_rate",
        "rate_or_issuance_rate",
    }:
        return "main_scenario_family_with_explicit_point_calibration_label"
    return "sensitivity_or_check_with_explicit_point_calibration_label"


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BetaChiAssumptionDisciplineError(
            f"invalid decimal value: {value}"
        ) from exc


def _as_decimal(value: Decimal | str) -> Decimal:
    return value if isinstance(value, Decimal) else _decimal(value)


def _as_str(value: Decimal | str) -> str:
    return str(value)


def _sign(value: Decimal) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def _fmt(value: Decimal) -> str:
    if value == value.to_integral():
        return str(value.quantize(Decimal("1")))
    return format(value.normalize(), "f")


def _int(value: str) -> int:
    return int(Decimal(value))
