"""Direct chi / beta-chi evidence screen for RateWall holder scenarios."""

from __future__ import annotations

import csv
import gzip
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ratewall.databook.beta_chi_assumption_discipline import (
    beta_chi_evidence_target_rows,
    beta_chi_robustness_threshold_rows,
)
from ratewall.databook.model_artifact_store import (
    ArtifactManifestView,
    artifact_manifest_exists,
)
from ratewall.databook.unified_scenario_results import DEFAULT_UNIFIED_SUITE_DIR

DEFAULT_TDCEST_DOWNSTREAM_DIR = Path.home() / "malus/proj/tdcest/data/processed"
DEFAULT_TDCSIM_PERIOD_TDC_DIR = (
    Path.home() / "malus/proj/tdcsim/output/ratewall_du_principal_fix_baseline"
)
DEFAULT_LOCAL_CURRENT_DEMAND_DIR = Path("data/raw/current_demand_gdp_share")

DIRECT_CHI_REQUIREMENT_FIELDS = [
    "direct_chi_requirement_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "evidence_distance_tier",
    "required_chi_floor_at_existing_min_beta",
    "required_beta_chi_floor",
    "required_beta_floor_at_existing_min_chi",
    "current_beta_times_chi",
    "selected_moving_delta_ratewall_ratio_vs_baseline",
    "target_estimand",
    "minimum_admissible_evidence",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DIRECT_CHI_SOURCE_FIELDS = [
    "direct_chi_source_row_id",
    "source_family",
    "source_artifact",
    "candidate_role",
    "row_count",
    "has_tdc_ex_overlap_treatment",
    "has_materialized_tdc_treatment",
    "has_current_demand_outcome",
    "has_identification_strategy",
    "reports_chi_lower_bound",
    "reported_chi_lower_bound",
    "reports_beta_chi_lower_bound",
    "reported_beta_chi_lower_bound",
    "admissibility_status",
    "admissibility_obstacle",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DIRECT_CHI_ADJUDICATION_FIELDS = [
    "direct_chi_adjudication_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "evidence_distance_tier",
    "required_chi_floor_at_existing_min_beta",
    "required_beta_chi_floor",
    "best_chi_lower_bound",
    "best_beta_chi_lower_bound",
    "direct_candidate_count",
    "admissible_candidate_count",
    "admission_result",
    "post_review_model_action",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DIRECT_BETA_CHI_ESTIMATOR_CONTRACT_FIELDS = [
    "direct_beta_chi_estimator_contract_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "evidence_distance_tier",
    "required_beta_chi_floor",
    "required_chi_floor_at_existing_min_beta",
    "estimator_estimand",
    "required_panel_grain",
    "required_treatment_input",
    "required_outcome_input",
    "required_identification_input",
    "required_inference_checks",
    "minimum_observation_rule",
    "current_tdc_treatment_source_status",
    "current_outcome_source_status",
    "current_identification_source_status",
    "current_contract_status",
    "admission_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

DIRECT_BETA_CHI_TARGET_IMPACT_FIELDS = [
    "direct_beta_chi_target_impact_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_axis",
    "evidence_distance_tier",
    "required_beta_chi_floor",
    "required_chi_floor_at_existing_min_beta",
    "best_beta_chi_lower_bound",
    "best_chi_lower_bound",
    "direct_evidence_admission_result",
    "current_claim_status",
    "if_floor_admitted_model_action",
    "final_model_use_after_admission",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class DirectChiEvidenceError(ValueError):
    """Raised when direct chi evidence rows cannot be built consistently."""


@dataclass(frozen=True)
class DirectChiSourcePaths:
    """Optional source paths for direct chi evidence screening."""

    tdcsim_suite_dir: Path = DEFAULT_UNIFIED_SUITE_DIR
    tdcest_downstream_dir: Path = DEFAULT_TDCEST_DOWNSTREAM_DIR
    tdcsim_period_tdc_dir: Path | None = None
    local_current_demand_dir: Path = DEFAULT_LOCAL_CURRENT_DEMAND_DIR


def direct_chi_requirement_rows(
    evidence_target_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Turn beta-chi target rows into direct chi / beta-chi requirements."""

    out: list[dict[str, str]] = []
    for row in evidence_target_rows:
        out.append(
            {
                "direct_chi_requirement_row_id": (
                    f"direct_chi_requirement::{row['fiscal_year']}::"
                    f"{row['scenario_id']}"
                ),
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "scenario_axis": row["scenario_axis"],
                "evidence_distance_tier": row["evidence_distance_tier"],
                "required_chi_floor_at_existing_min_beta": row[
                    "required_chi_floor_at_existing_min_beta"
                ],
                "required_beta_chi_floor": row["required_beta_chi_floor"],
                "required_beta_floor_at_existing_min_chi": row[
                    "required_beta_floor_at_existing_min_chi"
                ],
                "current_beta_times_chi": row["current_beta_times_chi"],
                "selected_moving_delta_ratewall_ratio_vs_baseline": row[
                    "selected_moving_delta_ratewall_ratio_vs_baseline"
                ],
                "target_estimand": (
                    "chi_or_beta_chi_response_to_materialized_tdc_ex_overlap_flow"
                ),
                "minimum_admissible_evidence": (
                    "identified_current_demand_response_to_materialized_tdc_ex_overlap;"
                    "or_direct_beta_chi_product_floor_with_lower_bound"
                ),
                "admission_status": "requirement_only_no_evidence_admitted",
                "allowed_use": "direct_chi_evidence_target_floor",
                "blocked_use": (
                    "chi_floor_admission_without_direct_evidence;"
                    "cash_like_mpc_mapping_as_floor;canonical_headline_promotion;"
                    "evidence_mode_claim;posterior_chi_claim"
                ),
                "claim_boundary": (
                    "requirement_rows_only;does_not_change_beta_chi_grid_or_scenario_math"
                ),
            }
        )
    return sorted(out, key=lambda item: (int(item["fiscal_year"]), item["scenario_id"]))


def direct_chi_source_inventory_rows(
    *,
    paths: DirectChiSourcePaths = DirectChiSourcePaths(),
    extra_candidate_rows: Iterable[Mapping[str, str]] = (),
) -> list[dict[str, str]]:
    """Inventory current source surfaces that might support direct chi evidence."""

    rows: list[dict[str, str]] = []
    rows.extend(_tdcsim_suite_rows(paths.tdcsim_suite_dir))
    if paths.tdcsim_period_tdc_dir is not None:
        rows.extend(_tdcsim_period_tdc_rows(paths.tdcsim_period_tdc_dir))
    rows.extend(_tdcest_downstream_rows(paths.tdcest_downstream_dir))
    rows.extend(_local_current_demand_rows(paths.local_current_demand_dir))
    for row in extra_candidate_rows:
        rows.append(_normalize_candidate_row(row))
    return sorted(rows, key=lambda item: item["direct_chi_source_row_id"])


def direct_chi_adjudication_rows(
    *,
    requirement_rows: Iterable[Mapping[str, str]],
    source_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Adjudicate whether any source row can admit a chi or beta-chi floor."""

    sources = list(source_rows)
    direct = [row for row in sources if _is_direct_candidate(row)]
    admissible = [row for row in direct if row["admissibility_status"] == "admissible"]
    out: list[dict[str, str]] = []
    for req in requirement_rows:
        chi_bound = _best_bound(admissible, "reported_chi_lower_bound")
        beta_chi_bound = _best_bound(admissible, "reported_beta_chi_lower_bound")
        chi_clears = (
            chi_bound is not None
            and chi_bound >= _decimal(req["required_chi_floor_at_existing_min_beta"])
        )
        beta_chi_clears = (
            beta_chi_bound is not None
            and beta_chi_bound >= _decimal(req["required_beta_chi_floor"])
        )
        if chi_clears or beta_chi_clears:
            result = "admit_floor_from_direct_evidence"
            action = "reclassify_target_after_owner_gate"
        elif direct:
            result = "not_admitted_direct_candidate_below_required_floor"
            action = "keep_point_calibrated_seek_stronger_direct_lower_bound"
        else:
            result = "not_admitted_no_direct_chi_or_beta_chi_evidence"
            action = "keep_point_calibrated_build_direct_estimator"
        out.append(
            {
                "direct_chi_adjudication_row_id": (
                    f"direct_chi_adjudication::{req['fiscal_year']}::"
                    f"{req['scenario_id']}"
                ),
                "fiscal_year": req["fiscal_year"],
                "scenario_id": req["scenario_id"],
                "scenario_axis": req["scenario_axis"],
                "evidence_distance_tier": req["evidence_distance_tier"],
                "required_chi_floor_at_existing_min_beta": req[
                    "required_chi_floor_at_existing_min_beta"
                ],
                "required_beta_chi_floor": req["required_beta_chi_floor"],
                "best_chi_lower_bound": _fmt_optional(chi_bound),
                "best_beta_chi_lower_bound": _fmt_optional(beta_chi_bound),
                "direct_candidate_count": str(len(direct)),
                "admissible_candidate_count": str(len(admissible)),
                "admission_result": result,
                "post_review_model_action": action,
                "allowed_use": "direct_chi_evidence_adjudication",
                "blocked_use": (
                    "chi_floor_admission_without_clearing_lower_bound;"
                    "cash_like_mpc_mapping_as_floor;canonical_headline_promotion;"
                    "evidence_mode_claim;posterior_chi_claim"
                ),
                "claim_boundary": (
                    "direct_evidence_gate_only;does_not_change_beta_chi_grid_or_scenario_math"
                ),
            }
        )
    return sorted(out, key=lambda item: (int(item["fiscal_year"]), item["scenario_id"]))


def direct_beta_chi_estimator_contract_rows(
    *,
    requirement_rows: Iterable[Mapping[str, str]],
    source_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Build the exact source/estimator contract for admitting beta-chi floors."""

    sources = list(source_rows)
    has_treatment = any(
        row.get("has_tdc_ex_overlap_treatment") == "true" for row in sources
    )
    has_outcome = any(row.get("has_current_demand_outcome") == "true" for row in sources)
    has_identification = any(
        row.get("has_identification_strategy") == "true" for row in sources
    )
    out: list[dict[str, str]] = []
    for req in requirement_rows:
        status = _estimator_contract_status(
            has_treatment=has_treatment,
            has_outcome=has_outcome,
            has_identification=has_identification,
        )
        out.append(
            {
                "direct_beta_chi_estimator_contract_row_id": (
                    f"direct_beta_chi_estimator_contract::{req['fiscal_year']}::"
                    f"{req['scenario_id']}"
                ),
                "fiscal_year": req["fiscal_year"],
                "scenario_id": req["scenario_id"],
                "scenario_axis": req["scenario_axis"],
                "evidence_distance_tier": req["evidence_distance_tier"],
                "required_beta_chi_floor": req["required_beta_chi_floor"],
                "required_chi_floor_at_existing_min_beta": req[
                    "required_chi_floor_at_existing_min_beta"
                ],
                "estimator_estimand": (
                    "lower_95_bound_of_current_demand_response_per_materialized_"
                    "tdc_ex_overlap_dollar_or_direct_beta_chi_product"
                ),
                "required_panel_grain": (
                    "period_x_recipient_or_holder_bucket_with_scenario_and_baseline_"
                    "keys"
                ),
                "required_treatment_input": (
                    "materialized_delta_tdc_ex_overlap_to_recipient_or_holder_bucket;"
                    "issuance_principal_interest_and_overlap_components_separated"
                ),
                "required_outcome_input": (
                    "observed_current_demand_spending_or_source_backed_current_"
                    "demand_proxy_matched_to_same_bucket_and_period"
                ),
                "required_identification_input": (
                    "predetermined_exposure_or_external_timing_shock;not_scenario_"
                    "assumption_only;not_one_sided_treatment_screen"
                ),
                "required_inference_checks": (
                    "clustered_or_hac_standard_errors;lower_95_bound_reported;"
                    "placebo_or_lead_check;sample_count_and_bucket_count_reported"
                ),
                "minimum_observation_rule": (
                    "enough_independent_period_or_bucket_variation_for_clustered_"
                    "inference;single_forecast_row_cannot_identify_beta_chi"
                ),
                "current_tdc_treatment_source_status": _present_status(has_treatment),
                "current_outcome_source_status": _present_status(has_outcome),
                "current_identification_source_status": _present_status(
                    has_identification
                ),
                "current_contract_status": status,
                "admission_status": "contract_only_no_floor_admitted",
                "allowed_use": "direct_beta_chi_final_evidence_contract",
                "blocked_use": (
                    "beta_chi_floor_admission_without_matching_contract;"
                    "chi_floor_admission_from_cash_like_mpc_mapping;"
                    "canonical_headline_promotion;evidence_mode_claim;"
                    "posterior_beta_or_chi_claim"
                ),
                "claim_boundary": (
                    "estimator_contract_only;does_not_change_beta_chi_grid_or_"
                    "scenario_math"
                ),
            }
        )
    return sorted(out, key=lambda item: (int(item["fiscal_year"]), item["scenario_id"]))


def direct_beta_chi_target_impact_rows(
    *,
    requirement_rows: Iterable[Mapping[str, str]],
    adjudication_rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    """Show which targets would reclassify if a direct floor clears."""

    adjudication_by_key = {
        (row["fiscal_year"], row["scenario_id"]): row for row in adjudication_rows
    }
    out: list[dict[str, str]] = []
    for req in requirement_rows:
        key = (req["fiscal_year"], req["scenario_id"])
        adjudication = adjudication_by_key.get(key)
        if adjudication is None:
            raise DirectChiEvidenceError(f"missing adjudication for {key}")
        admitted = (
            adjudication["admission_result"] == "admit_floor_from_direct_evidence"
        )
        out.append(
            {
                "direct_beta_chi_target_impact_row_id": (
                    f"direct_beta_chi_target_impact::{req['fiscal_year']}::"
                    f"{req['scenario_id']}"
                ),
                "fiscal_year": req["fiscal_year"],
                "scenario_id": req["scenario_id"],
                "scenario_axis": req["scenario_axis"],
                "evidence_distance_tier": req["evidence_distance_tier"],
                "required_beta_chi_floor": req["required_beta_chi_floor"],
                "required_chi_floor_at_existing_min_beta": req[
                    "required_chi_floor_at_existing_min_beta"
                ],
                "best_beta_chi_lower_bound": adjudication[
                    "best_beta_chi_lower_bound"
                ],
                "best_chi_lower_bound": adjudication["best_chi_lower_bound"],
                "direct_evidence_admission_result": adjudication[
                    "admission_result"
                ],
                "current_claim_status": (
                    "direct_floor_admitted"
                    if admitted
                    else "point_calibrated_only_no_direct_floor"
                ),
                "if_floor_admitted_model_action": (
                    "reclassify_as_sign_robust_over_admitted_beta_chi_floor"
                ),
                "final_model_use_after_admission": (
                    "scenario_claim_can_use_direct_floor_for_this_target_only"
                    if admitted
                    else "unchanged_point_calibrated_assumption_mode"
                ),
                "allowed_use": "direct_beta_chi_reclassification_target",
                "blocked_use": (
                    "global_beta_chi_prior_narrowing;canonical_headline_promotion;"
                    "evidence_mode_claim;posterior_beta_or_chi_claim"
                ),
                "claim_boundary": (
                    "target_impact_only;requires_direct_floor_admission_before_"
                    "scenario_reclassification"
                ),
            }
        )
    return sorted(out, key=lambda item: (int(item["fiscal_year"]), item["scenario_id"]))


def direct_chi_rows_from_claim_gate(
    claim_gate_rows: Iterable[Mapping[str, str]],
    *,
    paths: DirectChiSourcePaths = DirectChiSourcePaths(),
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """Build requirement, source, and adjudication rows from claim-gate rows."""

    thresholds = beta_chi_robustness_threshold_rows(claim_gate_rows)
    targets = beta_chi_evidence_target_rows(thresholds)
    requirements = direct_chi_requirement_rows(targets)
    sources = direct_chi_source_inventory_rows(paths=paths)
    adjudications = direct_chi_adjudication_rows(
        requirement_rows=requirements,
        source_rows=sources,
    )
    return requirements, sources, adjudications


def write_direct_chi_evidence_outputs(
    output_dir: str | Path,
    *,
    requirement_rows: Sequence[Mapping[str, str]],
    source_rows: Sequence[Mapping[str, str]],
    adjudication_rows: Sequence[Mapping[str, str]],
    estimator_contract_rows: Sequence[Mapping[str, str]] = (),
    target_impact_rows: Sequence[Mapping[str, str]] = (),
) -> dict[str, Path]:
    """Write direct chi evidence CSVs and a short memo."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "requirements_csv": out / "ratewall_direct_chi_requirements.csv",
        "source_inventory_csv": out / "ratewall_direct_chi_source_inventory.csv",
        "adjudication_csv": out / "ratewall_direct_chi_adjudication.csv",
        "estimator_contract_csv": (
            out / "ratewall_direct_beta_chi_estimator_contract.csv"
        ),
        "target_impact_csv": out / "ratewall_direct_beta_chi_target_impact.csv",
        "memo_md": out / "direct_chi_evidence_memo.md",
    }
    _write_csv(paths["requirements_csv"], DIRECT_CHI_REQUIREMENT_FIELDS, requirement_rows)
    _write_csv(paths["source_inventory_csv"], DIRECT_CHI_SOURCE_FIELDS, source_rows)
    _write_csv(paths["adjudication_csv"], DIRECT_CHI_ADJUDICATION_FIELDS, adjudication_rows)
    if estimator_contract_rows:
        _write_csv(
            paths["estimator_contract_csv"],
            DIRECT_BETA_CHI_ESTIMATOR_CONTRACT_FIELDS,
            estimator_contract_rows,
        )
    if target_impact_rows:
        _write_csv(
            paths["target_impact_csv"],
            DIRECT_BETA_CHI_TARGET_IMPACT_FIELDS,
            target_impact_rows,
        )
    paths["memo_md"].write_text(
        direct_chi_evidence_memo_markdown(
            requirement_rows=requirement_rows,
            source_rows=source_rows,
            adjudication_rows=adjudication_rows,
            estimator_contract_rows=estimator_contract_rows,
            target_impact_rows=target_impact_rows,
        ),
        encoding="utf-8",
    )
    return paths


def direct_chi_evidence_memo_markdown(
    *,
    requirement_rows: Sequence[Mapping[str, str]],
    source_rows: Sequence[Mapping[str, str]],
    adjudication_rows: Sequence[Mapping[str, str]],
    estimator_contract_rows: Sequence[Mapping[str, str]] = (),
    target_impact_rows: Sequence[Mapping[str, str]] = (),
) -> str:
    """Return a concise memo for the direct chi evidence gate."""

    admitted = [
        row
        for row in adjudication_rows
        if row["admission_result"] == "admit_floor_from_direct_evidence"
    ]
    direct_candidates = [
        row for row in source_rows if _is_direct_candidate(row)
    ]
    treatment_only = [
        row
        for row in source_rows
        if row.get("has_tdc_ex_overlap_treatment") == "true"
        and row.get("has_current_demand_outcome") != "true"
    ]
    outcome_only = [
        row for row in source_rows if row["candidate_role"] == "current_demand_outcome_side_only"
    ]
    contracts_ready = [
        row
        for row in estimator_contract_rows
        if row["current_contract_status"] == "ready_for_direct_estimator_input"
    ]
    target_reclassifications = [
        row
        for row in target_impact_rows
        if row["current_claim_status"] == "direct_floor_admitted"
    ]
    lines = [
        "# Direct Chi Evidence Memo",
        "",
        "## Bottom Line",
        "",
        (
            "No direct χ or β×χ floor is admitted from the current source set. "
            "TDC-est and TDCSim provide treatment-side deposit/TDC surfaces; "
            "RateWall current-demand data provide outcome-side context. The current "
            "artifacts do not jointly identify current-demand response to materialized "
            "TDC ex-overlap flow."
        ),
        "",
        "## Counts",
        "",
        f"- Requirement rows: `{len(requirement_rows)}`.",
        f"- Source inventory rows: `{len(source_rows)}`.",
        f"- Treatment-side-only rows: `{len(treatment_only)}`.",
        f"- Outcome-side-only rows: `{len(outcome_only)}`.",
        f"- Direct candidate rows: `{len(direct_candidates)}`.",
        f"- Admitted target rows: `{len(admitted)}`.",
        f"- Estimator contract rows: `{len(estimator_contract_rows)}`.",
        f"- Contract rows ready for direct estimator input: `{len(contracts_ready)}`.",
        f"- Target rows reclassified by direct floor: `{len(target_reclassifications)}`.",
        "",
        "## Model Consequence",
        "",
        (
            "Holder and combined rows that remain beta×chi mixed-sign stay "
            "point-calibrated. The bridge screen remains non-admitting until a "
            "direct estimator or source-backed lower bound clears the target floor."
        ),
    ]
    return "\n".join(lines) + "\n"


def _tdcest_downstream_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    contract = root / "tdc_downstream_estimator_contract.csv"
    if contract.exists():
        contract_rows = _read_csv(contract)
        rows.append(
            _source_row(
                source_family="tdcest_downstream_contract",
                source_artifact=str(contract),
                candidate_role="tdc_treatment_side_only",
                row_count=len(contract_rows),
                has_tdc_ex_overlap_treatment=False,
                has_materialized_tdc_treatment=True,
                has_current_demand_outcome=False,
                has_identification_strategy=False,
                obstacle=(
                    "tdcest_contract_selects_tdc_deposit_effect_series_but_does_not_"
                    "estimate_current_demand_response"
                ),
            )
        )
    series = root / "tdc_downstream_deposit_effect_series_panel.csv"
    if series.exists():
        series_rows = _read_csv(series)
        rows.append(
            _source_row(
                source_family="tdcest_downstream_series_panel",
                source_artifact=str(series),
                candidate_role="tdc_treatment_side_only",
                row_count=len(series_rows),
                has_tdc_ex_overlap_treatment=False,
                has_materialized_tdc_treatment=True,
                has_current_demand_outcome=False,
                has_identification_strategy=False,
                obstacle=(
                    "series_panel_is_tdc_estimator_surface_not_current_demand_outcome"
                ),
            )
        )
    comparison = root / "tdc_downstream_deposit_effect_comparison_panel.csv"
    if comparison.exists():
        comparison_rows = _read_csv(comparison)
        rows.append(
            _source_row(
                source_family="tdcest_downstream_comparison_panel",
                source_artifact=str(comparison),
                candidate_role="tdc_treatment_side_only",
                row_count=len(comparison_rows),
                has_tdc_ex_overlap_treatment=False,
                has_materialized_tdc_treatment=True,
                has_current_demand_outcome=False,
                has_identification_strategy=False,
                obstacle="comparison_panel_compares_tdc_estimator_variants_not_spending",
            )
        )
    return rows


def _tdcsim_suite_rows(root: Path) -> list[dict[str, str]]:
    logical_path = "ratewall_tdcsim_cbo_fiscal_year_ratio_input.csv"
    rows = _read_suite_csv(root, logical_path)
    out: list[dict[str, str]] = []
    if rows:
        out.append(
            _source_row(
                source_family="tdcsim_cbo_ratewall_ratio_input",
                source_artifact=str(root / logical_path),
                candidate_role="tdc_ex_overlap_treatment_side_only",
                row_count=len(rows),
                has_tdc_ex_overlap_treatment=True,
                has_materialized_tdc_treatment=True,
                has_current_demand_outcome=False,
                has_identification_strategy=False,
                obstacle=(
                    "tdcsim_suite_exports_tdc_ex_overlap_treatment_and_modeled_support_"
                    "but_not_observed_current_demand_response"
                ),
            )
        )
    out.extend(_tdcsim_period_tdc_rows(root))
    return out


def _tdcsim_period_tdc_rows(root: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for table_names, role in (
        (
            (
                "tdcsim_period_tdc_summary.csv",
                "tdcsim_period_tdc_summary.csv.gz",
                "outputs/tdcsim_period_tdc_summary.csv",
                "outputs/tdcsim_period_tdc_summary.csv.gz",
            ),
            "period_tdc_summary_treatment_side_only",
        ),
        (
            (
                "tdcsim_period_tdc_components.csv",
                "tdcsim_period_tdc_components.csv.gz",
                "outputs/tdcsim_period_tdc_components.csv",
                "outputs/tdcsim_period_tdc_components.csv.gz",
            ),
            "period_tdc_components_treatment_side_only",
        ),
    ):
        table_name, table_rows = _first_nonempty_suite_table(root, table_names)
        if not table_rows:
            continue
        has_required_tdc_columns = _has_period_tdc_required_columns(table_rows)
        obstacle = (
            "tdcsim_period_tdc_accounting_exports_treatment_components_"
            "but_not_observed_current_demand_response_or_identification"
        )
        if not has_required_tdc_columns:
            obstacle = (
                "tdcsim_period_tdc_accounting_missing_required_ex_overlap_or_"
                "component_columns"
            )
        out.append(
            _source_row(
                source_family="tdcsim_cbo_period_tdc_accounting",
                source_artifact=str(root / table_name),
                candidate_role=role,
                row_count=len(table_rows),
                has_tdc_ex_overlap_treatment=has_required_tdc_columns,
                has_materialized_tdc_treatment=has_required_tdc_columns,
                has_current_demand_outcome=False,
                has_identification_strategy=False,
                obstacle=obstacle,
            )
        )
    return out


def _first_nonempty_suite_table(
    root: Path,
    logical_paths: Sequence[str],
) -> tuple[str, list[dict[str, str]]]:
    for logical_path in logical_paths:
        rows = _read_suite_csv(root, logical_path)
        if rows:
            return logical_path, rows
    return logical_paths[0], []


def _has_period_tdc_required_columns(rows: Sequence[Mapping[str, str]]) -> bool:
    if not rows:
        return False
    fields = set(rows[0])
    summary_columns = {"period_start", "period_end", "tdc_change_ex_overlap_bil"}
    component_columns = {
        "period_start",
        "period_end",
        "amount_bil",
        "is_additive_to_tdc_change",
        "enters_tdc_deposit_support_default",
    }
    return summary_columns <= fields or component_columns <= fields


def _local_current_demand_rows(root: Path) -> list[dict[str, str]]:
    if not root.exists():
        return []
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".json"}
    ]
    if not files:
        return []
    return [
        _source_row(
            source_family="ratewall_current_demand_gdp_share",
            source_artifact=str(root),
            candidate_role="current_demand_outcome_side_only",
            row_count=len(files),
            has_tdc_ex_overlap_treatment=False,
            has_materialized_tdc_treatment=False,
            has_current_demand_outcome=True,
            has_identification_strategy=False,
            obstacle="current_demand_sources_do_not_identify_tdc_treatment",
        )
    ]


def _read_suite_csv(root: Path, logical_path: str) -> list[dict[str, str]]:
    if artifact_manifest_exists(root):
        manifest = ArtifactManifestView.from_root(root)
        if manifest.has_file(logical_path):
            with manifest.open_text(logical_path) as handle:
                return list(csv.DictReader(handle))
        return []
    path = root / logical_path
    if path.exists():
        if path.suffix == ".gz":
            return _read_gzip_csv(path)
        return _read_csv(path)
    return []


def _normalize_candidate_row(row: Mapping[str, str]) -> dict[str, str]:
    normalized = {field: row.get(field, "") for field in DIRECT_CHI_SOURCE_FIELDS}
    if not normalized["direct_chi_source_row_id"]:
        normalized["direct_chi_source_row_id"] = (
            f"direct_chi_source::{normalized['source_family']}::"
            f"{Path(normalized['source_artifact']).name}"
        )
    normalized["row_count"] = normalized["row_count"] or "1"
    normalized["admissibility_status"] = normalized["admissibility_status"] or (
        _candidate_admissibility_status(normalized)
    )
    normalized["allowed_use"] = normalized["allowed_use"] or "direct_chi_source_screen"
    normalized["blocked_use"] = normalized["blocked_use"] or (
        "chi_floor_admission_without_direct_lower_bound;canonical_headline_promotion;"
        "evidence_mode_claim"
    )
    normalized["claim_boundary"] = normalized["claim_boundary"] or (
        "source_inventory_only;does_not_change_beta_chi_grid_or_scenario_math"
    )
    return normalized


def _source_row(
    *,
    source_family: str,
    source_artifact: str,
    candidate_role: str,
    row_count: int,
    has_tdc_ex_overlap_treatment: bool,
    has_materialized_tdc_treatment: bool,
    has_current_demand_outcome: bool,
    has_identification_strategy: bool,
    obstacle: str,
) -> dict[str, str]:
    row = {
        "direct_chi_source_row_id": (
            f"direct_chi_source::{source_family}::{Path(source_artifact).name}"
        ),
        "source_family": source_family,
        "source_artifact": source_artifact,
        "candidate_role": candidate_role,
        "row_count": str(row_count),
        "has_tdc_ex_overlap_treatment": _bool(has_tdc_ex_overlap_treatment),
        "has_materialized_tdc_treatment": _bool(has_materialized_tdc_treatment),
        "has_current_demand_outcome": _bool(has_current_demand_outcome),
        "has_identification_strategy": _bool(has_identification_strategy),
        "reports_chi_lower_bound": "false",
        "reported_chi_lower_bound": "",
        "reports_beta_chi_lower_bound": "false",
        "reported_beta_chi_lower_bound": "",
        "admissibility_status": "",
        "admissibility_obstacle": obstacle,
        "allowed_use": "direct_chi_source_screen",
        "blocked_use": (
            "chi_floor_admission_without_direct_lower_bound;"
            "canonical_headline_promotion;evidence_mode_claim;posterior_chi_claim"
        ),
        "claim_boundary": (
            "source_inventory_only;does_not_change_beta_chi_grid_or_scenario_math"
        ),
    }
    row["admissibility_status"] = _candidate_admissibility_status(row)
    return row


def _candidate_admissibility_status(row: Mapping[str, str]) -> str:
    if row.get("has_tdc_ex_overlap_treatment") != "true":
        return "not_admitted_missing_tdc_ex_overlap_treatment"
    if row.get("has_current_demand_outcome") != "true":
        return "not_admitted_missing_current_demand_outcome"
    if row.get("has_identification_strategy") != "true":
        return "not_admitted_missing_identification_strategy"
    if (
        row.get("reports_chi_lower_bound") != "true"
        and row.get("reports_beta_chi_lower_bound") != "true"
    ):
        return "not_admitted_missing_lower_bound"
    return "admissible"


def _estimator_contract_status(
    *,
    has_treatment: bool,
    has_outcome: bool,
    has_identification: bool,
) -> str:
    missing = []
    if not has_treatment:
        missing.append("tdc_ex_overlap_treatment")
    if not has_outcome:
        missing.append("current_demand_outcome")
    if not has_identification:
        missing.append("identification_strategy")
    if missing:
        return "blocked_missing_" + "_and_".join(missing)
    return "ready_for_direct_estimator_input"


def _present_status(value: bool) -> str:
    return "present" if value else "missing"


def _is_direct_candidate(row: Mapping[str, str]) -> bool:
    return (
        row.get("has_tdc_ex_overlap_treatment") == "true"
        and row.get("has_current_demand_outcome") == "true"
        and row.get("has_identification_strategy") == "true"
    )


def _best_bound(rows: Iterable[Mapping[str, str]], field: str) -> Decimal | None:
    values = []
    for row in rows:
        value = row.get(field, "")
        if value:
            values.append(_decimal(value))
    if not values:
        return None
    return max(values)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_gzip_csv(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _decimal(value: str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DirectChiEvidenceError(f"invalid decimal: {value!r}") from exc


def _fmt_optional(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value, "f")


def _bool(value: bool) -> str:
    return "true" if value else "false"
