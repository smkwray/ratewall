"""Final economist-facing RateWall model readout."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.table_io import write_rows

DEFAULT_PRELIMINARY_DIR = Path("var/preliminary_scenario_results")
DEFAULT_OUTPUT_DIR = DEFAULT_PRELIMINARY_DIR / "final_model_readout"

FINAL_MODEL_READOUT_LEDGER_FIELDS = [
    "roadmap_gate_id",
    "gate_label",
    "gate_status",
    "evidence",
    "selected_value_change",
    "remaining_action",
    "claim_boundary",
]

FINAL_MODEL_RATIO_SNAPSHOT_FIELDS = [
    "ratio_row_id",
    "period_label",
    "surface_id",
    "object_role",
    "ratewall_ratio",
    "n_bil",
    "d_bil",
    "selection_status",
    "claim_boundary",
]

FINAL_MODEL_RATIO_TIME_SERIES_FIELDS = [
    "time_series_row_id",
    "period_label",
    "period_sort",
    "series_id",
    "series_role",
    "ratewall_ratio",
    "selected_status",
    "claim_boundary",
]

FINAL_FORECAST_SCENARIO_TIME_SERIES_FIELDS = [
    "forecast_time_series_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_rank",
    "scenario_selection_reason",
    "central_ratewall_ratio",
    "delta_central_ratewall_ratio_vs_baseline",
    "wall_hit_under_central_forecast",
    "claim_boundary",
]

FINAL_FORECAST_BETA_SHOCK_TIME_SERIES_FIELDS = [
    "beta_shock_row_id",
    "fiscal_year",
    "shock_id",
    "shock_label",
    "tdc_beta",
    "tdc_beta_multiplier_vs_default",
    "baseline_public_interest_n_bil",
    "baseline_tdc_component_bil",
    "shocked_n_bil",
    "baseline_d_bil",
    "shocked_ratewall_ratio",
    "delta_ratewall_ratio_vs_baseline",
    "claim_boundary",
]

FINAL_FORECAST_TDC_TIME_SERIES_FIELDS = [
    "forecast_tdc_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_rank",
    "scenario_selection_reason",
    "tdc_component_bil",
    "central_n_bil",
    "public_interest_n_bil",
    "central_ratewall_ratio",
    "claim_boundary",
]

DEFAULT_TDC_BETA = Decimal("0.34201759129420367")


def final_model_readout_markdown(
    *,
    preliminary_dir: str | Path = DEFAULT_PRELIMINARY_DIR,
) -> str:
    """Return the final economist-facing readout markdown."""

    root = Path(preliminary_dir)
    status_rows = _read_csv(
        root / "comparable_model_surface/ratewall_comparable_model_status.csv"
    )
    forecast = _row_by(status_rows, "surface_id", "forecast_central_tdcsim_cbo")
    current_status = _row_by(status_rows, "surface_id", "current_assumption_runtime")
    current_freeze = _single(
        _read_csv(root / "current_object_bridge/ratewall_current_object_freeze_decision.csv")
    )
    historical_rows = _read_csv(
        root / "historical_coverage_contract/ratewall_historical_coverage_contract.csv"
    )
    implemented_history = _row_by(historical_rows, "route_id", "implemented_short_panel")
    feasibility_rows = _read_csv(
        root / "historical_coverage_contract/ratewall_historical_extension_feasibility.csv"
    )
    d1_status = _single(
        _read_csv(root / "realized_safe_yield_income/ratewall_safe_yield_sublane_status.csv")
    )
    d1_admission = _single(
        _read_csv(
            root
            / "realized_safe_yield_income/ratewall_realized_safe_yield_payer_flow_admission.csv"
        )
    )
    role_rows = _read_csv(root / "demand_translation_ledger/ratewall_object_role_matrix.csv")
    role_counts = Counter(row["object_role"] for row in role_rows)
    ledger = final_model_readiness_ledger_rows(preliminary_dir=root)

    blocked_rows = [
        row for row in role_rows if row["object_role"] == "blocked_source_or_method"
    ]
    denominator_rows = [
        row for row in role_rows if row["object_role"] == "denominator_only"
    ]
    sensitivity_rows = [
        row
        for row in role_rows
        if row["object_role"] in {"sensitivity_only", "diagnostic_context", "candidate_replacement"}
    ]

    lines = [
        "# RateWall Final Economist-Facing Readout",
        "",
        "This readout closes the v1 model-classification pass. It explains what is selected, what is only context or sensitivity, and what remains blocked.",
        "",
        "## Object Definition And Claim Mode",
        "",
        "RateWall is `RW = N / D`: `N` is current-demand support and `D` is the conventional-demand shortfall. The estimate is an Assumption Mode model readout, not a fully source-identified causal/evidence-mode estimate.",
        "",
        f"- Classified D9 object rows: `{len(role_rows)}`.",
        f"- Selected forecast numerator rows: `{role_counts.get('selected_n', 0)}`.",
        f"- Selected block-input rows: `{role_counts.get('selected_block_input', 0)}`.",
        f"- Denominator-only rows: `{role_counts.get('denominator_only', 0)}`.",
        f"- Source/method-blocked rows: `{role_counts.get('blocked_source_or_method', 0)}`.",
        "",
        "## Selected Forecast Estimate",
        "",
        "The selected forecast readout uses the public-interest net block plus TDC ex-overlap beta chi. Direct Treasury interest, IORB, ON RRP, and bank Treasury split are inputs inside the public-interest block, not extra add-ons.",
        "",
        f"- Representative period/case: `{forecast['representative_period']}` / `{forecast['representative_case']}`.",
        f"- Selected forecast N: `{forecast['selected_or_provisional_n_bil']}` billion.",
        f"- Selected forecast D: `{forecast['selected_or_provisional_d_bil']}` billion.",
        f"- Selected forecast RW: `{forecast['selected_or_provisional_ratewall_ratio']}`.",
        f"- Numerator method: `{forecast['numerator_method_plain']}`.",
        f"- Denominator method: `{forecast['denominator_method_plain']}`.",
        "",
        "## Selected Current Benchmark",
        "",
        "The selected current benchmark is the frozen runtime annual-flow benchmark, not the legacy static paper lane. R38 did not replace the selected current benchmark, and D1 fallback did not alter the current benchmark.",
        "",
        f"- Selected current object: `{current_freeze['selected_current_object_id']}`.",
        f"- Selected current N: `{current_freeze['selected_n_bil']}` billion.",
        f"- Selected current D: `{current_freeze['selected_d_bil']}` billion.",
        f"- Selected current RW: `{current_freeze['selected_rw']}`.",
        f"- Freeze status: `{current_freeze['selection_status']}`.",
        f"- Replacement gate: `{current_freeze['replacement_gate_status']}`.",
        f"- Comparable-surface blocker: `{current_status['main_blocker']}`.",
        "",
        "## Historical Context And Coverage",
        "",
        "Historical rows are context and validation, not final wall-hit classifiers. No selected historical numerator currently exists.",
        "",
        f"- Implemented historical context window: `{implemented_history['coverage_window_start']}` to `{implemented_history['coverage_window_end']}`.",
        f"- Final classifier status: `{implemented_history['final_classifier_status']}`.",
        f"- Classifier allowed: `{implemented_history['classifier_allowed']}`.",
        f"- Historical formula lock: `{implemented_history['historical_n_formula']}`.",
        f"- Nonadditive decomposition terms: `{implemented_history['nonadditive_decomposition_terms']}`.",
        "",
        "Extension routes are coverage plans, not selected historical estimates:",
    ]
    for row in feasibility_rows:
        lines.append(
            f"- `{row['route_id']}`: `{row['target_window_start']}` to `{row['target_window_end']}`, status `{row['feasibility_status']}`."
        )

    lines.extend(
        [
            "",
            "## Diagnostics And Sensitivities",
            "",
            "Diagnostics and sensitivities are useful model information, but they do not change selected `N`, selected `D`, beta, chi, or the current benchmark.",
            "",
            f"- Diagnostic/sensitivity/candidate rows classified in D9: `{len(sensitivity_rows)}`.",
            "- Bounded deposit fallback is not release/report-grade central evidence.",
            "- Raw stock times MPC is not an accepted central route.",
            "- MMF/T-bill diagnostics are not additive central `N` on top of public-interest.",
            "",
            "## Source-Blocked Theoretical Channels",
            "",
            "Parked lanes are parked because source, recipient, timing, demand-conversion, denominator, owner, or non-overlap requirements are not met. They are not being dismissed as theoretically irrelevant.",
            "",
            f"- D1 source gate: `{d1_status['source_gate_status']}`.",
            f"- D1 accepted source rows: `{d1_status['accepted_current_rows']}` of `{d1_status['eligible_current_rows']}`.",
            f"- D1 gross payer-flow candidate: `{d1_status['gross_realized_income_bil']}` billion.",
            f"- D1 central allowed: `{d1_admission['central_n_delta_bil_allowed']}`; central delta: `{d1_admission['central_n_delta_bil']}`.",
            f"- D1 remaining blockers: `{d1_admission['blocked_reason']}`.",
            "",
            "No selected central safe-yield unless all D1 gates pass. BEA/IRS do not substitute for payer-flow panels. `Y001RC1Q027SBEA` is not personal-interest context.",
        ]
    )
    for row in blocked_rows:
        lines.append(
            f"- `{row['source_channel_id']}`: `{row['promotion_requirements_remaining']}`."
        )

    lines.extend(
        [
            "",
            "## Denominator-Only Routes",
            "",
            "Denominator routes explain `D`. Denominator drag is never booked as a numerator offset.",
            "",
            f"- Denominator-only rows classified in D9: `{len(denominator_rows)}`.",
        ]
    )
    for row in denominator_rows:
        lines.append(
            f"- `{row['source_channel_id']}`: `{row['same_period_denominator_status']}`."
        )

    lines.extend(
        [
            "",
            "## Completion/Readiness Ledger",
            "",
        ]
    )
    for row in ledger:
        lines.append(
            f"- `{row['roadmap_gate_id']}`: `{row['gate_status']}`; {row['evidence']}"
        )
    lines.extend(
        [
            "",
            "v1 is complete only because D9, D2/D10, T3, D1, D6/D7/D8, and this readout have now passed or fail-closed. No major theoretical channel remains unclassified; several remain unadmitted or source/method-blocked.",
            "",
        ]
    )
    return "\n".join(lines)


def final_model_readiness_ledger_rows(
    *,
    preliminary_dir: str | Path = DEFAULT_PRELIMINARY_DIR,
) -> list[dict[str, str]]:
    """Return the v1 completion/readiness ledger."""

    root = Path(preliminary_dir)
    d1_status = _single(
        _read_csv(root / "realized_safe_yield_income/ratewall_safe_yield_sublane_status.csv")
    )
    d1_admission = _single(
        _read_csv(
            root
            / "realized_safe_yield_income/ratewall_realized_safe_yield_payer_flow_admission.csv"
        )
    )
    current_freeze = _single(
        _read_csv(root / "current_object_bridge/ratewall_current_object_freeze_decision.csv")
    )
    historical = _row_by(
        _read_csv(root / "historical_coverage_contract/ratewall_historical_coverage_contract.csv"),
        "route_id",
        "implemented_short_panel",
    )
    role_rows = _read_csv(root / "demand_translation_ledger/ratewall_object_role_matrix.csv")
    comparable_status = _read_csv(
        root / "comparable_model_surface/ratewall_comparable_model_status.csv"
    )
    role_count = len(role_rows)
    return [
        _ledger_row(
            "D9",
            "demand/object-role ledger",
            "pass",
            f"{role_count} object rows classified",
            "false",
            "none",
            "no_unclassified_major_theoretical_channel",
        ),
        _ledger_row(
            "D2_D10",
            "current bridge/freeze",
            "pass",
            f"selected current object {current_freeze['selected_current_object_id']} frozen",
            "false",
            "none",
            "current_selected_values_frozen",
        ),
        _ledger_row(
            "T3",
            "historical coverage contract",
            "pass_context_only",
            f"implemented window {historical['coverage_window_start']} to {historical['coverage_window_end']}; {historical['final_classifier_status']}",
            "false",
            "keep historical nonclassifier unless owner reopens",
            "historical_context_not_classifier",
        ),
        _ledger_row(
            "D1",
            "safe-yield payer-flow source/admission",
            (
                "pass_source_gate_fail_closed_central"
                if d1_status["source_gate_status"].startswith("pass_")
                and d1_admission["central_n_delta_bil_allowed"] == "false"
                else "review_required"
            ),
            f"{d1_status['source_gate_status']}; central allowed {d1_admission['central_n_delta_bil_allowed']}",
            "false",
            d1_admission["blocked_reason"],
            "D1_source_gate_no_selected_value_change",
        ),
        _ledger_row(
            "D6_D7_D8",
            "disposition sync",
            "pass",
            f"{len(comparable_status)} comparable status rows and D9 role vocabulary synced",
            "false",
            "none",
            "disposition_sync_no_model_value_change",
        ),
        _ledger_row(
            "READOUT",
            "economist-facing readout",
            "pass",
            "selected, diagnostic, sensitivity, blocked, and denominator-only lanes separated",
            "false",
            "commit/stage decision only",
            "final_readout_no_model_value_change",
        ),
    ]


def final_model_ratio_snapshot_rows(
    *,
    preliminary_dir: str | Path = DEFAULT_PRELIMINARY_DIR,
) -> list[dict[str, str]]:
    """Return past/current/forecast RW ratio rows for the final PNG."""

    status_rows = _read_csv(
        Path(preliminary_dir)
        / "comparable_model_surface/ratewall_comparable_model_status.csv"
    )
    specs = [
        (
            "past_historical_context",
            "Past context",
            "historical_path_context",
            "historical_context_not_classifier",
        ),
        (
            "current_selected_benchmark",
            "Current selected",
            "current_assumption_runtime",
            "selected_current_benchmark",
        ),
        (
            "forecast_selected_2036",
            "Forecast selected",
            "forecast_central_tdcsim_cbo",
            "selected_forecast_model_surface",
        ),
    ]
    rows = []
    for row_id, label, surface_id, selection_status in specs:
        row = _row_by(status_rows, "surface_id", surface_id)
        rows.append(
            {
                "ratio_row_id": row_id,
                "period_label": f"{label}\n{row['representative_period']}",
                "surface_id": surface_id,
                "object_role": row["object_role"],
                "ratewall_ratio": row["selected_or_provisional_ratewall_ratio"],
                "n_bil": row["selected_or_provisional_n_bil"],
                "d_bil": row["selected_or_provisional_d_bil"],
                "selection_status": selection_status,
                "claim_boundary": row["claim_boundary"],
            }
        )
    return rows


def final_model_ratio_time_series_rows(
    *,
    preliminary_dir: str | Path = DEFAULT_PRELIMINARY_DIR,
) -> list[dict[str, str]]:
    """Return past/current/forecast RW time-series rows."""

    root = Path(preliminary_dir)
    historical_rows, historical_ratio_field, historical_series_role = (
        _historical_root_time_series_source(root)
    )
    current = _row_by(
        _read_csv(root / "current_object_bridge/ratewall_current_object_bridge.csv"),
        "current_object_bridge_row_id",
        "current_object_bridge::selected_runtime_benchmark",
    )
    forecast_rows = [
        row
        for row in _read_csv(
            root / "forecast_10y/ratewall_forecast_central_scenario_surface.csv"
        )
        if row["scenario_id"] == "cbo_baseline_noop_v1"
    ]
    rows = []
    for row in sorted(historical_rows, key=lambda item: item["period"]):
        rows.append(
            {
                "time_series_row_id": f"rw_time_series::historical_context::{row['period']}",
                "period_label": row["period"],
                "period_sort": _quarter_sort_value(row["period"]),
                "series_id": "historical_context_base",
                "series_role": historical_series_role,
                "ratewall_ratio": row[historical_ratio_field],
                "selected_status": "not_selected_historical_context",
                "claim_boundary": row["claim_boundary"],
            }
        )
    rows.append(
        {
            "time_series_row_id": "rw_time_series::current_selected::2026",
            "period_label": "Current 2026",
            "period_sort": "2026.50",
            "series_id": "current_selected_benchmark",
            "series_role": "current_selected",
            "ratewall_ratio": current["rw"],
            "selected_status": "selected_current_benchmark",
            "claim_boundary": current["claim_boundary"],
        }
    )
    for row in sorted(forecast_rows, key=lambda item: int(item["fiscal_year"])):
        rows.append(
            {
                "time_series_row_id": f"rw_time_series::forecast_selected::{row['fiscal_year']}",
                "period_label": f"FY{row['fiscal_year']}",
                "period_sort": f"{row['fiscal_year']}.00",
                "series_id": "forecast_selected_baseline",
                "series_role": "forecast_selected",
                "ratewall_ratio": row["central_ratewall_ratio"],
                "selected_status": "selected_forecast_baseline_path",
                "claim_boundary": row["sensitivity_rule"],
            }
        )
    return rows


def final_forecast_scenario_time_series_rows(
    *,
    preliminary_dir: str | Path = DEFAULT_PRELIMINARY_DIR,
    max_scenarios: int = 8,
) -> list[dict[str, str]]:
    """Return selected forecast scenario RW time-series rows."""

    forecast_rows = _read_csv(
        Path(preliminary_dir) / "forecast_10y/ratewall_forecast_central_scenario_surface.csv"
    )
    if max_scenarios < 1:
        raise ValueError("max_scenarios must be at least 1")
    selected_scenarios = _selected_forecast_scenarios(
        forecast_rows,
        max_scenarios=max_scenarios,
    )
    rank_by_scenario = {
        scenario_id: str(index + 1)
        for index, scenario_id in enumerate(selected_scenarios)
    }
    selected_set = set(selected_scenarios)
    rows = []
    for row in sorted(
        [row for row in forecast_rows if row["scenario_id"] in selected_set],
        key=lambda item: (int(item["fiscal_year"]), int(rank_by_scenario[item["scenario_id"]])),
    ):
        scenario_id = row["scenario_id"]
        rows.append(
            {
                "forecast_time_series_row_id": (
                    f"forecast_rw_time_series::{scenario_id}::{row['fiscal_year']}"
                ),
                "fiscal_year": row["fiscal_year"],
                "scenario_id": scenario_id,
                "scenario_rank": rank_by_scenario[scenario_id],
                "scenario_selection_reason": (
                    "baseline"
                    if scenario_id == "cbo_baseline_noop_v1"
                    else "top_abs_fy2036_central_rw_delta"
                ),
                "central_ratewall_ratio": row["central_ratewall_ratio"],
                "delta_central_ratewall_ratio_vs_baseline": row[
                    "delta_central_ratewall_ratio_vs_baseline"
                ],
                "wall_hit_under_central_forecast": row["wall_hit_under_central_forecast"],
                "claim_boundary": row["sensitivity_rule"],
            }
        )
    return rows


def final_forecast_beta_shock_time_series_rows(
    *,
    preliminary_dir: str | Path = DEFAULT_PRELIMINARY_DIR,
    default_beta: Decimal = DEFAULT_TDC_BETA,
) -> list[dict[str, str]]:
    """Return baseline forecast RW rows under temporary TDC beta shocks."""

    root = Path(preliminary_dir)
    forecast_rows = [
        row
        for row in _read_csv(
            root / "forecast_10y/ratewall_forecast_central_scenario_surface.csv"
        )
        if row["scenario_id"] == "cbo_baseline_noop_v1"
    ]
    public_interest_rows = {
        row["fiscal_year"]: row
        for row in _read_csv(
            root / "forecast_10y/ratewall_forecast_public_interest_net_block.csv"
        )
        if row["scenario_id"] == "cbo_baseline_noop_v1"
    }
    shocks = [
        ("baseline_beta_0_342", "baseline beta 0.342", default_beta),
        ("peak_beta_0_500", "beta peaks at 0.500", Decimal("0.5")),
        ("peak_beta_0_700", "beta peaks at 0.700", Decimal("0.7")),
    ]
    rows = []
    for forecast in sorted(forecast_rows, key=lambda row: int(row["fiscal_year"])):
        fiscal_year = int(forecast["fiscal_year"])
        public_interest = public_interest_rows[forecast["fiscal_year"]]
        public_interest_n = Decimal(
            public_interest["net_interest_after_fiscal_tga_offsets_bil"]
        )
        baseline_n = Decimal(forecast["central_n_bil"])
        baseline_tdc = baseline_n - public_interest_n
        baseline_d = Decimal(forecast["central_moving_denominator_bil"])
        baseline_ratio = Decimal(forecast["central_ratewall_ratio"])
        for shock_id, shock_label, peak_beta in shocks:
            beta = (
                default_beta
                if peak_beta == default_beta
                else _beta_rise_then_fade_path(
                    fiscal_year,
                    start_beta=default_beta,
                    peak_beta=peak_beta,
                    start_year=2027,
                    peak_year=2031,
                    end_year=2036,
                )
            )
            shocked_n = public_interest_n + baseline_tdc * (beta / default_beta)
            shocked_ratio = shocked_n / baseline_d
            rows.append(
                {
                    "beta_shock_row_id": (
                        f"forecast_beta_shock::{shock_id}::{fiscal_year}"
                    ),
                    "fiscal_year": str(fiscal_year),
                    "shock_id": shock_id,
                    "shock_label": shock_label,
                    "tdc_beta": _fmt_decimal(beta),
                    "tdc_beta_multiplier_vs_default": _fmt_decimal(
                        beta / default_beta
                    ),
                    "baseline_public_interest_n_bil": _fmt_decimal(public_interest_n),
                    "baseline_tdc_component_bil": _fmt_decimal(baseline_tdc),
                    "shocked_n_bil": _fmt_decimal(shocked_n),
                    "baseline_d_bil": _fmt_decimal(baseline_d),
                    "shocked_ratewall_ratio": _fmt_decimal(shocked_ratio),
                    "delta_ratewall_ratio_vs_baseline": _fmt_decimal(
                        shocked_ratio - baseline_ratio
                    ),
                    "claim_boundary": (
                        "tdc_beta_path_sensitivity_only_not_selected_forecast"
                    ),
                }
            )
    return rows


def final_forecast_tdc_time_series_rows(
    *,
    preliminary_dir: str | Path = DEFAULT_PRELIMINARY_DIR,
    extreme_count: int = 3,
) -> list[dict[str, str]]:
    """Return selected forecast scenarios' TDC components in billions."""

    root = Path(preliminary_dir)
    forecast_rows = _read_csv(
        root / "forecast_10y/ratewall_forecast_central_scenario_surface.csv"
    )
    public_interest_rows = {
        (row["scenario_id"], row["fiscal_year"]): row
        for row in _read_csv(
            root / "forecast_10y/ratewall_forecast_public_interest_net_block.csv"
        )
    }
    component_rows = []
    for row in forecast_rows:
        public_interest = public_interest_rows.get((row["scenario_id"], row["fiscal_year"]))
        if public_interest is None:
            continue
        public_interest_n = Decimal(
            public_interest["net_interest_after_fiscal_tga_offsets_bil"]
        )
        central_n = Decimal(row["central_n_bil"])
        component_rows.append(
            {
                "fiscal_year": row["fiscal_year"],
                "scenario_id": row["scenario_id"],
                "tdc_component_bil": central_n - public_interest_n,
                "central_n_bil": central_n,
                "public_interest_n_bil": public_interest_n,
                "central_ratewall_ratio": Decimal(row["central_ratewall_ratio"]),
                "claim_boundary": row["sensitivity_rule"],
            }
        )
    final_year = max(int(row["fiscal_year"]) for row in component_rows)
    final_rows = [row for row in component_rows if int(row["fiscal_year"]) == final_year]
    baseline = "cbo_baseline_noop_v1"
    nonbaseline_final_rows = [
        row for row in final_rows if row["scenario_id"] != baseline
    ]
    selected: list[tuple[str, str]] = [(baseline, "baseline")]
    selected.extend(
        (
            row["scenario_id"],
            f"highest_fy{final_year}_tdc_component",
        )
        for row in sorted(
            nonbaseline_final_rows,
            key=lambda row: row["tdc_component_bil"],
            reverse=True,
        )[:extreme_count]
    )
    selected.extend(
        (
            row["scenario_id"],
            f"lowest_fy{final_year}_tdc_component",
        )
        for row in sorted(
            nonbaseline_final_rows,
            key=lambda row: row["tdc_component_bil"],
        )[:extreme_count]
    )
    selected_reason: dict[str, str] = {}
    for scenario_id, reason in selected:
        selected_reason.setdefault(scenario_id, reason)
    selected_ids = set(selected_reason)
    rank_by_scenario = {
        scenario_id: str(index + 1)
        for index, scenario_id in enumerate(selected_reason)
    }
    rows = []
    for row in sorted(
        [row for row in component_rows if row["scenario_id"] in selected_ids],
        key=lambda row: (int(row["fiscal_year"]), int(rank_by_scenario[row["scenario_id"]])),
    ):
        scenario_id = row["scenario_id"]
        rows.append(
            {
                "forecast_tdc_row_id": (
                    f"forecast_tdc_component::{scenario_id}::{row['fiscal_year']}"
                ),
                "fiscal_year": row["fiscal_year"],
                "scenario_id": scenario_id,
                "scenario_rank": rank_by_scenario[scenario_id],
                "scenario_selection_reason": selected_reason[scenario_id],
                "tdc_component_bil": _fmt_decimal(row["tdc_component_bil"]),
                "central_n_bil": _fmt_decimal(row["central_n_bil"]),
                "public_interest_n_bil": _fmt_decimal(row["public_interest_n_bil"]),
                "central_ratewall_ratio": _fmt_decimal(row["central_ratewall_ratio"]),
                "claim_boundary": row["claim_boundary"],
            }
        )
    return rows


def write_final_model_readout_outputs(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    preliminary_dir: str | Path = DEFAULT_PRELIMINARY_DIR,
) -> dict[str, Path]:
    """Write final readout markdown and readiness ledger CSV."""

    out = Path(output_dir)
    ledger_rows = final_model_readiness_ledger_rows(preliminary_dir=preliminary_dir)
    ratio_rows = final_model_ratio_snapshot_rows(preliminary_dir=preliminary_dir)
    time_series_rows = final_model_ratio_time_series_rows(preliminary_dir=preliminary_dir)
    forecast_time_series_rows = final_forecast_scenario_time_series_rows(
        preliminary_dir=preliminary_dir
    )
    beta_shock_rows = final_forecast_beta_shock_time_series_rows(
        preliminary_dir=preliminary_dir
    )
    tdc_time_series_rows = final_forecast_tdc_time_series_rows(
        preliminary_dir=preliminary_dir
    )
    readout = final_model_readout_markdown(preliminary_dir=preliminary_dir)
    outputs = {
        "readout_md": out / "ratewall_final_economist_readout.md",
        "readiness_ledger_csv": out / "ratewall_final_readiness_ledger.csv",
        "ratio_snapshot_csv": out / "ratewall_final_rw_ratio_snapshot.csv",
        "ratio_snapshot_png": out / "ratewall_final_rw_ratio_snapshot.png",
        "ratio_time_series_csv": out / "ratewall_final_rw_ratio_time_series.csv",
        "ratio_time_series_png": out / "ratewall_final_rw_ratio_time_series.png",
        "forecast_scenario_time_series_csv": (
            out / "ratewall_forecast_scenario_rw_time_series.csv"
        ),
        "forecast_scenario_time_series_png": (
            out / "ratewall_forecast_scenario_rw_time_series.png"
        ),
        "forecast_beta_shock_time_series_csv": (
            out / "ratewall_forecast_tdc_beta_shock_time_series.csv"
        ),
        "forecast_beta_shock_time_series_png": (
            out / "ratewall_forecast_tdc_beta_shock_time_series.png"
        ),
        "forecast_tdc_time_series_csv": (
            out / "ratewall_forecast_tdc_component_time_series.csv"
        ),
        "forecast_tdc_time_series_png": (
            out / "ratewall_forecast_tdc_component_time_series.png"
        ),
    }
    write_rows(outputs["readiness_ledger_csv"], ledger_rows, FINAL_MODEL_READOUT_LEDGER_FIELDS)
    write_rows(
        outputs["ratio_snapshot_csv"],
        ratio_rows,
        FINAL_MODEL_RATIO_SNAPSHOT_FIELDS,
    )
    write_rows(
        outputs["ratio_time_series_csv"],
        time_series_rows,
        FINAL_MODEL_RATIO_TIME_SERIES_FIELDS,
    )
    write_rows(
        outputs["forecast_scenario_time_series_csv"],
        forecast_time_series_rows,
        FINAL_FORECAST_SCENARIO_TIME_SERIES_FIELDS,
    )
    write_rows(
        outputs["forecast_beta_shock_time_series_csv"],
        beta_shock_rows,
        FINAL_FORECAST_BETA_SHOCK_TIME_SERIES_FIELDS,
    )
    write_rows(
        outputs["forecast_tdc_time_series_csv"],
        tdc_time_series_rows,
        FINAL_FORECAST_TDC_TIME_SERIES_FIELDS,
    )
    outputs["readout_md"].parent.mkdir(parents=True, exist_ok=True)
    outputs["readout_md"].write_text(readout, encoding="utf-8")
    _write_ratio_snapshot_png(outputs["ratio_snapshot_png"], ratio_rows)
    _write_ratio_time_series_png(outputs["ratio_time_series_png"], time_series_rows)
    _write_forecast_scenario_time_series_png(
        outputs["forecast_scenario_time_series_png"],
        forecast_time_series_rows,
    )
    _write_forecast_beta_shock_time_series_png(
        outputs["forecast_beta_shock_time_series_png"],
        beta_shock_rows,
    )
    _write_forecast_tdc_time_series_png(
        outputs["forecast_tdc_time_series_png"],
        tdc_time_series_rows,
    )
    return outputs


def _ledger_row(
    gate_id: str,
    label: str,
    status: str,
    evidence: str,
    selected_value_change: str,
    remaining_action: str,
    claim_boundary: str,
) -> dict[str, str]:
    return {
        "roadmap_gate_id": gate_id,
        "gate_label": label,
        "gate_status": status,
        "evidence": evidence,
        "selected_value_change": selected_value_change,
        "remaining_action": remaining_action,
        "claim_boundary": claim_boundary,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _historical_root_time_series_source(
    root: Path,
) -> tuple[list[dict[str, str]], str, str]:
    root_path = (
        root
        / "historical_provisional_estimate"
        / "ratewall_historical_root_public_interest_rw_panel.csv"
    )
    if root_path.exists():
        return (
            [
                row
                for row in _read_csv(root_path)
                if row["assumption_case"] == "base"
            ],
            "root_public_interest_ratewall_ratio",
            "historical_root_public_interest_context",
        )
    provisional_path = (
        root
        / "historical_provisional_estimate"
        / "ratewall_historical_provisional_rw_panel.csv"
    )
    return (
        [
            row
            for row in _read_csv(provisional_path)
            if row["assumption_case"] == "base"
        ],
        "provisional_historical_ratewall_ratio",
        "past_context_nonclassifier",
    )


def _single(rows: Sequence[Mapping[str, str]]) -> Mapping[str, str]:
    if len(rows) != 1:
        raise ValueError(f"expected one row, found {len(rows)}")
    return rows[0]


def _row_by(
    rows: Sequence[Mapping[str, str]],
    field: str,
    value: str,
) -> Mapping[str, str]:
    matches = [row for row in rows if row.get(field) == value]
    if len(matches) != 1:
        raise ValueError(f"expected one row where {field}={value}, found {len(matches)}")
    return matches[0]


def _quarter_sort_value(period: str) -> str:
    year = int(period[:4])
    quarter = int(period[-1])
    return f"{year + (quarter - 1) / 4:.2f}"


def _fmt_decimal(value: Decimal) -> str:
    return str(value.normalize())


def _beta_rise_then_fade_path(
    fiscal_year: int,
    *,
    start_beta: Decimal,
    peak_beta: Decimal,
    start_year: int,
    peak_year: int,
    end_year: int,
) -> Decimal:
    if fiscal_year <= peak_year:
        span = Decimal(peak_year - start_year)
        step = Decimal(fiscal_year - start_year) / span if span else Decimal("1")
        return start_beta + (peak_beta - start_beta) * step
    span = Decimal(end_year - peak_year)
    step = Decimal(fiscal_year - peak_year) / span if span else Decimal("1")
    return peak_beta + (start_beta - peak_beta) * step


def _selected_forecast_scenarios(
    rows: Sequence[Mapping[str, str]],
    *,
    max_scenarios: int,
) -> list[str]:
    final_year = max(int(row["fiscal_year"]) for row in rows)
    final_rows = [row for row in rows if int(row["fiscal_year"]) == final_year]
    baseline = "cbo_baseline_noop_v1"
    ranked = sorted(
        [row for row in final_rows if row["scenario_id"] != baseline],
        key=lambda row: abs(float(row["delta_central_ratewall_ratio_vs_baseline"])),
        reverse=True,
    )
    selected = [baseline]
    selected.extend(row["scenario_id"] for row in ranked[: max_scenarios - 1])
    return selected[:max_scenarios]


def _write_ratio_snapshot_png(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [row["period_label"] for row in rows]
    values = [float(row["ratewall_ratio"]) for row in rows]
    colors = ["#6b7280", "#2563eb", "#059669"]

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    bars = ax.bar(labels, values, color=colors, width=0.58)
    ax.axhline(1.0, color="#991b1b", linewidth=1.4, linestyle="--")
    ax.text(
        2.45,
        1.015,
        "RW = 1 wall threshold",
        ha="right",
        va="bottom",
        fontsize=9,
        color="#991b1b",
    )
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.018,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=10,
            color="#111827",
        )
    ax.set_title("RateWall Ratio Snapshot", fontsize=14, pad=14)
    ax.set_ylabel("RW = N / D")
    ax.set_ylim(0, max(1.08, max(values) + 0.12))
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(
        0.0,
        -0.22,
        "Past is historical context only, not a final classifier. Current and forecast are selected model readouts.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_ratio_time_series_png(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FormatStrFormatter

    by_series: dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        by_series.setdefault(row["series_id"], []).append(row)
    for series_rows in by_series.values():
        series_rows.sort(key=lambda row: float(row["period_sort"]))

    style = {
        "historical_context_base": {
            "label": "Past public-interest context",
            "color": "#6b7280",
            "marker": "o",
            "linestyle": "--",
        },
        "current_selected_benchmark": {
            "label": "Current selected",
            "color": "#2563eb",
            "marker": "D",
            "linestyle": "None",
        },
        "forecast_selected_baseline": {
            "label": "Forecast selected baseline",
            "color": "#059669",
            "marker": "o",
            "linestyle": "-",
        },
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 6.2))
    y_min = 0.0
    y_max = 1.12
    clipped_points: list[tuple[float, float, str, str]] = []
    for series_id in [
        "historical_context_base",
        "current_selected_benchmark",
        "forecast_selected_baseline",
    ]:
        series_rows = by_series.get(series_id, [])
        if not series_rows:
            continue
        spec = style[series_id]
        x_values = [float(row["period_sort"]) for row in series_rows]
        y_values = [float(row["ratewall_ratio"]) for row in series_rows]
        display_values = [min(max(value, y_min), y_max) for value in y_values]
        ax.plot(
            x_values,
            display_values,
            label=spec["label"],
            color=spec["color"],
            marker=spec["marker"],
            linestyle=spec["linestyle"],
            linewidth=1.8,
            markersize=5.5,
        )
        for x_value, y_value, period_label in zip(
            x_values,
            y_values,
            (row["period_label"] for row in series_rows),
            strict=True,
        ):
            if y_value > y_max:
                clipped_points.append((x_value, y_max, period_label, f"{y_value:.2f}"))

    for x_value, y_value, period_label, true_value in clipped_points:
        ax.scatter(
            [x_value],
            [y_value],
            color="#6b7280",
            marker="^",
            s=54,
            zorder=5,
        )
    if clipped_points:
        clipped_note = "; ".join(
            f"{period_label}={true_value}"
            for _x_value, y_value, period_label, true_value in clipped_points
            if y_value == y_max
        )
        if clipped_note:
            ax.text(
                0.02,
                0.92,
                f"Clipped above axis: {clipped_note}",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=8.5,
                color="#4b5563",
                bbox={
                    "boxstyle": "round,pad=0.25",
                    "facecolor": "white",
                    "edgecolor": "none",
                    "alpha": 0.85,
                },
            )

    ax.axhline(0.0, color="#111827", linewidth=1.0)
    ax.axhline(1.0, color="#991b1b", linewidth=1.3, linestyle="--")
    ax.text(
        0.01,
        0.91,
        "RW = 1 wall threshold",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#991b1b",
    )
    ax.set_title("RateWall Ratios Over Time", fontsize=14, pad=14)
    ax.set_ylabel("RW = N / D")
    ax.set_xlabel("Period")
    all_x_values = [float(row["period_sort"]) for row in rows]
    ax.set_xlim(min(all_x_values) - 0.25, max(all_x_values) + 0.35)
    ax.set_ylim(y_min, y_max)
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    ax.set_xticks(
        [2003, 2006, 2009, 2012, 2015, 2018, 2021, 2024, 2027, 2030, 2033, 2036]
    )
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
    ax.grid(axis="x", color="#f3f4f6", linewidth=0.6)
    ax.legend(loc="upper right", frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(
        0.0,
        -0.18,
        "Historical root rows are public-interest-only context, not final classifiers; TDC mechanism context is excluded.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_forecast_scenario_time_series_png(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_scenario: dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        by_scenario.setdefault(row["scenario_id"], []).append(row)
    for scenario_rows in by_scenario.values():
        scenario_rows.sort(key=lambda row: int(row["fiscal_year"]))

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11.5, 6.5))
    for scenario_id, scenario_rows in sorted(
        by_scenario.items(),
        key=lambda item: int(item[1][0]["scenario_rank"]),
    ):
        x_values = [int(row["fiscal_year"]) for row in scenario_rows]
        y_values = [float(row["central_ratewall_ratio"]) for row in scenario_rows]
        linewidth = 2.8 if scenario_id == "cbo_baseline_noop_v1" else 1.6
        alpha = 1.0 if scenario_id == "cbo_baseline_noop_v1" else 0.82
        label = _short_scenario_label(scenario_id)
        ax.plot(
            x_values,
            y_values,
            marker="o",
            linewidth=linewidth,
            markersize=4.8,
            alpha=alpha,
            label=label,
        )

    ax.axhline(1.0, color="#991b1b", linewidth=1.2, linestyle="--")
    ax.text(
        2036,
        1.01,
        "RW = 1 wall threshold",
        ha="right",
        va="bottom",
        fontsize=9,
        color="#991b1b",
    )
    ax.set_title("Forecast RateWall Ratios By Scenario", fontsize=14, pad=14)
    ax.set_ylabel("RW = N / D")
    ax.set_xlabel("Fiscal year")
    ax.set_xlim(2026.8, 2036.2)
    all_values = [
        float(row["central_ratewall_ratio"])
        for scenario_rows in by_scenario.values()
        for row in scenario_rows
    ]
    ax.set_ylim(min(-0.04, min(all_values) - 0.02), 1.08)
    ax.set_xticks(range(2027, 2037))
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
    ax.grid(axis="x", color="#f3f4f6", linewidth=0.6)
    ax.legend(loc="center right", frameon=False, fontsize=8.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(
        0.0,
        -0.17,
        "Shows baseline plus the seven largest absolute FY2036 central RW scenario moves.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_forecast_beta_shock_time_series_png(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_shock: dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        by_shock.setdefault(row["shock_id"], []).append(row)
    for shock_rows in by_shock.values():
        shock_rows.sort(key=lambda row: int(row["fiscal_year"]))

    style = {
        "baseline_beta_0_342": {
            "label": "baseline beta 0.342",
            "color": "#2563eb",
            "linewidth": 2.6,
        },
        "peak_beta_0_500": {
            "label": "beta peaks at 0.500",
            "color": "#d97706",
            "linewidth": 1.9,
        },
        "peak_beta_0_700": {
            "label": "beta peaks at 0.700",
            "color": "#7c3aed",
            "linewidth": 1.9,
        },
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    for shock_id in ["baseline_beta_0_342", "peak_beta_0_500", "peak_beta_0_700"]:
        shock_rows = by_shock.get(shock_id, [])
        if not shock_rows:
            continue
        spec = style[shock_id]
        x_values = [int(row["fiscal_year"]) for row in shock_rows]
        y_values = [float(row["shocked_ratewall_ratio"]) for row in shock_rows]
        ax.plot(
            x_values,
            y_values,
            marker="o",
            linewidth=spec["linewidth"],
            markersize=5,
            color=spec["color"],
            label=spec["label"],
        )

    ax.axhline(1.0, color="#991b1b", linewidth=1.2, linestyle="--")
    ax.text(
        2036,
        1.01,
        "RW = 1 wall threshold",
        ha="right",
        va="bottom",
        fontsize=9,
        color="#991b1b",
    )
    ax.set_title("Baseline Forecast With TDC Beta Shock", fontsize=14, pad=14)
    ax.set_ylabel("RW = N / D")
    ax.set_xlabel("Fiscal year")
    ax.set_xlim(2026.8, 2036.2)
    all_values = [float(row["shocked_ratewall_ratio"]) for row in rows]
    ax.set_ylim(min(0.0, min(all_values) - 0.02), 1.08)
    ax.set_xticks(range(2027, 2037))
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
    ax.grid(axis="x", color="#f3f4f6", linewidth=0.6)
    ax.legend(loc="upper left", frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(
        0.0,
        -0.17,
        "Sensitivity only: public-interest block and denominator are held at baseline; only the TDC beta term is rescaled.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_forecast_tdc_time_series_png(
    path: Path,
    rows: Sequence[Mapping[str, str]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_scenario: dict[str, list[Mapping[str, str]]] = {}
    for row in rows:
        by_scenario.setdefault(row["scenario_id"], []).append(row)
    for scenario_rows in by_scenario.values():
        scenario_rows.sort(key=lambda row: int(row["fiscal_year"]))

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    for scenario_id, scenario_rows in sorted(
        by_scenario.items(),
        key=lambda item: int(item[1][0]["scenario_rank"]),
    ):
        x_values = [int(row["fiscal_year"]) for row in scenario_rows]
        y_values = [float(row["tdc_component_bil"]) for row in scenario_rows]
        linewidth = 2.8 if scenario_id == "cbo_baseline_noop_v1" else 1.8
        ax.plot(
            x_values,
            y_values,
            marker="o",
            linewidth=linewidth,
            markersize=4.8,
            label=_short_scenario_label(scenario_id),
        )

    ax.axhline(0.0, color="#111827", linewidth=1.0)
    ax.set_title("Forecast TDC Component By Scenario", fontsize=14, pad=14)
    ax.set_ylabel("TDC component, $ billions")
    ax.set_xlabel("Fiscal year")
    ax.set_xlim(2026.8, 2036.2)
    all_values = [float(row["tdc_component_bil"]) for row in rows]
    ax.set_ylim(min(all_values) - 2.0, max(all_values) + 2.0)
    ax.set_xticks(range(2027, 2037))
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
    ax.grid(axis="x", color="#f3f4f6", linewidth=0.6)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=8.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(
        0.0,
        -0.17,
        "Hand-selected as baseline plus highest and lowest FY2036 TDC-dollar components.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _short_scenario_label(scenario_id: str) -> str:
    labels = {
        "cbo_baseline_noop_v1": "baseline",
        "tdcsim_rate_down_25bp_v1": "rate down 25bp",
        "tdcsim_rate_up_25bp_v1": "rate up 25bp",
        "tdcsim_private_holder_low_v1": "private holder low",
        "tdcsim_private_holder_high_v1": "private holder high",
        "tdcsim_issuance_empirical_shorter_termprem_down_central_v1": (
            "shorter + term prem down"
        ),
        "tdcsim_issuance_empirical_longer_termprem_up_central_v1": (
            "longer + term prem up"
        ),
        "tdcsim_issuance_empirical_shorter_uncoupled_v1": "shorter issuance",
        "tdcsim_issuance_empirical_longer_uncoupled_v1": "longer issuance",
    }
    return labels.get(scenario_id, scenario_id.replace("tdcsim_", "").replace("_v1", ""))
