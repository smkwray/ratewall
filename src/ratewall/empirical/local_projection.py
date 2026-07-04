"""Initial local-projection design scaffolding.

This module defines specification metadata and design validation only. It does
not estimate monetary transmission from raw rate changes.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from math import log, sqrt
from pathlib import Path
from statistics import median

from ratewall.data.derived import derive_accounting_inputs
from ratewall.data.snapshots import read_snapshot_bundle


@dataclass(frozen=True)
class LocalProjectionSpec:
    outcome: str
    shock: str
    state_variable: str
    horizons: tuple[int, ...]
    controls: tuple[str, ...]

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.shock.lower() in {"fedfunds", "fed funds", "policy_rate_change"}:
            errors.append("raw policy-rate changes are not valid monetary shocks")
        if not self.horizons:
            errors.append("at least one horizon is required")
        if min(self.horizons) < 0:
            errors.append("horizons must be nonnegative")
        return errors

    def to_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome,
            "shock": self.shock,
            "state_variable": self.state_variable,
            "horizons": list(self.horizons),
            "controls": list(self.controls),
            "equation": (
                "z(t+h) = alpha_h + beta_h * MPShock(t) + gamma_h * "
                "MPShock(t) * S(t-1) + delta_h * S(t-1) + controls + error"
            ),
        }


@dataclass(frozen=True)
class MonetaryShockDataset:
    dataset_id: str
    source: str
    url: str
    shock_column: str
    date_column: str
    units: str
    identification: str
    admissible: bool
    notes: str

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.shock_column.lower() in {"fedfunds", "fed funds", "policy_rate_change"}:
            errors.append("raw policy-rate changes are not valid monetary shocks")
        if "surprise" not in self.identification.lower() and "narrative" not in self.identification.lower():
            errors.append("shock dataset must document surprise or narrative identification")
        if not self.admissible:
            errors.append(f"{self.dataset_id} is not admissible")
        return errors

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "source": self.source,
            "url": self.url,
            "date_column": self.date_column,
            "shock_column": self.shock_column,
            "units": self.units,
            "identification": self.identification,
            "admissible": self.admissible,
            "notes": self.notes,
        }


DEFAULT_SPECS = (
    LocalProjectionSpec(
        outcome="core_pce_inflation",
        shock="high_frequency_monetary_surprise",
        state_variable="public_liability_base_gdp",
        horizons=tuple(range(0, 13)),
        controls=("lagged_inflation", "output_gap", "financial_conditions"),
    ),
    LocalProjectionSpec(
        outcome="public_interest_income",
        shock="high_frequency_monetary_surprise",
        state_variable="repricing_exposure_gdp",
        horizons=tuple(range(0, 13)),
        controls=("lagged_policy_rate", "nominal_gdp_growth"),
    ),
)


DEFAULT_SHOCK_DATASETS = (
    MonetaryShockDataset(
        dataset_id="sf_fed_monetary_policy_surprises",
        source="Federal Reserve Bank of San Francisco",
        url="https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/",
        date_column="date",
        shock_column="orthogonalized_surprise_bps",
        units="basis_points",
        identification=(
            "High-frequency monetary policy surprises around FOMC announcements, "
            "orthogonalized with respect to public information before the event."
        ),
        admissible=True,
        notes=(
            "Use as an external shock/proxy. Do not substitute raw federal funds "
            "rate changes for this series."
        ),
    ),
    MonetaryShockDataset(
        dataset_id="fed_brw_monetary_policy_shocks",
        source="Board of Governors of the Federal Reserve System",
        url=(
            "https://www.federalreserve.gov/econres/feds/"
            "a-unified-measure-of-fed-monetary-policy-shocks.htm"
        ),
        date_column="month",
        shock_column="monthly_shock_pctpt",
        units="percentage_points",
        identification=(
            "Federal Reserve FEDS BRW monetary policy shock series used as "
            "an external surprise/proxy candidate; source file also includes "
            "FOMC-frequency shocks."
        ),
        admissible=True,
        notes=(
            "Use as an admissible external-proxy candidate only after support "
            "diagnostics. Do not substitute raw policy-rate changes."
        ),
    ),
)


def write_empirical_specs(
    path: Path, specs: tuple[LocalProjectionSpec, ...] = DEFAULT_SPECS
) -> Path:
    errors = [error for spec in specs for error in spec.validate()]
    if errors:
        raise ValueError("; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([spec.to_dict() for spec in specs], indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return path


def write_shock_dataset_catalog(
    path: Path,
    datasets: tuple[MonetaryShockDataset, ...] = DEFAULT_SHOCK_DATASETS,
) -> Path:
    errors = [error for dataset in datasets for error in dataset.validate()]
    if errors:
        raise ValueError("; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [dataset.to_dict() for dataset in datasets], indent=2, sort_keys=True
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_empirical_smoke_panel(
    *,
    snapshot_bundle: Path,
    output: Path,
) -> Path:
    rows = _build_empirical_smoke_rows(snapshot_bundle)
    _write_csv(output, rows, EMPIRICAL_SMOKE_FIELDNAMES)
    return output


EMPIRICAL_SMOKE_FIELDNAMES = [
    "date",
    "shock_dataset",
    "shock_column",
    "orthogonalized_surprise_bps",
    "public_liability_base_1y_gdp",
    "repricing_share_1y",
    "debt_held_public_gdp",
    "rate_sensitive_fed_liabilities_gdp",
    "reserves_asof",
    "on_rrp_asof",
    "gdp_asof",
    "debt_asof",
    "mspd_asof",
    "state_alignment_scope",
    "treasury_repricing_scope",
    "design_scope",
    "guardrail",
]


EMPIRICAL_RESULT_FIELDNAMES = [
    "artifact_layer",
    "result_id",
    "shock_dataset",
    "shock_column",
    "outcome_variable",
    "horizon_months",
    "state_variable",
    "n_obs",
    "sample_start",
    "sample_end",
    "estimator",
    "estimate",
    "standard_error",
    "t_stat",
    "response_unit",
    "state_median",
    "low_state_mean_shock_bps",
    "high_state_mean_shock_bps",
    "high_minus_low_mean_shock_bps",
    "result_status",
    "causal_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


OUTCOME_PANEL_FIELDNAMES = [
    "event_date",
    "shock_dataset",
    "shock_column",
    "orthogonalized_surprise_bps",
    "outcome_variable",
    "outcome_source",
    "horizon_months",
    "pre_outcome_asof",
    "post_outcome_asof",
    "pre_outcome_value",
    "post_outcome_value",
    "outcome_change",
    "outcome_change_unit",
    "lagged_outcome_start_asof",
    "lagged_outcome_end_asof",
    "lagged_outcome_change",
    "lagged_outcome_change_unit",
    "public_liability_base_1y_gdp",
    "repricing_share_1y",
    "debt_held_public_gdp",
    "rate_sensitive_fed_liabilities_gdp",
    "state_alignment_scope",
    "shock_identification",
    "raw_rate_change_identification_rejected",
    "panel_status",
]


def write_empirical_results(
    *,
    snapshot_bundle: Path,
    output: Path,
    outcome_panel: Path | None = None,
    figure: Path | None = None,
    report: Path | None = None,
    final_paper_support: Path | None = None,
    paper_support: Path | None = None,
) -> Path:
    """Write bounded empirical result artifacts from admissible shock joins.

    The result rows are source-backed shock/state associations. They are not
    local-projection estimates of inflation, output, pricing, or welfare.
    """

    smoke_rows = _build_empirical_smoke_rows(snapshot_bundle)
    panel_rows = _build_outcome_panel_rows(snapshot_bundle, smoke_rows)
    if outcome_panel is not None:
        _write_csv(outcome_panel, panel_rows, OUTCOME_PANEL_FIELDNAMES)
    result_rows = _build_empirical_result_rows(smoke_rows, panel_rows)
    _write_csv(output, result_rows, EMPIRICAL_RESULT_FIELDNAMES)
    _write_release_1_1_empirical_artifacts(
        output=output,
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        report=report,
    )
    _write_release_2_0_empirical_artifacts(
        output=output,
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        report=report,
    )
    _write_release_3_0_empirical_artifacts(
        output=output,
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        report=report,
    )
    _write_release_4_0_empirical_artifacts(
        output=output,
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        report=report,
    )
    _write_release_5_0_empirical_artifacts(
        output=output,
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        report=report,
    )
    _write_release_6_0_empirical_artifacts(
        output=output,
        snapshot_bundle=snapshot_bundle,
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        report=report,
    )
    _write_release_7_0_empirical_artifacts(
        output=output,
        snapshot_bundle=snapshot_bundle,
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        report=report,
    )
    _write_release_8_0_empirical_artifacts(
        output=output,
        snapshot_bundle=snapshot_bundle,
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        report=report,
    )
    _write_release_9_0_empirical_artifacts(
        output=output,
        snapshot_bundle=snapshot_bundle,
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        report=report,
    )
    if figure is not None:
        _write_empirical_state_figure(figure, result_rows)
    if report is not None:
        _write_empirical_result_report(
            report, result_rows, outcome_panel=outcome_panel, figure=figure
        )
    if final_paper_support is not None:
        _write_final_paper_support(final_paper_support, result_rows)
    if paper_support is not None:
        _update_paper_support_report(
            paper_support,
            result_rows,
            report=report,
            final_paper_support=final_paper_support,
        )
    return output


CAUSAL_IDENTIFICATION_AUDIT_FIELDNAMES = [
    "audit_component",
    "audit_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_1_1_decision",
    "raw_rate_change_identification_rejected",
    "causal_claim_enabled",
    "notes",
]


CAUSAL_DEFENSIBILITY_BLOCKER_FIELDNAMES = [
    "blocker_id",
    "blocker_status",
    "evidence_artifact",
    "required_resolution",
    "release_action",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


EVENT_STUDY_SUPPORT_FIELDNAMES = [
    "diagnostic_id",
    "outcome_variable",
    "horizon_months",
    "sample_start",
    "sample_end",
    "n_obs",
    "unique_event_years",
    "min_shock_bps",
    "max_shock_bps",
    "mean_abs_shock_bps",
    "state_variable",
    "state_median",
    "low_state_n",
    "high_state_n",
    "support_status",
    "raw_rate_change_identification_rejected",
    "bounded_event_study_appendix_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "notes",
]


EVENT_STUDY_ROBUSTNESS_FIELDNAMES = [
    "robustness_id",
    "outcome_variable",
    "horizon_months",
    "diagnostic_type",
    "estimator",
    "n_obs",
    "baseline_estimate",
    "robustness_estimate",
    "difference_from_baseline",
    "standard_error",
    "t_stat",
    "response_unit",
    "robustness_status",
    "raw_rate_change_identification_rejected",
    "bounded_event_study_appendix_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "notes",
]


SUBMISSION_IDENTIFICATION_DECISION_FIELDNAMES = [
    "decision_id",
    "decision_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_2_0_action",
    "bounded_event_study_appendix_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


DYNAMIC_LP_FEASIBILITY_FIELDNAMES = [
    "gate_id",
    "gate_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_3_0_decision",
    "bounded_event_study_appendix_enabled",
    "dynamic_lp_claim_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


PROXY_SVAR_FEASIBILITY_FIELDNAMES = [
    "gate_id",
    "gate_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_3_0_decision",
    "proxy_svar_claim_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


DYNAMIC_CAUSAL_FINAL_BLOCKER_FIELDNAMES = [
    "blocker_id",
    "blocker_status",
    "evidence_artifact",
    "blocked_dynamic_lp_gates",
    "blocked_proxy_svar_gates",
    "required_resolution",
    "release_3_0_action",
    "bounded_event_study_appendix_enabled",
    "dynamic_lp_claim_enabled",
    "proxy_svar_claim_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


EVENT_STUDY_HAC_FIELDNAMES = [
    "diagnostic_id",
    "outcome_variable",
    "horizon_months",
    "sample_start",
    "sample_end",
    "n_obs",
    "estimator",
    "ols_estimate",
    "ols_standard_error",
    "hac_lag",
    "hac_standard_error",
    "hac_t_stat",
    "response_unit",
    "diagnostic_status",
    "dynamic_lp_claim_enabled",
    "proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


PRETREND_PLACEBO_FIELDNAMES = [
    "diagnostic_id",
    "outcome_variable",
    "horizon_months",
    "sample_start",
    "sample_end",
    "n_obs",
    "placebo_variable",
    "estimator",
    "placebo_estimate",
    "placebo_standard_error",
    "placebo_t_stat",
    "diagnostic_status",
    "dynamic_lp_claim_enabled",
    "proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


DYNAMIC_IDENTIFICATION_PROMOTION_CONTRACT_FIELDNAMES = [
    "requirement_id",
    "requirement_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "future_opt_in_prerequisite",
    "dynamic_lp_claim_enabled",
    "proxy_svar_claim_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_4_0_DYNAMIC_BLOCKER_FIELDNAMES = [
    "blocker_id",
    "blocker_status",
    "evidence_artifact",
    "blocked_dynamic_lp_requirements",
    "blocked_proxy_svar_requirements",
    "diagnostic_support",
    "required_resolution",
    "release_4_0_action",
    "bounded_event_study_appendix_enabled",
    "dynamic_lp_claim_enabled",
    "proxy_svar_claim_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_4_0_SUBMISSION_CHECKLIST_FIELDNAMES = [
    "check_id",
    "check_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_4_0_action",
    "dynamic_lp_claim_enabled",
    "proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


EXTERNAL_REVIEW_ISSUE_MATRIX_FIELDNAMES = [
    "issue_id",
    "reviewer_concern",
    "response_status",
    "evidence_artifact",
    "release_response",
    "claim_boundary",
    "dynamic_lp_claim_enabled",
    "proxy_svar_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
]


CONTROLLED_DYNAMIC_LP_PANEL_FIELDNAMES = [
    "event_date",
    "outcome_variable",
    "horizon_months",
    "shock_dataset",
    "shock_column",
    "shock_100bp",
    "outcome_change",
    "lagged_outcome_change",
    "public_liability_base_1y_gdp",
    "repricing_share_1y",
    "debt_held_public_gdp",
    "rate_sensitive_fed_liabilities_gdp",
    "state_centered",
    "shock_state_interaction",
    "source_backed_control_count",
    "panel_status",
    "dynamic_lp_appendix_enabled",
    "proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


CONTROLLED_DYNAMIC_LP_RESULT_FIELDNAMES = [
    "result_id",
    "outcome_variable",
    "horizon_months",
    "n_obs",
    "sample_start",
    "sample_end",
    "estimator",
    "shock_estimate",
    "shock_hac_standard_error",
    "shock_hac_t_stat",
    "state_interaction_estimate",
    "state_interaction_hac_standard_error",
    "state_interaction_hac_t_stat",
    "control_variables",
    "hac_lag",
    "response_unit",
    "result_status",
    "dynamic_lp_appendix_enabled",
    "proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


DYNAMIC_LP_SUPPORT_FIELDNAMES = [
    "diagnostic_id",
    "outcome_variable",
    "horizon_months",
    "n_obs",
    "sample_start",
    "sample_end",
    "unique_event_years",
    "control_variables",
    "min_abs_shock_100bp",
    "max_abs_shock_100bp",
    "support_status",
    "dynamic_lp_appendix_enabled",
    "proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_5_0_IDENTIFICATION_DECISION_FIELDNAMES = [
    "decision_id",
    "decision_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_5_0_action",
    "controlled_dynamic_lp_appendix_enabled",
    "proxy_svar_claim_enabled",
    "state_dependent_claim_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_5_0_PROXY_SVAR_BLOCKER_FIELDNAMES = [
    "blocker_id",
    "blocker_status",
    "evidence_artifact",
    "blocked_requirements",
    "required_resolution",
    "release_5_0_action",
    "controlled_dynamic_lp_appendix_enabled",
    "proxy_svar_claim_enabled",
    "state_dependent_claim_enabled",
    "full_lp_proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


PROXY_SVAR_SYSTEM_PANEL_FIELDNAMES = [
    "month",
    "core_pce_inflation_3m_annualized",
    "industrial_production_growth_3m_annualized",
    "unemployment_rate",
    "fed_funds_rate",
    "fed_funds_rate_change",
    "sf_fed_proxy_shock_bps",
    "proxy_event_count",
    "public_liability_base_1y_gdp",
    "repricing_share_1y",
    "debt_held_public_gdp",
    "rate_sensitive_fed_liabilities_gdp",
    "state_alignment_scope",
    "system_variable_count",
    "panel_status",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


PROXY_SVAR_RELEVANCE_FIELDNAMES = [
    "diagnostic_id",
    "n_obs",
    "sample_start",
    "sample_end",
    "unique_event_years",
    "nonzero_proxy_months",
    "estimator",
    "dependent_variable",
    "instrument_variable",
    "first_stage_beta",
    "first_stage_standard_error",
    "first_stage_t_stat",
    "proxy_shock_std",
    "policy_change_std",
    "diagnostic_status",
    "required_value",
    "proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


PROXY_SVAR_RESIDUAL_DIAGNOSTIC_FIELDNAMES = [
    "diagnostic_id",
    "system_variable",
    "n_obs",
    "sample_start",
    "sample_end",
    "estimator",
    "ar1_coefficient",
    "residual_std",
    "lag1_residual_autocorrelation",
    "diagnostic_status",
    "required_value",
    "proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


PROXY_SVAR_TIMING_SUPPORT_FIELDNAMES = [
    "diagnostic_id",
    "n_system_months",
    "n_proxy_event_months",
    "n_event_months_missing_system",
    "monthly_sample_start",
    "monthly_sample_end",
    "proxy_sample_start",
    "proxy_sample_end",
    "timing_status",
    "required_value",
    "proxy_svar_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_6_0_IDENTIFICATION_DECISION_FIELDNAMES = [
    "decision_id",
    "decision_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_6_0_action",
    "controlled_dynamic_lp_appendix_enabled",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "valuation_incidence_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_6_0_PROXY_SVAR_BLOCKER_FIELDNAMES = [
    "blocker_id",
    "blocker_status",
    "evidence_artifact",
    "blocked_requirements",
    "required_resolution",
    "release_6_0_action",
    "controlled_dynamic_lp_appendix_enabled",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "valuation_incidence_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_6_0_VALUATION_FRONTIER_FIELDNAMES = [
    "frontier_id",
    "frontier_status",
    "evidence_artifact",
    "required_source_method",
    "explicit_opt_in_switches",
    "pricing_output_enabled",
    "holder_bridge_enabled",
    "tax_assumptions_enabled",
    "mpc_assumptions_enabled",
    "welfare_incidence_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "release_6_0_action",
    "notes",
]


RELEASE_7_0_VAR_LAG_SELECTION_FIELDNAMES = [
    "lag_order",
    "n_obs",
    "system_variables",
    "estimated_equations",
    "parameter_count",
    "system_sse",
    "system_aic",
    "system_bic",
    "lag_selection_status",
    "selected_by_bic",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_7_0_REDUCED_FORM_ESTIMATE_FIELDNAMES = [
    "estimate_id",
    "equation_variable",
    "regressor",
    "lag_order",
    "n_obs",
    "sample_start",
    "sample_end",
    "coefficient",
    "standard_error",
    "t_stat",
    "equation_sse",
    "estimate_status",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_7_0_RESIDUAL_COVARIANCE_FIELDNAMES = [
    "covariance_id",
    "row_variable",
    "column_variable",
    "lag_order",
    "n_obs",
    "covariance",
    "correlation",
    "covariance_status",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_7_0_PROXY_SUPPORT_FIELDNAMES = [
    "support_id",
    "target_variable",
    "lag_order",
    "n_obs",
    "sample_start",
    "sample_end",
    "unique_event_years",
    "nonzero_proxy_months",
    "estimator",
    "instrument_variable",
    "first_stage_beta",
    "first_stage_standard_error",
    "first_stage_t_stat",
    "first_stage_f_stat",
    "required_first_stage_f_stat",
    "support_status",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_7_0_TIMING_EXOGENEITY_AUDIT_FIELDNAMES = [
    "audit_id",
    "audit_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_7_0_action",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_7_0_CLAIM_PROMOTION_CONTRACT_FIELDNAMES = [
    "requirement_id",
    "requirement_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "future_opt_in_prerequisite",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "dynamic_identification_promotion_enabled",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_7_0_IDENTIFICATION_DECISION_FIELDNAMES = [
    "decision_id",
    "decision_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_7_0_action",
    "controlled_dynamic_lp_appendix_enabled",
    "reduced_form_system_diagnostics_enabled",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "valuation_incidence_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_7_0_PROXY_SVAR_BLOCKER_FIELDNAMES = [
    "blocker_id",
    "blocker_status",
    "evidence_artifact",
    "blocked_requirements",
    "required_resolution",
    "release_7_0_action",
    "controlled_dynamic_lp_appendix_enabled",
    "reduced_form_system_diagnostics_enabled",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "valuation_incidence_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_8_0_PROXY_SPECIFICATION_AUDIT_FIELDNAMES = [
    "audit_id",
    "proxy_specification",
    "target_variable",
    "lag_order",
    "n_obs",
    "sample_start",
    "sample_end",
    "unique_event_years",
    "nonzero_proxy_months",
    "estimator",
    "instrument_variable",
    "first_stage_beta",
    "first_stage_standard_error",
    "first_stage_t_stat",
    "first_stage_f_stat",
    "required_first_stage_f_stat",
    "audit_status",
    "pre_specified_role",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "dynamic_identification_promotion_enabled",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_8_0_STRUCTURAL_GAP_LEDGER_FIELDNAMES = [
    "gap_id",
    "gap_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_8_0_action",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "dynamic_identification_promotion_enabled",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_8_0_NONPROMOTION_PROOF_FIELDNAMES = [
    "proof_id",
    "proof_status",
    "evidence_artifact",
    "strongest_proxy_specification",
    "strongest_proxy_target",
    "strongest_proxy_f_stat",
    "blocked_requirements",
    "required_resolution",
    "release_8_0_action",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "dynamic_identification_promotion_enabled",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_8_0_IDENTIFICATION_DECISION_FIELDNAMES = [
    "decision_id",
    "decision_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_8_0_action",
    "controlled_dynamic_lp_appendix_enabled",
    "reduced_form_system_diagnostics_enabled",
    "proxy_specification_audit_enabled",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "valuation_incidence_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_9_0_EXTERNAL_PROXY_REGISTRY_FIELDNAMES = [
    "source_id",
    "source_name",
    "source_url",
    "source_status",
    "integration_status",
    "normalized_proxy_column",
    "sample_start",
    "sample_end",
    "n_rows",
    "retrieval_evidence",
    "structural_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_9_0_EXTERNAL_PROXY_SUPPORT_FIELDNAMES = [
    "audit_id",
    "proxy_source",
    "proxy_specification",
    "target_variable",
    "n_obs",
    "sample_start",
    "sample_end",
    "unique_event_years",
    "nonzero_proxy_months",
    "estimator",
    "instrument_variable",
    "first_stage_beta",
    "first_stage_standard_error",
    "first_stage_t_stat",
    "first_stage_f_stat",
    "required_first_stage_f_stat",
    "audit_status",
    "source_status",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "dynamic_identification_promotion_enabled",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_9_0_STRUCTURAL_IDENTIFICATION_DECISION_FIELDNAMES = [
    "decision_id",
    "decision_status",
    "evidence_artifact",
    "observed_value",
    "required_value",
    "release_9_0_action",
    "expanded_external_proxy_frontier_enabled",
    "defensible_structural_appendix_enabled",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "valuation_incidence_claim_enabled",
    "raw_rate_change_identification_rejected",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


RELEASE_9_0_NONPROMOTION_PROOF_FIELDNAMES = [
    "proof_id",
    "proof_status",
    "evidence_artifact",
    "strongest_proxy_source",
    "strongest_proxy_specification",
    "strongest_proxy_target",
    "strongest_proxy_f_stat",
    "blocked_requirements",
    "required_resolution",
    "release_9_0_action",
    "raw_rate_change_identification_rejected",
    "proxy_svar_claim_enabled",
    "system_identification_claim_enabled",
    "dynamic_identification_promotion_enabled",
    "pricing_output_enabled",
    "reset_calendar_construction_enabled",
    "incidence_claim_enabled",
    "notes",
]


def _build_empirical_smoke_rows(snapshot_bundle: Path) -> list[dict[str, object]]:
    snapshots = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in snapshots}
    shock_snapshot = by_series["sf_fed_monetary_policy_surprises"]
    derived = derive_accounting_inputs(snapshots)
    fred_history = {
        series_id: _dated_values(by_series[series_id].records)
        for series_id in ("WRESBAL", "RRPONTSYD", "GDP")
    }
    debt_history = _dated_records(by_series["debt_to_penny"].records, "record_date")
    mspd_history = _mspd_records_by_date(
        by_series.get("treasury_mspd_table_3", shock_snapshot).records
    )
    rows = []
    for record in shock_snapshot.records:
        shock = _decimal(record.get("orthogonalized_surprise_bps"))
        if shock is None:
            continue
        shock_date = _date(str(record["date"]))
        reserves = _latest_at_or_before(fred_history["WRESBAL"], shock_date)
        on_rrp = _latest_at_or_before(fred_history["RRPONTSYD"], shock_date)
        gdp = _latest_at_or_before(fred_history["GDP"], shock_date)
        historical_liabilities = _historical_fed_liabilities_gdp(
            reserves=reserves,
            on_rrp=on_rrp,
            gdp=gdp,
        )
        debt = _latest_record_at_or_before(debt_history, shock_date)
        mspd_asof = _latest_mspd_date_at_or_before(mspd_history, shock_date)
        repricing = (
            _mspd_repricing_for_date(mspd_history[mspd_asof], mspd_asof, debt=debt)
            if mspd_asof is not None
            else None
        )
        latest_public_liability_base = (
            (
                derived.horizons[1].debt_repricing
                + derived.reserves_bil
                + derived.on_rrp_bil
            )
            / derived.gdp_bil
        )
        public_liability_base = _historical_public_liability_base(
            debt=debt,
            repricing=repricing,
            reserves=reserves,
            on_rrp=on_rrp,
            gdp=gdp,
            latest_value=latest_public_liability_base,
        )
        rows.append(
            {
                "date": record["date"],
                "shock_dataset": "sf_fed_monetary_policy_surprises",
                "shock_column": "orthogonalized_surprise_bps",
                "orthogonalized_surprise_bps": shock,
                "public_liability_base_1y_gdp": public_liability_base,
                "repricing_share_1y": (
                    repricing["repricing_share_1y"]
                    if repricing is not None
                    else derived.maturity_ladder[1]["share_of_debt"]
                ),
                "debt_held_public_gdp": _debt_gdp(debt=debt, gdp=gdp),
                "rate_sensitive_fed_liabilities_gdp": historical_liabilities,
                "reserves_asof": _asof(reserves),
                "on_rrp_asof": _asof(on_rrp),
                "gdp_asof": _asof(gdp),
                "debt_asof": _record_asof(debt),
                "mspd_asof": mspd_asof.isoformat() if mspd_asof is not None else "",
                "state_alignment_scope": _state_alignment_scope(
                    reserves=reserves,
                    on_rrp=on_rrp,
                    gdp=gdp,
                ),
                "treasury_repricing_scope": _treasury_repricing_scope(
                    debt=debt, repricing=repricing
                ),
                "design_scope": "smoke_join_no_estimation",
                "guardrail": "not_raw_policy_rate_change",
            }
        )
    return rows


def _write_release_1_1_empirical_artifacts(
    *,
    output: Path,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    report: Path | None,
) -> None:
    tables_dir = output.parent
    reports_dir = report.parent if report is not None else tables_dir.parent / "reports"
    audit_rows = _causal_identification_audit_rows(
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
    )
    blocker_rows = _causal_defensibility_blocker_rows(audit_rows)
    _write_csv(
        tables_dir / "ratewall_causal_identification_audit.csv",
        audit_rows,
        CAUSAL_IDENTIFICATION_AUDIT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_causal_defensibility_blocker.csv",
        blocker_rows,
        CAUSAL_DEFENSIBILITY_BLOCKER_FIELDNAMES,
    )
    manifest_path = tables_dir / "ratewall_empirical_robustness_manifest.json"
    manifest_path.write_text(
        json.dumps(
            _empirical_robustness_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                audit_rows=audit_rows,
                blocker_rows=blocker_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ratewall_causal_identification_appendix.md").write_text(
        _causal_identification_appendix_text(
            audit_rows=audit_rows,
            blocker_rows=blocker_rows,
            result_rows=result_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_reviewer_limitations_memo.md").write_text(
        _reviewer_limitations_memo_text(
            audit_rows=audit_rows,
            blocker_rows=blocker_rows,
            result_rows=result_rows,
        ),
        encoding="utf-8",
    )


def _write_release_2_0_empirical_artifacts(
    *,
    output: Path,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    report: Path | None,
) -> None:
    tables_dir = output.parent
    reports_dir = report.parent if report is not None else tables_dir.parent / "reports"
    support_rows = _event_study_support_diagnostic_rows(panel_rows)
    robustness_rows = _event_study_robustness_rows(panel_rows)
    decision_rows = _submission_identification_decision_rows(
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        support_rows=support_rows,
        robustness_rows=robustness_rows,
    )
    _write_csv(
        tables_dir / "ratewall_event_study_support_diagnostics.csv",
        support_rows,
        EVENT_STUDY_SUPPORT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_event_study_robustness.csv",
        robustness_rows,
        EVENT_STUDY_ROBUSTNESS_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_submission_identification_decision.csv",
        decision_rows,
        SUBMISSION_IDENTIFICATION_DECISION_FIELDNAMES,
    )
    (tables_dir / "ratewall_empirical_robustness_manifest.json").write_text(
        json.dumps(
            _release_2_0_robustness_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                support_rows=support_rows,
                robustness_rows=robustness_rows,
                decision_rows=decision_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ratewall_submission_causal_appendix.md").write_text(
        _submission_causal_appendix_text(
            support_rows=support_rows,
            robustness_rows=robustness_rows,
            decision_rows=decision_rows,
            result_rows=result_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_external_review_response_packet.md").write_text(
        _external_review_response_packet_text(
            support_rows=support_rows,
            robustness_rows=robustness_rows,
            decision_rows=decision_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_submission_appendix_index.md").write_text(
        _submission_appendix_index_text(),
        encoding="utf-8",
    )
    _write_event_study_robustness_figure(
        tables_dir.parent / "figures" / "ratewall_event_study_robustness.svg",
        robustness_rows,
    )


def _write_release_3_0_empirical_artifacts(
    *,
    output: Path,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    report: Path | None,
) -> None:
    tables_dir = output.parent
    reports_dir = report.parent if report is not None else tables_dir.parent / "reports"
    support_rows = _event_study_support_diagnostic_rows(panel_rows)
    robustness_rows = _event_study_robustness_rows(panel_rows)
    submission_rows = _submission_identification_decision_rows(
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        support_rows=support_rows,
        robustness_rows=robustness_rows,
    )
    lp_rows = _dynamic_lp_feasibility_rows(
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        support_rows=support_rows,
        robustness_rows=robustness_rows,
        submission_rows=submission_rows,
    )
    proxy_rows = _proxy_svar_feasibility_rows(
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        support_rows=support_rows,
        robustness_rows=robustness_rows,
    )
    blocker_rows = _dynamic_causal_final_blocker_rows(
        lp_rows=lp_rows,
        proxy_rows=proxy_rows,
    )
    _write_csv(
        tables_dir / "ratewall_dynamic_lp_feasibility_diagnostics.csv",
        lp_rows,
        DYNAMIC_LP_FEASIBILITY_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_proxy_svar_feasibility_diagnostics.csv",
        proxy_rows,
        PROXY_SVAR_FEASIBILITY_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_dynamic_causal_final_blocker.csv",
        blocker_rows,
        DYNAMIC_CAUSAL_FINAL_BLOCKER_FIELDNAMES,
    )
    (tables_dir / "ratewall_empirical_robustness_manifest.json").write_text(
        json.dumps(
            _release_3_0_robustness_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                support_rows=support_rows,
                robustness_rows=robustness_rows,
                submission_rows=submission_rows,
                lp_rows=lp_rows,
                proxy_rows=proxy_rows,
                blocker_rows=blocker_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (tables_dir / "ratewall_journal_submission_manifest.json").write_text(
        json.dumps(
            _journal_submission_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                support_rows=support_rows,
                robustness_rows=robustness_rows,
                lp_rows=lp_rows,
                proxy_rows=proxy_rows,
                blocker_rows=blocker_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ratewall_journal_submission_appendix.md").write_text(
        _journal_submission_appendix_text(
            lp_rows=lp_rows,
            proxy_rows=proxy_rows,
            blocker_rows=blocker_rows,
            support_rows=support_rows,
            robustness_rows=robustness_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_dynamic_causal_blocker_memo.md").write_text(
        _dynamic_causal_blocker_memo_text(
            lp_rows=lp_rows,
            proxy_rows=proxy_rows,
            blocker_rows=blocker_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_referee_response_compendium.md").write_text(
        _referee_response_compendium_text(
            lp_rows=lp_rows,
            proxy_rows=proxy_rows,
            blocker_rows=blocker_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_release_3_0_cover_note.md").write_text(
        _release_3_0_cover_note_text(blocker_rows),
        encoding="utf-8",
    )
    _write_dynamic_causal_gate_figure(
        tables_dir.parent / "figures" / "ratewall_dynamic_causal_gate.svg",
        lp_rows=lp_rows,
        proxy_rows=proxy_rows,
    )


def _write_release_4_0_empirical_artifacts(
    *,
    output: Path,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    report: Path | None,
) -> None:
    tables_dir = output.parent
    reports_dir = report.parent if report is not None else tables_dir.parent / "reports"
    support_rows = _event_study_support_diagnostic_rows(panel_rows)
    robustness_rows = _event_study_robustness_rows(panel_rows)
    submission_rows = _submission_identification_decision_rows(
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        support_rows=support_rows,
        robustness_rows=robustness_rows,
    )
    lp_rows = _dynamic_lp_feasibility_rows(
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        support_rows=support_rows,
        robustness_rows=robustness_rows,
        submission_rows=submission_rows,
    )
    proxy_rows = _proxy_svar_feasibility_rows(
        smoke_rows=smoke_rows,
        panel_rows=panel_rows,
        result_rows=result_rows,
        support_rows=support_rows,
        robustness_rows=robustness_rows,
    )
    release_3_blocker_rows = _dynamic_causal_final_blocker_rows(
        lp_rows=lp_rows,
        proxy_rows=proxy_rows,
    )
    hac_rows = _event_study_hac_diagnostic_rows(panel_rows)
    placebo_rows = _pretrend_placebo_diagnostic_rows(panel_rows)
    contract_rows = _dynamic_identification_promotion_contract_rows(
        lp_rows=lp_rows,
        proxy_rows=proxy_rows,
        hac_rows=hac_rows,
        placebo_rows=placebo_rows,
        result_rows=result_rows,
    )
    release_4_blocker_rows = _release_4_0_dynamic_blocker_rows(
        lp_rows=lp_rows,
        proxy_rows=proxy_rows,
        hac_rows=hac_rows,
        placebo_rows=placebo_rows,
        contract_rows=contract_rows,
    )
    checklist_rows = _release_4_0_submission_checklist_rows(
        result_rows=result_rows,
        hac_rows=hac_rows,
        placebo_rows=placebo_rows,
        contract_rows=contract_rows,
        blocker_rows=release_4_blocker_rows,
    )
    issue_rows = _external_review_issue_matrix_rows(
        hac_rows=hac_rows,
        placebo_rows=placebo_rows,
        contract_rows=contract_rows,
        blocker_rows=release_4_blocker_rows,
    )
    _write_csv(
        tables_dir / "ratewall_event_study_hac_diagnostics.csv",
        hac_rows,
        EVENT_STUDY_HAC_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_pretrend_placebo_diagnostics.csv",
        placebo_rows,
        PRETREND_PLACEBO_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_dynamic_identification_promotion_contract_disabled.csv",
        contract_rows,
        DYNAMIC_IDENTIFICATION_PROMOTION_CONTRACT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_4_0_dynamic_causal_final_blocker.csv",
        release_4_blocker_rows,
        RELEASE_4_0_DYNAMIC_BLOCKER_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_4_0_submission_checklist.csv",
        checklist_rows,
        RELEASE_4_0_SUBMISSION_CHECKLIST_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_external_review_issue_matrix.csv",
        issue_rows,
        EXTERNAL_REVIEW_ISSUE_MATRIX_FIELDNAMES,
    )
    (tables_dir / "ratewall_empirical_robustness_manifest.json").write_text(
        json.dumps(
            _release_4_0_robustness_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                support_rows=support_rows,
                robustness_rows=robustness_rows,
                submission_rows=submission_rows,
                lp_rows=lp_rows,
                proxy_rows=proxy_rows,
                release_3_blocker_rows=release_3_blocker_rows,
                hac_rows=hac_rows,
                placebo_rows=placebo_rows,
                contract_rows=contract_rows,
                release_4_blocker_rows=release_4_blocker_rows,
                checklist_rows=checklist_rows,
                issue_rows=issue_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (tables_dir / "ratewall_release_4_0_submission_manifest.json").write_text(
        json.dumps(
            _release_4_0_submission_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                support_rows=support_rows,
                robustness_rows=robustness_rows,
                lp_rows=lp_rows,
                proxy_rows=proxy_rows,
                hac_rows=hac_rows,
                placebo_rows=placebo_rows,
                contract_rows=contract_rows,
                blocker_rows=release_4_blocker_rows,
                issue_rows=issue_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ratewall_release_4_0_final_submission_memo.md").write_text(
        _release_4_0_final_submission_memo_text(
            hac_rows=hac_rows,
            placebo_rows=placebo_rows,
            contract_rows=contract_rows,
            blocker_rows=release_4_blocker_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_release_4_0_referee_packet.md").write_text(
        _release_4_0_referee_packet_text(
            issue_rows=issue_rows,
            checklist_rows=checklist_rows,
            blocker_rows=release_4_blocker_rows,
        ),
        encoding="utf-8",
    )
    (
        reports_dir / "ratewall_release_4_0_identification_frontier_appendix.md"
    ).write_text(
        _release_4_0_identification_frontier_appendix_text(
            hac_rows=hac_rows,
            placebo_rows=placebo_rows,
            contract_rows=contract_rows,
            issue_rows=issue_rows,
            blocker_rows=release_4_blocker_rows,
        ),
        encoding="utf-8",
    )
    _write_release_4_0_identification_frontier_figure(
        tables_dir.parent / "figures" / "ratewall_release_4_0_identification_frontier.svg",
        contract_rows=contract_rows,
    )


def _write_release_5_0_empirical_artifacts(
    *,
    output: Path,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    report: Path | None,
) -> None:
    tables_dir = output.parent
    reports_dir = report.parent if report is not None else tables_dir.parent / "reports"
    controlled_panel_rows = _controlled_dynamic_lp_panel_rows(panel_rows)
    controlled_result_rows = _controlled_dynamic_lp_result_rows(controlled_panel_rows)
    support_rows = _dynamic_lp_support_rows(controlled_panel_rows)
    decision_rows = _release_5_0_identification_decision_rows(
        controlled_panel_rows=controlled_panel_rows,
        controlled_result_rows=controlled_result_rows,
        support_rows=support_rows,
        result_rows=result_rows,
    )
    proxy_blocker_rows = _release_5_0_proxy_svar_blocker_rows(decision_rows)
    _write_csv(
        tables_dir / "ratewall_controlled_dynamic_lp_panel.csv",
        controlled_panel_rows,
        CONTROLLED_DYNAMIC_LP_PANEL_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_controlled_dynamic_lp_results.csv",
        controlled_result_rows,
        CONTROLLED_DYNAMIC_LP_RESULT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_controlled_dynamic_lp_support_diagnostics.csv",
        support_rows,
        DYNAMIC_LP_SUPPORT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_5_0_identification_decision.csv",
        decision_rows,
        RELEASE_5_0_IDENTIFICATION_DECISION_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_5_0_proxy_svar_final_blocker.csv",
        proxy_blocker_rows,
        RELEASE_5_0_PROXY_SVAR_BLOCKER_FIELDNAMES,
    )
    (tables_dir / "ratewall_empirical_robustness_manifest.json").write_text(
        json.dumps(
            _release_5_0_robustness_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                controlled_panel_rows=controlled_panel_rows,
                controlled_result_rows=controlled_result_rows,
                support_rows=support_rows,
                decision_rows=decision_rows,
                proxy_blocker_rows=proxy_blocker_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (tables_dir / "ratewall_release_5_0_dynamic_causal_manifest.json").write_text(
        json.dumps(
            _release_5_0_dynamic_causal_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                controlled_panel_rows=controlled_panel_rows,
                controlled_result_rows=controlled_result_rows,
                support_rows=support_rows,
                decision_rows=decision_rows,
                proxy_blocker_rows=proxy_blocker_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ratewall_release_5_0_dynamic_lp_appendix.md").write_text(
        _release_5_0_dynamic_lp_appendix_text(
            controlled_result_rows=controlled_result_rows,
            support_rows=support_rows,
            decision_rows=decision_rows,
            proxy_blocker_rows=proxy_blocker_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_release_5_0_referee_response.md").write_text(
        _release_5_0_referee_response_text(
            controlled_result_rows=controlled_result_rows,
            decision_rows=decision_rows,
            proxy_blocker_rows=proxy_blocker_rows,
        ),
        encoding="utf-8",
    )
    _write_release_5_0_dynamic_lp_figure(
        tables_dir.parent / "figures" / "ratewall_release_5_0_dynamic_lp_estimates.svg",
        controlled_result_rows=controlled_result_rows,
    )


def _write_release_6_0_empirical_artifacts(
    *,
    output: Path,
    snapshot_bundle: Path,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    report: Path | None,
) -> None:
    tables_dir = output.parent
    reports_dir = report.parent if report is not None else tables_dir.parent / "reports"
    controlled_panel_rows = _controlled_dynamic_lp_panel_rows(panel_rows)
    controlled_result_rows = _controlled_dynamic_lp_result_rows(controlled_panel_rows)
    controlled_support_rows = _dynamic_lp_support_rows(controlled_panel_rows)
    controlled_decision_rows = _release_5_0_identification_decision_rows(
        controlled_panel_rows=controlled_panel_rows,
        controlled_result_rows=controlled_result_rows,
        support_rows=controlled_support_rows,
        result_rows=result_rows,
    )
    controlled_enabled = _release_6_0_controlled_dynamic_enabled(
        controlled_decision_rows
    )
    system_panel_rows = _proxy_svar_system_panel_rows(
        snapshot_bundle=snapshot_bundle,
        smoke_rows=smoke_rows,
    )
    relevance_rows = _proxy_svar_relevance_rows(system_panel_rows)
    residual_rows = _proxy_svar_residual_rows(system_panel_rows)
    timing_rows = _proxy_svar_timing_support_rows(
        system_panel_rows=system_panel_rows,
        smoke_rows=smoke_rows,
    )
    valuation_frontier_rows = _release_6_0_valuation_frontier_rows()
    decision_rows = _release_6_0_identification_decision_rows(
        system_panel_rows=system_panel_rows,
        relevance_rows=relevance_rows,
        residual_rows=residual_rows,
        timing_rows=timing_rows,
        valuation_frontier_rows=valuation_frontier_rows,
        controlled_dynamic_enabled=controlled_enabled,
    )
    blocker_rows = _release_6_0_proxy_svar_blocker_rows(decision_rows)

    _write_csv(
        tables_dir / "ratewall_proxy_svar_system_panel.csv",
        system_panel_rows,
        PROXY_SVAR_SYSTEM_PANEL_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_proxy_svar_proxy_relevance_diagnostics.csv",
        relevance_rows,
        PROXY_SVAR_RELEVANCE_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_proxy_svar_residual_diagnostics.csv",
        residual_rows,
        PROXY_SVAR_RESIDUAL_DIAGNOSTIC_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_proxy_svar_timing_support_diagnostics.csv",
        timing_rows,
        PROXY_SVAR_TIMING_SUPPORT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_6_0_identification_decision.csv",
        decision_rows,
        RELEASE_6_0_IDENTIFICATION_DECISION_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_6_0_proxy_svar_final_blocker.csv",
        blocker_rows,
        RELEASE_6_0_PROXY_SVAR_BLOCKER_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_6_0_valuation_incidence_frontier_disabled.csv",
        valuation_frontier_rows,
        RELEASE_6_0_VALUATION_FRONTIER_FIELDNAMES,
    )
    (tables_dir / "ratewall_empirical_robustness_manifest.json").write_text(
        json.dumps(
            _release_6_0_robustness_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                controlled_result_rows=controlled_result_rows,
                system_panel_rows=system_panel_rows,
                relevance_rows=relevance_rows,
                residual_rows=residual_rows,
                timing_rows=timing_rows,
                decision_rows=decision_rows,
                blocker_rows=blocker_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (tables_dir / "ratewall_release_6_0_system_identification_manifest.json").write_text(
        json.dumps(
            _release_6_0_system_identification_manifest(
                controlled_dynamic_enabled=controlled_enabled,
                system_panel_rows=system_panel_rows,
                relevance_rows=relevance_rows,
                residual_rows=residual_rows,
                timing_rows=timing_rows,
                decision_rows=decision_rows,
                blocker_rows=blocker_rows,
                valuation_frontier_rows=valuation_frontier_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ratewall_release_6_0_proxy_svar_system_appendix.md").write_text(
        _release_6_0_proxy_svar_system_appendix_text(
            system_panel_rows=system_panel_rows,
            relevance_rows=relevance_rows,
            residual_rows=residual_rows,
            timing_rows=timing_rows,
            decision_rows=decision_rows,
            blocker_rows=blocker_rows,
            valuation_frontier_rows=valuation_frontier_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_release_6_0_reviewer_response.md").write_text(
        _release_6_0_reviewer_response_text(
            relevance_rows=relevance_rows,
            residual_rows=residual_rows,
            timing_rows=timing_rows,
            decision_rows=decision_rows,
            blocker_rows=blocker_rows,
        ),
        encoding="utf-8",
    )
    _write_release_6_0_system_gate_figure(
        tables_dir.parent
        / "figures"
        / "ratewall_release_6_0_system_identification_gate.svg",
        decision_rows=decision_rows,
    )


def _write_release_7_0_empirical_artifacts(
    *,
    output: Path,
    snapshot_bundle: Path,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    report: Path | None,
) -> None:
    tables_dir = output.parent
    reports_dir = report.parent if report is not None else tables_dir.parent / "reports"
    controlled_panel_rows = _controlled_dynamic_lp_panel_rows(panel_rows)
    controlled_result_rows = _controlled_dynamic_lp_result_rows(controlled_panel_rows)
    controlled_support_rows = _dynamic_lp_support_rows(controlled_panel_rows)
    controlled_decision_rows = _release_5_0_identification_decision_rows(
        controlled_panel_rows=controlled_panel_rows,
        controlled_result_rows=controlled_result_rows,
        support_rows=controlled_support_rows,
        result_rows=result_rows,
    )
    controlled_enabled = _release_6_0_controlled_dynamic_enabled(
        controlled_decision_rows
    )
    system_panel_rows = _proxy_svar_system_panel_rows(
        snapshot_bundle=snapshot_bundle,
        smoke_rows=smoke_rows,
    )
    variables = _release_7_0_system_variables()
    lag_rows, selected_lag = _release_7_0_var_lag_selection_rows(
        system_panel_rows, variables=variables
    )
    selected_estimates = _release_7_0_var_equation_estimates(
        system_panel_rows,
        variables=variables,
        lag_order=selected_lag,
    )
    estimate_rows = _release_7_0_reduced_form_estimate_rows(
        selected_estimates, variables=variables, lag_order=selected_lag
    )
    covariance_rows = _release_7_0_residual_covariance_rows(
        selected_estimates, variables=variables, lag_order=selected_lag
    )
    proxy_support_rows = _release_7_0_proxy_support_rows(
        system_panel_rows=system_panel_rows,
        selected_estimates=selected_estimates,
        lag_order=selected_lag,
    )
    timing_audit_rows = _release_7_0_timing_exogeneity_audit_rows(
        system_panel_rows=system_panel_rows,
        lag_rows=lag_rows,
        estimate_rows=estimate_rows,
        covariance_rows=covariance_rows,
        proxy_support_rows=proxy_support_rows,
    )
    promotion_contract_rows = _release_7_0_claim_promotion_contract_rows(
        lag_rows=lag_rows,
        estimate_rows=estimate_rows,
        covariance_rows=covariance_rows,
        proxy_support_rows=proxy_support_rows,
        timing_audit_rows=timing_audit_rows,
    )
    decision_rows = _release_7_0_identification_decision_rows(
        lag_rows=lag_rows,
        estimate_rows=estimate_rows,
        covariance_rows=covariance_rows,
        proxy_support_rows=proxy_support_rows,
        timing_audit_rows=timing_audit_rows,
        promotion_contract_rows=promotion_contract_rows,
        controlled_dynamic_enabled=controlled_enabled,
    )
    blocker_rows = _release_7_0_proxy_svar_blocker_rows(decision_rows)

    _write_csv(
        tables_dir / "ratewall_release_7_0_var_lag_selection.csv",
        lag_rows,
        RELEASE_7_0_VAR_LAG_SELECTION_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_7_0_reduced_form_system_estimates.csv",
        estimate_rows,
        RELEASE_7_0_REDUCED_FORM_ESTIMATE_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_7_0_residual_covariance.csv",
        covariance_rows,
        RELEASE_7_0_RESIDUAL_COVARIANCE_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_7_0_proxy_relevance_support.csv",
        proxy_support_rows,
        RELEASE_7_0_PROXY_SUPPORT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv",
        timing_audit_rows,
        RELEASE_7_0_TIMING_EXOGENEITY_AUDIT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_7_0_claim_promotion_contract_disabled.csv",
        promotion_contract_rows,
        RELEASE_7_0_CLAIM_PROMOTION_CONTRACT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_7_0_identification_decision.csv",
        decision_rows,
        RELEASE_7_0_IDENTIFICATION_DECISION_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_7_0_proxy_svar_final_blocker.csv",
        blocker_rows,
        RELEASE_7_0_PROXY_SVAR_BLOCKER_FIELDNAMES,
    )
    (tables_dir / "ratewall_empirical_robustness_manifest.json").write_text(
        json.dumps(
            _release_7_0_robustness_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                lag_rows=lag_rows,
                estimate_rows=estimate_rows,
                covariance_rows=covariance_rows,
                proxy_support_rows=proxy_support_rows,
                timing_audit_rows=timing_audit_rows,
                promotion_contract_rows=promotion_contract_rows,
                decision_rows=decision_rows,
                blocker_rows=blocker_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (tables_dir / "ratewall_release_7_0_system_identification_manifest.json").write_text(
        json.dumps(
            _release_7_0_system_identification_manifest(
                controlled_dynamic_enabled=controlled_enabled,
                lag_rows=lag_rows,
                estimate_rows=estimate_rows,
                covariance_rows=covariance_rows,
                proxy_support_rows=proxy_support_rows,
                timing_audit_rows=timing_audit_rows,
                promotion_contract_rows=promotion_contract_rows,
                decision_rows=decision_rows,
                blocker_rows=blocker_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ratewall_release_7_0_system_identification_appendix.md").write_text(
        _release_7_0_system_identification_appendix_text(
            lag_rows=lag_rows,
            estimate_rows=estimate_rows,
            covariance_rows=covariance_rows,
            proxy_support_rows=proxy_support_rows,
            timing_audit_rows=timing_audit_rows,
            promotion_contract_rows=promotion_contract_rows,
            decision_rows=decision_rows,
            blocker_rows=blocker_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_release_7_0_external_review_packet.md").write_text(
        _release_7_0_external_review_packet_text(
            proxy_support_rows=proxy_support_rows,
            timing_audit_rows=timing_audit_rows,
            promotion_contract_rows=promotion_contract_rows,
            decision_rows=decision_rows,
            blocker_rows=blocker_rows,
        ),
        encoding="utf-8",
    )
    _write_release_7_0_system_frontier_figure(
        tables_dir.parent
        / "figures"
        / "ratewall_release_7_0_system_identification_frontier.svg",
        decision_rows=decision_rows,
    )


def _write_release_8_0_empirical_artifacts(
    *,
    output: Path,
    snapshot_bundle: Path,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    report: Path | None,
) -> None:
    tables_dir = output.parent
    reports_dir = report.parent if report is not None else tables_dir.parent / "reports"
    controlled_panel_rows = _controlled_dynamic_lp_panel_rows(panel_rows)
    controlled_result_rows = _controlled_dynamic_lp_result_rows(controlled_panel_rows)
    controlled_support_rows = _dynamic_lp_support_rows(controlled_panel_rows)
    controlled_decision_rows = _release_5_0_identification_decision_rows(
        controlled_panel_rows=controlled_panel_rows,
        controlled_result_rows=controlled_result_rows,
        support_rows=controlled_support_rows,
        result_rows=result_rows,
    )
    controlled_enabled = _release_6_0_controlled_dynamic_enabled(
        controlled_decision_rows
    )
    system_panel_rows = _proxy_svar_system_panel_rows(
        snapshot_bundle=snapshot_bundle,
        smoke_rows=smoke_rows,
    )
    variables = _release_7_0_system_variables()
    lag_rows, selected_lag = _release_7_0_var_lag_selection_rows(
        system_panel_rows, variables=variables
    )
    selected_estimates = _release_7_0_var_equation_estimates(
        system_panel_rows,
        variables=variables,
        lag_order=selected_lag,
    )
    estimate_rows = _release_7_0_reduced_form_estimate_rows(
        selected_estimates, variables=variables, lag_order=selected_lag
    )
    covariance_rows = _release_7_0_residual_covariance_rows(
        selected_estimates, variables=variables, lag_order=selected_lag
    )
    proxy_support_rows = _release_7_0_proxy_support_rows(
        system_panel_rows=system_panel_rows,
        selected_estimates=selected_estimates,
        lag_order=selected_lag,
    )
    timing_audit_rows = _release_7_0_timing_exogeneity_audit_rows(
        system_panel_rows=system_panel_rows,
        lag_rows=lag_rows,
        estimate_rows=estimate_rows,
        covariance_rows=covariance_rows,
        proxy_support_rows=proxy_support_rows,
    )
    proxy_spec_rows = _release_8_0_proxy_specification_audit_rows(
        system_panel_rows=system_panel_rows,
        selected_estimates=selected_estimates,
        lag_order=selected_lag,
    )
    structural_gap_rows = _release_8_0_structural_gap_rows(
        lag_rows=lag_rows,
        estimate_rows=estimate_rows,
        covariance_rows=covariance_rows,
        proxy_support_rows=proxy_support_rows,
        timing_audit_rows=timing_audit_rows,
        proxy_spec_rows=proxy_spec_rows,
    )
    decision_rows = _release_8_0_identification_decision_rows(
        controlled_dynamic_enabled=controlled_enabled,
        lag_rows=lag_rows,
        estimate_rows=estimate_rows,
        structural_gap_rows=structural_gap_rows,
        proxy_spec_rows=proxy_spec_rows,
    )
    proof_rows = _release_8_0_nonpromotion_proof_rows(
        decision_rows=decision_rows,
        structural_gap_rows=structural_gap_rows,
        proxy_spec_rows=proxy_spec_rows,
    )

    _write_csv(
        tables_dir / "ratewall_release_8_0_proxy_specification_audit.csv",
        proxy_spec_rows,
        RELEASE_8_0_PROXY_SPECIFICATION_AUDIT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_8_0_structural_gap_ledger.csv",
        structural_gap_rows,
        RELEASE_8_0_STRUCTURAL_GAP_LEDGER_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_8_0_nonpromotion_proof.csv",
        proof_rows,
        RELEASE_8_0_NONPROMOTION_PROOF_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_8_0_identification_decision.csv",
        decision_rows,
        RELEASE_8_0_IDENTIFICATION_DECISION_FIELDNAMES,
    )
    (tables_dir / "ratewall_empirical_robustness_manifest.json").write_text(
        json.dumps(
            _release_8_0_robustness_manifest(
                smoke_rows=smoke_rows,
                panel_rows=panel_rows,
                result_rows=result_rows,
                proxy_spec_rows=proxy_spec_rows,
                structural_gap_rows=structural_gap_rows,
                proof_rows=proof_rows,
                decision_rows=decision_rows,
                lag_rows=lag_rows,
                estimate_rows=estimate_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (tables_dir / "ratewall_release_8_0_system_identification_manifest.json").write_text(
        json.dumps(
            _release_8_0_system_identification_manifest(
                controlled_dynamic_enabled=controlled_enabled,
                lag_rows=lag_rows,
                estimate_rows=estimate_rows,
                proxy_spec_rows=proxy_spec_rows,
                structural_gap_rows=structural_gap_rows,
                proof_rows=proof_rows,
                decision_rows=decision_rows,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ratewall_release_8_0_system_nonpromotion_appendix.md").write_text(
        _release_8_0_nonpromotion_appendix_text(
            proxy_spec_rows=proxy_spec_rows,
            structural_gap_rows=structural_gap_rows,
            proof_rows=proof_rows,
            decision_rows=decision_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_release_8_0_reviewer_response.md").write_text(
        _release_8_0_reviewer_response_text(
            proxy_spec_rows=proxy_spec_rows,
            structural_gap_rows=structural_gap_rows,
            proof_rows=proof_rows,
            decision_rows=decision_rows,
        ),
        encoding="utf-8",
    )
    _write_release_8_0_nonpromotion_figure(
        tables_dir.parent / "figures" / "ratewall_release_8_0_nonpromotion_gate.svg",
        decision_rows=decision_rows,
    )


def _write_release_9_0_empirical_artifacts(
    *,
    output: Path,
    snapshot_bundle: Path,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    report: Path | None,
) -> None:
    tables_dir = output.parent
    reports_dir = report.parent if report is not None else tables_dir.parent / "reports"
    system_panel_rows = _proxy_svar_system_panel_rows(
        snapshot_bundle=snapshot_bundle,
        smoke_rows=smoke_rows,
    )
    variables = _release_7_0_system_variables()
    lag_rows, selected_lag = _release_7_0_var_lag_selection_rows(
        system_panel_rows, variables=variables
    )
    selected_estimates = _release_7_0_var_equation_estimates(
        system_panel_rows,
        variables=variables,
        lag_order=selected_lag,
    )
    registry_rows = _release_9_0_external_proxy_registry_rows(snapshot_bundle)
    support_rows = _release_9_0_external_proxy_support_rows(
        snapshot_bundle=snapshot_bundle,
        system_panel_rows=system_panel_rows,
        selected_estimates=selected_estimates,
        lag_order=selected_lag,
    )
    decision_rows = _release_9_0_structural_identification_decision_rows(
        registry_rows=registry_rows,
        support_rows=support_rows,
    )
    proof_rows = _release_9_0_nonpromotion_proof_rows(
        decision_rows=decision_rows,
        support_rows=support_rows,
    )

    _write_csv(
        tables_dir / "ratewall_release_9_0_external_proxy_source_registry.csv",
        registry_rows,
        RELEASE_9_0_EXTERNAL_PROXY_REGISTRY_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_9_0_external_proxy_support_audit.csv",
        support_rows,
        RELEASE_9_0_EXTERNAL_PROXY_SUPPORT_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_9_0_structural_identification_decision.csv",
        decision_rows,
        RELEASE_9_0_STRUCTURAL_IDENTIFICATION_DECISION_FIELDNAMES,
    )
    _write_csv(
        tables_dir / "ratewall_release_9_0_final_nonpromotion_proof.csv",
        proof_rows,
        RELEASE_9_0_NONPROMOTION_PROOF_FIELDNAMES,
    )
    (tables_dir / "ratewall_release_9_0_structural_identification_manifest.json").write_text(
        json.dumps(
            _release_9_0_structural_identification_manifest(
                registry_rows=registry_rows,
                support_rows=support_rows,
                decision_rows=decision_rows,
                proof_rows=proof_rows,
                lag_order=selected_lag,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ratewall_release_9_0_structural_boundary_appendix.md").write_text(
        _release_9_0_structural_boundary_appendix_text(
            registry_rows=registry_rows,
            support_rows=support_rows,
            decision_rows=decision_rows,
            proof_rows=proof_rows,
        ),
        encoding="utf-8",
    )
    (reports_dir / "ratewall_release_9_0_external_proxy_review_packet.md").write_text(
        _release_9_0_review_packet_text(
            registry_rows=registry_rows,
            support_rows=support_rows,
            decision_rows=decision_rows,
            proof_rows=proof_rows,
        ),
        encoding="utf-8",
    )
    _write_release_9_0_boundary_figure(
        tables_dir.parent / "figures" / "ratewall_release_9_0_structural_boundary.svg",
        decision_rows=decision_rows,
    )


def _release_6_0_controlled_dynamic_enabled(
    decision_rows: list[dict[str, object]],
) -> bool:
    return any(
        row.get("decision_id") == "release_5_0_identification_decision"
        and row.get("controlled_dynamic_lp_appendix_enabled") == "true"
        for row in decision_rows
    )


def _proxy_svar_system_panel_rows(
    *,
    snapshot_bundle: Path,
    smoke_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    snapshots = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in snapshots}
    required_series = ("PCEPILFE", "INDPRO", "UNRATE", "FEDFUNDS")
    if not all(series_id in by_series for series_id in required_series):
        return []
    monthly = {
        series_id: _monthly_series_values(by_series[series_id].records)
        for series_id in required_series
    }
    start_candidates = [
        min(values) for values in monthly.values() if values
    ]
    end_candidates = [
        max(values) for values in monthly.values() if values
    ]
    if not start_candidates or not end_candidates:
        return []
    start = max(start_candidates)
    end = min(end_candidates)
    shock_by_month = _shock_month_summaries(smoke_rows)
    state_by_month = _state_month_summaries(smoke_rows)
    rows: list[dict[str, object]] = []
    current = start
    while current <= end:
        pce = _latest_month_value_at_or_before(monthly["PCEPILFE"], current)
        pce_lag = _latest_month_value_at_or_before(
            monthly["PCEPILFE"], _add_months(current, -3)
        )
        indpro = _latest_month_value_at_or_before(monthly["INDPRO"], current)
        indpro_lag = _latest_month_value_at_or_before(
            monthly["INDPRO"], _add_months(current, -3)
        )
        unrate = _latest_month_value_at_or_before(monthly["UNRATE"], current)
        fed = _latest_month_value_at_or_before(monthly["FEDFUNDS"], current)
        fed_lag = _latest_month_value_at_or_before(
            monthly["FEDFUNDS"], _add_months(current, -1)
        )
        state = _latest_state_at_or_before_month(state_by_month, current)
        required_values = (
            pce,
            pce_lag,
            indpro,
            indpro_lag,
            unrate,
            fed,
            fed_lag,
            state,
        )
        if all(value is not None for value in required_values):
            shock = shock_by_month.get(current, {"shock_bps": 0.0, "count": 0})
            pce_change = _annualized_change(float(pce), float(pce_lag), 3)
            indpro_change = _annualized_change(float(indpro), float(indpro_lag), 3)
            rows.append(
                {
                    "month": current.isoformat(),
                    "core_pce_inflation_3m_annualized": f"{pce_change:.6f}",
                    "industrial_production_growth_3m_annualized": (
                        f"{indpro_change:.6f}"
                    ),
                    "unemployment_rate": f"{float(unrate):.6f}",
                    "fed_funds_rate": f"{float(fed):.6f}",
                    "fed_funds_rate_change": f"{(float(fed) - float(fed_lag)):.6f}",
                    "sf_fed_proxy_shock_bps": f"{float(shock['shock_bps']):.6f}",
                    "proxy_event_count": int(shock["count"]),
                    "public_liability_base_1y_gdp": (
                        f"{float(state['public_liability_base_1y_gdp']):.6f}"
                    ),
                    "repricing_share_1y": f"{float(state['repricing_share_1y']):.6f}",
                    "debt_held_public_gdp": (
                        f"{float(state['debt_held_public_gdp']):.6f}"
                    ),
                    "rate_sensitive_fed_liabilities_gdp": (
                        f"{float(state['rate_sensitive_fed_liabilities_gdp']):.6f}"
                    ),
                    "state_alignment_scope": state["state_alignment_scope"],
                    "system_variable_count": 8,
                    "panel_status": "source_backed_system_panel_row_not_proxy_svar",
                    "raw_rate_change_identification_rejected": "true",
                    "proxy_svar_claim_enabled": "false",
                    "pricing_output_enabled": "false",
                    "incidence_claim_enabled": "false",
                    "notes": (
                        "Monthly source-backed system row. FEDFUNDS is a system "
                        "policy variable for diagnostics, not the monetary shock."
                    ),
                }
            )
        current = _add_months(current, 1)
    return rows


def _proxy_svar_relevance_rows(
    system_panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    observations = []
    for row in system_panel_rows:
        if int(row["proxy_event_count"]) <= 0:
            continue
        proxy = _float(row.get("sf_fed_proxy_shock_bps"))
        policy_change = _float(row.get("fed_funds_rate_change"))
        if proxy is None or policy_change is None:
            continue
        observations.append((str(row["month"]), proxy / 100.0, policy_change))
    xs = [proxy for _month, proxy, _policy in observations]
    ys = [policy for _month, _proxy, policy in observations]
    beta, se, t_stat = _ols_slope(xs, ys)
    n_obs = len(observations)
    years = {month[:4] for month, _proxy, _policy in observations}
    enough_support = n_obs >= 30 and len(years) >= 8 and _std(xs) > 0 and _std(ys) > 0
    status = (
        "proxy_relevance_diagnostic_enabled_not_proxy_svar"
        if enough_support
        else "proxy_relevance_blocked_insufficient_system_support"
    )
    return [
        {
            "diagnostic_id": "sf_fed_proxy_to_policy_system_relevance",
            "n_obs": n_obs,
            "sample_start": min((month for month, _x, _y in observations), default=""),
            "sample_end": max((month for month, _x, _y in observations), default=""),
            "unique_event_years": len(years),
            "nonzero_proxy_months": sum(abs(value) > 0 for value in xs),
            "estimator": "diagnostic_ols_first_stage_not_identification",
            "dependent_variable": "fed_funds_rate_change_system_variable",
            "instrument_variable": "sf_fed_orthogonalized_surprise_100bp",
            "first_stage_beta": f"{beta:.6f}" if observations else "",
            "first_stage_standard_error": f"{se:.6f}" if observations else "",
            "first_stage_t_stat": f"{t_stat:.6f}" if observations else "",
            "proxy_shock_std": f"{_std(xs):.6f}" if observations else "",
            "policy_change_std": f"{_std(ys):.6f}" if observations else "",
            "diagnostic_status": status,
            "required_value": (
                "audited external-instrument relevance with sufficient event "
                "months, stable timing, and system residual diagnostics"
            ),
            "proxy_svar_claim_enabled": "false",
            "raw_rate_change_identification_rejected": "true",
            "pricing_output_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "This is a proxy relevance diagnostic. It does not identify a "
                "monetary shock from raw rate changes."
            ),
        }
    ]


def _proxy_svar_residual_rows(
    system_panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    variables = [
        "core_pce_inflation_3m_annualized",
        "industrial_production_growth_3m_annualized",
        "unemployment_rate",
        "fed_funds_rate",
        "public_liability_base_1y_gdp",
    ]
    rows: list[dict[str, object]] = []
    for variable in variables:
        observations = [
            (str(row["month"]), _float(row.get(variable)))
            for row in system_panel_rows
            if _float(row.get(variable)) is not None
        ]
        values = [float(value) for _month, value in observations if value is not None]
        months = [month for month, value in observations if value is not None]
        if len(values) < 12:
            rows.append(
                _proxy_svar_residual_row(
                    variable,
                    len(values),
                    min(months, default=""),
                    max(months, default=""),
                    "",
                    "",
                    "",
                    "residual_diagnostic_blocked_insufficient_monthly_support",
                )
            )
            continue
        y_values = values[1:]
        lag_values = values[:-1]
        beta, _se, _t_stat = _ols_slope(lag_values, y_values)
        alpha = _mean(y_values) - beta * _mean(lag_values)
        residuals = [
            y_value - alpha - beta * lag_value
            for y_value, lag_value in zip(y_values, lag_values)
        ]
        autocorr = (
            _correlation(residuals[1:], residuals[:-1])
            if len(residuals) >= 3
            else 0.0
        )
        rows.append(
            _proxy_svar_residual_row(
                variable,
                len(values),
                min(months),
                max(months),
                f"{beta:.6f}",
                f"{_std(residuals):.6f}",
                f"{autocorr:.6f}",
                "var_lite_residual_diagnostic_not_proxy_svar",
            )
        )
    return rows


def _proxy_svar_residual_row(
    variable: str,
    n_obs: int,
    sample_start: str,
    sample_end: str,
    ar1: str,
    residual_std: str,
    autocorr: str,
    status: str,
) -> dict[str, object]:
    return {
        "diagnostic_id": f"system_residual_{variable}",
        "system_variable": variable,
        "n_obs": n_obs,
        "sample_start": sample_start,
        "sample_end": sample_end,
        "estimator": "single_equation_ar1_residual_check_not_var_system",
        "ar1_coefficient": ar1,
        "residual_std": residual_std,
        "lag1_residual_autocorrelation": autocorr,
        "diagnostic_status": status,
        "required_value": (
            "estimated reduced-form VAR system with audited lag order, "
            "residual covariance, and invertibility diagnostics"
        ),
        "proxy_svar_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": (
            "Validation-only residual evidence. A univariate AR check is not a "
            "proxy-SVAR reduced-form system."
        ),
    }


def _proxy_svar_timing_support_rows(
    *,
    system_panel_rows: list[dict[str, object]],
    smoke_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    system_months = {str(row["month"]) for row in system_panel_rows}
    event_months = {
        _month_start(_date(str(row["date"]))).isoformat()
        for row in smoke_rows
        if row.get("date")
    }
    missing = sorted(event_months - system_months)
    enough_support = len(event_months) >= 30 and not missing
    return [
        {
            "diagnostic_id": "proxy_svar_timing_support",
            "n_system_months": len(system_months),
            "n_proxy_event_months": len(event_months),
            "n_event_months_missing_system": len(missing),
            "monthly_sample_start": min(system_months, default=""),
            "monthly_sample_end": max(system_months, default=""),
            "proxy_sample_start": min(event_months, default=""),
            "proxy_sample_end": max(event_months, default=""),
            "timing_status": (
                "timing_support_diagnostic_enabled_not_invertibility_proof"
                if enough_support
                else "timing_support_blocked_or_too_thin"
            ),
            "required_value": (
                "event-time proxy alignment plus audited recursive timing, "
                "invertibility, and exogeneity assumptions"
            ),
            "proxy_svar_claim_enabled": "false",
            "raw_rate_change_identification_rejected": "true",
            "pricing_output_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "Calendar support is necessary but not sufficient for a "
                "proxy-SVAR identification claim."
            ),
        }
    ]


def _release_6_0_valuation_frontier_rows() -> list[dict[str, object]]:
    base = {
        "pricing_output_enabled": "false",
        "holder_bridge_enabled": "false",
        "tax_assumptions_enabled": "false",
        "mpc_assumptions_enabled": "false",
        "welfare_incidence_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "release_6_0_action": "keep_frontier_disabled_fail_closed",
    }
    rows = [
        (
            "valuation_pricing_frontier",
            "disabled_missing_final_pricing_opt_in",
            "outputs/tables/treasury_valuation_engine_readiness_gate.csv",
            "audited pricing engine, reset calendars, FRN/TIPS conventions, and tests",
            "explicit_pricing_authorization_enabled",
        ),
        (
            "holder_incidence_frontier",
            "disabled_missing_holder_bridge_tax_mpc_welfare_opt_in",
            "outputs/tables/holder_allocation_design_ledger_disabled.csv",
            "legal-holder to final-owner bridge plus tax, MPC, and welfare method",
            "holder_bridge_enabled;tax_assumptions_enabled;mpc_assumptions_enabled;welfare_incidence_enabled",
        ),
        (
            "reset_calendar_frontier",
            "disabled_missing_official_recurring_reset_calendar_source",
            "outputs/tables/treasury_frn_reset_method_frontier_ledger.csv",
            "official machine-readable recurring reset-calendar method and coverage",
            "reset_calendar_construction_enabled",
        ),
    ]
    return [
        {
            **base,
            "frontier_id": frontier_id,
            "frontier_status": status,
            "evidence_artifact": artifact,
            "required_source_method": required,
            "explicit_opt_in_switches": switches,
            "notes": (
                "Release 6.0 audits the optional valuation/incidence frontier "
                "but emits no pricing, allocation, welfare, or incidence output."
            ),
        }
        for frontier_id, status, artifact, required, switches in rows
    ]


def _release_6_0_identification_decision_rows(
    *,
    system_panel_rows: list[dict[str, object]],
    relevance_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    timing_rows: list[dict[str, object]],
    valuation_frontier_rows: list[dict[str, object]],
    controlled_dynamic_enabled: bool,
) -> list[dict[str, object]]:
    system_ready = len(system_panel_rows) >= 120
    relevance_status = relevance_rows[0]["diagnostic_status"] if relevance_rows else ""
    residual_ready = bool(residual_rows) and all(
        row["diagnostic_status"] == "var_lite_residual_diagnostic_not_proxy_svar"
        for row in residual_rows
    )
    timing_status = timing_rows[0]["timing_status"] if timing_rows else ""
    valuation_disabled = bool(valuation_frontier_rows) and all(
        row["pricing_output_enabled"] == "false"
        and row["incidence_claim_enabled"] == "false"
        for row in valuation_frontier_rows
    )
    return [
        _release_6_decision_row(
            "source_backed_system_panel",
            "diagnostic_enabled_not_proxy_svar" if system_ready else "blocked",
            "outputs/tables/ratewall_proxy_svar_system_panel.csv",
            f"system_months={len(system_panel_rows)}",
            "at least 120 monthly source-backed system rows",
            "use_as_system_support_diagnostic_only",
            controlled_dynamic_enabled,
            "Monthly panel is useful for review, but it is not a proxy-SVAR.",
        ),
        _release_6_decision_row(
            "external_proxy_relevance",
            relevance_status or "blocked",
            "outputs/tables/ratewall_proxy_svar_proxy_relevance_diagnostics.csv",
            _release_6_relevance_observed(relevance_rows),
            "proxy relevance plus sufficient event support",
            "use_as_proxy_relevance_diagnostic_only",
            controlled_dynamic_enabled,
            "The SF Fed surprise remains the admissible proxy; raw rates remain rejected.",
        ),
        _release_6_decision_row(
            "reduced_form_system_residuals",
            "diagnostic_enabled_not_proxy_svar" if residual_ready else "blocked",
            "outputs/tables/ratewall_proxy_svar_residual_diagnostics.csv",
            f"residual_rows={len(residual_rows)}",
            "estimated multivariate reduced-form VAR residual system",
            "keep_proxy_svar_claim_disabled",
            controlled_dynamic_enabled,
            "Univariate AR residual checks do not satisfy the reduced-form system requirement.",
        ),
        _release_6_decision_row(
            "timing_invertibility_exogeneity",
            "blocked",
            "outputs/tables/ratewall_proxy_svar_timing_support_diagnostics.csv",
            timing_status or "no_timing_rows",
            "audited timing, invertibility, and exogeneity assumptions",
            "keep_proxy_svar_claim_disabled",
            controlled_dynamic_enabled,
            "Calendar support is not a proof of proxy-SVAR timing or invertibility.",
        ),
        _release_6_decision_row(
            "valuation_incidence_frontier",
            "disabled_fail_closed" if valuation_disabled else "blocked",
            "outputs/tables/ratewall_release_6_0_valuation_incidence_frontier_disabled.csv",
            f"disabled_frontier_rows={len(valuation_frontier_rows)}",
            "explicit pricing, holder bridge, tax, MPC, welfare, and reset-calendar opt-ins",
            "keep_valuation_incidence_frontier_disabled",
            controlled_dynamic_enabled,
            "Release 6.0 adds a frontier audit only; no valuation/incidence output is enabled.",
        ),
        _release_6_decision_row(
            "release_6_0_identification_decision",
            "proxy_svar_system_blocked_bounded_dynamic_lp_retained",
            "outputs/tables/ratewall_release_6_0_proxy_svar_final_blocker.csv",
            (
                f"system_ready={system_ready};residual_ready={residual_ready};"
                f"controlled_dynamic_enabled={controlled_dynamic_enabled}"
            ),
            "full proxy-SVAR/system identification or final blocker",
            "publish_release_6_0_system_blocker_with_bounded_dynamic_lp",
            controlled_dynamic_enabled,
            "This is the maximum defensible Release 6.0 empirical claim.",
        ),
    ]


def _release_6_relevance_observed(
    relevance_rows: list[dict[str, object]],
) -> str:
    if not relevance_rows:
        return "relevance_rows=0"
    row = relevance_rows[0]
    return (
        f"n_obs={row['n_obs']};unique_event_years={row['unique_event_years']};"
        f"first_stage_t_stat={row['first_stage_t_stat']}"
    )


def _release_6_decision_row(
    decision_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    action: str,
    controlled_dynamic_enabled: bool,
    notes: str,
) -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "decision_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_6_0_action": action,
        "controlled_dynamic_lp_appendix_enabled": str(controlled_dynamic_enabled).lower(),
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "valuation_incidence_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_6_0_proxy_svar_blocker_rows(
    decision_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    blocked = [
        str(row["decision_id"])
        for row in decision_rows
        if str(row["decision_status"]).startswith("blocked")
        or row["decision_status"] == "disabled_fail_closed"
    ]
    required = [
        f"{row['decision_id']}={row['required_value']}"
        for row in decision_rows
        if row["decision_id"] in blocked
    ]
    controlled_enabled = any(
        row.get("controlled_dynamic_lp_appendix_enabled") == "true"
        for row in decision_rows
    )
    return [
        {
            "blocker_id": "release_6_0_proxy_svar_system_final_blocker",
            "blocker_status": (
                "proxy_svar_system_blocked_bounded_dynamic_lp_retained"
            ),
            "evidence_artifact": (
                "outputs/tables/ratewall_release_6_0_identification_decision.csv"
            ),
            "blocked_requirements": ";".join(blocked),
            "required_resolution": "; ".join(required),
            "release_6_0_action": (
                "publish_source_backed_system_diagnostics_keep_proxy_svar_disabled"
            ),
            "controlled_dynamic_lp_appendix_enabled": str(controlled_enabled).lower(),
            "proxy_svar_claim_enabled": "false",
            "system_identification_claim_enabled": "false",
            "valuation_incidence_claim_enabled": "false",
            "raw_rate_change_identification_rejected": "true",
            "pricing_output_enabled": "false",
            "reset_calendar_construction_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "Release 6.0 strengthens the system-identification evidence "
                "surface but preserves Release 5.0 as bounded dynamic-LP evidence "
                "rather than claiming proxy-SVAR/system identification."
            ),
        }
    ]


def _release_6_0_robustness_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    controlled_result_rows: list[dict[str, object]],
    system_panel_rows: list[dict[str, object]],
    relevance_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    timing_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.empirical_robustness_manifest.v6",
        "release": "6.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "controlled_dynamic_lp_result_rows": len(controlled_result_rows),
        "proxy_svar_system_panel_rows": len(system_panel_rows),
        "proxy_svar_relevance_rows": len(relevance_rows),
        "proxy_svar_residual_diagnostic_rows": len(residual_rows),
        "proxy_svar_timing_support_rows": len(timing_rows),
        "release_6_0_decision_rows": len(decision_rows),
        "release_6_0_proxy_svar_final_blocker_rows": len(blocker_rows),
        "release_6_0_decision_status_counts": _count_by(
            decision_rows, "decision_status"
        ),
        "proxy_svar_claim_enabled": False,
        "system_identification_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "causal_claim_enabled": False,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "reset_calendar_construction_enabled": False,
        "release_6_0_decision": (
            "proxy_svar_system_blocked_bounded_dynamic_lp_retained"
        ),
        "artifact_role": (
            "source_backed_system_identification_diagnostics_with_final_proxy_svar_blocker"
        ),
    }


def _release_6_0_system_identification_manifest(
    *,
    controlled_dynamic_enabled: bool,
    system_panel_rows: list[dict[str, object]],
    relevance_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    timing_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
    valuation_frontier_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.release_6_0_system_identification_manifest.v1",
        "release": "6.0",
        "controlled_dynamic_lp_appendix_enabled": controlled_dynamic_enabled,
        "proxy_svar_system_panel_rows": len(system_panel_rows),
        "proxy_svar_relevance_rows": len(relevance_rows),
        "proxy_svar_residual_diagnostic_rows": len(residual_rows),
        "proxy_svar_timing_support_rows": len(timing_rows),
        "release_6_0_decision_rows": len(decision_rows),
        "release_6_0_proxy_svar_final_blocker_rows": len(blocker_rows),
        "valuation_incidence_frontier_rows": len(valuation_frontier_rows),
        "release_6_0_decision_status_counts": _count_by(
            decision_rows, "decision_status"
        ),
        "release_6_0_decision": (
            "proxy_svar_system_blocked_bounded_dynamic_lp_retained"
        ),
        "proxy_svar_claim_enabled": False,
        "system_identification_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "pricing_output_enabled": False,
        "reset_calendar_construction_enabled": False,
        "incidence_claim_enabled": False,
        "valuation_incidence_claim_enabled": False,
        "paper_claim_boundary": (
            "bounded_dynamic_lp_and_system_diagnostics_not_proxy_svar_pricing_or_incidence"
        ),
    }


def _monthly_series_values(records: list[dict[str, object]]) -> dict[date, Decimal]:
    values: dict[date, Decimal] = {}
    for record in sorted(records, key=lambda item: str(item.get("date", ""))):
        value = _decimal(record.get("value"))
        record_date = record.get("date")
        if value is None or not record_date:
            continue
        values[_month_start(_date(str(record_date)))] = value
    return values


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _month_end(value: date) -> date:
    month_start = _month_start(value)
    return date(month_start.year, month_start.month, _days_in_month(value.year, value.month))


def _latest_month_value_at_or_before(
    values: dict[date, Decimal],
    target: date,
) -> Decimal | None:
    month = _month_start(target)
    candidates = [value_date for value_date in values if value_date <= month]
    return values[max(candidates)] if candidates else None


def _shock_month_summaries(
    smoke_rows: list[dict[str, object]],
) -> dict[date, dict[str, float | int]]:
    summaries: dict[date, dict[str, float | int]] = {}
    for row in smoke_rows:
        if not row.get("date"):
            continue
        shock = _float(row.get("orthogonalized_surprise_bps"))
        if shock is None:
            continue
        month = _month_start(_date(str(row["date"])))
        current = summaries.setdefault(month, {"shock_bps": 0.0, "count": 0})
        current["shock_bps"] = float(current["shock_bps"]) + shock
        current["count"] = int(current["count"]) + 1
    return summaries


def _state_month_summaries(
    smoke_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    state_fields = (
        "public_liability_base_1y_gdp",
        "repricing_share_1y",
        "debt_held_public_gdp",
        "rate_sensitive_fed_liabilities_gdp",
    )
    for row in smoke_rows:
        if not row.get("date"):
            continue
        values = {field: _float(row.get(field)) for field in state_fields}
        if any(value is None for value in values.values()):
            continue
        event_date = _date(str(row["date"]))
        rows.append(
            {
                "date": event_date,
                "month": _month_start(event_date),
                "state_alignment_scope": row.get("state_alignment_scope", ""),
                **{field: float(value) for field, value in values.items()},
            }
        )
    return sorted(rows, key=lambda row: row["date"])


def _latest_state_at_or_before_month(
    state_rows: list[dict[str, object]],
    month: date,
) -> dict[str, object] | None:
    latest = None
    target = _month_end(month)
    for row in state_rows:
        if row["date"] > target:
            break
        latest = row
    return latest


def _annualized_change(current: float, lagged: float, months: int) -> float:
    if lagged <= 0:
        return 0.0
    return ((current / lagged) - 1.0) * 100.0 * (12.0 / months)


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_value = _mean(values)
    return sqrt(sum((value - mean_value) ** 2 for value in values) / (len(values) - 1))


def _release_6_0_proxy_svar_system_appendix_text(
    *,
    system_panel_rows: list[dict[str, object]],
    relevance_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    timing_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
    valuation_frontier_rows: list[dict[str, object]],
) -> str:
    final = blocker_rows[0]
    lines = [
        "# RateWall Release 6.0 Proxy-SVAR/System Identification Appendix",
        "",
        "## Release Decision",
        "",
        "Release 6.0 adds a source-backed monthly system panel and "
        "proxy-SVAR feasibility diagnostics. The package preserves bounded "
        "controlled dynamic-LP evidence where Release 5.0 gates pass, but it "
        "does not claim a proxy-SVAR or system-identification result.",
        "",
        f"- System panel rows: `{len(system_panel_rows)}`",
        f"- Proxy relevance diagnostic rows: `{len(relevance_rows)}`",
        f"- Residual diagnostic rows: `{len(residual_rows)}`",
        f"- Timing/support diagnostic rows: `{len(timing_rows)}`",
        f"- Valuation/incidence frontier rows: `{len(valuation_frontier_rows)}`",
        f"- Final blocker: `{final['blocker_status']}`",
        "- Raw policy-rate changes as shocks: rejected",
        "- Proxy-SVAR, pricing, reset-calendar construction, and incidence "
        "outputs enabled: `false`",
        "",
        "## System Diagnostics",
        "",
    ]
    for row in relevance_rows:
        lines.append(
            f"- `{row['diagnostic_id']}`: `{row['diagnostic_status']}`, "
            f"n={row['n_obs']}, t={row['first_stage_t_stat']}."
        )
    for row in residual_rows:
        lines.append(
            f"- `{row['diagnostic_id']}`: `{row['diagnostic_status']}`, "
            f"n={row['n_obs']}, residual autocorr={row['lag1_residual_autocorrelation']}."
        )
    for row in timing_rows:
        lines.append(
            f"- `{row['diagnostic_id']}`: `{row['timing_status']}`, "
            f"event months missing system rows={row['n_event_months_missing_system']}."
        )
    lines.extend(["", "## Release 6.0 Decision Ledger", ""])
    for row in decision_rows:
        lines.append(
            f"- `{row['decision_id']}`: `{row['decision_status']}`; "
            f"action `{row['release_6_0_action']}`."
        )
    lines.extend(["", "## Optional Valuation/Incidence Frontier", ""])
    for row in valuation_frontier_rows:
        lines.append(
            f"- `{row['frontier_id']}`: `{row['frontier_status']}`; "
            f"switches `{row['explicit_opt_in_switches']}`."
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "The system panel and diagnostics are review evidence only. FEDFUNDS "
            "appears only as a system policy variable, never as the monetary "
            "shock. The release does not claim that higher rates always raise "
            "inflation, does not claim the Federal Reserve has stopped working, "
            "and does not enable pricing, holder-incidence, tax, MPC, welfare, "
            "or reset-calendar outputs.",
            "",
        ]
    )
    return "\n".join(lines)


def _release_6_0_reviewer_response_text(
    *,
    relevance_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    timing_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> str:
    relevance = relevance_rows[0] if relevance_rows else {}
    timing = timing_rows[0] if timing_rows else {}
    final = blocker_rows[0]
    blocked = [
        row
        for row in decision_rows
        if str(row.get("decision_status", "")).startswith("blocked")
        or row.get("decision_status") == "disabled_fail_closed"
    ]
    lines = [
        "# RateWall Release 6.0 Reviewer Response",
        "",
        "## Concern: Is Release 6.0 a proxy-SVAR?",
        "",
        "Response: no. Release 6.0 adds source-backed system diagnostics and "
        "a proxy relevance surface, but the reduced-form system, timing, "
        "invertibility, and exogeneity gates remain unresolved.",
        "",
        f"- Relevance status: `{relevance.get('diagnostic_status', '')}`",
        f"- Timing status: `{timing.get('timing_status', '')}`",
        f"- Residual diagnostic rows: `{len(residual_rows)}`",
        f"- Final blocker: `{final['blocker_status']}`",
        "",
        "## Concern: Are raw rate changes being used as shocks?",
        "",
        "Response: no. The SF Fed orthogonalized surprise remains the shock "
        "surface. FEDFUNDS is included only as a system policy variable for "
        "diagnostics.",
        "",
        "## Blocked Or Disabled Release 6.0 Requirements",
        "",
    ]
    for row in blocked:
        lines.append(f"- `{row['decision_id']}` requires: {row['required_value']}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Pricing, holder bridge, tax, MPC, welfare, reset-calendar "
            "construction, allocation weights, and incidence outputs remain "
            "disabled.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_release_6_0_system_gate_figure(
    path: Path,
    *,
    decision_rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1180
    row_height = 40
    height = 124 + row_height * len(decision_rows)
    colors = {
        "blocked": "#9a4d3f",
        "disabled_fail_closed": "#7f5f28",
        "diagnostic_enabled_not_proxy_svar": "#2f6f73",
        "proxy_relevance_diagnostic_enabled_not_proxy_svar": "#2f6f73",
        "proxy_relevance_blocked_insufficient_system_support": "#9a4d3f",
        "proxy_svar_system_blocked_bounded_dynamic_lp_retained": "#7f5f28",
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="36" font-family="Arial" font-size="20" font-weight="700">RateWall Release 6.0 system-identification gate</text>',
        '<text x="24" y="62" font-family="Arial" font-size="12" fill="#444">Source-backed diagnostics only; proxy-SVAR, pricing, reset-calendar, and incidence outputs remain disabled.</text>',
        '<text x="24" y="94" font-family="Arial" font-size="12" font-weight="700">requirement</text>',
        '<text x="660" y="94" font-family="Arial" font-size="12" font-weight="700">status</text>',
    ]
    for idx, row in enumerate(decision_rows):
        y = 122 + idx * row_height
        status = str(row["decision_status"])
        fill = colors.get(status, "#777777")
        parts.extend(
            [
                f'<rect x="18" y="{y - 24}" width="{width - 36}" height="32" fill="#f7f7f7"/>',
                f'<text x="24" y="{y}" font-family="Arial" font-size="12" fill="#111">{row["decision_id"]}</text>',
                f'<rect x="660" y="{y - 18}" width="230" height="22" fill="{fill}"/>',
                f'<text x="900" y="{y}" font-family="Arial" font-size="11" fill="#111">{status}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _release_7_0_system_variables() -> list[str]:
    return [
        "core_pce_inflation_3m_annualized",
        "industrial_production_growth_3m_annualized",
        "unemployment_rate",
        "fed_funds_rate",
        "public_liability_base_1y_gdp",
    ]


def _release_7_0_var_lag_selection_rows(
    system_panel_rows: list[dict[str, object]],
    *,
    variables: list[str],
) -> tuple[list[dict[str, object]], int]:
    rows: list[dict[str, object]] = []
    eligible: list[tuple[int, float]] = []
    for lag_order in (1, 2, 3):
        estimates = _release_7_0_var_equation_estimates(
            system_panel_rows,
            variables=variables,
            lag_order=lag_order,
        )
        n_obs = max(
            (len(estimate["months"]) for estimate in estimates.values()),
            default=0,
        )
        coefficient_count = 1 + lag_order * len(variables)
        estimated_equations = len(estimates)
        parameter_count = estimated_equations * coefficient_count
        system_sse = sum(float(estimate["sse"]) for estimate in estimates.values())
        denominator = max(n_obs * max(estimated_equations, 1), 1)
        all_estimated = estimated_equations == len(variables) and n_obs > coefficient_count
        if all_estimated and system_sse > 0:
            system_aic = log(system_sse / denominator) + (
                2.0 * parameter_count / denominator
            )
            system_bic = log(system_sse / denominator) + (
                log(max(n_obs, 2)) * parameter_count / denominator
            )
            status = "estimated_reduced_form_diagnostic_not_proxy_svar"
            eligible.append((lag_order, system_bic))
        else:
            system_aic = 0.0
            system_bic = 0.0
            status = "blocked_insufficient_or_singular_reduced_form_system"
        rows.append(
            {
                "lag_order": lag_order,
                "n_obs": n_obs,
                "system_variables": ";".join(variables),
                "estimated_equations": estimated_equations,
                "parameter_count": parameter_count,
                "system_sse": _release_7_0_fmt(system_sse) if system_sse > 0 else "",
                "system_aic": _release_7_0_fmt(system_aic) if all_estimated else "",
                "system_bic": _release_7_0_fmt(system_bic) if all_estimated else "",
                "lag_selection_status": status,
                "selected_by_bic": "false",
                "raw_rate_change_identification_rejected": "true",
                "proxy_svar_claim_enabled": "false",
                "system_identification_claim_enabled": "false",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "Reduced-form VAR lag selection is diagnostic only. FEDFUNDS "
                    "is a system policy variable, not the monetary shock."
                ),
            }
        )
    selected_lag = min(eligible, key=lambda item: item[1])[0] if eligible else 0
    for row in rows:
        if int(row["lag_order"]) == selected_lag:
            row["selected_by_bic"] = "true"
    return rows, selected_lag


def _release_7_0_var_equation_estimates(
    system_panel_rows: list[dict[str, object]],
    *,
    variables: list[str],
    lag_order: int,
) -> dict[str, dict[str, object]]:
    if lag_order <= 0:
        return {}
    months, x_rows, y_by_variable, coefficient_names = _release_7_0_var_design(
        system_panel_rows,
        variables=variables,
        lag_order=lag_order,
    )
    estimates: dict[str, dict[str, object]] = {}
    if not x_rows:
        return estimates
    for variable in variables:
        y_values = y_by_variable.get(variable, [])
        model = _ols_hac_multivariate(
            x_rows,
            y_values,
            coefficient_names=coefficient_names,
            hac_lag=min(4, max(1, lag_order)),
        )
        if model is None:
            continue
        coefs = model["coef"]
        residuals = [
            y_value
            - sum(float(coefs[name]) * value for name, value in zip(coefficient_names, row))
            for row, y_value in zip(x_rows, y_values)
        ]
        estimates[variable] = {
            "months": months,
            "x": x_rows,
            "y": y_values,
            "coefficient_names": coefficient_names,
            "coef": coefs,
            "se": model["se"],
            "t": model["t"],
            "residuals": residuals,
            "sse": sum(residual * residual for residual in residuals),
        }
    return estimates


def _release_7_0_var_design(
    system_panel_rows: list[dict[str, object]],
    *,
    variables: list[str],
    lag_order: int,
) -> tuple[list[str], list[list[float]], dict[str, list[float]], list[str]]:
    ordered = sorted(system_panel_rows, key=lambda row: str(row.get("month", "")))
    value_rows: list[dict[str, object]] = []
    for row in ordered:
        values = {variable: _float(row.get(variable)) for variable in variables}
        if any(value is None for value in values.values()):
            continue
        value_rows.append({"month": str(row["month"]), **values})
    coefficient_names = ["intercept"] + [
        f"{variable}_lag{lag}"
        for lag in range(1, lag_order + 1)
        for variable in variables
    ]
    months: list[str] = []
    x_rows: list[list[float]] = []
    y_by_variable = {variable: [] for variable in variables}
    for index in range(lag_order, len(value_rows)):
        current = value_rows[index]
        lag_values: list[float] = []
        for lag in range(1, lag_order + 1):
            lagged = value_rows[index - lag]
            lag_values.extend(float(lagged[variable]) for variable in variables)
        months.append(str(current["month"]))
        x_rows.append([1.0, *lag_values])
        for variable in variables:
            y_by_variable[variable].append(float(current[variable]))
    return months, x_rows, y_by_variable, coefficient_names


def _release_7_0_reduced_form_estimate_rows(
    selected_estimates: dict[str, dict[str, object]],
    *,
    variables: list[str],
    lag_order: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if lag_order <= 0 or not selected_estimates:
        return [
            _release_7_0_estimate_placeholder_row(
                "blocked_insufficient_estimated_reduced_form_system"
            )
        ]
    for variable in variables:
        estimate = selected_estimates.get(variable)
        if estimate is None:
            rows.append(
                _release_7_0_estimate_placeholder_row(
                    "blocked_missing_equation_estimate",
                    equation_variable=variable,
                )
            )
            continue
        months = [str(month) for month in estimate["months"]]
        for coefficient_name in estimate["coefficient_names"]:
            rows.append(
                {
                    "estimate_id": f"{variable}_{coefficient_name}",
                    "equation_variable": variable,
                    "regressor": coefficient_name,
                    "lag_order": lag_order,
                    "n_obs": len(months),
                    "sample_start": min(months, default=""),
                    "sample_end": max(months, default=""),
                    "coefficient": _release_7_0_fmt(
                        float(estimate["coef"][coefficient_name])
                    ),
                    "standard_error": _release_7_0_fmt(
                        float(estimate["se"][coefficient_name])
                    ),
                    "t_stat": _release_7_0_fmt(
                        float(estimate["t"][coefficient_name])
                    ),
                    "equation_sse": _release_7_0_fmt(float(estimate["sse"])),
                    "estimate_status": (
                        "reduced_form_estimate_validation_only_not_proxy_svar"
                    ),
                    "raw_rate_change_identification_rejected": "true",
                    "proxy_svar_claim_enabled": "false",
                    "system_identification_claim_enabled": "false",
                    "pricing_output_enabled": "false",
                    "incidence_claim_enabled": "false",
                    "notes": (
                        "Estimated reduced-form equation coefficient. This is "
                        "a diagnostic system estimate, not a structural proxy-SVAR."
                    ),
                }
            )
    return rows


def _release_7_0_estimate_placeholder_row(
    status: str,
    *,
    equation_variable: str = "",
) -> dict[str, object]:
    return {
        "estimate_id": "release_7_0_reduced_form_system_blocker",
        "equation_variable": equation_variable,
        "regressor": "",
        "lag_order": "",
        "n_obs": 0,
        "sample_start": "",
        "sample_end": "",
        "coefficient": "",
        "standard_error": "",
        "t_stat": "",
        "equation_sse": "",
        "estimate_status": status,
        "raw_rate_change_identification_rejected": "true",
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": (
            "Release 7.0 keeps proxy-SVAR/system identification blocked when "
            "the reduced-form system cannot be estimated from source-backed rows."
        ),
    }


def _release_7_0_residual_covariance_rows(
    selected_estimates: dict[str, dict[str, object]],
    *,
    variables: list[str],
    lag_order: int,
) -> list[dict[str, object]]:
    if lag_order <= 0 or not selected_estimates:
        return [
            _release_7_0_covariance_row(
                "release_7_0_residual_covariance_blocker",
                "",
                "",
                lag_order,
                [],
                [],
                "blocked_missing_reduced_form_residuals",
            )
        ]
    rows: list[dict[str, object]] = []
    for row_variable in variables:
        for column_variable in variables:
            left = selected_estimates.get(row_variable, {}).get("residuals", [])
            right = selected_estimates.get(column_variable, {}).get("residuals", [])
            status = (
                "residual_covariance_diagnostic_not_proxy_svar"
                if left and right and len(left) == len(right)
                else "blocked_missing_reduced_form_residuals"
            )
            rows.append(
                _release_7_0_covariance_row(
                    f"{row_variable}_{column_variable}",
                    row_variable,
                    column_variable,
                    lag_order,
                    [float(value) for value in left],
                    [float(value) for value in right],
                    status,
                )
            )
    return rows


def _release_7_0_covariance_row(
    covariance_id: str,
    row_variable: str,
    column_variable: str,
    lag_order: int,
    left: list[float],
    right: list[float],
    status: str,
) -> dict[str, object]:
    n_obs = min(len(left), len(right))
    if n_obs >= 2:
        left_values = left[:n_obs]
        right_values = right[:n_obs]
        left_mean = _mean(left_values)
        right_mean = _mean(right_values)
        covariance = sum(
            (left_value - left_mean) * (right_value - right_mean)
            for left_value, right_value in zip(left_values, right_values)
        ) / (n_obs - 1)
        correlation = _correlation(left_values, right_values)
    else:
        covariance = 0.0
        correlation = 0.0
    return {
        "covariance_id": covariance_id,
        "row_variable": row_variable,
        "column_variable": column_variable,
        "lag_order": lag_order if lag_order > 0 else "",
        "n_obs": n_obs,
        "covariance": _release_7_0_fmt(covariance) if n_obs >= 2 else "",
        "correlation": _release_7_0_fmt(correlation) if n_obs >= 2 else "",
        "covariance_status": status,
        "raw_rate_change_identification_rejected": "true",
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": (
            "Residual covariance is a reduced-form diagnostic. It does not by "
            "itself establish proxy-SVAR invertibility or exogeneity."
        ),
    }


def _release_7_0_proxy_support_rows(
    *,
    system_panel_rows: list[dict[str, object]],
    selected_estimates: dict[str, dict[str, object]],
    lag_order: int,
) -> list[dict[str, object]]:
    event_observations = []
    for row in system_panel_rows:
        if int(row.get("proxy_event_count", 0)) <= 0:
            continue
        proxy = _float(row.get("sf_fed_proxy_shock_bps"))
        policy_change = _float(row.get("fed_funds_rate_change"))
        if proxy is None or policy_change is None:
            continue
        event_observations.append(
            (str(row["month"]), proxy / 100.0, policy_change)
        )
    rows = [
        _release_7_0_proxy_support_row(
            support_id="policy_change_external_proxy_relevance",
            target_variable="fed_funds_rate_change_system_variable",
            lag_order=lag_order,
            observations=event_observations,
            notes=(
                "First-stage diagnostic against the system policy variable. "
                "The policy variable is not used as the monetary shock."
            ),
        )
    ]
    policy_estimate = selected_estimates.get("fed_funds_rate")
    if policy_estimate is not None:
        residual_by_month = {
            str(month): float(residual)
            for month, residual in zip(
                policy_estimate["months"], policy_estimate["residuals"]
            )
        }
        residual_observations = [
            (month, proxy, residual_by_month[month])
            for month, proxy, _policy_change in event_observations
            if month in residual_by_month
        ]
    else:
        residual_observations = []
    rows.append(
        _release_7_0_proxy_support_row(
            support_id="policy_equation_residual_external_proxy_relevance",
            target_variable="fed_funds_rate_reduced_form_residual",
            lag_order=lag_order,
            observations=residual_observations,
            notes=(
                "First-stage diagnostic against the selected reduced-form "
                "policy residual. This remains support evidence only."
            ),
        )
    )
    return rows


def _release_7_0_proxy_support_row(
    *,
    support_id: str,
    target_variable: str,
    lag_order: int,
    observations: list[tuple[str, float, float]],
    notes: str,
) -> dict[str, object]:
    xs = [proxy for _month, proxy, _target in observations]
    ys = [target for _month, _proxy, target in observations]
    beta, se, t_stat = _ols_slope(xs, ys)
    f_stat = t_stat * t_stat
    months = [month for month, _proxy, _target in observations]
    years = {month[:4] for month in months}
    nonzero_proxy_months = sum(abs(proxy) > 0 for proxy in xs)
    support_pass = (
        len(observations) >= 30
        and len(years) >= 8
        and nonzero_proxy_months >= 30
        and f_stat >= 10.0
        and _std(xs) > 0
        and _std(ys) > 0
    )
    if support_pass:
        status = "proxy_relevance_support_pass_not_claim_promotion"
    elif observations:
        status = "blocked_weak_external_proxy_relevance_for_proxy_svar"
    else:
        status = "blocked_missing_external_proxy_residual_support"
    return {
        "support_id": support_id,
        "target_variable": target_variable,
        "lag_order": lag_order if lag_order > 0 else "",
        "n_obs": len(observations),
        "sample_start": min(months, default=""),
        "sample_end": max(months, default=""),
        "unique_event_years": len(years),
        "nonzero_proxy_months": nonzero_proxy_months,
        "estimator": "diagnostic_first_stage_not_structural_identification",
        "instrument_variable": "sf_fed_orthogonalized_surprise_100bp",
        "first_stage_beta": _release_7_0_fmt(beta) if observations else "",
        "first_stage_standard_error": _release_7_0_fmt(se) if observations else "",
        "first_stage_t_stat": _release_7_0_fmt(t_stat) if observations else "",
        "first_stage_f_stat": _release_7_0_fmt(f_stat) if observations else "",
        "required_first_stage_f_stat": "10.000000",
        "support_status": status,
        "raw_rate_change_identification_rejected": "true",
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_7_0_timing_exogeneity_audit_rows(
    *,
    system_panel_rows: list[dict[str, object]],
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
    covariance_rows: list[dict[str, object]],
    proxy_support_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    selected_lag = _release_7_0_selected_lag(lag_rows)
    reduced_form_ok = _release_7_0_reduced_form_estimated(estimate_rows)
    covariance_ok = bool(covariance_rows) and all(
        row.get("covariance_status") == "residual_covariance_diagnostic_not_proxy_svar"
        for row in covariance_rows
    )
    event_months = {
        str(row["month"])
        for row in system_panel_rows
        if int(row.get("proxy_event_count", 0)) > 0
    }
    proxy_f_values = [
        _float(row.get("first_stage_f_stat"))
        for row in proxy_support_rows
        if row.get("first_stage_f_stat")
    ]
    min_proxy_f = min((value for value in proxy_f_values if value is not None), default=0.0)
    proxy_support_ok = bool(proxy_support_rows) and all(
        row.get("support_status") == "proxy_relevance_support_pass_not_claim_promotion"
        for row in proxy_support_rows
    )
    return [
        _release_7_0_audit_row(
            "estimated_reduced_form_system",
            "pass_diagnostic_not_proxy_svar" if reduced_form_ok else "blocked",
            "outputs/tables/ratewall_release_7_0_reduced_form_system_estimates.csv",
            f"selected_lag={selected_lag};estimate_rows={len(estimate_rows)}",
            "estimated reduced-form system for all core variables",
            "use_reduced_form_diagnostics_only",
            "Reduced-form estimates are necessary but not sufficient for proxy-SVAR claims.",
        ),
        _release_7_0_audit_row(
            "residual_covariance_system",
            "pass_diagnostic_not_invertibility_proof" if covariance_ok else "blocked",
            "outputs/tables/ratewall_release_7_0_residual_covariance.csv",
            f"covariance_rows={len(covariance_rows)}",
            "residual covariance plus stability/invertibility diagnostics",
            "use_covariance_diagnostics_only",
            "Residual covariance is diagnostic, not a structural timing proof.",
        ),
        _release_7_0_audit_row(
            "external_proxy_relevance_threshold",
            "pass_diagnostic_not_claim_promotion" if proxy_support_ok else "blocked",
            "outputs/tables/ratewall_release_7_0_proxy_relevance_support.csv",
            f"min_first_stage_f_stat={_release_7_0_fmt(min_proxy_f)}",
            "first-stage support with F-statistic at or above 10 for required proxy links",
            "keep_proxy_svar_claim_disabled",
            "Weak proxy relevance blocks a structural proxy-SVAR promotion.",
        ),
        _release_7_0_audit_row(
            "event_timing_alignment",
            "pass_diagnostic_not_exogeneity_proof"
            if len(event_months) >= 30
            else "blocked",
            "outputs/tables/ratewall_proxy_svar_system_panel.csv",
            f"proxy_event_months={len(event_months)}",
            "event months aligned to source-backed system rows",
            "use_calendar_alignment_as_support_only",
            "Calendar support does not prove exogeneity or invertibility.",
        ),
        _release_7_0_audit_row(
            "recursive_timing_assumption",
            "blocked",
            "outputs/tables/ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv",
            "not_audited",
            "audited structural timing order and policy-information set",
            "keep_proxy_svar_claim_disabled",
            "Release 7.0 rejects prose-only structural timing assumptions.",
        ),
        _release_7_0_audit_row(
            "invertibility_and_exogeneity_assumptions",
            "blocked",
            "outputs/tables/ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv",
            "not_audited",
            "invertibility, exclusion, and external-proxy exogeneity diagnostics",
            "keep_proxy_svar_claim_disabled",
            "A reduced-form system plus weak proxy evidence is not a proxy-SVAR.",
        ),
    ]


def _release_7_0_audit_row(
    audit_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    action: str,
    notes: str,
) -> dict[str, object]:
    return {
        "audit_id": audit_id,
        "audit_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_7_0_action": action,
        "raw_rate_change_identification_rejected": "true",
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_7_0_claim_promotion_contract_rows(
    *,
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
    covariance_rows: list[dict[str, object]],
    proxy_support_rows: list[dict[str, object]],
    timing_audit_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    selected_lag = _release_7_0_selected_lag(lag_rows)
    reduced_form_ok = _release_7_0_reduced_form_estimated(estimate_rows)
    covariance_ok = bool(covariance_rows) and all(
        row.get("covariance_status") == "residual_covariance_diagnostic_not_proxy_svar"
        for row in covariance_rows
    )
    proxy_support_ok = bool(proxy_support_rows) and all(
        row.get("support_status") == "proxy_relevance_support_pass_not_claim_promotion"
        for row in proxy_support_rows
    )
    structural_assumptions_ok = all(
        str(row.get("audit_status", "")).startswith("pass")
        for row in timing_audit_rows
    )
    return [
        _release_7_0_contract_row(
            "reduced_form_system_estimation",
            "pass_diagnostic_not_claim_promotion" if reduced_form_ok else "blocked",
            "outputs/tables/ratewall_release_7_0_reduced_form_system_estimates.csv",
            f"selected_lag={selected_lag};estimate_rows={len(estimate_rows)}",
            "estimated reduced-form system for all variables",
            "keep_as_diagnostic_until_other_gates_pass",
            "System estimates alone do not authorize proxy-SVAR language.",
        ),
        _release_7_0_contract_row(
            "residual_covariance_and_stability",
            "diagnostic_not_promotion_ready" if covariance_ok else "blocked",
            "outputs/tables/ratewall_release_7_0_residual_covariance.csv",
            f"covariance_rows={len(covariance_rows)}",
            "residual covariance plus audited stability/invertibility tests",
            "add_stability_and_invertibility_tests_before_promotion",
            "Covariance output remains reviewer support rather than a structural proof.",
        ),
        _release_7_0_contract_row(
            "external_proxy_relevance",
            "pass_diagnostic_not_claim_promotion" if proxy_support_ok else "blocked",
            "outputs/tables/ratewall_release_7_0_proxy_relevance_support.csv",
            _release_7_0_proxy_support_observed(proxy_support_rows),
            "strong external-proxy first-stage support against the system shock",
            "require_proxy_relevance_threshold_before_promotion",
            "Weak or missing proxy support blocks proxy-SVAR promotion.",
        ),
        _release_7_0_contract_row(
            "timing_exogeneity_invertibility",
            "pass" if structural_assumptions_ok else "blocked",
            "outputs/tables/ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv",
            _release_7_0_audit_observed(timing_audit_rows),
            "audited timing, exogeneity, invertibility, and exclusion restrictions",
            "require_structural_assumption_audit_before_promotion",
            "Release 7.0 keeps structural assumptions blocked when only prose is available.",
        ),
        _release_7_0_contract_row(
            "explicit_claim_promotion_switch",
            "disabled_fail_closed",
            "outputs/tables/ratewall_release_7_0_claim_promotion_contract_disabled.csv",
            "dynamic_identification_promotion_enabled=false",
            "explicit future opt-in switch and negative tests",
            "keep_dynamic_identification_promotion_disabled",
            "No claim-promotion switch is enabled in Release 7.0.",
        ),
        _release_7_0_contract_row(
            "optional_valuation_incidence_frontier",
            "disabled_fail_closed",
            "outputs/tables/ratewall_release_6_0_valuation_incidence_frontier_disabled.csv",
            "pricing_output_enabled=false;incidence_claim_enabled=false",
            "pricing, holder bridge, tax, MPC, welfare, and incidence gates",
            "keep_optional_valuation_incidence_frontier_disabled",
            "Release 7.0 does not widen into valuation or incidence output.",
        ),
    ]


def _release_7_0_contract_row(
    requirement_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    prerequisite: str,
    notes: str,
) -> dict[str, object]:
    return {
        "requirement_id": requirement_id,
        "requirement_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "future_opt_in_prerequisite": prerequisite,
        "raw_rate_change_identification_rejected": "true",
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "dynamic_identification_promotion_enabled": "false",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_7_0_identification_decision_rows(
    *,
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
    covariance_rows: list[dict[str, object]],
    proxy_support_rows: list[dict[str, object]],
    timing_audit_rows: list[dict[str, object]],
    promotion_contract_rows: list[dict[str, object]],
    controlled_dynamic_enabled: bool,
) -> list[dict[str, object]]:
    selected_lag = _release_7_0_selected_lag(lag_rows)
    reduced_form_ok = _release_7_0_reduced_form_estimated(estimate_rows)
    covariance_ok = bool(covariance_rows) and all(
        row.get("covariance_status") == "residual_covariance_diagnostic_not_proxy_svar"
        for row in covariance_rows
    )
    proxy_support_ok = bool(proxy_support_rows) and all(
        row.get("support_status") == "proxy_relevance_support_pass_not_claim_promotion"
        for row in proxy_support_rows
    )
    structural_blocked = any(
        row.get("audit_status") == "blocked" for row in timing_audit_rows
    )
    contract_disabled = any(
        row.get("requirement_status") == "disabled_fail_closed"
        for row in promotion_contract_rows
    )
    reduced_form_enabled = reduced_form_ok and selected_lag > 0
    return [
        _release_7_0_decision_row(
            "estimated_reduced_form_system",
            "diagnostic_enabled_not_proxy_svar" if reduced_form_ok else "blocked",
            "outputs/tables/ratewall_release_7_0_reduced_form_system_estimates.csv",
            f"selected_lag={selected_lag};estimate_rows={len(estimate_rows)}",
            "estimated reduced-form VAR-style system",
            "publish_diagnostics_only",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            "Reduced-form estimates are review diagnostics, not a structural result.",
        ),
        _release_7_0_decision_row(
            "residual_covariance_diagnostics",
            "diagnostic_enabled_not_proxy_svar" if covariance_ok else "blocked",
            "outputs/tables/ratewall_release_7_0_residual_covariance.csv",
            f"covariance_rows={len(covariance_rows)}",
            "residual covariance with audited stability and invertibility checks",
            "publish_covariance_diagnostics_only",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            "Covariance rows do not identify a structural monetary shock.",
        ),
        _release_7_0_decision_row(
            "external_proxy_relevance",
            "diagnostic_pass_not_claim_promotion"
            if proxy_support_ok
            else "blocked_weak_or_missing_proxy_support",
            "outputs/tables/ratewall_release_7_0_proxy_relevance_support.csv",
            _release_7_0_proxy_support_observed(proxy_support_rows),
            "strong proxy first-stage support for structural identification",
            "keep_proxy_svar_claim_disabled",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            "Weak external-proxy support blocks a proxy-SVAR claim.",
        ),
        _release_7_0_decision_row(
            "timing_exogeneity_invertibility",
            "blocked" if structural_blocked else "diagnostic_pass_not_claim_promotion",
            "outputs/tables/ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv",
            _release_7_0_audit_observed(timing_audit_rows),
            "audited timing, exogeneity, invertibility, and exclusion restrictions",
            "keep_system_identification_claim_disabled",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            "Release 7.0 rejects structural promotion from reduced-form diagnostics alone.",
        ),
        _release_7_0_decision_row(
            "claim_promotion_contract",
            "disabled_fail_closed" if contract_disabled else "blocked",
            "outputs/tables/ratewall_release_7_0_claim_promotion_contract_disabled.csv",
            f"contract_rows={len(promotion_contract_rows)}",
            "all source/method gates plus explicit future claim-promotion opt-in",
            "keep_dynamic_identification_promotion_disabled",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            "Claim-promotion remains disabled even when diagnostic rows are present.",
        ),
        _release_7_0_decision_row(
            "release_7_0_identification_decision",
            "proxy_svar_system_blocked_reduced_form_diagnostics_published",
            "outputs/tables/ratewall_release_7_0_proxy_svar_final_blocker.csv",
            (
                f"reduced_form_enabled={reduced_form_enabled};"
                f"proxy_support_ok={proxy_support_ok};"
                f"structural_blocked={structural_blocked}"
            ),
            "defensible proxy-SVAR/system identification or final blocker",
            "publish_release_7_0_final_blocker_with_system_diagnostics",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            "This is the maximum defensible Release 7.0 empirical claim.",
        ),
    ]


def _release_7_0_decision_row(
    decision_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    action: str,
    controlled_dynamic_enabled: bool,
    reduced_form_enabled: bool,
    notes: str,
) -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "decision_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_7_0_action": action,
        "controlled_dynamic_lp_appendix_enabled": str(controlled_dynamic_enabled).lower(),
        "reduced_form_system_diagnostics_enabled": str(reduced_form_enabled).lower(),
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "valuation_incidence_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_7_0_proxy_svar_blocker_rows(
    decision_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    blocked = [
        str(row["decision_id"])
        for row in decision_rows
        if str(row["decision_status"]).startswith("blocked")
        or row["decision_status"] == "disabled_fail_closed"
    ]
    required = [
        f"{row['decision_id']}={row['required_value']}"
        for row in decision_rows
        if row["decision_id"] in blocked
    ]
    controlled_enabled = any(
        row.get("controlled_dynamic_lp_appendix_enabled") == "true"
        for row in decision_rows
    )
    reduced_form_enabled = any(
        row.get("reduced_form_system_diagnostics_enabled") == "true"
        for row in decision_rows
    )
    return [
        {
            "blocker_id": "release_7_0_proxy_svar_system_final_blocker",
            "blocker_status": (
                "proxy_svar_system_blocked_reduced_form_diagnostics_published"
            ),
            "evidence_artifact": (
                "outputs/tables/ratewall_release_7_0_identification_decision.csv"
            ),
            "blocked_requirements": ";".join(blocked),
            "required_resolution": "; ".join(required),
            "release_7_0_action": (
                "publish_reduced_form_system_diagnostics_keep_proxy_svar_disabled"
            ),
            "controlled_dynamic_lp_appendix_enabled": str(controlled_enabled).lower(),
            "reduced_form_system_diagnostics_enabled": str(
                reduced_form_enabled
            ).lower(),
            "proxy_svar_claim_enabled": "false",
            "system_identification_claim_enabled": "false",
            "valuation_incidence_claim_enabled": "false",
            "raw_rate_change_identification_rejected": "true",
            "pricing_output_enabled": "false",
            "reset_calendar_construction_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "Release 7.0 estimates and audits a reduced-form system where "
                "source support allows, but preserves the proxy-SVAR/system "
                "claim blocker because proxy relevance and structural "
                "assumption gates are not promotion-ready."
            ),
        }
    ]


def _release_7_0_robustness_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
    covariance_rows: list[dict[str, object]],
    proxy_support_rows: list[dict[str, object]],
    timing_audit_rows: list[dict[str, object]],
    promotion_contract_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.empirical_robustness_manifest.v7",
        "release": "7.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "release_7_0_var_lag_selection_rows": len(lag_rows),
        "release_7_0_reduced_form_estimate_rows": len(estimate_rows),
        "release_7_0_residual_covariance_rows": len(covariance_rows),
        "release_7_0_proxy_support_rows": len(proxy_support_rows),
        "release_7_0_timing_audit_rows": len(timing_audit_rows),
        "release_7_0_promotion_contract_rows": len(promotion_contract_rows),
        "release_7_0_decision_rows": len(decision_rows),
        "release_7_0_proxy_svar_final_blocker_rows": len(blocker_rows),
        "release_7_0_decision_status_counts": _count_by(
            decision_rows, "decision_status"
        ),
        "selected_lag_order": _release_7_0_selected_lag(lag_rows),
        "reduced_form_system_diagnostics_enabled": _release_7_0_reduced_form_estimated(
            estimate_rows
        ),
        "proxy_svar_claim_enabled": False,
        "system_identification_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "dynamic_identification_promotion_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "causal_claim_enabled": False,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "reset_calendar_construction_enabled": False,
        "release_7_0_decision": (
            "proxy_svar_system_blocked_reduced_form_diagnostics_published"
        ),
        "artifact_role": (
            "reduced_form_system_diagnostics_with_final_proxy_svar_system_blocker"
        ),
    }


def _release_7_0_system_identification_manifest(
    *,
    controlled_dynamic_enabled: bool,
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
    covariance_rows: list[dict[str, object]],
    proxy_support_rows: list[dict[str, object]],
    timing_audit_rows: list[dict[str, object]],
    promotion_contract_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.release_7_0_system_identification_manifest.v1",
        "release": "7.0",
        "controlled_dynamic_lp_appendix_enabled": controlled_dynamic_enabled,
        "selected_lag_order": _release_7_0_selected_lag(lag_rows),
        "var_lag_selection_rows": len(lag_rows),
        "reduced_form_system_estimate_rows": len(estimate_rows),
        "residual_covariance_rows": len(covariance_rows),
        "proxy_relevance_support_rows": len(proxy_support_rows),
        "timing_exogeneity_invertibility_audit_rows": len(timing_audit_rows),
        "claim_promotion_contract_rows": len(promotion_contract_rows),
        "release_7_0_decision_rows": len(decision_rows),
        "release_7_0_proxy_svar_final_blocker_rows": len(blocker_rows),
        "release_7_0_decision_status_counts": _count_by(
            decision_rows, "decision_status"
        ),
        "release_7_0_decision": (
            "proxy_svar_system_blocked_reduced_form_diagnostics_published"
        ),
        "reduced_form_system_diagnostics_enabled": _release_7_0_reduced_form_estimated(
            estimate_rows
        ),
        "proxy_svar_claim_enabled": False,
        "system_identification_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "dynamic_identification_promotion_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "pricing_output_enabled": False,
        "reset_calendar_construction_enabled": False,
        "incidence_claim_enabled": False,
        "valuation_incidence_claim_enabled": False,
        "paper_claim_boundary": (
            "reduced_form_system_diagnostics_not_proxy_svar_pricing_or_incidence"
        ),
    }


def _release_7_0_system_identification_appendix_text(
    *,
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
    covariance_rows: list[dict[str, object]],
    proxy_support_rows: list[dict[str, object]],
    timing_audit_rows: list[dict[str, object]],
    promotion_contract_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> str:
    final = blocker_rows[0]
    selected_lag = _release_7_0_selected_lag(lag_rows)
    lines = [
        "# RateWall Release 7.0 System-Identification Appendix",
        "",
        "## Release Decision",
        "",
        "Release 7.0 adds estimated reduced-form system diagnostics, proxy "
        "support diagnostics, residual covariance rows, and a fail-closed "
        "claim-promotion contract. It does not claim a proxy-SVAR or structural "
        "system-identification result.",
        "",
        f"- Selected diagnostic lag order: `{selected_lag}`",
        f"- Reduced-form estimate rows: `{len(estimate_rows)}`",
        f"- Residual covariance rows: `{len(covariance_rows)}`",
        f"- Proxy support rows: `{len(proxy_support_rows)}`",
        f"- Timing/exogeneity/invertibility audit rows: `{len(timing_audit_rows)}`",
        f"- Promotion-contract rows: `{len(promotion_contract_rows)}`",
        f"- Final blocker: `{final['blocker_status']}`",
        "- Raw policy-rate changes as shocks: rejected",
        "- Proxy-SVAR, system-identification, pricing, reset-calendar, and "
        "incidence outputs enabled: `false`",
        "",
        "## Lag Selection",
        "",
    ]
    for row in lag_rows:
        lines.append(
            f"- lag `{row['lag_order']}`: `{row['lag_selection_status']}`, "
            f"BIC `{row['system_bic']}`, selected `{row['selected_by_bic']}`."
        )
    lines.extend(["", "## Proxy Support", ""])
    for row in proxy_support_rows:
        lines.append(
            f"- `{row['support_id']}`: `{row['support_status']}`, "
            f"n={row['n_obs']}, F={row['first_stage_f_stat']}."
        )
    lines.extend(["", "## Structural Audit", ""])
    for row in timing_audit_rows:
        lines.append(
            f"- `{row['audit_id']}`: `{row['audit_status']}`; "
            f"required `{row['required_value']}`."
        )
    lines.extend(["", "## Fail-Closed Promotion Contract", ""])
    for row in promotion_contract_rows:
        lines.append(
            f"- `{row['requirement_id']}`: `{row['requirement_status']}`; "
            f"future prerequisite `{row['future_opt_in_prerequisite']}`."
        )
    lines.extend(["", "## Release 7.0 Decision Ledger", ""])
    for row in decision_rows:
        lines.append(
            f"- `{row['decision_id']}`: `{row['decision_status']}`; "
            f"action `{row['release_7_0_action']}`."
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "The reduced-form system is a diagnostic evidence surface. The SF "
            "Fed orthogonalized surprise remains the admissible external shock "
            "surface; FEDFUNDS is a system policy variable only. The appendix "
            "does not claim that higher rates always raise inflation, does not "
            "claim the Federal Reserve has stopped working, and does not enable "
            "pricing, holder-incidence, tax, MPC, welfare, reset-calendar, or "
            "incidence outputs.",
            "",
        ]
    )
    return "\n".join(lines)


def _release_7_0_external_review_packet_text(
    *,
    proxy_support_rows: list[dict[str, object]],
    timing_audit_rows: list[dict[str, object]],
    promotion_contract_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> str:
    final = blocker_rows[0]
    blocked = [
        row
        for row in decision_rows
        if str(row.get("decision_status", "")).startswith("blocked")
        or row.get("decision_status") == "disabled_fail_closed"
    ]
    lines = [
        "# RateWall Release 7.0 External Review Packet",
        "",
        "## Reviewer Concern: Did Release 7.0 finally estimate a proxy-SVAR?",
        "",
        "Response: no. It estimates and audits reduced-form system diagnostics "
        "where the source-backed monthly panel supports them, but leaves the "
        "structural proxy-SVAR/system claim blocked.",
        "",
        "## Reviewer Concern: Is the external proxy strong enough?",
        "",
    ]
    for row in proxy_support_rows:
        lines.append(
            f"- `{row['target_variable']}`: status `{row['support_status']}`, "
            f"F-stat `{row['first_stage_f_stat']}`."
        )
    lines.extend(
        [
            "",
            "## Reviewer Concern: What structural assumptions remain unresolved?",
            "",
        ]
    )
    for row in timing_audit_rows:
        if str(row.get("audit_status", "")).startswith("blocked"):
            lines.append(f"- `{row['audit_id']}` requires: {row['required_value']}")
    lines.extend(
        [
            "",
            "## Reviewer Concern: Can claims be promoted manually?",
            "",
            "Response: no. The promotion contract is fail-closed.",
        ]
    )
    for row in promotion_contract_rows:
        if row.get("requirement_status") != "pass":
            lines.append(
                f"- `{row['requirement_id']}`: `{row['requirement_status']}`."
            )
    lines.extend(
        [
            "",
            "## Final Release 7.0 Blocker",
            "",
            f"- `{final['blocker_id']}`: `{final['blocker_status']}`",
            f"- Blocked requirements: `{final['blocked_requirements']}`",
            "",
            "## Blocked Or Disabled Decision Rows",
            "",
        ]
    )
    for row in blocked:
        lines.append(f"- `{row['decision_id']}` requires: {row['required_value']}")
    lines.extend(
        [
            "",
            "Pricing, holder bridge, tax, MPC, welfare, reset-calendar "
            "construction, allocation weights, and incidence outputs remain "
            "disabled.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_release_7_0_system_frontier_figure(
    path: Path,
    *,
    decision_rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1220
    row_height = 40
    height = 126 + row_height * len(decision_rows)
    colors = {
        "blocked": "#9a4d3f",
        "blocked_weak_or_missing_proxy_support": "#9a4d3f",
        "disabled_fail_closed": "#7f5f28",
        "diagnostic_enabled_not_proxy_svar": "#2f6f73",
        "diagnostic_pass_not_claim_promotion": "#2f6f73",
        "proxy_svar_system_blocked_reduced_form_diagnostics_published": "#7f5f28",
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="36" font-family="Arial" font-size="20" font-weight="700">RateWall Release 7.0 system-identification frontier</text>',
        '<text x="24" y="62" font-family="Arial" font-size="12" fill="#444">Estimated reduced-form diagnostics; proxy-SVAR/system, pricing, reset-calendar, and incidence claims remain disabled.</text>',
        '<text x="24" y="94" font-family="Arial" font-size="12" font-weight="700">requirement</text>',
        '<text x="690" y="94" font-family="Arial" font-size="12" font-weight="700">status</text>',
    ]
    for idx, row in enumerate(decision_rows):
        y = 124 + idx * row_height
        status = str(row["decision_status"])
        fill = colors.get(status, "#777777")
        parts.extend(
            [
                f'<rect x="18" y="{y - 24}" width="{width - 36}" height="32" fill="#f7f7f7"/>',
                f'<text x="24" y="{y}" font-family="Arial" font-size="12" fill="#111">{row["decision_id"]}</text>',
                f'<rect x="690" y="{y - 18}" width="285" height="22" fill="{fill}"/>',
                f'<text x="986" y="{y}" font-family="Arial" font-size="11" fill="#111">{status}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _release_7_0_reduced_form_estimated(
    estimate_rows: list[dict[str, object]],
) -> bool:
    return bool(estimate_rows) and all(
        row.get("estimate_status")
        == "reduced_form_estimate_validation_only_not_proxy_svar"
        for row in estimate_rows
    )


def _release_7_0_selected_lag(lag_rows: list[dict[str, object]]) -> int:
    for row in lag_rows:
        if row.get("selected_by_bic") == "true":
            return int(row.get("lag_order", 0))
    return 0


def _release_7_0_proxy_support_observed(
    proxy_support_rows: list[dict[str, object]],
) -> str:
    if not proxy_support_rows:
        return "proxy_support_rows=0"
    parts = []
    for row in proxy_support_rows:
        parts.append(
            f"{row.get('support_id', '')}:n={row.get('n_obs', '')},"
            f"f={row.get('first_stage_f_stat', '')},"
            f"status={row.get('support_status', '')}"
        )
    return ";".join(parts)


def _release_7_0_audit_observed(
    timing_audit_rows: list[dict[str, object]],
) -> str:
    if not timing_audit_rows:
        return "timing_audit_rows=0"
    return ";".join(
        f"{row.get('audit_id', '')}={row.get('audit_status', '')}"
        for row in timing_audit_rows
    )


def _release_7_0_fmt(value: float) -> str:
    return f"{value:.6f}"


def _release_8_0_proxy_specification_audit_rows(
    *,
    system_panel_rows: list[dict[str, object]],
    selected_estimates: dict[str, dict[str, object]],
    lag_order: int,
) -> list[dict[str, object]]:
    event_rows: list[dict[str, object]] = []
    for row in system_panel_rows:
        event_count = int(row.get("proxy_event_count", 0))
        if event_count <= 0:
            continue
        proxy_bps = _float(row.get("sf_fed_proxy_shock_bps"))
        policy_change = _float(row.get("fed_funds_rate_change"))
        if proxy_bps is None or policy_change is None:
            continue
        event_rows.append(
            {
                "month": str(row["month"]),
                "proxy_bps": proxy_bps,
                "event_count": event_count,
                "policy_change": policy_change,
            }
        )
    policy_residual_by_month: dict[str, float] = {}
    policy_estimate = selected_estimates.get("fed_funds_rate")
    if policy_estimate is not None:
        policy_residual_by_month = {
            str(month): float(residual)
            for month, residual in zip(
                policy_estimate["months"], policy_estimate["residuals"]
            )
        }

    candidate_specs = [
        (
            "monthly_sum_100bp",
            "signed monthly sum of SF Fed orthogonalized surprises scaled to 100 bps",
            "pre_specified_admissible_signed_proxy",
        ),
        (
            "event_average_100bp",
            "signed monthly average surprise scaled to 100 bps when multiple FOMC events appear in a month",
            "pre_specified_admissible_signed_proxy",
        ),
        (
            "nonzero_monthly_sum_100bp",
            "signed monthly sum restricted to nonzero surprise months",
            "robustness_admissible_signed_proxy",
        ),
        (
            "winsorized_monthly_sum_100bp",
            "signed monthly sum with 5/95 winsorization, used only as a robustness diagnostic",
            "robustness_admissible_signed_proxy",
        ),
        (
            "absolute_surprise_magnitude",
            "absolute surprise magnitude discards the sign and is not a valid monetary-shock proxy",
            "rejected_not_signed_monetary_shock_proxy",
        ),
    ]
    rows: list[dict[str, object]] = []
    monthly_xs = [
        float(row["proxy_bps"]) / 100.0
        for row in event_rows
    ]
    winsorized_xs = _winsorized(monthly_xs)
    for spec_id, notes, role in candidate_specs:
        for target_id in (
            "fed_funds_rate_change_system_variable",
            "fed_funds_rate_reduced_form_residual",
        ):
            observations: list[tuple[str, float, float]] = []
            for index, row in enumerate(event_rows):
                if spec_id == "monthly_sum_100bp":
                    proxy = float(row["proxy_bps"]) / 100.0
                elif spec_id == "event_average_100bp":
                    proxy = float(row["proxy_bps"]) / max(int(row["event_count"]), 1)
                    proxy /= 100.0
                elif spec_id == "nonzero_monthly_sum_100bp":
                    proxy = float(row["proxy_bps"]) / 100.0
                    if abs(proxy) <= 0:
                        continue
                elif spec_id == "winsorized_monthly_sum_100bp":
                    proxy = winsorized_xs[index] if index < len(winsorized_xs) else 0.0
                else:
                    proxy = abs(float(row["proxy_bps"]) / 100.0)

                if target_id == "fed_funds_rate_change_system_variable":
                    target = _float(row.get("policy_change"))
                else:
                    target = policy_residual_by_month.get(str(row["month"]))
                if target is None:
                    continue
                observations.append((str(row["month"]), proxy, target))

            invalid = role == "rejected_not_signed_monetary_shock_proxy"
            rows.append(
                _release_8_0_proxy_specification_audit_row(
                    audit_id=f"{spec_id}_{target_id}",
                    proxy_specification=spec_id,
                    target_variable=target_id,
                    lag_order=lag_order,
                    observations=observations,
                    pre_specified_role=role,
                    invalid=invalid,
                    notes=notes,
                )
            )
    return rows


def _release_8_0_proxy_specification_audit_row(
    *,
    audit_id: str,
    proxy_specification: str,
    target_variable: str,
    lag_order: int,
    observations: list[tuple[str, float, float]],
    pre_specified_role: str,
    invalid: bool,
    notes: str,
) -> dict[str, object]:
    xs = [proxy for _month, proxy, _target in observations]
    ys = [target for _month, _proxy, target in observations]
    beta, se, t_stat = _ols_slope(xs, ys)
    f_stat = t_stat * t_stat
    months = [month for month, _proxy, _target in observations]
    years = {month[:4] for month in months}
    nonzero_proxy_months = sum(abs(proxy) > 0 for proxy in xs)
    support_pass = (
        not invalid
        and len(observations) >= 30
        and len(years) >= 8
        and nonzero_proxy_months >= 30
        and f_stat >= 10.0
        and _std(xs) > 0
        and _std(ys) > 0
    )
    if invalid:
        status = "rejected_invalid_unsigned_proxy_specification"
    elif support_pass:
        status = "proxy_specification_support_pass_not_claim_promotion"
    elif observations:
        status = "blocked_weak_or_insufficient_proxy_specification_support"
    else:
        status = "blocked_missing_proxy_specification_support"
    return {
        "audit_id": audit_id,
        "proxy_specification": proxy_specification,
        "target_variable": target_variable,
        "lag_order": lag_order if lag_order > 0 else "",
        "n_obs": len(observations),
        "sample_start": min(months, default=""),
        "sample_end": max(months, default=""),
        "unique_event_years": len(years),
        "nonzero_proxy_months": nonzero_proxy_months,
        "estimator": "diagnostic_first_stage_specification_audit_not_claim_promotion",
        "instrument_variable": "sf_fed_orthogonalized_surprise_100bp",
        "first_stage_beta": _release_7_0_fmt(beta) if observations else "",
        "first_stage_standard_error": _release_7_0_fmt(se) if observations else "",
        "first_stage_t_stat": _release_7_0_fmt(t_stat) if observations else "",
        "first_stage_f_stat": _release_7_0_fmt(f_stat) if observations else "",
        "required_first_stage_f_stat": "10.000000",
        "audit_status": status,
        "pre_specified_role": pre_specified_role,
        "raw_rate_change_identification_rejected": "true",
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "dynamic_identification_promotion_enabled": "false",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_8_0_structural_gap_rows(
    *,
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
    covariance_rows: list[dict[str, object]],
    proxy_support_rows: list[dict[str, object]],
    timing_audit_rows: list[dict[str, object]],
    proxy_spec_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    reduced_form_enabled = _release_7_0_reduced_form_estimated(estimate_rows)
    selected_lag = _release_7_0_selected_lag(lag_rows)
    strongest = _release_8_0_strongest_proxy_row(proxy_spec_rows)
    strongest_f = _release_8_0_float_from_row(strongest, "first_stage_f_stat")
    support_passes = [
        row for row in proxy_spec_rows
        if row.get("audit_status") == "proxy_specification_support_pass_not_claim_promotion"
    ]
    unresolved_audits = [
        row.get("audit_id", "")
        for row in timing_audit_rows
        if str(row.get("audit_status", "")).startswith("blocked")
    ]
    return [
        _release_8_0_gap_row(
            "reduced_form_system_surface",
            "diagnostic_enabled_not_structural_identification"
            if reduced_form_enabled
            else "blocked_missing_reduced_form_system",
            "outputs/tables/ratewall_release_7_0_reduced_form_system_estimates.csv",
            f"selected_lag={selected_lag};estimate_rows={len(estimate_rows)}",
            "estimated reduced-form diagnostic surface, plus structural restrictions",
            "carry_forward_reduced_form_diagnostics_only",
            "Reduced-form coefficients remain diagnostics, not structural monetary shocks.",
        ),
        _release_8_0_gap_row(
            "external_proxy_specification_frontier",
            "support_diagnostic_not_claim_promotion"
            if support_passes
            else "blocked_weak_or_missing_admissible_proxy_support",
            "outputs/tables/ratewall_release_8_0_proxy_specification_audit.csv",
            (
                f"strongest_spec={strongest.get('proxy_specification', '')};"
                f"strongest_target={strongest.get('target_variable', '')};"
                f"strongest_f={_release_7_0_fmt(strongest_f)}"
            ),
            "admissible signed external proxy with F-statistic >= 10 and enough event support",
            "publish_proxy_specification_audit_keep_structural_claim_disabled",
            "Release 8.0 audits signed proxy specifications instead of promoting weak first stages.",
        ),
        _release_8_0_gap_row(
            "timing_exogeneity_invertibility_restrictions",
            "blocked_structural_assumptions_unaudited"
            if unresolved_audits
            else "diagnostic_pass_not_claim_promotion",
            "outputs/tables/ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv",
            "blocked_audits=" + ";".join(unresolved_audits),
            "audited timing, exogeneity, invertibility, and exclusion restrictions",
            "reject_prose_only_structural_reconstruction",
            "A structural proxy-SVAR needs more than source-backed monthly joins.",
        ),
        _release_8_0_gap_row(
            "residual_stability_and_covariance_support",
            "diagnostic_enabled_not_invertibility_proof"
            if covariance_rows
            else "blocked_missing_residual_covariance",
            "outputs/tables/ratewall_release_7_0_residual_covariance.csv",
            f"covariance_rows={len(covariance_rows)}",
            "residual stability plus invertibility tests sufficient for structural promotion",
            "retain_covariance_as_diagnostic_only",
            "Residual covariance rows are useful review evidence but not a proof of invertibility.",
        ),
        _release_8_0_gap_row(
            "placebo_pretrend_and_state_support",
            "blocked_system_placebo_pretrend_not_established",
            "outputs/tables/ratewall_release_8_0_structural_gap_ledger.csv",
            "system_placebo_pretrend_rows=0",
            "system-specific placebo/pretrend diagnostics with sufficient support",
            "document_final_nonpromotion_requirement",
            "Earlier event-study placebo rows do not establish system-level proxy-SVAR exogeneity.",
        ),
        _release_8_0_gap_row(
            "explicit_structural_claim_promotion_gate",
            "disabled_fail_closed",
            "outputs/tables/ratewall_release_8_0_identification_decision.csv",
            "proxy_svar_claim_enabled=false;system_identification_claim_enabled=false",
            "all source/method gates plus explicit future promotion tests",
            "keep_all_structural_claim_switches_false",
            "The release cannot be promoted manually by narrative wording.",
        ),
        _release_8_0_gap_row(
            "optional_valuation_incidence_frontier",
            "disabled_fail_closed",
            "outputs/tables/treasury_valuation_engine_readiness_gate.csv",
            "pricing_output_enabled=false;reset_calendar_construction_enabled=false;incidence_claim_enabled=false",
            "explicit source/method, opt-in, and fail-closed tests",
            "keep_pricing_and_incidence_frontiers_disabled",
            "Release 8.0 is empirical-identification work, not pricing or welfare incidence.",
        ),
    ]


def _release_8_0_gap_row(
    gap_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    action: str,
    notes: str,
) -> dict[str, object]:
    return {
        "gap_id": gap_id,
        "gap_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_8_0_action": action,
        "raw_rate_change_identification_rejected": "true",
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "dynamic_identification_promotion_enabled": "false",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_8_0_identification_decision_rows(
    *,
    controlled_dynamic_enabled: bool,
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
    structural_gap_rows: list[dict[str, object]],
    proxy_spec_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    reduced_form_enabled = _release_7_0_reduced_form_estimated(estimate_rows)
    strongest = _release_8_0_strongest_proxy_row(proxy_spec_rows)
    strongest_f = _release_8_0_float_from_row(strongest, "first_stage_f_stat")
    blocked = [
        row
        for row in structural_gap_rows
        if str(row.get("gap_status", "")).startswith("blocked")
        or row.get("gap_status") == "disabled_fail_closed"
    ]
    return [
        _release_8_0_decision_row(
            "bounded_controlled_dynamic_lp_surface",
            "enabled_bounded_not_structural_system"
            if controlled_dynamic_enabled
            else "blocked_missing_controlled_dynamic_lp_surface",
            "outputs/tables/ratewall_controlled_dynamic_lp_results.csv",
            f"controlled_dynamic_lp_appendix_enabled={controlled_dynamic_enabled}",
            "bounded dynamic LP surface or final blocker",
            "carry_forward_bounded_dynamic_lp_only",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            bool(proxy_spec_rows),
            "Controlled dynamic LP rows remain bounded event-study evidence.",
        ),
        _release_8_0_decision_row(
            "reduced_form_system_surface",
            "enabled_diagnostic_not_structural"
            if reduced_form_enabled
            else "blocked_missing_reduced_form_system",
            "outputs/tables/ratewall_release_7_0_var_lag_selection.csv",
            f"selected_lag={_release_7_0_selected_lag(lag_rows)}",
            "reduced-form system diagnostics",
            "publish_as_diagnostic_surface_only",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            bool(proxy_spec_rows),
            "FEDFUNDS remains a policy variable in the system, not the monetary shock.",
        ),
        _release_8_0_decision_row(
            "admissible_proxy_specification_frontier",
            "blocked_or_diagnostic_not_promotion_ready"
            if blocked
            else "diagnostic_pass_not_claim_promotion",
            "outputs/tables/ratewall_release_8_0_proxy_specification_audit.csv",
            (
                f"strongest_spec={strongest.get('proxy_specification', '')};"
                f"strongest_f={_release_7_0_fmt(strongest_f)}"
            ),
            "proxy support plus timing/exogeneity/invertibility/placebo gates",
            "keep_structural_system_identification_disabled",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            bool(proxy_spec_rows),
            "No admissible proxy specification is allowed to promote claims alone.",
        ),
        _release_8_0_decision_row(
            "release_8_0_identification_decision",
            "structural_system_identification_not_promoted_final_bounded_package",
            "outputs/tables/ratewall_release_8_0_nonpromotion_proof.csv",
            "blocked_requirements=" + ";".join(
                str(row.get("gap_id", "")) for row in blocked
            ),
            "defensible structural system appendix or final non-promotion proof",
            "publish_release_8_0_final_nonpromotion_package",
            controlled_dynamic_enabled,
            reduced_form_enabled,
            bool(proxy_spec_rows),
            "Release 8.0 hardens the non-promotion proof instead of widening claims.",
        ),
    ]


def _release_8_0_decision_row(
    decision_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    action: str,
    controlled_dynamic_enabled: bool,
    reduced_form_enabled: bool,
    proxy_spec_audit_enabled: bool,
    notes: str,
) -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "decision_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_8_0_action": action,
        "controlled_dynamic_lp_appendix_enabled": str(controlled_dynamic_enabled).lower(),
        "reduced_form_system_diagnostics_enabled": str(reduced_form_enabled).lower(),
        "proxy_specification_audit_enabled": str(proxy_spec_audit_enabled).lower(),
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "valuation_incidence_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_8_0_nonpromotion_proof_rows(
    *,
    decision_rows: list[dict[str, object]],
    structural_gap_rows: list[dict[str, object]],
    proxy_spec_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    strongest = _release_8_0_strongest_proxy_row(proxy_spec_rows)
    strongest_f = _release_8_0_float_from_row(strongest, "first_stage_f_stat")
    blocked = [
        str(row.get("gap_id", ""))
        for row in structural_gap_rows
        if str(row.get("gap_status", "")).startswith("blocked")
        or row.get("gap_status") == "disabled_fail_closed"
    ]
    required = [
        f"{row['gap_id']}={row['required_value']}"
        for row in structural_gap_rows
        if str(row.get("gap_id", "")) in blocked
    ]
    final_status = next(
        (
            str(row.get("decision_status", ""))
            for row in decision_rows
            if row.get("decision_id") == "release_8_0_identification_decision"
        ),
        "structural_system_identification_not_promoted_final_bounded_package",
    )
    return [
        {
            "proof_id": "release_8_0_structural_system_nonpromotion_proof",
            "proof_status": final_status,
            "evidence_artifact": (
                "outputs/tables/ratewall_release_8_0_structural_gap_ledger.csv"
            ),
            "strongest_proxy_specification": strongest.get("proxy_specification", ""),
            "strongest_proxy_target": strongest.get("target_variable", ""),
            "strongest_proxy_f_stat": _release_7_0_fmt(strongest_f),
            "blocked_requirements": ";".join(blocked),
            "required_resolution": "; ".join(required),
            "release_8_0_action": (
                "publish_stronger_machine_readable_nonpromotion_proof"
            ),
            "raw_rate_change_identification_rejected": "true",
            "proxy_svar_claim_enabled": "false",
            "system_identification_claim_enabled": "false",
            "dynamic_identification_promotion_enabled": "false",
            "pricing_output_enabled": "false",
            "reset_calendar_construction_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "Release 8.0 audits alternative admissible external-proxy "
                "specifications and preserves the final non-promotion boundary "
                "because structural support remains incomplete."
            ),
        }
    ]


def _release_8_0_robustness_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    proxy_spec_rows: list[dict[str, object]],
    structural_gap_rows: list[dict[str, object]],
    proof_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
) -> dict[str, object]:
    strongest = _release_8_0_strongest_proxy_row(proxy_spec_rows)
    return {
        "schema": "ratewall.empirical_robustness_manifest.v8",
        "release": "8.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "release_8_0_proxy_specification_audit_rows": len(proxy_spec_rows),
        "release_8_0_structural_gap_rows": len(structural_gap_rows),
        "release_8_0_nonpromotion_proof_rows": len(proof_rows),
        "release_8_0_decision_rows": len(decision_rows),
        "release_8_0_decision_status_counts": _count_by(
            decision_rows, "decision_status"
        ),
        "selected_lag_order": _release_7_0_selected_lag(lag_rows),
        "reduced_form_system_diagnostics_enabled": _release_7_0_reduced_form_estimated(
            estimate_rows
        ),
        "strongest_proxy_specification": strongest.get("proxy_specification", ""),
        "strongest_proxy_target": strongest.get("target_variable", ""),
        "strongest_proxy_f_stat": _release_8_0_float_from_row(
            strongest, "first_stage_f_stat"
        ),
        "proxy_svar_claim_enabled": False,
        "system_identification_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "dynamic_identification_promotion_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "causal_claim_enabled": False,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "reset_calendar_construction_enabled": False,
        "release_8_0_decision": (
            "structural_system_identification_not_promoted_final_bounded_package"
        ),
        "artifact_role": (
            "admissible_proxy_specification_audit_with_final_nonpromotion_proof"
        ),
    }


def _release_8_0_system_identification_manifest(
    *,
    controlled_dynamic_enabled: bool,
    lag_rows: list[dict[str, object]],
    estimate_rows: list[dict[str, object]],
    proxy_spec_rows: list[dict[str, object]],
    structural_gap_rows: list[dict[str, object]],
    proof_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
) -> dict[str, object]:
    strongest = _release_8_0_strongest_proxy_row(proxy_spec_rows)
    return {
        "schema": "ratewall.release_8_0_system_identification_manifest.v1",
        "release": "8.0",
        "controlled_dynamic_lp_appendix_enabled": controlled_dynamic_enabled,
        "selected_lag_order": _release_7_0_selected_lag(lag_rows),
        "reduced_form_system_estimate_rows": len(estimate_rows),
        "proxy_specification_audit_rows": len(proxy_spec_rows),
        "structural_gap_ledger_rows": len(structural_gap_rows),
        "nonpromotion_proof_rows": len(proof_rows),
        "release_8_0_decision_rows": len(decision_rows),
        "release_8_0_decision_status_counts": _count_by(
            decision_rows, "decision_status"
        ),
        "release_8_0_decision": (
            "structural_system_identification_not_promoted_final_bounded_package"
        ),
        "reduced_form_system_diagnostics_enabled": _release_7_0_reduced_form_estimated(
            estimate_rows
        ),
        "strongest_proxy_specification": strongest.get("proxy_specification", ""),
        "strongest_proxy_target": strongest.get("target_variable", ""),
        "strongest_proxy_f_stat": _release_8_0_float_from_row(
            strongest, "first_stage_f_stat"
        ),
        "proxy_svar_claim_enabled": False,
        "system_identification_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "dynamic_identification_promotion_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "pricing_output_enabled": False,
        "reset_calendar_construction_enabled": False,
        "incidence_claim_enabled": False,
        "valuation_incidence_claim_enabled": False,
        "paper_claim_boundary": (
            "admissible_proxy_specification_audit_not_structural_system_identification"
        ),
    }


def _release_8_0_nonpromotion_appendix_text(
    *,
    proxy_spec_rows: list[dict[str, object]],
    structural_gap_rows: list[dict[str, object]],
    proof_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
) -> str:
    proof = proof_rows[0]
    lines = [
        "# RateWall Release 8.0 System-Identification Non-Promotion Appendix",
        "",
        "## Release Decision",
        "",
        "Release 8.0 audits admissible SF Fed external-proxy specifications "
        "against system targets and preserves a final non-promotion proof. It "
        "does not claim a structural proxy-SVAR/system result.",
        "",
        f"- Proxy specification audit rows: `{len(proxy_spec_rows)}`",
        f"- Structural gap rows: `{len(structural_gap_rows)}`",
        f"- Decision rows: `{len(decision_rows)}`",
        f"- Strongest proxy specification: `{proof['strongest_proxy_specification']}`",
        f"- Strongest first-stage F-statistic: `{proof['strongest_proxy_f_stat']}`",
        f"- Final proof status: `{proof['proof_status']}`",
        "- Raw policy-rate changes as shocks: rejected",
        "- Proxy-SVAR, system-identification, pricing, reset-calendar, and "
        "incidence outputs enabled: `false`",
        "",
        "## Proxy Specification Audit",
        "",
    ]
    for row in proxy_spec_rows:
        lines.append(
            f"- `{row['proxy_specification']}` to `{row['target_variable']}`: "
            f"`{row['audit_status']}`, n={row['n_obs']}, "
            f"F={row['first_stage_f_stat']}."
        )
    lines.extend(["", "## Structural Gap Ledger", ""])
    for row in structural_gap_rows:
        lines.append(
            f"- `{row['gap_id']}`: `{row['gap_status']}`; required "
            f"`{row['required_value']}`."
        )
    lines.extend(["", "## Decision Ledger", ""])
    for row in decision_rows:
        lines.append(
            f"- `{row['decision_id']}`: `{row['decision_status']}`; action "
            f"`{row['release_8_0_action']}`."
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "The SF Fed orthogonalized surprise remains the admissible shock "
            "surface. FEDFUNDS is used only as a system policy variable. The "
            "appendix does not claim that higher rates always raise inflation, "
            "does not claim the Federal Reserve has stopped working, and does "
            "not enable pricing, holder-incidence, tax, MPC, welfare, "
            "reset-calendar, or incidence outputs.",
            "",
        ]
    )
    return "\n".join(lines)


def _release_8_0_reviewer_response_text(
    *,
    proxy_spec_rows: list[dict[str, object]],
    structural_gap_rows: list[dict[str, object]],
    proof_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
) -> str:
    proof = proof_rows[0]
    blocked = [
        row for row in structural_gap_rows
        if str(row.get("gap_status", "")).startswith("blocked")
        or row.get("gap_status") == "disabled_fail_closed"
    ]
    lines = [
        "# RateWall Release 8.0 Reviewer Response",
        "",
        "## Reviewer Concern: Is there a stronger admissible proxy-SVAR design?",
        "",
        "Response: not in the current source-backed release. Release 8.0 "
        "audits signed SF Fed proxy specifications and documents the strongest "
        "observed support, but the structural promotion gates remain closed.",
        "",
        f"- Strongest audited specification: `{proof['strongest_proxy_specification']}`",
        f"- Strongest target: `{proof['strongest_proxy_target']}`",
        f"- Strongest F-statistic: `{proof['strongest_proxy_f_stat']}`",
        "",
        "## Proxy Specification Rows",
        "",
    ]
    for row in proxy_spec_rows:
        lines.append(
            f"- `{row['audit_id']}`: `{row['audit_status']}` "
            f"(F={row['first_stage_f_stat']})."
        )
    lines.extend(["", "## Remaining Blockers", ""])
    for row in blocked:
        lines.append(f"- `{row['gap_id']}` requires: {row['required_value']}")
    lines.extend(
        [
            "",
            "## Final Response",
            "",
            "The release remains a bounded accounting, scenario, dynamic-LP, "
            "and reduced-form system diagnostic package. It rejects raw rate "
            "changes as monetary shocks and keeps all pricing/incidence/welfare "
            "outputs disabled.",
            "",
            "## Decision Rows",
            "",
        ]
    )
    for row in decision_rows:
        lines.append(f"- `{row['decision_id']}`: `{row['decision_status']}`.")
    return "\n".join(lines) + "\n"


def _write_release_8_0_nonpromotion_figure(
    path: Path,
    *,
    decision_rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1240
    row_height = 40
    height = 126 + row_height * len(decision_rows)
    colors = {
        "enabled_bounded_not_structural_system": "#2f6f73",
        "enabled_diagnostic_not_structural": "#2f6f73",
        "blocked_or_diagnostic_not_promotion_ready": "#9a4d3f",
        "blocked_missing_controlled_dynamic_lp_surface": "#9a4d3f",
        "blocked_missing_reduced_form_system": "#9a4d3f",
        "diagnostic_pass_not_claim_promotion": "#b8752c",
        "structural_system_identification_not_promoted_final_bounded_package": "#7f5f28",
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="36" font-family="Arial" font-size="20" font-weight="700">RateWall Release 8.0 non-promotion gate</text>',
        '<text x="24" y="62" font-family="Arial" font-size="12" fill="#444">Admissible proxy-specification audit; structural proxy-SVAR/system, pricing, reset-calendar, and incidence claims remain disabled.</text>',
        '<text x="24" y="94" font-family="Arial" font-size="12" font-weight="700">decision</text>',
        '<text x="700" y="94" font-family="Arial" font-size="12" font-weight="700">status</text>',
    ]
    for idx, row in enumerate(decision_rows):
        y = 124 + idx * row_height
        status = str(row["decision_status"])
        fill = colors.get(status, "#777777")
        parts.extend(
            [
                f'<rect x="18" y="{y - 24}" width="{width - 36}" height="32" fill="#f7f7f7"/>',
                f'<text x="24" y="{y}" font-family="Arial" font-size="12" fill="#111">{row["decision_id"]}</text>',
                f'<rect x="700" y="{y - 18}" width="320" height="22" fill="{fill}"/>',
                f'<text x="1030" y="{y}" font-family="Arial" font-size="11" fill="#111">{status}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _release_8_0_strongest_proxy_row(
    proxy_spec_rows: list[dict[str, object]],
) -> dict[str, object]:
    valid = [
        row for row in proxy_spec_rows
        if row.get("pre_specified_role") != "rejected_not_signed_monetary_shock_proxy"
        and row.get("first_stage_f_stat")
    ]
    if not valid:
        return {}
    return max(valid, key=lambda row: _release_8_0_float_from_row(row, "first_stage_f_stat"))


def _release_8_0_float_from_row(row: dict[str, object], key: str) -> float:
    value = _float(row.get(key))
    return 0.0 if value is None else value


def _release_9_0_external_proxy_registry_rows(
    snapshot_bundle: Path,
) -> list[dict[str, object]]:
    snapshots = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in snapshots}
    rows = [
        _release_9_0_registry_row(
            source_id="sf_fed_monetary_policy_surprises",
            source_name="SF Fed Monetary Policy Surprises",
            source_url="https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/",
            snapshot=by_series.get("sf_fed_monetary_policy_surprises"),
            integration_status="already_integrated_admissible_proxy_frontier",
            normalized_proxy_column="orthogonalized_surprise_bps",
            notes="Carried forward as the baseline admissible signed high-frequency proxy.",
        ),
        _release_9_0_registry_row(
            source_id="fed_brw_monetary_policy_shocks",
            source_name="Federal Reserve BRW unified monetary policy shocks",
            source_url="https://www.federalreserve.gov/econres/feds/a-unified-measure-of-fed-monetary-policy-shocks.htm",
            snapshot=by_series.get("fed_brw_monetary_policy_shocks"),
            integration_status="new_release_9_0_live_integrated_external_proxy",
            normalized_proxy_column="monthly_shock_pctpt",
            notes="Official Federal Reserve research-data CSV integrated as an additional admissible external-proxy candidate.",
        ),
        _release_9_0_registry_row(
            source_id="sf_fed_usmpd",
            source_name="SF Fed U.S. Monetary Policy Event-Study Database",
            source_url="https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/",
            snapshot=None,
            integration_status="official_download_available_future_method_normalization",
            normalized_proxy_column="requires_documented_principal_component_construction",
            notes="Release 9.0 records the official USMPD source, but does not construct a structural proxy from workbook/R-code inputs by prose-only reconstruction.",
        ),
        _release_9_0_registry_row(
            source_id="romer_romer_narrative_shocks",
            source_name="Romer and Romer narrative monetary shocks",
            source_url="https://eml.berkeley.edu/~dromer/",
            snapshot=None,
            integration_status="literature_candidate_not_official_live_series_integrated",
            normalized_proxy_column="not_integrated",
            notes="Searched as a narrative-shock candidate; not used for Release 9.0 structural promotion without a current source-backed parser and harmonized sample audit.",
        ),
    ]
    return rows


def _release_9_0_registry_row(
    *,
    source_id: str,
    source_name: str,
    source_url: str,
    snapshot,
    integration_status: str,
    normalized_proxy_column: str,
    notes: str,
) -> dict[str, object]:
    records = list(snapshot.records if snapshot else [])
    months = sorted(
        str(record.get("month") or record.get("date") or record.get("fomc_date") or "")
        for record in records
        if record.get("month") or record.get("date") or record.get("fomc_date")
    )
    return {
        "source_id": source_id,
        "source_name": source_name,
        "source_url": snapshot.metadata.source_url if snapshot else source_url,
        "source_status": snapshot.metadata.snapshot_kind if snapshot else "not_in_snapshot",
        "integration_status": integration_status,
        "normalized_proxy_column": normalized_proxy_column,
        "sample_start": min(months, default=""),
        "sample_end": max(months, default=""),
        "n_rows": len(records),
        "retrieval_evidence": (
            snapshot.metadata.retrieved_at if snapshot else "web_source_audited_not_ingested"
        ),
        "structural_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_9_0_external_proxy_support_rows(
    *,
    snapshot_bundle: Path,
    system_panel_rows: list[dict[str, object]],
    selected_estimates: dict[str, dict[str, object]],
    lag_order: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    policy_residual_by_month: dict[str, float] = {}
    policy_estimate = selected_estimates.get("fed_funds_rate")
    if policy_estimate is not None:
        policy_residual_by_month = {
            str(month): float(residual)
            for month, residual in zip(
                policy_estimate["months"], policy_estimate["residuals"]
            )
        }
    rows.extend(
        _release_9_0_sf_fed_support_rows(
            system_panel_rows=system_panel_rows,
            policy_residual_by_month=policy_residual_by_month,
            lag_order=lag_order,
        )
    )
    rows.extend(
        _release_9_0_brw_support_rows(
            snapshot_bundle=snapshot_bundle,
            system_panel_rows=system_panel_rows,
            policy_residual_by_month=policy_residual_by_month,
            lag_order=lag_order,
        )
    )
    return rows


def _release_9_0_sf_fed_support_rows(
    *,
    system_panel_rows: list[dict[str, object]],
    policy_residual_by_month: dict[str, float],
    lag_order: int,
) -> list[dict[str, object]]:
    event_rows = []
    for row in system_panel_rows:
        if int(row.get("proxy_event_count", 0)) <= 0:
            continue
        proxy_bps = _float(row.get("sf_fed_proxy_shock_bps"))
        policy_change = _float(row.get("fed_funds_rate_change"))
        if proxy_bps is None or policy_change is None:
            continue
        event_rows.append(
            {
                "month": str(row["month"]),
                "proxy_100bp": proxy_bps / 100.0,
                "proxy_avg_100bp": proxy_bps / max(int(row["proxy_event_count"]), 1) / 100.0,
                "policy_change": policy_change,
            }
        )
    return _release_9_0_support_rows_for_source(
        source_id="sf_fed_monetary_policy_surprises",
        source_status="live_or_browser_download_in_snapshot",
        proxy_values=[
            ("sf_fed_monthly_sum_100bp", "orthogonalized monthly sum scaled to 100 bps", "proxy_100bp"),
            ("sf_fed_event_average_100bp", "orthogonalized event average scaled to 100 bps", "proxy_avg_100bp"),
        ],
        event_rows=event_rows,
        policy_residual_by_month=policy_residual_by_month,
        lag_order=lag_order,
    )


def _release_9_0_brw_support_rows(
    *,
    snapshot_bundle: Path,
    system_panel_rows: list[dict[str, object]],
    policy_residual_by_month: dict[str, float],
    lag_order: int,
) -> list[dict[str, object]]:
    snapshots = read_snapshot_bundle(snapshot_bundle)
    brw = next(
        (
            snapshot
            for snapshot in snapshots
            if snapshot.metadata.series_id == "fed_brw_monetary_policy_shocks"
        ),
        None,
    )
    if brw is None:
        return [
            _release_9_0_support_row(
                audit_id="fed_brw_monthly_100bp_missing_snapshot",
                proxy_source="fed_brw_monetary_policy_shocks",
                proxy_specification="brw_monthly_100bp",
                target_variable="fed_funds_rate_change_system_variable",
                lag_order=lag_order,
                observations=[],
                source_status="missing_input",
                notes="BRW source was not present in the snapshot bundle.",
            )
        ]
    system_by_month = {str(row["month"]): row for row in system_panel_rows}
    event_rows: list[dict[str, object]] = []
    for record in brw.records:
        month = str(record.get("month", ""))
        system_row = system_by_month.get(month)
        shock = _float(record.get("monthly_shock_pctpt"))
        policy_change = _float(system_row.get("fed_funds_rate_change")) if system_row else None
        if not month or shock is None or policy_change is None:
            continue
        event_rows.append(
            {
                "month": month,
                "proxy_100bp": shock,
                "proxy_nonzero_100bp": shock,
                "policy_change": policy_change,
            }
        )
    return _release_9_0_support_rows_for_source(
        source_id="fed_brw_monetary_policy_shocks",
        source_status=brw.metadata.snapshot_kind,
        proxy_values=[
            ("brw_monthly_100bp", "BRW monthly policy shock in percentage points, scaled as 100 bps units", "proxy_100bp"),
            ("brw_nonzero_monthly_100bp", "BRW monthly policy shock restricted to nonzero months", "proxy_nonzero_100bp"),
        ],
        event_rows=event_rows,
        policy_residual_by_month=policy_residual_by_month,
        lag_order=lag_order,
    )


def _release_9_0_support_rows_for_source(
    *,
    source_id: str,
    source_status: str,
    proxy_values: list[tuple[str, str, str]],
    event_rows: list[dict[str, object]],
    policy_residual_by_month: dict[str, float],
    lag_order: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for specification, notes, proxy_field in proxy_values:
        for target_variable in (
            "fed_funds_rate_change_system_variable",
            "fed_funds_rate_reduced_form_residual",
        ):
            observations: list[tuple[str, float, float]] = []
            for row in event_rows:
                proxy = _float(row.get(proxy_field))
                if proxy is None:
                    continue
                if "nonzero" in specification and abs(proxy) <= 0:
                    continue
                if target_variable == "fed_funds_rate_change_system_variable":
                    target = _float(row.get("policy_change"))
                else:
                    target = policy_residual_by_month.get(str(row["month"]))
                if target is None:
                    continue
                observations.append((str(row["month"]), proxy, target))
            rows.append(
                _release_9_0_support_row(
                    audit_id=f"{source_id}_{specification}_{target_variable}",
                    proxy_source=source_id,
                    proxy_specification=specification,
                    target_variable=target_variable,
                    lag_order=lag_order,
                    observations=observations,
                    source_status=source_status,
                    notes=notes,
                )
            )
    return rows


def _release_9_0_support_row(
    *,
    audit_id: str,
    proxy_source: str,
    proxy_specification: str,
    target_variable: str,
    lag_order: int,
    observations: list[tuple[str, float, float]],
    source_status: str,
    notes: str,
) -> dict[str, object]:
    xs = [proxy for _month, proxy, _target in observations]
    ys = [target for _month, _proxy, target in observations]
    beta, se, t_stat = _ols_slope(xs, ys)
    f_stat = t_stat * t_stat
    months = [month for month, _proxy, _target in observations]
    years = {month[:4] for month in months}
    nonzero_proxy_months = sum(abs(proxy) > 0 for proxy in xs)
    support_pass = (
        len(observations) >= 30
        and len(years) >= 8
        and nonzero_proxy_months >= 30
        and f_stat >= 10.0
        and _std(xs) > 0
        and _std(ys) > 0
    )
    status = (
        "proxy_relevance_support_pass_structural_gates_still_required"
        if support_pass
        else "blocked_weak_or_insufficient_external_proxy_support"
        if observations
        else "blocked_missing_external_proxy_overlap"
    )
    return {
        "audit_id": audit_id,
        "proxy_source": proxy_source,
        "proxy_specification": proxy_specification,
        "target_variable": target_variable,
        "n_obs": len(observations),
        "sample_start": min(months, default=""),
        "sample_end": max(months, default=""),
        "unique_event_years": len(years),
        "nonzero_proxy_months": nonzero_proxy_months,
        "estimator": "diagnostic_first_stage_external_proxy_audit_not_structural_promotion",
        "instrument_variable": proxy_specification,
        "first_stage_beta": _release_7_0_fmt(beta) if observations else "",
        "first_stage_standard_error": _release_7_0_fmt(se) if observations else "",
        "first_stage_t_stat": _release_7_0_fmt(t_stat) if observations else "",
        "first_stage_f_stat": _release_7_0_fmt(f_stat) if observations else "",
        "required_first_stage_f_stat": "10.000000",
        "audit_status": status,
        "source_status": source_status,
        "raw_rate_change_identification_rejected": "true",
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "dynamic_identification_promotion_enabled": "false",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_9_0_structural_identification_decision_rows(
    *,
    registry_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    strongest = _release_9_0_strongest_support_row(support_rows)
    strongest_f = _release_8_0_float_from_row(strongest, "first_stage_f_stat")
    support_passes = [
        row
        for row in support_rows
        if row.get("audit_status")
        == "proxy_relevance_support_pass_structural_gates_still_required"
    ]
    live_integrated = [
        row
        for row in registry_rows
        if "integrated" in str(row.get("integration_status", ""))
        and row.get("source_status") not in {"not_in_snapshot", "missing_input"}
    ]
    return [
        _release_9_0_decision_row(
            "external_proxy_source_expansion",
            "enabled_source_backed_external_proxy_frontier"
            if len(live_integrated) >= 2
            else "blocked_insufficient_live_external_proxy_frontier",
            "outputs/tables/ratewall_release_9_0_external_proxy_source_registry.csv",
            f"integrated_sources={len(live_integrated)}",
            "serious search plus at least two source-backed admissible proxy candidates",
            "publish_expanded_proxy_registry",
            False,
            "Release 9.0 adds BRW and records USMPD/literature frontier status.",
        ),
        _release_9_0_decision_row(
            "expanded_proxy_relevance_support",
            "support_diagnostic_pass_not_structural_promotion"
            if support_passes
            else "blocked_weak_or_insufficient_expanded_proxy_support",
            "outputs/tables/ratewall_release_9_0_external_proxy_support_audit.csv",
            (
                f"strongest_source={strongest.get('proxy_source', '')};"
                f"strongest_spec={strongest.get('proxy_specification', '')};"
                f"strongest_f={_release_7_0_fmt(strongest_f)}"
            ),
            "F-statistic >= 10 plus enough support, followed by structural gates",
            "publish_support_audit_keep_claim_promotion_disabled",
            False,
            "Proxy support alone is not a structural proxy-SVAR result.",
        ),
        _release_9_0_decision_row(
            "timing_exogeneity_invertibility_placebo_gate",
            "blocked_structural_assumption_stack_not_promoted",
            "outputs/tables/ratewall_release_9_0_final_nonpromotion_proof.csv",
            "system_timing_exogeneity_invertibility_placebo_gate=false",
            "audited timing, exogeneity, invertibility, placebo/pretrend, rank, and claim-promotion gates",
            "reject_structural_promotion_from_external_proxy_strength_alone",
            False,
            "Even a stronger proxy needs the full structural assumption stack.",
        ),
        _release_9_0_decision_row(
            "release_9_0_structural_identification_decision",
            "structural_system_identification_not_promoted_final_publication_boundary",
            "outputs/tables/ratewall_release_9_0_final_nonpromotion_proof.csv",
            "proxy_svar_claim_enabled=false;system_identification_claim_enabled=false",
            "defensible structural appendix or final non-promotion boundary",
            "publish_release_9_0_final_publication_boundary_package",
            False,
            "Release 9.0 expands the proxy frontier without widening claims.",
        ),
    ]


def _release_9_0_decision_row(
    decision_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    action: str,
    structural_appendix_enabled: bool,
    notes: str,
) -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "decision_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_9_0_action": action,
        "expanded_external_proxy_frontier_enabled": "true",
        "defensible_structural_appendix_enabled": str(structural_appendix_enabled).lower(),
        "proxy_svar_claim_enabled": "false",
        "system_identification_claim_enabled": "false",
        "valuation_incidence_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "reset_calendar_construction_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_9_0_nonpromotion_proof_rows(
    *,
    decision_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    strongest = _release_9_0_strongest_support_row(support_rows)
    strongest_f = _release_8_0_float_from_row(strongest, "first_stage_f_stat")
    blocked = [
        str(row.get("decision_id", ""))
        for row in decision_rows
        if str(row.get("decision_status", "")).startswith("blocked")
        or row.get("decision_status")
        == "structural_system_identification_not_promoted_final_publication_boundary"
    ]
    required = [
        f"{row['decision_id']}={row['required_value']}"
        for row in decision_rows
        if row["decision_id"] in blocked
    ]
    return [
        {
            "proof_id": "release_9_0_structural_system_nonpromotion_proof",
            "proof_status": "structural_system_identification_not_promoted_final_publication_boundary",
            "evidence_artifact": (
                "outputs/tables/ratewall_release_9_0_external_proxy_support_audit.csv"
            ),
            "strongest_proxy_source": strongest.get("proxy_source", ""),
            "strongest_proxy_specification": strongest.get("proxy_specification", ""),
            "strongest_proxy_target": strongest.get("target_variable", ""),
            "strongest_proxy_f_stat": _release_7_0_fmt(strongest_f),
            "blocked_requirements": ";".join(blocked),
            "required_resolution": "; ".join(required),
            "release_9_0_action": "publish_expanded_proxy_frontier_with_final_nonpromotion_boundary",
            "raw_rate_change_identification_rejected": "true",
            "proxy_svar_claim_enabled": "false",
            "system_identification_claim_enabled": "false",
            "dynamic_identification_promotion_enabled": "false",
            "pricing_output_enabled": "false",
            "reset_calendar_construction_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "Release 9.0 integrates the Federal Reserve BRW shock series "
                "and audits the expanded external-proxy frontier, but keeps "
                "structural system identification unpromoted."
            ),
        }
    ]


def _release_9_0_structural_identification_manifest(
    *,
    registry_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    proof_rows: list[dict[str, object]],
    lag_order: int,
) -> dict[str, object]:
    strongest = _release_9_0_strongest_support_row(support_rows)
    return {
        "schema": "ratewall.release_9_0_structural_identification_manifest.v1",
        "release": "9.0",
        "external_proxy_registry_rows": len(registry_rows),
        "external_proxy_support_rows": len(support_rows),
        "decision_rows": len(decision_rows),
        "nonpromotion_proof_rows": len(proof_rows),
        "selected_lag_order": lag_order,
        "integrated_proxy_sources": sorted(
            {
                str(row.get("source_id", ""))
                for row in registry_rows
                if "integrated" in str(row.get("integration_status", ""))
            }
        ),
        "strongest_proxy_source": strongest.get("proxy_source", ""),
        "strongest_proxy_specification": strongest.get("proxy_specification", ""),
        "strongest_proxy_target": strongest.get("target_variable", ""),
        "strongest_proxy_f_stat": _release_8_0_float_from_row(
            strongest, "first_stage_f_stat"
        ),
        "release_9_0_decision": (
            "structural_system_identification_not_promoted_final_publication_boundary"
        ),
        "proxy_svar_claim_enabled": False,
        "system_identification_claim_enabled": False,
        "defensible_structural_appendix_enabled": False,
        "dynamic_identification_promotion_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "pricing_output_enabled": False,
        "reset_calendar_construction_enabled": False,
        "incidence_claim_enabled": False,
        "artifact_role": (
            "expanded_external_proxy_frontier_with_final_publication_boundary"
        ),
    }


def _release_9_0_structural_boundary_appendix_text(
    *,
    registry_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    proof_rows: list[dict[str, object]],
) -> str:
    proof = proof_rows[0]
    lines = [
        "# RateWall Release 9.0 Structural Boundary Appendix",
        "",
        "## Release Decision",
        "",
        "Release 9.0 seriously expands the admissible external-proxy frontier "
        "by adding the Federal Reserve BRW shock series and recording the "
        "official SF Fed USMPD source as a future method-normalization path. "
        "It does not promote a structural proxy-SVAR/system claim.",
        "",
        f"- Source registry rows: `{len(registry_rows)}`",
        f"- External proxy support rows: `{len(support_rows)}`",
        f"- Decision rows: `{len(decision_rows)}`",
        f"- Strongest proxy source: `{proof['strongest_proxy_source']}`",
        f"- Strongest proxy specification: `{proof['strongest_proxy_specification']}`",
        f"- Strongest first-stage F-statistic: `{proof['strongest_proxy_f_stat']}`",
        "- Raw policy-rate changes as shocks: rejected",
        "- Proxy-SVAR, system-identification, pricing, reset-calendar, and incidence outputs enabled: `false`",
        "",
        "## External Proxy Source Registry",
        "",
    ]
    for row in registry_rows:
        lines.append(
            f"- `{row['source_id']}`: `{row['integration_status']}` "
            f"({row['source_status']}, rows={row['n_rows']})."
        )
    lines.extend(["", "## Support Audit", ""])
    for row in support_rows:
        lines.append(
            f"- `{row['audit_id']}`: `{row['audit_status']}`, "
            f"n={row['n_obs']}, F={row['first_stage_f_stat']}."
        )
    lines.extend(["", "## Decision Ledger", ""])
    for row in decision_rows:
        lines.append(
            f"- `{row['decision_id']}`: `{row['decision_status']}`; action "
            f"`{row['release_9_0_action']}`."
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "The expanded proxy frontier is a support audit, not a structural "
            "causal appendix. The release does not claim that higher rates "
            "always raise inflation, does not claim the Federal Reserve has "
            "stopped working, and does not enable pricing, holder-incidence, "
            "tax, MPC, welfare, reset-calendar, or incidence outputs.",
            "",
        ]
    )
    return "\n".join(lines)


def _release_9_0_review_packet_text(
    *,
    registry_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    proof_rows: list[dict[str, object]],
) -> str:
    proof = proof_rows[0]
    lines = [
        "# RateWall Release 9.0 External Proxy Review Packet",
        "",
        "## Reviewer Question: Did the release search beyond the baseline proxy?",
        "",
        "Response: yes. Release 9.0 adds the official Federal Reserve BRW "
        "shock CSV and records the SF Fed USMPD official source path, then "
        "runs fail-closed support diagnostics. It does not use raw policy-rate "
        "changes as shocks.",
        "",
        f"- Registry rows: `{len(registry_rows)}`",
        f"- Support rows: `{len(support_rows)}`",
        f"- Strongest audited proxy: `{proof['strongest_proxy_source']}` / "
        f"`{proof['strongest_proxy_specification']}`",
        f"- Strongest F-statistic: `{proof['strongest_proxy_f_stat']}`",
        "",
        "## Decision",
        "",
    ]
    for row in decision_rows:
        lines.append(f"- `{row['decision_id']}`: `{row['decision_status']}`.")
    lines.extend(
        [
            "",
            "## Remaining Boundary",
            "",
            "External-proxy relevance, by itself, does not establish timing, "
            "exogeneity, invertibility, placebo/pretrend, or claim-promotion "
            "requirements. Release 9.0 therefore remains a publication-boundary "
            "package rather than a structural system-identification promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_release_9_0_boundary_figure(
    path: Path,
    *,
    decision_rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1280
    row_height = 42
    height = 126 + row_height * len(decision_rows)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="36" font-family="Arial" font-size="20" font-weight="700">RateWall Release 9.0 structural boundary</text>',
        '<text x="24" y="62" font-family="Arial" font-size="12" fill="#444">Expanded admissible external-proxy frontier; structural proxy-SVAR/system, pricing, reset-calendar, and incidence claims remain disabled.</text>',
        '<text x="24" y="94" font-family="Arial" font-size="12" font-weight="700">decision</text>',
        '<text x="710" y="94" font-family="Arial" font-size="12" font-weight="700">status</text>',
    ]
    for idx, row in enumerate(decision_rows):
        y = 124 + idx * row_height
        status = str(row["decision_status"])
        fill = "#2f6f73" if status.startswith("enabled") else "#9a4d3f"
        if "not_promoted" in status:
            fill = "#7f5f28"
        parts.extend(
            [
                f'<rect x="18" y="{y - 24}" width="{width - 36}" height="34" fill="#f7f7f7"/>',
                f'<text x="24" y="{y}" font-family="Arial" font-size="12" fill="#111">{row["decision_id"]}</text>',
                f'<rect x="710" y="{y - 18}" width="330" height="22" fill="{fill}"/>',
                f'<text x="1050" y="{y}" font-family="Arial" font-size="11" fill="#111">{status}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _release_9_0_strongest_support_row(
    support_rows: list[dict[str, object]],
) -> dict[str, object]:
    valid = [row for row in support_rows if row.get("first_stage_f_stat")]
    if not valid:
        return {}
    return max(valid, key=lambda row: _release_8_0_float_from_row(row, "first_stage_f_stat"))


def _causal_identification_audit_rows(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    event_rows = [
        row
        for row in result_rows
        if row["artifact_layer"] == "empirical_event_study_estimate"
    ]
    association_rows = [
        row for row in result_rows if row["artifact_layer"] == "empirical_estimate_bounded"
    ]
    valid_panel_rows = [
        row
        for row in panel_rows
        if row.get("panel_status") == "audited_source_backed_event_outcome"
    ]
    outcomes = sorted({str(row.get("outcome_variable", "")) for row in valid_panel_rows})
    horizons = sorted({str(row.get("horizon_months", "")) for row in valid_panel_rows})
    min_event_n = min(
        (int(row["n_obs"]) for row in event_rows if str(row.get("n_obs", "")).isdigit()),
        default=0,
    )
    statuses = {
        str(row.get("result_status", ""))
        for row in result_rows
        if row.get("result_status")
    }
    raw_rate_rejected = all(
        row.get("raw_rate_change_identification_rejected") == "true"
        for row in result_rows
    )
    rows = [
        _causal_audit_row(
            "admissible_external_shock_source",
            "pass" if smoke_rows else "fail",
            "outputs/tables/empirical_smoke_panel.csv",
            f"sf_fed_orthogonalized_surprise_rows={len(smoke_rows)}",
            "nonempty admissible external shock panel",
            "bounded_event_study_allowed",
            raw_rate_rejected,
            "SF Fed orthogonalized surprises are an admissible shock/proxy surface.",
        ),
        _causal_audit_row(
            "official_outcome_panel",
            "pass" if valid_panel_rows and len(outcomes) >= 3 else "fail",
            "outputs/tables/ratewall_empirical_outcome_panel.csv",
            f"valid_rows={len(valid_panel_rows)};outcomes={','.join(outcomes)};horizons={','.join(horizons)}",
            "official outcome rows for inflation, output, and labor-market proxies",
            "bounded_event_study_allowed",
            raw_rate_rejected,
            "Outcome rows are pulled from official/source-backed series and aligned to events.",
        ),
        _causal_audit_row(
            "bounded_event_study_support",
            "pass" if event_rows and min_event_n >= 30 else "fail",
            "outputs/tables/ratewall_empirical_results.csv",
            f"event_study_rows={len(event_rows)};min_n={min_event_n}",
            "event-study rows with adequate per-row support for descriptive estimates",
            "bounded_event_study_allowed",
            raw_rate_rejected,
            "These estimates are reported as bounded event-study evidence only.",
        ),
        _causal_audit_row(
            "state_dependent_descriptive_support",
            "pass" if len(association_rows) >= 4 else "fail",
            "outputs/tables/ratewall_empirical_results.csv",
            f"association_rows={len(association_rows)}",
            "source-backed shock/state association rows",
            "descriptive_association_allowed",
            raw_rate_rejected,
            "State associations support diagnostics, not a causal transmission claim.",
        ),
        _causal_audit_row(
            "dynamic_lp_proxy_svar_identification",
            "blocked",
            "outputs/tables/ratewall_empirical_results.csv",
            f"statuses={','.join(sorted(statuses))}",
            "audited dynamic specification, lag/control design, horizon-by-state support diagnostics, and proxy-SVAR design",
            "final_blocker_full_lp_proxy_svar_not_defensible_release_1_1",
            raw_rate_rejected,
            "Release 1.1 does not widen the causal claim beyond bounded event-study evidence.",
        ),
        _causal_audit_row(
            "raw_rate_change_rejection",
            "pass" if raw_rate_rejected else "fail",
            "outputs/tables/ratewall_empirical_results.csv",
            f"raw_rate_change_identification_rejected={raw_rate_rejected}",
            "all empirical rows reject raw policy-rate changes as shocks",
            "required_guardrail_satisfied",
            raw_rate_rejected,
            "Raw policy-rate changes remain inadmissible.",
        ),
    ]
    return rows


def _event_study_support_diagnostic_rows(
    panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    groups = sorted(
        {
            (str(row["outcome_variable"]), int(row["horizon_months"]))
            for row in panel_rows
            if row.get("panel_status") == "audited_source_backed_event_outcome"
        }
    )
    if not groups:
        return [
            {
                "diagnostic_id": "support_no_audited_event_cells",
                "outcome_variable": "",
                "horizon_months": "",
                "sample_start": "",
                "sample_end": "",
                "n_obs": 0,
                "unique_event_years": 0,
                "min_shock_bps": "",
                "max_shock_bps": "",
                "mean_abs_shock_bps": "",
                "state_variable": "public_liability_base_1y_gdp",
                "state_median": "",
                "low_state_n": 0,
                "high_state_n": 0,
                "support_status": "support_limited_no_audited_event_cells",
                "raw_rate_change_identification_rejected": "true",
                "bounded_event_study_appendix_enabled": "false",
                "full_lp_proxy_svar_claim_enabled": "false",
                "notes": (
                    "No audited event-study outcome cells were available in this "
                    "snapshot; keep stronger empirical claims blocked."
                ),
            }
        ]
    for outcome, horizon in groups:
        observations = _event_observations(panel_rows, outcome, horizon)
        shocks = [shock * 100.0 for event_date, shock, _y, _state, _pre in observations]
        states = [state for _event_date, _shock, _y, state, _pre in observations]
        event_years = {event_date[:4] for event_date, _shock, _y, _state, _pre in observations}
        state_median = median(states) if states else 0.0
        low_state_n = sum(state <= state_median for state in states)
        high_state_n = sum(state > state_median for state in states)
        support_pass = (
            len(observations) >= 30
            and len(event_years) >= 5
            and low_state_n >= 10
            and high_state_n >= 10
            and max(shocks, default=0.0) > min(shocks, default=0.0)
        )
        rows.append(
            {
                "diagnostic_id": f"support_{outcome}_{horizon}m",
                "outcome_variable": outcome,
                "horizon_months": horizon,
                "sample_start": min((event_date for event_date, *_ in observations), default=""),
                "sample_end": max((event_date for event_date, *_ in observations), default=""),
                "n_obs": len(observations),
                "unique_event_years": len(event_years),
                "min_shock_bps": f"{min(shocks):.6f}" if shocks else "",
                "max_shock_bps": f"{max(shocks):.6f}" if shocks else "",
                "mean_abs_shock_bps": f"{_mean([abs(value) for value in shocks]):.6f}"
                if shocks
                else "",
                "state_variable": "public_liability_base_1y_gdp",
                "state_median": f"{state_median:.6f}" if states else "",
                "low_state_n": low_state_n,
                "high_state_n": high_state_n,
                "support_status": (
                    "submission_support_pass_bounded_event_study"
                    if support_pass
                    else "support_limited_keep_stronger_claim_blocked"
                ),
                "raw_rate_change_identification_rejected": "true",
                "bounded_event_study_appendix_enabled": str(support_pass).lower(),
                "full_lp_proxy_svar_claim_enabled": "false",
                "notes": (
                    "Support diagnostic for bounded SF Fed shock event-study rows. "
                    "It does not authorize full dynamic LP/proxy-SVAR claims."
                ),
            }
        )
    return rows


def _event_study_robustness_rows(
    panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    groups = sorted(
        {
            (str(row["outcome_variable"]), int(row["horizon_months"]))
            for row in panel_rows
            if row.get("panel_status") == "audited_source_backed_event_outcome"
        }
    )
    for outcome, horizon in groups:
        observations = _event_observations(panel_rows, outcome, horizon)
        if len(observations) < 8:
            continue
        shocks = [shock for _event_date, shock, _y, _state, _pre in observations]
        ys = [y for _event_date, _shock, y, _state, _pre in observations]
        baseline_beta, baseline_se, baseline_t = _ols_slope(shocks, ys)
        rows.append(
            _robustness_row(
                outcome=outcome,
                horizon=horizon,
                diagnostic_type="baseline_external_shock_event_study",
                estimator="single_shock_event_study_ols_per_100bp",
                n_obs=len(observations),
                baseline=baseline_beta,
                estimate=baseline_beta,
                standard_error=baseline_se,
                t_stat=baseline_t,
                response_unit=_response_unit(outcome),
                status="baseline_bounded_event_study_estimate",
                notes="Baseline reduced-form event-study slope using SF Fed orthogonalized surprises.",
            )
        )
        capped_shocks = _winsorized(shocks)
        winsor_beta, winsor_se, winsor_t = _ols_slope(capped_shocks, ys)
        rows.append(
            _robustness_row(
                outcome=outcome,
                horizon=horizon,
                diagnostic_type="winsorized_shock_5_95",
                estimator="single_shock_event_study_ols_winsorized_shock_per_100bp",
                n_obs=len(observations),
                baseline=baseline_beta,
                estimate=winsor_beta,
                standard_error=winsor_se,
                t_stat=winsor_t,
                response_unit=_response_unit(outcome),
                status="robustness_check_not_full_lp",
                notes="Shock-tail sensitivity check; bounded event-study evidence only.",
            )
        )
        drop_index = max(range(len(observations)), key=lambda idx: abs(shocks[idx]))
        dropped = [obs for idx, obs in enumerate(observations) if idx != drop_index]
        dropped_beta, dropped_se, dropped_t = _ols_slope(
            [shock for _event_date, shock, _y, _state, _pre in dropped],
            [y for _event_date, _shock, y, _state, _pre in dropped],
        )
        rows.append(
            _robustness_row(
                outcome=outcome,
                horizon=horizon,
                diagnostic_type="drop_largest_absolute_surprise",
                estimator="single_shock_event_study_ols_drop_max_abs_shock_per_100bp",
                n_obs=len(dropped),
                baseline=baseline_beta,
                estimate=dropped_beta,
                standard_error=dropped_se,
                t_stat=dropped_t,
                response_unit=_response_unit(outcome),
                status="robustness_check_not_full_lp",
                notes="Influence check dropping the largest absolute SF Fed surprise.",
            )
        )
        pre_values = [pre for _event_date, _shock, _y, _state, pre in observations]
        balance_beta, balance_se, balance_t = _ols_slope(shocks, pre_values)
        rows.append(
            _robustness_row(
                outcome=outcome,
                horizon=horizon,
                diagnostic_type="predetermined_outcome_balance",
                estimator="pre_event_outcome_level_on_external_shock",
                n_obs=len(observations),
                baseline=baseline_beta,
                estimate=balance_beta,
                standard_error=balance_se,
                t_stat=balance_t,
                response_unit="pre_outcome_level_per_100bp_surprise",
                status="balance_diagnostic_not_outcome_response",
                notes=(
                    "Predetermined outcome balance check. It is not a policy "
                    "response estimate and does not use raw rate changes."
                ),
            )
        )
    return rows


def _submission_identification_decision_rows(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    event_rows = [
        row
        for row in result_rows
        if row["artifact_layer"] == "empirical_event_study_estimate"
    ]
    support_ready = support_rows and all(
        row["support_status"] == "submission_support_pass_bounded_event_study"
        for row in support_rows
    )
    robustness_ready = len(robustness_rows) >= max(1, len(event_rows) * 4)
    raw_rate_rejected = all(
        row.get("raw_rate_change_identification_rejected") == "true"
        for row in result_rows
    )
    rows = [
        _submission_decision_row(
            "admissible_external_shock",
            "pass" if smoke_rows and raw_rate_rejected else "fail",
            "outputs/tables/empirical_smoke_panel.csv",
            f"shock_rows={len(smoke_rows)};raw_rate_rejected={raw_rate_rejected}",
            "nonempty SF Fed orthogonalized monetary-surprise panel and raw-rate rejection",
            "use_as_external_shock_for_bounded_event_study",
            bool(smoke_rows and raw_rate_rejected),
            "SF Fed surprises provide the admissible shock surface.",
        ),
        _submission_decision_row(
            "audited_outcome_state_panel",
            "pass" if panel_rows else "fail",
            "outputs/tables/ratewall_empirical_outcome_panel.csv",
            f"outcome_panel_rows={len(panel_rows)}",
            "source-backed outcome/state rows aligned to monetary-policy events",
            "use_as_submission_outcome_panel_with_limits",
            bool(panel_rows),
            "Outcome/state panels remain source-backed and timestamped.",
        ),
        _submission_decision_row(
            "support_diagnostics",
            "pass" if support_ready else "fail",
            "outputs/tables/ratewall_event_study_support_diagnostics.csv",
            f"support_rows={len(support_rows)};passing_rows={sum(row['support_status'] == 'submission_support_pass_bounded_event_study' for row in support_rows)}",
            "all event-study outcome/horizon cells pass bounded-support diagnostics",
            "use_support_table_as_submission_diagnostic",
            bool(support_ready),
            "Support diagnostics are necessary but not sufficient for full LP/proxy-SVAR claims.",
        ),
        _submission_decision_row(
            "robustness_diagnostics",
            "pass" if robustness_ready else "fail",
            "outputs/tables/ratewall_event_study_robustness.csv",
            f"robustness_rows={len(robustness_rows)};event_rows={len(event_rows)}",
            "baseline, shock-tail, influence, and predetermined-outcome diagnostics for each event-study row",
            "use_robustness_table_as_submission_diagnostic",
            bool(robustness_ready),
            "Robustness checks are reduced-form diagnostics, not a full dynamic model.",
        ),
        _submission_decision_row(
            "full_lp_proxy_svar_identification",
            "blocked",
            "outputs/tables/ratewall_submission_identification_decision.csv",
            "missing_audited_dynamic_lag_control_design_hac_serial_correlation_and_proxy_svar_system",
            "pre-specified dynamic controls/lags, HAC or clustered uncertainty, serial-correlation diagnostics, instrument relevance by horizon, and proxy-SVAR system checks",
            "block_full_lp_proxy_svar_claims_release_2_0",
            False,
            "Release 2.0 does not claim a full LP/proxy-SVAR transmission design.",
        ),
        _submission_decision_row(
            "release_2_0_submission_decision",
            "submission_ready_bounded_event_study_full_lp_proxy_svar_blocked"
            if support_ready and robustness_ready and raw_rate_rejected
            else "submission_blocked_pending_support",
            "outputs/reports/ratewall_submission_causal_appendix.md",
            f"event_rows={len(event_rows)};support_ready={support_ready};robustness_ready={robustness_ready}",
            "bounded admissible-shock event-study appendix with explicit full-LP/proxy-SVAR blocker",
            "publish_bounded_causal_evidence_appendix_keep_stronger_claim_blocked",
            bool(support_ready and robustness_ready and raw_rate_rejected),
            "This is the maximum Release 2.0 empirical claim.",
        ),
    ]
    return rows


def _submission_decision_row(
    decision_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    action: str,
    bounded_enabled: bool,
    notes: str,
) -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "decision_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_2_0_action": action,
        "bounded_event_study_appendix_enabled": str(bounded_enabled).lower(),
        "full_lp_proxy_svar_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _causal_audit_row(
    component: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    decision: str,
    raw_rate_rejected: bool,
    notes: str,
) -> dict[str, object]:
    return {
        "audit_component": component,
        "audit_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_1_1_decision": decision,
        "raw_rate_change_identification_rejected": str(raw_rate_rejected).lower(),
        "causal_claim_enabled": "false",
        "notes": notes,
    }


def _causal_defensibility_blocker_rows(
    audit_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    blocked = [
        row
        for row in audit_rows
        if row["audit_status"] in {"blocked", "fail"}
    ]
    if not blocked:
        return [
            {
                "blocker_id": "no_release_1_1_full_causal_blocker",
                "blocker_status": "cleared_for_bounded_event_study_only",
                "evidence_artifact": "outputs/tables/ratewall_causal_identification_audit.csv",
                "required_resolution": "No stronger LP/proxy-SVAR authorization is emitted.",
                "release_action": "keep_causal_claim_enabled_false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": "Bounded event-study evidence remains the maximum empirical claim.",
            }
        ]
    return [
        {
            "blocker_id": "release_1_1_full_lp_proxy_svar_defensibility_blocker",
            "blocker_status": "final_blocker_documented",
            "evidence_artifact": "outputs/tables/ratewall_causal_identification_audit.csv",
            "required_resolution": "; ".join(
                str(row["required_value"]) for row in blocked
            ),
            "release_action": "publish_bounded_event_study_and_block_stronger_causal_claim",
            "raw_rate_change_identification_rejected": "true",
            "pricing_output_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "Release 1.1 keeps the admissible event-study estimates and "
                "shock/state diagnostics, but blocks a full causal LP/proxy-SVAR "
                "claim until the listed identification requirements are audited."
            ),
        }
    ]


def _empirical_robustness_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    audit_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.empirical_robustness_manifest.v1",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "result_status_counts": _count_by(result_rows, "result_status"),
        "audit_status_counts": _count_by(audit_rows, "audit_status"),
        "blocker_status_counts": _count_by(blocker_rows, "blocker_status"),
        "raw_rate_change_identification_rejected": True,
        "causal_claim_enabled": False,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "release_1_1_decision": (
            "bounded_event_study_with_final_full_lp_proxy_svar_blocker"
        ),
        "artifact_role": (
            "review_ready_empirical_diagnostics_not_pricing_or_welfare_output"
        ),
    }


def _release_2_0_robustness_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.empirical_robustness_manifest.v2",
        "release": "2.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "support_diagnostic_rows": len(support_rows),
        "robustness_rows": len(robustness_rows),
        "result_status_counts": _count_by(result_rows, "result_status"),
        "support_status_counts": _count_by(support_rows, "support_status"),
        "robustness_status_counts": _count_by(robustness_rows, "robustness_status"),
        "decision_status_counts": _count_by(decision_rows, "decision_status"),
        "bounded_event_study_appendix_enabled": any(
            row.get("decision_id") == "release_2_0_submission_decision"
            and str(row.get("bounded_event_study_appendix_enabled")) == "true"
            for row in decision_rows
        ),
        "full_lp_proxy_svar_claim_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "causal_claim_enabled": False,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "release_2_0_decision": (
            "submission_ready_bounded_event_study_full_lp_proxy_svar_blocked"
        ),
        "artifact_role": (
            "submission_grade_bounded_causal_evidence_and_final_blocker_manifest"
        ),
    }


def _dynamic_lp_feasibility_rows(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
    submission_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    event_rows = [
        row
        for row in result_rows
        if row["artifact_layer"] == "empirical_event_study_estimate"
    ]
    audited_panel_rows = [
        row
        for row in panel_rows
        if row.get("panel_status") == "audited_source_backed_event_outcome"
    ]
    support_ready = support_rows and all(
        row.get("support_status") == "submission_support_pass_bounded_event_study"
        for row in support_rows
    )
    robustness_ready = len(robustness_rows) >= max(1, len(event_rows) * 4)
    bounded_ready = any(
        row.get("decision_id") == "release_2_0_submission_decision"
        and row.get("bounded_event_study_appendix_enabled") == "true"
        for row in submission_rows
    )
    raw_rate_rejected = result_rows and all(
        row.get("raw_rate_change_identification_rejected") == "true"
        for row in result_rows
    )
    return [
        _dynamic_lp_row(
            "admissible_external_shock_panel",
            "pass" if smoke_rows and raw_rate_rejected else "fail",
            "outputs/tables/empirical_smoke_panel.csv",
            f"shock_rows={len(smoke_rows)};raw_rate_rejected={raw_rate_rejected}",
            "nonempty admissible external-shock panel with raw-rate rejection",
            "bounded_event_study_only",
            bounded_ready,
            "SF Fed orthogonalized surprises are available as the shock surface.",
        ),
        _dynamic_lp_row(
            "audited_outcome_state_panel",
            "pass" if audited_panel_rows else "fail",
            "outputs/tables/ratewall_empirical_outcome_panel.csv",
            f"audited_rows={len(audited_panel_rows)};outcome_panel_rows={len(panel_rows)}",
            "source-backed outcome/state panel aligned to event dates",
            "bounded_event_study_only",
            bounded_ready,
            "The panel supports bounded event-study rows and support diagnostics.",
        ),
        _dynamic_lp_row(
            "horizon_state_support",
            "pass" if support_ready else "fail",
            "outputs/tables/ratewall_event_study_support_diagnostics.csv",
            f"support_rows={len(support_rows)};passing_rows={sum(row.get('support_status') == 'submission_support_pass_bounded_event_study' for row in support_rows)}",
            "all outcome/horizon cells pass bounded event-study support diagnostics",
            "bounded_event_study_only",
            bounded_ready,
            "Support diagnostics do not by themselves define a dynamic LP.",
        ),
        _dynamic_lp_row(
            "reduced_form_robustness_checks",
            "pass" if robustness_ready else "fail",
            "outputs/tables/ratewall_event_study_robustness.csv",
            f"robustness_rows={len(robustness_rows)};event_rows={len(event_rows)}",
            "baseline, shock-tail, influence, and balance diagnostics for each event-study cell",
            "bounded_event_study_only",
            bounded_ready,
            "Current robustness checks are reduced-form diagnostics, not dynamic LP uncertainty.",
        ),
        _dynamic_lp_row(
            "pre_specified_lag_control_matrix",
            "blocked",
            "outputs/empirical/local_projection_specs.json",
            "spec_metadata_exists_but_no_estimated_lagged_control_panel",
            "pre-specified dynamic lag/control matrix with source-backed controls by event date and horizon",
            "journal_grade_dynamic_lp_blocked",
            bounded_ready,
            "Release 3.0 rejects widening from event-study slopes to a full LP without a tested lag/control panel.",
        ),
        _dynamic_lp_row(
            "hac_or_clustered_uncertainty",
            "blocked",
            "outputs/tables/ratewall_event_study_robustness.csv",
            "single-shock OLS standard errors only; no HAC or clustered covariance estimator",
            "HAC or clustered uncertainty and serial-correlation diagnostics for dynamic horizons",
            "journal_grade_dynamic_lp_blocked",
            bounded_ready,
            "The current uncertainty rows are adequate for bounded diagnostics, not final dynamic LP inference.",
        ),
        _dynamic_lp_row(
            "pretrend_placebo_dynamic_diagnostics",
            "blocked",
            "outputs/tables/ratewall_event_study_robustness.csv",
            "predetermined outcome balance rows exist but no dynamic placebo/pretrend horizon suite",
            "pretrend, placebo, and serial-correlation diagnostics for the same dynamic specification",
            "journal_grade_dynamic_lp_blocked",
            bounded_ready,
            "Release 3.0 keeps the event-study appendix bounded until placebo/pretrend dynamics are audited.",
        ),
        _dynamic_lp_row(
            "state_dependent_dynamic_interaction",
            "blocked",
            "outputs/tables/ratewall_empirical_results.csv",
            "median-state split diagnostic exists; no estimated dynamic interaction design",
            "audited state-dependent LP interaction with support, controls, and uncertainty",
            "journal_grade_dynamic_lp_blocked",
            bounded_ready,
            "State splits remain descriptive support, not a state-dependent dynamic causal design.",
        ),
    ]


def _proxy_svar_feasibility_rows(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    raw_rate_rejected = result_rows and all(
        row.get("raw_rate_change_identification_rejected") == "true"
        for row in result_rows
    )
    support_pass = sum(
        row.get("support_status") == "submission_support_pass_bounded_event_study"
        for row in support_rows
    )
    outcome_count = len(
        {row.get("outcome_variable", "") for row in panel_rows if row.get("outcome_variable")}
    )
    return [
        _proxy_svar_row(
            "external_proxy_instrument",
            "pass" if smoke_rows and raw_rate_rejected else "fail",
            "outputs/tables/empirical_smoke_panel.csv",
            f"shock_rows={len(smoke_rows)};raw_rate_rejected={raw_rate_rejected}",
            "admissible external monetary-surprise proxy",
            "proxy_available_not_svar",
            "SF Fed surprises are admissible as a proxy surface, but availability is not a full proxy-SVAR.",
        ),
        _proxy_svar_row(
            "reduced_form_system_panel",
            "blocked",
            "outputs/tables/ratewall_empirical_outcome_panel.csv",
            f"outcome_families={outcome_count};panel_rows={len(panel_rows)}",
            "monthly reduced-form system with outcomes, policy variables, state variables, and controls",
            "journal_grade_proxy_svar_blocked",
            "The event-aligned outcome panel is not a reduced-form VAR system.",
        ),
        _proxy_svar_row(
            "instrument_relevance_and_first_stage",
            "blocked",
            "outputs/tables/ratewall_event_study_support_diagnostics.csv",
            f"support_pass_rows={support_pass};support_rows={len(support_rows)}",
            "first-stage or proxy relevance diagnostics inside an estimated system",
            "journal_grade_proxy_svar_blocked",
            "Support diagnostics are event-study sample checks, not proxy-SVAR relevance statistics.",
        ),
        _proxy_svar_row(
            "system_timing_and_exogeneity_audit",
            "blocked",
            "outputs/tables/ratewall_event_study_robustness.csv",
            f"robustness_rows={len(robustness_rows)}",
            "system timing, exogeneity, invertibility, and residual diagnostics",
            "journal_grade_proxy_svar_blocked",
            "No estimated VAR residual system exists in the current release.",
        ),
        _proxy_svar_row(
            "state_dependent_proxy_svar_design",
            "blocked",
            "outputs/tables/ratewall_empirical_results.csv",
            "state associations and bounded event-study rows exist; no state-dependent proxy-SVAR",
            "audited state-dependent proxy-SVAR design with support and controls",
            "journal_grade_proxy_svar_blocked",
            "Release 3.0 keeps state-dependent causal language blocked.",
        ),
    ]


def _dynamic_lp_row(
    gate_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    decision: str,
    bounded_ready: bool,
    notes: str,
) -> dict[str, object]:
    return {
        "gate_id": gate_id,
        "gate_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_3_0_decision": decision,
        "bounded_event_study_appendix_enabled": str(bounded_ready).lower(),
        "dynamic_lp_claim_enabled": "false",
        "full_lp_proxy_svar_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _proxy_svar_row(
    gate_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    decision: str,
    notes: str,
) -> dict[str, object]:
    return {
        "gate_id": gate_id,
        "gate_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_3_0_decision": decision,
        "proxy_svar_claim_enabled": "false",
        "full_lp_proxy_svar_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _dynamic_causal_final_blocker_rows(
    *,
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    blocked_lp = [
        str(row["gate_id"])
        for row in lp_rows
        if row["gate_status"] in {"blocked", "fail"}
    ]
    blocked_proxy = [
        str(row["gate_id"])
        for row in proxy_rows
        if row["gate_status"] in {"blocked", "fail"}
    ]
    required = [
        str(row["required_value"])
        for row in lp_rows + proxy_rows
        if row["gate_status"] in {"blocked", "fail"}
    ]
    bounded_ready = any(
        row.get("bounded_event_study_appendix_enabled") == "true" for row in lp_rows
    )
    return [
        {
            "blocker_id": "release_3_0_dynamic_causal_final_blocker",
            "blocker_status": "journal_grade_final_blocker_documented",
            "evidence_artifact": (
                "outputs/tables/ratewall_dynamic_lp_feasibility_diagnostics.csv;"
                "outputs/tables/ratewall_proxy_svar_feasibility_diagnostics.csv"
            ),
            "blocked_dynamic_lp_gates": ";".join(blocked_lp),
            "blocked_proxy_svar_gates": ";".join(blocked_proxy),
            "required_resolution": "; ".join(required),
            "release_3_0_action": (
                "journal_submission_bounded_event_study_dynamic_lp_proxy_svar_blocked"
            ),
            "bounded_event_study_appendix_enabled": str(bounded_ready).lower(),
            "dynamic_lp_claim_enabled": "false",
            "proxy_svar_claim_enabled": "false",
            "full_lp_proxy_svar_claim_enabled": "false",
            "raw_rate_change_identification_rejected": "true",
            "pricing_output_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "Release 3.0 is journal-submission ready as a bounded event-study "
                "and accounting package, with a final machine-readable blocker "
                "for full dynamic LP/proxy-SVAR claims."
            ),
        }
    ]


def _release_3_0_robustness_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
    submission_rows: list[dict[str, object]],
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.empirical_robustness_manifest.v3",
        "release": "3.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "support_diagnostic_rows": len(support_rows),
        "robustness_rows": len(robustness_rows),
        "submission_decision_rows": len(submission_rows),
        "dynamic_lp_feasibility_rows": len(lp_rows),
        "proxy_svar_feasibility_rows": len(proxy_rows),
        "dynamic_causal_final_blocker_rows": len(blocker_rows),
        "result_status_counts": _count_by(result_rows, "result_status"),
        "support_status_counts": _count_by(support_rows, "support_status"),
        "robustness_status_counts": _count_by(robustness_rows, "robustness_status"),
        "submission_decision_status_counts": _count_by(
            submission_rows, "decision_status"
        ),
        "dynamic_lp_gate_status_counts": _count_by(lp_rows, "gate_status"),
        "proxy_svar_gate_status_counts": _count_by(proxy_rows, "gate_status"),
        "blocker_status_counts": _count_by(blocker_rows, "blocker_status"),
        "bounded_event_study_appendix_enabled": any(
            row.get("bounded_event_study_appendix_enabled") == "true"
            for row in blocker_rows
        ),
        "dynamic_lp_claim_enabled": False,
        "proxy_svar_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "causal_claim_enabled": False,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "release_3_0_decision": (
            "journal_submission_bounded_event_study_dynamic_lp_proxy_svar_blocked"
        ),
        "artifact_role": (
            "journal_grade_bounded_causal_evidence_with_final_dynamic_causal_blocker"
        ),
    }


def _journal_submission_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.journal_submission_manifest.v1",
        "release": "3.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "event_study_support_rows": len(support_rows),
        "event_study_robustness_rows": len(robustness_rows),
        "dynamic_lp_feasibility_rows": len(lp_rows),
        "proxy_svar_feasibility_rows": len(proxy_rows),
        "dynamic_causal_final_blocker_rows": len(blocker_rows),
        "dynamic_lp_blocked_gates": [
            row["gate_id"] for row in lp_rows if row["gate_status"] == "blocked"
        ],
        "proxy_svar_blocked_gates": [
            row["gate_id"] for row in proxy_rows if row["gate_status"] == "blocked"
        ],
        "bounded_event_study_appendix_enabled": any(
            row.get("bounded_event_study_appendix_enabled") == "true"
            for row in blocker_rows
        ),
        "dynamic_lp_claim_enabled": False,
        "proxy_svar_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "release_3_0_decision": (
            "journal_submission_bounded_event_study_dynamic_lp_proxy_svar_blocked"
        ),
        "paper_claim_boundary": (
            "bounded_event_study_and_accounting_package_not_dynamic_causal_transmission"
        ),
    }


def _event_study_hac_diagnostic_rows(
    panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for outcome, horizon in _audited_outcome_horizon_groups(panel_rows):
        observations = sorted(
            _event_observations(panel_rows, outcome, horizon),
            key=lambda observation: observation[0],
        )
        if len(observations) < 8:
            continue
        xs = [shock for _event_date, shock, _y, _state, _pre in observations]
        ys = [y for _event_date, _shock, y, _state, _pre in observations]
        ols_beta, ols_se, _ols_t = _ols_slope(xs, ys)
        hac_lag = min(3, max(1, len(observations) // 8))
        hac_se, hac_t = _newey_west_slope_se(xs, ys, hac_lag)
        rows.append(
            {
                "diagnostic_id": f"hac_{outcome}_{horizon}m",
                "outcome_variable": outcome,
                "horizon_months": horizon,
                "sample_start": observations[0][0],
                "sample_end": observations[-1][0],
                "n_obs": len(observations),
                "estimator": "event_study_ols_newey_west_candidate_per_100bp",
                "ols_estimate": f"{ols_beta:.6f}",
                "ols_standard_error": f"{ols_se:.6f}",
                "hac_lag": hac_lag,
                "hac_standard_error": f"{hac_se:.6f}",
                "hac_t_stat": f"{hac_t:.6f}",
                "response_unit": _response_unit(outcome),
                "diagnostic_status": (
                    "hac_uncertainty_diagnostic_not_dynamic_lp"
                ),
                "dynamic_lp_claim_enabled": "false",
                "proxy_svar_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "Validation-only HAC-style uncertainty diagnostic for the "
                    "bounded event-study slope. It is not a full dynamic LP "
                    "or proxy-SVAR covariance design."
                ),
            }
        )
    if not rows:
        rows.append(
            {
                "diagnostic_id": "hac_no_audited_event_study_cells",
                "outcome_variable": "",
                "horizon_months": "",
                "sample_start": "",
                "sample_end": "",
                "n_obs": 0,
                "estimator": "event_study_hac_not_estimated",
                "ols_estimate": "",
                "ols_standard_error": "",
                "hac_lag": "",
                "hac_standard_error": "",
                "hac_t_stat": "",
                "response_unit": "",
                "diagnostic_status": (
                    "hac_uncertainty_blocked_no_audited_event_cells"
                ),
                "dynamic_lp_claim_enabled": "false",
                "proxy_svar_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "No audited event-study cells were available for HAC-style "
                    "diagnostics in this snapshot."
                ),
            }
        )
    return rows


def _pretrend_placebo_diagnostic_rows(
    panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for outcome, horizon in _audited_outcome_horizon_groups(panel_rows):
        observations = sorted(
            _event_observations(panel_rows, outcome, horizon),
            key=lambda observation: observation[0],
        )
        if len(observations) < 8:
            continue
        xs = [shock for _event_date, shock, _y, _state, _pre in observations]
        pre_values = [pre for _event_date, _shock, _y, _state, pre in observations]
        beta, se, t_stat = _ols_slope(xs, pre_values)
        rows.append(
            {
                "diagnostic_id": f"predetermined_level_placebo_{outcome}_{horizon}m",
                "outcome_variable": outcome,
                "horizon_months": horizon,
                "sample_start": observations[0][0],
                "sample_end": observations[-1][0],
                "n_obs": len(observations),
                "placebo_variable": "pre_event_outcome_level",
                "estimator": "pre_event_outcome_level_on_external_shock",
                "placebo_estimate": f"{beta:.6f}",
                "placebo_standard_error": f"{se:.6f}",
                "placebo_t_stat": f"{t_stat:.6f}",
                "diagnostic_status": (
                    "predetermined_level_placebo_not_dynamic_pretrend_suite"
                ),
                "dynamic_lp_claim_enabled": "false",
                "proxy_svar_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "This is a predetermined-level placebo check. It does not "
                    "replace a pre-event dynamic trend, serial-correlation, or "
                    "placebo-horizon suite."
                ),
            }
        )
    if not rows:
        rows.append(
            {
                "diagnostic_id": "placebo_no_audited_event_study_cells",
                "outcome_variable": "",
                "horizon_months": "",
                "sample_start": "",
                "sample_end": "",
                "n_obs": 0,
                "placebo_variable": "pre_event_outcome_level",
                "estimator": "pre_event_placebo_not_estimated",
                "placebo_estimate": "",
                "placebo_standard_error": "",
                "placebo_t_stat": "",
                "diagnostic_status": (
                    "placebo_pretrend_blocked_no_audited_event_cells"
                ),
                "dynamic_lp_claim_enabled": "false",
                "proxy_svar_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "No audited event-study cells were available for placebo "
                    "diagnostics in this snapshot."
                ),
            }
        )
    return rows


def _dynamic_identification_promotion_contract_rows(
    *,
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
    hac_rows: list[dict[str, object]],
    placebo_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    event_rows = [
        row
        for row in result_rows
        if row.get("artifact_layer") == "empirical_event_study_estimate"
    ]
    blocked_lp = [
        row for row in lp_rows if row.get("gate_status") in {"blocked", "fail"}
    ]
    blocked_proxy = [
        row for row in proxy_rows if row.get("gate_status") in {"blocked", "fail"}
    ]
    return [
        _promotion_contract_row(
            "audited_dynamic_lag_control_panel",
            "blocked",
            "outputs/empirical/local_projection_specs.json",
            "spec_metadata_exists_but_no_estimated_source_backed_lag_control_panel",
            "estimated event-date lag/control panel with pre-specified controls",
            "implement_and_test_dynamic_lag_control_panel",
            "Release 4.0 keeps dynamic LP claims disabled until this panel exists.",
        ),
        _promotion_contract_row(
            "hac_or_clustered_uncertainty",
            "partial_diagnostic_not_promotion_ready",
            "outputs/tables/ratewall_event_study_hac_diagnostics.csv",
            f"validation_only_hac_rows={len(hac_rows)};event_rows={len(event_rows)}",
            "audited HAC or clustered uncertainty for the final dynamic design",
            "audit_covariance_choice_and_serial_correlation_diagnostics",
            "HAC-style event-study diagnostics reduce review ambiguity but do not enable a dynamic LP.",
        ),
        _promotion_contract_row(
            "dynamic_pretrend_placebo_suite",
            "partial_diagnostic_not_promotion_ready",
            "outputs/tables/ratewall_pretrend_placebo_diagnostics.csv",
            f"predetermined_level_placebo_rows={len(placebo_rows)}",
            "pre-event dynamic trend and placebo-horizon tests for the same design",
            "add_dynamic_pretrend_and_placebo_horizon_suite",
            "Predetermined-level checks are useful but not a full pretrend suite.",
        ),
        _promotion_contract_row(
            "state_dependent_dynamic_interaction",
            "blocked",
            "outputs/tables/ratewall_dynamic_lp_feasibility_diagnostics.csv",
            f"blocked_dynamic_lp_rows={len(blocked_lp)}",
            "audited state interaction with support, controls, and uncertainty",
            "estimate_and_validate_state_dependent_dynamic_specification",
            "Median-state diagnostics remain descriptive until the full design is tested.",
        ),
        _promotion_contract_row(
            "proxy_svar_system",
            "blocked",
            "outputs/tables/ratewall_proxy_svar_feasibility_diagnostics.csv",
            f"blocked_proxy_svar_rows={len(blocked_proxy)}",
            "estimated reduced-form system with proxy relevance and timing diagnostics",
            "assemble_and_validate_proxy_svar_system",
            "An admissible external shock is not by itself a proxy-SVAR.",
        ),
        _promotion_contract_row(
            "explicit_claim_promotion_switch",
            "blocked",
            "outputs/tables/ratewall_release_4_0_dynamic_causal_final_blocker.csv",
            "dynamic_lp_claim_enabled=false;proxy_svar_claim_enabled=false",
            "future switch deliberately enabled only after all tests pass",
            "add_fail_closed_tests_for_any_claim_promotion",
            "Release 4.0 is fail-closed: stronger causal language is disabled.",
        ),
    ]


def _promotion_contract_row(
    requirement_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    prerequisite: str,
    notes: str,
) -> dict[str, object]:
    return {
        "requirement_id": requirement_id,
        "requirement_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "future_opt_in_prerequisite": prerequisite,
        "dynamic_lp_claim_enabled": "false",
        "proxy_svar_claim_enabled": "false",
        "full_lp_proxy_svar_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_4_0_dynamic_blocker_rows(
    *,
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
    hac_rows: list[dict[str, object]],
    placebo_rows: list[dict[str, object]],
    contract_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    blocked_lp = [
        str(row["gate_id"])
        for row in lp_rows
        if row["gate_status"] in {"blocked", "fail"}
    ]
    blocked_proxy = [
        str(row["gate_id"])
        for row in proxy_rows
        if row["gate_status"] in {"blocked", "fail"}
    ]
    blocked_contract = [
        str(row["required_value"])
        for row in contract_rows
        if row["requirement_status"] != "pass"
    ]
    bounded_ready = any(
        row.get("bounded_event_study_appendix_enabled") == "true" for row in lp_rows
    )
    return [
        {
            "blocker_id": "release_4_0_dynamic_causal_final_blocker",
            "blocker_status": "journal_grade_final_blocker_strengthened",
            "evidence_artifact": (
                "outputs/tables/ratewall_event_study_hac_diagnostics.csv;"
                "outputs/tables/ratewall_pretrend_placebo_diagnostics.csv;"
                "outputs/tables/ratewall_dynamic_identification_promotion_contract_disabled.csv"
            ),
            "blocked_dynamic_lp_requirements": ";".join(blocked_lp),
            "blocked_proxy_svar_requirements": ";".join(blocked_proxy),
            "diagnostic_support": (
                f"hac_rows={len(hac_rows)};placebo_rows={len(placebo_rows)};"
                f"promotion_contract_rows={len(contract_rows)}"
            ),
            "required_resolution": "; ".join(blocked_contract),
            "release_4_0_action": (
                "journal_submission_bounded_event_study_dynamic_design_blocked"
            ),
            "bounded_event_study_appendix_enabled": str(bounded_ready).lower(),
            "dynamic_lp_claim_enabled": "false",
            "proxy_svar_claim_enabled": "false",
            "full_lp_proxy_svar_claim_enabled": "false",
            "raw_rate_change_identification_rejected": "true",
            "pricing_output_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "Release 4.0 adds final review diagnostics and a disabled "
                "promotion contract. The bounded event-study appendix remains "
                "the maximum empirical claim."
            ),
        }
    ]


def _release_4_0_submission_checklist_rows(
    *,
    result_rows: list[dict[str, object]],
    hac_rows: list[dict[str, object]],
    placebo_rows: list[dict[str, object]],
    contract_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    event_rows = [
        row
        for row in result_rows
        if row.get("artifact_layer") == "empirical_event_study_estimate"
    ]
    contract_fail_closed = contract_rows and all(
        row.get("dynamic_lp_claim_enabled") == "false"
        and row.get("proxy_svar_claim_enabled") == "false"
        for row in contract_rows
    )
    return [
        _release_4_check_row(
            "bounded_event_study_evidence",
            "pass" if event_rows else "fail",
            "outputs/tables/ratewall_empirical_results.csv",
            f"bounded_event_study_rows={len(event_rows)}",
            "nonempty bounded event-study rows using admissible shocks",
            "retain_bounded_event_study_appendix",
            "Event-study rows remain bounded estimates with limitations.",
        ),
        _release_4_check_row(
            "hac_uncertainty_diagnostics",
            "pass_validation_only" if hac_rows else "fail",
            "outputs/tables/ratewall_event_study_hac_diagnostics.csv",
            f"hac_rows={len(hac_rows)}",
            "HAC-style diagnostic rows for event-study estimates",
            "use_as_review_diagnostic_not_claim_promotion",
            "These rows strengthen review transparency but not causal scope.",
        ),
        _release_4_check_row(
            "placebo_pretrend_readiness",
            "partial_validation_only" if placebo_rows else "fail",
            "outputs/tables/ratewall_pretrend_placebo_diagnostics.csv",
            f"placebo_rows={len(placebo_rows)}",
            "predetermined-level checks plus future dynamic pretrend suite",
            "keep_dynamic_pretrend_requirement_blocked",
            "Predetermined checks do not replace a dynamic pretrend suite.",
        ),
        _release_4_check_row(
            "dynamic_claim_promotion_contract",
            "blocked_fail_closed" if contract_fail_closed else "fail",
            "outputs/tables/ratewall_dynamic_identification_promotion_contract_disabled.csv",
            f"contract_rows={len(contract_rows)};fail_closed={contract_fail_closed}",
            "all promotion switches false until future tests deliberately pass",
            "preserve_disabled_stronger_causal_claims",
            "The contract documents exact future opt-in prerequisites.",
        ),
        _release_4_check_row(
            "final_journal_grade_blocker",
            "pass" if blocker_rows else "fail",
            "outputs/tables/ratewall_release_4_0_dynamic_causal_final_blocker.csv",
            f"blocker_rows={len(blocker_rows)}",
            "machine-readable final dynamic-causal blocker",
            "publish_blocker_if_dynamic_design_not_defensible",
            "Release 4.0 strengthens the blocker instead of overclaiming.",
        ),
    ]


def _release_4_check_row(
    check_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    action: str,
    notes: str,
) -> dict[str, object]:
    return {
        "check_id": check_id,
        "check_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_4_0_action": action,
        "dynamic_lp_claim_enabled": "false",
        "proxy_svar_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _external_review_issue_matrix_rows(
    *,
    hac_rows: list[dict[str, object]],
    placebo_rows: list[dict[str, object]],
    contract_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        _review_issue_row(
            "raw_rate_shock_substitution",
            "Could raw policy-rate changes be used instead of external shocks?",
            "resolved_guardrail",
            "outputs/tables/ratewall_empirical_results.csv",
            "Raw policy-rate changes are rejected in every empirical artifact.",
            "admissible_shock_only",
        ),
        _review_issue_row(
            "hac_or_clustered_uncertainty",
            "Does the package report serial-correlation-robust uncertainty?",
            "partially_addressed_not_claim_promotion",
            "outputs/tables/ratewall_event_study_hac_diagnostics.csv",
            f"{len(hac_rows)} HAC-style rows are provided as diagnostics only.",
            "bounded_event_study_not_dynamic_lp",
        ),
        _review_issue_row(
            "pretrend_placebo_suite",
            "Are placebo and pretrend diagnostics sufficient for a full LP?",
            "blocked_pending_dynamic_suite",
            "outputs/tables/ratewall_pretrend_placebo_diagnostics.csv",
            f"{len(placebo_rows)} predetermined-level checks exist; dynamic "
            "pretrend and placebo-horizon tests remain future requirements.",
            "dynamic_lp_blocked",
        ),
        _review_issue_row(
            "proxy_svar_relevance",
            "Can the SF Fed surprise be promoted to a proxy-SVAR result?",
            "blocked",
            "outputs/tables/ratewall_proxy_svar_feasibility_diagnostics.csv",
            "The shock is admissible, but no reduced-form system or first stage exists.",
            "proxy_svar_blocked",
        ),
        _review_issue_row(
            "claim_promotion",
            "What would be required to widen causal language?",
            "blocked_fail_closed",
            "outputs/tables/ratewall_dynamic_identification_promotion_contract_disabled.csv",
            f"{len(contract_rows)} disabled contract rows define future gates.",
            "future_opt_in_required",
        ),
        _review_issue_row(
            "final_submission_status",
            "Is Release 4.0 a dynamic causal paper?",
            "final_bounded_submission",
            "outputs/tables/ratewall_release_4_0_dynamic_causal_final_blocker.csv",
            f"{len(blocker_rows)} blocker rows keep stronger claims disabled.",
            "bounded_event_study_maximum_claim",
        ),
    ]


def _review_issue_row(
    issue_id: str,
    concern: str,
    status: str,
    artifact: str,
    response: str,
    boundary: str,
) -> dict[str, object]:
    return {
        "issue_id": issue_id,
        "reviewer_concern": concern,
        "response_status": status,
        "evidence_artifact": artifact,
        "release_response": response,
        "claim_boundary": boundary,
        "dynamic_lp_claim_enabled": "false",
        "proxy_svar_claim_enabled": "false",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
    }


def _release_4_0_robustness_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
    submission_rows: list[dict[str, object]],
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
    release_3_blocker_rows: list[dict[str, object]],
    hac_rows: list[dict[str, object]],
    placebo_rows: list[dict[str, object]],
    contract_rows: list[dict[str, object]],
    release_4_blocker_rows: list[dict[str, object]],
    checklist_rows: list[dict[str, object]],
    issue_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.empirical_robustness_manifest.v4",
        "release": "4.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "support_diagnostic_rows": len(support_rows),
        "robustness_rows": len(robustness_rows),
        "submission_decision_rows": len(submission_rows),
        "dynamic_lp_feasibility_rows": len(lp_rows),
        "proxy_svar_feasibility_rows": len(proxy_rows),
        "release_3_dynamic_causal_final_blocker_rows": len(release_3_blocker_rows),
        "event_study_hac_diagnostic_rows": len(hac_rows),
        "pretrend_placebo_diagnostic_rows": len(placebo_rows),
        "dynamic_identification_promotion_contract_rows": len(contract_rows),
        "release_4_dynamic_causal_final_blocker_rows": len(release_4_blocker_rows),
        "release_4_submission_checklist_rows": len(checklist_rows),
        "external_review_issue_rows": len(issue_rows),
        "result_status_counts": _count_by(result_rows, "result_status"),
        "hac_status_counts": _count_by(hac_rows, "diagnostic_status"),
        "placebo_status_counts": _count_by(placebo_rows, "diagnostic_status"),
        "promotion_contract_status_counts": _count_by(
            contract_rows, "requirement_status"
        ),
        "release_4_blocker_status_counts": _count_by(
            release_4_blocker_rows, "blocker_status"
        ),
        "dynamic_lp_claim_enabled": False,
        "proxy_svar_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "causal_claim_enabled": False,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "release_4_0_decision": (
            "final_bounded_journal_submission_dynamic_design_blocked"
        ),
        "artifact_role": (
            "submission_grade_bounded_causal_evidence_with_strengthened_final_blocker"
        ),
    }


def _release_4_0_submission_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
    hac_rows: list[dict[str, object]],
    placebo_rows: list[dict[str, object]],
    contract_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
    issue_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": "ratewall.release_4_0_submission_manifest.v1",
        "release": "4.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "support_diagnostic_rows": len(support_rows),
        "robustness_rows": len(robustness_rows),
        "dynamic_lp_feasibility_rows": len(lp_rows),
        "proxy_svar_feasibility_rows": len(proxy_rows),
        "event_study_hac_diagnostic_rows": len(hac_rows),
        "pretrend_placebo_diagnostic_rows": len(placebo_rows),
        "dynamic_identification_promotion_contract_rows": len(contract_rows),
        "release_4_dynamic_causal_final_blocker_rows": len(blocker_rows),
        "external_review_issue_rows": len(issue_rows),
        "blocked_promotion_requirements": [
            row["requirement_id"]
            for row in contract_rows
            if row["requirement_status"] != "pass"
        ],
        "bounded_event_study_appendix_enabled": True,
        "dynamic_lp_claim_enabled": False,
        "proxy_svar_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "release_4_0_decision": (
            "final_bounded_journal_submission_dynamic_design_blocked"
        ),
        "paper_claim_boundary": (
            "bounded_event_study_and_accounting_package_not_full_dynamic_causal_design"
        ),
    }


def _controlled_dynamic_lp_panel_rows(
    panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for outcome, horizon in _audited_outcome_horizon_groups(panel_rows):
        candidates = []
        for row in panel_rows:
            if row.get("panel_status") != "audited_source_backed_event_outcome":
                continue
            if row["outcome_variable"] != outcome or int(row["horizon_months"]) != horizon:
                continue
            values = {
                "shock_100bp": _float(row.get("orthogonalized_surprise_bps")),
                "outcome_change": _float(row.get("outcome_change")),
                "lagged_outcome_change": _float(row.get("lagged_outcome_change")),
                "public_liability_base_1y_gdp": _float(
                    row.get("public_liability_base_1y_gdp")
                ),
                "repricing_share_1y": _float(row.get("repricing_share_1y")),
                "debt_held_public_gdp": _float(row.get("debt_held_public_gdp")),
                "rate_sensitive_fed_liabilities_gdp": _float(
                    row.get("rate_sensitive_fed_liabilities_gdp")
                ),
            }
            if any(value is None for value in values.values()):
                continue
            candidates.append((row, values))
        if not candidates:
            continue
        state_mean = _mean(
            [float(values["public_liability_base_1y_gdp"]) for _row, values in candidates]
        )
        for row, values in candidates:
            shock = float(values["shock_100bp"]) / 100.0
            state = float(values["public_liability_base_1y_gdp"])
            state_centered = state - state_mean
            rows.append(
                {
                    "event_date": row["event_date"],
                    "outcome_variable": outcome,
                    "horizon_months": horizon,
                    "shock_dataset": row["shock_dataset"],
                    "shock_column": row["shock_column"],
                    "shock_100bp": f"{shock:.8f}",
                    "outcome_change": f"{float(values['outcome_change']):.6f}",
                    "lagged_outcome_change": (
                        f"{float(values['lagged_outcome_change']):.6f}"
                    ),
                    "public_liability_base_1y_gdp": f"{state:.6f}",
                    "repricing_share_1y": (
                        f"{float(values['repricing_share_1y']):.6f}"
                    ),
                    "debt_held_public_gdp": (
                        f"{float(values['debt_held_public_gdp']):.6f}"
                    ),
                    "rate_sensitive_fed_liabilities_gdp": (
                        f"{float(values['rate_sensitive_fed_liabilities_gdp']):.6f}"
                    ),
                    "state_centered": f"{state_centered:.6f}",
                    "shock_state_interaction": f"{(shock * state_centered):.8f}",
                    "source_backed_control_count": 5,
                    "panel_status": "source_backed_controlled_dynamic_lp_row",
                    "dynamic_lp_appendix_enabled": "true",
                    "proxy_svar_claim_enabled": "false",
                    "raw_rate_change_identification_rejected": "true",
                    "pricing_output_enabled": "false",
                    "incidence_claim_enabled": "false",
                    "notes": (
                        "Event-aligned source-backed controls for a bounded "
                        "admissible-shock dynamic local-projection appendix."
                    ),
                }
            )
    return rows


def _controlled_dynamic_lp_result_rows(
    controlled_panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for outcome, horizon in _controlled_panel_groups(controlled_panel_rows):
        observations = [
            row
            for row in controlled_panel_rows
            if row["outcome_variable"] == outcome and int(row["horizon_months"]) == horizon
        ]
        if len(observations) < 30:
            continue
        y_values = [_float(row["outcome_change"]) for row in observations]
        x_values = [
            [
                1.0,
                _float(row["shock_100bp"]),
                _float(row["shock_state_interaction"]),
                _float(row["lagged_outcome_change"]),
                _float(row["state_centered"]),
                _float(row["repricing_share_1y"]),
            ]
            for row in observations
        ]
        if any(value is None for value in y_values):
            continue
        if any(any(value is None for value in row) for row in x_values):
            continue
        y = [float(value) for value in y_values if value is not None]
        x = [[float(value) for value in row if value is not None] for row in x_values]
        hac_lag = min(4, max(1, len(observations) // 10))
        estimate = _ols_hac_multivariate(
            x,
            y,
            coefficient_names=[
                "intercept",
                "shock_100bp",
                "shock_state_interaction",
                "lagged_outcome_change",
                "state_centered",
                "repricing_share_1y",
            ],
            hac_lag=hac_lag,
        )
        if estimate is None:
            continue
        rows.append(
            {
                "result_id": f"controlled_dynamic_lp_{outcome}_{horizon}m",
                "outcome_variable": outcome,
                "horizon_months": horizon,
                "n_obs": len(observations),
                "sample_start": min(str(row["event_date"]) for row in observations),
                "sample_end": max(str(row["event_date"]) for row in observations),
                "estimator": "controlled_event_local_projection_hac_per_100bp",
                "shock_estimate": f"{estimate['coef']['shock_100bp']:.6f}",
                "shock_hac_standard_error": f"{estimate['se']['shock_100bp']:.6f}",
                "shock_hac_t_stat": f"{estimate['t']['shock_100bp']:.6f}",
                "state_interaction_estimate": (
                    f"{estimate['coef']['shock_state_interaction']:.6f}"
                ),
                "state_interaction_hac_standard_error": (
                    f"{estimate['se']['shock_state_interaction']:.6f}"
                ),
                "state_interaction_hac_t_stat": (
                    f"{estimate['t']['shock_state_interaction']:.6f}"
                ),
                "control_variables": (
                    "lagged_outcome_change;state_centered;repricing_share_1y"
                ),
                "hac_lag": hac_lag,
                "response_unit": _response_unit(outcome),
                "result_status": (
                    "admissible_shock_controlled_dynamic_lp_with_limitations"
                ),
                "dynamic_lp_appendix_enabled": "true",
                "proxy_svar_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "Controlled event-level local projection using SF Fed "
                    "orthogonalized surprises and source-backed lag/state "
                    "controls. This does not enable proxy-SVAR, pricing, "
                    "welfare, or incidence claims."
                ),
            }
        )
    if not rows:
        rows.append(
            {
                "result_id": "controlled_dynamic_lp_not_estimated",
                "outcome_variable": "",
                "horizon_months": "",
                "n_obs": len(controlled_panel_rows),
                "sample_start": "",
                "sample_end": "",
                "estimator": "controlled_event_local_projection_not_estimated",
                "shock_estimate": "",
                "shock_hac_standard_error": "",
                "shock_hac_t_stat": "",
                "state_interaction_estimate": "",
                "state_interaction_hac_standard_error": "",
                "state_interaction_hac_t_stat": "",
                "control_variables": "",
                "hac_lag": "",
                "response_unit": "",
                "result_status": "controlled_dynamic_lp_blocked_by_support_or_rank",
                "dynamic_lp_appendix_enabled": "false",
                "proxy_svar_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "No controlled dynamic-LP estimate is emitted when the "
                    "event/control panel is empty, too thin, or rank deficient."
                ),
            }
        )
    return rows


def _dynamic_lp_support_rows(
    controlled_panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for outcome, horizon in _controlled_panel_groups(controlled_panel_rows):
        observations = [
            row
            for row in controlled_panel_rows
            if row["outcome_variable"] == outcome and int(row["horizon_months"]) == horizon
        ]
        shocks = [abs(float(row["shock_100bp"])) for row in observations]
        years = {str(row["event_date"])[:4] for row in observations}
        support_pass = len(observations) >= 30 and len(years) >= 5 and max(shocks) > 0
        rows.append(
            {
                "diagnostic_id": f"controlled_dynamic_lp_support_{outcome}_{horizon}m",
                "outcome_variable": outcome,
                "horizon_months": horizon,
                "n_obs": len(observations),
                "sample_start": min(str(row["event_date"]) for row in observations),
                "sample_end": max(str(row["event_date"]) for row in observations),
                "unique_event_years": len(years),
                "control_variables": (
                    "lagged_outcome_change;state_centered;repricing_share_1y"
                ),
                "min_abs_shock_100bp": f"{min(shocks):.8f}",
                "max_abs_shock_100bp": f"{max(shocks):.8f}",
                "support_status": (
                    "controlled_dynamic_lp_support_pass"
                    if support_pass
                    else "controlled_dynamic_lp_support_blocked"
                ),
                "dynamic_lp_appendix_enabled": str(support_pass).lower(),
                "proxy_svar_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "Support diagnostic for the controlled admissible-shock "
                    "local-projection appendix."
                ),
            }
        )
    if not rows:
        rows.append(
            {
                "diagnostic_id": "controlled_dynamic_lp_support_no_rows",
                "outcome_variable": "",
                "horizon_months": "",
                "n_obs": 0,
                "sample_start": "",
                "sample_end": "",
                "unique_event_years": 0,
                "control_variables": "",
                "min_abs_shock_100bp": "",
                "max_abs_shock_100bp": "",
                "support_status": "controlled_dynamic_lp_support_blocked",
                "dynamic_lp_appendix_enabled": "false",
                "proxy_svar_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": "No controlled dynamic-LP panel rows were available.",
            }
        )
    return rows


def _release_5_0_identification_decision_rows(
    *,
    controlled_panel_rows: list[dict[str, object]],
    controlled_result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    controlled_estimates = [
        row
        for row in controlled_result_rows
        if row["result_status"]
        == "admissible_shock_controlled_dynamic_lp_with_limitations"
    ]
    support_ready = support_rows and all(
        row.get("support_status") == "controlled_dynamic_lp_support_pass"
        for row in support_rows
    )
    raw_rate_rejected = result_rows and all(
        row.get("raw_rate_change_identification_rejected") == "true"
        for row in result_rows
    )
    dynamic_enabled = bool(controlled_estimates and support_ready and raw_rate_rejected)
    return [
        _release_5_decision_row(
            "controlled_dynamic_lp_panel",
            "pass" if controlled_panel_rows else "blocked",
            "outputs/tables/ratewall_controlled_dynamic_lp_panel.csv",
            f"panel_rows={len(controlled_panel_rows)}",
            "source-backed event/control rows for each outcome-horizon cell",
            "use_control_panel_for_bounded_dynamic_lp",
            dynamic_enabled,
            False,
            "The panel is event-aligned and source-backed.",
        ),
        _release_5_decision_row(
            "controlled_dynamic_lp_estimates",
            "pass" if dynamic_enabled else "blocked",
            "outputs/tables/ratewall_controlled_dynamic_lp_results.csv",
            f"controlled_estimate_rows={len(controlled_estimates)}",
            "controlled dynamic-LP estimates with HAC uncertainty",
            "publish_bounded_dynamic_lp_appendix",
            dynamic_enabled,
            False,
            "The appendix is bounded to admissible-shock local projections.",
        ),
        _release_5_decision_row(
            "state_dependent_interaction",
            "diagnostic_enabled" if dynamic_enabled else "blocked",
            "outputs/tables/ratewall_controlled_dynamic_lp_results.csv",
            "shock_state_interaction_estimate_reported",
            "state interaction with support diagnostics and guarded language",
            "report_state_interaction_as_bounded_dynamic_lp_diagnostic",
            dynamic_enabled,
            dynamic_enabled,
            "State interactions are estimates with limitations, not welfare or threshold claims.",
        ),
        _release_5_decision_row(
            "proxy_svar_system",
            "blocked",
            "outputs/tables/ratewall_release_5_0_proxy_svar_final_blocker.csv",
            "no_reduced_form_system_or_proxy_first_stage_estimated",
            "estimated VAR system, proxy relevance, timing, and residual diagnostics",
            "keep_proxy_svar_claim_disabled",
            dynamic_enabled,
            False,
            "Release 5.0 implements controlled LPs, not a proxy-SVAR system.",
        ),
        _release_5_decision_row(
            "release_5_0_identification_decision",
            "controlled_dynamic_lp_enabled_proxy_svar_blocked"
            if dynamic_enabled
            else "dynamic_lp_blocked_by_support_or_rank",
            "outputs/reports/ratewall_release_5_0_dynamic_lp_appendix.md",
            f"dynamic_enabled={dynamic_enabled};support_ready={support_ready}",
            "bounded controlled dynamic-LP appendix with proxy-SVAR blocker",
            "publish_release_5_0_dynamic_lp_appendix_with_limits",
            dynamic_enabled,
            dynamic_enabled,
            "This is the maximum Release 5.0 empirical claim.",
        ),
    ]


def _release_5_decision_row(
    decision_id: str,
    status: str,
    artifact: str,
    observed: str,
    required: str,
    action: str,
    dynamic_enabled: bool,
    state_enabled: bool,
    notes: str,
) -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "decision_status": status,
        "evidence_artifact": artifact,
        "observed_value": observed,
        "required_value": required,
        "release_5_0_action": action,
        "controlled_dynamic_lp_appendix_enabled": str(dynamic_enabled).lower(),
        "proxy_svar_claim_enabled": "false",
        "state_dependent_claim_enabled": str(state_enabled).lower(),
        "full_lp_proxy_svar_claim_enabled": "false",
        "raw_rate_change_identification_rejected": "true",
        "pricing_output_enabled": "false",
        "incidence_claim_enabled": "false",
        "notes": notes,
    }


def _release_5_0_proxy_svar_blocker_rows(
    decision_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    blocked = [
        str(row["required_value"])
        for row in decision_rows
        if row["decision_id"] == "proxy_svar_system"
    ]
    dynamic_enabled = any(
        row.get("decision_id") == "release_5_0_identification_decision"
        and row.get("controlled_dynamic_lp_appendix_enabled") == "true"
        for row in decision_rows
    )
    return [
        {
            "blocker_id": "release_5_0_proxy_svar_final_blocker",
            "blocker_status": "proxy_svar_blocked_controlled_dynamic_lp_enabled"
            if dynamic_enabled
            else "proxy_svar_and_dynamic_lp_blocked",
            "evidence_artifact": (
                "outputs/tables/ratewall_release_5_0_identification_decision.csv"
            ),
            "blocked_requirements": "proxy_svar_system",
            "required_resolution": "; ".join(blocked),
            "release_5_0_action": (
                "publish_controlled_dynamic_lp_appendix_keep_proxy_svar_blocked"
                if dynamic_enabled
                else "preserve_final_blocker_until_dynamic_lp_support_passes"
            ),
            "controlled_dynamic_lp_appendix_enabled": str(dynamic_enabled).lower(),
            "proxy_svar_claim_enabled": "false",
            "state_dependent_claim_enabled": str(dynamic_enabled).lower(),
            "full_lp_proxy_svar_claim_enabled": "false",
            "raw_rate_change_identification_rejected": "true",
            "pricing_output_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "Release 5.0 can report bounded controlled local projections "
                "when support passes, but it still does not estimate a proxy-SVAR."
            ),
        }
    ]


def _release_5_0_robustness_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
    controlled_panel_rows: list[dict[str, object]],
    controlled_result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    proxy_blocker_rows: list[dict[str, object]],
) -> dict[str, object]:
    dynamic_enabled = any(
        row.get("controlled_dynamic_lp_appendix_enabled") == "true"
        for row in decision_rows
    )
    return {
        "schema": "ratewall.empirical_robustness_manifest.v5",
        "release": "5.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "empirical_result_rows": len(result_rows),
        "controlled_dynamic_lp_panel_rows": len(controlled_panel_rows),
        "controlled_dynamic_lp_result_rows": len(controlled_result_rows),
        "controlled_dynamic_lp_support_rows": len(support_rows),
        "release_5_0_decision_rows": len(decision_rows),
        "proxy_svar_final_blocker_rows": len(proxy_blocker_rows),
        "controlled_dynamic_lp_status_counts": _count_by(
            controlled_result_rows, "result_status"
        ),
        "controlled_dynamic_lp_support_status_counts": _count_by(
            support_rows, "support_status"
        ),
        "release_5_0_decision_status_counts": _count_by(
            decision_rows, "decision_status"
        ),
        "controlled_dynamic_lp_appendix_enabled": dynamic_enabled,
        "proxy_svar_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "causal_claim_enabled": False,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "release_5_0_decision": (
            "controlled_dynamic_lp_enabled_proxy_svar_blocked"
            if dynamic_enabled
            else "dynamic_lp_blocked_by_support_or_rank"
        ),
        "artifact_role": (
            "bounded_admissible_shock_dynamic_lp_appendix_with_proxy_svar_blocker"
        ),
    }


def _release_5_0_dynamic_causal_manifest(
    *,
    smoke_rows: list[dict[str, object]],
    panel_rows: list[dict[str, object]],
    controlled_panel_rows: list[dict[str, object]],
    controlled_result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    proxy_blocker_rows: list[dict[str, object]],
) -> dict[str, object]:
    dynamic_enabled = any(
        row.get("controlled_dynamic_lp_appendix_enabled") == "true"
        for row in decision_rows
    )
    return {
        "schema": "ratewall.release_5_0_dynamic_causal_manifest.v1",
        "release": "5.0",
        "shock_rows": len(smoke_rows),
        "outcome_panel_rows": len(panel_rows),
        "controlled_dynamic_lp_panel_rows": len(controlled_panel_rows),
        "controlled_dynamic_lp_result_rows": len(controlled_result_rows),
        "controlled_dynamic_lp_support_rows": len(support_rows),
        "release_5_0_decision_rows": len(decision_rows),
        "proxy_svar_final_blocker_rows": len(proxy_blocker_rows),
        "controlled_dynamic_lp_appendix_enabled": dynamic_enabled,
        "proxy_svar_claim_enabled": False,
        "full_lp_proxy_svar_claim_enabled": False,
        "raw_rate_change_identification_rejected": True,
        "pricing_output_enabled": False,
        "incidence_claim_enabled": False,
        "release_5_0_decision": (
            "controlled_dynamic_lp_enabled_proxy_svar_blocked"
            if dynamic_enabled
            else "dynamic_lp_blocked_by_support_or_rank"
        ),
        "paper_claim_boundary": (
            "bounded_admissible_shock_controlled_dynamic_lp_not_proxy_svar_pricing_or_incidence"
        ),
    }


def _controlled_panel_groups(
    controlled_panel_rows: list[dict[str, object]],
) -> list[tuple[str, int]]:
    return sorted(
        {
            (str(row["outcome_variable"]), int(row["horizon_months"]))
            for row in controlled_panel_rows
            if row.get("panel_status") == "source_backed_controlled_dynamic_lp_row"
        }
    )


def _release_5_0_dynamic_lp_appendix_text(
    *,
    controlled_result_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    proxy_blocker_rows: list[dict[str, object]],
) -> str:
    enabled = any(
        row.get("decision_id") == "release_5_0_identification_decision"
        and row.get("controlled_dynamic_lp_appendix_enabled") == "true"
        for row in decision_rows
    )
    estimate_rows = [
        row
        for row in controlled_result_rows
        if row.get("result_status")
        == "admissible_shock_controlled_dynamic_lp_with_limitations"
    ]
    lines = [
        "# RateWall Release 5.0 Dynamic LP Appendix",
        "",
        "## Identification Status",
        "",
        "Release 5.0 adds a bounded event-level local-projection appendix using "
        "SF Fed orthogonalized monetary surprises, official outcome panels, "
        "lagged outcome changes, and source-backed RateWall state controls. "
        "It rejects raw policy-rate changes as shocks and does not estimate a "
        "proxy-SVAR system.",
        "",
        f"- Controlled dynamic-LP appendix enabled: `{str(enabled).lower()}`",
        f"- Controlled estimate rows: `{len(estimate_rows)}`",
        f"- Support diagnostic rows: `{len(support_rows)}`",
        "- Proxy-SVAR claim enabled: `false`",
        "- Pricing, holder-incidence, tax, MPC, welfare, and reset-calendar "
        "outputs enabled: `false`",
        "",
        "## Controlled Dynamic-LP Estimates",
        "",
    ]
    if estimate_rows:
        for row in estimate_rows:
            lines.append(
                f"- `{row['result_id']}`: shock={row['shock_estimate']} "
                f"(HAC se={row['shock_hac_standard_error']}), "
                f"state interaction={row['state_interaction_estimate']} "
                f"(HAC se={row['state_interaction_hac_standard_error']}), "
                f"n={row['n_obs']}."
            )
    else:
        lines.append(
            "- No controlled dynamic-LP estimate is emitted in this snapshot; "
            "the blocker rows remain the operative evidence surface."
        )
    lines.extend(["", "## Support Diagnostics", ""])
    for row in support_rows:
        lines.append(
            f"- `{row['diagnostic_id']}`: `{row['support_status']}`, "
            f"n={row['n_obs']}, years={row['unique_event_years']}."
        )
    lines.extend(["", "## Release 5.0 Decision Rows", ""])
    for row in decision_rows:
        lines.append(
            f"- `{row['decision_id']}`: `{row['decision_status']}`; "
            f"action `{row['release_5_0_action']}`."
        )
    lines.extend(["", "## Proxy-SVAR Blocker", ""])
    for row in proxy_blocker_rows:
        lines.append(f"- `{row['blocker_id']}`: `{row['blocker_status']}`.")
        lines.append(f"  Required resolution: {row['required_resolution']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "The appendix is a bounded admissible-shock dynamic-LP appendix "
            "when the support/rank gates pass. It does not claim that higher "
            "rates always raise inflation, does not claim that the Federal "
            "Reserve has stopped working, and does not enable pricing, "
            "holder-incidence, tax, MPC, welfare, reset-calendar construction, "
            "or proxy-SVAR outputs.",
            "",
        ]
    )
    return "\n".join(lines)


def _release_5_0_referee_response_text(
    *,
    controlled_result_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    proxy_blocker_rows: list[dict[str, object]],
) -> str:
    estimate_rows = [
        row
        for row in controlled_result_rows
        if row.get("result_status")
        == "admissible_shock_controlled_dynamic_lp_with_limitations"
    ]
    final_decision = next(
        row
        for row in decision_rows
        if row.get("decision_id") == "release_5_0_identification_decision"
    )
    proxy_blocker = proxy_blocker_rows[0]
    return "\n".join(
        [
            "# RateWall Release 5.0 Referee Response",
            "",
            "## Concern: Does the package now contain a dynamic causal design?",
            "",
            "Response: Release 5.0 contains a bounded controlled local-projection "
            "appendix when the event/control panel has enough support and rank. "
            "The shock is the SF Fed orthogonalized monetary surprise, not a raw "
            "policy-rate change.",
            "",
            f"- Controlled dynamic-LP estimate rows: `{len(estimate_rows)}`",
            f"- Release decision: `{final_decision['decision_status']}`",
            "",
            "## Concern: Is this a proxy-SVAR?",
            "",
            "Response: no. The release does not estimate a reduced-form VAR "
            "system, proxy first stage, timing/invertibility diagnostics, or "
            "system residual diagnostics.",
            "",
            f"- Proxy-SVAR blocker: `{proxy_blocker['blocker_status']}`",
            f"- Required resolution: {proxy_blocker['required_resolution']}",
            "",
            "## Concern: Did the claim boundary change?",
            "",
            "Response: no pricing, holder allocation, tax, MPC, welfare, "
            "reset-calendar construction, or incidence outputs are enabled. "
            "The package still rejects universal inflation-sign language and "
            "does not claim that the Federal Reserve has stopped working.",
            "",
        ]
    )


def _write_release_5_0_dynamic_lp_figure(
    path: Path,
    *,
    controlled_result_rows: list[dict[str, object]],
) -> None:
    estimate_rows = [
        row
        for row in controlled_result_rows
        if row.get("result_status")
        == "admissible_shock_controlled_dynamic_lp_with_limitations"
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1100
    height = max(300, 112 + len(estimate_rows) * 42)
    zero_x = 520
    scale = 18
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="36" font-family="Arial" font-size="20" font-weight="700">RateWall Release 5.0 controlled dynamic LP</text>',
        '<text x="24" y="62" font-family="Arial" font-size="12" fill="#444">Admissible SF Fed shocks with lag/state controls; bounded appendix, not proxy-SVAR/pricing/incidence output.</text>',
        f'<line x1="{zero_x}" y1="84" x2="{zero_x}" y2="{height - 34}" stroke="#777" stroke-width="1"/>',
    ]
    if not estimate_rows:
        parts.append(
            '<text x="24" y="124" font-family="Arial" font-size="13" fill="#444">No controlled dynamic-LP estimates emitted; blocker remains active.</text>'
        )
    for idx, row in enumerate(estimate_rows):
        y = 102 + idx * 42
        estimate = float(row["shock_estimate"])
        bar_width = min(abs(estimate) * scale, 430)
        x = zero_x if estimate >= 0 else zero_x - bar_width
        fill = "#2f6f73" if estimate >= 0 else "#9a4d3f"
        label = f"{row['outcome_variable']} {row['horizon_months']}m"
        parts.extend(
            [
                f'<text x="24" y="{y + 17}" font-family="Arial" font-size="12" fill="#111">{label}</text>',
                f'<rect x="{x:.1f}" y="{y}" width="{bar_width:.1f}" height="22" fill="{fill}"/>',
                f'<text x="{zero_x + 452}" y="{y + 17}" font-family="Arial" font-size="11" fill="#222">shock={estimate:.3f}; n={row["n_obs"]}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _ols_hac_multivariate(
    x: list[list[float]],
    y: list[float],
    *,
    coefficient_names: list[str],
    hac_lag: int,
) -> dict[str, dict[str, float]] | None:
    if not x or len(x) != len(y) or len(x) <= len(coefficient_names):
        return None
    if any(len(row) != len(coefficient_names) for row in x):
        return None
    xt = _transpose(x)
    xtx = _matmul(xt, x)
    xtx_inv = _invert_matrix(xtx)
    if xtx_inv is None:
        return None
    xty = _matvec(xt, y)
    beta = _matvec(xtx_inv, xty)
    residuals = [
        y_value - sum(coef * value for coef, value in zip(beta, row))
        for row, y_value in zip(x, y)
    ]
    k = len(coefficient_names)
    meat = [[0.0 for _col in range(k)] for _row in range(k)]
    for row, residual in zip(x, residuals):
        _add_outer_product(meat, row, row, residual * residual)
    max_lag = min(hac_lag, len(x) - 1)
    for lag_index in range(1, max_lag + 1):
        weight = 1.0 - lag_index / (max_lag + 1.0)
        for idx in range(lag_index, len(x)):
            scale = weight * residuals[idx] * residuals[idx - lag_index]
            _add_outer_product(meat, x[idx], x[idx - lag_index], scale)
            _add_outer_product(meat, x[idx - lag_index], x[idx], scale)
    covariance = _matmul(_matmul(xtx_inv, meat), xtx_inv)
    standard_errors = [
        sqrt(max(covariance[index][index], 0.0))
        for index in range(k)
    ]
    coef_by_name = dict(zip(coefficient_names, beta))
    se_by_name = dict(zip(coefficient_names, standard_errors))
    t_by_name = {
        name: (coef_by_name[name] / se_by_name[name] if se_by_name[name] > 0 else 0.0)
        for name in coefficient_names
    }
    return {"coef": coef_by_name, "se": se_by_name, "t": t_by_name}


def _transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*matrix)]


def _matmul(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    right_t = _transpose(right)
    return [
        [sum(a * b for a, b in zip(left_row, right_col)) for right_col in right_t]
        for left_row in left
    ]


def _matvec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [sum(value * coef for value, coef in zip(row, vector)) for row in matrix]


def _add_outer_product(
    target: list[list[float]],
    left: list[float],
    right: list[float],
    scale: float,
) -> None:
    for row_index, left_value in enumerate(left):
        for col_index, right_value in enumerate(right):
            target[row_index][col_index] += scale * left_value * right_value


def _invert_matrix(matrix: list[list[float]]) -> list[list[float]] | None:
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        return None
    augmented = [
        [float(value) for value in row]
        + [1.0 if row_index == col_index else 0.0 for col_index in range(size)]
        for row_index, row in enumerate(matrix)
    ]
    for col_index in range(size):
        pivot = max(
            range(col_index, size),
            key=lambda row_index: abs(augmented[row_index][col_index]),
        )
        if abs(augmented[pivot][col_index]) < 1e-12:
            return None
        if pivot != col_index:
            augmented[col_index], augmented[pivot] = (
                augmented[pivot],
                augmented[col_index],
            )
        pivot_value = augmented[col_index][col_index]
        augmented[col_index] = [value / pivot_value for value in augmented[col_index]]
        for row_index in range(size):
            if row_index == col_index:
                continue
            factor = augmented[row_index][col_index]
            augmented[row_index] = [
                value - factor * pivot_row_value
                for value, pivot_row_value in zip(
                    augmented[row_index], augmented[col_index]
                )
            ]
    return [row[size:] for row in augmented]


def _count_by(rows: list[dict[str, object]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field, ""))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _causal_identification_appendix_text(
    *,
    audit_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
) -> str:
    event_count = sum(
        row["artifact_layer"] == "empirical_event_study_estimate"
        for row in result_rows
    )
    association_count = sum(
        row["artifact_layer"] == "empirical_estimate_bounded" for row in result_rows
    )
    lines = [
        "# RateWall Release 1.1 Causal-Identification Appendix",
        "",
        "## Release Decision",
        "",
        "Release 1.1 reports bounded event-study estimates using SF Fed "
        "orthogonalized monetary surprises and keeps full LP/proxy-SVAR "
        "causal transmission claims disabled.",
        "",
        f"- Bounded event-study rows: {event_count}",
        f"- Shock/state association rows: {association_count}",
        "- Raw policy-rate changes as shocks: rejected",
        "- Causal LP/proxy-SVAR claim enabled: false",
        "",
        "## Audit Ledger",
        "",
    ]
    for row in audit_rows:
        lines.append(
            f"- `{row['audit_component']}`: `{row['audit_status']}`; "
            f"decision `{row['release_1_1_decision']}`."
        )
    lines.extend(["", "## Final Blocker", ""])
    for row in blocker_rows:
        lines.append(f"- `{row['blocker_id']}`: `{row['blocker_status']}`.")
        lines.append(f"  Required resolution: {row['required_resolution']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "The appendix is a review-ready identification audit. It does not "
            "claim that higher rates always raise inflation, does not claim "
            "that the Federal Reserve has stopped working, and does not enable "
            "pricing, holder-incidence, tax, MPC, welfare, or reset-calendar outputs.",
            "",
        ]
    )
    return "\n".join(lines)


def _reviewer_limitations_memo_text(
    *,
    audit_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
) -> str:
    statuses = _count_by(result_rows, "result_status")
    blocked = [row for row in audit_rows if row["audit_status"] in {"blocked", "fail"}]
    lines = [
        "# RateWall Reviewer Limitations Memo",
        "",
        "## What The Release Supports",
        "",
        "- Source-backed public-liability accounting and scenario diagnostics.",
        "- Bounded event-study estimates using an admissible monetary-shock series.",
        "- Shock/state descriptive diagnostics for RateWall state variables.",
        "",
        "## What The Release Does Not Support",
        "",
        "- A full dynamic LP/proxy-SVAR monetary-transmission claim.",
        "- A universal inflation-sign claim for rate hikes.",
        "- A claim that the Federal Reserve has stopped working.",
        "- Pricing, holder allocation, tax, MPC, welfare, reset-calendar, or incidence outputs.",
        "",
        "## Empirical Result Status Counts",
        "",
    ]
    for status, count in sorted(statuses.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Remaining Review Blockers", ""])
    for row in blocked:
        lines.append(
            f"- `{row['audit_component']}` requires: {row['required_value']}"
        )
    lines.extend(["", "## Machine-Readable Blocker Rows", ""])
    for row in blocker_rows:
        lines.append(f"- `{row['blocker_id']}`: {row['release_action']}")
    lines.append("")
    return "\n".join(lines)


def _submission_causal_appendix_text(
    *,
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
    result_rows: list[dict[str, object]],
) -> str:
    event_count = sum(
        row["artifact_layer"] == "empirical_event_study_estimate"
        for row in result_rows
    )
    support_pass = sum(
        row["support_status"] == "submission_support_pass_bounded_event_study"
        for row in support_rows
    )
    full_lp_row = next(
        row
        for row in decision_rows
        if row["decision_id"] == "full_lp_proxy_svar_identification"
    )
    final_row = next(
        row
        for row in decision_rows
        if row["decision_id"] == "release_2_0_submission_decision"
    )
    lines = [
        "# RateWall Release 2.0 Submission Causal Appendix",
        "",
        "## Identification Claim",
        "",
        "Release 2.0 uses SF Fed orthogonalized high-frequency monetary-policy "
        "surprises as the admissible external shock. The appendix reports a "
        "bounded reduced-form event-study evidence package with support and "
        "robustness diagnostics. It does not claim a full dynamic LP/proxy-SVAR "
        "transmission model.",
        "",
        f"- Event-study estimate rows: {event_count}",
        f"- Support diagnostic rows passing: {support_pass} of {len(support_rows)}",
        f"- Robustness diagnostic rows: {len(robustness_rows)}",
        f"- Release decision: `{final_row['decision_status']}`",
        f"- Full LP/proxy-SVAR status: `{full_lp_row['decision_status']}`",
        "- Raw policy-rate changes as shocks: rejected",
        "- Pricing, holder allocation, welfare, and incidence outputs: disabled",
        "",
        "## Support Diagnostics",
        "",
    ]
    for row in support_rows:
        lines.append(
            f"- `{row['diagnostic_id']}`: `{row['support_status']}`, "
            f"n={row['n_obs']}, years={row['unique_event_years']}, "
            f"low/high state n={row['low_state_n']}/{row['high_state_n']}."
        )
    lines.extend(["", "## Robustness Diagnostics", ""])
    for row in robustness_rows:
        if row["diagnostic_type"] == "baseline_external_shock_event_study":
            continue
        lines.append(
            f"- `{row['robustness_id']}`: `{row['robustness_status']}`, "
            f"estimate={row['robustness_estimate']}, "
            f"delta={row['difference_from_baseline']}."
        )
    lines.extend(
        [
            "",
            "## Final Boundary",
            "",
            "The event-study appendix is submission-ready as bounded evidence "
            "because it uses an admissible shock and audited source-backed panels. "
            "The stronger LP/proxy-SVAR claim remains blocked pending the dynamic "
            "specification, lag/control, serial-correlation, and system-level "
            "diagnostics listed in `ratewall_submission_identification_decision.csv`.",
            "",
        ]
    )
    return "\n".join(lines)


def _external_review_response_packet_text(
    *,
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
    decision_rows: list[dict[str, object]],
) -> str:
    final_row = next(
        row
        for row in decision_rows
        if row["decision_id"] == "release_2_0_submission_decision"
    )
    blocked = [
        row
        for row in decision_rows
        if row["decision_status"] in {"blocked", "fail"}
    ]
    lines = [
        "# RateWall External Review Response Packet",
        "",
        "## Reviewer Concern: Identification",
        "",
        "Response: the release uses SF Fed orthogonalized monetary surprises, "
        "rejects raw policy-rate changes, and separates bounded event-study "
        "evidence from full dynamic LP/proxy-SVAR claims.",
        "",
        "## Reviewer Concern: Sample Support",
        "",
        f"Response: {len(support_rows)} support diagnostic rows and "
        f"{len(robustness_rows)} robustness rows are generated from the same "
        "source-backed outcome/state panel as the estimates.",
        "",
        "## Reviewer Concern: Overclaiming",
        "",
        "Response: pricing, holder allocation, tax, MPC, welfare, reset-calendar, "
        "and incidence outputs remain disabled; the release does not claim that "
        "higher rates always raise inflation or that the Federal Reserve has "
        "stopped working.",
        "",
        "## Release 2.0 Decision",
        "",
        f"- `{final_row['decision_id']}`: `{final_row['decision_status']}`",
        "",
        "## Remaining Blocked Items",
        "",
    ]
    for row in blocked:
        lines.append(f"- `{row['decision_id']}` requires: {row['required_value']}")
    lines.append("")
    return "\n".join(lines)


def _submission_appendix_index_text() -> str:
    return "\n".join(
        [
            "# RateWall Submission Appendix Index",
            "",
            "- `outputs/reports/ratewall_submission_causal_appendix.md`",
            "- `outputs/reports/ratewall_external_review_response_packet.md`",
            "- `outputs/tables/ratewall_event_study_support_diagnostics.csv`",
            "- `outputs/tables/ratewall_event_study_robustness.csv`",
            "- `outputs/tables/ratewall_submission_identification_decision.csv`",
            "- `outputs/tables/ratewall_empirical_robustness_manifest.json`",
            "- `outputs/figures/ratewall_event_study_robustness.svg`",
            "",
            "All appendix surfaces preserve the Release 2.0 claim boundary: "
            "bounded event-study evidence is separated from full LP/proxy-SVAR, "
            "pricing, holder-incidence, and welfare claims.",
            "",
        ]
    )


def _journal_submission_appendix_text(
    *,
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
    support_rows: list[dict[str, object]],
    robustness_rows: list[dict[str, object]],
) -> str:
    blocked_lp = [row for row in lp_rows if row["gate_status"] == "blocked"]
    blocked_proxy = [row for row in proxy_rows if row["gate_status"] == "blocked"]
    final = blocker_rows[0]
    lines = [
        "# RateWall Release 3.0 Journal-Submission Appendix",
        "",
        "## Release 3.0 Identification Decision",
        "",
        "Release 3.0 is organized as a journal-submission package for the "
        "source-labeled accounting, scenario, and bounded event-study evidence. "
        "It does not claim a full dynamic LP/proxy-SVAR monetary-transmission "
        "estimate because the feasibility gates below remain unresolved.",
        "",
        f"- Event-study support diagnostic rows: {len(support_rows)}",
        f"- Event-study robustness rows: {len(robustness_rows)}",
        f"- Dynamic LP feasibility rows: {len(lp_rows)}",
        f"- Proxy-SVAR feasibility rows: {len(proxy_rows)}",
        f"- Release action: `{final['release_3_0_action']}`",
        "- Bounded event-study appendix enabled: true",
        "- Dynamic LP claim enabled: false",
        "- Proxy-SVAR claim enabled: false",
        "- Raw policy-rate-change identification: rejected",
        "",
        "## Dynamic LP Feasibility Ledger",
        "",
    ]
    for row in lp_rows:
        lines.append(
            f"- `{row['gate_id']}`: `{row['gate_status']}`; "
            f"decision `{row['release_3_0_decision']}`."
        )
    lines.extend(["", "## Proxy-SVAR Feasibility Ledger", ""])
    for row in proxy_rows:
        lines.append(
            f"- `{row['gate_id']}`: `{row['gate_status']}`; "
            f"decision `{row['release_3_0_decision']}`."
        )
    lines.extend(["", "## Final Dynamic-Causal Blocker", ""])
    lines.append(f"- Blocked dynamic LP gates: {len(blocked_lp)}")
    lines.append(f"- Blocked proxy-SVAR gates: {len(blocked_proxy)}")
    lines.append(f"- Required resolution: {final['required_resolution']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This appendix strengthens the review surface by making the causal "
            "frontier machine-readable. It does not claim that higher rates "
            "always raise inflation, does not claim that the Federal Reserve "
            "has stopped working, and does not enable pricing, holder-incidence, "
            "tax, MPC, welfare, or reset-calendar outputs.",
            "",
        ]
    )
    return "\n".join(lines)


def _dynamic_causal_blocker_memo_text(
    *,
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> str:
    lines = [
        "# RateWall Dynamic-Causal Blocker Memo",
        "",
        "## Bottom Line",
        "",
        "The Release 3.0 evidence is journal-ready as bounded event-study and "
        "source-labeled accounting evidence. It is not journal-ready as a full "
        "dynamic LP/proxy-SVAR transmission estimate.",
        "",
        "## Blocked Dynamic LP Requirements",
        "",
    ]
    for row in lp_rows:
        if row["gate_status"] == "blocked":
            lines.append(f"- `{row['gate_id']}` requires: {row['required_value']}")
    lines.extend(["", "## Blocked Proxy-SVAR Requirements", ""])
    for row in proxy_rows:
        if row["gate_status"] == "blocked":
            lines.append(f"- `{row['gate_id']}` requires: {row['required_value']}")
    lines.extend(["", "## Machine-Readable Release Action", ""])
    for row in blocker_rows:
        lines.append(f"- `{row['blocker_id']}`: `{row['release_3_0_action']}`")
    lines.extend(
        [
            "",
            "## Use In Paper",
            "",
            "Use this memo to explain why the paper reports bounded event-study "
            "evidence instead of overstating a full causal design. The memo is "
            "a limitation surface, not a new estimate.",
            "",
        ]
    )
    return "\n".join(lines)


def _referee_response_compendium_text(
    *,
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> str:
    final = blocker_rows[0]
    return "\n".join(
        [
            "# RateWall Referee Response Compendium",
            "",
            "## Concern: Why not estimate a full dynamic LP?",
            "",
            "Response: Release 3.0 audits the required ingredients and keeps "
            "the full LP claim blocked because lag/control, HAC or clustered "
            "uncertainty, placebo/pretrend, and state-interaction gates are "
            "not yet satisfied.",
            "",
            "## Concern: Why not estimate a proxy-SVAR?",
            "",
            "Response: the SF Fed surprise is an admissible external shock, but "
            "the release does not assemble an estimated reduced-form system, "
            "first-stage relevance tests, timing/invertibility diagnostics, or "
            "state-dependent proxy-SVAR design.",
            "",
            "## Concern: Are the current empirical rows causal?",
            "",
            "Response: they are bounded event-study estimates and support "
            "diagnostics using an admissible shock; raw policy-rate changes are "
            "rejected and stronger transmission claims remain disabled.",
            "",
            "## Machine-Readable Evidence",
            "",
            "- `outputs/tables/ratewall_dynamic_lp_feasibility_diagnostics.csv`",
            "- `outputs/tables/ratewall_proxy_svar_feasibility_diagnostics.csv`",
            "- `outputs/tables/ratewall_dynamic_causal_final_blocker.csv`",
            "- `outputs/tables/ratewall_journal_submission_manifest.json`",
            f"- Release action: `{final['release_3_0_action']}`",
            f"- Dynamic LP rows: {len(lp_rows)}",
            f"- Proxy-SVAR rows: {len(proxy_rows)}",
            "",
        ]
    )


def _release_3_0_cover_note_text(
    blocker_rows: list[dict[str, object]],
) -> str:
    final = blocker_rows[0]
    return "\n".join(
        [
            "# RateWall Release 3.0 Cover Note",
            "",
            "Release 3.0 is the journal-submission package. It preserves the "
            "bounded event-study evidence and adds a final dynamic-causal "
            "blocker ledger rather than widening into unsupported LP/proxy-SVAR "
            "claims.",
            "",
            f"- Release action: `{final['release_3_0_action']}`",
            "- Dynamic LP claim enabled: false",
            "- Proxy-SVAR claim enabled: false",
            "- Pricing/incidence/welfare outputs enabled: false",
            "- Raw policy-rate-change shocks: rejected",
            "",
        ]
    )


def _release_4_0_final_submission_memo_text(
    *,
    hac_rows: list[dict[str, object]],
    placebo_rows: list[dict[str, object]],
    contract_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> str:
    final = blocker_rows[0]
    blocked_contract = [
        row
        for row in contract_rows
        if row.get("requirement_status") != "pass"
    ]
    lines = [
        "# RateWall Release 4.0 Final Submission Memo",
        "",
        "## Bottom Line",
        "",
        "Release 4.0 is the maximal defensible journal-submission package from "
        "the current evidence state. It adds HAC-style uncertainty diagnostics, "
        "predetermined-level placebo diagnostics, and a disabled causal-claim "
        "promotion contract, but it does not promote the bounded event-study "
        "appendix into a full dynamic LP/proxy-SVAR result.",
        "",
        f"- HAC-style diagnostic rows: {len(hac_rows)}",
        f"- Predetermined-level placebo rows: {len(placebo_rows)}",
        f"- Disabled promotion-contract rows: {len(contract_rows)}",
        f"- Unresolved promotion requirements: {len(blocked_contract)}",
        f"- Release action: `{final['release_4_0_action']}`",
        "- Dynamic LP claim enabled: false",
        "- Proxy-SVAR claim enabled: false",
        "- Raw policy-rate-change shocks: rejected",
        "- Pricing/incidence/welfare outputs enabled: false",
        "",
        "## Final Claim Boundary",
        "",
        "The evidence supports source-labeled accounting, scenario diagnostics, "
        "and bounded event-study evidence using an admissible external shock. "
        "It does not support a universal inflation-sign claim, a claim that the "
        "Federal Reserve has stopped working, or pricing/incidence/welfare claims.",
        "",
    ]
    return "\n".join(lines)


def _release_4_0_referee_packet_text(
    *,
    issue_rows: list[dict[str, object]],
    checklist_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> str:
    final = blocker_rows[0]
    lines = [
        "# RateWall Release 4.0 Referee Packet",
        "",
        "## Review Position",
        "",
        "The release is review-ready as a bounded accounting and event-study "
        "package. The machine-readable blocker is the answer to requests for "
        "a stronger dynamic causal design unless future gates are implemented.",
        "",
        f"- Final blocker: `{final['blocker_id']}`",
        f"- Final action: `{final['release_4_0_action']}`",
        "",
        "## Issue Matrix",
        "",
    ]
    for row in issue_rows:
        lines.append(
            f"- `{row['issue_id']}`: `{row['response_status']}`; "
            f"{row['release_response']}"
        )
    lines.extend(["", "## Submission Checklist", ""])
    for row in checklist_rows:
        lines.append(
            f"- `{row['check_id']}`: `{row['check_status']}`; "
            f"artifact `{row['evidence_artifact']}`."
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "No raw-rate shock estimate, pricing output, holder allocation, "
            "welfare layer, reset-calendar construction, or incidence output "
            "is enabled in this release.",
            "",
        ]
    )
    return "\n".join(lines)


def _release_4_0_identification_frontier_appendix_text(
    *,
    hac_rows: list[dict[str, object]],
    placebo_rows: list[dict[str, object]],
    contract_rows: list[dict[str, object]],
    issue_rows: list[dict[str, object]],
    blocker_rows: list[dict[str, object]],
) -> str:
    blocked = [
        row
        for row in contract_rows
        if row.get("requirement_status") != "pass"
    ]
    lines = [
        "# RateWall Release 4.0 Identification Frontier Appendix",
        "",
        "## What Is Newly Audited",
        "",
        f"- HAC-style event-study uncertainty diagnostics: {len(hac_rows)}",
        f"- Predetermined-level placebo diagnostics: {len(placebo_rows)}",
        f"- External-review issue rows: {len(issue_rows)}",
        "",
        "## Disabled Promotion Contract",
        "",
    ]
    for row in contract_rows:
        lines.append(
            f"- `{row['requirement_id']}`: `{row['requirement_status']}`; "
            f"future prerequisite `{row['future_opt_in_prerequisite']}`."
        )
    lines.extend(["", "## Final Blocker", ""])
    for row in blocker_rows:
        lines.append(f"- `{row['blocker_id']}`: `{row['blocker_status']}`.")
        lines.append(f"  Required resolution: {row['required_resolution']}")
    lines.extend(
        [
            "",
            "## Journal-Grade Decision",
            "",
            f"{len(blocked)} promotion requirements remain unresolved. "
            "Release 4.0 therefore publishes the stronger blocker rather than "
            "claiming a full dynamic LP/proxy-SVAR, state-dependent causal "
            "effect, pricing result, or incidence result.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_release_4_0_identification_frontier_figure(
    path: Path,
    *,
    contract_rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1100
    row_height = 38
    height = 118 + row_height * len(contract_rows)
    colors = {
        "blocked": "#9a4d3f",
        "partial_diagnostic_not_promotion_ready": "#b8752c",
        "pass": "#2f6f73",
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="36" font-family="Arial" font-size="20" font-weight="700">RateWall Release 4.0 identification frontier</text>',
        '<text x="24" y="62" font-family="Arial" font-size="12" fill="#444">Non-pricing, non-incidence, validation-only causal-promotion contract; all stronger claims remain disabled.</text>',
        '<text x="24" y="92" font-family="Arial" font-size="12" font-weight="700">requirement</text>',
        '<text x="720" y="92" font-family="Arial" font-size="12" font-weight="700">status</text>',
    ]
    for idx, row in enumerate(contract_rows):
        y = 118 + idx * row_height
        status = str(row["requirement_status"])
        fill = colors.get(status, "#777777")
        parts.extend(
            [
                f'<rect x="18" y="{y - 22}" width="{width - 36}" height="30" fill="#f7f7f7"/>',
                f'<text x="24" y="{y}" font-family="Arial" font-size="12" fill="#111">{row["requirement_id"]}</text>',
                f'<rect x="720" y="{y - 16}" width="185" height="20" fill="{fill}"/>',
                f'<text x="914" y="{y}" font-family="Arial" font-size="12" fill="#111">{status}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_empirical_result_rows(
    smoke_rows: list[dict[str, object]],
    outcome_panel_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    rows.extend(_event_study_result_rows(outcome_panel_rows))
    states = [
        "public_liability_base_1y_gdp",
        "repricing_share_1y",
        "debt_held_public_gdp",
        "rate_sensitive_fed_liabilities_gdp",
    ]
    for state in states:
        observations = []
        for row in smoke_rows:
            shock = _decimal(row.get("orthogonalized_surprise_bps"))
            state_value = _decimal(row.get(state))
            if shock is None or state_value is None:
                continue
            observations.append((str(row["date"]), float(shock), float(state_value)))
        if len(observations) < 2:
            continue
        state_median = median(value for _, _, value in observations)
        low_shocks = [shock for _, shock, value in observations if value <= state_median]
        high_shocks = [shock for _, shock, value in observations if value > state_median]
        if not low_shocks or not high_shocks:
            continue
        estimate = _correlation(
            [shock for _, shock, _ in observations],
            [value for _, _, value in observations],
        )
        rows.append(
            {
                "artifact_layer": "empirical_estimate_bounded",
                "result_id": f"sf_fed_shock_state_association_{state}",
                "shock_dataset": "sf_fed_monetary_policy_surprises",
                "shock_column": "orthogonalized_surprise_bps",
                "outcome_variable": "",
                "horizon_months": "",
                "state_variable": state,
                "n_obs": len(observations),
                "sample_start": min(date_value for date_value, _, _ in observations),
                "sample_end": max(date_value for date_value, _, _ in observations),
                "estimator": "pearson_correlation_and_median_state_split",
                "estimate": f"{estimate:.6f}",
                "standard_error": "",
                "t_stat": "",
                "response_unit": "correlation",
                "state_median": f"{state_median:.6f}",
                "low_state_mean_shock_bps": f"{_mean(low_shocks):.6f}",
                "high_state_mean_shock_bps": f"{_mean(high_shocks):.6f}",
                "high_minus_low_mean_shock_bps": (
                    f"{(_mean(high_shocks) - _mean(low_shocks)):.6f}"
                ),
                "result_status": "admissible_shock_state_association_not_causal_lp",
                "causal_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "Source-backed SF Fed orthogonalized monetary surprise joined "
                    "to RateWall state variables; descriptive association only."
                ),
            }
        )
    rows.append(
        {
            "artifact_layer": "empirical_estimation_gate",
            "result_id": "causal_transmission_estimation_blocker",
            "shock_dataset": "sf_fed_monetary_policy_surprises",
            "shock_column": "orthogonalized_surprise_bps",
            "outcome_variable": "core_pce_inflation_industrial_production_unemployment",
            "horizon_months": "3,6,12",
            "state_variable": "ratewall_state_panel",
            "n_obs": len(smoke_rows),
            "sample_start": min((str(row["date"]) for row in smoke_rows), default=""),
            "sample_end": max((str(row["date"]) for row in smoke_rows), default=""),
            "estimator": "causal_lp_not_estimated",
            "estimate": "",
            "standard_error": "",
            "t_stat": "",
            "response_unit": "",
            "state_median": "",
            "low_state_mean_shock_bps": "",
            "high_state_mean_shock_bps": "",
            "high_minus_low_mean_shock_bps": "",
            "result_status": "final_documented_blocker_for_full_causal_lp_proxy_svar",
            "causal_claim_enabled": "false",
            "raw_rate_change_identification_rejected": "true",
            "pricing_output_enabled": "false",
            "incidence_claim_enabled": "false",
            "notes": (
                "The package now reports admissible shock/state associations, "
                "and bounded event-study outcome estimates, but does not claim "
                "a full causal LP/proxy-SVAR transmission design."
            ),
        }
    )
    return rows


def _build_outcome_panel_rows(
    snapshot_bundle: Path, smoke_rows: list[dict[str, object]]
) -> list[dict[str, object]]:
    snapshots = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in snapshots}
    outcomes = {
        "core_pce_price_index": ("PCEPILFE", "annualized_percent_change"),
        "industrial_production": ("INDPRO", "annualized_percent_change"),
        "unemployment_rate": ("UNRATE", "percentage_point_change"),
    }
    histories = {
        outcome_id: _dated_values(by_series[series_id].records)
        for outcome_id, (series_id, _transform) in outcomes.items()
        if series_id in by_series
    }
    rows: list[dict[str, object]] = []
    for smoke in smoke_rows:
        event_date = _date(str(smoke["date"]))
        shock = _decimal(smoke.get("orthogonalized_surprise_bps"))
        if shock is None:
            continue
        for outcome_id, (series_id, transform) in outcomes.items():
            history = histories.get(outcome_id, [])
            pre = _latest_at_or_before(history, event_date)
            for horizon in (3, 6, 12):
                post = _first_at_or_after(history, _add_months(event_date, horizon))
                change = _outcome_change(pre, post, horizon, transform)
                lag_start = _latest_at_or_before(
                    history, _add_months(event_date, -horizon)
                )
                lagged_change = _outcome_change(lag_start, pre, horizon, transform)
                if pre is None or post is None or change is None:
                    status = "blocked_missing_pre_or_post_outcome_observation"
                else:
                    status = "audited_source_backed_event_outcome"
                rows.append(
                    {
                        "event_date": smoke["date"],
                        "shock_dataset": "sf_fed_monetary_policy_surprises",
                        "shock_column": "orthogonalized_surprise_bps",
                        "orthogonalized_surprise_bps": shock,
                        "outcome_variable": outcome_id,
                        "outcome_source": series_id,
                        "horizon_months": horizon,
                        "pre_outcome_asof": _asof(pre),
                        "post_outcome_asof": _asof(post),
                        "pre_outcome_value": "" if pre is None else pre[1],
                        "post_outcome_value": "" if post is None else post[1],
                        "outcome_change": "" if change is None else f"{change:.6f}",
                        "outcome_change_unit": (
                            "annualized_percent_change"
                            if transform == "annualized_percent_change"
                            else "percentage_points"
                        ),
                        "lagged_outcome_start_asof": _asof(lag_start),
                        "lagged_outcome_end_asof": _asof(pre),
                        "lagged_outcome_change": (
                            "" if lagged_change is None else f"{lagged_change:.6f}"
                        ),
                        "lagged_outcome_change_unit": (
                            "annualized_percent_change"
                            if transform == "annualized_percent_change"
                            else "percentage_points"
                        ),
                        "public_liability_base_1y_gdp": smoke[
                            "public_liability_base_1y_gdp"
                        ],
                        "repricing_share_1y": smoke["repricing_share_1y"],
                        "debt_held_public_gdp": smoke["debt_held_public_gdp"],
                        "rate_sensitive_fed_liabilities_gdp": smoke[
                            "rate_sensitive_fed_liabilities_gdp"
                        ],
                        "state_alignment_scope": smoke["state_alignment_scope"],
                        "shock_identification": (
                            "sf_fed_orthogonalized_high_frequency_surprise"
                        ),
                        "raw_rate_change_identification_rejected": "true",
                        "panel_status": status,
                    }
                )
    return rows


def _event_study_result_rows(panel_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    state_variable = "public_liability_base_1y_gdp"
    groups = sorted(
        {
            (str(row["outcome_variable"]), int(row["horizon_months"]))
            for row in panel_rows
            if row["panel_status"] == "audited_source_backed_event_outcome"
        }
    )
    for outcome, horizon in groups:
        observations = []
        for row in panel_rows:
            if row["outcome_variable"] != outcome or int(row["horizon_months"]) != horizon:
                continue
            y = _float(row.get("outcome_change"))
            shock = _float(row.get("orthogonalized_surprise_bps"))
            state_value = _float(row.get(state_variable))
            if y is None or shock is None or state_value is None:
                continue
            observations.append((str(row["event_date"]), shock / 100.0, y, state_value))
        if len(observations) < 8:
            continue
        beta, se, t_stat = _ols_slope(
            [shock_100bp for _, shock_100bp, _, _ in observations],
            [outcome_change for _, _, outcome_change, _ in observations],
        )
        state_median = median(state for _, _, _, state in observations)
        low_obs = [
            (shock_100bp, y)
            for _, shock_100bp, y, state in observations
            if state <= state_median
        ]
        high_obs = [
            (shock_100bp, y)
            for _, shock_100bp, y, state in observations
            if state > state_median
        ]
        low_beta = _ols_slope(
            [shock for shock, _ in low_obs], [y for _, y in low_obs]
        )[0]
        high_beta = _ols_slope(
            [shock for shock, _ in high_obs], [y for _, y in high_obs]
        )[0]
        rows.append(
            {
                "artifact_layer": "empirical_event_study_estimate",
                "result_id": f"sf_fed_event_study_{outcome}_{horizon}m",
                "shock_dataset": "sf_fed_monetary_policy_surprises",
                "shock_column": "orthogonalized_surprise_bps",
                "outcome_variable": outcome,
                "horizon_months": horizon,
                "state_variable": state_variable,
                "n_obs": len(observations),
                "sample_start": min(event_date for event_date, _, _, _ in observations),
                "sample_end": max(event_date for event_date, _, _, _ in observations),
                "estimator": "single_shock_event_study_ols_per_100bp",
                "estimate": f"{beta:.6f}",
                "standard_error": f"{se:.6f}",
                "t_stat": f"{t_stat:.6f}",
                "response_unit": _response_unit(outcome),
                "state_median": f"{state_median:.6f}",
                "low_state_mean_shock_bps": "",
                "high_state_mean_shock_bps": "",
                "high_minus_low_mean_shock_bps": f"{(high_beta - low_beta):.6f}",
                "result_status": "admissible_event_study_estimate_with_limitations",
                "causal_claim_enabled": "false",
                "raw_rate_change_identification_rejected": "true",
                "pricing_output_enabled": "false",
                "incidence_claim_enabled": "false",
                "notes": (
                    "OLS event-study slope of forward official outcome changes on "
                    "SF Fed orthogonalized surprises, scaled per 100 bps. This is "
                    "an admissible shock estimate with limitations, not a full "
                    "dynamic LP/proxy-SVAR result."
                ),
            }
        )
    return rows


def _event_observations(
    panel_rows: list[dict[str, object]], outcome: str, horizon: int
) -> list[tuple[str, float, float, float, float]]:
    observations = []
    for row in panel_rows:
        if row.get("panel_status") != "audited_source_backed_event_outcome":
            continue
        if row["outcome_variable"] != outcome or int(row["horizon_months"]) != horizon:
            continue
        y = _float(row.get("outcome_change"))
        shock = _float(row.get("orthogonalized_surprise_bps"))
        state_value = _float(row.get("public_liability_base_1y_gdp"))
        pre_value = _float(row.get("pre_outcome_value"))
        if y is None or shock is None or state_value is None or pre_value is None:
            continue
        observations.append(
            (str(row["event_date"]), shock / 100.0, y, state_value, pre_value)
        )
    return observations


def _audited_outcome_horizon_groups(
    panel_rows: list[dict[str, object]],
) -> list[tuple[str, int]]:
    return sorted(
        {
            (str(row["outcome_variable"]), int(row["horizon_months"]))
            for row in panel_rows
            if row.get("panel_status") == "audited_source_backed_event_outcome"
        }
    )


def _robustness_row(
    *,
    outcome: str,
    horizon: int,
    diagnostic_type: str,
    estimator: str,
    n_obs: int,
    baseline: float,
    estimate: float,
    standard_error: float,
    t_stat: float,
    response_unit: str,
    status: str,
    notes: str,
) -> dict[str, object]:
    return {
        "robustness_id": f"{diagnostic_type}_{outcome}_{horizon}m",
        "outcome_variable": outcome,
        "horizon_months": horizon,
        "diagnostic_type": diagnostic_type,
        "estimator": estimator,
        "n_obs": n_obs,
        "baseline_estimate": f"{baseline:.6f}",
        "robustness_estimate": f"{estimate:.6f}",
        "difference_from_baseline": f"{(estimate - baseline):.6f}",
        "standard_error": f"{standard_error:.6f}",
        "t_stat": f"{t_stat:.6f}",
        "response_unit": response_unit,
        "robustness_status": status,
        "raw_rate_change_identification_rejected": "true",
        "bounded_event_study_appendix_enabled": "true",
        "full_lp_proxy_svar_claim_enabled": "false",
        "notes": notes,
    }


def _winsorized(values: list[float]) -> list[float]:
    if len(values) < 3:
        return values
    ordered = sorted(values)
    low = _percentile(ordered, 0.05)
    high = _percentile(ordered, 0.95)
    return [min(max(value, low), high) for value in values]


def _percentile(ordered_values: list[float], pct: float) -> float:
    if not ordered_values:
        return 0.0
    index = pct * (len(ordered_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered_values) - 1)
    weight = index - lower
    return ordered_values[lower] * (1.0 - weight) + ordered_values[upper] * weight


def _write_event_study_robustness_figure(
    path: Path, rows: list[dict[str, object]]
) -> None:
    baseline_rows = [
        row
        for row in rows
        if row["diagnostic_type"] == "baseline_external_shock_event_study"
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 980
    height = max(340, 92 + len(baseline_rows) * 38)
    zero_x = 470
    scale = 18
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="36" font-family="Arial" font-size="20" font-weight="700">RateWall Release 2.0 event-study robustness</text>',
        '<text x="24" y="62" font-family="Arial" font-size="12" fill="#444">Baseline reduced-form event-study slopes per 100 bps SF Fed orthogonalized surprise; not full LP/proxy-SVAR estimates.</text>',
        f'<line x1="{zero_x}" y1="82" x2="{zero_x}" y2="{height - 32}" stroke="#777" stroke-width="1"/>',
    ]
    for idx, row in enumerate(baseline_rows):
        y = 92 + idx * 38
        estimate = float(row["robustness_estimate"])
        bar_width = min(abs(estimate) * scale, 420)
        x = zero_x if estimate >= 0 else zero_x - bar_width
        fill = "#2f6f73" if estimate >= 0 else "#9a4d3f"
        label = f"{row['outcome_variable']} {row['horizon_months']}m"
        parts.extend(
            [
                f'<text x="24" y="{y + 18}" font-family="Arial" font-size="12" fill="#111">{label}</text>',
                f'<rect x="{x:.1f}" y="{y}" width="{bar_width:.1f}" height="22" fill="{fill}"/>',
                f'<text x="{zero_x + 438}" y="{y + 17}" font-family="Arial" font-size="11" fill="#222">est={estimate:.3f}; n={row["n_obs"]}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _write_dynamic_causal_gate_figure(
    path: Path,
    *,
    lp_rows: list[dict[str, object]],
    proxy_rows: list[dict[str, object]],
) -> None:
    gate_rows = [
        ("LP", str(row["gate_id"]), str(row["gate_status"])) for row in lp_rows
    ] + [
        ("SVAR", str(row["gate_id"]), str(row["gate_status"])) for row in proxy_rows
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1040
    row_height = 34
    height = 112 + row_height * len(gate_rows)
    colors = {"pass": "#2f6f73", "fail": "#b8752c", "blocked": "#9a4d3f"}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="36" font-family="Arial" font-size="20" font-weight="700">RateWall Release 3.0 dynamic causal gate</text>',
        '<text x="24" y="62" font-family="Arial" font-size="12" fill="#444">Validation-only feasibility ledger; bounded event study remains enabled, dynamic LP/proxy-SVAR claims remain disabled.</text>',
        '<text x="24" y="92" font-family="Arial" font-size="12" font-weight="700">family</text>',
        '<text x="120" y="92" font-family="Arial" font-size="12" font-weight="700">gate</text>',
        '<text x="760" y="92" font-family="Arial" font-size="12" font-weight="700">status</text>',
    ]
    for idx, (family, gate, status) in enumerate(gate_rows):
        y = 112 + idx * row_height
        fill = colors.get(status, "#777777")
        parts.extend(
            [
                f'<rect x="18" y="{y - 20}" width="{width - 36}" height="28" fill="#f7f7f7"/>',
                f'<text x="24" y="{y}" font-family="Arial" font-size="12" fill="#111">{family}</text>',
                f'<text x="120" y="{y}" font-family="Arial" font-size="12" fill="#111">{gate}</text>',
                f'<rect x="760" y="{y - 14}" width="110" height="18" fill="{fill}"/>',
                f'<text x="880" y="{y}" font-family="Arial" font-size="12" fill="#111">{status}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _correlation(xs: list[float], ys: list[float]) -> float:
    x_mean = _mean(xs)
    y_mean = _mean(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    x_var = sum((x - x_mean) ** 2 for x in xs)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    if x_var <= 0 or y_var <= 0:
        return 0.0
    return numerator / ((x_var * y_var) ** 0.5)


def _write_empirical_state_figure(path: Path, rows: list[dict[str, object]]) -> None:
    estimate_rows = [
        row for row in rows if row["artifact_layer"] == "empirical_estimate_bounded"
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 920
    height = 360
    margin_left = 250
    zero_x = margin_left + 280
    scale = 230
    bar_height = 34
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="36" font-family="Arial" font-size="20" font-weight="700">RateWall admissible shock/state evidence</text>',
        '<text x="24" y="62" font-family="Arial" font-size="12" fill="#444">SF Fed orthogonalized monetary surprises; correlations are descriptive, not causal estimates.</text>',
        f'<line x1="{zero_x}" y1="86" x2="{zero_x}" y2="{height - 48}" stroke="#777" stroke-width="1"/>',
    ]
    for idx, row in enumerate(estimate_rows):
        y = 98 + idx * 58
        estimate = float(row["estimate"])
        bar_width = abs(estimate) * scale
        x = zero_x if estimate >= 0 else zero_x - bar_width
        fill = "#2f6f73" if estimate >= 0 else "#9a4d3f"
        parts.extend(
            [
                f'<text x="24" y="{y + 22}" font-family="Arial" font-size="13" fill="#111">{row["state_variable"]}</text>',
                f'<rect x="{x:.1f}" y="{y}" width="{bar_width:.1f}" height="{bar_height}" fill="{fill}"/>',
                f'<text x="{zero_x + scale + 18}" y="{y + 22}" font-family="Arial" font-size="12" fill="#222">corr={estimate:.3f}; n={row["n_obs"]}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _write_empirical_result_report(
    path: Path,
    rows: list[dict[str, object]],
    *,
    outcome_panel: Path | None,
    figure: Path | None,
) -> None:
    association_rows = [
        row for row in rows if row["artifact_layer"] == "empirical_estimate_bounded"
    ]
    event_rows = [
        row
        for row in rows
        if row["artifact_layer"] == "empirical_event_study_estimate"
    ]
    blocker = next(
        row for row in rows if row["result_id"] == "causal_transmission_estimation_blocker"
    )
    lines = [
        "# RateWall Empirical Result Status",
        "",
        "## Bounded Result Artifact",
        "",
        f"- Admissible event-study estimate rows: {len(event_rows)}",
        f"- Admissible shock/state association rows: {len(association_rows)}",
        f"- Monetary shock dataset: {blocker['shock_dataset']}",
        "- Raw policy-rate-change identification: rejected",
        "- Full causal LP/proxy-SVAR transmission claims: not enabled",
        "",
        "The empirical table reports source-backed event-study estimates from "
        "SF Fed orthogonalized monetary-policy surprises to official outcome "
        "series, plus state associations. It does not claim that higher rates "
        "always raise inflation or that the Federal Reserve has stopped working.",
        "",
        "## Output Files",
        "",
    ]
    if outcome_panel is not None:
        lines.append(f"- Outcome panel: `{outcome_panel}`")
    if figure is not None:
        lines.append(f"- Figure: `{figure}`")
    lines.extend(
        [
            "",
            "## Final Estimation Gate",
            "",
            str(blocker["notes"]),
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_final_paper_support(path: Path, rows: list[dict[str, object]]) -> None:
    event_rows = [
        row
        for row in rows
        if row["artifact_layer"] == "empirical_event_study_estimate"
    ]
    outcome_names = sorted({str(row["outcome_variable"]) for row in event_rows})
    lines = [
        "# RateWall Final Paper Support",
        "",
        "## Empirical Result Status",
        "",
        f"- Event-study estimate rows: {len(event_rows)}",
        f"- Outcome families: {', '.join(outcome_names) if outcome_names else 'none'}",
        "- Shock identification: SF Fed orthogonalized monetary surprises",
        "- Raw policy-rate-change identification: rejected",
        "- Full LP/proxy-SVAR claims: disabled pending a fuller design",
        "- Pricing, allocation, incidence, and welfare outputs: disabled",
        "",
        "## Paper Claim Boundary",
        "",
        "The final package can report source-labeled accounting, scenario "
        "diagnostics, bounded event-study estimates, and explicit limitations. "
        "It should not state that higher rates always raise inflation or that "
        "the Federal Reserve has stopped working.",
        "",
        "## Deck-Ready Empirical Slide",
        "",
        "Title: Debt-conditioned monetary transmission: bounded evidence.",
        "",
        "Message: high-frequency monetary-policy surprises are matched to "
        "official outcome panels and RateWall state variables; estimates are "
        "reported as limited event-study evidence, while stronger causal, "
        "pricing, and welfare claims remain gated.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _update_paper_support_report(
    path: Path,
    rows: list[dict[str, object]],
    *,
    report: Path | None,
    final_paper_support: Path | None,
) -> None:
    if not path.exists():
        return
    association_rows = [
        row for row in rows if row["artifact_layer"] == "empirical_estimate_bounded"
    ]
    event_rows = [
        row
        for row in rows
        if row["artifact_layer"] == "empirical_event_study_estimate"
    ]
    section = "\n".join(
        [
            "## Final Empirical Result Status",
            "",
            f"- Bounded admissible event-study estimate rows: {len(event_rows)}",
            f"- Bounded admissible shock/state result rows: {len(association_rows)}",
            "- Shock identification: SF Fed orthogonalized monetary surprises",
            "- Raw policy-rate-change identification: rejected",
            "- Full causal LP/proxy-SVAR transmission claims: not enabled",
            "- Pricing, holder allocation, tax, MPC, welfare, and incidence outputs: disabled",
            "",
            "These rows report reproducible source-backed outcome event-study "
            "estimates and state-dependent associations, while keeping "
            "descriptive accounting, scenario diagnostics, empirical estimates, "
            "pricing readiness, and welfare/incidence boundaries separate.",
            "",
        ]
    )
    if report is not None:
        section += f"See `{report}` for the generated empirical status note.\n"
    if final_paper_support is not None:
        section += f"See `{final_paper_support}` for final paper/deck support.\n"
    text = path.read_text(encoding="utf-8")
    marker = "\n## Final Empirical Result Status\n"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip() + "\n\n" + section
    else:
        text = text.rstrip() + "\n\n" + section
    path.write_text(text, encoding="utf-8")


def _first_at_or_after(
    values: list[tuple[date, Decimal]], target: date
) -> tuple[date, Decimal] | None:
    for value_date, value in values:
        if value_date >= target:
            return (value_date, value)
    return None


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days


def _outcome_change(
    pre: tuple[date, Decimal] | None,
    post: tuple[date, Decimal] | None,
    horizon_months: int,
    transform: str,
) -> float | None:
    if pre is None or post is None:
        return None
    pre_value = float(pre[1])
    post_value = float(post[1])
    if transform == "annualized_percent_change":
        if pre_value <= 0:
            return None
        return ((post_value / pre_value) - 1.0) * 100.0 * (12.0 / horizon_months)
    return post_value - pre_value


def _float(value: object) -> float | None:
    decimal = _decimal(value)
    return None if decimal is None else float(decimal)


def _ols_slope(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return 0.0, 0.0, 0.0
    x_mean = _mean(xs)
    y_mean = _mean(ys)
    sxx = sum((x - x_mean) ** 2 for x in xs)
    if sxx <= 0:
        return 0.0, 0.0, 0.0
    beta = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / sxx
    alpha = y_mean - beta * x_mean
    sse = sum((y - alpha - beta * x) ** 2 for x, y in zip(xs, ys))
    se = sqrt((sse / (len(xs) - 2)) / sxx) if len(xs) > 2 else 0.0
    t_stat = beta / se if se > 0 else 0.0
    return beta, se, t_stat


def _newey_west_slope_se(
    xs: list[float], ys: list[float], lag: int
) -> tuple[float, float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return 0.0, 0.0
    x_mean = _mean(xs)
    y_mean = _mean(ys)
    sxx = sum((x - x_mean) ** 2 for x in xs)
    if sxx <= 0:
        return 0.0, 0.0
    beta = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / sxx
    alpha = y_mean - beta * x_mean
    residuals = [y - alpha - beta * x for x, y in zip(xs, ys)]
    scores = [(x - x_mean) * residual for x, residual in zip(xs, residuals)]
    max_lag = min(lag, len(scores) - 1)
    long_run_variance = sum(score * score for score in scores)
    for lag_index in range(1, max_lag + 1):
        weight = 1.0 - lag_index / (max_lag + 1.0)
        covariance = sum(
            scores[index] * scores[index - lag_index]
            for index in range(lag_index, len(scores))
        )
        long_run_variance += 2.0 * weight * covariance
    se = sqrt(max(long_run_variance, 0.0)) / sxx
    t_stat = beta / se if se > 0 else 0.0
    return se, t_stat


def _response_unit(outcome: str) -> str:
    if outcome == "unemployment_rate":
        return "percentage_point_change_per_100bp_surprise"
    return "annualized_percent_change_per_100bp_surprise"


def _decimal(value: object) -> Decimal | None:
    if value in (None, "", ".", "null", "None"):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except Exception:
        return None


def _dated_values(records: list[dict[str, object]]) -> list[tuple[date, Decimal]]:
    values = []
    for record in records:
        value = _decimal(record.get("value"))
        if value is None:
            continue
        values.append((_date(str(record["date"])), value))
    return sorted(values)


def _dated_records(records: list[dict[str, object]], date_key: str) -> list[dict]:
    dated = [dict(record) for record in records if record.get(date_key)]
    return sorted(dated, key=lambda record: str(record[date_key]))


def _date(value: str) -> date:
    return date.fromisoformat(value[:10])


def _latest_at_or_before(
    values: list[tuple[date, Decimal]], target: date
) -> tuple[date, Decimal] | None:
    latest = None
    for value_date, value in values:
        if value_date > target:
            break
        latest = (value_date, value)
    return latest


def _latest_record_at_or_before(records: list[dict], target: date) -> dict | None:
    latest = None
    for record in records:
        record_date = _date(str(record["record_date"]))
        if record_date > target:
            break
        latest = record
    return latest


def _mspd_records_by_date(records: list[dict[str, object]]) -> dict[date, list[dict]]:
    by_date: dict[date, list[dict]] = {}
    for record in records:
        record_date = record.get("record_date")
        if not record_date:
            continue
        by_date.setdefault(_date(str(record_date)), []).append(dict(record))
    return by_date


def _latest_mspd_date_at_or_before(
    records_by_date: dict[date, list[dict]], target: date
) -> date | None:
    candidates = [record_date for record_date in records_by_date if record_date <= target]
    return max(candidates) if candidates else None


def _mspd_repricing_for_date(
    records: list[dict],
    as_of: date,
    *,
    debt: dict | None,
) -> dict[str, Decimal] | None:
    debt_bil = _debt_held_public_bil(debt)
    if debt_bil is None or debt_bil <= 0:
        return None
    amount_bil = Decimal("0")
    for record in records:
        if str(record.get("security_type_desc", "")).lower() != "marketable":
            continue
        security_class = str(record.get("security_class1_desc", "")).lower()
        if security_class.startswith("total"):
            continue
        amount = _mspd_amount_bil(record)
        if amount <= 0:
            continue
        maturity = record.get("maturity_date")
        if _is_floating_rate(record):
            months_to_repricing = Decimal("0")
        elif maturity in (None, "", "null"):
            continue
        else:
            days = (_date(str(maturity)) - as_of).days
            if days < 0:
                continue
            months_to_repricing = Decimal(days) / Decimal("30.4375")
        if months_to_repricing <= Decimal("12"):
            amount_bil += amount
    if amount_bil <= 0:
        return None
    return {
        "debt_repricing_1y_bil": amount_bil,
        "repricing_share_1y": min(amount_bil / debt_bil, Decimal("1")),
    }


def _is_floating_rate(record: dict) -> bool:
    description = " ".join(
        str(record.get(field, ""))
        for field in ("security_class1_desc", "security_class3_desc")
    ).lower()
    return "floating rate" in description


def _mspd_amount_bil(record: dict) -> Decimal:
    for field in ("current_month_outstanding_amt", "outstanding_amt"):
        value = _decimal(record.get(field))
        if value is not None:
            return value / Decimal("1000")
    issued = _decimal(record.get("issued_amt"))
    if issued is None:
        return Decimal("0")
    redeemed = _decimal(record.get("redeemed_amt")) or Decimal("0")
    return max(issued - redeemed, Decimal("0")) / Decimal("1000")


def _historical_fed_liabilities_gdp(
    *,
    reserves: tuple[date, Decimal] | None,
    on_rrp: tuple[date, Decimal] | None,
    gdp: tuple[date, Decimal] | None,
) -> Decimal | str:
    if reserves is None or gdp is None:
        return ""
    on_rrp_value = Decimal("0") if on_rrp is None else on_rrp[1]
    return ((reserves[1] + on_rrp_value) / Decimal("1000")) / gdp[1]


def _historical_public_liability_base(
    *,
    debt: dict | None,
    repricing: dict[str, Decimal] | None,
    reserves: tuple[date, Decimal] | None,
    on_rrp: tuple[date, Decimal] | None,
    gdp: tuple[date, Decimal] | None,
    latest_value: Decimal,
) -> Decimal:
    if repricing is None or reserves is None or gdp is None:
        return latest_value
    on_rrp_bil = Decimal("0") if on_rrp is None else on_rrp[1] / Decimal("1000")
    return (
        repricing["debt_repricing_1y_bil"]
        + reserves[1] / Decimal("1000")
        + on_rrp_bil
    ) / gdp[1]


def _debt_gdp(*, debt: dict | None, gdp: tuple[date, Decimal] | None) -> Decimal | str:
    debt_bil = _debt_held_public_bil(debt)
    if debt_bil is None or gdp is None:
        return ""
    return debt_bil / gdp[1]


def _debt_held_public_bil(debt: dict | None) -> Decimal | None:
    if debt is None:
        return None
    for field in ("debt_held_public_amt", "tot_pub_debt_out_amt"):
        value = _decimal(debt.get(field))
        if value is not None:
            return value / Decimal("1000000000")
    return None


def _asof(value: tuple[date, Decimal] | None) -> str:
    return "" if value is None else value[0].isoformat()


def _record_asof(value: dict | None) -> str:
    return "" if value is None else str(value.get("record_date", ""))


def _state_alignment_scope(
    *,
    reserves: tuple[date, Decimal] | None,
    on_rrp: tuple[date, Decimal] | None,
    gdp: tuple[date, Decimal] | None,
) -> str:
    if reserves is not None and on_rrp is not None and gdp is not None:
        return "historical_fred_reserves_rrp_gdp"
    if reserves is not None and gdp is not None:
        return "historical_fred_reserves_gdp_missing_rrp"
    return "insufficient_historical_fred_state"


def _treasury_repricing_scope(
    *, debt: dict | None, repricing: dict[str, Decimal] | None
) -> str:
    if debt is not None and repricing is not None:
        return "historical_debt_to_penny_and_mspd_table_3_proxy"
    if debt is not None:
        return "historical_debt_latest_mspd_table_3_proxy"
    return "latest_mspd_table_3_proxy"
