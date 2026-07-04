"""Calibration and denominator spine table writer adapters."""

from __future__ import annotations

from pathlib import Path

from ratewall.databook.table_io import write_rows


RATEWALL_DENOMINATOR_SENSITIVITY_FIELDS = [
    "assumption_set",
    "denominator_parameter",
    "component_value_bil",
    "component_share_of_scalar_drag",
    "split_minus_scalar_drag_bil",
    "denominator_share_sum",
    "denominator_share_sum_status",
    "split_denominator_total_drag_multiplier",
    "split_denominator_offset_ratio",
    "scalar_offset_ratio",
    "classification_change_flag",
    "classification_change_driver",
    "classification_change_driver_type",
    "decisive_denominator_channel",
    "component_share_interpretation",
    "claim_boundary",
]


RATEWALL_DENOMINATOR_LITERATURE_MATRIX_FIELDS = [
    "denominator_channel",
    "denominator_parameter",
    "citation_handle",
    "source_family",
    "identification_design",
    "horizon_relevance",
    "candidate_papers_or_source_families",
    "admissible_shock_requirement",
    "plausible_sign",
    "plausible_magnitude_status",
    "evidence_gap",
    "supports_low_base_high_prior",
    "evidence_strength",
    "source_status",
    "prior_basis",
    "external_review_status",
    "evidence_upgrade_blocker",
    "upgrade_gate",
    "claim_boundary",
]


RATEWALL_PARAMETER_PACK_FIELDS = [
    "parameter",
    "channel",
    "unit",
    "low",
    "base",
    "high",
    "source_status",
    "rationale",
    "source_note",
    "literature_context",
    "evidence_needed",
    "review_priority",
    "model_use",
    "review_question",
    "candidate_source_literature",
    "citation_handle",
    "source_family",
    "identification_design",
    "horizon_relevance",
    "uncertainty_status",
    "evidence_strength",
    "prior_basis",
    "external_review_status",
    "upgrade_gate",
    "evidence_upgrade_blocker",
    "calibration_status",
    "calibration_order",
    "calibration_distribution_shape",
    "calibration_low",
    "calibration_base",
    "calibration_high",
    "calibration_formula",
    "source_gate_table",
    "allowed_model_use",
    "scenario_implied_only",
    "forbidden_claim_risk",
    "plausibility_status",
    "claim_boundary",
]


RATEWALL_CALIBRATION_PARAMETER_RECOMMENDATION_FIELDS = [
    "rank",
    "parameter",
    "ratewall_channel",
    "recommended_low",
    "recommended_base",
    "recommended_high",
    "recommended_range_note",
    "calibration_status",
    "source_family",
    "source_status",
    "allowed_model_use",
    "source_gate_table",
    "can_narrow_prior",
    "can_replace_formula_handle",
    "can_enter_main_ratio",
    "main_offset_ratio_changed_this_tranche",
    "promotion_gate",
    "evidence_needed_before_promotion",
    "expected_classification_impact",
    "forbidden_claim_risk",
    "claim_boundary",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "raw_rate_shock_enabled",
    "causal_financialization_claim_enabled",
]


def _write_ratewall_denominator_sensitivity_table(
    path: Path, rows: list[dict[str, str]]
) -> None:
    write_rows(path, rows, RATEWALL_DENOMINATOR_SENSITIVITY_FIELDS)


def _write_ratewall_denominator_literature_matrix_table(
    path: Path, rows: list[dict[str, str]]
) -> None:
    write_rows(path, rows, RATEWALL_DENOMINATOR_LITERATURE_MATRIX_FIELDS)


def _write_ratewall_parameter_packs_table(
    path: Path, rows: list[dict[str, str]]
) -> None:
    write_rows(path, rows, RATEWALL_PARAMETER_PACK_FIELDS)


def _write_ratewall_calibration_parameter_recommendations_table(
    path: Path, rows: list[dict[str, str]]
) -> None:
    write_rows(path, rows, RATEWALL_CALIBRATION_PARAMETER_RECOMMENDATION_FIELDS)
